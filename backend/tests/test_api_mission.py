from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal local envs
    PdfReader = None


def _pdf_text(pdf: bytes) -> str:
    if PdfReader is None:
        return pdf.decode("latin1", errors="ignore")
    reader = PdfReader(BytesIO(pdf))
    assert reader.pages
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_mission_solve_ok() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "region", "query": "Pakistan"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200
    body = resp.json()
    assert body["solution"]["platform"]["bus_size_u"] in (6.0, 8.0, 3.0)
    assert body["constellation"]["satellites"] >= 1
    assert "budgets" in body["solution"]
    assert body["engineering_trace"]["solver"]["route_used"] == "/api/v1/mission/solve"
    assert body["engineering_trace"]["solver"]["solve_time_ms"] >= 0
    assert (
        body["engineering_trace"]["selection"]["bus_size_u"]
        == body["solution"]["platform"]["bus_size_u"]
    )
    assert (
        body["engineering_trace"]["budgets"]["total_mass_kg"]
        == body["solution"]["budgets"]["total_mass_kg"]
    )
    assert len(body["engineering_trace"]["subsystems"]) == len(body["solution"]["subsystems"])

    trace_subsystems = body["engineering_trace"]["subsystems"]
    assert isinstance(trace_subsystems, list)
    assert len(trace_subsystems) > 0
    assert any(s.get("selection_reason") for s in trace_subsystems)
    assert any(s.get("source_database") for s in trace_subsystems)

    constraint_names = {c["name"] for c in body["engineering_trace"]["constraints"]}
    assert "Mass Budget" in constraint_names
    assert "Average Power Budget" in constraint_names
    assert "Peak Power Budget" in constraint_names


def test_mission_solve_seeded_catalog_payload_still_works() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text


def test_mission_solve_accepts_full_db_iot_payload_id_and_derives_requirements() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "iot_communication",
            "payload": {"type": "catalog", "payload_id": "IOT-COM-BPT-001"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["requirements"]["payload_mass_kg"] == 1.9
    assert body["requirements"]["payload_volume_cm3"] == pytest.approx(1600.0)
    assert body["requirements"]["payload_avg_power_w"] == 8.5
    assert body["requirements"]["payload_peak_power_w"] == 12.0
    assert body["requirements"]["min_downlink_mbps"] == 45.0
    assert body["requirements"]["max_pointing_error_deg"] == 0.15
    assert body["requirements"]["thermal_class"] == "standard"


def test_mission_solve_accepts_full_db_navigation_payload_id_and_derives_requirements() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "navigation",
            "payload": {"type": "catalog", "payload_id": "NAV-RF-PNT-001"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["requirements"]["payload_mass_kg"] == 1.35
    assert body["requirements"]["payload_volume_cm3"] == pytest.approx(557.568)
    assert body["requirements"]["payload_avg_power_w"] == 5.8
    assert body["requirements"]["payload_peak_power_w"] == 8.8
    assert body["requirements"]["min_downlink_mbps"] == 18.0
    assert body["requirements"]["max_pointing_error_deg"] == 0.22
    assert body["requirements"]["thermal_class"] == "sensitive"


def test_mission_solve_unknown_payload_id_returns_400() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "UNKNOWN-PAYLOAD-XYZ"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 400
    assert "Unknown payload_id" in resp.text


def test_taxonomy_to_solve_integration_for_iot_and_navigation() -> None:
    app = create_app()
    client = TestClient(app)

    taxonomy = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in taxonomy["families"]}

    def _first_payload_id(family_id: str) -> str:
        fam = families[family_id]
        for cat in fam["payload_categories"]:
            if cat["category_id"] == "my_payload":
                continue
            payloads = cat.get("payloads") or []
            if payloads:
                return payloads[0]["payload_id"]
        raise AssertionError(f"No non-my_payload payloads found for {family_id}")

    for family_id in ("iot_communication", "navigation"):
        pid = _first_payload_id(family_id)
        req = {
            "input": {
                "family": family_id,
                "payload": {"type": "catalog", "payload_id": pid},
                "roi": {"type": "global"},
                "parameters": {"revisit_time_hours": 48},
            }
        }
        resp = client.post("/api/v1/mission/solve", json=req)
        assert resp.status_code == 200, resp.text


def test_mission_solve_accepts_engineering_preferences() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "region", "query": "Pakistan"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {
                    "altitude_km": 500,
                    "orbit_type": "leo",
                    "lifetime_years": 2,
                    "propulsion_preference": "electric",
                    "pointing_precision_preference": "fine",
                    "downlink_rate_preference": "high",
                    "optimization_priority": "balanced",
                    "max_budget_usd": 1000000,
                    "max_bus_u": 12,
                },
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200
    body = resp.json()
    assert "solution" in body
    assert "constellation" in body
    assert body["solution"]["platform"]["bus_size_u"] <= 12
    assert body["solution"]["budgets"]["total_cost_kusd"] <= 1000
    assert body["requirements"]["min_downlink_mbps"] >= 120
    assert body["requirements"]["max_pointing_error_deg"] <= 0.1
    notes = body["engineering_trace"]["solver"].get("notes") or []
    assert not any("not yet connected" in n for n in notes)
    assert any("Engineering preferences are connected" in n for n in notes)
    preferences = body["engineering_trace"]["preferences"]
    assert any(p["preference"] == "propulsion_preference" for p in preferences)
    assert body["engineering_trace"]["solver"]["objective_value"] is not None
    assert body["engineering_trace"]["solver"]["objective_weights"]["cost"] == 5.0


def test_mission_solve_max_bus_preference_constrains_or_fails() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 24,
                "engineering_preferences": {"max_bus_u": 6},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    assert resp.json()["solution"]["platform"]["bus_size_u"] <= 6

    req["input"]["parameters"]["engineering_preferences"]["max_bus_u"] = 1
    infeasible = client.post("/api/v1/mission/solve", json=req)
    assert infeasible.status_code == 400
    assert "max_bus_size_u" in infeasible.text


def test_mission_solve_max_budget_preference_is_hard_constraint() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {
                    "propulsion_preference": "electric",
                    "max_budget_usd": 500000,
                },
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 400
    assert "No feasible subsystem configuration" in resp.text


def test_mission_solve_downlink_preference_cannot_relax_payload_requirement() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"downlink_rate_preference": "low"},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requirements"]["min_downlink_mbps"] == 80.0
    assert any(
        p["preference"] == "downlink_rate_preference" and "max(payload requirement" in p["effect"]
        for p in body["engineering_trace"]["preferences"]
    )


