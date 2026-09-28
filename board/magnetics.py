"""Magnetic force between the board's head and the pen magnet (CALC, magpylib 5.2).

Local frame for all maps: z = 0 on the top of the paper (where the ball
writes), z up; the pen magnet centre sits above the paper; the head magnet
top face is at z = -gap.  ``offset`` = head axis position minus the pen-magnet
centre, in the paper plane.

The force is computed with ``magpylib.getFT`` (meshed target, finite-difference
field gradient).  ``dipole_force`` gives the analytic point-dipole force used
by the tests as an independent cross-check at large separation.

Options modelled
----------------
axial PM head     permanent magnet, axis vertical (baseline, K&J D88-N52)
diametric head    permanent magnet magnetised across its axis, rotated by a
                  motor to point the force (variant; K&J D8X0DIA)
coil heads        air-core coils (electromagnet cross head, PCB coil array);
                  force per ampere and per square-root watt
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import magpylib as magpy
from scipy.spatial.transform import Rotation as Rot

from . import params as P

MM = 1e-3
RHO_CU = 1.7241e-8  # ohm m at 20 C (AMF-29)


# ----------------------------------------------------------------------------- geometry
def pen_axis(alt_deg: float, az_deg: float) -> np.ndarray:
    """Unit vector from the ball toward the pen's rear."""
    a, z = math.radians(alt_deg), math.radians(az_deg)
    return np.array([math.cos(a) * math.cos(z), math.cos(a) * math.sin(z), math.sin(a)])


@dataclass
class PenMagnet:
    """The pen add-on magnet (disc), magnetised along the pen axis."""
    d_mm: float = P.PEN["pen_magnet_d_mm"].value
    h_mm: float = P.PEN["pen_magnet_h_mm"].value
    Br_T: float = P.PEN["pen_magnet_Br_T"].value
    height_mm: float = P.PEN["pen_magnet_height_mm"].value      # centre above the paper
    behind_mm: float = P.PEN["pen_magnet_behind_ball_mm"].value  # horizontal, along the azimuth
    alt_deg: float = P.PEN["alt_deg"].value
    az_deg: float = P.PEN["az_deg"].value
    axis: str = "pen"          # "pen": along the pen axis; "vertical": axis vertical
    ring_id_mm: float = 0.0    # > 0 makes it a ring
    mesh: int = 100

    def direction(self) -> np.ndarray:
        if self.axis == "vertical":
            return np.array([0.0, 0.0, 1.0])
        return pen_axis(self.alt_deg, self.az_deg)

    def centre_mm(self) -> np.ndarray:
        """Centre relative to the ball contact point (x, y) and the paper (z)."""
        z = math.radians(self.az_deg)
        return np.array([self.behind_mm * math.cos(z), self.behind_mm * math.sin(z), self.height_mm])

    def volume_m3(self) -> float:
        return math.pi / 4 * (self.d_mm ** 2 - self.ring_id_mm ** 2) * self.h_mm * 1e-9

    def moment_Am2(self) -> float:
        return self.Br_T * self.volume_m3() / P.MU0

    def build(self, centre_mm=None):
        c = self.centre_mm() if centre_mm is None else np.asarray(centre_mm, float)
        if self.ring_id_mm > 0:
            obj = magpy.magnet.CylinderSegment(
                dimension=(self.ring_id_mm / 2 * MM, self.d_mm / 2 * MM, self.h_mm * MM, 0, 360),
                polarization=(0, 0, self.Br_T), meshing=self.mesh)
        else:
            obj = magpy.magnet.Cylinder(dimension=(self.d_mm * MM, self.h_mm * MM),
                                        polarization=(0, 0, self.Br_T), meshing=self.mesh)
        u = self.direction()
        if not np.allclose(u, [0, 0, 1]):
            obj.orientation = Rot.align_vectors([u], [[0, 0, 1]])[0]
        obj.position = c * MM
        return obj


@dataclass
class Head:
    """Permanent-magnet head: a cylinder under the glass."""
    d_mm: float = P.HEAD["head_d_mm"].value
    h_mm: float = P.HEAD["head_h_mm"].value
    Br_T: float = P.HEAD["head_Br_T"].value
    magnetisation: str = "axial"   # or "diametric"
    angle_deg: float = 0.0          # direction of a diametric magnetisation in the paper plane

    def moment_Am2(self) -> float:
        return self.Br_T * math.pi / 4 * self.d_mm ** 2 * self.h_mm * 1e-9 / P.MU0

    def build(self):
        if self.magnetisation == "axial":
            pol = (0.0, 0.0, self.Br_T)
        else:
            a = math.radians(self.angle_deg)
            pol = (self.Br_T * math.cos(a), self.Br_T * math.sin(a), 0.0)
        return magpy.magnet.Cylinder(dimension=(self.d_mm * MM, self.h_mm * MM), polarization=pol)


