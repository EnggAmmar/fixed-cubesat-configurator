from __future__ import annotations

from app.schemas.bus_sizing import BusCandidateConstraints, BusCandidatesRequest
from app.schemas.constellation_estimator import ConstellationEstimateRequest
from app.schemas.mission import CatalogPayloadRef, MissionInput, MyPayloadInput
from app.schemas.payload_synthesis import MyPayloadSynthesisRequest, MyPayloadSynthesisResponse
from app.schemas.radiation_screening import RadiationMissionProfile, RadiationScreenResponse
from app.schemas.solve_mission import (
    PayloadSummary,
    SolveMissionRequest,
    SolveMissionResponse,
    SubsystemSelectionSummary,
)
from app.services.bus_sizing import evaluate_bus_candidates
from app.services.catalog import get_catalog
from app.services.constellation_estimator import estimate_constellation_v1
from app.services.optimization.cpsat_selection import solve_subsystems_cpsat
from app.services.payload_resolver import resolve_payload_for_requirements
from app.services.payload_synthesis import synthesize_confidential_payload
from app.services.radiation_screening import screen_architecture_radiation
from app.services.requirement_derivation import derive_subsystem_requirements


def _payload_summary_from_catalog(payload_id: str) -> PayloadSummary:
    catalog = get_catalog()
    p = resolve_payload_for_requirements(payload_id, catalog)
    if not p:
        raise ValueError(f"Unknown payload_id: {payload_id}")
    return PayloadSummary(
        type="catalog",
        payload_id=p.payload_id,
        name=p.label,
        length_mm=float(p.length_mm),
        width_mm=float(p.width_mm),
        height_mm=float(p.height_mm),
        mass_kg=float(p.mass_kg),
        avg_power_w=float(p.avg_power_w),
        peak_power_w=float(p.peak_power_w),
        data_rate_mbps=float(p.data_rate_mbps) if p.data_rate_mbps is not None else None,
        pointing_accuracy_deg=(
            float(p.pointing_accuracy_deg) if p.pointing_accuracy_deg is not None else None
        ),
        thermal_class=p.thermal_class,
    )


def _payload_summary_from_my_payload(payload: MyPayloadInput) -> PayloadSummary:
    return PayloadSummary(
        type="my_payload",
        payload_id=None,
        name=payload.name,
        length_mm=float(payload.length_mm),
        width_mm=float(payload.width_mm),
        height_mm=float(payload.height_mm),
        mass_kg=float(payload.mass_kg),
        avg_power_w=float(payload.avg_power_w),
        peak_power_w=float(payload.peak_power_w),
        data_rate_mbps=(
            float(payload.data_rate_mbps) if payload.data_rate_mbps is not None else None
        ),
        pointing_accuracy_deg=(
            float(payload.pointing_accuracy_deg)
            if payload.pointing_accuracy_deg is not None
            else None
        ),
        thermal_class=payload.thermal_class.value if payload.thermal_class is not None else None,
    )


