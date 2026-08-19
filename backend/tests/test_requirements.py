from __future__ import annotations

from app.schemas.mission import (
    CatalogPayloadRef,
    MissionFamily,
    MissionInput,
    MissionParameters,
    RoiGlobal,
)
from app.services.catalog import get_catalog
from app.services.requirements import derive_requirements


def test_derive_requirements_catalog_payload() -> None:
    catalog = get_catalog()
    mission_input = MissionInput(
        family=MissionFamily.remote_sensing,
        payload=CatalogPayloadRef(payload_id="rs_hyperspec_v1"),
        roi=RoiGlobal(),
        parameters=MissionParameters(revisit_time_hours=48),
    )
    req = derive_requirements(mission_input, catalog)
    assert req.payload_mass_kg > 0
    assert req.payload_volume_cm3 > 0
    assert req.min_downlink_mbps is not None
