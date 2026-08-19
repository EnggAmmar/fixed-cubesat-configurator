from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.bus_sizing import BusCandidate, BusCandidateConstraints
from app.schemas.constellation_estimator import ConstellationEstimateV1, EstimatorInputs
from app.schemas.mission import (
    CatalogPayloadRef,
    MissionFamily,
    MissionParameters,
    MyPayloadInput,
    RegionOfInterest,
    ThermalClass,
)
from app.schemas.payload_synthesis import MyPayloadSynthesisResponse
from app.schemas.radiation_screening import RadiationMissionProfile, RadiationScreenResponse
from app.schemas.requirement_derivation import (
    DerivedSubsystemRequirements,
    OptionalUserConstraints,
    OrbitFamily,
)
from app.schemas.subsystem_selection import Margins, SelectedComponent, Totals


class MyPayloadUserInput(BaseModel):
    type: Literal["my_payload"] = "my_payload"
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


SolveMissionPayload = Annotated[CatalogPayloadRef | MyPayloadUserInput, Field(discriminator="type")]


class SolveMissionInput(BaseModel):
    family: MissionFamily
    payload: SolveMissionPayload
    roi: RegionOfInterest
    parameters: MissionParameters


class RadiationOverrides(BaseModel):
    orbit_family: OrbitFamily | None = None
    mission_duration_months: float | None = Field(default=None, gt=0, le=240)
    shielding_assumption_mm_al: float | None = Field(default=None, gt=0, le=20)


class SolveMissionRequest(BaseModel):
    input: SolveMissionInput
    constraints: OptionalUserConstraints | None = None
    estimator: EstimatorInputs = Field(default_factory=EstimatorInputs)
    bus_constraints: BusCandidateConstraints | None = None
    radiation: RadiationOverrides | None = None


class PayloadSummary(BaseModel):
    type: Literal["catalog", "my_payload"]
    payload_id: str | None = None
    name: str

    length_mm: float
    width_mm: float
    height_mm: float

    mass_kg: float
    avg_power_w: float
    peak_power_w: float

    data_rate_mbps: float | None = None
    pointing_accuracy_deg: float | None = None
    thermal_class: str | None = None


class SubsystemSelectionSummary(BaseModel):
    feasible: bool
    status: str
    selected: list[SelectedComponent] = Field(default_factory=list)
    optional_selected: list[SelectedComponent] = Field(default_factory=list)
    totals: Totals | None = None
    margins: Margins | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class SolveMissionResponse(BaseModel):
    input: SolveMissionInput
    normalized_payload: MyPayloadInput | None = None
    payload_summary: PayloadSummary
    payload_synthesis: MyPayloadSynthesisResponse | None = None

    derived_requirements: DerivedSubsystemRequirements
    constellation: ConstellationEstimateV1 | None = None

    bus_candidates: list[BusCandidate] = Field(default_factory=list)
    chosen_bus_size_u: float | None = None

    subsystem_selection: SubsystemSelectionSummary
    radiation: RadiationScreenResponse | None = None
    radiation_profile: RadiationMissionProfile | None = None

    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    report_summary_markdown: str
