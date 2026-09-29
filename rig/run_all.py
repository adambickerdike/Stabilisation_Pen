"""python3 -m rig.run_all : write results/rig/ (tables, budgets, CALC envelopes, SIM demos, figures with CSV twins).

    python3 -m rig.run_all            tables, budgets, calculations, the self-test and the figures
    python3 -m rig.run_all --cad      also run mechanics/cad/rig_*.py (STEP files and drawings in results/rig/cad/)

One process. Every JSON carries stabpen.provenance metadata; every figure has a CSV twin and an
evidence stamp. Nothing here is a measurement.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

from . import CALC, RESULTS, SIM, bom, experiments, ledger, results_path
from . import uncertainty as U

BUILD_PLAN = [
    # (step, rig, what, start_week, weeks, cost class) -- durations are ASSUMPTIONS (one engineer, parts in stock)
    (1, "DAQ-1", "Teensy 4.1 + ADS131M08EVM + encoders, sync, logger", 0, 2, "A"),
    (2, "R9", "Contact and ink rig on a CoreXY frame (G1)", 1, 4, "B (low-cost) / C (standard)"),
    (3, "R10", "Page-sensor rig on the same frame", 3, 3, "B / D with Zaber truth"),
    (4, "R11", "Tablet protocol now; recording pen later", 0, 2, "B"),
    (5, "R12", "Actuator coupon bench (G2), when study B's coupons exist", 5, 3, "B / C"),
    (6, "R13-1", "One-axis loaded nib rig (G3)", 7, 4, "B / C"),
    (7, "R13-2", "Second axis, tilt-roll holder, 30 C runs (G4)", 11, 3, "B"),
    (8, "R14", "Grip simulant on the R13 stage (G5)", 12, 3, "A / B"),
]
COST_CLASS = {"A": "< USD 500", "B": "USD 500-2,000", "C": "USD 2,000-10,000", "D": "> USD 10,000"}

# R13 disturbance stage (PROPOSED DESIGN, mechanics/cad/rig_nib.py): four 0.15 x 15 x 50 mm leaves, E 200 GPa ASSUMED
STAGE_K = 324.0          # N/m, CALC: 4 E b t^3 / L^3
STAGE_M = 0.175          # kg, CAD roll-up of the moving stage without the pen (173-178 g; densities, coil 30 g and camera 15 g ASSUMED)
MODULES = {"slim core module (35 g)": 0.035, "24 mm pen module (90 g)": 0.090}   # ASSUMPTION (study B class masses)


def _prov(status, extra=None):
    from stabpen import provenance
    return provenance.metadata(status, extra=extra)


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def static_side_load() -> dict:
    """CALC: the static side load at the ball (review section 4) that G1 turns into a measured range."""
    thetas = np.arange(35, 76, 5.0)
    Fc = [0.05, 0.075, 0.10, 0.15]
    from .contact import predicted_ratio_perp_to_axial
    rows = []
    for th in thetas:
        r = {"theta_deg": float(th), "cot": float(1 / math.tan(math.radians(th)))}
        for F in Fc:
            r[f"Fperp_mN_Fc{F:g}_frictionless"] = 1e3 * F / math.tan(math.radians(th))
        for mu in (0.10, 0.15, 0.30):
            ratios = predicted_ratio_perp_to_axial(math.radians(th), mu, np.radians(np.arange(0, 360, 5)))
            r[f"ratio_min_mu{mu:g}"] = float(ratios.min())
            r[f"ratio_max_mu{mu:g}"] = float(ratios.max())
        # C1S copper loss for the frictionless load (review's inputs, CALC): P = (F_perp * L_t / L_a / Km)^2
        r["C1S_holding_W_Fc0.15"] = (0.15 / math.tan(math.radians(th)) * 76.48 / 11.5 / 0.656) ** 2
        rows.append(r)
    return {"rows": rows, "note": "F_perp = F_c cot(theta) without friction; with friction R_perp/F_c from P-6/P-7 over all "
                                  "stroke directions (rig.contact.predicted_ratio_perp_to_axial). C1S holding loss uses the "
                                  "review's inputs (L_t 76.48 mm, L_a 11.5 mm, Km 0.656 N/sqrt(W)): 4.717/1.628/0.166 W at "
                                  "35/50/75 deg (CALC, reproduces the review)."}


def disturbance_envelope() -> dict:
    """CALC: sine-by-sine force the R13 stage needs over the review's G3 envelope, against the LVCM-032-025-02 ratings."""
    from .frf import envelope_limits
    f = np.array([1, 2, 3, 4, 6, 8, 10, 12, 15, 20, 25, 30], float)
    cases = {name: STAGE_M + m for name, m in MODULES.items()}
    k = STAGE_K
    out = {"k_flex_N_per_m": k, "stage_moving_kg_without_pen": STAGE_M, "F_cont_N": 9.3, "F_peak_N": 29.3,
           "source": "ratings MFR AMF-232 (LVCM-032-025-02); stiffness CALC and moving mass from the CAD roll-up "
                     "(mechanics/cad/rig_nib.py, densities, coil and camera masses ASSUMPTION)", "cases": {}}
    for name, m in cases.items():
        rows = []
        for amp in (0.25e-3, 0.5e-3, 1e-3, 2e-3):
            e = envelope_limits(f, amp, m, k, 9.3, 29.3, 6.35e-3)
            rows.append({"amp_mm": amp * 1e3, "F_needed_N": e["F_needed_N"].round(3).tolist(),
                         "within_continuous": e["within_continuous"].tolist(), "within_peak": e["within_peak"].tolist()})
        out["cases"][name] = {"m_moving_kg": m, "rows": rows}
    out["f_hz"] = f.tolist()
    return out


