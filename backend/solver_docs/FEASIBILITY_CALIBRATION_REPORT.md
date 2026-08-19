# Feasibility Calibration Report (Prompt 12.9 - ONE_V3)

Generated on: 2026-04-30

Scope: targeted relaxation of *over-conservative hard feasibility closures* only (volume, thermal, secondary mass), based on Prompt 12.75 diagnostics.  
Non-scope: objective weights, solver architecture, payload databases, compatibility semantics.

## Patched calibration factors (exact)

- Volume packaging concurrency factor: `f_pack = 0.72`
  - Applied only to additive subsystem volumes `(EPS + ADCS + COMMS + OBC + THERM + PROP)`.
  - Payload envelope and harness reserve are not reduced.
- Thermal tier capacity uplift: `+22%` to `thermal_capacity_library.json:max_heat_rejection_w` for all tiers.
- Thermal bus radiator utilization factor: `f_rad_util = 1.15`
  - Applied in the thermal bus-cap coupling `Q_bus_cap = q_density * A_rad * f_rad_util`.
- Mass reserve rebalance factor: `f_mass_reserve = 0.86`
  - Applied only to **non-payload reserve adders** (bus structure margin term), not payload mass and not subsystem masses.

## Before/after smallest feasible bus (from diagnostic runs)

| Payload ID | Mission family | Prompt 12.75 smallest feasible bus | Prompt 12.9 smallest feasible bus | Shift |
|---|---|---:|---:|---:|
| `RS-EO-VIS-001` | Remote Sensing | `27U` | `27U` | `0` |
| `IOT-COM-BPT-001` | IoT Comm | `27U` | `16U` | `-11U` |
| `NAV-RF-PNT-001` | Navigation | `16U` | `12U` | `-4U` |

## Post-patch diagnostic observations (binding/near-binding)

## Dominant failing-family shift (Prompt 12.75 → Prompt 12.9)

Counts below refer to how many forced-bus cases **below the smallest feasible bus** reported each failing family at least once (diagnostic summary).

- `RS-EO-VIS-001`
  - Prompt 12.75: `VOLUME_CLOSURE_FAIL`(7), `COMPATIBILITY_ORDINAL_FAIL`(5), `THERMAL_REJECTION_FAIL`(5), `MASS_CLOSURE_FAIL`(4)
  - Prompt 12.9: `COMPATIBILITY_ORDINAL_FAIL`(6), `FORBIDDEN_NO_GOOD_FAIL`(5), `THERMAL_REJECTION_FAIL`(5), `VOLUME_CLOSURE_FAIL`(5)
- `IOT-COM-BPT-001`
  - Prompt 12.75: `THERMAL_REJECTION_FAIL`(5), `VOLUME_CLOSURE_FAIL`(5), `EPS_SOLAR_FAIL`(4), `FORBIDDEN_NO_GOOD_FAIL`(4)
  - Prompt 12.9: `THERMAL_REJECTION_FAIL`(5), `VOLUME_CLOSURE_FAIL`(5), `EPS_SOLAR_FAIL`(4), `MASS_CLOSURE_FAIL`(4)
  - Key improvement: smallest feasible bus moved down to `16U` and `COMMS_DOWNLINK_FAIL` becomes the primary blocker at `12U` (instead of universal volume/thermal).
- `NAV-RF-PNT-001`
  - Prompt 12.75: `VOLUME_CLOSURE_FAIL`(5), `MASS_CLOSURE_FAIL`(4), `THERMAL_REJECTION_FAIL`(4), `COMPATIBILITY_ORDINAL_FAIL`(3)
  - Prompt 12.9: `THERMAL_REJECTION_FAIL`(5), `MASS_CLOSURE_FAIL`(4), `COMPATIBILITY_ORDINAL_FAIL`(4), `VOLUME_CLOSURE_FAIL`(4)
  - Key improvement: smallest feasible bus moved down to `12U`.

### `RS-EO-VIS-001`

- Smallest feasible bus remains `27U`.
- At `27U` (first feasible): volume margin is no longer near-binding (`+5.736 U`), but thermal margin is now closer to binding (`+11.9 W`) with a lower thermal tier than before.
- Remaining infeasibility drivers below `27U` are now dominated by a mix of `COMPATIBILITY_ORDINAL_FAIL`, `FORBIDDEN_NO_GOOD_FAIL`, and residual `THERMAL_REJECTION_FAIL`/`VOLUME_CLOSURE_FAIL` on smaller buses.

Engineering interpretation: volume closure was materially relaxed, but this payload remains dominated by high-burden comms/pointing/ordinal constraints that keep smaller buses infeasible.

### `IOT-COM-BPT-001`

- Smallest feasible bus moved down from `27U` → `16U`.
- At `16U` (first feasible): near-binding closure is now volume (`+1.10 U`) while thermal has meaningful reserve (`+16.81 W`).

Engineering interpretation: the packaging concurrency factor and thermal uplift removed the previous universal volume/thermal infeasibility barrier for mid buses, allowing the solver to settle in a more credible preliminary packaging regime.

### `NAV-RF-PNT-001`

- Smallest feasible bus moved down from `16U` → `12U`.
- At `12U` (first feasible): thermal margin becomes the closest reserve (`+6.2864 W`), volume remains healthy (`+2.22 U`).

Engineering interpretation: thermal coupling was the main blocker for 6U/12U-class buses; the targeted thermal softening moves feasibility down without removing ordinal semantics.

## Verdict (Prompt 12.9)

- Oversized-bus pathology is **materially reduced** for the IoT and Navigation sample payloads (downshifts to `16U` and `12U` respectively).
- Remote sensing high-rate payload `RS-EO-VIS-001` remains `27U`-bounded; additional tightening/relaxation would require addressing comms/pointing/compatibility hard constraints (out of scope for Prompt 12.9).
