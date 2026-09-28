"""Figures of the fusion study from results/fusion/*.json (each with a CSV data twin and an evidence stamp)."""
from __future__ import annotations

import csv
import json
import os

import numpy as np

from . import RESULTS

LABELS = {"oracle": "oracle (physical limit)", "oracle_band": "tremor-band oracle (non-causal)",
          "kfosc_internal": "frozen Kalman (core)", "kfosc_port": "frozen Kalman (external port)",
          "kfosc_p1": "Kalman, retuned on P1", "akf": "acceleration Kalman (AKF)", "akf_120": "AKF, 120 Hz page sensor",
          "kfosc_port_120": "frozen Kalman, 120 Hz page sensor", "bmflc": "BMFLC on acceleration", "wflc": "WFLC on acceleration",
          "gru": "learned GRU", "gru_120": "learned GRU, 120 Hz page", "akf_personal": "AKF, personalised", "neutral": "no correction",
          "akf_robust": "AKF, robust tuning", "wflc_robust": "WFLC, robust tuning", "kfosc_p1_lp": "Kalman, retuned + low-pass",
          "kfosc_port_matched": "frozen Kalman (port, core IMU)"}


def _load(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p)) if os.path.exists(p) else None


def _csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def fig_ratio(grid):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    series = [k for k in ("oracle", "oracle_band", "kfosc_internal", "akf", "akf_robust", "gru", "akf_personal") if k in grid["summary"]]
    fig, axs = plt.subplots(1, 3, figsize=(10.2, 3.7), sharey=True)
    rows = []
    for ax, amp in zip(axs, (0.1, 0.3, 0.5)):
        for i, lab in enumerate(series):
            d = grid["summary"][lab]["ratio"]
            f = sorted(float(k.split("Hz")[0]) for k in d if k.endswith(f"_{amp:g}mm"))
            y = [d[f"{x:g}Hz_{amp:g}mm"]["mean"] for x in f]
            sd = [d[f"{x:g}Hz_{amp:g}mm"]["sd"] for x in f]
            ls = "--" if lab == "oracle_band" else "-"
            ax.plot(f, y, color=S[i], lw=2.0, ls=ls, label=LABELS.get(lab, lab))
            ax.plot(f, y, **plotstyle.marker_kw(S[i]))
            rows += [[lab, x, amp, m, s] for x, m, s in zip(f, y, sd)]
        ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
        ax.set_title(f"tremor {amp:g} mm peak", loc="left", fontsize=9.5)
        ax.set_xlabel("Tremor frequency (Hz)")
    axs[0].set_ylabel("Ink error / no correction")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=8)
    fig.suptitle("Pencil P1: ink error ratio per estimator, mean of test seeds 200-203 (lower is better)", x=0.01, ha="left", fontsize=10)
    plotstyle.stamp(fig, "simulation", "model P1, synthetic handwriting and tremor; sensor models with noise and latency; not measured")
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(os.path.join(RESULTS, "fig_ratio_vs_frequency.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_ratio_vs_frequency.csv"), ["estimator", "f0_hz", "amp_mm", "ratio_mean", "ratio_sd"], rows)


