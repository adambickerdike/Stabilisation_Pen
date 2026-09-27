#!/usr/bin/env python3
"""Electromagnetic model of a flat moving-coil voice-coil module (one axis).

Geometry (module frame: x = force axis, y = conductor axis, z = barrel axis)
  * two fixed NdFeB plates above/below a moving flat racetrack coil; each plate
    has two poles split at x = 0 (magnetised along z, opposite senses) so that
    flux crosses the gap downward for x < 0 and upward for x > 0;
  * optional soft-iron back plates, modelled by first-order image magnets
    (mu -> infinity plane; image = mirrored magnet, same magnetisation sense);
  * coil long sides run along y at x = -p and x = +p and carry opposite
    currents, so both contribute force along +x.
Method: B from magpylib (analytic cuboid fields); Lorentz force
F = I * sum(dl x B) over filament discretisation of the winding bundle.
Outputs: force constant map Kf(x, y), cross-axis force, resistance, motor
constant Km = Kf/sqrt(R), moving mass, coil self-field at a Hall location.
Evidence status: NUMERICAL SIMULATION (magnetostatics, linear magnets, no
saturation, no eddy currents).  Iron modelled by images is an upper bound
unless the back plate stays below ~1.5 T; see iron_flux_check.
Run: python3 analysis/em_actuator.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import asdict, dataclass

import magpylib as magpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import plotstyle, provenance  # noqa: E402

RHO_CU = 1.72e-8
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "em")


@dataclass
class VCMGeom:
    # magnets (m)
    Br: float = 1.32            # T, N42-class remanence (verify grade datasheet)
    t_m: float = 1.5e-3         # magnet thickness (z)
    X_m: float = 9.0e-3         # magnet plate extent along force axis
    Y_m: float = 6.0e-3         # magnet plate extent along conductor axis
    gap: float = 1.6e-3         # air gap between magnet faces (z)
    iron: bool = True           # back iron via first-order images
    t_fe: float = 1.5e-3        # back-iron thickness (for flux check)
    # coil (m)
    p: float = 2.2e-3           # half distance between long-side centrelines
    e: float = 1.2e-3           # winding bundle width (x)
    t_c: float = 1.0e-3         # winding thickness (z)
    L_side: float = 8.0e-3      # straight length of long sides (y)
    wire_d: float = 0.08e-3     # copper diameter
    fill: float = 0.55          # copper fill factor of bundle
    stroke: float = 1.6e-3      # +/- stroke along x at the actuator
    density_coil: float = 6500  # kg/m^3 bundle (copper + bond + insulation)


def magnets(g: VCMGeom):
    """List of magpylib Cuboids (plus images)."""
    zt = g.gap / 2 + g.t_m / 2
    half = g.X_m / 2
    mags = []
    for sx, sgn in ((-1, -1), (+1, +1)):     # x<0: flux downward (-z); x>0: upward (+z)
        cx = sx * half / 2
        for zc in (+zt, -zt):
            m = magpy.magnet.Cuboid(position=(cx, 0, zc), dimension=(half, g.Y_m, g.t_m),
                                    polarization=(0, 0, sgn * g.Br))
            mags.append(m)
            if g.iron:
                # iron plane at the outer face of this magnet; image mirrored across it
                zi = zc + math.copysign(g.t_m / 2, zc)
                z_img = 2 * zi - zc
                mags.append(magpy.magnet.Cuboid(position=(cx, 0, z_img), dimension=(half, g.Y_m, g.t_m),
                                                polarization=(0, 0, sgn * g.Br)))
    return magpy.Collection(*mags)


def coil_turns(g: VCMGeom):
    A_bundle = g.e * g.t_c
    A_w = math.pi * g.wire_d ** 2 / 4
    return int(g.fill * A_bundle / A_w)


def coil_filaments(g: VCMGeom, x0=0.0, y0=0.0, nx=4, nz=3, nseg=40):
    """Racetrack filaments: list of (points (m,3), direction unit (3,), dl, weight)."""
    fil = []
    xs = np.linspace(-g.e / 2 + g.e / (2 * nx), g.e / 2 - g.e / (2 * nx), nx)
    zs = np.linspace(-g.t_c / 2 + g.t_c / (2 * nz), g.t_c / 2 - g.t_c / (2 * nz), nz)
    w = 1.0 / (nx * nz)
    for dx in xs:
        for dz in zs:
            pp = g.p + dx          # radius of this filament from coil centre in x
            hl = g.L_side / 2
            # four straight segments (rounded ends approximated by straight end segments)
            corners = [(-pp, -hl), (-pp, hl), (pp, hl), (pp, -hl), (-pp, -hl)]
            for (xa, ya), (xb, yb) in zip(corners[:-1], corners[1:]):
                n = nseg
                s = (np.arange(n) + 0.5) / n
                pts = np.column_stack([x0 + xa + (xb - xa) * s, y0 + ya + (yb - ya) * s, np.full(n, dz)])
                d = np.array([xb - xa, yb - ya, 0.0])
                L = np.linalg.norm(d)
                fil.append((pts, d / L, L / n, w))
    return fil


def lorentz_force(g: VCMGeom, coll, x0=0.0, y0=0.0, current=1.0):
    """Force on the coil (N) for total ampere-turns N*current."""
    N = coil_turns(g)
    F = np.zeros(3)
    fil = coil_filaments(g, x0, y0)
    allpts = np.vstack([f[0] for f in fil])
    B = coll.getB(allpts)
    k = 0
    for pts, u, dl, w in fil:
        n = len(pts)
        Bs = B[k:k + n]
        k += n
        F += w * N * current * dl * np.cross(u[None, :], Bs).sum(axis=0)
    return F


def mean_turn_length(g: VCMGeom):
    return 2 * g.L_side + 2 * (2 * g.p)


def resistance(g: VCMGeom):
    N = coil_turns(g)
    A_w = math.pi * g.wire_d ** 2 / 4
    return RHO_CU * N * mean_turn_length(g) / A_w


def coil_mass(g: VCMGeom):
    return g.density_coil * g.e * g.t_c * mean_turn_length(g)


def magnet_mass(g: VCMGeom, rho=7500.0):
    return rho * 2 * g.X_m * g.Y_m * g.t_m


def iron_flux_check(g: VCMGeom, B_gap):
    """Peak flux density in a back plate carrying one pole's flux laterally."""
    phi = B_gap * (g.X_m / 2) * g.Y_m
    return phi / (g.t_fe * g.Y_m)


