from __future__ import annotations

from app.schemas.mission import (
    Budgets,
    ConstellationEstimate,
    DerivedRequirements,
    EngineeringTrace,
    EngineeringTraceBudget,
    EngineeringTraceConstraint,
    EngineeringTraceSelection,
    EngineeringTraceSolver,
    EngineeringTraceSubsystem,
    MissionInput,
    SolverSolution,
)


def _pass_fail_from_margin(margin: float | None) -> str:
    if margin is None:
        return "UNKNOWN"
    return "PASS" if margin >= 0 else "FAIL"


def _safe_float(meta: dict[str, object] | None, key: str) -> float | None:
    if not meta:
        return None
    v = meta.get(key)
    if v is None:
        return None
    try:
        return float(v)  # type: ignore[arg-type]
    except Exception:
        return None


def _subsystem_reasoning(
    *,
    domain: str,
    requirements: DerivedRequirements,
    subsystem_metadata: dict[str, object] | None,
    budgets: Budgets,
    bus_volume_margin_u: float | None,
) -> tuple[str | None, str | None, str | None]:
    # Keep these as lightweight, JSON-serializable strings. This is meant as an explainable
    # "backend mirror" rather than a full expert system.
    min_downlink_mbps = requirements.min_downlink_mbps
    max_pointing_error_deg = requirements.max_pointing_error_deg
    thermal_class = requirements.thermal_class.value

    selection_reason: str | None = None
    capacity_basis: str | None = None
    margin_basis: str | None = None

    if domain == "comm" and min_downlink_mbps is not None:
        downlink_mbps = _safe_float(subsystem_metadata, "downlink_mbps")
        if downlink_mbps is not None:
            selection_reason = (
                "Subsystem selection: meets downlink requirement "
                f"(required >= {min_downlink_mbps:g} Mbps; "
                f"selected provides {downlink_mbps:g} Mbps) "
                "while minimizing total configuration cost under mass/power constraints."
            )
            capacity_basis = (
                f"Downlink capacity basis: `downlink_mbps`={downlink_mbps:g} vs required "
                f"min_downlink_mbps={min_downlink_mbps:g}."
            )
        else:
            selection_reason = (
                "Subsystem selection: downlink requirement is present but selected component does "
                "not expose `downlink_mbps` metadata; selected under feasibility constraints while "
                "minimizing total configuration cost."
            )
            capacity_basis = (
                f"Downlink capacity basis: required min_downlink_mbps={min_downlink_mbps:g}."
            )

    if domain == "adcs" and max_pointing_error_deg is not None:
        pointing_error_deg = _safe_float(subsystem_metadata, "pointing_error_deg")
        if pointing_error_deg is not None:
            selection_reason = (
                "Subsystem selection: meets pointing accuracy requirement "
                f"(required <= {max_pointing_error_deg:g} deg; "
                f"selected has {pointing_error_deg:g} deg) "
                "while minimizing total configuration cost under mass/power constraints."
            )
            capacity_basis = (
                f"Pointing capacity basis: `pointing_error_deg`={pointing_error_deg:g} vs required "
                f"max_pointing_error_deg={max_pointing_error_deg:g}."
            )
        else:
            selection_reason = (
                "Subsystem selection: pointing accuracy requirement is present "
                "but selected component does not expose `pointing_error_deg` metadata; "
                "selected under feasibility constraints while minimizing total configuration cost."
            )
            capacity_basis = (
                "Pointing capacity basis: required "
                f"max_pointing_error_deg={max_pointing_error_deg:g}."
            )

    if domain == "thermal" and thermal_class == "sensitive":
        thermal_tag = (subsystem_metadata or {}).get("class")
        thermal_tag_str = str(thermal_tag) if thermal_tag is not None else None
        selection_reason = (
            "Subsystem selection: payload thermal class is `sensitive`; solver enforces an "
            "enhanced thermal option where available while minimizing total configuration cost."
        )
        capacity_basis = (
            "Thermal capacity basis: requires thermal `class`=enhanced for sensitive payloads; "
            f"selected class={thermal_tag_str!s}."
        )

    if selection_reason is None:
        selection_reason = (
            "Subsystem selection: chosen to minimize total configuration cost "
            "subject to mass/power and any available domain constraints."
        )

    margin_basis = (
        f"Margin basis: mass_margin_kg={budgets.mass_margin_kg:g} kg, "
        f"avg_power_margin_w={budgets.avg_power_margin_w:g} W, "
        f"peak_power_margin_w={budgets.peak_power_margin_w:g} W"
        + (
            f", bus_volume_margin_u={bus_volume_margin_u:g} U"
            if bus_volume_margin_u is not None
            else ""
        )
        + "."
    )

    return selection_reason, capacity_basis, margin_basis


