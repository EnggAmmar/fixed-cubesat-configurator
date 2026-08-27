from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

# backend/solver/'s tiers are an abstract LOW/MEDIUM/HIGH/EXTREME capability scale with
# no notion of a named vendor component (see cubesat_engine_adapter.py's module docstring).
# This maps each tier to a *representative* real product from the corresponding
# data_base/Subsystem/MASTER_*.json catalog, purely for display/traceability in the
# engineering trace - it never feeds back into solver decisions or sizing.
_TIER_ORDER = ["LOW", "MEDIUM", "HIGH", "EXTREME"]

_DOMAIN_TO_MASTER_FILE = {
    "eps": "MASTER_EPS.json",
    "adcs": "MASTER_ADCS.json",
    "comm": "MASTER_COMM.json",
    "obc": "MASTER_OBDH.json",
    "thermal": "MASTER_THERMAL.json",
    "propulsion": "MASTER_PROPULSION.json",
}


def _repo_root() -> Path:
    # backend/app/services/<this_file>.py -> services -> app -> backend -> repo_root
    return Path(__file__).resolve().parents[3]


def _product_id(product: dict[str, Any]) -> str | None:
    raw = product.get("item_id", product.get("id"))
    return str(raw) if raw is not None else None


def _product_mass_kg(product: dict[str, Any]) -> float | None:
    normalized = product.get("normalized")
    if not isinstance(normalized, dict):
        return None
    mass = normalized.get("mass_kg")
    return float(mass) if isinstance(mass, (int, float)) else None


def _bucket_representatives(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Ranks products by mass_kg and splits them into 4 mass-ordered buckets, one per
    tier, then picks the median product of each bucket as that tier's representative."""
    ranked = sorted(
        ((p, m) for p in products if (m := _product_mass_kg(p)) is not None),
        key=lambda pair: pair[1],
    )
    if not ranked:
        return {}

    n = len(ranked)
    bucket_count = min(len(_TIER_ORDER), n)
    representatives: dict[str, dict[str, Any]] = {}
    for i, tier in enumerate(_TIER_ORDER[:bucket_count]):
        start = (i * n) // bucket_count
        end = ((i + 1) * n) // bucket_count
        bucket = ranked[start:end]
        median_product, median_mass = bucket[len(bucket) // 2]
        representatives[tier] = {
            "item_id": _product_id(median_product),
            "vendor": median_product.get("vendor"),
            "product_name": median_product.get("product_name"),
            "trl": median_product.get("trl"),
            "mass_kg": median_mass,
        }
    # If fewer real products than tiers exist, the highest-mass product stands in for
    # every tier above the last populated bucket rather than leaving them unmapped.
    for tier in _TIER_ORDER[bucket_count:]:
        representatives[tier] = representatives[_TIER_ORDER[bucket_count - 1]]
    return representatives


@cache
def _load_domain_representatives(domain: str) -> dict[str, dict[str, Any]]:
    filename = _DOMAIN_TO_MASTER_FILE.get(domain)
    if filename is None:
        return {}
    path = _repo_root() / "backend" / "data_base" / "Subsystem" / filename
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    products = raw.get("products")
    if not isinstance(products, list):
        return {}
    return _bucket_representatives(products)


def representative_product(domain: str, tier: str) -> dict[str, Any] | None:
    """Real vendor product (vendor/product_name/TRL/mass) representative of the given
    abstract domain+tier combination, or None if no MASTER_*.json data is available for
    that domain (e.g. "structure", which has no per-tier vendor catalog)."""
    return _load_domain_representatives(domain).get(tier.upper())
