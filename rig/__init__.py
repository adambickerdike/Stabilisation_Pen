"""rig: acquisition and analysis software for the measurement rigs of study M.

Specification: docs/measurement_rig.md. Results: results/rig/.

Evidence status of everything this package computes in the repository: SIMULATION
(synthetic data made by rig.synth, partly through s2r's instrument models) or
CALCULATION. No rig has been built and nothing here is a measurement. When the
same code runs on files recorded on a real rig, its outputs are MEASURED and the
record rules of validation/records/README.md apply.

Labels used in every output (docs/measurement_rig.md, section 0):
  SIM                synthetic data run through the analysis (method check only)
  CALC               a calculation (uncertainty budget, envelope, sizing)
  MEASURED           a physical measurement (none exists yet)
  MFR <ledger id>    a manufacturer statement, ledger id in docs/evidence.csv or
                     results/rig/evidence_rows.csv
  LIT <ledger id>    a published result
  ASSUMPTION         an input nobody has measured
  PROPOSED DESIGN    a design choice made here

Import side effects: importing s2r (used for instrument models, FRF estimation
and the s2r-bench-1 file layout) pins BLAS/OpenMP/numba to one thread, which
keeps this package to one light process.
"""
from __future__ import annotations

import os
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

RESULTS = os.path.join(ROOT, "results", "rig")

SIM = "SIMULATION"
CALC = "CALCULATION"
MEASURED = "MEASURED"
ASSUMPTION = "ASSUMPTION"
PROPOSED = "PROPOSED DESIGN"

__version__ = "0.1.0"


def results_path(*parts: str) -> str:
    p = os.path.join(RESULTS, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p
