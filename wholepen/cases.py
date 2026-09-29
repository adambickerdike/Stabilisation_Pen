r"""Tremor classes as simulator inputs, pen variants, writer set-ups, one case and its metrics (SIMULATION inputs; the
writers and most tremor are synthetic; the recorded PD waveform is real data; nothing measured on this pen).

Tremor classes (targets.py; peak amplitude at the pen tip without any device, while writing):
  ET mild / moderate / severe          1 / 3 / 8 mm at 6 and 9 Hz (kinetic: present while writing)
  PD action mild / moderate / severe   1 / 3 / 8 mm at 5 Hz (present while writing)
  PD re-emergent (severe)              8 mm at 5 Hz, suppressed while the pen moves and re-emerging over 3 s in pauses
                                       and slow writing (sim2.tremor's gate; LIT PDT-09 latency)
  PD recorded                          the tremor line of a recorded NewHandPD patient (P21 meander, 5.37 Hz, its own
                                       amplitude and frequency wander), scaled to the class amplitude (H1 hand only)
H1 hand: the tremor is the project's elliptical hand-path tremor (stabpen.signals, P1 convention) with its hand-path
peak scaled so that the no-device tip moves the class amplitude (tip/hand ratio of the linear model at f0, CALC; the
achieved no-device tip tremor is measured and reported, SIM).  Arm hand: sim2.tremor's torque profiles at the forearm
and wrist, calibrated to the class amplitude at the lifted tip (sim2.tremor.calibrate, CALC).
Pen variants: 'base' (Rev J, heel drive, nose), 'endcap' (+ 30 g reaction-mass end-cap, study K), 'gt*' (+ a CMG tail
module of designs.py), 'tmd*' (+ tuned mass), 'collar*' (the pen hanging in a pivot collar).
Writers: v2 writers (sim2j.writers); the text "return library books by friday" (5 words) after a 4 s rest on the
paper (sim2j's ET protocol); the writer has learned each pen (iterative learning on its tremor-free run, 3 passes).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import BUILD, ROOT, SCRATCH  # noqa: F401
from . import control as C
from . import devices as DV
from . import lin as L
from . import stepper as WS
from sim2j import et as ET  # noqa: E402
from sim2j import revj as RJ  # noqa: E402
from sim2j import tasks as TK  # noqa: E402
from sim2j import writers as WV  # noqa: E402
from handwriting import metrics as MT  # noqa: E402
from handwriting import writers as HWR  # noqa: E402

SIM_DT = TK.SIM_DT
DT = 50e-6                               # physics step of the grid (sim2 5.3: 0.66 um against 12.5 us); 25 us checked
TEXT = WV.ET_SENTENCE                    # "return library books by friday": 5 words per writer
PRE_S = 4.0                              # s at rest on the paper before writing (sim2j ET protocol, ASSUMPTION)


# ------------------------------------------------------------------------------------------------ pen variants
@dataclass
class PenVariant:
    name: str
    endcap: bool = False
    gt: Optional[Dict] = None            # CMGTail kwargs
    tmd: Optional[Dict] = None           # devices.tuned_mass kwargs
    collar: Optional[Dict] = None        # devices.Collar kwargs
    grip_scale: float = 1.0              # H1 grip stiffness and damping scale (sim2 HandH1.grip_scale; HAP-26 range
                                         # 228-1043 N/m around 575 N/m: 0.5-2 x)
    r_rot: float = 0.5                   # H1 grip split (ASSUMPTION, EXP-I01)
    label: str = ""

    def build(self, hand_model: str = "h1", r_rot: Optional[float] = None, dt: float = DT, arm=None):
        from sim2 import params as P2
        r_rot = self.r_rot if r_rot is None else r_rot
        hand = P2.HandH1(r_rot=r_rot, grip_scale=self.grip_scale) if hand_model == "h1" else None
        cfg = RJ.config(hand_model=hand_model, heel=True, endcap=self.endcap, r_rot=r_rot, dt=dt, arm=arm, hand=hand,
                        label=f"Rev J {self.name}")
        if self.gt is not None:
            cfg.plugins.append(DV.CMGTail(**self.gt))
        if self.tmd is not None:
            cfg.plugins.append(DV.tuned_mass(**self.tmd))
        col = DV.Collar(**self.collar) if self.collar is not None else None
        return DV.build(cfg, collar=col)


def base_wp(pv: PenVariant, tmd_mode: str = "passive") -> C.WPConfig:
    """The device state the writer learns the pen with (and the tremor-free reference): a collar's servo holds the pen
    centred against the writing force, a tuned mass is on its flexures, a CMG's gimbals are held (inert)."""
    wp = C.WPConfig()
    if pv.tmd is not None:
        wp = replace(wp, tmd=tmd_mode)
    return wp


