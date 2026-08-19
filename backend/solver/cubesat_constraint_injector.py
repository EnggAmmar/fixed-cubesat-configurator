from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from .cubesat_cp_model_builder import BUS_CLASSES, TIERS, CubeSatModel, Tier
from .cubesat_data_loader import CubeSatData
from .cubesat_precompute_loader import PayloadPrecompute


S_MASS = 1000  # kg -> g
S_POWER = 1000  # W -> mW
S_VOL = 1000  # U -> mU
S_DATA = 1000  # GB -> MB
S_RATE = 1000  # Mb/s -> kb/s
S_DEG = 1_000_000  # deg -> microdeg

# Prompt 12.9 calibration factors (engineering packaging realism; conservative but not overbinding).
# NOTE(remediation step 4): left at their original values for now so step 2 (ordinal split)
# and step 3 (supported_bus_max) can be validated in isolation first; reset happens in step 4.
F_PACK_VOLUME = 0.72  # subsystem packaging concurrency factor for internal volume closure
F_MASS_RESERVE = 0.86  # reduce non-payload reserve conservatism (structure/harness-like)
F_RAD_UTIL = 1.15  # effective radiator utilization factor (bus-coupling)

# Integration-burden risk scoring (remediation): harness/EMI/contamination/radiation/
# vibration/deployment ordinals describe how awkward a payload is to integrate, not how
# capable a subsystem must be. They previously forced subsystem/bus tiers upward via hard
# >= constraints (e.g. comms tier >= harness ordinal), which is a category error: it let
# integration burden buy a payload a categorically more capable subsystem it never needed.
# They are additive risk-score inputs instead, so the optimizer weighs them as a cost
# rather than being forced to satisfy them as a feasibility wall.
_BURDEN_RISK_PTS = {1: 0, 2: 5, 3: 15, 4: 30}  # keyed by ordinal (1=LOW .. 4=EXTREME)


def burden_risk_pts(ordinal: int) -> int:
    return _BURDEN_RISK_PTS[ordinal]


def _ceil_scaled(value: float, scale: int) -> int:
    return int(math.ceil(value * scale - 1e-12))


def _floor_scaled(value: float, scale: int) -> int:
    return int(math.floor(value * scale + 1e-12))


def _ord_class(s: str) -> int:
    m = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EXTREME": 4}
    if s not in m:
        raise ValueError(f"Unknown class string: {s}")
    return m[s]


def _ord_cg(s: str) -> int:
    m = {"low": 1, "medium": 2, "high": 3}
    if s not in m:
        raise ValueError(f"Unknown cg_sensitivity_class: {s}")
    return m[s]


def _bus_ord(u: str) -> int:
    # Must align to Prompt 10 ordering.
    order = {b: i + 1 for i, b in enumerate(BUS_CLASSES)}
    if u not in order:
        raise ValueError(f"Unknown bus class: {u}")
    return order[u]


def _tier_ord(k: Tier) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EXTREME": 4}[k]


def _get_assumption(assumptions: dict[str, Any], section: str, key: str) -> float:
    try:
        v = assumptions[section][key]["value"]
        return float(v)
    except Exception as e:
        raise ValueError(f"Missing/invalid assumption {section}.{key}.value") from e


@dataclass(frozen=True)
class _PayloadInts:
    payload_id: str
    mass_g: int
    envelope_mU: int
    bus_min_u_mU: int
    bus_min_mass_g: int

    avg_power_mw: int
    nominal_rate_kbps: int
    pointing_req_uDeg: int
    cg_ord: int

    integration_risk: str

    pre_P_payload_peak_eff_mw: int
    pre_S_req_MB: int
    pre_R_ing_req_kbps: int
    pre_Q_payload_req_mw: int

    pre_fine_point: int
    pre_ultra_fine: int
    pre_extreme_data: int
    pre_high_thermal: int
    pre_DV_req_mps: int

    ord_req_eps: int
    ord_req_adcs: int
    ord_req_comms: int
    ord_req_obc: int
    ord_req_therm: int
    ord_req_struct: int
    ord_req_prop: int

    # Compatibility semantic propagation burdens (Prompt 12.5)
    ord_rad: int
    ord_vibe: int
    ord_emi: int
    ord_contam: int
    ord_deploy: int
    ord_harness: int


