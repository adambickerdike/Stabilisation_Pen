#!/usr/bin/env python3
"""B1.2 style-conditioned templates: template error when the prediction is right.

Evidence status: SIMULATION on synthetic writers (aiguide/writer.py); no person
was recorded.  Each writer first writes a pangram (calibration: one instance of
every letter), then the evaluation lines.  Before each letter the style is
estimated from everything already written (online), the correct letter's
template is synthesised and placed, and its distance to the writer's intended
path for that letter is measured.  The observed ink is the intended path plus
synthetic tremor (6 Hz, 0.3 mm peak) or clean, sampled at 200 Hz (ICD 0x02).

Shape sources: font glyph or the user's own exemplars (mean of recent
instances); style: estimated online, or the writer's true global style
(isolates the allograph and instance mismatch).  Placement: oracle anchor
(template start = intended start: shape error only), pen anchor (template
start = nib position at touchdown, i.e. intended start + tremor), app placement
from the previous letter (depth 1) or the one before it (depth 2).

Outputs results/ai/style_templates.json, fig_style_template_error.png,
fig_style_example.png.  Run: python3 -m aiguide.run_style  (about 2 min)
"""
from __future__ import annotations

import argparse
import math
import time
from collections import defaultdict

import numpy as np

from . import EVIDENCE_SIM, RESULTS_DIR
from .sentences import APP_NOTE_LINES, CALIB_SENTENCE, GUIDE_SENTENCE
from .style import StyleEstimate, StyleEstimator
from .template import anchor_to, app_origin, letter_template, template_error
from .writer import SyntheticWriter, contact_runs, sample_style
from stabpen import plotstyle, provenance
from stabpen import signals as sg

EVAL_LINES = [GUIDE_SENTENCE, APP_NOTE_LINES[0], APP_NOTE_LINES[2], APP_NOTE_LINES[4]]
DT = 1e-3
DEC = 5                      # 200 Hz observation


def observe(wr, tremor_amp, f0, rng):
    """Ink the app sees: intended + tremor, per stroke at 200 Hz, with times."""
    t = wr.intended.t
    d = np.zeros_like(wr.intended.xy) if tremor_amp <= 0 else sg.tremor(
        t, sg.TremorSpec(f0=f0, amp_pk=tremor_amp, onset=0.0), rng)
    ink = wr.intended.xy + d
    out = []
    for L in wr.letters:
        strokes, times = [], []
        for a, b in L.strokes:
            m = np.flatnonzero(wr.intended.pen_down[a:b]) + a
            m = m[::DEC] if len(m) > DEC else m
            if len(m) >= 2:
                strokes.append(ink[m])
                times.append(t[m])
        out.append((strokes, times, d))
    return out, d


def true_style_estimate(st, L_prev_x0=0.0):
    h = st.x_height_mm * 1e-3
    return StyleEstimate(h, st.width, math.radians(st.slant_deg), st.letter_gap, st.word_gap, 0.0, 0.0, 0.0,
                         st.speed_mm_s * 1e-3, st.air_speed_mm_s * 1e-3, 0)


