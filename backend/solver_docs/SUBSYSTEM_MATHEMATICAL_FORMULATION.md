# CP-SAT Subsystem Mathematical Formulation Blueprint (ONE_V3 Phase 2)

Generated on: 2026-04-30

## Purpose and scope

This document defines the **preliminary-design-grade mathematical formulation** that CP-SAT will later discretize into an optimization model.

It is intentionally solver-agnostic (no OR-Tools code yet) and specifies, for each subsystem:

1. engineering inputs consumed,
2. derived intermediate variables,
3. governing sizing equations,
4. feasibility constraints,
5. subsystem class outputs,
6. coupling dependencies with other subsystems.

Assumption constants referenced in equations are taken from:

- `backend/data_base/global_engineering_assumptions.json`

Payload engineering inputs and compatibility classes are taken from:

- the three mission master databases (payload objects)
- `backend/data_base/payload_compatibility_rules.json`

---

## Global notation (used throughout)

### Indices

- Let `i` index a payload product (one selected payload in a CP-SAT run unless otherwise stated).
- Let `b` index a discrete bus class candidate.
- Let `k` index a discrete subsystem tier/class option (EPS tier, ADCS tier, etc.).

### Core payload inputs (from master DB; per payload `i`)

- `m_p(i)` = payload mass = `mass_kg` [kg]
- `U_p(i)` = payload packaging envelope = `payload_envelope_u` [U]
- `dim_p(i)` = payload dimensions = `dimensions_mm.{length_mm,width_mm,height_mm}` [mm]
- `P_avg_p(i)` = `avg_power_w` [W]
- `P_peak_p(i)` = `peak_power_w` [W]
- `R_nom(i)` = `nominal_data_rate_mbps` [Mb/s]
- `DC(i)` = `mission_duty_cycle_percent` [%]
- `eclipse_req(i)` = `eclipse_operation_required` [bool]
- `point_req(i)` = `pointing_requirement_deg` [deg]
- `deploy_clear(i)` = `deployment_clearance_needed` [bool]
- `bus_min_u_hint(i)` = `recommended_bus_min_u` [U]
- `bus_min_m_hint(i)` = `recommended_bus_min_mass_kg` [kg]
- `D_day(i)` = `daily_data_generation_gb` [GB/day]
- `downlink_class(i)` = `required_downlink_class` in `{low, medium, high, very_high}`
- `latency(i)` = `latency_tolerance` in `{real_time, near_real_time, delay_tolerant}`
- `heat_frac(i)` = `heat_dissipation_fraction` [0..1]
- `thermal_ctl(i)` = `thermal_control_class` in `{passive, passive_plus, active}`
- `temp_stab(i)` = `temperature_stability_requirement` in `{low, medium, high}`
- `compute_class(i)` = `compute_load_class` in `{low, medium, high}`
- `risk(i)` = `integration_risk` in `{low, medium, high}`
- `structure_req(i)` = `structure_class_required` in `{LOW, MEDIUM, HIGH, EXTREME}` (from compatibility map)

### Compatibility outputs (from `payload_compatibility_rules.json`; per payload `i`)

Each is in `{LOW, MEDIUM, HIGH, EXTREME}`:

- `ADCS_req(i)` = `adcs_class_required`
- `COMMS_req(i)` = `comms_class_required`
- `EPS_req(i)` = `eps_class_required`
- `THERM_req(i)` = `thermal_class_required`
- `OBC_req(i)` = `obc_class_required`
- `STRUCT_req(i)` = `structure_class_required`
- `PROP_req(i)` = `propulsion_need_class`

### Mission-independent assumption constants (from `global_engineering_assumptions.json`)

Let:

