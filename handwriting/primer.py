"""Task 1: primer figures - how a pen is held, how handwriting moves, where tremor enters, what a pen can and cannot do.

Every figure is stamped with its evidence status and has a CSV twin with the plotted numbers.  Drawings of the hand are
schematic; positions of the Rev H parts come from results/revH/layout.json (PROPOSED DESIGN, every dimension an
ASSUMPTION until built).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import REPO_ROOT, RESULTS_DIR, ensure_paths
from . import params as PR
from . import plant as PL
from . import writers as W

ensure_paths()
from stabpen import plotstyle  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

C = plotstyle.SERIES
INK, INK2, MUTED, GRID = plotstyle.INK, plotstyle.INK2, plotstyle.MUTED, plotstyle.GRID


def write_csv(path: Path, header: List[str], rows: List[List]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _layout() -> Dict:
    for name in ("layout.json", "layout_provisional.json"):
        p = REPO_ROOT / "results" / "revH" / name
        if p.exists():
            d = json.loads(p.read_text())
            d["_file"] = str(p.relative_to(REPO_ROOT))
            return d
    raise FileNotFoundError("results/revH/layout.json")


# ------------------------------------------------------------------ 1. grasp and Rev H parts
def fig_grasp(out: Path) -> None:
    L = _layout()
    th = math.radians(L.get("tilt_deg", 50.0))
    ax_dir = np.array([-math.cos(th), math.sin(th)])        # from the tip (at the origin) up and back toward the writer
    nrm = np.array([math.sin(th), math.cos(th)])            # radial direction: + = upper side (away from the paper)

    def pt(z, r):
        return z * ax_dir + r * nrm

    def surface_r(z):
        for c in L["components"]:
            if c["id"] in ("front_sleeve", "shell", "skid_ring") and c["z0"] <= z <= c["z1"]:
                d0, d1 = c.get("d0", 22.0), c.get("d1", 22.0)
                return 0.5 * (d0 + (d1 - d0) * (z - c["z0"]) / max(c["z1"] - c["z0"], 1e-9))
        return 11.0

    plotstyle.apply()
    fig = plt.figure(figsize=(13.0, 7.4))
    fig.text(0.01, 0.975, "How the pen is held (dynamic tripod) and where Rev H's parts sit", fontsize=12, color=INK,
             va="top", fontweight="bold")
    ax = fig.add_axes([0.00, 0.04, 0.62, 0.90])
    ax2 = fig.add_axes([0.63, 0.47, 0.36, 0.44])
    ax3 = fig.add_axes([0.63, 0.05, 0.36, 0.38])
    rows = []
    colours = {"handle": "#d9d6cc", "nose": C[0], "sensor": C[2], "actuator": C[1], "cell": "#bdb9ab"}
    for c in L["components"]:
        z0, z1 = c["z0"], c["z1"]
        if c["shape"] in ("cylinder", "tube", "cone"):
            r0 = c.get("d0", 0) / 2
            r1 = c.get("d1", c.get("d0", 0)) / 2
            poly = [pt(z0, -r0), pt(z1, -r1), pt(z1, r1), pt(z0, r0)]
        else:
            sx, sy, _ = c.get("size", [2, 2, 2])
            off = (c.get("offset") or [0, 0])[0]
            poly = [pt(z0, off - sx / 2), pt(z1, off - sx / 2), pt(z1, off + sx / 2), pt(z0, off + sx / 2)]
        cid = c["id"]
        if c.get("moves_with") == "nose":
            col, alpha, zo = colours["nose"], 0.55, 3
        elif cid in ("imu", "hall3d", "optical", "pcb"):
            col, alpha, zo = colours["sensor"], 0.9, 4
        elif cid.startswith("coil") or cid == "back_ring":
            col, alpha, zo = colours["actuator"], 0.6, 3
        elif cid in ("battery",):
            col, alpha, zo = colours["cell"], 0.9, 2
        elif cid == "lra":
            col, alpha, zo = C[4], 0.9, 4
        else:
            col, alpha, zo = colours["handle"], 0.55 if cid != "shell" else 0.35, 1
        ax.add_patch(Polygon(poly, closed=True, facecolor=col, edgecolor=INK2, lw=0.6, alpha=alpha, zorder=zo))
        rows.append([cid, c.get("moves_with", ""), z0, z1, c.get("d0", ""), c.get("d1", ""), c.get("function", "")[:90]])
    ax.plot([-150, 30], [0, 0], color=INK, lw=1.2)
    ax.fill_between([-150, 30], -4, 0, color="#f1efe8", zorder=0)
    ax.text(-148, -3.2, "paper", fontsize=8.5, color=INK2)
    p0 = pt(0, 0)
    ax.add_patch(FancyArrowPatch((p0[0] - 3, 1.0), (p0[0] + 3, 1.0), arrowstyle="<->", mutation_scale=9, color=C[0], lw=1.8, zorder=8))
    hand = L.get("hand", {"finger_pads_z": [26, 32, 38], "web_z": 92})
    fz = hand["finger_pads_z"]
    # index pad on the upper side, middle finger under the barrel, thumb on the far side (dashed)
    pads = [(fz[1], +1, "index-finger pad (top)", (22, -4), "-"), (fz[0], -1, "middle finger\n(barrel rests on its side)", (-82, 0), "-"),
            (fz[2], +1, "thumb pad (far side)", (22, 6), "--")]
    for z, sd, nm, dxy, ls in pads:
        rr = surface_r(z) + 3.2
        q = pt(z, sd * rr)
        ax.add_patch(Circle(q, 3.4, facecolor="#f3c9a8", edgecolor="#a86e4b", lw=0.9, ls=ls, alpha=0.95, zorder=7))
        ax.annotate(nm, q, q + np.array(dxy), fontsize=8.5, color=INK, va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    qw = pt(hand["web_z"], -(surface_r(hand["web_z"]) + 4.0))
    ax.add_patch(Circle(qw, 5.0, facecolor="#f3c9a8", edgecolor="#a86e4b", lw=0.9, alpha=0.85, zorder=7))
    ax.annotate("barrel lies in the\nthumb-index web", qw, qw + np.array([-48, -2]), fontsize=8.5, color=INK, va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    pz = L.get("pivot_z", 45.0)
    pp = pt(pz, 0)
    ax.add_patch(Circle(pp, 1.6, facecolor="white", edgecolor=INK, lw=1.2, zorder=9))
    ax.annotate("flexure pivot: the nose\n(blue) tilts about here", pp, pp + np.array([34, -16]), fontsize=8.5, color=INK2,
                va="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.annotate("tip moves up to \u00b13 mm\nagainst the handle", p0 + np.array([3.5, 1.0]), p0 + np.array([12, 9]), fontsize=8.5,
                color=C[0], va="center", arrowprops=dict(arrowstyle="-", color=C[0], lw=0.8))
    lab = {"skid_ring": ("skid ring on the sleeve\ncarries the writing force", (-58, -7), -1),
           "coil_x+": ("voice coils and magnets\nmove the nose", (30, -2), +1),
           "imu": ("motion sensor (IMU)", (30, 2), +1), "battery": ("battery", (30, 0), +1),
           "lra": ("vibration motor (cues)", (30, 0), +1), "optical": ("paper-tracking sensor", (-78, 20), -1)}
    for cid, (txt, dxy, sd) in lab.items():
        c = next((c for c in L["components"] if c["id"] == cid), None)
        if c is None:
            continue
        zc = 0.5 * (c["z0"] + c["z1"])
        q = pt(zc, sd * surface_r(zc))
        ax.annotate(txt, q, q + np.array(dxy), fontsize=8.5, color=INK2, va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_aspect("equal")
    ax.set_xlim(-175, 75)
    ax.set_ylim(-6, 145)
    ax.axis("off")
    ax.plot([-170, -150], [138, 138], color=INK, lw=2)
    ax.text(-160, 140.5, "20 mm", ha="center", fontsize=8, color=INK2)
    ax.text(-170, 131, "side view, true proportions", fontsize=8.5, color=INK2)
    ax2.add_patch(Circle((0, 0), 11, facecolor=colours["handle"], edgecolor=INK2, lw=1))
    ax2.add_patch(Circle((0, 0), 3.5, facecolor=colours["nose"], edgecolor=INK2, lw=0.8, alpha=0.6))
    for ang, nm in ((150, "thumb pad"), (40, "index pad"), (-100, "middle finger\n(side of the last joint)")):
        a = math.radians(ang)
        ax2.add_patch(Circle((14.5 * math.cos(a), 14.5 * math.sin(a)), 4.0, facecolor="#f3c9a8", edgecolor="#a86e4b", lw=0.8))
        ax2.text(24 * math.cos(a), 23 * math.sin(a), nm, ha="center", va="center", fontsize=8.5, color=INK)
    ax2.text(0, -1.0, "nose", ha="center", va="center", fontsize=7, color="white")
    ax2.set_aspect("equal")
    ax2.set_xlim(-34, 34)
    ax2.set_ylim(-31, 29)
    ax2.axis("off")
    ax2.set_title("Cross-section at the finger pads (\u00d822 mm sleeve)", fontsize=9.5, loc="left")
    ax3.axis("off")
    txt = ("Dynamic tripod: the pads of the thumb and index finger pinch the\n"
           "barrel, it rests on the side of the middle finger and lies in the\n"
           "thumb-index web; the fingers move the pen. Grasp type (tripod or\n"
           "quadrupod, dynamic or lateral) did not change speed or legibility\n"
           "in 120 children (CON-33).\n\n"
           "Rev H: the fingers hold a fixed sleeve; only the nose inside it\n"
           "tilts on a flexure, so the ink can move \u00b13 mm while the fingers\n"
           "do not feel the tip move. Part positions from results/revH/\n"
           "layout.json (PROPOSED DESIGN); finger-pad and web positions are\n"
           "ASSUMPTIONS.")
    ax3.text(0, 1, txt, va="top", fontsize=8.8, color=INK2)
    plotstyle.stamp(fig, "PROPOSED DESIGN + LITERATURE (schematic)", "CON-33; layout: " + L["_file"])
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["component", "moves_with", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "function"], rows)


# ------------------------------------------------------------------ 2. which joints make which parts of the writing
def _components(written, fc_sweep=0.8):
    from scipy.signal import butter, sosfiltfilt
    it = written.intended
    dt = float(it.t[1] - it.t[0])
    step = max(1, int(round(0.002 / dt)))
    t = it.t[::step]
    xy = it.xy[::step]
    fs = 1.0 / (t[1] - t[0])
    sweep = sosfiltfilt(butter(2, fc_sweep, fs=fs, output="sos"), xy, axis=0)
    osc = xy - sweep
    return t, xy, sweep, osc, it.pen_down[::step]


def fig_joints(out: Path) -> None:
    wr = W.writer(0).write(W.ET_SENTENCE, dt=W.SIM_DT, seed=2000)
    t, xy, sweep, osc, down = _components(wr)
    st = wr.style
    # finger (up-down, along the slant) and wrist (sideways) axes of the letter oscillation
    sl = math.radians(st.slant_deg)
    u_f = np.array([math.sin(sl), math.cos(sl)])         # along the downstroke direction (fingers)
    u_w = np.array([math.cos(sl), -math.sin(sl)])        # across it (wrist)
    f_comp = osc @ u_f
    w_comp = osc @ u_w
    plotstyle.apply()
    fig = plt.figure(figsize=(12.5, 7.2))
    ax0 = fig.add_axes([0.05, 0.60, 0.55, 0.33])
    ax1 = fig.add_axes([0.05, 0.10, 0.55, 0.40])
    ax2 = fig.add_axes([0.64, 0.10, 0.34, 0.83])
    m = down
    xs, ys = xy[:, 0] * 1e3, xy[:, 1] * 1e3
    seg = np.where(m, ys, np.nan)
    ax0.plot(xs, seg, color=INK, lw=1.4)
    ax0.plot(sweep[:, 0] * 1e3, sweep[:, 1] * 1e3 - 4.0, color=C[1], lw=2.0)
    ax0.annotate("arm (shoulder, elbow, forearm):\nslow sweep along the line", (sweep[len(t) // 2, 0] * 1e3, sweep[len(t) // 2, 1] * 1e3 - 4.0),
                 (20, -9.5), fontsize=8.5, color=C[1], arrowprops=dict(arrowstyle="-", color=C[1], lw=0.8))
    ax0.set_aspect("equal")
    ax0.set_ylim(-11, 8)
    ax0.set_xlabel("mm along the line")
    ax0.set_title("A synthetic writer's 'return library books by friday' (aiguide writer 0) and its slow sweep", fontsize=10, loc="left")
    ax1.plot(t, f_comp * 1e3, color=C[0], lw=1.2, label="fingers: up-down strokes and loops (along the slant)")
    ax1.plot(t, w_comp * 1e3 - 3.5, color=C[2], lw=1.2, label="wrist: sideways strokes and slant")
    ax1.set_xlim(2.0, 7.0)
    ax1.set_xlabel("time (s)")
    ax1.set_ylabel("mm (offset for clarity)")
    ax1.legend(loc="upper right", fontsize=8.5)
    ax1.set_title("The letter part (writing minus the sweep): about 3-7 strokes per second", fontsize=10, loc="left")
    ax2.axis("off")
    lines = [
        ("Fingers (thumb, index, middle)", C[0], "Up-down strokes and loops of each letter, 1-5 mm.\nStrokes last 90-150 ms (CON-24); movement axis\nabout 134 deg vs 39 deg for the wrist (CON-32)."),
        ("Wrist", C[2], "Sideways strokes, joins and slant; works with the\nfingers in every letter (CON-31, CON-34)."),
        ("Forearm, elbow, shoulder", C[1], "Carry the hand along the line and to the next line:\nslow (below about 1 Hz), 10-30 mm/s."),
        ("Essential tremor", C[7], "Action tremor 4-12 Hz, largest in wrist flexion-extension\nand forearm rotation (HAP-33/PDT-32); fixed axis in\nthe ink (PDT-36). Older patients often 4-6 Hz (PDT-31)."),
        ("Parkinson's disease", C[6], "Rest tremor 4-6 Hz, usually smaller while writing\n(PDT-07). Main writing problems: small, shrinking\nletters (micrographia) and slowness (PDT-05/06/38)."),
        ("Why this matters", INK, "Tremor (4-12 Hz) sits in the same band as the finger\nand wrist strokes (3-7 Hz). A filter cannot tell them\napart; only a model of the writing or of the tremor can."),
    ]
    y = 0.98
    for title, col, body in lines:
        ax2.text(0.0, y, title, fontsize=10, color=col, fontweight="bold", va="top")
        ax2.text(0.0, y - 0.035, body, fontsize=8.6, color=INK2, va="top")
        y -= 0.165
    plotstyle.stamp(fig, "LITERATURE + CALCULATION on synthetic writing", "CON-24/31/32/34, HAP-33, PDT-05/06/07/31/36/38")
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["t_s", "x_mm", "y_mm", "pen_down", "sweep_x_mm", "sweep_y_mm", "finger_mm", "wrist_mm"],
              [[round(a, 4), round(b, 4), round(c, 4), int(d), round(e, 4), round(f, 4), round(g, 4), round(h, 4)]
               for a, b, c, d, e, f, g, h in zip(t[::5], xs[::5], ys[::5], m[::5], sweep[::5, 0] * 1e3, sweep[::5, 1] * 1e3,
                                                 f_comp[::5] * 1e3, w_comp[::5] * 1e3)])


# ------------------------------------------------------------------ 3. timing and spectrum
def fig_spectrum(out: Path) -> Dict:
    from scipy.signal import welch
    psd_acc, f = None, None
    durs = []
    for w in range(6):
        wr = W.writer(w).write(W.ET_SENTENCE, dt=W.SIM_DT, seed=2000 + w)
        it = wr.intended
        step = int(round(0.002 / (it.t[1] - it.t[0])))
        xy = it.xy[::step]
        fs = 500.0
        v = np.gradient(xy, 1.0 / fs, axis=0)
        fq, p = welch(v, fs=fs, nperseg=1024, axis=0)
        p = p.sum(axis=1)
        psd_acc = p if psd_acc is None else psd_acc + p
        f = fq
        sp = np.hypot(v[:, 0], v[:, 1])
        dn = it.pen_down[::step]
        mins = np.flatnonzero((sp[1:-1] < sp[:-2]) & (sp[1:-1] <= sp[2:]) & dn[1:-1]) + 1
        d = np.diff(mins) / fs
        durs += list(d[(d > 0.03) & (d < 0.6)])
    psd = psd_acc / psd_acc.sum()
    cum = np.cumsum(psd)
    f90 = float(f[np.searchsorted(cum, 0.90)])
    plotstyle.apply()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    ax = axes[0]
    ax.axvspan(4, 12, color=C[7], alpha=0.10, lw=0)
    ax.axvspan(4, 6, color=C[6], alpha=0.14, lw=0)
    ax.axvspan(8, 12, color=MUTED, alpha=0.10, lw=0)
    ax.semilogy(f, psd, color=INK, lw=2)
    ax.set_xlim(0, 20)
    ax.set_ylim(psd.max() * 3e-4, psd.max() * 3)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("share of pen-velocity energy per bin")
    ax.text(4.2, psd.max() * 0.5, "ET action\ntremor 4-12 Hz", fontsize=8.5, color=C[7])
    ax.text(4.1, psd.max() * 0.02, "PD rest\n4-6 Hz", fontsize=8.5, color=C[6])
    ax.text(8.2, psd.max() * 0.004, "physiological\n8-12 Hz", fontsize=8.5, color=INK2)
    ax.set_title(f"Pen-velocity spectrum: 90 % below {f90:.1f} Hz for these sharp synthetic letters\n(one real writer: 90 % below 4.9 Hz, CON-25; 'flat 1-5 Hz, near noise by 10 Hz', CON-24)", fontsize=9.5, loc="left")
    ax = axes[1]
    ax.hist(np.array(durs) * 1e3, bins=np.arange(30, 600, 15), color=C[0], alpha=0.85)
    ax.axvspan(90, 150, color=C[2], alpha=0.15, lw=0)
    ax.text(95, ax.get_ylim()[1] * 0.9, "90-150 ms\n(CON-24)", fontsize=8.5, color=INK2, va="top")
    ax.set_xlabel("time between speed minima (ms)")
    ax.set_ylabel("count")
    ax.set_title("Time between speed minima, synthetic writers (bimodal: short corner pieces,\nlonger strokes); real writing 90-150 ms (CON-24), IQR 105-160 ms (CON-25)", fontsize=9.5, loc="left")
    plotstyle.stamp(fig, "CALCULATION on synthetic writing (aiguide writers 0-5) + LITERATURE bands",
                    "CON-24, CON-25 (real writer: 90 % by 4.9 Hz), PDT-07/31")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["f_hz", "velocity_energy_share"], [[round(a, 3), float(b)] for a, b in zip(f, psd)])
    return {"f90_hz": f90, "stroke_ms_median": float(np.median(durs) * 1e3), "stroke_ms_iqr": [float(np.percentile(durs, 25) * 1e3), float(np.percentile(durs, 75) * 1e3)]}


# ------------------------------------------------------------------ 4. tremor in the ink
def fig_tremor_ink(out: Path) -> None:
    from .figures import lined_panel
    wr = W.writer(0).write(W.ET_SENTENCE, dt=W.SIM_DT, seed=2000)
    hand = PR.Hand.from_config()
    pen = PR.ordinary_pen()
    s0 = PL.scenario_from_written(wr, None)
    hp = PL.adapted_path(s0.intended, s0.dt, pen, hand)
    cases = [(None, None, "no tremor")] + [(f0, a, f"hand tremor {a * 1e3:g} mm at {f0:g} Hz") for a in (0.3e-3, 1.0e-3, 2.0e-3) for f0 in (5.0, 9.0)]
    plotstyle.apply()
    fig, axes = plt.subplots(len(cases), 1, figsize=(10.5, 1.45 * len(cases)))
    rows = []
    for ax, (f0, a, lab) in zip(axes, cases):
        d = None if f0 is None else W.tremor_path(s0.t, f0, a, 200, 0)
        r = PL.run(PL.with_hand_path(s0, hp, d), pen, hand)
        lined_panel(ax, r.ink * 1e3, r.contact > 0.5, x_height=wr.style.x_height_mm, title=f"Ordinary pen, {lab}")
        if f0 is None:
            x0 = float(np.nanmin(r.ink[:, 0]) * 1e3)
            ax.plot([x0, x0 + 10.0], [8.8, 8.8], color=INK, lw=1.5)
            ax.text(x0 + 11.0, 8.8, "10 mm", fontsize=7, color=INK2, va="center")
        rows.append([lab, f0, a])
    plotstyle.stamp(fig, "SIMULATION (model HW1; synthetic writer and tremor)", "enlarged about 2.5x; ruled lines 8 mm apart; tremor = peak at the hand")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["case", "f0_hz", "amp_m"], rows)


# ------------------------------------------------------------------ 5. forces and reach
def fig_forces(out: Path) -> List[List]:
    hand = PR.Hand.from_config()
    rev = PR.rev_h()
    brd = PR.board()
    w6 = 2 * math.pi * 6.0
    Zarm = abs(complex(hand.k_arm - hand.M_hand * w6 ** 2, w6 * hand.b_arm))
    k_series = 1.0 / (1.0 / hand.K_grip + 1.0 / hand.k_arm)
    F_move_static = k_series * 3e-3
    F_move_6 = 1.0 / (1.0 / hand.K_grip + 1.0 / Zarm) * 3e-3
    items = [
        ("Grip force of the three digits on the barrel", 4.9, "LITERATURE CON-05 (4.2-5.6 N, children); CON-04 sum ~6.5 N"),
        ("Writing force of the tip on the paper", 1.0, "LITERATURE CON-01 (mean 1.01 N)"),
        ("Push needed to move a relaxed hand 3 mm at 6 Hz", F_move_6, "CALC from HAP-26 impedance (grip + arm)"),
        ("Push needed to move it 3 mm slowly", F_move_static, "CALC HAP-26: grip 575 N/m in series with arm 170 N/m"),
        ("Rev H nose actuator (peak, at the tip)", rev.F_peak, "CALC results/revH/tip_params.json"),
        ("Guidance board on the pen magnet (cap)", brd.F_cap, f"CALC {brd.sources.get('file', 'board file')} (software cap); LIT HAP-16: 0.488 N"),
        ("Paper drag on the ball", 0.15, "ASSUMPTION mu 0.15 x 1 N (CON-13: 0.09-0.165)"),
        ("Inertial weight inside a pen (5 g, +-1 mm)", 0.013, "CALC docs/inertial_stabilisation.md 3.1 (2-30 mN)"),
    ]
    reach = [("Pencil Rev P0 nib stage", 0.3, "CALC config/pencil.yaml"), ("Rev H active nose", 3.0, "tip_params.json"),
             ("Guidance board", 150.0, "whole page (A5-A4); guided error ~2 mm in HAP-16"),
             ("Letter height (x-height)", 2.5, "aiguide writers 2.0-3.2 mm; PD start 5 mm (PDT-06)")]
    plotstyle.apply()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    names = [i[0] for i in items][::-1]
    vals = [i[1] for i in items][::-1]
    cols = [C[0] if "Rev H" in n else C[1] if "board" in n else C[7] if "Inertial" in n else MUTED for n in names]
    ax.barh(range(len(vals)), vals, color=cols)
    ax.set_xscale("log")
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(names, fontsize=8.5)
    for i, v in enumerate(vals):
        ax.text(v * 1.15, i, f"{v:.3g} N", va="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0.005, 20)
    ax.set_xlabel("force (N, log scale)")
    ax.set_title("Forces: a pen can push its own tip; only a grounded board can push the hand", fontsize=10, loc="left")
    ax = axes[1]
    rn = [r[0] for r in reach][::-1]
    rv = [r[1] for r in reach][::-1]
    ax.barh(range(len(rv)), rv, color=[C[1] if "board" in n else C[0] if "Rev H" in n else C[3] if "Letter" in n else MUTED for n in rn])
    ax.set_xscale("log")
    ax.set_yticks(range(len(rv)))
    ax.set_yticklabels(rn, fontsize=8.5)
    for i, v in enumerate(rv):
        ax.text(v * 1.15, i, f"{v:g} mm", va="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0.1, 1000)
    ax.set_xlabel("how far it can move the ink (mm, log scale)")
    ax.set_title("Reach of each device vs the size of a letter", fontsize=10, loc="left")
    plotstyle.stamp(fig, "CALCULATION + LITERATURE + PROPOSED DESIGN", "HAP-16, HAP-26, CON-01/04/05/13")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    rows = [[n, v, s] for n, v, s in items] + [[n, v, s] for n, v, s in reach]
    write_csv(out.with_suffix(".csv"), ["item", "value (N or mm)", "source"], rows)
    return rows


def build(outdir: Path = RESULTS_DIR) -> Dict:
    outdir.mkdir(parents=True, exist_ok=True)
    fig_grasp(outdir / "fig_primer_grasp.png")
    fig_joints(outdir / "fig_primer_joints.png")
    spec = fig_spectrum(outdir / "fig_primer_spectrum.png")
    fig_tremor_ink(outdir / "fig_primer_tremor_ink.png")
    forces = fig_forces(outdir / "fig_primer_forces.png")
    return {"spectrum": spec, "forces": forces}
