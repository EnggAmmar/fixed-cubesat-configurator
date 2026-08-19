# Discrete Engineering Capacity Summary (Prompt 9 - ONE_V3)

Generated on: 2026-04-30

## Deliverables

This prompt converts the abstract capacity functions from `backend/solver_docs/SUBSYSTEM_MATHEMATICAL_FORMULATION.md` into **discrete numerical lookup libraries** suitable for first-pass CubeSat optimization.

Created libraries:

1. `backend/solver_libs/bus_capacity_library.json`
2. `backend/solver_libs/eps_capacity_library.json`
3. `backend/solver_libs/adcs_capacity_library.json`
4. `backend/solver_libs/comms_capacity_library.json`
5. `backend/solver_libs/obc_capacity_library.json`
6. `backend/solver_libs/thermal_capacity_library.json`
7. `backend/solver_libs/propulsion_capacity_library.json`

## Design principles used

- Conservative thresholds (avoid falsely feasible designs).
- First-pass industrial preliminary sizing: numbers are intended to bound feasibility and drive discrete choices, not replace detailed design.
- Consistent coupling: bus capacity bounds packaging/area; subsystem tiers bound performance and mass/power/volume.
- Numeric coherence: capacities are internally consistent across power, storage, comms throughput, and heat rejection ranges observed in ONE_V3 payloads.

## How these libraries resolve the abstract functions (Prompt 8)

Below, `b` is selected bus class and `k_S` is selected tier for subsystem `S`.

### 1) Bus and structure proxies

From `bus_capacity_library.json`:

- `U_bus = bus.u_bus`
- `U_internal_usable = bus.usable_internal_volume_u`
- `m_bus_struct = bus.bus_structure_mass_kg`
- `U_bus_struct = bus.bus_structure_volume_u`
- `m_dry_max = bus.max_recommended_dry_mass_kg`
- `A_solar_body = bus.available_body_solar_area_m2`
- `A_solar_deploy = bus.deployable_panel_option_area_m2`
- `A_rad = bus.nominal_radiator_area_m2`
- `C_batt_pack_max = bus.battery_packaging_limit_wh`

This numerically supports:

- `f_struct(U_bus, STRUCT_selected)` -> `m_bus_struct` (with optional tier multiplier if STRUCT tiers are later added)

### 2) EPS availability functions

From `eps_capacity_library.json` (tier `k=EPS_selected`):

- `P_solar_eps_max = eps.max_solar_generation_w`
- `C_batt_eps_max = eps.max_battery_capacity_wh`
- `P_peak_bus_max = eps.max_peak_bus_power_w`
- `P_eps_self = eps.eps_avg_self_consumption_w`
- `m_eps = eps.eps_mass_kg`, `U_eps = eps.eps_volume_u`

Numeric feasibility checks:

- `P_solar_available(b,k) = min(P_solar_eps_max, P_solar_area_cap(b))`
- `C_batt_available(b,k) = min(C_batt_eps_max, C_batt_pack_max(b))`
- `P_bus_peak_available(k) = P_peak_bus_max`

Where the bus solar area cap is:

- `P_solar_area_cap(b) = Pdens_sunlit * (A_solar_body + A_solar_deploy)`

Recommended conservative default:

- `Pdens_sunlit = 160 W/m^2` (effective sunlit electrical generation per m^2, net of packing/angle losses)

This resolves:

- `P_solar_available(...)`
- `C_batt_available(...)`
- `f_eps(...)` -> `m_eps` and `U_eps`

### 3) ADCS availability functions

From `adcs_capacity_library.json` (tier `k=ADCS_selected`):

- `pointing_accuracy_deg`
- `slew_capability_deg_per_s`
- presence flags: `reaction_wheel_presence`, `star_tracker_presence`, `magnetorquer_presence`
- `P_adcs_avg`, `P_adcs_peak`, `m_adcs`, `U_adcs`

Numeric feasibility check:

- Sanity: `point_req(i) > 0`
- Feasible if: `point_req(i) <= pointing_accuracy_deg(ADCS_selected)`

This resolves:

- `f_adcs(...)` -> `m_adcs` and `U_adcs`

### 4) COMMS availability functions

From `comms_capacity_library.json` (tier `k=COMMS_selected`):

- `R_link_nom_max = comms.nominal_supported_downlink_mbps`
- `P_tx_peak = comms.tx_peak_power_w`
- `P_tx_avg = comms.tx_avg_power_w`
- `m_comms`, `U_comms`
- `pointing_dependency` in `{LOW, MEDIUM, HIGH, EXTREME}`

Numeric feasibility checks:

- `R_link_available(k) = R_link_nom_max`
- `R_link_available(k) >= R_nom_req_Mbps` (from Prompt 8 comm sizing)
- `ord(ADCS_selected) >= ord(comms.pointing_dependency)` (narrow-beam/optical pointing coupling)

This resolves:

- `R_link_available(...)`
- `f_comms(...)` -> `m_comms` and `U_comms`

