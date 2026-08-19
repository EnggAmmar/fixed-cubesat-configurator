from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.taxonomy import get_taxonomy
from solver.cubesat_data_loader import load_all_data
from solver.cubesat_precompute_loader import load_all_precompute
from solver.cubesat_solver_runner import run_cubesat_diagnostic, run_cubesat_solver


def test_cubesat_data_and_precompute_load() -> None:
    data = load_all_data()
    pre = load_all_precompute()

    assert len(data.payloads) >= 100
    assert len(data.bus_library) >= 5
    assert "EXTREME" in data.eps_library
    assert "EXTREME" in data.comms_library
    assert "EXTREME" in data.thermal_library

    assert len(pre.payload_precompute.payloads) == len(data.payloads)
    assert "bus_class_cost_usd_proxy" in pre.objective.cost_proxy_tables


def _assert_solution_shape(result: dict) -> None:
    assert result["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"}
    assert "selection" in result and isinstance(result["selection"], dict)
    assert "totals" in result and isinstance(result["totals"], dict)

    totals = result["totals"]
    for k in (
        "M_total_kg",
        "P_avg_total_w",
        "P_peak_total_w",
        "U_total_u",
        "Cost_total_usd_proxy",
        "Risk_total_points",
        "BusOversize_u",
    ):
        assert k in totals


def test_cubesat_solver_smoke_samples() -> None:
    rs = run_cubesat_solver("RS-EO-VIS-001")
    _assert_solution_shape(rs)
    assert rs["status"] in {"OPTIMAL", "FEASIBLE"}
    assert rs["selection"]["bus_class"] in {"12U", "16U"}
    assert rs["selection"]["prop_tier"] == "LOW"
    assert rs["selection"]["comms_tier"] in {"HIGH", "EXTREME"}
    assert rs["selection"]["obc_tier"] in {"HIGH", "EXTREME"}

    iot = run_cubesat_solver("IOT-COM-BPT-001")
    _assert_solution_shape(iot)
    assert iot["status"] in {"OPTIMAL", "FEASIBLE"}
    assert iot["selection"]["bus_class"] != "27U"

    nav = run_cubesat_solver("NAV-RF-PNT-001")
    _assert_solution_shape(nav)
    assert nav["status"] in {"OPTIMAL", "FEASIBLE"}
    assert nav["selection"]["bus_class"] in {"6U", "12U", "16U"}


def test_cubesat_diagnostic_smoke_rs_vis_001() -> None:
    d = run_cubesat_diagnostic("RS-EO-VIS-001")
    assert d["payload_id"] == "RS-EO-VIS-001"
    cases = d["bus_cases"]
    assert isinstance(cases, list)
    assert len(cases) == 9
    first_feasible = next((c for c in cases if c["status"] == "FEASIBLE"), None)
    assert first_feasible is not None
    assert first_feasible["bus_class"] in {"12U", "16U"}
    assert "margins" in first_feasible


def test_cubesat_solver_api_route() -> None:
    client = TestClient(create_app())

    r = client.post("/api/solve/cubesat", json={"payload_id": "RS-EO-VIS-001"})
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] in {"OPTIMAL", "FEASIBLE"}
    assert payload["selection"]["bus_class"] in {"12U", "16U"}

    r2 = client.post("/api/solve/cubesat", json={"payload_id": "RS-EO-VIS-001", "diagnostic": True})
    assert r2.status_code == 200
    payload2 = r2.json()
    assert payload2["payload_id"] == "RS-EO-VIS-001"
    assert len(payload2["bus_cases"]) == 9


def test_cubesat_diagnostic_rejects_seeded_v1_catalog_ids_with_clear_error() -> None:
    client = TestClient(create_app())

    resp = client.post(
        "/api/solve/cubesat",
        json={"payload_id": "rs_hyperspec_v1", "diagnostic": True},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unknown selected_payload_id: rs_hyperspec_v1"


def test_taxonomy_default_payloads_are_accepted_by_cubesat_diagnostic_api() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    taxonomy = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in taxonomy["families"]}

    # These categories are representative of the three mission families and are
    # used by the frontend through payloads[0]. They must be accepted by the
    # diagnostic API even if the resulting engineering case is infeasible.
    representative_defaults = [
        families["remote_sensing"]["payload_categories"][0]["payloads"][0]["payload_id"],
        families["iot_communication"]["payload_categories"][0]["payloads"][0]["payload_id"],
        families["navigation"]["payload_categories"][0]["payloads"][0]["payload_id"],
    ]

    assert representative_defaults
    for payload_id in representative_defaults:
        resp = client.post(
            "/api/solve/cubesat",
            json={"payload_id": payload_id, "diagnostic": True},
        )
        assert resp.status_code == 200, payload_id
        body = resp.json()
        assert body["payload_id"] == payload_id
        assert "bus_cases" in body
        assert isinstance(body["bus_cases"], list)
        assert len(body["bus_cases"]) == 9
