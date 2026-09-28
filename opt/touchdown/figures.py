"""Figures of the touchdown study (results/opt/fig_td_*.png), drawn from the stage caches in results/opt/logs/.
Every figure is stamped with its evidence status (SIMULATION / CALCULATION)."""
from __future__ import annotations

import json
import math
import os

import numpy as np

from stabpen import plotstyle as PS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "opt")
LOGS = os.path.join(OUT, "logs")
# colour follows the configuration in every figure (fixed categorical order)
CFG_ORDER = ["tilt_range_stop", "adaptive_0.30mm", "adaptive_ff", "adaptive_ff_tuned_servo", "adaptive_ff_fast_axial_sensor"]
CFG_LABEL = {"tilt_range_stop": "Tilt-range stop", "adaptive_0.30mm": "Adaptive stop 0.30 mm",
             "adaptive_ff": "Adaptive stop + feed-forward", "adaptive_ff_tuned_servo": "+ tuned servo",
             "adaptive_ff_fast_axial_sensor": "+ 10 kHz slide sensor"}


def _load(stage):
    p = os.path.join(LOGS, f"td_{stage}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _color(key):
    if key in CFG_ORDER:
        return PS.SERIES[CFG_ORDER.index(key)]
    return PS.MUTED


def _cfgs(val):
    """The configurations drawn (fixed order); others in the cache (the adaptive stop alone at the picked margin,
    within 0.02 mm of 0.30 mm) stay in the JSON only."""
    return [k for k in CFG_ORDER if k in val["summary"]]


def _fmt(v):
    return f"{v:.2f}" if v >= 0.1 else f"{v:.3f}"


def fig_tails(val):
    import matplotlib.pyplot as plt
    keys = _cfgs(val)
    th = "50"
    S = val["summary"]
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 3.9))
    x = np.arange(len(keys))
    lab = [CFG_LABEL.get(k, k.replace("_", " ")) for k in keys]
    col = [_color(k) for k in keys]
    tail = [S[k][th]["extra_tr_mm"] for k in keys]
    inst = [S[k][th]["extra_in_mm"] for k in keys]
    miss = [S[k][th]["missing_mm"] for k in keys]
    axs[0].bar(x, tail, color=col, width=0.7, edgecolor=PS.SURFACE, linewidth=2)
    axs[0].axhline(0.1, color=PS.INK2, lw=1.0)
    axs[0].text(1.45, 0.1, "REQ-PNC-006: 0.1 mm", ha="left", va="bottom", fontsize=7.5, color=PS.INK2)
    axs[0].set_title("Extra ink at touchdown and lift", loc="left", fontsize=9.5)
    axs[0].set_ylabel("mm per stroke (rigid pen-down)")
    axs[1].bar(x, inst, color=col, width=0.7, edgecolor=PS.SURFACE, linewidth=2)
    axs[1].set_title("Extra ink within strokes (skid device distortion)", loc="left", fontsize=9.5)
    axs[1].set_ylabel("mm per stroke")
    axs[2].bar(x, miss, color=col, width=0.7, edgecolor=PS.SURFACE, linewidth=2)
    axs[2].set_title("Missing ink", loc="left", fontsize=9.5)
    axs[2].set_ylabel("mm per stroke")
    for ax, vals in zip(axs, (tail, inst, miss)):
        ax.set_xticks(x)
        ax.set_xticklabels(lab, rotation=28, ha="right", fontsize=7.5)
        for xi, v in zip(x, vals):
            ax.text(xi, v, _fmt(v), ha="center", va="bottom", fontsize=7, color=PS.INK2)
    fig.suptitle("Touchdown and lift tails against a rigid pen, test seeds 200-203, 50 deg, no tremor (0.2 mm tolerance)",
                 x=0.01, ha="left", fontsize=9.5)
    PS.stamp(fig, "simulation", "pencil model P1, synthetic handwriting; not measured")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(os.path.join(OUT, "fig_td_tails.png"))
    plt.close(fig)


