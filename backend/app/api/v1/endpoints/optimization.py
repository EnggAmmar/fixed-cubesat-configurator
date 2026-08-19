from __future__ import annotations

from fastapi import APIRouter

from app.schemas.subsystem_selection import SubsystemSolveRequest, SubsystemSolveResponse
from app.services.optimization.cpsat_selection import solve_subsystems_cpsat
from app.services.requirement_derivation import derive_subsystem_requirements

router = APIRouter()


@router.post("/optimization/subsystems/solve", response_model=SubsystemSolveResponse)
def solve_subsystems(req: SubsystemSolveRequest) -> SubsystemSolveResponse:
    derived = derive_subsystem_requirements(req.input, req.constraints)
    feasible, status, selected, optional_selected, totals, margins, warnings, trace = (
        solve_subsystems_cpsat(req.input, derived, req.constraints)
    )
    return SubsystemSolveResponse(
        feasible=feasible,
        status=status,
        input=req.input,
        derived_requirements=derived,
        selected=selected,
        optional_selected=optional_selected,
        totals=totals,
        margins=margins,
        warnings=warnings,
        trace=trace,
    )
