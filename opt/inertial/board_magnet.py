r"""The guidance board's pen magnet on the Rev H pen (lead request after the board study): placement, fit against the sleeve,
the skid ring and the paper over the tilt range, and magnetic crosstalk at the nose's Hall sensor and the IMU.

Placement (board study, results/board/board_params.json 'pen_magnet'): K&J D42-N52 disc, 6.35 x 3.17 mm, 0.75 g (MFR AMF-91),
magnetised along the pen axis, in a keel under the FIXED front sleeve, 13.5 mm along the axis from the ball and 10.2 mm off the
axis toward the paper (Rev H frame: z along the axis from the ball; x transverse in the tilt plane, positive away from the
paper, so the paper side is -x).
Checks (CALC):
  * paper clearance of the keel (magnet + 0.5 mm wall, ASSUMPTION) against the plane through the skid-ring heel, 35-75 deg;
  * wall between the magnet and the sleeve bore that the swinging carrier needs;
  * fields by magpylib (SI units) of the pen magnet (static in the pen frame: a constant offset at the Hall sensor) and of
    the board head (K&J D88-N52 12.7 x 12.7 mm, axial, 3.7 mm below the writing surface; it moves under the pen: a varying
    field) at the nose Hall sensor and the IMU; the varying part is converted to an apparent nose position error with the
    field slope of the nose's own 1 x 1 mm position magnet.  No soft-iron shielding counted (the coil back ring around the
    Hall sensor would reduce it; FEM or a bench check needed).
Evidence: CALC on MFR magnet data and ASSUMPTION placement; nothing measured.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, Optional

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOARD = os.path.join(ROOT, "results", "board", "board_params.json")
MM = 1e-3


def placement() -> Dict:
    d = {"part": "K&J D42-N52 NdFeB disc", "d": 6.35, "h": 3.17, "mass_g": 0.75, "ledger": "AMF-91", "z_c": 13.5, "x_c": -10.2,
         "Br_T": 1.45, "source": "defaults (board study values)"}
    if os.path.exists(BOARD):
        b = json.load(open(BOARD))
        pm = b.get("pen_magnet", {})
        pf = pm.get("pen_frame_mm", {})
        d.update(part=pm.get("part", d["part"]), d=pm.get("d", d["d"]), h=pm.get("h", d["h"]), mass_g=pm.get("mass_g", d["mass_g"]),
                 ledger=pm.get("ledger", d["ledger"]), z_c=pf.get("along_axis_from_ball", d["z_c"]),
                 x_c=-abs(pf.get("off_axis_toward_paper", -d["x_c"])), source="results/board/board_params.json pen_magnet")
    return d


def keel_clearance(theta_deg, geo: Dict, pm: Optional[Dict] = None, wall=0.5) -> float:
    """Lowest height (mm) of the keel's outer surface above the paper plane through the skid-ring heel at the tilt."""
    pm = pm or placement()
    th = math.radians(theta_deg)
    z_ring, r_ring = geo["ball_protrusion_mm"], geo["skid_contact_radius"]
    z_front = pm["z_c"] - pm["h"] / 2 - wall
    x_low = pm["x_c"] - pm["d"] / 2 - wall
    h = []
    for z in (z_front, pm["z_c"] + pm["h"] / 2 + wall):
        h.append((z - z_ring) * math.sin(th) + (x_low + r_ring) * math.cos(th))
    return float(min(h))


def min_tilt(geo, pm=None, wall=0.5, margin=0.3):
    for t in np.arange(30.0, 80.01, 0.5):
        if keel_clearance(t, geo, pm, wall) >= margin:
            return float(t)
    return float("nan")


def _world(zp, xp, yp, theta_deg):
    th = math.radians(theta_deg)
    a = np.array([-math.cos(th), 0.0, math.sin(th)])
    t = np.array([math.sin(th), 0.0, math.cos(th)])
    return zp * a + xp * t + np.array([0.0, yp, 0.0])


