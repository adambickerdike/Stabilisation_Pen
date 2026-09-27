#!/usr/bin/env python3
"""Independent recalculation of the source report's worked examples, plus the
corrected analyses that replace them.

Evidence status of every number produced here: ANALYTICAL CALCULATION.
Nothing here is a measurement.

Outputs
  results/audit/audit_checks.csv      one row per reproduced report number
  results/audit/audit_corrections.json corrected analyses (machine readable)
  results/audit/fig_*.png             figures (each stamped with evidence status)
  results/audit/metadata.json         provenance
Run:  python3 analysis/audit_recalc.py
"""
from __future__ import annotations

import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import actuator, contact, frames, params, plotstyle, provenance  # noqa: E402

OUT = os.path.join(params.REPO_ROOT, "results", "audit")
os.makedirs(OUT, exist_ok=True)
plotstyle.apply()
import matplotlib.pyplot as plt  # noqa: E402

D2R = math.pi / 180.0
checks = []


def check(cid, section, quantity, report_value, recomputed, unit, tol_rel=0.03, note=""):
    ok = abs(recomputed - report_value) <= tol_rel * max(abs(report_value), 1e-12)
    checks.append({"id": cid, "report_section": section, "quantity": quantity,
                   "report_value": report_value, "recomputed_same_assumptions": round(float(recomputed), 6),
                   "unit": unit, "arithmetic_reproduced": "yes" if ok else "NO", "note": note})


# --------------------------------------------------------------------------
# S8 tilt kinematics
th35 = 35 * D2R
check("A-01", "s8", "axial accommodation for 0.5 mm TRANSVERSE motion at 35 deg", 0.71,
      0.5 / math.tan(th35), "mm",
      note="Correct for 0.5 mm transverse; but REQ is +/-0.5 mm per PAGE axis -> 0.5*cos35 = 0.41 mm (see COR-03).")
check("A-02", "s8/Fig3", "page/transverse gain 1/sin(theta) at 35 deg", 1.74, 1 / math.sin(th35), "-",
      note="Figure 3 curve reproduced (1/sin theta).")
J_num = frames.jacobian_numeric(th35, 0.3, 0.7)
J_ana = frames.jacobian(th35, 0.3, 0.7)
assert np.allclose(J_num, J_ana), "Jacobian derivation mismatch"

# S9 force and dynamic calculations (report assumptions)
m, A, f, k, N_rep, mu_rep = 1e-3, 0.5e-3, 8.0, 50.0, 0.75, 0.2
w = 2 * math.pi * f
check("A-03", "s9", "peak velocity", 25.1, w * A * 1e3, "mm/s")
check("A-04", "s9", "peak acceleration", 1.26, w * w * A, "m/s^2")
check("A-05", "s9", "inertial force", 1.26, m * w * w * A * 1e3, "mN")
check("A-06", "s9", "spring force at 0.5 mm", 25.0, k * A * 1e3, "mN")
check("A-07", "s9", "illustrative lateral drag", 150.0, mu_rep * N_rep * 1e3, "mN",
      note="Arithmetic correct; the physics omits N*cos(theta) (COR-01).")
check("A-08", "s9", "sum of force magnitudes", 176.0, (m * w * w * A + k * A + mu_rep * N_rep) * 1e3, "mN",
      tol_rel=0.01)
check("A-09", "s9", "undamped stage mode", 35.6, math.sqrt(k / m) / (2 * math.pi), "Hz",
      note="1 g moving mass is optimistic; see COR-06 (refill+carrier+actuator part >= 1.5-3 g translational; lever tip-equivalent ~5-20 g).")

