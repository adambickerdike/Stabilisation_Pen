r"""The refill in the integrated Rev J pen: slide range with the final heel, holder and tendon travel, the fatigue-rated
ink-force spring in the pen-lift drum, the front stop that follows the nose (DEC-041), and refill replacement.

CALC on a PROPOSED DESIGN; inputs ASSUMPTION unless a ledger id is given (revj/params.py).  Nothing built or measured.

Architecture (study N's proposal, made consistent here).
  * The D1 refill (67 mm, DEC-004) push-fits into a holder at its rear end.  The holder rides a closed tendon loop:
    drum -> forward along the refill to a FRONT pulley (in front of the holder's foremost position) -> holder -> back to
    a REAR pulley (behind the holder's rearmost position, on the arm between the gimbal and the magnet cap) -> drum.
    The drum is an annulus around the refill's path just in front of the gimbal (study N: within 5 mm of it), so the
    holder can slide through it.  (Study N's text routes one strand "from the holder back to the drum"; with 26.6 mm of
    slide the holder passes the drum, so that strand needs the rear pulley.)
  * A spiral (clock) spring inside the drum sets the ink force: M = k phi, strip 301 full hard, pre-coiled.  It is
    preloaded so that the force stays within +-20 % over the whole slide (phi_min >= 2 x the working angle).
  * The pen lift (study N): an electro-permanent brake locks the drum; a bistable latch turns it a little (0.5 mm lift).
  * The front stop that follows the nose (DEC-041) is the same brake, commanded by the refill-slide sensor: while the
    ball is on the paper, the slide sits where the geometry puts it; when the pen is lifted the spring pushes the refill
    out; the brake locks as soon as the slide exceeds the contact position by 0.3 mm (sim2's stop margin).  A fixed
    mechanical stop at the largest geometric extension + 0.3 mm is the backstop if the brake fails.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths
from . import params as PA

ensure_paths()
from opt.inertial.front_end import FrontRules, R_B, protrusion  # noqa: E402

RU = FrontRules()
REFILL_L = 67.0                     # mm, D1 mini refill (DEC-004)
HOLDER_L = 5.0                      # mm, ASSUMPTION (study N used 6 mm): 3 mm socket + 2 mm tendon anchors
LIFT_STROKE = 0.5                   # mm, pen-lift stroke (study N, LIT PAT-41)
FRONT_STOP_MARGIN = 0.3             # mm beyond contact (sim2 s5.8; DEC-041)
DRUM_Z = (68.0, 75.0)               # mm, pen-lift module in front of the gimbal (study N layout)


def slide_geometry(fe: Dict, cap_front: float, gimbal_rear: float) -> Dict:
    """Refill and holder travel from the closure `fe` (revj.frontend.close) and the nose's parts (CALC)."""
    lo, hi = fe["refill_slide_mm"]              # slide = extension ahead of the 50 deg rest position (+ = toward the paper)
    back = -lo                                  # largest retraction
    fwd = hi                                    # largest extension
    hold_rear_max = REFILL_L + HOLDER_L + back + LIFT_STROKE      # holder's rear face at its rearmost (pen lifted at 75 deg)
    hold_front_min = REFILL_L - fwd - FRONT_STOP_MARGIN          # holder's front face at its foremost (35 deg + margin)
    rear_pulley = (hold_rear_max + 0.2, hold_rear_max + 1.2)     # 1 mm pulley just behind the holder's rearmost
    out = {"slide_range_mm": fe["refill_slide_range_mm"], "slide_mm": [lo, hi], "retraction_max_mm": back,
           "extension_max_mm": fwd, "tendon_travel_mm": fe["refill_slide_range_mm"] + LIFT_STROKE + FRONT_STOP_MARGIN,
           "holder_length_mm": HOLDER_L, "holder_rear_max_z_mm": hold_rear_max, "holder_front_min_z_mm": hold_front_min,
           "rear_pulley_z_mm": list(rear_pulley), "cap_front_z_mm": cap_front, "gimbal_rear_z_mm": gimbal_rear,
           "rear_pulley_to_cap_mm": cap_front - rear_pulley[1],
           "front_pulley_z_mm": [hold_front_min - 3.0, hold_front_min - 2.0],
           "drum_z_mm": list(DRUM_Z),
           "holder_passes_drum": bool(hold_rear_max > DRUM_Z[0]),
           "label": "CALC (closure revj.frontend; holder length, lift stroke, pulley size ASSUMPTION)"}
    out["fits"] = bool(out["rear_pulley_to_cap_mm"] >= 0.3 and rear_pulley[0] >= gimbal_rear)
    return out


# --------------------------------------------------------------------------------------------------- spiral spring
STRIP_T_UM = (25.0, 30.0, 38.0, 40.0, 50.0, 64.0)     # precision strip thicknesses tried (ASSUMPTION series)


