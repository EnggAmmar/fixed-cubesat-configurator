from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.bus_sizing import BusCandidatesRequest, BusCandidatesResponse
from app.services.bus_sizing import evaluate_bus_candidates

router = APIRouter()


@router.post("/bus/candidates", response_model=BusCandidatesResponse)
def bus_candidates(req: BusCandidatesRequest) -> BusCandidatesResponse:
    try:
        return evaluate_bus_candidates(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
