"""Figures of the hardware study (results/opt/fig_hw_*.png).

Style: stabpen/plotstyle.py (validated categorical order, one y-axis per panel, legends for >= 2 series, text in
ink colours, evidence-status stamp).  Fixed colour per design in every figure: P0.1.2 current = SERIES[1],
P0.2 recommended = SERIES[0], alternatives a, b, c = SERIES[2], SERIES[3], SERIES[4], static-stroke optimum
P0.2s = SERIES[6].  The data behind every figure
are in results/opt/hardware.json.
"""
from __future__ import annotations

import math
import os

import numpy as np

from . import OUT
from stabpen import plotstyle  # noqa: E402

S = plotstyle.SERIES
COL = {"Q26": S[1], "P02": S[0], "P02a": S[2], "P02b": S[3], "P02c": S[4], "P02s": S[6]}
LAB = {"Q26": "P0.1.2 current", "P02": "P0.2 recommended", "P02a": "alt. a", "P02b": "alt. b", "P02c": "alt. c",
       "P02s": "P0.2s static optimum"}


def _save(fig, name):
    fig.savefig(os.path.join(OUT, name))
    import matplotlib.pyplot as plt
    plt.close(fig)


def _nondominated(U, P, M):
    nd = np.ones(len(U), bool)
    for i in range(len(U)):
        for j in range(len(U)):
            if j != i and U[j] >= U[i] - 1e-9 and P[j] <= P[i] + 1e-9 and M[j] <= M[i] + 1e-9 and \
                    (U[j] > U[i] + 1e-6 or P[j] < P[i] - 1e-6 or M[j] < M[i] - 1e-6):
                nd[i] = False
                break
    return nd


def fig_pareto(res):
    """Worst-case stroke against mean assist power and against mass (epsilon-constraint points): the recommended
    design's combination and, where computed, the static-stroke optimum's."""
    import matplotlib.pyplot as plt
    sets = [("P02", [p for p in res["pareto"]["points"] if p.get("feasible")])]
    so = res.get("static_optimum_studies", {}).get("pareto")
    if so:
        sets.append(("P02s", [p for p in so["points"] if p.get("feasible")]))
    if not sets[0][1]:
        return
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
    for key, pts in sets:
        if not pts:
            continue
        P = np.array([p["P_total_mean_mW"] for p in pts])
        M = np.array([p["mass_with_margin_g"] for p in pts])
        U = np.array([p["usable_wc_um"] for p in pts])
        nd = _nondominated(U, P, M)
        for ax, xv in ((axs[0], P), (axs[1], M)):
            ax.scatter(xv[~nd], U[~nd], s=34, facecolors="none", edgecolors=COL[key], linewidths=1.2)
            ax.scatter(xv[nd], U[nd], s=46, color=COL[key], edgecolors=plotstyle.SURFACE, linewidths=1.2,
                       label=f"{LAB[key]}: non-dominated")
    rec = res["recommended"]
    cur = res["model_checks"]["current_design"]
    for ax, xv in ((axs[0], rec["P_total_mean_mW"]), (axs[1], rec["mass_with_margin_g"])):
        ax.scatter([xv], [rec["usable_wc_um"]], s=160, facecolors="none", edgecolors=plotstyle.INK, linewidths=1.2)
        ax.annotate("P0.2", (xv, rec["usable_wc_um"]), xytext=(7, -12), textcoords="offset points", fontsize=8,
                    color=plotstyle.INK2)
    axs[0].set_xlabel("Mean assist battery power, 0.3 mm tremor 4-12 Hz (mW)", fontsize=8.5)
    axs[1].set_xlabel("Pen mass incl. 10 % wiring and adhesives (g)", fontsize=8.5)
    axs[0].set_ylabel("Worst-case usable stroke at the nib (um)")
    axs[0].legend(fontsize=7.2, loc="lower right")
    axs[0].set_title(f"Stroke vs power (P0.1.2: worst case {max(cur['usable_wc_um'], 0):.0f} um at "
                     f"{cur.get('P_total_mean_mW', float('nan')):.0f} mW)", loc="left", fontsize=9)
    axs[1].set_title("Stroke vs mass (open markers: dominated)", loc="left", fontsize=9)
    fig.suptitle("Pareto points (epsilon constraints on power and mass): -20 % parts, 35 deg, mu 0.15, F_c 0.15 N",
                 x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "calculation", "differentiable design model; drop and power surrogates; not measured")
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    _save(fig, "fig_hw_pareto.png")


