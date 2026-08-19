# Blank Payload Grid — Investigation Report (Docker build symptom)

## Report Date
2026-05-03

## Symptom (as reported)
- Select Payload page shell renders (title + Next button), but the **payload card grid is blank** for all mission families.

## Most Likely Failure Mode
The payload grid is blank when `frontend/src/pages/PayloadPage.tsx` computes:
- `family === null` OR `family.payload_categories` is empty

That happens if `getTaxonomy()` fails (network/500) or if `/api/v1/taxonomy` returns an unexpected/empty shape.

The most common root cause in Docker is:
1. `GET /api/v1/taxonomy` returns **HTTP 500** (backend exception), so the frontend `.catch()` runs and sets `family=null`.

## Evidence Available In This Runtime
Docker evidence was provided from the user’s environment (WSL2 + Docker Compose).

### 1) Host → backend direct (port 8000)
Command:
- `curl -i http://localhost:8000/api/v1/taxonomy`

Result:
- **HTTP/1.1 200 OK**
- `content-type: application/json`
- Response includes:
  - `version: "v1"`
  - `families`: `remote_sensing`, `iot_communication`, `navigation`
  - `remote_sensing.payload_categories`: present and non-empty (includes `hyperspectral`, `multispectral`, `vhr_optical`, `thermal`, `sar`, `my_payload`)

### 2) Host → frontend nginx → backend proxy (port 3000)
Command:
- `curl -i http://localhost:3000/api/v1/taxonomy`

Result:
- **HTTP/1.1 200 OK**
- `Server: nginx/...`
- `Content-Type: application/json`
- Response body matches the backend direct response shape (families + payload_categories present).

### 3) Backend container logs (tail)
Command:
- `docker compose logs backend --tail=200`

Result (relevant lines):
- backend served `GET /api/v1/taxonomy` with **200 OK**.

### 4) Frontend container logs (tail)
Command:
- `docker compose logs frontend --tail=200`

Result (relevant lines):
- nginx served `GET /api/v1/taxonomy` with **200** (as seen from curl).

### Key conclusion from Docker evidence
The failure is **not** the backend taxonomy endpoint and **not** the nginx `/api/` proxy.
Both `/api/v1/taxonomy` routes (direct 8000 and proxied via 3000) return HTTP 200 with non-empty `families[].payload_categories[]`.

This strongly suggests the blank grid is due to **frontend runtime state** (e.g., `draft.family` mismatch causing `find(...) ?? null`, stale `localStorage` mission state, or a browser-side runtime exception preventing taxonomy state from being applied).

## Exact Root Cause (code-level)
Updated classification based on Docker evidence:
- Backend/proxy: **healthy** (HTTP 200, correct JSON shape).
- Most likely: **(3) taxonomy returns families but no matching selected `family_id`**, or a **frontend runtime exception** preventing `family` from being set.

Specific backend weakness:
- `backend/app/services/taxonomy.py` previously performed per-category enrichment without exception isolation.
- Any exception in full DB enrichment (missing/invalid mapping file, path issues, JSON parse error, etc.) could crash `get_taxonomy()` and therefore 500 `/api/v1/taxonomy`.
- Frontend hides this failure by catching and setting `family=null`, yielding a blank UI grid.

## Minimal Safe Fix Applied
### 1) Make taxonomy enrichment exception-safe (prevents blank grid)
File: `backend/app/services/taxonomy.py`
- Wrapped **seeded catalog** enrichment and **full DB** enrichment in per-category `try/except`.
- On exception: logs and falls back to seeded payloads (or empty list), but still returns the taxonomy response.

This ensures:
- `/api/v1/taxonomy` should keep returning **HTTP 200** even if one category’s enrichment fails.
- The frontend still receives `payload_categories` and renders cards instead of a blank grid.

Note: Docker evidence shows taxonomy is already HTTP 200. The remaining blank-grid cause is therefore likely frontend state, but the backend hardening remains a safe guardrail.

### 2) Add regression test for endpoint health
File: `backend/tests/test_taxonomy_endpoint_health.py`
- Asserts `/api/v1/taxonomy` returns 200
- Asserts `families` exists and each family has non-empty `payload_categories`
- Asserts required keys exist for each category

## Files Inspected (relevant to root cause)
- `frontend/src/pages/PayloadPage.tsx` (grid renders from `family.payload_categories`)
- `frontend/src/lib/api.ts` (calls `/api/v1/taxonomy`)
- `frontend/nginx.conf` (Docker proxy for `/api/`)
- `docker-compose.yml` (ports/proxy topology)
- `backend/app/api/v1/endpoints/taxonomy.py` (route definition)
- `backend/app/services/taxonomy.py` (enrichment + failure mode)
- `backend/app/services/full_payload_catalog.py` (full DB mapping + file IO)
- `backend/app/data/taxonomy.json` (base taxonomy categories)
- `backend/app/data/payload_category_mapping.json` (category→variant mapping)

## Files Changed
- `backend/app/services/taxonomy.py`
- `backend/tests/test_taxonomy.py` (added exception-survival regression test earlier)
- `backend/tests/test_taxonomy_endpoint_health.py`
- `docs/BLANK_PAYLOAD_GRID_INVESTIGATION_REPORT.md`

## Tests Run
- `python -m pytest -q backend/tests` → **passed** (52 tests)

## Docker Rebuild Result
User environment shows taxonomy endpoint works in Docker; blank grid persists despite that.

Next required evidence to isolate the exact frontend cause:
1. Browser DevTools Network: the actual `GET /api/v1/taxonomy` request the UI makes (status + response).
2. Browser console errors on the Select Payload page.
3. Browser console output for:
   - `localStorage.getItem("mission_draft_v1")`
   - confirm `family` equals one of: `remote_sensing`, `iot_communication`, `navigation`

## What To Capture In Your Docker Environment (to confirm)
1. Browser Network: `GET http://localhost:3000/api/v1/taxonomy`
   - status code + response body (or error body)
2. Backend logs around the taxonomy request (`docker compose logs backend`)
3. Host curl:
   - `curl -i http://localhost:8000/api/v1/taxonomy`

If you still see a blank grid after this patch, the next likely causes are:
- nginx `/api/` proxy not routing to backend container (network/DNS issue)
- frontend was built with `VITE_DISABLE_TAXONOMY_FETCH=1` (would disable fetch and leave grid empty)
- taxonomy.json in the image/volume has empty `payload_categories`

## Final Verdict
**NOT_FIXED (Docker)** — backend/proxy are healthy; blank grid persists due to frontend runtime/state.
Backend hardening is complete, but an additional frontend-side diagnosis is required using browser console + localStorage state.
