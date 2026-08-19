# Remote Sensing Oversize Forensic Report (Prompt 12.95 - ONE_V3)

Generated on: 2026-04-30

Scope:
- Forensically diagnose why `RS-EO-VIS-001` was stuck at `27U` (pre-patch).
- Apply *narrow* Remote Sensing optical-camera semantic corrections **only if** evidence showed over-escalation.

Non-scope (explicitly not changed here):
- Objective weights
- Global feasibility calibration factors (`f_pack`, thermal calibration, mass reserve calibration)
- Prompt 12 solver architecture
- Frontend

---

## A) Remote Sensing sample diagnostic set (required)

Diagnostic mode used: `run_cubesat_diagnostic(payload_id)` probing bus-by-bus.

### A1) Sample table — smallest feasible bus + selected tiers + ordinals

Legend: ordinals use LOW=1, MEDIUM=2, HIGH=3, EXTREME=4.

| Payload ID | Type / Variant | Smallest feasible bus (before) | Smallest feasible bus (after) | EPS | ADCS | COMMS | OBC | THERM | PROP | ord_req_(eps/adcs/comms/obc/therm/struct/prop) | ord_(rad/vibe/emi/contam/deploy/harness) |
|---|---|---:|---:|---|---|---|---|---|---|---|---|
| `RS-EO-VIS-001` | Optical / Visible | `27U` | `16U` | EXTREME | EXTREME | EXTREME | HIGH | HIGH | LOW | `1/3/3/3/1/3/1` | before `3/3/3/3/3/4` → after `3/3/3/3/1/3` |
| `RS-EO-VIS-002` | Optical / Visible | *(no feasible bus)* | *(no feasible bus)* | - | - | - | - | - | - | `2/3/3/3/2/3/1` | before `3/3/3/3/3/4` → after `3/3/3/3/1/3` |
| `RS-EO-HSI-001` | Spectral / Hyperspectral | *(no feasible bus)* | *(no feasible bus)* | - | - | - | - | - | - | `1/3/3/3/3/3/1` | `3/3/3/3/3/4` |
| `RS-EO-XSAR-001` | SAR / X-band | *(no feasible bus)* | *(no feasible bus)* | - | - | - | - | - | - | `4/4/3/4/4/4/3` | `3/4/3/2/4/4` |
| `RS-EO-VIS-009` | Optical / Visible (lower-rate) | `27U` | `16U` | EXTREME | EXTREME | EXTREME | HIGH | HIGH | LOW | `1/2/3/3/1/3/1` | before `3/3/3/3/3/4` → after `3/3/3/3/1/3` |

Notes:
- “before” refers to the Prompt 12.9 state (prior to this Prompt 12.95 patch).
- “after” reflects the current Prompt 12.95 patched state.

---

## B) Exact `27U` drivers for `RS-EO-VIS-001` (pre-patch evidence)

Payload reality inputs (from payload DB):
- `nominal_data_rate_mbps = 95`
- `daily_data_generation_gb = 256.5`
- `latency_tolerance = delay_tolerant`
- `propulsion_need_class = LOW` (compatibility map) and `DV_req_mps = 0` (precompute)

Pre-patch semantic ordinals (from payload precompute):
- `ord_deploy = 3` (deployment burden proxy)
- `ord_harness = 4` (harness/integration burden proxy)

### B1) Forced-bus failure breakdown (all buses below `27U`, pre-patch)

For each bus, this lists:
- representative infeasible tier combination (from diagnostic enumeration)
- failing constraint families
- the *specific* ordinal/no-good triggers active in that representative case
- key negative margins (deficits)

#### `1U`
- Representative tiers: `EPS=HIGH, ADCS=HIGH, COMMS=EXTREME, OBC=EXTREME, THERM=LOW, PROP=LOW`
- Failing families: `VOLUME`, `MASS`, `EPS_SOLAR`, `EPS_BATTERY`, `THERMAL`, `COMPATIBILITY_ORDINAL`, `FORBIDDEN`
- Active triggers:
  - Forbidden: COMMS/OBC EXTREME not supported on `1U`, plus `BUS=1U` forbids `COMMS∈{HIGH,EXTREME}`, plus COMMS pointing-dependency requires ADCS EXTREME
  - Ordinal: bus stiffness below required; `THERM` below contamination burden; `PROP` below `deploy_min` (because `ord_deploy=3`)
- Key deficits: volume `-5.654 U`, mass `-13.853 kg`, solar `-158.9 W`, battery `-202.9 Wh`, thermal `-67.4 W`

#### `1.5U`
- Representative tiers: same as `1U`
- Failing families: same as `1U`
- Active triggers: same as `1U`
- Key deficits: volume `-5.404 U`, mass `-13.170 kg`, solar `-150.1 W`, battery `-182.9 Wh`, thermal `-66.3 W`

