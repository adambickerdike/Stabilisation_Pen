"""opt.tracker: the tremor tracker tuned by backpropagation through time and learned with an intent-aligned loss.

Evidence status of everything here: SIMULATION on the pencil model P1 with synthetic handwriting and synthetic
tremor (fusion/ sensor models), or CALCULATION (MCU cost).  No person was recorded and no hardware was measured.

Modules
-------
schedule    event bookkeeping of fusion.estimators._akf_run that depends only on sample times (which accelerometer
            and page samples each 0.5 ms tick processes, the rollback targets and re-applied samples, the filter time)
torch_akf   the acceleration-domain Kalman filter (AKF) of fusion.estimators.akf in PyTorch: same equations, batched
            over recordings with their own sample clocks, exact rollback of delayed page samples, frequency tracking,
            gates (hard = the numba ramps, or smooth), amplitude cap, output low-pass with predicted delay.
            Backpropagation through it is the discrete adjoint of the filter recursion.
losses      the intent-aligned loss: tremor-band (3-15 Hz) residual at contact ticks, false correction on tremor-free
            writing (weighted to the sharp glyph writers), estimate energy above 150 Hz
data        recorded sensor streams of the fusion training / validation specs and of the tuning conditions
train_akf   Adam / L-BFGS tuning of all AKF parameters (log-transformed), the lambda_fc Pareto sweep
gradcheck   finite-difference check of the adjoint gradients
learned     small causal networks with the tremor-band target, and the AKF + learned authority gate hybrid
personal    per-writer AKF parameters by gradient descent on the 20 s calibration recording (fusion.personal labels)
evaluate    closed loop on P1 (fusion.harness) and on the aiguide writers (fusion.aieval)
budget      MCU cost (fusion.budget conventions, nRF54L15 class)
run_study   python3 -m opt.tracker.run_study
"""
from __future__ import annotations

import os
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(PKG_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fusion  # noqa: E402  (sets NUMBA_CACHE_DIR and single-thread BLAS before numba / numpy work)

RESULTS = os.path.join(ROOT, "results", "opt")
MODEL_DIR = os.path.join(RESULTS, "tracker_models")
BUILD = os.path.join(PKG_DIR, "build")            # git-ignored ("build/" in .gitignore): caches and logs only
CACHE = os.path.join(BUILD, "cache")

EVIDENCE_SIM = ("SIMULATION (pencil model P1, synthetic handwriting and synthetic tremor, fusion/ sensor models; "
                "nothing measured)")
EVIDENCE_CALC = "CALCULATION (MAC counts; cycle model ASSUMPTION, fusion/budget.py conventions)"

# ------------------------------------------------------------------ seed plan (no test data used for tuning or training)
TEST_SEEDS = fusion.TEST_SEEDS                    # 200-203: final numbers only
AIGUIDE_TEST_WRITERS = (0, 1, 2, 3, 4, 5)          # final numbers only
TUNE_SEEDS = fusion.TUNE_SEEDS                    # 5000-5007: validation / model selection (grid generator)
AIGUIDE_TUNE_WRITERS = fusion.AIGUIDE_TUNE_WRITERS  # 100-105: validation / model selection (glyph writers)
TRAIN_PAIRS = 400                                 # fusion.learned._spec(i, "train"), i < 400: seeds 6000+i, glyph 16000+i
VAL_PAIRS = 24                                    # fusion.learned._spec(j, "val"): 9000-9011, 9101-9111, glyph 19000+j
STREAM_SEED_BASE = 30_000_000                     # sensor-noise draws of this study's training streams
CALIB_SEED_OFFSET = fusion.CALIB_SEED_OFFSET      # personal calibration of test seed s uses s + 40000 (as fusion)
