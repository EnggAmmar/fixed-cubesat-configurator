from __future__ import annotations

import re
from typing import Any

from app.schemas.mission import (
    DownlinkRatePreference,
    MissionInput,
    OptimizationPriority,
    PointingPrecisionPreference,
    PropulsionPreference,
)
from app.schemas.requirement_derivation import OptionalUserConstraints

DOWNLINK_PREFERENCE_MBPS = {
    DownlinkRatePreference.low: 5.0,
    DownlinkRatePreference.medium: 50.0,
    DownlinkRatePreference.high: 120.0,
    DownlinkRatePreference.optical_extreme: 3000.0,
}

POINTING_PREFERENCE_DEG = {
    PointingPrecisionPreference.coarse: 5.0,
    PointingPrecisionPreference.medium: 1.0,
    PointingPrecisionPreference.fine: 0.1,
    PointingPrecisionPreference.ultra_fine: 0.01,
}


def _add(
    applications: list[dict[str, Any]],
    preference: str,
    value: object,
    status: str,
    effect: str,
) -> None:
    applications.append(
        {
            "preference": preference,
            "value": value,
            "status": status,
            "effect": effect,
        }
    )


def optional_constraints_from_engineering_preferences(
    mission_input: MissionInput,
) -> tuple[OptionalUserConstraints | None, list[dict[str, Any]]]:
    prefs = mission_input.parameters.engineering_preferences
    if prefs is None:
        return None, []

    applications: list[dict[str, Any]] = []
    constraints = OptionalUserConstraints()

    if prefs.max_budget_usd is not None:
        constraints.cost_cap_kusd = float(prefs.max_budget_usd) / 1000.0
        _add(
            applications,
            "max_budget_usd",
            prefs.max_budget_usd,
            "applied_hard_constraint",
            f"total_cost_kusd <= {constraints.cost_cap_kusd:g}",
        )

    if prefs.max_bus_u is not None:
        constraints.max_bus_size_u = float(prefs.max_bus_u)
        _add(
            applications,
            "max_bus_u",
            prefs.max_bus_u,
            "applied_hard_constraint",
            f"selected bus_size_u <= {constraints.max_bus_size_u:g}",
        )

    downlink = prefs.downlink_rate_preference
    if downlink is None or downlink == DownlinkRatePreference.no_preference:
        _add(
            applications,
            "downlink_rate_preference",
            downlink.value if downlink else None,
            "ignored_no_preference",
            "payload-derived downlink requirement is unchanged",
        )
    else:
        threshold = DOWNLINK_PREFERENCE_MBPS[downlink]
        constraints.min_downlink_mbps = threshold
        _add(
            applications,
            "downlink_rate_preference",
            downlink.value,
            "applied_requirement_tightener",
            f"required downlink is max(payload requirement, {threshold:g} Mbps)",
        )

    pointing = prefs.pointing_precision_preference
    if pointing is None or pointing == PointingPrecisionPreference.no_preference:
        _add(
            applications,
            "pointing_precision_preference",
            pointing.value if pointing else None,
            "ignored_no_preference",
            "payload-derived pointing requirement is unchanged",
        )
    else:
        threshold = POINTING_PREFERENCE_DEG[pointing]
        constraints.max_pointing_error_deg = threshold
        _add(
            applications,
            "pointing_precision_preference",
            pointing.value,
            "applied_requirement_tightener",
            f"required pointing error is min(payload requirement, {threshold:g} deg)",
        )

    propulsion = prefs.propulsion_preference
    if propulsion is None or propulsion == PropulsionPreference.no_preference:
        _add(
            applications,
            "propulsion_preference",
            propulsion.value if propulsion else None,
            "ignored_no_preference",
            "propulsion selection is left to mission requirements/objective",
        )
    elif propulsion == PropulsionPreference.none:
        constraints.preferred_propulsion = "none"
        _add(
            applications,
            "propulsion_preference",
            propulsion.value,
            "applied_hard_constraint",
            "selected propulsion metadata type must be none unless mission requirements conflict",
        )
    else:
        constraints.preferred_propulsion = propulsion.value
        _add(
            applications,
            "propulsion_preference",
            propulsion.value,
            "applied_hard_constraint",
            f"selected propulsion metadata type must be {propulsion.value}",
        )

    priority = prefs.optimization_priority or OptimizationPriority.balanced
    constraints.optimization_priority = priority.value
    _add(
        applications,
        "optimization_priority",
        priority.value,
        "applied_objective_modifier",
        "objective weights adjusted for requested priority",
    )

    if prefs.altitude_km is not None:
        altitude = int(round(float(prefs.altitude_km)))
        constraints.altitude_band_km = (altitude, altitude)
        _add(
            applications,
            "altitude_km",
            prefs.altitude_km,
            "applied_orbit_assumption",
            f"altitude noted as fixed display/orbit assumption at {altitude:g} km",
        )

    if prefs.orbit_type is not None:
        _add(
            applications,
            "orbit_type",
            prefs.orbit_type.value,
            "applied_orbit_assumption",
            "orbit type is passed into derivation/trace where current v1 models support it",
        )

    if prefs.lifetime_years is not None:
        _add(
            applications,
            "lifetime_years",
            prefs.lifetime_years,
            "applied_risk_assumption",
            "lifetime is available for downstream risk/radiation heuristics",
        )

    return constraints, applications


def objective_weights_from_trace(trace: list[str]) -> dict[str, float] | None:
    for line in trace:
        if not line.startswith("Objective weights:"):
            continue
        pairs = re.findall(r"([a-z_]+)=([0-9.]+)", line)
        return {key: float(value) for key, value in pairs}
    return None


def objective_value_from_trace(trace: list[str]) -> float | None:
    for line in trace:
        if not line.startswith("Objective value:"):
            continue
        try:
            return float(line.split(":", 1)[1].strip().rstrip("."))
        except ValueError:
            return None
    return None
