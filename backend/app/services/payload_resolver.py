from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.catalog import Catalog, CatalogPayload


def _repo_root() -> Path:
    # backend/app/services/<this_file>.py -> backend/app/services -> backend/app
    # -> backend -> repo_root
    return Path(__file__).resolve().parents[3]


def _master_db_paths() -> dict[str, Path]:
    root = _repo_root()
    return {
        "remote_sensing": (
            root / "backend" / "data_base" / "Remote_Sensing" / "MASTER_Remote_Sensing.json"
        ),
        "iot_communication": root / "backend" / "data_base" / "IoT_Comm" / "MASTER_IoT_Comm.json",
        "navigation": root / "backend" / "data_base" / "Navigation" / "MASTER_Navigation.json",
    }


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict JSON at {path}, got {type(raw).__name__}")
    return raw


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _required_float(value: Any, *, field: str, payload_id: str) -> float:
    out = _as_float(value)
    if out is None:
        raise ValueError(f"Payload {payload_id} missing required numeric field: {field}")
    return out


def _product_label(product: dict[str, Any], payload_id: str) -> str:
    name = str(product.get("product_name") or "").strip()
    return name or payload_id


@lru_cache(maxsize=1)
def _full_db_payload_index() -> dict[str, tuple[str, dict[str, Any]]]:
    """
    Index payload_id -> (family_id, product) across MASTER_* databases.
    """
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for family_id, path in _master_db_paths().items():
        master = _load_json(path)
        variants = master.get("variants", [])
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            products = variant.get("products", [])
            if not isinstance(products, list):
                continue
            for product in products:
                if not isinstance(product, dict):
                    continue
                pid = str(product.get("payload_id") or "").strip()
                if not pid:
                    continue
                index.setdefault(pid, (family_id, product))
    return index


def _normalize_full_db_product(
    payload_id: str, family_id: str, product: dict[str, Any]
) -> CatalogPayload:
    dims = product.get("dimensions_mm") or {}
    if not isinstance(dims, dict):
        dims = {}

    length_mm = _required_float(
        dims.get("length_mm"), field="dimensions_mm.length_mm", payload_id=payload_id
    )
    width_mm = _required_float(
        dims.get("width_mm"), field="dimensions_mm.width_mm", payload_id=payload_id
    )
    height_mm = _required_float(
        dims.get("height_mm"), field="dimensions_mm.height_mm", payload_id=payload_id
    )

    mass_kg = _required_float(product.get("mass_kg"), field="mass_kg", payload_id=payload_id)
    avg_power_w = _required_float(
        product.get("avg_power_w"), field="avg_power_w", payload_id=payload_id
    )
    peak_power_w = _required_float(
        product.get("peak_power_w"), field="peak_power_w", payload_id=payload_id
    )

    data_rate_mbps = _as_float(product.get("nominal_data_rate_mbps"))
    pointing_accuracy_deg = _as_float(product.get("pointing_requirement_deg"))

    stability = str(product.get("temperature_stability_requirement") or "").strip().lower()
    thermal_class = "sensitive" if stability == "high" else "standard"

    return CatalogPayload(
        payload_id=payload_id,
        family=family_id,
        category_id="full_db",
        label=_product_label(product, payload_id),
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        mass_kg=mass_kg,
        avg_power_w=avg_power_w,
        peak_power_w=peak_power_w,
        data_rate_mbps=data_rate_mbps,
        pointing_accuracy_deg=pointing_accuracy_deg,
        thermal_class=thermal_class,
    )


def resolve_payload_for_requirements(payload_id: str, catalog: Catalog) -> CatalogPayload | None:
    """
    Resolve a payload into the existing `CatalogPayload` shape used by requirement derivation.

    Resolution order:
    1) Seeded catalog.json payloads
    2) Full MASTER_* databases (Remote Sensing / IoT Comm / Navigation)
    """
    seeded = catalog.get_payload(payload_id)
    if seeded:
        return seeded

    hit = _full_db_payload_index().get(payload_id)
    if not hit:
        return None
    family_id, product = hit
    return _normalize_full_db_product(payload_id, family_id, product)
