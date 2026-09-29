r"""Writes docs/whole_pen_shift.md from wholepen/doc_template.md and the result files: the generated tables between
<!-- W:name --> and <!-- /W:name --> markers, the «class|design|key|decimals» values from summary.json's headline and
the «NAME» values computed in named_values(), so every result number in the text comes from results/wholepen/*.json.
Usage: python3 -m wholepen.report   (edit the template, not the document)
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Dict

from . import DOC, RESULTS
from . import run_study as RS
from . import summary as SM


def _load(n):
    p = os.path.join(RESULTS, n)
    return json.load(open(p)) if os.path.exists(p) else None


def _fmt(v, f="{:.1f}"):
    return "–" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f.format(v)


def blocks() -> Dict[str, str]:
    s = _load("summary.json") or {}
    out = {}
    head = s.get("headline")
    if head:
        out["table_tip"] = SM.table_md(head, "tip_mm", "{:.1f}")
        out["table_words"] = SM.table_md(head, "words10", "{:.0f}")
        out["table_ratio"] = SM.table_md(head, "ratio_vs_none", "{:.2f}")
    hr = s.get("headline_real")
    if hr and hr.get("rows"):
        out["table_real_tip"] = SM.table_md(hr, "tip_mm", "{:.2f}")
        out["table_real_words"] = SM.table_md(hr, "words10", "{:.0f}")
    cards = s.get("cards")
    if cards:
        lines = ["| Population | Mode | Classes and writers | Readable words | Useful words / min | Tremor left at the tip (mm; no help) | Clean writing changed (µm) | Ink laid (coverage) | Nose power (W) | Other devices (W) | Felt grip-force change (N rms) |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in cards:
            cw = ", ".join(RS.CLASS_LABEL.get(x, x).split(" (")[0] for x in c.get("classes", [])) + f"; writers {', '.join(str(w) for w in c.get('writers', []))}"
            lines.append(f"| {c['population']} | {c['mode']} | {cw} | {c['readable_words']} | {_fmt(c['useful_words_per_min'])} | "
                         f"{_fmt(c['tremor_left_mm_mean'], '{:.2f}')} ({_fmt(c['tremor_no_help_mm_mean'], '{:.2f}')}) | "
                         f"{_fmt(c['clean_writing_changed_um'], '{:.0f}')} | {_fmt(c['coverage'], '{:.2f}')} | "
                         f"{_fmt(c['power_W_nose'], '{:.2f}')} | {_fmt(c['power_W_other_devices'], '{:.2f}')} | "
                         f"{_fmt(c.get('felt_grip_force_change_rms_N'), '{:.2f}')} |")
        lines += ["", "Missing strokes and completion time are in §3f (from the saved records). Felt grip-force change: "
                  "'–' where the device-off run was not in memory for the comparison."]
        out["cards"] = "\n".join(lines)
    st = s.get("strokes_from_traces")
    if st:
        L = ["| Writer | Tremor class | Pen and mode | Ink laid (of the intended strokes) | Strokes less than half inked | Lost pieces | Completion if the lost ink were re-traced (s added to the writing time) |",
             "|---|---|---|---|---|---|---|"]
        for r in st:
            if r["class"] not in ("ET_severe", "PD_severe"):
                continue
            L.append(f"| {r['w']} | {RS.CLASS_LABEL.get(r['class'], r['class'])} | {RS.LABELS.get(r['design'], r['design'])} | "
                     f"{100 * r['coverage_intended']:.0f} % | {r['missing_strokes']} of {r['n_strokes']} | {r['lost_pieces']} | "
                     f"+{r['completion_extra_s']:.1f} (× {r['completion_time_ratio']:.2f}) |")
        out["strokes"] = "\n".join(L)
    g = s.get("tail_and_collar_vs_locked_grips", []) + s.get("tail_and_collar_vs_locked_test", [])
    if g:
        lines = ["| Active device | Compared with | Tremor class | Grip (x nominal) | Writers | Tip tremor active (mm) | Tip tremor locked (mm) | Improvement over locked | Passes the 10 % gate |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for r in g:
            ws = r.get("writers") or []
            wl = ("tuning " if ws and min(ws) >= 100 else "test ") + ", ".join(str(w) for w in ws) if ws else "–"
            lines.append(f"| {RS.LABELS.get(r['active'], r['active'])} | {RS.LABELS.get(r['locked'], r['locked'])} | {RS.CLASS_LABEL.get(r['class'], r['class'])} | "
                         f"{r['grip']:g} | {wl} | {r['tip_active_mm']:.2f} | {r['tip_locked_mm']:.2f} | {100 * r['gain_vs_locked']:.0f} % | "
                         f"{'yes' if r['passes_10pc_gate'] else 'no'} |")
        out["gate_sim"] = "\n".join(lines)
    inc = s.get("collar_increment")
    if inc:
        L = ["| Tremor class | Rev J nose (its own pen) | Collar pen, collar locked + nose | Collar + nose | Collar's gain over locked | Nose, perfect knowledge | Collar + nose, perfect knowledge | Perfect knowledge: collar + nose / nose alone |",
             "|---|---|---|---|---|---|---|---|"]

        def cell(r, d):
            v = r.get(d)
            if not v:
                return "–"
            star = "*" if len(v["writers"]) < 2 else ""
            return f"{v['tip_mm']:.2f} mm, {v['words']:.0f} of {v['words_of']} words, ink laid {100 * v['coverage']:.0f} %{star}"
        def pct(g):
            if g is None:
                return "–"
            v = int(round(100 * g))
            return f"{v} %" if v != 0 else "0 %"
        for r in inc:
            g1 = r.get("collar_gain_vs_locked")
            g2 = r.get("oracle_collar_gain")
            rt = "–" if g2 is None else f"× {1 - g2:.1f}" + (" (worse)" if g2 < -0.05 else "")
            L.append(f"| {r['class_label']} | {cell(r, 'nose')} | {cell(r, 'collar_locked_nose')} | {cell(r, 'collar_nose')} | "
                     f"{pct(g1)} | {cell(r, 'nose_oracle')} | {cell(r, 'collar_nose_oracle')} | {rt} |")
        if any("*" in x for x in L):
            L += ["", "\\* test writer 0 only."]
        out["collar_increment"] = "\n".join(L)
    calc = _load("calc.json")
    if calc and "collar_control_compact" in calc:
        L = ["| Inner pen | Web rests on | Ink moved / ideal lever | Error of the controller's model | Loop margin (gain 0.75) | Actuator torque per mm of tip tremor |",
             "|---|---|---|---|---|---|"]
        for key, pen in (("collar_control_compact", "compact 12 mm barrel (22 g)"), ("collar_control_revJ", "Rev J pen as the inner pen (87 g)")):
            rows = calc[key]["rows"]
            for web in (True, False):
                rr = [r for r in rows if r["web_on_collar"] == web]
                ph = max(rr, key=lambda r: max(abs(x) for x in r["model_phase_err_deg"]))
                phv = max(abs(x) for x in ph["model_phase_err_deg"])
                L.append(f"| {pen} | {'the collar (saddle)' if web else 'the moving barrel'} | "
                         f"{min(r['transmission_min'] for r in rr):.2f}–{max(r['transmission_max'] for r in rr):.2f} | "
                         f"gain {min(min(r['model_gain_ratio']) for r in rr):.2f}–{max(max(r['model_gain_ratio']) for r in rr):.2f}, "
                         f"phase ≤ {phv:.0f}° ({ph['f']:g} Hz, grip {ph['grip_scale']:g} ×) | "
                         f"≥ {min(r['loop_margin_g0.75'] for r in rr):.2f} | "
                         f"{min(r['torque_mNm_per_mm_tip'] for r in rr):.1f}–{max(r['torque_mNm_per_mm_tip'] for r in rr):.1f} mN·m |")
        out["collar_control"] = "\n".join(L)
    lc = s.get("light_compare")
    if lc and lc.get("rows"):
        cls = lc["classes"]
        L = ["| Pen and mode | " + " | ".join(RS.CLASS_LABEL.get(c, c) for c in cls) + " |", "|---|" + "---|" * len(cls)]
        for r in lc["rows"]:
            cells = []
            for c in cls:
                v = r.get(c)
                if not v:
                    cells.append("–")
                    continue
                star = "*" if len(v["writers"]) < 2 else ""
                cells.append(f"{v['tip_mm']:.2f} mm, {v['words']:.0f} of {v['words_of']} words, ink laid {100 * v['coverage']:.0f} %{star}")
            if any(x != "–" for x in cells):
                L.append(f"| {r['label']} | " + " | ".join(cells) + " |")
        if any("*" in x for x in L[2:]):
            L += ["", "\\* test writer 0 only."]
        out["light_compare"] = "\n".join(L)
    v = _load("verification.json")
    if v:
        L = ["| Check | Result | Pass line |", "|---|---|---|"]
        for k in ("cmg_torque_50us", "cmg_torque_25us"):
            if k in v:
                r = v[k]
                L.append(f"| CMG pair torque vs closed form -2 h delta' cos(delta) ({k[-4:]}) | max rel. error {r.get('rel_err_max', r.get('err_max', float('nan'))):.3f}, off-axis {r.get('offaxis_rel_max', float('nan')):.1e} | < 0.05 (halves with the step) |")
        for k in ("cmg_energy_50us", "cmg_energy_25us"):
            if k in v:
                r = v[k]
                L.append(f"| CMG pair free-floating: energy and angular momentum ({k[-4:]}) | angular momentum drift over 1 s {r.get('L_drift_rel_max', float('nan')):.3f} (rotors at 2 600 rad/s: 0.13 rad per 50 µs step) | < 0.05; falls with the step |")
        if "tmd_closed" in v:
            L.append(f"| Tuned mass stroke vs 2-DOF closed form | max rel. error {v['tmd_closed']['err_max']:.3f} | < 0.05 |")
        if "collar_modes" in v:
            r = v["collar_modes"]
            L.append(f"| Collar rocking frequency vs sqrt(K_c/J) | {r['f_sim_Hz']:.3f} vs {r['f_closed_Hz']:.3f} Hz (rel. {r['rel_err']:.3f}); energy drift over 3 s undamped {r['E_drift_rel_max']:.3f} | < 0.02; < 0.05 |")
        if "sled_static" in v:
            L.append(f"| Hand displacement under a constant force vs F / k_arm | rel. error {v['sled_static']['rel_err']:.3f} | < 0.02 |")
        if "collar_v2_transmission" in v:
            for r in v["collar_v2_transmission"]["rows"]:
                L.append(f"| V2 collar, prescribed swing {r['axis']}: ink amplitude, full model vs the controller's linear model | {r['ink_amp_sim_mm']:.2f} vs {r['ink_amp_lin_mm']:.2f} mm (rel. {r['rel_err']:.3f}); ball on the paper {100 * r['contact_share']:.0f} % | < 0.10 |")
        if "dt_convergence" in v:
            r = v["dt_convergence"]
            L.append("| Time step 50 vs 25 us, closed loop (collar + nose, ET 3 mm) | " + "; ".join(f"{x['dt_us']:.0f} us: {x['tip_collar_nose_mm']:.3f} mm" for x in r["rows"]) + f" (rel. {r['rel_diff_tip']:.3f}) | < 0.05 |")
        out["verify"] = "\n".join(L)
    arm = (_load("summary.json") or {}).get("arm")
    if arm:
        L = ["| Class | Design | Tremor left (mm) | Words read (of 5) | Ink laid | Ink error (µm) |", "|---|---|---|---|---|---|"]
        for r in arm:
            L.append(f"| {RS.CLASS_LABEL.get(r['class'], r['class'])} | {RS.LABELS.get(r['design'], r['design'])} | {_fmt(r.get('tip_tremor_mm'), '{:.2f}')} | "
                     f"{_fmt(5 * r['words_app'] if r.get('words_app') is not None else None, '{:.0f}')} | {_fmt(r.get('coverage'), '{:.2f}')} | {_fmt(r.get('ink_err_um'), '{:.0f}')} |")
        out["arm"] = "\n".join(L)
    tune = RS.Rows("tune").values()
    if tune:
        keep = [("h1|g1|w100|s300|ET_moderate|collar_locked", "collar pen, locked (device-off reference)"),
                ("tr_nose|h1|g1|w100|s300|ET_moderate|nose", "Rev J nose, guarded tracker (sim2j G4)"),
                ("tr_nose_gl|h1|g1|w100|s300|ET_moderate|nose", "Rev J nose, gated listening (fallback Rev H as built)"),
                ("tr_nose_glg|h1|g1|w100|s300|ET_moderate|nose", "Rev J nose, gated listening + guarded fallback"),
                ("cpg_g0.75_f0.9|h1|g1|w100|s300|ET_moderate|collar_nose", "collar + nose, gain 0.75, reference cap 0.9"),
                ("cpg_g0.5_f0.65|h1|g1|w100|s300|ET_moderate|collar_nose", "collar + nose, gain 0.5, cap 0.65"),
                ("cpg_g0.5_s0.6_f0.65|h1|g1|w100|s300|ET_moderate|collar_nose", "collar + nose, gain 0.5, share <= 0.6, cap 0.65"),
                ("h1|g1|w100|s300|ET_moderate|collar_oracle", "collar alone, perfect knowledge"),
                ("h1|g1|w100|s300|PD_severe|collar_locked", "collar pen, locked (device-off reference)"),
                ("tr_nose|h1|g1|w100|s300|PD_severe|nose", "Rev J nose, guarded tracker"),
                ("tr_nose_gl|h1|g1|w100|s300|PD_severe|nose", "Rev J nose, gated listening"),
                ("tr_nose_glg|h1|g1|w100|s300|PD_severe|nose", "Rev J nose, gated listening + guarded fallback"),
                ("cpg_g0.75_f0.9|h1|g1|w100|s300|PD_severe|collar_nose", "collar + nose, gain 0.75, cap 0.9"),
                ("cpg_g0.5_f0.65|h1|g1|w100|s300|PD_severe|collar_nose", "collar + nose, gain 0.5, cap 0.65"),
                ("cpg_g0.5_s0.6_f0.65|h1|g1|w100|s300|PD_severe|collar_nose", "collar + nose, gain 0.5, share <= 0.6, cap 0.65"),
                ("h1|g1|w100|s300|PD_severe|collar_oracle", "collar alone, perfect knowledge"),
                ("h1|g1|w100|s300|ET_moderate|gt_locked", "gyro tail 100 g locked, nose held"),
                ("g|h1|g1|w100|s300|ET_moderate|gt_locked_nose", "gyro tail locked + nose (gated listening + guarded)"),
                ("cmgg_damp|h1|g1|w100|s300|ET_moderate|gt_nose", "gyro tail, rate-damping law + nose"),
                ("cmgg_afc|h1|g1|w100|s300|ET_moderate|gt_nose", "gyro tail, adaptive cancellation + nose"),
                ("cmgg_ff|h1|g1|w100|s300|ET_moderate|gt_nose", "gyro tail, phasor feed-forward + nose"),
                ("h1|g1|w100|s300|ET_moderate|gt_oracle", "gyro tail alone, perfect knowledge"),
                ("g|h1|g1|w100|s300|ET_severe|nose", "Rev J nose (gated listening + guarded)"),
                ("gmg0.3|h1|g1|w100|s300|ET_severe|nose_gate", "nose + write only when in reach, margin 0.3 mm"),
                ("gmg1.0|h1|g1|w100|s300|ET_severe|nose_gate", "nose + write only when in reach, margin 1.0 mm"),
                ("tr_nose|h1|g1|w100|s300|clean|nose", "tremor-free writing, guarded tracker"),
                ("tr_nose_gl|h1|g1|w100|s300|clean|nose", "tremor-free writing, gated listening"),
                ("tr_nose_glg|h1|g1|w100|s300|clean|nose", "tremor-free writing, gated listening + guarded")]
        d = {r["key"]: r for r in tune}
        L = ["| Case | Class | Tremor left (mm) | Ink error (µm) | Words read (of 5) | Ink laid | Pivot peak (rad) | Clean writing moved (µm) |",
             "|---|---|---|---|---|---|---|---|"]
        for k, lab in keep:
            r = d.get(k)
            if r is None:
                continue
            L.append(f"| {lab} | {RS.CLASS_LABEL.get(r['class'], r['class'])} | {_fmt(r.get('tip_tremor_mm'), '{:.2f}')} | {_fmt(r.get('ink_err_um'), '{:.0f}')} | "
                     f"{_fmt(5 * r['words_app'] if r.get('words_app') is not None else None, '{:.0f}')} | {_fmt(r.get('coverage'), '{:.2f}')} | "
                     f"{_fmt(r.get('pivot_peak_rad'), '{:.3f}') if r.get('pivot_peak_rad') else '–'} | "
                     f"{_fmt(r.get('moved_vs_clean_um'), '{:.0f}') if r['class'] == 'clean' else '–'} |")
        out["tuning"] = "\n".join(L)
    rules = _load("rules.json")
    if rules:
        out["rules"] = "```json\n" + json.dumps({"rules": rules["rules"], "evidence": rules.get("evidence"), "frozen_utc": rules.get("frozen_utc")}, indent=1) + "\n```"
    return out


TOKEN = re.compile(r"«([A-Za-z_0-9]+)\|([a-z_0-9]+)\|([a-z_0-9]+)(?:\|([0-9]))?»")


def fill_tokens(txt: str) -> str:
    """Replace «class|design|key|decimals» with the two-writer value from summary.json's headline (key: tip_mm,
    words10, coverage, ratio_vs_none, ink_err_um) or, for class 'clean', the tremor-free writing moved (µm) from the
    test rows."""
    s = _load("summary.json") or {}
    head = {(r["class"], r["design"]): r for r in s.get("headline", {}).get("rows", []) + s.get("headline_real", {}).get("rows", [])}
    for r in (s.get("light_compare") or {}).get("rows", []):
        for c in (s.get("light_compare") or {}).get("classes", []):
            v = r.get(c)
            if v and (c, r["design"]) not in head:
                head[(c, r["design"])] = {"tip_mm": v["tip_mm"], "words10": v["words"], "coverage": v["coverage"],
                                          "P_devices_W": v.get("P_devices_W"), "pivot_peak_rad": v.get("pivot_peak_rad")}
    test = RS.Rows("test").values()

    def rep(m):
        c, d, k, dec = m.group(1), m.group(2), m.group(3), m.group(4)
        dec = int(dec) if dec else (0 if k in ("words10", "ink_err_um") else 2)
        if c == "clean":
            v = [r.get("moved_vs_clean_um") for r in test if r.get("class") == "clean" and r.get("design") == d]
            v = [x for x in v if x is not None]
            return f"{max(v):.0f}" if v else "–"
        r = head.get((c, d))
        if r is None or r.get(k) is None:
            return "–"
        val = r[k] * (100.0 if k == "coverage" else 1.0)
        return f"{val:.{dec}f}"
    return TOKEN.sub(rep, txt)


NAMED = re.compile(r"«([A-Z][A-Z0-9_]+)»")


def named_values() -> Dict[str, str]:
    """Values the text names in capitals (computed here from the result files, so the text never carries a typed number)."""
    s = _load("summary.json") or {}
    calc = _load("calc.json") or {}
    rl = _load("rules_light.json")
    out: Dict[str, str] = {}
    lc = {(c, r["design"]): r.get(c) for r in (s.get("light_compare") or {}).get("rows", [])
          for c in (s.get("light_compare") or {}).get("classes", []) if r.get(c)}
    a, b = lc.get(("PD_severe", "light_nose")), lc.get(("PD_severe", "light_locked_nose"))
    if a and b:
        out["LIGHT_GAIN_PD8"] = f"{100 * (1 - a['tip_mm'] / b['tip_mm']):.0f}"
        out["LIGHT_COV_LOSS"] = f"{100 * (b['coverage'] - a['coverage']):.0f}"
    mm = (calc.get("collar_masses") or {})
    if "coil" in mm:
        c = mm["coil"]
        out.update(M_COLLAR=f"{c['collar_g']:.1f}", M_INNER=f"{c['barrel_g']:.1f}", M_TOTAL=f"{c['total_g']:.1f}",
                   ZG_INNER=f"{c['barrel_zg_mm']:.1f}",
                   ZG_DIFF=(f"{abs(c['barrel_zg_mm'] - 50.0):.1f} mm " + ("behind" if c["barrel_zg_mm"] > 50.0 else "in front of")))
    if "geared" in mm:
        out["M_GEARED"] = f"{mm['geared']['total_g']:.1f}"
    pw = [r for r in calc.get("collar_power_compact", []) if r["path"] == "V2" and r["actuator"] == "coil"]
    r8 = next((r for r in pw if abs(r["A_mm"] - 8.0) < 1e-6), None)
    if r8:
        out["CALC_SWING_W"] = f"{r8['P_tremor_W']:.2f}"
        out["CALC_HOLD_W"] = f"{r8['P_static_W']:.2f}"
    if r8:
        out["CALC_TAU8"] = f"{r8['tau_peak_mNm']:.1f}"
    for key, tag in (("collar_control_compact", "CMP"), ("collar_control_revJ", "RVJ")):
        rows = (calc.get(key) or {}).get("rows", [])
        for web, wt in ((True, "C"), (False, "B")):
            rr = [r for r in rows if r["web_on_collar"] == web]
            if not rr:
                continue
            out[f"{tag}{wt}_TMIN"] = f"{min(r['transmission_min'] for r in rr):.2f}"
            out[f"{tag}{wt}_TMAX"] = f"{max(r['transmission_max'] for r in rr):.2f}"
            out[f"{tag}{wt}_PH"] = f"{max(max(abs(x) for x in r['model_phase_err_deg']) for r in rr):.0f}"
            out[f"{tag}{wt}_MARGIN"] = f"{min(r['loop_margin_g0.75'] for r in rr):.2f}"
            out[f"{tag}{wt}_TQMIN"] = f"{min(r['torque_mNm_per_mm_tip'] for r in rr):.1f}"
            out[f"{tag}{wt}_TQMAX"] = f"{max(r['torque_mNm_per_mm_tip'] for r in rr):.1f}"
    st = {(r["w"], r["class"], r["design"]): r for r in (s.get("strokes_from_traces") or [])}
    mod = [r["missing_strokes"] for r in (s.get("strokes_from_traces") or []) if r["class"] in ("ET_moderate", "PD_moderate")]
    if mod:
        out["MOD_MISS_MAX"] = f"{max(mod)}"
    for tag, key in (("GATE_ET", (0, "ET_severe", "nose_gate")), ("GATE_PD", (0, "PD_severe", "nose_gate")),
                     ("NOSE_ET", (0, "ET_severe", "nose")), ("NOSE_PD", (0, "PD_severe", "nose"))):
        r = st.get(key)
        if r:
            out[f"{tag}_MISS"] = f"{r['missing_strokes']}"
            out[f"{tag}_EXTRA"] = f"{r['completion_extra_s']:.0f}"
            out["TASK_S"] = f"{r['task_time_s']:.1f}"
    gr = s.get("tail_and_collar_vs_locked_grips", []) + s.get("tail_and_collar_vs_locked_test", [])
    gt = {(r["grip"], tuple(r.get("writers", []))): r for r in gr if r["active"] == "gt_nose" and r["locked"] == "gt_locked_nose"}
    for (g, ws), r in gt.items():
        tag = "GT_TEST" if ws and min(ws) < 100 else f"GT_G{g:g}".replace(".", "")
        out[tag] = f"{100 * r['gain_vs_locked']:.0f}"
    col = [r for r in gr if r["active"] == "collar_nose" and r["locked"] == "collar_locked_nose"]
    if col:
        out["COL_GMIN"] = f"{100 * min(r['gain_vs_locked'] for r in col):.0f}"
        out["COL_GMAX"] = f"{100 * max(r['gain_vs_locked'] for r in col):.0f}"
    op = _load("optimise.json") or {}
    cd = op.get("collar_design")
    if cd:
        b, n0 = cd["best"], cd["nominal"]
        gz = cd["gradient_check_zp"]
        out.update(OPT_ZP=f"{b['z_p_mm']:.0f}", OPT_ZG=f"{b['z_g_mm']:.0f}", OPT_KS=f"{b['K_s']:.1f}", OPT_CS=f"{b['C_s']:.3f}",
                   OPT_TRAVEL=f"{b['travel_mm']:.1f}", OPT_TRAVEL0=f"{n0['travel_mm']:.1f}",
                   OPT_GAIN=f"{100 * (1 - b['f'] / n0['f']):.0f}", OPT_EVALS=f"{cd['cmaes']['evals']}",
                   OPT_GRAD=f"{gz['d_dzp_autograd']:.4g} against {gz['d_dzp_fd']:.4g}")
    cb = op.get("combo_100g")
    if cb:
        b, n0 = cb["best"], cb["nominal"]
        out.update(CMB_RO=f"{b['r_o_mm']:.1f}", CMB_RPM=f"{b['rpm']:.0f}", CMB_DMAX=f"{b['delta_max']:.2f}",
                   CMB_TQ=f"{b['tau_g_max_mNm']:.0f}", CMB_H=f"{b['h_mNms']:.1f}", CMB_E=f"{b['E_J']:.1f}", CMB_E0=f"{n0['E_J']:.1f}",
                   CMB_GAIN=f"{100 * (1 - b['f'] / n0['f']):.1f}", CMB_EVALS=f"{cb['cmaes']['evals']}")
        gc = cb.get("gradient_check", {})
        k = next(iter(gc), None)
        if k:
            out["CMB_GRAD"] = f"{gc[k]['d_dm_autograd']:.4g} against {gc[k]['d_dm_fd']:.4g}"
    cs = calc.get("collar_static")
    if cs:
        for r in cs["rows"]:
            out[f"HOLD{r['theta_deg']:.0f}"] = f"{r['P_coil_W']:.2f}" if r["P_coil_W"] >= 0.01 else f"{r['P_coil_W']:.3f}"
            out[f"HOLDM{r['theta_deg']:.0f}"] = f"{r['moment_mNm']:.1f}"
    if rl:
        r = rl["rules"]
        out["LF_RULE"] = f"gain {r['lf_gain']:g}, collar share up to {r['lf_share_max']:g}, reference up to {100 * r['lf_frac']:.0f} % of the range"
        t3, t8 = lc.get(("ET_moderate", "light_fine_t")), lc.get(("PD_severe", "light_fine_t"))
        n3 = next((x for x in s.get("headline", {}).get("rows", []) if x["class"] == "ET_moderate" and x["design"] == "nose"), None)
        n8 = next((x for x in s.get("headline", {}).get("rows", []) if x["class"] == "PD_severe" and x["design"] == "nose"), None)
        if t3 and t8 and n3 and n8:
            ev = rl.get("evidence", {})
            covs = [v.get("coverage") for v in ev.values() if v.get("coverage") is not None]
            tips = [v.get("tip_mm") for v in ev.values() if v.get("tip_mm") is not None]
            lk3 = lc.get(("ET_moderate", "light_locked"))
            out["LF_PARAGRAPH"] = (
                f"Giving the collar the gains it needs to take most of the tremor made the loop unstable: on the tuning writer "
                f"({len(ev)} settings with gain 0.75-1 and no share cap) only {100 * min(covs):.0f}-{100 * max(covs):.0f} % of the "
                f"ink was laid and " + (f"{min(tips):.1f}-{max(tips):.1f}" if round(min(tips), 1) != round(max(tips), 1) else f"{min(tips):.1f}")
                + f" mm of tremor was left. The less bad setting, frozen before its "
                f"test runs (`rules_light.json`: {out['LF_RULE']}), left {t3['tip_mm']:.2f} mm at 3 mm ET (ink laid "
                f"{100 * t3['coverage']:.0f} %) and {t8['tip_mm']:.2f} mm at 8 mm PD ({100 * t8['coverage']:.0f} %) on the test "
                f"writers — worse than the same pen with nothing moving"
                + (f" ({lk3['tip_mm']:.2f} mm at 3 mm ET)" if lk3 else "")
                + f" and far worse than the Rev J nose ({n3['tip_mm']:.2f} and {n8['tip_mm']:.2f} mm). This study found no causal "
                f"law with which the collar can be the main corrector; with perfect knowledge it can (above).")
    return out


def fill_named(txt: str) -> str:
    vals = named_values()
    return NAMED.sub(lambda m: vals.get(m.group(1), m.group(0)), txt)


TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc_template.md")


def fill_doc(path: str = DOC, template: str = TEMPLATE) -> str:
    """Write the document from its template (wholepen/doc_template.md: the text with «class|design|key» and «NAME»
    placeholders and empty generated blocks), so every number in the text comes from the result files; without the
    template, refresh the generated blocks of the document in place."""
    src = template if template and os.path.exists(template) else path
    txt = fill_named(fill_tokens(open(src).read()))
    for name, body in blocks().items():
        pat = re.compile(rf"(<!-- W:{name} -->)(.*?)(<!-- /W:{name} -->)", re.S)
        txt = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), txt)
    open(path, "w").write(txt)
    return path


if __name__ == "__main__":
    print(fill_doc())
