# Prompt 15E — Engineering Analysis Page (Three Tabs)

Date: 2026-05-09

## Summary

Added a new frontend route `/analysis` that re-runs the existing `POST /api/v1/mission/solve` call and renders the optional `engineering_trace` response from Prompt 15D across three tabs:

1. Selected Design
2. Engineering Budgets
3. Optimization Trace

The existing `/result` page remains unchanged aside from a new navigation button.

## Files Changed / Added

- `frontend/src/App.tsx`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/pages/AnalysisPage.tsx`
- `frontend/src/styles/global.css`
- `frontend/src/__tests__/analysisPage.test.tsx`
- `frontend/src/__tests__/resultPage_analysis_link.test.tsx`
- `frontend/tests/e2e/wizard_analysis_mock.spec.ts`

## New Route

- `/analysis` → `frontend/src/pages/AnalysisPage.tsx`

Routing behavior:

- Uses the current mission draft and `requireMissionInput(draft)`.
- Redirects if wizard prerequisites are missing:
  - missing `family` → `/`
  - missing `payload` → `/payload`
  - missing `roi` → `/roi`
  - missing `parameters` → `/parameters`
- Calls `solveMission(input)` (same contract as `/result`).
- Shows loading and error states.
- Shows an empty state if `engineering_trace` is missing:
  - “Engineering trace is not available for this solve.”

## Result → Analysis Navigation

`frontend/src/pages/ResultPage.tsx` now includes a secondary action:

- Button: “View Engineering Analysis”
- Navigates to: `/analysis`

## UI / Tab Design

`frontend/src/pages/AnalysisPage.tsx` uses `WizardShell` and displays:

- Summary header cards:
  - solver status
  - solve time (ms)
  - route used
  - payload source
  - platform/bus selection

Tabs (horizontal buttons):

1. **Selected Design**
   - `engineering_trace.selection`: platform/bus/payload/subsystem_count
   - `engineering_trace.subsystems`: list of subsystem entries (domain/name + optional mass/power/cost/tier)
2. **Engineering Budgets**
   - `engineering_trace.budgets`: totals + margins (when present)
   - `engineering_trace.constraints`: constraints table (PASS/FAIL/UNKNOWN badges)
3. **Optimization Trace**
   - `engineering_trace.solver`: route, solver_name, status, solve_time_ms, objective availability, notes
   - `engineering_trace.trace`: trace list
   - `engineering_trace.warnings`: warning box
   - Limitation note: CP-SAT diagnostics/top-N alternatives not shown yet

## Styling

Minimal style additions in `frontend/src/styles/global.css` (no redesign):

- `btnSecondary`
- `tabBar`, `tabButton`, `tabButtonActive`
- `constraintTable`
- `badgePass`, `badgeFail`, `badgeUnknown`
- `analysisGrid`, `traceList`

## Known Limitations (Intentional)

- `/analysis` re-runs `solveMission()` (no caching yet).
- `objective_value` is shown as “Not available on current route” when null/absent (v1 route).
- No CP-SAT bus-by-bus diagnostics or top‑N alternatives yet.
- No backend changes were made in this prompt.

## Tests Run

- Frontend unit tests: `npm --prefix frontend test`
- Frontend typecheck: `npm --prefix frontend run typecheck`
- Frontend e2e (Playwright): `npm --prefix frontend run test:e2e -- wizard_analysis_mock.spec.ts`

## Manual / Docker Verification Notes

- Covered via Playwright run (starts `vite dev` via Playwright `webServer` and clicks through `/ → /result → /analysis` with mocked backend response).

## Final Verdict

ENGINEERING_ANALYSIS_PAGE_READY

