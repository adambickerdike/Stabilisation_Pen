r"""Fast force maps of the moving-coil checkerboard actuator (CALCULATION; an upper bound, derated where it is used).

The same physics as bnib/magnetics.py and revk/feasibility.winding_map (read-only), written for speed so the optimiser
can afford thousands of designs:

  magnets   four square N52-class poles (side w, thickness t_m) at (+-c, +-c), c = w/2 + e, polarised +-z in a
            checkerboard on an iron back plate at z = 0; an iron keeper at z = D closes the circuit on the far side of the
            coil stack (D = t_m + c0 + copper stack + c1).  Both plates are infinitely permeable planes replaced by
            images (nose2/magnetics._images: mirror across a plane keeps the normal polarisation; +-n_img periods of
            2 D).  Option 'double': a second, identical magnet array on the keeper side (t_m2), same polarity pattern,
            so the flux crosses the gap straight.
  field     only B_z matters for the in-plane force on a flat winding (dF = I dl x B with dl in the plane:
            dF_x = I dl_y B_z, dF_y = -I dl_x B_z).  B_z of a z-polarised cuboid in closed form:
                B_z = J / (4 pi) sum_{i,j,k} (-1)^(i+j+k+1) atan(X_i Y_j / (Z_k R_ijk))
            (X_i = x - x_i etc., corners x_1 < x_2 ...), checked against magpylib's Cuboid in the tests.
  winding   concentric flat racetracks with end turns as wide as the legs (study K's buildable coil, revk/nib.py
            _racetrack_filaments), two per axis layer (one per pole row), the x and y packs split into sublayers in any
            order (xy, xyyx, yxxy, ...), with 0.05 mm of insulation between sublayers taken from the copper (the pass's
            winding_map convention); force per ampere-turn by midpoint quadrature over bundle x thickness x segment.
  Km        N per sqrt(W of copper at 20 degC):  K = F_AT sqrt(k_fill A / (2 rho l_mean)), A the pack's copper
            cross-section across its sublayers, l_mean = 4 (x_in + y_in + b) (turn-count independent).
  map       the 2 x 2 in-plane force matrix [F_x, F_y] per sqrt(W) of the x and y windings at each displacement of the
            coil; its smallest singular value is the weakest force per sqrt(W) in any direction (the pass's criterion).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, Sequence

import numpy as np

try:
    import numba as _nb
except Exception:  # pragma: no cover - numba is in requirements.txt
    _nb = None

RHO_CU = 1.7241e-8          # ohm m at 20 degC (MANUFACTURER AMF-29, as bnib/labels.py)
CU_DENS = 8890.0            # kg/m3 (MANUFACTURER AMF-29)
NDFEB_DENS = 7500.0         # kg/m3 (the pass's and K's value for the pole mass; AMF-139 gives 7.5-7.6 g/cc)
INSULATION = 0.05e-3        # m between sublayers (the pass's winding_map default; ASSUMPTION)


def _bz_kernel_py(P, S):
    out = np.zeros(P.shape[0])
    for m in range(S.shape[0]):
        cx, cy, cz, hx, hy, hz, J = S[m]
        X = (P[:, 0] - cx)[:, None] - np.array([-hx, hx])[None, :]
        Y = (P[:, 1] - cy)[:, None] - np.array([-hy, hy])[None, :]
        Z = (P[:, 2] - cz)[:, None] - np.array([-hz, hz])[None, :]
        acc = np.zeros(P.shape[0])
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    x, y, z = X[:, i], Y[:, j], Z[:, k]
                    r = np.sqrt(x * x + y * y + z * z)
                    sgn = -1.0 if (i + j + k) % 2 == 0 else 1.0
                    acc += sgn * np.arctan(x * y / (z * r))
        out += J / (4 * math.pi) * acc
    return out


if _nb is not None:
    @_nb.njit(cache=True, fastmath=False)
    def _bz_kernel(P, S):  # pragma: no cover - compiled
        n = P.shape[0]
        m = S.shape[0]
        out = np.zeros(n)
        inv4pi = 1.0 / (4.0 * math.pi)
        for a in range(n):
            px = P[a, 0]
            py = P[a, 1]
            pz = P[a, 2]
            s = 0.0
            for b in range(m):
                cx = S[b, 0]
                cy = S[b, 1]
                cz = S[b, 2]
                hx = S[b, 3]
                hy = S[b, 4]
                hz = S[b, 5]
                J = S[b, 6]
                acc = 0.0
                for i in range(2):
                    x = px - cx + (hx if i == 0 else -hx)
                    for j in range(2):
                        y = py - cy + (hy if j == 0 else -hy)
                        for k in range(2):
                            z = pz - cz + (hz if k == 0 else -hz)
                            r = math.sqrt(x * x + y * y + z * z)
                            sgn = -1.0 if (i + j + k) % 2 == 0 else 1.0
                            acc += sgn * math.atan(x * y / (z * r))
                s += J * acc
            out[a] = s * inv4pi
        return out
else:  # pragma: no cover
    _bz_kernel = _bz_kernel_py


def bz(points: np.ndarray, sources: np.ndarray) -> np.ndarray:
    """B_z (T) at points (N x 3, m) of z-polarised cuboids (M x 7: centre xyz, half sides xyz, polarisation J in T)."""
    P = np.ascontiguousarray(points, dtype=np.float64)
    S = np.ascontiguousarray(sources, dtype=np.float64)
    return _bz_kernel(P, S)


# ------------------------------------------------------------------------------------------------ magnet geometry
@dataclass(frozen=True)
class Magnets:
    """Checkerboard stator (m).  e: half the spacing between adjacent poles (the refill/carrier hole)."""
    w: float = 5.12e-3
    e: float = 2.2335e-3
    t_m: float = 3.5e-3
    c0: float = 0.30e-3           # magnet face -> first coil sublayer (running clearance; study B)
    t_cu: float = 1.6e-3          # total copper stack thickness (x + y packs, all sublayers, insulation included)
    c1: float = 0.15e-3           # last sublayer -> keeper (or the second array's face)
    Br: float = 1.42              # T (N52 low end, MANUFACTURER AMF-139)
    double: bool = False          # a second magnet array on the keeper side (same polarity pattern)
    t_m2: float = 0.0             # its thickness

    @property
    def c(self) -> float:
        return 0.5 * self.w + self.e

    @property
    def D(self) -> float:
        return self.t_m + self.c0 + self.t_cu + self.c1 + (self.t_m2 if self.double else 0.0)

    @property
    def r_out(self) -> float:
        """Outer corner radius of the pole array (the plates must reach beyond it)."""
        return math.sqrt(2.0) * (self.c + 0.5 * self.w)

    @property
    def mass_kg(self) -> float:
        return 4 * NDFEB_DENS * self.w * self.w * (self.t_m + (self.t_m2 if self.double else 0.0))


def sources(g: Magnets, n_img: int = 3) -> np.ndarray:
    """The poles and their images between the plates at z = 0 and z = D (as nose2/magnetics._images)."""
    D = g.D
    mags = []
    for i in (-1, 1):
        for j in (-1, 1):
            sgn = 1.0 if i * j > 0 else -1.0
            mags.append((i * g.c, j * g.c, g.t_m / 2, g.t_m / 2, sgn * g.Br))
            if g.double:
                mags.append((i * g.c, j * g.c, D - g.t_m2 / 2, g.t_m2 / 2, sgn * g.Br))
    out = []
    for (x, y, z0, hz, J) in mags:
        for k in range(-n_img, n_img + 1):
            out.append((x, y, z0 + 2 * k * D, g.w / 2, g.w / 2, hz, J))
            out.append((x, y, -z0 + 2 * k * D, g.w / 2, g.w / 2, hz, J))
    return np.array(out, dtype=np.float64)


# ------------------------------------------------------------------------------------------------ winding
@dataclass(frozen=True)
class Coil:
    """Concentric racetrack pair of each axis layer (m): turns from (x_in, y_in) to (x_in + b, y_in + b), centred at
    (0, +-yc) for the x layer (legs along y over the poles) and rotated 90 deg for the y layer."""
    x_in: float
    y_in: float
    b: float
    yc: float
    order: str = "xy"             # sublayer order from the magnets outward
    k_fill: float = 0.55          # copper fill of the pack (ASSUMPTION: bonded round wire 0.55, study B / K)

    @property
    def outer_radius(self) -> float:
        return math.hypot(self.x_in + self.b, self.yc + self.y_in + self.b)

    @property
    def inner_edge(self) -> float:
        return self.yc - self.y_in - self.b

    @property
    def l_mean(self) -> float:
        return 4.0 * (self.x_in + self.y_in + self.b)


def _racetrack_points(coil: Coil, axis: str, z_lo: float, t: float, nb: int, nt: int, nl: int):
    """Midpoints, dl and weights of the filaments of one sublayer of one axis (both racetracks)."""
    f = (np.arange(nb) + 0.5) / nb
    X = coil.x_in + f * coil.b                     # (nb,)
    Y = coil.y_in + f * coil.b
    zz = z_lo + (np.arange(nt) + 0.5) / nt * t      # (nt,)
    u = (np.arange(nl) + 0.5) / nl                  # (nl,)
    pts, dls = [], []
    for row in (-1.0, 1.0):
        cur = row                                   # the racetrack at -yc carries the reversed current
        yc = row * coil.yc
        for (x0, y0, x1, y1) in (("X", "-Y", "X", "+Y"), ("X", "+Y", "-X", "+Y"), ("-X", "+Y", "-X", "-Y"),
                                 ("-X", "-Y", "X", "-Y")):
            def val(tok, arrX, arrY):
                s = -1.0 if tok[0] == "-" else 1.0
                return s * (arrX if tok[-1] == "X" else arrY)
            ax0 = val(x0, X, Y); ay0 = yc + val(y0, X, Y)
            ax1 = val(x1, X, Y); ay1 = yc + val(y1, X, Y)
            # broadcast bundle (nb) x thickness (nt) x pieces (nl)
            px = ax0[:, None, None] + (ax1 - ax0)[:, None, None] * u[None, None, :]
            py = ay0[:, None, None] + (ay1 - ay0)[:, None, None] * u[None, None, :]
            pz = np.broadcast_to(zz[None, :, None], (nb, nt, nl))
            px = np.broadcast_to(px, (nb, nt, nl)); py = np.broadcast_to(py, (nb, nt, nl))
            dx = np.broadcast_to(((ax1 - ax0) / nl * cur)[:, None, None], (nb, nt, nl))
            dy = np.broadcast_to(((ay1 - ay0) / nl * cur)[:, None, None], (nb, nt, nl))
            pts.append(np.stack([px.ravel(), py.ravel(), pz.ravel()], 1))
            dls.append(np.stack([dx.ravel(), dy.ravel()], 1))
    P = np.concatenate(pts)
    dl = np.concatenate(dls)
    if axis == "y":
        P = P[:, [1, 0, 2]]
        dl = dl[:, [1, 0]]
    w = np.full(len(P), 1.0 / (nb * nt))
    return P, dl, w


def sublayer_z(g: Magnets, coil: Coil):
    n = len(coil.order)
    active = (g.t_cu - (n - 1) * INSULATION) / n
    z = [g.t_m + g.c0 + i * (active + INSULATION) for i in range(n)]
    return active, z


def force_map(g: Magnets, coil: Coil, positions: np.ndarray, quad=(3, 2, 12), field_scale: float = 1.0,
              n_img: int = 3) -> Dict:
    """In-plane force matrix per sqrt(W) (20 degC copper) at each coil displacement (positions: N x 2, m)."""
    positions = np.asarray(positions, float).reshape(-1, 2)
    order = coil.order
    if set(order) != {"x", "y"} or order.count("x") != order.count("y"):
        raise ValueError("equal numbers of x and y sublayers required")
    active, zs = sublayer_z(g, coil)
    if active <= 0:
        raise ValueError("no copper left after insulation")
    S = sources(g, n_img)
    nb, nt, nl = quad
    npos = len(positions)
    K = np.zeros((npos, 2, 2))
    for j, axis in enumerate(("x", "y")):
        subs = [i for i, ch in enumerate(order) if ch == axis]
        Fx = np.zeros(npos)
        Fy = np.zeros(npos)
        for li in subs:
            P, dl, w = _racetrack_points(coil, axis, zs[li], active, nb, nt, nl)
            allP = np.repeat(P[None, :, :], npos, axis=0).copy()
            allP[:, :, 0] += positions[:, 0:1]
            allP[:, :, 1] += positions[:, 1:2]
            B = bz(allP.reshape(-1, 3), S).reshape(npos, -1) * field_scale
            Fx += (B * (dl[:, 1] * w)[None, :]).sum(axis=1) / len(subs)
            Fy += (-B * (dl[:, 0] * w)[None, :]).sum(axis=1) / len(subs)
        area = coil.b * active * len(subs)
        norm = math.sqrt(coil.k_fill * area / (2.0 * RHO_CU * coil.l_mean))
        sign = 1.0 if axis == "x" else -1.0
        K[:, 0, j] = sign * Fx * norm
        K[:, 1, j] = sign * Fy * norm
    sv = np.linalg.svd(K, compute_uv=False)
    area_axis = coil.b * active * (len(order) // 2)
    m_cu = 2 * 2 * CU_DENS * coil.k_fill * area_axis * coil.l_mean      # two axes x two racetracks
    return {"positions_m": positions, "K": K, "sv_min": sv[:, -1], "sv_max": sv[:, 0], "active_m": active,
            "copper_mass_kg": m_cu, "label": "CALCULATION (analytic cuboid B_z + ideal-iron images; upper bound)"}


def disk_positions(radius: float, n_ang: int = 8, rings=(0.5, 1.0)) -> np.ndarray:
    """Centre plus rings of n_ang points (the pass's disk_samples(radius, n) is rings=(0.5, 1.0))."""
    a = np.arange(n_ang) * 2 * math.pi / n_ang
    ring = np.column_stack([np.cos(a), np.sin(a)])
    return np.vstack([np.zeros((1, 2))] + [ring * radius * r for r in rings])


def coil_resistance(coil: Coil, g: Magnets, n_turns_per_racetrack: float) -> float:
    active, _ = sublayer_z(g, coil)
    A = coil.b * active * (len(coil.order) // 2)
    return 2 * RHO_CU * n_turns_per_racetrack ** 2 * coil.l_mean / (coil.k_fill * A)


def turns_for_R(coil: Coil, g: Magnets, R: float) -> float:
    active, _ = sublayer_z(g, coil)
    A = coil.b * active * (len(coil.order) // 2)
    return math.sqrt(R * coil.k_fill * A / (2 * RHO_CU * coil.l_mean))


def summary(fm: Dict, field_scale: float = 1.0) -> Dict:
    K0 = fm["K"][0]
    return {"Km_centre_x_N_sqrtW": float(abs(K0[0, 0])) * field_scale, "Km_centre_y_N_sqrtW": float(abs(K0[1, 1])) * field_scale,
            "sv_min_centre_N_sqrtW": float(fm["sv_min"][0]) * field_scale,
            "sv_min_workspace_N_sqrtW": float(fm["sv_min"].min()) * field_scale,
            "cross_coupling_max": float(np.max(np.abs(fm["K"][:, 1, 0]) / np.maximum(np.abs(fm["K"][:, 0, 0]), 1e-12))),
            "copper_mass_g": fm["copper_mass_kg"] * 1e3, "field_scale": field_scale}
