# Payload Taxonomy Full-DB Integration Report (Prompt 14A)

Date: 2026-05-02  
Scope: Backend-only integration/mapping work to make `GET /api/v1/taxonomy` reflect payload availability from the **full MASTER payload databases** while preserving existing v1 seeded behavior as a safe fallback.

## 1) Files changed

Added:
- `backend/app/data/payload_category_mapping.json`
- `backend/app/services/full_payload_catalog.py`
- `docs/PAYLOAD_TAXONOMY_FULL_DB_INTEGRATION_REPORT.md`

Updated:
- `backend/app/services/taxonomy.py`
- `backend/tests/test_taxonomy.py`

No frontend files were changed.

## 2) Category mappings added

Mapping file: `backend/app/data/payload_category_mapping.json`

Remote Sensing (`remote_sensing`) category → full DB `payload_variant` mapping:

- `hyperspectral` → `Hyperspectral Imagers`
- `vhr_optical` → `Visible Light Cameras`, `Panchromatic Cameras`
- `thermal` → `NIR Sensors`, `SWIR Sensors`, `MWIR Sensors`, `LWIR Sensors`
- `sar` → `X-Band SAR`, `C-Band SAR`, `L-Band SAR`, `P-Band SAR`
- `multispectral` → **status: `missing_explicit_db_variant`** (kept disabled; no explicit “Multispectral” variant exists in the Remote Sensing master DB)
- `my_payload` → **status: `manual_frontend`** (UI-controlled special input)

## 3) How taxonomy enrichment works now

File: `backend/app/services/taxonomy.py`

For each `(family_id, category_id)`:

1. Load v1 seeded options from `backend/app/data/catalog.json` (existing behavior).
2. Load full DB options via `backend/app/services/full_payload_catalog.py:list_payload_options_for_category()`,
   using `backend/app/data/payload_category_mapping.json` to select which `payload_variant` values belong to the category.
3. If full DB returns options:
   - Merge **seeded first**, then full DB options (dedup by `payload_id`).
   - Rationale: preserve existing known-working seeded selections while exposing full DB availability.
4. If full DB returns no options:
   - Use seeded options only (fallback).

## 4) Taxonomy response counts (before/after)

### Before (pre-14A)

Remote Sensing payload counts (from the prior diagnosis run):

- `hyperspectral`: `1` (seeded)
- `vhr_optical`: `1` (seeded)
- `thermal`: `0`
- `sar`: `0`
- `multispectral`: `0`

### After (post-14A)

Remote Sensing payload counts (from `GET /api/v1/taxonomy` after this patch):

- `hyperspectral`: `6` (seeded `rs_hyperspec_v1` + full DB hyperspectral options)
- `vhr_optical`: `16` (seeded `rs_vhr_optical_v1` + full DB VIS+PAN options)
- `thermal`: `20` (full DB NIR+SWIR+MWIR+LWIR sensors)
- `sar`: `10` (full DB X/C/L/P-band SAR)
- `multispectral`: `0` (explicitly kept unavailable)

Representative full DB IDs now present in taxonomy:

- Thermal sample: `RS-EO-LWIR-001` … `RS-EO-LWIR-005`
- SAR sample: `RS-EO-CSAR-001`, `RS-EO-LSAR-001`, `RS-EO-PSAR-001`, …

## 5) Which frontend cards should now show SELECT (no frontend changes needed)

Because the frontend marks a card selectable when `category.payloads[]` is non-empty:

- Remote Sensing:
  - Hyperspectral: **SELECT** (still, seeded remains first)
  - VHR Optical: **SELECT** (still, seeded remains first)
  - Thermal: **SELECT** (now non-empty via full DB mapping)
  - SAR: **SELECT** (now non-empty via full DB mapping)
  - Multispectral: **COMING SOON** (kept empty by design)
  - My Payload: frontend-special-cased; remains **SELECT**

## 6) Tests added/updated

File: `backend/tests/test_taxonomy.py`

- Verifies `/api/v1/taxonomy` now returns non-empty payload lists for:
  - `remote_sensing.thermal`
  - `remote_sensing.sar`
- Verifies those IDs look like full DB Remote Sensing IDs (prefix `RS-`).
- Verifies `remote_sensing.multispectral` remains empty.
- Verifies seeded v1 payload IDs still appear when full DB listing is disabled via monkeypatch (fallback behavior).

## 7) Confirmation (constraints)

- No frontend changes.
- No solver math changes.
- No modifications to MASTER payload DB content.
- `backend/app/data/catalog.json` was not deleted or rewritten (still used and preserved as seeded fallback).