def test_mission_solve_pointing_preference_cannot_relax_payload_requirement() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"pointing_precision_preference": "coarse"},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    assert resp.json()["requirements"]["max_pointing_error_deg"] == 0.2


def test_mission_solve_optimization_priority_changes_objective_weights() -> None:
    app = create_app()
    client = TestClient(app)
    base_input = {
        "family": "iot_communication",
        "payload": {"type": "catalog", "payload_id": "IOT-COM-BPT-001"},
        "roi": {"type": "global"},
        "parameters": {"revisit_time_hours": 48, "engineering_preferences": {}},
    }
    low_cost = {
        "input": {
            **base_input,
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"optimization_priority": "lowest_cost"},
            },
        }
    }
    high_perf = {
        "input": {
            **base_input,
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"optimization_priority": "highest_performance"},
            },
        }
    }
    r1 = client.post("/api/v1/mission/solve", json=low_cost)
    r2 = client.post("/api/v1/mission/solve", json=high_perf)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    w1 = r1.json()["engineering_trace"]["solver"]["objective_weights"]
    w2 = r2.json()["engineering_trace"]["solver"]["objective_weights"]
    assert w1["cost"] > w2["cost"]
    assert w2["slack"] > w1["slack"]
    assert any(
        p["preference"] == "optimization_priority"
        for p in r1.json()["engineering_trace"]["preferences"]
    )


def test_mission_solve_propulsion_preference_conflict_is_clear() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"propulsion_preference": "chemical"},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 400
    assert "preferred_propulsion='chemical'" in resp.text


def test_mission_solve_no_propulsion_preference_allowed_when_not_required() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"propulsion_preference": "none"},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200, resp.text
    propulsion = next(
        s for s in resp.json()["solution"]["subsystems"] if s["domain"] == "propulsion"
    )
    assert propulsion["metadata"]["type"] == "none"


def test_mission_solve_no_propulsion_conflict_when_required() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "navigation",
            "payload": {"type": "catalog", "payload_id": "NAV-RF-PNT-001"},
            "roi": {"type": "global"},
            "parameters": {
                "revisit_time_hours": 48,
                "engineering_preferences": {"propulsion_preference": "none"},
            },
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 400
    assert "propulsion_preference='none' conflicts" in resp.text


def test_mission_solve_my_payload_includes_engineering_trace() -> None:
    app = create_app()
    client = TestClient(app)

    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "My Payload",
                "length_mm": 200,
                "width_mm": 120,
                "height_mm": 120,
                "mass_kg": 2.0,
                "avg_power_w": 8.0,
                "peak_power_w": 14.0,
                "data_rate_mbps": 10.0,
                "pointing_accuracy_deg": 0.6,
                "thermal_class": "standard",
            },
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/solve", json=req)
    assert resp.status_code == 200
    body = resp.json()
    assert body["engineering_trace"]["selection"]["payload_source"] == "my_payload"
    assert body["engineering_trace"]["solver"]["route_used"] == "/api/v1/mission/solve"


