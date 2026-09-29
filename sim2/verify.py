r"""Verification of simulator v2 (code and calculation verification in the ASME V&V 40 sense; every result SIM/CALC).

  contact_native   MuJoCo soft contact: static stiffness vs solref/solimp and the effective mass (against the closed
                   form k = m_eff d^2 / ((1 - d) d_w^2 tau^2 zeta^2)), creep in stick (against v = R f / b), sliding
                   force = mu N (elliptic and pyramidal cones), slip onset on an incline (tan alpha = mu), and the pen
                   sliding test (chatter index) over the solver settings
  friction_lugre   the H1 contact law: breakaway force mu_s N, steady sliding mu_k N, pre-sliding stiffness mu_s N /
                   x_pre, and a stick-slip oscillator against the analytic Coulomb (mu_s / mu_k) limit cycle
  convergence      the Rev H case at dt 12.5-100 us (training seed 300): ink error, oracle ratio, path differences
  energy           conservative (drift), damped (dE = damper work) and actuated (dE = actuator work) audits
  gyro             CMG reaction torque against h x omega over spin and gimbal rates; spin energy conservation
  sensors          IMU noise density and ODR against fusion.sensors; MuJoCo's native accelerometer against the
                   kinematic formula; page-sensor latency
"""
from __future__ import annotations

import math
import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Dict, List

import mujoco
import numpy as np

from . import builder as B
from . import params as P
from . import sim as S


def _still(T=0.3, dt=25e-6, N=1.0, vx=0.0, vy=0.0):
    n = int(round(T / dt))
    t = np.arange(n) * dt
    pref = np.zeros((n, 3))
    vref = np.zeros((n, 3))
    ramp = np.clip(t / 0.05, 0, 1)
    pref[:, 0] = vx * np.cumsum(ramp) * dt
    pref[:, 1] = vy * np.cumsum(ramp) * dt
    vref[:, 0] = vx * ramp
    vref[:, 1] = vy * ramp
    return SimpleNamespace(t=t, pref=pref, vref=vref, fpush=np.full(n, N), psi_disp=np.zeros(n), tremor_obj=None,
                           intended=pref[:, :2].copy())


# ============================================================================================ native contact
def _block_model(solref, solimp, mu, impratio=1.0, cone="elliptic", noslip=0, dt=1e-4, incline_deg=0.0, m=0.02,
                 integrator="implicitfast", drive=False):
    """A 20 g sphere (r 2 mm) on an inclined plane (plane geom in the world body; slides along the incline and its
    normal); optional velocity servo on the tangential slide (kv 50 N s/m, implicit) for sliding-force tests."""
    a = math.radians(incline_deg)
    ax = f"{math.cos(a):.12g} 0 {-math.sin(a):.12g}"
    az = f"{math.sin(a):.12g} 0 {math.cos(a):.12g}"
    act = ('<actuator><general name="v" joint="x" gainprm="50" biastype="affine" biasprm="0 0 -50"/></actuator>'
           if drive else "")
    xml = f"""
<mujoco>
  <compiler angle="radian"/>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="{integrator}" cone="{cone}" impratio="{impratio}"
          noslip_iterations="{noslip}"/>
  <worldbody>
    <geom name="floor" type="plane" size="1 1 0.01" euler="0 {a:.12g} 0" friction="{mu} 0.005 0.0001"
          solref="{solref[0]} {solref[1]}" solimp="{' '.join(map(str, solimp))}"/>
    <body name="block" pos="{0.0021 * math.sin(a):.12g} 0 {0.0021 * math.cos(a):.12g}">
      <joint name="x" type="slide" axis="{ax}"/>
      <joint name="z" type="slide" axis="{az}"/>
      <geom type="sphere" size="0.002" mass="{m}" friction="{mu} 0.005 0.0001" solref="{solref[0]} {solref[1]}"
            solimp="{' '.join(map(str, solimp))}"/>
    </body>
  </worldbody>
  {act}
</mujoco>"""
    mm = mujoco.MjModel.from_xml_string(xml)
    return mm, mujoco.MjData(mm)


