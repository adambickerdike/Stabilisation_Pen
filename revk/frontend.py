r"""The Rev K front end for a translation nib (CALCULATION on a PROPOSED DESIGN; clearance rules ASSUMPTION as DEC-034).

The handle rests on the paper at the skid ring's front outer edge, contact radius R_s; the ball centre sits
p(theta) = (R_s cos(theta) - r_b) / sin(theta) ahead of the ring plane (opt/inertial/front_end.protrusion, read-only).
The layout's z = 0 is the ball tip at 50 deg with the nib centred, so the ring plane is at z_ring = p(50 deg); s is the
distance behind the ring plane.  B1 translates the refill and its carrier by up to the stop (1.26 mm) in any direction;
its envelope is the refill (r 1.175 mm) ahead of the carrier's front guide station (z 9-11, r 2.0 mm) and the carrier
tube (r 1.6 mm) behind it, each plus the stop (no tilt: a translation nib swings nothing).

What sets R_s without a heel wheel: not the nib (a 4 mm ring would clear it) but the page sensor.  Its lens must stay
2.2-2.6 mm above the paper over 35-75 deg (MFR OPT-61), which puts the window about 1.4 mm inboard of the contact and
about 2 mm behind the ring plane (the tilt-invariant point, revj/frontend.py); at the bottom of the ring (azimuth 0) the
window is insensitive to roll to first order.  The folded optics block (lens + 45 deg mirror, 2 x 2 x 2 mm,
ASSUMPTION as Rev J) must clear the nib's envelope at the stop by 0.3 mm.  front_close() finds the smallest R_s on the
0.25 mm grid that passes every rule with the window at the bottom.

Also here: the height band of the lens over tilt and roll, the depth of field against the lifts between strokes
(REQ-BNIB-017), ink visibility (ray casting as revj/frontend.visibility with Rev K's solids), the grip and the hand, and
the heel pod for the heel-module variant (revj/frontend.pod_points and pod_contact_radius, read-only).
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths
from . import params as PR
from .params import val

ensure_paths()
from revj import frontend as RFR  # noqa: E402  (read-only reuse: window_height, pod_points, pod_contact_radius, EYES)

R_B = 0.35
STOP = None


def stop_mm() -> float:
    return val(PR.B1["stop_mm"])


def protrusion(theta_deg: float, R_s: float, r_b: float = R_B) -> float:
    th = math.radians(theta_deg)
    return (R_s * math.cos(th) - r_b) / math.sin(th)


def nib_envelope(R_s: float, s: np.ndarray, stop: Optional[float] = None) -> np.ndarray:
    """Radius (mm) of B1's moving refill + carrier at the stop against s behind the ring plane (CALC)."""
    st = stop_mm() if stop is None else stop
    z_ring = protrusion(50.0, R_s)
    z = np.asarray(s, float) + z_ring
    zc = val(PR.FRONT["carrier_front_z_mm"])
    gs = val(PR.FRONT["guide_station"])
    r = np.where(z < zc, val(PR.FRONT["refill_r_mm"]),
                 np.where(z <= zc + gs["len_mm"], gs["r_mm"], val(PR.FRONT["carrier_r_mm"])))
    return r + st


def window_height(R_s, s, r, phi_deg, theta_deg, roll_deg=0.0, lift=0.0):
    return RFR.window_height(R_s, s, r, phi_deg, theta_deg, roll_deg, lift)