- `f_sun` = `power_assumptions.sunlight_fraction.value` [-]
- `f_ecl` = `power_assumptions.eclipse_fraction.value` [-]
- `eta_eps` = `power_assumptions.eps_efficiency.value` [-]
- `k_deg` = `power_assumptions.solar_degradation_factor_eol.value` [-]
- `M_pow` = `power_assumptions.power_margin_factor.value` [-]
- `M_peak` = `power_assumptions.peak_power_headroom_factor.value` [-]

- `M_th` = `thermal_assumptions.thermal_margin_factor.value` [-]

- `M_mass` = `mass_margin_assumptions.mass_growth_margin.value` [-]
- `f_payload_mass_max` = `mass_margin_assumptions.payload_mass_fraction_max.value` [-]

- `f_fill` = `volume_margin_assumptions.volume_fill_limit.value` [-]
- `U_over` = `volume_margin_assumptions.payload_volume_overhead_u.value` [U]

- `DoD_lim` = `battery_assumptions.battery_dod_limit.value` [-]
- `eta_batt` = `battery_assumptions.battery_round_trip_efficiency.value` [-]
- `k_batt` = `battery_assumptions.battery_capacity_derating_factor.value` [-]

- `f_store_util` = `data_storage_assumptions.storage_utilization_limit.value` [-]
- `M_data` = `data_storage_assumptions.daily_data_contingency_margin.value` [-]

- `eta_dl` = `downlink_assumptions.downlink_efficiency_factor.value` [-]
- `T_contact_day` = `downlink_assumptions.nominal_contact_minutes_per_day.value` [min/day]
- `f_contact_use` = `downlink_assumptions.usable_contact_fraction.value` [-]

- `M_risk(low|medium|high)` = `reliability_assumptions.integration_risk_to_margin_map.value` [-]

---

## Discrete class sets (for CP-SAT discretization)

### Bus classes

Define bus class set:

`B = {1U, 1.5U, 2U, 3U, 6U, 12U, 16U, 27U, 50U+}`

For mathematical use, represent each class as a scalar `U_bus(b)` in [U]:

- `U_bus(1U)=1`, `U_bus(1.5U)=1.5`, `U_bus(2U)=2`, ..., `U_bus(27U)=27`, `U_bus(50U+)=50` (minimum)

Decision variable (later discrete):

- `x_b in {0,1}` with `sum_b x_b = 1` (select exactly one bus class)
- `U_bus_sel = sum_b x_b * U_bus(b)`

### Subsystem tier classes (generic pattern)

For each subsystem `S in {EPS, ADCS, COMMS, OBC, THERM, PROP, STRUCT}`, define tier set `K_S` with a decision vector:

- `y_{S,k} in {0,1}`, `sum_k y_{S,k} = 1`
- tier ordinal mapping `ord(LOW)=1`, `ord(MEDIUM)=2`, `ord(HIGH)=3`, `ord(EXTREME)=4`

Compatibility requirement constraint (generic):

- `ord(selected_S) >= ord(S_req(i))`

Implementation note for CP-SAT: enforce via tier-selection feasibility masks or big-M constraints.

---

## Parameter defaults (recommended starting point)

The formulation uses several tunable constants and library functions. To keep Phase 2 immediately usable, below are **recommended initial values** (conservative CubeSat preliminary design) until a dedicated subsystem library is added.

These are not mission-specific "estimates" for any payload; they are global design defaults.

### Structure / volume

- `alpha0 = 0.7 U` and `alpha1 = 0.10` for `U_reserved(U_bus) = alpha0 + alpha1*U_bus`
- `h0 = 0.10` and `h_deploy = 0.15` for `f_harness = 1 + h0 + h_deploy*I[deploy_clear]`
- `U_deploy_min = 3 U` (minimum bus class for payloads requiring deployment clearance)

### Housekeeping power

Use `P_hk = P_hk0 + P_hkU*U_bus_sel + sum_S beta_S*ord(S_selected)` with:

