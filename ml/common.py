"""Shared constants (the firmware <-> ML contract, docs/icd.md s5), paths,
environment guards and provenance helpers for the ml/ pipeline.

Importing this module first:
  * stops Python from writing byte-code into directories owned by others
    (stabpen/, sim/); ml/ writes only inside ml/, data/ and results/ml/;
  * points numba's on-disk cache at ml/runs/numba_cache (git-ignored) so that
    calling the simulator never writes into sim/pensim/__pycache__.
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DIR = os.path.join(ROOT, "ml")
RUNS = os.path.join(ML_DIR, "runs")                 # git-ignored cache (datasets, logs)
EXPORT = os.path.join(ML_DIR, "export")
RESULTS = os.path.join(ROOT, "results", "ml")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(os.path.join(RUNS, "numba_cache"), exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(RUNS, "numba_cache"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

EVIDENCE = "SIMULATION / synthetic data"
EVIDENCE_LONG = ("SIMULATION / synthetic data: synthetic handwriting (sigma-lognormal, stabpen.signals) "
                 "plus synthetic tremor; not human recordings, not bench measurements, no clinical claim")

# ------------------------------------------------------------------ contract (docs/icd.md s5)
FS = 250.0                 # Hz, predictor input rate
TS = 1.0 / FS
W = 64                     # samples per input window (256 ms)
H_S = 0.006                # s, prediction horizon after the newest sample's time stamp
FS_FINE = 1000.0           # Hz, generation rate of the synthetic truth (interpolated for delays)
MAC_BUDGET = 35_000
FLASH_BUDGET_B = 32 * 1024
RAM_BUDGET_B = 8 * 1024
TIME_BUDGET_S = 1e-3
F_CLK_HZ = 128e6

# The model exported to ml/export/ (contract v1.1: dp_x, dp_y only, no f_est input).  Its
# results use the plain file names (results/ml/quantization.json, export_c.json); any other
# model (e.g. tcn_s, contract v1.0 with f_est) gets <stem>_<model>.json and an out-of-tree
# C export in ml/runs/export_<model>/ (see ml/export_c.py).
EXPORT_MODEL = "tcn_s_nofest"


def result_json(stem, model):
    """results/ml/<stem>.json for EXPORT_MODEL, results/ml/<stem>_<model>.json otherwise."""
    return os.path.join(RESULTS, f"{stem}.json" if model == EXPORT_MODEL else f"{stem}_{model}.json")

# Time-stamp convention (proposed clarification, see ml/README.md "Proposed contract changes"):
# a sample is time-stamped when it becomes available to the firmware; it describes the housing
# at (stamp - sensor delay).  The target is d(stamp + h), i.e. the physical prediction horizon is
# h + delay (8-9 ms for a 2-3 ms optical delay).  Conventional estimators extrapolate by
# h + TAU_NOM (latency known from calibration, EXP-S01); the learned model learns it.
TAU_NOM = 0.0025

# ------------------------------------------------------------------ model input scaling
IN_CLIP_UM = 400.0         # |increment| per 4 ms sample represented without clipping (100 mm/s)
S_IN = 100.0               # float input = clip(dp_um) / S_IN
F_REF_HZ = 8.0             # f_est channel: (f_est - F_REF) * F_GAIN in "micrometre-equivalent" units
F_GAIN = 50.0
S_OUT = 100.0              # float output * S_OUT = d_hat in um

# ------------------------------------------------------------------ evaluation
HOLDOUT_BAND = (7.0, 8.0)  # nominal tremor f0 never used for training, validation or the main test
BANDS = ((4.0, 6.0), (6.0, 7.0), (7.0, 8.0), (8.0, 10.0), (10.0, 12.0001))
BAND_NAMES = ("4-6 Hz", "6-7 Hz", "7-8 Hz (holdout)", "8-10 Hz", "10-12 Hz")
FC_TARGETS_UM = (10.0, 25.0, 50.0)   # matched false-correction operating points (RMS, um)
FC_HEADLINE_UM = 25.0
WARMUP_S = 1.0             # ticks before this time are not scored (all estimators converge)
G_MAX = 2.0                # largest output gain allowed in the matched false-correction sweep
LAMBDA_NT = 4.0            # training/fitting weight of no-tremor samples (penalty on false correction)


def band_index(f0):
    """Index into BANDS for nominal tremor frequency f0 (array); -1 if outside / no tremor."""
    f0 = np.asarray(f0, float)
    out = np.full(f0.shape, -1, int)
    for i, (lo, hi) in enumerate(BANDS):
        out[(f0 >= lo) & (f0 < hi)] = i
    return out


def meta(seeds=None, extra=None, status=EVIDENCE):
    """Provenance block (stabpen.provenance) plus ML library versions."""
    from stabpen import provenance
    ex = {"evidence_detail": EVIDENCE_LONG}
    try:
        import torch
        ex["torch"] = torch.__version__
    except Exception:  # pragma: no cover
        pass
    try:
        import numba
        ex["numba"] = numba.__version__
    except Exception:  # pragma: no cover
        pass
    ex.update(extra or {})
    return provenance.metadata(status, seeds=seeds, extra=ex)


def write_json(path, obj):
    from stabpen import provenance
    provenance.write_json(path, obj)


def rpath(p):
    """Repository-relative path for reports."""
    return os.path.relpath(p, ROOT)
