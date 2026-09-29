r"""Figures of study N, each with its CSV twin (the data behind it).  Style: stabpen.plotstyle (validated categorical
order, one y-axis per panel, 2 px lines, legends for >= 2 series, text in ink colours, an evidence stamp).

fig_nose2_travel_by_task    travel each task needs (CALC)
fig_nose2_designs           autowrite power and added mass against guaranteed travel, per candidate and handle (CALC)
fig_nose2_magnetics         surrogate against magpylib (CALC)
fig_nose2_autowrite_example target letters and the ink laid by the pen while the hand sweeps with tremor (SIM)
fig_nose2_autowrite_grid    ink error and letters read against tremor amplitude, test writers and seeds (SIM)
fig_nose2_size_speed        largest letter size the planner fits against the nose's reach (CALC)
fig_nose2_delayed_ink       travel for ink that trails the hand, against the delay (CALC)
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, List

import numpy as np

from . import ensure_paths

ensure_paths()
from stabpen import plotstyle as PS  # noqa: E402

PS.apply()
import matplotlib.pyplot as plt  # noqa: E402

KIND_LABEL = {"gimbal_radial": "C1 gimbal, radial gap (Rev H type)", "gimbal_axial": "C1+ gimbal, flat axial gap",
              "gimbal_sphere": "C1S gimbal, spherical gap", "dual_plane": "C2 two actuation planes",
              "coarse_fine": "C3 coarse-fine", "xy_wire": "C4a translating carrier on wires"}
KIND_ORDER = ["gimbal_sphere", "gimbal_radial", "gimbal_axial", "dual_plane", "coarse_fine", "xy_wire"]
DESIGN_LABEL = {"revJ": "Rev J nose, pen lift", "revJ_noaxial": "Rev J nose, no pen lift", "revH": "Rev H nose (\u00b13 mm)"}


def _csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([("" if v is None else (round(v, 5) if isinstance(v, float) else v)) for v in r])


def _save(fig, path, status):
    PS.stamp(fig, status)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ travel by task
def travel_by_task(tasks: Dict, rec: Dict, out: str) -> str:
    import re
    req = tasks["requirements"]
    labels = [re.sub(r"(\d)ms", r"\1 ms", r["task"]) for r in req]
    vals = [r["travel_mm"] for r in req]
    fig, ax = plt.subplots(figsize=(8.2, 0.32 * len(req) + 1.6))
    y = np.arange(len(req))[::-1]
    ax.set_axisbelow(True)
    ax.barh(y, vals, height=0.62, color=PS.SERIES[0])
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("tip travel needed, radius at the ball (mm)")
    ax.set_ylim(-0.7, len(req) + 1.1)
    xr = rec["design"]["X_min_mm"]
    for n, (x, txt) in enumerate(((3.0, "Rev H usable travel 3 mm"), (xr, f"Rev J guaranteed travel {xr:.1f} mm"))):
        ax.axvline(x, color=PS.INK2, lw=1.2, ls="--")
        ax.text(x, len(req) + 0.35 - 0.75 * n, " " + txt, color=PS.INK2, fontsize=8, va="center")
    ax.grid(axis="y", visible=False)
    ax.set_title("Travel each task needs (worst tuning writer or seed)")
    p = os.path.join(out, "fig_nose2_travel_by_task.png")
    _save(fig, p, "CALCULATION on synthetic writers and tremor")
    _csv(p.replace(".png", ".csv"), ["task", "travel_mm", "basis"], [[r["task"], r["travel_mm"], r["basis"]] for r in req])
    return p


# ------------------------------------------------------------------ designs
def designs(best: List[Dict], rec: Dict, out: str) -> str:
    from .choose import best_per_cell, J
    cells = [c for c in best_per_cell(best) if abs(c["mu_m"] - 4.0) < 1e-9]
    kinds = [k for k in KIND_ORDER if any(c["kind"] == k for c in cells)]
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 7.0), sharex=True, sharey="row")
    rows = []
    for j, bore in enumerate(("22", "24")):
        for i, (key, lab) in enumerate((("P_autowrite_W", "coil loss while autowriting\nwith 1 mm tremor (W)"),
                                        ("mass_added_g", "added mass: actuator,\nflexure, iron (g)"))):
            ax = axes[i, j]
            for n, k in enumerate(kinds):
                pts = sorted([c for c in cells if c["kind"] == k and c["bore"] == bore and c.get("feasible")],
                             key=lambda c: c["x_min_req_mm"])
                if pts:
                    ax.plot([c["x_min_req_mm"] for c in pts], [c[key] for c in pts], color=PS.SERIES[n], lw=2,
                            label=KIND_LABEL[k], **{k2: v for k2, v in PS.marker_kw(PS.SERIES[n]).items() if k2 != "linestyle"})
                if i == 0:
                    for c in [c for c in cells if c["kind"] == k and c["bore"] == bore]:
                        rows.append([bore, k, c["x_min_req_mm"], bool(c.get("feasible")), c["P_autowrite_W"], c["mass_added_g"],
                                     c["Km_tip"], c["m_eff_tip_g"], J(c)])
            if i == 0:
                ax.axhline(0.2, color=PS.INK2, lw=1.0, ls="--")
                ax.text(0.02, 0.2, "coil 20 K above ambient", color=PS.INK2, fontsize=7.5, va="bottom",
                        transform=ax.get_yaxis_transform())
                ax.set_ylim(0.0, 0.3)
                ax.set_title(f"handle {bore} mm")
            if j == 0:
                ax.set_ylabel(lab)
            if i == 1:
                ax.set_xlabel("guaranteed tip travel over 35-75 deg (mm)")
            d = rec["design"]
            if (bore == "22" and rec["handle_od"] == 22.0) or (bore == "24" and rec["handle_od"] == 24.0):
                ax.plot([d["X_min_mm"]], [d[key]], marker="o", ms=13, mfc="none", mec=PS.INK, mew=1.5, ls="none")
                if i == 0:
                    ax.annotate("recommended", (d["X_min_mm"], d[key]), textcoords="offset points", xytext=(8, -14), fontsize=8,
                                color=PS.INK)
    hl = {}
    for ax in axes.ravel():
        for hnd, lab in zip(*ax.get_legend_handles_labels()):
            hl.setdefault(lab, hnd)
    for n, k in enumerate(kinds):                       # every candidate in the legend, feasible or not
        if KIND_LABEL[k] not in hl:
            hl[KIND_LABEL[k] + " (no feasible design)"] = plt.Line2D([], [], color=PS.SERIES[n], lw=2)
    fig.legend(list(hl.values()), list(hl.keys()), loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Best feasible design per candidate (lowest power + 4 W/kg x mass); lines end where no design is feasible", fontsize=10)
    fig.tight_layout()
    p = os.path.join(out, "fig_nose2_designs.png")
    _save(fig, p, "CALCULATION (design models, optimised)")
    _csv(p.replace(".png", ".csv"), ["handle_mm", "candidate", "travel_req_mm", "feasible", "P_autowrite_W", "mass_added_g",
                                     "Km_tip_N_per_sqrtW", "m_eff_tip_g", "J"], rows)
    return p


# ------------------------------------------------------------------ Pareto fronts
def pareto(fronts: Dict, out: str) -> str:
    """Non-dominated designs of every candidate (maximise travel and force per sqrt(W), minimise added mass and power),
    as small multiples: coil loss against added mass, one colour per guaranteed travel (the travel constraint is active,
    so every design sits at a whole-mm travel)."""
    kinds = [k for k in KIND_ORDER if k in fronts]
    n = len(kinds)
    ncol = 3
    nrow = int(math.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(11.0, 3.4 * nrow), sharex=True, sharey=True, squeeze=False)
    travels = sorted({round(r["X_min_mm"]) for k in kinds for r in fronts[k]["front4"]})
    col = {x: PS.SERIES[i] for i, x in enumerate(travels[:3])}
    rows = []
    for i, k in enumerate(kinds):
        ax = axes[i // ncol, i % ncol]
        F = fronts[k]["front4"]
        for x in travels[:3]:
            sub = [r for r in F if round(r["X_min_mm"]) == x]
            if sub:
                ax.plot([r["mass_added_g"] for r in sub], [r["P_autowrite_W"] for r in sub], color=col[x], marker="o", ms=5,
                        mec=PS.SURFACE, mew=0.6, ls="none", alpha=0.85, label=f"{x:g} mm guaranteed travel")
        ax.axhline(0.2, color=PS.INK2, lw=1.0, ls="--")
        ax.set_title(f"{KIND_LABEL[k]} ({len(F)} designs)", fontsize=9)
        ax.set_ylim(0.0, 0.3)
        if i % ncol == 0:
            ax.set_ylabel("coil loss, autowrite + 1 mm tremor (W)")
        if i // ncol == nrow - 1 or (i + ncol) >= n:
            ax.set_xlabel("added mass (g)")
            ax.tick_params(labelbottom=True)
        for r in F:
            rows.append([k, r["X_min_mm"], r["Km_tip"], r["mass_added_g"], r["P_autowrite_W"], r.get("bore")])
    for j in range(n, nrow * ncol):
        axes[j // ncol, j % ncol].set_visible(False)
    hl = {}
    for ax in axes.ravel():
        for hnd, lab in zip(*ax.get_legend_handles_labels()):
            hl.setdefault(lab, hnd)
    labs = sorted(hl, key=lambda t: float(t.split()[0]))
    fig.legend([hl[t] for t in labs], labs, loc="lower center", ncol=len(labs), bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("Pareto fronts (travel, force per \u221aW, added mass, power), both handles; dashed: coil 20 K above ambient",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    p = os.path.join(out, "fig_nose2_pareto.png")
    _save(fig, p, "CALCULATION (design models, optimised)")
    _csv(p.replace(".png", ".csv"), ["candidate", "X_min_mm", "Km_tip_N_per_sqrtW", "mass_added_g", "P_autowrite_W", "handle_bore"], rows)
    return p


# ------------------------------------------------------------------ magnetics
def magnetics(mg: Dict, out: str) -> str:
    fig, ax = plt.subplots(figsize=(5.2, 4.8))
    rows = []
    for n, kind in enumerate(("radial", "axial")):
        e = np.array(mg[kind]["parity"]["eta"]); p = np.array(mg[kind]["parity"]["eta_pred"])
        ax.plot(e, p, color=PS.SERIES[n], label=f"{kind} gap ({len(e)} designs)", **{k: v for k, v in PS.marker_kw(PS.SERIES[n]).items()
                                                                                       if k != "markersize"}, markersize=5)
        rows += [[kind, a, b] for a, b in zip(e, p)]
    lim = [0, max(max(r[1], r[2]) for r in rows) * 1.05]
    ax.plot(lim, lim, color=PS.INK2, lw=1.0, ls="--")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("flux factor eta, magpylib with iron images")
    ax.set_ylabel("flux factor eta, surrogate used by the optimiser")
    ax.legend(loc="upper left")
    ax.set_title("Gap-flux surrogate against magpylib")
    p = os.path.join(out, "fig_nose2_magnetics.png")
    _save(fig, p, "CALCULATION (magpylib, ideal iron)")
    _csv(p.replace(".png", ".csv"), ["topology", "eta_magpylib", "eta_surrogate"], rows)
    return p


# ------------------------------------------------------------------ autowrite example
def autowrite_example(designs_hw1: Dict, st, out: str, w: int = 0, seed: int = 200, f0: float = 8.0, amp: float = 1.0e-3,
                      h_mm: float = 2.5) -> str:
    from . import autowrite as AW
    from .tuning import sensor_seed
    panels = [("revJ", "Rev J nose with pen lift"), ("revJ_noaxial", "Rev J nose, ball kept on the paper (no pen lift)")]
    fig, axes = plt.subplots(len(panels) + 1, 1, figsize=(10.5, 5.0), sharex=True, sharey=True)
    rows = []
    c0 = AW.build(w, seed, h_mm, f0, amp, designs_hw1["revJ"], st)
    # the hand: the sweep plus tremor (the page-plane handle position the pen sees)
    ax = axes[0]
    ax.plot(c0.scn.pref[:, 0] * 1e3, c0.scn.pref[:, 1] * 1e3, color=PS.MUTED, lw=1.0)
    ax.set_title(f"The hand: a steady sweep at {c0.meta['v_h'] * 1e3:.1f} mm/s with {amp * 1e3:g} mm tremor at {f0:g} Hz "
                 f"(test writer {w}, seed {seed})", fontsize=9.5, loc="left")
    ax.set_ylabel("y (mm)")
    for t, x in zip(c0.scn.t[::40], c0.scn.pref[::40]):
        rows.append(["hand", "", float(t), float(x[0] * 1e3), float(x[1] * 1e3), 1])
    metrics = {}
    for ax, (key, title) in zip(axes[1:], panels):
        c = AW.build(w, seed, h_mm, f0, amp, designs_hw1[key], st)
        m = AW.run(c, sensor_seed(w, seed, f0, amp), keep=True)
        res = m.pop("_res"); m.pop("_cmd", None)
        metrics[key] = m
        for L in c.written.letters:
            for pl in L.polylines:
                P = np.asarray(pl)
                ax.plot(P[:, 0] * 1e3, P[:, 1] * 1e3, color=PS.GRID, lw=3.2, solid_capstyle="round")
        ink = res.ink * 1e3
        dn = res.contact > 0.5
        seg = np.split(np.arange(len(dn)), np.flatnonzero(np.diff(dn.astype(int)) != 0) + 1)
        for s in seg:
            if dn[s[0]] and len(s) > 1:
                ax.plot(ink[s, 0], ink[s, 1], color=PS.SERIES[0], lw=1.2)
        for k in range(0, len(dn), 40):
            rows.append([key, "ink", float(res.t[k]), float(ink[k, 0]), float(ink[k, 1]), int(dn[k])])
        ax.set_title(f"{title}: ink error {m['ink_err_um']:.0f} \u00b5m rms, letters read {m['letters_read'] * 100:.0f} % "
                     f"(ceiling {m['target_letters_read'] * 100:.0f} %), app read “{m['recognised']}”", fontsize=9, loc="left")
        ax.set_ylabel("y (mm)")
    for ax in axes:
        ax.set_aspect("equal", adjustable="box")
        ax.set_ylim(-2.2, 5.8)
    for L in c0.written.letters:
        for pl in L.polylines:
            for x, y in np.asarray(pl)[::8]:
                rows.append(["target", L.char, None, float(x * 1e3), float(y * 1e3), 1])
    axes[-1].set_xlabel("x along the line (mm); grey: the target letters, blue: ink")
    fig.subplots_adjust(left=0.06, right=0.99, top=0.95, bottom=0.1, hspace=0.35)
    p = os.path.join(out, "fig_nose2_autowrite_example.png")
    _save(fig, p, "SIMULATION (HW1, synthetic writer and tremor)")
    _csv(p.replace(".png", ".csv"), ["series", "detail", "t_s", "x_mm", "y_mm", "pen_down"], rows)
    return p, metrics


# ------------------------------------------------------------------ test grid
def autowrite_grid(summary: List[Dict], out: str) -> str:
    groups = sorted({(r["design"], r["h_mm"]) for r in summary}, key=lambda g: (["revJ", "revJ_noaxial", "revH"].index(g[0])
                                                                                if g[0] in ("revJ", "revJ_noaxial", "revH") else 9, g[1]))
    # a design whose plans all failed has no ink to show: it is named in the title instead of the legend
    empty = [g for g in groups if all(r.get("ink_err_um") is None for r in summary if (r["design"], r["h_mm"]) == g)]
    groups = [g for g in groups if g not in empty]
    nfail = sum(r["plan_fail"] for r in summary if (r["design"], r["h_mm"]) in groups)
    ntot = sum(r["n"] for r in summary if (r["design"], r["h_mm"]) in groups)
    amps = sorted({r["amp_mm"] for r in summary})
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.0))
    rows = []
    for n, (d, h) in enumerate(groups):
        lab = f"{DESIGN_LABEL.get(d, d)}, {h:g} mm letters"
        ys = {k: [] for k in ("ink_err_um", "letters_read", "P_coil_W")}
        for a in amps:
            sub = [r for r in summary if r["design"] == d and r["h_mm"] == h and r["amp_mm"] == a]
            for k in ys:
                v = [r[k] for r in sub if r.get(k) is not None]
                ys[k].append(float(np.mean(v)) if v else np.nan)
            rows.append([d, h, a, ys["ink_err_um"][-1], ys["letters_read"][-1], ys["P_coil_W"][-1],
                         float(np.mean([r["target_letters_read"] for r in sub if r.get("target_letters_read") is not None] or [np.nan])),
                         sum(r["plan_fail"] for r in sub), sum(r["n"] for r in sub)])
        for ax, k in zip(axes, ("ink_err_um", "letters_read", "P_coil_W")):
            y = np.array(ys[k]) * (100.0 if k == "letters_read" else 1.0)
            ax.plot(amps, y, color=PS.SERIES[n], label=lab, **{k2: v for k2, v in PS.marker_kw(PS.SERIES[n]).items() if k2 != "linestyle"})
    ceil = [r[6] for r in rows if r[0] == "revJ" and r[1] == 2.5]
    if ceil and np.isfinite(np.nanmean(ceil)):
        axes[1].axhline(100 * float(np.nanmean(ceil)), color=PS.INK2, lw=1.0, ls="--")
        axes[1].text(0.02, 100 * float(np.nanmean(ceil)), "ceiling: the recogniser on the clean target letters", color=PS.INK2,
                     fontsize=7.5, va="bottom", transform=axes[1].get_yaxis_transform())
    axes[0].set_ylabel("ink error to the target letters (\u00b5m rms)")
    axes[1].set_ylabel("letters read by the app's recogniser (%)")
    axes[2].set_ylabel("coil loss while writing (W)")
    axes[0].set_ylim(bottom=0.0)
    axes[2].set_ylim(bottom=0.0)
    lo = min([v for r in rows for v in [r[4]] if v == v] + [0.7])
    axes[1].set_ylim(100 * max(0.0, lo - 0.05), 101.0)
    for ax in axes:
        ax.set_xlabel("hand tremor amplitude (mm peak; mean of 4, 8, 12 Hz)")
        ax.set_xticks(amps)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=len(groups), bbox_to_anchor=(0.5, -0.08))
    note = f"; {nfail} of {ntot} cases had no plan at the tuned speed (not averaged)" if nfail else ""
    if empty:
        note += "; no plan fitted for " + ", ".join(f"{DESIGN_LABEL.get(d, d)} at {h:g} mm" for d, h in empty)
    fig.suptitle("Autowrite on the test writers 0-5 and seeds 200-203" + note, fontsize=10)
    fig.tight_layout()
    p = os.path.join(out, "fig_nose2_autowrite_grid.png")
    _save(fig, p, "SIMULATION (HW1, synthetic writers and tremor)")
    _csv(p.replace(".png", ".csv"), ["design", "x_height_mm", "tremor_amp_mm", "ink_err_um", "letters_read", "P_coil_W",
                                     "target_letters_read", "plan_failures", "cases"], rows)
    return p


# ------------------------------------------------------------------ size and speed
def size_speed(limits: Dict, out: str) -> str:
    cur = sorted(limits["curve"].values(), key=lambda v: v["reach_mm"])
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8))
    mk = {k: v for k, v in PS.marker_kw(PS.SERIES[0]).items() if k != "linestyle"}
    c1 = [v for v in cur if v["largest_x_height_mm"] > 0]          # 0 = not even the smallest size fits: not plotted
    axes[0].plot([v["reach_mm"] for v in c1], [v["largest_x_height_mm"] for v in c1], color=PS.SERIES[0], **mk)
    axes[0].set_xlabel("plan reach of the nose (mm)")
    axes[0].set_ylabel("largest x-height every test writer fits (mm)")
    axes[0].set_ylim(bottom=0.0)
    c2 = [v for v in cur if v["letters_per_s_at_fastest"] > 0]
    axes[1].plot([v["reach_mm"] for v in c2], [v["letters_per_s_at_fastest"] for v in c2], color=PS.SERIES[0], **mk)
    axes[1].set_ylim(bottom=0.0)
    axes[1].set_xlabel("plan reach of the nose (mm)")
    axes[1].set_ylabel("letters per second, fastest sweep at 2.5 mm")
    notes = []
    for k, v in limits["by_design"].items():
        if v["largest_x_height_mm"] <= 0:
            notes.append(f"{DESIGN_LABEL.get(k, k)} (plan reach {v['reach_mm']:.1f} mm): no size fits every test writer")
            continue
        axes[0].annotate(DESIGN_LABEL.get(k, k), (v["reach_mm"], v["largest_x_height_mm"]), textcoords="offset points", xytext=(6, -12),
                         fontsize=8, color=PS.INK2)
        axes[0].plot([v["reach_mm"]], [v["largest_x_height_mm"]], marker="o", ms=11, mfc="none", mec=PS.INK, ls="none")
    for n_, t in enumerate(notes):
        axes[0].text(0.35, 0.08 + 0.07 * n_, t, transform=axes[0].transAxes, fontsize=8, color=PS.INK2, va="bottom")
    fig.suptitle("What the reach buys (planner, test writers, seed 200)", fontsize=10.5)
    fig.tight_layout()
    p = os.path.join(out, "fig_nose2_size_speed.png")
    _save(fig, p, "CALCULATION (planner)")
    _csv(p.replace(".png", ".csv"), ["reach_mm", "largest_x_height_mm", "fastest_speed_factor_at_2.5mm", "letters_per_s_at_fastest"],
         [[v["reach_mm"], v["largest_x_height_mm"], v["fastest_speed_factor_at_2.5mm"], v["letters_per_s_at_fastest"]] for v in cur])
    return p


# ------------------------------------------------------------------ delayed ink
def delayed_ink(di: Dict, rec: Dict, out: str) -> str:
    taus = sorted(di, key=lambda k: float(k.replace("ms", "")))
    t = [float(k.replace("ms", "")) for k in taus]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    s1 = [di[k]["synthetic_p99_mm"] for k in taus]
    s2 = [di[k]["adult_speed_p99_mm"] for k in taus]
    ax.plot(t, s1, color=PS.SERIES[0], label="synthetic writers' own speed (p99)", **{k: v for k, v in PS.marker_kw(PS.SERIES[0]).items()
                                                                                     if k != "linestyle"})
    ax.plot(t, s2, color=PS.SERIES[1], label="rescaled to the adult phrase speed 30.5 mm/s (p99)",
            **{k: v for k, v in PS.marker_kw(PS.SERIES[1]).items() if k != "linestyle"})
    xr = rec["design"]["X_min_mm"]
    ax.axhline(xr, color=PS.INK2, lw=1.0, ls="--")
    ax.text(t[0], xr, f" Rev J guaranteed travel {xr:.1f} mm", color=PS.INK2, fontsize=8, va="bottom")
    ax.set_xlabel("ink delay behind the hand (ms)")
    ax.set_ylabel("tip travel needed (mm)")
    ax.legend(loc="upper left")
    ax.set_title("Delayed ink: how far the tip must reach back")
    p = os.path.join(out, "fig_nose2_delayed_ink.png")
    _save(fig, p, "CALCULATION on synthetic writers")
    _csv(p.replace(".png", ".csv"), ["delay_ms", "synthetic_p50_mm", "synthetic_p95_mm", "synthetic_p99_mm", "adult_speed_p99_mm",
                                     "inked_share_lifted_before_finish"],
         [[a, di[k]["synthetic_p50_mm"], di[k]["synthetic_p95_mm"], di[k]["synthetic_p99_mm"], di[k]["adult_speed_p99_mm"],
           di[k]["inked_share_lifted_before_finish"]] for a, k in zip(t, taus)])
    return p


def all_figures(data: Dict, out, quick: bool = False) -> Dict:
    from dataclasses import replace
    from . import autowrite as AW
    out = str(out)
    rec = data["choose"]["recommended"]
    files = {"travel_by_task": travel_by_task(data["tasks"], rec, out), "designs": designs(data["optimise"]["best"], rec, out),
             "magnetics": magnetics(data["magnetics"], out), "size_speed": size_speed(data["limits"], out),
             "pareto": pareto(data["optimise"]["fronts"], out),
             "delayed_ink": delayed_ink(data["tasks"]["delayed_ink"], rec, out),
             "autowrite_grid": autowrite_grid(data["test"]["summary"], out)}
    ds = {k: AW.NoseDesign(**v) for k, v in data["choose"]["hw1_designs"].items()}
    st = replace(AW.AWSettings(), **data["tuning"]["settings"])
    p, m = autowrite_example(ds, st, out)
    files["autowrite_example"] = p
    files["autowrite_example_metrics"] = m
    return files
