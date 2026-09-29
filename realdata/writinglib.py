"""The writing library: real recorded letters and words, with their timing, as HW1 and sim2 inputs.

Sources (sources.py):
  brush     real words (2-4 per recording) of 170 adults with real pen-down timing (10 ms points) and per-point
            letter labels.  The pen-up movements between strokes are not in the release: they are added as smooth
            in-air moves (ASSUMPTION timing below).  The physical size of each writer is DERIVED (calib.LABELS).
            Non-commercial research use: only aggregate numbers derived from it are committed.
  chartraj  real letters with real timing (one adult, 20 letters, 200 samples/s).  Words are COMPOSED from the
            writer's recorded letters (the letters are real; their placement on the line is ours).  CC BY 4.0: used for
            the committed before/after pictures.

Composition (both sources), ASSUMPTION values chosen before any simulation, as the aiguide writers' conventions:
  * in-air move between strokes: quintic Hermite from the end of a stroke (position, velocity) to the start of the
    next (position, velocity), duration 0.06 s + distance / 60 mm/s (aiguide v1: 0.06 s + distance / 45-75 mm/s),
    lift height 1.5 mm at mid-move (aiguide v1);
  * a note is written line by line: 2.6 letter heights between lines (the mean height of 'T', 'p', 'a' is the letter
    height of LIT PDT-06);
  * 0.2 s at rest before the first stroke and 0.3 s after the last (aiguide v1).
The note is built at 1 kHz with continuous position and velocity, then resampled by a cubic spline onto the
simulation grid (25 us, the HW1 step), so its acceleration is continuous (HW1's adapted hand path differentiates it
twice).

Outputs are aiguide ``Written`` objects (text, style, intended = stabpen.signals.Intended, letters, dt, meta):
exactly what model HW1 (handwriting.plant.scenario_from_written, handwriting.metrics) and sim2 scenarios
(sim.pensim.scenarios._assemble) take.
"""
from __future__ import annotations

import hashlib
import os
import json
import math
import re
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.interpolate import CubicSpline

from . import CACHE_DIR, ensure_paths
from . import calib as CB
from . import loaders as L
from .reader import WriterReader

ensure_paths()
from aiguide.writer import Letter, WriterStyle, Written  # noqa: E402
from stabpen import signals as sg  # noqa: E402

SIM_DT = 25e-6
BUILD_FS = 1000.0
AIR_BASE_S = 0.06           # ASSUMPTION (aiguide v1)
AIR_SPEED = 0.060           # m/s ASSUMPTION (aiguide v1 range 45-75 mm/s)
LIFT_H = 1.5e-3             # m ASSUMPTION (aiguide v1)
LINE_GAP_HEIGHTS = 2.6      # line pitch in letter heights (ASSUMPTION; 13 mm for 5 mm letters: wide ruled paper)
PDT06_MEDIAN_MM = 5.0       # LIT PDT-06: median letter height (mean of 'T', 'p', 'a') of healthy adults
PDT06_SD_MM = 1.4 / 1.349   # LIT PDT-06 IQR 1.4 mm -> SD of a normal distribution (CALC)
TPA_PER_XHEIGHT = (1.0 + 1.6 + 1.5) / 3.0   # mean of T, p, a heights in x-heights (ASSUMPTION, as sim2j.writers)
XLETTERS = set("acemnorsuvwxz")
SPLIT_TUNING_SHARE = 0.4


# ================================================================== splits
def split_of(source: str, writer: str) -> str:
    """Deterministic writer-level split: 40 % tuning, 60 % test (sha1 of source and writer id)."""
    h = int(hashlib.sha1(f"{source}:{writer}".encode()).hexdigest()[:8], 16) % 1000
    return "tuning" if h < SPLIT_TUNING_SHARE * 1000 else "test"


# ================================================================== geometry helpers
def _quintic_hermite(p0, v0, p1, v1, T: float, fs: float) -> np.ndarray:
    """Positions (n, 2) on [0, T) of the quintic with the given end positions and velocities and zero end
    accelerations (C2 at the joins when the neighbours have zero acceleration there; C1 otherwise)."""
    n = max(int(round(T * fs)), 2)
    s = np.arange(n) / n
    h00 = 1 - 10 * s ** 3 + 15 * s ** 4 - 6 * s ** 5
    h10 = s - 6 * s ** 3 + 8 * s ** 4 - 3 * s ** 5
    h01 = 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5
    h11 = -4 * s ** 3 + 7 * s ** 4 - 3 * s ** 5
    p0, v0, p1, v1 = (np.asarray(a, float) for a in (p0, v0, p1, v1))
    return (h00[:, None] * p0 + h10[:, None] * T * v0 + h01[:, None] * p1 + h11[:, None] * T * v1)


