"""Board geometry (single source for results/board/layout.json and mechanics/cad/guidance_board.py).

Board frame: x right, y away from the writer, z up; origin at the board's
front-left corner on the writing surface (top of the cover glass, z = 0).
All dimensions in mm.  PROPOSED DESIGN: catalogue parts are envelopes of the
cited parts; custom parts are concept geometry; nothing is built.
"""
from __future__ import annotations

from . import params as P

G = {
    "board": (300.0, 420.0),           # outer x, y
    "glass_y": 360.0,                  # glass covers y 0..360; back housing 360..420
    "glass_t": P.STACK["glass_mm"].value,
    "wall_t": 3.0,
    "base_top": -42.0, "base_t": 3.0,
    "paper": (45.0, 38.0, *P.A4_MM),   # x0, y0, w, h (A4 portrait)
    "yrail_x": (10.0, 290.0), "yrail": (12.0, 8.0), "yblock": (27.0, 45.4, 5.0),   # MGN12: rail w,h; block w,l,(h above rail)
    "beam": (20.0, 10.0),              # gantry beam width (y) x height
    "xrail": (9.0, 6.5), "xblock": (20.0, 39.9, 3.5),                              # MGN9
    "carriage_plate": (50.0, 60.0, 3.0),
    "cantilever_dy": -25.0,            # head axis relative to the X rail (toward the writer)
    "head": (P.HEAD["head_d_mm"].value, P.HEAD["head_h_mm"].value),
    "head_top_z": -(P.STACK["glass_mm"].value + P.STACK["clearance_mm"].value),
    "zlift": P.HEAD["zlift_travel_mm"].value,
    "ring": (52.0, 20.0, 1.0),         # Hall ring PCB OD, ID, thickness
    "servo": (20.0, 34.0, 26.0),       # XL330 envelope
    "motor": (42.0, 42.0, 48.0),
    "motor_xy": ((24.0, 396.0), (276.0, 396.0)),
    "idler_xy": ((24.0, 8.0), (276.0, 8.0)),
    "travel": {"x": [25.0, 275.0], "y": [8.0, 347.0]},   # head axis; the pen magnet sits 16.5 mm toward the writer from the ball
    "housing_top": 12.0,
}


def base_z0():
    return G["base_top"] - G["base_t"]


def z_levels():
    b = G["base_top"]
    yr_top = b + G["yrail"][1]
    yb_top = b + 13.0                  # MGN12H assembly height H = 13 (AMF-94)
    beam_top = yb_top + G["beam"][1]
    xb_top = beam_top + 10.0           # MGN9H assembly height H = 10 (AMF-94)
    plate_top = xb_top + G["carriage_plate"][2]
    return {"base_top": b, "yrail_top": yr_top, "yblock_top": yb_top, "beam_top": beam_top,
            "xblock_top": xb_top, "plate_top": plate_top, "head_top": G["head_top_z"]}


def travel():
    return {"x": list(G["travel"]["x"]), "y": list(G["travel"]["y"])}


