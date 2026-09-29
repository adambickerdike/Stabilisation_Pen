r"""Autowrite in model HW1 (SIMULATION; ``handwriting/`` is used read-only through its public API).

The scene.  The writer holds the pen with the skid on the paper and sweeps it steadily along the line (v_h, from the
planner), with or without hand tremor (the project's tremor model, 0.3-2 mm peak at the hand, 4-12 Hz).  The pen
knows the text (a writer's style from aiguide: size, slant, allographs) and draws it with the nose inside its reach.

What the pen does every 0.5 ms tick (causal; only sensor samples already available are used):
  1. handle position:  a complementary estimator fuses the page sensor (fusion's model: 1 kHz, 2 ms latency, 3 um)
     with the IMU (fusion's LSM6DSV16X model with gyroscope compensation), and predicts it L ahead (L = the nose
     servo's group delay + latency);
  2. progress:  the along-line hand position, low-passed by a critically damped tracking filter (zero lag on a steady
     sweep), sets the plan time tau (monotone: the pen waits rather than retracing);
  3. command:  nose = planned ink point(tau) - predicted handle position; HW1's servo (bandwidth, slew, force and travel
     limits of the design) moves the tip;
  4. ink contact:  with the axial degree of freedom the refill is lifted and lowered by the pen along the plan's
     pen-down flags (a fixed switching delay, ASSUMPTION); without it the ball stays on the paper for the whole line.
Closed loop by fixed-point passes: the handle motion depends weakly on the nose (reaction, ball drag), so the causal
command is recomputed from the sensor streams of the previous pass until it changes by < 5 um rms (at most 6 passes;
the number of passes and the last change are reported per case).

Conventions (ASSUMPTION unless noted): hand HAP-26 (HW1 Hand) that only sweeps and does not compensate drags
(writer_comp "none"); skid drag steady and balanced by the arm (mu_skid 1e-6 in HW1, sensitivity with "drag");
ball drag mu 0.15 (LIT CON-13 range) at the refill force 0.15 N; pen tilt 50 deg.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np
from numba import njit

from . import ensure_paths
from . import planner as PN

ensure_paths()
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import tracker as TR  # noqa: E402
from handwriting import writers as W  # noqa: E402
from fusion import sensors as S  # noqa: E402

TEXT = W.ET_SENTENCE
SIM_DT = W.SIM_DT


# ------------------------------------------------------------------ designs as HW1 pens
@dataclass
class NoseDesign:
    key: str
    label: str
    mass: float                 # kg, whole pen
    m_tip: float                # kg, tip-equivalent moving mass
    k_tip: float                # N/m, suspension at the tip
    q_lim: float                # m, usable travel radius (the guaranteed minimum over 35-75 deg)
    q_stop: float               # m
    servo_hz: float = 80.0
    servo_zeta: float = 0.7
    latency: float = 0.6e-3     # s (tick hold + current loop, as Rev H)
    slew: float = 0.6
    F_peak: float = 0.8         # N at the tip
    F_cont: float = 0.3
    Km_tip: float = 0.1         # N/sqrt(W) at the tip (copper loss = |F|^2 / Km^2, both axes)
    axial: bool = True          # the pen lifts and lowers its own refill
    axial_delay: float = 8e-3   # s, contact switching delay after the command (ASSUMPTION; CalComp's plotter pen lift ran
                                # at 40-50 pulses/s, LIT PAT-41)
    axial_W: float = 0.07       # W, average pen-lift power while autowriting (CALC, designs.axial_dof)
    F_c: float = 0.15           # N, refill axial force (ASSUMPTION, Rev H)
    r_imu: float = 0.0935
    sources: Dict[str, str] = field(default_factory=dict)

    def pen(self) -> PR.Pen:
        return PR.Pen(self.key, self.label, mass=self.mass, rigid=False, m_tip=self.m_tip, k_tip=self.k_tip, zeta_tip=0.05,
                      q_lim=self.q_lim, q_taper=0.1 * self.q_lim, q_stop=self.q_stop, servo_hz=self.servo_hz,
                      servo_zeta=self.servo_zeta, latency=self.latency, slew=self.slew, F_peak=self.F_peak, F_cont=self.F_cont,
                      skid=True, F_c=self.F_c, r_imu=self.r_imu, sources=dict(self.sources))


def revh_design() -> NoseDesign:
    """Rev H as built into HW1 (results/revH/tip_params.json via handwriting.params.rev_h), for comparison.  Km at the tip
    as Rev H states it (0.36 N/sqrt(W), CALC there) and as recalibrated here (designs.revh_as_designed)."""
    p = PR.rev_h()
    return NoseDesign("revH", "Rev H nose (+-3 mm)", p.mass, p.m_tip, p.k_tip, p.q_lim, p.q_stop, p.servo_hz, p.servo_zeta,
                      p.latency, p.slew, p.F_peak, p.F_cont, Km_tip=0.14, axial=False,
                      sources={"all": "results/revH/tip_params.json", "Km_tip": "CALC nose2 magnetics recalibration (0.355 stated)"})


P_COIL_MAX = 0.2        # W, the coil loss that keeps the coil within 20 K of ambient at 100 K/W (designs.DT_COIL_MAX)


def from_summary(des: Dict, handle_od: float, key: str = "revJ", axial: bool = True, servo_hz: float = 80.0,
                 label: Optional[str] = None, axial_W: float = 0.07) -> NoseDesign:
    """An optimised design (optimise.summary) as an HW1 pen.  Travel: the guaranteed minimum over 35-75 deg (HW1's travel
    limit is a circle); stop 0.5 mm beyond; pen mass from the layout's mass budget (CALC); moving mass at the tip from
    the design model (it includes the pen lift, whose share at the tip is about 0.02 g, so both variants use it)."""
    from .layout import layout
    geo = layout(des, handle_od=handle_od, axial=axial)
    X = des["X_min_mm"] * 1e-3
    Km = des["Km_tip"]
    return NoseDesign(key, label or f"Rev J nose ({des['kind']}, +-{des['X_min_mm']:.1f} mm{'' if axial else ', no pen lift'})",
                      mass=geo["mass_g"]["total_g"] * 1e-3, m_tip=des["m_eff_tip_g"] * 1e-3,
                      k_tip=des["k_tip_N_m"], q_lim=X, q_stop=X + 0.5e-3, servo_hz=servo_hz, F_peak=des["F_pk_tip_N"],
                      F_cont=Km * math.sqrt(P_COIL_MAX / 2.0), Km_tip=Km, axial=axial, axial_W=axial_W if axial else 0.0,
                      sources={"all": "nose2 optimise + choose (CALC)", "mass": "nose2/layout.py mass budget (CALC)"})


# ------------------------------------------------------------------ settings chosen on tuning data (tuning.py)
@dataclass
class AWSettings:
    reach_margin: float = 1.0e-3      # m kept free for tremor: plan reach = q_lim - margin
    obs_hz: float = 25.0              # handle observer bandwidth (page sensor vs IMU)
    prog_hz: float = 0.8              # progress filter bandwidth
    lead_extra: float = 0.0           # s added to the servo's group delay in the prediction
    speed: float = 1.0                # sweep speed as a factor of planner.line_speed
    plan: PN.PlanParams = field(default_factory=PN.PlanParams)


# ------------------------------------------------------------------ scenario
@dataclass
class Case:
    w: int
    seed: int
    h_mm: float
    f0: float
    amp: float
    design: NoseDesign
    st: AWSettings
    text: str = TEXT
    written: object = None
    tp: Optional[PN.TargetPath] = None
    plan: Optional[PN.Plan] = None
    scn: Optional[PL.Scenario] = None
    meta: Dict = field(default_factory=dict)


def build(w: int, seed: int, h_mm: float, f0: float, amp: float, design: NoseDesign, st: AWSettings, text: str = TEXT,
          plan_reach: Optional[float] = None, speed_mod: Tuple[float, float] = (0.0, 0.5),
          drift: Tuple[float, float] = (0.0, 0.2)) -> Case:
    """Text, plan and HW1 scenario (hand path = steady sweep + tremor).  Optional user behaviour for the sensitivities:
    speed_mod = (a, f): the sweep speed varies as v_h (1 + a cos 2 pi f t); drift = (d, f): the hand drifts d sin 2 pi f t
    across the line.  The plan is made for the steady sweep; the pen follows the measured hand (progress filter)."""
    written = W.writer(w, x_height_mm=h_mm).write(text, dt=1e-3, seed=2000 + w)
    tp = PN.target_from_written(written)
    v_h = PN.line_speed(tp, st.plan) * st.speed
    R = plan_reach if plan_reach is not None else max(design.q_lim - st.reach_margin, 0.5e-3)
    pl = PN.plan(tp, v_h, R, st.plan)
    c = Case(w, seed, h_mm, f0, amp, design, st, text, written, tp, pl, None, {"v_h": v_h, "plan_reach": R, "plan_ok": pl.ok})
    if not pl.ok:
        return c
    t = np.arange(0.0, pl.t[-1], SIM_DT)
    hx = np.interp(t, pl.t, pl.hand[:, 0])
    hy = np.interp(t, pl.t, pl.hand[:, 1])
    a_s, f_s = speed_mod
    if a_s:
        hx = hx + v_h * a_s / (2 * math.pi * f_s) * np.sin(2 * math.pi * f_s * t)
    d_y, f_y = drift
    if d_y:
        hy = hy + d_y * np.sin(2 * math.pi * f_y * t)
    hand = np.column_stack([hx, hy])
    trem = W.tremor_path(t, f0, amp, seed, w) if amp > 0 else np.zeros_like(hand)
    pref = np.ascontiguousarray(hand + trem)
    vref = np.ascontiguousarray(np.gradient(pref, SIM_DT, axis=0))
    down0 = np.zeros(len(t))
    scn = PL.Scenario(t=t, pref=pref, vref=vref, down=down0, intended=hand.copy(), tremor=trem, dt=SIM_DT,
                      meta={"lift": np.zeros(len(t)), "writer": w})
    c.scn = scn
    return c


# ------------------------------------------------------------------ the pen's causal loop (numba)
@njit(cache=True)
def _loop(tick_t, acc_t, acc_av, acc, pos_t, pos_av, pos, pos_ok, plan_t, plan_x, plan_y, plan_s, x0, v_h,
          kp, kv, w_prog, z_prog, L_pred, T_ax, qx_out, qy_out, tau_out, hx_out, hy_out):
    """Handle estimator + progress + command per tick.  Returns nothing; fills the outputs."""
    n = tick_t.shape[0]
    na = acc_t.shape[0]
    npos = pos_t.shape[0]
    Ts = tick_t[1] - tick_t[0]
    p0 = pos[0, 0]; p1 = pos[0, 1]
    v0 = 0.0; v1 = 0.0
    a0 = 0.0; a1 = 0.0
    ia = 0
    ip = 0
    # history of the estimate at the ticks (for delayed page samples)
    hist0 = np.zeros(n); hist1 = np.zeros(n); vh0 = np.zeros(n); vh1 = np.zeros(n)
    xf = pos[0, 0]; vf = v_h
    tau = 0.0
    for k in range(n):
        t = tick_t[k]
        # IMU samples available by now: integrate each over its own interval
        while ia < na and acc_av[ia] <= t:
            a0 = acc[ia, 0]; a1 = acc[ia, 1]
            ia += 1
        v0 += a0 * Ts; v1 += a1 * Ts
        p0 += v0 * Ts; p1 += v1 * Ts
        hist0[k] = p0; hist1[k] = p1; vh0[k] = v0; vh1[k] = v1
        # page samples available by now: correct with the innovation against the estimate at their acquisition time
        while ip < npos and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5:
                ka = int(pos_t[ip] / Ts)
                if ka < 0:
                    ka = 0
                if ka > k:
                    ka = k
                e0 = pos[ip, 0] - hist0[ka]
                e1 = pos[ip, 1] - hist1[ka]
                dt_a = t - pos_t[ip]
                p0 += kp * e0 + kv * e0 * dt_a
                p1 += kp * e1 + kv * e1 * dt_a
                v0 += kv * e0
                v1 += kv * e1
                # the stored estimates since the acquisition carry the same correction (re-propagated), so the next
                # innovation does not count this error again
                for j in range(ka, k + 1):
                    dtj = tick_t[j] - pos_t[ip]
                    hist0[j] += kp * e0 + kv * e0 * dtj
                    hist1[j] += kp * e1 + kv * e1 * dtj
            ip += 1
        # prediction L ahead
        px = p0 + v0 * L_pred + 0.5 * a0 * L_pred * L_pred
        py = p1 + v1 * L_pred + 0.5 * a1 * L_pred * L_pred
        hx_out[k] = px; hy_out[k] = py
        # progress: critically damped tracking filter on the along-line position (zero lag on a ramp)
        if k == 0:
            xf = p0; vf = v_h
        else:
            e = p0 - xf
            vf += w_prog * w_prog * e * Ts
            xf += (vf + 2.0 * z_prog * w_prog * e) * Ts
        tn = (xf - x0) / v_h + L_pred
        if tn > tau:
            tau = tn
        tau_out[k] = tau
        # command: planned ink point at tau minus the predicted handle
        j = 0
        # linear interpolation in the plan (uniform plan_t)
        dtp = plan_t[1] - plan_t[0]
        fj = (tau - plan_t[0]) / dtp
        if fj < 0.0:
            fj = 0.0
        if fj > plan_t.shape[0] - 1.001:
            fj = plan_t.shape[0] - 1.001
        j = int(fj)
        u = fj - j
        tx = plan_x[j] * (1 - u) + plan_x[j + 1] * u
        ty = plan_y[j] * (1 - u) + plan_y[j + 1] * u
        qx_out[k] = tx - px
        qy_out[k] = ty - py


def observer_gains(obs_hz: float, Ts_page: float = 1e-3, zeta: float = 0.9) -> Tuple[float, float]:
    """Discrete gains of the page-sensor correction (per page sample) for a 2nd-order observer of bandwidth obs_hz."""
    w = 2 * math.pi * obs_hz
    return 2 * zeta * w * Ts_page, w * w * Ts_page


def commands(c: Case, res: PL.Result, sensor_seed: int, page: str = "1k") -> Dict:
    """The pen's causal command per tick from the sensor streams of a run (and the progress it implies)."""
    d = c.design
    pen = d.pen()
    tick_decim = res.info["tick_decim"]
    rec = TR.record(res, c.scn, tick_decim)
    cfg = TR.sensor_config(pen, {"page": page, "comp": "gyro"})
    st = S.make_streams(rec, cfg, sensor_seed)
    n = st.n_ticks()
    # gains per page sample at the sensor's own rate; the bandwidth is capped at a tenth of that rate
    obs_hz = min(c.st.obs_hz, cfg.page.rate / 10.0)
    kp, kv = observer_gains(obs_hz, 1.0 / cfg.page.rate)
    L = PR.servo_group_delay(pen) + c.st.lead_extra
    pl = c.plan
    qx = np.zeros(n); qy = np.zeros(n); tau = np.zeros(n); hx = np.zeros(n); hy = np.zeros(n)
    _loop(st.tick_t, st.acc_t, st.acc_av, st.acc, st.pos_t, st.pos_av, st.pos, st.pos_ok, pl.t, pl.xy[:, 0].copy(),
          pl.xy[:, 1].copy(), pl.s, float(pl.hand[0, 0]), float(c.meta["v_h"]), kp, kv, 2 * math.pi * c.st.prog_hz, 1.0, L,
          d.axial_delay, qx, qy, tau, hx, hy)
    return {"q": np.column_stack([qx, qy]), "tau": tau, "hand_hat": np.column_stack([hx, hy]), "tick_t": st.tick_t}


