r"""The Rev J.1 layout (PROPOSED DESIGN): Rev J's layout (revj.packaging.build, read-only) with the round-3 changes,
in the same schema as results/revJ/layout.json, and its fit checks (revj.packaging.fit_checks re-run on the changed
layout, plus the checks the changes need).

Changes against Rev J (each justified in docs/revJ1_design.md):
  P1  gimbal strips 75 um (was 50 um), compression kept; the coil plate's back iron 1.5 mm (was 2.37: a magnetic-circuit
      estimate puts the iron at <= 1.9 T peak), so everything behind the plate moves 0.87 mm forward
  P3  a graphite (PGS) heat spreader, 0.1 x 30 mm, laminated into a recess of the shell's inner wall over z 80-110
  P4  the end-cap with the 9 mm tungsten slug (study K's family, rule J1-M2): about 29 g, 21 mm long
  P5  the first 15 mm of the front sleeve clear over its top 240 deg (hard-coated PC); the bottom 120 deg stays PEEK
  P6  the heel motors and their transfer gears 10 mm further back; the cue LRA moves forward into the space they free
  P2  the page sensor is a PMW3610-class die (same place and size in the layout)
"""
from __future__ import annotations

import copy
import math
from dataclasses import replace
from typing import Dict, List, Optional

from . import ensure_paths
from . import params as P1

ensure_paths()
from revj import frontend as RFR  # noqa: E402
from revj import packaging as RPK  # noqa: E402
from revj import params as RPA  # noqa: E402

T_BI_NEW = 1.5              # mm, PROPOSED DESIGN (revj1.magnetics.back_iron_flux: about 1.9 T peak estimated)
MOTOR_BACK_MM = 10.0        # mm, PROPOSED DESIGN (revj1.magnetics.detent: 0.55 x the motor friction, free space)
WINDOW = {"length_mm": 15.0, "clear_half_deg": 120.0, "material": "hard-coated polycarbonate (PC)",
          "note": "the finger pads sit at z 26-38 (Rev H hand model), so the first 15 mm behind the ring are free of fingers"}
ENDCAP_LS_MM = 9.0          # rule J1-M2 (revj1.endcap_mass)


def _shift(c: Dict, dz: float, ends=("z0", "z1")):
    for k in ends:
        c[k] = round(c[k] + dz, 3)


def endcap_parts(L_s_mm: float, z_start: float) -> List[Dict]:
    """Study K's compact end-cap parts (endcap.layout.lrm_parts_compact, read-only) for the family member with slug
    length L_s, its shell shortened to the coils' length + 4 mm, starting at z_start (CALC; PROPOSED DESIGN)."""
    from endcap import layout as EL
    from . import endcap_mass as EM
    s = EM.member(L_s_mm)
    X = s["X"] * 1e3
    L_mag = min(L_s_mm, 12.0)
    L_coil = L_mag + 2 * X
    L_shell = L_coil + 4.0
    saved = dict(EL.COMPACT)
    try:
        EL.COMPACT.update(z0=z_start, z1=z_start + L_shell, zc=z_start + 1.0 + L_coil / 2)
        parts = EL.lrm_parts_compact(s)
    finally:
        EL.COMPACT.clear()
        EL.COMPACT.update(saved)
    out = []
    for q in parts:
        if q["id"] == "ec_usb_moved":
            continue
        q = dict(q)
        q["group"] = "inertial"
        q["optional"] = True
        for k in ("z0", "z1"):
            q[k] = round(float(q[k]), 2)
        if q.get("mass_g") is not None:
            q["mass_g"] = round(float(q["mass_g"]), 3)
        out.append(q)
    return out, {"L_s_mm": L_s_mm, "L_coil_mm": L_coil, "L_shell_mm": L_shell, "stroke_mm": X,
                 "design_mass_g": s["mass_g"], "slug_g": s["parts_g"]["slug_g"], "Km": s["Km"], "F_act_N": s["F_act"],
                 "moving_mass_g": s["moving_mass_g"], "P_avg_W_design": s["P_avg_W"]}


