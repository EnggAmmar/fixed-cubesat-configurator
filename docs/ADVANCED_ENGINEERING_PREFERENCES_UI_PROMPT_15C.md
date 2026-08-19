# ADVANCED ENGINEERING PREFERENCES UI (Prompt 15C)

Date: 2026-05-08

## 1) Files changed

**Frontend**
- `frontend/src/pages/ParametersPage.tsx`
- `frontend/src/styles/global.css`
- `frontend/src/test/setup.ts`
- `frontend/src/__tests__/parametersPage_engineering_preferences.test.tsx`
- `frontend/tests/e2e/wizard_parameters_engineering_prefs_mock.spec.ts`

## 2) UI controls added (below Revisit Time)

Location: `frontend/src/pages/ParametersPage.tsx` under the existing revisit-time block.

Section title + hint:
- **Advanced Engineering Preferences**
- “Optional constraints and preferences for the engineering solver… (stored now; connected later)”

Controls (all optional / safe defaults):
- Orbit Altitude (km): range 300–1000 step 10 + numeric input
- Orbit Type: LEO / SSO / Polar / Equatorial / Custom
- Mission Lifetime (years): 0.5 / 1 / 2 / 3 / 5
- Propulsion Preference: No preference / None / Cold gas / Electric / Chemical / Green monoprop
- Pointing Precision: No preference / Coarse / Medium / Fine / Ultra-fine
- Downlink Rate Preference: No preference / Low / Medium / High / Optical/extreme
- Optimization Priority: Balanced / Lowest cost / Lowest mass / Highest performance / Lowest risk
- Max Budget (USD): numeric input (empty → undefined)
- Max Bus Size: Any / 1 / 1.5 / 2 / 3 / 6 / 12 / 16 / 27 / 50 (Any → undefined)

Minimal styling additions (no redesign):
- Added `select` styling to match inputs.
- Added helper layout classes: `formSection`, `formHint`, `preferencesGrid` in `frontend/src/styles/global.css`.

## 3) State persistence behavior

On `Finish`:
- Writes `revisit_time_hours` via `setRevisitHours(hours)`
- Writes preferences via `setEngineeringPreferences(nextPrefs)`
- Uses `flushSync` to ensure both writes happen before `nav("/result")`.

Empty fields:
- `max_budget_usd` empty → stored as `undefined` (not `""`, not `NaN`)
- `max_bus_u` “Any” → stored as `undefined`

Result:
- `localStorage["mission_draft_v1"]` includes `parameters.engineering_preferences` when finishing the page.

## 4) Old-draft compatibility

- Drafts missing `engineering_preferences` render with UI defaults (from `getDefaultEngineeringPreferences()` merged with any saved values).
- Partial/malformed prefs are tolerated by mission state load sanitization from Prompt 15B.

## 5) Tests run and results

Frontend unit tests:
- `npm --prefix frontend test` ✅ (all passing)

Backend acceptance smoke:
- `pytest -q backend/tests/test_api_mission.py` ✅ (3 passed)

Playwright (mocked backend verify request + localStorage):
- `npx playwright test tests/e2e/wizard_parameters_engineering_prefs_mock.spec.ts` ✅ (1 passed)

Playwright (full backend solve path still works):
- `E2E_FULL=1 npx playwright test tests/e2e/wizard.spec.ts` ✅ (1 passed)

## 6) Manual/Docker verification notes

Automated equivalent of manual verification was performed via Playwright:
- Wizard navigation `/ → /payload → /roi → /parameters → /result` still completes.
- `/result` still solves successfully against the running backend (full-flow e2e).
- LocalStorage contains `engineering_preferences` after finishing parameters (mocked + asserted).

## 7) What is intentionally not connected yet

- Backend solver ignores `engineering_preferences` for now (no constraints/objective changes yet).
- No `/analysis` page yet.

## 8) Final verdict

ADVANCED_ENGINEERING_PREFERENCES_UI_READY

