r"""The Rev J front end: DEC-034's closure generalised to the C1S nose (study N) AND the heel pod (study D).

CALC on a PROPOSED DESIGN; every clearance rule is an ASSUMPTION (opt/inertial/front_end.FrontRules, read-only, plus the
heel rules of drive/geometry.py).  Nothing here was built or measured.

Geometry (as opt/inertial/front_end.py).  The handle rests on the paper at the skid ring's front outer edge, radius R_s.
The ball centre sits p(theta) = (R_s cos(theta) - r_b) / sin(theta) ahead of the ring plane.  The nose tilts about the
gimbal s_g = z_p - p(50 deg) behind the ring plane; travel is an angle: usable alpha_u = X / z_p (X at 50 deg), stop
alpha_s = (X + 0.5 mm) / z_p.  s is the axial distance behind the ring plane (s < 0: ahead of it).

The heel (study D).  A 2 mm wheel (radius r_e) sits in a slot at the bottom of the ring.  Its contact is at R_d = R_s +
delta in the ring plane; it is steered about the 50 deg paper normal through its contact point; a steering ring (crown)
of radius r_e + 0.5 mm sits 2 r_e ... 2 r_e + 1 mm above the contact along that normal.  Every point of the wheel's swept
sphere (radius r_e + wall) and of the steering ring (radius + wall) must clear the nose's envelope at the stop by 0.3 mm
(drive/geometry.pod_contact_radius; reproduced here with the nose's envelope as an argument and tested against the drive
study's own number for Rev H, 8.676 mm).

The integration loop.  The larger ring pushes the ball further ahead of the ring and so SHORTENS the gimbal-to-ball
lever at steep tilts; the guaranteed ball travel (the minimum over 35-75 deg and every direction) then falls below 6.0 mm
unless the nose's angle grows a little; a larger angle swings the nozzle further toward the pod.  close() iterates
(travel, R_d, R_s) to a fixed point, sizing R_d in the 0.25 mm steps of front_end.py.

Also here: ink visibility with the C opening on top (ray casting from the writer's eye over the front end's solids), and
the page sensor's window height over tilt and roll (the sensor must sit at a fixed height above the paper).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths
from . import params as PA

ensure_paths()
from opt.inertial.front_end import FrontRules, R_B, protrusion  # noqa: E402  (read-only reuse)
from nose2 import frontend as FEN  # noqa: E402  (read-only reuse: vectorised closure, checked against front_end.py)

RU = FrontRules()
R_STEP = RU.R_step                      # 0.25 mm sizing steps (front_end.py)
REFILL_R = 1.175                        # D1 refill radius (2.35 mm, DEC-004)


@dataclass(frozen=True)
class Heel:
    """Heel pod dimensions (mm); defaults = study D's recommended wheel pod (ASSUMPTION values, revj/params.HEEL)."""
    r_e: float = 1.0
    t: float = 0.3
    c: float = 0.3
    cap_r_extra: float = 0.5
    cap_h: float = 1.0
    delta: float = 0.35
    theta0: float = 50.0
    roll_deg: float = 20.0

    @property
    def cap_r(self):
        return self.r_e + self.cap_r_extra


@dataclass(frozen=True)
class NoseGeo:
    z_p: float                     # gimbal, mm behind the ball at 50 deg
    X: float                       # usable (nominal) ball travel at 50 deg, mm
    stop_extra: float = 0.5

    @property
    def alpha_u(self):
        return self.X / self.z_p

    @property
    def alpha_s(self):
        return (self.X + self.stop_extra) / self.z_p


def c1s_nose(X: Optional[float] = None) -> NoseGeo:
    nd = PA.nose_design()
    return NoseGeo(z_p=nd["z_p"], X=nd["X_nom"] if X is None else X)


def revh_nose() -> NoseGeo:
    return NoseGeo(z_p=45.0, X=3.0)


