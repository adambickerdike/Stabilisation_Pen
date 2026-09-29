"""Heel geometry: where a drive element can sit next to the swinging nose (CALC on a PROPOSED DESIGN; ASSUMPTION inputs).

The Rev H front end (docs/opt_inertial.md 8.6, DEC-034) leaves no room for anything inside the skid ring: the nose
swings to 5.29 mm from the axis in the ring plane at its stop, the ring's lip is 1.16 mm thick at the 6.75 mm contact
radius.  A drive element must therefore sit OUTSIDE the nose's envelope, at the bottom of the heel, and it must be the
lowest point of the heel over the writing tilts (35-75 deg) so that it touches the paper.

Facts used (CALC here):
  * An element of radius r_e (a ball, or a wheel steered about the paper normal through its contact point, which
    sweeps a sphere of radius r_e about its centre) with a wall t around it, centred r_e above its contact along the
    paper normal at 50 deg, clears the nose envelope by c only if its contact radius R_d >= r_e cos(50) + r_e + t +
    env_max + c.
  * The element protrudes beyond a flat skid ring of radius R_s = R_d - delta by e(theta) = delta cos(theta) +
    r_e (1 - cos(theta - 50 deg)), so it is always the lowest point of the heel; the spring travel must cover it.
  * Pen roll psi moves the element up the side: it keeps contact while (R_s + s_tr) cos(psi) >= R_s.
  * Parts behind the contact plane on the paper side clear the paper at the lowest tilt (35 deg) while
    r <= R_d + s tan(35 deg).
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from . import ensure_paths

ensure_paths()
from opt.inertial import front_end as FE  # noqa: E402
from opt.inertial.revh import RevH  # noqa: E402

THETA0 = 50.0
C_NOSE = 0.3          # mm, radial clearance element-to-nose envelope at the stop (as front_end c_ring, ASSUMPTION)
T_WALL = 0.3          # mm, housing / fork wall around the element (ASSUMPTION)


def envelope(R: float = 6.75, s_grid=None) -> Dict:
    """Radius (mm) of the swinging nose at its 3.5 mm stop versus s (mm behind the ring plane; negative = ahead)."""
    d, ru = RevH(), FE.FrontRules()
    dm = FE.dims(R, d, ru)
    s = np.linspace(-6.0, 12.0, 181) if s_grid is None else np.asarray(s_grid, float)
    refill_r = 1.175
    env = np.where(s >= 0.0,
                   np.array([FE.nozzle_r(float(x), ru) for x in s]) + dm["alpha_s"] * (dm["s_g"] - s),
                   refill_r + dm["alpha_s"] * (dm["s_g"] - s))
    return {"s_mm": s, "r_mm": env, "dims": dm}


def required_contact_radius(r_e: float, t: float = T_WALL, c: float = C_NOSE, theta0: float = THETA0,
                            iters: int = 4) -> Dict:
    """Smallest contact radius R_d (mm) at which an element of radius r_e (mm) and wall t clears the nose (CALC)."""
    R = 6.75
    for _ in range(iters):
        e = envelope(R)
        th = math.radians(theta0)
        s_c = r_e * math.sin(th)
        rho = r_e + t
        m = (e["s_mm"] >= s_c - rho) & (e["s_mm"] <= s_c + rho)
        env_max = float(np.max(e["r_mm"][m]))
        R = r_e * math.cos(th) + rho + env_max + c
    return {"r_e_mm": r_e, "R_d_mm": R, "env_max_mm": env_max, "centre_radial_mm": R - r_e * math.cos(th),
            "centre_axial_mm": s_c}


def protrusion_vs_tilt(r_e: float, delta: float, thetas=(35.0, 40.0, 50.0, 60.0, 75.0)) -> List[Dict]:
    """How far the element sticks out beyond a flat skid ring of radius R_d - delta (mm), per tilt (CALC)."""
    out = []
    for th in thetas:
        e = delta * math.cos(math.radians(th)) + r_e * (1.0 - math.cos(math.radians(th - THETA0)))
        out.append({"theta_deg": th, "protrusion_mm": e})
    return out


def roll_tolerance(R_s: float, s_tr: float) -> float:
    """Largest pen roll (deg) at which a sprung element with travel s_tr (mm) beyond the ring still touches (CALC)."""
    return math.degrees(math.acos(R_s / (R_s + s_tr)))


def travel_for_roll(R_s: float, psi_deg: float) -> float:
    return R_s * (1.0 / math.cos(math.radians(psi_deg)) - 1.0)


def paper_wedge(R_d: float, s: np.ndarray, theta_min: float = 35.0, c: float = 0.3) -> np.ndarray:
    """Largest radius (mm) on the paper side at s mm behind the contact plane that clears the paper at theta_min."""
    th = math.radians(theta_min)
    return R_d + np.asarray(s) * math.tan(th) - c / math.cos(th)


def front_end_at(R: float) -> Dict:
    """Ball protrusion ahead of the heel and refill slide over 35-75 deg (with corrections) for contact radius R (mm);
    front_end.py's own method (CALC)."""
    d, ru = RevH(), FE.FrontRules()
    dm = dict(FE.dims(R, d, ru))
    dm["nozzle_r_front"] = ru.nozzle_r_front
    slides = []
    for th in np.arange(35.0, 75.01, 5.0):
        for ph in range(0, 360, 30):
            for a in (0.0, dm["alpha_u"]):
                slides.append(FE.pose(float(th), dm, float(ph), float(a), ru)["slide"])
    return {"R_mm": R, "ball_ahead_50_mm": FE.protrusion(50.0, R), "ball_ahead_35_mm": FE.protrusion(35.0, R),
            "ball_ahead_75_mm": FE.protrusion(75.0, R), "refill_slide_range_mm": float(max(slides) - min(slides)),
            "sleeve_front_d_mm": 2.0 * (R + ru.sleeve_step)}


