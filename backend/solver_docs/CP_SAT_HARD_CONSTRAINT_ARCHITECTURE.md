# CP-SAT Hard Binary Feasibility Constraint Architecture (Prompt 10 - ONE_V3)

Generated on: 2026-04-30

## Scope

This document defines the solver-ready hard feasibility constraint architecture for a finite-domain CP-SAT (integer/boolean) model.

It consumes:

- Blueprint: `backend/solver_docs/SUBSYSTEM_MATHEMATICAL_FORMULATION.md`
- Discrete capacity libraries:
  - `backend/solver_libs/bus_capacity_library.json`
  - `backend/solver_libs/eps_capacity_library.json`
  - `backend/solver_libs/adcs_capacity_library.json`
  - `backend/solver_libs/comms_capacity_library.json`
  - `backend/solver_libs/obc_capacity_library.json`
  - `backend/solver_libs/thermal_capacity_library.json`
  - `backend/solver_libs/propulsion_capacity_library.json`
- Databases + metadata:
  - `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
  - `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
  - `backend/data_base/Navigation/MASTER_Navigation.json`
  - `backend/data_base/payload_compatibility_rules.json`
  - `backend/data_base/global_engineering_assumptions.json`

No OR-Tools / Python solver code is written here. This is the complete hard-constraint mathematics that Prompt 11+ will implement.

---

## 0) CP-SAT integer scaling (mandatory for implementation)

CP-SAT is integer/boolean. Any fractional quantity (kg, W, U, m^2, GB/day, Mb/s) must be scaled to integer units before coding.

Recommended scaling (Prompt 11 must pick one consistent scheme):

- Mass: kg -> g using `S_m = 1000`
- Power: W -> mW using `S_p = 1000`
- Volume: U -> mU using `S_u = 1000`
- Area: m^2 -> cm^2 using `S_a = 10000` (or mm^2 using `1e6`)
- Data/day: GB/day -> MB/day using `S_d = 1000` (ONE_V3 uses decimal GB)
- Data rate: Mb/s -> kb/s using `S_r = 1000`

All equations below are expressed in real units for clarity, but every constraint is written in a CP-SAT implementable (linear, integer-coefficient) form. Any divisions are to be removed by precomputing integer coefficients.

---

## 1) Decision variable definitions

### 1.1 Payload selection

Let `I` be the set of all payload products (across all mission families).

- `x_i in {0,1}` for each `i in I`
  - `x_i = 1` iff payload `i` is selected.

### 1.2 Mission branch selection (optional generalization)

Let mission families `F = {RS, IOT, NAV}` and let `I_f subseteq I` be the payloads belonging to family `f`.

- `z_f in {0,1}` for each `f in F`
  - `z_f = 1` iff mission family branch `f` is active.

### 1.3 Bus class selection

Let bus classes `U = {1U, 1.5U, 2U, 3U, 6U, 12U, 16U, 27U, 50U+}`.

- `b_u in {0,1}` for each `u in U`
  - `b_u = 1` iff bus class `u` is selected.

### 1.4 Subsystem tier selections (one-hot each)

Tier set `K = {LOW, MEDIUM, HIGH, EXTREME}`.

- EPS: `e_k in {0,1}` for `k in K`
- ADCS: `a_k in {0,1}` for `k in K`
- COMMS: `c_k in {0,1}` for `k in K`
- OBC: `o_k in {0,1}` for `k in K`
- THERMAL: `t_k in {0,1}` for `k in K`
- PROP: `p_k in {0,1}` for `k in K`

### 1.5 Integer aggregate variables

Aggregate variables are defined by equalities in Section 12:

- `M_total` [kg]
- `P_avg_total` [W]
- `P_peak_total` [W]
- `U_total` [U]
- `Cost_total` [cost units]
- `Risk_total` [risk units]

---

## 2) One-of selection constraints

### 2.1 Payload and branch

If mission family is fixed externally:

- `sum_{i in I} x_i = 1`

