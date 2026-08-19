from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_regional_remote_sensing_prefers_sso_and_reasoning() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/constellation/estimate",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
                "roi": {"type": "region", "query": "Pakistan"},
                "parameters": {"revisit_time_hours": 48},
            },
            "estimator": {
                "allowed_orbit_families": ["sun_synchronous_leo", "leo"],
                "altitude_range_km": [450, 650],
                "inclination_range_deg": [90, 100],
                "payload_swath_km": 60,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["estimate"]
    assert body["recommended_orbit_family"] == "sun_synchronous_leo"
    assert any(500 <= a <= 650 for a in body["candidate_altitudes_km"])
    assert any(97.0 <= i <= 99.0 for i in body["candidate_inclinations_deg"])
    assert body["estimated_number_of_satellites"] >= 1
    assert any("Satellite count rule" in t for t in body["trace"])
    assert "candidate_walker_constellations" in body


def test_global_communication_prefers_leo_and_more_sats() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/constellation/estimate",
        json={
            "input": {
                "family": "iot_communication",
                "payload": {
                    "type": "my_payload",
                    "name": "Comms",
                    "length_mm": 90,
                    "width_mm": 90,
                    "height_mm": 90,
                    "mass_kg": 1.0,
                    "avg_power_w": 3.0,
                    "peak_power_w": 5.0,
                },
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 24},
            },
            "estimator": {
                "allowed_orbit_families": ["leo"],
                "altitude_range_km": [500, 800],
                "inclination_range_deg": [0, 100],
                "payload_swath_km": 1200,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["estimate"]
    assert body["recommended_orbit_family"] == "leo"
    assert any("Global coverage" in a for a in body["assumptions"])
    assert body["estimated_number_of_satellites"] >= 1


def test_stricter_revisit_requires_more_satellites() -> None:
    client = TestClient(create_app())
    base = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "region", "query": "Pakistan"},
            "parameters": {"revisit_time_hours": 48},
        },
        "estimator": {
            "allowed_orbit_families": ["sun_synchronous_leo"],
            "altitude_range_km": [450, 650],
            "inclination_range_deg": [90, 100],
            "payload_swath_km": 50,
        },
    }
    loose = client.post("/api/v1/constellation/estimate", json=base).json()["estimate"]
    base["input"]["parameters"]["revisit_time_hours"] = 12
    strict = client.post("/api/v1/constellation/estimate", json=base).json()["estimate"]

    assert strict["estimated_number_of_satellites"] >= loose["estimated_number_of_satellites"]
