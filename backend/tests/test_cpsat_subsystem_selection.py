from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _solve(client: TestClient, mission_input: dict, constraints: dict | None = None) -> dict:
    payload: dict = {"input": mission_input}
    if constraints is not None:
        payload["constraints"] = constraints
    resp = client.post("/api/v1/optimization/subsystems/solve", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _selected_ids(resp: dict, domain: str) -> set[str]:
    return {c["item_id"] for c in resp["selected"] if c["domain"] == domain}


def test_feasible_remote_sensing_catalog_case() -> None:
    client = TestClient(create_app())
    resp = _solve(
        client,
        {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "region", "query": "Pakistan"},
            "parameters": {"revisit_time_hours": 48},
        },
    )
    assert resp["feasible"] is True
    assert "structure" in {c["domain"] for c in resp["selected"]}
    assert "comm_xband" in _selected_ids(resp, "comm")
    assert "adcs_precise" in _selected_ids(resp, "adcs")
    assert "thermal_enhanced" in _selected_ids(resp, "thermal")
    assert resp["totals"] is not None
    assert resp["margins"] is not None
    assert any("Objective:" in t for t in resp["trace"])


def test_feasible_my_payload_case() -> None:
    client = TestClient(create_app())
    resp = _solve(
        client,
        {
            "family": "iot_communication",
            "payload": {
                "type": "my_payload",
                "name": "My IoT Payload",
                "length_mm": 90,
                "width_mm": 90,
                "height_mm": 90,
                "mass_kg": 1.2,
                "avg_power_w": 2.0,
                "peak_power_w": 3.0,
                "data_rate_mbps": 2.0,
            },
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        },
    )
    assert resp["feasible"] is True
    # Low data-rate should allow S-band and basic storage
    assert "comm_sband" in _selected_ids(resp, "comm")
    assert "obc_basic" in _selected_ids(resp, "obc")


def test_infeasible_case_returns_actionable_warnings() -> None:
    client = TestClient(create_app())
    resp = _solve(
        client,
        {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "Impossible Storage",
                "length_mm": 100,
                "width_mm": 90,
                "height_mm": 90,
                "mass_kg": 1.0,
                "avg_power_w": 5.0,
                "peak_power_w": 9.0,
                "storage_required_gb": 5000,
                "data_rate_mbps": 120.0,
                "pointing_accuracy_deg": 0.2,
            },
            "roi": {"type": "region", "query": "PK"},
            "parameters": {"revisit_time_hours": 48},
        },
    )
    assert resp["feasible"] is False
    assert resp["status"] in {"precheck_infeasible", "infeasible"}
    assert any("storage" in w.lower() for w in resp["warnings"])


def test_high_data_rate_requires_stronger_comms_and_storage() -> None:
    client = TestClient(create_app())
    resp = _solve(
        client,
        {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "High Rate Payload",
                "length_mm": 200,
                "width_mm": 120,
                "height_mm": 120,
                "mass_kg": 2.6,
                "avg_power_w": 10.0,
                "peak_power_w": 16.0,
                "data_rate_mbps": 120.0,
                "storage_required_gb": 512.0,
                "pointing_accuracy_deg": 0.3,
                "thermal_class": "sensitive",
            },
            "roi": {"type": "region", "query": "PK"},
            "parameters": {"revisit_time_hours": 24},
        },
    )
    assert resp["feasible"] is True
    assert "comm_xband" in _selected_ids(resp, "comm")
    assert "obc_high_storage" in _selected_ids(resp, "obc")
