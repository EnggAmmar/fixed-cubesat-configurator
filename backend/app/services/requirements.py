from __future__ import annotations

from app.schemas.mission import DerivedRequirements, MissionInput, ThermalClass
from app.services.catalog import Catalog
from app.services.payload_resolver import resolve_payload_for_requirements


def _volume_cm3(length_mm: float, width_mm: float, height_mm: float) -> float:
    return (length_mm * width_mm * height_mm) / 1000.0


def derive_requirements(mission_input: MissionInput, catalog: Catalog) -> DerivedRequirements:
    payload = mission_input.payload

    if payload.type == "catalog":
        p = resolve_payload_for_requirements(payload.payload_id, catalog)
        if not p:
            raise ValueError(f"Unknown payload_id: {payload.payload_id}")
        thermal = (
            ThermalClass(p.thermal_class)
            if p.thermal_class in ThermalClass._value2member_map_
            else ThermalClass.standard
        )
        return DerivedRequirements(
            payload_mass_kg=p.mass_kg,
            payload_volume_cm3=_volume_cm3(p.length_mm, p.width_mm, p.height_mm),
            payload_avg_power_w=p.avg_power_w,
            payload_peak_power_w=p.peak_power_w,
            min_downlink_mbps=p.data_rate_mbps,
            max_pointing_error_deg=p.pointing_accuracy_deg,
            thermal_class=thermal,
        )

    thermal = payload.thermal_class or ThermalClass.standard
    return DerivedRequirements(
        payload_mass_kg=payload.mass_kg,
        payload_volume_cm3=_volume_cm3(payload.length_mm, payload.width_mm, payload.height_mm),
        payload_avg_power_w=payload.avg_power_w,
        payload_peak_power_w=payload.peak_power_w,
        min_downlink_mbps=payload.data_rate_mbps,
        max_pointing_error_deg=payload.pointing_accuracy_deg,
        thermal_class=thermal,
    )
