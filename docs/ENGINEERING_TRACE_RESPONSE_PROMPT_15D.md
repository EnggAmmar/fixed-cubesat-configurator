# ENGINEERING TRACE RESPONSE (Prompt 15D)

Date: 2026-05-09

## 1) Files changed

**Backend**
- `backend/app/schemas/mission.py`
- `backend/app/api/v1/endpoints/mission.py`
- `backend/app/services/engineering_trace.py` (new)
- `backend/tests/test_api_mission.py`

**Frontend (types only)**
- `frontend/src/lib/api.ts`
- `frontend/src/__tests__/api_types_engineering_trace.test.ts`

## 2) `engineering_trace` schema

Added to `backend/app/schemas/mission.py`:
- `EngineeringTraceSolver`
- `EngineeringTraceSelection`
- `EngineeringTraceBudget`
- `EngineeringTraceSubsystem`
- `EngineeringTraceConstraint`
- `EngineeringTrace`

Extended:
- `MissionSolveResponse.engineering_trace: EngineeringTrace | None = None`

## 3) Mapping from current solve output → `engineering_trace`

Builder: `backend/app/services/engineering_trace.py` → `build_engineering_trace(...)`

Route: `/api/v1/mission/solve`

Populates:
- `engineering_trace.solver`
  - `route_used`: `"/api/v1/mission/solve"`
  - `solver_name`: `"v1_requirement_constellation_subsystem_solver"`
  - `status`: `"FEASIBLE"` on success
  - `solve_time_ms`: wall-clock time measured in endpoint (see below)
  - `objective_value`: `None` (not available from current v1 route)
  - `notes`: includes a forward-compat note when `input.parameters.engineering_preferences` is present

- `engineering_trace.selection`
  - `platform_name`, `bus_size_u`: from `solution.platform`
  - `payload_id`: catalog payload_id when `payload.type == "catalog"`
  - `payload_source`: `"catalog"` or `"my_payload"`
  - `subsystem_count`: `len(solution.subsystems)`

- `engineering_trace.budgets`
  - totals + margins from `solution.budgets`
  - `bus_volume_margin_u`: derived from `(platform.max_payload_volume_cm3 - requirements.payload_volume_cm3) / 1000`

- `engineering_trace.subsystems`
  - per-subsystem: `domain`, `name`, `mass_kg`, `avg_power_w`, `peak_power_w`, `cost_kusd`, `metadata`
  - `tier`: `None` on this route

- `engineering_trace.constraints`
  - Mass Budget (kg)
  - Average Power Budget (W)
  - Peak Power Budget (W)
  - Payload Volume Budget (U) (derived from platform payload volume capacity)
  - Each constraint gets `PASS/FAIL/UNKNOWN` based on margin sign where available

- `engineering_trace.trace`
  - includes `solution.trace`
  - appends concise constellation + budget summary lines

- `engineering_trace.warnings`
  - copies `solution.warnings`

## 4) Solve time measurement

In `backend/app/api/v1/endpoints/mission.py`:
- Uses `time.perf_counter()` around the end-to-end pipeline:
  - `derive_requirements`
  - `estimate_constellation`
  - `solve_subsystems`
  - trace building
- Stores milliseconds in `engineering_trace.solver.solve_time_ms`

## 5) Known limitations (intentional)

- `objective_value` is not available on the current `/api/v1/mission/solve` route (set to `None`).
- No bus-by-bus diagnostic or top-N alternatives exposed here yet.
- Tiered CP-SAT `/api/solve/cubesat` remains separate.
- `engineering_preferences` are accepted and carried, but still a no-op for solver behavior.

## 6) Tests run and results

Backend:
- `pytest -q backend/tests/test_api_mission.py` ✅
  - verifies `engineering_trace` presence + field mappings
  - verifies My Payload still works and includes trace
  - verifies preference-note behavior when `engineering_preferences` is sent

Frontend:
- `npm --prefix frontend test` ✅
  - includes `api_types_engineering_trace.test.ts` to confirm TS type accepts `engineering_trace`

## 7) Final verdict

ENGINEERING_TRACE_RESPONSE_READY_FOR_ANALYSIS_PAGE

