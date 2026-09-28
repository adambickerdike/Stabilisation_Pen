"""The architectures compared (CALC unless labelled).

(i-a)  magnetic carriage with a permanent-magnet head (axial)        -> recommended
(i-b)  magnetic carriage with an electromagnet head (Langerak, HAP-16)
(i-c)  magnetic carriage with a rotating diametric permanent magnet (variant)
(ii)   planar coil array (PCB coils or iron-core coil grid), no moving parts
(iii)  2-DOF desktop haptic linkage (five-bar pantograph) tied to the pen
(iv)   macro-mini: board for the gross path + the Rev H nose for the fine path;
       passive "cobot" steering (PAT-27) noted as a future handheld idea
"""
from __future__ import annotations

import math

import numpy as np

from . import params as P
from . import magnetics as M
from . import stage as ST


# ----------------------------------------------------------------------------- five-bar pantograph (iii)
def fivebar_jacobian(q1, q5, L1, L2, d):
    """Planar five-bar: motors at (-d/2, 0) and (+d/2, 0), proximal L1, distal L2.

    Returns end point (m) and the Jacobian dp/dq (2x2), or None if unreachable.
    """
    A = np.array([-d / 2, 0.0]) + L1 * np.array([math.cos(q1), math.sin(q1)])
    B = np.array([d / 2, 0.0]) + L1 * np.array([math.cos(q5), math.sin(q5)])
    AB = B - A
    c = np.linalg.norm(AB)
    if c > 2 * L2 or c < 1e-9:
        return None
    h = math.sqrt(L2 ** 2 - (c / 2) ** 2)
    mid = A + AB / 2
    nrm = np.array([-AB[1], AB[0]]) / c
    p = mid + h * nrm
    # numerical Jacobian
    eps = 1e-6
    J = np.zeros((2, 2))
    for k, (dq1, dq5) in enumerate(((eps, 0.0), (0.0, eps))):
        r = fivebar_point(q1 + dq1, q5 + dq5, L1, L2, d)
        if r is None:
            return None
        J[:, k] = (r - p) / eps
    return p, J


def fivebar_point(q1, q5, L1, L2, d):
    A = np.array([-d / 2, 0.0]) + L1 * np.array([math.cos(q1), math.sin(q1)])
    B = np.array([d / 2, 0.0]) + L1 * np.array([math.cos(q5), math.sin(q5)])
    AB = B - A
    c = np.linalg.norm(AB)
    if c > 2 * L2 or c < 1e-9:
        return None
    h = math.sqrt(L2 ** 2 - (c / 2) ** 2)
    return A + AB / 2 + h * np.array([-AB[1], AB[0]]) / c


def fivebar_ik(p, L1, L2, d):
    """Inverse kinematics (elbows out)."""
    out = []
    for base, sgn in ((np.array([-d / 2, 0.0]), +1), (np.array([d / 2, 0.0]), -1)):
        v = p - base
        r = np.linalg.norm(v)
        if r > L1 + L2 or r < abs(L1 - L2):
            return None
        a = math.atan2(v[1], v[0])
        b = math.acos((L1 ** 2 + r ** 2 - L2 ** 2) / (2 * L1 * r))
        out.append(a + sgn * b)
    return out


def pantograph_study(paper=(148.0, 210.0), L1=0.16, L2=0.22, d=0.06, y_off=0.06, tau_Nm=0.15,
                     link_mass_kg=0.03, grid=15) -> dict:
    """Force per motor torque and apparent mass over a paper area in front of the motors (CALC)."""
    w, h = paper[0] * 1e-3, paper[1] * 1e-3
    xs = np.linspace(-w / 2, w / 2, grid)
    ys = np.linspace(y_off, y_off + h, grid)
    fmin, reach, mapp = [], 0, []
    for x in xs:
        for y in ys:
            q = fivebar_ik(np.array([x, y]), L1, L2, d)
            if q is None:
                continue
            r = fivebar_jacobian(q[0], q[1], L1, L2, d)
            if r is None:
                continue
            _, J = r
            s = np.linalg.svd(J, compute_uv=False)
            if s.min() < 1e-6:
                continue
            reach += 1
            fmin.append(tau_Nm / s.max())               # worst-direction force for tau on each motor
            # apparent mass at the pen: proximal link (m L1^2/3) + half a distal link at the elbow,
            # per joint; the other distal halves and a 15 g pen collar at the end point (ASSUMPTION)
            Jq = link_mass_kg * L1 ** 2 / 3 + 0.5 * link_mass_kg * L1 ** 2
            Jinv = np.linalg.inv(J)
            Mx = Jinv.T @ np.diag([Jq, Jq]) @ Jinv + (link_mass_kg + 0.015) * np.eye(2)
            mapp.append(float(np.linalg.eigvalsh(Mx).max()))
    n = grid * grid
    return {"paper_mm": list(paper), "link_L1_m": L1, "link_L2_m": L2, "base_m": d, "motor_torque_Nm": tau_Nm,
            "reach_fraction": reach / n, "force_worst_direction_N": [float(min(fmin)), float(np.median(fmin))] if fmin else None,
            "apparent_mass_kg_median": float(np.median(mapp)) if mapp else None,
            "apparent_mass_kg_p90": float(np.percentile(mapp, 90)) if mapp else None,
            "label": "CALC (rigid five-bar; ASSUMPTION link mass 0.03 kg each, 15 g collar, no rotor inertia)"}


