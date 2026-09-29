"""Markdown tables for docs/real_tracker.md generated from results/realtrack/realtrack.json (no hand transcription).
python3 -m realtrack.doc  ->  realtrack/build/doc_tables.md"""
from __future__ import annotations

import json
from typing import Dict, List

import numpy as np

from . import BUILD_DIR, RESULTS_DIR

DEV = [("none", "Ordinary pen"), ("revJ_gated|deltapen", "Rev J gated (R)"), ("revJ_g4|deltapen", "Rev J + G4"),
       ("revJ_new|deltapen", "Rev J + best causal"), ("revJ_oracle", "Perfect knowledge")]


def f(x, nd=1):
    try:
        x = float(x)
        return "-" if not np.isfinite(x) else f"{x:.{nd}f}"
    except Exception:
        return "-"


def ci(v, nd=1):
    if not v or not np.isfinite(v.get("mean", np.nan)):
        return "-"
    return f"{f(v['mean'], nd)} ({f(v['lo'], nd)}-{f(v['hi'], nd)})"


def one_number(out: Dict) -> str:
    rows = out["test"]["one_number_table"]
    L = ["| Tremor (size at the pen tip) | No tremor (same notes) | Ordinary pen | Best causal tracker (this study) | "
         "Perfect knowledge |", "|---|---|---|---|---|"]
    for r in rows:
        if r["kind"] == "all" and r["class"] != "severe":
            continue
        lab = f"{r['label']}, {r['class']} ({r['amp_mm']:.2f} mm)"
        L.append(f"| {lab} | {f((r.get('ceiling') or {}).get('mean'))} | {f((r.get('ordinary') or {}).get('mean'))} | "
                 f"{f((r.get('best_causal') or {}).get('mean'))} | {f((r.get('perfect') or {}).get('mean'))} |")
    return "\n".join(L)


def cards(out: Dict) -> str:
    ag = out["test"]["cards"]
    L = []
    kinds = {"PD": "Parkinson's", "ET": "Essential tremor", "all": "PD and ET pooled"}
    for kind in ("all", "PD", "ET"):
        for cls in ("severe", "moderate", "mild"):
            cd = ag["real"].get(f"{kind}/{cls}")
            if not cd:
                continue
            L.append(f"**{kinds[kind]}, {cls} class: {cd['_amp_mm_mean']:.2f} mm at the tip, about {cd['_f0_mean']:.1f} Hz** "
                     f"({cd['_n_writers']} test writers, {cd['_n_cases']} notes; 95 % intervals over writers)\n")
            L.append("| | " + " | ".join(n for _, n in DEV) + " |")
            L.append("|---" * (len(DEV) + 1) + "|")
            L.append("| Readable words out of 10 | " + " | ".join(ci((cd.get(d) or {}).get("words_of_10")) for d, _ in DEV) + " |")
            L.append("| ... gain over the ordinary pen | - | " + " | ".join(
                ci((cd.get(d) or {}).get("words_of_10_gain")) for d, _ in DEV[1:]) + " |")
            L.append("| Tremor left at the tip, mm | " + " | ".join(ci((cd.get(d) or {}).get("tip_tremor_mm"), 2) for d, _ in DEV) + " |")
            row = ["1 (reference)"]
            for d, _ in DEV[1:]:
                v = (cd.get(d) or {}).get("tip_tremor_ratio")
                if v and np.isfinite(v.get("mean", np.nan)):
                    pw = 100 * (1 - v["mean"] ** 2)
                    row.append(f"{f(v['mean'], 2)} (power {'-' if pw >= 0 else '+'}{abs(pw):.0f} %)")
                else:
                    row.append("-")
            L.append("| ... share of the ordinary pen's (amplitude) | " + " | ".join(row) + " |")
            fc = out["test"]["cards"]["clean"]["clean_real"]
            L.append("| Clean writing moved, um | 0 (reference) | " + " | ".join(
                ci((fc.get(d) or {}).get("false_correction_um")) for d, _ in DEV[1:4]) + " | - |")
            L.append("| Readable words without tremor | " + " | ".join(
                f((fc.get(d) or {}).get("words_of_10", {}).get("mean")) for d, _ in DEV[:4]) + " | - |")
            held = (cd.get("revJ_held") or {}).get("tip_tremor_ratio")
            ide = (cd.get("revJ_new") or {}).get("tip_tremor_ratio")
            L.append(f"\nRev J with the nose held (no tracker): tip tremor {ci(held, 2)} x the ordinary pen's. "
                     f"Best causal tracker with the ideal page sensor (bound): {ci(ide, 2)} x.\n")
    return "\n".join(L)


def tuning(out: Dict) -> str:
    t = out["tuning"]
    L = ["| Family (literature) | Severe tremor left, tip (x ordinary pen) | Broadband residual (x nose held) | Clean writing "
         "moved, um | Passes T2-T4 |", "|---|---|---|---|---|"]
    names = {"akf": "AKF, listening form (the Rev H tracker's model)", "wflc": "WFLC (ACT-08)",
             "bmflc": "BMFLC, LMS weights (ACT-09/10)", "bmflc_kf": "BMFLC with Kalman weights (ACT-09)",
             "epll": "EPLL / adaptive oscillator (ACT-140/142)"}
    for fam, v in t["stage1"].items():
        L.append(f"| {names.get(fam, fam)}: raw, no gate | {f(v['severe_ratio'], 2)} | {f(v['J_severe_bb'], 2)} | "
                 f"(ungated) | no |")
    for fam, v in t["stage2_amplitude_only"].items():
        s = v["summary"]
        L.append(f"| {names.get(fam, fam)} + amplitude authority | {f(s['severe_ratio'], 2)} | {f(s['severe_bb'], 2)} | "
                 f"{f(s['clean_um_mean'])} (max {f(s['clean_um_max'])}) | {'yes' if v['passes']['all'] else 'no'} |")
    for key, lab in (("binary_gate", "ai2's listening estimate + retuned binary gate"),
                     ("soft_confidence", "ai2's listening estimate + soft confidence authority"),
                     ("joint_akf", "AKF + authority tuned jointly"), ("net_authority", "TCN on real data + authority")):
        v = t.get(key)
        if v:
            s = v["summary"]
            L.append(f"| {lab} | {f(s['severe_ratio'], 2)} | {f(s['severe_bb'], 2)} | {f(s['clean_um_mean'])} "
                     f"(max {f(s['clean_um_max'])}) | {'yes' if v['passes']['all'] else 'no'} |")
    return "\n".join(L)


def main():
    out = json.loads((RESULTS_DIR / "realtrack.json").read_text())
    parts = ["## One-number table\n", one_number(out), "\n## Results cards\n", cards(out), "\n## Tuning table\n", tuning(out)]
    (BUILD_DIR / "doc_tables.md").write_text("\n".join(parts) + "\n")
    print(BUILD_DIR / "doc_tables.md")


if __name__ == "__main__":
    main()
