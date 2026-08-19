from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.schemas.payload_synthesis import MyPayloadSynthesisRequest
from app.services.payload_synthesis import synthesize_confidential_payload


def test_synthesize_defaults_and_volume() -> None:
    req = MyPayloadSynthesisRequest(
        name=" Confidential Payload ",
        mission_family="remote_sensing",
        external_length_mm=200,
        external_width_mm=100,
        external_height_mm=100,
        mass_kg=2.5,
        power_avg_w=8,
        power_peak_w=12,
    )
    out = synthesize_confidential_payload(req)
    assert out.payload.type == "my_payload"
    assert out.payload.name == "Confidential Payload"
    assert out.payload.thermal_class.value == "standard"
    assert out.occupied_volume_u == pytest.approx(2.0)
    assert out.packaging.external_volume_cm3 == pytest.approx(2000.0)
    assert out.packaging.fits_standard_1u_cross_section is True
    assert out.packaging.estimated_stack_u == 2
    assert any("Thermal class not provided" in w for w in out.warnings)


def test_synthesize_clamps_peak_power() -> None:
    req = MyPayloadSynthesisRequest(
        name="X",
        mission_family="navigation",
        external_length_mm=100,
        external_width_mm=90,
        external_height_mm=90,
        mass_kg=1.0,
        power_avg_w=10,
        power_peak_w=5,
        optional_pointing_accuracy_deg=1.0,
    )
    out = synthesize_confidential_payload(req)
    assert out.payload.peak_power_w == out.payload.avg_power_w
    assert any("Peak power was below average power" in w for w in out.warnings)


def test_invalid_request_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        MyPayloadSynthesisRequest(
            name="bad",
            mission_family="remote_sensing",
            external_length_mm=-1,
            external_width_mm=10,
            external_height_mm=10,
            mass_kg=1,
            power_avg_w=1,
            power_peak_w=1,
        )


def test_preview_endpoint_ok_and_validation() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/payload/my-payload/preview",
        json={
            "name": "My Payload",
            "mission_family": "remote_sensing",
            "external_length_mm": 120,
            "external_width_mm": 80,
            "external_height_mm": 80,
            "mass_kg": 1.2,
            "power_avg_w": 5,
            "power_peak_w": 9,
            "optional_storage_required_gb": 128,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["payload"]["type"] == "my_payload"
    assert body["packaging"]["occupied_volume_u"] > 0
    assert any("Storage requirement captured" in w for w in body["warnings"])

    bad = client.post(
        "/api/v1/payload/my-payload/preview",
        json={
            "name": "Bad",
            "mission_family": "remote_sensing",
            "external_length_mm": -1,
            "external_width_mm": 80,
            "external_height_mm": 80,
            "mass_kg": 1.2,
            "power_avg_w": 5,
            "power_peak_w": 9,
        },
    )
    assert bad.status_code == 422
