r"""Labelled inputs of simulator v2.

Frames (as H1, stabpen/frames.py): page frame {P} with x, y in the page and z out of the page; pen axis a (ball -> cap)
at altitude theta and azimuth phi; t1 = sin(th) h - cos(th) n (tilt plane, toward the paper side); t2 = (-sin phi,
cos phi, 0).  Pen-local frame: x = t1, y = t2, z = a, origin at the ball centre of the nose held centred.  Positions
along the pen are z (m) from the ball centre toward the cap.

Evidence labels: SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, PROPOSED DESIGN (the Rev H layout).
Nothing in this package has been measured on hardware or people.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ROOT

D2R = math.pi / 180.0
G_PHYS = 9.80665
LAYOUT = os.path.join(ROOT, "results", "revH", "layout.json")

LABELS: Dict[str, Tuple[str, str]] = {}


def lab(name: str, label: str, source: str) -> None:
    LABELS[name] = (label, source)


# ================================================================================ Rev H geometry (layout.json)
def _layout() -> Dict:
    if os.path.exists(LAYOUT):
        return json.load(open(LAYOUT))
    return {}


_L = _layout()


def _comp(cid: str) -> Optional[Dict]:
    for c in _L.get("components", []):
        if c["id"] == cid:
            return c
    return None


def _zc(cid: str, default: float) -> float:
    c = _comp(cid)
    return 0.5 * (c["z0"] + c["z1"]) * 1e-3 if c else default


@dataclass
class Geometry:
    theta_deg: float = float(_L.get("tilt_deg", 50.0))
    phi_deg: float = 0.0
    length: float = float(_L.get("length", 170.0)) * 1e-3
    handle_od: float = float(_L.get("handle_od", 22.0)) * 1e-3
    r_b: float = 0.35e-3                     # ball radius (H1 CONTACT r_b)
    skid_R: float = float(_L.get("skid_contact_radius", 6.75)) * 1e-3
    skid_open_deg: float = 120.0             # C ring opening on the top (away from the paper)
    skid_rho: float = 0.6e-3                 # lip tube radius (1.16 mm wall, 1.5 mm long ring)
    skid_segments: int = 31                  # capsules over the 240 deg arc (odd: one centred on t1)
    z_p: float = float(_L.get("pivot_z", 45.0)) * 1e-3
    z_a: float = float(_L.get("actuator_z", 79.0)) * 1e-3
    travel: float = float(_L.get("tip_travel_mm", 3.0)) * 1e-3
    travel_stop: float = 3.5e-3
    z_f: float = 0.032                       # finger-pad zone centre (layout hand.finger_pads_z 26/32/38)
    z_w: float = float((_L.get("hand") or {}).get("web_z", 92.0)) * 1e-3
    z_imu: float = _zc("imu", 0.09125)
    r_imu: float = 1.0e-3                    # radial offset of the IMU (layout offset x 1.0 mm)
    z_hall_sensor: float = _zc("hall3d", 0.08525)
    z_hall_magnet: float = _zc("hall_magnet", 0.08325)
    z_page_sensor: float = _zc("optical", 0.017)
    z_endcap: Tuple[float, float] = (0.151, 0.169)   # rear module envelope (rm_frame)
    front_stop_margin: float = 0.3e-3        # tilt-adaptive refill front stop (DEC-026 / touchdown study), axial

    def vectors(self, theta_deg: Optional[float] = None, phi_deg: Optional[float] = None):
        th = (self.theta_deg if theta_deg is None else theta_deg) * D2R
        ph = (self.phi_deg if phi_deg is None else phi_deg) * D2R
        h = np.array([math.cos(ph), math.sin(ph), 0.0])
        n = np.array([0.0, 0.0, 1.0])
        a = math.cos(th) * h + math.sin(th) * n
        t1 = math.sin(th) * h - math.cos(th) * n
        t2 = np.array([-math.sin(ph), math.cos(ph), 0.0])
        return a, t1, t2, n, h

    def p_nom(self, theta_deg: Optional[float] = None) -> float:
        """Axial distance of the skid contact plane behind the ball centre with both on the paper (H1 protrusion_centre)."""
        th = (self.theta_deg if theta_deg is None else theta_deg) * D2R
        return (self.skid_R * math.cos(th) - self.r_b) / math.sin(th)


lab("geom", "PROPOSED DESIGN", "results/revH/layout.json (Rev H-B): tilt 50 deg, skid contact radius 6.75 mm (DEC-034, "
    "opt/inertial/front_end.py), gimbal 45 mm, coils 79 mm, travel 3.0 mm usable / 3.5 mm stop, IMU 90-92.5 mm, Hall 84.75-85.75 mm")
lab("geom.theta", "LIT (CON-02)", "writing altitude about 50 deg; 35-75 deg allowed (REQ-RVH-002)")
lab("geom.skid_rho", "ASSUMPTION", "lip tube radius 0.6 mm (layout: lip wall 1.16 mm, ring 1.5 mm long)")
lab("geom.z_imu", "PROPOSED DESIGN", "layout imu z 90-92.5 mm; the opt/inertial tracker runs used 100 mm (kept for the H1 check)")


# ================================================================================ mass properties (opt/inertial/revh.py)
WIRING = 0.10
lab("mass.wiring", "ASSUMPTION", "+10 % wiring and adhesives on every part (P0/H1 convention)")


def _rev_h():
    from opt.inertial import revh as RH
    return RH, RH.RevH()


def part_lists(wiring: float = WIRING):
    """(handle parts, nose parts without the refill, refill parts); each part (name, m kg, z m, L m, r2 m^2), x(1 + wiring)."""
    RH, d = _rev_h()
    hp = [(n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in RH.handle_parts(d)]
    npar = [(n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in RH.nose_parts(d) if n != "refill_D1"]
    rf = [(n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in RH.nose_parts(d) if n == "refill_D1"]
    return hp, npar, rf


def rigid_props(parts, z_ref: float = 0.0):
    """Mass, CoM z, transverse inertia about the CoM and axial inertia of axisymmetric parts on the pen axis."""
    m = sum(p[1] for p in parts)
    zg = sum(p[1] * p[2] for p in parts) / m
    Jt = sum(p[1] * ((p[2] - zg) ** 2 + p[3] ** 2 / 12.0 + p[4]) for p in parts)
    Ja = sum(p[1] * 2.0 * p[4] for p in parts)
    return {"m": m, "z_g": zg, "J_t": Jt, "J_a": max(Ja, 1e-10)}


lab("mass.parts", "CALC (PROPOSED DESIGN)", "opt/inertial/revh.handle_parts/nose_parts (Rev H: handle 67.1 g, nose 7.9 g incl. "
    "the 0.84 g D1 refill, DEC-004), transverse inertia of tubes and rods as uniform bodies")


# ================================================================================ hand (H1: HAP-26)
@dataclass
class HandH1:
    k_nib: float = 575.0        # tip-referred grip stiffness (N/m)
    b_nib: float = 1.3          # N s/m
    M: float = 0.21             # hand mass (kg)
    k_arm: float = 170.0        # arm spring to the imposed path (N/m)
    b_arm: float = 11.0         # N s/m
    r_rot: float = 0.5          # share of the nib compliance from pen tilt in the grip (ASSUMPTION, EXP-I01)
    rho_w: float = 0.3          # web share of the translational grip stiffness (ASSUMPTION)
    k_roll: float = 0.2         # grip torsional stiffness about the pen axis (N m/rad), ASSUMPTION
    lock_roll: bool = False
    rot_tremor: bool = False    # add the imposed wrist-rotation hinge (H1 wrist-tremor cases)
    grip_scale: float = 1.0
    grip_damp_add: float = 0.0


lab("hand.HAP26", "LIT (HAP-26)", "Fu & Cavusoglu 2012 lumped model at the stylus: k1 575 N/m (228-1043), b1 1.3 N s/m, "
    "M 0.21 kg (0.016-0.57), k2 170 N/m (63-533), b2 11 N s/m (3.7-27.6) (config/parameters.yaml hand.*); per-axis nominal "
    "X/Y/Z k1 380/552/770 N/m, M 0.22/0.27/0.20 kg, k2 79/105/272 N/m")
lab("hand.split", "ASSUMPTION", "r_rot 0.5 (swept 0.3-0.7), rho_w 0.3: unmeasured split of the grip compliance (EXP-I01)")
lab("hand.k_roll", "ASSUMPTION", "grip torsional stiffness 0.2 N m/rad: three pads (HAP-31, 1.5 kN/m) at 11 mm radius give "
    "0.5 N m/rad for the skin alone; finger joints in series lower it (no measurement found)")


# ================================================================================ paper contact
@dataclass
class Contact:
    model: str = "h1"                   # 'h1' (compliant penalty normal + LuGre friction, numba; default for ink studies) |
                                        # 'mujoco' (MuJoCo soft contacts, Coulomb, elliptic cone; geometry-rich plug-ins)
    mu_ball: float = 0.15
    mu_skid: float = 0.12
    mu_rubber: float = 0.6
    # MuJoCo soft-contact settings for contact.model = 'mujoco' (chosen by the contact stage, results/sim2/
    # verification.json: the stiff setting (0.5 ms, 0.99/0.999, impratio 10) creeps least but chatters when the pen
    # slides (normal-force cv about 2.6-3, apparent mu 0.55-1.7); this one slides with mu exactly and cv about 0.25,
    # at the price of about 30 um/s creep in stick)
    solref: Tuple[float, float] = (2e-3, 1.0)
    solimp: Tuple[float, float, float, float, float] = (0.95, 0.99, 1e-4, 0.5, 2.0)
    impratio: float = 1.0
    cone: str = "elliptic"
    noslip_iterations: int = 0
    # H1 contact law (sim/handpen/params.CONTACT)
    ms_ratio: float = 1.3
    v_s: float = 0.002
    presliding: float = 1e-5
    k_sk: float = 1.0e5
    c_sk: float = 10.0
    k_ball: float = 1.0e5
    c_ball: float = 2.0
    skid_point: str = "ring"            # 'ring': analytic lowest point of the C ring; 'fixed': H1's body-fixed point


lab("contact.mu", "ASSUMPTION", "ball on paper 0.15 (config writing.mu_eff; CON-13 0.09-0.165), skid 0.12 (P1/H1; EXP-Q01), "
    "rubber heel element 0.6 (range 0.3-0.8 in the Rev J plan; to measure)")
lab("contact.solref", "SIM (choice)", "MuJoCo soft contact (native mode only): timeconst 2 ms, dampratio 1, solimp (0.95, "
    "0.99, 0.1 mm), impratio 1, elliptic cones; chosen by the contact stage (sliding friction exact, chatter index 0.25; "
    "creep in stick about 30 um/s) over the stiff 0.5 ms / impratio 10 setting (chatters while sliding)")
lab("contact.h1", "ASSUMPTION (H1/P1)", "penalty 1e5 N/m and 10 N s/m at the skid; LuGre normalised by N, mu_s/mu_k 1.3, Stribeck "
    "speed 2 mm/s, presliding 10 um (EXP-Q01, EXP-B01/B02)")
lab("contact.ball_penalty", "ASSUMPTION", "ball penalty 1e5 N/m, 2 N s/m in the H1 contact mode (sim2 has a sliding refill; "
    "H1 used a constant force inside a 0.3 mm margin)")


# ================================================================================ nose, refill, voice coils
@dataclass
class Nose:
    k_r: float = 0.025                  # gimbal bending stiffness per axis (N m/rad)
    zeta_flex: float = 0.02             # flexure structural damping ratio
    Km_act: float = 0.47                # N/sqrt(W) per axis at the magnets
    R: float = 2.47                     # ohm per axis (3.7 V / 1.5 A)
    L_ind: float = 100e-6               # H per axis
    I_max: float = 1.5                  # A (driver limit)
    V_supply: float = 3.7               # V (cell)
    alpha_cu: float = 0.00393           # 1/K
    R_th: float = 100.0                 # K/W coil to ambient
    C_th: float = 0.5                   # J/K
    T_amb: float = 25.0                 # degC
    T_max: float = 120.0                # degC coil limit (IEC class 155 wire derated)
    servo_mode: str = "ref_model"       # 'ref_model' (H1-equivalent) | 'pid'
    servo_hz: float = 80.0
    servo_zeta: float = 0.7
    inner_hz: float = 80.0              # causal servo; frozen sampled-data design in servo_design_study.py
    servo_rate: float = 10000.0
    slew: float = 0.6                   # tip reference slew limit (m/s)
    ref_rate: float = 2000.0            # reference (tracker) rate
    auth_tau: float = 0.05              # contact-gated authority time constant (s)
    q_taper: float = 0.3e-3
    bias: bool = True                   # static load bias (refill spring transverse component), H1 convention
    hall_noise: float = 5e-6            # tip-referred Hall noise (m rms); ASSUMPTION, not measured
    hall_delay: float = 50e-6
    mass_scale: float = 1.0             # diagnostic only: scales the nose and refill mass and inertia
    velocity_source: str = "hall"      # causal measured feedback; 'legacy_true' is an optimistic SIM bound
    velocity_cutoff_hz: float = 300.0   # low-pass on backward Hall differences, fixed before sensitivity study
    hall_max_age: float = 1e-3          # no current demand while feedback is missing/stale
    contact_source: str = "measured"   # delayed refill-slide channel; 'legacy_force' is an optimistic bound

    @property
    def K_f(self) -> float:
        return self.Km_act * math.sqrt(self.R)


lab("nose.k_r", "ASSUMPTION", "gimbal bending 0.025 N m/rad (tip_params.json suspension; laser-cut cross strip, AMF-20)")
lab("nose.coil", "CALC (ASSUMPTION inputs)", "Km 0.47 N/sqrt(W) per axis at the magnets (opt/inertial adjoint design); R 2.47 "
    "ohm so that 3.7 V drives 1.5 A (tip peak 0.84 N, tip_params.json); K_f = Km sqrt(R) = 0.74 N/A; L 100 uH, thermal "
    "100 K/W and 0.5 J/K ASSUMPTION (EXP-I05)")
lab("nose.servo", "ASSUMPTION", "80 Hz, zeta 0.7, 10 kHz inner rate, 0.6 m/s slew (tip_params.json servo); 'ref_model' = H1's "
    "second-order follower realised by an inverse-dynamics + PD inner loop at 400 Hz")


@dataclass
class Refill:
    F_c: float = 0.15                   # constant-force spring (N)
    L_ref: float = 1.0                  # constant-force spring modelled as k = F_c / L_ref, springref -L_ref (0.7 % over 7 mm)
    slide_range: Tuple[float, float] = (-0.3e-3, 8.0e-3)   # axial slide (+ = into the pen); front stop = tilt-adaptive margin
    frictionloss: float = 0.0           # slide friction (N)
    damping: float = 0.01               # N s/m (viscous slide, ASSUMPTION)
    front_stop: str = "nose_adaptive"   # 'nose_adaptive': stop at s = q1 cot(theta) - margin (follows the nose, as H1
                                        # assumes); 'carrier': fixed at -margin on the carrier; 'wide': -(margin +
                                        # travel_stop cot(theta)), always reaching the paper within the travel


lab("refill", "ASSUMPTION", "constant-force spring 0.15 N (P0 value, EXP-Q02); D1 refill 0.84 g (DEC-004) x1.1; front stop "
    "0.3 mm beyond the contact position (tilt-adaptive stop, DEC-026) that follows the nose deflection ('nose_adaptive', "
    "H1's implicit assumption); no slide friction (to measure, EXP-V04)")


# ================================================================================ sensors
@dataclass
class Sensors:
    imu_on: str = "handle"
    hall_rate: float = 10000.0
    hall_noise: float = 5e-6            # tip-referred, m rms
    page_rate: float = 1000.0
    page_latency: float = 2e-3
    page_noise: float = 3e-6
    page_lift_max: float = 0.8e-3
    force_rate: float = 1000.0
    force_noise: float = 5e-3           # N rms (skid-ring load cell)
    force_latency: float = 1e-3
    slide_rate: float = 1000.0
    slide_noise: float = 2e-6
    slide_latency: float = 1e-3
    slide_thr: float = 0.1e-3


lab("sensors.imu", "MFR (OPT-37) + ASSUMPTION", "LSM6DSV16X: 60 ug/sqrt(Hz), 2.8 mdps/sqrt(Hz), ODR 3840 Hz, bias/scale/"
    "misalignment after calibration as fusion/sensors.py")
lab("sensors.hall", "ASSUMPTION (from MFR OPT-45)", "TMAG5273 noise 110-125 uT rms / 16 mT/mm slope = 7 um at the magnet; "
    "5 um rms tip-referred at 10 kHz with averaging")
lab("sensors.page", "ASSUMPTION", "optical flow at 1 kHz, 2 ms latency, 3 um noise (P1 default; EXP-S01)")
lab("sensors.force", "ASSUMPTION", "skid-ring load cell 1 kHz, 5 mN rms, 1 ms (no part selected)")
lab("sensors.slide", "ASSUMPTION", "axial slide Hall 1 kHz, 1 ms, 2 um (fusion ContactSensor)")


# ================================================================================ articulated arm (hand model 'arm')
@dataclass
class Arm:
    # segments (ASSUMPTION: anthropometric order of magnitude for a 70 kg adult; tables not opened)
    m_forearm: float = 0.15             # effective forearm mass moved by the arm base: the forearm rests on the desk and
                                        # HAP-26's lumped model carries only the hand mass (ASSUMPTION; anatomical 1.1 kg)
    L_forearm: float = 0.26
    m_hand: float = 0.42
    hand_com: float = 0.065             # from the wrist toward the fingers
    J_hand: float = 3.0e-3              # about the wrist (kg m^2), H1 WRIST.J (2-4.5e-3)
    m_base: float = 0.05                # effective upper-arm/elbow mass moved by the arm base (kg), ASSUMPTION
    wrist_to_grip: float = 0.085        # wrist centre to the grip elastic centre (m)
    forearm_dir_deg: float = 20.0       # forearm direction in the page from +x (elbow -> wrist is -x rotated)
    # joint impedance (passive + active at co-contraction level cc)
    k_wrist_fe: float = 1.28            # LIT HAP-32 passive (N m/rad)
    k_wrist_rud: float = 1.74
    k_ps: float = 0.25                  # LIT HAP-32 pronation-supination 0.2-0.3
    b_wrist: float = 0.03               # N m s/rad (ASSUMPTION)
    k_base: float = 170.0               # arm base (shoulder/elbow) translational stiffness (N/m), HAP-26 k2
    k_base_y: float = 0.0               # page-y base stiffness (0: same as k_base)
    b_base: float = 11.0
    k_base_z: float = 272.0             # HAP-26 Z k2
    b_base_z: float = 18.0
    k_finger: float = 400.0             # finger stage (N/m) ASSUMPTION
    b_finger: float = 2.0
    cc: float = 1.0                     # co-contraction multiplier on the joint stiffness (DR 1-4, MyoSuite check)
    zeta: float = 0.35                  # damping ratio of the wrist and forearm joints (constant over cc, Perreault 2004)
    hand_rest: bool = False             # ulnar side of the hand resting on the paper
    mu_skin: float = 0.4                # skin on paper (ASSUMPTION)


lab("arm.segments", "ASSUMPTION", "hand 0.42 kg, hand inertia about the wrist 3e-3 kg m^2 (H1 WRIST.J 2-4.5e-3); effective "
    "forearm + upper-arm mass moved by the arm base 0.2 kg (the forearm rests on the desk; anatomical forearm about 1.1 kg); "
    "anthropometric tables not opened")
lab("arm.wrist_k", "LIT (HAP-32)", "passive wrist stiffness [1.28 -0.18; -0.18 1.74] N m/rad (FE, RUD); pronation-supination "
    "0.2-0.3 N m/rad (Formica et al. 2012)")
lab("arm.base", "LIT (HAP-26)", "arm spring 170 N/m, 11 N s/m in the page (Z: 272 N/m, 18 N s/m) at the arm base")
lab("arm.cc", "ASSUMPTION + SIM (MyoSuite check)", "co-contraction multiplier 1-4 on joint stiffness; range from the MyoArm "
    "end-point stiffness study (results/sim2/myo_impedance.json)")


ARM_CALIBRATION = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sim2",
                               "arm_calibration.json")


def calibrated_arm(path: Optional[str] = None) -> "Arm":
    """The arm with its joint impedance fitted to H1's tip impedance (run_study stage 'arm', SIM fit), or the
    passive defaults if the calibration has not been run."""
    import json
    p = path or ARM_CALIBRATION
    if not os.path.exists(p):
        return Arm()
    a = json.load(open(p))["arm"]
    return Arm(k_wrist_fe=a["k_wrist_fe"], k_wrist_rud=a["k_wrist_rud"], k_ps=a["k_ps"], zeta=a["zeta"],
               k_base=a["k_base_x"], k_base_y=a["k_base_y"], k_base_z=a["k_base_z"], b_base=a["b_base"],
               b_base_z=a["b_base_z"])


# s2r/config names (validation/sim_to_real.md, results/s2r/*.json 'values') -> sim2 fields.  The Rev H nose is
# identified by the same B03/B05 methods as the pencil stage (EXP-I05 / EXP-V02); k_tip is tip-referred at the ball.
S2R_MAP = {
    "actuator.R20": ("nose", "R"), "actuator.L": ("nose", "L_ind"), "actuator.Rth_coil_amb": ("nose", "R_th"),
    "actuator.Cth_coil": ("nose", "C_th"), "stage.zeta_open": ("nose", "zeta_flex"), "sensing.hall_delay": ("nose", "hall_delay"),
    "writing.mu_eff": ("contact", "mu_ball"), "writing.mu_static_ratio": ("contact", "ms_ratio"),
    "writing.stribeck_speed": ("contact", "v_s"), "friction.x_presliding": ("contact", "presliding"),
    "writing.paper_stiffness": ("contact", "k_ball"), "skid.mu": ("contact", "mu_skid"),
    "hand.grip_stiffness": ("hand", "k_nib"), "hand.grip_damping": ("hand", "b_nib"), "hand.mass": ("hand", "M"),
    "hand.arm_stiffness": ("hand", "k_arm"), "hand.arm_damping": ("hand", "b_arm"), "hand.r_rot": ("hand", "r_rot"),
    "sensing.opt_noise": ("sensors", "page_noise"), "sensing.opt_delay": ("sensors", "page_latency"),
    "sensing.hall_noise_tip": ("sensors", "hall_noise"),
}


def from_identified(values: Dict[str, float], base: Optional["Config"] = None) -> "Config":
    """A sim2 configuration from identified bench parameters (s2r pipeline output, e.g. results/s2r/*.json 'values',
    or a bench identification of the Rev H pen with the same names).  Unknown names are ignored and listed in
    cfg.label.  actuator.Kf sets the motor constant with R20 (Km = Kf / sqrt(R)); stage.k_tip sets the gimbal bending
    stiffness k_r = k_tip z_p^2; writing.paper_stiffness sets both penalty stiffnesses of the H1 contact law."""
    cfg = base or Config()
    groups = {"nose": {}, "contact": {}, "hand": {}, "sensors": {}}
    unknown = []
    for k, v in values.items():
        if k in S2R_MAP:
            g, f = S2R_MAP[k]
            groups[g][f] = float(v)
        elif k not in ("actuator.Kf", "stage.k_tip"):
            unknown.append(k)
    if "writing.paper_stiffness" in values:
        groups["contact"]["k_sk"] = float(values["writing.paper_stiffness"])
    R = groups["nose"].get("R", cfg.nose.R)
    if "actuator.Kf" in values:
        groups["nose"]["Km_act"] = float(values["actuator.Kf"]) / math.sqrt(R)
    if "stage.k_tip" in values:
        groups["nose"]["k_r"] = float(values["stage.k_tip"]) * cfg.geom.z_p ** 2
    return cfg.replace(nose=replace(cfg.nose, **groups["nose"]), contact=replace(cfg.contact, **groups["contact"]),
                       hand=replace(cfg.hand, **groups["hand"]), sensors=replace(cfg.sensors, **groups["sensors"]),
                       label=(cfg.label + " | " if cfg.label else "") + "identified" + (f" (ignored: {', '.join(unknown)})" if unknown else ""))


# s2r names -> sim2 Gymnasium DR keys (env.DR), for narrowing the randomisation to identified intervals
S2R_DR_MAP = {"writing.mu_eff": "mu_ball", "writing.mu_static_ratio": "ms_ratio", "writing.stribeck_speed": "v_s",
              "friction.x_presliding": "presliding", "hand.grip_stiffness": "k_nib", "hand.grip_damping": "b_nib",
              "hand.mass": "M", "hand.arm_stiffness": "k_arm", "hand.arm_damping": "b_arm", "sensing.opt_delay": "page_latency",
              "sensing.hall_noise_tip": "hall_noise", "skid.mu": "mu_skid"}


def identified_values(path: str, truth_id: Optional[str] = None) -> Tuple[Dict[str, float], Dict[str, float]]:
    """(values, U95) from an s2r identification file (results/s2r/c1_identification.json style: per_truth[*].estimates
    {name: {value, U95}}), or from a flat {'values': {...}} / {'estimates': {...}} JSON of a bench identification."""
    import json
    o = json.load(open(path))
    est = None
    if "per_truth" in o:
        pts = o["per_truth"]
        pt = next((p for p in pts if truth_id is None or p.get("id") == truth_id), pts[0])
        est = pt["estimates"]
    elif "estimates" in o:
        est = o["estimates"]
    if est is not None:
        vals = {k: float(v["value"]) for k, v in est.items() if isinstance(v, dict) and "value" in v}
        u95 = {k: float(v.get("U95", float("nan"))) for k, v in est.items() if isinstance(v, dict) and "value" in v}
        return vals, u95
    vals = {k: float(v) for k, v in o["values"].items()}
    return vals, {k: float("nan") for k in vals}


def dr_ranges_from_identified(values: Dict[str, float], u95: Dict[str, float], widen: float = 1.0) -> Dict[str, Tuple[float, float]]:
    """Identified intervals (value +- widen*U95) on the Gymnasium DR keys, for SimOpt-style narrowing (docs/sim_v2.md 8.4)."""
    out = {}
    for k, key in S2R_DR_MAP.items():
        if k in values and k in u95 and math.isfinite(u95[k]):
            v, u = values[k], widen * u95[k]
            out[key] = (max(v - u, 0.0), v + u)
    return out


# ================================================================================ configuration of one case
@dataclass
class Config:
    geom: Geometry = field(default_factory=Geometry)
    hand_model: str = "h1"              # 'h1' | 'arm'
    hand: HandH1 = field(default_factory=HandH1)
    arm: Arm = field(default_factory=Arm)
    contact: Contact = field(default_factory=Contact)
    nose: Nose = field(default_factory=Nose)
    refill: Refill = field(default_factory=Refill)
    sensors: Sensors = field(default_factory=Sensors)
    plugins: List = field(default_factory=list)
    dt: float = 25e-6
    integrator: str = "implicitfast"
    gravity: bool = False               # H1 convention: the push force is the net writing force; True for the 'arm' hand
    N0: float = 1.0
    wiring: float = WIRING
    nose_on: bool = True                # False: the nose is welded to the handle (a rigid pen)
    record_hz: float = 4000.0
    label: str = ""

    def replace(self, **kw):
        return replace(self, **kw)

    def to_dict(self):
        d = asdict(self)
        d["plugins"] = [p.describe() for p in self.plugins]
        return d


def h1_check_config(r_rot: float = 0.5, **kw) -> Config:
    """H1 reproduction: explicitly optimistic, noiseless/true-velocity servo.

    This historical consistency check is not a sensor-realistic controller.
    Normal Config() uses causal Hall velocity instead.
    """
    g = Geometry(z_imu=0.100, r_imu=0.0)
    kw.setdefault("nose", Nose(hall_noise=0.0, velocity_source="legacy_true", inner_hz=400.0,
                               contact_source="legacy_force"))
    return Config(geom=g, hand=HandH1(r_rot=r_rot, lock_roll=True), contact=Contact(model="h1", skid_point="fixed"),
                  gravity=False, **kw)


def labels_table() -> List[Dict]:
    return [{"name": k, "label": v[0], "source": v[1]} for k, v in sorted(LABELS.items())]