def native_block_tests(solref=(5e-4, 1.0), solimp=(0.99, 0.999, 1e-4, 0.5, 2.0), mu=0.12, impratio=10.0) -> Dict:
    """Static stiffness, creep in stick, sliding force, slip onset, for one set of contact parameters."""
    out = {"solref": list(solref), "solimp": list(solimp), "mu": mu, "impratio": impratio}
    m = 0.02
    # --- static stiffness under an extra 1 N load (gravity 0.196 N)
    mm, d = _block_model(solref, solimp, mu, impratio, m=m, dt=2.5e-5)
    for k in range(int(0.1 / mm.opt.timestep)):
        mujoco.mj_step(mm, d)
    z0 = d.qpos[1]
    for k in range(int(0.1 / mm.opt.timestep)):
        d.qfrc_applied[1] = -1.0
        mujoco.mj_step(mm, d)
    k_meas = 1.0 / max(z0 - d.qpos[1], 1e-15)
    dmin = solimp[0]
    dw = solimp[1]
    tau, zeta = solref
    k_pred = m * dmin ** 2 / ((1 - dmin) * dw ** 2 * tau ** 2 * zeta ** 2)
    out["static_stiffness_N_per_m"] = {"measured": float(k_meas), "closed_form": float(k_pred)}
    # --- creep: tangential load 0.5 mu N (well inside the cone) on a horizontal plane
    mm, d = _block_model(solref, solimp, mu, impratio, m=m, dt=2.5e-5)
    for k in range(int(0.05 / mm.opt.timestep)):
        mujoco.mj_step(mm, d)
    x0 = d.qpos[0]
    T = 0.2
    Ft = 0.5 * mu * m * 9.81
    for k in range(int(T / mm.opt.timestep)):
        d.qfrc_applied[0] = Ft
        mujoco.mj_step(mm, d)
    v_creep = (d.qpos[0] - x0) / T
    b = 2.0 / (dw * tau)
    R_f = (1 - dmin) / dmin * (1.0 / m) / impratio
    out["creep"] = {"F_t_over_muN": 0.5, "v_creep_m_s": float(v_creep), "closed_form_m_s": float(R_f * Ft / b)}
    for ns in (10,):
        mm, d = _block_model(solref, solimp, mu, impratio, noslip=ns, m=m, dt=2.5e-5)
        for k in range(int(0.05 / mm.opt.timestep)):
            mujoco.mj_step(mm, d)
        x0 = d.qpos[0]
        for k in range(int(T / mm.opt.timestep)):
            d.qfrc_applied[0] = Ft
            mujoco.mj_step(mm, d)
        out["creep"][f"v_creep_noslip{ns}_m_s"] = float((d.qpos[0] - x0) / T)
    # --- sliding force at constant speed (velocity servo on x), elliptic and pyramidal
    for cone in ("elliptic", "pyramidal"):
        mm, d = _block_model(solref, solimp, mu, impratio if cone == "elliptic" else 1.0, cone=cone, m=m, dt=2.5e-5, drive=True)
        d.ctrl[0] = 0.02
        FT, FN, NC = [], [], []
        for k in range(int(0.3 / mm.opt.timestep)):
            mujoco.mj_step(mm, d)
            if k * mm.opt.timestep > 0.15:
                f6 = np.zeros(6)
                ft = 0.0
                fn = 0.0
                for i in range(d.ncon):
                    mujoco.mj_contactForce(mm, d, i, f6)
                    fn += f6[0]
                    ft += math.hypot(f6[1], f6[2])
                FT.append(ft)
                FN.append(fn)
                NC.append(d.ncon)
        # time-averaged friction over time-averaged normal force; the contact can flicker (no contact in some steps
        # when the equilibrium penetration is nanometres and the collision margin is zero)
        out[f"sliding_mu_{cone}"] = float(np.sum(FT) / max(np.sum(FN), 1e-12))
        out[f"sliding_contact_fraction_{cone}"] = float(np.mean(np.array(NC) > 0))
        out[f"sliding_speed_{cone}_m_s"] = float(d.qvel[0])
    # gliding: mean normal gap while sliding against the resting height (Castro et al.: phi ~ (dt + tau) mu |v_t|)
    mm, d = _block_model(solref, solimp, mu, impratio, m=m, dt=2.5e-5, drive=True)
    for k in range(int(0.1 / mm.opt.timestep)):
        mujoco.mj_step(mm, d)
    z_rest = d.qpos[1]
    d.ctrl[0] = 0.02
    zs = []
    ncs = []
    for k in range(int(0.3 / mm.opt.timestep)):
        mujoco.mj_step(mm, d)
        if k * mm.opt.timestep > 0.1:
            zs.append(d.qpos[1] - z_rest)
            ncs.append(d.ncon)
    out["gliding"] = {"mean_gap_um": float(np.mean(zs) * 1e6), "contact_fraction": float(np.mean(np.array(ncs) > 0)),
                      "predicted_um": float((mm.opt.timestep + solref[0]) * mu * 0.02 * 1e6), "v_t_m_s": 0.02}
    # --- slip onset on an incline: slip if tan(alpha) > mu
    res = {}
    for a_deg in (math.degrees(math.atan(mu)) - 2.0, math.degrees(math.atan(mu)) + 2.0):
        mm, d = _block_model(solref, solimp, mu, impratio, incline_deg=a_deg, m=m, dt=2.5e-5)
        for k in range(int(0.05 / mm.opt.timestep)):
            mujoco.mj_step(mm, d)
        x0 = d.qpos[0]
        Tt = 0.2
        for k in range(int(Tt / mm.opt.timestep)):
            mujoco.mj_step(mm, d)
        dx = abs(d.qpos[0] - x0)
        a_pred = 9.81 * max(math.sin(math.radians(a_deg)) - mu * math.cos(math.radians(a_deg)), 0.0)
        res[f"{a_deg:.2f}deg"] = {"displacement_m": float(dx), "predicted_rigid_m": float(0.5 * a_pred * Tt ** 2)}
    out["incline"] = res
    return out


