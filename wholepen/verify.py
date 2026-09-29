r"""Simulator checks for every new device (SIM against CALC closed forms; ASME V&V 40 code/calculation verification).

  cmg_torque      a scissored pair on a welded base: the base's reaction torque while the gimbals turn at a set rate
                  equals -2 h delta' cos(delta) about the output axis (closed form), and the off-axis torque cancels
  cmg_energy      the same pair with free gimbals on a free-floating base (no actuators, no damping): kinetic energy and
                  angular momentum are conserved (drift over 1 s at the study's 50 us step and at 25 us)
  tmd_closed      the tuned mass on a base driven sinusoidally: its stroke per base motion equals the closed form
                  |k + j c w| / |k - m w^2 + j c w| - 1 (relative motion), at 3 frequencies
  collar_modes    the pen hanging in the collar (collar welded, pen lifted, no gravity): the free rocking frequency
                  equals sqrt(K_c / J_pivot) (closed form from the model's own inertia about the pivot)
  collar_energy   the same, undamped: energy conserved
  sled_static     a constant force on the H1 hand (pen lifted): the static displacement equals F / k_arm
  collar_v2_transmission  the V2 collar in the full model driven by a prescribed sine: the ink's motion against the
                  linear model the controller uses
  dt_convergence  one closed-loop collar case at 50 us and 25 us: tip tremor agrees
Evidence status: SIMULATION checked against CALCULATION.
"""
from __future__ import annotations

import math
from typing import Dict

import mujoco
import numpy as np

from . import ROOT  # noqa: F401
from . import devices as DV


def _pair_model(gt: DV.CMGTail, dt: float, free_base: bool, actuated: bool) -> str:
    lines = []
    A = lines.append
    A('<mujoco model="cmg_check">')
    A(f'  <option timestep="{dt:.9g}" gravity="0 0 0" integrator="implicitfast"/>')
    A('  <worldbody>')
    A('    <body name="base" pos="0 0 0">')
    if free_base:
        A('      <freejoint name="base_free"/>')
    A('      <inertial pos="0 0 0" mass="0.1" diaginertia="2e-4 2e-4 5e-5"/>')
    A('      <site name="base_s" pos="0 0 0"/>')
    gt2 = DV.CMGTail(**{k: getattr(gt, k) for k in ("mode", "r_o", "r_i", "thick", "rpm", "delta_max", "rate_max",
                                                     "tau_g_max", "kv_g", "J_frame", "m_frame", "spin_kv")})
    gt2.z = 0.0
    body = []
    gt2.mjcf_handle(body.append, "      ", None, {})
    if not actuated:
        body = [ln.replace('damping="1e-6"', 'damping="0"').replace('damping="1e-4"', 'damping="0"') for ln in body]
    lines += body
    A('    </body>')
    A('  </worldbody>')
    if actuated:
        A('  <actuator>')
        gt2.mjcf_actuators(A, None, {})
        A('  </actuator>')
    A('  <sensor><torque name="tq" site="base_s"/></sensor>')
    A('</mujoco>')
    return "\n".join(lines), gt2


def cmg_torque(gt: DV.CMGTail = None, dt: float = 50e-6, rate: float = 5.0, T: float = 0.12) -> Dict:
    gt = gt or DV.CMGTail(mode="turret")
    xml, g2 = _pair_model(gt, dt, free_base=False, actuated=True)
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    w = g2.rpm * 2 * math.pi / 60
    sp = [m.jnt_dofadr[m.joint(f"gt0{j}_s").id] for j in (0, 1)]
    gq = [m.jnt_qposadr[m.joint(f"gt0{j}_g").id] for j in (0, 1)]
    for j, s in enumerate((1.0, -1.0)):
        d.qvel[sp[j]] = s * w
        d.ctrl[m.actuator(f"gt0{j}_sv").id] = s * w
    errs = []
    offs = []
    n = int(T / dt)
    for k in range(n):
        d.ctrl[m.actuator("gt00_gv").id] = rate
        d.ctrl[m.actuator("gt01_gv").id] = -rate
        mujoco.mj_step(m, d)
        if k > n // 3:
            tq = d.sensordata[0:3].copy()          # torque on the base from the world, in the site frame (= -reaction)
            dl = d.qpos[gq[0]]
            dld = d.qvel[m.jnt_dofadr[m.joint("gt00_g").id]]
            expected = 2 * g2.h * dld * math.cos(dl)
            errs.append(abs(abs(tq[0]) - abs(expected)) / max(abs(expected), 1e-12))
            offs.append(math.hypot(tq[1], tq[2]) / max(abs(expected), 1e-12))
    return {"h_Nms": g2.h, "rate": rate, "rel_err_max": float(max(errs)), "offaxis_rel_max": float(max(offs)),
            "label": "SIM against CALC (tau = 2 h delta' cos delta)"}


