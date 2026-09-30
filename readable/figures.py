"""Figures with CSV twins (results/readable/fig_*.png + .csv).

Style: the project's validated palette and rules (stabpen/plotstyle.py: fixed categorical order, 2 px lines, markers with
a surface ring, hairline grid, text in ink colours, an evidence stamp on every figure).  Colours are fixed per entity in
every chart: residual type (a) amplitude blue, (b) lag violet, (c) noise green; the ordinary pen orange; perfect
knowledge magenta; the fitted curve ink.  Yellow and magenta are below 3:1 contrast, so every chart has a legend, direct
labels where they fit, and a CSV table.  One y-axis per panel.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

SIM_TAG = "SIMULATION (model HW1) with real recorded inputs; curve = CALCULATION"
COL = {"a": "#2a78d6", "b": "#4a3aa7", "c": "#1baf7a", "none": "#eb6834", "oracle": "#e87ba4", "curve": "#0b0b0b",
       "frozen": "#898781", "cal": "#2a78d6", "fir_raw": "#2a78d6", "ai2tcn_gated": "#008300", "net_gated": "#1baf7a",
       "akf_raw": "#4a3aa7", "ai2tcn_raw": "#eda100", "net_raw": "#e87ba4"}
TYPE_LABEL = {"a": "(a) tremor scaled: amplitude error", "b": "(b) perfect estimate delayed: lag error",
              "c": "(c) perfect + band-limited noise"}


def write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence], comments: Sequence[str] = ()):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        for c in comments:
            f.write("# " + str(c).replace("\n", " ") + "\n")
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if (isinstance(x, float) and not np.isfinite(x)) else
                        (round(x, 6) if isinstance(x, float) else x) for x in r])


def _plt():
    from stabpen import plotstyle as PS
    PS.apply()
    import matplotlib.pyplot as plt
    return plt, PS


def _mk(PS, color, marker="o", size=7):
    return dict(marker=marker, markersize=size, markerfacecolor=color, markeredgecolor=PS.SURFACE,
                markeredgewidth=1.4, linestyle="none")


def _dev_type(dev: str, row: Dict) -> Optional[str]:
    if dev == "none":
        return "none"
    if dev in ("revJ_oracle", "E13a_0.00"):
        return "oracle"
    t = (row.get("param") or {}).get("type")
    return t


# ------------------------------------------------------------------ E13
def _level_rows(tables: Dict, keys: Sequence[str]) -> List[Dict]:
    out = []
    for key in keys:
        t = tables.get(key) or []
        for row in t[1:]:
            ty = _dev_type(row["device"], row)
            if ty is None:
                continue
            out.append({"set": key, "device": row["device"], "type": ty, "r": row["tip_tremor_mm"]["mean"],
                        "r_lo": row["tip_tremor_mm"]["lo"], "r_hi": row["tip_tremor_mm"]["hi"],
                        "w": row["words_of_10"]["mean"], "w_lo": row["words_of_10"]["lo"], "w_hi": row["words_of_10"]["hi"],
                        "n": row["n_cases"], "param": row.get("param")})
    return out


def fig_e13_curve(out: Dict, d: Path) -> Optional[Path]:
    from . import curve as CV
    e = out.get("e13") or {}
    tun = e.get("tuning") or {}
    if not tun.get("fits"):
        return None
    plt, PS = _plt()
    splits = [("tuning", tun)] + ([("test", e["test"])] if (e.get("test") or {}).get("fits") else [])
    fig, axs = plt.subplots(1, len(splits), figsize=(6.2 * len(splits), 5.6), sharey=True, squeeze=False)
    rows_csv = []
    rr = np.linspace(0.0, 1.95, 160)
    for ax, (name, blk) in zip(axs[0], splits):
        f = blk["fits"]["pooled"]
        p = f["fit"]["p"]
        lvl = _level_rows(blk["tables"], ("all/severe", "all/moderate"))
        pts = {}
        for ty in ("a", "b", "c", "none", "oracle"):
            sel = [x for x in lvl if x["type"] == ty]
            if not sel:
                continue
            lab = {"none": "ordinary pen", "oracle": "perfect knowledge"}.get(ty, TYPE_LABEL.get(ty, ty))
            mk = {"a": "o", "b": "s", "c": "^", "none": "D", "oracle": "*"}[ty]
            for j, x in enumerate(sel):
                ax.errorbar(x["r"], x["w"], yerr=[[x["w"] - x["w_lo"]], [x["w_hi"] - x["w"]]], color=COL[ty],
                            elinewidth=1.0, capsize=0, zorder=2, **_mk(PS, COL[ty], mk, 8 if ty != "oracle" else 11),
                            label=lab if j == 0 else None)
                rows_csv.append([name, x["set"], x["device"], ty, x["r"], x["r_lo"], x["r_hi"], x["w"], x["w_lo"],
                                 x["w_hi"], x["n"]])
        ax.plot(rr, CV.model(rr, p), color=COL["curve"], lw=1.8, zorder=3, label="fitted curve (log-logistic)")
        for r_, w_ in zip(rr[::8], CV.model(rr[::8], p)):
            rows_csv.append([name, "curve", "", "fit", float(r_), "", "", float(w_), "", "", ""])
        w_ord, w_clean = f.get("w_ord_severe"), f.get("w_clean")
        if w_ord is not None and np.isfinite(w_ord):
            ax.axhline(w_ord + 2.0, color=PS.INK2, lw=1.0, ls=(0, (4, 3)), zorder=1)
            ax.text(1.93, w_ord + 2.12, f"ordinary pen + 2 words (DEC-055): {w_ord + 2:.1f}", ha="right", va="bottom",
                    fontsize=7.8, color=PS.INK2)
            ax.annotate("study E's best causal tracker\n(test split: 1.12 mm left)", xy=(1.12, 0.05),
                        xytext=(1.12, w_ord + 3.3), fontsize=7.2, color=PS.INK2, ha="center", va="bottom",
                        arrowprops=dict(arrowstyle="-", color=PS.MUTED, lw=0.8))
        if w_clean is not None and np.isfinite(w_clean):
            ax.axhline(0.8 * w_clean, color=PS.INK2, lw=1.0, ls=(0, (1, 2)), zorder=1)
            ax.text(1.93, 0.8 * w_clean + 0.12, f"80 % of the tremor-free words: {0.8 * w_clean:.1f}", ha="right",
                    va="bottom", fontsize=7.8, color=PS.INK2)
        ci = f.get("ci95") or {}
        for key, lab, ls in (("r_plus2_mm", "+2 words", (0, (4, 3))), ("r_80_mm", "80 %", (0, (1, 2)))):
            v = f.get(key)
            if v is not None and np.isfinite(v):
                c = ci.get(key) or {}
                if np.isfinite(c.get("lo", np.nan)) and np.isfinite(c.get("hi", np.nan)):
                    ax.axvspan(c["lo"], c["hi"], color=PS.GRID, alpha=0.7, zorder=0, lw=0)
                ax.axvline(v, color=PS.INK2, lw=1.0, ls=ls, zorder=1)
                ax.text(v + 0.015, 9.45 if key == "r_plus2_mm" else 8.95, f"{lab}: {v:.2f} mm", fontsize=7.8,
                        color=PS.INK, ha="left")
        ax.set_xlim(0, 1.95)
        ax.set_ylim(0, 10)
        ax.set_xlabel("tremor left at the pen tip, mm (peak, f0 +- 2 Hz; R's measure)")
        n_w = f.get("n_writers")
        ax.set_title(f"{'Tuning split' if name == 'tuning' else 'Test split (confirmation, run once)'}: "
                     f"{n_w} writers, PD and ET, severe and moderate", fontsize=10, loc="left")
    axs[0][0].set_ylabel("words read out of 10 (AI reader, literal)")
    h, lab = axs[0][0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, fontsize=7.8, bbox_to_anchor=(0.5, 0.035))
    fig.suptitle("How much tremor may be left at the tip for words to be readable (EXP-E13)", fontsize=11.5, x=0.01,
                 ha="left")
    PS.stamp(fig, SIM_TAG, "points: mean over writers, 95 % writer-bootstrap interval; grey band: 95 % interval of "
                           "the threshold")
    fig.tight_layout(rect=(0, 0.13, 1, 0.95))
    path = d / "fig_e13_curve.png"
    fig.savefig(path)
    plt.close(fig)
    write_csv(d / "fig_e13_curve.csv", ["split", "set", "device", "type", "tip_tremor_mm", "tip_lo", "tip_hi",
                                        "words_of_10", "words_lo", "words_hi", "n_cases"], rows_csv,
              [SIM_TAG, "one row per residual level (mean over writers, 95 % writer-bootstrap interval) and the fitted "
                        "curve (type 'fit')"])
    return path


def fig_e13_kinds(out: Dict, d: Path) -> Optional[Path]:
    from . import curve as CV
    tun = (out.get("e13") or {}).get("tuning") or {}
    if not tun.get("fits"):
        return None
    plt, PS = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3), sharey=True)
    rows_csv = []
    rr = np.linspace(0.0, 1.95, 160)
    pooled = tun["fits"]["pooled"]["fit"]["p"]
    for ax, kind in zip(axs, ("PD", "ET")):
        f = tun["fits"].get(f"kind_{kind}")
        lvl = _level_rows(tun["tables"], (f"{kind}/severe", f"{kind}/moderate"))
        for ty in ("a", "b", "c", "none", "oracle"):
            sel = [x for x in lvl if x["type"] == ty]
            mk = {"a": "o", "b": "s", "c": "^", "none": "D", "oracle": "*"}[ty]
            for j, x in enumerate(sel):
                ax.plot(x["r"], x["w"], **_mk(PS, COL[ty], mk, 8 if ty != "oracle" else 11),
                        label=({"none": "ordinary pen", "oracle": "perfect knowledge"}.get(ty, TYPE_LABEL.get(ty))
                               if j == 0 else None))
                rows_csv.append([kind, x["set"], x["device"], ty, x["r"], x["w"], x["n"]])
        ax.plot(rr, CV.model(rr, pooled), color=PS.MUTED, lw=1.4, label="pooled curve (PD + ET)")
        if f and np.all(np.isfinite(f["fit"]["p"])):
            ax.plot(rr, CV.model(rr, f["fit"]["p"]), color=COL["curve"], lw=1.8, label="curve for this tremor kind")
            v = f.get("r_plus2_mm")
            if v is not None and np.isfinite(v):
                ax.axvline(v, color=PS.INK2, lw=1.0, ls=(0, (4, 3)))
                ax.text(v + 0.015, 9.2, f"+2 words: {v:.2f} mm", fontsize=7.8, color=PS.INK)
        ax.set_xlim(0, 1.95)
        ax.set_ylim(0, 10)
        ax.set_title({"PD": "Parkinson's tremor (UCI, pen tip)", "ET": "Essential tremor (Zenodo, hand)"}[kind] +
                     ", tuning split", fontsize=10, loc="left")
        ax.set_xlabel("tremor left at the pen tip, mm")
    axs[0].set_ylabel("words read out of 10")
    axs[0].legend(loc="upper right", fontsize=7.4)
    PS.stamp(fig, SIM_TAG, "means over the 5 tuning writers")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path = d / "fig_e13_by_kind.png"
    fig.savefig(path)
    plt.close(fig)
    write_csv(d / "fig_e13_by_kind.csv", ["kind", "set", "device", "type", "tip_tremor_mm", "words_of_10", "n_cases"],
              rows_csv, [SIM_TAG, "tuning split, means over writers"])
    return path


# ------------------------------------------------------------------ E11
def fig_e11(out: Dict, d: Path) -> Optional[Path]:
    t = ((out.get("e11") or {}).get("test") or {})
    pw = t.get("per_writer")
    if not pw:
        return None
    plt, PS = _plt()
    designs = [k for k in ("D1", "D2", "D3") if any(r.get(f"{k}_frozen_um") is not None for r in pw)]
    fig, axs = plt.subplots(1, len(designs), figsize=(4.4 * len(designs), 4.9), sharey=True, squeeze=False)
    rows_csv = []
    names = [r["writer"].replace(".dat", "").replace("hpb2-", "") for r in pw]
    y = np.arange(len(pw))
    title = {"D1": "ai2's TCN + size gate (E's frozen)", "D2": "TCN trained on real data + size gate",
             "D3": "listening AKF + confidence gate"}
    for ax, k in zip(axs[0], designs):
        fz = np.array([np.nan if r.get(f"{k}_frozen_um") is None else r[f"{k}_frozen_um"] for r in pw], float)
        ca = np.array([np.nan if r.get(f"{k}_cal_um") is None else r[f"{k}_cal_um"] for r in pw], float)
        lo = 0.05
        for j in range(len(pw)):
            ax.plot([max(fz[j], lo), max(ca[j], lo)], [y[j], y[j]], color=PS.GRID, lw=2.0, zorder=1)
        ax.plot(np.maximum(fz, lo), y, **_mk(PS, COL["frozen"], "o", 8), label="gate as frozen by E", zorder=3)
        ax.plot(np.maximum(ca, lo), y, **_mk(PS, COL["cal"], "o", 8), label="gate calibrated on the writer's own "
                                                                          "clean note", zorder=4)
        ax.axvline(50.0, color=PS.INK2, lw=1.0, ls=(0, (4, 3)))
        ax.text(50.0, 1.005, "50 um, any writer (DEC-055)", transform=ax.get_xaxis_transform(), fontsize=7.2,
                color=PS.INK2, ha="center", va="bottom")
        ax.set_xscale("log")
        ax.set_xlim(lo * 0.8, 2000)
        ax.set_title(f"{k}: {title[k]}", fontsize=9.5, loc="left", pad=14)
        ax.set_xlabel("clean writing moved, um (log scale)")
        for j in range(len(pw)):
            rows_csv.append([k, names[j], pw[j]["note"], fz[j], ca[j], pw[j].get(f"{k}_a_lo_mm"),
                             pw[j].get(f"{k}_calib_max_mm")])
    axs[0][0].set_yticks(y)
    axs[0][0].set_yticklabels([f"test note {r['note']} ({n})" for r, n in zip(pw, names)])
    axs[0][0].invert_yaxis()
    h, l = axs[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=7.8, bbox_to_anchor=(0.5, 0.045))
    fig.suptitle("Per-writer gate calibration (EXP-E11): clean writing moved on each held-out writer's note "
                 "(INFORMATION ONLY)", fontsize=10.5, x=0.01, ha="left")
    PS.stamp(fig, "SIMULATION (model HW1) with real recorded inputs", "test split already seen by study E: a "
                  "feasibility check, not a claim; values below 0.05 um are drawn at 0.05 um")
    fig.tight_layout(rect=(0, 0.12, 1, 0.93))
    path = d / "fig_e11_clean.png"
    fig.savefig(path)
    plt.close(fig)
    write_csv(d / "fig_e11_clean.csv", ["design", "writer", "test_note", "clean_um_frozen_gate", "clean_um_calibrated_gate",
                                        "calibrated_a_lo_mm", "calibration_note_A_max_mm"], rows_csv,
              [SIM_TAG, "INFORMATION ONLY: the test split was already seen by study E"])
    return path


# ------------------------------------------------------------------ gap
STEP_LABEL = ["perfect\nknowledge", "prediction\nonly (AR)", "sensing,\ntremor alone", "full: tremor\n+ writing"]


def fig_gap(out: Dict, d: Path) -> Optional[Path]:
    g = out.get("gap") or {}
    split = "test" if g.get("test") else ("tuning" if g.get("tuning") else None)
    if split is None:
        return None
    plt, PS = _plt()
    chains = g[split]["chains"]
    order = [k for k in ("fir_raw", "ai2tcn_gated", "net_gated", "akf_raw") if k in chains]
    fig, axs = plt.subplots(1, 2, figsize=(12.4, 5.2))
    rows_csv = []
    x = np.arange(4)
    wkey = "words_via_test_curve" if split == "test" else "words_via_curve"
    lab = {"fir_raw": "linear IMU filter trained on the tremor alone",
           "ai2tcn_gated": "E's frozen tracker (ai2's TCN + gate)",
           "net_gated": "TCN trained on real data + gate (E, info)",
           "akf_raw": "listening AKF, capture-tuned (E)"}
    for j, k in enumerate(order):
        steps = chains[k]["steps"]
        off = (j - (len(order) - 1) / 2) * 0.12
        r = [s["tip_tremor_mm"]["mean"] if s.get("tip_tremor_mm") else np.nan for s in steps]
        w = [s[wkey]["mean"] if s.get(wkey) else np.nan for s in steps]
        wr = [s["words_read"]["mean"] if s.get("words_read") else np.nan for s in steps]
        mk = {kk: v for kk, v in _mk(PS, COL[k], "o", 8).items() if kk != "linestyle"}
        axs[0].plot(x[:len(r)] + off, r, color=COL[k], lw=1.4, label=lab[k], **mk)
        axs[1].plot(x[:len(w)] + off, w, color=COL[k], lw=1.4, label=lab[k], **mk)
        for xi, v in zip(x[:len(wr)] + off, wr):
            if np.isfinite(v):
                axs[1].plot(xi, v, marker="o", markersize=8, markerfacecolor=PS.SURFACE, markeredgecolor=COL[k],
                            markeredgewidth=1.6, linestyle="none", zorder=5)
        for s_, a, b, c in zip(steps, r, w, wr):
            rows_csv.append([split, k, s_["step"], s_["config"], a, b, c])
    axs[1].plot([], [], marker="o", markersize=8, markerfacecolor=PS.SURFACE, markeredgecolor=PS.INK2,
                markeredgewidth=1.6, linestyle="none", label="read directly by the AI reader")
    e = out.get("e13") or {}
    thr = [("tuning", ((e.get("tuning") or {}).get("fits") or {}).get("pooled") or {}),
           ("test", ((e.get("test") or {}).get("fits") or {}).get("pooled") or {})]
    for nm, fp in thr:
        v = fp.get("r_plus2_mm")
        if v is not None and np.isfinite(v):
            axs[0].axhline(v, color=PS.INK2, lw=1.0, ls=(0, (4, 3)) if nm == "tuning" else (0, (6, 2, 1, 2)))
            axs[0].text(-0.35, v + 0.012, f"+2 words, {nm} ({v:.2f} mm)", fontsize=7.4, color=PS.INK2,
                        va="bottom", ha="left")
    v = (thr[0][1] or {}).get("r_80_mm")
    if v is not None and np.isfinite(v):
        axs[0].axhline(v, color=PS.INK2, lw=1.0, ls=(0, (1, 2)))
        axs[0].text(-0.35, v + 0.012, f"80 % of tremor-free words ({v:.2f} mm)", fontsize=7.4, color=PS.INK2,
                    va="bottom", ha="left")
    cc = (chains.get("fir_raw") or {}).get("clean_change_um")
    if cc and np.isfinite(cc.get("mean", np.nan)):
        axs[1].annotate(f"it also moves clean writing\nabout {cc['mean'] / 1000:.1f} mm: nothing is read",
                        xy=(3 - 0.18, 0.15), xytext=(2.45, 8.3), fontsize=7.4, color=PS.INK2,
                        arrowprops=dict(arrowstyle="-", color=PS.MUTED, lw=0.8))
    for ax in axs:
        ax.set_xticks(x)
        ax.set_xticklabels(STEP_LABEL, fontsize=8.2)
        ax.set_xlim(-0.4, 3.5)
    axs[0].set_ylabel("tremor left at the tip, mm")
    axs[0].set_ylim(0, 2.0)
    axs[1].set_ylabel("words read out of 10")
    axs[1].set_ylim(0, 10)
    axs[0].set_title("Tremor left at the tip (severe class, 1.72 mm)", fontsize=10, loc="left")
    axs[1].set_title("Words: via the " + ("test split's curve" if split == "test" else "tuning curve")
                     + " (filled) and read directly (open)", fontsize=10, loc="left")
    h, l = axs[1].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=7.6, bbox_to_anchor=(0.5, 0.04))
    fig.suptitle(f"Where the gap lies: prediction, sensing or separating tremor from writing ({split} split)",
                 fontsize=11, x=0.01, ha="left")
    PS.stamp(fig, SIM_TAG, "means over writers; each estimate drives the nose on the full case (tremor + writing)")
    fig.tight_layout(rect=(0, 0.13, 1, 0.94))
    path = d / "fig_gap.png"
    fig.savefig(path)
    plt.close(fig)
    write_csv(d / "fig_gap.csv", ["split", "estimator", "step", "config", "tip_tremor_mm",
                                  "words_via_" + ("test_curve" if split == "test" else "tuning_curve"),
                                  "words_read_directly"], rows_csv, [SIM_TAG, "means over writers"])
    return path


def all_figures(out: Dict, d: Path) -> List[Path]:
    made = []
    for fn in (fig_e13_curve, fig_e13_kinds, fig_e11, fig_gap):
        try:
            p = fn(out, d)
            if p:
                made.append(p)
        except Exception as e:                       # a figure never stops the report
            import traceback
            print(f"[figures] {fn.__name__} failed: {e!r}\n{traceback.format_exc()}", flush=True)
    return made
