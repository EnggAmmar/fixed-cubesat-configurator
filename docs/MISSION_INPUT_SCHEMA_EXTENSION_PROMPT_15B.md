# MISSION INPUT / STATE / API SCHEMA EXTENSION (Prompt 15B)

Date: 2026-05-08

## Summary
Extended the mission input schema (frontend + backend) to carry **optional** advanced engineering preferences:

- `altitude_km`
- `orbit_type`
- `lifetime_years`
- `propulsion_preference`
- `pointing_precision_preference`
- `downlink_rate_preference`
- `optimization_priority`
- `max_budget_usd`
- `max_bus_u`

This prompt is **schema/state only**: the solver does not use these fields yet.

## Files changed

**Frontend**
- `frontend/src/lib/api.ts`
- `frontend/src/state/mission.tsx`
- `frontend/src/pages/PayloadPage.tsx`
- `frontend/src/__tests__/mission_engineering_preferences.test.tsx`

**Backend**
- `backend/app/schemas/mission.py`
- `backend/app/api/v1/endpoints/mission.py`
- `backend/app/api/solve_cubesat.py`
- `backend/tests/test_api_mission.py`

## Frontend schema changes

Added explicit types in `frontend/src/lib/api.ts`:
- `OrbitType`
- `PropulsionPreference`
- `PointingPrecisionPreference`
- `DownlinkRatePreference`
- `OptimizationPriority`
- `EngineeringPreferences`

Extended `MissionInput`:
```ts
parameters: {
  revisit_time_hours: number;
  engineering_preferences?: EngineeringPreferences;
}
```

## Frontend state changes (safe + backward compatible)

In `frontend/src/state/mission.tsx`:
- `MissionDraft.parameters` now supports `engineering_preferences`.
- Added `setEngineeringPreferences(prefs)` which merges into `draft.parameters.engineering_preferences` and preserves `revisit_time_hours`.
- Added `getDefaultEngineeringPreferences()` helper (defaults only; not auto-applied).
- Improved localStorage load behavior for `mission_draft_v1`:
  - tolerant JSON parse
  - basic sanitization for invalid family values (fallback to `"remote_sensing"`)
  - tolerates missing `engineering_preferences`

`requireMissionInput(draft)` still only requires the legacy required fields; `engineering_preferences` remains optional.

## Backend schema changes (safe + backward compatible)

In `backend/app/schemas/mission.py`:
- Added enums:
  - `OrbitType`, `PropulsionPreference`, `PointingPrecisionPreference`,
    `DownlinkRatePreference`, `OptimizationPriority`
- Added `EngineeringPreferences` model (all optional fields).
- Extended `MissionParameters` with:
  - `engineering_preferences: EngineeringPreferences | None = None`

This preserves compatibility with old requests that only send `revisit_time_hours`.

## What is intentionally NOT connected yet

- No constraints/objective changes based on `engineering_preferences`.
- No changes to constellation/requirements derivation based on `altitude_km`/`orbit_type`/`lifetime_years`.

Backend note added in `backend/app/api/v1/endpoints/mission.py`:
“Prompt 15C/15D will connect these preferences to constraints/objective (no-op for now).”

## Tests

Backend:
- Extended `backend/tests/test_api_mission.py` to verify:
  1) legacy request still succeeds
  2) request including `parameters.engineering_preferences` is accepted (no 422) and returns a compatible response

Frontend:
- Added `frontend/src/__tests__/mission_engineering_preferences.test.tsx` to verify:
  1) `requireMissionInput` passes engineering prefs through when present
  2) legacy drafts still work
  3) `setEngineeringPreferences` merges + persists without erasing revisit hours

Test commands executed:
- `pytest -q backend/tests/test_api_mission.py`
- `npm --prefix frontend test`

## Verdict
MISSION_SCHEMA_EXTENDED_READY_FOR_UI_CONTROLS