def fig_overview(grid):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    labs = [k for k in ("oracle", "oracle_band", "kfosc_internal", "kfosc_port", "kfosc_p1", "kfosc_p1_lp", "bmflc", "wflc", "wflc_robust",
                        "akf", "akf_robust", "akf_personal", "gru", "kfosc_port_120", "akf_120", "gru_120")
            if k in grid["summary"] and "overall" in grid["summary"][k]]
    r = [grid["summary"][k]["overall"]["ratio_mean"] for k in labs]
    b = [grid["summary"][k]["overall"]["band_ratio_mean"] for k in labs]
    dist = [grid["distortion_um"].get(k, {}).get("mean", np.nan) for k in labs]
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 1.2 + 0.33 * len(labs)), sharey=True)
    y = np.arange(len(labs))[::-1]
    for ax, vals, title in ((axs[0], r, "Ink error ratio, mean of 60 conditions"), (axs[1], b, "3-15 Hz band ratio, mean"),
                            (axs[2], dist, "Distortion on tremor-free writing (um)")):
        ax.barh(y, vals, color=S[0], height=0.62)
        for yy, v in zip(y, vals):
            if np.isfinite(v):
                ax.text(v, yy, f" {v:.2f}" if title != "Distortion on tremor-free writing (um)" else f" {v:.0f}", va="center",
                        fontsize=7.5, color=plotstyle.INK2)
        ax.set_title(title, loc="left", fontsize=9.5)
        if "ratio" in title:
            ax.axvline(1.0, color=plotstyle.MUTED, lw=1.0)
    axs[0].set_yticks(y)
    axs[0].set_yticklabels([LABELS.get(k, k) for k in labs], fontsize=8)
    plotstyle.stamp(fig, "simulation", "model P1; oracles are references, not estimators; not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_estimators_overview.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_estimators_overview.csv"), ["estimator", "ratio_mean", "band_ratio_mean", "distortion_um"],
         [[k, a, c, d] for k, a, c, d in zip(labs, r, b, dist)])


def fig_leverarm(sens):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    comps = ["none", "nose", "dual", "gyro", "ideal"]
    names = {"none": "board IMU, no compensation", "nose": "nose accelerometer only", "dual": "nose + board accelerometers",
             "gyro": "board 6-axis IMU, gyro-compensated", "ideal": "translation-only IMU (reference)"}
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0))
    rows = []
    ol = sens["leverarm_open_loop"]["rows"]
    for i, c in enumerate(comps):
        rr = sorted({r["rho"] for r in ol})
        y = [np.mean([r["band_error_rel"] for r in ol if r["comp"] == c and r["rho"] == rho]) for rho in rr]
        axs[0].plot(rr, y, color=S[i], label=names[c])
        axs[0].plot(rr, y, **plotstyle.marker_kw(S[i]))
        rows += [["open_loop", c, rho, v] for rho, v in zip(rr, y)]
    axs[0].set_xlabel("pen rotation rho (displacement 100 mm up the barrel per unit nib displacement)")
    axs[0].set_ylabel("tremor-band error of nib acceleration / true")
    axs[0].set_title("Open loop: what the IMU reports for the nib", loc="left", fontsize=9.5)
    axs[0].legend(fontsize=7.5)
    cl = sens["leverarm_closed_loop"]["summary"]
    x = np.arange(len(comps))
    for j, page in enumerate(("1k", "120")):
        vals = [cl.get(f"{page}_{c}_rho0.5", {}).get("ratio_mean", np.nan) for c in comps]
        axs[1].bar(x + (j - 0.5) * 0.38, vals, 0.36, color=S[j], label={"1k": "page sensor 1 kHz / 2 ms", "120": "page sensor 120 Hz / 10 ms"}[page])
        rows += [["closed_loop_rho0.5", c, page, v] for c, v in zip(comps, vals)]
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(["none", "nose only", "dual", "gyro", "ideal"], fontsize=8)
    axs[1].axhline(1.0, color=plotstyle.MUTED, lw=1.0)
    axs[1].set_ylabel("AKF ink error ratio (4/8/12 Hz, 0.3 mm, tuning seeds)")
    axs[1].set_title("Closed loop at rho = 0.5", loc="left", fontsize=9.5)
    axs[1].legend(fontsize=7.5)
    plotstyle.stamp(fig, "simulation", "P1 housing motion + kinematic pen rotation (ASSUMPTION); IMU 100 mm, nose 17 mm from the nib")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_leverarm.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_leverarm.csv"), ["panel", "compensation", "rho_or_page", "value"], rows)