def pen_sliding(settings: List[Dict], speed=0.02, directions=((1, 0), (-1, 0), (0, 1)), T=0.3) -> List[Dict]:
    """The Rev H pen (H1 hand, rigid nose) dragged at constant speed with native contacts: chatter index (std/mean of
    the skid normal force), apparent friction coefficient, contact flicker."""
    rows = []
    for st in settings:
        for (dx, dy) in directions:
            ck = dict(st)
            dt = ck.pop("dt", 25e-6)
            cfg = P.h1_check_config(0.5).replace(contact=P.Contact(model="mujoco", **ck), nose_on=False, dt=dt)
            pm = B.build(cfg)
            r = S.run(pm, _still(T=T, dt=dt, vx=speed * dx, vy=speed * dy))
            msk = r["t"] > 0.12
            Ns = r["Ns"][msk]
            fs = np.hypot(r["fsx"][msk], r["fsy"][msk])
            rows.append({**st, "dt": dt, "dir": [dx, dy], "Ns_mean": float(Ns.mean()), "Ns_cv": float(Ns.std() / max(Ns.mean(), 1e-9)),
                         "mu_apparent": float(fs.mean() / max(Ns.mean(), 1e-9)),
                         "flicker": int(np.sum(np.diff((r["contact"][msk] > 0).astype(int)) != 0)),
                         "tip_z_um": float(r["tipz"][msk].mean() * 1e6)})
    return rows


