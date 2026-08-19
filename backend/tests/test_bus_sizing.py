from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.bus_sizing import BusCandidatesRequest
from app.services.bus_sizing import evaluate_bus_candidates
from app.services.catalog import get_catalog


def test_small_payload_fits_2u_before_3u() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/bus/candidates",
        json={
            "input": {
                "family": "iot_communication",
                "payload": {
                    "type": "my_payload",
                    "name": "Small",
                    "length_mm": 90,
                    "width_mm": 90,
                    "height_mm": 90,
                    "mass_kg": 0.8,
                    "avg_power_w": 2.0,
                    "peak_power_w": 3.0,
                },
                "roi": {"type": "region", "query": "PK"},
                "parameters": {"revisit_time_hours": 48},
            }
        },
    )
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    fitting = [c for c in candidates if c["overall_fit"]]
    assert fitting, "Expected at least one fitting candidate"
    assert fitting[0]["size_u"] in (2.0, 3.0)
    assert fitting[0]["size_u"] <= fitting[1]["size_u"] if len(fitting) > 1 else True


def test_cross_section_requires_8u() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/bus/candidates",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {
                    "type": "my_payload",
                    "name": "Wide Payload",
                    "length_mm": 150,
                    "width_mm": 120,
                    "height_mm": 110,
                    "mass_kg": 2.0,
                    "avg_power_w": 10.0,
                    "peak_power_w": 14.0,
                },
                "roi": {"type": "region", "query": "PK"},
                "parameters": {"revisit_time_hours": 48},
            },
            "constraints": {"include_commercial_sizes": True},
        },
    )
    assert resp.status_code == 200
    fitting = [c for c in resp.json()["candidates"] if c["overall_fit"]]
    assert fitting
    # 6U is 100x200 cross-section; with all dimensions >100 mm there is no valid orientation.
    assert fitting[0]["size_u"] >= 8.0
    assert fitting[0]["label"] in ("8U", "12U", "16U")


def test_excluding_commercial_sizes_removes_8u_16u() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/bus/candidates",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
                "roi": {"type": "region", "query": "PK"},
                "parameters": {"revisit_time_hours": 48},
            },
            "constraints": {"include_commercial_sizes": False},
        },
    )
    assert resp.status_code == 200
    sizes = {c["size_u"] for c in resp.json()["candidates"]}
    assert 8.0 not in sizes
    assert 16.0 not in sizes
    assert 12.0 in sizes


def test_full_master_catalog_payload_resolves_for_bus_candidates() -> None:
    payload_id = "RS-EO-HSI-001"
    assert get_catalog().get_payload(payload_id) is None

    resp = evaluate_bus_candidates(
        BusCandidatesRequest.model_validate(
            {
                "input": {
                    "family": "remote_sensing",
                    "payload": {"type": "catalog", "payload_id": payload_id},
                    "roi": {"type": "global"},
                    "parameters": {"revisit_time_hours": 24},
                },
                "constraints": {"include_commercial_sizes": True},
            }
        )
    )

    assert resp.candidates
    assert len(resp.candidates) >= 1
    assert resp.candidates[0].payload_occupied_volume_u == pytest.approx(1.690304)


def test_max_bus_size_constraint_filters() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/bus/candidates",
        json={
            "input": {
                "family": "navigation",
                "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
                "roi": {"type": "region", "query": "EU"},
                "parameters": {"revisit_time_hours": 72},
            },
            "constraints": {"max_bus_size_u": 3},
        },
    )
    assert resp.status_code == 200
    assert all(c["size_u"] <= 3.0 for c in resp.json()["candidates"])
