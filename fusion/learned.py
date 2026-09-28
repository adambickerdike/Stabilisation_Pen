r"""Learned causal estimator: a streaming GRU on IMU + page-sensor inputs, trained on P1 runs (SIMULATION).

Inputs (per network step, 1 kHz, all causal: a sample enters once it is available):
  0-1  mean page-frame nib acceleration of the IMU samples that arrived during the step (m/s^2,
       fusion.sensors, gyroscope-compensated board IMU), scaled 1/(1 m/s^2)
  2-3  page-sensor increment between the two latest available samples if a new one arrived
       (units of 10 um), else 0
  4    1 if a new page-sensor sample arrived during the step
  5    page sensor valid (lift < 0.8 mm)
  6    axial contact flag
Output: d_hat(t_k + h + tau_lp), the oracle's housing disturbance (p_H - clean p_H), units of 100 um;
h = 2 ms covers the stage lag and the zero-order hold over the next network period (ticks at 2 kHz
use the latest network output); tau_lp = 3.75 ms is the low-frequency group delay of the 60 Hz
2nd-order output low-pass applied at the ticks (estimate jitter near the 192 Hz stage resonance
dithers the pen's friction in P1, see fusion/tune.py).
Model: GRU (hidden H) + linear head.  MAC per step 3 H (I + H) + 3 H + 2 H (I = 7).
Training data (fusion.data.draw_spec): domain-randomised pens, hands and writers (tilt 35-75 deg,
user force 0.5-2 N, hand impedance over config/parameters.yaml `hand` ranges, skid friction
0.06-0.2, handwriting size, slant and speed) with randomised tremor (3-14 Hz, 0.05-0.6 mm peak,
harmonic 0-0.4, amplitude and frequency drift, ellipticity, orientation, onset), plus the same
writing without tremor (false-correction penalty: loss weight LAMBDA_FC on d_hat^2 there); 25 % of
the pairs use the nominal pen and hand.  Sensor noise, IMU bias and the pen-rotation parameters
(rho_t, rho_w, psi) are re-drawn per augmentation.  Seeds: training 6000 + i, validation 9000-9011;
never the test seeds 200-203 or the aiguide writers.
"""
from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import BUILD, RESULTS, TRAIN_SEEDS_BASE, VAL_SEEDS
from . import data as FD
from . import sensors as S

NET_HZ = 1000.0
N_IN = 7
ACC_S = 1.0          # m/s^2 per unit
POS_S = 10e-6        # m per unit (increments)
OUT_S = 100e-6       # m per unit
H_DEFAULT = 2e-3
LP_HZ = 60.0
LAMBDA_FC = 4.0
MODEL_DIR = os.path.join(RESULTS, "model")


# ------------------------------------------------------------------ features
def features(st: S.Streams, rate: float = NET_HZ) -> Tuple[np.ndarray, np.ndarray]:
    """(X (K, N_IN) float32, t_k (K,)) for network steps t_k = k / rate up to the last tick."""
    t_end = float(st.tick_t[-1])
    tk = np.arange(0.0, t_end + 1e-12, 1.0 / rate)
    K = len(tk)
    X = np.zeros((K, N_IN), np.float32)
    # accelerometer: mean of the samples that became available in (t_{k-1}, t_k]
    ia = np.searchsorted(st.acc_av, tk, side="right")
    cs = np.vstack([np.zeros((1, 2)), np.cumsum(st.acc, axis=0)])
    i0 = np.r_[0, ia[:-1]]
    cnt = ia - i0
    acc = np.zeros((K, 2))
    ok = cnt > 0
    acc[ok] = (cs[ia[ok]] - cs[i0[ok]]) / cnt[ok, None]
    # hold the previous value where no sample arrived
    last = np.maximum.accumulate(np.where(ok, np.arange(K), 0))
    acc = acc[last]
    X[:, 0:2] = acc / ACC_S
    # page sensor: latest available sample
    jp = np.searchsorted(st.pos_av, tk, side="right") - 1
    jprev = np.r_[-1, jp[:-1]]
    new = (jp > jprev) & (jp >= 0)
    valid = np.where(jp >= 0, st.pos_ok[np.maximum(jp, 0)], 0.0)
    # increment since the sample that was latest at the previous step (covers steps in which two samples arrived)
    prev_idx = np.where(new, jprev, 0)
    has_prev = new & (jprev >= 0)
    dp = np.zeros((K, 2))
    both = has_prev & (st.pos_ok[np.maximum(jp, 0)] > 0.5) & (st.pos_ok[np.maximum(prev_idx, 0)] > 0.5)
    dp[both] = st.pos[jp[both]] - st.pos[prev_idx[both]]
    X[:, 2:4] = np.clip(dp / POS_S, -50, 50)
    X[:, 4] = new.astype(np.float32)
    X[:, 5] = valid
    jc = np.searchsorted(st.con_av, tk, side="right") - 1
    X[:, 6] = np.where(jc >= 0, st.con[np.maximum(jc, 0)], 0.0)
    return X, tk