# ============================================================================================ LuGre law
def lugre_tests(mu_k=0.12, ms=1.3, v_s=0.002, x_pre=1e-5, N=1.0, m=0.02, dt=2.5e-5) -> Dict:
    """Point mass on the paper with the H1 law (normal force given), driven by a spring whose far end moves at v_d:
    breakaway = mu_s N, sliding = mu_k N at v >> v_s, pre-sliding stiffness mu_s N / x_pre; stick-slip period and
    force drop against the analytic Coulomb (mu_s, mu_k) oscillator.  The LuGre update is the one in contact.py."""
    from .contact import PointContact
    pc = PointContact("t", 0, "sphere", 0, 0, mu_k, mu_k * ms, v_s, x_pre)
    out = {}

    def lug(vx):
        vn = abs(vx)
        gv = pc.mu_k + (pc.mu_s - pc.mu_k) * math.exp(-(vn / pc.v_s) ** 2)
        den = 1.0 + dt * pc.sg0 * vn / gv
        pc.z[0] = (pc.z[0] + dt * vx) / den
        return -N * pc.sg0 * pc.z[0]

    # pre-sliding stiffness: tiny displacement
    pc.z = [0.0, 0.0]
    f = 0.0
    x = 0.0
    for k in range(200):
        v = 1e-7 / (200 * dt)
        x += v * dt
        f = lug(v)
    out["presliding_stiffness_N_per_m"] = {"measured": float(-f / x), "closed_form": float(mu_k * ms * N / x_pre)}
    # spring-driven stick-slip
    k_s = 200.0
    v_d = 1e-3
    for label, kk in (("stick_slip", k_s),):
        pc.z = [0.0, 0.0]
        x, v = 0.0, 0.0
        T = 3.0
        n = int(T / dt)
        F = np.zeros(n)
        X = np.zeros(n)
        V = np.zeros(n)
        for i in range(n):
            xd = v_d * i * dt
            fs = kk * (xd - x)
            ff = lug(v)
            a = (fs + ff) / m
            v += a * dt
            x += v * dt
            F[i] = fs
            X[i] = x
            V[i] = v
        t = np.arange(n) * dt
        msk = t > 1.0
        Fm = F[msk]
        out[label] = {"F_max_N": float(Fm.max()), "F_min_N": float(Fm.min()), "mu_s_N": mu_k * ms * N, "mu_k_N": mu_k * N}
        # analytic Coulomb oscillator (no Stribeck smoothing, no damping): stick until k x = mu_s N, slip ends when the
        # relative velocity returns to 0; force after slip = 2 mu_k N - mu_s N (for v_d -> 0)
        out[label]["F_min_analytic_N"] = float(2 * mu_k * N - mu_k * ms * N)
        # period for v_d -> 0: stick time 2 (mu_s - mu_k) N / (k v_d) + slip time pi / omega
        om = math.sqrt(kk / m)
        T_an = 2 * (mu_k * ms - mu_k) * N / (kk * v_d) + math.pi / om
        # measured period from the force peaks
        pk = [i for i in range(1, len(Fm) - 1) if Fm[i] > Fm[i - 1] and Fm[i] >= Fm[i + 1] and Fm[i] > 0.9 * Fm.max()]
        per = np.diff(np.array(pk)) * dt if len(pk) > 2 else np.array([np.nan])
        out[label]["period_s"] = float(np.median(per))
        out[label]["period_analytic_s"] = float(T_an)
    # steady sliding at 20 mm/s: friction = mu_k N (Stribeck term exp(-100) ~ 0)
    pc.z = [0.0, 0.0]
    for i in range(4000):
        f = lug(0.02)
    out["sliding_20mm_s"] = {"F_N": float(-f), "mu_k_N": mu_k * N}
    return out


