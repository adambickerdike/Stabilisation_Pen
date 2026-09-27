#!/usr/bin/env python3
"""B2 closed-loop guidance with AI-predicted templates on the unmodified M1 simulator.

Evidence status: SIMULATION (model M1, sim/pensim unmodified) on synthetic
writers (aiguide/writer.py) with synthetic tremor; the text predictor is the
Tatoeba-CC0 n-gram model of B1.1.  No person was recorded.

A synthetic writer first writes a pangram (style calibration), then the study
sentence with 0.3 mm tremor at 4, 6, 8 or 10 Hz.  Template conditions:
  oracle          the writer's true intended path (the default guided template)
  ai_correct      correct letters in the estimated style (own exemplars), pen-anchored, full authority
  ai_predicted    the predictor's top-1 letter at glyph depth 2 (the template lead needs it),
                  authority c = min(1, c_hat / 0.8), zero below c_hat 0.5 (ICD s5 rule 5)
  wrong_letter    every letter's template is the predictor's most likely *wrong* letter,
                  at full authority (worst case) and gated by its own confidence
  wrong_word      the second word's template is the predictor's next-word guess (app-placed)
  neutral         no correction;   kalman   free mode (assertive Kalman set, results/sim/estimator_selection.json)
Configurations: revA and pencil_like (aiguide/guidance.py).  Micrographia: the
same writers with a 35 % size decrement along the line and templates at the
calibration size.

Outputs results/ai/guidance.json, viz_guided.json and fig_guidance_*.png.
Run: python3 -m aiguide.run_guidance  (about 6-10 min with 2 processes)
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import EVIDENCE_SIM, RESULTS_DIR, use_private_numba_cache

use_private_numba_cache()
from . import guidance as G  # noqa: E402
from . import lm  # noqa: E402
from .glyphs import LETTERS  # noqa: E402
from .metrics import GlyphRecognizer  # noqa: E402
from .run_style import observe  # noqa: E402
from .sentences import CALIB_SENTENCE, GUIDE_SENTENCE  # noqa: E402
from .style import StyleEstimator  # noqa: E402
from .glyphs import width as glyph_width  # noqa: E402
from .template import LetterTemplate, anchor_to, letter_template  # noqa: E402
from .writer import SyntheticWriter, sample_style  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

AMP = 3e-4
F0S = (4.0, 6.0, 8.0, 10.0)
DEPTH = 2
WRONG_WORD_INDEX = 1
VIZ = {"writer": 0, "f0": 6.0, "config": "pencil_like"}
VIZ_EXTRA: dict = {}   # the viewer compares every AI case with the first case keyed "neutral": keep one config


# ------------------------------------------------------------------ predictions
def predictions(pred, text: str, depth: int):
    """Per glyph: top-1 letter and its confidence, most likely wrong letter and its confidence."""
    g = [i for i, c in enumerate(text) if c != " "]
    L = np.array([lm.SYM[c] for c in LETTERS])
    out = []
    for j, i in enumerate(g):
        if j - depth >= 0:
            ctx, d = text[:g[j - depth] + 1], depth
        else:
            ctx, d = "", j + 1
        p = pred.glyph_ahead(ctx, d)
        pl = p[L]
        top = int(np.argmax(pl))
        truth = LETTERS.index(text[i])
        pw = pl.copy()
        pw[truth] = -1
        alt = int(np.argmax(pw))
        out.append({"char": text[i], "context": ctx, "depth": d, "top1": LETTERS[top], "conf": float(pl[top]),
                    "correct": LETTERS[top] == text[i], "wrong": LETTERS[alt], "wrong_conf": float(pl[alt]),
                    "p_true": float(pl[truth])})
    return out


def word_prediction(pred, text: str, wi: int):
    words = text.split(" ")
    ctx = " ".join(words[:wi]) + " "
    for w, p in pred.next_words(ctx, 5):
        if w != words[wi] and all(c in LETTERS for c in w):
            return w, p
    return "the", 0.0


# ------------------------------------------------------------------ one scenario
def calibrate(wtr, wseed, amp, f0, micro_free_style=None):
    cal_writer = wtr
    if micro_free_style is not None:
        cal_writer = copy.copy(wtr)
        cal_writer.style = micro_free_style
    cal = cal_writer.write(CALIB_SENTENCE, dt=1e-3, seed=1000 + wseed)
    obs, _ = observe(cal, amp, f0, np.random.default_rng(5000 + wseed))
    est = StyleEstimator()
    prev = None
    for L, (strokes, times, _d) in zip(cal.letters, obs):
        est.update(L.char, strokes, t_strokes=times, new_word=prev is not None and cal.text[L.text_index - 1] == " ")
        prev = L
    return est


def build_templates(wr, est0, neutral, preds, wrong_word=None, freeze_size=False):
    """Pen-anchored letter templates per condition from the online style estimate."""
    td = G.touchdowns(wr, neutral)
    hp = G.hand_path_strokes(wr, neutral)
    est = copy.deepcopy(est0)
    if freeze_size:
        est.freeze_size()
    conds = defaultdict(list)
    for k, L in enumerate(wr.letters):
        e = est.estimate()
        anchor = td[k] if td[k] is not None else L.polylines[0][0]
        pk = preds[k] if preds is not None else {"top1": L.char, "conf": 1.0, "wrong": L.char, "wrong_conf": 1.0}
        for cond, ch, cf in (("ai_correct", L.char, 1.0), ("ai_predicted", pk["top1"], pk["conf"]),
                             ("wrong_letter", pk["wrong"], pk["wrong_conf"]),
                             ("a_for_o", "a" if L.char == "o" else L.char, 1.0)):
            t = letter_template(ch, e, 0.0, 0.0, estimator=est, mode="exemplar", conf=cf, glyph_index=k)
            conds[cond].append(anchor_to(t, anchor))
            if cond == "ai_correct":          # same shape, anchored at the intended start (perfect anchoring)
                conds["ai_correct_ideal_anchor"].append(anchor_to(t, L.polylines[0][0]))
        strokes, times = hp[k]
        if strokes:
            est.update(L.char, strokes, t_strokes=times,
                       new_word=k > 0 and wr.text[L.text_index - 1] == " ", keep_exemplar=True)
    e0 = est0.estimate()
    tracks = {c: G.track_from_letters(v, e0) for c, v in conds.items()}
    if wrong_word is not None:
        word, _p = wrong_word
        idx = [k for k, L in enumerate(wr.letters) if L.word_index == WRONG_WORD_INDEX]
        letters = [t for k, t in enumerate(conds["ai_correct"]) if k < idx[0]]
        anchor = td[idx[0]] if td[idx[0]] is not None else wr.letters[idx[0]].polylines[0][0]
        cur_x0 = cur_y0 = None
        for j, ch in enumerate(word):
            if j == 0:
                t = letter_template(ch, e0, 0.0, 0.0, estimator=est0, mode="exemplar", conf=1.0, glyph_index=idx[0])
                shift = np.asarray(anchor, float) - t.strokes[0][0]
                t = t.translate(shift)
                cur_x0, cur_y0 = float(shift[0]), float(shift[1])          # glyph origin after anchoring
            else:
                cur_x0 = cur_x0 + e0.a * glyph_width(word[j - 1]) + e0.letter_gap * e0.size
                t = letter_template(ch, e0, cur_x0, cur_y0, estimator=est0, mode="exemplar", conf=1.0,
                                    glyph_index=idx[0] + j)
            letters.append(t)
        letters += [t for k, t in enumerate(conds["ai_correct"]) if k > idx[-1]]
        tracks["wrong_word"] = G.track_from_letters(letters, e0)
        conds["wrong_word"] = letters
    return conds, tracks, est


def scenario(job):
    """All conditions for one (writer, f0, config) scenario, or the micrographia variant."""
    wseed, f0, cfg_name, kind = job["writer"], job["f0"], job["config"], job["kind"]
    cfg = G.CONFIGS[cfg_name]
    q_lim = cfg["ctrl"]["q_lim"]
    off = G.nib_offset(cfg)
    pred = lm.cached_predictor()
    st = sample_style(np.random.default_rng(wseed))
    wtr = SyntheticWriter(st, seed=wseed)
    micro = kind == "micrographia"
    amp = 0.0 if micro else AMP
    if micro:
        st_m = copy.copy(st)
        st_m.micrographia = 0.35
        wtr_m = SyntheticWriter(st_m, seed=wseed)
        est0 = calibrate(wtr, wseed, amp, f0)
        wr = wtr_m.write(GUIDE_SENTENCE, dt=G.SIM_DT, seed=2000 + wseed)
        wr_target = wtr.write(GUIDE_SENTENCE, dt=G.SIM_DT, seed=2000 + wseed)
    else:
        est0 = calibrate(wtr, wseed, amp, f0)
        wr = wtr.write(GUIDE_SENTENCE, dt=G.SIM_DT, seed=2000 + wseed)
    e0 = est0.estimate()
    rec = GlyphRecognizer(e0.h, e0.width, e0.slant)
    tremor = None if amp <= 0 else sg.TremorSpec(f0=f0, amp_pk=amp)
    scn = G.make_scenario(wr, tremor, cfg["N0"], seed=3000 + 10 * wseed + int(f0))
    S = 11 + wseed
    arrs, info = {}, {}
    arrs["neutral"] = G.arrays(G.run(scn, cfg, "neutral", seed=S))
    neutral = arrs["neutral"]
    windows = G.letter_windows(wr, float(neutral["t"][-1]))
    out = {"job": job, "nib_offset_um": (off * 1e6).tolist(), "style": vars(st), "calib_estimate": {"h_mm": e0.h * 1e3, "width": e0.width,
                                                              "slant_deg": math.degrees(e0.slant)}}
    out["intended_recognition_accuracy"] = float(np.mean([rec.classify(L.polylines)[0] == L.char for L in wr.letters]))
    preds = predictions(pred, GUIDE_SENTENCE, DEPTH)
    if micro:
        conds, tracks, _ = build_templates(wr, est0, neutral, None, freeze_size=True)
        # oracle target: the same letters written at the calibration size, anchored at the touchdowns
        td = G.touchdowns(wr, neutral)
        tl = []
        for k, (L, Lt) in enumerate(zip(wr.letters, wr_target.letters)):
            t = LetterTemplate(Lt.char, [p.copy() for p in Lt.polylines], 1.0, "oracle", k)
            tl.append(anchor_to(t, td[k] if td[k] is not None else L.polylines[0][0]))
        tracks["target_oracle"] = G.track_from_letters(tl, e0)
        conds["target_oracle"] = tl
        arrs["target_oracle"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["target_oracle"].xy, seed=S))
        arrs["target_ai"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["ai_correct"].xy, seed=S))
        tracks["target_ai"] = tracks["ai_correct"]
        conds["target_ai"] = conds["ai_correct"]
        res = {}
        for name in ("neutral", "target_oracle", "target_ai"):
            res[name] = G.case_metrics(wr, arrs[name], rec, q_lim, neutral=neutral, offset=off)
        heights = []
        for k, L in enumerate(wr.letters):
            ht = float(np.ptp(np.vstack(conds["target_ai"][k].strokes)[:, 1]))
            hto = float(np.ptp(np.vstack(conds["target_oracle"][k].strokes)[:, 1]))
            hu = float(np.ptp(np.vstack(L.polylines)[:, 1]))
            row = {"char": L.char, "user_um": hu * 1e6, "template_ai_um": ht * 1e6, "template_oracle_um": hto * 1e6}
            for name in ("neutral", "target_oracle", "target_ai"):
                lmx = res[name]["letters"][k]
                row[f"ink_{name}_um"] = lmx.get("height_um")
            heights.append(row)
        out["micrographia"] = {"cases": {k: v["summary"] for k, v in res.items()}, "heights": heights}
        if job.get("viz"):
            out["viz"] = viz_cases(wr, scn, arrs, tracks, {k: None for k in arrs}, res, micro=True, config=cfg_name)
        return out
    arrs["kalman"] = G.arrays(G.run(scn, cfg, "kfosc", extra=G.kalman_params(), seed=S))
    arrs["oracle"] = G.arrays(G.run(scn, cfg, "guided", seed=S))
    ww = word_prediction(pred, GUIDE_SENTENCE, WRONG_WORD_INDEX)
    conds, tracks, _ = build_templates(wr, est0, neutral, preds, wrong_word=ww)
    arrs["ai_correct"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["ai_correct"].xy, seed=S))
    fast = {"authority_tau": 0.01}
    arrs["oracle_fast"] = G.arrays(G.run(scn, cfg, "guided", seed=S, extra=fast))
    arrs["ai_correct_fast"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["ai_correct"].xy, seed=S, extra=fast))
    arrs["ai_correct_ideal_anchor"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["ai_correct_ideal_anchor"].xy, seed=S))
    arrs["wrong_letter_full"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["wrong_letter"].xy, seed=S))
    arrs["wrong_word"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["wrong_word"].xy, seed=S))
    conf_by_case = {}
    for name, trk, key in (("ai_predicted", "ai_predicted", "conf"), ("wrong_letter_gated", "wrong_letter", "wrong_conf")):
        levels = [G.quantise(G.authority(p[key])) for p in preds]
        runs = {lev: G.arrays(G.run(scn, cfg, "guided", tmpl=tracks[trk].xy, g=lev, seed=S)) for lev in sorted(set(levels))}
        arrs[name], info[name] = G.splice(runs, levels, windows)
        info[name]["levels"] = levels
        conf_by_case[name] = [p[key] for p in preds]
        # cross-check of the splice emulation: one run at the mean per-letter authority ("per run")
        g_mean = float(np.mean([G.authority(p[key]) for p in preds]))
        arrs[name + "_perrun"] = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks[trk].xy, g=g_mean, seed=S))
        info[name]["per_run_g"] = g_mean
    # the task's example: an 'a' template while the user writes 'o' (full authority on the o's only)
    lev_ao = [1.0 if L.char == "o" else 0.0 for L in wr.letters]
    run_ao = G.arrays(G.run(scn, cfg, "guided", tmpl=tracks["a_for_o"].xy, seed=S))
    arrs["a_for_o"], info["a_for_o"] = G.splice({0.0: neutral, 1.0: run_ao}, lev_ao, windows)
    info["a_for_o"]["levels"] = lev_ao
    conf_by_case["a_for_o"] = lev_ao
    res = {}
    for name, arr in arrs.items():
        res[name] = G.case_metrics(wr, arr, rec, q_lim, neutral=neutral if name != "neutral" else None, offset=off)
    # prediction-split metrics for ai_predicted
    ok = [k for k, p in enumerate(preds) if p["correct"]]
    bad = [k for k, p in enumerate(preds) if not p["correct"]]
    extra = {}
    for sub, idx in (("predicted_correct", ok), ("predicted_wrong", bad)):
        if idx:
            extra[sub] = G.case_metrics(wr, arrs["ai_predicted"], rec, q_lim, neutral=neutral, letter_idx=idx, offset=off)["summary"]
            extra[sub + "_neutral"] = G.case_metrics(wr, arrs["neutral"], rec, q_lim, letter_idx=idx, offset=off)["summary"]
    widx = [k for k, L in enumerate(wr.letters) if L.word_index == WRONG_WORD_INDEX]
    extra["wrong_word_letters"] = G.case_metrics(wr, arrs["wrong_word"], rec, q_lim, neutral=neutral, letter_idx=widx, offset=off)["summary"]
    extra["wrong_word_letters_neutral"] = G.case_metrics(wr, arrs["neutral"], rec, q_lim, letter_idx=widx, offset=off)["summary"]
    nxt = [k for k, L in enumerate(wr.letters) if L.word_index == WRONG_WORD_INDEX + 1]
    extra["after_wrong_word_letters"] = G.case_metrics(wr, arrs["wrong_word"], rec, q_lim, neutral=neutral, letter_idx=nxt, offset=off)["summary"]
    o_idx = [k for k, L in enumerate(wr.letters) if L.char == "o"]
    extra["a_for_o_letters"] = G.case_metrics(wr, arrs["a_for_o"], rec, q_lim, neutral=neutral, letter_idx=o_idx, offset=off)["summary"]
    extra["a_for_o_letters_neutral"] = G.case_metrics(wr, arrs["neutral"], rec, q_lim, letter_idx=o_idx, offset=off)["summary"]
    # flips: wrong-letter guidance making the letter read as the predicted letter
    flips = {"a_for_o": {"read_as_predicted_wrong_letter": sum(1 for k in o_idx if res["a_for_o"]["letters"][k].get("recognised_as") == "a"),
                         "still_read_as_true_letter": sum(1 for k in o_idx if res["a_for_o"]["letters"][k].get("recognised_ok")),
                         "n": len(o_idx)}}
    for name in ("wrong_letter_full", "wrong_letter_gated"):
        n_flip = sum(1 for k, L in enumerate(res[name]["letters"]) if L.get("recognised_as") == preds[k]["wrong"])
        n_ok = sum(1 for L in res[name]["letters"] if L.get("recognised_ok"))
        flips[name] = {"read_as_predicted_wrong_letter": n_flip, "still_read_as_true_letter": n_ok,
                       "n": len(res[name]["letters"])}
    out.update({"cases": {k: v["summary"] for k, v in res.items()}, "letters": {k: v["letters"] for k, v in res.items()},
                "ai_predicted_split": extra, "wrong_letter_flips": flips, "splice": info,
                "predictions": preds if (wseed == 0 and f0 == F0S[0]) else None, "wrong_word": {"true": GUIDE_SENTENCE.split(" ")[WRONG_WORD_INDEX],
                                                     "predicted": ww[0], "p": ww[1]}})
    if job.get("viz"):
        out["viz"] = viz_cases(wr, scn, arrs, tracks, conf_by_case, res, preds=preds, config=cfg_name, levels=info)
    return out


# ------------------------------------------------------------------ break-even sweep
SWEEP_AMPS = (0.0, 0.01, 0.02, 0.04, 0.06, 0.09, 0.13, 0.18, 0.25)      # x-height units of a smooth random warp


def sweep_job(job):
    """Ink path error against a controlled template error: intended letters warped by a smooth random
    deformation (writer-model warp family) with the first point kept, so the template is 'placed' exactly
    and only its shape is wrong.  Returns one row per amplitude."""
    from .writer import apply_warp, warp_params
    wseed, f0, cfg_name = job["writer"], job["f0"], job["config"]
    cfg = G.CONFIGS[cfg_name]
    off = G.nib_offset(cfg)
    st = sample_style(np.random.default_rng(wseed))
    wtr = SyntheticWriter(st, seed=wseed)
    wr = wtr.write(GUIDE_SENTENCE, dt=G.SIM_DT, seed=2000 + wseed)
    scn = G.make_scenario(wr, sg.TremorSpec(f0=f0, amp_pk=AMP), cfg["N0"], seed=3000 + 10 * wseed + int(f0))
    S = 11 + wseed
    rec = GlyphRecognizer(st.x_height_mm * 1e-3, st.width, math.radians(st.slant_deg))
    neutral = G.arrays(G.run(scn, cfg, "neutral", seed=S))
    base = G.case_metrics(wr, neutral, rec, cfg["ctrl"]["q_lim"], offset=off)["summary"]
    rows = []
    for amp in SWEEP_AMPS:
        rng = np.random.default_rng(700 + wseed)
        letters, errs = [], []
        for k, L in enumerate(wr.letters):
            h = L.size
            p0 = L.polylines[0][0]
            w = warp_params(rng, amp)
            strokes = [p0 + h * (apply_warp((P - p0) / h, w) - apply_warp(np.zeros((1, 2)), w)) for P in L.polylines]
            t = LetterTemplate(L.char, strokes, 1.0, "warped", k)
            from .template import template_error
            errs.append(template_error(L.polylines, t.strokes)["d"])
            letters.append(t)
        trk = G.track_from_letters(letters, calibrate_est_for_speed(st))
        arr = G.arrays(G.run(scn, cfg, "guided", tmpl=trk.xy, seed=S))
        m = G.case_metrics(wr, arr, rec, cfg["ctrl"]["q_lim"], neutral=neutral, offset=off)["summary"]
        e = np.concatenate(errs) * 1e6
        rows.append({"config": cfg_name, "writer": wseed, "f0": f0, "amp": amp,
                     "template_rms_um": float(np.sqrt(np.mean(e ** 2))), "ink_path_rms_um": m["path_rms_um"],
                     "ink_dtw_um": m.get("dtw_mean_um"), "neutral_path_rms_um": base["path_rms_um"],
                     "neutral_dtw_um": base.get("dtw_mean_um")})
    return rows


def calibrate_est_for_speed(st):
    """Template timing for the sweep: the writer's nominal speeds (timing does not change the path)."""
    from .style import StyleEstimate
    return StyleEstimate(st.x_height_mm * 1e-3, st.width, math.radians(st.slant_deg), st.letter_gap, st.word_gap,
                         0.0, 0.0, 0.0, st.speed_mm_s * 1e-3, st.air_speed_mm_s * 1e-3, 0)


