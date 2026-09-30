r"""The Rev K pen, every part placed (PROPOSED DESIGN), in the schema of results/revJ/layout.json, with the fit checks.

Frames as Rev J: z along the pen axis from the ball tip at 50 deg (nib centred) toward the back; x in the tilt plane,
positive AWAY from the paper (the paper side is -x); y lateral; mm and g.  Each component: id, label, group, shape
(cylinder | cone | tube | box), z0, z1, d0, d1, d_in, size [x, y, z], offset [x, y], moves_with ('handle' | 'nib' |
'head'), optional, function, part, ledger, mass_g.  'nib' parts translate with the carrier (+-1.26 mm at the stop);
'head' parts belong to the counter-face head (they turn and tilt with the paper; drawn at 50 deg, roll 0).  Rev J's
'nose' parts are gone; ids that keep a role keep Rev J's id (skid_ring, front_sleeve, shell, rear_cap, main_board, imu,
page_sensor, battery, lra, refill, ball, position_magnet, nose_hall).

Axial stack (base pen), from the tip:
  ring and front cone (the ink window over the top 240 deg), the page-sensor optics at the bottom of the cone, the die
  behind them; B1's carrier with its front rolling guide station; study B's actuator moved 4.5 mm forward (so that the
  wire anchor ring clears the counter-face head: PROPOSED DESIGN); a ball thrust guide on both faces of the carrier flange
  (it carries the counter-face couple, nib.couple); the four C17200 wires to the anchor ring; the main board on top
  above the wires; the counter-face head (roll cage, carriage, face, float, puck, three SQUIGGLE positioners); a
  bulkhead; the LIR14500 with the cue LRA beside it; the rear cap with two charging pads.
The heel-module variant (optional parts, 'variant': 'heel'): study D's pod and wheel at a 6.1 mm contact radius, inner
shafts in the cone, a transfer mesh, outer shafts in grooves of the bottom wall, the two motors under the cell.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths
from . import params as PR
from .params import V, val

ensure_paths()

PD, ASM, MFR, CALC = PR.PD, PR.ASM, PR.MFR, PR.CALC

# ------------------------------------------------------------------------------------------------ layout inputs
LAY = {
    "actuator_shift_mm": V(-4.5, "mm", PD, "study B's actuator stack moved forward so the wire anchor ring clears the "
                           "counter-face head's swept face (study B: back plate at z 25.93; the bore is 22 mm from z 20)"),
    "wire_length_mm": V(26.80, "mm", CALC, "study B's wire length (bnib optimiser), kept"),
    "ball_guide": V({"ball_d_mm": 0.8, "n_per_side": 6, "circle_r_mm": 8.3, "race_t_mm": 0.3, "race_w_mm": 2.26,
                     "flange_d_mm": 18.86, "flange_t_mm": 1.5, "race_spring_preload_N": 4.0, "hard_stop_um": 20.0},
                    "-", PD, "Rev K: a planar ball thrust guide on both faces of the carrier flange (Si3N4 balls on 440C "
                    "races on preloaded wave springs, hard stops 20 um behind), <= 2 um play; the races as wide as the balls' "
                    "rolling (half the flange's stroke) and clear of the wires' envelope"),
    "lateral_stop": V({"z0_mm": 16.5, "len_mm": 2.0, "d_in_mm": 2 * (1.6 + 1.2587), "d0_mm": 8.0, "k_N_m": 1.0e6},
                      "-", PD, "the carrier's lateral stop moves to the carrier tube inside the cone: a Ti bush with a thin "
                      "polyimide face on three spokes (stiff enough that the coils stay off the bore in a 1 m drop)"),
    "board": V({"z0_mm": 35.5, "len_mm": 22.8, "t_mm": 1.0, "w_mm": 14.0, "x_mm": 7.5, "comp_h_mm": 1.2},
               "mm", PD, "4-layer board on top above the wires (Rev J.1: 1 x 14 x 22 mm at x 7.5)"),
    "hall_pkg": V({"x_mm": 3.0, "y_mm": 4.9, "z_mm": 1.1, "r_mm": 4.5, "die_gap_mm": 1.7}, "mm", MFR,
                  "TMAG5170A1QDGKR, VSSOP-8 3.0 x 3.0 mm body, 4.9 mm over the leads, 1.1 mm high (OPT-44 / AMF-250); on a "
                  "flex tab carried by the rear race ring; die 1.7 mm behind the position magnet's centre (PROPOSED DESIGN: "
                  "keeps the field inside the A1 range)"),
    "head_walls": V({"carriage_od": 21.4, "carriage_id": 20.8, "cage_od": 20.2, "cage_id": 19.2},
                    "mm", PD, "follower carriage (Ti, slides in the 22 mm bore) and roll cage (PEEK-CF, turns in the carriage)"),
    "motor_box": V([2.8, 2.8, 6.0], "mm", MFR, "SQL-RV-1.8 housing (AMF-15 / AMF-106)"),
    "battery": V({"d_mm": 14.1, "l_mm": 48.5, "x_mm": 3.0, "g": 20.0}, "-", MFR, "LIR14500 (AMF-80), axis 3 mm up (Rev J.1)"),
    "lra": V({"size": [3.0, 8.0, 8.0], "x_mm": -8.3, "g": 1.0}, "-", ASM, "8 mm coin LRA on edge under the cell (AMF-45 class)"),
    "rear_cap_len_mm": V(3.0, "mm", PD, "rear cap with two gold charging pads for a cradle (pogo pins)"),
    "rho_g_cc": V({"PEEK": 1.32, "PEEK_CF": 1.40, "TPE": 1.10, "PC": 1.20, "Ti": 4.43, "steel": 7.85, "440C": 7.8,
                   "Si3N4": 3.2, "sapphire": 3.98, "N52": 7.5, "Cu": 8.89, "C17200": 8.25, "POM": 1.41},
                  "g/cm3", MFR, "handbook densities (AMF-24 PEEK, AMF-21 Ti; others catalogue)"),
}


def rho(m: str) -> float:
    return val(LAY["rho_g_cc"])[m] * 1e-3            # g/mm3


def tube_mass(d0, d_in, L, mat, d1=None):
    d1 = d0 if d1 is None else d1
    ro0, ro1 = d0 / 2, d1 / 2
    V_out = math.pi * L / 3 * (ro0 ** 2 + ro0 * ro1 + ro1 ** 2)
    return (V_out - math.pi * (d_in / 2) ** 2 * L) * rho(mat)


def comp(id, label, group, shape, z0, z1, *, d0=None, d1=None, d_in=None, size=None, offset=(0.0, 0.0), moves="handle",
         optional=False, function="", part="", ledger="", mass=None, **extra) -> Dict:
    c = {"id": id, "label": label, "group": group, "shape": shape, "z0": float(z0), "z1": float(z1)}
    if d0 is not None:
        c["d0"] = float(d0)
        c["d1"] = float(d0 if d1 is None else d1)
    if d_in is not None:
        c["d_in"] = float(d_in)
    if size is not None:
        c["size"] = [float(s) for s in size]
    c.update({"offset": [float(offset[0]), float(offset[1])], "moves_with": moves, "optional": optional,
              "function": function, "part": part, "ledger": ledger, "mass_g": None if mass is None else float(mass)})
    c.update(extra)
    return c


# ------------------------------------------------------------------------------------------------ the base pen
def base_components(fc: Dict, hd: Dict, coil: Dict) -> Dict:
    """Every part of the base Rev K pen (PROPOSED DESIGN) and the key positions."""
    b1 = PR.b1()["comps"]
    R_s = fc["R_s_mm"]
    z_ring = fc["z_ring_mm"]
    ring_len = val(PR.FRONT["ring_len_mm"])
    zg = val(PR.ENVELOPE["grip_full_od_from_z_mm"])
    D = val(PR.ENVELOPE["handle_od_held_mm"])
    wall = val(PR.FRONT["sleeve_wall_mm"])
    sh = val(LAY["actuator_shift_mm"])
    bg = val(LAY["ball_guide"])
    C = []
    P = {}
    # --- refill and nib (moving with the carrier) -------------------------------------------------------------
    C.append(comp("ball", "0.7 mm ball and tip cone", "refill", "cone", 0.0, 3.0, d0=0.7, d1=2.35, moves="nib",
                  function="writes", part="ISO 12757-1 D1 refill tip", ledger="CON-22", mass=0.0))
    C.append(comp("refill", "D1 refill (67 mm)", "refill", "cylinder", 3.0, 67.0, d0=2.35, moves="nib",
                  function="ink; slides in the carrier as the tilt changes (6.7 mm over 35-75 deg)", part="metal D1 refill",
                  ledger="CON-22; DEC-004", mass=0.84))
    zc0 = val(PR.FRONT["carrier_front_z_mm"])
    gs = val(PR.FRONT["guide_station"])
    # stack behind the keeper: front race, front balls, flange, rear balls, rear race
    kp = b1["bnib_keeper"]
    z_keeper = (kp["z0"] + sh, kp["z1"] + sh)
    zr_f = (z_keeper[1], z_keeper[1] + bg["race_t_mm"])
    zb_f = (zr_f[1], zr_f[1] + bg["ball_d_mm"])
    z_fl = (zb_f[1], zb_f[1] + bg["flange_t_mm"])
    zb_r = (z_fl[1], z_fl[1] + bg["ball_d_mm"])
    zr_r = (zb_r[1], zb_r[1] + bg["race_t_mm"])
    P.update({"keeper_z": z_keeper, "flange_z": z_fl, "front_race_z": zr_f, "rear_race_z": zr_r})
    car_z1 = z_fl[1] + 0.5
    C.append(comp("carrier", "Ti-6Al-4V carrier tube 3.2 / 2.5 mm", "moving_nib", "tube", zc0, car_z1, d0=3.2, d_in=2.5,
                  moves="nib", function="holds the refill on two rolling guide stations; carries the coils and the flange",
                  part="Ti-6Al-4V tube", ledger="AMF-21; docs/balanced_nib.md",
                  mass=tube_mass(3.2, 2.5, car_z1 - zc0, "Ti")))
    C.append(comp("carrier_front_guide", "front rolling guide station (three rollers)", "moving_nib", "tube", zc0,
                  zc0 + gs["len_mm"], d0=2 * gs["r_mm"], d_in=3.2, moves="nib",
                  function="lets the refill slide with <= 0.01 friction (REQ-BNIB-016)", part="jewel rollers in windows",
                  ledger="REQ-BNIB-016", mass=0.03))
    C.append(comp("carrier_rear_guide", "rear rolling guide station (in the flange hub)", "moving_nib", "tube",
                  z_fl[0] - 0.5, z_fl[1], d0=2 * gs["r_mm"], d_in=3.2, moves="nib", function="rear refill guide",
                  part="jewel rollers", ledger="REQ-BNIB-016", mass=0.03))
    g = coil["geometry_mm"]
    X_out = g["X_out"]
    Y_ext = g["row_centre_yc"] + g["Y_out"]
    zcoil0 = b1["bnib_magnet_1"]["z1"] + sh + val(PR.FRONT["c_run_mm"])
    m_cu = coil["m_cu_g"]
    C.append(comp("coil_x", "moving coil layer x (two concentric racetracks)", "actuator", "box", zcoil0, zcoil0 + 0.8,
                  size=[2 * X_out, 2 * Y_ext, 0.8], d_in=2 * (val(PR.FRONT["carrier_r_mm"]) + 0.1), moves="nib",
                  function="x force on the carrier", part="bonded self-supporting coil or flex, polyimide former",
                  ledger="AMF-29; nib.buildable_coil", mass=0.5 * m_cu + 0.05,
                  corner_r_mm=g["outer_corner_r"], inner_edge_mm=g["inner_edge_y"]))
    C.append(comp("coil_y", "moving coil layer y (two concentric racetracks)", "actuator", "box", zcoil0 + 0.8, zcoil0 + 1.6,
                  size=[2 * Y_ext, 2 * X_out, 0.8], d_in=2 * (val(PR.FRONT["carrier_r_mm"]) + 0.1), moves="nib",
                  function="y force on the carrier", part="as coil_x, turned 90 deg", ledger="AMF-29; nib.buildable_coil",
                  mass=0.5 * m_cu + 0.05, corner_r_mm=g["outer_corner_r"], inner_edge_mm=g["inner_edge_y"]))
    C.append(comp("carrier_flange", "carrier flange: wire clamps and the ball-guide faces", "moving_nib", "tube", z_fl[0],
                  z_fl[1], d0=bg["flange_d_mm"], d_in=2.6, moves="nib",
                  function="clamps the four wires (coil leads soldered on); runs between the two ball layers",
                  part="Ti-6Al-4V, hardened faces (TiN) or 440C inserts", ledger="PROPOSED DESIGN",
                  mass=tube_mass(bg["flange_d_mm"], 2.6, bg["flange_t_mm"], "Ti") * 0.7))
    C.append(comp("position_magnet", "1 mm N52 position magnet", "sensor", "box", zb_r[0], zb_r[0] + 1.0,
                  size=[1.0, 1.0, 1.0], offset=(val(LAY["hall_pkg"])["r_mm"], 0.0), moves="nib",
                  function="the nib Hall's target", part="N52 cube 1 mm", ledger="AMF-139", mass=0.0075))
    # --- fixed nib parts (handle) ------------------------------------------------------------------------------
    bp = b1["bnib_back_plate"]
    C.append(comp("back_plate", "1010 back plate", "actuator", "tube", bp["z0"] + sh, bp["z1"] + sh, d0=bp["d0"],
                  d_in=bp["d_in"], function="closes the magnets' flux", part="1010 steel, laser cut", ledger="AMF-140",
                  mass=bp["mass_g"]))
    for i in range(1, 5):
        m = b1[f"bnib_magnet_{i}"]
        C.append(comp(f"pole_magnet_{i}", f"N52 pole magnet {i} (checkerboard)", "magnet", "box", m["z0"] + sh, m["z1"] + sh,
                      size=m["size"], offset=m["offset"], function="gap field", part="N52 5.12 x 5.12 x 3.5 mm",
                      ledger="AMF-139", mass=m["mass_g"]))
    C.append(comp("keeper", "1010 keeper", "actuator", "tube", z_keeper[0], z_keeper[1], d0=kp["d0"], d_in=kp["d_in"],
                  function="closes the flux behind the coils; carries the front race", part="1010 steel",
                  ledger="AMF-140", mass=kp["mass_g"]))
    rw = bg["race_w_mm"]
    d_r_out, d_r_in = 2 * (bg["circle_r_mm"] + rw / 2), 2 * (bg["circle_r_mm"] - rw / 2)
    C.append(comp("front_race", "front race (on the keeper)", "mechanism", "tube", zr_f[0], zr_f[1], d0=d_r_out, d_in=d_r_in,
                  function="ball-guide race", part="440C ring, lapped", ledger="PROPOSED DESIGN",
                  mass=tube_mass(d_r_out, d_r_in, bg["race_t_mm"], "440C")))
    m_balls = bg["n_per_side"] * math.pi / 6 * bg["ball_d_mm"] ** 3 * rho("Si3N4") + 0.01
    C.append(comp("front_balls", f"{bg['n_per_side']} Si3N4 balls in a cage (front layer)", "mechanism", "tube", zb_f[0],
                  zb_f[1], d0=2 * bg["circle_r_mm"] + bg["ball_d_mm"], d_in=2 * bg["circle_r_mm"] - bg["ball_d_mm"],
                  function="carries the counter-face couple and the axial load; lets the carrier translate",
                  part="Si3N4 grade 5 balls, PEEK cage", ledger="PROPOSED DESIGN", mass=m_balls))
    C.append(comp("rear_balls", f"{bg['n_per_side']} Si3N4 balls in a cage (rear layer)", "mechanism", "tube", zb_r[0],
                  zb_r[1], d0=2 * bg["circle_r_mm"] + bg["ball_d_mm"], d_in=2 * bg["circle_r_mm"] - bg["ball_d_mm"],
                  function="as the front layer", part="Si3N4 balls, PEEK cage", ledger="PROPOSED DESIGN", mass=m_balls))
    C.append(comp("rear_race", "rear race ring on four posts", "mechanism", "tube", zr_r[0], zr_r[1], d0=d_r_out, d_in=d_r_in,
                  function="ball-guide race; carries the Hall tab", part="440C ring on four Ti posts to the shell (diagonals)",
                  ledger="PROPOSED DESIGN", mass=tube_mass(d_r_out, d_r_in, bg["race_t_mm"], "440C") + 0.08))
    ls = val(LAY["lateral_stop"])
    C.append(comp("lateral_stop", "lateral stop bush round the carrier (in the cone, on three spokes)", "mechanism", "tube",
                  ls["z0_mm"], ls["z0_mm"] + ls["len_mm"], d0=ls["d0_mm"], d_in=ls["d_in_mm"],
                  function="stops the carrier at 1.26 mm (drop, REQ-BNIB-012)", part="Ti bush, polyimide face, PEEK spokes",
                  ledger="EXP-B25", mass=tube_mass(ls["d0_mm"], ls["d_in_mm"], ls["len_mm"], "Ti") + 0.05))
    hp = val(LAY["hall_pkg"])
    z_hall0 = max(zr_r[1] + 0.1, zb_r[0] + 0.5 + hp["die_gap_mm"] - 0.55)
    C.append(comp("nose_hall", "TMAG5170 nib Hall (3-axis)", "sensor", "box", z_hall0, z_hall0 + hp["z_mm"],
                  size=[hp["x_mm"], hp["y_mm"], hp["z_mm"]], offset=(hp["r_mm"], 0.0),
                  function="nib position (x, y) at up to 10 kSPS", part="TMAG5170A1QDGKR", ledger="OPT-44; AMF-250",
                  mass=0.03))
    P["hall_die_z"] = z_hall0 + 0.55
    P["position_magnet_centre_z"] = zb_r[0] + 0.5
    wl = val(LAY["wire_length_mm"])
    w_z0 = 0.5 * (z_fl[0] + z_fl[1])
    w_z1 = w_z0 + wl
    d_w = 0.10
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1)), 1):
        r = val(PR.B1["wire_circle_r_mm"]) / math.sqrt(2)
        C.append(comp(f"wire_{i}", f"C17200 suspension wire {i} (a coil lead)", "mechanism", "cylinder", w_z0, w_z1, d0=d_w,
                      offset=(sx * r, sy * r), function="suspension and a coil lead (two per coil)",
                      part="C17200 TH04 wire 0.10 mm", ledger="AMF-19; AMF-251",
                      mass=math.pi / 4 * d_w ** 2 * wl * rho("C17200")))
    ar = b1["bnib_anchor_ring"]
    C.append(comp("anchor_ring", "wire anchor ring (the coil leads' solder pads) on an axially soft diaphragm", "structure",
                  "tube", w_z1, w_z1 + 1.5, d0=ar["d0"], d_in=ar["d_in"],
                  function="fixes the wires' rear ends laterally; axially soft (about 0.01 N/um) so that the ball guide, not "
                           "the wires, sets the flange's axial position (assembly preload <= 0.05 N); flex to the board",
                  part="FR4 / polyimide ring on a 301 steel spoked diaphragm to the shell (bottom 120 deg)",
                  ledger="PROPOSED DESIGN", mass=ar["mass_g"]))
    P["anchor_ring_z"] = (w_z1, w_z1 + 1.5)
    P["wire_z"] = (w_z0, w_z1)
    # --- front end ------------------------------------------------------------------------------------------------
    rb = fc["ring_bore_r_mm"]
    C.append(comp("skid_ring", f"skid ring (contact radius {R_s:g} mm, open 120 deg on top)", "skid", "tube", z_ring,
                  z_ring + ring_len, d0=2 * R_s, d_in=2 * rb, open_deg=val(PR.FRONT["open_deg"]),
                  function="rests on the paper and carries the writing force", part="PTFE-coated POM",
                  ledger="DEC-034", mass=tube_mass(2 * R_s, 2 * rb, ring_len, "POM") * (240.0 / 360.0)))
    zc_front = z_ring + ring_len
    slope = (D / 2 - R_s) / (zg - zc_front)
    cone_segs = [(zc_front, 10.0), (10.0, 14.0), (14.0, zg)]
    for k, (a, b) in enumerate(cone_segs, 1):
        da = 2 * (R_s + slope * (a - zc_front))
        db = 2 * (R_s + slope * (b - zc_front))
        C.append(comp(f"front_cone_{k}", f"front cone {k} (clear hard-coated PC window over the top 240 deg)", "grip", "tube",
                      a, b, d0=da, d1=db, d_in=da - 2 * wall,
                      function="the ink window (ink visibility, REQ-RVJ-I06) and the path to the paper",
                      part="hard-coated PC (top 240 deg) and PEEK (bottom 120 deg, page-sensor window)",
                      ledger="DEC-045; AMF-159", mass=tube_mass(da, da - 2 * wall, b - a, "PC", d1=db) * 0.8))
    C.append(comp("front_sleeve", "grip sleeve (24 mm)", "grip", "tube", zg, 45.0, d0=D, d_in=D - 2 * wall,
                  function="where the fingers hold (pads at z 26 / 32 / 38)", part="PEEK with a TPE skin",
                  ledger="AMF-24", mass=tube_mass(D, D - 2 * wall, 45.0 - zg, "PEEK") * 1.1))
    w = fc["window"]
    ob = val(PR.FRONT["optics_block"])
    xo = -(w["r_mm"] - 1.0)
    zo = z_ring + w["s_mm"] - 0.5
    C.append(comp("page_optics", "page-sensor lens and 45 deg mirror block", "sensor", "box", zo, zo + 2.0,
                  size=[2.0, 1.8, 2.0], offset=(xo, 0.0),
                  function="images the paper 2.2-2.6 mm below the lens at every tilt (bottom of the ring: roll-insensitive)",
                  part="custom moulded lens + mirror", ledger="OPT-61", mass=0.02))
    C.append(comp("page_sensor", "PMW3610-class optical-flow die (on a flex)", "sensor", "box", 10.2, 15.2,
                  size=[2.0, 3.0, 5.0], offset=(-5.0, 0.0), function="page position (paper-side sensor)",
                  part="PMW3610-class die, chip on flex", ledger="OPT-61; AMF-109", mass=0.5))
    # --- electronics ----------------------------------------------------------------------------------------------
    bd = val(LAY["board"])
    C.append(comp("main_board", "main board (nRF54L15, 2 x DRV8214, charger, fuel gauge, 3 x NSD-2101)", "electronics", "box",
                  bd["z0_mm"], bd["z0_mm"] + bd["len_mm"], size=[bd["t_mm"], bd["w_mm"], bd["len_mm"]],
                  offset=(bd["x_mm"], 0.0), function="control, radio, drivers", part="4-layer board",
                  ledger="OPT-60; AMF-37; AMF-15", mass=5.0))
    C.append(comp("board_parts", "components on the board's inner side", "electronics", "box", bd["z0_mm"],
                  bd["z0_mm"] + bd["len_mm"], size=[bd["comp_h_mm"], bd["w_mm"] - 2.0, bd["len_mm"]],
                  offset=(bd["x_mm"] - bd["t_mm"] / 2 - bd["comp_h_mm"] / 2, 0.0), function="ICs and passives",
                  part="-", ledger="-", mass=None))
    C.append(comp("imu", "LSM6DSV16X IMU", "sensor", "box", bd["z0_mm"] + 14.0, bd["z0_mm"] + 16.5, size=[0.83, 3.0, 2.5],
                  offset=(bd["x_mm"] + bd["t_mm"] / 2 + 0.415, 0.0), function="tilt, roll, motion", part="LSM6DSV16XTR",
                  ledger="OPT-37; AMF-254", mass=None))
    # --- counter-face head -----------------------------------------------------------------------------------------
    hw = val(LAY["head_walls"])
    mb = val(LAY["motor_box"])
    zc50 = hd["z_c50_mm"]
    pk = hd["puck"]
    z_puck0 = hd["z_r50_mm"]
    C.append(comp("refill_holder", "refill holder: vented PEEK cup + stem + 1.2 mm joint ball (the shoe is on the face)",
                  "balance", "cylinder", z_puck0 - 1.2, z_puck0 + pk["stem_mm"], d0=3.2, moves="nib",
                  function="takes the refill's plain rear end; its ball snaps into the face's shoe (pulls the refill back in "
                           "a lift)", part="PEEK cup, Ti stem, Si3N4 ball", ledger="PROPOSED DESIGN", mass=0.05,
                  cad="cup_stem_ball", joint_z=z_puck0 + pk["stem_mm"], joint_ball_d=pk["joint_ball_d_mm"]))
    zO = 0.5 * (hd["follower_z_mm"][0] + hd["follower_z_mm"][1])
    P["hinge_z"] = zO
    sw0, sw1 = hd["swept_z_mm"]
    cage0 = P["anchor_ring_z"][1] + 0.6
    motor_t0 = sw1 + 1.2
    cage1 = motor_t0 + mb[2] + 0.5
    C.append(comp("head_cage", "roll cage (turns +-30 deg; carries the tilt hinge and the tilt positioner)", "balance",
                  "tube", cage0, cage1, d0=hw["cage_od"], d_in=hw["cage_id"], moves="head",
                  function="turns the face with the pen's roll", part="PEEK-CF tube, jewel rollers",
                  ledger="PROPOSED DESIGN", mass=tube_mass(hw["cage_od"], hw["cage_id"], cage1 - cage0, "PEEK_CF")))
    C.append(comp("head_carriage", "follower carriage (slides <= 3 mm; slot at the bottom for the heel variant)", "balance",
                  "tube", cage0, cage1 + 0.5, d0=hw["carriage_od"], d_in=hw["carriage_id"], moves="head",
                  function="moves the head along the pen (pen lift, refill length)", part="Ti tube 0.3 mm wall",
                  ledger="PROPOSED DESIGN", mass=tube_mass(hw["carriage_od"], hw["carriage_id"], cage1 + 0.5 - cage0, "Ti")))
    face = hd["face"]
    # the face drawn at 50 deg (roll 0) as an equivalent axial box: its centre, its axial and radial extent
    from .counterface import Head, normal
    h = Head(R_s, hd["L_O_mm"], hd["x_h_mm"])
    pts = np.array(h.plate_points(50.0, face["u0_mm"], face["u1_mm"], face["width_mm"], back=1.2))
    xs, zs = pts[:, 0], pts[:, 2]
    C.append(comp("head_shoe", "captive shoe on three rolling balls (drawn at 50 deg)", "balance", "box",
                  float(h.z_c(50.0)) - 1.0, float(h.z_c(50.0)) + 1.0, size=[1.0, pk["shoe_d_mm"], 1.0], moves="head",
                  function="rides on the face under the tray's rim; the refill's joint ball snaps into its slotted socket",
                  part="PEEK-CF shoe, three 0.5 mm Si3N4 balls", ledger="PROPOSED DESIGN", mass=0.03, cad="tilted_shoe",
                  shoe_d=pk["shoe_d_mm"], r_pb=pk["r_pb_mm"]))
    C.append(comp("head_face", "counter-face: sapphire tray on a Ti bracket (drawn at 50 deg)", "balance", "box",
                  float(zs.min()), float(zs.max()), size=[float(xs.max() - xs.min()), face["width_mm"], float(zs.max() - zs.min())],
                  offset=(float(0.5 * (xs.max() + xs.min())), 0.0), moves="head",
                  function="parallel to the paper; pushes the puck with the ink force F_n",
                  part="0.3 mm sapphire + Ti-6Al-4V bracket and hinge arms", ledger="AMF-160; AMF-21",
                  mass=face["length_mm"] * face["width_mm"] * 0.3 * rho("sapphire") + 0.25,
                  tilt_deg=50.0, face_plate_mm=[face["length_mm"], face["width_mm"]],
                  plate_corners_50deg=[[float(p[0]), float(p[1]), float(p[2])] for p in pts]))
    n50 = normal(50.0)
    C.append(comp("head_float", "float flexure + constant-force spring (on the bracket)", "balance", "box",
                  float(zs.max()), float(zs.max()) + 1.5, size=[3.0, 4.0, 1.5],
                  offset=(float(0.5 * (xs.max() + xs.min())), 0.0), moves="head",
                  function=f"the face floats +-{hd['gap_mm']:.2f} mm along its normal between two stops (front: the "
                           "follower stop)", part="parallel strip flexure 301 steel, constant-force strip spring",
                  ledger="PROPOSED DESIGN", mass=0.10))
    C.append(comp("head_tilt_motor", "tilt positioner SQL-RV-1.8 + crank", "balance", "box", motor_t0, motor_t0 + mb[2],
                  size=mb, offset=(-7.3, 0.0), moves="head", function="sets the face's tilt (hinge 15-55 deg)",
                  part="New Scale SQL-RV-1.8 + NSD-2101", ledger="AMF-15; AMF-106", mass=val(PR.HEAD["pos_mass_g"]) + 0.03))
    C.append(comp("head_balance_spring", "tilt balance spring (torsion)", "balance", "box", motor_t0, motor_t0 + 2.0,
                  size=[1.0, 3.0, 2.0], offset=(-8.9, 0.0), moves="head",
                  function="carries the mean F_n x u so the tilt positioner moves the residual", part="301 steel torsion spring",
                  ledger="PROPOSED DESIGN", mass=0.02))
    C.append(comp("face_hall", "face-position Hall (TMAG5273 class) + 1 mm magnet", "sensor", "box", motor_t0 - 1.0,
                  motor_t0, size=[1.0, 2.0, 1.0], offset=(3.0, 0.0), moves="head",
                  function="float position: touchdown, lift, refill seated", part="TMAG5273 class", ledger="OPT-45",
                  mass=0.03))
    zm = cage1 + 0.8
    C.append(comp("head_roll_motor", "roll positioner SQL-RV-1.8 (on a 5.5 mm crank of the cage)",
                  "balance", "box", zm, zm + mb[2], size=mb, offset=(0.0, 7.3),
                  function="turns the cage +-30 deg", part="SQL-RV-1.8 + NSD-2101", ledger="AMF-15; AMF-106",
                  mass=val(PR.HEAD["pos_mass_g"]) + 0.05))
    C.append(comp("head_follower_motor", "follower positioner SQL-RV-1.8 (the pen lift)", "balance", "box", zm, zm + mb[2],
                  size=mb, offset=(0.0, -7.3), function="moves the carriage: the pen lift (DEC-050) and the refill length",
                  part="SQL-RV-1.8 + NSD-2101", ledger="AMF-15; AMF-106", mass=val(PR.HEAD["pos_mass_g"]) + 0.03))
    C.append(comp("head_flex", "head flex (three motor drives, face Hall)", "electronics", "box", zm, zm + mb[2],
                  size=[0.3, 8.0, mb[2]], offset=(7.5, 0.0), function="to the main board", part="polyimide flex",
                  ledger="-", mass=0.15))
    zbh = zm + mb[2] + 0.5
    C.append(comp("bulkhead", "bulkhead (head drop stop, cell stop)", "structure", "cylinder", zbh, zbh + 0.8, d0=21.8,
                  function="carries the refill's blow in a drop through the head; locates the cell", part="PEEK disc",
                  ledger="PROPOSED DESIGN", mass=math.pi / 4 * 21.8 ** 2 * 0.8 * rho("PEEK") * 0.6))
    P["head_z"] = (cage0, zbh + 0.8)
    # --- cell, cue, rear ---------------------------------------------------------------------------------------------
    bt = val(LAY["battery"])
    zb0 = zbh + 0.8 + 0.5
    C.append(comp("battery", "LIR14500 Li-ion cell (2.22 Wh usable)", "power", "cylinder", zb0, zb0 + bt["l_mm"],
                  d0=bt["d_mm"], offset=(bt["x_mm"], 0.0), function="energy", part="LIR14500 750 mAh",
                  ledger="AMF-80", mass=bt["g"]))
    lr = val(LAY["lra"])
    C.append(comp("lra", "cue LRA 8 mm (on edge under the cell)", "haptic", "box", zb0 + 0.5, zb0 + 0.5 + lr["size"][2],
                  size=lr["size"], offset=(lr["x_mm"], 0.0), function="tick cues (spelling, guidance)",
                  part="8 mm coin LRA", ledger="AMF-45", mass=lr["g"]))
    P["lra_z"] = (zb0 + 0.5, zb0 + 0.5 + lr["size"][2])
    z_shell1 = zb0 + bt["l_mm"] + 0.5
    C.append(comp("shell", "PEEK shell 24 / 22 mm", "structure", "tube", 45.0, z_shell1, d0=D, d_in=D - 2 * wall,
                  function="structure", part="PEEK, machined (100) / moulded (1000)", ledger="AMF-24",
                  mass=tube_mass(D, D - 2 * wall, z_shell1 - 45.0, "PEEK")))
    rc = val(LAY["rear_cap_len_mm"])
    C.append(comp("rear_cap", "rear cap with two charging pads", "structure", "cylinder", z_shell1, z_shell1 + rc, d0=D,
                  d1=D - 2.0, function="closes the pen; charging contacts; the button", part="PEEK cap, gold pads, pogo cradle",
                  ledger="PROPOSED DESIGN", mass=math.pi / 4 * (D - 1.0) ** 2 * rc * rho("PEEK") * 0.35))
    C.append(comp("charging_pads", "two gold charging pads", "electronics", "box", z_shell1 + rc - 0.3, z_shell1 + rc,
                  size=[6.0, 10.0, 0.3], offset=(0.0, 0.0), function="cradle charging (5 V, pogo pins)",
                  part="gold-plated brass pads", ledger="PROPOSED DESIGN", mass=0.1))
    P["length"] = z_shell1 + rc
    P["battery_z"] = (zb0, zb0 + bt["l_mm"])
    return {"components": C, "positions": P}


# ------------------------------------------------------------------------------------------------ the heel variant
def heel_components(fc_h: Dict, base: Dict) -> Dict:
    """Study D's steered and driven heel as an optional module (PROPOSED DESIGN, Rev J.1's parts at Rev K's radius)."""
    from .frontend import heel_shafts
    R_s, R_d = fc_h["R_s_mm"], fc_h["R_d_mm"]
    z_ring = fc_h["z_ring_mm"]
    hs = heel_shafts(R_s, R_d)
    P = base["positions"]
    C = []
    kw = dict(optional=True, variant="heel")
    C.append(comp("drive_wheel", "2 mm heel wheel (O-ring tyre)", "drive", "cylinder", z_ring - 0.5, z_ring + 0.5, d0=2.0,
                  offset=(-(R_d - 0.3), 0.0), moves="drive", function="steered and driven heel (retracted by default, DEC-048)",
                  part="PTFE hub, O-ring tyre", ledger="AMF-111; AMF-112", mass=0.01, **kw))
    C.append(comp("drive_fork", "steering fork and crown", "drive", "cylinder", z_ring + 0.6, z_ring + 1.6, d0=3.0,
                  offset=(-(R_d - 1.2), 0.0), moves="drive", function="steers the wheel about the paper normal",
                  part="module-0.1 crown", ledger="DEC-037", mass=0.08, **kw))
    C.append(comp("drive_pod", "heel pod (sprung, with the retract latch)", "drive", "box", z_ring + 1.5, z_ring + 5.5,
                  size=[2.1, 4.0, 4.0], offset=(-(R_d - 0.9), 0.0), moves="drive",
                  function="0.55 N preload; a bistable latch lifts the wheel 0.5 mm (retracted)", part="PEEK pod, 301 spring",
                  ledger="DEC-037; DEC-048", mass=0.12, **kw))
    for side, y in (("drive", 1.0), ("steering", -1.0)):
        C.append(comp(f"drive_inner_shaft_{side}", f"inner {side} shaft (in a sleeve groove)", "drive", "cylinder",
                      z_ring + 5.5, hs["gearbox_z_mm"], d0=0.8, offset=(-hs["inner_shaft_r_mm"], y), moves="handle",
                      function="pod to the transfer mesh", part="0.8 mm steel shaft in a 1.0 mm liner",
                      ledger="DEC-037", mass=math.pi / 4 * 0.8 ** 2 * (hs["gearbox_z_mm"] - z_ring - 5.5) * rho("steel"), **kw))
    C.append(comp("drive_front_transfer", "front transfer mesh (two spur pairs)", "drive", "box", hs["gearbox_z_mm"],
                  hs["gearbox_z_mm"] + 2.0, size=[3.0, 6.0, 2.0], offset=(-9.0, 0.0), function="inner to outer shafts",
                  part="module-0.1 gears, jewels", ledger="DEC-037", mass=0.12, **kw))
    zm0 = P["lra_z"][1] + 2.5
    for side, y in (("drive", 1.6), ("steering", -1.6)):
        C.append(comp(f"drive_shaft_{side}", f"outer {side} shaft (in a groove of the bottom wall)", "drive", "cylinder",
                      hs["gearbox_z_mm"] + 2.0, zm0 - 2.2, d0=0.8, offset=(-10.9, y),
                      function="motor to the front transfer", part="0.8 mm non-magnetic steel shaft in a 1.0 mm liner",
                      ledger="DEC-037", mass=math.pi / 4 * 0.8 ** 2 * (zm0 - 2.2 - hs["gearbox_z_mm"] - 2.0) * rho("steel"),
                      **kw))
    C.append(comp("drive_transfer", "rear transfer (motor to shafts)", "drive", "box", zm0 - 2.2, zm0 - 0.2,
                  size=[4.0, 8.0, 2.0], offset=(-8.2, 0.0), function="motor pinions to the shafts", part="gears",
                  ledger="DEC-037", mass=0.25, **kw))
    for side, y in (("drive", 3.2), ("steer", -3.2)):
        C.append(comp(f"{side}_motor", f"Faulhaber 0620 B {side} motor", "drive", "cylinder", zm0, zm0 + 20.0, d0=6.0,
                      offset=(-7.0, y), function="heel drive / steering", part="Faulhaber 0620 B", ledger="AMF-100",
                      mass=2.5, **kw))
    C.append(comp("drive_sensors", "pod load and steering sensors", "drive", "box", z_ring + 2.0, z_ring + 3.0,
                  size=[0.8, 1.5, 1.0], offset=(-(R_d - 2.4), 2.0), moves="drive", function="load, steer angle",
                  part="Hall + strain", ledger="OPT-45; OPT-46", mass=0.04, **kw))
    return {"components": C, "shafts": hs, "motor_z": (zm0, zm0 + 20.0)}