def run(n_writers: int, tremor_conds, seed0: int = 0, example: bool = True):
    acc = defaultdict(lambda: defaultdict(list))
    style_err = defaultdict(list)
    ex_store = None
    for wseed in range(seed0, seed0 + n_writers):
        rng = np.random.default_rng(wseed)
        st = sample_style(rng)
        wtr = SyntheticWriter(st, seed=wseed)
        cal = wtr.write(CALIB_SENTENCE, dt=DT, seed=1000 + wseed)
        lines = [wtr.write(s, dt=DT, seed=2000 + 10 * wseed + i) for i, s in enumerate(EVAL_LINES)]
        for tname, (amp, f0) in tremor_conds.items():
            trng = np.random.default_rng(5000 + wseed)
            est = StyleEstimator()
            obs, _ = observe(cal, amp, f0, trng)
            prev_char = None
            for L, (strokes, times, _d) in zip(cal.letters, obs):
                new_word = prev_char is not None and cal.text[L.text_index - 1] == " "
                est.update(L.char, strokes, t_strokes=times, new_word=new_word)
                prev_char = L.char
            e0 = est.estimate()
            style_err[f"{tname}/size_rel"].append(e0.h / (st.x_height_mm * 1e-3) - 1)
            style_err[f"{tname}/slant_deg"].append(math.degrees(e0.slant) - st.slant_deg)
            style_err[f"{tname}/width_rel"].append(e0.width / st.width - 1)
            style_err[f"{tname}/speed_rel"].append(e0.speed / (st.speed_mm_s * 1e-3) - 1)
            for li, wr in enumerate(lines):
                obs, dline = observe(wr, amp, f0, trng)
                fits = []
                for k, (L, (strokes, times, _d)) in enumerate(zip(wr.letters, obs)):
                    e = est.estimate()
                    new_word = k > 0 and wr.text[L.text_index - 1] == " "
                    true_first = L.polylines[0][0]
                    td = strokes[0][0] if strokes else true_first            # nib at touchdown
                    cands = {}
                    for mode in ("font", "exemplar"):
                        tpl = letter_template(L.char, e, 0.0, 0.0, estimator=est, mode=mode)
                        cands[(mode, "oracle_anchor")] = anchor_to(tpl, true_first)
                        cands[(mode, "pen_anchor")] = anchor_to(tpl, td)
                        if k >= 1 and fits:
                            x0, y0 = app_origin(wr.letters[k - 1].char, fits[-1].x0, e,
                                                new_word)
                            cands[(mode, "app_depth1")] = letter_template(L.char, e, x0, y0, estimator=est, mode=mode)
                        if k >= 2 and len(fits) >= 2:
                            nw1 = wr.text[wr.letters[k - 1].text_index - 1] == " "
                            x1, _ = app_origin(wr.letters[k - 2].char, fits[-2].x0, e, nw1)
                            x0, y0 = app_origin(wr.letters[k - 1].char, x1, e, new_word)
                            cands[(mode, "app_depth2")] = letter_template(L.char, e, x0, y0, estimator=est, mode=mode)
                    # true global style (no estimation error): font shape, oracle anchor
                    ts = true_style_estimate(st)
                    cands[("font_true_style", "oracle_anchor")] = anchor_to(letter_template(L.char, ts, 0, 0), true_first)
                    for key, tpl in cands.items():
                        r = template_error(L.polylines, tpl.strokes)
                        a = acc[(tname,) + key]
                        a["d"].append(r["d"])
                        a["d_shape"].append(r["d_shape"])
                        a["letter_rms"].append(float(np.sqrt(np.mean(r["d"] ** 2))))
                        a["source_exemplar"].append(tpl.source == "exemplar")
                    if example and ex_store is None and tname != "clean" and li == 0 and k == 3:
                        ex_store = {"letter": L.char, "intended": [p.tolist() for p in L.polylines],
                                    "ink": [s.tolist() for s in strokes],
                                    "font_pen_anchor": [p.tolist() for p in cands[("font", "pen_anchor")].strokes],
                                    "exemplar_pen_anchor": [p.tolist() for p in cands[("exemplar", "pen_anchor")].strokes],
                                    "exemplar_app_depth1": [p.tolist() for p in cands[("exemplar", "app_depth1")].strokes]}
                    if strokes:
                        fits.append(est.update(L.char, strokes, t_strokes=times, new_word=new_word))
    return acc, style_err, ex_store


def summarise(acc):
    out = {}
    for key, a in sorted(acc.items()):
        d = np.concatenate(a["d"]) * 1e6
        ds = np.concatenate(a["d_shape"]) * 1e6
        out["/".join(key)] = {"n_letters": len(a["letter_rms"]), "rms_um": float(np.sqrt(np.mean(d ** 2))),
                              "p95_um": float(np.percentile(d, 95)), "median_letter_rms_um": float(np.median(a["letter_rms"]) * 1e6),
                              "shape_rms_um": float(np.sqrt(np.mean(ds ** 2))), "shape_p95_um": float(np.percentile(ds, 95)),
                              "exemplar_share": float(np.mean(a["source_exemplar"]))}
    return out