def fig_pareto(bo_res, base):
    import matplotlib.pyplot as plt
    rows = bo_res["all"]
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    m = np.array([r["x"]["margin"] * 1e3 for r in rows])
    fx = np.array([r["res"]["oracle_ratio"] for r in rows])
    fy = np.array([max(r["res"]["extra_tr_mm"], 1e-3) for r in rows])
    bins = [0.1, 0.175, 0.25, 0.325, 0.401]
    ramp = [PS.SEQ_BLUE[1], PS.SEQ_BLUE[3], PS.SEQ_BLUE[4], PS.SEQ_BLUE[6]]
    for i in range(4):
        sel = (m >= bins[i]) & (m < bins[i + 1])
        ax.plot(fx[sel], fy[sel], color=ramp[i], label=f"feed-forward, margin {bins[i]:.2f}-{bins[i + 1]:.2f} mm", **PS.marker_kw(ramp[i]))
    from .bo import pareto_mask
    keep = pareto_mask(np.column_stack([fx, fy]))
    order = np.argsort(fx[keep])
    ax.step(fx[keep][order], fy[keep][order], where="post", color=PS.INK2, lw=1.2, label="Pareto front: tail ink vs ratio")
    for name, b in base.items():
        a = b["agg"]
        ax.plot([a["oracle_ratio"]], [max(a["extra_tr_mm"], 1e-3)], marker="s", markersize=8, color=PS.SERIES[1],
                markeredgecolor=PS.SURFACE, markeredgewidth=1.6, linestyle="none")
        ax.annotate(name.replace("adaptive_", "stop ").replace("tilt_range_stop", "tilt-range stop").replace("mm", " mm"),
                    (a["oracle_ratio"], max(a["extra_tr_mm"], 1e-3)), textcoords="offset points", xytext=(6, 4), fontsize=7.5, color=PS.INK2)
    fin = bo_res["final"]
    ax.plot([fin["agg"]["oracle_ratio"]], [max(fin["agg"]["extra_tr_mm"], 1e-3)], marker="*", markersize=15, color=PS.SERIES[2],
            markeredgecolor=PS.SURFACE, linestyle="none", label="pick, re-scored on held-out seeds 310-319")
    ax.plot([], [], marker="s", color=PS.SERIES[1], linestyle="none", label="front stop alone (no feed-forward)")
    ax.set_yscale("log")
    ax.set_xlabel("Correction ratio, perfect intent, 6 Hz / 0.3 mm (lower is better)")
    ax.set_ylabel("Extra ink at touchdown and lift (mm per stroke)")
    ax.set_title("Feed-forward and stop margin: tails against correction (search seeds 300-309, 50 deg)", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.2, loc="upper right")
    PS.stamp(fig, "simulation", "pencil model P1; Bayesian optimisation (ParEGO); not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_td_pareto.png"))
    plt.close(fig)


def fig_event(ev):
    """Touchdown and lift of seed 200 at 2 kHz (td_viz_event.json): ink point against its working position under the
    housing (in contact only), stage deflection and refill slide, for the three front-stop / feed-forward cases."""
    import matplotlib.pyplot as plt
    keymap = {"tilt_range_stop": "tilt_range_stop", "adaptive_stop": "adaptive_0.30mm", "adaptive_ff": "adaptive_ff"}
    fig, axs = plt.subplots(3, 2, figsize=(10.4, 7.0), sharex="col")
    for j, name in enumerate(("touchdown", "lift")):
        e = ev["events"][name]
        for key, c in e.items():
            if key == "t0":
                continue
            col = _color(keymap[key])
            t = np.array(c["t_ms"])
            con = np.array(c["contact"]) > 0
            axs[0, j].plot(t, np.where(con, c["ink_minus_working_um"], np.nan), color=col, lw=1.6, label=CFG_LABEL[keymap[key]])
            axs[1, j].plot(t, c["q1_um"], color=col, lw=1.6)
            axs[2, j].plot(t, c["slide_um"], color=col, lw=1.6)
            t_r = c["t_rigid_event_ms"]
        for i in range(3):
            axs[i, j].axvline(t_r, color=PS.MUTED, lw=1.0)
        axs[0, j].text(t_r, axs[0, j].get_ylim()[1], " rigid pen " + ("lands" if name == "touchdown" else "lifts"),
                       fontsize=7.5, color=PS.INK2, va="top")
        axs[0, j].set_title(f"{name.capitalize()} (seed 200, 50 deg, no tremor)", loc="left", fontsize=9.5)
        axs[2, j].set_xlabel("Time (ms)")
    axs[0, 0].set_ylabel("Ink minus working point\nalong azimuth, in contact (um)")
    axs[1, 0].set_ylabel("Stage q1 (um)")
    axs[2, 0].set_ylabel("Refill slide s (um)")
    axs[0, 0].legend(fontsize=7.2, loc="lower right")
    PS.stamp(fig, "simulation", "pencil model P1, 2 kHz record; not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_td_event.png"))
    plt.close(fig)


