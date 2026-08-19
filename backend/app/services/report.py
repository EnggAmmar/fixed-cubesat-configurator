from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.schemas.mission import (
    ConstellationEstimate,
    DerivedRequirements,
    EngineeringTrace,
    MissionInput,
    SolverSolution,
)
from app.services.branding import branding_logo_data_uri
from app.services.catalog import Catalog, CatalogPayload, CatalogPlatform, get_catalog
from app.services.payload_resolver import resolve_payload_for_requirements

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "report"
REPORT_TEMPLATE = "mission_report.html"
REPORT_CSS = "mission_report.css"

DOMAIN_ORDER = {
    "structure": 0,
    "eps": 1,
    "adcs": 2,
    "obc": 3,
    "comm": 4,
    "thermal": 5,
    "propulsion": 6,
    "radiation_support_components": 7,
}

WARNING_ORDER = {"Critical": 0, "Major": 1, "Minor": 2, "Info": 3}

NEXT_ENGINEERING_ACTIONS = [
    "Validate payload data generation and duty-cycle assumptions.",
    "Validate swath and coverage model against ROI geometry.",
    "Verify EPS energy balance across sunlight/eclipse and peak load cases.",
    "Verify optical or RF link budget with ground-station contact assumptions.",
    "Verify ADCS pointing, stability, and jitter against payload needs.",
    "Perform thermal and radiation assessment for selected orbit and lifetime.",
    "Review selected bus size against smaller feasible candidates.",
    "Export requirements for detailed design and supplier review.",
]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fmt(value: object, unit: str = "", digits: int = 2) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, int):
        return f"{value:d}{unit}"
    if isinstance(value, float):
        return f"{value:.{digits}f}{unit}"
    return f"{value}{unit}"


def _label(value: object) -> str:
    return str(value).replace("_", " ").title()


def _payload_name(mission_input: MissionInput) -> str:
    if mission_input.payload.type == "my_payload":
        return mission_input.payload.name
    return mission_input.payload.payload_id


@lru_cache(maxsize=1)
def _catalog_platforms_by_id() -> dict[str, CatalogPlatform]:
    return {platform.item_id: platform for platform in get_catalog().iter_platforms()}


