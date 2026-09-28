"""Markdown tables for docs/sensor_fusion_ai.md, printed from results/fusion/*.json (python3 -m fusion.report)."""
from __future__ import annotations

import json
import os

import numpy as np

from . import RESULTS

ORDER = ["oracle", "oracle_band", "kfosc_internal", "kfosc_port_matched", "kfosc_port", "kfosc_p1", "kfosc_p1_lp", "bmflc", "wflc",
         "wflc_robust", "akf", "akf_robust", "akf_personal", "gru", "kfosc_port_120", "akf_120", "gru_120"]
NAMES = {"oracle": "Oracle (physical limit, perfect knowledge)", "oracle_band": "Tremor-band oracle (3-15 Hz, non-causal)",
         "kfosc_internal": "(a) Frozen Kalman, core mode", "kfosc_port_matched": "(a) Frozen Kalman, external port, core's IMU",
         "kfosc_port": "(a) Frozen Kalman, external port, this study's sensors", "kfosc_p1": "Frozen-structure Kalman retuned on P1",
         "kfosc_p1_lp": "Frozen-structure Kalman retuned on P1, with the output low-pass",
         "bmflc": "(c) BMFLC on acceleration", "wflc": "(c) WFLC on acceleration", "akf": "(b) Acceleration Kalman (AKF), page 1 kHz",
         "akf_personal": "(f) AKF, personalised", "gru": "(d) Learned GRU, page 1 kHz", "kfosc_port_120": "(a) Frozen Kalman, page 120 Hz",
         "akf_robust": "(b) AKF, robust tuning (grid + glyph writers)", "wflc_robust": "(c) WFLC, robust tuning",
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
            "pull_wrong_letter_gated", "pull_wrong_letter_full", "akf", "akf_robust", "wflc", "wflc_robust", "gru", "ctx_none", "ctx_oracle",
            "ctx_ai_correct", "ctx_ai_predicted", "ctx_wrong_letter_gated", "ctx_wrong_letter_full"]
    out = ["| Case | path RMS all ink (µm) | path RMS writing only (µm) | DTW writing only (µm) | recognised (writing only) | ink ratio vs no correction | distortion on tremor-free writing (µm) | at soft limit | flips |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        if k not in S:
            continue
        s = S[k]
        g = lambda m, nd=0: (f"{s[m]['mean']:.{nd}f} ± {s[m]['sd']:.{nd}f}" if m in s else "")
        fl = f"{s['flips_newly_read_as_wrong_letter_total']}/{s['flips_n_letters_total']}" if "flips_newly_read_as_wrong_letter_total" in s else ""
        out.append(f"| {k} | {g('path_rms_um')} | {g('wo_path_rms_um')} | {g('wo_dtw_mean_um')} | {g('wo_recognition_accuracy', 3)} | "
                   f"{g('ratio', 3)} | {g('distortion_um')} | {g('at_soft_limit', 3)} | {fl} |")
    te = c["template_error"]
    out.append("\n| Template | total (µm) | after per-letter offset | after per-letter affine | segment-mean removed | < 3 Hz | 3-15 Hz |")
    out.append("|---|---|---|---|---|---|---|")
    for k in ("oracle", "ai_correct", "ai_predicted", "wrong_letter"):
        t = te[k]
        f = lambda m: f"{t[m]['mean']:.0f}" if m in t else ""
        out.append(f"| {k} | {f('total')} | {f('after_offset')} | {f('after_affine')} | {f('segment_mean_removed_rms_um')} | {f('below_3Hz_rms_um')} | {f('band_3_15Hz_rms_um')} |")
    return "\n".join(out)


COMP_NAMES = {"none": "board accelerometer, no compensation", "nose": "nose accelerometer only (17 mm)",
              "dual": "nose + board accelerometers", "gyro": "board 6-axis IMU, gyroscope-compensated",
              "ideal": "translation-only IMU at the nib (reference)"}


def sensor_tables(s):
    out = []
    ol = s["leverarm_open_loop"]["rows"]
    out.append("| Compensation | rho = 0 | rho = 0.5 | rho = 1.0 |")
    out.append("|---|---|---|---|")
    for c in ("none", "nose", "dual", "gyro", "ideal"):
        cells = [f"{np.mean([r['band_error_rel'] for r in ol if r['comp'] == c and r['rho'] == rho]) * 100:.1f} %" for rho in (0.0, 0.5, 1.0)]
        out.append(f"| {COMP_NAMES[c]} | " + " | ".join(cells) + " |")
    cl = s["leverarm_closed_loop"]["summary"]
    out.append("\n| Compensation | page 1 kHz, rho 0.5 | page 1 kHz, rho 1.0 | page 120 Hz, rho 0.5 | page 120 Hz, rho 1.0 |")
    out.append("|---|---|---|---|---|")
    for c in ("none", "nose", "dual", "gyro", "ideal"):
        cells = []
        for page, rho in (("1k", 0.5), ("1k", 1.0), ("120", 0.5), ("120", 1.0)):
            v = cl.get(f"{page}_{c}_rho{rho:g}")
            cells.append("" if v is None else f"{v['ratio_mean']:.3f} (band {v['band_ratio_mean']:.3f})")
        out.append(f"| {COMP_NAMES[c]} | " + " | ".join(cells) + " |")
    fc = s.get("friction_control", {}).get("summary", {})
    if fc:
        out.append("\nfriction control: " + json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in fc.items()}))
    jc = s.get("jitter_check", {}).get("summary", {})
    for k, v in jc.items():
        out.append(f"jitter {k}: ratio {v['ratio_mean']:.3f}, P_rail {v['P_rail_classB_mW_mean']:.0f} mW, housing {v['housing_vs_neutral_um_mean']:.0f} um")
    nz = s.get("imu_noise_closed_loop", {}).get("summary", {})
    out.append("imu noise closed loop: " + json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in nz.items()}))
    aa = s.get("imu_aa_check", {}).get("summary", {})
    out.append("imu_aa check (internal kfosc): " + json.dumps({k: round(v["kfosc_internal_ratio_mean"], 3) for k, v in aa.items()}))
    return "\n".join(out)


