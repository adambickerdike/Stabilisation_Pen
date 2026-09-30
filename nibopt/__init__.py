"""nibopt: study N of round 4 - the balanced nib's reach, force and heat, reconciled and optimised.

What it does (docs/nib_optimisation.md, results/nibopt/):
  reconcile   Rev K's B1 (study K), the independent engineering pass's re-optimised 1.059 mm and 1.5 mm nibs (24 mm body)
              and its 20 mm / 1.059 mm compaction, put under ONE load model, ONE force-constant convention and the same
              duties (study B's duty A, a severe-tremor duty at study F's target, the pass's worst-case periodic screen);
              battery hours per mode in study K's budget structure and skin temperature on study K's fin model; every
              difference between study K's and the pass's numbers itemised
  optimise    a constrained multi-objective search (NSGA-II, written here) over the nib family: usable radius, body
              diameter, magnets, iron path, winding, suspension (straight wire leads on a preloaded ball guide; the
              flexure-guided carriers are screened first and rejected, nibopt/suspension.screen_topologies),
              moving-mass options
  recommend   reach-first, balanced, slim and Rev K-envelope candidates; CAD (mechanics/cad/nibopt.py) and pen-level
              budgets

Evidence labels (the programme's convention; every number in the results carries one):
  CALCULATION      a calculation in this package (closed forms, beam models, analytic magnet fields, fin model)
  SIMULATION       an executed simulation, quoted from its study with its file (this package runs none)
  PROPOSED DESIGN  a dimension or choice made here
  MANUFACTURER     a datasheet value with its ledger id
  LITERATURE       a published value with its ledger id
  ASSUMPTION       an input nobody has measured; the experiment that pins it is named
Nothing in this package was built or measured.  The magnet model is an upper bound (ideal iron); it is derated.

Read-only inputs (imported or read, never written): revk/, bnib/, revj/, revj1/, nose2/, stabpen/, results/revK/,
results/bnib/, results/improvement/mechanics/, results/readable/.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

# one process, one BLAS / numba thread (four cores are shared with other studies)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

__version__ = "0.1.0"
VERSION = "nibopt-0.1"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS = REPO_ROOT / "results" / "nibopt"
BUILD = PKG_DIR / "build"                      # git-ignored caches ("build/" in .gitignore)
DOC = REPO_ROOT / "docs" / "nib_optimisation.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EVIDENCE = ("CALCULATION on PROPOSED DESIGNS (study N, round 4: the balanced nib's reach, force and heat); inputs from "
            "study K (revk/, results/revK/), study B (bnib/, results/bnib/), study F (results/readable/), the independent "
            "engineering pass (revk/feasibility.py, revk/improve.py, revk/compact.py, results/improvement/mechanics/), "
            "datasheets (MANUFACTURER) or ASSUMPTION; nothing built or measured")


def sha16(path: Path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except OSError:
        return "missing"


READ_ONLY = [
    "revk/feasibility.py", "revk/improve.py", "revk/compact.py", "revk/budgets.py", "revk/params.py", "revk/nib.py",
    "revk/counterface.py", "revk/frontend.py", "revk/tolerance.py", "bnib/loads.py", "bnib/contact.py", "bnib/balance.py",
    "bnib/flexure.py", "bnib/magnetics.py", "bnib/labels.py", "bnib/candidates.py", "nose2/magnetics.py",
    "results/revK/revK.json", "results/revK/layout.json", "results/revK/budgets.json",
    "results/improvement/mechanics/mechanics_study.json", "results/improvement/mechanics/compact_20mm.json",
    "results/readable/readable.json", "results/bnib/bnib.json",
]


def read_only_digests() -> dict:
    return {p: sha16(REPO_ROOT / p) for p in READ_ONLY}


def own_digests() -> dict:
    files = sorted(PKG_DIR.glob("*.py")) + [REPO_ROOT / "mechanics" / "cad" / "nibopt.py"]
    return {str(p.relative_to(REPO_ROOT)): sha16(p) for p in files if p.exists()}