def test_mission_report_markdown() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    for path in ("/api/v1/mission/report", "/api/v1/mission/report?format=markdown"):
        resp = client.post(path, json=req)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "# Mission Report" in resp.text
        assert "Mission Input" in resp.text
        assert "Platform" in resp.text
        assert "Selected Subsystems" in resp.text
        assert "rs_hyperspec_v1" in resp.text
        assert "Generated:" not in resp.text


def test_mission_report_pdf_format() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    resp = client.post("/api/v1/mission/report?format=pdf", json=req)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.headers["content-disposition"] == "attachment; filename=cubesat-mission-report.pdf"
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 10 * 1024
    assert b"/Subtype /Image" not in resp.content
    json_resp = client.post("/api/v1/mission/report?format=json", json=req)
    assert json_resp.status_code == 200, json_resp.text
    report = json_resp.json()
    text = _pdf_text(resp.content)
    assert "CubeSat Mission Configuration Report" in text
    assert report["report_id"] in text
    assert report["platform"]["selected_platform_name"] in text
    assert "SOLVER STATUS" in text
    assert "Engineering Budgets & Margins" in text
    assert "Warnings, Risk & Data Completeness" in text


def test_mission_report_v1_json_and_html_formats() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "My Camera",
                "length_mm": 200,
                "width_mm": 120,
                "height_mm": 120,
                "mass_kg": 2.0,
                "avg_power_w": 8.0,
                "peak_power_w": 14.0,
                "data_rate_mbps": 10.0,
                "pointing_accuracy_deg": 0.6,
                "thermal_class": "standard",
            },
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }

    json_resp = client.post("/api/v1/mission/report?format=json", json=req)
    assert json_resp.status_code == 200, json_resp.text
    assert json_resp.headers["content-type"].startswith("application/json")
    body = json_resp.json()
    assert body["report_id"].startswith("CFG-")
    assert "mission_summary" in body
    assert "constellation" in body
    assert "payload" in body
    assert "selected_subsystems" in body
    assert "budgets" in body
    assert "margins" in body
    assert body["mission_summary"]["family"] == "remote_sensing"
    assert body["payload"]["name"] == "My Camera"
    assert body["data_budget"]["data_per_day_per_satellite_gb"] == pytest.approx(108.0)
    assert body["payload"]["swath_width_km"] is None
    assert "sections" in body
    assert "mission_inputs" in body
    assert "requirements" in body
    assert "cost_breakdown" in body
    assert "next_engineering_actions" in body
    assert any(w["code"] == "COVERAGE_GEOMETRY_UNAVAILABLE" for w in body["warnings"])
    assert any(w["code"] == "RADIATION_UNAVAILABLE" for w in body["warnings"])
    assert body["subsystems"] == sorted(
        body["subsystems"],
        key=lambda item: {
            "structure": 0,
            "eps": 1,
            "adcs": 2,
            "obc": 3,
            "comm": 4,
            "thermal": 5,
            "propulsion": 6,
            "radiation_support_components": 7,
        }.get(item["domain"], 999),
    )

    html_resp = client.post("/api/v1/mission/report?format=html", json=req)
    assert html_resp.status_code == 200, html_resp.text
    assert html_resp.headers["content-type"].startswith("text/html")
    assert "CubeSat Mission Configuration Report" in html_resp.text
    assert "CubeSat Mission Configurator logo" in html_resp.text
    assert "data:image/png;base64," in html_resp.text
    assert "Remote Sensing" in html_resp.text
    assert "Selected platform" in html_resp.text
    assert "Estimated satellites" in html_resp.text
    assert "Planes" in html_resp.text
    assert "Subsystem Architecture" in html_resp.text
    assert "<table" in html_resp.text
    assert "Radiation screening not available." in html_resp.text
    assert "Next Engineering Actions" in html_resp.text
    assert "coverage geometry is unavailable" in html_resp.text


