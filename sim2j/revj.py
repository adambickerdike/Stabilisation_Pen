r"""The Rev J pen in simulator v2 (PROPOSED DESIGN inputs from round 1; every model value labelled).

  handle     Rev J layout of study N (results/nose2/layout.json: handle Ø24 x 175 mm, 65.28 g with +10 % wiring, CALC):
             front sleeve, skid ring (contact radius 10.0 mm, DEC-036), page sensor, gimbal mount, shell, fixed coil
             plate of the spherical-gap actuator, PCB, cell, LRA, rear cap; grip zone and finger pads as Rev H.
  nose       the C1S short-arm gimbal (DEC-036): pivot 76.48 mm behind the ball, magnets on an 11.5 mm arm, gimbal
             stiffness 0.0028 N m/rad (0.48 N/m at the tip), tip-equivalent moving mass 2.10 g, Km 0.656 N/sqrt(W) at
             the magnets (0.099 N/sqrt(W) at the tip; image-method magnetics, an upper bound), 3.7 V / 1.5 A drive
             (R 2.47 ohm, K_f 1.03 N/A at the magnets: 0.233 N peak at the tip), usable tip travel 6.0 mm (the
             servo's soft limit), coil 100 uH, 100 K/W, 0.5 J/K (ASSUMPTION as Rev H); 80 Hz servo (as nose2's HW1 runs).
  refill     D1 refill on a 0.15 N spring (ASSUMPTION, EXP-Q02/N06) with the front stop that follows the nose
             deflection 0.3 mm beyond contact (DEC-041 (4); sim2's 'nose_adaptive'), and a pen lift (DEC-036: drum,
             tendon, brake, bistable latch) modelled as a commanded retraction of the front stop by 0.5 mm with an 8 ms
             switching delay (nose2 autowrite convention; PAT-41 0.5-0.64 mm).
  heel drive the 2 mm steered and driven wheel (DEC-037) at the bottom of the ring, wheel.py; its motors, shafts, pod
             and sensors add 6.6 g to the handle (drive layout_parts, CALC), motors at z 50-70 mm (ASSUMPTION: study D
             placed them between Rev H's gimbal and coils; with the C1S nose the lead's revj study decides; its
             results/revJ/sim_params.json did not exist when this ran).
  end-cap    optional detachable reaction mass (DEC-038): 30.4 g tungsten slug, +-4 mm in two axes on 5 Hz flexures
             (damping ratio 0.7), coil force constant 0.735 N/sqrt(W) with a 1 W peak (endcap design 'lrm'), 43.3 g in
             all, centred 173 mm from the tip (ASSUMPTION: behind the Rev J cell, which ends at 161 mm; the pen grows to
             about 185 mm with it).  sim2's ReactionMass plug-in.
The Rev J pen with the heel drive weighs 83.45 + 6.6 = 90 g (CALC; DEC-037's +9.1 g includes a larger front sleeve that
the C1S front already has); with the end-cap 133 g.  Every result from this model is a SIMULATION.
"""
from __future__ import annotations

import contextlib
import json
import math
import os
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ROOT
import sim2  # noqa: F401  (paths, env)
from sim2 import builder as B
from sim2 import params as P
from sim2 import plugins as PL

NOSE2_LAYOUT = os.path.join(ROOT, "results", "nose2", "layout.json")
NOSE2_JSON = os.path.join(ROOT, "results", "nose2", "nose2.json")
REVJ_PARAMS = os.path.join(ROOT, "results", "revJ", "sim_params.json")     # the lead's integration (not present yet)


def _nose2():
    d = json.load(open(NOSE2_JSON))
    return d["recommended"]["design"], json.load(open(NOSE2_LAYOUT))