def cmg_energy(gt: DV.CMGTail = None, dt: float = 50e-6, T: float = 1.0) -> Dict:
    gt = gt or DV.CMGTail(mode="turret")
    xml, g2 = _pair_model(gt, dt, free_base=True, actuated=False)
    m = mujoco.MjModel.from_xml_string(xml)
    m.opt.enableflags |= int(mujoco.mjtEnableBit.mjENBL_ENERGY)
    d = mujoco.MjData(m)
    w = g2.rpm * 2 * math.pi / 60
    for j, s in enumerate((1.0, -1.0)):
        d.qvel[m.jnt_dofadr[m.joint(f"gt0{j}_s").id]] = s * w
    d.qvel[3:6] = [0.5, -0.3, 0.2]            # base angular velocity (rad/s)
    mujoco.mj_forward(m, d)
    E0 = d.energy[1]
    L0 = _angmom(m, d)
    n = int(T / dt)
    Emax = 0.0
    Lmax = 0.0
    for k in range(n):
        mujoco.mj_step(m, d)
        Emax = max(Emax, abs(d.energy[1] - E0) / E0)
        Lmax = max(Lmax, float(np.linalg.norm(_angmom(m, d) - L0)) / max(float(np.linalg.norm(L0)), 1e-12))
    return {"dt": dt, "E0_J": float(E0), "E_drift_rel_max": Emax, "L_drift_rel_max": Lmax,
            "label": "SIM (free gimbals, free base, no damping): energy and angular momentum conservation"}


def _angmom(m, d):
    """Total angular momentum about the world origin."""
    Ltot = np.zeros(3)
    for b in range(1, m.nbody):
        mass = m.body_mass[b]
        xc = d.xipos[b]
        v6 = np.zeros(6)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, b, v6, 0)
        R = d.ximat[b].reshape(3, 3)
        I = R @ np.diag(m.body_inertia[b]) @ R.T
        Ltot += I @ v6[0:3] + mass * np.cross(xc, v6[3:6])
    return Ltot


def tmd_closed(m_: float = 0.040, f_tune: float = 6.0, zeta: float = 0.08, dt: float = 50e-6) -> Dict:
    k = m_ * (2 * math.pi * f_tune) ** 2
    c = 2 * zeta * math.sqrt(k * m_)
    rows = []
    for f in (4.0, 6.0, 9.0):
        xml = f'''<mujoco><option timestep="{dt}" gravity="0 0 0" integrator="implicitfast"/>
<worldbody><body name="b"><joint name="bx" type="slide" axis="1 0 0"/><inertial pos="0 0 0" mass="1" diaginertia="1e-3 1e-3 1e-3"/>
<body name="t"><joint name="tx" type="slide" axis="1 0 0" stiffness="{k}" damping="{c}"/><inertial pos="0 0 0" mass="{m_}" diaginertia="1e-6 1e-6 1e-6"/></body>
</body></worldbody>
<actuator><position name="p" joint="bx" kp="4e6" kv="4e3"/></actuator></mujoco>'''
        mm = mujoco.MjModel.from_xml_string(xml)
        dd = mujoco.MjData(mm)
        w = 2 * math.pi * f
        X = 1e-3
        n = int(4.0 / dt)
        rel = []
        base = []
        for kk in range(n):
            t = kk * dt
            dd.ctrl[0] = X * math.sin(w * t)
            mujoco.mj_step(mm, dd)
            if t > 2.5:
                rel.append(dd.qpos[1])
                base.append(dd.qpos[0])
        amp_rel = (max(rel) - min(rel)) / 2
        amp_b = (max(base) - min(base)) / 2
        expected = abs((k + 1j * c * w) / (k - m_ * w * w + 1j * c * w) - 1.0)
        rows.append({"f": f, "rel_per_base_sim": amp_rel / amp_b, "rel_per_base_closed": expected,
                     "err": abs(amp_rel / amp_b - expected) / expected})
    return {"rows": rows, "err_max": max(r["err"] for r in rows), "label": "SIM against CALC (2-DOF absorber transmissibility)"}


