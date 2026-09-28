"""Markdown tables for docs/sensor_fusion_ai.md, printed from results/fusion/*.json (python3 -m fusion.report)."""
from __future__ import annotations

import json
import os

import numpy as np

from . import RESULTS

ORDER = ["oracle", "oracle_band", "kfosc_internal", "kfosc_port_matched", "kfosc_port", "kfosc_p1", "kfosc_p1_lp", "bmflc", "wflc", "akf",
         "akf_personal", "gru", "kfosc_port_120", "akf_120", "gru_120"]
NAMES = {"oracle": "Oracle (physical limit, perfect knowledge)", "oracle_band": "Tremor-band oracle (3-15 Hz, non-causal)",
         "kfosc_internal": "(a) Frozen Kalman, core mode", "kfosc_port_matched": "(a) Frozen Kalman, external port, core's IMU",
         "kfosc_port": "(a) Frozen Kalman, external port, this study's sensors", "kfosc_p1": "Frozen-structure Kalman retuned on P1",
         "kfosc_p1_lp": "Frozen-structure Kalman retuned on P1, with the output low-pass",
         "bmflc": "(c) BMFLC on acceleration", "wflc": "(c) WFLC on acceleration", "akf": "(b) Acceleration Kalman (AKF), page 1 kHz",
         "akf_personal": "(f) AKF, personalised", "gru": "(d) Learned GRU, page 1 kHz", "kfosc_port_120": "(a) Frozen Kalman, page 120 Hz",
         "akf_120": "(b) AKF, page 120 Hz / 10 ms", "gru_120": "(d) GRU, page 120 Hz"}


def _j(n):
    p = os.path.join(RESULTS, n)
    return json.load(open(p)) if os.path.exists(p) else None


def grid_tables(g):
    S = g["summary"]
    labs = [l for l in ORDER if l in S]
    out = []
    for amp in (0.1, 0.3, 0.5):
        out.append(f"\n**{amp:g} mm peak** (ratio, mean ± SD over seeds 200-203)\n")
        out.append("| Estimator | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz |")
        out.append("|---|---|---|---|---|---|")
        for l in labs:
            cells = []
            for f in (4, 6, 8, 10, 12):
                v = S[l]["ratio"].get(f"{f}Hz_{amp:g}mm")
                cells.append("" if v is None else f"{v['mean']:.2f} ± {v['sd']:.2f}")
            out.append(f"| {NAMES.get(l, l)} | " + " | ".join(cells) + " |")
    out.append("\n| Estimator | mean ratio | mean band ratio (3-15 Hz) | distortion (µm) | saturation | class-B rail (mW) | recovery rail (mW) |")
    out.append("|---|---|---|---|---|---|---|")
    D = g["distortion_um"]
    for l in labs:
        o = S[l].get("overall", {})
        pr = [v["mean"] for v in S[l].get("P_rail_recovery_mW", {}).values()]
        d = D.get(l, {})
        out.append(f"| {NAMES.get(l, l)} | {o.get('ratio_mean', float('nan')):.3f} | {o.get('band_ratio_mean', float('nan')):.3f} | "
                   f"{d.get('mean', float('nan')):.0f} ± {d.get('sd', float('nan')):.0f} | {o.get('q_sat_mean', float('nan')):.3f} | "
                   f"{o.get('P_rail_classB_mW_mean', float('nan')):.0f} | {np.mean(pr) if pr else float('nan'):.1f} |")
    return "\n".join(out)


def achievable(g):
    """Share of the tremor-band limit reached: (1 - ratio) / (1 - ratio of the tremor-band oracle), per condition, then averaged."""
    S = g["summary"]
    out = {}
    if "oracle_band" not in S:
        return out
    for l in ORDER:
        if l not in S or l in ("oracle", "oracle_band"):
            continue
        fr = []
        for k, v in S[l]["ratio"].items():
            b = S["oracle_band"]["ratio"].get(k)
            if b and b["mean"] < 0.98:
                fr.append((1 - v["mean"]) / (1 - b["mean"]))
        if fr:
            out[l] = float(np.mean(fr))
    return out


def context_table(c):
    S = c["summary"]
    keys = ["neutral_no_tremor", "neutral", "oracle_disturbance", "kfosc_internal", "pull_oracle", "pull_ai_correct", "pull_ai_predicted",
            "pull_wrong_letter_gated", "pull_wrong_letter_full", "akf", "gru", "ctx_none", "ctx_oracle", "ctx_ai_correct", "ctx_ai_predicted",
            "ctx_wrong_letter_gated", "ctx_wrong_letter_full"]
    out = ["| Case | path RMS all ink (µm) | path RMS writing only (µm) | DTW writing only (µm) | recognised (writing only) | ink ratio vs no correction | at soft limit | flips |",
           "|---|---|---|---|---|---|---|---|"]
    for k in keys:
        if k not in S:
            continue
        s = S[k]
        g = lambda m, nd=0: (f"{s[m]['mean']:.{nd}f} ± {s[m]['sd']:.{nd}f}" if m in s else "")
        fl = f"{s['flips_newly_read_as_wrong_letter_total']}/{s['flips_n_letters_total']}" if "flips_newly_read_as_wrong_letter_total" in s else ""
        out.append(f"| {k} | {g('path_rms_um')} | {g('wo_path_rms_um')} | {g('wo_dtw_mean_um')} | {g('wo_recognition_accuracy', 3)} | "
                   f"{g('ratio', 3)} | {g('at_soft_limit', 3)} | {fl} |")
    te = c["template_error"]
    out.append("\n| Template | total (µm) | after per-letter offset | after per-letter affine | segment-mean removed | < 3 Hz | 3-15 Hz |")
    out.append("|---|---|---|---|---|---|---|")
    for k in ("oracle", "ai_correct", "ai_predicted", "wrong_letter"):
        t = te[k]
        f = lambda m: f"{t[m]['mean']:.0f}" if m in t else ""
        out.append(f"| {k} | {f('total')} | {f('after_offset')} | {f('after_affine')} | {f('segment_mean_removed_rms_um')} | {f('below_3Hz_rms_um')} | {f('band_3_15Hz_rms_um')} |")
    return "\n".join(out)


def main():
    g = _j("grid.json")
    if g:
        print(grid_tables(g))
        print("\nshare of the tremor-band limit reached (mean over conditions):",
              {k: round(v, 3) for k, v in achievable(g).items()})
    c = _j("context.json")
    if c:
        print(context_table(c))


if __name__ == "__main__":
    main()
