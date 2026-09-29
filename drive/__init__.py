"""drive: a paper-grounded drive at the heel of the Rev H pen (study D, Rev J round 1).

Question: the pen always touches the paper while writing.  Which compact actuator at the skid/heel can push, steer
or brake the pen (and so the hand) along the paper, with the most useful force, safely?

Evidence status: every number this package produces is a CALCULATION (CALC: contact mechanics, motor and gear
catalogue arithmetic, geometry, a differentiable design model), a SIMULATION (SIM: model HW1-D = the handwriting
study's model HW1 with a friction-limited drive element at the heel, on SYNTHETIC writers, SYNTHETIC tremor and
SYNTHETIC writing forces), a manufacturer statement (MFR, ledger id), literature (LIT, ledger id) or an ASSUMPTION.
Nothing here has been built or measured on a pen, on paper or on a person.

Modules
-------
params       every design value with its label and source
catalog      catalogue motors, gearheads, sensors and wheels (MFR rows AMF-100...)
contact      writing-force model, drive-element normal load, traction, tyre stiffness, rolling resistance, slip
geometry     heel geometry: space next to the swinging nose, contact radius, tilt and roll tolerance
concepts     sizing of every concept (driven ball, omni-wheels, steered wheel with or without brake or drive,
             braked ball, controllable friction pads, others) with catalogue parts
design_opt   differentiable (torch autograd) sizing model of the two best concepts, adjoint optimisation with a
             finite-difference gradient check; Bayesian optimisation of control gains lives in tune.py
plant        model HW1-D: HW1's hand, handle, nose, ball and skid (reused equations and code) plus the heel drive
             element (holonomic drive, steered wheel with free/braked/driven rolling, isotropic brake), its sensors,
             control laws and safety supervisor; numba
scenarios    tasks (a) guided tracing, (b) PD "write big" loops, (c) reversed-letter lead-through, (d) tremor,
             (e) gross-scale autowrite, built on the handwriting and board studies' writers and paths
tune         tuning on tuning writers/seeds (Bayesian optimisation, GP + expected improvement), then the frozen rules
figures      figures, each with a CSV twin, and the markdown tables of the report
evidence     proposed ledger rows (results/drive/evidence_rows.csv)
layout       heel-drive parts of the recommended concept in the Rev H layout schema (results/drive/layout_parts.json);
             mechanics/cad/heel_drive.py builds the CAD from the same list
proposals    proposed requirement rows and experiments EXP-D01...
run_study    one command: python3 -m drive.run_study [--quick]

Seed plan (no test leakage): tuning on writers 100-102 and seed 300 (from the handwriting study's tuning set);
the rules are frozen in results/drive/rules.json before any test run; tests on writers 0-5 and seeds 200-203.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS_DIR = REPO_ROOT / "results" / "drive"
BUILD_DIR = PKG_DIR / "build"                       # git-ignored ("build/")

EVIDENCE_SIM = ("SIMULATION (model HW1-D: HW1 + a friction-limited heel drive; synthetic writers, tremor and writing "
                "forces; nothing measured)")
EVIDENCE_CALC = "CALCULATION (contact mechanics, catalogue arithmetic, geometry; PROPOSED DESIGN; nothing measured)"

TUNE_WRITERS = (100, 101, 102, 103, 104, 105)
TUNE_SEEDS = (300, 301, 302, 303)
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)


def ensure_paths() -> None:
    """Repository root and app/ on sys.path (handwriting, board, opt, aiguide, penapp, stabpen); private numba cache."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
