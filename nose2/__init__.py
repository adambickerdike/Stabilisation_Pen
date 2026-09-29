"""nose2: Rev J study N, "nose v2" -- multi-pivot, multi-coil tip manipulation with +-5-8 mm, and autowrite within reach.

Evidence status of everything this package produces:
  CALC  a calculation (design models, closed-form physics, magnetics with magpylib's analytic magnets);
  SIM   an executed simulation of model HW1 (``handwriting/``, used read-only through its public API) on
        SYNTHETIC glyph writers (``aiguide``) and SYNTHETIC tremor (``stabpen.signals``);
  LIT / MFR  a published or manufacturer statement with its ledger id (``docs/evidence.csv`` or the rows this
        study proposes in ``results/nose2/evidence_rows.csv``);
  ASSUMPTION  an input nobody has measured.
Nothing here was built or measured on a pen or a person.

Seed discipline (docs/revJ_plan.md section 5): every design rule and setting is chosen on tuning writers
100-103 and tuning seeds 300-303; the rules are then frozen (``tuning.py``) and the final tables use the
test writers 0-5 and test seeds 200-203 only.

Modules
-------
planner     look-ahead autowrite planner: the text's pen path, a time warp chosen by dynamic programming so that
            the path stays within the nose's reach of a steadily sweeping hand
tasks       travel sizing from the tasks (tremor, guidance, autowrite, delayed ink), CALC on synthetic writers
frontend    the DEC-034 front-end closure generalised to +-4-8 mm (vectorised re-implementation of
            opt/inertial/front_end.py, checked against it)
magnetics   gap-flux calibration of the actuator topologies with magpylib (iron by images)
designs     differentiable (PyTorch) models of the candidate mechanisms
optimise    adjoint (L-BFGS) + CMA-ES over catalogue parts, Pareto fronts
autowrite   HW1 wrapper: steady hand sweep (+ tremor), the nose renders a known text; estimator, axial DOF
tuning      rules and tuning runs (tuning writers and seeds only)
evaluate    the test grid (test writers and seeds only)
figures, layout, evidence, report, run_study
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                     # git-ignored (".gitignore: build/")
RESULTS_DIR = REPO_ROOT / "results" / "nose2"

EVIDENCE_SIM = "SIMULATION (model HW1 via nose2/autowrite.py; synthetic glyph writers and synthetic tremor; not a measurement)"
EVIDENCE_CALC = "CALCULATION (design models on a PROPOSED DESIGN; inputs ASSUMPTION unless a ledger id is given)"

TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301, 302, 303)


def ensure_paths() -> None:
    """Repository root and app/ on sys.path (stabpen, handwriting, aiguide, penapp); a private numba cache."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