def _end_velocity(t: np.ndarray, xy: np.ndarray, which: str) -> np.ndarray:
    if len(t) < 3:
        return np.zeros(2)
    if which == "start":
        return (xy[2] - xy[0]) / max(t[2] - t[0], 1e-9)
    return (xy[-1] - xy[-3]) / max(t[-1] - t[-3], 1e-9)


@dataclass
class Stroke:
    t: np.ndarray               # (n,) s, from 0
    xy: np.ndarray              # (n, 2) m
    char: np.ndarray            # (n,) index into the note's text, -1 unknown
    air: Optional[np.ndarray] = None    # (m, 2) m: the RECORDED in-air points before this stroke (proximity), if any
    air_fs: float = 0.0                 # their sample rate (Hz)


AIR_GAP_MAX = 2.0e-3            # recorded in-air path used only if it joins both strokes within 2 mm (else the pen
                                # left the digitiser's proximity range and the timing is unknown)


@dataclass
class RealWritten(Written):
    """aiguide Written + the real-data provenance (source, writer, recordings used, scale label)."""
    reader: Optional[WriterReader] = None
    real: Dict = field(default_factory=dict)


def assemble(strokes: Sequence[Stroke], text: str, *, dt: float = SIM_DT, height_m: float, writer: str,
             source: str, meta: Optional[Dict] = None, reader: Optional[WriterReader] = None,
             per_stroke_letters: bool = False) -> RealWritten:
    """Join pen-down strokes with in-air moves into one continuous note and build its aiguide Written."""
    fs = BUILD_FS
    T_all, X_all, D_all, C_all, S_all, Z_all = [], [], [], [], [], []
    t_cur = 0.0
    first = strokes[0]
    p = first.xy[0] + np.array([-1.0e-3, 1.0e-3])
    v = np.zeros(2)

    def emit(xy, down, char, sid, lift):
        nonlocal t_cur
        n = len(xy)
        T_all.append(t_cur + np.arange(n) / fs)
        X_all.append(xy)
        D_all.append(np.full(n, down))
        C_all.append(char)
        S_all.append(np.full(n, sid))
        Z_all.append(lift)
        t_cur += n / fs

    emit(np.repeat(p[None, :], int(0.2 * fs), 0), False, -np.ones(int(0.2 * fs), int), -1, np.full(int(0.2 * fs), LIFT_H))
    n_rec_air = 0
    for si, st in enumerate(strokes):
        v1 = _end_velocity(st.t, st.xy, "start")
        d = float(np.hypot(*(st.xy[0] - p)))
        T = AIR_BASE_S + d / AIR_SPEED
        A = st.air if (st.air is not None and si > 0) else None
        if A is not None and len(A) >= 1 and st.air_fs > 0 and \
                float(np.hypot(*(A[0] - p))) <= AIR_GAP_MAX and float(np.hypot(*(A[-1] - st.xy[0]))) <= AIR_GAP_MAX:
            # the recorded hover path and its real duration (cubic spline through the recorded points, clamped to
            # the strokes' end velocities)
            m = len(A)
            ta = np.arange(m + 2) / st.air_fs
            pts = np.vstack([p[None, :], A, st.xy[0][None, :]])
            keep = np.concatenate([[True], np.hypot(*np.diff(pts, axis=0).T) > 0]) | (np.arange(m + 2) == m + 1)
            ta_, pts_ = ta[keep], pts[keep]
            if len(ta_) >= 3:
                cs = CubicSpline(ta_, pts_, axis=0, bc_type=((1, v), (1, v1)))
                air = cs(np.arange(0.0, ta_[-1], 1.0 / fs))
                n_rec_air += 1
            else:
                air = _quintic_hermite(p, v, st.xy[0], v1, max(T, (m + 1) / st.air_fs), fs)
        elif A is not None and st.air_fs > 0:
            air = _quintic_hermite(p, v, st.xy[0], v1, max(T, (len(A) + 1) / st.air_fs), fs)
        else:
            air = _quintic_hermite(p, v, st.xy[0], v1, T, fs)
        if len(air) < 2:
            air = _quintic_hermite(p, v, st.xy[0], v1, T, fs)
        s = np.arange(len(air)) / len(air)
        emit(air, False, -np.ones(len(air), int), -1, LIFT_H * np.sin(np.pi * s) ** 2 + (LIFT_H if si == 0 else 0.0) * (1 - s) ** 3)
        # the stroke, resampled at fs by a cubic spline of its own samples (its duration kept)
        te = np.arange(0.0, st.t[-1] + 0.5 / fs, 1.0 / fs)
        xy = CubicSpline(st.t, st.xy, axis=0)(te) if len(st.t) >= 4 else np.column_stack(
            [np.interp(te, st.t, st.xy[:, 0]), np.interp(te, st.t, st.xy[:, 1])])
        ch = st.char[np.clip(np.searchsorted(st.t, te, side="right") - 1, 0, len(st.t) - 1)]
        emit(xy, True, ch, si, np.zeros(len(te)))
        p = xy[-1]
        v = _end_velocity(te, xy, "end")
    away = p + np.array([1.5e-3, 1.0e-3])
    air = _quintic_hermite(p, v, away, np.zeros(2), AIR_BASE_S + 1.8e-3 / AIR_SPEED, fs)
    s = np.arange(len(air)) / len(air)
    emit(air, False, -np.ones(len(air), int), -1, LIFT_H * np.sin(0.5 * np.pi * s) ** 2)
    emit(np.repeat(away[None, :], int(0.3 * fs), 0), False, -np.ones(int(0.3 * fs), int), -1, np.full(int(0.3 * fs), LIFT_H))
    t1 = np.concatenate(T_all)
    X1 = np.vstack(X_all)
    D1 = np.concatenate(D_all)
    C1 = np.concatenate(C_all)
    S1 = np.concatenate(S_all)
    Z1 = np.concatenate(Z_all)
    # simulation grid: cubic spline of the 1 kHz note (C2), contact and labels by nearest 1 kHz sample
    t = np.arange(0.0, t1[-1], dt)
    xy = CubicSpline(t1, X1, axis=0)(t)
    k = np.clip(np.round(t * fs).astype(int), 0, len(t1) - 1)
    down = D1[k]
    lift = np.interp(t, t1, Z1)
    lift[down] = 0.0
    char = C1[k]
    sid = S1[k]
    it = sg.Intended(t=t, xy=np.ascontiguousarray(xy), pen_down=down.astype(bool), lift=lift, features=[])
    letters = _stroke_letters(text, t, xy, down, char, sid, height_m) if per_stroke_letters else \
        _letters(text, t, xy, down, char, sid, height_m)
    for Lt in letters:
        it.features.append(("letter", Lt.t0, Lt.t1, {"char": Lt.char, "glyph_index": Lt.glyph_index}))
    xh = height_m / TPA_PER_XHEIGHT
    style = WriterStyle(x_height_mm=xh * 1e3, slant_deg=0.0, width=1.0)
    real = {"source": source, "writer": writer, "letter_height_mm": height_m * 1e3, "x_height_mm": xh * 1e3,
            "duration_s": float(t[-1]), "pen_down_s": float(down.sum() * dt), "recorded_air_moves": int(n_rec_air),
            "air_moves": int(len(strokes)), **(meta or {})}
    # time span of each written line (for the reader): from the line's first to its last pen-down sample
    if real.get("lines"):
        starts = np.cumsum([0] + [len(l) + 1 for l in real["lines"][:-1]])
        spans = []
        for a, ln in zip(starts, real["lines"]):
            sel = np.flatnonzero((char >= a) & (char < a + len(ln)) & down)
            spans.append([float(t[sel[0]]), float(t[sel[-1]])] if len(sel) else [0.0, 0.0])
        real["line_spans"] = spans
    return RealWritten(text, style, it, letters, dt, meta={"synthetic": False, "real": real}, reader=reader, real=real)


