from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.radiation import RadiationComponent, RadiationDatabase


def _db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "radiation_db.json"


@lru_cache(maxsize=1)
def get_radiation_db() -> RadiationDatabase:
    raw = json.loads(_db_path().read_text(encoding="utf-8"))
    return RadiationDatabase.model_validate(raw)


@lru_cache(maxsize=1)
def radiation_index_by_component_id() -> dict[str, RadiationComponent]:
    db = get_radiation_db()
    idx: dict[str, RadiationComponent] = {}
    for c in db.components:
        if c.component_id:
            idx[c.component_id] = c
    return idx
