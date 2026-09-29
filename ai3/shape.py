"""Task 4b: shape assist on real handwriting (SIMULATION: model HW1 of handwriting/, read-only; real UJI letters).

The writer's hand writes real letters (UJI Pen Characters v2, one repetition), rescaled to a 3 mm x-height and timed
at the uniform point rate of task 1 (ASSUMPTION), joined into words with pen lifts; tremor (the project's model) or a
dysgraphia-like smooth warp (the handwriting study's error model, 0.14 x-height, ASSUMPTION) can be added.  The pen is
Rev H's nose in HW1 (the Rev J nose has more travel; shape assist needs < 0.5 mm).

Shape assist (PROPOSED DESIGN), per letter, from the page sensor (handle position, 1 kHz, 2 ms late, 3 um noise):
  1 recognise the letter while it is written (task 1's recogniser on the hand's path); act only once the top posterior
    reaches c_min (the pen never acts on a letter it has not recognised);
  2 template = the writer's OWN other sample of that letter (the calibration; ai2 found copies of the writer's letters
    the most faithful style source);
  3 correspondence by open-end dynamic time warping of the path so far to the template (progress can only move forward,
    so the ink cannot collapse onto the nearest part of the template: the failure found in task 4a); the template is
    placed by the least-squares offset over the matched points (the writer keeps the letter's position and size);
  4 command = g x (deviation from the template shape, minus a dead band d0), limited to |q| <= q_max, low-passed;
  5 ramp in over 30 ms after recognition, out at the pen lift.
The independent legibility judge is an OFFLINE reader: a small CNN on the rendered ink image (no stroke order or timing),
trained on the UJI training writers only; it never sees the test writers and is not the recogniser the assist uses.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from numba import njit

from . import ensure_paths
from . import online as O

ensure_paths()

IMG = 32
PX_PER_XH = 7.0
XH_M = O.XH_MM * 1e-3


# ============================================================================================ rendering and the judge
def render(strokes: Sequence[np.ndarray], xh: float = 1.0, size: int = IMG, px_per_xh: float = PX_PER_XH,
           sigma: float = 0.7) -> np.ndarray:
    """Ink image of a letter (strokes in units where xh is the x-height), centred on its bounding box."""
    pts = []
    for s in strokes:
        s = np.asarray(s, float) / xh
        if len(s) == 1:
            pts.append(s)
            continue
        seg = np.hypot(*np.diff(s, axis=0).T)
        L = float(seg.sum())
        n = max(2, int(L * px_per_xh / 0.3) + 1)
        u = np.linspace(0, 1, n)
        cs = np.r_[0.0, np.cumsum(seg)] / max(L, 1e-12)
        pts.append(np.column_stack([np.interp(u, cs, s[:, 0]), np.interp(u, cs, s[:, 1])]))
    if not pts:
        return np.zeros((size, size), np.float32)
    P = np.vstack(pts)
    c = 0.5 * (P.min(0) + P.max(0))
    X = (P[:, 0] - c[0]) * px_per_xh + size / 2
    Y = size / 2 - (P[:, 1] - c[1]) * px_per_xh
    img = np.zeros((size, size), np.float32)
    ix = np.floor(X).astype(int); iy = np.floor(Y).astype(int)
    for dx in (-1, 0, 1, 2):
        for dy in (-1, 0, 1, 2):
            gx = ix + dx; gy = iy + dy
            m = (gx >= 0) & (gx < size) & (gy >= 0) & (gy < size)
            w = np.exp(-((gx[m] + 0.5 - X[m]) ** 2 + (gy[m] + 0.5 - Y[m]) ** 2) / (2 * sigma ** 2))
            np.add.at(img, (gy[m], gx[m]), w)
    return np.clip(img, 0, 1.0)


def make_judge():
    import torch
    nn = torch.nn

    class Judge(nn.Module):
        def __init__(self):
            super().__init__()
            self.f = nn.Sequential(nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                                   nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                                   nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                                   nn.Flatten(), nn.Linear(64 * 4 * 4, 96), nn.ReLU(), nn.Linear(96, 26))

        def forward(self, x):
            return self.f(x)

    return Judge()


def train_judge(items: List[Dict], val: List[Dict], minutes: float, dt: float, seed: int = 3, log=print):
    """The offline reader, trained on the training writers' letters with the 'full' augmentation of task 1."""
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    m = make_judge()
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    cfg = {"affine": True, "jitter": True, "tremor": True, "p_tremor": 0.4, "tremor_max": 0.3, "sl": True,
           "sl_scales": (0.3, 0.6)}
    t0 = time.time()
    steps = 0
    best = (-1.0, None)
    last = time.time()
    while time.time() - t0 < minutes * 60:
        frac = (time.time() - t0) / (minutes * 60)
        for g in opt.param_groups:
            g["lr"] = 2e-3 * (0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * min(frac, 1.0))))
        idx = rng.integers(0, len(items), size=64)
        X = np.stack([render(O.augment(items[i], rng, cfg, dt)) for i in idx])[:, None]
        y = torch.tensor([items[i]["label"] for i in idx])
        lo = m(torch.from_numpy(X))
        loss = torch.nn.functional.cross_entropy(lo, y, label_smoothing=0.05)
        opt.zero_grad(); loss.backward(); opt.step()
        steps += 1
        if time.time() - last > 60 or time.time() - t0 >= minutes * 60:
            acc = judge_accuracy(m, val)
            if acc > best[0]:
                best = (acc, {k: v.detach().clone() for k, v in m.state_dict().items()})
            log(f"[judge] {steps} steps {(time.time() - t0) / 60:.1f} min val {acc:.3f}")
            last = time.time()
    if best[1] is not None:
        m.load_state_dict(best[1])
    m.eval()
    return m, {"steps": steps, "minutes": (time.time() - t0) / 60, "best_val": best[0]}


