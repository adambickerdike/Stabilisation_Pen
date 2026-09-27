#!/usr/bin/env python3
"""Rear planar 2-axis moving-magnet actuator and lever-ratio sweep.

Topology (actuator frame: x, y transverse; z along barrel axis)
  * moving paddle at the rear end of the lever carrier: one NdFeB disc of
    radius r_m split into four quadrants magnetised +z/-z in a checkerboard
    (Q1 +, Q2 -, Q3 +, Q4 -).  The magnet volume serves BOTH axes;
  * fixed flat racetrack coils in two stacked layers on each side of the
    paddle: X layer = two coils over the upper/lower half-discs with active
    sides along y at x = +/-a; Y layer = the same rotated 90 degrees.  The
    lower/left coil of each pair is connected in reverse so both push the
    same way.  Front layers have an open centre for the carrier;
  * optional soft-iron plates outside the outer coil layers (first-order
    images of the paddle magnets).
Envelope: the swept paddle (r_m + sqrt(2)*stroke) and the coils must fit in
radius R_env; stroke = n * tip_travel (lever ratio n = L2/L1).  Active sides
must stay inside their quadrant over the stroke.
Outputs Kf (N/A), resistance per axis, Km (N/sqrt(W)), cross-coupling over
the stroke, moving mass, tip-referred Km = n*Km and holding power for the
design and high loads.
Evidence status: NUMERICAL SIMULATION (linear magnets, image iron, no
saturation or eddy currents).  Validate with EXP-B03 force-current map.
"""
from __future__ import annotations

import math
import os
import sys

import magpylib as magpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import contact, plotstyle, provenance  # noqa: E402

RHO_CU = 1.72e-8
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "em")


def design(n, tip_travel=0.60e-3, R_env=6.2e-3, Br=1.32, t_m=1.2e-3, gap=0.35e-3, t_c=0.55e-3,
           layer_gap=0.1e-3, wire_d=0.063e-3, fill=0.55, margin=0.25e-3, double_sided=True, iron=True):
    stroke = n * tip_travel
    r_m = R_env - math.sqrt(2) * stroke - margin           # largest magnet whose swept disc fits
    a = r_m / 2
    side_w = min(1.2e-3, 2 * (a - stroke - margin))       # active side must not cross x = 0 or leave disc
    if side_w < 0.3e-3 or r_m < 2e-3:
        return None
    return dict(n=n, stroke=stroke, r_m=r_m, a=a, side_w=side_w, t_m=t_m, gap=gap, t_c=t_c,
                layer_gap=layer_gap, wire_d=wire_d, fill=fill, Br=Br, double_sided=double_sided, iron=iron,
                coil_len=r_m - 0.2e-3, R_env=R_env, margin=margin)


def paddle(d):
    q = []
    for k, sgn in enumerate((+1, -1, +1, -1)):
        q.append(magpy.magnet.CylinderSegment(position=(0, 0, 0),
                                              dimension=(0.0, d["r_m"], d["t_m"], 90 * k, 90 * (k + 1)),
                                              polarization=(0, 0, sgn * d["Br"])))
    return q


def layer_z(d):
    """z-centres of (X, Y) coil layers on each side (X nearer on front, Y nearer on back)."""
    z1 = d["t_m"] / 2 + d["gap"] + d["t_c"] / 2
    z2 = z1 + d["t_c"] + d["layer_gap"]
    zs = {"x": [-z1], "y": [-z2]}
    if d["double_sided"]:
        zs["y"].append(+z1)
        zs["x"].append(+z2)
    return zs


def filaments(d, axis, z, shift, nw=3, nt=2, nseg=20):
    """Coil pair filaments for one axis at layer z, expressed in the paddle frame
    (paddle displaced by 'shift' -> coils appear displaced by -shift)."""
    sx, sy = shift
    out = []
    hl = d["coil_len"] / 2
    for half in (+1, -1):                  # upper/lower (X) or right/left (Y) coil
        centre = half * (0.1e-3 + hl)
        for dw in np.linspace(-d["side_w"] / 2, d["side_w"] / 2, nw + 2)[1:-1]:
            for dt in np.linspace(-d["t_c"] / 2, d["t_c"] / 2, nt + 2)[1:-1]:
                aa = d["a"] + dw
                if axis == "x":
                    corners = [(-aa, centre - hl), (-aa, centre + hl), (aa, centre + hl), (aa, centre - hl), (-aa, centre - hl)]
                else:
                    corners = [(centre - hl, -aa), (centre + hl, -aa), (centre + hl, aa), (centre - hl, aa), (centre - hl, -aa)]
                corners = [(u - sx, v - sy) for u, v in corners]
                for (xa, ya), (xb, yb) in zip(corners[:-1], corners[1:]):
                    s = (np.arange(nseg) + 0.5) / nseg
                    pts = np.column_stack([xa + (xb - xa) * s, ya + (yb - ya) * s, np.full(nseg, z + dt)])
                    v = np.array([xb - xa, yb - ya, 0.0])
                    L = np.linalg.norm(v)
                    # reverse current in the lower/left coil so both coils push the same way
                    out.append((pts, half * v / L, L / nseg, 1.0 / (nw * nt)))
    return out


def turns(d):
    return int(d["fill"] * d["side_w"] * d["t_c"] / (math.pi * d["wire_d"] ** 2 / 4))


def coil_length_per_turn(d):
    return 2 * d["coil_len"] + 2 * (2 * d["a"])


def R_axis(d):
    """Resistance of all coils of one axis in series (2 coils per layer)."""
    n_layers = 2 if d["double_sided"] else 1
    A_w = math.pi * d["wire_d"] ** 2 / 4
    return n_layers * 2 * RHO_CU * turns(d) * coil_length_per_turn(d) / A_w


