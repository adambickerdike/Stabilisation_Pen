r"""Component layout of the recommended Rev J nose (PROPOSED DESIGN; dimensions ASSUMPTION or CALC from the optimised
design; masses CALC).  The output follows the schema of results/revH/layout.json (opt/inertial/geometry.py) so the 3-D
explainer can draw it: top-level geometry keys, "components" (id, label, group, shape, z0, z1, moves_with, optional,
function, part, ledger, d0/d1/d_in or size/offset, mass_g) and "fit_checks".

Units mm; z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane (+x away from the paper),
y lateral.  Groups as Rev H (structure | grip | moving_nose | refill | actuator | mechanism | sensor | electronics |
power | haptic).  moves_with: nose | handle | refill_lift (the refill's own axial motion).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from . import designs as DS
from . import ensure_paths
from . import frontend as FEN

ensure_paths()
from opt.inertial.front_end import FrontRules, protrusion  # noqa: E402
from opt.inertial.geometry import comp  # noqa: E402  (read-only reuse of the Rev H component record)

RHO = {"Ti": 4.42, "Al": 2.70, "PEEK": 1.30, "TPE": 1.10, "POM": 1.41, "Fe": 7.87, "NdFeB": 7.6, "Cu": 8.89}   # g/cm3
# sources: Ti AMF-21, PEEK AMF-24, NdFeB AMF-139, Cu AMF-29; Al, TPE, POM, Fe handbook values (ASSUMPTION)


def _tube_mass(do, di, L, rho):
    return rho * math.pi / 4 * (do * do - di * di) * L * 1e-3        # mm -> g


def layout(des: Dict, handle_od: float = 24.0, length: float = 175.0, axial: bool = True, theta_deg: float = 50.0) -> Dict:
    """Layout of a gimbal_radial or gimbal_sphere design summary from optimise.summary (lengths in m inside)."""
    kind = des["kind"]
    v = des["vars"]
    zp = v["z_p"] * 1e3
    Lb = v["L_b"] * 1e3
    za = zp + Lb
    X = des["X_nom_mm"]
    Xmin = des["X_min_mm"]
    w, t_m, t_c = v["w"] * 1e3, v["t_m"] * 1e3, v["t_c"] * 1e3
    l = v.get("l", 0.0) * 1e3
    gap = des["gap_mm"]
    ru = FrontRules()
    fe = FEN.size(FEN.Nose(z_p=zp, travel=X))
    R = fe["R_mm"]
    dm = fe["dims"]
    prot = protrusion(theta_deg, R)
    z_skid = prot
    z_cf = z_skid + ru.nozzle_len
    bore_r = handle_od / 2 - 1.0
    z_end = float(DS.front_end(X * 1e-3, zp * 1e-3)["z_end"]) * 1e3       # rearmost end of the refill holder (CALC)
    a_s = (X + 0.5) / zp                                                   # tilt at the stop (rad)
    s_act = des["stroke_act_mm"]
    comps: List[Dict] = []
    A = comps.append
    # ---------------- refill, nose
    A(comp("ball", "Ball tip", "refill", "cone", 0.0, 3.0, "nose", 0.7, 2.35, function="The point that touches the paper and writes.",
           part="ISO 12757-2 D1 mini refill", ledger="DEC-004"))
    A(comp("refill", "Ink refill (D1 mini)", "refill", "cylinder", 3.0, 67.0, "nose", 2.35, 2.35,
           function=f"Standard replaceable refill.  It slides along the nose so the ball stays on the paper: about "
                    f"{fe['refill_slide_range_mm']:.0f} mm over 35-75 deg tilt and the tip's travel (CALC, front-end closure).",
           part="ISO 12757-2 D1 mini refill", ledger="DEC-004", mass_g=0.84))
    A(comp("refill_spring", "Refill holder and ink-force spring", "mechanism", "cylinder", 67.0, 67.0 + DS.HOLDER_L * 1e3, "nose",
           3.2, 3.2, function=f"Holds the refill's end and presses the ball onto the paper (about 0.15 N) while the refill slides; its "
                              f"rearmost position is {z_end:.0f} mm from the tip.  Needs a fatigue-rated spring (not a stock "
                              f"constant-force strip: MFR AMF-144 rates 2 500-25 000 cycles).",
           part="custom (holder + long soft spring or magnetic spring, to design; ASSUMPTION 0.5 g)", ledger="AMF-144",
           mass_g=DS.M_REAR * 1e3))
    if axial:
        A(comp("refill_lift", "Pen lift: brake and latch", "mechanism", "cylinder", zp - 8.5, zp - 1.5, "nose", 5.6, 5.6,
               function="The pen's own pen-up/down, inside the carrier just in front of the gimbal: an electro-permanent brake clamps "
                        "the refill and a bistable latch moves the clamp back 0.5 mm, lifting the ball; neither needs power to hold.",
               part="custom (electro-permanent brake + bistable reluctance latch, about 2 g; ASSUMPTION)", ledger="PAT-41",
               mass_g=DS.M_LIFT * 1e3))
    A(comp("carrier", "Moving nose (refill carrier)", "moving_nose", "tube", z_cf, zp - 1.5, "nose", 7.0, 7.0, 6.0,
           function=f"Thin titanium tube holding the refill; it tilts on the gimbal so the ball moves at least {Xmin:.1f} mm in every "
                    f"direction over 35-75 deg of pen tilt.", part="custom (Ti-6Al-4V tube 7/6 mm)", ledger="AMF-21",
           mass_g=_tube_mass(7.0, 6.0, zp - 1.5 - z_cf, RHO["Ti"])))
    A(comp("carrier_nozzle", "Nose nozzle", "moving_nose", "cone", z_skid, z_cf, "nose", 2 * ru.nozzle_r_front, 2 * ru.carrier_r,
           function="Front of the moving nose; guides the refill tip.", part="custom (PEEK)", ledger="AMF-24", mass_g=0.4))
    hub = max(2 * w, 2 * DS.R_CH * 1e3 + 1.5) if kind == "gimbal_radial" else 5.0
    arm_z1 = za - (l / 2 if kind == "gimbal_radial" else 1.0)
    A(comp("arm", "Short rear arm", "moving_nose", "tube", zp + 1.5, max(arm_z1, zp + 2.0), "nose", 5.0, 5.0, 3.0,
           function="Carries the magnets just behind the gimbal: a short arm keeps the magnets' stroke (and the magnet-coil gap) "
                    "small; the tip moves the opposite way, about " f"{zp / Lb:.1f} x the magnets' motion.",
           part="custom (aluminium 6061 tube 5/3 mm; the refill passes through)", ledger="",
           mass_g=_tube_mass(5.0, 3.0, max(arm_z1, zp + 2.0) - zp - 1.5, RHO["Al"])))
    act_checks = {}
    if kind == "gimbal_radial":
        z0m, z1m = za - l / 2, za + l / 2
        A(comp("magnet_hub", "Magnet hub (soft iron)", "moving_nose", "box", z0m, z1m, "nose", size=[hub, hub, l],
               function="Square soft-iron hub: one magnet pair on each face; it returns the magnets' flux.", part="custom (soft iron, 60 % solid)",
               ledger="", mass_g=0.6 * RHO["Fe"] * hub * hub * l * 1e-3))
        rm = hub / 2 + t_m / 2
        for face, (ox, oy, nx, ny) in {"x+": (rm, 0, 1, 0), "x-": (-rm, 0, -1, 0), "y+": (0, rm, 0, 1), "y-": (0, -rm, 0, -1)}.items():
            for k, sgn in ((1, 1.0), (2, -1.0)):
                # two poles side by side across the force direction (tangential), N | S
                tx, ty = (0, sgn * w / 2) if nx != 0 else (sgn * w / 2, 0)
                sx, sy = (t_m, w) if nx != 0 else (w, t_m)
                A(comp(f"magnet_{face}{k}", f"Actuator magnet, {'N' if k == 1 else 'S'} pole ({'y' if face[0] == 'x' else 'x'}-force)",
                       "actuator", "box", z0m, z1m, "nose", size=[sx, sy, l], offset=[ox + tx, oy + ty],
                       function="NdFeB block on the moving hub; the flat coil facing the pole pair pushes it sideways (shear).",
                       part=f"NdFeB {des['parts']['grade']} block {w:.1f} x {l:.1f} x {t_m:.1f} mm", ledger="AMF-139/AMF-28",
                       mass_g=RHO["NdFeB"] * w * l * t_m * 1e-3))
        r_coil = hub / 2 + t_m + gap + t_c / 2
        for face, (ox, oy, nx) in {"x+": (r_coil, 0, 1), "x-": (-r_coil, 0, 1), "y+": (0, r_coil, 0), "y-": (0, -r_coil, 0)}.items():
            sx, sy = (t_c, 2 * w + 0.6) if nx else (2 * w + 0.6, t_c)
            A(comp(f"coil_{face}", f"Flat racetrack coil ({'y' if face[0] == 'x' else 'x'}-force)", "actuator", "box", z0m - w / 2, z1m + w / 2,
                   "handle", size=[sx, sy, l + w], offset=[ox, oy],
                   function="Fixed coil, one leg over each pole of the pair; current pushes the magnets sideways.",
                   part=f"custom (self-bonding {des['parts']['wire'] * 1e3:.3f} mm magnet wire, IEC class 155)", ledger="AMF-29/AMF-30"))
        r_out = hub / 2 + t_m + gap + t_c
        A(comp("back_ring", "Soft-iron ring (flux return)", "actuator", "tube", z0m - w / 2 - 0.5, z1m + w / 2 + 0.5, "handle", handle_od, handle_od,
               2 * (r_out + 0.05), function="Shell section over the coils in soft iron: closes the magnets' flux through the coils.",
               part=f"custom ({des['parts']['iron']}, nickel plated)", ledger="AMF-140" if des["parts"]["iron"] == "Hiperco50A" else ""))
        act_checks["coil_radius_margin_mm"] = round(bore_r - r_out - 0.5, 3)
        act_checks["magnet_clears_gimbal_mm"] = round(z0m - (zp + 1.5), 3)
        z_act_end = z1m + w / 2 + 0.5
    else:
        # checkerboard cap on the arm's end (spherical faces for C1S), two coil layers on a concentric plate; when the refill
        # reaches behind the cap, its channel passes through a central hole and the four pole units sit outside it
        through = z_end > za
        r_hole = (DS.R_CH * 1e3 + s_act + 0.3) if through else 0.0
        r_disc = w * math.sqrt(2) + 0.5 + r_hole
        z0m = za - t_m / 2
        faces = "spherical" if kind in ("gimbal_sphere", "coarse_fine") else "flat"
        A(comp("magnet_cap", "Magnet cap (2 x 2 checkerboard on soft iron)", "actuator", "tube" if through else "cylinder", za - t_m - 0.6, za,
               "nose", 2 * r_disc, 2 * r_disc, 2 * (DS.R_CH * 1e3 + 0.3) if through else None,
               function=f"Four magnet poles (N S / S N) on a soft-iron cap with a {faces} face centred on the gimbal: tilting slides the "
                        f"poles along the coils" + (" at a constant gap" if faces == "spherical" else "") +
                        (". The refill channel passes through its centre." if through else "."),
               part=f"NdFeB {des['parts']['grade']} segments {w:.1f} x {w:.1f} x {t_m:.1f} mm on a {faces} soft-iron cap (custom)",
               ledger="AMF-139", mass_g=des["m_act_move_g"] if "m_act_move_g" in des else None))
        A(comp("coil_plate", f"Two-layer {faces} coil plate", "actuator", "tube" if through else "cylinder", za + gap, za + gap + 2 * t_c + 0.8,
               "handle", 2 * (r_disc + s_act + 0.5), 2 * (r_disc + s_act + 0.5), 2 * r_hole if through else None,
               function="x and y coil layers on a soft-iron plate concentric with the cap" +
                        ("; its central hole lets the refill channel swing." if through else "."),
               part="custom (bonded coils on a formed plate)", ledger="AMF-29/AMF-30"))
        act_checks["coil_radius_margin_mm"] = round(bore_r - (r_disc + s_act + 0.5), 3)
        act_checks["magnet_clears_gimbal_mm"] = round(za - t_m - 0.6 - (zp + 1.5), 3)
        z_act_end = za + gap + 2 * t_c + 0.8
    if z_end > za:
        A(comp("refill_channel", "Refill channel (behind the actuator)", "moving_nose", "tube", za, z_end, "nose", 2 * DS.R_CH * 1e3,
               2 * DS.R_CH * 1e3, 3.4, function="Thin tube that carries the refill's rear end and its holder behind the actuator; it swings "
                                              "with the nose.", part="custom (Ti-6Al-4V tube 4.0/3.4 mm)", ledger="AMF-21",
               mass_g=DS.LIN_CH * (z_end - za)))
    act_checks["refill_channel_swing_margin_mm"] = round(bore_r - (a_s * max(z_end - zp, 0.0) + DS.R_CH * 1e3 + 0.3), 3)
    z_act_end = max(z_act_end, z_end + 1.0)
    A(comp("hall_magnet", "Position magnet", "sensor", "cylinder", z_act_end + 0.5, z_act_end + 1.5, "nose", 1.0, 1.0,
           function="Tiny magnet on the moving arm read by the 3-D Hall sensor.", part="supermagnete S-01-01-N", ledger="AMF-72"))
    A(comp("hall3d", "3-D Hall position sensor", "sensor", "box", z_act_end + 2.5, z_act_end + 3.5, "handle", size=[3.0, 3.0, 1.0],
           function="Reads the nose position in x and y (20 kSPS single axis) for the position servo; the larger travel needs the "
                    "+-50 mT range.", part="TI TMAG5170 (3-D Hall, SPI) or TMAG5273", ledger="OPT-53/OPT-45"))
    # ---------------- handle
    ring = comp("skid_ring", "Skid ring (C-shaped heel)", "structure", "tube", z_skid, z_skid + ru.ring_len, "handle", 2 * R, 2 * R,
                2 * dm["ring_bore_r"], function="Rests on the paper and carries the writing force; the nose swings inside its lip. Open on "
                "the top so the ink stays visible.", part=f"custom (PTFE-coated POM, contact radius {R:.2f} mm)", ledger="DEC-034",
                mass_g=RHO["POM"] * (2 / 3) * math.pi * (R * R - dm["ring_bore_r"] ** 2) * ru.ring_len * 1e-3)
    ring["open_deg"] = 120.0
    A(ring)
    z_sl1 = 50.0
    sl_do0 = 2 * dm["sleeve_front_r"]
    A(comp("front_sleeve", "Front sleeve (fixed grip)", "grip", "tube", z_skid + ru.ring_len, z_sl1, "handle", sl_do0, handle_od,
           2 * dm["sleeve_bore_r"], function="Where the fingers rest. It does not move; the nose swings inside it.",
           part="PEEK core + TPE overmould", ledger="AMF-24",
           mass_g=_tube_mass(0.5 * (sl_do0 + handle_od), 2 * dm["sleeve_bore_r"], z_sl1 - z_skid - ru.ring_len, 0.5 * (RHO["TPE"] + RHO["PEEK"]))))
    A(comp("optical", "Paper sensor (required for autowrite)", "sensor", "box", 14.0, 20.0, "handle", size=[5.0, 5.0, 6.0],
           offset=[-(dm["sleeve_bore_r"] + 3.0), 0.0], optional=False,
           function="Sees the paper beside the nose: where the pen is on the page (autowrite needs it; 1 kHz, 2 ms assumed).",
           part="optical-flow sensor, to select (PMW3360 class needs a flat window 2.4 mm from the paper; ASSUMPTION)", ledger="OPT-54",
           mass_g=1.0))
    A(comp("gimbal", "Flexure gimbal (2-axis)", "mechanism", "tube", zp - 1.5, zp + 1.5, "handle", 2 * (bore_r - 0.5), 2 * (bore_r - 0.5), 5.5,
           function=f"Laser-cut cross-strip flexures: the nose tilts +-{math.degrees(X / zp):.1f} deg in two directions with no friction; stiff "
                    f"along the pen.", part=f"custom ({des['parts']['flexure']} {des['parts']['t_flex'] * 1e3:.3f} mm, laser-cut)",
           ledger="AMF-20" if "NiTi" not in des["parts"]["flexure"] else "AMF-141/AMF-142", mass_g=2.0))
    A(comp("shell", "Handle shell", "structure", "tube", 50.0, length, "handle", handle_od, handle_od, handle_od - 2.0,
           function=f"The body you hold: {handle_od:.0f} mm across.", part="PEEK or glass-filled nylon, 1 mm wall", ledger="AMF-24",
           mass_g=_tube_mass(handle_od, handle_od - 2.0, length - 50.0, RHO["PEEK"])))
    z_pcb0 = z_act_end + 5.0
    z_cell0 = z_pcb0 + 17.0
    A(comp("pcb", "Control board", "electronics", "box", z_pcb0, z_cell0 - 1.0, "handle", size=[1.0, 15.0, z_cell0 - 1.0 - z_pcb0],
           function="MCU with Bluetooth, two coil drivers with current sensing, the lift driver, charger and the IMU.",
           part="nRF54L15 + 2 x DRV8214 + lift driver + charger", ledger="AMF-44/AMF-37", mass_g=5.0))
    A(comp("imu", "Motion sensor (IMU)", "sensor", "box", z_pcb0 + 4.0, z_pcb0 + 6.5, "handle", size=[2.5, 3.0, 0.83], offset=[1.0, 0.0],
           function="Accelerometer and gyroscope: with the paper sensor it tells where the handle is, 2000 times a second.",
           part="ST LSM6DSV16X", ledger="OPT-37"))
    A(comp("battery", "Rechargeable cell", "power", "cylinder", z_cell0, z_cell0 + 48.5, "handle", 14.1, 14.1,
           function="EEMB LIR14500, 750 mAh.", part="EEMB LIR14500", ledger="AMF-80", mass_g=20.0))
    z_after = z_cell0 + 48.5 + 1.0
    A(comp("lra", "Vibration cue motor", "haptic", "cylinder", z_after, z_after + 3.0, "handle", 8.0, 8.0, optional=True,
           function="Gentle buzz cues.", part="coin LRA 8 mm", ledger="AMF-45", mass_g=1.0))
    A(comp("usb", "USB-C port and button", "electronics", "box", z_after + 4.0, z_after + 7.5, "handle", size=[8.4, 2.6, 3.5],
           offset=[0.0, handle_od / 2 - 2.0], function="Charging and mode button.", part="USB-C receptacle (mid-mount)", ledger=""))
    A(comp("rear_cap", "Rear cap", "structure", "cylinder", length - 3.0, length, "handle", handle_od, handle_od - 2.0,
           function="Closes the handle.", part="custom (PEEK)", ledger="AMF-24", mass_g=3.0))
    # ---------------- masses (CALC; Rev H convention: + 10 % wiring and adhesive)
    stat_extra = des["m_act_stat_g"] if "m_act_stat_g" in des else des["mass_added_g"] - des.get("m_act_move_g", 0.0)
    nose_g = sum(c.get("mass_g", 0.0) or 0.0 for c in comps if c["moves_with"] == "nose") + \
        (des.get("m_act_move_g", 0.0) if kind == "gimbal_radial" else 0.0)
    if kind == "gimbal_radial":
        nose_g -= sum(c.get("mass_g", 0.0) or 0.0 for c in comps if c["id"].startswith("magnet_") and c["id"] != "magnet_hub")
        nose_g -= next((c.get("mass_g", 0.0) for c in comps if c["id"] == "magnet_hub"), 0.0)
    handle_g = sum(c.get("mass_g", 0.0) or 0.0 for c in comps if c["moves_with"] == "handle") + stat_extra + 0.5    # + flex and Hall (ASSUMPTION)
    ms = {"nose_g": nose_g * 1.1, "handle_g": handle_g * 1.1}
    ms["total_g"] = ms["nose_g"] + ms["handle_g"]
    zc = sum(((c["z0"] + c["z1"]) / 2) * (c.get("mass_g") or 0.0) for c in comps) / max(sum((c.get("mass_g") or 0.0) for c in comps), 1e-9)
    ms["com_mm"] = zc
    ms["moving_mass_at_tip_g"] = des["m_eff_tip_g"]                    # includes the pen lift, holder and channel (designs.nose_inertia)
    geo = {"units": "mm", "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x, y transverse",
           "pivot_z": round(zp, 2), "actuator_z": round(za, 2), "tip_travel_mm": round(X, 2), "tip_travel_min_35_75_mm": round(Xmin, 2),
           "magnet_stroke_mm": round(des["stroke_act_mm"], 2), "lever_tip_per_magnet": round(zp / Lb, 3), "tilt_deg": theta_deg,
           "front_opening_d": round(2 * dm["sleeve_bore_r"], 2), "skid_contact_radius": R, "ball_protrusion_mm": round(prot, 2),
           "handle_od": handle_od, "length": length, "grip_zone": {"z0": 20.0, "z1": 45.0},
           "hand": {"finger_pads_z": [26.0, 32.0, 38.0], "web_z": 92.0},
           "refill_slide_mm": round(fe["refill_slide_range_mm"], 1), "mass_g": {k: round(v, 2) for k, v in ms.items()},
           "components": comps}
    geo["refill_end_max_mm"] = round(z_end, 1)
    fc = {"carrier_clears_front_opening_mm": round(dm["sleeve_bore_r"] - (3.5 + X * (zp - z_cf) / zp), 3),
          "skid_ring_wall_mm": round(fe["ring_wall_mm"] - ru.ring_wall_min, 3),
          "nozzle_above_paper_mm": round(fe["nozzle_clear_usable_min_mm"] - ru.c_paper, 3),
          "sleeve_front_above_paper_mm": round(fe["sleeve_front_clear_min_mm"], 3),
          "carrier_at_stop_mm": round(fe["carrier_stop_clearance_mm"], 3),
          "cell_radius_margin_mm": round(bore_r - 14.1 / 2, 3),
          "length_margin_mm": round(length - 3.0 - (z_after + 7.5), 3)}
    fc.update(act_checks)
    fc["all_pass"] = all(val >= 0 for val in fc.values())
    geo["fit_checks"] = fc
    return geo
