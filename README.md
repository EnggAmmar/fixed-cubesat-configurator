# CubeSat Design Configurator

CubeSat Design Configurator is a conceptual design platform for automated CubeSat configuration selection based on mission requirements. It turns payload, orbit, coverage, pointing, power, data, and mission preferences into a feasible preliminary spacecraft architecture with traceable engineering margins.

> This tool supports early-phase concept exploration. Its outputs are not a substitute for detailed engineering analysis, qualification, or mission assurance.

## Overview

The application guides a user from mission definition to a candidate CubeSat design. A React interface collects mission and payload inputs, a FastAPI backend derives engineering requirements and constellation estimates, and an optimization layer selects compatible platform and subsystem options from catalog data. Results include the selected architecture, budget closure, warnings, solver trace, and downloadable reports.

## Key features

- Mission-driven configuration workflow for catalog and user-defined payloads
- Payload, region-of-interest, orbit, constellation, and mission-parameter inputs
- Automated bus and subsystem selection subject to engineering constraints
- Mass, volume, average/peak power, storage, downlink, pointing, thermal, and propulsion checks
- Explainable feasibility results, residual margins, warnings, and optimization trace
- Interactive React/Three.js visualization of Earth, orbit, and spacecraft context
- PDF, HTML, Markdown, and JSON reporting support
- Docker-based local deployment plus backend, frontend, and end-to-end tests

## System architecture

```text
React + Three.js frontend
          |
          | REST / JSON
          v
FastAPI API and validation
          |
          v
Mission and engineering services
  - requirement derivation
  - constellation estimation
  - bus and subsystem sizing
          |
          v
Optimization and feasibility layer
          |
          +---- catalog and capacity data (JSON)
          |
          v
Selected architecture, margins, warnings, and reports
```

The repository is organized around `frontend/` for the browser application, `backend/` for APIs and engineering/optimization services, `docs/` for architecture and technical material, and `scripts/` for repeatable checks.

## Optimization methods

The current codebase uses Google OR-Tools CP-SAT for discrete platform and subsystem selection. It applies hard feasibility constraints first and then ranks feasible configurations using an integer-scaled, preference-sensitive objective.

The planned optimization comparison framework includes:

- **Greedy baseline** — a deterministic, fast reference method that selects the first or locally best compatible component at each stage. It provides a transparent baseline for solution quality and runtime comparisons.
- **MILP optimization** — a mixed-integer linear programming formulation for globally selecting a bus and subsystem combination while satisfying coupled mission, mass, volume, power, data, pointing, thermal, and compatibility constraints.
- **MILP altitude-range envelope optimization** — an extension that evaluates or co-optimizes designs across a permitted altitude interval, preserving feasibility across the mission envelope instead of at a single nominal altitude.

CBC and HiGHS are intended solver backends for the MILP variants. They are not dependencies of the present CP-SAT implementation and must be integrated before those variants can be executed.

## Supported subsystems

- Payload
- Attitude Determination and Control System (ADCS)
- Electrical Power System (EPS)
- On-Board Computer (OBC)
- Communication
- Propulsion
- Thermal control

## Technology stack

- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Optimization:** Google OR-Tools CP-SAT; planned MILP support through CBC/HiGHS
- **Frontend:** React, TypeScript, Vite, Three.js, React Three Fiber, Zustand
- **Reporting:** ReportLab and Jinja2
- **Infrastructure:** Docker and Docker Compose
- **Testing and quality:** pytest, Ruff, Vitest, Playwright, ESLint, Prettier
- **Data:** repository-managed JSON catalogs and capacity libraries

PostgreSQL and Redis are not required by the current repository.

## Installation

### Docker (recommended)

Prerequisites: Docker Desktop or Docker Engine with the Compose plugin.

```bash
git clone https://github.com/EnggAmmar/CubeSat-Design-Configurator.git
cd CubeSat-Design-Configurator
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- Backend API documentation: <http://localhost:8000/docs>

Stop the application with `docker compose down`.

### Local development

Prerequisites: Python 3.10+ and a current Node.js LTS release.

Backend (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Backend (macOS/Linux):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server prints its local URL, normally <http://localhost:5173>.

## Usage

1. Open the frontend and select a mission family.
2. Choose a catalog payload or enter a custom payload definition.
3. Define the region of interest and mission parameters.
4. Submit the mission for analysis and optimization.
5. Review the proposed bus and subsystem architecture, feasibility margins, warnings, and engineering trace.
6. Export the available mission report artifacts for further concept studies.

## Verification and tests

```bash
make test
```

Individual checks are also available:

```bash
cd backend && ruff check . && pytest -q
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build
```

End-to-end tests can be run from `frontend/` with `npm run test:e2e`, or against the full Docker stack with `npm run test:e2e:docker`.

## Future improvements

- Implement and benchmark the Greedy, MILP, and altitude-range envelope methods
- Add CBC and HiGHS solver adapters and reproducible solver-comparison reports
- Expand and validate the component catalogs with supplier and qualification data
- Add uncertainty, sensitivity, robustness, and lifecycle-cost analysis
- Improve orbit, coverage, communications-link, thermal, and radiation fidelity
- Support collaborative projects, saved design variants, and configuration versioning
- Add deployment profiles, authentication, and optional persistent data services
- Extend report traceability and verification against higher-fidelity engineering tools

## License

No license file is currently included. All rights are reserved unless a license is added by the repository owner.
