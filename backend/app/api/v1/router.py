from fastapi import APIRouter

from app.api.v1.endpoints.bus import router as bus_router
from app.api.v1.endpoints.constellation import router as constellation_router
from app.api.v1.endpoints.mission import router as mission_router
from app.api.v1.endpoints.optimization import router as optimization_router
from app.api.v1.endpoints.payload import router as payload_router
from app.api.v1.endpoints.radiation import router as radiation_router
from app.api.v1.endpoints.requirements import router as requirements_router
from app.api.v1.endpoints.taxonomy import router as taxonomy_router

api_router = APIRouter()
api_router.include_router(mission_router, tags=["mission"])
api_router.include_router(payload_router, tags=["payload"])
api_router.include_router(requirements_router, tags=["requirements"])
api_router.include_router(taxonomy_router, tags=["taxonomy"])
api_router.include_router(bus_router, tags=["bus"])
api_router.include_router(optimization_router, tags=["optimization"])
api_router.include_router(constellation_router, tags=["constellation"])
api_router.include_router(radiation_router, tags=["radiation"])
