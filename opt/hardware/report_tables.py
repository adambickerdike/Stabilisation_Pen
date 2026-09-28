"""Markdown tables for docs/opt_hardware.md, generated from results/opt/hardware.json (so the report's numbers
are transcribed by code).   python3 -m opt.hardware.report_tables > /tmp/tables.md"""
from __future__ import annotations

import json
import os

from . import OUT


def _f(v, fmt="{:.0f}"):
    try:
        return fmt.format(v)
    except (TypeError, ValueError):
        return str(v)


def tables(res=None):
    res = res or json.load(open(os.path.join(OUT, "hardware.json")))
    out = []
    rec = res["recommended"]
    cur = res["model_checks"]["current_design"]
    alts = res.get("alternatives", [])

    def row(name, key, fmt="{:.0f}", scale=1.0):
        vals = [cur.get(key)] + [rec.get(key)] + [a.get(key) for a in alts]
        return "| " + name + " | " + " | ".join(_f(v * scale if isinstance(v, (int, float)) else v, fmt) for v in vals) + " |"
    hdr = "| Quantity | P0.1.2 current | **P0.2 recommended** | " + " | ".join(a.get("stage_key", "alt.") for a in alts) + " |"
    out.append("### Design comparison (CALC unless marked)\n")
    out.append(hdr)
    out.append("|" + "---|" * (3 + len(alts)))
    x0, x1 = cur["x"], rec["x"]
    xs = [x0, x1] + [a["x"] for a in alts]
    for nm, k, sc, fmt in (("plate width (mm)", "w", 1e3, "{:.2f}"), ("plate thickness (mm)", "t", 1e3, "{:.2f}"),
                           ("free length (mm)", "Lf", 1e3, "{:.1f}"), ("clamp length (mm)", "Lc", 1e3, "{:.1f}"),
                           ("plate offset from axis (mm)", "d", 1e3, "{:.2f}"), ("gimbal z (mm)", "zg", 1e3, "{:.1f}"),
                           ("collar front z (mm)", "zc0", 1e3, "{:.1f}"), ("leaf thickness (um)", "leaf_t", 1e6, "{:.0f}"),
                           ("leaf width (mm)", "leaf_w", 1e3, "{:.2f}"), ("leaf span (mm)", "leaf_L", 1e3, "{:.2f}"),
                           ("skid ring radius (mm)", "r_ring", 1e3, "{:.2f}"), ("drive range (V)", "V", 1.0, "{:.0f}"),
                           ("stop travel at the nib (mm)", "q_stop", 1e3, "{:.2f}"), ("cell length (mm)", "L_cell", 1e3, "{:.1f}")):
        out.append(f"| {nm} | " + " | ".join(_f(x[k] * sc, fmt) for x in xs) + " |")
    out.append(row("lever (nib per collar)", "lever", "{:.3f}"))
    out.append(row("**worst-case usable stroke (um)** (-20 %, 35 deg, mu 0.15, worst direction)", "usable_wc_um"))
    out.append(row("worst-case loaded stroke, raw (um)", "q_wc_um"))
    out.append(row("worst case at mu 0.35 (um)", "q_wc_mu035_um"))
    out.append(row("nominal loaded stroke (um) (50 deg, mu 0.15)", "q_nom_um"))
    out.append(row("nominal at -20 % tolerance (um)", "q_nom_tol_um"))
    out.append(row("servo soft limit (um)", "q_lim_um"))
    out.append(row("blocking force at the nib (N)", "F_b_nib_N", "{:.3f}"))
    out.append(row("free stroke at the nib (um)", "free_stroke_nib_um"))
    out.append(row("first resonance (Hz)", "f1_Hz"))
    out.append(row("driven capacitance per axis, small signal (uF)", "C_axis_uF", "{:.2f}"))
    out.append(row("pen mass incl. 10 % (g)", "mass_with_margin_g", "{:.1f}"))
    out.append(row("plate clamp stress, driven onto a stop (MPa)", "sig_stop_MPa", "{:.0f}"))
    out.append(row("drop stress 2 ms, surrogate + 1 sd (MPa)", "sig_drop_2ms_MPa", "{:.0f}"))
    out.append(row("allowable at P_fail 1e-4 (MPa)", "sig_allow_MPa", "{:.0f}"))
    out.append(row("leaf buckling safety factor", "leaf_sf", "{:.2f}"))
    out.append(row("nib travel the spring must take (mm)", "protrusion_travel_mm", "{:.2f}"))
    out.append(row("Hall noise at the nib (um rms)", "sigma_nib_um", "{:.2f}"))
    out.append(row("assist power, mean of 0.3 mm cases (mW)", "P_total_mean_mW"))
    out.append(row("assist life, worst 0.3 mm case (h)", "life_assist_h", "{:.2f}"))
    out.append(row("recording life (h)", "life_recording_h", "{:.1f}"))
    out.append("")
    # BOM
    out.append("### BOM (P0.2)\n")
    out.append("| Part | Source | Status | Key specification | Ledger |")
    out.append("|---|---|---|---|---|")
    for b in rec["bom"]:
        out.append(f"| {b['part']} | {b['source']} | {b['status']} | {b['key_spec']} | {b['ledger']} |")
    out.append("")
    # P1
    p1 = res.get("p1_validation", {})
    if p1:
        out.append("### P1 validation (SIM, seeds 200-203, oracle)\n")
        keys = [k for k in ["Q26", "P02"] + [a["stage_key"] for a in alts] if k in p1]
        out.append("| Case | " + " | ".join(f"{k} ratio / at limit / rail rec. mW" for k in keys) + " |")
        out.append("|---|" + "---|" * len(keys))
        cases = list(p1[keys[0]]["grid"].keys())
        for c in cases:
            out.append(f"| {c} | " + " | ".join(
                f"{p1[k]['grid'][c]['oracle_ratio']:.2f} / {p1[k]['grid'][c]['time_at_limit']:.2f} / "
                f"{p1[k]['grid'][c]['P_rail_recovery_mW']:.1f}" for k in keys) + " |")
        out.append("| **mean** | " + " | ".join(f"{p1[k]['mean_oracle_ratio']:.3f} / {p1[k]['mean_time_at_limit']:.2f} / -"
                                               for k in keys) + " |")
        out.append("")
        out.append("| 35 deg, -20 %, 0.3 mm | " + " | ".join(f"{k}" for k in keys) + " |")
        out.append("|---|" + "---|" * len(keys))
        for c in p1[keys[0]]["worst_case"]:
            out.append(f"| {c} | " + " | ".join(f"{p1[k]['worst_case'][c]['oracle_ratio']:.2f} "
                                               f"({p1[k]['worst_case'][c]['time_at_limit']:.2f})" for k in keys) + " |")
        out.append("")
    # selection among the finalists
    sel = res.get("selection")
    if sel:
        out.append("### Finalists ranked by P1 (SIM) and the design model (CALC)\n")
        out.append("| Candidate | P1 worst case (35 deg, -20 %, 0.3 mm) | P1 grid mean | P1 time at limit | "
                   "static worst case (um) | nominal (um) | k at the nib (N/m) | f1 (Hz) | skid ring (mm) | life (h) |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for d in sorted(sel["rows"], key=lambda d: d["p1_worstcase_ratio"]):
            mark = " **(selected)**" if d["key"] == sel["selected"] else ""
            out.append(f"| {d['key']}{mark}: {d['label'].split(': ', 1)[-1]} | {d['p1_worstcase_ratio']:.3f} | "
                       f"{d['p1_grid_ratio']:.3f} | {d['p1_time_at_limit']:.2f} | {d['usable_wc_um']:.0f} | "
                       f"{d['q_nom_um']:.0f} | {d['k_tot_nib']:.0f} | {d['f1_Hz']:.0f} | {d['skid_ring_mm']:.2f} | "
                       f"{(d.get('life_assist_h') or float('nan')):.2f} |")
        out.append("")
    # catalogue
    out.append("### Catalogue of parts found (status, source)\n")
    out.append("| Category | Part | Status | Key specification | Price seen | Ledger | Role / verdict |")
    out.append("|---|---|---|---|---|---|---|")
    for p in res["catalogue"]:
        out.append(f"| {p['category']} | {p['part']} | {p['status']} | {p['key_spec']} | {p.get('price') or '-'} | "
                   f"{p.get('ledger') or '-'} | {p['role']} |")
    out.append("")
    # enumeration
    out.append("### Enumeration (best of each discrete combination, CALC)\n")
    out.append("| Combination | feasible | worst-case usable (um) | nominal loaded (um) | mass (g) | power (mW) | life (h) |")
    out.append("|---|---|---|---|---|---|---|")
    for r in sorted(res["enumeration"], key=lambda r: -r["usable_wc_um"] if r["feasible"] else 1e9):
        out.append(f"| {r['key']} | {'yes' if r['feasible'] else 'no'} | {r['usable_wc_um']:.0f} | {r['q_nom_um']:.0f} | "
                   f"{r['mass_with_margin_g']:.1f} | {r.get('P_total_mean_mW', float('nan')):.0f} | "
                   f"{r.get('life_assist_h', float('nan')):.2f} |")
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    print(tables())
