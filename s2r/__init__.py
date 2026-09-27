"""Sim-to-real methodology for the stabilisation pen, built and demonstrated in simulation.

Everything this package produces is SIMULATION or CALCULATION. The "bench" is
virtual: M1 (sim/pensim) or small standalone models with hidden true parameters,
seen through measurement models of the instruments named in
validation/bench_protocols.md. Twin experiments show that the identification and
calibration method works on data whose structure we control. They do not show
that M1 is right about the real pen; only the bench can.

Import side effects (deliberate, before any numba import):
  * NUMBA_CACHE_DIR defaults to s2r/build/numba_cache so this package never
    writes compiled bytecode into sim/pensim/ (other agents share that tree).
  * the repository root is put on sys.path so ``sim.pensim`` and ``stabpen``
    import the same way the rest of the repository does;
  * BLAS/OpenMP/numba thread pools default to one thread per process, so the
    "at most 2 processes" CPU budget also holds in cores.
"""
from __future__ import annotations

import os
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG_DIR)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(PKG_DIR, "build", "numba_cache"))
# one compute thread per process: the CPU budget is counted in processes (at most 2 workers)
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RESULTS = os.path.join(ROOT, "results", "s2r")

# Evidence labels used in every output (docs/sim_to_real.md section 0).
SIMULATION = "SIMULATION"
CALCULATION = "CALCULATION"
ASSUMPTION = "ASSUMPTION"
PROTOCOL = "PROTOCOL"      # value copied from validation/bench_protocols.md
