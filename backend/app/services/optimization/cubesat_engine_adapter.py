from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from app.schemas.requirement_derivation import DerivedSubsystemRequirements, OptionalUserConstraints
from app.schemas.subsystem_selection import Margins, SelectedComponent, Totals
from app.services.optimization.cpsat_selection import solve_subsystems_cpsat
from app.services.vendor_traceability import representative_product
from solver.cubesat_data_loader import CubeSatData, load_all_data
from solver.cubesat_precompute_loader import ObjectiveCoefficients, load_all_precompute
from solver.cubesat_solver_runner import run_cubesat_solver

# backend/solver/'s bus classes go up to 27U/50U+; its tiers are an abstract
# LOW..EXTREME capability scale rather than named catalog products - this adapter
# builds SelectedComponent-shaped entries directly from that engine's own library
# data so the rest of the v1 pipeline (built around cpsat_selection.py's discrete
# catalog picks) doesn't need to change at all.


class _SubsystemSpec(NamedTuple):
    domain: str  # domain string used by the rest of the app (cpsat_selection.py's convention)
    selection_key: str  # key on backend/solver/'s "selection" dict
    library_name: str  # attribute name on CubeSatData
    mass_key: str
    avg_power_key: str
    peak_power_key: str | None  # None if the library has no peak-power field
    label: str  # display label, e.g. "EXTREME Comms"


_SUBSYSTEM_SPECS = [
    _SubsystemSpec(
        domain="eps", selection_key="eps_tier", library_name="eps_library",
        mass_key="eps_mass_kg", avg_power_key="eps_avg_self_consumption_w",
        peak_power_key=None, label="EPS",
    ),
    _SubsystemSpec(
        domain="adcs", selection_key="adcs_tier", library_name="adcs_library",
        mass_key="adcs_mass_kg", avg_power_key="adcs_avg_power_w",
        peak_power_key="adcs_peak_power_w", label="ADCS",
    ),
    _SubsystemSpec(
        domain="comm", selection_key="comms_tier", library_name="comms_library",
        mass_key="comms_mass_kg", avg_power_key="tx_avg_power_w",
        peak_power_key="tx_peak_power_w", label="Comms",
    ),
    _SubsystemSpec(
        domain="obc", selection_key="obc_tier", library_name="obc_library",
        mass_key="obc_mass_kg", avg_power_key="obc_avg_power_w",
        peak_power_key="obc_peak_power_w", label="OBC",
    ),
    _SubsystemSpec(
        domain="thermal", selection_key="thermal_tier", library_name="thermal_library",
        mass_key="thermal_mass_kg", avg_power_key="thermal_avg_power_w",
        peak_power_key="thermal_peak_power_w", label="Thermal",
    ),
    _SubsystemSpec(
        domain="propulsion", selection_key="prop_tier", library_name="propulsion_library",
        mass_key="prop_mass_kg", avg_power_key="prop_avg_power_w",
        peak_power_key="prop_peak_power_w", label="Propulsion",
    ),
]

# Maps each domain to its cost/risk proxy table key in objective_function_coefficients.json.
_PROXY_PREFIX = {
    "eps": "eps_tier",
    "adcs": "adcs_tier",
    "comm": "comms_tier",
    "obc": "obc_tier",
    "thermal": "thermal_tier",
    "propulsion": "propulsion_tier",
}

_SOURCE_DATABASE = "backend/solver (MASTER_*.json + payload_precompute_constants.json)"


@dataclass(frozen=True)
class _Ctx:
    data: CubeSatData
    objective: ObjectiveCoefficients


