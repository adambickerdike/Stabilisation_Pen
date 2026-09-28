"""Reference values of the current design from the existing (numpy) code, for the agreement checks of the
differentiable model: sim/pencil/design.py (stage, loads, Weibull), analysis/pencil_mechanisms.py (stage-check
stress formulas), and the CAD outputs of mechanics/cad/pencil_revP.py (results/cad/pencil_revP{Q,L}_summary.json).
Evidence status: CALCULATION / CAD (proposed design)."""
from __future__ import annotations

import json
import math
import os

from . import ROOT
from sim.pencil import design as D  # noqa: E402

D2R = math.pi / 180.0


def stage_reference(key="Q26", V_rail=60.0):
    st = D.stage(key, V_rail=V_rail)
    st_tol = D.stage(key, V_rail=V_rail, tol=-0.2)
    P = D.Params()
    Fc, mu = P["nib.spring_force"], P["nib.mu_nib"]
    F_nom = D.load_extremes("skid", Fc, 50 * D2R, mu)["R_perp_max"]
    F_35 = D.load_extremes("skid", Fc, 35 * D2R, mu)["R_perp_max"]
    F_35_mu35 = D.load_extremes("skid", Fc, 35 * D2R, 0.35)["R_perp_max"]
    b = st.bender
    stop_col = st.nib["nib_stop"] / st.n
    return {
        "F_nom": F_nom, "F_35": F_35, "F_35_mu035": F_35_mu35,
        "F_b_nib": st.F_b_nib, "k_b_nib": st.k_b_nib, "k_par_nib": st.k_par_nib, "m_eq_nib": st.m_eq_nib,
        "m_couple_nib": st.m_couple_nib, "f1": st.f1, "n": st.n, "C_axis": st.C_axis, "g_V": st.g_V,
        "stroke_nom": st.stroke_under_load(F_nom), "stroke_35": st.stroke_under_load(F_35),
        "stroke_tol_nom": st_tol.stroke_under_load(F_nom),
        "stroke_tol_35_raw": (st_tol.F_b_nib - F_35) / (st_tol.k_b_nib + st_tol.k_par_nib),
        "F_b_nib_tol": st_tol.F_b_nib,
        "sig_stop_driven": b.clamp_stress(b.k * (stop_col + b.delta_f)),
        "sig_stop_unpowered": b.clamp_stress(b.k * stop_col),
        "sigma0": D.sigma0_bender(b),
        "leaf_k_cross": D.RECOMMENDED_LEAF.k_cross, "leaf_k_drive": D.RECOMMENDED_LEAF.k_drive,
        "leaf_sf": D.RECOMMENDED_LEAF.sf_buckling(b.F_b),
        "leaf_stress_stop": D.RECOMMENDED_LEAF.stress_cross(stop_col),
    }


def cad_reference(variant="Q"):
    d = json.load(open(os.path.join(ROOT, "results", "cad", f"pencil_revP{variant}_summary.json")))
    s = d["summary"]
    sc = s["section_checks"]
    webs = [min(r["web_inner_mm"], r["web_outer_mm"]) for r in s["snubbers"]]
    return {"plate_to_bore": sc["plate_to_bore_mm"], "plate_to_plate": sc["plate_to_plate_mm"],
            "plate_to_refill": sc["plate_to_refill_mm"], "hall_outer_to_nose_wall": sc["hall_outer_to_nose_wall_mm"],
            "collar_to_nose_wall": sc["collar_to_nose_wall_mm"],
            "refill_cone_to_skid_aperture": sc["refill_cone_to_skid_aperture_at_theta_min_mm"],
            "optical_sensor_to_refill": sc["optical_sensor_to_refill_mm"], "snubber_min_web": min(webs),
            "snubber_gaps": [r["gap_mm"] for r in s["snubbers"]], "mass_total_g": s["mass_total_g"],
            "parameters_mm": s["parameters_mm"]}


def cad_exact_gaps(variant="Q"):
    """The CAD fit formulas evaluated without the 3-decimal rounding of the summary (same formulas as
    mechanics/cad/pencil_revP.section_checks and snubbers, on the summary's parameters)."""
    P = cad_reference(variant)["parameters_mm"]
    rb, t, w, d, sw = P["r_bore"], P["plate_t"], P["plate_w"], P["plate_d"], P["tip_sweep"]
    out = {}
    if P["n_plates"] == 4:
        out["plate_to_bore"] = rb - math.hypot(d + t / 2 + sw, w / 2)
        out["plate_to_plate"] = d - t / 2 - sw - w / 2
    else:
        out["plate_to_bore"] = rb - math.hypot(d + t / 2 + sw, max(1.2, w - 1.2))
        out["plate_to_plate"] = d - t / 2 - sw - 1.2
    zt = P["z_plate_tip"]
    u_ref = P["nib_travel"] / P["lever"] * (P["z_gimbal"] - zt) / (P["z_gimbal"] - (P["collar_z0"] + P["collar_L"] / 2))
    out["plate_to_refill"] = d - t / 2 - (sw - u_ref) - P["refill_d"] / 2

    def nose_inner_r(z):
        zs = P["z_skid"] + P["skid_w"]
        r0, r1, z1 = P["skid_r"] - 0.05, P["r_bore"], zs + P["nose_L"] - 0.5
        return r0 + (r1 - r0) * min(max((z - zs) / (z1 - zs), 0.0), 1.0)

    zc = P["collar_z0"] + P["collar_L"] / 2
    x_face = P["collar_od"] / 2 + 0.3 + P["nib_travel"] / P["lever"] + 0.15
    out["hall_outer_to_nose_wall"] = nose_inner_r(zc) - (x_face + 0.6)
    out["collar_to_nose_wall"] = nose_inner_r(P["collar_z0"]) - (P["collar_od"] / 2 + P["nib_travel"] / P["lever"])
    p_max = P["skid_r"] / math.tan(math.radians(P["theta_min"]))
    r_cone = P["socket_d"] / 2 + (P["refill_d"] / 2 - P["socket_d"] / 2) * min(max((p_max - 0.3) / (P["cone_L"] - 0.3), 0), 1)
    out["refill_cone_to_skid_aperture"] = (P["skid_r"] - 0.15) - (r_cone + P["nib_travel"])
    out["optical_sensor_to_refill"] = nose_inner_r(P["collar_z0"] - 2.0) - 0.7 - (P["refill_d"] / 2 + P["nib_travel"])
    webs, gaps = [], []
    tip_stop = P["nib_travel"] / P["lever"]
    for sfr in P["snub_stations"]:
        z = P["z_plate_tip"] + sfr * P["plate_free"]
        xi = (P["z_clamp0"] - z) / P["plate_free"]
        gap = tip_stop * (3 * xi ** 2 - xi ** 3) / 2 + P["snub_gap_extra"]
        sweep = P["nib_travel"] * (P["z_gimbal"] - z) / P["z_gimbal"]
        r_hole = P["refill_d"] / 2 + sweep + 0.10
        inner, outer = d - t / 2 - gap, d + t / 2 + gap
        webs.append(min(inner - r_hole, (rb - 0.05) - outer))
        gaps.append(gap)
    out["snubber_min_web"] = min(webs)
    out["snubber_gaps"] = gaps
    return out