def targets(tk: np.ndarray, rec1: S.Record, rec0: Optional[S.Record], h: float = H_DEFAULT):
    """(y (K, 2) in OUT_S units, mask (K,)): d(t_k + h), weighted where the nib is in contact after 0.3 s."""
    if rec0 is None:
        y = np.zeros((len(tk), 2), np.float32)
        rec = rec1
    else:
        y = (S.truth_at(tk + h, rec1, rec0) / OUT_S).astype(np.float32)
        rec = rec1
    con = np.interp(tk + h, rec.t, rec.contact) > 0.5
    return y, (con & (tk > 0.3)).astype(np.float32)


# ------------------------------------------------------------------ model
def build_model(hidden: int = 48):
    import torch
    from torch import nn

    class GRUEst(nn.Module):
        def __init__(self, hidden):
            super().__init__()
            self.hidden = hidden
            self.gru = nn.GRU(N_IN, hidden, batch_first=True)
            self.head = nn.Linear(hidden, 2)
            nn.init.normal_(self.head.weight, std=0.01)
            nn.init.zeros_(self.head.bias)

        def forward(self, x, h0=None):
            y, h = self.gru(x, h0)
            return self.head(y), h

    return GRUEst(hidden)


def macs_per_step(hidden: int) -> int:
    return 3 * hidden * (N_IN + hidden) + 3 * hidden * hidden * 0 + 3 * hidden * 2 + 2 * hidden


def n_params(hidden: int) -> int:
    return 3 * hidden * (N_IN + hidden) + 6 * hidden + 2 * hidden + 2


# ------------------------------------------------------------------ training data
def _sensor_cfg(rng, page: str = "1k") -> S.SensorConfig:
    cfg = S.config(page=page, comp="gyro", rho_t=float(rng.uniform(-0.5, 1.5)), rho_w=float(rng.uniform(0.0, 1.0)),
                   psi_t=float(rng.uniform(-math.pi / 2, math.pi / 2)))
    return cfg