def best_window(R_s: float, phi_set: Sequence[float] = (0.0,), target: float = 2.4, band: float = 0.2,
                roll_design: float = 20.0, y_min: float = 0.0, stop: Optional[float] = None) -> Optional[Dict]:
    """The page-sensor window (azimuth phi from the bottom, s behind the ring plane, radius r) whose lens height stays
    closest to 2.4 mm over 35-75 deg and +-roll_design, subject to: inside the band with no roll, the optics block
    clear of the nib's envelope at the stop by 0.3 mm, the window on the part's surface (CALC)."""
    thetas = np.linspace(35.0, 75.0, 41)
    rolls = np.linspace(-roll_design, roll_design, 11)
    ob = val(PR.FRONT["optics_block"])
    c = val(PR.FRONT["c_run_mm"])
    best = None
    for phi in phi_set:
        for s in np.arange(0.5, 4.51, 0.05):
            for dr in np.arange(0.4, 3.51, 0.02):
                r = (R_s - dr) / math.cos(math.radians(phi))
                if r > (R_s if s <= val(PR.FRONT["ring_len_mm"]) else R_s + 0.3 * (s - 1.5)):
                    continue
                if r * math.sin(math.radians(phi)) < y_min:
                    continue
                r_in = r - ob["normal_mm"] * math.cos(math.radians(50.0)) - ob["half_width_mm"]
                s_in = s + ob["normal_mm"] * math.sin(math.radians(50.0))
                if r_in < float(nib_envelope(R_s, np.array([s_in]), stop=stop)[0]) + c:
                    continue
                H0 = window_height(R_s, s, r, phi, thetas)
                if float(np.max(np.abs(H0 - target))) > band - 0.02:
                    continue
                H = window_height(R_s, s, r, phi, thetas[:, None], rolls[None, :])
                err = float(np.max(np.abs(H - target)))
                if best is None or err < best["max_dev_mm"]:
                    best = {"phi_deg": float(phi), "s_mm": float(s), "r_mm": float(r), "dr_mm": float(dr),
                            "y_mm": float(r * math.sin(math.radians(phi))), "max_dev_mm": err,
                            "block_inner_r_mm": r_in, "block_s_mm": s_in}
    return best


def band_at(R_s: float, w: Dict, roll: float) -> List[float]:
    thetas = np.linspace(35.0, 75.0, 41)
    H = window_height(R_s, w["s_mm"], w["r_mm"], w["phi_deg"], thetas[:, None], np.linspace(-roll, roll, 21)[None, :])
    return [float(H.min()), float(H.max())]


def roll_tolerance(R_s: float, w: Dict, target: float = 2.4, band: float = 0.2) -> float:
    for roll in np.arange(0.0, 45.01, 0.5):
        lo, hi = band_at(R_s, w, roll)
        if lo < target - band or hi > target + band:
            return float(max(roll - 0.5, 0.0))
    return 45.0


def front_close(heel: bool = False, quick: bool = False, travel: Optional[float] = None,
                stop: Optional[float] = None, body_od_mm: Optional[float] = None) -> Dict:
    """The smallest ring (0.25 mm grid) that passes every front-end rule; without a heel the window is at the bottom
    (azimuth 0), with the heel pod it goes beside the pod (|y| >= 2.7 mm, Rev J's rule) (CALC)."""
    step = val(PR.FRONT["R_step_mm"])
    c = val(PR.FRONT["c_run_mm"])
    lip = val(PR.FRONT["ring_wall_min_mm"])
    hist = []
    R = 3.75
    chosen = None
    while R <= 12.0:
        env_ring = float(np.max(nib_envelope(R, np.linspace(0.0, val(PR.FRONT["ring_len_mm"]), 16), stop=stop)))
        bore = env_ring + c
        ok_lip = R - bore >= lip
        if heel:
            pr = heel_pod(R)
            ok_heel = pr["R_d_needed_mm"] <= R + 0.35 + 1e-9
            phis = np.arange(20.0, 46.0, 1.0 if not quick else 2.5)
            w = best_window(R, phis, y_min=2.7, stop=stop) if ok_heel else None
        else:
            ok_heel = True
            w = best_window(R, (0.0,), stop=stop)
        hist.append({"R_s_mm": R, "ring_bore_r_mm": bore, "lip_ok": ok_lip, "heel_ok": ok_heel, "window": w})
        if ok_lip and ok_heel and w is not None:
            chosen = R
            break
        R += step
    if chosen is None:
        raise ValueError("no front-end layout within 12 mm contact radius")
    w = hist[-1]["window"]
    z_ring = protrusion(50.0, chosen)
    out = {"R_s_mm": chosen, "R_d_mm": chosen + 0.35 if heel else None, "z_ring_mm": z_ring,
           "ring_bore_r_mm": hist[-1]["ring_bore_r_mm"], "ring_lip_mm": chosen - hist[-1]["ring_bore_r_mm"],
           "window": w, "roll_tolerance_deg": roll_tolerance(chosen, w),
           "band_mm": {f"roll{r:g}": band_at(chosen, w, r) for r in (0.0, 5.0, 10.0, 20.0)},
           "history": hist, "heel": heel,
           "protrusion_mm": {f"{t:g}": protrusion(t, chosen) for t in (35.0, 40.0, 50.0, 60.0, 70.0, 75.0)},
           "label": "CALCULATION (front-end closure, rules ASSUMPTION: DEC-034 lip 1.0 mm, 0.3 mm running clearances; "
                    "optics block ASSUMPTION; lens band MANUFACTURER OPT-61)"}
    out.update(checks(chosen, w, travel=travel, body_od_mm=body_od_mm))
    return out