def _stroke_letters(text: str, t, xy, down, char, sid, height_m: float) -> List[Letter]:
    """Pseudo-letters, one per pen-down stroke (for recordings without letter labels): the ink error is then taken
    per stroke; word_index = the line's word index of the stroke's line start."""
    out: List[Letter] = []
    starts = [i for i, c in enumerate(text) if c != " " and (i == 0 or text[i - 1] == " ")]
    for k in sorted(set(int(v) for v in np.unique(sid) if v >= 0)):
        idx = np.flatnonzero((sid == k) & down)
        if len(idx) < 2:
            continue
        a, b = int(idx[0]), int(idx[-1]) + 1
        ci = int(char[idx[0]])
        wi = sum(1 for s0 in starts if s0 <= ci) - 1 if ci >= 0 else 0
        Lt = Letter("?", max(ci, 0), len(out), max(wi, 0), (a, b), [(a, b)], [xy[a:b:40] if b - a > 80 else xy[a:b]],
                    height_m / TPA_PER_XHEIGHT, float(xy[a:b, 0].min()), float(xy[a:b, 1].min()))
        Lt.t0, Lt.t1 = float(t[a]), float(t[min(b, len(t) - 1)])
        out.append(Lt)
    return out


def _letters(text: str, t, xy, down, char, sid, height_m: float) -> List[Letter]:
    """aiguide Letter records from the per-sample character labels (index into text)."""
    out: List[Letter] = []
    gi = 0
    wi = 0
    for ti, ch in enumerate(text):
        if ch == " ":
            wi += 1
            continue
        idx = np.flatnonzero((char == ti) & down)
        if len(idx) == 0:
            out.append(Letter(ch, ti, gi, wi, (0, 0), [], [], height_m, 0.0, 0.0, 0.0, 0.0))
            gi += 1
            continue
        # contiguous runs of this letter's samples (a letter may span several strokes, or part of one)
        br = np.flatnonzero(np.diff(idx) > 1) + 1
        runs = np.split(idx, br)
        strokes = [(int(r[0]), int(r[-1]) + 1) for r in runs if len(r) >= 2]
        polys = [xy[a:b:40] if b - a > 80 else xy[a:b] for a, b in strokes]      # 1 kHz polylines
        a0, a1 = (strokes[0][0], strokes[-1][1]) if strokes else (int(idx[0]), int(idx[-1]) + 1)
        P = xy[idx]
        Lt = Letter(ch, ti, gi, wi, (a0, a1), strokes, polys, height_m / TPA_PER_XHEIGHT, float(P[:, 0].min()),
                    float(P[:, 1].min()))
        Lt.t0 = float(t[a0])
        Lt.t1 = float(t[min(a1, len(t) - 1)])
        out.append(Lt)
        gi += 1
    return out


