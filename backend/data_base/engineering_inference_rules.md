# Engineering Inference Rules (First-Pass)

Generated on: 2026-04-29

## Purpose

This document describes the conservative, first-pass heuristics used to populate solver-facing engineering fields inside:

- `backend/data_base/Remote_Sensing/MASTER_Remote_Sensing.json`
- `backend/data_base/IoT_Comm/MASTER_IoT_Comm.json`
- `backend/data_base/Navigation/MASTER_Navigation.json`

Inputs used (existing fields and mission context):

- Product fields: `mass_kg`, `payload_envelope_u`, `avg_power_w`, `peak_power_w`, `nominal_data_rate_mbps`, `pointing_requirement_deg`, `ground_resolution_m`, `swath_km`
- Variant context: `payload_type`, `payload_variant`, `payload_group`

Non-goals:

- No attempt to estimate missing physics/mission parameters from external sources.
- No changes to any original payload values or mission hierarchy.

## Enumerations and Units

Unless stated otherwise, all inferred categorical fields are strings from a small controlled set.

- `recommended_bus_min_u`: integer, CubeSat-style discrete units in `{1,2,3,6,12,16,27}`
- `recommended_bus_min_mass_kg`: float (kg)
- `cg_sensitivity_class`: `"low" | "medium" | "high"`
- `deployment_clearance_needed`: boolean
- `mission_duty_cycle_percent`: integer percent, `0..100`
- `eclipse_operation_required`: boolean
- `battery_discharge_sensitivity`: `"low" | "medium" | "high"`
- `daily_data_generation_gb`: float (decimal GB/day, where 1 GB = 1e9 bytes)
- `compute_load_class`: `"low" | "medium" | "high"`
- `required_downlink_class`: `"low" | "medium" | "high" | "very_high"`
- `latency_tolerance`: `"real_time" | "near_real_time" | "delay_tolerant"`
- `ground_contact_dependency`: `"low" | "medium" | "high"`
- `heat_dissipation_fraction`: float, `0..1` (fraction of electrical power assumed to appear as internal waste heat)
- `thermal_control_class`: `"passive" | "passive_plus" | "active"`
- `temperature_stability_requirement`: `"low" | "medium" | "high"`
- `mission_value_score`: integer score, `1..5` (relative ranking only)
- `trl`: integer `1..9` (coarse estimate only)
- `integration_risk`: `"low" | "medium" | "high"`
- `radiation_sensitivity`: `"low" | "medium" | "high"`

## Field-by-Field Heuristics

### 1) recommended_bus_min_u

Goal: produce a conservative minimum bus size class capable of physically and energetically hosting the payload.

Steps:

1. Start with volume overhead: `ceil(payload_envelope_u + 0.5)`.
2. Enforce minimum practical payload-carrying size: at least `2U`.
3. Apply minimums based on:
   - Mass:
     - `mass_kg >= 3.0` -> at least `6U`
     - `mass_kg >= 2.0` -> at least `3U`
   - Power:
     - `peak_power_w >= 40` or `avg_power_w >= 20` -> at least `12U`
     - `peak_power_w >= 20` or `avg_power_w >= 12` -> at least `6U`
     - `peak_power_w >= 10` or `avg_power_w >= 6` -> at least `3U`
   - Data rate:
     - `nominal_data_rate_mbps >= 500` -> at least `12U`
     - `nominal_data_rate_mbps >= 100` -> at least `6U`
     - `nominal_data_rate_mbps >= 20` -> at least `3U`
   - Pointing:
     - `pointing_requirement_deg <= 0.05` -> at least `6U`
     - `pointing_requirement_deg <= 0.10` -> at least `3U`
   - Deployment mechanism likely:
     - If a deploy mechanism is likely (see `deployment_clearance_needed` section and “deploy mechanism likely” rules below), enforce at least `6U`.
4. Snap to the next available standard size in `{1,2,3,6,12,16,27}`.

