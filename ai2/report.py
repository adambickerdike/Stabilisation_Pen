"""Stage report: figures (each with a CSV twin), ai2.json (with stabpen.provenance metadata), samples.json (delayed-ink
before/after strips in the schema of results/aiprior/samples.json) and the proposed ledger rows (evidence.py).

Evidence status: SIMULATION / CALCULATION on synthetic writers and public text; nothing measured on a person or a pen.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import (EVIDENCE_SIM, F0S, AMPS, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, __version__, ensure_paths)
from . import common as C

ensure_paths()
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from handwriting import figures as FG  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402

S = plotstyle.SERIES
STATUS = "SIMULATION (model HW1)"
LABELS = {
    "none": "Ordinary pen", "revH_off": "Rev H, nose held", "tracker": "Rev H + tracker (as built)",
    "gated": "Rev H + gated listening tracker (causal)",
    "delayed_3mm": "Delayed ink, +-3 mm nose (chosen on seed 300)", "delayed_6mm": "Delayed ink, +-6 mm nose (chosen on seed 300)",
    "lag_25_6mm": "Delayed ink 25 ms, +-6 mm", "lag_50_6mm": "Delayed ink 50 ms, +-6 mm", "lag_100_6mm": "Delayed ink 100 ms, +-6 mm",
    "limit_50_6mm": "Delayed ink 50 ms, Z-refill contact delay (limit)", "limit_100_6mm": "Delayed ink 100 ms, Z-refill contact delay (limit)",
    "oracle": "Rev H, perfect knowledge (limit)", "oracle_delayed_50_3mm": "Perfect knowledge, 50 ms delay, +-3 mm (limit)",
    "oracle_delayed_100_6mm": "Perfect knowledge, 100 ms delay, +-6 mm (limit)",
    "clean_copy": "App clean copy (digital, after writing)",
    "learned_tcn": "Learned TCN (causal)", "learned_ctx": "Learned TCN + 20 s calibration",
    "learned_hybrid": "Hybrid Kalman-network (causal)", "learned_transformer": "Learned transformer (causal)",
    "rl_arbiter": "RL arbiter (shared control)", "rl_residual": "Residual RL on the command",
    "learned_delayed_3mm": "Delayed ink, learned fixed-lag estimator, +-3 mm", "learned_delayed_6mm": "Delayed ink, learned fixed-lag estimator, +-6 mm",
}
SHORT = {
    "none": "ordinary pen", "revH_off": "nose held", "tracker": "Rev H tracker", "gated": "gated tracker",
    "delayed_3mm": "delayed, 3 mm", "delayed_6mm": "delayed, 6 mm", "lag_25_6mm": "25 ms, 6 mm", "lag_50_6mm": "50 ms, 6 mm",
    "lag_100_6mm": "100 ms, 6 mm", "limit_50_6mm": "50 ms Z-refill", "limit_100_6mm": "100 ms Z-refill", "oracle": "perfect (limit)",
    "oracle_delayed_50_3mm": "perfect +50 ms", "oracle_delayed_100_6mm": "perfect +100 ms", "clean_copy": "app clean copy",
    "learned_tcn": "TCN", "learned_ctx": "TCN + calibration", "learned_hybrid": "hybrid", "learned_transformer": "transformer",
    "rl_arbiter": "RL arbiter", "rl_residual": "residual RL", "learned_delayed_3mm": "learned delayed, 3 mm",
    "learned_delayed_6mm": "learned delayed, 6 mm",
}
COL = {"none": plotstyle.MUTED, "tracker": S[1], "gated": S[0], "delayed_3mm": S[2], "delayed_6mm": S[5], "oracle": S[6],
       "clean_copy": S[4], "learned_tcn": S[3], "learned_ctx": S[3], "learned_hybrid": S[7], "learned_transformer": S[3],
       "rl_arbiter": S[4], "rl_residual": S[4]}
METRICS = ("ink_err_um", "recognition", "word_acc_app", "coverage", "q_p95_mm", "q_p99_mm", "over_3mm", "over_6mm", "at_travel_limit",
           "lag_mean_ms", "q_rms_mm")


def _is(amp_mm: float, which: str) -> bool:
    return (amp_mm >= 1.0) if which == "1_2mm" else (0 < amp_mm < 0.5) if which == "0p3mm" else False


# ------------------------------------------------------------------ aggregation of the test grid
def test_rows(test: Dict) -> List[Dict]:
    rows = []
    for o in test["outs"]:
        for r in o["rows"]:
            rows.append({"writer": o["writer"], "seed": r["seed"], "f0": r["f0"], "amp_mm": r["amp_mm"], "v": r["variants"],
                         "gate_open_frac": r.get("gate_open_frac")})
    return rows


def _mean(vals) -> Optional[float]:
    v = [x for x in vals if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else None


def aggregate(test: Dict) -> Dict:
    rows = test_rows(test)
    names = sorted({k for r in rows for k in r["v"]})
    free = [o["tremor_free"] for o in test["outs"]]
    out = {"variants": names, "n_scenarios": len(rows), "by_condition": {}, "summary": {}, "tremor_free": {}}
    for nm in names:
        bc = {}
        for f0 in F0S:
            for a in AMPS:
                sel = [r["v"][nm] for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - a * 1e3) < 1e-6 and nm in r["v"]]
                bc[f"{f0:g}Hz_{a * 1e3:g}mm"] = {k: _mean([m.get(k) for m in sel]) for k in METRICS} | {"n": len(sel)}
        out["by_condition"][nm] = bc
        sm = {}
        for which in ("1_2mm", "0p3mm"):
            sel = [r["v"][nm] for r in rows if _is(r["amp_mm"], which) and nm in r["v"]]
            for k in METRICS:
                sm[f"{k}_{which}"] = _mean([m.get(k) for m in sel])
        for f0 in F0S:
            sel = [r["v"][nm] for r in rows if r["f0"] == f0 and r["amp_mm"] >= 1.0 and nm in r["v"]]
            sm[f"ink_err_um_{f0:g}Hz_1_2mm"] = _mean([m.get("ink_err_um") for m in sel])
            sm[f"recognition_{f0:g}Hz_1_2mm"] = _mean([m.get("recognition") for m in sel])
        out["summary"][nm] = sm
        fr = [f["variants"][nm] for f in free if nm in f["variants"]]
        if fr:
            out["tremor_free"][nm] = {"false_correction_um": _mean([m.get("false_correction_um") for m in fr]),
                                      "false_correction_max_um": float(max([m.get("false_correction_um") or 0.0 for m in fr])),
                                      "recognition": _mean([m.get("recognition") for m in fr]),
                                      "word_acc_app": _mean([m.get("word_acc_app") for m in fr]),
                                      "ink_err_um": _mean([m.get("ink_err_um") for m in fr]), "n": len(fr)}
    out["gate_open_frac_by_condition"] = {f"{f0:g}Hz_{a * 1e3:g}mm": _mean([r["gate_open_frac"] for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - a * 1e3) < 1e-6])
                                          for f0 in F0S for a in AMPS}
    out["gate_open_frac_tremor_free"] = _mean([f.get("gate_open_frac") for f in free])
    out["rules_on_test"] = rules_on_test(test)
    out["paired"] = paired(test)
    return out


def rules_on_test(test: Dict) -> Dict:
    """The tuning rules R1-R4 (stage D2) recomputed on the test grid, for every variant with the needed metrics."""
    from . import tuning as TU
    outs = [{"rows": [{"f0": r["f0"], "amp_mm": r["amp_mm"], "v": r["variants"]} for r in o["rows"]] +
             [{"f0": 0.0, "amp_mm": 0.0, "v": o["tremor_free"]["variants"]}]} for o in test["outs"]]
    tab = TU.select_d2(outs, [])["table"]
    keep = [k for k in tab if not k.startswith(("none", "revH_off", "clean_copy", "oracle")) and not k.startswith("limit")]
    return {k: {kk: tab[k][kk] for kk in ("R1", "R2", "R3", "R4", "passes", "fc_um", "tracker_fc_um", "J_ink_1_2mm_um",
                                           "tracker_J_ink_1_2mm_um", "ink_0p3mm_um", "letters_1_2mm", "coverage_1_2mm")}
            for k in keep}


def paired(test: Dict, n_boot: int = 4000) -> Dict:
    """Paired differences (variant - reference) of the ink error at 1-2 mm and of letters read at 1-2 mm, averaged per
    (writer, seed) cluster, with a 95 % percentile bootstrap over the 24 clusters."""
    rows = test_rows(test)
    pairs = [("gated", "tracker"), ("delayed_3mm", "gated"), ("delayed_6mm", "gated"), ("delayed_3mm", "tracker"),
             ("lag_50_6mm", "gated"), ("lag_100_6mm", "gated"), ("limit_100_6mm", "gated")]
    pairs += [(k, "gated") for k in ("learned_tcn", "learned_ctx", "learned_hybrid", "learned_transformer", "rl_arbiter", "rl_residual")]
    pairs += [(k, "tracker") for k in ("learned_tcn", "learned_ctx", "learned_hybrid", "learned_transformer", "rl_arbiter", "rl_residual")]
    rng = np.random.default_rng(0)
    out = {}
    for a, b in pairs:
        for metric in ("ink_err_um", "recognition"):
            cl = {}
            for r in rows:
                if r["amp_mm"] < 1.0 or a not in r["v"] or b not in r["v"]:
                    continue
                x, y = r["v"][a].get(metric), r["v"][b].get(metric)
                if x is None or y is None:
                    continue
                cl.setdefault((r["writer"], r["seed"]), []).append(x - y)
            if not cl:
                continue
            d = np.array([np.mean(v) for v in cl.values()])
            bs = np.array([np.mean(d[rng.integers(0, len(d), len(d))]) for _ in range(n_boot)])
            out[f"{a}-{b}:{metric}"] = {"mean": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                        "n_clusters": int(len(d)), "conditions": "1-2 mm, 6-10 Hz"}
    return out


# ------------------------------------------------------------------ figures
def fig_delayed(agg: Dict, od: Path) -> None:
    sm, tf = agg["summary"], agg["tremor_free"]
    lags = [0, 25, 50, 100]
    def pick(*names):
        return next((n for n in names if n in sm), None)
    series_def = [("Catch-up lag, RTS smoother + detector", ["gated", pick("lag_25_6mm", "delayed_3mm"), pick("lag_50_6mm", "delayed_6mm"), "lag_100_6mm"], S[0], "-"),
                  ("Z-refill contact delay (limit policy), +-6 mm", ["gated", None, pick("limit_50_6mm"), "limit_100_6mm"], S[2], "--"),
                  ("Perfect knowledge + lag (limit)", ["oracle", None, pick("oracle_delayed_50_3mm"), "oracle_delayed_100_6mm"], S[6], ":")]
    panels = []
    for key, title, yl, src in (("ink_err_um_1_2mm", "Ink error, 1-2 mm tremor (um RMS)", "um", "sm"),
                                ("recognition_1_2mm", "Letters read, 1-2 mm tremor", "share", "sm"),
                                ("coverage_1_2mm", "Intended path covered by ink (0.3 mm), 1-2 mm", "share", "sm"),
                                ("q_p95_mm_1_2mm", "Nose travel needed, p95 (mm), 1-2 mm", "mm", "sm"),
                                ("ink_err_um_0p3mm", "Ink error, 0.3 mm tremor (um RMS)", "um", "sm"),
                                ("false_correction_um", "Tremor-free writing moved (um RMS)", "um", "tf")):
        ser = []
        for lab, names, col, ls in series_def:
            ys = []
            for nm in names:
                if nm is None:
                    ys.append(float("nan")); continue
                v = (sm.get(nm, {}) if src == "sm" else tf.get(nm, {})).get(key)
                ys.append(float("nan") if v is None else v)
            if any(np.isfinite(ys)):
                ser.append({"label": lab, "y": ys, "color": col, "ls": ls})
        tr = (sm.get("tracker", {}) if src == "sm" else tf.get("tracker", {})).get(key)
        if tr is not None:
            ser.append({"label": "Rev H tracker (as built)", "y": [tr] * len(lags), "color": S[1], "ls": "-."})
        panels.append({"title": title, "x": lags, "xlabel": "ink lag behind the hand (ms)", "ylabel": yl, "series": ser, "xticks": lags})
    FG.lines_chart(od / "fig_delayed_ink.png", panels, STATUS,
                   "Test writers 0-5 x seeds 200-203 x 6/8/10 Hz. 0 ms = the causal gated tracker; 25 ms = the chosen +-3 mm setting, 50 and 100 ms = +-6 mm.")


def _fmt_um(v):
    return "n/a" if v is None else f"{v:.0f} um"


def fig_before_after(test: Dict, od: Path) -> None:
    viz, rows, writer = None, None, None
    for o in test["outs"]:
        if o.get("viz"):
            viz, rows, writer = o["viz"], o["rows"], o["writer"]
    if viz is None:
        return
    keys = ["intended", "none", "tracker", "gated", "delayed_3mm", "delayed_6mm", "lag_100_6mm", "limit_100_6mm", "clean_copy", "oracle"]
    labels = {"intended": "Intended", "none": "Ordinary pen", "tracker": "Rev H + tracker\n(as built)",
              "gated": "Gated listening\ntracker (0 ms)", "delayed_3mm": "Delayed ink,\n+-3 mm nose", "delayed_6mm": "Delayed ink,\n+-6 mm nose",
              "lag_100_6mm": "Delayed ink 100 ms\n(catch-up), +-6 mm", "limit_100_6mm": "Delayed ink 100 ms\n(Z-refill limit)",
              "clean_copy": "App clean copy\n(digital, not ink)", "oracle": "Perfect knowledge\n(limit)"}
    cols = []
    for case in [k for k in viz if "Hz_" in k]:
        f0 = float(case.split("Hz")[0]); amp = float(case.split("_")[1].rstrip("mm"))
        r = next((r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
        metrics = {}
        for dv in keys[1:]:
            if r is None or dv not in r["variants"]:
                continue
            m = r["variants"][dv]
            nw = len(str(m.get("recognised_words", "")).split()) or 5
            txt = f"ink error {_fmt_um(m.get('ink_err_um'))}  ·  letters read {m.get('recognition', 0):.0%}\nwords read by the app {round((m.get('word_acc_app') or 0) * nw)}/{nw}"
            if m.get("lag_mean_ms"):
                txt += f"  ·  mean lag {m['lag_mean_ms']:.0f} ms"
            metrics[dv] = txt
        paths = {k: viz[case][k] for k in keys if k in viz[case]}
        paths["intended"] = viz["intended"]
        metrics["intended"] = "what the writer meant to write\n(the same hand without tremor)"
        cols.append({"title": f"hand tremor {amp:g} mm peak at {f0:g} Hz (writer {writer}, seed 200)", "paths": paths,
                     "intended": viz["intended"], "metrics": metrics, "x_height": viz.get("x_height_mm", 2.5)})
    FG.before_after(od / "fig_before_after.png", cols, keys, labels, STATUS,
                    "Delayed ink = the nose follows a fixed-lag estimate, so the ink trails the hand by the lag (the writer sees the ink "
                    "that far behind the pen's travel). Grey dashes: intended letters. Synthetic writer and tremor; nothing measured.",
                    suptitle="Delayed ink: the same sentence, hand and tremor, with each estimator")


def fig_separation(agg: Dict, od: Path) -> None:
    sm, tf = agg["summary"], agg["tremor_free"]
    order = [k for k in ("tracker", "gated", "learned_tcn", "learned_ctx", "learned_transformer", "learned_hybrid", "rl_arbiter",
                         "rl_residual", "delayed_3mm", "oracle") if k in sm]
    labs = [SHORT[k] for k in order]
    cols = [COL.get(k, S[0]) for k in order]
    panels = [{"title": "Ink error, 1-2 mm tremor (um RMS)", "labels": labs, "values": [sm[k].get("ink_err_um_1_2mm") for k in order], "colors": cols, "fmt": "{:.0f}"},
              {"title": "Ink error, 0.3 mm tremor (um RMS)", "labels": labs, "values": [sm[k].get("ink_err_um_0p3mm") for k in order], "colors": cols, "fmt": "{:.0f}"},
              {"title": "Tremor-free writing moved (um RMS)", "labels": labs, "values": [tf.get(k, {}).get("false_correction_um") for k in order],
               "colors": cols, "fmt": "{:.1f}", "ref": 25.0},
              {"title": "Letters read, 1-2 mm tremor", "labels": labs, "values": [sm[k].get("recognition_1_2mm") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Words read by the app, 1-2 mm tremor", "labels": labs, "values": [sm[k].get("word_acc_app_1_2mm") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Ink error, 6 Hz 1-2 mm (um RMS)", "labels": labs, "values": [sm[k].get("ink_err_um_6Hz_1_2mm") for k in order], "colors": cols, "fmt": "{:.0f}"}]
    FG.bars_chart(od / "fig_separation.png", panels, STATUS,
                  "Test grid; causal estimators at lag 0 on the Rev H nose (+-3 mm); dashed line: REQ-ML-001's 25 um false-correction line.")


def fig_training(learn: Optional[Dict], rl: Optional[Dict], od: Path) -> None:
    plotstyle.apply()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
    rows = []
    if learn:
        for i, (mode, info) in enumerate(learn["models"].items()):
            h = info.get("history", [])
            if not h:
                continue
            x = [e["step"] for e in h]; y = [e["val"] for e in h]
            axes[0].plot(x, y, color=S[i % len(S)], label=f"{mode} ({info['n_params']} parameters)")
            rows += [["learned", mode, xx, yy] for xx, yy in zip(x, y)]
        for k, lab, ls in (("model_based_stack", "model-based stack", "--"), ("rts_ungated", "RTS smoother, ungated", ":")):
            ref = learn.get("reference", {}).get(k, {}).get("J")
            if ref:
                axes[0].axhline(ref, color=plotstyle.MUTED, ls=ls, lw=1, label=lab)
                rows.append(["learned", k, "", ref])
        axes[0].set_title("Learned estimators: tuning score J (um) vs training step", fontsize=9.5, loc="left")
        axes[0].set_xlabel("training step (batch of 24 x 3 s, one CPU thread)"); axes[0].set_ylabel("J (um)")
        axes[0].legend(fontsize=7, frameon=False)
    if rl:
        for i, (name, pol) in enumerate(rl.get("policies", {}).items()):
            x = [c["steps"] for c in pol["checkpoints"]]; y = [c["reward_mean"] for c in pol["checkpoints"]]
            axes[1].plot(x, y, color=S[(i + 4) % len(S)], marker="o", ms=3, label=f"{name} ({pol['wall_min']:.0f} min)")
            rows += [["rl", name, xx, yy] for xx, yy in zip(x, y)]
        axes[1].axhline(0.0, color=plotstyle.MUTED, lw=1)
        mb = rl.get("model_based_arbiter", {}).get("reward_mean")
        if mb is not None:
            axes[1].axhline(mb, color=plotstyle.MUTED, ls="--", lw=1, label="model-based gate (same reward)")
            rows.append(["rl", "model_based_arbiter", "", mb])
        axes[1].set_title("RL policies: mean tuning reward vs environment steps", fontsize=9.5, loc="left")
        axes[1].set_xlabel("environment steps"); axes[1].set_ylabel("reward per decision (vs base)")
        axes[1].legend(fontsize=7, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, STATUS, "tuning writers 100-103, seed 300 (replay objective)")
    fig.savefig(od / "fig_training.png"); plt.close(fig)
    FG.write_csv(od / "fig_training.csv", ["panel", "series", "x", "y"], rows)


def fig_text(text: Dict, od: Path) -> None:
    ev = text["eval"]
    models = [m for m in ("NG0", "NG1", "TF_small", "TF", "MIX") if m in ev]
    panels = []
    for sname, stitle in (("tatoeba_test", "Tatoeba test"), ("common_voice_test", "Common Voice test"), ("note_lines", "app note lines")):
        for key, sub, t in (("glyph_d2", "top1", "letter two ahead, top-1"), ("glyph_d2", "top3", "letter two ahead, top-3"),
                            ("next_word", "top1", "next word, top-1"), ("next_word", "top3", "next word, top-3")):
            vals = [ev[m].get(sname, {}).get(key, {}).get(sub) for m in models]
            if any(v is not None for v in vals):
                panels.append({"title": f"{stitle}: {t}", "labels": models, "values": vals, "colors": [S[i] for i in range(len(models))],
                               "fmt": "{:.2f}", "xlim": (0, 1)})
    FG.bars_chart(od / "fig_text.png", panels, "CALCULATION (public CC0 text)", "NG = n-gram (NG0 = aiguide as used so far); TF = small "
                  "character transformer; MIX = TF + NG1", ncols=4, size=(14.0, 3.6))


def fig_synth(synth: Dict, od: Path) -> None:
    A = synth.get("A_synthetic_writers", {})
    ex = A.get("examples_mm") or {}
    methods = [("held", "held-out real\ninstance"), ("font", "font in the\nwriter's style"), ("copy", "copy of one\nreference"),
               ("sl_recon", "sigma-lognormal\nreconstruction"), ("sl_k1", "sigma-lognormal,\n1 reference"), ("sl_k3", "sigma-lognormal,\n3 references")]
    plotstyle.apply()
    letters = sorted(ex)
    fig = plt.figure(figsize=(12.5, 6.2))
    rows = []
    if letters:
        gs = fig.add_gridspec(len(methods), len(letters) + 3, wspace=0.15, hspace=0.25)
        for i, (m, lab) in enumerate(methods):
            for j, ch in enumerate(letters):
                ax = fig.add_subplot(gs[i, j])
                strokes = ex[ch].get(m)
                if m == "held" and strokes:
                    strokes = strokes[0]
                for s in strokes or []:
                    a = np.asarray(s, float)
                    if a.ndim == 2 and len(a):
                        ax.plot(a[:, 0], a[:, 1], color=plotstyle.INK, lw=1.2)
                        rows += [[m, ch, k, float(p[0]), float(p[1])] for k, p in enumerate(a[::4])]
                ax.set_aspect("equal"); ax.axis("off")
                if i == 0:
                    ax.set_title(f"'{ch}'", fontsize=9)
                if j == 0:
                    ax.text(-0.35, 0.5, lab, transform=ax.transAxes, fontsize=7.5, ha="right", va="center")
        axb = fig.add_subplot(gs[:, len(letters) + 1:])
    else:
        axb = fig.add_subplot(111)
    ms = [m for m in ("font", "copy", "sl_recon", "sl_k1", "sl_k3") if m in A]
    yy = np.arange(len(ms))
    leg = [A[m]["legibility"] for m in ms]; wid = [A[m]["writer_id_acc"] for m in ms]
    axb.barh(yy + 0.2, leg, height=0.38, color=S[0], label="legible (app recogniser)")
    axb.barh(yy - 0.2, wid, height=0.38, color=S[2], label="writer identified (6 writers)")
    axb.set_yticks(yy); axb.set_yticklabels(ms, fontsize=8); axb.set_xlim(0, 1.15)
    for y0, a, b in zip(yy, leg, wid):
        axb.text(a, y0 + 0.2, f" {a:.2f}", va="center", fontsize=7); axb.text(b, y0 - 0.2, f" {b:.2f}", va="center", fontsize=7)
    if "chance_writer_id" in A:
        axb.axvline(A["chance_writer_id"], color=plotstyle.MUTED, ls="--", lw=1)
    axb.legend(fontsize=7, frameon=False, loc="lower right")
    axb.set_title("Synthetic test writers 0-5, 26 letters", fontsize=9, loc="left")
    rows += [["bars", m, "legibility", a, b] for m, a, b in zip(ms, leg, wid)]
    plotstyle.stamp(fig, "CALCULATION (synthetic writers)", f"writer {A.get('examples_writer', 0)}; mm")
    fig.savefig(od / "fig_synthesis.png"); plt.close(fig)
    FG.write_csv(od / "fig_synthesis.csv", ["method", "letter", "index", "x_mm_or_legibility", "y_mm_or_writer_id"], rows)


def fig_shared(shared: Dict, od: Path) -> None:
    t = shared["test"]
    order = [k for k in ("none", "fixed_partial", "fixed_full", "aan", "aan_fade", "check_plant_partial") if k in t]
    lab = {"none": "no guidance", "fixed_partial": "fixed 0.5", "fixed_full": "fixed 1.0", "aan": "assist as needed",
           "aan_fade": "AAN, faster fade", "check_plant_partial": "plant guide mode 0.5 (check)"}
    labs = [lab[k] for k in order]
    cols = [S[i % len(S)] for i in range(len(order))]
    panels = [{"title": "Distance of the ink to the target letters (um RMS)", "labels": labs, "values": [t[k].get("target_err_um") for k in order], "colors": cols, "fmt": "{:.0f}"},
              {"title": "Device share of the ink motion", "labels": labs, "values": [t[k].get("device_share") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Letters read", "labels": labs, "values": [t[k].get("letters_read_ok") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Mean guidance gain on malformed letters", "labels": labs, "values": [t[k].get("gain_on_malformed") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Mean guidance gain on well-formed letters", "labels": labs, "values": [t[k].get("gain_on_wellformed") for k in order], "colors": cols, "fmt": "{:.2f}"},
              {"title": "Nose deflection RMS (mm)", "labels": labs, "values": [t[k].get("nose_q_rms_mm") for k in order], "colors": cols, "fmt": "{:.2f}"}]
    FG.bars_chart(od / "fig_shared_control.png", panels, STATUS,
                  "Guided copying by dysgraphia-like synthetic learners (passive hand, no learning); test writers 0-5, seeds 200-203.")


def fig_tuning(d2b: Optional[Dict], cl: Optional[Dict], od: Path) -> None:
    panels = []
    if d2b:
        tab = d2b["selection"]["table"]
        ks = sorted(tab, key=lambda k: tab[k]["J_ink_1_2mm_um"])[:14]

        def short(k):
            lam = k.split("lam_max")[1].split("_")[0]
            lo = k.split("amp_lo")[1].split("_")[0]
            return f"{float(lam) * 1e3:.0f} ms, amp gate {float(lo) * 1e3:.2f} mm, nose {k[-1]}"
        panels.append({"title": "D2b: ink error 1-2 mm (um), tuning seed 300 (* = passes R1-R4)",
                       "labels": [("* " if tab[k]["passes"] else "  ") + short(k) for k in ks],
                       "values": [tab[k]["J_ink_1_2mm_um"] for k in ks], "colors": [S[0] if tab[k]["passes"] else plotstyle.MUTED for k in ks],
                       "fmt": "{:.0f}", "ref": tab[ks[0]]["tracker_J_ink_1_2mm_um"]})
    if cl:
        tab = cl["table"]
        ks = sorted(tab, key=lambda k: tab[k]["J_ink_1_2mm_um"])
        panels.append({"title": "cl: learned and RL candidates, ink error 1-2 mm (um), tuning seeds 300-301 (* = passes R1-R4)",
                       "labels": [("* " if tab[k]["passes"] else "  ") + SHORT.get(k, k) for k in ks],
                       "values": [tab[k]["J_ink_1_2mm_um"] for k in ks], "colors": [S[0] if tab[k]["passes"] else plotstyle.MUTED for k in ks],
                       "fmt": "{:.0f}", "ref": tab[ks[0]]["tracker_J_ink_1_2mm_um"]})
    if panels:
        FG.bars_chart(od / "fig_tuning.png", panels, "SIMULATION (model HW1), tuning writers 100-103",
                      "dashed line: the Rev H tracker on the same runs", ncols=2, size=(13.0, 5.2), share_labels=False)


# ------------------------------------------------------------------ kinematics of a lagging ink (CALC)
KIN_LAGS = (0.025, 0.05, 0.1, 0.25)


def kinematics(writers: Sequence[int] = TEST_WRITERS, lags: Sequence[float] = KIN_LAGS) -> Dict:
    """CALC on the writers' intended paths (no tremor, no plant): for an ink that trails the hand by lag along the path,
    the hand-ink distance |x(t) - x(t - lag)| over pen-down time (the nose travel the lag alone needs) and the share of
    pen-down time whose point lag earlier lies in the same stroke (the rest are stroke starts, where a catch-up policy
    must shorten the lag, and stroke ends, which a lagging ink cuts short unless the contact itself is delayed)."""
    from aiprior import core as CO
    out = {"writers": list(writers), "lags_s": list(lags), "per_writer": {}}
    for w in writers:
        it = CO.Writer(w).written.intended
        dec = max(1, int(round(1e-3 / float(it.t[1] - it.t[0]))))
        xy = np.asarray(it.xy)[::dec]; down = np.asarray(it.pen_down)[::dec].astype(bool)
        sid = np.cumsum(np.r_[down[0], down[1:] & ~down[:-1]])
        sp = np.hypot(*np.gradient(xy, 1e-3, axis=0).T)[down]
        row = {"speed_median_mm_s": float(np.median(sp) * 1e3), "speed_p95_mm_s": float(np.percentile(sp, 95) * 1e3)}
        for lag in lags:
            n = int(round(lag * 1e3))
            k = np.flatnonzero(down); k = k[k >= n]
            d = np.hypot(*(xy[k] - xy[k - n]).T)
            same = (sid[k] == sid[k - n]) & down[k - n]
            row[f"{lag * 1e3:.0f}ms"] = {"disp_p50_mm": float(np.median(d) * 1e3), "disp_p95_mm": float(np.percentile(d, 95) * 1e3),
                                         "share_full_lag_in_stroke": float(np.mean(same))}
        out["per_writer"][str(w)] = row
    for lag in lags:
        key = f"{lag * 1e3:.0f}ms"
        vals = [r[key] for r in out["per_writer"].values()]
        out[key] = {k: [float(min(v[k] for v in vals)), float(max(v[k] for v in vals))] for k in vals[0]}
    return out


def fig_kinematics(kin: Dict, od: Path) -> None:
    lags = [l * 1e3 for l in kin["lags_s"]]
    ser_d, ser_s = [], []
    for i, (w, r) in enumerate(kin["per_writer"].items()):
        ser_d.append({"label": f"writer {w}", "y": [r[f"{l:.0f}ms"]["disp_p95_mm"] for l in lags], "color": S[i % len(S)]})
        ser_s.append({"label": f"writer {w}", "y": [r[f"{l:.0f}ms"]["share_full_lag_in_stroke"] for l in lags], "color": S[i % len(S)]})
    FG.lines_chart(od / "fig_lag_kinematics.png",
                   [{"title": "Hand-ink distance over the lag, p95 (mm)", "x": lags, "xlabel": "ink lag (ms)", "ylabel": "mm", "series": ser_d, "xticks": lags},
                    {"title": "Pen-down time with the full lag inside the stroke", "x": lags, "xlabel": "ink lag (ms)", "ylabel": "share", "series": ser_s,
                     "xticks": lags, "ylim": (0, 1)}],
                   "CALCULATION (intended paths)", "test writers 0-5, 'return library books by friday'; no tremor", ncols=2, size=(12.5, 4.2))


# ------------------------------------------------------------------ samples.json
def _dec(path, hz_in: float = 50.0, hz_out: float = 50.0, nd: int = 2, max_pts: int = 3000):
    p = np.asarray(path, float)
    step = max(1, int(round(hz_in / hz_out)))
    q = p[::step]
    if len(q) > max_pts:
        q = q[:: int(math.ceil(len(q) / max_pts))]
    return [[round(float(a), nd), round(float(b), nd), int(c > 0.5)] for a, b, c in q]


def samples(test: Dict, od: Path) -> Dict:
    panels = []
    keys = ["none", "tracker", "gated", "delayed_3mm", "delayed_6mm", "lag_100_6mm", "limit_100_6mm", "clean_copy", "oracle",
            "oracle_delayed_100_6mm"]
    for o in test["outs"]:
        if not o.get("viz"):
            continue
        v = o["viz"]
        for case in [k for k in v if "Hz_" in k]:
            f0 = float(case.split("Hz")[0]); amp = float(case.split("_")[1].rstrip("mm"))
            r = next((r for r in o["rows"] if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
            for dv in keys:
                if dv not in v[case]:
                    continue
                m = r["variants"].get(dv, {}) if r else {}
                digital = dv == "clean_copy"
                lagged = dv.startswith(("delayed", "lag_", "limit_", "oracle_delayed"))
                panels.append({"id": f"ai2_{dv}_{case}".replace(".", "p"), "title": f"{LABELS[dv]} - tremor {amp:g} mm at {f0:g} Hz",
                               "condition": "et_tremor_delayed_ink", "device": dv,
                               "caption": (f"Writer {o['writer']}, 'return library books by friday', hand tremor {amp:g} mm peak at {f0:g} Hz "
                                           "(seed 200). The same hand and tremor for every row. "
                                           + ("DIGITAL copy made by the app after writing (non-causal); the paper keeps the pen's ink."
                                              if digital else ("Ink on the paper; it trails the hand by the lag (mean "
                                                               f"{m.get('lag_mean_ms', 0) or 0:.0f} ms while writing)." if lagged
                                                               else "Ink on the paper (causal pen)."))),
                               "evidence": "SIM", "intended": _dec(v["intended"]), "ink": _dec(v[case][dv]),
                               "metrics": {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k)) for k in
                                           ("ink_err_um", "recognition", "word_acc_app", "recognised_words", "app_words", "coverage",
                                            "lag_mean_ms", "q_p95_mm", "at_travel_limit") if k in m}})
    doc = {"meta": provenance.metadata("SIMULATION (model HW1; synthetic writers; nothing measured)",
                                       seeds={"writers": list(TEST_WRITERS), "seeds": [200]},
                                       extra={"script": "ai2/report.py", "version": __version__,
                                              "schema": "panels[{id, title, condition, device, caption, evidence, intended [[x_mm, y_mm, pen_down]], ink [[...]], metrics}]; paths at 50 Hz, 0.01 mm",
                                              "units": "mm; page frame, x along the line, y up; pen_down 0/1"}),
           "panels": panels}
    (od / "samples.json").write_text(json.dumps(doc, separators=(",", ":")))
    return doc


# ------------------------------------------------------------------ summaries of the other stages
def learn_summary(learn: Optional[Dict], quick: bool = False) -> Optional[Dict]:
    if not learn:
        return None
    ref = learn.get("reference", {})
    try:            # recomputed from the tuning arrays (the stage's own Rev H reference repeated dh(t) at every lag;
        from . import stage_learn as SL        # corrected to dh(t - lag) after the stage ran; model scores unchanged)
        from . import stage_learn_data as SLD
        tune = SLD.load_tuning()
        if tune:
            ref = SL.references(tune, SLD.model_params(quick))
    except Exception:
        pass
    out = {"n_train": learn["n_train"], "rule": learn.get("rule"), "ranked": learn.get("ranked"), "best": learn.get("best_learned"),
           "reference": {k: {kk: v[kk] for kk in ("J", "res_1_2mm_um", "res_0p3mm_um", "leak_um", "by_lag_1_2mm_um", "by_f0_1_2mm_um") if kk in v}
                         for k, v in ref.items()}, "models": {}}
    for m, info in learn["models"].items():
        sc = info["tuning_score"]
        out["models"][m] = {"J": sc["J"], "res_1_2mm_um": sc["res_1_2mm_um"], "res_0p3mm_um": sc["res_0p3mm_um"], "leak_um": sc["leak_um"],
                            "by_lag_1_2mm_um": sc["by_lag_1_2mm_um"], "by_f0_1_2mm_um": sc.get("by_f0_1_2mm_um"),
                            "n_params": info["n_params"], "macs_per_step": info["macs_per_step"], "steps": info["steps"],
                            "train_minutes": info["minutes"], "receptive_field_steps": info["receptive_field_steps"], "cfg": info["cfg"],
                            "mcu_ms_per_step_int8": mcu_ms(info["macs_per_step"], len(info["cfg"].get("dil", [])) * 2 + 2 if "dil" in info["cfg"] else 12),
                            "weights_kB_int8": info["n_params"] / 1024.0}
    return out


def mcu_ms(macs: int, n_layers: int) -> float:
    """CALC (ASSUMPTION as fusion/budget.py): int8 CMSIS-NN 0.5 MAC/cycle + 300 cycles per layer call at 128 MHz."""
    return (macs / 0.5 + 300 * n_layers) / 128e6 * 1e3


def rl_summary(rl: Optional[Dict]) -> Optional[Dict]:
    if not rl:
        return None
    out = {"n_train": rl["n_train"], "rules": rl.get("rules"), "chosen_arbiter": rl.get("chosen_arbiter"),
           "chosen_residual": rl.get("chosen_residual"), "compute_min_total": rl.get("compute_min_total"),
           "model_based_arbiter": {k: v for k, v in rl.get("model_based_arbiter", {}).items() if k != "rows"}, "policies": {}}
    for k, p in rl.get("policies", {}).items():
        out["policies"][k] = {"algorithm": p["algorithm"], "env_steps": p["env_steps"], "wall_min": p["wall_min"], "train_min": p["train_min"],
                              "passes_rule": p["passes_rule"], "best": {kk: v for kk, v in p["best"].items() if kk != "path"},
                              "checkpoints": [{kk: v for kk, v in c.items() if kk != "path"} for c in p["checkpoints"]]}
    return out


def tuning_summary(d01, d2, d2b, cl) -> Dict:
    out = {}
    if d01:
        out["d0"] = {"chosen": d01.get("chosen_tremor"), "rule": "D0: lowest time-aligned tremor residual (1-2 mm, 6-10 Hz, lags 0/25/50 ms)",
                     "table": d01["d0"].get("table") if isinstance(d01.get("d0"), dict) else None}
        out["d1"] = {"chosen": d01.get("chosen_det"), "selection": {k: v for k, v in d01["d1"].items() if k != "rows"} if isinstance(d01.get("d1"), dict) else None}
    for name, d in (("d2", d2), ("d2b", d2b)):
        if d:
            out[name] = {"selection": d["selection"], "confirmation_seed_301": d.get("confirmation_seed_301"),
                         "candidates": d.get("candidates")}
    if cl:
        out["cl"] = {k: cl[k] for k in ("table", "passing", "best_passing", "adopted", "rules")}
    return out


# ------------------------------------------------------------------ build
def build(quick: bool = False) -> Dict:
    from . import evidence as EV
    od = C.out_dir(quick)
    L = {k: C.load(k, quick) for k in ("d01", "d2", "d2b", "learn_data", "learn", "rl", "cl", "test", "text", "synth", "shared")}
    agg = aggregate(L["test"]) if L["test"] else None
    if agg:
        fig_delayed(agg, od)
        fig_before_after(L["test"], od)
        fig_separation(agg, od)
        samples(L["test"], od)
    if L["learn"] or L["rl"]:
        fig_training(L["learn"], L["rl"], od)
    if L["text"]:
        fig_text(L["text"], od)
    if L["synth"]:
        fig_synth(L["synth"], od)
    if L["shared"]:
        fig_shared(L["shared"], od)
    fig_tuning(L["d2b"], L["cl"], od)
    kin = C.load("kinematics", quick)
    if kin is None:
        kin = kinematics(TEST_WRITERS[:2] if quick else TEST_WRITERS)
        C.save("kinematics", kin, quick)
    fig_kinematics(kin, od)
    doc = {"meta": provenance.metadata(EVIDENCE_SIM,
                                       seeds={"test_writers": list(TEST_WRITERS), "test_seeds": list(TEST_SEEDS),
                                              "tune_writers": list(TUNE_WRITERS), "tune_seeds": list(TUNE_SEEDS),
                                              "train_writers": ">= 1000", "train_seeds": ">= 5000"},
                                       extra={"script": "ai2/run_study.py", "version": __version__, "quick": quick}),
           "labels": LABELS,
           "tuning": tuning_summary(L["d01"], L["d2"], L["d2b"], L["cl"]),
           "test_settings": L["test"]["settings"] if L["test"] else None,
           "test_candidates": L["test"].get("candidates") if L["test"] else None,
           "aggregate": agg,
           "lag_kinematics_calc": kin,
           "learn": learn_summary(L["learn"], quick),
           "rl": rl_summary(L["rl"]),
           "text": ({k: v for k, v in L["text"].items()} if L["text"] else None),
           "synth": L["synth"],
           "shared": ({k: v for k, v in L["shared"].items() if k != "tuning"} | {"tuning_summary": {k: {kk: vv for kk, vv in v.items()}
                                                                                                 for k, v in L["shared"]["tuning"].items()}}
                      if L["shared"] else None),
           "compute": compute_record(L)}
    provenance.write_json(str(od / "ai2.json"), doc)
    EV.write_rows(od / "evidence_rows.csv", doc)
    C.log(f"[report] wrote {od}")
    return doc


def compute_record(L: Dict) -> Dict:
    out = {"threads_per_process": 1, "note": "wall-clock on a shared 4-core machine (other studies running); one process for long runs"}
    if L.get("learn"):
        out["learn_train_min"] = {m: i.get("minutes") for m, i in L["learn"]["models"].items()}
    if L.get("rl"):
        out["rl_wall_min"] = {k: p.get("wall_min") for k, p in L["rl"].get("policies", {}).items()}
        out["rl_env_steps"] = {k: p.get("env_steps") for k, p in L["rl"].get("policies", {}).items()}
    if L.get("text"):
        out["text_min"] = L["text"].get("minutes_total")
    if L.get("synth"):
        out["synth_min"] = L["synth"].get("minutes")
    if L.get("test"):
        out["test_writer_jobs_s"] = [o.get("elapsed_s") for o in L["test"]["outs"]]
    return out


def run(quick: bool, workers: int):
    return build(quick)
