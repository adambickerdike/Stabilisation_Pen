r"""Essential tremor in sim2 with the Rev J pen: the writer set-up, the controllers and one case (SIMULATION).

Writer set-up (per writer and pen model): the v2 writer (or v1) writes the text at the simulation step; the hand path
is adapted to the pen by iterative learning on the tremor-free run (time-advanced by the measured lag, 10 Hz, 3 passes;
the writer has learned the pen, as HW1's adapted writer); the adapted writer's tremor-free ink with the devices neutral
is the reference ("clean ink").  sim2's pen-paper dynamics (stick-slip, touchdown, rotation in the grip) leave about
0.2 mm rms between the clean ink and the intended letters after adaptation (SIM); the ink error is therefore measured
against the clean ink letters (sim2/H1's convention, DEC-040), and letters and words are read on the ink itself.

Controllers (firmware.FWConfig):
  none            the Rev J pen with the nose held centred and the wheel retracted
  nose            nose + the guarded tracker (AKF re-tuned for Rev H, frequency-runaway guard), wheel retracted
  nose_noguard    the same without the guard (diagnostic)
  nose_wheel      nose as above + the heel wheel in its tremor mode (steer + brake), coordinated through the tracker:
                  the wheel damps and constrains, the tracker sees the resulting handle motion, the nose cancels the rest
  nose_wheel_ec   + the reaction-mass end-cap feed-forward (pen with the end-cap)
  oracle          the nose with perfect knowledge of the handle's tremor (the mechanism's limit)
  rl              the nose with the RL policy on the tracker's features (rl.py)
Metrics: tasks.metrics (ink error to the clean-ink letters, letters and words read by the app, band error, device share,
felt grip force, power) and, on tremor-free writing, the false correction (ink moved against the device-off run).
"""
from __future__ import annotations

import copy
import math
import os
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import BUILD, ROOT  # noqa: F401
from . import revj as RJ
from . import stepper as ST
from . import tasks as TK
from . import writers as WV
from .akf_online import DetParams, GuardParams, frozen_det, frozen_guard, frozen_tracker
from .firmware import FWConfig
from handwriting import metrics as MT  # noqa: E402

ET_TEXT = "return library"             # the first two words of the handwriting study's sentence (compute; stated)
DT = 50e-6                              # test-grid step (sim2 section 5.3: 0.66 um from 12.5 us); 25 us checked
SIM_DT = TK.SIM_DT


def akf_params():
    from sim2 import sensors as SS
    return SS.revh_params()


def controller(name: str, guard: Optional[GuardParams] = None, policy=None, seed: int = 0,
               det: Optional[DetParams] = None) -> FWConfig:
    g = guard or frozen_guard()
    dp = det or frozen_det()
    akf = akf_params()
    return replace(_controller(name, g, akf, policy, seed), det=dp)


def _controller(name, g, akf, policy, seed) -> FWConfig:
    if name == "none":
        return FWConfig(seed=seed)
    if name == "nose":                # the frozen default tracker (results/sim2j/rules.json)
        return FWConfig(nose="tremor", akf=akf, guard=g, tracker=frozen_tracker(), seed=seed)
    if name == "nose_guarded":
        return FWConfig(nose="tremor", akf=akf, guard=g, tracker="guarded", seed=seed)
    if name == "nose_gl":             # ai2's gated listening tracker, fallback the Rev H tracker as built (DEC-042)
        return FWConfig(nose="tremor", akf=akf, guard=g, tracker="gl", seed=seed)
    if name == "nose_glg":            # gated listening with the guarded tracker as the fallback
        return FWConfig(nose="tremor", akf=akf, guard=g, tracker="glg", seed=seed)
    if name == "nose_noguard":
        return FWConfig(nose="tremor", akf=akf, guard=replace(g, on=False), seed=seed)
    if name == "nose_wheel":
        return FWConfig(nose="tremor", wheel="tremor", akf=akf, guard=g, tracker=frozen_tracker(), seed=seed)
    if name == "wheel_only":
        return FWConfig(wheel="tremor", akf=akf, guard=g, seed=seed)
    if name == "nose_freewheel":
        return FWConfig(nose="tremor", wheel="free", akf=akf, guard=g, tracker=frozen_tracker(), seed=seed)
    if name == "nose_wheel_ec":
        return FWConfig(nose="tremor", wheel="tremor", endcap="ff", akf=akf, guard=g, tracker=frozen_tracker(), seed=seed)
    if name == "nose_ec":
        return FWConfig(nose="tremor", endcap="ff", akf=akf, guard=g, tracker=frozen_tracker(), seed=seed)
    if name == "oracle":
        return FWConfig(nose="oracle", seed=seed)
    if name == "rl":
        return FWConfig(nose="tremor", akf=akf, guard=g, tracker=frozen_tracker(), policy=policy, seed=seed)
    raise KeyError(name)


