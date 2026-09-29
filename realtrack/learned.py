"""Learned causal estimators trained on REAL inputs (tuning split only), cross-fitted by writer and patient fold.

Evidence status: SIMULATION (training data = model HW1 runs with real tuning notes and real tuning tremor; the target is
the simulation's true handle tremor).  No test writer, text or patient is ever loaded here.

Inputs (causal): the page-frame nib acceleration of the pen's IMU (fusion.sensors; gyroscope-compensated board IMU),
pairs block-averaged (FIFO read), then averaged over each input step of 1 / FS_IN (every sample that became AVAILABLE in
the step; held if none).  The page sensor is not used: with the DeltaPen-class error model its error in the tremor band
is hundreds of um (the error accumulates, as in a relative sensor), while the accelerometer's noise there is < 1 um.

fir   a linear causal filter, the same for both page axes (isotropy), L taps at FS_IN; polyphase: at a 2 kHz tick
      with phase p (0.5 ms steps since the newest input step) the filter h_p predicts the handle tremor at the tick
      time + the servo group delay (the delay handling is learned); ridge least squares (normal equations), loss =
      squared error on active ticks (in contact or within 2 mm of the page) + LAMBDA_FC x squared output on tremor-free
      notes (the false-correction penalty of fusion.learned / ai2)
net   a small causal network (TCN or GRU, <= 50 k parameters, int8-friendly), same inputs plus the contact flag,
      output at FS_IN with the polyphase head (8 outputs per step, one per tick phase) (see train_net)
Cross-fitting: fold k = tuning writer k + the tuning subjects of fold k (cases.py); the model scored on fold k's
selection cases is trained on the other four folds' data only.  The model used on the test split is trained on all
five folds' data (fixed rule; no test data).
"""
from __future__ import annotations

import json
import math
import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR
from . import cases as C

FS_IN = 250.0
TICK_HZ = 2000.0
N_PH = int(TICK_HZ / FS_IN)          # 8 tick phases per input step
LAMBDA_FC = 1.0
MODEL_DIR = BUILD_DIR / "models"


# ------------------------------------------------------------------ inputs
def acc_grid(st, fs: float = FS_IN):
    """(t_k (K,), A (K, 2)): the mean page-frame acceleration of the samples available in (t_{k-1}, t_k], held."""
    from .estimators import acc_blocks
    ta, tav, y = acc_blocks(st)
    t_end = float(st.tick_t[-1])
    tk = np.arange(0.0, t_end + 1e-12, 1.0 / fs)
    ia = np.searchsorted(tav, tk, side="right")
    cs = np.vstack([np.zeros((1, 2)), np.cumsum(y, axis=0)])
    i0 = np.r_[0, ia[:-1]]
    cnt = ia - i0
    A = np.zeros((len(tk), 2))
    ok = cnt > 0
    A[ok] = (cs[ia[ok]] - cs[i0[ok]]) / cnt[ok, None]
    last = np.maximum.accumulate(np.where(ok, np.arange(len(tk)), 0))
    return tk, A[last]


def tick_index(tick_t: np.ndarray, fs: float = FS_IN):
    """For each tick: the newest completed input step k and the tick's phase p within the step."""
    k = np.floor(tick_t * fs + 1e-9).astype(int)
    p = np.clip(np.round((tick_t - k / fs) * TICK_HZ).astype(int), 0, N_PH - 1)
    return k, p


def target(case, lead: float) -> np.ndarray:
    tick_t = case.tick_t
    d = case.truth
    return np.column_stack([np.interp(tick_t + lead, tick_t, d[:, 0]), np.interp(tick_t + lead, tick_t, d[:, 1])])


# ------------------------------------------------------------------ FIR (ridge, polyphase, isotropic)
def _lagmat(x: np.ndarray, k: np.ndarray, L: int) -> np.ndarray:
    """Rows x[k - j], j = 0..L-1 (zeros before the start)."""
    idx = k[:, None] - np.arange(L)[None, :]
    out = np.where(idx >= 0, x[np.clip(idx, 0, len(x) - 1)], 0.0)
    return out


def fir_stats(case, L: int, lead: float, sensor: str = "deltapen", hp_hz: float = 0.0, weight_clean: float = LAMBDA_FC,
              stride: int = 1) -> Dict:
    """Per phase: X'X (L x L, the same for every phase: the inputs are the 250 Hz steps), X'y_p (L,), from one case
    (both axes stacked).  Rows: the input steps k with the nose active (tick at t_k) after 1 s; the target of phase p
    is the truth at t_k + p / 2000 s + lead."""
    st = case.streams(sensor)
    tk, A = acc_grid(st)
    if hp_hz > 0:
        from scipy.signal import butter, lfilter
        b, a = butter(2, hp_hz, btype="high", fs=FS_IN)
        A = lfilter(b, a, A, axis=0)
    act = np.interp(tk, case.tick_t, case.arrays["active_ticks"]) > 0.5
    sel = np.flatnonzero(act & (tk > 1.0))[::max(1, stride)]
    w = 1.0 if case.meta.get("tremor") else weight_clean
    Xs = [_lagmat(A[:, ax], sel, L) for ax in range(2)]
    XX = w * sum(X.T @ X for X in Xs)
    out = {}
    tick_t = case.tick_t
    d = case.truth if case.meta.get("tremor") else np.zeros((len(tick_t), 2))
    for ph in range(N_PH):
        tt = tk[sel] + ph / TICK_HZ + lead
        Xy = np.zeros(L)
        yy = 0.0
        for ax in range(2):
            y = np.interp(tt, tick_t, d[:, ax])
            Xy += Xs[ax].T @ y
            yy += float(y @ y)
        out[ph] = (XX, w * Xy, w * yy, 2 * len(sel))
    return out


