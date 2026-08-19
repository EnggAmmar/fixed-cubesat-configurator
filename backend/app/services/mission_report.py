from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Iterable

from app.schemas.mission_report import (
    BusPlatformSection,
    ConstellationSection,
    MissionReportJson,
    MissionSummarySection,
    PayloadSection,
    RadiationSection,
    TraceSection,
)
from app.schemas.solve_mission import SolveMissionRequest, SolveMissionResponse
from app.services.branding import branding_logo_data_uri
from app.services.solve_mission import solve_mission


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _domain_sort_key(domain: str) -> tuple[int, str]:
    order = {
        "structure": 0,
        "adcs": 1,
        "eps": 2,
        "obc": 3,
        "comm": 4,
        "thermal": 5,
        "propulsion": 6,
        "radiation_support_components": 7,
    }
    return (order.get(domain, 999), domain)


def _normalize_for_report(resp: SolveMissionResponse) -> SolveMissionResponse:
    # Ensure deterministic ordering in the report independent of solver/library iteration.
    sel = resp.subsystem_selection
    sel.selected.sort(key=lambda c: _domain_sort_key(c.domain))
    sel.optional_selected.sort(key=lambda c: _domain_sort_key(c.domain))

    resp.warnings = _dedupe_preserve_order(resp.warnings)
    sel.warnings = _dedupe_preserve_order(sel.warnings)
    return resp


def build_report_json(req: SolveMissionRequest) -> MissionReportJson:
    resp = _normalize_for_report(solve_mission(req))

    assumptions: list[str] = []
    if resp.constellation is not None:
        assumptions.extend(resp.constellation.assumptions)
    if resp.radiation is not None:
        assumptions.extend(resp.radiation.assumptions)
    assumptions = _dedupe_preserve_order(assumptions)

    constellation = ConstellationSection(available=resp.constellation is not None)
    if resp.constellation is not None:
        c = resp.constellation
        constellation = ConstellationSection(
            available=True,
            orbit_family=c.recommended_orbit_family.value,
            estimated_satellites=c.estimated_number_of_satellites,
            planes=c.recommended_candidate.planes,
            satellites_per_plane=c.recommended_candidate.satellites_per_plane,
            trace=list(c.trace),
            assumptions=list(c.assumptions),
            warnings=list(c.warnings),
        )

    structure = next(
        (c for c in resp.subsystem_selection.selected if c.domain == "structure"),
        None,
    )
    structure_component: dict[str, object] | None = None
    if structure is not None:
        structure_component = {
            "item_id": structure.item_id,
            "name": structure.name,
            "bus_size_u": structure.metadata.get("bus_size_u"),
            "max_total_mass_kg": structure.metadata.get("max_total_mass_kg"),
            "max_payload_volume_cm3": structure.metadata.get("max_payload_volume_cm3"),
            "avg_power_gen_w": structure.metadata.get("avg_power_gen_w"),
            "peak_power_gen_w": structure.metadata.get("peak_power_gen_w"),
        }

    bus_candidates = [
        {
            "size_u": c.size_u,
            "label": c.label,
            "official": c.official,
            "fitness_score": c.fitness_score,
            "overall_fit": c.overall_fit,
            "reasoning": list(c.reasoning),
        }
        for c in resp.bus_candidates
    ]

    radiation = RadiationSection(
        profile=resp.radiation_profile,
        screening=resp.radiation,
    )

    trace = TraceSection(
        derivation_trace=list(resp.derived_requirements.trace),
        solver_trace=list(resp.subsystem_selection.trace),
        constellation_trace=(
            list(resp.constellation.trace) if resp.constellation is not None else []
        ),
        radiation_trace=list(resp.radiation.trace) if resp.radiation is not None else [],
        pipeline_trace=list(resp.trace),
    )

    report = MissionReportJson(
        input=resp.input,
        mission_summary=MissionSummarySection(
            family=resp.input.family,
            roi=resp.input.roi,
            parameters=resp.input.parameters,
            constraints=req.constraints,
        ),
        payload=PayloadSection(
            summary=resp.payload_summary,
            synthesis=resp.payload_synthesis,
        ),
        derived_requirements=resp.derived_requirements,
        constellation=constellation,
        bus_platform=BusPlatformSection(
            chosen_bus_size_u=resp.chosen_bus_size_u,
            structure_component=structure_component,
            bus_candidates=bus_candidates,
        ),
        subsystem_selection=resp.subsystem_selection,
        radiation=radiation,
        warnings=list(resp.warnings),
        assumptions=assumptions,
        trace=trace,
    )
    return report