def heel_design(r_e: float = 1.5, delta: float = 0.35, roll_deg: float = 20.0) -> Dict:
    """The heel of the recommended design: element radius r_e, protrusion delta beyond the ring, roll tolerance (CALC)."""
    req = required_contact_radius(r_e)
    R_d = math.ceil(req["R_d_mm"] * 4.0) / 4.0           # 0.25 mm steps, as front_end.py
    R_s = R_d - delta
    tilt = protrusion_vs_tilt(r_e, delta)
    s_tr = max(max(t["protrusion_mm"] for t in tilt), travel_for_roll(R_s, roll_deg))
    fe = front_end_at(R_s)
    return {"r_e_mm": r_e, "R_d_mm": R_d, "R_skid_mm": R_s, "delta_mm": delta, "spring_travel_mm": s_tr,
            "roll_tolerance_deg": roll_tolerance(R_s, s_tr), "protrusion_by_tilt": tilt, "requirement": req,
            "front_end": fe, "front_end_revH": front_end_at(6.75)}


def sweep_element_sizes(sizes=(0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)) -> List[Dict]:
    rows = []
    for r in sizes:
        q = required_contact_radius(r)
        fe = front_end_at(q["R_d_mm"])
        rows.append({"r_e_mm": r, "R_d_mm": q["R_d_mm"], "sleeve_front_d_mm": fe["sleeve_front_d_mm"],
                     "ball_ahead_50_mm": fe["ball_ahead_50_mm"], "refill_slide_mm": fe["refill_slide_range_mm"]})
    return rows


# ----------------------------------------------------------------------------- element + mechanism above it
def pod_contact_radius(r_e: float, cap_h: float, cap_r: float, t: float = T_WALL, c: float = C_NOSE,
                       theta0: float = THETA0, n_az: int = 48, n_h: int = 7, R0: float = 8.0, iters: int = 5,
                       cap_z0: float = None) -> Dict:
    """Contact radius (mm) needed when a mechanism sits on top of the element: for the steered wheel, a steering
    ring (radius cap_r) from the wheel's top (2 r_e above the contact along the paper normal) up to 2 r_e + cap_h;
    for the ball, its two drive rollers (cap_r ~ ball radius + roller diameter, cap_h ~ roller diameter).  Every
    point of the element sphere (radius r_e + t about its centre) and of the cap cylinder (about the paper normal at
    theta0) must clear the swinging nose by c (CALC)."""
    th = math.radians(theta0)
    n = np.array([math.cos(th), 0.0, math.sin(th)])          # paper normal in the pen frame (x away from paper, z back)
    e1 = np.array([math.sin(th), 0.0, -math.cos(th)])        # in the tilt plane, perpendicular to n
    e2 = np.array([0.0, 1.0, 0.0])
    pts = []
    for a in np.linspace(0.0, 2 * math.pi, n_az, endpoint=False):
        u = math.cos(a) * e1 + math.sin(a) * e2
        for h in np.linspace(-1.0, 1.0, n_h):                 # element sphere, as a stack of circles
            rr = (r_e + t) * math.sqrt(max(1.0 - h * h, 0.0))
            pts.append(r_e * n + h * (r_e + t) * n + rr * u)
        z0 = 2.0 * r_e if cap_z0 is None else cap_z0
        for h in np.linspace(z0, z0 + cap_h, n_h):
            pts.append(h * n + (cap_r + t) * u)
    P = np.array(pts)                                          # relative to the contact point
    R = R0
    for _ in range(iters):
        e = envelope(R)
        s = P[:, 2]                                            # axial position behind the contact plane
        radial = R - P[:, 0]                                   # distance from the pen axis on the paper side
        env = np.interp(s, e["s_mm"], e["r_mm"])
        need = np.max(env + c - radial)
        R = R + need
    return {"r_e_mm": r_e, "cap_h_mm": cap_h, "cap_r_mm": cap_r, "R_d_mm": float(R),
            "sleeve_front_d_mm": 2.0 * (R + 0.75)}


def wheel_pod(r_e: float, ring_h: float = 1.0, ring_gap: float = 0.5) -> Dict:
    """Steered wheel: a steering ring (fork top) of height ring_h and radius r_e + ring_gap above the wheel (CALC)."""
    return pod_contact_radius(r_e, ring_h, r_e + ring_gap)


def ball_pod(r_e: float, r_r: float = 0.6, elev_deg: float = 30.0) -> Dict:
    """Driven ball: two rollers of radius r_r touch the ball 'elev_deg' above its equator (so their preload also
    presses the ball on the paper); they occupy heights r_e + (r_e + r_r) sin(elev) +/- r_r and radii up to
    (r_e + r_r) cos(elev) + r_r about the ball's normal axis (CALC)."""
    e = math.radians(elev_deg)
    zc = r_e + (r_e + r_r) * math.sin(e)
    return pod_contact_radius(r_e, 2.0 * r_r, (r_e + r_r) * math.cos(e) + r_r, cap_z0=zc - r_r)
