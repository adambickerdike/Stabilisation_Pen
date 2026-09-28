"""Writer set-up, tremor scenarios, the pen's sensor streams, the tracker, the oracle and the app's AI templates.

Everything runs on model HW1 (``handwriting/``, used read-only) with the handwriting study's conventions, so the
"Rev H + tracker" and "perfect knowledge" rows reproduce ``results/handwriting`` on the same seeds:

* the writer is adapted to the pen (tremor-free ink = intended letters) and compensates the paper drag;
* the nose acts while the tip is within 2 mm of the page (hover gating, rule T7);
* the tracker is the AKF re-tuned for Rev H (results/opt/inertial_tracker_revh.json) on the fusion sensor models,
  run on the sensor streams of the nose-held ("neutral") run, as handwriting/tracker.py does; its prediction horizon
  includes the servo group delay;
* the oracle is the true handle disturbance with a preview equal to the servo group delay (a limit, not a design).

The app's AI (all causal on the pen side; the app side only uses letters that are already finished):
* text: aiguide's calibrated Tatoeba-CC0 n-gram predictor, top-1 letter two glyphs ahead (the template lead time);
* style: aiguide's online style estimator, calibrated on a pangram and updated letter by letter.  The ink it learns
  from is the app's non-causal clean copy (cleancopy.py) of what the pen recorded: the pangram (hand path + tremor,
  ASSUMPTION: no pen dynamics, as aiguide) and, during the sentence, the handle track from the page sensor (never
  the guided ink, so a template cannot learn from itself);
* placement: each letter template is anchored at the pen's touchdown, at the tracker-corrected handle position
  (page sample minus the tracker's tremor estimate), because the pen only knows its position through its sensors.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import cleancopy as CC

ensure_paths()
from handwriting import et_study as ET  # noqa: E402
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import tracker as TR  # noqa: E402
from handwriting import writers as W  # noqa: E402
from fusion import context as CX  # noqa: E402
from fusion import estimators as ES  # noqa: E402
from fusion import sensors as S  # noqa: E402
from aiguide import guidance as G  # noqa: E402
from aiguide import lm  # noqa: E402
from aiguide import run_guidance as RG  # noqa: E402
from aiguide.sentences import CALIB_SENTENCE  # noqa: E402
from aiguide.style import StyleEstimator  # noqa: E402
from aiguide.template import LetterTemplate, anchor_to, letter_template  # noqa: E402
from stabpen import signals as sg  # noqa: E402

TEXT = W.ET_SENTENCE                 # "return library books by friday"
DEPTH = 2                            # glyphs ahead (the template must reach the pen before touchdown)
C_MIN = G.C_MIN                      # 0.5: letters below send no template (ICD s5 rule 5)
C_FULL = G.C_FULL                    # 0.8: full authority at or above
TRACKER_TAG = len("revH_akf_revh")   # the handwriting study's sensor-seed tag for the re-tuned tracker (same noise draws)
CAL_FS = 1000.0                      # app-side sampling of recorded tracks (Hz)
PS_NOISE = 3e-6                      # page-sensor noise (m RMS), fusion default
HALL_NOISE = 5e-6                    # nose Hall-sensor noise at the tip (m RMS), ASSUMPTION


def gated_conf(c: float) -> float:
    """ICD s5 rule 5: 0 below c_min, else min(1, c / c_full)."""
    return 0.0 if c < C_MIN else min(1.0, c / C_FULL)


@lru_cache(maxsize=1)
def predictor():
    return lm.cached_predictor()


@lru_cache(maxsize=4)
def predictions(text: str = TEXT, depth: int = DEPTH):
    """Per glyph: top-1 letter two glyphs ahead and its calibrated confidence; the most likely wrong letter."""
    return RG.predictions(predictor(), text, depth)


# ------------------------------------------------------------------ pens, tracker
def pens() -> Dict[str, PR.Pen]:
    return {"none": PR.ordinary_pen(), "revH": PR.rev_h()}


def tracker() -> Dict:
    t = PR.akf_revh()
    if t is None:
        raise FileNotFoundError("results/opt/inertial_tracker_revh.json (the Rev H tracker) is required")
    return t


def tracker_params(pen: PR.Pen, trk: Optional[Dict] = None) -> Dict:
    p = dict((trk or tracker())["params"])
    p["horizon"] = float(p.get("horizon", 0.0)) + PR.servo_group_delay(pen)
    return p


# ------------------------------------------------------------------ one writer
class Writer:
    """Writing, recogniser, adapted hand paths and tremor-free runs of one writer (handwriting.et_study.WriterSetup)."""

    def __init__(self, w: int):
        self.w = w
        self.hand = PR.Hand.from_config()
        self.pens = pens()
        self.su = ET.WriterSetup(w, self.hand, self.pens)
        self.written = self.su.written
        self.rec = self.su.rec
        self.preds = predictions()
        self.trk = tracker()

    @property
    def scn0(self):
        return self.su.scn0


@dataclass
class Scenario:
    """One (writer, f0, amp, seed) case: the scenario, the nose-held run, the sensor streams and the tracker."""
    wr: Writer
    f0: float
    amp: float
    seed: int
    scn: PL.Scenario
    neutral: PL.Result                   # Rev H, nose held (the hand-only counterfactual)
    streams: S.Streams
    dh: np.ndarray                       # tracker estimate per tick (m)
    info: Dict
    runs: Dict[str, PL.Result] = field(default_factory=dict)
    extra: Dict = field(default_factory=dict)

    @property
    def pen(self):
        return self.wr.pens["revH"]

    @property
    def Ts(self):
        return self.neutral.info["Ts"]

    @property
    def n_ticks(self):
        return self.neutral.info["n_ticks"]


def sensor_seed(w: int, seed: int, f0: float, amp: float, tag: int) -> int:
    return ET.sensor_seed(w, seed, f0, amp, tag)


def streams_for(res: PL.Result, scn: PL.Scenario, pen: PR.Pen, trk: Dict, seed: int) -> S.Streams:
    rec = TR.record(res, scn, res.info["tick_decim"])
    return S.make_streams(rec, TR.sensor_config(pen, trk["sensors"]), seed)


def make_scenario(wr: Writer, f0: float, amp: float, seed: int) -> Scenario:
    """Tremor (the handwriting study's draw), the nose-held run, its sensor streams and the tracker's estimate."""
    tremor = W.tremor_path(wr.scn0.t, f0, amp, seed, wr.w) if amp > 0 else None
    return _scenario(wr, tremor, f0, amp, seed, sensor_seed(wr.w, seed, f0, amp, TRACKER_TAG))


def make_clean_scenario(wr: Writer) -> Scenario:
    """Tremor-free writing (false correction), with the handwriting study's distortion seed for the re-tuned tracker."""
    return _scenario(wr, None, 0.0, 0.0, 0, sensor_seed(wr.w, 0, 0.0, 0.0, 50 + len("_akf_revh")))


def _scenario(wr: Writer, tremor, f0, amp, seed, s_seed) -> Scenario:
    pen = wr.pens["revH"]
    scn = wr.su.scenario("revH", tremor)
    neutral = wr.su.clean["revH"] if tremor is None else PL.run(scn, pen, wr.hand, ctl=PL.Controls())
    st = streams_for(neutral, scn, pen, wr.trk, s_seed)
    dh, info = ES.akf(st, tracker_params(pen, wr.trk))
    return Scenario(wr, f0, amp, seed, scn, neutral, st, dh, info)


def run_cmd(sc: Scenario, qext: Optional[np.ndarray]) -> PL.Result:
    """Closed loop with a per-tick nose command (m); None = nose held."""
    if qext is None:
        return sc.neutral
    return PL.run(sc.scn, sc.pen, sc.wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(qext)))


