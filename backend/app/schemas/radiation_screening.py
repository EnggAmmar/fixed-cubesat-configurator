from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.requirement_derivation import OrbitFamily
from app.schemas.subsystem_selection import SelectedComponent


class RadiationMissionProfile(BaseModel):
    orbit_family: OrbitFamily = OrbitFamily.leo
    mission_duration_months: float = Field(default=12.0, gt=0, le=240)
    shielding_assumption_mm_al: float = Field(default=2.0, gt=0, le=20)


class RadiationFlag(BaseModel):
    component_id: str | None = None
    item_id: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    component_name: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    mitigations: list[str] = Field(default_factory=list)


class RadiationScreenRequest(BaseModel):
    mission: RadiationMissionProfile
    selected: list[SelectedComponent] = Field(default_factory=list)
    optional_selected: list[SelectedComponent] = Field(default_factory=list)


class RadiationScreenResponse(BaseModel):
    mission: RadiationMissionProfile
    flags: list[RadiationFlag] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
