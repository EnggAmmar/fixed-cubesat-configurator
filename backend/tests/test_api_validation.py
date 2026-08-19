from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_solve_mission_rejects_payload_mission_family_mismatch() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/solve-mission",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {
                    "type": "my_payload",
                    "name": "Confidential",
                    "mission_family": "navigation",
                    "external_length_mm": 180,
                    "external_width_mm": 90,
                    "external_height_mm": 90,
                    "mass_kg": 2.1,
                    "power_avg_w": 8.0,
                    "power_peak_w": 14.0,
                },
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 72},
            }
        },
    )
    assert resp.status_code == 400, resp.text
    assert "mission_family must match" in resp.text


def test_report_download_rejects_unknown_format() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/report/download?format=xlsx",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 24},
            }
        },
    )
    assert resp.status_code == 400, resp.text
    assert "format must be" in resp.text


def test_v1_report_rejects_unknown_format() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/mission/report?format=docx",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 24},
            }
        },
    )
    assert resp.status_code == 400, resp.text
    assert "format must be" in resp.text


def test_payload_preview_validation_error_is_422() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/payload/my-payload/preview",
        json={
            "name": "Bad",
            "mission_family": "remote_sensing",
            "external_length_mm": -1,
            "external_width_mm": 10,
            "external_height_mm": 10,
            "mass_kg": 1,
            "power_avg_w": 1,
            "power_peak_w": 2,
        },
    )
    assert resp.status_code == 422, resp.text