def checks(R_s: float, w: Dict, travel: Optional[float] = None,
           body_od_mm: Optional[float] = None) -> Dict:
    """Front-end rules at the chosen ring: the nozzle (carrier front) above the paper over 35-75 deg with the nib at its
    usable travel toward the paper, the refill slide, the sleeve cone above the paper, the lens depth of field against
    the lifts between strokes (CALC)."""
    z_ring = protrusion(50.0, R_s)
    trav = val(PR.B1["travel_mm"]) if travel is None else travel
    zc = val(PR.FRONT["carrier_front_z_mm"])
    gs = val(PR.FRONT["guide_station"])
    s_cf = zc - z_ring
    worst_noz = 1e9
    for t in np.linspace(35.0, 75.0, 41):
        th = math.radians(t)
        # the carrier's front guide station, bottom edge, nib displaced toward the paper
        s = s_cf
        # at tilt t the refill (and carrier) sit (p(t) - p(50)) further forward? No: the CARRIER does not slide; only the refill
        h = (R_s - (gs["r_mm"] + trav)) * math.cos(th) + s * math.sin(th)
        worst_noz = min(worst_noz, h)
    p = {t: protrusion(t, R_s) for t in (35.0, 75.0)}
    slide_tilt = p[35.0] - p[75.0]
    corr = {t: trav / math.tan(math.radians(t)) for t in (35.0, 50.0, 75.0)}
    zg = val(PR.ENVELOPE["grip_full_od_from_z_mm"])
    r_grip = (val(PR.ENVELOPE["handle_od_held_mm"]) if body_od_mm is None else body_od_mm) / 2
    if r_grip < R_s:
        raise ValueError("body radius must accommodate the selected front ring")
    L_c = zg - (z_ring + val(PR.FRONT["ring_len_mm"]))
    slope = (r_grip - R_s) / L_c
    cone_clear = min((R_s - (R_s + slope * max(s - 1.5, 0.0))) * math.cos(math.radians(t)) + s * math.sin(math.radians(t))
                     for t in np.linspace(35.0, 75.0, 21) for s in np.linspace(1.5, L_c + 1.5, 41))
    dof = val(PR.FRONT["lens_band_mm"])
    lift_needed = val(PR.FRONT["lift_cutoff_needed_mm"])
    lift_tracked = (dof[2] - 2.4)                                  # height margin above the nominal lens plane
    return {"nozzle_above_paper_min_mm": worst_noz, "nozzle_rule_margin_mm": worst_noz - val(PR.FRONT["c_paper_mm"]),
            "refill_slide_tilt_35_75_mm": slide_tilt,
            "refill_slide_correction_mm": {f"{k:g}": v for k, v in corr.items()},
            "refill_slide_total_mm": slide_tilt + 2 * corr[35.0],
            "sleeve_cone": {"from_z_mm": z_ring + 1.5, "to_z_mm": zg, "front_d_mm": 2 * R_s,
                            "body_od_mm": 2 * r_grip, "half_angle_deg":
                            math.degrees(math.atan(slope)), "min_height_above_paper_mm": cone_clear},
            "lens_dof": {"band_mm": dof, "lift_tracked_mm": lift_tracked, "lift_needed_mm": lift_needed,
                         "passes_REQ_BNIB_017": lift_tracked >= lift_needed,
                         "note": "OPT-61 gives the PMW3610's lens plane 2.2-2.6 mm (+-0.2 mm depth of field); a lift of the "
                                 "handle between strokes (sim writer: 1.2 mm median) takes the window out of that band; "
                                 "whether the die keeps tracking beyond it on paper is unknown (EXP-J10 / EXP-T04)"}}