# ============================================================================================ convergence
def convergence(dts=(12.5e-6, 25e-6, 50e-6, 100e-6), seed=300, f0=8.0, amp=1.0e-3, contact="h1", T=3.0, log=print,
                integrator: str = "implicitfast") -> Dict:
    from opt.inertial import scen as SC
    from sim.handpen import evaluate as HE
    sc = SC.get(seed, SC.tremor(f0, amp), duration=T)
    sc0 = SC.get(seed, None, duration=T)
    rows = []
    ref_ink = None
    for dt in dts:
        cfg = P.h1_check_config(0.5).replace(dt=dt, integrator=integrator)
        if contact != "h1":
            cfg = cfg.replace(contact=replace(cfg.contact, model="mujoco"))
        pm = B.build(cfg)
        t0 = time.time()
        ref = S.run(pm, sc0)
        un = S.run(pm, sc)
        n = int(round(T / dt))
        clean = S.clean_ticks(ref, int(math.ceil(n / max(int(round(0.5e-3 / dt)), 1))))
        orc = S.run(pm, sc, S.RunOptions(source="oracle", clean=clean))
        mu = HE.compare(un, ref)
        mo = HE.compare(orc, ref)
        tt = np.arange(0.5, T - 0.05, 0.25e-3)
        ink = np.column_stack([np.interp(tt, un["t"], un["ballx"]), np.interp(tt, un["t"], un["bally"])])
        row = {"dt_us": dt * 1e6, "integrator": integrator, "unmod_e_rms_um": mu["e_rms_um"],
               "oracle_ratio": mo["e_rms_um"] / mu["e_rms_um"], "wall_s": time.time() - t0, "ink": ink}
        rows.append(row)
        if log:
            log(f"  convergence {contact} {integrator} dt {dt * 1e6:.1f} us: unmod {row['unmod_e_rms_um']:.2f} um, "
                f"oracle {row['oracle_ratio']:.4f} ({row['wall_s']:.0f} s)")
    # ink path differences against the finest step (and between successive steps: observed order of convergence)
    fin = rows[0]["ink"]
    for r in rows:
        r["ink_path_diff_um"] = float(np.sqrt(np.mean(np.sum((r["ink"] - fin) ** 2, axis=1))) * 1e6)
    for i in range(2, len(rows)):
        e1 = np.sqrt(np.mean(np.sum((rows[i - 1]["ink"] - rows[i - 2]["ink"]) ** 2, axis=1)))
        e2 = np.sqrt(np.mean(np.sum((rows[i]["ink"] - rows[i - 1]["ink"]) ** 2, axis=1)))
        rr = rows[i]["dt_us"] / rows[i - 1]["dt_us"]
        rows[i]["observed_order"] = float(math.log(max(e2, 1e-30) / max(e1, 1e-30)) / math.log(rr)) if e1 > 0 else None
    for r in rows:
        r.pop("ink")
        if log:
            log(f"    dt {r['dt_us']:.1f} us: ink path difference vs finest {r['ink_path_diff_um']:.3f} um, "
                f"observed order {r.get('observed_order')}")
    return {"rows": rows, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "contact": contact, "integrator": integrator}


