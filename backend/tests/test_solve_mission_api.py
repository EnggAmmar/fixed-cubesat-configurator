from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_solve_mission_catalog_payload_happy_path() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/solve-mission",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
                "roi": {"type": "region", "query": "Pakistan"},
                "parameters": {"revisit_time_hours": 48},
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["payload_summary"]["type"] == "catalog"
    assert body["derived_requirements"]["required_bus_volume_u"] > 0
    assert "subsystem_selection" in body
    assert isinstance(body["subsystem_selection"]["selected"], list)
    assert "report_summary_markdown" in body


def test_solve_mission_my_payload_synthesis_path() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/solve-mission",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {
                    "type": "my_payload",
                    "name": "Confidential Camera",
                    "mission_family": "remote_sensing",
                    "external_length_mm": 180,
                    "external_width_mm": 90,
                    "external_height_mm": 90,
                    "mass_kg": 2.1,
                    "power_avg_w": 8.0,
                    "power_peak_w": 14.0,
                    "optional_data_rate_mbps": 120.0,
                    "optional_pointing_accuracy_deg": 0.15,
                    "optional_storage_required_gb": 256.0,
                },
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 72},
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["payload_summary"]["type"] == "my_payload"
    assert body["payload_synthesis"] is not None
    assert body["normalized_payload"] is not None
    assert body["normalized_payload"]["type"] == "my_payload"


def test_solve_mission_infeasible_case_returns_partial_outputs() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/solve-mission",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {
                    "type": "my_payload",
                    "name": "Huge Instrument",
                    "mission_family": "remote_sensing",
                    "external_length_mm": 350,
                    "external_width_mm": 250,
                    "external_height_mm": 250,
                    "mass_kg": 8.0,
                    "power_avg_w": 30.0,
                    "power_peak_w": 60.0,
                },
                "roi": {"type": "region", "query": "Pakistan"},
                "parameters": {"revisit_time_hours": 24},
            },
            "constraints": {"max_bus_size_u": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subsystem_selection"]["feasible"] is False
    assert body["derived_requirements"]["required_bus_volume_u"] > 0
    assert isinstance(body["warnings"], list)
    assert body["radiation"] is not None
