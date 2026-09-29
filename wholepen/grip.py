r"""Task 2: a justified grip model with sensitivity bounds (LIT + CALC), and how freely a held pen can pivot.

Model (the one every simulation of this study uses; identical to H1's and to study K's): the pen touches the hand in
two zones fixed to the hand frame - the finger pads (thumb, index, middle; centre z_f = 32 mm, pads 26-38 mm on the
Rev J handle) with transverse stiffness k_f, axial stiffness and a pad tilt stiffness kappa_f, and the thumb-index
web (z_w = 92 mm) with transverse stiffness k_w - calibrated so that the pen tip sees the measured stylus-grip
impedance of LIT HAP-26 (575 N/m, 1.3 N s/m) in every direction, for any split r_rot (share of the tip compliance
that comes from the pen rotating in the grip) and web share rho_w.  The split is not measured (EXP-I01).
Literature bounds used as cross-checks (not fitted):
  finger-pad skin in shear   k = 1.48 n^0.35 N/mm per pad at normal force n (LIT HAP-31); pad forces while writing on
                             paper 3.1 / 2.1 / 1.3 N (thumb / index / middle, children; LIT CON-75)
  finger joints              MCP/PIP/DIP stiffness 0.45-0.71 N m/rad while tapping, 1.0-1.7 N m/rad expected for an
                             extended MCP at higher forces (LIT HAP-115)
  wrist                      passive stiffness 1.28 / 1.74 N m/rad (FE / RUD), pronation-supination 0.2-0.3 (LIT HAP-32);
                             sim2's articulated arm reaches the HAP-26 tip impedance with the wrist 8 x stiffer (co-contraction)
  pen attitude in writing    about 50 deg to the paper, varying about 2.5 deg, rarely more than 10 deg (LIT CON-02)
  grip force                 4-6 N from the three digits (LIT CON-05), 4.3 x the writing force (LIT CON-07)
Outputs: the zone values for r_rot 0.3 / 0.5 / 0.7 (study K's splits) and grip scales 0.5-2 (HAP-26 95 % CI
228-1043 N/m); the pen's rotational stiffness about the grip's elastic centre; the torque needed to pivot the pen by
1 degree or to move its tip 1 mm by pivoting at 0-10 Hz; the pen's rocking resonance with and without a heavy tail.
Evidence status: CALCULATION on LIT and ASSUMPTION inputs.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from . import ROOT  # noqa: F401
from . import lin as L


def pad_skin_shear(forces=(3.07, 2.11, 1.34)) -> Dict:
    """LIT HAP-31 power law at the digit forces of LIT CON-75 (on paper, controls)."""
    per = [1.48 * n ** 0.35 * 1e3 for n in forces]
    return {"digit_forces_N": list(forces), "per_pad_N_m": per, "three_pads_N_m": float(sum(per)),
            "label": "CALC from LIT HAP-31 (k = 1.48 n^0.35 N/mm) and LIT CON-75 (thumb/index/middle forces on paper)"}


def split_table(r_rots=(0.3, 0.5, 0.7), rho_w: float = 0.3, scales=(0.5, 1.0, 2.0), pen: Dict = None,
                tail: Dict = None) -> List[Dict]:
    """Zone values and pivoting quantities per split and grip scale (CALC)."""
    pen = pen or L.PEN
    rows = []
    for s in scales:
        for r in r_rots:
            h = L.HandP(r_rot=r, rho_w=rho_w, grip_scale=s)
            gz = L.grip_zones(h)
            z_c = gz.z_c
            K_r = gz.K_r
            # pen inertia about the elastic centre (transverse), with an optional rigid tail mass
            m, zg, Jt = pen["m"], pen["z_g"], pen["J_t"]
            J = Jt + m * (zg - z_c) ** 2
            if tail:
                J += tail["m"] * (tail["z"] - z_c) ** 2 + tail.get("J", 0.0)
            f_rock = math.sqrt(K_r / J) / (2 * math.pi)
            rows.append({"grip_scale": s, "r_rot": r, "rho_w": rho_w, "k_f_N_m": gz.k_f, "k_w_N_m": gz.k_w,
                         "kappa_f_Nm_rad": gz.kappa_f, "k_axial_N_m": gz.k_a, "z_c_mm": z_c * 1e3,
                         "K_r_Nm_rad": K_r, "web_share_of_K_r": gz.k_f * gz.k_w * (gz.z_w - gz.z_f) ** 2 / gz.k_t / K_r,
                         "torque_per_deg_mNm": K_r * math.radians(1.0) * 1e3,
                         "torque_per_mm_tip_static_mNm": K_r / z_c * 1e-3 * 1e3,
                         "pen_J_about_zc": J, "rocking_Hz": f_rock, "tail": tail})
    return rows


def pivot_torque_freq(r_rot: float = 0.5, freqs=(1.0, 3.0, 5.0, 8.0, 10.0), tail_m: float = 0.0,
                      tail_z: float = 0.177) -> List[Dict]:
    """Torque on the pen (about t2 and t1) that moves the tip 1 mm at f, in the normal grip (lin.py, H1 hand,
    frictionless paper; CALC)."""
    import torch
    mdl = L.Model(hand=L.HandP(r_rot=r_rot))
    if tail_m > 0:
        mdl.tail = L.Tail(m=tail_m, z=tail_z, J_t=0.0)
    asm = L.Assembly(mdl)
    out = []
    for f in freqs:
        w = 2 * math.pi * f
        g1 = L.amp(asm.tip(asm.solve(w, asm.u_torque_pen(asm.t1))))
        g2 = L.amp(asm.tip(asm.solve(w, asm.u_torque_pen(asm.t2))))
        out.append({"f_Hz": f, "mNm_per_mm_about_t1": 1e-3 / g1 * 1e3, "mNm_per_mm_about_t2": 1e-3 / g2 * 1e3})
    return out


def summary() -> Dict:
    return {"model": __doc__.split("Literature bounds")[0].strip(),
            "skin": pad_skin_shear(),
            "splits": split_table(),
            "splits_heavy_tail": split_table(scales=(1.0,), tail={"m": 0.100, "z": 0.177, "J": 2.0e-5}),
            "pivot_torque": {str(r): pivot_torque_freq(r) for r in (0.3, 0.5, 0.7)},
            "pivot_torque_tail100g": {str(r): pivot_torque_freq(r, tail_m=0.100) for r in (0.3, 0.5, 0.7)},
            "finger_joint_Nm_rad": {"tapping": (0.45, 0.71), "extended_mcp_expected": (1.0, 1.7), "src": "HAP-115"},
            "wrist_Nm_rad": {"FE": 1.28, "RUD": 1.74, "PS": (0.2, 0.3), "src": "HAP-32"},
            "pen_angle": {"mean_deg": 50, "variation_deg": 2.5, "rarely_above_deg": 10, "src": "CON-02"},
            "hap26": {"k1_N_m": 575, "b1_Ns_m": 1.3, "M_kg": 0.21, "k2_N_m": 170, "b2_Ns_m": 11,
                      "k1_CI_N_m": (228, 1043), "src": "HAP-26"},
            "label": "CALC on LIT (HAP-26, HAP-31, HAP-32, HAP-115, CON-02, CON-05, CON-07, CON-75) and ASSUMPTION splits"}
