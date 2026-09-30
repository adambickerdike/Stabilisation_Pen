"""Style-conditioned template synthesis.

Predicted characters become a pen trajectory in the user's style:

1. shape: the user's own exemplar of the character (mean of its recent
   instances, glyph units) or, if there is none yet, the font glyph;
2. style: the estimated size (or a frozen target size), width and slant;
3. placement, one of
   * ``app``    - the app places the letter after the previous letter with
                  the estimated letter/word gap and baseline;
   * ``anchor`` - the pen translates the letter so that its first point is
                  the nib position at the letter's first touchdown ("place it
                  after the current pen position"; the pen knows its own
                  position, the app only knows it ~100 ms late);
4. timing: minimum-jerk pieces at the estimated pen-down speed with pen
   lifts between strokes, sampled at the stage rate (the M1 guided core and
   the firmware index templates by progress at the stage rate).

A template never moves the ink by more than the stage travel: the guided
core clips the correction at q_lim and drops authority when the nib is more
than 2 q_lim from the template.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .glyphs import GLYPH_SET, arclength, resample, width as glyph_width
from .style import StyleEstimate, StyleEstimator
from .writer import Path

from penapp.synth import _split_at_corners  # noqa: E402  (aiguide puts app/ on sys.path)


@dataclass
class LetterTemplate:
    char: str
    strokes: List[np.ndarray]            # page frame, m
    conf: float = 1.0                    # predictor confidence c-hat (0..1)
    source: str = "font"                 # font | exemplar | oracle
    glyph_index: int = -1

    def translate(self, d) -> "LetterTemplate":
        d = np.asarray(d, float)
        return LetterTemplate(self.char, [s + d for s in self.strokes], self.conf, self.source, self.glyph_index)

    def points(self) -> np.ndarray:
        return np.vstack(self.strokes)


def shape_units(char: str, estimator: Optional[StyleEstimator], mode: str = "exemplar") -> Tuple[List[np.ndarray], str]:
    if mode == "exemplar" and estimator is not None:
        ex = estimator.exemplar(char)
        if ex is not None:
            return ex, "exemplar"
    return [np.asarray(s, float) for s in GLYPH_SET[char]], "font"


def letter_template(char: str, est: StyleEstimate, x0: float, y0: float, *, estimator: Optional[StyleEstimator] = None,
                    mode: str = "exemplar", conf: float = 1.0, glyph_index: int = -1) -> LetterTemplate:
    g, src = shape_units(char, estimator, mode)
    a, b, h = est.a, est.b, est.size
    strokes = [np.column_stack([x0 + a * s[:, 0] + b * s[:, 1], y0 + h * s[:, 1]]) for s in g]
    return LetterTemplate(char, strokes, conf, src, glyph_index)


def app_origin(prev_char: str, prev_x0: float, est: StyleEstimate, new_word: bool) -> Tuple[float, float]:
    """Origin of the next letter placed by the app after a letter at ``prev_x0``."""
    gap = est.word_gap if new_word else est.letter_gap
    x0 = prev_x0 + est.a * glyph_width(prev_char) + gap * est.size
    return x0, est.baseline(x0)


def anchor_to(t: LetterTemplate, touchdown_xy) -> LetterTemplate:
    """Translate a letter template so its first point is the touchdown point."""
    return t.translate(np.asarray(touchdown_xy, float) - t.strokes[0][0])


@dataclass
class TemplateTrack:
    """A template trajectory at the stage rate for a sequence of letters."""
    xy: np.ndarray                       # (m, 2) m, stage-rate samples
    pen_down: np.ndarray                 # (m,) bool
    letter_of: np.ndarray                # (m,) glyph index of the letter a sample belongs to (-1 = air)
    letters: List[LetterTemplate] = field(default_factory=list)
    dt: float = 5e-4


def build_track(letters: Sequence[LetterTemplate], *, speed: float, air_speed: float, dt: float = 5e-4,
                start=None, corner_deg: float = 60.0) -> TemplateTrack:
    """Timed trajectory through ``letters`` (minimum-jerk pieces, pen lifts between strokes)."""
    first = letters[0].strokes[0][0]
    start = first + np.array([-1.0e-3, 1.0e-3]) if start is None else np.asarray(start, float)
    pb = Path(dt, start=tuple(start), lift_height=1.5e-3)
    owner = [np.array([-1])]
    pb.dwell(0.1)
    owner.append(np.full(pb.n - 1, -1))
    for L in letters:
        for s in L.strokes:
            n0 = pb.n
            travel = float(np.hypot(*(s[0] - pb.pos)))
            pb.move(s[0], 0.06 + travel / max(air_speed, 1e-3))
            owner.append(np.full(pb.n - n0, -1))
            n0 = pb.n
            pb.pen(True, 0.04)
            pb.dwell(0.015)
            for piece in _split_at_corners(s, corner_deg):
                length = float(arclength(piece)[-1])
                pb.polyline(piece, max(0.05, length / max(speed, 1e-3)))
            pb.dwell(0.01)
            pb.pen(False, 0.04)
            owner.append(np.full(pb.n - n0, L.glyph_index))
    pb.dwell(0.3)
    owner.append(np.full(pb.n - sum(len(o) for o in owner), -1))
    it = pb.build()
    return TemplateTrack(it.xy, it.pen_down, np.concatenate(owner)[:len(it.xy)], list(letters), dt)


# ------------------------------------------------------------------ metrics
def dense(strokes: Sequence[np.ndarray], step: float = 5e-6) -> np.ndarray:
    out = []
    for s in strokes:
        L = arclength(s)[-1]
        out.append(resample(s, max(2, int(L / step) + 1)) if L > 0 else s[:1])
    return np.vstack(out)


def template_error(intended: Sequence[np.ndarray], templ: Sequence[np.ndarray]) -> Dict[str, np.ndarray]:
    """Distances (m) from every intended point to the template and the translation-free (shape) residual."""
    from scipy.spatial import cKDTree
    I = dense(intended)
    Tm = dense(templ)
    d, _ = cKDTree(Tm).query(I)
    # translation-free: remove the best translation (3 nearest-point iterations)
    off = np.zeros(2)
    tree = cKDTree(Tm)
    for _ in range(3):
        _, j = tree.query(I - off)
        off = np.mean(I - Tm[j], axis=0)
    ds, _ = tree.query(I - off)
    return {"d": d, "d_shape": ds, "offset": off}