# --------------------------------------------------------------------------------------------------- nose envelope
def envelope(R: float, nz: NoseGeo, s: Optional[np.ndarray] = None, ru: FrontRules = RU) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Radius (mm) of the swinging nose at its stop against s (mm behind the ring plane): the nozzle cone and carrier
    behind the ring plane, the refill ahead of it (as drive/geometry.envelope, with the nose as an argument)."""
    dm = FEN.dims(R, FEN.Nose(z_p=nz.z_p, travel=nz.X, stop_extra=nz.stop_extra), ru)
    s = np.linspace(-8.0, 16.0, 481) if s is None else np.asarray(s, float)
    nozr = ru.nozzle_r_front + (ru.carrier_r - ru.nozzle_r_front) * np.clip(s, 0.0, ru.nozzle_len) / ru.nozzle_len
    env = np.where(s >= 0.0, nozr + dm["alpha_s"] * (dm["s_g"] - s), REFILL_R + dm["alpha_s"] * (dm["s_g"] - s))
    return s, env, dm


def pod_points(h: Heel, n_az: int = 72, n_h: int = 9) -> np.ndarray:
    """Points of the wheel pod relative to the wheel's contact point, pen frame (x away from the paper, y, s along the
    axis): the wheel's swept sphere (radius r_e + t about its centre, r_e above the contact on the paper normal) and the
    steering ring (radius cap_r + t, from 2 r_e to 2 r_e + cap_h along the normal).  As drive/geometry.pod_contact_radius."""
    th = math.radians(h.theta0)
    n = np.array([math.cos(th), 0.0, math.sin(th)])
    e1 = np.array([math.sin(th), 0.0, -math.cos(th)])
    e2 = np.array([0.0, 1.0, 0.0])
    pts = []
    for a in np.linspace(0.0, 2 * math.pi, n_az, endpoint=False):
        u = math.cos(a) * e1 + math.sin(a) * e2
        for hh in np.linspace(-1.0, 1.0, n_h):
            rr = (h.r_e + h.t) * math.sqrt(max(1.0 - hh * hh, 0.0))
            pts.append(h.r_e * n + hh * (h.r_e + h.t) * n + rr * u)
        if h.cap_h > 0:
            for hh in np.linspace(2.0 * h.r_e, 2.0 * h.r_e + h.cap_h, n_h):
                pts.append(hh * n + (h.cap_r + h.t) * u)
    return np.array(pts)


def pod_contact_radius(env_fun: Callable[[float], Tuple[np.ndarray, np.ndarray]], h: Heel, R0: float = 8.0,
                       iters: int = 8) -> Dict:
    """Smallest wheel contact radius R_d (mm, continuous) at which every pod point clears the nose envelope by h.c.
    env_fun(R) -> (s, r_env) for a ring of contact radius R (the envelope depends weakly on R through p(50))."""
    P = pod_points(h)
    R = R0
    worst = None
    for _ in range(iters):
        s, env = env_fun(R)
        need_i = np.interp(P[:, 2], s, env) + h.c - (R - P[:, 0])
        k = int(np.argmax(need_i))
        worst = {"s_mm": float(P[k, 2]), "inboard_mm": float(P[k, 0]), "lateral_mm": float(P[k, 1])}
        R = R + float(need_i[k])
    return {"R_d_mm": float(R), "worst_point": worst}


def ceil_step(R: float, step: float = R_STEP) -> float:
    return math.ceil(R / step - 1e-9) * step


def nose_only_R(nz: NoseGeo, ru: FrontRules = RU) -> Dict:
    """DEC-034 closure without the heel (nose2/frontend.size): the smallest ring passing ring lip, nozzle, sleeve front
    and carrier rules."""
    return FEN.size(FEN.Nose(z_p=nz.z_p, travel=nz.X, stop_extra=nz.stop_extra), ru, n_theta=9, n_phi=24)


def travel_for_min(X_min: float, R: float, z_p: float, ru: FrontRules = RU, n_theta: int = 17, n_phi: int = 72) -> float:
    """Nominal travel at 50 deg whose minimum ball travel over 35-75 deg and every direction is X_min, for ring R."""
    lo, hi = X_min, 1.4 * X_min
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        c = FEN.check(R, FEN.Nose(z_p=z_p, travel=mid), ru, n_theta=n_theta, n_phi=n_phi)
        if c["ball_travel_usable_min_mm"] >= X_min:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-4:
            break
    return hi


# --------------------------------------------------------------------------------------------------- closure
def check(R_s: float, nz: NoseGeo, h: Optional[Heel] = None, sleeve_step: float = 0.0, ru: FrontRules = RU,
          n_theta: int = 17, n_phi: int = 72) -> Dict:
    """Every front-end rule at ring radius R_s (and wheel contact R_s + delta when a heel is fitted)."""
    c = FEN.check(R_s, FEN.Nose(z_p=nz.z_p, travel=nz.X, stop_extra=nz.stop_extra), ru, n_theta=n_theta, n_phi=n_phi)
    th = np.radians(np.array(c["theta_deg"]))
    sleeve_front = ru.ring_len * np.sin(th) + (R_s - (R_s + sleeve_step)) * np.cos(th)
    out = {k: c[k] for k in ("R_mm", "ring_wall_mm", "carrier_stop_clearance_mm", "nozzle_clear_usable_min_mm",
                             "nozzle_clear_stop_min_mm", "ball_travel_usable_min_mm", "ball_travel_usable_max_mm",
                             "refill_slide_mm", "refill_slide_range_mm", "refill_slide_range_40_70_mm")}
    out["dims"] = c["dims"]
    out["sleeve_step_mm"] = sleeve_step
    out["sleeve_front_d_mm"] = 2.0 * (R_s + sleeve_step)
    out["sleeve_front_clear_min_mm"] = float(sleeve_front.min())
    out["protrusion_mm"] = {f"{t:g}": float(protrusion(t, R_s)) for t in (35.0, 40.0, 50.0, 60.0, 70.0, 75.0)}
    rules = {"ring_wall": out["ring_wall_mm"] - ru.ring_wall_min, "nozzle": out["nozzle_clear_usable_min_mm"] - ru.c_paper,
             "sleeve_front": out["sleeve_front_clear_min_mm"], "carrier": out["carrier_stop_clearance_mm"]}
    if h is not None:
        R_d = R_s + h.delta
        env_fun = lambda R, nz=nz: envelope(R, nz)[:2]                                     # noqa: E731
        s, env = env_fun(R_s)
        P = pod_points(h)
        clr = (R_d - P[:, 0]) - (np.interp(P[:, 2], s, env) + h.c)
        out["R_d_mm"] = R_d
        out["pod_clearance_min_mm"] = float(clr.min()) + h.c - h.c           # margin beyond the 0.3 mm rule
        out["pod_to_nose_at_stop_mm"] = float(clr.min() + h.c)               # actual gap pod-nose at the stop
        # the wheel is the lowest point of the heel at every tilt: protrusion beyond the ring (drive/geometry)
        out["wheel_protrusion_mm"] = {f"{t:g}": float(h.delta * math.cos(math.radians(t)) + h.r_e * (1 - math.cos(math.radians(t - h.theta0))))
                                      for t in (35.0, 50.0, 75.0)}
        s_tr = max(max(out["wheel_protrusion_mm"].values()), R_s * (1 / math.cos(math.radians(h.roll_deg)) - 1))
        out["spring_travel_mm"] = s_tr
        out["roll_tolerance_deg"] = math.degrees(math.acos(R_s / (R_s + s_tr)))
        rules["pod"] = out["pod_clearance_min_mm"]
    out["rule_margins_mm"] = rules
    out["passes"] = bool(all(v >= -1e-9 for v in rules.values()) and out["carrier_stop_clearance_mm"] >= 0)
    return out


def close(h: Optional[Heel] = Heel(), X_min_req: float = 6.0, sleeve_step: float = 0.0, nz0: Optional[NoseGeo] = None,
          keep_angle: bool = False, n_theta: int = 17, n_phi: int = 72, max_iter: int = 8) -> Dict:
    """Fixed point of (nose travel, wheel contact radius R_d, ring radius R_s).
    keep_angle=True keeps study N's angle (X unchanged) and reports the guaranteed travel that results."""
    nz = nz0 or c1s_nose()
    hist = []
    R_nose = nose_only_R(nz)["R_mm"]
    R_s = R_nose
    for it in range(max_iter):
        if h is not None:
            env_fun = lambda R, nz=nz: envelope(R, nz)[:2]                                 # noqa: E731
            pr = pod_contact_radius(env_fun, h)
            R_d = ceil_step(pr["R_d_mm"])
            R_s_new = max(R_d - h.delta, nose_only_R(nz)["R_mm"])
        else:
            pr, R_d = None, None
            R_s_new = nose_only_R(nz)["R_mm"]
        X_new = nz.X if keep_angle else travel_for_min(X_min_req, R_s_new, nz.z_p, n_theta=n_theta, n_phi=n_phi)
        hist.append({"iter": it, "X_nom_mm": X_new, "R_d_continuous_mm": pr["R_d_mm"] if pr else None, "R_d_mm": R_d,
                     "R_s_mm": R_s_new})
        converged = abs(R_s_new - R_s) < 1e-9 and abs(X_new - nz.X) < 2e-4
        R_s = R_s_new
        nz = replace(nz, X=X_new)
        if converged and it > 0:
            break
    chk = check(R_s, nz, h, sleeve_step=sleeve_step, n_theta=n_theta, n_phi=n_phi)
    chk["history"] = hist
    chk["X_nom_mm"] = nz.X
    chk["alpha_u_rad"] = nz.alpha_u
    chk["alpha_s_rad"] = nz.alpha_s
    chk["z_p_mm"] = nz.z_p
    if h is not None:
        env_fun = lambda R, nz=nz: envelope(R, nz)[:2]                                     # noqa: E731
        pr = pod_contact_radius(env_fun, h)
        chk["R_d_needed_continuous_mm"] = pr["R_d_mm"]
        chk["pod_worst_point"] = pr["worst_point"]
    chk["nose_only_R_mm"] = nose_only_R(nz)["R_mm"]
    return chk


