"""Task 1: a small recogniser for letters AS THEY ARE WRITTEN, trained on real online handwriting (CALCULATION).

Data (real, public): UJI Pen Characters v2 lower-case letters (60 writers x 26 letters x 2 repetitions; CC BY 4.0).
  split (fixed before training, rules.py): the 40 'trn' writers -> 32 training + 8 tuning writers (sha256 of the writer
  id); the 20 'tst' writers are used only for the final tables.  UCI Character Trajectories (one other writer, another
  tablet, 20 single-stroke letters, real 200 Hz timing) is a cross-dataset test only.
Time: UJI stores points, not times.  ASSUMPTION (checked): the points are samples at a uniform rate (the speed-curvature
  exponent of the raw point sequence is 0.21, against 0.05 for the same letters resampled by arc length, CALC); the rate
  is set so that the median pen-down speed at a 3 mm x-height is 30 mm/s (adult phrase speed on paper 30.5 mm/s, LIT
  CON-20).  Time matters only for the tremor augmentation and for the latency in ms.
Input: the letter as it is being written, resampled every 0.1 x-height of pen path (the app knows the writer's x-height
  from calibration); per point (x, y) from the letter's first point, (dx, dy), and a pen flag (0 on the pen-up jump
  to the next stroke).  Nothing after the current point is used (streaming).
Model: a 2-layer GRU (hidden 96) with a linear read-out at every point; loss = cross-entropy at every prefix, so the
  posterior is meaningful while the letter is incomplete.  Language context (optional, at inference): the posterior is
  multiplied by the text predictor's next-letter distribution raised to a weight beta (tuned on the tuning writers).
Augmentation (training only): affine (slant, scale, rotation), sigma-lognormal variation of each stroke (ai2/synth.py,
  read-only: extract, perturb the lognormal parameters, regenerate), and tremor (4-12 Hz, elliptical, 0-0.4 x-height).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import BUILD_DIR, ensure_paths
from .common import log, stable_hash

ensure_paths()

LETTERS = "abcdefghijklmnopqrstuvwxyz"
L2I = {c: i for i, c in enumerate(LETTERS)}
XH_LETTERS = "acemnorsuvwxz"
STEP = 0.1                  # arc-length resampling step (x-height units)
XH_MM = 3.0                 # standard x-height for time and pen simulations (ASSUMPTION)
SPEED_MM_S = 30.0           # median pen-down speed at XH_MM (LIT CON-20, rounded; ASSUMPTION for UJI timing)
N_FEAT = 5
FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


# ============================================================================================ splits and scales
def split_of(writer: str) -> str:
    """'train' / 'tune' / 'test' (fixed rule: tst writers are test; trn writers with sha256 bucket < 20 are tuning)."""
    if writer.startswith("tst"):
        return "test"
    return "tune" if stable_hash("ai3-online:" + writer) < 20 else "train"


def writer_xheights(letters) -> Dict[str, float]:
    """Median ink height (mm) of each writer's x-height letters: the writer's x-height, as the calibration gives it."""
    hs: Dict[str, List[float]] = {}
    for L in letters:
        if L.char in XH_LETTERS:
            a = np.vstack(L.strokes)
            hs.setdefault(L.writer, []).append(float(np.ptp(a[:, 1])))
    return {w: float(np.median(v)) for w, v in hs.items()}


def sample_dt(letters, xh: Dict[str, float]) -> float:
    """Seconds per UJI point such that the median pen-down speed at XH_MM is SPEED_MM_S (ASSUMPTION, see module doc)."""
    sp = []
    for L in letters:
        f = XH_MM / xh[L.writer]
        for s in L.strokes:
            if len(s) > 2:
                sp.append(np.median(np.hypot(*np.diff(s, axis=0).T)) * f)
    return float(np.median(sp) / SPEED_MM_S)


# ============================================================================================ encoding
def _resample(P: np.ndarray, step: float) -> np.ndarray:
    seg = np.hypot(*np.diff(P, axis=0).T) if len(P) > 1 else np.zeros(0)
    s = np.r_[0.0, np.cumsum(seg)]
    if len(P) < 2 or s[-1] < 1e-9:
        return np.repeat(P[:1], 2, axis=0)
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    u = np.linspace(0.0, s[-1], n)
    return np.column_stack([np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])])


def encode(strokes: Sequence[np.ndarray], xh: float, step: float = STEP) -> Tuple[np.ndarray, np.ndarray]:
    """(T, 5) features and (T,) cumulative pen-down path fraction of a (possibly partial) letter.
    strokes in mm (or any unit with xh in the same unit)."""
    if not strokes:
        return np.zeros((0, N_FEAT), np.float32), np.zeros(0)
    o = np.asarray(strokes[0][0], float)
    pts, pen = [], []
    for k, s in enumerate(strokes):
        r = _resample((np.asarray(s, float) - o) / xh, step)
        pts.append(r)
        pen.append(np.r_[0.0 if k > 0 else 1.0, np.ones(len(r) - 1)])
    X = np.vstack(pts)
    pn = np.concatenate(pen)
    d = np.diff(np.vstack([X[:1], X]), axis=0)
    F = np.column_stack([X, d, pn]).astype(np.float32)
    seg = np.hypot(d[:, 0], d[:, 1]) * pn
    cum = np.cumsum(seg)
    frac = cum / max(cum[-1], 1e-9)
    return F, frac


# ============================================================================================ augmentation
def affine(strokes, rng) -> List[np.ndarray]:
    sh = rng.normal(0, 0.12)
    sx, sy = np.exp(rng.normal(0, 0.08)), np.exp(rng.normal(0, 0.08))
    th = rng.normal(0, 0.05)
    A = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) @ np.array([[sx, sh], [0, sy]])
    c = np.vstack(strokes).mean(0)
    return [(np.asarray(s) - c) @ A.T + c for s in strokes]


def add_tremor(strokes, rng, xh: float, dt: float, amp_xh: Tuple[float, float] = (0.0, 0.4)) -> List[np.ndarray]:
    """Elliptical tremor (4-12 Hz, minor/major 0.4, fixed axis, 15 % second harmonic) added along the letter's time
    course (pen-up gaps: 0.15 s between strokes).  amp in x-height units, peak."""
    A = rng.uniform(*amp_xh) * xh
    f = rng.uniform(4.0, 12.0)
    ax = rng.uniform(0, math.pi)
    u = np.array([math.cos(ax), math.sin(ax)]); v = np.array([-u[1], u[0]])
    ph = rng.uniform(0, 2 * math.pi)
    out, t0 = [], 0.0
    for s in strokes:
        s = np.asarray(s, float)
        t = t0 + np.arange(len(s)) * dt
        w = 2 * math.pi * f * t + ph
        d = A * (np.cos(w)[:, None] * u + 0.4 * np.sin(w)[:, None] * v + 0.15 * np.cos(2 * w)[:, None] * u)
        out.append(s + d)
        t0 = t[-1] + 0.15
    return out


@dataclass
class SLFit:
    """Sigma-lognormal fit of one letter (per stroke): parameters, start, time base (ai2/synth.py conventions)."""
    strokes: List[Tuple[np.ndarray, np.ndarray, np.ndarray]]   # (t at 200 Hz, P (m,6), start)
    snr: float


def sl_fit_letter(strokes: Sequence[np.ndarray], dt: float, max_nfev: int = 60) -> Optional[SLFit]:
    """Fit each stroke (resampled to ai2's 200 Hz time base under the uniform-rate ASSUMPTION).  max_nfev 60 instead
    of ai2's 400: median reconstruction SNR 29 dB instead of 30 dB on 20 training letters, 4x faster (CALC)."""
    from ai2 import synth as SY
    out, snrs = [], []
    for s in strokes:
        s = np.asarray(s, float)
        if len(s) < 6:
            return None
        tt = np.arange(len(s)) * dt
        t = np.arange(0.0, tt[-1] + 1e-9, 1.0 / SY.FS)
        if len(t) < 8:
            return None
        xy = np.column_stack([np.interp(t, tt, s[:, 0]), np.interp(t, tt, s[:, 1])])
        r = SY.extract(t, xy, max_nfev=max_nfev)
        if not len(r["P"]) or not np.isfinite(r["snr_db"]):
            return None
        out.append((t, r["P"], r["start"]))
        snrs.append(r["snr_db"])
    return SLFit(out, float(np.min(snrs)))


def sl_variant(fit: SLFit, rng, scale: float) -> List[np.ndarray]:
    from ai2 import synth as SY
    sp = {k: v * scale for k, v in SY.DEFAULT_SPREAD.items()}
    return [SY.trajectory(t, SY.perturb(P, rng, sp), start) for t, P, start in fit.strokes]


# ============================================================================================ model
def make_model(hidden: int = 96, layers: int = 2):
    import torch
    nn = torch.nn

    class OnlineRec(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = nn.Linear(N_FEAT, hidden)
            self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
            self.out = nn.Linear(hidden, len(LETTERS))
            self.cfg = {"hidden": hidden, "layers": layers}

        def forward(self, x, h=None):
            z = torch.tanh(self.inp(x))
            y, h = self.gru(z, h)
            return self.out(y), h

    return OnlineRec()


def n_params(model) -> int:
    return int(sum(p.numel() for p in model.parameters()))


def macs_per_point(cfg: Dict) -> int:
    """Multiply-accumulates per new point (CALC): input layer, GRU (3 gates x (in + hidden) x hidden per layer), head."""
    H, L = cfg["hidden"], cfg["layers"]
    return int(N_FEAT * H + L * 3 * (H + H) * H + H * len(LETTERS))


# ============================================================================================ training
@dataclass
class TrainSet:
    items: List[Dict]            # {'strokes' (x-height units), 'label', 'writer', 'sl': SLFit or None}
    dt_xh: float                 # seconds per original point (for tremor timing)


def build_items(letters, xh: Dict[str, float], split: str, sl_fits: Optional[Dict] = None) -> List[Dict]:
    out = []
    for i, L in enumerate(letters):
        if split_of(L.writer) != split:
            continue
        s = [np.asarray(x, float) / xh[L.writer] for x in L.strokes]
        out.append({"strokes": s, "label": L2I[L.char], "writer": L.writer, "key": f"{L.writer}-{L.rep}-{L.char}",
                    "sl": (sl_fits or {}).get(f"{L.writer}-{L.rep}-{L.char}")})
    return out


def augment(item: Dict, rng, cfg: Dict, dt: float) -> List[np.ndarray]:
    s = item["strokes"]
    if cfg.get("sl") and item.get("sl") is not None and rng.random() < 0.6:
        s = sl_variant(item["sl"], rng, rng.choice(cfg.get("sl_scales", (0.3, 0.6))))
        s = [x / 1.0 for x in s]
    if cfg.get("affine"):
        s = affine(s, rng)
    if cfg.get("tremor") and rng.random() < cfg.get("p_tremor", 0.5):
        s = add_tremor(s, rng, 1.0, dt, (0.02, cfg.get("tremor_max", 0.4)))
    if cfg.get("jitter"):
        s = [x + rng.normal(0, 0.01, x.shape) for x in s]
    return s


def _batch(seqs: List[np.ndarray], labels: List[int]):
    import torch
    T = max(len(q) for q in seqs)
    X = np.zeros((len(seqs), T, N_FEAT), np.float32)
    M = np.zeros((len(seqs), T), np.float32)
    for i, q in enumerate(seqs):
        X[i, :len(q)] = q
        M[i, :len(q)] = 1.0
    return torch.from_numpy(X), torch.from_numpy(M), torch.tensor(labels)


def train(train_items: List[Dict], val_items: List[Dict], cfg: Dict, minutes: float, dt: float, seed: int = 0,
          ckpt=None, log_every: float = 60.0):
    """Time-boxed training (resumable from ckpt: state_dict + optimiser + rng + elapsed)."""
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    model = make_model(cfg.get("hidden", 96), cfg.get("layers", 2))
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.get("lr", 3e-3), weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    state = {"elapsed": 0.0, "steps": 0, "hist": [], "best": (-1.0, None)}
    if ckpt is not None and ckpt.exists():
        st = torch.load(ckpt, weights_only=False)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"])
        rng.bit_generator.state = st["rng"]; state = st["state"]
        log(f"[online] resumed {ckpt.name} at {state['elapsed'] / 60:.1f} min, {state['steps']} steps")
    budget = minutes * 60.0
    t_start = time.time() - state["elapsed"]
    last_log = time.time()
    last_ck = time.time()
    B = cfg.get("batch", 48)
    ls = cfg.get("label_smoothing", 0.05)
    while time.time() - t_start < budget:
        frac = (time.time() - t_start) / budget
        for g in opt.param_groups:
            g["lr"] = cfg.get("lr", 3e-3) * (0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * min(frac, 1.0))))
        idx = rng.integers(0, len(train_items), size=B)
        seqs, labs = [], []
        for i in idx:
            it = train_items[i]
            s = augment(it, rng, cfg, dt)
            F, _ = encode(s, 1.0)
            seqs.append(F); labs.append(it["label"])
        X, M, y = _batch(seqs, labs)
        lo, _ = model(X)
        ce = torch.nn.functional.cross_entropy(lo.reshape(-1, len(LETTERS)), y.repeat_interleave(X.shape[1]),
                                               reduction="none", label_smoothing=ls).reshape(M.shape)
        # every prefix counts; later points weigh a little more (the full letter must be right)
        Tn = M.sum(1, keepdim=True)
        pos = torch.cumsum(M, 1) / Tn
        wgt = M * (0.5 + pos)
        loss = (ce * wgt).sum() / wgt.sum()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        state["steps"] += 1
        if time.time() - last_log > log_every or time.time() - t_start >= budget:
            acc = evaluate_fracs(model, val_items, fracs=(0.5, 1.0))
            score = 0.5 * (acc["top1"][0] + acc["top1"][1])
            state["hist"].append({"minutes": (time.time() - t_start) / 60, "steps": state["steps"], "loss": float(loss.detach()),
                                  "val_top1_half": acc["top1"][0], "val_top1_full": acc["top1"][1]})
            if score > state["best"][0]:
                state["best"] = (score, {k: v.detach().clone() for k, v in model.state_dict().items()})
            log(f"[online] {cfg.get('name')} {state['hist'][-1]}")
            last_log = time.time()
        if ckpt is not None and time.time() - last_ck > 120:
            state["elapsed"] = time.time() - t_start
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "rng": rng.bit_generator.state,
                        "state": state}, ckpt)
            last_ck = time.time()
    state["elapsed"] = time.time() - t_start
    if state["best"][1] is not None:
        model.load_state_dict(state["best"][1])
    model.eval()
    if ckpt is not None:
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "rng": rng.bit_generator.state,
                    "state": state}, ckpt)
    info = {"cfg": cfg, "steps": state["steps"], "minutes": state["elapsed"] / 60, "history": state["hist"],
            "best_val_score": state["best"][0], "n_params": n_params(model), "macs_per_point": macs_per_point(model.cfg),
            "n_train": len(train_items), "n_val": len(val_items)}
    return model, info