- `P_hk0 = 2.0 W`
- `P_hkU = 0.4 W/U`
- `beta_ADCS = 0.5 W`, `beta_COMMS = 0.4 W`, `beta_OBC = 0.4 W`, `beta_THERM = 0.6 W`, `beta_PROP = 0.2 W`
- `P_hk_peak = 1.2 * P_hk` (peak housekeeping multiplier)

### Orbit timing (for EPS energy closure)

- `T_orbit = 1.5 h` (typical LEO; can be replaced by a mission input later)
- `gamma_ecl = 0.5` if `eclipse_req=false` (reduced eclipse sizing for payloads not required to operate in eclipse)

### Data buffering

- `N_store = 2 days` for storage sizing in Section E (parameterizable)

### Thermal heat rejection proxy

For `Q_out_max_W = q0 * A_rad(U_bus_sel, THERM_selected)` use:

- `A_rad(U_bus_sel, *) = A0 * U_bus_sel` with `A0 = 0.015 m^2/U` (effective radiating area proxy)
- `q0(LOW)=120 W/m^2`, `q0(MEDIUM)=180 W/m^2`, `q0(HIGH)=250 W/m^2`, `q0(EXTREME)=320 W/m^2`

These values are intended to be conservative "net effective" rejection densities (after view factors and non-idealities).

---

# A) STRUCTURE / BUS SIZING FORMULATION

## A1) Inputs consumed

Payload-driven inputs:

- `U_p(i)`, `m_p(i)`, `dim_p(i)`
- `deploy_clear(i)`
- `bus_min_u_hint(i)`, `bus_min_m_hint(i)`
- `STRUCT_req(i)`

Assumptions:

- `U_over`, `f_fill`, `M_mass`, `M_risk(risk(i))`

## A2) Derived intermediate variables

1. **Required internal volume allocation (payload + integration overhead)**

- `U_payload_alloc(i) = U_p(i) + U_over`

2. **Subsystem reserved volume allocation**

Because non-payload subsystems must exist, define a bus-size-dependent reserved volume function:

- `U_reserved(U_bus_sel) = alpha0 + alpha1 * U_bus_sel`

Where `alpha0, alpha1` are preliminary design constants (to be stored in a later bus library). Typical behavior: `U_reserved` grows slowly with bus size.

3. **Harness / keep-out allocation factor**

Use an allocation factor that increases for deployable payloads:

- `f_harness(i) = 1 + h0 + h_deploy * I[deploy_clear(i)=true]`

Where `I[*]` is an indicator (1 if true else 0).

4. **Total required bus volume**

- `U_req_total(i) = (U_payload_alloc(i) * f_harness(i)) + U_reserved(U_bus_sel)`

5. **Fill-limit feasibility**

Impose that the required total volume does not exceed usable packaging fill:

- `U_req_total(i) <= f_fill * U_bus_sel`

6. **Selected bus class candidate**

Define:

- `selected_bus_class_candidate = argmin_b { U_bus(b) : U_bus(b) >= max(bus_min_u_hint(i), U_req_total(i)/f_fill) }`

In CP-SAT, this becomes a set of constraints on `x_b`.

## A3) Governing sizing equations (preliminary)

### A3.1 Minimum bus size constraints

1. Hard minimum based on payload-provided hint:

- `U_bus_sel >= bus_min_u_hint(i)`

2. Packaging constraint:

- `U_bus_sel >= U_req_total(i)/f_fill`

### A3.2 Mass closure lower bound

Use the payload-derived minimum bus mass hint as a **hard lower bound**:

- `m_bus_min(i) = bus_min_m_hint(i)`

Then constrain total dry mass:

- `m_dry >= m_bus_min(i)`

And enforce payload fraction sanity:

- `m_p(i) <= f_payload_mass_max * m_dry`

### A3.3 Structural margin factor

Compute a structural mass margin multiplier combining early growth + integration risk:

- `M_struct(i) = (1 + M_mass) * M_risk(risk(i))`

## A4) Feasibility constraints (structure/bus)