# S10 IMU bias drift
check("A-10", "s10", "position error after 1 s from 1 mg bias", 4.9, 0.5 * 1e-3 * 9.80665 * 1.0 ** 2 * 1e3, "mm")
# S11 relocalisation illustrations
check("A-11", "s11", "0.5% scale error over 100 mm", 0.5, 0.005 * 100, "mm")
check("A-12", "s11", "1 deg heading error over 100 mm (transverse)", 1.75, 100 * math.sin(1 * D2R), "mm")
check("A-13", "s11", "DeltaPen 6000 dpi increment", 4.2, 25.4e3 / 6000, "um")
# S13 delay residual EA = 2|sin(pi f tau)|
for cid, tau, rv in (("A-14", 5e-3, 0.25), ("A-15", 10e-3, 0.50), ("A-16", 20e-3, 0.96)):
    check(cid, "s13/Fig4", f"residual/original at 8 Hz, {tau*1e3:.0f} ms", rv, 2 * abs(math.sin(math.pi * 8 * tau)), "-")
# S14 enlargement
check("A-17", "s14", "offset for 1.5x enlargement of 5 mm", 2.5, (1.5 - 1) * 5.0, "mm")
# S22 energy
E = 0.8 * 3.7 * 0.120
check("A-18", "s22", "usable energy", 0.355, E, "Wh")
for cid, I, P_rep, t_rep in (("A-19", 0.08, 0.202, 105), ("A-20", 0.18, 0.618, 34), ("A-21", 0.30, 1.54, 14)):
    P = 0.10 + 2 * 8.0 * I ** 2
    check(cid + "P", "s22", f"power at {I*1e3:.0f} mA RMS per coil", P_rep, P, "W")
    check(cid + "t", "s22", f"writing time at {I*1e3:.0f} mA RMS per coil", t_rep, E / P * 60, "min", tol_rel=0.02)
check("A-22", "s22", "force constant for 0.15 N at 80 mA", 1.9, 0.15 / 0.080, "N/A")
check("A-23", "s22", "battery current at 1.54 W, 3.7 V", 0.42, 1.54 / 3.7, "A")
check("A-24", "s22", "C-rate of 120 mAh cell at 1.54 W", 3.5, 1.54 / 3.7 / 0.120, "1/h")
# S23 packaging volume
bore = 15 - 2 * 0.7
check("A-25", "s23", "bore diameter", 13.6, bore, "mm")
check("A-26", "s23", "cylindrical volume 13.6 mm x 140 mm", 20.3, math.pi * (bore / 2) ** 2 * 140 / 1000, "cm^3")
check("A-27", "s23", "mass allocation lower sum", 20, 5 + 1 + 3 + 3 + 5 + 1 + 2, "g", tol_rel=0.0)
check("A-28", "s23", "mass allocation upper sum", 34, 8 + 3 + 5 + 5 + 7 + 3 + 3, "g", tol_rel=0.0)
# S24 storage
check("A-29", "s24", "24-byte record field sum", 24, 2 + 8 + 2 + 4 + 2 + 1 + 1 + 4, "byte", tol_rel=0.0)
check("A-30", "s24", "data rate at 200 Hz", 4.8, 24 * 200 / 1000, "kB/s")
check("A-31", "s24", "per hour", 17.28, 24 * 200 * 3600 / 1e6, "MB")
check("A-32", "s24", "32 MB duration", 1.8, 32 / 17.28, "h", tol_rel=0.05)
check("A-33", "s24", "raw 32 B at 1 kHz per hour", 115.2, 32 * 1000 * 3600 / 1e6, "MB")
# S27 sample size
check("A-34", "s27", "paired n for sigma_D = 2 delta (normal approx)", 32, ((1.96 + 0.84) * 2) ** 2, "-", tol_rel=0.03)


def paired_t_n(ratio, alpha=0.05, power=0.8):
    """Exact-iteration sample size for a two-sided paired t-test (sigma_D/delta = ratio)."""
    from scipy import stats
    for n in range(3, 1000):
        df = n - 1
        tcrit = stats.t.ppf(1 - alpha / 2, df)
        ncp = math.sqrt(n) / ratio
        pw = 1 - stats.nct.cdf(tcrit, df, ncp) + stats.nct.cdf(-tcrit, df, ncp)
        if pw >= power:
            return n, pw
    return None, None


n_t, pw_t = paired_t_n(2.0)

# --------------------------------------------------------------------------
# Corrected analyses
corr = {}

