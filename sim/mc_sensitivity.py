#!/usr/bin/env python3
"""Which uncertain parameters drive the outcomes?  Rank correlations on the
Monte Carlo sweep (results/sim/sweeps/monte_carlo.csv).

Evidence status: SIMULATION (exploratory parameter ranges from
config/parameters.yaml; the ranges are declarations, not population data, so
the correlations rank sensitivities inside those ranges only).

For each outcome (oracle residual ratio, Kalman-assertive ratio, copper loss,
coil temperature) the Spearman correlation with each sampled parameter is
reported with a bootstrap 90 % interval.  Parameters whose |rho| interval
excludes 0.2 are flagged as the ones experiments must pin down first.
Outputs results/sim/mc_sensitivity.json and fig_mc_sensitivity.png.
Run: python3 sim/mc_sensitivity.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stabpen import plotstyle, provenance  # noqa: E402

OUTCOMES = {"oracle_ratio": "oracle residual ratio", "kf_asr_ratio": "Kalman (assertive) ratio",
            "P_cu_neutral_W": "copper loss, neutral", "T_coil_max_C": "peak coil temperature"}


def main():
    d = pd.read_csv(os.path.join(ROOT, "results", "sim", "sweeps", "monte_carlo.csv"))
    params = [c for c in d.columns if "." in c]
    rng = np.random.default_rng(5)
    res = {}
    for oc in OUTCOMES:
        v = d[[oc] + params].dropna()
        rows = {}
        for p in params:
            rho = stats.spearmanr(v[p], v[oc]).statistic
            boots = []
            for _ in range(400):
                idx = rng.integers(0, len(v), len(v))
                boots.append(stats.spearmanr(v[p].values[idx], v[oc].values[idx]).statistic)
            lo, hi = np.percentile(boots, [5, 95])
            rows[p] = {"rho": float(rho), "ci90": [float(lo), float(hi)],
                       "important": bool(min(abs(lo), abs(hi)) > 0.2 and np.sign(lo) == np.sign(hi))}
        res[oc] = {"n": int(len(v)), "by_parameter": dict(sorted(rows.items(), key=lambda kv: -abs(kv[1]["rho"])))}
    meta = provenance.metadata("simulation (Monte Carlo over declared ranges; Spearman rank correlation)")
    provenance.write_json(os.path.join(ROOT, "results", "sim", "mc_sensitivity.json"), {"meta": meta, "outcomes": res})
    for oc, r in res.items():
        top = [(p, round(x["rho"], 2)) for p, x in list(r["by_parameter"].items())[:5]]
        print(oc, top)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(OUTCOMES), figsize=(14.5, 4.2), sharey=True)
    order = sorted(params, key=lambda p: -max(abs(res[o]["by_parameter"][p]["rho"]) for o in OUTCOMES))
    y = np.arange(len(order))
    for ax, (oc, label) in zip(axs, OUTCOMES.items()):
        rho = [res[oc]["by_parameter"][p]["rho"] for p in order]
        lo = [res[oc]["by_parameter"][p]["ci90"][0] for p in order]
        hi = [res[oc]["by_parameter"][p]["ci90"][1] for p in order]
        cols = [plotstyle.SERIES[0] if r >= 0 else plotstyle.SERIES[1] for r in rho]
        ax.barh(y, rho, color=cols, height=0.6, edgecolor=plotstyle.SURFACE)
        ax.hlines(y, lo, hi, color=plotstyle.INK2, lw=1.0)
        ax.axvline(0, color=plotstyle.INK2, lw=0.8)
        ax.set_xlim(-1, 1)
        ax.set_title(label, loc="left", fontsize=9.5)
        ax.set_xlabel("Spearman rho (90 % bootstrap)")
    axs[0].set_yticks(y, [p.split(".", 1)[1] for p in order], fontsize=7.5)
    axs[0].invert_yaxis()
    plotstyle.stamp(fig, "simulation", "160 Monte Carlo samples over declared (not population) ranges; blue positive, orange negative")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "results", "sim", "fig_mc_sensitivity.png"))


if __name__ == "__main__":
    main()
