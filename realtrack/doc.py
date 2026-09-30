"""Markdown tables for docs/real_tracker.md generated from results/realtrack/realtrack.json (no hand transcription).
python3 -m realtrack.doc  ->  realtrack/build/doc_tables.md"""
from __future__ import annotations

import json
from typing import Dict, List

import numpy as np

from . import BUILD_DIR, RESULTS_DIR

DEV = [("none", "Ordinary pen"), ("revJ_gated|deltapen", "Rev J gated (R)"), ("revJ_tcn|deltapen", "ai2's TCN, no gate (R)"),
       ("revJ_g4|deltapen", "Rev J + G4"), ("revJ_new|deltapen", "Rev J + best causal"), ("revJ_oracle", "Perfect knowledge")]
INFO = [("revJ_held", "Rev J, nose held (no tracker)"), ("revJ_gated|deltapen", "Rev J gated (R's baseline)"),
        ("revJ_g4|deltapen", "G4, ported (second baseline)"), ("revJ_tcn|deltapen", "ai2's TCN, no gate (R)"),
        ("revJ_new|deltapen", "**Best causal tracker, frozen: ai2's TCN + soft size gate**"),
        ("revJ_new", "... the same with the ideal page sensor (bound)"),
        ("revJ_info_net|deltapen", "Information: TCN trained on real data + soft size gate"),
        ("revJ_info_listen_conf|deltapen", "Information: listening AKF + soft confidence gate"),
        ("revJ_info_glg|deltapen", "Information: GLG (study W), as tuned here"),
        ("revJ_info_ungated_akf|deltapen", "Information: listening AKF, no gate"),
        ("revJ_oracle", "Perfect knowledge (the nose's limit)")]


def f(x, nd=1):
    try:
        x = float(x)
        return "-" if not np.isfinite(x) else f"{x:.{nd}f}"
    except Exception:
        return "-"


def ci(v, nd=1):
    if not v or not np.isfinite(v.get("mean", np.nan)):
        return "-"
    lo, hi = v.get("lo", np.nan), v.get("hi", np.nan)
    sep = " to " if (np.isfinite(lo) and lo < 0) else "-"
    return f"{f(v['mean'], nd)} ({f(lo, nd)}{sep}{f(hi, nd)})"


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
    fc = ag["clean"]["clean_real"]
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
            L.append("| Clean writing moved, um (notes without tremor) | 0 (reference) | " + " | ".join(
                ci((fc.get(d) or {}).get("false_correction_um")) for d, _ in DEV[1:-1]) + " | - |")
            L.append("| Readable words without tremor | " + " | ".join(
                f((fc.get(d) or {}).get("words_of_10", {}).get("mean")) for d, _ in DEV[:-1]) + " | - |")
            held = (cd.get("revJ_held") or {}).get("tip_tremor_ratio")
            ide = (cd.get("revJ_new") or {}).get("tip_tremor_ratio")
            L.append(f"\nRev J with the nose held (no tracker): tip tremor {ci(held, 2)} x the ordinary pen's. "
                     f"Best causal tracker with the ideal page sensor (bound): {ci(ide, 2)} x.\n")
    return "\n".join(L)


def dec055(out: Dict) -> str:
    d = out["test"]["dec055"]
    names = {"chosen": "Best causal tracker (frozen: ai2's TCN + soft size gate)", "g4": "G4, ported (sim2j)",
             "R_gated": "Rev J gated (R)", "R_tcn": "ai2's TCN, no gate (R)"}
    L = ["| Design | Words gained over the ordinary pen, severe, PD and ET pooled (95 % interval) | Clean writing moved, "
         "um: mean over writers (worst writer) | Words line (>= 2, interval above 0) | Clean line (<= 25 um mean, no writer "
         "above 50 um) | DEC-055 |", "|---|---|---|---|---|---|"]
    for k, lab in names.items():
        v = d.get(k) or {}
        if not v.get("evaluated"):
            L.append(f"| {lab} | not read | | | | not evaluated |")
            continue
        g = {"mean": v.get("words_gain_mean"), "lo": v.get("words_gain_lo"), "hi": v.get("words_gain_hi")}
        L.append(f"| {lab} | {ci(g, 2)} | {f(v.get('clean_change_um_mean'))} ({f(v.get('clean_change_um_worst_writer'))}) | "
                 f"{'met' if v['passes_words'] else 'not met'} | {'met' if v['passes_clean'] else 'not met'} | "
                 f"**{'passed' if v['passes'] else 'not passed'}** |")
    return "\n".join(L)