def fig_topologies(res):
    import matplotlib.pyplot as plt
    rows = list(res["enumeration"])
    if not rows:
        return
    rows = sorted(rows, key=lambda r: (r.get("feasible", False), r["usable_wc_um"] if r.get("feasible") else 0.0))
    labels = [r["key"].replace("-recovery_lt8365-drv5055a4_x2", "").replace("-ic", " (inactive clamp)") for r in rows]
    fam = [r["options"]["topology"] for r in rows]
    colors = {"Q": S[0], "L": S[2], "Q2L": S[3]}
    fig, ax = plt.subplots(figsize=(7.6, max(3.2, 0.2 * len(rows) + 1.2)))
    y = np.arange(len(rows))
    ax.barh(y, [max(r["usable_wc_um"], 0.0) if r.get("feasible") else 0.0 for r in rows], color=[colors[f] for f in fam],
            height=0.72, edgecolor=plotstyle.SURFACE)
    for yi, r in zip(y, rows):
        if not r.get("feasible"):
            ax.text(3, yi, "infeasible: cannot hold the worst-case load", va="center", fontsize=6.5, color=plotstyle.INK2)
        elif r["usable_wc_um"] < 1.0:
            ax.text(3, yi, "0", va="center", fontsize=6.5, color=plotstyle.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.axvline(300, color=plotstyle.MUTED, lw=1.0)
    ax.text(302, len(rows) - 0.5, "REQ-PNC-003 +/-300 um", fontsize=7, color=plotstyle.INK2, va="top")
    tube = res["other_topologies"]["tube"]["with_lever_1.34_um"]
    ax.set_xlabel("Best worst-case usable stroke at the nib (um); P0.1.2 current: 0 um")
    handles = [plt.matplotlib.patches.Patch(color=colors[k], label=v) for k, v in
               (("Q", "Q: push-pull pair per axis"), ("L", "L: one plate per axis"), ("Q2L", "Q + flexure lever"))]
    ax.legend(handles=handles, fontsize=7, loc="lower right")
    ax.set_title(f"Enumeration of discrete choices (piezo tube: {tube:.0f} um; front pivot: does not fit)",
                 loc="left", fontsize=9)
    plotstyle.stamp(fig, "calculation", "each bar = multi-start gradient optimum; not measured")
    fig.tight_layout()
    _save(fig, "fig_hw_topologies.png")


def fig_sensitivity(res):
    import matplotlib.pyplot as plt
    sens = res["sensitivities"]["recommended"]["q_wc"]["grad"]
    names = [k for k in sens if k not in ("n2",)]
    el = np.array([sens[k]["elasticity"] for k in names])
    order = np.argsort(np.abs(el))
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.9), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axs[0]
    y = np.arange(len(names))
    ax.barh(y, el[order], color=[S[0] if v >= 0 else S[1] for v in el[order]], height=0.7, edgecolor=plotstyle.SURFACE)
    ax.set_yticks(y)
    ax.set_yticklabels([names[i] for i in order], fontsize=7.5)
    ax.axvline(0, color=plotstyle.BASELINE, lw=1.0)
    ax.set_xlabel("Elasticity of the worst-case stroke (x/q dq/dx)")
    ax.set_title("Adjoint gradients at P0.2 (blue +, orange -)", loc="left", fontsize=9)
    act = [a for a in res["recommended"].get("active", []) if a["multiplier"] > 1e-4
           and not a["constraint"].startswith("epi_")][:10]
    ax = axs[1]
    if act:
        y2 = np.arange(len(act))[::-1]
        ax.barh(y2, [a["multiplier"] for a in act], color=S[2], height=0.7, edgecolor=plotstyle.SURFACE)
        ax.set_yticks(y2)
        ax.set_yticklabels([a["constraint"] for a in act], fontsize=7.5)
    ax.set_xlabel("um of worst-case stroke per 1 % relaxation")
    ax.set_title("Active constraints: shadow prices (Lagrange multipliers)", loc="left", fontsize=9)
    plotstyle.stamp(fig, "calculation", "reverse-mode autodiff of the design model; not measured")
    fig.tight_layout()
    _save(fig, "fig_hw_sensitivity.png")


