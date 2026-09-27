"""aiguide tests: repository root and app/ on sys.path; numba cache kept out of sim/."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "app")):
    if p not in sys.path:
        sys.path.insert(0, p)

import aiguide  # noqa: E402

aiguide.use_private_numba_cache()