DES, LAY = _nose2()
Z_P = float(DES["z_p_mm"]) * 1e-3                   # 76.48 mm
Z_A = float(DES["z_a_mm"]) * 1e-3                   # 87.99 mm
M_TIP = float(DES["m_eff_tip_g"]) * 1e-3            # 2.10 g
K_TIP = float(DES["k_tip_N_m"])                     # 0.478 N/m
KM_ACT = float(DES["Km_act"])                       # 0.656 N/sqrt(W) at the magnets
F_PK_TIP = float(DES["F_pk_tip_N"])                 # 0.233 N at 3.7 V / 1.5 A
TRAVEL = float(DES["X_min_mm"]) * 1e-3              # 6.0 mm guaranteed over 35-75 deg
MASS = LAY["mass_g"]                                # nose 18.17, handle 65.28, total 83.45 g (CALC, incl. wiring)

LABELS = {
    "nose": "PROPOSED DESIGN + CALC (results/nose2/nose2.json recommended design, DEC-036)",
    "handle": "PROPOSED DESIGN + CALC (results/nose2/layout.json components; masses scaled to the layout budget)",
    "coil": "CALC (K_f from the 0.233 N peak tip force at 1.5 A; R = (K_f / Km)^2) + ASSUMPTION (L, thermal: Rev H values)",
    "servo": "ASSUMPTION (80 Hz, zeta 0.7, 0.6 m/s slew: Rev H and nose2's HW1 runs)",
    "refill": "ASSUMPTION (0.15 N spring, EXP-Q02/N06) + DEC-041 (4) front stop that follows the nose",
    "pen_lift": "PROPOSED DESIGN (DEC-036): 0.5 mm, 8 ms switching (nose2 autowrite ASSUMPTION; PAT-41)",
    "heel_mass": "CALC (results/drive/layout_parts.json: 6.6 g of new heel-drive parts; motors at z 50-70 mm ASSUMPTION)",
    "endcap": "PROPOSED DESIGN (DEC-038; results/endcap/endcap_study.json designs.lrm); position ASSUMPTION",
}


# ------------------------------------------------------------------------------------------------ mass properties
def _r2_tube(od, id_):
    return (od * od + id_ * id_) / 16.0