# ------------------------------------------------------------------------------------------------ tremor inputs
TREMOR_KINDS = ("ET", "PD_action", "PD_reemergent", "PD_recorded")


def tip_per_hand(pen_lin: Dict, f0: float, r_rot: float = 0.5) -> float:
    """No-device tip peak per unit hand-path peak of the elliptical tremor (lin.py, CALC)."""
    mdl = L.Model(hand=L.HandP(r_rot=r_rot), pen=dict(pen_lin), c_paper=3.0)
    return L.amp(L.frf_tremor(mdl, f0, 1.0))


_REC = None


def recorded_pd(t: np.ndarray, seed: int) -> np.ndarray:
    """Normalised 2-D tremor waveform from a recorded NewHandPD patient (realdata.pd_waveform): unit peak of the
    major axis at the recording's mean envelope; a random start inside the recording per seed (REAL DATA, CALC)."""
    global _REC
    if _REC is None:
        from . import realdata as RD
        _REC = RD.pd_waveform()
    w = _REC["xy"]
    fs = _REC["fs"]
    n = len(t)
    dt = float(t[1] - t[0])
    tw = np.arange(len(w)) / fs
    rng = np.random.default_rng(55_000 + seed)
    span = tw[-1]
    t0 = float(rng.uniform(0, max(span - 1.0, 0.0)))
    tt = (t0 + t) % span
    out = np.column_stack([np.interp(tt, tw, w[:, 0]), np.interp(tt, tw, w[:, 1])])
    ramp = np.clip(t / 0.3, 0, 1)
    return out * ramp[:, None]


# empirical input corrections (measured no-device tip tremor of the BASE pen on the tuning writers / target), set by the
# 'calibrate' stage and frozen in results/wholepen/rules.json before any test run; 1.0 until then
CAL: Dict[str, float] = {}


def cal_key(hand_model: str, kind: str, f0: float) -> str:
    return f"{hand_model}|{kind}|{f0:g}"


_REAL: Dict = {}


def real_draw(case: TK.WriterCase, kind: str, amp_tip: float, seed: int):
    """A real recorded tremor waveform at the pen tip from study R's library (realdata.library, test split; PD: UCI
    spirals, ET: Zenodo hand recordings scaled to the tip classes), scaled to amp_tip (REAL DATA, CALC)."""
    key = (case.w, len(case.t), kind, round(amp_tip * 1e7), seed)
    if key not in _REAL:
        from realdata import library as RL
        a = amp_tip * 1e3
        cls = "severe" if a > 0.51 else ("moderate" if a > 0.165 else "mild")
        _REAL[key] = RL.tremor(cls, seed=seed, kind="ET" if kind == "REAL_ET" else "PD", split="test", t=case.t, amp_mm=a)
    return _REAL[key]


