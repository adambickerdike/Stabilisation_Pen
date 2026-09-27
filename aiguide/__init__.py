"""aiguide: AI prediction for physical micro-guidance and digital autocorrect.

Evidence status: every number this package produces is a CALCULATION or a
SIMULATION on SYNTHETIC handwriting (glyph-font writers, synthetic tremor) and
on a public-domain text corpus (Tatoeba English sentences released under
CC0 1.0).  No person was recorded; nothing here is a measurement.

The physics bound shapes the whole package: the nib stage can move the ink by
at most its usable travel (0.30 mm in the pencil concept, 0.55 mm in Rev A)
while letters are 2-4 mm tall, so the pen can only nudge strokes toward a
predicted template; it cannot turn one letter or word into another.  Digital
correction in the app is unbounded, and it never overwrites the original ink.

Modules
-------
corpus          public-domain corpus: provenance, normalisation to the glyph alphabet, splits
lm              character Kneser-Ney n-gram + word Kneser-Ney model, calibrated predictor
adapter         predictor protocol, local n-gram adapter, large-model adapter specification
glyphs          single-line glyph font (from app/penapp/synth.py) and geometry helpers
writer          synthetic writers: style, allographs, timing, micrographia
style           online style estimation from written letters (affine fit, exemplars)
template        style-conditioned template synthesis, placement, confidence
stroke_predict  on-device stroke continuation (kinematic and a small MLP), MAC budget
metrics         path distance, DTW legibility proxy, template-matching recogniser
guidance        closed-loop runs of the unmodified M1 simulator with templates
icd_template    proposed ICD record 0x06 (template segment), BLE bandwidth
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
DATA_DIR = PKG_DIR / "data"
BUILD_DIR = PKG_DIR / "build"            # git-ignored (".gitignore: build/"): caches only
RESULTS_DIR = REPO_ROOT / "results" / "ai"

EVIDENCE_SIM = "SIMULATION (synthetic glyph writers and synthetic tremor; model M1 unmodified; not a measurement)"
EVIDENCE_CALC = "CALCULATION (on synthetic data or public-domain text; not a measurement)"


def ensure_paths() -> None:
    """Put the repository root and app/ on sys.path (stabpen, sim, penapp)."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


def use_private_numba_cache() -> None:
    """Keep numba's cache for the simulator core out of sim/ (other agents run it)."""
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
