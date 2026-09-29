r"""Front-end closure for +-4-8 mm of tip travel: DEC-034 generalised (CALC on a PROPOSED DESIGN; inputs ASSUMPTION).

This is a vectorised re-implementation of ``opt/inertial/front_end.py`` (read-only; its rules and conventions are
used unchanged, ``FrontRules``) so that the closure can be swept over travel, pivot position and tilt range quickly.
``tests/test_frontend.py`` checks it against the original at the Rev H design point (6.75 mm contact radius, 13.5 mm
refill slide).

Geometry (as front_end.py).  The handle rests on the paper at the skid ring's front outer edge (contact radius R).
The ball centre sits p(theta) = (R cos(theta) - r_b) / sin(theta) ahead of the ring plane.  The nose tilts about a
gimbal s_g = z_p - p(50 deg) behind the ring plane; the refill slides along the nose so the ball stays on the paper.
Travel is an angle: usable alpha_u = X / z_p (X at the nominal 50 deg), stop alpha_s = (X + 0.5 mm) / z_p.
Rules (FrontRules): ring lip >= 1.0 mm after clearing the nose at the stop by 0.3 mm; nozzle >= 0.3 mm above the paper
within the usable travel over 35-75 deg; the sleeve's front edge above the paper; the carrier clears the sleeve bore.

New outputs here: the contact radius as a function of travel (sized in 0.25 mm steps), the refill slide the travel
needs (it sets the refill spring), the ball's travel over 35-75 deg in every direction (the travel that autowrite can
count on is the minimum), the front diameter the writer sees around the ink, and a "heel" variant with the pivot
moved (z_p) to trade the ring size against the swing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, Optional

import numpy as np

from . import ensure_paths

ensure_paths()
from opt.inertial.front_end import FrontRules, R_B, protrusion  # noqa: E402  (read-only reuse)


@dataclass
class Nose:
    """What the closure needs of a nose design (mm)."""
    z_p: float = 45.0            # gimbal (pivot) distance behind the ball at the nominal tilt
    travel: float = 3.0          # usable ball travel at the nominal tilt
    stop_extra: float = 0.5      # stop = travel + stop_extra
    translate: float = 0.0       # share of the tip motion made by translating the whole carrier (dual-plane designs):
                                 # 0 = pure tilt about z_p, 1 = pure translation


def dims(R: float, nz: Nose, ru: FrontRules) -> Dict:
    p50 = protrusion(ru.theta_nom, R)
    s_g = nz.z_p - p50
    a_u = nz.travel / nz.z_p
    a_s = (nz.travel + nz.stop_extra) / nz.z_p
    ss = np.linspace(0.0, ru.ring_len, 31)
    nr = ru.nozzle_r_front + (ru.carrier_r - ru.nozzle_r_front) * np.clip(ss, 0.0, ru.nozzle_len) / ru.nozzle_len
    if nz.translate > 0:
        # a translating carrier moves by the same amount along its whole length (share translate of the travel)
        sw_s = (1 - nz.translate) * a_s * (s_g - ss) + nz.translate * (nz.travel + nz.stop_extra) * np.ones_like(ss)
        sw_u_cf = (1 - nz.translate) * a_u * (s_g - ru.nozzle_len) + nz.translate * nz.travel
        sw_s_cf = (1 - nz.translate) * a_s * (s_g - ru.nozzle_len) + nz.translate * (nz.travel + nz.stop_extra)
    else:
        sw_s = a_s * (s_g - ss)
        sw_u_cf = a_u * (s_g - ru.nozzle_len)
        sw_s_cf = a_s * (s_g - ru.nozzle_len)
    env = float(np.max(nr + sw_s))
    r_bore = env + ru.c_ring
    r_sleeve = ru.carrier_r + sw_u_cf + ru.c_sleeve
    return {"R": R, "p50": p50, "s_g": s_g, "alpha_u": a_u, "alpha_s": a_s, "ring_bore_r": r_bore, "ring_wall": R - r_bore,
            "carrier_front_s": ru.nozzle_len, "sleeve_bore_r": r_sleeve,
            "carrier_stop_clearance": r_sleeve - (ru.carrier_r + sw_s_cf), "sleeve_front_r": R + ru.sleeve_step}


def _rot(v, k, ang):
    """Rodrigues rotation of vectors v (..., 3) about unit axes k (..., 3) by angles ang (...)."""
    c = np.cos(ang)[..., None]
    s = np.sin(ang)[..., None]
    kv = np.sum(k * v, axis=-1, keepdims=True)
    return v * c + np.cross(k, v) * s + k * kv * (1.0 - c)


def poses(theta_deg: np.ndarray, dm: Dict, phi_deg: np.ndarray, alpha: float, ru: FrontRules, nz: Nose,
          n_rim: int = 73) -> Dict[str, np.ndarray]:
    """Vectorised pose() of front_end.py over tilts (T,) x directions (P,).  Returns arrays (T, P): the nozzle's
    lowest point above the paper, the refill slide and the ball's travel on the paper."""
    th = np.radians(np.asarray(theta_deg, float))[:, None]              # (T,1)
    ph = np.radians(np.asarray(phi_deg, float))[None, :]                # (1,P)
    T, P = th.shape[0], ph.shape[1]
    a = np.stack([np.cos(th) * np.ones_like(ph), np.zeros((T, P)), np.sin(th) * np.ones_like(ph)], -1)      # pen axis
    tp = np.stack([np.sin(th) * np.ones_like(ph), np.zeros((T, P)), -np.cos(th) * np.ones_like(ph)], -1)    # toward paper
    ty = np.zeros((T, P, 3)); ty[..., 1] = 1.0
    R = dm["R"]
    C = np.zeros((T, P, 3)); C[..., 2] = R * np.cos(th)
    G = C + dm["s_g"] * a
    u = np.cos(ph)[..., None] * tp + np.sin(ph)[..., None] * ty
    k = np.cross(u, a)
    k = k / np.linalg.norm(k, axis=-1, keepdims=True)
    tr = nz.translate
    ang = (1 - tr) * alpha * np.ones((T, P))
    shift = tr * alpha * nz.z_p                                          # translation of the carrier (mm) along u
    a_n = _rot(a, k, ang)
    Gs = G + shift * u * 0.0                                             # the gimbal point itself does not move
    # ball centre on the (tilted, shifted) nose axis at height r_b: the axis passes through G + shift*u
    Ga = G + shift * u
    L = (Ga[..., 2] - R_B) / a_n[..., 2]
    B = Ga - L[..., None] * a_n
    L0 = dm["s_g"] + protrusion(ru.theta_nom, R)
    B0 = G - (dm["s_g"] + protrusion_arr(np.degrees(th[:, 0]), R))[:, None, None] * a
    psi = np.linspace(0.0, 2 * math.pi, n_rim)
    zmin = np.full((T, P), np.inf)
    for c_, s_ in zip(np.cos(psi), np.sin(psi)):
        rho = dm["nozzle_r_front"] * (c_ * tp + s_ * ty)
        Pn = G + shift * u + _rot(-dm["s_g"] * a + rho, k, ang)
        zmin = np.minimum(zmin, Pn[..., 2])
    return {"nozzle_min_z": zmin, "slide": L - L0, "ball_travel": np.linalg.norm((B - B0)[..., :2], axis=-1)}


