#!/usr/bin/env python3
"""Mechanism configuration trade study under ONE common requirement set.

Requirement set (docs/requirements.csv): page correction disc radius 0.5 mm
over altitude 35-75 deg; design contact point N = 1.0 N, mu = 0.15, theta =
50 deg; high point N = 1.5 N, mu = 0.20, theta = 40 deg; bench corner
N = 2.0 N, mu = 0.35, theta = 35 deg; tremor correction amplitude 0.3 mm at
8 Hz.  All loads come from stabpen.contact (transverse reaction incl. the
normal component, COR-01).

Configurations
  A  direct-drive translational carriage near the tip (report baseline)
  B  front-pivot lever n = 3.17 + rear annular actuator (research baseline)
  B-MM  as B with moving magnets / fixed bonded coils (thermal variant)
  C  amplified piezo stacks (APA50XS class) with ~15:1 amplification lever
  D  B + skid-referenced nib: user force carried by a nose skid; nib contact
     force set by a constant-force spring F_c
  E  B + slow zero-hold-power bias actuator (SQUIGGLE-class) carrying the
     quasi-static load; voice coil carries only the dynamic part
  F  external electromagnetic surface (no onboard actuator; special surface)
Every number is an ANALYTICAL CALCULATION from stated assumptions and ledger
datasheet values; no configuration has been built or measured.
Outputs results/trade/config_trade.json and .csv.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import contact, provenance  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "trade")
D2R = math.pi / 180
POINTS = {"design": (1.0, 0.15, 50.0), "high": (1.5, 0.20, 40.0), "bench_corner": (2.0, 0.35, 35.0)}
P_ELEC = 0.06            # W electronics (budget, docs/budgets.md)
DUTY_DOWN = 0.65         # pen-down fraction while writing (assumption, measure EXP-H02)
CELL = {"name": "Grepow GRP5811047 narrow LiPo (AMF-33)", "mAh": 200, "V": 3.7, "usable": 0.8, "Imax_A": 4.0}
CELL_10440 = {"name": "EEMB LIR10440 (AMF-31)", "mAh": 320, "V": 3.7, "usable": 0.8, "Imax_A": 0.32}
T_LIMIT_SURFACE = 43.0   # C continuously held (AMF-35 ECMA-287); regulatory review required
T_AMB = 25.0


def load(point, Fc=None):
    N, mu, th = POINTS[point]
    th_r = th * D2R
    if Fc is not None:
        # skid: nib normal force set by constant axial spring Fc: N_nib = Fc / sin(th) (friction neglected)
        N = min(N, Fc / math.sin(th_r))
    b = contact.transverse_load_bounds(N, mu, th_r)
    return float(b["rms"]), float(b["max"]), N


def dyn_force_tip(m_eq, amp=0.3e-3, f=8.0, k=150.0, c_fric=0.0):
    w = 2 * math.pi * f
    return math.hypot(m_eq * w * w * amp - k * amp, c_fric)


def lorentz(name, Km_axis, n, m_eq, Rth_coil, note, Fc=None, bias_fraction=0.0, stroke_ok=True, fits=True):
    rows = {}
    for pt in POINTS:
        F_rms, F_max, N_eff = load(pt, Fc)
        F_static = F_rms * (1 - bias_fraction)
        F_dyn = dyn_force_tip(m_eq)
        Km_tip = n * Km_axis
        P_hold = (F_static / Km_tip) ** 2
        P_dyn = (F_dyn / Km_tip) ** 2 / 2          # sinusoidal RMS
        P = P_hold + P_dyn
        rows[pt] = {"F_perp_rms_N": F_rms, "F_perp_max_N": F_max, "N_nib_N": N_eff, "Km_tip": Km_tip,
                    "P_copper_contact_W": P, "coil_rise_K": P * Rth_coil,
                    "I_axis_A_at_F_max": F_max * (1 - bias_fraction) / (n * Km_axis * math.sqrt(11.0))}
    d = rows["design"]
    P_avg = d["P_copper_contact_W"] * DUTY_DOWN + P_ELEC
    return {"config": name, "fits_envelope": fits, "stroke_feasible": stroke_ok, "Km_axis": Km_axis, "n": n,
            "m_eq_g": m_eq * 1e3, "Rth_coil_K_per_W": Rth_coil, "points": rows,
            "avg_power_writing_W": P_avg,
            "runtime_min_grepow200": CELL["mAh"] * 1e-3 * CELL["V"] * CELL["usable"] / P_avg * 60,
            "runtime_min_10440": CELL_10440["mAh"] * 1e-3 * CELL_10440["V"] * CELL_10440["usable"] / P_avg * 60,
            "note": note}


def main():
    os.makedirs(OUT, exist_ok=True)
    cfgs = []
    cfgs.append(lorentz("A direct-drive carriage near tip", 0.19, 1.0, 2.5e-3, 60.0,
                        "Km from magpylib frontDD module (results/em/em_actuator.json); annulus around refill limits copper and magnet volume",
                        fits=True))
    cfgs.append(lorentz("B lever n=3.17, moving-coil annular sandwich (Rev A)", 0.30, 3.17, 10.3e-3, 130.0,
                        "Km bracket 0.24-0.34 (em_actuator flat sandwich proxy); moving coil in 0.45 mm air gaps: poor heat path (~130 K/W)"))
    cfgs.append(lorentz("B-MM lever n=3.17, moving magnet, fixed bonded coils", 0.20, 3.17, 19.0e-3, 25.0,
                        "Coils outside a single moving magnet give lower Km (em_planar 0.13-0.15 thin disc; 0.20 assumed with iron); magnet adds ~1.2 g at L2 (x n^2)"))
    cfgs.append(lorentz("D skid + constant-force nib (Fc = 0.30 N) on B actuator", 0.30, 3.17, 10.3e-3, 130.0,
                        "User force carried by nose skid; nib load bounded; changes writing feel (EXP-H03)", Fc=0.30))
    cfgs.append(lorentz("E B + slow zero-hold bias actuator (80% of static load)", 0.30, 3.17, 10.3e-3, 130.0,
                        "SQUIGGLE-class bias (AMF-15: 0.3 N stall, 0 mW hold) through a spring; bias bandwidth ~1-2 Hz", bias_fraction=0.8))
    # C: amplified piezo (APA50XS: 66 um nominal stroke, 16 N blocked, -20..150 V, 0.30 uF, 2.0 g each; AMF-14)
    stroke_um, Fb = 66.0, 16.0
    tip_travel_um = 2 * 550.0                    # peak-to-peak commanded page travel (stage coordinates)
    n_amp = tip_travel_um / stroke_um            # required amplification
    Fb_tip = 2 * Fb / n_amp                      # two APAs per axis push-pull
    F_des = load("design")[0]
    F_high = load("high")[1]
    piezo = {"config": "C amplified piezo, 2 x APA50XS per axis", "n_amplification": n_amp, "blocked_force_tip_N": Fb_tip,
             "force_at_half_stroke_tip_N": Fb_tip * 0.5, "design_load_N": F_des, "high_load_max_N": F_high,
             "stroke_feasible": Fb_tip * 0.5 >= F_high, "hold_power_W": 0.0,
             "drive": "DRV2700 boost, -20..150 V (AMF-16)",
             "dynamic_power_W_est": 4 * 0.30e-6 * 150 ** 2 * 8.0 * 0.5,
             "mass_g_actuators_only": 4 * 2.0, "fits_envelope": False,
             "note": "Each APA50XS is 13 x 9 x 5 mm; four plus a ~17:1 compliant amplifier do not fit the front 60 mm of a 14.6 mm bore "
                     "without a bulge; amplifier compliance and drop fragility are major risks"}
    cfgs.append(piezo)
    cfgs.append({"config": "F external electromagnetic surface (Langerak-class)", "fits_envelope": True, "stroke_feasible": True,
                 "note": "No onboard actuator; requires special tablet-sized surface under paper (HAP-16); product alternative only"})
    rows = []
    for c in cfgs:
        r = {"config": c["config"], "fits": c.get("fits_envelope"), "stroke_ok": c.get("stroke_feasible")}
        if "points" in c:
            for pt in POINTS:
                r[f"P_{pt}_W"] = round(c["points"][pt]["P_copper_contact_W"], 3)
                r[f"coil_rise_{pt}_K"] = round(c["points"][pt]["coil_rise_K"], 1)
            r["avg_power_W"] = round(c["avg_power_writing_W"], 3)
            r["runtime_min_200mAh"] = round(c["runtime_min_grepow200"])
        rows.append(r)
    with open(os.path.join(OUT, "config_trade.csv"), "w", newline="") as f:
        keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "config", k))
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    meta = provenance.metadata("analytical calculation (datasheet and magpylib inputs; nothing built)",
                               extra={"points": POINTS, "P_elec_W": P_ELEC, "duty_down": DUTY_DOWN, "cell": CELL})
    provenance.write_json(os.path.join(OUT, "config_trade.json"), {"meta": meta, "configs": cfgs})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
