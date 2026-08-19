# CONFIGURATOR ENGINEERING COCKPIT — AUDIT (Prompt 15A)

Date: 2026-05-08  
Scope: **Audit only** (no UI redesign, no solver math changes, no DB/taxonomy edits).

## 0) Files inspected

**Frontend**
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/pages/MissionFamilyPage.tsx`
- `frontend/src/pages/PayloadPage.tsx`
- `frontend/src/pages/RoiPage.tsx`
- `frontend/src/pages/ParametersPage.tsx`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/components/WizardShell.tsx`
- `frontend/src/state/mission.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/guards.ts`
- `frontend/src/ui/RouteTransition.tsx`
- `frontend/src/store/sceneStore.ts`

**Backend**
- `backend/app/main.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/mission.py`
- `backend/app/api/v1/endpoints/taxonomy.py`
- `backend/app/api/v1/endpoints/requirements.py`
- `backend/app/api/v1/endpoints/constellation.py`
- `backend/app/api/v1/endpoints/optimization.py`
- `backend/app/api/v1/endpoints/payload.py`
- `backend/app/api/solve_mission.py`
- `backend/app/api/solve_cubesat.py`
- `backend/app/api/report.py`
- `backend/app/schemas/mission.py`
- `backend/app/schemas/solve_mission.py`
- `backend/app/schemas/taxonomy.py`
- `backend/app/schemas/requirement_derivation.py`
- `backend/app/schemas/subsystem_selection.py`
- `backend/app/schemas/mission_report.py`
- `backend/app/services/taxonomy.py`
- `backend/app/services/full_payload_catalog.py`
- `backend/app/services/catalog.py`
- `backend/app/services/requirements.py`
- `backend/app/services/requirement_derivation.py`
- `backend/app/services/constellation.py`
- `backend/app/services/report.py`
- `backend/app/services/optimization/solver.py`
- `backend/app/services/optimization/cpsat_selection.py`
- `backend/app/services/solve_mission.py`
- `backend/app/data/taxonomy.json`
- `backend/solver/cubesat_solver_runner.py`
- `backend/solver/cubesat_solution_formatter.py`

---

## A) Current frontend route map (verified)

Routes are defined in `frontend/src/App.tsx`.

### Route flow (happy path)
`/` → `/payload` → `/roi` → `/parameters` → `/result`

### Per-route details

#### 1) `/` → Mission Family
1. **route path:** `/`
2. **page component:** `frontend/src/pages/MissionFamilyPage.tsx`
3. **user input:** chooses a mission family card (Remote Sensing / IoT / Navigation).
4. **mission draft reads/writes:**
   - writes: `draft.family` via `setFamily(family_id)`
   - resets: `payload`, `roi`, `parameters` cleared by `setFamily(...)` and also `reset()` is called first
5. **backend calls:**
   - `getTaxonomy()` → `GET /api/v1/taxonomy` (skipped if `VITE_DISABLE_TAXONOMY_FETCH === "1"`)
   - has a local `FALLBACK` list if taxonomy fetch fails
6. **navigation:**
   - on select: `reset(); setFamily(id); nav("/payload")`

#### 2) `/payload` → Payload selection (+ My Payload form)
1. **route path:** `/payload`
2. **page component:** `frontend/src/pages/PayloadPage.tsx`
3. **user input:**
   - picks a **payload category card** (not a specific payload)
   - if category is `my_payload`: fills **partial** My Payload fields (name, mass, L/W/H, avg power, peak power)
     - note: defaults include additional fields (`data_rate_mbps`, `pointing_accuracy_deg`, `thermal_class`) but the UI currently does not render inputs for them
4. **mission draft reads/writes:**
   - reads: `draft.family`, `draft.payload`
   - writes: `draft.payload` via `setPayload(...)`
     - catalog path: `{ type: "catalog", payload_id: <first payload in category> }`
     - my_payload path: `{ type: "my_payload", name, length_mm, width_mm, height_mm, mass_kg, avg_power_w, peak_power_w, ... }`
5. **backend calls:**
   - `getTaxonomy()` → `GET /api/v1/taxonomy` to populate categories and their first payload_id
