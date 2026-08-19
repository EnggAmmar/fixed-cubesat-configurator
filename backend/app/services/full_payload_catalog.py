from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FullDbPayloadOption:
    payload_id: str
    label: str
    source: str
    payload_variant: str
    payload_type: str
    payload_group: str
    mission_family: str


def _app_root() -> Path:
    # backend/app/services/<this_file>.py -> backend/app/services -> backend/app
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    # backend/app/services/<this_file>.py -> backend/app -> backend -> repo_root
    return Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict JSON at {path}, got {type(raw).__name__}")
    return raw


def _mapping_path() -> Path:
    return _app_root() / "data" / "payload_category_mapping.json"


@lru_cache(maxsize=1)
def load_payload_category_mapping() -> dict[str, Any]:
    return _load_json(_mapping_path())


def _master_db_paths() -> dict[str, Path]:
    root = _repo_root()
    return {
        "remote_sensing": (
            root / "backend" / "data_base" / "Remote_Sensing" / "MASTER_Remote_Sensing.json"
        ),
        "iot_communication": root / "backend" / "data_base" / "IoT_Comm" / "MASTER_IoT_Comm.json",
        "navigation": root / "backend" / "data_base" / "Navigation" / "MASTER_Navigation.json",
    }


@lru_cache(maxsize=1)
def _load_master_db(family_id: str) -> dict[str, Any]:
    paths = _master_db_paths()
    path = paths.get(family_id)
    if not path:
        raise ValueError(f"Unknown family_id for master DB: {family_id}")
    return _load_json(path)


def _iter_variant_products(
    master_db: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    """
    Yield (variant, product) tuples from a MASTER_*.json file.
    """
    variants = master_db.get("variants", [])
    if not isinstance(variants, list):
        return
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        products = variant.get("products", [])
        if not isinstance(products, list):
            continue
        for product in products:
            if not isinstance(product, dict):
                continue
            yield (variant, product)


def _product_label(product: dict[str, Any]) -> str:
    name = str(product.get("product_name") or "").strip()
    vendor = str(product.get("vendor") or "").strip()
    if name and vendor:
        return f"{name} ({vendor})"
    if name:
        return name
    payload_id = str(product.get("payload_id") or "").strip()
    return payload_id or "Unknown payload"


def list_payload_options_for_category(
    family_id: str,
    category_id: str,
) -> list[FullDbPayloadOption]:
    """
    List lightweight payload options from the full MASTER_* databases, using
    `backend/app/data/payload_category_mapping.json` to map category_id -> payload_variant(s).

    This is listing/availability only; it does not run CP-SAT or mission solves.
    """
    mapping = load_payload_category_mapping()
    families = mapping.get("families", {})
    fam_map = families.get(family_id, {})
    cat_map = fam_map.get(category_id, {})

    status = str(cat_map.get("status") or "").strip()
    if status in ("manual_frontend", "missing_explicit_db_variant"):
        return []

    wanted_variants = cat_map.get("payload_variants", [])
    if not isinstance(wanted_variants, list) or not wanted_variants:
        return []

    master_db = _load_master_db(family_id)
    mission_family = str(master_db.get("mission_family") or family_id)

    out: list[FullDbPayloadOption] = []
    for variant, product in _iter_variant_products(master_db):
        payload_variant = str(variant.get("payload_variant") or "")
        if payload_variant not in wanted_variants:
            continue
        payload_id = str(product.get("payload_id") or "").strip()
        if not payload_id:
            continue

        out.append(
            FullDbPayloadOption(
                payload_id=payload_id,
                label=_product_label(product),
                source="full_db",
                payload_variant=payload_variant,
                payload_type=str(variant.get("payload_type") or ""),
                payload_group=str(variant.get("payload_group") or ""),
                mission_family=mission_family,
            )
        )

    # Stable ordering for determinism (tests + UI predictability).
    out.sort(key=lambda p: (p.payload_variant, p.payload_id))
    return out