# ============================================================================================ energy
def energy_audit(case="conservative", T=0.5, dt=25e-6, integrator="implicitfast") -> Dict:
    """Energy balance of the pen in the air (no paper contact).  'conservative': no damping, passive springs only
    (arm spring as joint stiffness), initial deflection; 'damped': grip and arm damping on; 'actuated': coil torque
    on the nose.  Checks E(T) - E(0) against the integrated work of dampers and actuators."""
    hand = P.HandH1(r_rot=0.5, lock_roll=True)
    rf = P.Refill(F_c=1e-9, slide_range=(-0.02, 0.02), front_stop="carrier")
    nz = P.Nose(zeta_flex=0.0 if case != "damped" else 0.02)
    if case in ("conservative", "actuated"):
        hand = replace(hand, b_nib=1e-12)
        rf = replace(rf, damping=0.0)
    cfg = P.Config(hand=hand, refill=rf, nose=nz, contact=P.Contact(model="h1"), gravity=False, dt=dt,
                   integrator=integrator)
    pm = B.build(cfg)
    m, d = pm.m, pm.d
    # arm spring: make the hand slides passive springs (conservative) and remove the servo actuators' effect
    for nm in ("x", "y", "z"):
        j = pm.ids[f"jnt:hand_{nm}"]
        m.jnt_stiffness[j] = 170.0
        m.dof_damping[m.jnt_dofadr[j]] = 0.0 if case != "damped" else 11.0
        m.actuator_gainprm[pm.ids[f"act:arm_p_{nm}"], 0] = 0.0
        m.actuator_biasprm[pm.ids[f"act:arm_p_{nm}"], 1] = 0.0
        m.actuator_gainprm[pm.ids[f"act:arm_v_{nm}"], 0] = 0.0
        m.actuator_biasprm[pm.ids[f"act:arm_v_{nm}"], 2] = 0.0
    m.opt.enableflags |= int(mujoco.mjtEnableBit.mjENBL_ENERGY)
    mujoco.mj_resetData(m, d)
    # lift the pen well above the paper and give it an initial deflection and velocity
    d.qpos[pm.jnt_qadr("hand_z")] = 5e-3
    m.qpos_spring[pm.jnt_qadr("hand_z")] = 5e-3
    d.qpos[pm.jnt_qadr("grip_t1")] = 0.3e-3
    d.qvel[pm.jnt_dadr("grip_t2")] = 0.02
    d.qvel[pm.jnt_dadr("grip_b1")] = 0.05
    d.qpos[pm.jnt_qadr("nose_1")] = 0.01
    mujoco.mj_forward(m, d)
    E0 = d.energy[0] + d.energy[1]
    n = int(round(T / dt))
    W_damp = 0.0
    W_act = 0.0
    W_con = 0.0
    act = [pm.ids["act:coil_1"], pm.ids["act:coil_2"]]
    for k in range(n):
        mujoco.mj_step1(m, d)
        if case == "actuated":
            d.ctrl[act[0]] = 0.05 * math.sin(2 * math.pi * 30.0 * k * dt)
        v0 = d.qvel.copy()
        mujoco.mj_step2(m, d)
        # powers with the forces of this step and the midpoint of the velocities (before/after the step)
        vm = 0.5 * (v0 + d.qvel)
        W_damp += float(d.qfrc_damper @ vm) * dt
        W_act += float(d.qfrc_actuator @ vm) * dt
        W_con += float(d.qfrc_constraint @ vm) * dt
    mujoco.mj_forward(m, d)
    E1 = d.energy[0] + d.energy[1]
    m.opt.enableflags &= ~int(mujoco.mjtEnableBit.mjENBL_ENERGY)
    dE = E1 - E0
    W = W_damp + W_act + W_con
    scale = max(abs(E0), abs(W_damp), abs(W_act), 1e-12)
    return {"case": case, "integrator": integrator, "dt_us": dt * 1e6, "E0_J": float(E0), "E1_J": float(E1), "dE_J": float(dE),
            "W_damper_J": W_damp, "W_actuator_J": W_act, "W_constraint_J": W_con, "residual_J": float(dE - W),
            "residual_rel": float((dE - W) / scale)}