def contact_schedule(c: Case, tick_t: np.ndarray, tau: np.ndarray) -> np.ndarray:
    """Ball contact at the simulation steps: with the axial DOF the planned pen-down at the current plan time, applied
    after the switching delay; without it the ball stays down from the first touchdown to the last lift."""
    pl = c.plan
    down_plan = np.interp(tau, pl.t, pl.down.astype(float)) > 0.5
    # (the plan's pen-down flags are sampled at the plan step; dwells keep short strokes at >= 25 ms)
    t = c.scn.t
    if c.design.axial:
        # the pen knows the plan: it commands the refill for the plan time one switching delay ahead
        down_lead = np.interp(tau + c.design.axial_delay, pl.t, pl.down.astype(float)) > 0.5
        td = tick_t + c.design.axial_delay
        k = np.clip(np.searchsorted(td, t, side="right") - 1, 0, len(td) - 1)
        dn = down_lead[k] & (t >= td[0])
    else:
        on = np.flatnonzero(down_plan)
        dn = np.zeros(len(t), bool)
        if len(on):
            t0, t1 = tick_t[on[0]], tick_t[on[-1]]
            dn = (t >= t0) & (t <= t1)
    return dn.astype(np.float64)


_HAND = {}


def hand_default(writer_comp: str = "none") -> PR.Hand:
    if writer_comp not in _HAND:
        _HAND[writer_comp] = PR.Hand.from_config(writer_comp=writer_comp)
    return _HAND[writer_comp]