def _build_payload_ints(
    data: CubeSatData, precompute: PayloadPrecompute
) -> dict[str, _PayloadInts]:
    out: dict[str, _PayloadInts] = {}
    for pid, rec in data.payloads.items():
        prod = rec.product
        pre = precompute.payloads.get(pid, {})
        if not isinstance(pre, dict):
            raise ValueError(f"payload_precompute_constants missing payload_id: {pid}")
        ppre = pre.get("precompute", {})
        if not isinstance(ppre, dict):
            raise ValueError(f"payload_precompute_constants invalid precompute block for: {pid}")

        mass_g = _ceil_scaled(float(prod.get("mass_kg", 0.0) or 0.0), S_MASS)
        env_mU = _ceil_scaled(float(prod.get("payload_envelope_u", 0.0) or 0.0), S_VOL)
        bus_min_u = _ceil_scaled(float(prod.get("recommended_bus_min_u", 0.0) or 0.0), S_VOL)
        bus_min_mass_g = _ceil_scaled(
            float(prod.get("recommended_bus_min_mass_kg", 0.0) or 0.0), S_MASS
        )

        avg_mw = _ceil_scaled(float(prod.get("avg_power_w", 0.0) or 0.0), S_POWER)
        nominal_rate_kbps = _ceil_scaled(
            float(prod.get("nominal_data_rate_mbps", 0.0) or 0.0), S_RATE
        )
        pointing_uDeg = _ceil_scaled(
            float(prod.get("pointing_requirement_deg", 999.0) or 999.0), S_DEG
        )
        cg_ord = _ord_cg(str(prod.get("cg_sensitivity_class") or "low"))

        integration_risk = str(prod.get("integration_risk") or "medium")

        pre_peak_eff_mw = _ceil_scaled(float(ppre["P_payload_peak_eff_w"]), S_POWER)
        pre_S_req_MB = _ceil_scaled(float(ppre["S_req_gb"]), S_DATA)
        pre_R_ing_req_kbps = _ceil_scaled(float(ppre["R_ing_req_mbps"]), S_RATE)
        pre_Q_payload_req_mw = _ceil_scaled(float(ppre["Q_payload_req_w"]), S_POWER)

        out[pid] = _PayloadInts(
            payload_id=pid,
            mass_g=mass_g,
            envelope_mU=env_mU,
            bus_min_u_mU=bus_min_u,
            bus_min_mass_g=bus_min_mass_g,
            avg_power_mw=avg_mw,
            nominal_rate_kbps=nominal_rate_kbps,
            pointing_req_uDeg=pointing_uDeg,
            cg_ord=cg_ord,
            integration_risk=integration_risk,
            pre_P_payload_peak_eff_mw=pre_peak_eff_mw,
            pre_S_req_MB=pre_S_req_MB,
            pre_R_ing_req_kbps=pre_R_ing_req_kbps,
            pre_Q_payload_req_mw=pre_Q_payload_req_mw,
            pre_fine_point=int(ppre["fine_point"]),
            pre_ultra_fine=int(ppre["ultra_fine"]),
            pre_extreme_data=int(ppre["extreme_data"]),
            pre_high_thermal=int(ppre["high_thermal"]),
            pre_DV_req_mps=int(ppre["DV_req_mps"]),
            ord_req_eps=int(ppre["ord_req_eps"]),
            ord_req_adcs=int(ppre["ord_req_adcs"]),
            ord_req_comms=int(ppre["ord_req_comms"]),
            ord_req_obc=int(ppre["ord_req_obc"]),
            ord_req_therm=int(ppre["ord_req_therm"]),
            ord_req_struct=int(ppre["ord_req_struct"]),
            ord_req_prop=int(ppre["ord_req_prop"]),
            ord_rad=int(ppre["ord_rad"]),
            ord_vibe=int(ppre["ord_vibe"]),
            ord_emi=int(ppre["ord_emi"]),
            ord_contam=int(ppre["ord_contam"]),
            ord_deploy=int(ppre["ord_deploy"]),
            ord_harness=int(ppre["ord_harness"]),
        )
    return out


