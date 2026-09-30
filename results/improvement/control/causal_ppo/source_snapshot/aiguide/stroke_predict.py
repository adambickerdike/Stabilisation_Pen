"""On-device stroke continuation: predict the current stroke 50-200 ms ahead.

Input: the pen's own position history (fused housing / nib position, ICD 4.2
p_H) at 200 Hz within the current stroke; output: the intended position h
ahead.  No language model is involved; this is the pen-MCU class of predictor
that can bridge the app's template latency or smooth a stroke locally.

Predictors (all causal):
  hold    the current position (baseline: error = distance travelled in h)
  cv      least-squares line over the last k samples, extrapolated (a fixed FIR per horizon)
  ca      least-squares parabola over the last k samples, extrapolated (a fixed FIR per horizon)
  arc     constant speed and turn rate from the parabola's velocity and acceleration
  mlp     2 x 64 ReLU network on the last 24 samples in a heading-aligned frame
          (trained with torch on synthetic writers; writer-disjoint split)

Evidence status: SIMULATION on synthetic glyph writers; the MAC counts are
CALCULATIONS.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

RATE = 200.0
TS = 1.0 / RATE
W = 24                               # history window (samples) = 120 ms
HORIZONS_S = (0.02, 0.05, 0.10, 0.15, 0.20)


@dataclass
class Windows:
    X: np.ndarray        # (n, W, 2) positions relative to the newest sample, m (observed: may include tremor)
    Y: np.ndarray        # (n, H, 2) intended displacement at each horizon relative to the newest *observed* sample, m
    Yi: np.ndarray       # (n, H, 2) intended displacement relative to the newest *intended* sample, m
    writer: np.ndarray   # (n,) writer id
    speed: np.ndarray    # (n,) intended speed at the newest sample, m/s


def windows_from_path(t: np.ndarray, intended: np.ndarray, observed: np.ndarray, pen_down: np.ndarray,
                      writer_id: int, horizons=HORIZONS_S, rate: float = RATE, min_hist: int = 6,
                      stride: int = 2) -> Windows:
    """Windows at ``rate`` inside pen-down runs; history zero-padded (edge-held) before the stroke start."""
    dt = t[1] - t[0]
    dec = max(1, int(round(1.0 / (rate * dt))))
    ti = t[::dec]
    I = intended[::dec]
    O = observed[::dec]
    D = pen_down[::dec]
    hs = [int(round(h * rate)) for h in horizons]
    d = np.diff(np.r_[0, D.astype(np.int8), 0])
    Xs, Ys, Yis, sp = [], [], [], []
    vI = np.gradient(I, 1.0 / rate, axis=0)
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        for k in range(a + min_hist, b - max(hs), stride):
            lo = k - W + 1
            idx = np.clip(np.arange(lo, k + 1), a, None)          # hold the first stroke sample before the start
            hist = O[idx] - O[k]
            Xs.append(hist)
            Ys.append(np.stack([I[k + h] - O[k] for h in hs]))
            Yis.append(np.stack([I[k + h] - I[k] for h in hs]))
            sp.append(np.hypot(*vI[k]))
    if not Xs:
        z = np.zeros((0, W, 2))
        return Windows(z, np.zeros((0, len(hs), 2)), np.zeros((0, len(hs), 2)), np.zeros(0, int), np.zeros(0))
    n = len(Xs)
    return Windows(np.asarray(Xs), np.asarray(Ys), np.asarray(Yis), np.full(n, writer_id), np.asarray(sp))


def concat(ws: Sequence[Windows]) -> Windows:
    return Windows(*(np.concatenate([getattr(w, f) for w in ws]) for f in ("X", "Y", "Yi", "writer", "speed")))


# ------------------------------------------------------------ kinematic FIRs
def poly_fir(k: int, deg: int, h_s: float, rate: float = RATE) -> np.ndarray:
    """FIR weights (length k, oldest first) extrapolating a degree-``deg`` LS fit h_s ahead."""
    tau = (np.arange(k) - (k - 1)) / rate
    V = np.vander(tau, deg + 1, increasing=True)
    pinv = np.linalg.pinv(V)                      # (deg+1, k)
    e = np.array([h_s ** p for p in range(deg + 1)])
    return e @ pinv


def predict_poly(X: np.ndarray, k: int, deg: int, horizons=HORIZONS_S) -> np.ndarray:
    out = np.zeros((X.shape[0], len(horizons), 2))
    for j, h in enumerate(horizons):
        w = poly_fir(k, deg, h)
        out[:, j, :] = np.einsum("k,nkc->nc", w, X[:, -k:, :])
    return out


def predict_arc(X: np.ndarray, k: int, horizons=HORIZONS_S, k_max_curv: float = 3000.0) -> np.ndarray:
    """Constant speed and turn rate: circle through the newest, middle and oldest of the last k samples.

    Exact for noise-free circular arcs at constant speed; the heading at the
    newest sample is the chord direction turned by half the subtended angle.
    """
    m = max(1, (k - 1) // 2)
    P0 = X[:, -1, :]
    P1 = X[:, -1 - m, :]
    P2 = X[:, -1 - 2 * m, :]
    a = P0 - P1
    b = P1 - P2
    c = P0 - P2
    la, lb, lc = (np.hypot(v[:, 0], v[:, 1]) for v in (a, b, c))
    cross = b[:, 0] * a[:, 1] - b[:, 1] * a[:, 0]
    kap = np.where(la * lb * lc > 1e-15, 2.0 * cross / np.maximum(la * lb * lc, 1e-30), 0.0)
    kap = np.clip(kap, -k_max_curv, k_max_curv)
    # arc lengths from chords
    def arc(ch):
        x = np.clip(np.abs(kap) * ch / 2.0, 0.0, 1.0)
        return np.where(np.abs(kap) > 1e-9, 2.0 * np.arcsin(x) / np.maximum(np.abs(kap), 1e-12), ch)
    speed = (arc(la) + arc(lb)) / (2 * m * TS)
    th = np.arctan2(a[:, 1], a[:, 0]) + 0.5 * kap * arc(la)
    om = speed * kap
    out = np.zeros((X.shape[0], len(horizons), 2))
    for j, h in enumerate(horizons):
        straight = np.abs(kap) < 1e-6
        kk = np.where(straight, 1.0, kap)
        dx = np.where(straight, speed * h * np.cos(th), (np.sin(th + om * h) - np.sin(th)) / kk)
        dy = np.where(straight, speed * h * np.sin(th), (np.cos(th) - np.cos(th + om * h)) / kk)
        out[:, j, 0] = P0[:, 0] + dx
        out[:, j, 1] = P0[:, 1] + dy
    return out


# ------------------------------------------------------------------- MLP
def _heading(X: np.ndarray, k: int = 4) -> np.ndarray:
    d = X[:, -1, :] - X[:, -1 - k, :]
    return np.arctan2(d[:, 1], d[:, 0])


def _rot(v: np.ndarray, ang: np.ndarray) -> np.ndarray:
    c, s = np.cos(ang), np.sin(ang)
    x, y = v[..., 0], v[..., 1]
    if v.ndim == 3:
        c, s = c[:, None], s[:, None]
    return np.stack([c * x - s * y, s * x + c * y], axis=-1)


def mlp_features(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    th = _heading(X)
    Xr = _rot(X, -th) * 1e3                         # mm, heading frame
    return Xr.reshape(len(X), -1).astype(np.float32), th


class MLPPredictor:
    def __init__(self, hidden: int = 64, n_h: int = len(HORIZONS_S)):
        import torch
        self.hidden = hidden
        self.n_h = n_h
        self.net = torch.nn.Sequential(torch.nn.Linear(2 * W, hidden), torch.nn.ReLU(),
                                       torch.nn.Linear(hidden, hidden), torch.nn.ReLU(),
                                       torch.nn.Linear(hidden, 2 * n_h))
        self.history: Dict[str, List[float]] = {"train": [], "val": []}

    def macs(self) -> int:
        return 2 * W * self.hidden + self.hidden * self.hidden + self.hidden * 2 * self.n_h

    def n_params(self) -> int:
        return sum(p.numel() for p in self.net.parameters())

    def fit(self, tr: Windows, va: Windows, epochs: int = 30, lr: float = 2e-3, batch: int = 512, seed: int = 7):
        import torch
        torch.manual_seed(seed)
        torch.set_num_threads(2)
        Xtr, thtr = mlp_features(tr.X)
        Ytr = (_rot(tr.Y, -thtr) * 1e3).reshape(len(tr.Y), -1).astype(np.float32)
        Xva, thva = mlp_features(va.X)
        Yva = (_rot(va.Y, -thva) * 1e3).reshape(len(va.Y), -1).astype(np.float32)
        xt, yt = torch.from_numpy(Xtr), torch.from_numpy(Ytr)
        xv, yv = torch.from_numpy(Xva), torch.from_numpy(Yva)
        opt = torch.optim.AdamW(self.net.parameters(), lr=lr, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
        best, best_state = 1e18, None
        g = torch.Generator().manual_seed(seed)
        for ep in range(epochs):
            self.net.train()
            perm = torch.randperm(len(xt), generator=g)
            tot = 0.0
            for i in range(0, len(xt), batch):
                j = perm[i:i + batch]
                loss = torch.nn.functional.smooth_l1_loss(self.net(xt[j]), yt[j], beta=0.05)
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += float(loss.detach()) * len(j)
            sched.step()
            self.net.eval()
            with torch.no_grad():
                vl = float(torch.mean((self.net(xv) - yv) ** 2))
            self.history["train"].append(tot / len(xt))
            self.history["val"].append(vl)
            if vl < best:
                best = vl
                best_state = {k: v.clone() for k, v in self.net.state_dict().items()}
        self.net.load_state_dict(best_state)
        self.best_epoch = int(np.argmin(self.history["val"]))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        import torch
        F, th = mlp_features(X)
        with torch.no_grad():
            out = self.net(torch.from_numpy(F)).numpy().reshape(len(X), self.n_h, 2) / 1e3
        return _rot(out, th)


# ------------------------------------------------------------------ budget
def mac_budget(k_cv: int, k_ca: int, k_arc: int, mlp_macs: int, rate_hz: float = 250.0, f_cpu: float = 128e6) -> dict:
    """MAC and time per prediction on a Cortex-M33 (single-precision FPU; CALCULATION).

    FIR predictors: k MACs per axis per horizon.  Arc: the parabola fit
    (3 k per axis) + 20-step integration (about 10 flops per step with sin/cos
    from a 2-term recurrence) per horizon.  MLP: dense layers.  Cycles: 1.5 per
    float MAC (load + VFMA, pessimistic for M33 without SIMD float); int8
    CMSIS-NN at 0.5 MAC/cycle for the MLP alternative (EML-23 figure used by ml/).
    """
    H = len(HORIZONS_S)
    rows = {
        "cv": 2 * H * k_cv,
        "ca": 2 * H * k_ca,
        "arc": 60 + H * 12,                  # circumcircle (3 points) + closed-form arc per horizon
        "mlp_float": mlp_macs,
    }
    out = {}
    for name, m in rows.items():
        cyc = 1.5 * m + 200
        out[name] = {"mac": int(m), "cycles": int(cyc), "time_us_128MHz": cyc / f_cpu * 1e6,
                     "cpu_load_at_rate": cyc * rate_hz / f_cpu}
    cyc8 = mlp_macs / 0.5 + 3 * 300
    out["mlp_int8_cmsis"] = {"mac": int(mlp_macs), "cycles": int(cyc8), "time_us_128MHz": cyc8 / f_cpu * 1e6,
                             "cpu_load_at_rate": cyc8 * rate_hz / f_cpu}
    out["_assumptions"] = {"rate_hz": rate_hz, "f_cpu_hz": f_cpu, "float_cycles_per_mac": 1.5, "overhead_cycles": 200,
                           "int8_mac_per_cycle": 0.5, "icd_s5_budget": "<= 35 k MAC, <= 1 ms at 128 MHz per inference"}
    return out
