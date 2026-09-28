"""opt.hardware: the nib-stage hardware optimised for correction authority inside the Rev P0 envelope.

Evidence status of everything here: CALCULATION (design model, catalogue scaling), SIMULATION (finite-element
drop model, the pencil model P1) or MANUFACTURER STATEMENT / LITERATURE with a ledger id (catalogue).  No part
has been built or measured.

Modules
-------
catalogue      buyable and buildable parts with sources, ledger ids and status (catalogue / custom from a
               supplier's standard process / build in-house): piezo benders and plates, tubes, drivers, cells,
               Hall sensors, flexure materials and processes, refills
model          the design model of sim/pencil/design.py, analysis/pencil_mechanisms.py and the CAD fit formulas of
               mechanics/cad/pencil_revP.py re-expressed in PyTorch; reverse-mode automatic differentiation gives the
               exact gradients (the adjoint) of every objective and constraint; drive power with the
               sim/pencil/power.py conventions and a closed-loop Hall-noise model
reference      the same quantities from the existing numpy code (design.py, pencil_mechanisms.py, CAD formulas),
               for the agreement checks
drop_surrogate response surface of the finite-element drop stress (analysis/pencil_mechanisms.drop_sim), trained
               on a design of experiments; used as a differentiable constraint, verified by the FE at the optimum
optimise       augmented-Lagrangian L-BFGS-B and projected Adam with multiple starts, exhaustive enumeration of the
               discrete choices (topology, ceramic, stack, leaf material, driver, Hall sensor), a small Gaussian-
               process Bayesian optimiser (torch) as a global check, epsilon-constraint Pareto fronts
p1_harness     the pencil model P1 on the harness grid (neutral and oracle, seeds 200-203) for any registered stage
registry       stage-registry entries for sim/pencil/design.py and the CAD overlay for mechanics/cad/pencil_revP.py
run_study      python3 -m opt.hardware.run_study
"""
from __future__ import annotations

import os
import sys

# one thread per process: the host's 4 cores are shared, and the model's small batched tensors run ~10x faster
# single-threaded than with intra-op threading (measured: 25 ms vs 270 ms per forward+backward at B = 16)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
try:
    import torch as _torch
    _torch.set_num_threads(1)
except ImportError:          # pragma: no cover
    pass

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(PKG_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "results", "opt")
