from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.taxonomy import CatalogPayloadOption, TaxonomyResponse
from app.services.catalog import get_catalog
from app.services.full_payload_catalog import list_payload_options_for_category


def _taxonomy_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "taxonomy.json"


def _load_taxonomy_base() -> TaxonomyResponse:
    raw = json.loads(_taxonomy_path().read_text(encoding="utf-8"))
    return TaxonomyResponse.model_validate(raw)


@lru_cache(maxsize=1)
def get_taxonomy() -> TaxonomyResponse:
    base = _load_taxonomy_base()
    catalog = get_catalog()

    enriched_families = []
    for fam in base.families:
        enriched_categories = []
        for cat in fam.payload_categories:
            seeded_payloads = [
                CatalogPayloadOption(payload_id=p.payload_id, label=p.label)
                for p in catalog.list_payloads(
                    family=fam.family_id.value, category_id=cat.category_id
                )
            ]

            full_db_payloads = [
                CatalogPayloadOption(payload_id=p.payload_id, label=p.label)
                for p in list_payload_options_for_category(
                    family_id=fam.family_id.value, category_id=cat.category_id
                )
            ]

            # Prefer full MASTER_* database payload IDs when available.
            # The frontend currently selects the first payload for each category,
            # and the CP-SAT diagnostic endpoint is backed by the MASTER_* data
            # loader/precompute set. Keeping full-db IDs first prevents the UI
            # from auto-selecting seeded demo IDs such as `rs_hyperspec_v1`,
            # which are valid for the v1 mission solver but unknown to the
            # diagnostic solver. Seeded payloads are still preserved as fallback
            # entries so existing v1 demos and tests remain available.
            if full_db_payloads:
                seen: set[str] = set()
                merged: list[CatalogPayloadOption] = []
                for p in full_db_payloads + seeded_payloads:
                    if p.payload_id in seen:
                        continue
                    seen.add(p.payload_id)
                    merged.append(p)
                payloads = merged
            else:
                payloads = seeded_payloads
            enriched_categories.append(cat.model_copy(update={"payloads": payloads}))
        enriched_families.append(fam.model_copy(update={"payload_categories": enriched_categories}))

    return base.model_copy(update={"families": enriched_families})