“Deploy mechanism likely” is true when:

- `mounting_face` is `external_panel` or `side_deploy`, OR
- `payload_variant` contains keywords: `arrays`, `beacon`, `laser communication terminals`

### 2) recommended_bus_min_mass_kg

Goal: coarse minimum total spacecraft mass allocation consistent with the bus size and a non-extreme payload fraction.

Computed as:

- `max(0.7 * (recommended_bus_min_u * 2.0), mass_kg / 0.4)`

Rationale:

- `2.0 kg/U` is used as a conservative “practical mass density” figure.
- `0.4` payload mass fraction cap avoids implying unrealistically payload-dominated spacecraft.

### 3) cg_sensitivity_class

- `"high"` if deploy mechanism likely OR `pointing_requirement_deg <= 0.05`
- `"medium"` if `pointing_requirement_deg <= 0.10`
- `"low"` otherwise

### 4) deployment_clearance_needed

Set `true` when any of the following are true:

- `mounting_face` is `external_panel` or `side_deploy`
- `payload_variant` suggests external RF/optical apertures: keywords `arrays`, `beacon`, `laser communication terminals`
- The payload is observational / aperture-driven: keywords across `payload_group/payload_type/payload_variant` include
  `earth observation`, `space observation`, `optical imaging`, `infrared imaging`, `spectral imaging`, `telescope`,
  `synthetic aperture radar`, `weather radar`, `missile warning`, `uv sensors`

Otherwise `false`.

### 5) mission_duty_cycle_percent

A coarse operational duty cycle intended for first-pass power/data budgeting.

- Continuous sensor-like payloads -> `90%`:
  - `Magnetometers`, `Particle Detectors`, `Atmospheric Sensors`, `High-Energy Detectors`
  - `Timing Payloads`, `PNT Augmentation`, `Navigation Beacons`
- Communication payloads:
  - If `peak_power_w >= 20` or `avg_power_w >= 12` -> `40%`
  - Else -> `60%`
- Edge computing payloads -> `60%`
- Imaging payloads:
  - `Optical/IR/Spectral Imaging`, `Telescopes` -> `25%`
  - `Synthetic Aperture Radar`, `Weather Radar` -> `20%`
- Biological payloads -> `70%`
- Defense/intelligence (generic) -> `50%`
- Default -> `50%`

### 6) eclipse_operation_required

Set `true` if any of:

- `latency_tolerance == "real_time"`
- `mission_duty_cycle_percent >= 80`
- keywords include: `life support`, `timing payload`, `navigation beacon`, `pnt augmentation`

Else `false`.

### 7) battery_discharge_sensitivity

Based on peak-to-average draw and duty cycle:

- `"high"` if `peak_power_w >= max(20, avg_power_w*1.6)` OR duty >= 80
- `"medium"` if `peak_power_w >= max(10, avg_power_w*1.3)` OR duty >= 60
- `"low"` otherwise

### 8) daily_data_generation_gb

Computed using:

- `daily_data_generation_gb = nominal_data_rate_mbps * duty_fraction * utilization_factor * 10.8`

Where:

- `duty_fraction = mission_duty_cycle_percent / 100`
- `10.8` converts `1 Mbps` sustained for 24h into `GB/day` (decimal GB)

Utilization factors (to avoid treating link capability as always-on payload generation):

- Navigation / timing payloads: `0.01`
- Communication payloads: `0.10`
- Edge computing payloads: `0.20`
- Earth observation imaging/radar payloads: `1.00`
- Scientific instruments: `0.50`
- Biological payloads: `0.20`
- Defense/intelligence payloads: `0.50`
- Default: `0.20`

### 9) compute_load_class

- `"high"` for Edge Computing payloads (`GPU/FPGA/TPU/NPU/DSP/VPU`)
- `"high"`/`"medium"` for `Hyperspectral`, `SAR`, `Signal Processors`, `Software-Defined`, `Encryption Analysis`:
  - `"high"` if `daily_data_generation_gb >= 100` else `"medium"`
