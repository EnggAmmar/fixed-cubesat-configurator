from __future__ import annotations

import math
from typing import Any, Iterable

from ortools.sat.python import cp_model

from .cubesat_constraint_injector import (
    F_MASS_RESERVE,
    F_PACK_VOLUME,
    F_RAD_UTIL,
    burden_risk_pts,
    inject_constraints,
)
from .cubesat_cp_model_builder import BUS_CLASSES, TIERS, build_cp_model
from .cubesat_data_loader import load_all_data
from .cubesat_objective_builder import attach_objective
from .cubesat_precompute_loader import load_all_precompute
from .cubesat_solution_formatter import format_solution


def _apply_solver_parameters(s: cp_model.CpSolver) -> None:
    # Practical industrial defaults for CP-SAT.
    s.parameters.max_time_in_seconds = 10.0
    s.parameters.num_search_workers = 8
    s.parameters.log_search_progress = False


def _apply_solver_parameters_diagnostic(s: cp_model.CpSolver) -> None:
    # Deterministic diagnostics: 1 worker, stable seed.
    s.parameters.max_time_in_seconds = 5.0
    s.parameters.num_search_workers = 1
    s.parameters.random_seed = 0
    s.parameters.log_search_progress = False


def run_cubesat_solver(selected_payload_id: str) -> dict[str, Any]:
    data = load_all_data()
    pre = load_all_precompute()

    payload_ids = sorted(data.payloads.keys())
    sm = build_cp_model(payload_ids)

    inject_constraints(sm, data, pre.payload_precompute, selected_payload_id)

    attach_objective(sm, data, pre.objective)

    solver = cp_model.CpSolver()
    _apply_solver_parameters(solver)
    status = solver.solve(sm.model)

    return format_solution(sm, data, pre.objective, solver, status)