# ----------------------------------------------------------------------------- the table
def comparison(force_rows: list, diam_rows: list, coil: dict, cross: dict, stage_summary: dict,
               sens: dict, panto_a5: dict, panto_a4: dict) -> list:
    g = {round(r["gap_mm"], 2): r for r in force_rows}
    dg = {round(r["gap_mm"], 2): r for r in diam_rows}

    def f(gap, key="lateral_isotropic_N", tab=g):
        r = tab.get(round(gap, 2))
        return None if r is None else round(r[key], 2)

    bw = stage_summary["position_bandwidth_Hz"]
    lat = stage_summary["latency"]["total_effective_ms"]
    pw = stage_summary["power"]
    return [
        {"id": "i-a", "name": "Magnetic carriage, permanent-magnet head (axial) on a CoreXY stage [RECOMMENDED]",
         "lateral_force_vs_gap_N": {f"{k}": f(k) for k in (0.5, 1.0, 2.0, 2.7, 3.0)},
         "force_note": "CALC magpylib; isotropic = weakest direction; best direction x1.3-1.5; the Z-lift scales it down to 0.1 N (15 mm gap) for partial guidance or off",
         "normal_pull_N": f"{f(2.7, 'normal_at_zero_lateral_N')} at zero lateral offset (2.7 mm gap); the controller keeps it lower by raising the Z-lift or using larger offsets",
         "workspace": "A4 (head travel 230 x 317 mm) or A5; the head must reach 10-15 mm beyond the paper edge for full force at the edge",
         "bandwidth_Hz": round(bw, 0), "latency_ms": round(lat, 1),
         "position_accuracy_mm": f"{sens['summary']['ball_noise_rms_mm_median']:.2f} noise, <= {sens['summary']['ball_total_rms_mm_max']:.2f} total at the ball (CALC)",
         "power_heat": f"magnet force 0 W; steppers {pw['board_W_avg']:.1f} W average ({pw['peak_W']:.0f} W peak) at the back corners, not under the page",
         "noise": "stepper and belt: StealthChop chopper claimed inaudible at low speed (MFR AMF-93); to be measured (EXP-G04)",
         "safety": "force bounded by the magnets (breakaway); software cap 0.40 N; yield on override; no pinch points above the glass; power loss leaves at most the passive magnet pull; magnet warnings (pacemakers, cards)",
         "pen_addon": "K&J D42-N52 disc 6.35 x 3.17 mm, 0.75 g, in the heel of the fixed front sleeve (MFR AMF-91)",
         "build": "moderate: 3D-printer-class mechanics, catalogue electronics, one calibration jig"},
        {"id": "i-b", "name": "Magnetic carriage, electromagnet head (Langerak et al.)",
         "lateral_force_vs_gap_N": {"reported": 0.488},
         "force_note": "LIT HAP-16: 488 mN at 11 W through a Sensel Morph tablet and paper; force per watt 0.15 N/sqrt(W) (CALC from LIT)",
         "normal_pull_N": "similar to i-a at equal lateral force (dipole physics), but zero with the coil off",
         "workspace": "as i-a", "bandwidth_Hz": "current loop > 100 Hz; the carriage still has to follow the pen", "latency_ms": "~10 pen-to-magnet, ~20 total (LIT HAP-16)",
         "position_accuracy_mm": "their tablet 6502 DPI, 500 Hz (LIT HAP-16); ours as i-a",
         "power_heat": f"{M.power_for_force(0.4, 0.488 / math.sqrt(11.0)):.1f} W for 0.4 N (CALC from LIT), under the page: touch-temperature and a fan",
         "noise": "fan + stage", "safety": "force off with power off (a plus)", "pen_addon": "ring magnet in the pen (LIT)",
         "build": "moderate; thermal design under the paper is the hard part"},
        {"id": "i-c", "name": "Magnetic carriage, rotating diametric permanent magnet (variant)",
         "lateral_force_vs_gap_N": {k: f(k, "across_azimuth_lateral_N", dg) for k in (0.5, 1.0, 2.0, 2.7, 3.0)},
         "force_note": "CALC magpylib, K&J D8X0DIA 12.7 x 25.4 mm N42 centred under the pen magnet; force points along the head's magnetisation",
         "normal_pull_N": f"0 across the pen azimuth; {f(2.7, 'along_azimuth_normal_N', dg)} N (push up) at full force along it (2.7 mm gap)",
         "workspace": "as i-a", "bandwidth_Hz": "direction set by a rotary axis (small stepper, ~30 ms for 180 deg, ASSUMPTION)", "latency_ms": "as i-a",
         "position_accuracy_mm": "harder: the head field is not axisymmetric, so the Hall ring must rotate with it or carry an angle-dependent calibration",
         "power_heat": "as i-a plus a third motor", "noise": "as i-a", "safety": "as i-a",
         "pen_addon": "as i-a (better with a vertical magnet, which then loses the pen azimuth)",
         "build": "moderate-hard: 4 axes (X, Y, rotation, Z)"},
        {"id": "ii", "name": "Planar coil array under the page, no moving parts",
         "lateral_force_vs_gap_N": {"pcb_km_N_per_sqrtW_at_0.8mm": round(coil["km_N_per_sqrtW"], 3)},
         "force_note": f"CALC magpylib: 6-layer PCB coils at 12 mm pitch in anti-phase pairs; 0.4 N needs {M.power_for_force(0.4, coil['km_N_per_sqrtW']):.0f} W per coil pair. Iron-core grids (FingerFlux: 19 x 12 electromagnets, 3500 turns, 40 V, 255 mA each = 10.2 W, LIT HAP-54) are strong enough to be felt but an A4 grid needs about 165 channels",
         "normal_pull_N": "can be zero (anti-phase pairs)", "workspace": "any size, cost scales with area",
         "bandwidth_Hz": "> 100 (current)", "latency_ms": "~2", "position_accuracy_mm": "the coils can also sense (inductive), unproven here",
         "power_heat": "tens to hundreds of W under the page for 0.4 N: not acceptable", "noise": "silent", "safety": "no moving parts; heat is the hazard",
         "pen_addon": "as i-a", "build": "hard (165+ driver channels, thermal)"},
        {"id": "iii", "name": "2-DOF desktop haptic linkage (five-bar pantograph) tied to the pen",
         "lateral_force_vs_gap_N": {"no_gap": f"{panto_a5['force_worst_direction_N'][0]:.2f}-{panto_a5['force_worst_direction_N'][1]:.2f} N worst direction over A5 with 0.15 N m motors (CALC)"},
         "force_note": "no magnetic gap; research devices: 3D Systems Touch 3.3 N peak, > 0.88 N continuous (MFR HAP-52); Pantograph Mk-II DC-400 Hz (LIT HAP-53)",
         "normal_pull_N": "none (planar), but the linkage's mass and friction are felt (Touch: 45 g apparent mass, 0.26 N backdrive friction, MFR HAP-52)",
         "workspace": f"A5 reachable with 160/220 mm links ({panto_a5['reach_fraction']*100:.0f} % of the grid); A4 needs longer, heavier links ({panto_a4['reach_fraction']*100:.0f} % reachable with 220/300 mm)",
         "bandwidth_Hz": "> 100 (direct drive)", "latency_ms": "~1 (encoders in the loop)",
         "position_accuracy_mm": "0.01-0.06 from encoders (Touch 0.055 mm resolution, MFR HAP-52; Pantograph ~10 um, LIT HAP-53)",
         "power_heat": "a few W in motors beside the page", "noise": "quiet (direct drive); cogging if gimbal BLDC",
         "safety": "active device that can inject energy: needs torque limits and a clutch; scissor pinch points beside the hand; the pen is tethered",
         "pen_addon": "a collar with a ball joint and a light rod (10-20 g, ASSUMPTION); must allow pen lift, tilt and roll",
         "build": "moderate (kits exist for small workspaces), hard for A4"},
        {"id": "iv", "name": "Macro-mini: magnetic board for the gross path + Rev H nose for the fine path (recommended use of i-a)",
         "lateral_force_vs_gap_N": {"board": "as i-a", "nose": "0.21 N continuous, 0.84 N peak at the tip, +/-3 mm (results/revH/tip_params.json)"},
         "force_note": "SIM (board.control): tracing ink error 1.6 mm -> 0.7 mm with full board guidance, -> 0.11-0.14 mm with the nose assisting",
         "normal_pull_N": "as i-a", "workspace": "as i-a", "bandwidth_Hz": "board ~25, nose 80 (Rev H servo)", "latency_ms": "board ~8, nose < 2",
         "position_accuracy_mm": "as i-a; the nose knows its own deflection (Hall)", "power_heat": "as i-a; the pen spends nothing on the board's force (magnet on the handle)",
         "noise": "as i-a", "safety": "as i-a; in learning modes the nose is held central so errors stay visible (HAP-01/05/06)",
         "pen_addon": "as i-a", "build": "as i-a plus a BLE link to the pen",
         "also_considered": "a passive 'cobot' pen that steers a wheel on the paper (PAT-27, expired) uses the paper as ground without a board; not studied here"},
    ]
