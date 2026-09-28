r"""Learned trackers trained on the tremor band, not on the whole disturbance (SIMULATION).

Both run at 1 kHz on causal inputs, their output is held over the two 0.5 ms stage ticks that follow (zero-order
hold) and passes the same 2nd-order Butterworth output low-pass as the AKF; they are trained through that
low-pass, at the tick level, so the prediction over the sensor and filter delays is learned rather than set.

opt_gru     GRU(7 -> H) + linear head on fusion.learned.features (IMU nib acceleration, page increments, new-sample
            flag, page validity, axial contact; the old GRU's inputs), output lp 60 Hz.
            Target: the true tremor-band disturbance db = BP_3-15Hz(d) (zero phase: the tremor-band oracle's
            signal, which a causal model can only predict), loss over the tremor recordings
                E = sqrt( sum_rec sum_m |d_hat - db|^2 / sum_rec sum_m |db|^2 )   (every frequency of the error
            counts, so slow friction drift in the output is penalised, unlike the old GRU's whole-disturbance
            target; energy-weighted over recordings like the AKF objective)
            + lambda_fc x false correction on the tremor-free runs (glyph writers weighted 3:1) + mu x RMS above
            150 Hz (the same terms as the AKF objective, opt.tracker.losses).
opt_hybrid  the adjoint-tuned AKF (numba core + output stage, fixed parameters) with a learned authority gate:
            gamma = sigmoid(GRU(16 -> H)) multiplies the AKF's estimate before its output low-pass,
                d_hat = LP(gamma x g_eff x d_akf).
            Inputs: the AKF's estimate before the low-pass (2) and its magnitude, its authority, tracked frequency,
            amplitude, the intent velocity (2) and speed, and the 7 sensor features.  The gate can only remove
            correction (0 <= gamma <= 1), never add content the AKF did not estimate.
            Loss: the AKF objective (band residual of d - d_hat, false correction, jitter).
Training data: fusion.learned._spec(i, "train") pairs (i < 400: 30 % glyph writers) with randomised sensor
rotation (opt.tracker.data); model selection on the validation pairs (fusion val specs) and tuning seeds 5004-5007.
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
from torch import nn

from . import MODEL_DIR
from . import losses as LS
from . import torch_akf as TA

from fusion import learned as FL  # noqa: E402
from fusion import sensors as S  # noqa: E402

NET_HZ = 1000.0
OUT_S = 100e-6
N_IN_GRU = FL.N_IN
N_IN_GATE = 16


# ------------------------------------------------------------------ features
def akf_features(st: S.Streams, akf_parts: Dict, K1: int) -> np.ndarray:
    """Hybrid gate inputs at 1 kHz (K1 steps): the AKF quantities at the tick of each network step plus the sensors."""
    X7, _ = FL.features(st, NET_HZ)
    X7 = X7[:K1]
    idx = np.minimum(np.arange(K1) * 2, len(st.tick_t) - 1)              # tick 2j is the network step t_j
    u = akf_parts["u"][idx]                                               # (K1, 2) estimate before the low-pass
    g = akf_parts["authority"][idx]
    f = akf_parts["f_est"][idx]
    a = akf_parts["amp_f"][idx]
    v = akf_parts["v"][idx]                                               # (K1, 2) intent velocity
    F = np.zeros((K1, N_IN_GATE), np.float32)
    F[:, 0:2] = u / OUT_S
    F[:, 2] = np.hypot(u[:, 0], u[:, 1]) / OUT_S
    F[:, 3] = g
    F[:, 4] = f / 10.0
    F[:, 5] = a / OUT_S
    F[:, 6:8] = v / 0.02
    F[:, 8] = np.hypot(v[:, 0], v[:, 1]) / 0.02
    F[:, 9:16] = X7
    return F


# ------------------------------------------------------------------ models
class GRUTracker(nn.Module):
    def __init__(self, n_in: int, hidden: int, n_out: int, gate: bool = False):
        super().__init__()
        self.hidden, self.n_in, self.gate = hidden, n_in, gate
        self.gru = nn.GRU(n_in, hidden, batch_first=True)
        self.head = nn.Linear(hidden, n_out)
        nn.init.normal_(self.head.weight, std=0.01)
        nn.init.constant_(self.head.bias, 3.0 if gate else 0.0)            # the gate starts open (sigmoid(3) = 0.95)

    def forward(self, x, h0=None):
        y, h = self.gru(x, h0)
        y = self.head(y)
        return (torch.sigmoid(y) if self.gate else y), h


def macs_per_step(n_in: int, hidden: int, n_out: int) -> int:
    """GRU gates 3 H (I + H) + candidate/update elementwise 3 H + head H n_out (fusion.learned convention)."""
    return 3 * hidden * (n_in + hidden) + 3 * hidden * n_out + 2 * hidden


def n_params(n_in: int, hidden: int, n_out: int) -> int:
    return 3 * hidden * (n_in + hidden) + 6 * hidden + hidden * n_out + n_out


# ------------------------------------------------------------------ tick-level output (ZOH + low-pass), torch
def zoh_lp(y1k: torch.Tensor, K: int, lp_hz: float, Ts: float = 0.5e-3) -> torch.Tensor:
    """(B, K1, C) at 1 kHz -> (B, K, C) at the ticks: zero-order hold over the two ticks, then the 2nd-order
    Butterworth low-pass of fusion.estimators._lp2_coef (exact IR, FFT convolution)."""
    B, K1, C = y1k.shape
    y = y1k.repeat_interleave(2, dim=1)[:, :K]
    if y.shape[1] < K:
        y = torch.cat([y, y[:, -1:].expand(B, K - y.shape[1], C)], 1)
    if lp_hz <= 0:
        return y
    h = TA.lp2_ir(torch.tensor([lp_hz], dtype=y.dtype), Ts, K)          # (1, K)
    return TA._fft_causal_conv(y.movedim(1, -1), h[:, None, :].to(y.dtype)).movedim(-1, 1)


# ------------------------------------------------------------------ inference (estimator interface for fusion.harness)
_MODELS: Dict = {}


def load(name: str):
    if name not in _MODELS:
        cfg = json.load(open(os.path.join(MODEL_DIR, name + ".json")))
        m = GRUTracker(cfg["n_in"], cfg["hidden"], cfg["n_out"], gate=cfg["kind"] == "hybrid")
        m.load_state_dict(torch.load(os.path.join(MODEL_DIR, name + ".pt"), map_location="cpu"))
        m.eval()
        _MODELS[name] = (m, cfg)
    return _MODELS[name]


def akf_parts_numpy(st: S.Streams, akf_params: Dict) -> Dict[str, np.ndarray]:
    """The AKF's per-tick quantities for one recording (numba core + torch output stage, no gradients)."""
    from . import adjoint as AD
    from . import schedule as SCH
    sch = [SCH.build(st)]
    ev = __import__("opt.tracker.data", fromlist=["light_events"]).light_events(sch)
    pk = AD.Packed(sch)
    static = TA.static_of(akf_params)
    with torch.no_grad():
        prm = TA.expand(TA.numba_to_values(akf_params), 1)
        XO, W = AD.CoreFn.apply(AD.core_params(prm, static["harm"]), pk, static["harm"])
        out, parts = TA.output_stage(XO, W, ev, prm, static, None, return_parts=True)
    u = (parts["authority"][..., None] * parts["d_pred"])[0].numpy()
    return {"out": out[0].numpy(), "u": u, "authority": parts["authority"][0].numpy(), "f_est": parts["f_est"][0].numpy(),
            "amp_f": parts["amp_f"][0].numpy(), "v": XO[0, :, :, 0].numpy()}