def run_family_solver(selected_payload_id: str, top_n: int = 5) -> dict[str, Any]:
    if top_n <= 0:
        raise ValueError("top_n must be >= 1")

    data = load_all_data()
    pre = load_all_precompute()
    payload_ids = sorted(data.payloads.keys())

    solutions: list[dict[str, Any]] = []
    no_goods: list[tuple[str, str, str, str, str, str, str]] = []

    for _ in range(top_n):
        sm = build_cp_model(payload_ids)
        inject_constraints(sm, data, pre.payload_precompute, selected_payload_id)
        attach_objective(sm, data, pre.objective)

        # Forbid previously found exact architecture tuples (bus + tier selections).
        for (bus, eps, adcs, comms, obc, therm, prop) in no_goods:
            sm.model.add_bool_or(
                [
                    sm.vars.b_bus[bus].Not(),
                    sm.vars.e_eps[eps].Not(),
                    sm.vars.a_adcs[adcs].Not(),
                    sm.vars.c_comms[comms].Not(),
                    sm.vars.o_obc[obc].Not(),
                    sm.vars.t_thermal[therm].Not(),
                    sm.vars.p_prop[prop].Not(),
                ]
            )

        solver = cp_model.CpSolver()
        _apply_solver_parameters(solver)
        status = solver.solve(sm.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break

        sol = format_solution(sm, data, pre.objective, solver, status)
        solutions.append(sol)

        sel = sol["selection"]
        no_goods.append(
            (
                str(sel["bus_class"]),
                str(sel["eps_tier"]),
                str(sel["adcs_tier"]),
                str(sel["comms_tier"]),
                str(sel["obc_tier"]),
                str(sel["thermal_tier"]),
                str(sel["prop_tier"]),
            )
        )

    return {
        "payload_id": selected_payload_id,
        "solutions_found": len(solutions),
        "solutions": solutions,
    }


def run_cubesat_diagnostic(selected_payload_id: str) -> dict[str, Any]:
    """
    Diagnostic mode: probe feasibility bus-by-bus.

    For each bus class:
    - force bus selection
    - solve CP-SAT for best tiers
    - if infeasible, run deterministic closure evaluation via enumeration (outside CP-SAT)
    """
    data = load_all_data()
    pre = load_all_precompute()

    if selected_payload_id not in data.payloads:
        raise ValueError(f"Unknown selected_payload_id: {selected_payload_id}")
    if selected_payload_id not in pre.payload_precompute.payloads:
        raise ValueError(f"Missing precompute for payload_id: {selected_payload_id}")

    payload_prod = data.payloads[selected_payload_id].product
    payload_pre = pre.payload_precompute.payloads[selected_payload_id]["precompute"]

    # Assumptions used (match constraint injector)
    ass = data.assumptions

    def _ass(section: str, key: str) -> float:
        return float(ass[section][key]["value"])

    f_sun = _ass("power_assumptions", "sunlight_fraction")
    f_ecl = _ass("power_assumptions", "eclipse_fraction")
    eta_eps = _ass("power_assumptions", "eps_efficiency")
    k_deg = _ass("power_assumptions", "solar_degradation_factor_eol")
    M_pow = _ass("power_assumptions", "power_margin_factor")
    M_peak = _ass("power_assumptions", "peak_power_headroom_factor")

    DoD_lim = _ass("battery_assumptions", "battery_dod_limit")
    eta_batt = _ass("battery_assumptions", "battery_round_trip_efficiency")
    k_batt = _ass("battery_assumptions", "battery_capacity_derating_factor")

    M_mass = _ass("mass_margin_assumptions", "mass_growth_margin")
    f_fill = _ass("volume_margin_assumptions", "volume_fill_limit")
    U_over_u = _ass("volume_margin_assumptions", "payload_volume_overhead_u")
    M_data = _ass("data_storage_assumptions", "daily_data_contingency_margin")

    eta_dl = _ass("downlink_assumptions", "downlink_efficiency_factor")
    T_contact_day_min = _ass("downlink_assumptions", "nominal_contact_minutes_per_day")
    f_contact_use = _ass("downlink_assumptions", "usable_contact_fraction")

    f_heat_int = _ass("thermal_assumptions", "internal_heat_fraction_default")
    M_th = _ass("thermal_assumptions", "thermal_margin_factor")

    Pdens_sunlit = _ass("solar_generation_assumptions", "Pdens_sunlit_W_per_m2")
    T_orbit_hr = _ass("orbit_assumptions", "nominal_orbit_period_hr")

    # Helpers for ordinals
    ord_class = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EXTREME": 4}
    ord_cg = {"low": 1, "medium": 2, "high": 3}

    def _bus_ord(u: str) -> int:
        return {b: i + 1 for i, b in enumerate(BUS_CLASSES)}[u]

    def _tier_ord(k: str) -> int:
        return ord_class[k]

    # Pull numeric payload fields.
    def _f(key: str, default: float = 0.0) -> float:
        v = payload_prod.get(key, default)
        if v is None:
            return default
        return float(v)

    payload_mass_kg = _f("mass_kg")
    payload_env_u = _f("payload_envelope_u")
    payload_avg_w = _f("avg_power_w")
    payload_nominal_mbps = _f("nominal_data_rate_mbps")
    payload_point_req_deg = _f("pointing_requirement_deg", 999.0)
    payload_cg = str(payload_prod.get("cg_sensitivity_class") or "low")

    # Precomputed scalars (Prompt 11/12.5)
    P_peak_eff_w = float(payload_pre["P_payload_peak_eff_w"])
    S_req_gb = float(payload_pre["S_req_gb"])
    R_ing_req_mbps = float(payload_pre["R_ing_req_mbps"])
    Q_payload_req_w = float(payload_pre["Q_payload_req_w"])
    fine_point = int(payload_pre["fine_point"])
    ultra_fine = int(payload_pre["ultra_fine"])
    extreme_data = int(payload_pre["extreme_data"])
    high_thermal = int(payload_pre["high_thermal"])
    DV_req_mps = float(payload_pre["DV_req_mps"])

    # Compatibility ordinals
    ord_req_eps = int(payload_pre["ord_req_eps"])
    ord_req_adcs = int(payload_pre["ord_req_adcs"])
    ord_req_comms = int(payload_pre["ord_req_comms"])
    ord_req_obc = int(payload_pre["ord_req_obc"])
    ord_req_therm = int(payload_pre["ord_req_therm"])
    ord_req_struct = int(payload_pre["ord_req_struct"])
    ord_req_prop = int(payload_pre["ord_req_prop"])

    # Semantic propagation burdens (Prompt 12.5)
    ord_rad = int(payload_pre["ord_rad"])
    ord_vibe = int(payload_pre["ord_vibe"])
    ord_emi = int(payload_pre["ord_emi"])
    ord_contam = int(payload_pre["ord_contam"])
    ord_deploy = int(payload_pre["ord_deploy"])
    ord_harness = int(payload_pre["ord_harness"])

    def _eval_case(bus: str, tiers: dict[str, str]) -> tuple[list[str], dict[str, float]]:
        """
        Deterministic closure evaluator using the same constants/logic as the CP-SAT model.

        Returns: (violated_families, margins dict)
        """
        eps = tiers["eps"]
        adcs = tiers["adcs"]
        comms = tiers["comms"]
        obc = tiers["obc"]
        therm = tiers["thermal"]
        prop = tiers["prop"]

        fails: list[str] = []

        # --- Supported-bus legality (treated as forbidden) ---
        def _supported(lib: dict[str, Any], key: str) -> bool:
            # Lower bound only - no supported_bus_max cutoff (see
            # cubesat_constraint_injector.py's supported-bus-range comments).
            min_u = str(lib[key]["supported_bus_min"])
            return _bus_ord(min_u) <= _bus_ord(bus)

        if not _supported(data.eps_library, eps):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if not _supported(data.adcs_library, adcs):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if not _supported(data.comms_library, comms):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if not _supported(data.obc_library, obc):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if not _supported(data.thermal_library, therm):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if not _supported(data.propulsion_library, prop):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # Bus-specific no-goods.
        if bus in ("1U", "1.5U", "2U") and eps == "EXTREME":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if bus in ("1U", "1.5U", "2U") and prop == "EXTREME":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if bus == "1U" and comms in ("HIGH", "EXTREME"):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # Pointing-driven no-goods.
        if fine_point and adcs == "LOW":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if ultra_fine and adcs == "MEDIUM":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # Data-driven no-goods.
        if extreme_data and comms == "LOW":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if extreme_data and obc == "LOW":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # Thermal burden no-good.
        if high_thermal and therm == "LOW":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # COMMS-ADCS coupling no-goods.
        if comms == "EXTREME" and adcs in ("LOW", "MEDIUM"):
            fails.append("FORBIDDEN_NO_GOOD_FAIL")
        if comms == "HIGH" and adcs == "LOW":
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # COMMS pointing dependency ordinal.
        ord_point_dep = ord_class[str(data.comms_library[comms]["pointing_dependency"])]
        if _tier_ord(adcs) < ord_point_dep:
            fails.append("FORBIDDEN_NO_GOOD_FAIL")

        # --- Compatibility/ordinal minimum constraints ---
        # EPS / ADCS required
        if _tier_ord(eps) < ord_req_eps:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")
        if _tier_ord(adcs) < ord_req_adcs:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")

        # Structural ruggedization: bus stiffness >= required structure class.
        # (radiation/vibration/deployment burdens are integration-burden risk inputs,
        # not a hard floor here — see _BURDEN_RISK_PTS in cubesat_constraint_injector.py)
        bus_stiff = ord_class[str(data.bus_library[bus]["structural_stiffness_class"])]
        if bus_stiff < ord_req_struct:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")

        # Comms / OBC tier >= required capability class.
        # (EMI/harness burdens are integration-burden risk inputs, not a hard floor here)
        if _tier_ord(comms) < ord_req_comms:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")
        if _tier_ord(obc) < ord_req_obc:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")

        # Thermal tier >= required capability class.
        # (contamination cleanliness is an integration-burden risk input, not a hard floor here)
        if _tier_ord(therm) < ord_req_therm:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")

        # Prop tier >= required capability class.
        # (deployment burden is an integration-burden risk input, not a hard floor here)
        if _tier_ord(prop) < ord_req_prop:
            fails.append("COMPATIBILITY_ORDINAL_FAIL")

        # --- ADCS pointing feasibility ---
        cap_deg = float(data.adcs_library[adcs]["pointing_accuracy_deg"])
        pointing_margin_deg = payload_point_req_deg - cap_deg
        if pointing_margin_deg < 0:
            fails.append("ADCS_POINTING_FAIL")

        # --- COMMS feasibility (nominal + daily) ---
        comms_cap_mbps = float(data.comms_library[comms]["nominal_supported_downlink_mbps"])
        downlink_margin_mbps = comms_cap_mbps - payload_nominal_mbps
        if downlink_margin_mbps < 0:
            fails.append("COMMS_DOWNLINK_FAIL")

        # Daily downlink closure (MB/day)
        T_eff_day = T_contact_day_min * f_contact_use
        daily_cap_gb = comms_cap_mbps * eta_dl * T_eff_day * 60.0 / (8.0 * 1000.0)
        daily_req_gb = M_data * float(payload_prod.get("daily_data_generation_gb") or 0.0)
        daily_data_margin_gb = daily_cap_gb - daily_req_gb
        if daily_data_margin_gb < 0:
            fails.append("COMMS_DOWNLINK_FAIL")

        # --- OBC feasibility ---
        obc_store_gb = float(data.obc_library[obc]["max_storage_gb"])
        storage_margin_gb = obc_store_gb - S_req_gb
        if storage_margin_gb < 0:
            fails.append("OBC_STORAGE_FAIL")

        obc_ingest_mbps = float(data.obc_library[obc]["supported_ingest_mbps"])
        ingest_margin_mbps = obc_ingest_mbps - R_ing_req_mbps
        if ingest_margin_mbps < 0:
            fails.append("OBC_INGEST_FAIL")

        # --- Volume closure ---
        U_bus = float(data.bus_library[bus]["u_bus"])
        U_usable = float(data.bus_library[bus]["usable_internal_volume_u"])
        U_sub = (
            float(data.eps_library[eps]["eps_volume_u"])
            + float(data.adcs_library[adcs]["adcs_volume_u"])
            + float(data.comms_library[comms]["comms_volume_u"])
            + float(data.obc_library[obc]["obc_volume_u"])
            + float(data.thermal_library[therm]["thermal_volume_u"])
            + float(data.propulsion_library[prop]["propellant_volume_u"])
        )

        # Prompt 12.9 calibration: apply packaging concurrency factor to subsystem volumes only.
        # Do not reduce payload envelope or harness reserve.
        U_sub_eff = math.ceil((F_PACK_VOLUME * U_sub) * 1000.0 - 1e-12) / 1000.0
        U_total = payload_env_u + U_over_u + U_sub_eff
        volume_margin_u = U_usable - U_total
        fill_margin_u = (f_fill * U_bus) - U_total
        if volume_margin_u < 0 or fill_margin_u < 0:
            fails.append("VOLUME_CLOSURE_FAIL")

        # Also enforce payload recommended bus minimum U as part of bus feasibility.
        bus_min_u_hint = float(payload_prod.get("recommended_bus_min_u") or 0.0)
        if U_bus < bus_min_u_hint:
            fails.append("VOLUME_CLOSURE_FAIL")

        # --- Mass closure ---
        M_dry_max = float(data.bus_library[bus]["max_recommended_dry_mass_kg"])
        m_bus_struct = float(data.bus_library[bus]["bus_structure_mass_kg"])
        m_sub = (
            float(data.eps_library[eps]["eps_mass_kg"])
            + float(data.adcs_library[adcs]["adcs_mass_kg"])
            + float(data.comms_library[comms]["comms_mass_kg"])
            + float(data.obc_library[obc]["obc_mass_kg"])
            + float(data.thermal_library[therm]["thermal_mass_kg"])
            + float(data.propulsion_library[prop]["prop_mass_kg"])
        )
        # Prompt 12.9 calibration: reduce reserve conservatism only for non-payload reserve adders.
        # Payload and subsystem masses remain unchanged.
        M_total = (1.0 + M_mass) * (payload_mass_kg + m_sub) + (1.0 + (F_MASS_RESERVE * M_mass)) * m_bus_struct
        mass_margin_kg = M_dry_max - M_total
        if mass_margin_kg < 0:
            fails.append("MASS_CLOSURE_FAIL")

        bus_min_mass_hint = float(payload_prod.get("recommended_bus_min_mass_kg") or 0.0)
        if M_dry_max < bus_min_mass_hint:
            fails.append("MASS_CLOSURE_FAIL")

        # --- EPS solar/battery feasibility (computed from P_avg_total) ---
        P_sub_avg = (
            float(data.eps_library[eps]["eps_avg_self_consumption_w"])
            + float(data.adcs_library[adcs]["adcs_avg_power_w"])
            + float(data.comms_library[comms]["tx_avg_power_w"])
            + float(data.obc_library[obc]["obc_avg_power_w"])
            + float(data.thermal_library[therm]["thermal_avg_power_w"])
            + float(data.propulsion_library[prop]["prop_avg_power_w"])
        )
        P_avg_total = M_pow * (payload_avg_w + P_sub_avg)

        P_solar_req = P_avg_total / (eta_eps * k_deg * f_sun)
        A_total = float(data.bus_library[bus]["available_body_solar_area_m2"]) + float(
            data.bus_library[bus]["deployable_panel_option_area_m2"]
        )
        P_solar_avail = min(
            float(data.eps_library[eps]["max_solar_generation_w"]),
            Pdens_sunlit * A_total,
        )
        solar_margin_w = P_solar_avail - P_solar_req
        if solar_margin_w < 0:
            fails.append("EPS_SOLAR_FAIL")

        E_ecl_Wh = (P_avg_total / eta_eps) * (f_ecl * T_orbit_hr)
        C_batt_req = E_ecl_Wh / (DoD_lim * k_batt * eta_batt)
        C_batt_avail = min(
            float(data.eps_library[eps]["max_battery_capacity_wh"]),
            float(data.bus_library[bus]["battery_packaging_limit_wh"]),
        )
        battery_margin_wh = C_batt_avail - C_batt_req
        if battery_margin_wh < 0:
            fails.append("EPS_BATTERY_FAIL")

        # --- Peak bus power ---
        P_sub_peak = (
            float(data.adcs_library[adcs]["adcs_peak_power_w"])
            + float(data.comms_library[comms]["tx_peak_power_w"])
            + float(data.obc_library[obc]["obc_peak_power_w"])
            + float(data.thermal_library[therm]["thermal_peak_power_w"])
            + float(data.propulsion_library[prop]["prop_peak_power_w"])
        )
        P_peak_total = M_peak * (P_peak_eff_w + P_sub_peak)
        P_peak_cap = float(data.eps_library[eps]["max_peak_bus_power_w"])
        peak_power_margin_w = P_peak_cap - P_peak_total
        if peak_power_margin_w < 0:
            fails.append("EPS_PEAK_POWER_FAIL")

        # --- Thermal rejection ---
        Q_sub_req = (M_th * f_heat_int) * P_sub_avg
        Q_req = Q_payload_req_w + Q_sub_req
        Q_tier_cap = float(data.thermal_library[therm]["max_heat_rejection_w"])
        q_density = float(data.thermal_library[therm]["q_reject_density_w_per_m2"])
        A_rad = float(data.bus_library[bus]["nominal_radiator_area_m2"])
        Q_bus_cap = q_density * A_rad * F_RAD_UTIL
        Q_cap = min(Q_tier_cap, Q_bus_cap)
        thermal_margin_w = Q_cap - Q_req
        if thermal_margin_w < 0:
            fails.append("THERMAL_REJECTION_FAIL")

        # --- Propulsion DV feasibility ---
        DV_cap = float(data.propulsion_library[prop]["delta_v_support_mps"])
        dv_margin_mps = DV_cap - DV_req_mps
        if dv_margin_mps < 0:
            fails.append("PROP_DELTAV_FAIL")

        margins = {
            "mass_margin_kg": round(mass_margin_kg, 6),
            "volume_margin_u": round(min(volume_margin_u, fill_margin_u), 6),
            "solar_margin_w": round(solar_margin_w, 6),
            "battery_margin_wh": round(battery_margin_wh, 6),
            "peak_power_margin_w": round(peak_power_margin_w, 6),
            "downlink_margin_mbps": round(downlink_margin_mbps, 6),
            "storage_margin_gb": round(storage_margin_gb, 6),
            "thermal_margin_w": round(thermal_margin_w, 6),
            "dv_margin_mps": round(dv_margin_mps, 6),
        }
        return sorted(set(fails)), margins

    def _diagnose_infeasible(bus: str) -> dict[str, Any]:
        # Enumerate tier combinations to identify irreducible failing families + margins.
        tier_options: list[list[str]] = [list(TIERS)] * 6
        keys = ["eps", "adcs", "comms", "obc", "thermal", "prop"]

        combos: list[tuple[dict[str, str], list[str], dict[str, float]]] = []
        for eps in TIERS:
            for adcs in TIERS:
                for comms in TIERS:
                    for obc in TIERS:
                        for therm in TIERS:
                            for prop in TIERS:
                                tiers = {
                                    "eps": eps,
                                    "adcs": adcs,
                                    "comms": comms,
                                    "obc": obc,
                                    "thermal": therm,
                                    "prop": prop,
                                }
                                fails, margins = _eval_case(bus, tiers)
                                combos.append((tiers, fails, margins))
                                if not fails:
                                    # If we find a fully-feasible combo, CP-SAT should have been feasible.
                                    return {
                                        "diagnostic_note": "FOUND_FEASIBLE_COMBO_OUTSIDE_CPSAT",
                                        "tiers": tiers,
                                        "violated_families": [],
                                        "margins": margins,
                                    }

        # Find minimum violation count
        min_v = min(len(f) for _, f, _ in combos)
        best = [(t, f, m) for (t, f, m) in combos if len(f) == min_v]

        # Choose representative "best effort" by minimizing total deficit magnitude across key margins.
        def _deficit_score(m: dict[str, float]) -> float:
            s = 0.0
            for k in (
                "mass_margin_kg",
                "volume_margin_u",
                "solar_margin_w",
                "battery_margin_wh",
                "peak_power_margin_w",
                "downlink_margin_mbps",
                "storage_margin_gb",
                "thermal_margin_w",
                "dv_margin_mps",
            ):
                v = float(m.get(k, 0.0))
                if v < 0:
                    s += (-v)
            return s

        rep = min(best, key=lambda x: _deficit_score(x[2]))

        # First-order families:
        # - If a non-empty intersection exists across all min-violation combos, those are irreducible blockers.
        # - If the intersection is empty (conflict-driven infeasibility), use the representative fail set.
        irr = set(best[0][1])
        for _, f, _ in best[1:]:
            irr.intersection_update(f)
        first_order_note = "intersection_across_min_violation_combos"
        if not irr:
            irr = set(rep[1])
            first_order_note = "conflict_driven; representative_fail_set"

        return {
            "min_violation_count": min_v,
            "representative_tiers": rep[0],
            "representative_fails": rep[1],
            "representative_margins": rep[2],
            "first_order_families": sorted(irr),
            "first_order_note": first_order_note,
        }

    bus_cases: list[dict[str, Any]] = []

    for bus in BUS_CLASSES:
        payload_ids = sorted(data.payloads.keys())
        sm = build_cp_model(payload_ids)
        inject_constraints(sm, data, pre.payload_precompute, selected_payload_id)

        # Force bus selection.
        for u, bv in sm.vars.b_bus.items():
            sm.model.add(bv == (1 if u == bus else 0))

        attach_objective(sm, data, pre.objective)

        solver = cp_model.CpSolver()
        _apply_solver_parameters_diagnostic(solver)
        status = solver.solve(sm.model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            sol = format_solution(sm, data, pre.objective, solver, status)
            tiers = {
                "eps": sol["selection"]["eps_tier"],
                "adcs": sol["selection"]["adcs_tier"],
                "comms": sol["selection"]["comms_tier"],
                "obc": sol["selection"]["obc_tier"],
                "thermal": sol["selection"]["thermal_tier"],
                "prop": sol["selection"]["prop_tier"],
            }
            fails, margins = _eval_case(bus, tiers)
            bus_cases.append(
                {
                    "bus_class": bus,
                    "status": "FEASIBLE",
                    "objective_value": sol["objective_value"],
                    "tiers": tiers,
                    "violated_families": fails,
                    "margins": margins,
                }
            )
        else:
            diag = _diagnose_infeasible(bus)
            bus_cases.append(
                {
                    "bus_class": bus,
                    "status": "INFEASIBLE",
                    "tiers": diag.get("representative_tiers"),
                    "objective_value": None,
                    "violated_families": diag.get("representative_fails", []),
                    "first_order_families": diag.get("first_order_families", []),
                    "margins": diag.get("representative_margins", {}),
                    "diagnostic_detail": {
                        "min_violation_count": diag.get("min_violation_count"),
                        "first_order_note": diag.get("first_order_note"),
                    },
                }
            )

    return {
        "payload_id": selected_payload_id,
        "payload_meta": {
            "vendor": payload_prod.get("vendor"),
            "product_name": payload_prod.get("product_name"),
            "recommended_bus_min_u": payload_prod.get("recommended_bus_min_u"),
            "recommended_bus_min_mass_kg": payload_prod.get("recommended_bus_min_mass_kg"),
        },
        "integration_burden": {
            # Ordinals (1=LOW..4=EXTREME) contribute additive risk points to the objective
            # instead of forcing subsystem tiers up; shown here for the same transparency
            # the rest of this diagnostic already gives every other closure.
            "ord_rad": ord_rad,
            "ord_vibe": ord_vibe,
            "ord_emi": ord_emi,
            "ord_contam": ord_contam,
            "ord_deploy": ord_deploy,
            "ord_harness": ord_harness,
            "risk_points_total": (
                burden_risk_pts(ord_rad)
                + burden_risk_pts(ord_vibe)
                + burden_risk_pts(ord_emi)
                + burden_risk_pts(ord_contam)
                + burden_risk_pts(ord_deploy)
                + burden_risk_pts(ord_harness)
            ),
        },
        "bus_cases": bus_cases,
    }
