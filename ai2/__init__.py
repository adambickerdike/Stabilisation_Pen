"""ai2: AI and control v2 for the Rev J pen (study L).

Evidence status: every number this package produces is a SIMULATION (model HW1 of ``handwriting/``, used read-only,
through the conventions of ``aiprior/``), a CALCULATION on synthetic writers (aiguide glyph-font writers) with
synthetic tremor, or a CALCULATION on public text corpora.  Nothing was measured on a person or on hardware.

Tasks (see docs/ai_control_v2.md):
  1  delayed ink        fixed-lag estimators (RTS fixed-lag Kalman smoother; windowed zero-phase smoother and fixed-lag
                        Wiener filter for comparison) that let the ink trail the hand by a lag; nose travel, stroke ends,
                        false correction                          smoothers.py, delayed.py, tuning.py, stage_test.py
  2  separation         the model-based causal stack (tremor-line detector + hysteresis/amplitude gate + listening
                        fixed-lag RTS at lag 0 + Rev H fallback) and learned causal estimators (TCN, calibrated TCN,
                        hybrid Kalman-network, transformer) with domain randomisation
                                                      data.py, learned.py, stage_learn*.py, candidates.py, stage_cl.py
  3  RL                 Gymnasium environments with a swappable plant backend (HW1 replay; sim2 can plug in), SB3 PPO
                        and SAC: a shared-control arbiter and a residual policy on the command     rl_env.py, stage_rl.py
  4  text prediction    word + character models on CC0 text, a small transformer       textpred.py, stage_text.py
  5  synthesis          sigma-lognormal extraction and synthesis in the writer's style; a few-shot generator on UJI
                                                                                        synth.py, stage_synth.py
  6  shared control     arbitration by confidence, assistance as needed, hand-back    shared.py, stage_shared.py
  report                figures with CSV twins, ai2.json, samples.json, proposed ledger rows    report.py, evidence.py

Seed conventions (no test leakage; the handwriting and aiprior studies' conventions):
  test         aiguide writers 0-5, seeds 200-203 (final tables only)
  tuning       aiguide writers 100-103, seeds 300+ (every choice, rules fixed before the test)
  training     aiguide writers 1000+ (learned models only), seeds 5000+
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

__version__ = "0.1.0"

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent
BUILD_DIR = PKG_DIR / "build"                      # git-ignored (".gitignore: build/")
RESULTS_DIR = REPO_ROOT / "results" / "ai2"

EVIDENCE_SIM = ("SIMULATION (model HW1 of handwriting/ via aiprior conventions; synthetic glyph writers, synthetic "
                "tremor; not a measurement)")
EVIDENCE_CALC = "CALCULATION (on synthetic data or public text; not a measurement)"

TEST_WRITERS = (0, 1, 2, 3, 4, 5)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_WRITERS = (100, 101, 102, 103)
TUNE_SEEDS = (300, 301)
TRAIN_WRITER0 = 1000                               # learned models train on writers >= 1000
F0S = (6.0, 8.0, 10.0)
AMPS = (0.3e-3, 1.0e-3, 2.0e-3)


def ensure_paths() -> None:
    """Repository root and app/ on sys.path; a private numba cache in ai2/build (set before any numba import)."""
    if "NUMBA_CACHE_DIR" not in os.environ:
        d = BUILD_DIR / "numba_cache"
        d.mkdir(parents=True, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = str(d)
    for p in (str(REPO_ROOT), str(REPO_ROOT / "app")):
        if p not in sys.path:
            sys.path.insert(0, p)


def limit_threads(n: int = 1) -> None:
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, str(n))


limit_threads(int(os.environ.get("AI2_THREADS", "1")))     # one numerical thread per process (shared machine)
ensure_paths()
