from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionInput
from app.schemas.requirement_derivation import OrbitFamily


class EstimatorInputs(BaseModel):
    payload_swath_km: float | None = Field(default=None, gt=0)
    payload_field_of_regard_deg: float | None = Field(default=None, gt=0, le=80)

    altitude_range_km: tuple[int, int] = (450, 650)
    inclination_range_deg: tuple[float, float] = (0.0, 100.0)

    allowed_orbit_families: list[OrbitFamily] = Field(default_factory=list)

    payload_data_volume_gb_per_day: float | None = Field(default=None, gt=0)
    downlink_mbps_assumed: float | None = Field(default=None, gt=0)


class WalkerCandidate(BaseModel):
    total_satellites: int = Field(..., ge=1)
    planes: int = Field(..., ge=1)
    satellites_per_plane: int = Field(..., ge=1)
    relative_phasing_f: int = Field(..., ge=0)
    score: float
    rationale: list[str] = Field(default_factory=list)


class ConstellationEstimateV1(BaseModel):
    recommended_orbit_family: OrbitFamily
    candidate_altitudes_km: list[int] = Field(default_factory=list)
    candidate_inclinations_deg: list[float] = Field(default_factory=list)

    estimated_number_of_satellites: int = Field(..., ge=1)
    recommended_candidate: WalkerCandidate
    candidate_walker_constellations: list[WalkerCandidate] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ConstellationEstimateRequest(BaseModel):
    input: MissionInput
    estimator: EstimatorInputs = Field(default_factory=EstimatorInputs)


class ConstellationEstimateResponse(BaseModel):
    input: MissionInput
    estimate: ConstellationEstimateV1
