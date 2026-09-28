r"""Front-end geometry closure of the Rev H nose (CALC on a PROPOSED DESIGN; every input is an ASSUMPTION).

Why this exists.  The first Rev H layout drew the skid ring as a 15.9 mm annulus whose front face sat 1.5 mm ahead of the
contact plane, while the model H1 used a 5.5 mm contact radius.  Drawn that way the ring sits 1.5-3 mm below the paper at
50 deg.  Worse, a 5.5 mm contact radius leaves no room for the ring itself: at the 3.5 mm stop the swinging nozzle reaches
5.46 mm from the axis in the ring's plane (0.04 mm of wall), and with the nozzle 1.5 mm ahead of the ring the nozzle meets
the paper at steep tilts.  Nothing in H1 checks these clearances.  This module sizes the front end so that it closes over the
writing tilts of REQ-RVH-002 (35-75 deg) and every direction of tip travel:

  1. the skid ring's front outer edge (contact radius R) is the only part of the handle that reaches the paper;
  2. the moving nose clears the ring's bore and the sleeve's bore at the stop;
  3. the nozzle stays above the paper for every correction within the usable travel;
  4. the refill's axial slide (tilt + correction) is known: it sets the refill spring's travel.

Frames.  The handle is fixed by the ring.  s is the axial distance behind the ring plane (s < 0: ahead of it).  The ball
centre sits p(theta) = (R cos(theta) - r_b) / sin(theta) ahead of the ring plane (ball and ring both on the paper; the same
formula as sim/handpen/params.protrusion_centre).  The gimbal is z_p behind the ball at the nominal tilt, so s_g = z_p - p(50).
The layout keeps its convention (z from the ball tip, ring plane at z = p(50 deg); r_b = 0.35 mm is not added).
Nose travel is an angle: usable alpha_u = travel / z_p, stop alpha_s = stop / z_p, so the ball's travel varies with tilt.

Run: python3 -m opt.inertial.front_end [--sens]   -> results/revH/front_end.json (+ fig_front_end.png, .csv)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass, replace
from typing import Dict, List, Optional

import numpy as np

from .revh import RevH

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "revH")
R_B = 0.35                  # ball radius of the D1 mini refill (mm; sim/handpen CONTACT r_b)


@dataclass(frozen=True)
class FrontRules:
    """Clearance rules and fixed front-end dimensions (mm).  ASSUMPTION: engineering judgement, no tolerance stack yet."""
    theta_min: float = 35.0          # REQ-RVH-002 writing tilts
    theta_max: float = 75.0
    theta_nom: float = 50.0
    stop: float = 3.5                # ball travel at the stop, at the nominal tilt
    nozzle_r_front: float = 1.8      # nozzle radius at its front face (guides the 2.35 mm refill)
    nozzle_len: float = 5.0          # nozzle cone length; the 7 mm carrier starts behind it
    carrier_r: float = 3.5
    ring_len: float = 1.5            # skid ring length along the axis (its front face is the contact plane)
    ring_wall_min: float = 1.0       # radial wall of the ring's lip (PTFE-coated POM)
    c_ring: float = 0.3              # radial clearance nose-to-ring at the stop
    c_sleeve: float = 0.5            # radial clearance carrier-to-sleeve at the usable travel (as in the first layout)
    c_paper: float = 0.3             # nozzle-to-paper clearance within the usable travel
    sleeve_step: float = 0.75        # the sleeve's front face is this much larger in radius than the ring
    R_step: float = 0.25             # contact radius is sized in these steps


def protrusion(theta_deg, R, r_b=R_B):
    th = math.radians(theta_deg)
    return (R * math.cos(th) - r_b) / math.sin(th)


def nozzle_r(s, ru: FrontRules):
    """Nozzle outer radius at s behind its front face (the front face sits in the ring plane)."""
    return ru.nozzle_r_front + (ru.carrier_r - ru.nozzle_r_front) * min(max(s, 0.0), ru.nozzle_len) / ru.nozzle_len


def dims(R, d: RevH, ru: FrontRules) -> Dict:
    """Front-end dimensions for a contact radius R (mm)."""
    zp = d.z_p * 1e3
    p50 = protrusion(ru.theta_nom, R)
    s_g = zp - p50
    a_u = d.travel * 1e3 / zp
    a_s = ru.stop / zp
    ss = np.linspace(0.0, ru.ring_len, 31)
    env = float(max(nozzle_r(float(s), ru) + a_s * (s_g - float(s)) for s in ss))   # nose envelope inside the ring at the stop
    r_bore = env + ru.c_ring
    s_cf = ru.nozzle_len                                              # carrier front, behind the ring plane
    r_sleeve = ru.carrier_r + a_u * (s_g - s_cf) + ru.c_sleeve        # sleeve bore at the carrier front (as geometry.py)
    return {"R": R, "p50": p50, "s_g": s_g, "alpha_u": a_u, "alpha_s": a_s, "ring_bore_r": r_bore, "ring_wall": R - r_bore,
            "carrier_front_s": s_cf, "sleeve_bore_r": r_sleeve,
            "carrier_stop_clearance": r_sleeve - (ru.carrier_r + a_s * (s_g - s_cf)),
            "sleeve_front_r": R + ru.sleeve_step}


def _rot(v, k, ang):
    """Rodrigues rotation of v about the unit axis k."""
    return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * np.dot(k, v) * (1.0 - math.cos(ang))


def pose(theta_deg, dm: Dict, phi_deg: float, alpha: float, ru: FrontRules) -> Dict:
    """Handle on the paper at the tilt, nose rotated by alpha toward direction phi (0 = toward the paper in the tilt plane,
    90 = sideways).  Returns the nozzle's lowest point, the refill slide and the ball's travel on the paper."""
    th = math.radians(theta_deg)
    a = np.array([math.cos(th), 0.0, math.sin(th)])             # pen axis, ball -> back
    tp = np.array([math.sin(th), 0.0, -math.cos(th)])           # perpendicular in the tilt plane, toward the paper
    ty = np.array([0.0, 1.0, 0.0])
    R = dm["R"]
    C = np.array([0.0, 0.0, R * math.cos(th)])                  # ring-plane centre: the ring's lowest rim point is on the paper
    G = C + dm["s_g"] * a                                       # gimbal
    ph = math.radians(phi_deg)
    u = math.cos(ph) * tp + math.sin(ph) * ty                   # the ball moves toward +u
    k = np.cross(u, a)
    k = k / np.linalg.norm(k)
    a_n = _rot(a, k, alpha)                                     # nose axis after the tilt (ball -> back)
    # ball centre on the nose axis at height r_b (the refill slides along the nose)
    L = (G[2] - R_B) / a_n[2]
    B = G - L * a_n
    L0 = dm["s_g"] + protrusion(ru.theta_nom, R)                # gimbal-to-ball at the nominal tilt, no correction
    B0 = G - (dm["s_g"] + protrusion(theta_deg, R)) * a
    # nozzle front rim (in the ring plane when undeflected)
    zs = []
    for psi in np.linspace(0.0, 2 * math.pi, 73):
        rho = dm["nozzle_r_front"] * (math.cos(psi) * tp + math.sin(psi) * ty)
        P = G + _rot(-dm["s_g"] * a + rho, k, alpha)
        zs.append(P[2])
    return {"nozzle_min_z": float(min(zs)), "slide": float(L - L0), "ball_travel": float(np.linalg.norm((B - B0)[:2]))}


def check(R, d: Optional[RevH] = None, ru: FrontRules = FrontRules(), n_theta=9, n_phi=24) -> Dict:
    d = d or RevH()
    dm = dims(R, d, ru)
    dm["nozzle_r_front"] = ru.nozzle_r_front
    thetas = np.linspace(ru.theta_min, ru.theta_max, n_theta)
    phis = np.arange(0.0, 360.0, 360.0 / n_phi)
    rows = []
    for t in thetas:
        pu = [pose(t, dm, ph, dm["alpha_u"], ru) for ph in phis]
        ps = [pose(t, dm, ph, dm["alpha_s"], ru) for ph in phis]
        p0 = pose(t, dm, 0.0, 0.0, ru)
        th = math.radians(t)
        rows.append({"theta_deg": float(t), "protrusion_mm": protrusion(t, R),
                     "nozzle_clear_rest_mm": p0["nozzle_min_z"],
                     "nozzle_clear_usable_mm": min(q["nozzle_min_z"] for q in pu),
                     "nozzle_clear_stop_mm": min(q["nozzle_min_z"] for q in ps),
                     "slide_min_mm": min(q["slide"] for q in pu + [p0]), "slide_max_mm": max(q["slide"] for q in pu + [p0]),
                     "ball_travel_usable_min_mm": min(q["ball_travel"] for q in pu),
                     "ball_travel_usable_max_mm": max(q["ball_travel"] for q in pu),
                     # the sleeve's front outer edge (ring_len behind the ring plane, radius R + step) above the paper
                     "sleeve_front_clear_mm": ru.ring_len * math.sin(th) + (R - dm["sleeve_front_r"]) * math.cos(th)})
    slide_lo = min(r["slide_min_mm"] for r in rows)
    slide_hi = max(r["slide_max_mm"] for r in rows)
    sub = [r for r in rows if 40.0 - 1e-9 <= r["theta_deg"] <= 70.0 + 1e-9]
    out = {"R_mm": R, "dims": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in dm.items()}, "by_tilt": rows,
           "ring_wall_mm": dm["ring_wall"], "carrier_stop_clearance_mm": dm["carrier_stop_clearance"],
           "nozzle_clear_usable_min_mm": min(r["nozzle_clear_usable_mm"] for r in rows),
           "nozzle_clear_stop_min_mm": min(r["nozzle_clear_stop_mm"] for r in rows),
           "sleeve_front_clear_min_mm": min(r["sleeve_front_clear_mm"] for r in rows),
           "ball_travel_usable_min_mm": min(r["ball_travel_usable_min_mm"] for r in rows),
           "refill_slide_mm": [slide_lo, slide_hi], "refill_slide_range_mm": slide_hi - slide_lo}
    if sub:
        out["refill_slide_range_40_70_mm"] = (max(r["slide_max_mm"] for r in sub) - min(r["slide_min_mm"] for r in sub))
    out["passes"] = bool(out["ring_wall_mm"] >= ru.ring_wall_min - 1e-9 and out["nozzle_clear_usable_min_mm"] >= ru.c_paper
                         and out["sleeve_front_clear_min_mm"] > 0.0 and out["carrier_stop_clearance_mm"] >= 0.0)
    return out


def size_R(d: Optional[RevH] = None, ru: FrontRules = FrontRules(), R0=5.5, R1=9.0) -> Dict:
    """Smallest contact radius (in R_step steps) that passes every rule."""
    d = d or RevH()
    tried = []
    for R in np.arange(R0, R1 + 1e-9, ru.R_step):
        c = check(float(R), d, ru, n_theta=9, n_phi=24)
        tried.append({"R_mm": float(R), "ring_wall_mm": c["ring_wall_mm"], "nozzle_clear_usable_min_mm": c["nozzle_clear_usable_min_mm"],
                      "sleeve_front_clear_min_mm": c["sleeve_front_clear_min_mm"], "passes": c["passes"]})
        if c["passes"]:
            return {"R_mm": float(R), "tried": tried}
    return {"R_mm": float("nan"), "tried": tried}


def sensitivity(R_old=5.5, R_new=None, seeds=(200, 201), f0s=(8.0, 10.0), amp=1.0e-3, splits=(0.5, 0.7)) -> Dict:
    """Does the contact radius change the simulated results?  H1 (sim/handpen) with the Rev H tracker setting (SIM)."""
    from .evaluate import RevHEval
    from .run_study import revh_tracker_params
    R_new = R_new or RevH().skid_r * 1e3
    prm = revh_tracker_params()
    res = {}
    for R in (R_old, R_new):
        d = replace(RevH(), skid_r=R * 1e-3)
        rows, dist = [], []
        for rr in splits:
            ev = RevHEval(d, r_rot=rr, akf_params=prm)
            for s in seeds:
                for f0 in f0s:
                    c = ev.case(s, f0, amp, controllers=("oracle", "akf"), power=False)
                    rows.append({"r_rot": rr, "seed": s, "f0": f0, "unmod_um": c["unmod_e_rms_um"], "oracle": c["oracle"]["ratio"],
                                 "akf": c["akf"]["ratio"]})
            if rr == 0.5:
                dist = [ev.distortion(s, "lognormal")["distortion_um"] for s in seeds]
        res[f"{R:g}"] = {"rows": rows, "distortion_um": dist,
                         "mean": {str(rr): {k: float(np.mean([r[k] for r in rows if r["r_rot"] == rr])) for k in ("unmod_um", "oracle", "akf")}
                                  for rr in splits}}
    a, b = res[f"{R_old:g}"], res[f"{R_new:g}"]
    res["max_abs_change"] = {
        "oracle_ratio": max(abs(x["oracle"] - y["oracle"]) for x, y in zip(a["rows"], b["rows"])),
        "akf_ratio": max(abs(x["akf"] - y["akf"]) for x, y in zip(a["rows"], b["rows"])),
        "unmod_rel": max(abs(x["unmod_um"] / y["unmod_um"] - 1.0) for x, y in zip(a["rows"], b["rows"])),
        "distortion_um": max(abs(x - y) for x, y in zip(a["distortion_um"], b["distortion_um"]))}
    res["conditions"] = {"seeds": list(seeds), "f0_hz": list(f0s), "amp_mm": amp * 1e3, "r_rot": list(splits),
                         "tracker": "Rev H setting (results/opt/inertial_tracker_revh.json)",
                         "label": "SIMULATION (model H1, synthetic writing and tremor, test seeds 200-201; not used for any choice)"}
    return res


def figure(R, d: RevH, ru: FrontRules, path_png: str):
    """Side views in the tilt plane at 35, 50 and 75 deg: ring, sleeve front, nozzle, refill and ball, with the nose at rest
    and at the usable travel toward and away from the paper."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dm = dims(R, d, ru)

    def rot2(v, ang):                                     # counter-clockwise in this view moves the ball toward the paper
        c, s_ = math.cos(ang), math.sin(ang)
        return np.array([c * v[0] - s_ * v[1], s_ * v[0] + c * v[1]])

    fig, axs = plt.subplots(1, 3, figsize=(12.0, 4.4), constrained_layout=True)
    for ax, t in zip(axs, (ru.theta_min, ru.theta_nom, ru.theta_max)):
        th = math.radians(t)
        a2 = np.array([math.cos(th), math.sin(th)])       # pen axis in the view (along the paper, height), ball -> back
        n2 = np.array([math.sin(th), -math.cos(th)])      # perpendicular toward the paper
        C = np.array([0.0, R * math.cos(th)])             # ring-plane centre; C + R n2 is the contact point
        G = C + dm["s_g"] * a2
        ax.fill_between([-14, 20], -1.5, 0.0, color="0.9", zorder=0)
        ax.axhline(0.0, color="0.5", lw=0.8)

        def H(s_, r_):                                    # handle point: s behind the ring plane, r toward the paper
            return C + s_ * a2 + r_ * n2

        for sgn, alp in ((+1, 0.95), (-1, 0.35)):         # paper side solid, top side faint (the C opening)
            ring = [H(0, sgn * dm["ring_bore_r"]), H(0, sgn * R), H(ru.ring_len, sgn * R), H(ru.ring_len, sgn * dm["ring_bore_r"])]
            ax.add_patch(plt.Polygon(ring, closed=True, fc="#262d33", ec="none", alpha=alp))
            slv = [H(ru.ring_len, sgn * dm["sleeve_bore_r"]), H(ru.ring_len, sgn * dm["sleeve_front_r"]),
                   H(16.0, sgn * (dm["sleeve_front_r"] + 1.4)), H(16.0, sgn * dm["sleeve_bore_r"])]
            ax.add_patch(plt.Polygon(slv, closed=True, fc="#5d6a73", ec="none", alpha=0.3 * alp))
        for alpha, col, ls in ((0.0, "#2a78d6", "-"), (dm["alpha_u"], "#c8452a", "--"), (-dm["alpha_u"], "#0b7a3d", ":")):
            def N(s_, r_):                                # nose point, rotated about the gimbal
                return G + rot2((s_ - dm["s_g"]) * a2 + r_ * n2, alpha)
            nz = [N(0.0, ru.nozzle_r_front), N(ru.nozzle_len, ru.carrier_r), N(16.0, ru.carrier_r),
                  N(16.0, -ru.carrier_r), N(ru.nozzle_len, -ru.carrier_r), N(0.0, -ru.nozzle_r_front)]
            ax.add_patch(plt.Polygon(nz, closed=True, fc="none", ec=col, lw=1.3, ls=ls))
            an = rot2(a2, alpha)
            Lb = (G[1] - R_B) / an[1]                     # the refill slides until the ball is on the paper
            B = G - Lb * an
            E = N(0.0, 0.0)
            ax.plot([B[0], E[0]], [B[1], E[1]], color=col, lw=2.2, ls=ls, solid_capstyle="butt")
            ax.add_patch(plt.Circle(B, R_B, fc=col, ec="none"))
        ax.set_aspect("equal")
        ax.set_xlim(-16, 22)
        ax.set_ylim(-1.5, 17)
        ax.set_title(f"pen tilt {t:.0f}°", fontsize=10)
        ax.set_xlabel("mm along the paper")
        if t == ru.theta_nom:
            kw = dict(fontsize=7.5, color="0.2", arrowprops=dict(arrowstyle="-", color="0.4", lw=0.6))
            ax.annotate("skid ring on the paper\n(fixed sleeve)", xy=tuple(H(0.7, R)), xytext=(9.0, 2.2), **kw)
            ax.annotate("nozzle", xy=tuple(G + rot2((0.8 - dm["s_g"]) * a2 + ru.nozzle_r_front * n2, 0.0)), xytext=(-9.5, 9.0), **kw)
            ax.annotate("ball", xy=(float((C - protrusion(t, R) * a2)[0]), R_B), xytext=(-11.0, 3.0), **kw)
    axs[0].set_ylabel("mm above the paper")
    fig.suptitle(f"Rev H front end (CALC on a proposed design): skid ring contact radius {R:g} mm; dark = paper side of the C-shaped ring\n"
                 "blue: nose at rest; red dashed: usable travel toward the paper side; green dotted: away from it (the refill slides "
                 "so the ball stays on the paper)", fontsize=8.5)
    fig.savefig(path_png, dpi=150)
    plt.close(fig)


