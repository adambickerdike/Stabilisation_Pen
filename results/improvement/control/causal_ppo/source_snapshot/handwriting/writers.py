"""Synthetic writers for the three studies.  NOTHING HERE IS HUMAN DATA.

* ET study: aiguide writers (``aiguide.writer.sample_style`` seeded by the writer index) writing
  ``aiguide.sentences.GUIDE_SENTENCE``; tremor from ``stabpen.signals.tremor`` (the project's tremor model).
* PD study: the same writers, larger and slower (ASSUMPTION), with a per-letter size schedule for progressive
  micrographia and the writer's response to cues or lines (ASSUMPTION ranges from PDT-05/06/18/19, section 7 of
  docs/handwriting_outcomes.md).
* Practice study: the same writers with a writer-error model (ASSUMPTION): malformed letters (extra smooth
  deformation), size and baseline irregularity, letter reversals (b/d, p/q) and wrong letters.

``ScheduledWriter.write`` reproduces ``aiguide.writer.SyntheticWriter.write`` exactly when no schedule is given
(tested), so the ET writing is aiguide's writing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths

ensure_paths()
from aiguide.glyphs import GLYPH_SET, arclength, width as glyph_width  # noqa: E402
from aiguide.sentences import GUIDE_SENTENCE  # noqa: E402
from aiguide.writer import (Letter, Path, SyntheticWriter, Written, apply_warp, sample_style,  # noqa: E402
                            warp_params)
from penapp.synth import _split_at_corners  # noqa: E402
from stabpen import signals as sg  # noqa: E402

ET_SENTENCE = GUIDE_SENTENCE                              # "return library books by friday" (aiguide, fusion, opt studies)
PD_SENTENCE = "the quick brown fox jumps over the lazy dog"     # pangram: every letter once, 35 letters
PRACTICE_SENTENCE = "a big dog dug a deep pit by the pond"      # b, d, p, g: reversal-prone letters (27 letters)
SIM_DT = 25e-6
MIRROR = {"b": "d", "d": "b", "p": "q", "q": "p"}


class ScheduledWriter(SyntheticWriter):
    """aiguide's synthetic writer with optional per-glyph schedules (identical output when none is given)."""

    def write(self, text: str, *, dt: float = 1e-3, seed: int = 0, start=(0.0, 0.0), size_scale: float = 1.0,
              size_factors: Optional[Sequence[float]] = None, tempo_factors: Optional[Sequence[float]] = None,
              glyph_override: Optional[Dict[int, str]] = None, extra_warp: Optional[Sequence[float]] = None,
              baseline_offsets: Optional[Sequence[float]] = None, err_seed: int = 0) -> Written:
        st = self.style
        rng = np.random.default_rng(seed)
        rng_err = np.random.default_rng(err_seed)
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
            sf = 1.0 if size_factors is None else float(size_factors[min(gi, len(size_factors) - 1)])
            if ch == " ":
                size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1)) * sf
                x += (st.word_gap - st.letter_gap) * size
                wi += 1
                continue
            wch = ch if glyph_override is None else glyph_override.get(gi, ch)
            if wch not in GLYPH_SET:
                raise ValueError(f"no glyph for {wch!r}")
            size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1)) * (1.0 + rng.normal(0.0, st.scale_jitter)) * sf
            y_base = start[1] + slope * (x - start[0]) + st.baseline_wander * h0 * math.sin(
                2 * np.pi * (x - start[0]) / (st.wander_period * h0) + wph)
            if baseline_offsets is not None:
                y_base += float(baseline_offsets[gi]) * h0
            shape = self.glyph_shape(wch, rng)
            if extra_warp is not None and extra_warp[gi] > 0:
                w_extra = warp_params(rng_err, float(extra_warp[gi]))
                shape = [apply_warp(s, w_extra) for s in shape]
            tf = 1.0 if tempo_factors is None else float(tempo_factors[gi])
            polys, strokes = [], []
            a_letter = None
            for s in shape:
                P = np.column_stack([x + size * (st.width * s[:, 0] + s[:, 1] * shear), y_base + size * s[:, 1]])
                travel = float(np.hypot(*(P[0] - pb.pos)))
                pb.move(P[0], (0.06 + travel / (st.air_speed_mm_s * 1e-3)) * tf)
                a = pb.n
                if a_letter is None:
                    a_letter = a
                pb.pen(True, 0.04)
                pb.dwell(0.015)
                for piece in _split_at_corners(P, st.corner_deg):
                    length = float(arclength(piece)[-1])
                    T = max(0.05, length / (st.speed_mm_s * 1e-3)) * max(0.5, 1.0 + rng.normal(0.0, st.tempo_jitter)) * tf
                    pb.polyline(piece, T)
                pb.dwell(0.01)
                pb.pen(False, 0.04)
                strokes.append((a, pb.n))
                polys.append(P)
            letters.append(Letter(wch, ti, gi, wi, (a_letter, pb.n), strokes, polys, size, x, y_base))
            x += (glyph_width(wch) * st.width + st.letter_gap) * size
            gi += 1
        pb.dwell(0.3)
        it = pb.build()
        for L in letters:
            L.t0 = float(it.t[L.span[0]])
            L.t1 = float(it.t[min(L.span[1], len(it.t) - 1)])
            it.features.append(("letter", L.t0, L.t1, {"char": L.char, "glyph_index": L.glyph_index}))
        return Written(text, st, it, letters, dt, meta={"writer_seed": self.seed, "instance_seed": seed,
                                                         "style": dict(vars(st)), "synthetic": True})


