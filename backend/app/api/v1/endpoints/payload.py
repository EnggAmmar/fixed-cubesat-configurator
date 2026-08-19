from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.payload_synthesis import MyPayloadSynthesisRequest, MyPayloadSynthesisResponse
from app.services.payload_synthesis import synthesize_confidential_payload

router = APIRouter()


@router.post("/payload/my-payload/preview", response_model=MyPayloadSynthesisResponse)
def preview_my_payload(req: MyPayloadSynthesisRequest) -> MyPayloadSynthesisResponse:
    try:
        return synthesize_confidential_payload(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
