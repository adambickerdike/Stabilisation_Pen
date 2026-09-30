r"""Device plug-ins with one interface (studies D, K and N hand over their parameters later).

A plug-in is a dataclass of labelled parameters plus these hooks, called by builder.build() and by the simulator:

  modify_handle_parts(parts)      add or remove mass on the handle (fixed parts: frames, coils, motors)
  mjcf_handle(A, ind, cfg, info)  bodies/joints/geoms/sites attached to the handle (pen-local frame, z from the ball)
  mjcf_nose(A, ind, cfg, info)    the same, attached to the nose
  mjcf_nose_joints(A, ind, cfg, info)  extra nose joints ahead of the gimbal hinges (multi-plane nose)
  mjcf_world(A, ind, cfg, info)   world bodies (e.g. a desk board)
  mjcf_actuators(A, cfg, info)    <actuator> entries (names prefixed by the plug-in name)
  mjcf_sensors(A, cfg, info)      <sensor> entries
  bind(pm), reset(pm)             resolve ids after compilation; initial state (e.g. rotor spin)
  commands()                      [(name, lo, hi, unit)]: the device's command channels (the RL action space uses them)
  apply(pm, t, cmd)               map commands to ctrl (with current, thermal and rate limits), every control tick
  observe(pm) -> dict             device sensors (encoders, currents)
  power(pm) -> float              electrical power drawn now (W), for the energy and battery bookkeeping
  describe() -> dict              parameters with labels

Implemented:
  HeelDrive        driven ball, steered wheel, braked wheel or omni pair at the heel of the fixed sleeve, pressed on the
                   paper by a suspension spring, with Coulomb friction to the paper (rubber); motor torque and speed
                   limits (study D).
  EndCapRotor      spinning rotor(s) on gimbal joints in the rear cap: passive gyroscope, reaction wheel, single or
                   scissored-pair control-moment gyroscope; gyroscopic torques are native MuJoCo dynamics (study K).
  ReactionMass     a mass on 2-3 slide joints with stroke stops and a centring spring, driven by voice coils (study K;
                   the Rev H evaluated module by default).
  MultiPlaneNose   a second actuation plane for the nose (study N): the gimbal pivot rides on two lateral slides with a
                   centring flexure and its own voice coils, so the tip gets translation (pivot) and tilt (standard
                   coils): +-5-8 mm of tip travel with tilt control.
Every default is an ASSUMPTION or PROPOSED DESIGN value, labelled in `describe()`.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import mujoco
import numpy as np

from . import params as P


def _f(x) -> str:
    return " ".join(f"{float(v):.9g}" for v in np.atleast_1d(x))


class Plugin:
    name: str = "plugin"
    label: str = "ASSUMPTION"

    # ---- model generation
    def modify_handle_parts(self, parts):
        return parts

    def mjcf_handle(self, A, ind, cfg, info):
        pass

    def mjcf_nose(self, A, ind, cfg, info):
        pass

    def mjcf_nose_joints(self, A, ind, cfg, info):
        """Joints of the nose body placed before the standard gimbal hinges (e.g. lateral slides of the pivot)."""
        pass

    def mjcf_world(self, A, ind, cfg, info):
        pass

    def mjcf_actuators(self, A, cfg, info):
        pass

    def mjcf_sensors(self, A, cfg, info):
        pass

    # ---- runtime
    def bind(self, pm):
        self.pm = pm

    def reset(self, pm):
        pass

    def commands(self) -> List[Tuple[str, float, float, str]]:
        return []

    def apply(self, pm, t: float, cmd: np.ndarray) -> None:
        pass

    def observe(self, pm) -> Dict[str, float]:
        return {}

    def power(self, pm) -> float:
        return 0.0

    def record_channels(self) -> List[str]:
        return []

    def record(self, pm) -> List[float]:
        return []

    def describe(self) -> Dict:
        d = {k: v for k, v in asdict(self).items()} if hasattr(self, "__dataclass_fields__") else {}
        d["plugin"] = self.name
        d["label"] = self.label
        return d


# ================================================================================================ voice coil helper
@dataclass
class Coil:
    """Voice-coil electrical and thermal model (per axis).  Force = K_f * I.  The command is a current; the available
    current is limited by the driver (I_max) and by the supply headroom V >= I R(T) + K_f v (back-EMF); the coil
    temperature follows a first-order thermal model driven by the copper loss I^2 R(T)."""
    K_f: float = 0.74
    R20: float = 2.47
    L: float = 100e-6
    I_max: float = 1.5
    V: float = 3.7
    alpha: float = 0.00393
    R_th: float = 100.0
    C_th: float = 0.5
    T_amb: float = 25.0
    T: float = 25.0

    def R(self) -> float:
        return self.R20 * (1.0 + self.alpha * (self.T - 20.0))

    def limit(self, I_cmd: float, v: float = 0.0) -> float:
        R = self.R()
        I_v = max(self.V - abs(self.K_f * v), 0.0) / R
        lim = min(self.I_max, I_v)
        return max(-lim, min(lim, I_cmd))

    def step_thermal(self, I: float, dt: float) -> float:
        P_cu = I * I * self.R()
        self.T += dt * (P_cu - (self.T - self.T_amb) / self.R_th) / self.C_th
        return P_cu


# ================================================================================================ reaction mass
@dataclass
class ReactionMass(Plugin):
    name: str = "rm"
    m: float = 19.8e-3                   # moving tungsten slug (kg): Rev H evaluated module (AMF-49)
    z: float = 0.160                     # position along the pen (m)
    stroke: Tuple[float, float, float] = (2.75e-3, 2.75e-3, 0.0)   # t1, t2, axial half-stroke (0 = locked)
    k_c: float = 0.0                     # centring spring (N/m); the Rev H module used a 5 Hz centring loop instead
    c_c: float = 0.0
    K_f: float = 0.9                     # N/A per axis (Km 0.9 N/sqrt(W), R 1 ohm: ASSUMPTION)
    R20: float = 1.0
    I_max: float = 0.55                  # A (0.5 N force limit)
    fixed_mass: float = 8.0e-3           # frame, coils, flexures added to the handle (kg)
    label: str = "PROPOSED DESIGN (opt/inertial rear-cap module: WHA 19.8 g, +/-2.75 mm, Km 0.9 N/sqrt(W) ASSUMPTION)"

    def __post_init__(self):
        self.coils = [Coil(K_f=self.K_f, R20=self.R20, I_max=self.I_max) for _ in range(3)]

    def modify_handle_parts(self, parts):
        return parts + [("rm_fixed", self.fixed_mass, self.z, 0.018, 0.009 ** 2 / 2)]

    def mjcf_handle(self, A, ind, cfg, info):
        r = 5e-3
        L = 14e-3
        Jt = self.m * (3 * r * r + L * L) / 12.0
        Ja = self.m * r * r / 2.0
        A(f'{ind}<body name="{self.name}_mass" pos="0 0 {self.z:.9g}">')
        for i, (ax, s) in enumerate(zip(("1 0 0", "0 1 0", "0 0 1"), self.stroke)):
            if s > 0:
                A(f'{ind}  <joint name="{self.name}_{i}" type="slide" axis="{ax}" range="{-s:.9g} {s:.9g}" limited="true" '
                  f'stiffness="{self.k_c:.9g}" damping="{self.c_c:.9g}" solreflimit="1e-3 1"/>')
        A(f'{ind}  <inertial pos="0 0 0" mass="{self.m:.9g}" diaginertia="{Jt:.9g} {Jt:.9g} {Ja:.9g}"/>')
        A(f'{ind}  <geom type="cylinder" fromto="0 0 {-L / 2:.6g} 0 0 {L / 2:.6g}" size="{r:.6g}" rgba="0.5 0.5 0.55 1"/>')
        A(f'{ind}</body>')

    def mjcf_actuators(self, A, cfg, info):
        for i, s in enumerate(self.stroke):
            if s > 0:
                A(f'    <general name="{self.name}_f{i}" joint="{self.name}_{i}" gear="{self.K_f:.9g}" '
                  f'ctrlrange="{-self.I_max:.6g} {self.I_max:.6g}" ctrllimited="true"/>')

    def bind(self, pm):
        self.pm = pm
        self.act = [pm.ids.get(f"act:{self.name}_f{i}") for i in range(3)]
        self.jq = [pm.m.jnt_qposadr[pm.ids[f"jnt:{self.name}_{i}"]] if f"jnt:{self.name}_{i}" in pm.ids else None for i in range(3)]
        self.jv = [pm.m.jnt_dofadr[pm.ids[f"jnt:{self.name}_{i}"]] if f"jnt:{self.name}_{i}" in pm.ids else None for i in range(3)]

    def commands(self):
        return [(f"{self.name}_F{i}", -self.K_f * self.I_max, self.K_f * self.I_max, "N") for i in range(3) if self.stroke[i] > 0]

    def apply(self, pm, t, cmd):
        k = 0
        for i in range(3):
            if self.act[i] is None:
                continue
            v = pm.d.qvel[self.jv[i]]
            I = self.coils[i].limit(float(cmd[k]) / self.K_f, v)
            pm.d.ctrl[self.act[i]] = I
            k += 1

    def power(self, pm):
        return sum(c.R() * pm.d.ctrl[a] ** 2 for c, a in zip(self.coils, self.act) if a is not None)

    def record_channels(self):
        return [f"{self.name}_x{i}" for i in range(3)]

    def record(self, pm):
        return [float(pm.d.qpos[j]) if j is not None else 0.0 for j in self.jq]


# ================================================================================================ end-cap rotor / CMG
@dataclass
class EndCapRotor(Plugin):
    """Rotor(s) in the rear cap on gimbal joints.  mode: 'gyro' (passive rotor, gimbals locked), 'wheel' (reaction wheel,
    spin torque controlled), 'cmg' (single gimbal per rotor, gimbal rate controlled), 'cmg_pair' (scissored pair per
    axis: two rotors with opposite spin and opposite gimbal rates about each of t1 and t2).  Spin axis = pen axis a
    at zero gimbal angle.  Gyroscopic torques are MuJoCo's rigid-body dynamics (no added coupling term)."""
    name: str = "rotor"
    mode: str = "cmg"
    z: float = 0.160
    m: float = 18.1e-3                   # tungsten disc 16 x 5 mm (Rev J plan example): 18000 pi 0.008^2 0.005
    r: float = 8.0e-3
    thick: float = 5.0e-3
    spin_rpm: float = 20000.0
    gimbal_axes: Tuple[str, ...] = ("t2",)   # gimbal axis per rotor ('t1' or 't2')
    delta_max: float = 0.6               # gimbal angle limit (rad)
    rate_max: float = 30.0               # gimbal rate limit (rad/s)
    servo_hz: float = 100.0              # gimbal rate servo bandwidth
    gimbal_I: float = 2e-8               # gimbal frame inertia (kg m^2)
    spin_kv: float = 0.02                # spin velocity servo gain (N m s/rad)
    fixed_mass: float = 6.0e-3           # motors, bearings, frame (kg)
    label: str = "ASSUMPTION (Rev J plan: 16 x 5 mm WHA rotor at 20 000 rpm, h about 1.2 mN m s; K study hands over)"

    @property
    def I_spin(self) -> float:
        return 0.5 * self.m * self.r ** 2

    @property
    def I_trans(self) -> float:
        return self.m * (3 * self.r ** 2 + self.thick ** 2) / 12.0

    @property
    def h(self) -> float:
        return self.I_spin * self.spin_rpm * 2 * math.pi / 60.0

    def rotors(self):
        if self.mode == "cmg_pair":
            out = []
            for ax in self.gimbal_axes:
                out += [(ax, +1.0), (ax, -1.0)]
            return out
        return [(ax, 1.0) for ax in self.gimbal_axes]

    def modify_handle_parts(self, parts):
        return parts + [("rotor_fixed", self.fixed_mass, self.z, 0.01, 0.009 ** 2 / 2)]

    def mjcf_handle(self, A, ind, cfg, info):
        axv = {"t1": "1 0 0", "t2": "0 1 0"}
        for k, (ax, sgn) in enumerate(self.rotors()):
            zk = self.z + (k - (len(self.rotors()) - 1) / 2.0) * (self.thick + 1.5e-3)
            A(f'{ind}<body name="{self.name}{k}_gimbal" pos="0 0 {zk:.9g}">')
            lim = f'range="{-self.delta_max * 1.05:.6g} {self.delta_max * 1.05:.6g}" limited="true"'
            if self.mode in ("gyro", "wheel"):
                A(f'{ind}  <inertial pos="0 0 0" mass="1e-4" diaginertia="{self.gimbal_I:.6g} {self.gimbal_I:.6g} {self.gimbal_I:.6g}"/>')
            else:
                A(f'{ind}  <joint name="{self.name}{k}_g" type="hinge" axis="{axv[ax]}" {lim} damping="1e-7"/>')
                A(f'{ind}  <inertial pos="0 0 0" mass="1e-4" diaginertia="{self.gimbal_I:.6g} {self.gimbal_I:.6g} {self.gimbal_I:.6g}"/>')
            A(f'{ind}  <body name="{self.name}{k}" pos="0 0 0">')
            A(f'{ind}    <joint name="{self.name}{k}_spin" type="hinge" axis="0 0 1" damping="0"/>')
            A(f'{ind}    <inertial pos="0 0 0" mass="{self.m:.9g}" diaginertia="{self.I_trans:.9g} {self.I_trans:.9g} {self.I_spin:.9g}"/>')
            A(f'{ind}    <geom type="cylinder" fromto="0 0 {-self.thick / 2:.6g} 0 0 {self.thick / 2:.6g}" size="{self.r:.6g}" rgba="0.6 0.5 0.3 1"/>')
            A(f'{ind}  </body>')
            A(f'{ind}</body>')

    def mjcf_actuators(self, A, cfg, info):
        for k, (ax, sgn) in enumerate(self.rotors()):
            A(f'    <general name="{self.name}{k}_spin_v" joint="{self.name}{k}_spin" gainprm="{self.spin_kv:.6g}" '
              f'biastype="affine" biasprm="0 0 {-self.spin_kv:.6g}"/>')
            if self.mode == "wheel":
                A(f'    <motor name="{self.name}{k}_spin_tq" joint="{self.name}{k}_spin"/>')
            if self.mode in ("cmg", "cmg_pair"):
                kvg = 2 * math.pi * self.servo_hz * max(self.gimbal_I, 1e-9) * 50
                A(f'    <general name="{self.name}{k}_gv" joint="{self.name}{k}_g" gainprm="{kvg:.6g}" biastype="affine" biasprm="0 0 {-kvg:.6g}"/>')

    def bind(self, pm):
        self.pm = pm
        R = self.rotors()
        self.spin_q = [pm.m.jnt_dofadr[pm.ids[f"jnt:{self.name}{k}_spin"]] for k in range(len(R))]
        self.g_q = [pm.m.jnt_qposadr[pm.ids[f"jnt:{self.name}{k}_g"]] if f"jnt:{self.name}{k}_g" in pm.ids else None for k in range(len(R))]
        self.g_v = [pm.m.jnt_dofadr[pm.ids[f"jnt:{self.name}{k}_g"]] if f"jnt:{self.name}{k}_g" in pm.ids else None for k in range(len(R))]
        self.a_spin = [pm.ids[f"act:{self.name}{k}_spin_v"] for k in range(len(R))]
        self.a_gv = [pm.ids.get(f"act:{self.name}{k}_gv") for k in range(len(R))]
        self.a_tq = [pm.ids.get(f"act:{self.name}{k}_spin_tq") for k in range(len(R))]

    def reset(self, pm):
        w = self.spin_rpm * 2 * math.pi / 60.0
        for k, (ax, sgn) in enumerate(self.rotors()):
            pm.d.qvel[self.spin_q[k]] = sgn * w
            pm.d.ctrl[self.a_spin[k]] = sgn * w

    def commands(self):
        if self.mode == "wheel":
            return [(f"{self.name}{k}_tq", -1e-3, 1e-3, "N m") for k in range(len(self.rotors()))]
        if self.mode in ("cmg", "cmg_pair"):
            return [(f"{self.name}_rate_{ax}", -self.rate_max, self.rate_max, "rad/s") for ax in self.gimbal_axes]
        return []

    def apply(self, pm, t, cmd):
        if self.mode == "wheel":
            for k in range(len(self.rotors())):
                pm.d.ctrl[self.a_tq[k]] = float(cmd[k])
            return
        if self.mode not in ("cmg", "cmg_pair"):
            return
        for k, (ax, sgn) in enumerate(self.rotors()):
            j = self.gimbal_axes.index(ax)
            rate = float(np.clip(cmd[j], -self.rate_max, self.rate_max)) * sgn
            dl = pm.d.qpos[self.g_q[k]]
            if (dl >= self.delta_max and rate > 0) or (dl <= -self.delta_max and rate < 0):
                rate = 0.0
            pm.d.ctrl[self.a_gv[k]] = rate

    def record_channels(self):
        n = len(self.rotors())
        return [f"{self.name}{k}_delta" for k in range(n)] + [f"{self.name}{k}_spin" for k in range(n)]

    def record(self, pm):
        out = [float(pm.d.qpos[q]) if q is not None else 0.0 for q in self.g_q]
        return out + [float(pm.d.qvel[q]) for q in self.spin_q]