def _markdown_report(
    resp: SolveMissionResponse,
    payload_synthesis: MyPayloadSynthesisResponse | None,
    radiation: RadiationScreenResponse | None,
) -> str:
    lines: list[str] = []
    lines.append("# Mission Solve Report (v1)")
    lines.append("")
    lines.append("## Mission Input")
    lines.append(f"- Family: `{resp.input.family.value}`")
    lines.append(f"- ROI: `{resp.input.roi.type}`")
    if resp.input.roi.type == "region":
        lines.append(f"- Region query: `{resp.input.roi.query}`")
    lines.append(f"- Revisit target: `{resp.input.parameters.revisit_time_hours:g} h`")
    lines.append("")

    lines.append("## Payload")
    ps = resp.payload_summary
    lines.append(f"- Type: `{ps.type}`")
    if ps.payload_id:
        lines.append(f"- Payload ID: `{ps.payload_id}`")
    lines.append(f"- Name: `{ps.name}`")
    lines.append(f"- Envelope: `{ps.length_mm:g} x {ps.width_mm:g} x {ps.height_mm:g} mm`")
    lines.append(f"- Mass: `{ps.mass_kg:g} kg`")
    lines.append(f"- Power: avg `{ps.avg_power_w:g} W`, peak `{ps.peak_power_w:g} W`")
    if payload_synthesis and payload_synthesis.warnings:
        for w in payload_synthesis.warnings:
            lines.append(f"- Synthesis warning: {w}")
    lines.append("")

    lines.append("## Derived Requirements")
    d = resp.derived_requirements
    lines.append(f"- Required bus volume: `{d.required_bus_volume_u:g} U`")
    lines.append(f"- Estimated mass budget: `{d.estimated_total_mass_budget_kg:g} kg`")
    lines.append(f"- Downlink class: `{d.required_downlink_class.value}`")
    lines.append(f"- Storage: `{d.required_storage_gb:g} GB`")
    lines.append(f"- Pointing accuracy: `{d.required_pointing_accuracy_deg:g} deg`")
    lines.append("")

    if resp.constellation is not None:
        lines.append("## Constellation Estimate (v1 approx.)")
        c = resp.constellation
        lines.append(f"- Orbit family: `{c.recommended_orbit_family.value}`")
        lines.append(f"- Estimated satellites: `{c.estimated_number_of_satellites}`")
        lines.append(
            "- Walker: "
            f"`{c.recommended_candidate.total_satellites}` sats / "
            f"`{c.recommended_candidate.planes}` planes"
        )
        lines.append("")

    lines.append("## Subsystem Selection (CP-SAT)")
    s = resp.subsystem_selection
    lines.append(f"- Feasible: `{s.feasible}` (`{s.status}`)")
    if resp.chosen_bus_size_u is not None:
        lines.append(f"- Chosen bus size: `{resp.chosen_bus_size_u:g} U`")
    if s.totals is not None:
        lines.append(f"- Total mass: `{s.totals.total_mass_kg:g} kg`")
        lines.append(f"- Total avg power: `{s.totals.total_avg_power_w:g} W`")
        lines.append(f"- Total peak power: `{s.totals.total_peak_power_w:g} W`")
        lines.append(f"- Indicative cost: `{s.totals.total_cost_kusd:g} kUSD`")
    if s.margins is not None:
        lines.append(f"- Mass margin: `{s.margins.mass_margin_kg:g} kg`")
        lines.append(f"- Avg power margin: `{s.margins.avg_power_margin_w:g} W`")
        lines.append("")

    if radiation is not None:
        lines.append("## Radiation Screening (v1)")
        if radiation.flags:
            for f in radiation.flags[:10]:
                lines.append(f"- [{f.severity}] `{f.domain}:{f.item_id}`: {f.message}")
        else:
            lines.append("- No flags.")
        lines.append("")

    if resp.warnings:
        lines.append("## Warnings")
        for w in resp.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def solve_mission(req: SolveMissionRequest) -> SolveMissionResponse:
    warnings: list[str] = []
    trace: list[str] = []

    # ---- Payload normalization / synthesis ----
    payload_synthesis: MyPayloadSynthesisResponse | None = None
    normalized_payload: MyPayloadInput | None = None

    if req.input.payload.type == "catalog":
        payload_summary = _payload_summary_from_catalog(req.input.payload.payload_id)
        payload_sel = CatalogPayloadRef(payload_id=req.input.payload.payload_id)
    else:
        if req.input.payload.mission_family != req.input.family:
            raise ValueError("payload.mission_family must match input.family")

        payload_synthesis = synthesize_confidential_payload(
            MyPayloadSynthesisRequest(
                name=req.input.payload.name,
                mission_family=req.input.family,
                external_length_mm=req.input.payload.external_length_mm,
                external_width_mm=req.input.payload.external_width_mm,
                external_height_mm=req.input.payload.external_height_mm,
                mass_kg=req.input.payload.mass_kg,
                power_avg_w=req.input.payload.power_avg_w,
                power_peak_w=req.input.payload.power_peak_w,
                optional_data_rate_mbps=req.input.payload.optional_data_rate_mbps,
                optional_pointing_accuracy_deg=req.input.payload.optional_pointing_accuracy_deg,
                optional_thermal_class=req.input.payload.optional_thermal_class,
                optional_storage_required_gb=req.input.payload.optional_storage_required_gb,
                optional_gpu_required_tops=req.input.payload.optional_gpu_required_tops,
            )
        )
        normalized_payload = payload_synthesis.payload
        payload_summary = _payload_summary_from_my_payload(normalized_payload)
        payload_sel = normalized_payload

    mission_input = MissionInput(
        family=req.input.family,
        payload=payload_sel,
        roi=req.input.roi,
        parameters=req.input.parameters,
    )
    trace.append("Input validated; payload normalized.")

    # ---- Requirement derivation ----
    derived = derive_subsystem_requirements(mission_input, req.constraints)
    warnings.extend(derived.warnings)
    trace.append("Derived subsystem-level requirements.")

    # ---- Constellation estimation (best-effort) ----
    constellation = None
    try:
        constellation = estimate_constellation_v1(
            ConstellationEstimateRequest(input=mission_input, estimator=req.estimator)
        )
        warnings.extend(constellation.warnings)
        trace.append("Estimated constellation/orbit candidates (v1).")
    except ValueError as e:
        warnings.append(f"Constellation estimator failed: {e}")
        trace.append("Constellation estimator failed; continuing without constellation output.")

    # ---- Bus sizing (best-effort) ----
    bus_candidates = []
    try:
        bus_constraints = req.bus_constraints or BusCandidateConstraints(
            max_bus_size_u=req.constraints.max_bus_size_u if req.constraints else None
        )
        bus_candidates = evaluate_bus_candidates(
            BusCandidatesRequest(input=mission_input, constraints=bus_constraints)
        ).candidates
        trace.append("Evaluated bus-size candidates (packaging fitness).")
    except ValueError as e:
        warnings.append(f"Bus candidate evaluation failed: {e}")

    # ---- CP-SAT subsystem selection ----
    feasible, status, selected, optional_selected, totals, margins, s_warnings, s_trace = (
        solve_subsystems_cpsat(mission_input, derived, req.constraints)
    )
    warnings.extend(s_warnings)
    trace.extend(s_trace)
    trace.append("Subsystem selection complete (CP-SAT).")

    chosen_bus_size_u: float | None = None
    for c in selected:
        if c.domain == "structure":
            try:
                chosen_bus_size_u = float(c.metadata.get("bus_size_u"))  # type: ignore[arg-type]
            except Exception:
                chosen_bus_size_u = None
            break
    if chosen_bus_size_u is None and bus_candidates:
        chosen_bus_size_u = float(bus_candidates[0].size_u)

    subsystem_summary = SubsystemSelectionSummary(
        feasible=feasible,
        status=status,
        selected=selected,
        optional_selected=optional_selected,
        totals=totals,
        margins=margins,
        warnings=s_warnings,
        trace=s_trace,
    )

    # ---- Radiation screening (warnings-only v1) ----
    orbit_family = (
        req.radiation.orbit_family
        if req.radiation and req.radiation.orbit_family is not None
        else (
            constellation.recommended_orbit_family
            if constellation is not None
            else derived.recommended_orbit_family
        )
    )
    mission_duration_months = (
        req.radiation.mission_duration_months
        if req.radiation and req.radiation.mission_duration_months is not None
        else 24.0
    )
    shielding_mm = (
        req.radiation.shielding_assumption_mm_al
        if req.radiation and req.radiation.shielding_assumption_mm_al is not None
        else 2.0
    )
    rad_profile = RadiationMissionProfile(
        orbit_family=orbit_family,
        mission_duration_months=mission_duration_months,
        shielding_assumption_mm_al=shielding_mm,
    )
    rad_resp = screen_architecture_radiation(
        mission=rad_profile,
        selected=selected,
        optional_selected=optional_selected,
    )
    trace.append("Radiation screening complete (warnings-only v1).")

    # Include radiation flag messages in the top-level warning list for convenience.
    for f in rad_resp.flags:
        warnings.append(f"Radiation [{f.severity}] {f.domain}:{f.item_id}: {f.message}")

    resp = SolveMissionResponse(
        input=req.input,
        normalized_payload=normalized_payload,
        payload_summary=payload_summary,
        payload_synthesis=payload_synthesis,
        derived_requirements=derived,
        constellation=constellation,
        bus_candidates=bus_candidates,
        chosen_bus_size_u=chosen_bus_size_u,
        subsystem_selection=subsystem_summary,
        radiation=rad_resp,
        radiation_profile=rad_profile,
        warnings=warnings,
        trace=trace,
        report_summary_markdown="",
    )
    resp.report_summary_markdown = _markdown_report(resp, payload_synthesis, rad_resp)
    return resp
