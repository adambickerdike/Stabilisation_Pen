"""Figures of study B, each with a CSV twin holding the plotted numbers (results/bnib/fig_*.png + .csv).
Labels on every figure: CALC / SIM / LIT as in the data; PROPOSED DESIGN for the nib."""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, List, Sequence

import numpy as np

from . import RESULTS

D2R = math.pi / 180.0
OUT_DIR = RESULTS          # report.write_all points this at bnib/build/quick in --quick mode


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _csv(path: str, header: Sequence[str], rows: List[Sequence]):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([f"{v:.6g}" if isinstance(v, float) else v for v in r])


def _out(name):
    os.makedirs(OUT_DIR, exist_ok=True)
    return os.path.join(str(OUT_DIR), f"{name}.png"), os.path.join(str(OUT_DIR), f"{name}.csv")


# ------------------------------------------------------------------------------------------------ the balance principle
def balance_principle(theta_deg: float = 50.0, F_s: float = 0.15) -> str:
    """Two labelled sketches (CALC numbers at 50 deg): (a) the spring pushes the refill along the pen from the moving
    carrier: the paper's push has a part across the pen that the nib's coils must hold; (b) the spring pushes a face
    parallel to the paper on the handle: the face's push and the paper's push are parallel and opposite, so the refill
    needs no sideways force from the nib."""
    plt = _plt()
    from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle
    th = theta_deg * D2R
    N = F_s / math.sin(th)
    side = F_s / math.tan(th)
    fig, axs = plt.subplots(1, 2, figsize=(15.0, 6.4))
    a = np.array([math.cos(th), math.sin(th)])            # pen axis in the (h, n) plane
    t1 = np.array([math.sin(th), -math.cos(th)])          # across the pen, toward the paper side
    Lr = 6.0
    P0 = np.array([0.0, 0.0])
    P1 = P0 + Lr * a

    def arrow(ax, p, q, col, lw=2.2):
        ax.add_patch(FancyArrowPatch(tuple(p), tuple(q), arrowstyle="-|>", mutation_scale=16, color=col, lw=lw))
    for k, ax in enumerate(axs):
        ax.axhline(0, color="k", lw=1.2)
        ax.fill_between([-3.2, 8.2], -0.7, 0, color="0.93")
        ax.text(6.6, -0.5, "paper", fontsize=10)
        ax.plot([P0[0], P1[0]], [P0[1], P1[1]], color="0.25", lw=8, solid_capstyle="round", alpha=0.9)
        pr = P0 + 4.6 * a + 0.42 * t1
        ax.text(pr[0], pr[1], "refill", rotation=theta_deg, fontsize=10, color="0.25", ha="center", va="center")
        ax.plot(*P0, "o", color="k", ms=8)
        ax.text(0.15, -0.45, "ball", fontsize=9)
        c0, c1 = P0 + 0.8 * a, P0 + 3.2 * a
        w = 0.30
        ax.add_patch(Polygon([c0 + w * t1, c1 + w * t1, c1 - w * t1, c0 - w * t1], closed=True, color="C1", alpha=0.35))
        cl = P0 + 2.0 * a + 1.05 * t1
        ax.text(cl[0], cl[1], "nib carrier\n(moves sideways)", fontsize=9, color="C1", ha="left", va="center")
        arrow(ax, P0, P0 + np.array([0.0, 2.4]), "C2")
        ax.text(-0.18, 1.2, f"paper pushes\nthe ball up\nN = {N:.3f} N", color="C2", fontsize=9, ha="right", va="center")
        if k == 0:
            arrow(ax, P1 + 1.3 * a, P1 + 0.08 * a, "C0")
            q = P1 + 1.35 * a
            ax.text(q[0] + 0.1, q[1], f"ink spring pushes along\nthe pen: F_s = {F_s:.2f} N\n(reacts on the carrier)",
                    fontsize=9, color="C0", ha="left", va="center")
            mid = P0 + 2.0 * a
            tip = mid - 2.3 * t1
            arrow(ax, mid, tip, "C3", lw=2.8)
            ax.text(tip[0] - 0.1, tip[1] + 0.35, f"the coils must hold\nF_s cot(theta) = {side:.3f} N\nwhile the ball is down",
                    color="C3", fontsize=10, fontweight="bold", ha="center", va="bottom")
            ax.set_title(f"(a) no balance: {side:.3f} N across the pen at {theta_deg:.0f} deg\n(Rev J C1S: x 6.65 lever -> "
                         f"1.63 W at 50 deg, CALC)", fontsize=11)
        else:
            fc = P1 + np.array([0.0, 0.22])
            ax.add_patch(Rectangle((fc[0] - 1.1, fc[1]), 2.2, 0.2, color="C0", alpha=0.85))
            ax.text(fc[0] + 1.25, fc[1] + 0.55, "counter-face on the handle\n(kept parallel to the paper)", fontsize=9,
                    color="C0", ha="left", va="center")
            arrow(ax, fc + np.array([0.0, 1.5]), fc + np.array([0.0, 0.24]), "C0")
            ax.text(fc[0] - 0.15, fc[1] + 1.0, f"spring pushes\nthe face down:\nF_n = N = {N:.3f} N", fontsize=9, color="C0",
                    ha="right", va="center")
            ax.plot([fc[0] - 1.1, fc[0] + 1.1], [fc[1] - 0.25, fc[1] - 0.25], "k:", lw=1.0)
            ax.text(fc[0] + 1.25, fc[1] - 0.75, "dotted: the follower stop just below the face;\nthe face stops there when the "
                    "ball lifts,\nso nothing is held in the air", fontsize=8, ha="left", va="center")
            ax.text(3.0, 2.45, "the two pushes are parallel and opposite:\nnothing across the pen for the coils to hold\n"
                    "(what is left: about 5 % from orientation errors)", color="C3", fontsize=10, fontweight="bold",
                    ha="left", va="center")
            ax.set_title("(b) counter-face: ~0 across the pen at any tilt; it scales with the actual spring force\n"
                         "(when the nib moves, the refill's end slides along the face)", fontsize=11)
        ax.set_xlim(-3.2, 8.4)
        ax.set_ylim(-0.8, 7.4)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("How the balance works (CALC statics at 50 deg; PROPOSED DESIGN; not to scale)", fontsize=12)
    png, cs = _out("fig_balance_principle")
    fig.savefig(png, dpi=140, bbox_inches="tight")
    plt.close(fig)
    rows = []
    for tdeg in (35.0, 50.0, 60.0, 75.0):
        t = tdeg * D2R
        rows.append([tdeg, F_s, F_s / math.sin(t), F_s / math.tan(t), 0.0])
    _csv(cs, ["theta_deg", "F_s_N", "N_paper_N", "side_load_no_balance_N", "side_load_counterface_ideal_N"], rows)
    return png