# ================================================================================================ heel drive
@dataclass
class HeelDrive(Plugin):
    """A rolling element at the heel of the fixed sleeve, pressed on the paper by a suspension spring (it shares the
    writing load with the skid ring).  kind: 'ball' (sphere with two driven axes: forces in any direction up to mu N),
    'wheel' (steered wheel: a steering hinge about the paper normal of the element and a rolling hinge; drive or brake
    torque on the rolling axis), 'omni' (two orthogonal driven wheels, idealised as a ball driven on 2 axes).
    Position: at z along the pen, on the paper side of the sleeve (radius r_mount along t1).  All defaults ASSUMPTION."""
    name: str = "heel"
    kind: str = "ball"
    z: float = 0.012
    r_mount: float = 7.2e-3
    radius: float = 1.5e-3
    m: float = 0.3e-3
    mu: float = 0.6
    k_susp: float = 300.0                # N/m suspension spring along the mount axis
    preload: float = 0.3                 # N suspension preload at the nominal position
    travel: float = 1.0e-3
    tau_max: float = 2e-4                # N m per drive axis (motor + gearing, ASSUMPTION)
    omega_max: float = 200.0             # rad/s
    steer_kp: float = 2e-3               # N m/rad steering servo (wheel)
    fixed_mass: float = 3.0e-3
    label: str = "ASSUMPTION (study D hands over the drive element; mu 0.3-0.8 in the Rev J plan)"

    def modify_handle_parts(self, parts):
        return parts + [("heel_fixed", self.fixed_mass, self.z, 0.008, 0.004 ** 2 / 2)]

    def mjcf_handle(self, A, ind, cfg, info):
        g = cfg.geom
        th = g.theta_deg * P.D2R
        # mount axis: the paper normal expressed in the pen frame at the nominal tilt: n = sin(th) a - cos(th) t1
        nloc = np.array([-math.cos(th), 0.0, math.sin(th)])
        # element centre: on the ring side (t1) at z; height so that its lowest point touches the paper at nominal
        # tilt when the suspension carries its preload
        base = np.array([self.r_mount, 0.0, self.z])
        # height of the base point above the paper at nominal (ball centre at r_b): r_b + base . n_world
        a, t1, t2, n, h = g.vectors()
        hb = g.r_b + base[0] * (t1 @ n) + base[2] * (a @ n)
        d0 = hb - self.radius                            # the element must move down (along -n) by d0 to touch
        s_pre = self.preload / self.k_susp
        c = self.name
        A(f'{ind}<body name="{c}_carriage" pos="{_f(base)}">')
        A(f'{ind}  <joint name="{c}_susp" type="slide" axis="{_f(-nloc)}" range="{-self.travel:.6g} {d0 + self.travel:.6g}" limited="true" '
          f'stiffness="{self.k_susp:.6g}" springref="{d0 + s_pre:.9g}" damping="0.5"/>')
        A(f'{ind}  <inertial pos="0 0 0" mass="2e-4" diaginertia="1e-9 1e-9 1e-9"/>')
        A(f'{ind}  <body name="{c}_elem" pos="{_f(-nloc * 0.0)}">')
        if self.kind in ("ball", "omni"):
            for i, ax in enumerate(("0 1 0", "1 0 0")):
                A(f'{ind}    <joint name="{c}_r{i}" type="hinge" axis="{ax}" damping="1e-7"/>')
            I = 0.4 * self.m * self.radius ** 2
            A(f'{ind}    <inertial pos="0 0 0" mass="{self.m:.6g}" diaginertia="{I:.6g} {I:.6g} {I:.6g}"/>')
            A(f'{ind}    <geom name="{c}_geom" type="sphere" size="{self.radius:.6g}" contype="2" conaffinity="1" condim="3" '
              f'friction="{self.mu:.6g} 0.005 0.0001" solref="{_f(cfg.contact.solref)}" solimp="{_f(cfg.contact.solimp)}" rgba="0.2 0.2 0.2 1" group="0"/>')
        else:
            A(f'{ind}    <joint name="{c}_steer" type="hinge" axis="{_f(nloc)}" damping="1e-6"/>')
            A(f'{ind}    <inertial pos="0 0 0" mass="1e-4" diaginertia="1e-10 1e-10 1e-10"/>')
            A(f'{ind}    <body name="{c}_wheel" pos="0 0 0">')
            A(f'{ind}      <joint name="{c}_roll" type="hinge" axis="0 1 0" damping="1e-7"/>')
            I = 0.5 * self.m * self.radius ** 2
            A(f'{ind}      <inertial pos="0 0 0" mass="{self.m:.6g}" diaginertia="{I / 2:.6g} {I:.6g} {I / 2:.6g}"/>')
            A(f'{ind}      <geom name="{c}_geom" type="cylinder" fromto="0 -0.0005 0 0 0.0005 0" size="{self.radius:.6g}" contype="2" '
              f'conaffinity="1" condim="3" friction="{self.mu:.6g} 0.005 0.0001" solref="{_f(cfg.contact.solref)}" '
              f'solimp="{_f(cfg.contact.solimp)}" rgba="0.2 0.2 0.2 1" group="0"/>')
            A(f'{ind}    </body>')
        A(f'{ind}  </body>')
        A(f'{ind}</body>')

    def mjcf_actuators(self, A, cfg, info):
        c = self.name
        if self.kind in ("ball", "omni"):
            for i in range(2):
                A(f'    <motor name="{c}_m{i}" joint="{c}_r{i}" ctrlrange="{-self.tau_max:.6g} {self.tau_max:.6g}" ctrllimited="true"/>')
        else:
            A(f'    <general name="{c}_steer_p" joint="{c}_steer" gainprm="{self.steer_kp:.6g}" biastype="affine" biasprm="0 {-self.steer_kp:.6g} {-self.steer_kp * 0.02:.6g}"/>')
            A(f'    <motor name="{c}_drive" joint="{c}_roll" ctrlrange="{-self.tau_max:.6g} {self.tau_max:.6g}" ctrllimited="true"/>')

    def bind(self, pm):
        self.pm = pm
        c = self.name
        self.acts = [pm.ids[k] for k in (f"act:{c}_m0", f"act:{c}_m1", f"act:{c}_steer_p", f"act:{c}_drive") if k in pm.ids]
        self.geom = pm.ids[f"geom:{c}_geom"]

    def reset(self, pm):
        # start with the suspension compressed so the element touches the paper
        pass

    def commands(self):
        if self.kind in ("ball", "omni"):
            return [(f"{self.name}_tau0", -self.tau_max, self.tau_max, "N m"), (f"{self.name}_tau1", -self.tau_max, self.tau_max, "N m")]
        return [(f"{self.name}_steer", -1.0, 1.0, "rad"), (f"{self.name}_tau", -self.tau_max, self.tau_max, "N m")]

    def apply(self, pm, t, cmd):
        for i, a in enumerate(self.acts):
            pm.d.ctrl[a] = float(cmd[i])

    def power(self, pm):
        # mechanical power of the drive torques (electrical losses: ASSUMPTION efficiency 0.3)
        return 0.0

    def contact_force(self, pm):
        """(normal, tangential magnitude) of the element's native contacts with the paper (N)."""
        m, d = pm.m, pm.d
        fn, ft = 0.0, 0.0
        f6 = np.zeros(6)
        for i in range(d.ncon):
            c = d.contact[i]
            if self.geom in (c.geom1, c.geom2):
                mujoco.mj_contactForce(m, d, i, f6)
                fn += f6[0]
                ft += math.hypot(f6[1], f6[2])
        return fn, ft

    def record_channels(self):
        return [f"{self.name}_N", f"{self.name}_ft"]

    def record(self, pm):
        return list(self.contact_force(pm))


