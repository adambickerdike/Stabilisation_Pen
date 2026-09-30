"""revk: study K of round 4 - the Rev K integrated layout (docs/revK_design.md, results/revK/).

Rev K is the Rev J body with study B's balanced translation nib B1 (DEC-050, docs/balanced_nib.md, config/nib.yaml,
results/bnib/) in place of the C1S nose, the heel wheel retracted (DEC-048) and no tail or end-cap (DEC-051).  This
package places every part along the pen, checks the fits, budgets mass, balance, power per mode, battery hours, skin
temperature, the nib's structural modes against DEC-050's 2.5 x rule and cost, and writes the parameters the whole-pen
simulator (sim2 / sim2j) needs to run Rev K later.

Evidence labels used throughout (the programme's convention):
  CALCULATION      a calculation in this package (closed forms, beam models, magpylib magnetics, ray casting, fin model)
  SIMULATION       an executed simulation (quoted from study B / sim2j with its file; this package runs none by default)
  MANUFACTURER     a datasheet or distributor page, with the part number and the ledger id (docs/evidence.csv, or the rows
                   proposed in results/revK/evidence_rows.csv for sources opened in this study)
  LITERATURE       a published source with its ledger id
  ASSUMPTION       an input nobody has measured; each names the test that will pin it
  PROPOSED DESIGN  a dimension or choice made here
Nothing in this package was built or measured on a pen or a person.

Read-only inputs (imported or read, never written): bnib/ (the nib's models), results/bnib/, config/nib.yaml, revj/,
revj1/, results/revJ/, results/revJ1/, opt/, nose2/, stabpen/.

Modules
-------
params        every Rev K input as V(value, unit, label, source)
nib           B1 in the pen: the design point, a buildable coil against the bore (magpylib), the suspension wires as coil
              leads, the loaded modes free and stuck against the 2.5 x rule, drop and shock, the Hall keep-outs, the nib's
              power per duty
frontend      the front end for a translation nib: ring, sleeve, page-sensor window, ink visibility, the hand; the heel
              pod for the heel-module variant
counterface   the counter-face head: kinematics over tilt, roll, nib travel and wobble; the follower stop; the pen lift; the
              magnetic refill coupling; the face-parallelism tolerance stack; the refill change
tolerance     the nib-centring stack
layout        every part placed (the Rev J layout schema) and the fit checks, base pen and heel-module variant
budgets       mass, balance, inertia; power per mode and battery hours; skin temperature; cost and bill of materials
simparams     results/revK/sim_params.json in the schema of results/revJ/sim_params.json
figures, evidence, run
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# one process, one BLAS thread (four cores are shared with other studies)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

__version__ = "0.1.0"
VERSION = "revk-0.1"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS = REPO_ROOT / "results" / "revK"
BUILD = PKG_DIR / "build"                      # git-ignored caches ("build/" in .gitignore)
DOC = REPO_ROOT / "docs" / "revK_design.md"

EVIDENCE_CALC = ("CALCULATION on a PROPOSED DESIGN (Rev K integrated layout, study K of round 4); inputs from study B "
                 "(bnib/, results/bnib/, config/nib.yaml), Rev J / J.1 (revj/, revj1/), datasheets (MANUFACTURER) or "
                 "ASSUMPTION; nothing built or measured")


def ensure_paths() -> None:
    """Repository root and app/ on sys.path (bnib, revj, revj1, opt, nose2, stabpen are imported read-only); a private
    numba cache in revk/build (never another package's build directory)."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    if "MPLCONFIGDIR" not in os.environ:
        d = BUILD / "mpl"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(d)


ensure_paths()


def file_sha(rel: str) -> str:
    """sha256 (16 hex) of a repository file (the read-only inputs that other studies may still be editing are recorded
    with every result that used them)."""
    p = REPO_ROOT / rel
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return "missing"


READ_ONLY_INPUTS = ("results/bnib/bnib.json", "results/bnib/layout_parts.json", "config/nib.yaml", "bnib/flexure.py",
                    "bnib/magnetics.py", "bnib/candidates.py", "bnib/loads.py", "bnib/labels.py", "bnib/balance.py",
                    "revj/params.py", "revj/budgets.py", "revj/frontend.py", "revj1/params.py", "revj1/power.py",
                    "revj1/thermal.py", "results/revJ/layout.json", "results/revJ/sim_params.json",
                    "results/revJ1/layout.json", "results/revJ1/budgets.json", "opt/inertial/front_end.py",
                    "docs/decisions.md", "docs/requirements.csv")


def provenance(evidence_status: str, quick: bool = False, extra: dict = None) -> dict:
    """The stabpen.provenance block of every result file of this study (git revision, the read-only inputs' sha256,
    parameters, command, versions)."""
    from stabpen import provenance as _pv
    ex = {"package": "revk", "version": VERSION, "script": "revk/run.py", "doc": "docs/revK_design.md", "quick": quick,
          "read_only_inputs_sha256_16": {r: file_sha(r) for r in READ_ONLY_INPUTS},
          "revk_sources_sha256_16": {f"revk/{p.name}": file_sha(f"revk/{p.name}") for p in sorted(PKG_DIR.glob("*.py"))},
          "parameters": "every input with its label and source is in revK.json -> inputs (revk/params.py, revk/layout.LAY, "
                        "revk/tolerance tables)"}
    try:
        import magpylib, matplotlib  # noqa: F401
        ex["magpylib"] = magpylib.__version__
        ex["matplotlib"] = matplotlib.__version__
    except Exception:
        pass
    if extra:
        ex.update(extra)
    return _pv.metadata(evidence_status, extra=ex)


def out_dir(quick: bool = False) -> Path:
    """results/revK/ (full run) or revk/build/quick/ (--quick, git-ignored); REVK_OUT overrides both (tests)."""
    if os.environ.get("REVK_OUT"):
        d = Path(os.environ["REVK_OUT"])
    else:
        d = BUILD / "quick" if quick else RESULTS
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_path(*parts: str) -> Path:
    p = BUILD.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def clean(o):
    """JSON-safe copy (numpy scalars and arrays, inf/nan as strings)."""
    import math
    import numpy as np
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        o = float(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return "inf" if math.isinf(o) else "nan"
    return o


def write_json(path, obj: dict, status: str, quick: bool = False, extra: dict = None) -> str:
    md = provenance(status, quick, extra)
    obj = {"meta": md, "stabpen.provenance": md, **obj}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean(obj), f, indent=1)
    return str(path)
