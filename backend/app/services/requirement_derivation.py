from __future__ import annotations

import math

from app.schemas.mission import MissionInput, ThermalClass
from app.schemas.requirement_derivation import (
    DerivedSubsystemRequirements,
    DownlinkClass,
    OptionalUserConstraints,
    OrbitFamily,
    ThermalMode,
)
from app.services.catalog import get_catalog
from app.services.payload_resolver import resolve_payload_for_requirements
from app.services.units import occupied_u_from_cm3, volume_cm3_from_mm

_STANDARD_BUS_SIZES_U = [1.0, 1.5, 2.0, 3.0, 6.0, 8.0, 12.0, 16.0]


def _snap_up_to_standard_u(required_u: float) -> float:
    for u in _STANDARD_BUS_SIZES_U:
        if u >= required_u:
            return u
    return _STANDARD_BUS_SIZES_U[-1]


def _downlink_class_from_mbps(value: float) -> DownlinkClass:
    if value < 5:
        return DownlinkClass.low
    if value < 50:
        return DownlinkClass.medium
    return DownlinkClass.high


def _downlink_class_from_threshold(value: float) -> DownlinkClass:
    return _downlink_class_from_mbps(value)


def _default_pointing_deg(family: str) -> float:
    if family == "remote_sensing":
        return 0.5
    if family == "iot_communication":
        return 5.0
    return 2.0


def _recommended_orbit_family(family: str) -> OrbitFamily:
    if family == "remote_sensing":
        return OrbitFamily.sun_synchronous_leo
    if family == "iot_communication":
        return OrbitFamily.leo
    return OrbitFamily.meo


def _thermal_mode(thermal_class: ThermalClass, payload_avg_power_w: float) -> ThermalMode:
    if thermal_class.value == "sensitive":
        return ThermalMode.enhanced
    if payload_avg_power_w >= 25:
        return ThermalMode.enhanced
    return ThermalMode.standard


def _estimate_storage_gb(
    family: str, revisit_h: float, downlink_class: DownlinkClass, mbps: float | None
) -> float:
    if mbps is not None:
        # Transparent heuristic:
        # assume average duty cycle (family-based) and buffer for 1 revisit interval.
        duty = (
            0.08 if family == "remote_sensing" else 0.02 if family == "iot_communication" else 0.01
        )
        seconds = revisit_h * 3600.0
        mbit = mbps * seconds * duty
        gb = (mbit / 8.0) / 1024.0  # MB -> GB (approx)
        return max(16.0, math.ceil(gb))

    # Fallback by class + revisit
    if family == "remote_sensing":
        if revisit_h <= 24:
            return 256.0 if downlink_class == DownlinkClass.high else 128.0
        if revisit_h <= 48:
            return 128.0
        return 64.0
    if family == "iot_communication":
        return 32.0 if downlink_class != DownlinkClass.low else 16.0
    return 16.0


def _bus_overheads(family: str) -> tuple[float, float, float]:
    # avg_power_overhead_w, peak_power_overhead_w, base_volume_overhead_u
    if family == "remote_sensing":
        return (18.0, 25.0, 1.2)
    if family == "iot_communication":
        return (12.0, 18.0, 1.0)
    return (14.0, 20.0, 1.0)