def judge_probs(m, letters: Sequence[Sequence[np.ndarray]], xh: float = 1.0) -> np.ndarray:
    import torch
    if not len(letters):
        return np.zeros((0, 26))
    X = np.stack([render(s, xh) for s in letters])[:, None]
    with torch.no_grad():
        return torch.softmax(m(torch.from_numpy(X)), -1).numpy()


def judge_accuracy(m, items: List[Dict]) -> float:
    P = judge_probs(m, [it["strokes"] for it in items])
    return float(np.mean(P.argmax(1) == np.array([it["label"] for it in items])))


# ============================================================================================ words from real letters
@dataclass
class WordCase:
    writer: str
    word: str
    scn: object                                   # HW1 Scenario
    windows: List[Tuple[float, float]]            # (t0, t1) of each letter (first touchdown to last lift)
    written: List[List[np.ndarray]]               # the intended strokes of each letter (page frame, m)
    templates: List[List[np.ndarray]]             # the writer's other sample of each letter (letter frame, m)
    meta: Dict = field(default_factory=dict)


def _timed(pb, P: np.ndarray, dt_point: float):
    """Append a stroke with the real point timing (uniform rate), interpolated to the simulator step."""
    n_pts = len(P)
    T = max((n_pts - 1) * dt_point, pb.dt * 2)
    n = max(int(round(T / pb.dt)), 2)
    tt = np.linspace(0, T, n)
    ts = np.linspace(0, T, n_pts) if n_pts > 1 else np.zeros(1)
    xy = np.column_stack([np.interp(tt, ts, P[:, 0]), np.interp(tt, ts, P[:, 1])]) if n_pts > 1 else np.repeat(P, n, 0)
    pb._append(xy, np.full(n, True), np.full(n, 0.0))