6. **navigation:**
   - guards: if `draft.family` missing → redirects to `/`
   - Next: `setPayload(...)` then `nav("/roi")`
   - Back button: `backTo="/"` (rendered by `WizardShell`)

#### 3) `/roi` → Region of Interest
1. **route path:** `/roi`
2. **page component:** `frontend/src/pages/RoiPage.tsx`
3. **user input:**
   - toggle: Global Coverage (checkbox)
   - if not global: region query text (min length enforced in UI: 2 chars)
4. **mission draft reads/writes:**
   - reads: `draft.family`, `draft.payload`, `draft.roi`
   - writes: `draft.roi` via `setRoi({ type: "global" } | { type: "region", query })`
5. **backend calls:** none
6. **navigation:**
   - guards:
     - if `draft.family` missing → `/`
     - if `draft.payload` missing → `/payload`
   - Next: `nav("/parameters")`
   - Back button: `backTo="/payload"`

Scene side-effect (not backend): ROI query is also pushed into `zustand` (`useSceneStore`) and geocoded locally via `resolveCountry(...)` for polygon highlight preview.

#### 4) `/parameters` → Mission Parameters
1. **route path:** `/parameters`
2. **page component:** `frontend/src/pages/ParametersPage.tsx`
3. **user input:** revisit time in hours (range slider + numeric input).
4. **mission draft reads/writes:**
   - reads: `draft.parameters?.revisit_time_hours` (default UI value is `48` if unset)
   - writes: `draft.parameters = { revisit_time_hours: hours }` via `setRevisitHours(hours)`
5. **backend calls:** none
6. **navigation:**
   - guards:
     - missing `family` → `/`
     - missing `payload` → `/payload`
     - missing `roi` → `/roi`
   - Finish: `nav("/result")`
   - Back button: `backTo="/roi"`

#### 5) `/result` → Solve + Summary
1. **route path:** `/result`
2. **page component:** `frontend/src/pages/ResultPage.tsx`
3. **user input:** none (this page auto-solves); offers “Download Mission Doc”.
4. **mission draft reads/writes:**
   - reads: entire draft; converts to `MissionInput` via `requireMissionInput(draft)`
   - does not write draft
5. **backend calls:**
   - `solveMission(input)` → `POST /api/v1/mission/solve` with JSON body `{ input: MissionInput }`
   - `downloadMissionReport(input)` → `POST /api/v1/mission/report` (returns Markdown blob)
6. **navigation:**
   - guards enforce previous steps (missing family/payload/roi/parameters → redirect back)
   - Back button: `backTo="/parameters"`

Scene side-effect: after solve, updates constellation counts in `useSceneStore`.

---

## B) Current frontend mission state (MissionDraft) + persistence

Source of truth: `frontend/src/state/mission.tsx`

### 1) Types
- `MissionInput` (frontend): `frontend/src/lib/api.ts`  
  ```
  interface MissionInput {
    family: MissionFamily;
    payload: PayloadSelection;
    roi: Roi;
    parameters: { revisit_time_hours: number };
  }
  ```
- `MissionDraft` (frontend): `frontend/src/state/mission.tsx`
  - defined as `Partial<MissionInput> & { family?; payload?; roi?; parameters?: { revisit_time_hours: number } }`

### 2) localStorage key
- `STORAGE_KEY = "mission_draft_v1"`

### 3) Persisted fields (current)
Persisted as the full `draft` JSON blob:
- `family`
- `payload`
- `roi`
- `parameters.revisit_time_hours`

### 4) Default values
- Default draft: `{}` when storage is empty/unreadable
- UI defaults (not persisted until user action):
  - ParametersPage revisit slider defaults to `48` hours if `draft.parameters` missing
  - PayloadPage MyPayload defaults are hardcoded in component state (only persisted on “Next”)

### 5) updateDraft / reset behavior
In `MissionProvider`:
- `setFamily(family)` overwrites the draft to `{ family, payload: undefined, roi: undefined, parameters: undefined }`
- `setPayload(payload)` persists `{ ...draft, payload }`
- `setRoi(roi)` persists `{ ...draft, roi }`
- `setRevisitHours(hours)` persists `{ ...draft, parameters: { revisit_time_hours: hours } }`
- `reset()` persists `{}`