def fig_snr(sens):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    from . import parts as PT
    plotstyle.apply()
    S = plotstyle.SERIES
    f = np.logspace(np.log10(2.0), np.log10(20.0), 60)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    rows = []
    for i, name in enumerate(("LSM6DSV16X", "ICM-45686", "BMA530", "ADXL367", "BMI323")):
        nd = PT.PARTS[name].acc_nd()
        y = [PT.displacement_noise_um(nd, x) for x in f]
        ax.loglog(f, y, color=S[i], label=f"{name} ({PT.PARTS[name].acc_nd_ug:g} ug/rtHz)")
        rows += [[name, x, v] for x, v in zip(f, y)]
    for j, (s, r, lab) in enumerate(((3e-6, 1000.0, "page sensor 3 um @ 1 kHz"), (3e-6, 120.0, "page sensor 3 um @ 120 Hz"))):
        v = PT.page_sensor_nd_um(s, r)
        ax.loglog(f, [v] * len(f), color=plotstyle.INK2, lw=1.2, ls=["--", ":"][j], label=lab)
        rows.append([lab, "flat", v])
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("displacement noise density (um/sqrt(Hz))")
    ax.set_title("Displacement-equivalent noise: accelerometers vs page sensor", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5)
    plotstyle.stamp(fig, "calculation", "datasheet noise densities (MFR, OPT-37..42); page-sensor noise ASSUMPTION")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_sensor_noise.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_sensor_noise.csv"), ["sensor", "f_hz", "um_per_rtHz"], rows)


def fig_template(ctx):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0))
    rows = []
    sp = ctx["template_error_spectrum_writer0"]
    for i, c in enumerate(("ai_correct", "ai_predicted", "wrong_letter")):
        f = np.array(sp[c]["f_hz"]); p = np.array(sp[c]["psd_um2_per_hz"])
        m = (f > 0) & (f <= 40)
        axs[0].semilogy(f[m], p[m], color=S[i], label={"ai_correct": "AI template, correct letter", "ai_predicted": "AI-predicted template",
                                                         "wrong_letter": "wrong letter"}[c])
        rows += [["psd", c, a, b] for a, b in zip(f[m], p[m])]
    axs[0].axvspan(3, 15, color=plotstyle.GRID, alpha=0.6, lw=0)
    axs[0].set_xlabel("frequency along the written stroke (Hz)")
    axs[0].set_ylabel("cross-track template error PSD (um^2/Hz)")
    axs[0].set_title("Template error spectrum (writer 0; shaded: 3-15 Hz)", loc="left", fontsize=9.5)
    axs[0].legend(fontsize=7.5)
    te = ctx["template_error"]
    keys = [("total", "total"), ("after_offset", "after per-letter offset"), ("after_affine", "after per-letter affine"),
            ("band_3_15Hz_rms_um", "3-15 Hz band")]
    conds = ["ai_correct", "ai_predicted", "wrong_letter"]
    x = np.arange(len(keys))
    for i, c in enumerate(conds):
        v = [te[c][k]["mean"] for k, _ in keys]
        axs[1].bar(x + (i - 1) * 0.27, v, 0.25, color=S[i], label=c.replace("_", " "))
        rows += [["rms", c, k, vv] for (k, _), vv in zip(keys, v)]
    axs[1].set_xticks(x)
    axs[1].set_xticklabels([n for _, n in keys], fontsize=8)
    axs[1].set_ylabel("RMS template error (um)")
    axs[1].set_title("Where the template error lives (6 writers x 4 f0)", loc="left", fontsize=9.5)
    axs[1].legend(fontsize=7.5)
    plotstyle.stamp(fig, "simulation", "aiguide glyph writers; templates from the n-gram predictor and style estimator")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_template_error.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_template_error.csv"), ["panel", "condition", "x", "value"], rows)


