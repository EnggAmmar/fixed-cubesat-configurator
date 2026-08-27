from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.mission import MissionFamily


def _post(client: TestClient, body: dict) -> dict:
    resp = client.post("/api/v1/requirements/derive", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_remote_sensing_catalog_payload_derivation() -> None:
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
                "roi": {"type": "region", "query": "Pakistan"},
                "parameters": {"revisit_time_hours": 48},
            }
        },
    )

    derived = body["derived"]
    assert derived["required_downlink_class"] in {"medium", "high"}
    assert derived["required_pointing_accuracy_deg"] <= 0.2
    assert derived["recommended_orbit_family"] == "sun_synchronous_leo"
    assert any("Payload input: catalog payload" in t for t in derived["trace"])


def test_iot_my_payload_defaults_and_orbit() -> None:
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": "iot_communication",
                "payload": {
                    "type": "my_payload",
                    "name": "My IoT Payload",
                    "length_mm": 120,
                    "width_mm": 90,
                    "height_mm": 90,
                    "mass_kg": 1.2,
                    "avg_power_w": 4.0,
                    "peak_power_w": 6.0,
                    "data_rate_mbps": 2.0,
                },
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 12},
            }
        },
    )
    derived = body["derived"]
    assert derived["required_downlink_class"] == "low"
    assert derived["recommended_orbit_family"] == "leo"
    assert derived["required_storage_gb"] >= 16
    assert any("ROI: global coverage" in t for t in derived["trace"])


def test_navigation_my_payload_sets_propulsion_recommended() -> None:
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": "navigation",
                "payload": {
                    "type": "my_payload",
                    "name": "Nav Payload",
                    "length_mm": 90,
                    "width_mm": 90,
                    "height_mm": 140,
                    "mass_kg": 1.0,
                    "avg_power_w": 5.0,
                    "peak_power_w": 9.0,
                    "pointing_accuracy_deg": 3.0,
                },
                "roi": {"type": "region", "query": "EU"},
                "parameters": {"revisit_time_hours": 72},
            }
        },
    )
    derived = body["derived"]
    assert derived["recommended_orbit_family"] == "meo"
    assert derived["propulsion_recommended"] is True


def test_constraints_warn_on_max_bus_size() -> None:
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": MissionFamily.remote_sensing,
                "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
                "roi": {"type": "region", "query": "Pakistan"},
                "parameters": {"revisit_time_hours": 24},
            },
            "constraints": {"max_bus_size_u": 1.0},
        },
    )
    derived = body["derived"]
    assert any("Max bus size constraint" in w for w in derived["warnings"])
    assert any("Constraint check: max_bus_size_u" in t for t in derived["trace"])


def test_full_db_payload_recommended_bus_matches_own_rule_is_informational_only() -> None:
    """RS-EO-HSI-001 carries recommended_bus_min_u=6 in the full-DB record, and this
    pipeline's own packaging rule also lands on 6U for it - an exact match should
    surface as a trace note only, never a warning."""
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "RS-EO-HSI-001"},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 24},
            }
        },
    )
    derived = body["derived"]
    assert any("Cross-check: payload database recommends" in t for t in derived["trace"])
    assert not any("smaller than the payload database" in w for w in derived["warnings"])


def test_full_db_payload_undersized_vs_database_recommendation_warns() -> None:
    """NAV-RF-BEACON-001's own database record recommends >= 3U, but this pipeline's
    simple packaging heuristic computes only 1.5U for such a small/light payload -
    a real, currently-occurring gap (F-08) that should surface as an actionable
    warning, not just a trace note, since it's the tool sizing *smaller* than the
    database's own engineering judgment."""
    client = TestClient(create_app())
    body = _post(
        client,
        {
            "input": {
                "family": "navigation",
                "payload": {"type": "catalog", "payload_id": "NAV-RF-BEACON-001"},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 48},
            }
        },
    )
    derived = body["derived"]
    assert derived["required_bus_volume_u"] < 3.0
    assert any(
        "smaller than the payload database's own recommendation" in w for w in derived["warnings"]
    )
