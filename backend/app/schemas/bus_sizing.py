from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionFamily, MissionInput


class StructureSize(BaseModel):
    size_u: float = Field(..., gt=0)
    label: str = Field(..., min_length=1)
    official: bool
    cross_section_mm: tuple[float, float] = Field(..., min_length=2, max_length=2)
    max_length_mm: float = Field(..., gt=0)
    subsystem_reserve_fraction: float = Field(..., gt=0, lt=1)
    notes: list[str] = Field(default_factory=list)


class StructureCatalog(BaseModel):
    version: str = Field(..., min_length=1)
    structures: list[StructureSize] = Field(default_factory=list)


class BusCandidateConstraints(BaseModel):
    max_bus_size_u: float | None = Field(default=None, gt=0)
    include_commercial_sizes: bool = True


class BusCandidate(BaseModel):
    size_u: float
    label: str
    official: bool

    nominal_total_volume_u: float
    subsystem_reserve_margin_u: float
    usable_payload_volume_u: float

    payload_occupied_volume_u: float
    payload_volume_with_margin_u: float

    envelope_fit: bool
    volume_fit: bool
    overall_fit: bool

    fitness_score: float
    reasoning: list[str] = Field(default_factory=list)


class BusCandidatesRequest(BaseModel):
    input: MissionInput
    constraints: BusCandidateConstraints | None = None


class BusCandidatesResponse(BaseModel):
    mission_family: MissionFamily
    candidates: list[BusCandidate] = Field(default_factory=list)
