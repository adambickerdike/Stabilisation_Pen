"""ai3: spelling, prediction and clearer handwriting for the Rev J pen (study S, round 4).

Evidence status of everything this package produces (every number carries one of these labels):
  SIM         an executed simulation (model HW1 of handwriting/ or HW1-D of drive/, used read-only; or the
              study's own writer-response simulation of the physical spell checker)
  CALC        a calculation on real public data (UJI Pen Characters v2, UCI Character Trajectories, the Birkbeck
              and Holbrook misspelling corpora, CC0 text, public-domain journals) or on simulation output
  LIT         published literature, with a ledger id (proposed rows in results/ai3/evidence_rows.csv)
  ASSUMPTION  an input nobody has measured (writer responses to cues, costs, rates)
Nothing here was measured on a pen or on a person.

Tasks (docs/spelling_and_clarity.md):
  1  online letter recognition while writing      online.py, stage_online.py
  2  physical spell checker                       spell.py, stage_spell.py, cues.py
  3  text prediction v2 (personalisation)          predict.py, stage_predict.py
  4  clearer handwriting (tracing diagnosis, shape assist, clean copy)
                                                  tracing_diag.py, shape.py, stage_shape.py
  5  optimisation on tuning data with rules fixed before testing           rules.py
  report: figures with CSV twins, ai3.json, samples, proposed ledger rows  report.py, evidence.py

Data discipline (fixed before any test result was computed; see rules.py):
  online recogniser   UJI v2 writers: 'trn' writers split into training and tuning (validation) writers;
                      the 20 'tst' writers only for the final tables; Character Trajectories (another writer and
                      device) only as a final cross-dataset test
  spelling            Birkbeck pairs split by target word (hash); Holbrook passages split by child (hash)
  prediction          journals split into an adaptation history and a held-out part per journal; tuning journals
                      and test journals disjoint
  shape assist        UJI tuning writers for every choice; UJI test writers for the tables
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored (".gitignore: build/")
RAW_DIR = BUILD_DIR / "raw"                        # raw downloads (git-ignored)
RESULTS_DIR = REPO_ROOT / "results" / "ai3"

EVIDENCE_SIM = ("SIMULATION (model HW1/HW1-D used read-only, or the study's writer-response simulation; real public "
                "handwriting and misspelling data where stated; not a measurement)")
EVIDENCE_CALC = "CALCULATION (on real public data or on simulation output; not a measurement)"


def ensure_paths() -> None:
    """Repository root and app/ on sys.path; a private numba cache in ai3/build (set before any numba import, so the
    read-only packages never write their numba caches next to their sources)."""
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


def limit_threads(n: int = 1) -> None:
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, str(n))


limit_threads(int(os.environ.get("AI3_THREADS", "1")))     # one numerical thread (shared machine)
ensure_paths()