# COR-01 transverse contact load includes N cos(theta)
thetas = np.linspace(35, 75, 41) * D2R
res = []
for th in thetas:
    b = contact.transverse_load_bounds(N_rep, mu_rep, th)
    res.append((th / D2R, b["max"], b["min"], b["mean"], b["rms"]))
res = np.array(res)
corr["COR-01"] = {
    "statement": "Stage must react the transverse component of the full contact reaction, "
                 "|R_perp| = N sqrt((cos th + mu cos beta sin th)^2 + (mu sin beta)^2), not mu N.",
    "report_assumptions": {"N": N_rep, "mu": mu_rep},
    "report_drag_term_N": mu_rep * N_rep,
    "corrected_at_35deg_N": {"max": float(res[0, 1]), "min": float(res[0, 2]), "mean": float(res[0, 3])},
    "corrected_at_55deg_N": {k: float(v) for k, v in zip(["max", "min", "mean"], res[20, 1:4])},
    "corrected_at_75deg_N": {"max": float(res[-1, 1]), "min": float(res[-1, 2]), "mean": float(res[-1, 3])},
    "ratio_mean_to_report_at_35_55_75": [float(res[0, 3] / 0.15), float(res[20, 3] / 0.15), float(res[-1, 3] / 0.15)],
    "bench_envelope_worst_N": float(contact.transverse_load_bounds(2.0, 0.35, 35 * D2R)["max"]),
    "evidence_status": "analytical calculation; mu and N ranges are assumptions pending EXP-B01",
}

fig, ax = plt.subplots(figsize=(6.6, 3.6))
ax.fill_between(res[:, 0], res[:, 2], res[:, 1], color=plotstyle.SERIES[0], alpha=0.12, linewidth=0)
ax.plot(res[:, 0], res[:, 3], color=plotstyle.SERIES[0], label="Corrected |R⊥|, mean over stroke direction")
ax.plot(res[:, 0], res[:, 1], color=plotstyle.SERIES[0], linewidth=1.0)
ax.plot(res[:, 0], res[:, 2], color=plotstyle.SERIES[0], linewidth=1.0)
ax.axhline(0.15, color=plotstyle.SERIES[1], label="Report sizing term μN = 0.15 N")
ax.set_xlabel("Pen altitude above page θ (deg)")
ax.set_ylabel("Transverse load on stage (N)")
ax.set_title("Stage load at the report's own assumptions (N = 0.75 N, μ = 0.2)", loc="left")
ax.text(36, res[0, 1] + 0.02, "band: push … pull strokes", color=plotstyle.INK2, fontsize=8)
ax.set_ylim(0, 1.0)
ax.legend(loc="upper right")
plotstyle.stamp(fig, "analytical calculation", "stabpen.contact; not measured")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_transverse_load_vs_tilt.png"))
plt.close(fig)

# COR-02 holding power: direct drive vs lever
Km_direct = np.array([0.15, 0.3, 0.6])
F_design = contact.transverse_load_bounds(1.0, 0.15, 50 * D2R)["rms"]
F_worst = contact.transverse_load_bounds(2.0, 0.35, 35 * D2R)["max"]
corr["COR-02"] = {
    "design_point": {"N": 1.0, "mu": 0.15, "theta_deg": 50, "F_perp_rms_N": float(F_design)},
    "worst_bench_point": {"N": 2.0, "mu": 0.35, "theta_deg": 35, "F_perp_max_N": float(F_worst)},
    "direct_drive_hold_power_W": {f"Km={km}": float(actuator.hold_power(F_design, km)) for km in Km_direct},
    "lever_n4_Km0.35_hold_power_W": float(actuator.hold_power(F_design / 4, 0.35)),
    "lever_n4_Km0.35_worst_W": float(actuator.hold_power(F_worst / 4, 0.35)),
    "note": "Holding power is independent of wire gauge (motor-constant scaling). Km values are "
            "bracketing assumptions until analysis/em_actuator.py and EXP-B03 establish them.",
}

