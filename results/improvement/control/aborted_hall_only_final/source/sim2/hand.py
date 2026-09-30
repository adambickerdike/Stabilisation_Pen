r"""Articulated hand model 'arm': forearm-wrist-hand chain, writer controller and tremor torques.

Chain (page frame; right-handed writer; every geometric value is ASSUMPTION, params.Arm):
  arm_base  3 slides (page x, y, z) at the elbow: the shoulder/elbow positioning of the forearm on the desk, with the
            arm's impedance (HAP-26 k2, b2); carries the forearm mass
  forearm_d pronation-supination hinge about the forearm axis (elbow -> wrist) at the wrist
  palm      wrist flexion-extension and radial-ulnar deviation hinges at the wrist centre (semi-pronated hand: the
            flexion axis is the horizontal normal to the forearm rotated 45 deg about it); the hand's mass and inertia
  handle    the pen, attached through H1's two-zone grip joints at the elastic centre (builder.py), so the grip is
            exactly H1's in the linear regime; the finger-joint compliance is inside the grip calibration (HAP-26).
Joint impedance = the writer's muscles: passive stiffness (LIT HAP-32: wrist [1.28 -0.18; -0.18 1.74] N m/rad, PS
0.2-0.3 N m/rad) times a co-contraction multiplier cc, damping at a constant damping ratio (Perreault et al. 2004 found a
nearly invariant damping ratio across force levels: LIT, abstract), realised as position/velocity servos around the
planned (equilibrium) trajectory, plus feedforward torques from inverse dynamics (an internal model of arm + pen), the
writing force J^T F_N and the expected paper drag (writer compensation, ASSUMPTION as HW1), and tremor torques at the
forearm and wrist (tremor.py).
Planning: the intended pen-tip path (sigma-lognormal writer, stabpen.signals; or aiguide writers) is split into a slow
part (< 1 Hz, words and the line: the arm base) and the letters (wrist and forearm rotations), solved by Newton IK on the
tip position with the grip undeflected.
Evidence status: SIMULATION with ASSUMPTION/LIT parameters.  The model's tip impedance is fitted to H1's (HAP-26) in
the page plane by `calibrate_to_h1` (SIM), not measured.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

import mujoco
import numpy as np

from . import params as P

ARM_JOINTS = ("arm_x", "arm_y", "arm_z", "ps", "wfe", "wrud")


def _f(x) -> str:
    return " ".join(f"{float(v):.9g}" for v in np.atleast_1d(x))


def geometry(cfg: P.Config, z0: float, z_c: float) -> Dict[str, np.ndarray]:
    ar, g = cfg.arm, cfg.geom
    a, t1, t2, n, h = g.vectors()
    tip = np.array([0.0, 0.0, z0])
    grip = tip + z_c * a
    beta = ar.forearm_dir_deg * P.D2R
    u_back = np.array([math.cos(beta), -math.sin(beta), 0.0])      # from the hand toward the elbow (in the page)
    wrist = grip + ar.wrist_to_grip * u_back + np.array([0.0, 0.0, 0.010])
    elbow = wrist + ar.L_forearm * u_back + np.array([0.0, 0.0, 0.020])
    u_f = (wrist - elbow) / np.linalg.norm(wrist - elbow)            # forearm axis, elbow -> wrist
    e_perp = np.cross(n, u_f)
    e_perp /= np.linalg.norm(e_perp)
    pr = 45.0 * P.D2R                                                # semi-pronation (ASSUMPTION)
    e_up = np.cross(u_f, e_perp)
    e_fe = math.cos(pr) * e_up + math.sin(pr) * e_perp               # flexion-extension axis
    e_rud = np.cross(u_f, e_fe)
    e_rud /= np.linalg.norm(e_rud)
    return {"tip": tip, "grip": grip, "wrist": wrist, "elbow": elbow, "u_f": u_f, "e_fe": e_fe / np.linalg.norm(e_fe),
            "e_rud": e_rud}


def arm_mjcf(cfg: P.Config, A, z0: float, gp: Dict):
    ar = cfg.arm
    G = geometry(cfg, z0, gp["z_c"])
    el, wr, tip = G["elbow"], G["wrist"], G["tip"]
    m_fa = ar.m_forearm + ar.m_base
    com_fa = 0.45 * (wr - el)
    Jfa = ar.m_forearm * ar.L_forearm ** 2 / 12.0
    A(f'    <body name="arm_base" pos="{_f(el)}">')
    for ax, nm in (("1 0 0", "arm_x"), ("0 1 0", "arm_y"), ("0 0 1", "arm_z")):
        A(f'      <joint name="{nm}" type="slide" axis="{ax}"/>')
    A(f'      <inertial pos="{_f(com_fa)}" mass="{m_fa:.9g}" diaginertia="{Jfa:.6g} {Jfa:.6g} {Jfa / 10:.6g}"/>')
    A(f'      <geom type="capsule" fromto="0 0 0 {_f(wr - el)}" size="0.03" rgba="0.9 0.75 0.65 0.4"/>')
    A(f'      <body name="forearm_d" pos="{_f(wr - el)}">')
    A(f'        <joint name="ps" type="hinge" axis="{_f(G["u_f"])}" pos="0 0 0"/>')
    A('        <inertial pos="0 0 0" mass="0.05" diaginertia="2e-4 2e-4 2e-4"/>')
    A('        <body name="palm" pos="0 0 0">')
    A(f'          <joint name="wfe" type="hinge" axis="{_f(G["e_fe"])}" pos="0 0 0"/>')
    A(f'          <joint name="wrud" type="hinge" axis="{_f(G["e_rud"])}" pos="0 0 0"/>')
    d_hand = (G["grip"] - wr) / np.linalg.norm(G["grip"] - wr)
    com_h = ar.hand_com * d_hand
    Jc = max(ar.J_hand - ar.m_hand * ar.hand_com ** 2, 1e-5)
    A(f'          <inertial pos="{_f(com_h)}" mass="{ar.m_hand:.9g}" diaginertia="{Jc:.6g} {Jc:.6g} {Jc:.6g}"/>')
    A(f'          <geom type="ellipsoid" pos="{_f(com_h)}" size="0.045 0.035 0.015" rgba="0.9 0.75 0.65 0.4"/>')
    A('          <site name="hand_c" pos="0 0 0" size="0.002"/>')
    if ar.hand_rest:
        # ulnar side of the hand on the paper: a capsule under the palm (skin friction, ASSUMPTION)
        c = com_h + np.array([0.0, 0.0, -(wr[2] + com_h[2]) + 0.004])
        A(f'          <geom name="hand_rest" type="capsule" fromto="{_f(c - 0.01 * d_hand)} {_f(c + 0.01 * d_hand)}" size="0.004" '
          f'contype="2" conaffinity="1" condim="3" friction="{ar.mu_skin:.6g} 0.005 0.0001" '
          f'solref="{_f(cfg.contact.solref)}" solimp="{_f(cfg.contact.solimp)}" group="0"/>')
    ind = "          "
    # the pen handle is opened by the builder with pos relative to the palm: tip - wrist
    A(f'{ind}<!-- handle -->')
    close = ['          <!-- /handle -->', '        </body>', '      </body>', '    </body>']
    # builder writes '<body name="handle" pos="0 0 0" ...>': shift it with a frame body
    A(f'{ind}<body name="grip_frame" pos="{_f(tip - wr)}">')
    A(f'{ind}  <inertial pos="0 0 0" mass="1e-6" diaginertia="1e-12 1e-12 1e-12"/>')
    close = [f'{ind}</body>'] + close[1:]
    return ind + "  ", close


def joint_impedance(cfg: P.Config) -> Dict[str, Tuple[float, float]]:
    """(stiffness, damping) per chain joint at co-contraction cc (N/m or N m/rad; N s/m or N m s/rad)."""
    ar = cfg.arm
    cc = ar.cc
    zeta = ar.zeta
    I_w = ar.J_hand
    I_ps = 1.5e-3
    k_fe, k_rud, k_ps = ar.k_wrist_fe * cc, ar.k_wrist_rud * cc, ar.k_ps * cc
    kby = ar.k_base_y if ar.k_base_y > 0 else ar.k_base
    out = {"arm_x": (ar.k_base, ar.b_base), "arm_y": (kby, ar.b_base), "arm_z": (ar.k_base_z, ar.b_base_z),
           "ps": (k_ps, 2 * zeta * math.sqrt(k_ps * I_ps)), "wfe": (k_fe, 2 * zeta * math.sqrt(k_fe * I_w)),
           "wrud": (k_rud, 2 * zeta * math.sqrt(k_rud * I_w))}
    return out


def arm_actuators(cfg: P.Config, A):
    imp = joint_impedance(cfg)
    for j in ARM_JOINTS:
        k, b = imp[j]
        A(f'    <general name="{j}_p" joint="{j}" gainprm="{k:.9g}" biastype="affine" biasprm="0 {-k:.9g} 0"/>')
        A(f'    <general name="{j}_v" joint="{j}" gainprm="{b:.9g}" biastype="affine" biasprm="0 0 {-b:.9g}"/>')
        A(f'    <motor name="{j}_tau" joint="{j}"/>')


# ================================================================================================ planning and drive
def _joint_addrs(pm, names):
    return [pm.jnt_qadr(n) for n in names], [pm.jnt_dadr(n) for n in names]


def tip_fk(pm, q_arm: np.ndarray) -> np.ndarray:
    m = pm.m
    d = mujoco.MjData(m)
    qa, _ = _joint_addrs(pm, ARM_JOINTS)
    d.qpos[:] = pm.d.qpos0 if hasattr(pm.d, "qpos0") else m.qpos0
    for i, a in enumerate(qa):
        d.qpos[a] = q_arm[i]
    mujoco.mj_kinematics(m, d)
    return d.site_xpos[pm.ids["site:tip"]].copy()


def plan(pm, t: np.ndarray, target: np.ndarray, split_hz: float = 1.0, grid_dt: float = 1e-3, return_grid: bool = False):
    """Joint trajectories (n, 6) of the arm for the tip path `target` (n, 3) (page frame, absolute).
    The slow part (< split_hz) goes to the arm base (x, y); the letters and the height to the wrist, the forearm
    rotation and the base z (Newton IK on a 1 kHz grid with the grip undeflected, then interpolated)."""
    from scipy.signal import butter, sosfiltfilt
    m = pm.m
    d = mujoco.MjData(m)
    mujoco.mj_resetData(m, d)
    qa, _ = _joint_addrs(pm, ARM_JOINTS)
    s_tip = pm.ids["site:tip"]
    tg = np.arange(t[0], t[-1] + grid_dt, grid_dt)
    P0 = np.column_stack([np.interp(tg, t, target[:, j]) for j in range(3)])
    mujoco.mj_kinematics(m, d)
    p_nom = d.site_xpos[s_tip].copy()
    dp = P0 - p_nom
    sos = butter(2, split_hz, fs=1.0 / grid_dt, output="sos")
    low = sosfiltfilt(sos, dp, axis=0)
    Q = np.zeros((len(tg), 6))
    q = np.zeros(6)
    jac = np.zeros((3, m.nv))
    _, da = _joint_addrs(pm, ARM_JOINTS)
    W = np.diag([0.0, 0.0, 1.0, 0.4, 1.0, 1.0])       # free variables: base z, ps, fe, rud
    for i in range(len(tg)):
        q[0], q[1] = low[i, 0], low[i, 1]
        for it in range(3):
            for k, a in enumerate(qa):
                d.qpos[a] = q[k]
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            r = P0[i] - d.site_xpos[s_tip]
            if it > 0 and np.linalg.norm(r) < 1e-8:
                break
            mujoco.mj_jacSite(m, d, jac, None, s_tip)
            J = jac[:, da]
            JW = J @ W
            dq = W @ JW.T @ np.linalg.solve(JW @ JW.T + 1e-10 * np.eye(3), r)
            q = q + dq
        Q[i] = q
    if return_grid:
        return tg, Q
    Qs = np.column_stack([np.interp(t, tg, Q[:, j]) for j in range(6)])
    return Qs


class ArmDrive:
    """Per-step writer controller of the 'arm' hand: equilibrium trajectory (position + velocity servos), feedforward
    torques (inverse dynamics of arm + pen, writing force, expected drag) and tremor torques."""

    def __init__(self, pm, scn, dt: float, tremor: Optional[Dict[str, np.ndarray]] = None, drag_comp: bool = True):
        self.pm = pm
        m = pm.m
        cfg = pm.cfg
        t = np.asarray(scn.t)
        if abs((t[1] - t[0]) - dt) > 1e-12:
            tn = np.arange(0.0, t[-1] + 0.5 * dt, dt)
        else:
            tn = t
        n = len(tn)
        self.n = n
        pref = np.asarray(scn.pref)
        tgt = np.column_stack([np.interp(tn, t, pref[:, 0]), np.interp(tn, t, pref[:, 1]),
                               pm.info["z0"] + np.interp(tn, t, pref[:, 2])])
        # joint plan on a 1 kHz grid, then a cubic spline gives smooth positions, velocities and accelerations at the
        # simulation step (differentiating a linearly interpolated plan at 25 us would give acceleration spikes)
        from scipy.interpolate import CubicSpline
        if getattr(scn, "arm_plan", None) is not None:
            tg, Qg = scn.arm_plan
        else:
            tg, Qg = plan(pm, tn, tgt, return_grid=True)
        cs = CubicSpline(tg, Qg, axis=0)
        Q, Qd, Qdd = cs(tn), cs(tn, 1), cs(tn, 2)
        self.Q, self.Qd = Q, Qd
        # inverse dynamics on a 1 kHz grid (pen rigid in the grip), interpolated
        d = mujoco.MjData(m)
        qa, da = _joint_addrs(pm, ARM_JOINTS)
        step = max(int(round(1e-3 / dt)), 1)
        idx = np.arange(0, n, step)
        TAU = np.zeros((len(idx), 6))
        jac = np.zeros((3, m.nv))
        s_tip = pm.ids["site:tip"]
        fpush = np.interp(tn, t, np.asarray(scn.fpush))
        v_int = np.gradient(tgt[:, :2], dt, axis=0)
        # the internal model has no paper and no limits: constraints off during the inverse dynamics
        flags0 = m.opt.disableflags
        m.opt.disableflags = flags0 | int(mujoco.mjtDisableBit.mjDSBL_CONSTRAINT)
        mu_eff = cfg.contact.mu_skid * pm.info["N_skid0"] / max(cfg.N0, 1e-9) + cfg.contact.mu_ball * pm.info["N_ball0"] / max(cfg.N0, 1e-9)
        for r, k in enumerate(idx):
            mujoco.mj_resetData(m, d)
            for j, a in enumerate(qa):
                d.qpos[a] = Q[k, j]
                d.qvel[da[j]] = Qd[k, j]
                d.qacc[da[j]] = Qdd[k, j]
            mujoco.mj_inverse(m, d)
            tau = np.array([d.qfrc_inverse[a] for a in da])
            # writing force: the hand pushes the pen down with fpush and forward against the drag
            mujoco.mj_jacSite(m, d, jac, None, s_tip)
            J = jac[:, da]
            F = np.array([0.0, 0.0, -fpush[k]])
            if drag_comp:
                v = v_int[k]
                sp = np.linalg.norm(v)
                if sp > 1e-4:
                    F[:2] += mu_eff * fpush[k] * v / sp
            tau += J.T @ F
            TAU[r] = tau
        m.opt.disableflags = flags0
        self.TAU = np.column_stack([np.interp(np.arange(n), idx, TAU[:, j]) for j in range(6)])
        if tremor is not None:
            self.TAU[:, 3] += tremor.get("ps", 0.0)[:n] if np.ndim(tremor.get("ps", 0.0)) else 0.0
            self.TAU[:, 4] += tremor.get("fe", 0.0)[:n] if np.ndim(tremor.get("fe", 0.0)) else 0.0
            self.TAU[:, 5] += tremor.get("rud", 0.0)[:n] if np.ndim(tremor.get("rud", 0.0)) else 0.0
            arm_t = tremor.get("arm", None)
            if arm_t is not None and np.ndim(arm_t):
                # arm-level tremor force along the page y (ASSUMPTION direction)
                self.TAU[:, 1] += arm_t[:n]
        self.ap = [pm.ids[f"act:{j}_p"] for j in ARM_JOINTS]
        self.av = [pm.ids[f"act:{j}_v"] for j in ARM_JOINTS]
        self.at = [pm.ids[f"act:{j}_tau"] for j in ARM_JOINTS]
        self.idx = np.array(self.ap + self.av + self.at, dtype=np.int64)
        self.ctl = np.ascontiguousarray(np.column_stack([Q, Qd, self.TAU]))
        # push force on the pen is exerted by the hand (through the grip): no external push
        self.fpush = fpush

    def step(self, k: int):
        self.pm.d.ctrl[self.idx] = self.ctl[min(k, self.n - 1)]


# ================================================================================================ linear tip impedance
def tip_frf(pm, freqs: np.ndarray, directions=("x", "y", "z"), lifted: bool = True) -> Dict[str, np.ndarray]:
    """Driving-point compliance of the pen tip (m/N) at `freqs` from a force applied at the tip, by linearising the
    model (mjd_transitionFD) about the rest state.  lifted: the paper contact is removed (the ball and skid do not
    touch), so the result is the hand + grip + pen impedance (the HAP-26 measurement condition: stylus in the air)."""
    m, d = pm.m, pm.d
    from . import builder as B
    B.reset(pm)
    if lifted:
        # raise everything: move the hand/arm base up by 5 mm so no contact is active
        for nm in ("hand_z", "arm_z"):
            if pm.has("jnt:" + nm):
                d.qpos[pm.jnt_qadr(nm)] = 5e-3
                a = pm.ids.get("act:arm_p_z", pm.ids.get("act:arm_z_p"))
                if a is not None:
                    d.ctrl[a] = 5e-3
    for nm in ARM_JOINTS:
        if pm.has(f"act:{nm}_p"):
            d.ctrl[pm.ids[f"act:{nm}_p"]] = d.qpos[pm.jnt_qadr(nm)]
    mujoco.mj_forward(m, d)
    nv = m.nv
    nx = 2 * nv + m.na
    Amat = np.zeros((nx, nx))
    mujoco.mjd_transitionFD(m, d, 1e-7, True, Amat, None, None, None)
    dt = m.opt.timestep
    s_tip = pm.ids["site:tip"]
    jac = np.zeros((3, nv))
    mujoco.mj_jacSite(m, d, jac, None, s_tip)
    # input: generalized force J^T F enters the velocity update as dt M^-1 J^T F
    Minv = np.zeros((nv, nv))
    mujoco.mj_solveM(m, d, Minv, np.eye(nv))
    out = {}
    z = np.exp(1j * 2 * np.pi * np.asarray(freqs) * dt)
    for di, dn in enumerate(("x", "y", "z")):
        if dn not in directions:
            continue
        e = np.zeros(3)
        e[di] = 1.0
        Bv = np.zeros(nx)
        Bv[nv:2 * nv] = dt * (Minv @ (jac.T @ e))
        Cp = np.zeros(nx)
        Cp[:nv] = jac[di]                       # tip displacement along the same direction (position part)
        H = np.array([Cp @ np.linalg.solve(zz * np.eye(nx) - Amat, Bv) for zz in z])
        out[dn] = H
    B.reset(pm)
    return out


def _linearise_lifted(pm):
    """A (discrete transition), jacobian of the tip, dt and M^-1 at the lifted rest state (no paper contact)."""
    m, d = pm.m, pm.d
    from . import builder as B
    B.reset(pm)
    for nm in ("hand_z", "arm_z"):
        if pm.has("jnt:" + nm):
            d.qpos[pm.jnt_qadr(nm)] = 5e-3
            a = pm.ids.get("act:arm_p_z", pm.ids.get("act:arm_z_p"))
            if a is not None:
                d.ctrl[a] = 5e-3
    for nm in ARM_JOINTS:
        if pm.has(f"act:{nm}_p"):
            d.ctrl[pm.ids[f"act:{nm}_p"]] = d.qpos[pm.jnt_qadr(nm)]
    mujoco.mj_forward(m, d)
    nv = m.nv
    nx = 2 * nv + m.na
    Amat = np.zeros((nx, nx))
    mujoco.mjd_transitionFD(m, d, 1e-7, True, Amat, None, None, None)
    jac = np.zeros((3, nv))
    mujoco.mj_jacSite(m, d, jac, None, pm.ids["site:tip"])
    Minv = np.zeros((nv, nv))
    mujoco.mj_solveM(m, d, Minv, np.eye(nv))
    return Amat, jac, m.opt.timestep, Minv


def torque_frf(pm, freqs: np.ndarray, joints=("ps", "wfe", "wrud", "arm_y"), output: str = "tip") -> Dict[str, np.ndarray]:
    """Pen-tip displacement (page x, y, z; m) per unit generalized force at each chain joint (N m, or N for the arm
    base slides) at `freqs`, pen lifted (linearisation about the rest state, modal form).  output='joint' returns the
    driving-point response of the same joint instead (rad per N m), shape (nf, 1).  CALC on the SIM model."""
    from . import builder as B
    Amat, jac, dt, Minv = _linearise_lifted(pm)
    nv = pm.m.nv
    nx = Amat.shape[0]
    lam, V = np.linalg.eig(Amat)
    z = np.exp(1j * 2 * np.pi * np.asarray(freqs, float) * dt)
    out = {}
    for j in joints:
        e = np.zeros(nv)
        e[pm.jnt_dadr(j)] = 1.0
        Bv = np.zeros(nx)
        Bv[nv:2 * nv] = dt * (Minv @ e)
        w = np.linalg.solve(V, Bv.astype(complex))
        CV = jac @ V[:nv, :] if output == "tip" else V[[pm.jnt_dadr(j)], :]
        out[j] = np.einsum("in,fn,n->fi", CV, 1.0 / (z[:, None] - lam[None, :]), w)
    B.reset(pm)
    return out


def hap26_compliance(f, k1=575.0, b1=1.3, M=0.21, k2=170.0, b2=11.0):
    s = 2j * np.pi * np.asarray(f, float)
    return (M * s ** 2 + (b1 + b2) * s + k1 + k2) / (b1 * M * s ** 3 + (b1 * b2 + k1 * M) * s ** 2 + (b2 * k1 + b1 * k2) * s + k1 * k2)


def calibrate_to_h1(cfg: P.Config, r_rot: float = 0.5, freqs: Optional[np.ndarray] = None, maxiter: int = 1500,
                    log=None) -> Dict:
    """Fit the arm's joint impedance so that the pen-tip driving-point compliance (pen in the air, nose rigid) matches the
    H1 hand model's (HAP-26 lumped arm + the same two-zone grip + the same pen) over 0.6-20 Hz in x, y and z (SIM fit;
    complex relative error).  Free: stiffness multipliers of wrist flexion-extension, radial-ulnar deviation and
    pronation-supination (co-contraction), their damping ratio, the arm-base stiffness per page axis and its damping.
    A penalty keeps the multipliers within 0.5-8 x the passive values (HAP-32) and the base within 50-3000 N/m.
    The anatomy (masses, inertias, geometry) stays as set.  Returns the fitted Arm values and the fit quality."""
    from scipy.optimize import minimize
    from . import builder as B
    freqs = np.asarray(freqs if freqs is not None else [0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0])
    cfg_h1 = P.h1_check_config(r_rot).replace(nose_on=False, contact=cfg.contact)
    Hh = tip_frf(B.build(cfg_h1), freqs)
    names = ["m_fe", "m_rud", "m_ps", "zeta", "k_bx", "k_by", "k_bz", "b_b", "b_bz"]
    lo = np.log([0.5, 0.5, 0.5, 0.1, 50, 50, 50, 1, 1])
    hi = np.log([8.0, 8.0, 8.0, 2.0, 3000, 3000, 3000, 100, 200])

    def arm_of(x):
        v = dict(zip(names, np.exp(x)))
        a = replace(cfg.arm, cc=1.0, zeta=v["zeta"], k_wrist_fe=cfg.arm.k_wrist_fe * v["m_fe"],
                    k_wrist_rud=cfg.arm.k_wrist_rud * v["m_rud"], k_ps=cfg.arm.k_ps * v["m_ps"], k_base=v["k_bx"],
                    b_base=v["b_b"], k_base_z=v["k_bz"], b_base_z=v["b_bz"])
        a.k_base_y = v["k_by"]
        return a, v

    def cost(x):
        pen = float(np.sum(np.clip(lo - x, 0, None) ** 2 + np.clip(x - hi, 0, None) ** 2)) * 10.0
        a, _ = arm_of(np.clip(x, lo - 1, hi + 1))
        try:
            pm = B.build(cfg.replace(arm=a, hand=replace(cfg.hand, r_rot=r_rot), nose_on=False))
            H = tip_frf(pm, freqs)
        except Exception:
            return 1e6
        e = 0.0
        for dn in ("x", "y", "z"):
            e += np.mean(np.abs(H[dn] - Hh[dn]) ** 2 / np.abs(Hh[dn]) ** 2)
        return float(e / 3.0) + pen

    x0 = np.log([2.0, 2.0, 2.0, 0.5, 400.0, 400.0, 600.0, 11.0, 18.0])
    res = minimize(cost, x0, method="Nelder-Mead", options={"maxiter": maxiter, "maxfev": maxiter, "xatol": 1e-3, "fatol": 1e-7})
    res2 = minimize(cost, res.x, method="Nelder-Mead", options={"maxiter": maxiter, "maxfev": maxiter, "xatol": 1e-4, "fatol": 1e-8})
    a, v = arm_of(res2.x)
    pm = B.build(cfg.replace(arm=a, hand=replace(cfg.hand, r_rot=r_rot), nose_on=False))
    H = tip_frf(pm, freqs)
    rel = {dn: (np.abs(H[dn]) / np.abs(Hh[dn]) - 1.0).tolist() for dn in ("x", "y", "z")}
    ph = {dn: (np.angle(H[dn] / Hh[dn], deg=True)).tolist() for dn in ("x", "y", "z")}
    err = math.sqrt(max(res2.fun, 0.0))
    out = {"multipliers": {k: float(val) for k, val in v.items()},
           "arm": {"k_wrist_fe": a.k_wrist_fe, "k_wrist_rud": a.k_wrist_rud, "k_ps": a.k_ps, "zeta": a.zeta,
                   "k_base_x": a.k_base, "k_base_y": a.k_base_y, "k_base_z": a.k_base_z, "b_base": a.b_base,
                   "b_base_z": a.b_base_z},
           "rms_rel_error": err, "freqs": freqs.tolist(), "mag_rel_error": rel, "phase_error_deg": ph,
           "H_arm": {dn: np.abs(H[dn]).tolist() for dn in H}, "H_h1": {dn: np.abs(Hh[dn]).tolist() for dn in Hh},
           "hap26": np.abs(hap26_compliance(freqs)).tolist(), "nfev": int(res.nfev + res2.nfev)}
    if log:
        log(f"arm calibration: rms rel error {err:.3f}, {out['arm']}")
    return out
