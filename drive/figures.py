"""Figures of study D (each PNG has a CSV twin with the plotted numbers) and the summary table of the report.

Evidence status is stamped on every figure: CALC for the design figures, SIM for the task figures (HW1-D model,
test writers 0-5 with the frozen rules of results/drive/rules.json).  Nothing here is a measurement.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths

ensure_paths()
from stabpen import plotstyle as ps  # noqa: E402

ps.apply()
import matplotlib.pyplot as plt  # noqa: E402

LABEL = {
    "none": "Rev H, nothing on",
    "nose_partial": "nose alone (partial)",
    "board_partial": "desk board, partial",
    "board_full": "desk board, full",
    "board_lead": "desk board, lead",
    "board_lead+nose": "desk board lead + nose",
    "ball_partial": "heel ball, partial",
    "ball_full": "heel ball, full",
    "ball_lead": "heel ball, lead",
    "ball_lead+nose": "heel ball lead + nose",
    "ball_damp": "heel ball, damper",
    "ball_brake": "heel ball, brake",
    "ball_damp+nose_akf": "ball damper + nose",
    "wheel_path": "steered wheel (steer only)",
    "wheel_partial": "steered wheel, free in band",
    "wheel_path+nose": "steered wheel + nose",
    "sd_full": "steered + driven wheel",
    "sd_path": "driven wheel, steer only",
    "sd_lead": "steered + driven wheel, lead",
    "sd_lead+nose": "wheel lead + nose",
    "wheel_tremor_brake": "wheel: steer + brake",
    "wheel_known_text": "wheel on known text",
    "nose_akf": "nose (tremor tracker)",
    "nose_oracle": "nose (oracle)",
    "writer_alone": "writer alone (writes)",
    "nose_nogate": "nose alone (writer writes)",
    "relaxed_nose": "relaxed hand, nose only",
}
SIM_STAMP = "SIM (HW1-D model; test writers, frozen rules; nothing measured)"
CALC_STAMP = "CALC (proposed design; catalogue data and assumptions; nothing measured)"


def lab(c: str) -> str:
    return LABEL.get(c, c)


def _csv(path: Path, header: List[str], rows: List[List]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if (isinstance(v, float) and math.isnan(v)) else v for v in r])


def _get(cell: Dict, k: str) -> float:
    v = cell.get(k)
    return float("nan") if v is None else float(v)


def _save(fig, out: Path, name: str, status: str, extra: str = "") -> Path:
    ps.stamp(fig, status, extra)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = out / f"{name}.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ============================================================================== design figures (CALC)
def fig_geometry(design: Dict, out: Path) -> Path:
    pods = design["geometry"].get("pods", [])
    r = np.array([p["r_e_mm"] for p in pods])
    bare = np.array([p["R_bare_mm"] for p in pods])
    wh = np.array([p["R_wheel_pod_mm"] for p in pods])
    bl = np.array([p["R_ball_pod_mm"] for p in pods])
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4))
    ax = axs[0]
    ax.plot(r, bare, color=ps.MUTED, lw=1.5, ls="--", label="element alone")
    ax.plot(r, wh, color=ps.SERIES[0], label="steered wheel + steering ring")
    ax.plot(r, bl, color=ps.SERIES[1], label="ball + two drive rollers (r 0.6 mm)")
    ax.axhline(6.75, color=ps.INK2, lw=1, ls=":")
    ax.text(r.min(), 6.9, "Rev H skid ring 6.75 mm (DEC-034)", fontsize=8, color=ps.INK2)
    ax.set_xlabel("element radius r_e (mm)")
    ax.set_ylabel("heel contact radius needed (mm)")
    ax.set_title("The drive must sit outside the swinging nose", loc="left")
    ax.legend(loc="lower right")
    ax = axs[1]
    fe = [p["front_end"] for p in pods]
    ax.plot(r, [f["sleeve_front_d_mm"] for f in fe], color=ps.SERIES[0], label="sleeve front diameter (wheel pod)")
    ax.plot(r, [f["refill_slide_range_mm"] for f in fe], color=ps.SERIES[2], label="refill slide over 35-75 deg")
    ax.plot(r, [f["ball_ahead_50_mm"] for f in fe], color=ps.SERIES[3], label="ink ball ahead of the heel at 50 deg")
    ref = design["geometry"]["heel_1p0"]["front_end_revH"]
    ax.axhline(ref["sleeve_front_d_mm"], color=ps.SERIES[0], lw=1, ls=":")
    ax.axhline(ref["refill_slide_range_mm"], color=ps.SERIES[2], lw=1, ls=":")
    ax.axhline(ref["ball_ahead_50_mm"], color=ps.SERIES[3], lw=1, ls=":")
    ax.text(r.min(), ref["sleeve_front_d_mm"] + 0.3, "dotted: Rev H today", fontsize=8, color=ps.INK2)
    ax.set_xlabel("element radius r_e (mm)")
    ax.set_ylabel("mm")
    ax.set_title("What the bigger heel costs the front end", loc="left")
    ax.legend(loc="upper left", fontsize=7.5)
    p = _save(fig, out, "fig_heel_geometry", CALC_STAMP, "drive/geometry.py; opt/inertial/front_end.py method")
    _csv(out / "fig_heel_geometry.csv",
         ["r_e_mm", "R_element_alone_mm", "R_wheel_pod_mm", "R_ball_pod_mm", "sleeve_front_d_mm_wheel_pod",
          "refill_slide_mm_wheel_pod", "ball_ahead_50deg_mm_wheel_pod"],
         [[p_["r_e_mm"], p_["R_bare_mm"], p_["R_wheel_pod_mm"], p_["R_ball_pod_mm"], p_["front_end"]["sleeve_front_d_mm"],
           p_["front_end"]["refill_slide_range_mm"], p_["front_end"]["ball_ahead_50_mm"]] for p_ in pods])
    return p


def fig_capacity(design: Dict, out: Path) -> Path:
    cap = design["capacity"]
    Ps = sorted({c["P_N"] for c in cap})
    mus = sorted({c["mu"] for c in cap})
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2))
    rows = []
    for i, mu in enumerate(mus):
        sel = [c for c in cap if c["mu"] == mu]
        sel.sort(key=lambda c: c["P_N"])
        axs[0].plot([c["P_N"] for c in sel], [c["cap_mean_N"] for c in sel], color=ps.SERIES[i], label=f"mean, mu {mu:g}")
        axs[0].plot([c["P_N"] for c in sel], [c["cap_p10_N"] for c in sel], color=ps.SERIES[i], ls="--", lw=1.4,
                    label=f"weakest 10 % of writers, mu {mu:g}")
        for c in sel:
            rows.append([c["P_N"], mu, c["cap_mean_N"], c["cap_p10_N"], c["cap_p50_N"], c["share_full"]])
    axs[0].axhline(0.4, color=ps.MUTED, lw=1, ls="-.")
    axs[0].text(Ps[0], 0.42, "desk board cap 0.4 N", fontsize=8, color=ps.INK2)
    axs[0].set_xlabel("preload of the sprung element P (N)")
    axs[0].set_ylabel("traction force available (N)")
    axs[0].set_title("Traction the paper gives, over the writer population", loc="left")
    axs[0].legend(fontsize=7, loc="upper left")
    sel = sorted([c for c in cap if c["mu"] == mus[0]], key=lambda c: c["P_N"])
    axs[1].plot([c["P_N"] for c in sel], [100 * c["share_full"] for c in sel], color=ps.SERIES[0])
    axs[1].plot([c["P_N"] for c in sel], [100 * c["share_full"] for c in sel], **ps.marker_kw(ps.SERIES[0]))
    axs[1].set_xlabel("preload P (N)")
    axs[1].set_ylabel("writers whose mean force keeps the element fully loaded (%)")
    axs[1].set_title("Light writers unload the heel", loc="left")
    p = _save(fig, out, "fig_traction_capacity", CALC_STAMP,
              "writer force CON-01 lognormal; ball carries 0.196 N; mu range ASSUMPTION (AMF-111)")
    _csv(out / "fig_traction_capacity.csv", ["P_N", "mu", "cap_mean_N", "cap_p10_N", "cap_p50_N", "share_full"], rows)
    return p


def fig_design_pareto(design: Dict, out: Path) -> Optional[Path]:
    par = design.get("design_opt", {}).get("pareto", {})
    if not par:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    rows = []
    for i, (concept, pr) in enumerate(par.items()):
        R = [r["R_d_mm"] for r in pr]
        ax.plot(R, [r["F_use_mean_N"] for r in pr], color=ps.SERIES[i], label=f"{concept}: mean over writers")
        ax.plot(R, [r["F_use_p10_N"] for r in pr], color=ps.SERIES[i], ls="--", lw=1.4, label=f"{concept}: weakest 10 %")
        ax.plot(R, [r["F_use_mean_N"] for r in pr], **ps.marker_kw(ps.SERIES[i]))
        for r in pr:
            rows.append([concept, r["w_dR"], r["R_d_mm"], r["r_e_mm"], r["P_N"], r["G"], r["F_use_mean_N"], r["F_use_p10_N"],
                         r["share_full"], r["m_r_g"], r["P_cu_W"], r["F_rr_N"]])
    ax.set_xlabel("heel contact radius (mm)")
    ax.set_ylabel("usable force at mu 0.6 (N)")
    ax.set_title("Force against heel size (autograd optimum per size weight)", loc="left")
    ax.legend(fontsize=7.5)
    p = _save(fig, out, "fig_design_pareto", CALC_STAMP, "drive/design_opt.py (torch autograd; FD-checked)")
    _csv(out / "fig_design_pareto.csv", ["concept", "w_dR", "R_d_mm", "r_e_mm", "P_N", "G", "F_use_mean_N", "F_use_p10_N",
                                         "share_full", "m_r_g", "P_cu_W", "F_rr_N"], rows)
    return p


# ============================================================================== task figures (SIM)
def _bars(ax, conds, cells, key, scale=1.0, color=None, ylabel="", ref=None):
    y = [_get(cells[c], key) * scale for c in conds]
    e = [_get(cells[c], key + "_sd") * scale for c in conds]
    x = np.arange(len(conds))
    ax.bar(x, y, yerr=e, color=color or ps.SERIES[0], capsize=2, error_kw={"elinewidth": 0.8, "ecolor": ps.INK2})
    ax.set_xticks(x)
    ax.set_xticklabels([lab(c) for c in conds], rotation=35, ha="right", fontsize=7.5)
    ax.set_ylabel(ylabel)
    if ref is not None:
        ax.axhline(ref, color=ps.MUTED, lw=1, ls="-.")
    return y, e


def fig_practice(tasks: Dict, out: Path) -> Optional[Path]:
    pr = tasks.get("practice", {}).get("aggregate", {})
    if not pr:
        return None
    profiles = list(pr.keys())
    conds = [c for c in pr[profiles[0]].keys()]
    order = ["none", "nose_partial", "board_partial", "board_full", "ball_partial", "ball_full", "wheel_path",
             "wheel_partial", "wheel_path+nose", "sd_full"]
    conds = [c for c in order if c in conds] + [c for c in conds if c not in order]
    fig, axs = plt.subplots(len(profiles), 3, figsize=(14, 4.2 * len(profiles)), squeeze=False)
    rows = []
    for i, prof in enumerate(profiles):
        cells = pr[prof]
        _bars(axs[i, 0], conds, cells, "target_err_um", color=ps.SERIES[0], ylabel="distance ink to target letters (um)",
              ref=_get(cells["none"], "target_err_um"))
        axs[i, 0].set_title(f"{prof}: target error", loc="left")
        _bars(axs[i, 1], conds, cells, "letters_read_ok", scale=100, color=ps.SERIES[2], ylabel="letters read as target (%)",
              ref=100 * _get(cells["none"], "letters_read_ok"))
        axs[i, 1].set_title(f"{prof}: letters read by the app recogniser", loc="left")
        _bars(axs[i, 2], conds, cells, "F_rms_N", color=ps.SERIES[1], ylabel="device force on the pen, RMS (N)")
        axs[i, 2].set_title(f"{prof}: force used", loc="left")
        for c in conds:
            cl = cells[c]
            rows.append([prof, c, lab(c), cl.get("n"), _get(cl, "target_err_um"), _get(cl, "target_err_um_sd"),
                         _get(cl, "letters_read_ok"), _get(cl, "error_letters_read_as_target"), _get(cl, "words_app"), _get(cl, "device_share"), _get(cl, "F_rms_N"),
                         _get(cl, "F_p95_N"), _get(cl, "felt_p95_N"), _get(cl, "slide_share"), _get(cl, "slip_events"),
                         _get(cl, "coverage")])
    p = _save(fig, out, "fig_practice", SIM_STAMP, "task (a): guided tracing of the practice sentence")
    _csv(out / "fig_practice.csv", ["profile", "cond", "label", "n", "target_err_um", "target_err_um_sd", "letters_read_ok",
                                    "error_letters_read_as_target", "words_app", "device_share", "F_rms_N", "F_p95_N", "felt_p95_N", "slide_share",
                                    "slip_events", "coverage"], rows)
    return p


def fig_feel(tasks: Dict, out: Path) -> Optional[Path]:
    rs = tasks.get("resisting", {}).get("aggregate", {})
    pr = tasks.get("practice", {}).get("aggregate", {}).get("dysgraphia", {})
    if not rs or not pr:
        return None
    conds = [c for c in ["board_full", "ball_full", "wheel_path", "sd_path", "sd_full"] if c in rs and c in pr]
    x = np.arange(len(conds))
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3))
    rows = []
    for k, (key, title) in enumerate([("felt_p95_N", "Change in grip force the writer feels (95th percentile)"),
                                      ("target_err_um", "Target error")]):
        ax = axs[k]
        a = [_get(pr[c], key) for c in conds]
        b = [_get(rs[c], key) for c in conds]
        ax.bar(x - 0.2, a, 0.4, color=ps.SERIES[0], label="relaxed writer (HAP-26 nominal arm)")
        ax.bar(x + 0.2, b, 0.4, color=ps.SERIES[1], label="lightly resisting writer (upper-CI arm)")
        ax.set_xticks(x)
        ax.set_xticklabels([lab(c) for c in conds], rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("N" if key.endswith("_N") else "um")
        ax.set_title(title, loc="left")
        if k == 0:
            ax.legend(fontsize=7.5)
        for c, va, vb in zip(conds, a, b):
            rows.append([key, c, lab(c), va, vb])
    p = _save(fig, out, "fig_feel_resisting", SIM_STAMP, "task (a) dysgraphia learners; resisting-writer runs")
    _csv(out / "fig_feel_resisting.csv", ["metric", "cond", "label", "relaxed_writer", "lightly_resisting_writer"], rows)
    return p


def fig_loops_reversal(tasks: Dict, out: Path) -> Optional[Path]:
    lp = tasks.get("loops", {}).get("aggregate", {})
    rv = tasks.get("reversal", {}).get("aggregate", {})
    if not lp or not rv:
        return None
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    rows = []
    conds = [c for c in ["none", "board_full", "ball_full", "wheel_path", "sd_path", "sd_full"] if c in lp.get("relaxed", {})]
    x = np.arange(len(conds))
    for i, hand in enumerate(["relaxed", "lightly_resisting"]):
        if hand not in lp:
            continue
        v = [_get(lp[hand][c], "loop_height_ratio_ink") for c in conds]
        e = [_get(lp[hand][c], "loop_height_ratio_ink_sd") for c in conds]
        axs[0].bar(x + (i - 0.5) * 0.4, v, 0.4, yerr=e, color=ps.SERIES[i], capsize=2, label=hand.replace("_", " "))
        for c, vv in zip(conds, v):
            rows.append(["loops", hand, c, "loop_height_ratio_ink", vv])
    axs[0].axhline(1.0, color=ps.MUTED, lw=1, ls="-.")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels([lab(c) for c in conds], rotation=25, ha="right", fontsize=8)
    axs[0].set_ylabel("loop height / 10 mm target")
    axs[0].set_title("(b) 'write big': loops shrinking 0.8 -> 0.6", loc="left")
    axs[0].legend(fontsize=7.5)
    for j, (wtr, key, yl, title) in enumerate([("set on b", "bowl_correct_side", "share of bowl ink on the 'd' side",
                                               "(c) writer set on 'b', template 'd'"),
                                              ("relaxed (lead-through)", "bowl_to_template_rms_mm", "bowl ink to template, RMS (mm)",
                                               "(c) relaxed hand led through 'd'")]):
        cells = rv.get(wtr, {})
        cs = list(cells.keys())
        xx = np.arange(len(cs))
        v = [_get(cells[c], key) for c in cs]
        e = [_get(cells[c], key + "_sd") for c in cs]
        axs[j + 1].bar(xx, v, yerr=e, color=ps.SERIES[2 + j], capsize=2)
        axs[j + 1].set_xticks(xx)
        axs[j + 1].set_xticklabels([lab(c) for c in cs], rotation=25, ha="right", fontsize=8)
        axs[j + 1].set_ylabel(yl)
        axs[j + 1].set_title(title, loc="left")
        for c in cs:
            rows.append(["reversal", wtr, c, key, _get(cells[c], key)])
            rows.append(["reversal", wtr, c, "felt_p95_N", _get(cells[c], "felt_p95_N")])
            rows.append(["reversal", wtr, c, "F_max_N", _get(cells[c], "F_max_N")])
    p = _save(fig, out, "fig_loops_reversal", SIM_STAMP, "tasks (b) and (c)")
    _csv(out / "fig_loops_reversal.csv", ["task", "writer", "cond", "metric", "value"], rows)
    return p


def fig_autowrite(tasks: Dict, out: Path) -> Optional[Path]:
    aw = tasks.get("autowrite", {})
    ag = aw.get("aggregate", {})
    if not ag:
        return None
    order = ["writer_alone", "nose_nogate", "relaxed_nose", "board_lead+nose", "ball_lead", "ball_lead+nose", "sd_lead",
             "sd_lead+nose"]
    conds = [c for c in order if c in ag]
    fig = plt.figure(figsize=(15, 8.2))
    gs = fig.add_gridspec(2, 3)
    ax = fig.add_subplot(gs[0, 0])
    _bars(ax, conds, ag, "letters_read_ok", scale=100, color=ps.SERIES[2], ylabel="letters read as target (%)")
    ax.set_title("(e) autowrite: letters read", loc="left")
    ax = fig.add_subplot(gs[0, 1])
    _bars(ax, conds, ag, "target_err_um", color=ps.SERIES[0], ylabel="distance to target (um)")
    ax.set_title("target error", loc="left")
    ax = fig.add_subplot(gs[0, 2])
    _bars(ax, conds, ag, "device_work_share", scale=100, color=ps.SERIES[1], ylabel="device share of positive work (%)")
    ax.set_title("who moved the pen", loc="left")
    paths = aw.get("paths_first_case", {})
    show = [c for c in ["relaxed_nose", "board_lead+nose", "sd_lead+nose"] if c in paths]
    rows = []
    for k, c in enumerate(show):
        ax = fig.add_subplot(gs[1, k])
        P = np.asarray(paths[c])
        if P.ndim == 2 and P.shape[1] >= 3:
            dn = P[:, 2] > 0.5
            x, y = P[:, 0], P[:, 1]                    # handwriting.metrics.decimate_path: mm
            xs = np.where(dn, x, np.nan)
            ys = np.where(dn, y, np.nan)
            ax.plot(xs, ys, color=ps.INK, lw=1.0)
            for i in range(0, len(P), 4):
                rows.append([c, P[i, 0], P[i, 1], int(dn[i])])
        ax.set_aspect("equal")
        ax.set_title(lab(c), loc="left", fontsize=9)
        ax.set_xlabel("mm")
    for c in conds:
        rows.append([c + " (aggregate)", _get(ag[c], "letters_read_ok"), _get(ag[c], "target_err_um"),
                     _get(ag[c], "pen_speed_mm_s")])
    p = _save(fig, out, "fig_autowrite", SIM_STAMP, "task (e): relaxed hand, the drive leads at gross scale")
    _csv(out / "fig_autowrite.csv", ["cond_or_path", "x_mm_or_letters_read", "y_mm_or_target_err_um",
                                     "pen_down_or_speed_mm_s"], rows)
    return p


def fig_tremor(tasks: Dict, out: Path) -> Optional[Path]:
    tr = tasks.get("tremor", {})
    byc = tr.get("by_cell", {})
    if not byc:
        return None
    cells = sorted(byc.keys(), key=lambda s: (float(s.split("Hz")[0]), s))
    conds = [c for c in ["nose_akf", "nose_oracle", "ball_damp", "ball_brake", "wheel_tremor_brake", "ball_damp+nose_akf",
                         "wheel_known_text"] if c in byc[cells[0]]]
    amps = sorted({c.split("_")[1] for c in cells})
    fig, axs = plt.subplots(1, len(amps) + 1, figsize=(5.2 * (len(amps) + 1), 4.4))
    axs = np.atleast_1d(axs)
    rows = []
    for j, a in enumerate(amps):
        ax = axs[j]
        cs = [c for c in cells if c.endswith(a)]
        f = [float(c.split("Hz")[0]) for c in cs]
        for i, cond in enumerate(conds):
            v = [_get(byc[c].get(cond, {}), "ratio") for c in cs]
            ax.plot(f, v, color=ps.SERIES[i % len(ps.SERIES)], label=lab(cond))
            ax.plot(f, v, **ps.marker_kw(ps.SERIES[i % len(ps.SERIES)]))
            for ff, vv, c in zip(f, v, cs):
                rows.append(["tremor", a, ff, cond, vv, _get(byc[c].get(cond, {}), "ink_err_um"),
                             _get(byc[c].get(cond, {}), "letters_read")])
        ax.axhline(1.0, color=ps.MUTED, lw=1, ls="-.")
        ax.set_xlabel("tremor frequency (Hz)")
        ax.set_ylabel("ink error / ink error with nothing on")
        ax.set_title(f"(d) tremor {a.replace('mm', ' mm')} at the hand", loc="left")
        if j == 0:
            ax.legend(fontsize=7)
    ax = axs[-1]
    tf = tr.get("tremor_free", {})
    nv = tf.get("naive", {})
    ad = tf.get("adapted", {})
    cs = [c for c in conds if c in nv and c not in ("nose_oracle",)] + (["none"] if "none" in nv else [])
    x = np.arange(len(cs))
    ax.bar(x - 0.2, [_get(nv.get(c, {}), "ink_err_um") for c in cs], 0.4, color=ps.SERIES[0], label="writer ignores the device")
    ax.bar(x + 0.2, [_get(ad.get(c, {}), "ink_err_um") for c in cs], 0.4, color=ps.SERIES[2],
           label="writer adapted to its drag (ASSUMPTION)")
    ax.set_xticks(x)
    ax.set_xticklabels([lab(c) for c in cs], rotation=30, ha="right", fontsize=7.5)
    ax.set_ylabel("ink error of tremor-free writing (um)")
    ax.set_title("What the device does to clean writing", loc="left")
    ax.legend(fontsize=7)
    for c in cs:
        rows.append(["tremor_free", "", 0.0, c, float("nan"), _get(nv.get(c, {}), "ink_err_um"), _get(ad.get(c, {}), "ink_err_um")])
    p = _save(fig, out, "fig_tremor", SIM_STAMP, "task (d): ET writers, HW1 tremor model")
    _csv(out / "fig_tremor.csv", ["part", "amp", "f0_Hz", "cond", "ratio_or_nan", "ink_err_um", "letters_read_or_adapted_err_um"],
         rows)
    return p


# ============================================================================== all
def make_all(design: Optional[Dict], tasks: Optional[Dict], rules: Optional[Dict], out: Path, quick: bool = False) -> List[str]:
    figs = []
    sfx = "_quick" if quick else ""
    o = Path(out)
    if design:
        for f in (fig_geometry, fig_capacity, fig_design_pareto):
            try:
                p = f(design, o)
            except KeyError as e:          # a design file from an older run
                print(f"  skip {f.__name__}: missing {e}")
                p = None
            if p:
                figs.append(str(p))
    if tasks:
        for f in (fig_practice, fig_feel, fig_loops_reversal, fig_autowrite, fig_tremor):
            p = f(tasks, o)
            if p:
                if sfx:
                    q = p.with_name(p.stem + sfx + p.suffix)
                    p.rename(q)
                    c = p.with_suffix(".csv")
                    if c.exists():
                        c.rename(c.with_name(c.stem + sfx + ".csv"))
                    p = q
                figs.append(str(p))
    return figs


def _cell(agg: Dict, cond: str, keys: List[str]) -> Dict:
    c = agg.get(cond, {})
    return {k: c.get(k) for k in keys if c.get(k) is not None} | {"n": c.get("n")}


def summary(design: Optional[Dict], tasks: Optional[Dict], rules: Optional[Dict]) -> Dict:
    """The numbers the report quotes, each block with its label."""
    s = {"labels": {"design": "CALC", "tasks": "SIM (test writers, frozen rules)"}}
    if rules:
        s["rules"] = {"sha256_16": rules.get("sha256_16"), "frozen_utc": rules.get("frozen_utc"),
                      "gains": rules.get("gains")}
    if design:
        g = design["geometry"]
        s["geometry"] = {"pods": g.get("pods"), "heel_1p0": {k: g["heel_1p0"][k] for k in
                                                             ("R_d_mm", "R_skid_mm", "spring_travel_mm", "roll_tolerance_deg")}}
        do = design.get("design_opt", {})
        for c in ("wheel", "ball"):
            b = do.get(f"best_{c}")
            if b:
                s[f"design_{c}"] = {"motor": b["motor"], "gear": b["snapped"]["chosen"]["gear"],
                                    "terms": b["snapped"]["chosen"]["terms"]}
        s["grad_check_max_rel_err"] = {c: v["max_rel_err"] for c, v in do.get("grad_check", {}).items()}
    if tasks:
        pr = tasks.get("practice", {}).get("aggregate", {})
        kp = ["target_err_um", "target_err_um_sd", "letters_read_ok", "words_app", "device_share", "F_rms_N", "F_p95_N",
              "felt_p95_N", "slide_share", "slip_events", "yields", "coverage", "P_drive_mean_W"]
        s["practice"] = {prof: {c: _cell(cells, c, kp) for c in cells} for prof, cells in pr.items()}
        rs = tasks.get("resisting", {}).get("aggregate", {})
        s["resisting"] = {c: _cell(rs, c, ["target_err_um", "letters_read_ok", "F_rms_N", "felt_rms_N", "felt_p95_N",
                                           "yields", "slide_share"]) for c in rs}
        lp = tasks.get("loops", {}).get("aggregate", {})
        s["loops"] = {h: {c: _cell(cells, c, ["loop_height_ratio_ink", "last_loop_ratio", "ink_to_template_rms_mm",
                                              "F_rms_N", "felt_rms_N", "slide_share"]) for c in cells} for h, cells in lp.items()}
        rv = tasks.get("reversal", {}).get("aggregate", {})
        s["reversal"] = {w: {c: _cell(cells, c, ["bowl_correct_side", "bowl_to_template_rms_mm", "F_max_N", "felt_p95_N",
                                                 "yields"]) for c in cells} for w, cells in rv.items()}
        aw = tasks.get("autowrite", {}).get("aggregate", {})
        s["autowrite"] = {c: _cell(aw, c, ["letters_read_ok", "words_app", "target_err_um", "device_work_share",
                                           "pen_speed_mm_s", "F_rms_N", "F_max_N", "slide_share", "P_drive_mean_W"])
                          for c in aw}
        tr = tasks.get("tremor", {})
        s["tremor"] = {"by_amp": {a: {c: _cell(cells, c, ["ratio", "ink_err_um", "letters_read", "words_app", "F_rms_N",
                                                          "felt_rms_N", "P_drive_mean_W"]) for c in cells}
                                  for a, cells in tr.get("by_amp", {}).items()},
                       "tremor_free": tr.get("tremor_free")}
    return s


# ============================================================================== markdown tables for the report
def _f(v, nd=2, scale=1.0, pct=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    v = float(v) * scale
    if pct:
        return f"{100.0 * v:.0f} %"
    return f"{v:.{nd}f}"


def _pm(cell, k, nd=0, scale=1.0, pct=False):
    m, s = cell.get(k), cell.get(k + "_sd")
    if m is None:
        return "-"
    if pct:
        return f"{100 * m:.0f} ± {100 * (s or 0):.0f} %"
    return f"{m * scale:.{nd}f} ± {(s or 0) * scale:.{nd}f}"


def markdown_tables(design: Optional[Dict], tasks: Optional[Dict]) -> str:
    L: List[str] = []
    if design:
        L.append("### T1. Traction the paper gives at preload 0.55 N (CALC)\n")
        L.append("| mu | mean over writers (N) | weakest 10 % (N) | writers with full load |")
        L.append("|---|---|---|---|")
        for c in design["capacity"]:
            if abs(c["P_N"] - 0.55) < 1e-9:
                L.append(f"| {c['mu']:g} | {_f(c['cap_mean_N'])} | {_f(c['cap_p10_N'])} | {_f(c['share_full'], pct=True)} |")
        L.append("\n### T2. The 2 mm wheel's tyre on paper (CALC; Hertz, Persson AMF-112, Mindlin)\n")
        L.append("| load (N) | contact radius (mm) | mean pressure (MPa) | rolling resistance coefficient | rolling drag (mN) | tangential stiffness (N/mm) |")
        L.append("|---|---|---|---|---|---|")
        for r in design["tyre"]:
            if abs(r["r_mm"] - 1.0) < 1e-9:
                L.append(f"| {r['N']:g} | {_f(r['a_mm'], 3)} | {_f(r['p_MPa'], 2)} | {_f(r['mu_rr'], 3)} | {_f(r['F_rr_mN'], 1)} | {_f(r['k_t_N_per_mm'], 2)} |")
        L.append("\n### T3. Candidates at the heel (CALC with catalogue parts; section 3 gives the verdicts)\n")
        L.append("| concept | force on the pen (N) | speed (m/s) | mass (g) | heel size | when off |")
        L.append("|---|---|---|---|---|---|")
        for r in design["concepts"]:
            if r["key"] == "others":
                continue
            L.append(f"| {r['name']} | {r['force_any_dir_N']} | {r['speed_m_s'][:40]} | {r['mass_g']} | {r['size']} | {r['off_feel'][:90]} |")
        do = design.get("design_opt", {})
        L.append("\n### T4. Optimised builds (CALC; torch autograd, gradients checked against finite differences)\n")
        L.append("| | steered + driven wheel | driven ball |")
        L.append("|---|---|---|")
        bw, bb = do.get("best_wheel"), do.get("best_ball")
        if bw and bb:
            tw, tb = bw["snapped"]["chosen"]["terms"], bb["snapped"]["chosen"]["terms"]
            rows = [("motor", bw["motor"], bb["motor"]), ("gear (snapped)", bw["snapped"]["chosen"]["gear"], bb["snapped"]["chosen"]["gear"]),
                    ("element radius (mm)", _f(tw["r_e_mm"]), _f(tb["r_e_mm"])), ("roller radius (mm)", "-", _f(tb["r_r_mm"])),
                    ("preload P (N)", _f(tw["P_N"]), _f(tb["P_N"])), ("motor force, continuous (N)", _f(tw["F_mot_N"]), _f(tb["F_mot_N"])),
                    ("no-load speed (m/s)", _f(tw["v_max_m_s"]), _f(tb["v_max_m_s"])),
                    ("usable force, mean writer, mu 0.6 (N)", _f(tw["F_use_mean_N"]), _f(tb["F_use_mean_N"])),
                    ("usable force, weakest 10 % (N)", _f(tw["F_use_p10_N"]), _f(tb["F_use_p10_N"])),
                    ("writers with full load", _f(tw["share_full"], pct=True), _f(tb["share_full"], pct=True)),
                    ("reflected mass (g)", _f(tw["m_r_g"], 1), _f(tb["m_r_g"], 1)),
                    ("back-drive force (mN)", _f(tw["F_bd_N"], 0, 1e3), _f(tb["F_bd_N"], 0, 1e3)),
                    ("internal scrub (mN)", _f(tw["scrub_N"], 0, 1e3), _f(tb["scrub_N"], 0, 1e3)),
                    ("rolling drag (mN)", _f(tw["F_rr_N"], 0, 1e3), _f(tb["F_rr_N"], 0, 1e3)),
                    ("copper loss at 0.15 N RMS (mW)", _f(tw["P_cu_W"], 0, 1e3), _f(tb["P_cu_W"], 0, 1e3)),
                    ("heel contact radius (mm)", _f(tw["R_d_mm"]), _f(tb["R_d_mm"]))]
            for a, b, c in rows:
                L.append(f"| {a} | {b} | {c} |")
            gc = do.get("grad_check", {})
            L.append(f"\nGradient check, largest relative error autograd vs central differences: wheel "
                     f"{gc.get('wheel', {}).get('max_rel_err', float('nan')):.1e}, ball {gc.get('ball', {}).get('max_rel_err', float('nan')):.1e} (CALC).")
    if tasks:
        pr = tasks.get("practice", {}).get("aggregate", {})
        n0 = None
        for prof, cells in pr.items():
            L.append(f"\n### T5-{prof}. (a) Guided tracing, {prof} learners (SIM; 6 test writers x 4 seeds; mean ± SD)\n")
            L.append("| condition | target error (um) | letters read | learner's error letters read as the target | words read (app) | force RMS (N) | force p95 (N) | felt change p95 (N) | true sliding | slip flags per run | coverage | drive power (mW) |")
            L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
            order = ["none", "nose_partial", "board_partial", "board_full", "ball_partial", "ball_full", "wheel_path",
                     "wheel_partial", "sd_path", "sd_full", "wheel_path+nose"]
            for c in [c for c in order if c in cells]:
                cl = cells[c]
                L.append(f"| {lab(c)} | {_pm(cl, 'target_err_um')} | {_f(cl.get('letters_read_ok'), pct=True)} | "
                         f"{_f(cl.get('error_letters_read_as_target'), pct=True)} | "
                         f"{_f(cl.get('words_app'), pct=True)} | {_f(cl.get('F_rms_N'))} | {_f(cl.get('F_p95_N'))} | "
                         f"{_f(cl.get('felt_p95_N'))} | {_f(cl.get('slide_share'), 3)} | {_f(cl.get('slip_events'), 1)} | "
                         f"{_f(cl.get('coverage'), pct=True)} | {_f(cl.get('P_drive_mean_W'), 0, 1e3)} |")
                n0 = cl.get("n")
        rs = tasks.get("resisting", {}).get("aggregate", {})
        if rs:
            L.append("\n### T6. A lightly resisting writer (SIM; upper-CI arm impedance; 6 writers x 2 seeds)\n")
            L.append("| condition | target error (um) | letters read | force RMS (N) | force p95 (N) | felt change RMS (N) | felt change p95 (N) | yields |")
            L.append("|---|---|---|---|---|---|---|---|")
            for c in ["none", "board_full", "ball_full", "wheel_path", "sd_path", "sd_full"]:
                if c in rs:
                    cl = rs[c]
                    L.append(f"| {lab(c)} | {_pm(cl, 'target_err_um')} | {_f(cl.get('letters_read_ok'), pct=True)} | {_f(cl.get('F_rms_N'))} | "
                             f"{_f(cl.get('F_p95_N'))} | {_f(cl.get('felt_rms_N'))} | {_f(cl.get('felt_p95_N'))} | {_f(cl.get('yields'), 1)} |")
        lp = tasks.get("loops", {}).get("aggregate", {})
        if lp:
            L.append("\n### T7. (b) 'Write big' loops: the writer's loops shrink from 0.8 to 0.6 of 10 mm (SIM; 4 seeds)\n")
            L.append("| hand | condition | loop height / target | last loop / target | ink to template RMS (mm) | force RMS (N) | felt change RMS (N) |")
            L.append("|---|---|---|---|---|---|---|")
            for h, cells in lp.items():
                for c in ["none", "board_full", "ball_full", "wheel_path", "sd_path", "sd_full"]:
                    if c in cells:
                        cl = cells[c]
                        L.append(f"| {h.replace('_', ' ')} | {lab(c)} | {_pm(cl, 'loop_height_ratio_ink', 2)} | {_f(cl.get('last_loop_ratio'))} | "
                                 f"{_f(cl.get('ink_to_template_rms_mm'))} | {_f(cl.get('F_rms_N'))} | {_f(cl.get('felt_rms_N'))} |")
        rv = tasks.get("reversal", {}).get("aggregate", {})
        if rv:
            L.append("\n### T8. (c) Reversed letter: template 'd' (SIM; 4 seeds)\n")
            L.append("| writer | condition | bowl ink on the 'd' side | template bowl covered | bowl ink to template RMS (mm) | force max (N) | felt change p95 (N) |")
            L.append("|---|---|---|---|---|---|---|")
            for w, cells in rv.items():
                for c, cl in cells.items():
                    L.append(f"| {w} | {lab(c)} | {_f(cl.get('bowl_correct_side'), pct=True)} | {_f(cl.get('bowl_coverage'), pct=True)} | "
                             f"{_f(cl.get('bowl_to_template_rms_mm'))} | {_f(cl.get('F_max_N'))} | {_f(cl.get('felt_p95_N'))} |")
        aw = tasks.get("autowrite", {}).get("aggregate", {})
        if aw:
            L.append("\n### T9. (e) Autowrite: the drive leads a relaxed hand along the practice sentence (SIM; 6 writers x 2 seeds)\n")
            L.append("| condition | letters read | words read (app) | target error (um) | device share of the work | pen speed (mm/s) | force RMS (N) | force max (N) | drive power (mW) |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for c in ["writer_alone", "nose_nogate", "relaxed_nose", "board_lead+nose", "ball_lead", "ball_lead+nose", "sd_lead", "sd_lead+nose"]:
                if c in aw:
                    cl = aw[c]
                    L.append(f"| {lab(c)} | {_pm(cl, 'letters_read_ok', pct=True)} | {_f(cl.get('words_app'), pct=True)} | {_pm(cl, 'target_err_um')} | "
                             f"{_f(cl.get('device_work_share'), pct=True)} | {_f(cl.get('pen_speed_mm_s'), 1)} | {_f(cl.get('F_rms_N'))} | "
                             f"{_f(cl.get('F_max_N'))} | {_f(cl.get('P_drive_mean_W'), 0, 1e3)} |")
        tr = tasks.get("tremor", {})
        ba = tr.get("by_amp", {})
        if ba:
            L.append("\n### T10. (d) Tremor at 4-10 Hz: ink error relative to Rev H with nothing on (SIM; 6 ET writers, 1 seed)\n")
            amps = sorted(ba.keys())
            L.append("| condition | " + " | ".join(f"ink error ratio, {a}" for a in amps) + " | letters read, " + amps[0] +
                     " | force RMS (N) | felt change RMS (N) | tremor-free distortion (um) | same, writer adapted (um) |")
            L.append("|---|" + "---|" * (len(amps) + 5))
            tf = tr.get("tremor_free", {})
            for c in ["none", "nose_akf", "nose_oracle", "ball_damp", "ball_brake", "wheel_tremor_brake", "ball_damp+nose_akf",
                      "wheel_known_text"]:
                if c not in ba[amps[0]]:
                    continue
                vals = [_pm(ba[a].get(c, {}), "ratio", 2) for a in amps]
                cl = ba[amps[0]][c]
                L.append(f"| {lab(c)} | " + " | ".join(vals) + f" | {_f(cl.get('letters_read'), pct=True)} | {_f(cl.get('F_rms_N'))} | "
                         f"{_f(cl.get('felt_rms_N'))} | {_f(tf.get('naive', {}).get(c, {}).get('ink_err_um'), 0)} | "
                         f"{_f(tf.get('adapted', {}).get(c, {}).get('ink_err_um'), 0)} |")
            bc = tr.get("by_cell", {})
            if bc:
                L.append("\nBy frequency (ratio, 1 mm):\n")
                cells = sorted([k for k in bc if k.endswith("_1mm")], key=lambda s: float(s.split("Hz")[0]))
                L.append("| condition | " + " | ".join(k.replace("_", " ") for k in cells) + " |")
                L.append("|---|" + "---|" * len(cells))
                for c in ["nose_akf", "ball_damp", "ball_brake", "wheel_tremor_brake", "ball_damp+nose_akf", "wheel_known_text"]:
                    if c in bc[cells[0]]:
                        L.append(f"| {lab(c)} | " + " | ".join(_f(bc[k].get(c, {}).get("ratio")) for k in cells) + " |")
                adapted = [k for k in bc[cells[0]] if "(adapted" in k] if cells else []
                if "8Hz_1mm" in bc:
                    ad = {k: v for k, v in bc["8Hz_1mm"].items() if "(adapted" in k}
                    if ad:
                        L.append("\nWriter adapted to the device's drag (ASSUMPTION sensitivity), 8 Hz 1 mm, ratio: " +
                                 "; ".join(f"{k.replace(' (adapted writer)', '')} {_f(v.get('ratio'))}" for k, v in ad.items()))
    return "\n".join(L) + "\n"
