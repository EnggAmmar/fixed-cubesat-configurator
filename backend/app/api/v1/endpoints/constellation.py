from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.constellation_estimator import (
    ConstellationEstimateRequest,
    ConstellationEstimateResponse,
)
from app.services.constellation_estimator import estimate_constellation_v1

router = APIRouter()


@router.post("/constellation/estimate", response_model=ConstellationEstimateResponse)
def estimate_constellation(req: ConstellationEstimateRequest) -> ConstellationEstimateResponse:
    try:
        est = estimate_constellation_v1(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ConstellationEstimateResponse(input=req.input, estimate=est)
