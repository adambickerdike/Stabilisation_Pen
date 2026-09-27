#!/usr/bin/env python3
"""Tolerance and clearance stack-ups for the Rev A mechanism.

Evidence status: CALCULATION on the nominal CAD geometry
(mechanics/cad/pen_revA.py, results/cad/pen_revA_summary.json) with assumed
manufacturing tolerances (engineering judgement for precision-machined and
bonded parts; every tolerance is listed with its basis).  Worst case and RSS
(tolerances taken as +/-3 sigma) plus a 200 000-sample Monte Carlo.

Stacks
  S1  actuator axial gap, front and rear faces of the coil paddle, including
      lever tilt at full travel and the axial slide s of whatever carries the
      paddle: suspension behind the pivot (kappa_s = 0, whole lever slides)
      vs refill sliding in the carrier (kappa_s = 1, paddle does not slide)
  S2  radial clearance of the carrier through the magnet bore at full swing
  S3  ball/cone clearance in the tip aperture at full travel
  S4  lever-ratio (gain) error from pivot and actuator positions
  S5  Hall sense-magnet gap: refill length tolerance moves the magnet
Design options for S1: nominal (gap 0.45 mm, travel 0.65 mm) and the proposed
Rev A.1 values (gap 0.50 mm, travel 0.60 mm).
Outputs: results/mechanics/tolerance.json, fig_gap_budget.png.
Run: python3 mechanics/tolerance_analysis.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stabpen import plotstyle, provenance  # noqa: E402

CAD = json.load(open(os.path.join(ROOT, "results", "cad", "pen_revA_summary.json")))["summary"]
PM = CAD["parameters_mm"]
DER = CAD["derived_mm"]

# (name, +/- tolerance mm (3 sigma), sensitivity to the clearance, basis)
S1_TOL = [
    ("magnet thickness", 0.05, 1.0, "sintered NdFeB ground, +/-0.05"),
    ("magnet bond line", 0.02, 1.0, "controlled adhesive gap"),
    ("stator axial position in barrel", 0.05, 1.0, "bore shoulder + press fit"),
    ("iron/magnet stack", 0.03, 1.0, "ground back iron"),
    ("coil paddle half-thickness", 0.025, 1.0, "coil thickness +/-0.05"),
    ("paddle perpendicularity 0.3 deg at r_p", None, 1.0, "r_p sin(0.3 deg)"),
    ("paddle axial position on carrier", 0.05, 1.0, "bonded on a shoulder"),
    ("pivot (gimbal) axial position", 0.05, 1.0, "gimbal clamp datum"),
    ("differential expansion Al/Ti over 38 mm, 20 K", 0.011, 1.0, "(23.6-8.6) ppm/K"),
]


def s1_tolerances(r_p):
    out = []
    for name, tol, sens, basis in S1_TOL:
        if tol is None:
            tol = r_p * math.sin(math.radians(0.3))
        out.append((name, tol, sens, basis))
    return out


def s1(gap, travel, kappa_s, s_design, s_stop, r_p, z_act, L1, rng):
    psi = math.asin(travel / L1)
    edge = r_p * math.sin(psi)                    # axial excursion of the paddle rim from tilt
    arc = (z_act - L1) * (1 - math.cos(psi))      # whole paddle moves toward the pivot
    front_use = edge + arc                        # rim nearest the front magnet
    rear_use = edge - arc
    s_d = s_design if kappa_s == 0 else 0.0
    s_x = s_stop if kappa_s == 0 else 0.0
    tols = s1_tolerances(r_p)
    wc = sum(t for _, t, _, _ in tols)
    rss = math.sqrt(sum(t ** 2 for _, t, _, _ in tols))
    # Monte Carlo: each tolerance ~ N(0, (t/3)^2); clearance = gap - use - sum(dev)
    dev = sum(rng.normal(0, t / 3, 200_000) for _, t, _, _ in tols)
    res = {}
    for side, use in (("front", front_use), ("rear_design_load", rear_use + s_d), ("rear_at_axial_stop", rear_use + s_x)):
        nom = gap - use
        mc = nom - dev
        res[side] = {"nominal_clearance_mm": nom, "worst_case_mm": nom - wc, "rss_mm": nom - rss,
                     "p_contact": float(np.mean(mc <= 0.0)), "p_below_0p05": float(np.mean(mc <= 0.05))}
    return {"gap_mm": gap, "tip_travel_mm": travel, "kappa_s": kappa_s, "psi_deg": math.degrees(psi),
            "tilt_edge_mm": edge, "arc_mm": arc, "tol_worst_mm": wc, "tol_rss_mm": rss, "sides": res}


def s2(travel, rng):
    # carrier OD through magnet bore at z_act: radial clearance at full swing
    swing = travel * (PM["z_act"] - PM["L1"]) / PM["L1"]
    ri = min(DER["act_ri_front"], DER["act_ri_rear"])
    nom = ri - PM["carrier_od"] / 2 - swing
    tols = [("magnet ID", 0.05), ("carrier OD", 0.02), ("stator concentricity to pivot axis (TIR 0.10)", 0.05),
            ("pivot lateral position scaled to z_act", 0.03 * (PM["z_act"] - PM["L1"]) / PM["L1"])]
    wc = sum(t for _, t in tols)
    rss = math.sqrt(sum(t ** 2 for _, t in tols))
    return {"swing_mm": swing, "nominal_clearance_mm": nom, "worst_case_mm": nom - wc, "rss_mm": nom - rss, "tolerances": tols}


def s3(travel):
    # ball / cone at the aperture plane (aperture radius vs ball radius + travel)
    r_ap = PM["tip_aperture"] / 2
    r_obj = PM["ball_d"] / 2 + 0.1 + (PM["refill_d"] / 2 - PM["ball_d"] / 2 - 0.1) * (1.0 / PM["cone_L"])   # cone radius 1 mm behind ball
    nom = r_ap - r_obj - travel
    tols = [("aperture diameter/2", 0.02), ("refill cone OD/2 (ISO 12757 class, VERIFY)", 0.05), ("nose concentricity", 0.05),
            ("pivot lateral position", 0.03)]
    wc = sum(t for _, t in tols)
    rss = math.sqrt(sum(t ** 2 for _, t in tols))
    return {"nominal_clearance_mm": nom, "worst_case_mm": nom - wc, "rss_mm": nom - rss, "tolerances": tols}


def s6(theta_deg, s_nose, r_nose, q_max, r_ball=0.35, margin=0.3):
    """Nose-to-paper clearance.  A point of the nose at axial distance s behind the
    ball centre and radius r (on the paper side of the tilt plane) sits
    s sin(theta) - r cos(theta) + r_ball above the paper; a stage displacement of
    the ball by -q along t1 lowers the housing by q cos(theta)."""
    th = math.radians(theta_deg)
    h = s_nose * math.sin(th) - r_nose * math.cos(th) + r_ball
    h_worst = h - q_max * math.cos(th)
    s_needed = (r_nose * math.cos(th) - r_ball + margin + q_max * math.cos(th)) / math.sin(th)
    return {"theta_deg": theta_deg, "clearance_nominal_mm": h, "clearance_worst_mm": h_worst, "s_needed_mm": s_needed}


def s4():
    L1, L2 = PM["L1"], PM["z_act"] - PM["L1"]
    tL1, tL2 = 0.10, 0.10
    n = L2 / L1
    dn = math.sqrt((tL2 / L1) ** 2 + (L2 * tL1 / L1 ** 2) ** 2)
    return {"n": n, "n_tol_rss": dn, "gain_error_pct_rss": 100 * dn / n,
            "note": "static gain error calibrated with the Hall/optical map (EXP-B04); residual after calibration < 0.5 %"}


def s5():
    # dipole field on axis ~ 1/(d)^3 with d = gap + half magnet length
    gap = PM["hall_gap"]; t = PM["sense_mag_t"]
    d0 = gap + t / 2
    tol_len = 0.30      # refill length tolerance (ISO 12757-2 class, VERIFY) plus seat 0.05
    rows = []
    for dl in (-tol_len, 0.0, tol_len):
        d = d0 + dl
        rows.append({"refill_length_dev_mm": dl, "rel_field": (d0 / d) ** 3})
    return {"nominal_distance_mm": d0, "field_variation": rows,
            "consequence": "Bz offset changes by up to ~+/-40 % between refills: the axial-force channel must be re-zeroed at each refill insertion (pen-up, s = 0) and its gain re-checked against a known force (dock)"}


def main():
    rng = np.random.default_rng(12)
    r_p = DER["paddle_ro"]
    s_design = (1.0 * (math.sin(math.radians(50)) + 0.15 * math.cos(math.radians(50))) - 0.25) / 2000.0 * 1e3   # mm
    s_stop = 0.6
    cases = {}
    for label, gap, travel in (("RevA_nominal", PM["act_gap"], PM["tip_travel_mech"]), ("RevA1_proposed", 0.50, 0.60)):
        for kap in (0, 1):
            cases[f"{label}_kappa{kap}"] = s1(gap, travel, kap, s_design, s_stop, r_p, PM["z_act"], PM["L1"], rng)
    out = {"S1_actuator_gap": cases, "S1_tolerances": [(n, t, b) for n, t, _, b in s1_tolerances(r_p)],
           "S1_axial_slide_design_mm": s_design, "S1_axial_slide_stop_mm": s_stop,
           "S2_carrier_bore": {k: s2(tr, rng) for k, tr in (("travel_0.65", 0.65), ("travel_0.60", 0.60))},
           "S3_tip_aperture": {k: s3(tr) for k, tr in (("travel_0.65", 0.65), ("travel_0.60", 0.60))},
           "S4_lever_gain": s4(), "S5_hall_gap": s5(),
           "S6_nose_paper_clearance": {
               "RevA_nose_s1_r3": [s6(th, 1.0, 3.0, 0.65) for th in (35.0, 50.0, 75.0)],
               "RevA1_nose_s5_r2.6": [s6(th, 5.0, 2.6, 0.60) for th in (35.0, 50.0, 75.0)],
               "note": "Rev A nose (6 mm OD tip 1 mm behind the ball) touches the paper at all writing altitudes; Rev A.1 moves the nose tip to 5 mm (OD 5.2, aperture 4.2) so the refill point protrudes like an ordinary ballpoint"},
           "magnetic_gap_penalty": {"note": "air-gap field B ~ Br t_m/(t_m + g_total) for the sandwich; gap 0.45 -> 0.50 per side raises g_total 1.9 -> 2.0 mm",
                                    "B_ratio": (1.5 / (1.5 + 2.0)) / (1.5 / (1.5 + 1.9)), "power_ratio": ((1.5 + 2.0) / (1.5 + 1.9)) ** 2}}
    meta = provenance.metadata("calculation (nominal CAD + assumed tolerances)")
    provenance.write_json(os.path.join(ROOT, "results", "mechanics", "tolerance.json"), {"meta": meta, **out})
    for k, c in cases.items():
        print(k, {s: {kk: round(vv, 3) for kk, vv in v.items()} for s, v in c["sides"].items()})
    for k in ("S2_carrier_bore", "S3_tip_aperture"):
        print(k, {kk: {x: (round(y, 3) if isinstance(y, float) else y) for x, y in vv.items() if x != "tolerances"} for kk, vv in out[k].items()})
    print("S4", out["S4_lever_gain"]); print("S5", out["S5_hall_gap"]["field_variation"]); print("gap penalty", out["magnetic_gap_penalty"])
    for k, v in out["S6_nose_paper_clearance"].items():
        if k != "note":
            print("S6", k, [(r["theta_deg"], round(r["clearance_worst_mm"], 2), round(r["s_needed_mm"], 2)) for r in v])
    # figure: S1 clearance (RSS) per side and case
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels, vals, cols = [], [], []
    for j, (k, c) in enumerate(cases.items()):
        for side, v in c["sides"].items():
            labels.append(f"{k.replace('_kappa', ' k=')}\n{side.replace('_', ' ')}")
            vals.append(v["rss_mm"] * 1e3)
            cols.append(plotstyle.SERIES[j])
    y = np.arange(len(vals))
    ax.barh(y, vals, color=cols, height=0.62, edgecolor=plotstyle.SURFACE)
    ax.axvline(0, color=plotstyle.INK2, lw=1.0)
    ax.axvline(50, color=plotstyle.MUTED, lw=1.0, ls="--")
    ax.set_yticks(y, labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("Paddle-to-magnet clearance after RSS tolerances (um); dashed: 50 um margin")
    ax.set_title("Actuator gap budget: only kappa_s = 1 with gap 0.50 / travel 0.60 keeps margin everywhere", loc="left", fontsize=10)
    plotstyle.stamp(fig, "calculation", "nominal CAD + assumed 3-sigma tolerances; not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "results", "mechanics", "fig_gap_budget.png"))


if __name__ == "__main__":
    main()