def derive_subsystem_requirements(
    mission_input: MissionInput,
    constraints: OptionalUserConstraints | None = None,
) -> DerivedSubsystemRequirements:
    trace: list[str] = []
    warnings: list[str] = []

    family = mission_input.family.value
    revisit_h = float(mission_input.parameters.revisit_time_hours)

    if mission_input.payload.type == "catalog":
        payload_id = mission_input.payload.payload_id
        catalog = get_catalog()
        p = resolve_payload_for_requirements(payload_id, catalog)
        if not p:
            raise ValueError(f"Unknown catalog payload_id: {payload_id}")

        payload_name = p.label
        payload_mass_kg = float(p.mass_kg)
        payload_avg_w = float(p.avg_power_w)
        payload_peak_w = float(p.peak_power_w)
        payload_vol_u = occupied_u_from_cm3(
            volume_cm3_from_mm(float(p.length_mm), float(p.width_mm), float(p.height_mm))
        )
        data_rate_mbps = p.data_rate_mbps
        pointing_accuracy_deg = p.pointing_accuracy_deg
        thermal_class = (
            ThermalClass(p.thermal_class)
            if p.thermal_class in ThermalClass._value2member_map_
            else ThermalClass.standard
        )
        trace.append(f"Payload input: catalog payload `{payload_id}` ({payload_name}).")
    else:
        p = mission_input.payload
        payload_name = p.name
        payload_mass_kg = float(p.mass_kg)
        payload_avg_w = float(p.avg_power_w)
        payload_peak_w = float(p.peak_power_w)
        vol_cm3 = volume_cm3_from_mm(float(p.length_mm), float(p.width_mm), float(p.height_mm))
        payload_vol_u = occupied_u_from_cm3(vol_cm3)
        data_rate_mbps = p.data_rate_mbps
        pointing_accuracy_deg = p.pointing_accuracy_deg
        thermal_class = p.thermal_class or ThermalClass.standard
        trace.append(f"Payload input: My Payload `{payload_name}`.")
        trace.append(f"Payload volume: {vol_cm3:g} cm^3 => {payload_vol_u:g} U (1U≈1000 cm^3).")
        if p.gpu_required_tops is not None:
            warnings.append("GPU/processing requirement captured but not yet used in derivation.")
        if p.storage_required_gb is not None:
            trace.append(
                f"My Payload includes storage_required_gb={float(p.storage_required_gb):g}."
            )

    avg_over, peak_over, vol_over_u = _bus_overheads(family)

    packing_factor = 1.6 if family == "remote_sensing" else 1.3
    required_bus_u = payload_vol_u * packing_factor + vol_over_u
    trace.append(
        "Bus volume rule: required_u = "
        f"payload_u({payload_vol_u:g}) * {packing_factor:g} + overhead({vol_over_u:g})."
    )
    recommended_bus_u = _snap_up_to_standard_u(required_bus_u)
    trace.append(f"Recommended standard bus size: {recommended_bus_u:g}U.")

    estimated_total_mass_budget_kg = max(1.0, payload_mass_kg * 1.25 + recommended_bus_u * 1.1)
    trace.append(
        "Mass budget rule: payload_mass*1.25 + recommended_bus_u*1.1 (transparent v1 heuristic)."
    )

    required_pointing_deg = (
        float(pointing_accuracy_deg)
        if pointing_accuracy_deg is not None
        else _default_pointing_deg(family)
    )
    if pointing_accuracy_deg is None:
        trace.append(
            f"Pointing rule: defaulted by family `{family}` to {required_pointing_deg:g} deg."
        )
    else:
        trace.append(
            f"Pointing rule: derived from payload requirement {required_pointing_deg:g} deg."
        )

    if data_rate_mbps is None:
        downlink_class = (
            DownlinkClass.high
            if family == "remote_sensing"
            else DownlinkClass.medium
            if family == "iot_communication"
            else DownlinkClass.low
        )
        trace.append(
            f"Downlink rule: no data rate provided; defaulted to `{downlink_class.value}`."
        )
        warnings.append("Data rate not provided; downlink class inferred from mission family.")
    else:
        downlink_class = _downlink_class_from_mbps(float(data_rate_mbps))
        trace.append(
            f"Downlink rule: data_rate={float(data_rate_mbps):g} Mbps => "
            f"`{downlink_class.value}` class."
        )
    required_downlink_mbps = float(data_rate_mbps) if data_rate_mbps is not None else None

    if constraints and constraints.min_downlink_mbps is not None:
        preference_mbps = float(constraints.min_downlink_mbps)
        if required_downlink_mbps is None or preference_mbps > required_downlink_mbps:
            required_downlink_mbps = preference_mbps
            trace.append(
                "Preference rule: min_downlink_mbps tightened required downlink to "
                f"{preference_mbps:g} Mbps."
            )
        else:
            trace.append(
                "Preference rule: min_downlink_mbps did not relax payload downlink "
                f"({preference_mbps:g} <= {required_downlink_mbps:g} Mbps)."
            )
        downlink_class = max(
            downlink_class,
            _downlink_class_from_threshold(preference_mbps),
            key=lambda cls: {"low": 0, "medium": 1, "high": 2}[cls.value],
        )

    if constraints and constraints.max_pointing_error_deg is not None:
        preference_pointing = float(constraints.max_pointing_error_deg)
        if preference_pointing < required_pointing_deg:
            required_pointing_deg = preference_pointing
            trace.append(
                "Preference rule: max_pointing_error_deg tightened pointing requirement to "
                f"{preference_pointing:g} deg."
            )
        else:
            trace.append(
                "Preference rule: max_pointing_error_deg did not relax payload pointing "
                f"({preference_pointing:g} >= {required_pointing_deg:g} deg)."
            )

    required_storage_gb = (
        float(mission_input.payload.storage_required_gb)
        if mission_input.payload.type == "my_payload"
        and mission_input.payload.storage_required_gb is not None
        else _estimate_storage_gb(family, revisit_h, downlink_class, data_rate_mbps)
    )
    if (
        mission_input.payload.type == "my_payload"
        and mission_input.payload.storage_required_gb is not None
    ):
        trace.append(f"Storage rule: user-provided storage_required_gb={required_storage_gb:g}.")
    else:
        trace.append(
            "Storage rule: estimated "
            f"required_storage_gb={required_storage_gb:g} "
            "(family/revisit/downlink heuristic)."
        )

    thermal_mode = _thermal_mode(thermal_class, payload_avg_w)
    trace.append(
        f"Thermal rule: thermal_class={thermal_class.value}, payload_avg_w={payload_avg_w:g} "
        f"=> `{thermal_mode.value}`."
    )

    required_eps_avg_gen_w = (payload_avg_w + avg_over) * 1.2
    trace.append(
        "EPS rule: avg_gen_w = "
        f"(payload_avg_w({payload_avg_w:g}) + overhead({avg_over:g})) * 1.2 margin."
    )

    # Battery heuristic assumes ~30 minutes operation at peak load with 30% margin.
    required_battery_wh = math.ceil((payload_peak_w + peak_over) * 0.5 * 1.3)
    trace.append(
        "Battery rule: Wh = (payload_peak + overhead_peak) * 0.5h * 1.3 margin "
        "(transparent v1 heuristic)."
    )

    orbit_family = _recommended_orbit_family(family)
    trace.append(f"Orbit rule: family `{family}` => `{orbit_family.value}`.")

    propulsion_recommended = orbit_family == OrbitFamily.meo
    if constraints and constraints.preferred_propulsion == "none":
        if propulsion_recommended:
            warnings.append(
                "Propulsion preference 'none' conflicts with mission-derived propulsion need."
            )
            trace.append(
                "Propulsion rule: preferred_propulsion='none' conflicts with "
                f"orbit_family={orbit_family.value} recommendation."
            )
        else:
            trace.append(
                "Propulsion rule: preferred_propulsion='none' keeps propulsion optional/none."
            )
    elif constraints and constraints.preferred_propulsion:
        propulsion_recommended = True
        trace.append(
            f"Propulsion rule: preferred_propulsion='{constraints.preferred_propulsion}' "
            "=> propulsion required."
        )
    else:
        trace.append(
            f"Propulsion rule: orbit_family={orbit_family.value} "
            f"=> recommended={propulsion_recommended}."
        )

    if constraints:
        if (
            constraints.max_bus_size_u is not None
            and constraints.max_bus_size_u < recommended_bus_u
        ):
            warnings.append(
                f"Max bus size constraint ({constraints.max_bus_size_u:g}U) is below recommended "
                f"({recommended_bus_u:g}U)."
            )
            trace.append("Constraint check: max_bus_size_u may conflict with packaging.")
        if constraints.altitude_band_km is not None:
            a0, a1 = constraints.altitude_band_km
            trace.append(f"Constraint noted: altitude_band_km=({a0}, {a1}).")
        if constraints.cost_cap_kusd is not None:
            trace.append(f"Constraint noted: cost_cap_kusd={constraints.cost_cap_kusd:g}.")

    if mission_input.roi.type == "global":
        trace.append(
            "ROI: global coverage selected (affects constellation sizing, not per-sat requirements "
            "in v1)."
        )
    else:
        trace.append(f"ROI: regional query '{mission_input.roi.query}'.")

    return DerivedSubsystemRequirements(
        required_bus_volume_u=float(required_bus_u),
        estimated_total_mass_budget_kg=float(estimated_total_mass_budget_kg),
        payload_power_avg_w=float(payload_avg_w),
        payload_power_peak_w=float(payload_peak_w),
        required_pointing_accuracy_deg=float(required_pointing_deg),
        required_downlink_class=downlink_class,
        required_downlink_mbps=required_downlink_mbps,
        required_storage_gb=float(required_storage_gb),
        required_thermal_mode=thermal_mode,
        required_eps_avg_generation_w=float(required_eps_avg_gen_w),
        required_battery_wh=float(required_battery_wh),
        propulsion_recommended=bool(propulsion_recommended),
        recommended_orbit_family=orbit_family,
        warnings=warnings,
        trace=trace,
    )
