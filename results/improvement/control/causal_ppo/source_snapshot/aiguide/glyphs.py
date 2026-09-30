"""Single-line glyph font and geometry helpers.

The font is the one of app/penapp/synth.py (polylines in x-height units:
baseline y = 0, x-height 1, ascender 1.6, descender -0.6); it is imported,
not copied, so the app, the writer model and the templates share one font.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import ensure_paths

ensure_paths()
from penapp.synth import GLYPHS, glyph_width  # noqa: E402

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def strokes(ch: str) -> List[np.ndarray]:
    """Strokes of a glyph as (k, 2) arrays in x-height units."""
    return [np.asarray(s, float) for s in GLYPHS[ch]]


def width(ch: str) -> float:
    return float(glyph_width(ch))


def arclength(P: np.ndarray) -> np.ndarray:
    return np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def resample(P: np.ndarray, n: int) -> np.ndarray:
    """n points equally spaced in arclength along polyline P."""
    s = arclength(P)
    if s[-1] <= 0:
        return np.repeat(P[:1], n, axis=0)
    u = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])])


def resample_strokes(strs: Sequence[np.ndarray], n_total: int = 64) -> Tuple[np.ndarray, np.ndarray]:
    """Resample a multi-stroke shape to ~n_total points, allotted by stroke length.

    Returns (points (n, 2), stroke index per point).  Dots (zero-length strokes)
    get at least 2 points.
    """
    lens = np.array([max(arclength(s)[-1], 1e-9) for s in strs])
    alloc = np.maximum(2, np.round(n_total * lens / lens.sum()).astype(int))
    pts, sid = [], []
    for k, (s, m) in enumerate(zip(strs, alloc)):
        pts.append(resample(s, int(m)))
        sid.append(np.full(int(m), k))
    return np.vstack(pts), np.concatenate(sid)


def bbox(strs: Sequence[np.ndarray]) -> Tuple[float, float, float, float]:
    a = np.vstack(strs)
    return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def extent_y(ch: str) -> Tuple[float, float]:
    b = bbox(strokes(ch))
    return b[1], b[3]


GLYPH_SET: Dict[str, List[np.ndarray]] = {c: strokes(c) for c in GLYPHS}
