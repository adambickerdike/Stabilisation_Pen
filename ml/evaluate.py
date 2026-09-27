#!/usr/bin/env python3
r"""Evaluate every predictor on the held-out sets (SIMULATION / synthetic data).

Protocol (fixed before looking at test results):
  * hyper-parameters, epochs and output gains are chosen on VALIDATION writers only;
  * matched false correction: for each target F in {10, 25, 50} um RMS the output gain of
    each method is frozen on validation (ml/metrics.py) and applied unchanged to every
    test set; unit-gain (as designed / as trained) results are reported too;
  * residual ratio per nominal-f0 band, pooled over writers; 95 % CIs by writer
    bootstrap (2000 resamples; simulator seeds are the resampling unit of realism_sim);
  * paired differences TCN - each baseline on the same bootstrap resamples;
  * "strongest baseline" per band is picked on the TEST set among non-oracle methods,
    which favours the baselines (conservative for the network);
  * no-tremor distortion on the canonical feature course (never used in training);
  * the ICD s5 guard (ml_guard.c rules) applied to the int8 TCN with the frozen
    controller KF as reference and fallback.
Outputs: results/ml/eval_results.json, results/ml/headline_table.md,
results/ml/fig_*.png (+ fig_*.csv data twins).
Run: python3 -m ml.evaluate --model tcn_s
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time

import numpy as np
import torch

from . import common as C
from . import baselines as BL
from . import datasets as D
from . import metrics as MT
from . import models as M
from . import quantize as Q

SETS = ("test", "test_freq_holdout", "stress_tremor", "stress_writing", "realism_sim", "realism_sim_band")
SET_LABEL = {"test": "test (in-distribution)", "test_freq_holdout": "frequency holdout 7-8 Hz",
             "stress_tremor": "stress: tremor model", "stress_writing": "stress: fast writing",
             "realism_sim": "simulator realism (full band)", "realism_sim_band": "simulator realism (3-15 Hz)"}
NON_ORACLE = ("bpf", "kf", "kf_gated", "kf_ctrl_bal", "kf_ctrl_ass", "bmflc", "arls", "arls_sched")
LABEL = {"zero": "zero", "bpf": "band-pass + extrapolation", "kf": "Kalman oscillator (tuned)",
         "kf_gated": "Kalman + f-gate (tuned)", "kf_ctrl_bal": "Kalman controller, frozen balanced",
         "kf_ctrl_ass": "Kalman controller, frozen assertive", "bmflc": "BMFLC", "arls": "AR-LS (global)",
         "arls_sched": "AR-LS (f_est-scheduled)", "tcn": "TCN (float)", "tcn_int8": "TCN (int8)",
         "tcn_nofest": "TCN without f_est (ablation)", "tcn_alt": "TCN (other size)",
         "oracle_hold": "oracle: true d, no prediction", "oracle_osc": "oracle: true oscillator state"}


# ------------------------------------------------------------------ predictors
def load_predictors(model_name, alt_name=None):
    sel = json.load(open(os.path.join(C.RESULTS, "baselines_tuning.json")))["selected"]
    man = json.load(open(os.path.join(C.RESULTS, "dataset_manifest.json")))
    frozen = man["kf_frozen_250Hz"]
    arls = {}
    for fam in ("arls", "arls_sched"):
        z = np.load(os.path.join(C.RESULTS, "model", f"{fam}.npz"))
        m = BL.ARLS(p=int(z["p"]), alpha=float(z["alpha"]), sched=bool(z["sched"]))
        m.B = z["B"]
        arls[fam] = m
    model, cfg = Q.load_float(model_name)
    qm = Q.load_qmodel(os.path.join(C.RESULTS, "model", f"{model_name}_int8.npz"))

    def kfc(cfg_):
        def f(rec):
            o = BL.kf_run(BL.position(rec), **cfg_)
            return o["dhat_um"] * o["g_eff"][:, None]
        return f
    P = {
        "zero": lambda r: np.zeros((len(r["t"]), 2)),
        "bpf": lambda r: BL.bpf_run(BL.position(r), **sel["bpf"]["cfg"]),
        "kf": lambda r: BL.kf_run(BL.position(r), **sel["kf"]["cfg"])["dhat_um"],
        "kf_gated": kfc(sel["kf_gated"]["cfg"]),
        "kf_ctrl_bal": kfc(frozen["balanced"]),
        "kf_ctrl_ass": kfc(frozen["assertive"]),
        "bmflc": lambda r: BL.bmflc_run(BL.position(r), **sel["bmflc"]["cfg"]),
        "arls": lambda r: arls["arls"].predict(r),
        "arls_sched": lambda r: arls["arls_sched"].predict(r),
        "tcn": lambda r: M.predict(model, r),
        "tcn_int8": lambda r: Q.predict_int8(qm, r),
        "oracle_hold": lambda r: np.asarray(r["oracle_hold_um"], np.float64),
        "oracle_osc": lambda r: np.asarray(r["oracle_phase_um"], np.float64),
    }
    extra = {}
    for tag, nm in (("tcn_nofest", model_name + "_nofest"), ("tcn_alt", alt_name)):
        if nm and os.path.exists(os.path.join(C.RESULTS, "model", f"{nm}.pt")):
            mm, cc = Q.load_float(nm)
            P[tag] = (lambda mm_: (lambda r: M.predict(mm_, r)))(mm)
            extra[tag] = cc
    info = {"selected_baselines": {k: v["cfg"] for k, v in sel.items()}, "frozen_kf": frozen,
            "tcn_config": cfg, "int8_hash": qm["hash"], "extra_models": extra}
    return P, info, model, qm


def grouped_stats(recs, preds):
    """Per-writer stats (records of the same writer id are summed)."""
    groups = {}
    for r, p in zip(recs, preds):
        wid = r["meta"]["writer"]["writer_id"]
        s = MT.rec_stats(r, p)
        if wid in groups:
            g = groups[wid]
            for k in ("Sdd", "Sdy", "Syy", "n"):
                g[k] = g[k] + s[k]
            g["Snt"] += s["Snt"]
            g["nnt"] += s["nnt"]
        else:
            groups[wid] = s
    return MT.stack(list(groups.values())), list(groups)


def feature_distortion(recs, preds, g):
    """No-tremor distortion on the canonical feature course: RMS and max |g d_hat|
    over pen-down ticks, overall and per feature type."""
    per = {}
    tot, n = 0.0, 0
    for r, p in zip(recs, preds):
        m = MT.score_mask(r)
        y = g * np.linalg.norm(p, axis=1)
        tot += float(np.sum(y[m] ** 2))
        n += int(m.sum())
        t = r["t"] + C.H_S
        for f in r["meta"]["features"]:
            mm = m & (t >= f["t0"]) & (t <= f["t1"])
            if mm.any():
                d = per.setdefault(f["name"], {"sum2": 0.0, "n": 0, "max_um": 0.0})
                d["sum2"] += float(np.sum(y[mm] ** 2))
                d["n"] += int(mm.sum())
                d["max_um"] = max(d["max_um"], float(np.max(y[mm])))
    out = {k: {"rms_um": np.sqrt(v["sum2"] / v["n"]), "max_um": v["max_um"]} for k, v in per.items()}
    return {"rms_um": float(np.sqrt(tot / max(n, 1))), "per_feature": out}


def ml_guard(d_ml, d_kf, q_lim_um=550.0, dev_um=150.0, dev_ms=20.0, rate_mm_s=50.0):
    """docs/icd.md s5 guard rules; on reject the Kalman estimate is used."""
    n = len(d_ml)
    rej = np.zeros(n, bool)
    why = {"q_lim": 0, "deviation": 0, "rate": 0, "nan": 0}
    run = 0
    need = int(np.ceil(dev_ms * 1e-3 / C.TS))
    prev = np.zeros(2)
    for k in range(n):
        y = d_ml[k]
        if not np.all(np.isfinite(y)):
            rej[k] = True
            why["nan"] += 1
            continue
        if np.linalg.norm(y) > q_lim_um:
            rej[k] = True
            why["q_lim"] += 1
        run = run + 1 if np.linalg.norm(y - d_kf[k]) > dev_um else 0
        if run > need:
            rej[k] = True
            why["deviation"] += 1
        if np.linalg.norm(y - prev) / C.TS * 1e-3 > rate_mm_s:
            rej[k] = True
            why["rate"] += 1
        prev = y
    return np.where(rej[:, None], d_kf, d_ml), rej, why


# ------------------------------------------------------------------ figures
COLORS = None


def colors():
    from stabpen import plotstyle as ps
    return {"tcn": ps.SERIES[0], "kf": ps.SERIES[1], "bmflc": ps.SERIES[2], "arls_sched": ps.SERIES[3],
            "bpf": ps.SERIES[4], "oracle_osc": ps.SERIES[5], "tcn_int8": ps.SERIES[6], "kf_gated": ps.SERIES[7],
            "oracle_hold": ps.MUTED, "true": ps.INK}


def _csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def fig_by_band(res, path):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    meths = ["bpf", "bmflc", "kf", "arls_sched", "tcn", "oracle_osc"]
    F = f"{C.FC_HEADLINE_UM:g}"
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    xs = np.arange(len(C.BANDS))
    off = np.linspace(-0.3, 0.3, len(meths))
    rows = []
    for j, m in enumerate(meths):
        ys, lo, hi = [], [], []
        for b in range(len(C.BANDS)):
            src = "test_freq_holdout" if b == 2 else "test"
            r = res["sets"][src]["matched"][F][m]
            ys.append(r["rr_band"][b])
            lo.append(r["ci"]["rr_band_ci95"][b][0])
            hi.append(r["ci"]["rr_band_ci95"][b][1])
            rows.append([C.BAND_NAMES[b], src, m, F, ys[-1], lo[-1], hi[-1]])
        ys, lo, hi = map(np.array, (ys, lo, hi))
        ax.errorbar(xs + off[j], ys, yerr=[ys - lo, hi - ys], fmt="none", ecolor=col[m], elinewidth=1.4, capsize=0)
        ax.plot(xs + off[j], ys, label=LABEL[m], **ps.marker_kw(col[m]))
    ax.axhline(1.0, color=ps.BASELINE, lw=1.2)
    ax.text(len(C.BANDS) - 0.52, 1.015, "no correction", ha="right", va="bottom", fontsize=8, color=ps.INK2)
    ax.axvspan(1.5, 2.5, color=ps.GRID, alpha=0.35, lw=0)
    ax.set_xticks(xs, [n.replace(" (holdout)", "\n(unseen f0)") for n in C.BAND_NAMES])
    ax.set_ylabel("residual ratio  RMS(d - g d_hat) / RMS(d)")
    ax.set_xlabel("nominal tremor frequency band")
    ax.set_ylim(0, 1.15)
    ax.set_title(f"Residual disturbance at matched false correction (FC <= {F} um RMS on validation), test writers",
                 loc="left", fontsize=10)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0.0, -0.42), frameon=False)
    ps.stamp(fig, "simulation", "synthetic data, 95 % writer-bootstrap CI; 7-8 Hz from the frequency-holdout writers")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["band", "set", "method", "fc_target_um", "rr", "ci_lo", "ci_hi"], rows)


def fig_curves(res, path):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    meths = ["bpf", "bmflc", "kf", "kf_gated", "arls_sched", "tcn"]   # oracles have FC = 0 (a vertical line)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    rows = []
    for m in meths:
        sw = res["sets"]["test"]["sweep"][m]
        fc, rr = np.array(sw["fc_um"]), np.array(sw["rr_all"])
        keep = fc <= 120
        ax.plot(fc[keep], rr[keep], color=col[m], label=LABEL[m])
        op = res["sets"]["test"]["matched"][f"{C.FC_HEADLINE_UM:g}"][m]
        ax.plot([op["fc_um"]], [op["rr_all"]], **ps.marker_kw(col[m]))
        rows += [[m, g, a, b] for g, a, b in zip(sw["gain"], sw["fc_um"], sw["rr_all"])]
    ax.axvline(C.FC_HEADLINE_UM, color=ps.BASELINE, lw=1.0)
    ax.text(C.FC_HEADLINE_UM + 1, 1.08, "matching target", fontsize=8, color=ps.INK2, va="top")
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("false correction: RMS |g d_hat| on no-tremor writing (um)")
    ax.set_ylabel("residual ratio, all tremor bands pooled")
    ax.set_title("Operating curves: output gain g swept 0 -> 2 (test writers); dots = validation-frozen gain",
                 loc="left", fontsize=10)
    ax.legend(loc="lower left", fontsize=8)
    ps.stamp(fig, "simulation", "synthetic data")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["method", "gain", "fc_um", "rr_all"], rows)


def fig_shift(res, path):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    meths = ["bpf", "bmflc", "kf", "arls_sched", "tcn", "oracle_hold"]
    F = f"{C.FC_HEADLINE_UM:g}"
    sets = [s for s in SETS if s in res["sets"]]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    xs = np.arange(len(sets))
    off = np.linspace(-0.28, 0.28, len(meths))
    rows = []
    for j, m in enumerate(meths):
        ys = np.array([res["sets"][s]["matched"][F][m]["rr_all"] for s in sets])
        ci = [res["sets"][s]["matched"][F][m]["ci"]["rr_all_ci95"] for s in sets]
        lo, hi = np.array([c[0] for c in ci]), np.array([c[1] for c in ci])
        ax.errorbar(xs + off[j], ys, yerr=[ys - lo, hi - ys], fmt="none", ecolor=col[m], elinewidth=1.4)
        ax.plot(xs + off[j], ys, label=LABEL[m], **ps.marker_kw(col[m]))
        rows += [[s, m, F, y, a, b] for s, y, a, b in zip(sets, ys, lo, hi)]
    ax.axhline(1.0, color=ps.BASELINE, lw=1.2)
    ax.set_xticks(xs, [SET_LABEL[s].replace(": ", ":\n").replace(" (", "\n(") for s in sets])
    ax.set_ylim(0, 1.25)
    ax.set_ylabel("residual ratio, all bands pooled")
    ax.set_title(f"Robustness to distribution shift (gains frozen on validation for FC <= {F} um)", loc="left", fontsize=10)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0.0, -0.45), frameon=False)
    ps.stamp(fig, "simulation", "synthetic data; realism = coupled simulator housing, 12 seeds")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["set", "method", "fc_target_um", "rr_all", "ci_lo", "ci_hi"], rows)


def fig_trace(rec, preds, path, t_windows):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    fig, axes = plt.subplots(len(t_windows), 1, figsize=(8.6, 2.6 * len(t_windows)))
    rows = []
    for ax, (t0, t1, title) in zip(np.atleast_1d(axes), t_windows):
        m = (rec["t"] >= t0) & (rec["t"] <= t1)
        tt = rec["t"][m] + C.H_S
        ax.plot(tt, rec["d_tgt_um"][m, 0], color=col["true"], lw=2.0, label="true d_x(t + h)")
        for k in ("kf", "bmflc", "tcn"):
            ax.plot(tt, preds[k][m, 0], color=col[k], lw=1.6, label=LABEL[k])
        ax.set_ylabel("x disturbance (um)")
        ax.set_title(title, loc="left", fontsize=9.5)
        rows += [[float(a), float(b)] + [float(preds[k][i, 0]) for k in ("kf", "bmflc", "tcn")]
                 for a, b, i in zip(tt, rec["d_tgt_um"][m, 0], np.flatnonzero(m))]
    np.atleast_1d(axes)[-1].set_xlabel("time (s)")
    np.atleast_1d(axes)[0].legend(ncol=4, loc="upper left", fontsize=8)
    ps.stamp(fig, "simulation", "synthetic test writer; unit output gain")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["t_s", "d_true_x_um", "kf_x_um", "bmflc_x_um", "tcn_x_um"], rows)


def fig_quant(res, path):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    F = f"{C.FC_HEADLINE_UM:g}"
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    xs = np.arange(len(C.BANDS))
    rows = []
    for j, m in enumerate(("tcn", "tcn_int8")):
        ys, lo, hi = [], [], []
        for b in range(len(C.BANDS)):
            src = "test_freq_holdout" if b == 2 else "test"
            r = res["sets"][src]["matched"][F][m]
            ys.append(r["rr_band"][b])
            lo.append(r["ci"]["rr_band_ci95"][b][0])
            hi.append(r["ci"]["rr_band_ci95"][b][1])
            rows.append([C.BAND_NAMES[b], m, ys[-1], lo[-1], hi[-1]])
        ys, lo, hi = map(np.array, (ys, lo, hi))
        ax.errorbar(xs + (j - 0.5) * 0.25, ys, yerr=[ys - lo, hi - ys], fmt="none", ecolor=col[m], elinewidth=1.4)
        ax.plot(xs + (j - 0.5) * 0.25, ys, label=LABEL[m], **ps.marker_kw(col[m]))
    ax.set_xticks(xs, [n.replace(" (holdout)", "\n(unseen f0)") for n in C.BAND_NAMES])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("residual ratio")
    q = res.get("quantization_summary", {})
    ax.set_title(f"float vs int8 TCN (FC <= {F} um); RMS(float - int8) = {q.get('rms_diff_test_um', float('nan')):.2f} um",
                 loc="left", fontsize=10)
    ax.legend(loc="upper right")
    ps.stamp(fig, "simulation", "synthetic data, 95 % writer-bootstrap CI")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["band", "model", "rr", "ci_lo", "ci_hi"], rows)


def fig_features(res, path):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as ps
    ps.apply()
    col = colors()
    meths = ["bpf", "bmflc", "kf", "arls_sched", "tcn"]
    fd = res["feature_course"][f"{C.FC_HEADLINE_UM:g}"]
    feats = sorted({k for m in meths for k in fd[m]["per_feature"]})
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    xs = np.arange(len(feats))
    off = np.linspace(-0.26, 0.26, len(meths))
    rows = []
    for j, m in enumerate(meths):
        ys = np.array([fd[m]["per_feature"].get(f, {}).get("rms_um", np.nan) for f in feats])
        ax.plot(xs + off[j], ys, label=LABEL[m], **ps.marker_kw(col[m]))
        rows += [[f, m, y, fd[m]["per_feature"].get(f, {}).get("max_um", np.nan)] for f, y in zip(feats, ys)]
    ax.axhline(50.0, color=ps.BASELINE, lw=1.2)
    ax.text(len(feats) - 0.55, 51, "REQ-CTRL-005 limit (50 um RMS, whole controller)", ha="right", va="bottom",
            fontsize=8, color=ps.INK2)
    ax.set_xticks(xs, feats)
    ax.set_ylim(0, max(60.0, float(np.nanmax([r[2] for r in rows])) * 1.12))
    ax.set_ylabel("false correction RMS |g d_hat| (um)")
    ax.set_title("No-tremor distortion on the canonical feature course (never in training), frozen gains",
                 loc="left", fontsize=10)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0.0, -0.36), frameon=False, fontsize=8)
    ps.stamp(fig, "simulation", "synthetic course, 3 scales x 3 speeds x 2 sensor draws")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _csv(path.replace(".png", ".csv"), ["feature", "method", "rms_um", "max_um"], rows)


def eval_set(recs, preds, names, gains, boot_n, with_sweep=False):
    st, wids = {}, None
    for m in names:
        st[m], wids = grouped_stats(recs, preds[m])
    out = {"n_writers": len(wids), "matched": {}}
    if with_sweep:
        out["sweep"] = {m: MT.sweep(st[m], np.linspace(0.0, C.G_MAX, 41)) for m in names}
    for key, gm in gains.items():
        rows = {}
        boot, diffs = MT.bootstrap(st, gm, B=boot_n, seed=1000 + len(key),
                                   paired=[("tcn", b) for b in NON_ORACLE] + [("tcn_int8", "tcn")])
        for m in names:
            p = MT.pooled(st[m], gm[m])
            rows[m] = {"gain": gm[m], "rr_band": [float(x) for x in p["rr_band"]], "rr_all": p["rr_all"],
                       "fc_um": p["fc_um"], "n_band": [int(x) for x in p["n_band"]],
                       "d_rms_band_um": [float(x) for x in p["d_rms_band_um"]], "ci": boot[m]}
        strongest = []
        for b in range(len(C.BANDS)):
            cand = [(rows[m]["rr_band"][b], m) for m in NON_ORACLE if np.isfinite(rows[m]["rr_band"][b])]
            strongest.append(min(cand)[1] if cand else None)
        out["matched"][key] = rows
        out.setdefault("paired", {})[key] = diffs
        out.setdefault("strongest_baseline_per_band", {})[key] = strongest
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="tcn_s")
    ap.add_argument("--alt", default=None, help="other TCN size to report alongside")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--figures-only", action="store_true", help="redraw figures from eval_results.json")
    args = ap.parse_args()
    if args.figures_only:
        res = json.load(open(os.path.join(C.RESULTS, "eval_results.json")))
        fig_by_band(res, os.path.join(C.RESULTS, "fig_residual_by_band.png"))
        fig_curves(res, os.path.join(C.RESULTS, "fig_operating_curves.png"))
        fig_shift(res, os.path.join(C.RESULTS, "fig_distribution_shift.png"))
        fig_quant(res, os.path.join(C.RESULTS, "fig_quantization.png"))
        fig_features(res, os.path.join(C.RESULTS, "fig_feature_course.png"))
        headline_table(res, os.path.join(C.RESULTS, "headline_table.md"))
        return
    torch.set_num_threads(2)
    t0 = time.time()
    P, info, model, qm = load_predictors(args.model, args.alt)
    names = list(P)
    res = {"protocol": {"fc_targets_um": C.FC_TARGETS_UM, "headline_fc_um": C.FC_HEADLINE_UM, "bands": C.BAND_NAMES,
                        "warmup_s": C.WARMUP_S, "horizon_s": C.H_S, "horizon_conventional_s": C.H_S + C.TAU_NOM,
                        "gain_rule": "g = min(g_opt, F / FC_val(1), G_MAX) on validation", "g_max": C.G_MAX,
                        "bootstrap": args.boot},
           "methods": {m: LABEL.get(m, m) for m in names}, "info": info, "sets": {}}
    # ---- validation: frozen gains
    val = D.load_split("val")
    vst = {}
    for m in names:
        vst[m], _ = grouped_stats(val, [P[m](r) for r in val])
    gains = {f"{F:g}": {m: MT.select_gain(vst[m], F)[0] for m in names} for F in C.FC_TARGETS_UM}
    gains["unit"] = {m: 1.0 for m in names}
    res["gains"] = gains
    res["val"] = {m: {"rr_all_at_fc25": MT.pooled(vst[m], gains[f"{C.FC_HEADLINE_UM:g}"][m])["rr_all"],
                      "fc_g1_um": MT.pooled(vst[m], 1.0)["fc_um"]} for m in names}
    print(f"validation done {time.time() - t0:.0f} s", flush=True)
    keep_preds = {}
    test_recs = None
    for sname in SETS:
        if sname == "realism_sim_band":
            if "realism_sim" not in res["sets"]:
                continue
            # the simulator's housing disturbance (tremor run - clean run) holds 40-70 % of its power below
            # 3 Hz (slow path divergence through contact/hand dynamics) that no causal tremor estimator can
            # separate from intent; score the 3-15 Hz part as sim/pensim/evaluate.py does (zero-phase band-pass
            # of target and prediction, offline scoring only)
            from scipy import signal as sps
            sos = sps.butter(4, [3.0, 15.0], btype="band", fs=C.FS, output="sos")
            bp = lambda x: sps.sosfiltfilt(sos, np.asarray(x, np.float64), axis=0) if np.all(np.isfinite(x)) else x  # noqa: E731
            recs = [dict(r, d_tgt_um=bp(r["d_tgt_um"])) for r in realism_recs]
            preds = {m: [bp(p) for p in realism_preds[m]] for m in names}
        else:
            if not D.exists(sname):
                continue
            recs = D.load_split(sname)
            preds = {m: [P[m](r) for r in recs] for m in names}
        if sname == "test":
            keep_preds = {m: preds[m] for m in ("kf", "bmflc", "tcn", "tcn_int8", "kf_ctrl_bal", "kf_ctrl_ass")}
            test_recs = recs
        if sname == "realism_sim":
            realism_recs, realism_preds = recs, preds
        res["sets"][sname] = eval_set(recs, preds, names, gains, args.boot, with_sweep=(sname == "test"))
        F = f"{C.FC_HEADLINE_UM:g}"
        out = res["sets"][sname]
        print(f"{sname}: " + ", ".join(f"{m} {out['matched'][F][m]['rr_all']:.3f}" for m in
                                       ("kf", "kf_gated", "bmflc", "arls_sched", "tcn", "tcn_int8")), flush=True)
    # ---- no-tremor feature course
    recs = D.load_split("test_features")
    preds = {m: [P[m](r) for r in recs] for m in names}
    res["feature_course"] = {key: {m: feature_distortion(recs, preds[m], gm[m]) for m in names}
                             for key, gm in gains.items()}
    # ---- guard on the int8 TCN (test writers)
    g25 = gains[f"{C.FC_HEADLINE_UM:g}"]
    guard = {}
    for ref in ("kf_ctrl_bal", "kf_ctrl_ass"):
        sts, nrej, ntr, whys = [], 0, 0, {}
        for r, pm, pk in zip(test_recs, keep_preds["tcn_int8"], keep_preds[ref]):
            gd, rej, why = ml_guard(pm * g25["tcn_int8"], pk)
            m = MT.score_mask(r)
            nrej += int(np.sum(rej & m))
            ntr += int(m.sum())
            for k, v in why.items():
                whys[k] = whys.get(k, 0) + v
            sts.append(MT.rec_stats(r, gd))
        stg = MT.stack(sts)
        p = MT.pooled(stg, 1.0)
        guard[ref] = {"reject_fraction_scored": nrej / max(ntr, 1), "reasons_ticks": whys,
                      "rr_band": [float(x) for x in p["rr_band"]], "rr_all": p["rr_all"], "fc_um": p["fc_um"]}
    res["guard_int8_test"] = guard
    q = json.load(open(C.result_json("quantization", args.model)))   # quantization[_<model>].json
    res["quantization_summary"] = {"rms_diff_test_um": q["splits"]["test"]["rms_float_minus_int8_um"],
                                   "hash": q["hash_sha256"]}
    res["meta"] = C.meta(seeds={"bootstrap": "1000 + len(gain key)"}, extra={"elapsed_s": time.time() - t0})
    write_compact(os.path.join(C.RESULTS, "eval_results.json"), res)
    # ---- figures
    fig_by_band(res, os.path.join(C.RESULTS, "fig_residual_by_band.png"))
    fig_curves(res, os.path.join(C.RESULTS, "fig_operating_curves.png"))
    fig_shift(res, os.path.join(C.RESULTS, "fig_distribution_shift.png"))
    fig_quant(res, os.path.join(C.RESULTS, "fig_quantization.png"))
    fig_features(res, os.path.join(C.RESULTS, "fig_feature_course.png"))
    # example trace: a test writer with tremor in 4-6 Hz and no-tremor writing
    best = None
    for i, r in enumerate(test_recs):
        segs = r["meta"]["segments"]
        if segs and 4.5 <= segs[0]["spec"]["f0"] < 6.0 and segs[0]["spec"]["amp_pk"] > 2.5e-4:
            off = [(a["t1"], b["t0"]) for a, b in zip(segs[:-1], segs[1:]) if b["t0"] - a["t1"] > 3.0]
            if off:
                best = (i, segs[0], off[0])
                break
    if best:
        i, seg, (a, b) = best
        r = test_recs[i]
        pr = {k: keep_preds[k][i] for k in ("kf", "bmflc", "tcn")}
        tm = seg["t0"] + 2.0
        fig_trace(r, pr, os.path.join(C.RESULTS, "fig_example_trace.png"),
                  [(tm, tm + 1.5, f"{r['meta']['writer']['writer_id']}: tremor segment, nominal f0 "
                                  f"{seg['spec']['f0']:.1f} Hz, {seg['spec']['amp_pk'] * 1e3:.2f} mm peak"),
                   (a + 0.6, a + 2.1, "same writer, no tremor: any output is false correction")])
    headline_table(res, os.path.join(C.RESULTS, "headline_table.md"))
    print(f"done {time.time() - t0:.0f} s", flush=True)


def _round(o, sig=5):
    if isinstance(o, float):
        return float(f"{o:.{sig}g}") if np.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _round(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v, sig) for v in o]
    if isinstance(o, np.ndarray):
        return _round(o.tolist(), sig)
    if isinstance(o, (np.floating,)):
        return _round(float(o), sig)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def write_compact(path, res):
    """Floats rounded to 5 significant digits (NaN -> null), one JSON line per top-level key."""
    r = _round(res)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in r.items())
                + "\n}\n")


def headline_table(res, path):
    F = f"{C.FC_HEADLINE_UM:g}"
    meths = ["zero", "bpf", "kf", "kf_gated", "kf_ctrl_bal", "bmflc", "arls", "arls_sched", "tcn", "tcn_int8",
             "oracle_hold", "oracle_osc"]
    meths = [m for m in meths if m in res["sets"]["test"]["matched"][F]]
    lines = [f"Residual ratio at matched false correction (gain frozen on validation for FC <= {F} um RMS). "
             "Test writers; 7-8 Hz row = frequency-holdout writers. [95 % writer-bootstrap CI]. "
             "SIMULATION / synthetic data.", "",
             "| band | " + " | ".join(LABEL[m] for m in meths) + " |", "|---|" + "---|" * len(meths)]
    for b, bn in enumerate(C.BAND_NAMES):
        src = "test_freq_holdout" if b == 2 else "test"
        cells = []
        for m in meths:
            r = res["sets"][src]["matched"][F][m]
            v, (lo, hi) = r["rr_band"][b], r["ci"]["rr_band_ci95"][b]
            cells.append(f"{v:.2f} [{lo:.2f}, {hi:.2f}]")
        lines.append(f"| {bn} | " + " | ".join(cells) + " |")
    cells = [f"{res['sets']['test']['matched'][F][m]['fc_um']:.1f}" for m in meths]
    lines.append("| FC on test (um RMS) | " + " | ".join(cells) + " |")
    cells = [f"{res['sets']['test']['matched'][F][m]['gain']:.2f}" for m in meths]
    lines.append("| frozen gain g | " + " | ".join(cells) + " |")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
