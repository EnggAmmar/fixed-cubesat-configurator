# Docker Runtime Solver Verification Report (Prompt 13 - ONE_V3)

Generated on: 2026-04-30

This report verifies CP-SAT solver runtime integration for:
- `backend/solver/` (OR-Tools CP-SAT implementation)
- required JSON assets under `backend/data_base/`, `backend/solver_libs/`, `backend/solver_precompute/`
- backend FastAPI route integration
- backend tests for runtime/shape/sanity

Important limitation:
- **Docker CLI is not available in the current environment** (`docker` command not found), so actual `docker compose build/up/exec` could not be executed here.
- All local (non-Docker) compile + solver runs + API tests were executed successfully.

---

## A) Dependency verification (ortools)

Verified backend Python dependencies in `backend/requirements.txt`:
- `ortools>=9.9` is present.

No dependency file changes were required for OR-Tools.

---

## B) Docker file copy / path verification

### Identified issue

Original Docker setup only copied `backend/app/` into the image and mounted `./backend:/app`.
This prevents `from backend.solver ...` imports inside the container because there was no `/app/backend` package path.

### Applied fix (backend-only)

Patched:
- `backend/Dockerfile`
- `docker-compose.yml`

Key changes:
- Image now copies the **entire backend payload** into `/app/backend` (includes `solver`, libs, precompute, docs, and data_base).
- Container runtime sets:
  - `PYTHONPATH=/app:/app/backend`
  - `working_dir: /app/backend`
  - volume mount: `./backend:/app/backend`

This ensures both:
- `import app...` works (because `/app/backend` is on `sys.path`)
- `import backend.solver...` works (because `/app` is on `sys.path`, containing the `backend/` package)

---

## C) Python import / compile verification (local)

Executed locally:
- `python -m compileall backend/solver backend/app backend/tests -q` ✅
- Imports:
  - `from backend.solver.cubesat_solver_runner import run_cubesat_solver, run_family_solver, run_cubesat_diagnostic` ✅

---

## D) Solver smoke tests (local)

Executed locally:

```python
from backend.solver.cubesat_solver_runner import run_cubesat_solver

for pid in ["RS-EO-VIS-001", "IOT-COM-BPT-001", "NAV-RF-PNT-001"]:
    result = run_cubesat_solver(pid)
    print(pid, result["status"], result["selection"], result["totals"])
```

Observed (local run):
- `RS-EO-VIS-001` → `OPTIMAL`, bus `16U`, `PROP=LOW`
- `IOT-COM-BPT-001` → `OPTIMAL`, bus `16U`
- `NAV-RF-PNT-001` → `OPTIMAL`, bus `12U`

Diagnostic smoke:
- `run_cubesat_diagnostic("RS-EO-VIS-001")` returns 9 bus cases and smallest feasible bus `16U`.

---

## E) Backend tests added (runtime + formulation consistency)

Added:
- `backend/tests/test_cubesat_solver_runtime.py`

Tests verify:
1. Data loading (payload catalog, compatibility map, assumptions, capacity libraries, precompute constants, objective coefficients)
2. Solver output shape + required totals keys
3. Sanity assertions on bus/tier choices for:
   - `RS-EO-VIS-001` (must be feasible; must not be `27U`; `PROP` remains `LOW`)
   - `IOT-COM-BPT-001` (must be feasible; must not be `27U`)
   - `NAV-RF-PNT-001` (must be feasible; must not exceed `16U`)
4. Diagnostic function presence and bus-by-bus output
5. API route smoke via FastAPI `TestClient`

Local test execution:
- `pytest backend/tests/test_cubesat_solver_runtime.py` ✅ (4 passed)

---

## F) API route integration (backend-only)

Added a minimal CP-SAT solver API endpoint:
- `POST /api/solve/cubesat`

Implementation:
- `backend/app/api/solve_cubesat.py`
- Registered in `backend/app/main.py`

Request:
```json
{
  "payload_id": "RS-EO-VIS-001",
  "top_n": 1,
  "diagnostic": false
}
```

Behavior:
- `diagnostic=true` → returns `run_cubesat_diagnostic(payload_id)`
- `top_n>1` → returns `run_family_solver(payload_id, top_n)`
- else → returns `run_cubesat_solver(payload_id)`

---

## G) Docker runtime smoke tests (not executed here)

Could not run the required Docker commands due to missing Docker CLI in this environment:
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend ...`

Recommended commands to run on a machine with Docker installed:

1) Build + start:
```bash
docker compose build
docker compose up -d
```

2) Import smoke test:
```bash
docker compose exec backend python - <<'PY'
from backend.solver.cubesat_solver_runner import run_cubesat_solver, run_family_solver, run_cubesat_diagnostic
print("imports_ok")
PY
```

3) Solver smoke test:
```bash
docker compose exec backend python - <<'PY'
from backend.solver.cubesat_solver_runner import run_cubesat_solver
for pid in ["RS-EO-VIS-001", "IOT-COM-BPT-001", "NAV-RF-PNT-001"]:
    r = run_cubesat_solver(pid)
    print(pid, r["status"], r["selection"], r["totals"])
PY
```

4) API smoke tests:
```bash
curl -X POST http://localhost:8000/api/solve/cubesat \\
  -H "Content-Type: application/json" \\
  -d '{"payload_id":"RS-EO-VIS-001","top_n":1,"diagnostic":false}'
```

```bash
curl -X POST http://localhost:8000/api/solve/cubesat \\
  -H "Content-Type: application/json" \\
  -d '{"payload_id":"RS-EO-VIS-001","diagnostic":true}'
```

---

## H) Final verdict

**READY_FOR_FRONTEND_INTEGRATION** (backend runtime perspective), with one external prerequisite:
- Docker must be available on the target machine to execute the container smoke tests; the Dockerfile and compose were patched to include all solver assets and correct Python import paths.