# ================================================================== BRUSH notes
BRUSH_WRITERS_JSON = CACHE_DIR / "brush_writers.json"
_LOWER = re.compile(r"^[a-z]+( [a-z]+)*$")
_DRILL = re.compile(r"^(.)\1+$")                     # letter drills such as 'ppp' are not words


def _is_words(s: str) -> bool:
    return bool(_LOWER.match(s)) and not any(_DRILL.match(w) for w in s.split())


def brush_writer_stats(log=print, max_writers: Optional[int] = None) -> Dict:
    """Per writer (one pass over the release, cached): the lower-case-only recordings, the median pixel heights of
    'T', 'p' and 'a' and of the x-height letters, and the recordings' letter coverage."""
    if BRUSH_WRITERS_JSON.exists():
        d = json.loads(BRUSH_WRITERS_JSON.read_text())
        if max_writers is None or len(d["writers"]) >= max_writers:
            return d
    idx = L.brush_index()
    out = {}
    z = zipfile.ZipFile(L.BRUSH_ZIP)
    for wi, (w, members) in enumerate(sorted(idx.items(), key=lambda kv: int(kv[0]))):
        if max_writers is not None and wi >= max_writers:
            break
        heights: Dict[str, List[float]] = {}
        lower = []
        for m in members:
            try:
                sent, draw, ci = L.brush_load(m, z)
            except Exception:
                continue
            ys = -draw[:, 1]
            for k, ch in enumerate(sent):
                if ch in "Tpa" or ch in XLETTERS:
                    sel = ci == k
                    if sel.sum() >= 3:
                        heights.setdefault(ch, []).append(float(np.ptp(ys[sel])))
            s = sent.strip()
            if _is_words(s):
                labelled = {int(k) for k in np.unique(ci) if k >= 0}
                need = {k for k, c in enumerate(sent) if c != " "}
                if need <= labelled:
                    lower.append(m)
        med = {c: float(np.median(v)) for c, v in heights.items() if len(v) >= 2}
        tpa = [med[c] for c in "Tpa" if c in med]
        xs = [med[c] for c in XLETTERS if c in med]
        out[w] = {"n_recordings": len(members), "lowercase_recordings": lower,
                  "height_T_p_a_px": float(np.mean(tpa)) if len(tpa) == 3 else None,
                  "xheight_px": float(np.median(xs)) if xs else None, "split": split_of("brush", w)}
        if log and wi % 20 == 0:
            log(f"[brush] writer {w}: {len(members)} recordings, {len(lower)} lower-case")
    z.close()
    d = {"writers": out, "label": CB.LABELS["brush"]}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BRUSH_WRITERS_JSON.write_text(json.dumps(d))
    return d


