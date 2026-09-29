r"""The integrated Rev J layout (PROPOSED DESIGN): every component in the schema of results/revH/layout.json, and the
fit checks that make it one consistent pen.  Dimensions CALC from the closure (revj.frontend), the refill geometry
(revj.refill) and study N's actuator, or ASSUMPTION; masses CALC from volumes and catalogue values (MFR ids).

Schema (as results/revH/layout.json "components"): id, label, group, shape (cylinder | cone | tube | box), z0, z1
(mm along the axis from the ball tip), d0, d1, d_in, size ([x, y, z] mm), offset ([x, y] mm; x in the tilt plane,
positive AWAY from the paper), moves_with (nose | handle | drive | inertial_mass), optional, function, part, ledger,
mass_g.  Extra keys used here: open_deg (C-shaped parts, opening on top), replaced_by_endcap (the base pen's rear cap),
notch (a local flat or groove the schema cannot draw), cad (hints for mechanics/cad/revJ_pen.py).

Packaging, front to back (the answer to conflict 2):
  front      skid ring (C, 120 deg open on top) with the heel wheel in a slot at the bottom; heel pod behind it; the page
             sensor's window beside the pod (folded optics, die in the sleeve wall)
  grip       front sleeve 23.3 -> 24 mm; the two drive shafts run in grooves in its bottom wall (no external keel)
  mid        the MAIN BOARD lies along the top of the handle (z 50-72), above the swinging carrier; the IMU and the
             nose's two linear Hall sensors (reading a small magnet on the carrier) sit on it
  actuator   pen-lift drum in front of the gimbal (moves with the nose); gimbal; short arm; magnet cap; coil plate.  The
             cap is flattened at the bottom and the coil plate and gimbal frame are notched there so the shafts pass
  rear       the CELL right behind the coil plate, lifted 3 mm toward the top; the two MOTORS under its front half, with
             the transfer gears in front of them; the cue LRA under the cell behind the motors; USB beside the cell's end
  back       a 3 mm rear cap (base pen, 145 mm) or the detachable reaction-mass end-cap (166 mm)
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ensure_paths
from . import frontend as FR
from . import params as PA
from . import refill as RF

ensure_paths()
from opt.inertial.front_end import FrontRules, protrusion  # noqa: E402
from opt.inertial.geometry import comp  # noqa: E402  (read-only reuse of the Rev H component record)

RU = FrontRules()
D_HANDLE = 24.0
BORE_R = 11.0                        # 1 mm PEEK wall (Rev H / study N)
CELL_OFFSET_X = 3.0                  # mm: the cell's axis lifted toward the top (+x) to free the bottom for the motors
MOTOR_XY = (-7.2, 3.2)               # mm: motor axes (x, +-y), under the lifted cell
SHAFT_R = 10.8                       # mm: drive-shaft axes from the pen axis (the sleeve's front skin sets it)
SHAFT_XY = (-math.sqrt(SHAFT_R ** 2 - 1.6 ** 2), 1.6)   # mm: +-8.5 deg either side of the bottom
CAP_FLAT_R = 8.8                     # mm: the magnet cap's flat at the bottom (the poles end at 6.3 mm)
NOTCH_R = 9.9                        # mm: coil-plate and gimbal-frame notches at the bottom (+-10 deg)
LINER_D = 1.0                        # mm, PTFE liner around each 0.8 mm shaft (ASSUMPTION; study D used 1.2)
BOARD_Z = (50.0, 72.0)               # mm, main board along the top of the mid-section
BOARD_X = (7.0, 8.0)                 # mm, its FR4 (x away from the paper); components to x 6.4 below and 9.2 above
MAG_Z = (62.0, 64.0)                 # mm, nose position magnet on the carrier's top
GROUPS = ("moving_nose", "refill", "skid", "grip", "mechanism", "actuator", "sensor", "electronics", "power", "haptic",
          "drive", "inertial", "structure")
MOVES = ("nose", "handle", "drive", "inertial_mass")


def _rho(name: str) -> float:
    return PA.RHO[name].value * 1e-3        # g/mm^3


def _tube(do, di, L, rho):
    return math.pi / 4 * (do * do - di * di) * L * rho


def build(fe: Optional[Dict] = None, quick: bool = False) -> Dict:
    """Closure + layout + fit checks.  fe: revj.frontend.close(...) (computed if not given)."""
    nt, npf = (9, 24) if quick else (17, 72)
    h = FR.Heel()
    if fe is None:
        fe = FR.close(h, n_theta=nt, n_phi=npf)
    nd = PA.nose_design()
    nz = replace(FR.c1s_nose(), X=fe["X_nom_mm"])
    R_s, R_d = fe["R_mm"], fe["R_d_mm"]
    dm = fe["dims"]
    z_ring = protrusion(50.0, R_s)
    z_cf = z_ring + RU.nozzle_len
    zp, za = nd["z_p"], nd["z_a"]
    cap_front = nd["cap_front"]
    t_c, t_bi = nd["t_c"], nd["t_bi"]
    z_plate0 = za + nd["gap"]
    z_plate1 = z_plate0 + 2 * t_c + t_bi                     # two coil layers + the stator back iron (study N's model)
    rf = RF.summary(fe, nd)
    sl = rf["slide"]
    ps = FR.page_sensor_window(R_s, R_d, nz, h)
    win = ps["window"]
    th50 = math.radians(50.0)
    nrm = np.array([math.cos(th50), 0.0, math.sin(th50)])  # paper normal in (x, y, z)
    contact = np.array([-R_d, 0.0, z_ring])
    wheel_c = contact + h.r_e * nrm
    crown_c = contact + (2.0 * h.r_e + 0.5 * h.cap_h) * nrm
    cell_d, cell_l = PA.POWER["cell_d_mm"].value, PA.POWER["cell_l_mm"].value
    z_cell0 = z_plate1 + 0.5
    z_cell1 = z_cell0 + cell_l
    z_gear = (z_cell0, z_cell0 + 2.0)
    z_mot = (z_gear[1] + 0.2, z_gear[1] + 0.2 + PA.MOTOR["l_mm"].value)
    z_shell1 = z_cell1 + 0.5
    L_base = z_shell1 + 3.0
    ec = PA.endcap_parts()
    ec_shift = z_shell1 - 151.0                             # study K's end-cap started at z 151 behind the Rev H cell
    comps: List[Dict] = []
    A = comps.append

    # ------------------------------------------------------------------ refill (moves with the nose)
    A(comp("ball", "Ball tip", "refill", "cone", 0.0, 3.0, "nose", 0.7, 2.35, function="The point that touches the paper and writes.",
           part="ISO 12757-2 D1 mini refill (metal body preferred: it sticks out up to 16 mm beyond the nozzle at 35 deg)",
           ledger="DEC-004"))
    A(comp("refill", "Ink refill (D1 mini)", "refill", "cylinder", 3.0, 67.0, "nose", 2.35, 2.35,
           function=f"Standard replaceable refill.  It slides {sl['slide_range_mm']:.1f} mm along the nose over 35-75 deg of tilt "
                    f"and the tip's travel so the ball stays on the paper (CALC).",
           part="ISO 12757-2 D1 mini refill", ledger="DEC-004", mass_g=0.84))
    A(comp("refill_holder", "Refill holder (tendon end)", "refill", "cylinder", 67.0, 67.0 + RF.HOLDER_L, "nose", 3.2, 3.2,
           function="The refill push-fits into it; a closed tendon loop joins it to the ink-force drum.  Its rearmost position "
                    f"is z {sl['holder_rear_max_z_mm']:.1f} mm (75 deg, nose deflected, pen lifted).",
           part="custom (PEEK holder, socket for the D1 refill, two tendon anchors; ASSUMPTION 0.5 g)", ledger="PAT-41",
           mass_g=0.5))
    # ------------------------------------------------------------------ moving nose
    A(comp("carrier_nozzle", "Nose nozzle (unscrews to change the refill)", "moving_nose", "cone", z_ring, z_cf, "nose",
           2 * RU.nozzle_r_front, 2 * RU.carrier_r, function="Front of the moving nose; guides the refill; its front face sits in "
           "the ring plane.  It unscrews for a refill change.", part="custom (PEEK)", ledger="AMF-24", mass_g=0.4))
    m_carrier = _tube(7.0, 6.0, (zp - 1.5) - z_cf, _rho("Ti"))
    A(comp("carrier", "Moving nose (refill carrier)", "moving_nose", "tube", z_cf, zp - 1.5, "nose", 7.0, 7.0, 6.0,
           function=f"Titanium tube holding the refill; it tilts on the gimbal so the ball moves at least 6.0 mm in every "
                    f"direction over 35-75 deg ({fe['X_nom_mm']:.2f} mm at 50 deg).", part="custom (Ti-6Al-4V tube 7/6 mm)",
           ledger="AMF-21", mass_g=m_carrier))
    A(comp("front_pulley", "Front tendon pulley", "mechanism", "cylinder", sl["front_pulley_z_mm"][0], sl["front_pulley_z_mm"][1],
           "nose", 1.5, 1.5, function="Turns the tendon loop in front of the holder's foremost position.",
           part="custom (PTFE pulley d 1.5 mm on a 0.3 mm pin; tendon UHMWPE 0.2 mm, ASSUMPTION)", ledger="", mass_g=0.02))
    A(comp("pen_lift", "Pen lift and ink-force drum", "mechanism", "tube", RF.DRUM_Z[0], RF.DRUM_Z[1], "nose", 5.6, 5.6, 3.6,
           function=("Annular module around the refill's path in front of the gimbal.  A pre-coiled spiral spring in the drum "
                     f"sets the ink force (0.12-0.18 N over the whole slide, fatigue-rated) through the tendon loop; an "
                     "electro-permanent brake locks the drum (pen lift, and the front stop that follows the nose); a bistable "
                     "latch lifts the refill 0.5 mm.  No holding power."),
           part="custom (drum, 301 FH spiral spring 38 um x 2.6 mm x 139 mm, EP brake, bistable latch; about 2 g, ASSUMPTION)",
           ledger="PAT-41; AMF-20", mass_g=2.0))
    A(comp("slide_sensor", "Refill-slide sensor (drum angle)", "sensor", "box", RF.DRUM_Z[1] - 1.0, RF.DRUM_Z[1], "nose",
           size=[1.2, 1.2, 1.0], offset=[0.0, 2.2], function="3-D Hall on the pen-lift module reading a 1 mm diametric magnet "
           "on the drum: slide = drum angle x 2.8 mm.  Pen-down, pen-up and the front-stop logic use it.",
           part="TMAG5273-class 3-D Hall (WSON) + d 1 mm magnet (ASSUMPTION package)", ledger="OPT-45; AMF-72", mass_g=0.05))
    A(comp("arm", "Short rear arm", "moving_nose", "tube", zp + 1.5, cap_front, "nose", 5.0, 5.0, 3.6,
           function="Carries the magnet cap 11.5 mm behind the gimbal; the refill holder may enter it; it carries the rear "
                    "tendon pulley.", part="custom (aluminium 6061 tube 5/3.6 mm)", ledger="", mass_g=_tube(5.0, 3.6, cap_front - zp - 1.5, _rho("Al"))))
    A(comp("rear_pulley", "Rear tendon pulley", "mechanism", "cylinder", sl["rear_pulley_z_mm"][0], sl["rear_pulley_z_mm"][1],
           "nose", 1.5, 1.5, function="Turns the tendon loop behind the holder's rearmost position, inside the arm.",
           part="custom (PTFE pulley d 1.5 mm)", ledger="", mass_g=0.02))
    A(comp("position_magnet", "Nose position magnet", "sensor", "box", MAG_Z[0], MAG_Z[1], "nose", size=[1.0, 2.0, 2.0],
           offset=[3.5 + 0.5, 0.0], function="Small magnet on top of the carrier, read by the two linear Hall sensors on the main "
           "board's underside above it (the carrier moves 1.2 mm here for 6.6 mm at the ball).", part="NdFeB N52 2 x 2 x 1 mm, magnetised along x",
           ledger="AMF-139", mass_g=7.6e-3 * 4.0))
    # ------------------------------------------------------------------ actuator (study N's C1S)
    cap = comp("magnet_cap", "Magnet cap (2 x 2 checkerboard, spherical face)", "actuator", "cylinder", cap_front, za, "nose",
               2 * nd["r_disc"], 2 * nd["r_disc"],
               function="Four N52 poles on a spherical Hiperco cap centred on the gimbal; tilting slides the poles along the coils "
                        f"at a constant 0.77 mm gap.  Its rim is flattened at the bottom (to {CAP_FLAT_R:.1f} mm radius) where the "
                        "drive shafts pass; the poles end 6.3 mm from the axis there, so the flat costs no pole area.",
               part=f"NdFeB N52 segments {nd['w']:.1f} x {nd['w']:.1f} x {nd['t_m']:.1f} mm on a Hiperco 50A cap (custom)",
               ledger="AMF-139; AMF-140", mass_g=nd["m_act_move_g"])
    cap["notch"] = {"flat_at_bottom_radius_mm": CAP_FLAT_R}
    A(cap)
    plate = comp("coil_plate", "Two-layer spherical coil plate and back iron", "actuator", "cylinder", z_plate0, z_plate1, "handle",
                 2 * BORE_R, 2 * BORE_R,
                 function="x and y coil layers (0.55 mm) on a Hiperco plate concentric with the cap; the plate's rim is notched "
                          f"at the bottom (r > {NOTCH_R:.2f} mm, +-10 deg) for the drive shafts.  Its back iron is drawn at "
                          f"study N's model thickness ({t_bi:.2f} mm; study N's layout drew 0.8 mm).",
                 part="custom (bonded 0.20 mm wire coils on a formed Hiperco 50A plate)", ledger="AMF-29; AMF-30; AMF-140",
                 mass_g=nd["m_act_stat_g"])
    plate["notch"] = {"bottom_rim_radius_mm": NOTCH_R, "half_angle_deg": 10.0}
    A(plate)
    gim = comp("gimbal", "Flexure gimbal (2-axis)", "mechanism", "tube", zp - 1.5, zp + 1.5, "handle", 21.0, 21.0, 5.5,
               function=f"Cross-strip flexures: the nose tilts +-{math.degrees(nz.alpha_u):.1f} deg (usable) in two directions; "
                        "its frame is notched at the bottom for the shafts.", part="custom (301 FH 0.050 mm strips, laser cut)",
               ledger="AMF-20", mass_g=2.0)
    gim["notch"] = {"bottom_rim_radius_mm": NOTCH_R}
    A(gim)
    # ------------------------------------------------------------------ skid, grip, structure
    ring_m = _tube(2 * R_s, 2 * dm["ring_bore_r"], RU.ring_len, _rho("POM")) * 240.0 / 360.0
    ring = comp("skid_ring", "Skid ring (C-shaped heel) with the wheel slot", "skid", "tube", z_ring, z_ring + RU.ring_len, "handle",
                2 * R_s, 2 * R_s, 2 * dm["ring_bore_r"],
                function=f"Rests on the paper and carries the writing force above the wheel's preload; contact radius {R_s:.2f} mm "
                         f"(study N alone: 10.0; study D on Rev H: 8.40).  The nose swings inside its lip; it is open 120 deg on "
                         f"top so the ink stays visible; the heel wheel reaches the paper through a 3.2 mm slot at the bottom.",
                part=f"custom (PTFE-coated POM; contact radius {R_s:.2f} mm, flush with the sleeve front)", ledger="DEC-034",
                mass_g=ring_m)
    ring["open_deg"] = 120.0
    ring["notch"] = {"wheel_slot_width_mm": 3.2}
    A(ring)
    z_s0 = z_ring + RU.ring_len
    sleeve_bore = 2 * dm["sleeve_bore_r"]
    sleeve_m = _tube(0.5 * (2 * R_s + D_HANDLE), sleeve_bore, BOARD_Z[0] - z_s0, 0.5 * (_rho("PEEK") + _rho("TPE")))
    sl_c = comp("front_sleeve", "Front sleeve (fixed grip)", "grip", "tube", z_s0, BOARD_Z[0], "handle", 2 * R_s, D_HANDLE, sleeve_bore,
                function="Where the fingers rest; it does not move.  Its bottom wall carries the two drive shafts in grooves; a "
                         "small cheek on one side of the heel holds the page sensor; its first 10 mm continue the ring's top "
                         "opening (C) so the ink stays visible at shallow tilts.",
                part="PEEK core + TPE overmould", ledger="AMF-24", mass_g=sleeve_m)
    sl_c["open_deg_front"] = {"deg": 120.0, "length_mm": 10.0}
    A(sl_c)
    A(comp("shell", "Handle shell", "structure", "tube", BOARD_Z[0], z_shell1, "handle", D_HANDLE, D_HANDLE, 2 * BORE_R,
           function="The body you hold: 24 mm across; grooves in its bottom wall carry the drive shafts past the actuator.",
           part="PEEK or glass-filled nylon, 1 mm wall", ledger="AMF-24", mass_g=_tube(D_HANDLE, 2 * BORE_R, z_shell1 - BOARD_Z[0], _rho("PEEK"))))
    rc = comp("rear_cap", "Rear cap (base pen)", "structure", "cylinder", z_shell1, z_shell1 + 3.0, "handle", D_HANDLE, D_HANDLE - 2.0,
              function="Closes the base pen; unscrews so the end-cap can take its place.", part="custom (PEEK)", ledger="AMF-24",
              mass_g=_tube(D_HANDLE, 0.0, 3.0, _rho("PEEK")) * 0.6)
    rc["replaced_by_endcap"] = True
    A(rc)
    # ------------------------------------------------------------------ sensors and electronics
    A(comp("main_board", "Main board (along the top)", "electronics", "box", BOARD_Z[0], BOARD_Z[1], "handle",
           size=[BOARD_X[1] - BOARD_X[0], 14.0, BOARD_Z[1] - BOARD_Z[0]], offset=[0.5 * (BOARD_X[0] + BOARD_X[1]), 0.0],
           function="Lies along the top of the handle above the swinging carrier: MCU with Bluetooth, two coil drivers, the "
                    "pen-lift driver, two 3-phase motor drivers, the charger, the IMU and the nose's two linear Hall "
                    "sensors.",
           part="nRF54L15 + 2 x DRV8214 + 2 x DRV8311-class + charger + LSM6DSV16X + 2 x DRV5055-A4 (14 x 22 mm, "
                "ASSUMPTION)",
           ledger="AMF-44; AMF-37; OPT-37; OPT-46", mass_g=5.5))
    A(comp("imu", "Motion sensor (IMU)", "sensor", "box", 55.0, 57.5, "handle", size=[0.83, 3.0, 2.5], offset=[BOARD_X[1] + 0.42, 0.0],
           function="Accelerometer and gyroscope on the main board, 57 mm from the tip (Rev H: 92 mm).", part="ST LSM6DSV16X",
           ledger="OPT-37"))
    A(comp("nose_hall", "Nose position sensors (two linear Halls)", "sensor", "box", MAG_Z[0] - 0.5, MAG_Z[1] + 0.5, "handle",
           size=[0.7, 4.0, 3.0], offset=[BOARD_X[0] - 0.35, 0.0],
           function="Two linear Halls 2.4 mm apart on the board's underside, 2.8 mm above the carrier's magnet: x from the "
                    "sum, y from the difference (uniform fields cancel in y).  Moved here from behind the coil plate.",
           part="2 x TI DRV5055-A4 (+-169 mT), SOT-23", ledger="OPT-46"))
    z_w = z_ring + win["s_mm"]
    ps_body = comp("page_sensor", "Page sensor (folded optics beside the heel)", "sensor", "box", z_w - 0.5, z_w + 4.5, "handle",
                   size=[2.0, 3.0, 5.0], offset=[-10.3, 5.0],
                   function=f"Sees the paper beside the heel wheel, 2.4 mm below its lens, at 1 kHz: where the pen is on the page "
                            f"(autowrite, capture) and wheel slip (heel drive).  Its window sits where the height changes least "
                            f"with tilt ({ps['height_band_mm']['roll0'][0]:.2f}-{ps['height_band_mm']['roll0'][1]:.2f} mm over 35-75 deg); "
                            f"a mirror folds the view to a chip-on-board die in the sleeve wall.",
                   part="optical-flow die (PMW3360 class performance, 1 kHz; its own package does not fit) + lens + 45 deg mirror "
                        "(PROPOSED DESIGN)", ledger="OPT-54; AMF-109", mass_g=1.0)
    ps_body["window"] = {"z_mm": z_w, "r_mm": win["r_mm"], "phi_deg": win["phi_deg"], "y_mm": win["y_mm"]}
    A(ps_body)
    A(comp("usb", "USB-C port and button", "electronics", "box", z_cell1 - 4.0, z_cell1 - 0.5, "handle", size=[8.4, 2.6, 3.5],
           offset=[0.0, 9.0], function="Charging and mode button, beside the cell's rear end (as study K moved it).",
           part="USB-C receptacle (mid-mount)", ledger="", mass_g=0.5))
    A(comp("battery", "Rechargeable cell (lifted 3 mm)", "power", "cylinder", z_cell0, z_cell1, "handle", cell_d, cell_d,
           offset=[CELL_OFFSET_X, 0.0], function="EEMB LIR14500, 750 mAh; its axis is 3 mm above the pen's so the two motors fit "
                                                "under it.", part="EEMB LIR14500", ledger="AMF-80", mass_g=PA.POWER["cell_g"].value))
    A(comp("lra", "Vibration cue motor", "haptic", "box", z_mot[1] + 0.8, z_mot[1] + 8.8, "handle", size=[3.0, 8.0, 8.0],
           offset=[-8.6, 0.0], optional=True, function="Gentle buzz cues, lying flat against the bottom wall under the cell.",
           part="coin LRA 8 mm", ledger="AMF-45", mass_g=1.0))
    # ------------------------------------------------------------------ heel drive (study D, repacked)
    A(comp("drive_wheel", "Heel wheel with O-ring tyre", "drive", "cylinder", wheel_c[2] - 0.5, wheel_c[2] + 0.5, "drive",
           2 * h.r_e, 2 * h.r_e, offset=[float(wheel_c[0]), 0.0],
           function=f"2 mm wheel in the ring's bottom slot, contact radius {R_d:.2f} mm (0.35 mm beyond the ring): steered about "
                    f"the paper normal through its contact, driven through a 2:1 bevel (study D).",
           part="custom brass hub + NBR O-ring 0.6 mm cord; axle d 0.3 mm in jewel bearings", ledger="AMF-111; AMF-112",
           mass_g=0.006))
    A(comp("drive_fork", "Steering fork and crown", "drive", "cylinder", crown_c[2] - 0.5, crown_c[2] + 0.5, "drive",
           2 * h.cap_r, 2 * h.cap_r, offset=[float(crown_c[0]), 0.0],
           function="Holds the wheel; its crown (the steering ring, r 1.5 mm, 2-3 mm above the contact along the paper normal) is "
                    "what sets the heel's size.", part="custom (hardened steel fork, brass crown module 0.1)", ledger="", mass_g=0.08))
    A(comp("drive_pod", "Heel pod (sprung)", "drive", "box", z_s0, z_s0 + 4.0, "drive", size=[2.1, 4.0, 4.0], offset=[-10.75, 0.0],
           function="Bearing block for the fork and the two bevel pinions; hangs on the preload flexure (0.55 N).",
           part="custom (PEEK housing, jewel bearings)", ledger="", mass_g=0.075))
    A(comp("drive_spring", "Preload flexure", "drive", "box", z_s0 + 4.0, z_s0 + 9.0, "handle", size=[0.3, 2.0, 5.0],
           offset=[-11.2, 0.0], function="Leaf spring in the sleeve's bottom wall between the shafts: presses the pod down with "
           f"0.55 N over {fe['spring_travel_mm']:.2f} mm of travel.", part="custom (17-7PH leaf 0.1 mm)", ledger="AMF-20",
           mass_g=0.01))
    A(comp("drive_load_sensor", "Wheel-load sensor", "drive", "box", z_s0 + 7.5, z_s0 + 8.5, "handle", size=[0.8, 1.5, 1.0],
           offset=[-10.5, 0.0], function="Linear Hall reading the flexure's bend (the wheel's load).",
           part="DRV5055 class + 1 mm magnet", ledger="OPT-46; AMF-72", mass_g=0.02))
    A(comp("drive_steer_sensor", "Steering-angle sensor", "drive", "box", z_s0 + 1.2, z_s0 + 2.2, "drive", size=[0.8, 1.5, 1.0],
           offset=[-10.2, -3.0], function="3-D Hall reading a diametric magnet on the fork (heading at the wheel).",
           part="TMAG5273 class + d 1 mm magnet", ledger="OPT-45", mass_g=0.02))
    z_sh0 = z_s0 + 2.0
    for name, sgn in (("drive_shaft_drive", 1.0), ("drive_shaft_steering", -1.0)):
        A(comp(name, "Drive shaft" if sgn > 0 else "Steering shaft", "drive", "cylinder", z_sh0, z_gear[0], "drive", 0.8, 0.8,
               offset=[SHAFT_XY[0], sgn * SHAFT_XY[1]],
               function="0.8 mm steel shaft in a PTFE liner, in a groove of the sleeve and shell bottom wall, from the transfer "
                        f"gears behind the coil plate to the heel pod ({z_gear[0] - z_sh0:.0f} mm; study D: 39 mm).",
               part="custom (austenitic stainless shaft d 0.8 mm, PTFE liner d 1.0 mm)", ledger="",
               mass_g=math.pi / 4 * 0.64 * (z_gear[0] - z_sh0) * _rho("steel") + math.pi / 4 * (1.0 - 0.64) * (z_gear[0] - z_sh0) * 2.2e-3))
    A(comp("drive_transfer", "Transfer gears", "drive", "box", z_gear[0], z_gear[1], "handle", size=[6.4, 10.0, 2.0], offset=[-7.7, 0.0],
           function="Two 3-gear trains (in two planes) that move each motor's output out to its shaft at the bottom wall.",
           part="module 0.1 brass gears, idler about d 3 mm (ASSUMPTION)", ledger="", mass_g=0.25))
    for name, sgn, lab, fn in (("drive_motor", 1.0, "Wheel drive motor", "Turns the wheel (lead-through and autowrite modes only)."),
                               ("steer_motor", -1.0, "Steering motor", "Turns the wheel's heading.")):
        A(comp(name, lab, "drive", "cylinder", z_mot[0], z_mot[1], "handle", PA.MOTOR["d_mm"].value, PA.MOTOR["d_mm"].value,
               offset=[MOTOR_XY[0], sgn * MOTOR_XY[1]], function=fn + "  Under the lifted cell, behind the actuator.",
               part="Faulhaber 0620 B brushless DC, 6 x 20 mm", ledger="AMF-100", mass_g=PA.MOTOR["mass_g"].value))
    # ------------------------------------------------------------------ end-cap (study K, moved to the new cell end)
    for p in ec["components"]:
        q = dict(p)
        if q["id"] == "ec_usb_moved":
            continue                                  # the USB is already beside the cell's end in Rev J
        q["z0"] = round(q["z0"] + ec_shift, 2)
        q["z1"] = round(q["z1"] + ec_shift, 2)
        q["group"] = "inertial"
        q["optional"] = True
        for k in ("d0", "d1", "d_in"):
            if k in q:
                q[k] = round(q[k], 2)
        if "mass_g" in q:
            q["mass_g"] = round(q["mass_g"], 3)
        A(q)
    for c in comps:
        for k in ("z0", "z1"):
            c[k] = round(float(c[k]), 2)
        if "offset" in c:
            c["offset"] = [round(float(v), 2) for v in c["offset"]]
        if "size" in c:
            c["size"] = [round(float(v), 2) for v in c["size"]]
        if c.get("mass_g") is not None:
            c["mass_g"] = round(float(c["mass_g"]), 3)
    geo = {"units": "mm", "axis": "z along the pen axis from the ball tip (z = 0 at 50 deg, nose centred) toward the back; x in "
                                  "the tilt plane, positive away from the paper; y lateral",
           "pivot_z": round(zp, 2), "actuator_z": round(za, 2), "tip_travel_mm": round(fe["X_nom_mm"], 2),
           "tip_travel_min_35_75_mm": round(fe["ball_travel_usable_min_mm"], 3),
           "magnet_stroke_mm": round(nz.alpha_s * nd["L_b"], 2), "lever_tip_per_magnet": round(zp / nd["L_b"], 3),
           "tilt_deg": 50.0, "front_opening_d": round(sleeve_bore, 2), "skid_contact_radius": R_s,
           "heel_contact_radius": R_d, "ball_protrusion_mm": round(z_ring, 2), "handle_od": D_HANDLE,
           "length": round(L_base, 2), "length_with_endcap": round(z_shell1 + PA.ENDCAP["length_mm"].value, 2),
           "grip_zone": {"z0": 20.0, "z1": 45.0}, "hand": {"finger_pads_z": [26.0, 32.0, 38.0], "web_z": 92.0},
           "refill_slide_mm": round(sl["slide_range_mm"], 2), "components": comps}
    geo["fit_checks"] = fit_checks(geo, fe, nz, nd, rf, ps, h)
    geo["_internal"] = {"fe": fe, "refill": rf, "page_sensor": ps, "z_cell": [z_cell0, z_cell1], "z_motor": list(z_mot),
                        "z_gear": list(z_gear), "z_plate": [z_plate0, z_plate1], "ec_shift": ec_shift}
    return geo


# --------------------------------------------------------------------------------------------------- fit checks
def _c(geo, cid):
    return next(c for c in geo["components"] if c["id"] == cid)


def _env_nose_stop(z: np.ndarray, nz: FR.NoseGeo) -> np.ndarray:
    """Radius of the swinging carrier (Ø7) at its stop, against z behind the ball (mm)."""
    return 3.5 + nz.alpha_s * np.abs(nz.z_p - z)


def fit_checks(geo: Dict, fe: Dict, nz: FR.NoseGeo, nd: Dict, rf: Dict, ps: Dict, h: FR.Heel) -> Dict:
    """Clearances of the integrated layout (CALC); every value is a margin beyond its rule (>= 0 passes)."""
    out = {}
    ru = RU
    # front end (closure rules; revj.frontend.check)
    out["guaranteed_travel_mm"] = round(fe["ball_travel_usable_min_mm"] - 6.0, 3)
    out["skid_ring_wall_mm"] = round(fe["ring_wall_mm"] - ru.ring_wall_min, 3)
    out["nozzle_above_paper_mm"] = round(fe["nozzle_clear_usable_min_mm"] - ru.c_paper, 3)
    out["sleeve_front_above_paper_mm"] = round(fe["sleeve_front_clear_min_mm"], 3)
    out["carrier_at_stop_mm"] = round(fe["carrier_stop_clearance_mm"], 3)
    out["heel_pod_to_nose_at_stop_mm"] = round(fe["pod_clearance_min_mm"], 3)
    # parts behind the ring on the paper side above the paper over 35-75 deg (0.3 mm), including the page-sensor cheek
    R_s = fe["R_mm"]
    z_ring = protrusion(50.0, R_s)
    worst = 1e9
    for cid in ("drive_pod", "drive_spring", "drive_load_sensor", "page_sensor"):
        c = _c(geo, cid)
        sx, sy, _ = c["size"]
        ox, oy = c["offset"]
        for z in (c["z0"], c["z1"]):
            for x in (ox - sx / 2, ox + sx / 2):
                for y in (oy - sy / 2, oy + sy / 2):
                    r = math.hypot(x, y)
                    phi = math.degrees(math.atan2(abs(y), -x)) if x < 0 else 90.0 + math.degrees(math.atan2(x, abs(y)))
                    hmin = float(np.min(FR.window_height(R_s, z - z_ring, r, phi, np.linspace(35, 75, 41))))
                    worst = min(worst, hmin)
    out["heel_parts_above_paper_35_75_mm"] = round(worst - 0.3, 3)
    # the pod housing and the page sensor's body against the nose's envelope at its stop (0.3 mm)
    s_env, env, _ = FR.envelope(R_s, nz)
    for cid in ("drive_pod", "page_sensor"):
        c = _c(geo, cid)
        sx, sy, _ = c["size"]
        ox, oy = c["offset"]
        xi = ox + sx / 2                                             # inner face (toward the axis; x < 0 parts)
        r_in = math.hypot(xi, max(0.0, abs(oy) - sy / 2))
        s_rng = np.linspace(c["z0"], c["z1"], 21) - z_ring
        out[f"{cid}_to_nose_at_stop_mm"] = round(r_in - float(np.max(np.interp(s_rng, s_env, env))) - 0.3, 3)
    out["refill_holder_to_cap_mm"] = round(rf["slide"]["rear_pulley_to_cap_mm"] - 0.3, 3)
    out["refill_spring_goodman_small_SF"] = round(rf["spring"]["chosen"]["SF_small"] - 1.3, 3)
    # page sensor: lens height within its reference band (2.2-2.6 mm, MFR OPT-54) over 35-75 deg with the pen unrolled
    lo, hi = ps["height_band_mm"]["roll0"]
    out["page_sensor_height_band_roll0_mm"] = round(min(lo - 2.2, 2.6 - hi), 3)
    # mid-section: main board above the swinging carrier (+ the position magnet), and the Hall-magnet gap
    z = np.linspace(_c(geo, "main_board")["z0"], _c(geo, "main_board")["z1"], 45)
    env = _env_nose_stop(z, nz)
    mag = (z >= MAG_Z[0]) & (z <= MAG_Z[1])
    top = env + np.where(mag, 1.0, 0.0)
    out["board_underside_to_nose_mm"] = round(float(np.min((BOARD_X[0] - 0.6) - top)) - 0.3, 3)
    hs = _c(geo, "nose_hall")
    z_m = 0.5 * (MAG_Z[0] + MAG_Z[1])
    mag_top_stop = 3.5 + 1.0 + nz.alpha_s * (nz.z_p - z_m)
    out["hall_to_magnet_at_stop_mm"] = round((hs["offset"][0] - hs["size"][0] / 2) - mag_top_stop - 0.3, 3)
    # actuator: cap and plate in the bore; the shafts past the flattened cap, the notched plate and gimbal
    liner_in = math.hypot(*SHAFT_XY) - LINER_D / 2
    out["cap_rim_in_bore_at_stop_mm"] = round(BORE_R - (nd["r_disc"] + nz.alpha_s * nd["L_b"]) - 0.3, 3)
    out["shaft_to_cap_flat_at_stop_mm"] = round(liner_in - (CAP_FLAT_R + nz.alpha_s * nd["L_b"]) - 0.3, 3)
    out["shaft_to_plate_notch_mm"] = round(liner_in - NOTCH_R - 0.3, 3)
    out["shaft_to_gimbal_notch_mm"] = round(liner_in - NOTCH_R - 0.3, 3)
    # skin outside the shaft grooves: the shell (r 12) and the tapered front sleeve at the shafts' front end
    sl = _c(geo, "front_sleeve")
    sh = _c(geo, "drive_shaft_drive")

    def r_sleeve(z: float) -> float:
        return sl["d0"] / 2 + (sl["d1"] - sl["d0"]) / 2 * (z - sl["z0"]) / (sl["z1"] - sl["z0"])
    liner_out = math.hypot(*SHAFT_XY) + LINER_D / 2
    out["shaft_liner_skin_mm"] = round(min(D_HANDLE / 2, r_sleeve(sh["z0"])) - liner_out - 0.3, 3)
    fl = _c(geo, "drive_spring")
    out["preload_flexure_skin_mm"] = round(r_sleeve(fl["z0"]) - (abs(fl["offset"][0]) + fl["size"][0] / 2) - 0.3, 3)
    ls = _c(geo, "drive_load_sensor")
    out["preload_flexure_to_load_sensor_mm"] = round((abs(fl["offset"][0]) - fl["size"][0] / 2)
                                                     - (abs(ls["offset"][0]) + ls["size"][0] / 2), 3)
    st = _c(geo, "drive_steer_sensor")                          # static parts: gap >= 0
    out["steer_sensor_to_steering_shaft_mm"] = round(abs(st["offset"][1]) - st["size"][1] / 2 - (SHAFT_XY[1] + LINER_D / 2), 3)
    out["shafts_to_page_sensor_mm"] = round((_c(geo, "page_sensor")["offset"][1] - 1.5) - (SHAFT_XY[1] + LINER_D / 2), 3)
    out["shafts_to_preload_flexure_mm"] = round((SHAFT_XY[1] - LINER_D / 2) - 1.0, 3)
    out["cap_to_gimbal_mm"] = round(nd["cap_front"] - (nd["z_p"] + 1.5) - 0.3, 3)
    # rear: cell, motors, gears, LRA, USB in the bore
    cell_r = PA.POWER["cell_d_mm"].value / 2
    mr = PA.MOTOR["d_mm"].value / 2
    out["cell_in_bore_mm"] = round(BORE_R - (CELL_OFFSET_X + cell_r), 3)
    out["cell_behind_coil_plate_mm"] = round(_c(geo, "battery")["z0"] - _c(geo, "coil_plate")["z1"] - 0.3, 3)
    out["motor_in_bore_mm"] = round(BORE_R - (math.hypot(*MOTOR_XY) + mr), 3)
    out["motor_to_motor_mm"] = round(2 * MOTOR_XY[1] - 2 * mr - 0.3, 3)
    out["motor_to_cell_mm"] = round(math.hypot(MOTOR_XY[0] - CELL_OFFSET_X, MOTOR_XY[1]) - mr - cell_r - 0.3, 3)
    g = _c(geo, "drive_transfer")
    out["transfer_gears_to_cell_mm"] = round((CELL_OFFSET_X - cell_r) - (g["offset"][0] + g["size"][0] / 2) - 0.2, 3)
    lra = _c(geo, "lra")
    lx0, lx1 = lra["offset"][0] - lra["size"][0] / 2, lra["offset"][0] + lra["size"][0] / 2
    out["lra_in_bore_mm"] = round(BORE_R - math.hypot(lx0, lra["size"][1] / 2), 3)
    out["lra_to_cell_mm"] = round(math.hypot(CELL_OFFSET_X - lx1, 0.0) - cell_r, 3)
    usb = _c(geo, "usb")
    out["usb_to_cell_mm"] = round((usb["offset"][1] - usb["size"][1] / 2) - math.sqrt(max(cell_r ** 2 - (0.0 - CELL_OFFSET_X) ** 2, 0.0)), 3)
    # envelope
    held = [c for c in geo["components"] if not c.get("optional") and c["group"] != "inertial"
            and c["z1"] > 20.0 and c["z0"] < 100.0 and c["id"] not in ("page_sensor",)]
    r_max = 0.0
    for c in held:
        if c["shape"] == "box":
            ox, oy = c.get("offset", [0, 0])
            sx, sy, _ = c["size"]
            r_max = max(r_max, max(math.hypot(ox + a * sx / 2, oy + b * sy / 2) for a in (-1, 1) for b in (-1, 1)))
        else:
            ox, oy = c.get("offset", [0, 0])
            r_max = max(r_max, math.hypot(ox, oy) + max(c.get("d0", 0), c.get("d1", 0)) / 2)
    out["od_where_held_mm"] = round(D_HANDLE - 2 * r_max, 3)
    out["length_base_mm"] = round(PA.ENVELOPE["length_mm"].value - geo["length"], 3)
    out["length_with_endcap_mm"] = round(PA.ENVELOPE["length_mm"].value - geo["length_with_endcap"], 3)
    ecs = [c for c in geo["components"] if c["group"] == "inertial"]
    out["endcap_od_mm"] = round(PA.ENVELOPE["endcap_od_mm"].value - max(c.get("d0", 0) for c in ecs), 3)
    out["all_pass"] = bool(all(v >= -1e-9 for k, v in out.items() if k != "all_pass"))
    out["label"] = "CALC (margins beyond each rule, mm; rules ASSUMPTION: 0.3 mm running clearances, DEC-034 front-end rules)"
    return out


def round1_conflicts(fe: Dict, clearance: float = 0.3) -> Dict:
    """Why the round-1 parts do not fit together as drawn (CALC): study D's heel-drive parts, placed around the Rev H
    nose (gimbal at 45 mm), against the C1S nose's swept envelope at its stop (carrier r 3.5 mm tilting about the
    gimbal at z_p by the stop angle), with the 0.3 mm running clearance.  Positive overlap = collision."""
    from . import REPO_ROOT
    parts = json.loads((REPO_ROOT / "results" / "drive" / "layout_parts.json").read_text())["components"]
    z_p, a_s = fe["z_p_mm"], fe["alpha_s_rad"]
    r_c, z_front = 3.5, 14.32                                    # study N carrier radius; carrier front (nozzle ahead)

    def env(z: float) -> float:
        z = max(z, z_front)
        return r_c * math.cos(a_s) + max(z_p - z, 0.0) * math.sin(a_s)

    out = {}
    for c in parts:
        if c["id"] not in ("drive_motor", "steer_motor", "drive_transfer", "drive_shaft_drive", "drive_shaft_steering",
                           "drive_keel", "drive_paper_sensor"):
            continue
        ox, oy = c.get("offset") or (0.0, 0.0)
        if c["shape"] == "cylinder":
            r_in = math.hypot(ox, oy) - 0.5 * c["d0"]
        else:
            sx, sy = c["size"][0], c["size"][1]
            r_in = math.hypot(max(abs(ox) - sx / 2, 0.0), max(abs(oy) - sy / 2, 0.0))
        rows = {}
        for z in sorted({c["z0"], 0.5 * (c["z0"] + c["z1"]), c["z1"]}):
            rows[f"{z:.1f}"] = {"nose_envelope_r_mm": env(z), "overlap_mm": env(z) + clearance - r_in}
        worst = max(v["overlap_mm"] for v in rows.values())
        out[c["id"]] = {"z_mm": [c["z0"], c["z1"]], "r_inner_mm": r_in, "by_z": rows, "worst_overlap_mm": worst,
                        "collides": worst > 0.0}
    return {"parts": out, "clearance_mm": clearance, "z_p_mm": z_p, "alpha_s_rad": a_s,
            "label": "CALC (results/drive/layout_parts.json read-only; C1S nose envelope from revj/frontend.close)"}


def public(geo: Dict) -> Dict:
    """The layout without the internal working data (for layout.json)."""
    return {k: v for k, v in geo.items() if not k.startswith("_")}