def run_none(sc: Scenario) -> PL.Result:
    """The ordinary 12 g pen with the same hand, writing and tremor."""
    scn = sc.wr.su.scenario("none", None if sc.amp <= 0 else sc.scn.tremor)
    return PL.run(scn, sc.wr.pens["none"], sc.wr.hand, ctl=PL.Controls())


def oracle_cmd(sc: Scenario) -> np.ndarray:
    return TR.oracle_command(sc.neutral, sc.wr.su.clean["revH"], sc.pen, sc.n_ticks, sc.Ts)


def ticks_to_record(sc: Scenario, x_ticks: np.ndarray, t_rec: np.ndarray) -> np.ndarray:
    """Per-tick signal sampled at record times (zero-order hold, as the plant reads it)."""
    k = np.clip(np.floor(t_rec / sc.Ts + 1e-9).astype(int), 0, len(x_ticks) - 1)
    return np.asarray(x_ticks)[k]


# ------------------------------------------------------------------ recorded tracks (what the pen logs)
def recorded_track(res: PL.Result, which: str, rng: np.random.Generator, fs: float = CAL_FS):
    """The track the pen reports to the app at fs: 'handle' (page sensor) or 'ink' (page sensor + nose Hall sensor).
    Returns (t, xy, pen_down)."""
    t = res.t
    step = max(1, int(round((1.0 / fs) / float(t[1] - t[0]))))
    idx = np.arange(0, len(t), step)
    xy = (res.handle if which == "handle" else res.ink)[idx].copy()
    xy += rng.standard_normal(xy.shape) * PS_NOISE
    if which == "ink":
        xy += rng.standard_normal(xy.shape) * HALL_NOISE
    return t[idx].copy(), xy, res.contact[idx] > 0.5


