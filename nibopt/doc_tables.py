"""Markdown tables for docs/nib_optimisation.md, generated from results/nibopt/*.json so the document's numbers are the
computed ones:  python3 -m nibopt.doc_tables > nibopt/build/doc_tables.md"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import RESULTS

NAMES = {"K_B1": "Rev K's B1 (study K)", "P_1059_24": "pass 1.059 mm / 24 mm", "P_150_24": "pass 1.5 mm / 24 mm",
         "P_1059_20": "pass 1.059 mm / 20 mm"}


def f(x, n=1):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    try:
        return f"{x:.{n}f}"
    except Exception:
        return str(x)


def mw(x, n=1):
    return "-" if x is None else f"{x * 1e3:.{n}f}"


def load(name):
    return json.loads((RESULTS / name).read_text())


def reconciliation() -> str:
    r = load("reconciliation.json")
    t = r["table"]
    ks = list(t)
    head = "| quantity (label) | " + " | ".join(NAMES.get(k, k) for k in ks) + " |\n|---|" + "---|" * len(ks) + "\n"
    rows = []

    def row(label, fn):
        rows.append(f"| {label} | " + " | ".join(fn(t[k]) for k in ks) + " |")
    row("usable radius / stop (mm) (PD)", lambda e: f"{e['design']['reach_mm']:.3f} / {e['design']['stop_mm']:.3f}")
    row("body OD / length (mm) (PD / CALC)", lambda e: f"{e['design']['od_mm']:.0f} / {e['design']['length_mm']:.1f}")
    row("moving mass, this model (g) (CALC)", lambda e: f(e["design"]["m_move_g"], 2))
    row("K_m at the centre x / y, upper bound (N/sqrt W) (CALC)",
        lambda e: f"{e['magnetics']['Km_centre_x_N_sqrtW']:.3f} / {e['magnetics']['Km_centre_y_N_sqrtW']:.3f}")
    row("weakest over the disk / x 0.7 (N/sqrt W) (CALC)",
        lambda e: f"{e['magnetics']['sv_min_workspace_N_sqrtW']:.3f} / {e['magnetics']['sv_min_workspace_x0.7']:.3f}")
    row("wires: n x d x L (mm), anchor (N/m) (PD)",
        lambda e: f"{e['design']['wires']['n']} x {e['design']['wires']['d_mm']:.2f} x {e['design']['wires']['L_mm']:.1f}, "
                  f"{e['design']['wires']['anchor_N_m']:.0f}")
    row("Goodman at the stop, worst tolerance corner (CALC; >= 1.5)", lambda e: f(e["wires"]["goodman_worst_corner"], 2))
    row("guide drag at 35 deg (mN) / Hertz sustained / drop (GPa) (CALC)",
        lambda e: f"{e['guide']['drag_35_mN']:.1f} / {e['guide']['hertz_run_GPa']:.2f} / {e['guide']['hertz_static_GPa']:.2f}")
    row("lead factor R_loop / R_coil (CALC)", lambda e: f(e["leads"]["factor"], 3))
    row("**duty A, mean 35-75 deg (mW): weakest x 0.7** (CALC)", lambda e: "**" + mw(e["dutyA"]["worst07"]["mean"]) + "**")
    row("duty A, mean: centre x 1.0 / centre x 0.7 (mW) (CALC)",
        lambda e: f"{mw(e['dutyA']['centre10']['mean'])} / {mw(e['dutyA']['centre07']['mean'])}")
    row("duty A, worst (35 deg, worst roll, residual p95): weakest x 0.7 / centre x 1.0 (mW) (CALC)",
        lambda e: f"{mw(e['dutyA']['worst07']['worst'])} / {mw(e['dutyA']['centre10']['worst'])}")
    row("severe duty (study F's +2-words residual, 6 Hz), mean / at 35 deg: weakest x 0.7 (mW) (CALC on SIM statistics)",
        lambda e: f"{mw(e['severe']['worst07']['mean'])} / {mw(e['severe']['worst07']['P35_W'])}")
    row("severe duty: nib travel rms 2-D (mm) / share at the stop (CALC)",
        lambda e: f"{e['severe_motion']['q_rms_2d_mm']:.2f} / {e['severe_motion']['at_limit']:.2f}")
    row("tremor left at the tip at the severe class, estimator at the +2 residual / perfect knowledge (mm) (SIM, study F, "
        "interpolated by reach)", lambda e: f"{e['severe_motion']['F_a_r2_tip_mm']:.2f} / {e['severe_motion']['F_oracle_tip_mm']:.2f}")
    row("**worst-case screen, matched loads (W): weakest x 0.7** (CALC)", lambda e: "**" + f(e["screen"]["worst07"], 3) + "**")
    row("screen: the pass's map x 0.7 / centre x 1.0 (W) (CALC)",
        lambda e: f"{f(e['screen']['map07'], 3)} / {f(e['screen']['centre10'], 3)}")
    row("screen: coil if sustained (degC) (CALC)", lambda e: f(e["screen"]["worst07_coil_C"], 0))
    row("hours, steady 1 mm: conservative / optimistic (CALC)",
        lambda e: f"{e['battery']['conservative']['steady_1mm']['hours']:.1f} / {e['battery']['optimistic']['steady_1mm']['hours']:.1f}")
    row("hours, severe duty: conservative / optimistic (CALC)",
        lambda e: f"{e['battery']['conservative']['severe']['hours']:.1f} / {e['battery']['optimistic']['severe']['hours']:.1f}")
    row("skin, hottest point, severe at 35 deg: weakest x 0.7 / centre x 1.0 (degC, 30 degC room) (CALC)",
        lambda e: f"{e['severe']['worst07']['skin']['max_shell_C']:.1f} / {e['severe']['centre10']['skin']['max_shell_C']:.1f}")
    row("front finger pad, steady 1 mm at 35 deg: weakest x 0.7 (degC) (CALC)",
        lambda e: f(e["nib_by_mode"]["worst07"]["steady_1mm"]["front_pad_C"], 1))
    row("peak force (N) / current (A) / voltage (V) at 3.3 V (CALC)",
        lambda e: f"{e['electrical']['F_peak_N']:.3f} / {e['electrical']['I_peak_A']:.2f} / {e['electrical']['V_peak_V']:.2f}")
    row("servo bandwidth allowed, worst case (Hz; >= 40) (CALC)", lambda e: f(e["modes"]["servo_bw_max_worst_Hz"], 1))
    row("coil clearance at the stop, p99 (mm; >= 0.2) (CALC)", lambda e: f(e["fit"]["coil_clearance_p99_mm"], 2))
    row("constraints failed (CALC)", lambda e: ", ".join(k for k, v in e["constraints"].items() if k != "feasible" and v < 0)
        or "none")
    return head + "\n".join(rows) + "\n"


def waterfall_K() -> str:
    r = load("reconciliation.json")["waterfall_K"]
    s = "| step | change | duty A, mean (mW) | change (mW) |\n|---|---|---|---|\n"
    for x in r["steps"]:
        d = "-" if x["delta_mW"] is None else f"{x['delta_mW']:+.2f}"
        s += f"| {x['step']} | {x['name']}: {x['what']} | {x['P_mW']:.2f} | {d} |\n"
    return s


def waterfall_pass(name="P_150_24", key="waterfall_pass") -> str:
    r = load("reconciliation.json")[key][name]
    s = "| step | change | worst-case screen (W) | change (W) |\n|---|---|---|---|\n"
    for x in r["steps"]:
        d = "-" if x["delta_W"] is None else f"{x['delta_W']:+.4f}"
        s += f"| {x['step']} | {x['name']}: {x['what']} | {x['P_W']:.4f} | {d} |\n"
    return s


def pass_summary() -> str:
    r = load("reconciliation.json")["waterfall_pass"]
    s = "| design | the pass (20 mN) | re-run | this package, the pass's loads | + matched static | + drag fluctuation | + guide drag | coil temperature | weakest x 0.7 |\n|---|---|---|---|---|---|---|---|---|\n"
    for n, w in r.items():
        v = [x["P_W"] for x in w["steps"]]
        # steps: 0 published, 1 re-run, 2 package, 3 mass, 4 static, 5 drag var, 6 guide, 7 temp, 8 weakest
        s += f"| {NAMES.get(n, n)} | {v[0]:.4f} | {v[1]:.4f} | {v[2]:.4f} | {v[4]:.4f} | {v[5]:.4f} | {v[6]:.4f} | {v[7]:.4f} | {v[8]:.4f} |\n"
    return s


def topologies() -> str:
    r = load("reconciliation.json")["screen_topologies"]
    s = "| topology | carries the couple? | lateral force at the 1.7 mm stop (mN) | drag (mN) | why |\n|---|---|---|---|---|\n"
    for x in r["rows"]:
        fs = "-" if x.get("F_stop_mN") is None else f"{x['F_stop_mN']:.0f}"
        s += f"| {x['topology']} | {'yes' if x['carries_couple'] else 'no'} | {fs} | {f(x.get('drag_mN'), 1)} | {x['reason']} |\n"
    return s


def pareto() -> str:
    r = load("pareto.json")
    s = "| body OD <= (mm) | largest usable radius (mm) | its typical loss (mW) | its worst-case loss (W) | length (mm) |\n|---|---|---|---|---|\n"
    for od, v in r["targeted"]["max_reach_by_od"].items():
        s += f"| {od} | {v['reach_mm']:.2f} | {v['typical_W'] * 1e3:.1f} | {v['screen_W']:.3f} | {v['length_mm']:.1f} |\n"
    s += "\n| usable radius bin (mm), OD <= 24 | best typical loss (mW) | its worst-case (W) | OD (mm) | length (mm) | reach per typical watt (mm/W) |\n|---|---|---|---|---|---|\n"
    for b, v in r["targeted"]["reach_per_watt"].get("best_by_reach_bin_od_le_24", {}).items():
        s += (f"| {b} | {v['typical_W'] * 1e3:.1f} | {v['screen_W']:.3f} | {v['od_mm']:.1f} | {v['length_mm']:.1f} | "
              f"{v['reach_per_W_mm']:.1f} |\n")
    return s


def candidates() -> str:
    c = load("candidates.json")["candidates"]
    ks = list(c)
    head = "| quantity (label) | " + " | ".join(ks) + " |\n|---|" + "---|" * len(ks) + "\n"
    rows = []

    def row(label, fn):
        rows.append(f"| {label} | " + " | ".join(fn(c[k]) for k in ks) + " |")
    row("usable radius / stop (mm) (PD)", lambda x: f"{x['design']['reach_mm']:.2f} / {x['design']['stop_mm']:.2f}")
    row("body OD / length (mm) (PD / CALC)", lambda x: f"{x['design']['od_mm']:.1f} / {x['design']['length_mm']:.1f}")
    row("poles w x t_m (mm), grade, layout (PD)",
        lambda x: f"{x['design']['magnets_mm']['w']:.2f} x {x['design']['magnets_mm']['t_m']:.2f}, {x['design']['grade']}, "
                  f"{'double' if x['design']['magnets_mm']['double'] else 'single + keeper'}"
                  + (f" ({x['design']['magnets_mm']['t_m2']:.2f})" if x['design']['magnets_mm']['double'] else ""))
    row("iron, plate thickness (mm) (PD / CALC)", lambda x: f"{x['design']['iron']}, {x['design']['plate_t_mm']:.2f}")
    row("winding: copper stack (mm), order, fill, bundle (mm) (PD)",
        lambda x: f"{x['design']['magnets_mm']['t_cu']:.2f}, {x['design']['coil_mm']['order']}, {x['design']['coil_mm']['k_fill']:.2f}, "
                  f"{x['design']['coil_mm']['b']:.2f}")
    row("coil resistance per axis (ohm) (PD)", lambda x: f(x["design"]["R_coil_ohm"], 2))
    row("wires n x d x L (mm), anchor (N/m) (PD)",
        lambda x: f"{x['design']['wires']['n']} x {x['design']['wires']['d_mm']:.2f} x {x['design']['wires']['L_mm']:.1f}, "
                  f"{x['design']['wires']['anchor_N_m']:.0f}")
    row("guide: ball circle (mm), balls, preload per race (N), rear race (PD)",
        lambda x: f"{x['design']['guide']['circle_r_mm']:.2f}, {x['design']['guide']['n_balls']} x {x['design']['guide']['ball_d_mm']:.1f} mm, "
                  f"{x['design']['guide']['preload_per_race_N']:.2f}, {x['design']['guide']['rear_race']}")
    row("carrier / flange (PD)", lambda x: f"{x['design']['carrier_mat']} / {x['design']['flange_mat']} r {x['design']['guide']['flange_r_mm']:.2f} x {x['design']['flange_t_mm']:.2f} mm")
    row("moving mass (g) (CALC)", lambda x: f(x["design"]["m_move_g"], 2))
    row("K_m centre x / y; weakest over the disk (N/sqrt W, upper bound) (CALC)",
        lambda x: f"{x['evaluation']['magnetics']['Km_centre_x_N_sqrtW']:.3f} / {x['evaluation']['magnetics']['Km_centre_y_N_sqrtW']:.3f}; "
                  f"{x['evaluation']['magnetics']['sv_min_workspace_N_sqrtW']:.3f}")
    row("**duty A mean, weakest x 0.7 (mW)** (CALC)", lambda x: "**" + mw(x["evaluation"]["dutyA"]["worst07"]["mean"]) + "**")
    row("duty A mean, centre x 1.0 (mW) (CALC)", lambda x: mw(x["evaluation"]["dutyA"]["centre10"]["mean"]))
    row("severe duty at 35 deg, weakest x 0.7 (mW) (CALC)", lambda x: mw(x["evaluation"]["severe"]["worst07"]["P35_W"]))
    row("**worst-case screen, weakest x 0.7 (W)** (CALC)", lambda x: "**" + f(x["evaluation"]["screen"]["worst07"], 3) + "**")
    row("skin, hottest point, severe at 35 deg (degC) (CALC)",
        lambda x: f(x["evaluation"]["severe"]["worst07"]["skin"]["max_shell_C"], 1))
    row("Goodman worst corner / Hertz sustained (GPa) (CALC)",
        lambda x: f"{x['evaluation']['wires']['goodman_worst_corner']:.2f} / {x['evaluation']['guide']['hertz_run_GPa']:.2f}")
    row("servo bandwidth allowed (Hz) / coil clearance p99 (mm) (CALC)",
        lambda x: f"{x['evaluation']['modes']['servo_bw_max_worst_Hz']:.1f} / {x['evaluation']['fit']['coil_clearance_p99_mm']:.2f}")
    row("voltage at the peak force (V; <= 3.3) (CALC)", lambda x: f(x["evaluation"]["electrical"]["V_peak_V"], 2))
    row("study F at this reach: tip residual, estimator at +2 / perfect knowledge (mm) (SIM)",
        lambda x: f"{x['evaluation']['severe_motion']['F_a_r2_tip_mm']:.2f} / {x['evaluation']['severe_motion']['F_oracle_tip_mm']:.2f}")
    row("all constraints met (CALC)", lambda x: f(x["evaluation"]["constraints"]["feasible"]))
    return head + "\n".join(rows) + "\n"


def levers() -> str:
    lv = load("levers.json")["studies"]
    s = ""
    for name, st in lv.items():
        s += f"Around '{name}' (base: typical {st['base']['typical_W'] * 1e3:.1f} mW, screen {st['base']['screen_W']:.3f} W, "
        s += f"skin {st['base']['skin_C']:.1f} degC)\n\n| lever | typical (mW) | change | screen (W) | skin (degC) |\n|---|---|---|---|---|\n"
        for r in sorted(st["rows"], key=lambda r: -abs(r["d_typical_pct"])):
            s += (f"| {r['lever']} | {r['typical_W'] * 1e3:.1f} | {r['d_typical_pct']:+.0f} % | {r['screen_W']:.3f} | "
                  f"{r['skin_C']:.1f} |\n")
    return s


def budgets() -> str:
    b = load("budgets.json")["budgets"]
    ks = list(b)
    head = "| quantity (CALC) | " + " | ".join(ks) + " |\n|---|" + "---|" * len(ks) + "\n"
    rows = []

    def row(label, fn):
        rows.append(f"| {label} | " + " | ".join(fn(b[k]) for k in ks) + " |")
    row("pen mass (g) / balance point from the tip (mm)", lambda x: f"{x['mass']['mass_g']:.1f} / {x['mass']['com_mm']:.1f}")
    row("moving mass (g)", lambda x: f(x["mass"]["moving_g"], 2))
    row("length / OD (mm)", lambda x: f"{x['length_mm']:.1f} / {x['od_mm']:.1f}")
    for mode in ("steady_0mm", "steady_1mm", "steady_2mm", "guide", "spelling_cue", "severe"):
        row(f"hours, {mode}: conservative - optimistic",
            lambda x, m=mode: f"{x['battery_hours']['conservative'][m]:.1f} - {x['battery_hours']['optimistic'][m]:.1f}")
    row("skin at 35 deg, steady 1 mm, weakest x 0.7: front pad / hottest (degC)",
        lambda x: f"{x['skin_by_mode']['worst07']['steady_1mm']['front_pad_C']:.1f} / {x['skin_by_mode']['worst07']['steady_1mm']['max_shell_C']:.1f}")
    row("skin at 35 deg, severe, weakest x 0.7: front pad / hottest (degC)",
        lambda x: f"{x['skin_by_mode']['worst07']['severe']['front_pad_C']:.1f} / {x['skin_by_mode']['worst07']['severe']['max_shell_C']:.1f}")
    return head + "\n".join(rows) + "\n"


def main():
    parts = [("Reconciliation", reconciliation), ("Waterfall K", waterfall_K), ("Waterfall pass 1.5", waterfall_pass),
             ("Waterfall pass K", lambda: waterfall_pass("K_B1")), ("Pass summary", pass_summary),
             ("Topologies", topologies), ("Pareto", pareto), ("Candidates", candidates), ("Levers", levers),
             ("Budgets", budgets)]
    for title, fn in parts:
        try:
            sys.stdout.write(f"\n## {title}\n\n{fn()}\n")
        except FileNotFoundError as e:
            sys.stdout.write(f"\n## {title}\n\n(missing: {e})\n")


if __name__ == "__main__":
    main()