def variants(quick: bool = False) -> Dict:
    """The front-end cases compared in docs/revJ_design.md s3 (CALC)."""
    nt, npf = (9, 24) if quick else (17, 72)
    out = {}
    # (a) round-1 references
    rh = revh_nose()
    out["revH_nose_only"] = close(None, X_min_req=2.75, nz0=rh, keep_angle=True, n_theta=nt, n_phi=npf, sleeve_step=0.75)
    out["revH_with_heel_studyD"] = close(Heel(), nz0=rh, keep_angle=True, n_theta=nt, n_phi=npf, sleeve_step=0.75)
    out["nose2_only"] = close(None, nz0=c1s_nose(), keep_angle=True, n_theta=nt, n_phi=npf, sleeve_step=0.75)
    # (b) integration: C1S nose + study D pod, study N's angle kept (guaranteed travel drops)
    out["revJ_keep_angle"] = close(Heel(), nz0=c1s_nose(), keep_angle=True, n_theta=nt, n_phi=npf)
    # (c) integration: C1S nose + study D pod, 6.0 mm guaranteed (recommended)
    out["revJ"] = close(Heel(), nz0=c1s_nose(), n_theta=nt, n_phi=npf)
    # (d) the same with the Rev H sleeve step (front 1.5 mm wider)
    out["revJ_with_revH_step"] = check(out["revJ"]["R_mm"], replace(c1s_nose(), X=out["revJ"]["X_nom_mm"]), Heel(),
                                       sleeve_step=0.75, n_theta=nt, n_phi=npf)
    # (e) what sets the heel: the pod without its steering ring (a lower bound for a redesigned pod)
    nzj = replace(c1s_nose(), X=out["revJ"]["X_nom_mm"])
    env_fun = lambda R, nz=nzj: envelope(R, nz)[:2]                                           # noqa: E731
    out["pod_without_steering_ring_R_d_mm"] = pod_contact_radius(env_fun, Heel(cap_h=0.0, cap_r_extra=0.0))["R_d_mm"]
    out["pod_steer_axis_55deg_R_d_mm"] = pod_contact_radius(env_fun, Heel(theta0=55.0))["R_d_mm"]
    return out