def fig_fc_sweep(res):
    import matplotlib.pyplot as plt
    sets = [("P02", res["fc_sweep"], "-")]
    so = res.get("static_optimum_studies", {}).get("fc_sweep")
    if so:
        sets.append(("P02s", so["rows"], "--"))
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for key, rows, ls in sets:
        for i, mu in enumerate((0.15, 0.35)):
            rr = sorted([r for r in rows if abs(r["mu_wc"] - mu) < 1e-9], key=lambda r: r["Fc"])
            c = S[0] if i == 0 else S[2]
            ax.plot([r["Fc"] for r in rr], [max(r["usable_wc_um"], 0) if r.get("feasible") else 0.0 for r in rr],
                    color=c, label=f"{LAB[key]}, nib mu {mu:.2f}", **plotstyle.marker_kw(c) | {"linestyle": ls})
    ax.axhline(300, color=plotstyle.MUTED, lw=1.0)
    ax.text(0.30, 306, "REQ-PNC-003 +/-300 um", ha="right", fontsize=7.5, color=plotstyle.INK2)
    ax.set_xlabel("Nib spring force F_c (N): ASSUMPTION range, EXP-Q02 decides")
    ax.set_ylabel("Worst-case usable stroke at the nib (um)")
    ax.set_title("Re-optimised for each F_c: -20 % parts, 35 deg, worst direction (0 = cannot hold)", loc="left", fontsize=9)
    ax.legend(fontsize=7)
    plotstyle.stamp(fig, "calculation", "one optimum per point; not measured")
    fig.tight_layout()
    _save(fig, "fig_hw_fc_sweep.png")


def fig_stop_sweep(res):
    """Robustness vs authority: worst-case usable stroke against the nominal soft limit, and the firmware stop clamp."""
    import matplotlib.pyplot as plt
    rows = [r for r in res.get("stop_sweep", []) if r.get("feasible")]
    fw = [r for r in res.get("firmware_stop_clamp", []) if r.get("feasible")]
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.5))
    src = res.get("robustness_studies_design", {}).get("stop_sweep", "P02")
    sets = [(src, rows, "-")]
    so = res.get("static_optimum_studies", {}).get("stop_sweep")
    if so and src != "P02s":
        sets.append(("P02s", [r for r in so["rows"] if r.get("feasible")], "--"))
    for key, rr, ls in sets:
        rr = sorted(rr, key=lambda r: r["q_lim_min_um"])
        ql = [r["q_lim_um"] for r in rr]
        axs[0].plot(ql, [max(r["usable_wc_um"], 0) for r in rr], color=S[0], label=f"worst case, {LAB[key]}",
                    **plotstyle.marker_kw(S[0]) | {"linestyle": ls})
        axs[0].plot(ql, [r["q_nom_um"] for r in rr], color=S[2], label=f"nominal (50 deg), {LAB[key]}",
                    **plotstyle.marker_kw(S[2]) | {"linestyle": ls})
    ql = sorted(r["q_lim_um"] for r in rows)
    axs[0].plot(ql, ql, color=plotstyle.MUTED, lw=1.0, ls=":", label="soft limit")
    axs[0].set_xlabel("Nominal soft limit = stop travel - 0.10 mm (um)")
    axs[0].set_ylabel("Stroke at the nib (um)")
    axs[0].set_title("More travel in typical writing costs worst-case stroke", loc="left", fontsize=9)
    axs[0].legend(fontsize=6.5)
    if fw:
        fw = sorted(fw, key=lambda r: -r["stop_drive_frac"])
        axs[1].plot([r["stop_drive_frac"] for r in fw], [r["usable_wc_um"] for r in fw], color=S[0],
                    **plotstyle.marker_kw(S[0]) | {"linestyle": "-"})
        axs[1].invert_xaxis()
        src_fw = res.get("robustness_studies_design", {}).get("firmware_clamp", "P02")
        axs[1].set_xlabel("Drive while pinned at a stop (1 = no firmware clamp)")
        axs[1].set_ylabel("Worst-case usable stroke (um)")
        axs[1].set_title(f"Firmware stop clamp ({LAB[src_fw]})", loc="left", fontsize=9)
    plotstyle.stamp(fig, "calculation", "each point re-optimised; not measured")
    fig.tight_layout()
    _save(fig, "fig_hw_stop_sweep.png")


