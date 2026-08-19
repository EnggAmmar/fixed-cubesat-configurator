from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Response

from app.schemas.mission import (
    Budgets,
    CatalogPayloadRef,
    DerivedRequirements,
    MissionFamiliesResponse,
    MissionInput,
    MissionReportRequest,
    MissionSolveRequest,
    MissionSolveResponse,
    MyPayloadInput,
    PayloadCategoriesResponse,
    PlatformSummary,
    SelectedSubsystem,
    SolverSolution,
)
from app.schemas.solve_mission import (
    MyPayloadUserInput,
)
from app.schemas.solve_mission import (
    SolveMissionInput as AdvancedSolveMissionInput,
)
from app.schemas.solve_mission import (
    SolveMissionRequest as AdvancedSolveMissionRequest,
)
from app.services.catalog import get_catalog
from app.services.constellation import estimate_constellation
from app.services.engineering_preferences import (
    objective_value_from_trace,
    objective_weights_from_trace,
    optional_constraints_from_engineering_preferences,
)
from app.services.engineering_trace import build_engineering_trace
from app.services.report import (
    build_mission_report_payload,
    render_mission_report_html,
    render_mission_report_markdown_from_payload,
    render_mission_report_pdf,
    report_payload_json_bytes,
)
from app.services.requirements import derive_requirements
from app.services.solve_mission import solve_mission as solve_mission_advanced
from app.services.taxonomy import get_taxonomy

router = APIRouter()


def _advanced_payload_from_v1(payload: CatalogPayloadRef | MyPayloadInput) -> dict:
    if payload.type == "catalog":
        return {"type": "catalog", "payload_id": payload.payload_id}
    return {
        "type": "my_payload",
        "name": payload.name,
        "mission_family": None,
        "external_length_mm": payload.length_mm,
        "external_width_mm": payload.width_mm,
        "external_height_mm": payload.height_mm,
        "mass_kg": payload.mass_kg,
        "power_avg_w": payload.avg_power_w,
        "power_peak_w": payload.peak_power_w,
        "optional_data_rate_mbps": payload.data_rate_mbps,
        "optional_pointing_accuracy_deg": payload.pointing_accuracy_deg,
        "optional_thermal_class": payload.thermal_class,
        "optional_storage_required_gb": payload.storage_required_gb,
        "optional_gpu_required_tops": payload.gpu_required_tops,
    }


def _advanced_input_from_v1(mission_input: MissionInput) -> AdvancedSolveMissionInput:
    payload = _advanced_payload_from_v1(mission_input.payload)
    if payload["type"] == "my_payload":
        payload["mission_family"] = mission_input.family
        advanced_payload = MyPayloadUserInput.model_validate(payload)
    else:
        advanced_payload = CatalogPayloadRef.model_validate(payload)
    return AdvancedSolveMissionInput(
        family=mission_input.family,
        payload=advanced_payload,
        roi=mission_input.roi,
        parameters=mission_input.parameters,
    )


def _requirements_from_advanced(
    base: DerivedRequirements, advanced_required_downlink_mbps: float | None
) -> DerivedRequirements:
    min_downlink = base.min_downlink_mbps
    if advanced_required_downlink_mbps is not None:
        min_downlink = (
            advanced_required_downlink_mbps
            if min_downlink is None
            else max(min_downlink, advanced_required_downlink_mbps)
        )
    return base.model_copy(update={"min_downlink_mbps": min_downlink})


def _solution_from_advanced(advanced_response) -> SolverSolution:
    selection = advanced_response.subsystem_selection
    if not selection.feasible or selection.totals is None or selection.margins is None:
        details = "; ".join(advanced_response.warnings or selection.warnings or [selection.status])
        raise ValueError(f"No feasible subsystem configuration found: {details}")

    structure = next((c for c in selection.selected if c.domain == "structure"), None)
    if structure is None:
        raise ValueError("Advanced solver did not return a structure/platform selection.")

    platform = PlatformSummary(
        platform_id=structure.item_id,
        name=structure.name,
        bus_size_u=float(structure.metadata["bus_size_u"]),
        max_total_mass_kg=float(structure.metadata["max_total_mass_kg"]),
        max_payload_volume_cm3=float(structure.metadata["max_payload_volume_cm3"]),
        avg_power_gen_w=float(structure.metadata["avg_power_gen_w"]),
        peak_power_gen_w=float(structure.metadata["peak_power_gen_w"]),
    )
    selected = [
        SelectedSubsystem(
            domain=c.domain,
            item_id=c.item_id,
            name=c.name,
            mass_kg=c.mass_kg,
            avg_power_w=c.avg_power_w,
            peak_power_w=c.peak_power_w,
            cost_kusd=c.cost_kusd,
            metadata=c.metadata,
        )
        for c in [*selection.selected, *selection.optional_selected]
        if c.domain != "structure"
    ]
    budgets = Budgets(
        total_mass_kg=selection.totals.total_mass_kg,
        total_avg_power_w=selection.totals.total_avg_power_w,
        total_peak_power_w=selection.totals.total_peak_power_w,
        total_cost_kusd=selection.totals.total_cost_kusd,
        mass_margin_kg=selection.margins.mass_margin_kg,
        avg_power_margin_w=selection.margins.avg_power_margin_w,
        peak_power_margin_w=selection.margins.peak_power_margin_w,
    )
    return SolverSolution(
        platform=platform,
        subsystems=selected,
        budgets=budgets,
        warnings=list(advanced_response.warnings or []),
        trace=list(advanced_response.trace or []),
    )


