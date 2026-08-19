from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.schemas.mission import (
    Budgets,
    ConstellationEstimate,
    DerivedRequirements,
    MissionInput,
    PlatformSummary,
    SelectedSubsystem,
    SolverSolution,
)
from app.services.catalog import Catalog, CatalogPlatform, CatalogSubsystem


@dataclass(frozen=True)
class _Choice:
    key: str
    name: str
    mass_g: int
    avg_power_mw: int
    peak_power_mw: int
    cost_usd: int
    metadata: dict[str, object]


def _kg_to_g(value: float) -> int:
    return int(round(value * 1000))


def _w_to_mw(value: float) -> int:
    return int(round(value * 1000))


def _kusd_to_usd(value: float) -> int:
    return int(round(value * 1000))


def _platform_to_choice(p: CatalogPlatform) -> _Choice:
    return _Choice(
        key=p.item_id,
        name=p.name,
        mass_g=0,
        avg_power_mw=0,
        peak_power_mw=0,
        cost_usd=_kusd_to_usd(p.cost_kusd),
        metadata={
            "bus_size_u": p.bus_size_u,
            "max_total_mass_kg": p.max_total_mass_kg,
            "max_payload_volume_cm3": p.max_payload_volume_cm3,
            "avg_power_gen_w": p.avg_power_gen_w,
            "peak_power_gen_w": p.peak_power_gen_w,
        },
    )


def _subsystem_to_choice(s: CatalogSubsystem) -> _Choice:
    return _Choice(
        key=s.item_id,
        name=s.name,
        mass_g=_kg_to_g(s.mass_kg),
        avg_power_mw=_w_to_mw(s.avg_power_w),
        peak_power_mw=_w_to_mw(s.peak_power_w),
        cost_usd=_kusd_to_usd(s.cost_kusd),
        metadata=dict(s.metadata),
    )


def _choose_one(
    model: cp_model.CpModel, choices: list[_Choice], prefix: str
) -> tuple[list[cp_model.IntVar], list[_Choice]]:
    vars_: list[cp_model.IntVar] = []
    for c in choices:
        vars_.append(model.new_bool_var(f"{prefix}_{c.key}"))
    model.add(sum(vars_) == 1)
    return vars_, choices


def _weighted_sum(vars_: list[cp_model.IntVar], weights: list[int]) -> cp_model.LinearExpr:
    return sum(v * w for v, w in zip(vars_, weights, strict=True))


