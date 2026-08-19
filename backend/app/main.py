from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.report import router as report_router
from app.api.solve_cubesat import router as solve_cubesat_router
from app.api.solve_mission import router as solve_mission_router
from app.api.v1.router import api_router


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return ["http://localhost:3000", "http://localhost:5173"]
    return [v.strip() for v in value.split(",") if v.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="CubeSat Mission Configurator API",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(solve_mission_router, prefix="/api", tags=["solve"])
    app.include_router(solve_cubesat_router, prefix="/api", tags=["solve"])
    app.include_router(report_router, prefix="/api", tags=["report"])
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
