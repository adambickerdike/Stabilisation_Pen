"""Python interface to the pencil simulator core (model P1).

build_params(): packed parameter vector from config/pencil.yaml (over config/parameters.yaml),
                the stage reduction in sim/pencil/design.py and the controller settings.
run():          one scenario -> named recorded channels.
references(), housing_disturbance(), with_disturbance(): the harness conventions of
                sim/pensim/bench.py and harness.py (neutral clean reference; the oracle gets the
                clean housing path as its disturbance reference).
Scenarios are the M1 builders (sim/pensim/scenarios.py).  Evidence status: SIMULATION.
"""
from __future__ import annotations

import copy
import json
import math
import os
from dataclasses import dataclass, field, replace
from typing import Dict, Optional

import numpy as np

from . import core
from . import design as D
from .layout import IDX, MODES, NP, NREC, RIDX

MODEL_VERSION = "P1.0"
ROOT = D.ROOT
# Bouc-Wen giving an open-loop loop width of about 12 % of full stroke (ASSUMPTION; EXP-Q04 measures)
BW = dict(alpha=0.31, beta=1.0, gamma=1.0)


def frozen_kf():
    """Kalman parameters frozen on the M1 tuning seeds (results/sim/estimator_selection.json)."""
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
    return dict(sel["kfosc"]["selected"]["params"])


@dataclass
class PencilConfig:
    stage_key: str = "Q26"
    skid: bool = True
    locked: bool = False                 # conventional rigid pen: stage and axial slide locked, nib carries N
    stage_locked: bool = False           # stage rigid (q = 0) but skid and spring-loaded nib active
    F_c_ref: Optional[float] = None      # spring force at the design tilt (N); None -> nib.spring_force
    mu_nib: Optional[float] = None
    mu_skid: Optional[float] = None
    mu_bush: float = 0.08                # ASSUMPTION: PTFE-lined collar and gimbal bores (EXP-Q06)
    zeta_stage: float = 0.05             # ASSUMPTION: open-loop stage damping ratio (EXP-Q07)
    hysteresis: bool = True
    V_rail: float = 60.0
    tol: float = 0.0                     # AMF-11 tolerance applied to stroke and force (e.g. -0.2)
    k_skid: float = 1.0e5                # ASSUMPTION: skid-paper contact stiffness (EXP-Q01)
    c_skid: float = 10.0                 # ASSUMPTION
    pen_mass: Optional[float] = None     # kg; None -> CAD (Q) + 10 % wiring and adhesives
    m1_match: bool = False               # use M1's housing mass (cross-check against sim/pensim)
    drv_bw: float = 2000.0               # ASSUMPTION: driver small-signal bandwidth into 2-2.6 uF (Hz)
    drv_slew: float = 3.0e5              # V/s; AMF-16 DRV2700 slew 150-600 V/ms
    servo_hz: float = 10000.0            # inner piezo servo and Hall rate (ASSUMPTION: 10 kSPS Hall)
    servo_bw: float = 25.0               # integral corner (Hz); loop check: PM >= 52 deg, GM 14.8 dB (run_study servo_check)
    servo_zeta: float = 0.4              # damping target of the D term
    d_filt_hz: float = 600.0             # derivative filter corner (Hz): limits Hall-noise-driven drive power
    overrides: Dict = field(default_factory=dict)


@dataclass
class Controller:
    mode: str = "neutral"
    g_assist: float = 1.0
    q_lim: Optional[float] = None        # None -> stage.travel_nib (usable correction radius)
    q_taper: float = 0.05e-3
    slew: float = 0.08
    authority_tau: float = 0.05
    horizon: Optional[float] = None
    kf_qj: float = 3.0
    kf_qt: float = 2e-8
    kf_r: float = 2.5e-11
    kf_w0_hz: float = 6.0
    kf_tau_decay: float = 0.5
    kf_tau_w: float = 0.3
    kf_wmin_hz: float = 2.5
    kf_wmax_hz: float = 14.0
    conf_nis_hi: float = 6.0
    f_gate: float = 0.0
    f_gate_width: float = 1.5
    ff_ref: float = 1.0
    ff_bias: float = 1.0
    V_fixed: float = 30.0


def kalman_controller(**kw):
    return Controller(mode="kfosc", **{**frozen_kf(), **kw})


def _base_params():
    return D.Params()


