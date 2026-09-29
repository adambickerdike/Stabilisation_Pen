"""ai2 tests: repository root and app/ on sys.path; one numerical thread; numba cache in ai2/build (git-ignored)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai2  # noqa: E402,F401  (sets the numba cache and the thread limits before numpy-heavy imports)