def info(out: Dict) -> str:
    """Every pen on one line: tip tremor as a share of the ordinary pen's per class (PD and ET pooled), clean-writing
    change (mean and the worst writer), words where read."""
    ag = out["test"]["cards"]
    fc = ag["clean"]["clean_real"]
    per = out["test"].get("per_note") or []
    L = ["| Pen | Severe: tip tremor (x ordinary pen) | Moderate | Mild | Clean writing moved, um: mean (worst writer) | "
         "Words of 10, severe | Words of 10, no tremor |", "|---|---|---|---|---|---|---|"]
    for dev, lab in INFO:
        r = []
        for cls in ("severe", "moderate", "mild"):
            v = ((ag["real"].get(f"all/{cls}") or {}).get(dev) or {}).get("tip_tremor_ratio")
            r.append(ci(v, 2) if v else "-")
        cm = (fc.get(dev) or {}).get("false_correction_um")
        worst = [((p.get("clean") or {}).get(dev) or {}).get("false_correction_um") for p in per]
        worst = [x for x in worst if x is not None and np.isfinite(x)]
        cl = "-" if not cm or not np.isfinite(cm.get("mean", np.nan)) else \
            f"{f(cm['mean'])} ({f(max(worst)) if worst else '-'})"
        if dev in ("revJ_held", "revJ_oracle"):
            cl = "0 (reference)" if dev == "revJ_held" else "-"
        ws = ((ag["real"].get("all/severe") or {}).get(dev) or {}).get("words_of_10")
        wc = (fc.get(dev) or {}).get("words_of_10")
        L.append(f"| {lab} | " + " | ".join(r) + f" | {cl} | {ci(ws)} | {ci(wc)} |")
    return "\n".join(L)


def per_writer(out: Dict) -> str:
    per = out["test"].get("per_note") or []
    devs = [("revJ_gated|deltapen", "Rev J gated (R)"), ("revJ_tcn|deltapen", "ai2's TCN, no gate (R)"),
            ("revJ_g4|deltapen", "G4"), ("revJ_new|deltapen", "Best causal (frozen)"),
            ("revJ_info_net|deltapen", "TCN on real data (info)"), ("revJ_info_listen_conf|deltapen", "Listening + soft gate (info)"),
            ("revJ_info_glg|deltapen", "GLG (info)"), ("revJ_info_ungated_akf|deltapen", "Listening AKF, no gate (info)")]
    L = ["| Test note (UNIPEN writer) | " + " | ".join(n for _, n in devs) + " |", "|---" * (len(devs) + 1) + "|"]
    for p in per:
        c = p.get("clean") or {}
        L.append(f"| {p['note']} ({p['writer']}) | " + " | ".join(
            f((c.get(d) or {}).get("false_correction_um"), 0) for d, _ in devs) + " |")
    return "\n".join(L)


def per_writer_severe(out: Dict) -> str:
    per = out["test"].get("per_note") or []
    devs = [("none", "Ordinary pen"), ("revJ_held", "Nose held"), ("revJ_new|deltapen", "Best causal (frozen)"),
            ("revJ_info_net|deltapen", "TCN on real data (info)"), ("revJ_oracle", "Perfect knowledge")]
    L = ["| Test note | Tremor | " + " | ".join(n for _, n in devs) + " |", "|---" * (len(devs) + 2) + "|"]
    for p in per:
        for kind in ("PD", "ET"):
            t = (p.get("tremor") or {}).get(f"{kind}/severe") or {}
            L.append(f"| {p['note']} | {kind} | " + " | ".join(
                f((t.get(d) or {}).get("tip_tremor_mm"), 2) for d, _ in devs) + " |")
    return "\n".join(L)