def solve_subsystems(
    mission_input: MissionInput,
    requirements: DerivedRequirements,
    constellation: ConstellationEstimate,
    catalog: Catalog,
) -> SolverSolution:
    model = cp_model.CpModel()

    platforms = [_platform_to_choice(p) for p in catalog.iter_platforms()]
    if not platforms:
        raise ValueError("Catalog has no platforms")

    domain_list = ["eps", "adcs", "obc", "comm", "thermal"]
    subsystems_by_domain: dict[str, list[_Choice]] = {}
    for domain in domain_list:
        subs = [_subsystem_to_choice(s) for s in catalog.iter_subsystems(domain)]
        if not subs:
            raise ValueError(f"Catalog has no subsystems for domain: {domain}")
        subsystems_by_domain[domain] = subs

    plat_vars, plat_choices = _choose_one(model, platforms, "platform")
    domain_vars: dict[str, list[cp_model.IntVar]] = {}
    domain_choices: dict[str, list[_Choice]] = {}
    for domain in domain_list:
        vars_, choices = _choose_one(model, subsystems_by_domain[domain], domain)
        domain_vars[domain] = vars_
        domain_choices[domain] = choices

    payload_mass_g = _kg_to_g(requirements.payload_mass_kg)
    payload_avg_power_mw = _w_to_mw(requirements.payload_avg_power_w)
    payload_peak_power_mw = _w_to_mw(requirements.payload_peak_power_w)

    total_mass_g = payload_mass_g + sum(
        _weighted_sum(domain_vars[d], [c.mass_g for c in domain_choices[d]]) for d in domain_list
    )
    total_avg_power_mw = payload_avg_power_mw + sum(
        _weighted_sum(domain_vars[d], [c.avg_power_mw for c in domain_choices[d]])
        for d in domain_list
    )
    total_peak_power_mw = payload_peak_power_mw + sum(
        _weighted_sum(domain_vars[d], [c.peak_power_mw for c in domain_choices[d]])
        for d in domain_list
    )

    platform_max_mass_g = _weighted_sum(
        plat_vars,
        [_kg_to_g(float(c.metadata["max_total_mass_kg"])) for c in plat_choices],
    )
    platform_avg_power_gen_mw = _weighted_sum(
        plat_vars,
        [_w_to_mw(float(c.metadata["avg_power_gen_w"])) for c in plat_choices],
    )
    platform_peak_power_gen_mw = _weighted_sum(
        plat_vars,
        [_w_to_mw(float(c.metadata["peak_power_gen_w"])) for c in plat_choices],
    )

    model.add(total_mass_g <= platform_max_mass_g)
    model.add(total_avg_power_mw <= platform_avg_power_gen_mw)
    model.add(total_peak_power_mw <= platform_peak_power_gen_mw)

    payload_vol_scaled = int(round(requirements.payload_volume_cm3 * 10))
    platform_payload_vol_scaled = _weighted_sum(
        plat_vars,
        [int(round(float(c.metadata["max_payload_volume_cm3"]) * 10)) for c in plat_choices],
    )
    model.add(payload_vol_scaled <= platform_payload_vol_scaled)

    if requirements.min_downlink_mbps is not None:
        required = int(round(requirements.min_downlink_mbps * 100))
        comm_rates = [
            int(round(float(c.metadata.get("downlink_mbps", 0.0)) * 100))
            for c in domain_choices["comm"]
        ]
        model.add(_weighted_sum(domain_vars["comm"], comm_rates) >= required)

    if requirements.max_pointing_error_deg is not None:
        required = int(round(requirements.max_pointing_error_deg * 1000))
        adcs_errors = [
            int(round(float(c.metadata.get("pointing_error_deg", 999.0)) * 1000))
            for c in domain_choices["adcs"]
        ]
        model.add(_weighted_sum(domain_vars["adcs"], adcs_errors) <= required)

    if requirements.thermal_class.value == "sensitive":
        thermal_classes = [
            1 if c.metadata.get("class") == "enhanced" else 0 for c in domain_choices["thermal"]
        ]
        model.add(_weighted_sum(domain_vars["thermal"], thermal_classes) >= 1)

    total_cost_usd = _weighted_sum(plat_vars, [c.cost_usd for c in plat_choices]) + sum(
        _weighted_sum(domain_vars[d], [c.cost_usd for c in domain_choices[d]]) for d in domain_list
    )
    model.minimize(total_cost_usd)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0

    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("No feasible subsystem configuration found for constraints")

    platform_choice = next(
        c for v, c in zip(plat_vars, plat_choices, strict=True) if solver.value(v) == 1
    )

    platform = PlatformSummary(
        platform_id=platform_choice.key,
        name=platform_choice.name,
        bus_size_u=float(platform_choice.metadata["bus_size_u"]),
        max_total_mass_kg=float(platform_choice.metadata["max_total_mass_kg"]),
        max_payload_volume_cm3=float(platform_choice.metadata["max_payload_volume_cm3"]),
        avg_power_gen_w=float(platform_choice.metadata["avg_power_gen_w"]),
        peak_power_gen_w=float(platform_choice.metadata["peak_power_gen_w"]),
    )

    selected: list[SelectedSubsystem] = []
    selected_cost_usd = 0
    selected_mass_g = payload_mass_g
    selected_avg_power_mw = payload_avg_power_mw
    selected_peak_power_mw = payload_peak_power_mw
    for domain in domain_list:
        vlist = domain_vars[domain]
        clist = domain_choices[domain]
        choice = next(c for v, c in zip(vlist, clist, strict=True) if solver.value(v) == 1)
        selected_cost_usd += choice.cost_usd
        selected_mass_g += choice.mass_g
        selected_avg_power_mw += choice.avg_power_mw
        selected_peak_power_mw += choice.peak_power_mw
        selected.append(
            SelectedSubsystem(
                domain=domain,
                item_id=choice.key,
                name=choice.name,
                mass_kg=choice.mass_g / 1000.0,
                avg_power_w=choice.avg_power_mw / 1000.0,
                peak_power_w=choice.peak_power_mw / 1000.0,
                cost_kusd=choice.cost_usd / 1000.0,
                metadata=choice.metadata,
            )
        )

    selected_cost_usd += platform_choice.cost_usd

    total_mass_kg = selected_mass_g / 1000.0
    total_avg_power_w = selected_avg_power_mw / 1000.0
    total_peak_power_w = selected_peak_power_mw / 1000.0
    total_cost_kusd = selected_cost_usd / 1000.0

    budgets = Budgets(
        total_mass_kg=total_mass_kg,
        total_avg_power_w=total_avg_power_w,
        total_peak_power_w=total_peak_power_w,
        total_cost_kusd=total_cost_kusd,
        mass_margin_kg=platform.max_total_mass_kg - total_mass_kg,
        avg_power_margin_w=platform.avg_power_gen_w - total_avg_power_w,
        peak_power_margin_w=platform.peak_power_gen_w - total_peak_power_w,
    )

    warnings: list[str] = []
    if budgets.mass_margin_kg < 0.5:
        warnings.append("Tight mass margin (< 0.5 kg).")
    if budgets.avg_power_margin_w < 2:
        warnings.append("Tight average power margin (< 2 W).")

    trace = [
        (
            f"Constellation (approx.): {constellation.satellites} sats / "
            f"{constellation.planes} planes."
        ),
        "CP-SAT objective: minimize indicative subsystem + platform cost.",
    ]

    return SolverSolution(
        platform=platform,
        subsystems=selected,
        budgets=budgets,
        warnings=warnings,
        trace=trace,
    )