def estimate(name: str, st: S.Streams, params: Optional[Dict] = None, extra: Optional[Dict] = None):
    """fusion estimator interface: (d_hat (n_ticks, 2), info)."""
    p = dict(params or {})
    model = p.get("model", name)
    m, cfg = load(model)
    K = len(st.tick_t)
    K1 = int(math.ceil(K / 2))
    torch.set_num_threads(1)
    with torch.no_grad():
        if cfg["kind"] == "gru":
            X, _ = FL.features(st, NET_HZ)
            X = X[:K1]
            y, _ = m(torch.from_numpy(X[None]))
            out = zoh_lp(y.double() * cfg["out_scale"], K, cfg["lp_hz"])[0].numpy()
            return out, {"model": model}
        ap = akf_parts_numpy(st, cfg["akf_params"])
        F = akf_features(st, ap, K1)
        gam, _ = m(torch.from_numpy(F[None]))
        g2 = gam.double().repeat_interleave(2, dim=1)[:, :K]
        if g2.shape[1] < K:
            g2 = torch.cat([g2, g2[:, -1:].expand(1, K - g2.shape[1], 1)], 1)
        u = torch.from_numpy(ap["u"])[None] * g2
        out = zoh_lp_ticks(u, cfg["akf_params"].get("lp_hz", 60.0))[0].numpy()
        return out, {"model": model, "gate": g2[0, :, 0].numpy(), "authority": ap["authority"] * g2[0, :, 0].numpy(),
                     "f_est": ap["f_est"]}


def zoh_lp_ticks(u: torch.Tensor, lp_hz: float, Ts: float = 0.5e-3) -> torch.Tensor:
    """(B, K, C) at the ticks -> the AKF output low-pass."""
    if lp_hz <= 0:
        return u
    K = u.shape[1]
    h = TA.lp2_ir(torch.tensor([lp_hz], dtype=u.dtype), Ts, K)
    return TA._fft_causal_conv(u.movedim(1, -1), h[:, None, :].to(u.dtype)).movedim(-1, 1)