def protrusion_arr(theta_deg, R, r_b=R_B):
    th = np.radians(np.asarray(theta_deg, float))
    return (R * np.cos(th) - r_b) / np.sin(th)


def check(R: float, nz: Nose, ru: FrontRules = FrontRules(), n_theta: int = 9, n_phi: int = 24) -> Dict:
    ru = replace(ru, stop=nz.travel + nz.stop_extra)
    dm = dims(R, nz, ru)
    dm["nozzle_r_front"] = ru.nozzle_r_front
    thetas = np.linspace(ru.theta_min, ru.theta_max, n_theta)
    phis = np.arange(0.0, 360.0, 360.0 / n_phi)
    pu = poses(thetas, dm, phis, dm["alpha_u"], ru, nz)
    ps = poses(thetas, dm, phis, dm["alpha_s"], ru, nz)
    p0 = poses(thetas, dm, np.array([0.0]), 0.0, ru, nz)
    th = np.radians(thetas)
    sleeve_front = ru.ring_len * np.sin(th) + (R - dm["sleeve_front_r"]) * np.cos(th)
    slide_lo = float(min(pu["slide"].min(), p0["slide"].min()))
    slide_hi = float(max(pu["slide"].max(), p0["slide"].max()))
    m = (thetas >= 40.0 - 1e-9) & (thetas <= 70.0 + 1e-9)
    out = {"R_mm": R, "dims": {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in dm.items()},
           "theta_deg": thetas.tolist(),
           "ring_wall_mm": dm["ring_wall"], "carrier_stop_clearance_mm": dm["carrier_stop_clearance"],
           "nozzle_clear_usable_min_mm": float(pu["nozzle_min_z"].min()), "nozzle_clear_stop_min_mm": float(ps["nozzle_min_z"].min()),
           "sleeve_front_clear_min_mm": float(sleeve_front.min()),
           "ball_travel_usable_min_mm": float(pu["ball_travel"].min()), "ball_travel_usable_max_mm": float(pu["ball_travel"].max()),
           "ball_travel_min_by_tilt_mm": pu["ball_travel"].min(axis=1).tolist(),
           "ball_travel_max_by_tilt_mm": pu["ball_travel"].max(axis=1).tolist(),
           "refill_slide_mm": [slide_lo, slide_hi], "refill_slide_range_mm": slide_hi - slide_lo,
           "refill_slide_range_40_70_mm": float(max(pu["slide"][m].max(), p0["slide"][m].max()) - min(pu["slide"][m].min(), p0["slide"][m].min())),
           "protrusion_35_75_mm": [float(protrusion(ru.theta_min, R)), float(protrusion(ru.theta_max, R))],
           "front_diameter_mm": 2.0 * dm["sleeve_front_r"]}
    out["passes"] = bool(out["ring_wall_mm"] >= ru.ring_wall_min - 1e-9 and out["nozzle_clear_usable_min_mm"] >= ru.c_paper
                         and out["sleeve_front_clear_min_mm"] > 0.0 and out["carrier_stop_clearance_mm"] >= 0.0)
    return out


