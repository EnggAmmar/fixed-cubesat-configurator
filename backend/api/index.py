from __future__ import annotations

import sys
from pathlib import Path

# Vercel's Python runtime invokes this file directly, so `backend/` (the parent of
# this api/ directory) isn't guaranteed to be on sys.path the way `--app-dir backend`
# makes it for local uvicorn runs. Add it explicitly before importing the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import create_app  # noqa: E402

app = create_app()