def revj_parts(wiring: float = P.WIRING, heel: bool = True):
    """(handle parts, nose parts without the refill, refill parts) in sim2's part-list format (name, m kg, z m, L m,
    r2 m^2), with the +10 % wiring convention.  Handle and nose masses are scaled so that their totals equal the nose2
    layout's budget (handle 65.28 g, nose 18.17 g with wiring) and the nose's inertia about the gimbal gives the
    design's tip-equivalent moving mass of 2.10 g (CALC)."""
    comp = {c["id"]: c for c in LAY["components"]}

    def zc(cid):
        c = comp[cid]
        return 0.5 * (c["z0"] + c["z1"]) * 1e-3, (c["z1"] - c["z0"]) * 1e-3

    hp = []
    for cid, od, id_, m in (("skid_ring", 0.0215, 0.0188, 0.10), ("front_sleeve", 0.024, 0.0188, 6.29),
                            ("optical", 0.006, 0.0, 1.0), ("gimbal", 0.020, 0.012, 2.0), ("shell", 0.024, 0.022, 11.74),
                            ("coil_plate", 0.022, 0.004, 8.71), ("pcb", 0.012, 0.0, 5.0), ("battery", 0.0145, 0.0, 20.0),
                            ("lra", 0.008, 0.0, 1.0), ("rear_cap", 0.024, 0.0, 3.0), ("hall3d", 0.004, 0.0, 0.2),
                            ("usb", 0.008, 0.0, 0.8)):
        z, L = zc(cid)
        hp.append([cid, m * 1e-3, z, L, _r2_tube(od, id_)])
    target_h = MASS["handle_g"] * 1e-3 / (1 + wiring)
    s = target_h / sum(p[1] for p in hp)
    hp = [(n, m * s * (1 + wiring), z, L, r2) for n, m, z, L, r2 in hp]
    if heel:
        # study D's new heel-drive parts (results/drive/layout_parts.json), CALC; the larger front sleeve is already in
        # the C1S front end
        for n, m, z, L, r2 in (("heel_motors", 5.0e-3, 0.0595, 0.020, 0.003 ** 2),
                               ("heel_shafts_keel", 0.67e-3, 0.030, 0.040, 0.004 ** 2),
                               ("heel_pod_wheel", 0.19e-3, 0.009, 0.004, 0.001 ** 2),
                               ("heel_sensors_gears", 0.61e-3, 0.030, 0.030, 0.004 ** 2),
                               ("heel_drivers", 0.15e-3, 0.101, 0.004, 0.004 ** 2)):
            hp.append((n, m * (1 + wiring), z, L, r2))
    npar = []
    for cid, od, id_, m in (("carrier", 0.007, 0.006, 2.8), ("carrier_nozzle", 0.005, 0.002, 0.4), ("arm", 0.005, 0.0, 0.23),
                            ("magnet_cap", 0.020, 0.0, 9.75), ("refill_lift", 0.006, 0.003, 2.0)):
        z, L = zc(cid)
        npar.append([cid, m * 1e-3, z, L, _r2_tube(od, id_)])
    z, L = zc("refill_spring")
    rf = [("refill_D1", 0.84e-3, 0.035, 0.064, 0.00235 ** 2 / 16), ("refill_holder", 0.5e-3, z, L, 0.003 ** 2 / 4)]
    # the layout's part masses give a tip-equivalent mass of about 1.5 g; the design model's 2.10 g includes more mass
    # far from the gimbal (carrier, channel, nozzle).  Scale the distal parts (carrier, nozzle) so that the nose + refill
    # inertia about the gimbal / z_p^2 = 2.10 g; the magnet cap, arm and pen lift keep their layout masses (CALC)
    J = lambda parts: sum(m * (1 + wiring) * ((zz - Z_P) ** 2 + LL * LL / 12 + r2) for _, m, zz, LL, r2 in parts)
    distal = [p for p in npar if p[0] in ("carrier", "carrier_nozzle")]
    rest = [p for p in npar if p[0] not in ("carrier", "carrier_nozzle")]
    k = (M_TIP * Z_P ** 2 - J(rf) - J(rest)) / J(distal)
    npar = [(n, m * (k if n in ("carrier", "carrier_nozzle") else 1.0) * (1 + wiring), z, L, r2) for n, m, z, L, r2 in npar]
    rf = [(n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in rf]
    return hp, npar, rf, {"nose_scale": k, "handle_scale": s}


@contextlib.contextmanager
def _parts_patch(heel: bool):
    """sim2.builder takes its part lists from sim2.params.part_lists (Rev H).  Swap in the Rev J lists for one build
    (runtime substitution in this process only; sim2's files are not edited)."""
    orig = P.part_lists

    def revj(wiring=P.WIRING):
        hp, npar, rf, _ = revj_parts(wiring, heel=heel)
        return hp, npar, rf
    P.part_lists = revj
    try:
        yield
    finally:
        P.part_lists = orig


# ------------------------------------------------------------------------------------------------ configuration
def geometry(theta_deg: float = 50.0) -> P.Geometry:
    comp = {c["id"]: c for c in LAY["components"]}
    zc = lambda cid: 0.5 * (comp[cid]["z0"] + comp[cid]["z1"]) * 1e-3
    return P.Geometry(theta_deg=theta_deg, length=LAY["length"] * 1e-3, handle_od=LAY["handle_od"] * 1e-3,
                      skid_R=LAY["skid_contact_radius"] * 1e-3, z_p=Z_P, z_a=Z_A, travel=TRAVEL,
                      travel_stop=TRAVEL + 0.5e-3, z_f=0.032, z_w=0.092, z_imu=zc("imu"), r_imu=1.0e-3,
                      z_hall_sensor=zc("hall3d"), z_hall_magnet=zc("hall_magnet"), z_page_sensor=zc("optical"),
                      z_endcap=(0.161, 0.185), front_stop_margin=0.3e-3)


def nose() -> P.Nose:
    R = 2.47
    K_f = F_PK_TIP * (Z_P / (Z_A - Z_P)) / 1.5        # N/A at the magnets from the peak tip force at 1.5 A
    Km = K_f / math.sqrt(R)
    return P.Nose(k_r=K_TIP * Z_P ** 2, zeta_flex=0.02, Km_act=Km, R=R, L_ind=100e-6, I_max=1.5, V_supply=3.7,
                  servo_hz=80.0, servo_zeta=0.7, inner_hz=400.0, slew=0.6, q_taper=0.6e-3)


def refill() -> P.Refill:
    return P.Refill(F_c=0.15, slide_range=(-0.3e-3, 26e-3), front_stop="nose_adaptive")


class HeelMass(PL.Plugin):
    """The heel drive's fixed parts are in revj_parts(heel=True); this plug-in only documents them (no bodies: the wheel
    itself is the wheel.py kernel)."""
    name = "heel"
    label = LABELS["heel_mass"]

    def describe(self):
        return {"plugin": "heel", "label": self.label, "added_g": 6.6}


def endcap_plugin(z: float = 0.173) -> PL.ReactionMass:
    """DEC-038 reaction mass as sim2's ReactionMass: 30.4 g, +-4 mm, 5 Hz flexure, damping ratio 0.7, coil limit from
    the design's 1 W peak (F = Km sqrt(1 W) = 0.735 N; ASSUMPTION R 1 ohm so I_max = 0.735 / K_f)."""
    m = 30.39e-3
    k_c = m * (2 * math.pi * 5.0) ** 2
    c_c = 2 * 0.7 * math.sqrt(k_c * m)
    Km = 0.7353
    R = 1.0
    K_f = Km * math.sqrt(R)
    F_peak = Km * math.sqrt(1.0)
    return PL.ReactionMass(name="rm", m=m, z=z, stroke=(4.0e-3, 4.0e-3, 0.0), k_c=k_c, c_c=c_c, K_f=K_f, R20=R,
                           I_max=F_peak / K_f, fixed_mass=(44.996 - 30.386) * 1e-3,
                           label=LABELS["endcap"])


def config(hand_model: str = "h1", heel: bool = True, endcap: bool = False, theta_deg: float = 50.0,
           r_rot: float = 0.5, N0: float = 1.0, dt: float = 25e-6, arm: Optional[P.Arm] = None,
           hand: Optional[P.HandH1] = None, contact: Optional[P.Contact] = None, label: str = "Rev J") -> P.Config:
    plugins = []
    if heel:
        plugins.append(HeelMass())
    if endcap:
        plugins.append(endcap_plugin())
    kw = dict(geom=geometry(theta_deg), nose=nose(), refill=refill(), plugins=plugins, N0=N0, dt=dt,
              hand_model=hand_model, label=label)
    if hand_model == "h1":
        kw["hand"] = hand or P.HandH1(r_rot=r_rot)
        kw["gravity"] = False
    else:
        kw["arm"] = arm or P.calibrated_arm()
        kw["gravity"] = False
    if contact is not None:
        kw["contact"] = contact
    return P.Config(**kw)


def build(cfg: P.Config) -> B.PenModel:
    heel = any(isinstance(p, HeelMass) for p in cfg.plugins)
    with _parts_patch(heel):
        pm = B.build(cfg)
    pm.info["revj"] = {"heel": heel, "endcap": any(isinstance(p, PL.ReactionMass) for p in cfg.plugins)}
    return pm


def mass_summary(pm: B.PenModel) -> Dict:
    H, N, RF = pm.info["handle"], pm.info["nose"], pm.info["refill"]
    extra = 0.0
    for pl in pm.plugins:
        if isinstance(pl, PL.ReactionMass):
            extra += pl.m
    m_tot = H["m"] + N["m"] + RF["m"] + extra
    return {"handle_g": H["m"] * 1e3, "nose_g": N["m"] * 1e3, "refill_g": RF["m"] * 1e3, "moving_extra_g": extra * 1e3,
            "total_g": m_tot * 1e3, "nose_I_pivot_kgm2": pm.info["nose_I_pivot"],
            "m_tip_equiv_g": pm.info["nose_I_pivot"] / Z_P ** 2 * 1e3, "K_f_N_per_A": pm.info["K_f"],
            "tip_force_per_A_N": pm.info["K_f"] * pm.info["coil_arm"] / Z_P,
            "label": "CALC (sim2 model mass properties of the Rev J pen)"}