PEN_OF = {"nose_wheel_ec": "endcap", "nose_ec": "endcap"}


class PenModels:
    """One sim2 model per pen variant (built once): 'base' (Rev J with the heel drive) and 'endcap'."""

    def __init__(self, hand_model: str = "h1", dt: float = DT, **cfg_kw):
        self.kw = dict(hand_model=hand_model, dt=dt, **cfg_kw)
        self.pms = {}

    def get(self, pen: str = "base"):
        if pen not in self.pms:
            self.pms[pen] = RJ.build(RJ.config(heel=True, endcap=(pen == "endcap"), **self.kw))
        return self.pms[pen]


def clean_letters(written, r) -> List[List[np.ndarray]]:
    """Per letter: the clean run's in-contact ink during the letter window, split at contact changes."""
    t = r["t"]
    ink = r.ink()
    con = r["contact"] > 0.5
    out = []
    for L in written.letters:
        m = (t >= L.t0) & (t <= L.t1)
        idx = np.flatnonzero(m)
        polys = []
        if len(idx):
            c = con[idx]
            d = np.diff(np.r_[0, c.astype(np.int8), 0])
            A, B = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
            for a, b in zip(A, B):
                if b - a >= 3:
                    polys.append(ink[idx[a]:idx[b - 1] + 1])
        if not polys:
            polys = [np.asarray(p) for p in L.polylines]
        out.append(polys)
    return out


ET_PRE_S = 4.0          # s the pen rests on the paper before writing (tremor detectors need 2-4 s of signal; a
                        # pen picked up and placed before writing has that time) - ASSUMPTION, stated with the results