If mission family is a decision:

- `sum_{f in F} z_f = 1`
- `sum_{i in I_f} x_i = z_f` for each `f in F`

### 2.2 Bus and subsystem tiers (one-hot)

- `sum_{u in U} b_u = 1`
- `sum_{k in K} e_k = 1`
- `sum_{k in K} a_k = 1`
- `sum_{k in K} c_k = 1`
- `sum_{k in K} o_k = 1`
- `sum_{k in K} t_k = 1`
- `sum_{k in K} p_k = 1`

---

## 3) Parameters extracted from JSON (constants)

All parameters in this section are constants built from the JSON libraries/DBs.

### 3.1 Bus parameters (from `bus_capacity_library.json`)

For each bus class `u in U`:

- `U_bus(u)` [U] (`u_bus`)
- `U_usable(u)` [U] (`usable_internal_volume_u`)
- `M_dry_max(u)` [kg] (`max_recommended_dry_mass_kg`)
- `A_solar_body(u)` [m^2] (`available_body_solar_area_m2`)
- `A_solar_deploy(u)` [m^2] (`deployable_panel_option_area_m2`)
- `A_rad(u)` [m^2] (`nominal_radiator_area_m2`)
- `C_batt_pack(u)` [Wh] (`battery_packaging_limit_wh`)
- `m_bus_struct(u)` [kg] (`bus_structure_mass_kg`)
- `U_bus_struct(u)` [U] (`bus_structure_volume_u`)
- `bus_struct_stiff_class(u)` in `{LOW,MEDIUM,HIGH,EXTREME}` (`structural_stiffness_class`)
- `bus_cg_tol_class(u)` in `{LOW,MEDIUM,HIGH,EXTREME}` (`cg_tolerance_class`)

Selection projections (linear because of one-hot `b_u`):

- `U_bus_sel = sum_u b_u * U_bus(u)`
- `U_usable_sel = sum_u b_u * U_usable(u)`
- `M_dry_max_sel = sum_u b_u * M_dry_max(u)`
- `A_solar_total_sel = sum_u b_u * (A_solar_body(u) + A_solar_deploy(u))`
- `A_rad_sel = sum_u b_u * A_rad(u)`
- `C_batt_pack_sel = sum_u b_u * C_batt_pack(u)`
- `m_bus_struct_sel = sum_u b_u * m_bus_struct(u)`
- `U_bus_struct_sel = sum_u b_u * U_bus_struct(u)`

### 3.2 Tier parameters (from subsystem libraries)

For each tier `k in K`:

EPS tier:

- `P_solar_eps_max(k)` [W] (`max_solar_generation_w`)
- `C_batt_eps_max(k)` [Wh] (`max_battery_capacity_wh`)
- `P_peak_bus_max(k)` [W] (`max_peak_bus_power_w`)
- `P_eps_self(k)` [W] (`eps_avg_self_consumption_w`)
- `m_eps(k)` [kg] (`eps_mass_kg`), `U_eps(k)` [U] (`eps_volume_u`)
- supported bus min/max: `Umin_eps(k)`, `Umax_eps(k)`

ADCS tier:

- `point_acc(k)` [deg] (`pointing_accuracy_deg`)
- `ord_dist_reject(k)` in `{1,2,3,4}` derived from `disturbance_rejection_class`
- `P_adcs_avg(k)` [W] (`adcs_avg_power_w`), `P_adcs_peak(k)` [W] (`adcs_peak_power_w`)
- `m_adcs(k)` [kg] (`adcs_mass_kg`), `U_adcs(k)` [U] (`adcs_volume_u`)
- supported bus min/max: `Umin_adcs(k)`, `Umax_adcs(k)`

COMMS tier:

- `R_comms_max(k)` [Mb/s] (`nominal_supported_downlink_mbps`)
- `ord_point_dep(k)` in `{1,2,3,4}` derived from `pointing_dependency`
- `P_tx_avg(k)` [W] (`tx_avg_power_w`), `P_tx_peak(k)` [W] (`tx_peak_power_w`)
- `m_comms(k)` [kg] (`comms_mass_kg`), `U_comms(k)` [U] (`comms_volume_u`)
- supported bus min/max: `Umin_comms(k)`, `Umax_comms(k)`

OBC tier:

- `S_store_max(k)` [GB] (`max_storage_gb`)
- `R_ingest_max(k)` [Mb/s] (`supported_ingest_mbps`)
- `P_obc_avg(k)` [W] (`obc_avg_power_w`), `P_obc_peak(k)` [W] (`obc_peak_power_w`)
- `m_obc(k)` [kg] (`obc_mass_kg`), `U_obc(k)` [U] (`obc_volume_u`)
- supported bus min/max: `Umin_obc(k)`, `Umax_obc(k)`

THERMAL tier:

- `Q_tier_max(k)` [W] (`max_heat_rejection_w`)
- `q_reject_density(k)` [W/m^2] (`q_reject_density_w_per_m2`)
- `P_therm_avg(k)` [W] (`thermal_avg_power_w`), `P_therm_peak(k)` [W] (`thermal_peak_power_w`)
- `m_therm(k)` [kg] (`thermal_mass_kg`), `U_therm(k)` [U] (`thermal_volume_u`)
- supported bus min/max: `Umin_therm(k)`, `Umax_therm(k)`

PROP tier:

- `DV_cap(k)` [m/s] (`delta_v_support_mps`)
- `P_prop_avg(k)` [W] (`prop_avg_power_w`), `P_prop_peak(k)` [W] (`prop_peak_power_w`)
- `m_prop(k)` [kg] (`prop_mass_kg`), `U_prop(k)` [U] (`propellant_volume_u`)
- supported bus min/max: `Umin_prop(k)`, `Umax_prop(k)`

### 3.3 Global assumptions (from `global_engineering_assumptions.json`)

Let the following be constants (solver-local aliases):

From `power_assumptions`:

- `f_sun` = `sunlight_fraction`
- `f_ecl` = `eclipse_fraction`
- `eta_eps` = `eps_efficiency`
- `k_deg` = `solar_degradation_factor_eol`
- `M_pow` = `power_margin_factor`
- `M_peak` = `peak_power_headroom_factor`

From `battery_assumptions`:

- `DoD_lim` = `battery_dod_limit`
- `eta_batt` = `battery_round_trip_efficiency`
- `k_batt` = `battery_capacity_derating_factor`

From `mass_margin_assumptions`:

- `M_mass` = `mass_growth_margin`

From `volume_margin_assumptions`:

- `f_fill` = `volume_fill_limit`
- `U_over` = `payload_volume_overhead_u`

From `data_storage_assumptions`:

- `f_store_util` = `storage_utilization_limit`
- `M_data` = `daily_data_contingency_margin`

From `downlink_assumptions`:

- `eta_dl` = `downlink_efficiency_factor`
- `T_contact_day` = `nominal_contact_minutes_per_day`
- `f_contact_use` = `usable_contact_fraction`

From `thermal_assumptions`:

- `M_th` = `thermal_margin_factor`
- `f_heat_int` = `internal_heat_fraction_default`

Additional conservative constants (from `SUBSYSTEM_MATHEMATICAL_FORMULATION.md` defaults):

- `Pdens_sunlit` [W/m^2]
- `T_orbit_hr` [h]

### 3.4 Ordinals and mappings (discrete classes)

Tier ordinal:

- `ord(LOW)=1`, `ord(MEDIUM)=2`, `ord(HIGH)=3`, `ord(EXTREME)=4`

Bus ordering (for supported-range checks):

- `U_order = [1U, 1.5U, 2U, 3U, 6U, 12U, 16U, 27U, 50U+]`
- `ord_U(u)` in `{1..9}` for that ordering
- `ord_U_sel = sum_u b_u * ord_U(u)`

Class ordinals from payload DB / compatibility map:

