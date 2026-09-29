"""Sizing of every heel-drive concept with catalogue parts (CALC; inputs MFR with ledger ids, LIT, ASSUMPTION).

For each concept: the force it can put on the pen at the heel (traction and motor limits), speed, bandwidth, power,
mass, size (the contact radius the nose forces on it), heat, noise, cost class, what pen roll does to it, how it feels
when switched off (reflected mass, back-drive force), safety, and a verdict.  The numbers feed the comparison table of
docs/grounded_drive.md section 3; the two best concepts are then optimised in design_opt.py.

Conventions: forces at the paper contact of the element (N); P = spring preload of the element (N); mu = tyre-paper
friction; the traction limit is mu * min(P, N_heel) (contact.py).  Battery 3.7 V nominal (AMF-80).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

import numpy as np

from . import catalog as CT
from . import contact as CO
from .params import CONTACT, CONTROL

V_BATT = 3.7
MU_LO, MU_HI = CONTACT["mu_drive_range"].value
P_NOM = 0.55                 # N, preload of the chosen design (design_opt.py optimum 0.57, snapped build)
F_TYP_RMS = 0.15             # N, typical RMS drive force while guiding (ASSUMPTION; the SIM tables report the real one)
V_TYP = 0.03                 # m/s, typical writing speed (CON-08 signatures 38-226 mm/s; synthetic writers ~30 mm/s)
V_REQ = 0.15                 # m/s, speed the drive must reach (ASSUMPTION: above most letter-stroke peaks)
BASE_POWER_W = 0.081         # Rev H pen while writing (docs/opt_inertial.md 1; CALC there)
CELL_WH = 0.75 * 3.7         # EEMB LIR14500 750 mAh (AMF-80)


# ----------------------------------------------------------------------------- one motor + gear + output radius
def train(motor: CT.Motor, gear: Optional[CT.Gearhead], r_out: float, V: float = V_BATT) -> Dict:
    """Force and feel of a motor-gear-roller train at an output radius r_out (m) (CALC)."""
    G = gear.ratio if gear else 1.0
    eta = gear.eta if gear else 1.0
    tau_c = motor.tau_cont_mNm * CT.MNM
    tau_pk = min(motor.stall_at(V), motor.tau_stall_mNm * CT.MNM * 1.5)
    F_c = tau_c * G * eta / r_out
    F_pk = tau_pk * G * eta / r_out
    if gear:
        F_c = min(F_c, gear.tau_cont_mNm * CT.MNM / r_out)
        F_pk = min(F_pk, gear.tau_int_mNm * CT.MNM / r_out)
    w0 = motor.n0_at(V) * 2.0 * math.pi / 60.0
    v_max = w0 / G * r_out
    m_r = motor.J() * G * G / (r_out * r_out)
    F_bd = motor.tau_fric_mNm * CT.MNM * G / (eta * r_out)
    kt = motor.kt_mNm_A * CT.MNM
    b_short = (kt * kt / motor.R_ohm) * (G / r_out) ** 2 * eta
    k_P = motor.R_ohm * (r_out / (kt * G * eta)) ** 2               # W per N^2 at the output
    mass = motor.mass_g + (gear.mass_g if gear else 0.0)
    length = motor.l_mm + (gear.l_mm if gear else 0.0)
    return {"motor": motor.key, "gear": gear.key if gear else "direct", "ratio": G, "r_out_mm": r_out * 1e3,
            "F_cont_N": F_c, "F_peak_N": F_pk, "v_noload_m_s": v_max, "m_reflected_g": m_r * 1e3,
            "F_backdrive_N": F_bd, "b_short_N_s_m": b_short, "P_per_N2_W": k_P, "mass_g": mass, "length_mm": length,
            "d_mm": max(motor.d_mm, gear.d_mm if gear else 0.0), "Rth_K_W": motor.Rth_K_W, "T_max_C": motor.T_max_C,
            "ledger": ",".join(sorted({motor.ledger} | ({gear.ledger} if gear else set())))}


def heat(train_row: Dict, F_rms: float, T_amb: float = 30.0) -> Dict:
    P = train_row["P_per_N2_W"] * F_rms * F_rms
    return {"P_cu_W": P, "winding_rise_K": P * train_row["Rth_K_W"] * 1.5,
            "note": "x1.5 for the enclosed pen (ASSUMPTION)"}


# ----------------------------------------------------------------------------- heading rates of handwriting
def heading_rates(writers=(100, 101, 102), text: Optional[str] = None, v_min: float = 5.0, smooth_mm: float = 0.0) -> Dict:
    """Rate of change of the stroke direction (mod pi: a wheel can roll backwards) on synthetic writers' intended
    letters (CALC on SIMULATED writing; tuning writers only).  smooth_mm > 0 low-passes the path first (the wheel then
    follows only the gross path and the nose does the detail)."""
    from . import ensure_paths
    ensure_paths()
    from handwriting import writers as W
    from scipy.ndimage import gaussian_filter1d
    text = text or W.PRACTICE_SENTENCE
    rates, turns, speeds = [], [], []
    dt = 1e-3
    for w in writers:
        wr = W.writer(w).write(text, dt=dt, seed=6000 + w)
        xy = wr.intended.xy * 1e3
        d = wr.intended.pen_down > 0.5
        if smooth_mm > 0:
            # smooth along each pen-down run by arc length (approximately, by time at the mean speed)
            sig = smooth_mm / max(wr.style.speed_mm_s, 1.0) / dt
            xy = np.column_stack([gaussian_filter1d(xy[:, 0], sig), gaussian_filter1d(xy[:, 1], sig)])
        v = np.gradient(xy, dt, axis=0)
        sp = np.hypot(v[:, 0], v[:, 1])
        a2 = np.unwrap(2.0 * np.arctan2(v[:, 1], v[:, 0]))
        r = np.abs(np.gradient(a2, dt)) / 2.0
        m = d & (sp > v_min)
        rates.append(r[m])
        speeds.append(sp[d])
        # corners: runs where the speed is below v_min inside a pen-down stroke; heading change across them
        slow = d & (sp <= v_min)
        edges = np.diff(np.r_[0, slow.astype(np.int8), 0])
        for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
            if a > 0 and b < len(a2) - 1 and d[a - 1] and d[min(b, len(d) - 1)]:
                dth = abs(((a2[b] - a2[a - 1]) / 2.0 + math.pi / 2) % math.pi - math.pi / 2)
                turns.append((math.degrees(dth), (b - a) * dt))
    R = np.concatenate(rates)
    S = np.concatenate(speeds)
    T = np.array(turns) if turns else np.zeros((0, 2))
    big = T[T[:, 0] > 20.0] if len(T) else T
    return {"writers": list(writers), "smooth_mm": smooth_mm, "n": int(len(R)),
            "rate_rad_s_p50_p90_p99": [float(np.percentile(R, q)) for q in (50, 90, 99)],
            "time_share_rate_above_20_rad_s": float(np.mean(R > 20.0)),
            "speed_mm_s_p50_p90_p99": [float(np.percentile(S, q)) for q in (50, 90, 99)],
            "corners_over_20deg": int(len(big)),
            "corner_turn_deg_median": float(np.median(big[:, 0])) if len(big) else 0.0,
            "corner_dwell_ms_median": float(np.median(big[:, 1]) * 1e3) if len(big) else 0.0,
            "label": "CALC on synthetic tuning writers (aiguide glyph writers; not human data)"}


# ----------------------------------------------------------------------------- the concepts
@dataclass
class Row:
    key: str
    name: str
    principle: str
    actuators: str
    force_any_dir_N: str
    force_note: str
    speed_m_s: str
    bandwidth: str
    power_W: str
    mass_g: str
    size: str
    heat: str
    noise: str
    cost_class: str
    roll: str
    off_feel: str
    safety: str
    verdict: str
    labels: str
    ledger: str
    numbers: Dict


def _trac(P=P_NOM):
    return MU_LO * P, MU_HI * P


def concepts(heading: Optional[Dict] = None) -> List[Row]:
    from . import geometry as GE
    lo, hi = _trac()
    rows: List[Row] = []
    tyre = CO.Tyre(r_e=1.0e-3, rho=0.3e-3, t_layer=0.3e-3)           # the chosen 2 mm wheel with a 0.6 mm O-ring cord
    rr = tyre.rolling_resistance(P_NOM) * P_NOM
    a = tyre.hertz(P_NOM)["a_m"]
    geo15 = GE.required_contact_radius(1.5)
    geo10 = GE.required_contact_radius(1.0)
    pod_w = GE.wheel_pod(1.0)["R_d_mm"]                                 # 2 mm wheel + steering ring (CALC)
    pod_b = GE.ball_pod(1.0, 0.4)["R_d_mm"]                             # 2 mm ball + two rollers r 0.4 mm (CALC)
    geo30 = GE.required_contact_radius(3.0)
    geo575 = GE.required_contact_radius(5.75)
    heading = heading or {}
    hr = heading.get("rate_rad_s_p50_p90_p99", [float("nan")] * 3)

    # --- drive trains (catalogue)
    mx, fh, orb = CT.MOTORS["mxDCX6M"], CT.MOTORS["fh0620B"], CT.MOTORS["orbBMN04"]
    t_wheel = train(fh, CT.PATHS["WHEEL_PATH"], 1.0e-3)                  # wheel r 1.0 mm: shafts, bevels 2:1 (design_opt)
    t_roll = train(fh, CT.PATHS["BALL_PATH"], 0.40e-3)                   # ball drive roller r 0.40 mm (design_opt)
    t_steer = train(fh, CT.PATHS["STEER_PATH"], 1.0)                      # r_out 1 m: N = N m (torque at the axis)
    t_steer_mx = train(mx, CT.GEARHEADS["GP6A_3.9"], 1.0)
    t_omni = train(mx, CT.GEARHEADS["GP6A_3.9"], 3.0e-3)                  # custom 6 mm omni-wheel
    t_orb = train(orb, CT.GEARHEADS["SPG04_100"], 1.5e-3)
    steer_rate = t_steer["v_noload_m_s"]                                  # rad/s at the steering axis (r_out = 1 m)
    scrub = CO.scrub_torque(P_NOM, MU_HI, a)

    # 1. driven ball
    P_r = 0.6 / 0.8                  # roller preload to transmit 0.6 N at mu_roller_ball 0.8 (ASSUMPTION)
    scrub_drag_smooth = 0.3 * P_r    # axial slip of the orthogonal roller (LIT AMF-117: "the orthogonal roller must be slipping")
    rows.append(Row(
        "ball", "Driven ball (trackball in reverse)", "Two rollers turn a rubber-coated ball about two axes; the ball pushes on the paper in any direction",
        "2 motors (Faulhaber 0620 B) on shafts to 2 rollers r 0.40 mm (bevel 1:1), 1 idler, preload spring",
        f"{lo:.2f}-{hi:.2f}", f"traction-limited (mu 0.6-1.2 x P {P_NOM} N); motor limit {t_roll['F_cont_N']:.2f} N continuous",
        f"{t_roll['v_noload_m_s']:.2f}", "motor current loop about 1 kHz; the force at once in any direction (no steering)",
        f"{t_roll['P_per_N2_W'] * F_TYP_RMS ** 2 * 2:.3f} (2 motors, {F_TYP_RMS} N RMS)",
        f"{2 * t_roll['mass_g'] + 1.5:.1f}", f"ball d 2 mm with rollers: heel contact radius >= {pod_b:.2f} mm (Rev H 6.75)",
        "negligible (< 1 K winding rise)", "gearhead whine (not quantified; EXP-D06)", "high (2 precision micromotors)",
        "contact survives roll of +/-20 deg with 0.5 mm spring travel; force map rotates with roll (IMU corrects)",
        f"reflected mass {t_roll['m_reflected_g']:.0f} g per axis; back-drive {t_roll['F_backdrive_N']:.2f} N plus the "
        f"orthogonal roller's axial slip about {scrub_drag_smooth:.2f} N with smooth rollers -> retract when off",
        "force <= mu_max x P = 0.6 N by physics; lift = zero force; current cap; slip detection",
        "Strong and holonomic, but the ball drive slips inside itself (LIT AMF-117), wears and collects ink and paper dust "
        "like old mouse balls (PAT-33); second choice",
        "CALC; MFR AMF-100, AMF-103; LIT AMF-117, AMF-118; ASSUMPTION roller friction", "AMF-100,AMF-103,AMF-117,AMF-118",
        {"train": t_roll, "roller_preload_N": P_r, "axial_scrub_drag_N": scrub_drag_smooth, "R_d_mm": pod_b}))

    # 2. omni-wheels
    rows.append(Row(
        "omni", "Two micro omni-wheels", "Two omni-wheels at +/-45 deg to the pen push along their rims and roll freely along their axles",
        "2 motors (maxon DCX 6 M + GP 6 A 3.9:1) + 2 custom omni-wheels d 6 mm (smallest commercial found: 11.5 mm, AMF-110)",
        f"{lo / 2:.2f}-{hi / math.sqrt(2):.2f}",
        "each wheel carries about half the heel load, so along one wheel's axis only half the traction pushes "
        "(0.5-0.71 x mu P, CALC)",
        f"{t_omni['v_noload_m_s']:.2f}", "as the ball", f"{t_omni['P_per_N2_W'] * F_TYP_RMS ** 2 * 2:.3f}",
        f"{2 * t_omni['mass_g'] + 1.0:.1f}", f"6 mm wheels: heel contact radius >= {geo30['R_d_mm']:.1f} mm; 11.5 mm "
        f"commercial wheels: >= {geo575['R_d_mm']:.0f} mm (does not fit)", "negligible", "gearhead whine",
        "high (2 micromotors + custom omni-wheels)", "two contacts side by side: roll unloads one wheel",
        f"reflected mass {t_omni['m_reflected_g']:.0f} g per wheel; the rollers clog with paper dust (ASSUMPTION)",
        "as the ball", "Reject: half the traction of one contact, larger, fragile rollers",
        "CALC; MFR AMF-101, AMF-102, AMF-110", "AMF-101,AMF-102,AMF-110",
        {"train": t_omni, "R_d_6mm": geo30["R_d_mm"], "R_d_11p5mm": geo575["R_d_mm"]}))

    # 3. steered wheel (cobot), steer only
    rows.append(Row(
        "steer", "Steered wheel, steer only (cobot)", "A free-rolling wheel is steered; it rolls along its heading and "
        "grips across it, so the writer's own motion is channelled along the letter (LIT HAP-60)",
        "1 steering motor (Faulhaber 0620 B, transfer gears, crown 2:1 on the fork) + Hall angle sensor at the fork; free "
        "wheel d 2 mm with an O-ring tyre",
        f"{lo:.2f}-{hi:.2f} across the path (constraint); 0 along it",
        f"cannot push; the across-path force is a reaction, up to mu x P; along the path only rolling resistance "
        f"{rr * 1e3:.0f} mN (CALC, Persson AMF-112)",
        f"steering {steer_rate:.0f} rad/s no-load (needed: p90 {hr[1]:.0f}, p99 {hr[2]:.0f} rad/s on synthetic letters)",
        f"steering servo about 30-50 Hz (ASSUMPTION); the across-path grip acts at once (mechanical)",
        "about 0.005-0.02 (steering only; power is supplied by the writer)", f"{t_steer['mass_g'] + 1.2:.1f}",
        f"wheel d 2 mm with steering ring: heel contact radius >= {pod_w:.2f} mm", "negligible", "one small motor, intermittent",
        "medium (1 micromotor)", "heading map changes with roll and tilt (IMU corrects); contact survives +/-20 deg",
        f"when not guiding, the wheel must follow the writer's direction (free mode, LIT HAP-60 eq. 2) or retract",
        "intrinsically passive: cannot move the pen by itself (LIT HAP-60, PAT-27); across-path force <= mu_max P",
        "Best guidance per watt and the safest; cannot lead a still or relaxed hand",
        "CALC; LIT HAP-60, AMF-112; MFR AMF-100, AMF-103", "HAP-60,AMF-112,AMF-100,AMF-103",
        {"steer_train": t_steer, "steer_train_alt": t_steer_mx, "scrub_torque_mNm": scrub * 1e3,
         "rolling_resistance_N": rr, "R_d_mm": pod_w}))

    # 4. steered wheel + brake
    b_short = t_wheel["b_short_N_s_m"]
    rows.append(Row(
        "steer_brake", "Steered wheel with an axle brake", "As 3, plus a brake on the wheel: along-path damping (dissipative only)",
        "steering motor + a hub-train motor used as a generator (short-circuit or PWM braking) or a friction brake",
        f"{lo:.2f}-{hi:.2f} across; along the path up to mu x P as braking only",
        f"motor braking {b_short:.1f} N s/m at full short (Faulhaber 0620 B, 2:1, r 1.0 mm); more with a higher ratio",
        "as 3", "as 3", "< 0.02 (braking recovers energy)", f"{t_steer['mass_g'] + t_wheel['mass_g'] + 1.5:.1f}",
        "as 3 plus the hub train", "negligible", "as 3", "high (2 micromotors)", "as 3",
        "as 3", "passive (can only resist)", "Good for tremor: across-path constraint plus along-path damping",
        "CALC; MFR AMF-100, AMF-103", "AMF-100,AMF-103", {"hub_train": t_wheel}))

    # 5. steered + driven wheel (powered cobot)
    rows.append(Row(
        "steer_drive", "Steered and driven wheel (powered cobot)", "As 3, and a motor turns the wheel: it pushes along its "
        "heading, holds across it, and can lead a relaxed hand",
        "steering motor + drive motor (both Faulhaber 0620 B) in the handle; two 0.8 mm shafts in a keel to the heel pod; "
        "crown 2:1 for steering, bevels 2:1 to the axle",
        f"{lo:.2f}-{hi:.2f} in any direction after steering",
        f"traction-limited; motor limit {t_wheel['F_cont_N']:.2f} N continuous, {t_wheel['F_peak_N']:.2f} N peak "
        f"(0620 B at 3.7 V, 2:1, three meshes, r 1.0 mm)", f"{t_wheel['v_noload_m_s']:.2f}",
        "drive: current loop about 1 kHz; direction: steering servo about 30-50 Hz",
        f"{t_wheel['P_per_N2_W'] * F_TYP_RMS ** 2:.3f} drive + steering", f"{t_steer['mass_g'] + t_wheel['mass_g'] + 2.0:.1f}",
        f"wheel d 2 mm with steering ring: heel contact radius >= {pod_w:.2f} mm", "negligible", "two small motors",
        "high (2 micromotors, watch-scale bevel)", "as 3",
        f"reflected mass along the heading {t_wheel['m_reflected_g']:.1f} g; back-drive {t_wheel['F_backdrive_N'] * 1e3:.0f} mN "
        f"(so it can stay down and follow the writer)",
        "force <= mu_max x P by physics; current cap; slip detection; lift = zero",
        "Recommended: the strongest guidance, can lead a relaxed hand ('writes for you' at gross scale), low power",
        "CALC; LIT HAP-60; MFR AMF-100, AMF-103", "HAP-60,AMF-100,AMF-103", {"drive_train": t_wheel,
                                                                              "drive_train_4mm": t_orb}))

    # 6. braked ball
    rows.append(Row(
        "brake_ball", "Braked ball (variable damping)", "A ball rolls with the pen; an electromagnetic, MR or piezo brake "
        "slows it: resistance in every direction, never a push",
        "1 brake (solenoid pad as the Reflective Haptics stylus, HAP-68; or MR fluid AMF-108; or a SQUIGGLE-pressed pad AMF-106)",
        f"0-{hi:.2f} opposing motion only", "isotropic: it cannot tell writing from tremor, so it resists both",
        "n/a (passive)", "solenoid 5-20 ms (ASSUMPTION); SQUIGGLE 7 mm/s is too slow to modulate at tremor rates",
        "0.02-0.3 (solenoid holding current, ASSUMPTION)", "3-6 (ASSUMPTION)",
        f"ball d 2 mm: heel contact radius >= {geo10['R_d_mm']:.1f} mm plus the brake", "coil heat near the fingers if held on",
        "quiet", "low-medium", "roll-invariant ball, contact as the ball", "a free ball: light",
        "passive; brake force <= mu P", "Tremor damping only; weak for guidance; roll-invariant",
        "CALC; LIT HAP-68; MFR AMF-106, AMF-108", "HAP-68,AMF-106,AMF-108", {}))

    # 7. controllable friction pads
    area = 24e-6
    ea = [p * area for p in (1e3, 5e3)]
    rows.append(Row(
        "friction_pad", "Controllable friction pads", "Electroadhesion pulls the paper to a heel pad; or ultrasonic "
        "vibration lowers the pad's friction; or a steered anisotropic (scale-like) pad",
        "high-voltage electrode pad; or a piezo pad; or a pad on a steering motor",
        f"electroadhesion {ea[0] * 0.6:.3f}-{ea[1] * 0.6:.3f} extra friction",
        f"a 24 mm2 pad at 1-5 kPa on paper adds {ea[0]:.3f}-{ea[1]:.3f} N of normal force (dielectric targets: pre-contact "
        "pressure 1-100 x below release, AMF-114); ultrasonic squeeze films need a smooth, airtight contact (AMF-115; "
        "paper is porous); anisotropic pads (AMF-116) slide with 3-6 x the drag of a rolling wheel (ASSUMPTION ratio)",
        "n/a", "fast (electrostatic ms)", "0.01-0.1 (400-2000 V converter; ASSUMPTION)", "1-3", "a pad on the heel",
        "none", "ultrasonic silent; HV none", "low", "pad under the heel", "none", "high voltage at the fingertips (EA)",
        "Reject: too weak (EA), unlikely on paper (ultrasonic), draggy (anisotropic)",
        "CALC; LIT AMF-114, AMF-115, AMF-116", "AMF-114,AMF-115,AMF-116", {"ea_normal_N": ea}))

    # 8. others
    rows.append(Row(
        "others", "Others considered", "(a) piezo 'walking' foot with the paper as the slider; (b) 4 mm brushless hub "
        "(Orbray BMN04) driving the wheel directly; (c) asymmetric-vibration pseudo-force (study K); (d) desk board",
        "-", f"(b) {t_orb['F_cont_N']:.2f} N continuous at r 1.5 mm with an assumed 100:1 head",
        "(a) paper compliance absorbs the micrometre vibration (ASSUMPTION); (b) too weak and slow: "
        f"{t_orb['v_noload_m_s'] * 1e3:.0f} mm/s no-load; (c) no net force; (d) 0.4 N cap, grounded, separate device",
        "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-",
        "Keep the board for practice at a desk; the others are not pursued", "CALC; MFR AMF-104, AMF-107",
        "AMF-104,AMF-107", {"orbray_train": t_orb}))
    return rows


def table(heading: Optional[Dict] = None) -> List[Dict]:
    return [asdict(r) for r in concepts(heading)]