def build_engineering_trace(
    *,
    mission_input: MissionInput,
    requirements: DerivedRequirements,
    constellation: ConstellationEstimate,
    solution: SolverSolution,
    solve_time_ms: float | None,
    preference_applications: list[dict[str, object]] | None = None,
    objective_value: float | None = None,
    objective_weights: dict[str, float] | None = None,
) -> EngineeringTrace:
    notes: list[str] = []
    if preference_applications:
        notes.append(
            "Engineering preferences are connected to solver constraints/objective; see "
            "`preferences` for applied/ignored/conflict status."
        )

    notes.append(
        "Requirement derivation: payload mass/power/volume are derived from the selected payload; "
        "downlink/pointing/thermal constraints are derived when payload metadata is present."
    )
    notes.append(
        "Constellation estimate: satellites/planes derived from revisit target and ROI mode; "
        "v1 uses this estimate for explanatory context "
        "(subsystem selection does not yet scale constraints by constellation size)."
    )
    notes.append(
        "Constraint margins: computed vs selected platform capacities "
        "(mass, average power, peak power, and payload volume where available)."
    )

    payload_id: str | None = None
    payload_source: str | None = None
    if mission_input.payload.type == "catalog":
        payload_id = mission_input.payload.payload_id
        payload_source = "catalog"
    else:
        payload_id = None
        payload_source = "my_payload"

    platform = solution.platform
    budgets = solution.budgets

    # Volume margin is not explicitly returned by the v1 solver, but the platform provides a
    # max payload volume constraint and requirements contains payload volume. Expose a consistent
    # approximation in "U" for engineering analysis (1U ~= 1000 cm^3).
    try:
        payload_vol_cm3 = float(requirements.payload_volume_cm3)
        max_payload_vol_cm3 = float(platform.max_payload_volume_cm3)
        vol_margin_u = (max_payload_vol_cm3 - payload_vol_cm3) / 1000.0
    except Exception:
        vol_margin_u = None

    trace_lines: list[str] = []
    trace_lines.extend(solution.trace or [])
    trace_lines.append(
        f"Constellation: {constellation.satellites} sats / {constellation.planes} planes."
    )
    trace_lines.append(
        "Budgets: "
        f"mass={budgets.total_mass_kg:g} kg, "
        f"avg_power={budgets.total_avg_power_w:g} W, "
        f"peak_power={budgets.total_peak_power_w:g} W, "
        f"cost={budgets.total_cost_kusd:g} kUSD."
    )

    subsystems: list[EngineeringTraceSubsystem] = []
    for s in solution.subsystems:
        selection_reason, capacity_basis, margin_basis = _subsystem_reasoning(
            domain=s.domain,
            requirements=requirements,
            subsystem_metadata=s.metadata,
            budgets=budgets,
            bus_volume_margin_u=vol_margin_u,
        )
        meta = s.metadata or {}
        subsystems.append(
            EngineeringTraceSubsystem(
                domain=s.domain,
                name=s.name,
                mass_kg=s.mass_kg,
                avg_power_w=s.avg_power_w,
                peak_power_w=s.peak_power_w,
                cost_kusd=s.cost_kusd,
                tier=meta.get("tier") or None,
                metadata=s.metadata,
                selection_reason=selection_reason,
                source_library=None,
                source_database=str(meta.get("source_database") or "catalog.json"),
                capacity_basis=capacity_basis,
                margin_basis=margin_basis,
            )
        )

    constraints: list[EngineeringTraceConstraint] = []
    constraints.append(
        EngineeringTraceConstraint(
            name="Mass Budget",
            required=budgets.total_mass_kg,
            capacity=float(platform.max_total_mass_kg),
            margin=budgets.mass_margin_kg,
            units="kg",
            status=_pass_fail_from_margin(budgets.mass_margin_kg),
        )
    )
    constraints.append(
        EngineeringTraceConstraint(
            name="Average Power Budget",
            required=budgets.total_avg_power_w,
            capacity=float(platform.avg_power_gen_w),
            margin=budgets.avg_power_margin_w,
            units="W",
            status=_pass_fail_from_margin(budgets.avg_power_margin_w),
        )
    )
    constraints.append(
        EngineeringTraceConstraint(
            name="Peak Power Budget",
            required=budgets.total_peak_power_w,
            capacity=float(platform.peak_power_gen_w),
            margin=budgets.peak_power_margin_w,
            units="W",
            status=_pass_fail_from_margin(budgets.peak_power_margin_w),
        )
    )
    if vol_margin_u is not None:
        constraints.append(
            EngineeringTraceConstraint(
                name="Payload Volume Budget",
                required=payload_vol_cm3 / 1000.0,
                capacity=max_payload_vol_cm3 / 1000.0,
                margin=vol_margin_u,
                units="U",
                status=_pass_fail_from_margin(vol_margin_u),
            )
        )

    return EngineeringTrace(
        solver=EngineeringTraceSolver(
            route_used="/api/v1/mission/solve",
            solver_name="v1_requirement_constellation_subsystem_solver",
            status="FEASIBLE",
            solve_time_ms=solve_time_ms,
            objective_value=objective_value,
            objective_weights=objective_weights,
            notes=notes,
        ),
        selection=EngineeringTraceSelection(
            platform_name=platform.name,
            bus_size_u=float(platform.bus_size_u),
            payload_id=payload_id,
            payload_source=payload_source,
            subsystem_count=len(solution.subsystems),
        ),
        budgets=EngineeringTraceBudget(
            total_mass_kg=budgets.total_mass_kg,
            total_avg_power_w=budgets.total_avg_power_w,
            total_peak_power_w=budgets.total_peak_power_w,
            total_cost_kusd=budgets.total_cost_kusd,
            mass_margin_kg=budgets.mass_margin_kg,
            avg_power_margin_w=budgets.avg_power_margin_w,
            peak_power_margin_w=budgets.peak_power_margin_w,
            bus_volume_margin_u=vol_margin_u,
        ),
        subsystems=subsystems,
        constraints=constraints,
        trace=trace_lines,
        warnings=list(solution.warnings or []),
        preferences=preference_applications or [],
    )
