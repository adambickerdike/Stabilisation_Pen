"""nose2 tests: repository root and app/ on sys.path; numba cache in nose2/build (git-ignored)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "app")):
    if p not in sys.path:
        sys.path.insert(0, p)

import nose2  # noqa: E402,F401  (sets NUMBA_CACHE_DIR if unset)
