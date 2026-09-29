#!/usr/bin/env python3
"""Shared helpers for the study-M measurement-rig CAD scripts (mechanics/cad/rig_*.py).

Evidence status: PROPOSED DESIGN.  Geometry helpers, flexure formulas (CALC), mass roll-ups (densities are
ASSUMPTIONS, listed in RHO), clearance checks and a projected-edge drawing routine that draws the CAD solids
themselves (so the drawings cannot drift from the STEP files).

Frames.  Page frame: paper surface z = 0, x along the rig's long axis, z up.  Pen frame (local): ball at the
origin, pen axis +Z toward the cap.  tilt(wp, theta) turns the local frame so that the axis points up at
altitude theta toward -x (the same convention as mechanics/cad/bench_rig.py).

Outputs of every rig script go to results/rig/cad/: <name>_assembly.step, drawing_<name>.png,
<name>_summary.json (with stabpen.provenance metadata).
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, Iterable

import numpy as np
import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "rig", "cad")

E_STEEL = 200e9      # Pa, spring steel (ASSUMPTION: 190-210 GPa class)
E_TI = 110e9         # Pa (ASSUMPTION)
# densities in g/cm^3 (ASSUMPTION, handbook class values)
RHO = {"al": 2.70, "steel": 7.85, "print": 1.25, "cfrp": 1.55, "tungsten": 19.0, "brass": 8.50, "glass": 2.50,
       "silicone": 1.10, "peek": 1.30, "pcb": 1.85, "copper": 8.96, "ndfeb": 7.50}


# ------------------------------------------------------------------------------------------------ solids
def cyl(d: float, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).circle(d / 2).extrude(z1 - z0)


def tube(od: float, idd: float, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).circle(od / 2).circle(idd / 2).extrude(z1 - z0)


def box(sx: float, sy: float, sz: float, c=(0.0, 0.0, 0.0)) -> cq.Workplane:
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)


def cone(r0: float, r1: float, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").add(cq.Solid.makeCone(r0, r1, z1 - z0, pnt=cq.Vector(0, 0, z0), dir=cq.Vector(0, 0, 1)))


def sector_xz(r_in: float, r_out: float, a0: float, a1: float, t: float, y0: float) -> cq.Workplane:
    """Annular sector in the x-z plane, centred on the origin, angles in degrees measured from -x toward +z
    (the altitude convention), thickness t from y = y0 to y0 + t."""
    a0r, a1r, am = math.radians(a0), math.radians(a1), math.radians(0.5 * (a0 + a1))

    def p(r, a):
        return (-r * math.cos(a), r * math.sin(a))

    w = (cq.Workplane("XZ").moveTo(*p(r_in, a0r)).lineTo(*p(r_out, a0r)).threePointArc(p(r_out, am), p(r_out, a1r))
         .lineTo(*p(r_in, a1r)).threePointArc(p(r_in, am), p(r_in, a0r)).close().extrude(-t))
    # Workplane("XZ") normal is -y; extrude(-t) goes toward +y from y = 0
    return w.translate((0, y0, 0))


def tilt(wp: cq.Workplane, theta_deg: float, about=(0.0, 0.0, 0.0)) -> cq.Workplane:
    """Local pen frame (axis +Z) -> page frame, axis up at altitude theta toward -x, turning about `about`."""
    return wp.rotate(about, (about[0], about[1] + 1.0, about[2]), theta_deg - 90.0)


def roll(wp: cq.Workplane, roll_deg: float) -> cq.Workplane:
    """Rotate about the local pen axis (apply before tilt)."""
    return wp.rotate((0, 0, 0), (0, 0, 1), roll_deg)


def yaw(wp: cq.Workplane, deg: float) -> cq.Workplane:
    return wp.rotate((0, 0, 0), (0, 0, 1), deg)


# ------------------------------------------------------------------------------------------------ CALC helpers
def leaf_k(b: float, t: float, L: float, E: float = E_STEEL) -> float:
    """Transverse stiffness of one fixed-guided leaf (N/m): E b t^3 / L^3 (= 12 E I / L^3)."""
    return E * b * t ** 3 / L ** 3


def leaf_stress(t: float, d: float, L: float, E: float = E_STEEL) -> float:
    """Peak bending stress (Pa) of a fixed-guided leaf at transverse deflection d: 3 E t d / L^2."""
    return 3.0 * E * t * d / L ** 2


def leaf_buckling(b: float, t: float, L: float, E: float = E_STEEL) -> float:
    """Euler load (N) of one leaf, both ends clamped with sidesway (K = 1): pi^2 E I / L^2."""
    return math.pi ** 2 * E * (b * t ** 3 / 12.0) / L ** 2


def leaf_shortening(d: float, L: float) -> float:
    """Parasitic axial motion (m) of a parallel-leaf stage at transverse deflection d: 0.6 d^2 / L."""
    return 0.6 * d * d / L


def cross_pivot_k(b: float, t: float, L: float, n: int = 2, E: float = E_STEEL) -> float:
    """Small-angle rotational stiffness (N m/rad) of n strips of length L crossing at their midpoints, no axial load:
    each strip needs M = E I theta / L (fixed-guided beam relations with the tip displaced theta L / 2)."""
    return n * E * (b * t ** 3 / 12.0) / L


def mode_hz(k: float, m: float) -> float:
    return math.sqrt(k / m) / (2 * math.pi)


def volume_mm3(wp: cq.Workplane) -> float:
    return float(sum(v.Volume() for v in wp.vals() if hasattr(v, "Volume")))


def mass_g(wp: cq.Workplane, material: str) -> float:
    return volume_mm3(wp) * RHO[material] / 1000.0


def overlap_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        inter = a.intersect(b)
        return float(sum(v.Volume() for v in inter.vals() if hasattr(v, "Volume")))
    except Exception:            # noqa: BLE001 - OCC can refuse degenerate booleans; report as unknown
        return float("nan")


class _BB:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax = xmin, ymin, zmin, xmax, ymax, zmax


def bbox(wp: cq.Workplane) -> _BB:
    """Tight (optimal) axis-aligned bounding box of the solids in wp."""
    comp = cq.Compound.makeCompound([v for v in wp.vals() if isinstance(v, cq.Shape)])
    try:
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        b = Bnd_Box()
        BRepBndLib.AddOptimal_s(comp.wrapped, b, False, False)
        return _BB(*b.Get())
    except Exception:            # noqa: BLE001 - fall back to a fine tessellation
        pts = np.array([tuple(v) for v in comp.tessellate(0.005)[0]])
        return _BB(*pts.min(axis=0), *pts.max(axis=0))


def zmin(wp: cq.Workplane) -> float:
    return float(bbox(wp).zmin)


def pair_clearances(moving: Dict[str, cq.Workplane], fixed: Dict[str, cq.Workplane], skip: Iterable = ()) -> list:
    """Overlap volumes between every moving part and every fixed part (report only overlaps > 1e-6 mm^3)."""
    rows = []
    bf = {k: bbox(v) for k, v in fixed.items()}
    for km, vm in moving.items():
        if km in skip:
            continue
        bm = bbox(vm)
        for kf, vf in fixed.items():
            b = bf[kf]
            if (bm.xmin > b.xmax or bm.xmax < b.xmin or bm.ymin > b.ymax or bm.ymax < b.ymin
                    or bm.zmin > b.zmax or bm.zmax < b.zmin):
                continue                      # boxes apart: no overlap possible
            v = overlap_mm3(vm, vf)
            if not (v <= 1e-6):
                rows.append({"part": km, "against": kf, "overlap_mm3": round(v, 4)})
    return rows


# ------------------------------------------------------------------------------------------------ output
def save_assembly(name: str, parts: Dict[str, cq.Workplane], colors: Dict[str, str] = None) -> str:
    os.makedirs(OUT, exist_ok=True)
    asm = cq.Assembly(name=name)
    for k, v in parts.items():
        c = (colors or {}).get(k)
        asm.add(v, name=k, color=cq.Color(c) if c else None)
    path = os.path.join(OUT, f"{name}_assembly.step")
    asm.save(path)
    return path


def write_summary(name: str, status: str, summary: dict) -> str:
    os.makedirs(OUT, exist_ok=True)
    meta = provenance.metadata(status, extra={"cadquery": cq.__version__, "script": f"mechanics/cad/{name}.py"})
    path = os.path.join(OUT, f"{name}_summary.json")
    provenance.write_json(path, {"meta": meta, "summary": summary})
    return path


def _edge_points(e, n: int = 24) -> np.ndarray:
    try:
        if e.geomType() == "LINE":
            ts = (0.0, 1.0)
        else:
            ts = np.linspace(0.0, 1.0, n)
        return np.array([tuple(e.positionAt(t)) for t in ts])
    except Exception:            # noqa: BLE001
        return np.zeros((0, 3))


_VIEWS = {  # plane -> (view normal N, drawing x direction); drawing y = N x Xdir
    "xz": ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0)),     # side view, looking from -y: x right, z up
    "xy": ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),      # top view: x right, y up
    "yz": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),      # end view from +x: y right, z up
}


def _hlr_edges(shape, plane: str):
    """Hidden-line projection (OCC HLRBRep): returns (visible, hidden) lists of 2-D polylines, silhouettes included."""
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    n, xd = _VIEWS[plane]
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xd))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    out = []
    for group in ((h.VCompound(), h.Rg1LineVCompound(), h.OutLineVCompound()), (h.HCompound(), h.OutLineHCompound())):
        lines = []
        for comp in group:
            if comp is None or comp.IsNull():
                continue
            for e in cq.Shape.cast(comp).Edges():
                p = _edge_points(e)
                if len(p):
                    lines.append(p[:, :2])
        out.append(lines)
    return out[0], out[1]


def project(ax, wp: cq.Workplane, plane: str = "xz", color="#52514e", lw: float = 0.6, n: int = 24, alpha: float = 1.0,
            hidden: bool = False):
    """Draw the solids in `wp` projected on `plane` ('xz', 'xy' or 'yz') with hidden-line removal per part
    (outlines and silhouettes of curved faces included).  Falls back to raw edge projection if HLR fails."""
    for v in wp.vals():
        if not isinstance(v, cq.Shape):
            continue
        try:
            vis, hid = _hlr_edges(v, plane)
        except Exception:        # noqa: BLE001
            i, j = {"xz": (0, 2), "xy": (0, 1), "yz": (1, 2)}[plane]
            vis = [(_edge_points(e, n)[:, [i, j]]) for e in v.Edges()]
            hid = []
        for p in vis:
            if len(p):
                ax.plot(p[:, 0], p[:, 1], color=color, lw=lw, alpha=alpha, solid_capstyle="round")
        if hidden:
            for p in hid:
                if len(p):
                    ax.plot(p[:, 0], p[:, 1], color=color, lw=0.35 * lw, alpha=0.5 * alpha, ls=(0, (2, 2)))


def dim(ax, p0, p1, text: str, off: float = 0.0, color="#0b0b0b", fs: float = 7.5, text_off: float = 2.0):
    """Linear dimension between p0 and p1 offset perpendicular by `off` (drawing units)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.hypot(*d)) or 1.0
    nrm = np.array([-d[1], d[0]]) / L
    a, b = p0 + off * nrm, p1 + off * nrm
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<->", color=color, lw=0.7, shrinkA=0, shrinkB=0))
    if off:
        for p, q in ((p0, a), (p1, b)):
            ax.plot([p[0], q[0] + 0.15 * off * nrm[0]], [p[1], q[1] + 0.15 * off * nrm[1]], color=color, lw=0.4)
    m = 0.5 * (a + b) + text_off * nrm
    ang = math.degrees(math.atan2(d[1], d[0]))
    if ang > 90:
        ang -= 180
    if ang < -90:
        ang += 180
    ax.text(m[0], m[1], text, fontsize=fs, color=color, rotation=ang, rotation_mode="anchor", ha="center", va="bottom")


def label(ax, xy, text, xytext, fs: float = 7.5):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fs, color="#0b0b0b",
                arrowprops=dict(arrowstyle="-", color="#898781", lw=0.6))


def new_figure(ncols: int = 2, size=(12.5, 6.2), width_ratios=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from stabpen import plotstyle
    plotstyle.apply()
    fig, axs = plt.subplots(1, ncols, figsize=size, gridspec_kw={"width_ratios": width_ratios} if width_ratios else None)
    for ax in np.atleast_1d(axs):
        ax.set_aspect("equal")
        ax.grid(False)
    return fig, axs


def finish(fig, path: str, extra: str):
    from stabpen import plotstyle
    plotstyle.stamp(fig, "proposed design", extra)
    fig.tight_layout()
    fig.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path