# ------------------------------------------------------------------------------------------------ fit checks
def _chk(cid, what, value, rule, margin, label="CALCULATION (layout geometry)", unit="mm", marginal=0.1, note=""):
    st = "fail" if margin < -1e-4 else ("marginal" if margin < marginal else "pass")
    return {"id": cid, "what": what, "value": value, "rule": rule, "margin": margin, "unit": unit, "status": st,
            "passes": st != "fail", "note": note, "label": label}


def fit_checks(fc: Dict, hd: Dict, coil: Dict, base: Dict, nibsum: Dict, cf_stack: Dict, heel: Optional[Dict] = None,
               fc_h: Optional[Dict] = None, hand: Optional[Dict] = None) -> List[Dict]:
    """Every fit check (margin beyond its rule; 'marginal' below 0.1 mm or below 1.5 x on force ratios) (CALC)."""
    from .frontend import nib_envelope
    c = {x["id"]: x for x in base["components"]}
    P = base["positions"]
    stop = val(PR.B1["stop_mm"])
    run = val(PR.FRONT["c_run_mm"])
    fix = val(PR.FRONT["c_fixed_mm"])
    R_s = fc["R_s_mm"]
    out = []
    # front end
    out.append(_chk("F1", "skid-ring lip (ring radius less its bore)", fc["ring_lip_mm"], ">= 1.0 (DEC-034)",
                    fc["ring_lip_mm"] - val(PR.FRONT["ring_wall_min_mm"])))
    w = fc["window"]
    env = float(nib_envelope(R_s, np.array([w["block_s_mm"]]))[0])
    out.append(_chk("F2", "page-sensor optics block vs the nib's envelope at the stop", w["block_inner_r_mm"] - env,
                    ">= 0.3 running", w["block_inner_r_mm"] - env - run))
    lo, hi = fc["band_mm"]["roll0"]
    out.append(_chk("F3", "lens height over 35-75 deg (no roll)", [lo, hi], "2.2-2.6 mm (MFR OPT-61)",
                    min(lo - 2.2, 2.6 - hi), label="CALCULATION (window height, revj/frontend.window_height)"))
    out.append(_chk("F4", "page sensor roll tolerance", fc["roll_tolerance_deg"], ">= 20 deg (REQ-RVJ-N06)",
                    fc["roll_tolerance_deg"] - 20.0, unit="deg", marginal=2.0))
    out.append(_chk("F5", "lens depth of field vs the lifts between strokes (REQ-BNIB-017)",
                    fc["lens_dof"]["lift_tracked_mm"], ">= 2.0 mm tracked lift",
                    fc["lens_dof"]["lift_tracked_mm"] - fc["lens_dof"]["lift_needed_mm"],
                    note="a requirement conflict for any mouse-class die; EXP-J10 / EXP-T04"))
    out.append(_chk("F6", "sleeve cone above the paper at 35-75 deg", fc["sleeve_cone"]["min_height_above_paper_mm"],
                    ">= 0.3 (DEC-034)", fc["sleeve_cone"]["min_height_above_paper_mm"] - val(PR.FRONT["c_paper_mm"])))
    out.append(_chk("F7", "carrier nozzle above the paper, nib at travel", fc["nozzle_above_paper_min_mm"], ">= 0.3",
                    fc["nozzle_rule_margin_mm"]))
    ps = c["page_sensor"]
    zc_front = fc["z_ring_mm"] + 1.5
    slope = (12.0 - R_s) / (val(PR.ENVELOPE["grip_full_od_from_z_mm"]) - zc_front)
    r_in_at = lambda z: R_s + slope * (z - zc_front) - val(PR.FRONT["sleeve_wall_mm"])
    corner = math.hypot(abs(ps["offset"][0]) + ps["size"][0] / 2, ps["size"][1] / 2)
    out.append(_chk("F8", "page-sensor die inside the cone", r_in_at(ps["z0"]) - corner, ">= 0.2 fixed",
                    r_in_at(ps["z0"]) - corner - fix))
    inner_x = abs(ps["offset"][0]) - ps["size"][0] / 2
    env_die = float(np.max(nib_envelope(R_s, np.linspace(ps["z0"], ps["z1"], 11) - fc["z_ring_mm"])))
    out.append(_chk("F9", "page-sensor die vs the nib's envelope at the stop", inner_x - env_die, ">= 0.3 running",
                    inner_x - env_die - run))
    po = c["page_optics"]
    corner_o = math.hypot(abs(po["offset"][0]) + po["size"][0] / 2, po["size"][1] / 2)
    out.append(_chk("F10", "optics block inside the cone wall", r_in_at(po["z0"]) - corner_o, ">= 0.2 fixed",
                    r_in_at(po["z0"]) - corner_o - fix))
    # nib
    g = coil["geometry_mm"]
    out.append(_chk("N1", "buildable coil corner at the stop vs the 22 mm bore", g["bore_r"] - g["corner_at_stop_r"],
                    ">= 0.3 running", g["bore_r"] - g["corner_at_stop_r"] - run))
    out.append(_chk("N2", "coil's inner end runs vs the carrier", g["inner_edge_y"] - val(PR.FRONT["carrier_r_mm"]),
                    ">= 0.1 (former edge)", g["inner_edge_y"] - val(PR.FRONT["carrier_r_mm"]) - 0.1))
    fp = nibsum["coil_footprint"]
    out.append(_chk("N3", "study B's idealised coil at the stop vs the bore (for the record)",
                    fp["idealised_corner_r_mm"] + stop, "<= 10.7 (bore 11.0 less 0.3)", fp["margin_idealised_vs_PEEK_bore_mm"],
                    note="study B's zero-width end turns; a buildable coil with the same legs: "
                         f"{fp['margin_buildable_same_legs_mm']:.2f} mm"))
    hole = c["back_plate"]["d_in"] / 2
    out.append(_chk("N4", "back plate and keeper hole vs the carrier at the stop", hole - (1.6 + stop), ">= 0.3 running",
                    hole - (1.6 + stop) - run))
    fl = c["carrier_flange"]
    out.append(_chk("N5", "flange rim at the stop vs the bore", 11.0 - (fl["d0"] / 2 + stop), ">= 0.3 running",
                    11.0 - (fl["d0"] / 2 + stop) - run))
    bg = val(LAY["ball_guide"])
    wire_env = val(PR.B1["wire_circle_r_mm"]) + stop + 0.05
    out.append(_chk("N6", "rear race ring vs the wires' envelope at the stop", bg["circle_r_mm"] - bg["race_w_mm"] / 2 - wire_env,
                    ">= 0.3 running", bg["circle_r_mm"] - bg["race_w_mm"] / 2 - wire_env - run))
    need = bg["circle_r_mm"] + bg["ball_d_mm"] / 2 + stop / 2
    out.append(_chk("N7", "balls stay on the flange face and the races at the stop (they roll half the stroke)",
                    min(fl["d0"] / 2, bg["circle_r_mm"] + bg["race_w_mm"] / 2) - need, ">= 0.05",
                    min(fl["d0"] / 2, bg["circle_r_mm"] + bg["race_w_mm"] / 2) - need - 0.05))
    ls = c["lateral_stop"]
    out.append(_chk("N20", "lateral stop bush vs the carrier tube (the stop gap)", ls["d_in"] / 2 - 1.6, "= stop 1.26 mm",
                    abs(ls["d_in"] / 2 - 1.6 - stop) * -1.0 + 0.001, marginal=0.0,
                    note="the stop itself: the coils, flange and refill clearances are all counted at this stop"))
    dl = [r for r in nibsum["drop"]["lateral"] if abs(r["k_stop_N_m"] - val(LAY["lateral_stop"])["k_N_m"]) < 1.0]
    if dl:
        d0 = dl[0]
        out.append(_chk("N21", "1 m drop sideways: the stop's deflection vs the coil's clearance at the stop",
                        d0["stop_deflection_mm"], f"<= {d0['coil_margin_mm']:.2f} mm (the coil stays off the bore)",
                        d0["coil_margin_mm"] - d0["stop_deflection_mm"], note=f"stop {d0['k_stop_N_m']:.0e} N/m, "
                        f"{d0['peak_force_N']:.0f} N, wire SF {d0['wire_static_SF']:.1f}",
                        label="CALCULATION (energy method; stop stiffness ASSUMPTION; EXP-B25)"))
    bd = val(LAY["board"])
    comp_x = bd["x_mm"] - bd["t_mm"] / 2 - bd["comp_h_mm"]
    wx = val(PR.B1["wire_circle_r_mm"]) / math.sqrt(2) + stop + 0.05
    out.append(_chk("N8", "board components vs the wires' envelope (x)", comp_x - wx, ">= 0.3 running", comp_x - wx - run))
    hp = c["nose_hall"]
    hx0 = hp["offset"][0] - hp["size"][0] / 2
    out.append(_chk("N9", "nib Hall package vs the refill at the stop", hx0 - (1.175 + stop), ">= 0.3 running",
                    hx0 - (1.175 + stop) - run))
    wpos = np.array([val(PR.B1["wire_circle_r_mm"]) / math.sqrt(2)] * 2)
    corner_h = np.array([hp["offset"][0] - hp["size"][0] / 2, hp["size"][1] / 2])
    d_hw = float(np.linalg.norm(wpos - corner_h)) - stop - 0.05
    out.append(_chk("N10", "nib Hall package vs the nearest wire at the stop", d_hw, ">= 0.3 running", d_hw - run))
    out.append(_chk("N11", "board front vs the rear race ring (axial)", bd["z0_mm"] - c["rear_race"]["z1"], ">= 0.2 fixed",
                    bd["z0_mm"] - c["rear_race"]["z1"] - fix))
    ar0 = P["anchor_ring_z"][0]
    out.append(_chk("N12", "board rear vs the anchor ring (axial)", ar0 - (bd["z0_mm"] + bd["len_mm"]), ">= 0.2 fixed",
                    ar0 - (bd["z0_mm"] + bd["len_mm"]) - fix))
    out.append(_chk("N13", "anchor ring vs the counter-face's swept plate (axial)", hd["swept_z_mm"][0] - P["anchor_ring_z"][1],
                    ">= 0.3 running", hd["swept_z_mm"][0] - P["anchor_ring_z"][1] - run))
    cp = nibsum["couple"]
    out.append(_chk("N14", "wire axial force from the counter-face couple vs sidesway buckling (without the ball guide)",
                    cp["worst"]["wire_force_N"], f"<= P_cr {cp['wire']['P_sidesway_per_wire_N']:.3f} N",
                    cp["wire"]["P_sidesway_per_wire_N"] / cp["worst"]["wire_force_N"] - 1.0, unit="x",
                    note="fails for study B's wires as designed; Rev K's ball thrust guide carries the couple"))
    hz = [r for r in cp["ball_guide_hertz"] if abs(r["ball_d_mm"] - bg["ball_d_mm"]) < 1e-6]
    h_rel = max(r["p_max_GPa"] for r in hz if r["case"] in ("couple", "race_spring_release"))
    h_rig = max(r["p_max_GPa"] for r in hz if r["case"] == "drop_2000g_rigid_races")
    out.append(_chk("N15", "ball-guide Hertz stress at the race springs' release load (the most a drop puts on a ball)", h_rel,
                    "<= 4.0 GPa (440C static, ASSUMPTION)", 4.0 - h_rel, unit="GPa", marginal=0.5,
                    note=f"rigid races would see {h_rig:.1f} GPa in a 2000 g drop (brinelling): the sprung races are needed",
                    label="CALCULATION (Hertz; moduli ASSUMPTION)"))
    ld = nibsum["leads"]["options"]["revK_C17200_0.100"]
    out.append(_chk("N16", "wire fatigue (Goodman SF at Kt 1.8) as coil leads", ld["wire_stage"]["goodman_SF"],
                    ">= 1.5", ld["wire_stage"]["goodman_SF"] / 1.5 - 1.0, unit="x", marginal=0.25,
                    label="CALCULATION (bnib/flexure.wire_stage, C17200 AMF-19 x 0.85)"))
    wm = [r for r in nibsum.get("wire_mc", {}).get("rows", []) if r["material"] == "C17200_TH04" and abs(r["d_mm"] - 0.10) < 1e-6
          and r["preload_max_N"] <= 0.05 + 1e-9]
    if wm:
        p5 = wm[0]["goodman_SF_p1_p5_p50"][1]
        out.append(_chk("N16b", "wire fatigue over study B's tolerance draws (5th percentile), axially soft anchor",
                        p5, ">= 1.0 (no failure in 95 % of builds); 1.5 wanted", p5 - 1.0, unit="x", marginal=0.5,
                        note="with study B's 0-0.3 N assembly preload the 5th percentile is "
                             f"{[r for r in nibsum['wire_mc']['rows'] if r['material'] == 'C17200_TH04' and abs(r['d_mm'] - 0.10) < 1e-6 and r['preload_max_N'] > 0.1][0]['goodman_SF_p1_p5_p50'][1]:.2f}"
                             " (C17200's fatigue strength is below Ti-6Al-4V's); 0.08 mm wire: 1.50",
                        label="CALCULATION (bnib/flexure Monte Carlo; tolerances ASSUMPTION; EXP-B25)"))
    out.append(_chk("N17", "study B's Ti-6Al-4V wires as coil leads (for the record)",
                    nibsum["leads"]["options"]["studyB_Ti64_0.128"]["I_max_3V3_A"], ">= 1.0 A at 3.3 V",
                    nibsum["leads"]["options"]["studyB_Ti64_0.128"]["I_max_3V3_A"] - 1.0, unit="A",
                    note="Ti-6Al-4V (170 uOhm cm) cannot carry the coil current; Rev K uses C17200"))
    md = nibsum["modes"]["by_restraint"]["revK_ball_guide"]
    bw_min = val(PR.NIB["servo_bw_min_Hz"])
    out.append(_chk("N18", "DEC-050 2.5 x rule: servo bandwidth allowed (worst case, ball stuck or free)",
                    md["servo_bw_max_worst_Hz"], f">= {bw_min:g} Hz (REQ-BNIB-006)", md["servo_bw_max_worst_Hz"] / bw_min - 1.0,
                    unit="x", marginal=0.25, label="CALCULATION (bnib/flexure.loaded_modes)"))
    mdB = nibsum["modes"]["by_restraint"]["studyB_wires"]
    out.append(_chk("N19", "the same for study B's wire suspension (for the record)", mdB["servo_bw_max_worst_Hz"],
                    f">= {bw_min:g} Hz", mdB["servo_bw_max_worst_Hz"] / bw_min - 1.0, unit="x", marginal=0.25))
    k_w = ld["wire_stage"]["k_lat_N_m"]
    m_mv = nibsum["m_move_g"] * 1e-3
    sag = m_mv * 9.81 * math.cos(math.radians(35.0)) / k_w * 1e3
    out.append(_chk("N22", "unpowered rest position vs REQ-BNIB-011 (centred within 0.1 mm)", sag, "<= 0.1 mm",
                    0.1 - sag, note=f"gravity across the pen (35 deg) on {k_w:.2f} N/m sags the carrier {sag:.0f} mm: it rests "
                                     "on its soft stop, 1.26 mm off centre, and the pen still writes (study B's 3.8 N/m: "
                                     f"{m_mv * 9.81 * math.cos(math.radians(35.0)) / 3.79 * 1e3:.0f} mm)",
                    label="CALCULATION (statics)"))
    # head
    hw = val(LAY["head_walls"])
    out.append(_chk("H1", "swept face and bracket vs the roll cage's bore", hw["cage_id"] / 2 - hd["swept_r_max_mm"],
                    ">= 0.3 running", hw["cage_id"] / 2 - hd["swept_r_max_mm"] - run))
    out.append(_chk("H2", "follower travel needed vs one SQL-RV-1.8", hd["positioner_travel_needed_mm"], "<= 6.0 (AMF-15)",
                    val(PR.HEAD["pos_travel_mm"]) - hd["positioner_travel_needed_mm"], marginal=1.0))
    ld_ = hd["loads"]
    for k, cid in (("tilt", "H3"), ("roll", "H4"), ("follower", "H5")):
        out.append(_chk(cid, f"{k} positioner force margin (stall 0.30 N)", ld_[k]["force_N"], ">= 1.5 x",
                        ld_[k]["margin_x"] / 1.5 - 1.0, unit="x", marginal=0.1,
                        label="CALCULATION (statics; stall MANUFACTURER AMF-15)",
                        note="re-set the roll only near nib centre (the peak needs the nib at its stop)" if k == "roll" else ""))
    out.append(_chk("H6", "touchdown travel of the refill (float gap / sin 35 deg) vs REQ-BNIB-002",
                    hd["ink_tail"]["refill_travel_at_touchdown_mm"]["35"], "<= 0.25 mm",
                    0.25 - hd["ink_tail"]["refill_travel_at_touchdown_mm"]["35"],
                    note="the float must span the +-2.5 deg tilt wobble (0.46 mm); REQ-BNIB-002 allows 0.04 mm"))
    out.append(_chk("H7", "face-parallelism residual (mean, 95th pct) vs REQ-BNIB-001", cf_stack["ratio_to_Fs_cot"]["p95"],
                    "mean <= 0.10, p95 <= 0.25", min(0.10 - cf_stack["ratio_to_Fs_cot"]["mean"], 0.25 - cf_stack["ratio_to_Fs_cot"]["p95"]),
                    unit="x", marginal=0.02, label="CALCULATION (Monte Carlo; contributors ASSUMPTION)"))
    out.append(_chk("H8", "cage vs carriage vs shell (radial running gaps)",
                    min((hw["carriage_id"] - hw["cage_od"]) / 2, (22.0 - hw["carriage_od"]) / 2), ">= 0.3 running",
                    min((hw["carriage_id"] - hw["cage_od"]) / 2, (22.0 - hw["carriage_od"]) / 2) - run))
    out.append(_chk("H9", "cage front vs the anchor ring (axial, the carriage's lift stroke included)",
                    c["head_cage"]["z0"] - P["anchor_ring_z"][1] - 0.0, ">= 0.3 running",
                    c["head_cage"]["z0"] - P["anchor_ring_z"][1] - run,
                    note="the lift moves the head backward (away from the ring)"))
    out.append(_chk("H10", "cell vs the bulkhead (axial)", c["battery"]["z0"] - c["bulkhead"]["z1"], ">= 0.2 fixed",
                    c["battery"]["z0"] - c["bulkhead"]["z1"] - fix))
    # electronics, cell, envelope
    bcorner = math.hypot(bd["x_mm"] + bd["t_mm"] / 2, bd["w_mm"] / 2)
    out.append(_chk("E1", "board corners inside the bore", 11.0 - bcorner, ">= 0.2 fixed", 11.0 - bcorner - fix))
    bt = val(LAY["battery"])
    out.append(_chk("E2", "cell inside the bore (axis 3 mm up)", 11.0 - (bt["x_mm"] + bt["d_mm"] / 2), ">= 0.2 fixed",
                    11.0 - (bt["x_mm"] + bt["d_mm"] / 2) - fix))
    lr = c["lra"]
    lr_corner = math.hypot(abs(lr["offset"][0]) + lr["size"][0] / 2, lr["size"][1] / 2)
    out.append(_chk("E3", "LRA corners inside the bore", 11.0 - lr_corner, ">= 0.2 fixed", 11.0 - lr_corner - fix))
    gap_lb = (bt["x_mm"] - bt["d_mm"] / 2) - (lr["offset"][0] + lr["size"][0] / 2)
    out.append(_chk("E4", "LRA vs the cell", gap_lb, ">= 0.2 fixed", gap_lb - fix))
    hf = nibsum["hall"]
    out.append(_chk("E5", "field at the nib Hall within the A1 range (pole magnets + position magnet)",
                    hf["position_magnet_max_component_mT"] + float(np.max(np.abs(hf["pole_magnets_mT"]))),
                    "< 100 mT (TMAG5170-A1)", 100.0 - hf["position_magnet_max_component_mT"]
                    - float(np.max(np.abs(hf["pole_magnets_mT"]))), unit="mT", marginal=10.0,
                    label="CALCULATION (magpylib, free space: an upper bound for the pole magnets)"))
    out.append(_chk("E6", "nib Hall noise at the tip (1 kHz bandwidth)", hf["tip_noise_um_rms_1kHz"], "<= 5 um rms",
                    5.0 - hf["tip_noise_um_rms_1kHz"], unit="um", marginal=1.0,
                    label="CALCULATION (magpylib gradient; noise MANUFACTURER OPT-44)"))
    L = P["length"]
    out.append(_chk("L1", "pen length", L, "<= 175 mm", val(PR.ENVELOPE["length_mm"]) - L, marginal=5.0))
    if hand:
        out.append(_chk("L2", "grip 24 mm under every finger pad", hand["pads"][0]["d_front_edge_mm"], "= 24 mm (DEC-029)",
                        0.0 if hand["all_pads_on_full_grip"] else -1.0, marginal=0.0))
        out.append(_chk("L3", "handle underside at the front finger pad, 35 deg (vs an ordinary 9 mm pen)",
                        hand["pads"][0]["underside_above_paper_35deg_mm"], ">= ordinary pen",
                        hand["front_pad_vs_ordinary_mm"], marginal=0.0,
                        note="the 24 mm grip sits 3.3 mm closer to the paper than an ordinary pen's at 35 deg: a feel "
                             "question for EXP-K03-type tests", label="CALCULATION (geometry; hand model ASSUMPTION)"))
    if heel and fc_h:
        hs = heel["shafts"]
        out.append(_chk("V1", "heel variant: page sensor roll tolerance (window beside the pod)", fc_h["roll_tolerance_deg"],
                        ">= 20 deg", fc_h["roll_tolerance_deg"] - 20.0, unit="deg", marginal=2.0,
                        note="the window must leave the bottom of the ring for the pod"))
        out.append(_chk("V2", "heel variant: inner shafts' skin in the cone", hs["skin_outside_inner_liners_mm"], ">= 0.3",
                        hs["skin_outside_inner_liners_mm"] - 0.3))
        out.append(_chk("V3", "heel variant: outer shafts' liners vs the roll cage", (10.9 - 0.5) - 10.1, ">= 0.3 running",
                        (10.9 - 0.5) - 10.1 - run))
        out.append(_chk("V4", "heel variant: outer shafts vs the back plate and keeper (need 1.2 mm notches)",
                        (10.9 - 0.5) - 10.7, ">= 0.2 fixed", (10.9 - 0.5) - 10.7 - fix,
                        note="notch both plates at the bottom (a few % of the iron; EXP-B23 checks Km)"))
        bx = bt["x_mm"] - bt["d_mm"] / 2
        dm = math.hypot(bt["x_mm"] + 7.0, 3.2) - bt["d_mm"] / 2 - 3.0
        out.append(_chk("V5", "heel variant: motors vs the cell", dm, ">= 0.2 fixed", dm - fix))
        out.append(_chk("V6", "heel variant: motors inside the bore", 11.0 - (math.hypot(7.0, 3.2) + 3.0), ">= 0.2 fixed",
                        11.0 - (math.hypot(7.0, 3.2) + 3.0) - fix))
        lra = c["lra"]
        dml = (heel["motor_z"][0] - 2.2) - lra["z1"]
        out.append(_chk("V7", "heel variant: rear transfer vs the LRA (axial)", dml, ">= 0.2 fixed", dml - fix))
    return out