# ----------------------------------------------------------------------------- force maps
def offset_grid(half_mm: float = 16.0, step_mm: float = 1.0) -> np.ndarray:
    xs = np.arange(-half_mm, half_mm + 1e-9, step_mm)
    X, Y = np.meshgrid(xs, xs, indexing="xy")
    return np.stack([X.ravel(), Y.ravel()], 1)


def force_at_offsets(head: Head, pen: PenMagnet, gap_mm: float, offsets_mm: np.ndarray,
                     pen_centre_mm=None) -> np.ndarray:
    """Force on the pen magnet (N, shape (n, 3)) for head-axis offsets (mm) from the pen-magnet centre."""
    pm = pen.build(pen_centre_mm)
    c = np.asarray(pm.position) / MM
    src = head.build()
    offs = np.atleast_2d(offsets_mm)
    pos = np.stack([c[0] + offs[:, 0], c[1] + offs[:, 1],
                    np.full(len(offs), -gap_mm - head.h_mm / 2)], 1) * MM
    src.position = pos
    F, _ = magpy.getFT(src, pm)
    return np.asarray(F).reshape(len(offs), 3)


def lateral_capability(F: np.ndarray, offsets: np.ndarray, n_dir: int = 36, tol_rel: float = 0.05,
                       tol_abs: float = 0.01) -> dict:
    """Best force along each paper-plane direction, with a small sideways component.

    Returns the isotropic capability (the weakest direction), the best
    direction, and the normal force (negative = pulls the pen down) at the
    chosen offsets.
    """
    th = np.radians(np.arange(0, 360, 360 / n_dir))
    best, fz, off_used = [], [], []
    for a in th:
        e = np.array([math.cos(a), math.sin(a)])
        par = F[:, 0] * e[0] + F[:, 1] * e[1]
        perp = np.abs(-F[:, 0] * e[1] + F[:, 1] * e[0])
        ok = perp <= tol_rel * np.maximum(par, 1e-12) + tol_abs
        v = np.where(ok, par, -np.inf)
        k = int(np.argmax(v))
        best.append(float(v[k]))
        fz.append(float(F[k, 2]))
        off_used.append(offsets[k].tolist())
    best = np.array(best)
    Fl = np.hypot(F[:, 0], F[:, 1])
    i0 = int(np.argmin(Fl + 10.0 * (np.hypot(offsets[:, 0], offsets[:, 1]) > 8.0)))
    return {
        "lateral_isotropic_N": float(best.min()),
        "lateral_best_direction_N": float(best.max()),
        "lateral_mean_over_directions_N": float(best.mean()),
        "normal_at_best_N": [float(min(fz)), float(max(fz))],
        "offset_for_best_mm": [float(np.hypot(*o)) for o in off_used],
        "zero_lateral_offset_mm": offsets[i0].tolist(),
        "normal_at_zero_lateral_N": float(F[i0, 2]),
        "max_normal_pull_N": float(-F[:, 2].min()),
        "per_direction_N": best.tolist(),
    }


def stiffness_at_zero(head: Head, pen: PenMagnet, gap_mm: float, zero_offset_mm, h: float = 0.5) -> float:
    """Slope of the lateral force against head offset near the zero-force point (N/mm), mean of x and y."""
    z0 = np.asarray(zero_offset_mm, float)
    offs = np.array([z0 + [h, 0], z0 - [h, 0], z0 + [0, h], z0 - [0, h]])
    F = force_at_offsets(head, pen, gap_mm, offs)
    kx = (F[0, 0] - F[1, 0]) / (2 * h)
    ky = (F[2, 1] - F[3, 1]) / (2 * h)
    return float(0.5 * (kx + ky))


def force_vs_gap(gaps_mm, head: Head = None, pen: PenMagnet = None, half_mm: float = 16.0,
                 step_mm: float = 1.0) -> list:
    head = head or Head()
    pen = pen or PenMagnet()
    offs = offset_grid(half_mm, step_mm)
    rows = []
    for g in gaps_mm:
        F = force_at_offsets(head, pen, g, offs)
        cap = lateral_capability(F, offs)
        k = stiffness_at_zero(head, pen, g, cap["zero_lateral_offset_mm"])
        rows.append({"gap_mm": float(g), **{k2: v for k2, v in cap.items() if k2 != "per_direction_N"},
                     "slope_at_zero_N_per_mm": k})
    return rows


