#!/usr/bin/env python3
"""Pivot and suspension flexure calculations for the front-pivot lever.

Evidence status: ANALYTICAL CALCULATION (Euler-Bernoulli beams, linear
elastic, nominal dimensions).  Material data: AMF ledger (C17200 TH04:
E 131 GPa, fatigue strength ~310 MPa at 1e8 cycles, AMF-18/19; recommended
allowables: alternating <= 150 MPa, peak <= yield/4 ~ 310 MPa, AMF notes).
Validation: EXP-M02 force-displacement and loaded cycling of flexure coupons.

1) Three-wire conical pivot (Rev A initial concept): a wire whose line of
   action passes through the virtual centre, fixed at the housing end, with
   the inner end rigidly attached to the rotating carrier.  For a rotation psi
   about the centre, the inner end moves v = -r_c psi and rotates psi, giving
   strain energy U = 1/2 EI psi^2 (12 r_c^2 + 12 l r_c + 4 l^2)/l^3 and peak
   bending moment M = EI psi (6 r_c + 4 l)/l^2.
2) Cross-strip (Haberland) pivots arranged as a two-stage gimbal around the
   carrier: rotational stiffness per cross-strip pivot ~ 8 E I / L (two blades
   crossing at mid-length, I = w t^3/12); blade stress ~ E t psi / L (S-bend,
   factor 2 on the pure-bending value); Euler buckling of a blade in
   compression P_cr = 4 pi^2 E I_min / L^2.
3) Axial suspension: two planar spiral-arm diaphragms carrying the gimbal
   (k_ax target ~2 kN/m, DEC-006), guided-cantilever arm model.
Run: python3 mechanics/flexure_calc.py
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import provenance  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "mechanics")
BECU = {"E": 131e9, "fatigue": 310e6, "yield": 1241e6, "allow_alt": 150e6, "allow_peak": 310e6, "rho": 8360}
L1 = 12e-3
TIP_MECH = 0.65e-3
TIP_TYP = 0.30e-3       # typical correction amplitude (tremor band), fatigue case
AXIAL_MAX = 2.0         # N axial writing load (bench envelope)


def wire_pivot(d, l, r_c, n=3, mat=BECU, cone_deg=45.0):
    I = math.pi * d ** 4 / 64
    E = mat["E"]
    k_w = E * I * (12 * r_c ** 2 + 12 * l * r_c + 4 * l ** 2) / l ** 3
    k_lo, k_hi = 1.5 * k_w, 3.0 * k_w           # in-plane only .. isotropic in+out of plane
    psi_m, psi_t = math.asin(TIP_MECH / L1), math.asin(TIP_TYP / L1)
    sig = lambda psi: E * psi * (d / 2) * (6 * r_c + 4 * l) / l ** 2
    P_cr = 4 * math.pi ** 2 * E * I / l ** 2
    P_wire = AXIAL_MAX / n / math.cos(math.radians(cone_deg))
    return {"type": "3-wire conical pivot", "d_mm": d * 1e3, "l_mm": l * 1e3, "r_c_mm": r_c * 1e3,
            "k_tip_N_per_m_range": [k_lo / L1 ** 2, k_hi / L1 ** 2],
            "stress_full_travel_MPa": sig(psi_m) / 1e6, "stress_typical_MPa": sig(psi_t) / 1e6,
            "buckling_load_per_wire_N": P_cr, "axial_load_per_wire_N": P_wire,
            "buckling_margin": P_cr / P_wire,
            "passes": sig(psi_m) <= mat["allow_peak"] and sig(psi_t) <= mat["allow_alt"] and P_cr / P_wire >= 3}


def cross_strip_gimbal(t, w, L, mat=BECU, pivots_per_axis=2, blades_per_pivot=2):
    E = mat["E"]
    I = w * t ** 3 / 12
    k_piv = 8 * E * I / L
    k_axis = pivots_per_axis * k_piv
    psi_m, psi_t = math.asin(TIP_MECH / L1), math.asin(TIP_TYP / L1)
    sig = lambda psi: E * t * psi / L                 # S-bend factor 2 on E t psi / (2L)
    I_min = I
    P_cr = 4 * math.pi ** 2 * E * I_min / L ** 2
    n_blades_stage = pivots_per_axis * blades_per_pivot
    P_blade = AXIAL_MAX / n_blades_stage / math.cos(math.radians(45.0))
    mass = mat["rho"] * t * w * L * n_blades_stage * 2
    return {"type": "two-stage cross-strip gimbal", "t_mm": t * 1e3, "w_mm": w * 1e3, "L_mm": L * 1e3,
            "k_tip_N_per_m_per_axis": k_axis / L1 ** 2,
            "stress_full_travel_MPa": sig(psi_m) / 1e6, "stress_typical_MPa": sig(psi_t) / 1e6,
            "buckling_load_per_blade_N": P_cr, "axial_load_per_blade_N": P_blade, "buckling_margin": P_cr / P_blade,
            "centre_shift_note": "cross-strip pivot centre drift ~ L psi^2/8 ~ sub-micrometre here",
            "blade_mass_mg": mass * 1e6,
            "passes": sig(psi_m) <= mat["allow_peak"] and sig(psi_t) <= mat["allow_alt"] and P_cr / P_blade >= 3}


def spiral_diaphragm(t, b, L_arm, n_arms=3, n_diaphragms=2, mat=BECU, s_max=1.0e-3):
    """Planar diaphragm with n arms modelled as guided cantilevers (axial)."""
    E = mat["E"]
    I = b * t ** 3 / 12
    k_arm = 12 * E * I / L_arm ** 3
    k_ax = k_arm * n_arms * n_diaphragms
    sig = 3 * E * t * s_max / L_arm ** 2                # guided cantilever peak stress at deflection s
    radial_k = n_arms * E * b * t / L_arm             # in-plane (tension/compression of arms, upper bound)
    return {"type": "spiral-arm diaphragm pair", "t_mm": t * 1e3, "b_mm": b * 1e3, "L_arm_mm": L_arm * 1e3,
            "k_axial_N_per_m": k_ax, "stress_at_stop_MPa": sig / 1e6, "radial_k_upper_N_per_m": radial_k,
            "passes": sig <= mat["allow_peak"]}


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {"material": BECU, "L1_m": L1}
    res["wire_candidates"] = [wire_pivot(0.25e-3, 5.37e-3, 2.4e-3), wire_pivot(0.10e-3, 8.0e-3, 1.8e-3),
                              wire_pivot(0.15e-3, 10.0e-3, 1.8e-3)]
    res["gimbal_candidates"] = [cross_strip_gimbal(0.05e-3, 1.0e-3, 2.0e-3), cross_strip_gimbal(0.04e-3, 1.2e-3, 2.5e-3),
                                cross_strip_gimbal(0.075e-3, 0.8e-3, 2.5e-3)]
    # axial suspension: target ~2 kN/m with diaphragm arms in the 14 mm bore around the gimbal
    # short straight arms (fail) versus long spiral arms (~270 deg spiral in a 12 mm disc, ~15 mm arm length)
    res["suspension_candidates"] = [spiral_diaphragm(0.10e-3, 0.8e-3, 6.0e-3), spiral_diaphragm(0.12e-3, 0.8e-3, 7.0e-3),
                                    spiral_diaphragm(0.22e-3, 0.8e-3, 15.0e-3, s_max=0.6e-3),
                                    spiral_diaphragm(0.20e-3, 1.0e-3, 16.0e-3, s_max=0.6e-3)]
    meta = provenance.metadata("analytical calculation (beam theory; nominal geometry)")
    provenance.write_json(os.path.join(OUT, "flexure_calc.json"), {"meta": meta, "results": res})
    for grp in ("wire_candidates", "gimbal_candidates", "suspension_candidates"):
        print(grp)
        for c in res[grp]:
            print("  ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if k != "centre_shift_note"})


if __name__ == "__main__":
    main()
