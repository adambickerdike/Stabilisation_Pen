"""handwriting: what the pen can and cannot do for real handwriting (study HW1).

Evidence status: every number this package produces is a CALCULATION or a
SIMULATION on SYNTHETIC handwriting (aiguide glyph-font writers) with
SYNTHETIC tremor, micrographia and writing errors.  Nothing was measured on a
person or on hardware.  Literature values carry their ledger ids
(docs/evidence.csv, proposed rows in results/handwriting/evidence_rows.csv).

Model HW1 ("hand-pen-paper, one model, swappable tips")
  * hand: HAP-26 impedance as in models M1/P1/H1 (imposed path + passive
    hand-mass perturbation, grip spring and damper at the tip);
  * writer: compensates the paper drag (nominal ASSUMPTION, so a healthy
    writer's ink matches the intended letters); the P1 open-loop convention
    is kept as a sensitivity case;
  * pens: an ordinary pen, a weighted pen, the pencil Rev P0 (+-0.3 mm nib
    stage) and Rev H (active nose, +-3 mm), each a tip module with travel,
    servo bandwidth, latency, slew and force limits;
  * sensing for the tremor tracker: fusion/ sensor models (IMU + page sensor)
    on the simulated handle motion, and the shipped AKF of opt/tracker;
  * optional guidance board: a force field on the nose magnet.

Modules
-------
params      device, hand and board parameters with their evidence labels
plant       HW1 numerical core (numba) and run()
writers     synthetic writers for ET, PD (micrographia) and practice (errors)
tracker     fusion sensor streams + AKF for HW1 runs
metrics     ink error, recognition, readability, size, fluency, authorship
et_study    task 2: ET tremor before/after
pd_study    task 3: PD micrographia before/after
practice    task 4: guided practice and spelling
primer      task 1: primer figures
figures     before/after panels on lined paper at true scale (+ CSV twins)
samples     samples.json for the 3-D explainer page
evidence    proposed ledger rows (results/handwriting/evidence_rows.csv)
run_study   one command: python3 -m handwriting.run_study [--quick]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored (".gitignore: build/")
RESULTS_DIR = REPO_ROOT / "results" / "handwriting"

EVIDENCE_SIM = "SIMULATION (model HW1; synthetic glyph writers, synthetic tremor; not a measurement)"
EVIDENCE_CALC = "CALCULATION (analytic or on synthetic data; not a measurement)"

# Seed conventions (no test leakage): tuning on aiguide writers >= 100 and seeds >= 300; final numbers on
# aiguide test writers 0-5 and seeds 200-203.
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103, 104, 105)
TUNE_SEEDS = (300, 301, 302, 303)


def ensure_paths() -> None:
    """Repository root and app/ on sys.path (stabpen, sim, fusion, aiguide, penapp); a private numba cache."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
