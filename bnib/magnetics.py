r"""Force maps of the nib actuators over the full stroke (CALC; magpylib analytic cuboid magnets, soft iron by images).

Topology (PROPOSED DESIGN): the annular axial-gap checkerboard of study N (nose2 'axial', C1+/C1S) turned into a
MOVING-COIL translation actuator.  Four square poles (side w, thickness t_m, polarised +-z in a checkerboard) sit on a
fixed soft-iron plate around a central hole for the refill; a fixed soft-iron keeper closes the circuit on the other
side of the gap; the two coil layers (x legs along y, y legs along x; racetracks, one leg over each pole of a row or a
column) move laterally in the gap with the refill carrier.  Translation keeps the gap constant (no stroke-dependent
gap, study N's key lesson), and a moving coil carries no magnetic pull, no negative stiffness and no magnet mass.

Iron: both plates are infinitely permeable planes replaced by images (nose2.magnetics._images, three periods; the
convention is checked there to 4e-16 T): an UPPER BOUND on the flux (real iron is finite and saturates).  Lorentz force:
F = sum over filaments of I (dl x B), the coil bundles discretised into n_b x n_t filaments and each straight segment
into n_l points (midpoint rule).  Force constant of a layer of n_r racetracks in series:
    Km = F_NI / sqrt(n_r) * sqrt(k_fill A_w / (rho_Cu l_turn))        (F_NI: force per ampere-turn of the whole layer)
independent of the number of turns.  Km(dx, dy) over the stroke gives the force constant's variation and the
cross-coupling (y force from the x layer).  The moving-magnet variant's pull on the suspension and its lateral stiffness
come from magpylib getFT between the real magnets and their images.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Dict, List, Optional

import numpy as np

from .labels import MAT, val

RHO_CU = val(MAT["Cu_res"])


def _magpy():
    import magpylib as magpy
    return magpy


@dataclass(frozen=True)
class ChkGeom:
    """Annular axial-gap checkerboard (lengths in m).  e: half the spacing between adjacent poles (the refill hole)."""
    w: float = 5.0e-3            # pole side
    e: float = 1.6e-3            # half spacing between poles (central hole: inner corner at sqrt(2) e from the axis)
    t_m: float = 2.0e-3          # magnet thickness
    c0: float = 0.30e-3          # clearance magnet face -> first coil layer (moving coil)
    t_x: float = 0.45e-3         # x-layer thickness
    t_y: float = 0.45e-3         # y-layer thickness
    c1: float = 0.15e-3          # clearance last layer -> keeper
    Br: float = 1.42             # T (N52 low end, MFR AMF-139)
    s: float = 1.0e-3            # stroke (half) of the coil relative to the magnets
    k_fill: float = 0.55         # copper fill of the bonded flat coil (ASSUMPTION, nose2 WIRES at 0.10 mm)
    leg_over: float = 0.0        # extra leg length beyond the pole on each side (m); 0: leg length = w (study N's rule
                                 # keeps b = w - 2 s wide legs over the poles)

    @property
    def c(self) -> float:
        return 0.5 * self.w + self.e

    @property
    def D(self) -> float:
        return self.t_m + self.c0 + self.t_x + self.t_y + self.c1

    @property
    def b_leg(self) -> float:
        return max(self.w - 2.0 * self.s, 0.4e-3)

    @property
    def r_hole(self) -> float:
        return math.sqrt(2.0) * self.e

    @property
    def r_out(self) -> float:
        """Radius of the magnet array's outer corner (the moving coil's end turns reach about the same)."""
        return math.sqrt(2.0) * (self.c + 0.5 * self.w)


def sources(g: ChkGeom, n_img: int = 3, shift=(0.0, 0.0)):
    """The magnets with their images between the plates at z = 0 and z = D (shift: the magnets' lateral offset)."""
    from nose2 import magnetics as NM
    mags = []
    for i in (-1, 1):
        for j in (-1, 1):
            sgn = 1.0 if i * j > 0 else -1.0
            mags.append(((i * g.c + shift[0], j * g.c + shift[1], g.t_m / 2), (g.w, g.w, g.t_m), (0.0, 0.0, sgn * g.Br)))
    return NM._images(mags, g.D, axis=2, n=n_img)


def _racetrack_segments(xc: float, y0: float, y1: float, z: float, cur_sign: float, axis: str):
    """One racetrack of the x layer (legs along y at x = +-xc between y0 and y1) or the y layer (roles swapped):
    returns (p0, p1, sign) straight segments with the circulation +y on the +xc leg (x layer)."""
    segs = [((xc, y0, z), (xc, y1, z)), ((xc, y1, z), (-xc, y1, z)), ((-xc, y1, z), (-xc, y0, z)), ((-xc, y0, z), (xc, y0, z))]
    out = []
    for p0, p1 in segs:
        p0 = np.array(p0); p1 = np.array(p1)
        if axis == "y":                       # swap x and y for the y layer
            p0 = p0[[1, 0, 2]]; p1 = p1[[1, 0, 2]]
        out.append((p0, p1, cur_sign))
    return out


def layer_filaments(g: ChkGeom, axis: str = "x", nb: int = 4, nt: int = 2, nl: int = 16, disp=(0.0, 0.0)):
    """Midpoints, direction x length and current weight (per total ampere-turn of the layer) of the filament pieces."""
    L = g.w + 2 * g.leg_over
    if axis == "x":
        z0, tt = g.t_m + g.c0, g.t_x
    else:
        z0, tt = g.t_m + g.c0 + g.t_x, g.t_y
    pts, dls, wts = [], [], []
    nf = nb * nt
    for row in (-1, 1):
        # the row's pole under the +c leg has sign row (checkerboard): circulation sign that makes the force +axis
        cur = 1.0 if row > 0 else -1.0
        yc = row * g.c
        for ib in range(nb):
            dxb = (ib + 0.5) / nb * g.b_leg - 0.5 * g.b_leg
            for it in range(nt):
                z = z0 + (it + 0.5) / nt * tt
                segs = _racetrack_segments(g.c + dxb, yc - L / 2, yc + L / 2, z, cur, axis)
                for p0, p1, sg in segs:
                    for k in range(nl):
                        u0, u1 = k / nl, (k + 1) / nl
                        a = p0 + (p1 - p0) * u0
                        b = p0 + (p1 - p0) * u1
                        pts.append(0.5 * (a + b) + np.array([disp[0], disp[1], 0.0]))
                        dls.append((b - a) * sg)
                        wts.append(1.0 / (2 * nf))      # two racetracks share the layer's ampere-turns
    return np.array(pts), np.array(dls), np.array(wts)


def layer_force(g: ChkGeom, axis: str = "x", disp=(0.0, 0.0), src=None, **kw) -> np.ndarray:
    """Force (N) on the layer per total ampere-turn of the layer (both racetracks in series, NI = 1 A-turn each...
    normalised so that the returned vector is the force per ampere-turn flowing in every turn)."""
    src = sources(g) if src is None else src
    P, dl, wt = layer_filaments(g, axis, disp=disp, **kw)
    B = src.getB(P)
    dF = np.cross(dl, B) * wt[:, None]
    # every filament stands for 1/(2 nf) of the ampere-turns of ONE racetrack pair; per ampere-turn of each racetrack
    # the force is 2 x the weighted sum (two racetracks, each carrying the full ampere-turns)
    return 2.0 * dF.sum(axis=0)


def km_from_force(g: ChkGeom, F_per_AT: float, axis: str = "x", n_r: int = 2) -> float:
    """Force constant of the layer (N/sqrt(W)) from the force per ampere-turn of each racetrack (both in series)."""
    t = g.t_x if axis == "x" else g.t_y
    A_w = g.b_leg * t
    L = g.w + 2 * g.leg_over
    l_turn = 2 * (L + 2 * g.c)
    return F_per_AT / math.sqrt(n_r) * math.sqrt(g.k_fill * A_w / (RHO_CU * l_turn))


def coil_resistance_mass(g: ChkGeom, axis: str = "x", n_r: int = 2, R_target: float = 2.5) -> Dict:
    t = g.t_x if axis == "x" else g.t_y
    A_w = g.b_leg * t
    L = g.w + 2 * g.leg_over
    l_turn = 2 * (L + 2 * g.c)
    m_cu = n_r * 2 * (val(MAT["Cu_rho"]) * g.k_fill * A_w * l_turn / 2)       # two legs' worth of bundle per turn length
    # turns for a target resistance: R = n_r rho N^2 l_turn / (k A_w)
    N = math.sqrt(R_target * g.k_fill * A_w / (n_r * RHO_CU * l_turn))
    return {"A_w_mm2": A_w * 1e6, "l_turn_mm": l_turn * 1e3, "m_cu_g": m_cu * 1e3, "turns_for_R": N, "R_target": R_target}


def km_map(g: ChkGeom, n: int = 5, axis: str = "x", **kw) -> Dict:
    """Km over the stroke grid (dx, dy in [-s, s]^2), the cross-coupling and the variation (CALC)."""
    src = sources(g)
    xs = np.linspace(-g.s, g.s, n)
    Fm = np.zeros((n, n, 3))
    for i, dx in enumerate(xs):
        for j, dy in enumerate(xs):
            Fm[i, j] = layer_force(g, axis, (dx, dy), src, **kw)
    k = 0 if axis == "x" else 1
    other = 1 - k
    F0 = layer_force(g, axis, (0.0, 0.0), src, **kw)
    Km = np.array([[km_from_force(g, abs(Fm[i, j, k]), axis) for j in range(n)] for i in range(n)])
    Km0 = km_from_force(g, abs(F0[k]), axis)
    cross = Fm[:, :, other] / np.maximum(np.abs(Fm[:, :, k]), 1e-12)
    return {"xs_mm": (xs * 1e3).tolist(), "Km_grid": Km.tolist(), "Km0": Km0, "Km_min": float(Km.min()), "Km_max": float(Km.max()),
            "variation": float((Km.max() - Km.min()) / Km0), "cross_max": float(np.abs(cross).max()),
            "Fz_per_AT_max": float(np.abs(Fm[:, :, 2]).max()), "F0_per_AT": F0.tolist(),
            "label": "CALC (magpylib cuboids + iron images: upper bound)"}


def gap_flux(g: ChkGeom, n: int = 7) -> float:
    """Mean |Bz| over the coil layers above the central 60 % of each pole (T), for comparison with nose2's model."""
    src = sources(g)
    zs = np.linspace(g.t_m + g.c0, g.t_m + g.c0 + g.t_x + g.t_y, n)
    vals = []
    for i in (-1, 1):
        for j in (-1, 1):
            u = np.linspace(-0.3 * g.w, 0.3 * g.w, n)
            P = np.array(np.meshgrid(i * g.c + u, j * g.c + u, zs, indexing="ij")).reshape(3, -1).T
            vals.append(np.abs(src.getB(P)[:, 2]))
    return float(np.mean(np.concatenate(vals)))


def nose2_km(g: ChkGeom, wire: float = 0.10e-3) -> Dict:
    """nose2's differentiable axial-topology model for the same geometry (its surrogate eta fit), for comparison."""
    import torch
    from nose2 import designs as ND
    t = lambda x: torch.tensor(float(x), dtype=torch.float64)
    parts = ND.Parts(grade="N52", wire=wire, iron="Hiperco50A", bore="24")
    tc = 0.5 * (g.t_x + g.t_y)
    A = ND.act_unit(parts, "axial", t(g.w), t(g.w), t(g.t_m), t(tc), t(g.s), None, t(0.0), r_hole=t(g.r_hole))
    return {"Km": float(A["Km"]), "B": float(A["B"]), "r_out_mm": float(A["r_out"]) * 1e3, "m_move_g": float(A["m_move"]) * 1e3,
            "m_stat_g": float(A["m_stat"]) * 1e3, "label": "CALC (nose2/designs.act_unit 'axial', read-only)"}


def keeper_pull(g: ChkGeom, n: int = 61) -> Dict:
    """Axial pull between the magnet array (with its back plate) and the keeper: the Maxwell stress B_z^2 / (2 mu0)
    integrated over the keeper face (for an ideal-iron plane the surface field is normal).  In the moving-COIL design both
    are fixed to the handle, so the pull only loads the handle's structure; in a moving-MAGNET design it loads the
    suspension axially.  An infinite ideal plane gives no lateral force (the pressure is normal), so the lateral
    negative stiffness of a moving-magnet array over a large keeper is ~0 to this model's accuracy; edges add some
    (not modelled: EXP-B23 measures it).  CALC, ideal iron (an upper bound)."""
    src = sources(g)
    R = g.r_out + 3e-3
    xs = np.linspace(-R, R, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    P = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, g.D - 1e-7)])
    Bz = src.getB(P)[:, 2]
    dA = (xs[1] - xs[0]) ** 2
    mu0 = 4e-7 * math.pi
    F = float(np.sum(Bz ** 2) * dA / (2 * mu0))
    return {"pull_N": F, "area_mm2": (2 * R) ** 2 * 1e6, "label": "CALC (Maxwell stress on the keeper, magpylib + images)"}