GLANCE = [("neutral", "neutral", "No correction"), ("oracle", "oracle_disturbance", "Oracle: perfect knowledge of the whole disturbance (a limit, not an estimator)"),
          ("oracle_band", None, "Tremor-band oracle: perfect 3-15 Hz knowledge, non-causal (the limit for tremor estimators)"),
          ("kfosc_internal", "kfosc_internal", "Frozen Kalman filter (today's core)"),
          ("akf", "akf", "AKF, tuned on the grid's writing"), ("akf_robust", "akf_robust", "AKF, robust tuning (recommended)"),
          ("wflc", "wflc", "WFLC on acceleration"), ("gru", "gru", "Learned GRU"), ("akf_personal", None, "AKF, personalised by the 20 s calibration"),
          (None, "ctx_ai_correct", "AI prior: correct letters in the writer's style"), (None, "ctx_ai_predicted", "AI prior: the phone's predicted letters (confidence-gated)"),
          (None, "ctx_wrong_letter_full", "AI prior: wrong letter at full confidence (safety)"),
          (None, "pull_ai_correct", "Old template pull: correct letters (for comparison)")]


def glance(g, c):
    rows = ["| | P1 grid ratio | P1 grid 3-15 Hz ratio | P1 distortion (µm) | aiguide path RMS, writing only (µm) | aiguide ink ratio | aiguide distortion (µm) |",
            "|---|---|---|---|---|---|---|"]
    S = (g or {}).get("summary", {})
    D = (g or {}).get("distortion_um", {})
    C = (c or {}).get("summary", {})
    for gk, ck, name in GLANCE:
        o = S.get(gk, {}).get("overall", {}) if gk else {}
        r = "1" if gk == "neutral" else (f"{o['ratio_mean']:.3f}" if "ratio_mean" in o else "–")
        b = "1" if gk == "neutral" else (f"{o['band_ratio_mean']:.3f}" if "band_ratio_mean" in o else "–")
        d = "0" if gk == "neutral" else (f"{D[gk]['mean']:.0f}" if gk in D else "–")
        cs = C.get(ck, {}) if ck else {}
        pw = f"{cs['wo_path_rms_um']['mean']:.0f}" if "wo_path_rms_um" in cs else "–"
        cr = f"{cs['ratio']['mean']:.3f}" if "ratio" in cs and ck not in ("neutral",) else ("1" if ck == "neutral" else "–")
        cd = f"{cs['distortion_um']['mean']:.0f}" if "distortion_um" in cs else ("0" if ck == "neutral" else "–")
        rows.append(f"| {name} | {r} | {b} | {d} | {pw} | {cr} | {cd} |")
    return "\n".join(rows)


def main():
    g0, c0 = _j("grid.json"), _j("context.json")
    if g0 or c0:
        print(glance(g0, c0))
    s = _j("sensors.json")
    if s:
        print(sensor_tables(s))
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