# COR-03 axial accommodation for a page-referenced workspace
wt = {}
for deg in (35, 50, 75):
    wt[str(deg)] = frames.stage_travel_for_paper_disc(0.5e-3, deg * D2R)
corr["COR-03"] = {"statement": "For a +/-0.5 mm PAGE disc, transverse stage radius 0.5 mm suffices for any roll; "
                               "axial accommodation needed is r*cos(theta) (0.41 mm at 35 deg), not 0.71 mm.",
                  "values_m": wt}

# COR-05 pressure modulation vs axial stiffness (corrections.csv numbering)
ks = np.logspace(1.5, 3.7, 60)
dN35 = contact.pressure_modulation(ks, 0.5e-3 * math.sin(35 * D2R), 35 * D2R)
dN50 = contact.pressure_modulation(ks, 0.5e-3 * math.sin(50 * D2R), 50 * D2R)
corr["COR-05"] = {"statement": "Axial accommodation against an axial stiffness k modulates the normal force by "
                               "k * r cos(theta) / sin(theta) ... at 0.5 mm page correction.",
                  "k_for_dN_le_0.1N_at35deg": float(ks[np.argmax(dN35 > 0.1)]) if np.any(dN35 > 0.1) else None,
                  "dN_at_k250_35deg_N": float(contact.pressure_modulation(250, 0.5e-3 * math.sin(35 * D2R), 35 * D2R)),
                  "dN_at_k1000_35deg_N": float(contact.pressure_modulation(1000, 0.5e-3 * math.sin(35 * D2R), 35 * D2R))}
fig, ax = plt.subplots(figsize=(6.2, 3.4))
ax.loglog(ks, dN35, color=plotstyle.SERIES[0], label="θ = 35°")
ax.loglog(ks, dN50, color=plotstyle.SERIES[1], label="θ = 50°")
ax.axhline(0.1, color=plotstyle.MUTED, linewidth=1.0)
ax.text(40, 0.11, "0.1 N (10% of 1 N)", color=plotstyle.INK2, fontsize=8)
ax.set_xlabel("Effective axial stiffness at the nib (N/m)")
ax.set_ylabel("Normal-force modulation amplitude (N)")
ax.set_title("Pressure modulation from 0.5 mm page correction along the tilt plane", loc="left")
ax.legend()
plotstyle.stamp(fig, "analytical calculation", "rigid page; hand compliance neglected")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_pressure_modulation.png"))
plt.close(fig)

# COR-07 delay: extend beyond ideal equal-amplitude cancellation
f_ax = np.linspace(1, 15, 281)
out = {}
for label, tau, fn, zeta in (("ideal 5 ms", 5e-3, None, None), ("5 ms + 60 Hz servo", 5e-3, 60.0, 0.7),
                             ("2 ms + 60 Hz servo", 2e-3, 60.0, 0.7), ("2 ms + 30 Hz servo", 2e-3, 30.0, 0.7)):
    s = 2j * math.pi * f_ax
    T = np.ones_like(s) if fn is None else (2 * math.pi * fn) ** 2 / (s ** 2 + 2 * zeta * 2 * math.pi * fn * s + (2 * math.pi * fn) ** 2)
    out[label] = np.abs(1 - T * np.exp(-s * tau))
corr["COR-07"] = {"statement": "Report's |1-exp(-j w tau)| holds only for unity-gain instantaneous actuation. "
                               "Servo phase lag adds equivalent delay; e.g. a 60 Hz, zeta 0.7 servo adds ~3.7 ms at 8 Hz.",
                  "residual_at_8Hz": {k: float(np.interp(8.0, f_ax, v)) for k, v in out.items()}}
fig, ax = plt.subplots(figsize=(6.4, 3.5))
for i, (k, v) in enumerate(out.items()):
    ax.plot(f_ax, v, color=plotstyle.SERIES[i], label=k)
ax.axhline(1.0, color=plotstyle.MUTED, linewidth=1.0)
ax.set_xlabel("Disturbance frequency (Hz)")
ax.set_ylabel("Residual / original amplitude")
ax.set_title("Cancellation residual: delay plus closed-loop stage dynamics", loc="left")
ax.set_ylim(0, 1.2)
ax.legend(loc="upper left")
plotstyle.stamp(fig, "analytical calculation", "no prediction, exact amplitude knowledge")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_delay_residual_servo.png"))
plt.close(fig)