def fir_solve(stats: List[Dict], L: int, ridge: float) -> np.ndarray:
    """h (N_PH, L) from summed statistics; ridge relative to the mean diagonal."""
    H = np.zeros((N_PH, L))
    for ph in range(N_PH):
        XX = sum(s[ph][0] for s in stats if ph in s)
        Xy = sum(s[ph][1] for s in stats if ph in s)
        lam = ridge * float(np.trace(XX)) / L
        H[ph] = np.linalg.solve(XX + lam * np.eye(L), Xy)
    return H


def fir_apply(st, H: np.ndarray, hp_hz: float = 0.0) -> np.ndarray:
    tk, A = acc_grid(st)
    if hp_hz > 0:
        from scipy.signal import butter, lfilter
        b, a = butter(2, hp_hz, btype="high", fs=FS_IN)
        A = lfilter(b, a, A, axis=0)
    L = H.shape[1]
    k, p = tick_index(st.tick_t)
    out = np.zeros((len(st.tick_t), 2))
    # the filter outputs of every phase at every input step, then each tick picks its phase
    from scipy.signal import lfilter
    Yph = np.zeros((N_PH, len(tk), 2))
    for ph in range(N_PH):
        for ax in range(2):
            Yph[ph, :, ax] = lfilter(H[ph], [1.0], A[:, ax])
    kk = np.clip(k, 0, len(tk) - 1)
    out[:, 0] = Yph[p, kk, 0]
    out[:, 1] = Yph[p, kk, 1]
    return out


_FIR: Dict = {}


def load_fir(tag: str) -> Dict:
    if tag not in _FIR:
        _FIR[tag] = json.loads((MODEL_DIR / f"fir_{tag}.json").read_text())
    return _FIR[tag]


def estimate(name: str, st, p: Optional[Dict], horizon, case=None):
    """Registry hook (estimators.raw_estimate): p = {'tag': model tag, 'fold': 'auto' | int | None}."""
    p = dict(p or {})
    tag = p.get("tag", "fir_main")
    fold = p.get("fold", "auto")
    if fold == "auto":
        fold = None if case is None or case.spec.get("split") != "tuning" else int(case.spec["fold"])
    if name == "fir":
        m = load_fir(tag)
        H = np.asarray(m["H_all"] if fold is None else m["H_fold"][str(fold)])
        return fir_apply(st, H, m.get("hp_hz", 0.0)), {"fold": fold, "tag": tag}
    if name == "net":
        from . import netmodel as NM
        return NM.estimate(st, tag, fold, case=case), {"fold": fold, "tag": tag}
    raise KeyError(name)


def train_fir(specs: Sequence[Dict], L: int = 128, lead: Optional[float] = None, ridge: float = 1e-3,
              hp_hz: float = 0.0, sensor: str = "deltapen", tag: str = "fir_main", weight_clean: float = LAMBDA_FC,
              log=print) -> Dict:
    """Cross-fitted FIR: statistics per fold, a filter per held-out fold and one on all folds."""
    from .estimators import servo_delay
    lead = servo_delay() if lead is None else lead
    t0 = time.time()
    per_fold: Dict[int, List[Dict]] = {f: [] for f in range(C.N_FOLDS)}
    for s in specs:
        c = C.load_case(s)
        per_fold[int(s["fold"])].append(fir_stats(c, L, lead, sensor, hp_hz, weight_clean))
        del c
    allst = [x for v in per_fold.values() for x in v]
    H_all = fir_solve(allst, L, ridge)
    H_fold = {str(f): fir_solve([x for g, v in per_fold.items() if g != f for x in v], L, ridge).tolist()
              for f in range(C.N_FOLDS)}
    m = {"tag": tag, "L": L, "fs_in": FS_IN, "lead_s": lead, "ridge": ridge, "hp_hz": hp_hz, "sensor": sensor,
         "weight_clean": weight_clean, "H_all": H_all.tolist(), "H_fold": H_fold, "n_cases": len(specs),
         "trained_on": "tuning split only (cases.py folds)", "elapsed_s": time.time() - t0}
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (MODEL_DIR / f"fir_{tag}.json").write_text(json.dumps(m))
    _FIR.pop(tag, None)
    log(f"[fir] {tag}: L {L} at {FS_IN:g} Hz, lead {lead * 1e3:.2f} ms, ridge {ridge:g}, {len(specs)} cases, "
        f"{m['elapsed_s']:.0f} s")
    return m