def size(nz: Nose, ru: FrontRules = FrontRules(), R0: float = 5.5, R1: float = 18.0, n_theta: int = 9, n_phi: int = 24) -> Dict:
    """Smallest contact radius (in ru.R_step steps) that passes every rule, and its closure."""
    for R in np.arange(R0, R1 + 1e-9, ru.R_step):
        c = check(float(R), nz, ru, n_theta, n_phi)
        if c["passes"]:
            return c
    return {"R_mm": float("nan"), "passes": False}


def travel_for_min(X_min: float, z_p: float = 45.0, ru: FrontRules = FrontRules(), translate: float = 0.0) -> Dict:
    """The nominal travel (at 50 deg) whose minimum ball travel over 35-75 deg and every direction is >= X_min."""
    lo, hi = X_min, 2.0 * X_min
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        c = size(Nose(z_p=z_p, travel=mid, translate=translate), ru)
        if c.get("passes") and c["ball_travel_usable_min_mm"] >= X_min:
            hi = mid
        else:
            lo = mid
        if hi - lo < 0.02:
            break
    c = size(Nose(z_p=z_p, travel=hi, translate=translate), ru)
    c["travel_nominal_mm"] = hi
    return c


def sweep(X_list=(3.0, 4.0, 5.0, 6.0, 7.0, 8.0), zp_list=(35.0, 45.0, 55.0, 65.0), ru: FrontRules = FrontRules()) -> list:
    rows = []
    for zp in zp_list:
        for X in X_list:
            c = size(Nose(z_p=zp, travel=X), ru)
            rows.append({"z_p_mm": zp, "travel_nominal_mm": X, "R_mm": c.get("R_mm"), "passes": c.get("passes"),
                         "front_diameter_mm": c.get("front_diameter_mm"), "ring_wall_mm": c.get("ring_wall_mm"),
                         "nozzle_clear_mm": c.get("nozzle_clear_usable_min_mm"), "refill_slide_mm": c.get("refill_slide_range_mm"),
                         "refill_slide_40_70_mm": c.get("refill_slide_range_40_70_mm"),
                         "ball_travel_min_mm": c.get("ball_travel_usable_min_mm"), "ball_travel_max_mm": c.get("ball_travel_usable_max_mm"),
                         "protrusion_35_mm": (c.get("protrusion_35_75_mm") or [None, None])[0],
                         "protrusion_75_mm": (c.get("protrusion_35_75_mm") or [None, None])[1],
                         "sleeve_bore_r_mm": (c.get("dims") or {}).get("sleeve_bore_r")})
    return rows


def refill_follow_lift(R: float = 6.75, thetas=(40.0, 50.0, 60.0, 70.0, 75.0), theta_stop: float = 35.0) -> Dict:
    """Architecture B's free refill (constant-force spring, forward stop set so the ball reaches the paper at theta_stop)
    follows a pen lift: the ball stays on the paper until the refill reaches its stop.  The axial extension left at tilt
    theta is p(theta_stop) - p(theta); a vertical lift dh needs dh / sin(theta) of extension, so the ball follows lifts up
    to (p(theta_stop) - p(theta)) sin(theta) (CALC; with the nose deflected there is even more extension).  The
    synthetic writers lift the pen 1.5 mm between strokes (aiguide.writer.Path lift_height, ASSUMPTION)."""
    p0 = float(protrusion(theta_stop, R))
    out = {"R_mm": R, "theta_stop_deg": theta_stop, "protrusion_stop_mm": p0, "by_tilt": []}
    for th in thetas:
        ext = p0 - float(protrusion(th, R))
        out["by_tilt"].append({"theta_deg": th, "extension_left_mm": ext, "lift_followed_mm": ext * math.sin(math.radians(th))})
    return out