def build_word(letter_samples: List[List[np.ndarray]], templates: List[List[np.ndarray]], xh_writer_mm: float,
               dt_point: float, word: str, writer: str, warp_amp: float = 0.0, warp_seed: int = 0,
               sim_dt: float = 25e-6) -> WordCase:
    """letter_samples: UJI strokes (mm, y up, box coordinates) of each letter; scaled to a 3 mm x-height."""
    from aiguide.writer import Path as APath, warp_params, apply_warp
    from handwriting import plant as PL
    f = O.XH_MM / xh_writer_mm * 1e-3                     # mm (writer) -> m at 3 mm x-height
    rng = np.random.default_rng(warp_seed)
    placed, tpls = [], []
    x_cursor = 0.0
    for k, (ls, tp) in enumerate(zip(letter_samples, templates)):
        S = [np.asarray(s, float) * f for s in ls]
        if warp_amp > 0:
            w = warp_params(rng, warp_amp)
            S = [apply_warp(s / XH_M, w) * XH_M for s in S]
        allp = np.vstack(S)
        dx = x_cursor - allp[:, 0].min() + (0.35 * XH_M if k else 0.0)
        S = [s + np.array([dx, 0.0]) for s in S]
        x_cursor = np.vstack(S)[:, 0].max()
        placed.append(S)
        T = [np.asarray(s, float) * f for s in tp]
        tpls.append(T)
    start = placed[0][0][0] + np.array([-1.0e-3, 1.0e-3])
    pb = APath(sim_dt, start=tuple(start), lift_height=1.5e-3)
    pb.dwell(0.15)
    windows = []
    for S in placed:
        t0 = None
        for s in S:
            travel = float(np.hypot(*(s[0] - pb.pos)))
            pb.move(s[0], 0.06 + travel / 0.08)
            pb.pen(True, 0.03)
            if t0 is None:
                t0 = pb._t
            pb.dwell(0.01)
            _timed(pb, s, dt_point)
            pb.dwell(0.008)
            pb.pen(False, 0.03)
        windows.append((t0, pb._t))
    pb.dwell(0.2)
    it = pb.build()
    scn = PL.Scenario(t=it.t, pref=np.ascontiguousarray(it.xy), vref=np.ascontiguousarray(np.gradient(it.xy, sim_dt, axis=0)),
                      down=np.ascontiguousarray(it.pen_down.astype(np.float64)), intended=it.xy,
                      tremor=np.zeros_like(it.xy), dt=sim_dt, meta={"lift": it.lift})
    return WordCase(writer, word, scn, windows, placed, tpls)


def with_tremor(case: WordCase, f0: float, amp: float, seed: int, pen, hand):
    from handwriting import plant as PL, writers as W
    hp = PL.adapted_path(case.scn.intended, case.scn.dt, pen, hand)
    d = W.tremor_path(case.scn.t, f0, amp, seed, 7) if amp > 0 else None
    return PL.with_hand_path(case.scn, hp, d)


# ============================================================================================ the controller
@njit(cache=True)
def open_end_dtw(A, B):
    """Open-end DTW of path A (all of it) against a prefix of template B; returns (index in B matched to A's last point,
    the matched B index for every A point)."""
    n, m = A.shape[0], B.shape[0]
    D = np.full((n + 1, m + 1), 1e30)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = math.sqrt((A[i - 1, 0] - B[j - 1, 0]) ** 2 + (A[i - 1, 1] - B[j - 1, 1]) ** 2)
            best = D[i - 1, j - 1]
            if D[i - 1, j] < best:
                best = D[i - 1, j]
            if D[i, j - 1] < best:
                best = D[i, j - 1]
            D[i, j] = c + best
    # best end in B, normalised by (i + j) so short and long prefixes compare
    jb = 1
    bv = 1e30
    for j in range(1, m + 1):
        v = D[n, j] / (n + j)
        if v < bv:
            bv = v
            jb = j
    # backtrack
    match = np.zeros(n, np.int64)
    i, j = n, jb
    while i > 0 and j > 0:
        match[i - 1] = j - 1
        a = D[i - 1, j - 1]; b = D[i - 1, j]; c = D[i, j - 1]
        if a <= b and a <= c:
            i -= 1; j -= 1
        elif b <= c:
            i -= 1
        else:
            j -= 1
    return jb - 1, match


