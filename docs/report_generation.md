# Report Generation

The final result download uses the v1 mission report endpoint:

```text
POST /api/v1/mission/report?format=pdf
```

The frontend calls this endpoint from `downloadMissionReport()` and downloads the response as
`cubesat-mission-report.pdf`. The result page also exposes JSON and HTML downloads for engineering
review/debugging.

## Supported formats

All formats accept the same request body as `/api/v1/mission/report`:

```json
{
  "input": {
    "family": "remote_sensing",
    "payload": { "type": "catalog", "payload_id": "rs_hyperspec_v1" },
    "roi": { "type": "global" },
    "parameters": { "revisit_time_hours": 24 }
  }
}
```

Supported query values:

- `format=pdf`: engineering-grade PDF download, `application/pdf`, filename `cubesat-mission-report.pdf`.
- `format=html`: HTML report preview, `text/html; charset=utf-8`.
- `format=json`: structured report payload, `application/json; charset=utf-8`.
- `format=markdown` or `format=md`: backwards-compatible Markdown output.
- omitted `format`: defaults to Markdown for compatibility with existing direct callers.

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/mission/report?format=pdf" \
  -H "content-type: application/json" \
  --data @mission.json \
  --output cubesat-mission-report.pdf
```

## Report contents

The PDF/HTML report includes:

- cover and mission identity,
- executive KPI summary,
- mission inputs and derived-requirement provenance,
- orbit and constellation architecture,
- data budget and downlink/storage status,
- payload geometry and coverage status,
- selected platform and bus candidate comparison,
- selected subsystem architecture with selection reasons,
- budgets and margins,
- cost breakdown,
- solver trace and constraints,
- severity-ranked warnings, assumptions, radiation status, timeline, and next engineering actions.

## Docker dependency notes

- PDF rendering uses `reportlab`, declared in `backend/requirements.txt`.
- HTML preview rendering uses `jinja2`, declared in `backend/requirements.txt`.
- No browser runtime, Chromium install, WeasyPrint native libraries, or extra apt packages are required.
- The current `python:3.11-slim` backend image remains sufficient and minimal.

## Local troubleshooting

- Rebuild the backend image after dependency changes: `docker compose build backend`.
- Run the full stack: `docker compose up --build`.
- Check backend health/docs: `http://localhost:8000/docs`.
- Check frontend: `http://localhost:3000`.
- If PDF generation fails in Docker, inspect backend logs: `docker compose logs backend`.
- If the frontend download fails but backend works, verify nginx proxying through
  `http://localhost:3000/api/v1/mission/report?format=pdf` with a POST request.

## Known limitations

- Report metrics are display-only and do not change solver decisions.
- Data budget estimates use catalog daily data when available; otherwise they use the existing report
  assumption of full-day data-rate conversion and state that assumption explicitly.
- Swath is shown from catalog metadata when available, or from the documented altitude/FOV
  approximation only when both inputs exist.
- Required storage, contact windows, and duty cycle remain unavailable unless supplied by the payload
  or catalog metadata.
- Radiation screening displays "Radiation screening not available." in the v1 report path when no
  screening result is available and creates a deterministic warning.
- Docker runtime validation requires Docker to be installed locally.