def fig_validation(p1, keys=None):
    import matplotlib.pyplot as plt
    if not p1:
        return
    keys = [k for k in (keys or ("Q26", "P02", "P02a", "P02b", "P02c", "P02s")) if k in p1]
    fig, axs = plt.subplots(2, 3, figsize=(10.0, 5.8), sharex=True)
    for j, amp in enumerate((0.1, 0.3, 0.5)):
        for key in keys:
            g = p1[key]["grid"]["oracle"]
            cases = [c for c in g["ratio"] if abs(float(c.split("_")[1][:-2]) - amp) < 1e-9]
            f = [float(c.split("Hz")[0]) for c in cases]
            o = np.argsort(f)
            f = np.array(f)[o]
            r = np.array([g["ratio"][c]["mean"] for c in cases])[o]
            t = np.array([g["q_sat_frac"][c]["mean"] for c in cases])[o]
            kw = plotstyle.marker_kw(COL[key]) | {"linestyle": "-"}
            axs[0, j].plot(f, r, color=COL[key], label=LAB[key], **kw)
            axs[1, j].plot(f, t, color=COL[key], label=LAB[key], **kw)
        axs[0, j].set_title(f"tremor {amp:.1f} mm peak", loc="left", fontsize=9)
        axs[1, j].set_xlabel("Tremor frequency (Hz)")
        axs[0, j].set_ylim(0, None)
        axs[1, j].set_ylim(0, 1)
    axs[0, 0].set_ylabel("Oracle ink error / neutral")
    axs[1, 0].set_ylabel("Fraction of time at the travel limit")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower left", bbox_to_anchor=(0.01, 0.0), ncol=3, fontsize=7.5, frameon=False)
    fig.suptitle("Pencil model P1, harness grid (seeds 200-203, 50 deg, F_c 0.15 N): oracle bound and travel limit",
                 x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "simulation", "model P1, synthetic handwriting and tremor; not measured")
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    _save(fig, "fig_hw_validation.png")
    # worst-case condition and rail power
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.4))
    for key in keys:
        w = p1[key]["worst_case_35deg_minus20pct"]["oracle"]
        cases = sorted(w["ratio"], key=lambda c: float(c.split("Hz")[0]))
        f = [float(c.split("Hz")[0]) for c in cases]
        kw = plotstyle.marker_kw(COL[key]) | {"linestyle": "-"}
        axs[0].plot(f, [w["ratio"][c]["mean"] for c in cases], color=COL[key], label=LAB[key], **kw)
        g = p1[key]["grid"]["oracle"]
        cs = sorted([c for c in g["P_rail_recovery_mW"] if c.endswith("_0.3mm")], key=lambda c: float(c.split("Hz")[0]))
        axs[1].plot([float(c.split("Hz")[0]) for c in cs], [g["P_rail_recovery_mW"][c]["mean"] for c in cs],
                    color=COL[key], label=LAB[key], **kw)
        axs[2].plot([float(c.split("Hz")[0]) for c in cs], [g["P_rail_classB_mW"][c]["mean"] for c in cs],
                    color=COL[key], label=LAB[key], **kw)
    axs[0].set_title("35 deg, -20 % tolerance, 0.3 mm", loc="left", fontsize=9)
    axs[0].set_ylabel("Oracle ink error / neutral")
    axs[1].set_title("Rail power, charge recovery, 0.3 mm", loc="left", fontsize=9)
    axs[1].set_ylabel("mW (both axes)")
    axs[2].set_title("Rail power, class-B, 0.3 mm", loc="left", fontsize=9)
    axs[2].set_ylabel("mW (both axes)")
    for ax in axs:
        ax.set_xlabel("Tremor frequency (Hz)")
        ax.set_ylim(0, None)
    axs[0].legend(fontsize=7.5)
    plotstyle.stamp(fig, "simulation", "model P1 with each design's Hall noise; not measured")
    fig.tight_layout()
    _save(fig, "fig_hw_validation_worstcase_power.png")


