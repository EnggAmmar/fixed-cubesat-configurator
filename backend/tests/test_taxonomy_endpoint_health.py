from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.taxonomy import get_taxonomy


def test_taxonomy_endpoint_health_shape() -> None:
    # Ensure the endpoint always returns a non-empty, frontend-compatible shape.
    # The frontend payload card grid depends on `families[].payload_categories[]`.
    get_taxonomy.cache_clear()
    client = TestClient(create_app())

    resp = client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body.get("families"), list)
    assert len(body["families"]) == 3

    families = {f.get("family_id"): f for f in body["families"]}
    assert set(families.keys()) == {"remote_sensing", "iot_communication", "navigation"}

    for fam_id, fam in families.items():
        assert fam.get("label")
        assert fam.get("description")
        cats = fam.get("payload_categories")
        assert isinstance(cats, list)
        assert cats, f"Expected non-empty payload_categories for {fam_id}"
        for cat in cats:
            assert isinstance(cat, dict)
            assert cat.get("category_id")
            assert cat.get("label")
            assert cat.get("description")
            assert "payloads" in cat
            assert isinstance(cat["payloads"], list)

    # Remote sensing is the main UI flow; ensure it has at least the expected core cards.
    rs_cats = families["remote_sensing"]["payload_categories"]
    assert len(rs_cats) >= 5
