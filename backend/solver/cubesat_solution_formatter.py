from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ortools.sat.python import cp_model

from .cubesat_constraint_injector import F_PACK_VOLUME
from .cubesat_cp_model_builder import TIERS, CubeSatModel, Tier
from .cubesat_data_loader import CubeSatData
from .cubesat_precompute_loader import ObjectiveCoefficients


@dataclass(frozen=True)
class _Selection:
    payload_id: str
    bus_class: str
    eps_tier: Tier
    adcs_tier: Tier
    comms_tier: Tier
    obc_tier: Tier
    thermal_tier: Tier
    prop_tier: Tier


def _picked_one(vars_map: dict[str, cp_model.IntVar], solver: cp_model.CpSolver) -> str:
    for k, v in vars_map.items():
        if solver.value(v) == 1:
            return k
    return ""


def _picked_one_tier(vars_map: dict[Tier, cp_model.IntVar], solver: cp_model.CpSolver) -> Tier:
    for k in TIERS:
        if solver.value(vars_map[k]) == 1:
            return k
    return "LOW"


def _assumption(data: CubeSatData, section: str, key: str) -> float:
    return float(data.assumptions[section][key]["value"])


def _compute_capacities(data: CubeSatData, sel: _Selection) -> dict[str, float]:
    """
    Capacities available to the selected (bus, tiers) combination, in plain float
    arithmetic, re-deriving the same formulas cubesat_constraint_injector.py uses as
    CP-SAT constraints - once the combination is fixed (post-solve), these are ordinary
    arithmetic, not a fresh optimization. Used for margin/headroom reporting; not fed
    back into the solver.
    """
    bus = data.bus_library[sel.bus_class]
    eps = data.eps_library[sel.eps_tier]

    f_sun = _assumption(data, "power_assumptions", "sunlight_fraction")
    f_ecl = _assumption(data, "power_assumptions", "eclipse_fraction")
    eta_eps = _assumption(data, "power_assumptions", "eps_efficiency")
    k_deg = _assumption(data, "power_assumptions", "solar_degradation_factor_eol")
    DoD_lim = _assumption(data, "battery_assumptions", "battery_dod_limit")
    eta_batt = _assumption(data, "battery_assumptions", "battery_round_trip_efficiency")
    k_batt = _assumption(data, "battery_assumptions", "battery_capacity_derating_factor")
    Pdens_sunlit = _assumption(data, "solar_generation_assumptions", "Pdens_sunlit_W_per_m2")
    T_orbit_hr = _assumption(data, "orbit_assumptions", "nominal_orbit_period_hr")
    U_over_u = _assumption(data, "volume_margin_assumptions", "payload_volume_overhead_u")

    def _pavg_cap_from_batt_wh(c_wh: float) -> float:
        return (c_wh * eta_eps * DoD_lim * k_batt * eta_batt) / (f_ecl * T_orbit_hr)

    eps_solar_cap_w = float(eps["max_solar_generation_w"]) * eta_eps * k_deg * f_sun
    bus_area_m2 = float(bus["available_body_solar_area_m2"]) + float(
        bus["deployable_panel_option_area_m2"]
    )
    bus_area_cap_w = (Pdens_sunlit * bus_area_m2) * eta_eps * k_deg * f_sun
    eps_batt_cap_w = _pavg_cap_from_batt_wh(float(eps["max_battery_capacity_wh"]))
    bus_batt_cap_w = _pavg_cap_from_batt_wh(float(bus["battery_packaging_limit_wh"]))
    P_avg_cap_w = min(eps_solar_cap_w, bus_area_cap_w, eps_batt_cap_w, bus_batt_cap_w)

    P_peak_cap_w = float(eps["max_peak_bus_power_w"])

    U_sub_u = (
        float(data.eps_library[sel.eps_tier]["eps_volume_u"])
        + float(data.adcs_library[sel.adcs_tier]["adcs_volume_u"])
        + float(data.comms_library[sel.comms_tier]["comms_volume_u"])
        + float(data.obc_library[sel.obc_tier]["obc_volume_u"])
        + float(data.thermal_library[sel.thermal_tier]["thermal_volume_u"])
        + float(data.propulsion_library[sel.prop_tier]["propellant_volume_u"])
    )
    U_payload_avail_u = (
        float(bus["usable_internal_volume_u"]) - U_over_u - (F_PACK_VOLUME * U_sub_u)
    )

    return {
        "M_dry_max_kg": float(bus["max_recommended_dry_mass_kg"]),
        "U_payload_avail_u": U_payload_avail_u,
        "P_avg_cap_w": P_avg_cap_w,
        "P_peak_cap_w": P_peak_cap_w,
    }


def format_solution(
    sm: CubeSatModel,
    data: CubeSatData,
    objective: ObjectiveCoefficients,
    solver: cp_model.CpSolver,
    status: int,
) -> dict[str, Any]:
    status_name = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }.get(status, str(status))

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # No feasible assignment exists: solver variables hold no meaningful values.
        # Do not read them (they previously surfaced as e.g. 2.1 GW of "peak power").
        return {
            "status": status_name,
            "objective_value": None,
            "selection": None,
            "payload_metadata": None,
            "totals": None,
            "solver_stats": {
                "wall_time_s": solver.wall_time,
                "num_conflicts": solver.num_conflicts,
                "num_branches": solver.num_branches,
            },
            "objective_weights": objective.weights_percent,
        }

    v = sm.vars

    payload_id = _picked_one(v.x_payload, solver)
    bus_class = _picked_one(v.b_bus, solver)
    eps_tier = _picked_one_tier(v.e_eps, solver)
    adcs_tier = _picked_one_tier(v.a_adcs, solver)
    comms_tier = _picked_one_tier(v.c_comms, solver)
    obc_tier = _picked_one_tier(v.o_obc, solver)
    thermal_tier = _picked_one_tier(v.t_thermal, solver)
    prop_tier = _picked_one_tier(v.p_prop, solver)

    sel = _Selection(
        payload_id=payload_id,
        bus_class=bus_class,
        eps_tier=eps_tier,
        adcs_tier=adcs_tier,
        comms_tier=comms_tier,
        obc_tier=obc_tier,
        thermal_tier=thermal_tier,
        prop_tier=prop_tier,
    )

    record = data.payloads.get(payload_id)
    payload_meta: dict[str, Any] = {}
    if record:
        payload_meta = {
            "mission_family": record.mission_family,
            "payload_group": record.payload_group,
            "payload_type": record.payload_type,
            "payload_variant": record.payload_variant,
            "vendor": record.product.get("vendor"),
            "product_name": record.product.get("product_name"),
        }

    result: dict[str, Any] = {
        "status": status_name,
        "objective_value": float(solver.objective_value),
        "selection": asdict(sel),
        "payload_metadata": payload_meta,
        "totals": {
            "M_total_kg": solver.value(v.M_total_g) / 1000.0,
            "P_avg_total_w": solver.value(v.P_avg_total_mw) / 1000.0,
            "P_peak_total_w": solver.value(v.P_peak_total_mw) / 1000.0,
            "U_total_u": solver.value(v.U_total_mU) / 1000.0,
            "Cost_total_usd_proxy": solver.value(v.Cost_total),
            "Risk_total_points": solver.value(v.Risk_total),
            "BusOversize_u": solver.value(v.BusOversize_mU) / 1000.0,
        },
        "capacities": _compute_capacities(data, sel),
        "solver_stats": {
            "wall_time_s": solver.wall_time,
            "num_conflicts": solver.num_conflicts,
            "num_branches": solver.num_branches,
        },
        "objective_weights": objective.weights_percent,
    }
    return result