# --------------------------------------------------------------------------------------------------- side-view data
def side_view(R_s: float, nz: NoseGeo, h: Optional[Heel], theta_deg: float) -> Dict:
    """2-D side view (tilt plane) of the front end at a tilt: paper line, ring, sleeve front, nose at rest and at the
    usable travel toward / away from the paper, the ball, and the wheel.  Used by the figure (CALC)."""
    th = math.radians(theta_deg)
    a2 = np.array([math.cos(th), math.sin(th)])
    n2 = np.array([math.sin(th), -math.cos(th)])
    C = np.array([0.0, R_s * math.cos(th)])
    s_g = nz.z_p - protrusion(RU.theta_nom, R_s)
    G = C + s_g * a2
    out = {"theta_deg": theta_deg, "C": C.tolist(), "G": G.tolist(), "a2": a2.tolist(), "n2": n2.tolist(), "s_g": s_g,
           "alpha_u": nz.alpha_u}
    if h is not None:
        R_d = R_s + h.delta
        cpt = C + R_d * n2                              # the wheel's contact point in this view (lowest rim point + delta)
        nn = np.array([-n2[0], -n2[1]])                 # inward radial in the view
        out["wheel_centre"] = (cpt + h.r_e * (math.cos(math.radians(h.theta0)) * nn + math.sin(math.radians(h.theta0)) * a2)).tolist()
    return out