def components(head_xy=None, zlift_mm: float = 0.0):
    """Components in the board frame.  head_xy: head axis position (default: page centre)."""
    x0, y0, w, h = G["paper"]
    hx, hy = head_xy if head_xy is not None else (x0 + w / 2, y0 + h / 2)
    Z = z_levels()
    bx, by = G["board"]
    gy = G["glass_y"]
    beam_y = hy - G["cantilever_dy"]
    hd, hh = G["head"]
    htop = G["head_top_z"] - zlift_mm
    comps = []

    def box(id_, label, group, x0_, y0_, z0_, sx, sy, sz, moves="board", function="", part="custom", ledger=""):
        comps.append({"id": id_, "label": label, "group": group, "shape": "box", "x0": round(x0_, 2), "y0": round(y0_, 2),
                      "z0": round(z0_, 2), "size": [round(sx, 2), round(sy, 2), round(sz, 2)], "moves_with": moves,
                      "function": function, "part": part, "ledger": ledger})

    def cyl(id_, label, group, cx, cy, cz, d, hgt, moves="board", function="", part="custom", ledger="", shape="cylinder", d_in=None):
        c = {"id": id_, "label": label, "group": group, "shape": shape, "center": [round(cx, 2), round(cy, 2), round(cz, 2)],
             "d": round(d, 2), "h": round(hgt, 2), "moves_with": moves, "function": function, "part": part, "ledger": ledger}
        if d_in is not None:
            c["d_in"] = d_in
        comps.append(c)

    # --- structure
    box("base_plate", "Base plate", "structure", 0, 0, base_z0(), bx, by, G["base_t"],
        function="Stiff aluminium floor of the board; everything mounts to it.", part="custom: aluminium 5052/6061, 3 mm")
    box("wall_left", "Left wall", "structure", 0, 0, G["base_top"], G["wall_t"], gy, -G["base_top"],
        function="Side wall; carries the glass edge.", part="custom: aluminium sheet 3 mm")
    box("wall_right", "Right wall", "structure", bx - G["wall_t"], 0, G["base_top"], G["wall_t"], gy, -G["base_top"],
        function="Side wall; carries the glass edge.", part="custom: aluminium sheet 3 mm")
    box("wall_front", "Front wall", "structure", 0, 0, G["base_top"], bx, G["wall_t"], -G["base_top"],
        function="Front wall under the writer's forearm.", part="custom: aluminium sheet 3 mm")
    box("glass", "Glass writing surface", "structure", 0, 0, -G["glass_t"], bx, gy, G["glass_t"],
        function="2 mm strengthened glass: flat, hard writing surface that lets the magnetic field through.",
        part="custom: chemically strengthened glass 2.0 mm, anti-shatter film")
    box("paper", "Paper (A4)", "structure", x0, y0, 0.0, w, h, P.STACK["paper_mm"].value,
        function="An ordinary sheet; practice sheets are printed with corner marks and pushed against the paper stop.", part="A4 paper")
    box("paper_stop", "Paper stop", "structure", x0 - 4, y0 - 4, 0.0, w + 4, 4, 2.0,
        function="L-shaped stop that places the sheet where the app expects it.", part="custom: PA12 print")
    box("housing", "Back housing", "structure", 0, gy, base_z0(), bx, by - gy, G["housing_top"] - base_z0(),
        function="Covers the motors and the electronics; also a pen ledge.", part="custom: PA12 or aluminium")
    # --- stage
    for i, xr in enumerate(G["yrail_x"]):
        box(f"yrail_{i}", "Y rail (MGN12)", "mechanism", xr - G["yrail"][0] / 2, 5.0, G["base_top"], G["yrail"][0], 405.0, G["yrail"][1],
            function="Steel guide for the gantry (front-back).", part="HIWIN MGN12 rail", ledger="AMF-94")
        box(f"yblock_{i}", "Y block (MGN12H)", "mechanism", xr - G["yblock"][0] / 2, beam_y - G["yblock"][1] / 2, Z["yrail_top"],
            G["yblock"][0], G["yblock"][1], Z["yblock_top"] - Z["yrail_top"], moves="carriage",
            function="Carriage block of the gantry.", part="HIWIN MGN12H", ledger="AMF-94")
    box("beam", "Gantry beam", "mechanism", G["yrail_x"][0], beam_y - G["beam"][0] / 2, Z["yblock_top"],
        G["yrail_x"][1] - G["yrail_x"][0], G["beam"][0], G["beam"][1], moves="carriage",
        function="Aluminium beam that moves front-back and carries the X rail.", part="custom: aluminium 20 x 10 tube")
    box("xrail", "X rail (MGN9)", "mechanism", G["yrail_x"][0] + 10, beam_y - G["xrail"][0] / 2, Z["beam_top"],
        G["yrail_x"][1] - G["yrail_x"][0] - 20, G["xrail"][0], G["xrail"][1], moves="carriage",
        function="Steel guide for the carriage (left-right).", part="HIWIN MGN9 rail", ledger="AMF-94")
    box("xblock", "X block (MGN9H)", "mechanism", hx - G["xblock"][1] / 2, beam_y - G["xblock"][0] / 2, Z["beam_top"] + G["xrail"][1],
        G["xblock"][1], G["xblock"][0], Z["xblock_top"] - Z["beam_top"] - G["xrail"][1], moves="carriage",
        function="Carriage block.", part="HIWIN MGN9H", ledger="AMF-94")
    cp = G["carriage_plate"]
    box("carriage_plate", "Carriage plate and cantilever", "mechanism", hx - cp[0] / 2, hy - 15.0, Z["xblock_top"],
        cp[0], beam_y - hy + 25.0, cp[2], moves="carriage",
        function="Aluminium plate on the X block; its arm reaches 25 mm toward the writer to hold the head beside the rail.",
        part="custom: aluminium 3 mm")
    for i, (mx, my) in enumerate(G["motor_xy"]):
        m = G["motor"]
        box(f"motor_{'AB'[i]}", f"Stepper motor {'AB'[i]}", "actuator", mx - m[0] / 2, my - m[1] / 2, G["base_top"], m[0], m[1], m[2],
            function="Drives one CoreXY belt; together they move the head anywhere under the page.",
            part="StepperOnline 17HS19-2004S1 (NEMA 17)", ledger="AMF-92")
    for i, (ix, iy) in enumerate(G["idler_xy"]):
        cyl(f"idler_{i}", "Belt idler", "mechanism", ix, iy, Z["yblock_top"] - 6, 16.0, 9.0,
            function="Turns the belt at the front corners.", part="GT2 20T idler (to select)")
    box("belt_left", "Belt (left run)", "mechanism", 22.0, 8.0, Z["yblock_top"] - 8, 2.0, 388.0, 6.0,
        function="GT2 6 mm belt of motor A.", part="GT2 6 mm belt (to select)")
    box("belt_right", "Belt (right run)", "mechanism", 276.0, 8.0, Z["yblock_top"] - 8, 2.0, 388.0, 6.0,
        function="GT2 6 mm belt of motor B.", part="GT2 6 mm belt (to select)")
    # --- head (moves with the carriage)
    cyl("head_magnet", "Head magnet", "magnet", hx, hy, htop - hh / 2, hd, hh, moves="carriage",
        function="Permanent magnet under the glass. Where it sits relative to the pen's magnet sets the pull on the pen: direction and strength.",
        part="K&J D88-N52, 12.7 x 12.7 mm, N52", ledger="AMF-90")
    cyl("head_cup", "Magnet cup on the Z parallelogram", "mechanism", hx, hy, htop - hh - 3.0, 16.0, 6.0, moves="carriage",
        function="Aluminium cup; a parallelogram keeps the magnet upright while it is lowered by up to 12 mm.",
        part="custom: aluminium cup, PA12/POM links")
    ro, ri, rt = G["ring"]
    cyl("hall_ring", "Hall sensor ring", "sensor", hx, hy, -G["glass_t"] - 0.3 - rt / 2, ro, rt, moves="carriage",
        function="Eight 3-axis Hall sensors around the head: they measure where the pen's magnet is, 1000 times a second.",
        part="custom PCB with 8 x TI TMAG5170A2", ledger="AMF-95", shape="tube", d_in=ri)
    sv = G["servo"]
    # hangs under the carriage plate beside the magnet: 34 mm along x, 20 along y, 26 high
    box("zservo", "Z-lift servo", "actuator", hx + 9.0, hy - sv[0] / 2, Z["xblock_top"] - sv[2], sv[1], sv[0], sv[2], moves="carriage",
        function="Raises and lowers the head magnet: the guidance level, and off.",
        part="ROBOTIS XL330-M288-T", ledger="AMF-96")
    # --- electronics and power
    box("main_pcb", "Main board", "electronics", 100.0, 372.0, G["base_top"] + 4, 100.0, 40.0, 1.6,
        function="nRF54L15 (Bluetooth to the pen and the phone), two TMC2209 motor drivers, the safety monitor.",
        part="custom PCB: nRF54L15 + 2 x TMC2209", ledger="AMF-44/AMF-93")
    box("dc_jack", "24 V input and power switch", "power", 140.0, 416.0, -20.0, 20.0, 4.0, 12.0,
        function="Input from the external 24 V adaptor; power switch.", part="MEAN WELL GST60A24-P1J (external)", ledger="AMF-97")
    box("stop_button", "Stop button", "electronics", 230.0, 375.0, G["housing_top"], 16.0, 16.0, 4.0,
        function="Stops the motors and lowers the head at once (hardware cut of the driver enable lines).", part="momentary switch (to select)")
    box("arm_rest", "Arm-rest wedge (optional)", "structure", 0, -80.0, base_z0(), bx, 80.0, -base_z0(),
        function="The writing surface is about 45 mm above the desk; the wedge supports the forearm.", part="custom: PU foam in a PA12 shell")
    return comps


