"""Synthetic writers.  NOTHING HERE IS HUMAN DATA.

A writer writes text with the single-line glyph font of app/penapp/synth.py,
deformed and placed in a personal style:

* global style: x-height, slant, width, letter and word spacing, baseline
  slope and slow wander, writing and air speed;
* writer-specific allographs: a smooth random deformation of every glyph,
  fixed for the writer (what a font-based template cannot know);
* per-instance variability: smooth deformation, size and offset jitter, tempo
  jitter of each minimum-jerk piece (every letter instance differs);
* optional micrographia: progressive size decrement along the line.

Timing follows app/penapp/synth.py: pen lifts between strokes, minimum-jerk
pieces split at sharp corners (``stabpen.signals.PathBuilder`` semantics, with
a vectorised polyline segment).  The parameter ranges are illustrative
settings of the generator, not claims about people.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ensure_paths
from .glyphs import GLYPH_SET, arclength, width as glyph_width

ensure_paths()
from penapp.synth import _split_at_corners  # noqa: E402
from stabpen import signals as sg  # noqa: E402


@dataclass
class WriterStyle:
    x_height_mm: float = 2.6
    slant_deg: float = 12.0
    width: float = 1.0
    letter_gap: float = 0.32          # x-height units
    word_gap: float = 1.3             # x-height units
    baseline_slope_deg: float = 0.0
    baseline_wander: float = 0.04     # x-height units (amplitude of a slow wander)
    wander_period: float = 6.0        # x-height units
    speed_mm_s: float = 28.0
    air_speed_mm_s: float = 60.0
    allograph_amp: float = 0.07       # x-height units, writer-specific glyph deformation
    instance_amp: float = 0.025       # x-height units, per-instance deformation
    scale_jitter: float = 0.04        # relative SD of per-instance size
    offset_jitter: float = 0.03       # x-height units, per-instance offset SD
    tempo_jitter: float = 0.10        # relative SD of each piece's duration
    corner_deg: float = 60.0
    micrographia: float = 0.0         # fractional size decrement from the first to the last letter


def sample_style(rng: np.random.Generator, **over) -> WriterStyle:
    st = WriterStyle(
        x_height_mm=float(rng.uniform(2.0, 3.2)), slant_deg=float(rng.uniform(0.0, 22.0)),
        width=float(rng.uniform(0.85, 1.2)), letter_gap=float(rng.uniform(0.22, 0.45)),
        word_gap=float(rng.uniform(1.0, 1.6)), baseline_slope_deg=float(rng.normal(0.0, 1.5)),
        baseline_wander=float(rng.uniform(0.02, 0.07)), wander_period=float(rng.uniform(4.0, 9.0)),
        speed_mm_s=float(rng.uniform(20.0, 34.0)), air_speed_mm_s=float(rng.uniform(45.0, 75.0)),
        allograph_amp=float(rng.uniform(0.04, 0.10)), instance_amp=float(rng.uniform(0.015, 0.035)),
        scale_jitter=float(rng.uniform(0.03, 0.06)), offset_jitter=float(rng.uniform(0.02, 0.05)),
        tempo_jitter=float(rng.uniform(0.05, 0.15)))
    for k, v in over.items():
        setattr(st, k, v)
    return st


# ------------------------------------------------------------------ warps
def warp_params(rng: np.random.Generator, amp: float) -> Tuple[np.ndarray, ...]:
    """Smooth random 2-D deformation: small affine part + two low-frequency sine fields."""
    A = rng.normal(0.0, 0.6 * amp, (2, 2))
    b = rng.normal(0.0, 0.3 * amp, 2)
    F = rng.normal(0.0, 1.0, (2, 2)) * 1.2          # cycles per x-height
    ph = rng.uniform(0.0, 2 * np.pi, 2)
    C = rng.normal(0.0, amp, (2, 2))
    return A, b, F, ph, C


def apply_warp(P: np.ndarray, w) -> np.ndarray:
    A, b, F, ph, C = w
    d = P @ A.T + b
    for m in range(2):
        d = d + np.sin(2 * np.pi * (P @ F[m]) + ph[m])[:, None] * C[m][None, :]
    return P + d


# --------------------------------------------------------------- path builder
class Path(sg.PathBuilder):
    """``stabpen.signals.PathBuilder`` with a sample counter and a vectorised polyline segment."""

    def __init__(self, dt, start=(0.0, 0.0), lift_height=1.5e-3):
        super().__init__(dt, start, lift_height)
        self.n = 1

    def _append(self, xy, down, lift):
        super()._append(xy, down, lift)
        self.n += len(xy)

    def polyline(self, P: np.ndarray, T: float):
        """Follow polyline P with minimum-jerk timing along its arclength (as ``curve``)."""
        n = max(int(round(T / self.dt)), 2)
        u = sg.min_jerk_profile(np.linspace(0.0, 1.0, n))
        s = arclength(P)
        su = u * s[-1]
        xy = np.column_stack([np.interp(su, s, P[:, 0]), np.interp(su, s, P[:, 1])])
        d = self.is_down
        self._append(xy, np.full(n, d), np.full(n, 0.0 if d else self.lift_height))
        return self


# ------------------------------------------------------------------ records
@dataclass
class Letter:
    char: str
    text_index: int                   # position in the text string
    glyph_index: int                  # position among written glyphs
    word_index: int
    span: Tuple[int, int]             # samples [first pen-down transition, last pen-up transition end)
    strokes: List[Tuple[int, int]]    # sample ranges of each stroke (pen-down transition to pen-up end)
    polylines: List[np.ndarray]       # intended stroke polylines, page frame (m)
    size: float                       # x-height of this instance (m)
    x0: float                         # letter origin (m)
    y0: float                         # baseline at the origin (m)
    t0: float = 0.0
    t1: float = 0.0


@dataclass
class Written:
    text: str
    style: WriterStyle
    intended: sg.Intended
    letters: List[Letter]
    dt: float
    meta: Dict = field(default_factory=dict)

    def letter_xy(self, L: Letter, pen_down_only: bool = True) -> np.ndarray:
        a, b = L.span
        xy = self.intended.xy[a:b]
        if pen_down_only:
            xy = xy[self.intended.pen_down[a:b]]
        return xy


class SyntheticWriter:
    """One synthetic writer: a style plus fixed allograph deformations."""

    def __init__(self, style: WriterStyle, seed: int = 0):
        self.style = style
        self.seed = seed
        rng = np.random.default_rng(10_000 + seed)
        self.allographs = {c: warp_params(rng, style.allograph_amp) for c in sorted(GLYPH_SET)}

    def glyph_shape(self, ch: str, rng: Optional[np.random.Generator] = None) -> List[np.ndarray]:
        """The writer's version of a glyph in x-height units (allograph, plus instance noise if rng)."""
        out = []
        inst = warp_params(rng, self.style.instance_amp) if rng is not None else None
        off = rng.normal(0.0, self.style.offset_jitter, 2) if rng is not None else np.zeros(2)
        for s in GLYPH_SET[ch]:
            p = apply_warp(s, self.allographs[ch])
            if inst is not None:
                p = apply_warp(p, inst)
            out.append(p + off)
        return out

    def write(self, text: str, *, dt: float = 1e-3, seed: int = 0, start=(0.0, 0.0),
              size_scale: float = 1.0) -> Written:
        st = self.style
        rng = np.random.default_rng(seed)
        h0 = st.x_height_mm * 1e-3 * size_scale
        shear = math.tan(math.radians(st.slant_deg))
        slope = math.tan(math.radians(st.baseline_slope_deg))
        wph = rng.uniform(0, 2 * np.pi)
        pb = Path(dt, start=(start[0] - 1.0e-3, start[1] + 1.0e-3), lift_height=1.5e-3)
        pb.dwell(0.2)
        n_glyphs = sum(1 for c in text if c != " ")
        letters: List[Letter] = []
        x = start[0]
        gi = 0
        wi = 0
        for ti, ch in enumerate(text):
            if ch == " ":
                size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1))
                x += (st.word_gap - st.letter_gap) * size
                wi += 1
                continue
            if ch not in GLYPH_SET:
                raise ValueError(f"no glyph for {ch!r}")
            size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1)) * (1.0 + rng.normal(0.0, st.scale_jitter))
            y_base = start[1] + slope * (x - start[0]) + st.baseline_wander * h0 * math.sin(
                2 * np.pi * (x - start[0]) / (st.wander_period * h0) + wph)
            shape = self.glyph_shape(ch, rng)
            polys, strokes = [], []
            a_letter = None
            for s in shape:
                P = np.column_stack([x + size * (st.width * s[:, 0] + s[:, 1] * shear), y_base + size * s[:, 1]])
                travel = float(np.hypot(*(P[0] - pb.pos)))
                pb.move(P[0], 0.06 + travel / (st.air_speed_mm_s * 1e-3))
                a = pb.n
                if a_letter is None:
                    a_letter = a
                pb.pen(True, 0.04)
                pb.dwell(0.015)
                for piece in _split_at_corners(P, st.corner_deg):
                    length = float(arclength(piece)[-1])
                    T = max(0.05, length / (st.speed_mm_s * 1e-3)) * max(0.5, 1.0 + rng.normal(0.0, st.tempo_jitter))
                    pb.polyline(piece, T)
                pb.dwell(0.01)
                pb.pen(False, 0.04)
                strokes.append((a, pb.n))
                polys.append(P)
            letters.append(Letter(ch, ti, gi, wi, (a_letter, pb.n), strokes, polys, size, x, y_base))
            x += (glyph_width(ch) * st.width + st.letter_gap) * size
            gi += 1
        pb.dwell(0.3)
        it = pb.build()
        for L in letters:
            L.t0 = float(it.t[L.span[0]])
            L.t1 = float(it.t[min(L.span[1], len(it.t) - 1)])
            it.features.append(("letter", L.t0, L.t1, {"char": L.char, "glyph_index": L.glyph_index}))
        return Written(text, st, it, letters, dt, meta={"writer_seed": self.seed, "instance_seed": seed,
                                                         "style": asdict(st), "synthetic": True})


def contact_runs(pen_down: np.ndarray) -> List[Tuple[int, int]]:
    d = np.diff(np.r_[0, pen_down.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))