def diametric_force_vs_gap(gaps_mm, pen: PenMagnet = None, head: Head = None) -> list:
    """Diametric head centred under the pen magnet, pointed across and along the pen azimuth."""
    pen = pen or PenMagnet()
    rows = []
    for g in gaps_mm:
        out = {"gap_mm": float(g)}
        for name, ang in (("across_azimuth", pen.az_deg + 90.0), ("along_azimuth", pen.az_deg)):
            h = head or Head(d_mm=P.HEAD["diam_head_d_mm"].value, h_mm=P.HEAD["diam_head_h_mm"].value,
                             Br_T=P.HEAD["diam_head_Br_T"].value, magnetisation="diametric")
            h = Head(d_mm=h.d_mm, h_mm=h.h_mm, Br_T=h.Br_T, magnetisation="diametric", angle_deg=ang)
            F = force_at_offsets(h, pen, g, np.zeros((1, 2)))[0]
            out[f"{name}_lateral_N"] = float(math.hypot(F[0], F[1]))
            out[f"{name}_normal_N"] = float(F[2])
        rows.append(out)
    return rows


def full_map(gap_mm: float, head: Head = None, pen: PenMagnet = None, half_mm: float = 16.0, step_mm: float = 1.0):
    head = head or Head()
    pen = pen or PenMagnet()
    offs = offset_grid(half_mm, step_mm)
    return offs, force_at_offsets(head, pen, gap_mm, offs)


# ----------------------------------------------------------------------------- analytic cross-check
def dipole_force(m1, r1, m2, r2) -> np.ndarray:
    """Force on dipole 2 (at r2, moment m2) from dipole 1 (SI units)."""
    m1, r1, m2, r2 = map(lambda a: np.asarray(a, float), (m1, r1, m2, r2))
    r = r2 - r1
    d = np.linalg.norm(r)
    rh = r / d
    return (3 * P.MU0 / (4 * math.pi * d ** 4)) * (
        np.dot(m1, rh) * m2 + np.dot(m2, rh) * m1 + np.dot(m1, m2) * rh - 5 * np.dot(m1, rh) * np.dot(m2, rh) * rh)


# ----------------------------------------------------------------------------- coils
@dataclass
class Coil:
    """Air-core coil as concentric circular turns in layers (planar spiral approximation)."""
    r_in_mm: float
    r_out_mm: float
    turns_per_layer: int
    layers: int
    layer_pitch_mm: float
    z_top_mm: float                  # z of the top layer (local frame, paper top = 0)
    xy_mm: tuple = (0.0, 0.0)
    wire_area_mm2: float = 0.0105    # copper cross-section of one turn
    sign: float = 1.0

    def resistance_ohm(self, temp_C: float = 20.0) -> float:
        r = np.linspace(self.r_in_mm, self.r_out_mm, self.turns_per_layer)
        length_m = 2 * math.pi * r.sum() * self.layers * MM
        rho = RHO_CU * (1 + 0.00393 * (temp_C - 20.0))
        return rho * length_m / (self.wire_area_mm2 * 1e-6)

    def build(self, current_A: float = 1.0):
        col = magpy.Collection()
        radii = np.linspace(self.r_in_mm, self.r_out_mm, self.turns_per_layer)
        for L in range(self.layers):
            z = self.z_top_mm - L * self.layer_pitch_mm
            for r in radii:
                col.add(magpy.current.Circle(current=self.sign * current_A, diameter=2 * r * MM,
                                             position=(self.xy_mm[0] * MM, self.xy_mm[1] * MM, z * MM)))
        return col


def coil_force(coils, pen: PenMagnet, pen_centre_mm, current_A: float = 1.0) -> np.ndarray:
    pm = pen.build(pen_centre_mm)
    F = np.zeros(3)
    for c in coils:
        f, _ = magpy.getFT(c.build(current_A), pm)
        F += np.asarray(f).reshape(-1, 3).sum(0)
    return F