def brush_scale(w: str, stats: Dict) -> Tuple[float, float]:
    """(m per px, target letter height m) for writer w: the mean height of its 'T', 'p', 'a' set to a draw from the
    healthy-adult distribution of LIT PDT-06 (seeded by the writer id; clipped to 3.6-6.4 mm).  Writers without all
    three letters use their x-height letters x 1.37 (ASSUMPTION, TPA_PER_XHEIGHT)."""
    s = stats["writers"][w]
    rng = np.random.default_rng(int(hashlib.sha1(f"brush-size:{w}".encode()).hexdigest()[:8], 16))
    target = float(np.clip(rng.normal(PDT06_MEDIAN_MM, PDT06_SD_MM), 3.6, 6.4)) * 1e-3
    px = s["height_T_p_a_px"] or ((s["xheight_px"] or 20.0) * TPA_PER_XHEIGHT)
    return target / max(px, 1e-6), target


def brush_reader(w: str, exclude: Sequence[str], scale: float, stats: Dict, max_per_letter: int = 8) -> WriterReader:
    """The writer's own clean letters from its OTHER lower-case recordings (never the ones in the note)."""
    inst: Dict[str, List[List[np.ndarray]]] = {}
    z = zipfile.ZipFile(L.BRUSH_ZIP)
    pool = [m for m in stats["writers"][w]["lowercase_recordings"] if m not in set(exclude)]
    pool += [m for m in L.brush_index()[w] if m not in set(exclude) and m not in pool]
    for m in pool:
        sent, draw, ci = L.brush_load(m, z)
        eos = draw[:, 2] > 0.5
        sid = np.r_[0, np.cumsum(eos[:-1])]
        xy = np.column_stack([draw[:, 0], -draw[:, 1]]) * scale
        for k, ch in enumerate(sent):
            if not ("a" <= ch <= "z") or len(inst.get(ch, [])) >= max_per_letter:
                continue
            sel = np.flatnonzero(ci == k)
            if len(sel) < 3:
                continue
            strokes = [xy[sel[sid[sel] == s]] for s in np.unique(sid[sel])]
            inst.setdefault(ch, []).append([s for s in strokes if len(s) >= 2])
        if len(inst) == 26 and all(len(v) >= max_per_letter for v in inst.values()):
            break
    z.close()
    return WriterReader(inst, max_per_letter=max_per_letter)


def brush_note(w: str, seed: int = 0, n_words: int = 10, dt: float = SIM_DT, stats: Optional[Dict] = None,
               with_reader: bool = True, max_lines: int = 5) -> Optional[RealWritten]:
    """A note of about n_words real words by BRUSH writer w: its lower-case recordings (seeded choice), one per
    line, each line a real recording (pen-down timing real, pen-up moves added)."""
    stats = stats or brush_writer_stats()
    s = stats["writers"].get(w)
    if not s or len(s["lowercase_recordings"]) < 2:
        return None
    scale, height = brush_scale(w, stats)
    rng = np.random.default_rng(int(hashlib.sha1(f"brush-note:{w}:{seed}".encode()).hexdigest()[:8], 16))
    pool = list(s["lowercase_recordings"])
    rng.shuffle(pool)
    chosen, words = [], 0
    z = zipfile.ZipFile(L.BRUSH_ZIP)
    recs = []
    for m in pool:
        r = L.brush_record(m, scale, z)
        nw = len(r.text.split())
        if words + nw > n_words + 1 and chosen:
            continue
        chosen.append(m)
        recs.append(r)
        words += nw
        if words >= n_words or len(chosen) >= max_lines:
            break
    z.close()
    reader = brush_reader(w, chosen, scale, stats) if with_reader else None
    text = " ".join(r.text.strip() for r in recs)
    if reader is not None and not reader.covers(text):
        # drop the lines with letters the reader has never seen from this writer
        keep = [r for r in recs if reader.covers(r.text)]
        if not keep:
            return None
        recs = keep
        text = " ".join(r.text.strip() for r in recs)
    strokes: List[Stroke] = []
    off = 0
    line_pitch = LINE_GAP_HEIGHTS * height
    for li, r in enumerate(recs):
        x0 = r.xy[:, 0].min()
        ytop = np.percentile(r.xy[:, 1], 90)
        shift = np.array([-x0, -li * line_pitch - ytop + height * 0.6])
        lead = len(r.text) - len(r.text.lstrip())
        for sidx in np.unique(r.stroke):
            sel = np.flatnonzero(r.stroke == sidx)
            if len(sel) < 2:
                continue
            ch = np.where(r.char[sel] >= lead, r.char[sel] - lead + off, -1)
            strokes.append(Stroke(t=r.t[sel] - r.t[sel][0], xy=r.xy[sel] + shift, char=ch))
        off += len(r.text.strip()) + 1
    meta = {"recordings": [r.rid for r in recs], "lines": [r.text.strip() for r in recs],
            "scale_mm_per_px": scale * 1e3, "split": s["split"],
            "scale_label": CB.LABELS["brush"], "licence": "BRUSH: non-commercial research use"}
    return assemble(strokes, text, dt=dt, height_m=height, writer=f"brush/{w}", source="brush", meta=meta, reader=reader)