- `ord_cg(low)=1`, `ord_cg(medium)=2`, `ord_cg(high)=3` (payload field `cg_sensitivity_class`)
- `ord_class(LOW)=1`, `ord_class(MEDIUM)=2`, `ord_class(HIGH)=3`, `ord_class(EXTREME)=4`

### 3.5 Compatibility requirements (from `payload_compatibility_rules.json`)

For each payload `i in I`, the compatibility map provides:

- `req_adcs(i)` (`adcs_class_required`)
- `req_comms(i)` (`comms_class_required`)
- `req_eps(i)` (`eps_class_required`)
- `req_therm(i)` (`thermal_class_required`)
- `req_obc(i)` (`obc_class_required`)
- `req_struct(i)` (`structure_class_required`)
- `req_prop(i)` (`propulsion_need_class`)

Selected required ordinals (linear, one payload):

- `ord_req_adcs_sel = sum_i x_i * ord_class(req_adcs(i))`
- `ord_req_comms_sel = sum_i x_i * ord_class(req_comms(i))`
- `ord_req_eps_sel = sum_i x_i * ord_class(req_eps(i))`
- `ord_req_therm_sel = sum_i x_i * ord_class(req_therm(i))`
- `ord_req_obc_sel = sum_i x_i * ord_class(req_obc(i))`
- `ord_req_struct_sel = sum_i x_i * ord_class(req_struct(i))`
- `ord_req_prop_sel = sum_i x_i * ord_class(req_prop(i))`

---

## 4) Bus feasibility hard constraints

### 4.1 Selected payload values (one payload)

From the payload DB (payload object fields):

- `m_p_sel = sum_i x_i * mass_kg(i)` [kg]
- `U_p_sel = sum_i x_i * payload_envelope_u(i)` [U]
- `bus_min_u_sel = sum_i x_i * recommended_bus_min_u(i)` [U]
- `bus_min_m_sel = sum_i x_i * recommended_bus_min_mass_kg(i)` [kg]

### 4.2 Subsystem packaging and mass sums (from tier selections)

Subsystem volumes:

- `U_sub = sum_k ( e_k*U_eps(k) + a_k*U_adcs(k) + c_k*U_comms(k) + o_k*U_obc(k) + t_k*U_therm(k) + p_k*U_prop(k) )`

Subsystem masses:

- `M_sub = sum_k ( e_k*m_eps(k) + a_k*m_adcs(k) + c_k*m_comms(k) + o_k*m_obc(k) + t_k*m_therm(k) + p_k*m_prop(k) )`

### 4.3 Volume feasibility (hard)

Total packaging volume (linear additive closure):

- `U_total = (U_p_sel + U_over) + U_bus_struct_sel + U_sub`

Hard feasibility:

- `U_total <= U_usable_sel`

Optional stricter fill limit:

- `U_total <= f_fill * U_bus_sel`

### 4.4 Mass feasibility (hard)

Nominal dry mass:

- `M_total_nom = m_p_sel + m_bus_struct_sel + M_sub`

Apply mass growth margin:

- `M_total = (1 + M_mass) * M_total_nom`

Hard feasibility:

- `M_total <= M_dry_max_sel`

### 4.5 Bus minimum hint feasibility (hard)

- `U_bus_sel >= bus_min_u_sel`
- `M_dry_max_sel >= bus_min_m_sel`

### 4.6 Structure/CG compatibility (hard)

Map bus stiffness and CG tolerance to ordinals:

- `ord_bus_stiff_sel = sum_u b_u * ord_class(bus_struct_stiff_class(u))`
- `ord_bus_cg_tol_sel = sum_u b_u * ord_class(bus_cg_tol_class(u))`

Hard feasibility:

- `ord_bus_stiff_sel >= ord_req_struct_sel`

Also enforce bus CG tolerance meets payload CG sensitivity burden:

