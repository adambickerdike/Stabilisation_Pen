"""Task 2 (and the learned fixed-lag estimator of task 1): learned tremor estimators, trained on domain-randomised
synthetic writers (data.py) and selected on the tuning writers.

Evidence status: SIMULATION (training and evaluation on synthetic writers and tremor, model HW1).

Models (all causal in time; outputs at 500 Hz):
  tcn     causal dilated temporal convolution network (Bai et al. 2018) on the 7 sensor features of fusion.learned
          (accelerometer, page-sensor increments, new-sample flag, page valid, axial contact); receptive field about
          1 s; outputs the tremor displacement of the handle at t + delta - lag for the lags of data.LAGS (lag 0 is
          the causal estimate, the others are fixed-lag estimates for delayed ink)
  hybrid  a Kalman-network hybrid: the same network with the model-based stack's quantities as extra inputs (the
          tremor-line detector's gate, peak ratio and line amplitude, the amplitude gate, the ungated fixed-lag RTS
          estimates) and a residual output on the model-based stack's own estimate (the gated RTS estimate with the
          Rev H tracker as fallback, stage D2b's amplitude gate): estimate = model-based + network correction
  ctx     tcn conditioned on the user's calibration (tremor frequency and amplitude from the 20 s calibration, two
          constant inputs): per-user adaptation without retraining
  transformer  a small causal transformer (causal convolution front end, 2 self-attention layers over the last
          0.5 s with ALiBi distance biases (Press et al. 2022), 500 Hz), the same inputs and outputs as tcn
Loss: squared error of the estimate on pen-down steps + lambda_fc x squared output on tremor-free samples (the
false-correction penalty of fusion.learned).
"""
from __future__ import annotations

import math
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths
from . import data as DA

ensure_paths()
from fusion import learned as FL  # noqa: E402

ACC_S = 1.0          # m/s^2 per unit
POS_S = 10e-6        # m per unit (page-sensor increments)
OUT_S = 100e-6       # m per unit (outputs)
N_IN = 7


def _torch():
    import torch
    return torch