def writer(w: int, **style_over) -> ScheduledWriter:
    st = sample_style(np.random.default_rng(w))
    for k, v in style_over.items():
        setattr(st, k, v)
    return ScheduledWriter(st, seed=w)


def tremor_path(t: np.ndarray, f0: float, amp: float, seed: int, w: int, **kw) -> np.ndarray:
    """Hand tremor (the project's model, stabpen.signals.tremor), seeded by (seed, writer, f0, amplitude)."""
    spec = sg.TremorSpec(f0=f0, amp_pk=amp, **kw)
    rs = 1_000_000 * seed + 1000 * w + 10 * int(round(f0)) + int(round(amp * 1e4))
    return sg.tremor(t, spec, np.random.default_rng(rs))


# ------------------------------------------------------------------ PD micrographia schedules (ASSUMPTION ranges)
@dataclass
class PDProfile:
    """Progressive micrographia and the writer's response to cues / lines.  Every range is an ASSUMPTION within the
    magnitudes of the cited literature (docs/handwriting_outcomes.md section 7)."""
    h0_mm: float = 5.0               # start x-height: PDT-06 letter height 5.0 mm (controls, ET)
    decrement: float = 0.25          # fractional size loss from the first to the last letter (PDT-05: stroke length -23 %)
    speed_factor: float = 0.6        # PD writes slower (PDT-10, PDT-38); ASSUMPTION
    cue_threshold: float = 0.10      # cue when the measured size is > 10 % below the start (task definition)
    cue_latency_letters: int = 1     # the writer responds from the next letter (ASSUMPTION)
    cue_recovery: float = 0.8        # fraction of the deficit recovered after a cue (PDT-19: 'more normal'; ASSUMPTION 0.5-1.0)
    cue_tempo: float = 1.15          # movement time x 1.15 for 3 letters after a cue (PDT-19: size up via longer time)
    cue_refractory_letters: int = 3
    size_meas_noise: float = 0.03    # relative error of the pen's letter-size measurement (ASSUMPTION)
    lines_keep: float = 0.5          # with >= 1 cm lines the decrement is kept at this fraction (PDT-18/33; ASSUMPTION 0.3-0.7)
    lines_jitter: float = 0.7        # and the size jitter at this fraction (PDT-18 'size variability improved')
    tremor_hz: float = 5.0           # PD tremor during writing (small; PDT-07: rest tremor diminishes in movement)
    tremor_amp: float = 0.15e-3      # m at the hand (ASSUMPTION)


def pd_profile(seed: int) -> PDProfile:
    """Per (writer, seed) draw of the ASSUMPTION ranges."""
    rng = np.random.default_rng(900_000 + seed)
    return PDProfile(decrement=float(rng.uniform(0.2, 0.3)), cue_recovery=float(rng.uniform(0.5, 1.0)),
                     cue_tempo=float(rng.uniform(1.10, 1.20)), lines_keep=float(rng.uniform(0.3, 0.7)),
                     speed_factor=float(rng.uniform(0.5, 0.7)), tremor_hz=float(rng.uniform(4.0, 6.0)),
                     tremor_amp=float(rng.uniform(0.05e-3, 0.25e-3)))


