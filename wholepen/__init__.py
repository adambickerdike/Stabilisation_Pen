"""wholepen: study W of round 4 - shifting and pivoting the WHOLE pen against tremor of 1-10 mm (docs/whole_pen_shift.md).

Evidence status: every number this package produces is a CALCULATION (closed forms, the reduced linear model lin.py,
design models) or a SIMULATION (MuJoCo through sim2 and the Rev J closed loop of sim2j, used read-only) on SYNTHETIC
writers and SYNTHETIC or RECORDED tremor.  Nothing was built or measured on a pen or a person.  Labels used throughout:
SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, PROPOSED DESIGN.  sim2 ranks concepts (context of use COU-1,
docs/sim_v2.md section 8.1); its numbers are not evidence of benefit to people.

Modules
-------
targets     task 1: tremor at the pen tip per class (mild / moderate / severe; ET, PD action, PD rest/re-emergent) from the
            literature (rating-scale relations, prevalence) and from recorded data (realdata.py)
realdata    the recorded PD data sets: UCI spiral tablet data (positions) and NewHandPD pen signals (1 kHz accelerations):
            tremor lines, frequencies, amplitudes, share of patients with a tremor line while drawing
grip        task 2: the grip model (finger pads, thumb-index web, pivoting of a held pen) with literature bounds and a
            sensitivity range, compared with H1 and study K's splits
lin         reduced linear model (small motions, frequency domain, torch float64 for exact gradients): hand, two-zone
            grip, optional pivot collar, pen, tail devices (CMG pair, tuned mass), paper, heel and sled forces
designs     task 3: the candidate mechanisms sized (mass, travel, force/torque, power, heat, noise, stored energy, safety)
devices     the new devices in sim2 (MuJoCo): CMG tail module (scissored pairs), tuned mass, pivot collar (builder patch),
            hand-rest sled; with their verification hooks
control     the device control laws (tremor-band only), run inside sim2j's firmware at the 2 kHz tick
stepper     sim2j's Rev J stepper with the whole-pen devices and controllers in the loop
cases       tremor classes as simulator inputs (H1 hand path and articulated-arm torques; recorded PD waveforms), writer
            set-ups, one case, metrics (tip tremor, ink error, letters and words read, force, power, speed)
verify      per-device simulator checks: energy, closed forms, time-step convergence
optimise    CMA-ES + exact-gradient polish of the best combination's parameters on the linear model, checked in sim2
figures     figures with CSV twins, before/after writing pictures
explain     animation.json keyframes and layout_parts.json for the 3-D explainer
evidence    proposed ledger rows (results/wholepen/evidence_rows.csv)
run_study   one command: python3 -m wholepen.run_study [--quick] [--stages ...]; long stages resume from caches
"""
from __future__ import annotations

import os as _os
import sys as _sys

_PKG = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.dirname(_PKG)
BUILD = _os.path.join(_PKG, "build")                  # gitignored caches (build/)
RESULTS = _os.path.join(ROOT, "results", "wholepen")
DOC = _os.path.join(ROOT, "docs", "whole_pen_shift.md")
# numba caches of the packages this one compiles go to wholepen/build; one BLAS thread per process (shared machine)
_os.environ.setdefault("NUMBA_CACHE_DIR", _os.path.join(BUILD, "numba_cache"))
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    _os.environ.setdefault(_k, "1")
for _p in (ROOT, _os.path.join(ROOT, "app")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

VERSION = "wholepen-0.1"

# data discipline (docs/round4_plan.md section 5): rules are fixed on tuning writers/seeds before any test run
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301, 302, 303)

# recorded data (read-only inputs; not in the repository): the lead's copy of NewHandPD's PatientSignal.zip and the
# copies this study downloaded (HealthySignal.zip, the UCI spiral archive) in the session scratchpad
SCRATCH = _os.environ.get("WHOLEPEN_DATA", "/tmp/claude-0/-home-user-Stabilisation-Pen/21ffa498-a5b5-550f-aea7-f21160eb3068/scratchpad")


def provenance(evidence_status: str, seeds=None, extra=None) -> dict:
    """stabpen.provenance block for every result file of this study."""
    from stabpen import provenance as _pv
    ex = {"package": "wholepen", "version": VERSION}
    if extra:
        ex.update(extra)
    return _pv.metadata(evidence_status, seeds=seeds, extra=ex)


def write_json(name: str, obj: dict) -> str:
    from stabpen import provenance as _pv
    path = name if _os.path.isabs(name) else _os.path.join(RESULTS, name)
    _pv.write_json(path, obj)
    return path
