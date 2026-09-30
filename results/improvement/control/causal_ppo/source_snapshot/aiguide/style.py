"""Online style estimation from what the user has already written.

Per completed, recognised letter the ink is fitted to its font glyph with the
style's affine form (the same form the writer model and app/penapp/synth.py
use):

    x = x0 + a * gx + b * gy,     y = y0 + h * gy        (a = h * width, b = h * tan(slant))

Correspondence starts from arclength fractions of the (lightly smoothed) ink
and the glyph, stroke by stroke, and is refined by iterations of
nearest-point matching (ICP, 10 iterations), which tolerates tremor wiggle.  The estimator
aggregates robust (median) size, width and slant over recent letters, a
baseline line through the recent letter origins, the letter and word gaps,
the pen-down speed and the air-move speed, and keeps each letter's
*exemplars*: the user's own instances mapped back to glyph units.

Exemplars should be built from the unassisted hand path (ink minus the stage
offset, ICD 4.6 v2 proposal), never from guided ink: guided ink follows the
template, so learning from it would make the template converge to itself.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.spatial import cKDTree

from .glyphs import GLYPH_SET, arclength, resample, width as glyph_width

N_PTS = 64


@dataclass
class LetterFit:
    char: str
    a: float
    b: float
    h: float
    x0: float
    y0: float
    rms: float                          # residual RMS (m)
    n_strokes_ink: int
    exemplar: Optional[List[np.ndarray]] = None   # the instance in glyph units (per stroke)
    t_start: float = 0.0
    t_end: float = 0.0
    path_len: float = 0.0
    pen_down_time: float = 0.0

    @property
    def width(self) -> float:
        return self.a / self.h if self.h else 1.0

    @property
    def slant(self) -> float:
        return math.atan2(self.b, self.h)


def _smooth(P: np.ndarray, k: int = 5) -> np.ndarray:
    if len(P) < k + 2:
        return P
    ker = np.ones(k) / k
    pad = np.vstack([np.repeat(P[:1], k // 2, 0), P, np.repeat(P[-1:], k // 2, 0)])
    return np.column_stack([np.convolve(pad[:, 0], ker, "valid"), np.convolve(pad[:, 1], ker, "valid")])


@dataclass
class Prior:
    """Current style belief used to regularise letters whose glyph does not constrain a parameter
    (e.g. 'l' has no horizontal extent, '-' no vertical extent)."""
    h: float = 2.6e-3
    width: float = 1.0
    slant: float = math.radians(10.0)
    weight: float = 2e-4      # prior weight per point (glyph units squared); matters only for degenerate glyphs


def _solve(G: np.ndarray, Q: np.ndarray, prior: Optional[Prior] = None) -> Tuple[float, ...]:
    """Ridge least squares for (a, b, x0) and (h, y0) given glyph points G and ink points Q.

    The ridge terms pull h, a = h*width and b = h*tan(slant) toward the prior with
    a weight that only matters when the glyph's extent does not determine them.
    """
    pr = prior or Prior()
    n = len(G)
    lam = pr.weight * n
    gy = G[:, 1]
    # y: minimise |h gy + y0 - Qy|^2 + lam (h - h_p)^2
    Ay = np.column_stack([gy, np.ones(n)])
    Ay = np.vstack([Ay, [math.sqrt(lam), 0.0]])
    by = np.r_[Q[:, 1], math.sqrt(lam) * pr.h]
    h, y0 = np.linalg.lstsq(Ay, by, rcond=None)[0]
    hp = h if h > 1e-5 else pr.h
    Ax = np.column_stack([G[:, 0], gy, np.ones(n)])
    Ax = np.vstack([Ax, [math.sqrt(lam), 0.0, 0.0], [0.0, math.sqrt(lam), 0.0]])
    bx = np.r_[Q[:, 0], math.sqrt(lam) * hp * pr.width, math.sqrt(lam) * hp * math.tan(pr.slant)]
    ax, bb, x0 = np.linalg.lstsq(Ax, bx, rcond=None)[0]
    return float(ax), float(bb), float(h), float(x0), float(y0)


def _apply(G: np.ndarray, a, b, h, x0, y0) -> np.ndarray:
    return np.column_stack([x0 + a * G[:, 0] + b * G[:, 1], y0 + h * G[:, 1]])


def _inverse(Q: np.ndarray, a, b, h, x0, y0) -> np.ndarray:
    gy = (Q[:, 1] - y0) / h
    gx = (Q[:, 0] - x0 - b * gy) / a
    return np.column_stack([gx, gy])


def fit_letter(char: str, ink_strokes: Sequence[np.ndarray], *, n_icp: int = 10, smooth: int = 11,
               glyph: Optional[List[np.ndarray]] = None, prior: Optional[Prior] = None) -> LetterFit:
    """Fit the style's affine map from ``glyph`` (default: the font glyph) to the ink."""
    glyph = glyph if glyph is not None else GLYPH_SET[char]
    ink = [_smooth(np.asarray(s, float), smooth) for s in ink_strokes if len(s) >= 2]
    if not ink:
        raise ValueError("no ink")
    if len(ink) == len(glyph):
        pairs = list(zip(glyph, ink))
    else:                                   # stroke structure differs: match the concatenations
        pairs = [(np.vstack(glyph), np.vstack(ink))]
    G, Q = [], []
    for g, q in pairs:
        lg, lq = arclength(g)[-1], arclength(q)[-1]
        m = max(8, int(N_PTS * max(lg, 1e-6) / max(sum(arclength(x)[-1] for x in glyph), 1e-6)))
        G.append(resample(g, m) if lg > 0 else np.repeat(g[:1], m, 0))
        Q.append(resample(q, m) if lq > 0 else np.repeat(q[:1], m, 0))
    G = np.vstack(G)
    Q = np.vstack(Q)
    p = _solve(G, Q, prior)
    dense = np.vstack([resample(g, 400) if arclength(g)[-1] > 0 else np.repeat(g[:1], 4, 0) for g in glyph])
    Qall = np.vstack(ink)
    for _ in range(n_icp):
        tree = cKDTree(_apply(dense, *p))
        _, j = tree.query(Qall)
        p = _solve(dense[j], Qall, prior)
    tree = cKDTree(_apply(dense, *p))
    d, _ = tree.query(Qall)
    a, b, h, x0, y0 = p
    ex = None
    if h > 1e-5 and abs(a) > 1e-5:
        ex = [_inverse(s, a, b, h, x0, y0) for s in ink]
    return LetterFit(char, a, b, h, x0, y0, float(np.sqrt(np.mean(d ** 2))), len(ink), ex)