def fig_section(res):
    """Cross-sections at the bender station with the tips at the stops: P0.1.2 and P0.2."""
    import matplotlib.pyplot as plt
    from . import model as MD
    designs = [("P0.1.2", MD.CURRENT, "Q", 0.40, 1, S[1]),
               ("P0.2", res["recommended"]["x"], res["recommended"]["options"]["topology"], None,
                res["recommended"]["options"]["stack"], S[0])]
    so = res.get("static_optimum")
    if so and so.get("stage_key") != res["recommended"].get("candidate"):
        designs.append(("P0.2s", so["x"], so["options"]["topology"], None, so["options"]["stack"], S[6]))
    fig, axs = plt.subplots(1, len(designs), figsize=(3.6 * len(designs), 3.6))
    for ax, (name, x, topo, sw, stack, c) in zip(axs, designs):
        rb = MD.R_BORE * 1e3
        ax.add_patch(plt.Circle((0, 0), rb, fill=False, color=plotstyle.INK2, lw=1.2))
        ax.add_patch(plt.Circle((0, 0), MD.R_REFILL * 1e3, color=S[2], alpha=0.5))
        zg, zcc = x["zg"], x["zc0"] + 1.5e-3
        n = zg / (zg - zcc)
        sweep = sw if sw is not None else x["q_stop"] / n * 1e3 + 0.05
        t = (stack * x["t"] + (stack - 1) * 0.05e-3) * 1e3
        w, d = x["w"] * 1e3, x["d"] * 1e3
        rects = []
        if topo in ("Q", "Q2L"):
            for sx in (-1, 1):
                rects.append((sx * d - t / 2, sx * d + t / 2, -w / 2, w / 2, 1))
                rects.append((-w / 2, w / 2, sx * d - t / 2, sx * d + t / 2, 0))
        else:
            rects.append((-d - t / 2, -d + t / 2, -1.2, w - 1.2, 1))
            rects.append((-1.2, w - 1.2, -d - t / 2, -d + t / 2, 0))
        for x0, x1, y0, y1, ax_x in rects:
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=c, alpha=0.85))
            if ax_x:
                ax.add_patch(plt.Rectangle((x0 - sweep, y0), x1 - x0 + 2 * sweep, y1 - y0, fill=False, ec=c, lw=0.8, ls="--"))
            else:
                ax.add_patch(plt.Rectangle((x0, y0 - sweep), x1 - x0, y1 - y0 + 2 * sweep, fill=False, ec=c, lw=0.8, ls="--"))
        ax.set_xlim(-4.3, 4.3)
        ax.set_ylim(-4.3, 4.3)
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_title(f"{name}: {w:.2f} x {t:.2f} mm plates, sweep +/-{sweep:.2f} mm", loc="left", fontsize=8.5)
        ax.tick_params(labelsize=7)
    axs[0].set_ylabel("mm")
    fig.suptitle("Bender station in the 7.9 mm bore (dashed: tips at the stops; green disc: refill)", x=0.01, ha="left",
                 fontsize=9.5)
    plotstyle.stamp(fig, "proposed design", "fit formulas of mechanics/cad/pencil_revP.py")
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    _save(fig, "fig_hw_section.png")


def make_all(res, p1):
    plotstyle.apply()
    for fn in (fig_pareto, fig_topologies, fig_sensitivity, fig_fc_sweep, fig_section, fig_stop_sweep):
        try:
            fn(res)
        except Exception as e:  # a missing block must not stop the others
            print("figure", fn.__name__, "failed:", e)
    rec = res.get("recommended", {})
    if rec.get("candidate"):
        LAB["P02"] = f"P0.2 recommended (= {rec['candidate']})"
    keys = ["Q26", "P02"] + [a["stage_key"] for a in res.get("alternatives", [])]
    try:
        fig_validation(p1, keys)
    except Exception as e:
        print("figure validation failed:", e)
