from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.mission import PayloadCategory


@dataclass(frozen=True)
class CatalogPayload:
    payload_id: str
    family: str
    category_id: str
    label: str
    length_mm: float
    width_mm: float
    height_mm: float
    mass_kg: float
    avg_power_w: float
    peak_power_w: float
    data_rate_mbps: float | None
    pointing_accuracy_deg: float | None
    thermal_class: str | None


@dataclass(frozen=True)
class CatalogSubsystem:
    domain: str
    item_id: str
    name: str
    mass_kg: float
    avg_power_w: float
    peak_power_w: float
    cost_kusd: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CatalogPlatform:
    item_id: str
    name: str
    bus_size_u: float
    max_total_mass_kg: float
    max_payload_volume_cm3: float
    avg_power_gen_w: float
    peak_power_gen_w: float
    cost_kusd: float
    metadata: dict[str, Any]


class Catalog:
    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

        self._families = raw.get("mission_families", {})
        self._payloads = [
            CatalogPayload(**p)
            for p in raw.get("payloads", [])  # type: ignore[arg-type]
        ]
        self._platforms = [
            CatalogPlatform(**p)
            for p in raw.get("platforms", [])  # type: ignore[arg-type]
        ]
        self._subsystems_by_domain: dict[str, list[CatalogSubsystem]] = {}
        for domain, items in raw.get("subsystems", {}).items():
            self._subsystems_by_domain[domain] = [
                CatalogSubsystem(domain=domain, **it)  # type: ignore[arg-type]
                for it in items
            ]

    def list_mission_families(self) -> list[str]:
        return list(self._families.keys())

    def list_payload_categories(self, family: str) -> list[PayloadCategory]:
        family_meta = self._families.get(family)
        if not family_meta:
            return []
        cats = family_meta.get("payload_categories", [])
        return [PayloadCategory(**c) for c in cats]

    def get_payload(self, payload_id: str) -> CatalogPayload | None:
        for p in self._payloads:
            if p.payload_id == payload_id:
                return p
        return None

    def iter_platforms(self) -> Iterable[CatalogPlatform]:
        return list(self._platforms)

    def iter_subsystems(self, domain: str) -> Iterable[CatalogSubsystem]:
        return list(self._subsystems_by_domain.get(domain, []))

    def list_payloads(self, family: str, category_id: str) -> list[CatalogPayload]:
        return [p for p in self._payloads if p.family == family and p.category_id == category_id]


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    data_path = Path(__file__).resolve().parents[1] / "data" / "catalog.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return Catalog(raw)
