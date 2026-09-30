"""Figures of study P, each with a CSV twin (results/platen/fig_*.png + .csv).  Static matplotlib; the reference
palette of the data-visualisation guide (categorical slots in fixed order; hairline recessive axes; text in ink
colours, identity carried by the marks and the legend)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
FAMILY = {"nib": SLOT[0], "platen": SLOT[1], "ordinary": SLOT[2]}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": AXIS,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
                         "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                         "axes.axisbelow": True})
    return plt


def _csv(path: Path, header: Sequence[str], rows: List[Sequence]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([("" if v is None else (f"{v:.6g}" if isinstance(v, float) else v)) for v in r])


def _ci(b: Optional[Dict]):
    if not b or b.get("mean") is None or not np.isfinite(b.get("mean", np.nan)):
        return None
    return b["mean"], b["lo"], b["hi"]


def fig_tremor(tr: Dict, f_curve: Dict, out: Path, tag: str = "all/severe") -> Optional[Path]:
    """Tip tremor left and words of 10 per pen (severe class, tuning split)."""
    tab = (tr.get("by_class") or {}).get(tag)
    if not tab:
        return None
    rows = [("none", "Ordinary pen, fixed page (platen off)", "ordinary"),
            ("F10_oracle", "Nib +-1.0 mm, perfect knowledge (F)", "nib"),
            ("F15_oracle", "Nib +-1.5 mm, perfect knowledge (F)", "nib"),
            ("F6_oracle", "Rev J nose +-6 mm, perfect knowledge (F)", "nib"),
            ("N10_E_chosen", "Nib +-1.0 mm, E's frozen design", "nib"),
            ("N15_E_chosen", "Nib +-1.5 mm, E's frozen design", "nib"),
            ("N6_E_chosen", "Rev J nose +-6 mm, E's frozen design", "nib"),
            ("N15_E_net", "Nib +-1.5 mm, E's real-data TCN", "nib"),
            ("P_oracle", "Platen +-5 mm, perfect knowledge", "platen"),
            ("P_cam_sep", "Platen, perfect separation + camera", "platen"),
            ("P_E_chosen", "Platen, E's frozen design", "platen"),
            ("P_E_net", "Platen, E's real-data TCN", "platen")]
    rows = [r for r in rows if r[0] in tab]
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 0.42 * len(rows) + 1.9), sharey=True,
                             gridspec_kw={"wspace": 0.08})
    y = np.arange(len(rows))[::-1]
    csv_rows = []
    for yi, (key, label, fam) in zip(y, rows):
        e = tab[key]
        tt = _ci(e.get("tip_tremor_mm"))
        read = _ci(e.get("words_read"))
        curve = _ci(e.get("words_via_curve"))
        col = FAMILY[fam]
        if tt:
            axes[0].plot([tt[1], tt[2]], [yi, yi], color=col, lw=2, solid_capstyle="round")
            axes[0].plot(tt[0], yi, "o", ms=7, color=col, mec=SURFACE, mew=1.5)
        w = read or curve
        if w:
            axes[1].plot([w[1], w[2]], [yi, yi], color=col, lw=2, solid_capstyle="round")
            axes[1].plot(w[0], yi, "o", ms=7, color=col if read else SURFACE, mec=col if not read else SURFACE,
                         mew=1.8 if not read else 1.5)
        csv_rows.append([key, label, fam, *(tt or (None, None, None)), *(read or (None, None, None)),
                         *(curve or (None, None, None)), e.get("n_cases")])
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([r[1] for r in rows])
    r2, r80 = f_curve["r_plus2_mm"], f_curve["r_80_mm"]
    for x, txt, yy, va in ((r2, f" +2 words (F, tuning) {r2:.2f} mm", y[0] + 0.55, "bottom"),
                           (r80, f" near-normal (F) {r80:.2f} mm", y[-1] - 0.55, "top")):
        axes[0].axvline(x, color=MUTED, lw=1)
        axes[0].text(x, yy, txt, color=INK2, fontsize=7.5, ha="left", va=va)
    axes[0].set_xlabel("Tremor left at the tip, mm (R's measure; writer mean, 95 % interval)")
    axes[0].set_xlim(0, 2.0)
    w_ord = (tab.get("none") or {}).get("words_read") or {}
    if w_ord.get("mean") is not None:
        axes[1].axvline(w_ord["mean"] + 2, color=MUTED, lw=1)
        axes[1].text(w_ord["mean"] + 2, y[0] + 0.55, " ordinary pen + 2 words (DEC-055)", color=INK2, fontsize=7.5,
                     ha="left", va="bottom")
    axes[1].set_xlabel("Words of 10 (filled: read by R's reader; hollow: F's curve)")
    axes[1].set_xlim(0, 10)
    for ax in axes:
        ax.set_ylim(-1.3, len(rows) + 0.2)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=FAMILY[f], marker="o", lw=2, label=l) for f, l in
         (("ordinary", "ordinary pen"), ("nib", "handheld nib (Rev J nose, travel cut)"), ("platen", "platen"))]
    h += [Line2D([], [], color=INK2, marker="o", ls="none", mfc=INK2, label="read"),
          Line2D([], [], color=INK2, marker="o", ls="none", mfc=SURFACE, label="via curve (CALC)")]
    fig.legend(handles=h, loc="lower center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Severe tremor (1.72 mm at the tip), real inputs, tuning split: what reaches the ink "
                 "(SIMULATION, model HW1 + platen stage)", fontsize=10.5, color=INK, x=0.02, ha="left")
    fig.subplots_adjust(left=0.27, right=0.98, top=0.9, bottom=0.2)
    p = out / "fig_tremor.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    _csv(p.with_suffix(".csv"), ["row", "label", "family", "tip_mm", "tip_lo", "tip_hi", "words_read", "read_lo",
                                 "read_hi", "words_curve", "curve_lo", "curve_hi", "n_cases"], csv_rows)
    return p


def fig_reach(tr: Dict, sens: Dict, f_curve: Dict, out: Path) -> Optional[Path]:
    """Tremor left at the tip against usable travel, perfect knowledge: the nib (F) and the platen."""
    tab = (tr.get("by_class") or {}).get("all/severe") or {}
    rows = (sens or {}).get("rows") or {}
    nib = [(1.0, tab.get("F10_oracle")), (1.5, tab.get("F15_oracle")), (2.0, tab.get("F2_oracle")),
           (3.0, tab.get("F3_oracle")), (6.0, tab.get("F6_oracle"))]
    plat = [(3.0, rows.get("travel_3mm|oracle")), (4.0, rows.get("travel_4mm|oracle")),
            (5.0, rows.get("baseline|oracle")), (6.0, rows.get("travel_6mm|oracle"))]
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    csv_rows = []
    for series, pts, col, lab in (("nib", nib, FAMILY["nib"], "handheld nib (Rev J nose, travel cut; study F)"),
                                  ("platen", plat, FAMILY["platen"], "platen (fine stage, travel cut)")):
        xs, ms, lo, hi = [], [], [], []
        for x, e in pts:
            c = _ci((e or {}).get("tip_tremor_mm"))
            if c:
                xs.append(x); ms.append(c[0]); lo.append(c[1]); hi.append(c[2])
                csv_rows.append([series, x, *c])
        if xs:
            ax.plot(xs, ms, "-", color=col, lw=2, label=lab)
            ax.vlines(xs, lo, hi, color=col, lw=2)
            ax.plot(xs, ms, "o", color=col, ms=7, mec=SURFACE, mew=1.5)
    for yv, txt in ((f_curve["r_plus2_mm"], "+2 words (F)"), (f_curve["r_80_mm"], "near-normal (F)")):
        ax.axhline(yv, color=MUTED, lw=1)
        ax.text(7.35, yv + 0.01, txt, color=INK2, fontsize=8, va="bottom", ha="right")
    ax.set_xlabel("Usable travel (radius), mm")
    ax.set_ylabel("Tremor left at the tip, mm (perfect knowledge)")
    ax.set_xlim(0.5, 7.4)
    ax.set_ylim(0, 1.2)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Reach: perfect knowledge of severe real tremor, tuning split (SIMULATION)", fontsize=10, loc="left")
    fig.tight_layout()
    p = out / "fig_reach.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    _csv(p.with_suffix(".csv"), ["series", "travel_mm", "tip_mm", "tip_lo", "tip_hi"], csv_rows)
    return p


def fig_sensing(sens: Dict, f_curve: Dict, out: Path) -> Optional[Path]:
    """Tremor left against the camera's latency and noise (perfect separation) and the fine stage's bandwidth
    (perfect separation with the camera, and perfect knowledge)."""
    rows = (sens or {}).get("rows") or {}
    if not rows:
        return None
    lat = [(2, "latency_2ms"), (4, "latency_4ms"), (6, "baseline"), (10, "latency_10ms"), (15, "latency_15ms"),
           (25, "latency_25ms")]
    noi = [(0, "noise_0um"), (5, "noise_5um"), (15, "baseline"), (30, "noise_30um"), (60, "noise_60um")]
    bwd = [(15, "bandwidth_15Hz"), (25, "bandwidth_25Hz"), (40, "baseline"), (80, "bandwidth_80Hz")]
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.2), sharey=True, gridspec_kw={"wspace": 0.08})
    csv_rows = []
    panels = ((axes[0], lat, "Camera latency, ms (250 Hz, 15 um)", "latency", ("camera",)),
              (axes[1], noi, "Camera noise, um RMS per axis (250 Hz, 6 ms)", "noise", ("camera",)),
              (axes[2], bwd, "Fine-stage bandwidth, Hz (camera 250 Hz, 6 ms, 15 um)", "bandwidth", ("camera", "oracle")))
    for ax, pts, xl, name, drives in panels:
        for drive in drives:
            col = FAMILY["platen"] if drive == "camera" else SLOT[3]
            xs, ms, lo, hi = [], [], [], []
            for x, key in pts:
                c = _ci((rows.get(f"{key}|{drive}") or {}).get("tip_tremor_mm"))
                if c:
                    xs.append(x); ms.append(c[0]); lo.append(c[1]); hi.append(c[2])
                    csv_rows.append([name, drive, x, *c])
            if not xs:
                continue
            lab = "camera + predictor (perfect separation)" if drive == "camera" else "perfect knowledge"
            ax.plot(xs, ms, "-", color=col, lw=2, label=lab if name == "bandwidth" else None)
            ax.vlines(xs, lo, hi, color=col, lw=2)
            ax.plot(xs, ms, "o", color=col, ms=7, mec=SURFACE, mew=1.5)
        if name != "bandwidth":
            orc = _ci((rows.get("baseline|oracle") or {}).get("tip_tremor_mm"))
            if orc:
                ax.axhline(orc[0], color=INK2, lw=1)
                ax.text(0.99, orc[0], "perfect knowledge ", color=INK2, fontsize=7.5, va="bottom", ha="right",
                        transform=ax.get_yaxis_transform())
        for yv, txt in ((f_curve["r_plus2_mm"], " +2 words (F)"), (f_curve["r_80_mm"], " near-normal (F)")):
            ax.axhline(yv, color=MUTED, lw=1)
            ax.text(0.01, yv, txt, color=INK2, fontsize=7.5, va="bottom", ha="left", transform=ax.get_yaxis_transform())
        ax.set_xlabel(xl)
    axes[2].legend(loc="upper right", fontsize=7.5)
    axes[0].set_ylabel("Tremor left at the tip, mm")
    axes[0].set_ylim(0, 1.0)
    fig.suptitle("Sensing and bandwidth: severe real tremor, tuning split (SIMULATION; each predictor refitted for its "
                 "setting)", fontsize=10, x=0.02, ha="left", color=INK)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.86, bottom=0.14)
    p = out / "fig_sensing.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    _csv(p.with_suffix(".csv"), ["sweep", "drive", "x", "tip_mm", "tip_lo", "tip_hi"], csv_rows)
    return p


HAND_ORDER = [("still", "still hand"), ("drift", "drift"), ("mod_PD", "moderate PD"), ("mod_ET", "moderate ET"),
              ("sev_PD", "severe PD"), ("sev_ET", "severe ET")]
CONFIG_ORDER = [("proposed", "platen, proposed (firm grip on the rest, 0.5 N, ink loop)"),
                ("firm_ideal", "platen, hand cancels the drag (HW1 convention)"),
                ("relaxed_ink_loop", "platen, relaxed hand, ink loop"),
                ("relaxed_naive", "platen, relaxed hand, tip following")]


def fig_accepted(acc: Dict, five: Dict, out: Path) -> Optional[Path]:
    summ = (acc or {}).get("summary") or {}
    if not summ:
        return None
    texts = [t for t in ("se", "library") if any(k.startswith(t + "|") for k in summ)]
    plt = _plt()
    fig, axes = plt.subplots(1, len(texts) + 1, figsize=(4.9 * len(texts) + 3.0, 4.3),
                             gridspec_kw={"width_ratios": [3] * len(texts) + [1.25], "wspace": 0.25})
    csv_rows = []
    bw = 0.19
    for ax, text in zip(axes, texts):
        x = np.arange(len(HAND_ORDER))
        for ci, (cfg, lab) in enumerate(CONFIG_ORDER):
            vals = []
            for hk, _ in HAND_ORDER:
                s = summ.get(f"{text}|{cfg}|{hk}")
                vals.append(s["engineering_complete"] if s else np.nan)
                if s:
                    csv_rows.append([text, cfg, hk, s["engineering_complete"], s["n"], s["refused"],
                                     s["median_coverage"], s["median_rms_mm"], s["ink_passes_both"],
                                     s["ink_lp30_passes_both"]])
            xb = x + (ci - 1.5) * (bw + 0.012)
            ax.bar(xb, vals, width=bw, color=SLOT[ci], label=lab if text == texts[0] else None)
            for xi, v in zip(xb, vals):              # a zero is a result: mark it
                if v == 0:
                    ax.text(xi, 0.15, "0", ha="center", va="bottom", fontsize=6.5, color=INK2)
        cr = summ.get(f"{text}|cradle|cradle")
        if cr:
            csv_rows.append([text, "cradle", "cradle", cr["engineering_complete"], cr["n"], cr["refused"],
                             cr["median_coverage"], cr["median_rms_mm"], cr["ink_passes_both"], cr["ink_lp30_passes_both"]])
            ax.text(0.01, 0.98, f"pen in a cradle (still): {cr['engineering_complete']}/{cr['n']}",
                    transform=ax.transAxes, ha="left", va="top", fontsize=8, color=INK2)
        n = max((s["n"] for k, s in summ.items() if k.startswith(text + "|")), default=20)
        ax.set_xticks(x)
        ax.set_xticklabels([h[1] for h in HAND_ORDER], rotation=20, ha="right")
        ax.set_ylim(0, n + 3)
        ax.set_ylabel(f"Words completed (of {n}; the five-bar's criterion)")
        ax.set_title(f"'{text}' {'suffix' if text == 'se' else 'rewrite'}", fontsize=10, loc="left")
    # the five-bar (published, 'se' suffix)
    ax = axes[-1]
    fb = [r for r in ((five or {}).get("summary") or []) if r.get("feedforward")]
    labs, vals = [], []
    for r in fb:
        labs.append("no grip" if r["grip_stiffness_N_m"] == 0 else f"{r['grip_stiffness_N_m']:.0f} N/m grip")
        vals.append(r["engineering_complete"])
        csv_rows.append(["se", "fivebar", labs[-1], r["engineering_complete"], r["words"], r["refused"],
                         r["median_ink_coverage"], r["median_actual_ink_error_mm"], None, None])
    ax.bar(np.arange(len(vals)), vals, width=0.5, color=MUTED)       # the published comparator, in neutral
    for xi, v in enumerate(vals):
        if v == 0:
            ax.text(xi, 0.15, "0", ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xticks(np.arange(len(vals)))
    ax.set_xticklabels(labs, rotation=20, ha="right")
    ax.set_ylim(0, 23)
    ax.set_title("grounded five-bar, 'se'\n(no tremor; published)", fontsize=9.5, loc="left")
    fig.legend(loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.45, -0.01))
    fig.suptitle("Accepted writing by moving the page under a held pen (SIMULATION)", fontsize=10.5, x=0.02,
                 ha="left", color=INK)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.86, bottom=0.34)
    p = out / "fig_accepted.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    _csv(p.with_suffix(".csv"), ["text", "config", "hand", "complete", "n", "refused", "median_coverage",
                                 "median_rms_mm", "ink_acc_jerk_pass", "ink_acc_jerk_pass_lp30"], csv_rows)
    return p


def fig_accepted_example(traces: List[Dict], out: Path) -> Optional[Path]:
    """Ink on the page against the reference, and the page and tip motion, for a few example runs."""
    if not traces:
        return None
    plt = _plt()
    fig, axes = plt.subplots(2, len(traces), figsize=(4.2 * len(traces), 7.0), squeeze=False,
                             gridspec_kw={"height_ratios": [1.2, 1.0], "hspace": 0.5, "wspace": 0.25})
    csv_rows = []
    for j, tr in enumerate(traces):
        ax = axes[0, j]
        t, ink, ref, con, req = tr["t"], tr["ink"] * 1e3, tr["ref"] * 1e3, tr["contact"] > 0.5, tr["req"]
        ax.plot(ref[req, 0], ref[req, 1], ".", ms=1.2, color=MUTED, label="reference (requested ink)")
        ink_c = np.where(con[:, None], ink, np.nan)
        ax.plot(ink_c[:, 0], ink_c[:, 1], "-", lw=1.2, color=SLOT[1], label="ink on the page")
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_title(tr["title"], fontsize=9, loc="left")
        ax.set_xlabel("page x, mm")
        ax.set_ylabel("page y, mm")
        if j == 0:
            ax.legend(fontsize=7.5, loc="upper left")
        bx = axes[1, j]
        page, tip = tr["page"] * 1e3, tr["tip"] * 1e3
        bx.plot(t, page[:, 0], color=SLOT[0], lw=1.2, label="page x")
        bx.plot(t, tip[:, 0], color=SLOT[2], lw=1.2, label="pen tip x (desk)")
        bx.set_xlabel("time, s")
        bx.set_ylabel("mm")
        if j == 0:
            bx.legend(fontsize=7.5, loc="upper right")
        k = np.arange(0, len(t), 20)
        for i in k:
            csv_rows.append([tr["title"].replace("\n", " "), t[i], ink[i, 0], ink[i, 1], ref[i, 0], ref[i, 1],
                             int(con[i]), int(req[i]),
                             page[i, 0], page[i, 1], tip[i, 0], tip[i, 1]])
    fig.suptitle("Accepted 'se' written by the platen: example runs (SIMULATION)", fontsize=10.5, x=0.02, ha="left",
                 color=INK)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.08)
    p = out / "fig_accepted_example.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    _csv(p.with_suffix(".csv"), ["run", "t_s", "ink_x_mm", "ink_y_mm", "ref_x_mm", "ref_y_mm", "contact", "requested",
                                 "page_x_mm", "page_y_mm", "tip_x_mm", "tip_y_mm"], csv_rows)
    return p