# ------------------------------------------------------------------------------------------------ heel pod (variant)
def heel_pod(R_s: float) -> Dict:
    """Study D's wheel pod (revj/frontend.Heel, read-only) against the translation nib's envelope at the stop: the
    smallest wheel contact radius R_d whose pod clears the nib by 0.3 mm (CALC)."""
    h = RFR.Heel()

    def env_fun(R):
        s = np.linspace(-8.0, 16.0, 481)
        return s, nib_envelope(R, s)
    pr = RFR.pod_contact_radius(env_fun, h, R0=R_s + 0.35, ring_offset=h.delta)
    return {"R_d_needed_mm": pr["R_d_mm"], "worst_point": pr["worst_point"], "delta_mm": h.delta}


def heel_shafts(R_s: float, R_d: float) -> Dict:
    """Can study D's straight 0.8 mm shafts (in 1.0 mm liners, Rev J: 10.8 mm from the axis in the wall) reach a pod at
    R_d with a small front?  They cannot run straight: the sleeve cone is only R_s + ... at the pod.  Rev K's variant puts
    a transfer gear pair where the sleeve reaches 23.2 mm (0.3 mm skin outside the liners at r 10.8) and short inner
    shafts forward to the pod inside the cone (CALC)."""
    z_ring = protrusion(50.0, R_s)
    zg = val(PR.ENVELOPE["grip_full_od_from_z_mm"])
    r_grip = val(PR.ENVELOPE["handle_od_held_mm"]) / 2
    L_c = zg - (z_ring + 1.5)
    slope = (r_grip - R_s) / L_c

    def r_cone(z):
        return R_s + slope * min(max(z - z_ring - 1.5, 0.0), L_c) if z >= z_ring + 1.5 else R_s
    liner_out = 10.8 + 0.5
    z_gear = next(z for z in np.arange(z_ring, 60.0, 0.1) if r_cone(z) - liner_out >= 0.3)
    r_inner = R_d - 0.6                                            # the pod's shaft entry (study D: 0.6 mm in from the contact)
    z_pod1 = z_ring + 1.5 + 4.0
    skin = min(r_cone(z) - (r_inner + 0.5) for z in np.arange(z_pod1, z_gear, 0.1))
    return {"gearbox_z_mm": z_gear, "inner_shaft_r_mm": r_inner, "inner_shaft_len_mm": z_gear - z_pod1,
            "skin_outside_inner_liners_mm": skin, "passes_skin_rule": skin >= 0.3,
            "note": "the inner shafts run in grooves of the sleeve wall (Rev J's rule: 0.3 mm of skin outside the liners); "
                    "a transfer mesh (efficiency 0.9, ASSUMPTION) at the gearbox",
            "label": "CALCULATION (geometry; study D shaft and liner sizes)"}


