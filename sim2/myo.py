r"""Muscle-based check: end-point stiffness and damping of the MyoSuite arm (MyoArm, 63 Hill-type muscles, 38 joints)
holding a pen, at several co-contraction levels (a virtual EXP-I01).

Procedure (every step SIM with MyoSuite 2.12.2's myoarm.xml; the model is read-only, a copy is extended with MjSpec):
  1. writing posture (ASSUMPTION: shoulder elevation 20 deg, plane of elevation 52 deg, elbow 92 deg, forearm
     semi-pronated, wrist slightly extended); thumb, index and middle fingers closed by IK around a 22 mm pen
     (the three distal phalanges 11 mm from a common axis), ring and little finger flexed;
  2. a light pen body (5 g) welded to the three distal phalanges (stiff welds: the finger pads' skin compliance,
     4.4 kN/m per HAP-31, is left out); the measurement point is on the pen 40 mm ahead of the pads' centre (HAP-26
     measured at the stylus point about 4 cm ahead of the fingers);
  3. every muscle activation held at the co-contraction level c (0 ... 0.3) (activation dynamics bypassed: act and ctrl
     set to c); gravity off (forearm supported on the desk); the net joint torque of the posture balanced by a constant
     applied torque, then settled;
  4. static stiffness: +- 0.1 N steps along page x, y, z at the pen point (displacement after 1.5 s) -> 3x3 compliance;
  5. dynamic impedance: random-phase multisine force (0.5-20 Hz) per axis, H1 FRF estimate, fit of a mass-spring-
     damper (the HAP-26 arm part: M, b2, k2) to the point compliance.
Caveats (stated in the report): Hill-type models have no short-range stiffness (history-dependent stiffness of
cross-bridges), so small-perturbation stiffness at co-contraction is underestimated (De Groote et al.; Cui et al.);
MyoArm has joint damping 0.05-1.05 N m s/rad as a model parameter (not muscle-derived); no reflexes; rigid pad welds.
"""
from __future__ import annotations

import math
import os
import time
from typing import Dict, List, Optional

import mujoco
import numpy as np

MYO_XML = "/usr/local/lib/python3.11/dist-packages/myosuite/simhive/myo_sim/arm/myoarm.xml"

POSTURE = dict(elv_angle=0.9, shoulder_elv=0.35, shoulder_rot=0.2, elbow_flexion=1.6, pro_sup=0.6, deviation=0.0,
               flexion=-0.15, mcp4_flexion=1.0, pm4_flexion=1.2, md4_flexion=0.6, mcp5_flexion=1.0, pm5_flexion=1.2,
               md5_flexion=0.6)
FINGER_JOINTS = ["cmc_abduction", "cmc_flexion", "mp_flexion", "ip_flexion", "mcp2_flexion", "mcp2_abduction",
                 "pm2_flexion", "md2_flexion", "mcp3_flexion", "mcp3_abduction", "pm3_flexion", "md3_flexion"]
TIPS = ("distal_thumb", "distph2", "distph3")


def _myo_path():
    try:
        import myosuite
        p = os.path.join(os.path.dirname(myosuite.__file__), "simhive", "myo_sim", "arm", "myoarm.xml")
        if os.path.exists(p):
            return p
    except Exception:
        pass
    return MYO_XML


def enforce_joint_equalities(m, d):
    """Set every joint-coupling equality exactly (MyoArm couples the shoulder-girdle joints and shoulder1_r2 to the
    shoulder elevation / plane of elevation): y - y0 = a0 + a1 (x - x0) + ... + a4 (x - x0)^4."""
    for i in range(m.neq):
        if m.eq_type[i] != mujoco.mjtEq.mjEQ_JOINT or m.eq_obj2id[i] < 0:
            continue
        j1, j2 = m.eq_obj1id[i], m.eq_obj2id[i]
        a1, a2 = m.jnt_qposadr[j1], m.jnt_qposadr[j2]
        x = d.qpos[a2] - m.qpos0[a2]
        c = m.eq_data[i, :5]
        d.qpos[a1] = m.qpos0[a1] + c[0] + c[1] * x + c[2] * x ** 2 + c[3] * x ** 3 + c[4] * x ** 4