def figure(summ, tremor_names, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    keys = [("font", "oracle_anchor"), ("exemplar", "oracle_anchor"), ("font", "pen_anchor"), ("exemplar", "pen_anchor"),
            ("font", "app_depth1"), ("exemplar", "app_depth1"), ("exemplar", "app_depth2")]
    labels = ["font\noracle", "exemplar\noracle", "font\npen", "exemplar\npen", "font\napp d1", "exemplar\napp d1",
              "exemplar\napp d2"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
    x = np.arange(len(keys))
    wbar = 0.38
    for ai, (metric, title) in enumerate((("rms_um", "Path error to intended, RMS (µm)"),
                                          ("shape_rms_um", "Shape error after best translation, RMS (µm)"))):
        ax = axes[ai]
        for ti, tn in enumerate(tremor_names):
            vals = [summ.get(f"{tn}/{k[0]}/{k[1]}", {}).get(metric, np.nan) for k in keys]
            ax.bar(x + (ti - 0.5) * wbar, vals, wbar, color=plotstyle.SERIES[ti], label=f"ink: {tn}")
            for xi, v in zip(x, vals):
                if np.isfinite(v):
                    ax.text(xi + (ti - 0.5) * wbar, v + 4, f"{v:.0f}", ha="center", fontsize=6.5, color=plotstyle.INK2)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_title(title)
        ax.axhline(300, color=plotstyle.STATUS["critical"], lw=1, ls="--")
        ax.text(len(keys) - 0.5, 305, "pencil travel 300 µm", ha="right", va="bottom", fontsize=7, color=plotstyle.INK2)
    axes[0].legend(loc="upper left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "synthetic writers; correct prediction; template vs intended path")
    fig.savefig(path)
    plt.close(fig)


def figure_example(ex, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    def draw(strokes, color, label, lw=2.0, ls="-"):
        for i, s in enumerate(strokes):
            s = np.asarray(s) * 1e3
            ax.plot(s[:, 0], s[:, 1], color=color, lw=lw, ls=ls, label=label if i == 0 else None)
    draw(ex["intended"], plotstyle.INK, "intended (writer)", 2.4)
    draw(ex["ink"], plotstyle.MUTED, "ink seen by the app (tremor)", 1.2)
    draw(ex["font_pen_anchor"], plotstyle.SERIES[1], "template: font, pen anchor", 1.6, "--")
    draw(ex["exemplar_pen_anchor"], plotstyle.SERIES[0], "template: own exemplars, pen anchor", 1.6)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"Letter '{ex['letter']}': templates vs intended")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "synthetic writer")
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--writers", type=int, default=24)
    args = ap.parse_args(argv)
    t0 = time.time()
    conds = {"clean": (0.0, 6.0), "tremor_6Hz_0.3mm": (3e-4, 6.0)}
    acc, serr, ex = run(args.writers, conds)
    summ = summarise(acc)
    se = {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)} for k, v in serr.items()}
    res = {"meta": provenance.metadata(EVIDENCE_SIM + "; open loop (no stage), template geometry only",
                                       seeds={"writers": list(range(args.writers)), "calibration_instance": "1000+w",
                                              "line_instance": "2000+10w+i", "tremor": "5000+w"}),
           "setup": {"writers": args.writers, "calibration_sentence": CALIB_SENTENCE, "eval_lines": EVAL_LINES,
                     "observation": "intended + tremor, 200 Hz per stroke", "tremor_conditions": conds,
                     "prediction": "correct letter (this measures style mismatch only)"},
           "template_error": summ, "style_estimate_after_calibration": se,
           "example": ex, "runtime_s": round(time.time() - t0, 1)}
    provenance.write_json(str(RESULTS_DIR / "style_templates.json"), res)
    figure(summ, list(conds), RESULTS_DIR / "fig_style_template_error.png")
    if ex:
        figure_example(ex, RESULTS_DIR / "fig_style_example.png")
    for k, v in summ.items():
        print(f"{k:45s} rms {v['rms_um']:6.0f}  p95 {v['p95_um']:6.0f}  shape {v['shape_rms_um']:6.0f}  n {v['n_letters']}")
    print(se)
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