# ------------------------------------------------------------------------------------------------ ink visibility
def _solids(R_s: float, theta: float, open_deg: float = 120.0, open_len: float = 0.0, clear_len: float = 0.0,
            clear_half_deg: float = 120.0, r_grip: float = 12.0) -> List[Callable]:
    z_ring = protrusion(50.0, R_s)
    rb = float(np.max(nib_envelope(R_s, np.linspace(0, 1.5, 8)))) + val(PR.FRONT["c_run_mm"])
    zg = val(PR.ENVELOPE["grip_full_od_from_z_mm"])
    L_c = zg - (z_ring + 1.5)
    wall = val(PR.FRONT["sleeve_wall_mm"])
    half_open = open_deg / 2.0
    p_ball = protrusion(theta, R_s)

    def ang(P):
        return np.degrees(np.arctan2(np.abs(P[:, 1]), P[:, 0]))

    def ring(P):
        r = np.hypot(P[:, 0], P[:, 1])
        return (P[:, 2] >= 0) & (P[:, 2] <= 1.5) & (r >= rb) & (r <= R_s) & (ang(P) >= half_open)

    def sleeve(P):
        r = np.hypot(P[:, 0], P[:, 1])
        s = P[:, 2]
        r_out = R_s + (r_grip - R_s) * np.clip((s - 1.5) / L_c, 0.0, 1.0)
        r_in = np.maximum(r_out - wall - 1.5, nib_envelope(R_s, s) + 0.3)
        a = ang(P)
        opened = (s <= 1.5 + open_len) & (a < half_open)
        clear = (s <= 1.5 + clear_len) & (a < clear_half_deg)
        return (s > 1.5) & (s <= 60.0) & (r >= r_in) & (r <= r_out) & ~opened & ~clear

    def nib(P):
        r = np.hypot(P[:, 0], P[:, 1])
        s = P[:, 2]
        z = s + z_ring
        zc = val(PR.FRONT["carrier_front_z_mm"])
        tip = 0.35 + (1.175 - 0.35) * np.clip((s + p_ball) / 3.0, 0.0, 1.0)
        rr = np.where(z < zc, 1.175, 2.0)
        return ((s >= -p_ball) & (s < 60) & (r <= np.where(s < -p_ball + 3.0, tip, rr)))
    return [ring, sleeve, nib]


VIS_OPTIONS = {
    "ring_open_120": dict(),
    "open_120_into_sleeve_10": dict(open_len=10.0),
    "clear_top_15_w120": dict(clear_len=15.0, clear_half_deg=120.0),
}


def first_visible(R_s: float, theta: float, eye_el: float, eye_az: float, trail_deg: float, opt: Dict,
                  ds=np.arange(0.25, 6.01, 0.25), step: float = 0.1, reach: float = 45.0) -> float:
    sol = _solids(R_s, theta, **opt)
    th = math.radians(theta)
    a, tp = RFR._world_to_pen(th)
    ey = np.array([0.0, 1.0, 0.0])
    C = np.array([0.0, 0.0, R_s * math.cos(th)])
    B = C - protrusion(theta, R_s) * a
    B[2] = 0.0
    aa, ee = math.radians(eye_az), math.radians(eye_el)
    eye = np.array([math.cos(ee) * math.cos(aa), math.cos(ee) * math.sin(aa), math.sin(ee)])
    ts = np.arange(step, reach, step)
    d = np.array([math.cos(math.radians(trail_deg)), math.sin(math.radians(trail_deg)), 0.0])
    P0 = B[None, :] + ds[:, None] * d[None, :]
    Rr = P0[:, None, :] + ts[None, :, None] * eye[None, None, :]
    Q = Rr - C[None, None, :]
    Pp = np.stack([-(Q @ tp), Q @ ey, Q @ a], axis=-1).reshape(-1, 3)
    hit = np.zeros(Pp.shape[0], bool)
    for f in sol:
        hit |= f(Pp)
    vis = ~hit.reshape(len(ds), len(ts)).any(axis=1)
    return float(ds[np.argmax(vis)]) if vis.any() else float("inf")


