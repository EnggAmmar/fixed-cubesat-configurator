from __future__ import annotations

import math

from app.schemas.mission import ConstellationEstimate, DerivedRequirements, MissionInput


def estimate_constellation(
    mission_input: MissionInput, requirements: DerivedRequirements
) -> ConstellationEstimate:
    revisit = mission_input.parameters.revisit_time_hours
    roi_multiplier = 2 if mission_input.roi.type == "global" else 1

    sats = max(1, math.ceil((24.0 / revisit) * roi_multiplier))
    planes = max(1, min(4, sats))
    sats_per_plane = math.ceil(sats / planes)

    if mission_input.family.value == "remote_sensing":
        orbit_type = "Sun-synchronous"
        altitude_km = 550
    elif mission_input.family.value == "iot_communication":
        orbit_type = "LEO"
        altitude_km = 600
    else:
        orbit_type = "MEO (approx.)"
        altitude_km = 20000

    prefs = mission_input.parameters.engineering_preferences
    if prefs is not None:
        if prefs.orbit_type is not None:
            orbit_type = prefs.orbit_type.value.replace("_", " ").upper()
        if prefs.altitude_km is not None:
            altitude_km = int(round(float(prefs.altitude_km)))

    notes = [
        "v1 uses an explainable approximation model (not high-fidelity propagation).",
        f"ROI mode: {mission_input.roi.type}. Revisit target: {revisit:g} h.",
    ]
    if prefs is not None and prefs.orbit_type is not None:
        notes.append(f"Engineering preference applied: orbit_type={prefs.orbit_type.value}.")
    if prefs is not None and prefs.altitude_km is not None:
        notes.append(f"Engineering preference applied: altitude_km={prefs.altitude_km:g}.")
    if prefs is not None and prefs.lifetime_years is not None:
        notes.append(f"Engineering preference noted: lifetime_years={prefs.lifetime_years:g}.")

    return ConstellationEstimate(
        orbit_type=orbit_type,
        altitude_km=altitude_km,
        satellites=sats,
        planes=planes,
        satellites_per_plane=sats_per_plane,
        notes=notes,
    )