- `ord_cg_sel = sum_i x_i * ord_cg(cg_sensitivity_class(i))` in `{1,2,3}`
- `ord_bus_cg_tol_sel >= ord_cg_sel`

---

## 5) EPS hard feasibility constraints

### 5.1 Average power closure (payload + subsystem)

- `P_payload_avg_sel = sum_i x_i * avg_power_w(i)` [W]
- `P_sub_avg = sum_k ( e_k*P_eps_self(k) + a_k*P_adcs_avg(k) + c_k*P_tx_avg(k) + o_k*P_obc_avg(k) + t_k*P_therm_avg(k) + p_k*P_prop_avg(k) )` [W]
- `P_avg_total = M_pow * (P_payload_avg_sel + P_sub_avg)` [W]

### 5.2 Solar generation feasibility (hard)

Define a linear solar requirement model by precomputing an integer coefficient in implementation:

- `P_solar_req >= alpha_solar * P_avg_total`
  - where `alpha_solar = 1 / (eta_eps * k_deg * f_sun)` (constant)

Hard feasibility:

- EPS tier cap: `P_solar_req <= sum_k e_k * P_solar_eps_max(k)`
- Bus area cap: `P_solar_req <= Pdens_sunlit * A_solar_total_sel`

### 5.3 Battery capacity feasibility (hard)

Eclipse energy requirement is linear in average power:

- `E_ecl_Wh >= alpha_ecl * P_avg_total`
  - where `alpha_ecl = (f_ecl * T_orbit_hr) / eta_eps` (constant)

Battery requirement:

- `C_batt_req >= alpha_batt * E_ecl_Wh`
  - where `alpha_batt = 1 / (DoD_lim * k_batt * eta_batt)` (constant)

Hard feasibility:

- EPS tier cap: `C_batt_req <= sum_k e_k * C_batt_eps_max(k)`
- Bus packaging cap: `C_batt_req <= C_batt_pack_sel`

### 5.4 Peak bus power feasibility (hard)

Precompute per payload:

- `P_payload_peak_eff(i) = max(peak_power_w(i), avg_power_w(i))` (constant)

Then:

- `P_payload_peak_eff_sel = sum_i x_i * P_payload_peak_eff(i)` [W]
- `P_sub_peak = sum_k ( a_k*P_adcs_peak(k) + c_k*P_tx_peak(k) + o_k*P_obc_peak(k) + t_k*P_therm_peak(k) + p_k*P_prop_peak(k) )` [W]
- `P_peak_total = M_peak * (P_payload_peak_eff_sel + P_sub_peak)` [W]

Hard feasibility:

- `P_peak_total <= sum_k e_k * P_peak_bus_max(k)`

### 5.5 EPS supported bus range legality (hard)

Convert library `supported_bus_min/max` to ordinals `ord_U_min_eps(k)`, `ord_U_max_eps(k)`.

- `ord_U_sel >= sum_k e_k * ord_U_min_eps(k)`
- `ord_U_sel <= sum_k e_k * ord_U_max_eps(k)`

### 5.6 EPS compatibility requirement (hard)

Let `ord_eps_tier = sum_k e_k * ord(k)` in `{1,2,3,4}`.

- `ord_eps_tier >= ord_req_eps_sel`

---

## 6) ADCS hard feasibility constraints

### 6.1 Pointing accuracy feasibility (hard)

- `point_sel = sum_i x_i * pointing_requirement_deg(i)` [deg]
- `point_cap = sum_k a_k * point_acc(k)` [deg]
- `point_sel <= point_cap`

### 6.2 CG sensitivity / disturbance rejection feasibility (hard)

Interpret ADCS tier ordinal as disturbance rejection capability:

- `ord_adcs_tier = sum_k a_k * ord(k)` in `{1,2,3,4}`
- `ord_adcs_tier >= ord_cg_sel`

### 6.3 ADCS supported bus range legality (hard)

- `ord_U_sel >= sum_k a_k * ord_U_min_adcs(k)`
- `ord_U_sel <= sum_k a_k * ord_U_max_adcs(k)`