### 6) Stale localStorage risks
- No schema migration: JSON is parsed “as-is” into `MissionDraft`. Unknown/obsolete keys will remain until overwritten/reset.
- Version pinning is only via the key name (`mission_draft_v1`). Adding fields later is safe, but **changing types/meaning** needs either:
  - a new storage key (`mission_draft_v2`), or
  - a versioned payload + migration function.

### 7) Where key wizard values live
- family: `draft.family`
- payload selection:
  - catalog: `draft.payload = { type: "catalog", payload_id }`
  - custom: `draft.payload = { type: "my_payload", ... }`
- ROI:
  - `draft.roi = { type: "global" }` or `{ type: "region", query }`
- revisit time:
  - `draft.parameters.revisit_time_hours`

### Where future new fields should be added later (do not add yet)
Add to:
- Frontend request shape: `frontend/src/lib/api.ts` → `MissionInput` and associated TS types
- Frontend persisted draft: `frontend/src/state/mission.tsx` → `MissionDraft` + `requireMissionInput`

Proposed insertion points (names to be finalized later):
- `MissionInput.parameters` (extend object) or a new `MissionInput.preferences` block:
  - `altitude_km`
  - `orbit_type`
  - `lifetime_years`
  - `propulsion_preference`
  - `pointing_precision_preference`
  - `downlink_rate_preference`
  - `optimization_priority`
  - `max_budget_usd` (or `cost_cap_kusd`)
  - `max_bus_u` (or `max_bus_size_u`)

---

## C) Current backend API contracts (relevant routes)

Backend app wiring is in `backend/app/main.py`.

### 1) `GET /api/v1/taxonomy`
- **route:** `backend/app/api/v1/endpoints/taxonomy.py`
- **response schema:** `backend/app/schemas/taxonomy.py` → `TaxonomyResponse`
- **used by frontend:** yes (`getTaxonomy()` in `frontend/src/lib/api.ts`)
- **notes:**
  - taxonomy is enriched with “full DB” payloads via `backend/app/services/full_payload_catalog.py`
  - this is availability/listing only; it does not validate that a payload_id is solvable by the current `/api/v1/mission/solve` pipeline

### 2) `POST /api/v1/mission/solve`
- **route:** `backend/app/api/v1/endpoints/mission.py` → `mission_solve(req: MissionSolveRequest)`
- **request schema:** `backend/app/schemas/mission.py` → `MissionSolveRequest` (`{ input: MissionInput }`)
- **response schema:** `backend/app/schemas/mission.py` → `MissionSolveResponse`
- **used by frontend:** yes (`solveMission()` in `frontend/src/lib/api.ts`)
- **solver used:** CP-SAT (OR-Tools) via `backend/app/services/optimization/solver.py` (simple “pick 1 per domain + platform” model)
- **payload_id support:**
  - **catalog payload IDs only** (must exist in `backend/app/data/catalog.json`)
  - **My Payload** supported (the payload numeric fields are used directly)
  - **full MASTER DB payload IDs** are **not** supported by this route today (will raise `Unknown payload_id`)

### 3) `POST /api/v1/mission/report`
- **route:** `backend/app/api/v1/endpoints/mission.py` → `mission_report(...)`
- **request schema:** `MissionReportRequest` (same input as solve)
- **response:** raw Markdown text (`text/markdown`)
- **used by frontend:** yes (`downloadMissionReport()` in `frontend/src/lib/api.ts`)

### 4) `POST /api/solve/cubesat`
- **route:** `backend/app/api/solve_cubesat.py`
- **request schema:** `CubeSatSolveRequest` (`payload_id`, `top_n`, `diagnostic`)
- **response:** untyped JSON `dict[str, Any]`
- **used by frontend:** no (currently unused)
- **solver used:** CP-SAT (OR-Tools) via `backend/solver/cubesat_solver_runner.py`
- **payload_id support:**
  - expects `payload_id` to exist in the loaded solver dataset (`backend/solver/cubesat_data_loader.py` → MASTER DB based)
  - **My Payload/custom payload is not supported** by this route (it only accepts `payload_id`)
