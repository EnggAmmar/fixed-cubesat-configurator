from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.mission import MissionFamily


class CatalogPayloadOption(BaseModel):
    payload_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)


class TaxonomyPayloadCategory(BaseModel):
    category_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    payloads: list[CatalogPayloadOption] = Field(default_factory=list)


class TaxonomyMissionFamily(BaseModel):
    family_id: MissionFamily
    label: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    payload_categories: list[TaxonomyPayloadCategory] = Field(default_factory=list)


class TaxonomyResponse(BaseModel):
    version: str = Field(..., min_length=1)
    families: list[TaxonomyMissionFamily] = Field(default_factory=list)