def _bus_component(ctx: _Ctx, bus_class: str, capacities: dict[str, float]) -> SelectedComponent:
    bus = ctx.data.bus_library[bus_class]
    cost_usd = float(ctx.objective.cost_proxy_tables["bus_class_cost_usd_proxy"][bus_class])
    return SelectedComponent(
        domain="structure",
        item_id=f"backend_solver_bus_{bus_class}",
        name=f"{bus_class} Bus",
        mass_kg=float(bus["bus_structure_mass_kg"]),
        avg_power_w=0.0,
        peak_power_w=0.0,
        cost_kusd=cost_usd / 1000.0,
        risk_points=0.0,  # backend/solver/ has no bus-class-specific risk table
        metadata={
            "bus_size_u": float(bus["u_bus"]),
            "max_total_mass_kg": capacities["M_dry_max_kg"],
            "max_payload_volume_cm3": max(0.0, capacities["U_payload_avail_u"]) * 1000.0,
            "avg_power_gen_w": capacities["P_avg_cap_w"],
            "peak_power_gen_w": capacities["P_peak_cap_w"],
            "tier": "",
            "source_database": _SOURCE_DATABASE,
        },
    )


def _subsystem_component(ctx: _Ctx, selection: dict[str, str]) -> list[SelectedComponent]:
    out: list[SelectedComponent] = []
    for spec in _SUBSYSTEM_SPECS:
        tier = selection[spec.selection_key]
        lib_entry = getattr(ctx.data, spec.library_name)[tier]
        avg_power_w = float(lib_entry[spec.avg_power_key])
        # EPS has no peak_power_w field in backend/solver/ (its peak-power constraint
        # excludes EPS self-consumption entirely) - avg is a reasonable stand-in.
        peak_power_w = float(lib_entry[spec.peak_power_key]) if spec.peak_power_key else avg_power_w

        proxy_prefix = _PROXY_PREFIX[spec.domain]
        cost_usd = float(ctx.objective.cost_proxy_tables[f"{proxy_prefix}_cost_usd_proxy"][tier])
        risk_pts = float(ctx.objective.risk_proxy_tables[f"{proxy_prefix}_risk_points"][tier])

        metadata: dict[str, object] = {"tier": tier, "source_database": _SOURCE_DATABASE}
        if spec.domain == "comm":
            metadata["downlink_mbps"] = float(lib_entry["nominal_supported_downlink_mbps"])
        if spec.domain == "adcs":
            metadata["pointing_error_deg"] = float(lib_entry["pointing_accuracy_deg"])
        rep_product = representative_product(spec.domain, tier)
        if rep_product is not None:
            metadata["representative_product"] = rep_product

        out.append(
            SelectedComponent(
                domain=spec.domain,
                item_id=f"backend_solver_{spec.domain}_{tier}",
                name=f"{tier} {spec.label}",
                mass_kg=float(lib_entry[spec.mass_key]),
                avg_power_w=avg_power_w,
                peak_power_w=peak_power_w,
                cost_kusd=cost_usd / 1000.0,
                risk_points=risk_pts,
                metadata=metadata,
            )
        )
    return out


# OptionalUserConstraints fields backend/solver/ has no way to honor, that also have a
# *real* effect on solve_subsystems_cpsat's behavior (a hard model constraint, or a
# tightened value baked into `derived` upstream of subsystem selection). If a caller
# sets any of these, routing to backend/solver/ would silently ignore an explicit ask
# (e.g. "no propulsion", a cost cap, a tightened downlink/pointing requirement) rather
# than respecting or rejecting it - fall back to solve_subsystems_cpsat instead, which
# does support them. ground_station_count is deliberately excluded: backend/solver/ is
# the one engine that consumes it.
#
# altitude_band_km is deliberately excluded too, despite existing on
# OptionalUserConstraints: confirmed by reading requirement_derivation.py, it only ever
# appends a trace note ("Constraint noted: altitude_band_km=...") and changes no
# requirement value for *either* engine - it's inert scaffolding for a not-yet-built
# feature (the fixed review's issue #6), not a real ask either engine currently honors.
# The frontend's altitude slider also always submits a default value (e.g. 500 km) even
# when the user never touches it, so treating it as "unsupported" would make
# backend/solver/ unreachable from the actual wizard - same failure mode
# _has_real_optimization_priority already guards against for optimization_priority.
_UNSUPPORTED_CONSTRAINT_FIELDS = (
    "cost_cap_kusd",
    "max_bus_size_u",
    "preferred_propulsion",
    "min_downlink_mbps",
    "max_pointing_error_deg",
)


