from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.schemas.requirement_derivation import (
    DerivedSubsystemRequirements,
    DownlinkClass,
    OptionalUserConstraints,
)
from app.schemas.subsystem_selection import Margins, SelectedComponent, Totals
from app.services.catalog import Catalog, CatalogPlatform, CatalogSubsystem, get_catalog
from app.services.payload_resolver import resolve_payload_for_requirements
from app.services.units import volume_cm3_from_mm


@dataclass(frozen=True)
class _Choice:
    domain: str
    item_id: str
    name: str
    mass_g: int
    avg_power_mw: int
    peak_power_mw: int
    cost_usd: int
    risk_pts: int
    metadata: dict[str, object]


def _kg_to_g(value: float) -> int:
    return int(round(value * 1000))


def _w_to_mw(value: float) -> int:
    return int(round(value * 1000))


def _kusd_to_usd(value: float) -> int:
    return int(round(value * 1000))


def _safe_float(meta: dict[str, object], key: str, default: float) -> float:
    v = meta.get(key, default)
    try:
        return float(v)  # type: ignore[arg-type]
    except Exception:
        return default


def _platform_to_choice(p: CatalogPlatform) -> _Choice:
    meta = dict(p.metadata)
    return _Choice(
        domain="structure",
        item_id=p.item_id,
        name=p.name,
        mass_g=_kg_to_g(_safe_float(meta, "dry_mass_kg", 0.0)),
        avg_power_mw=0,
        peak_power_mw=0,
        cost_usd=_kusd_to_usd(p.cost_kusd),
        risk_pts=int(round(_safe_float(meta, "risk_points", 10.0))),
        metadata={
            **meta,
            "bus_size_u": p.bus_size_u,
            "max_total_mass_kg": p.max_total_mass_kg,
            "max_payload_volume_cm3": p.max_payload_volume_cm3,
            "avg_power_gen_w": p.avg_power_gen_w,
            "peak_power_gen_w": p.peak_power_gen_w,
        },
    )


def _subsystem_to_choice(domain: str, s: CatalogSubsystem) -> _Choice:
    meta = dict(s.metadata)
    return _Choice(
        domain=domain,
        item_id=s.item_id,
        name=s.name,
        mass_g=_kg_to_g(s.mass_kg),
        avg_power_mw=_w_to_mw(s.avg_power_w),
        peak_power_mw=_w_to_mw(s.peak_power_w),
        cost_usd=_kusd_to_usd(s.cost_kusd),
        risk_pts=int(round(_safe_float(meta, "risk_points", 10.0))),
        metadata=meta,
    )


def _choose_one(
    model: cp_model.CpModel, domain: str, choices: list[_Choice]
) -> tuple[list[cp_model.IntVar], list[_Choice]]:
    vars_: list[cp_model.IntVar] = []
    for c in choices:
        vars_.append(model.new_bool_var(f"{domain}_{c.item_id}"))
    model.add(sum(vars_) == 1)
    return vars_, choices


def _weighted_sum(vars_: list[cp_model.IntVar], weights: list[int]) -> cp_model.LinearExpr:
    return sum(v * w for v, w in zip(vars_, weights, strict=True))


def _required_downlink_mbps(cls: DownlinkClass) -> float:
    if cls.value == "low":
        return 5.0
    if cls.value == "medium":
        return 50.0
    return 100.0


def _effective_required_downlink_mbps(derived: DerivedSubsystemRequirements) -> float:
    class_requirement = _required_downlink_mbps(derived.required_downlink_class)
    if derived.required_downlink_mbps is None:
        return class_requirement
    return max(class_requirement, float(derived.required_downlink_mbps))


def _objective_weights(priority: str | None) -> dict[str, int]:
    if priority == "lowest_cost":
        return {"cost": 10, "mass": 1, "risk": 20, "slack": 1, "over_budget": 2}
    if priority == "lowest_mass":
        return {"cost": 4, "mass": 5, "risk": 20, "slack": 1, "over_budget": 4}
    if priority == "highest_performance":
        return {"cost": 3, "mass": 1, "risk": 20, "slack": 8, "over_budget": 1}
    if priority == "lowest_risk":
        return {"cost": 4, "mass": 1, "risk": 90, "slack": 2, "over_budget": 2}
    return {"cost": 5, "mass": 1, "risk": 30, "slack": 1, "over_budget": 2}