- Volume: `U_req_total(i) <= f_fill * U_bus_sel`
- Payload fraction: `m_p(i) <= f_payload_mass_max * m_dry`
- Compatibility: `ord(STRUCT_selected) >= ord(STRUCT_req(i))`
- Deployables: if `deploy_clear(i)=true`, disallow bus classes below a deployable minimum (parameter `U_deploy_min`):
  - `U_bus_sel >= U_deploy_min`

## A5) Subsystem class outputs

- `STRUCT_selected in {LOW, MEDIUM, HIGH, EXTREME}` (selected structural tier)
- `U_bus_sel` (selected bus size class)

## A6) Coupling dependencies

- Larger `U_bus_sel` increases available solar area and radiator area proxies (EPS/THERM coupling).
- `U_bus_sel` impacts inertia and ADCS disturbance torque requirements (ADCS coupling).
- `U_bus_sel` bounds available volume for batteries/OBC/comms hardware (EPS/OBC/COMMS coupling).

---

# B) EPS (Electrical Power Subsystem) FORMULATION

## B1) Inputs consumed

- `P_avg_p(i)`, `P_peak_p(i)`, `DC(i)`, `eclipse_req(i)`
- `EPS_req(i)`
- `U_bus_sel`
- constants: `f_sun`, `f_ecl`, `eta_eps`, `k_deg`, `M_pow`, `M_peak`, `DoD_lim`, `eta_batt`, `k_batt`, `M_risk(risk(i))`

## B2) Derived intermediate variables

### B2.1 Payload power profile proxies

Convert duty cycle to fraction:

- `d = DC(i)/100`

Define payload orbit-average power proxy:

- `P_avg_payload_orbit(i) = P_avg_p(i)` (already an average draw estimate)

Define peak power with headroom:

- `P_peak_budget(i) = M_peak * P_peak_p(i)`

### B2.2 Housekeeping (bus) power model

Define bus housekeeping average power as a function of bus class and subsystem tiers:

- `P_hk = P_hk0 + P_hkU * U_bus_sel + sum_S beta_S * ord(S_selected)`

Where `S_selected` includes ADCS/COMMS/OBC/THERM tiers (coupling). `P_hk0, P_hkU, beta_S` are design constants to be stored in a subsystem library.

### B2.3 Total average and peak power budgets

- `P_avg_total = M_pow * (P_avg_payload_orbit(i) + P_hk)`
- `P_peak_total = max(P_peak_budget(i), P_avg_total)` (peak must at least cover average)

### B2.4 Eclipse energy requirement

Let `T_orbit` be the orbit period [h] (parameter; typical LEO ~ 1.5 h). Then:

- `E_ecl_Wh = (P_avg_total / eta_eps) * (f_ecl * T_orbit) * M_risk(risk(i))`

If `eclipse_req(i)=false`, allow a reduced eclipse sizing factor `gamma_ecl < 1`:

- `E_ecl_Wh = gamma_ecl * E_ecl_Wh`

### B2.5 Required battery capacity

Battery usable energy (considering DoD and derating):

- `C_batt_req_Wh = E_ecl_Wh / (DoD_lim * k_batt * eta_batt)`

### B2.6 Required solar generation

Ensure sunlit generation covers sunlit consumption plus energy to recharge eclipse:

Sunlit energy consumption:

- `E_sun_load_Wh = (P_avg_total / eta_eps) * (f_sun * T_orbit)`

Total energy needed during sunlit (loads + eclipse recharge):

- `E_sun_need_Wh = E_sun_load_Wh + E_ecl_Wh`

Required average sunlit generation power:

- `P_solar_req_W = (E_sun_need_Wh / (f_sun * T_orbit)) / k_deg`

## B3) Governing feasibility constraints

1. Generation must exceed required:

- `P_solar_available(U_bus_sel, EPS_selected) >= P_solar_req_W`

