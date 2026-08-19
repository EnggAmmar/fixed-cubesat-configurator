from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MissionFamily(StrEnum):
    remote_sensing = "remote_sensing"
    iot_communication = "iot_communication"
    navigation = "navigation"


class ThermalClass(StrEnum):
    standard = "standard"
    sensitive = "sensitive"


class OrbitType(StrEnum):
    leo = "leo"
    sso = "sso"
    polar = "polar"
    equatorial = "equatorial"
    custom = "custom"


class PropulsionPreference(StrEnum):
    no_preference = "no_preference"
    none = "none"
    cold_gas = "cold_gas"
    electric = "electric"
    chemical = "chemical"
    green_monoprop = "green_monoprop"


class PointingPrecisionPreference(StrEnum):
    no_preference = "no_preference"
    coarse = "coarse"
    medium = "medium"
    fine = "fine"
    ultra_fine = "ultra_fine"


class DownlinkRatePreference(StrEnum):
    no_preference = "no_preference"
    low = "low"
    medium = "medium"
    high = "high"
    optical_extreme = "optical_extreme"


class OptimizationPriority(StrEnum):
    balanced = "balanced"
    lowest_cost = "lowest_cost"
    lowest_mass = "lowest_mass"
    highest_performance = "highest_performance"
    lowest_risk = "lowest_risk"


class EngineeringPreferences(BaseModel):
    altitude_km: float | None = Field(default=None, gt=0)
    orbit_type: OrbitType | None = None
    lifetime_years: float | None = Field(default=None, gt=0)

    propulsion_preference: PropulsionPreference | None = None
    pointing_precision_preference: PointingPrecisionPreference | None = None
    downlink_rate_preference: DownlinkRatePreference | None = None
    optimization_priority: OptimizationPriority | None = None

    max_budget_usd: float | None = Field(default=None, gt=0)
    max_bus_u: float | None = Field(default=None, gt=0)


class CatalogPayloadRef(BaseModel):
    type: Literal["catalog"] = "catalog"
    payload_id: str = Field(..., min_length=1)


class MyPayloadInput(BaseModel):
    type: Literal["my_payload"] = "my_payload"
    name: str = Field(..., min_length=1)
    length_mm: float = Field(..., gt=0)
    width_mm: float = Field(..., gt=0)
    height_mm: float = Field(..., gt=0)
    mass_kg: float = Field(..., gt=0)
    avg_power_w: float = Field(..., ge=0)
    peak_power_w: float = Field(..., ge=0)
    data_rate_mbps: float | None = Field(default=None, gt=0)
    pointing_accuracy_deg: float | None = Field(default=None, gt=0)
    thermal_class: ThermalClass | None = None
    storage_required_gb: float | None = Field(default=None, gt=0)
    gpu_required_tops: float | None = Field(default=None, gt=0)


PayloadSelection = Annotated[CatalogPayloadRef | MyPayloadInput, Field(discriminator="type")]


class RoiGlobal(BaseModel):
    type: Literal["global"] = "global"


class RoiRegion(BaseModel):
    type: Literal["region"] = "region"
    query: str = Field(..., min_length=2)


RegionOfInterest = Annotated[RoiGlobal | RoiRegion, Field(discriminator="type")]


class MissionParameters(BaseModel):
    revisit_time_hours: float = Field(..., gt=0, le=720)
    engineering_preferences: EngineeringPreferences | None = None


class MissionInput(BaseModel):
    family: MissionFamily
    payload: PayloadSelection
    roi: RegionOfInterest
    parameters: MissionParameters


class DerivedRequirements(BaseModel):
    payload_mass_kg: float
    payload_volume_cm3: float
    payload_avg_power_w: float
    payload_peak_power_w: float
    min_downlink_mbps: float | None = None
    max_pointing_error_deg: float | None = None
    thermal_class: ThermalClass = ThermalClass.standard


class ConstellationEstimate(BaseModel):
    orbit_type: str
    altitude_km: int
    satellites: int
    planes: int
    satellites_per_plane: int
    notes: list[str] = Field(default_factory=list)


class SelectedSubsystem(BaseModel):
    domain: str
    item_id: str
    name: str
    mass_kg: float
    avg_power_w: float
    peak_power_w: float
    cost_kusd: float
    metadata: dict[str, object] = Field(default_factory=dict)


class PlatformSummary(BaseModel):
    platform_id: str
    name: str
    bus_size_u: float
    max_total_mass_kg: float
    max_payload_volume_cm3: float
    avg_power_gen_w: float
    peak_power_gen_w: float


class Budgets(BaseModel):
    total_mass_kg: float
    total_avg_power_w: float
    total_peak_power_w: float
    total_cost_kusd: float
    mass_margin_kg: float
    avg_power_margin_w: float
    peak_power_margin_w: float


class SolverSolution(BaseModel):
    platform: PlatformSummary
    subsystems: list[SelectedSubsystem]
    budgets: Budgets
    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class EngineeringTraceSolver(BaseModel):
    route_used: str
    solver_name: str
    status: str | None = None
    solve_time_ms: float | None = None
    objective_value: float | None = None
    objective_weights: dict[str, float] | None = None
    notes: list[str] = Field(default_factory=list)


class EngineeringTraceSelection(BaseModel):
    platform_name: str | None = None
    bus_size_u: float | None = None
    payload_id: str | None = None
    payload_source: str | None = None
    subsystem_count: int | None = None


class EngineeringTraceBudget(BaseModel):
    total_mass_kg: float | None = None
    total_avg_power_w: float | None = None
    total_peak_power_w: float | None = None
    total_cost_kusd: float | None = None
    mass_margin_kg: float | None = None
    avg_power_margin_w: float | None = None
    peak_power_margin_w: float | None = None
    bus_volume_margin_u: float | None = None


class EngineeringTraceSubsystem(BaseModel):
    domain: str
    name: str
    mass_kg: float | None = None
    avg_power_w: float | None = None
    peak_power_w: float | None = None
    cost_kusd: float | None = None
    tier: str | None = None
    metadata: dict[str, object] | None = None
    selection_reason: str | None = None
    source_library: str | None = None
    source_database: str | None = None
    capacity_basis: str | None = None
    margin_basis: str | None = None


class EngineeringTraceConstraint(BaseModel):
    name: str
    required: float | None = None
    capacity: float | None = None
    margin: float | None = None
    units: str | None = None
    status: str = "UNKNOWN"


class EngineeringTrace(BaseModel):
    solver: EngineeringTraceSolver
    selection: EngineeringTraceSelection
    budgets: EngineeringTraceBudget
    subsystems: list[EngineeringTraceSubsystem] = Field(default_factory=list)
    constraints: list[EngineeringTraceConstraint] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preferences: list[dict[str, object]] = Field(default_factory=list)


class MissionSolveRequest(BaseModel):
    input: MissionInput


class MissionReportRequest(BaseModel):
    input: MissionInput


class MissionSolveResponse(BaseModel):
    input: MissionInput
    requirements: DerivedRequirements
    constellation: ConstellationEstimate
    solution: SolverSolution
    engineering_trace: EngineeringTrace | None = None


class MissionFamiliesResponse(BaseModel):
    families: list[MissionFamily]


class PayloadCategory(BaseModel):
    category_id: str
    label: str


class PayloadCategoriesResponse(BaseModel):
    categories: list[PayloadCategory]
