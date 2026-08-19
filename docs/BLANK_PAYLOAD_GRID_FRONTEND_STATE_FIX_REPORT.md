# Blank Payload Grid — Frontend Stale State Fix Report

## Root cause
The Docker backend + nginx proxy were confirmed healthy (both `http://localhost:8000/api/v1/taxonomy` and `http://localhost:3000/api/v1/taxonomy` return HTTP 200 with `families[].payload_categories[]` populated).

The blank grid occurs when the frontend computes an empty `options` array:
- `frontend/src/pages/PayloadPage.tsx` builds cards from `family.payload_categories`.
- `family` is set from taxonomy via:
  - `t.families.find((f) => f.family_id === (draft.family ?? "remote_sensing")) ?? null`
- `draft.family` is loaded from `localStorage` key `mission_draft_v1` by `frontend/src/state/mission.tsx`.

If `mission_draft_v1.family` is **stale/invalid** (e.g., an old enum name like `iot_comm`), then:
- taxonomy lookup finds no match → `family=null`
- `cats = fam?.payload_categories ?? []` → `[]`
- the payload card grid renders **no buttons** (blank grid), even though taxonomy is available.

## Fix implemented (minimal runtime-state hardening)
### 1) PayloadPage family fallback + visible taxonomy error
File: `frontend/src/pages/PayloadPage.tsx`

Changes:
- If `draft.family` does not match any taxonomy `family_id`, fall back to:
  1. `remote_sensing` if present, else
  2. first available family in taxonomy.
- Never set `family=null` when taxonomy contains families.
- If taxonomy fetch truly fails, show a visible error banner instead of silently showing an empty panel.

Effect:
- Stale `mission_draft_v1.family` can no longer blank the grid.
- True API failures are surfaced to the user.

### 2) LocalStorage sanitization on load
File: `frontend/src/state/mission.tsx`

Changes:
- Added `VALID_FAMILIES = ["remote_sensing","iot_communication","navigation"]`.
- When loading `mission_draft_v1`, if `family` is not valid:
  - overwrite storage with a cleaned draft `{ family: "remote_sensing" }`
  - return the cleaned draft (drops stale payload/roi/parameters to avoid mismatches).

Effect:
- Fix is persistent: once the app loads, localStorage is automatically repaired.

## Files changed
- `frontend/src/pages/PayloadPage.tsx`
- `frontend/src/state/mission.tsx`
- `frontend/src/__tests__/payloadPage_state.test.tsx`
- `frontend/tests/e2e/payload_stale_state_mock.spec.ts`
- `docs/BLANK_PAYLOAD_GRID_FRONTEND_STATE_FIX_REPORT.md`

## Tests added / updated
### Unit (Vitest)
File: `frontend/src/__tests__/payloadPage_state.test.tsx`
- Valid localStorage family renders payload cards.
- Invalid localStorage family falls back and renders payload cards.
- Taxonomy fetch failure shows a visible error message.

### E2E (Playwright, mocked backend)
File: `frontend/tests/e2e/payload_stale_state_mock.spec.ts`
- Preloads `localStorage.mission_draft_v1` with invalid family.
- Mocks `/api/v1/taxonomy`.
- Verifies the Payload page still renders cards (e.g., `VHR Optical`).

## Docker verification checklist (run in your environment)
1. With Docker UI open, set:
   - `localStorage.setItem("mission_draft_v1", JSON.stringify({ family: "bad_family" }))`
   - `location.href="/payload"`
2. Expected: payload cards still render (fallback to Remote Sensing).
3. If you break backend connectivity, expected: visible taxonomy error banner appears.

## Verdict
**FIXED_FRONTEND_STALE_STATE_BLANK_GRID**