def _solve_v1_integrated(
    req: MissionSolveRequest, solve_time_ms: float | None
) -> MissionSolveResponse:
    catalog = get_catalog()
    constraints, preference_applications = optional_constraints_from_engineering_preferences(
        req.input
    )
    advanced_request = AdvancedSolveMissionRequest(
        input=_advanced_input_from_v1(req.input),
        constraints=constraints,
    )
    advanced_response = solve_mission_advanced(advanced_request)
    requirements_base = derive_requirements(req.input, catalog)
    requirements = _requirements_from_advanced(
        requirements_base,
        advanced_response.derived_requirements.required_downlink_mbps,
    )
    advanced_pointing = advanced_response.derived_requirements.required_pointing_accuracy_deg
    if requirements.max_pointing_error_deg is not None and (
        advanced_pointing < requirements.max_pointing_error_deg
    ):
        requirements = requirements.model_copy(update={"max_pointing_error_deg": advanced_pointing})
    constellation = estimate_constellation(req.input, requirements)
    solution = _solution_from_advanced(advanced_response)
    objective_value = objective_value_from_trace(advanced_response.subsystem_selection.trace)
    objective_weights = objective_weights_from_trace(advanced_response.subsystem_selection.trace)
    engineering_trace = build_engineering_trace(
        mission_input=req.input,
        requirements=requirements,
        constellation=constellation,
        solution=solution,
        solve_time_ms=solve_time_ms,
        preference_applications=preference_applications,
        objective_value=objective_value,
        objective_weights=objective_weights,
    )
    engineering_trace.trace.extend(advanced_response.trace)
    return MissionSolveResponse(
        input=req.input,
        requirements=requirements,
        constellation=constellation,
        solution=solution,
        engineering_trace=engineering_trace,
    )


@router.get("/mission-families", response_model=MissionFamiliesResponse)
def mission_families() -> MissionFamiliesResponse:
    taxonomy = get_taxonomy()
    return MissionFamiliesResponse(families=[f.family_id for f in taxonomy.families])


@router.get("/payload-categories", response_model=PayloadCategoriesResponse)
def payload_categories(family: str) -> PayloadCategoriesResponse:
    taxonomy = get_taxonomy()
    fam = next((f for f in taxonomy.families if f.family_id.value == family), None)
    if not fam:
        return PayloadCategoriesResponse(categories=[])
    return PayloadCategoriesResponse(
        categories=[
            {"category_id": c.category_id, "label": c.label} for c in fam.payload_categories
        ]
    )


@router.post("/mission/solve", response_model=MissionSolveResponse)
def mission_solve(req: MissionSolveRequest) -> MissionSolveResponse:
    try:
        t0 = time.perf_counter()
        response = _solve_v1_integrated(req, solve_time_ms=None)
        solve_time_ms = (time.perf_counter() - t0) * 1000.0
        if response.engineering_trace is not None:
            response.engineering_trace.solver.solve_time_ms = solve_time_ms
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return response


@router.post("/mission/report")
def mission_report(req: MissionReportRequest, format: str = "markdown") -> Response:
    try:
        solved = _solve_v1_integrated(MissionSolveRequest(input=req.input), solve_time_ms=None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    report = build_mission_report_payload(
        mission_input=req.input,
        requirements=solved.requirements,
        constellation=solved.constellation,
        solution=solved.solution,
        engineering_trace=solved.engineering_trace,
    )
    if format == "pdf":
        pdf = render_mission_report_pdf(report)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"content-disposition": "attachment; filename=cubesat-mission-report.pdf"},
        )
    if format == "json":
        return Response(
            content=report_payload_json_bytes(report),
            media_type="application/json; charset=utf-8",
            headers={"content-disposition": "attachment; filename=mission-report.json"},
        )
    if format == "html":
        return Response(
            content=render_mission_report_html(report).encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"content-disposition": "attachment; filename=mission-report.html"},
        )
    if format in {"markdown", "md"}:
        md = render_mission_report_markdown_from_payload(report)
        return Response(content=md, media_type="text/markdown; charset=utf-8")
    raise HTTPException(
        status_code=400,
        detail="format must be 'pdf', 'html', 'json', 'markdown', or 'md'",
    )
