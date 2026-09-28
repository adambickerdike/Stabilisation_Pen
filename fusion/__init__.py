"""fusion: sensing and AI that tell tremor from intended writing, closed loop on the pencil model P1.

Evidence status: every number this package produces is a CALCULATION (datasheet
arithmetic, labelled with ledger ids) or a SIMULATION on synthetic handwriting and
synthetic tremor (sim/pencil, model P1).  No person was recorded and no hardware
was measured.  Datasheet values are manufacturer statements (MFR) with the ledger
ids of results/fusion/evidence_rows.csv; everything else a model needs is an
ASSUMPTION and is labelled as such where it is defined.

Modules
-------
parts       datasheet values of candidate IMUs and accelerometers (MFR), SNR in the tremor band (CALC)
sensors     sensor models on top of the recorded P1 housing motion: page (optical) sensor, IMU
            (accelerometer + gyroscope) with a kinematic pen-rotation component, nose accelerometer,
            axial contact sensor; noise, bias, drift, quantisation, rate and latency
data        scenario generation (test grid: sim.pensim.scenarios.handwriting; training: a faster,
            domain-randomised copy) and cached neutral P1 runs
harness     closed-loop evaluation through Controller(mode="external"): neutral, oracle,
            tremor-band oracle, external estimators, metrics (ratio, band ratio, distortion,
            saturation, rail power, path distance), optional re-estimation iteration
estimators  causal estimators (numba): frozen Kalman oscillator port (kfosc), acceleration-domain
            Kalman with delayed page-sensor updates and frequency tracking (AKF), WFLC and BMFLC on
            acceleration
learned     learned causal estimator (GRU) on IMU + page-sensor inputs, trained on P1 runs
context     AI-context estimator: letter template as an intent prior inside the Kalman filter
personal    per-writer calibration against frozen population parameters
tune        parameter search on training seeds (never on test seeds 200-203 or aiguide writers 0-5)
budget      MCU cost (MAC per tick, memory, latency) on an nRF54L15-class Cortex-M33 (CALC)
run_study   python3 -m fusion.run_study
"""
from __future__ import annotations

import os
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG_DIR)
RESULTS = os.path.join(ROOT, "results", "fusion")
BUILD = os.path.join(PKG_DIR, "build")          # git-ignored (".gitignore: build/"): caches only
CACHE = os.path.join(BUILD, "cache")

# keep numba caches (this package's estimators and the P1 core it calls) out of sim/ and stabpen/
os.makedirs(os.path.join(BUILD, "numba_cache"), exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(BUILD, "numba_cache"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

EVIDENCE_SIM = "SIMULATION (pencil model P1, synthetic handwriting and synthetic tremor; nothing measured)"
EVIDENCE_CALC = "CALCULATION (datasheet values labelled MFR with ledger ids; assumptions labelled)"

# seed plan (no overlap with the test seeds 200-203, their tremor streams 1200-1203, or aiguide writers 0-5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_SEEDS = tuple(range(5000, 5008))          # tuning of every conventional estimator (and the gains of the learned one)
TRAIN_SEEDS_BASE = 6000                        # learned-model training runs: 6000 + i (tremor stream 7000 + i)
VAL_SEEDS = tuple(range(9000, 9012))           # learned-model validation (early stopping)
CALIB_SEED_OFFSET = 40000                      # personalisation: calibration recording of test condition s uses s + 40000
AIGUIDE_TUNE_WRITERS = tuple(range(100, 106))  # context-estimator tuning writers (aiguide test writers are 0-5)
