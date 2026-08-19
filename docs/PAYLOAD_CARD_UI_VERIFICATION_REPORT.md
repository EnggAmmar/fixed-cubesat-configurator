# Payload Card UI Verification Report (Prompt 14B)

Date: 2026-05-02  
Goal: Verify the frontend “Select Payload” cards reflect backend taxonomy availability after Prompt 14A (full DB taxonomy enrichment).

## 1) Backend taxonomy counts (Remote Sensing)

Backend started locally (already running on `http://127.0.0.1:8000`).

Call: `GET /api/v1/taxonomy`

Remote Sensing category payload counts observed:

- `hyperspectral`: `6`
- `multispectral`: `0`
- `vhr_optical`: `16`
- `thermal`: `20`
- `sar`: `10`
- `my_payload`: `0`

This matches the expected Prompt 14A outcome (thermal/sar now non-empty; multispectral remains empty; my_payload can be empty).

## 2) Actual UI CTA states (Select Payload)

Frontend run via Vite dev server (`http://127.0.0.1:5173`).

Observed on **Remote Sensing → Select Payload**:

| Card label | CTA | Disabled |
|---|---|---|
| Hyperspectral | Select | No |
| Multispectral | Coming soon | Yes |
| VHR Optical | Select | No |
| Thermal | Select | No |
| SAR | Select | No |
| My Payload | Select | No |

Verdict: Thermal and SAR correctly switched to **Select** because taxonomy now provides payloads for those categories.

## 3) Frontend logic check (no changes)

File inspected: `frontend/src/pages/PayloadPage.tsx`

Confirmed logic is unchanged and correct:

- Category is disabled when `payloads[]` is empty (`disabled: !c.payloads[0]?.payload_id`).
- Category is enabled when `payloads[]` has at least one entry.
- `my_payload` is special-cased enabled in the frontend.

No frontend patch was required.

## 4) Click-through test results

Method: headless Playwright driving the UI.

Enabled cards (click card → click Next → verify navigation to ROI page):

- Hyperspectral: PASS (navigates to `/roi`)
- VHR Optical: PASS (navigates to `/roi`)
- Thermal: PASS (navigates to `/roi`)
- SAR: PASS (navigates to `/roi`)
- My Payload: PASS (navigates to `/roi`)

Disabled card behavior:

- Multispectral: PASS (card disabled; Next remains disabled; does not navigate)

## 5) Console / network errors

During Playwright runs:

- Browser console errors: none observed
- Page errors: none observed
- Network request failures: none observed

## 6) Files changed in Prompt 14B

- Added `docs/PAYLOAD_CARD_UI_VERIFICATION_REPORT.md`

No frontend source files were modified.

## 7) Final verdict

**UI_PAYLOAD_AVAILABILITY_FIXED**

- Cards now showing **SELECT**: Hyperspectral, VHR Optical, Thermal, SAR, My Payload
- Cards still showing **COMING SOON**: Multispectral (expected; mapping status is `missing_explicit_db_variant` due to no explicit DB variant)