def _resample_path(P: np.ndarray, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """Arc-length resampling that also returns, for every output point, the index of the source sample."""
    seg = np.hypot(*np.diff(P, axis=0).T) if len(P) > 1 else np.zeros(0)
    s = np.r_[0.0, np.cumsum(seg)]
    if s[-1] < step:
        return P[[0, -1]], np.array([0, len(P) - 1])
    u = np.arange(0.0, s[-1] + 1e-12, step)
    idx = np.searchsorted(s, u, side="right") - 1
    return np.column_stack([np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])]), np.clip(idx, 0, len(P) - 1)


@dataclass
class LetterTrack:
    """What the controller computed for one letter (config-independent parts)."""
    commit_tick: Dict[float, int]                  # c_min -> tick index of recognition (or -1)
    letter: Dict[float, int]                       # c_min -> recognised class
    dev: Dict[float, np.ndarray]                   # c_min -> (n_ticks, 2) shape deviation from commit to lift (NaN before)


def controller_signals(res, case: WordCase, rec_model, tick_hz: float, c_mins: Sequence[float],
                       templates_by_class: Optional[Dict[int, List[np.ndarray]]] = None, ps_lat: float = 2e-3,
                       ps_noise: float = 3e-6, seed: int = 0, update_ms: float = 10.0) -> Dict:
    """Page-sensor stream from a nose-held run -> per tick shape deviation (x, y) for each c_min.  Causal: at tick k the
    controller uses handle samples up to t_k - ps_lat.  templates_by_class: the writer's own sample of every letter
    (needed when the recogniser picks another letter than the one written)."""
    import torch
    rng = np.random.default_rng(seed)
    t = res.t
    H = res.handle
    con = res.contact > 0.5
    Ts = 1.0 / tick_hz
    n_ticks = int(math.ceil(t[-1] / Ts)) + 1
    tick_t = np.arange(n_ticks) * Ts
    # page sensor at 1 kHz: sample times, value = handle at (sample time - latency) + noise
    ps_t = np.arange(0.0, t[-1], 1e-3)
    ps_xy = np.column_stack([np.interp(ps_t - ps_lat, t, H[:, 0]), np.interp(ps_t - ps_lat, t, H[:, 1])])
    ps_xy += rng.normal(0, ps_noise, ps_xy.shape)
    ps_down = np.interp(ps_t - 1e-3, t, con.astype(float)) > 0.5
    dev = {c: np.full((n_ticks, 2), np.nan) for c in c_mins}
    commit = {c: [] for c in c_mins}
    letter_out = {c: [] for c in c_mins}
    step_m = O.STEP * XH_M
    for k, (t0, t1) in enumerate(case.windows):
        m = (ps_t >= t0 - 0.02) & (ps_t <= t1 + 0.01)
        idx_all = np.flatnonzero(m)
        if len(idx_all) < 5:
            for c in c_mins:
                commit[c].append(-1); letter_out[c].append(-1)
            continue
        # strokes of the letter from the sensed contact
        dn = ps_down[idx_all]
        # updates every update_ms of the letter
        upd = idx_all[::max(1, int(update_ms))]
        state = {c: None for c in c_mins}
        for ui in upd:
            sel = idx_all[(idx_all <= ui) & ps_down[idx_all]]
            if len(sel) < 3:
                continue
            # strokes (split at pen lifts)
            br = np.flatnonzero(np.diff(sel) > 1)
            strokes = np.split(ps_xy[sel], br + 1)
            F, fr = O.encode([s for s in strokes if len(s)], XH_M)
            if len(F) < 2:
                continue
            with torch.no_grad():
                lo, _ = rec_model(torch.from_numpy(F[None]))
                p = torch.softmax(lo[0, -1], -1).numpy()
            for c in c_mins:
                if state[c] is None and p.max() >= c:
                    state[c] = {"cls": int(np.argmax(p)), "tick": int(math.ceil(ps_t[ui] / Ts))}
            # deviation for every committed c_min
            done = {}
            for c in c_mins:
                st = state[c]
                if st is None:
                    continue
                cls = st["cls"]
                key = cls
                if key in done:
                    dv = done[key]
                else:
                    # the calibration sample of the recognised class: for the class actually written, the writer's
                    # other sample of it (case.templates); for any other class, the writer's sample of that class
                    if k < len(case.word) and cls == O.L2I.get(case.word[k]):
                        tpl = case.templates[k]
                    else:
                        tpl = (templates_by_class or {}).get(cls)
                    if tpl is None:
                        done[key] = None
                        continue
                    # pen-down path so far (letter frame) and the template, both resampled every STEP x-height
                    A_parts, B_parts = [], []
                    for s in strokes:
                        if len(s) >= 2:
                            A_parts.append(_resample_path(s, step_m)[0])
                    for s in tpl:
                        if len(s) >= 2:
                            B_parts.append(_resample_path(np.asarray(s), step_m)[0])
                    if not A_parts or not B_parts:
                        done[key] = None
                        continue
                    A = np.vstack(A_parts); B = np.vstack(B_parts)
                    B = B - B[0] + A[0]
                    jb, match = open_end_dtw(A, B)
                    off = np.mean(A - B[match], axis=0)          # least-squares placement over the matched part
                    target = B[jb] + off
                    dv = target - A[-1]
                    done[key] = dv
                if dv is None:
                    continue
                k0 = int(math.ceil(ps_t[ui] / Ts))
                k1 = min(n_ticks, k0 + int(update_ms * 1e-3 / Ts) + 1)
                dev[c][k0:k1] = dv
        for c in c_mins:
            commit[c].append(state[c]["tick"] if state[c] else -1)
            letter_out[c].append(state[c]["cls"] if state[c] else -1)
    return {"dev": dev, "commit": commit, "letter": letter_out, "tick_t": tick_t}