# ============================================================================================ gyroscope
def gyro_torque(spin_rpms=(5000, 10000, 20000), rates=(2.0, 5.0, 10.0), dt=25e-6) -> Dict:
    """A rotor (16 x 5 mm tungsten, h = I_s w_s) on a gimbal about y in a body welded to the world through a torque
    sensor: drive the gimbal at a constant rate and compare the reaction torque with h x omega_gimbal."""
    rows = []
    for rpm in spin_rpms:
        for rate in rates:
            m_r, r, th = 18.1e-3, 8e-3, 5e-3
            Is = 0.5 * m_r * r * r
            It = m_r * (3 * r * r + th * th) / 12.0
            xml = f"""
<mujoco>
  <option timestep="{dt}" gravity="0 0 0" integrator="implicitfast"/>
  <worldbody>
    <body name="base" pos="0 0 0">
      <inertial pos="0 0 0" mass="0.05" diaginertia="1e-5 1e-5 1e-5"/>
      <site name="s" pos="0 0 0"/>
      <body name="gimbal" pos="0 0 0">
        <joint name="g" type="hinge" axis="0 1 0"/>
        <inertial pos="0 0 0" mass="1e-4" diaginertia="2e-8 2e-8 2e-8"/>
        <body name="rotor" pos="0 0 0">
          <joint name="spin" type="hinge" axis="0 0 1"/>
          <inertial pos="0 0 0" mass="{m_r}" diaginertia="{It} {It} {Is}"/>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <general name="gv" joint="g" gainprm="1" biastype="affine" biasprm="0 0 -1"/>
    <general name="sv" joint="spin" gainprm="0.05" biastype="affine" biasprm="0 0 -0.05"/>
  </actuator>
  <sensor><torque name="tq" site="s"/></sensor>
</mujoco>"""
            mm = mujoco.MjModel.from_xml_string(xml)
            d = mujoco.MjData(mm)
            w = rpm * 2 * math.pi / 60.0
            d.qvel[1] = w
            d.ctrl[1] = w
            d.ctrl[0] = rate
            mujoco.mj_forward(mm, d)
            T = 0.2
            n = int(T / dt)
            tq = []
            pred = []
            for k in range(n):
                mujoco.mj_step(mm, d)
                if k * dt > 0.05:
                    tq.append(d.sensordata[0:3].copy())
                    dl = d.qpos[0]
                    h = Is * d.qvel[1] * np.array([math.sin(dl), 0.0, math.cos(dl)])
                    om = np.array([0.0, d.qvel[0], 0.0])
                    # reaction on the base = -(d/dt of the rotor's angular momentum) = -(omega x h) for steady rates
                    pred.append(-np.cross(om, h))
            tq = np.array(tq)
            pred = np.array(pred)
            # the torque sensor reports the torque the child exerts... sign convention: compare magnitudes and correlation
            err = np.linalg.norm(np.abs(tq).mean(axis=0) - np.abs(pred).mean(axis=0)) / np.linalg.norm(np.abs(pred).mean(axis=0))
            rows.append({"spin_rpm": rpm, "gimbal_rate_rad_s": rate, "h_mNms": Is * w * 1e3,
                         "torque_measured_mNm": float(np.linalg.norm(tq.mean(axis=0)) * 1e3),
                         "h_x_omega_mNm": float(np.linalg.norm(pred.mean(axis=0)) * 1e3), "rel_error": float(err)})
    return {"rows": rows, "max_rel_error": float(max(r["rel_error"] for r in rows))}


