"""Interface files (results/revH/), the assembled results JSON, figures with CSV twins, the replay and the evidence rows.

Stages callable from run_study: report (everything below), interfaces (tip_params.json + layout.json only).
Evidence labels: SIM (model H1 runs), CALC (formulas, design models), MFR (ledger id), LITERATURE (ledger id), ASSUMPTION.
"""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from stabpen import provenance
from . import catalog as CT
from . import geometry as GE
from . import revh as RH

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVH_DIR = os.path.join(ROOT, "results", "revH")
OPT = os.path.join(ROOT, "results", "opt")
CACHE = os.path.join(OPT, "_cache")


def _stage(name):
    p = os.path.join(CACHE, f"inertial_stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _mean(rows, f):
    v = [f(r) for r in rows]
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def grid_summary(grid: Dict) -> Dict:
    """Mean over test seeds per (tracker, r_rot, tremor kind, amplitude, frequency)."""
    out = {}
    for tag, rows in grid["rows"].items():
        for r in rows:
            k = (tag, r["r_rot"], r["kind"], r["amp_mm"], r["f0"])
            out.setdefault(k, []).append(r)
    summ = []
    for (tag, rr, kind, amp, f0), rows in sorted(out.items()):
        row = {"tracker": tag, "r_rot": rr, "kind": kind, "amp_mm": amp, "f0": f0, "n": len(rows),
               "unmod_e_rms_um": _mean(rows, lambda r: r["unmod_e_rms_um"]),
               "akf_ratio": _mean(rows, lambda r: r["akf"]["ratio"]), "akf_band_ratio": _mean(rows, lambda r: r["akf"]["band_ratio"]),
               "akf_q_sat": _mean(rows, lambda r: r["akf"]["q_sat_frac"]),
               "akf_F_tip_rms_N": [_mean(rows, lambda r: r["akf"]["F_tip_rms_N"][0]), _mean(rows, lambda r: r["akf"]["F_tip_rms_N"][1])]}
        if "oracle" in rows[0]:
            row["oracle_ratio"] = _mean(rows, lambda r: r["oracle"]["ratio"])
            row["oracle_q_sat"] = _mean(rows, lambda r: r["oracle"]["q_sat_frac"])
        summ.append(row)
    return summ


def power_final(F_rms_axes, d: Optional[RH.RevH] = None):
    """Recompute the tip copper loss for the final design constant Km_tip (CALC)."""
    d = d or RH.RevH()
    Pcu = float(sum(f * f for f in F_rms_axes) / d.Km_tip ** 2)
    return {"P_cu_W": Pcu, "P_total_W": CT.ELECTRONICS["base_W"] + 0.012 + Pcu}


# ------------------------------------------------------------------ interface files for the other agents
def _tracker_changes() -> str:
    p = os.path.join(OPT, "inertial_tracker_revh.json")
    if not os.path.exists(p):
        return "n/a"
    from . import tracker as TK
    ship = TK.ship_params()
    ch = json.load(open(p))["changed"]
    return ", ".join(f"{k} {ship.get(k, float('nan')):.3g} -> {v:.3g}" for k, v in ch.items())


def write_tip_params(final=True, addon_decision: Optional[Dict] = None, calib: Optional[Dict] = None):
    d = RH.RevH()
    ms = RH.masses(d)
    geo = GE.layout(d)
    grid = _stage("grid")
    th = math.radians(50.0)
    Fpk_act = d.Km_act * math.sqrt(3.7 * 1.5)
    Fc_act = d.Km_act * math.sqrt(0.35)
    res = {}
    if grid:
        sm = grid_summary(grid)
        B_or = [r["oracle_ratio"] for r in sm if r["tracker"] == "ship" and r["kind"] == "trans"]
        rv = [r for r in sm if r["tracker"] == "revh" and r["kind"] == "trans" and r["r_rot"] == 0.5]
        Fr = [r["akf_F_tip_rms_N"] for r in sm if r["tracker"] == "revh"]
        pw = power_final(np.mean(Fr, axis=0).tolist(), d)
        A = grid["A"]["rows"]
        res = {"B_oracle_ratio_range": [min(B_or), max(B_or)],
               "B_revh_tracker_ratio_8_12Hz_1_2mm": [min(r["akf_ratio"] for r in rv if r["f0"] >= 8 and r["amp_mm"] >= 1),
                                                    max(r["akf_ratio"] for r in rv if r["f0"] >= 8 and r["amp_mm"] >= 1)],
               "A_oracle_ratio_range": summarise_arch(grid)["ranges"]["A_oracle"],
               "A_P_cu_with_bias_W": float(np.mean([r["akf"]["P_cu_W"] for r in A])),
               "A_P_cu_without_bias_W": float(np.mean([r["akf"]["P_cu_no_bias_W"] for r in A])),
               "A_writing_force_std_N": float(np.mean([r["akf"]["N_std_N"] for r in A])),
               "B_tip_force_rms_N": np.mean(Fr, axis=0).tolist(), "B_power_W": pw,
               "B_P_cu_W_mean": float(np.mean([r["akf"]["P_cu_W"] for tag in ("revh",) for r in grid["rows"][tag]])),
               "A_design_point": grid["A"]["design"],
               "note": "ranges are means over test seeds per condition; B over 0.1-2 mm, 4-12 Hz and the three splits, A at r_rot 0.5 and 0.3-2 mm",
               "label": "SIM (model H1, test seeds 200-203, first use; see results/opt/inertial_opt.json)"}
    cell = CT.CELLS[d.cell]
    out = {
        "meta": provenance.metadata("SIMULATION + CALCULATION (Rev H active nose, model H1; nothing measured)" if final else
                                    "PROVISIONAL", seeds={"test": [200, 201, 202, 203], "train": [300, 301]},
                                    extra={"script": "opt/inertial/report.py", "doc": "docs/opt_inertial.md"}),
        "architecture": "B",
        "architecture_note": (("B = a skid ring on the FIXED front sleeve carries the writing force; the refill carrier (the moving nose) "
                               "tilts on a 2-axis flexure gimbal so the ball moves up to +/-3 mm; the refill slides axially on a soft "
                               "constant-force spring so the ball stays on the paper. Chosen over A (rigid nose carrying the load) by "
                               "simulation: A's ceiling with perfect knowledge is {a0:.2f}-{a1:.2f} of the ink error against {b0:.2f}-{b1:.2f} for B, A "
                               "needs {pa:.2f} W of copper loss with a bias spring ({pn:.1f} W without) against about {pb:.3f} W for B, and a rigid "
                               "nose must press the tip into the paper for tilt-plane corrections ({ns:.2f} N rms writing-force change).").format(
                                   a0=res["A_oracle_ratio_range"][0], a1=res["A_oracle_ratio_range"][1], b0=res["B_oracle_ratio_range"][0],
                                   b1=res["B_oracle_ratio_range"][1], pa=res["A_P_cu_with_bias_W"], pn=res["A_P_cu_without_bias_W"],
                                   pb=res["B_P_cu_W_mean"], ns=res["A_writing_force_std_N"]) if res else "B (see docs/opt_inertial.md)"),
        "results_summary": res,
        "tip_travel_mm": {"usable_radius": d.travel * 1e3, "mechanical_stop_radius": (d.travel + 0.5e-3) * 1e3,
                          "label": "PROPOSED; SIM: never at its limit with perfect knowledge of 2 mm tremor except peaks at 10-12 Hz (see sweep)"},
        "refill_axial_slide_mm": {"value": 8.0, "note": "delta cot(theta) for the tilt-plane correction (2.5 mm at 3 mm, 50 deg) plus the tilt-dependent ball protrusion 1.1-7.3 mm at 75-35 deg (skid contact radius 5.5 mm); constant-force spring 0.15 N (P0 value, ASSUMPTION)",
                                  "label": "CALC"},
        "moving_mass_at_tip_g": {"value": round(ms["moving_mass_at_tip_g"], 3), "total_moving_g": round(ms["nose_g"], 3),
                                 "inertia_about_pivot_g_mm2": round(ms["nose_inertia_about_pivot_g_mm2"], 1),
                                 "label": "CALC (parts in opt/inertial/revh.nose_parts: Ti carrier, D1 refill, Al arm, 4 NdFeB magnets)"},
        "suspension_stiffness_N_per_m": {"value": round(d.k_r / d.z_p ** 2, 2), "gimbal_bending_Nm_per_rad": d.k_r,
                                         "label": "ASSUMPTION (laser-cut cross-strip gimbal, 301 full-hard / 17-7PH, AMF-20)"},
        "actuator": {"type": "2-axis moving-magnet flat voice coils: 4 NdFeB magnets on the nose's rear arm, 4 flat coils with a soft-iron "
                             "back ring in the handle; each magnet moves parallel to its coil (shear) for its own axis",
                     "Km_actuator_N_per_sqrtW_per_axis": round(d.Km_act, 3), "Km_at_tip_N_per_sqrtW_per_axis": round(d.Km_tip, 3),
                     "lever_tip_per_magnet": round(d.lever, 3),
                     "magnet_mm": [d.mag_w * 1e3, d.mag_l * 1e3, d.mag_t * 1e3], "coil_thickness_mm": d.coil_t * 1e3,
                     "magnet_stroke_mm": round(d.travel / d.lever * 1e3, 3),
                     "force_limit_at_tip_N": {"peak": round(Fpk_act / d.lever, 3), "continuous": round(Fc_act / d.lever, 3)},
                     "drivers": "2 x TI DRV8214 H-bridge with current mirror (AMF-37), 3.7 V cell",
                     "label": "CALC (adjoint design model opt/inertial/adjoint.py; magnet and copper data MFR AMF-28/AMF-29; leakage, fill and end-turn factors ASSUMPTION); peak = Km sqrt(3.7 V x 1.5 A), continuous = Km sqrt(0.35 W) per axis (ASSUMPTION thermal)"},
        "static_tip_load_N": {"refill_spring_transverse": round(0.15 / math.sin(th) * math.cos(th), 4),
                              "ball_friction": round(0.15 * 0.15 / math.sin(th), 4),
                              "bias": "a fixed spring or magnet offset cancels the 0.126 N refill-spring component (constant in the handle frame when the grip sleeve fixes the roll)",
                              "label": "CALC (F_c 0.15 N, mu_ball 0.15, 50 deg; ASSUMPTION values from config/pencil.yaml)"},
        "servo": {"type": "PID position loop on the 3-D Hall reading of the arm magnet; reference = -(tracker estimate) mapped to the tip",
                  "bandwidth_Hz": d.servo_hz, "damping": d.servo_zeta, "inner_rate_Hz": 10000.0,
                  "tip_reference_slew_m_s": d.slew,
                  "label": "ASSUMPTION (modelled in H1 as the stage's 2nd-order follower); sensitivity in the sweep"},
        "latency_ms": {"imu_to_estimate": 1.4, "controller_tick": 0.5, "servo_group_delay_at_12Hz": round(1e3 * 2 * d.servo_zeta / (2 * math.pi * d.servo_hz), 2),
                       "label": "ASSUMPTION built on MFR OPT-37 (fusion) and CALC for the 2nd-order servo"},
        "power_model": {"formula": "P_total = 0.065 + 0.012 + (F_tip_rms_t1^2 + F_tip_rms_t2^2) / Km_tip^2   [W]; F_tip = m_eff q'' + k_s q + ball loads - bias",
                        "Km_tip_N_per_sqrtW": round(d.Km_tip, 4), "typical_W": res.get("B_power_W", {}).get("P_total_W"),
                        "battery": {"part": cell.name, "ledger": cell.src, "usable_Wh": round(cell.Wh, 3),
                                    "life_h_writing_continuously": round(cell.Wh / res["B_power_W"]["P_total_W"], 1) if res else None},
                        "label": "CALC on SIM forces; 0.065 W base electronics and 0.012 W drivers/Hall ASSUMPTION"},
        "geometry_mm": {"pivot_z": geo["pivot_z"], "actuator_z": geo["actuator_z"], "front_opening_d": geo["front_opening_d"],
                        "skid_ring": {"contact_radius": geo["skid_contact_radius"], "od": round(geo["front_opening_d"] + 3.0, 2),
                                      "ball_protrusion_at_50deg": geo["ball_protrusion_mm"],
                                      "note": "C-shaped heel skid (open at the front for visibility) - feel and visibility ASSUMPTION, to test (EXP-H03 extension)"},
                        "grip_zone_z": [geo["grip_zone"]["z0"], geo["grip_zone"]["z1"]], "finger_pads_z": geo["hand"]["finger_pads_z"],
                        "web_z": geo["hand"]["web_z"], "handle_od": geo["handle_od"], "length": geo["length"], "pen_tilt_deg": 50.0,
                        "tilt_range_deg": [35.0, 75.0], "label": "PROPOSED DESIGN (opt/inertial/geometry.py, mechanics/cad/revH_pen.py)"},
        "mass_g": {"pen_without_inertial_module": round(ms["total_g"], 2), "handle": round(ms["handle_g"], 2), "moving_nose": round(ms["nose_g"], 2),
                   "com_mm_from_tip": round(ms["com_mm"], 1), "label": "CALC from assumed parts +10 % wiring"},
        "inertial_addon": addon_decision or {"status": "evaluated in docs/opt_inertial.md; see layout.json 'optional' components"},
        "tracker": {"default": "results/opt/tracker_models/akf_ship.json (shipped)", "rev_h_setting": "results/opt/inertial_tracker_revh.json",
                    "note": "Rev H setting chosen by ParEGO on training seeds by a pre-declared false-correction rule; changed from the shipped set: " + _tracker_changes(),
                    "per_user_band": ({"search_band_x_f_cal": calib["band"], "how": "20-30 s calibration at first use sets f_cal; the frequency search is limited to the band (opt/inertial/run_study.calibrated_params)",
                                       "result_r_rot_0.5": [r for r in calib["test"] if r["r_rot"] == 0.5], "distortion_um": calib["distortion"],
                                       "label": "SIM (test seeds, +10 % calibration error)"} if calib else None)},
    }
    os.makedirs(REVH_DIR, exist_ok=True)
    path = os.path.join(REVH_DIR, "tip_params.json" if final else "tip_params_provisional.json")
    provenance.write_json(path, out)
    return out


def write_layout(addon: Optional[Dict] = None, addon_recommended: bool = False):
    d = RH.RevH()
    geo = GE.layout(d, addon=addon)
    meta = provenance.metadata("PROPOSED DESIGN (dimensioned concept; CALC masses; ASSUMPTION dimensions) - Rev H active-nose pen, architecture B",
                               extra={"script": "opt/inertial/geometry.py (also mechanics/cad/revH_pen.py)", "doc": "docs/opt_inertial.md",
                                      "inertial_addon_recommended": addon_recommended})
    out = {"meta": meta, **{k: v for k, v in geo.items()}}
    os.makedirs(REVH_DIR, exist_ok=True)
    provenance.write_json(os.path.join(REVH_DIR, "layout.json"), out)
    return out


def stage_interfaces(quick=False):
    write_tip_params(final=True)
    write_layout(addon=None)


# ================================================================== study summaries (from the stage caches)
BAND = dict(amps=(1.0, 2.0), fs=(8.0, 10.0, 12.0))
SPLITS = (0.3, 0.5, 0.7)


def _sel(rows, **kw):
    out = []
    for r in rows:
        ok = True
        for k, v in kw.items():
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                ok &= r.get(k) in v
            else:
                ok &= r.get(k) == v
        if ok:
            out.append(r)
    return out


def summarise_arch(grid) -> Dict:
    """A vs B at r_rot 0.5 (A was run at the nominal split only): oracle and causal ratios, power, writing-force change."""
    A = grid["A"]["rows"]
    Bs = _sel(grid["rows"]["ship"], kind="trans", r_rot=0.5)
    Br = _sel(grid["rows"]["revh"], kind="trans", r_rot=0.5)
    out = {"A_design": grid["A"]["design"], "B_design": grid["design"], "by_condition": []}
    for amp in (0.3, 1.0, 2.0):
        for f0 in (4.0, 6.0, 8.0, 10.0, 12.0):
            a = _sel(A, amp_mm=amp, f0=f0)
            bs = _sel(Bs, amp_mm=amp, f0=f0)
            br = _sel(Br, amp_mm=amp, f0=f0)
            if not a or not bs:
                continue
            out["by_condition"].append({
                "amp_mm": amp, "f0": f0,
                "A_oracle": _mean(a, lambda r: r["oracle"]["ratio"]), "A_causal_ship": _mean(a, lambda r: r["akf"]["ratio"]),
                "A_P_cu_W": _mean(a, lambda r: r["akf"]["P_cu_W"]), "A_P_cu_no_bias_W": _mean(a, lambda r: r["akf"]["P_cu_no_bias_W"]),
                "A_N_std_N": _mean(a, lambda r: r["akf"]["N_std_N"]),
                "B_oracle": _mean(bs, lambda r: r["oracle"]["ratio"]), "B_causal_ship": _mean(bs, lambda r: r["akf"]["ratio"]),
                "B_causal_revh": _mean(br, lambda r: r["akf"]["ratio"]) if br else float("nan"),
                "B_P_cu_W": _mean(br or bs, lambda r: r["akf"]["P_cu_W"]), "B_oracle_P_cu_W": _mean(bs, lambda r: r["oracle"]["P_cu_W"])})
    bc = out["by_condition"]
    out["ranges"] = {k: [min(r[k] for r in bc), max(r[k] for r in bc)] for k in bc[0] if k not in ("amp_mm", "f0")}
    out["label"] = "SIM (model H1, test seeds 200-203, r_rot 0.5); power CALC from the simulated forces"
    return out


def summarise_B(grid) -> Dict:
    sm = grid_summary(grid)
    dist = {tag: {"lognormal_um": _mean([r for r in v if r["writer"] == "lognormal"], lambda r: r["distortion_um"]),
                  "glyph_um": _mean([r for r in v if r["writer"] == "glyph"], lambda r: r["distortion_um"])}
            for tag, v in grid["distortion"].items()}
    band = {}
    for tag in ("ship", "revh"):
        for rr in SPLITS:
            rows = [r for r in sm if r["tracker"] == tag and r["r_rot"] == rr and r["kind"] == "trans" and r["amp_mm"] in BAND["amps"]
                    and r["f0"] in BAND["fs"]]
            band[f"{tag}_r{rr}"] = {"causal": float(np.mean([r["akf_ratio"] for r in rows]))}
            orows = [r for r in sm if r["tracker"] == "ship" and r["r_rot"] == rr and r["kind"] == "trans" and r["amp_mm"] in BAND["amps"]
                     and r["f0"] in BAND["fs"]]
            band[f"{tag}_r{rr}"]["oracle"] = float(np.mean([r["oracle_ratio"] for r in orows]))
    return {"summary": sm, "distortion": dist, "band_8_12Hz_1_2mm": band,
            "label": "SIM (model H1, Rev H-B, test seeds 200-203; glyph test seeds 210-213 for distortion)"}


def summarise_addon(ad) -> Dict:
    rows = ad["rows"]
    out = {"rm": ad["rm"], "by_split": {}, "by_condition": []}
    groups = {"band_8_12Hz_1_2mm": dict(kind="trans", amp_mm=BAND["amps"], f0=BAND["fs"]), "all_translational": dict(kind="trans"),
              "0.3mm": dict(kind="trans", amp_mm=0.3), "4_6Hz": dict(kind="trans", f0=(4.0, 6.0)), "wrist_8Hz": dict(kind="wrist")}
    cfgs = ("nose", "nose+weight", "nose+ff", "nose+ff_cal", "nose+afc", "weight", "rm_neutral", "ilc", "ff", "afc")
    for rr in SPLITS:
        if not _sel(rows, r_rot=rr):
            continue
        d = {}
        for gname, flt in groups.items():
            rs = _sel(rows, r_rot=rr, **flt)
            if not rs:
                continue
            g = {c: _mean(rs, lambda r, c=c: r.get(c)) for c in cfgs}
            seeds = sorted(set(r["seed"] for r in rs))
            for c in ("nose+ff", "nose+ff_cal", "nose+afc", "nose+weight"):
                per = [np.mean([1 - r[c] / r["nose"] for r in rs if r["seed"] == s and c in r]) for s in seeds]
                g[f"gain_{c}"] = {"mean": float(np.mean(per)), "seed_min": float(np.min(per)), "seed_max": float(np.max(per)),
                                  "frac_conditions_worse": float(np.mean([r[c] > r["nose"] for r in rs if c in r]))}
            g["ff_P_cu_W_mean"] = _mean(rs, lambda r: r["ff_P_W"])
            g["ff_P_cu_W_max"] = float(np.max([r["ff_P_W"] for r in rs]))
            g["ff_stroke_peak_mm_max"] = float(np.max([max(r["ff_stroke_pk_mm"]) for r in rs]))
            d[gname] = g
        out["by_split"][str(rr)] = d
    for rr in SPLITS:
        for kind in ("trans", "wrist"):
            for amp in (0.3, 1.0, 2.0):
                for f0 in (4.0, 6.0, 8.0, 10.0, 12.0):
                    rs = _sel(rows, r_rot=rr, kind=kind, amp_mm=amp, f0=f0)
                    if rs:
                        out["by_condition"].append({"r_rot": rr, "kind": kind, "amp_mm": amp, "f0": f0,
                                                    **{c: _mean(rs, lambda r, c=c: r.get(c)) for c in cfgs},
                                                    "ff_P_cu_W": _mean(rs, lambda r: r["ff_P_W"]),
                                                    "ff_stroke_peak_mm": float(np.max([max(r["ff_stroke_pk_mm"]) for r in rs]))})
    out["distortion_um"] = {c: {w: _mean([x for x in ad["distortion"] if x["ctrl"] == c and x["writer"] == w], lambda x: x["distortion_um"])
                                for w in ("lognormal", "glyph")} for c in ("ff", "afc")}
    out["label"] = "SIM (model H1, Rev H-B + rear-cap reaction mass, test seeds 200-203; ratios against the Rev H pen without add-on or correction)"
    return out


def addon_decision(sa: Dict, d: Optional[RH.RevH] = None) -> Dict:
    """Decision on the rear-cap module against the lead's guide (<= 30 g, <= 0.5 W, measurable benefit on top of the nose).
    'Measurable' as used here (set after the grid, not pre-declared): >= 10 % further reduction of the ink error in the
    8-12 Hz, 1-2 mm band on every test seed at r_rot 0.5 and 0.7, and no split where it is worse on average."""
    d = d or RH.RevH()
    rm = sa["rm"]
    m_add = rm["m_g"] + rm["added_fixed_g"]
    splits = [rr for rr in SPLITS if str(rr) in sa["by_split"]]
    g = {rr: sa["by_split"][str(rr)]["band_8_12Hz_1_2mm"]["gain_nose+ff"] for rr in splits}
    gc = {rr: sa["by_split"][str(rr)]["band_8_12Hz_1_2mm"]["gain_nose+ff_cal"] for rr in splits}
    gw = {rr: sa["by_split"][str(rr)]["band_8_12Hz_1_2mm"]["gain_nose+weight"] for rr in splits}
    P = max(sa["by_split"][str(rr)]["all_translational"]["ff_P_cu_W_max"] for rr in splits)
    measurable = all(g[rr]["seed_min"] >= 0.10 for rr in (0.5, 0.7) if rr in g) and all(g[rr]["mean"] > 0 for rr in splits)
    ok_mass = m_add <= 30.0
    P_mod = P + 0.012
    ok_power = P_mod <= 0.5
    total = RH.masses(d)["total_g"] + m_add
    cell10440 = total - (CT.CELLS["LIR14500"].m - CT.CELLS["LIR10440"].m) * 1e3
    return {"include": bool(measurable and ok_mass and ok_power), "as": "optional rear-cap module (Rev H standard build without it)",
            "module": rm["label"], "added_mass_g": m_add, "pen_mass_with_module_g": round(total, 1),
            "pen_mass_with_module_and_10440_g": round(cell10440, 1),
            "power_W": {"copper_max_W": P, "module_total_max_W": P_mod, "note": "copper loss max over all test conditions + 0.012 W driver/Hall (ASSUMPTION)"},
            "gain_band_8_12Hz_1_2mm": {str(rr): g[rr] for rr in splits},
            "gain_with_grip_calibration": {str(rr): gc[rr] for rr in splits},
            "passive_weight_gain": {str(rr): gw[rr] for rr in splits},
            "criteria": {"measurable": measurable, "mass_ok_30g": ok_mass, "power_ok_0.5W": ok_power,
                         "rule": addon_decision.__doc__.split("'Measurable'")[1].strip()},
            "label": "SIM + CALC"}


def summarise_sweep(sw) -> Dict:
    from collections import defaultdict
    g = defaultdict(list)
    for r in sw["rows"]:
        g[(r["travel_mm"], r["servo_hz"])].append(r)
    rows = [{"travel_mm": k[0], "servo_hz": k[1], "oracle": _mean(v, lambda r: r["oracle"]), "causal": _mean(v, lambda r: r["akf"]),
             "oracle_sat": _mean(v, lambda r: r["oracle_sat"]), "causal_sat": _mean(v, lambda r: r["akf_sat"])} for k, v in sorted(g.items())]
    return {"rows": rows, "seeds": sw["seeds"], "label": sw["label"]}


def summarise_calib(cb) -> Dict:
    from collections import defaultdict
    out = {"band": cb["band"], "dev": [], "test": [], "distortion": {}}
    g = defaultdict(list)
    for r in cb["dev_rows"]:
        g[(r["cal_err"], r["amp_mm"], r["f0"])].append(r)
    out["dev"] = [{"cal_err": k[0], "amp_mm": k[1], "f0": k[2], "causal": _mean(v, lambda r: r["akf"]["ratio"]),
                   "f_est": _mean(v, lambda r: r.get("akf_f_est_mean"))} for k, v in sorted(g.items())]
    g = defaultdict(list)
    for r in cb["test_rows"]:
        g[(r["r_rot"], r["amp_mm"], r["f0"])].append(r)
    out["test"] = [{"r_rot": k[0], "amp_mm": k[1], "f0": k[2], "causal": _mean(v, lambda r: r["akf"]["ratio"]),
                    "f_est": _mean(v, lambda r: r.get("akf_f_est_mean")), "P_cu_W": _mean(v, lambda r: r["akf"].get("P_cu_W"))}
                   for k, v in sorted(g.items())]
    for fc in sorted(set(x["f_cal"] for x in cb["distortion"])):
        rs = [x for x in cb["distortion"] if x["f_cal"] == fc]
        out["distortion"][f"{fc:.2f}"] = {w: _mean([x for x in rs if x["writer"] == w], lambda x: x["distortion_um"]) for w in ("lognormal", "glyph")}
    out["label"] = cb["label"]
    return out


def summarise_neural(nn) -> Dict:
    def agg(rows, c):
        return _mean(rows, lambda r: r.get(c))
    out = {"train": nn["train"], "cost": nn["cost"], "history_val": [h for h in nn["history"] if "val" in h]}
    out["validation_h1"] = {c: agg(nn["val_rows"], c) for c in ("rm_neutral", "ff", "nn")}
    out["test_h1"] = {}
    for rr in SPLITS:
        rs = _sel(nn["test_rows"], r_rot=rr)
        if rs:
            out["test_h1"][str(rr)] = {c: agg(rs, c) for c in ("nose", "ff", "nn", "nose+ff", "nose+nn")}
            out["test_h1"][str(rr)]["nn_P_cu_W"] = agg(rs, "nn_P_W")
    out["distortion_um"] = {w: _mean([x for x in nn["distortion"] if x["writer"] == w], lambda x: x["distortion_um"]) for w in ("lognormal", "glyph")}
    out["label"] = nn["label"]
    return out


# ================================================================== figures
def make_figures(S: Dict, akf_params=None) -> List[str]:
    from . import figures as FG
    files = []
    F = (4.0, 6.0, 8.0, 10.0, 12.0)
    # 1. architecture A vs B (r_rot 0.5)
    ar = S["arch"]["by_condition"]
    panels = {}
    for amp in (0.3, 1.0, 2.0):
        rs = sorted([r for r in ar if r["amp_mm"] == amp], key=lambda r: r["f0"])
        x = [r["f0"] for r in rs]
        panels[f"{amp:g} mm tremor"] = {"B (skid carries load), perfect knowledge": (x, [r["B_oracle"] for r in rs]),
                                        "B, causal (Rev H tracker)": (x, [r["B_causal_revh"] for r in rs]),
                                        "A (nose carries load), perfect knowledge": (x, [r["A_oracle"] for r in rs]),
                                        "A, causal (shipped tracker)": (x, [r["A_causal_ship"] for r in rs])}
    files.append(FG.lines_panels("fig_in_arch", "Rev H active nose: architecture B vs A (ink error with / without correction)", panels,
                                 "tremor frequency (Hz)", "ink error ratio (lower is better)", ylim=(0, 1.15), hline=1.0,
                                 note=("SIM, model H1, test seeds 200-203, grip split r_rot 0.5. A also needs {0:.2f}-{1:.2f} W of coil power with a bias spring "
                                       "({2:.1f}-{3:.1f} W without) and changes the writing force by {4:.2f}-{5:.2f} N rms; B needs about {6:.3f} W.").format(
                                           *S["arch"]["ranges"]["A_P_cu_W"], *S["arch"]["ranges"]["A_P_cu_no_bias_W"], *S["arch"]["ranges"]["A_N_std_N"],
                                           float(np.mean([r["B_P_cu_W"] for r in ar])))))
    # 2. grip split, causal (Rev H tracker) and oracle
    sm = S["B"]["summary"]
    panels = {}
    for amp in (1.0, 2.0):
        ser = {}
        for rr in SPLITS:
            rs = sorted([r for r in sm if r["tracker"] == "revh" and r["r_rot"] == rr and r["kind"] == "trans" and r["amp_mm"] == amp],
                        key=lambda r: r["f0"])
            ser[f"causal, r_rot {rr}"] = ([r["f0"] for r in rs], [r["akf_ratio"] for r in rs])
        rs = sorted([r for r in sm if r["tracker"] == "ship" and r["r_rot"] == 0.5 and r["kind"] == "trans" and r["amp_mm"] == amp],
                    key=lambda r: r["f0"])
        ser["perfect knowledge, r_rot 0.5"] = ([r["f0"] for r in rs], [r["oracle_ratio"] for r in rs])
        panels[f"{amp:g} mm tremor"] = ser
    files.append(FG.lines_panels("fig_in_splits", "Rev H-B nose at the three grip splits (causal, Rev H tracker setting)", panels,
                                 "tremor frequency (Hz)", "ink error ratio", ylim=(0, 1.15), hline=1.0,
                                 note="SIM, test seeds 200-203. r_rot = share of the grip compliance that is rotational (unmeasured, EXP-I01). "
                                      "The perfect-knowledge ceiling changes little with the split (0.09-0.24 over all splits)."))
    # 3. calibrated band
    if S.get("calib"):
        cb = S["calib"]["test"]
        panels = {}
        for amp in (0.3, 1.0, 2.0):
            ser = {}
            rs = sorted([r for r in sm if r["tracker"] == "revh" and r["r_rot"] == 0.5 and r["kind"] == "trans" and r["amp_mm"] == amp],
                        key=lambda r: r["f0"])
            ser["Rev H tracker (open band)"] = ([r["f0"] for r in rs], [r["akf_ratio"] for r in rs])
            rc = sorted([r for r in cb if r["r_rot"] == 0.5 and r["amp_mm"] == amp], key=lambda r: r["f0"])
            ser["per-user calibrated band (+10 % error)"] = ([r["f0"] for r in rc], [r["causal"] for r in rc])
            ro = sorted([r for r in sm if r["tracker"] == "ship" and r["r_rot"] == 0.5 and r["kind"] == "trans" and r["amp_mm"] == amp],
                        key=lambda r: r["f0"])
            ser["perfect knowledge"] = ([r["f0"] for r in ro], [r["oracle_ratio"] for r in ro])
            panels[f"{amp:g} mm tremor"] = ser
        files.append(FG.lines_panels("fig_in_calib", "Per-user tremor-band calibration of the tracker (Rev H-B nose, r_rot 0.5)", panels,
                                     "tremor frequency (Hz)", "ink error ratio", ylim=(0, 1.15), hline=1.0,
                                     note="SIM, test seeds 200-203. The open-band tracker locks onto the second harmonic at 4-6 Hz; limiting the "
                                          "search to 0.75-1.3 x the user's calibrated frequency (set 10 % high here) removes the lock."))
    # 4. add-on dot plot
    sa = S["addon"]
    cats = {"nose (Rev H)": "nose", "nose + passive weight 27.8 g": "nose+weight", "nose + reaction mass, feed-forward": "nose+ff",
            "nose + reaction mass, FF after grip calibration": "nose+ff_cal", "nose + reaction mass, adaptive (AFC)": "nose+afc",
            "reaction mass alone, perfect knowledge": "ilc"}
    panels = {}
    for rr in [x for x in SPLITS if str(x) in sa["by_split"]]:
        b = sa["by_split"][str(rr)]
        panels[f"r_rot {rr}"] = {"8-12 Hz, 1-2 mm tremor": {k: b.get("band_8_12Hz_1_2mm", {}).get(v, np.nan) for k, v in cats.items()},
                                 "all translational conditions": {k: b.get("all_translational", {}).get(v, np.nan) for k, v in cats.items()},
                                 "wrist tremor 8 Hz": {k: b.get("wrist_8Hz", {}).get(v, np.nan) for k, v in cats.items() if v != "ilc"}}
    files.append(FG.dots_panels("fig_in_addon", "Rear-cap inertial module on top of the active nose (mean ink error ratio)", panels,
                                "ink error ratio", xlim=(0.2, 1.1),
                                note="SIM, test seeds 200-203. Ratio = ink error / ink error of Rev H without the module and without correction (lower is better). "
                                     "Reaction mass: 19.8 g tungsten, +/-2.75 mm, 5 Hz centring, +8 g coils/frame. Passive weight: the same 27.8 g fixed in the cap."))
    # 5. sweep
    sw = S["sweep"]["rows"]
    panels = {}
    for key, title in (("oracle", "perfect knowledge"), ("causal", "causal (Rev H tracker)")):
        ser = {}
        for fs in (30.0, 80.0, 150.0):
            rs = sorted([r for r in sw if r["servo_hz"] == fs], key=lambda r: r["travel_mm"])
            ser[f"servo {fs:g} Hz"] = ([r["travel_mm"] for r in rs], [r[key] for r in rs])
        panels[title] = ser
    files.append(FG.lines_panels("fig_in_sweep", "Nose travel and servo bandwidth (training seeds 300-303, r_rot 0.5)", panels,
                                 "usable tip travel radius (mm)", "ink error ratio (mean, 6-12 Hz, 1-2 mm)", ylim=(0, 1.0),
                                 note="SIM. The causal result is set by the tracker, not by the travel beyond 1.5 mm or the servo beyond 80 Hz."))
    # 6. tracker ParEGO
    if S.get("tracker_log"):
        pts = [(r["res"]["band_ratio"], r["res"]["false_corr_um"]) for r in S["tracker_log"] if r.get("res")]
        x0 = [r for r in S["tracker_log"] if r["tag"] == "x0"][0]["res"]
        tr = S["tracker"]["training"]
        files.append(FG.scatter_front("fig_in_tracker", "Rev H tracker setting by ParEGO (training seeds)", pts,
                                      {"chosen Rev H setting": (tr["band_ratio"], tr["false_corr_um"]),
                                       "shipped set": (x0["band_ratio"], x0["false_corr_um"])},
                                      "tremor band ratio (lower is better)", "false correction on tremor-free writing (um)",
                                      note="SIM, model H1 Rev H-B, training seeds 300-301 and glyph 330-331; 51 evaluations; pre-declared rule: "
                                           "lognormal distortion <= 15 um and glyph <= 30 um."))
    # 7. adjoint front
    if S.get("adjoint"):
        fr = S["adjoint"]["front"]
        pts = [(r["out"]["mass"] * 1e3, r["out"]["P"] * 1e3) for r in fr]
        ch = [r for r in fr if r["mu_mass"] == S["adjoint"].get("chosen_mu", 5.0)][0]
        files.append(FG.scatter_front("fig_in_adjoint", "Nose actuator: adjoint design front", pts,
                                      {"chosen (mass weight 5)": (ch["out"]["mass"] * 1e3, ch["out"]["P"] * 1e3)},
                                      "moving + magnet mass of the actuator set (g)", "copper loss for the design tip force (mW)",
                                      note="CALC: differentiable magnet-coil model (opt/inertial/adjoint.py), gradients by autograd checked by central "
                                           "differences; one point per mass weight 0.5-20.", muted_label="optimum for another mass weight"))
    # 8. neural training curve
    if S.get("neural"):
        hv = S["neural"]["history_val"]
        its = [h["it"] for h in hv]
        files.append(FG.lines_panels("fig_in_neural", "Neural reaction-mass controller: validation during BPTT fine-tuning",
                                     {"validation windows (seeds 316-317)": {"ratio with / without policy": (its, [h["val"]["ratio"] for h in hv])}},
                                     "iteration (-1 = after cloning the feed-forward)", "tip ratio (linear model)", ylim=(0.85, 1.02),
                                     note="SIM on the differentiable linear model; the policy is kept at its best validation iteration.", width=5.0))
    # 9. time-domain example
    files.append(time_example(akf_params))
    return files


def time_example(akf_params=None, seed=200, f0=10.0, amp=1.0e-3, t0=2.0, t1=3.0):
    """Page-x ink deviation from the tremor-free reference: Rev H without correction, nose (causal), nose + reaction mass."""
    from sim.handpen import model as HM
    from . import addon as AD
    from . import addon_eval as AE
    from . import figures as FG
    from . import scen as SC
    from . import tracker as TK
    d = RH.RevH()
    rm = AE.default_rm()
    cfg0, cfgR = RH.config_B(d), RH.config_B(d, device=rm)
    sc0, sc = SC.get(seed), SC.get(seed, SC.tremor(f0, amp))
    n = len(sc.t)
    ref0, refR = HM.run(sc0, cfg0, rec_hz=TK.REC_HZ), HM.run(sc0, cfgR, rec_hz=TK.REC_HZ)
    un = HM.run(sc, cfg0, rec_hz=TK.REC_HZ)
    dh, _, _ = TK.estimate(un, sc, seed=seed + 7000, body="pen", params=akf_params)
    rn = HM.run(sc, cfg0.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
    unR = HM.run(sc, cfgR, rec_hz=TK.REC_HZ)
    dhR, infoR, _ = TK.estimate(unR, sc, seed=seed + 7000, body="pen", params=akf_params)
    u = np.zeros((n, 3))
    u[:, 0:2] = TK.to_steps(AD.ff_phasor(dhR, infoR["f_est"], d, rm), n)
    rR = HM.run(sc, cfgR, uff=u, rec_hz=TK.REC_HZ)
    dh2, _, _ = TK.estimate(rR, sc, seed=seed + 7000, body="pen", params=akf_params)
    rnR = HM.run(sc, cfgR.replace(stage=True, stage_src=1), uff=u, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
    t = un["t"]
    m = (t >= t0) & (t < t1)
    k = np.where(m)[0][::4]
    ser = {"Rev H, no correction": (un.ink()[k, 0] - ref0.ink()[k, 0]) * 1e3,
           "active nose (causal)": (rn.ink()[k, 0] - ref0.ink()[k, 0]) * 1e3,
           "nose + rear reaction mass": (rnR.ink()[k, 0] - refR.ink()[k, 0]) * 1e3}
    return FG.time_series("fig_in_time", f"Ink deviation from the tremor-free line (page x), {f0:g} Hz / {amp * 1e3:g} mm hand tremor",
                          t[k], ser, "deviation (mm)",
                          note=f"SIM, model H1, test seed {seed}, r_rot 0.5, Rev H tracker setting (causal); 1 s of a 5 s run.")


# ================================================================== bill of materials and firmware sketch
def bom(geo: Dict) -> List[Dict]:
    """Bill of materials from the layout components (part, ledger, mass) plus the parts that are not drawn."""
    rows = []
    for c in geo["components"]:
        rows.append({"id": c["id"], "item": c["label"], "group": c["group"], "part": c.get("part", ""), "ledger": c.get("ledger", ""),
                     "make_or_buy": "make" if c.get("part", "").startswith("custom") or c.get("part", "") == "" else "buy",
                     "optional": c.get("optional", False), "mass_g": c.get("mass_g")})
    rows += [
        {"id": "drv", "item": "Coil drivers (nose 2 axes; module 2 axes)", "group": "electronics", "part": "TI DRV8214 (x2, x4 with the module)",
         "ledger": "AMF-37", "make_or_buy": "buy", "optional": False, "mass_g": None},
        {"id": "hall", "item": "Nose position sensor", "group": "sensor", "part": "TI TMAG5273 3-D Hall (I2C) at the arm magnet", "ledger": "OPT-45",
         "make_or_buy": "buy", "optional": False, "mass_g": None},
        {"id": "hall_rm", "item": "Module position sensor", "group": "sensor", "part": "TI TMAG5273 3-D Hall", "ledger": "OPT-45",
         "make_or_buy": "buy", "optional": True, "mass_g": None},
    ]
    return rows


FIRMWARE = {
    "rates_Hz": {"imu": 2000.0, "tracker": 2000.0, "nose_servo": 10000.0, "module_feedforward": 2000.0, "hall": 10000.0},
    "states": ["off", "idle (nose locked centred by the servo at low gain)", "calibrate (20-30 s: grip split probe, tremor frequency)",
               "write (pen down: tracker + nose servo; module feed-forward if fitted)", "lift (pen up: nose re-centres at 0.6 m/s max)",
               "fault (over-travel, over-current or low cell: nose to centre, coils off)"],
    "mcu": "nRF54L15 (128 MHz Cortex-M33, AMF-44)",
    "load_pct": {"akf_tracker": 6.2, "nose_servo_pid_10kHz": 1.0, "module_phasor_ff": 0.3, "neural_policy_if_used": None},
    "note": "AKF load from the tracker study (OPT-37 MFR + CALC); PID 10 kHz x ~60 cycles; phasor feed-forward 2 kHz x ~200 cycles (CALC)",
}


def stage_report(quick=False):
    """Assemble everything.  With --quick the quick-stage caches are used and the outputs go to results/opt/_cache/quick/
    (the final results, interface files, replay and evidence rows are left untouched)."""
    from . import evidence as EVD
    from . import figures as FG

    def st(name):
        if quick:
            q = _stage(name + "_quick")
            if q is not None:
                return q
        return _stage(name)

    qdir = os.path.join(CACHE, "quick")
    if quick:
        os.makedirs(qdir, exist_ok=True)
        FG.OUT = qdir
    S: Dict = {}
    grid = st("grid")
    S["arch"] = summarise_arch(grid)
    S["B"] = summarise_B(grid)
    ad = st("addon")
    S["addon"] = summarise_addon(ad)
    S["addon_decision"] = addon_decision(S["addon"])
    sw = st("sweep")
    S["sweep"] = summarise_sweep(sw) if sw else None
    cb = st("calib")
    S["calib"] = summarise_calib(cb) if cb else None
    nn = st("neural")
    S["neural"] = summarise_neural(nn) if nn else None
    S["tiers"] = _stage("tiers")
    S["adjoint"] = st("nose_adjoint")
    trk_path = os.path.join(OPT, "inertial_tracker_revh.json")
    S["tracker"] = json.load(open(trk_path)) if os.path.exists(trk_path) else None
    logp = os.path.join(CACHE, "inertial_tracker_parego.jsonl")
    S["tracker_log"] = [json.loads(l) for l in open(logp)] if os.path.exists(logp) else None
    prm = S["tracker"]["params"] if S["tracker"] else None
    # CMG / RM / weight screen (CALC, linear bounds) at the three splits
    from . import addon as AD
    from . import addon_eval as AE
    d = RH.RevH()
    rm = AE.default_rm()
    cm = AD.cmg_rear()
    screen = {"rm": {"label": rm.label, "added_g": (rm.m + rm.added_fixed) * 1e3},
              "cmg": {"label": cm.label, "added_g": cm.added_fixed * 1e3, "power": AD.cmg_power(cm)}, "bounds": {}}
    for rr in SPLITS:
        for A_ in (0.3e-3, 1.0e-3):
            screen["bounds"][f"r{rr}_{A_ * 1e3:g}mm"] = {
                "rm": AD.linear_bounds(d, rm, r_rot=rr, A=A_), "cmg": AD.linear_bounds(d, cm, r_rot=rr, A=A_),
                "weight": AD.linear_bounds(d, type("W", (), {"kind": "weight"})(), r_rot=rr, A=A_, extra_weight=rm.m + rm.added_fixed)}
    screen["label"] = "CALC (frictionless linear model, optimally phased single-frequency input within force/stroke or gimbal limits; optimistic)"
    S["screen"] = screen
    # figures
    figs = make_figures(S, akf_params=prm)
    if quick:
        out = {"quick": True, "summaries": {k: S[k] for k in ("arch", "addon_decision", "sweep", "calib", "neural") if S.get(k)},
               "figures": [os.path.relpath(f, ROOT) for f in figs]}
        provenance.write_json(os.path.join(qdir, "inertial_opt_quick.json"), out)
        return out
    # interface files and replay
    dec = S["addon_decision"]
    addon_geo = None
    if dec["include"]:
        import importlib.util
        spec = importlib.util.spec_from_file_location("revH_pen", os.path.join(ROOT, "mechanics", "cad", "revH_pen.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        addon_geo = mod.default_addon()
    tip = write_tip_params(final=True, addon_decision=dec, calib=S["calib"])
    lay = write_layout(addon=addon_geo, addon_recommended=dec["include"])
    from . import viz as VZ
    viz_metrics = VZ.write(akf_params=prm)
    geo = GE.layout(d, addon=addon_geo)
    # assembled results
    ms = RH.masses(d)
    cell = CT.CELLS[d.cell]
    P_tot = float(np.mean([r["B_P_cu_W"] for r in S["arch"]["by_condition"]])) + CT.ELECTRONICS["base_W"] + 0.012
    out = {
        "meta": provenance.metadata("SIMULATION + CALCULATION (Rev H active-nose pen with inertial options; model H1; nothing measured)",
                                    seeds={"test": [200, 201, 202, 203], "glyph_test": [210, 211, 212, 213], "train": list(range(300, 316)),
                                           "val": [316, 317, 318, 319], "glyph_train": [330, 331]},
                                    extra={"script": "opt/inertial/run_study.py", "doc": "docs/opt_inertial.md"}),
        "choice": {"architecture": "B", "inertial_module": dec,
                   "why": ("B (skid ring on the fixed front sleeve carries the writing force; the refill carrier tilts on a flexure gimbal) "
                           "beats A on every simulated criterion: perfect-knowledge ceiling 0.09-0.24 vs 0.15-0.77, coil power ~0.002 W vs "
                           "0.31-1.0 W (with a bias spring), no writing-force modulation (A: 0.3-0.7 N rms), and the tilt-plane correction "
                           "needs no pressing of the tip into the paper.")},
        "design": RH.describe(d) if hasattr(RH, "describe") else None, "masses_g": ms, "fit_checks": geo["fit_checks"],
        "power_battery": {"P_total_W_typical": P_tot, "cell": cell.name, "ledger": cell.src, "usable_Wh": cell.Wh,
                          "life_h": cell.Wh / P_tot, "module_W_max": dec["power_W"]["module_total_max_W"],
                          "life_h_with_module_worst": cell.Wh / (P_tot + dec["power_W"]["module_total_max_W"]),
                          "label": "CALC on SIM forces; base electronics 0.065 W ASSUMPTION"},
        "architecture": S["arch"], "rev_h_B": {k: v for k, v in S["B"].items() if k != "summary"}, "rev_h_B_table": S["B"]["summary"],
        "tracker_setting": {k: v for k, v in (S["tracker"] or {}).items() if k != "meta"},
        "calibrated_band": S["calib"], "sweep": S["sweep"], "inertial_module": S["addon"], "inertial_screen": screen,
        "neural": S["neural"], "tiers_T0_T2": S["tiers"], "adjoint_nose": S["adjoint"], "firmware": FIRMWARE, "bom": bom(geo),
        "replay": {"files": ["results/opt/viz_inertial_opt.json", "results/opt/viz_inertial_opt_1mm.json"], "metrics": viz_metrics},
        "figures": [os.path.relpath(f, ROOT) for f in figs],
        "interfaces": ["results/revH/tip_params.json", "results/revH/layout.json"],
    }
    provenance.write_json(os.path.join(OPT, "inertial_opt.json"), out)
    rows = EVD.static_rows() + EVD.study_rows(out)
    EVD.write(rows, os.path.join(OPT, "inertial_evidence_rows.csv"))
    return out