#### `2U`
- Representative tiers: same as `1U`
- Failing families: same as `1U`
- Active triggers: same as `1U` (plus bus stiffness still below required)
- Key deficits: volume `-5.104 U`, mass `-12.687 kg`, solar `-137.3 W`, battery `-157.9 Wh`, thermal `-65.2 W`

#### `3U`
- Representative tiers: `EPS=MEDIUM, ADCS=HIGH, COMMS=LOW, OBC=EXTREME, THERM=LOW, PROP=LOW`
- Failing families: `VOLUME`, `MASS`, `EPS_SOLAR`, `THERMAL`, `COMMS_DOWNLINK`, `COMPATIBILITY_ORDINAL`, `FORBIDDEN`
- Active triggers:
  - Forbidden: `OBC=EXTREME` not supported on `3U`
  - Ordinal: bus stiffness below required; `COMMS` below `ord_harness=4`; `THERM` below `ord_contam=3`; `PROP` below deploy minimum (from `ord_deploy=3`)
  - COMMS: nominal margin `-93 Mbps` and daily downlink margin `-320.36 GB/day`
- Key deficits: volume `-2.704 U`, mass `-5.462 kg`, solar `-23.32 W`, thermal `-26.97 W`

#### `6U`
- Representative tiers: `EPS=HIGH, ADCS=HIGH, COMMS=MEDIUM, OBC=EXTREME, THERM=LOW, PROP=LOW`
- Failing families: `VOLUME`, `THERMAL`, `COMMS_DOWNLINK`, `COMPATIBILITY_ORDINAL`
- Active triggers:
  - Ordinal: `COMMS` below `ord_harness=4`; `THERM` below `ord_contam=3`; `PROP` below deploy minimum (from `ord_deploy=3`)
  - COMMS: nominal margin `-70 Mbps` and daily downlink margin `-317.28 GB/day`
- Key deficits: volume `-1.608 U`, thermal `-26.4 W`

#### `12U`
- Representative tiers: `EPS=HIGH, ADCS=HIGH, COMMS=HIGH, OBC=EXTREME, THERM=HIGH, PROP=LOW`
- Failing families: `COMMS_DOWNLINK`, `COMPATIBILITY_ORDINAL`
- Active triggers:
  - Ordinal: `COMMS` below `ord_harness=4`; `PROP` below deploy minimum (from `ord_deploy=3`)
  - COMMS: nominal margin `+85 Mbps`, but daily downlink margin `-296.53 GB/day` (daily is the blocker)
- Key deficits: daily downlink only (other closures were not binding in the representative case)

#### `16U`
- Representative tiers: `EPS=EXTREME, ADCS=HIGH, COMMS=EXTREME, OBC=EXTREME, THERM=EXTREME, PROP=MEDIUM`
- Failing families: `FORBIDDEN_NO_GOOD_FAIL` (conflict-driven)
- Active triggers in representative case:
  - Forbidden: `ADCS=HIGH` not supported on `16U` (HIGH ADCS capped at `12U`)
  - Forbidden: `PROP=MEDIUM` not supported on `16U` (MEDIUM PROP capped at `12U`)
  - Forbidden: `COMMS=EXTREME` pointing-dependency requires `ADCS=EXTREME`
- Why `16U` still failed even if “supported tiers” are chosen:
  - Forcing fully-supported tiers (`EPS=EXTREME, ADCS=EXTREME, COMMS=EXTREME, OBC=EXTREME, THERM=EXTREME, PROP=HIGH`) yields a **volume deficit** of about `-0.24 U` at `16U` (effective subsystem stack too large).

### B2) Conclusion (pre-patch)

`RS-EO-VIS-001` was not “randomly oversized”: the solver was being forced into a *very high-volume* tier bundle primarily due to:

1. `ord_harness = 4` forcing `COMMS>=EXTREME` and `OBC>=EXTREME` even though the payload is not in an EXTREME data/latency regime.
2. `ord_deploy = 3` forcing propulsion tier ≥ MEDIUM despite `DV_req_mps = 0` and compatibility `propulsion_need_class = LOW`.
3. Once `COMMS=EXTREME` is selected to satisfy daily downlink, its `pointing_dependency=EXTREME` forces `ADCS=EXTREME`, further increasing packaging burden.

These drivers were traced to the *semantic burden heuristics*, not to the global feasibility calibration factors.

---

## C) Semantic over-escalation checks (results)

### C1) ord_contam (thermal cleanliness)

- For `RS-EO-VIS-001`: `ord_contam=3` (HIGH), not forcing EXTREME thermal.
- This matched the Prompt 12.95 rule (ordinary visible camera, `ground_resolution_m=4.75`, `thermal_control_class=passive`, `temperature_stability_requirement=medium`).
- No patch required.

### C2) Deployment / propulsion coupling

Evidence:
- Pre-patch `ord_deploy=3` was being set because `deployment_clearance_needed==true` in the payload DB.
- That ordinal then enforced propulsion tier ≥ MEDIUM via `prop_tier >= ord_deploy - 1`, despite:
  - `propulsion_need_class=LOW`, and
  - `DV_req_mps=0`.

