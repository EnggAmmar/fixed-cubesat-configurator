from __future__ import annotations

from fastapi import APIRouter

from app.schemas.taxonomy import TaxonomyResponse
from app.services.taxonomy import get_taxonomy

router = APIRouter()


@router.get("/taxonomy", response_model=TaxonomyResponse)
def taxonomy() -> TaxonomyResponse:
    return get_taxonomy()
