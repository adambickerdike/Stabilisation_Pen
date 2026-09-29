"""revj: the Rev J integrated design (round 2): one consistent pen from the round-1 studies N (nose v2), D (heel drive)
and K (inertial end-cap), with the conflicts between them settled by calculation.

Evidence status of everything this package produces:
  CALC        a calculation on a PROPOSED DESIGN (geometry, closure checks, masses, budgets, magnetics with
              magpylib's analytic magnets, thermal fin estimates, spring design);
  SIM         only where a round-1 study's executed simulation is quoted (the file is named);
  LIT / MFR   a published or manufacturer statement with its ledger id in docs/evidence.csv;
  ASSUMPTION  an input nobody has measured.
Nothing here was built or measured on a pen or a person.  No new simulation of writers or tremor is run here.

Read-only inputs (never edited by this package):
  results/nose2/nose2.json, results/nose2/layout.json      (study N: C1S nose, pen lift, autowrite results)
  results/drive/layout_parts.json, drive/                   (study D: steered and driven heel wheel)
  results/endcap/layout_parts.json, results/endcap/endcap_study.json  (study K: reaction-mass end-cap)
  results/revH/layout.json, opt/inertial/front_end.py       (Rev H layout and the DEC-034 closure rules)

Modules
-------
params      every input with its label and source (loaded from the round-1 results where they exist)
frontend    DEC-034 closure generalised to the heel pod, wheel, steering ring and shafts; ink visibility; page-sensor
            window height over tilt and roll
refill      refill slide, holder travel, the spiral ink-force spring in the pen-lift drum (fatigue), the front stop
            that follows the nose, refill replacement
packaging   the integrated component layout (Rev H schema) and its fit checks
budgets     mass, centre of mass and inertia (with and without the end-cap), length, power and battery per mode,
            heat at the grip, cost class
magnetics   stray fields of the C1S magnets, the end-cap tiles and the sensor magnets at the motors, Hall sensors,
            IMU and outside the pen
simparams   the parameters a MuJoCo simulator (sim2) needs for the nose, heel wheel, refill and end-cap
run         python3 -m revj.run [--quick]  -> results/revJ/*.json and figures
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
RESULTS_DIR = REPO_ROOT / "results" / "revJ"

EVIDENCE_CALC = ("CALCULATION on a PROPOSED DESIGN (Rev J integration, round 2); inputs from the round-1 studies "
                 "(labelled) or ASSUMPTION; nothing built or measured")


def ensure_paths() -> None:
    """Repository root on sys.path (stabpen, opt, nose2, drive, endcap are imported read-only)."""
    p = str(REPO_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = PKG_DIR / "build" / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)


ensure_paths()
