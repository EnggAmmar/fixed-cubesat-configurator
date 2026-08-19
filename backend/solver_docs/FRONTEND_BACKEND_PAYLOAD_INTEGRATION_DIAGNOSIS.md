# FRONTEND ↔ BACKEND Payload Integration Diagnosis (ONE_V3)

Date: 2026-05-02  
Repo HEAD: `4c63abb` (local branch `main`)  

This document is a **diagnostic report only**. It explains why some payload cards show **Coming soon** even though the repository contains Remote Sensing payload records and a CP-SAT solver dataset.

Explicit statement: **NO CODE CHANGES APPLIED IN THIS DIAGNOSTIC PASS** (except adding this Markdown report).

---

## 1) Current observed UI behavior (Select Payload)

### Docker reproduction status

- The `docker` CLI is **not available** in this environment (`docker` command not found), so `docker compose up --build` could not be executed here.
- To still confirm behavior end-to-end, the backend (`uvicorn`) and frontend (`vite`) were run locally and the UI was inspected via headless Playwright against `http://127.0.0.1:5173`.

### Observed Remote Sensing payload cards

On the **Select Payload** screen (Remote Sensing family), the cards render as:

| Card label | UI CTA |
|---|---|
| Hyperspectral | Select |
| Multispectral | Coming soon |
| VHR Optical | Select |
| Thermal | Coming soon |
| SAR | Coming soon |
| My Payload | Select |

This matches the behavior described in the issue report.

---

## 2) Where “Coming soon” is defined (frontend)

**Primary UI logic**

- File: `frontend/src/pages/PayloadPage.tsx`
- Component: `PayloadPage`
- Rendered CTA text:
  - `p.disabled ? "Coming soon" : "Select"`
- The disable/enable logic:
  - For category `my_payload`: always enabled (`disabled: false`)
  - For all other categories:
    - `const payloadId = c.payloads[0]?.payload_id;`
    - `disabled: !payloadId`
    - If the backend taxonomy returns **zero payloads** for a category, the card is disabled and shows **Coming soon**

**No other instances**

- The string `"Coming soon"` appears only in `frontend/src/pages/PayloadPage.tsx`.

---

## 3) Payload cards: source of truth (what drives the UI)

### What the frontend uses

- File: `frontend/src/lib/api.ts`
- `getTaxonomy()` performs `GET /api/v1/taxonomy`
- The payload page uses `taxonomy.families[].payload_categories[].payloads[]`
- **Availability is entirely determined by** whether each category’s `payloads` array is non-empty.

### How `/api/v1/taxonomy` is built (backend)

- Route: `backend/app/api/v1/endpoints/taxonomy.py` (`GET /taxonomy`)
- Implementation: `backend/app/services/taxonomy.py:get_taxonomy()`
  - Loads base categories from `backend/app/data/taxonomy.json`
  - Enriches each category by listing matching payloads from `backend/app/data/catalog.json` via:
    - `backend/app/services/catalog.py:get_catalog()`
    - `catalog.list_payloads(family=..., category_id=...)`

### Key finding

Even though the repository contains a large payload database in `backend/data_base/...`, the **UI taxonomy enrichment is driven by `backend/app/data/catalog.json`** (explicitly described as “Seeded example data” in `README.md`).

So, “Coming soon” currently means:

> “No representative payload was added to `backend/app/data/catalog.json` for this mission family + category_id.”

---

## 4) Per-card mapping (Remote Sensing) — what the UI expects vs what exists

The Remote Sensing categories come from `backend/app/data/taxonomy.json`:

- `hyperspectral`
- `multispectral`
- `vhr_optical`
- `thermal`
- `sar`
- `my_payload`

The backend taxonomy enrichment currently yields these counts (from `/api/v1/taxonomy`):

- `hyperspectral: 1`
- `multispectral: 0`
- `vhr_optical: 1`
- `thermal: 0`
- `sar: 0`
- `my_payload: 0` (special-cased enabled in frontend anyway)

### Card-by-card (what is actually driving availability today)

| Visible card label | Frontend key (`category_id`) | Backend `/api/v1/taxonomy` payloads | Current availability is… |
|---|---:|---:|---|
| Hyperspectral | `hyperspectral` | `["rs_hyperspec_v1"]` | Data-driven from `backend/app/data/catalog.json` |
| Multispectral | `multispectral` | `[]` | Data-driven from `backend/app/data/catalog.json` (empty ⇒ Coming soon) |
| VHR Optical | `vhr_optical` | `["rs_vhr_optical_v1"]` | Data-driven from `backend/app/data/catalog.json` |
| Thermal | `thermal` | `[]` | Data-driven from `backend/app/data/catalog.json` (empty ⇒ Coming soon) |
| SAR | `sar` | `[]` | Data-driven from `backend/app/data/catalog.json` (empty ⇒ Coming soon) |
| My Payload | `my_payload` | `[]` | **Hardcoded enabled** in `frontend/src/pages/PayloadPage.tsx` |

### Expected mapping to the “full” payload database (not currently wired)

The repository also contains a larger Remote Sensing payload dataset:

- File: `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`