def build(quick: bool = False, fe: Optional[Dict] = None) -> Dict:
    nt, npf = (9, 24) if quick else (17, 72)
    h = RFR.Heel()
    fe = fe or RFR.close(h, n_theta=nt, n_phi=npf)
    geo = RPK.build(fe, quick=quick)                       # Rev J (read-only function)
    geo = copy.deepcopy(geo)
    internal = geo.pop("_internal")
    nd = RPA.nose_design()
    comps = geo["components"]
    c = {x["id"]: x for x in comps}
    changes = []
    # ---------------------------------------------------------------- P1: coil plate back iron 2.37 -> 1.5 mm
    plate = c["coil_plate"]
    t_bi_old = nd["t_bi"]
    d_t = T_BI_NEW - t_bi_old
    z_old_end = plate["z1"]
    dm_plate = d_t * math.pi * 11.0 ** 2 * RPA.RHO["Hiperco"].value * 1e-3
    plate["z1"] = round(plate["z1"] + d_t, 3)
    plate["mass_g"] = round(plate["mass_g"] + dm_plate, 3)
    plate["function"] += f"  Rev J.1: back iron {T_BI_NEW:.1f} mm (was {t_bi_old:.2f} mm)."
    changes.append(f"coil plate back iron {t_bi_old:.2f} -> {T_BI_NEW:.2f} mm ({dm_plate:+.2f} g; the parts behind move {d_t:+.2f} mm)")
    for x in comps:
        if x["id"] in ("coil_plate",):
            continue
        if x["z0"] >= z_old_end - 0.6 and x.get("group") != "inertial":
            _shift(x, d_t)
        elif x["id"] in ("shell", "drive_shaft_drive", "drive_shaft_steering"):
            _shift(x, d_t, ends=("z1",))
    z_shell_end = c["shell"]["z1"]
    geo["length"] = round(c["rear_cap"]["z1"], 2)
    # ---------------------------------------------------------------- P1: gimbal strips 75 um
    g = c["gimbal"]
    g["part"] = "custom (301 FH 0.075 mm strips, laser cut; crossing at mid-length; compression as study N) + axial stops"
    g["mass_g"] = round(g["mass_g"] + 0.02, 3)
    g["function"] += "  Rev J.1: 75 um strips carry the cap's axial pull in compression (buckling 55 N, beam model)."
    changes.append("gimbal strips 50 -> 75 um (buckling 16.4 -> 55 N, CALC beam model)")
    # ---------------------------------------------------------------- P6: motors and gears 10 mm back, LRA forward
    for mid in ("drive_motor", "steer_motor", "drive_transfer"):
        _shift(c[mid], MOTOR_BACK_MM)
    for sid in ("drive_shaft_drive", "drive_shaft_steering"):
        _shift(c[sid], MOTOR_BACK_MM, ends=("z1",))
    lra = c["lra"]
    L_lra = lra["z1"] - lra["z0"]
    lra["z0"] = round(c["battery"]["z0"] + 0.6, 3)
    lra["z1"] = round(lra["z0"] + L_lra, 3)
    lra["function"] = "Gentle buzz cues, lying flat against the bottom wall under the cell's front end (Rev J.1: moved forward)."
    changes.append(f"heel motors and transfer gears {MOTOR_BACK_MM:+.0f} mm (motors z {c['drive_motor']['z0']:.1f}-"
                   f"{c['drive_motor']['z1']:.1f}); shafts {c['drive_shaft_drive']['z1'] - c['drive_shaft_drive']['z0']:.1f} mm; "
                   f"LRA to z {lra['z0']:.1f}-{lra['z1']:.1f}")
    # ---------------------------------------------------------------- P3: graphite spreader in the shell wall
    from . import thermal as TH
    sp = TH.CHOSEN
    comps.append(RPK.comp("heat_spreader", "Heat spreader (graphite sheet in the shell wall)", "structure", "tube",
                          sp["z_mm"][0], sp["z_mm"][1], "handle", 22.2, 22.2, 22.0,
                          function="Spreads the coil plate's heat along 30 mm of shell under the thumb-index web; laminated in "
                                   "a 0.1 mm recess of the inner wall, so the bore does not shrink.",
                          part="pyrolytic graphite sheet 0.1 mm (PGS class, a-b plane 600-800 W/mK, about 1 g/cm3; MFR AMF-158)",
                          ledger="AMF-158", mass_g=round(TH.chosen_mass_g(), 3)))
    changes.append(f"graphite spreader 0.1 x 30 mm in the shell wall (+{TH.chosen_mass_g():.2f} g; Rev J's 0.5 mm Al sleeve: "
                   "+2.1 g, and inside the bore it would hit the cap and the motors)")
    # ---------------------------------------------------------------- P5: clear sleeve window
    sl = c["front_sleeve"]
    sl["window"] = {"z0": sl["z0"], "z1": round(sl["z0"] + WINDOW["length_mm"], 2), "clear_half_deg_about_top": WINDOW["clear_half_deg"],
                    "material": WINDOW["material"], "note": WINDOW["note"]}
    sl["part"] = "PEEK core + TPE overmould; first 15 mm clear hard-coated PC over the top 240 deg (bottom 120 deg PEEK)"
    changes.append("front sleeve: first 15 mm clear over the top 240 deg (hard-coated PC)")
    # ---------------------------------------------------------------- P2: page-sensor die
    ps = c["page_sensor"]
    ps["part"] = ("low-power optical-navigation die (PMW3610 class: 0.60 mA run at 1.8 V, 3200 cpi, 24-30 in/s; MFR OPT-61) + "
                  "lens + 45 deg mirror (PROPOSED DESIGN); PMW3360 class as the fallback for autowrite")
    ps["ledger"] = "OPT-61; OPT-54; AMF-109"
    changes.append("page sensor: PMW3610-class die, on in every mode")
    # ---------------------------------------------------------------- P4: the lighter end-cap
    comps[:] = [x for x in comps if x.get("group") != "inertial"]
    ec, ec_info = endcap_parts(ENDCAP_LS_MM, z_shell_end)
    comps.extend(ec)
    geo["length_with_endcap"] = round(z_shell_end + ec_info["L_shell_mm"], 2)
    changes.append(f"end-cap: slug L {ENDCAP_LS_MM:.0f} mm ({ec_info['slug_g']:.1f} g), shell {ec_info['L_shell_mm']:.1f} mm, "
                   f"{sum(x.get('mass_g') or 0 for x in ec):.1f} g")
    # ---------------------------------------------------------------- fit checks
    nz = replace(RFR.c1s_nose(), X=fe["X_nom_mm"])
    fc = RPK.fit_checks(geo, fe, nz, nd, internal["refill"], internal["page_sensor"], h)
    fc.update(extra_checks(geo, nd, nz, ec_info))
    fc["all_pass"] = bool(all(v >= -1e-9 for k, v in fc.items() if k not in ("all_pass", "label")))
    geo["fit_checks"] = fc
    geo["revJ1_changes"] = changes
    geo["endcap_member"] = ec_info
    geo["_internal"] = dict(internal, fe=fe, nz=nz, h=h)
    return geo


