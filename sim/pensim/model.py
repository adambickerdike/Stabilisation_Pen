"""Python interface to the compiled simulator core (model version M1).

build_params(): assemble the packed parameter vector from config/parameters.yaml,
                the configuration geometry and controller design choices.
run():          execute one scenario and return named recorded channels.
Evidence status of every output: SIMULATION.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
from scipy import signal as sps

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stabpen import params as sp_params  # noqa: E402
from .layout import IDX, MODES, NP, NREC, RIDX  # noqa: E402
from . import core  # noqa: E402

MODEL_VERSION = "M1.0"


@dataclass
class Geometry:
    """Moving-part geometry of a configuration (tip-equivalent reduction)."""
    kind: str = "lever"            # "lever" (front pivot, rear actuator) or "translational"
    L1: float = 0.012              # pivot -> ball (m)             [CAD Rev A]
    L2: float = 0.038              # pivot -> actuator force line (m)  [CAD Rev A, n = 3.17]
    m_carrier: float = 1.13e-3     # Ti carrier tube (kg)          [CAD Rev A]
    L_carrier_front: float = 0.009 # carrier extent in front of pivot (m)
    L_carrier_rear: float = 0.052  # carrier extent behind pivot (m)
    m_refill: float = 0.6e-3       # kg (weigh samples, EXP-B02)
    m_act: float = 0.44e-3         # moving-coil paddle at L2 (kg)  [CAD Rev A]
    m_trans: float = 2.0e-3        # translational carriage mass (kg) if kind == translational

    def reduce(self):
        """Return tip-equivalent mass, coupling mass, moving mass, CoM factor, lever ratio."""
        if self.kind == "translational":
            m = self.m_trans
            return {"m_eq": m, "m_couple": -m, "m_mov": m, "cm_factor": 1.0, "n_lever": 1.0, "L1": 1e9}
        L1, L2 = self.L1, self.L2
        # rod: carrier + refill as uniform rods from -Lf (tip side) to +Lr (rear)
        m_rod = self.m_carrier + self.m_refill
        Lf, Lr = self.L_carrier_front, self.L_carrier_rear
        J_rod = m_rod * (Lf ** 3 + Lr ** 3) / (3 * (Lf + Lr))
        x_rod = m_rod * (Lr ** 2 - Lf ** 2) / (2 * (Lf + Lr))   # first moment about pivot (+ rear)
        J = J_rod + self.m_act * L2 ** 2
        first = x_rod + self.m_act * L2
        m_mov = m_rod + self.m_act
        L_cm = first / m_mov
        return {"m_eq": J / L1 ** 2, "m_couple": m_mov * L_cm / L1, "m_mov": m_mov,
                "cm_factor": -L_cm / L1, "n_lever": L2 / L1, "L1": L1, "L_cm": L_cm, "J_pivot": J}


@dataclass
class Controller:
    mode: str = "kfosc"
    f_stage: float = 2000.0
    pos_bw: float = 60.0            # Hz closed-loop design bandwidth
    zeta: float = 0.7
    ki_ratio: float = 0.2           # integral corner as fraction of pos_bw
    d_filt_ratio: float = 5.0
    ff_contact: float = 0.0         # DEC-011: measured-force contact feedforward disabled (nib bounce at low altitude, sim/diag_ff_chatter.py)
    ff_contact_fc: float = 60.0     # Hz low-pass on the force used for contact feedforward when enabled (<=0: none)
    ff_contact_order: int = 2       # 1: first-order, 2: second-order Butterworth
    ff_accel: float = 1.0
    ff_ref: float = 1.0
    g_assist: float = 1.0
    q_lim: float = 0.55e-3
    q_taper: float = 0.1e-3
    slew: float = 0.08              # m/s max command slew (0.08 m/s >> tremor 0.03 m/s)
    authority_tau: float = 0.05     # s
    bp_lo: float = 3.0
    bp_hi: float = 14.0
    bp_tune_hz: float = 6.0
    horizon: Optional[float] = None  # s; None -> computed from delays
    kf_qj: float = 3.0
    kf_qt: float = 2e-8
    kf_r: float = 2.5e-11
    kf_w0_hz: float = 6.0
    kf_tau_decay: float = 0.5
    kf_tau_w: float = 0.3
    kf_wmin_hz: float = 2.5
    kf_wmax_hz: float = 14.0
    conf_nis_hi: float = 6.0
    oracle_h: float = 0.0
    cur_bw: float = 2000.0
    axial_comp: float = 0.0
    gamma_acc: Optional[float] = None   # None -> computed from nominal compliances
    f_gate: float = 0.0                 # Hz; 0 disables the frequency gate
    f_gate_width: float = 1.5           # Hz
    axial_comp_tau: float = 2.0


@dataclass
class Scenario:
    t: np.ndarray
    pref: np.ndarray       # (n,3) hand reference: x, y, lift height
    vref: np.ndarray
    fpush: np.ndarray      # (n,) N
    dtrue: np.ndarray      # (n,2) true tremor component in hand reference
    intended: np.ndarray   # (n,2)
    opt_ok: np.ndarray     # (n,) uint8
    theta_deg: float = 50.0
    phi_deg: float = 0.0
    rho_deg: float = 0.0
    N0: float = 1.0
    meta: Dict = field(default_factory=dict)


def _pget(p, key, over):
    return over.get(key, p[key])


def build_params(scn: Scenario, ctrl: Controller, geom: Optional[Geometry] = None,
                 overrides: Optional[Dict] = None, dt: float = 25e-6, rec_hz: float = 2000.0):
    """Assemble the packed parameter vector.  overrides: dotted parameter keys
    (config/parameters.yaml) or direct layout names, applied last."""
    p = sp_params.load()
    over = dict(overrides or {})
    geom = geom or Geometry(L1=_pget(p, "stage.L1", over), L2=_pget(p, "stage.L2", over))
    red = geom.reduce()
    P = np.zeros(NP)

    def setp(name, val):
        P[IDX[name]] = float(val)

    n = len(scn.t)
    setp("dt", dt); setp("n_steps", n); setp("rec_decim", round(1.0 / (rec_hz * dt)))
    th = math.radians(scn.theta_deg)
    setp("theta", th); setp("phi", math.radians(scn.phi_deg)); setp("rho", math.radians(scn.rho_deg))
    m_eq = red["m_eq"]
    k_tip = _pget(p, "stage.k_tip", over)
    zeta_o = _pget(p, "stage.zeta_open", over)
    setp("m_eq", m_eq); setp("k_tip", k_tip); setp("c_tip", 2 * zeta_o * math.sqrt(k_tip * m_eq))
    setp("m_couple", red["m_couple"]); setp("m_mov", red["m_mov"]); setp("cm_factor", red["cm_factor"])
    setp("L1", red["L1"])
    setp("q_stop", _pget(p, "stage.travel_tip_mech", over))
    setp("k_stop", _pget(p, "stage.stop_stiffness", over)); setp("c_stop", 20.0)
    m_ax = _pget(p, "stage.axial_mass", over)
    k_ax = _pget(p, "stage.axial_k", over)
    setp("m_ax", m_ax); setp("k_ax", k_ax)
    setp("c_ax", 2 * _pget(p, "stage.axial_zeta", over) * math.sqrt(k_ax * m_ax))
    F_pre = _pget(p, "stage.axial_preload", over)
    setp("F_pre", F_pre); setp("s_max", _pget(p, "stage.axial_travel", over))
    # housing + hand
    setp("m_H", _pget(p, "pen.housing_mass", over))
    setp("K_hxy", _pget(p, "hand.grip_stiffness", over)); setp("C_hxy", _pget(p, "hand.grip_damping", over))
    setp("M_hand", _pget(p, "hand.mass", over)); setp("k_arm", _pget(p, "hand.arm_stiffness", over))
    setp("b_arm", _pget(p, "hand.arm_damping", over))
    setp("K_hz", _pget(p, "hand.normal_stiffness", over)); setp("C_hz", _pget(p, "hand.normal_damping", over))
    # contact + friction
    k_p = _pget(p, "writing.paper_stiffness", over)
    r_b = _pget(p, "refill.ball_radius", over)
    mu_k = _pget(p, "writing.mu_eff", over)
    setp("k_p", k_p); setp("c_p", _pget(p, "writing.paper_damping", over)); setp("r_b", r_b)
    setp("mu_k", mu_k); setp("mu_s", mu_k * _pget(p, "writing.mu_static_ratio", over))
    setp("v_s", _pget(p, "writing.stribeck_speed", over))
    x_pre = over.get("friction.x_presliding", 1e-5)
    setp("sigma0", mu_k * _pget(p, "writing.mu_static_ratio", over) / x_pre)
    setp("sigma1", over.get("friction.sigma1", 0.0)); setp("sigma2", over.get("friction.sigma2", 0.0))
    # static housing height at the nominal load (for hand z reference)
    N0 = scn.N0
    s0 = 0.0 if ctrl.mode == "rigid" else min(max(0.0, (N0 * math.sin(th) - F_pre) / k_ax), _pget(p, "stage.axial_travel", over))
    setp("z0", r_b - N0 / k_p - s0 * math.sin(th))
    # actuator
    setp("n_lever", red["n_lever"]); setp("Kf", _pget(p, "actuator.Kf", over))
    R20 = _pget(p, "actuator.R20", over); Lc = _pget(p, "actuator.L", over)
    setp("R20", R20); setp("Lc", Lc)
    setp("V_bus", _pget(p, "electrical.v_bat_nom", over))
    rbr = _pget(p, "electrical.r_bridge", over); rsh = _pget(p, "electrical.r_shunt", over)
    setp("r_bridge", rbr); setp("r_shunt", rsh)
    setp("i_max", _pget(p, "actuator.i_max", over)); setp("alpha_cu", _pget(p, "actuator.alpha_cu", over))
    setp("alpha_B", over.get("actuator.alpha_B", -0.0012))
    setp("Rth", _pget(p, "actuator.Rth_coil_amb", over)); setp("Cth", _pget(p, "actuator.Cth_coil", over))
    setp("T_amb", _pget(p, "thermal.t_ambient", over))
    f_cur = _pget(p, "control.f_current", over)
    cdec = max(1, round(1.0 / (f_cur * dt)))
    setp("cur_decim", cdec)
    wci = 2 * math.pi * ctrl.cur_bw
    setp("Kp_i", Lc * wci); setp("Ki_i", (R20 + rbr + rsh) * wci)
    # sensors
    def steps(tsec):
        return max(0, round(tsec / dt))
    setp("hall_noise", _pget(p, "sensing.hall_noise_tip", over)); setp("hall_delay", steps(_pget(p, "sensing.hall_delay", over)))
    ict = _pget(p, "sensing.hall_i_crosstalk_tip", over)
    setp("hall_ict", ict); setp("hall_ict_comp", over.get("sensing.hall_ict_comp", ict))
    setp("opt_decim", round(1.0 / (_pget(p, "sensing.opt_rate", over) * dt)))
    setp("opt_delay", steps(_pget(p, "sensing.opt_delay", over)))
    setp("opt_noise", _pget(p, "sensing.opt_noise", over)); setp("opt_scale", over.get("sensing.opt_scale", 0.0))
    setp("opt_lift_max", over.get("sensing.opt_lift_max", 0.8e-3))
    imu_rate = _pget(p, "sensing.imu_rate", over)
    setp("imu_decim", max(1, round(1.0 / (imu_rate * dt))))
    setp("imu_delay", steps(_pget(p, "sensing.imu_delay", over)))
    setp("imu_noise", _pget(p, "sensing.imu_acc_noise_density", over) * math.sqrt(imu_rate / 2.0))
    b = _pget(p, "sensing.imu_acc_bias", over)
    setp("imu_bias_x", b); setp("imu_bias_y", -0.5 * b)
    setp("force_decim", round(1.0 / (_pget(p, "sensing.force_rate", over) * dt)))
    setp("force_delay", steps(1.0e-3)); setp("force_noise", _pget(p, "sensing.force_noise", over) / max(k_ax, 1e-9) * k_ax)
    # controller
    setp("mode", MODES[ctrl.mode])
    sdec = round(1.0 / (ctrl.f_stage * dt))
    Ts = sdec * dt
    setp("stage_decim", sdec)
    wc = 2 * math.pi * ctrl.pos_bw
    Kp = max(m_eq * wc ** 2 - k_tip, 0.0)
    Kd = max(2 * ctrl.zeta * m_eq * wc, 0.0)
    Ki = Kp * wc * ctrl.ki_ratio
    setp("Kp", Kp); setp("Kd", Kd); setp("Ki", Ki); setp("d_filt", ctrl.d_filt_ratio * ctrl.pos_bw)
    setp("ff_contact", ctrl.ff_contact); setp("ff_accel", ctrl.ff_accel); setp("ff_ref", ctrl.ff_ref)
    setp("ffc_fc", ctrl.ff_contact_fc)
    fsd = 1.0 / (round(1.0 / (ctrl.f_stage * dt)) * dt)
    if ctrl.ff_contact_fc <= 0:
        fb = (1.0, 0.0, 0.0, 0.0, 0.0)
    elif ctrl.ff_contact_order == 2:
        b0, b1, b2, _a0, a1, a2 = sps.butter(2, ctrl.ff_contact_fc, btype="low", fs=fsd, output="sos")[0]
        fb = (b0, b1, b2, a1, a2)
    else:
        al = 1.0 - math.exp(-2.0 * math.pi * ctrl.ff_contact_fc / fsd)
        fb = (al, 0.0, 0.0, -(1.0 - al), 0.0)
    for nm, v in zip(("ffc_b0", "ffc_b1", "ffc_b2", "ffc_a1", "ffc_a2"), fb):
        setp(nm, v)
    setp("mu_hat", mu_k)
    setp("g_assist", ctrl.g_assist); setp("q_lim", ctrl.q_lim); setp("q_taper", ctrl.q_taper)
    setp("slew", ctrl.slew); setp("authority_tau", ctrl.authority_tau)
    fs = 1.0 / Ts
    sos_h = sps.butter(2, ctrl.bp_lo, btype="high", fs=fs, output="sos")[0]
    sos_l = sps.butter(2, ctrl.bp_hi, btype="low", fs=fs, output="sos")[0]
    for name, sos in (("bp1", sos_h), ("bp2", sos_l)):
        b0, b1, b2, a0, a1, a2 = sos
        base = IDX[f"{name}_b0"]
        P[base:base + 5] = [b0, b1, b2, a1, a2]
    w_t, h_h = sps.sosfreqz(np.vstack([sos_h, sos_l]), worN=[ctrl.bp_tune_hz], fs=fs)
    setp("bp_gain_comp", 1.0 / abs(h_h[0]))
    imu_delay = _pget(p, "sensing.imu_delay", over)
    if ctrl.horizon is None:
        servo_lag = 0.0 if ctrl.ff_ref > 0 else 2 * ctrl.zeta / wc
        hor = imu_delay + Ts / 2 + servo_lag + 1.0 / (2 * math.pi * ctrl.cur_bw)
    else:
        hor = ctrl.horizon
    setp("horizon", hor)
    setp("kf_qj", ctrl.kf_qj); setp("kf_qt", ctrl.kf_qt); setp("kf_r", ctrl.kf_r)
    setp("kf_w0", 2 * math.pi * ctrl.kf_w0_hz); setp("kf_rdamp", math.exp(-Ts / ctrl.kf_tau_decay))
    setp("kf_wgain", Ts / ctrl.kf_tau_w)
    setp("kf_wmin", 2 * math.pi * ctrl.kf_wmin_hz); setp("kf_wmax", 2 * math.pi * ctrl.kf_wmax_hz)
    setp("conf_nis_hi", ctrl.conf_nis_hi)
    setp("oracle_h", round(ctrl.oracle_h / dt))
    setp("q_init", 0.0); setp("require_contact", 1.0)
    setp("axial_comp", ctrl.axial_comp); setp("axial_comp_tau", ctrl.axial_comp_tau)
    if ctrl.gamma_acc is None:
        Kn = _pget(p, "hand.normal_stiffness", over)
        gam = Kn * math.sin(th) ** 2 / (Kn * math.sin(th) ** 2 + k_ax)
    else:
        gam = ctrl.gamma_acc
    setp("gamma_acc", gam)
    setp("f_gate", ctrl.f_gate); setp("f_gate_width", ctrl.f_gate_width)
    setp("kappa_s", over.get("stage.kappa_s", 0.0))   # Rev A: suspension behind pivot (DEC-007)
    setp("fail_type", over.get("fail_type", 0)); setp("fail_time", over.get("fail_time", 1e9))
    info_gamma = gam
    # direct layout-name overrides last
    for k_, v in over.items():
        if k_ in IDX:
            setp(k_, v)
    info = {"reduction": red, "Kp": Kp, "Kd": Kd, "Ki": Ki, "horizon_s": hor, "Ts": Ts, "gamma_acc": info_gamma,
            "model_version": MODEL_VERSION, "params_version": p.version(), "params_digest": p.digest()}
    return P, info


class Result:
    def __init__(self, rec, info, scn, ctrl, P):
        self.rec = rec
        self.info = info
        self.scn = scn
        self.ctrl = ctrl
        self.P = P

    def __getitem__(self, name):
        return self.rec[:, RIDX[name]]

    def xy(self, base):
        i = RIDX[base]
        return self.rec[:, i:i + 2]


def run(scn: Scenario, ctrl: Controller, geom: Optional[Geometry] = None, overrides=None,
        seed: int = 1, dt: float = 25e-6, rec_hz: float = 2000.0, tmpl=None) -> Result:
    P, info = build_params(scn, ctrl, geom, overrides, dt, rec_hz)
    n = len(scn.t)
    nrec = int(math.ceil(n / P[IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC))
    if tmpl is None:
        sdec = int(P[IDX["stage_decim"]])
        tmpl = np.ascontiguousarray(scn.intended[::sdec])
    m = core.simulate(P, np.ascontiguousarray(scn.pref), np.ascontiguousarray(scn.vref),
                      np.ascontiguousarray(scn.fpush), np.ascontiguousarray(scn.dtrue),
                      np.ascontiguousarray(tmpl), np.ascontiguousarray(scn.opt_ok.astype(np.float64)),
                      seed, rec)
    return Result(rec[:m], info, scn, ctrl, P)
