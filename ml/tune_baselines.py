#!/usr/bin/env python3
r"""Tune the conventional baselines on the VALIDATION writers (never on test).

Criterion (identical for every method, including the network's epoch selection):
all-band residual ratio at matched false correction FC <= 25 um (ml/metrics.py).
Least-squares predictors are fitted on the TRAINING writers with the network's
sample weights; only their order / ridge strength is chosen on validation.
Frozen controller configurations (results/sim/estimator_selection.json snapshot
in results/ml/dataset_manifest.json) are evaluated as they are.
Outputs: results/ml/baselines_tuning.json (every grid point) and
results/ml/model/arls*.npz (fitted coefficients).
Run: python3 -m ml.tune_baselines
Evidence status: SIMULATION / synthetic data.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import time

import numpy as np
from scipy import signal as sps

from . import common as C
from . import baselines as BL
from . import datasets as D
from . import metrics as MT

GRIDS = {
    "bpf": [dict(lo=lo, hi=hi, tune_hz=7.0, tau_d=td) for lo, hi, td in
            itertools.product((5.0, 6.0, 7.0, 8.0, 9.0, 10.0), (14.0, 16.0, 20.0), (0.00224, 0.008, 0.02))],
    "kf": [dict(qj=qj, qt=qt, r=r) for qj, qt, r in
           itertools.product((1.0, 3.0, 10.0, 30.0), (1e-9, 3e-9, 1e-8, 3e-8, 1e-7, 3e-7),
                             (1e-12, 3.125e-12, 1e-11, 3e-11, 1e-10))],
    "kf_gate": (5.5, 6.5, 7.5, 8.5),
    "bmflc": [dict(f_lo=a, f_hi=14.0, df=0.5, mu=mu, f_hp=hp) for a, mu, hp in
              itertools.product((5.0, 6.0, 7.0, 8.0), (0.05, 0.1, 0.2, 0.4), (2.5, 4.0, 6.0))],
    "arls": [dict(p=p, alpha=a) for p, a in itertools.product((32, 64), (1e-4, 3e-4, 1e-3, 3e-3, 1e-2))],
    "arls_sched": [dict(p=p, alpha=a) for p, a in itertools.product((32, 64), (1e-4, 1e-3, 1e-2))],
}
EXTENSIONS = {   # later passes: widen grids whose optimum sat on an edge (merged, never replaced)
    "bpf": [dict(lo=lo, hi=hi, tune_hz=7.0, tau_d=td) for lo, hi, td in
            itertools.product((10.0, 11.0, 12.0), (12.0, 13.0, 14.0), (0.02, 0.05)) if hi > lo],
    "kf": [dict(qj=qj, qt=qt, r=r) for qj, qt, r in
           itertools.product((30.0, 100.0, 300.0, 1000.0), (3e-9, 1e-8, 3e-8), (1e-10, 3e-10, 1e-9, 3e-9))] +
          [dict(qj=qj, qt=qt, r=r) for qj, qt, r in
           itertools.product((10.0, 30.0, 100.0), (1e-8, 3e-8, 1e-7), (3e-9, 1e-8, 3e-8, 1e-7))],
    "bmflc": [dict(f_lo=a, f_hi=14.0, df=0.5, mu=mu, f_hp=hp) for a, mu, hp in
              itertools.product((8.0, 9.0, 10.0), (0.1, 0.2, 0.4), (6.0, 8.0))] +
             [dict(f_lo=a, f_hi=14.0, df=0.5, mu=mu, f_hp=hp) for a, mu, hp in
              itertools.product((10.0, 11.0, 12.0), (0.2, 0.4, 0.8), (8.0, 10.0))],
}
KF_FIXED = {"w0_hz": 7.0, "tau_decay": 0.5, "tau_w": 0.3, "wmin_hz": 2.5, "wmax_hz": 14.0, "nis_hi": 6.0,
            "f_gate_width": 1.5, "authority_tau": 0.05}


def score(val, preds):
    st = MT.stack([MT.rec_stats(r, p) for r, p in zip(val, preds)])
    crit, g = MT.matched_rr_all(st, C.FC_HEADLINE_UM)
    p1 = MT.pooled(st, 1.0)
    return {"criterion": crit, "gain_fc25": g, "rr_all_g1": p1["rr_all"], "fc_g1_um": p1["fc_um"],
            "rr_band_g1": [float(x) for x in p1["rr_band"]]}


def gated(o, fgate, fgw=1.5, tau=0.05):
    """Controller command g_eff * d_hat for a frequency gate applied post hoc to a run made
    with f_gate = 0 (conf already contains the NIS confidence)."""
    gate = np.clip((o["f_est"] - (fgate - 0.5 * fgw)) / fgw, 0.0, 1.0)
    a = 1.0 - math.exp(-C.TS / tau)
    geff = sps.lfilter([a], [1.0, -(1.0 - a)], o["conf"] * gate)
    return o["dhat_um"] * geff[:, None]


def extend(fams):
    """Evaluate EXTENSIONS grids for the given families and merge into baselines_tuning.json."""
    t0 = time.time()
    path = os.path.join(C.RESULTS, "baselines_tuning.json")
    out = json.load(open(path))
    val = D.load_split("val")
    pos = [BL.position(r) for r in val]
    seen = lambda fam: {json.dumps(r["cfg"], sort_keys=True) for r in out["grids"][fam]}  # noqa: E731
    for fam in fams:
        if fam == "kf":
            done, done_g = seen("kf"), seen("kf_gated")
            for cfg in EXTENSIONS["kf"]:
                full = dict(KF_FIXED, **cfg, f_gate=0.0)
                if json.dumps(full, sort_keys=True) in done:
                    continue
                outs = [BL.kf_run(p, **full) for p in pos]
                out["grids"]["kf"].append({"cfg": full, "pass": 2, **score(val, [o["dhat_um"] for o in outs])})
                for fg in GRIDS["kf_gate"]:
                    gcfg = dict(full, f_gate=fg)
                    if json.dumps(gcfg, sort_keys=True) not in done_g:
                        out["grids"]["kf_gated"].append({"cfg": gcfg, "pass": 2, **score(val, [gated(o, fg) for o in outs])})
        else:
            done = seen(fam)
            fn = BL.bpf_run if fam == "bpf" else BL.bmflc_run
            for cfg in EXTENSIONS[fam]:
                if json.dumps(cfg, sort_keys=True) in done:
                    continue
                out["grids"][fam].append({"cfg": cfg, "pass": 2, **score(val, [fn(p, **cfg) for p in pos])})
        print(f"{fam} extended {time.time() - t0:.0f} s", flush=True)
    for fam, rows in out["grids"].items():
        b = min(rows, key=lambda r: r["criterion"])
        out["selected"][fam] = b
        print(f"SELECTED {fam}: crit {b['criterion']:.4f} g {b['gain_fc25']:.3f} fc_g1 {b['fc_g1_um']:.1f} cfg {b['cfg']}",
              flush=True)
    out["meta_extension"] = C.meta(extra={"elapsed_s": time.time() - t0, "families": fams})
    C.write_json(path, out)


def main():
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--extend":
        return extend(sys.argv[2:])
    t0 = time.time()
    man = json.load(open(os.path.join(C.RESULTS, "dataset_manifest.json")))
    frozen = man["kf_frozen_250Hz"]
    val = D.load_split("val")
    pos = [BL.position(r) for r in val]
    out = {"criterion": f"validation rr_all at matched FC <= {C.FC_HEADLINE_UM} um", "grids": {}, "selected": {}}

    # ---------------- band-pass + extrapolation
    rows = []
    for cfg in GRIDS["bpf"]:
        rows.append({"cfg": cfg, **score(val, [BL.bpf_run(p, **cfg) for p in pos])})
    out["grids"]["bpf"] = rows
    print(f"bpf done {time.time() - t0:.0f} s", flush=True)

    # ---------------- Kalman oscillator (raw prediction, and controller command with gate)
    rows, rows_g = [], []
    for cfg in GRIDS["kf"]:
        full = dict(KF_FIXED, **cfg, f_gate=0.0)
        outs = [BL.kf_run(p, **full) for p in pos]
        rows.append({"cfg": full, **score(val, [o["dhat_um"] for o in outs])})
        for fg in GRIDS["kf_gate"]:
            rows_g.append({"cfg": dict(full, f_gate=fg), **score(val, [gated(o, fg) for o in outs])})
    out["grids"]["kf"] = rows
    out["grids"]["kf_gated"] = rows_g
    print(f"kf done {time.time() - t0:.0f} s", flush=True)
    for name in ("balanced", "assertive"):
        cfg = frozen[name]
        outs = [BL.kf_run(p, **cfg) for p in pos]
        out["grids"][f"kf_ctrl_{name[:3]}"] = [{"cfg": cfg, **score(val, [o["dhat_um"] * o["g_eff"][:, None] for o in outs])}]

    # ---------------- BMFLC
    rows = []
    for cfg in GRIDS["bmflc"]:
        rows.append({"cfg": cfg, **score(val, [BL.bmflc_run(p, **cfg) for p in pos])})
    out["grids"]["bmflc"] = rows
    print(f"bmflc done {time.time() - t0:.0f} s", flush=True)

    # ---------------- least-squares FIR predictors (fit on train)
    train = D.load_split("train")
    mdir = os.path.join(C.RESULTS, "model")
    os.makedirs(mdir, exist_ok=True)
    for fam, sched, stride in (("arls", False, 1), ("arls_sched", True, 3)):
        rows = []
        best = (np.inf, None)
        for p in sorted({g["p"] for g in GRIDS[fam]}):
            # accumulate the Gram matrix once per order; ridge strengths reuse it
            m0 = BL.ARLS(p=p, alpha=0.0, sched=sched)
            G = Bx = None
            for rec in train:
                X = BL._design(rec, p, sched)[::stride]
                Y = (np.asarray(rec["d_tgt_um"], np.float64) / C.S_OUT)[::stride]
                w = BL.sample_weights(rec)[::stride]
                Xw = X * w[:, None]
                G = Xw.T @ X if G is None else G + Xw.T @ X
                Bx = Xw.T @ Y if Bx is None else Bx + Xw.T @ Y
            for cfg in [g for g in GRIDS[fam] if g["p"] == p]:
                lam = cfg["alpha"] * np.trace(G) / G.shape[0]
                m = BL.ARLS(p=p, alpha=cfg["alpha"], sched=sched)
                m.B = np.linalg.solve(G + lam * np.eye(G.shape[0]), Bx)
                sc = score(val, [m.predict(r) for r in val])
                rows.append({"cfg": cfg, **sc})
                if sc["criterion"] < best[0]:
                    best = (sc["criterion"], m)
            del m0
        out["grids"][fam] = rows
        bm = best[1]
        np.savez(os.path.join(mdir, f"{fam}.npz"), B=bm.B, p=bm.p, alpha=bm.alpha, sched=bm.sched,
                 centers=BL.SCHED_CENTERS)
        print(f"{fam} done {time.time() - t0:.0f} s", flush=True)

    for fam, rows in out["grids"].items():
        b = min(rows, key=lambda r: r["criterion"])
        out["selected"][fam] = b
        print(f"SELECTED {fam}: crit {b['criterion']:.4f} g {b['gain_fc25']:.3f} rr_g1 {b['rr_all_g1']:.3f} "
              f"fc_g1 {b['fc_g1_um']:.1f} cfg {b['cfg']}", flush=True)
    out["meta"] = C.meta(extra={"elapsed_s": time.time() - t0, "horizon_conventional_s": C.H_S + C.TAU_NOM,
                                "val_writers": len(val)})
    C.write_json(os.path.join(C.RESULTS, "baselines_tuning.json"), out)
    print(f"done {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