### 5) OBC / storage availability functions

From `obc_capacity_library.json` (tier `k=OBC_selected`):

- `Storage_available_GB = obc.max_storage_gb`
- `Ingest_supported_Mbps = obc.supported_ingest_mbps`
- `P_obc_avg`, `P_obc_peak`, `m_obc`, `U_obc`

Numeric feasibility checks:

- `Storage_available_GB >= D_store_req_GB` (from Prompt 8)
- `Ingest_supported_Mbps >= R_ingest_req_Mbps` where a conservative proxy is:
  - `R_ingest_req_Mbps = (D_day_req_Gb/day) / (24*3600) * 1000` (average ingest)
  - optionally increase for near-real-time pipelines: multiply by 5 to represent burst processing

This resolves:

- `Storage_available_GB(...)`
- `f_obc(...)` -> `m_obc` and `U_obc`

### 6) Thermal availability functions

From `thermal_capacity_library.json` (tier `k=THERM_selected`):

- `Q_tier_max = thermal.max_heat_rejection_w`
- `q_density = thermal.q_reject_density_w_per_m2`
- `P_therm_avg`, `P_therm_peak`, `m_therm`, `U_therm`

Combine with bus radiator area:

- `Q_bus_cap = q_density * A_rad(b)`
- `Q_out_max = min(Q_tier_max, Q_bus_cap)`

Thermal feasibility:

- `Q_out_max >= Q_design_W` (from Prompt 8 thermal sizing)

This resolves:

- `f_therm(...)` -> `m_therm` and `U_therm`

### 7) Propulsion availability functions

From `propulsion_capacity_library.json` (tier `k=PROP_selected`):

- `DeltaV_available = prop.delta_v_support_mps`
- `U_prop = prop.propellant_volume_u`
- `P_prop_avg`, `P_prop_peak`, `m_prop`

Feasibility proxy:

- `DeltaV_available >= DeltaV_req_proxy(PROP_req(i))` where mapping can start as:
  - LOW -> 0 m/s
  - MEDIUM -> 10 m/s
  - HIGH -> 50 m/s
  - EXTREME -> 150 m/s

This resolves:

- `f_prop(...)` -> `m_prop` and `U_prop`

---

## Rationale behind numerical values and scaling

### Bus scaling logic

Bus capacities scale roughly with `U_bus` but are capped conservatively to avoid overestimating:

- Usable internal volume is far less than geometric volume due to rails, panels, harness, and keep-outs.
- Solar area scales with surface area and panel practicality; deployables increase area significantly for 6U+ buses.
- Radiator area scales with available exterior area (proxy), with larger buses enabling more usable radiator placement.
- Battery packaging limit scales with volume; upper values assume realistic packing and thermal constraints.

### EPS tiers

EPS tiers are designed to bound:

- sunlit generation capability (W),
- battery capacity (Wh),
- peak regulated bus power delivery (W),
and to provide mass/volume/power overhead proxies.

The supported bus range prevents infeasible combinations (e.g., EXTREME EPS in 1U).

### ADCS tiers

ADCS tiers follow the common progression:

- LOW: magnetorquer-based coarse pointing,
- MEDIUM: reaction wheels (no star tracker) moderate pointing,
- HIGH: reaction wheels + star tracker fine pointing,
- EXTREME: fine pointing with high disturbance rejection and higher power/mass.

### COMMS tiers

Mapping is intentionally aligned to:

- LOW -> VHF/UHF,
- MEDIUM -> S-band,
- HIGH -> X-band,
- EXTREME -> optical / very-high-rate RF.

pointing_dependency captures the realistic coupling that higher-rate links typically require better pointing.

### OBC tiers

OBC tiers provide both:

- storage feasibility (`max_storage_gb`),
- pipeline feasibility (`supported_ingest_mbps`),
plus power/mass/volume proxies.

### Thermal tiers

Thermal tiers represent increasing ability to reject internal heat and maintain stability:

- LOW/MEDIUM mostly passive with increasing heater and layout capability,
- HIGH/EXTREME include stronger active control and radiator usage.

The coupling via `q_reject_density_w_per_m2 * bus.nominal_radiator_area_m2` ensures bus size influences thermal feasibility.

### Propulsion tiers

Propulsion tiers map to:

- LOW: none,
- MEDIUM: cold gas/simple microprop,
- HIGH: electric microprop,
- EXTREME: dedicated higher-impulse systems.

The values are used as feasibility bounds for delta-v proxies and volume/power/mass closure.

---

## Conservative assumptions and usage notes

- All capacities are first-pass and should be treated as feasibility screens; detailed design will tighten them.
- For COMM and OBC, payload data fields like `daily_data_generation_gb` are modeled estimates; the libraries provide consistent scaling for optimization rather than ground-truth flight performance.
- Future improvement path (Phase 3+): add a dedicated subsystem library for `P_hk` coefficients and a more detailed bus geometry library for inertia and radiator/solar area estimation.
