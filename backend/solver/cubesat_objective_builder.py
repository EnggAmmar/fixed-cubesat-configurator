from __future__ import annotations

from ortools.sat.python import cp_model

from .cubesat_cp_model_builder import BUS_CLASSES, TIERS, CubeSatModel
from .cubesat_data_loader import CubeSatData
from .cubesat_precompute_loader import ObjectiveCoefficients


def _define_cost_and_risk_totals(
    sm: CubeSatModel,
    data: CubeSatData,
    objective: ObjectiveCoefficients,
) -> None:
    model = sm.model
    v = sm.vars

    cost = objective.cost_proxy_tables
    risk = objective.risk_proxy_tables

    bus_cost = cost["bus_class_cost_usd_proxy"]
    eps_cost = cost["eps_tier_cost_usd_proxy"]
    adcs_cost = cost["adcs_tier_cost_usd_proxy"]
    comms_cost = cost["comms_tier_cost_usd_proxy"]
    obc_cost = cost["obc_tier_cost_usd_proxy"]
    therm_cost = cost["thermal_tier_cost_usd_proxy"]
    prop_cost = cost["propulsion_tier_cost_usd_proxy"]

    payload_risk_pts = risk["payload_integration_risk_points"]
    eps_risk = risk["eps_tier_risk_points"]
    adcs_risk = risk["adcs_tier_risk_points"]
    comms_risk = risk["comms_tier_risk_points"]
    obc_risk = risk["obc_tier_risk_points"]
    therm_risk = risk["thermal_tier_risk_points"]
    prop_risk = risk["propulsion_tier_risk_points"]

    payload_risk_sel = sum(
        v.x_payload[pid]
        * int(
            payload_risk_pts[
                str(data.payloads[pid].product.get("integration_risk") or "medium")
            ]
        )
        for pid in data.payloads
    )

    cost_expr = (
        sum(v.b_bus[u] * int(bus_cost[u]) for u in BUS_CLASSES)
        + sum(v.e_eps[k] * int(eps_cost[k]) for k in TIERS)
        + sum(v.a_adcs[k] * int(adcs_cost[k]) for k in TIERS)
        + sum(v.c_comms[k] * int(comms_cost[k]) for k in TIERS)
        + sum(v.o_obc[k] * int(obc_cost[k]) for k in TIERS)
        + sum(v.t_thermal[k] * int(therm_cost[k]) for k in TIERS)
        + sum(v.p_prop[k] * int(prop_cost[k]) for k in TIERS)
    )
    model.add(v.Cost_total == cost_expr)

    risk_expr = (
        payload_risk_sel
        + sum(v.e_eps[k] * int(eps_risk[k]) for k in TIERS)
        + sum(v.a_adcs[k] * int(adcs_risk[k]) for k in TIERS)
        + sum(v.c_comms[k] * int(comms_risk[k]) for k in TIERS)
        + sum(v.o_obc[k] * int(obc_risk[k]) for k in TIERS)
        + sum(v.t_thermal[k] * int(therm_risk[k]) for k in TIERS)
        + sum(v.p_prop[k] * int(prop_risk[k]) for k in TIERS)
        + v.IntegrationBurdenRisk_total
    )
    model.add(v.Risk_total == risk_expr)


def attach_objective(sm: CubeSatModel, data: CubeSatData, objective: ObjectiveCoefficients) -> None:
    model = sm.model
    v = sm.vars

    _define_cost_and_risk_totals(sm, data, objective)

    coeffs = objective.integer_objective.get("linear_objective_coefficients", {})
    if not isinstance(coeffs, dict):
        raise ValueError("objective_function_coefficients: missing linear_objective_coefficients")

    k_mass = int(coeffs["k_mass_per_g"])
    k_power = int(coeffs["k_power_per_mw"])
    k_cost = int(coeffs["k_cost_per_usd_proxy"])
    k_risk = int(coeffs["k_risk_per_point"])
    k_oversize = int(coeffs["k_oversize_per_mU"])

    Z = (
        k_mass * v.M_total_g
        + k_power * v.P_avg_total_mw
        + k_cost * v.Cost_total
        + k_risk * v.Risk_total
        + k_oversize * v.BusOversize_mU
    )
    model.minimize(Z)