def fig_adjoint(adj):
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(11.2, 3.6))
    tr = adj["traces_ideal"]["vx0"]
    t = np.array(tr["t"]) * 1e3
    for ax, name, lab in ((axs[0], "slide_um", "Refill slide s (um)"), (axs[1], "stage_q1_um", "Stage q1 (um)")):
        ax.plot(t, tr["p1"][name], color=PS.SERIES[0], lw=1.8, label="P1")
        ax.plot(t, tr["reduced"][name], color=PS.SERIES[1], lw=1.4, label="reduced torch model")
        ax.set_ylabel(lab)
        ax.set_xlabel("Time (ms)")
        ax.legend(fontsize=7.5)
    axs[0].set_title("Down-up event, ideal law: P1 against the reduced model", loc="left", fontsize=9.5)
    st = adj["study"]
    names = [n for n, v in st.items() if isinstance(v, dict) and "history" in v][:6]
    for i, n in enumerate(names):
        h = st[n]["history"]
        axs[2].plot([r["iter"] for r in h], [r["loss_um"] for r in h], color=PS.SERIES[i], lw=1.8, label=n.replace("_", " "))
    axs[2].axhline(st["no_feedforward"]["mean_rms_ink_um"], color=PS.MUTED, lw=1.0)
    axs[2].text(0, st["no_feedforward"]["mean_rms_ink_um"], "no feed-forward", fontsize=7.5, color=PS.INK2, va="bottom")
    axs[2].set_xlabel("Adam iteration (adjoint gradient)")
    axs[2].set_ylabel("RMS ink deviation in contact (um)")
    axs[2].set_title("Law structure: adjoint fits", loc="left", fontsize=9.5)
    axs[2].legend(fontsize=7.2)
    PS.stamp(fig, "simulation", "reduced model (torch) and P1; not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_td_adjoint.png"))
    plt.close(fig)


def fig_servo(sv):
    import matplotlib.pyplot as plt
    keys = [k for k in ("hall_1.0um", "hall_0.3um") if k in sv]
    fig, axs = plt.subplots(1, len(keys), figsize=(5.2 * len(keys), 4.0), squeeze=False)
    for ax, k in zip(axs[0], keys):
        d = sv[k]
        feas = [r for r in d["all"] if r["res"].get("feasible")]
        pmin = d.get("robust_rule_pm_min_deg_at_stiffness_pm20pct")
        rob = [r for r in feas if pmin is None or r["res"].get("pm_tol20", -1e9) >= pmin - 1e-9]
        nom = [r for r in feas if r not in rob]
        ax.plot([r["res"]["P_rail_classB_mW"] for r in rob], [r["res"]["track_um"] for r in rob], color=PS.SEQ_BLUE[4],
                label="explored, margins met also at stiffness +-20 %", **PS.marker_kw(PS.SEQ_BLUE[4]))
        if nom:
            ax.plot([r["res"]["P_rail_classB_mW"] for r in nom], [r["res"]["track_um"] for r in nom], color=PS.SEQ_BLUE[1],
                    label="explored, margins met at nominal stiffness only", **PS.marker_kw(PS.SEQ_BLUE[1]))
        fr = sorted(d["front"], key=lambda r: r["res"]["P_rail_classB_mW"])
        ax.plot([r["res"]["P_rail_classB_mW"] for r in fr], [r["res"]["track_um"] for r in fr], color=PS.INK2, lw=1.2, label="Pareto front")
        for name, mk, col in (("default", "s", PS.SERIES[1]), ("best_tracking_at_default_power", "*", PS.SERIES[2]),
                              ("lowest_power_at_default_tracking", "D", PS.SERIES[3])):
            r = d[name]["res"]
            ax.plot([r["P_rail_classB_mW"]], [r["track_um"]], marker=mk, markersize=15 if mk == "*" else 8, color=col,
                    markeredgecolor=PS.SURFACE, markeredgewidth=1.4, linestyle="none", label=name.replace("_", " "))
        nr = d.get("nominal_rule_only", {}).get("best_tracking_at_default_power")
        if nr and nr["x"] != d["best_tracking_at_default_power"]["x"]:
            r = nr["res"]
            ax.plot([r["P_rail_classB_mW"]], [r["track_um"]], marker="*", markersize=15, color="none", markeredgecolor=PS.SERIES[2],
                    markeredgewidth=1.2, linestyle="none", label="best tracking, nominal rule only (less robust)")
        ax.set_xlabel("Rail power, class-B driver, oracle 6 Hz / 0.3 mm (mW)")
        ax.set_ylabel("Stage tracking error in contact (um RMS)")
        ax.set_title(f"Hall noise {k.split('_')[1].replace('um', ' um')}", loc="left", fontsize=9.5)
        ax.legend(fontsize=7.2)
    fig.suptitle("Inner piezo servo: tracking against rail power (training seeds 300-305)\n"
                 "Margin rule: PM >= 45 deg, GM >= 10 dB, |S| <= 2 at nominal stiffness; the picks also keep PM >= 44 deg at "
                 "stiffness +-20 % (the default's own worst case)", x=0.01, ha="left", fontsize=9.0)
    PS.stamp(fig, "simulation", "pencil model P1; loop margins by calculation; not measured")
    fig.tight_layout(rect=(0, 0.02, 1, 0.92))
    fig.savefig(os.path.join(OUT, "fig_td_servo.png"))
    plt.close(fig)


