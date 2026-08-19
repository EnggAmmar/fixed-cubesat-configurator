from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionFamily, MyPayloadInput, ThermalClass


class MyPayloadSynthesisRequest(BaseModel):
    name: str = Field(..., min_length=1)
    mission_family: MissionFamily

    external_length_mm: float = Field(..., gt=0)
    external_width_mm: float = Field(..., gt=0)
    external_height_mm: float = Field(..., gt=0)

    mass_kg: float = Field(..., gt=0)
    power_avg_w: float = Field(..., ge=0)
    power_peak_w: float = Field(..., ge=0)

    optional_data_rate_mbps: float | None = Field(default=None, gt=0)
    optional_pointing_accuracy_deg: float | None = Field(default=None, gt=0)
    optional_thermal_class: ThermalClass | None = None
    optional_storage_required_gb: float | None = Field(default=None, gt=0)
    optional_gpu_required_tops: float | None = Field(default=None, gt=0)


class PackagingMetadata(BaseModel):
    external_volume_cm3: float
    occupied_volume_u: float
    assumed_orientation_mm: dict[str, float]
    fits_standard_1u_cross_section: bool
    estimated_stack_u: int | None = None
    notes: list[str] = Field(default_factory=list)


class MyPayloadSynthesisResponse(BaseModel):
    mission_family: MissionFamily
    payload: MyPayloadInput
    occupied_volume_u: float
    packaging: PackagingMetadata
    warnings: list[str] = Field(default_factory=list)