# ------------------------------------------------------------------ the app's AI: style and templates
def calibrate_style(wr: Writer, f0: float, amp: float, seed: int, clean_kw: Optional[Dict] = None) -> StyleEstimator:
    """Style from the app's clean copy of a calibration pangram written with the same tremor.

    The pangram is aiguide's (a different sentence by the same writer, instance seed 1000 + w); the recorded track is
    the hand path plus tremor (ASSUMPTION: no pen dynamics, as aiguide's calibration), which the app cleans
    non-causally before fitting letters (cleancopy.wiener_clean)."""
    cal = wr.written_cal if hasattr(wr, "written_cal") else None
    if cal is None:
        wtr = W.writer(wr.w)
        cal = wtr.write(CALIB_SENTENCE, dt=1.0 / CAL_FS, seed=1000 + wr.w)
        wr.written_cal = cal
    t = cal.intended.t
    xy = cal.intended.xy.copy()
    if amp > 0:
        rs = 7_000_000 + 1000 * wr.w + 10 * int(round(f0)) + int(round(amp * 1e4)) + 97 * (seed % 1000)
        xy = xy + sg.tremor(t, sg.TremorSpec(f0=f0, amp_pk=amp), np.random.default_rng(rs))
    down = np.asarray(cal.intended.pen_down, bool)
    xy = xy + np.random.default_rng(11 + wr.w).standard_normal(xy.shape) * PS_NOISE
    clean, _ = CC.wiener_clean(t, xy, down, **(clean_kw or {}))
    est = StyleEstimator()
    dec = 5                                                     # 200 Hz, as aiguide
    for L in cal.letters:
        strokes, times = [], []
        for a, b in L.strokes:
            m = np.flatnonzero(down[a:b]) + a
            m = m[::dec] if len(m) > dec else m
            if len(m) >= 2:
                strokes.append(clean[m])
                times.append(t[m])
        if strokes:
            est.update(L.char, strokes, t_strokes=times,
                       new_word=L.text_index > 0 and cal.text[L.text_index - 1] == " ")
    return est


