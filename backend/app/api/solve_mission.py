from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.solve_mission import SolveMissionRequest, SolveMissionResponse
from app.services.solve_mission import solve_mission

router = APIRouter()


@router.post("/solve-mission", response_model=SolveMissionResponse)
def solve_mission_api(req: SolveMissionRequest) -> SolveMissionResponse:
    try:
        return solve_mission(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