2. Battery capacity must exceed required:

- `C_batt_available(U_bus_sel, EPS_selected) >= C_batt_req_Wh`

3. Peak power delivery:

- `P_bus_peak_available(EPS_selected) >= P_peak_total`

4. Compatibility:

- `ord(EPS_selected) >= ord(EPS_req(i))`

## B4) Subsystem class outputs

- `EPS_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `C_batt_req_Wh`, `P_solar_req_W` (continuous sizing drivers)

## B5) Coupling dependencies

- COMMS tier increases peak power and battery sizing via `P_hk` and potentially dedicated TX peak loads.
- THERM tier adds heater power / active thermal loads, increasing `P_avg_total`.
- Bus class affects available solar area and battery packaging volume.

---

# C) ADCS FORMULATION

## C1) Inputs consumed

- `point_req(i)`, `cg_sensitivity_class(i)`, `deploy_clear(i)`
- `U_bus_sel`
- payload mass distribution proxy (from `dim_p(i)` + bus geometry library)
- `ADCS_req(i)`

## C2) Derived intermediate variables

### C2.1 Required pointing class

Define pointing class thresholds:

- If `point_req(i) <= 0.05 deg` -> `point_class = EXTREME`
- Else if `<= 0.10 deg` -> `point_class = HIGH`
- Else if `<= 0.20 deg` -> `point_class = MEDIUM`
- Else -> `point_class = LOW`

### C2.2 Inertia penalty factor

Use bus size and payload size to proxy inertia:

- `I_proxy = kappa_I * U_bus_sel^gamma * (1 + kappa_dim * (max(dim_p)/100 mm))`

Where `kappa_I, gamma, kappa_dim` are tunable constants from an ADCS library.

### C2.3 Disturbance rejection proxy

Define a disturbance proxy increasing for deployables and larger buses:

- `D_proxy = D0 + D_U * U_bus_sel + D_deploy * I[deploy_clear(i)=true]`

### C2.4 Required actuator torque class and sensor precision class

Actuator torque need proxy:

- `tau_req_proxy proportional to I_proxy * D_proxy`

Map to actuator class:

- LOW: magnetorquer-only + detumble
- MEDIUM: small reaction wheels + mag torquer desat
- HIGH: higher-capacity wheels + star tracker
- EXTREME: high-capacity wheels + star tracker + fine guidance (and deployable dynamics margin)

Sensor precision need:

- LOW: sun sensors + magnetometer
- MEDIUM: coarse sun sensors + gyro
- HIGH: star tracker + gyro
- EXTREME: star tracker + high-grade gyro + fine pointing controller

## C3) Governing feasibility constraints

1. Tier must meet pointing:

- `ord(ADCS_selected) >= ord(point_class)`

2. Tier must meet compatibility:

- `ord(ADCS_selected) >= ord(ADCS_req(i))`

3. Deployables impose minimum tier:

- If `deploy_clear(i)=true` then `ADCS_selected in {HIGH, EXTREME}` (parameterizable)

## C4) Subsystem class outputs

- `ADCS_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `required_actuator_torque_class`, `required_sensor_precision_class` (often equal to `ADCS_selected` tier)

## C5) Coupling dependencies

- ADCS tier increases housekeeping power and may increase structure stiffness requirements (STRUCT coupling).
- ADCS tier influences comm pointing feasibility (COMMS coupling) for high-rate/optical links.

---

# D) COMMUNICATION SUBSYSTEM FORMULATION

## D1) Inputs consumed

- `R_nom(i)`, `D_day(i)`, `latency(i)`, `downlink_class(i)`
- `U_bus_sel`
- `COMMS_req(i)`
- constants: `eta_dl`, `T_contact_day`, `f_contact_use`, `M_data`

## D2) Derived intermediate variables

### D2.1 Total daily downlink requirement

Apply contingency margin:

- `D_day_req = M_data * D_day(i)`  [GB/day]