def pcb_array_km(gap_to_copper_mm: float, pitch_mm: float = 12.0, layers: int = 6, turns: int = 16,
                 trace_w_mm: float = 0.15, cu_um: float = 70.0, layer_pitch_mm: float = 0.3,
                 pen: PenMagnet = None, n_pos: int = 7) -> dict:
    """Best lateral force per square-root watt from a pair of adjacent PCB coils driven in anti-phase.

    The pen magnet is moved across the pair; the best position is reported.
    """
    pen = pen or PenMagnet(mesh=60)
    r_out = pitch_mm / 2 - 0.3
    r_in = r_out - turns * 2 * trace_w_mm
    common = dict(r_in_mm=max(r_in, 0.3), r_out_mm=r_out, turns_per_layer=turns, layers=layers,
                  layer_pitch_mm=layer_pitch_mm, z_top_mm=-gap_to_copper_mm,
                  wire_area_mm2=trace_w_mm * cu_um * 1e-3)
    a = Coil(xy_mm=(-pitch_mm / 2, 0.0), sign=+1.0, **common)
    b = Coil(xy_mm=(+pitch_mm / 2, 0.0), sign=-1.0, **common)
    R = a.resistance_ohm(60.0) + b.resistance_ohm(60.0)
    best = None
    c0 = pen.centre_mm()
    for x in np.linspace(-pitch_mm / 2, pitch_mm / 2, n_pos):
        cm = np.array([x, 0.0, c0[2]])
        F = coil_force([a, b], pen, cm, 1.0)
        fl = math.hypot(F[0], F[1])
        if best is None or fl > best[0]:
            best = (fl, F, x)
    fl, F, x = best
    return {"gap_to_copper_mm": gap_to_copper_mm, "pitch_mm": pitch_mm, "layers": layers, "turns_per_layer": turns,
            "resistance_pair_ohm_60C": R, "lateral_N_per_A": fl, "normal_N_per_A": float(F[2]),
            "km_N_per_sqrtW": fl / math.sqrt(R), "best_pen_x_mm": float(x)}


def em_cross_head_km(gap_mm: float, coil_od_mm: float = 12.0, coil_id_mm: float = 3.0, coil_h_mm: float = 10.0,
                     fill: float = 0.6, wire_d_mm: float = 0.3, spacing_mm: float = 14.0,
                     pen: PenMagnet = None) -> dict:
    """Air-core 'cross head' on the carriage: a pair of vertical-axis coils in anti-phase per axis.

    The pen magnet sits above the midpoint (the carriage follows it).  Iron
    cores would raise the force per watt; that factor is not computed here.
    """
    pen = pen or PenMagnet(mesh=60)
    area = (coil_od_mm - coil_id_mm) / 2 * coil_h_mm * fill
    a_w = math.pi / 4 * wire_d_mm ** 2
    n_total = int(area / a_w)
    layers = max(2, int(round(coil_h_mm / (wire_d_mm * 1.1))))
    tpl = max(2, n_total // layers)
    common = dict(r_in_mm=coil_id_mm / 2, r_out_mm=coil_od_mm / 2, turns_per_layer=tpl, layers=layers,
                  layer_pitch_mm=coil_h_mm / layers, z_top_mm=-gap_mm, wire_area_mm2=a_w)
    a = Coil(xy_mm=(-spacing_mm / 2, 0.0), sign=+1.0, **common)
    b = Coil(xy_mm=(+spacing_mm / 2, 0.0), sign=-1.0, **common)
    R = a.resistance_ohm(60.0) + b.resistance_ohm(60.0)
    c0 = pen.centre_mm()
    F = coil_force([a, b], pen, np.array([0.0, 0.0, c0[2]]), 1.0)
    fl = math.hypot(F[0], F[1])
    return {"gap_mm": gap_mm, "turns_per_coil": tpl * layers, "resistance_pair_ohm_60C": R,
            "lateral_N_per_A": fl, "normal_N_per_A": float(F[2]), "km_N_per_sqrtW": fl / math.sqrt(R)}


def power_for_force(force_N: float, km: float) -> float:
    return (force_N / km) ** 2 if km > 0 else float("inf")


def head_field_at(points_mm: np.ndarray, gap_mm: float, head: Head = None) -> np.ndarray:
    """Head-magnet flux density (T) at points (mm, local frame)."""
    head = head or Head()
    src = head.build()
    src.position = (0.0, 0.0, (-gap_mm - head.h_mm / 2) * MM)
    return np.asarray(src.getB(np.asarray(points_mm) * MM))


def pen_field_at(points_mm: np.ndarray, pen: PenMagnet, centre_mm) -> np.ndarray:
    pm = pen.build(centre_mm)
    return np.asarray(pm.getB(np.asarray(points_mm) * MM))
