# CubeSat Mission PDF Report Design

This design uses the provided visual direction as inspiration only: clean white/black
academic/engineering formatting, large section titles, sparse cards, simple vector graphics, page
numbers, and a report-like layout. It must not copy any third-party logo, contact details, visual
assets, or proprietary wording.

## Branding and layout principles

- Brand: neutral academic/engineering identity for `CubeSat Configurator`.
- Palette: white background, black text, light gray dividers, one muted technical accent color.
- Typography: large section titles, compact labels, tabular numeric values, generous whitespace.
- Graphics: generated vector/CSS/SVG-only constellation and CubeSat placeholders; no external assets.
- Footer: page number, report ID, and `CubeSat Configurator` label on every page except cover if desired.
- Determinism: report ID is derived from a canonical input hash; no timestamp is required for identity.

## Report ID

- Field: `report_id`.
- Source: deterministic hash of canonical report input, not wall-clock time.
- Proposed algorithm:
  - Serialize canonical input with sorted keys and stable separators.
  - Include mission input, optional user constraints, estimator settings, bus constraints, and radiation
    overrides when present.
  - Compute `sha256(canonical_json).hexdigest()[:12].upper()`.
  - Render as `CFG-<HASH12>`.

## Proposed PDF sections

### 1. Cover Page

- Title: `CubeSat Mission Configuration Report`
- Generated for: mission family
- Payload name/class
- ROI
- Chosen bus size
- Configuration/report ID derived deterministically from input hash, not timestamp
- Visual treatment:
  - Large report title at top-left.
  - Sparse metadata card with mission family, payload, ROI, bus size, and report ID.
  - Simple line-art CubeSat or constellation motif using vector shapes only.

### 2. Mission & Constellation Summary

- Revisit target in hours
- Estimated number of satellites
- Orbit family/type
- Number of planes
- Satellites per plane if available
- Annual data generated estimate where enough data exists
- Visual treatment:
  - Four to six engineering cards.
  - Small constellation graphic: planes as arcs/rings and satellites as dots.
  - Missing derived values render as `Not available`, not as inferred claims.

### 3. Orbit / Architecture Page

- Orbit type/family
- Altitude if selected or assumed
- Planes
- Satellites per plane
- Engineering assumptions and warnings
- Visual treatment:
  - Orbit architecture card.
  - Assumptions and warnings as concise callouts.
  - Warnings are visually distinct but restrained, using a thin border or label.

### 4. Data Budget Page

- Data per day per satellite
- Data per day constellation total
- Annual generated data
- Required storage
- Downlink class / min downlink if available
- Visual treatment:
  - Data flow graphic: payload -> storage -> downlink.
  - Data budget cards with units.
  - Only render calculated data estimates when data rate and satellite count are available.

Documentation comment for future renderer:

```text
If payload data_rate_mbps and estimated_satellites are available:
  data_per_day_per_satellite_gb = data_rate_mbps * 86400 / 8 / 1000
  constellation_data_per_day_gb = data_per_day_per_satellite_gb * estimated_satellites
  annual_generated_data_tb = constellation_data_per_day_gb * 365 / 1000
Do not render these as claims when any required input is missing.
```

### 5. Satellite Fleet Page

- Payload name/class
- Platform/bus size
- Max total mass
- Selected platform name
- Simple CubeSat illustration placeholder using CSS/SVG/vector shapes, no external copyrighted asset
- Visual treatment:
  - Fleet count visualization with repeated small CubeSat glyphs or grouped dots.
  - Platform card with bus size and selected structure/platform.
  - Keep the illustration schematic, not product-like.

### 6. Payload Geometry / Coverage Page

- Payload dimensions
- Payload mass/power
- Pointing accuracy requirement
- Optional: estimated swath width if field-of-view and altitude are available
- Include formula in documentation comments only, not as a claim if required inputs are missing
- Visual treatment:
  - Dimension box: length x width x height.
  - Payload mass and power cards.
  - Coverage graphic placeholder with angle cone only when field-of-view is present.

Documentation comment for future renderer:

```text
If field_of_view_deg and altitude_km are available:
  swath_width_km = 2 * altitude_km * tan(radians(field_of_view_deg) / 2)
Do not render estimated swath width when field-of-view or altitude is missing.
```

### 7. Subsystem Architecture Page

- Platform, structure, EPS, ADCS, OBC, communication, thermal, propulsion/radiation components where selected
- Mass, average power, peak power, cost columns
- Visual treatment:
  - Table-first engineering layout.
  - One row per selected component.
  - Optional components grouped under a separate `Optional / Support Components` subheading when present.

### 8. Budgets & Margins Page

- Total mass
- Mass margin
- Average power and margin
- Peak power and margin
- Bus volume margin
- Indicative cost
- Highlight PASS/WARN/FAIL status based on margins
- Visual treatment:
  - Budget cards with status labels.
  - Margins as numeric values and simple horizontal bars.
  - Cost is explicitly labeled `indicative`.

Proposed status rule:

- `PASS`: all available margins are greater than or equal to zero and key margins exceed configured warn thresholds.
- `WARN`: all available margins are greater than or equal to zero, but at least one key margin is close to zero.
- `FAIL`: any available margin is below zero or solver feasibility status is false/infeasible.

