from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class RadClass(StrEnum):
    cots = "cots"
    screened_cots = "screened_cots"
    rad_tolerant = "rad_tolerant"
    rad_hard = "rad_hard"


class VerificationStatus(StrEnum):
    unverified = "unverified"
    vendor_claim = "vendor_claim"
    test_report = "test_report"
    flight_heritage = "flight_heritage"


class RadiationComponent(BaseModel):
    component_name: str = Field(..., min_length=1)
    vendor: str = Field(..., min_length=1)
    component_type: str = Field(..., min_length=1)
    part_family: str = Field(..., min_length=1)
    rad_class: RadClass
    tid_krad: float = Field(..., ge=0)
    see_notes: str = Field(..., min_length=1)
    latchup_notes: str = Field(..., min_length=1)
    shielding_assumptions: str = Field(..., min_length=1)
    heritage_notes: str = Field(..., min_length=1)
    operating_voltage: str = Field(..., min_length=1)
    package: str = Field(..., min_length=1)
    source_url: HttpUrl | None = None
    verification_status: VerificationStatus

    # Optional mapping key for catalogs (v1 convenience)
    component_id: str | None = Field(default=None, min_length=1)


class RadiationDatabase(BaseModel):
    version: str = Field(..., min_length=1)
    components: list[RadiationComponent] = Field(default_factory=list)