def command(dev: np.ndarray, g: float, q_max: float, d0_m: float, tick_hz: float, lp_hz: float = 30.0,
            ramp_s: float = 0.03) -> np.ndarray:
    """Per-tick nose command from the shape deviation: dead band, gain, limit, ramp and low-pass."""
    from scipy.signal import butter, lfilter
    e = np.nan_to_num(dev, nan=0.0)
    active = ~np.isnan(dev[:, 0])
    mag = np.hypot(e[:, 0], e[:, 1])
    shrink = np.where(mag > d0_m, (mag - d0_m) / np.maximum(mag, 1e-12), 0.0)
    q = g * e * shrink[:, None]
    qm = np.hypot(q[:, 0], q[:, 1])
    q *= np.where(qm > q_max, q_max / np.maximum(qm, 1e-12), 1.0)[:, None]
    # ramp in/out: first-order authority with time constant ramp_s
    a = np.zeros(len(q))
    al = 1.0 - math.exp(-1.0 / (tick_hz * ramp_s))
    for i in range(1, len(q)):
        a[i] = a[i - 1] + al * ((1.0 if active[i] else 0.0) - a[i - 1])
    q *= a[:, None]
    b, aa = butter(1, lp_hz, fs=tick_hz)
    return lfilter(b, aa, q, axis=0)


def servo_response(qcmd: np.ndarray, tick_hz: float, servo_hz: float = 80.0, zeta: float = 0.7,
                   latency: float = 0.6e-3) -> np.ndarray:
    """Fast approximation of the nose following a command (2nd-order follower + latency) for tuning sweeps; the final
    numbers use HW1's closed loop."""
    from scipy.signal import bilinear, lfilter
    w = 2 * math.pi * servo_hz
    b, a = bilinear([w * w], [1.0, 2 * zeta * w, w * w], tick_hz)
    d = int(round(latency * tick_hz))
    q = np.vstack([np.zeros((d, 2)), qcmd[:len(qcmd) - d]]) if d > 0 else qcmd
    return lfilter(b, a, q, axis=0)


def letters_ink(t: np.ndarray, ink: np.ndarray, down: np.ndarray, windows) -> List[List[np.ndarray]]:
    out = []
    for (t0, t1) in windows:
        m = (t >= t0 - 0.005) & (t <= t1 + 0.005)
        idx = np.flatnonzero(m & (down > 0.5))
        if len(idx) < 3:
            out.append([])
            continue
        br = np.flatnonzero(np.diff(idx) > 1)
        out.append([ink[s] for s in np.split(idx, br + 1) if len(s) >= 2])
    return out
