#!/usr/bin/env python3
"""B1.1 text predictor: held-out accuracy and calibration.

Evidence status: CALCULATION on public-domain text (Tatoeba English, CC0 1.0),
80/10/10 split by hashed sentence id; the model is trained on the training
split, lambda and temperatures are chosen on validation, all numbers below are
on the test split unless labelled otherwise.  "Note lines" are synthetic
note-like text (aiguide/sentences.py), out of the corpus domain.

Outputs results/ai/text_predictor.json and fig_text_calibration.png.
Run: python3 -m aiguide.run_text   (about 4 min on one core; the model is cached in aiguide/build/)
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from . import EVIDENCE_CALC, RESULTS_DIR, corpus, lm
from .sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES, GUIDE_SENTENCE, RARE_LINES
from stabpen import plotstyle, provenance

C_FULL = 0.8          # config/pencil.yaml ai.confidence_full


def topk_metrics(P: np.ndarray, y: np.ndarray) -> dict:
    order = np.argsort(-P, axis=1)
    top1 = order[:, 0] == y
    top3 = (order[:, :3] == y[:, None]).any(axis=1)
    conf = P[np.arange(len(y)), order[:, 0]]
    cal = lm.calibration(conf, top1.astype(float))
    return {"n": int(len(y)), "top1": float(top1.mean()), "top3": float(top3.mean()),
            "nll_bits": float(-np.mean(np.log2(np.maximum(P[np.arange(len(y)), y], 1e-300)))),
            "ece": cal["ece"], "brier_top1": cal["brier_top1"], "reliability": cal["bins"],
            "_conf": conf, "_correct": top1}


def strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def next_char_eval(pred, sentences, categories=True):
    pos = lm.positions(sentences)
    ctx = [c for c, _ in pos]
    y = np.array([lm.SYM[t] for _, t in pos])
    P, Pc, _ = lm.batch_raw_dists(pred, ctx)
    P = lm._temper(P, pred.T)
    out = {"mixture": strip(topk_metrics(P, y)), "char_only": strip(topk_metrics(Pc, y))}
    if categories:
        prevc = np.array([(c[-1] if c else "\n") for c in ctx])
        tgt = np.array([t for _, t in pos])
        letter = np.isin(tgt, list(corpus.LETTERS))
        cats = {"letter_within_word": letter & np.isin(prevc, list(corpus.LETTERS + "'")),
                "letter_word_initial": letter & np.isin(prevc, [" ", "\n"]),
                "space": tgt == " ", "end_of_sentence": tgt == "\n",
                "punctuation_or_digit": np.isin(tgt, list(corpus.DIGITS + corpus.PUNCT))}
        out["by_target"] = {k: {"n": int(m.sum()), "top1": float((np.argmax(P[m], 1) == y[m]).mean()),
                                "share": float(m.mean())} for k, m in cats.items() if m.sum()}
    return out, P, y


def glyph_eval(pred, sentences, d, n, seed):
    pos = lm.glyph_positions(sentences, d)
    rng = np.random.default_rng(seed)
    sel = rng.choice(len(pos), size=min(n, len(pos)), replace=False) if n else np.arange(len(pos))
    P = np.stack([pred.glyph_ahead(pos[i][0], d) for i in sel])
    y = np.array([lm.SYM[pos[i][1]] for i in sel])
    return topk_metrics(P, y)


def authority_table(conf, correct, c_full=C_FULL, c_mins=(0.0, 0.2, 0.3, 0.4, 0.5, 0.6)):
    """Authority c = min(1, conf / c_full), zero below c_min (ICD s5 rule 5)."""
    rows = []
    for cm in c_mins:
        c = np.where(conf < cm, 0.0, np.minimum(1.0, conf / c_full))
        g = c > 0
        rows.append({"c_min": cm, "guided_fraction": float(g.mean()),
                     "full_authority_fraction": float((c >= 1.0).mean()),
                     "precision_when_guided": float(correct[g].mean()) if g.any() else None,
                     "mean_authority_correct": float(c[correct].mean()) if correct.any() else None,
                     "mean_authority_wrong": float(c[~correct].mean()) if (~correct).any() else None,
                     "authority_weighted_error_share": float(c[~correct].sum() / max(c.sum(), 1e-12))})
    return rows


def word_eval(pred, sentences, max_n=None, seed=0):
    items = []
    for s in sentences:
        ws = s.split(" ")
        for i, tok in enumerate(ws):
            w = tok.strip(".,:-/")
            if not w:
                continue
            ctx = " ".join(ws[:i]) + (" " if i else "")
            items.append((ctx, w))
    if max_n and len(items) > max_n:
        rng = np.random.default_rng(seed)
        items = [items[i] for i in rng.choice(len(items), max_n, replace=False)]
    res = {"next_word": {"n": 0, "top1": 0, "top3": 0}}
    comp = {k: {"n": 0, "top1": 0, "top3": 0} for k in (1, 2, 3)}
    oov = 0
    for ctx, w in items:
        oov += not pred.word.in_vocab(w)
        top = [x for x, _ in pred.next_words(ctx, 3)]
        r = res["next_word"]
        r["n"] += 1
        r["top1"] += top[0] == w
        r["top3"] += w in top
        for k in (1, 2, 3):
            if len(w) > k:
                c = [x for x, _ in pred.complete_word(ctx + w[:k], 3)]
                comp[k]["n"] += 1
                comp[k]["top1"] += bool(c) and c[0] == w
                comp[k]["top3"] += w in c
    out = {"next_word_before_first_letter": {"n": res["next_word"]["n"],
                                             "top1": res["next_word"]["top1"] / max(res["next_word"]["n"], 1),
                                             "top3": res["next_word"]["top3"] / max(res["next_word"]["n"], 1)},
           "oov_rate": oov / max(len(items), 1)}
    for k, r in comp.items():
        out[f"completion_after_{k}_letters"] = {"n": r["n"], "top1": r["top1"] / max(r["n"], 1),
                                                "top3": r["top3"] / max(r["n"], 1)}
    return out


def figure(rel, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, axes = plt.subplots(1, len(rel), figsize=(3.3 * len(rel), 3.4), sharey=True)
    for ax, (title, bins, ece) in zip(axes, rel):
        xs = [b["mean_conf"] for b in bins if b.get("n")]
        ys = [b["accuracy"] for b in bins if b.get("n")]
        ns = [b["n"] for b in bins if b.get("n")]
        ax.plot([0, 1], [0, 1], color=plotstyle.BASELINE, lw=1.2, label="perfect calibration")
        ax.plot(xs, ys, color=plotstyle.SERIES[0], label="model (test split)")
        ax.plot(xs, ys, **plotstyle.marker_kw(plotstyle.SERIES[0]))
        ax.set_title(f"{title}\nECE {ece:.3f}", fontsize=9.5)
        ax.set_xlabel("top-1 confidence")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        for x, yv, nn in zip(xs, ys, ns):
            if nn < 100:
                ax.annotate(f"n={nn}", (x, yv), fontsize=6.5, color=plotstyle.INK2, xytext=(3, -9),
                            textcoords="offset points")
    axes[0].set_ylabel("accuracy")
    axes[0].legend(loc="upper left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "CALCULATION", "Tatoeba CC0 test split; char KN 7-gram + word KN bigram")
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glyph-n", type=int, default=6000, help="sampled test positions per glyph depth")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args(argv)
    t0 = time.time()
    sp = corpus.make_splits()
    pred = lm.cached_predictor(sp, rebuild=args.rebuild)
    t_build = time.time() - t0
    res = {"corpus": corpus.provenance(), "splits": sp.info, "model": pred.info}
    print("model", pred.info, flush=True)

    t = time.time()
    nc, P, y = next_char_eval(pred, sp.test)
    res["test_next_char"] = nc
    print("next char", {k: round(v, 4) for k, v in nc["mixture"].items() if isinstance(v, float)},
          f"{time.time() - t:.1f}s", flush=True)
    rel = [("next character (depth 1)", nc["mixture"]["reliability"], nc["mixture"]["ece"])]

    res["test_next_glyph"] = {}
    for d in (1, 2):
        t = time.time()
        g = glyph_eval(pred, sp.test, d, args.glyph_n, seed=10 + d)
        res["test_next_glyph"][f"depth_{d}"] = strip(g)
        res["test_next_glyph"][f"depth_{d}"]["authority"] = authority_table(g["_conf"], g["_correct"])
        rel.append((f"next glyph, depth {d}", g["reliability"], g["ece"]))
        print(f"glyph d={d}", {k: round(v, 4) for k, v in strip(g).items() if isinstance(v, float)},
              f"{time.time() - t:.1f}s", flush=True)

    t = time.time()
    res["test_words"] = word_eval(pred, sp.test, max_n=20000)
    print("words", res["test_words"], f"{time.time() - t:.1f}s", flush=True)

    notes = {"app_note_lines": APP_NOTE_LINES, "extra_note_lines": EXTRA_NOTE_LINES, "rare_word_lines": RARE_LINES}
    res["note_lines_out_of_domain"] = {}
    for name, lines in notes.items():
        nc_n, _, _ = next_char_eval(pred, lines, categories=False)
        gl = {f"depth_{d}": strip(glyph_eval(pred, lines, d, 0, 0)) for d in (1, 2)}
        for v in gl.values():
            v.pop("reliability", None)
        m = nc_n["mixture"]
        m.pop("reliability", None)
        res["note_lines_out_of_domain"][name] = {"n_lines": len(lines), "next_char": m, "next_glyph": gl,
                                                 "words": word_eval(pred, lines)}
    # the closed-loop study sentence, letter by letter (depth 2)
    s = GUIDE_SENTENCE
    rows = []
    for ctx, tgt in lm.glyph_positions([s], 2):
        top = pred.next_glyphs(ctx, 2, 3)
        rows.append({"context": ctx, "target": tgt, "top3": [[c, round(p, 3)] for c, p in top]})
    res["guide_sentence_depth2"] = {"sentence": s, "letters": rows,
                                    "top1_accuracy": float(np.mean([r["top3"][0][0] == r["target"] for r in rows]))}
    res["timing_s"] = {"build_or_load": round(t_build, 1), "total": round(time.time() - t0, 1)}
    res["meta"] = provenance.metadata(EVIDENCE_CALC + "; Tatoeba CC0 text, held-out test split",
                                      seeds={"glyph_sampling": [11, 12], "word_sampling": 0},
                                      extra={"corpus_url": corpus.SOURCE["url"], "corpus_licence": corpus.SOURCE["licence"]})
    provenance.write_json(str(RESULTS_DIR / "text_predictor.json"), res)
    figure(rel, RESULTS_DIR / "fig_text_calibration.png")
    print("wrote results/ai/text_predictor.json", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