- Else data-driven:
  - `daily_data_generation_gb >= 100` -> `"high"`
  - `>= 10` -> `"medium"`
  - else `"low"`

### 10) required_downlink_class

Based on instantaneous capability and daily volume:

- `"very_high"` if `nominal_data_rate_mbps >= 500` OR `daily_data_generation_gb >= 1000`
- `"high"` if `nominal_data_rate_mbps >= 100` OR `daily_data_generation_gb >= 100`
- `"medium"` if `nominal_data_rate_mbps >= 10` OR `daily_data_generation_gb >= 10`
- `"low"` otherwise

### 11) latency_tolerance

Keyword-based:

- `"real_time"`: `missile warning`, `timing payload`, `pnt augmentation`, `navigation beacons`
- `"near_real_time"`: communications and RF-intel keywords (`communication`, `interceptors`, `signals intelligence`, `direction finding`, `geolocation`) and life-support-like payloads
- `"delay_tolerant"` otherwise

### 12) ground_contact_dependency

Based on data volume class:

- `"high"` if required downlink is `"high"`/`"very_high"` OR `daily_data_generation_gb >= 100`
- `"medium"` if required downlink is `"medium"` OR `daily_data_generation_gb >= 10`
- `"low"` otherwise

### 13) heat_dissipation_fraction

Conservative thermal assumption:

- `0.85` for strong transmitter/link keywords: `RF Transmitters`, `Transponders`, `Optical Communication`, `Laser`
- `0.90` otherwise

### 14) temperature_stability_requirement

Keyword-based:

- `"high"`: `Timing Payloads`, `Telescopes`, `Spectrometers`, `Hyperspectral`, `Infrared Imaging`, `Missile Warning`, `Bioreactor`, `Environment Control`
- `"medium"`: `Optical Imaging`, `UV Sensors`, `Particle Detectors`, `Magnetometers`
- `"low"` otherwise

### 15) thermal_control_class

Based on power levels and stability requirement:

- `"active"` if:
  - `temperature_stability_requirement == "high"` and (`avg_power_w >= 7` or `peak_power_w >= 15`), OR
  - `avg_power_w >= 15` or `peak_power_w >= 25`
- `"passive_plus"` if:
  - `avg_power_w >= 7` or `peak_power_w >= 15` or `temperature_stability_requirement == "high"`
- `"passive"` otherwise

### 16) mission_value_score

Relative, category-based score:

- `5`: defense/intelligence and missile-warning / SIGINT-like payloads
- `4`: navigation/timing; SAR/hyperspectral/IR/weather-radar earth observation
- `3`: earth observation (general), communications, scientific/biological payloads

### 17) trl

Conservative, coarse estimate:

- Default `6`
- `7` if:
  - `vendor` contains `"OEM"`, OR
  - `estimated_cost_usd >= 250000`
- Force `6` for:
  - `vendor` contains `"Derived"`, OR
  - Edge compute accelerator keywords (GPU/TPU/NPU/VPU)

### 18) integration_risk

- `"high"` if any of:
  - deploy mechanism likely
  - `required_downlink_class` is `"high"` or `"very_high"`
  - `avg_power_w >= 15` or `peak_power_w >= 25`
  - `pointing_requirement_deg <= 0.05`
- `"low"` if all of:
  - `peak_power_w <= 8` AND `avg_power_w <= 5`
  - `required_downlink_class == "low"`
  - `pointing_requirement_deg >= 0.15`
- `"medium"` otherwise

### 19) radiation_sensitivity

- `"high"` for:
  - Edge compute payloads (`GPU/FPGA/TPU/NPU/DSP/VPU`)
  - High-energy / particle detector classes (`Particle Detectors`, `High-Energy`, `Gamma/X-ray`)
- `"medium"` for:
  - SAR/weather radar, optical comm, RF-intel classes
- Default `"medium"`

