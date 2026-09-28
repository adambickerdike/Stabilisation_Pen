"""aiprior: does AI letter prediction close the gap between Rev H's causal tremor tracker and perfect knowledge?

Evidence status: every number this package produces is a SIMULATION (model HW1 of ``handwriting/``, used read-only)
or a CALCULATION on synthetic writers (aiguide glyph-font writers) with synthetic tremor.  Nothing was measured on a
person or on hardware.

Three kinds of help are compared on the same writer, sentence and tremor:

  A(i)   AI prior       the app's predicted letters, drawn in the writer's style, enter the tremor tracker as a
                        template prior (fusion.context "ctx": tremor-referenced cross-track pseudo-measurement,
                        confidence-scaled noise, innovation gate, persistent-mismatch drop rule T5).  The template
                        never commands the nose: the nose still cancels only the estimated tremor.
  A(ii)  AI guidance    partial guidance of the nose toward the predicted template, on top of the tracker, with
                        authority = confidence gate x tremor-amplitude gate x capture gate, a per-letter drop rule
                        and the nose's own travel limit (guide.py).
  B      clean copy     non-causal digital clean-up of the recorded tip path in the app (cleancopy.py).  Digital
                        only: the ink on the paper is what the causal pen wrote.

Modules
-------
core        writer set-up, scenarios, sensor streams, tracker, oracle, templates (the app's AI), closed-loop runs
guide       A(ii): the causal guidance command from the pen's own sensor streams
cleancopy   B: zero-phase band-stop, non-causal Wiener smoother and the clean copy's metrics
study       every variant on one (writer, frequency, amplitude, seed) scenario, with the metrics
tuning      candidate settings and the selection rules (fixed before any test run), on tuning data only
report      figures (+ CSV twins), aiprior.json, samples.json, proposed ledger rows
run_study   one command: python3 -m aiprior.run_study [--quick]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored (".gitignore: build/")
RESULTS_DIR = REPO_ROOT / "results" / "aiprior"

EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/; synthetic glyph writers, synthetic tremor, "
                "Tatoeba-CC0 text predictor; not a measurement)")
EVIDENCE_CALC = "CALCULATION (on synthetic data; not a measurement)"

# Seed conventions (no test leakage): tuning on aiguide writers >= 100 and seeds >= 300; final numbers on aiguide test
# writers 0-5 and seeds 200-203 (the handwriting study's convention).
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301)
F0S = (6.0, 8.0, 10.0)
AMPS = (0.3e-3, 1.0e-3, 2.0e-3)


def ensure_paths() -> None:
    """Repository root and app/ on sys.path; a private numba cache (never written into another package's build/)."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
