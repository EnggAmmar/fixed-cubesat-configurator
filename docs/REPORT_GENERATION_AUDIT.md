# Report Generation Audit

## Branch and current flow

- Branch verified locally as `main_document_generation`.
- The final frontend result-page download flow calls `POST /api/v1/mission/report?format=pdf` from `frontend/src/lib/api.ts` and downloads from `frontend/src/pages/ResultPage.tsx`.
- The v1 report endpoint uses `MissionReportRequest` from `backend/app/schemas/mission.py`, then runs one server-side pass through requirement derivation, constellation estimation, CP-SAT subsystem selection, and engineering trace construction.
- The older `/api/report.json` and `/api/report/download` routes remain present and are backed by `backend/app/services/mission_report.py` plus `backend/app/services/pdf_report.py`.

## Current report fields and calculation sources

- Mission identity comes from user input: mission family, ROI, revisit target, payload selection, and engineering preferences.
- Payload mass, dimensions, volume, power, pointing, thermal class, and minimum downlink come from user payload fields or resolved payload catalog fields.
- Full-database catalog metadata is read for report-only fields when available: daily data generation, swath, ground resolution, required downlink class, and onboard storage days.
- Constellation values come from `estimate_constellation`: orbit family, altitude, estimated satellites, planes, and satellites per plane.
- Platform/subsystem choices and total mass, power, and cost budgets come from CP-SAT output; the report does not alter solver decisions.
- Engineering trace supplies solver route/status, constraints, subsystem selection reasons, margins, and assumptions.
- Report-only margins are displayed as used/capacity/absolute/percent where capacities are available.

## Missing or limited fields

- Objective value remains unavailable in the current v1 engineering trace.
- Duty-cycle/contact assumptions are not mission inputs, so generated-data calculations either use catalog daily data or the pre-existing report assumption of continuous payload data-rate conversion.
- Required storage is unavailable when neither user payload storage nor catalog storage-days metadata exists.
- Radiation screening is unavailable in the v1 report path and is surfaced as a warning.
- Coverage geometry cannot be claimed valid when FOV/swath/GSD are missing; the report now flags that explicitly.

## Implementation plan

- Keep `/api/v1/mission/report` backwards compatible: Markdown remains default, with explicit `pdf`, `html`, and `json` formats.
- Expand the structured report payload with provenance, warnings, constraints, bus candidates, cost breakdown, data completeness, radiation status, timeline, and next engineering actions.
- Upgrade HTML/PDF rendering to show engineering-grade sections rather than sparse solver summaries.
- Keep frontend changes limited to the final report download area and expose PDF/JSON/HTML downloads.
- Add regression tests for major report sections, warning generation, constraints, subsystem reasoning, non-empty PDF/HTML, and frontend download behavior.

## Files modified

- `backend/app/services/report.py`
- `backend/app/templates/report/mission_report.html`
- `backend/app/templates/report/mission_report.css`
- `backend/tests/test_api_mission.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/__tests__/resultPage_analysis_link.test.tsx`
- `docs/REPORT_GENERATION_AUDIT.md`

## Validation notes

Validation commands and outcomes are recorded in the final Codex response for this task. Docker validation depends on a local Docker CLI; previous attempts in this environment failed because `docker` was not available on `PATH`.

## Validation results for this pass

Passing commands:

- `python -m ruff check backend`
- `python -m ruff format --check backend/app/services/report.py backend/tests/test_api_mission.py`
- `npx prettier -c src/lib/api.ts src/pages/ResultPage.tsx src/__tests__/resultPage_analysis_link.test.tsx`
- `npx eslint src/lib/api.ts src/pages/ResultPage.tsx src/__tests__/resultPage_analysis_link.test.tsx`
- `python -m pytest backend/tests`
- `npm test`
- `npm run build`

Pre-existing/unrelated checks still failing:

- `python -m ruff format --check backend` reports seven unrelated backend files that would be reformatted.
- `npm run format:check` reports existing Prettier drift in 47 unrelated frontend files.
- `npm run lint` reports existing `no-explicit-any` and React hook warnings outside this report-download change.
- `docker compose build` cannot run in this environment because the `docker` command is not available on `PATH`.
