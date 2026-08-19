# Document Generation Audit

Audit reflects the current working tree on `main_document_generation`.

## Current frontend flow

1. The `Download Mission Doc` button in `frontend/src/pages/ResultPage.tsx` calls
   `downloadMissionReport(input)`.
2. `downloadMissionReport` in `frontend/src/lib/api.ts` currently posts to
   `POST /api/v1/mission/report?format=pdf`.
3. The browser download filename is currently `cubesat-mission-report.pdf`.

## Current returned file type

- `POST /api/v1/mission/report?format=pdf` returns `application/pdf` with
  `Content-Disposition: attachment; filename=cubesat-mission-report.pdf`.
- The same v1 route still supports the backwards-compatible default Markdown path:
  `POST /api/v1/mission/report` returns `text/markdown; charset=utf-8`.
- The v1 route also supports `format=json` and `format=html`; default remains Markdown to avoid
  breaking direct callers that used the original route without a query string.
- The separate non-v1 report route supports `POST /api/report/download?format=pdf|html|json`.

## Service wiring

- `backend/app/api/v1/endpoints/mission.py` is the frontend-facing route.
- The v1 route derives requirements, estimates constellation, solves subsystems, then renders through
  `backend/app/services/pdf_report.py` for PDF or `backend/app/services/report.py` for Markdown.
- `backend/app/services/mission_report.py` is wired into `backend/app/api/report.py`, not directly into
  the v1 frontend route. It powers `/api/report.json` and `/api/report/download`.

## Existing report tests

- `backend/tests/test_mission_report_generation.py`
  - deterministic JSON download from `/api/report/download?format=json`
  - deterministic HTML download from `/api/report/download?format=html`
  - deterministic PDF download from `/api/report/download?format=pdf`
  - section coverage for `/api/report.json`
- `backend/tests/test_api_mission.py`
  - Markdown response for `/api/v1/mission/report`
  - PDF response for `/api/v1/mission/report?format=pdf`
- `backend/tests/test_api_validation.py`
  - unknown report format rejection for `/api/report/download`

## Available PDF libraries

- `reportlab` is declared in `backend/requirements.txt` for deterministic backend PDF rendering
  without browser/system HTML-to-PDF dependencies.
- Frontend has Playwright as a dev dependency for tests, but the backend does not depend on a browser
  runtime for report generation.

## Minimal PDF dependencies

- The selected minimal dependency is `reportlab` in `backend/requirements.txt`; it does not require
  browser or heavyweight system packages in the current `python:3.11-slim` Docker image.
- If HTML/CSS fidelity is required, `weasyprint` or a Playwright/Chromium renderer can produce richer
  layouts, but they add Docker system packages and/or browser installation steps. That is more reliable
  for CSS fidelity, but not minimal for this repository.
