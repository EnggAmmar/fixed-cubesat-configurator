from __future__ import annotations

from fastapi import APIRouter

from app.schemas.radiation_screening import RadiationScreenRequest, RadiationScreenResponse
from app.services.radiation_screening import screen_architecture_radiation

router = APIRouter()


@router.post("/radiation/screen", response_model=RadiationScreenResponse)
def radiation_screen(req: RadiationScreenRequest) -> RadiationScreenResponse:
    return screen_architecture_radiation(
        mission=req.mission,
        selected=req.selected,
        optional_selected=req.optional_selected,
    )
