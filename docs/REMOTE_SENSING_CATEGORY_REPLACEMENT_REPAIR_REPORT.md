# Remote Sensing Category Replacement — Repair Report (Prompt 14E-REPAIR)

## Summary
After replacing the unsupported **Multispectral** UI category with **Infrared Imaging** (`infrared_imaging`), a report came in that the **Select Payload** page rendered **no payload cards** (blank grid) while the page shell still loaded.

In this workspace I could **not reproduce a blank grid** (taxonomy returned HTTP 200 and the Playwright full wizard flow passed). However, the code path had a clear failure mode that *would* produce the exact symptom in any environment where `/api/v1/taxonomy` errors.

This repair hardens the backend taxonomy enrichment so that **a single full-DB enrichment exception cannot 500 the taxonomy endpoint** and therefore cannot blank the payload card grid.

## Root Cause (code-level)
`frontend/src/pages/PayloadPage.tsx` renders payload cards strictly from `GET /api/v1/taxonomy`. If the taxonomy request fails or returns non-JSON, `getTaxonomy()` rejects and `family` is set to `null`, which makes `options` an empty array and the card grid renders **nothing**.

Before this repair, `backend/app/services/taxonomy.py` did **not** isolate exceptions from:
- full database enrichment (`list_payload_options_for_category(...)`)
- seeded catalog enrichment (`catalog.list_payloads(...)`)

So if full-DB enrichment raised (e.g., missing/invalid `payload_category_mapping.json`, JSON parse error, file path issues in a container), `/api/v1/taxonomy` could return **HTTP 500**, producing the frontend’s blank card grid.

## What I Observed Locally
### Backend
- `GET /api/v1/taxonomy` → **200** with `Content-Type: application/json`
- Remote Sensing payload counts (from `get_taxonomy()`):
  - `hyperspectral`: 6
  - `infrared_imaging`: 10
  - `vhr_optical`: 16
  - `thermal`: 10
  - `sar`: 10
  - `my_payload`: 0

### Frontend
- Playwright full flow (`frontend/tests/e2e/wizard.spec.ts` with `E2E_FULL=1`) passed.
- No runtime exceptions seen; only non-fatal WebGL/THREE warnings.

## Fix Applied (smallest safe change)
### Backend: make taxonomy enrichment exception-safe
File: `backend/app/services/taxonomy.py`
- Wrapped seeded-catalog enrichment and full-DB enrichment per-category in `try/except`.
- On exception, logs and falls back to whichever payload list is still available, ensuring taxonomy response still returns categories and payload arrays instead of 500’ing.

### Tests
File: `backend/tests/test_taxonomy.py`
- Added regression test `test_taxonomy_endpoint_survives_full_db_enrichment_exception` that forces `list_payload_options_for_category` to raise and asserts:
  - taxonomy endpoint still returns **HTTP 200**
  - categories still exist
  - seeded payload IDs are still present (fallback behavior)

## Files Changed
- `backend/app/services/taxonomy.py`
- `backend/tests/test_taxonomy.py`
- `docs/REMOTE_SENSING_CATEGORY_REPLACEMENT_REPAIR_REPORT.md`

## Docker / Cache Notes
This runtime environment does not have the `docker` CLI available, so I could not perform a Compose rebuild check here. The backend change is designed to make taxonomy resilient even when a container environment has partial/full-DB enrichment problems.

## Tests Run
- `python -m pytest -q backend/tests` → **51 passed**
- `npx playwright test wizard.spec.ts` with `E2E_FULL=1` → **passed**

## Before/After Category List (Remote Sensing)
- Before: included `multispectral` (disabled due to missing explicit DB variant)
- After: `multispectral` removed; `infrared_imaging` added and mapped to DB-backed NIR/SWIR payload variants

## Verdict
**FIXED_EMPTY_PAYLOAD_GRID**

Reason: taxonomy endpoint can no longer fail entirely due to a full-DB enrichment error; the frontend will receive a valid taxonomy response (at minimum the base taxonomy + seeded catalog fallback), preventing an empty options list and a blank payload grid.

## Confirmation
- No solver math or CP-SAT constraints changed.
- No MASTER payload database files were modified.
- No frontend styling changes were made.