def disturbance_design_examples() -> dict:
    from .frf import design_disturbance, stage_force_needed
    out = []
    for xp in (0.25e-3, 0.5e-3, 1e-3, 2e-3):
        d = design_disturbance(xp, f_lo=1.0, f_hi=30.0, n_tones=24, T=10.0, fs=2000.0, a_max=40.0)
        F = stage_force_needed(d["x"], 2000.0, STAGE_M + MODULES["24 mm pen module (90 g)"], STAGE_K)
        out.append({"x_peak_mm": round(d["x_peak_m"] * 1e3, 3), "a_peak_m_s2": round(d["a_peak"], 2),
                    "acc_limited": d["acc_limited"], "crest": round(d["crest"], 2), "tones": len(d["f"]),
                    "F_peak_N_24mm_module": round(F["F_peak_N"], 2), "F_rms_N_24mm_module": round(F["F_rms_N"], 2)})
    return {"rows": out, "note": "24 log-spaced tones 1-30 Hz on a 0.1 Hz grid, Schroeder phases, peak acceleration capped at "
                                 "40 m/s^2 (ASSUMPTION: keeps the nib module's own accelerometers in range); force for the "
                                 f"{STAGE_M + MODULES['24 mm pen module (90 g)']:.3f} kg moving mass (24 mm pen) on the "
                                 f"{STAGE_K:.0f} N/m flexure"}


def page_noise_example() -> dict:
    """SIM: the EXP-J10 addition's model on synthetic window errors, (a) sim2j's own 'deltapen_held' draw (DeltaPen's
    median and mean used as the held position error, as sim2j does) and (b) the same plus a 5 um walk step."""
    from . import synth
    from .pagesense import page_error_model_from_runs
    sig = math.sqrt(2 * math.log(68.3 / 23.6))
    out = {}
    for name, walk in (("sim2j_deltapen_held", 0.0), ("held_plus_5um_walk", 5.0)):
        r = synth.page_error_runs(held_median_um=23.6, held_sigma=sig, walk_step_um=walk, n_runs=30)
        m = page_error_model_from_runs(r["runs"])
        m["_truth"] = r["_truth"]
        out[name] = m
    return out


