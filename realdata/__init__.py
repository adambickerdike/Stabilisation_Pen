"""realdata: real recorded handwriting and real recorded tremor as simulation inputs (study R, round 4).

Evidence status of what this package produces:
  * LOADERS and LIBRARIES read recordings made by other people (datasets in ``sources.py``, each with its citation,
    licence and what may be redistributed).  Their numbers are MEASUREMENTS BY OTHERS, re-analysed here (CALC).
    Where a dataset gives no physical unit, the calibration used is DERIVED and labelled (``calib.py``).
  * The tremor-only signals are extracted with ZERO-PHASE (non-causal) filters.  That is allowed for simulation
    INPUTS only; no controller or tracker in this package or elsewhere may use them (the trackers see only the
    simulated sensor streams).
  * The headline comparison (``hw1.py``) is a SIMULATION of model HW1 (``handwriting/``, used read-only) driven by
    the real inputs.  Nothing here was measured on the pen or on a person by this project.

Labels used for every number: SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, DATA (a recording made by
others, re-analysed here: always with its dataset key).

Modules
-------
sources      dataset registry: citation, URL, licence, redistribution, files and checksums; download
calib        unit calibrations (manufacturer pixel pitch, gravity sphere fit, documented unit scales)
dsp          resampling, zero-phase band limits, acceleration -> displacement, tremor parameters
loaders      one loader per dataset (tremor: UCI spirals, NewHandPD, Zenodo ET, PADS; writing: BRUSH, UNIPEN,
             UCI Character Trajectories, UJI)
tremorlib    the tremor library: per-recording parameters, severity classes, tremor-only waveforms
reader       a writer-adapted letter reader (the app's reader for real handwriting)
writinglib   the writing library: real words and sentences with timing in HW1 (aiguide Written) and sim2 formats
library      the public API for other studies: tremor(cls, seed), writing(split, seed), hw1_scenario, sim2_scenario
kinematics   validation of real and synthetic writers against the literature (speed, strokes, power law, spectra)
hw1          the headline comparison on real inputs (ordinary pen, Rev H tracker, Rev J + gated tracker, Rev J +
             causal TCN, perfect knowledge), with the synthetic-input factorial that explains the change
figures      figures with CSV twins; the before/after pictures for non-engineers
report       realdata.json, samples.json, evidence_rows.csv
run          python3 -m realdata.run [--quick] [--stages ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                  # git-ignored ("build/" in .gitignore)
RAW_DIR = BUILD_DIR / "raw"                    # raw downloads (never committed)
CACHE_DIR = BUILD_DIR / "cache"                # stage caches (resumable)
RESULTS_DIR = REPO_ROOT / "results" / "realdata"
DOC_PATH = REPO_ROOT / "docs" / "real_data.md"

EVIDENCE_DATA = ("DATA: recordings made by others (dataset key given), re-analysed here (CALC); units as documented "
                 "or DERIVED calibration where labelled")
EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/, used read-only) with REAL recorded inputs: handwriting and "
                "tremor recorded by others; not a measurement of the pen or of any person by this project")
EVIDENCE_CALC = "CALCULATION on recorded data or on simulation output; not a measurement by this project"


def limit_threads(n: int = 1) -> None:
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, str(n))


def ensure_paths() -> None:
    """Repository root and app/ on sys.path; a private numba cache in realdata/build (set before any numba import)."""
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


limit_threads(int(os.environ.get("REALDATA_THREADS", "1")))      # one process, one numerical thread (shared machine)
ensure_paths()