Result: over-escalation confirmed for VIS/PAN optical camera variants.

### C3) Harness forcing EXTREME OBC/COMMS

Evidence:
- Pre-patch `ord_harness=4` was also driven by `deployment_clearance_needed==true` (methodology bump).
- Payload data regime for `RS-EO-VIS-001` does **not** meet EXTREME thresholds:
  - `daily_data_generation_gb = 256.5 < 1000`
  - `nominal_data_rate_mbps = 95 < 250`
  - `latency_tolerance = delay_tolerant` (not real_time)

Result: over-escalation confirmed for VIS/PAN optical camera variants.

### C4) Storage model realism

Evidence:
- Pre-patch `S_req_gb` for `RS-EO-VIS-001` was `1202.34375 GB`, forcing `OBC=EXTREME` (1024 GB OBC HIGH cannot satisfy).
- For VIS/PAN imagery, a conservative compression proxy is reasonable for storage buffering to avoid systematically forcing EXTREME OBC.

Result: a VIS/PAN-only storage compression proxy was applied (see Patch section).

---

## D) Targeted patches applied (Prompt 12.95)

Patched files:
- `backend/solver_precompute/payload_precompute_constants.json`
- `backend/solver_docs/PAYLOAD_PRECOMPUTE_METHODOLOGY.md`

No solver constraints were globally relaxed; only precompute semantics for VIS/PAN optical cameras were corrected.

### D1) Optical VIS/PAN-only storage compression proxy

- Applied to `payload_variant ∈ {Visible Light Cameras, Panchromatic Cameras}`:
  - `S_req_gb := S_req_gb / 1.5`

Example (`RS-EO-VIS-001`):
- `S_req_gb`: `1202.34375 → 801.5625`

### D2) Deployment/propulsion semantic fix for VIS/PAN cameras

- For VIS/PAN camera payloads:
  - `ord_deploy := 1` (LOW)

Example (`RS-EO-VIS-001`):
- `ord_deploy`: `3 → 1`

### D3) Harness ordinal de-escalation for VIS/PAN cameras

- For VIS/PAN camera payloads:
  - Removed “deployment clearance” bump from `ord_harness`
  - EXTREME gating enforced per Prompt 12.95 (daily ≥ 1000, or rate ≥ 250, or real_time latency, or downlink_class very_high/extreme)

Example (`RS-EO-VIS-001`):
- `ord_harness`: `4 → 3`

### D4) Payload IDs modified (targeted set)

These precompute-only patches were applied to the Remote Sensing VIS/PAN camera families:
- `RS-EO-VIS-001` … `RS-EO-VIS-010` (10 payloads)
- `RS-EO-PAN-001` … `RS-EO-PAN-005` (5 payloads)

---

## E) Post-patch validation (required)

Executed (Prompt 12.95 required set):
- `run_cubesat_diagnostic("RS-EO-VIS-001")` → smallest feasible bus now `16U`
- `run_cubesat_diagnostic("RS-EO-VIS-002")` → still *no feasible bus*
- `run_cubesat_diagnostic("RS-EO-HSI-001")` → still *no feasible bus*

Solver regression guard (Prompt 12.95 required):
- `run_cubesat_solver("RS-EO-VIS-001")` → selects `16U` with tiers `EXTREME/EXTREME/EXTREME/HIGH/HIGH/LOW`
- `run_cubesat_solver("IOT-COM-BPT-001")` → still selects `16U` (no regression from Prompt 12.9)
- `run_cubesat_solver("NAV-RF-PNT-001")` → still selects `12U` (no regression from Prompt 12.9)

---

## F) Final recommendation

- **Remote Sensing (ordinary VIS/PAN optical cameras): acceptable now.**
  - The `27U` pathology for `RS-EO-VIS-001` was traced to *semantic over-escalation* (`ord_harness`, `ord_deploy`, and storage buffering without compression proxy) and is now corrected without weakening global constraints.

- **Remote Sensing (higher-burden payloads): still requires deeper data/assumption correction.**
  - `RS-EO-VIS-002`, `RS-EO-HSI-001`, and `RS-EO-XSAR-001` remain infeasible under current downlink/contact assumptions and comms tier capacities.
  - Direct evidence using the current daily downlink model (COMMS EXTREME cap):
    - COMMS EXTREME daily capacity ≈ `401.625 GB/day`
    - Daily requirement = `M_data * daily_data_generation_gb`
      - `RS-EO-VIS-002`: req ≈ `405.0` → margin ≈ `-3.375 GB/day`
      - `RS-EO-HSI-001`: req ≈ `472.5` → margin ≈ `-70.875 GB/day`
      - `RS-EO-XSAR-001`: req ≈ `864.0` → margin ≈ `-462.375 GB/day`
  - This is not addressed here because it would require mission-level assumptions (contact time, station network) or comms library changes, which are explicitly out of scope for this narrow prompt.