def templates(sc: Scenario, est0: StyleEstimator, clean_kw: Optional[Dict] = None) -> Dict[str, List[LetterTemplate]]:
    """Letter templates per prediction case, pen-anchored at the tracker-corrected touchdown position.

    oracle        the writer's true intended letters (a known text, e.g. copying; the upper bound of any template)
    ai_correct    the correct letter in the estimated style (own exemplars), full confidence
    ai_predicted  the predictor's top-1 letter two glyphs ahead, with its calibrated confidence
    wrong_full    the most likely wrong letter for every letter, at full confidence (safety case)"""
    wr = sc.wr
    written = wr.written
    res = sc.neutral
    # touchdown anchors: corrected handle position (handle - tracker estimate) at each letter's first contact
    dh_rec = ticks_to_record(sc, sc.dh, res.t)
    anchor_arr = {"t": res.t, "contact": res.contact, "pH": np.column_stack([res.handle - dh_rec, np.zeros(len(res.t))])}
    td = G.touchdowns(written, anchor_arr)
    # exemplar source: the app's clean copy of the recorded handle track (never the guided ink)
    t1, xy1, down1 = recorded_track(res, "handle", np.random.default_rng(31 + wr.w + int(sc.seed) + int(sc.f0 * 10)))
    clean1, _ = CC.wiener_clean(t1, xy1, down1, **(clean_kw or {}))
    hp_arr = {"t": t1, "contact": down1.astype(float), "pH": np.column_stack([clean1, np.zeros(len(t1))])}
    hp = G.hand_path_strokes(written, hp_arr)
    est = copy.deepcopy(est0)
    preds = wr.preds
    out = {"oracle": [], "ai_correct": [], "ai_predicted": [], "wrong_full": []}
    for k, L in enumerate(written.letters):
        e = est.estimate()
        anchor = td[k] if td[k] is not None else L.polylines[0][0]
        pk = preds[k]
        for cond, ch, cf in (("ai_correct", L.char, 1.0), ("ai_predicted", pk["top1"], pk["conf"]),
                             ("wrong_full", pk["wrong"], 1.0)):
            tpl = letter_template(ch, e, 0.0, 0.0, estimator=est, mode="exemplar", conf=cf, glyph_index=k)
            out[cond].append(anchor_to(tpl, anchor))
        out["oracle"].append(LetterTemplate(L.char, [np.asarray(p, float).copy() for p in L.polylines], 1.0, "oracle", k))
        strokes, times = hp[k]
        if strokes:
            est.update(L.char, strokes, t_strokes=times, new_word=k > 0 and written.text[L.text_index - 1] == " ",
                       keep_exemplar=True)
    return out


def template_conf(cond: str, preds: Sequence[Dict]) -> List[float]:
    """Per-letter authority the pen applies (rule 5 on the calibrated confidence)."""
    if cond == "ai_predicted":
        return [gated_conf(p["conf"]) for p in preds]
    return [1.0] * len(preds)


def template_arrays(letters: Sequence[LetterTemplate], conf: Sequence[float], step: float = 20e-6) -> Dict:
    return CX.template_arrays(letters, conf, step=step)


def template_error_um(sc: Scenario, letters: Sequence[LetterTemplate]) -> Dict[str, float]:
    """Distance of the template from the intended letters: RMS over intended pen-down points of the nearest template
    point of the same letter; after removing a per-letter offset (placement); and the 3-15 Hz part along the
    intended trajectory (what a tremor estimator could confuse with tremor)."""
    from scipy.signal import butter, sosfiltfilt
    from scipy.spatial import cKDTree
    it = sc.wr.written.intended
    dec = max(1, int(round(1e-3 / (it.t[1] - it.t[0]))))
    tot, off, band = [], [], []
    sos = butter(4, [3.0, 15.0], btype="band", fs=1000.0, output="sos")
    for k, L in enumerate(sc.wr.written.letters):
        T = np.vstack([CX.template_arrays([letters[k]], [1.0], step=5e-6)["xy"]])
        if len(T) < 2:
            continue
        tree = cKDTree(T)
        idx = np.concatenate([np.arange(a, b, dec) for (a, b) in L.strokes])
        idx = idx[np.asarray(it.pen_down)[idx]]
        if len(idx) < 8:
            continue
        P = it.xy[idx]
        _, j = tree.query(P)
        e = P - T[j]
        tot.append(np.sum(e ** 2, axis=1))
        o = e.mean(axis=0)
        _, j2 = tree.query(P - o)
        off.append(np.sum((P - o - T[j2]) ** 2, axis=1))
        for (a, b) in L.strokes:
            ii = np.arange(a, b, dec)
            ii = ii[np.asarray(it.pen_down)[ii]]
            if len(ii) < 40:
                continue
            _, jj = tree.query(it.xy[ii])
            es = it.xy[ii] - T[jj]
            band.append(np.sum(sosfiltfilt(sos, es - es.mean(0), axis=0) ** 2, axis=1))
    f = lambda v: float(np.sqrt(np.mean(np.concatenate(v))) * 1e6) if v else float("nan")  # noqa: E731
    return {"total_um": f(tot), "after_offset_um": f(off), "band_3_15Hz_um": f(band)}
