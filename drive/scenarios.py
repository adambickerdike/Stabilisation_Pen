"""Tasks (a)-(e) of study D on model HW1-D, with the handwriting and board studies' writers and paths (SIMULATION).

(a) guided tracing / copying: handwriting.practice learners (dysgraphia-like, dyslexia-like) copy "a big dog dug a deep
    pit by the pond"; the target is the copybook letter anchored at the learner's touchdown (as HW1).
(b) Parkinson's "write big": board.control.loops (10 mm target loops; the writer's loops shrink 0.8 -> 0.6).
(c) reversed letter: template 'd', writer intends 'b' (board.control.letter_b_or_d); a writer set on 'b' (imposed
    path) and a relaxed writer led through the 'd' (lead-through).
(d) tremor: handwriting ET writers ("return library books by friday") with tremor (stabpen.signals.tremor) at
    4-10 Hz, 1-2 mm; a steered wheel holding the direction of the intended motion (from a causal low-pass of the pen's
    velocity), with or without along-path braking or active damping; a driven ball as an active damper; the Rev H
    nose with the AKF tracker (HW1) alone and combined.
(e) gross-scale autowrite: a relaxed writer holds the pen; the drive leads it along the letter path of the practice
    sentence and the nose (+/-3 mm, no gate) does the detail; the writer only makes the pen-up moves.
Every run uses a writer-specific normal-force profile (contact.force_profile; CON-01 statistics).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace, field, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ensure_paths
from . import contact as CO
from . import plant as DP

ensure_paths()
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import practice as PRc  # noqa: E402
from handwriting import writers as W  # noqa: E402
from aiguide.writer import Path as APath  # noqa: E402
from board import control as BC  # noqa: E402

SIM_DT = W.SIM_DT
TICK_DT = 5e-4


# ----------------------------------------------------------------------------- hardware of the concepts (design point)
@dataclass
class Hardware:
    """Plant parameters of the heel elements at the chosen design point (design_opt.py, CALC; ASSUMPTION where noted)."""
    P: float = 0.55                   # N preload (design_opt: 0.57)
    k_lat: float = 1500.0             # N/m tyre tangential stiffness (contact.Tyre ~2.4 N/mm; fork and paper in series)
    c_rr_wheel: float = 0.066         # rolling resistance / N (Persson, r_e 1.0 mm, 0.5 N; contact.Tyre)
    c_rr_ball: float = 0.05
    # steered and driven wheel: Faulhaber 0620 B + bevel 2:1, r_e 1.0 mm
    m_r_wheel_driven: float = 0.0038
    F_bd_wheel_driven: float = 0.024
    m_r_wheel_free: float = 0.0001    # a bare 2 mm wheel (brass; CALC ~0.1 g effective)
    F_bd_wheel_free: float = 0.002
    # driven ball d 2 mm: two Faulhaber 0620 B + bevel 1:1 on rollers r 0.40 mm (design_opt snapped build, CALC);
    # micro-omni rollers (ASSUMPTION scrub 0.03 N); smooth rollers 0.3 x preload (LIT AMF-117)
    m_r_ball: float = 0.0061
    F_bd_ball: float = 0.028
    scrub_ball: float = 0.03
    scrub_ball_smooth: float = 0.225
    # steering: 0620 B + 06/1 4:1, Hall angle sensing; servo 40 Hz (ASSUMPTION), rate 500 rad/s, acc 6e4 rad/s^2 (CALC)
    w_s: float = 2 * math.pi * 40.0
    rate_s: float = 500.0
    acc_s: float = 6.0e4
    F_cap: float = 0.5
    # traction estimate: the controller does not know the paper; it starts at 0.8 and the slip rule lowers it
    # (ASSUMPTION; EXP-D01 measures the spread over papers, EXP-D05 the slip rule)
    mu_hat0: float = 0.8
    k_safe: float = 0.8


HW = Hardware()


@dataclass
class Gains:
    """Control gains (defaults before tuning; tune.py replaces them from results/drive/rules.json)."""
    # holonomic heel drive: the board's law (ASSUMPTION values, board/params.py CONTROL) with the heel's cap
    K_partial: float = 100.0
    band: float = 1.0e-3
    K_full: float = 200.0
    D: float = 2.0
    lead: float = 0.10
    slew: float = 20.0
    # steered wheel path mode
    L_a: float = 1.0e-3
    plaw: int = 0
    k_st: float = 5.0
    L_t: float = 0.3e-3
    # lead-through / autowrite
    K_lead: float = 200.0
    F_lead: float = 0.25
    v_lead: float = 0.02
    Kv: float = 10.0
    # tremor
    f_lp: float = 3.0
    m_eff: float = 0.3
    b_wheel: float = 5.0
    b_ball: float = 5.0

    def as_dict(self):
        return asdict(self)


# ----------------------------------------------------------------------------- conditions
def drive_for(cond: str, g: Gains, mu: float, hw: Hardware = HW, board: Optional[PR.Board] = None) -> DP.Drive:
    """The Drive of a named condition (the nose settings are in nose_for)."""
    c = cond.replace("+nose", "")
    base = dict(P=hw.P, mu=mu, mu_hat0=hw.mu_hat0, k_safe=hw.k_safe, k_lat=hw.k_lat, F_cap=hw.F_cap, slew=g.slew, L_a=g.L_a, w_s=hw.w_s, rate_s=hw.rate_s,
                acc_s=hw.acc_s, f_lp=g.f_lp, plaw=g.plaw, k_st=g.k_st, L_t=g.L_t)
    if c in ("none", "nose_partial", "nose_full", "nose_nogate", "nose_akf", "nose_oracle", "writer_alone",
             "relaxed_nose"):
        return DP.Drive(mode="off")
    if c.startswith("board"):
        b = board or PR.board()
        kw = dict(mode="guide", kind="holo", grounded=True, F_cap=b.F_cap, D=b.D, lead=b.lead, slew=b.slew, b_tau=b.tau,
                  b_dead=int(round(b.dead / TICK_DT)), b_noise=b.noise, b_pull=b.normal_pull, over_d=b.over_d,
                  over_t=b.over_t, fade=b.fade, restore=b.restore)
        if c == "board_partial":
            return DP.Drive(sub=1, Kp=b.K_partial, band=b.band, **kw)
        if c == "board_full":
            return DP.Drive(sub=2, Kp=b.K_full, **kw)
        if c == "board_lead":            # the board study's lead-through: 0.20 N/mm + 0.3 N along the letter
            kw.update(mode="guide", sub=2, Kp=b.K_full, lead=0.30, lead_v_min=-1.0)
            return DP.Drive(**kw)
        raise KeyError(cond)
    ball = dict(kind="holo", m_r=hw.m_r_ball, F_bdc=hw.F_bd_ball, scrub=hw.scrub_ball, c_rr=hw.c_rr_ball, **base)
    if c.startswith("ballsmooth"):
        # smooth drive rollers: the orthogonal roller's axial slip 0.3 x its preload (LIT AMF-117; 0.75 N preload)
        ball["scrub"] = hw.scrub_ball_smooth
        c = c.replace("ballsmooth", "ball")
    if c == "ball_partial":
        return DP.Drive(mode="guide", sub=1, Kp=g.K_partial, band=g.band, D=g.D, **ball)
    if c == "ball_full":
        return DP.Drive(mode="guide", sub=2, Kp=g.K_full, D=g.D, lead=g.lead, **ball)
    if c == "ball_lead":
        return DP.Drive(mode="lead", Kl=g.K_lead, F_lead=g.F_lead, v_lead=g.v_lead, Kv=g.Kv, **ball)
    if c == "ball_damp":
        return DP.Drive(mode="damp", b_damp=g.b_ball, **ball)
    if c == "ball_brake":
        return DP.Drive(mode="brake", b_damp=g.b_ball, b_max=50.0, **ball)
    wfree = dict(kind="wheel", long="free", m_r=hw.m_r_wheel_free, F_bdc=hw.F_bd_wheel_free, c_rr=hw.c_rr_wheel, **base)
    wdrv = dict(kind="wheel", long="drive", m_r=hw.m_r_wheel_driven, F_bdc=hw.F_bd_wheel_driven, c_rr=hw.c_rr_wheel, **base)
    if c == "wheel_path":
        return DP.Drive(mode="path", **wfree)
    if c == "wheel_partial":
        return DP.Drive(mode="path", free_in_band=True, band=g.band, **wfree)
    if c == "sd_path":                 # steered + driven, transparent (no push) in guidance
        return DP.Drive(mode="path", lead=0.0, **wdrv)
    if c == "sd_full":                 # plus the board's small lead while the writer moves forward
        return DP.Drive(mode="path", lead=g.lead, **wdrv)
    if c == "sd_lead":
        return DP.Drive(mode="lead", F_lead=g.F_lead, v_lead=g.v_lead, Kv=g.Kv, **wdrv)
    if c == "wheel_tremor":
        return DP.Drive(mode="wheel_tremor", m_eff=g.m_eff, **wfree)
    if c == "wheel_tremor_vel":        # steering along the low-passed pen velocity (shows the lock-in problem)
        return DP.Drive(mode="wheel_tremor", tlaw=0, **wfree)
    if c == "wheel_tremor_brake":
        return DP.Drive(mode="wheel_tremor", **dict(wfree, long="brake", m_r=hw.m_r_wheel_driven,
                                                     F_bdc=hw.F_bd_wheel_driven), b_damp=g.b_wheel, b_max=50.0,
                        m_eff=g.m_eff)
    if c == "wheel_tremor_damp":
        return DP.Drive(mode="wheel_tremor", **dict(wdrv, long="damp"), b_damp=g.b_wheel, m_eff=g.m_eff)
    raise KeyError(cond)


def nose_for(cond: str, track=None) -> Dict:
    """Nose settings: 'central' (learn), 'partial' (0.5), 'full' (1.0), 'nogate', or the tremor tracker/oracle."""
    if cond in ("nose_partial",):
        return {"g": 0.5}
    if cond in ("nose_full",):
        return {"g": 1.0}
    if cond in ("nose_nogate", "relaxed_nose") or cond.endswith("+nose"):
        return {"g": 1.0, "nogate": True}
    return {}


def nose_ctl(nose: Dict, track) -> PL.Controls:
    if not nose or track is None:
        return PL.Controls(stroke_match=True)
    ctl = PL.Controls(tmpl=track.xy, tmpl_down=track.pen_down.astype(float), g_guide=nose["g"], stroke_match=True)
    if nose.get("nogate"):
        ctl.capture = 10e-3
        ctl.drop_d = 1.0
    return ctl


# ----------------------------------------------------------------------------- common metrics
def drive_metrics(r: DP.Result, r_ref: Optional[DP.Result] = None) -> Dict:
    c = r.contact > 0.5
    if not c.any():
        return {}
    F = np.hypot(r["FBx"], r["FBy"])          # everything the drive (or board) puts on the handle
    Ft = np.hypot(r["Ftx"], r["Fty"])
    out = {"F_rms_N": float(np.sqrt(np.mean(F[c] ** 2))), "F_p95_N": float(np.percentile(F[c], 95)),
           "F_max_N": float(F[c].max()), "slide_share": float(np.mean(r["slide"][c] > 0.5)),
           "slip_flag_share": float(np.mean(r["slip"][c] > 0.5)),
           "slip_events": int(np.sum(np.diff((r["slip"] > 0.5).astype(int)) == 1)),
           "yields": int(r["yield"][-1]), "Nd_mean_N": float(np.mean(r["Nd"][c])),
           "cap_mean_N": float(np.mean(r["capd"][c])), "mu_hat_mean": float(np.mean(r["muh"][c]))}
    if r_ref is not None:
        n = min(len(r.t), len(r_ref.t))
        dg = np.hypot(r["Fgx"][:n] - r_ref["Fgx"][:n], r["Fgy"][:n] - r_ref["Fgy"][:n])
        cc = c[:n]
        out["felt_rms_N"] = float(np.sqrt(np.mean(dg[cc] ** 2)))
        out["felt_p95_N"] = float(np.percentile(dg[cc], 95))
    # electrical power estimate (CALC): copper loss k_P Fm^2 + positive mechanical power Fm . W / 0.8
    Fm = np.hypot(r["Fmx"], r["Fmy"])
    if r.info.get("kind") == "wheel":
        Pm = np.maximum(r["Fmx"] * r["u"], 0.0)
        kP = 3.48      # W/N^2 copper loss: 0620 B, 2:1 through three meshes (eta 0.73), wheel r 1.0 mm (concepts.train, CALC)
    else:
        Pm = np.maximum(r["Fmx"] * r["Wx"] + r["Fmy"] * r["Wy"], 0.0)
        kP = 1.81      # W/N^2 per axis: 0620 B, 1:1 through two meshes (eta 0.81), rollers r 0.40 mm (concepts.train, CALC)
    out["P_drive_mean_W"] = float(np.mean((kP * Fm ** 2 + Pm / 0.8)[c])) if r.info.get("kind") in ("wheel", "holo") and not r.info.get("grounded") else 0.0
    return out


# ----------------------------------------------------------------------------- (a) guided practice
def practice_case(w: int, seed: int, profile: str):
    hand = PR.Hand.from_config()
    pen = PR.rev_h()
    su = PRc.setup(w, seed, profile, hand, pen)
    Nm = CO.writer_mean_force(10_000 * w + seed)
    Nt = CO.force_profile(su["scn"].t, su["scn"].down, Nm, 10_000 * w + seed)
    return {"su": su, "hand": hand, "pen": pen, "writing": PR.Writing(), "Nt": Nt, "N_mean": Nm, "w": w, "seed": seed,
            "profile": profile}


def run_practice(case: Dict, cond: str, g: Gains, mu: float, hand: Optional[PR.Hand] = None,
                 ref: Optional[DP.Result] = None, hw: Hardware = HW, keep: bool = False) -> Tuple[Dict, DP.Result]:
    su = case["su"]
    hand = hand or case["hand"]
    trk = su["track"]
    drv = drive_for(cond, g, mu, hw)
    ctl = nose_ctl(nose_for(cond), trk)
    r = DP.run(su["scn"], case["pen"], hand, case["writing"], ctl, drv, Ntot=case["Nt"], drive_tmpl=trk.xy,
               drive_tdown=trk.pen_down.astype(float), seed=su["seed"], rec_hz=2000.0)
    r_none = ref if ref is not None else r
    ev = PRc.evaluate(su, r, r_none)
    ev.pop("_rows", None)
    ev.update(drive_metrics(r, ref))
    ev["coverage"] = coverage(su, r)
    ev["cond"] = cond
    return ev, r


def coverage(su: Dict, r, thr: float = 0.3e-3) -> float:
    """Share of the target letters' length that has ink within thr (CALC on SIM): the distance-to-target error does
    not see strokes that were cut short; this does."""
    from scipy.spatial import cKDTree
    from aiguide.template import dense
    key = "_tmpl_dense"
    if key not in su:
        su[key] = np.vstack([dense(t.strokes, step=50e-6) for t in su["tl"]])
    ink = r.ink[r.contact > 0.5]
    if len(ink) < 2:
        return 0.0
    d, _ = cKDTree(ink).query(su[key])
    return float(np.mean(d < thr))


# ----------------------------------------------------------------------------- strokes -> scenario (tasks b, c)
def strokes_scenario(strokes_mm: List[np.ndarray], speed_mm_s: float, dt: float = SIM_DT, lift_mm: float = 1.5,
                     start_offset=(-1.0, 1.0), hold_s: float = 0.0, hold_factor: float = 1.0):
    """HW1 Scenario whose intended path draws the given strokes (mm) at a constant speed (minimum-jerk per stroke),
    with pen lifts between strokes.  hold_s / hold_factor stretch each pen-down period (a relaxed writer keeps the pen
    down while the drive leads: stroke time x hold_factor + hold_s, the writer's hand held at the stroke end)."""
    first = strokes_mm[0][0] * 1e-3
    pb = APath(dt, start=(first[0] + start_offset[0] * 1e-3, first[1] + start_offset[1] * 1e-3), lift_height=lift_mm * 1e-3)
    pb.dwell(0.1)
    for s in strokes_mm:
        P = np.asarray(s, float) * 1e-3
        travel = float(np.hypot(*(P[0] - pb.pos)))
        pb.move(P[0], 0.06 + travel / 0.1)
        pb.pen(True, 0.04)
        pb.dwell(0.015)
        L = float(np.sum(np.hypot(*np.diff(P, axis=0).T)))
        T = max(0.05, L / (speed_mm_s * 1e-3))
        pb.polyline(P, T)
        pb.dwell(0.01 + (hold_factor - 1.0) * T + hold_s)
        pb.pen(False, 0.04)
    pb.dwell(0.2)
    it = pb.build()
    scn = PL.Scenario(t=it.t, pref=np.ascontiguousarray(it.xy), vref=np.ascontiguousarray(np.gradient(it.xy, dt, axis=0)),
                      down=np.ascontiguousarray(it.pen_down.astype(np.float64)), intended=it.xy,
                      tremor=np.zeros_like(it.xy), dt=dt, meta={"lift": it.lift})
    return scn


def strokes_track(strokes_mm: List[np.ndarray], speed_mm_s: float) -> "Track":
    """Template track at the controller tick with pen-down flags (for stroke matching)."""
    scn = strokes_scenario(strokes_mm, speed_mm_s, dt=TICK_DT)

    class Track:
        pass
    t = Track()
    t.xy = np.ascontiguousarray(scn.intended)
    t.pen_down = scn.down > 0.5
    return t


def adapt(scn, pen, hand):
    hp = PL.adapted_path(scn.intended, scn.dt, pen, hand)
    return PL.with_hand_path(scn, hp, None)


def _hand(name: str) -> PR.Hand:
    from .params import HAND_CASES
    h = PR.Hand.from_config()
    c = HAND_CASES[name]
    return replace(h, k_arm=c["k_arm"], b_arm=c["b_arm"])


# ----------------------------------------------------------------------------- (b) PD write big
def loops_case(seed: int, target_mm: float = 10.0, start_ratio: float = 0.8, end_ratio: float = 0.6,
               speed: float = 20.0, hand: str = "relaxed"):
    tp = BC.loops(5, target_mm, 6.0, 900, 20.0, 150.0)
    intended = BC.loops(5, target_mm, 6.0, 900, 20.0, 150.0,
                        scale_fn=lambda u: start_ratio + (end_ratio - start_ratio) * u)
    pen = PR.rev_h()
    hd = _hand(hand)
    scn = adapt(strokes_scenario([intended], speed), pen, hd)
    trk = strokes_track([tp], speed)
    Nm = CO.writer_mean_force(50_000 + seed)
    Nt = CO.force_profile(scn.t, scn.down, Nm, 50_000 + seed)
    return {"scn": scn, "track": trk, "pen": pen, "hand": hd, "Nt": Nt, "target_mm": target_mm, "seed": seed,
            "intended_mm": intended, "template_mm": tp, "hand_name": hand}


def run_loops(case: Dict, cond: str, g: Gains, mu: float, hw: Hardware = HW, ref=None):
    drv = drive_for(cond, g, mu, hw)
    trk = case["track"]
    r = DP.run(case["scn"], case["pen"], case["hand"], PR.Writing(), nose_ctl(nose_for(cond), trk), drv, Ntot=case["Nt"],
               drive_tmpl=trk.xy, drive_tdown=trk.pen_down.astype(float), seed=7000 + case["seed"], rec_hz=2000.0)
    c = r.contact > 0.5
    y = r.ink[c, 1] * 1e3 - 150.0
    yi = case["intended_mm"][:, 1] - 150.0
    # per-loop heights: split the ink by the template's loop period in x (6 mm advance per loop)
    x = r.ink[c, 0] * 1e3 - 20.0
    heights = []
    for k in range(5):
        m = (x >= 6.0 * k - 3.0) & (x < 6.0 * k + 3.0)
        if m.sum() > 10:
            heights.append(float(np.percentile(y[m], 99) - np.percentile(y[m], 1)))
    ev = {"cond": cond, "loop_height_ratio_ink": float((np.percentile(y, 99) - np.percentile(y, 1)) / case["target_mm"]),
          "loop_height_ratio_intended": float((yi.max() - yi.min()) / case["target_mm"]),
          "last_loop_ratio": heights[-1] / case["target_mm"] if heights else float("nan")}
    dense = np.column_stack([case["template_mm"][:, 0], case["template_mm"][:, 1]])
    ink = r.ink[c][::20] * 1e3
    d = np.sqrt(((ink[:, None, :] - dense[None, :, :]) ** 2).sum(-1)).min(1)
    ev["ink_to_template_rms_mm"] = float(np.sqrt(np.mean(d ** 2)))
    ev.update(drive_metrics(r, ref))
    return ev, r


# ----------------------------------------------------------------------------- (c) reversal and lead-through
def reversal_case(seed: int = 0, relaxed: bool = False, hand: str = "relaxed", speed: float = 25.0,
                  lead_speed: float = 8.0):
    tpl = BC.letter_b_or_d("d", 8.0, 30.0, 150.0)
    intended = BC.letter_b_or_d("b", 8.0, 30.0, 150.0)
    pen = PR.rev_h()
    hd = _hand(hand)
    if relaxed:
        # the relaxed writer puts the pen down at each stroke start and keeps it down while the drive leads
        # (template length / lead speed x 1.3 + 0.3 s); the pen-up moves are the writer's own
        scn = adapt(strokes_scenario(tpl, lead_speed, hold_factor=1.3, hold_s=0.3), pen, hd)
    else:
        scn = adapt(strokes_scenario(intended, speed), pen, hd)
    trk = strokes_track(tpl, speed)
    Nm = CO.writer_mean_force(60_000 + seed)
    Nt = CO.force_profile(scn.t, scn.down, Nm, 60_000 + seed)
    return {"scn": scn, "track": trk, "pen": pen, "hand": hd, "Nt": Nt, "relaxed": relaxed, "seed": seed,
            "template_mm": tpl, "intended_mm": intended, "hand_name": hand}


def run_reversal(case: Dict, cond: str, g: Gains, mu: float, hw: Hardware = HW, ref=None):
    drv = drive_for(cond, g, mu, hw)
    drv.relaxed = bool(case["relaxed"])
    trk = case["track"]
    r = DP.run(case["scn"], case["pen"], case["hand"], PR.Writing(), nose_ctl(nose_for(cond), trk), drv, Ntot=case["Nt"],
               drive_tmpl=trk.xy, drive_tdown=trk.pen_down.astype(float), seed=8000 + case["seed"], rec_hz=2000.0)
    c = r.contact > 0.5
    # bowl = the second pen-down run
    d = np.diff(np.r_[0, c.astype(int), 0])
    a_, b_ = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    ev = {"cond": cond, "relaxed": bool(case["relaxed"])}
    if len(a_) >= 2:
        ink = r.ink[a_[1] + 40:b_[1]] * 1e3
        ev["bowl_correct_side"] = float(np.mean(ink[:, 0] < 30.0 - 0.5))
        dense = case["template_mm"][1]
        dd = np.sqrt(((ink[::5, None, :] - dense[None, :, :]) ** 2).sum(-1)).min(1)
        ev["bowl_to_template_rms_mm"] = float(np.sqrt(np.mean(dd ** 2)))
        # share of the template bowl that has ink within 0.3 mm (a dot at the start scores ~0; CALC on SIM)
        tb = np.asarray(dense, float)
        seg = np.hypot(*np.diff(tb, axis=0).T)
        u = np.r_[0.0, np.cumsum(seg)]
        ud = np.linspace(0.0, u[-1], max(int(u[-1] / 0.05), 2))
        tbd = np.column_stack([np.interp(ud, u, tb[:, 0]), np.interp(ud, u, tb[:, 1])])
        ik = r.ink[a_[1]:b_[1]][::4] * 1e3
        d2 = np.sqrt(((tbd[:, None, :] - ik[None, :, :]) ** 2).sum(-1)).min(1)
        ev["bowl_coverage"] = float(np.mean(d2 < 0.3))
    else:
        ev["bowl_coverage"] = 0.0
    ev.update(drive_metrics(r, ref))
    return ev, r


# ----------------------------------------------------------------------------- (d) tremor
class ETWriter:
    """An ET writer (handwriting.et_study pattern), its clean run and recogniser, for the Rev H pen."""

    def __init__(self, w: int, text: str = W.ET_SENTENCE):
        self.w = w
        self.hand = PR.Hand.from_config()
        self.pen = PR.rev_h()
        self.written = W.writer(w).write(text, dt=SIM_DT, seed=2000 + w)
        self.scn0 = PL.scenario_from_written(self.written, None, meta={"writer": w})
        self.hp = PL.adapted_path(self.scn0.intended, self.scn0.dt, self.pen, self.hand)
        self.rec = MT.recognizer_for(self.written)
        self.text = text
        Nm = CO.writer_mean_force(30_000 + w)
        self.Nt = CO.force_profile(self.scn0.t, self.scn0.down, Nm, 30_000 + w)
        self.N_mean = Nm

    def scenario(self, tremor):
        return PL.with_hand_path(self.scn0, self.hp, tremor)


def et_metrics(etw: ETWriter, r, scn) -> Dict:
    rows = MT.letter_rows(etw.written, r, etw.rec)
    s = MT.summary(rows)
    wd = MT.words(rows, etw.text)
    return {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"), "letters_read": s.get("recognition_accuracy"),
            "words_letters": wd["word_accuracy_letters"], "words_app": wd.get("word_accuracy_app"),
            "band_err_um": MT.band_error_um(r, scn), "aligned_err_um": MT.aligned_error_um(r, scn)}


def adapted_hand_path(etw: ETWriter, drv: DP.Drive, seed: int, band_hz: float = 3.0) -> np.ndarray:
    """ASSUMPTION (sensitivity): the writer has learnt the device's predictable drag on their own tremor-free writing
    and pushes through it below band_hz, as HW1's adapted_path does for the pen's inertia: hand path + the grip-and-arm
    static compliance x the low-passed device force of a tremor-free run."""
    from scipy.signal import butter, sosfiltfilt
    wri = PR.Writing()
    rc = DP.run(etw.scenario(None), etw.pen, etw.hand, wri, PL.Controls(), drv, Ntot=etw.Nt, hand_path=etw.hp,
                tremor=np.zeros_like(etw.hp), seed=90_000 + seed, rec_hz=4000.0)
    F = np.column_stack([np.interp(etw.scn0.t, rc.t, rc["FBx"]), np.interp(etw.scn0.t, rc.t, rc["FBy"])])
    fs = 1.0 / etw.scn0.dt
    F = sosfiltfilt(butter(2, band_hz, fs=fs, output="sos"), F, axis=0)
    C = 1.0 / etw.hand.K_grip + 1.0 / etw.hand.k_arm
    return etw.hp - C * F


def run_tremor(etw: ETWriter, f0: float, amp: float, seed: int, conds: List[str], g: Gains, mu: float,
               trackers: Optional[Dict] = None, hw: Hardware = HW, adapt_writer: bool = False) -> Dict:
    """All conditions on one (writer, f0, amp, seed).  The nose tracker runs on the same-drive run with the nose
    held central, then closes the loop with -d_hat (HW1's pattern, handwriting/tracker.py and et_study.py)."""
    from handwriting import tracker as TR
    d = W.tremor_path(etw.scn0.t, f0, amp, seed, etw.w) if amp > 0 else np.zeros_like(etw.scn0.intended)
    scn = etw.scenario(d)
    wri = PR.Writing()
    out = {}
    base_cache = {}
    for cond in conds:
        drv_name = cond.replace("+nose_akf", "").replace("nose_akf", "none").replace("nose_oracle", "none")
        drv = drive_for(drv_name if drv_name else "none", g, mu, hw)
        key = drv_name
        hp = etw.hp
        if adapt_writer and drv.mode != "off":
            hp = adapted_hand_path(etw, drv, seed)
        if key not in base_cache:
            base_cache[key] = DP.run(scn, etw.pen, etw.hand, wri, PL.Controls(), drv, Ntot=etw.Nt, hand_path=hp,
                                     tremor=d, seed=90_000 + seed, rec_hz=4000.0)
        rn = base_cache[key]
        if "nose_akf" in cond and trackers:
            tr = trackers.get("revh") or trackers["ship"]
            sseed = 70_000_000 + 1000 * etw.w + 10 * int(round(f0)) + int(round(amp * 1e4)) + seed
            dh, _ = TR.akf_estimate(rn, scn, etw.pen, tr, sseed)
            r = DP.run(scn, etw.pen, etw.hand, wri, PL.Controls(qext=-dh), drv, Ntot=etw.Nt, hand_path=hp, tremor=d,
                       seed=90_000 + seed, rec_hz=4000.0)
        elif "nose_oracle" in cond:
            clean = DP.run(etw.scenario(None), etw.pen, etw.hand, wri, PL.Controls(), drv, Ntot=etw.Nt, hand_path=hp,
                           tremor=np.zeros_like(d), seed=90_000 + seed, rec_hz=4000.0)
            qo = TR.oracle_command(rn, clean, etw.pen, rn.info["n_ticks"], rn.info["Ts"])
            r = DP.run(scn, etw.pen, etw.hand, wri, PL.Controls(qext=qo), drv, Ntot=etw.Nt, hand_path=hp, tremor=d,
                       seed=90_000 + seed, rec_hz=4000.0)
        else:
            r = rn
        ev = et_metrics(etw, r, scn)
        ev.update(drive_metrics(r, base_cache.get("none")))
        out[cond] = ev
    return out


# ----------------------------------------------------------------------------- (e) autowrite
def autowrite_case(w: int, seed: int, profile: str = "dysgraphia", lead_speed: float = 8.0):
    """The practice learner (for the recogniser, the targets and the reference ink) plus a relaxed schedule: the pen
    goes down at each target stroke's start and stays down while the drive leads (length / lead speed x 1.3 + 0.2 s);
    the writer makes the pen-up moves (ASSUMPTION: the app shows where the next stroke starts)."""
    case = practice_case(w, seed, profile)
    su = case["su"]
    strokes = [np.asarray(s, float) * 1e3 for t in su["tl"] for s in t.strokes]
    scn_r = adapt(strokes_scenario(strokes, lead_speed, hold_factor=1.3, hold_s=0.2), case["pen"], case["hand"])
    case["scn_relaxed"] = scn_r
    case["Nt_relaxed"] = CO.force_profile(scn_r.t, scn_r.down, case["N_mean"], 10_000 * w + seed + 1)
    return case


def run_autowrite(case: Dict, cond: str, g: Gains, mu: float, hw: Hardware = HW, ref=None):
    """Relaxed writer: the anchor follows the hand while the pen is down; the writer makes the pen-up moves along
    their own intended path.  The drive leads along the target letters; '+nose' adds the nose without a gate."""
    su = case["su"]
    trk = su["track"]
    drv = drive_for(cond, g, mu, hw)
    relaxed = cond not in ("writer_alone", "nose_nogate")
    drv.relaxed = relaxed
    ctl = nose_ctl(nose_for(cond), trk)
    scn = case["scn_relaxed"] if relaxed else su["scn"]
    Nt = case["Nt_relaxed"] if relaxed else case["Nt"]
    r = DP.run(scn, case["pen"], case["hand"], case["writing"], ctl, drv, Ntot=Nt, drive_tmpl=trk.xy,
               drive_tdown=trk.pen_down.astype(float), seed=su["seed"], rec_hz=2000.0)
    if relaxed:
        ev = evaluate_by_strokes(case, r)
    else:
        r_none = ref if ref is not None else r
        ev = PRc.evaluate(su, r, r_none)
        ev.pop("_rows", None)
        ev["coverage"] = coverage(su, r)
    ev.update(drive_metrics(r, None))
    ev.update(work_share(r))
    c = r.contact > 0.5
    ev["pen_speed_mm_s"] = float(np.mean(np.hypot(r["vHx"], r["vHy"])[c]) * 1e3)
    ev["cond"] = cond
    return ev, r


def work_share(r) -> Dict:
    """Who moved the pen (CALC on SIM): positive mechanical work on the handle by the drive (or board) against the
    positive work by the writer's grip, while the pen is down."""
    c = r.contact > 0.5
    dt = float(r.t[1] - r.t[0])
    v = np.column_stack([r["vHx"], r["vHy"]])
    Pd = np.sum(np.column_stack([r["FBx"], r["FBy"]]) * v, axis=1)
    Pg = np.sum(np.column_stack([r["Fgx"], r["Fgy"]]) * v, axis=1)
    Wd = float(np.sum(np.maximum(Pd, 0.0)[c]) * dt)
    Wg = float(np.sum(np.maximum(Pg, 0.0)[c]) * dt)
    return {"work_device_mJ": Wd * 1e3, "work_writer_mJ": Wg * 1e3, "device_work_share": Wd / max(Wd + Wg, 1e-12)}


def evaluate_by_strokes(case: Dict, r) -> Dict:
    """Letters of a relaxed-writer run, segmented by pen-down runs (one per target stroke, in order), scored against
    the target letters with the app's recogniser (aiguide letter_metrics, handwriting.metrics words)."""
    from aiguide.metrics import letter_metrics
    su = case["su"]
    c = r.contact > 0.5
    d = np.diff(np.r_[0, c.astype(np.int8), 0])
    A, B = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    owner = [i for i, t in enumerate(su["tl"]) for _ in t.strokes]
    q = r.xy("qx")
    rows = []
    wi = 0
    k = 0
    words = W.PRACTICE_SENTENCE.split(" ")
    word_of = []
    for wi_, wd in enumerate(words):
        word_of += [wi_] * len(wd)
    for i, t in enumerate(su["tl"]):
        idx = [j for j, o in enumerate(owner) if o == i]
        if not idx or idx[-1] >= len(A):
            rows.append({"char": su["targets"][i], "missing": True, "word_index": word_of[i], "written_char": t.char})
            continue
        a, b = A[idx[0]], B[idx[-1]]
        lm = letter_metrics(r.ink[a:b], r.contact[a:b], t.strokes, su["targets"][i], su["rec"], q=q[a:b])
        lm["word_index"] = word_of[i]
        lm["written_char"] = t.char
        rows.append(lm)
    s = MT.summary(rows)
    wd = MT.words(rows, W.PRACTICE_SENTENCE)
    return {"target_err_um": s.get("path_rms_um"), "target_p95_um": s.get("path_p95_um"),
            "letters_read_ok": s.get("recognition_accuracy"), "words_read_ok_letters": wd["word_accuracy_letters"],
            "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
            "n_strokes_done": int(len(A)), "n_strokes_target": int(len(owner)), "coverage": coverage(su, r)}