def grasp_posture(m, d, r_pen=0.011):
    """Set the posture and close thumb, index and middle around a pen (IK on the finger joints)."""
    from scipy.optimize import least_squares
    names = [m.joint(i).name for i in range(m.njnt)]
    for k, v in POSTURE.items():
        d.qpos[m.jnt_qposadr[names.index(k)]] = v
    enforce_joint_equalities(m, d)
    init = dict(cmc_abduction=0.3, cmc_flexion=0.3, mp_flexion=0.2, ip_flexion=0.1, mcp2_flexion=0.6, mcp2_abduction=0.0,
                pm2_flexion=0.6, md2_flexion=0.3, mcp3_flexion=0.7, mcp3_abduction=0.0, pm3_flexion=0.8, md3_flexion=0.3)
    idx = [m.jnt_qposadr[names.index(j)] for j in FINGER_JOINTS]
    lo = np.array([m.jnt_range[names.index(j)][0] for j in FINGER_JOINTS])
    hi = np.array([m.jnt_range[names.index(j)][1] for j in FINGER_JOINTS])
    x0 = np.clip(np.array([init[j] for j in FINGER_JOINTS]), lo + 1e-3, hi - 1e-3)
    tip_ids = [m.body(b).id for b in TIPS]

    def res(x):
        d.qpos[idx] = x[:12]
        mujoco.mj_kinematics(m, d)
        P = np.array([d.xpos[i] for i in tip_ids])
        c = P.mean(axis=0)
        r = [np.linalg.norm(P[i] - c) - r_pen for i in range(3)]
        # keep the three pads roughly in a plane normal to the pen axis: equal pairwise spacing
        pw = [np.linalg.norm(P[0] - P[1]), np.linalg.norm(P[1] - P[2]), np.linalg.norm(P[0] - P[2])]
        return np.concatenate([np.array(r) * 10, (np.array(pw) - np.mean(pw)) * 5, (x[:12] - x0) * 0.02])

    sol = least_squares(res, x0, bounds=(lo, hi))
    d.qpos[idx] = sol.x
    mujoco.mj_forward(m, d)
    P = np.array([d.xpos[i] for i in tip_ids])
    return {"finger_q": dict(zip(FINGER_JOINTS, sol.x.tolist())), "pad_radius_mm": [float(np.linalg.norm(p - P.mean(0)) * 1e3) for p in P],
            "cost": float(sol.cost)}


def build(level_posture=None, dt=1e-3):
    """MyoArm + a pen welded to the three distal phalanges.  Returns (model, data, info)."""
    path = _myo_path()
    spec = mujoco.MjSpec.from_file(path)
    m0 = spec.compile()
    d0 = mujoco.MjData(m0)
    ginfo = grasp_posture(m0, d0)
    qpos_grasp = d0.qpos.copy()
    tip_ids = [m0.body(b).id for b in TIPS]
    P = np.array([d0.xpos[i] for i in tip_ids])
    c = P.mean(axis=0)
    # pen axis: normal of the pads' plane, oriented from the hand (second metacarpal) toward the pads, then tilted
    n = np.cross(P[1] - P[0], P[2] - P[0])
    n /= np.linalg.norm(n)
    base = d0.xpos[m0.body("secondmc").id]
    if np.dot(c - base, n) < 0:
        n = -n
    tip = c + 0.040 * n
    # add the pen: a free body with a small mass at the pads' centre, a site at the tip
    pen = spec.worldbody.add_body(name="pen", pos=c.tolist())
    pen.add_freejoint(name="pen_free")
    pen.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, size=[0.011, 0.0, 0.0], fromto=(np.zeros(3) - 0.06 * n).tolist() + (0.04 * n).tolist(),
                 mass=0.005, contype=0, conaffinity=0, rgba=[0.2, 0.2, 0.7, 0.4])
    pen.add_site(name="pen_tip", pos=(0.040 * n).tolist(), size=[0.002, 0.0, 0.0])
    for b in TIPS:
        spec.add_equality(type=mujoco.mjtEq.mjEQ_WELD, name1="pen", name2=b, objtype=mujoco.mjtObj.mjOBJ_BODY,
                          solref=[2 * dt, 1.0], solimp=[0.95, 0.99, 0.001, 0.5, 2.0])
    spec.option.timestep = dt
    spec.option.gravity = [0.0, 0.0, 0.0]
    m = spec.compile()
    d = mujoco.MjData(m)
    # copy the arm posture; the pen free joint at the pads' centre with identity orientation
    nq0 = m0.nq
    d.qpos[:nq0] = qpos_grasp
    fj = m.joint("pen_free").id
    a = m.jnt_qposadr[fj]
    d.qpos[a:a + 3] = c
    d.qpos[a + 3:a + 7] = [1, 0, 0, 0]
    # weld relative poses from the current configuration
    mujoco.mj_forward(m, d)
    for i in range(m.neq):
        if m.eq_type[i] == mujoco.mjtEq.mjEQ_WELD:
            b1, b2 = m.eq_obj1id[i], m.eq_obj2id[i]
            # relpose of body2 in body1 frame
            R1 = d.xmat[b1].reshape(3, 3)
            p_rel = R1.T @ (d.xpos[b2] - d.xpos[b1])
            q1 = d.xquat[b1].copy()
            q2 = d.xquat[b2].copy()
            q1c = np.array([q1[0], -q1[1], -q1[2], -q1[3]])
            qr = np.zeros(4)
            mujoco.mju_mulQuat(qr, q1c, q2)
            m.eq_data[i, 0:3] = 0.0                     # anchor
            m.eq_data[i, 3:6] = p_rel
            m.eq_data[i, 6:10] = qr
            m.eq_data[i, 10] = 1.0
    info = {"grasp": ginfo, "pads_centre": c.tolist(), "pen_axis": n.tolist(), "pen_tip": tip.tolist(),
            "model": path, "n_muscles": int(m.nu), "n_joints": int(m.njnt), "dt": dt}
    return m, d, info


