r"""The whole-pen devices in sim2 (MuJoCo 3.6): PROPOSED DESIGN inputs, SIMULATION outputs.

  CMGTail      a detachable gyroscopic tail module: scissored pairs of control-moment gyroscopes (two tungsten rotors
               spinning in opposite senses on gimbals driven in opposite senses, so the pair's torque lies on one axis
               perpendicular to the pen and the off-axis torques cancel; LIT PAT-37).  mode 'pairs': two pairs, output
               axes t1 and t2 (4 rotors); mode 'turret': one pair on a turret about the pen axis that turns its output
               axis to the tremor's main axis (2 rotors).  Gyroscopic torques are MuJoCo's rigid-body dynamics.  Each
               gimbal is driven by a rate servo with a torque limit (a geared motor with a speed loop); each rotor by a
               spin-speed servo.
  TunedMass    a tungsten mass on transverse flexures tuned to the tremor frequency (passive), with optional
               semi-active retuning of the stiffness (sim2's ReactionMass body, coils unused unless 'active').
  Collar       the fingers and the web hold a collar (saddle); the whole pen pivots in it on a 2-axis gimbal at z_p with
               stiffness K_c and damping c_c, optionally driven by two motors in the collar (Liftware principle, LIT
               ACT-16, ACT-17, PAT-12).  Implemented as a patch of sim2's MJCF: the grip joints move from the pen to the
               collar body and the pen hangs from the collar by two hinges.
Every default is labelled; the sizing is in designs.py (CALC).
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import mujoco
import numpy as np

from . import ROOT  # noqa: F401
from sim2 import builder as B  # noqa: E402
from sim2 import plugins as PL  # noqa: E402
from sim2 import params as P  # noqa: E402

RHO_W = 18000.0          # kg/m^3 tungsten heavy alloy (MFR AMF-49: 18 g/cm^3; AMF-125: 17.0-18.8)


def _f(x) -> str:
    return " ".join(f"{float(v):.9g}" for v in np.atleast_1d(x))


# ================================================================================================ CMG tail module
@dataclass
class CMGTail(PL.Plugin):
    name: str = "gt"
    mode: str = "pairs"                  # 'pairs' (outputs t1 and t2, 4 rotors) | 'turret' (1 pair, 2 rotors)
    z: float = 0.160                     # module centre along the pen (m)
    r_o: float = 11.0e-3                 # rotor ring outer radius (m)
    r_i: float = 5.5e-3                  # inner radius (hub motor inside)
    thick: float = 4.5e-3                # rotor thickness (m)
    rpm: float = 25000.0                 # spin speed
    delta_max: float = 1.0               # gimbal soft limit (rad); hard stop at 1.25 x
    rate_max: float = 60.0               # gimbal rate limit (rad/s)
    tau_g_max: float = 0.030             # gimbal motor torque limit per gimbal (N m)
    kv_g: float = 0.05                   # gimbal rate-servo gain (N m s/rad)
    J_frame: float = 3.0e-7              # gimbal frame + motor rotor inertia about the gimbal axis (kg m^2)
    m_frame: float = 1.5e-3              # gimbal frame mass (kg) per rotor
    spin_kv: float = 0.02                # spin speed servo gain (N m s/rad)
    fixed_mass: float = 30e-3            # housing, spin and gimbal motors, bearings, electronics, cell (kg)
    turret_kp: float = 0.05              # turret position servo (N m/rad)
    label: str = "PROPOSED DESIGN (designs.py CMG tail; rotor tungsten MFR AMF-49; sizes ASSUMPTION)"

    # ---- rotor properties
    @property
    def m_rotor(self) -> float:
        return RHO_W * math.pi * (self.r_o ** 2 - self.r_i ** 2) * self.thick

    @property
    def I_spin(self) -> float:
        return 0.5 * self.m_rotor * (self.r_o ** 2 + self.r_i ** 2)

    @property
    def I_trans(self) -> float:
        return 0.25 * self.m_rotor * (self.r_o ** 2 + self.r_i ** 2) + self.m_rotor * self.thick ** 2 / 12.0

    @property
    def h(self) -> float:
        return self.I_spin * self.rpm * 2 * math.pi / 60.0

    def pairs(self) -> List[str]:
        return ["t1", "t2"] if self.mode == "pairs" else ["tu"]

    def n_rotors(self) -> int:
        return 2 * len(self.pairs())

    @property
    def mass_total(self) -> float:
        return self.fixed_mass + self.n_rotors() * (self.m_rotor + self.m_frame)

    def gimbal_axis(self, out: str) -> np.ndarray:
        """gimbal axis g with g x a = o (pen frame x = t1, y = t2, z = a): o = t1 -> g = t2; o = t2 -> g = -t1."""
        return np.array([0.0, 1.0, 0.0]) if out in ("t1", "tu") else np.array([-1.0, 0.0, 0.0])

    def slot(self) -> float:
        """Axial space one tilting rotor needs at the soft limit (m): r sin(delta) + t/2 cos(delta), both sides."""
        d = self.delta_max * 1.25
        return 2.0 * (self.r_o * math.sin(min(d, math.pi / 2)) + 0.5 * self.thick * math.cos(min(d, math.pi / 2))) + 1.0e-3

    def rotor_z(self) -> List[float]:
        n = self.n_rotors()
        s = self.slot()
        return [self.z + (k - (n - 1) / 2.0) * s for k in range(n)]

    # ---- model generation
    def modify_handle_parts(self, parts):
        L = max(self.slot() * self.n_rotors(), 0.02)
        return parts + [("gt_fixed", self.fixed_mass, self.z, L, 0.012 ** 2 / 2)]

    def mjcf_handle(self, A, ind, cfg, info):
        zs = self.rotor_z()
        lim = self.delta_max * 1.25
        A(f'{ind}<body name="{self.name}_turret" pos="0 0 {self.z:.9g}">')
        if self.mode == "turret":
            A(f'{ind}  <joint name="{self.name}_tu" type="hinge" axis="0 0 1" damping="1e-4"/>')
        A(f'{ind}  <inertial pos="0 0 0" mass="1e-4" diaginertia="1e-9 1e-9 1e-9"/>')
        k = 0
        for p, out in enumerate(self.pairs()):
            g = self.gimbal_axis(out)
            for j in (0, 1):
                dz = zs[k] - self.z
                A(f'{ind}  <body name="{self.name}{p}{j}_g" pos="0 0 {dz:.9g}">')
                A(f'{ind}    <joint name="{self.name}{p}{j}_g" type="hinge" axis="{_f(g)}" range="{-lim:.6g} {lim:.6g}" '
                  f'limited="true" damping="1e-6" solreflimit="2e-3 1"/>')
                Jf = self.J_frame
                A(f'{ind}    <inertial pos="0 0 0" mass="{self.m_frame:.9g}" diaginertia="{Jf:.6g} {Jf:.6g} {Jf:.6g}"/>')
                A(f'{ind}    <body name="{self.name}{p}{j}_r" pos="0 0 0">')
                A(f'{ind}      <joint name="{self.name}{p}{j}_s" type="hinge" axis="0 0 1" damping="0"/>')
                A(f'{ind}      <inertial pos="0 0 0" mass="{self.m_rotor:.9g}" diaginertia="{self.I_trans:.9g} '
                  f'{self.I_trans:.9g} {self.I_spin:.9g}"/>')
                A(f'{ind}      <geom type="cylinder" fromto="0 0 {-self.thick / 2:.6g} 0 0 {self.thick / 2:.6g}" '
                  f'size="{self.r_o:.6g}" rgba="0.55 0.45 0.3 1"/>')
                A(f'{ind}    </body>')
                A(f'{ind}  </body>')
                k += 1
        A(f'{ind}</body>')

    def mjcf_actuators(self, A, cfg, info):
        for p, out in enumerate(self.pairs()):
            for j in (0, 1):
                nm = f"{self.name}{p}{j}"
                A(f'    <general name="{nm}_sv" joint="{nm}_s" gainprm="{self.spin_kv:.6g}" biastype="affine" '
                  f'biasprm="0 0 {-self.spin_kv:.6g}"/>')
                A(f'    <general name="{nm}_gv" joint="{nm}_g" gainprm="{self.kv_g:.6g}" biastype="affine" '
                  f'biasprm="0 0 {-self.kv_g:.6g}" forcerange="{-self.tau_g_max:.6g} {self.tau_g_max:.6g}" forcelimited="true"/>')
        if self.mode == "turret":
            kd = 2 * 0.8 * math.sqrt(self.turret_kp * 5e-6)
            A(f'    <general name="{self.name}_tup" joint="{self.name}_tu" gainprm="{self.turret_kp:.6g}" biastype="affine" '
              f'biasprm="0 {-self.turret_kp:.6g} {-kd:.6g}" forcerange="-0.01 0.01" forcelimited="true"/>')

    def bind(self, pm):
        self.pm = pm
        self.spin_d, self.g_q, self.g_d, self.a_sv, self.a_gv = [], [], [], [], []
        for p, out in enumerate(self.pairs()):
            for j in (0, 1):
                nm = f"{self.name}{p}{j}"
                self.spin_d.append(pm.jnt_dadr(nm + "_s"))
                self.g_q.append(pm.jnt_qadr(nm + "_g"))
                self.g_d.append(pm.jnt_dadr(nm + "_g"))
                self.a_sv.append(pm.ids[f"act:{nm}_sv"])
                self.a_gv.append(pm.ids[f"act:{nm}_gv"])
        self.tu_q = pm.jnt_qadr(self.name + "_tu") if self.mode == "turret" else None
        self.a_tu = pm.ids.get(f"act:{self.name}_tup")
        self.rate_cmd = [0.0] * len(self.pairs())

    def reset(self, pm):
        w = self.rpm * 2 * math.pi / 60.0
        k = 0
        for p, out in enumerate(self.pairs()):
            for j, sgn in enumerate((1.0, -1.0)):
                pm.d.qvel[self.spin_d[k]] = sgn * w
                pm.d.ctrl[self.a_sv[k]] = sgn * w
                pm.d.ctrl[self.a_gv[k]] = 0.0
                k += 1
        if self.a_tu is not None:
            pm.d.ctrl[self.a_tu] = 0.0
        self.rate_cmd = [0.0] * len(self.pairs())

    def commands(self):
        c = [(f"{self.name}_rate_{o}", -self.rate_max, self.rate_max, "rad/s") for o in self.pairs()]
        if self.mode == "turret":
            c.append((f"{self.name}_turret", -math.pi, math.pi, "rad"))
        return c

    def apply(self, pm, t, cmd):
        """cmd: gimbal rate per pair (rad/s, on the first gimbal; the second turns the opposite way) [, turret angle]."""
        k = 0
        for p in range(len(self.pairs())):
            r = float(np.clip(cmd[p], -self.rate_max, self.rate_max))
            dl = pm.d.qpos[self.g_q[k]]
            if (dl >= self.delta_max and r > 0) or (dl <= -self.delta_max and r < 0):
                r = 0.0
            self.rate_cmd[p] = r
            pm.d.ctrl[self.a_gv[k]] = r
            pm.d.ctrl[self.a_gv[k + 1]] = -r
            k += 2
        if self.mode == "turret" and len(cmd) > len(self.pairs()):
            pm.d.ctrl[self.a_tu] = float(cmd[len(self.pairs())])

    def delta(self, pm) -> List[float]:
        return [float(pm.d.qpos[self.g_q[2 * p]]) for p in range(len(self.pairs()))]

    def gimbal_torque(self, pm) -> np.ndarray:
        return np.array([float(pm.d.actuator_force[a]) for a in self.a_gv])

    def power(self, pm) -> float:
        """Mechanical power of the gimbal servos (|tau * rate|, W) - the electrical estimate is in designs.py."""
        P = 0.0
        for k, a in enumerate(self.a_gv):
            P += abs(float(pm.d.actuator_force[a]) * float(pm.d.qvel[self.g_d[k]]))
        return P

    def record_channels(self):
        ch = [f"{self.name}_d{p}" for p in range(len(self.pairs()))]
        ch += [f"{self.name}_tq{k}" for k in range(self.n_rotors())]
        ch += [f"{self.name}_P", f"{self.name}_w0"]
        if self.mode == "turret":
            ch.append(f"{self.name}_tu")
        return ch

    def record(self, pm):
        out = self.delta(pm)
        out += list(self.gimbal_torque(pm))
        out += [self.power(pm), float(pm.d.qvel[self.spin_d[0]])]
        if self.mode == "turret":
            out.append(float(pm.d.qpos[self.tu_q]))
        return out

    def describe(self):
        d = {k: v for k, v in asdict(self).items()}
        d.update(plugin=self.name, label=self.label, m_rotor_g=self.m_rotor * 1e3, h_Nms=self.h,
                 I_spin=self.I_spin, n_rotors=self.n_rotors(), mass_total_g=self.mass_total * 1e3, slot_mm=self.slot() * 1e3)
        return d


# ================================================================================================ tuned mass
def tuned_mass(m: float = 40e-3, f_tune: float = 5.0, zeta: float = 0.08, z: float = 0.160, stroke: float = 5e-3,
               fixed_mass: float = 12e-3, active: bool = False, Km: float = 0.735) -> PL.ReactionMass:
    """A tungsten mass on transverse flexures tuned to f_tune (k = m (2 pi f)^2), damping ratio zeta (eddy-current or
    elastomer, ASSUMPTION); coils present only when 'active' (a driven reaction mass as study K)."""
    k = m * (2 * math.pi * f_tune) ** 2
    c = 2 * zeta * math.sqrt(k * m)
    R = 1.0
    K_f = Km * math.sqrt(R) if active else 1e-6
    rm = PL.ReactionMass(name="tm", m=m, z=z, stroke=(stroke, stroke, 0.0), k_c=k, c_c=c, K_f=K_f, R20=R,
                         I_max=(Km * math.sqrt(1.0) / K_f) if active else 0.0, fixed_mass=fixed_mass,
                         label="PROPOSED DESIGN (designs.py tuned mass; ASSUMPTION flexure and damping)")
    return rm


# ================================================================================================ pivot collar
@dataclass
class Collar:
    z_p: float = 0.060                   # pivot along the pen (m)
    K_c: float = 0.20                    # N m/rad about t1, t2
    c_c: float = 2e-3                    # N m s/rad
    m: float = 14e-3                     # collar / saddle mass (kg)
    z_cm: float = 0.055
    J: float = 8e-6                      # kg m^2
    range_rad: float = 0.30              # hinge hard stop (rad)
    tau_max: float = 0.080               # collar motor torque limit per axis (N m); 0: no motors
    label: str = "PROPOSED DESIGN (designs.py collar; values ASSUMPTION, swept)"


def _handle_span(lines: List[str]) -> Tuple[int, int, str]:
    i0 = next(i for i, ln in enumerate(lines) if ln.lstrip().startswith('<body name="handle"'))
    ind = lines[i0][:len(lines[i0]) - len(lines[i0].lstrip())]
    depth = 0
    for i in range(i0, len(lines)):
        s = lines[i].strip()
        if s.startswith("<body"):
            depth += 0 if s.endswith("/>") else 1
        elif s.startswith("</body>"):
            depth -= 1
            if depth == 0:
                return i0, i, ind
    raise ValueError("handle body not closed")


def patch_collar(xml: str, col: Collar) -> str:
    lines = xml.split("\n")
    i0, i1, ind = _handle_span(lines)
    head = lines[i0]
    quat = re.search(r'quat="([^"]+)"', head).group(1)
    j = i0 + 1
    grip = []
    while lines[j].strip().startswith('<joint name="grip_'):
        grip.append(lines[j])
        j += 1
    body_rest = lines[j:i1]
    new = [f'{ind}<body name="collar" pos="0 0 0" quat="{quat}">'] + grip
    new.append(f'{ind}  <inertial pos="0 0 {col.z_cm:.9g}" mass="{col.m:.9g}" diaginertia="{col.J:.6g} {col.J:.6g} {col.J / 2:.6g}"/>')
    new.append(f'{ind}  <geom type="cylinder" fromto="0 0 0.02 0 0 0.095" size="0.0135" rgba="0.3 0.6 0.4 0.25"/>')
    new.append(f'{ind}  <site name="collar_piv" pos="0 0 {col.z_p:.9g}" size="0.001"/>')
    new.append(f'{ind}  <body name="handle" pos="0 0 0">')
    for nm, ax in (("piv_1", "0 1 0"), ("piv_2", "1 0 0")):
        new.append(f'{ind}    <joint name="{nm}" type="hinge" axis="{ax}" pos="0 0 {col.z_p:.9g}" stiffness="{col.K_c:.9g}" '
                   f'damping="{col.c_c:.9g}" range="{-col.range_rad:.6g} {col.range_rad:.6g}" limited="true" solreflimit="2e-3 1"/>')
    new += ["  " + ln for ln in body_rest]
    new.append(f'{ind}  </body>')
    new.append(f'{ind}</body>')
    lines = lines[:i0] + new + lines[i1 + 1:]
    out = "\n".join(lines)
    if col.tau_max > 0:
        act = "".join(f'    <motor name="piv_m{k}" joint="piv_{k}" ctrlrange="{-col.tau_max:.6g} {col.tau_max:.6g}" '
                      f'ctrllimited="true"/>\n' for k in (1, 2))
        out = out.replace("  </actuator>", act + "  </actuator>", 1)
    out = out.replace('<sensor>', '<sensor>\n    <jointpos name="piv1_q" joint="piv_1"/>\n    <jointpos name="piv2_q" joint="piv_2"/>', 1)
    return out


def recompile(pm: B.PenModel, xml: str) -> B.PenModel:
    """sim2.builder.build's tail on a patched MJCF: compile, ids, the same info and plug-ins, bind, reset."""
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
    info = dict(pm.info)
    info["skid_geoms"] = [ids[k] for k in ids if k.startswith("geom:skid")]
    info["nq"], info["nv"], info["nu"] = m.nq, m.nv, m.nu
    out = B.PenModel(cfg=pm.cfg, xml=xml, m=m, d=d, ids=ids, info=info, plugins=list(pm.plugins))
    for pl in out.plugins:
        pl.bind(out)
    B.reset(out)
    return out


def build(cfg: P.Config, collar: Optional[Collar] = None) -> B.PenModel:
    """The Rev J pen (sim2j.revj.build: the lead's parts, heel drive, optional end-cap) with this study's plug-ins in
    cfg.plugins, optionally hanging in a pivot collar."""
    from sim2j import revj as RJ
    pm = RJ.build(cfg)
    if collar is None:
        return pm
    pm2 = recompile(pm, patch_collar(pm.xml, collar))
    pm2.info["collar"] = asdict(collar)
    return pm2
