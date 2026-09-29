"""bnib: study B of round 4 - the balanced two-axis nib (docs/balanced_nib.md, results/bnib/, config/nib.yaml).

Question.  The Rev J moving nose (C1S) spends most of its coil power holding the ball against the paper: the refill
spring pushes the ball along the tilted pen, the paper pushes back partly sideways (F_c cot theta), and the C1S lever
(ball 76.48 mm from the gimbal, magnets on an 11.5 mm arm) multiplies that side load by 6.65 at the magnets
(independent review of 2026-09-29, section 4; docs/reviews/2026-09-29_review_response.md).  This package designs the
fast core that must work before anything else is built on it: a low-mass, mechanically load-balanced two-axis nib.

Evidence labels used throughout (docs/round4_plan.md section 5):
  CALC             a calculation in this package (closed forms, design models, magpylib magnetics, beam models);
  SIM              an executed simulation (sim2 / MuJoCo 3.6, synthetic writers and synthetic tremor);
  LIT / MFR        a published or manufacturer statement with its ledger id (docs/evidence.csv, or the rows this study
                   proposes in results/bnib/evidence_rows.csv, only for sources actually opened);
  ASSUMPTION       an input nobody has measured;
  PROPOSED DESIGN  a dimension or choice made here.
Nothing in this package was built or measured on a pen or a person.

Modules
-------
labels       the labelled-value record V and the ledger ids used
interface    config/nib.yaml: the ONE versioned definition of the nib's physical interface (writer and loader)
contact      vector contact statics at the ball with a friction map; contact Jacobian; the refill's axial balance
loads        every force and moment on the nib, tip-referred, for any nib and pose; why study N's duty model missed the
             static term (reproduces 4.717 / 1.628 / 0.166 W)
magnetics    magpylib + image-method force maps of the actuators: Km(position), cross-coupling, parasitic pull,
             negative stiffness over the full stroke
flexure      translation and gimbal flexures: stiffness, full-travel strain with stress concentrations, Goodman fatigue
             at 43.2 million cycles, buckling, loaded eigenmodes with geometric stiffness, tolerances (revj1.gimbal reused)
thermal      two-node thermal model (coil, grip shell) with a governor
actuators    voice-coil (nose2 topology models, magpylib-calibrated) and piezo-bender stage models
balance      the balance mechanisms: scheduled bias (b), contact-driven counter-face (c), steep tip (e), low ink force (d)
inkforce     the minimum ink force by tip type: what the sources opened here say, and what gate G1 must measure
candidates   candidates (a)-(h) for the two grip classes (24 mm pen, DEC-029; 12-16 mm slim core): one metrics dict each
optimise     CMA-ES + exact-gradient (PyTorch autograd) polish on epsilon-constraint problems; Pareto fronts
sim          the best candidates in sim2 (MuJoCo): friction map, filtered servo, DeltaPen-style page sensor, counter-face
             contact, governor; ET/PD tremor, false correction and thermal runs
layout, figures, evidence, report, run_study
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# one process, one BLAS thread (four cores are shared with five other studies)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

__version__ = "0.1.0"
VERSION = "bnib-0.1"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS = REPO_ROOT / "results" / "bnib"
BUILD = PKG_DIR / "build"                      # git-ignored caches ("build/" in .gitignore)
CONFIG_NIB = REPO_ROOT / "config" / "nib.yaml"
DOC = REPO_ROOT / "docs" / "balanced_nib.md"

# data discipline (docs/round4_plan.md section 5): rules are fixed on tuning writers/seeds before any test run
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301, 302, 303)

EVIDENCE_CALC = ("CALCULATION on PROPOSED DESIGNS (study B, balanced nib); inputs LIT/MFR with ledger ids or ASSUMPTION; "
                 "nothing built or measured")
EVIDENCE_SIM = ("SIMULATION (sim2, MuJoCo 3.6; synthetic writers and synthetic tremor; PROPOSED DESIGN parameters). sim2 ranks "
                "concepts (context of use COU-1, docs/sim_v2.md section 8.1) until bench calibration; not evidence of "
                "benefit to people")


def ensure_paths() -> None:
    """Repository root and app/ on sys.path (stabpen, nose2, revj1, sim2, sim2j, handwriting, penapp are imported
    read-only); a private numba cache in bnib/build."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()


def file_sha(rel: str) -> str:
    """sha256 (16 hex) of a repository file: read-only inputs that other studies may still be editing are recorded
    with the result that used them."""
    p = REPO_ROOT / rel
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return "missing"


READ_ONLY_INPUTS = ("nose2/designs.py", "nose2/magnetics.py", "revj1/gimbal.py", "sim2/builder.py", "sim2/sim.py",
                    "sim2/contact.py", "sim2j/akf_online.py", "sim2j/writers.py", "sim2j/tasks.py", "wholepen/designs.py",
                    "results/nose2/nose2.json")


def provenance(evidence_status: str, seeds=None, extra=None) -> dict:
    """The stabpen.provenance block for every result file of this study (with the digests of the read-only inputs)."""
    from stabpen import provenance as _pv
    ex = {"package": "bnib", "version": VERSION, "read_only_inputs_sha256_16": {r: file_sha(r) for r in READ_ONLY_INPUTS}}
    if extra:
        ex.update(extra)
    return _pv.metadata(evidence_status, seeds=seeds, extra=ex)


def write_json(name: str, obj: dict) -> str:
    from stabpen import provenance as _pv
    path = name if os.path.isabs(name) else str(RESULTS / name)
    _pv.write_json(path, obj)
    return path


def read_json(name: str) -> dict:
    path = name if os.path.isabs(name) else str(RESULTS / name)
    with open(path) as f:
        return json.load(f)


def cache_path(*parts: str) -> Path:
    p = BUILD.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
