"""The public API of the real-data library, for the other studies.

    from realdata import library as RL
    cls = RL.classes()                                   # severity classes, mm at the pen tip (DATA uci_spiral)
    tr = RL.tremor("moderate", seed=3, kind="PD", split="test", duration=20.0)     # real tremor, scaled to the class
    wr = RL.writing("test", seed=3)                      # real words, real timing, ballpoint on paper (UNIPEN hpb2)
    scn = RL.hw1_scenario(wr, tr)                        # model HW1 scenario (handwriting.plant.Scenario)
    s2 = RL.sim2_scenario(wr, tr)                        # sim2 / H1 scenario (sim.pensim.scenarios.Scenario)
    rd = wr.reader                                       # the writer-adapted reader (handwriting.metrics compatible)

Tremor draws
  kind 'PD'  2-D pen-tip tremor recorded while PD patients drew spirals on a tablet (uci_spiral, CC BY 4.0)
  kind 'ET'  hand acceleration of ET patients holding the arms out (zenodo_et, CC BY 4.0), converted to displacement
             in the tremor band; one axis, so the page-plane ellipse is CONSTRUCTED: minor axis = ellipticity x the
             90-degree-shifted signal (Hilbert), ellipticity drawn from the inter-quartile range of the real 2-D PD tip
             tremor, major axis at 30 +- 15 degrees above the line (LIT PDT-36: ET spirals show a fixed axis, 8 to 2
             o'clock); ASSUMPTION
  The waveform keeps its real frequency, frequency wander, amplitude modulation, intermittency and harmonics; its
  amplitude is set to the class (power amplitude: sqrt(2) x RMS of the major axis at f0 +- 2 Hz, the basis of the
  class boundaries; = TremorSpec.amp_pk for a steady tremor), drawn log-uniformly inside the class range unless amp_mm
  is given.  A 0.3 s onset ramp is applied
  (as stabpen TremorSpec.onset).  A waveform shorter than the request is continued by repeating it with a 0.5 s
  raised-cosine cross-fade (flagged in the draw's meta).  Extraction is zero-phase: inputs only.
Splits: recordings and writers are split into 'tuning' and 'test' before any evaluation (tremorlib, writinglib).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import hilbert

from . import ensure_paths
from . import dsp as D
from . import tremorlib as TL
from . import writinglib as WL

ensure_paths()

ET_AXIS_DEG = (30.0, 15.0)          # mean, half-range (ASSUMPTION from LIT PDT-36)
ONSET_S = 0.3
XFADE_S = 0.5


@dataclass
class TremorDraw:
    t: np.ndarray
    d: np.ndarray                    # (n, 2) m, page frame
    meta: Dict = field(default_factory=dict)


def _rng(*key) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha1(":".join(map(str, key)).encode()).hexdigest()[:12], 16))


def classes(quick: bool = False) -> Dict:
    """Severity classes (mm at the pen tip, peak = major semi-axis) with their definitions and sources."""
    return TL.load(quick)["classes"]


def candidates(kind: str, split: str, quick: bool = False) -> List[Dict]:
    lib = TL.load(quick)
    src = {"PD": "uci_spiral", "ET": "zenodo_et"}
    kinds = ("PD", "ET") if kind == "any" else (kind,)
    return [x for x in lib["rows"] if x.get("generator") and x["split"] == split and x["group"] in kinds
            and x["source"] == src[x["group"]]]


def _loop(w: np.ndarray, n: int, fs: float, start: int) -> (np.ndarray, bool):
    """n samples of w from `start`, continued by repetition with raised-cosine cross-fades if needed."""
    if len(w) - start >= n:
        return w[start:start + n], False
    out = w[start:].copy()
    nx = int(XFADE_S * fs)
    while len(out) < n:
        nxt = w[:min(len(w), n - len(out) + nx)]
        k = min(nx, len(out), len(nxt))
        r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))[:, None]
        out[-k:] = out[-k:] * (1 - r) + nxt[:k] * r
        out = np.vstack([out, nxt[k:]])
    return out[:n], True


def tremor(cls: str = "moderate", seed: int = 0, kind: str = "PD", split: str = "test", duration: Optional[float] = None,
           dt: float = WL.SIM_DT, t: Optional[np.ndarray] = None, amp_mm: Optional[float] = None, quick: bool = False,
           rid: Optional[str] = None) -> TremorDraw:
    """A real tremor waveform of `kind` from `split`, scaled to severity class `cls` (or to amp_mm)."""
    if t is None:
        t = np.arange(0.0, float(duration or 20.0), dt)
    t = np.asarray(t, float)
    rng = _rng("tremor", cls, seed, kind, split)
    cands = candidates(kind, split, quick)
    if rid is not None:
        cands = [x for x in TL.load(quick)["rows"] if x["rid"] == rid]
    if not cands:
        raise ValueError(f"no {kind} tremor waveform in split {split!r}")
    row = cands[int(rng.integers(len(cands)))]
    w = np.asarray(TL.waveforms(quick)[row["rid"]], float)
    fs = TL.WAVE_FS
    lib = TL.load(quick)
    construct = {}
    if w.shape[1] == 1:
        e_lo, e_hi = lib["shape_2d"]["ellipticity_iqr"]
        e = float(rng.uniform(e_lo, e_hi))
        th = math.radians(ET_AXIS_DEG[0] + rng.uniform(-ET_AXIS_DEG[1], ET_AXIS_DEG[1]))
        z = hilbert(w[:, 0])
        maj, mnr = z.real, e * z.imag
        w = np.column_stack([math.cos(th) * maj - math.sin(th) * mnr, math.sin(th) * maj + math.cos(th) * mnr])
        construct = {"ellipticity": e, "axis_deg": math.degrees(th), "label": "ASSUMPTION: 1-axis recording made 2-D "
                     "(Hilbert quadrature minor axis, ellipticity from real PD tip tremor, axis from LIT PDT-36)"}
    n_need = int(math.ceil((t[-1] - t[0]) * fs)) + 4
    start = int(rng.integers(0, max(1, len(w) - n_need))) if len(w) > n_need else int(rng.integers(0, len(w) // 2))
    seg, looped = _loop(w, n_need, fs, start)
    tt = np.arange(len(seg)) / fs
    d = CubicSpline(tt, seg, axis=0)(np.clip(t - t[0], 0, tt[-1]))
    # amplitude: median major-axis envelope of the used segment -> target
    cl = lib["classes"]
    if amp_mm is None:
        lo, hi = cl[cls]["range_mm"] if cls != "none" else (0.5 * cl["none"]["representative_mm"], cl["none"]["range_mm"][1])
        lo = max(lo, 1e-3)
        amp_mm = float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
    fs_d = 1.0 / float(t[1] - t[0])
    dec = max(1, int(round(fs_d / 1000.0)))
    a_now = D.power_amplitude(d[::dec], fs_d / dec, float(row["f0"]))
    d = d * (amp_mm * 1e-3 / max(a_now, 1e-30))
    ramp = np.clip((t - t[0]) / ONSET_S, 0.0, 1.0)
    d = d * ramp[:, None]
    meta = {"kind": kind, "class": cls, "amp_mm": amp_mm, "rid": row["rid"], "source": row["source"],
            "subject": row["subject"], "split": split, "f0": row["f0"], "native_env_cv": row["env_cv"],
            "native_f_sd": row["f_sd"], "native_harmonic": row.get("harmonic_excess"), "looped": looped,
            "start_s": start / fs, "construction": construct, "seed": seed,
            "definition": "amp_mm = sqrt(2) x RMS of the major axis at f0 +- 2 Hz (power amplitude; = TremorSpec.amp_pk "
                          "for a steady tremor; the basis of the severity classes)",
            "evidence": "DATA (" + row["source"] + "), zero-phase extraction, scaled to the class (CALC)"}
    return TremorDraw(t=t, d=np.ascontiguousarray(d), meta=meta)


def synthetic_like(draw: TremorDraw, seed: int = 0) -> TremorDraw:
    """The project's synthetic tremor (stabpen.signals.tremor, TremorSpec defaults) with the same frequency and the
    same peak amplitude as a real draw: the counterfactual that isolates the effect of the real waveform."""
    from stabpen import signals as sg
    spec = sg.TremorSpec(f0=float(draw.meta["f0"]), amp_pk=float(draw.meta["amp_mm"]) * 1e-3)
    d = sg.tremor(draw.t, spec, _rng("synthetic-like", draw.meta["rid"], seed))
    fs_d = 1.0 / float(draw.t[1] - draw.t[0])
    dec = max(1, int(round(fs_d / 1000.0)))
    d = d * (float(draw.meta["amp_mm"]) * 1e-3 / max(D.power_amplitude(d[::dec], fs_d / dec, float(draw.meta["f0"])), 1e-30))
    return TremorDraw(t=draw.t, d=d, meta=dict(draw.meta, synthetic=True, rid="synthetic:" + draw.meta["rid"],
                                               evidence="ASSUMPTION model (stabpen TremorSpec defaults) at the real f0 and amplitude"))


# ------------------------------------------------------------------ writing
def writing(split: str = "test", seed: int = 0, source: str = "unipen", n_words: int = 10, dt: float = WL.SIM_DT,
            writer: Optional[str] = None, **kw) -> WL.RealWritten:
    """Real handwriting with timing in the aiguide Written format.
    source 'unipen' (default): ballpoint on paper, HP Labs 1992 (UNIPEN hpp/hpb2), writer- and text-disjoint splits;
           writer i of the split = seed % n_writers, a different choice of lines per seed
    source 'chartraj': one writer's recorded letters composed into a sentence (CC BY; for committed pictures)
    source 'brush': BRUSH words (timing artefact at 8-12 Hz: NOT for tracker evaluation; kept for the diagnostic)"""
    if source == "chartraj":
        return WL.ct_note(seed=seed, split=split, dt=dt, **kw)
    if source == "unipen":
        idx = WL.unipen_index()
        ws = WL.unipen_writers(split, idx)
        if not ws:
            raise FileNotFoundError(
                f"No licensed UNIPEN writers indexed for split {split!r}; obtain the dataset "
                "under its licence and rebuild the writing index before running this study")
        if writer is not None and writer not in ws:
            raise ValueError(f"UNIPEN writer {writer!r} is not in split {split!r}")
        w = writer or ws[seed % len(ws)]
        out = WL.unipen_note(w, seed=seed, n_words=n_words, dt=dt, index=idx, **kw)
        if out is None:
            raise ValueError(f"UNIPEN writer {w} has too few lines in its split")
        return out
    if source != "brush":
        raise ValueError(f"Unknown handwriting source {source!r}")
    stats = WL.brush_writer_stats()
    ws = WL.brush_writers(split, stats)
    if not ws:
        raise FileNotFoundError(f"No BRUSH writers indexed for split {split!r}; rebuild the writing index")
    if writer is not None and writer not in ws:
        raise ValueError(f"BRUSH writer {writer!r} is not in split {split!r}")
    w = writer or ws[seed % len(ws)]
    out = WL.brush_note(w, seed=seed, n_words=n_words, dt=dt, stats=stats, **kw)
    if out is None:
        raise ValueError(f"BRUSH writer {w} has too few lower-case recordings")
    return out


class RealWriter:
    """Writer-interface parity with aiguide/sim2j writers: RealWriter(key).write(text, dt, seed) -> Written.
    For UNIPEN (key 'unipen/<i>' = the i-th writer of the split, or a writer file id) and BRUSH the text is what the
    writer recorded (the argument is ignored); for chartraj any text made of the 20 recorded letters is composed."""

    def __init__(self, key: str = "unipen/0", split: str = "test"):
        self.source, self.id = key.split("/", 1)
        self.split = split

    def write(self, text: Optional[str] = None, *, dt: float = WL.SIM_DT, seed: int = 0, **kw):
        if self.source == "chartraj":
            return WL.ct_note(text or WL.CT_SENTENCE, seed=seed, split=self.split, dt=dt)
        if self.source == "unipen":
            ws = WL.unipen_writers(self.split)
            if not ws:
                raise FileNotFoundError(f"No licensed UNIPEN writers indexed for split {self.split!r}")
            w = ws[int(self.id) % len(ws)] if self.id.isdigit() else self.id
            return writing(self.split, seed=seed, source="unipen", dt=dt, writer=w, **kw)
        return writing(self.split, seed=seed, source="brush", dt=dt, writer=self.id)


# ------------------------------------------------------------------ scenarios
def tremor_for(written, cls: str, seed: int = 0, kind: str = "PD", split: str = "test", **kw) -> TremorDraw:
    return tremor(cls, seed=seed, kind=kind, split=split, t=written.intended.t, **kw)


def hw1_scenario(written, draw: Optional[TremorDraw] = None):
    """handwriting.plant.Scenario: imposed hand path = real intended writing + real tremor (HW1 convention)."""
    from handwriting import plant as PL
    d = None if draw is None else draw.d
    return PL.scenario_from_written(written, d, meta={"writer": written.real.get("writer") if hasattr(written, "real") else None,
                                                       "tremor": None if draw is None else draw.meta})


def sim2_scenario(written, draw: Optional[TremorDraw] = None, N0: float = 1.0, theta_deg: float = 50.0):
    """sim.pensim.scenarios.Scenario (H1 convention, used by sim2's H1 hand): pref = (xy + tremor, lift), fpush from
    the lift profile.  Translational tremor only (psi_disp = 0, tremor_obj = None)."""
    from sim.pensim import scenarios
    it = written.intended
    d = np.zeros_like(it.xy) if draw is None else draw.d
    sc = scenarios._assemble(it, d, N0, theta_deg, meta={"kind": "realdata", "writer": getattr(written, "real", {}).get("writer"),
                                                         "tremor": None if draw is None else draw.meta})
    sc.psi_disp = np.zeros(len(sc.t))
    sc.tremor_obj = None
    return sc