def figures(side, env, tur_rows, st):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    fig_dir = RESULTS
    made = []

    # 1. static side load: frictionless lines for four F_c + friction band at 0.15 N
    th = [r["theta_deg"] for r in side["rows"]]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for i, F in enumerate([0.05, 0.075, 0.10, 0.15]):
        y = [r[f"Fperp_mN_Fc{F:g}_frictionless"] for r in side["rows"]]
        ax.plot(th, y, color=ps.SERIES[i], label=f"F_c = {F:g} N (no friction)")
        ax.text(th[1] + 0.3, y[1] + 6, f"{F:g} N", color=ps.INK2, fontsize=8, va="bottom")
    lo = [1e3 * 0.15 * r["ratio_min_mu0.15"] for r in side["rows"]]
    hi = [1e3 * 0.15 * r["ratio_max_mu0.15"] for r in side["rows"]]
    ax.fill_between(th, lo, hi, color=ps.SERIES[3], alpha=0.18, lw=0, label="F_c 0.15 N, mu 0.15, any stroke direction")
    ax.set_xlabel("pen altitude above the page theta (deg)")
    ax.set_ylabel("static side load at the ball (mN)")
    ax.set_title("What gate G1 measures: the side load a nib must hold, per F_c", loc="left")
    ax.legend(loc="upper right")
    ax.set_xlim(34, 79)
    ps.stamp(fig, "calculation", "F_c cot(theta) and P-6/P-7 with an assumed mu; R9 replaces both with measured maps")
    fig.tight_layout()
    p = os.path.join(fig_dir, "fig_rig_static_side_load.png")
    fig.savefig(p)
    plt.close(fig)
    _write_csv(p.replace(".png", ".csv"), ["theta_deg"] + [f"Fperp_mN_Fc{F:g}_frictionless" for F in (0.05, 0.075, 0.10, 0.15)]
               + ["Fperp_mN_Fc0.15_mu0.15_min", "Fperp_mN_Fc0.15_mu0.15_max"],
               [[r["theta_deg"]] + [round(r[f"Fperp_mN_Fc{F:g}_frictionless"], 3) for F in (0.05, 0.075, 0.10, 0.15)]
                + [round(a, 3), round(b, 3)] for r, a, b in zip(side["rows"], lo, hi)])
    made.append(p)

    # 2. disturbance envelope: force needed vs frequency for 4 amplitudes (24 mm module) + actuator ratings
    f = env["f_hz"]
    case = env["cases"]["24 mm pen module (90 g)"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for i, row in enumerate(case["rows"]):
        ax.plot(f, row["F_needed_N"], color=ps.SERIES[i], marker="o", markersize=5, markeredgecolor=ps.SURFACE,
                label=f"{row['amp_mm']:g} mm peak")
    ax.axhline(env["F_cont_N"], color=ps.MUTED, lw=1.2, ls="--")
    ax.axhline(env["F_peak_N"], color=ps.MUTED, lw=1.2, ls=":")
    ax.text(2.0, env["F_cont_N"] * 1.1, "voice coil continuous 9.3 N (MFR AMF-232)", color=ps.INK2, fontsize=8)
    ax.text(2.0, env["F_peak_N"] * 1.1, "voice coil peak 29.3 N", color=ps.INK2, fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("disturbance frequency (Hz)")
    ax.set_ylabel("stage force for a sine (N)")
    ax.set_title(f"R13 stage force over the G3 envelope ({case['m_moving_kg']:.3f} kg moving, 24 mm pen)", loc="left")
    ax.legend(loc="lower right")
    ax.set_ylim(5e-3, 80)
    ps.stamp(fig, "calculation", "|k - m w^2| x; k from the leaf design, mass from the CAD roll-up (assumed densities)")
    fig.tight_layout()
    p = os.path.join(fig_dir, "fig_rig_disturbance_envelope.png")
    fig.savefig(p)
    plt.close(fig)
    _write_csv(p.replace(".png", ".csv"), ["f_hz"] + [f"F_needed_N_{r['amp_mm']:g}mm" for r in case["rows"]],
               [[fv] + [r["F_needed_N"][i] for r in case["rows"]] for i, fv in enumerate(f)])
    made.append(p)

    # 3. TUR per decision (horizontal bars, one axis)
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    labels = [f"{r['rig']}: {r['short']}" for r in tur_rows]
    vals = [min(r["TUR"], 30) for r in tur_rows]
    y = np.arange(len(vals))[::-1]
    ax.barh(y, vals, color=ps.SERIES[0], height=0.6)
    ax.axvline(4, color=ps.INK2, lw=1.2)
    ax.text(4.3, y[-1] - 0.9, "TUR 4: simple acceptance to the right, guarded to the left", color=ps.INK2, fontsize=8)
    ax.set_ylim(y[-1] - 1.3, y[0] + 0.6)
    for yy, v, r in zip(y, vals, tur_rows):
        ax.text(v + 0.3, yy, f"{r['TUR']:.1f}", va="center", color=ps.INK2, fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("test uncertainty ratio (tolerance / U, k = 2); capped at 30")
    ax.set_title("Can each rig decide what it is built to decide?", loc="left")
    ps.stamp(fig, "calculation", "budgets in rig/uncertainty.py; MFR values and assumptions, not measured")
    fig.tight_layout()
    p = os.path.join(fig_dir, "fig_rig_tur.png")
    fig.savefig(p)
    plt.close(fig)
    _write_csv(p.replace(".png", ".csv"), ["rig", "short", "decision", "U_k2", "unit", "tolerance", "TUR", "rule", "dominant_term"],
               [[r["rig"], r["short"], r["decision"], r["U_k2"], r["unit"], r["tolerance"], r["TUR"], r["rule"], r["dominant_term"]]
                for r in tur_rows])
    made.append(p)

    # 4. SIM demo: transmissibility recovered from synthetic multitone data
    ex = st.get("_extras", {}).get("check_frf")
    if ex:
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        ax.plot(ex["transmissibility_f"], ex["T_true"], color=ps.SERIES[0], label="synthetic plant (truth)")
        ax.plot(ex["transmissibility_f"], ex["T_meas"], **ps.marker_kw(ps.SERIES[1]), label="recovered by rig.frf")
        ax.set_xscale("log")
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("ink motion / housing motion")
        ax.set_title("Method check: transmissibility from a 1-30 Hz multitone (oracle nib, 60 Hz servo, 2.5 ms)", loc="left")
        ax.legend(loc="upper left")
        ps.stamp(fig, "simulation", "synthetic data only; checks the analysis, says nothing about a nib")
        fig.tight_layout()
        p = os.path.join(fig_dir, "fig_rig_method_transmissibility.png")
        fig.savefig(p)
        plt.close(fig)
        _write_csv(p.replace(".png", ".csv"), ["f_hz", "T_true", "T_recovered"],
                   [[round(a, 4), round(b, 5), round(c, 5)] for a, b, c in zip(ex["transmissibility_f"], ex["T_true"], ex["T_meas"])])
        made.append(p)

    # 5. build order (Gantt)
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    for i, (step, rig, what, s, w, cc) in enumerate(BUILD_PLAN):
        yy = len(BUILD_PLAN) - i
        ax.barh(yy, w, left=s, color=ps.SERIES[0] if rig != "R11" else ps.SERIES[2], height=0.55)
        ax.text(s + w + 0.15, yy, f"{rig}: {what} [{cc}]", va="center", fontsize=7.5, color=ps.INK2)
    ax.set_yticks([])
    ax.set_xlim(0, 30)
    ax.set_xlabel("weeks from the start (one engineer; parts in stock) - assumption")
    ax.set_title("Build order: G1 and sensing first, the nib rigs when study B's parts exist", loc="left")
    ps.stamp(fig, "proposed design", "durations are assumptions")
    fig.tight_layout()
    p = os.path.join(fig_dir, "fig_rig_build_order.png")
    fig.savefig(p)
    plt.close(fig)
    _write_csv(p.replace(".png", ".csv"), ["step", "rig", "what", "start_week", "weeks", "cost_class"], BUILD_PLAN)
    made.append(p)
    return made


def run_cad():
    root = os.path.dirname(RESULTS.rstrip("/"))
    root = os.path.dirname(root)
    outs = {}
    for name in ("rig_contact", "rig_coupon", "rig_nib", "rig_pagesense", "rig_grip", "rig_recpen"):
        script = os.path.join(root, "mechanics", "cad", name + ".py")
        if not os.path.exists(script):
            continue
        t0 = time.time()
        r = subprocess.run([sys.executable, script], cwd=root, capture_output=True, text=True)
        outs[name] = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1),
                      "stderr_tail": r.stderr[-400:] if r.returncode else ""}
        print(f"  {name}: rc={r.returncode} in {outs[name]['seconds']} s")
    return outs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cad", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(RESULTS, exist_ok=True)
    t0 = time.time()
    n_bom = bom.write(results_path("bom.csv"))
    n_led = ledger.write(results_path("evidence_rows.csv"))
    n_exp = experiments.write_all(RESULTS)
    budgets = {k: b.as_dict() for k, b in U.all_budgets().items()}
    tur_rows = U.tur_table()
    side = static_side_load()
    env = disturbance_envelope()
    dex = disturbance_design_examples()
    pn = page_noise_example()
    provenance_mod = __import__("stabpen.provenance", fromlist=["provenance"])
    provenance_mod.write_json(results_path("page_noise_model_example.json"),
                              {"meta": _prov(SIM + " (synthetic window errors; the format EXP-J10 will fill with measurements)"),
                               "models": pn})
    _write_csv(results_path("page_noise_model_example_structure.csv"), ["case", "lag_s", "rms_um", "p95_um", "n"],
               [[k, r["lag_s"], round(r["rms_um"], 3), round(r["p95_um"], 3), r["n"]] for k, m in pn.items()
                for r in m["structure_function"]])
    from .selftest import run as selftest_run
    st = selftest_run(quick=False, write=True)
    summary = {"meta": _prov(CALC + " (budgets, envelopes) and " + SIM + " (self-test on synthetic data)"),
               "bom_rows": n_bom, "bom_seen_price_floor_usd": bom.seen_totals(), "evidence_rows": n_led,
               "experiments": n_exp, "uncertainty_budgets": budgets, "tur_table": tur_rows,
               "static_side_load": side, "disturbance_envelope": env, "disturbance_designs": dex,
               "page_noise_example": {k: {kk: m[kk] for kk in ("window_error_um", "held_rms_um", "walk_step_rms_um",
                                                                "mode_supported", "drift", "sim2j")} for k, m in pn.items()},
               "build_plan": [dict(zip(["step", "rig", "what", "start_week", "weeks", "cost_class"], r)) for r in BUILD_PLAN],
               "cost_classes": COST_CLASS,
               "selftest": {k: st[k] for k in ("n_checks", "n_pass", "all_pass", "timing_s")}}
    from stabpen import provenance
    provenance.write_json(results_path("rig_summary.json"), summary)
    _write_csv(results_path("uncertainty_budgets.csv"), ["budget", "measurand", "unit", "line", "value", "distribution",
                                                         "u", "source", "U_k2"],
               [[k, b["measurand"], b["unit"], l["name"], l["value"], l["distribution"], round(l["u"], 5), l["source"],
                 round(b["U"], 4)] for k, b in budgets.items() for l in b["lines"]])
    made = [] if a.no_figures else figures(side, env, tur_rows, st)
    cad = run_cad() if a.cad else {}
    print(f"results/rig written in {time.time() - t0:.1f} s: bom {n_bom} rows, ledger {n_led} rows, {n_exp}, "
          f"self-test {st['n_pass']}/{st['n_checks']}, figures {len(made)}, cad {list(cad)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