# ============================================================================================ sensors
def sensor_tests(T=4.0, seed=5) -> Dict:
    """(1) IMU readings of a pen held still: noise density and ODR against fusion.sensors (LSM6DSV16X); (2) MuJoCo's
    native accelerometer against f = R^T (a - g) from the recorded site velocity, and the H1-style kinematic formula
    (positions differentiated twice), on a tremor run; (3) page-sensor latency by cross-correlation."""
    from fusion import sensors as FS
    from scipy.signal import welch
    from . import sensors as SN
    out = {}
    cfg = P.h1_check_config(0.5)
    pm = B.build(cfg)
    r = S.run(pm, _still(T=T))
    res_imu = {}
    for comp in ("none", "gyro"):
        st = SN.make_streams(r, seed, cfg.geom.z_imu, comp=comp)
        fs_a = 1.0 / float(np.median(np.diff(st.acc_t)))
        nds = []
        for ax in range(2):
            acc = st.acc[len(st.acc) // 4:, ax]
            f, Pxx = welch(acc - acc.mean(), fs=fs_a, nperseg=4096)
            msk = (f > 20) & (f < 200)
            nds.append(math.sqrt(np.mean(Pxx[msk])) / FS.PT.UG)            # one-sided PSD = datasheet density^2
        res_imu[comp] = {"odr_Hz": fs_a, "acc_nd_ug_per_rtHz_x_y": nds}
    out["imu"] = {"raw_reading": res_imu["none"], "compensated": res_imu["gyro"], "odr_fusion_Hz": FS.AccelModel().odr,
                  "acc_nd_fusion_ug_per_rtHz": FS.AccelModel().nd / FS.PT.UG,
                  "note": "pen held still on the paper; 20-200 Hz band; 'raw' = accelerometer reading rotated to the page "
                          "(fusion's reading model: its noise density should come back); 'compensated' adds the firmware's "
                          "lever-arm term r x d(omega)/dt, which differentiates gyro noise (dominant above ~50 Hz)"}
    # (2) native accelerometer vs kinematic specific force on a tremor case
    from opt.inertial import scen as SC
    sc = SC.get(300, SC.tremor(8.0, 1.0e-3), duration=2.0)
    m, d = pm.m, pm.d
    B.reset(pm)
    sl_acc = B.sensor_slice(pm, "imu_acc")
    sl_v = B.sensor_slice(pm, "imu_linvel")
    s_imu = pm.ids["site:imu"]
    rec_nat, rec_v, rec_R, rec_p = [], [], [], []
    from .contact import ContactLaw
    law = ContactLaw(pm)
    dt = m.opt.timestep
    hidx = [pm.ids[k] for k in ("act:arm_p_x", "act:arm_p_y", "act:arm_p_z", "act:arm_v_x", "act:arm_v_y", "act:arm_v_z")]
    aref = np.gradient(sc.vref, dt, axis=0) * cfg.hand.M
    af = [pm.ids["act:arm_f_x"], pm.ids["act:arm_f_y"], pm.ids["act:arm_f_z"]]
    n = len(sc.t)
    for k in range(n):
        mujoco.mj_step1(m, d)
        d.ctrl[hidx] = np.concatenate([sc.pref[k], sc.vref[k]])
        d.ctrl[af] = aref[k]
        law.forces(sc.fpush[k])
        mujoco.mj_step2(m, d)
        if k % 10 == 0:
            rec_nat.append(d.sensordata[sl_acc].copy())
            rec_v.append(d.sensordata[sl_v].copy())
            rec_R.append(d.site_xmat[s_imu].reshape(3, 3).copy())
            rec_p.append(d.site_xpos[s_imu].copy())
    nat = np.array(rec_nat)
    V = np.array(rec_v)
    Rm = np.array(rec_R)
    Pp = np.array(rec_p)
    h = 10 * dt
    a_v = np.gradient(V, h, axis=0)
    f_v = np.einsum("nji,nj->ni", Rm, a_v)                    # gravity off in the dynamics: the native sensor has no g
    a_p = np.gradient(np.gradient(Pp, h, axis=0), h, axis=0)
    f_p = np.einsum("nji,nj->ni", Rm, a_p)
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [3.0, 15.0], btype="band", fs=1.0 / h, output="sos")
    sl = slice(len(nat) // 4, None)
    bn, bv, bp = (sosfiltfilt(sos, x, axis=0)[sl] for x in (nat, f_v, f_p))
    out["accelerometer_consistency_3_15Hz"] = {
        "corr_native_vs_velocity_diff": float(np.corrcoef(bn[:, 0], bv[:, 0])[0, 1]),
        "corr_native_vs_position_diff": float(np.corrcoef(bn[:, 0], bp[:, 0])[0, 1]),
        "rms_rel_diff_native_vs_velocity": float(np.sqrt(np.mean((bn - bv) ** 2)) / np.sqrt(np.mean(bn ** 2)))}
    # (3) page-sensor latency
    st = SN.make_streams(r, seed, cfg.geom.z_imu)
    out["page"] = {"rate_Hz": 1.0 / float(np.median(np.diff(st.pos_t))), "latency_s": float(np.median(st.pos_av - st.pos_t))}
    return out