def collar_modes(col: DV.Collar = None, dt: float = 50e-6, undamped: bool = True) -> Dict:
    """The Rev J pen hanging in the collar with the collar welded (hand and grip removed), pen lifted, no gravity."""
    from sim2j import revj as RJ
    col = col or DV.Collar(tau_max=0.0)
    if undamped:
        col = DV.Collar(**{**col.__dict__, "c_c": 0.0, "tau_max": 0.0})
    cfg = RJ.config(hand_model="h1", heel=True, endcap=False, dt=dt)
    pm = DV.build(cfg, collar=col)
    xml = pm.xml
    # weld the collar: remove the grip joints (the collar then belongs to the hand) and the hand's slides
    import re
    xml = re.sub(r'\s*<joint name="grip_[^>]*/>', "", xml)
    xml = re.sub(r'\s*<joint name="hand_[xyz]"[^>]*/>', "", xml)
    xml = re.sub(r'\s*<general name="arm_[pv]_[xyz]"[^>]*/>', "", xml)
    xml = re.sub(r'\s*<motor name="arm_f_[xyz]"[^>]*/>', "", xml)
    xml = xml.replace('damping="0.01"', 'damping="0"')
    m = mujoco.MjModel.from_xml_string(xml)
    m.opt.enableflags |= int(mujoco.mjtEnableBit.mjENBL_ENERGY)
    # lock the nose and refill (rigid pen) so the mode is the pen's rocking alone
    for jn in ("nose_1", "nose_2", "refill_s"):
        j = m.joint(jn).id
        m.jnt_stiffness[j] = 1e3
        m.dof_damping[m.jnt_dofadr[j]] = 0.0
    d = mujoco.MjData(m)
    j1 = m.joint("piv_1").id
    q1 = m.jnt_qposadr[j1]
    v1 = m.jnt_dofadr[j1]
    d.qpos[q1] = 0.01
    mujoco.mj_forward(m, d)
    # inertia about the pivot axis from the mass matrix (the pivot dof's diagonal entry, nose locked by stiffness)
    M = np.zeros((m.nv, m.nv))
    mujoco.mj_fullM(m, M, d.qM)
    J = M[v1, v1]
    f_closed = math.sqrt(col.K_c / J) / (2 * math.pi)
    E0 = d.energy[0] + d.energy[1]
    ts, qs = [], []
    n = int(3.0 / dt)
    Emax = 0.0
    for k in range(n):
        mujoco.mj_step(m, d)
        ts.append(k * dt)
        qs.append(d.qpos[q1])
        Emax = max(Emax, abs(d.energy[0] + d.energy[1] - E0) / max(abs(E0), 1e-12))
    qs = np.array(qs)
    zc = np.flatnonzero((qs[:-1] < 0) & (qs[1:] >= 0))
    f_sim = (len(zc) - 1) / (ts[zc[-1]] - ts[zc[0]]) if len(zc) > 2 else float("nan")
    return {"J_pivot_kg_m2": float(J), "f_closed_Hz": f_closed, "f_sim_Hz": float(f_sim),
            "rel_err": abs(f_sim - f_closed) / f_closed, "E_drift_rel_max": Emax,
            "label": "SIM against CALC (rocking frequency sqrt(K_c/J)); energy conservation, undamped"}


def sled_static(F: float = 0.5, dt: float = 50e-6) -> Dict:
    """Constant force on the H1 hand body, pen lifted: displacement F / k_arm (the grip carries no load: the pen is
    free)."""
    from sim2j import revj as RJ
    cfg = RJ.config(hand_model="h1", heel=True, endcap=False, dt=dt)
    pm = DV.build(cfg)
    m, d = pm.m, pm.d
    mujoco.mj_resetData(m, d)
    bh = pm.ids["body:hand"]
    jx = pm.jnt_qadr("hand_x")
    for nm in ("x", "y", "z"):
        d.ctrl[pm.ids[f"act:arm_p_{nm}"]] = 0.0
        d.ctrl[pm.ids[f"act:arm_v_{nm}"]] = 0.0
    n = int(3.0 / dt)
    for k in range(n):
        d.xfrc_applied[bh, 0] = F
        mujoco.mj_step(m, d)
    x = float(d.qpos[jx])
    k_arm = pm.cfg.hand.k_arm
    return {"x_sim_m": x, "x_closed_m": F / k_arm, "rel_err": abs(x - F / k_arm) / (F / k_arm),
            "label": "SIM against CALC (static F / k_arm)"}