- **engineering trace features:** supports `top_n` alternatives and a `diagnostic` mode that probes feasibility bus-by-bus.

### 5) Other solver-adjacent endpoints (not used by current UI)
- `POST /api/solve-mission` (non-v1): `backend/app/api/solve_mission.py` (uses `backend/app/services/solve_mission.py`)
- `POST /api/report.json` and `POST /api/report/download`: `backend/app/api/report.py`
- `POST /api/v1/optimization/subsystems/solve`: `backend/app/api/v1/endpoints/optimization.py` (CP-SAT with margins, risk, optional radiation components)
- `POST /api/v1/requirements/derive`: `backend/app/api/v1/endpoints/requirements.py`
- `POST /api/v1/constellation/estimate`: `backend/app/api/v1/endpoints/constellation.py`

---

## D) Current solve path trace (from the existing Result page)

### 1) Exact file/function chain (current UI)
1. `frontend/src/pages/ResultPage.tsx`
   - builds `input` via `requireMissionInput(draft)`
   - calls `solveMission(input)`
2. `frontend/src/lib/api.ts` → `solveMission(input)`
   - `POST /api/v1/mission/solve` with body `{ input }`
3. `backend/app/api/v1/endpoints/mission.py` → `mission_solve(req)`
   - `catalog = get_catalog()`
   - `requirements = derive_requirements(req.input, catalog)` (`backend/app/services/requirements.py`)
   - `constellation = estimate_constellation(req.input, requirements)` (`backend/app/services/constellation.py`)
   - `solution = solve_subsystems(req.input, requirements, constellation, catalog)` (`backend/app/services/optimization/solver.py`)
4. `backend/app/schemas/mission.py` → `MissionSolveResponse(...)`
5. `frontend/src/pages/ResultPage.tsx` renders summary UI from the response.

### 2) Payload ID passed today
- If catalog payload: a single string `payload_id` chosen as the **first payload** in the selected taxonomy category (`PayloadPage` picks `c.payloads[0].payload_id`).
- If My Payload: a full numeric payload object (dimensions/mass/power; optional data/pointing/thermal fields exist in the type, but are not currently collected in the UI).

### 3) Do full database payload IDs go through CP-SAT today?
Not reliably.
- `/api/v1/taxonomy` can surface MASTER DB payload IDs.
- `/api/v1/mission/solve` only resolves payload IDs against `backend/app/data/catalog.json`. If the selected taxonomy category has **no seeded catalog payloads** and the first payload is from full DB, the solve will fail with `400` (`Unknown payload_id`).

### 4) Result fields currently rendered in the frontend
From `frontend/src/pages/ResultPage.tsx`:
- constellation: `satellites`, `planes` (used for the scene store), and `orbit_type` (displayed)
- solution:
  - platform: `bus_size_u`, `name`
  - budgets: `total_cost_kusd` (displayed), `total_mass_kg` (not currently displayed)
  - subsystems: `domain`, `name`
  - warnings: displayed

### 5) Useful CP-SAT fields currently not exposed in the UI (but already in backend response)
`/api/v1/mission/solve` already returns more than the UI uses, including:
- detailed subsystem fields: `mass_kg`, `avg_power_w`, `peak_power_w`, `cost_kusd`, `metadata`
- budgets: `total_avg_power_w`, `total_peak_power_w`, and margins (`mass_margin_kg`, `avg_power_margin_w`, `peak_power_margin_w`)
- solution `trace: list[str]`

What is *not* currently computed/exposed on this route:
- solver wall time, objective value, solver status, binding-constraint diagnostics

---

## E) Current Result page capability (what it displays today)

Source: `frontend/src/pages/ResultPage.tsx`

Displays:
- **loading state:** “Solving...”
- **error state:** “Solve error: …”
- **constellation:** satellites count + orbit_type label
- **platform:** bus size (U) + platform name
- **cost:** “Indicative Cost” shown as rounded kUSD
- **subsystems list:** domain + name
- **warnings box:** string list (note: bullet character is currently rendered as `â€¢` due to encoding in the string literal)
- **download:** “Download Mission Doc” → `/api/v1/mission/report` (Markdown)