### D2.2 Available effective contact time per day

- `T_eff_day = T_contact_day * f_contact_use`  [min/day]

### D2.3 Minimum required effective throughput

Convert to Gb/day:

- `D_day_req_Gb = 8 * D_day_req`  [Gb/day]

Required average effective downlink rate:

- `R_eff_req_Mbps = (D_day_req_Gb * 1000) / (T_eff_day * 60)`  [Mb/s]

Because downlink is not perfectly efficient, required nominal link rate:

- `R_nom_req_Mbps = R_eff_req_Mbps / eta_dl`

### D2.4 Communication architecture tier mapping

Map `downlink_class(i)` to architecture candidates:

- LOW: VHF/UHF (store-and-forward, kbps-low Mbps regime)
- MEDIUM: S-band (low-tens of Mbps)
- HIGH: X-band (tens-hundreds of Mbps)
- EXTREME: Optical / very-high-rate RF (hundreds-Gbps class)

Define:

- `COMMS_selected` must satisfy both `R_nom_req_Mbps` and `COMMS_req(i)`.

## D3) Governing feasibility constraints

1. Throughput feasibility:

- `R_link_available(COMMS_selected, U_bus_sel, ADCS_selected) >= R_nom_req_Mbps`

2. Latency feasibility (qualitative):

- If `latency(i)=real_time`, disallow LOW COMMS tier (requires at least MEDIUM) and enforce additional ground contact/network requirement:
  - `COMMS_selected in {MEDIUM, HIGH, EXTREME}`

3. Compatibility:

- `ord(COMMS_selected) >= ord(COMMS_req(i))`

## D4) Subsystem class outputs

- `COMMS_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `R_nom_req_Mbps`, `T_eff_day` (continuous drivers)
- `antenna_complexity_class`, `transmitter_power_class` (functions of COMMS tier)

## D5) Coupling dependencies

- High COMMS tiers often require higher ADCS tier (pointing for narrow beams/optical links).
- COMMS peak transmit loads couple into EPS peak power and thermal dissipation.

---

# E) OBC / DATA HANDLING FORMULATION

## E1) Inputs consumed

- `compute_class(i)`, `D_day(i)`, `latency(i)`, `mission_value_score(i)` (from payload)
- `OBC_req(i)`
- constants: `f_store_util`, `M_data`

## E2) Derived intermediate variables

### E2.1 Onboard storage requirement

Assume storage must buffer at least `N_store` days of data (parameter; typical 1-3 days):

- `D_store_req_GB = (M_data * D_day(i) * N_store) / f_store_util`

### E2.2 Processing class

Map compute load class to OBC architecture:

- LOW: simple MCU-class OBC
- MEDIUM: higher-performance MCU + RTOS + basic fault tolerance
- HIGH: FPGA-assisted or high-performance compute (AI / intensive DSP)
- EXTREME: high-performance compute + redundancy + high-rate ingest pipelines

Latency influence:

- If `latency(i)=real_time`, require at least MEDIUM OBC tier.

Mission value influence (fault tolerance):

- If `mission_value_score(i) >= 4`, require at least MEDIUM fault tolerance tier.

## E3) Governing feasibility constraints

1. Storage feasibility:

- `Storage_available_GB(OBC_selected) >= D_store_req_GB`

2. Processing feasibility:

- `ord(OBC_selected) >= ord(OBC_req(i))`
- `latency(i)=real_time => ord(OBC_selected) >= ord(MEDIUM)`

## E4) Subsystem class outputs

- `OBC_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `D_store_req_GB`

## E5) Coupling dependencies

- OBC tier affects EPS (power) and THERM (heat) via housekeeping and compute waste heat.
- COMMS tier may require OBC tier for protocol stacks, encryption, and high-rate buffering.

---

# F) THERMAL CONTROL FORMULATION

## F1) Inputs consumed