def _set_activation(m, d, level):
    for i in range(m.nu):
        if m.actuator_dyntype[i] == mujoco.mjtDyn.mjDYN_MUSCLE:
            d.act[m.actuator_actadr[i]] = level
            d.ctrl[i] = level


def _input_matrix(m, d, jac, eps=1e-3):
    """Discrete-time input matrix of a force at the pen point (page x, y, z) by central finite differences of one
    mj_step, in mjd_transitionFD's state convention [dq (tangent), qvel, act]."""
    nv, na = m.nv, m.na
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    st = np.zeros(mujoco.mj_stateSize(m, spec))
    mujoco.mj_getState(m, d, st, spec)
    q0 = d.qpos.copy()
    base = d.qfrc_applied.copy()
    B = np.zeros((2 * nv + na, 3))
    for j in range(3):
        xs = []
        for sgn in (1.0, -1.0):
            mujoco.mj_setState(m, d, st, spec)
            d.qfrc_applied[:] = base + sgn * eps * jac[j, :]
            mujoco.mj_step(m, d)
            dq = np.zeros(nv)
            mujoco.mj_differentiatePos(m, dq, 1.0, q0, d.qpos)
            xs.append(np.concatenate([dq, d.qvel, d.act]))
        B[:, j] = (xs[0] - xs[1]) / (2 * eps)
    mujoco.mj_setState(m, d, st, spec)
    d.qfrc_applied[:] = base
    mujoco.mj_forward(m, d)
    return B


