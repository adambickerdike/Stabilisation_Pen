r"""Guided writing in sim2 with the Rev J pen: dysgraphia tracing, PD 'write big' loops, dyslexia lead-through
(SIMULATION; the tasks of the handwriting and drive studies, rebuilt on the v2 writers).

  tracing      dysgraphia-like learners (handwriting.writers error model: malformed letters, size and baseline
               irregularity) copy "a big dog dug a deep pit by the pond"; the target = the copybook letters in the
               learner's size and slant anchored at the learner's first touchdown of each letter (handwriting.practice);
               the learner's hand path is adapted to the pen (as ET).  Controllers: none; nose guidance partial (0.5)
               and full (1.0) (HW1's law: capture 2 mm, drop 2.5 mm / 60 ms, stroke matching); the steered wheel
               alone (steer-only Stanley on the template); wheel + nose (coordinated: the wheel for the gross path and
               the constraint, the nose for the fine correction).
  loops        a micrographia-like writer draws 5 loops (board.control.loops, 10 mm target) that shrink from 0.8 to 0.6
               of the target (drive task b), relaxed (HAP-26 nominal arm) and lightly resisting (the HAP-26 upper 95 %
               CI arm: 533 N/m, 27.6 N s/m) hands; wheel steer-only and wheel + nose on the 10 mm template.
  lead         a relaxed writer (the writer's aim follows the hand while the pen is down, time constant 0.25 s; the
               writer makes the pen-up moves: the drive study's model) is led along the target letters by the driven
               wheel, with the nose adding the detail (drive task e: 'wheel lead + nose'); dyslexia-like learners, so
               the target letters are the correct ones whatever the learner would have written.
Metrics: distance of the ink to the target letters, letters read as the target and words read by the app
(handwriting.metrics), coverage, device share, felt grip force, wheel force and slip, power.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import ROOT  # noqa: F401
from . import revj as RJ
from . import stepper as ST
from . import tasks as TK
from . import writers as WV
from .firmware import FWConfig
from handwriting import metrics as MT  # noqa: E402
from handwriting import writers as HWR  # noqa: E402
from aiguide.glyphs import GLYPH_SET  # noqa: E402
from aiguide.template import LetterTemplate, build_track  # noqa: E402
from sim.pensim import scenarios as PS  # noqa: E402
from stabpen import signals as sg  # noqa: E402

SIM_DT = TK.SIM_DT
DT = 50e-6
PRACTICE = HWR.PRACTICE_SENTENCE


def learner(w: int, seed: int, profile: str, text: str = PRACTICE, version: str = "v2"):
    prof = HWR.dysgraphia_profile() if profile == "dysgraphia" else HWR.dyslexia_profile()
    if profile == "dyslexia":
        s = text.replace(" ", "")
        k = s.find("deep")
        prof.wrong_letters = {k + 2: "a"} if k >= 0 else {}
    plan = HWR.error_plan(text, prof, 10_000 * w + seed)
    wtr = WV.writer(w, version)
    wr = wtr.write(text, dt=SIM_DT, seed=6000 + w, size_factors=plan["size"], glyph_override=plan["override"],
                   extra_warp=plan["warp"], baseline_offsets=plan["baseline"], err_seed=8000 + 10 * w + seed)
    targets = [c for c in text if c != " "]
    return wr, plan, targets, wtr


def target_letters(wr, targets: List[str], size_scale: float) -> List[LetterTemplate]:
    """Copybook glyphs of the correct letters in the learner's size, width and slant, anchored at the learner's first
    touchdown of the letter (handwriting.practice.target_letters with the v2 letter size)."""
    st = wr.style
    shear = math.tan(math.radians(st.slant_deg))
    out = []
    h = st.x_height_mm * 1e-3 * size_scale
    for k, (L, ch) in enumerate(zip(wr.letters, targets)):
        strokes = [np.column_stack([h * (st.width * g[:, 0] + g[:, 1] * shear), h * g[:, 1]]) for g in GLYPH_SET[ch]]
        t = LetterTemplate(ch, strokes, 1.0, "copybook", k)
        out.append(t.translate(L.polylines[0][0] - strokes[0][0]))
    return out


class GuidedCase:
    """A learner (tracing) with its adapted hand path, template track and clean run with nothing on."""

    def __init__(self, w: int, seed: int, profile: str, pm, n_adapt: int = 3, relaxed: bool = False, log=None,
                 version: str = "v2"):
        self.w, self.seed, self.profile = w, seed, profile
        self.pm = pm
        wr, plan, targets, wtr = learner(w, seed, profile, version=version)
        self.written, self.plan, self.targets = wr, plan, targets
        self.rec = MT.recognizer_for(wr)
        scale = wtr.kp.size_scale if version == "v2" else 1.0
        v_t = wtr.v_target if version == "v2" else wr.style.speed_mm_s * 1e-3
        self.tl = target_letters(wr, targets, scale)
        self.track = build_track(self.tl, speed=v_t, air_speed=wr.style.air_speed_mm_s * 1e-3, dt=0.5e-3)
        it = wr.intended
        self.t = it.t
        self.intended = it.xy.copy()
        self.hand_path = it.xy.copy()
        self.v_target = v_t
        t0 = time.time()
        self.adapt_hist = self._adapt(n_adapt)
        self.none = ST.run(pm, self.scenario(), FWConfig(), self.task())
        if log:
            log(f"[guided] {profile} w{w} s{seed}: adaptation {['%.0f' % h for h in self.adapt_hist]} um, "
                f"{time.time() - t0:.0f} s")

    def task(self):
        return {"template": {"xy": self.track.xy, "down": self.track.pen_down.astype(float)}}

    def scenario(self, hand_path=None):
        it = self.written.intended
        hp = self.hand_path if hand_path is None else hand_path
        itx = sg.Intended(it.t, hp, it.pen_down, it.lift, it.features)
        sc = PS._assemble(itx, np.zeros_like(hp), 1.0, 50.0, meta={"kind": "tracing", "writer": self.w})
        sc.intended = self.intended
        sc.psi_disp = np.zeros(len(it.t))
        sc.tremor_obj = None
        return sc

    def _adapt(self, n_iter):
        m = self.written.intended.pen_down
        sos = butter(2, 10.0, fs=1.0 / SIM_DT, output="sos")
        v = np.gradient(self.intended, SIM_DT, axis=0)
        hist = []
        for _ in range(n_iter):
            r = ST.run(self.pm, self.scenario(), FWConfig())
            ink = np.column_stack([np.interp(self.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - self.intended
            hist.append(float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6))
            lag = max(0.0, float(-np.sum(e[m] * v[m]) / max(np.sum(v[m] * v[m]), 1e-30)))
            k = int(round(lag / SIM_DT))
            ea = np.vstack([e[k:], np.repeat(e[-1:], k, 0)]) if k > 0 else e
            self.hand_path = self.hand_path - 0.9 * sosfiltfilt(sos, ea, axis=0)
        return hist

    def metrics(self, r) -> Dict:
        R = TK.Res(r)
        rows = MT.letter_rows(self.written, R, self.rec, targets=self.targets, target_polys=[t.strokes for t in self.tl])
        s = MT.summary(rows)
        wd = MT.words(rows, PRACTICE)
        kinds = self.plan["kind"]
        ok_err = [rw.get("recognised_ok", False) for rw, k in zip(rows, kinds) if k != "ok"]
        out = {"target_err_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
               "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
               "error_letters_read_as_target": float(np.mean(ok_err)) if ok_err else None,
               "coverage": coverage(self.tl, r)}
        out.update(TK.device_effect(r, self.none))
        out.update(TK.power(r))
        out.update(wheel_metrics(r))
        return out


def coverage(tl, r, thr: float = 0.3e-3) -> float:
    from scipy.spatial import cKDTree
    from aiguide.template import dense
    tm = np.vstack([dense(t.strokes, step=50e-6) for t in tl])
    ink = r.ink()[r["contact"] > 0.5]
    if len(ink) < 2:
        return 0.0
    d, _ = cKDTree(ink).query(tm)
    return float(np.mean(d < thr))


def wheel_metrics(r) -> Dict:
    if "wN" not in r.idx:
        return {}
    c = r["contact"] > 0.5
    if not c.any():
        return {}
    F = np.hypot(r["wFx"], r["wFy"])
    return {"wheel_F_rms_N": float(np.sqrt(np.mean(F[c] ** 2))), "wheel_F_p95_N": float(np.percentile(F[c], 95)),
            "wheel_F_max_N": float(F[c].max()), "wheel_N_mean_N": float(np.mean(r["wN"][c])),
            "wheel_slide_share": float(np.mean(r["wslide"][c] > 0.5))}


TRACING_CTL = {
    "none": FWConfig(),
    "nose_partial": FWConfig(nose="guide", g_guide=0.5),
    "nose_full": FWConfig(nose="guide", g_guide=1.0),
    "wheel": FWConfig(wheel="path"),
    "wheel_nose": FWConfig(nose="guide", g_guide=1.0, wheel="path"),
}


def mu_case(w, seed, tag=0):
    return float(np.random.default_rng(990_000 + 1000 * w + seed + 37 * tag).uniform(0.6, 1.2))


def run_tracing(gc: GuidedCase, ctl: str) -> Dict:
    fw = replace(TRACING_CTL[ctl], seed=gc.seed * 13 + gc.w)
    mu = mu_case(gc.w, gc.seed)
    t0 = time.time()
    r = ST.run(gc.pm, gc.scenario(), fw, gc.task(), mu=mu, seed=gc.seed)
    m = gc.metrics(r)
    m.update({"w": gc.w, "seed": gc.seed, "profile": gc.profile, "ctl": ctl, "mu": mu, "wall_s": time.time() - t0})
    return m


# ================================================================================================ loops (PD write big)
HANDS = {"relaxed": dict(k_arm=170.0, b_arm=11.0), "resisting": dict(k_arm=533.0, b_arm=27.6)}


class LoopsCase:
    def __init__(self, seed: int, hand: str = "relaxed", target_mm: float = 10.0, start_ratio: float = 0.8,
                 end_ratio: float = 0.6, speed_mm_s: float = 20.0, dt: float = DT, n_adapt: int = 3):
        from board import control as BC
        from aiguide.writer import Path as APath
        self.seed = seed
        self.hand = hand
        self.target_mm = target_mm
        self.tp = BC.loops(5, target_mm, 6.0, 900, 20.0, 150.0)
        self.intended_mm = BC.loops(5, target_mm, 6.0, 900, 20.0, 150.0,
                                    scale_fn=lambda u: start_ratio + (end_ratio - start_ratio) * u)
        cfg = RJ.config(heel=True, dt=dt, hand=RJ.P.HandH1(r_rot=0.5, **HANDS[hand]))
        self.pm = RJ.build(cfg)
        self.it = self._intended(self.intended_mm * 1e-3, speed_mm_s)
        self.track_it = self._intended(self.tp * 1e-3, speed_mm_s, dt_=0.5e-3)
        self.t = self.it.t
        self.hand_path = self.it.xy.copy()
        m = self.it.pen_down
        sos = butter(2, 10.0, fs=1.0 / SIM_DT, output="sos")
        v = np.gradient(self.it.xy, SIM_DT, axis=0)
        for _ in range(n_adapt):
            r = ST.run(self.pm, self.scenario(), FWConfig())
            ink = np.column_stack([np.interp(self.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - self.it.xy
            lag = max(0.0, float(-np.sum(e[m] * v[m]) / max(np.sum(v[m] * v[m]), 1e-30)))
            k = int(round(lag / SIM_DT))
            ea = np.vstack([e[k:], np.repeat(e[-1:], k, 0)]) if k > 0 else e
            self.hand_path = self.hand_path - 0.9 * sosfiltfilt(sos, ea, axis=0)
        self.none = ST.run(self.pm, self.scenario(), FWConfig(), self.task())

    def _intended(self, P, speed_mm_s, dt_=SIM_DT):
        from aiguide.writer import Path as APath
        first = P[0]
        pb = APath(dt_, start=(first[0] - 1e-3, first[1] + 1e-3), lift_height=1.5e-3)
        pb.dwell(0.1)
        pb.move(P[0], 0.1)
        pb.pen(True, 0.04)
        pb.dwell(0.015)
        L = float(np.sum(np.hypot(*np.diff(P, axis=0).T)))
        pb.polyline(P, max(0.05, L / (speed_mm_s * 1e-3)))
        pb.dwell(0.01)
        pb.pen(False, 0.04)
        pb.dwell(0.2)
        return pb.build()

    def task(self):
        return {"template": {"xy": self.track_it.xy, "down": self.track_it.pen_down.astype(float)},
                "psi0": math.atan2(*(self.tp[1] - self.tp[0])[::-1])}

    def scenario(self):
        it = self.it
        itx = sg.Intended(it.t, self.hand_path, it.pen_down, it.lift, [])
        sc = PS._assemble(itx, np.zeros_like(self.hand_path), 1.0, 50.0, meta={"kind": "loops"})
        sc.intended = it.xy.copy()
        sc.psi_disp = np.zeros(len(it.t))
        sc.tremor_obj = None
        return sc

    def metrics(self, r) -> Dict:
        c = r["contact"] > 0.5
        y = r.ink()[c, 1] * 1e3 - 150.0
        x = r.ink()[c, 0] * 1e3 - 20.0
        heights = []
        for k in range(5):
            m = (x >= 6.0 * k - 3.0) & (x < 6.0 * k + 3.0)
            if m.sum() > 10:
                heights.append(float(np.percentile(y[m], 99) - np.percentile(y[m], 1)))
        out = {"loop_height_ratio": float((np.percentile(y, 99) - np.percentile(y, 1)) / self.target_mm),
               "last_loop_ratio": heights[-1] / self.target_mm if heights else float("nan"),
               "loop_heights_mm": heights}
        ink = r.ink()[c][::10] * 1e3
        d = np.sqrt(((ink[:, None, :] - self.tp[None, :, :]) ** 2).sum(-1)).min(1)
        out["ink_to_template_rms_mm"] = float(np.sqrt(np.mean(d ** 2)))
        out.update(TK.device_effect(r, self.none))
        out.update(wheel_metrics(r))
        out.update(TK.power(r))
        return out


LOOPS_CTL = {"none": FWConfig(), "wheel": FWConfig(wheel="path"), "wheel_nose": FWConfig(wheel="path", nose="guide", g_guide=1.0),
             "wheel_lead": FWConfig(wheel="lead"), "nose_full": FWConfig(nose="guide", g_guide=1.0)}


def run_loops(lc: LoopsCase, ctl: str) -> Dict:
    fw = replace(LOOPS_CTL[ctl], seed=lc.seed)
    mu = mu_case(lc.seed, lc.seed, tag=5)
    t0 = time.time()
    r = ST.run(lc.pm, lc.scenario(), fw, lc.task(), mu=mu, seed=lc.seed)
    m = lc.metrics(r)
    m.update({"seed": lc.seed, "hand": lc.hand, "ctl": ctl, "mu": mu, "wall_s": time.time() - t0})
    return m


# ================================================================================================ lead-through (dyslexia)
RELAXED = {"tau": 0.25, "tau_air": 0.05}       # drive/params.RELAX_TAU_S (ASSUMPTION, board lead-through model)
LEAD_WORDS = (3, 4, 5)                          # "dug a deep": the learner's error word and its neighbours (compute)


class LeadCase:
    """Dyslexia lead-through: a dyslexia-like learner (handwriting.writers dyslexia profile: 'deep' written 'daep'); the
    target = the correct copybook letters in the learner's size anchored at the learner's touchdowns (as tracing).
    A relaxed writer (stepper 'relaxed': the aim follows the hand while the pen is down, 0.25 s) puts the pen down at
    each target stroke's start and keeps it down for (stroke time at the lead speed) x 1.3 + 0.2 s while the drive leads
    it; the writer makes the pen-up moves to the next stroke's start (the app shows where it starts: ASSUMPTION; drive
    task e's schedule).  Conditions: 'writer_alone' (the learner writes as they would, adapted hand path, nothing on),
    'lead' (driven wheel lead mode along the target), 'lead_nose' (+ nose guidance on the template), 'relaxed_none'
    (relaxed writer, nothing on: the pen stays where the writer puts it down)."""

    def __init__(self, w: int, seed: int, pm, lead_speed: float = 8.0, version: str = "v2", n_adapt: int = 3, log=None,
                 words: Optional[tuple] = None):
        from aiguide.writer import Path as APath
        self.w, self.seed, self.pm = w, seed, pm
        self.gc = GuidedCase(w, seed, "dyslexia", pm, n_adapt=n_adapt, version=version, log=log)
        tw = PRACTICE.split(" ")
        word_of = [wi for wi, wd in enumerate(tw) for _ in wd]
        self.sel = [i for i in range(len(self.gc.tl)) if words is None or word_of[i] in words]
        self.words = tuple(sorted(set(word_of[i] for i in self.sel)))
        self.subtext = " ".join(tw[i] for i in self.words)
        self.word_local = {wi: k for k, wi in enumerate(self.words)}
        self.word_of = word_of
        self.tl = [self.gc.tl[i] for i in self.sel]
        self.track = build_track(self.tl, speed=self.gc.v_target, air_speed=self.gc.written.style.air_speed_mm_s * 1e-3,
                                 dt=0.5e-3)
        strokes = [np.asarray(s, float) for t in self.tl for s in t.strokes]
        self.owner = [i for i, t in enumerate(self.tl) for _ in t.strokes]
        first = strokes[0][0]
        pb = APath(SIM_DT, start=(first[0] - 1e-3, first[1] + 1e-3), lift_height=1.5e-3)
        pb.dwell(0.1)
        for s in strokes:
            travel = float(np.hypot(*(s[0] - pb.pos)))
            pb.move(s[0], 0.06 + travel / 0.1)
            pb.pen(True, 0.04)
            pb.dwell(0.015)
            L = float(np.sum(np.hypot(*np.diff(s, axis=0).T)))
            T = max(0.05, L / (lead_speed * 1e-3))
            pb.polyline(s, T)
            pb.dwell(0.01 + 0.3 * T + 0.2)
            pb.pen(False, 0.04)
        pb.dwell(0.2)
        self.it = pb.build()
        self.n_strokes = len(strokes)

    def task(self):
        return {"template": {"xy": self.track.xy, "down": self.track.pen_down.astype(float)}}

    def writer_alone(self) -> Dict:
        """The learner writing by themselves (adapted hand path, nothing on), scored on the same letters and words."""
        gc = self.gc
        rows = MT.letter_rows(gc.written, TK.Res(gc.none), gc.rec, targets=gc.targets,
                              target_polys=[t.strokes for t in gc.tl])
        sub = []
        for i in self.sel:
            r = dict(rows[i])
            r["word_index"] = self.word_local[self.word_of[i]]
            sub.append(r)
        s = MT.summary(sub)
        wd = MT.words(sub, self.subtext)
        return {"target_err_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
                "words_letters": wd["word_accuracy_letters"], "words_app": wd.get("word_accuracy_app"),
                "recognised": " ".join(wd["recognised"]), "coverage": coverage(self.tl, gc.none)}

    def scenario(self):
        it = self.it
        itx = sg.Intended(it.t, it.xy, it.pen_down, it.lift, [])
        sc = PS._assemble(itx, np.zeros_like(it.xy), 1.0, 50.0, meta={"kind": "lead", "writer": self.w})
        sc.intended = it.xy.copy()
        sc.psi_disp = np.zeros(len(it.t))
        sc.tremor_obj = None
        return sc

    def evaluate_by_strokes(self, r) -> Dict:
        """drive/scenarios.evaluate_by_strokes on sim2 records: the ink split into pen-down runs, one per target stroke
        in order, scored against the target letters (aiguide letter_metrics, the app's recogniser, words)."""
        from aiguide.metrics import letter_metrics
        gc = self.gc
        A, B = pen_down_runs(r)
        ink = r.ink()
        q = np.column_stack([r["qpx"], r["qpy"]]) if "qpx" in r.idx else None
        rows = []
        for i, t in enumerate(self.tl):
            gi = self.sel[i]
            wl = self.word_local[self.word_of[gi]]
            idx = [j for j, o in enumerate(self.owner) if o == i]
            if not idx or idx[-1] >= len(A):
                rows.append({"char": gc.targets[gi], "missing": True, "word_index": wl})
                continue
            a, b = A[idx[0]], B[idx[-1]]
            lm = letter_metrics(ink[a:b], r["contact"][a:b], t.strokes, gc.targets[gi], gc.rec,
                                q=q[a:b] if q is not None else None)
            lm["word_index"] = wl
            rows.append(lm)
        s = MT.summary(rows)
        wd = MT.words(rows, self.subtext)
        return {"target_err_um": s.get("path_rms_um"), "target_p95_um": s.get("path_p95_um"),
                "letters_read": s.get("recognition_accuracy"), "words_letters": wd["word_accuracy_letters"],
                "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
                "n_strokes_done": int(len(A)), "n_strokes_target": int(self.n_strokes),
                "coverage": coverage(self.tl, r)}


def pen_down_runs(r, min_gap_s: float = 0.04, min_len_s: float = 0.01):
    """Pen-down runs of a record (index ranges), with touchdown bounces merged: gaps shorter than min_gap_s join the
    runs around them (sim2's ball bounces at touchdown; the firmware's stroke counter uses the same 40 ms)."""
    c = r["contact"] > 0.5
    t = r["t"]
    dt = float(t[1] - t[0]) if len(t) > 1 else 5e-4
    d = np.diff(np.r_[0, c.astype(np.int8), 0])
    A, B = list(np.flatnonzero(d == 1)), list(np.flatnonzero(d == -1))
    i = 0
    while i + 1 < len(A):
        if (A[i + 1] - B[i]) * dt < min_gap_s:
            B[i] = B[i + 1]
            del A[i + 1], B[i + 1]
        else:
            i += 1
    A, B = np.array(A, int), np.array(B, int)
    keep = (B - A) * dt >= min_len_s
    return A[keep], B[keep]


LEAD_CTL = {"relaxed_none": FWConfig(), "lead": FWConfig(wheel="lead"),
            "lead_nose": FWConfig(wheel="lead", nose="guide", g_guide=1.0)}


def run_lead(lc: LeadCase, ctl: str, ref=None, keep: bool = False) -> Dict:
    """ref: the 'relaxed_none' run (the device share and the felt grip force are measured against it: without the
    device the relaxed writer's pen stays where it was put down)."""
    t0 = time.time()
    mu = mu_case(lc.w, lc.seed, tag=9)
    if ctl == "writer_alone":
        m = lc.writer_alone()
        m.update({"w": lc.w, "seed": lc.seed, "ctl": ctl, "mu": mu, "wall_s": 0.0, "words_used": lc.subtext})
        return m
    fw = replace(LEAD_CTL[ctl], seed=lc.seed * 17 + lc.w)
    r = ST.run(lc.pm, lc.scenario(), fw, lc.task(), mu=mu, seed=lc.seed, relaxed=RELAXED)
    m = lc.evaluate_by_strokes(r)
    m.update(wheel_metrics(r))
    if ref is not None:
        m.update(TK.device_effect(r, ref))
    m.update(TK.power(r))
    if keep:
        m["_r"] = r
    c = r["contact"] > 0.5
    v = np.hypot(*np.gradient(r.ink(), float(r["t"][1] - r["t"][0]), axis=0).T)
    m["pen_speed_mm_s"] = float(np.mean(v[c]) * 1e3) if c.any() else 0.0
    m.update({"w": lc.w, "seed": lc.seed, "ctl": ctl, "mu": mu, "wall_s": time.time() - t0})
    return m