def _active_length_time(ink_strokes, t_strokes, frac: float = 0.2) -> Tuple[float, float]:
    """Path length and time while the (smoothed) pen speed exceeds ``frac`` of its stroke maximum
    (excludes touchdown, dwell and lift phases)."""
    L = T = 0.0
    for s, t in zip(ink_strokes, t_strokes):
        s = _smooth(np.asarray(s, float), 5)
        t = np.asarray(t, float)
        if len(s) < 3:
            continue
        seg = np.hypot(*np.diff(s, axis=0).T)
        dtt = np.diff(t)
        v = seg / np.maximum(dtt, 1e-9)
        m = v > frac * v.max()
        L += float(seg[m].sum())
        T += float(dtt[m].sum())
    return L, T


@dataclass
class StyleEstimate:
    h: float
    width: float
    slant: float                      # rad
    letter_gap: float                 # x-height units
    word_gap: float                   # x-height units
    baseline_y: float                 # baseline height at x_ref
    baseline_slope: float
    x_ref: float
    speed: float                      # m/s, pen-down path speed
    air_speed: float                  # m/s
    n_letters: int
    size_frozen: Optional[float] = None

    def baseline(self, x: float) -> float:
        return self.baseline_y + self.baseline_slope * (x - self.x_ref)

    @property
    def a(self) -> float:
        return (self.size_frozen or self.h) * self.width

    @property
    def b(self) -> float:
        return (self.size_frozen or self.h) * math.tan(self.slant)

    @property
    def size(self) -> float:
        return self.size_frozen or self.h