def static_state(cfg: PencilConfig, theta, N0, P=None):
    """Static nib, skid and housing-height quantities for the build and for the tests."""
    P = P or _base_params()
    st = D.stage(cfg.stage_key, V_rail=cfg.V_rail, tol=cfg.tol)
    r_ring = P["skid.ring_radius"]
    r_b = P["refill.ball_radius"]
    pb = D.protrusion_budget(r_ring, r_ball=r_b)
    p_nom = D.protrusion(theta, r_ring, r_b)["p_centre"]
    p_ref = D.protrusion(P["writing.tilt_deg"] * math.pi / 180, r_ring, r_b)["p_centre"]
    Fc_ref = P["nib.spring_force"] if cfg.F_c_ref is None else cfg.F_c_ref
    k_sp = P["nib.spring_rate"]
    F_sp0 = Fc_ref + k_sp * (p_ref - p_nom)          # the spring is more compressed at a smaller protrusion
    k_p = P["writing.paper_stiffness"]
    N_nib0 = F_sp0 / math.sin(theta)
    return {"stage": st, "p_nom": p_nom, "s_min": p_nom - pb["front_stop_centre"], "s_max": p_nom - pb["rear_stop_centre"],
            "F_sp0": F_sp0, "k_sp": k_sp, "N_nib0": N_nib0, "N_skid0": max(N0 - N_nib0, 0.0), "k_p": k_p,
            "r_b": r_b, "r_ring": r_ring, "budget": pb}