def _fmt(value: float | int | None, default: str = "—") -> str:
    if value is None:
        return default
    if isinstance(value, int):
        return f"{value:d}"
    return f"{value:.2f}"


def render_report_html(report: MissionReportJson) -> str:
    ms = report.mission_summary
    payload = report.payload.summary
    dr = report.derived_requirements
    sel = report.subsystem_selection
    report_input_json = json.dumps(
        report.input.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    report_id = f"CFG-{hashlib.sha256(report_input_json.encode('utf-8')).hexdigest()[:12].upper()}"
    logo_uri = branding_logo_data_uri()
    small_logo_uri = branding_logo_data_uri(small=True)

    def e(s: str) -> str:
        return html.escape(s, quote=True)

    def kv(k: str, v: str) -> str:
        return f"<div><span class='k'>{e(k)}</span><span class='v'>{v}</span></div>"

    subsystem_rows: list[str] = []
    for c in sel.selected:
        subsystem_rows.append(
            "<tr>"
            f"<td>{e(c.domain)}</td>"
            f"<td>{e(c.name)}</td>"
            f"<td class='num'>{_fmt(c.mass_kg)}</td>"
            f"<td class='num'>{_fmt(c.avg_power_w)}</td>"
            f"<td class='num'>{_fmt(c.peak_power_w)}</td>"
            f"<td class='num'>{_fmt(c.cost_kusd)}</td>"
            "</tr>"
        )

    constellation_bits = "<div class='muted'>Not available (estimator failed or disabled).</div>"
    if report.constellation.available:
        rows = [
            kv("Orbit family", e(report.constellation.orbit_family or "—")),
            kv("Estimated satellites", _fmt(report.constellation.estimated_satellites)),
            kv("Planes", _fmt(report.constellation.planes)),
            kv("Satellites/plane", _fmt(report.constellation.satellites_per_plane)),
        ]
        constellation_bits = "<div class='kv'>" + "".join(rows) + "</div>"

    warning_items = "".join(f"<li>{e(w)}</li>" for w in report.warnings) or "<li>None</li>"
    assumption_items = "".join(f"<li>{e(a)}</li>" for a in report.assumptions) or "<li>None</li>"

    rad_flags = "<li>None</li>"
    if report.radiation.screening and report.radiation.screening.flags:
        rad_flags = "".join(
            f"<li><span class='pill {e(f.severity)}'>{e(f.severity)}</span> "
            f"<span class='mono'>{e(f.domain)}:{e(f.item_id)}</span> {e(f.message)}</li>"
            for f in report.radiation.screening.flags
        )

    totals = sel.totals
    margins = sel.margins

    css = "\n".join(
        [
            ":root {",
            "  --bg: #070b12;",
            "  --panel: #0b1220;",
            "  --text: #e9eef6;",
            "  --muted: rgba(233, 238, 246, 0.65);",
            "  --line: rgba(255, 255, 255, 0.12);",
            "  --blue: #00a3ff;",
            "  --danger: #ff5166;",
            "}",
            "html, body {",
            "  margin: 0;",
            "  padding: 0;",
            "  background: var(--bg);",
            "  color: var(--text);",
            "  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto,",
            "    Helvetica, Arial;",
            "}",
            ".wrap { max-width: 1040px; margin: 0 auto; padding: 32px; }",
            ".reportTop {",
            "  display: flex;",
            "  align-items: flex-start;",
            "  justify-content: space-between;",
            "  gap: 24px;",
            "  margin-bottom: 22px;",
            "}",
            ".reportLogo {",
            "  width: 118px;",
            "  height: 118px;",
            "  object-fit: contain;",
            "  border-radius: 16px;",
            "  background: #fff;",
            "  border: 1px solid rgba(255, 255, 255, 0.14);",
            "}",
            "h1 { margin: 0 0 6px; font-size: 28px; letter-spacing: 0.02em; }",
            "h2 {",
            "  margin: 22px 0 10px;",
            "  font-size: 14px;",
            "  letter-spacing: 0.16em;",
            "  text-transform: uppercase;",
            "  color: var(--muted);",
            "}",
            ".card {",
            "  background: linear-gradient(180deg, rgba(10,16,28,0.85), rgba(0,0,0,0.55));",
            "  border: 1px solid var(--line);",
            "  border-radius: 14px;",
            "  padding: 14px;",
            "}",
            ".grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }",
            ".kv { display: grid; gap: 8px; }",
            ".kv > div {",
            "  display: flex;",
            "  justify-content: space-between;",
            "  gap: 12px;",
            "  border-bottom: 1px dashed rgba(255, 255, 255, 0.12);",
            "  padding-bottom: 8px;",
            "}",
            ".k { color: var(--muted); font-size: 12px; }",
            ".v { font-weight: 700; font-size: 12px; }",
            ".muted { color: var(--muted); font-size: 12px; }",
            ".reportFooter {",
            "  margin-top: 24px;",
            "  padding-top: 14px;",
            "  border-top: 1px solid var(--line);",
            "  display: flex;",
            "  align-items: center;",
            "  justify-content: space-between;",
            "}",
            ".footerBrand { display: inline-flex; align-items: center; gap: 8px; }",
            ".footerLogo {",
            "  width: 24px;",
            "  height: 24px;",
            "  object-fit: cover;",
            "  border-radius: 5px;",
            "  background: #fff;",
            "}",
            "table { width: 100%; border-collapse: collapse; font-size: 12px; }",
            "th, td {",
            "  padding: 10px;",
            "  border-bottom: 1px solid rgba(255, 255, 255, 0.10);",
            "  vertical-align: top;",
            "}",
            "th {",
            "  color: var(--muted);",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.12em;",
            "  font-size: 11px;",
            "  text-align: left;",
            "}",
            "td.num { text-align: right; font-variant-numeric: tabular-nums; }",
            "ul { margin: 0; padding-left: 18px; font-size: 12px; }",
            ".mono {",
            "  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,",
            "    'Liberation Mono',",
            "    'Courier New', monospace;",
            "}",
            ".pill {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  justify-content: center;",
            "  padding: 2px 8px;",
            "  border-radius: 999px;",
            "  border: 1px solid rgba(255, 255, 255, 0.16);",
            "  margin-right: 8px;",
            "  font-size: 11px;",
            "  letter-spacing: 0.04em;",
            "  text-transform: uppercase;",
            "}",
            ".pill.low {",
            "  border-color: rgba(0, 163, 255, 0.30);",
            "  color: rgba(29, 211, 255, 0.95);",
            "}",
            ".pill.medium {",
            "  border-color: rgba(255, 200, 0, 0.25);",
            "  color: rgba(255, 220, 130, 0.95);",
            "}",
            ".pill.high {",
            "  border-color: rgba(255, 81, 102, 0.30);",
            "  color: rgba(255, 120, 140, 0.95);",
            "}",
            "@media print {",
            "  html, body { background: #fff; color: #000; }",
            "  .card { background: #fff; border-color: #ddd; }",
            "  h2 { color: #444; }",
            "  .reportLogo { border-color: #ddd; }",
            "}",
        ]
    )
    logo_html = (
        f"<img class='reportLogo' src='{logo_uri}' alt='CubeSat Mission Configurator logo' />"
        if logo_uri
        else ""
    )
    footer_logo_html = (
        f"<img class='footerLogo' src='{small_logo_uri}' alt='' />" if small_logo_uri else ""
    )

    lines: list[str] = []
    lines.extend(
        [
            "<!doctype html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8' />",
            "<meta name='viewport' content='width=device-width, initial-scale=1' />",
            "<title>Mission Report</title>",
            "<style>",
            css,
            "</style>",
            "</head>",
            "<body>",
            "<div class='wrap'>",
            "<div class='reportTop'>",
            "<div>",
            "<h1>CubeSat Mission Configuration Report</h1>",
            f"<div class='muted'>{report_id} · Deterministic output for the same inputs "
            "(no timestamps).</div>",
            "</div>",
            logo_html,
            "</div>",
            "",
            "<h2>Mission Summary</h2>",
            "<div class='card grid'>",
            "  <div class='kv'>",
            kv("Report ID", e(report_id)),
            kv("Family", e(ms.family.value)),
            kv("ROI", e(ms.roi.type)),
        ]
    )
    if ms.roi.type == "region":
        lines.append(kv("Region query", e(ms.roi.query)))
    lines.extend(
        [
            kv("Revisit target", f"{_fmt(ms.parameters.revisit_time_hours)} h"),
            "  </div>",
            "  <div class='kv'>",
            kv("Payload", e(payload.name)),
            kv("Solver status", e(sel.status)),
            kv("Selected bus size", f"{_fmt(report.bus_platform.chosen_bus_size_u)} U"),
            kv(
                "Envelope",
                f"{_fmt(payload.length_mm)} x {_fmt(payload.width_mm)} x "
                f"{_fmt(payload.height_mm)} mm",
            ),
            kv("Mass", f"{_fmt(payload.mass_kg)} kg"),
            kv(
                "Power",
                f"{_fmt(payload.avg_power_w)} W avg / {_fmt(payload.peak_power_w)} W peak",
            ),
            "  </div>",
            "</div>",
            "",
            "<h2>Constellation Estimate</h2>",
            f"<div class='card'>{constellation_bits}</div>",
            "",
            "<h2>Derived Requirements</h2>",
            "<div class='card kv'>",
            kv("Required bus volume", f"{_fmt(dr.required_bus_volume_u)} U"),
            kv("Estimated mass budget", f"{_fmt(dr.estimated_total_mass_budget_kg)} kg"),
            kv("Downlink class", e(dr.required_downlink_class.value)),
            kv("Storage", f"{_fmt(dr.required_storage_gb)} GB"),
            kv("Pointing accuracy", f"{_fmt(dr.required_pointing_accuracy_deg)} deg"),
            "</div>",
            "",
            "<h2>Selected Subsystems</h2>",
            "<div class='card'>",
            "<table>",
            "<thead><tr>",
            "<th>Domain</th>",
            "<th>Name</th>",
            "<th class='num'>Mass (kg)</th>",
            "<th class='num'>Avg W</th>",
            "<th class='num'>Peak W</th>",
            "<th class='num'>Cost (kUSD)</th>",
            "</tr></thead>",
            "<tbody>",
            *subsystem_rows,
            "</tbody>",
            "</table>",
            "</div>",
            "",
            "<h2>Totals & Margins</h2>",
            "<div class='card grid'>",
            "  <div class='kv'>",
            kv("Feasible", f"{e(str(sel.feasible))} ({e(sel.status)})"),
            kv("Chosen bus size", f"{_fmt(report.bus_platform.chosen_bus_size_u)} U"),
            kv("Total mass", f"{_fmt(totals.total_mass_kg) if totals else '—'} kg"),
            kv(
                "Total avg power",
                f"{_fmt(totals.total_avg_power_w) if totals else '—'} W",
            ),
            kv(
                "Total peak power",
                f"{_fmt(totals.total_peak_power_w) if totals else '—'} W",
            ),
            kv(
                "Indicative cost",
                f"{_fmt(totals.total_cost_kusd) if totals else '—'} kUSD",
            ),
            "  </div>",
            "  <div class='kv'>",
            kv("Mass margin", f"{_fmt(margins.mass_margin_kg) if margins else '—'} kg"),
            kv(
                "Avg power margin",
                f"{_fmt(margins.avg_power_margin_w) if margins else '—'} W",
            ),
            kv(
                "Peak power margin",
                f"{_fmt(margins.peak_power_margin_w) if margins else '—'} W",
            ),
            kv(
                "Bus volume margin",
                f"{_fmt(margins.bus_volume_margin_u) if margins else '—'} U",
            ),
            "  </div>",
            "</div>",
            "",
            "<h2>Radiation Screening</h2>",
            "<div class='card'>",
            "<ul>",
            rad_flags,
            "</ul>",
            "</div>",
            "",
            "<h2>Warnings</h2>",
            "<div class='card'><ul>",
            warning_items,
            "</ul></div>",
            "",
            "<h2>Assumptions</h2>",
            "<div class='card'><ul>",
            assumption_items,
            "</ul></div>",
            "",
            "<div class='reportFooter'>",
            f"<span class='footerBrand'>{footer_logo_html}<span>CubeSat Configurator</span></span>",
            f"<span class='muted'>{report_id}</span>",
            "</div>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(lines)


def report_json_bytes(report: MissionReportJson) -> bytes:
    # Use stdlib json to guarantee stable key ordering.
    return json.dumps(
        report.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
