from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.schemas.mission_report import MissionReportJson
from app.schemas.solve_mission import SolveMissionRequest
from app.services.mission_report import build_report_json, render_report_html, report_json_bytes
from app.services.pdf_report import render_report_pdf

router = APIRouter()


@router.post("/report.json", response_model=MissionReportJson)
def report_json(req: SolveMissionRequest) -> MissionReportJson:
    return build_report_json(req)


@router.post("/report/download")
def report_download(req: SolveMissionRequest, format: str = "html") -> Response:
    try:
        report = build_report_json(req)
        if format == "pdf":
            content = render_report_pdf(report)
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"content-disposition": "attachment; filename=cubesat-mission-report.pdf"},
            )
        if format == "json":
            content = report_json_bytes(report)
            return Response(
                content=content,
                media_type="application/json; charset=utf-8",
                headers={"content-disposition": "attachment; filename=mission-report.json"},
            )
        if format == "html":
            content = render_report_html(report).encode("utf-8")
            return Response(
                content=content,
                media_type="text/html; charset=utf-8",
                headers={"content-disposition": "attachment; filename=mission-report.html"},
            )
        raise ValueError("format must be 'pdf', 'html', or 'json'")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