class WriterSetup:
    def __init__(self, w: int, pens: PenModels, version: str = "v2", text: str = ET_TEXT, pen: str = "base",
                 n_adapt: int = 3, log=None, pre_s: float = ET_PRE_S, adapt_ctl: str = "none"):
        """adapt_ctl: the controller the writer learns the pen with and whose tremor-free ink is the reference ('none':
        devices off; 'wheel_only': the heel wheel in its tremor mode, for the writer who has learned the wheel)."""
        self.adapt_ctl = adapt_ctl
        self.w, self.version, self.text, self.pen = w, version, text, pen
        self.pre_s = pre_s
        self.pm = pens.get(pen)
        self.case = TK.WriterCase(w, version=version, text=text, pre_s=pre_s)
        t0 = time.time()
        cache = self._cache_path(n_adapt)
        if cache and os.path.exists(cache):
            z = np.load(cache)
            self.case.hand_path = z["hand_path"]
            self.adapt_hist = [float(v) for v in z["adapt_hist"]]
        else:
            self.adapt_hist = self._adapt(n_adapt)
            if cache:
                np.savez(cache, hand_path=self.case.hand_path, adapt_hist=np.array(self.adapt_hist))
        self.clean = ST.run(self.pm, self.case.scenario(), controller(self.adapt_ctl))
        self.ref_polys = clean_letters(self.case.written, self.clean)
        rows = MT.letter_rows(self.case.written, TK.Res(self.clean), self.case.rec)
        s = MT.summary(rows)
        wd = MT.words(rows, text)
        self.clean_floor = {"ink_to_intended_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
                            "words_app": wd.get("word_accuracy_app"), "adapt_hist_um": self.adapt_hist}
        self.setup_s = time.time() - t0
        self.clean_runs = {}
        if log:
            log(f"[setup] writer {w} {version} pen {pen}: adaptation {['%.0f' % h for h in self.adapt_hist]} um, "
                f"clean floor {self.clean_floor['ink_to_intended_um']:.0f} um, {self.setup_s:.0f} s")

    def _cache_path(self, n_adapt: int) -> Optional[str]:
        """The adapted hand path depends on the writer, the text, the pen model and the step: cached per key."""
        import hashlib
        pm = self.pm
        key = f"{self.w}|{self.version}|{self.text}|{self.pen}|{pm.cfg.label}|{pm.m.opt.timestep}|{n_adapt}|{self.pre_s}|" \
              f"{'' if self.adapt_ctl == 'none' else self.adapt_ctl}|" \
              f"{(pm.info.get('revj') or {}).get('lead')}|{pm.cfg.hand}|{pm.cfg.hand_model}|{pm.cfg.contact}|{pm.cfg.refill}"
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        d = os.path.join(BUILD, "setups")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"setup_w{self.w}_{self.version}_{self.pen}_{h}.npz")

    def _adapt(self, n_iter):
        case = self.case
        m = case.written.intended.pen_down
        sos = butter(2, 10.0, fs=1.0 / SIM_DT, output="sos")
        hist = []
        v = np.gradient(case.intended, SIM_DT, axis=0)
        for it in range(n_iter):
            r = ST.run(self.pm, case.scenario(), controller(self.adapt_ctl))
            ink = np.column_stack([np.interp(case.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - case.intended
            hist.append(float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6))
            lag = max(0.0, float(-np.sum(e[m] * v[m]) / max(np.sum(v[m] * v[m]), 1e-30)))
            k = int(round(lag / SIM_DT))
            ea = np.vstack([e[k:], np.repeat(e[-1:], k, 0)]) if k > 0 else e
            case.hand_path = case.hand_path - 0.9 * sosfiltfilt(sos, ea, axis=0)
        return hist

    def clean_ref(self, seed: int):
        """The device-off tremor-free run with the case's seed (the servo's Hall noise enters the physics, and sim2's
        stick-slip contact amplifies any difference: the false correction is measured against the same noise)."""
        if seed not in self.clean_runs:
            self.clean_runs[seed] = ST.run(self.pm, self.case.scenario(),
                                           replace(controller(self.adapt_ctl, seed=seed * 7 + self.w), record_streams=True),
                                           mu=mu_for(self.w, seed, 0.0, 0.0), seed=seed)
        return self.clean_runs[seed]

    def metrics(self, r, ref_none=None, clean_ref=None) -> Dict:
        R = TK.Res(r)
        rows = MT.letter_rows(self.case.written, R, self.case.rec, target_polys=self.ref_polys)
        s = MT.summary(rows)
        wd = MT.words(rows, self.text)
        out = {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"),
               "letters_read": s.get("recognition_accuracy"), "words_app": wd.get("word_accuracy_app"),
               "words_letters": wd["word_accuracy_letters"], "recognised": " ".join(wd["recognised"])}
        # the error to the intended letters too (handwriting study's reference; includes the ~0.2 mm floor)
        rows_i = MT.letter_rows(self.case.written, R, self.case.rec)
        out["ink_err_intended_um"] = MT.summary(rows_i).get("path_rms_um")
        out["moved_vs_clean_um"] = TK.moved(r, clean_ref if clean_ref is not None else self.clean)
        out.update(TK.power(r))
        if ref_none is not None:
            out.update(TK.device_effect(r, ref_none))
        out["guard_events"] = len(r.info.get("guard_events", []))
        if "f_est" in r.idx:
            m = r["t"] > 1.0
            out["f_est_median"] = float(np.median(r["f_est"][m]))
            out["f_at_bound_share"] = float(np.mean(r["f_est"][m] > 14.4))
        if "wN" in r.idx:
            c = r["contact"] > 0.5
            F = np.hypot(r["wFx"], r["wFy"])
            out["wheel_F_rms_N"] = float(np.sqrt(np.mean(F[c] ** 2))) if c.any() else 0.0
            out["wheel_F_p95_N"] = float(np.percentile(F[c], 95)) if c.any() else 0.0
            out["wheel_slide_share"] = float(np.mean(r["wslide"][c] > 0.5)) if c.any() else 0.0
        return out


def mu_for(w: int, seed: int, f0: float, amp: float) -> float:
    """True tyre-paper friction per case, uniform 0.6-1.2 (drive study's test convention), seeded by the case."""
    rng = np.random.default_rng(880_000 + 1000 * w + seed + int(round(10 * f0)) * 7 + int(round(amp * 1e4)) * 13)
    return float(rng.uniform(0.6, 1.2))


def oracle_table(r_none, r_clean, n_ticks: int, gd: float, Ts: float = 0.5e-3) -> np.ndarray:
    """d(t + preview) at the ticks: handle tip (tremor, device off) - handle tip (clean, device off)."""
    t = r_none["t"]
    n = min(len(t), len(r_clean["t"]))
    d = r_none.ball()[:n] - r_clean.ball()[:n]
    tt = np.arange(n_ticks) * Ts
    return np.column_stack([np.interp(tt, t[:n], d[:, 0]), np.interp(tt, t[:n], d[:, 1])])


def run_case(su: WriterSetup, ctl_name: str, f0: float, amp: float, seed: int, ref_none=None, policy=None,
             guard: Optional[GuardParams] = None, keep: bool = False, det: Optional[DetParams] = None,
             record: bool = False) -> Dict:
    case = su.case
    tr = case.tremor(f0, amp, seed) if amp > 0 else None
    scn = case.scenario(tremor=tr)
    fw = controller(ctl_name, guard=guard, policy=policy, seed=seed * 7 + su.w, det=det)
    if record:
        fw = replace(fw, record_streams=True)
    task = {}
    if ctl_name == "oracle":
        if ref_none is None:
            raise ValueError("oracle needs the device-off run")
        gd = 2 * su.pm.cfg.nose.servo_zeta / (2 * math.pi * su.pm.cfg.nose.servo_hz) + 0.25e-3
        task["oracle_d"] = oracle_table(ref_none, su.clean, int(len(case.t) * SIM_DT / 0.5e-3) + 10, gd)
    mu = mu_for(su.w, seed, f0, amp)
    t0 = time.time()
    r = ST.run(su.pm, scn, fw, task, mu=mu, seed=seed)
    el = time.time() - t0
    m = su.metrics(r, ref_none=ref_none, clean_ref=su.clean_ref(seed) if amp <= 0 else None)
    m.update({"w": su.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "ctl": ctl_name, "mu": mu, "wall_s": el,
              "writer": su.version, "pen": su.pen})
    if keep:
        m["_r"] = r
    return m


# ------------------------------------------------------------------------------------------------ the 'arm' hand model
_ARM_CAL = {}


def arm_tremor(pm, scn, f0: float, amp: float, seed: int):
    """ET tremor as torques at the forearm and wrist of sim2's articulated 'arm' hand (sim2.tremor ET profile: channel
    shares and phases, frequency and amplitude wander), calibrated so that the lifted pen tip moves amp peak at f0
    (sim2.tremor.calibrate on the linearised arm, CALC)."""
    from sim2 import tremor as TR
    p = TR.profile("ET", f0=f0, amp_tip=amp)
    key = (id(pm), round(f0, 3), round(amp, 6))
    if key not in _ARM_CAL:
        _ARM_CAL[key] = TR.calibrate(pm, p, f0)
    dt = float(pm.m.opt.timestep)
    n = int(round(float(scn.t[-1]) / dt)) + 4
    t = np.arange(n) * dt
    return TR.torques(t, p, _ARM_CAL[key]["A0"], np.random.default_rng(10_000 + seed))


def run_case_arm(su: WriterSetup, ctl_name: str, f0: float, amp: float, seed: int, ref_none=None, keep: bool = False,
                 record: bool = False) -> Dict:
    """run_case for the 'arm' hand model: the tremor enters as joint torques, the hand path carries no tremor."""
    case = su.case
    scn = case.scenario()
    tq = arm_tremor(su.pm, scn, f0, amp, seed) if amp > 0 else None
    fw = controller(ctl_name, seed=seed * 7 + su.w)
    if record:
        fw = replace(fw, record_streams=True)
    task = {}
    if ctl_name == "oracle":
        gd = 2 * su.pm.cfg.nose.servo_zeta / (2 * math.pi * su.pm.cfg.nose.servo_hz) + 0.25e-3
        task["oracle_d"] = oracle_table(ref_none, su.clean, int(len(case.t) * SIM_DT / 0.5e-3) + 10, gd)
    mu = mu_for(su.w, seed, f0, amp)
    t0 = time.time()
    r = ST.run(su.pm, scn, fw, task, mu=mu, seed=seed, arm_tremor=tq)
    m = su.metrics(r, ref_none=ref_none, clean_ref=su.clean_ref(seed) if amp <= 0 else None)
    m.update({"w": su.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "ctl": ctl_name, "mu": mu, "wall_s": time.time() - t0,
              "writer": su.version, "pen": su.pen, "hand_model": "arm"})
    if keep:
        m["_r"] = r
    return m
