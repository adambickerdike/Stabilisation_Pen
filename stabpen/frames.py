r"""Reference frames and the paper-plane Jacobian.

Frames (see docs/architecture.md, section "Reference frames")
-------------------------------------------------------------
{P} page frame: e_x, e_y in the page, n = e_z out of the page (right-handed).
{H} housing frame: origin at the nominal ball centre C0 (stage neutral, axial
    suspension at its reference deflection); z_H = a is the barrel axis pointing
    from the nib toward the cap; x_H, y_H are fixed to a housing datum.

Pen orientation in {P}
    theta : altitude, angle between a and the page plane (90 deg = upright)
    phi   : azimuth of the page projection of a, measured from e_x (CCW)
    rho   : roll of {H} about a

    h  = ( cos phi, sin phi, 0)            page projection direction of a
    a  = cos(theta) h + sin(theta) n
    t1 = sin(theta) h - cos(theta) n       in tilt plane, perpendicular to a
    t2 = (-sin phi, cos phi, 0)            parallel to page, perpendicular to h
    (t1, t2, a) is right-handed; t1 x t2 = a.
    x_H =  cos(rho) t1 + sin(rho) t2
    y_H = -sin(rho) t1 + cos(rho) t2

Tip (ball-centre) displacement relative to the housing
    delta = q1 x_H + q2 y_H + s a          (s > 0: ball retracts toward the cap)
Maintained contact with a rigid page (delta . n = 0) gives
    s = cot(theta) * q_t1,   q_t1 = q1 cos(rho) - q2 sin(rho)
and the page-plane displacement
    delta_page = (q_t1 / sin theta) h + q_t2 t2,   q_t2 = q1 sin(rho) + q2 cos(rho)
so  J = Rot(phi) diag(1/sin theta, 1) Rot(rho),  det J = 1/sin theta,
condition number kappa(J) = 1/sin theta.

The ink is deposited at the page projection of the ball centre, independent of
pen orientation, because the ball is spherical.  Second-order effects of the
pivot arc (retraction q^2/(2 L1), nib rotation q/L1) are provided separately.
"""
from __future__ import annotations

import numpy as np


def rot2(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s], [s, c]])


def basis(theta: float, phi: float = 0.0, rho: float = 0.0) -> dict:
    """Unit vectors (in page coordinates) for a pen orientation. Angles in rad."""
    ct, st = np.cos(theta), np.sin(theta)
    h = np.array([np.cos(phi), np.sin(phi), 0.0])
    n = np.array([0.0, 0.0, 1.0])
    a = ct * h + st * n
    t1 = st * h - ct * n
    t2 = np.array([-np.sin(phi), np.cos(phi), 0.0])
    xH = np.cos(rho) * t1 + np.sin(rho) * t2
    yH = -np.sin(rho) * t1 + np.cos(rho) * t2
    return {"h": h, "n": n, "a": a, "t1": t1, "t2": t2, "xH": xH, "yH": yH}


def R_PH(theta: float, phi: float = 0.0, rho: float = 0.0) -> np.ndarray:
    """Rotation matrix whose columns are x_H, y_H, z_H=a expressed in {P}."""
    b = basis(theta, phi, rho)
    return np.column_stack([b["xH"], b["yH"], b["a"]])


def jacobian(theta: float, phi: float = 0.0, rho: float = 0.0) -> np.ndarray:
    """2x2 map from transverse stage coordinates (q1,q2) in {H} to page (x,y),
    assuming the axial suspension accommodates s = cot(theta) q_t1 freely."""
    return rot2(phi) @ np.diag([1.0 / np.sin(theta), 1.0]) @ rot2(rho)


def jacobian_numeric(theta: float, phi: float = 0.0, rho: float = 0.0) -> np.ndarray:
    """Independent numerical construction of J from 3-D vectors (for verification)."""
    b = basis(theta, phi, rho)
    cols = []
    for v in (b["xH"], b["yH"]):
        s = -(v @ b["n"]) / (b["a"] @ b["n"])   # axial accommodation for unit q
        d = v + s * b["a"]
        cols.append(d[:2])
    return np.column_stack(cols)


def inverse_jacobian(theta: float, phi: float = 0.0, rho: float = 0.0) -> np.ndarray:
    return rot2(-rho) @ np.diag([np.sin(theta), 1.0]) @ rot2(-phi)


def axial_accommodation(q1, q2, theta: float, rho: float = 0.0):
    """Axial ball displacement s needed to keep a rigid page contact (m)."""
    q_t1 = q1 * np.cos(rho) - q2 * np.sin(rho)
    return q_t1 / np.tan(theta)


def stage_travel_for_paper_disc(r_page: float, theta: float) -> dict:
    """Transverse stage displacement needed to reach every point of a page disc
    of radius r_page at altitude theta, for any roll (worst case over rho)."""
    q_t1_max = r_page * np.sin(theta)      # tilt-plane component
    q_t2_max = r_page                      # lateral component
    s_max = r_page * np.cos(theta)         # axial accommodation
    return {"q_t1_max": q_t1_max, "q_t2_max": q_t2_max,
            "q_radius_any_roll": max(q_t1_max, q_t2_max), "s_max": s_max}


def page_workspace(q_radius: float, theta: float, phi: float = 0.0, rho: float = 0.0, n: int = 181):
    """Page-plane image of a circular transverse stage workspace (closed polyline)."""
    ang = np.linspace(0.0, 2.0 * np.pi, n)
    q = q_radius * np.vstack([np.cos(ang), np.sin(ang)])
    return jacobian(theta, phi, rho) @ q


def pivot_second_order(q_mag, L1: float):
    """Pivot-arc effects for a front-pivot lever: axial retraction (m) and nib
    rotation (rad) for transverse tip displacement magnitude q_mag."""
    psi = np.arcsin(np.clip(q_mag / L1, -1.0, 1.0))
    return {"retraction": L1 * (1.0 - np.cos(psi)), "nib_rotation": psi}