def run(c: Case, sensor_seed: int, passes: int = 6, tol_um: float = 5.0, hand: Optional[PR.Hand] = None,
        writing: Optional[PR.Writing] = None, keep: bool = False, page: str = "1k") -> Dict:
    """Closed-loop autowrite of one case: fixed-point passes until the causal command changes by < tol_um rms (at most
    `passes`); returns metrics (and the run if keep)."""
    if not c.plan.ok:
        return {"plan_ok": False}
    hand = hand or hand_default("none")
    writing = writing or PR.Writing(mu_skid=1e-6)          # steady skid drag balanced by the arm (0 breaks HW1's LuGre)
    pen = c.design.pen()
    # pass 0: the nominal command (plan minus the nominal sweep) to get a first handle motion
    Ts = 1.0 / pen.tick_hz
    tt = np.arange(0.0, c.scn.t[-1] + Ts, Ts)
    tau0 = tt.copy()
    q0 = np.column_stack([np.interp(tt, c.plan.t, c.plan.xy[:, 0] - c.plan.hand[:, 0]),
                          np.interp(tt, c.plan.t, c.plan.xy[:, 1] - c.plan.hand[:, 1])])
    scn = c.scn
    scn.down = np.ascontiguousarray(contact_schedule(c, tt, tau0))
    res = PL.run(scn, pen, hand, writing, PL.Controls(qext=np.ascontiguousarray(q0)))
    hist = []
    cmd = None
    for p in range(passes):
        cmd = commands(c, res, sensor_seed, page)
        scn.down = np.ascontiguousarray(contact_schedule(c, cmd["tick_t"], cmd["tau"]))
        res_new = PL.run(scn, pen, hand, writing, PL.Controls(qext=np.ascontiguousarray(cmd["q"])))
        if hist:
            n = min(len(hist[-1]), len(cmd["q"]))
            dq = float(np.sqrt(np.mean(np.sum((hist[-1][:n] - cmd["q"][:n]) ** 2, axis=1))) * 1e6)
        else:
            dq = float("nan")
        hist.append(cmd["q"])
        res = res_new
        c.meta[f"pass{p}_dq_um"] = dq
        last = p
        if dq == dq and dq < tol_um:
            break
    out = metrics(c, res, cmd)
    out["convergence_dq_um"] = c.meta.get(f"pass{last}_dq_um")
    out["passes"] = last + 1
    if keep:
        out["_res"] = res
        out["_cmd"] = cmd
    return out


