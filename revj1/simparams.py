r"""MuJoCo parameters (sim2 / sim2j) for the Rev J.1 pen, in the schema of results/revJ/sim_params.json.

Built by running Rev J's builder (revj.simparams.build, read-only) on the Rev J.1 layout, then replacing the entries
that Rev J.1 changes, each with value, unit, label and source.  Metres, kilograms, seconds.
"""
from __future__ import annotations

import math
from typing import Dict

from . import ensure_paths
from . import params as P1

ensure_paths()
from revj import simparams as RSP  # noqa: E402


def _v(value, unit, label, source, note=""):
    d = {"value": value, "unit": unit, "label": label, "source": source}
    if note:
        d["note"] = note
    return d


def build(geo: Dict, bud_revj_format: Dict, mag_revj_format: Dict, fe: Dict, rf: Dict, bud1: Dict, mag1: Dict,
          endcap_verdict: Dict) -> Dict:
    sp = RSP.build(geo, bud_revj_format, mag_revj_format, fe, rf)
    gs = bud1["gimbal"]
    ap = mag1["pull_variants"]["rows"]["revJ"]
    conv = mag1["pull_variants"]["D_conventions"]
    pulls = [conv[k]["pull_N"] for k in conv]
    det = mag1["detent"]
    moved = [r for r in det["moving_back"] if abs(r["moved_back_mm"] - 10.0) < 1e-6]
    det_bound = (moved[0]["torque_amp_mNm"] if moved else det["worst_torque_amp_mNm"]) * 1e-3
    ec = geo["endcap_member"]
    nose = sp["nose"]
    nose["flexure_k_Nm_per_rad"] = _v(gs["k_pull_Nm_rad"], "N m/rad", "CALC",
                                      "revj1/gimbal.py (75 um strips in compression under the 16.5 N pull; beam model)",
                                      f"unloaded {gs['k_unloaded_Nm_rad']:.4f} N m/rad; the stiffness rises with the pull "
                                      "(compression stiffens a mid-length cross-strip pivot)")
    nose["flexure_k_unloaded_Nm_per_rad"] = _v(gs["k_unloaded_Nm_rad"], "N m/rad", "CALC", "revj1/gimbal.py")
    nose["gimbal_buckling_axial_N"] = _v(gs.get("buckling_N", 55.3), "N", "CALC", "revj1/gimbal.py (beam model of the 75 um pivot)")
    nose["axial_magnetic_pull_N"] = _v(ap["pull_N"], "N", "CALC",
                                       "image method, ideal iron (upper bound for the stated iron face)",
                                       f"the face position is uncertain: {min(pulls):.1f}-{max(pulls):.1f} N across the three "
                                       "conventions in revj1/magnetics.py")
    nose["magnetic_negative_k_Nm_per_rad"] = _v([0.0, ap["pull_N"] * 0.05e-3], "N m/rad", "CALC",
                                                "revj1/magnetics.centring: F e_p with the sphere centre within 0.05 mm")
    nose["coil_Rth_K_W"] = _v(bud1["heat"]["chosen_R_K_W"] + bud1["heat"]["web"]["R_int_K_W"], "K/W", "CALC",
                              "revj1/thermal.py (15 K/W inside + the shell with the graphite spreader)")
    nose["coil_power_sensitivity"] = _v(list(P1.NOSE_POWER_FACTORS.value), "-", "ASSUMPTION", P1.NOSE_POWER_FACTORS.source)
    hw = sp["heel_wheel"]
    hw["magnetic_detent_torque_bound_Nm"] = _v(det_bound, "N m", "CALC",
                                               "revj1/magnetics.detent (motors 10 mm back; free space, vector-averaged "
                                               "transverse field; an upper bound)")
    L_sh = (next(c for c in geo["components"] if c["id"] == "drive_transfer")["z0"]
            - next(c for c in geo["components"] if c["id"] == "drive_shaft_drive")["z0"]) * 1e-3
    hw["shaft_length_m"] = _v(L_sh, "m", "CALC", "Rev J.1 layout (motors and gears 10 mm back)")
    hw["shaft_torsion_Nm_per_rad"] = _v(80e9 * math.pi * (0.8e-3) ** 4 / 32 / L_sh, "N m/rad", "CALC",
                                        "G 80 GPa steel (ASSUMPTION), d 0.8 mm")
    e = sp["endcap"]
    e["slug_mass_kg"] = _v(sum(c["mass_g"] for c in geo["components"] if c.get("moves_with") == "inertial_mass") * 1e-3, "kg",
                           "CALC", f"study K's LRM family, slug {ec['L_s_mm']:.0f} mm (rule J1-M2, revj1/endcap_mass.py)")
    e["slug_centre_z_m"] = _v(0.5 * sum((c["z0"] + c["z1"]) for c in geo["components"] if c["id"] == "ec_slug") * 1e-3, "m",
                              "CALC", "Rev J.1 layout")
    e["stroke_m"] = _v(ec["stroke_mm"] * 1e-3, "m", "CALC", "study K design model (endcap.design.lrm2)")
    k_ec = e["slug_mass_kg"]["value"] * (2 * math.pi * 5.0) ** 2
    e["flexure_k_N_per_m"] = _v(k_ec, "N/m", "CALC", "m (2 pi 5 Hz)^2 per axis")
    e["Km_N_per_sqrtW"] = _v(ec["Km"], "N/sqrt(W)", "CALC", "study K design model")
    e["F_act_N"] = _v(ec["F_act_N"], "N", "CALC", "study K design model (0.5 W per axis)")
    e["test_verdict_SIM"] = _v({k: endcap_verdict.get(k) for k in ("r0.3", "r0.5", "r0.7", "pass", "P_act_W_mean_SIM")}, "-", "SIM",
                               "revj1/endcap_mass.py (study K's H1 cascade, test seeds 200-203, Rev H pen)")
    s = sp["sensors"]
    pg = dict(s["page_sensor"]["value"])
    pg.update({"part": "PMW3610 class", "rate_hz": 1000.0, "latency_s": 0.002, "quantisation_m": 25.4e-3 / 3200,
               "noise_m": 3e-6, "valid_height_m": [2.2e-3, 2.6e-3], "on_in_modes": ["steady", "guide", "lead", "autowrite"]})
    s["page_sensor"] = _v(pg, "-", "ASSUMPTION / MFR",
                          "OPT-61 (PMW3610: 3200 cpi, 24-30 in/s, lens plane 2.2-2.6 mm); 1 kHz and 2 ms kept as the requirement "
                          "(REQ-RVJ-N06); noise unmeasured (EXP-J10)")
    dr = sp["domain_randomisation_added"]
    dr["axial_pull_N"] = [min(pulls), max(pulls)]
    dr["nose_flexure_k_Nm_per_rad"] = [gs["k_unloaded_Nm_rad"], gs["k_pull_Nm_rad"] * 1.2]
    dr["motor_detent_Nm"] = [0.0, det_bound]
    dr["nose_coil_power_factor"] = list(P1.NOSE_POWER_FACTORS.value)
    dr["note"] = (dr.get("note", "") + "; Rev J.1: pull, flexure and detent ranges from revj1 (CALC); the coil-power factor "
                  "is a reporting sensitivity, not a plant parameter")
    sp["revJ1"] = {"changes": geo.get("revJ1_changes", []),
                   "label": "PROPOSED DESIGN; entries not listed here are Rev J's builder on the Rev J.1 layout"}
    return sp
