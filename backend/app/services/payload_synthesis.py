from __future__ import annotations

from app.schemas.mission import MyPayloadInput, ThermalClass
from app.schemas.payload_synthesis import (
    MyPayloadSynthesisRequest,
    MyPayloadSynthesisResponse,
    PackagingMetadata,
)
from app.services.units import ceil_div_mm_to_u, occupied_u_from_cm3, volume_cm3_from_mm


def synthesize_confidential_payload(
    req: MyPayloadSynthesisRequest,
) -> MyPayloadSynthesisResponse:
    warnings: list[str] = []
    notes: list[str] = []

    name = req.name.strip()
    if not name:
        raise ValueError("Payload name must be non-empty.")

    avg_power_w = float(req.power_avg_w)
    peak_power_w = float(req.power_peak_w)
    if peak_power_w < avg_power_w:
        warnings.append("Peak power was below average power; clamped peak to avg.")
        peak_power_w = avg_power_w

    thermal_class = req.optional_thermal_class or ThermalClass.standard
    if req.optional_thermal_class is None:
        warnings.append("Thermal class not provided; defaulted to `standard`.")

    if req.optional_data_rate_mbps is None:
        warnings.append("Data rate not provided; downlink constraints may be under-specified.")
    if req.optional_pointing_accuracy_deg is None:
        warnings.append("Pointing accuracy not provided; ADCS constraints may be under-specified.")
    if req.optional_storage_required_gb is not None:
        warnings.append("Storage requirement captured but not yet enforced in v1 solver.")
    if req.optional_gpu_required_tops is not None:
        warnings.append("GPU/processing requirement captured but not yet enforced in v1 solver.")

    length_mm = float(req.external_length_mm)
    width_mm = float(req.external_width_mm)
    height_mm = float(req.external_height_mm)

    external_volume_cm3 = volume_cm3_from_mm(length_mm, width_mm, height_mm)
    occupied_u = occupied_u_from_cm3(external_volume_cm3)

    a, b, c = sorted([length_mm, width_mm, height_mm])
    fits_cross_section = a <= 100.0 and b <= 100.0
    estimated_stack_u: int | None = None
    if fits_cross_section:
        estimated_stack_u = ceil_div_mm_to_u(c)
        notes.append(f"Assumed orientation: cross-section {a:g}x{b:g} mm, stack length {c:g} mm.")
    else:
        warnings.append(
            "Payload exceeds standard 1U cross-section in all orientations (min two dims > 100 mm)."
        )

    packaging = PackagingMetadata(
        external_volume_cm3=external_volume_cm3,
        occupied_volume_u=occupied_u,
        assumed_orientation_mm={
            "cross_section_a_mm": a,
            "cross_section_b_mm": b,
            "stack_length_mm": c,
        },
        fits_standard_1u_cross_section=fits_cross_section,
        estimated_stack_u=estimated_stack_u,
        notes=notes,
    )

    payload = MyPayloadInput(
        type="my_payload",
        name=name,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        mass_kg=float(req.mass_kg),
        avg_power_w=avg_power_w,
        peak_power_w=peak_power_w,
        data_rate_mbps=req.optional_data_rate_mbps,
        pointing_accuracy_deg=req.optional_pointing_accuracy_deg,
        thermal_class=thermal_class,
        storage_required_gb=req.optional_storage_required_gb,
        gpu_required_tops=req.optional_gpu_required_tops,
    )

    return MyPayloadSynthesisResponse(
        mission_family=req.mission_family,
        payload=payload,
        occupied_volume_u=occupied_u,
        packaging=packaging,
        warnings=warnings,
    )
