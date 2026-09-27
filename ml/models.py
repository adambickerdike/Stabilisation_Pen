r"""Learned causal disturbance predictors (SIMULATION / synthetic data).

TCNTree: causal dilated temporal convolutional network, kernel 2, dilations
1, 2, 4, 8, 16, 32 (receptive field 64 samples = the contract window W), ReLU,
followed by a 2-layer MLP head, evaluated only at the newest sample.  Evaluated
that way the dilated stack reduces exactly to a binary tree of stride-2 layers:
layer l maps each pair of adjacent positions (older, newer) of its input
sequence to one output position, 64 -> 32 -> 16 -> 8 -> 4 -> 2 -> 1.  Each layer
is therefore a fully-connected layer applied to a batch of contiguous channel
pairs (NHWC), i.e. one CMSIS-NN arm_fully_connected_s8 call (or arm_convolve_s8
with a 1x2 kernel, stride 2, dilation 1); no dilated kernel is needed.

Input (contract, docs/icd.md s5): window of 64 increments dp (x, y) in um, mapped to
channels in "um-equivalent" units and scaled by 1/S_IN:
    ch0, ch1 = clip(dp_um, +-IN_CLIP_UM) / S_IN
    ch2      = clip((f_est - F_REF_HZ) * F_GAIN, +-IN_CLIP_UM) / S_IN   (broadcast over the window)
ch2 exists only in 3-channel models (contract v1.0, e.g. tcn_s).  Contract v1.1 dropped
f_est: a model trained with the f_est channel held at zero (train.py --no-fest) is
deployed as the equivalent 2-channel model (`drop_fest`, exact), e.g. tcn_s_nofest.
Sharing one scale lets the int8 input tensor use a single symmetric quantiser
(IN_CLIP_UM / 127 = 3.15 um per LSB for dp, 0.063 Hz per LSB for f_est).
Output: d_hat(t_k + h) in um = S_OUT * network output.
The streaming alternative (one new position per layer and step, cached
intermediate states) is implemented in `stream_reference` for the budget
analysis and the equivalence test.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import common as C

CONFIGS = {
    "tcn_s": {"channels": (8, 12, 16, 24, 32, 32), "head": 24},
    "tcn_m": {"channels": (12, 16, 24, 32, 40, 48), "head": 32},
}
C_IN = 3                       # training layout: dp_x, dp_y, f_est (contract v1.0)
INPUT_NAMES = ("dp_x", "dp_y", "f_est")


def input_names(c_in):
    """Names of the input channels of a c_in-channel model (2: contract v1.1, 3: v1.0)."""
    assert c_in in (2, 3), c_in
    return list(INPUT_NAMES[:c_in])


def deployed_c_in(cfg):
    """Input channels of a model as deployed, from its saved config (results/ml/model/<name>.json):
    3-channel models trained with the f_est channel held at zero (use_fest false) are
    deployed with 2 channels (see drop_fest)."""
    c_in = int(cfg.get("c_in", C_IN))
    return 2 if (c_in == 3 and not cfg.get("use_fest", True)) else c_in


class TCNTree(nn.Module):
    def __init__(self, channels=(8, 12, 16, 24, 32, 32), head=24, c_in=C_IN):
        super().__init__()
        assert len(channels) == 6, "6 levels: 2**6 = W = 64"
        assert c_in in (2, 3), "inputs: dp_x, dp_y (+ f_est)"
        self.channels, self.head_units, self.c_in = tuple(channels), int(head), int(c_in)
        cin = c_in
        self.levels = nn.ModuleList()
        for c in channels:
            self.levels.append(nn.Linear(2 * cin, c))
            cin = c
        self.head = nn.Linear(cin, head)
        self.out = nn.Linear(head, 2)
        for m in list(self.levels) + [self.head]:
            nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
            nn.init.zeros_(m.bias)
        nn.init.normal_(self.out.weight, std=0.01)
        nn.init.zeros_(self.out.bias)
        # 3 channels: False = ablation with the f_est channel held at zero; 2 channels: no f_est
        self.use_fest = self.c_in == 3

    def forward(self, x, return_acts=False):
        """x: (B, 64, c_in) channels-last (oldest sample first)."""
        acts = [x]
        h = x
        for lin in self.levels:
            b, L, c = h.shape
            h = F.relu(lin(h.reshape(b, L // 2, 2 * c)))
            acts.append(h)
        h = F.relu(self.head(h.reshape(h.shape[0], -1)))
        acts.append(h)
        y = self.out(h)
        acts.append(y)
        return (y, acts) if return_acts else y

    def config(self):
        return {"arch": "TCNTree", "channels": list(self.channels), "head": self.head_units, "c_in": self.c_in,
                "kernel": 2, "dilations": [1, 2, 4, 8, 16, 32], "receptive_field": 64}

    def layer_table(self):
        """Per-layer MACs (window mode = tree), parameters and output sizes."""
        rows = []
        cin, L = self.c_in, C.W
        for i, c in enumerate(self.channels):
            L //= 2
            rows.append({"layer": f"level{i + 1} (dilation {2 ** i})", "positions": L, "c_in": cin, "c_out": c,
                         "macs": L * 2 * cin * c, "weights": 2 * cin * c, "biases": c, "out_elems": L * c,
                         "stream_macs": 2 * cin * c, "stream_state_elems": (2 ** i) * cin})
            cin = c
        rows.append({"layer": "head", "positions": 1, "c_in": cin, "c_out": self.head_units,
                     "macs": cin * self.head_units, "weights": cin * self.head_units, "biases": self.head_units,
                     "out_elems": self.head_units, "stream_macs": cin * self.head_units, "stream_state_elems": 0})
        rows.append({"layer": "out", "positions": 1, "c_in": self.head_units, "c_out": 2, "macs": 2 * self.head_units,
                     "weights": 2 * self.head_units, "biases": 2, "out_elems": 2, "stream_macs": 2 * self.head_units,
                     "stream_state_elems": 0})
        return rows

    def macs(self):
        return int(sum(r["macs"] for r in self.layer_table()))

    def n_params(self):
        return int(sum(p.numel() for p in self.parameters()))


def build(name):
    return TCNTree(**CONFIGS[name])


def drop_fest(model):
    """Equivalent 2-channel copy (contract v1.1) of a 3-channel TCN trained with the f_est
    channel held at zero (train.py --no-fest).  Level 1 sees (older, newer) sample pairs laid
    out as [dp_x, dp_y, f_est] x 2, so its f_est weight columns are 2 and 5.  They only ever
    multiplied zero, so removing them leaves the function unchanged: exact in real arithmetic,
    float32 results differ only by summation order (unit-tested).  Other layers are copied."""
    assert model.c_in == 3 and not model.use_fest, "only for models trained without f_est"
    m2 = TCNTree(channels=model.channels, head=model.head_units, c_in=2)
    sd = {k: v.detach().clone() for k, v in model.state_dict().items()}
    keep = [0, 1, 3, 4]                                   # dp_x, dp_y of the older, then the newer sample
    sd["levels.0.weight"] = sd["levels.0.weight"][:, keep].contiguous()
    m2.load_state_dict(sd)
    m2.eval()
    return m2


# ------------------------------------------------------------------ input pipeline
def input_channels(dp_um, f_est=None, c_in=C_IN):
    """Per-tick channels (n, c_in) in model units (before windowing); f_est is not used when c_in == 2."""
    x = np.empty((len(dp_um), c_in), np.float32)
    x[:, :2] = np.clip(dp_um, -C.IN_CLIP_UM, C.IN_CLIP_UM) / C.S_IN
    if c_in == 3:
        x[:, 2] = np.clip((np.asarray(f_est, np.float64) - C.F_REF_HZ) * C.F_GAIN, -C.IN_CLIP_UM, C.IN_CLIP_UM) / C.S_IN
    return x


def gather_windows(ch, idx):
    """ch: (N, c_in) per-tick channels; idx: (B,) newest tick of each window (>= W-1).
    Returns (B, W, c_in); a 3rd (f_est) channel is broadcast from the newest tick."""
    off = np.arange(-(C.W - 1), 1)
    win = ch[idx[:, None] + off[None, :]]
    if ch.shape[1] > 2:
        win[:, :, 2] = ch[idx, 2][:, None]
    return win


def rec_windows(rec, c_in=C_IN):
    """All windows of one recording, (K, W, c_in); ticks k < W-1 are zero-padded (never scored)."""
    ch = input_channels(rec["dp_um"], rec.get("f_est"), c_in)
    pad = np.zeros((C.W - 1, c_in), np.float32)
    chp = np.vstack([pad, ch])
    idx = np.arange(len(ch)) + (C.W - 1)
    return gather_windows(chp, idx)


@torch.no_grad()
def predict(model, rec, batch=32768):
    model.eval()
    X = rec_windows(rec, model.c_in)
    if model.c_in == 3 and not getattr(model, "use_fest", True):
        X[:, :, 2] = 0.0
    out = np.empty((len(X), 2), np.float64)
    for a in range(0, len(X), batch):
        out[a:a + batch] = model(torch.from_numpy(X[a:a + batch])).numpy()
    return out * C.S_OUT


# ------------------------------------------------------------------ streaming alternative
def stream_reference(model, ch):
    """Streaming evaluation of the same weights: at every tick each level computes
    one new position from its input at t and t - 2**(l-1) (cached).  With the f_est
    channel constant, or absent (2 channels), this equals the window (tree) evaluation
    at every tick >= W-1.  ch: (N, c_in) per-tick channels.  Returns (N, 2) in model units."""
    Ws = [(m.weight.detach().numpy().astype(np.float64), m.bias.detach().numpy().astype(np.float64))
          for m in model.levels]
    Wh = (model.head.weight.detach().numpy().astype(np.float64), model.head.bias.detach().numpy().astype(np.float64))
    Wo = (model.out.weight.detach().numpy().astype(np.float64), model.out.bias.detach().numpy().astype(np.float64))
    N = len(ch)
    seqs = [np.asarray(ch, np.float64)]
    for l, (w, b) in enumerate(Ws):
        d = 2 ** l
        x = seqs[-1]
        prev = np.vstack([np.zeros((d, x.shape[1])), x[:-d]])
        seqs.append(np.maximum(np.concatenate([prev, x], axis=1) @ w.T + b, 0.0))
    h = np.maximum(seqs[-1] @ Wh[0].T + Wh[1], 0.0)
    return h @ Wo[0].T + Wo[1]