def impedance(level: float, m=None, d=None, info=None, freqs=None, **_) -> Dict:
    """Pen-point driving-point compliance C(j w) of the arm + fingers + pen at co-contraction `level`, by linearising
    MyoArm's discrete dynamics (mjd_transitionFD: muscles with fixed activation, joint damping, soft welds, shoulder
    couplings) about the grasp posture, with the posture's net torque balanced by a constant applied torque.
    Returns the static stiffness matrix (low-frequency limit), per-axis fits of the HAP-26 arm part (M, b, k) over
    0.5-20 Hz, the stability of the linearised posture (spectral radius), and the compliance curves."""
    if m is None:
        m, d, info = build()
    freqs = np.asarray(freqs if freqs is not None else np.concatenate([[0.05, 0.1, 0.2], np.arange(0.5, 30.01, 0.5)]))
    dt = m.opt.timestep
    q_init = d.qpos.copy()
    mujoco.mj_resetData(m, d)
    d.qpos[:] = q_init
    _set_activation(m, d, level)
    d.qvel[:] = 0.0
    mujoco.mj_forward(m, d)
    # balance: constant applied torque = minus the net smooth generalized force (muscles, passive, bias); the
    # constraints (joint couplings, pad welds) are satisfied exactly by the posture, so they carry no force at rest
    d.qfrc_applied[:] = d.qfrc_bias - d.qfrc_passive - d.qfrc_actuator
    mujoco.mj_forward(m, d)
    acc_resid = float(np.max(np.abs(d.qacc)))
    nv, na = m.nv, m.na
    nx = 2 * nv + na
    A = np.zeros((nx, nx))
    mujoco.mjd_transitionFD(m, d, 1e-6, True, A, None, None, None)
    s_tip = m.site("pen_tip").id
    jac = np.zeros((3, nv))
    mujoco.mj_jacSite(m, d, jac, None, s_tip)
    z = np.exp(1j * 2 * np.pi * freqs * dt)
    # modal form: A = V diag(lam) V^-1, so (zI - A)^-1 B = V diag(1/(z - lam)) V^-1 B (one eigendecomposition)
    lam, V = np.linalg.eig(A)
    Bm = _input_matrix(m, d, jac, eps=1e-3)                 # nx x 3, force at the pen point (finite differences)
    W = np.linalg.solve(V, Bm.astype(complex))              # modal inputs, nx x 3
    CV = jac @ V[:nv, :]                                    # 3 x nx modal outputs (pen-point displacement)
    H = np.einsum("in,fn,nj->fij", CV, 1.0 / (z[:, None] - lam[None, :]), W)
    # static (low-frequency) stiffness from the lowest frequency
    C0 = H[0].real
    K = np.linalg.inv(0.5 * (C0 + C0.T))
    w, _ = np.linalg.eigh(K)
    fits = {}
    for i, nm in enumerate("xyz"):
        fits[nm] = {"two_mass_fit": fit_two_mass(freqs, H[:, i, i]),
                    "k_lowfreq_N_per_m": float(1.0 / H[0, i, i].real),
                    "compliance_mag_m_per_N": np.abs(H[:, i, i]).tolist(),
                    "compliance_phase_deg": np.degrees(np.angle(H[:, i, i])).tolist()}
    # unstable (divergent) modes of the linearised posture: |lambda| > 1
    unst = np.where(np.abs(lam) > 1.0 + 1e-9)[0]
    growth = [float(np.log(abs(lam[k])) / dt) for k in unst]
    names = [m.joint(j).name for j in range(m.njnt)]
    dofname = []
    for j in range(m.njnt):
        nd = {0: 6, 1: 3, 2: 1, 3: 1}[m.jnt_type[j]]
        dofname += [names[j] + (f"[{k}]" if nd > 1 else "") for k in range(nd)]
    modes = []
    for k in unst[np.argsort(-np.abs(lam[unst]))][:3]:
        v = np.abs(V[:nv, k]) + np.abs(V[nv:2 * nv, k])
        top = np.argsort(-v)[:3]
        modes.append({"lambda": [float(lam[k].real), float(lam[k].imag)], "growth_per_s": float(np.log(abs(lam[k])) / dt),
                      "tip_share": float(np.linalg.norm(CV[:, k]) / (np.linalg.norm(V[:nv, k]) + 1e-30)),
                      "dofs": [(dofname[t], round(float(v[t] / v.sum()), 2)) for t in top]})
    rho = float(np.max(np.abs(lam)))
    return {"cocontraction": level, "freqs_Hz": freqs.tolist(), "static_K_N_per_m": K.tolist(),
            "static_K_eig_N_per_m": w.tolist(), "static_K_axis_N_per_m": [float(K[i, i]) for i in range(3)],
            "dynamic_fit": fits, "spectral_radius": rho, "stable": bool(rho < 1.0 + 1e-9), "qacc_residual": acc_resid,
            "n_unstable": int(len(unst)), "max_growth_per_s": float(max(growth) if growth else 0.0), "unstable_modes": modes,
            "info": info}


# HAP-26 (Fu & Cavusoglu 2012, Table II, nominal): stylus -(k1 || b1)- M -(k2 || b2)- ground, per axis
HAP26 = {"X": dict(k1=379.5, b1=1.839, M=0.218, k2=78.75, b2=4.645),
         "Y": dict(k1=552.4, b1=3.609, M=0.269, k2=105.3, b2=6.430),
         "Z": dict(k1=769.9, b1=0.776, M=0.204, k2=271.7, b2=18.06)}
H1_TIP = dict(k1=575.0, b1=1.3, M=0.21, k2=170.0, b2=11.0)      # H1 hand at the tip (docs/inertial_stabilisation.md)
# MyoArm world axes (z up; forearm points to -y) -> HAP-26 axes (X left-right, Y up-down, Z fore-aft)
AXIS_MAP = {"x": "X", "y": "Z", "z": "Y"}


def two_mass_compliance(f, k1, b1, M, k2, b2):
    s = 2j * np.pi * np.asarray(f, float)
    return 1.0 / (k1 + b1 * s) + 1.0 / (M * s ** 2 + b2 * s + k2)


