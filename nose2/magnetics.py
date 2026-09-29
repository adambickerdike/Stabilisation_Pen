r"""Gap flux of the candidate actuator topologies (CALC with magpylib's analytic cuboid magnets; soft iron by images).

Why.  The Rev H lumped model (opt/inertial/adjoint.py) sets the gap flux as eta_leak B_r t_m / (t_m + t_c + g0 + s)
with eta_leak = 0.55 (ASSUMPTION).  Rev J's larger travel makes the gap the design driver, so the leakage factor is
computed here for each topology and fitted as a smooth function the differentiable models can use.

Iron.  An infinitely permeable plane is replaced by images (a magnet mirrored across the plane, magnetisation
(-Mx, -My, +Mz) for a plane normal to z; checked in tests: a magnet on iron equals a magnet of double length).  Two
parallel planes (the magnet's back iron and the coil's back iron) give an infinite image series, truncated at
+-N_IMG periods.  Real iron is finite and saturates, so these are upper bounds; the Rev H calibration check (a lumped
formula of the same kind gives 0.7-1.0 N/sqrt(W) for the Moticont volumes, AMF-02/AMF-73) is kept as the
cross-check.  Magnet grade: N48-N52 class, B_r 1.42 T used (MFR AMF-139, low end of N52; the K&J table AMF-28
recommends an SH grade in a warm actuator: N48SH ~1.38-1.42 T).

Topologies
  radial   Rev H: magnets on the four faces of a soft-iron hub, magnetised radially, facing flat coils backed by a
           soft-iron ring.  The magnet-to-coil gap must also clear the OTHER axis's stroke s (a magnet moving sideways
           along y approaches its x-coil), so g = g0 + s.
  axial    new: a checkerboard of poles (+z, -z) on a soft-iron disc at the end of the arm, facing a flat coil layer
           backed by a soft-iron disc across the pen axis.  Both axes move the magnets parallel to the coil plane, so
           the gap does not depend on the stroke (a spherical coil surface centred on the gimbal keeps it constant
           under tilt; a flat one changes it by about r alpha at the rim).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

BR = 1.42          # T, NdFeB N52 low end (MFR AMF-139: 1.42-1.48 T); N48SH class similar (AMF-28)
N_IMG = 3


def _magpy():
    import magpylib as magpy
    return magpy


def _images(mags, D: float, axis: int = 2, n: int = N_IMG):
    """Images of cuboid magnets between two mu=inf planes at coordinate 0 and D along `axis` (period 2D)."""
    magpy = _magpy()
    out = []
    for (pos, dim, M) in mags:
        pos = np.asarray(pos, float); M = np.asarray(M, float)
        Mm = -M.copy(); Mm[axis] = M[axis]                         # mirror: normal component kept, tangential flipped
        for k in range(-n, n + 1):
            p1 = pos.copy(); p1[axis] = pos[axis] + 2 * k * D
            out.append(magpy.magnet.Cuboid(polarization=M, dimension=dim, position=p1))
            p2 = pos.copy(); p2[axis] = -pos[axis] + 2 * k * D
            out.append(magpy.magnet.Cuboid(polarization=Mm, dimension=dim, position=p2))
    return magpy.Collection(*out)


def radial_B(w: float, l: float, t_m: float, g: float, t_c: float, n: int = N_IMG, npts: int = 7) -> float:
    """Mean |B| normal to the coil (radial) over the coil volume facing the magnet face (w x l), iron hub at x = 0 and
    iron ring at x = t_m + g + t_c (T)."""
    D = t_m + g + t_c
    col = _images([((t_m / 2, 0.0, 0.0), (t_m, w, l), (BR, 0.0, 0.0))], D, axis=0, n=n)
    xs = np.linspace(t_m + g, D, npts)
    ys = np.linspace(-0.45 * w, 0.45 * w, npts)
    zs = np.linspace(-0.45 * l, 0.45 * l, npts)
    P = np.array(np.meshgrid(xs, ys, zs, indexing="ij")).reshape(3, -1).T
    B = col.getB(P)
    return float(np.mean(np.abs(B[:, 0])))


def axial_B(a: float, t_m: float, g: float, t_c: float, n_side: int = 2, leg_frac: float = 0.6, n: int = N_IMG,
            npts: int = 7) -> float:
    """Checkerboard of n_side x n_side square poles (side a, +-z), iron behind the magnets (z = 0) and behind the coil
    layer (z = t_m + g + t_c).  Mean |B_z| over the coil layer above the central leg_frac of each pole (T)."""
    D = t_m + g + t_c
    mags = []
    for i in range(n_side):
        for j in range(n_side):
            sgn = 1.0 if (i + j) % 2 == 0 else -1.0
            cx = (i - (n_side - 1) / 2) * a
            cy = (j - (n_side - 1) / 2) * a
            mags.append(((cx, cy, t_m / 2), (a, a, t_m), (0.0, 0.0, sgn * BR)))
    col = _images(mags, D, axis=2, n=n)
    zs = np.linspace(t_m + g, D, npts)
    vals = []
    for i in range(n_side):
        for j in range(n_side):
            cx = (i - (n_side - 1) / 2) * a
            cy = (j - (n_side - 1) / 2) * a
            u = np.linspace(-leg_frac * a / 2, leg_frac * a / 2, npts)
            P = np.array(np.meshgrid(cx + u, cy + u, zs, indexing="ij")).reshape(3, -1).T
            vals.append(np.abs(col.getB(P)[:, 2]))
    return float(np.mean(np.concatenate(vals)))


def ideal_B(t_m: float, g_tot: float) -> float:
    """Infinite-width magnet between two iron planes: B_r t_m / (t_m + g_tot)."""
    return BR * t_m / (t_m + g_tot)


# ------------------------------------------------------------------ the surrogate used by designs.py
# Grid of the fit (CALC; npts 5 per axis of the averaging box).  Radial: 720 designs, axial: 240.
SURR_GRID = {
    "radial": {"w": (2e-3, 3e-3, 5e-3, 8e-3), "l": (4e-3, 6.5e-3, 10e-3), "t_m": (1.0e-3, 2.0e-3, 3.0e-3, 4.5e-3),
               "g": (0.5e-3, 1.5e-3, 3.0e-3, 5.0e-3, 7.0e-3), "t_c": (0.8e-3, 1.5e-3, 2.5e-3)},
    "axial": {"w": (3e-3, 4.5e-3, 6e-3, 8e-3), "t_m": (1.0e-3, 2.0e-3, 3.0e-3, 4.5e-3),
              "g": (0.3e-3, 0.6e-3, 1.0e-3, 1.6e-3, 2.5e-3), "t_c": (0.8e-3, 1.5e-3, 2.5e-3)}}


def surrogate_rows(kind: str, npts: int = 5, every: int = 1) -> np.ndarray:
    """magpylib gap flux over SURR_GRID (every k-th design with every > 1, for tests).  Columns w, l, t_m, g, t_c, B."""
    G = SURR_GRID[kind]
    rows = []
    if kind == "radial":
        for w in G["w"]:
            for l in G["l"]:
                for t_m in G["t_m"]:
                    for g in G["g"]:
                        for t_c in G["t_c"]:
                            rows.append((w, l, t_m, g, t_c))
    else:
        for a in G["w"]:
            for t_m in G["t_m"]:
                for g in G["g"]:
                    for t_c in G["t_c"]:
                        rows.append((a, a, t_m, g, t_c))
    rows = rows[::every]
    out = []
    for (w, l, t_m, g, t_c) in rows:
        B = radial_B(w, l, t_m, g, t_c, npts=npts) if kind == "radial" else axial_B(w, t_m, g, t_c, npts=npts)
        out.append((w, l, t_m, g, t_c, B))
    return np.array(out)


def surrogate_features(kind: str, w, l, t_m, G, t_c) -> np.ndarray:
    """Log-quadratic features of eta: x = ln(G/w), y = ln(t_m/w), u = t_c/G (+ z = ln(w/l) for the radial faces)."""
    x = np.log(G / w); y = np.log(t_m / w); u = t_c / G
    cols = [np.ones_like(x), x, y, u, x * x, y * y, x * y, x * u, y * u]
    if kind == "radial":
        z = np.log(w / l)
        cols += [z, x * z]
    return np.column_stack(cols)


def fit_surrogate(kind: str, rows: np.ndarray) -> Dict:
    """Least squares of ln(eta) on the features (CALC).  eta = B / (B_r t_m / (t_m + g + t_c))."""
    w, l, t_m, g, t_c, B = rows.T
    G = g + t_c
    eta = B / (BR * t_m / (t_m + G))
    A = surrogate_features(kind, w, l, t_m, G, t_c)
    c, *_ = np.linalg.lstsq(A, np.log(eta), rcond=None)
    rel = np.exp(A @ c) / eta - 1.0
    return {"coef": [float(v) for v in c], "n": int(len(eta)), "rel_rms": float(np.sqrt(np.mean(rel ** 2))),
            "rel_p95": float(np.percentile(np.abs(rel), 95)), "rel_max": float(np.abs(rel).max()),
            "eta_min": float(eta.min()), "eta_max": float(eta.max())}


def check_surrogate(kind: str, rows: np.ndarray, coef) -> Dict:
    """Relative error of a frozen surrogate (designs.ETA_RADIAL / ETA_AXIAL) against magpylib rows (CALC)."""
    w, l, t_m, g, t_c, B = rows.T
    G = g + t_c
    eta = B / (BR * t_m / (t_m + G))
    pred = np.exp(surrogate_features(kind, w, l, t_m, G, t_c) @ np.asarray(coef))
    rel = pred / eta - 1.0
    return {"n": int(len(eta)), "rel_rms": float(np.sqrt(np.mean(rel ** 2))), "rel_p95": float(np.percentile(np.abs(rel), 95)),
            "rel_max": float(np.abs(rel).max()), "eta": eta.tolist(), "eta_pred": pred.tolist()}


def image_check(w: float = 3e-3, t_m: float = 2e-3, l: float = 6e-3) -> Dict:
    """Image convention check: a magnet lying on one mu = inf plane gives, above it, the field of a magnet of double
    thickness in free space (the image doubles the magnet).  Returns both fields at three points (T)."""
    magpy = _magpy()
    one = magpy.magnet.Cuboid(polarization=(0, 0, BR), dimension=(w, l, t_m), position=(0, 0, t_m / 2))
    img = magpy.magnet.Cuboid(polarization=(0, 0, BR), dimension=(w, l, t_m), position=(0, 0, -t_m / 2))
    double = magpy.magnet.Cuboid(polarization=(0, 0, BR), dimension=(w, l, 2 * t_m), position=(0, 0, 0.0))
    P = np.array([[0, 0, t_m + 0.5e-3], [0.5e-3, 0.3e-3, t_m + 1.0e-3], [1.0e-3, -0.5e-3, t_m + 2.0e-3]])
    B_img = magpy.Collection(one, img).getB(P)
    B_dbl = double.getB(P)
    return {"B_images": B_img.tolist(), "B_double": B_dbl.tolist(), "max_abs_diff_T": float(np.abs(B_img - B_dbl).max())}