@lru_cache(maxsize=1)
def _full_db_report_payload_index() -> dict[str, dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    paths = [
        root / "backend" / "data_base" / "Remote_Sensing" / "MASTER_Remote_Sensing.json",
        root / "backend" / "data_base" / "IoT_Comm" / "MASTER_IoT_Comm.json",
        root / "backend" / "data_base" / "Navigation" / "MASTER_Navigation.json",
    ]
    index: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        for variant in raw.get("variants", []):
            if not isinstance(variant, dict):
                continue
            for product in variant.get("products", []):
                if not isinstance(product, dict):
                    continue
                payload_id = str(product.get("payload_id") or "").strip()
                if payload_id:
                    index.setdefault(payload_id, product)
    return index


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _payload_catalog(
    mission_input: MissionInput, catalog: Catalog | None = None
) -> CatalogPayload | None:
    if mission_input.payload.type != "catalog":
        return None
    return resolve_payload_for_requirements(
        mission_input.payload.payload_id, catalog or get_catalog()
    )


def _payload_raw_metadata(mission_input: MissionInput) -> dict[str, Any]:
    if mission_input.payload.type != "catalog":
        return {}
    return dict(_full_db_report_payload_index().get(mission_input.payload.payload_id) or {})


def _payload_data_rate_mbps(
    mission_input: MissionInput,
    catalog_payload: CatalogPayload | None = None,
) -> float | None:
    if mission_input.payload.type == "my_payload":
        return mission_input.payload.data_rate_mbps
    if catalog_payload is not None:
        return catalog_payload.data_rate_mbps
    return None


def _payload_dimensions(
    mission_input: MissionInput,
    catalog_payload: CatalogPayload | None = None,
) -> dict[str, float | None]:
    if mission_input.payload.type == "my_payload":
        return {
            "length_mm": mission_input.payload.length_mm,
            "width_mm": mission_input.payload.width_mm,
            "height_mm": mission_input.payload.height_mm,
        }
    if catalog_payload is not None:
        return {
            "length_mm": catalog_payload.length_mm,
            "width_mm": catalog_payload.width_mm,
            "height_mm": catalog_payload.height_mm,
        }
    return {"length_mm": None, "width_mm": None, "height_mm": None}


def _report_id(mission_input: MissionInput) -> str:
    canonical = _stable_json({"input": mission_input.model_dump(mode="json")})
    return f"CFG-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12].upper()}"


def _domain_sort_key(component: Mapping[str, object]) -> tuple[int, str]:
    domain = str(component.get("domain") or "")
    return (DOMAIN_ORDER.get(domain, 999), domain)


def calculate_data_budget(
    *,
    data_rate_mbps: float | None,
    satellite_count: int | None,
    daily_data_generation_gb: float | None = None,
    duty_cycle_seconds_per_day: float | None = None,
) -> dict[str, float | None]:
    """Derive report-only data volume metrics without changing solver decisions.

    Conversion assumption: Mbps is megabits per second; GB/TB are decimal units. If a
    catalog-provided daily data estimate is available, it is preferred. Otherwise, this keeps the
    existing report behavior of using a full-day duty cycle for payload data-rate conversion and
    labels that assumption explicitly in the returned provenance fields.
    Formulae when data rate is used:
    - GB/day/satellite = Mbps * duty_cycle_seconds_per_day / 8 / 1000
    - GB/day/constellation = GB/day/satellite * satellite_count
    - TB/year = GB/day/constellation * 365 / 1000
    """
    provenance = "unavailable"
    duty_seconds = duty_cycle_seconds_per_day
    data_per_day_per_satellite_gb = daily_data_generation_gb
    if data_per_day_per_satellite_gb is not None:
        provenance = "payload catalog"
    elif data_rate_mbps is not None:
        duty_seconds = duty_seconds if duty_seconds is not None else 86400.0
        data_per_day_per_satellite_gb = data_rate_mbps * duty_seconds / 8 / 1000
        provenance = "computed from payload data rate"

    if data_per_day_per_satellite_gb is None or satellite_count is None:
        return {
            "data_per_day_per_satellite_gb": None,
            "data_per_day_constellation_gb": None,
            "annual_generated_data_tb": None,
            "data_rate_mbps": data_rate_mbps,
            "duty_cycle_seconds_per_day": duty_seconds,
            "provenance": provenance,
        }
    data_per_day_constellation_gb = data_per_day_per_satellite_gb * satellite_count
    annual_generated_data_tb = data_per_day_constellation_gb * 365 / 1000
    return {
        "data_per_day_per_satellite_gb": data_per_day_per_satellite_gb,
        "data_per_day_constellation_gb": data_per_day_constellation_gb,
        "annual_generated_data_tb": annual_generated_data_tb,
        "data_rate_mbps": data_rate_mbps,
        "duty_cycle_seconds_per_day": duty_seconds,
        "provenance": provenance,
    }


def calculate_swath_width_km(
    *, altitude_km: float | None, field_of_view_deg: float | None
) -> float | None:
    """Estimate swath width only when altitude and field-of-view are both available.

    Formula: swath_width_km = 2 * altitude_km * tan(radians(field_of_view_deg) / 2).
    This is display-only and must not affect solver decisions.
    """
    if altitude_km is None or field_of_view_deg is None:
        return None
    return 2 * altitude_km * math.tan(math.radians(field_of_view_deg) / 2)


def _budget_status(budgets: Mapping[str, float | None]) -> str:
    margins = [
        budgets.get("mass_margin_kg"),
        budgets.get("avg_power_margin_w"),
        budgets.get("peak_power_margin_w"),
        budgets.get("bus_volume_margin_u"),
    ]
    known = [m for m in margins if m is not None]
    if any(m < 0 for m in known):
        return "FAIL"
    if not known:
        return "UNKNOWN"
    if (
        (budgets.get("mass_margin_kg") is not None and budgets["mass_margin_kg"] < 0.5)
        or (budgets.get("avg_power_margin_w") is not None and budgets["avg_power_margin_w"] < 5)
        or (budgets.get("peak_power_margin_w") is not None and budgets["peak_power_margin_w"] < 5)
        or (budgets.get("bus_volume_margin_u") is not None and budgets["bus_volume_margin_u"] < 0.5)
    ):
        return "WARN"
    return "PASS"


def _provenance(value: object, source: str) -> dict[str, object]:
    return {"value": value, "source": source if value is not None else "unavailable"}


def _margin_percent(margin: float | None, capacity: float | None) -> float | None:
    if margin is None or capacity in (None, 0):
        return None
    return margin / capacity * 100.0


def _selected_subsystem(
    subsystems: Sequence[Mapping[str, Any]], domain: str
) -> Mapping[str, Any] | None:
    return next((item for item in subsystems if item.get("domain") == domain), None)


def _display_constraint(
    *,
    name: str,
    required: float | None,
    capacity: float | None,
    units: str,
    margin: float | None = None,
    pass_when_lower_is_better: bool = False,
    reason_if_missing: str,
) -> dict[str, Any]:
    if required is None or capacity is None:
        return {
            "name": name,
            "required": required,
            "capacity": capacity,
            "margin": None,
            "units": units,
            "status": "NOT_EVALUATED",
            "note": reason_if_missing,
        }
    computed_margin = margin
    if computed_margin is None:
        computed_margin = required - capacity if pass_when_lower_is_better else capacity - required
    return {
        "name": name,
        "required": required,
        "capacity": capacity,
        "margin": computed_margin,
        "units": units,
        "status": "PASS" if computed_margin >= 0 else "FAIL",
        "note": "",
    }


def _warning(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _dedupe_warnings(warnings: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for warning in warnings:
        key = (str(warning.get("severity")), str(warning.get("message")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "severity": str(warning.get("severity") or "Info"),
                "code": str(warning.get("code") or "INFO"),
                "message": str(warning.get("message") or ""),
            }
        )
    return sorted(unique, key=lambda item: (WARNING_ORDER.get(item["severity"], 99), item["code"]))


def _legacy_warning_strings(warnings: Sequence[Mapping[str, str]]) -> list[str]:
    return [f"{w['severity']}: {w['message']}" for w in warnings]


def build_mission_report_payload(
    *,
    mission_input: MissionInput,
    requirements: DerivedRequirements,
    constellation: ConstellationEstimate,
    solution: SolverSolution,
    engineering_trace: EngineeringTrace | None = None,
) -> dict[str, Any]:
    catalog_payload = _payload_catalog(mission_input)
    raw_payload = _payload_raw_metadata(mission_input)
    payload_dims = _payload_dimensions(mission_input, catalog_payload)
    data_rate_mbps = _payload_data_rate_mbps(mission_input, catalog_payload)
    daily_data_gb = _safe_float(raw_payload.get("daily_data_generation_gb"))
    field_of_view_deg = _safe_float(raw_payload.get("field_of_view_deg"))
    gsd_m = _safe_float(raw_payload.get("ground_resolution_m"))
    catalog_swath_km = _safe_float(raw_payload.get("swath_km"))
    computed_swath_km = calculate_swath_width_km(
        altitude_km=float(constellation.altitude_km),
        field_of_view_deg=field_of_view_deg,
    )
    swath_width_km = catalog_swath_km if catalog_swath_km is not None else computed_swath_km
    trace = engineering_trace.model_dump(mode="json") if engineering_trace is not None else {}
    trace_budgets = trace.get("budgets") or {}
    trace_solver = trace.get("solver") or {}
    trace_subsystems = {
        (item.get("domain"), item.get("name")): item for item in trace.get("subsystems", [])
    }

    budgets: dict[str, Any] = {
        "total_mass_kg": solution.budgets.total_mass_kg,
        "mass_capacity_kg": solution.platform.max_total_mass_kg,
        "mass_margin_kg": solution.budgets.mass_margin_kg,
        "mass_margin_percent": _margin_percent(
            solution.budgets.mass_margin_kg, solution.platform.max_total_mass_kg
        ),
        "total_avg_power_w": solution.budgets.total_avg_power_w,
        "avg_power_capacity_w": solution.platform.avg_power_gen_w,
        "avg_power_margin_w": solution.budgets.avg_power_margin_w,
        "avg_power_margin_percent": _margin_percent(
            solution.budgets.avg_power_margin_w, solution.platform.avg_power_gen_w
        ),
        "total_peak_power_w": solution.budgets.total_peak_power_w,
        "peak_power_capacity_w": solution.platform.peak_power_gen_w,
        "peak_power_margin_w": solution.budgets.peak_power_margin_w,
        "peak_power_margin_percent": _margin_percent(
            solution.budgets.peak_power_margin_w, solution.platform.peak_power_gen_w
        ),
        "payload_volume_used_u": requirements.payload_volume_cm3 / 1000.0,
        "payload_volume_capacity_u": solution.platform.max_payload_volume_cm3 / 1000.0,
        "bus_volume_margin_u": trace_budgets.get("bus_volume_margin_u"),
        "bus_volume_margin_percent": _margin_percent(
            trace_budgets.get("bus_volume_margin_u"),
            solution.platform.max_payload_volume_cm3 / 1000.0,
        ),
        "total_cost_kusd": solution.budgets.total_cost_kusd,
    }
    budgets["status"] = _budget_status(budgets)
    roi_label = mission_input.roi.query if mission_input.roi.type == "region" else "Global coverage"
    payload_source = (
        "user input" if mission_input.payload.type == "my_payload" else "payload catalog"
    )

    subsystems = []
    for selected in solution.subsystems:
        trace_item = trace_subsystems.get((selected.domain, selected.name), {})
        subsystems.append(
            {
                "domain": selected.domain,
                "item_id": selected.item_id,
                "name": selected.name,
                "mass_kg": selected.mass_kg,
                "avg_power_w": selected.avg_power_w,
                "peak_power_w": selected.peak_power_w,
                "cost_kusd": selected.cost_kusd,
                "metadata": dict(selected.metadata),
                "selection_reason": trace_item.get("selection_reason"),
                "capacity_basis": trace_item.get("capacity_basis"),
                "margin_basis": trace_item.get("margin_basis"),
                "source_database": trace_item.get("source_database"),
                "optional": False,
            }
        )
    subsystems = sorted(subsystems, key=_domain_sort_key)

    data_budget = calculate_data_budget(
        data_rate_mbps=data_rate_mbps,
        satellite_count=constellation.satellites,
        daily_data_generation_gb=daily_data_gb,
        duty_cycle_seconds_per_day=_safe_float(raw_payload.get("duty_cycle_seconds_per_day")),
    )
    required_storage_gb = None
    if mission_input.payload.type == "my_payload":
        required_storage_gb = mission_input.payload.storage_required_gb
    storage_days = _safe_float(raw_payload.get("onboard_storage_days"))
    if required_storage_gb is None and storage_days is not None:
        daily = data_budget.get("data_per_day_per_satellite_gb")
        required_storage_gb = daily * storage_days if daily is not None else None
    selected_obc = _selected_subsystem(subsystems, "obc") or {}
    selected_comm = _selected_subsystem(subsystems, "comm") or {}
    selected_adcs = _selected_subsystem(subsystems, "adcs") or {}
    selected_thermal = _selected_subsystem(subsystems, "thermal") or {}
    obc_storage_gb = _safe_float((selected_obc.get("metadata") or {}).get("storage_gb"))
    selected_downlink_mbps = _safe_float((selected_comm.get("metadata") or {}).get("downlink_mbps"))
    selected_pointing_deg = _safe_float(
        (selected_adcs.get("metadata") or {}).get("pointing_error_deg")
    )
    selected_thermal_class = (selected_thermal.get("metadata") or {}).get("class")

    data_budget.update(
        {
            "required_storage_gb": required_storage_gb,
            "selected_obc_storage_gb": obc_storage_gb,
            "storage_margin_gb": (
                obc_storage_gb - required_storage_gb
                if obc_storage_gb is not None and required_storage_gb is not None
                else None
            ),
            "downlink_class": raw_payload.get("required_downlink_class"),
            "min_downlink_mbps": requirements.min_downlink_mbps,
            "selected_downlink_mbps": selected_downlink_mbps,
            "downlink_margin_mbps": (
                selected_downlink_mbps - requirements.min_downlink_mbps
                if selected_downlink_mbps is not None and requirements.min_downlink_mbps is not None
                else None
            ),
            "contact_assumptions": "Not available",
            "conversion_note": (
                "Decimal GB/TB. Data-rate conversions use Mbps * duty seconds / 8 / 1000."
            ),
        }
    )

    platform_catalog = _catalog_platforms_by_id().get(solution.platform.platform_id)
    platform_cost_kusd = platform_catalog.cost_kusd if platform_catalog is not None else None
    subsystem_cost_kusd = sum(float(item["cost_kusd"] or 0) for item in subsystems)
    visible_cost_kusd = subsystem_cost_kusd + (platform_cost_kusd or 0)
    cost_delta_kusd = solution.budgets.total_cost_kusd - visible_cost_kusd

    bus_candidates = []
    for platform in sorted(_catalog_platforms_by_id().values(), key=lambda item: item.bus_size_u):
        feasible = (
            budgets["total_mass_kg"] <= platform.max_total_mass_kg
            and budgets["total_avg_power_w"] <= platform.avg_power_gen_w
            and budgets["total_peak_power_w"] <= platform.peak_power_gen_w
            and requirements.payload_volume_cm3 <= platform.max_payload_volume_cm3
        )
        selected = platform.item_id == solution.platform.platform_id
        if selected:
            status = "selected"
            reason = "Selected by CP-SAT minimum-cost objective under active constraints."
        elif feasible:
            status = "feasible"
            reason = "Would satisfy aggregate report constraints but was not selected by objective."
        else:
            status = "rejected"
            failed = []
            if budgets["total_mass_kg"] > platform.max_total_mass_kg:
                failed.append("mass")
            if budgets["total_avg_power_w"] > platform.avg_power_gen_w:
                failed.append("average power")
            if budgets["total_peak_power_w"] > platform.peak_power_gen_w:
                failed.append("peak power")
            if requirements.payload_volume_cm3 > platform.max_payload_volume_cm3:
                failed.append("payload volume")
            reason = "Insufficient " + ", ".join(failed) + "."
        bus_candidates.append(
            {
                "candidate_bus": platform.name,
                "bus_size_u": platform.bus_size_u,
                "status": status,
                "reason": reason,
                "cost_kusd": platform.cost_kusd,
            }
        )

    base_constraints = list(trace.get("constraints", []))
    extra_constraints = [
        _display_constraint(
            name="Downlink Capacity",
            required=requirements.min_downlink_mbps,
            capacity=selected_downlink_mbps,
            units="Mbps",
            reason_if_missing=(
                "Required downlink or selected communication capacity metadata is unavailable."
            ),
        ),
        _display_constraint(
            name="ADCS Pointing",
            required=requirements.max_pointing_error_deg,
            capacity=selected_pointing_deg,
            units="deg",
            pass_when_lower_is_better=True,
            reason_if_missing=(
                "Pointing requirement or selected ADCS pointing metadata is unavailable."
            ),
        ),
        {
            "name": "Thermal Requirement",
            "required": None,
            "capacity": None,
            "margin": None,
            "units": "class",
            "required_display": requirements.thermal_class.value,
            "capacity_display": selected_thermal_class or "Not available",
            "status": "PASS"
            if requirements.thermal_class.value == "standard"
            or selected_thermal_class == "enhanced"
            else "NOT_EVALUATED",
            "note": (
                "Categorical thermal class check from payload requirement and selected thermal "
                "metadata."
            ),
        },
        _display_constraint(
            name="Storage/Data Requirement",
            required=required_storage_gb,
            capacity=obc_storage_gb,
            units="GB",
            reason_if_missing=(
                "Required storage is unavailable or selected OBC storage metadata is unavailable."
            ),
        ),
    ]
    constraints = base_constraints + extra_constraints

    assumptions = list(constellation.notes) + list(trace_solver.get("notes") or [])
    if data_budget.get("provenance") == "computed from payload data rate":
        assumptions.append(
            "Data budget uses the existing report assumption of continuous 86400-second payload "
            "duty cycle because no duty-cycle input is available."
        )
    assumptions.append(
        "Revisit value is user-requested; constellation size is estimated by the v1 "
        "approximation model, not propagated coverage analysis."
    )

    warnings: list[dict[str, str]] = [
        _warning("Minor", "SOLVER_WARNING", warning) for warning in solution.warnings or []
    ]
    is_remote_sensing = mission_input.family.value == "remote_sensing"
    if is_remote_sensing and data_budget.get("annual_generated_data_tb") is None:
        warnings.append(
            _warning(
                "Major",
                "ANNUAL_DATA_UNAVAILABLE",
                "Annual data generation is unavailable for this remote sensing mission.",
            )
        )
    if any(value is None for value in payload_dims.values()):
        warnings.append(
            _warning(
                "Major", "PAYLOAD_DIMENSIONS_UNAVAILABLE", "Payload dimensions are unavailable."
            )
        )
    if is_remote_sensing and field_of_view_deg is None and swath_width_km is None:
        warnings.append(
            _warning(
                "Major",
                "COVERAGE_GEOMETRY_UNAVAILABLE",
                "FOV/swath coverage geometry is unavailable; coverage validity is not established.",
            )
        )
    if required_storage_gb is None:
        warnings.append(
            _warning("Major", "REQUIRED_STORAGE_UNAVAILABLE", "Required storage is unavailable.")
        )
    if data_budget.get("downlink_class") is None:
        warnings.append(
            _warning("Minor", "DOWNLINK_CLASS_UNAVAILABLE", "Downlink class is unavailable.")
        )
    warnings.append(
        _warning(
            "Major" if is_remote_sensing else "Minor",
            "RADIATION_UNAVAILABLE",
            "Radiation screening not available.",
        )
    )
    if mission_input.parameters.engineering_preferences is not None:
        warnings.append(
            _warning(
                "Info",
                "ENGINEERING_PREFS_SOLVER_CONNECTED",
                "Engineering preferences are applied to solver constraints/objective where "
                "supported; see Solver Trace for applied/ignored status.",
            )
        )
    if trace_solver.get("objective_value") is None:
        warnings.append(
            _warning(
                "Info", "OBJECTIVE_VALUE_UNAVAILABLE", "Solver objective value is unavailable."
            )
        )
    if abs(cost_delta_kusd) > 0.01:
        warnings.append(
            _warning(
                "Minor",
                "COST_COMPOSITION_INCOMPLETE",
                "Visible cost composition does not exactly match total indicative cost.",
            )
        )
    if any(item.get("status") == "NOT_EVALUATED" for item in extra_constraints):
        warnings.append(
            _warning(
                "Minor",
                "CONSTRAINTS_NOT_EVALUATED",
                "Some report-level constraints cannot be evaluated from available metadata.",
            )
        )
    warnings = _dedupe_warnings(warnings)

    margins = {
        "mass_margin_kg": budgets["mass_margin_kg"],
        "mass_margin_percent": budgets["mass_margin_percent"],
        "avg_power_margin_w": budgets["avg_power_margin_w"],
        "avg_power_margin_percent": budgets["avg_power_margin_percent"],
        "peak_power_margin_w": budgets["peak_power_margin_w"],
        "peak_power_margin_percent": budgets["peak_power_margin_percent"],
        "bus_volume_margin_u": budgets["bus_volume_margin_u"],
        "bus_volume_margin_percent": budgets["bus_volume_margin_percent"],
        "status": budgets["status"],
    }
    mission_summary = {
        "family": mission_input.family.value,
        "roi_type": mission_input.roi.type,
        "roi_label": roi_label,
        "revisit_time_hours": mission_input.parameters.revisit_time_hours,
        "solver_status": trace_solver.get("status"),
        "warning_count": len(warnings),
    }
    engineering_preferences = (
        mission_input.parameters.engineering_preferences.model_dump(mode="json")
        if mission_input.parameters.engineering_preferences is not None
        else None
    )
    report = {
        "version": "v1",
        "report_id": _report_id(mission_input),
        "mission": mission_summary,
        "mission_summary": mission_summary,
        "mission_inputs": {
            "family": _provenance(mission_input.family.value, "user input"),
            "payload_class": _provenance(mission_input.payload.type, "user input"),
            "roi": _provenance(roi_label, "user input"),
            "revisit_time_hours": _provenance(
                mission_input.parameters.revisit_time_hours, "user input"
            ),
            "engineering_preferences": _provenance(engineering_preferences, "user input"),
            "constraints": constraints,
        },
        "requirements": {
            "payload_mass_kg": _provenance(requirements.payload_mass_kg, payload_source),
            "payload_volume_cm3": _provenance(requirements.payload_volume_cm3, "computed"),
            "payload_avg_power_w": _provenance(requirements.payload_avg_power_w, payload_source),
            "payload_peak_power_w": _provenance(requirements.payload_peak_power_w, payload_source),
            "min_downlink_mbps": _provenance(requirements.min_downlink_mbps, payload_source),
            "max_pointing_error_deg": _provenance(
                requirements.max_pointing_error_deg, payload_source
            ),
            "thermal_class": _provenance(requirements.thermal_class.value, payload_source),
            "required_storage_gb": _provenance(required_storage_gb, "computed"),
        },
        "payload": {
            "name": catalog_payload.label
            if catalog_payload is not None
            else _payload_name(mission_input),
            "class": mission_input.payload.type,
            "payload_id": getattr(mission_input.payload, "payload_id", None),
            "source": payload_source,
            **payload_dims,
            "mass_kg": requirements.payload_mass_kg,
            "volume_cm3": requirements.payload_volume_cm3,
            "avg_power_w": requirements.payload_avg_power_w,
            "peak_power_w": requirements.payload_peak_power_w,
            "data_rate_mbps": data_rate_mbps,
            "pointing_accuracy_deg": requirements.max_pointing_error_deg,
            "field_of_view_deg": field_of_view_deg,
            "ground_resolution_m": gsd_m,
            "swath_width_km": swath_width_km,
            "swath_provenance": "payload catalog"
            if catalog_swath_km is not None
            else "computed approximation"
            if computed_swath_km is not None
            else "unavailable",
            "coverage_geometry_status": "available"
            if swath_width_km is not None
            else "unavailable",
            "thermal_class": requirements.thermal_class.value,
        },
        "constellation": {
            "available": True,
            "estimated_satellites": constellation.satellites,
            "orbit_family": constellation.orbit_type,
            "orbit_type": constellation.orbit_type,
            "altitude_km": constellation.altitude_km,
            "inclination_deg": None,
            "ltan": None,
            "planes": constellation.planes,
            "satellites_per_plane": constellation.satellites_per_plane,
            "revisit_basis": "user-requested target; constellation is v1 estimated",
            "assumptions": list(constellation.notes),
            "warnings": [w for w in warnings if w["code"] == "COVERAGE_GEOMETRY_UNAVAILABLE"],
        },
        "data_budget": data_budget,
        "radiation": {
            "available": False,
            "summary": "Radiation screening not available.",
            "profile": None,
            "severity": "Major" if is_remote_sensing else "Minor",
            "flags": [],
            "assumptions": [],
        },
        "platform": {
            "chosen_bus_size_u": solution.platform.bus_size_u,
            "selected_platform_name": solution.platform.name,
            "platform_id": solution.platform.platform_id,
            "max_total_mass_kg": solution.platform.max_total_mass_kg,
            "max_payload_volume_cm3": solution.platform.max_payload_volume_cm3,
            "usable_payload_volume_u": solution.platform.max_payload_volume_cm3 / 1000.0,
            "avg_power_gen_w": solution.platform.avg_power_gen_w,
            "peak_power_gen_w": solution.platform.peak_power_gen_w,
            "cost_kusd": platform_cost_kusd,
            "selection_reason": (
                "Selected by CP-SAT minimum-cost objective while satisfying active mass, power, "
                "volume, downlink, pointing, and thermal constraints."
            ),
            "bus_candidates": bus_candidates,
        },
        "bus_candidates": bus_candidates,
        "subsystems": subsystems,
        "selected_subsystems": subsystems,
        "budgets": budgets,
        "margins": margins,
        "cost_breakdown": {
            "platform_cost_kusd": platform_cost_kusd,
            "subsystem_costs": [
                {"domain": s["domain"], "name": s["name"], "cost_kusd": s["cost_kusd"]}
                for s in subsystems
            ],
            "payload_cost_kusd": None,
            "integration_margin_kusd": None,
            "visible_total_kusd": visible_cost_kusd,
            "total_indicative_cost_kusd": solution.budgets.total_cost_kusd,
            "composition_note": (
                "Total indicative cost is platform plus selected subsystem costs; payload and "
                "integration costs are not available unless separately supplied."
            ),
        },
        "solver": {
            "route": trace_solver.get("route_used"),
            "name": trace_solver.get("solver_name"),
            "status": trace_solver.get("status"),
            "objective_description": (
                "Minimize indicative platform plus subsystem cost subject to active feasibility "
                "constraints."
            ),
            "objective_value": trace_solver.get("objective_value"),
            "solve_time_ms": trace_solver.get("solve_time_ms"),
            "constraints": constraints,
            "candidate_comparison": bus_candidates,
            "warnings": _legacy_warning_strings(warnings),
            "warnings_structured": warnings,
            "assumptions": assumptions,
            "trace": list(solution.trace or []) + list(trace.get("trace", [])),
        },
        "warnings": warnings,
        "assumptions": assumptions,
        "data_completeness": {
            "missing": [
                warning["code"] for warning in warnings if "UNAVAILABLE" in warning["code"]
            ],
            "not_evaluated_constraints": [
                item["name"] for item in constraints if item.get("status") == "NOT_EVALUATED"
            ],
        },
        "timeline": [
            "Concept phase",
            "Requirements refinement",
            "Payload confirmation",
            "Architecture review",
            "AIT / validation placeholder",
            "Launch/integration placeholder",
        ],
        "next_engineering_actions": list(NEXT_ENGINEERING_ACTIONS),
    }
    report["sections"] = {
        "cover": report["mission_summary"],
        "executive_summary": report["mission_summary"],
        "mission_inputs": report["mission_inputs"],
        "derived_requirements": report["requirements"],
        "orbit_architecture": report["constellation"],
        "data_budget": report["data_budget"],
        "payload_geometry": report["payload"],
        "satellite_fleet": report["platform"],
        "subsystem_architecture": report["subsystems"],
        "budgets_and_margins": report["budgets"],
        "cost_breakdown": report["cost_breakdown"],
        "solver_trace": report["solver"],
        "warnings_assumptions": {"warnings": warnings, "assumptions": assumptions},
        "radiation": report["radiation"],
        "timeline": report["timeline"],
        "next_engineering_actions": report["next_engineering_actions"],
    }
    return report


def report_payload_json_bytes(report: Mapping[str, Any]) -> bytes:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def render_mission_report_markdown(
    mission_input: MissionInput,
    requirements: DerivedRequirements,
    constellation: ConstellationEstimate,
    solution: SolverSolution,
    engineering_trace: EngineeringTrace | None = None,
) -> str:
    report = build_mission_report_payload(
        mission_input=mission_input,
        requirements=requirements,
        constellation=constellation,
        solution=solution,
        engineering_trace=engineering_trace,
    )
    return render_mission_report_markdown_from_payload(report)


def render_mission_report_markdown_from_payload(report: Mapping[str, Any]) -> str:
    mission = report["mission"]
    payload = report["payload"]
    constellation = report["constellation"]
    platform = report["platform"]
    budgets = report["budgets"]
    lines = [
        "# Mission Report (v1)",
        "",
        "CubeSat Mission Configuration Report",
        "",
        f"Report ID: `{report['report_id']}`",
        "",
        "## Mission Input",
        f"- Family: `{mission['family']}`",
        f"- ROI: `{mission['roi_label']}`",
        f"- Revisit time target: `{mission['revisit_time_hours']:g} h`",
        "",
        "## Payload",
        f"- Name/class: `{payload['name']}` / `{payload['class']}`",
        f"- Payload ID: `{payload['payload_id'] or 'Not available'}`",
        f"- Mass: `{payload['mass_kg']:g} kg`",
        f"- Power: `{payload['avg_power_w']:g} W avg / {payload['peak_power_w']:g} W peak`",
        "",
        "## Constellation Estimate (Approx.)",
        f"- Orbit: `{constellation['orbit_type']}` @ `{constellation['altitude_km']} km`",
        f"- Constellation: `{constellation['estimated_satellites']} sats` "
        f"in `{constellation['planes']} planes`",
        f"- Satellites/plane: `{constellation['satellites_per_plane']}`",
        "",
        "## Platform",
        f"- Selected: `{platform['selected_platform_name']}` (`{platform['chosen_bus_size_u']}U`)",
        f"- Max total mass: `{platform['max_total_mass_kg']:g} kg`",
        "",
        "## Budgets",
        f"- Status: `{budgets['status']}`",
        f"- Total mass: `{budgets['total_mass_kg']:g} kg` "
        f"(margin `{budgets['mass_margin_kg']:g} kg`)",
        f"- Avg power: `{budgets['total_avg_power_w']:g} W` "
        f"(margin `{budgets['avg_power_margin_w']:g} W`)",
        f"- Peak power: `{budgets['total_peak_power_w']:g} W` "
        f"(margin `{budgets['peak_power_margin_w']:g} W`)",
        f"- Indicative cost: `{budgets['total_cost_kusd']:g} kUSD`",
        "",
        "## Selected Subsystems",
    ]
    for subsystem in report["subsystems"]:
        lines.append(
            f"- `{subsystem['domain']}`: `{subsystem['name']}` "
            f"(mass `{subsystem['mass_kg']:g} kg`, avg `{subsystem['avg_power_w']:g} W`, "
            f"cost `{subsystem['cost_kusd']:g} kUSD`)"
        )
    if report["solver"]["warnings"]:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in report["solver"]["warnings"])
    return "\n".join(lines) + "\n"


def _dimension_label(payload: Mapping[str, Any]) -> str:
    values = [payload.get("length_mm"), payload.get("width_mm"), payload.get("height_mm")]
    if any(v is None for v in values):
        return "Not available"
    return f"{values[0]:.1f} x {values[1]:.1f} x {values[2]:.1f} mm"


def _svg_satellite() -> str:
    return """<svg viewBox="0 0 360 160" width="100%" height="145">
<rect x="145" y="45" width="70" height="70" rx="8" fill="#fff" stroke="#111" stroke-width="3"/>
<rect x="55" y="55" width="75" height="50" fill="#f5f6f8" stroke="#111" stroke-width="2"/>
<rect x="230" y="55" width="75" height="50" fill="#f5f6f8" stroke="#111" stroke-width="2"/>
<line x1="130" y1="80" x2="145" y2="80" stroke="#111" stroke-width="3"/>
<line x1="215" y1="80" x2="230" y2="80" stroke="#111" stroke-width="3"/>
</svg>"""


def _svg_constellation(planes: int | None, satellites_per_plane: int | None) -> str:
    plane_count = max(1, min(int(planes or 1), 6))
    sats = max(1, min(int(satellites_per_plane or 1), 12))
    rings: list[str] = []
    dots: list[str] = []
    for plane_index in range(plane_count):
        rx = 124 - plane_index * 8
        ry = 46 + plane_index * 10
        rings.append(
            f'<ellipse cx="180" cy="95" rx="{rx}" ry="{ry}" fill="none" '
            'stroke="#20242a" stroke-width="1.6" opacity="0.38"/>'
        )
        for sat_index in range(sats):
            angle = 2 * math.pi * sat_index / sats + plane_index * 0.4
            x = 180 + rx * math.cos(angle)
            y = 95 + ry * math.sin(angle)
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#111"/>')
    return (
        '<svg viewBox="0 0 360 190" class="diagram-svg" role="img" '
        'aria-label="Constellation orbit plane diagram">'
        '<circle cx="180" cy="95" r="28" fill="#f4f6f8" stroke="#111" stroke-width="2"/>'
        + "".join(rings)
        + "".join(dots)
        + "</svg>"
    )


def _svg_data_bar(data_budget: Mapping[str, Any]) -> str:
    values = [
        data_budget.get("data_per_day_per_satellite_gb"),
        data_budget.get("data_per_day_constellation_gb"),
        data_budget.get("annual_generated_data_tb"),
    ]
    numeric = [float(v) for v in values if isinstance(v, int | float)]
    scale = max(numeric) if numeric else 1.0
    labels = ["Per satellite", "Constellation", "Annual TB"]
    bars: list[str] = []
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 30 + index * 42
        width = 0 if value is None else max(8, min(260, 260 * float(value) / scale))
        bars.append(f'<text x="24" y="{y + 15}" class="svg-label">{label}</text>')
        bars.append(f'<rect x="130" y="{y}" width="260" height="18" rx="9" fill="#edf0f4"/>')
        bars.append(f'<rect x="130" y="{y}" width="{width:.1f}" height="18" rx="9" fill="#111"/>')
        bars.append(f'<text x="404" y="{y + 14}" class="svg-value">{_fmt(value)}</text>')
    return (
        '<svg viewBox="0 0 520 160" class="diagram-svg" role="img" '
        'aria-label="Data budget bar chart">' + "".join(bars) + "</svg>"
    )


def _svg_payload_geometry(payload: Mapping[str, Any]) -> str:
    if payload.get("swath_width_km") is None:
        return (
            '<svg viewBox="0 0 360 160" class="diagram-svg" role="img" '
            'aria-label="Payload geometry unavailable">'
            '<rect x="132" y="42" width="96" height="64" rx="8" fill="#fff" '
            'stroke="#111" stroke-width="2"/>'
            '<text x="180" y="132" text-anchor="middle" class="svg-label">'
            "Coverage geometry not available</text></svg>"
        )
    return (
        '<svg viewBox="0 0 360 160" class="diagram-svg" role="img" '
        'aria-label="Payload coverage cone">'
        '<rect x="156" y="26" width="48" height="38" rx="6" fill="#fff" '
        'stroke="#111" stroke-width="2"/>'
        '<path d="M180 64 L92 134 H268 Z" fill="#f3f5f8" stroke="#111" stroke-width="2"/>'
        '<line x1="92" y1="134" x2="268" y2="134" stroke="#111" stroke-width="2"/>'
        "</svg>"
    )


def render_mission_report_html(report: Mapping[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(REPORT_TEMPLATE)
    css = (TEMPLATE_DIR / REPORT_CSS).read_text(encoding="utf-8")
    return template.render(
        report=report,
        css=css,
        logo_data_uri=branding_logo_data_uri(),
        logo_small_data_uri=branding_logo_data_uri(small=True),
        fmt=_fmt,
        label=_label,
        dimension_label=_dimension_label,
        svg_satellite=_svg_satellite,
        svg_constellation=_svg_constellation,
        svg_data_bar=_svg_data_bar,
        svg_payload_geometry=_svg_payload_geometry,
    )


class _PdfLayout:
    def __init__(self, report: Mapping[str, Any]) -> None:
        self.report = report
        self.buffer = BytesIO()
        self.canvas = canvas.Canvas(
            self.buffer,
            pagesize=landscape(A4),
            invariant=1,
            pageCompression=0,
        )
        self.width, self.height = landscape(A4)
        self.margin = 14 * mm
        self.bottom = 16 * mm
        self.content_top = self.height - 38 * mm
        self.fau_blue = colors.HexColor("#002F6C")
        self.turquoise = colors.HexColor("#34677D")
        self.status_green = colors.HexColor("#658D67")
        self.positive_accent = colors.HexColor("#97C139")
        self.grey = colors.HexColor("#B0BCC4")
        self.orange = colors.HexColor("#F5821F")
        self.charcoal = colors.black
        self.muted = self.turquoise
        self.panel = colors.HexColor("#F6F8F9")
        self.panel_alt = colors.HexColor("#EEF2F4")
        self.light_positive = colors.HexColor("#EEF6DD")
        self.light_attention = colors.HexColor("#FFF0E1")
        self.light_info = colors.HexColor("#EEF2F4")
        self.navy = self.fau_blue
        self.line = self.grey
        self.green = self.status_green
        self.green_fill = self.light_positive
        self.amber = self.orange
        self.amber_fill = self.light_attention
        self.red = self.orange
        self.red_fill = self.light_attention
        self.blue = self.fau_blue
        self.blue_fill = self.light_info

    def build(self) -> bytes:
        self._cover()
        self._mission_orbit_summary()
        self._selected_architecture()
        self._budgets_and_margins()
        self._payload_coverage_data()
        self._cost_breakdown()
        self._risk_review()
        self._solver_validation()
        self._next_actions_and_appendix()
        self.canvas.save()
        return self.buffer.getvalue()

    def _page(self, title: str, subtitle: str | None = None) -> None:
        self.canvas.setFillColor(colors.white)
        self.canvas.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        self.canvas.setFillColor(self.panel)
        self.canvas.rect(0, self.height - 27 * mm, self.width, 27 * mm, stroke=0, fill=1)
        self.canvas.setFillColor(self.fau_blue)
        self.canvas.rect(0, self.height - 28 * mm, self.width, 0.55 * mm, stroke=0, fill=1)
        self._draw_text(self.margin, self.height - 16 * mm, title, 17, bold=True)
        if subtitle:
            self._draw_text(self.margin, self.height - 23 * mm, subtitle, 8.5, color=self.muted)
        self._footer()

    def _footer(self) -> None:
        self.canvas.setFont("Helvetica", 7)
        self.canvas.setFillColor(self.grey)
        self.canvas.drawString(self.margin, 8 * mm, self._pdf_text(str(self.report["report_id"])))
        self.canvas.drawRightString(
            self.width - self.margin, 9 * mm, f"Page {self.canvas.getPageNumber()}"
        )

    def _done(self) -> None:
        self.canvas.showPage()

    @staticmethod
    def _pdf_text(value: object) -> str:
        text = str(value)
        replacements = {
            "\u2014": "-",
            "\u2013": "-",
            "\u2022": "-",
            "\u00d7": "x",
            "\u2264": "<=",
            "\u2265": ">=",
            "\u03bc": "u",
            "Not available": "Unavailable",
        }
        for source, replacement in replacements.items():
            text = text.replace(source, replacement)
        return text.encode("cp1252", errors="replace").decode("cp1252")

    def _display_value(self, value: object, unit: str = "", digits: int = 2) -> str:
        if isinstance(value, Mapping):
            if not value:
                return "Unavailable"
            return "; ".join(
                f"{_label(key)}: {self._display_value(item)}" for key, item in value.items()
            )
        if isinstance(value, list):
            return "; ".join(self._display_value(item) for item in value) or "Unavailable"
        return self._pdf_text(_fmt(value, unit, digits)).replace("Not available", "Unavailable")

    def _draw_text(
        self,
        x: float,
        y: float,
        text: object,
        size: float = 9,
        *,
        bold: bool = False,
        color: colors.Color | None = None,
    ) -> None:
        self.canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.canvas.setFillColor(color or self.charcoal)
        self.canvas.drawString(x, y, self._pdf_text(text))

    def _wrap_lines(
        self,
        text: object,
        width: float,
        size: float = 8,
        *,
        bold: bool = False,
    ) -> list[str]:
        value = self._pdf_text(text).strip()
        if not value:
            return ["Unavailable"]
        font = "Helvetica-Bold" if bold else "Helvetica"
        lines: list[str] = []
        current = ""
        for word in value.split():
            candidate = f"{current} {word}".strip()
            if stringWidth(candidate, font, size) <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            while stringWidth(current, font, size) > width and len(current) > 6:
                cut = max(6, int(len(current) * width / stringWidth(current, font, size)))
                lines.append(current[:cut])
                current = current[cut:]
        if current:
            lines.append(current)
        return lines or ["Unavailable"]

    def _wrapped_text(
        self,
        x: float,
        y: float,
        text: object,
        width: float,
        size: float = 8.5,
        *,
        bold: bool = False,
        color: colors.Color | None = None,
        leading: float | None = None,
        max_lines: int | None = None,
    ) -> float:
        lines = self._wrap_lines(text, width, size, bold=bold)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = f"{lines[-1].rstrip('.')}..."
        step = leading or (size + 3)
        for line in lines:
            self._draw_text(x, y, line, size, bold=bold, color=color)
            y -= step
        return y

    def _section_header(
        self,
        x: float,
        y: float,
        w: float,
        title: str,
        subtitle: str | None = None,
    ) -> float:
        self._draw_text(x, y, title.upper(), 9.5, bold=True, color=self.blue)
        self.canvas.setStrokeColor(self.line)
        self.canvas.setLineWidth(0.55)
        self.canvas.line(x, y - 7, x + w, y - 7)
        if subtitle:
            return self._wrapped_text(x, y - 16, subtitle, w, 7.8, color=self.muted) - 5
        return y - 20

    def _status_badge(
        self,
        x: float,
        y: float,
        text: object,
        *,
        status: object | None = None,
    ) -> float:
        label = self._pdf_text(text)
        color, fill = self._status_colors(status if status is not None else label)
        width = stringWidth(label, "Helvetica-Bold", 7.6) + 12
        self.canvas.setFillColor(fill)
        self.canvas.setStrokeColor(color)
        self.canvas.roundRect(x, y - 11, width, 14, 7, stroke=1, fill=1)
        self._draw_text(x + 6, y - 6.5, label, 7.6, bold=True, color=color)
        return width

    def _metric_card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        value: object,
        *,
        subtext: object | None = None,
        status: object | None = None,
    ) -> None:
        fill = self.panel if status is None else self._status_colors(status)[1]
        self.canvas.setFillColor(fill)
        self.canvas.setStrokeColor(self.line)
        self.canvas.roundRect(x, y - h, w, h, 6, stroke=1, fill=1)
        self._draw_text(x + 9, y - 13, label.upper(), 6.8, bold=True, color=self.muted)
        value_y = self._wrapped_text(
            x + 9,
            y - 29,
            self._display_value(value),
            w - 18,
            12.5,
            bold=True,
            max_lines=2,
        )
        if subtext is not None:
            self._wrapped_text(x + 9, value_y - 1, subtext, w - 18, 7.2, color=self.muted)

    def _cards_grid(
        self,
        items: Sequence[tuple[str, object] | tuple[str, object, object | None]],
        x: float,
        y: float,
        w: float,
        *,
        columns: int = 3,
        card_h: float = 23 * mm,
    ) -> float:
        gap = 5 * mm
        card_w = (w - gap * (columns - 1)) / columns
        for index, item in enumerate(items):
            label = item[0]
            value = item[1]
            subtext = item[2] if len(item) > 2 else None
            row, col = divmod(index, columns)
            self._metric_card(
                x + col * (card_w + gap),
                y - row * (card_h + gap),
                card_w,
                card_h,
                label,
                value,
                subtext=subtext,
            )
        rows = math.ceil(len(items) / columns) if items else 0
        return y - rows * card_h - max(0, rows - 1) * gap

    def _status_colors(self, status: object) -> tuple[colors.Color, colors.Color]:
        text = self._pdf_text(status).upper()
        if any(token in text for token in ("FAIL", "CRITICAL", "ERROR", "INFEASIBLE")):
            return self.orange, self.light_attention
        if any(token in text for token in ("WARN", "MAJOR", "NOT_EVALUATED")):
            return self.orange, self.light_attention
        if "MINOR" in text:
            return self.fau_blue, self.panel_alt
        if any(token in text for token in ("PASS", "OK", "OPTIMAL", "FEASIBLE", "SELECTED")):
            return self.status_green, self.green_fill
        if "INFO" in text:
            return self.fau_blue, self.panel_alt
        return self.muted, self.panel_alt

    def _constellation(self, x: float, y: float, w: float, h: float) -> None:
        c = self.report["constellation"]
        planes = max(1, min(int(c.get("planes") or 1), 6))
        sats = max(1, min(int(c.get("satellites_per_plane") or 1), 12))
        cx, cy = x + w / 2, y + h / 2
        self.canvas.setStrokeColor(self.grey)
        self.canvas.setLineWidth(0.8)
        for i in range(planes):
            rx, ry = (w - i * 24) / 2, (h - 24 - i * 10) / 2
            self.canvas.ellipse(cx - rx, cy - ry, cx + rx, cy + ry)
            for j in range(sats):
                angle = 2 * math.pi * j / sats + i * 0.35
                self.canvas.setFillColor(self.turquoise)
                self.canvas.circle(
                    cx + rx * math.cos(angle),
                    cy + ry * math.sin(angle),
                    2,
                    fill=1,
                )
        self.canvas.setFillColor(self.panel_alt)
        self.canvas.setStrokeColor(self.navy)
        self.canvas.circle(cx, cy, 14, fill=1)

    def _data_bars(self, x: float, y: float, w: float) -> float:
        data_budget = self.report["data_budget"]
        items = [
            ("Per satellite", data_budget.get("data_per_day_per_satellite_gb")),
            ("Constellation", data_budget.get("data_per_day_constellation_gb")),
            ("Annual TB", data_budget.get("annual_generated_data_tb")),
        ]
        numeric = [float(value) for _, value in items if isinstance(value, int | float)]
        scale = max(numeric) if numeric else 1.0
        for index, (label, value) in enumerate(items):
            bar_y = y - index * 12 * mm
            self._draw_text(x, bar_y + 5, label, 7.8, color=self.muted)
            self.canvas.setFillColor(self.panel_alt)
            self.canvas.roundRect(x + 34 * mm, bar_y, w, 5 * mm, 2.5 * mm, stroke=0, fill=1)
            if value is not None:
                width = max(4 * mm, min(w, w * float(value) / scale))
                self.canvas.setFillColor(self.blue)
                self.canvas.roundRect(
                    x + 34 * mm,
                    bar_y,
                    width,
                    5 * mm,
                    2.5 * mm,
                    stroke=0,
                    fill=1,
                )
            self._draw_text(x + 34 * mm + w + 5 * mm, bar_y + 4.5, self._display_value(value), 7.8)
        return y - len(items) * 12 * mm

    def _coverage_sketch(self, x: float, y: float) -> None:
        payload = self.report["payload"]
        self.canvas.setStrokeColor(self.navy)
        self.canvas.setFillColor(colors.white)
        self.canvas.roundRect(x + 34 * mm, y + 36 * mm, 22 * mm, 14 * mm, 4, stroke=1, fill=1)
        if payload.get("swath_width_km") is None:
            self.canvas.setFillColor(self.muted)
            self.canvas.setFont("Helvetica", 8.5)
            self.canvas.drawCentredString(x + 45 * mm, y + 21 * mm, "Coverage not evaluated")
            return
        self.canvas.setFillColor(self.panel_alt)
        path = self.canvas.beginPath()
        path.moveTo(x + 45 * mm, y + 36 * mm)
        path.lineTo(x, y)
        path.lineTo(x + 90 * mm, y)
        path.close()
        self.canvas.drawPath(path, stroke=1, fill=1)

    def _text_list(
        self,
        title: str,
        items: Sequence[object],
        y: float,
        empty: str,
        *,
        x: float | None = None,
        w: float | None = None,
        page_title: str,
    ) -> float:
        x = x if x is not None else self.margin
        w = w if w is not None else self.width - 2 * self.margin
        y = self._section_header(x, y, w, title)
        values = list(items) or [empty]
        for value in values:
            lines = self._wrap_lines(value, w - 9 * mm, 8.2)
            if y - len(lines) * 4.8 * mm < self.bottom + 4 * mm:
                self._done()
                self._page(f"{page_title} (continued)")
                y = self.content_top
            self.canvas.setFillColor(self.blue)
            self.canvas.circle(x + 2.5 * mm, y - 1, 1.5, stroke=0, fill=1)
            y = self._wrapped_text(x + 6 * mm, y, value, w - 7 * mm, 8.2, color=self.charcoal)
            y -= 3
        return y - 4 * mm

    def _draw_bullets(
        self,
        items: Sequence[object],
        x: float,
        y: float,
        w: float,
        *,
        max_items: int | None = None,
        page_title: str,
        size: float = 8.2,
    ) -> float:
        values = list(items)
        extra = 0
        if max_items is not None and len(values) > max_items:
            extra = len(values) - max_items
            values = values[:max_items]
        if extra:
            values.append(f"Additional items retained in the JSON export: {extra}")
        if not values:
            values = ["None"]

        bullet_x = x + 2.5 * mm
        text_x = x + 6.0 * mm
        line_gap = size + 2.5
        for value in values:
            lines = self._wrap_lines(value, w - 7 * mm, size)
            needed = len(lines) * line_gap + 3 * mm
            if y - needed < self.bottom + 4 * mm:
                self._done()
                self._page(f"{page_title} (continued)")
                y = self.content_top
            self.canvas.setFillColor(self.turquoise)
            self.canvas.circle(bullet_x, y - 1, 1.25, stroke=0, fill=1)
            for line in lines:
                self._draw_text(text_x, y, line, size, color=self.charcoal)
                y -= line_gap
            y -= 2.5
        return y

    def _cover(self) -> None:
        self.canvas.setFillColor(colors.white)
        self.canvas.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        self.canvas.setFillColor(self.navy)
        self.canvas.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        self.canvas.setFillColor(self.turquoise)
        self.canvas.rect(self.width * 0.56, 0, self.width * 0.44, self.height, stroke=0, fill=1)
        self._footer()
        m, p, platform = self.report["mission"], self.report["payload"], self.report["platform"]
        solver = self.report["solver"]
        budgets = self.report["budgets"]
        warnings = self.report.get("warnings") or []
        self._draw_text(
            self.margin,
            self.height - 58 * mm,
            "CubeSat Mission Configuration Report",
            30,
            bold=True,
            color=colors.white,
        )
        self._draw_text(
            self.margin,
            self.height - 70 * mm,
            "Engineering configuration snapshot for mission review",
            11,
            color=self.grey,
        )
        self._draw_text(
            self.margin,
            self.height - 84 * mm,
            f"Report ID: {self.report['report_id']}",
            10,
            bold=True,
            color=colors.white,
        )
        self._status_badge(
            self.margin,
            self.height - 96 * mm,
            f"Solver {solver.get('status') or 'Unavailable'}",
            status=solver.get("status"),
        )
        self._status_badge(
            self.margin + 44 * mm,
            self.height - 96 * mm,
            f"Budgets {budgets.get('status') or 'Unavailable'}",
            status=budgets.get("status"),
        )
        review_status = "Review notes present" if warnings else "No review notes"
        self._status_badge(
            self.margin + 88 * mm,
            self.height - 96 * mm,
            f"{len(warnings)} warnings",
            status="WARN" if warnings else "PASS",
        )
        card_y = self.height - 124 * mm
        card_w = (self.width * 0.52 - self.margin - 7 * mm) / 2
        cover_items = [
            ("Mission family", _label(m["family"])),
            ("Payload", p["name"]),
            ("ROI", m["roi_label"]),
            ("Selected bus", f"{platform['selected_platform_name']}"),
            ("Platform size", _fmt(platform["chosen_bus_size_u"], " U")),
            ("Review status", review_status),
        ]
        for index, (label, value) in enumerate(cover_items):
            row, col = divmod(index, 2)
            self._metric_card(
                self.margin + col * (card_w + 7 * mm),
                card_y - row * 27 * mm,
                card_w,
                21 * mm,
                label,
                value,
            )
        self._done()

    def _mission_orbit_summary(self) -> None:
        self._page(
            "Mission & Orbit Summary",
            "Mission inputs, derived drivers, and constellation sizing in one view.",
        )
        m = self.report["mission"]
        c = self.report["constellation"]
        y = self._cards_grid(
            [
                ("Mission family", _label(m["family"])),
                ("ROI", m["roi_label"]),
                ("Revisit target", _fmt(m["revisit_time_hours"], " h")),
                ("Orbit family/type", str(c["orbit_type"])),
                ("Altitude", _fmt(c["altitude_km"], " km")),
                ("Estimated satellites", _fmt(c["estimated_satellites"])),
            ],
            self.margin,
            self.content_top,
            self.width - 2 * self.margin,
            columns=3,
            card_h=20 * mm,
        )
        rows = []
        for key, item in self.report["mission_inputs"].items():
            if key == "constraints":
                continue
            if key == "engineering_preferences" and item.get("value") in (None, {}, []):
                continue
            rows.append(
                [
                    f"Input - {_label(key)}",
                    self._display_value(item.get("value")),
                    item.get("source"),
                ]
            )
        for key, item in self.report["requirements"].items():
            if item.get("value") is None:
                continue
            rows.append(
                [
                    f"Requirement - {_label(key)}",
                    self._display_value(item.get("value")),
                    item.get("source"),
                ]
            )
        self._wrapped_table(
            ["Review item", "Value", "Source"],
            rows,
            [76 * mm, 96 * mm, 42 * mm],
            self.margin,
            y - 8 * mm,
            "Mission & Orbit Summary",
        )
        self._done()

    def _selected_architecture(self) -> None:
        self._page(
            "Selected Architecture",
            "Selected bus, subsystems, and nearby platform candidates.",
        )
        p = self.report["payload"]
        platform = self.report["platform"]
        y = self._cards_grid(
            [
                ("Payload", str(p["name"])),
                ("Selected bus/platform", platform["selected_platform_name"]),
                ("Bus size", _fmt(platform["chosen_bus_size_u"], " U")),
                ("Mass capacity", _fmt(platform["max_total_mass_kg"], " kg")),
                ("Payload volume capacity", _fmt(platform["max_payload_volume_cm3"], " cm3")),
                ("Peak power capacity", _fmt(platform["peak_power_gen_w"], " W")),
            ],
            self.margin,
            self.content_top,
            self.width - 2 * self.margin,
            columns=3,
        )
        self._section_header(
            self.margin,
            y - 7 * mm,
            self.width - 2 * self.margin,
            "Architecture rationale",
        )
        self._wrapped_text(
            self.margin,
            y - 20 * mm,
            platform["selection_reason"],
            self.width - 2 * self.margin,
            8.5,
        )
        rows = [
            [
                str(s["domain"]),
                str(s["name"]),
                _fmt(s["mass_kg"], " kg"),
                _fmt(s["avg_power_w"], " W"),
                _fmt(s["peak_power_w"], " W"),
                _fmt(s["cost_kusd"], " kUSD"),
                str(s.get("selection_reason") or "Unavailable"),
            ]
            for s in self.report["subsystems"]
        ]
        y = self._wrapped_table(
            ["Domain", "Component", "Mass", "Avg", "Peak", "Cost", "Selection reason"],
            rows,
            [18 * mm, 40 * mm, 18 * mm, 18 * mm, 18 * mm, 21 * mm, 92 * mm],
            self.margin,
            91 * mm,
            "Selected Architecture",
        )
        candidates = [
            [
                f"{c['bus_size_u']}U",
                c["candidate_bus"],
                c["status"],
                c["reason"],
            ]
            for c in self.report["bus_candidates"][:5]
        ]
        self._wrapped_table(
            ["Bus", "Platform", "Status", "Reason"],
            candidates,
            [18 * mm, 48 * mm, 24 * mm, 128 * mm],
            self.margin,
            y,
            "Selected Architecture",
        )
        self._done()

    def _budgets_and_margins(self) -> None:
        self._page(
            "Engineering Budgets & Margins",
            "Mass, power, payload volume, and cost closure for the selected architecture.",
        )
        b = self.report["budgets"]
        self._status_badge(
            self.width - self.margin - 45 * mm,
            self.height - 16 * mm,
            f"Budget status: {b['status']}",
            status=b["status"],
        )
        y = self._cards_grid(
            [
                ("Total mass", _fmt(b["total_mass_kg"], " kg")),
                ("Mass margin", _fmt(b["mass_margin_kg"], " kg")),
                ("Average power", _fmt(b["total_avg_power_w"], " W")),
                ("Average power margin", _fmt(b["avg_power_margin_w"], " W")),
                ("Peak power", _fmt(b["total_peak_power_w"], " W")),
                ("Peak power margin", _fmt(b["peak_power_margin_w"], " W")),
                ("Payload volume", _fmt(b["payload_volume_used_u"], " U")),
                ("Bus volume margin", _fmt(b["bus_volume_margin_u"], " U")),
                ("Indicative cost", _fmt(b["total_cost_kusd"], " kUSD")),
            ],
            self.margin,
            self.content_top,
            self.width - 2 * self.margin,
            columns=3,
        )
        bar_y = y - 6 * mm
        for label, used, cap, margin, unit in [
            ("Mass", b["total_mass_kg"], b["mass_capacity_kg"], b["mass_margin_kg"], "kg"),
            (
                "Average power",
                b["total_avg_power_w"],
                b["avg_power_capacity_w"],
                b["avg_power_margin_w"],
                "W",
            ),
            (
                "Peak power",
                b["total_peak_power_w"],
                b["peak_power_capacity_w"],
                b["peak_power_margin_w"],
                "W",
            ),
            (
                "Payload volume",
                b["payload_volume_used_u"],
                b["payload_volume_capacity_u"],
                b["bus_volume_margin_u"],
                "U",
            ),
        ]:
            bar_y = self._margin_bar(
                self.margin,
                bar_y,
                self.width - 2 * self.margin,
                label,
                used,
                cap,
                margin,
                unit,
            )
        self._done()

    def _payload_coverage_data(self) -> None:
        self._page(
            "Payload, Coverage & Data Budget",
            "Payload envelope, coverage fields, storage, and downlink review.",
        )
        p = self.report["payload"]
        d = self.report["data_budget"]
        y = self._cards_grid(
            [
                ("Payload dimensions", _dimension_label(p)),
                ("Payload mass", _fmt(p["mass_kg"], " kg")),
                ("Payload power", f"{_fmt(p['avg_power_w'], ' W')} avg"),
                ("Swath width", _fmt(p["swath_width_km"], " km")),
                ("Ground resolution", _fmt(p["ground_resolution_m"], " m")),
                ("Pointing requirement", _fmt(p["pointing_accuracy_deg"], " deg")),
                ("Annual data", _fmt(d["annual_generated_data_tb"], " TB/year")),
                ("Required storage", _fmt(d["required_storage_gb"], " GB")),
                ("Selected downlink", _fmt(d["selected_downlink_mbps"], " Mbps")),
            ],
            self.margin,
            self.content_top,
            self.width - 2 * self.margin,
            columns=3,
        )
        left_w = (self.width - 2 * self.margin - 8 * mm) * 0.48
        right_x = self.margin + left_w + 8 * mm
        right_w = self.width - right_x - self.margin
        y_left = self._section_header(self.margin, y - 8 * mm, left_w, "Coverage geometry")
        self._coverage_sketch(self.margin + 12 * mm, y_left - 56 * mm)
        self._wrapped_text(
            self.margin,
            y_left - 65 * mm,
            f"Geometry status: {p['coverage_geometry_status']}; provenance: "
            f"{p['swath_provenance']}.",
            left_w,
            8.2,
            color=self.muted,
        )
        y_right = self._section_header(right_x, y - 8 * mm, right_w, "Data budget")
        self._data_bars(right_x, y_right - 5 * mm, right_w - 56 * mm)
        self._wrapped_text(
            right_x,
            y_right - 48 * mm,
            f"{d['conversion_note']} Provenance: {d['provenance']}.",
            right_w,
            8.0,
            color=self.muted,
        )
        self._done()

    def _wrapped_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[object]],
        widths: Sequence[float],
        x: float,
        y: float,
        page_title: str,
    ) -> float:
        table_w = sum(widths)

        def draw_header(top_y: float) -> float:
            self.canvas.setFillColor(self.blue_fill)
            self.canvas.setStrokeColor(self.grey)
            self.canvas.roundRect(x, top_y - 7 * mm, table_w, 7 * mm, 3, stroke=1, fill=1)
            cell_x = x
            for header, width in zip(headers, widths, strict=True):
                self._wrapped_text(
                    cell_x + 2 * mm,
                    top_y - 4.7 * mm,
                    header,
                    width - 4 * mm,
                    7.2,
                    bold=True,
                    color=self.navy,
                    max_lines=1,
                )
                cell_x += width
            return top_y - 7 * mm

        y = draw_header(y)
        for index, row in enumerate(rows):
            cell_lines = [
                self._wrap_lines(value, width - 4 * mm, 7.0)
                for value, width in zip(row, widths, strict=True)
            ]
            max_lines = max(len(lines) for lines in cell_lines) if cell_lines else 1
            row_h = max(7 * mm, max_lines * 3.6 * mm + 4.2 * mm)
            if y - row_h < self.bottom + 5 * mm:
                self._done()
                self._page(f"{page_title} (continued)")
                y = draw_header(self.content_top)
            self.canvas.setFillColor(colors.white if index % 2 == 0 else self.panel)
            self.canvas.setStrokeColor(self.grey)
            self.canvas.rect(x, y - row_h, table_w, row_h, stroke=1, fill=1)
            cell_x = x
            for lines, width in zip(cell_lines, widths, strict=True):
                text_y = y - 3.8 * mm
                for line in lines:
                    self._draw_text(cell_x + 2 * mm, text_y, line, 7.0, color=self.charcoal)
                    text_y -= 3.6 * mm
                cell_x += width
            y -= row_h
        return y - 4 * mm

    def _margin_bar(
        self,
        x: float,
        y: float,
        w: float,
        label: str,
        used: object,
        capacity: object,
        margin_value: object,
        unit: str,
    ) -> float:
        used_f = _safe_float(used)
        cap_f = _safe_float(capacity)
        margin_f = _safe_float(margin_value)
        ratio = (
            0.0 if used_f is None or cap_f in (None, 0.0) else max(0.0, min(1.0, used_f / cap_f))
        )
        status = "PASS" if margin_f is None or margin_f >= 0 else "FAIL"
        self._draw_text(x, y, label, 8.8, bold=True)
        summary = (
            f"{self._display_value(used, f' {unit}')} used / "
            f"{self._display_value(capacity, f' {unit}')} capacity; "
            f"margin {self._display_value(margin_value, f' {unit}')}"
        )
        self._draw_text(x + 42 * mm, y, summary, 8.0, color=self.muted)
        self.canvas.setFillColor(self.panel_alt)
        self.canvas.roundRect(x + 42 * mm, y - 9 * mm, w - 58 * mm, 5 * mm, 2.5 * mm, 0, 1)
        self.canvas.setFillColor(self.green if status == "PASS" else self.red)
        self.canvas.roundRect(
            x + 42 * mm,
            y - 9 * mm,
            (w - 58 * mm) * ratio,
            5 * mm,
            2.5 * mm,
            0,
            1,
        )
        self._status_badge(x + w - 13 * mm, y, status, status=status)
        return y - 15 * mm

    def _cost_breakdown(self) -> None:
        self._page(
            "Cost Summary",
            "Indicative platform and subsystem cost composition for the selected concept.",
        )
        cost = self.report["cost_breakdown"]
        rows = [["Platform", _fmt(cost.get("platform_cost_kusd"), " kUSD")]]
        rows.extend(
            [
                [f"{item['domain']} - {item['name']}", _fmt(item.get("cost_kusd"), " kUSD")]
                for item in cost.get("subsystem_costs", [])
            ]
        )
        rows.extend(
            [
                ["Payload", _fmt(cost.get("payload_cost_kusd"), " kUSD")],
                ["Integration/system margin", _fmt(cost.get("integration_margin_kusd"), " kUSD")],
                [
                    "Total indicative cost",
                    _fmt(cost.get("total_indicative_cost_kusd"), " kUSD"),
                ],
            ]
        )
        left_w = 130 * mm
        self._wrapped_table(
            ["Cost item", "Value"],
            rows,
            [95 * mm, 32 * mm],
            self.margin,
            self.content_top,
            "Cost Summary",
        )
        y = self._section_header(self.margin + left_w + 10 * mm, self.content_top, 88 * mm, "Notes")
        self._wrapped_text(
            self.margin + left_w + 10 * mm,
            y,
            cost["composition_note"],
            88 * mm,
            8.3,
            color=self.charcoal,
        )
        self._done()

    def _solver_validation(self) -> None:
        self._page(
            "Solver / Validation Summary",
            "Constraint checks and solver metadata without changing the JSON report payload.",
        )
        solver = self.report["solver"]
        y = self._cards_grid(
            [
                ("Solver", solver["name"] or "Unavailable"),
                ("Solver status", solver["status"] or "Unavailable"),
                ("Objective value", _fmt(solver["objective_value"])),
                ("Solve time", _fmt(solver["solve_time_ms"], " ms")),
                ("Constraints", str(len(solver.get("constraints") or []))),
                ("Trace lines", str(len(solver.get("trace") or []))),
            ],
            self.margin,
            self.content_top,
            self.width - 2 * self.margin,
            columns=3,
        )
        rows = [
            [
                str(c.get("name")),
                str(c.get("required_display") or _fmt(c.get("required"))),
                str(c.get("capacity_display") or _fmt(c.get("capacity"))),
                f"{_fmt(c.get('margin'))} {c.get('units') or ''}".strip(),
                str(c.get("status")),
            ]
            for c in solver.get("constraints", [])
        ]
        y = self._wrapped_table(
            ["Constraint", "Required", "Capacity", "Margin", "Status"],
            rows,
            [60 * mm, 40 * mm, 40 * mm, 40 * mm, 31 * mm],
            self.margin,
            y - 8 * mm,
            "Solver / Validation Summary",
        )
        trace_lines = solver.get("trace", [])[:5]
        if trace_lines and y > 54 * mm:
            self._text_list(
                "Validation trace",
                trace_lines,
                y,
                "No trace entries.",
                page_title="Solver / Validation Summary",
            )
        self._done()

    def _format_warning_for_display(self, warning: Mapping[str, str]) -> tuple[str, str, str]:
        severity = str(warning.get("severity") or "Info")
        code = str(warning.get("code") or "INFO")
        message = str(warning.get("message") or "")
        return severity, self._pdf_text(message), code

    def _pdf_warning_items(self) -> list[tuple[str, str, str]]:
        grouped: list[tuple[str, str, str]] = []
        radiation_messages: list[str] = []
        for warning in self.report["warnings"]:
            severity, message, code = self._format_warning_for_display(warning)
            if message.startswith("Radiation ["):
                radiation_messages.append(message)
                continue
            grouped.append((severity, message, code))
        if radiation_messages:
            missing = sum("No radiation record found" in msg for msg in radiation_messages)
            risk = sum("Radiation risk" in msg for msg in radiation_messages)
            details = []
            if risk:
                details.append(f"{risk} TID/class screening note{'s' if risk != 1 else ''}")
            if missing:
                details.append(f"{missing} metadata gap{'s' if missing != 1 else ''}")
            detail_text = "; ".join(details) or f"{len(radiation_messages)} component notes"
            grouped.append(
                (
                    "Minor",
                    "Radiation component review: "
                    f"{len(radiation_messages)} component-level note"
                    f"{'s' if len(radiation_messages) != 1 else ''} ({detail_text}). "
                    "Component details are retained in the JSON export.",
                    f"SOLVER_WARNING x{len(radiation_messages)}",
                )
            )
        return grouped

    def _risk_review(self) -> None:
        self._page(
            "Warnings, Risk & Data Completeness",
            "Engineering review notes grouped by severity, with raw codes kept secondary.",
        )
        warnings = self._pdf_warning_items()
        severity_groups = ["Critical", "Major", "Minor", "Info"]
        x = self.margin
        y = self.content_top
        col_gap = 7 * mm
        left_w = (self.width - 2 * self.margin - col_gap) * 0.62
        right_x = x + left_w + col_gap
        right_w = self.width - right_x - self.margin
        y = self._section_header(x, y, left_w, "Risk review notes")
        if not warnings:
            self._status_badge(x, y, "No report warnings", status="PASS")
            y -= 14 * mm
        for severity in severity_groups:
            items = [(msg, code) for sev, msg, code in warnings if sev == severity]
            if not items:
                continue
            color, fill = self._status_colors(severity)
            self.canvas.setFillColor(fill)
            self.canvas.setStrokeColor(color)
            self.canvas.roundRect(x, y - 7 * mm, left_w, 8 * mm, 4, stroke=1, fill=1)
            self._draw_text(x + 3 * mm, y - 4.5 * mm, severity, 8, bold=True, color=color)
            y -= 11 * mm
            for message, code in items:
                lines = self._wrap_lines(message, left_w - 8 * mm, 8.0)
                needed = len(lines) * 4.2 * mm + 7 * mm
                if y - needed < self.bottom:
                    self._done()
                    self._page("Warnings, Risk & Data Completeness (continued)")
                    y = self.content_top
                y = self._wrapped_text(x + 4 * mm, y, message, left_w - 8 * mm, 8.0)
                self._draw_text(x + 4 * mm, y + 1, f"Code: {code}", 6.8, color=self.muted)
                y -= 7 * mm

        completeness = self.report.get("data_completeness") or {}
        y2 = self._section_header(right_x, self.content_top, right_w, "Data completeness")
        missing = completeness.get("missing") or []
        not_evaluated = completeness.get("not_evaluated_constraints") or []
        review_cards = [
            ("Missing data fields", str(len(missing))),
            ("Not evaluated checks", str(len(not_evaluated))),
            ("Total warnings", str(len(warnings))),
        ]
        detail_y = self._cards_grid(review_cards, right_x, y2, right_w, columns=1, card_h=16 * mm)
        detail_y = self._section_header(
            right_x,
            detail_y - 6 * mm,
            right_w,
            "Missing fields",
        )
        detail_y = self._draw_bullets(
            [str(item) for item in missing] or ["None"],
            right_x,
            detail_y,
            right_w,
            max_items=5,
            page_title="Warnings, Risk & Data Completeness",
            size=7.5,
        )
        if not_evaluated:
            detail_y = self._section_header(right_x, detail_y - 2 * mm, right_w, "Not evaluated")
            detail_y = self._draw_bullets(
                [str(item) for item in not_evaluated],
                right_x,
                detail_y,
                right_w,
                max_items=4,
                page_title="Warnings, Risk & Data Completeness",
                size=7.5,
            )
        radiation = self.report.get("radiation") or {}
        radiation_y = detail_y - 2 * mm
        if radiation_y < 42 * mm:
            self._done()
            self._page("Warnings, Risk & Data Completeness (continued)")
            radiation_y = self.content_top
            right_x = self.margin
            right_w = self.width - 2 * self.margin
        y3 = self._section_header(right_x, radiation_y, right_w, "Radiation review")
        self._wrapped_text(
            right_x,
            y3,
            radiation.get("summary") or "Radiation screening unavailable.",
            right_w,
            8.0,
            color=self.charcoal,
        )
        self._done()

    def _next_actions_and_appendix(self) -> None:
        self._page(
            "Next Engineering Actions",
            "Roadmap for follow-up analysis, supplier review, and design closure.",
        )
        actions = self.report.get("next_engineering_actions", [])
        left_w = (self.width - 2 * self.margin - 8 * mm) * 0.55
        right_x = self.margin + left_w + 8 * mm
        y_left = self._section_header(self.margin, self.content_top, left_w, "Review roadmap")
        y_left = self._draw_bullets(
            actions or ["No next actions provided."],
            self.margin,
            y_left,
            left_w,
            max_items=8,
            page_title="Next Engineering Actions",
            size=8.1,
        )

        assumptions = list(self.report.get("assumptions", []))
        key_assumptions = assumptions[:7]
        if len(assumptions) > len(key_assumptions):
            key_assumptions.append("Additional assumptions are retained in the JSON export.")
        y_right = self._section_header(
            right_x,
            self.content_top,
            self.width - right_x - self.margin,
            "Key assumptions",
        )
        self._draw_bullets(
            key_assumptions or ["No assumptions provided."],
            right_x,
            y_right,
            self.width - right_x - self.margin,
            max_items=8,
            page_title="Next Engineering Actions",
            size=7.9,
        )

        timeline = self.report.get("timeline") or []
        if timeline:
            y_phase = min(y_left, 64 * mm)
            y_phase = max(y_phase, 52 * mm)
            y_phase = self._section_header(
                self.margin,
                y_phase,
                self.width - 2 * self.margin,
                "Planning phases",
            )
            self._draw_bullets(
                timeline,
                self.margin,
                y_phase,
                self.width - 2 * self.margin,
                max_items=6,
                page_title="Next Engineering Actions",
                size=7.8,
            )
        self._done()


def render_mission_report_pdf(report: Mapping[str, Any]) -> bytes:
    return _PdfLayout(report).build()
