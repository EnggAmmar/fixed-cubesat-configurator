from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.taxonomy import get_taxonomy


def test_taxonomy_endpoint_contains_expected_families_and_categories() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())
    resp = client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    body = resp.json()

    assert body["version"] == "v1"
    families = {f["family_id"]: f for f in body["families"]}
    assert set(families.keys()) == {"remote_sensing", "iot_communication", "navigation"}

    expected = {
        "remote_sensing": {
            "hyperspectral",
            "infrared_imaging",
            "vhr_optical",
            "thermal",
            "sar",
            "my_payload",
        },
        "iot_communication": {
            "iot_store_and_forward",
            "broadband_rf_comms",
            "optical_laser_comms",
            "quantum_secure_comms",
            "my_payload",
        },
        "navigation": {
            "pnt_augmentation",
            "navigation_beacons",
            "rf_geolocation",
            "timing_payloads",
            "my_payload",
        },
    }

    for fam_id, fam in families.items():
        assert fam["label"]
        assert fam["description"]
        cats = {c["category_id"]: c for c in fam["payload_categories"]}
        assert set(cats.keys()) == expected[fam_id]
        assert "my_payload" in cats
        if fam_id == "remote_sensing":
            assert "multispectral" not in cats
            assert "infrared_imaging" in cats
        if fam_id == "iot_communication":
            assert "broadband_comms" not in cats
            assert "optical_comms" not in cats
            assert "secure_comms" not in cats
            assert "broadband_rf_comms" in cats
            assert "optical_laser_comms" in cats
            assert "quantum_secure_comms" in cats
        if fam_id == "navigation":
            assert "ais_adsb_tracking" not in cats
            assert "rf_navigation_payload" not in cats
            assert "timing_navigation_experiment" not in cats
            assert "navigation_beacons" in cats
            assert "rf_geolocation" in cats
            assert "timing_payloads" in cats
        for cat in cats.values():
            assert cat["label"]
            assert cat["description"]
            assert "payloads" in cat
            assert isinstance(cat["payloads"], list)


def test_taxonomy_payload_grouping_matches_catalog() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())
    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}

    rs = families["remote_sensing"]
    cats = {c["category_id"]: c for c in rs["payload_categories"]}

    hyperspec_payload_ids = {p["payload_id"] for p in cats["hyperspectral"]["payloads"]}
    vhr_payload_ids = {p["payload_id"] for p in cats["vhr_optical"]["payloads"]}

    assert "rs_hyperspec_v1" in hyperspec_payload_ids
    assert "rs_vhr_optical_v1" in vhr_payload_ids

    # Infrared imaging is full-DB backed (not seeded in v1 catalog); it should still exist.
    assert "infrared_imaging" in cats


def test_taxonomy_prefers_full_db_payload_ids_for_frontend_default_selection() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())
    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}
    rs = families["remote_sensing"]
    cats = {c["category_id"]: c for c in rs["payload_categories"]}

    # PayloadPage uses payloads[0] as the selected catalog payload for a category.
    # The first item must therefore be compatible with /api/solve/cubesat diagnostics.
    assert cats["hyperspectral"]["payloads"][0]["payload_id"].startswith("RS-")
    assert cats["vhr_optical"]["payloads"][0]["payload_id"].startswith("RS-")

    # Seeded demo IDs remain available as fallback entries for v1 mission-solver coverage.
    assert any(p["payload_id"] == "rs_hyperspec_v1" for p in cats["hyperspectral"]["payloads"])
    assert any(p["payload_id"] == "rs_vhr_optical_v1" for p in cats["vhr_optical"]["payloads"])


def test_legacy_family_and_category_endpoints_derive_from_taxonomy() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    fam = client.get("/api/v1/mission-families").json()
    assert set(fam["families"]) == {"remote_sensing", "iot_communication", "navigation"}

    cats = client.get("/api/v1/payload-categories", params={"family": "navigation"}).json()
    cat_ids = {c["category_id"] for c in cats["categories"]}
    assert "my_payload" in cat_ids
    assert "pnt_augmentation" in cat_ids
    assert "navigation_beacons" in cat_ids
    assert "rf_geolocation" in cat_ids
    assert "timing_payloads" in cat_ids