def h1_tremor(case: TK.WriterCase, kind: str, f0: float, amp_tip: float, seed: int, pen_lin: Dict = None,
              r_rot: float = 0.5) -> np.ndarray:
    """Hand-path tremor (n, 2) for the H1 hand.  The SAME hand tremor for every pen: its hand-path peak is scaled so
    that the Rev J pen WITHOUT devices (lin.PEN) moves amp_tip at its tip (linear model, CALC), times the empirical
    correction CAL (SIM on the tuning writers); a heavier pen then shows what its mass does to the same tremor."""
    if kind.startswith("REAL"):
        dr = real_draw(case, kind, amp_tip, seed)
        return dr.d / max(tip_per_hand(dict(L.PEN), float(dr.meta["f0"]), r_rot), 1e-6)
    k = tip_per_hand(dict(L.PEN), f0, r_rot)
    A_hand = amp_tip / max(k, 1e-6) * CAL.get(cal_key("h1", kind, f0), 1.0)
    if kind == "PD_recorded":
        return recorded_pd(case.t, seed) * A_hand
    tr = case.tremor(f0, A_hand, seed)
    if kind == "PD_reemergent":
        from sim2 import tremor as TR
        it = case.written.intended
        v = np.hypot(*np.gradient(it.xy, SIM_DT, axis=0).T) * it.pen_down
        p = TR.profile("PD_rest", f0=f0)
        g = TR.gate(case.t, v, p)
        tr = tr * g[:, None]
    return tr


_BASE_ARM_PM = None


def base_arm_pm():
    """The Rev J pen without devices in the articulated arm: the tremor torques are calibrated on it once and applied
    unchanged to every pen (the person's tremor does not depend on the pen)."""
    global _BASE_ARM_PM
    if _BASE_ARM_PM is None:
        _BASE_ARM_PM = PenVariant("base").build(hand_model="arm")
    return _BASE_ARM_PM


def arm_tremor(pm, scn, kind: str, f0: float, amp_tip: float, seed: int, case: TK.WriterCase):
    """Joint torques for the articulated arm (sim2.tremor profiles, calibrated on the device-free Rev J pen to the
    lifted-tip peak, times the empirical correction CAL)."""
    from sim2 import tremor as TR
    prof = {"ET": "ET", "PD_action": "PD_action", "PD_reemergent": "PD_rest", "PD_recorded": "PD_action"}[kind]
    amp_eff = amp_tip * CAL.get(cal_key("arm", kind, f0), 1.0)
    p = TR.profile(prof, f0=f0, amp_tip=amp_eff)
    key = (prof, round(f0, 3), round(amp_eff, 7))
    if key not in _ARM_CAL:
        _ARM_CAL[key] = TR.calibrate(base_arm_pm(), p, f0)
    dt = float(pm.m.opt.timestep)
    n = int(round(float(scn.t[-1]) / dt)) + 4
    t = np.arange(n) * dt
    speed = None
    if prof == "PD_rest":
        it = case.written.intended
        v = np.hypot(*np.gradient(it.xy, SIM_DT, axis=0).T) * it.pen_down
        speed = np.interp(t, case.t, v)
    return TR.torques(t, p, _ARM_CAL[key]["A0"], np.random.default_rng(10_000 + seed), speed=speed)


_ARM_CAL: Dict = {}