def tuning(out: Dict) -> str:
    t = out["tuning"]
    ln = out.get("learned") or {}
    rc = out.get("raw_clean") or {}
    L = ["| Design (literature) | Severe tremor left at the tip (x ordinary pen) | Broadband residual, severe (x nose held) | "
         "Clean writing moved, um: mean (worst note) | Passes T2-T4 |", "|---|---|---|---|---|"]
    names = {"akf": "AKF, listening form (the Rev H tracker's model)", "wflc": "WFLC (ACT-08)",
             "bmflc": "BMFLC, LMS weights (ACT-09/10)", "bmflc_kf": "BMFLC with Kalman weights (ACT-09)",
             "epll": "EPLL / adaptive oscillator (ACT-140/142)"}

    def row(lab, s, ok):
        return (f"| {lab} | {f(s.get('severe_ratio'), 2)} | {f(s.get('severe_bb'), 2)} | "
                f"{f(s.get('clean_um_mean'), 0)} ({f(s.get('clean_um_max'), 0)}) | {ok} |")
    for fam, v in t["stage1"].items():
        c = (rc.get(fam) or {})
        cl = f"{f(c.get('clean_um_mean'), 0)} ({f(c.get('clean_um_max'), 0)})" if c else "not measured"
        L.append(f"| {names.get(fam, fam)}: tuned for capture, no gate | {f(v['severe_ratio'], 2)} | {f(v['J_severe_bb'], 2)} | "
                 f"{cl} | no |")
    if ln.get("fir_raw"):
        L.append(row("Linear FIR on the accelerometer, least squares, cross-fitted (the best fixed filter)", ln["fir_raw"], "no"))
    for fam, v in t["stage2_amplitude_only"].items():
        L.append(row(f"{names.get(fam, fam)} + size gate (best setting)", v["summary"], "yes" if v["passes"]["all"] else "no"))
    bg = t.get("binary_gate")
    if bg:
        L.append(row("ai2's listening estimate + binary gate, R's setting (Rev H fallback)", bg["R_setting"],
                     "yes" if (bg.get("R_setting_passes") or {}).get("all") else "no"))
        L.append(row("ai2's listening estimate + binary gate, retuned", bg["summary"], "yes" if bg["passes"]["all"] else "no"))
    g = t.get("glg")
    if g:
        L.append(row("GLG (study W): as W froze it", g["as_frozen_by_W"]["summary"], "yes" if g["as_frozen_by_W"]["passes"]["all"] else "no"))
        L.append(row("GLG (study W): retuned here", g["retuned"]["summary"], "yes" if g["retuned"]["passes"]["all"] else "no"))
    for key, lab in (("joint_akf", "AKF + soft size gate, tuned jointly"),
                     ("soft_confidence", "ai2's listening estimate + soft confidence gate (best classical)")):
        v = t.get(key)
        if v:
            L.append(row(lab, v["summary"], "yes" if v["passes"]["all"] else "no"))
    for key, lab in (("net_authority", "TCN trained here on real data (17 k parameters)"),
                     ("ai2tcn_authority", "ai2's TCN (34 k parameters, synthetic writers)")):
        v = t.get(key)
        if v:
            L.append(row(f"{lab}: no gate", v["raw"], "no"))
            L.append(row(f"{lab} + soft size gate", v["summary"], "yes" if v["passes"]["all"] else "no"))
    return "\n".join(L)


def finalists(out: Dict) -> str:
    fz = out.get("frozen") or {}
    tp = fz.get("tuning_full_plant") or {}
    lab = {"ai2tcn": "ai2's TCN + soft size gate", "net": "TCN trained on real data + soft size gate",
           "listen_conf": "listening AKF + soft confidence gate", "joint_akf": "AKF + soft size gate (joint)",
           "gate_listen": "listening AKF + retuned binary gate", "glg": "GLG"}
    L = ["| Finalist (full HW1 plant, tuning split) | Objective T1 | Severe tip tremor (x ordinary): PD / ET | "
         "Moderate / mild (x nose held) | Clean writing moved, um: mean (worst note) | Passes | Chosen |",
         "|---|---|---|---|---|---|---|"]
    for k, v in tp.items():
        s = v["summary"]
        L.append(f"| {lab.get(k, k)} | {f(v.get('J'), 3)} | {f(s.get('severe_PD_ratio'), 2)} / {f(s.get('severe_ET_ratio'), 2)} | "
                 f"{f(s.get('moderate_rheld'), 3)} / {f(s.get('mild_rheld'), 3)} | {f(s.get('clean_um_mean'))} "
                 f"({f(s.get('clean_um_max'))}) | {'yes' if (v.get('passes') or {}).get('all') else 'no'} | "
                 f"{'**yes**' if k == fz.get('chosen_name') else ''} |")
    return "\n".join(L)


