"""board: the optional desk guidance board for the Rev H pen.

Evidence status: every number this package produces is a CALCULATION (CALC:
magpylib magnetostatics, linear dynamics, plate theory), a SIMULATION (SIM:
the closed-loop guidance runs in ``control.py`` on synthetic letter paths and
the HAP-26 hand model), a manufacturer statement (MFR, ledger id) or an
ASSUMPTION.  Nothing here has been built or measured.

The board is a grounded accessory under the paper.  An XY belt stage (CoreXY)
under a 2 mm glass writing surface carries a permanent-magnet head.  The head
pulls on a small magnet fixed in the heel of the pen's skid ring, so the board
pushes on the pen's handle, and so on the hand, over the whole page.  The
pen's active nose keeps doing the fine, fast correction (+/-3 mm) and the
board does the gross path.

Modules
-------
params        every design value, with its label and source
magnetics     magpylib force maps (head vs pen magnet), coil-array and
              electromagnet options, dipole cross-check
hand          HAP-26 two-stage hand impedance: deflection per force, nudge/steer
stage         CoreXY stage: stepper torque-speed, belt modes, bandwidth, latency
sensing       Hall-ring localisation of the pen magnet (Monte Carlo) and the
              comparison of sensing options
control       time-free path guidance (progress variable), partial/full levels,
              safety supervisor, closed-loop simulation with the hand model
architectures the comparison of architectures (i)-(iv)
bom           bill of materials and proposed evidence-ledger rows
layout        results/board/layout.json for the 3-D explainer
figures       figures with CSV twins
run_study     one command: ``python3 -m board.run_study``
"""
from __future__ import annotations

import os

# Keep numerical libraries light: the CPU is shared (<= 2 threads).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO_ROOT, "results", "board")
