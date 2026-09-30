r"""Scenarios of the round-2 study in sim2 (SIMULATION inputs; synthetic writers and tremor, nothing measured).

  WriterCase     one writer (v2 by default, v1 for comparison) writing a text at the sim step, with its recogniser;
                 hand path adapted to the Rev J pen (iterative learning on the tremor-free run: the writer has learned
                 the pen, as HW1's adapted writer, and compensates the paper drag); tremor on the hand path (H1 hand:
                 handwriting.writers.tremor_path, the project's tremor model and seeding, as the handwriting, drive and
                 nose2 studies) or as torques at the forearm and wrist (arm hand: sim2.tremor ET profile, calibrated
                 to the peak amplitude at the lifted pen tip).
  ET             "return library books by friday", test writers 0-5, seeds 200-203, 4-12 Hz x 0.3-2 mm
  loops          PD 'write big': board.control.loops (5 loops, 10 mm target) drawn by a writer whose loops shrink
                 from 0.8 to 0.6 of the target (drive study task b)
  tracing        dysgraphia-like learners copy "a big dog dug a deep pit by the pond" (handwriting.practice error
                 model); the template = the copybook letters anchored at the learner's touchdowns (drive task a)
  lead-through   a relaxed writer holds the pen down while the drive leads along the target letters (drive task e);
                 dyslexia-like learners, the practice sentence
  autowrite      the hand sweeps along the line; the pen draws a known text with the C1S nose (nose2 planner)
Every run is a SIMULATION.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import ROOT  # noqa: F401
from . import writers as WV
from sim.pensim import scenarios as PS  # noqa: E402
from stabpen import signals as sg  # noqa: E402
from handwriting import metrics as MT  # noqa: E402
from handwriting import writers as HWR  # noqa: E402

SIM_DT = 25e-6


class Res:
    """sim2 Result -> the attributes handwriting.metrics expects (t, ink, contact, handle, xy('qx'))."""

    def __init__(self, r):
        self.r = r
        self.t = r["t"]
        self.ink = r.ink()
        self.contact = r["contact"]
        self.handle = r.ball()
        self.info = r.info

    def __getitem__(self, k):
        return self.r[k]

    def xy(self, base):
        if base in ("qx", "q"):
            return np.column_stack([self.r["qpx"], self.r["qpy"]]) if "qpx" in self.r.idx else np.zeros((len(self.t), 2))
        return self.r.xy(base)


def preroll(written, pre_s: float):
    """The same writing preceded by pre_s seconds of the pen resting on the paper at the first touchdown (the writer
    has placed the pen; tremor, when present, acts from the start).  The approach before the first touchdown is dropped;
    letter windows, spans and features are shifted.  The rest's ink is not scored (it lies outside every letter)."""
    import copy
    it = written.intended
    dt = float(it.t[1] - it.t[0])
    k0 = int(np.flatnonzero(it.pen_down)[0])
    n_pre = int(round(pre_s / dt))
    xy = np.vstack([np.repeat(it.xy[k0:k0 + 1], n_pre, 0), it.xy[k0:]])
    down = np.r_[np.ones(n_pre, bool), it.pen_down[k0:]]
    lift = np.r_[np.zeros(n_pre), it.lift[k0:]]
    t = np.arange(len(xy)) * dt
    shift_t = n_pre * dt - float(it.t[k0])
    shift_k = n_pre - k0
    feats = [(f[0], f[1] + shift_t, f[2] + shift_t) + tuple(f[3:]) for f in it.features]
    out = copy.copy(written)
    out.intended = sg.Intended(t, xy, down, lift, feats)
    out.letters = []
    for L in written.letters:
        L2 = copy.copy(L)
        L2.span = (L.span[0] + shift_k, L.span[1] + shift_k)
        L2.strokes = [(a + shift_k, b + shift_k) for a, b in L.strokes]
        L2.t0 = L.t0 + shift_t
        L2.t1 = L.t1 + shift_t
        out.letters.append(L2)
    out.meta = dict(written.meta, preroll_s=pre_s)
    return out