# --------------------------------------------------------------------------------------------------- ink visibility
def _solids_pen_frame(R_s: float, dm: Dict, h: Optional[Heel], sleeve_step: float, cheek: Optional[Dict]) -> List[Callable]:
    """Occupancy tests f(P) -> bool array for points P (N, 3) in the pen frame (x away from paper, y, s behind the ring
    plane).  The C ring (120 deg open on top), the full sleeve behind it, the heel pod, the page-sensor cheek and the
    nose (centred) with the refill ahead of the ring."""
    rb = dm["ring_bore_r"]
    sb = dm["sleeve_bore_r"]
    sol = []

    def ring(P):
        r = np.hypot(P[:, 0], P[:, 1])
        ang = np.degrees(np.arctan2(np.abs(P[:, 1]), P[:, 0]))      # 0 deg = top (+x), 180 = bottom
        return (P[:, 2] >= 0) & (P[:, 2] <= RU.ring_len) & (r >= rb) & (r <= R_s) & (ang >= 60.0)
    sol.append(ring)

    def sleeve(P):
        r = np.hypot(P[:, 0], P[:, 1])
        s = P[:, 2]
        r_out = np.minimum(R_s + sleeve_step + np.clip(s - RU.ring_len, 0, None) * 0.5, 12.0)
        return (s > RU.ring_len) & (s <= 60.0) & (r >= sb) & (r <= r_out)
    sol.append(sleeve)

    def nose(P):
        r = np.hypot(P[:, 0], P[:, 1])
        s = P[:, 2]
        nozr = RU.nozzle_r_front + (RU.carrier_r - RU.nozzle_r_front) * np.clip(s, 0, RU.nozzle_len) / RU.nozzle_len
        return ((s >= 0) & (s <= 60) & (r <= nozr)) | ((s < 0) & (r <= REFILL_R))
    sol.append(nose)
    if h is not None:
        th = math.radians(h.theta0)
        n = np.array([math.cos(th), 0.0, math.sin(th)])
        contact = np.array([-(R_s + h.delta), 0.0, 0.0])
        wc = contact + h.r_e * n

        def pod(P):
            d = np.linalg.norm(P - wc, axis=1)
            q = P - contact
            hh = q @ n
            rad = np.linalg.norm(q - np.outer(hh, n), axis=1)
            cap = (hh >= 2 * h.r_e) & (hh <= 2 * h.r_e + h.cap_h) & (rad <= h.cap_r + h.t)
            # the pod housing behind the ring (box, as the drive study's pod): radial R_d-3.4 .. R_d-0.3, 4 mm long
            r = np.hypot(P[:, 0], P[:, 1])
            box = (P[:, 2] >= RU.ring_len) & (P[:, 2] <= RU.ring_len + 4.0) & (np.abs(P[:, 1]) <= 2.0) & (P[:, 0] < 0) & \
                  (r >= R_s + h.delta - 3.4) & (r <= R_s + h.delta - 0.3)
            return (d <= h.r_e + h.t) | cap | box
        sol.append(pod)
    if cheek is not None:
        cx, cy, s0, s1, sx, sy = cheek["x"], cheek["y"], cheek["s0"], cheek["s1"], cheek["sx"], cheek["sy"]

        def ch(P):
            return (np.abs(P[:, 0] - cx) <= sx / 2) & (np.abs(P[:, 1] - cy) <= sy / 2) & (P[:, 2] >= s0) & (P[:, 2] <= s1)
        sol.append(ch)
    return sol