def collar_v2_transmission(f: float = 6.0, amp: float = 0.05, T: float = 2.5) -> Dict:
    """The V2 collar in the full closed-loop model (H1 hand, pen resting on the paper, no tremor, nose held): the
    servo's reference follows a prescribed sine about t2 (tilt plane) or t1 (sideways); the ink's peak-to-peak motion
    against the linear model's ink response (lin.py, the controller's internal model) at the same frequency."""
    from dataclasses import replace
    from stabpen import signals as sg
    from sim2j import et as ET, tasks as TK
    from . import cases as CS, control as C, stepper as WS
    pv = CS.PenVariant("collar", collar=dict(z_p=0.050))
    pm = pv.build()
    case = TK.WriterCase(100, text="r", pre_s=T)
    n = int(T / TK.SIM_DT)
    case.t = case.t[:n]; case.intended = case.intended[:n]; case.hand_path = case.hand_path[:n]
    it = case.written.intended
    case.written.intended = sg.Intended(it.t[:n], it.xy[:n], it.pen_down[:n], it.lift[:n], [])
    scn = case.scenario()
    col = pm.info["collar"]
    ex = {"z_p": col["z_p"], "K_c": col["K_c"], "c_c": col["c_c"], "m_c": col["m"], "z_cm": col["z_cm"], "J_c": col["J"],
          "K_s": col["K_s"], "C_s": col["C_s"], "skid_on_collar": col["skid_on_collar"]}
    fr, G = C.internal_model("collar", DV.pen_props(pm), ex, out="ink")
    i = int(np.argmin(np.abs(fr - f)))
    rows = []
    for axis in (1, 0):
        fw = replace(ET.controller("nose", seed=1), reach=1e-9)
        st = WS.WPStepper(pm, scn, fw, C.WPConfig(collar="ff", collar_alloc="full"), task={"f0": f}, mu=0.9, seed=1)

        def law(dev, mode, t, f_est, cap, axis=axis):
            u = np.zeros(2)
            u[axis] = amp * math.sin(2 * math.pi * f * t) * min(1.0, t / 0.5)
            return u
        st.fw._law = law
        st.fw._commit = lambda *a: None
        st.advance(st.n)
        r = st.result()
        m = r["t"] > 1.0
        pp = np.ptp(r.ink()[m][:, :2], axis=0)
        j = 0 if axis == 1 else 1                  # t2 moves the ink along page x, t1 along page y
        sim = float(pp[j] / 2)
        lin = float(abs(G[i, j, axis]) * amp)
        rows.append({"axis": "t2 (tilt plane)" if axis == 1 else "t1 (sideways)", "ink_amp_sim_mm": sim * 1e3,
                     "ink_amp_lin_mm": lin * 1e3, "rel_err": abs(sim - lin) / lin,
                     "contact_share": float(np.mean(r["contact"][m] > 0.5))})
    return {"f": f, "amp_rad": amp, "rows": rows, "err_max": max(r["rel_err"] for r in rows),
            "label": "SIM (full model) against CALC (lin.py V2 ink response, the controller's internal model)"}


def dt_convergence(dts=(50e-6, 25e-6)) -> Dict:
    """One closed-loop case (tuning writer 100, 'return', ET 6 Hz 3 mm, the V2 collar + nose, seed 300) at the study's
    50 us step and at 25 us."""
    from . import cases as CS, control as C
    out = []
    for dt in dts:
        pv = CS.PenVariant(f"collar_dt{int(dt * 1e6)}", collar=dict(z_p=0.050))
        pm = pv.build(dt=dt)
        su = CS.Setup(100, pv, pm, text="return")
        ref = CS.run_case(su, "none", C.WPConfig(), "ET", 6.0, 3e-3, 300, keep=True)
        r0 = ref.pop("_r")
        m = CS.run_case(su, "nose", C.WPConfig(collar="ff"), "ET", 6.0, 3e-3, 300, ref_none=r0)
        out.append({"dt_us": dt * 1e6, "tip_none_mm": ref["tip_tremor_mm"], "tip_collar_nose_mm": m["tip_tremor_mm"],
                    "ink_err_um": m["ink_err_um"], "pivot_peak_rad": m.get("pivot_peak_rad")})
    a, b = out[0], out[-1]
    return {"rows": out, "rel_diff_tip": abs(a["tip_collar_nose_mm"] - b["tip_collar_nose_mm"]) / max(b["tip_collar_nose_mm"], 1e-9),
            "label": "SIM at two steps (each with its own writer adaptation)"}


def run_all(quick: bool = False) -> Dict:
    from . import designs as DS
    d = DS.cmg_design(100, mode="turret")
    gt = DV.CMGTail(mode="turret", r_o=d["rotor_r_o_mm"] * 1e-3, r_i=d["rotor_r_i_mm"] * 1e-3, thick=d["rotor_t_mm"] * 1e-3,
                    rpm=25000.0, fixed_mass=d["fixed_g"] * 1e-3, tau_g_max=0.045)
    out = {"cmg_torque_50us": cmg_torque(gt, 50e-6), "cmg_torque_25us": cmg_torque(gt, 25e-6),
           "cmg_energy_50us": cmg_energy(gt, 50e-6, T=0.3 if quick else 1.0),
           "tmd_closed": tmd_closed(), "collar_modes": collar_modes(), "sled_static": sled_static(),
           "collar_v2_transmission": collar_v2_transmission()}
    if not quick:
        out["cmg_energy_25us"] = cmg_energy(gt, 25e-6, T=1.0)
        out["dt_convergence"] = dt_convergence()
    return out