def make_tcn(n_in: int, n_out: int, ch: int = 32, k: int = 3, dil=(1, 2, 4, 8, 16, 32, 64, 128), residual_in: int = 0):
    torch = _torch()
    nn = torch.nn

    class CausalConv(nn.Module):
        def __init__(self, cin, cout, k, d):
            super().__init__()
            self.pad = (k - 1) * d
            self.conv = nn.Conv1d(cin, cout, k, dilation=d)

        def forward(self, x):
            return self.conv(nn.functional.pad(x, (self.pad, 0)))

    class Block(nn.Module):
        def __init__(self, d):
            super().__init__()
            self.c1 = CausalConv(ch, ch, k, d)
            self.c2 = nn.Conv1d(ch, ch, 1)

        def forward(self, x):
            return x + self.c2(nn.functional.gelu(self.c1(x)))

    class TCN(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = nn.Conv1d(n_in, ch, 1)
            self.blocks = nn.ModuleList([Block(d) for d in dil])
            self.head = nn.Conv1d(ch, n_out, 1)
            nn.init.normal_(self.head.weight, std=0.01)
            nn.init.zeros_(self.head.bias)
            self.cfg = {"n_in": n_in, "n_out": n_out, "ch": ch, "k": k, "dil": list(dil), "residual_in": residual_in}
            self.rf = 1 + sum((k - 1) * d for d in dil)

        def forward(self, x):                      # x: (B, T, n_in) -> (B, T, n_out)
            h = self.inp(x.transpose(1, 2))
            for b in self.blocks:
                h = b(h)
            y = self.head(h).transpose(1, 2)
            if residual_in:                        # hybrid: the last residual_in inputs are the base estimate
                y = y + x[..., -residual_in:]
            return y

    return TCN()


def tcn_macs(cfg: Dict) -> int:
    ch, k = cfg["ch"], cfg["k"]
    return int(cfg["n_in"] * ch + len(cfg["dil"]) * (k * ch * ch + ch * ch) + ch * cfg["n_out"])


def tcn_params(model) -> int:
    return int(sum(p.numel() for p in model.parameters()))


def make_transformer(n_in: int, n_out: int, d: int = 48, heads: int = 4, layers: int = 2, window: int = 256,
                     ff: int = 96, residual_in: int = 0):
    """Causal transformer: two causal convolutions (kernel 5, dilations 1 and 2) then `layers` pre-norm self-attention
    blocks restricted to the last `window` steps, with ALiBi linear distance biases per head (no absolute positions,
    so it runs on a sliding window)."""
    torch = _torch()
    nn = torch.nn

    class CausalConv(nn.Module):
        def __init__(self, cin, cout, k, dd):
            super().__init__()
            self.pad = (k - 1) * dd
            self.conv = nn.Conv1d(cin, cout, k, dilation=dd)

        def forward(self, x):
            return self.conv(nn.functional.pad(x, (self.pad, 0)))

    class Attn(nn.Module):
        def __init__(self):
            super().__init__()
            self.n1 = nn.LayerNorm(d)
            self.qkv = nn.Linear(d, 3 * d)
            self.o = nn.Linear(d, d)
            self.n2 = nn.LayerNorm(d)
            self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

        def forward(self, x, bias):
            B, T, _ = x.shape
            h = self.n1(x)
            q, k, v = self.qkv(h).view(B, T, 3, heads, d // heads).permute(2, 0, 3, 1, 4)
            a = torch.softmax(q @ k.transpose(-1, -2) / math.sqrt(d // heads) + bias[:, :T, :T], dim=-1)
            x = x + self.o((a @ v).transpose(1, 2).reshape(B, T, d))
            return x + self.ff(self.n2(x))

    class TF(nn.Module):
        def __init__(self):
            super().__init__()
            self.c1 = CausalConv(n_in, d, 5, 1)
            self.c2 = CausalConv(d, d, 5, 2)
            self.blocks = nn.ModuleList([Attn() for _ in range(layers)])
            self.head = nn.Linear(d, n_out)
            nn.init.normal_(self.head.weight, std=0.01)
            nn.init.zeros_(self.head.bias)
            self.slopes = torch.tensor([2.0 ** (-8.0 * (i + 1) / heads) for i in range(heads)])
            self.cfg = {"arch": "transformer", "n_in": n_in, "n_out": n_out, "d": d, "heads": heads, "layers": layers,
                        "window": window, "ff": ff, "residual_in": residual_in}
            self.rf = window * layers + 13
            self._bias = {}

        def bias(self, T):
            if T not in self._bias:
                i = torch.arange(T)[:, None]; j = torch.arange(T)[None, :]
                dist = (i - j).float()
                b = -self.slopes[:, None, None] * dist[None]
                b = b.masked_fill((j > i)[None] | (dist >= window)[None], float("-inf"))
                self._bias = {T: b}
            return self._bias[T]

        def forward(self, x):                          # (B, T, n_in) -> (B, T, n_out)
            h = self.c2(nn.functional.gelu(self.c1(x.transpose(1, 2)))).transpose(1, 2)
            b = self.bias(x.shape[1])
            for blk in self.blocks:
                h = blk(h, b)
            y = self.head(h)
            if residual_in:
                y = y + x[..., -residual_in:]
            return y

    return TF()


def model_macs(cfg: Dict) -> int:
    """Multiply-accumulates per 500 Hz output step (streaming inference)."""
    if cfg.get("arch") == "transformer":
        d, w, L, ff = cfg["d"], cfg["window"], cfg["layers"], cfg["ff"]
        return int(5 * cfg["n_in"] * d + 5 * d * d + L * (4 * d * d + 2 * w * d + 2 * d * ff) + d * cfg["n_out"])
    return tcn_macs(cfg)


def build_model(cfg: Dict):
    if cfg.get("arch") == "transformer":
        return make_transformer(cfg["n_in"], cfg["n_out"], d=cfg["d"], heads=cfg["heads"], layers=cfg["layers"],
                                window=cfg["window"], ff=cfg["ff"], residual_in=cfg["residual_in"])
    return make_tcn(cfg["n_in"], cfg["n_out"], ch=cfg["ch"], k=cfg["k"], dil=cfg["dil"], residual_in=cfg["residual_in"])


# ------------------------------------------------------------------ inputs
def inputs(X: np.ndarray, extra: Optional[np.ndarray] = None, ctx: Optional[Sequence[float]] = None) -> np.ndarray:
    """Network inputs: the 7 fusion features (already scaled by fusion.learned: acc / 1 m/s^2, increments / 10 um)
    plus optional extra channels (hybrid: RTS estimates / 100 um and the gate) and constant context channels."""
    Z = [np.asarray(X, np.float32)]
    if ctx is not None:
        Z.append(np.tile(np.asarray(ctx, np.float32)[None, :], (len(X), 1)))
    if extra is not None:
        Z.append(np.asarray(extra, np.float32))
    return np.concatenate(Z, axis=1)


def base_estimate(mb: Dict, amp_lo: float = 0.0, amp_hi: float = 0.0, lags: Sequence[float] = DA.LAGS):
    """The model-based stack's estimate at the network steps (as delayed.estimates/command build it): the listening
    RTS estimate D at each lag weighted by g = hysteresis gate x amplitude gate, the Rev H tracker's causal estimate
    dh(t - lag) for the rest.  Returns (B (T, L, 2), g (T,))."""
    g = np.asarray(mb["gate"], float)
    if amp_hi > amp_lo:
        g = g * np.clip((np.asarray(mb["amp"], float) - amp_lo) / (amp_hi - amp_lo), 0.0, 1.0)
    dh = np.asarray(mb["dh"], float)
    T = len(g)
    t = np.arange(T) / DA.NET_HZ
    B = np.zeros((T, len(lags), 2))
    for i, lag in enumerate(lags):
        fb = np.column_stack([np.interp(t - lag, t, dh[:, 0], left=0.0), np.interp(t - lag, t, dh[:, 1], left=0.0)])
        B[:, i] = g[:, None] * np.asarray(mb["D"][:, i], float) + (1.0 - g[:, None]) * fb
    return B, g


def make_inputs(mode: str, X: np.ndarray, mb: Optional[Dict] = None, ctx: Optional[Sequence[float]] = None,
                amp_gate: Sequence[float] = (0.0, 0.0)) -> np.ndarray:
    """Network inputs of each mode (see the module docstring); ctx = (f Hz, amplitude m) from the calibration."""
    if mode in ("tcn", "transformer"):
        return inputs(X)
    if mode == "ctx":
        return inputs(X, ctx=ctx_features(*(ctx or (0.0, 0.0))))
    if mode == "hybrid":
        T = len(X)
        B, g = base_estimate(mb, *amp_gate)
        extra = np.column_stack([mb["gate"], np.asarray(mb["ratio"]) / 10.0, np.asarray(mb["amp"]) / 1e-3, g,
                                 np.asarray(mb["D"]).reshape(T, -1) / OUT_S, B.reshape(T, -1) / OUT_S])
        return inputs(X, extra=np.clip(extra, -100, 100))
    raise KeyError(mode)


def ctx_features(f_hz: float, amp_m: float) -> List[float]:
    """Calibration context: frequency (Hz / 10) and log amplitude (log10(amp / 1 mm)); zeros = no tremor found."""
    if amp_m <= 0:
        return [0.0, -1.5]
    return [f_hz / 10.0, math.log10(max(amp_m, 1e-5) / 1e-3)]


# ------------------------------------------------------------------ training
def train(train_set: List[Dict], val_fn: Callable, cfg: Dict, minutes: float = 15.0, batch: int = 24, seq: int = 1500,
          lr: float = 2e-3, lambda_fc: float = 4.0, seed: int = 0, log: Callable = print, mode: str = "tcn") -> Tuple[object, Dict]:
    """Time-boxed training; the model with the best validation score (val_fn(model) -> float, lower is better) is kept."""
    torch = _torch()
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    n_lags = train_set[0]["Y"].shape[1]
    n_in = train_set[0]["Z"].shape[1]
    res_in = 2 * n_lags if mode == "hybrid" else 0
    if mode == "transformer":
        model = make_transformer(n_in, 2 * n_lags, d=cfg.get("d", 48), heads=cfg.get("heads", 4), layers=cfg.get("layers", 2),
                                 window=cfg.get("window", 256), ff=cfg.get("ff", 96), residual_in=res_in)
    else:
        model = make_tcn(n_in, 2 * n_lags, ch=cfg.get("ch", 32), k=cfg.get("k", 3), dil=cfg.get("dil", (1, 2, 4, 8, 16, 32, 64, 128)),
                         residual_in=res_in)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    warm = min(model.rf, seq // 3)
    t0 = time.time(); t_end = t0 + minutes * 60.0
    step, hist = 0, []
    best = (float("inf"), None)
    lengths = np.array([len(s["Z"]) for s in train_set])
    usable = [i for i, L in enumerate(lengths) if L > seq + 10]
    while time.time() < t_end:
        frac = (time.time() - t0) / (t_end - t0)
        for gp in opt.param_groups:
            gp["lr"] = lr * min(1.0, (step + 1) / 100) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(frac, 1.0))))
        xs, ys, ms, fcs = [], [], [], []
        for _ in range(batch):
            i = usable[int(rng.integers(len(usable)))]
            s = train_set[i]
            a = int(rng.integers(0, len(s["Z"]) - seq))
            xs.append(s["Z"][a:a + seq]); ys.append(s["Y"][a:a + seq].reshape(seq, -1) / OUT_S)
            m = s["mask"][a:a + seq].copy(); m[:warm] = 0.0
            ms.append(m); fcs.append(0.0 if s["spec"]["amp"] > 0 else 1.0)
        x = torch.from_numpy(np.stack(xs)); y = torch.from_numpy(np.stack(ys).astype(np.float32))
        m = torch.from_numpy(np.stack(ms)); fc = torch.from_numpy(np.array(fcs, np.float32))
        out = model(x)
        err = ((out - y) ** 2).sum(-1)                          # (B, T)
        w_t = m * (1.0 - fc)[:, None]
        loss_t = (err * w_t).sum() / w_t.sum().clamp(min=1.0)
        w_f = m * fc[:, None]
        loss_f = ((out ** 2).sum(-1) * w_f).sum() / w_f.sum().clamp(min=1.0)
        loss = loss_t + lambda_fc * loss_f
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        if step % 150 == 0:
            model.eval()
            v = float(val_fn(model))
            model.train()
            hist.append({"step": step, "loss": float(loss), "loss_tremor": float(loss_t), "loss_fc": float(loss_f),
                         "val": v, "minutes": (time.time() - t0) / 60.0})
            log(f"  [{mode}] step {step} loss {float(loss):.3f} (tremor {float(loss_t):.3f}, fc {float(loss_f):.4f}) val {v:.1f}")
            if v < best[0]:
                best = (v, {k: t.detach().clone() for k, t in model.state_dict().items()})
    if best[1] is not None:
        model.load_state_dict(best[1])
    model.eval()
    return model, {"cfg": model.cfg, "mode": mode, "steps": step, "minutes": (time.time() - t0) / 60.0, "history": hist,
                   "best_val": best[0], "n_params": tcn_params(model), "macs_per_step": model_macs(model.cfg),
                   "lambda_fc": lambda_fc, "batch": batch, "seq": seq, "lr": lr, "receptive_field_steps": model.rf,
                   "n_train_samples": len(train_set)}


def predict(model, Z: np.ndarray, chunk: int = 1024) -> np.ndarray:
    """(T, n_lags, 2) tremor estimates (m) for one record (causal; the transformer runs on sliding chunks whose
    history covers its attention window, which gives the same outputs as streaming inference)."""
    torch = _torch()
    Z = np.asarray(Z, np.float32)
    with torch.no_grad():
        if getattr(model, "cfg", {}).get("arch") != "transformer" or len(Z) <= chunk:
            y = model(torch.from_numpy(Z)[None])[0].numpy()
        else:
            hist = model.cfg["window"] * model.cfg["layers"] + 16
            parts = []
            for a in range(0, len(Z), chunk):
                a0 = max(0, a - hist)
                yy = model(torch.from_numpy(Z[a0:a + chunk])[None])[0].numpy()
                parts.append(yy[a - a0:])
            y = np.concatenate(parts, axis=0)
    return y.reshape(len(Z), -1, 2) * OUT_S


def on_lag_grid(D_lags: np.ndarray, lags_src: Sequence[float], lag_grid: Sequence[float]) -> np.ndarray:
    """Interpolate estimates given at lags_src onto lag_grid (clamped beyond the largest)."""
    src = np.asarray(lags_src, float)
    out = np.zeros((D_lags.shape[0], len(lag_grid), 2))
    for j, lg in enumerate(lag_grid):
        lg = min(max(lg, src[0]), src[-1])
        i1 = int(np.searchsorted(src, lg, side="left"))
        i1 = min(max(i1, 1), len(src) - 1)
        i0 = i1 - 1
        w = (lg - src[i0]) / max(src[i1] - src[i0], 1e-12)
        out[:, j] = (1 - w) * D_lags[:, i0] + w * D_lags[:, i1]
    return out


class LearnedEstimator:
    """A trained model as the estimator of delayed.estimates (estimator "learned") or as a causal tracker: the network
    runs once over the record (the output at step k uses sensor data available by t_k only), the outputs are held
    (zero-order) to the estimator output times and interpolated between the trained lags (clamped beyond 100 ms)."""

    def __init__(self, model, mode: str, pen, model_params: Optional[Dict] = None, amp_gate=(0.0, 0.0), ctx=None):
        self.model, self.mode, self.pen = model, mode, pen
        self.mp = model_params
        self.amp_gate = tuple(amp_gate)
        self.ctx = ctx
        self.last = None

    def outputs(self, st) -> Tuple[np.ndarray, np.ndarray]:
        X, tk = FL.features(st, DA.NET_HZ)
        mb = DA.model_based(st, self.pen, tk, self.mp["tremor"], self.mp["det"]) if self.mode == "hybrid" else None
        Y = predict(self.model, make_inputs(self.mode, X, mb, self.ctx, self.amp_gate))
        self.last = {"tk": tk, "Y": Y}
        return tk, Y

    def fixed_lag(self, st, lags, delta, t_out) -> np.ndarray:
        from handwriting import params as PR
        assert abs(delta - PR.servo_group_delay(self.pen)) < 1e-6, "trained for the Rev H servo delay"
        tk, Y = self.outputs(st)
        return hold_extrapolate(tk, on_lag_grid(Y, DA.LAGS, lags), t_out)


def hold_extrapolate(tk: np.ndarray, Y: np.ndarray, t_out) -> np.ndarray:
    """Causal resampling of step outputs to later times: the latest output at or before each time, linearly
    extrapolated from the two latest outputs (each output targets its own time + delta - lag, so the target moves with
    the time; the extrapolation error for a 10 Hz, 1 mm tremor is below about 10 um for 2 ms steps - CALCULATION)."""
    t_out = np.asarray(t_out, float)
    k = np.clip(np.searchsorted(tk, t_out + 1e-9, side="right") - 1, 0, len(tk) - 1)
    k0 = np.maximum(k - 1, 0)
    dt = np.maximum(tk[k] - tk[k0], 1e-12)
    w = np.where(k > k0, (t_out - tk[k]) / dt, 0.0)
    w = w.reshape((-1,) + (1,) * (Y.ndim - 1))
    return Y[k] + w * (Y[k] - Y[k0])
