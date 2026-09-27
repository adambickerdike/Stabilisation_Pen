"""Stroke segmentation, resampling and capture-fidelity analysis.

Segmentation works on the *original* layer and only ever produces derived
layers: a stroke table (pen-down/up runs of the logged ``stroke_id``, with
flags for suspiciously short strokes, dropouts and missing pen events) and
line/word groupings as stroke-id ranges.

The capture-fidelity analysis quantifies the error that the ICD 0x02 stroke
format itself (200 Hz, 1 um, 1 ms) introduces relative to a high-rate
reference: the coupled simulator's deposited-ink traces
(``results/sim/nominal/traces_*.npz``, 1 kHz float32, decimated by
``sim/run_nominal.py`` from the 2 kHz simulation).  Evidence status:
SIMULATION-DERIVED analysis on synthetic handwriting; not a measurement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import __version__
from ._util import (file_sha256, ranges_from_ids, rel_to_repo, git_revision, environment_info,
                    utc_now)
from .logfmt import EventCode, ParsedLog, RESEARCH_DTYPE
from .notes import NoteStore, OriginalLayer, ValidationError

SEGMENTER_ID = f"penapp.capture.segment@{__version__}"
HAND_PATH_ID = f"penapp.capture.hand_path_from_research@{__version__}"
FIDELITY_ID = f"penapp.capture.fidelity@{__version__}"
FORMAT_PERIOD_MS = 5          # 200 Hz stroke samples (ICD 2, 4.3)


# ======================================================== raw contact runs
def contact_intervals(contact: np.ndarray) -> List[Tuple[int, int]]:
    """Half-open index intervals ``[start, stop)`` of consecutive True values."""
    c = np.asarray(contact, bool)
    if not c.size:
        return []
    d = np.diff(np.r_[0, c.astype(np.int8), 0])
    starts = np.flatnonzero(d == 1)
    stops = np.flatnonzero(d == -1)
    return list(zip(starts.tolist(), stops.tolist()))


# ============================================================ stroke table
@dataclass
class StrokeInfo:
    stroke_id: int
    i0: int                   # first sample index in the original layer
    i1: int                   # one past the last sample index
    t0_ms: int
    t1_ms: int
    n: int
    bbox_um: List[int]
    length_um: float
    flags: List[str] = field(default_factory=list)

    @property
    def cx(self) -> float:
        return 0.5 * (self.bbox_um[0] + self.bbox_um[2])

    @property
    def cy(self) -> float:
        return 0.5 * (self.bbox_um[1] + self.bbox_um[3])

    @property
    def height(self) -> float:
        return float(self.bbox_um[3] - self.bbox_um[1])

    @property
    def width(self) -> float:
        return float(self.bbox_um[2] - self.bbox_um[0])

    def to_json(self) -> dict:
        return {"stroke_id": self.stroke_id, "i0": self.i0, "i1": self.i1, "t0_ms": self.t0_ms,
                "t1_ms": self.t1_ms, "n": self.n, "bbox_um": self.bbox_um,
                "length_um": round(self.length_um, 1), "flags": self.flags}


def stroke_table(orig: OriginalLayer, *, events: Optional[Sequence[dict]] = None,
                 period_ms: int = FORMAT_PERIOD_MS, short_ms: int = 25,
                 event_tol_ms: int = 10) -> List[StrokeInfo]:
    """Pen-down/up segmentation of the original layer by logged ``stroke_id``.

    Flags (never corrections): ``single_sample``, ``short`` (duration below
    ``short_ms``: possible contact bounce), ``dropout`` (gap above 1.5 sample
    periods inside a stroke), ``non_contiguous`` (the id appears in more than
    one run), ``no_pen_down_event`` / ``no_pen_up_event`` (when events are given).
    """
    s = orig.samples
    runs = orig.stroke_runs
    seen: Dict[int, int] = {}
    for sid, _, _ in runs:
        seen[sid] = seen.get(sid, 0) + 1
    downs = ups = None
    if events is not None:
        downs = np.array([e["t_us"] for e in events if e["code"] == EventCode.PEN_DOWN], dtype=np.int64)
        ups = np.array([e["t_us"] for e in events if e["code"] == EventCode.PEN_UP], dtype=np.int64)
    out = []
    for sid, a, b in runs:
        seg = s[a:b]
        x = seg["x_um"].astype(np.int64)
        y = seg["y_um"].astype(np.int64)
        t = seg["t_ms"].astype(np.int64)
        length = float(np.sum(np.hypot(np.diff(x), np.diff(y)))) if len(seg) > 1 else 0.0
        flags = []
        if len(seg) == 1:
            flags.append("single_sample")
        if t[-1] - t[0] < short_ms:
            flags.append("short")
        if len(seg) > 1 and np.max(np.diff(t)) > 1.5 * period_ms:
            flags.append("dropout")
        if seen[sid] > 1:
            flags.append("non_contiguous")
        if downs is not None and events:
            if not len(downs) or np.min(np.abs(downs - t[0] * 1000)) > (event_tol_ms + period_ms) * 1000:
                flags.append("no_pen_down_event")
            if not len(ups) or np.min(np.abs(ups - t[-1] * 1000)) > (event_tol_ms + period_ms) * 1000:
                flags.append("no_pen_up_event")
        out.append(StrokeInfo(int(sid), int(a), int(b), int(t[0]), int(t[-1]), int(len(seg)),
                              [int(x.min()), int(y.min()), int(x.max()), int(y.max())], length, flags))
    return out


# ============================================================ lines, words
def estimate_x_height(strokes: Sequence[StrokeInfo]) -> Optional[float]:
    h = np.array([st.height for st in strokes], float)
    if not len(h):
        return None
    ref = np.percentile(h, 90)
    big = h[h > 0.2 * ref]
    return float(np.median(big)) if len(big) else None


def group_lines_words(strokes: Sequence[StrokeInfo], *, x_height_um: Optional[float] = None,
                      line_factor: float = 1.1, word_gap_factor: float = 0.6):
    """Group strokes (in writing order) into lines and words.

    New line: the stroke's vertical centre departs from the running median of
    the current line by more than ``line_factor`` x-heights.  New word: the
    stroke starts more than ``word_gap_factor`` x-heights right of the current
    word's right edge.  Heuristic for left-to-right scripts; returns
    (x_height, [[word strokes, ...] per line]).
    """
    h = x_height_um if x_height_um is not None else estimate_x_height(strokes)
    if h is None or h <= 0:
        return h, []
    lines: List[List[List[StrokeInfo]]] = []
    line_cys: List[float] = []
    for st in sorted(strokes, key=lambda s: (s.t0_ms, s.stroke_id)):
        if not lines or abs(st.cy - float(np.median(line_cys))) > line_factor * h:
            lines.append([[st]])
            line_cys = [st.cy]
            continue
        line_cys.append(st.cy)
        word = lines[-1][-1]
        right = max(w.bbox_um[2] for w in word)
        if st.bbox_um[0] - right > word_gap_factor * h:
            lines[-1].append([st])
        else:
            word.append(st)
    return h, lines


def _bbox_union(strokes: Iterable[StrokeInfo]) -> List[int]:
    b = np.array([s.bbox_um for s in strokes])
    return [int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 2].max()), int(b[:, 3].max())]


def segmentation_payload(orig: OriginalLayer, *, events=None, **params) -> Tuple[dict, dict]:
    table = stroke_table(orig, events=events, **{k: v for k, v in params.items()
                                                  if k in ("period_ms", "short_ms", "event_tol_ms")})
    gparams = {k: v for k, v in params.items() if k in ("x_height_um", "line_factor", "word_gap_factor")}
    h, lines = group_lines_words(table, **gparams)
    spans = []
    for li, line in enumerate(lines):
        lid = f"l{li}"
        spans.append({"span_id": lid, "level": "line",
                      "stroke_ranges": ranges_from_ids(s.stroke_id for w in line for s in w),
                      "bbox_um": _bbox_union(s for w in line for s in w)})
        for wi, word in enumerate(line):
            spans.append({"span_id": f"{lid}.w{wi}", "level": "word", "parent": lid,
                          "stroke_ranges": ranges_from_ids(s.stroke_id for s in word),
                          "bbox_um": _bbox_union(word)})
    payload = {"x_height_um": None if h is None else round(float(h), 1),
               "strokes": [st.to_json() for st in table], "spans": spans}
    used = {"period_ms": FORMAT_PERIOD_MS, "short_ms": 25, "event_tol_ms": 10, "line_factor": 1.1,
            "word_gap_factor": 0.6}
    used.update(params)
    return payload, used


def add_segmentation_layer(store: NoteStore, note_id: str, **params) -> dict:
    note = store.get_note(note_id)
    orig = store.get_original(note["original_sha256"])
    payload, used = segmentation_payload(orig, events=note["events"], **params)
    return store.add_layer(kind="segmentation", note_ids=[note_id], created_by=SEGMENTER_ID,
                           inputs=[{"type": "original", "sha256": orig.sha256,
                                    "stroke_ranges": ranges_from_ids(orig.stroke_ids)}]
                           if orig.n_samples else [{"type": "original", "sha256": orig.sha256}],
                           payload=payload, params=used)


# ============================================================ hand path
def hand_path_payload(orig: OriginalLayer, research: np.ndarray, research_t_us: np.ndarray,
                      *, max_gap_us: int = 2000) -> dict:
    """Hand-path estimate at each stroke-sample time from research-frame p_H.

    p_H (fused housing position, 0.1 um, page frame) is linearly interpolated to
    the stroke-sample times; points farther than ``max_gap_us`` from any frame
    are omitted.  Assumes p_H and the stroke x, y share the page origin
    (ICD ambiguity A9).
    """
    t_r = np.asarray(research_t_us, np.int64)
    if len(research) != len(t_r):
        raise ValidationError("research frames and time stamps differ in length")
    order = np.argsort(t_r, kind="stable")
    t_r = t_r[order]
    px = research["p_Hx"].astype(np.float64)[order] * 0.1
    py = research["p_Hy"].astype(np.float64)[order] * 0.1
    s = orig.samples
    strokes = []
    for sid, a, b in orig.stroke_runs:
        t_ms = s["t_ms"][a:b].astype(np.int64)
        tq = t_ms * 1000
        if not len(t_r):
            break
        j = np.clip(np.searchsorted(t_r, tq), 1, len(t_r) - 1)
        gap = np.minimum(np.abs(t_r[j] - tq), np.abs(t_r[j - 1] - tq))
        ok = (gap <= max_gap_us) & (tq >= t_r[0]) & (tq <= t_r[-1])
        if not ok.any():
            continue
        xs = np.interp(tq[ok], t_r, px)
        ys = np.interp(tq[ok], t_r, py)
        strokes.append({"stroke_id": int(sid), "t_ms": t_ms[ok].tolist(),
                        "x_um": np.round(xs, 1).tolist(), "y_um": np.round(ys, 1).tolist()})
    return {"method": "research-frame p_H (0x01 p_Hx, p_Hy) linearly interpolated to stroke-sample times",
            "evidence_status": "derived estimate; synthetic when the log is synthetic", "strokes": strokes}


def add_hand_path_layer(store: NoteStore, note_id: str, parsed: ParsedLog, source_sha256: str) -> Optional[dict]:
    if not len(parsed.research):
        return None
    note = store.get_note(note_id)
    orig = store.get_original(note["original_sha256"])
    payload = hand_path_payload(orig, parsed.research, parsed.research_t_us)
    if not payload["strokes"]:
        return None
    ids = [st["stroke_id"] for st in payload["strokes"]]
    return store.add_layer(kind="hand_path_estimate", note_ids=[note_id], created_by=HAND_PATH_ID,
                           inputs=[{"type": "original", "sha256": orig.sha256, "stroke_ranges": ranges_from_ids(ids)},
                                   {"type": "source_file", "sha256": source_sha256, "record_type": 1,
                                    "fields": ["t_us", "p_Hx", "p_Hy"]}],
                           payload=payload, params={"max_gap_us": 2000})


# ============================================================ resampling
def resample_time(t_ms: np.ndarray, xy: np.ndarray, rate_hz: float) -> Tuple[np.ndarray, np.ndarray]:
    """Uniform-time resampling by linear interpolation (endpoints kept)."""
    t = np.asarray(t_ms, float)
    xy = np.asarray(xy, float)
    if len(t) < 2:
        return t.copy(), xy.copy()
    step = 1000.0 / rate_hz
    tn = np.arange(t[0], t[-1] + 1e-9, step)
    if tn[-1] < t[-1]:
        tn = np.r_[tn, t[-1]]
    return tn, np.column_stack([np.interp(tn, t, xy[:, 0]), np.interp(tn, t, xy[:, 1])])


def resample_arclength(xy: np.ndarray, spacing: float) -> np.ndarray:
    """Points at uniform arc-length spacing along the polyline (endpoints kept)."""
    xy = np.asarray(xy, float)
    if len(xy) < 2:
        return xy.copy()
    keep = np.r_[True, np.any(np.diff(xy, axis=0) != 0, axis=1)]
    xy = xy[keep]
    if len(xy) < 2:
        return xy[:1].copy()
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    sn = np.arange(0.0, s[-1], spacing)
    sn = np.r_[sn, s[-1]] if sn[-1] < s[-1] else sn
    return np.column_stack([np.interp(sn, s, xy[:, 0]), np.interp(sn, s, xy[:, 1])])


def densify(xy: np.ndarray, max_step: float, t: Optional[np.ndarray] = None):
    """Insert collinear points so that no edge exceeds ``max_step`` (vertices kept).

    If per-vertex parameters ``t`` (e.g. time stamps) are given they are
    interpolated too and ``(xy, t)`` is returned.
    """
    xy = np.asarray(xy, float)
    if len(xy) < 2:
        return (xy.copy(), np.asarray(t, float).copy()) if t is not None else xy.copy()
    seg = np.diff(xy, axis=0)
    k = np.maximum(1, np.ceil(np.hypot(seg[:, 0], seg[:, 1]) / max_step).astype(np.int64))
    idx = np.repeat(np.arange(len(seg)), k)
    frac = (np.arange(int(k.sum())) - np.repeat(np.cumsum(k) - k, k)) / np.repeat(k, k)
    out = np.vstack([xy[idx] + seg[idx] * frac[:, None], xy[-1:]])
    if t is None:
        return out
    t = np.asarray(t, float)
    return out, np.r_[t[idx] + np.diff(t)[idx] * frac, t[-1]]


# ======================================================== Frechet distance
def discrete_frechet_reference(P, Q) -> float:
    """Eiter-Mannila discrete Frechet distance, plain O(nm) loops (test reference)."""
    P = np.asarray(P, float)
    Q = np.asarray(Q, float)
    n, m = len(P), len(Q)
    ca = np.full((n, m), np.inf)
    for i in range(n):
        for j in range(m):
            d = math.hypot(*(P[i] - Q[j]))
            if i == 0 and j == 0:
                ca[i, j] = d
            else:
                best = min(ca[i - 1, j] if i else np.inf, ca[i, j - 1] if j else np.inf,
                           ca[i - 1, j - 1] if i and j else np.inf)
                ca[i, j] = max(d, best)
    return float(ca[-1, -1])


def _frechet_antidiagonal(P: np.ndarray, Q: np.ndarray) -> float:
    """Exact discrete Frechet distance, numpy-vectorised over anti-diagonals."""
    n, m = len(P), len(Q)
    p2 = p1 = None
    lo2 = lo1 = 0
    for k in range(n + m - 1):
        lo, hi = max(0, k - m + 1), min(n - 1, k)
        i = np.arange(lo, hi + 1)
        j = k - i
        d = np.hypot(P[i, 0] - Q[j, 0], P[i, 1] - Q[j, 1])
        if k == 0:
            cur = d
        else:
            best = np.full(len(i), np.inf)
            # (i-1, j) and (i, j-1) lie on diagonal k-1
            for di in (1, 0):
                src = i - di
                ok = (src >= lo1) & (src < lo1 + len(p1))
                best[ok] = np.minimum(best[ok], p1[src[ok] - lo1])
            if p2 is not None:           # (i-1, j-1) on diagonal k-2
                src = i - 1
                ok = (src >= lo2) & (src < lo2 + len(p2)) & (j >= 1)
                best[ok] = np.minimum(best[ok], p2[src[ok] - lo2])
            cur = np.maximum(d, best)
        p2, lo2 = p1, lo1
        p1, lo1 = cur, lo
    return float(p1[-1])


try:                                        # numba is already a dependency of sim/
    import numba as _nb

    @_nb.njit(cache=True)
    def _frechet_band_nb(P, Q, lo, hi):     # pragma: no cover - compiled
        """Banded DP; returns (banded optimum, lower bound of any band-leaving path).

        A monotone path that leaves the band does so first through a boundary
        cell c whose in-band predecessor p has banded value ca(p); its value is
        at least max(d(c), min ca(p)).  If the minimum of that bound over all
        boundary cells is >= the banded optimum, the banded optimum is global.
        """
        n = P.shape[0]
        m = Q.shape[0]
        inf = np.inf
        prev = np.full(m, inf)
        cur = np.full(m, inf)
        exit_lb = inf
        for i in range(n):
            if i >= 2:
                for j in range(lo[i - 2], hi[i - 2] + 1):
                    cur[j] = inf
            a = lo[i]
            b = hi[i]
            if i > 0:                        # left boundary: (i, j) for lo[i-1] <= j < lo[i]
                for j in range(lo[i - 1], a):
                    pm = prev[j]
                    if j - 1 >= lo[i - 1] and prev[j - 1] < pm:
                        pm = prev[j - 1]
                    if pm < exit_lb:
                        dx = P[i, 0] - Q[j, 0]
                        dy = P[i, 1] - Q[j, 1]
                        d = math.sqrt(dx * dx + dy * dy)
                        lb = d if d > pm else pm
                        if lb < exit_lb:
                            exit_lb = lb
            for j in range(a, b + 1):
                dx = P[i, 0] - Q[j, 0]
                dy = P[i, 1] - Q[j, 1]
                d = math.sqrt(dx * dx + dy * dy)
                if i == 0 and j == 0:
                    cur[j] = d
                    continue
                best = inf
                if i > 0:
                    if prev[j] < best:
                        best = prev[j]
                    if j > 0 and prev[j - 1] < best:
                        best = prev[j - 1]
                if j > a and cur[j - 1] < best:
                    best = cur[j - 1]
                cur[j] = d if d > best else best
            if b + 1 < m:                    # right boundary: (i, hi[i] + 1)
                pm = cur[b]
                if i > 0 and hi[i - 1] == b and prev[b] < pm:
                    pm = prev[b]
                if pm < exit_lb:
                    dx = P[i, 0] - Q[b + 1, 0]
                    dy = P[i, 1] - Q[b + 1, 1]
                    d = math.sqrt(dx * dx + dy * dy)
                    lb = d if d > pm else pm
                    if lb < exit_lb:
                        exit_lb = lb
            tmp = prev
            prev = cur
            cur = tmp
        return prev[m - 1], exit_lb

    HAVE_NUMBA = True
except Exception:                           # pragma: no cover - fallback path
    HAVE_NUMBA = False


def _arclength_keys(P: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    sP = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    sQ = np.r_[0.0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    return sP * (sQ[-1] / sP[-1] if sP[-1] > 0 else 0.0), sQ


def _band(kP: np.ndarray, kQ: np.ndarray, width: float) -> Tuple[np.ndarray, np.ndarray]:
    """Monotone, connected index band {j : |kQ[j] - kP[i]| <= width} per row i."""
    m = len(kQ)
    lo = np.clip(np.searchsorted(kQ, kP - width, side="left"), 0, m - 1)
    hi = np.clip(np.searchsorted(kQ, kP + width, side="right") - 1, 0, m - 1)
    lo[0] = 0
    hi[-1] = m - 1
    hi = np.maximum.accumulate(np.maximum(hi, lo))
    lo = np.minimum(lo, hi)
    lo[1:] = np.minimum(lo[1:], hi[:-1] + 1)      # a monotone path needs lo[i+1] <= hi[i] + 1
    lo = np.maximum.accumulate(lo)
    return lo.astype(np.int64), hi.astype(np.int64)


def discrete_frechet(P, Q, *, keys: Optional[Tuple[np.ndarray, np.ndarray]] = None,
                     width: Optional[float] = None) -> float:
    """Exact discrete Frechet distance between vertex sequences P and Q.

    With numba the dynamic programme runs in a band around a monotone
    correspondence ``keys = (kP, kQ)`` (non-decreasing parameters in common
    units, e.g. time stamps; default: arc length scaled to equal length) and is
    *certified*: any coupling that leaves the band must pass a boundary cell
    whose value is at least max(distance, value of its in-band predecessor);
    if that bound is not below the banded optimum the optimum is global,
    otherwise the band is doubled.  Without numba (or for small inputs) the full
    anti-diagonal DP is used.  Both paths return identical values.
    """
    P = np.ascontiguousarray(P, dtype=np.float64)
    Q = np.ascontiguousarray(Q, dtype=np.float64)
    if not len(P) or not len(Q):
        raise ValueError("empty polyline")
    if len(P) == 1 or len(Q) == 1:
        A, B = (P, Q) if len(P) == 1 else (Q, P)
        return float(np.max(np.hypot(B[:, 0] - A[0, 0], B[:, 1] - A[0, 1])))
    if not HAVE_NUMBA or len(P) * len(Q) < 40000:
        return _frechet_antidiagonal(P, Q)
    if keys is None:
        kP, kQ = _arclength_keys(P, Q)
        w = 200.0 if width is None else float(width)
    else:
        kP, kQ = (np.asarray(k, np.float64) for k in keys)
        if len(kP) != len(P) or len(kQ) != len(Q) or np.any(np.diff(kP) < 0) or np.any(np.diff(kQ) < 0):
            raise ValueError("keys must be non-decreasing and match the polylines")
        w = 5.0 if width is None else float(width)
    span = max(kP[-1] - kP[0], kQ[-1] - kQ[0], 1e-9)
    while True:
        lo, hi = _band(kP, kQ, w)
        val, exit_lb = _frechet_band_nb(P, Q, lo, hi)
        if exit_lb >= val or bool(np.all(lo == 0) and np.all(hi == len(Q) - 1)):
            return float(val)
        if w > 2.0 * span:
            return _frechet_antidiagonal(P, Q)       # pragma: no cover - degenerate keys
        w *= 2.0


# ===================================================== capture fidelity
VARIANTS = {
    "format_point": "ICD 0x02 as specified: instantaneous sample every 5 ms, x/y rounded to 1 um (headline)",
    "sampling_only": "200 Hz point sampling without rounding (isolates temporal sampling)",
    "quantisation_only": "1 kHz reference rounded to 1 um (isolates spatial quantisation)",
    "format_boxcar5": "200 Hz from a centred 5-sample (5 ms) boxcar mean, rounded to 1 um (alternative decimation)",
    "format_point_endpoints": "format_point plus extra samples at the pen-down and pen-up instants (proposed ICD change)",
}


@dataclass
class Trace:
    name: str
    path: str
    sha256: str
    t_ms: np.ndarray
    xy_um: np.ndarray            # float, relative to the first-contact position (page origin)
    contact: np.ndarray


def load_trace(path) -> Trace:
    d = np.load(path)
    t_ms = np.round(d["t"].astype(np.float64) * 1000.0).astype(np.int64)
    if len(t_ms) > 1 and not np.all(np.diff(t_ms) == 1):
        raise ValueError(f"{path}: expected a uniform 1 kHz time base")
    tip = d["tip"].astype(np.float64)
    contact = d["contact"].astype(bool)
    if not contact.any():
        raise ValueError(f"{path}: no contact samples")
    origin = tip[np.flatnonzero(contact)[0]]
    name = Path(path).stem.replace("traces_", "")
    return Trace(name, rel_to_repo(path), file_sha256(path), t_ms, (tip - origin) * 1e6, contact)


def _capture(tr: Trace, a: int, b: int, variant: str, phase: int, period: int = FORMAT_PERIOD_MS):
    idx = np.arange(a, b)
    if variant == "quantisation_only":
        grid = idx
    else:
        grid = idx[(tr.t_ms[idx] - phase) % period == 0]
    if variant == "format_point_endpoints":
        grid = np.unique(np.r_[a, grid, b - 1])
    if not len(grid):
        return grid, np.zeros(0, np.int64), np.zeros((0, 2))
    if variant == "format_boxcar5":
        xy = np.array([tr.xy_um[max(a, g - 2):min(b, g + 3)].mean(axis=0) for g in grid])
    else:
        xy = tr.xy_um[grid]
    if variant != "sampling_only":
        xy = np.rint(xy)
    return grid, tr.t_ms[grid], xy


def stroke_fidelity(tr: Trace, a: int, b: int, variant: str, phase: int, *, densify_um: float = 2.0,
                    frechet: bool = True, vertex_frechet: bool = False) -> dict:
    """Error of one captured stroke against the 1 kHz reference stroke [a, b)."""
    ref_t = tr.t_ms[a:b]
    ref = tr.xy_um[a:b]
    grid, cap_t, cap = _capture(tr, a, b, variant, phase)
    v = np.hypot(*np.diff(ref, axis=0).T) if len(ref) > 1 else np.zeros(0)   # um per ms == mm/s
    acc = np.hypot(*np.diff(ref, 2, axis=0).T) if len(ref) > 2 else np.zeros(1)  # um/ms^2 == m/s^2
    row = {"i0": int(a), "i1": int(b), "t0_ms": int(ref_t[0]), "duration_ms": int(b - a),
           "path_length_mm": round(float(v.sum()) / 1000.0, 3),
           "peak_speed_mm_s": round(float(v.max()) if len(v) else 0.0, 2),
           "peak_accel_m_s2": round(float(acc.max()), 2),
           "n_ref": int(b - a), "n_capture": int(len(grid))}
    period = 1 if variant == "quantisation_only" else FORMAT_PERIOD_MS
    # linear-interpolation error bound |e| <= a_max T^2 / 8 (+ rounding radius sqrt(2)/2 um)
    row["interp_bound_um"] = None if variant == "format_boxcar5" else round(
        float(acc.max()) * period ** 2 / 8.0 + (0.0 if variant == "sampling_only" else math.sqrt(0.5)), 3)
    if not len(grid):
        row.update({"missed": True})
        return row
    row["missed"] = False
    inner = (ref_t >= cap_t[0]) & (ref_t <= cap_t[-1])
    if len(cap) > 1:
        rx = np.interp(ref_t[inner], cap_t, cap[:, 0])
        ry = np.interp(ref_t[inner], cap_t, cap[:, 1])
    else:
        rx = np.full(int(inner.sum()), cap[0, 0])
        ry = np.full(int(inner.sum()), cap[0, 1])
    dev_in = np.hypot(ref[inner, 0] - rx, ref[inner, 1] - ry)
    before = ref_t < cap_t[0]
    after = ref_t > cap_t[-1]
    dev_end = np.r_[np.hypot(*(ref[before] - cap[0]).T) if before.any() else np.zeros(0),
                    np.hypot(*(ref[after] - cap[-1]).T) if after.any() else np.zeros(0)]
    dev_all = np.r_[dev_in, dev_end]
    row.update({
        "max_dev_um": round(float(dev_all.max()), 3),
        "rms_dev_um": round(float(np.sqrt(np.mean(dev_all ** 2))), 3),
        "interior_max_dev_um": round(float(dev_in.max()), 3) if len(dev_in) else 0.0,
        "interior_rms_dev_um": round(float(np.sqrt(np.mean(dev_in ** 2))), 3) if len(dev_in) else 0.0,
        "end_truncation_max_um": round(float(dev_end.max()), 3) if len(dev_end) else 0.0,
        "n_interior": int(inner.sum()), "n_end": int(len(dev_end)),
        "_sq_interior": float(np.sum(dev_in ** 2)), "_sq_all": float(np.sum(dev_all ** 2)),
    })
    if len(dev_in):
        k = int(np.argmax(dev_in))
        row["interior_max_at_ms"] = int(ref_t[inner][k] - ref_t[0])
    if frechet:
        # the time-aligned coupling bounds the Frechet distance: seed the search band with it
        Pd, tP = densify(ref, densify_um, t=ref_t)
        Qd, tQ = densify(cap, densify_um, t=cap_t)
        fd = discrete_frechet(Pd, Qd, keys=(tP, tQ), width=float(FORMAT_PERIOD_MS))
        row["frechet_um"] = round(fd, 3)
        row["frechet_continuous_bracket_um"] = [round(max(0.0, fd - densify_um), 3), round(fd, 3)]
    if vertex_frechet:
        row["frechet_vertices_um"] = round(discrete_frechet(ref, cap, keys=(ref_t, cap_t),
                                                            width=float(FORMAT_PERIOD_MS)), 3)
    return row


def _aggregate(rows: List[dict], main_ms: int) -> dict:
    main = [r for r in rows if r["duration_ms"] >= main_ms]
    short = [r for r in rows if r["duration_ms"] < main_ms]
    got = [r for r in main if not r["missed"]]
    out = {"n_stroke_evaluations": len(rows), "n_main": len(main), "n_short": len(short),
           "short_missed": sum(r["missed"] for r in short),
           "short_single_sample": sum((not r["missed"]) and r["n_capture"] == 1 for r in short),
           "main_missed": sum(r["missed"] for r in main)}
    if got:
        worst = max(got, key=lambda r: r["max_dev_um"])
        n_in = sum(r["n_interior"] for r in got)
        n_all = sum(r["n_interior"] + r["n_end"] for r in got)
        out.update({
            "max_dev_um": worst["max_dev_um"],
            "max_dev_at": {k: worst[k] for k in ("trace", "phase_ms", "i0", "duration_ms")},
            "rms_dev_um": round(math.sqrt(sum(r["_sq_all"] for r in got) / n_all), 3),
            "interior_max_dev_um": max(r["interior_max_dev_um"] for r in got),
            "interior_rms_dev_um": round(math.sqrt(sum(r["_sq_interior"] for r in got) / n_in), 3),
            "end_truncation_max_um": max(r["end_truncation_max_um"] for r in got),
        })
        early = [r for r in got if r.get("interior_max_at_ms") is not None]
        if early:
            out["interior_max_in_first_50ms"] = f"{sum(r['interior_max_at_ms'] < 50 for r in early)}/{len(early)}"
        bounded = [r for r in got if r["interp_bound_um"] is not None]
        if bounded:
            out["interior_within_interp_bound"] = (
                f"{sum(r['interior_max_dev_um'] <= r['interp_bound_um'] + 1e-6 for r in bounded)}/{len(bounded)}")
        fr = [r["frechet_um"] for r in got if "frechet_um" in r]
        if fr:
            out.update({"frechet_max_um": max(fr), "frechet_median_um": round(float(np.median(fr)), 3),
                        "frechet_p95_um": round(float(np.percentile(fr, 95)), 3)})
    sg = [r for r in short if not r["missed"]]
    if sg:
        out["short_max_dev_um"] = max(r["max_dev_um"] for r in sg)
    return out


def fidelity_analysis(trace_paths: Sequence, *, phases: Sequence[int] = tuple(range(FORMAT_PERIOD_MS)),
                      variants: Sequence[str] = tuple(VARIANTS), densify_um: float = 2.0,
                      main_ms: int = 50, frechet: bool = True) -> dict:
    """Capture fidelity of the ICD stroke format against high-rate reference traces."""
    traces = [load_trace(p) for p in trace_paths]
    per_variant: Dict[str, List[dict]] = {v: [] for v in variants}
    for tr in traces:
        for a, b in contact_intervals(tr.contact):
            for var in variants:
                for ph in (phases if var != "quantisation_only" else (0,)):
                    row = stroke_fidelity(tr, a, b, var, ph, densify_um=densify_um, frechet=frechet,
                                          vertex_frechet=(var == "format_point" and frechet))
                    row["trace"] = tr.name
                    row["phase_ms"] = int(ph)
                    per_variant[var].append(row)
    summary = {v: _aggregate(rows, main_ms) for v, rows in per_variant.items()}
    head = [r for r in per_variant.get("format_point", []) if not r["missed"] and r["duration_ms"] >= main_ms]
    vf = [r["frechet_vertices_um"] for r in head if "frechet_vertices_um" in r]
    if vf and "format_point" in summary:
        summary["format_point"]["frechet_vertices_only_max_um"] = max(vf)
        summary["format_point"]["frechet_vertices_only_median_um"] = round(float(np.median(vf)), 3)
    strokes = {}
    for tr in traces:
        strokes[tr.name] = [{"i0": a, "i1": b, "t0_ms": int(tr.t_ms[a]), "duration_ms": int(b - a)}
                            for a, b in contact_intervals(tr.contact)]
    detail = [{k: v for k, v in r.items() if not k.startswith("_")}
              for r in per_variant.get("format_point", [])]
    return {
        "meta": {
            "evidence_status": ("SIMULATION-DERIVED ANALYSIS: synthetic handwriting and tremor through the "
                                "coupled pen simulator (model M1); not a measurement of any person or device"),
            "generated_by": FIDELITY_ID, "generated_utc": utc_now(), "git_revision": git_revision(),
            "environment": environment_info(), "numba": HAVE_NUMBA,
            "inputs": [{"trace": tr.name, "path": tr.path, "sha256": tr.sha256, "n_samples": int(len(tr.t_ms)),
                        "rate_hz": 1000, "n_contact_intervals": len(strokes[tr.name])} for tr in traces],
            "reference": ("deposited-ink position 'tip' of each simulator trace at 1 kHz (float32, decimated by "
                          "sim/run_nominal.py from the 2 kHz simulation; scenario per results/sim/nominal/metrics.json: "
                          "test seed 200, 9 Hz 0.3 mm tremor, altitude 50 deg, 1 N); strokes = contiguous "
                          "'contact' runs; page origin = first contact position"),
            "format": {"rate_hz": 200, "xy_lsb_um": 1, "t_lsb_ms": 1, "source": "docs/icd.md 4.3"},
        },
        "method": {
            "variants": {v: VARIANTS[v] for v in variants},
            "phases_ms": list(phases),
            "phase_note": "the 5 ms sampling grid is evaluated at every 1 ms offset; worst cases are over phases",
            "time_aligned_deviation": ("captured samples are linearly interpolated at the reference time stamps; "
                                       "reference points before the first / after the last captured sample are "
                                       "compared with that endpoint (end truncation). max/rms over all points; "
                                       "this coupling bounds the Frechet distance from above"),
            "frechet": (f"exact discrete Frechet distance (Eiter-Mannila) between the reference and captured "
                        f"polylines after densifying both to edges <= {densify_um} um; the continuous Frechet "
                        f"distance lies in [value - {densify_um}, value]"),
            "frechet_vertices_only": ("discrete Frechet on the raw vertex sets (1 kHz vs 200 Hz) is reported for "
                                      "the headline variant only to show its sampling bias: with sparse vertices it "
                                      "is dominated by half the inter-sample spacing, not by capture error"),
            "interp_bound": "a_max * T^2 / 8 + sqrt(2)/2 um (linear interpolation + rounding), a_max from 1 kHz second differences",
            "main_stroke_min_ms": main_ms,
        },
        "summary": summary,
        "contact_intervals": strokes,
        "per_stroke_format_point": detail,
    }


def run_fidelity(trace_paths: Sequence, out_path, **kw) -> dict:
    from ._util import write_json
    res = fidelity_analysis(trace_paths, **kw)
    res["interpretation"] = interpret_fidelity(res)
    write_json(out_path, res)
    return res


def interpret_fidelity(res: dict) -> List[str]:
    s = res["summary"]
    out = []
    fp = s.get("format_point", {})
    if "max_dev_um" in fp:
        out.append(f"Headline (format_point, main strokes, worst over traces and sampling phases): time-aligned "
                   f"max deviation {fp['max_dev_um']} um, RMS {fp['rms_dev_um']} um; interior-only max "
                   f"{fp['interior_max_dev_um']} um, RMS {fp['interior_rms_dev_um']} um; densified discrete "
                   f"Frechet max {fp.get('frechet_max_um')} um (median {fp.get('frechet_median_um')} um).")
        out.append(f"End truncation dominates the maximum: up to {fp['end_truncation_max_um']} um because the "
                   f"first/last sample can fall up to 4 ms inside the contact interval while the pen moves.")
    fe = s.get("format_point_endpoints", {})
    if "max_dev_um" in fe:
        out.append(f"Adding samples at the pen-down/up instants reduces the max deviation to {fe['max_dev_um']} um "
                   f"(end truncation {fe['end_truncation_max_um']} um).")
    q = s.get("quantisation_only", {})
    if "max_dev_um" in q:
        out.append(f"1 um rounding alone contributes at most {q['max_dev_um']} um (RMS {q['rms_dev_um']} um); "
                   f"the format error is sampling-dominated.")
    if fp.get("short_missed") is not None:
        out.append(f"Short contacts (< {res['method']['main_stroke_min_ms']} ms, bounces in the simulator): "
                   f"{fp['short_missed']} of {fp['n_short']} phase-evaluations produced no sample and "
                   f"{fp['short_single_sample']} a single sample; the format cannot represent them faithfully.")
    out.append("Scale for comparison (research ledger OPT-02): DeltaPen optical-flow tracking reports 0.068 mm "
               "mean absolute error per 10 ms window, i.e. the sensing error, not the stroke format, is expected "
               "to dominate capture error.")
    out.append("These figures describe the format applied to simulated ink; they say nothing about sensor "
               "accuracy, which must be measured (bench protocol).")
    return out
