r"""Look-ahead autowrite planner (CALC; the plan is then executed in model HW1 by ``autowrite.py``).

The task.  In autowrite mode the hand only sweeps the pen along the line; the nose draws the letters inside its reach.
The pen knows the text in advance (a known text: copying, dictation, a note typed in the app), so it can plan the
whole line before the hand gets there.  The plan chooses *when* each point of the text is drawn.

Target path.  The text is written by an aiguide writer (``aiguide.writer``: the writer's own style, size, slant and
letter shapes) and turned into one ordered path: every pen-down stroke, resampled at ``ds`` along its arc length, and
straight pen-up moves between strokes (drawn in the air: the pen lifts itself with its axial degree of freedom, or,
without one, the ball stays on the paper and the move is inked).

Time warp by dynamic programming.  The hand position H_j is known on a grid j (a steady sweep at v_h, or, when the
plan is executed, the measured hand position along the line).  The plan picks one path index i_j per step so that
  * the drawn point stays within the reach R of the hand:  |P(i_j) - H_j| <= R;
  * progress is monotone with bounded speed: pen-down v_min_down <= v <= v_max_down (no dwell blobs inside a
    stroke), pen-up 0 <= v <= v_max_up (the pen may wait in the air);
  * the sum of squared excursions |P(i_j) - H_j|^2 is minimal (Viterbi, exact on the grid).
The smallest feasible R (bisection) is the reach the text needs at that size and sweep speed: the travel requirement
of autowrite before any tremor margin.  A zero-phase smoothing of the progress then limits the drawing acceleration
(the plan is made ahead of time, so zero phase is allowed).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
from numba import njit

from . import ensure_paths

ensure_paths()


@dataclass
class TargetPath:
    xy: np.ndarray                    # (N, 2) m, page frame
    down: np.ndarray                  # (N,) bool, pen-down sample
    s: np.ndarray                     # (N,) m, arc length along the whole path (pen-up moves included)
    letter: np.ndarray                # (N,) int, glyph index of the letter the sample belongs to (-1: pen-up move)
    stroke: np.ndarray                # (N,) int, global stroke index (-1: pen-up move)
    stroke_end: np.ndarray            # (N,) bool, last sample of a pen-down stroke (a stop is allowed there)
    ds: float
    letters: List[Dict] = field(default_factory=list)   # per glyph: char, glyph_index, word_index, polylines, size

    @property
    def n(self):
        return len(self.s)

    @property
    def length_down(self):
        d = np.hypot(*np.diff(self.xy, axis=0).T)
        return float(np.sum(d[self.down[1:] & self.down[:-1]]))

    @property
    def length_up(self):
        return float(self.s[-1] - self.length_down)


def _resample(P: np.ndarray, ds: float) -> np.ndarray:
    seg = np.hypot(*np.diff(P, axis=0).T)
    s = np.r_[0.0, np.cumsum(seg)]
    if s[-1] <= 0:
        return P[:1].copy()
    n = max(2, int(math.ceil(s[-1] / ds)) + 1)
    u = np.linspace(0.0, s[-1], n)
    return np.column_stack([np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])])


def target_from_written(written, ds: float = 40e-6, dwell_start: float = 0.015, dwell_end: float = 0.010,
                        v_ref: float = 45e-3) -> TargetPath:
    """Ordered pen path of an aiguide ``Written`` (the writer's intended letters in page coordinates).  Each pen-down
    stroke starts and ends with a dwell (repeated samples: the DP needs at least dwell_* seconds to pass them at its
    fastest pen-down rate), as the synthetic writers do (aiguide writer: 15 ms after touchdown, 10 ms before lift), so
    that dots and short strokes leave ink."""
    n_ds = int(math.ceil(dwell_start * v_ref / ds))
    n_de = int(math.ceil(dwell_end * v_ref / ds))
    pts, dn, let, strk = [], [], [], []
    letters = []
    gs = 0
    prev_end = None
    for L in written.letters:
        letters.append({"char": L.char, "glyph_index": L.glyph_index, "word_index": L.word_index,
                        "polylines": [np.asarray(p, float) for p in L.polylines], "size": float(L.size),
                        "x0": float(L.x0), "y0": float(L.y0)})
        for P in L.polylines:
            P = np.asarray(P, float)
            if prev_end is not None:
                up = _resample(np.vstack([prev_end, P[0]]), ds)[1:-1]
                if len(up):
                    pts.append(up); dn.append(np.zeros(len(up), bool)); let.append(np.full(len(up), -1)); strk.append(np.full(len(up), -1))
            Q = _resample(P, ds)
            Q = np.vstack([np.repeat(Q[:1], n_ds, axis=0), Q, np.repeat(Q[-1:], n_de, axis=0)])
            pts.append(Q); dn.append(np.ones(len(Q), bool)); let.append(np.full(len(Q), L.glyph_index)); strk.append(np.full(len(Q), gs))
            gs += 1
            prev_end = Q[-1]
    xy = np.vstack(pts)
    down = np.concatenate(dn)
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    stroke = np.concatenate(strk)
    stroke_end = np.zeros(len(s), bool)
    idx = np.flatnonzero(down)
    if len(idx):
        nxt = np.r_[stroke[1:], -2]
        stroke_end = down & (nxt != stroke)
    return TargetPath(np.ascontiguousarray(xy), down, s, np.concatenate(let), stroke, stroke_end, ds, letters)


@njit(cache=True)
def _viterbi(Px, Py, down, stroke_end, Hx, Hy, R2, dmin_dn, dmax_dn, dmax_up, back):
    """Min-sum DP over (step j, path index i).  Returns the final cost array; back[j, i] = step size taken to reach
    i at step j (-1: unreachable).  i must start at 0 at j = 0."""
    N = Px.shape[0]
    M = Hx.shape[0]
    INF = 1e300
    cost = np.full(N, INF)
    new = np.full(N, INF)
    d0 = (Px[0] - Hx[0]) ** 2 + (Py[0] - Hy[0]) ** 2
    if d0 <= R2:
        cost[0] = d0
    back[0, 0] = 0
    for j in range(1, M):
        for i in range(N):
            new[i] = INF
        hx = Hx[j]; hy = Hy[j]
        for i in range(N):
            c = cost[i]
            if c >= INF:
                continue
            if down[i] and not stroke_end[i]:
                lo = dmin_dn; hi = dmax_dn
            elif down[i]:
                lo = 0; hi = dmax_dn
            else:
                lo = 0; hi = dmax_up
            for d in range(lo, hi + 1):
                k = i + d
                if k >= N:
                    break
                # inside a pen-down stroke the slower (writing) limit applies to the whole step
                if d > dmax_dn and down[k]:
                    break
                e = (Px[k] - hx) ** 2 + (Py[k] - hy) ** 2
                if e > R2:
                    continue
                v = c + e
                if v < new[k]:
                    new[k] = v
                    back[j, k] = d
        for i in range(N):
            cost[i] = new[i]
    return cost


@dataclass
class PlanParams:
    dt: float = 10e-3             # planning step (s)
    v_max_down: float = 45e-3     # m/s, drawing speed limit (ASSUMPTION; adult phrase writing ~30 mm/s, CON-20)
    v_min_down: float = 4e-3      # m/s, no dwell inside a stroke (ASSUMPTION)
    v_max_up: float = 90e-3       # m/s, pen-up moves (ASSUMPTION; the writers' air speed is 45-75 mm/s)
    smooth_hz: float = 6.0        # zero-phase smoothing of the progress (plan-time, so zero phase is allowed)
    lead_in: float = 0.4          # s of sweep before the first letter's position (the hand starts left of the text)


@dataclass
class Plan:
    ok: bool
    reach: float                  # m, the reach used by the DP
    t: np.ndarray                 # (M,) s
    hand: np.ndarray              # (M, 2) nominal hand (reach centre) positions
    s: np.ndarray                 # (M,) planned arc length (smoothed, monotone)
    xy: np.ndarray                # (M, 2) planned drawn point
    down: np.ndarray              # (M,) bool, planned pen-down
    exc: np.ndarray               # (M,) m, excursion |xy - hand| after smoothing
    path: Optional[TargetPath] = None     # the path the plan indexes (text with head and tail)
    meta: Dict = field(default_factory=dict)

    def at(self, tq: np.ndarray):
        """Planned drawn point and pen-down state at query times (linear in arc length)."""
        sq = np.interp(tq, self.t, self.s)
        return sq


def sweep(tp: TargetPath, v_h: float, pp: PlanParams, y_c: Optional[float] = None, t_extra: float = 1.0):
    """Nominal steady sweep: the reach centre moves along +x at v_h from lead_in before the first point."""
    x0 = float(tp.xy[0, 0]) - pp.lead_in * v_h
    x1 = float(tp.xy[:, 0].max())
    T = (x1 - x0) / v_h + t_extra
    t = np.arange(0.0, T, pp.dt)
    if y_c is None:
        y_c = centre_height(tp)
    return t, np.column_stack([x0 + v_h * t, np.full(len(t), y_c)])


def centre_height(tp: TargetPath) -> float:
    """The reach centre's height: the middle of the text's vertical extent (ascender to descender), per line."""
    y = tp.xy[tp.down, 1]
    return float(0.5 * (np.percentile(y, 0.5) + np.percentile(y, 99.5)))


def _dp(tp: TargetPath, H: np.ndarray, R: float, pp: PlanParams):
    q = pp.dt / tp.ds
    dmax_dn = max(1, int(math.floor(pp.v_max_down * q)))
    dmin_dn = min(dmax_dn, int(math.ceil(pp.v_min_down * q)))
    dmax_up = max(dmax_dn, int(math.floor(pp.v_max_up * q)))
    M = len(H)
    back = np.full((M, tp.n), -1, dtype=np.int16)
    cost = _viterbi(tp.xy[:, 0].copy(), tp.xy[:, 1].copy(), tp.down, tp.stroke_end, H[:, 0].copy(), H[:, 1].copy(),
                    R * R, dmin_dn, dmax_dn, dmax_up, back)
    if not np.isfinite(cost[-1]) or cost[-1] > 1e299:
        return None
    # the text is finished at some step; stay at the end afterwards: find the first step whose back[.., N-1] is set
    idx = np.zeros(M, dtype=np.int64)
    # backtrack from the last step at the final index (the DP lets the pen wait at the end only if the end point
    # stays in reach; a finished text is held by setting the path's end as absorbing below)
    i = tp.n - 1
    for j in range(M - 1, 0, -1):
        idx[j] = i
        d = back[j, i]
        if d < 0:
            return None
        i -= int(d)
    idx[0] = i
    return idx if i == 0 else None


def plan(tp: TargetPath, v_h: float, R: float, pp: Optional[PlanParams] = None, y_c: Optional[float] = None) -> Plan:
    """Plan the line for a steady sweep at v_h and reach R.  The path's end is extended by a pen-up tail that
    follows the hand, so a finished text never forces an excursion."""
    pp = pp or PlanParams()
    t, H = sweep(tp, v_h, pp, y_c)
    tpx = _with_tail(tp, H)
    plan_path = tpx
    idx = _dp(tpx, H, R, pp)
    if idx is None:
        return Plan(False, R, t, H, np.zeros(len(t)), np.zeros((len(t), 2)), np.zeros(len(t), bool), np.full(len(t), np.inf),
                    meta={"v_h": v_h})
    # smooth the path index (not the arc length) so that dwells (repeated samples) keep their duration
    fidx = _smooth_monotone(idx.astype(float), pp.dt, pp.smooth_hz)
    ar = np.arange(tpx.n, dtype=float)
    s = np.interp(fidx, ar, tpx.s)
    xy = np.column_stack([np.interp(fidx, ar, tpx.xy[:, 0]), np.interp(fidx, ar, tpx.xy[:, 1])])
    down = tpx.down[np.clip(np.round(fidx).astype(int), 0, tpx.n - 1)]
    exc = np.hypot(*(xy - H).T)
    speed = np.abs(np.gradient(s, pp.dt))
    out = Plan(True, R, t, H, s, xy, down, exc, path=plan_path,
                meta={"v_h": v_h, "reach_used_mm": R * 1e3, "exc_max_mm": float(exc.max() * 1e3),
                      "exc_p99_mm": float(np.percentile(exc, 99) * 1e3), "exc_rms_mm": float(np.sqrt(np.mean(exc ** 2)) * 1e3),
                      "exc_max_raw_mm": float(np.hypot(*(tpx.xy[idx] - H).T).max() * 1e3),
                      "speed_down_p95_mm_s": float(np.percentile(speed[down], 95) * 1e3) if down.any() else 0.0,
                      "t_start_s": float(t[min(len(t) - 1, np.searchsorted(fidx, tpx.n_head))]),
                      "t_end_s": float(t[min(len(t) - 1, np.searchsorted(fidx, tpx.n_head + tp.n - 1))]),
                      "s_text": (tpx.s_text0, tpx.s_text1)},
               )
    out.idx = fidx
    return out


def _with_tail(tp: TargetPath, H: np.ndarray) -> TargetPath:
    """Prepend a pen-up head from the hand's start to the first point (the pen waits in the air until the text comes
    into reach) and append a pen-up tail along the sweep (so the DP can finish early and wait in reach)."""
    head = _resample(np.vstack([H[0], tp.xy[0]]), tp.ds)[:-1]
    nh = len(head)
    end = tp.xy[-1]
    L = max(float(H[-1, 0] - end[0]), 2 * tp.ds)
    n = max(2, int(L / tp.ds))
    tail = np.column_stack([end[0] + tp.ds * np.arange(1, n + 1), np.full(n, H[-1, 1])])
    tail[:, 1] = end[1] + (H[-1, 1] - end[1]) * np.clip(np.arange(1, n + 1) / max(1, int(3e-3 / tp.ds)), 0, 1)
    xy = np.vstack([head, tp.xy, tail])
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    out = TargetPath(xy, np.r_[np.zeros(nh, bool), tp.down, np.zeros(n, bool)], s,
                     np.r_[np.full(nh, -1), tp.letter, np.full(n, -1)], np.r_[np.full(nh, -1), tp.stroke, np.full(n, -1)],
                     np.r_[np.zeros(nh, bool), tp.stroke_end, np.zeros(n, bool)], tp.ds, tp.letters)
    out.n_head = nh
    out.s_text0 = float(s[nh])
    out.s_text1 = float(s[nh + tp.n - 1])
    return out


def _smooth_monotone(s: np.ndarray, dt: float, fc: float) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt
    if fc <= 0 or len(s) < 30:
        return np.maximum.accumulate(s)
    sos = butter(2, fc, fs=1.0 / dt, output="sos")
    pad = np.r_[np.full(50, s[0]), s, np.full(50, s[-1])]
    y = sosfiltfilt(sos, pad)[50:-50]
    y = np.maximum.accumulate(np.clip(y, s[0], s[-1]))
    return y


def min_reach(tp: TargetPath, v_h: float, pp: Optional[PlanParams] = None, lo: float = 0.5e-3, hi: float = 16e-3,
              tol: float = 0.05e-3, y_c: Optional[float] = None) -> Dict:
    """Smallest reach (bisection on the DP's feasibility) for the line at sweep speed v_h (CALC)."""
    pp = pp or PlanParams()
    if plan(tp, v_h, hi, pp, y_c).ok is False:
        return {"reach_mm": float("inf"), "v_h_mm_s": v_h * 1e3}
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if plan(tp, v_h, mid, pp, y_c).ok:
            hi = mid
        else:
            lo = mid
    p = plan(tp, v_h, hi, pp, y_c)
    return {"reach_mm": hi * 1e3, "v_h_mm_s": v_h * 1e3, "exc_max_smoothed_mm": p.meta.get("exc_max_mm"),
            "exc_rms_mm": p.meta.get("exc_rms_mm"), "t_end_s": p.meta.get("t_end_s")}


def line_speed(tp: TargetPath, pp: PlanParams, duty: float = 0.8) -> float:
    """A sweep speed at which the pen can draw the line: the drawing time at the speed limits divided by the line
    length, with a duty factor (the pen needs slack to wait for the hand)."""
    T = tp.length_down / (0.8 * pp.v_max_down) + tp.length_up / (0.8 * pp.v_max_up)
    L = float(tp.xy[:, 0].max() - tp.xy[:, 0].min())
    return duty * L / T