def visibility(R_s: float, quick: bool = False) -> Dict:
    """First-visible distance of the fresh ink behind the ball over tilt x eye position (Rev J.1's sweep: elevation
    40-70 deg, azimuth 0-60 deg to the writer's side, trail at 120 deg; ASSUMPTION range), for three Rev K fronts (CALC)."""
    thetas, els, azs = ((50.0,), (55.0,), (-30.0,)) if quick else ((35.0, 50.0, 60.0, 75.0), (40.0, 55.0, 70.0), (0.0, -30.0, -60.0))
    out = {}
    for name, opt in VIS_OPTIONS.items():
        rows = []
        for t in thetas:
            for el in els:
                for az in azs:
                    rows.append({"tilt_deg": t, "eye_el_deg": el, "eye_az_deg": az,
                                 "first_visible_mm": first_visible(R_s, t, el, az, -120.0, opt)})
        fin = [r["first_visible_mm"] for r in rows]
        out[name] = {"rows": rows, "share_within_1mm": float(np.mean([f <= 1.0 for f in fin])),
                     "share_within_3mm": float(np.mean([f <= 3.0 for f in fin])),
                     "median_mm": float(np.median([f if np.isfinite(f) else 99.0 for f in fin]))}
    return {"options": out, "revJ1_reference": {"within_1mm": 0.47, "within_3mm": 0.61, "revJ_within_1mm": 0.22,
                                                "source": "docs/revJ1_design.md s7 (CALC)"},
            "label": "CALCULATION (ray casting; eye positions and trail direction ASSUMPTION as Rev J.1)"}


# ------------------------------------------------------------------------------------------------ the hand
def hand(R_s: float) -> Dict:
    """The grip against the Rev H hand model: diameter under each finger pad, the front cone, and how far the handle's
    underside sits above the paper at the finger pads at 35 deg, against an ordinary 9 mm pen held 25 mm from its tip
    (CALC; hand positions ASSUMPTION)."""
    z_ring = protrusion(50.0, R_s)
    zg = val(PR.ENVELOPE["grip_full_od_from_z_mm"])
    r_grip = val(PR.ENVELOPE["handle_od_held_mm"]) / 2
    L_c = zg - (z_ring + 1.5)

    def r_at(z):
        return R_s + (r_grip - R_s) * min(max((z - z_ring - 1.5) / L_c, 0.0), 1.0)
    pads = val(PR.ENVELOPE["finger_pads_z_mm"])
    half = val(PR.ENVELOPE["finger_pad_half_mm"])
    th = math.radians(35.0)
    shift = protrusion(35.0, R_s) - protrusion(50.0, R_s)
    rows = []
    for zp in pads:
        h = (zp + shift) * math.sin(th) - r_at(zp) * math.cos(th) + R_B
        rows.append({"pad_z_mm": zp, "d_mm": 2 * r_at(zp), "d_front_edge_mm": 2 * r_at(zp - half),
                     "underside_above_paper_35deg_mm": h})
    op = val(PR.ENVELOPE["ordinary_pen"])
    h_ord = op["pad_z_mm"] * math.sin(th) - op["od_mm"] / 2 * math.cos(th)
    shift_j = protrusion(35.0, 11.65) - protrusion(50.0, 11.65)
    h_revj = (26.0 + shift_j) * math.sin(th) - 12.0 * math.cos(th) + R_B
    return {"pads": rows, "front_d_mm": 2 * R_s, "cone_z_mm": [z_ring + 1.5, zg],
            "all_pads_on_full_grip": all(r["d_front_edge_mm"] >= 2 * r_grip - 1e-6 for r in rows),
            "ordinary_pen_underside_35deg_mm": h_ord, "revJ_front_pad_underside_35deg_mm": h_revj,
            "front_pad_vs_ordinary_mm": rows[0]["underside_above_paper_35deg_mm"] - h_ord,
            "label": "CALCULATION (geometry; hand model ASSUMPTION, Rev H)"}
