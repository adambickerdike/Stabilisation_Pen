"""realtrack: causal tremor estimators for the Rev J nose, tuned and tested on REAL recorded inputs (study E, round 4).

Question: can a causal tremor estimator, small enough for the pen's microcontroller, make real tremor-affected writing
more readable while leaving clean real writing alone?  Everything is evaluated in model HW1 (handwriting/, read-only)
with study R's real-input library (realdata/, read-only): real handwriting (UNIPEN hpb2), real Parkinson's tip tremor
(UCI spirals) and real essential tremor (Zenodo ET), the DeltaPen-class page sensor, held-out test writers, texts and
patients, and the literal handwriting reader (TrOCR base).

Evidence labels used for every number: SIM (a simulation run), CALC (a calculation), DATA (recordings made by others,
re-analysed), LIT (ledger id), MFR, ASSUMPTION, PROPOSED DESIGN.  Nothing here was measured on a person or on hardware.

Data discipline (fixed before any test case ran): every choice (estimator family, parameters, gates, training, the
chosen design) is made on study R's TUNING split (5 tuning writers, tuning texts, tuning patients); the choice is frozen
(results/realtrack/frozen.json, with its time); the TEST split (9 test writers, test texts, test patients) is run once.

Modules
-------
cases       tuning and test cases: real notes (Rev J and the ordinary pen), real tremor draws, the nose-held run, its
            sensor streams (ideal and DeltaPen-class page sensor), the true handle tremor; a compact on-disk cache
servo       the Rev J servo path as a linear surrogate (command -> tip), its measured lag, and the fast tip-tremor measure
estimators  causal estimators (numba, tick by tick): the ported G4 guarded tracker, soft-gated listening AKF, WFLC,
            BMFLC, BMFLC with a Kalman filter, adaptive oscillator / enhanced PLL, multi-harmonic Kalman tracker; the
            authority (soft confidence) and the delay handling
learned     a small causal network (TCN / GRU, <= 50 k parameters, int8-friendly) trained on composed real writing
            (tuning writers) + real tremor (tuning patients); cross-fitted by writer and patient for selection
tune        the tuning protocol (rules written before the runs), the searches and the freeze
delay       the actuator and servo lag, and the horizon sweep ('does prediction remove the Rev H worsening?')
test        the one test run on R's test split with R's measures and results cards
mcu         MCU cost per 1 kHz step of the chosen design (CALC, nRF54L15 / nRF5340 class)
sim2check   one small confirmation in the physics simulator sim2 (sim2j's ET grid), if time allows
figures     figures with CSV twins and the before/after pictures (CC BY letters and tremor only)
report      results/realtrack/*.json with stabpen.provenance, evidence_rows.csv
run         python3 -m realtrack.run [--quick] [--stages ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                     # git-ignored ("build/" in .gitignore)
CACHE_DIR = BUILD_DIR / "cache"
RESULTS_DIR = REPO_ROOT / "results" / "realtrack"
DOC_PATH = REPO_ROOT / "docs" / "real_tracker.md"

EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/, used read-only) with REAL recorded inputs (study R's library): "
                "handwriting and tremor recorded by others; not a measurement of the pen or of any person")
EVIDENCE_CALC = "CALCULATION on simulation output or on recorded data; not a measurement by this project"


def _env() -> None:
    """One process, one numerical thread (shared machine); a private numba cache in realtrack/build (set BEFORE any
    numba import, so realdata's default cache folder is never written); the reader's model files are read offline."""
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, os.environ.get("REALTRACK_THREADS", "1"))
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


_env()