def brush_writers(split: str, stats: Optional[Dict] = None, min_lower: int = 6) -> List[str]:
    stats = stats or brush_writer_stats()
    return sorted([w for w, s in stats["writers"].items() if s["split"] == split and len(s["lowercase_recordings"]) >= min_lower],
                  key=int)


# ================================================================== UNIPEN notes (ballpoint on paper, clean digitiser)
UNIPEN_SETUPS = ("hpp/hpb2",)       # selected by kinematics.unipen_survey (rule below), before any HW1 run on UNIPEN
UNIPEN_INDEX_JSON = CACHE_DIR / "unipen_index.json"
UNIPEN_RULE = ("recording setups (contributor + documentation file = one device, surface, rate and resolution) of UNIPEN "
               "category 8, measured on lines of lower-case words with the one kinematics function: <= 2.5 % of the "
               "pen-down velocity energy at 8-12 Hz and <= 3 % above 12 Hz (a clean digitiser; LIT CON-25: 1.3-1.7 %), "
               "mean pen-down speed 15-60 mm/s (LIT CON-20), 100-250 samples/s, >= 15 points/mm, >= 10 writers, writing "
               "on paper.  Only 'hpp/hpb2' passes: HP Labs Palo Alto staff, 1992, Wacom 420-510C, untethered inking pen "
               "with a ballpoint refill on preprinted paper forms, 100 samples/s, 500 points/inch (0.05 mm), 14 writers")
UNIPEN_FILE_SPLIT_NOTE = ("one file = one writer = one session (hpb2 documentation).  Writers are split before any note "
                          "is made (rank of a hash: 40 %, i.e. 5 of 14, tuning).  The prompts come from one stack of "
                          "forms, so every text line was written by 2-12 writers: the distinct line TEXTS are split too "
                          "(hash, 40 % tuning), and a note uses only lines whose text is in its writer's split "
                          "(writer-disjoint and text-disjoint)")


def rank_split(keys: Sequence[str], salt: str, share: float = SPLIT_TUNING_SHARE) -> Dict[str, str]:
    """Exactly floor(share x n) keys to 'tuning' (lowest sha1 of salt:key), the rest to 'test'."""
    ks = sorted(keys, key=lambda k: hashlib.sha1(f"{salt}:{k}".encode()).hexdigest())
    n_t = int(share * len(ks))
    return {k: ("tuning" if i < n_t else "test") for i, k in enumerate(ks)}


def unipen_index(setups: Sequence[str] = UNIPEN_SETUPS, log=print) -> Dict:
    """writer (file) -> lower-case word segments (index in the file, label, words), cached."""
    if UNIPEN_INDEX_JSON.exists():
        d = json.loads(UNIPEN_INDEX_JSON.read_text())
        if d.get("setups") == list(setups):
            return d
    import glob as _glob
    out = {}
    for setup in setups:
        c, doc = setup.split("/")
        for path in sorted(_glob.glob(str(L.UNIPEN_ROOT / "data" / "8" / c / "**" / "*.dat"), recursive=True)):
            f = L.unipen_file(path)
            if f is None or f["doc"] != doc:
                continue
            segs = []
            for si, sg_ in enumerate(f["segments"]):
                lab = sg_["label"].strip()
                if sg_["level"] == "TEXT" and _is_words(lab) and (sg_.get("quality") or "OK") != "BAD":
                    segs.append({"i": si, "label": lab, "n_words": len(lab.split())})
            w = os.path.relpath(path, L.UNIPEN_ROOT / "data" / "8")
            out[w] = {"path": path, "segments": segs, "pps": f["pps"], "res_x_per_mm": f["res_x_per_mm"],
                      "device": f["device"], "pen": f["pen"], "surface": f["surface"], "setup": setup}
    wsplit = rank_split(list(out), "unipen-writer")
    texts = sorted({sg_["label"] for v in out.values() for sg_ in v["segments"]})
    tsplit = {t_: split_of("unipen-text", t_) for t_ in texts}
    for w, v in out.items():
        v["split"] = wsplit[w]
        for sg_ in v["segments"]:
            sg_["text_split"] = tsplit[sg_["label"]]
    d = {"setups": list(setups), "writers": out, "rule": UNIPEN_RULE, "split_note": UNIPEN_FILE_SPLIT_NOTE,
         "n_texts": {"tuning": sum(1 for v in tsplit.values() if v == "tuning"),
                     "test": sum(1 for v in tsplit.values() if v == "test")}}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    UNIPEN_INDEX_JSON.write_text(json.dumps(d))
    return d