def breakeven(rows):
    """Template error at which guided ink error equals the unguided error (linear interpolation of the means)."""
    out = {}
    for cfg in sorted({r["config"] for r in rows}):
        R = [r for r in rows if r["config"] == cfg]
        amps = sorted({r["amp"] for r in R})
        te = np.array([np.mean([r["template_rms_um"] for r in R if r["amp"] == a]) for a in amps])
        ink = np.array([np.mean([r["ink_path_rms_um"] for r in R if r["amp"] == a]) for a in amps])
        dtw = np.array([np.mean([r["ink_dtw_um"] for r in R if r["amp"] == a]) for a in amps])
        neu = float(np.mean([r["neutral_path_rms_um"] for r in R]))
        neu_dtw = float(np.mean([r["neutral_dtw_um"] for r in R]))
        def cross(y, ref):
            for i in range(1, len(y)):
                if (y[i - 1] - ref) * (y[i] - ref) <= 0 and y[i] != y[i - 1]:
                    return float(te[i - 1] + (ref - y[i - 1]) * (te[i] - te[i - 1]) / (y[i] - y[i - 1]))
            return None
        out[cfg] = {"template_rms_um": te.tolist(), "ink_path_rms_um": ink.tolist(), "ink_dtw_um": dtw.tolist(),
                    "neutral_path_rms_um": neu, "neutral_dtw_um": neu_dtw,
                    "breakeven_template_rms_um_path": cross(ink, neu), "breakeven_template_rms_um_dtw": cross(dtw, neu_dtw)}
    return out


