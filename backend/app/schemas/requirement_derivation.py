from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.mission import MissionInput


class DownlinkClass(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class ThermalMode(StrEnum):
    standard = "standard"
    enhanced = "enhanced"


class OrbitFamily(StrEnum):
    sun_synchronous_leo = "sun_synchronous_leo"
    leo = "leo"
    meo = "meo"


class OptionalUserConstraints(BaseModel):
    cost_cap_kusd: float | None = Field(default=None, gt=0)
    max_bus_size_u: float | None = Field(default=None, gt=0)
    preferred_propulsion: str | None = Field(default=None, min_length=1)
    altitude_band_km: tuple[int, int] | None = None
    min_downlink_mbps: float | None = Field(default=None, gt=0)
    max_pointing_error_deg: float | None = Field(default=None, gt=0)
    optimization_priority: str | None = Field(default=None, min_length=1)
    # Ground stations contributing daily contact time; only consumed by the
    # backend/solver/-backed engine adapter (see cubesat_engine_adapter.py). Defaults
    # to 1 there if unset - no behavior change for callers that don't set this.
    ground_station_count: int | None = Field(default=None, ge=1)


class DerivedSubsystemRequirements(BaseModel):
    required_bus_volume_u: float = Field(..., gt=0)
    estimated_total_mass_budget_kg: float = Field(..., gt=0)

    payload_power_avg_w: float = Field(..., ge=0)
    payload_power_peak_w: float = Field(..., ge=0)

    required_pointing_accuracy_deg: float = Field(..., gt=0)
    required_downlink_class: DownlinkClass
    required_downlink_mbps: float | None = Field(default=None, gt=0)

    required_storage_gb: float = Field(..., gt=0)
    required_thermal_mode: ThermalMode

    required_eps_avg_generation_w: float = Field(..., ge=0)
    required_battery_wh: float = Field(..., gt=0)

    propulsion_recommended: bool
    recommended_orbit_family: OrbitFamily

    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class RequirementsDerivationRequest(BaseModel):
    input: MissionInput
    constraints: OptionalUserConstraints | None = None


class RequirementsDerivationResponse(BaseModel):
    input: MissionInput
    derived: DerivedSubsystemRequirements