def _unipen_pool(v: Dict) -> List[Dict]:
    """The lines a note may use: those whose text belongs to the writer's split (writer- and text-disjoint)."""
    return [sg_ for sg_ in v["segments"] if sg_.get("text_split") == v["split"]]


def unipen_writers(split: str, index: Optional[Dict] = None, min_segments: int = 6) -> List[str]:
    index = index or unipen_index()
    return sorted(w for w, v in index["writers"].items() if v["split"] == split and len(_unipen_pool(v)) >= min_segments)


@lru_cache(maxsize=4)
def _unipen_parsed(path: str) -> Dict:
    return L.unipen_file(path)


def unipen_note(w: str, seed: int = 0, n_words: int = 10, dt: float = SIM_DT, index: Optional[Dict] = None,
                max_lines: int = 6) -> Optional[RealWritten]:
    """A note of about n_words real words by UNIPEN writer w: lines of lower-case words (seeded choice), one per ruled
    line, each with its recorded pen-down strokes and, where the digitiser tracked the hovering pen, its recorded
    in-air path and timing between strokes (documented physical units).  Line changes are added moves (ASSUMPTION)."""
    index = index or unipen_index()
    v = index["writers"].get(w)
    if not v:
        return None
    pool = _unipen_pool(v)
    if len(pool) < 2:
        return None
    f = _unipen_parsed(v["path"])
    comps = f["components"]
    rng = np.random.default_rng(int(hashlib.sha1(f"unipen-note:{w}:{seed}".encode()).hexdigest()[:8], 16))
    order = rng.permutation(len(pool))
    chosen, words = [], 0
    for k in order:
        sg_ = pool[int(k)]
        if words + sg_["n_words"] > n_words + 1 and chosen:
            continue
        chosen.append(sg_)
        words += sg_["n_words"]
        if words >= n_words or len(chosen) >= max_lines:
            break
    res = np.array([f["res_x_per_mm"], f["res_y_per_mm"]]) * 1e3        # points per metre
    lines = []
    for sg_ in chosen:
        seg = f["segments"][sg_["i"]]
        ids = [i for i in L._range_ids(seg["range"]) if i < len(comps)]
        ss, air = [], None
        for i in ids:
            down, P = comps[i]
            if not down:
                air = P / res if len(P) else None
                continue
            if len(P) >= 3:
                ss.append((P / res, air))
            air = None
        if ss:
            lines.append((sg_["label"], ss))
    if not lines:
        return None
    # physical size is as recorded.  Letter height (metadata only; the project's 'T, p, a' height): x-height = 2 x the
    # median over the lines of the inter-quartile range of the pen-down points' height (ASSUMPTION: most ink lies in
    # the x-height band, so its IQR is about half the x-height); T, p, a average 1.367 x-heights
    iqr_y = [float(np.subtract(*np.percentile(np.vstack([s_ for s_, _a in ss])[:, 1], [75, 25]))) for _, ss in lines]
    h_line = [float(np.ptp(np.vstack([s_ for s_, _a in ss])[:, 1])) for _, ss in lines]
    height_tpa = 2.0 * TPA_PER_XHEIGHT * float(np.median(iqr_y)) if iqr_y else 5e-3
    pitch = max(8e-3, 1.25 * float(np.percentile(h_line, 90)))
    strokes_out: List[Stroke] = []
    off = 0
    text = " ".join(lab for lab, _ in lines)
    for li, (lab, ss) in enumerate(lines):
        P = np.vstack([s_ for s_, _a in ss])
        # the hpb2 tablet's y grows upwards (checked on descenders: see tests); each line is shifted so that its top
        # sits on its ruled line position and its left end at x = 0
        shift = np.array([-P[:, 0].min(), -li * pitch - P[:, 1].max()])
        for j, (s_, a_) in enumerate(ss):
            n = len(s_)
            strokes_out.append(Stroke(t=np.arange(n) / f["pps"], xy=s_ + shift, char=np.full(n, off),
                                      air=(a_ + shift) if (a_ is not None and j > 0) else None, air_fs=f["pps"]))
        off += len(lab) + 1
    meta = {"recordings": [f"unipen/{w}#{sg_['i']}" for sg_ in chosen], "lines": [lab for lab, _ in lines],
            "split": v["split"], "units": "documented (UNIPEN header: 500 points/inch, 100 samples/s)",
            "device": v["device"], "pen": v["pen"], "surface": v.get("surface", ""), "setup": v.get("setup", ""),
            "licence": "UNIPEN: research use only (iUF notice)", "letters": "not labelled (one pseudo-letter per stroke)"}
    meta["letter_height_rule"] = ("1.367 x (2 x the median line IQR of the pen-down points' height) (ASSUMPTION; "
                                  "metadata only: the note keeps its recorded size)")
    return assemble(strokes_out, text, dt=dt, height_m=height_tpa, writer=f"unipen/{w}", source="unipen",
                    meta=meta, per_stroke_letters=True)


