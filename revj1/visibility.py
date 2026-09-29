r"""P5: can the writer see the fresh ink next to the ball?  Ray casting as revj.frontend.visibility (read-only reuse of
its nose, pod and page-sensor-cheek solids), with the ring and the sleeve rebuilt here so that they can be opened wider
or made partly transparent, and with the eye position swept instead of fixed.

Options (PROPOSED DESIGN variants of the Rev J front end):
  revJ            C ring open 120 deg on top, the opening carried 10 mm into the sleeve (Rev J, chosen there)
  open_150/180    the same, opened to 150 / 180 deg (the ring still spans the bottom and the sides, where it touches the
                  paper at up to +-20 deg of roll and holds the wheel slot)
  clear_sleeve_L  a transparent top sector of the sleeve (+-75 deg about the top) over its first L mm behind the ring;
                  the ring itself opaque
  clear_ring      the ring's top part transparent too (sapphire; PMMA or PC would haze on paper)
  no_front        ring and sleeve fully removed: the upper bound, only the nose, the refill and the heel pod block
Eye positions (ASSUMPTION range; no writing-posture source with eye angles could be opened, see the doc): elevation
40-70 deg above the paper, azimuth 0-60 deg to the left of the pen's back direction (right-handed), and mirrored for
left-handed writers; the fresh ink trails at 120 deg from the pen's back direction (Rev J's assumption).
All CALC; nothing measured (EXP-J08 with people).
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths

ensure_paths()
from revj import frontend as RFR  # noqa: E402
from opt.inertial.front_end import protrusion  # noqa: E402
from nose2 import frontend as FEN  # noqa: E402

RU = RFR.RU


def _solids(R_s: float, dm: Dict, h, p_ball: float, L_taper: float, open_deg: float = 120.0, open_len: float = 10.0,
            clear_sleeve_len: float = 0.0, clear_half_deg: float = 75.0, clear_ring: bool = False, no_front: bool = False,
            r_grip: float = 12.0) -> List[Callable]:
    base = RFR._solids_pen_frame(R_s, dm, h, 0.0, None, p_ball=p_ball, r_grip=r_grip, L_taper=L_taper,
                                 sleeve_open_len=open_len)
    nose, pod = base[2], (base[3] if len(base) > 3 else None)
    rb, sb = dm["ring_bore_r"], dm["sleeve_bore_r"]
    half_open = open_deg / 2.0

    def ang(P):
        return np.degrees(np.arctan2(np.abs(P[:, 1]), P[:, 0]))          # 0 = top (+x), 180 = bottom

    def ring(P):
        r = np.hypot(P[:, 0], P[:, 1])
        a = ang(P)
        solid = (P[:, 2] >= 0) & (P[:, 2] <= RU.ring_len) & (r >= rb) & (r <= R_s) & (a >= half_open)
        if clear_ring:
            solid &= ~(a < clear_half_deg)
        return solid

    def sleeve(P):
        r = np.hypot(P[:, 0], P[:, 1])
        s = P[:, 2]
        r_out = R_s + (r_grip - R_s) * np.clip((s - RU.ring_len) / L_taper, 0.0, 1.0)
        a = ang(P)
        opened = (s <= RU.ring_len + open_len) & (a < half_open)
        clear = (s <= RU.ring_len + clear_sleeve_len) & (a < clear_half_deg)
        return (s > RU.ring_len) & (s <= 60.0) & (r >= sb) & (r <= r_out) & ~opened & ~clear

    sol = [nose]
    if pod is not None:
        sol.append(pod)
    if not no_front:
        sol += [ring, sleeve]
    return sol


OPTIONS = {
    "revJ": dict(),
    "open_150": dict(open_deg=150.0),
    "open_180": dict(open_deg=180.0),
    "clear_sleeve_10": dict(clear_sleeve_len=10.0),
    "clear_sleeve_20": dict(clear_sleeve_len=20.0),
    "clear_sleeve_20_ring": dict(clear_sleeve_len=20.0, clear_ring=True),
    "clear_sleeve_15_w120": dict(clear_sleeve_len=15.0, clear_half_deg=120.0),
    "clear_sleeve_15_w120_ring": dict(clear_sleeve_len=15.0, clear_half_deg=120.0, clear_ring=True),
    "clear_sleeve_30_w120_ring": dict(clear_sleeve_len=30.0, clear_half_deg=120.0, clear_ring=True),
    "no_front": dict(no_front=True),
}
CHOSEN = "clear_sleeve_15_w120"


def first_visible(R_s: float, nz, h, theta: float, eye_el: float, eye_az: float, trail_deg: float, opt: Dict,
                  ds=np.arange(0.25, 6.01, 0.25), step: float = 0.1, reach: float = 45.0) -> float:
    """Distance behind the ball (mm) along the fresh-ink direction at which the paper first becomes visible (CALC)."""
    dm = FEN.dims(R_s, FEN.Nose(z_p=nz.z_p, travel=nz.X, stop_extra=nz.stop_extra), RU)
    z_ring = protrusion(50.0, R_s)
    sol = _solids(R_s, dm, h, protrusion(theta, R_s), max(50.0 - z_ring - RU.ring_len, 1.0), **opt)
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


def sweep(R_s: float, nz, h, thetas: Sequence[float] = (35.0, 50.0, 60.0, 75.0), els: Sequence[float] = (40.0, 55.0, 70.0),
          azs: Sequence[float] = (0.0, -30.0, -60.0), options: Optional[Sequence[str]] = None, quick: bool = False) -> Dict:
    """First-visible distance for every option x tilt x eye position (right-handed; the geometry is mirror-symmetric
    except for the page-sensor cheek, which is not modelled here, so left-handed = mirrored) (CALC)."""
    options = list(options or OPTIONS.keys())
    if quick:
        thetas, els, azs = (50.0,), (55.0,), (-30.0,)
    out = {}
    for name in options:
        rows = []
        for t in thetas:
            for el in els:
                for az in azs:
                    trail = -120.0 if az <= 0 else 120.0
                    fv = first_visible(R_s, nz, h, t, el, az, trail, OPTIONS[name])
                    rows.append({"tilt_deg": t, "eye_el_deg": el, "eye_az_deg": az, "first_visible_mm": fv})
        fin = [r["first_visible_mm"] for r in rows]
        out[name] = {"rows": rows, "share_within_1mm": float(np.mean([f <= 1.0 for f in fin])),
                     "share_within_3mm": float(np.mean([f <= 3.0 for f in fin])),
                     "median_mm": float(np.median([f if np.isfinite(f) else 99.0 for f in fin]))}
    return {"options": out, "thetas": list(thetas), "eye_el": list(els), "eye_az": list(azs),
            "label": "CALC (ray casting; eye positions ASSUMPTION range; trail direction ASSUMPTION)"}


MATERIALS = {
    "PC_hardcoated": {"transmission_pct": "88-90", "pencil_hardness": "HB-2H (uncoated); coated comparable to PMMA",
                      "impact_kJ_m2": "60-80", "source": "LIT AMF-159 (secondary comparison page)",
                      "verdict": "sleeve window: yes (impact-tough); ring: no (hazes on paper)"},
    "PMMA": {"transmission_pct": "92", "pencil_hardness": "2H-4H", "impact_kJ_m2": "1.5-2.5",
             "source": "LIT AMF-159", "verdict": "sleeve window: brittle at a drop; ring: hazes on paper"},
    "sapphire": {"vickers_GPa": 22.5, "density_g_cm3": 3.97, "flexural_MPa": 690, "source": "MFR AMF-160 (Kyocera)",
                 "verdict": "ring insert: scratch-proof against paper fillers; costly; heavier (3.97 g/cm3)"},
}
