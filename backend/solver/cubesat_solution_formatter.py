from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ortools.sat.python import cp_model

from .cubesat_cp_model_builder import BUS_CLASSES, TIERS, CubeSatModel, Tier
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
        "solver_stats": {
            "wall_time_s": solver.wall_time,
            "num_conflicts": solver.num_conflicts,
            "num_branches": solver.num_branches,
        },
        "objective_weights": objective.weights_percent,
    }
    return result