def coil_self_field(g: VCMGeom, point, x0=0.0, y0=0.0, current=1.0):
    """B (T) at a point produced by the coil (all turns) at 1 A, air core."""
    N = coil_turns(g)
    hl = g.L_side / 2
    pp = g.p
    verts = np.array([(-pp, -hl, 0), (-pp, hl, 0), (pp, hl, 0), (pp, -hl, 0), (-pp, -hl, 0)]) + np.array([x0, y0, 0])
    line = magpy.current.Polyline(current=N * current, vertices=verts)
    return line.getB(point)


def inductance_estimate(g: VCMGeom):
    """Air-core flux-linkage estimate L = N * Phi / I (single mean turn), then
    x mu_r_eff factor for the iron-bounded gap (reported separately)."""
    N = coil_turns(g)
    hl = g.L_side / 2
    pp = g.p
    verts = np.array([(-pp, -hl, 0), (-pp, hl, 0), (pp, hl, 0), (pp, -hl, 0), (-pp, -hl, 0)])
    line = magpy.current.Polyline(current=1.0, vertices=verts)
    xs = np.linspace(-pp * 0.95, pp * 0.95, 30)
    ys = np.linspace(-hl * 0.95, hl * 0.95, 40)
    X, Y = np.meshgrid(xs, ys)
    pts = np.column_stack([X.ravel(), Y.ravel(), np.zeros(X.size)])
    Bz = line.getB(pts)[:, 2]
    phi = Bz.mean() * (2 * pp) * (2 * hl)
    L_air = N * N * phi
    return abs(L_air)


