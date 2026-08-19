from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    # When running with `backend/` on PYTHONPATH (tests, Docker), prefer sibling import.
    from solver.cubesat_solver_runner import (  # type: ignore[import-not-found]
        run_cubesat_diagnostic,
        run_cubesat_solver,
        run_family_solver,
    )
except ModuleNotFoundError:  # pragma: no cover
    # Fallback for environments where repo root is on PYTHONPATH.
    from backend.solver.cubesat_solver_runner import (
        run_cubesat_diagnostic,
        run_cubesat_solver,
        run_family_solver,
    )

router = APIRouter()


class CubeSatSolveRequest(BaseModel):
    payload_id: str = Field(..., min_length=1)
    top_n: int = Field(default=1, ge=1, le=50)
    diagnostic: bool = False


@router.post("/solve/cubesat")
def solve_cubesat_api(req: CubeSatSolveRequest) -> dict[str, Any]:
    try:
        if req.diagnostic:
            return run_cubesat_diagnostic(req.payload_id)
        if req.top_n > 1:
            return run_family_solver(req.payload_id, top_n=req.top_n)
        return run_cubesat_solver(req.payload_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