def pen_magnet_info():
    Pn = P.PEN
    return {"part": "K&J D42-N52 NdFeB disc", "d": Pn["pen_magnet_d_mm"].value, "h": Pn["pen_magnet_h_mm"].value,
            "mass_g": Pn["pen_magnet_mass_g"].value, "ledger": "AMF-91",
            "location": "keel under the FIXED front sleeve of the Rev H pen (moves with the handle, not the nose)",
            "magnetisation": "along the pen axis, north toward the pen's rear",
            "pen_frame_mm": {"along_axis_from_ball": Pn["pen_magnet_axial_mm"].value,
                             "off_axis_toward_paper": Pn["pen_magnet_radial_mm"].value,
                             "axis": "Rev H frame: z along the pen axis from the ball"},
            "board_frame_at_50deg_mm": {"height_above_paper": Pn["pen_magnet_height_mm"].value,
                                        "behind_ball_along_azimuth": Pn["pen_magnet_behind_ball_mm"].value},
            "why_not_on_the_nose": "the nose actuator carries only 0.21 N continuously on a 12 N/m suspension (results/revH/tip_params.json)",
            "label": "MFR (magnet) + ASSUMPTION/CALC (placement, to confirm in Rev H CAD)"}


def layout_json(meta: dict) -> dict:
    return {"meta": meta, "units": "mm",
            "axis": "board frame: x right, y away from the writer, z up; origin at the board's front-left corner on the writing surface",
            "board_outer_mm": list(G["board"]) + [G["housing_top"] - base_z0()],
            "writing_surface_z": 0.0, "paper_area": {"x0": G["paper"][0], "y0": G["paper"][1], "w": G["paper"][2], "h": G["paper"][3]},
            "carriage_travel": travel(),
            "head_z_travel": {"top_face_z": [G["head_top_z"] - G["zlift"], G["head_top_z"]],
                              "note": "top = working (gap 2.7 mm to the paper top), bottom = retracted/off"},
            "components": components(),
            "pen_magnet": pen_magnet_info()}