# ============================================================================================ evaluation
def posteriors(model, seqs: List[np.ndarray]) -> List[np.ndarray]:
    """Per-point class posteriors (T, 26) of each sequence (streaming-equivalent: causal GRU)."""
    import torch
    out = []
    with torch.no_grad():
        for a in range(0, len(seqs), 64):
            chunk = seqs[a:a + 64]
            X, M, _ = _batch(chunk, [0] * len(chunk))
            lo, _ = model(X)
            P = torch.softmax(lo, -1).numpy()
            for i, q in enumerate(chunk):
                out.append(P[i, :len(q)])
    return out


def at_fraction(P: np.ndarray, frac: np.ndarray, f: float) -> np.ndarray:
    k = int(np.searchsorted(frac, f + 1e-9, side="right")) - 1
    return P[max(k, 0)]


def evaluate_fracs(model, items: List[Dict], fracs=FRACTIONS, prior: Optional[np.ndarray] = None,
                   beta: float = 0.0) -> Dict:
    seqs, fr, y = [], [], []
    for it in items:
        F, f = encode(it["strokes"], 1.0)
        seqs.append(F); fr.append(f); y.append(it["label"])
    P = posteriors(model, seqs)
    top1, top3 = [], []
    for f in fracs:
        c1 = c3 = 0
        for i, (p, q) in enumerate(zip(P, fr)):
            v = at_fraction(p, q, f)
            if prior is not None and beta > 0:
                v = v * np.power(np.maximum(prior[i], 1e-6), beta)
                v = v / v.sum()
            o = np.argsort(-v)
            c1 += int(o[0] == y[i]); c3 += int(y[i] in o[:3])
        top1.append(c1 / max(len(P), 1)); top3.append(c3 / max(len(P), 1))
    return {"fractions": list(fracs), "top1": top1, "top3": top3, "n": len(P)}