@dataclass
class WriterCase:
    w: int
    version: str = "v2"
    text: str = WV.ET_SENTENCE
    write_kw: Dict = field(default_factory=dict)
    N0: float = 1.0
    pre_s: float = 0.0              # the pen rests on the paper this long before writing (preroll)

    def __post_init__(self):
        wr = WV.writer(self.w, self.version)
        self.written = wr.write(self.text, dt=SIM_DT, seed=2000 + self.w, **self.write_kw)
        if self.pre_s > 0:
            self.written = preroll(self.written, self.pre_s)
        self.rec = MT.recognizer_for(self.written)
        it = self.written.intended
        self.t = it.t
        self.intended = it.xy.copy()
        self.hand_path = it.xy.copy()
        self.adapted = False

    def scenario(self, tremor: Optional[np.ndarray] = None, hand_path: Optional[np.ndarray] = None, theta_deg: float = 50.0):
        it = self.written.intended
        hp = self.hand_path if hand_path is None else hand_path
        d = np.zeros_like(hp) if tremor is None else tremor
        itx = sg.Intended(it.t, hp, it.pen_down, it.lift, it.features)
        sc = PS._assemble(itx, d, self.N0, theta_deg, meta={"kind": "sim2j", "writer": self.w})
        sc.intended = self.intended
        sc.psi_disp = np.zeros(len(it.t))
        sc.tremor_obj = None
        sc.down = it.pen_down.astype(float)
        return sc

    def tremor(self, f0: float, amp: float, seed: int, **kw):
        return HWR.tremor_path(self.t, f0, amp, seed, self.w, **kw)

    def adapt(self, run_clean, n_iter: int = 2, band_hz: float = 15.0):
        """Iterative learning of the hand path on the tremor-free run (the writer has learned the pen): hand path -=
        low-passed (ink - intended) (CALC on SIM).  run_clean(scn) -> sim2 Result."""
        sos = butter(2, band_hz, fs=1.0 / SIM_DT, output="sos")
        hist = []
        for it in range(n_iter):
            r = run_clean(self.scenario())
            ink = np.column_stack([np.interp(self.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - self.intended
            m = self.written.intended.pen_down
            hist.append(float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6))
            self.hand_path = self.hand_path - sosfiltfilt(sos, e, axis=0)
        self.adapted = True
        return hist


def metrics(case: WriterCase, r, ref_none=None, ref_clean=None) -> Dict:
    """Handwriting-study metrics (handwriting.metrics) on a sim2 result, plus device share, force and power."""
    R = Res(r)
    rows = MT.letter_rows(case.written, R, case.rec)
    s = MT.summary(rows)
    wd = MT.words(rows, case.text)

    class _S:
        pass
    sc = _S()
    sc.dt = SIM_DT
    sc.t = case.t
    sc.intended = case.intended
    out = {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"),
           "letters_read": s.get("recognition_accuracy"), "words_letters": wd["word_accuracy_letters"],
           "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
           "band_err_um": MT.band_error_um(R, sc), "aligned_err_um": MT.aligned_error_um(R, sc)}
    c = R.contact > 0.5
    out["contact_share"] = float(np.mean(c[R.t > 0.3]))
    out.update(power(r))
    if ref_none is not None:
        out.update(device_effect(r, ref_none))
    if ref_clean is not None:
        out["moved_um"] = moved(r, ref_clean)
    return out


def moved(r, ref) -> float:
    """RMS distance (um) between two runs' ink while both are in contact (false correction on tremor-free writing)."""
    n = min(len(r["t"]), len(ref["t"]))
    m = (r["contact"][:n] > 0.5) & (ref["contact"][:n] > 0.5)
    d = r.ink()[:n] - ref.ink()[:n]
    return float(np.sqrt(np.mean(np.sum(d[m] ** 2, axis=1))) * 1e6) if m.any() else float("nan")


def device_effect(r, ref) -> Dict:
    """Device share of the ink motion (handwriting.metrics.authorship: L(c) / (L(c) + L(h)), h = the same hand's ink
    without the device) and the change in grip force the writer feels (drive study's 'felt change')."""
    n = min(len(r["t"]), len(ref["t"]))
    m = (r["contact"][:n] > 0.5) & (ref["contact"][:n] > 0.5)
    h = ref.ink()[:n]
    cc = r.ink()[:n] - h
    dm = m[1:] & m[:-1]
    Lh = float(np.sum(np.hypot(*np.diff(h, axis=0).T)[dm]))
    Lc = float(np.sum(np.hypot(*np.diff(cc, axis=0).T)[dm]))
    out = {"device_share": Lc / max(Lc + Lh, 1e-12)}
    if "grip_ax" in r.idx and "grip_ax" in ref.idx:
        dg = np.hypot(r["grip_ax"][:n] - ref["grip_ax"][:n], r["grip_ay"][:n] - ref["grip_ay"][:n])
        out["felt_rms_N"] = float(np.sqrt(np.mean(dg[m] ** 2))) if m.any() else float("nan")
        out["felt_p95_N"] = float(np.percentile(dg[m], 95)) if m.any() else float("nan")
    return out


P_ELEC = 0.077        # W electronics (ASSUMPTION, Rev H; nose2 total-power convention)
E_LIFT = 0.017        # J per pen-lift cycle (CALC, nose2 axial_dof)


def power(r) -> Dict:
    """Mean electrical power (CALC on SIM): nose copper loss (sim2's coil model, incl. the contact-gated bias current
    that holds the refill spring's transverse ball load), wheel drive (copper k_P F^2 with k_P from the wheel parameters:
    4.30 W/N^2 for the lead's motor and gearing, 3.48 in study D; + positive mechanical power / 0.8), end-cap copper
    F^2 / Km^2, pen lift (17 mJ per cycle, nose2 / sim_params), electronics 0.077 W; battery 2.22 Wh usable."""
    t = r["t"]
    T = float(t[-1] - t[0]) if len(t) > 1 else 1.0
    m = t > 0.3
    P_nose = float(np.mean(r["Pcu"][m])) if "Pcu" in r.idx else 0.0
    P_wheel = 0.0
    if "wFmc" in r.idx:
        F = r["wFmc"]
        u = r["wu"]
        kP = float(r.info.get("wheel_kP", 3.48))
        P_wheel = float(np.mean((kP * F ** 2 + np.maximum(F * u, 0.0) / 0.8)[m]))
    P_ec = 0.0
    if "ecx" in r.idx:
        rm_K = 0.7353
        P_ec = float(np.mean(((r["ecx"] ** 2 + r["ecy"] ** 2) / rm_K ** 2)[m]))
    n_lift = r.info.get("energy", {}).get("lift_cycles", 0)
    P_lift = n_lift * E_LIFT / T if T > 0 else 0.0
    tot = P_nose + P_wheel + P_ec + P_lift + P_ELEC
    return {"P_nose_W": P_nose, "P_wheel_W": P_wheel, "P_endcap_W": P_ec, "P_lift_W": P_lift, "P_total_W": tot,
            "battery_h": 2.22 / tot if tot > 0 else float("nan")}


# ================================================================================================ autowrite
class AutowriteCase:
    """nose2's autowrite scene in sim2: the hand sweeps the pen steadily along the line (skid on the paper, H1 hand),
    optionally with hand tremor; the pen draws a known text in the writer's style with the C1S nose inside its reach
    and lifts the ball between strokes (pen lift).  Plan: nose2.planner (reach = travel - 0.5 mm margin, 1.25 x the
    line speed; the pen falls back to 1.0 x when the line does not fit: DEC-039's per-line speed rule)."""

    def __init__(self, w: int, h_mm: float = 2.5, text: str = WV.ET_SENTENCE, version: str = "v1",
                 reach: float = 5.5e-3, speeds=(1.25, 1.0), N0: float = 1.0):
        from nose2 import planner as PN
        self.w = w
        self.text = text
        self.version = version
        wr = WV.writer(w, version, x_height_mm=h_mm) if version == "v1" else WV.writer(w, version)
        if version == "v1":
            self.written = wr.write(text, dt=1e-3, seed=2000 + w)
        else:
            self.written = wr.write(text, dt=1e-3, seed=2000 + w, size_scale=h_mm / (wr.style.x_height_mm * wr.kp.size_scale))
        self.rec = MT.recognizer_for(self.written)
        self.tp = PN.target_from_written(self.written)
        pp = PN.PlanParams()
        self.plan = None
        for sp in speeds:
            v_h = PN.line_speed(self.tp, pp) * sp
            pl = PN.plan(self.tp, v_h, reach, pp)
            if pl.ok:
                self.plan, self.v_h, self.speed = pl, v_h, sp
                break
        self.ok = self.plan is not None
        self.N0 = N0

    def scenario(self, f0: float = 0.0, amp: float = 0.0, seed: int = 200):
        pl = self.plan
        t = np.arange(0.0, pl.t[-1], SIM_DT)
        hx = np.interp(t, pl.t, pl.hand[:, 0])
        hy = np.interp(t, pl.t, pl.hand[:, 1])
        hand = np.column_stack([hx, hy])
        trem = HWR.tremor_path(t, f0, amp, seed, self.w) if amp > 0 else np.zeros_like(hand)
        itx = sg.Intended(t, hand, np.ones(len(t), bool), np.zeros(len(t)), [])
        sc = PS._assemble(itx, trem, self.N0, 50.0, meta={"kind": "autowrite", "writer": self.w})
        sc.intended = hand.copy()
        sc.psi_disp = np.zeros(len(t))
        sc.tremor_obj = None
        self.t = t
        return sc

    def task(self) -> Dict:
        return {"plan": self.plan, "v_h": self.v_h}

    def retimed(self, r):
        """Letter windows from the executed plan progress (nose2/autowrite.retimed)."""
        import copy
        wr = copy.copy(self.written)
        wr.letters = [copy.copy(L) for L in self.written.letters]
        tau = np.asarray(r.info.get("aw_tau"))
        tick_t = np.arange(len(tau)) * 0.5e-3
        path = self.plan.path
        i_tau = np.interp(tau, self.plan.t, self.plan.idx)
        for L in wr.letters:
            idx = np.flatnonzero(path.letter == L.glyph_index)
            k0 = int(np.searchsorted(i_tau, idx[0] - 0.5))
            k1 = int(np.searchsorted(i_tau, idx[-1] + 0.5))
            L.t0 = float(tick_t[min(k0, len(i_tau) - 1)])
            L.t1 = float(tick_t[min(k1, len(i_tau) - 1)])
        return wr

    def metrics(self, r) -> Dict:
        from nose2 import autowrite as AW
        wr = self.retimed(r)
        R = Res(r)
        rows = MT.letter_rows(wr, R, self.rec, pad=0.0)
        s = MT.summary(rows)
        wd = MT.words(rows, self.text)
        tgt = AW.target_read(self.written, self.rec)
        t_text = (wr.letters[0].t0, wr.letters[-1].t1)
        dur = t_text[1] - t_text[0]
        out = {"ink_err_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
               "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
               "target_letters_read": tgt["letters"], "target_words_app": tgt["words_app"],
               "letters_per_s": len(wr.letters) / dur if dur > 0 else float("nan"), "v_h_mm_s": self.v_h * 1e3,
               "speed_factor": self.speed}
        out.update(power(r))
        q = np.hypot(r["qpx"], r["qpy"]) if "qpx" in r.idx else np.zeros(len(r["t"]))
        mt = (r["t"] >= t_text[0]) & (r["t"] <= t_text[1])
        out["q_max_mm"] = float(q[mt].max() * 1e3) if mt.any() else float("nan")
        out["at_reach"] = float(np.mean(q[mt] >= 0.95 * 6.0e-3)) if mt.any() else float("nan")
        return out