def mcu(out: Dict) -> str:
    m = out.get("mcu") or {}
    rows = []

    def add(lab, parts):
        parts = [p for p in parts if p]
        if not parts:
            return
        mac = sum(p["mac_per_1ms_step"] for p in parts)
        cpu = sum(p["cpu_share_128MHz"] for p in parts)
        ram = sum(p["ram_bytes"] for p in parts)
        fl = sum(p.get("flash_bytes", 0) for p in parts)
        rows.append(f"| {lab} | {mac:,.0f} | {100 * cpu:.1f} % | {ram / 1024:.1f} kB ({100 * ram / 262144:.1f} %) | "
                    f"{fl / 1024:.1f} kB |")
    add("**Best causal tracker, frozen: ai2's TCN (int8) + soft size gate**", [m.get("ai2_tcn"), m.get("authority")])
    add("TCN trained on real data (int8) + soft size gate", [m.get("tcn_real_data"), m.get("authority")])
    add("Listening AKF + ai2's detector + soft confidence gate", [m.get("akf"), m.get("detector"), m.get("authority")])
    g4 = m.get("g4") or {}
    add("G4 (Rev H AKF + guard + ai2's detector)", [g4.get("akf"), g4.get("detector")])
    add("AKF alone (the Rev H tracker's model)", [m.get("akf")])
    add("EPLL, fundamental + 2nd harmonic", [m.get("epll")])
    add("WFLC, fundamental + harmonic", [m.get("wflc")])
    add("BMFLC, 19 frequencies (LMS)", [m.get("bmflc_19")])
    add("BMFLC-KF, 19 frequencies", [m.get("bmflc_kf_19")])
    add("BMFLC-KF, 37 frequencies", [m.get("bmflc_kf_37")])
    add("Linear FIR, 128 taps, polyphase", [m.get("fir_128")])
    L = ["| Design | Multiply-accumulates per 1 ms | Share of a 128 MHz Cortex-M33 | RAM (share of the nRF54L15's 256 KB) "
         "| Weights and constants (flash) |", "|---|---|---|---|---|"] + rows
    return "\n".join(L)


def delay(out: Dict) -> str:
    dl = out.get("delay") or {}
    hz = dl.get("horizon") or {}
    if not hz:
        return "(delay analysis missing)"
    labs = list(hz.keys())
    offs = hz[labs[0]]["offsets_ms"]
    L = ["| Prediction beyond the servo delay, ms | " + " | ".join(f"{o:+g}" for o in offs) + " |",
         "|---" * (len(offs) + 1) + "|"]
    for lab in labs:
        by = hz[lab]["by_offset"]
        L.append(f"| {lab}: severe tip tremor (x ordinary pen) | " + " | ".join(
            f((by.get(str(o)) or {}).get("severe_ratio"), 3) for o in offs) + " |")
        L.append(f"| {lab}: mild tip tremor (x nose held) | " + " | ".join(
            f((by.get(str(o)) or {}).get("mild_rheld"), 3) for o in offs) + " |")
    return "\n".join(L)


def sim2(out: Dict) -> str:
    s = out.get("sim2") or {}
    rows = s.get("rows") or []
    if not rows:
        return "(sim2 check missing)"
    L = ["| ET cell (f0, size) | Ink error, device off, um | G4 (sim2j) | ai2's TCN (sim2j) | Best causal (frozen) | "
         "Perfect knowledge (sim2j) | Words readable (device off / G4 / frozen / perfect) |", "|---|---|---|---|---|---|---|"]
    clean = None
    for r in rows:
        if not r.get("amp_mm"):
            clean = r
            continue
        L.append(f"| {r['f0']:g} Hz, {r['amp_mm']:g} mm | "
                 f"{f(r.get('none_ink_err_um_sim2j'), 0)} | {f(r.get('nose_ratio'), 2)} | {f(r.get('tcn_ratio'), 2)} | "
                 f"{f(r.get('new_ratio'), 2)} | {f(r.get('oracle_ratio'), 2)} | {r.get('none_words_app', '-')} / "
                 f"{r.get('nose_words_app', '-')} / {r.get('new_words_app', '-')} / {r.get('oracle_words_app', '-')} |")
    if clean:
        L.append(f"\nNo tremor (same writer and seed): writing moved {f(clean.get('nose_moved_um'))} um by G4, "
                 f"{f(clean.get('tcn_moved_um'))} um by ai2's TCN (no gate), {f(clean.get('new_moved_um'))} um by the frozen "
                 f"design; words readable: G4 {clean.get('nose_words_app', '-')}, frozen {clean.get('new_words_app', '-')}.")
    return "\n".join(L)


def main():
    out = json.loads((RESULTS_DIR / "realtrack.json").read_text())
    parts = ["## One-number table\n", one_number(out), "\n## DEC-055\n", dec055(out), "\n## Every pen\n", info(out),
             "\n## Clean writing per writer\n", per_writer(out), "\n## Severe tip tremor per note, mm\n", per_writer_severe(out),
             "\n## Results cards\n", cards(out), "\n## Tuning table\n", tuning(out), "\n## Finalists\n", finalists(out),
             "\n## MCU\n", mcu(out), "\n## Delay\n", delay(out), "\n## sim2\n", sim2(out)]
    (BUILD_DIR / "doc_tables.md").write_text("\n".join(parts) + "\n")
    print(BUILD_DIR / "doc_tables.md")


if __name__ == "__main__":
    main()