def pd_schedule(n: int, prof: PDProfile, mode: str, rng: np.random.Generator):
    """Per-glyph size and tempo factors (relative to the start size) and the cue events.

    mode: "none" | "cue" | "lines" (| "size_assist": as none; the pen enlarges the ink)."""
    dec = prof.decrement / max(n - 1, 1)
    if mode == "lines":
        dec *= prof.lines_keep
    s = np.ones(n)
    tempo = np.ones(n)
    cues: List[int] = []
    last_cue = -10 ** 6
    cur = 1.0
    pending = {}
    for i in range(n):
        if i in pending:
            cur = cur + pending.pop(i) * (1.0 - cur)
            for j in range(i, min(n, i + 3)):
                tempo[j] = prof.cue_tempo
        s[i] = cur
        if mode == "cue":
            meas = cur * (1.0 + rng.normal(0.0, prof.size_meas_noise))
            if meas < 1.0 - prof.cue_threshold and i - last_cue >= prof.cue_refractory_letters:
                cues.append(i)
                last_cue = i
                pending[i + prof.cue_latency_letters] = prof.cue_recovery
        cur = cur - dec
    return s, tempo, cues


# ------------------------------------------------------------------ practice: writer-error model (ASSUMPTION)
@dataclass
class ErrorProfile:
    name: str
    extra_warp: float = 0.0          # x-height units of extra smooth deformation per letter (malformation)
    malformed_frac: float = 0.0      # fraction of letters malformed
    size_jitter: float = 0.0         # extra relative size SD
    baseline_sd: float = 0.0         # x-height units, per-letter baseline offset SD
    p_reversal: float = 0.0          # probability that b/d/p/q is written mirrored
    wrong_letters: Dict[int, str] = field(default_factory=dict)   # glyph index -> letter written instead


def dysgraphia_profile() -> ErrorProfile:
    """Poor letter formation and irregular size/baseline (motor handwriting difficulty); ASSUMPTION magnitudes."""
    return ErrorProfile("dysgraphia", extra_warp=0.14, malformed_frac=0.6, size_jitter=0.15, baseline_sd=0.12)


def dyslexia_profile() -> ErrorProfile:
    """Normal letter formation; letter reversals and a wrong letter (spelling); ASSUMPTION magnitudes."""
    return ErrorProfile("dyslexia", extra_warp=0.0, malformed_frac=0.0, size_jitter=0.0, baseline_sd=0.0,
                        p_reversal=0.35, wrong_letters={})


def error_plan(text: str, prof: ErrorProfile, seed: int):
    """Per-glyph overrides for one (writer, seed): glyph written, extra warp, size factor, baseline offset."""
    rng = np.random.default_rng(700_000 + seed)
    glyphs = [c for c in text if c != " "]
    n = len(glyphs)
    over: Dict[int, str] = {}
    kind: List[str] = ["ok"] * n
    for i, c in enumerate(glyphs):
        if c in MIRROR and rng.uniform() < prof.p_reversal:
            over[i] = MIRROR[c]
            kind[i] = "reversal"
    for i, c in prof.wrong_letters.items():
        if i < n:
            over[i] = c
            kind[i] = "wrong_letter"
    warp = np.where(rng.uniform(size=n) < prof.malformed_frac, prof.extra_warp * rng.uniform(0.6, 1.4, n), 0.0)
    for i in range(n):
        if warp[i] > 0 and kind[i] == "ok":
            kind[i] = "malformed"
    size = 1.0 + prof.size_jitter * rng.standard_normal(n)
    size = np.clip(size, 0.6, 1.5)
    base = prof.baseline_sd * rng.standard_normal(n)
    return {"override": over, "warp": warp, "size": size, "baseline": base, "kind": kind}


def spelling_error_word(text: str) -> Dict[int, str]:
    """A same-length spelling error for the practice sentence (letter-order swap in 'deep' -> 'depe' is not
    phonological; use the classic confusion 'pond' -> 'bond' (p/b) and 'dug' -> 'dig' is a real word).  Here: the
    vowel substitution 'deep' -> 'daep' (a plausible phonics-based misspelling; ASSUMPTION)."""
    glyphs = [c for c in text if c != " "]
    idx = {}
    # locate "deep"
    s = text.replace(" ", "")
    k = s.find("deep")
    if k >= 0:
        idx[k + 1] = "a"          # d[e->a]ep
    return idx
