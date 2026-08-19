from __future__ import annotations

from app.schemas.mission import (
    CatalogPayloadRef,
    MissionFamily,
    MissionInput,
    MissionParameters,
    RoiRegion,
)
from app.services.catalog import get_catalog
from app.services.constellation import estimate_constellation
from app.services.optimization.solver import solve_subsystems
from app.services.requirements import derive_requirements


def test_solver_respects_pointing_and_downlink_constraints() -> None:
    catalog = get_catalog()
    mission_input = MissionInput(
        family=MissionFamily.remote_sensing,
        payload=CatalogPayloadRef(payload_id="rs_vhr_optical_v1"),
        roi=RoiRegion(query="Pakistan"),
        parameters=MissionParameters(revisit_time_hours=48),
    )
    reqs = derive_requirements(mission_input, catalog)
    const = estimate_constellation(mission_input, reqs)
    sol = solve_subsystems(mission_input, reqs, const, catalog)

    comm = next(s for s in sol.subsystems if s.domain == "comm")
    assert float(comm.metadata.get("downlink_mbps", 0)) >= (reqs.min_downlink_mbps or 0)

    adcs = next(s for s in sol.subsystems if s.domain == "adcs")
    assert float(adcs.metadata.get("pointing_error_deg", 999)) <= (
        reqs.max_pointing_error_deg or 999
    )