def crosstalk(geo: Dict, theta_deg=50.0, pm: Optional[Dict] = None, head_offsets_mm=(-24.0, -12.0, 0.0, 12.0, 24.0),
              gap_mm=3.7, retract_mm=12.0) -> Dict:
    import magpylib as magpy
    pm = pm or placement()
    th = math.radians(theta_deg)
    a = np.array([-math.cos(th), 0.0, math.sin(th)])
    comp = {c["id"]: c for c in geo["components"]}

    def centre(cid):
        c = comp[cid]
        ox, oy = c.get("offset", [0.0, 0.0])
        return _world(0.5 * (c["z0"] + c["z1"]), ox, oy, theta_deg)

    obs = {"hall3d": centre("hall3d"), "imu": centre("imu")}
    # pen magnet: axis along the pen axis, north toward the rear (+a)
    pc = _world(pm["z_c"], pm["x_c"], 0.0, theta_deg)
    pen = magpy.magnet.Cylinder(dimension=(pm["d"] * MM, pm["h"] * MM), polarization=(0.0, 0.0, pm["Br_T"]))
    # rotate the default z axis onto a
    from scipy.spatial.transform import Rotation as R
    rot, _ = R.align_vectors([a], [[0.0, 0.0, 1.0]])
    pen.rotate(rot)
    pen.move(pc * MM)
    out = {"pen_magnet_centre_world_mm": pc.round(2).tolist(), "observers_world_mm": {k: v.round(2).tolist() for k, v in obs.items()}}
    out["pen_magnet_field_uT"] = {k: float(np.linalg.norm(pen.getB(v * MM)) * 1e6) for k, v in obs.items()}
    # board head sweep (head centred under the pen magnet in plan view, then offsets along x and y); retracted case
    head_B = {k: [] for k in obs}
    cases = []
    for dx in head_offsets_mm:
        for dy in head_offsets_mm:
            for ret in (0.0, retract_mm):
                hz = -(gap_mm + ret + 12.7 / 2)
                head = magpy.magnet.Cylinder(dimension=(12.7 * MM, 12.7 * MM), polarization=(0.0, 0.0, 1.45),
                                             position=((pc[0] + dx) * MM, dy * MM, hz * MM))
                row = {"dx": dx, "dy": dy, "retracted": ret > 0}
                for k, v in obs.items():
                    B = head.getB(v * MM)
                    head_B[k].append(B)
                    row[k + "_uT"] = float(np.linalg.norm(B) * 1e6)
                cases.append(row)
    out["head_field_uT"] = {k: {"min": float(min(np.linalg.norm(b) for b in v) * 1e6), "max": float(max(np.linalg.norm(b) for b in v) * 1e6),
                                "max_change_any_component": float((np.max(np.array(v), axis=0) - np.min(np.array(v), axis=0)).max() * 1e6)}
                            for k, v in head_B.items()}
    # nose Hall signal slope: 1 x 1 mm N45 position magnet 2.0 mm from the sensor along the axis, moved sideways
    hm, hs = comp["hall_magnet"], comp["hall3d"]
    dz = 0.5 * (hs["z0"] + hs["z1"]) - 0.5 * (hm["z0"] + hm["z1"])
    Bx = []
    for dlt in (-0.05, 0.05):
        m = magpy.magnet.Cylinder(dimension=(1.0 * MM, 1.0 * MM), polarization=(0.0, 0.0, 1.33), position=(dlt * MM, 0.0, 0.0))
        Bx.append(m.getB((0.0, 0.0, dz * MM))[0])
    slope = abs(Bx[1] - Bx[0]) / (0.1 * MM)                     # T per m at the magnet
    lever_hall = (0.5 * (hm["z0"] + hm["z1"]) - geo["pivot_z"]) / geo["pivot_z"]   # magnet motion per tip motion
    dB = out["head_field_uT"]["hall3d"]["max_change_any_component"] * 1e-6
    # slope in T/m equals mT/mm numerically; apparent tip error = field change / slope / (magnet motion per tip motion)
    out["hall_signal"] = {"distance_mm": float(dz), "slope_mT_per_mm_at_magnet": float(slope),
                          "magnet_motion_per_tip_motion": float(lever_hall),
                          "apparent_tip_error_um_unshielded": float(dB / slope / lever_hall * 1e6)}
    out["label"] = ("CALC (magpylib 5 dipole-exact cylinder fields; MFR Br 1.45 T N52 / 1.33 T N45; placement ASSUMPTION; "
                    "no shielding counted)")
    return out


def summary(geo: Dict) -> Dict:
    pm = placement()
    cl = {f"{t:g}": round(keel_clearance(t, geo, pm), 2) for t in (35.0, 40.0, 45.0, 50.0, 60.0, 75.0)}
    # wall between the magnet and the sleeve bore at the magnet: the carrier (d 7) swings X (z_p - z)/z_p there
    sw = geo["tip_travel_mm"] * (geo["pivot_z"] - pm["z_c"]) / geo["pivot_z"]
    bore_r = 3.5 + sw + 0.3
    inner = abs(pm["x_c"]) - pm["d"] / 2
    out = {"placement": pm, "keel_wall_mm_ASSUMPTION": 0.5,
           "paper_clearance_mm_by_tilt": cl, "min_tilt_deg_for_0.3mm_clearance": min_tilt(geo, pm),
           "wall_to_carrier_swing_mm": round(inner - bore_r, 2), "added_mass_g": round((pm["mass_g"] + 0.3) * 1.1, 2),
           "added_mass_note": "magnet 0.75 g + keel 0.3 g (ASSUMPTION) + 10 % (the P0 wiring convention)"}
    try:
        out["crosstalk"] = crosstalk(geo, pm=pm)
    except Exception as e:                  # magpylib missing: keep the geometry checks
        out["crosstalk"] = {"error": str(e)}
    return out