Initial warn thresholds should be renderer constants, not solver constraints:

- Mass margin warning threshold: `< 10%` of capacity when capacity is known, otherwise `< 0.5 kg`.
- Average/peak power margin warning threshold: `< 10%` of capacity when capacity is known, otherwise `< 5 W`.
- Bus volume margin warning threshold: `< 0.5 U`.

### 9. Solver Trace / Explainability Page

- Solver name/status if available
- Objective value if available
- Key constraints and margins
- Warnings
- Assumptions
- Keep concise; do not dump raw JSON unless user downloads JSON
- Visual treatment:
  - Short solver summary card.
  - Compact constraints table.
  - Warnings and assumptions as capped lists; overflow can be summarized as `+ N more in JSON export`.

### 10. Optional Timeline / Next Steps Page

- Concept phase
- Requirements refinement
- Payload confirmation
- Architecture review
- AIT / validation placeholder
- This is generic and must be labeled as `illustrative planning timeline`, not a commercial promise
- Visual treatment:
  - Linear timeline with five neutral milestones.
  - Include a clear label: `Illustrative planning timeline; not a schedule commitment.`

## Proposed internal report data model

Prefer deriving this model from existing solve/report objects rather than re-solving. The renderer should accept
a single prepared dictionary/context and produce PDF bytes.

```python
ReportRenderContext = {
    "report_id": str,
    "version": "v1",
    "mission": {
        "family": str,
        "roi_type": str,
        "roi_label": str | None,
        "revisit_time_hours": float | None,
        "constraints": dict | None,
    },
    "payload": {
        "name": str,
        "class": str | None,
        "payload_id": str | None,
        "dimensions_mm": {"length": float | None, "width": float | None, "height": float | None},
        "mass_kg": float | None,
        "avg_power_w": float | None,
        "peak_power_w": float | None,
        "data_rate_mbps": float | None,
        "pointing_accuracy_deg": float | None,
        "field_of_view_deg": float | None,
    },
    "constellation": {
        "available": bool,
        "estimated_satellites": int | None,
        "orbit_family": str | None,
        "orbit_type": str | None,
        "altitude_km": float | None,
        "planes": int | None,
        "satellites_per_plane": int | None,
        "assumptions": list[str],
        "warnings": list[str],
    },
    "data_budget": {
        "data_per_day_per_satellite_gb": float | None,
        "data_per_day_constellation_gb": float | None,
        "annual_generated_data_tb": float | None,
        "required_storage_gb": float | None,
        "downlink_class": str | None,
        "min_downlink_mbps": float | None,
    },
    "platform": {
        "chosen_bus_size_u": float | None,
        "selected_platform_name": str | None,
        "max_total_mass_kg": float | None,
        "structure_component": dict | None,
    },
    "subsystems": [
        {
            "domain": str,
            "name": str,
            "item_id": str | None,
            "mass_kg": float | None,
            "avg_power_w": float | None,
            "peak_power_w": float | None,
            "cost_kusd": float | None,
            "optional": bool,
        }
    ],
    "budgets": {
        "total_mass_kg": float | None,
        "mass_margin_kg": float | None,
        "total_avg_power_w": float | None,
        "avg_power_margin_w": float | None,
        "total_peak_power_w": float | None,
        "peak_power_margin_w": float | None,
        "bus_volume_margin_u": float | None,
        "total_cost_kusd": float | None,
        "status": "PASS" | "WARN" | "FAIL" | "UNKNOWN",
    },
    "solver": {
        "name": str | None,
        "status": str | None,
        "objective_value": float | None,
        "constraints": list[dict],
        "warnings": list[str],
        "assumptions": list[str],
    },
}
```

## Source mapping

- Preferred backend source: `MissionReportJson` from `backend/app/services/mission_report.py`.
  - It already combines mission summary, payload summary, derived requirements, constellation,
    bus platform, subsystem selection, radiation, warnings, assumptions, and trace.
  - It is the best source for `/api/report/download` because `build_report_json(req)` already solves once
    and returns a structured report object.
- Current v1 frontend route source: `MissionReportRequest` plus v1 solve pieces in
  `backend/app/api/v1/endpoints/mission.py`.
  - To avoid diverging report logic, prefer adapting the v1 route to build the same
    `ReportRenderContext` from its already-computed `requirements`, `constellation`, and `solution`, or
    migrate the frontend download button to the structured `/api/report/download?format=pdf` route.
- Avoid duplicate solver calls:
  - Do not call `solve_mission` or `solve_subsystems` inside the renderer.
  - The route should solve once, prepare `ReportRenderContext`, then render.
  - If the UI already has a solve result, a future optimization can allow generating from a cached solve
    result or a report JSON endpoint, but the server must remain authoritative for downloadable reports.

## Renderer behavior for missing values

- Render unavailable data as `Not available`.
- Do not infer altitude, field-of-view, swath width, min downlink, or annual data unless the required
  fields are present in the source model.
- Keep derived display metrics report-only; they must not alter solver decisions, CP-SAT objectives,
  component databases, payload catalogs, or constellation estimator behavior.
