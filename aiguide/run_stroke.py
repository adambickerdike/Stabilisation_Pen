#!/usr/bin/env python3
"""B1.3 stroke continuation 50-200 ms ahead (on-device class).

Evidence status: SIMULATION on synthetic writers (glyph font with personal
style, aiguide/writer.py) writing Tatoeba training-split sentences; a second,
different generator (sigma-lognormal scribble, stabpen.signals) is an
out-of-generator check.  Writer-disjoint split: 40 train / 10 validation /
10 test writers.  Fit windows (k) are chosen on validation writers.  Input
is the pen's position at 200 Hz with 3 um sensor noise, clean or with
synthetic tremor (random 4-10 Hz, 0.3 mm peak); the target is the intended
position h ahead.  The MAC budget is a CALCULATION.

Outputs results/ai/stroke_prediction.json and fig_stroke_prediction.png.
Run: python3 -m aiguide.run_stroke  (about 30 s, 2 torch threads)
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from . import EVIDENCE_SIM, RESULTS_DIR, corpus
from . import stroke_predict as sp
from .writer import SyntheticWriter, sample_style
from stabpen import plotstyle, provenance
from stabpen import signals as sg

DT = 1e-3
NOISE = 3e-6


def pick_sentences(rng, pool, n):
    idx = rng.choice(len(pool), n, replace=False)
    return [pool[i] for i in idx]


def writer_windows(wid, sentences, tremor, rng):
    st = sample_style(np.random.default_rng(wid))
    wtr = SyntheticWriter(st, seed=wid)
    out = []
    for i, s in enumerate(sentences):
        wr = wtr.write(s, dt=DT, seed=50_000 + 10 * wid + i)
        it = wr.intended
        obs = it.xy + NOISE * rng.standard_normal(it.xy.shape)
        if tremor:
            f0 = rng.uniform(4.0, 10.0)
            obs = obs + sg.tremor(it.t, sg.TremorSpec(f0=f0, amp_pk=3e-4, onset=0.0), rng)
        out.append(sp.windows_from_path(it.t, it.xy, obs, it.pen_down, wid))
    return sp.concat(out)


def lognormal_windows(seed, tremor, rng, duration=12.0):
    it = sg.lognormal_handwriting(DT, duration, np.random.default_rng(seed))
    obs = it.xy + NOISE * rng.standard_normal(it.xy.shape)
    if tremor:
        obs = obs + sg.tremor(it.t, sg.TremorSpec(f0=rng.uniform(4.0, 10.0), amp_pk=3e-4, onset=0.0), rng)
    return sp.windows_from_path(it.t, it.xy, obs, it.pen_down, 10_000 + seed)


def errors(pred, Y):
    return np.hypot(*(pred - Y).transpose(2, 0, 1))          # (n, H)


def summary(e):
    return {f"{int(h * 1000)}ms": {"median_um": float(np.median(e[:, j]) * 1e6), "rms_um": float(np.sqrt(np.mean(e[:, j] ** 2)) * 1e6),
                                   "p90_um": float(np.percentile(e[:, j], 90) * 1e6),
                                   "within_300um": float(np.mean(e[:, j] < 300e-6)),
                                   "within_550um": float(np.mean(e[:, j] < 550e-6))}
            for j, h in enumerate(sp.HORIZONS_S)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=int, default=40)
    ap.add_argument("--val", type=int, default=10)
    ap.add_argument("--test", type=int, default=10)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--figure-only", action="store_true", help="redraw the figure from results/ai/stroke_prediction.json")
    args = ap.parse_args(argv)
    if args.figure_only:
        import json
        d = json.loads((RESULTS_DIR / "stroke_prediction.json").read_text())
        figure({c: v["test"] for c, v in d["conditions"].items()}, RESULTS_DIR / "fig_stroke_prediction.png")
        return
    t0 = time.time()
    spl = corpus.make_splits()
    pool = [s for s in spl.train if 12 <= len(s) <= 60 and all(c in corpus.ALPHABET for c in s)]
    ids = {"train": range(100, 100 + args.train), "val": range(200, 200 + args.val), "test": range(300, 300 + args.test)}
    res = {"setup": {"rate_hz": sp.RATE, "window_samples": sp.W, "horizons_s": list(sp.HORIZONS_S),
                     "writers": {k: [min(v), max(v)] for k, v in ids.items()}, "sensor_noise_m": NOISE,
                     "tremor": "random f0 4-10 Hz per sentence, 0.3 mm peak (stabpen.signals.tremor)",
                     "sentences_per_writer": 4, "text": "Tatoeba CC0 training-split sentences, 12-60 chars"},
           "conditions": {}}
    rel = {}
    for cond, tremor in (("clean", False), ("tremor", True)):
        tc = time.time()
        data = {}
        for split, wids in ids.items():
            ws = []
            for wid in wids:
                rng = np.random.default_rng(90_000 + wid + (7 if tremor else 0))
                ws.append(writer_windows(wid, pick_sentences(rng, pool, 4), tremor, rng))
            data[split] = sp.concat(ws)
        rngl = np.random.default_rng(77 + tremor)
        data["lognormal"] = sp.concat([lognormal_windows(s, tremor, rngl) for s in range(6)])
        va, te = data["val"], data["test"]
        # tune k on validation (median error averaged over horizons)
        best = {}
        for name, deg, grid in (("cv", 1, (3, 4, 6, 8, 10, 12)), ("ca", 2, (6, 8, 10, 12, 16, 20, 24)),
                                ("arc", None, (3, 5, 7, 9, 13, 17, 21))):
            scores = {}
            for k in grid:
                p = sp.predict_arc(va.X, k) if name == "arc" else sp.predict_poly(va.X, k, deg)
                scores[k] = float(np.mean(np.median(errors(p, va.Y), axis=0)))
            best[name] = min(scores, key=scores.get)
        mlp = sp.MLPPredictor().fit(data["train"], va, epochs=args.epochs)
        preds = {"hold": lambda X: np.zeros((len(X), len(sp.HORIZONS_S), 2)),
                 "cv": lambda X: sp.predict_poly(X, best["cv"], 1),
                 "ca": lambda X: sp.predict_poly(X, best["ca"], 2),
                 "arc": lambda X: sp.predict_arc(X, best["arc"]),
                 "mlp": mlp.predict}
        cres = {"k_selected_on_val": best, "n_windows": {k: int(len(v.X)) for k, v in data.items()},
                "mlp": {"params": mlp.n_params(), "macs": mlp.macs(), "best_epoch": mlp.best_epoch,
                        "val_mse_mm2": [round(v, 5) for v in mlp.history["val"]]},
                "test": {}, "lognormal_generator": {}}
        for name, f in preds.items():
            cres["test"][name] = summary(errors(f(te.X), te.Y))
            cres["lognormal_generator"][name] = summary(errors(f(data["lognormal"].X), data["lognormal"].Y))
        # speed context: distance travelled in h (the 'hold' error) is the scale of the problem
        cres["test_intended_speed_mm_s"] = {"median": float(np.median(te.speed) * 1e3),
                                            "p90": float(np.percentile(te.speed, 90) * 1e3)}
        res["conditions"][cond] = cres
        rel[cond] = cres["test"]
        print(cond, f"{time.time() - tc:.0f}s", best, {n: cres["test"][n]["100ms"]["median_um"] for n in preds})
    res["mac_budget"] = sp.mac_budget(res["conditions"]["clean"]["k_selected_on_val"]["cv"],
                                      res["conditions"]["clean"]["k_selected_on_val"]["ca"],
                                      res["conditions"]["clean"]["k_selected_on_val"]["arc"],
                                      sp.MLPPredictor().macs())
    res["meta"] = provenance.metadata(EVIDENCE_SIM + "; open-loop prediction, no stage",
                                      seeds={"writers": {k: [min(v), max(v)] for k, v in ids.items()},
                                             "mlp_torch": 7, "tremor_rng": "90000+writer(+7)"},
                                      extra={"torch_threads": 2})
    res["runtime_s"] = round(time.time() - t0, 1)
    provenance.write_json(str(RESULTS_DIR / "stroke_prediction.json"), res)
    figure(rel, RESULTS_DIR / "fig_stroke_prediction.png")
    print(f"{time.time() - t0:.0f}s")


def figure(rel, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    hs = [int(h * 1000) for h in sp.HORIZONS_S]
    names = ["hold", "cv", "ca", "arc", "mlp"]
    labels = {"hold": "hold (distance travelled)", "cv": "constant velocity", "ca": "constant acceleration",
              "arc": "constant turn rate", "mlp": "MLP 2x64"}
    for ax, cond in zip(axes, ("clean", "tremor")):
        for i, n in enumerate(names):
            med = [rel[cond][n][f"{h}ms"]["median_um"] for h in hs]
            p90 = [rel[cond][n][f"{h}ms"]["p90_um"] for h in hs]
            c = plotstyle.SERIES[i]
            ax.plot(hs, med, color=c, label=labels[n])
            ax.plot(hs, med, **plotstyle.marker_kw(c))
            ax.plot(hs, p90, color=c, lw=1.0, ls=":")
        ax.axhline(300, color=plotstyle.STATUS["critical"], lw=1, ls="--")
        ax.text(hs[-1], 320, "pencil travel 300 µm", fontsize=7, color=plotstyle.INK2, va="bottom", ha="right")
        ax.set_yscale("log")
        ax.set_ylim(50, 3e4)
        ax.set_title(f"{'Clean position input' if cond == 'clean' else 'Input with 4-10 Hz, 0.3 mm tremor'}")
        ax.set_xlabel("prediction horizon (ms)")
        ax.set_xticks(hs)
    axes[0].set_ylabel("error to intended position (µm)\nsolid: median, dotted: p90")
    axes[0].legend(loc="upper left", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "synthetic writers, 10 test writers (writer-disjoint)")
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