Does not display (even though parts exist in the backend response):
- total mass / total power / margins
- payload summary and derived requirements
- CP-SAT trace details

Gaps vs future engineering-analysis page needs:
- solve time and solver status
- objective score / weights
- binding constraints + margins by constraint
- alternatives/top-N architectures
- bus-by-bus feasibility diagnostics
- detailed budget breakdowns (mass/power/volume/data/thermal/propulsion)

---

## F) Best place to add the new user inputs (recommendation)

Target future inputs:
1. altitude / orbit
2. propulsion preference
3. pointing precision preference
4. downlink rate preference
5. lifetime
6. optimization priority

Recommendation (min-change, preserves current style):
- Extend the existing `ParametersPage` (`/parameters`) into two blocks:
  1) **Mission Parameters (basic):** keep `revisit_time_hours` exactly as-is.
  2) **Advanced Engineering Preferences (new, optional):** altitude/orbit, lifetime, propulsion, pointing, downlink, optimization priority.

Reasons:
- Keeps wizard route flow stable (`/` → `/payload` → `/roi` → `/parameters` → `/result`).
- Keeps new controls in the page that already semantically owns “parameters”.
- Avoids introducing a new route that must be guarded/migrated in `firstMissingStep(...)` and in multiple pages.

Alternative (if ParametersPage must stay minimal):
- Add a new page `"/advanced"` between `/parameters` and `/result` to collect the new fields, and keep `/parameters` focused on revisit time.

---

## G) Best place for the new Solver Analysis page (recommendation)

Goal: new page with three top options/tabs:
1. Selected Design
2. Engineering Budgets
3. Optimization Trace

Recommendation:
- New route path: `"/analysis"` (or `"/solver-analysis"`).
- Reachability: keep `"/result"` as the summary page, add a button/link “Engineering Analysis” that navigates to `"/analysis"`.

Data needs (minimum for tabs):
- Selected Design: selected bus/platform, selected subsystems (+ tiers if using tiered solver), totals.
- Engineering Budgets: mass/power/volume margins; ideally downlink/storage/thermal/propulsion margins too.
- Optimization Trace: solver status, objective value, solve time, key constraint slacks/binding constraints, and (optionally) alternatives/top-N.

Avoid rerunning the solver:
- Short term (frontend-only): cache the last solve response in-memory (context) + persist a copy in localStorage keyed by a hash of `MissionInput`.
- Longer term (backend-assisted): backend returns a `solve_id` and stores results in a short-lived cache; `"/analysis"` fetches by `solve_id`.

Refresh behavior:
- If user refreshes `"/analysis"`:
  - if local cache exists for the current mission input hash, render it;
  - otherwise re-run solve once (explicit “Recompute” button) and store.

---

## H) Backend gap analysis for engineering trace (CP-SAT diagnostics)

This repo currently contains **three** “solver-shaped” outputs with different trace richness:

1) **Current UI path:** `/api/v1/mission/solve` → `backend/app/services/optimization/solver.py`  
2) **Richer v1 CP-SAT:** `/api/v1/optimization/subsystems/solve` → `backend/app/services/optimization/cpsat_selection.py`  
3) **Tiered CP-SAT (MASTER DB):** `/api/solve/cubesat` → `backend/solver/*`

Requested engineering-trace fields classification:

| Field | `/api/v1/mission/solve` | `/api/v1/optimization/subsystems/solve` | `/api/solve/cubesat` |
|---|---|---|---|
| solver status | not exposed (only errors) | **already available** (`feasible`, `status`) | **already available** (`status`) |
| selected bus/platform | **already available** (`solution.platform`) | **already available** (`selected` includes `structure`) | **already available** (`selection.bus_class`) |
| selected subsystem tiers | not applicable (no tiers) | not tiers (component IDs) | **already available** (`selection.*_tier`) |
| total mass / power / cost | **already available** (budgets) | **already available** (`totals`) | **already available** (`totals`) |
| solve time | available internally but not exposed | available internally but not exposed | **already available** (`solver_stats.wall_time_s`) |
| objective score | available internally but not exposed | available internally but not exposed | **already available** (`objective_value`) |
| bus oversize | not computed | **already available** (via `bus_volume_margin_u`) | **already available** (`totals.BusOversize_u`) |
| constraints/margins | **already available** (mass/power margins only) | **already available** (mass/power/bus-volume margins) | **already available** (margins in diagnostic mode; totals include oversize proxy) |
| bus-by-bus diagnostic | not supported | not supported | **already available** (`diagnostic: true` → `bus_cases`) |
| alternatives / top-N | not supported | not supported | **already available** (`top_n > 1`) |