def _payload_volume_cm3_from_input(mission_input) -> float:
    p = mission_input.payload
    if p.type == "my_payload":
        return volume_cm3_from_mm(float(p.length_mm), float(p.width_mm), float(p.height_mm))
    catalog = get_catalog()
    cp = resolve_payload_for_requirements(p.payload_id, catalog)
    if not cp:
        raise ValueError(f"Unknown catalog payload_id: {p.payload_id}")
    return volume_cm3_from_mm(float(cp.length_mm), float(cp.width_mm), float(cp.height_mm))


def _precheck_feasibility(
    derived: DerivedSubsystemRequirements,
    catalog: Catalog,
    constraints: OptionalUserConstraints | None,
) -> tuple[bool, list[str], list[str]]:
    warnings: list[str] = []
    trace: list[str] = []

    required_mbps = _effective_required_downlink_mbps(derived)
    comm_ok = any(
        float(s.metadata.get("downlink_mbps", 0.0)) >= required_mbps
        for s in catalog.iter_subsystems("comm")
    )
    if not comm_ok:
        warnings.append(
            "No comm option meets required downlink class "
            f"`{derived.required_downlink_class.value}` (>= {required_mbps:g} Mbps)."
        )
        trace.append("Precheck: comm domain has no feasible options for downlink constraint.")

    obc_ok = any(
        float(s.metadata.get("storage_gb", 0.0)) >= float(derived.required_storage_gb)
        for s in catalog.iter_subsystems("obc")
    )
    if not obc_ok:
        warnings.append(
            f"No OBC option meets required storage ({derived.required_storage_gb:g} GB)."
        )
        trace.append("Precheck: obc domain has no feasible options for storage constraint.")

    adcs_ok = any(
        float(s.metadata.get("pointing_error_deg", 999.0))
        <= float(derived.required_pointing_accuracy_deg)
        for s in catalog.iter_subsystems("adcs")
    )
    if not adcs_ok:
        warnings.append(
            "No ADCS option meets required pointing accuracy "
            f"({derived.required_pointing_accuracy_deg:g} deg error or better)."
        )
        trace.append("Precheck: adcs domain has no feasible options for pointing constraint.")

    thermal_ok = True
    if derived.required_thermal_mode.value == "enhanced":
        thermal_ok = any(
            s.metadata.get("class") == "enhanced" for s in catalog.iter_subsystems("thermal")
        )
    if not thermal_ok:
        warnings.append("No thermal option meets required thermal mode `enhanced`.")
        trace.append("Precheck: thermal domain has no feasible options for enhanced mode.")

    eps_ok = any(
        float(s.metadata.get("battery_wh", 0.0)) >= float(derived.required_battery_wh)
        for s in catalog.iter_subsystems("eps")
    )
    if not eps_ok:
        warnings.append(
            f"No EPS option meets required battery energy ({derived.required_battery_wh:g} Wh)."
        )
        trace.append("Precheck: eps domain has no feasible options for battery constraint.")

    if constraints and constraints.preferred_propulsion:
        preferred = constraints.preferred_propulsion
        if preferred == "none" and derived.propulsion_recommended:
            warnings.append(
                "propulsion_preference='none' conflicts with mission-derived propulsion "
                "requirement."
            )
            trace.append("Precheck: propulsion preference conflicts with mission requirements.")
        prop_ok = any(
            s.metadata.get("type") == preferred for s in catalog.iter_subsystems("propulsion")
        )
        if not prop_ok:
            warnings.append(f"No propulsion option matches preferred_propulsion='{preferred}'.")
            trace.append("Precheck: propulsion preference has no matching catalog option.")

    required_u = float(derived.required_bus_volume_u)
    required_avg_gen = float(derived.required_eps_avg_generation_w)
    platforms = list(catalog.iter_platforms())
    structure_ok = any(
        (float(p.bus_size_u) >= required_u) and (float(p.avg_power_gen_w) >= required_avg_gen)
        for p in platforms
    )
    if constraints and constraints.max_bus_size_u is not None:
        max_u = float(constraints.max_bus_size_u)
        structure_ok = any(
            (float(p.bus_size_u) >= required_u)
            and (float(p.bus_size_u) <= max_u)
            and (float(p.avg_power_gen_w) >= required_avg_gen)
            for p in platforms
        )
        if not structure_ok:
            warnings.append(
                "No structure option fits required bus volume "
                f"({required_u:g}U) and power generation ({required_avg_gen:g}W) "
                f"under max_bus_size_u={max_u:g}U."
            )
            trace.append("Precheck: structure options eliminated by max_bus_size_u.")

    if not structure_ok and not (constraints and constraints.max_bus_size_u is not None):
        warnings.append(
            f"No structure option fits required bus volume ({required_u:g}U) and power generation "
            f"({required_avg_gen:g}W)."
        )
        trace.append(
            "Precheck: structure options cannot satisfy bus volume / generation constraints."
        )

    ok = (
        comm_ok
        and obc_ok
        and adcs_ok
        and thermal_ok
        and eps_ok
        and structure_ok
        and not any("preferred_propulsion" in warning for warning in warnings)
        and not any("propulsion_preference" in warning for warning in warnings)
    )
    return ok, warnings, trace