# ------------------------------------------------------------------------------------------------ build
def build(fc: Dict, fc_h: Dict, hd: Dict, coil: Dict, nibsum: Dict, cf_stack: Dict, hand: Dict) -> Dict:
    base = base_components(fc, hd, coil)
    heel = heel_components(fc_h, base)
    checks = fit_checks(fc, hd, coil, base, nibsum, cf_stack, heel, fc_h, hand)
    n_fail = sum(1 for x in checks if x["status"] == "fail")
    n_marg = sum(1 for x in checks if x["status"] == "marginal")
    P = base["positions"]
    return {"units": "mm, g", "axis": "z along the pen axis from the ball tip at 50 deg (nib centred) toward the back; x in "
                                       "the tilt plane, positive away from the paper; y lateral",
            "skid_contact_radius": fc["R_s_mm"], "ball_protrusion_mm": fc["z_ring_mm"],
            "protrusion_by_tilt_mm": fc["protrusion_mm"], "handle_od": val(PR.ENVELOPE["handle_od_held_mm"]),
            "length": P["length"], "grip_zone": list(val(PR.ENVELOPE["grip_zone_mm"])),
            "hand": {"finger_pads_z": list(val(PR.ENVELOPE["finger_pads_z_mm"])), "web_z": val(PR.ENVELOPE["web_z_mm"])},
            "tip_travel_mm": val(PR.B1["travel_mm"]), "stop_mm": val(PR.B1["stop_mm"]),
            "refill_slide_mm": fc["refill_slide_total_mm"], "positions": P,
            "components": base["components"], "heel_variant": {"components": heel["components"], "shafts": heel["shafts"],
                                                                "R_s_mm": fc_h["R_s_mm"], "R_d_mm": fc_h["R_d_mm"],
                                                                "motor_z": heel["motor_z"]},
            "fit_checks": checks,
            "fit_summary": {"n": len(checks), "pass": len(checks) - n_fail - n_marg, "marginal": n_marg, "fail": n_fail,
                            "fails": [x["id"] for x in checks if x["status"] == "fail"],
                            "marginals": [x["id"] for x in checks if x["status"] == "marginal"]},
            "tables": {"layout": PR.table(LAY)},
            "label": "PROPOSED DESIGN (layout); fit checks CALCULATION; nothing built or measured"}
