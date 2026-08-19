from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

BRANDING_DIR = Path(__file__).resolve().parents[1] / "assets" / "branding"
FULL_LOGO = BRANDING_DIR / "cubesat-logo-full.png"
SMALL_LOGO = BRANDING_DIR / "cubesat-logo-small.png"


def get_branding_logo_path(*, small: bool = False) -> Path | None:
    path = SMALL_LOGO if small else FULL_LOGO
    return path if path.exists() else None


@lru_cache(maxsize=2)
def branding_logo_data_uri(*, small: bool = False) -> str | None:
    path = get_branding_logo_path(small=small)
    if path is None:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