def _spec(i: int, kind: str):
    base = TRAIN_SEEDS_BASE if kind == "train" else 0
    seed = base + i if kind == "train" else VAL_SEEDS[i % len(VAL_SEEDS)] + 100 * (i // len(VAL_SEEDS))
    spec = FD.draw_spec(seed)
    if (seed % 4) == 0:                     # 25 % nominal pen and hand (the test configuration), randomised tremor/writing
        spec.mu_skid = None
        spec.hand = {}
        spec.theta_deg = 50.0
        spec.N0 = 1.0
    return spec


def _lp_delay(fc):
    return 0.0 if fc <= 0 else math.sqrt(2.0) / (2.0 * math.pi * fc)


def _make_pair(args):
    i, kind, n_aug, page, h = args
    spec = _spec(i, kind)
    r1, r0 = FD.pair_records(spec)
    rng = np.random.default_rng(spec.seed * 7 + 1)
    out = []
    for a in range(n_aug):
        for rec, rc0 in ((r1, r0), (r0, None)):
            pg = page if page != "mix" else ("1k" if rng.random() < 0.5 else "120")
            st = S.make_streams(rec, _sensor_cfg(rng, pg), int(rng.integers(1 << 30)))
            X, tk = features(st)
            y, m = targets(tk, rec, rc0, h)
            out.append((X, y, m, rc0 is None))
    return out


def dataset(n: int, kind: str, n_aug: int = 2, page: str = "1k", h: float = H_DEFAULT, workers: int = 2):
    """Sequences (X, y, mask, is_clean); the target horizon includes the output low-pass's group delay."""
    jobs = [(i, kind, n_aug, page, h + _lp_delay(LP_HZ)) for i in range(n)]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            parts = list(ex.map(_make_pair, jobs, chunksize=4))
    else:
        parts = [_make_pair(j) for j in jobs]
    return [x for p in parts for x in p]


# ------------------------------------------------------------------ training
def train(n_train: int = 400, n_val: int = 24, hidden: int = 48, epochs: int = 14, seq: int = 1500, batch: int = 32,
          lr: float = 3e-3, page: str = "1k", h: float = H_DEFAULT, threads: int = 2, max_minutes: float = 40.0,
          seed: int = 7, workers: int = 2, tag: str = "", log=print) -> Dict:
    import torch
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    t0 = time.time()
    tr = dataset(n_train, "train", 2, page, h, workers)
    va = dataset(n_val, "val", 1, page, h, workers)
    t_data = time.time() - t0
    log(f"[learned] data: {len(tr)} train sequences, {len(va)} val sequences, {t_data:.0f} s")
    model = build_model(hidden)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    K = min(x[0].shape[0] for x in tr)
    steps_per_epoch = max(1, (max(1, K // seq) * len(tr)) // batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * steps_per_epoch, pct_start=0.15)
    burn = 300

    reps = max(1, K // seq)

    def batch_iter():
        order = np.concatenate([rng.permutation(len(tr)) for _ in range(reps)])     # about K/seq crops per sequence
        for b0 in range(0, len(order) - batch + 1, batch):
            idx = order[b0:b0 + batch]
            st = rng.integers(0, max(1, K - seq - burn), size=len(idx))
            xb = np.stack([tr[i][0][s:s + seq + burn] for i, s in zip(idx, st)])
            yb = np.stack([tr[i][1][s:s + seq + burn] for i, s in zip(idx, st)])
            mb = np.stack([tr[i][2][s:s + seq + burn] for i, s in zip(idx, st)])
            wb = np.array([LAMBDA_FC if tr[i][3] else 1.0 for i in idx], np.float32)
            mb[:, :burn] = 0.0
            yield (torch.from_numpy(xb), torch.from_numpy(yb), torch.from_numpy(mb) * torch.from_numpy(wb)[:, None])

    def val_score():
        model.eval()
        num = den = fc = n_fc = 0.0
        with torch.no_grad():
            for X, y, m, clean in va:
                yh, _ = model(torch.from_numpy(X[None]))
                yh = yh[0].numpy()
                mm = m > 0
                if clean:
                    fc += float(np.sum(yh[mm] ** 2)); n_fc += mm.sum()
                else:
                    num += float(np.sum((yh[mm] - y[mm]) ** 2)); den += float(np.sum(y[mm] ** 2))
        model.train()
        return math.sqrt(num / max(den, 1e-12)), math.sqrt(fc / max(n_fc, 1)) * OUT_S * 1e6

    best = (1e9, None, -1)
    hist = []
    stop = False
    for ep in range(epochs):
        tl = 0.0; nb = 0
        for xb, yb, wb in batch_iter():
            yh, _ = model(xb)
            loss = (wb[..., None] * (yh - yb) ** 2).sum() / wb.sum().clamp_min(1.0)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            if sched.last_epoch < sched.total_steps - 1:
                sched.step()
            tl += float(loss); nb += 1
            if (time.time() - t0) / 60.0 > max_minutes:
                stop = True
                break
        rr, fc = val_score()
        score = rr + 2.0 * max(0.0, fc / 25.0 - 1.0)
        hist.append({"epoch": ep, "train_loss": tl / max(nb, 1), "val_rr": rr, "val_fc_um": fc, "score": score,
                     "elapsed_s": time.time() - t0})
        log(f"[learned] epoch {ep}: loss {tl / max(nb, 1):.4f} val RR {rr:.3f} FC {fc:.1f} um ({time.time() - t0:.0f} s)")
        if score < best[0]:
            best = (score, {k: v.detach().clone() for k, v in model.state_dict().items()}, ep)
        if stop:
            break
    model.load_state_dict(best[1])
    os.makedirs(MODEL_DIR, exist_ok=True)
    name = f"gru{hidden}_{page}{tag}"
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, name + ".pt"))
    cfg = {"name": name, "hidden": hidden, "n_in": N_IN, "net_hz": NET_HZ, "horizon_s": h, "lp_hz": LP_HZ,
           "target_horizon_s": h + _lp_delay(LP_HZ), "page": page,
           "acc_scale": ACC_S, "pos_scale": POS_S, "out_scale": OUT_S, "lambda_fc": LAMBDA_FC, "n_train_pairs": n_train,
           "n_val_pairs": n_val, "best_epoch": best[2], "history": hist, "train_seeds": f"{TRAIN_SEEDS_BASE}..{TRAIN_SEEDS_BASE + n_train - 1}",
           "val_seeds": list(VAL_SEEDS), "data_s": t_data, "total_s": time.time() - t0, "threads": threads,
           "macs_per_step": macs_per_step(hidden), "params": n_params(hidden), "seq": seq, "batch": batch, "lr": lr}
    with open(os.path.join(MODEL_DIR, name + ".json"), "w") as f:
        json.dump(cfg, f, indent=1)
    return cfg


# ------------------------------------------------------------------ inference (estimator interface)
_MODELS: Dict = {}


def load_model(name: str):
    if name not in _MODELS:
        import torch
        torch.set_num_threads(1)
        cfg = json.load(open(os.path.join(MODEL_DIR, name + ".json")))
        m = build_model(cfg["hidden"])
        m.load_state_dict(torch.load(os.path.join(MODEL_DIR, name + ".pt"), map_location="cpu"))
        m.eval()
        _MODELS[name] = (m, cfg)
    return _MODELS[name]


def estimate(st: S.Streams, params: Optional[Dict] = None, extra: Optional[Dict] = None):
    import torch
    from scipy.signal import butter, lfilter
    p = {"model": "gru48_1k", "g": 1.0}
    if params:
        p.update(params)
    m, cfg = load_model(p["model"])
    X, tk = features(st, cfg["net_hz"])
    with torch.no_grad():
        y, _ = m(torch.from_numpy(X[None]))
    d = y[0].numpy().astype(np.float64) * cfg["out_scale"]
    # ticks use the latest network output (computed at t_k from samples available by t_k)
    j = np.clip(np.searchsorted(tk, st.tick_t, side="right") - 1, 0, len(tk) - 1)
    out = p["g"] * d[j]
    lp = float(cfg.get("lp_hz", 0.0))
    if lp > 0:                                  # causal 2nd-order output low-pass (its delay is in the target)
        Ts = float(st.tick_t[1] - st.tick_t[0])
        b, a = butter(2, lp, fs=1.0 / Ts)
        out = lfilter(b, a, out, axis=0)
    return out, {"params": p, "model_cfg": {k: cfg.get(k) for k in ("name", "hidden", "horizon_s", "lp_hz", "macs_per_step", "params")}}