def test_taxonomy_full_db_populates_thermal_and_sar_categories() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}
    rs = families["remote_sensing"]
    cats = {c["category_id"]: c for c in rs["payload_categories"]}

    thermal_ids = {p["payload_id"] for p in cats["thermal"]["payloads"]}
    sar_ids = {p["payload_id"] for p in cats["sar"]["payloads"]}
    ir_ids = {p["payload_id"] for p in cats["infrared_imaging"]["payloads"]}

    assert thermal_ids, "Expected full DB mapping to provide thermal payload options."
    assert sar_ids, "Expected full DB mapping to provide SAR payload options."
    assert ir_ids, "Expected full DB mapping to provide infrared imaging payload options."

    # These should come from the full payload DB (Remote Sensing master DB uses RS-* ids).
    assert any(pid.startswith("RS-") for pid in thermal_ids)
    assert any(pid.startswith("RS-") for pid in sar_ids)
    assert any(pid.startswith("RS-EO-NIR-") or pid.startswith("RS-EO-SWIR-") for pid in ir_ids)

    # Infrared imaging replaces the old multispectral category and should be populated.
    assert "multispectral" not in cats


def test_taxonomy_full_db_populates_iot_communication_categories() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}
    iot = families["iot_communication"]
    cats = {c["category_id"]: c for c in iot["payload_categories"]}

    sof_ids = {p["payload_id"] for p in cats["iot_store_and_forward"]["payloads"]}
    rf_ids = {p["payload_id"] for p in cats["broadband_rf_comms"]["payloads"]}
    optical_ids = {p["payload_id"] for p in cats["optical_laser_comms"]["payloads"]}
    quantum_ids = {p["payload_id"] for p in cats["quantum_secure_comms"]["payloads"]}

    assert sof_ids, "Expected full DB mapping to provide IoT store-and-forward payload options."
    assert rf_ids, "Expected full DB mapping to provide broadband RF payload options."
    assert optical_ids, "Expected full DB mapping to provide optical/laser comms payload options."
    assert quantum_ids, "Expected full DB mapping to provide quantum secure comms payload options."

    assert any(pid.startswith("IOT-COM-BPT-") or pid.startswith("IOT-COM-RGT-") for pid in sof_ids)
    assert any(
        pid.startswith("IOT-COM-SDT-")
        or pid.startswith("IOT-COM-TX-")
        or pid.startswith("IOT-COM-RX-")
        or pid.startswith("IOT-COM-SP-")
        for pid in rf_ids
    )
    assert any(
        pid.startswith("IOT-COM-LCT-") or pid.startswith("IOT-COM-OL-") for pid in optical_ids
    )
    assert any(pid.startswith("IOT-COM-QC-") for pid in quantum_ids)


def test_taxonomy_full_db_populates_navigation_categories() -> None:
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}
    nav = families["navigation"]
    cats = {c["category_id"]: c for c in nav["payload_categories"]}

    pnt_ids = {p["payload_id"] for p in cats["pnt_augmentation"]["payloads"]}
    beacon_ids = {p["payload_id"] for p in cats["navigation_beacons"]["payloads"]}
    geo_ids = {p["payload_id"] for p in cats["rf_geolocation"]["payloads"]}
    timing_ids = {p["payload_id"] for p in cats["timing_payloads"]["payloads"]}

    assert pnt_ids, "Expected full DB mapping to provide PNT augmentation payload options."
    assert beacon_ids, "Expected full DB mapping to provide navigation beacon payload options."
    assert geo_ids, "Expected full DB mapping to provide RF geolocation payload options."
    assert timing_ids, "Expected full DB mapping to provide timing payload options."

    assert any(pid.startswith("NAV-RF-PNT-") for pid in pnt_ids)
    assert any(pid.startswith("NAV-RF-BEACON-") for pid in beacon_ids)
    assert any(pid.startswith("NAV-RF-TIME-") for pid in timing_ids)
    assert any(pid.startswith("NAV-DEF-DFA-") or pid.startswith("NAV-DEF-RFSL-") for pid in geo_ids)


def test_taxonomy_falls_back_to_seeded_catalog_when_full_db_disabled(monkeypatch) -> None:
    # Patch the imported function reference inside app.services.taxonomy (not the defining module),
    # then confirm seeded v1 payload IDs still appear.
    get_taxonomy.cache_clear()
    import app.services.taxonomy as taxonomy_mod

    def _no_full_db(*args, **kwargs):  # type: ignore[no-untyped-def]
        return []

    monkeypatch.setattr(taxonomy_mod, "list_payload_options_for_category", _no_full_db)

    client = TestClient(create_app())
    body = client.get("/api/v1/taxonomy").json()
    families = {f["family_id"]: f for f in body["families"]}
    rs = families["remote_sensing"]
    cats = {c["category_id"]: c for c in rs["payload_categories"]}

    hyperspec_payload_ids = {p["payload_id"] for p in cats["hyperspectral"]["payloads"]}
    vhr_payload_ids = {p["payload_id"] for p in cats["vhr_optical"]["payloads"]}

    assert "rs_hyperspec_v1" in hyperspec_payload_ids
    assert "rs_vhr_optical_v1" in vhr_payload_ids