def fit_two_mass(freqs, C, band=(1.0, 20.0)) -> Dict:
    """Fit HAP-26's structure (k1, b1, M, k2, b2 > 0) to a driving-point compliance over `band` (complex-log error,
    i.e. magnitude in log units and phase in radians, equally weighted; multi-start)."""
    from scipy.optimize import least_squares
    f = np.asarray(freqs, float)
    msk = (f >= band[0]) & (f <= band[1])
    fv, Cv = f[msk], np.asarray(C)[msk]

    def res(x):
        k1, b1, M, k2, b2 = np.exp(x)
        e = np.log(two_mass_compliance(fv, k1, b1, M, k2, b2) / Cv)
        return np.concatenate([e.real, np.angle(np.exp(1j * e.imag))])

    best = None
    for x0 in ([500, 2, 0.2, 100, 10], [2000, 5, 0.3, 50, 30], [300, 1, 0.1, 300, 5], [5000, 20, 0.5, 20, 60]):
        r = least_squares(res, np.log(x0), bounds=(np.log([1, 1e-3, 1e-3, 1e-2, 1e-2]), np.log([1e6, 1e3, 5, 1e5, 1e3])))
        if best is None or r.cost < best.cost:
            best = r
    k1, b1, M, k2, b2 = np.exp(best.x)
    rms = float(np.sqrt(np.mean(best.fun ** 2)))
    return {"k1_N_per_m": float(k1), "b1_Ns_per_m": float(b1), "M_kg": float(M), "k2_N_per_m": float(k2),
            "b2_Ns_per_m": float(b2), "rms_log_error": rms, "band_Hz": list(band)}


def impedance_table(rows, f_eval=(1.0, 4.0, 8.0, 12.0)) -> List[Dict]:
    """|Z| = 1/|C| (N/m) at the pen point per MyoArm axis and co-contraction, next to HAP-26 (nominal, mapped axis)
    and H1; ratios MyoArm / HAP-26."""
    out = []
    for r in rows:
        f = np.asarray(r["freqs_Hz"])
        for ax in "xyz":
            C = np.asarray(r["dynamic_fit"][ax]["compliance_mag_m_per_N"])
            hp = HAP26[AXIS_MAP[ax]]
            for fe in f_eval:
                z_myo = float(1.0 / np.interp(fe, f, C))
                z_hap = float(1.0 / abs(two_mass_compliance([fe], **hp)[0]))
                z_h1 = float(1.0 / abs(two_mass_compliance([fe], **H1_TIP)[0]))
                out.append({"cocontraction": r["cocontraction"], "axis": ax, "hap26_axis": AXIS_MAP[ax], "f_Hz": fe,
                            "Z_myoarm_N_per_m": z_myo, "Z_hap26_N_per_m": z_hap, "Z_h1_N_per_m": z_h1,
                            "ratio_myo_to_hap26": z_myo / z_hap})
    return out


def study(levels=(0.0, 0.02, 0.05, 0.1, 0.2, 0.3), quick=False, log=print) -> Dict:
    t0 = time.time()
    m, d, info = build()
    rows = []
    for lv in (levels[:2] if quick else levels):
        r = impedance(lv, m, d, info)
        rows.append(r)
        if log:
            fx = r["dynamic_fit"]
            tm = " ".join(f"{ax}: k1 {fx[ax]['two_mass_fit']['k1_N_per_m']:.0f} b1 {fx[ax]['two_mass_fit']['b1_Ns_per_m']:.2f} "
                          f"M {fx[ax]['two_mass_fit']['M_kg']:.3f} k2 {fx[ax]['two_mass_fit']['k2_N_per_m']:.0f} "
                          f"b2 {fx[ax]['two_mass_fit']['b2_Ns_per_m']:.1f} (rms {fx[ax]['two_mass_fit']['rms_log_error']:.2f})"
                          for ax in "xyz")
            log(f"  MyoArm c = {lv:.2f}: unstable modes {r['n_unstable']} (max growth {r['max_growth_per_s']:.2f} /s); "
                f"two-mass fit 1-20 Hz {tm} ({time.time() - t0:.0f} s)")
    tab = impedance_table(rows)
    if log:
        for fe in (4.0, 8.0, 12.0):
            for ax in "xyz":
                zz = [t for t in tab if t["f_Hz"] == fe and t["axis"] == ax]
                log(f"  |Z| {fe:.0f} Hz axis {ax} (HAP-26 {AXIS_MAP[ax]} {zz[0]['Z_hap26_N_per_m']:.0f}, H1 {zz[0]['Z_h1_N_per_m']:.0f} N/m): "
                    + ", ".join(f"c {t['cocontraction']:.2f}: {t['Z_myoarm_N_per_m']:.0f}" for t in zz))
    return {"rows": rows, "info": info, "table": tab, "hap26": HAP26, "h1_tip": H1_TIP, "axis_map": AXIS_MAP,
            "elapsed_s": time.time() - t0}
