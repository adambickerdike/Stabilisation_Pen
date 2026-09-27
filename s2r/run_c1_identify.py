#!/usr/bin/env python3
"""C1 part A: blind identification of hidden plants at protocol settings.

15 hidden plants (10 inside the declared ranges, 5 with about 40 % of their keys
pushed outside) are measured on the virtual bench in the protocol order
(EXP-B03 -> B05 -> B01/B02) and identified from the recorded datasets only. The
truths are committed (SHA-256) before identification and revealed afterwards.
The identified sets feed C2 (run_c2_twin.py).

Evidence status: SIMULATION (virtual bench on M1 and standalone models) and
CALCULATION (identification). Not a measurement of any pen.
Outputs: results/s2r/c1_identification.json, fig_c1_recovery.png
Run: python3 -m s2r.run_c1_identify [--quick]     (about 4 min on 2 processes)
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import s2r  # noqa: F401  (environment)
from s2r import common, pipeline
from s2r import truth as tr

SEED = 20260927
N_IN, N_OUT = 10, 5


def _one(args):
    i, vals, seed = args
    t0 = time.time()
    r = pipeline.run(vals, seed)
    r["elapsed_s"] = time.time() - t0
    return i, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    n_in, n_out = (2, 1) if a.quick else (N_IN, N_OUT)
    t0 = time.time()
    truths = tr.batch(SEED, n_in, n_out)
    commit = tr.commitment(truths)
    jobs = [(i, t["values"], SEED + 101 * i) for i, t in enumerate(truths)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = dict(ex.map(_one, jobs))
    rows = []
    for i, t in enumerate(truths):
        sc = pipeline.score(res[i]["estimates"], t["values"])
        rows.append({"id": t["id"], "kind": t["kind"], "outside": t["outside"], "score": sc,
                     "estimates": res[i]["estimates"], "bench_s": res[i]["bench_s"], "diag": res[i]["diag"]})
    keys = pipeline.IDENTIFIED_KEYS
    summary = {}
    for k in keys:
        e = np.array([r["score"][k]["rel_err"] for r in rows])
        z = np.array([r["score"][k]["z"] for r in rows])
        cov = np.array([r["score"][k]["covered95"] for r in rows])
        u = np.array([r["score"][k]["U95_rel"] for r in rows])
        inr = np.array([r["score"][k]["in_declared_range"] for r in rows])
        summary[k] = {"rel_err": common.summarize(e), "rel_err_outside_range": common.summarize(e[~inr]),
                      "z_rms": float(np.sqrt(np.mean(z ** 2))), "coverage95": float(np.mean(cov)),
                      "U95_rel_median": float(np.median(u)), "n_outside_range": int((~inr).sum())}
    bench = {k: float(np.median([r["bench_s"][k] for r in rows])) for k in rows[0]["bench_s"]}
    payload = {"truth_commitment_sha256": commit, "truths_revealed": truths, "summary": summary,
               "bench_time_s_median": bench, "per_truth": rows,
               "protocol_settings": pipeline.PROTOCOL,
               "diagnostics": {
                   "B03_coil_dT_max_K_median": float(np.median([r["diag"]["B03"]["coil_dT_max_K"] for r in rows])),
                   "B03_protocol_dT_rule_met_fraction": float(np.mean(
                       [r["diag"]["B03"]["protocol_dT_rule_2K_met"] for r in rows])),
                   "B05_coherence_min": float(np.min([r["diag"]["B05"]["coherence_min_fit_band"] for r in rows])),
                   "B05_q_peak_um_max": float(np.max([r["diag"]["B05"]["q_peak_um"] for r in rows])),
                   "B02_recip_R2_pooled_min": float(np.min([r["diag"]["B01B02"]["recip_R2_pooled"] for r in rows])),
                   "B02_recip_R2_record_min": float(np.min([r["diag"]["B01B02"]["recip_R2_min"] for r in rows])),
                   "B02_recip_R2_pooled_mean_removed_min": float(np.min(
                       [r["diag"]["B01B02"]["recip_R2_pooled_mean_removed"] for r in rows])),
                   "B02_recip_NRMSE_median_max": float(np.max(
                       [r["diag"]["B01B02"]["recip_NRMSE_vs_muN_median"] for r in rows])),
                   "B02_recip_NRMSE_mean_removed_median_max": float(np.max(
                       [r["diag"]["B01B02"]["recip_NRMSE_mean_removed_median"] for r in rows]))},
               "elapsed_s": time.time() - t0}
    path = common.write_result("c1_identification", payload,
                               "SIMULATION (virtual bench, hidden plants) + CALCULATION (identification)",
                               seeds={"truth_batch": SEED, "runs": [j[2] for j in jobs]})
    # figure: relative error per parameter, inside vs outside the declared range
    fig, ax = common.figure(figsize=(9.5, 4.4))
    from stabpen import plotstyle
    ys = np.arange(len(keys))
    for j, k in enumerate(keys):
        for r in rows:
            s = r["score"][k]
            c = plotstyle.SERIES[0] if s["in_declared_range"] else plotstyle.SERIES[1]
            flagged = s["U95_rel"] > 0.5          # the analysis itself reports "not identifiable"
            ax.plot(100 * s["rel_err"], j + np.random.default_rng(j).uniform(-0.15, 0.15), "o", ms=5 if flagged else 4,
                    markerfacecolor="none" if flagged else c, markeredgecolor=c, alpha=0.9)
        ax.plot([-100 * summary[k]["U95_rel_median"], 100 * summary[k]["U95_rel_median"]], [j, j], "|-",
                color=plotstyle.INK2, lw=1.0, ms=9)
    ax.set_yticks(ys, [k.split(".", 1)[1] for k in keys], fontsize=8)
    ax.invert_yaxis()
    ax.set_xscale("symlog", linthresh=1.0)
    ax.axvline(0, color=plotstyle.MUTED, lw=0.8)
    ax.set_xlabel("identification error (%), symlog; bar = median U95")
    ax.set_title("Blind recovery of hidden plants at protocol settings (blue: value in declared range, orange: "
                 "outside; hollow: U95 > 50 %, reported unidentifiable)", loc="left", fontsize=9.5)
    common.save_figure(fig, "fig_c1_recovery", "simulation",
                       f"virtual bench, {len(rows)} hidden plants, protocol instruments; twin experiment, not a measurement")
    print(path, f"{time.time() - t0:.0f} s")
    for k in keys:
        s = summary[k]
        print(f"{k:28s} rms {100 * s['rel_err']['rms']:.2f}%  p95|e| {100 * s['rel_err']['abs_p95']:.2f}%  "
              f"U95 {100 * s['U95_rel_median']:.2f}%  cov {s['coverage95']:.2f}  z_rms {s['z_rms']:.2f}")


if __name__ == "__main__":
    main()