def force(d, mags, axis, shift):
    N = turns(d)
    F = np.zeros(3)
    zs = layer_z(d)[axis]
    for z in zs:
        fil = filaments(d, axis, z, shift)
        pts = np.vstack([f[0] for f in fil])
        B = magpy.getB(mags, pts, sumup=True)
        if d["iron"]:
            outer = max(abs(v) for v in layer_z(d)["x"] + layer_z(d)["y"])
            z_fe = math.copysign(outer + d["t_c"] / 2 + 0.1e-3, z)
            img = [magpy.magnet.CylinderSegment(position=(0, 0, 2 * z_fe), dimension=m.dimension,
                                                polarization=m.polarization) for m in mags]
            B = B + magpy.getB(img, pts, sumup=True)
        k = 0
        for p_, u, dl, w in fil:
            nn = len(p_)
            F += w * N * dl * np.cross(u[None, :], B[k:k + nn]).sum(axis=0)
            k += nn
    return -F   # reaction on the moving paddle


def evaluate(d, grid=5):
    mags = paddle(d)
    s = d["stroke"]
    g = np.linspace(-s, s, grid)
    KX = np.zeros((grid, grid)); KY = np.zeros((grid, grid)); CX = np.zeros((grid, grid)); CY = np.zeros((grid, grid))
    for i, px in enumerate(g):
        for j, py in enumerate(g):
            fx = force(d, mags, "x", (px, py))
            fy = force(d, mags, "y", (px, py))
            KX[i, j], CX[i, j] = fx[0], fx[1]
            KY[i, j], CY[i, j] = fy[1], fy[0]
    sx = 1.0 if KX[grid // 2, grid // 2] >= 0 else -1.0
    sy = 1.0 if KY[grid // 2, grid // 2] >= 0 else -1.0
    KX *= sx; CX *= sx; KY *= sy; CY *= sy
    R = R_axis(d)
    kmin = float(min(KX.min(), KY.min()))
    kc = float(0.5 * (KX[grid // 2, grid // 2] + KY[grid // 2, grid // 2]))
    return {"Kf_centre_N_per_A": kc, "Kf_min_N_per_A": kmin, "Kf_x_centre": float(KX[grid // 2, grid // 2]),
            "Kf_y_centre": float(KY[grid // 2, grid // 2]), "R_axis_ohm": R, "turns_per_coil": turns(d),
            "Km_centre": kc / math.sqrt(R), "Km_min": kmin / math.sqrt(R),
            "cross_max_frac": float(max(np.abs(CX).max(), np.abs(CY).max()) / kc),
            "magnet_mass_g": math.pi * d["r_m"] ** 2 * d["t_m"] * 7500 * 1e3}


def main():
    os.makedirs(OUT, exist_ok=True)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    D2R = math.pi / 180
    F_design = float(contact.transverse_load_bounds(1.0, 0.15, 50 * D2R)["rms"])
    F_high = float(contact.transverse_load_bounds(1.5, 0.2, 40 * D2R)["rms"])
    rows = []
    for n in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
        d = design(n)
        if d is None:
            rows.append({"n": n, "fits": False})
            print(f"n={n}: layout infeasible in envelope")
            continue
        r = evaluate(d)
        km_tip = n * r["Km_min"]
        refl = n ** 2 * (r["magnet_mass_g"] + 0.15)
        row = {"n": n, "fits": True, **{k: v for k, v in d.items() if isinstance(v, (int, float))}, **r,
               "Km_tip_min": km_tip, "P_hold_design_W": (F_design / km_tip) ** 2,
               "P_hold_high_W": (F_high / km_tip) ** 2, "reflected_paddle_mass_g": refl}
        rows.append(row)
        print(f"n={n:.1f} stroke={d['stroke']*1e3:.2f} r_m={d['r_m']*1e3:.2f} side={d['side_w']*1e3:.2f} turns={r['turns_per_coil']} "
              f"Kf={r['Kf_centre_N_per_A']:.3f} (min {r['Kf_min_N_per_A']:.3f}) R={r['R_axis_ohm']:.1f} Km={r['Km_centre']:.3f} "
              f"Km_tip_min={km_tip:.2f} cross={r['cross_max_frac']:.2f} mag={r['magnet_mass_g']:.2f} g refl={refl:.1f} g "
              f"P_design={row['P_hold_design_W']:.3f} W P_high={row['P_hold_high_W']:.3f} W", flush=True)
    ok = [r for r in rows if r.get("fits")]
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    for key, lab, c in (("P_hold_design_W", "design load: 1 N, 50°, μ 0.15", plotstyle.SERIES[0]),
                        ("P_hold_high_W", "high load: 1.5 N, 40°, μ 0.2", plotstyle.SERIES[1])):
        ax.plot([r["n"] for r in ok], [r[key] for r in ok], color=c, label=lab, marker="o",
                markerfacecolor=c, markeredgecolor=plotstyle.SURFACE, markeredgewidth=1.6)
    ax.set_yscale("log")
    ax.set_xlabel("Lever ratio n = L2/L1")
    ax.set_ylabel("Copper loss to hold the load (W)")
    ax.set_title("Planar moving-magnet actuator inside Ø12.4 mm: holding power vs lever ratio", loc="left", fontsize=10)
    ax.legend()
    plotstyle.stamp(fig, "numerical simulation", "magpylib; worst Kf over stroke; not measured")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_planar_lever_sweep.png"))
    plt.close(fig)
    meta = provenance.metadata("numerical simulation (magnetostatic, unvalidated)",
                               extra={"magpylib": magpy.__version__, "F_design_N": F_design, "F_high_N": F_high})
    provenance.write_json(os.path.join(OUT, "em_planar_sweep.json"), {"meta": meta, "rows": rows})


if __name__ == "__main__":
    main()