- `P_avg_p(i)`, `P_peak_p(i)`, `heat_frac(i)`
- `thermal_ctl(i)`, `temp_stab(i)`
- `U_bus_sel`
- `THERM_req(i)`
- constants: `M_th`

## F2) Derived intermediate variables

### F2.1 Internal heat load proxy

Orbit-average internally generated heat:

- `Q_gen_avg_W = heat_frac(i) * (P_avg_p(i) + P_hk)`  [W]

Peak transient heat (proxy):

- `Q_gen_peak_W = heat_frac(i) * (P_peak_p(i) + P_hk_peak)`  [W]

Apply thermal margin:

- `Q_design_W = M_th * max(Q_gen_avg_W, Q_gen_peak_W)`

### F2.2 Radiator area need proxy (first-pass)

Use an effective radiator capability model:

- `Q_out_max_W = q0 * A_rad(U_bus_sel, THERM_selected)`

Where `q0` is an effective heat rejection density (W/m^2-equivalent proxy) and `A_rad` is available radiator area as a function of bus class and thermal tier.

Thermal feasibility requires:

- `Q_out_max_W >= Q_design_W`

### F2.3 Heater requirement proxy

If `temp_stab(i)=high` or `eclipse_req(i)=true`, impose heater capability:

- `Heater_req = 1` if `temp_stab(i)=high` OR `eclipse_req(i)=true`, else `0`

## F3) Governing feasibility constraints

1. Thermal rejection feasibility:

- `q0 * A_rad(U_bus_sel, THERM_selected) >= Q_design_W`

2. Stability requirement:

- `temp_stab(i)=high => THERM_selected in {HIGH, EXTREME}` (parameterizable)

3. Compatibility:

- `ord(THERM_selected) >= ord(THERM_req(i))`

## F4) Subsystem class outputs

