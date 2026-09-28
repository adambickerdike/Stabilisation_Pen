r"""Rev H: the bigger-grip pen with an active nose (and optional inertial add-on), as configurations of model H1.

Geometry (z from the ball tip toward the back, PROPOSED DESIGN; every mass is CALC from assumed parts, ASSUMPTION):
  handle  Ø22 mm x 170 mm; fixed front sleeve z 18-50 mm with the tripod grip (finger pads 26/32/38 mm, web 92 mm);
          2-axis flexure gimbal at z_p; coils and back iron at z_a; board 84-100 mm; 14500 cell 102-152 mm; rear cap.
  nose    the moving front section: carrier tube with the refill, rear arm through the gimbal to the actuator magnets.
Two architectures (the lead's task, 2026-09-28):
  A  the whole nose carries the writing load (the ball is the only paper contact).  Model: H1 grip-sleeve extension:
     sleeve = handle (grip zones, push force routed through it), pen body = nose (ball carries the full normal force,
     skid_geom (0, 0), mu 0.15), actuated pivot at z_p with voice coils at z_a (force actuator + bias preload), tip
     position servo in the in-loop controller, reference = -(tracker estimate).
  B  a skid ring on the FIXED sleeve carries the writing load; the refill carrier moves on the gimbal inside a large skid
     opening, its refill sliding axially on the P0 constant-force spring.  Model: H1 pen body = handle (skid at the ring's
     contact radius), the H1 kinematic nib stage = the moving refill with the Rev H travel, servo bandwidth and slew;
     actuator forces and power follow from the stage trajectory and the ball loads (post-processing, CALC).
Evidence status: CALCULATION inputs + SIMULATION when run.  Nothing measured.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from sim.handpen import params as HP
from sim.handpen.params import CONTACT, Config, Device, Sleeve, protrusion_centre
from . import catalog as CT

D2R = math.pi / 180.0


@dataclass
class RevH:
    """Design variables of the Rev H active nose (defaults = first cut, ASSUMPTION; optimised in the study)."""
    arch: str = "B"
    travel: float = 3.0e-3            # usable tip travel radius (m)
    z_p: float = 0.045                # gimbal position (adjoint design, opt/inertial/adjoint.py, mu_mass 5 W/kg)
    z_a: float = 0.079                # actuator (magnet) position
    servo_hz: float = 80.0            # tip position-servo bandwidth
    servo_zeta: float = 0.7
    slew: float = 0.6                 # tip reference slew limit (m/s)
    Km_act: float = 0.47              # N/sqrt(W) per axis at the actuator (CALC, adjoint design model; ASSUMPTION inputs)
    mag_w: float = 3.0e-3             # magnet face width (4 magnets, 2 per axis; at the search's lower bound)
    mag_l: float = 6.5e-3             # magnet length along the pen
    mag_t: float = 2.8e-3             # magnet thickness
    coil_t: float = 1.43e-3           # coil thickness
    F_peak_act: float = 1.2           # N per axis at the actuator
    k_r: float = 0.025                # gimbal bending stiffness (N m/rad)
    handle_od: float = 22.0e-3
    length: float = 0.170
    z_f: float = 0.032                # finger-pad zone centre
    z_w: float = 0.092                # thumb-index web
    skid_r: float = 6.75e-3           # B: skid ring contact radius (lowest rim point); front-end closure (front_end.py; the stage results used 5.5)
    mu_ball: float = 0.15             # A: ball friction carrying the full load (config nib.mu_nib, ASSUMPTION)
    bias: bool = True                 # static load bias (B: refill-spring component; A: N cos(theta) at nominal force)
    cell: str = "LIR14500"
    shell: str = "PEEK"               # PEEK (1.30 g/cm3, AMF-24) or Al (2.70, ASSUMPTION)
    extra_mass: float = 0.0           # passive weighted-handle comparator (kg)
    extra_mass_z: float = 0.150
    label: str = ""

    @property
    def lever(self):
        """Tip displacement per actuator displacement (the tip moves opposite to the magnets)."""
        return self.z_p / (self.z_a - self.z_p)

    @property
    def Km_tip(self):
        return self.Km_act / self.lever


# ------------------------------------------------------------------ parts (name, m kg, z m, L m, r2 m^2)
def _tube_r2(do, di):
    return ((do / 2) ** 2 + (di / 2) ** 2) / 4


def nose_parts(d: RevH) -> List[Tuple[str, float, float, float, float]]:
    """Moving nose (CALC from assumed parts): carrier tube (titanium Ø7/6 from the tip to the gimbal), refill (D1 mini, 0.84 g,
    DEC-004), rear arm (aluminium Ø5 from the gimbal to the magnets), 4 NdFeB magnets 4 x 4 x 6 mm (N45, 7.5 g/cm3) and their
    clamp, Hall target magnet."""
    zp, za = d.z_p, d.z_a
    Lt = zp - 0.004
    m_tube = 4.5e3 * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * Lt          # Ti-6Al-4V 4.42 g/cm3 (AMF-21) rounded
    m_arm = CT.RHO_AL * math.pi / 4 * 0.005 ** 2 * max(za - zp, 0.005)
    m_mag = 4 * 7.5e3 * d.mag_w * d.mag_l * d.mag_t
    return [("nose_tube", m_tube, 0.004 + Lt / 2, Lt, _tube_r2(0.007, 0.006)),
            ("refill_D1", 0.84e-3, 0.0345, 0.067, 1.175e-3 ** 2 / 4),
            ("nose_tip_guide", 0.4e-3, 0.004, 0.006, 0.0025 ** 2 / 4),
            ("rear_arm", m_arm, zp + (za - zp) / 2, za - zp, 0.0025 ** 2 / 4),
            ("magnets", m_mag, za, d.mag_l, 0.004 ** 2),
            ("magnet_clamp", 0.6e-3, za, 0.006, 0.004 ** 2)]


def coil_mass(d: RevH):
    """Copper of the four flat coils (fill 0.6, +40 % end turns) plus the soft-iron back ring that forms the shell over the
    coil zone (OD 22 / ID 20 mm, magnet length + 2 x stroke + 3 mm long); CALC."""
    s_mag = d.travel / d.lever
    V_act = 2 * (d.mag_w + 2 * s_mag + 1e-3) * d.mag_l * d.coil_t
    m_cu = CT.RHO_CU * 0.6 * V_act * 1.4 * 2
    Lr = d.mag_l + 2 * s_mag + 3e-3
    m_fe = 7.8e3 * math.pi / 4 * (d.handle_od ** 2 - (d.handle_od - 2e-3) ** 2) * Lr
    return m_cu + m_fe


def handle_parts(d: RevH) -> List[Tuple[str, float, float, float, float]]:
    """Fixed handle (CALC from assumed parts; wiring and adhesive +10 % applied by the caller like the P0 convention)."""
    rho_shell = CT.RHO_PEEK if d.shell == "PEEK" else CT.RHO_AL
    do, wall = d.handle_od, 1.0e-3
    z0s, z1s = 0.050, d.length
    m_shell = rho_shell * math.pi / 4 * (do ** 2 - (do - 2 * wall) ** 2) * (z1s - z0s)
    # front sleeve: structural core (PEEK 1 mm) + TPE overmould (1.1 g/cm3 ASSUMPTION) from the 13 mm opening to 22 mm
    m_front = 1.1e3 * math.pi / 4 * (do ** 2 - 0.015 ** 2) * 0.032 + CT.RHO_PEEK * math.pi / 4 * (0.015 ** 2 - 0.013 ** 2) * 0.032
    cell = CT.CELLS[d.cell]
    parts = [("front_sleeve", m_front, 0.034, 0.032, _tube_r2(do, 0.013)),
             ("shell", m_shell, (z0s + z1s) / 2, z1s - z0s, _tube_r2(do, do - 2 * wall)),
             ("gimbal_mount", 2.0e-3, d.z_p, 0.004, _tube_r2(0.017, 0.010)),
             # coils and back iron at the magnets (adjoint design model: copper + 1 mm soft-iron yokes, +50 % frames)
             ("coils_backiron", coil_mass(d), d.z_a, 0.012, _tube_r2(0.019, 0.012)),
             ("hall_flex", 0.5e-3, d.z_a - 0.006, 0.004, 0.006 ** 2),
             ("pcb", 5.0e-3, 0.092, 0.016, 0.007 ** 2 / 3),
             ("cell", cell.m, 0.102 + cell.L / 2, cell.L, (cell.d / 2) ** 2 / 4 * 2),
             ("lra", 1.0e-3, 0.155, 0.003, 0.004 ** 2 / 2),
             ("rear_cap_usb", 3.0e-3, 0.166, 0.008, (do / 2) ** 2 / 4)]
    if d.arch == "B":
        parts.append(("skid_ring", 0.6e-3, 0.002, 0.004, _tube_r2(0.014, 0.009)))
    if d.extra_mass > 0:
        parts.append(("weight", d.extra_mass, d.extra_mass_z, 0.015, 0.006 ** 2 / 4))
    return parts


def _cad_names():
    parts, _ = HP.cad_parts()
    return [p[0] for p in parts]


def body_mod(parts, wiring=0.10):
    """Replace every P0 CAD part by `parts`; H1 multiplies the CAD parts by (1 + wiring), so the new parts get the same factor
    here (pen_body applies it only to the CAD list).  The new parts are prefixed 'revh_': H1 adds before it removes, and a
    Rev H part named like a P0 CAD part (pcb, skid_ring, refill_D1) would otherwise be removed with it."""
    return {"remove": _cad_names(), "add": [("revh_" + n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in parts]}


def masses(d: RevH) -> Dict[str, float]:
    hp, npar = handle_parts(d), nose_parts(d)
    mh = sum(p[1] for p in hp) * 1.1
    mn = sum(p[1] for p in npar) * 1.1
    zc = (sum(p[1] * p[2] for p in hp) + sum(p[1] * p[2] for p in npar)) * 1.1 / (mh + mn)
    I = sum(p[1] * (p[2] - d.z_p) ** 2 + p[1] * (p[3] ** 2 / 12 + p[4]) for p in npar) * 1.1
    return {"handle_g": mh * 1e3, "nose_g": mn * 1e3, "total_g": (mh + mn) * 1e3, "com_mm": zc * 1e3,
            "nose_inertia_about_pivot_g_mm2": I * 1e9, "moving_mass_at_tip_g": I / d.z_p ** 2 * 1e3}


# ------------------------------------------------------------------ H1 configurations
def config_B(d: RevH, r_rot=0.5, rho_w=0.3, theta_deg=50.0, device: Optional[Device] = None, **kw) -> Config:
    """Architecture B: H1 pen body = handle + nose (rigid at tremor frequencies; the servo is stiff), skid at the ring's
    contact radius, the nib stage = the moving refill with the Rev H travel."""
    parts = handle_parts(d) + nose_parts(d)
    p_nom = protrusion_centre(theta_deg, r_ring=d.skid_r)
    return Config(theta_deg=theta_deg, r_rot=r_rot, rho_w=rho_w, z_f=d.z_f, z_w=d.z_w, body_mod=body_mod(parts),
                  skid_geom=(p_nom, d.skid_r), stage=False, q_lim=d.travel, q_taper=min(0.3e-3, 0.1 * d.travel),
                  q_stop=d.travel + 0.5e-3, stage_hz=d.servo_hz, stage_zeta=d.servo_zeta, stage_slew=d.slew,
                  device=device if device is not None else Device(), **kw)


def sleeve_A(d: RevH, F_bias=(0.0, 0.0)) -> Sleeve:
    hp = handle_parts(d)
    m = sum(p[1] for p in hp) * 1.1
    zg = sum(p[1] * p[2] for p in hp) * 1.1 / m
    J = sum(p[1] * ((p[2] - zg) ** 2 + p[3] ** 2 / 12 + p[4]) for p in hp) * 1.1
    lat = d.travel / d.lever + 0.5e-3          # actuator stop (mechanical) beyond the travel
    return Sleeve(m=m, z_g=zg, J_g=J, z_p=d.z_p, k_pt=1.0e5, k_pa=2.0e5, k_pr=d.k_r, beta_p=2e-5, z_a=d.z_a, act="vcm",
                  k_a=0.0, c_a=0.0, stroke=lat, F_max=d.F_peak_act, preload=tuple(F_bias), push_on_sleeve=True, k_stop=2.0e4,
                  label="Rev H handle (A): nose on a gimbal at z_p, voice coils at z_a")


def config_A(d: RevH, r_rot=0.5, rho_w=0.3, theta_deg=50.0, N0=1.0, **kw) -> Config:
    th = theta_deg * D2R
    # static bias at the actuator for the nominal transverse tip load N0 cos(theta) along -t1 (tip) -> magnets move +t1
    F_tip = N0 * math.cos(th) if d.bias else 0.0
    F_act = F_tip * d.lever
    return Config(theta_deg=theta_deg, N0=N0, r_rot=r_rot, rho_w=rho_w, z_f=d.z_f, z_w=d.z_w,
                  body_mod=body_mod(nose_parts(d)), skid_geom=(0.0, 0.0), mu_skid=d.mu_ball, mu_nib=d.mu_ball,
                  sleeve=sleeve_A(d, (F_act_sign(F_act), 0.0)), stage=False, **kw)


def F_act_sign(F_act):
    """Bias sign: the paper's normal force N n has the transverse part -N cos(theta) t1 at the tip; its moment about the
    gimbal, z_p N cos(theta), is balanced by a force -N cos(theta) z_p / (z_a - z_p) along t1 on the nose at z_a
    (CALC; checked in tests: zero mean servo effort in static writing)."""
    return -F_act


def describe(d: RevH) -> Dict:
    ms = masses(d)
    return {"arch": d.arch, "travel_mm": d.travel * 1e3, "z_p_mm": d.z_p * 1e3, "z_a_mm": d.z_a * 1e3, "lever_tip_per_act": d.lever,
            "Km_tip": d.Km_tip, "servo_hz": d.servo_hz, "servo_zeta": d.servo_zeta, **{k: round(v, 3) for k, v in ms.items()}}