# ------------------------------------------------------------------------------------------------ C1S reconciliation
def c1s_reconciliation(rec: Dict) -> str:
    plt = _plt()
    rows = rec["rows"]
    th = [r["theta_deg"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.semilogy(th, [r["P_static_review_W"] for r in rows], "o-", label="static side load only (review s4, CALC)")
    ax.semilogy(th, [r["P_mean_W"] for r in rows], "s-", label="all loads, duty 1 mm rms 8 Hz (this study, CALC)")
    nd = rec["duty_model"]
    ax.axhline(nd["P_tremor_W"], color="C3", ls="--", label=f"study N's duty model {nd['P_tremor_W']:.2f} W (CALC)")
    sj = rec.get("sim2j", {}).get("rows", {})
    if sj:
        vals = [v.get("P_nose_W") for v in sj.values() if v.get("P_nose_W")]
        if vals:
            ax.axhspan(min(vals), max(vals), color="C2", alpha=0.15, label="sim2j runs at 50 deg (SIM)")
    ax.set_xlabel("pen tilt (deg)")
    ax.set_ylabel("C1S coil power (W)")
    ax.set_title("Rev J C1S nose: the static term the duty model missed", fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)
    png, cs = _out("fig_c1s_reconciliation")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["theta_deg", "P_static_review_W", "P_mean_all_loads_W", "static_side_load_N", "gravity_N", "inertia_rms_N"],
         [[r["theta_deg"], r["P_static_review_W"], r["P_mean_W"], r["static_side_load_N"], r["gravity_N"], r["inertia_rms_N"]]
          for r in rows])
    return png


# ------------------------------------------------------------------------------------------------ candidates
def power_vs_tilt(cands: Dict, grip: str = "pen24") -> str:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    rows = []
    for k, r in cands.items():
        if not k.startswith(grip + "|"):
            continue
        th = sorted(r["P_mean_W_by_theta"].keys(), key=float)
        P = [r["P_mean_W_by_theta"][t] for t in th]
        ax.semilogy([float(t) for t in th], P, "o-", label=k.split("|")[1])
        for t, p in zip(th, P):
            rows.append([k.split("|")[1], float(t), p])
    ax.set_xlabel("pen tilt (deg)")
    ax.set_ylabel("mean nib power (W), duty A: 0.2 mm rms, 8 Hz, 70 % contact")
    ax.set_title(f"Candidates, {grip} (CALC; Km at the image-method upper bound)", fontsize=10)
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, which="both", alpha=0.3)
    png, cs = _out(f"fig_power_vs_tilt_{grip}")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["candidate", "theta_deg", "P_mean_W"], rows)
    return png