def evaluate(g: VCMGeom, grid=7):
    coll = magnets(g)
    xs = np.linspace(-g.stroke, g.stroke, grid)
    ys = np.linspace(-g.stroke, g.stroke, grid)
    Kx = np.zeros((grid, grid))
    Ky = np.zeros((grid, grid))
    Fz = np.zeros((grid, grid))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            F = lorentz_force(g, coll, x, y, 1.0)
            Kx[i, j], Ky[i, j], Fz[i, j] = F
    # sign convention: filament traversal sets current direction; report magnitudes
    sgn = 1.0 if Kx[grid // 2, grid // 2] >= 0 else -1.0
    Kx *= sgn
    Ky *= sgn
    R = resistance(g)
    Kf0 = Kx[grid // 2, grid // 2]
    Bgap = float(np.abs(coll.getB((g.X_m / 4, 0, 0))[2]))
    out = {
        "geometry": asdict(g),
        "turns": coil_turns(g),
        "R_ohm_20C": R,
        "Kf_center_N_per_A": Kf0,
        "Kf_min_over_stroke": float(Kx.min()),
        "Kf_max_over_stroke": float(Kx.max()),
        "Kf_variation_pct": float((Kx.max() - Kx.min()) / Kf0 * 100),
        "cross_force_max_N_per_A": float(np.abs(Ky).max()),
        "axial_force_max_N_per_A": float(np.abs(Fz).max()),
        "Km_center_N_per_sqrtW": Kf0 / math.sqrt(R),
        "Km_min_N_per_sqrtW": float(Kx.min() / math.sqrt(R)),
        "coil_mass_g": coil_mass(g) * 1e3,
        "magnet_mass_g": magnet_mass(g) * 1e3,
        "B_gap_mid_pole_T": Bgap,
        "iron_flux_T": iron_flux_check(g, Bgap) if g.iron else None,
        "L_air_uH": inductance_estimate(g) * 1e6,
        "module_height_z_mm": (g.gap + 2 * g.t_m + (2 * g.t_fe if g.iron else 0)) * 1e3,
        "Kx_map": Kx.tolist(), "Ky_map": Ky.tolist(), "grid_m": xs.tolist(),
    }
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    results = {}
    base = VCMGeom()
    variants = {
        "rearA_iron": base,
        "rearA_no_iron": VCMGeom(iron=False),
        "rearA_thin_gap": VCMGeom(gap=1.2e-3, t_c=0.7e-3),
        "rearA_iron_2p5": VCMGeom(t_fe=2.5e-3),
        "rearA_wide": VCMGeom(X_m=10.0e-3, Y_m=7.0e-3, L_side=9.0e-3, e=1.5e-3, p=2.4e-3),
        # front direct-drive module constrained to annulus around refill (short, small)
        "frontDD_iron": VCMGeom(X_m=5.0e-3, Y_m=4.0e-3, t_m=1.0e-3, gap=1.3e-3, p=1.2e-3, e=0.8e-3,
                                t_c=0.8e-3, L_side=5.0e-3, stroke=0.65e-3, t_fe=1.0e-3),
    }
    for name, g in variants.items():
        results[name] = evaluate(g)
        r = results[name]
        print(f"{name:16s} N={r['turns']:4d} R={r['R_ohm_20C']:5.1f} ohm Kf={r['Kf_center_N_per_A']:.3f} N/A "
              f"({r['Kf_variation_pct']:.0f}% var) Km={r['Km_center_N_per_sqrtW']:.3f} N/sqrtW "
              f"Bgap={r['B_gap_mid_pole_T']:.2f} T iron={r['iron_flux_T']} coil={r['coil_mass_g']:.2f} g "
              f"mag={r['magnet_mass_g']:.2f} g L~{r['L_air_uH']:.0f} uH h={r['module_height_z_mm']:.1f} mm "
              f"cross={r['cross_force_max_N_per_A']:.3f} axial={r['axial_force_max_N_per_A']:.3f}")
    # Hall crosstalk: coil self-field per ampere at a sensor 6 mm axially from the coil plane
    g = base
    for dz in (4e-3, 6e-3, 10e-3):
        B = coil_self_field(g, (0, 0, dz))
        results.setdefault("hall_crosstalk_T_per_A", {})[f"dz_{dz*1e3:.0f}mm"] = B.tolist()
    # force-constant map figure for the base design
    r = results["rearA_iron"]
    grid = np.array(r["grid_m"]) * 1e3
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    Kx = np.array(r["Kx_map"])
    for j, lab in ((len(grid) // 2, "y = 0"), (0, f"y = {grid[0]:.1f} mm"), (len(grid) - 1, f"y = {grid[-1]:.1f} mm")):
        ax.plot(grid, Kx[:, j], label=lab)
    ax.set_xlabel("Coil position along force axis x (mm)")
    ax.set_ylabel("Force constant Kf (N/A)")
    ax.set_title("Moving-coil module rearA_iron: Kf over the actuator stroke", loc="left")
    ax.set_ylim(0, max(1.0, Kx.max() * 1.15))
    ax.legend()
    plotstyle.stamp(fig, "numerical simulation", "magpylib, image-iron, linear magnets")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_kf_map.png"))
    plt.close(fig)
    meta = provenance.metadata("numerical simulation (magnetostatic, unvalidated)",
                               extra={"magpylib": magpy.__version__, "script": "analysis/em_actuator.py"})
    provenance.write_json(os.path.join(OUT, "em_actuator.json"), {"meta": meta, "results": results})


if __name__ == "__main__":
    main()