### 6.4 ADCS compatibility requirement (hard)

- `ord_adcs_tier >= ord_req_adcs_sel`

---

## 7) COMMS hard feasibility constraints

### 7.1 Nominal rate feasibility (hard)

- `R_nom_sel = sum_i x_i * nominal_data_rate_mbps(i)` [Mb/s]
- `R_cap = sum_k c_k * R_comms_max(k)` [Mb/s]
- `R_nom_sel <= R_cap`

### 7.2 Daily downlink closure feasibility (hard)

Selected daily data requirement with contingency:

- `D_day_req_sel = sum_i x_i * (M_data * daily_data_generation_gb(i))` [GB/day]

Precompute tier daily capacity constants using assumptions:

- `T_eff_day = T_contact_day * f_contact_use` [min/day] (constant)
- `D_day_cap(k) = R_comms_max(k) * eta_dl * T_eff_day * 60 / (8 * 1000)` [GB/day] (constant per tier)

Hard feasibility:

- `D_day_req_sel <= sum_k c_k * D_day_cap(k)`

### 7.3 COMMS pointing dependency coupling (hard)

Let:

- `ord_comms_tier = sum_k c_k * ord(k)` in `{1,2,3,4}`
- `ord_comms_point_dep = sum_k c_k * ord_point_dep(k)` in `{1,2,3,4}`

Hard feasibility:

- `ord_adcs_tier >= ord_comms_point_dep`

### 7.4 COMMS supported bus range legality (hard)

- `ord_U_sel >= sum_k c_k * ord_U_min_comms(k)`
- `ord_U_sel <= sum_k c_k * ord_U_max_comms(k)`

### 7.5 COMMS compatibility requirement (hard)

- `ord_comms_tier >= ord_req_comms_sel`

---

## 8) OBC hard feasibility constraints

### 8.1 Onboard storage feasibility (hard)

Avoid bilinear `D_day_req_sel * days` by precomputing per payload:

- `S_req(i) = (M_data * daily_data_generation_gb(i)) * onboard_storage_days(i) / f_store_util` [GB] (constant; if `onboard_storage_days(i)` is null, substitute a global default in precompute)

Then:

- `S_req_sel = sum_i x_i * S_req(i)` [GB]
- `S_cap = sum_k o_k * S_store_max(k)` [GB]
- `S_req_sel <= S_cap`

### 8.2 Ingest/processing pipeline feasibility (hard)

Precompute per payload:

- `R_ing_req(i)` [Mb/s] as a conservative ingest-rate proxy derived from `daily_data_generation_gb(i)` and `latency_tolerance(i)` (and any fixed constants from the formulation).

Then:

- `R_ing_req_sel = sum_i x_i * R_ing_req(i)` [Mb/s]
- `R_ing_req_sel <= sum_k o_k * R_ingest_max(k)`

### 8.3 OBC supported bus range legality (hard)

- `ord_U_sel >= sum_k o_k * ord_U_min_obc(k)`
- `ord_U_sel <= sum_k o_k * ord_U_max_obc(k)`

### 8.4 OBC compatibility requirement (hard)

Let `ord_obc_tier = sum_k o_k * ord(k)` in `{1,2,3,4}`.

- `ord_obc_tier >= ord_req_obc_sel`

---

## 9) THERMAL hard feasibility constraints

### 9.1 Heat rejection requirement (hard)

Payload heat requirement per payload (precompute, constant):

- `P_th_design(i) = max(avg_power_w(i), mission_duty_cycle_percent(i)/100 * peak_power_w(i))`
- `Q_payload_req(i) = M_th * heat_dissipation_fraction(i) * P_th_design(i)` [W]

Selected payload heat:

- `Q_payload_req_sel = sum_i x_i * Q_payload_req(i)` [W]

Subsystem heat proxy (linear):

- `Q_sub_req = M_th * f_heat_int * P_sub_avg` [W]

Total required:

- `Q_req = Q_payload_req_sel + Q_sub_req`

### 9.2 Thermal availability (hard)

Tier cap:

- `Q_req <= sum_k t_k * Q_tier_max(k)`

Bus radiator area coupled cap via precomputed table:

- Precompute `Q_bus_cap(u,k) = q_reject_density(k) * A_rad(u)` [W]

Introduce AND binaries for the selected `(u,k)` pair:

- `z_{u,k} in {0,1}` for all `u in U, k in K`
- `z_{u,k} <= b_u`
- `z_{u,k} <= t_k`
- `z_{u,k} >= b_u + t_k - 1`
- `sum_{u,k} z_{u,k} = 1`

Hard feasibility:

- `Q_req <= sum_{u,k} z_{u,k} * Q_bus_cap(u,k)`

### 9.3 THERMAL supported bus range legality (hard)

- `ord_U_sel >= sum_k t_k * ord_U_min_therm(k)`
- `ord_U_sel <= sum_k t_k * ord_U_max_therm(k)`

### 9.4 THERMAL compatibility requirement (hard)

Let `ord_therm_tier = sum_k t_k * ord(k)` in `{1,2,3,4}`.

- `ord_therm_tier >= ord_req_therm_sel`

---

## 10) PROPULSION hard feasibility constraints

### 10.1 Delta-v proxy feasibility (hard)

Map required propulsion need class to a conservative delta-v proxy requirement (constants):

- `DV_req(LOW)=0`, `DV_req(MEDIUM)=10`, `DV_req(HIGH)=50`, `DV_req(EXTREME)=150` [m/s]

Then:

- `DV_req_sel = sum_i x_i * DV_req(req_prop(i))`
- `DV_cap_sel = sum_k p_k * DV_cap(k)`
- `DV_cap_sel >= DV_req_sel`

### 10.2 PROP supported bus range legality (hard)

- `ord_U_sel >= sum_k p_k * ord_U_min_prop(k)`
- `ord_U_sel <= sum_k p_k * ord_U_max_prop(k)`

### 10.3 PROP compatibility requirement (hard)

Let `ord_prop_tier = sum_k p_k * ord(k)` in `{1,2,3,4}`.

- `ord_prop_tier >= ord_req_prop_sel`

---

## 11) Cross-subsystem forbidden combinations (hard no-goods)

These are additional hard implications expressed as linear forbidden-pair constraints. They reduce search and block physically implausible combinations beyond pure capacity checks.

### 11.1 Bus-size forbiddance examples

If bus is <= 2U, forbid EXTREME EPS:

- `(b_1U + b_1.5U + b_2U) + e_EXTREME <= 1`

If bus is <= 2U, forbid EXTREME PROP:

- `(b_1U + b_1.5U + b_2U) + p_EXTREME <= 1`

If bus is 1U, forbid HIGH/EXTREME COMMS:

- `b_1U + c_HIGH <= 1`
- `b_1U + c_EXTREME <= 1`

### 11.2 Pointing-driven forbiddance

Precompute flags:

- `fine_point(i)=1` if `pointing_requirement_deg(i) <= 0.10`, else 0
- `ultra_fine(i)=1` if `pointing_requirement_deg(i) <= 0.05`, else 0

Then:

- `fine_point_sel + a_LOW <= 1` where `fine_point_sel = sum_i x_i * fine_point(i)`
- `ultra_fine_sel + a_MEDIUM <= 1` where `ultra_fine_sel = sum_i x_i * ultra_fine(i)`

### 11.3 Data-driven forbiddance

Precompute:

- `extreme_data(i)=1` if `daily_data_generation_gb(i) >= D_extreme_threshold` (engineering-chosen constant), else 0

Then:

- `extreme_data_sel + c_LOW <= 1`
- `extreme_data_sel + o_LOW <= 1`

### 11.4 Thermal burden forbiddance

Precompute:

- `high_thermal(i)=1` if `req_therm(i) in {HIGH,EXTREME}` OR payload thermal fields indicate active/stability requirements, else 0

