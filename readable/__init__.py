"""readable: how much tremor may be left at the pen tip for words to be readable, per-user gate calibration, and where
the gap between the best causal tremor estimator and perfect knowledge lies (study F, round 4).

Three questions, all in model HW1 (handwriting/, read-only) with study R's real-input library (realdata/, read-only) and
study E's estimators and cached tuning cases (realtrack/, read-only):
  E13   words read out of 10 against the tremor left at the tip, for three kinds of residual on top of perfect
        knowledge of the tremor: (a) the tremor scaled (an amplitude error), (b) the perfect estimate delayed (a lag
        error), (c) perfect cancellation plus band-limited noise (a random error).  The curve is fitted on R's TUNING
        split, the residual that gives +2 words (DEC-055) and 80 % of the tremor-free words are read off it, frozen, and
        confirmed once on R's TEST split.
  E11   per-writer calibration of the authority gate on the user's own clean writing (REQ-CTRL-016): the rule is chosen
        on the tuning split (each tuning note calibrated on the writer's other note), then applied once to the test
        writers (each calibrated on a different note of the same writer).  INFORMATION ONLY: study E has already seen
        the test split.
  gap   prediction or separation?  The residual left by predicting the tremor over the pen's real horizon when the
        tremor signal alone is known causally, against the residual left by the full estimators on tremor plus writing;
        each mapped to words through the E13 curve.

Evidence labels used for every number: SIMULATION (model HW1 with REAL recorded inputs: UNIPEN hpb2 writing, UCI PD tip
tremor, Zenodo ET hand tremor), CALCULATION, ASSUMPTION, PROPOSED DESIGN, LITERATURE (with its ledger id).  Nothing here
is a MEASUREMENT: nothing was built, and nothing was measured on a person or on hardware.

Modules
-------
common     paths, environment, R's and E's objects (notes, cases, pens), the measures, R-format cards
residual   the three E13 residual constructions (pure functions)
curve      the words-versus-residual model, its fit, its inversion and the writer bootstrap (pure functions)
e13        the E13 plan, the tuning and test jobs, the freeze and the aggregation
e11        the per-writer gate calibration: the rule grid, the tuning choice, the test jobs, the aggregation
gap        causal predictors of the clean tremor signal, the tremor-only sensor streams, the decomposition
jobs       a job runner with at most two worker processes (resumable: one JSON per job in readable/build)
figures    figures with CSV twins (results/readable/fig_*.png + .csv)
report     results/readable/readable.json (with stabpen.provenance), frozen.json, evidence_rows.csv
doc        the generated tables quoted by docs/readable_target.md
run        python3 -m readable.run [--quick] [--stages ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored ("build/" in .gitignore)
RESULTS_DIR = REPO_ROOT / "results" / "readable"
DOC_PATH = REPO_ROOT / "docs" / "readable_target.md"

EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/, used read-only) with REAL recorded inputs (study R's library: "
                "UNIPEN hpb2 writing, UCI PD tip tremor, Zenodo ET hand tremor); not a measurement of the pen or of any "
                "person")
EVIDENCE_CALC = "CALCULATION on simulation output; not a measurement"


def _env() -> None:
    """One numerical thread per process (shared machine); a private numba cache in readable/build, set BEFORE any numba
    import so that realdata's and realtrack's cache folders are never written; the reader's files are read offline."""
    n = os.environ.get("READABLE_THREADS", "1")
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, n)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


_env()