def _has_real_optimization_priority(constraints: OptionalUserConstraints | None) -> bool:
    priority = getattr(constraints, "optimization_priority", None) if constraints else None
    return priority is not None and priority != "balanced"


def _is_routable(
    mission_input, data: CubeSatData, constraints: OptionalUserConstraints | None
) -> str | None:
    """Returns the payload_id to solve with backend/solver/, or None to fall back."""
    payload = mission_input.payload
    if getattr(payload, "type", None) != "catalog":
        return None
    payload_id = payload.payload_id
    if payload_id not in data.payloads:
        return None
    if _has_real_optimization_priority(constraints):
        return None
    if constraints is not None and any(
        getattr(constraints, field, None) is not None for field in _UNSUPPORTED_CONSTRAINT_FIELDS
    ):
        return None
    return payload_id


def solve_subsystems_via_backend_solver(
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
    data = load_all_data()
    payload_id = _is_routable(mission_input, data, constraints)
    if payload_id is None:
        return solve_subsystems_cpsat(mission_input, derived, constraints)

    ground_station_count = 1
    if constraints is not None and getattr(constraints, "ground_station_count", None):
        ground_station_count = int(constraints.ground_station_count)

    result = run_cubesat_solver(payload_id, ground_station_count)

    trace = [
        f"Engine: backend/solver/ (fixed compatibility-ordinal engine), payload_id={payload_id}, "
        f"ground_station_count={ground_station_count}.",
        f"Solver status: {result['status']}.",
    ]

    if result["status"] not in ("OPTIMAL", "FEASIBLE"):
        warnings = [
            "No feasible subsystem configuration found for constraints.",
            "Try increasing bus size / power generation, relaxing storage/downlink/pointing "
            "requirements, or raising ground_station_count.",
        ]
        return (False, result["status"].lower(), [], [], None, None, warnings, trace)

    objective = load_all_precompute().objective
    ctx = _Ctx(data=data, objective=objective)
    sel = result["selection"]
    capacities = result["capacities"]

    structure = _bus_component(ctx, sel["bus_class"], capacities)
    selected = [structure, *_subsystem_component(ctx, sel)]

    totals_raw = result["totals"]
    totals = Totals(
        total_mass_kg=totals_raw["M_total_kg"],
        total_avg_power_w=totals_raw["P_avg_total_w"],
        total_peak_power_w=totals_raw["P_peak_total_w"],
        total_cost_kusd=totals_raw["Cost_total_usd_proxy"] / 1000.0,
        total_risk_points=float(totals_raw["Risk_total_points"]),
    )
    margins = Margins(
        mass_margin_kg=capacities["M_dry_max_kg"] - totals_raw["M_total_kg"],
        avg_power_margin_w=capacities["P_avg_cap_w"] - totals_raw["P_avg_total_w"],
        peak_power_margin_w=capacities["P_peak_cap_w"] - totals_raw["P_peak_total_w"],
        bus_volume_margin_u=totals_raw["BusOversize_u"],
    )

    trace.append(
        "Budgets: "
        f"mass={totals.total_mass_kg:g} kg, avg_power={totals.total_avg_power_w:g} W, "
        f"peak_power={totals.total_peak_power_w:g} W, cost={totals.total_cost_kusd:g} kUSD, "
        f"risk={totals.total_risk_points:g} pts."
    )

    warnings: list[str] = []
    if margins.mass_margin_kg < 0.5:
        warnings.append("Tight mass margin (< 0.5 kg).")
    if margins.avg_power_margin_w < 2:
        warnings.append("Tight average power margin (< 2 W).")

    return (True, result["status"].lower(), selected, [], totals, margins, warnings, trace)