Then:

- `high_thermal_sel + t_LOW <= 1`

### 11.5 COMMS-ADCS coupling

If COMMS is EXTREME, require ADCS >= HIGH:

- `c_EXTREME + a_LOW <= 1`
- `c_EXTREME + a_MEDIUM <= 1`

If COMMS is HIGH, require ADCS >= MEDIUM:

- `c_HIGH + a_LOW <= 1`

### 11.6 Supported-bus forbidden pairs (generic form)

For any subsystem tier variable `y_k` and any bus class `b_u` outside the tier supported range, add:

- `y_k + b_u <= 1`

This is equivalent to the ordinal range constraints; use whichever is simpler in implementation.

---

## 12) Global aggregate variable definitions (equalities)

These are not required for feasibility-only solving, but are required for reporting and later objective construction.

### 12.1 Mass

- `M_total_nom = m_p_sel + m_bus_struct_sel + M_sub`
- `M_total = (1 + M_mass) * M_total_nom`

### 12.2 Average power

- `P_avg_total = M_pow * (P_payload_avg_sel + P_sub_avg)`

### 12.3 Peak power

- `P_peak_total = M_peak * (P_payload_peak_eff_sel + P_sub_peak)`

### 12.4 Volume

- `U_total = (U_p_sel + U_over) + U_bus_struct_sel + U_sub`

### 12.5 Cost proxy

Define ordinals:

- `ord_eps_tier = sum_k e_k * ord(k)` etc.

Then a linear proxy (weights chosen later):

- `Cost_total = c0 + c_bus*U_bus_sel + c_eps*ord_eps_tier + c_adcs*ord_adcs_tier + c_comms*ord_comms_tier + c_obc*ord_obc_tier + c_therm*ord_therm_tier + c_prop*ord_prop_tier`

### 12.6 Risk proxy

Precompute a payload risk ordinal from the payload DB field `integration_risk`:

- `ord_risk(low)=1`, `ord_risk(medium)=2`, `ord_risk(high)=3`
- `ord_risk_sel = sum_i x_i * ord_risk(integration_risk(i))`

Then:

- `Risk_total = r0 + r_payload*ord_risk_sel + r_eps*ord_eps_tier + r_adcs*ord_adcs_tier + r_comms*ord_comms_tier + r_obc*ord_obc_tier + r_therm*ord_therm_tier + r_prop*ord_prop_tier`

---

## 13) Feasibility flag definition (diagnostic architecture)

In a strict CP-SAT model, feasibility is implicit: the model is feasible iff all hard constraints are satisfiable.

If a binary feasibility indicator is required (for soft-diagnosis runs), use violation binaries:

For each hard constraint `j` of the form `lhs_j <= rhs_j`, define `v_j in {0,1}` and a sufficiently large constant `BigM_j`:

- `lhs_j <= rhs_j + BigM_j * v_j`

Then define a global:

- `FEASIBLE in {0,1}`
- `v_j <= 1 - FEASIBLE` for all `j`
- `FEASIBLE >= 1 - sum_j v_j`

Interpretation:

- If `FEASIBLE=1`, then all `v_j=0` and all original hard constraints must hold.
- If `FEASIBLE=0`, some constraints may be violated and `v_j` localizes violations.

---

## Implementation notes (Prompt 11 precompute checklist)

1. Precompute payload constants used in constraints:
   - `P_payload_peak_eff(i)`, `S_req(i)`, `R_ing_req(i)`, `Q_payload_req(i)`, and all flags (`fine_point(i)`, `extreme_data(i)`, `high_thermal(i)`).
2. Convert library supported bus ranges and class strings to ordinals once (tables).
3. Remove divisions by multiplying both sides with denominators or by using scaled integer coefficients (`alpha_solar`, `alpha_ecl`, `alpha_batt`).
4. Keep the core model linear; use AND binaries only where unavoidable (thermal bus-area coupling table).
