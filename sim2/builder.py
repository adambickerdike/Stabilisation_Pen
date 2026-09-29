r"""MJCF generator for the hand-pen-paper model (MuJoCo 3.6).

`build(cfg)` returns a `PenModel`: the MJCF text, the compiled mujoco.MjModel, a fresh MjData, named ids and the
derived parameters (grip calibration, mass properties, equilibrium heights).  The model is generated from the labelled
inputs of params.py; plug-ins add their own bodies, joints, actuators and sites through `Plugin.mjcf()`.

Body tree ('h1' hand; the 'arm' hand replaces the hand bodies by the forearm-wrist-hand chain of hand.py):

  world ─ paper (plane z = 0)
        └ hand (3 slides with the HAP-26 arm spring to the imposed path, 0.21 kg)
            └ hand_rot (optional imposed wrist rotation, kinematic servo)
                └ handle (grip joints at the elastic centre z_c: slides t1, t2, a; hinges about t2, t1; roll)
                    ├ skid ring (C: capsules over 240 deg, contact radius 6.75 mm), sites (tip, imu, hall, grip zones)
                    ├ plug-in bodies (end-cap rotor/CMG, reaction mass, heel drive)
                    └ nose (2 hinges at the gimbal z_p, flexure stiffness, coil actuators with gear K_f (z_a - z_p))
                        └ refill (slide along a, constant-force spring F_c, tilt-adaptive front stop) ─ ball (r_b)

Grip joints at the elastic centre reproduce H1's two-zone grip exactly in the linear regime: per plane the zone
stiffness K = [[k_t, S], [S, I2 + kappa_f]] about the nib becomes diag(k_t, K_r) about z_c = S/k_t with
K_r = I2 + kappa_f - S^2/k_t (congruence; CALC, checked in tests), and the stiffness-proportional damping transforms the
same way.  Evidence status of the model: PROPOSED DESIGN geometry + LIT/ASSUMPTION parameters (params.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import mujoco
import numpy as np

from . import params as P


def _f(x) -> str:
    return " ".join(f"{float(v):.9g}" for v in np.atleast_1d(x))


def quat_from_R(R: np.ndarray) -> np.ndarray:
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.ascontiguousarray(R, dtype=np.float64).ravel())
    return q


@dataclass
class PenModel:
    cfg: P.Config
    xml: str
    m: mujoco.MjModel
    d: mujoco.MjData
    ids: Dict[str, int]
    info: Dict
    plugins: List = field(default_factory=list)

    def jnt_qadr(self, name: str) -> int:
        return int(self.m.jnt_qposadr[self.ids["jnt:" + name]])

    def jnt_dadr(self, name: str) -> int:
        return int(self.m.jnt_dofadr[self.ids["jnt:" + name]])

    def has(self, key: str) -> bool:
        return key in self.ids


# ----------------------------------------------------------------------------------------------- grip calibration
def grip_params(cfg: P.Config) -> Dict:
    """H1 two-zone grip (sim/handpen/grip.calibrate) mapped to joints at the elastic centre (CALC)."""
    from sim.handpen import grip as G
    h, g = cfg.hand, cfg.geom
    gr = G.calibrate(h.k_nib, h.b_nib, h.r_rot, h.rho_w, g.z_f, g.z_w, h.grip_scale, h.grip_damp_add)
    k_t = gr.k_f + gr.k_w
    S = gr.k_f * gr.z_f + gr.k_w * gr.z_w
    I2 = gr.k_f * gr.z_f ** 2 + gr.k_w * gr.z_w ** 2
    z_c = S / k_t
    K_r = I2 + gr.kappa_f - S * S / k_t
    return {"k_t": k_t, "k_a": gr.k_a, "K_r": K_r, "z_c": z_c, "beta": gr.beta, "k_f": gr.k_f, "k_w": gr.k_w,
            "kappa_f": gr.kappa_f, "r_rot": gr.r_rot, "rho_w": gr.rho_w, "summary": gr.summary()}


# ----------------------------------------------------------------------------------------------- geometry helpers
def pen_rotation(cfg: P.Config) -> np.ndarray:
    a, t1, t2, n, h = cfg.geom.vectors()
    return np.column_stack([t1, t2, a])


def skid_capsules(g: P.Geometry, theta_deg: Optional[float] = None) -> List[np.ndarray]:
    """Capsule segments (local pen frame) of the C ring: centreline radius R0 and axial position z_ring chosen so the
    lowest surface point at the nominal tilt is H1's skid point (p_nom a + R t1).  The number of segments is odd so that
    the middle segment is centred on t1 (the side toward the paper); the chord sag is R0 (1 - cos(dphi/2))."""
    th = (g.theta_deg if theta_deg is None else theta_deg) * P.D2R
    rho = g.skid_rho
    z_ring = g.p_nom(theta_deg) + rho * math.sin(th)
    R0 = g.skid_R - rho * math.cos(th)
    arc = 2 * math.pi - g.skid_open_deg * P.D2R
    nseg = g.skid_segments if g.skid_segments % 2 == 1 else g.skid_segments + 1
    dphi = arc / nseg
    ang = [-arc / 2 + i * dphi for i in range(nseg + 1)]
    segs = []
    for i in range(nseg):
        p0 = np.array([R0 * math.cos(ang[i]), R0 * math.sin(ang[i]), z_ring])
        p1 = np.array([R0 * math.cos(ang[i + 1]), R0 * math.sin(ang[i + 1]), z_ring])
        segs.append(np.concatenate([p0, p1]))
    return segs


# ----------------------------------------------------------------------------------------------- MJCF text
def _contact_attrs(cfg: P.Config, mu: float, native: bool) -> str:
    c = cfg.contact
    if not native:
        return 'contype="0" conaffinity="0"'
    return (f'contype="2" conaffinity="1" condim="3" friction="{mu:.6g} 0.005 0.0001" '
            f'solref="{_f(c.solref)}" solimp="{_f(c.solimp)}"')


def build(cfg: Optional[P.Config] = None) -> PenModel:
    cfg = cfg or P.Config()
    g, c, nz, rf = cfg.geom, cfg.contact, cfg.nose, cfg.refill
    a, t1, t2, n, h = g.vectors()
    th = g.theta_deg * P.D2R
    Rp = pen_rotation(cfg)
    qp = quat_from_R(Rp)
    native = c.model == "mujoco"
    gp = grip_params(cfg)
    hp, npar, rfp = P.part_lists(cfg.wiring)
    for pl in cfg.plugins:
        hp = pl.modify_handle_parts(hp)
    H = P.rigid_props(hp)
    N = P.rigid_props(npar)
    RF = P.rigid_props(rfp)
    info: Dict = {"grip": gp, "handle": H, "nose": N, "refill": RF, "theta_deg": g.theta_deg,
                  "p_nom": g.p_nom(), "contact_model": c.model, "hand_model": cfg.hand_model}
    beta = gp["beta"]
    z_c = gp["z_c"]
    # static loads (gravity off: H1 convention; push force N0 at the handle tip)
    N_ball0 = rf.F_c / math.sin(th)
    N_skid0 = max(cfg.N0 - N_ball0, 0.0)
    info.update(N_ball0=N_ball0, N_skid0=N_skid0)
    if native:
        z0 = g.r_b          # refined after compilation by settle()
    else:
        z0 = g.r_b - N_skid0 / c.k_sk
    info["z0"] = z0
    # nose bias: static transverse ball load F_c cot(theta) at the ball -> torque about the gimbal (about +t2)
    tau_bias = g.z_p * rf.F_c / math.tan(th)
    info["tau_bias"] = tau_bias
    nose_I = N["J_t"] + N["m"] * (N["z_g"] - g.z_p) ** 2 + RF["J_t"] + RF["m"] * (RF["z_g"] - g.z_p) ** 2
    info["nose_I_pivot"] = nose_I
    c_flex = 2.0 * nz.zeta_flex * math.sqrt(nz.k_r * nose_I)
    info["nose_c_flex"] = c_flex
    arm = g.z_a - g.z_p
    info["coil_arm"] = arm
    K_f = nz.K_f
    info["K_f"] = K_f
    lines: List[str] = []
    A = lines.append
    A(f'<mujoco model="sim2_revH">')
    A('  <compiler angle="radian" autolimits="true" inertiafromgeom="false"/>')
    grav = "0 0 -9.80665" if cfg.gravity else "0 0 0"
    A(f'  <option timestep="{cfg.dt:.9g}" gravity="{grav}" integrator="{cfg.integrator}" cone="{c.cone}" '
      f'impratio="{c.impratio:.6g}" noslip_iterations="{int(c.noslip_iterations)}" tolerance="1e-10" iterations="60"/>')
    A('  <visual><global offwidth="1280" offheight="960"/></visual>')
    A('  <default>')
    A('    <geom contype="0" conaffinity="0" group="1" rgba="0.8 0.8 0.85 1"/>')
    A('    <joint limited="false" armature="0"/>')
    A('  </default>')
    A('  <worldbody>')
    A(f'    <geom name="paper" type="plane" size="0.3 0.3 0.01" contype="1" conaffinity="2" condim="3" '
      f'friction="0 0.005 0.0001" solref="{_f(c.solref)}" solimp="{_f(c.solimp)}" rgba="0.97 0.97 0.93 1" group="0"/>')
    A('    <light pos="0 0 0.5" dir="0 0 -1"/>')
    # ------------------------------------------------------------------ hand
    close_hand = []
    if cfg.hand_model == "h1":
        hh = cfg.hand
        A(f'    <body name="hand" pos="0 0 {z0:.9g}">')
        for ax, nm in (("1 0 0", "x"), ("0 1 0", "y"), ("0 0 1", "z")):
            A(f'      <joint name="hand_{nm}" type="slide" axis="{ax}"/>')
        A(f'      <inertial pos="0 0 0" mass="{hh.M:.9g}" diaginertia="1e-6 1e-6 1e-6"/>')
        A('      <geom type="sphere" size="0.004" rgba="0.9 0.7 0.6 0.4"/>')
        if hh.rot_tremor:
            # imposed hand-frame rotation (H1 wrist tremor): a stiff kinematic servo on a heavy frame (1 kg m^2,
            # 300 Hz), so the grip's reaction torque does not move it (0.1 N m -> 3e-8 rad)
            A('      <body name="hand_rot" pos="0 0 0">')
            A('        <joint name="hand_psi" type="hinge" axis="0 0 1" pos="0.2 0 0"/>')
            A('        <inertial pos="0 0 0" mass="1e-5" diaginertia="1 1 1"/>')
            close_hand = ['      </body>', '    </body>']
            ind = "        "
        else:
            close_hand = ['    </body>']
            ind = "      "
    else:
        from . import hand as HD
        ind, close_hand = HD.arm_mjcf(cfg, A, z0, gp)
    # ------------------------------------------------------------------ handle (pen body) with grip joints
    A(f'{ind}<body name="handle" pos="0 0 0" quat="{_f(qp)}">')
    kt, ka, Kr = gp["k_t"], gp["k_a"], gp["K_r"]
    A(f'{ind}  <joint name="grip_t1" type="slide" axis="1 0 0" stiffness="{kt:.9g}" damping="{beta * kt:.9g}"/>')
    A(f'{ind}  <joint name="grip_t2" type="slide" axis="0 1 0" stiffness="{kt:.9g}" damping="{beta * kt:.9g}"/>')
    A(f'{ind}  <joint name="grip_a" type="slide" axis="0 0 1" stiffness="{ka:.9g}" damping="{beta * ka:.9g}"/>')
    A(f'{ind}  <joint name="grip_b1" type="hinge" axis="0 1 0" pos="0 0 {z_c:.9g}" stiffness="{Kr:.9g}" damping="{beta * Kr:.9g}"/>')
    A(f'{ind}  <joint name="grip_b2" type="hinge" axis="1 0 0" pos="0 0 {z_c:.9g}" stiffness="{Kr:.9g}" damping="{beta * Kr:.9g}"/>')
    if not cfg.hand.lock_roll:
        kr = cfg.hand.k_roll
        A(f'{ind}  <joint name="grip_roll" type="hinge" axis="0 0 1" pos="0 0 {z_c:.9g}" stiffness="{kr:.9g}" damping="{beta * kr:.9g}"/>')
    A(f'{ind}  <inertial pos="0 0 {H["z_g"]:.9g}" mass="{H["m"]:.9g}" diaginertia="{H["J_t"]:.9g} {H["J_t"]:.9g} {H["J_a"]:.9g}"/>')
    # visual shell and sleeve
    A(f'{ind}  <geom type="cylinder" fromto="0 0 0.05 0 0 {g.length:.6g}" size="{g.handle_od / 2:.6g}" rgba="0.3 0.35 0.45 0.35"/>')
    A(f'{ind}  <geom type="cylinder" fromto="0 0 0.0067 0 0 0.05" size="0.0095" rgba="0.2 0.5 0.4 0.35"/>')
    # skid ring
    for i, s in enumerate(skid_capsules(g)):
        A(f'{ind}  <geom name="skid{i}" type="capsule" fromto="{_f(s)}" size="{g.skid_rho:.6g}" '
          f'{_contact_attrs(cfg, c.mu_skid, native)} rgba="0.9 0.9 0.9 1" group="0"/>')
    # sites (local pen frame)
    A(f'{ind}  <site name="tip" pos="0 0 0" size="0.0005"/>')
    A(f'{ind}  <site name="skid_pt" pos="{g.skid_R:.9g} 0 {g.p_nom():.9g}" size="0.0004"/>')
    A(f'{ind}  <site name="imu" pos="{g.r_imu:.9g} 0 {g.z_imu:.9g}" size="0.0015"/>')
    A(f'{ind}  <site name="hall_sensor" pos="0 0 {g.z_hall_sensor:.9g}" size="0.0008"/>')
    A(f'{ind}  <site name="page_sensor" pos="0 0 {g.z_page_sensor:.9g}" size="0.0008"/>')
    A(f'{ind}  <site name="finger" pos="0 0 {g.z_f:.9g}" size="0.001"/>')
    A(f'{ind}  <site name="web" pos="0 0 {g.z_w:.9g}" size="0.001"/>')
    A(f'{ind}  <site name="grip_c" pos="0 0 {z_c:.9g}" size="0.001"/>')
    A(f'{ind}  <site name="coil" pos="0 0 {g.z_a:.9g}" size="0.001"/>')
    A(f'{ind}  <site name="cap" pos="0 0 {g.length:.9g}" size="0.001"/>')
    for pl in cfg.plugins:
        pl.mjcf_handle(A, ind + "  ", cfg, info)
    # ------------------------------------------------------------------ nose + refill
    nose_bias_ref = 0.0
    A(f'{ind}  <body name="nose" pos="0 0 {g.z_p:.9g}">')
    for pl in cfg.plugins:
        pl.mjcf_nose_joints(A, ind + "    ", cfg, info)
    if cfg.nose_on:
        A(f'{ind}    <joint name="nose_1" type="hinge" axis="0 1 0" stiffness="{nz.k_r:.9g}" springref="{nose_bias_ref:.9g}" '
          f'damping="{c_flex:.9g}" range="-0.2 0.2" limited="true"/>')
        A(f'{ind}    <joint name="nose_2" type="hinge" axis="1 0 0" stiffness="{nz.k_r:.9g}" damping="{c_flex:.9g}" '
          f'range="-0.2 0.2" limited="true"/>')
    A(f'{ind}    <inertial pos="0 0 {N["z_g"] - g.z_p:.9g}" mass="{N["m"]:.9g}" '
      f'diaginertia="{N["J_t"]:.9g} {N["J_t"]:.9g} {N["J_a"]:.9g}"/>')
    A(f'{ind}    <geom type="cylinder" fromto="0 0 {0.0102 - g.z_p:.6g} 0 0 0" size="0.0035" rgba="0.75 0.75 0.8 0.8"/>')
    A(f'{ind}    <geom type="cylinder" fromto="0 0 0 0 0 {g.z_a - g.z_p + 0.003:.6g}" size="0.0025" rgba="0.75 0.75 0.8 0.8"/>')
    A(f'{ind}    <site name="magnet" pos="0 0 {g.z_a - g.z_p:.9g}" size="0.001"/>')
    A(f'{ind}    <site name="hall_magnet" pos="0 0 {g.z_hall_magnet - g.z_p:.9g}" size="0.0006"/>')
    A(f'{ind}    <site name="nose_tip" pos="0 0 {-g.z_p:.9g}" size="0.0004"/>')
    # refill: slide along a, constant-force spring, tilt-adaptive front stop
    s_lo, s_hi = rf.slide_range
    cot = math.cos(th) / math.sin(th)
    if rf.front_stop == "wide":
        s_lo = -(g.front_stop_margin + g.travel_stop * cot)
    elif rf.front_stop in ("carrier", "nose_adaptive"):
        s_lo = -g.front_stop_margin
    info["refill_s_lo"] = s_lo
    info["cot_theta"] = cot
    kcf = rf.F_c / rf.L_ref
    A(f'{ind}    <body name="refill" pos="0 0 {-g.z_p:.9g}">')
    A(f'{ind}      <joint name="refill_s" type="slide" axis="0 0 1" range="{s_lo:.9g} {s_hi:.9g}" limited="true" '
      f'stiffness="{kcf:.9g}" springref="{-rf.L_ref:.9g}" damping="{rf.damping:.9g}" frictionloss="{rf.frictionloss:.9g}" '
      f'solreflimit="2e-4 1" solimplimit="0.99 0.999 1e-4 0.5 2"/>')
    A(f'{ind}      <inertial pos="0 0 {RF["z_g"]:.9g}" mass="{RF["m"]:.9g}" diaginertia="{RF["J_t"]:.9g} {RF["J_t"]:.9g} {RF["J_a"]:.9g}"/>')
    A(f'{ind}      <geom type="cylinder" fromto="0 0 0.003 0 0 0.067" size="0.001175" rgba="0.2 0.2 0.8 1"/>')
    A(f'{ind}      <geom name="ball" type="sphere" size="{g.r_b:.9g}" pos="0 0 0" {_contact_attrs(cfg, c.mu_ball, native)} '
      f'rgba="0.1 0.1 0.1 1" group="0"/>')
    A(f'{ind}      <site name="ball" pos="0 0 0" size="0.0003"/>')
    A(f'{ind}    </body>')
    for pl in cfg.plugins:
        pl.mjcf_nose(A, ind + "    ", cfg, info)
    A(f'{ind}  </body>')
    A(f'{ind}</body>')
    for ln in close_hand:
        A(ln)
    for pl in cfg.plugins:
        pl.mjcf_world(A, "    ", cfg, info)
    A('  </worldbody>')
    # ------------------------------------------------------------------ actuators
    A('  <actuator>')
    if cfg.hand_model == "h1":
        hh = cfg.hand
        for nm in ("x", "y", "z"):
            A(f'    <general name="arm_p_{nm}" joint="hand_{nm}" gainprm="{hh.k_arm:.9g}" biastype="affine" biasprm="0 {-hh.k_arm:.9g} 0"/>')
            A(f'    <general name="arm_v_{nm}" joint="hand_{nm}" gainprm="{hh.b_arm:.9g}" biastype="affine" biasprm="0 0 {-hh.b_arm:.9g}"/>')
            # inertial feedforward M a_ref: H1's hand mass moves with the imposed path and only its deviation dM
            # obeys M dM'' = -k dM - b dM' - F_grip (sim/handpen/core.py)
            A(f'    <motor name="arm_f_{nm}" joint="hand_{nm}"/>')
        if hh.rot_tremor:
            wr = 2 * math.pi * 300.0
            A(f'    <general name="psi_p" joint="hand_psi" gainprm="{wr * wr:.9g}" biastype="affine" biasprm="0 {-wr * wr:.9g} 0"/>')
            A(f'    <general name="psi_v" joint="hand_psi" gainprm="{2 * wr:.9g}" biastype="affine" biasprm="0 0 {-2 * wr:.9g}"/>')
    else:
        from . import hand as HD
        HD.arm_actuators(cfg, A)
    if cfg.nose_on:
        tau_e = nz.L_ind / nz.R
        gear = K_f * arm
        for i in (1, 2):
            A(f'    <general name="coil_{i}" joint="nose_{i}" gear="{gear:.9g}" dyntype="filterexact" dynprm="{tau_e:.9g}" '
              f'ctrlrange="{-nz.I_max:.6g} {nz.I_max:.6g}" ctrllimited="true"/>')
    for pl in cfg.plugins:
        pl.mjcf_actuators(A, cfg, info)
    A('  </actuator>')
    # ------------------------------------------------------------------ sensors (native; noise is added by sensors.py)
    A('  <sensor>')
    A('    <accelerometer name="imu_acc" site="imu"/>')
    A('    <gyro name="imu_gyr" site="imu"/>')
    A('    <velocimeter name="imu_vel" site="imu"/>')
    A('    <framelinvel name="tip_vel" objtype="site" objname="tip"/>')
    A('    <framelinvel name="ball_vel" objtype="site" objname="ball"/>')
    A('    <framelinvel name="imu_linvel" objtype="site" objname="imu"/>')
    A('    <frameangvel name="imu_angvel" objtype="site" objname="imu"/>')
    for pl in cfg.plugins:
        pl.mjcf_sensors(A, cfg, info)
    A('  </sensor>')
    A('</mujoco>')
    xml = "\n".join(lines)
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    ids: Dict[str, int] = {}
    for i in range(m.nbody):
        ids["body:" + m.body(i).name] = i
    for i in range(m.njnt):
        ids["jnt:" + m.joint(i).name] = i
    for i in range(m.nsite):
        ids["site:" + m.site(i).name] = i
    for i in range(m.nu):
        ids["act:" + m.actuator(i).name] = i
    for i in range(m.ngeom):
        if m.geom(i).name:
            ids["geom:" + m.geom(i).name] = i
    for i in range(m.nsensor):
        ids["sens:" + m.sensor(i).name] = i
    info["skid_geoms"] = [ids[k] for k in ids if k.startswith("geom:skid")]
    info["nq"], info["nv"], info["nu"] = m.nq, m.nv, m.nu
    pm = PenModel(cfg=cfg, xml=xml, m=m, d=d, ids=ids, info=info, plugins=list(cfg.plugins))
    for pl in cfg.plugins:
        pl.bind(pm)
    reset(pm)
    if native and cfg.hand_model == "h1":
        settle_native(pm)
    return pm


def settle_native(pm: PenModel, T: float = 0.25) -> None:
    """Native soft contacts: find the static height of the handle tip under the push force N0 (the contact's static
    compliance depends on solref/solimp and the effective mass), then move the hand frame there so the grip is unloaded
    at rest (H1 convention).  Two passes."""
    m, d = pm.m, pm.d
    cfg = pm.cfg
    g = cfg.geom
    th = g.theta_deg * P.D2R
    bh = pm.ids["body:hand"]
    s_tip = pm.ids["site:tip"]
    jr = pm.jnt_qadr("refill_s")
    n = int(round(T / m.opt.timestep))
    for _ in range(2):
        mujoco.mj_resetData(m, d)
        d.qpos[jr] = (g.r_b - pm.info["z0"]) / math.sin(th)
        mujoco.mj_forward(m, d)
        for k in range(n):
            mujoco.mj_step1(m, d)
            pt = d.site_xpos[s_tip]
            ch = d.xipos[pm.ids["body:handle"]]
            xh = d.xfrc_applied[pm.ids["body:handle"]]
            xh[:] = 0.0
            xh[2] = -cfg.N0
            xh[3] = (pt[1] - ch[1]) * -cfg.N0
            xh[4] = -(pt[0] - ch[0]) * -cfg.N0
            if pm.has("jnt:nose_1"):
                for jn in ("nose_1", "nose_2"):
                    a = pm.jnt_qadr(jn)
                    v = pm.jnt_dadr(jn)
                    act = pm.ids["act:coil_" + jn[-1]]
                    tau = -40.0 * d.qpos[a] - 0.02 * d.qvel[v]
                    d.ctrl[act] = tau / (pm.info["K_f"] * pm.info["coil_arm"])
            mujoco.mj_step2(m, d)
        z_tip = float(d.site_xpos[s_tip][2])
        dz = z_tip - pm.info["z0"]
        m.body_pos[bh][2] += dz
        pm.info["z0"] = z_tip
        pm.info["s0"] = float(d.qpos[jr])
    d.xfrc_applied[:] = 0.0
    reset(pm, s0=pm.info["s0"])


def sensor_slice(pm: PenModel, name: str) -> slice:
    i = pm.ids["sens:" + name]
    a = int(pm.m.sensor_adr[i])
    return slice(a, a + int(pm.m.sensor_dim[i]))


def reset(pm: PenModel, s0: Optional[float] = None) -> None:
    """Initial state: every joint at its reference; the refill slide at the contact position (ball on the paper)."""
    m, d = pm.m, pm.d
    mujoco.mj_resetData(m, d)
    if pm.has("jnt:refill_s"):
        g = pm.cfg.geom
        th = g.theta_deg * P.D2R
        if s0 is None:
            # ball centre at r_b with the handle tip at z0: z0 + s sin(th) = r_b - small
            s0 = (g.r_b - pm.info["z0"]) / math.sin(th)
        d.qpos[pm.jnt_qadr("refill_s")] = s0
    for pl in pm.plugins:
        pl.reset(pm)
    mujoco.mj_forward(m, d)
