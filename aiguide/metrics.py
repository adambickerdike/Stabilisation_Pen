"""Metrics for guided writing (all CALCULATIONS on simulated ink).

path distance   every in-contact ink sample of a letter to the nearest point of
                that letter's intended path (per-letter, so a letter is never
                matched to a neighbour), RMS and p95 in um
legibility      (a) DTW distance between the ink letter and the clean intended
                letter after removing the centroid offset (mean um per matched
                point; translation does not affect legibility);
                (b) template matching: the ink letter is classified among the
                26 lower-case glyphs rendered in the writer's estimated style,
                size-normalised, by DTW; accuracy and margin
travel limit    fraction of in-contact time with |q_ref| >= 0.95 q_lim, and with
                the nib stage on its mechanical stop
height          vertical extent of a letter's ink (micrographia)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from numba import njit
from scipy.spatial import cKDTree

from .glyphs import GLYPH_SET, LETTERS, arclength, resample

N_RS = 64


@njit(cache=True)
def _dtw(A, B):
    n, m = A.shape[0], B.shape[0]
    D = np.full((n + 1, m + 1), 1e30)
    L = np.zeros((n + 1, m + 1))
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = math.sqrt((A[i - 1, 0] - B[j - 1, 0]) ** 2 + (A[i - 1, 1] - B[j - 1, 1]) ** 2)
            best = D[i - 1, j - 1]
            bl = L[i - 1, j - 1]
            if D[i - 1, j] < best:
                best = D[i - 1, j]
                bl = L[i - 1, j]
            if D[i, j - 1] < best:
                best = D[i, j - 1]
                bl = L[i, j - 1]
            D[i, j] = c + best
            L[i, j] = bl + 1.0
    return D[n, m] / L[n, m]


def dtw(A: np.ndarray, B: np.ndarray) -> float:
    """Mean matched-point distance along the optimal DTW path."""
    return float(_dtw(np.ascontiguousarray(A, dtype=np.float64), np.ascontiguousarray(B, dtype=np.float64)))


def shape_points(strokes: Sequence[np.ndarray], n: int = N_RS) -> np.ndarray:
    """Concatenate strokes in writing order and resample to n points by arclength."""
    P = np.vstack([np.asarray(s, float) for s in strokes if len(s)])
    return resample(P, n) if arclength(P)[-1] > 0 else np.repeat(P[:1], n, axis=0)


def normalise(P: np.ndarray) -> np.ndarray:
    c = P - P.mean(axis=0)
    r = math.sqrt(float(np.mean(np.sum(c ** 2, axis=1))))
    return c / max(r, 1e-12)


def dense(strokes: Sequence[np.ndarray], step: float = 5e-6) -> np.ndarray:
    out = []
    for s in strokes:
        s = np.asarray(s, float)
        L = arclength(s)[-1] if len(s) > 1 else 0.0
        out.append(resample(s, max(2, int(L / step) + 1)) if L > 0 else s[:1])
    return np.vstack(out)


class GlyphRecognizer:
    """Size-normalised DTW template matching among the 26 lower-case glyphs in a writer's style."""

    def __init__(self, h: float, width: float, slant: float, letters: str = LETTERS):
        self.letters = letters
        self.refs = {}
        for c in letters:
            strokes = [np.column_stack([h * width * s[:, 0] + h * math.tan(slant) * s[:, 1], h * s[:, 1]])
                       for s in GLYPH_SET[c]]
            self.refs[c] = normalise(shape_points(strokes))

    def classify(self, strokes: Sequence[np.ndarray]) -> Tuple[str, Dict[str, float]]:
        q = normalise(shape_points(strokes))
        d = {c: dtw(q, r) for c, r in self.refs.items()}
        return min(d, key=d.get), d


def split_strokes(xy: np.ndarray, contact: np.ndarray) -> List[np.ndarray]:
    d = np.diff(np.r_[0, contact.astype(np.int8), 0])
    return [xy[a:b] for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= 2]


def letter_metrics(ink: np.ndarray, contact: np.ndarray, intended_strokes: Sequence[np.ndarray], char: str,
                   recognizer: Optional[GlyphRecognizer] = None, decim: int = 10, q: Optional[np.ndarray] = None) -> Dict:
    """Metrics of one letter's ink (samples of the letter's time window)."""
    m = contact > 0
    if m.sum() < 4:
        return {"char": char, "n": int(m.sum()), "missing": True}
    tree = cKDTree(dense(intended_strokes))
    d, _ = tree.query(ink[m])
    strokes = [s[::decim] if len(s) > 2 * decim else s for s in split_strokes(ink, m)]
    out = {"char": char, "n": int(m.sum()), "d": d, "path_rms_um": float(np.sqrt(np.mean(d ** 2)) * 1e6),
           "path_max_um": float(d.max() * 1e6)}
    if q is not None:
        out["max_stage_um"] = float(np.hypot(q[m, 0], q[m, 1]).max() * 1e6)
    if strokes:
        A = shape_points(strokes)
        B = shape_points(intended_strokes)
        out["dtw_um"] = dtw(A - A.mean(0), B - B.mean(0)) * 1e6
        yy = ink[m][:, 1]
        out["height_um"] = float((yy.max() - yy.min()) * 1e6)
        if recognizer is not None:
            pred, dd = recognizer.classify(strokes)
            ds = sorted(dd.values())
            out["recognised_as"] = pred
            out["recognised_ok"] = pred == char
            out["margin"] = float((min(v for c, v in dd.items() if c != char) - dd[char]) / max(dd[char], 1e-9))
            out["rank_true"] = int(sorted(dd, key=dd.get).index(char)) + 1
    return out


def travel_limit(qr: np.ndarray, stop: np.ndarray, contact: np.ndarray, q_lim: float) -> Dict[str, float]:
    m = contact > 0
    if not m.any():
        return {"at_soft_limit": 0.0, "on_stop": 0.0}
    r = np.hypot(qr[:, 0], qr[:, 1])
    return {"at_soft_limit": float(np.mean(r[m] >= 0.95 * q_lim)), "on_stop": float(np.mean(stop[m] > 0.5)),
            "qr_p95_um": float(np.percentile(r[m], 95) * 1e6), "qr_max_um": float(r[m].max() * 1e6)}


def pool(letters: Sequence[Dict]) -> Dict:
    """Aggregate per-letter metrics."""
    ok = [L for L in letters if not L.get("missing")]
    if not ok:
        return {}
    d = np.concatenate([L["d"] for L in ok]) * 1e6
    out = {"n_letters": len(ok), "path_rms_um": float(np.sqrt(np.mean(d ** 2))), "path_p95_um": float(np.percentile(d, 95)),
           "path_max_um": float(d.max())}
    dt = [L["dtw_um"] for L in ok if "dtw_um" in L]
    if dt:
        out["dtw_mean_um"] = float(np.mean(dt))
    rec = [L for L in ok if "recognised_ok" in L]
    if rec:
        out["recognition_accuracy"] = float(np.mean([L["recognised_ok"] for L in rec]))
        out["recognition_margin_median"] = float(np.median([L["margin"] for L in rec]))
    return out