# ------------------------------------------------------------------ metrics
def retimed(c: Case, cmd: Dict):
    """A copy of the Written whose letter windows follow the executed progress (the ink of letter k is laid while the
    plan time passes the letter's samples)."""
    wr = copy.copy(c.written)
    wr.letters = [copy.copy(L) for L in c.written.letters]
    path = c.plan.path
    i_tau = np.interp(cmd["tau"], c.plan.t, c.plan.idx)
    for L in wr.letters:
        idx = np.flatnonzero(path.letter == L.glyph_index)
        k0 = int(np.searchsorted(i_tau, idx[0] - 0.5))
        k1 = int(np.searchsorted(i_tau, idx[-1] + 0.5))
        L.t0 = float(cmd["tick_t"][min(k0, len(i_tau) - 1)])
        L.t1 = float(cmd["tick_t"][min(k1, len(i_tau) - 1)])
    return wr


def metrics(c: Case, res: PL.Result, cmd: Dict) -> Dict:
    wr = retimed(c, cmd)
    rec = MT.recognizer_for(wr)
    rows = MT.letter_rows(wr, res, rec, pad=0.0)
    s = MT.summary(rows)
    wd = MT.words(rows, c.text)
    d = c.design
    m = res.contact > 0.5
    F2 = res["Fax"] ** 2 + res["Fay"] ** 2
    t_text = (wr.letters[0].t0, wr.letters[-1].t1)
    mt = (res.t >= t_text[0]) & (res.t <= t_text[1])
    P_cu = float(np.mean(F2[mt]) / d.Km_tip ** 2) if mt.any() else float("nan")
    qc = np.hypot(res["qcx"], res["qcy"])
    q = np.hypot(res["qx"], res["qy"])
    hand_dev = res.handle - np.column_stack([np.interp(res.t, c.scn.t, c.scn.intended[:, 0]), np.interp(res.t, c.scn.t, c.scn.intended[:, 1])])
    n_let = len(wr.letters)
    dur = t_text[1] - t_text[0]
    tgt = target_read(c.written, rec)
    return {"plan_ok": True, "w": c.w, "seed": c.seed, "h_mm": c.h_mm, "f0": c.f0, "amp_mm": c.amp * 1e3, "design": d.key,
            "axial": d.axial, "v_h_mm_s": c.meta["v_h"] * 1e3, "plan_reach_mm": c.meta["plan_reach"] * 1e3,
            "ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"), "dtw_um": s.get("dtw_mean_um"),
            "letters_read": s.get("recognition_accuracy"), "target_letters_read": tgt["letters"],
            "target_words_read_app": tgt["words_app"], "words_read_letters": wd["word_accuracy_letters"],
            "words_read_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
            "letters_per_s": n_let / dur if dur > 0 else float("nan"), "line_s": dur,
            "P_coil_W": P_cu, "P_axial_W": d.axial_W if d.axial else 0.0,
            "F_rms_N": float(np.sqrt(np.mean(F2[mt]))) if mt.any() else float("nan"),
            "F_p99_N": float(np.percentile(np.sqrt(F2[mt]), 99)) if mt.any() else float("nan"),
            "at_travel_limit": float(np.mean(qc[mt] >= 0.95 * d.q_lim)) if mt.any() else float("nan"),
            "on_stop": float(np.mean(res["stop"][mt] > 0.5)) if mt.any() else float("nan"),
            "at_force_limit": float(np.mean(res["sat"][mt] > 0.5)) if mt.any() else float("nan"),
            "q_max_mm": float(q[mt].max() * 1e3) if mt.any() else float("nan"),
            "handle_dev_rms_um": float(np.sqrt(np.mean(np.sum(hand_dev[mt] ** 2, axis=1))) * 1e6) if mt.any() else float("nan"),
            "reaction_rms_N": float(np.sqrt(np.mean(F2[mt]))) if mt.any() else float("nan")}


_TGT = {}


def target_read(written, rec) -> Dict:
    """The recogniser on the clean target letters themselves: the ceiling any pen can reach for this writer's style."""
    key = (written.meta.get("writer_seed"), written.style.x_height_mm, written.text)
    if key not in _TGT:
        rows = []
        for L in written.letters:
            pred, _ = rec.classify([np.asarray(p) for p in L.polylines])
            rows.append({"char": L.char, "recognised_as": pred, "recognised_ok": pred == L.char, "word_index": L.word_index})
        wd = MT.words(rows, written.text)
        _TGT[key] = {"letters": float(np.mean([r["recognised_ok"] for r in rows])), "words_app": wd.get("word_accuracy_app")}
    return _TGT[key]


def ink_paths(c: Case, res: PL.Result, hz: float = 60.0) -> Dict:
    """Ink and target paths (mm) for figures and the viewer."""
    return {"ink": MT.decimate_path(res, None, hz).tolist(),
            "target": [[float(x * 1e3), float(y * 1e3), 1.0] for x, y in c.tp.xy[::10]],
            "handle": MT.decimate_path(res, None, hz, key="handle").tolist()}
