from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.radiation_screening import RadiationMissionProfile
from app.schemas.subsystem_selection import SelectedComponent
from app.services.radiation_screening import screen_architecture_radiation

MISSING_RECORD_MESSAGE = "No radiation record found for component"


def _selected(domain: str, item_id: str, name: str) -> SelectedComponent:
    return SelectedComponent(
        domain=domain,
        item_id=item_id,
        name=name,
        mass_kg=0.1,
        avg_power_w=1.0,
        peak_power_w=2.0,
        cost_kusd=1.0,
        risk_points=1.0,
        metadata={},
    )


def test_screening_flags_low_tid_for_harsh_mission() -> None:
    mission = RadiationMissionProfile(
        orbit_family="meo",
        mission_duration_months=36,
        shielding_assumption_mm_al=2.0,
    )
    out = screen_architecture_radiation(
        mission=mission,
        selected=[
            SelectedComponent(
                domain="comms",
                item_id="comm_xband",
                name="X-band Downlink",
                mass_kg=0.7,
                avg_power_w=10.0,
                peak_power_w=18.0,
                cost_kusd=95.0,
                risk_points=12.0,
                metadata={},
            )
        ],
        optional_selected=[],
    )
    assert out.flags, "Expected at least one radiation flag"
    assert out.flags[0].severity in {"medium", "high"}
    assert "required" in out.flags[0].message


def test_unknown_component_emits_low_severity_flag() -> None:
    mission = RadiationMissionProfile(orbit_family="leo", mission_duration_months=12)
    out = screen_architecture_radiation(
        mission=mission,
        selected=[
            SelectedComponent(
                domain="obc",
                item_id="unknown_part",
                name="Unknown",
                mass_kg=0.1,
                avg_power_w=1.0,
                peak_power_w=2.0,
                cost_kusd=1.0,
                risk_points=1.0,
                metadata={},
            )
        ],
    )
    assert out.flags
    assert out.flags[0].severity == "low"
    assert MISSING_RECORD_MESSAGE in out.flags[0].message


def test_tier_metadata_gets_generic_estimate_instead_of_missing_record() -> None:
    """Regression test for the backend/solver radiation blind spot: components
    from that engine carry a 'tier' in metadata but have no entry in
    radiation_db.json (their ids look like 'backend_solver_eps_HIGH'). Screening
    should use a generic tier-level estimate instead of reporting a missing
    record for every one of them."""
    mission = RadiationMissionProfile(orbit_family="leo", mission_duration_months=12)
    out = screen_architecture_radiation(
        mission=mission,
        selected=[
            SelectedComponent(
                domain="eps",
                item_id="backend_solver_eps_HIGH",
                name="HIGH EPS",
                mass_kg=1.0,
                avg_power_w=5.0,
                peak_power_w=8.0,
                cost_kusd=10.0,
                risk_points=1.0,
                metadata={"tier": "HIGH"},
            )
        ],
    )
    assert all(MISSING_RECORD_MESSAGE not in flag.message for flag in out.flags)
    # A tier-tagged component always produces exactly one flag now: either a
    # low-severity "generic estimate, no elevated risk" note, or a genuine
    # risk flag computed from the generic estimate - never silence and never
    # the "no radiation record found" message checked above.
    assert len(out.flags) == 1
    assert "generic" in out.flags[0].message.lower()


def test_selected_catalog_components_have_radiation_records() -> None:
    mission = RadiationMissionProfile(
        orbit_family="sun_synchronous_leo",
        mission_duration_months=24,
        shielding_assumption_mm_al=2.0,
    )
    out = screen_architecture_radiation(
        mission=mission,
        selected=[
            _selected("structure", "plat_8u_high", "8U Platform (High Capability)"),
            _selected("adcs", "adcs_optical", "ADCS (Optical-Grade)"),
            _selected("eps", "eps_basic", "EPS (Basic)"),
            _selected("obc", "obc_payload_gpu", "OBC (Payload GPU)"),
            _selected("comm", "comm_optical", "Optical Downlink Terminal"),
            _selected("thermal", "thermal_enhanced", "Thermal (Enhanced)"),
            _selected("propulsion", "prop_none", "No Propulsion"),
        ],
    )

    assert out.flags == []
    assert all("Radiation risk" not in flag.message for flag in out.flags)
    assert all(MISSING_RECORD_MESSAGE not in flag.message for flag in out.flags)


def test_rs_hsi_mission_warnings_do_not_report_missing_radiation_records() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/solve-mission",
        json={
            "input": {
                "family": "remote_sensing",
                "payload": {"type": "catalog", "payload_id": "RS-EO-HSI-001"},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 24},
            }
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert all(MISSING_RECORD_MESSAGE not in warning for warning in body["warnings"])
    assert all(MISSING_RECORD_MESSAGE not in flag["message"] for flag in body["radiation"]["flags"])


def test_api_endpoint_returns_flags() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/radiation/screen",
        json={
            "mission": {
                "orbit_family": "sun_synchronous_leo",
                "mission_duration_months": 24,
                "shielding_assumption_mm_al": 2,
            },
            "selected": [
                {
                    "domain": "obc",
                    "item_id": "obc_high_storage",
                    "name": "OBC (High Storage)",
                    "mass_kg": 0.75,
                    "avg_power_w": 8,
                    "peak_power_w": 14,
                    "cost_kusd": 78,
                    "risk_points": 12,
                    "metadata": {},
                }
            ],
            "optional_selected": [],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "flags" in body
    assert isinstance(body["flags"], list)
    assert any("tid_krad" in f["message"] for f in body["flags"])