def build_params(scn, ctrl: Controller, cfg: Optional[PencilConfig] = None, dt: float = 25e-6, rec_hz: float = 2000.0):
    cfg = cfg or PencilConfig()
    P = _base_params()
    ov = dict(cfg.overrides)
    g = lambda key: ov.get(key, P[key])      # noqa: E731
    Pv = np.zeros(NP)

    def setp(name, val):
        Pv[IDX[name]] = float(val)

    n = len(scn.t)
    th = math.radians(scn.theta_deg)
    setp("dt", dt); setp("n_steps", n); setp("rec_decim", round(1.0 / (rec_hz * dt)))
    setp("theta", th); setp("phi", math.radians(scn.phi_deg)); setp("rho", math.radians(scn.rho_deg))
    ss = static_state(cfg, th, scn.N0, P)
    st = ss["stage"]
    k_tot = st.k_b_nib + st.k_par_nib
    c_st = 2 * cfg.zeta_stage * math.sqrt(k_tot * st.m_eq_nib)
    setp("m_eq", st.m_eq_nib); setp("k_b", st.k_b_nib); setp("k_par", st.k_par_nib); setp("c_st", c_st)
    setp("m_cpl", st.m_couple_nib); setp("g_V", st.g_V); setp("V_rail", cfg.V_rail); setp("L_piv", st.nib["L_nib"])
    setp("q_stop", st.nib["nib_stop"]); setp("k_stop", g("stage.stop_stiffness")); setp("c_stop", 20.0)
    locked = cfg.locked or ctrl.mode == "locked"
    setp("lock_stage", 1.0 if (locked or cfg.stage_locked) else 0.0)
    setp("bw_on", 1.0 if cfg.hysteresis else 0.0)
    setp("bw_alpha", BW["alpha"]); setp("bw_beta", BW["beta"]); setp("bw_gamma", BW["gamma"])
    setp("bw_hsat", BW["alpha"] / (BW["beta"] + BW["gamma"]))
    setp("drv_tau", 1.0 / (2 * math.pi * cfg.drv_bw)); setp("drv_slew", cfg.drv_slew)
    setp("C_axis", st.C_axis * D.C_LARGE_SIGNAL); setp("eta_c", 0.85)
    # axial
    m_ax = st.nib["m_ax"]
    setp("m_ax", m_ax); setp("k_sp", ss["k_sp"]); setp("F_sp0", ss["F_sp0"])
    setp("c_ax", 2 * 0.3 * math.sqrt(ss["k_sp"] * m_ax))
    setp("s_min", ss["s_min"]); setp("s_max", ss["s_max"])
    setp("mu_b", cfg.mu_bush)
    nb = st.nib
    setp("bear_fac", nb["L_nib"] / nb["L_col"] + (nb["L_nib"] - nb["L_col"]) / nb["L_col"])
    setp("v_b", 1e-4)
    setp("lock_axial", 1.0 if locked else 0.0)
    setp("s_init", ss["s_min"])
    # housing + hand
    if cfg.m1_match:
        from sim.pensim import model as m1
        red = m1.Geometry().reduce()
        M_t = P.base["pen.housing_mass"] + red["m_mov"] + P.base["stage.axial_mass"]
    else:
        M_t = cfg.pen_mass if cfg.pen_mass is not None else D.cad("Q")["mass_total_g"] * 1.1e-3
    setp("M_t", M_t)
    setp("K_hxy", g("hand.grip_stiffness")); setp("C_hxy", g("hand.grip_damping"))
    setp("M_hand", g("hand.mass")); setp("k_arm", g("hand.arm_stiffness")); setp("b_arm", g("hand.arm_damping"))
    setp("K_hz", g("hand.normal_stiffness")); setp("C_hz", g("hand.normal_damping"))
    # nib contact
    k_p = g("writing.paper_stiffness")
    r_b = g("refill.ball_radius")
    mu_k = (P["nib.mu_nib"] if cfg.mu_nib is None else cfg.mu_nib) if not cfg.m1_match else g("writing.mu_eff")
    msr = g("writing.mu_static_ratio")
    setp("k_p", k_p); setp("c_p", g("writing.paper_damping")); setp("r_b", r_b)
    setp("mu_k", mu_k); setp("mu_s", mu_k * msr); setp("v_s", g("writing.stribeck_speed"))
    setp("sigma0", mu_k * msr / 1e-5); setp("sigma1", 0.0); setp("sigma2", 0.0)
    # skid
    skid_on = cfg.skid and not locked
    mu_sk = P["skid.mu"] if cfg.mu_skid is None else cfg.mu_skid
    setp("skid_on", 1.0 if skid_on else 0.0); setp("k_sk", cfg.k_skid); setp("c_sk", cfg.c_skid)
    setp("mu_sk", max(mu_sk, 1e-6)); setp("mus_sk", max(mu_sk, 1e-6) * msr); setp("vs_sk", g("writing.stribeck_speed"))
    setp("sigma0_sk", max(mu_sk, 1e-6) * msr / 1e-5 if mu_sk > 0 else 0.0)
    setp("p_nom", ss["p_nom"]); setp("r_ring", ss["r_ring"])
    # static housing height (hand z reference)
    N0 = scn.N0
    if locked:
        z0 = r_b - N0 / k_p
    elif skid_on and N0 > ss["N_nib0"]:
        z0 = r_b - (N0 - ss["N_nib0"]) / cfg.k_skid
    else:
        z0 = r_b - N0 / k_p - ss["s_max"] * math.sin(th)
    setp("z0", z0)
    # sensors (config/parameters.yaml sensing.*)
    def steps(tsec):
        return max(0, round(tsec / dt))
    setp("hall_noise", g("sensing.hall_noise_tip")); setp("hall_delay", steps(g("sensing.hall_delay")))
    setp("opt_decim", round(1.0 / (g("sensing.opt_rate") * dt))); setp("opt_delay", steps(g("sensing.opt_delay")))
    setp("opt_noise", g("sensing.opt_noise")); setp("opt_lift_max", ov.get("sensing.opt_lift_max", 0.8e-3))
    imu_rate = g("sensing.imu_rate")
    setp("imu_decim", max(1, round(1.0 / (imu_rate * dt)))); setp("imu_delay", steps(g("sensing.imu_delay")))
    setp("imu_noise", g("sensing.imu_acc_noise_density") * math.sqrt(imu_rate / 2.0))
    b = g("sensing.imu_acc_bias")
    setp("imu_bias_x", b); setp("imu_bias_y", -0.5 * b)
    setp("ax_decim", round(1.0 / (g("sensing.force_rate") * dt))); setp("ax_delay", steps(1e-3))
    setp("ax_noise", ov.get("sensing.axial_noise", 2e-6)); setp("contact_thr", ov.get("contact_thr", 0.1e-3))
    # controller
    setp("mode", MODES[ctrl.mode])
    f_stage = g("control.f_stage")
    sdec = round(1.0 / (f_stage * dt))
    Ts = sdec * dt
    vdec = max(1, round(1.0 / (cfg.servo_hz * dt)))
    setp("stage_decim", sdec); setp("servo_decim", vdec)
    Ki = k_tot * 2 * math.pi * cfg.servo_bw
    Kd = max(2 * cfg.servo_zeta * math.sqrt(k_tot * st.m_eq_nib) - c_st, 0.0)
    setp("Ki", Ki); setp("Kp", 0.0); setp("Kd", Kd); setp("d_filt", cfg.d_filt_hz)
    setp("ff_ref", ctrl.ff_ref); setp("ff_bias", ctrl.ff_bias)
    # static transverse load the stage supplies (paper normal force at the nib, expected)
    cr, sr = math.cos(math.radians(scn.rho_deg)), math.sin(math.radians(scn.rho_deg))
    xHz = cr * (-math.cos(th))
    yHz = -sr * (-math.cos(th))
    setp("F_bias0", -ss["N_nib0"] * xHz)       # paper normal force N z-hat gives Q = N z.x_H; the stage supplies -Q
    setp("F_bias1", -ss["N_nib0"] * yHz)
    q_lim = P["stage.travel_nib"] if ctrl.q_lim is None else ctrl.q_lim
    setp("g_assist", ctrl.g_assist); setp("q_lim", q_lim); setp("q_taper", ctrl.q_taper)
    setp("slew", ctrl.slew); setp("authority_tau", ctrl.authority_tau)
    hor = ctrl.horizon if ctrl.horizon is not None else g("sensing.imu_delay") + Ts / 2 + 1.0 / (2 * math.pi * cfg.drv_bw)
    setp("horizon", hor)
    setp("kf_qj", ctrl.kf_qj); setp("kf_qt", ctrl.kf_qt); setp("kf_r", ctrl.kf_r)
    setp("kf_w0", 2 * math.pi * ctrl.kf_w0_hz); setp("kf_rdamp", math.exp(-Ts / ctrl.kf_tau_decay))
    setp("kf_wgain", Ts / ctrl.kf_tau_w)
    setp("kf_wmin", 2 * math.pi * ctrl.kf_wmin_hz); setp("kf_wmax", 2 * math.pi * ctrl.kf_wmax_hz)
    setp("conf_nis_hi", ctrl.conf_nis_hi); setp("f_gate", ctrl.f_gate); setp("f_gate_width", ctrl.f_gate_width)
    Kn = cfg.k_skid if skid_on else g("hand.normal_stiffness")
    gam = Kn * math.sin(th) ** 2 / (Kn * math.sin(th) ** 2 + ss["k_sp"])
    setp("gamma_acc", gam)
    setp("q_init", 0.0); setp("F_test0", 0.0); setp("F_test1", 0.0); setp("V_fixed", ctrl.V_fixed)
    setp("require_contact", 1.0)
    for k_, v in ov.items():
        if k_ in IDX:
            setp(k_, v)
    info = {"model_version": MODEL_VERSION, "stage": st.summary(), "static": {k: v for k, v in ss.items() if k not in ("stage", "budget")},
            "M_t_kg": M_t, "Ki": Ki, "Kd": Kd, "c_stage": c_st, "gamma_acc": gam, "horizon_s": hor, "Ts": Ts,
            "servo_Ts": vdec * dt, "params_version": P.version()}
    return Pv, info