def main(argv=None):
    from stabpen import provenance
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sens", action="store_true", help="also run the H1 sensitivity check (about a minute)")
    a = ap.parse_args(argv)
    d = RevH()
    ru = FrontRules()
    sz = size_R(d, ru)
    R_design = d.skid_r * 1e3
    chk = check(R_design, d, ru, n_theta=17, n_phi=36)
    old = check(5.5, d, ru, n_theta=17, n_phi=36)
    os.makedirs(OUT, exist_ok=True)
    png = os.path.join(OUT, "fig_front_end.png")
    figure(R_design, d, ru, png)
    with open(os.path.join(OUT, "fig_front_end.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(chk["by_tilt"][0].keys()))
        w.writeheader()
        for r in chk["by_tilt"]:
            w.writerow({k: round(v, 4) for k, v in r.items()})
    out = {"meta": provenance.metadata("CALCULATION (front-end geometry closure of the Rev H nose; PROPOSED DESIGN; inputs ASSUMPTION)",
                                       extra={"script": "opt/inertial/front_end.py", "doc": "docs/opt_inertial.md section 8.6"}),
           "rules": ru.__dict__, "sizing": sz, "design": chk, "R5.5_with_this_front_end": {k: old[k] for k in (
               "ring_wall_mm", "nozzle_clear_usable_min_mm", "nozzle_clear_stop_min_mm", "refill_slide_range_mm")},
           "note": ("The skid contact radius is an input of the dynamics (H1 skid_geom).  The study's stage results were computed with "
                    "5.5 mm; see 'sensitivity' for the change at the closed design's radius.")}
    sens_path = os.path.join(OUT, "front_end_sensitivity.json")
    if a.sens:
        out["sensitivity"] = sensitivity(5.5, R_design)
        provenance.write_json(sens_path, out["sensitivity"])
    elif os.path.exists(sens_path):
        out["sensitivity"] = json.load(open(sens_path))
    provenance.write_json(os.path.join(OUT, "front_end.json"), out)
    print(f"sized R = {sz['R_mm']} mm (design value {R_design} mm); ring wall {chk['ring_wall_mm']:.2f} mm; nozzle clearance "
          f"{chk['nozzle_clear_usable_min_mm']:.2f} mm (usable), {chk['nozzle_clear_stop_min_mm']:.2f} mm (stop); refill slide "
          f"{chk['refill_slide_range_mm']:.1f} mm over 35-75 deg ({chk.get('refill_slide_range_40_70_mm', float('nan')):.1f} mm over 40-70); "
          f"ball travel >= {chk['ball_travel_usable_min_mm']:.2f} mm; passes {chk['passes']}")
    if "sensitivity" in out:
        print("sensitivity:", json.dumps(out["sensitivity"]["max_abs_change"]))
    return out


if __name__ == "__main__":
    main()