def commit_stats(P_list: List[np.ndarray], fr_list: List[np.ndarray], y: Sequence[int], tau: float,
                 min_frac: float = 0.0) -> Dict:
    """Commit to a letter at the first point whose top posterior >= tau (and at least min_frac of the letter
    written); letters never committed are decided at their end."""
    n = len(P_list)
    committed, correct_c, fr_at, correct_all = 0, 0, [], 0
    for P, fr, yy in zip(P_list, fr_list, y):
        m = (P.max(1) >= tau) & (fr >= min_frac)
        if m.any():
            k = int(np.argmax(m))
            committed += 1
            ok = int(np.argmax(P[k]) == yy)
            correct_c += ok
            correct_all += ok
            fr_at.append(float(fr[k]))
        else:
            correct_all += int(np.argmax(P[-1]) == yy)
    return {"tau": tau, "committed_share": committed / max(n, 1), "commit_accuracy": correct_c / max(committed, 1),
            "median_fraction_at_commit": float(np.median(fr_at)) if fr_at else float("nan"),
            "committed_before_end_share": float(np.mean(np.array(fr_at) < 0.999)) * committed / max(n, 1) if fr_at else 0.0,
            "overall_accuracy": correct_all / max(n, 1), "n": n}


def latency_ms(model, n_points: int = 400) -> Dict:
    """Wall time per streaming update (one point, hidden state carried), this container's CPU, one thread."""
    import torch
    torch.set_num_threads(1)
    x = torch.zeros((1, 1, N_FEAT))
    h = None
    with torch.no_grad():
        for _ in range(20):
            _, h = model(x, h)
        t0 = time.perf_counter()
        for _ in range(n_points):
            lo, h = model(x, h)
            torch.softmax(lo, -1)
        dt = (time.perf_counter() - t0) / n_points
    return {"ms_per_point": dt * 1e3, "points_per_letter_median": None}
