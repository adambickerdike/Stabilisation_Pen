"""rebaseline: study X, the re-baseline of the project's headline simulation results after the engineering pass of
30 September 2026 (commit e09a15f).

The engineering pass found that several earlier simulation results used optimistic or incorrect models: exact
simulator velocity and immediate true contact in sim2's nib servo, a 400 Hz inner loop that is unstable with causal
sensing, a page-sensor model that let future motion alter past errors (realdata/sensors.py version 1), balanced-nib
loads without phase, wire tension or the guide's rolling drag, and an RL reward that stopped charging tracking error
when the ball lost contact.  This package reruns the headline results with the corrected models and says which
conclusions survive.

Evidence labels used on every number: SIMULATION (the model, the sensing mode and the inputs are named), CALCULATION,
ASSUMPTION, LITERATURE.  Nothing here is a measurement: nothing was built, and nothing was measured on a pen or a person.

Other packages (sim2, sim2j, bnib, realdata, realtrack, readable, revk, handwriting, ...) are imported READ-ONLY.
Where a run needs a different behaviour, it is a runtime substitution inside this process (never an edit of their
files), and it is named in the result's provenance.  Caches go to rebaseline/build/ (git-ignored); results to
results/rebaseline/; the write-up is docs/rebaseline.md.

Modules
-------
common        paths, provenance (git revision, input hashes, seeds, parameters, command, versions), JSON and row caches
impact        the impact register: every SIM row of docs/claims_register.md's preserved register, the model it used,
              and its classification (unaffected / affected and rerun here / affected and not rerun / superseded)
sim2j_cards   task 2: sim2j's headline cards (Rev J + guarded tracker G4, ET grid) under causal sensing, legacy flags,
              and the legacy flags with the historical firmware contact channel (the exact reproduction)
bnib_rerun    task 3: the balanced nib in sim2 (study B's set-up) with DEC-066's 40/46 Hz servo and corrected loads
              (nonlinear wires with the stated anchor stiffness, about 8 mN of guide drag), Rev K's nib and the
              24 mm / 1.5 mm candidate
reach_b1      task 4: study F's perfect-knowledge reach check with the balanced nib's servo bandwidth and moving mass
page_v2       task 5: the DeltaPen-class page-sensor rows of studies R, E and F re-analysed with the causal version 2
report        results/rebaseline/*.json summaries, the evidence rows CSV and the tables quoted by docs/rebaseline.md
run           python3 -m rebaseline.run [--quick] [--stages ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored (root .gitignore: build/)
RESULTS_DIR = REPO_ROOT / "results" / "rebaseline"
DOC_PATH = REPO_ROOT / "docs" / "rebaseline.md"

EVIDENCE_SIM = ("SIMULATION on synthetic or recorded inputs as named per result; not a measurement of a pen or of any "
                "person")
EVIDENCE_CALC = "CALCULATION on simulation output or on stated parameters; not a measurement"


def env() -> None:
    """One numerical thread per process (shared 4-core machine), private numba and matplotlib caches in
    rebaseline/build, set BEFORE any numba import so that no other package's build folder is written."""
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ[v] = "1"
    if "NUMBA_CACHE_DIR" not in os.environ or "rebaseline" not in os.environ["NUMBA_CACHE_DIR"]:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    os.environ.setdefault("MPLCONFIGDIR", str(BUILD_DIR / "mpl"))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


env()