# ================================================================== Character Trajectories: composed sentences
CT_LETTERS = "abcdeghlmnopqrsuvwyz"
CT_SENTENCE = "please hold your pen as normal and draw some round loops"      # only the 20 recorded letters
CT_ASC = set("bdhl")
CT_DESC = set("gpqy")


@lru_cache(maxsize=1)
def _ct_by_letter() -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {}
    for c in L.chartraj():
        out.setdefault(c["char"], []).append(c)
    return out


def ct_split_of(instance_index: int) -> str:
    return split_of("chartraj", str(instance_index))


def ct_note(text: str = CT_SENTENCE, seed: int = 0, split: str = "test", dt: float = SIM_DT,
            height_mm: float = PDT06_MEDIAN_MM, gap_letter: float = 0.30, gap_word: float = 1.0,
            max_line_mm: float = 110.0) -> RealWritten:
    """A sentence composed from the one writer's recorded letters (instances of the requested split, seeded choice),
    resized so that the mean height of the writer's 'p' and 'a' (and 1.5 x-heights for 'T', which is not recorded)
    equals height_mm; letter gap 0.30 and word gap 1.0 x-height (ASSUMPTION, inside the aiguide writers' ranges).
    Reader templates: other instances of the same letters from the TUNING split (never the letters written)."""
    by = _ct_by_letter()
    rng = np.random.default_rng(int(hashlib.sha1(f"ct:{text}:{seed}:{split}".encode()).hexdigest()[:8], 16))
    # the writer's size: median heights of 'a' and 'p' in file units -> x-height
    h_a = np.median([np.ptp(c["xy"][:, 1]) for c in by["a"]])
    h_p = np.median([np.ptp(c["xy"][:, 1]) for c in by["p"]])
    tpa_native = (h_a + h_p + 1.5 * h_a) / 3.0
    k = height_mm * 1e-3 / tpa_native
    xh = h_a * k
    strokes: List[Stroke] = []
    x = 0.0
    y = 0.0
    used = []
    ci = 0
    lines = [[]]
    words = text.split(" ")
    wstart = np.cumsum([0] + [len(w) + 1 for w in words[:-1]])
    line_pitch = LINE_GAP_HEIGHTS * height_mm * 1e-3
    for ti, ch in enumerate(text):
        if ch == " ":
            x += (gap_word - gap_letter) * xh
            continue
        if ti in set(wstart.tolist()):
            wi_ = int(np.searchsorted(wstart, ti))
            est = sum(0.75 * xh + gap_letter * xh for _ in words[wi_])      # rough word width
            if x > 0 and x + est > max_line_mm * 1e-3:
                x, y = 0.0, y - line_pitch
                lines.append([])
            lines[-1].append(words[wi_])
        if ch not in by:
            raise ValueError(f"'{ch}' is not one of the recorded letters {CT_LETTERS}")
        pool = [c for c in by[ch] if ct_split_of(c["i"]) == split] or by[ch]
        c = pool[int(rng.integers(len(pool)))]
        used.append(int(c["i"]))
        P = c["xy"] * k
        top, bot = P[:, 1].max(), P[:, 1].min()
        if ch in CT_DESC:
            dy = xh - top                    # the top of the bowl on the x-height line
        else:
            dy = -bot                        # sits on the baseline
        P = P + np.array([x - P[:, 0].min(), dy + y])
        strokes.append(Stroke(t=c["t"], xy=P, char=np.full(len(P), ti)))
        x += np.ptp(P[:, 0]) + gap_letter * xh
        ci += 1
    # reader: other instances (tuning split) of every letter used
    inst = {ch: [[c["xy"] * k] for c in by[ch] if ct_split_of(c["i"]) == "tuning" and int(c["i"]) not in used][:8]
            for ch in set(text) - {" "}}
    reader = WriterReader(inst)
    meta = {"instances": used, "lines": [" ".join(l) for l in lines if l], "scale_label": CB.LABELS["chartraj"],
            "licence": "CC BY 4.0 (UCI Character Trajectories)",
            "split": split, "composition": "letters recorded one at a time, placed on a line here (ASSUMPTION gaps)"}
    return assemble(strokes, text, dt=dt, height_m=height_mm * 1e-3, writer="chartraj/1", source="chartraj", meta=meta,
                    reader=reader)