# ------------------------------------------------------------------------------------------------ writer set-up
class Setup(ET.WriterSetup):
    """sim2j's writer set-up on a whole-pen variant: adaptation and the clean reference run through this study's
    stepper with the variant's base device state."""

    def __init__(self, w: int, pv: PenVariant, pm, version: str = "v2", text: str = TEXT, n_adapt: int = 3, log=None,
                 pre_s: float = PRE_S, hand_model: str = "h1"):
        self.pv = pv
        self.hand_model = hand_model
        self._pm = pm

        class _Pens:
            def get(self_, pen):
                return pm
        self.wp0 = base_wp(pv)
        super().__init__(w, _Pens(), version=version, text=text, pen=pv.name, n_adapt=n_adapt, log=log, pre_s=pre_s,
                         adapt_ctl="none")
        self.pen_lin = self._pen_lin()
        if pv.collar is not None:
            _post_init_clean(self)

    def clean_ref(self, seed: int):
        if seed not in self.clean_runs:
            self.clean_runs[seed] = self._run(self.case.scenario(), replace(ET.controller("none", seed=seed * 7 + self.w),
                                                                            record_streams=False),
                                              mu=ET.mu_for(self.w, seed, 0.0, 0.0), seed=seed)
        return self.clean_runs[seed]

    def _pen_lin(self) -> Dict:
        return DV.pen_props(self.pm)

    def _run(self, scn, fw, wp=None, task=None, mu=0.9, seed=0, arm_tremor=None):
        return WS.run(self.pm, scn, fw, wp or self.wp0, task=task, mu=mu, seed=seed, arm_tremor=arm_tremor)

    def _cache_path(self, n_adapt: int) -> Optional[str]:
        pm = self.pm
        key = f"W|{self.w}|{self.version}|{self.text}|{self.pv}|{pm.m.opt.timestep}|{n_adapt}|{self.pre_s}|" \
              f"{pm.cfg.hand}|{pm.cfg.hand_model}|{pm.cfg.contact}|{pm.cfg.refill}|{pm.cfg.nose}|{self.wp0}"
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        d = os.path.join(BUILD, "setups")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"setup_w{self.w}_{self.pv.name}_{self.hand_model}_{h}.npz")

    def _adapt(self, n_iter):
        case = self.case
        m = case.written.intended.pen_down
        sos = butter(2, 10.0, fs=1.0 / SIM_DT, output="sos")
        hist = []
        v = np.gradient(case.intended, SIM_DT, axis=0)
        for it in range(n_iter):
            r = self._run(case.scenario(), ET.controller("none"))
            ink = np.column_stack([np.interp(case.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - case.intended
            hist.append(float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6))
            lag = max(0.0, float(-np.sum(e[m] * v[m]) / max(np.sum(v[m] * v[m]), 1e-30)))
            k = int(round(lag / SIM_DT))
            ea = np.vstack([e[k:], np.repeat(e[-1:], k, 0)]) if k > 0 else e
            case.hand_path = case.hand_path - 0.9 * sosfiltfilt(sos, ea, axis=0)
        return hist


def _post_init_clean(su: Setup):
    """Replace sim2j's clean run (its stepper does not know this study's devices) by this study's."""
    su.clean = su._run(su.case.scenario(), ET.controller("none"))
    su.ref_polys = ET.clean_letters(su.case.written, su.clean)
    rows = MT.letter_rows(su.case.written, TK.Res(su.clean), su.case.rec)
    s = MT.summary(rows)
    wd = MT.words(rows, su.text)
    su.clean_floor = {"ink_to_intended_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
                      "words_app": wd.get("word_accuracy_app"), "adapt_hist_um": su.adapt_hist}


# ------------------------------------------------------------------------------------------------ metrics
def tremor_amp_mm(r, ref, band=(2.5, 20.0), key: str = "ink", t0: float = PRE_S + 0.3) -> float:
    """Peak-equivalent tremor amplitude (mm) of r relative to ref in the tremor band while writing: sqrt(2 x the
    largest eigenvalue of the covariance of the band-passed difference), in-contact samples of both runs after t0."""
    n = min(len(r["t"]), len(ref["t"]))
    t = r["t"][:n]
    a = r.ink()[:n] if key == "ink" else r.ball()[:n]
    b = ref.ink()[:n] if key == "ink" else ref.ball()[:n]
    dd = a - b
    fs = 1.0 / float(t[1] - t[0])
    sos = butter(2, [band[0], min(band[1], 0.45 * fs)], btype="band", fs=fs, output="sos")
    db = sosfiltfilt(sos, dd, axis=0)
    m = (t > t0)
    if key == "ink":
        m &= (r["contact"][:n] > 0.5) & (ref["contact"][:n] > 0.5)
    if m.sum() < 50:
        return float("nan")
    X = db[m]
    C_ = X.T @ X / len(X)
    return float(math.sqrt(2.0 * max(np.linalg.eigvalsh(C_)[-1], 0.0)) * 1e3)


def coverage(r, ref, t0: float = PRE_S) -> float:
    """Share of the reference run's inked samples that are also inked in r (gating costs ink: 1 = nothing lost)."""
    n = min(len(r["t"]), len(ref["t"]))
    m = ref["t"][:n] > t0
    c_ref = (ref["contact"][:n] > 0.5) & m
    c = (r["contact"][:n] > 0.5) & c_ref
    return float(c.sum() / max(c_ref.sum(), 1))


def _close_gaps(c: np.ndarray, n_gap: int) -> np.ndarray:
    """Boolean contact with gaps shorter than n_gap samples filled (contact flicker is not a lifted stroke)."""
    c = np.asarray(c, bool).copy()
    if n_gap <= 0 or not c.any():
        return c
    edges = np.flatnonzero(np.diff(np.r_[0, c.astype(int), 0]))
    starts, ends = edges[0::2], edges[1::2]
    for e, s2 in zip(ends[:-1], starts[1:]):
        if s2 - e < n_gap:
            c[e:s2] = True
    return c


def _segments(c: np.ndarray, n_min: int = 1):
    edges = np.flatnonzero(np.diff(np.r_[0, np.asarray(c, bool).astype(int), 0]))
    return [(a, b) for a, b in zip(edges[0::2], edges[1::2]) if b - a >= n_min]


def strokes_from_trace(path: str, t0: float = PRE_S, gap_s: float = 0.04, miss_share: float = 0.5,
                       t_reposition: float = 0.2) -> Dict:
    """Coverage, missing strokes and completion time from a saved trace (SIM record at 250 Hz), with the writer's
    intended pen-down segments as the strokes (gaps shorter than 40 ms merged, strokes shorter than 40 ms dropped) and
    the run's contact with its flicker (gaps < 40 ms) closed.  Completion time: the lost ink re-traced afterwards at the
    writer's own mean inked speed plus 0.2 s per lost piece (ASSUMPTION), as in ink_completeness."""
    z = np.load(path)
    t = z["t"]
    n = min(len(t), len(z["it_t"]))
    t = t[:n]
    dt = float(t[1] - t[0])
    ng = max(1, int(round(gap_s / dt)))
    m = t > t0
    down = _close_gaps(z["it_down"][:n] > 0.5, ng) & m
    c = _close_gaps(z["contact"][:n] > 0.5, ng)
    xy = z["it_xy"][:n]
    step = np.r_[0.0, np.hypot(*np.diff(xy, axis=0).T)]
    segs = _segments(down, ng)
    miss = sum(1 for a, b in segs if float(np.mean(c[a:b])) < miss_share)
    lost = down & ~c
    lost_pieces = len(_segments(lost, ng))
    lost_mm = float(np.sum(step[lost])) * 1e3
    ink_mm = float(np.sum(step[down])) * 1e3
    v = ink_mm / max(float(np.sum(down)) * dt, 1e-9)
    T_task = float(t[-1] - t0)
    extra = lost_mm / max(v, 1e-9) + t_reposition * lost_pieces
    return {"coverage_intended": float(np.sum(down & c) / max(down.sum(), 1)), "n_strokes": len(segs), "missing_strokes": miss,
            "missing_stroke_rate": miss / max(len(segs), 1), "lost_pieces": lost_pieces, "ink_lost_mm": lost_mm,
            "task_time_s": T_task, "completion_extra_s": extra, "completion_time_ratio": (T_task + extra) / max(T_task, 1e-9)}


def ink_completeness(r, ref, t0: float = PRE_S, miss_share: float = 0.5, t_reposition: float = 0.2) -> Dict:
    """What an ink gate costs (the review's section 13: coverage, missing strokes and completion time must accompany
    the error).  Strokes are the reference run's (tremor-free, device off) contiguous pen-down segments after t0; a
    stroke is missing when less than half of it is inked in r.  ink_lost_mm: the reference ink path not laid.
    Completion time: the writer model does not wait for the pen (the task time is unchanged); if the pen re-traced the
    lost ink afterwards ('autowrite' completion, ASSUMPTION: at the writer's own mean inked speed plus 0.2 s to
    reposition per lost segment), the task would take autowrite_extra_s longer (SIM on the record, CALC for the time).
    NOTE: the reference's contact flickers (sub-40 ms gaps), which splits its strokes into hundreds of pieces, so
    missing_strokes, missing_stroke_rate, lost_segments, autowrite_extra_s and completion_time_ratio from this function
    overstate the loss (kept unchanged so every row of the campaign uses one definition); the reported stroke metrics
    come from strokes_from_trace (the writer's intended strokes, flicker merged).  coverage is unaffected."""
    n = min(len(r["t"]), len(ref["t"]))
    t = ref["t"][:n]
    m = t > t0
    c_ref = (ref["contact"][:n] > 0.5) & m
    c = (r["contact"][:n] > 0.5)
    ink = ref.ink()[:n]
    step = np.r_[0.0, np.hypot(*np.diff(ink, axis=0).T)]
    # segments of the reference
    edges = np.flatnonzero(np.diff(np.r_[0, c_ref.astype(int), 0]))
    segs = list(zip(edges[0::2], edges[1::2]))
    n_miss = 0
    n_part = 0
    lost_segments = 0
    for a, b in segs:
        share = float(np.mean(c[a:b])) if b > a else 1.0
        if share < miss_share:
            n_miss += 1
        elif share < 0.9:
            n_part += 1
        lost = c_ref[a:b] & ~c[a:b]
        if lost.any():
            lost_segments += int(np.sum(np.diff(np.r_[0, lost.astype(int)]) == 1))
    lost_mm = float(np.sum(step[c_ref & ~c])) * 1e3
    inked_mm = float(np.sum(step[c_ref])) * 1e3
    T_ink = float(np.sum(c_ref)) * float(t[1] - t[0])
    v_ink = inked_mm / max(T_ink, 1e-9)
    T_task = float(t[-1] - t0)
    extra = lost_mm / max(v_ink, 1e-9) + t_reposition * lost_segments
    return {"coverage": float(np.sum(c_ref & c) / max(c_ref.sum(), 1)), "n_strokes": len(segs),
            "missing_strokes": n_miss, "missing_stroke_rate": n_miss / max(len(segs), 1), "partial_strokes": n_part,
            "ink_lost_mm": lost_mm, "ink_ref_mm": inked_mm, "lost_segments": lost_segments,
            "task_time_s": T_task, "autowrite_extra_s": extra, "completion_time_ratio": (T_task + extra) / max(T_task, 1e-9)}


def device_power(r, pv: PenVariant, wp: C.WPConfig) -> Dict:
    """Electrical power of the whole-pen devices (CALC on SIM): designs.py's electrical models on the recorded
    mechanical quantities."""
    from . import designs as DS
    T = float(r["t"][-1] - r["t"][0]) if len(r["t"]) > 1 else 1.0
    e = r.info.get("w_energy", {})
    out = {}
    if pv.gt is not None:
        out.update(DS.cmg_power(pv.gt, e.get("cmg_mech_J", 0.0) / T, active=(wp.cmg != "off")))
    if pv.collar is not None:
        out["P_collar_W"] = DS.collar_power(e.get("col_cu_J", 0.0) / T, e.get("col_mech_J", 0.0) / T)
    if wp.sled != "off":
        out["P_sled_W"] = DS.drive_power_from_F2(e.get("sled_J", 0.0) / T, kind="sled")
    if wp.omni != "off":
        out["P_omni_W"] = DS.drive_power_from_F2(e.get("omni_J", 0.0) / T, kind="omni")
    if wp.gate:
        out["P_gate_W"] = TK.E_LIFT * e.get("gate_lift_cycles", 0) / T
    out["P_devices_W"] = float(sum(v for k, v in out.items() if k.startswith("P_")))
    return out


PAGE_ERR = {"measured": "deltapen_walk", "held": "deltapen_held", "ideal": "white"}


def run_case(su: Setup, fw_name: str, wp: C.WPConfig, kind: str, f0: float, amp_tip: float, seed: int,
             ref_none=None, keep: bool = False, oracle_nose: bool = False, nose_reach: Optional[float] = None,
             oracle_split: Optional[float] = None) -> Dict:
    """One case: this writer and pen, a tremor class, a firmware (sim2j controller name) and the device laws."""
    case = su.case
    arm = su.hand_model == "arm"
    if kind.startswith("REAL") and amp_tip > 0:
        f0 = float(real_draw(case, kind, amp_tip, seed).meta["f0"])      # the recording's own tremor frequency
    fw = replace(ET.controller(fw_name, seed=seed * 7 + su.w), page_error=PAGE_ERR[wp.page_err])
    if nose_reach is not None:
        fw = replace(fw, reach=nose_reach)
    task = {"f0": f0}
    if arm:
        scn = case.scenario()
        tq = arm_tremor(su.pm, scn, kind, f0, amp_tip, seed, case) if amp_tip > 0 else None
    else:
        tr = h1_tremor(case, kind, f0, amp_tip, seed) if amp_tip > 0 else None
        scn = case.scenario(tremor=tr)
        tq = None
    needs_oracle = fw_name == "oracle" or any(getattr(wp, k) == "oracle" for k in ("cmg", "collar", "sled", "omni"))
    if needs_oracle:
        if ref_none is None:
            raise ValueError("an oracle needs the device-off run")
        gd = 2 * su.pm.cfg.nose.servo_zeta / (2 * math.pi * su.pm.cfg.nose.servo_hz) + 0.25e-3
        nt = int(len(case.t) * SIM_DT / 0.5e-3) + 10
        task["oracle_d"] = ET.oracle_table(ref_none, su.clean, nt, gd)
        # the devices' oracle: the true no-device handle tremor, band-passed zero-phase to the tremor band (2.5-15 Hz)
        # so that slow differences between the two runs (writing drift) do not reach the devices
        od = ET.oracle_table(ref_none, su.clean, nt, 0.0)
        sos_o = butter(2, [2.5, 15.0], btype="band", fs=2000.0, output="sos")
        task["oracle_d_dev"] = sosfiltfilt(sos_o, od, axis=0)
        if oracle_split is not None:
            # both the nose and a device know the tremor perfectly: the nose takes this share, the device the rest
            task["oracle_d"] = task["oracle_d"] * oracle_split
            task["oracle_d_dev"] = task["oracle_d_dev"] * (1.0 - oracle_split)
    mu = ET.mu_for(su.w, seed, f0, amp_tip)
    t0 = time.time()
    r = WS.run(su.pm, scn, fw, wp, task=task, mu=mu, seed=seed, arm_tremor=tq)
    el = time.time() - t0
    m = su.metrics(r, ref_none=ref_none)
    m["tip_tremor_mm"] = tremor_amp_mm(r, su.clean, key="ink")
    m["handle_tremor_mm"] = tremor_amp_mm(r, su.clean, key="handle")
    m.update(ink_completeness(r, su.clean))
    m.update(device_power(r, su.pv, wp))
    if "w_act" in r.idx:
        m["detector_open_share"] = float(np.mean(r["w_act"][r["t"] > PRE_S]))
    gt = next((p for p in su.pm.plugins if isinstance(p, DV.CMGTail)), None)
    if gt is not None:
        dl = np.array([r[f"gt_d{p}"] for p in range(len(gt.pairs()))])
        m["gimbal_peak_rad"] = float(np.max(np.abs(dl))) if dl.size else 0.0
        tq_ = np.array([r[f"gt_tq{k}"] for k in range(gt.n_rotors())])
        m["gimbal_tq_p95_mNm"] = float(np.percentile(np.abs(tq_), 95) * 1e3) if tq_.size else 0.0
    if "w_piv1" in r.idx:
        m["pivot_peak_rad"] = float(np.max(np.hypot(r["w_piv1"], r["w_piv2"])))
    m.update({"w": su.w, "seed": seed, "f0": f0, "amp_mm": amp_tip * 1e3, "kind": kind, "fw": fw_name,
              "wp": asdict(wp), "pen": su.pv.name, "hand_model": su.hand_model, "mu": mu, "wall_s": el})
    if keep:
        m["_r"] = r
    return m
