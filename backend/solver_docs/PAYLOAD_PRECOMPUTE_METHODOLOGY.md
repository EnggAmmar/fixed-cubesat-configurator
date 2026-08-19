# Payload Precompute Methodology (Prompt 11 - ONE_V3)

Generated on: 2026-04-30

## Scope

This document defines the exact numerical precomputations used to generate:

- `backend/solver_precompute/payload_precompute_constants.json`

These constants are required by:

- `backend/solver_docs/CP_SAT_HARD_CONSTRAINT_ARCHITECTURE.md`

No OR-Tools solver code is written here.

---

## Inputs consumed

### Payload databases (source of per-payload engineering fields)

- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
- `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
- `backend/data_base/Navigation/MASTER_Navigation.json`

Required payload fields (per product object):

- `payload_id`
- `avg_power_w`, `peak_power_w`
- `mission_duty_cycle_percent`
- `daily_data_generation_gb`
- `nominal_data_rate_mbps`
- `latency_tolerance` in `{delay_tolerant, near_real_time, real_time}`
- `pointing_requirement_deg`
- `heat_dissipation_fraction`
- `thermal_control_class` in `{passive, passive_plus, active}`
- `temperature_stability_requirement` in `{low, medium, high}`

### Compatibility metadata map (source of required subsystem classes)

- `backend/data_base/payload_compatibility_rules.json`

Required compatibility fields (per payload_id):

- `eps_class_required`, `adcs_class_required`, `comms_class_required`, `obc_class_required`
- `thermal_class_required`, `structure_class_required`, `propulsion_need_class`

### Global engineering assumptions (source of mission-independent constants)

- `backend/data_base/global_engineering_assumptions.json`

Constants used:

- `data_storage_assumptions.storage_utilization_limit.value` -> `f_store_util`
- `data_storage_assumptions.daily_data_contingency_margin.value` -> `M_data`
- `data_storage_assumptions.onboard_storage_days_default.value` -> `N_store_default_days`
- `thermal_assumptions.thermal_margin_factor.value` -> `M_th`

---

## Discrete ordinal mappings

### Required subsystem ordinals (from compatibility classes)

`ord_class(LOW)=1`, `ord_class(MEDIUM)=2`, `ord_class(HIGH)=3`, `ord_class(EXTREME)=4`

Stored per payload in `payload_precompute_constants.json` as:

- `ord_req_eps`, `ord_req_adcs`, `ord_req_comms`, `ord_req_obc`, `ord_req_therm`, `ord_req_struct`, `ord_req_prop`

### CG sensitivity ordinals (payload field)

`ord_cg(low)=1`, `ord_cg(medium)=2`, `ord_cg(high)=3`

Included in the precompute file header for consistency with Prompt 10.

---

## A1) Peak power effective

Stored key:

- `P_payload_peak_eff_w`

Definition:

- `P_payload_peak_eff(i) = max(peak_power_w(i), avg_power_w(i))`

Units: W

Rationale:

- Avoids non-linear `max()` usage inside CP-SAT by precomputing the effective payload peak power scalar.

---

## A2) OBC storage requirement

Stored key:

- `S_req_gb`

Definition:

- Raw storage buffering requirement:
  - `S_req_raw(i) = ((daily_data_generation_gb(i) * N_store_default_days) * M_data) / f_store_util`

- Optical EO compression proxy (Prompt 12.95, VIS/PAN only):
  - For `payload_variant ∈ {Visible Light Cameras, Panchromatic Cameras}`:
    - `S_req(i) = S_req_raw(i) / optical_compression_factor`
    - `optical_compression_factor = 1.5`
  - Else:
    - `S_req(i) = S_req_raw(i)`

Units: GB

Constants:

- `N_store_default_days` from `global_engineering_assumptions.json`
- `M_data` from `global_engineering_assumptions.json`
- `f_store_util` from `global_engineering_assumptions.json`

Notes:

- This intentionally uses the mission-independent default storage buffering days (not the per-payload `onboard_storage_days`, which may be null).
- ONE_V3 default storage buffering is set to `N_store_default_days = 3` days in `global_engineering_assumptions.json`.
- The optical compression proxy is applied only to VIS/PAN imagery payloads to avoid over-forcing EXTREME OBC tiers for ordinary optical cameras; it is not applied to hyperspectral, SAR, IR, or scientific payloads.

---

## A3) OBC ingest rate requirement proxy

Stored key:

- `R_ing_req_mbps`

Definition steps:

1. Convert daily data to an average ingest rate:
   - `R_avg_ing(i) = daily_data_generation_gb(i) * 8 * 1000 / 86400`  [Mb/s]
   - (Uses decimal GB: 1 GB = 8*1000 Mb)

2. Apply a latency-driven concentration factor:
   - `k_lat(delay_tolerant)=1`
   - `k_lat(near_real_time)=3`
   - `k_lat(real_time)=10`
   - `R_lat(i) = k_lat(latency_tolerance(i)) * R_avg_ing(i)`

3. Ensure the OBC ingest path can accept the payload's nominal interface rate:
   - `R_base(i) = max(nominal_data_rate_mbps(i), R_lat(i))`

4. Apply a conservative margin:
   - `R_ing_req(i) = 1.20 * R_base(i)`

Units: Mb/s

Why nominal_data_rate_mbps participates:

- Many payloads are bursty: the average daily data can be small while the interface rate is still high. The OBC ingest path must handle the interface rate even if it does not run continuously.

---

## A4) Thermal payload heat rejection requirement

Stored key:

- `Q_payload_req_w`

Definition:

1. Duty-weighted design power:
   - `P_th_design(i) = max(avg_power_w(i), (mission_duty_cycle_percent(i)/100) * peak_power_w(i))`

2. Payload internal heat rejection requirement proxy:
   - `Q_payload_req(i) = M_th * heat_dissipation_fraction(i) * P_th_design(i)`

Units: W

Constants:

- `M_th` from `global_engineering_assumptions.json` (`thermal_assumptions.thermal_margin_factor`)

Notes:

- This is a feasibility proxy consistent with Prompt 10 thermal constraints. It is not a full radiative balance model.

---

## A5) Fine pointing flags

Stored keys:

- `fine_point`
- `ultra_fine`

Definition:

- `fine_point(i) = 1 if pointing_requirement_deg(i) <= 0.10 else 0`
- `ultra_fine(i) = 1 if pointing_requirement_deg(i) <= 0.05 else 0`

Units: binary

Usage:

- Enables hard no-goods in Prompt 10 (forbid low-tier ADCS for fine pointing payloads).

---

## A6) Extreme data flag

Stored key:

- `extreme_data`

Definition:

- `extreme_data(i) = 1 if daily_data_generation_gb(i) >= D_extreme_threshold_gb_per_day else 0`

Chosen threshold:

- `D_extreme_threshold_gb_per_day = 200.0`

Rationale:

- For CubeSat-class studies, 200+ GB/day generally forces high-rate downlink, higher OBC throughput, and a larger bus/EPS.

---

## A7) High thermal flag

Stored key:

- `high_thermal`

Definition:

`high_thermal(i) = 1` if any condition is true:

- compatibility `thermal_class_required(i)` is `HIGH` or `EXTREME`, OR
- payload `thermal_control_class(i) == active`, OR
- payload `temperature_stability_requirement(i) == high`

Units: binary

Usage:

- Enables hard no-goods in Prompt 10 (forbid low-tier thermal solutions when the payload is thermally demanding).

---

## A8) Delta-v proxy requirement

Stored key:

- `DV_req_mps`

Definition:

Map compatibility `propulsion_need_class(i)` to a conservative delta-v proxy:

- `LOW -> 0 m/s`
- `MEDIUM -> 10 m/s`
- `HIGH -> 50 m/s`
- `EXTREME -> 150 m/s`

Units: m/s

Notes:

- This is a proxy feasibility requirement used for discrete propulsion tier screening (Prompt 10).

---

## A9) Required subsystem ordinals

Stored keys:

- `ord_req_eps`, `ord_req_adcs`, `ord_req_comms`, `ord_req_obc`, `ord_req_therm`, `ord_req_struct`, `ord_req_prop`

Definition:

- `ord_req_subsystem(i) = ord_class(required_class_string(i))`

Where `required_class_string(i)` is taken from `payload_compatibility_rules.json` for the matching `payload_id`.

---

## A10) Compatibility semantic propagation burdens (hardening patch)

These additional ordinal burdens are injected into each payload precompute record to ensure that
compatibility semantics remain mathematically active in CP-SAT selection (Prompt 12.5).

Stored keys (all integers using LOW=1, MEDIUM=2, HIGH=3, EXTREME=4):

- `ord_rad` (radiation / environment robustness burden proxy)
- `ord_vibe` (vibration / mechanical robustness burden proxy)
- `ord_emi` (EMI/EMC integration burden proxy)
- `ord_contam` (contamination / cleanliness burden proxy)
- `ord_deploy` (deployment mechanism burden proxy)
- `ord_harness` (harness / integration wiring burden proxy)

### ord_rad

- Source: payload DB field `radiation_sensitivity` (low/medium/high)
- Mapping:
  - `low->1`, `medium->2`, `high->3` (EXTREME=4 reserved if ever introduced in DB)

### ord_vibe

Definition (proxy from packaging + mass + deployment burden):

- Start with:
  - EXTREME (4) if `mass_kg>=5` OR `payload_envelope_u>=6` OR `recommended_bus_min_u>=27`
  - HIGH (3) if `mass_kg>=2.5` OR `payload_envelope_u>=2.5` OR `recommended_bus_min_u>=12`
  - MEDIUM (2) if `mass_kg>=1.2` OR `payload_envelope_u>=1.2` OR `recommended_bus_min_u>=6`
  - else LOW (1)
- If `deployment_clearance_needed==true`, bump by +1 (cap at 4).

### ord_emi

Definition (proxy from required comm class + RF indicators):

- Start with `ord_emi = ord_class(comms_class_required)` from `payload_compatibility_rules.json`.
- Enforce at least MEDIUM if payload type/band implies RF (RF communication / radar, or Ka/X/S-band indicators).
- If `nominal_data_rate_mbps >= 100`, bump to at least HIGH.

### ord_contam

Definition (proxy for optical cleanliness sensitivity):

- HIGH (3) for optical/imaging/hyperspectral/camera payloads.
- EXTREME (4) if such payload also has `ground_resolution_m <= 1.0` (when available).
- MEDIUM (2) for non-optical remote-sensing payloads.
- else LOW (1).

### ord_deploy

Definition:

- LOW (1) by default.
- For VIS/PAN optical camera payloads (`payload_variant ∈ {Visible Light Cameras, Panchromatic Cameras}`):
  - keep LOW (1) even if `deployment_clearance_needed==true` (camera keep-out is not treated as a deployable mechanism burden in CP-SAT).
- For other payloads:
  - If `deployment_clearance_needed==true`, set HIGH (3).
  - If deployed and also `recommended_bus_min_u>=12` OR `payload_envelope_u>=2` OR `mass_kg>=2`, set EXTREME (4).

### ord_harness

Definition (proxy from subsystem burden + power/data):

- Base: `ord_harness = max(ord_eps_required, ord_comms_required, ord_obc_required)` from compatibility map.
- If `avg_power_w >= 10` OR `peak_power_w >= 20`, bump to at least HIGH.
- If `nominal_data_rate_mbps >= 100`, bump to at least HIGH.
- If `required_downlink_class` is `very_high` / `extreme`, force EXTREME.
- EXTREME gating (Prompt 12.95):
  - EXTREME should require at least one of:
    - `daily_data_generation_gb >= 1000`, OR
    - `nominal_data_rate_mbps >= 250`, OR
    - `latency_tolerance == real_time`.
  - Do **not** bump `ord_harness` solely because `deployment_clearance_needed==true` for VIS/PAN optical cameras.

---

## Output structure notes

For each `payload_id`, the JSON stores:

- `source` (mission family + variant context + source file)
- `inputs_used` (exact payload fields consumed by the computation)
- `precompute` (the required constants used by Prompt 10 hard constraints)