# COR-08 IMU: attitude error dominates bias
g0 = 9.80665
corr["COR-08"] = {
    "bias_1mg_1s_mm": 0.5 * 1e-3 * g0 * 1e3,
    "attitude_0.1deg_gravity_leak_1s_mm": 0.5 * g0 * math.sin(0.1 * D2R) * 1e3,
    "noise_70ug_rtHz_random_walk_1s_mm": 7e-4 * 1.0 ** 1.5 / math.sqrt(3) * 1e3,
    "statement": "Report's 1 mg example understates the problem; a 0.1 deg attitude error leaks ~1.7 mg of gravity "
                 "(8.6 mm after 1 s). IMU is useful only over the optical latency window (ms).",
    "error_over_2ms_optical_gap_um": 0.5 * (1e-3 * g0 + g0 * math.sin(0.1 * D2R)) * (2e-3) ** 2 * 1e6,
}

# COR-02 (runtime part) energy: runtime with corrected load
Pel = float(__import__("stabpen.params", fromlist=["load"]).load()["electrical.p_electronics_active"])
E_10440 = 0.8 * 3.7 * 0.350
rt = {}
for label, n_lev, km in (("direct Km0.3", 1, 0.3), ("direct Km0.6", 1, 0.6), ("lever n4 Km0.35", 4, 0.35), ("lever n5 Km0.45", 5, 0.45)):
    P_act = actuator.hold_power(F_design / n_lev, km) * 0.65  # 65% pen-down duty (assumption)
    rt[label] = {"P_act_avg_W": float(P_act), "runtime_min_120mAh": float(E / (P_act + Pel) * 60),
                 "runtime_min_350mAh": float(E_10440 / (P_act + Pel) * 60)}
corr["COR-02_runtime"] = {"assumptions": f"design point N=1 N, mu=0.15, theta=50 deg; 65% pen-down duty; {Pel:.3f} W electronics (config); "
                                 "dynamic tremor currents excluded (see sim results)", "runtime": rt}

# Sample size: t-distribution
corr["COR-09"] = {"paired_t_exact_n_for_ratio_2": n_t, "achieved_power": pw_t,
                  "statement": "Normal approximation gives 32; exact paired t gives slightly more before attrition."}

# write outputs
with open(os.path.join(OUT, "audit_checks.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(checks[0].keys()))
    wr.writeheader()
    wr.writerows(checks)
provenance.write_json(os.path.join(OUT, "audit_corrections.json"), corr)
provenance.write_json(os.path.join(OUT, "metadata.json"),
                      provenance.metadata("analytical calculation", extra={"script": "analysis/audit_recalc.py"}))

n_ok = sum(c["arithmetic_reproduced"] == "yes" for c in checks)
print(f"{n_ok}/{len(checks)} report numbers reproduced under the report's own assumptions")
for c in checks:
    if c["arithmetic_reproduced"] != "yes":
        print("  MISMATCH", c)
print("COR-01 mean transverse load at 35/55/75 deg (N):",
      [round(corr["COR-01"][k]["mean"], 3) for k in ("corrected_at_35deg_N", "corrected_at_55deg_N", "corrected_at_75deg_N")])
print("COR-02 hold power direct (W):", corr["COR-02"]["direct_drive_hold_power_W"], " lever:",
      round(corr["COR-02"]["lever_n4_Km0.35_hold_power_W"], 3), " lever worst:", round(corr["COR-02"]["lever_n4_Km0.35_worst_W"], 3))
print("COR-05", corr["COR-05"])
print("COR-07", corr["COR-07"]["residual_at_8Hz"])
print("COR-08", {k: round(v, 3) if isinstance(v, float) else v for k, v in corr["COR-08"].items() if k != "statement"})
print("COR-02 runtime", rt)
print("COR-09", corr["COR-09"])