def inject_constraints(
    sm: CubeSatModel, data: CubeSatData, precompute: PayloadPrecompute, selected_payload_id: str
) -> None:
    model = sm.model
    v = sm.vars

    payload_ints = _build_payload_ints(data, precompute)
    if selected_payload_id not in payload_ints:
        raise ValueError(f"Unknown selected_payload_id: {selected_payload_id}")

    # ---- 2) One-hot constraints ----
    model.add(sum(v.x_payload.values()) == 1)
    model.add(sum(v.b_bus.values()) == 1)
    model.add(sum(v.e_eps.values()) == 1)
    model.add(sum(v.a_adcs.values()) == 1)
    model.add(sum(v.c_comms.values()) == 1)
    model.add(sum(v.o_obc.values()) == 1)
    model.add(sum(v.t_thermal.values()) == 1)
    model.add(sum(v.p_prop.values()) == 1)

    # Fix payload selection externally.
    for pid, x in v.x_payload.items():
        model.add(x == (1 if pid == selected_payload_id else 0))

    # ---- Assumptions (Prompt 10 / 11.5) ----
    ass = data.assumptions
    f_sun = _get_assumption(ass, "power_assumptions", "sunlight_fraction")
    f_ecl = _get_assumption(ass, "power_assumptions", "eclipse_fraction")
    eta_eps = _get_assumption(ass, "power_assumptions", "eps_efficiency")
    k_deg = _get_assumption(ass, "power_assumptions", "solar_degradation_factor_eol")
    M_pow = _get_assumption(ass, "power_assumptions", "power_margin_factor")
    M_peak = _get_assumption(ass, "power_assumptions", "peak_power_headroom_factor")

    DoD_lim = _get_assumption(ass, "battery_assumptions", "battery_dod_limit")
    eta_batt = _get_assumption(ass, "battery_assumptions", "battery_round_trip_efficiency")
    k_batt = _get_assumption(ass, "battery_assumptions", "battery_capacity_derating_factor")

    M_mass = _get_assumption(ass, "mass_margin_assumptions", "mass_growth_margin")
    f_fill = _get_assumption(ass, "volume_margin_assumptions", "volume_fill_limit")
    U_over_u = _get_assumption(ass, "volume_margin_assumptions", "payload_volume_overhead_u")
    M_data = _get_assumption(ass, "data_storage_assumptions", "daily_data_contingency_margin")

    eta_dl = _get_assumption(ass, "downlink_assumptions", "downlink_efficiency_factor")
    T_contact_day_min = _get_assumption(ass, "downlink_assumptions", "nominal_contact_minutes_per_day")
    f_contact_use = _get_assumption(ass, "downlink_assumptions", "usable_contact_fraction")

    f_heat_int = _get_assumption(ass, "thermal_assumptions", "internal_heat_fraction_default")

    # Centralized engineering constants (no hardcoded numeric literals in constraints).
    Pdens_sunlit_W_per_m2 = _get_assumption(
        ass, "solar_generation_assumptions", "Pdens_sunlit_W_per_m2"
    )
    T_orbit_hr = _get_assumption(ass, "orbit_assumptions", "nominal_orbit_period_hr")

    # ---- Precompute selection expressions (linear) ----
    # Payload-selected scalars (only one payload is allowed, but keep it generic).
    m_payload_g = sum(v.x_payload[pid] * payload_ints[pid].mass_g for pid in payload_ints)
    U_payload_mU = sum(v.x_payload[pid] * payload_ints[pid].envelope_mU for pid in payload_ints)
    bus_min_u_sel_mU = sum(
        v.x_payload[pid] * payload_ints[pid].bus_min_u_mU for pid in payload_ints
    )
    bus_min_mass_sel_g = sum(
        v.x_payload[pid] * payload_ints[pid].bus_min_mass_g for pid in payload_ints
    )

    P_payload_avg_mw = sum(
        v.x_payload[pid] * payload_ints[pid].avg_power_mw for pid in payload_ints
    )
    P_payload_peak_eff_mw = sum(
        v.x_payload[pid] * payload_ints[pid].pre_P_payload_peak_eff_mw for pid in payload_ints
    )

    pointing_req_uDeg = sum(
        v.x_payload[pid] * payload_ints[pid].pointing_req_uDeg for pid in payload_ints
    )
    cg_ord_sel = sum(v.x_payload[pid] * payload_ints[pid].cg_ord for pid in payload_ints)

    fine_point_sel = sum(
        v.x_payload[pid] * payload_ints[pid].pre_fine_point for pid in payload_ints
    )
    ultra_fine_sel = sum(
        v.x_payload[pid] * payload_ints[pid].pre_ultra_fine for pid in payload_ints
    )
    extreme_data_sel = sum(
        v.x_payload[pid] * payload_ints[pid].pre_extreme_data for pid in payload_ints
    )
    high_thermal_sel = sum(
        v.x_payload[pid] * payload_ints[pid].pre_high_thermal for pid in payload_ints
    )

    DV_req_sel = sum(v.x_payload[pid] * payload_ints[pid].pre_DV_req_mps for pid in payload_ints)

    ord_req_eps_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_req_eps for pid in payload_ints)
    ord_req_adcs_sel = sum(
        v.x_payload[pid] * payload_ints[pid].ord_req_adcs for pid in payload_ints
    )
    ord_req_comms_sel = sum(
        v.x_payload[pid] * payload_ints[pid].ord_req_comms for pid in payload_ints
    )
    ord_req_obc_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_req_obc for pid in payload_ints)
    ord_req_therm_sel = sum(
        v.x_payload[pid] * payload_ints[pid].ord_req_therm for pid in payload_ints
    )
    ord_req_struct_sel = sum(
        v.x_payload[pid] * payload_ints[pid].ord_req_struct for pid in payload_ints
    )
    ord_req_prop_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_req_prop for pid in payload_ints)

    # Compatibility semantic propagation burdens (Prompt 12.5).
    ord_rad_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_rad for pid in payload_ints)
    ord_vibe_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_vibe for pid in payload_ints)
    ord_emi_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_emi for pid in payload_ints)
    ord_contam_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_contam for pid in payload_ints)
    ord_deploy_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_deploy for pid in payload_ints)
    ord_harness_sel = sum(v.x_payload[pid] * payload_ints[pid].ord_harness for pid in payload_ints)

    # Integration-burden risk score (see _BURDEN_RISK_PTS): additive, not a tier floor.
    burden_risk_sel = sum(
        v.x_payload[pid]
        * (
            burden_risk_pts(payload_ints[pid].ord_harness)
            + burden_risk_pts(payload_ints[pid].ord_emi)
            + burden_risk_pts(payload_ints[pid].ord_contam)
            + burden_risk_pts(payload_ints[pid].ord_rad)
            + burden_risk_pts(payload_ints[pid].ord_vibe)
            + burden_risk_pts(payload_ints[pid].ord_deploy)
        )
        for pid in payload_ints
    )
    model.add(v.IntegrationBurdenRisk_total == burden_risk_sel)

    # ---- 4) Bus feasibility (volume + mass + minimums) ----
    U_over_mU = _ceil_scaled(U_over_u, S_VOL)

    # Bus selection projections from bus library.
    U_bus_sel_mU = sum(
        v.b_bus[u] * _ceil_scaled(float(data.bus_library[u]["u_bus"]), S_VOL) for u in BUS_CLASSES
    )
    U_usable_sel_mU = sum(
        v.b_bus[u]
        * _floor_scaled(float(data.bus_library[u]["usable_internal_volume_u"]), S_VOL)
        for u in BUS_CLASSES
    )
    U_bus_struct_sel_mU = sum(
        v.b_bus[u]
        * _ceil_scaled(float(data.bus_library[u]["bus_structure_volume_u"]), S_VOL)
        for u in BUS_CLASSES
    )

    M_dry_max_sel_g = sum(
        v.b_bus[u]
        * _floor_scaled(float(data.bus_library[u]["max_recommended_dry_mass_kg"]), S_MASS)
        for u in BUS_CLASSES
    )
    m_bus_struct_sel_g = sum(
        v.b_bus[u]
        * _ceil_scaled(float(data.bus_library[u]["bus_structure_mass_kg"]), S_MASS)
        for u in BUS_CLASSES
    )

    # Subsystem volumes and masses (library-derived proxies).
    def _tier_sum(var_map: dict[Tier, cp_model.IntVar], coeffs: dict[Tier, int]) -> cp_model.LinearExpr:
        return sum(var_map[k] * coeffs[k] for k in TIERS)

    U_eps_mU = {k: _ceil_scaled(float(data.eps_library[k]["eps_volume_u"]), S_VOL) for k in TIERS}
    m_eps_g = {k: _ceil_scaled(float(data.eps_library[k]["eps_mass_kg"]), S_MASS) for k in TIERS}
    U_adcs_mU = {k: _ceil_scaled(float(data.adcs_library[k]["adcs_volume_u"]), S_VOL) for k in TIERS}
    m_adcs_g = {k: _ceil_scaled(float(data.adcs_library[k]["adcs_mass_kg"]), S_MASS) for k in TIERS}
    U_comms_mU = {k: _ceil_scaled(float(data.comms_library[k]["comms_volume_u"]), S_VOL) for k in TIERS}
    m_comms_g = {k: _ceil_scaled(float(data.comms_library[k]["comms_mass_kg"]), S_MASS) for k in TIERS}
    U_obc_mU = {k: _ceil_scaled(float(data.obc_library[k]["obc_volume_u"]), S_VOL) for k in TIERS}
    m_obc_g = {k: _ceil_scaled(float(data.obc_library[k]["obc_mass_kg"]), S_MASS) for k in TIERS}
    U_therm_mU = {
        k: _ceil_scaled(float(data.thermal_library[k]["thermal_volume_u"]), S_VOL) for k in TIERS
    }
    m_therm_g = {
        k: _ceil_scaled(float(data.thermal_library[k]["thermal_mass_kg"]), S_MASS) for k in TIERS
    }
    U_prop_mU = {
        k: _ceil_scaled(float(data.propulsion_library[k]["propellant_volume_u"]), S_VOL)
        for k in TIERS
    }
    m_prop_g = {k: _ceil_scaled(float(data.propulsion_library[k]["prop_mass_kg"]), S_MASS) for k in TIERS}

    U_sub_mU = (
        _tier_sum(v.e_eps, U_eps_mU)
        + _tier_sum(v.a_adcs, U_adcs_mU)
        + _tier_sum(v.c_comms, U_comms_mU)
        + _tier_sum(v.o_obc, U_obc_mU)
        + _tier_sum(v.t_thermal, U_therm_mU)
        + _tier_sum(v.p_prop, U_prop_mU)
    )
    M_sub_g = (
        _tier_sum(v.e_eps, m_eps_g)
        + _tier_sum(v.a_adcs, m_adcs_g)
        + _tier_sum(v.c_comms, m_comms_g)
        + _tier_sum(v.o_obc, m_obc_g)
        + _tier_sum(v.t_thermal, m_therm_g)
        + _tier_sum(v.p_prop, m_prop_g)
    )

    # Volume closure (Prompt 12.9): subsystem volumes are not purely additive in practice due to
    # shared avionics stacking, panel-mounted electronics, and co-packaging of harness/thermal
    # hardware. Model this via a conservative packaging concurrency factor applied to subsystem U.
    # Payload envelope and harness reserve are NOT reduced.
    #
    # effective_subsystem_volume = F_PACK_VOLUME * (EPS_u + ADCS_u + COMMS_u + OBC_u + THERM_u + PROP_u)
    # U_total = payload_envelope + harness_overhead + effective_subsystem_volume
    f_pack_num = int(round(F_PACK_VOLUME * 100))
    U_sub_eff_mU = model.new_int_var(0, 200_000, "U_sub_eff_mU")
    # U_sub_eff_mU = ceil((f_pack_num/100) * U_sub_mU) in mU units.
    model.add(U_sub_eff_mU * 100 >= U_sub_mU * f_pack_num)
    model.add(U_sub_eff_mU * 100 <= U_sub_mU * f_pack_num + 99)

    model.add(v.U_total_mU == U_payload_mU + U_over_mU + U_sub_eff_mU)
    model.add(v.U_total_mU <= U_usable_sel_mU)

    # Optional fill limit: U_total <= f_fill * U_bus
    f_fill_num = int(round(f_fill * 1000))
    model.add(v.U_total_mU * 1000 <= U_bus_sel_mU * f_fill_num)

    # Mass totals with growth margin.
    # Prompt 12.9: reduce overbinding reserve conservatism by applying F_MASS_RESERVE only to
    # non-payload reserve adders (structure/harness-like). Payload and subsystem masses remain unchanged.
    M_payload_sub_nom_g = m_payload_g + M_sub_g
    M_mass_ppm = int(round(M_mass * 1000))
    M_mass_bus_ppm = int(round((M_mass * F_MASS_RESERVE) * 1000))
    # v.M_total_g = ceil( (1+M_mass)*(payload+subsystems) + (1+F_MASS_RESERVE*M_mass)*bus_structure )
    rhs_scaled = (
        M_payload_sub_nom_g * (1000 + M_mass_ppm) + m_bus_struct_sel_g * (1000 + M_mass_bus_ppm)
    )
    model.add(v.M_total_g * 1000 >= rhs_scaled)
    model.add(v.M_total_g * 1000 <= rhs_scaled + 999)
    model.add(v.M_total_g <= M_dry_max_sel_g)

    # Bus minimum hints.
    model.add(U_bus_sel_mU >= bus_min_u_sel_mU)
    model.add(M_dry_max_sel_g >= bus_min_mass_sel_g)

    # Structure/CG compatibility (ordinal).
    ord_bus_stiff_sel = sum(
        v.b_bus[u] * _ord_class(str(data.bus_library[u]["structural_stiffness_class"]))
        for u in BUS_CLASSES
    )
    ord_bus_cg_tol_sel = sum(
        v.b_bus[u] * _ord_class(str(data.bus_library[u]["cg_tolerance_class"])) for u in BUS_CLASSES
    )
    model.add(ord_bus_stiff_sel >= ord_req_struct_sel)
    model.add(ord_bus_cg_tol_sel >= cg_ord_sel)

    # Radiation/vibration/deployment ruggedization burdens are integration-burden risk
    # inputs (see _BURDEN_RISK_PTS), not a hard floor on bus structural stiffness.

    # Bus oversize penalty (Prompt 11.5): U_bus - recommended_min_u
    model.add(v.BusOversize_mU == U_bus_sel_mU - bus_min_u_sel_mU)

    # ---- 5) EPS constraints ----
    # Power closure (avg).
    P_eps_self_mw = {k: _ceil_scaled(float(data.eps_library[k]["eps_avg_self_consumption_w"]), S_POWER) for k in TIERS}
    P_adcs_avg_mw = {k: _ceil_scaled(float(data.adcs_library[k]["adcs_avg_power_w"]), S_POWER) for k in TIERS}
    P_tx_avg_mw = {k: _ceil_scaled(float(data.comms_library[k]["tx_avg_power_w"]), S_POWER) for k in TIERS}
    P_obc_avg_mw = {k: _ceil_scaled(float(data.obc_library[k]["obc_avg_power_w"]), S_POWER) for k in TIERS}
    P_therm_avg_mw = {k: _ceil_scaled(float(data.thermal_library[k]["thermal_avg_power_w"]), S_POWER) for k in TIERS}
    P_prop_avg_mw = {k: _ceil_scaled(float(data.propulsion_library[k]["prop_avg_power_w"]), S_POWER) for k in TIERS}

    P_sub_avg_mw = (
        _tier_sum(v.e_eps, P_eps_self_mw)
        + _tier_sum(v.a_adcs, P_adcs_avg_mw)
        + _tier_sum(v.c_comms, P_tx_avg_mw)
        + _tier_sum(v.o_obc, P_obc_avg_mw)
        + _tier_sum(v.t_thermal, P_therm_avg_mw)
        + _tier_sum(v.p_prop, P_prop_avg_mw)
    )
    P_avg_base_mw = P_payload_avg_mw + P_sub_avg_mw
    M_pow_num = int(round(M_pow * 1000))
    model.add(v.P_avg_total_mw * 1000 >= P_avg_base_mw * M_pow_num)
    model.add(v.P_avg_total_mw * 1000 <= P_avg_base_mw * M_pow_num + 999)

    # Solar feasibility converted to P_avg_total caps (no P_solar_req var).
    eps_solar_cap_mw: dict[Tier, int] = {}
    for k in TIERS:
        P_solar_eps_max_w = float(data.eps_library[k]["max_solar_generation_w"])
        cap_w = P_solar_eps_max_w * eta_eps * k_deg * f_sun
        eps_solar_cap_mw[k] = _floor_scaled(cap_w, S_POWER)
    model.add(v.P_avg_total_mw <= _tier_sum(v.e_eps, eps_solar_cap_mw))

    bus_area_cap_mw: dict[str, int] = {}
    for u in BUS_CLASSES:
        A_total = float(data.bus_library[u]["available_body_solar_area_m2"]) + float(
            data.bus_library[u]["deployable_panel_option_area_m2"]
        )
        cap_w = (Pdens_sunlit_W_per_m2 * A_total) * eta_eps * k_deg * f_sun
        bus_area_cap_mw[u] = _floor_scaled(cap_w, S_POWER)
    model.add(v.P_avg_total_mw <= sum(v.b_bus[u] * bus_area_cap_mw[u] for u in BUS_CLASSES))

    # Battery feasibility converted to P_avg_total caps.
    def _pavg_cap_from_batt_wh(C_wh: float) -> int:
        cap_w = (C_wh * eta_eps * DoD_lim * k_batt * eta_batt) / (f_ecl * T_orbit_hr)
        return _floor_scaled(cap_w, S_POWER)

    eps_batt_cap_mw = {k: _pavg_cap_from_batt_wh(float(data.eps_library[k]["max_battery_capacity_wh"])) for k in TIERS}
    model.add(v.P_avg_total_mw <= _tier_sum(v.e_eps, eps_batt_cap_mw))

    bus_pack_batt_cap_mw = {u: _pavg_cap_from_batt_wh(float(data.bus_library[u]["battery_packaging_limit_wh"])) for u in BUS_CLASSES}
    model.add(v.P_avg_total_mw <= sum(v.b_bus[u] * bus_pack_batt_cap_mw[u] for u in BUS_CLASSES))

    # Peak power feasibility.
    P_adcs_peak_mw = {k: _ceil_scaled(float(data.adcs_library[k]["adcs_peak_power_w"]), S_POWER) for k in TIERS}
    P_tx_peak_mw = {k: _ceil_scaled(float(data.comms_library[k]["tx_peak_power_w"]), S_POWER) for k in TIERS}
    P_obc_peak_mw = {k: _ceil_scaled(float(data.obc_library[k]["obc_peak_power_w"]), S_POWER) for k in TIERS}
    P_therm_peak_mw = {k: _ceil_scaled(float(data.thermal_library[k]["thermal_peak_power_w"]), S_POWER) for k in TIERS}
    P_prop_peak_mw = {k: _ceil_scaled(float(data.propulsion_library[k]["prop_peak_power_w"]), S_POWER) for k in TIERS}

    P_sub_peak_mw = (
        _tier_sum(v.a_adcs, P_adcs_peak_mw)
        + _tier_sum(v.c_comms, P_tx_peak_mw)
        + _tier_sum(v.o_obc, P_obc_peak_mw)
        + _tier_sum(v.t_thermal, P_therm_peak_mw)
        + _tier_sum(v.p_prop, P_prop_peak_mw)
    )
    P_peak_base_mw = P_payload_peak_eff_mw + P_sub_peak_mw
    M_peak_num = int(round(M_peak * 1000))
    model.add(v.P_peak_total_mw * 1000 >= P_peak_base_mw * M_peak_num)
    model.add(v.P_peak_total_mw * 1000 <= P_peak_base_mw * M_peak_num + 999)

    P_peak_bus_max_mw = {k: _floor_scaled(float(data.eps_library[k]["max_peak_bus_power_w"]), S_POWER) for k in TIERS}
    model.add(v.P_peak_total_mw <= _tier_sum(v.e_eps, P_peak_bus_max_mw))

    # EPS compatibility ordinal: selected EPS tier must meet required class.
    ord_eps_tier = sum(v.e_eps[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_eps_tier >= ord_req_eps_sel)

    # EPS supported bus range: forbid unsupported (bus, tier) pairs.
    for k in TIERS:
        min_u = str(data.eps_library[k]["supported_bus_min"])
        max_u = str(data.eps_library[k]["supported_bus_max"])
        min_ord = _bus_ord(min_u)
        max_ord = _bus_ord(max_u)
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.e_eps[k] + v.b_bus[u] <= 1)

    # ---- 6) ADCS constraints ----
    # Pointing: achievable error must be <= required error.
    point_acc_uDeg = {k: _floor_scaled(float(data.adcs_library[k]["pointing_accuracy_deg"]), S_DEG) for k in TIERS}
    point_acc_sel = _tier_sum(v.a_adcs, point_acc_uDeg)
    model.add(point_acc_sel <= pointing_req_uDeg)

    # Disturbance rejection / CG sensitivity.
    ord_adcs_reject = {
        k: _ord_class(str(data.adcs_library[k]["disturbance_rejection_class"])) for k in TIERS
    }
    ord_adcs_reject_sel = _tier_sum(v.a_adcs, ord_adcs_reject)
    model.add(ord_adcs_reject_sel >= cg_ord_sel)

    ord_adcs_tier = sum(v.a_adcs[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_adcs_tier >= ord_req_adcs_sel)

    # Supported bus range.
    for k in TIERS:
        min_ord = _bus_ord(str(data.adcs_library[k]["supported_bus_min"]))
        max_ord = _bus_ord(str(data.adcs_library[k]["supported_bus_max"]))
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.a_adcs[k] + v.b_bus[u] <= 1)

    # Fine pointing no-goods.
    model.add(fine_point_sel + v.a_adcs["LOW"] <= 1)
    model.add(ultra_fine_sel + v.a_adcs["MEDIUM"] <= 1)

    # ---- 7) COMMS constraints ----
    R_comms_max_kbps = {k: _floor_scaled(float(data.comms_library[k]["nominal_supported_downlink_mbps"]), S_RATE) for k in TIERS}
    model.add(sum(v.c_comms[k] * R_comms_max_kbps[k] for k in TIERS) >= sum(v.x_payload[pid] * payload_ints[pid].nominal_rate_kbps for pid in payload_ints))

    # Daily downlink closure.
    T_eff_day_min = T_contact_day_min * f_contact_use
    D_day_cap_MB: dict[Tier, int] = {}
    for k in TIERS:
        R_mbps = float(data.comms_library[k]["nominal_supported_downlink_mbps"])
        cap_mb = math.floor(R_mbps * eta_dl * T_eff_day_min * 60.0 / 8.0 + 1e-12)
        D_day_cap_MB[k] = int(max(0, cap_mb))

    D_day_req_MB_by_payload = {}
    for pid, p in payload_ints.items():
        daily_mb = _ceil_scaled(float(data.payloads[pid].product.get("daily_data_generation_gb", 0.0) or 0.0), S_DATA)
        D_day_req_MB_by_payload[pid] = int(math.ceil(daily_mb * M_data - 1e-12))
    D_day_req_sel_MB = sum(v.x_payload[pid] * D_day_req_MB_by_payload[pid] for pid in payload_ints)
    model.add(D_day_req_sel_MB <= _tier_sum(v.c_comms, D_day_cap_MB))

    # COMMS pointing dependency: ADCS tier ordinal >= comms dependency ordinal.
    ord_comms_point_dep = {
        k: _ord_class(str(data.comms_library[k]["pointing_dependency"])) for k in TIERS
    }
    ord_comms_point_dep_sel = _tier_sum(v.c_comms, ord_comms_point_dep)
    model.add(ord_adcs_tier >= ord_comms_point_dep_sel)

    ord_comms_tier = sum(v.c_comms[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_comms_tier >= ord_req_comms_sel)

    # EMI and harness burdens are integration-burden risk inputs, not a hard floor on the
    # COMMS tier (see _BURDEN_RISK_PTS).

    # Supported bus range.
    for k in TIERS:
        min_ord = _bus_ord(str(data.comms_library[k]["supported_bus_min"]))
        max_ord = _bus_ord(str(data.comms_library[k]["supported_bus_max"]))
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.c_comms[k] + v.b_bus[u] <= 1)

    # Extreme data no-goods.
    model.add(extreme_data_sel + v.c_comms["LOW"] <= 1)

    # COMMS-ADCS no-goods (explicit).
    model.add(v.c_comms["EXTREME"] + v.a_adcs["LOW"] <= 1)
    model.add(v.c_comms["EXTREME"] + v.a_adcs["MEDIUM"] <= 1)
    model.add(v.c_comms["HIGH"] + v.a_adcs["LOW"] <= 1)

    # ---- 8) OBC constraints ----
    S_store_max_MB = {k: _floor_scaled(float(data.obc_library[k]["max_storage_gb"]), S_DATA) for k in TIERS}
    S_req_sel_MB = sum(v.x_payload[pid] * payload_ints[pid].pre_S_req_MB for pid in payload_ints)
    model.add(S_req_sel_MB <= _tier_sum(v.o_obc, S_store_max_MB))

    R_ingest_max_kbps = {k: _floor_scaled(float(data.obc_library[k]["supported_ingest_mbps"]), S_RATE) for k in TIERS}
    R_ing_req_sel_kbps = sum(
        v.x_payload[pid] * payload_ints[pid].pre_R_ing_req_kbps for pid in payload_ints
    )
    model.add(R_ing_req_sel_kbps <= _tier_sum(v.o_obc, R_ingest_max_kbps))

    ord_obc_tier = sum(v.o_obc[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_obc_tier >= ord_req_obc_sel)

    # EMI and harness burdens are integration-burden risk inputs, not a hard floor on the
    # OBC tier (see _BURDEN_RISK_PTS).

    for k in TIERS:
        min_ord = _bus_ord(str(data.obc_library[k]["supported_bus_min"]))
        max_ord = _bus_ord(str(data.obc_library[k]["supported_bus_max"]))
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.o_obc[k] + v.b_bus[u] <= 1)

    # Extreme data no-goods (OBC).
    model.add(extreme_data_sel + v.o_obc["LOW"] <= 1)

    # ---- 9) THERMAL constraints ----
    # Total heat requirement = payload heat (precomputed) + subsystem heat proxy.
    Q_payload_req_sel_mw = sum(
        v.x_payload[pid] * payload_ints[pid].pre_Q_payload_req_mw for pid in payload_ints
    )

    # Q_sub_req_mw approx = M_th * f_heat_int * P_sub_avg_mw
    # M_th is already applied inside Q_payload_req in precompute; apply same for subsystems here.
    M_th = _get_assumption(ass, "thermal_assumptions", "thermal_margin_factor")
    coeff = M_th * f_heat_int  # e.g. 1.2 * 0.9 = 1.08
    coeff_num = int(round(coeff * 1000))
    Q_sub_req_mw = model.new_int_var(0, 5_000_000, "Q_sub_req_mw")
    model.add(Q_sub_req_mw * 1000 >= P_sub_avg_mw * coeff_num)
    model.add(Q_sub_req_mw * 1000 <= P_sub_avg_mw * coeff_num + 999)

    Q_req_mw = model.new_int_var(0, 10_000_000, "Q_req_mw")
    model.add(Q_req_mw == Q_payload_req_sel_mw + Q_sub_req_mw)

    Q_tier_max_mw = {k: _floor_scaled(float(data.thermal_library[k]["max_heat_rejection_w"]), S_POWER) for k in TIERS}
    model.add(Q_req_mw <= _tier_sum(v.t_thermal, Q_tier_max_mw))

    # Bus radiator coupling cap via AND z_{u,k}.
    z: dict[tuple[str, Tier], cp_model.IntVar] = {}
    for u in BUS_CLASSES:
        for k in TIERS:
            z[(u, k)] = model.new_bool_var(f"z_therm[{u},{k}]")
            model.add(z[(u, k)] <= v.b_bus[u])
            model.add(z[(u, k)] <= v.t_thermal[k])
            model.add(z[(u, k)] >= v.b_bus[u] + v.t_thermal[k] - 1)
    model.add(sum(z.values()) == 1)

    Q_bus_cap_mw: dict[tuple[str, Tier], int] = {}
    for u in BUS_CLASSES:
        A_rad = float(data.bus_library[u]["nominal_radiator_area_m2"])
        for k in TIERS:
            q_density = float(data.thermal_library[k]["q_reject_density_w_per_m2"])
            cap_w = q_density * A_rad * F_RAD_UTIL
            Q_bus_cap_mw[(u, k)] = _floor_scaled(cap_w, S_POWER)
    model.add(Q_req_mw <= sum(z[(u, k)] * Q_bus_cap_mw[(u, k)] for u in BUS_CLASSES for k in TIERS))

    ord_therm_tier = sum(v.t_thermal[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_therm_tier >= ord_req_therm_sel)

    # Contamination cleanliness is an integration-burden risk input, not a hard floor on
    # the thermal tier (see _BURDEN_RISK_PTS).

    for k in TIERS:
        min_ord = _bus_ord(str(data.thermal_library[k]["supported_bus_min"]))
        max_ord = _bus_ord(str(data.thermal_library[k]["supported_bus_max"]))
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.t_thermal[k] + v.b_bus[u] <= 1)

    # High thermal no-good: forbid LOW thermal.
    model.add(high_thermal_sel + v.t_thermal["LOW"] <= 1)

    # ---- 10) PROPULSION constraints ----
    DV_cap = {k: int(data.propulsion_library[k]["delta_v_support_mps"]) for k in TIERS}
    model.add(_tier_sum(v.p_prop, DV_cap) >= DV_req_sel)

    ord_prop_tier = sum(v.p_prop[k] * _tier_ord(k) for k in TIERS)
    model.add(ord_prop_tier >= ord_req_prop_sel)

    # Deployment burden is an integration-burden risk input, not a hard floor on the
    # propulsion tier (see _BURDEN_RISK_PTS).

    for k in TIERS:
        min_ord = _bus_ord(str(data.propulsion_library[k]["supported_bus_min"]))
        max_ord = _bus_ord(str(data.propulsion_library[k]["supported_bus_max"]))
        for u in BUS_CLASSES:
            if not (min_ord <= _bus_ord(u) <= max_ord):
                model.add(v.p_prop[k] + v.b_bus[u] <= 1)

    # ---- 11) Cross-subsystem forbidden combinations ----
    # If bus <= 2U, forbid EXTREME EPS and EXTREME PROP.
    model.add(v.b_bus["1U"] + v.b_bus["1.5U"] + v.b_bus["2U"] + v.e_eps["EXTREME"] <= 1)
    model.add(v.b_bus["1U"] + v.b_bus["1.5U"] + v.b_bus["2U"] + v.p_prop["EXTREME"] <= 1)

    # If bus is 1U, forbid HIGH/EXTREME COMMS.
    model.add(v.b_bus["1U"] + v.c_comms["HIGH"] <= 1)
    model.add(v.b_bus["1U"] + v.c_comms["EXTREME"] <= 1)