def _world_to_pen(theta: float):
    """Rotation and offset: a world point (paper z = 0; the pen's back rises toward +x_w) -> pen frame."""
    a = np.array([math.cos(theta), 0.0, math.sin(theta)])           # pen axis (ball -> back) in the world
    tp = np.array([math.sin(theta), 0.0, -math.cos(theta)])         # toward the paper, perpendicular to the axis
    return a, tp


def visibility(R_s: float, nz: NoseGeo, h: Optional[Heel] = None, sleeve_step: float = 0.0, cheek: Optional[Dict] = None,
               thetas: Sequence[float] = (35.0, 50.0, 75.0), elevations: Sequence[float] = (40.0, 55.0, 70.0),
               azimuths: Sequence[float] = tuple(range(-90, 91, 15)), ink_len: float = 3.0, n_dir: int = 24,
               n_ink: int = 7, step: float = 0.1, reach: float = 40.0) -> Dict:
    """Share of the most recent ink (a 3 mm stroke leaving the ball in any of n_dir directions on the paper) and of the
    ball's contact point that the writer can see, from eye directions (elevation above the paper; azimuth relative to
    the pen's back direction, + = to the pen's left when looking from behind it) (CALC; eye directions ASSUMPTION).
    A paper point is hidden if the straight ray toward the eye enters any front-end solid within `reach` mm."""
    dm = FEN.dims(R_s, FEN.Nose(z_p=nz.z_p, travel=nz.X, stop_extra=nz.stop_extra), RU)
    sol = _solids_pen_frame(R_s, dm, h, sleeve_step, cheek)
    res = {}
    for t in thetas:
        th = math.radians(t)
        a, tp = _world_to_pen(th)
        ey = np.array([0.0, 1.0, 0.0])
        C = np.array([0.0, 0.0, R_s * math.cos(th)])                 # ring-plane centre in the world
        B = C - protrusion(t, R_s) * a                                 # ball centre
        B[2] = 0.0                                                     # its contact point on the paper
        pts = [B.copy()]
        for k in range(n_dir):
            ang = 2 * math.pi * k / n_dir
            d = np.array([math.cos(ang), math.sin(ang), 0.0])
            for j in range(1, n_ink + 1):
                pts.append(B + d * ink_len * j / n_ink)
        pts = np.array(pts)
        per = {}
        for el in elevations:
            for az in azimuths:
                e_back = np.array([1.0, 0.0, 0.0])                     # the pen's back direction on the paper (+x_w)
                e_left = np.array([0.0, 1.0, 0.0])
                aa = math.radians(az)
                hor = math.cos(aa) * e_back + math.sin(aa) * e_left
                eye = math.cos(math.radians(el)) * hor + math.sin(math.radians(el)) * np.array([0.0, 0.0, 1.0])
                ts = np.arange(step, reach, step)
                R = pts[:, None, :] + ts[None, :, None] * eye[None, None, :]        # (Np, Nt, 3) world
                Q = R - C[None, None, :]
                Pp = np.stack([-(Q @ tp), Q @ ey, Q @ a], axis=-1).reshape(-1, 3)    # pen frame: x = away from paper
                hit = np.zeros(Pp.shape[0], bool)
                for f in sol:
                    hit |= f(Pp)
                hidden = hit.reshape(len(pts), len(ts)).any(axis=1)
                per[f"el{el:g}_az{az:+g}"] = {"ball_visible": bool(not hidden[0]),
                                              "recent_ink_visible_share": float(1.0 - hidden[1:].mean())}
        vals = list(per.values())
        res[f"{t:g}"] = {"by_eye": per, "ball_visible_share": float(np.mean([v["ball_visible"] for v in vals])),
                         "recent_ink_visible_mean": float(np.mean([v["recent_ink_visible_share"] for v in vals])),
                         "recent_ink_visible_min": float(np.min([v["recent_ink_visible_share"] for v in vals]))}
    return res


