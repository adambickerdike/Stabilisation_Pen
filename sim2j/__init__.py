"""sim2j: the whole Rev J pen in simulator v2 (Rev J round 2, closed-loop simulation study).

Evidence status: every number this package produces is a SIMULATION (MuJoCo 3.6 through sim2) or a CALCULATION on
SYNTHETIC writers and SYNTHETIC tremor.  Nothing here was measured on a pen or a person.  Labels used throughout:
SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, PROPOSED DESIGN.  Until EXP-V01/V02/V04 calibrate sim2 and
EXP-V05 validates it, these results rank concepts (context of use COU-1, docs/sim_v2.md section 8.1) and are not
evidence of benefit.

Modules
-------
writers     writer model v2: the aiguide glyph writers re-timed by the two-thirds power law, fitted to adult phrase
            speed (LIT CON-20), the velocity spectrum (LIT CON-25, CON-24) and the power law (LIT CON-27); the v1
            writers are kept for comparison
revj        the Rev J pen in sim2: C1S nose (+-6 mm, DEC-036), refill front stop that follows the nose, pen lift,
            heel wheel (DEC-037), optional reaction-mass end-cap (DEC-038); parameters from round 1
wheel       the steered and driven heel wheel: tyre bristle law, steering servo, rolling degree of freedom (numba,
            every physics step), after drive/plant.py (HW1-D)
akf_online  the project's AKF tremor tracker (fusion/estimators.py) ported to a tick-by-tick form, bit-exact against
            the batch version, with a frequency-runaway guard and a running spectral tremor-line detector
sensing     the pen's own sensors, online: IMU (fusion noise models, firmware compensation), page sensor, refill
            slide, wheel load and heading
firmware    the controllers: tremor cancellation, coordinated nose + wheel, end-cap feed-forward, template guidance,
            lead-through, autowrite (nose2 planner), pen lift, supervisor (force caps, lateral release, yield)
stepper     sim2's stepper with the Rev J devices and the firmware in the loop
tasks       scenarios: ET, PD 'write big' loops, dysgraphia tracing, dyslexia lead-through and autowrite, severe tremor
metrics     ink error, letters and words read by the app's recogniser, device share, force on the hand, power
rl          Gymnasium environment on the Rev J pen with domain randomisation; PPO (Stable-Baselines3)
verify      overlap checks against round 1 (nose2 autowrite in HW1, drive tasks in HW1-D)
run_study   one command: python3 -m sim2j.run_study [--quick] [--stages ...]
"""
from __future__ import annotations

import os as _os
import sys as _sys

_PKG = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.dirname(_PKG)
BUILD = _os.path.join(_PKG, "build")
RESULTS = _os.path.join(ROOT, "results", "sim2j")
# numba caches of every package this one compiles go to sim2j/build (gitignored); one BLAS thread per process
_os.environ.setdefault("NUMBA_CACHE_DIR", _os.path.join(BUILD, "numba_cache"))
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    _os.environ.setdefault(_k, "1")
for _p in (ROOT, _os.path.join(ROOT, "app")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

VERSION = "sim2j-0.1"

# data discipline (docs/revJ_plan.md section 5): every rule is fixed on tuning writers/seeds before any test run
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301, 302, 303)
TRAIN_WRITERS = tuple(range(1000, 1400))       # RL and fitting only (never 0-5, 100-105)
