"""platen: a moving-paper XY platen as an alternative to the handheld nib (study P, the active writing surface).

The idea: the paper moves under a pen the user holds, so the relative motion between ink and paper is created
without pushing the hand; the reaction goes into the desk.  The platen can counter tremor by moving the page with the
pen tip, and it can write accepted strokes while the user simply holds the pen down.

Everything here is PROPOSED DESIGN, CALCULATION or SIMULATION.  Nothing was built and nothing was measured on a
person or on hardware.  Evidence labels used on every number: CALCULATION, SIMULATION (the model and its inputs are
named), PROPOSED DESIGN, MANUFACTURER, LITERATURE, ASSUMPTION.

Reused read-only: model HW1 (handwriting/), study R's real-input library and reader (realdata/), study E's tuning
cases, estimators and frozen designs (realtrack/), study F's frozen words curve and reach results (readable/,
results/readable/), the accepted-writing references of the independent engineering pass (ai3/, results/improvement/).
Nothing in those packages is changed; the numba cache is private to platen/build.

Modules
-------
design      the proposed platen: stage, hold-down, palm rest, sensing options, lift/contact, budgets (PROPOSED DESIGN,
            CALCULATION, MANUFACTURER and LITERATURE values with their sources)
plant       the moving-page plant: HW1's hand and rigid pen co-simulated with a servo-driven page stage (coarse + fine),
            ball friction on the RELATIVE velocity, paper slip, lift/lower of the page; numba
sensing     sensing models for the platen (clip-on IMU, stylus IMU + contact, camera, EMR digitizer under the platen)
tremor      part (a): tremor on real recorded inputs (tuning split): perfect knowledge and study E's estimators through
            the stage, words read by study R's literal reader
accepted    part (b): accepted references ('se' suffixes, 'library' rewrite) executed by moving the page under a held pen
sensitivity part (c): page slip, pen tilt, sensing delay and noise, stage bandwidth, friction convention
report      results/platen/*.json with stabpen.provenance, figures with CSV twins, evidence_rows.csv
run         python3 -m platen.run [--quick] [--stages ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored ("build/" in .gitignore)
RESULTS_DIR = REPO_ROOT / "results" / "platen"
DOC_PATH = REPO_ROOT / "docs" / "platen_concept.md"

EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/, used read-only, with the moving-page stage of platen/plant.py) "
                "with REAL recorded inputs (study R's library: UNIPEN hpb2 writing, UCI PD tip tremor, Zenodo ET hand "
                "tremor); not a measurement of any device or person")
EVIDENCE_CALC = "CALCULATION on simulation output or on stated inputs; not a measurement"


def _env() -> None:
    """One numerical thread per process (shared machine); a private numba cache in platen/build, set BEFORE any numba
    import so that no other package's cache folder is written."""
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, "1")
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("MPLCONFIGDIR", str(BUILD_DIR / "mpl"))
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


_env()