def balance_quality(bq: Dict) -> str:
    plt = _plt()
    names = list(bq.keys())
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    x = np.arange(len(names))
    mc = [bq[n]["residual_contact_mean_N"] for n in names]
    p95 = [bq[n]["residual_contact_p95_N"] for n in names]
    pu = [bq[n]["residual_penup_mean_N"] for n in names]
    ax.bar(x - 0.25, mc, 0.25, label="in contact, mean")
    ax.bar(x, p95, 0.25, label="in contact, 95th percentile")
    ax.bar(x + 0.25, pu, 0.25, label="pen up, mean")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, fontsize=8)
    ax.set_ylabel("static load left on the nib (N)")
    ax.set_title("Balance quality over tilt 35-75 deg, roll, inks, papers, F_s +-20 %, sensing errors (CALC, Monte Carlo)",
                 fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    png, cs = _out("fig_balance_quality")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["mechanism", "residual_contact_mean_N", "residual_contact_p95_N", "residual_penup_mean_N", "unbalanced_mean_N",
              "friction_fluct_rms_N"],
         [[n, bq[n]["residual_contact_mean_N"], bq[n]["residual_contact_p95_N"], bq[n]["residual_penup_mean_N"],
           bq[n]["unbalanced_mean_N"], bq[n]["friction_fluct_rms_N"]] for n in names])
    return png


def pareto(opt: Dict) -> List[str]:
    plt = _plt()
    out = []
    for grip, fr in opt["fronts"].items():
        pts = []
        for pr in list(opt["problems"].values()):
            if pr["grip"] == grip:
                pts += [dict(p, family=pr["family"]) for p in pr["points"] if p.get("feasible_eps")]
        pts += [dict(p, family="piezo") for p in opt["piezo"].get(grip, {}).get("points", []) if p.get("feasible_eps")]
        if not pts:
            continue
        fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
        keys = sorted({p["key"] for p in pts})
        rows = []
        for i, k in enumerate(keys):
            P = [p for p in pts if p["key"] == k]
            axs[0].scatter([p["travel_mm"] for p in P], [p["P_cont_W"] * 1e3 for p in P], s=6, alpha=0.4, label=k, color=f"C{i}")
            axs[1].scatter([p["mass_g"] for p in P], [p["P_cont_W"] * 1e3 for p in P], s=6, alpha=0.4, color=f"C{i}")
            axs[2].scatter([p["m_eff_g"] for p in P], [(p.get("P_peak_W") or np.nan) for p in P], s=6, alpha=0.4, color=f"C{i}")
            for p in P:
                rows.append([k, p["family"], p["travel_mm"], p["P_cont_W"], p.get("P_peak_W"), p["mass_g"], p["m_eff_g"],
                             p["od_mm"], p["T_skin_C"], p.get("hall_noise_um"), p.get("com_mm")])
        f1 = fr["P_vs_travel"]
        axs[0].plot([p["travel_mm"] for p in f1], [p["P_cont_W"] * 1e3 for p in f1], "k-", lw=1.2, label="front")
        axs[0].set_xlabel("usable travel under load at Km x 0.7 (mm)")
        axs[0].set_ylabel("continuous power (mW), duty A, Km x 0.85")
        axs[0].set_yscale("log")
        axs[1].set_xlabel("pen mass (g)")
        axs[1].set_yscale("log")
        axs[2].set_xlabel("tip-equivalent moving mass (g)")
        axs[2].set_ylabel("peak power at 12 Hz full travel (W)")
        axs[2].set_yscale("log")
        axs[0].legend(fontsize=7)
        for ax in axs:
            ax.grid(True, which="both", alpha=0.3)
        fig.suptitle(f"Feasible designs and fronts, {grip} (CALC; every point meets bore, fatigue >= 1.5, bandwidth >= 40 Hz, "
                     f"skin <= 41 degC)", fontsize=10)
        png, cs = _out(f"fig_pareto_{grip}")
        fig.tight_layout()
        fig.savefig(png, dpi=140)
        plt.close(fig)
        _csv(cs, ["candidate", "family", "travel_mm", "P_cont_W", "P_peak_W", "mass_g", "m_eff_g", "od_mm", "T_skin_C",
                  "hall_noise_um", "com_mm"], rows)
        out.append(png)
    return out