def fig_tilt(val):
    import matplotlib.pyplot as plt
    keys = _cfgs(val)
    S = val["summary"]
    ths = sorted(float(t) for t in val["thetas"])
    floor = 1e-3
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 4.0))
    mk = lambda col: {kk: vv for kk, vv in PS.marker_kw(col).items() if kk != "linestyle"}   # noqa: E731
    for k in keys:
        col = _color(k)
        y1 = [max(S[k][f"{t:g}"]["extra_tr_mm"], floor) for t in ths]
        y2 = [S[k][f"{t:g}"]["oracle_ratio"] for t in ths]
        axs[0].plot(ths, y1, color=col, lw=1.8, label=CFG_LABEL.get(k, k), **mk(col))
        axs[1].plot(ths, y2, color=col, lw=1.8, **mk(col))
    axs[0].axhline(0.1, color=PS.INK2, lw=1.0)
    axs[0].text(58.0, 0.1, "REQ-PNC-006", fontsize=7.2, color=PS.INK2, va="bottom")
    axs[0].set_yscale("log")
    axs[0].set_ylim(floor * 0.7, 1.5)
    axs[0].text(ths[0], floor * 1.08, "0 drawn at 0.001", fontsize=7.2, color=PS.INK2, ha="left", va="bottom")
    axs[0].set_xlabel("Tilt (deg)"); axs[0].set_ylabel("Tail ink (mm per stroke)")
    axs[0].set_title("Tails against tilt (test seeds)", loc="left", fontsize=9.5)
    axs[1].set_xlabel("Tilt (deg)"); axs[1].set_ylabel("Correction ratio, oracle 6 Hz / 0.3 mm")
    axs[1].set_title("Correction against tilt (lower is better)", loc="left", fontsize=9.5)
    lag = val.get("tilt_lag_proxy", {})
    if lag:
        dth = sorted(lag, key=lambda s: float(s.replace("deg", "")))
        for name, key in (("adaptive_alone", "adaptive_0.30mm"), ("adaptive_ff", "adaptive_ff")):
            col = _color(key)
            xs = [float(d.replace("deg", "")) for d in dth]
            ys = [lag[d][name]["agg"]["extra_tr_mm"] for d in dth]
            axs[2].plot(xs, ys, color=col, lw=1.8, **mk(col))
        for d in dth:
            x = float(d.replace("deg", ""))
            y = lag[d]["adaptive_alone"]["agg"]["extra_tr_mm"]
            axs[2].annotate(f"stop {lag[d]['adaptive_alone']['effective_margin_mm']:.2f} mm", (x, y), textcoords="offset points",
                            xytext=(7, 4), fontsize=7, color=PS.INK2, ha="left", va="bottom")
        axs[2].set_ylim(0, 0.24)
        axs[2].set_xlim(-6, 7.5)
        axs[2].set_xlabel("Stop set for tilt + error (deg), pen at 50 deg"); axs[2].set_ylabel("Tail ink (mm per stroke)")
        axs[2].set_title("Stop lagging a tilt change (picked margin)", loc="left", fontsize=9.5)
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=len(lab), fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, 0.035))
    PS.stamp(fig, "simulation", "pencil model P1, tilt constant within each run; not measured")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_td_tilt.png"))
    plt.close(fig)


def make_all():
    PS.apply()
    val, bo_res, base, adj, sv = _load("validate"), _load("bo"), _load("baseline"), _load("adjoint"), _load("servo")
    made = []
    if val:
        fig_tails(val); fig_tilt(val); made += ["fig_td_tails.png", "fig_td_tilt.png"]
    if bo_res and base:
        fig_pareto(bo_res, base); made.append("fig_td_pareto.png")
    ev = _load("viz_event")
    if ev:
        fig_event(ev); made.append("fig_td_event.png")
    if adj:
        fig_adjoint(adj); made.append("fig_td_adjoint.png")
    if sv:
        fig_servo(sv); made.append("fig_td_servo.png")
    print("figures", made)
    return made
