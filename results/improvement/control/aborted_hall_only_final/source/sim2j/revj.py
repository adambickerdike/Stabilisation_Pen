r"""The Rev J pen in simulator v2 (PROPOSED DESIGN; every model value labelled).

Two sources of the pen's parameters (config(source=...)):
  'revJ'    (default when present) the lead's integration results/revJ/sim_params.json + results/revJ/layout.json
            (CALC on a PROPOSED DESIGN, round 2): handle 68.89 g with the heel drive (COM 89.8 mm), nose 18.1 g
            about the gimbal at 76.48 mm (tip-equivalent 1.53 g from the layout; study N's model gave 2.10 g), refill
            1.74 g on a 0.15 N spring (-2.19 N/m, 0.01 N friction), skid ring contact radius 11.65 mm, heel wheel at
            12.0 mm (0.35 mm beyond the ring), IMU 56.25 mm from the tip and 8.42 mm off the axis, page sensor 1 kHz,
            2 ms, 3 um, valid up to 2 mm lift, nose Hall noise 3.2 / 6.4 um (5.1 um rms used), end-cap slug 30.39 g at
            152.7 mm on 5 Hz flexures with damping ratio 0.05, pen 144.7 mm long (165.7 mm with the end-cap).
  'round1'  the round-1 assembly described below (study N's layout and design model; used before the lead's file
            existed and for the comparison with nose2's HW1 runs).
Round-1 assembly:

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
REVJ_PARAMS = os.path.join(ROOT, "results", "revJ", "sim_params.json")     # the lead's integration (round 2)
REVJ_LAYOUT = os.path.join(ROOT, "results", "revJ", "layout.json")


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
def _parts_patch(heel: bool, endcap: bool = False, source: str = "round1"):
    """sim2.builder takes its part lists from sim2.params.part_lists (Rev H).  Swap in the Rev J lists for one build
    (runtime substitution in this process only; sim2's files are not edited)."""
    orig = P.part_lists

    def revj(wiring=P.WIRING):
        if source == "revJ":
            hp, npar, rf, _ = lead_parts(wiring, heel=heel, endcap=endcap)
        else:
            hp, npar, rf, _ = revj_parts(wiring, heel=heel)
        return hp, npar, rf
    P.part_lists = revj
    try:
        yield
    finally:
        P.part_lists = orig


# ------------------------------------------------------------------------------------------------ the lead's integration
_LEAD = None


def lead_available() -> bool:
    return os.path.exists(REVJ_PARAMS) and os.path.exists(REVJ_LAYOUT)


def default_source() -> str:
    return "revJ" if lead_available() else "round1"


def lead() -> Dict:
    """results/revJ/sim_params.json and layout.json (read once per process) with their provenance."""
    global _LEAD
    if _LEAD is None:
        import hashlib
        raw = open(REVJ_PARAMS, "rb").read()
        sp = json.loads(raw)
        lay = json.load(open(REVJ_LAYOUT))
        _LEAD = {"sp": sp["sim_params"], "lay": lay,
                 "meta": {"file": "results/revJ/sim_params.json", "generated_utc": sp.get("meta", {}).get("generated_utc"),
                          "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
                          "layout_generated_utc": (lay.get("meta") or {}).get("generated_utc"),
                          "label": sp.get("meta", {}).get("evidence_status")}}
    return _LEAD


def _v(x):
    return x["value"] if isinstance(x, dict) and "value" in x else x


def _lead_part(c: Dict, m: float):
    """A layout component as a sim2 part (name, m kg, z m, L m, r2 m^2): sim2's rigid_props uses J_t = m (dz^2 + L^2/12
    + r2) and J_a = 2 m r2, so r2 = (ro^2 + ri^2)/4 for cylinders and tubes, (sx^2 + sy^2)/24 for boxes, plus half the
    squared radial offset of an off-axis part (its axial and mean transverse contribution)."""
    L = (c["z1"] - c["z0"]) * 1e-3
    z = 0.5 * (c["z0"] + c["z1"]) * 1e-3
    if c["shape"] == "box":
        sx, sy = c["size"][0], c["size"][1]
        r2 = (sx * sx + sy * sy) / 24.0
    else:
        ro = 0.25 * (c.get("d0", 0.0) + c.get("d1", c.get("d0", 0.0)))
        ri = 0.5 * c.get("d_in", 0.0) if c["shape"] == "tube" else 0.0
        r2 = (ro * ro + ri * ri) / 4.0
    ox, oy = c.get("offset", [0.0, 0.0])
    r2 += 0.5 * (ox * ox + oy * oy)
    return (c["id"], m, z, L, r2 * 1e-6)


def lead_parts(wiring: float = P.WIRING, heel: bool = True, endcap: bool = False):
    """(handle, nose without the refill, refill) from the lead's layout (results/revJ/layout.json), x(1 + wiring) as the
    lead's budgets; the refill body is the refill and holder (layout) + the ink drum's reflected 0.3 g and the spring's
    0.1 g (sim_params refill.moving_mass 1.74 g, CALC/ASSUMPTION).  The handle includes the heel drive (the lead's
    'handle' = every part but the moving nose and the end-cap slug); heel=False removes the drive parts (the C1S pen of
    study N, for the comparison with nose2); endcap=True replaces the rear cap by the end-cap's fixed parts (its slug
    and magnets are the ReactionMass body)."""
    L = lead()
    comps = L["lay"]["components"]
    f = 1.0 + wiring
    hp, npar = [], []
    for c in comps:
        m = c.get("mass_g") or 0.0
        if m <= 0:
            continue
        mw, grp = c.get("moves_with"), c["group"]
        if mw == "nose":
            if grp == "refill":
                continue
            npar.append(_lead_part(c, m * 1e-3 * f))
        elif mw in ("handle", "drive"):
            if grp == "drive" and not heel:
                continue
            if grp == "inertial" and not endcap:
                continue
            if endcap and c.get("replaced_by_endcap"):
                continue
            hp.append(_lead_part(c, m * 1e-3 * (1.0 if grp == "inertial" else f)))   # the lead: no allowance on the end-cap
    comp = {c["id"]: c for c in comps}
    zh = 0.5 * (comp["refill_holder"]["z0"] + comp["refill_holder"]["z1"]) * 1e-3
    rf = [_lead_part(comp["refill"], 0.84e-3), _lead_part(comp["refill_holder"], 0.5e-3),
          ("drum_reflected", 0.3e-3, zh, 0.0, 0.0), ("refill_spring", 0.1e-3, zh, 0.0, 0.0)]
    return hp, npar, rf, {"source": "revJ"}


def lead_geometry(theta_deg: float = 50.0) -> P.Geometry:
    """sim2's handle frame has x = t1 toward the paper; the lead's frame has x away from the paper, so its IMU
    offset +8.42 mm (on the board, on the top side) is r_imu = -8.42 mm here and its wheel at x = -12 mm is +12 mm."""
    L = lead()
    sp, lay = L["sp"], L["lay"]
    comp = {c["id"]: c for c in lay["components"]}
    zc = lambda cid: 0.5 * (comp[cid]["z0"] + comp[cid]["z1"]) * 1e-3
    zp = lay["pivot_z"] * 1e-3
    usable = _v(sp["nose"]["usable_angle_rad"])
    stop = _v(sp["nose"]["stop_angle_rad"])
    imu = _v(sp["sensors"]["imu_position_m"])
    ps = _v(sp["sensors"]["page_sensor"])
    return P.Geometry(theta_deg=theta_deg, length=lay["length"] * 1e-3, handle_od=lay["handle_od"] * 1e-3,
                      skid_R=_v(sp["skid_ring"]["contact_radius_m"]), skid_open_deg=_v(sp["skid_ring"]["open_deg_top"]),
                      skid_rho=_v(sp["skid_ring"]["tube_radius_m"]), z_p=zp, z_a=_v(sp["nose"]["actuator_z_m"]),
                      travel=usable * zp, travel_stop=stop * zp, z_f=0.032, z_w=lay["hand"]["web_z"] * 1e-3,
                      z_imu=imu[2], r_imu=-imu[0], z_hall_sensor=zc("nose_hall"), z_hall_magnet=zc("position_magnet"),
                      z_page_sensor=ps["window_m"][2], z_endcap=(comp["ec_shell"]["z0"] * 1e-3, comp["ec_shell"]["z1"] * 1e-3),
                      front_stop_margin=_v(sp["refill"]["front_stop"])["margin_m"])


def _hall_noise() -> float:
    n = _v(lead()["sp"]["sensors"]["nose_position_noise_m"])
    return math.sqrt(0.5 * (n[0] ** 2 + n[1] ** 2))


def lead_nose(neg_k: float = 0.0, km_scale: float = 1.0, kr_scale: float = 1.0) -> P.Nose:
    """C1S nose from sim_params: flexure 0.0028 N m/rad minus the magnetic negative stiffness (0-0.00165 N m/rad,
    nominal 0: sphere centres aligned), Km 0.656 N/sqrt(W) at the magnets (image method: upper bound; DR 0.7-1.0),
    R 2.47 ohm, 100 uH, 1.5 A, 3.7 V, 100 K/W, 0.5 J/K, 80 Hz / 0.7 servo, 0.6 m/s slew, Hall noise 5.1 um rms at the
    tip (3.2 / 6.4 um per axis), 50 us Hall delay.  The servo holds the refill spring's transverse ball load
    F_c cot(theta) with a contact-gated bias current (sim2 H1 convention: Nose.bias)."""
    n = lead()["sp"]["nose"]
    s = lead()["sp"]["sensors"]
    return P.Nose(k_r=_v(n["flexure_k_Nm_per_rad"]) * kr_scale - neg_k, zeta_flex=_v(n["damping_ratio"]),
                  Km_act=_v(n["Km_act_N_per_sqrtW"]) * km_scale, R=_v(n["coil_R_ohm"]), L_ind=_v(n["coil_L_H"]),
                  I_max=_v(n["I_max_A"]), V_supply=_v(n["V_bus_V"]), R_th=_v(n["coil_Rth_K_W"]), C_th=_v(n["coil_Cth_J_K"]),
                  servo_hz=_v(n["servo_hz"]), servo_zeta=_v(n["servo_zeta"]), inner_hz=80.0, slew=_v(n["slew_m_s"]),
                  q_taper=0.6e-3, hall_noise=_hall_noise(), hall_delay=_v(s["nose_position_delay_s"]))


def lead_refill(F_c: Optional[float] = None) -> P.Refill:
    r = lead()["sp"]["refill"]
    Fc = _v(r["spring_force_N"]) if F_c is None else F_c
    grad = abs(_v(r["spring_gradient_N_per_m"]))
    rng = _v(r["slide_range_m"])
    return P.Refill(F_c=Fc, L_ref=max(Fc / max(grad, 1e-6), 1e-3), slide_range=(-0.3e-3, abs(rng[0])),
                    frictionloss=_v(r["friction_hysteresis_N"]), front_stop="nose_adaptive")


def lead_sensors() -> P.Sensors:
    s = lead()["sp"]["sensors"]
    ps = _v(s["page_sensor"])
    sl = _v(lead()["sp"]["refill"]["slide_sensor"])
    return P.Sensors(hall_noise=_hall_noise(), page_rate=ps["rate_hz"], page_latency=ps["latency_s"],
                     page_noise=ps["noise_m"], page_lift_max=ps["lift_cutoff_m"][0], slide_rate=sl["rate_hz"],
                     slide_noise=sl["noise_m"], slide_latency=sl["delay_s"])


def lead_endcap_plugin() -> PL.ReactionMass:
    """The end-cap from sim_params: 30.39 g slug at 152.7 mm, +-4 mm, 30.0 N/m flexures (5 Hz), damping ratio 0.05,
    Km 0.735 N/sqrt(W), 1 W peak (ASSUMPTION R 1 ohm: I_max = F_peak / K_f); its fixed parts are in the handle."""
    ec = lead()["sp"]["endcap"]
    m = _v(ec["slug_mass_kg"])
    k = _v(ec["flexure_k_N_per_m"])
    zeta = _v(ec["damping_ratio"])
    Km = _v(ec["Km_N_per_sqrtW"])
    s = _v(ec["stroke_m"])
    R = 1.0
    K_f = Km * math.sqrt(R)
    F_peak = Km * math.sqrt(_v(ec["P_peak_W"]))
    return PL.ReactionMass(name="rm", m=m, z=_v(ec["slug_centre_z_m"]), stroke=(s, s, 0.0), k_c=k,
                           c_c=2.0 * zeta * math.sqrt(k * m), K_f=K_f, R20=R, I_max=F_peak / K_f, fixed_mass=0.0,
                           label="PROPOSED DESIGN + CALC (results/revJ/sim_params.json endcap; study K)")


def wheel_params(source: Optional[str] = None, mu: float = 0.9):
    """Heel-wheel parameters: the lead's (sim_params heel_wheel: contact at 12.0 mm in the ring plane, i.e. 0.35 mm
    beyond the 11.65 mm ring, 0.55 N preload on a 200 N/m leaf with 0.75 mm travel, rolling coefficient 0.078,
    back-drive 0.03 N, reflected mass 3.8 g; copper loss from the motor data R 8.8 ohm, kt 1.09 mN m/A, 2:1, 0.656
    efficiency, 1 mm wheel radius) or study D's (round 1)."""
    from .wheel import WheelParams
    src = source or default_source()
    if src != "revJ":
        return WheelParams(mu=mu)
    hw = lead()["sp"]["heel_wheel"]
    mot = _v(hw["motor"])
    kF = mot["kt_mNm_A"] * 1e-3 * _v(hw["drive_ratio"]) * _v(hw["drive_efficiency"]) / _v(hw["radius_m"])
    cp = _v(hw["contact_point_m"])
    return WheelParams(mu=mu, R_w=abs(cp[0]), h_w=0.0, P=_v(hw["preload_N"]), travel=_v(hw["spring_travel_m"]),
                       k_s=_v(hw["spring_rate_N_per_m"]), k_lat=_v(hw["k_lat_N_per_m"]), c_rr=_v(hw["rolling_coef"]),
                       m_r=_v(hw["reflected_mass_kg"]), F_bdc=_v(hw["backdrive_N"]), kP_copper=mot["R_ohm"] / kF ** 2,
                       F_peak=_v(hw["F_peak_N"]), F_cont=_v(hw["F_cont_N"]))


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
                  servo_hz=80.0, servo_zeta=0.7, inner_hz=80.0, slew=0.6, q_taper=0.6e-3)


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
           hand: Optional[P.HandH1] = None, contact: Optional[P.Contact] = None, label: str = "Rev J",
           source: Optional[str] = None, F_c: Optional[float] = None, neg_k: float = 0.0, km_scale: float = 1.0) -> P.Config:
    src = source or default_source()
    plugins = []
    if heel:
        plugins.append(HeelMass())
    if endcap:
        plugins.append(lead_endcap_plugin() if src == "revJ" else endcap_plugin())
    if src == "revJ":
        kw = dict(geom=lead_geometry(theta_deg), nose=lead_nose(neg_k=neg_k, km_scale=km_scale),
                  refill=lead_refill(F_c), sensors=lead_sensors())
    else:
        nz = nose()
        if km_scale != 1.0 or neg_k:
            nz = replace(nz, Km_act=nz.Km_act * km_scale, k_r=nz.k_r - neg_k)
        rf = refill() if F_c is None else replace(refill(), F_c=F_c)
        kw = dict(geom=geometry(theta_deg), nose=nz, refill=rf)
    kw.update(plugins=plugins, N0=N0, dt=dt, record_hz=2000.0, hand_model=hand_model, label=f"{label} [{src}]")
    if hand_model == "h1":
        kw["hand"] = hand or P.HandH1(r_rot=r_rot)
        kw["gravity"] = False
    else:
        kw["arm"] = arm or P.calibrated_arm()
        kw["gravity"] = False
    if contact is not None:
        kw["contact"] = contact
    return P.Config(**kw)


def source_of(cfg: P.Config) -> str:
    return "revJ" if "[revJ]" in (cfg.label or "") else "round1"


def build(cfg: P.Config) -> B.PenModel:
    heel = any(isinstance(p, HeelMass) for p in cfg.plugins)
    endcap = any(isinstance(p, PL.ReactionMass) for p in cfg.plugins)
    src = source_of(cfg)
    with _parts_patch(heel, endcap, src):
        pm = B.build(cfg)
    pm.info["revj"] = {"heel": heel, "endcap": endcap, "source": src,
                       "lead": lead()["meta"] if src == "revJ" else None}
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