def ink_force(sens: Dict) -> str:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    rows = []
    for k, lab in (("c_counterface", "counter-face"), ("f_translation", "same nib, no balance")):
        R = sens[k]
        ax.loglog([r["F_s_N"] for r in R], [r["P_cont_W"] * 1e3 for r in R], "o-", label=lab)
        for r in R:
            rows.append([k, r["F_s_N"], r["P_cont_W"], r["P_35deg_W"], r["travel_under_load_mm"]])
    for F, lab in ((0.15, "design 0.15 N (ASSUMPTION)"), (0.686, "lowest MFR test load found (CON-97)"),
                   (1.5, "ISO 12757-1 test load (CON-21)")):
        ax.axvline(F, color="0.5", ls=":", lw=1)
        ax.text(F * 1.03, ax.get_ylim()[0] * 1.5 if ax.get_ylim()[0] > 0 else 1, lab, rotation=90, fontsize=7, va="bottom")
    ax.set_xlabel("refill spring force F_s along the pen (N)")
    ax.set_ylabel("continuous nib power (mW), 24 mm, duty A")
    ax.set_title("If gate G1 finds a higher minimum ink force (CALC)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    png, cs = _out("fig_ink_force_sensitivity")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["candidate", "F_s_N", "P_cont_W", "P_35deg_W", "travel_under_load_mm"], rows)
    return png


def thermal(traces: Dict) -> str:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    rows = []
    for i, (k, tr) in enumerate(traces.items()):
        if not tr:
            continue
        t = np.array(tr["t_s"]) / 60
        ax.plot(t, tr["T_coil"], "-", color=f"C{i}", label=f"{k}: coil")
        ax.plot(t, tr["T_skin"], "--", color=f"C{i}", label=f"{k}: skin")
        for a, b, c in zip(tr["t_s"], tr["T_coil"], tr["T_skin"]):
            rows.append([k, a, b, c])
    ax.axhline(41, color="k", ls=":", lw=1)
    ax.text(0.5, 41.3, "skin target 41 degC (AMF-34)", fontsize=7)
    ax.set_xlabel("minutes of writing at 35 deg (the largest static load), 30 degC room")
    ax.set_ylabel("temperature (degC)")
    ax.set_title("Two-node thermal model with the governor (CALC)", fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    png, cs = _out("fig_thermal")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["design", "t_s", "T_coil_C", "T_skin_C"], rows)
    return png


def sim_cards(sim: Dict) -> str:
    plt = _plt()
    cards = sim.get("cards", {})
    if not cards:
        return ""
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8))
    rows = []
    names = list(cards.keys())
    cells = sorted({c for n in names for c in cards[n]["by_cell"].keys()})
    x = np.arange(len(cells))
    wbar = 0.8 / max(len(names), 1)
    for i, n in enumerate(names):
        bc = cards[n]["by_cell"]
        r = [bc.get(c, {}).get("ratio_mean", np.nan) for c in cells]
        wn = [bc.get(c, {}).get("words_nib", np.nan) * 10 for c in cells]
        wo = [bc.get(c, {}).get("words_off", np.nan) * 10 for c in cells]
        axs[0].bar(x + (i - (len(names) - 1) / 2) * wbar, r, wbar, label=f"{n}: {cards[n]['title']}")
        axs[1].bar(x + (i - (len(names) - 1) / 2) * wbar, wn, wbar, label=f"{n} nib on")
        axs[1].scatter(x + (i - (len(names) - 1) / 2) * wbar, wo, color="k", s=10, zorder=3)
        for c, a, b, d in zip(cells, r, wn, wo):
            rows.append([n, c, a, b, d])
    axs[0].axhline(1.0, color="k", lw=0.8)
    axs[0].set_ylabel("tremor left at the tip (ink error nib on / off)")
    axs[1].set_ylabel("readable words out of 10 (bars nib on, dots off)")
    for ax in axs:
        ax.set_xticks(x)
        ax.set_xticklabels(cells, rotation=30, fontsize=7)
        ax.grid(True, axis="y", alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.suptitle("SIMULATION (sim2; synthetic writers 0-5, synthetic ET/PD tremor, DeltaPen-calibrated page sensor)", fontsize=10)
    png, cs = _out("fig_sim_cards")
    fig.tight_layout()
    fig.savefig(png, dpi=140)
    plt.close(fig)
    _csv(cs, ["design", "cell", "ink_ratio_mean", "words_per10_nib", "words_per10_off"], rows)
    return png
