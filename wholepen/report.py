r"""Fills the generated parts of docs/whole_pen_shift.md from the result files (between <!-- W:name --> and
<!-- /W:name --> markers), so every number in those parts comes from results/wholepen/*.json.
Usage: python3 -m wholepen.report
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
    cards = s.get("cards")
    if cards:
        lines = ["| Population | Mode | Readable words | Useful words / min | Tremor left at the tip (mm; no help) | Clean writing changed (µm) | Ink laid (coverage) | Missing strokes | Nose power (W) | Other devices (W) |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for c in cards:
            lines.append(f"| {c['population']} | {c['mode']} | {c['readable_words']} | {_fmt(c['useful_words_per_min'])} | "
                         f"{_fmt(c['tremor_left_mm_mean'], '{:.2f}')} ({_fmt(c['tremor_no_help_mm_mean'], '{:.2f}')}) | "
                         f"{_fmt(c['clean_writing_changed_um'], '{:.0f}')} | {_fmt(c['coverage'], '{:.2f}')} | "
                         f"{_fmt(100 * c['missing_stroke_rate'] if c['missing_stroke_rate'] is not None else None, '{:.0f} %')} | "
                         f"{_fmt(c['power_W_nose'], '{:.2f}')} | {_fmt(c['power_W_other_devices'], '{:.2f}')} |")
        out["cards"] = "\n".join(lines)
    g = s.get("tail_and_collar_vs_locked_grips", []) + s.get("tail_and_collar_vs_locked_test", [])
    if g:
        lines = ["| Active device | Compared with | Tremor class | Grip (x nominal) | Tip tremor active (mm) | Tip tremor locked (mm) | Improvement over locked | Passes the 10 % gate |",
                 "|---|---|---|---|---|---|---|---|"]
        for r in g:
            lines.append(f"| {RS.LABELS.get(r['active'], r['active'])} | {RS.LABELS.get(r['locked'], r['locked'])} | {RS.CLASS_LABEL.get(r['class'], r['class'])} | "
                         f"{r['grip']:g} | {r['tip_active_mm']:.2f} | {r['tip_locked_mm']:.2f} | {100 * r['gain_vs_locked']:.0f} % | "
                         f"{'yes' if r['passes_10pc_gate'] else 'no'} |")
        out["gate_sim"] = "\n".join(lines)
    v = _load("verification.json")
    if v:
        L = ["| Check | Result | Pass line |", "|---|---|---|"]
        for k in ("cmg_torque_50us", "cmg_torque_25us"):
            if k in v:
                r = v[k]
                L.append(f"| CMG pair torque vs closed form -2 h delta' cos(delta) ({k[-4:]}) | max rel. error {r.get('rel_err_max', r.get('err_max', float('nan'))):.2e}, off-axis {r.get('offaxis_rel_max', float('nan')):.2e} | < 1e-2 |")
        for k in ("cmg_energy_50us", "cmg_energy_25us"):
            if k in v:
                r = v[k]
                L.append(f"| CMG pair free-floating: energy and angular momentum ({k[-4:]}) | energy drift {r.get('E_drift_rel_max', float('nan')):.2e}, momentum drift {r.get('L_drift_rel_max', float('nan')):.2e} | < 1e-3 |")
        if "tmd_closed" in v:
            L.append(f"| Tuned mass stroke vs 2-DOF closed form | max rel. error {v['tmd_closed']['err_max']:.3f} | < 0.05 |")
        if "collar_modes" in v:
            r = v["collar_modes"]
            L.append(f"| Collar rocking frequency vs sqrt(K_c/J) | {r['f_sim_Hz']:.3f} vs {r['f_closed_Hz']:.3f} Hz (rel. {r['rel_err']:.3f}); energy drift {r['E_drift_rel_max']:.1e} | < 0.02; < 1e-3 |")
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
    rules = _load("rules.json")
    if rules:
        out["rules"] = "```json\n" + json.dumps({"rules": rules["rules"], "evidence": rules.get("evidence"), "frozen_utc": rules.get("frozen_utc")}, indent=1) + "\n```"
    return out


def fill_doc(path: str = DOC) -> str:
    txt = open(path).read()
    for name, body in blocks().items():
        pat = re.compile(rf"(<!-- W:{name} -->)(.*?)(<!-- /W:{name} -->)", re.S)
        txt = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), txt)
    open(path, "w").write(txt)
    return path


if __name__ == "__main__":
    print(fill_doc())