# --------------------------------------------------------------------------------------------------- page sensor window
def window_height(R_s: float, s: float, r: float, phi_deg: float, theta_deg, roll_deg=0.0, lift=0.0):
    """Height (mm) above the paper of a handle point at s behind the ring plane, radius r, azimuth phi from the bottom
    (paper side), at tilt theta and pen roll psi; the ring's lowest rim point is on the paper, raised by `lift` when the
    sprung wheel holds the ring off the paper (light writing).  h = (R_s - r cos(phi + psi)) cos(theta) + s sin(theta)."""
    th = np.radians(np.asarray(theta_deg, float))
    ph = np.radians(phi_deg + np.asarray(roll_deg, float))
    return (R_s - r * np.cos(ph)) * np.cos(th) + s * np.sin(th) + lift


def page_sensor_window(R_s: float, R_d: float, nz: NoseGeo, h: Heel, target: float = 2.4, band: float = 0.2,
                       roll_design: float = 10.0) -> Dict:
    """Place the page sensor's lens reference point (PMW3360 class: lens plane 2.2-2.6 mm from the surface, MFR OPT-54)
    where its height changes least over 35-75 deg of tilt and +-roll_design of roll, outside the wheel pod (|y| >= 2.2 mm
    at the bottom) and outside the nose's envelope at the stop (CALC).  Reports the height band over tilt, roll and the
    heel lift for the chosen point and for study D's placement (bottom, z 14-20)."""
    thetas = np.linspace(35.0, 75.0, 41)
    rolls = np.linspace(-roll_design, roll_design, 9)
    s_env, env, _ = envelope(R_s, nz)
    best = None
    for phi in np.arange(12.0, 46.0, 1.0):
        for s in np.arange(0.5, 6.01, 0.25):
            for dr in np.arange(0.2, 4.01, 0.05):
                r = (R_s - dr) / math.cos(math.radians(phi))
                y = r * math.sin(math.radians(phi))
                if y < 2.2 + 1.0:                                  # a 2 mm-wide window beside the 4 mm-wide pod (|y| <= 2.2)
                    continue
                if r - 1.0 < float(np.interp(s, s_env, env)) + 0.3:  # sensor body inboard of the window clears the nose
                    continue
                H = window_height(R_s, s, r, phi, thetas[:, None], rolls[None, :])
                err = float(np.max(np.abs(H - target)))
                if best is None or err < best["max_dev_mm"]:
                    best = {"phi_deg": float(phi), "s_mm": float(s), "r_mm": float(r), "y_mm": float(y), "max_dev_mm": err}
    phi, s, r = best["phi_deg"], best["s_mm"], best["r_mm"]

    def band_at(roll):
        H = window_height(R_s, s, r, phi, thetas[:, None], np.linspace(-roll, roll, 9)[None, :])
        return [float(H.min()), float(H.max())]
    lift_max = h.delta * math.cos(math.radians(35.0)) + h.r_e * (1 - math.cos(math.radians(15.0)))
    out = {"target_mm": target, "tolerance_mm": band, "window": best,
           "height_band_mm": {"roll0": band_at(0.0), "roll10": band_at(10.0), "roll20": band_at(20.0)},
           "height_with_heel_lift_mm": [float(window_height(R_s, s, r, phi, thetas).min()),
                                        float(window_height(R_s, s, r, phi, thetas, lift=lift_max).max())],
           "roll_tolerance_deg_for_band": None}
    for roll in np.arange(0.0, 30.01, 0.5):
        lo, hi = band_at(roll)
        if lo < target - band or hi > target + band:
            out["roll_tolerance_deg_for_band"] = float(max(roll - 0.5, 0.0))
            break
    # study D's placement: bottom (phi 0), z 14-20 behind the ball at 50 deg; lens plane at the sensor's paper face
    s_D = 14.0 - protrusion(50.0, 8.40)
    rD = 8.6 + 2.0
    out["studyD_placement_on_revJ"] = {
        "note": "study D put the sensor at the bottom, z 14-20, 8.6 mm off the axis (Rev H nose); on the Rev J front the "
                "same spot lies inside the C1S nose's swing (r_env at the stop about 9.3 mm)",
        "nose_env_at_s_mm": float(np.interp(s_D, s_env, env))}
    return out