# ================================================================================================ multi-plane nose
@dataclass
class MultiPlaneNose(Plugin):
    """Study N's multi-plane nose, realised here as a second actuation plane: the gimbal pivot of the standard nose is
    carried by two lateral slides (pen-local t1 and t2) with a centring flexure k_lat and stroke +-travel_pivot, driven
    by a second pair of voice coils (force K_f2 I, current limit I_max2); the standard coils keep the tilt.  Lateral
    pivot motion moves the ball by the same amount without tilting the nose, tilt moves it by the lever, so together
    they give translation and tilt control of the tip (about +-(travel_pivot + tilt travel), e.g. +-5-8 mm).
    Every default is an ASSUMPTION placeholder until study N hands over its design."""
    name: str = "mpn"
    travel_pivot: float = 3.0e-3         # lateral stroke of the pivot (m)
    k_lat: float = 50.0                  # centring flexure stiffness per axis (N/m)
    c_lat: float = 0.05                  # flexure damping (N s/m)
    m_carrier: float = 3.0e-3            # moving carrier (kg) added to the nose body inertia path
    K_f2: float = 0.74                   # N/A (same coil as the tilt coils)
    I_max2: float = 1.5
    R20: float = 2.47
    fixed_mass: float = 4.0e-3           # second coil set + frame on the handle (kg)
    label: str = "ASSUMPTION placeholder for study N (nose v2, +-5-8 mm tip travel)"

    def __post_init__(self):
        self.coils = [Coil(K_f=self.K_f2, R20=self.R20, I_max=self.I_max2) for _ in range(2)]

    def modify_handle_parts(self, parts):
        return parts + [("mpn_fixed", self.fixed_mass, 0.050, 0.008, 0.006 ** 2 / 2)]

    def mjcf_nose_joints(self, A, ind, cfg, info):
        for i, ax in enumerate(("1 0 0", "0 1 0")):
            A(f'{ind}<joint name="{self.name}_s{i}" type="slide" axis="{ax}" range="{-self.travel_pivot:.6g} {self.travel_pivot:.6g}" '
              f'limited="true" stiffness="{self.k_lat:.6g}" damping="{self.c_lat:.6g}" armature="{self.m_carrier:.6g}" '
              f'solreflimit="1e-3 1"/>')

    def mjcf_actuators(self, A, cfg, info):
        for i in range(2):
            A(f'    <general name="{self.name}_f{i}" joint="{self.name}_s{i}" gear="{self.K_f2:.9g}" '
              f'ctrlrange="{-self.I_max2:.6g} {self.I_max2:.6g}" ctrllimited="true"/>')

    def bind(self, pm):
        self.pm = pm
        self.act = [pm.ids[f"act:{self.name}_f{i}"] for i in range(2)]
        self.jq = [pm.m.jnt_qposadr[pm.ids[f"jnt:{self.name}_s{i}"]] for i in range(2)]
        self.jv = [pm.m.jnt_dofadr[pm.ids[f"jnt:{self.name}_s{i}"]] for i in range(2)]

    def commands(self):
        return [(f"{self.name}_F{i}", -self.K_f2 * self.I_max2, self.K_f2 * self.I_max2, "N") for i in range(2)]

    def apply(self, pm, t, cmd):
        for i in range(2):
            v = pm.d.qvel[self.jv[i]]
            pm.d.ctrl[self.act[i]] = self.coils[i].limit(float(cmd[i]) / self.K_f2, v)

    def power(self, pm):
        return sum(c.R() * pm.d.ctrl[a] ** 2 for c, a in zip(self.coils, self.act))

    def record_channels(self):
        return [f"{self.name}_s0", f"{self.name}_s1"]

    def record(self, pm):
        return [float(pm.d.qpos[j]) for j in self.jq]