def solve_subsystems_cpsat(
    mission_input,
    derived: DerivedSubsystemRequirements,
    constraints: OptionalUserConstraints | None = None,
) -> tuple[
    bool,
    str,
    list[SelectedComponent],
    list[SelectedComponent],
    Totals | None,
    Margins | None,
    list[str],
    list[str],
]:
    catalog = get_catalog()
    pre_ok, pre_warnings, pre_trace = _precheck_feasibility(derived, catalog, constraints)
    if not pre_ok:
        return (
            False,
            "precheck_infeasible",
            [],
            [],
            None,
            None,
            pre_warnings,
            pre_trace,
        )

    model = cp_model.CpModel()

    platforms = [_platform_to_choice(p) for p in catalog.iter_platforms()]
    if constraints and constraints.max_bus_size_u is not None:
        max_u = float(constraints.max_bus_size_u)
        platforms = [p for p in platforms if float(p.metadata["bus_size_u"]) <= max_u]
    if not platforms:
        return (
            False,
            "no_structure_options",
            [],
            [],
            None,
            None,
            ["No structure options available under current constraints."],
            pre_trace,
        )

    domains_required = ["adcs", "eps", "obc", "comm", "thermal", "propulsion"]
    subs: dict[str, list[_Choice]] = {}
    for d in domains_required:
        choices = [_subsystem_to_choice(d, s) for s in catalog.iter_subsystems(d)]
        if not choices:
            return (
                False,
                "missing_catalog_domain",
                [],
                [],
                None,
                None,
                [f"Catalog is missing subsystem domain: {d}"],
                pre_trace,
            )
        subs[d] = choices

    rad_choices = [
        _subsystem_to_choice("radiation", s)
        for s in catalog.iter_subsystems("radiation_support_components")
    ]

    struct_vars, struct_choices = _choose_one(model, "structure", platforms)
    domain_vars: dict[str, list[cp_model.IntVar]] = {}
    domain_choices: dict[str, list[_Choice]] = {}
    for d in domains_required:
        v, c = _choose_one(model, d, subs[d])
        domain_vars[d] = v
        domain_choices[d] = c

    rad_vars: list[cp_model.IntVar] = []
    for c in rad_choices:
        rad_vars.append(model.new_bool_var(f"rad_{c.item_id}"))

    # --- Capacity and requirement constraints ---
    required_bus_u10 = int(round(float(derived.required_bus_volume_u) * 10))
    structure_bus_u10 = _weighted_sum(
        struct_vars,
        [int(round(float(c.metadata["bus_size_u"]) * 10)) for c in struct_choices],
    )
    model.add(structure_bus_u10 >= required_bus_u10)

    required_avg_gen_mw = _w_to_mw(float(derived.required_eps_avg_generation_w))
    structure_avg_gen_mw = _weighted_sum(
        struct_vars,
        [_w_to_mw(float(c.metadata["avg_power_gen_w"])) for c in struct_choices],
    )
    model.add(structure_avg_gen_mw >= required_avg_gen_mw)

    structure_peak_gen_mw = _weighted_sum(
        struct_vars,
        [_w_to_mw(float(c.metadata["peak_power_gen_w"])) for c in struct_choices],
    )

    payload_avg_mw = _w_to_mw(float(derived.payload_power_avg_w))
    payload_peak_mw = _w_to_mw(float(derived.payload_power_peak_w))
    payload_mass_g = 0
    if mission_input.payload.type == "my_payload":
        payload_mass_g = _kg_to_g(float(mission_input.payload.mass_kg))
    else:
        cp = resolve_payload_for_requirements(mission_input.payload.payload_id, catalog)
        payload_mass_g = _kg_to_g(float(cp.mass_kg)) if cp else 0

    total_mass_g = (
        payload_mass_g
        + _weighted_sum(struct_vars, [c.mass_g for c in struct_choices])
        + sum(
            _weighted_sum(domain_vars[d], [c.mass_g for c in domain_choices[d]])
            for d in domains_required
        )
        + (_weighted_sum(rad_vars, [c.mass_g for c in rad_choices]) if rad_choices else 0)
    )

    total_avg_mw = (
        payload_avg_mw
        + sum(
            _weighted_sum(domain_vars[d], [c.avg_power_mw for c in domain_choices[d]])
            for d in domains_required
        )
        + (_weighted_sum(rad_vars, [c.avg_power_mw for c in rad_choices]) if rad_choices else 0)
    )
    total_peak_mw = (
        payload_peak_mw
        + sum(
            _weighted_sum(domain_vars[d], [c.peak_power_mw for c in domain_choices[d]])
            for d in domains_required
        )
        + (_weighted_sum(rad_vars, [c.peak_power_mw for c in rad_choices]) if rad_choices else 0)
    )

    structure_max_mass_g = _weighted_sum(
        struct_vars,
        [_kg_to_g(float(c.metadata["max_total_mass_kg"])) for c in struct_choices],
    )
    model.add(total_mass_g <= structure_max_mass_g)
    model.add(total_avg_mw <= structure_avg_gen_mw)
    model.add(total_peak_mw <= structure_peak_gen_mw)

    # Payload volume capacity
    payload_vol_cm3 = _payload_volume_cm3_from_input(mission_input)
    payload_vol_scaled = int(round(payload_vol_cm3 * 10))
    structure_payload_vol_scaled = _weighted_sum(
        struct_vars,
        [int(round(float(c.metadata["max_payload_volume_cm3"]) * 10)) for c in struct_choices],
    )
    model.add(payload_vol_scaled <= structure_payload_vol_scaled)

    # ADCS pointing constraint
    req_pointing_mdeg = int(round(float(derived.required_pointing_accuracy_deg) * 1000))
    adcs_errors = [
        int(round(float(c.metadata.get("pointing_error_deg", 999.0)) * 1000))
        for c in domain_choices["adcs"]
    ]
    model.add(_weighted_sum(domain_vars["adcs"], adcs_errors) <= req_pointing_mdeg)

    # COMM downlink constraint
    req_mbps = _effective_required_downlink_mbps(derived)
    req_mbps_scaled = int(round(req_mbps * 100))
    comm_rates = [
        int(round(float(c.metadata.get("downlink_mbps", 0.0)) * 100))
        for c in domain_choices["comm"]
    ]
    model.add(_weighted_sum(domain_vars["comm"], comm_rates) >= req_mbps_scaled)

    # OBC storage constraint
    req_storage = int(round(float(derived.required_storage_gb) * 10))
    obc_storage = [
        int(round(float(c.metadata.get("storage_gb", 0.0)) * 10)) for c in domain_choices["obc"]
    ]
    model.add(_weighted_sum(domain_vars["obc"], obc_storage) >= req_storage)

    # EPS battery constraint
    req_batt = int(round(float(derived.required_battery_wh) * 10))
    eps_batt = [
        int(round(float(c.metadata.get("battery_wh", 0.0)) * 10)) for c in domain_choices["eps"]
    ]
    model.add(_weighted_sum(domain_vars["eps"], eps_batt) >= req_batt)

    # Thermal mode constraint
    if derived.required_thermal_mode.value == "enhanced":
        thermal_class = [
            1 if c.metadata.get("class") == "enhanced" else 0 for c in domain_choices["thermal"]
        ]
        model.add(_weighted_sum(domain_vars["thermal"], thermal_class) >= 1)

    # Propulsion recommendation (hard for now if derived says recommended)
    if derived.propulsion_recommended:
        prop_is_none = [
            1 if c.metadata.get("type") == "none" else 0 for c in domain_choices["propulsion"]
        ]
        model.add(_weighted_sum(domain_vars["propulsion"], prop_is_none) == 0)
    if constraints and constraints.preferred_propulsion:
        preferred = constraints.preferred_propulsion
        prop_matches = [
            1 if c.metadata.get("type") == preferred else 0 for c in domain_choices["propulsion"]
        ]
        model.add(_weighted_sum(domain_vars["propulsion"], prop_matches) == 1)

    # Cost cap
    total_cost_usd = (
        _weighted_sum(struct_vars, [c.cost_usd for c in struct_choices])
        + sum(
            _weighted_sum(domain_vars[d], [c.cost_usd for c in domain_choices[d]])
            for d in domains_required
        )
        + (_weighted_sum(rad_vars, [c.cost_usd for c in rad_choices]) if rad_choices else 0)
    )
    if constraints and constraints.cost_cap_kusd is not None:
        cap_usd = _kusd_to_usd(float(constraints.cost_cap_kusd))
        model.add(total_cost_usd <= cap_usd)

    # Risk points with optional reductions from radiation components
    base_risk = (
        _weighted_sum(struct_vars, [c.risk_pts for c in struct_choices])
        + sum(
            _weighted_sum(domain_vars[d], [c.risk_pts for c in domain_choices[d]])
            for d in domains_required
        )
        + (_weighted_sum(rad_vars, [c.risk_pts for c in rad_choices]) if rad_choices else 0)
    )
    rad_reductions = [
        int(round(_safe_float(c.metadata, "risk_reduction_points", 0.0))) for c in rad_choices
    ]
    risk_reduction = _weighted_sum(rad_vars, rad_reductions) if rad_choices else 0
    risk_total = model.new_int_var(0, 10_000, "risk_total")
    model.add(risk_total == base_risk - risk_reduction)

    # Margin slacks (to "maximize margin" via negative weight)
    mass_slack = model.new_int_var(0, 10_000_000, "mass_slack_g")
    model.add(mass_slack == structure_max_mass_g - total_mass_g)
    avg_slack = model.new_int_var(0, 10_000_000, "avg_slack_mw")
    model.add(avg_slack == structure_avg_gen_mw - total_avg_mw)
    peak_slack = model.new_int_var(0, 10_000_000, "peak_slack_mw")
    model.add(peak_slack == structure_peak_gen_mw - total_peak_mw)

    mass_slack_100g = model.new_int_var(0, 10_000_000, "mass_slack_100g")
    model.add_division_equality(mass_slack_100g, mass_slack, 100)
    avg_slack_w = model.new_int_var(0, 10_000_000, "avg_slack_w")
    model.add_division_equality(avg_slack_w, avg_slack, 1000)
    peak_slack_w = model.new_int_var(0, 10_000_000, "peak_slack_w")
    model.add_division_equality(peak_slack_w, peak_slack, 1000)

    # Over-budget penalty (soft) relative to derived estimated budget
    budget_g = _kg_to_g(float(derived.estimated_total_mass_budget_kg))
    over_budget = model.new_int_var(0, 10_000_000, "over_budget_g")
    model.add(over_budget >= total_mass_g - budget_g)
    model.add(over_budget >= 0)

    # Objective weights (transparent v1 tuning)
    weights = _objective_weights(constraints.optimization_priority if constraints else None)
    cost_w = weights["cost"]
    mass_w = weights["mass"]
    risk_w = weights["risk"]
    slack_w = weights["slack"]  # subtract slack
    over_budget_w = weights["over_budget"]

    model.minimize(
        cost_w * total_cost_usd
        + mass_w * total_mass_g
        + risk_w * risk_total
        + over_budget_w * over_budget
        - slack_w * mass_slack_100g
        - slack_w * avg_slack_w
        - slack_w * peak_slack_w
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    # Determinism: keep outputs stable across runs for the same inputs.
    solver.parameters.random_seed = 0
    solver.parameters.num_search_workers = 1

    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        warnings = [
            "No feasible subsystem configuration found for constraints.",
            "Try increasing bus size / power generation, relaxing storage/downlink/pointing "
            "requirements, or raising cost cap.",
        ]
        return (
            False,
            "infeasible",
            [],
            [],
            None,
            None,
            pre_warnings + warnings,
            pre_trace + ["CP-SAT status: infeasible."],
        )

    def _pick_one(vs: list[cp_model.IntVar], cs: list[_Choice]) -> _Choice:
        return next(c for v, c in zip(vs, cs, strict=True) if solver.value(v) == 1)

    selected: list[SelectedComponent] = []
    optional_selected: list[SelectedComponent] = []

    structure = _pick_one(struct_vars, struct_choices)
    selected.append(
        SelectedComponent(
            domain="structure",
            item_id=structure.item_id,
            name=structure.name,
            mass_kg=structure.mass_g / 1000.0,
            avg_power_w=0.0,
            peak_power_w=0.0,
            cost_kusd=structure.cost_usd / 1000.0,
            risk_points=float(structure.risk_pts),
            metadata=structure.metadata,
        )
    )

    for d in domains_required:
        c = _pick_one(domain_vars[d], domain_choices[d])
        selected.append(
            SelectedComponent(
                domain=d,
                item_id=c.item_id,
                name=c.name,
                mass_kg=c.mass_g / 1000.0,
                avg_power_w=c.avg_power_mw / 1000.0,
                peak_power_w=c.peak_power_mw / 1000.0,
                cost_kusd=c.cost_usd / 1000.0,
                risk_points=float(c.risk_pts),
                metadata=c.metadata,
            )
        )

    for v, c in zip(rad_vars, rad_choices, strict=True):
        if solver.value(v) == 1:
            optional_selected.append(
                SelectedComponent(
                    domain="radiation_support_components",
                    item_id=c.item_id,
                    name=c.name,
                    mass_kg=c.mass_g / 1000.0,
                    avg_power_w=c.avg_power_mw / 1000.0,
                    peak_power_w=c.peak_power_mw / 1000.0,
                    cost_kusd=c.cost_usd / 1000.0,
                    risk_points=float(c.risk_pts),
                    metadata=c.metadata,
                )
            )

    totals = Totals(
        total_mass_kg=solver.value(total_mass_g) / 1000.0,
        total_avg_power_w=solver.value(total_avg_mw) / 1000.0,
        total_peak_power_w=solver.value(total_peak_mw) / 1000.0,
        total_cost_kusd=solver.value(total_cost_usd) / 1000.0,
        total_risk_points=float(solver.value(risk_total)),
    )

    margins = Margins(
        mass_margin_kg=solver.value(mass_slack) / 1000.0,
        avg_power_margin_w=solver.value(avg_slack) / 1000.0,
        peak_power_margin_w=solver.value(peak_slack) / 1000.0,
        bus_volume_margin_u=(
            float(structure.metadata["bus_size_u"]) - float(derived.required_bus_volume_u)
        ),
    )

    trace = pre_trace + [
        "CP-SAT decision variables: one per required domain + optional radiation components.",
        "Objective weights: "
        f"cost={cost_w}, mass={mass_w}, risk={risk_w}, "
        f"slack={slack_w}, over_budget={over_budget_w}.",
        f"Objective value: {solver.objective_value:g}.",
        "Objective: minimize weighted cost + mass + risk + over-budget; maximize margins via "
        "slack bonuses.",
        f"Solver status: {'optimal' if status == cp_model.OPTIMAL else 'feasible'}.",
    ]

    warnings = list(pre_warnings)
    if margins.mass_margin_kg < 0.5:
        warnings.append("Tight mass margin (< 0.5 kg).")
    if margins.avg_power_margin_w < 2:
        warnings.append("Tight average power margin (< 2 W).")

    return (
        True,
        "optimal" if status == cp_model.OPTIMAL else "feasible",
        selected,
        optional_selected,
        totals,
        margins,
        warnings,
        trace,
    )