class StyleEstimator:
    """Aggregates letter fits online; holds the user's exemplars per character."""

    def __init__(self, window: int = 16, max_exemplars: int = 4):
        self.fits: Deque[LetterFit] = deque(maxlen=window)
        self.all_fits: List[LetterFit] = []
        self.exemplars: Dict[str, Deque[List[np.ndarray]]] = defaultdict(lambda: deque(maxlen=max_exemplars))
        self.gaps: Deque[float] = deque(maxlen=window)
        self.word_gaps: Deque[float] = deque(maxlen=8)
        self.air: Deque[float] = deque(maxlen=window)
        self.size_frozen: Optional[float] = None
        self._last: Optional[LetterFit] = None

    def update(self, char: str, ink_strokes: Sequence[np.ndarray], *, t_strokes: Sequence[np.ndarray] = (),
               new_word: bool = False, keep_exemplar: bool = True) -> LetterFit:
        prior = None
        if self.fits:
            e = self.estimate()
            prior = Prior(e.h, e.width, e.slant)
        f = fit_letter(char, ink_strokes, prior=prior)
        if t_strokes:
            f.t_start = float(t_strokes[0][0])
            f.t_end = float(t_strokes[-1][-1])
            f.path_len, f.pen_down_time = _active_length_time(ink_strokes, t_strokes)
        prev = self._last
        if prev is not None and f.h > 0:
            adv = prev.x0 + prev.a * glyph_width(prev.char)
            gap = (f.x0 - adv) / max(np.median([x.h for x in self.fits] + [f.h]), 1e-6)
            if new_word:
                self.word_gaps.append(gap)
            else:
                self.gaps.append(gap)
            if t_strokes and prev.t_end > 0 and prev.path_len > 0:
                dist = float(np.hypot(*(np.asarray(ink_strokes[0][0]) - self._last_end)))
                dtm = f.t_start - prev.t_end
                if dtm > 0:
                    self.air.append(dist / dtm)
        self.fits.append(f)
        self.all_fits.append(f)
        if keep_exemplar and f.exemplar is not None and f.rms < 0.25 * max(f.h, 1e-6):
            self.exemplars[char].append(f.exemplar)
        self._last = f
        self._last_end = np.asarray(ink_strokes[-1][-1], float)
        return f

    def freeze_size(self, h: Optional[float] = None) -> None:
        """Keep the template size fixed (micrographia cueing target) instead of tracking the ink."""
        self.size_frozen = h if h is not None else self.estimate().h

    def estimate(self) -> StyleEstimate:
        fs = list(self.fits)
        if not fs:
            raise ValueError("no letters yet")
        h = float(np.median([f.h for f in fs]))
        w = float(np.median([f.width for f in fs]))
        sl = float(np.median([f.slant for f in fs]))
        xs = np.array([f.x0 for f in fs])
        ys = np.array([f.y0 for f in fs])
        if len(fs) >= 3 and np.ptp(xs) > 2 * h:
            slope, icpt = np.polyfit(xs, ys, 1)
            slope = float(np.clip(slope, -0.2, 0.2))
            yb = float(icpt + slope * xs[-1])
        else:
            slope, yb = 0.0, float(np.median(ys))
        lg = float(np.median(self.gaps)) if self.gaps else 0.32
        wg = float(np.median(self.word_gaps)) if self.word_gaps else 1.3
        sp = [f.path_len / f.pen_down_time for f in fs if f.pen_down_time > 0]
        speed = float(np.median(sp)) if sp else 0.028
        air = float(np.median(self.air)) if self.air else 0.06
        return StyleEstimate(h, w, sl, lg, wg, yb, slope, float(xs[-1]), speed, air, len(self.all_fits),
                             self.size_frozen)

    def exemplar(self, char: str, n: int = N_PTS) -> Optional[List[np.ndarray]]:
        """Mean of the stored instances of ``char`` (glyph units), stroke by stroke; None if none or inconsistent."""
        ex = list(self.exemplars.get(char, []))
        if not ex:
            return None
        ns = [len(e) for e in ex]
        k = max(set(ns), key=ns.count)
        ex = [e for e in ex if len(e) == k]
        out = []
        for si in range(k):
            L = [arclength(e[si])[-1] for e in ex]
            m = max(4, int(n * np.mean(L) / max(sum(np.mean([arclength(e[j])[-1] for e in ex]) for j in range(k)), 1e-9)))
            out.append(np.mean([resample(e[si], m) for e in ex], axis=0))
        return out