Summary:
- If the engineering cockpit needs “Optimization Trace” and alternatives, `/api/solve/cubesat` is already closest (it already returns objective + wall time + diagnostic + top-N).
- If the cockpit must stay aligned to the current mission wizard input (family/ROI/revisit/MyPayload), the best *nearby* route to extend is `/api/v1/optimization/subsystems/solve` (it already has feasibility, margins, risk points, trace strings), but it still lacks solve time/objective and top-N/diagnostic.

---

## I) Risk analysis + mitigations

1) **Breaking existing wizard navigation**
- Risk: adding a new step/route requires updating guards in every page + `firstMissingStep(...)`.
- Mitigation: prefer extending `ParametersPage` first; if adding a new route, update guards centrally and add testIDs per page.

2) **Stale localStorage migration**
- Risk: `mission_draft_v1` may contain old/new fields with no migration.
- Mitigation: bump storage key (`mission_draft_v2`) when changing meaning/types; or store `{ version, draft }` and migrate on load.

3) **Frontend/backend schema mismatch**
- Risk: frontend TS types (`frontend/src/lib/api.ts`) currently under-specify the backend response; future additions may diverge.
- Mitigation: define shared JSON schemas (or generate TS from Pydantic/OpenAPI), or at minimum add explicit `MissionSolveResponse` typing that matches backend.

4) **CP-SAT output shape mismatch (v1 vs tiered solver)**
- Risk: `/api/v1/mission/solve` output is “platform + domain subsystems”, but `/api/solve/cubesat` output is “bus_class + tier selections + totals”.
- Mitigation: design an adapter response for the analysis page with a stable “Selected Design” shape; keep both raw payloads for deep trace.

5) **Infeasible payload handling**
- Risk: tiered solver can return `INFEASIBLE`; current result page expects success or throws.
- Mitigation: add explicit infeasible UI state + guidance; include “why infeasible” (diagnostic families/margins) where available.

6) **Docker env / proxy / CORS issues**
- Risk: different origins for Vite and API; taxonomy fetch can fail.
- Mitigation: keep fallback taxonomy (already present) and document required `CORS_ORIGINS`; add a health check gating.

7) **Custom payload not supported by tiered CP-SAT**
- Risk: `My Payload` currently exists in the wizard, but `/api/solve/cubesat` only accepts `payload_id`.
- Mitigation: either (a) keep “My Payload” on the v1 CP-SAT pipeline initially, or (b) implement a “payload synthesis → temporary payload_id” adapter later.

8) **Large diagnostic response size**
- Risk: `diagnostic: true` can return many bus cases and margin details; `top_n` can return multiple full solutions.
- Mitigation: return summaries by default; lazy-load deep diagnostics per tab; add pagination/top_n limits (already capped at 50).

9) **Repeated solver runtime on page reload**
- Risk: `/result` re-solves on each mount; analysis page could re-solve too.
- Mitigation: cache results in localStorage by input hash; backend `solve_id` cache later; add explicit “Recompute” button.

---

## J) Recommended implementation sequence (Prompts 15B+)

1) **Prompt 15B:** extend mission state/schema (frontend + backend request types) to carry new inputs (no UI changes beyond wiring if required by prompt).  
2) Add/extend backend endpoint to accept the new fields **without changing CP-SAT math**, ideally by:
   - extending `/api/v1/mission/solve` response to include solver stats (wall time, objective) and richer budgets, or
   - adding a parallel “analysis” endpoint that wraps existing solver outputs.
3) Add analysis route `"/analysis"` (UI skeleton only) that can render the stored solve output without re-solving.
4) Expose diagnostic/top-N only when the analysis tabs request it (avoid heavy payloads on normal solves).

