"""realdata tests: repository root and app/ on sys.path; numba cache kept in realdata/build (git-ignored)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "app")):
    if p not in sys.path:
        sys.path.insert(0, p)

import realdata  # noqa: E402,F401  (sets NUMBA_CACHE_DIR if unset)
