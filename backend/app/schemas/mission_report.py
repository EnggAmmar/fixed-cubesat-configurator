from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionFamily, MissionParameters, RegionOfInterest
from app.schemas.payload_synthesis import MyPayloadSynthesisResponse
from app.schemas.radiation_screening import RadiationMissionProfile, RadiationScreenResponse
from app.schemas.requirement_derivation import DerivedSubsystemRequirements, OptionalUserConstraints
from app.schemas.solve_mission import PayloadSummary, SolveMissionInput, SubsystemSelectionSummary


class MissionSummarySection(BaseModel):
    family: MissionFamily
    roi: RegionOfInterest
    parameters: MissionParameters
    constraints: OptionalUserConstraints | None = None


class PayloadSection(BaseModel):
    summary: PayloadSummary
    synthesis: MyPayloadSynthesisResponse | None = None


class ConstellationSection(BaseModel):
    available: bool
    orbit_family: str | None = None
    estimated_satellites: int | None = None
    planes: int | None = None
    satellites_per_plane: int | None = None
    trace: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BusPlatformSection(BaseModel):
    chosen_bus_size_u: float | None = None
    structure_component: dict[str, object] | None = None
    bus_candidates: list[dict[str, object]] = Field(default_factory=list)


class RadiationSection(BaseModel):
    profile: RadiationMissionProfile | None = None
    screening: RadiationScreenResponse | None = None


class TraceSection(BaseModel):
    derivation_trace: list[str] = Field(default_factory=list)
    solver_trace: list[str] = Field(default_factory=list)
    constellation_trace: list[str] = Field(default_factory=list)
    radiation_trace: list[str] = Field(default_factory=list)
    pipeline_trace: list[str] = Field(default_factory=list)


class MissionReportJson(BaseModel):
    version: str = Field(default="v1", min_length=1)
    input: SolveMissionInput

    mission_summary: MissionSummarySection
    payload: PayloadSection
    derived_requirements: DerivedSubsystemRequirements
    constellation: ConstellationSection
    bus_platform: BusPlatformSection
    subsystem_selection: SubsystemSelectionSummary
    radiation: RadiationSection

    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    trace: TraceSection