def spiral_spring(travel_mm: float, F_nom: float = 0.15, cycles_small: float = 1e8, small_amp_mm: float = 1.3,
                  t_um: Optional[float] = None) -> Dict:
    """Size the drum's spiral spring (CALC; 301 full hard, AMF-20).  Linear spiral: M = k phi, k = E b t^3 / (12 L),
    bending stress sigma = E t phi / (2 L) (change from the pre-coiled free shape).  Force F = M / r_drum.
    +-tol over the working angle needs phi_min >= (1 - tol) / (2 tol) x ... ; here phi_max / phi_min = (1+tol)/(1-tol).
    Static: sigma(phi_max) <= 0.55 UTS.  Fatigue (Goodman, knockdown for 1e8 cycles): small cycles of +-small_amp_mm of
    slide (2 mm tremor: about 0.65 mm of slide per mm of ball travel, study N) about the highest mean stress; large
    cycles over the whole slide (tilt changes, lifts)."""
    E = PA.SPRING["E_GPa"].value * 1e9
    UTS = PA.SPRING["UTS_MPa"].value * 1e6
    Se = PA.SPRING["fatigue_MPa"].value * 1e6 * PA.SPRING["knockdown_1e8"].value
    tol = PA.SPRING["force_tol"].value
    r_d = PA.SPRING["r_drum_mm"].value * 1e-3
    r_h = PA.SPRING["r_hub_mm"].value * 1e-3
    dphi = travel_mm * 1e-3 / r_d
    ratio = (1 + tol) / (1 - tol)
    phi_min = dphi / (ratio - 1)
    phi_max = phi_min + dphi
    M_mid = F_nom * r_d
    k = M_mid / (0.5 * (phi_min + phi_max))
    rows = []
    for t in ([t_um] if t_um else STRIP_T_UM):
        tt = t * 1e-6
        L = E * tt * phi_max / (2 * PA.SPRING["sigma_static_frac"].value * UTS)       # shortest strip within the static limit
        b = 12 * L * k / (E * tt ** 3)
        s_max = E * tt * phi_max / (2 * L)
        s_min = E * tt * phi_min / (2 * L)
        da = small_amp_mm * 1e-3 / r_d
        sa_small = E * tt * da / (2 * L)
        g_small = sa_small / Se + s_max / UTS
        sa_big, sm_big = 0.5 * (s_max - s_min), 0.5 * (s_max + s_min)
        g_big = sa_big / Se + sm_big / UTS
        packed = L * tt / (math.pi * (r_d ** 2 - r_h ** 2))           # share of the drum annulus the strip fills
        rows.append({"t_um": t, "L_mm": L * 1e3, "b_mm": b * 1e3, "sigma_max_MPa": s_max / 1e6, "sigma_min_MPa": s_min / 1e6,
                     "sigma_a_small_MPa": sa_small / 1e6, "goodman_small": g_small, "SF_small": 1 / g_small,
                     "goodman_large": g_big, "SF_large": 1 / g_big, "annulus_fill": packed,
                     "fits": bool(b <= 4.0e-3 and packed <= 0.5)})
    ok = [r for r in rows if r["fits"]]
    best = min(ok, key=lambda r: abs(r["b_mm"] - 2.5)) if ok else None
    thetas = np.array([35.0, 50.0, 75.0])
    return {"r_drum_mm": r_d * 1e3, "working_angle_rad": dphi, "working_turns": dphi / (2 * math.pi),
            "phi_min_rad": phi_min, "phi_max_rad": phi_max, "k_N_m_per_rad": k, "M_mid_mNm": M_mid * 1e3,
            "force_range_N": [F_nom * (1 - tol), F_nom * (1 + tol)], "rows": rows, "chosen": best,
            "cycles_small": cycles_small,
            "ball_normal_force_N": {f"{t:g}": float(f / math.sin(math.radians(t))) for t, f in
                                    zip(thetas, (F_nom * (1 - tol), F_nom, F_nom * (1 + tol)))},
            "ball_normal_note": "wound so that the force is lowest with the refill extended (35 deg) and highest retracted "
                                "(75 deg): the ball's normal force F / sin(theta) then varies only 0.19-0.21 N (CALC)",
            "label": "CALC (linear spiral spring, Goodman with the AMF-20 fatigue strength x 0.8 knockdown, ASSUMPTION)"}


