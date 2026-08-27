"""Scenario benchmark for the mission-solve pipeline.

Runs a fixed set of mission scenarios (one per real payload category, plus a
couple of My Payload cases) through the live backend's actual user-facing
endpoint, `POST /api/v1/mission/solve`, holding ROI and revisit time constant
so mission family and payload are the only varying factors.

For every scenario whose payload is known to the `backend/solver/` engine, it
also calls the diagnostic endpoint (`POST /api/solve/cubesat`,
`diagnostic: true`) to get two independent references that were NOT produced
by the primary solve path:

  - `recommended_bus_min_u` / `recommended_bus_min_mass_kg`: an engineering
    judgment call stored on the payload record itself (ground truth external
    to the solver).
  - `bus_cases[]`: every bus size solved independently and in isolation, from
    which the smallest feasible bus is the true optimum the model itself can
    reach for that payload (ground truth internal to the solver).

A scenario is scored "optimal" if the primary path's bus size matches that
internal optimum, and its gap to the external recommendation is reported
separately rather than forced into a pass/fail (the recommendation is not
always achievable under the model's own conservative constraints, and that
gap is itself useful data, not necessarily a defect).

Usage:
    backend/.venv/Scripts/python.exe backend/scripts/scenario_benchmark.py \\
        [base_url] [ground_station_count]

`ground_station_count` is optional and, when given, is threaded into every
catalog scenario's `engineering_preferences` (My Payload scenarios ignore it -
they run on the fallback engine, which has no ground-segment model). Useful
for re-running the same 15 scenarios under a more realistic ground segment
than the single-station default, to see how much of any "always oversized
vs. the database recommendation" gap is explained by that one assumption.

Requires the backend to already be running (default http://localhost:8010).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"
GROUND_STATION_COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else None

BUS_LADDER = ["1U", "1.5U", "2U", "3U", "6U", "8U", "12U", "16U", "27U", "50U+"]

ROI: dict[str, Any] = {"type": "global"}
PARAMETERS: dict[str, Any] = {"revisit_time_hours": 48}
if GROUND_STATION_COUNT is not None:
    PARAMETERS["engineering_preferences"] = {"ground_station_count": GROUND_STATION_COUNT}

CATALOG_SCENARIOS: list[tuple[str, str, str]] = [
    ("remote_sensing", "hyperspectral", "RS-EO-HSI-001"),
    ("remote_sensing", "infrared_imaging", "RS-EO-NIR-001"),
    ("remote_sensing", "vhr_optical", "RS-EO-PAN-001"),
    ("remote_sensing", "thermal", "RS-EO-LWIR-001"),
    ("remote_sensing", "sar", "RS-EO-CSAR-001"),
    ("iot_communication", "iot_store_and_forward", "IOT-COM-BPT-001"),
    ("iot_communication", "broadband_rf_comms", "IOT-COM-RX-001"),
    ("iot_communication", "optical_laser_comms", "IOT-COM-LCT-001"),
    ("iot_communication", "quantum_secure_comms", "IOT-COM-QC-001"),
    ("navigation", "pnt_augmentation", "NAV-RF-PNT-001"),
    ("navigation", "navigation_beacons", "NAV-RF-BEACON-001"),
    ("navigation", "rf_geolocation", "NAV-DEF-DFA-001"),
    ("navigation", "timing_payloads", "NAV-RF-TIME-001"),
]

MY_PAYLOAD_SCENARIOS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "remote_sensing",
        "my_payload_optical",
        {
            "name": "Custom Optical Imager",
            "length_mm": 150,
            "width_mm": 100,
            "height_mm": 100,
            "mass_kg": 1.8,
            "avg_power_w": 12,
            "peak_power_w": 20,
            "data_rate_mbps": 50,
            "pointing_accuracy_deg": 0.3,
        },
    ),
    (
        "iot_communication",
        "my_payload_relay",
        {
            "name": "Custom IoT Relay",
            "length_mm": 120,
            "width_mm": 90,
            "height_mm": 90,
            "mass_kg": 0.9,
            "avg_power_w": 5,
            "peak_power_w": 9,
        },
    ),
]


def _post(path: str, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return None, f"HTTP {e.code}: {detail[:300]}"
    except Exception as e:  # noqa: BLE001 - benchmark script, want to keep going
        return None, f"{type(e).__name__}: {e}"


def _ladder_index(bus_class: str) -> int | None:
    try:
        return BUS_LADDER.index(bus_class)
    except ValueError:
        return None


def _bus_u_to_label(bus_u: float) -> str | None:
    """Map a numeric bus size (e.g. 12.0) back to its ladder label (e.g. '12U')."""
    for label in BUS_LADDER:
        if label == "50U+":
            if bus_u >= 50:
                return label
        elif float(label.rstrip("U")) == float(bus_u):
            return label
    return None


def _smallest_feasible(bus_cases: list[dict[str, Any]]) -> str | None:
    feasible = [c["bus_class"] for c in bus_cases if c.get("status") in ("OPTIMAL", "FEASIBLE")]
    feasible.sort(key=lambda b: _ladder_index(b) if _ladder_index(b) is not None else 999)
    return feasible[0] if feasible else None


def _engine_used(solve: dict[str, Any]) -> str:
    subs = (solve.get("solution") or {}).get("subsystems") or []
    for s in subs:
        src = (s.get("metadata") or {}).get("source_database")
        if src:
            return src
    return "unknown"


def _radiation_warning_count(solve: dict[str, Any]) -> int:
    warnings = (solve.get("solution") or {}).get("warnings") or []
    return sum(1 for w in warnings if "No radiation record found" in w)


@dataclass
class ScenarioResult:
    scenario: str
    family: str
    payload_kind: str
    payload_id: str | None
    feasible: bool
    error: str | None = None
    actual_bus_u: float | None = None
    total_mass_kg: float | None = None
    total_cost_kusd: float | None = None
    engine: str = "unknown"
    radiation_warnings: int = 0
    recommended_bus_min_u: float | None = None
    model_optimal_bus: str | None = None
    steps_above_model_optimum: int | None = None
    steps_above_recommendation: int | None = None
    ground_truth_available: bool = False
    notes: list[str] = field(default_factory=list)


def run_scenario_catalog(family: str, category: str, payload_id: str) -> ScenarioResult:
    scenario = f"{family}/{category}"
    mission_input = {
        "family": family,
        "payload": {"type": "catalog", "payload_id": payload_id},
        "roi": ROI,
        "parameters": PARAMETERS,
    }
    solve, err = _post("/api/v1/mission/solve", {"input": mission_input})
    r = ScenarioResult(
        scenario=scenario, family=family, payload_kind="catalog", payload_id=payload_id,
        feasible=solve is not None, error=err,
    )
    if solve is not None:
        r.actual_bus_u = solve["solution"]["platform"]["bus_size_u"]
        r.total_mass_kg = solve["solution"]["budgets"]["total_mass_kg"]
        r.total_cost_kusd = solve["solution"]["budgets"]["total_cost_kusd"]
        r.engine = _engine_used(solve)
        r.radiation_warnings = _radiation_warning_count(solve)

    diag_body: dict[str, Any] = {"payload_id": payload_id, "diagnostic": True}
    if GROUND_STATION_COUNT is not None:
        diag_body["ground_station_count"] = GROUND_STATION_COUNT
    diag, diag_err = _post("/api/solve/cubesat", diag_body)
    if diag is not None and diag.get("payload_meta"):
        r.ground_truth_available = True
        r.recommended_bus_min_u = diag["payload_meta"].get("recommended_bus_min_u")
        r.model_optimal_bus = _smallest_feasible(diag.get("bus_cases", []))

        actual_label = _bus_u_to_label(r.actual_bus_u) if r.actual_bus_u is not None else None
        actual_idx = _ladder_index(actual_label) if actual_label else None
        optimum_idx = _ladder_index(r.model_optimal_bus) if r.model_optimal_bus else None
        if actual_idx is not None and optimum_idx is not None:
            r.steps_above_model_optimum = actual_idx - optimum_idx

        rec_u = r.recommended_bus_min_u
        rec_label = _bus_u_to_label(rec_u) if rec_u is not None else None
        rec_idx = _ladder_index(rec_label) if rec_label else None
        if actual_idx is not None and rec_idx is not None:
            r.steps_above_recommendation = actual_idx - rec_idx
    else:
        reason = diag_err or "payload not in backend/solver catalog"
        r.notes.append(f"no diagnostic ground truth available ({reason})")

    if r.total_mass_kg is not None and solve is not None:
        summary = solve.get("payload_summary")
        payload_summary_mass = summary["mass_kg"] if summary else None
        # sanity check for the F-09 mass-zeroing bug: total can never be
        # less than the payload alone
        if payload_summary_mass and r.total_mass_kg < payload_summary_mass:
            r.notes.append(
                f"SUSPECT mass bug: total_mass_kg={r.total_mass_kg} "
                f"< payload's own mass {payload_summary_mass}"
            )
    return r


def run_scenario_my_payload(family: str, tag: str, spec: dict[str, Any]) -> ScenarioResult:
    scenario = f"{family}/{tag}"
    mission_input = {
        "family": family,
        "payload": {"type": "my_payload", **spec},
        "roi": ROI,
        "parameters": PARAMETERS,
    }
    solve, err = _post("/api/v1/mission/solve", {"input": mission_input})
    r = ScenarioResult(
        scenario=scenario, family=family, payload_kind="my_payload", payload_id=None,
        feasible=solve is not None, error=err,
    )
    r.notes.append(
        "routes through the fallback engine (cpsat_selection.py) - "
        "no backend/solver ground truth exists"
    )
    if solve is not None:
        r.actual_bus_u = solve["solution"]["platform"]["bus_size_u"]
        r.total_mass_kg = solve["solution"]["budgets"]["total_mass_kg"]
        r.total_cost_kusd = solve["solution"]["budgets"]["total_cost_kusd"]
        r.engine = _engine_used(solve)
        r.radiation_warnings = _radiation_warning_count(solve)
        if r.total_mass_kg < spec["mass_kg"]:
            r.notes.append(
                f"SUSPECT mass bug: total_mass_kg={r.total_mass_kg} "
                f"< payload's own mass {spec['mass_kg']}"
            )
    return r


def main() -> None:
    results: list[ScenarioResult] = []
    for family, category, payload_id in CATALOG_SCENARIOS:
        print(f"solving {family}/{category} ({payload_id}) ...", file=sys.stderr)
        results.append(run_scenario_catalog(family, category, payload_id))
    for family, tag, spec in MY_PAYLOAD_SCENARIOS:
        print(f"solving {family}/{tag} (my_payload) ...", file=sys.stderr)
        results.append(run_scenario_my_payload(family, tag, spec))

    suffix = f"_gs{GROUND_STATION_COUNT}" if GROUND_STATION_COUNT is not None else ""
    out_path = Path(__file__).parent / f"scenario_benchmark_results{suffix}.json"
    out_path.write_text(
        json.dumps([r.__dict__ for r in results], indent=2, default=str), encoding="utf-8"
    )

    total = len(results)
    infeasible = [r for r in results if not r.feasible]
    solved_with_gt = [r for r in results if r.ground_truth_available and r.feasible]
    optimal = [r for r in solved_with_gt if r.steps_above_model_optimum == 0]
    suboptimal = [r for r in solved_with_gt if (r.steps_above_model_optimum or 0) > 0]
    matches_recommendation = [r for r in solved_with_gt if r.steps_above_recommendation == 0]
    radiation_hit = [r for r in results if r.radiation_warnings > 0]
    suspect_bugs = [r for r in results if any("SUSPECT" in n for n in r.notes)]

    print()
    header = f"{'SCENARIO':<38}{'BUS':>6}{'ENGINE':>10}{'OPTIMAL?':>10}{'VS REC.':>10}"
    print(header + f"{'RAD.WARN':>10}")
    for r in results:
        if not r.feasible:
            print(f"{r.scenario:<38}{'FAIL':>6}  {str(r.error)[:60]}")
            continue
        is_new_engine = "backend/solver" in r.engine
        engine_short = "new" if is_new_engine else ("old" if r.engine != "unknown" else "?")
        if r.steps_above_model_optimum is None:
            opt = "-"
        elif r.steps_above_model_optimum == 0:
            opt = "yes"
        else:
            opt = f"{r.steps_above_model_optimum:+d}"
        if r.steps_above_recommendation is None:
            rec = "-"
        elif r.steps_above_recommendation == 0:
            rec = "match"
        else:
            rec = f"{r.steps_above_recommendation:+d}"
        bus_label = f"{r.actual_bus_u}U"
        row = f"{r.scenario:<38}{bus_label:>6}{engine_short:>10}{opt:>10}{rec:>10}"
        print(row + f"{r.radiation_warnings:>10}")

    print()
    print("=" * 72)
    catalog_total = sum(1 for r in results if r.payload_kind == "catalog")
    my_payload_total = total - catalog_total
    print(f"Scenarios run: {total}  ({catalog_total} catalog, {my_payload_total} custom)")
    print(f"Infeasible / errored:         {len(infeasible)} / {total}")
    print(f"Catalog scenarios with ground truth: {len(solved_with_gt)} / {catalog_total}")
    print(f"  -> matched model's own optimum bus:   {len(optimal)} / {len(solved_with_gt)}")
    print(f"  -> exceeded it (suboptimal):           {len(suboptimal)} / {len(solved_with_gt)}")
    n_match = len(matches_recommendation)
    print(f"  -> matched database's recommended bus: {n_match} / {len(solved_with_gt)}")
    print(f"Scenarios with radiation-screening blind spot (F-13): {len(radiation_hit)} / {total}")
    print(f"Scenarios with a suspected correctness bug:  {len(suspect_bugs)} / {total}")
    print()
    print(f"Full raw results written to {out_path}")


if __name__ == "__main__":
    main()