def fig_breakeven(be, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    names = {"revA": "Rev A (0.55 mm, 1 N)", "pencil_like": "pencil-like (0.30 mm, 0.15 N)", "pencil_0.3N": "pencil limits at 0.3 N"}
    for ax, (key, nkey, title) in zip(axes, (("ink_path_rms_um", "neutral_path_rms_um", "Ink path distance to intended, RMS (µm)"),
                                             ("ink_dtw_um", "neutral_dtw_um", "Legibility proxy: DTW to clean letter (µm)"))):
        for cfg in ("revA", "pencil_like", "pencil_0.3N"):
            d = be[cfg]
            c = plotstyle.SERIES[CFG_COLOR[cfg]]
            ax.plot(d["template_rms_um"], d[key], color=c, label=f"guided, {names.get(cfg, cfg)}")
            ax.plot(d["template_rms_um"], d[key], **plotstyle.marker_kw(c))
            ax.axhline(d[nkey], color=c, lw=1.0, ls="--")
        ax.set_xlabel("template error to the intended path, RMS (µm)")
        ax.set_title(title, fontsize=9.5)
    axes[0].text(0.02, 0.97, "dashed: no guidance (same config)", transform=axes[0].transAxes, fontsize=7.5,
                 color=plotstyle.INK2, va="top")
    axes[0].legend(loc="lower right", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "M1 unmodified; 6 Hz 0.3 mm tremor; intended letters warped by a smooth random field")
    fig.savefig(path)
    plt.close(fig)


# ------------------------------------------------------------------ viz export
def _r(a, nd=3):
    return np.round(np.asarray(a, float) * 1e3, nd).tolist()


def viz_cases(wr, scn, arrs, tracks, conf_by_case, res, preds=None, micro=False, config="pencil_like", levels=None):
    t = arrs["neutral"]["t"]
    step = max(1, int(round(0.01 / (t[1] - t[0]))))
    sel = np.arange(0, len(t), step)
    ts = t[sel]
    kk = np.clip(np.round(ts / G.SIM_DT).astype(int), 0, len(scn.intended) - 1)
    intended = scn.intended[kk]
    names = {"neutral": "No guidance (neutral stage)", "kalman": "No prediction: Kalman free mode",
             "oracle": "Oracle template (true intended path)", "ai_predicted": "AI-predicted template (depth 2, confidence-gated)",
             "ai_correct": "AI template, prediction correct (style mismatch only)",
             "ai_predicted_note": "templates are shown only for letters whose confidence reached c_min",
             "wrong_letter_full": "Wrong prediction: most likely wrong letter, full authority",
             "wrong_word": "Wrong next word predicted for word 2",
             "a_for_o": "Wrong letter: 'a' template while the user writes 'o' (full authority on the o's)",
             "target_oracle": "Micrographia: template at the calibration size (oracle shapes)",
             "target_ai": "Micrographia: AI template at the calibration size"}
    keys = (["neutral", "target_oracle", "target_ai"] if micro else
            ["neutral", "kalman", "oracle", "ai_predicted", "ai_correct", "wrong_letter_full", "wrong_word", "a_for_o"])
    if config in VIZ_EXTRA:
        keys = [k for k in keys if k in VIZ_EXTRA[config]]
    out = []
    for key in keys:
        a = arrs[key]
        conf = np.zeros(len(ts))
        if key in ("oracle", "ai_correct", "target_oracle", "target_ai"):
            conf[:] = 1.0
        elif key == "wrong_letter_full" and preds is not None:
            conf[:] = 1.0
        elif key == "wrong_word":
            conf[:] = 1.0
        elif key in conf_by_case and conf_by_case[key] is not None:
            for L, c in zip(wr.letters, conf_by_case[key]):
                conf[(ts >= L.t0) & (ts <= L.t1)] = c
        if key == "oracle":
            k50 = np.arange(0, len(scn.intended), 800)                      # 50 Hz
            tp = scn.intended[k50]
            tdown = (scn.fpush[k50] > 0.5 * scn.N0).astype(int)
        elif key in ("neutral", "kalman"):
            tp = np.zeros((0, 2))
            tdown = np.zeros(0, int)
        else:
            trk = tracks["ai_predicted" if key == "ai_predicted" else "wrong_letter" if key == "wrong_letter_full" else key]
            keep = np.ones(len(trk.xy), bool)
            if levels is not None and key in levels:                           # only templates that are actually sent
                used = [k for k, lev in enumerate(levels[key]["levels"]) if lev > 0]
                keep = np.isin(trk.letter_of, used)
            tp = trk.xy[keep][::40]                                            # 50 Hz of the stage-rate track
            tdown = trk.pen_down[keep][::40].astype(int)
        tpl = np.round(tp * 1e3, 3).tolist()
        prefix = ("" if config == VIZ["config"] else config.replace(".", "") + "_") + ("micrographia_" if micro else "")
        lab = names[key] + ("" if config == VIZ["config"] else f" [{G.CONFIGS[config]['label']}]")
        out.append({"key": prefix + key, "label": lab, "config": config, "t": np.round(ts, 3).tolist(), "intended": _r(intended),
                    "template": tpl, "template_pen_down": tdown.tolist(), "housing": _r(a["pH"][sel]), "ink": _r(a["tip"][sel]),
                    "contact": a["contact"][sel].astype(int).tolist(), "confidence": np.round(conf, 3).tolist(),
                    "authority": np.round(a["g"][sel], 2).tolist(),
                    "metrics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res[key]["summary"].items()}})
    return out


# ------------------------------------------------------------------ aggregation
def aggregate(outs):
    agg = defaultdict(lambda: defaultdict(list))
    for o in outs:
        if "cases" not in o:
            continue
        cfg = o["job"]["config"]
        for case, s in o["cases"].items():
            for k, v in s.items():
                if isinstance(v, (int, float)):
                    agg[(cfg, case)][k].append(v)
        for sub, s in o["ai_predicted_split"].items():
            for k, v in s.items():
                if isinstance(v, (int, float)):
                    agg[(cfg, "split:" + sub)][k].append(v)
    table = {}
    for (cfg, case), d in agg.items():
        table.setdefault(cfg, {})[case] = {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)}
                                           for k, v in d.items()}
    by_f0 = defaultdict(lambda: defaultdict(list))
    for o in outs:
        if "cases" not in o:
            continue
        for case, s in o["cases"].items():
            by_f0[(o["job"]["config"], case, o["job"]["f0"])]["path_rms_um"].append(s["path_rms_um"])
            by_f0[(o["job"]["config"], case, o["job"]["f0"])]["dtw_mean_um"].append(s.get("dtw_mean_um", np.nan))
    f0tab = {}
    for (cfg, case, f0), d in by_f0.items():
        f0tab.setdefault(cfg, {}).setdefault(case, {})[str(f0)] = {k: float(np.nanmean(v)) for k, v in d.items()}
    return table, f0tab


def safety_aggregate(outs):
    """Wrong-template outcomes (letter flips) and the splice-emulation discontinuities, per config."""
    fl = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    jumps = defaultdict(list)
    for o in outs:
        if "wrong_letter_flips" not in o:
            continue
        cfg = o["job"]["config"]
        for case, d in o["wrong_letter_flips"].items():
            for k, v in d.items():
                fl[cfg][case][k] += v
        for case, d in o["splice"].items():
            if "max_housing_jump_um" in d and d["n_splices"]:
                jumps[cfg].append(d["max_housing_jump_um"])
    return {"flips": {c: {k: dict(v) for k, v in d.items()} for c, d in fl.items()},
            "splice_housing_jump_um": {c: {"median_of_max": float(np.median(v)), "max": float(np.max(v)), "n_runs": len(v)}
                                       for c, v in jumps.items()}}


def micro_aggregate(outs):
    """Letter heights: restoration toward the template measured from the user's intended height.

    restored = (h_ink_guided - h_user) / (h_template - h_user), pooled over letters with a deficit
    > 0.1 mm; device_shrink = (h_ink_neutral - h_user) / h_user (M1's open-loop hand lags the nib
    through grip compliance at 1 N, which shortens small letters even without guidance).
    """
    rows = defaultdict(list)
    summ = defaultdict(lambda: defaultdict(list))
    for o in outs:
        if "micrographia" not in o:
            continue
        cfg = o["job"]["config"]
        rows[cfg].extend(o["micrographia"]["heights"])
        for case, s in o["micrographia"]["cases"].items():
            for k, v in s.items():
                if isinstance(v, (int, float)):
                    summ[(cfg, case)][k].append(v)
    out = {}
    for cfg, hs in rows.items():
        def restored(key, tkey):
            num, den = [], []
            for h in hs:
                if h.get(key) is None:
                    continue
                deficit = h[tkey] - h["user_um"]
                if deficit > 100:
                    num.append(h[key] - h["user_um"])
                    den.append(deficit)
            return {"mean_height_change_vs_user_um": float(np.mean(num)) if num else None,
                    "mean_deficit_um": float(np.mean(den)) if den else None,
                    "fraction_restored": float(np.sum(num) / np.sum(den)) if den else None, "n_letters": len(num)}
        neu = [(h["ink_neutral_um"] - h["user_um"]) / h["user_um"] for h in hs if h.get("ink_neutral_um")]
        out[cfg] = {"target_oracle": restored("ink_target_oracle_um", "template_oracle_um"),
                    "target_ai": restored("ink_target_ai_um", "template_ai_um"),
                    "unguided_ink": restored("ink_neutral_um", "template_oracle_um"),
                    "device_shrink_unguided_mean": float(np.mean(neu)) if neu else None,
                    "mean_user_height_um": float(np.mean([h["user_um"] for h in hs])),
                    "mean_template_height_um": float(np.mean([h["template_oracle_um"] for h in hs])),
                    "cases": {case: {k: float(np.mean(v)) for k, v in d.items()} for (c2, case), d in summ.items() if c2 == cfg}}
    return out


# ------------------------------------------------------------------ figures
CFG_COLOR = {"revA": 0, "pencil_like": 1, "pencil_0.3N": 2}


def fig_summary(table, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    cases = ["neutral", "kalman", "oracle", "oracle_fast", "ai_correct", "ai_correct_ideal_anchor", "ai_correct_fast",
             "ai_predicted", "wrong_letter_gated", "wrong_letter_full", "wrong_word"]
    labels = ["neutral", "Kalman\nfree", "oracle", "oracle\n10 ms", "AI\ncorrect", "AI corr.\nideal anchor",
              "AI corr.\n10 ms", "AI\npredicted", "wrong\ngated", "wrong\nfull", "wrong\nword"]
    metrics = [("path_rms_um", "Path distance to intended, RMS (µm)"), ("dtw_mean_um", "Legibility proxy: DTW to clean letter (µm)"),
               ("recognition_accuracy", "Template-matching recognition (fraction)")]
    fig, axes = plt.subplots(3, 1, figsize=(11, 9.5))
    x = np.arange(len(cases))
    names = {"revA": "Rev A (0.55 mm, 1 N)", "pencil_like": "pencil-like (0.30 mm, 0.15 N)",
             "pencil_0.3N": "pencil limits at 0.3 N (suppl.)"}
    for ai, (m, title) in enumerate(metrics):
        ax = axes[ai]
        for ci, cfg in enumerate(("revA", "pencil_like", "pencil_0.3N")):
            vals = [table.get(cfg, {}).get(c, {}).get(m, {}).get("mean", np.nan) for c in cases]
            sds = [table.get(cfg, {}).get(c, {}).get(m, {}).get("sd", np.nan) for c in cases]
            ax.bar(x + (ci - 1) * 0.27, vals, 0.27, yerr=sds, color=plotstyle.SERIES[ci], ecolor=plotstyle.INK2,
                   capsize=2, error_kw={"lw": 0.8}, label=names[cfg])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_title(title, fontsize=9.5, loc="left")
        if m == "recognition_accuracy":
            ax.set_ylim(0, 1.05)
    axes[0].legend(loc="upper right", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "M1 unmodified; synthetic writers; 0.3 mm tremor 4-10 Hz; mean ± SD over writers and f0")
    fig.savefig(path)
    plt.close(fig)


def fig_frequency(f0tab, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    cases = [("neutral", "neutral"), ("kalman", "Kalman free"), ("oracle", "oracle template"), ("ai_correct", "AI, correct"),
             ("ai_predicted", "AI predicted (gated)"), ("wrong_letter_full", "wrong letter, full")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.7), sharey=True)
    for ax, cfg in zip(axes, ("revA", "pencil_like", "pencil_0.3N")):
        for i, (c, lab) in enumerate(cases):
            d = f0tab.get(cfg, {}).get(c, {})
            fs = sorted(float(k) for k in d)
            ys = [d[str(f)]["path_rms_um"] for f in fs]
            ax.plot(fs, ys, color=plotstyle.SERIES[i], label=lab)
            ax.plot(fs, ys, **plotstyle.marker_kw(plotstyle.SERIES[i]))
        ax.set_title({"revA": "Rev A (q_lim 0.55 mm, 1 N)", "pencil_like": "Pencil-like (q_lim 0.30 mm, 0.15 N)",
                      "pencil_0.3N": "Pencil limits at 0.3 N (suppl.)"}[cfg], fontsize=9.5)
        ax.set_xlabel("tremor frequency (Hz), 0.3 mm peak")
        ax.set_xticks(F0S)
    axes[0].set_ylabel("path distance to intended, RMS (µm)")
    axes[0].legend(fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "mean over synthetic writers")
    fig.savefig(path)
    plt.close(fig)


def fig_example(viz, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    keys = ["neutral", "oracle", "ai_predicted", "wrong_letter_full"]
    cases = {c["key"]: c for c in viz}
    fig, axes = plt.subplots(len(keys), 1, figsize=(10, 1.75 * len(keys)), sharex=True)
    for ax, k in zip(axes, keys):
        c = cases[k]
        I = np.array(c["intended"])
        con = np.array(c["contact"]) > 0
        ink = np.array(c["ink"])
        Iw = np.where(con[:, None], I, np.nan)
        ax.plot(Iw[:, 0], Iw[:, 1], color=plotstyle.BASELINE, lw=3.0, label="intended")
        if c["template"]:
            tp = np.array(c["template"], float)
            tp[np.asarray(c["template_pen_down"]) == 0] = np.nan
            ax.plot(tp[:, 0], tp[:, 1], color=plotstyle.SERIES[1], lw=1.0, ls="--", label="template")
        inkw = np.where(con[:, None], ink, np.nan)
        ax.plot(inkw[:, 0], inkw[:, 1], color=plotstyle.SERIES[0], lw=1.3, label="ink")
        m = c["metrics"]
        ax.set_title(f"{c['label']}  |  path RMS {m.get('path_rms_um', float('nan')):.0f} µm, "
                     f"DTW {m.get('dtw_mean_um', float('nan')):.0f} µm, read {m.get('recognition_accuracy', float('nan')):.2f}",
                     fontsize=8.5, loc="left")
        ax.set_aspect("equal")
        ax.set_ylabel("y (mm)")
    axes[0].legend(loc="upper right", fontsize=7, ncol=3)
    axes[-1].set_xlabel("x (mm)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "pencil-like limits, 6 Hz 0.3 mm tremor, one synthetic writer")
    fig.savefig(path)
    plt.close(fig)


def fig_micro(outs, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
    for ax, cfg in zip(axes, ("revA", "pencil_like", "pencil_0.3N")):
        rows = [h for o in outs if "micrographia" in o and o["job"]["config"] == cfg for h in o["micrographia"]["heights"]]
        if not rows:
            continue
        nper = len([h for h in outs[0]["micrographia"]["heights"]]) if "micrographia" in outs[0] else None
        # mean over writers per letter position
        by = defaultdict(lambda: defaultdict(list))
        for o in outs:
            if "micrographia" not in o or o["job"]["config"] != cfg:
                continue
            for k, h in enumerate(o["micrographia"]["heights"]):
                for key in ("user_um", "template_oracle_um", "ink_neutral_um", "ink_target_oracle_um", "ink_target_ai_um"):
                    if h.get(key) is not None:
                        by[k][key].append(h[key] / 1e3)
        ks = sorted(by)
        for i, (key, lab) in enumerate((("template_oracle_um", "template (calibration size)"), ("user_um", "user's intended (35 % decrement)"),
                                        ("ink_neutral_um", "ink, no guidance"), ("ink_target_oracle_um", "ink, guided (oracle shapes)"),
                                        ("ink_target_ai_um", "ink, guided (AI template)"))):
            ys = [np.mean(by[k][key]) for k in ks]
            ax.plot(ks, ys, color=plotstyle.SERIES[i], label=lab, lw=1.6)
        ax.set_title({"revA": "Rev A (q_lim 0.55 mm)", "pencil_like": "Pencil-like (q_lim 0.30 mm, 0.15 N)",
                      "pencil_0.3N": "Pencil limits at 0.3 N (suppl.)"}[cfg], fontsize=9.5)
        ax.set_xlabel("letter index in the sentence")
    axes[0].set_ylabel("letter height (mm), mean over writers")
    axes[0].legend(fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "SIMULATION", "synthetic micrographia, no tremor")
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--writers", type=int, default=6)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--f0", type=float, nargs="*", default=list(F0S))
    args = ap.parse_args(argv)
    t0 = time.time()
    lm.cached_predictor()          # build once before forking
    jobs = []
    for cfg in ("revA", "pencil_like", "pencil_0.3N"):
        for w in range(args.writers):
            for f0 in args.f0:
                jobs.append({"writer": w, "f0": f0, "config": cfg, "kind": "tremor",
                             "viz": (w == VIZ["writer"] and f0 == VIZ["f0"] and (cfg == VIZ["config"] or cfg in VIZ_EXTRA))})
            jobs.append({"writer": w, "f0": 5.0, "config": cfg, "kind": "micrographia", "viz": False})
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            outs = list(ex.map(scenario, jobs))
    else:
        outs = [scenario(j) for j in jobs]
    sweep_jobs = [{"writer": w, "f0": 6.0, "config": cfg} for cfg in ("revA", "pencil_like", "pencil_0.3N")
                  for w in range(min(args.writers, 4))]
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            sweep_rows = [r for rows in ex.map(sweep_job, sweep_jobs) for r in rows]
    else:
        sweep_rows = [r for j in sweep_jobs for r in sweep_job(j)]
    be = breakeven(sweep_rows)
    table, f0tab = aggregate(outs)
    micro = micro_aggregate(outs)
    safety = safety_aggregate(outs)
    viz = [c for o in outs if "viz" in o for c in o.pop("viz")]
    for o in outs:
        o.pop("letters", None) if o["job"]["kind"] == "micrographia" else None
    first = next(o for o in outs if o["job"]["kind"] == "tremor")
    res = {"meta": provenance.metadata(EVIDENCE_SIM, seeds={"writers": list(range(args.writers)), "f0_hz": args.f0,
                                                            "tremor": "3000+10w+f0", "sensor_noise": "11+w",
                                                            "calibration": "1000+w", "sentence_instance": "2000+w"},
                                       extra={"model": "M1 (sim/pensim, unmodified)",
                                              "configs": {k: v["label"] for k, v in G.CONFIGS.items()},
                                              "authority_rule": f"c = min(1, c_hat/{G.C_FULL}), 0 below c_hat {G.C_MIN}; levels {G.LEVELS}",
                                              "lm": "char KN 7-gram + word KN bigram, Tatoeba CC0 (results/ai/text_predictor.json)"}),
           "setup": {"sentence": GUIDE_SENTENCE, "calibration_sentence": CALIB_SENTENCE, "tremor_amp_m": AMP,
                     "f0_hz": args.f0, "writers": args.writers, "prediction_depth_glyphs": DEPTH,
                     "micrographia": "35 % linear size decrement along the line, no tremor, template at calibration size"},
           "predictions_for_sentence": next(o["predictions"] for o in outs if o.get("predictions")),
           "wrong_word": first["wrong_word"],
           "summary": table, "by_frequency": f0tab, "micrographia": micro, "safety": safety,
           "breakeven": {"method": "intended letters warped by a smooth random field (first point kept), guided at full "
                                   "authority; writers 0-3, 6 Hz 0.3 mm tremor", "by_config": be, "rows": sweep_rows},
           "splice_checks": [dict(o["splice"], job=o["job"]) for o in outs if "splice" in o],
           "scenarios": [{k: v for k, v in o.items() if k not in ("letters",)} for o in outs],
           "runtime_s": round(time.time() - t0, 1)}
    provenance.write_json(str(RESULTS_DIR / "guidance.json"), res)
    vz = {"meta": provenance.metadata(EVIDENCE_SIM + "; synthetic writer, 100 Hz export",
                                      seeds={"writer": VIZ["writer"], "f0_hz": VIZ["f0"]},
                                      extra={"config": G.CONFIGS[VIZ["config"]]["label"], "sentence": GUIDE_SENTENCE,
                                             "notes": ["template: the template trajectory at 50 Hz including pen-up moves; template_pen_down flags its pen-down points; empty for no-guidance cases",
                                                       "confidence: predictor confidence of the letter being written (1 for oracle and forced cases)",
                                                       "authority: effective stage authority g_eff recorded by the simulator",
                                                       "housing z: simulator housing height (mm); ink = deposited nib position",
                                                       "the pencil concept's piezo stage and skid are not in M1"]}),
          "units": {"length": "mm", "time": "s"}, "cases": viz}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "viz_guided.json", "w", encoding="utf-8") as f:   # compact: the 3D-view file must stay < 2 MB
        json.dump(vz, f, separators=(",", ":"), default=provenance._default)
    fig_summary(table, RESULTS_DIR / "fig_guidance_summary.png")
    fig_frequency(f0tab, RESULTS_DIR / "fig_guidance_frequency.png")
    if viz:
        fig_example(viz, RESULTS_DIR / "fig_guidance_example.png")
    fig_micro(outs, RESULTS_DIR / "fig_micrographia.png")
    fig_breakeven(be, RESULTS_DIR / "fig_guidance_breakeven.png")
    print("breakeven", {k: (v["breakeven_template_rms_um_path"], v["breakeven_template_rms_um_dtw"]) for k, v in be.items()})
    for cfg, d in table.items():
        print(cfg)
        for case, m in sorted(d.items()):
            print(f"  {case:34s} path {m['path_rms_um']['mean']:6.0f}  p95 {m['path_p95_um']['mean']:6.0f}  "
                  f"dtw {m.get('dtw_mean_um', {}).get('mean', float('nan')):6.0f}  "
                  f"rec {m.get('recognition_accuracy', {}).get('mean', float('nan')):.2f}  "
                  f"lim {m.get('at_soft_limit', {}).get('mean', float('nan')):.2f}  "
                  f"imp {m.get('max_imposed_um', {}).get('mean', float('nan')):6.0f}")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "cases"} for k, v in micro.items()}, indent=1))
    print(json.dumps(safety, indent=1))
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
