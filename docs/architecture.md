# Architecture (v1)

## Monorepo layout

- `backend/`: FastAPI app + engineering services (requirements → constellation estimate → CP-SAT selection → report)
- `frontend/`: React + Vite wizard UI (mission family → payload → ROI → parameters → result)
- `docs/`: documentation

## Primary flow

1. User completes the wizard in the frontend.
2. Frontend sends `POST /api/v1/mission/solve` to backend.
3. Backend:
   - derives requirements from payload + mission inputs
   - estimates a constellation (v1 approximation)
   - selects a platform + subsystems with OR-Tools CP-SAT
4. Frontend renders summary cards and allows downloading `POST /api/v1/mission/report` (Markdown).

