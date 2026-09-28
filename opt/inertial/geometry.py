"""Rev H component layout (single source for the CAD script, results/revH/layout.json and the replay's geometry).

Units mm; z along the pen axis from the ball tip (z = 0) toward the back; x, y transverse (x in the tilt plane, toward
the paper side; y lateral).  Every dimension is a PROPOSED DESIGN (ASSUMPTION) derived from the design variables in
opt/inertial/revh.RevH (adjoint-optimised actuator) and catalogue parts (ledger ids).  Masses are CALC.
Groups (for the 3-D explainer): structure | grip | moving_nose | refill | actuator | mechanism | sensor | electronics |
power | haptic | inertial.  moves_with: nose | handle | inertial_mass.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from . import catalog as CT
from .revh import RevH, masses, protrusion_centre


def comp(id_, label, group, shape, z0, z1, moves="handle", d0=None, d1=None, d_in=None, size=None, offset=None,
         optional=False, function="", part="custom", ledger="", mass_g=None):
    c = {"id": id_, "label": label, "group": group, "shape": shape, "z0": round(z0, 2), "z1": round(z1, 2), "moves_with": moves,
         "optional": optional, "function": function, "part": part, "ledger": ledger}
    if d0 is not None:
        c["d0"] = round(d0, 2)
        c["d1"] = round(d1 if d1 is not None else d0, 2)
    if d_in is not None:
        c["d_in"] = round(d_in, 2)
    if size is not None:
        c["size"] = [round(v, 2) for v in size]
    if offset is not None:
        c["offset"] = [round(v, 2) for v in offset]
    if mass_g is not None:
        c["mass_g"] = round(mass_g, 2)
    return c


def layout(d: Optional[RevH] = None, addon: Optional[Dict] = None, theta_deg=50.0) -> Dict:
    d = d or RevH()
    zp, za = d.z_p * 1e3, d.z_a * 1e3
    X = d.travel * 1e3
    lam = d.lever
    s_mag = X / lam                                       # magnet stroke (mm)
    skid_r = d.skid_r * 1e3
    prot = protrusion_centre(theta_deg, r_ring=d.skid_r) * 1e3        # ball centre ahead of the skid-ring plane
    z_skid = prot                                          # skid-ring contact plane
    # front opening: the carrier's swing at its front end (z 8 mm) plus clearance
    z_cf = 8.0
    swing_front = X * (zp - z_cf) / zp
    open_d = 7.0 + 2 * swing_front + 1.0
    L = d.length * 1e3
    D = d.handle_od * 1e3
    cell = CT.CELLS[d.cell]
    mag_w, mag_l, mag_t, coil_t = d.mag_w * 1e3, d.mag_l * 1e3, d.mag_t * 1e3, d.coil_t * 1e3
    hub = 5.0
    gap = 0.5 + s_mag                                       # magnet-coil gap takes the other axis's stroke
    r_mag = hub / 2 + mag_t / 2
    r_coil = hub / 2 + mag_t + gap + coil_t / 2
    z_cell0 = 101.0
    comps: List[Dict] = []
    A = comps.append
    # ---------------- refill and moving nose
    A(comp("ball", "Ball tip", "refill", "cone", 0.0, 3.0, "nose", 0.7, 2.35, function="The point that touches the paper and writes.",
           part="ISO 12757-2 D1 mini refill", ledger="DEC-004"))
    A(comp("refill", "Ink refill (D1 mini)", "refill", "cylinder", 3.0, 67.0, "nose", 2.35, 2.35,
           function="Standard replaceable refill; it slides along its axis on a soft constant-force spring so the ball stays on the paper while the nose tilts.",
           part="ISO 12757-2 D1 mini refill", ledger="DEC-004", mass_g=0.84))
    A(comp("refill_spring", "Constant-force refill spring", "mechanism", "cylinder", 67.0, 75.0, "nose", 2.4, 2.4,
           function="Presses the refill onto the paper with about 0.15 N over 6 mm of axial travel (tilt and correction changes).",
           part="custom (music-wire, long soft spring)", ledger=""))
    A(comp("carrier", "Moving nose (refill carrier)", "moving_nose", "tube", z_cf, zp - 1.5, "nose", 7.0, 7.0, 6.0,
           function="Thin titanium tube that holds the refill; it tilts on the gimbal so the tip moves up to about 3 mm against the handle.",
           part="custom (Ti-6Al-4V tube 7/6 mm)", ledger="AMF-21"))
    A(comp("carrier_nozzle", "Nose nozzle", "moving_nose", "cone", 3.0, z_cf, "nose", 3.6, 7.0,
           function="Front of the moving nose; guides the refill tip.", part="custom (PEEK)", ledger="AMF-24"))
    A(comp("arm", "Rear arm", "moving_nose", "cylinder", zp + 1.5, za - mag_l / 2, "nose", 5.0, 5.0,
           function="Carries the magnets behind the gimbal: the tip moves the opposite way, 1/lever times the magnet motion.",
           part="custom (aluminium 6061)", ledger=""))
    A(comp("magnet_hub", "Magnet hub", "moving_nose", "box", za - mag_l / 2, za + mag_l / 2, "nose", size=[hub, hub, mag_l],
           function="Square hub on the arm carrying four magnets.", part="custom (soft iron)", ledger=""))
    for k, (ox, oy, sx, sy) in enumerate(((r_mag, 0, mag_t, mag_w), (-r_mag, 0, mag_t, mag_w), (0, r_mag, mag_w, mag_t), (0, -r_mag, mag_w, mag_t))):
        ax = "x" if k < 2 else "y"
        A(comp(f"magnet_{ax}{'+' if k % 2 == 0 else '-'}", f"Actuator magnet ({'y' if ax == 'x' else 'x'}-force)", "actuator", "box",
               za - mag_l / 2, za + mag_l / 2, "nose", size=[sx, sy, mag_l], offset=[ox, oy],
               function="NdFeB magnet on the moving arm; the coil facing it pushes it sideways (shear), tilting the nose.",
               part=f"NdFeB N45 block {mag_w:.1f} x {mag_l:.1f} x {mag_t:.1f} mm", ledger="AMF-28"))
    A(comp("hall_magnet", "Position magnet", "sensor", "cylinder", za + mag_l / 2 + 0.5, za + mag_l / 2 + 1.5, "nose", 1.0, 1.0,
           function="Tiny magnet at the end of the arm read by the 3-D Hall sensor.", part="supermagnete S-01-01-N", ledger="AMF-72"))
    # ---------------- handle (fixed)
    A(comp("skid_ring", "Skid ring (C-shaped heel)", "structure", "tube", z_skid - 1.5, z_skid + 0.5, "handle", open_d + 3.0, open_d + 3.0,
           open_d, function="Rests on the paper and carries the writing force; the ball moves inside its opening. Open at the front so the ink stays visible.",
           part="custom (PTFE-coated POM, contact radius %.1f mm)" % skid_r, ledger=""))
    A(comp("front_sleeve", "Front sleeve (fixed grip)", "grip", "tube", z_skid + 0.5, 50.0, "handle", 16.0, D, open_d,
           function="Where the thumb, index and middle finger rest. It does not move; the nose moves inside it.",
           part="PEEK core + TPE overmould", ledger="AMF-24"))
    A(comp("gimbal", "Flexure gimbal (2-axis)", "mechanism", "tube", zp - 1.5, zp + 1.5, "handle", 17.0, 17.0, 5.5,
           function="Laser-cut spring-steel cross flexures: the nose tilts in two directions with no friction or backlash; stiff along the pen.",
           part="custom (301 full-hard or 17-7PH 0.1 mm, laser-cut)", ledger="AMF-20"))
    z_ring0, z_ring1 = za - mag_l / 2 - s_mag - 1.5, za + mag_l / 2 + s_mag + 1.5
    A(comp("shell", "Handle shell", "structure", "tube", 50.0, L, "handle", D, D, D - 2.0,
           function="The body you hold: 22 mm thick, easier to grip than a pencil.", part="PEEK or glass-filled nylon, 1 mm wall", ledger="AMF-24"))
    A(comp("back_ring", "Soft-iron ring (flux return)", "actuator", "tube", z_ring0, z_ring1, "handle", D, D, D - 2.0,
           function="Section of the shell over the coils made of soft iron: it closes the magnets' flux through the coils.",
           part="custom (soft iron / 1010 steel, nickel plated)", ledger=""))
    for k, (ox, oy, sx, sy) in enumerate(((r_coil, 0, coil_t, mag_w + 2 * s_mag + 1.0), (-r_coil, 0, coil_t, mag_w + 2 * s_mag + 1.0),
                                           (0, r_coil, mag_w + 2 * s_mag + 1.0, coil_t), (0, -r_coil, mag_w + 2 * s_mag + 1.0, coil_t))):
        ax = "x" if k < 2 else "y"
        A(comp(f"coil_{ax}{'+' if k % 2 == 0 else '-'}", f"Flat voice coil ({'y' if ax == 'x' else 'x'}-force)", "actuator", "box",
               za - mag_l / 2 - s_mag - 0.5, za + mag_l / 2 + s_mag + 0.5, "handle", size=[sx, sy, mag_l + 2 * s_mag + 1.0],
               offset=[ox, oy], function="Fixed flat coil with a soft-iron back plate; current through it pushes the magnet sideways.",
               part="custom (self-bonding 0.1 mm magnet wire, IEC class 155)", ledger="AMF-29/AMF-30"))
    A(comp("hall3d", "3-D Hall position sensor", "sensor", "box", za + mag_l / 2 + 2.5, za + mag_l / 2 + 3.5, "handle", size=[2.9, 2.8, 1.0],
           function="Reads the nose position in x and y about 10 000 times a second for the position servo.",
           part="TI TMAG5273 (3-D Hall, I2C) or DRV5055 x2", ledger="OPT-45/OPT-46"))
    z_pcb0 = za + mag_l / 2 + s_mag + 2.0
    A(comp("pcb", "Control board", "electronics", "box", z_pcb0, z_cell0 - 2.0, "handle", size=[1.0, 15.0, z_cell0 - 2.0 - z_pcb0],
           function="nRF54L15-class MCU with Bluetooth, two coil drivers with current sensing, charger and the IMU. Runs the tremor tracker and the servo.",
           part="nRF54L15 + 2 x DRV8214 + charger", ledger="AMF-44/AMF-37"))
    A(comp("imu", "Motion sensor (IMU)", "sensor", "box", 90.0, 92.5, "handle", size=[2.5, 3.0, 0.83], offset=[1.0, 0.0],
           function="Accelerometer and gyroscope: measures the hand's shake about 2000 times a second (feeds the tracker).",
           part="ST LSM6DSV16X", ledger="OPT-37"))
    A(comp("battery", "Rechargeable cell", "power", "cylinder", z_cell0, z_cell0 + cell.L * 1e3, "handle", cell.d * 1e3, cell.d * 1e3,
           function=f"{cell.name}, {cell.mAh:.0f} mAh.", part=cell.name, ledger=cell.src))
    z_after = z_cell0 + cell.L * 1e3 + 1.0
    if addon:
        z_after = z_cell0 - 6.0 - 1.0          # the cue motor and the port move ahead of the cell (board end)
    A(comp("lra", "Vibration cue motor", "haptic", "cylinder", z_after, z_after + 3.0, "handle", 8.0, 8.0, optional=True,
           function="Gentle buzz cues (write bigger, slow down, check a word).", part="coin LRA 8 mm", ledger="AMF-45"))
    z_usb = z_after + 4.0 if not addon else z_cell0 + cell.L * 1e3 + 0.5
    A(comp("usb", "USB-C port and button", "electronics", "box", z_usb, z_usb + 3.5, "handle", size=[8.4, 2.6, 3.5],
           offset=[0.0, D / 2 - 2.0], function="Charging and on/off / mode button (side port so the rear cap stays free).",
           part="USB-C receptacle (mid-mount)", ledger=""))
    A(comp("rear_cap", "Rear cap", "structure", "cylinder", L - 3.0, L, "handle", D, D - 2.0, function="Closes the handle.",
           part="custom (PEEK)", ledger="AMF-24"))
    A(comp("optical", "Paper sensor (optional)", "sensor", "box", 14.0, 20.0, "handle", size=[5.0, 5.0, 6.0], offset=[-(open_d / 2 + 2.0), 0.0],
           optional=True, function="Optical sensor beside the nose that sees the paper: page position for capture and the tracker (1 kHz, 2 ms assumed).",
           part="to select (optical flow class)", ledger=""))
    if addon:
        z0 = addon["z0"]; z1 = addon["z1"]
        A(comp("rm_frame", "Inertial module frame", "inertial", "tube", z0, z1, "handle", addon["frame_d"], addon["frame_d"], addon["frame_d"] - 1.0,
               optional=True, function="Houses the moving tungsten mass, its coils and flexures.", part="custom (aluminium)", ledger=""))
        A(comp("rm_mass", "Tungsten reaction mass", "inertial", "cylinder", addon["mz0"], addon["mz1"], "inertial_mass", addon["mass_d"], addon["mass_d"],
               optional=True, function="A heavy slug pushed sideways by coils: its reaction steadies the whole pen against the shake.",
               part="Tungsten heavy alloy ASTM B777 class 3 (non-magnetic grade)", ledger="AMF-49", mass_g=addon["m_g"]))
        A(comp("rm_coils", "Reaction-mass coils", "inertial", "tube", addon["mz0"], addon["mz1"], "handle", addon["frame_d"] - 1.0,
               addon["frame_d"] - 1.0, addon["mass_d"] + 2 * addon["stroke"] + 1.0, optional=True,
               function="Four flat coils facing magnets on the slug (2 axes).", part="custom", ledger=""))
    ms = masses(d)
    geo = {"units": "mm", "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x, y transverse",
           "pivot_z": zp, "actuator_z": za, "tip_travel_mm": X, "magnet_stroke_mm": round(s_mag, 2), "lever_tip_per_magnet": round(lam, 3),
           "tilt_deg": theta_deg, "front_opening_d": round(open_d, 2), "skid_contact_radius": skid_r, "ball_protrusion_mm": round(prot, 2),
           "handle_od": D, "length": L, "grip_zone": {"z0": 20.0, "z1": 45.0},
           "hand": {"finger_pads_z": [d.z_f * 1e3 - 6.0, d.z_f * 1e3, d.z_f * 1e3 + 6.0], "web_z": d.z_w * 1e3},
           "mass_g": {k: round(v, 2) for k, v in ms.items()}, "components": comps}
    geo["fit_checks"] = fit_checks(d, geo)
    return geo


def fit_checks(d: RevH, g: Dict) -> Dict:
    """Geometric fit checks (CALC)."""
    D, L = g["handle_od"], g["length"]
    out = {}
    X = g["tip_travel_mm"]
    zp = g["pivot_z"]
    # the carrier (d 7) swings X (zp - z)/zp; the front sleeve bore at the carrier front must clear it
    sw = X * (zp - 8.0) / zp
    out["carrier_clears_front_opening_mm"] = round(g["front_opening_d"] / 2 - (3.5 + sw), 3)
    # the magnets + gap + coils fit inside the shell bore
    coil = [c for c in g["components"] if c["id"] == "coil_x+"][0]
    r_out = coil["offset"][0] + coil["size"][0] / 2
    out["coil_radius_margin_mm"] = round((D - 2.0) / 2 - r_out, 3)
    # magnet stroke within its coil (shear) and within the gap (other axis)
    out["magnet_gap_mm"] = round(0.5 + g["magnet_stroke_mm"], 3)
    cell = [c for c in g["components"] if c["id"] == "battery"][0]
    out["cell_radius_margin_mm"] = round((D - 2.0) / 2 - cell["d0"] / 2, 3)
    last = max(c["z1"] for c in g["components"] if not c.get("optional") or c["group"] == "inertial")
    out["length_margin_mm"] = round(L - last, 3)
    out["all_pass"] = all(v >= 0 for k, v in out.items() if k != "magnet_gap_mm")
    return out