- `THERM_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `Q_design_W`
- `thermal_solution_tier` consistent with `THERM_selected` and payload-provided `thermal_ctl(i)`

## F5) Coupling dependencies

- Thermal tier increases EPS load (heaters / active control).
- Thermal tier affects structure design (radiator placement, conduction paths).

---

# G) PROPULSION FORMULATION

## G1) Inputs consumed

- `PROP_req(i)` (from compatibility map)
- mission family/category context (from variant-level classification)
- `U_bus_sel`

## G2) Derived intermediate variables

### G2.1 Delta-v need proxy

Define a proxy delta-v requirement class:

- `delta_v_class = PROP_req(i)` (payload-driven proxy; mission/orbit may override later)

Map to numerical ranges (parameter library; example only):

- LOW: `delta_v_req ~= 0..5 m/s` (no propulsion or minimal)
- MEDIUM: `delta_v_req ~= 5..50 m/s` (maintenance / modest maneuvers)
- HIGH: `delta_v_req ~= 50..200 m/s` (formation, significant maintenance)
- EXTREME: `delta_v_req > 200 m/s` (not typical for CubeSat without dedicated propulsion)

### G2.2 Propulsion solution tier mapping

Candidate propulsion tiers:

- LOW: none
- MEDIUM: cold gas / resistojet / simple monoprop micro
- HIGH: electric microprop (e.g., ion/Hall) for higher total impulse
- EXTREME: chemical higher impulse (rare; likely large bus)

## G3) Governing feasibility constraints

1. Bus capacity constraints:

- If `PROP_selected != none`, require `U_bus_sel >= U_prop_min(PROP_selected)` and allocate propellant tank volume.

2. Compatibility:

- `ord(PROP_selected) >= ord(PROP_req(i))`

## G4) Subsystem class outputs

- `PROP_selected in {LOW, MEDIUM, HIGH, EXTREME}`
- `delta_v_req` proxy and propellant volume proxy (used in closure)

## G5) Coupling dependencies

- Propulsion mass/volume competes with payload and battery volume (STRUCT/EPS coupling).
- Propulsion power draw couples into EPS.

---

# H) SYSTEM-LEVEL MASS / POWER / VOLUME CLOSURE FORMULATION

## H1) Inputs consumed

All selected subsystem tiers:

- `U_bus_sel`, `STRUCT_selected`, `EPS_selected`, `ADCS_selected`, `COMMS_selected`, `OBC_selected`, `THERM_selected`, `PROP_selected`

Payload inputs:

- `m_p(i)`, `U_p(i)`, `P_avg_p(i)`, `P_peak_p(i)`, `D_day(i)`

Margins:

- `M_mass`, `M_pow`, `M_th`, `M_risk(risk(i))`

## H2) Derived intermediate variables

### H2.1 Mass closure

Let subsystem mass models be functions of tier and bus size:

- `m_struct = f_struct(U_bus_sel, STRUCT_selected)`
- `m_eps = f_eps(EPS_selected, P_solar_req_W, C_batt_req_Wh)`
- `m_adcs = f_adcs(ADCS_selected, U_bus_sel)`
- `m_comms = f_comms(COMMS_selected, R_nom_req_Mbps)`
- `m_obc = f_obc(OBC_selected, D_store_req_GB)`
- `m_therm = f_therm(THERM_selected, Q_design_W)`
- `m_prop = f_prop(PROP_selected, delta_v_req)`

Total dry mass estimate:

- `m_dry = M_risk(risk(i)) * ( m_p(i) + m_struct + m_eps + m_adcs + m_comms + m_obc + m_therm + m_prop ) * (1 + M_mass)`

### H2.2 Power closure

Total average power:

- `P_avg_total = M_pow * (P_avg_p(i) + P_hk + P_active_therm(THERM_selected) + P_prop_avg(PROP_selected))`

Total peak power:

- `P_peak_total = M_peak * max(P_peak_p(i), P_tx_peak(COMMS_selected), P_prop_peak(PROP_selected), P_avg_total)`

EPS feasibility must hold (Section B constraints).

### H2.3 Volume closure

Total used volume (in U):

- `U_used = U_payload_alloc(i) + U_batt(C_batt_req_Wh) + U_comms(COMMS_selected) + U_obc(OBC_selected) + U_prop(PROP_selected) + U_struct_misc`

Feasibility:

- `U_used <= f_fill * U_bus_sel`

### H2.4 Cost proxy and risk proxy

Define cost proxy as a weighted sum of tiers and key continuous drivers:

- `Cost_proxy = c0 + sum_S c_S * ord(S_selected) + c_P * P_solar_req_W + c_B * C_batt_req_Wh + c_R * R_nom_req_Mbps`

Define risk proxy:

- `Risk_proxy = r0 + r_int * ord(risk(i)) + sum_S r_S * ord(S_selected)`

## H3) Global feasibility constraints (system level)

1. Select exactly one tier per subsystem and one bus class:

- `sum_b x_b = 1`
- `for allS: sum_k y_{S,k} = 1`

2. Compatibility constraints:

- `ord(S_selected) >= ord(S_req(i))` for each subsystem requirement in compatibility map

3. Closure constraints:

- EPS generation and storage constraints (Section B)
- Volume and mass feasibility constraints (Section A/H)
- Comms throughput constraint (Section D)
- Thermal rejection constraint (Section F)

## H4) Notes for later CP-SAT discretization

1. Continuous drivers (e.g., `P_solar_req_W`, `C_batt_req_Wh`, `R_nom_req_Mbps`, `Q_design_W`) are computed deterministically from a chosen payload and chosen subsystem tiers.
2. Discretization occurs by:
   - selecting tier libraries with capacity thresholds, and
   - linking continuous requirements to tier feasibility masks.
3. Recommended solver pattern:
   - **payload selection variable** + **subsystem tier selection variables** + **hard feasibility constraints** + **objective on mass/cost/risk**.