def test_mission_report_engineering_sections_for_full_catalog_payload() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "RS-EO-HSI-001"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }

    resp = client.post("/api/v1/mission/report?format=json", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    bus_warning = "Bus candidate evaluation failed: Unknown catalog payload_id: RS-EO-HSI-001"
    assert all(warning["message"] != bus_warning for warning in body["warnings"])
    assert body["payload"]["payload_id"] == "RS-EO-HSI-001"
    assert body["payload"]["source"] == "payload catalog"
    assert body["data_budget"]["annual_generated_data_tb"] is not None
    assert body["data_budget"]["provenance"] == "payload catalog"
    assert body["payload"]["swath_width_km"] is not None
    assert body["platform"]["bus_candidates"]
    assert any(c["status"] == "selected" for c in body["platform"]["bus_candidates"])
    assert body["cost_breakdown"]["platform_cost_kusd"] is not None
    assert body["sections"]["solver_trace"]["constraints"]


def test_mission_report_missing_data_generates_engineering_warnings() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "No Data Camera",
                "length_mm": 200,
                "width_mm": 120,
                "height_mm": 120,
                "mass_kg": 2.0,
                "avg_power_w": 8.0,
                "peak_power_w": 14.0,
                "pointing_accuracy_deg": 0.6,
                "thermal_class": "standard",
            },
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/report?format=json", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    warning_codes = {warning["code"] for warning in body["warnings"]}
    assert "ANNUAL_DATA_UNAVAILABLE" in warning_codes
    assert "COVERAGE_GEOMETRY_UNAVAILABLE" in warning_codes
    assert "REQUIRED_STORAGE_UNAVAILABLE" in warning_codes
    assert body["data_budget"]["annual_generated_data_tb"] is None


def test_mission_report_constraints_and_subsystem_reasoning_are_visible() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_vhr_optical_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    resp = client.post("/api/v1/mission/report?format=json", json=req)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    constraint_names = {constraint["name"] for constraint in body["solver"]["constraints"]}
    assert "Mass Budget" in constraint_names
    assert "Average Power Budget" in constraint_names
    assert "Peak Power Budget" in constraint_names
    assert "Payload Volume Budget" in constraint_names
    assert "Downlink Capacity" in constraint_names
    assert "ADCS Pointing" in constraint_names
    assert "Thermal Requirement" in constraint_names
    assert "Storage/Data Requirement" in constraint_names
    for subsystem in body["selected_subsystems"]:
        assert subsystem["mass_kg"] is not None
        assert subsystem["avg_power_w"] is not None
        assert subsystem["peak_power_w"] is not None
        assert subsystem["cost_kusd"] is not None
        assert subsystem["selection_reason"]
    assert all("..." not in assumption for assumption in body["assumptions"])


def test_mission_report_v1_pdf_is_deterministic() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    r1 = client.post("/api/v1/mission/report?format=pdf", json=req)
    r2 = client.post("/api/v1/mission/report?format=pdf", json=req)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.content == r2.content


def test_mission_report_v1_json_is_deterministic_for_same_input() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    r1 = client.post("/api/v1/mission/report?format=json", json=req)
    r2 = client.post("/api/v1/mission/report?format=json", json=req)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    body1 = r1.json()
    body2 = r2.json()
    assert body1["report_id"] == body2["report_id"]
    assert body1["mission_summary"] == body2["mission_summary"]
    assert body1["constellation"] == body2["constellation"]
    assert body1["payload"] == body2["payload"]
    assert body1["selected_subsystems"] == body2["selected_subsystems"]
    assert body1["budgets"] == body2["budgets"]
    assert body1["margins"] == body2["margins"]
    assert "data:image/png;base64," not in r1.text


def test_mission_report_missing_optional_preferences_renders_pdf_and_html() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {"type": "catalog", "payload_id": "rs_hyperspec_v1"},
            "roi": {"type": "global"},
            "parameters": {"revisit_time_hours": 24},
        }
    }
    pdf_resp = client.post("/api/v1/mission/report?format=pdf", json=req)
    html_resp = client.post("/api/v1/mission/report?format=html", json=req)
    assert pdf_resp.status_code == 200, pdf_resp.text
    assert pdf_resp.headers["content-type"].startswith("application/pdf")
    assert pdf_resp.content.startswith(b"%PDF")
    assert html_resp.status_code == 200, html_resp.text
    assert html_resp.headers["content-type"].startswith("text/html")
    assert "CubeSat Mission Configuration Report" in html_resp.text


def test_mission_report_html_escapes_user_strings() -> None:
    app = create_app()
    client = TestClient(app)
    req = {
        "input": {
            "family": "remote_sensing",
            "payload": {
                "type": "my_payload",
                "name": "<script>alert('x')</script>",
                "length_mm": 200,
                "width_mm": 120,
                "height_mm": 120,
                "mass_kg": 2.0,
                "avg_power_w": 8.0,
                "peak_power_w": 14.0,
                "data_rate_mbps": 10.0,
                "pointing_accuracy_deg": 0.6,
                "thermal_class": "standard",
            },
            "roi": {"type": "region", "query": "<b>Moon</b>"},
            "parameters": {"revisit_time_hours": 48},
        }
    }
    resp = client.post("/api/v1/mission/report?format=html", json=req)
    assert resp.status_code == 200, resp.text
    assert "<script>alert" not in resp.text
    assert "&lt;script&gt;alert" in resp.text
    assert "&lt;b&gt;Moon&lt;/b&gt;" in resp.text