class Result:
    def __init__(self, rec, info, scn, ctrl, cfg, P):
        self.rec = rec
        self.info = info
        self.scn = scn
        self.ctrl = ctrl
        self.cfg = cfg
        self.P = P

    def __getitem__(self, name):
        return self.rec[:, RIDX[name]]

    def xy(self, base):
        i = RIDX[base]
        return self.rec[:, i:i + 2]

    def ink(self):
        """Ink point in the page = page projection of the ball centre."""
        return self.rec[:, [RIDX["Cx"], RIDX["Cy"]]]


def run(scn, ctrl: Controller, cfg: Optional[PencilConfig] = None, seed: int = 1, dt: float = 25e-6,
        rec_hz: float = 2000.0, tmpl=None) -> Result:
    cfg = cfg or PencilConfig()
    Pv, info = build_params(scn, ctrl, cfg, dt, rec_hz)
    n = len(scn.t)
    nrec = int(math.ceil(n / Pv[IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC))
    if tmpl is None:
        sdec = int(Pv[IDX["stage_decim"]])
        tmpl = np.ascontiguousarray(scn.intended[::sdec])
    m = core.simulate(Pv, np.ascontiguousarray(scn.pref), np.ascontiguousarray(scn.vref),
                      np.ascontiguousarray(scn.fpush), np.ascontiguousarray(scn.dtrue),
                      np.ascontiguousarray(tmpl), np.ascontiguousarray(scn.opt_ok.astype(np.float64)),
                      seed, rec)
    return Result(rec[:m], info, scn, ctrl, cfg, Pv)


# ---------------------------------------------------------------- harness helpers
def housing_disturbance(scn_tremor, ref_clean: Result):
    """Clean housing path (neutral, no tremor) at the simulation rate: the oracle's reference
    (as sim/pensim/bench.housing_disturbance)."""
    t_rec = ref_clean["t"]
    clean = ref_clean.xy("pHx")
    t = scn_tremor.t
    return np.column_stack([np.interp(t, t_rec, clean[:, 0]), np.interp(t, t_rec, clean[:, 1])])


def with_disturbance(scn, d):
    s2 = copy.copy(scn)
    s2.dtrue = d
    return s2