def fig_context(ctx):
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    cases = [("neutral", "no correction"), ("neutral_no_tremor", "no tremor"), ("oracle_disturbance", "disturbance oracle"),
             ("kfosc_internal", "frozen Kalman"), ("pull_oracle", "pull: oracle tpl"), ("pull_ai_correct", "pull: AI correct"),
             ("pull_ai_predicted", "pull: AI predicted"), ("akf", "AKF (grid tuning)"), ("akf_robust", "AKF (robust tuning)"),
             ("wflc", "WFLC"), ("gru", "GRU, no template"), ("ctx_none", "prior: none (same filter)"),
             ("ctx_oracle", "prior: oracle tpl"), ("ctx_ai_correct", "prior: AI correct"), ("ctx_ai_predicted", "prior: AI predicted"),
             ("ctx_wrong_letter_gated", "prior: wrong, gated"), ("ctx_wrong_letter_full", "prior: wrong, full")]
    cases = [c for c in cases if c[0] in ctx["summary"]]
    fig, axs = plt.subplots(1, 4, figsize=(15.5, 5.4), sharey=True)
    y = np.arange(len(cases))[::-1]
    rows = []
    for ax, key, title in ((axs[0], "wo_path_rms_um", "Path distance to intended,\nwriting only (um)"),
                           (axs[1], "ratio", "Ink error ratio\nvs no correction"),
                           (axs[2], "wo_recognition_accuracy", "Recognition,\nwriting only"),
                           (axs[3], "distortion_um", "Distortion on the same writing\nwithout tremor (um)")):
        v = [ctx["summary"][c].get(key, {}).get("mean", np.nan) for c, _ in cases]
        sd = [ctx["summary"][c].get(key, {}).get("sd", np.nan) for c, _ in cases]
        ax.barh(y, v, xerr=sd, color=S[0], height=0.62, error_kw={"lw": 0.7, "ecolor": plotstyle.INK2, "capsize": 1.5})
        ax.set_title(title, loc="left", fontsize=9)
        rows += [[c, key, a, b] for (c, _), a, b in zip(cases, v, sd)]
    axs[0].set_yticks(y)
    axs[0].set_yticklabels([n for _, n in cases], fontsize=8)
    plotstyle.stamp(fig, "simulation", "aiguide writers 0-5, 0.3 mm tremor 4-10 Hz, pencil model P1; mean +- SD over 24 scenarios")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_context.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_context.csv"), ["case", "metric", "mean", "sd"], rows)


def fig_jitter(sens):
    if "jitter_check" not in sens:
        return
    from stabpen import plotstyle
    import matplotlib.pyplot as plt
    plotstyle.apply()
    S = plotstyle.SERIES
    J = sens["jitter_check"]["summary"]
    labs = list(J.keys())
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.6), sharey=True)
    y = np.arange(len(labs))[::-1]
    for ax, key, title in ((axs[0], "ratio_mean", "Ink error ratio"), (axs[1], "P_rail_classB_mW_mean", "Rail power, class-B (mW)")):
        v = [J[k][key] for k in labs]
        ax.barh(y, v, color=S[1], height=0.6)
        ax.set_title(title, loc="left", fontsize=9.5)
    axs[0].set_yticks(y)
    axs[0].set_yticklabels(labs, fontsize=8)
    plotstyle.stamp(fig, "simulation", "tremor-band oracle plus band-limited jitter, tuning seeds 5000-5001, 8 Hz 0.3 mm")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig_estimate_jitter.png"))
    plt.close(fig)
    _csv(os.path.join(RESULTS, "fig_estimate_jitter.csv"), ["case", "ratio_mean", "P_rail_classB_mW_mean"],
         [[k, J[k]["ratio_mean"], J[k]["P_rail_classB_mW_mean"]] for k in labs])


def make_all():
    g = _load("grid.json")
    if g:
        fig_ratio(g)
        fig_overview(g)
    s = _load("sensors.json")
    if s:
        fig_leverarm(s)
        fig_snr(s)
        fig_jitter(s)
    c = _load("context.json")
    if c:
        fig_template(c)
        fig_context(c)
