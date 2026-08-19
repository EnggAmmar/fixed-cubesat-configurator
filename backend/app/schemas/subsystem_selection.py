from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionInput
from app.schemas.requirement_derivation import DerivedSubsystemRequirements, OptionalUserConstraints


class SelectedComponent(BaseModel):
    domain: str
    item_id: str
    name: str
    mass_kg: float = Field(..., ge=0)
    avg_power_w: float = Field(..., ge=0)
    peak_power_w: float = Field(..., ge=0)
    cost_kusd: float = Field(..., ge=0)
    risk_points: float = Field(..., ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class Totals(BaseModel):
    total_mass_kg: float
    total_avg_power_w: float
    total_peak_power_w: float
    total_cost_kusd: float
    total_risk_points: float


class Margins(BaseModel):
    mass_margin_kg: float
    avg_power_margin_w: float
    peak_power_margin_w: float
    bus_volume_margin_u: float


class SubsystemSolveRequest(BaseModel):
    input: MissionInput
    constraints: OptionalUserConstraints | None = None


class SubsystemSolveResponse(BaseModel):
    feasible: bool
    status: str
    input: MissionInput
    derived_requirements: DerivedSubsystemRequirements
    selected: list[SelectedComponent] = Field(default_factory=list)
    optional_selected: list[SelectedComponent] = Field(default_factory=list)
    totals: Totals | None = None
    margins: Margins | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