def reflected_mass(k_sp: float = 0.0) -> Dict:
    """Axial moving mass of the refill path (g): refill + holder/pulleys + the drum rotor's inertia reflected through the
    capstan (m r_rim^2 / r_d^2 with a thin sleeve at the capstan radius: its full mass).  CALC, ASSUMPTION masses."""
    m_refill = 0.84
    m_holder = 0.5
    m_drum = PA.SPRING["m_drum_rotor_g"].value
    m_spring = 0.1                                     # a third of the strip's mass moves (ASSUMPTION)
    m = m_refill + m_holder + m_drum + m_spring
    return {"refill_g": m_refill, "holder_pulleys_g": m_holder, "drum_reflected_g": m_drum, "spring_g": m_spring,
            "total_g": m, "max_accel_m_s2_at_0.12N": 0.12 / (m * 1e-3),
            "need_accel_m_s2_12Hz_2mm": (2 * math.pi * 12) ** 2 * 1.3e-3,
            "label": "CALC (masses ASSUMPTION: refill 0.84 g DEC-004 via Rev H; holder 0.5 g study N)"}


# --------------------------------------------------------------------------------------------------- front stop
def front_stop(R_s: float, z_p: float, X: float, theta: float = 50.0) -> Dict:
    """The front stop that follows the nose (CALC).  Sensitivities of the contact position L (gimbal to ball along the
    nose) to tilt and nose deflection; the lock threshold; the ink tail left at a pen lift; the fixed-stop margin DEC-041
    names as the alternative."""
    th = math.radians(theta)
    dL_dth = -(R_s - R_B * math.cos(th)) / math.sin(th) ** 2             # mm/rad (d p / d theta)
    slide_per_mm = 0.65                                                   # mm of slide per mm of ball travel in the tilt plane (study N)
    tilt_err_deg = 0.5                                                    # ASSUMPTION: fused tilt estimate while writing
    lift_speed = 30.0                                                     # mm/s, ASSUMPTION pen-lift speed
    t_det = FRONT_STOP_MARGIN / (lift_speed / math.sin(th)) * 1e3         # ms until the slide exceeds contact by the margin
    t_brake = 3.0                                                         # ms, ASSUMPTION electro-permanent brake engage
    writing_speed = 30.5                                                  # mm/s, LIT CON-20 (adult phrase speed)
    tail = writing_speed * (t_det + t_brake) * 1e-3
    theta_min = math.radians(35.0)
    fixed_margin = X / math.tan(theta_min) + FRONT_STOP_MARGIN            # DEC-041's fixed-stop alternative
    lift_followed_fixed = fixed_margin * math.sin(th)                     # a free refill then follows lifts of this height
    return {"dL_dtheta_mm_per_deg": dL_dth * math.pi / 180.0, "slide_per_mm_ball_travel": slide_per_mm,
            "tilt_error_deg": tilt_err_deg, "L_error_from_tilt_mm": abs(dL_dth * math.radians(tilt_err_deg)),
            "lock_threshold_mm": FRONT_STOP_MARGIN, "detect_ms": t_det, "brake_ms": t_brake,
            "ink_tail_at_lift_mm": tail,
            "fixed_stop_margin_mm": fixed_margin, "lift_followed_with_fixed_stop_mm": lift_followed_fixed,
            "rule": ("lock the drum when (slide - L_contact(theta, q)) > 0.3 mm, where L_contact comes from the IMU tilt "
                     "(gyro-aided) and the nose Hall; release when the wheel-load or writing-force sensor sees contact; "
                     "the slide itself (not the computed L) is the primary signal: a lift shows as a fast extension of "
                     "the slide that the nose's motion does not explain"),
            "labels": {"lift_speed": "ASSUMPTION 30 mm/s", "brake": "ASSUMPTION 3 ms", "writing_speed": "LIT CON-20 30.5 mm/s",
                       "tilt_error": "ASSUMPTION 0.5 deg (gyro-aided tilt while writing)", "margin": "sim2 s5.8 / DEC-041 0.3 mm"}}


REPLACEMENT = [
    "In 'refill change' the pen drives the holder to its front stop and locks the drum (the old refill then protrudes "
    "about 18 mm beyond the nozzle at rest).",
    "Unscrew the nozzle (PEEK cone, 5 mm long, at the ring plane; reachable through the ring's 120 deg top opening with "
    "the fingertips or the supplied key).",
    "Pull the refill forward out of the holder's socket and the carrier (the holder stays on its tendon, deep in the "
    "carrier; nothing else is unhooked).",
    "Push a new D1 refill in until it seats in the holder; screw the nozzle back; the pen releases the drum and checks the "
    "slide with its sensor (a refill that is not seated shows as a wrong rest position).",
]


def summary(fe: Dict, nose: Dict) -> Dict:
    geo = slide_geometry(fe, cap_front=nose["cap_front"], gimbal_rear=nose["z_p"] + 1.5)
    sp = spiral_spring(geo["tendon_travel_mm"])
    return {"slide": geo, "spring": sp, "moving_mass": reflected_mass(),
            "front_stop": front_stop(fe["R_mm"], fe["z_p_mm"], fe["X_nom_mm"]),
            "replacement_steps": REPLACEMENT}
