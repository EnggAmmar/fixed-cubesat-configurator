from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _req() -> dict:
    return {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }


def test_report_json_is_deterministic_for_same_inputs() -> None:
    client = TestClient(create_app())
    r1 = client.post("/api/report/download?format=json", json=_req())
    r2 = client.post("/api/report/download?format=json", json=_req())
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.headers["content-type"].startswith("application/json")
    assert r1.content == r2.content


def test_report_html_is_deterministic_for_same_inputs() -> None:
    client = TestClient(create_app())
    r1 = client.post("/api/report/download?format=html", json=_req())
    r2 = client.post("/api/report/download?format=html", json=_req())
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.headers["content-type"].startswith("text/html")
    assert b"CubeSat Mission Configuration Report" in r1.content
    assert b"CubeSat Mission Configurator logo" in r1.content
    assert b"data:image/png;base64," in r1.content
    assert r1.content == r2.content


def test_report_pdf_is_deterministic_for_same_inputs() -> None:
    client = TestClient(create_app())
    r1 = client.post("/api/report/download?format=pdf", json=_req())
    r2 = client.post("/api/report/download?format=pdf", json=_req())
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.headers["content-type"].startswith("application/pdf")
    assert r1.headers["content-disposition"] == "attachment; filename=cubesat-mission-report.pdf"
    assert r1.content.startswith(b"%PDF-1.4")
    assert r1.content == r2.content


def test_report_json_endpoint_has_sections() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/report.json", json=_req())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == "v1"
    assert "mission_summary" in body
    assert "payload" in body
    assert "derived_requirements" in body
    assert "subsystem_selection" in body
    assert "data:image/png;base64," not in resp.text
