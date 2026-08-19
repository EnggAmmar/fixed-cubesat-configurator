# CP-SAT Objective Strategy (Prompt 11 - ONE_V3)

Generated on: 2026-04-30

## Scope

This document instantiates the numerical objective strategy and proxy coefficients for Prompt 12 implementation.

Artifacts produced:

- `backend/solver_precompute/objective_function_coefficients.json`

This objective is designed for feasibility-first preliminary optimization:

- Capability is guaranteed by hard feasibility constraints (Prompt 10).
- The objective is NOT intended to maximize payload performance.
- The objective drives selection toward the smallest practical feasible spacecraft.

No OR-Tools solver code is written here.

---

## 1) Philosophy

Primary goals (in order):

1. Smallest feasible spacecraft (mass and bus size discipline).
2. Lowest practical average power burden (reduces EPS complexity and thermal load).
3. Lowest practical cost proxy (COTS realism).
4. Lowest integration and subsystem complexity risk.
5. Explicitly penalize oversizing the bus beyond payload minimum.

---

## 2) Cost proxy tables (engineering conservative)

Cost proxies are coarse screening values for trade studies and are not intended as vendor quotes.

Cost tables are defined in:

- `backend/solver_precompute/objective_function_coefficients.json`

They provide USD-like magnitude scaling:

- bus class costs (structure + integration overhead proxy)
- subsystem tier costs (relative hardware and integration complexity proxy)

Rationale:

- Costs should increase super-linearly from LOW to EXTREME tiers, especially for COMMS and PROP.
- Larger buses impose non-trivial cost growth due to structure, integration, and test overhead.
- Prompt 12.5 flattens the bus-class cost curve to avoid over-penalizing larger buses when they are required for packaging/power closure.

---

## 3) Risk proxy tables

Risk proxies are integer penalty points used to discourage high complexity when multiple feasible solutions exist.

They are defined in:

- `backend/solver_precompute/objective_function_coefficients.json`

Included sources:

- payload integration risk: `integration_risk` in payload DB (low/medium/high) -> points
- subsystem tier complexity risk: tier -> points per subsystem

Rationale:

- EXTREME COMMS and PROP tiers carry disproportionately higher integration/test risk.
- ADCS fine-pointing tiers also carry significant calibration and integration risk.
- Prompt 12.5 softens the integer objective risk influence by increasing the risk normalization scale (reducing `k_risk_per_point` by ~30%).

---

## 4) Global weighted objective

Prompt 10 defines the aggregate variables:

- `M_total`, `P_avg_total`, `Cost_total`, `Risk_total`

Prompt 11 instantiates a scalar objective:

Minimize:

Z =
  w_mass * normalized(M_total)
+ w_avg_power * normalized(P_avg_total)
+ w_cost * normalized(Cost_total)
+ w_risk * normalized(Risk_total)
+ w_bus_oversize * normalized(bus_oversize_penalty)

Where each `normalized(X) = X / X_norm` uses the normalization scales defined in:

- `backend/solver_precompute/objective_function_coefficients.json`

### 4.1 Chosen weights (percent)

Weights sum to 100:

- `w_mass = 35`
- `w_avg_power = 20`
- `w_cost = 25`
- `w_risk = 12`
- `w_bus_oversize = 8`

Justification:

- Mass and cost dominate early feasibility and integration success.
- Power strongly correlates with EPS/thermal/packaging difficulty.
- Risk steers away from extreme-tier solutions when a simpler solution is feasible.
- Oversize penalty is strengthened to prevent the solver from lazily selecting larger buses when feasibility is only mildly improved.

---

## 5) Bus oversize penalty definition

The oversize penalty is defined in bus volume units U:

- `bus_oversize_u = max(0, U_bus_sel - bus_min_u_sel)`

Where:

- `U_bus_sel` is the selected bus nominal size (from the bus library via one-hot `b_u`).
- `bus_min_u_sel` is the selected payload's `recommended_bus_min_u`.

Implementation note:

- Prompt 10 hard feasibility already enforces `U_bus_sel >= bus_min_u_sel`, so the `max(0, ...)` can be implemented as the linear difference `(U_bus_sel - bus_min_u_sel)` in scaled integer units.

---

## 6) CP-SAT integerization notes

OR-Tools CP-SAT minimizes a linear integer objective. Prompt 11 provides:

- normalization scales
- weights
- a recommended `objective_integer_scale`
- derived integer coefficients for a recommended scaling (kg->g, W->mW, U->mU)

All of these are stored in:

- `backend/solver_precompute/objective_function_coefficients.json`

If coefficient rounding causes a term to vanish (coefficient rounds to 0), increase `objective_integer_scale`.
