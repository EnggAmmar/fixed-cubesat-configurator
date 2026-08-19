from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.requirement_derivation import (
    RequirementsDerivationRequest,
    RequirementsDerivationResponse,
)
from app.services.requirement_derivation import derive_subsystem_requirements

router = APIRouter()


@router.post("/requirements/derive", response_model=RequirementsDerivationResponse)
def derive_requirements(req: RequirementsDerivationRequest) -> RequirementsDerivationResponse:
    try:
        derived = derive_subsystem_requirements(req.input, req.constraints)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RequirementsDerivationResponse(input=req.input, derived=derived)