def extra_checks(geo: Dict, nd: Dict, nz, ec_info: Dict) -> Dict:
    """Checks the Rev J.1 changes need (margins in mm beyond each rule, CALC; rules ASSUMPTION as Rev J: 0.3 mm running
    clearances, 0.2 mm between fixed parts)."""
    c = {x["id"]: x for x in geo["components"]}
    out = {}
    # LRA (moved forward) against the transfer gears (moved back), along z
    out["lra_to_transfer_gears_z_mm"] = round(c["drive_transfer"]["z0"] - c["lra"]["z1"] - 0.2, 3)
    # the LRA behind the coil plate
    out["lra_behind_coil_plate_mm"] = round(c["lra"]["z0"] - c["coil_plate"]["z1"] - 0.2, 3)
    # motors inside the cell's length (they lie under it)
    out["motors_under_cell_mm"] = round(c["battery"]["z1"] - c["drive_motor"]["z1"], 3)
    # motor end against the USB port (z) where they share the bottom/side: the USB sits at +y 9 mm, the motors at -7.2 x
    out["end_cap_member_length_mm"] = round(175.0 - geo["length_with_endcap"], 3)
    # the LRA now lies over the drive shafts' rear part: shaft liners (0.5 mm radius) to the LRA's bottom face (fixed parts)
    sh = c["drive_shaft_drive"]
    lra = c["lra"]
    z_overlap = min(sh["z1"], lra["z1"]) - max(sh["z0"], lra["z0"])
    if z_overlap > 0:
        x_face = lra["offset"][0] - lra["size"][0] / 2
        out["lra_to_shaft_liners_mm"] = round(abs(sh["offset"][0]) - abs(x_face) - 0.5, 3)
    # the spreader sits in the wall: bore unchanged (0.1 mm recess in a 1.0 mm wall leaves 0.9 mm of PEEK)
    out["spreader_wall_left_mm"] = round(1.0 - P1.SPREADERS["PGS_graphite"]["t_mm"][1] - 0.5, 3)
    # gimbal strip length unchanged (study N's frame)
    return out


def public(geo: Dict) -> Dict:
    return {k: v for k, v in geo.items() if not k.startswith("_")}
