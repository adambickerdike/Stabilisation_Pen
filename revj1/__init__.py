"""revj1: the Rev J design-iteration study, round 3 ("Rev J.1").

The integrated Rev J pen (revj/, results/revJ/, DEC-044) passes its 38 geometric fit checks, but its budgets and loads
found six problems.  This package fixes them by calculation, chooses provisionally, and assembles Rev J.1:

  P1 gimbal axial load     revj1.gimbal (cross-strip pivot under axial load, thrust pivots) and revj1.magnetics
                           (the pull, ironless and spaced plates, a repelling ring, centring)
  P2 battery               revj1.power (page-sensor gating and frame rate per mode, sensor and MCU duty cycles, cells)
  P3 heat                  revj1.thermal (skin limit, spreader sizing in aluminium, copper or graphite sheet)
  P4 mass                  revj1.endcap_mass (study K's H1 models, read-only: the lightest slug that keeps rule R-T1)
                           and the base-pen savings in revj1.layout
  P5 ink visibility        revj1.visibility (transparent window, wider opening, eye positions)
  P6 heel-motor detent     revj1.magnetics (the torque that turns a rotor, a soft-iron cup, moving the motors)
  integration              revj1.layout (Rev J.1 layout and fit checks), revj1.budgets, revj1.simparams, revj1.figures
  ledger                   revj1.evidence (proposed rows, sources actually opened)
  run                      python3 -m revj1.run [--quick]  ->  results/revJ1/

Evidence status of everything here:
  CALC        a calculation on a PROPOSED DESIGN (this package's code);
  SIM         an executed simulation: only the end-cap sweep (study K's model H1, read-only, synthetic writing and
              tremor), and round-1 SIM results quoted with their file;
  LIT / MFR   a published or manufacturer statement with its ledger id (docs/evidence.csv, or the rows proposed in
              results/revJ1/evidence_rows.csv);
  ASSUMPTION  an input nobody has measured.
Nothing here was built or measured on a pen or a person.

Read-only inputs: revj/ (imported), results/revJ/, results/nose2/, results/endcap/, nose2/, endcap/, drive/, opt/, sim/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# One process, one thread: the four cores are shared with other studies, and multi-threaded BLAS on small matrices only
# thrashes (set before numpy is first imported).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS_DIR = REPO_ROOT / "results" / "revJ1"
CACHE_DIR = RESULTS_DIR / "_cache"

EVIDENCE_CALC = ("CALCULATION on a PROPOSED DESIGN (Rev J.1, design iteration round 3); inputs from Rev J (revj/), the round-1 "
                 "studies (labelled), datasheets (MFR) or ASSUMPTION; nothing built or measured")


def ensure_paths() -> None:
    """Repository root on sys.path (revj, stabpen, opt, nose2, drive, endcap are imported read-only)."""
    p = str(REPO_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = PKG_DIR / "build" / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