That dataset uses `payload_variant` labels such as:

- `Hyperspectral Imagers`
- `Visible Light Cameras`
- `Panchromatic Cameras`
- `NIR Sensors`, `SWIR Sensors`, `MWIR Sensors`, `LWIR Sensors`
- `X-Band SAR`, `C-Band SAR`, `L-Band SAR`, `P-Band SAR`

**Important:** there is currently **no code path** mapping `category_id` (e.g. `thermal`, `sar`) to these `payload_variant` strings for the v1 UI taxonomy payload lists.

---

## 5) Backend/database payload availability (Remote Sensing DB)

### Database file inspected

- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`

### Counts & sample payload IDs by variant (subset relevant to the UI cards)

- Hyperspectral-like:
  - `Hyperspectral Imagers`: 5 payloads (e.g. `RS-EO-HSI-001` … `RS-EO-HSI-005`)
- Optical-like (VHR Optical could map here, but no mapping exists today):
  - `Visible Light Cameras`: 10 payloads (e.g. `RS-EO-VIS-001` …)
  - `Panchromatic Cameras`: 5 payloads (e.g. `RS-EO-PAN-001` …)
- Thermal / IR-like:
  - `NIR Sensors`: 5 payloads
  - `SWIR Sensors`: 5 payloads
  - `MWIR Sensors`: 5 payloads
  - `LWIR Sensors`: 5 payloads
- SAR-like:
  - `X-Band SAR`: 3 payloads
  - `C-Band SAR`: 2 payloads
  - `L-Band SAR`: 3 payloads
  - `P-Band SAR`: 2 payloads

### Multispectral note (DB naming mismatch)

No `payload_variant` containing “Multispectral” exists in `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`.

If the UI’s `multispectral` category is expected to map to something in the database, that mapping must be defined explicitly (e.g., map to `Visible Light Cameras` and/or specific VIS+NIR/SWIR products), or the database would need an explicit multispectral variant.

---

## 6) Backend solver feasibility (representative checks)

There are **two different solver flows** present in this repo:

1) **v1 UI flow** (the UI currently uses this):
   - Frontend calls `POST /api/v1/mission/solve` (see `frontend/src/lib/api.ts`)
   - This path uses the **seeded v1 catalog**:
     - `backend/app/data/catalog.json`
     - `backend/app/services/optimization/solver.py` (via API)

2) **Legacy/alternate CubeSat solver API** (not called by the current frontend):
   - `POST /api/solve/cubesat` (see `backend/app/api/solve_cubesat.py`)
   - Uses CP-SAT data loader reading master payload DB files:
     - `backend/solver/cubesat_data_loader.py` → `backend/data_base/*/MASTER_*.json`

### v1 UI solver (current selectable payloads)

The currently selectable catalog payloads solve successfully via `/api/v1/mission/solve`:

- `rs_hyperspec_v1` → solved (example output selected `6U Platform (Plus)`)
- `rs_vhr_optical_v1` → solved (example output selected `6U Platform (Plus)`)

### CubeSat solver (examples from the full payload DB)

Representative runs using `backend/solver/cubesat_solver_runner.py`:

- Optical proxy:
  - `RS-EO-VIS-001` → `OPTIMAL` (bus `16U`)
  - `RS-EO-PAN-001` → `OPTIMAL` (bus `16U`)
- Thermal proxy:
  - `RS-EO-LWIR-004` → `OPTIMAL`, but feasibility-by-bus shows **not feasible at `16U`**, feasible at `27U`+
- Hyperspectral proxy:
  - `RS-EO-HSI-001` → `INFEASIBLE` (in this solver formulation)
- SAR proxy (multiple):
  - `RS-EO-XSAR-001`, `RS-EO-XSAR-002`, `RS-EO-CSAR-001`, `RS-EO-LSAR-001`, `RS-EO-PSAR-002` → `INFEASIBLE`

Takeaway:

- Even if the UI were wired directly to the “full” payload DB, **some categories may still be infeasible** under the current CP-SAT capacity libraries (especially SAR, and at least one hyperspectral example).
- Thermal/IR examples may require bus classes **larger than the v1 mission API platform list** (which currently tops out at `16U` in `backend/app/data/catalog.json`).

---

## 7) API integration status (frontend ↔ backend)

### Frontend API calls

- Taxonomy:
  - `GET /api/v1/taxonomy` (`frontend/src/lib/api.ts:getTaxonomy`)
- Solver:
  - `POST /api/v1/mission/solve` (`frontend/src/lib/api.ts:solveMission`)
- Report download:
  - `POST /api/v1/mission/report` (`frontend/src/lib/api.ts:downloadMissionReport`)

No frontend references to:

- `POST /api/solve/cubesat`

### Docker wiring (as defined in repo)

- Compose file: `docker-compose.yml`
  - Backend exposed as `8000:8000`
  - Frontend exposed as `3000:80`
- Nginx proxy: `frontend/nginx.conf`
  - Proxies `/api/` → `http://backend:8000`
- CORS:
  - `docker-compose.yml` sets `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`
  - Backend parses `CORS_ORIGINS` in `backend/app/main.py`

Conclusion:

- The frontend **is** talking to the backend for taxonomy/availability.
- The “Coming soon” state is not coming from browser/network errors; it is produced by the backend taxonomy response (empty `payloads[]` arrays).

---

## 8) Root cause analysis (classification + evidence)

### Root cause RC-1 — Seeded v1 catalog is missing categories (stale / incomplete availability source)

Classification: **(1) frontend hardcoded availability flags are stale** (more precisely: backend provides stale payload availability via a seeded catalog), and **(3) backend lacks a payload listing endpoint** for the full database that the user expects.

Evidence:

- `backend/app/data/catalog.json` contains only:
  - `rs_hyperspec_v1` (`hyperspectral`)
  - `rs_vhr_optical_v1` (`vhr_optical`)
- Therefore `/api/v1/taxonomy` returns empty `payloads[]` for `multispectral`, `thermal`, `sar`
- `frontend/src/pages/PayloadPage.tsx` disables cards when `payloads[0]` is missing, rendering “Coming soon”
- `README.md` explicitly frames `backend/app/data/catalog.json` as “Seeded example data in v1 scope”

Files involved:

- Frontend:
  - `frontend/src/pages/PayloadPage.tsx`
  - `frontend/src/lib/api.ts`
- Backend (v1 taxonomy + catalog):
  - `backend/app/services/taxonomy.py`
  - `backend/app/services/catalog.py`
  - `backend/app/data/catalog.json`
  - `backend/app/data/taxonomy.json`

Fix scope: **backend-only** (update catalog/enrichment) or **integration-level** (wire taxonomy to full DB).

### Root cause RC-2 — Category naming/mapping gap (Multispectral)

Classification: **(2) frontend card labels do not map to backend payload variant names** and/or **(6) database truly missing payload type** (as named).

Evidence:

- UI category: `multispectral` (from `backend/app/data/taxonomy.json`)
- Full Remote Sensing DB has no `payload_variant` labeled “Multispectral”

Files involved:

- `backend/app/data/taxonomy.json`
- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`

Fix scope: **integration-level** (define mapping), possibly **database** if an explicit multispectral variant is desired.

### Root cause RC-3 — Solver feasibility/limits may justify keeping some cards disabled (not currently the gating logic)

Classification: **(7) payload exists but solver returns infeasible** (observed for SAR examples; at least one hyperspectral example).

Evidence:

- Full CP-SAT solver (`backend/solver/...`) reports SAR examples as `INFEASIBLE`.
- Thermal example required `27U`+ buses, while the v1 mission API catalog platforms top out at `16U`.

Important nuance:

- The current UI’s “Coming soon” gating is **not** computed from solver feasibility; it is computed from presence/absence in `backend/app/data/catalog.json`.
- However, feasibility evidence suggests that **enabling cards blindly** could expose users to solver infeasibility unless representative payloads and platform limits are aligned.

Fix scope: **integration-level** (select feasible representative payloads per category and ensure the v1 mission solver can support them).

---

## 9) Recommended minimal fix plan (later patch; not applied here)

Minimal, safe plan (do not “blindly enable”):

1) Decide which solver + dataset is the source of truth for the UI:
   - Keep v1 mission solver with curated representatives (`backend/app/data/catalog.json`), or
   - Switch payload selection to the full CP-SAT DB (`backend/data_base/...`) and expose an API to list payloads by category.
2) If staying with v1 mission solver:
   - Add **one representative, solvable payload** per category you want selectable into `backend/app/data/catalog.json` (and ensure platforms support it).
   - Keep SAR/hyperspectral disabled if they are not feasible under the intended constraints, or add smaller representative payloads if available.
3) If integrating the full DB:
   - Add an API endpoint that lists payloads by `mission_family` + `category_id` by mapping category IDs to DB `payload_variant` sets.
   - Update taxonomy enrichment to use that endpoint/source instead of `backend/app/data/catalog.json`.
4) For Multispectral:
   - Define an explicit mapping (e.g., to `Visible Light Cameras` + some band constraints), or add a dedicated multispectral variant to the DB.

---

## 10) Files that would likely need modification in a later patch

Depending on the chosen approach:

- Backend (v1 catalog approach):
  - `backend/app/data/catalog.json`
  - Potentially `backend/app/services/taxonomy.py`
- Backend (full DB integration approach):
  - `backend/app/api/v1/endpoints/*` (new listing endpoint)
  - `backend/app/services/taxonomy.py` (enrichment source)
  - `backend/solver/cubesat_data_loader.py` (if reused for listing/mapping)
- Frontend (only if UX changes are desired; not required for catalog-only fix):
  - `frontend/src/pages/PayloadPage.tsx` (only if selection behavior changes)

---

## 11) Notes about local workspace state during this diagnosis

- Prior to `git pull`, there were local unstaged modifications to:
  - `backend/data_base/IoT_Comm/Block_A_pt1.json`
  - `backend/data_base/Navigation/Block_A.json`
  - `backend/data_base/Navigation/Block_B.json`
- These were stashed (to allow a clean pull) with message:
  - `diag: stash local DB json edits before pull`
- `git pull --ff-only` reported: “Already up to date.”

