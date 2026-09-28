"""Figures of the tracker study (results/opt/fig_tr_*.png, each with a CSV data twin).  SIMULATION.

stabpen.plotstyle: the repository's validated categorical order (fixed, never cycled), 2 px lines, >= 8 px markers
with a surface ring, one y-axis per panel, hairline grid, ink-coloured text, a legend for every multi-series panel,
an evidence-status stamp on every figure.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Sequence

import numpy as np

from . import RESULTS

MARKERS = ["o", "s", "^", "D", "v", "P", "X", "h"]


def _csv(name: str, header: Sequence[str], rows: List[Sequence]):
    with open(os.path.join(RESULTS, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def fig_ratio_vs_frequency(grid_summary: Dict, labels: Sequence[tuple], name: str = "fig_tr_ratio_vs_frequency"):
    """Tremor-band ratio vs tremor frequency, one panel per amplitude.  labels: [(key, legend text)]."""
    from stabpen import plotstyle as PSt
    import matplotlib.pyplot as plt
    PSt.apply()
    S = PSt.SERIES
    amps = (0.1, 0.3, 0.5)
    f0s = (4.0, 6.0, 8.0, 10.0, 12.0)
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), sharey=True)
    rows = []
    for j, a in enumerate(amps):
        ax = axes[j]
        for i, (key, text) in enumerate(labels):
            by = grid_summary.get(key, {}).get("by_condition", {})
            y = [by.get(f"{f:g}Hz_{a:g}mm", {}).get("band_ratio", {}).get("mean", np.nan) for f in f0s]
            sd = [by.get(f"{f:g}Hz_{a:g}mm", {}).get("band_ratio", {}).get("sd", np.nan) for f in f0s]
            col = S[i % len(S)] if key != "oracle_band" else PSt.MUTED
            ls = "-" if key != "oracle_band" else "--"
            ax.plot(f0s, y, color=col, lw=2.0, ls=ls, label=text if j == 0 else None, zorder=3)
            kw = PSt.marker_kw(col)
            kw["marker"] = MARKERS[i % len(MARKERS)]
            ax.plot(f0s, y, **kw, zorder=4)
            for f, v, s in zip(f0s, y, sd):
                rows.append([key, a, f, v, s])
        ax.axhline(1.0, color=PSt.MUTED, lw=1.0)
        ax.set_title(f"tremor {a:g} mm peak")
        ax.set_xlabel("tremor frequency (Hz)")
        ax.set_xticks(f0s)
    axes[0].set_ylabel("tremor-band (3-15 Hz) ink-error ratio\n(1 = no benefit, lower is better)")
    fig.legend(loc="upper center", ncol=min(4, len(labels)), bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    PSt.stamp(fig, "simulation", "model P1, test seeds 200-203, mean of 4; synthetic handwriting and tremor; not measured")
    fig.savefig(os.path.join(RESULTS, name + ".png"))
    plt.close(fig)
    _csv(name + ".csv", ["label", "amp_mm", "f0_hz", "band_ratio_mean", "band_ratio_sd"], rows)


def fig_pareto(points: List[Dict], others: List[Dict], name: str = "fig_tr_pareto"):
    """Band ratio (P1 test grid) against false correction: distortion on the grid's writing (left) and on the
    sharp glyph writers' tremor-free writing (right).  points: the lambda sweep (dicts with lam, band, dist_grid,
    dist_glyph); others: previous sets and learned trackers (label, band, dist_grid, dist_glyph)."""
    from stabpen import plotstyle as PSt
    import matplotlib.pyplot as plt
    PSt.apply()
    S = PSt.SERIES
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), sharey=True)
    rows = []
    for j, (key, xl) in enumerate((("dist_grid", "distortion on tremor-free grid writing (um RMS)"),
                                   ("dist_glyph", "distortion on tremor-free glyph writing (um RMS)"))):
        ax = axes[j]
        for chain_i, chain in enumerate(sorted({p["chain"] for p in points})):
            pc = sorted([p for p in points if p["chain"] == chain], key=lambda p: p["lam"])
            x = [p[key] for p in pc]; y = [p["band"] for p in pc]
            col = S[chain_i]
            ax.plot(x, y, color=col, lw=2.0, label=f"adjoint-tuned AKF, chain {chain} (λ_fc sweep, labels = λ_fc)" if j == 0 else None, zorder=3)
            kw = PSt.marker_kw(col)
            ax.plot(x, y, **kw, zorder=4)
            for p in pc:
                ax.annotate(f"{p['lam']:g}", (p[key], p["band"]), xytext=(4, 4), textcoords="offset points", fontsize=7,
                            color=PSt.INK2)
        for i, o in enumerate(others):
            # the other trackers in ink: shape and a direct label carry the identity (a scatter keeps colour to 2 series)
            ax.plot([o[key]], [o["band"]], marker=MARKERS[(2 + i) % len(MARKERS)], markersize=8, markerfacecolor=PSt.INK2,
                    markeredgecolor=PSt.SURFACE, markeredgewidth=1.6, linestyle="none", label=o["label"] if j == 0 else None,
                    zorder=5)
            dx, dy, ha = o.get("offset", (5, -9, "left"))
            ax.annotate(o["short"], (o[key], o["band"]), xytext=(dx, dy), textcoords="offset points", fontsize=7.5, color=PSt.INK,
                        ha=ha)
        ax.set_xlabel(xl)
        ax.set_xscale("log")
        from matplotlib.ticker import FuncFormatter, LogLocator
        ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    for p in points:
        rows.append([f"chain {p['chain']}", p["lam"], p["band"], p["dist_grid"], p["dist_glyph"]])
    for o in others:
        rows.append([o["label"], "", o["band"], o["dist_grid"], o["dist_glyph"]])
    axes[0].set_ylabel("tremor-band ink-error ratio, P1 test grid\n(lower is better)")
    fig.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0.03, 1, 0.86))
    PSt.stamp(fig, "simulation", "model P1 test seeds 200-203 (60 conditions) and aiguide test writers 0-5 (24 scenarios); not measured")
    fig.savefig(os.path.join(RESULTS, name + ".png"))
    plt.close(fig)
    _csv(name + ".csv", ["series", "lambda_fc", "band_ratio_test_grid", "distortion_grid_um", "distortion_glyph_um"], rows)


def fig_training(sweep_points: List[Dict], learned: Dict, name: str = "fig_tr_training"):
    """(a) validation objective (exact gates) along the two lambda_fc chains of the adjoint-tuned AKF; (b, c) the
    learned models per epoch on the same validation measures: 3-15 Hz residual ratio and false correction."""
    from stabpen import plotstyle as PSt
    import matplotlib.pyplot as plt
    PSt.apply()
    S = PSt.SERIES
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.1))
    rows = []
    ax = axes[0]
    chains = sorted({p["chain"] for p in sweep_points})
    for ci, chain in enumerate(chains):
        pc = sorted([p for p in sweep_points if p["chain"] == chain], key=lambda p: p["order"])
        x0 = 0
        xs, ys = [], []
        for p in pc:
            for h in p["val_hist"]:
                xs.append(x0 + h[0]); ys.append(h[1])
                rows.append([f"AKF chain {chain}", "objective", p["lam"], x0 + h[0], h[1]])
            x0 += p["iters"]
            if ci == 0:
                ax.axvline(x0, color=PSt.GRID, lw=1.0)
        ax.plot(xs, ys, color=S[ci], lw=2.0, label=f"AKF chain {chain}")
    ax.set_xlabel("Adam iteration (full batch);\nλ_fc = 0.01, 0.03, 0.1, 0.3, 1 between the grey lines")
    ax.set_ylabel("validation objective (exact gates)")
    ax.set_title("(a) adjoint-tuned AKF", loc="left")
    ax.legend(loc="upper left")
    series = (("gru", "GRU, tremor-band target", 2), ("hybrid", "AKF + learned gate", 3))
    for ai_, (q, ylab, title) in enumerate((("rr_band", "3-15 Hz residual ratio (open loop)", "(b) learned models: tremor band"),
                                             ("fc_w_um", "false correction, tremor-free writing (um RMS)", "(c) learned models: false correction"))):
        ax = axes[1 + ai_]
        for k, text, ci in series:
            if k not in learned:
                continue
            h = learned[k]["history"]
            for vs, ls, vtext in (("val", "-", "validation pairs"), ("tune_grid", "--", "tuning seeds 5004-5007")):
                x = [e["epoch"] for e in h if vs in e["val"]]
                y = [e["val"][vs].get(q) for e in h if vs in e["val"]]
                if not x:
                    continue
                ax.plot(x, y, color=S[ci], lw=2.0, ls=ls, label=f"{text}, {vtext}")
                kw = PSt.marker_kw(S[ci]); kw["marker"] = MARKERS[ci]
                ax.plot(x, y, **kw)
                rows += [[text, f"{q} {vs}", "", e_, v] for e_, v in zip(x, y)]
        ax.set_xlabel("epoch")
        ax.set_ylabel(ylab)
        ax.set_title(title, loc="left")
    h_, l_ = axes[1].get_legend_handles_labels()
    fig.legend(h_, l_, loc="upper center", ncol=2, bbox_to_anchor=(0.66, 1.0), fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.86))
    PSt.stamp(fig, "simulation", "validation: fusion val specs (24 pairs), tuning seeds 5004-5007, aiguide writers 100-105; not measured")
    fig.savefig(os.path.join(RESULTS, name + ".png"))
    plt.close(fig)
    _csv(name + ".csv", ["series", "measure", "lambda_fc", "iteration_or_epoch", "value"], rows)


def fig_personal(pers: Dict, pers_fc: Dict = None, name: str = "fig_tr_personal"):
    """Band ratio per test condition at 0.3 mm: population, 12-candidate choice, adjoint refinement (with and
    without the false-correction term)."""
    from stabpen import plotstyle as PSt
    import matplotlib.pyplot as plt
    PSt.apply()
    S = PSt.SERIES
    g = dict(pers["test"]["grid_summary"])
    dist = dict(pers["test"]["distortion_um"])
    series = [("akf_robust", "population set (robust AKF)"), ("akf_personal", "personal: 12-candidate choice"),
              ("akf_personal_adjoint", "personal: adjoint, calibration fit only")]
    if pers_fc:
        g.update(pers_fc["test"]["grid_summary"])
        dist["akf_personal_adjoint_fc"] = pers_fc["test"]["distortion_um"]
        series.append(("akf_personal_adjoint_fc", "personal: adjoint, fit + false-correction term"))
    series.append(("oracle_band", "tremor-band oracle (not causal)"))
    f0s = (4.0, 6.0, 8.0, 10.0, 12.0)
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    rows = []
    for i, (lab, text) in enumerate(series):
        if lab in dist:
            text = f"{text} (distortion {dist[lab]:.0f} um)"
        by = g.get(lab, {}).get("by_condition", {})
        y = [by.get(f"{f:g}Hz_0.3mm", {}).get("band_ratio", {}).get("mean", np.nan) for f in f0s]
        col = S[i] if lab != "oracle_band" else PSt.MUTED
        ax.plot(f0s, y, color=col, lw=2.0, ls="-" if lab != "oracle_band" else "--", label=text)
        kw = PSt.marker_kw(col); kw["marker"] = MARKERS[i]
        ax.plot(f0s, y, **kw)
        rows += [[lab, f, v] for f, v in zip(f0s, y)]
    ax.axhline(1.0, color=PSt.MUTED, lw=1.0)
    ax.set_xlabel("tremor frequency (Hz), 0.3 mm peak")
    ax.set_ylabel("tremor-band ink-error ratio")
    ax.set_xticks(f0s)
    ax.set_ylim(0.0, 1.1)
    fig.legend(loc="upper center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0.04, 1, 0.84))
    PSt.stamp(fig, "simulation", "P1 test seeds 200-203, mean of 4; distortion: closed loop on tremor-free writing, 6 and 10 Hz calibrations; not measured")
    fig.savefig(os.path.join(RESULTS, name + ".png"))
    plt.close(fig)
    _csv(name + ".csv", ["label", "f0_hz", "band_ratio_mean"], rows)
