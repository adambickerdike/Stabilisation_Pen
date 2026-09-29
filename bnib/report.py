"""results/bnib/bnib.json, the figures with CSV twins, the evidence rows and docs/balanced_nib.md from the stages' outputs.

Everything reported is CALC or SIM on PROPOSED DESIGNS with LIT/MFR/ASSUMPTION inputs (labels on every number); nothing
was built or measured."""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from . import BUILD, DOC, RESULTS, provenance, write_json
from .labels import C1S, CONTACT, DRIVE, FAT, GRIP, SENSORS, THERMAL, val

D2R = math.pi / 180.0
TH = ("35.0", "50.0", "60.0", "75.0")


def _f(x, nd=2, unit=""):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "-"
    if isinstance(x, (int, np.integer)):
        return f"{x}{unit}"
    if abs(x) >= 100:
        return f"{x:.0f}{unit}"
    return f"{x:.{nd}f}{unit}"


def _mw(x, nd=1):
    return "-" if x is None else _f(x * 1e3, nd)


# ------------------------------------------------------------------------------------------------ cards
TITLES = {
    "a_long_arm": "(a) longer-arm gimbal (Rev H layout, lever 1.32), no balance",
    "b_bias": "(b) tilt/roll-scheduled bias spring (positioner, no clutch)",
    "b_bias_epm": "(b') scheduled bias with an electro-permanent clutch (released at every lift)",
    "c_counterface": "(c) contact-driven counter-face, IMU-scheduled (two slow positioners)",
    "c_counterface_cam": "(c') counter-face with a slide cam for tilt and one roll positioner",
    "c_counterface_keyed": "(c'') counter-face with a slide cam and a keyed grip (no motors)",
    "d_low_ink": "(d) lower ink force (0.075 N), no balance",
    "e_steep_tip": "(e) steeper writing tip (35 deg bend, short custom cartridge)",
    "f_translation": "(f) two-axis flexure translation stage, no balance",
    "g_coarse_fine": "(g) coarse/fine: +-0.5 mm counter-face nib + study W's pivot collar",
    "h_piezo": "(h) piezo bender fine stage (PICMA-class plates)",
    "h_piezo_c": "(h') piezo fine stage + counter-face",
}


def card(r: Dict) -> Dict:
    rows = {f"{x['theta_deg']:.1f}": x for x in r["rows"]}
    pw = {}
    for t in TH:
        x = rows.get(t, {})
        pw[t] = {k: x.get(k) for k in ("P_hold_W", "P_penup_W", "P_friction_W", "P_dynamic_W", "P_mean_W", "P_mean_roll_max_W",
                                       "P_hold_roll_max_W", "static_N", "loaded_usable_mm", "hold_N")}
    fam = r["family"]
    fat = r.get("fatigue", {})
    fx = r.get("flexure") or {}
    c = {"key": r["key"], "title": TITLES.get(r["key"], r["title"]), "grip": r["grip"], "family": fam,
         "balance": r["balance"], "power_by_tilt": pw, "P_cont_W": r["P_cont_W"], "P_cont_worst_W": r["P_cont_worst_W"],
         "P_cont_duty_B_W": r.get("P_cont_duty_B_W"), "duty_B_feasible": r.get("duty_B_feasible"), "P_peak_W": r.get("P_peak_W"),
         "travel_design_mm": r["travel_mm"], "travel_under_load_mm": r["travel_under_load_mm"], "Km_tip": r.get("Km_tip"),
         "Km_tip_min": r.get("Km_tip_min"), "m_eff_tip_g": r["m_eff_tip_g"], "k_tip_N_m": r.get("k_tip_N_m"),
         "bandwidth_Hz": r["bandwidth_Hz"], "modes": r.get("modes"), "T_coil_C": r.get("T_coil_C"), "T_skin_C": r["T_skin_C"],
         "governor_min": r.get("governor_authority_min"), "mass_g": r["mass_g"], "od_mm": r["od_mm"], "length_mm": r["length_mm"],
         "com_mm": r["com_mm"], "battery_h": r["battery_h"], "fits_bore": r.get("fits_bore"), "duty_feasible": r.get("duty_feasible"),
         "fatigue": {k: fat.get(k) for k in ("goodman_SF_full_travel", "static_SF_stop", "Kt", "material", "cycles", "buckling_SF",
                                              "buckling_N", "pull_N", "note")},
         "strain_stop": fx.get("strain_stop", fat.get("strain_stop")), "stress_stop_MPa": fx.get("stress_stop_MPa"),
         "shock": r.get("shock"), "sensing": r.get("sensing"), "manufacture": r.get("manufacture"),
         "failure_state": r.get("failure_state"), "tolerance_mc": r.get("tolerance_mc"),
         "P_35_vs_Fs": r.get("P_mean_35deg_vs_Fs"), "piezo": r.get("piezo"), "collar": None}
    c["verdict"] = verdict(c)
    return c


def verdict(c: Dict) -> str:
    bad = []
    if c.get("fits_bore") is False:
        bad.append("does not fit the bore")
    if c["travel_under_load_mm"] is not None and c["travel_under_load_mm"] < 0.3:
        bad.append(f"no usable travel under the 35 deg load ({c['travel_under_load_mm']:.2f} mm)")
    if c["P_cont_W"] > 0.3:
        bad.append(f"continuous power {c['P_cont_W']:.2f} W")
    if c["T_skin_C"] is not None and c["T_skin_C"] >= 40.9:
        bad.append("skin at the 41 degC governor limit")
    if bad:
        return "NOT FEASIBLE: " + "; ".join(bad)
    P = c["P_cont_W"]
    tag = "feasible"
    if P < 0.02:
        tag = "feasible, low power"
    out = f"{tag}: {P * 1e3:.1f} mW continuous (duty A), {c['travel_under_load_mm']:.2f} mm under load, {c['mass_g']:.0f} g"
    if c["family"] != "piezo":
        hold = max(max((v.get("P_hold_W") or 0.0), (v.get("P_hold_roll_max_W") or 0.0)) for v in c["power_by_tilt"].values())
        if hold > 0.1:
            out += f"; FAILS REQ-RVJ-N10 (holding {hold * 1e3:.0f} mW at the worst tilt > 0.1 W)"
        else:
            out += f"; meets REQ-RVJ-N10 (holding <= {hold * 1e3:.1f} mW)"
    if c["key"] == "g_coarse_fine":
        out += "; the collar's own power is study W's"
    return out


# ------------------------------------------------------------------------------------------------ decision, requirements
def decision_draft(res: Dict) -> Dict:
    rec = res["recommended"]
    return {
        "id": "DEC-050 (DRAFT, proposed by study B; resolves DEC-046; the lead decides)",
        "title": "The mechanism that carries the static side load (DEC-046): a two-axis translation nib on four wires with "
                 "the contact-driven counter-face; the C1S nose is not carried forward",
        "decision": [
            "Adopt the B1 nib (candidate c) as the fast core of the first prototype and of gates G3-G4: +-1.0 mm two-axis "
            "translation of the refill on four Ti-6Al-4V wires, a moving-coil annular axial-gap checkerboard (N52 poles and "
            "1010 plates on the handle, coils on the carrier), a filtered position servo, and the counter-face that "
            "balances the paper's push at the refill's rear end.",
            "Do not carry the C1S short-arm nose (DEC-036) forward as the fast core: its static side load costs 4.7 / 1.6 / "
            "0.17 W at 35 / 50 / 75 deg (review, reproduced CALC); a longer arm (candidate a, Rev H's layout) cuts that only "
            f"to {rec['a_P_cont_mW']:.0f} mW at +-0.5 mm (it runs out of force at +-1 mm with Km x 0.7) and carries "
            "5-15 g of tip-equivalent moving mass.",
            f"REQ-RVJ-N10 (<= 0.1 W steady coil heat with the ball on the paper over 35-75 deg): B1 holds with at most "
            f"{rec['hold_max_mW']:.1f} mW (worst tilt and roll, CALC; {rec['hold_max_km07_mW']:.1f} mW at Km x 0.7).",
            "Fallbacks if the counter-face fails its bench test (EXP-B22 with EXP-J17): first the EPM-clutched scheduled bias "
            f"(b': {rec['bepm_hold_max_mW']:.0f} mW holding at worst, CALC); the same nib unbalanced (f) holds "
            f"{rec['f_hold_max_mW']:.0f} mW at 35 deg and so meets REQ-RVJ-N10 only above about "
            f"{rec['f_theta_ok_deg']:.0f} deg or with a lower ink force.",
            "Large tremor (> 1 mm) is not the nib's job: it goes to study W's collar / whole-pen shifting (candidate g "
            "couples a +-0.5 mm counter-face nib to W's collar).",
            "Slim core (12-16 mm): voice coils around a D1 refill do not fit (candidates a-g infeasible at 14 mm); the "
            "piezo bender stage (h, h') is the slim branch, a trade study, not the first prototype.",
            "Freeze the refill spring force only after gate G1 measures the minimum reliable ink force (EXP-B20 / EXP-T02). "
            "The counter-face balances whatever force G1 picks, but the ball's drag grows with it: B1's continuous power is "
            f"about {rec.get('P_at_Fs', {}).get('0.15', float('nan')):.0f} mW at 0.15 N, "
            f"{rec.get('P_at_Fs', {}).get('0.3', float('nan')):.0f} mW at 0.3 N and "
            f"{rec.get('P_at_Fs', {}).get('0.69', float('nan')):.0f} mW at 0.69 N (CALC): G1 sets the power and thermal budget.",
        ],
        "because": [
            f"Balance: the residual static load is {res['bq_residual_mN']:.1f} mN mean ({res['bq_ratio']:.0%} of the "
            "unbalanced load) over 35-75 deg, all rolls, two inks, six papers, +-20 % spring force and the IMU errors "
            "(CALC, Monte Carlo); it vanishes on lift.",
            f"Power: {rec['P_cont_mW']:.1f} mW continuous at duty A with the image-method Km ({rec['P_cont_km085_mW']:.1f} mW at "
            f"0.85 x, {rec['P_cont_km07_mW']:.1f} mW at 0.7 x; 35 deg: {rec['P35_mW']:.1f} mW) against {rec['f_P_cont_mW']:.0f} "
            "mW for the same nib unbalanced (CALC).",
            f"Travel +-{rec['travel_mm']:.2f} mm under the 35 deg load at Km x 0.7, a hot coil and 3.3 V; tip-equivalent "
            f"moving mass {rec['m_eff_g']:.1f} g; first parasitic mode {rec['f_par_Hz']:.0f} Hz; wire Goodman safety factor "
            f"{rec['SF']:.1f} at full travel for 43.2 M cycles (CALC).",
            "A moving coil keeps the magnetic gap constant: no negative stiffness and no pull on the suspension.",
            "Unpowered it writes like a normal pen (centred by its wires, the face still balancing).",
        ] + _sim_because(res.get("sim") or {}),
        "unproven": rec["unproven"],
        "revisit_if": [
            "EXP-B22 measures a residual side load > 25 % of F_s cot(theta) or a face that does not release on lift within "
            "20 ms (-> candidate f or b').",
            "EXP-B23 measures Km < 0.7 x the image-method value (-> larger poles; the 24 mm bore is then the limit).",
            f"EXP-B20 finds a minimum reliable force above about 0.3 N (-> B1's power passes "
            f"{rec.get('P_at_Fs', {}).get('0.3', float('nan')):.0f} mW and reaches about "
            f"{rec.get('P_at_Fs', {}).get('0.69', float('nan')):.0f} mW at 0.69 N through the ball's drag: lower-friction "
            "inks, a larger Km or a better thermal path become the drivers).",
            "EXP-B25 wire coupons fail before 43.2 M cycles at the stop travel.",
            "The sim2 ranking reverses when the page sensor is measured on paper (EXP-T04 / EXP-B32).",
        ],
        "supersedes_or_affects": ["DEC-036 (C1S nose)", "DEC-041 (the nose's Km and stiffness claims)", "DEC-044 / DEC-045 "
                                  "(Rev J / J.1 battery and heat claims stay suspended until the B1 numbers are measured)"],
    }


def _sim_because(sim: Dict) -> List[str]:
    """One SIM line for the decision draft, read off the sim cards and sim2j's Rev J reference (no new numbers)."""
    c = (sim.get("cards") or {}).get("B1") or {}
    if not c:
        return []
    by = c.get("by_cell") or {}
    ref = (sim.get("sim2j_revJ_reference") or {}).get("cells") or {}
    P_j = [v["P_nose_W"] for v in ref.values() if v.get("P_nose_W")]
    th = c.get("thermal_35deg") or {}
    g = lambda d, k: d.get(k) if d else None
    fmt = lambda x, nd=2: "-" if x is None else f"{x:.{nd}f}"
    r = lambda cell, d=by: fmt(g(d.get(cell), "ratio_mean" if d is by else "ratio_nose"))
    s = (f"Simulation (SIM; sim2, {c.get('n_writers')} synthetic writers, the project's frozen tracker, a DeltaPen-calibrated "
         f"page sensor): with the tracker B1 leaves {r('ET 8 Hz 1 mm')} / {r('ET 12 Hz 1 mm')} of the tremor's ink error at "
         f"8 / 12 Hz 1 mm, the Rev J C1S nose {r('ET 8 Hz 1 mm', ref)} / {r('ET 12 Hz 1 mm', ref)} in sim2j's runs; at 8 Hz "
         f"2 mm {r('ET 8 Hz 2 mm')} against {r('ET 8 Hz 2 mm', ref)} (B1's +-1 mm reach clips); B1 draws "
         f"{fmt(c.get('P_nib_mW_tremor_mean'), 1)} mW, the nose {fmt(sum(P_j) / len(P_j) if P_j else None, 1)} W; "
         f"tremor-free writing moved {fmt(c.get('clean_moved_um_mean'), 1)} um")
    if th:
        s += (f"; at 35 deg with 2 mm tremor for 30 min the coil reaches {fmt(th['T_after_30min'][0], 1)} degC and the skin "
              f"{fmt(th['T_after_30min'][1], 1)} degC ("
              + ("governor idle" if (th.get("gov_min_hot") or 0.0) >= 0.999 else f"governor authority down to {fmt(th.get('gov_min_hot'))}")
              + ")")
    return [s + "."]


def requirements(res: Dict) -> List[Dict]:
    rec = res["recommended"]
    b1 = ((res.get("sim") or {}).get("cards") or {}).get("B1") or {}
    th = b1.get("thermal_35deg") or {}
    face_now = ("CALC (design rule)" + (f"; SIM: face engaged {100 * b1['face_engaged_in_contact_mean']:.1f} % of the contact "
                f"time, {100 * b1['face_engaged_penup_mean']:.1f} % of the pen-up time" if b1.get("face_engaged_in_contact_mean")
                is not None and b1.get("face_engaged_penup_mean") is not None else "; SIM face engagement"))
    ls = (((res.get("sim") or {}).get("lift_cutoff_sensitivity") or {}).get("designs") or {}).get("B1") or {}
    lift_now = (f"SIM: with a 0.8 mm cut-off B1's tracker left {ls['nose']['ratio_lift08']:.2f} of the tremor instead of "
                f"{ls['nose']['ratio_lift2']:.2f}, perfect knowledge {ls['oracle']['ratio_lift08']:.2f} instead of "
                f"{ls['oracle']['ratio_lift2']:.2f}" if ls.get("nose") and ls.get("oracle") else "MFR OPT-54: 2-3 mm")
    skin_now = (f"SIM + CALC: B1 {th['T_after_30min'][1]:.1f} degC skin, {th['T_after_30min'][0]:.1f} degC coil after 30 min "
                f"({1e3 * th['P_nib_mean_W']:.0f} mW)" if th else "CALC/SIM (bnib.json thermal)")
    R = [
        ("REQ-BNIB-001", "Static side load left on the nib while writing", "<= 10 % of F_s cot(theta), mean over 35-75 deg and "
         "all rolls; <= 25 % at the 95th percentile", f"CALC {res['bq_ratio']:.0%} mean", "EXP-B22", "G2"),
        ("REQ-BNIB-002", "Balance released on lift", "pen-up residual <= 10 % of the contact balance force within 20 ms of lift; "
         "full balance within 0.25 mm of refill travel at touchdown", face_now, "EXP-B22", "G2"),
        ("REQ-BNIB-003", "Usable travel under load", ">= +-1.0 mm at 35 deg, 12 Hz, coil +90 K, 3.3 V, Km x 0.7",
         f"CALC {rec['travel_mm']:.2f} mm", "EXP-B26", "G3"),
        ("REQ-BNIB-004", "Continuous nib power (duty A: 0.2 mm rms, 8 Hz, 70 % contact); holding coil heat per "
         "REQ-RVJ-N10", "<= 20 mW mean over 35-75 deg; holding <= 0.1 W at every tilt and roll (REQ-RVJ-N10)",
         f"CALC {rec['P_cont_mW']:.1f} mW; holding <= {rec['hold_max_mW']:.1f} mW", "EXP-J17; EXP-B27; EXP-B29", "G4"),
        ("REQ-BNIB-005", "Tip-equivalent moving mass", "<= 4.5 g", f"CALC {rec['m_eff_g']:.2f} g", "EXP-B26", "G3"),
        ("REQ-BNIB-006", "First parasitic mode of the loaded nib (ball free and stuck)", ">= 120 Hz (bandwidth >= 40 Hz)",
         f"CALC {rec['f_par_Hz']:.0f} Hz", "EXP-B26", "G3"),
        ("REQ-BNIB-007", "Suspension fatigue", "Goodman safety factor >= 1.5 at the stop travel for 43.2 M cycles, clamp Kt "
         "included", f"CALC {rec['SF']:.2f}", "EXP-B25", "G2"),
        ("REQ-BNIB-008", "Ink force at the ball", "set value +-20 % over 35-75 deg with the balance engaged", "CALC N = F_n",
         "EXP-B20; EXP-B22", "G1"),
        ("REQ-BNIB-009", "Nib position sensing and a filtered servo (with REQ-RVJ-C04)", "<= 2 um rms tip-referred at 1 kHz with "
         "the coils driven (calibrated cross-talk); the servo acts on an observer's estimate, never on the raw Hall reading",
         f"CALC {rec['hall_um']:.2f} um; SIM filtered servo", "EXP-B24", "G2"),
        ("REQ-BNIB-010", "Skin temperature", "<= 41 degC in a 30 degC room at 35 deg with 2 mm tremor for 30 min (governor in "
         "the loop)", skin_now, "EXP-B29", "G4"),
        ("REQ-BNIB-011", "Unpowered state", "the nib centred by its suspension within 0.1 mm and the pen writes like a normal pen",
         "CALC (failure state)", "EXP-B27", "G4"),
        ("REQ-BNIB-012", "Drop", "1 m onto a hard floor: wires elastic (axial stops <= 20 um), face and positioners undamaged",
         "CALC (flexure.shock)", "EXP-B25", "G2"),
        ("REQ-BNIB-013", "Interface", "the nib's physical interface lives in config/nib.yaml (versioned); simulators and other "
         "studies read it", "PROPOSED", "-", "all"),
        ("REQ-BNIB-014", "Minimum ink force known before F_s is frozen", "per tip type and paper (six papers), 35-75 deg, "
         "5-60 mm/s", "UNKNOWN (no source gives it)", "EXP-B20 (EXP-T02)", "G1"),
        ("REQ-BNIB-015", "Face orientation sensing", "IMU tilt error <= 1 deg and roll error <= 2 deg (1 sigma) while writing",
         "ASSUMPTION", "EXP-B28", "G2"),
        ("REQ-BNIB-016", "Refill guide friction", "guide friction coefficient <= 0.01 (a ball or roller guide): the counter-face's "
         "couple loads the two bushings with 0.6-0.75 N, and the slide friction acts across the pen as h cot(theta)",
         "ASSUMPTION mu_g 0.005", "EXP-B22", "G2"),
        ("REQ-BNIB-017", "Page sensor lift range (with the page sensor's own requirements)", "keeps the page through the lifts "
         "between strokes: lift cut-off >= 2 mm above the writing height (OPT-54 class)", lift_now, "EXP-B32", "G4"),
    ]
    return [{"id": a, "title": b, "requirement": c, "status_now": d, "verified_by": e, "gate": f} for a, b, c, d, e, f in R]


def experiments() -> List[Dict]:
    E = [
        ("EXP-B20", "G1", "Minimum reliable ink force per tip type (D1 oil x2, gel, rollerball, fineliner) on six papers, "
         "35-75 deg, 5-60 mm/s: gap fraction vs normal force", "study M rig R9 + scanner (merges into EXP-T02)",
         "the F_s set point and its tolerance in config/nib.yaml"),
        ("EXP-B21", "G1", "Friction vector map mu(N, v, ink, paper) and the static side load measured apart (axial cell + "
         "plate under the paper)", "rig R9 (EXP-T01)", "the friction map in config/nib.yaml; the balance's fluctuation"),
        ("EXP-B22", "G2", "Counter-face bench: residual side load at the carrier over tilt 35-75 deg, roll 0-360 deg, F_s "
         "0.1-0.7 N, three refills; release on lift and return at touchdown (high-speed camera + carrier force cell); "
         "extends EXP-J17 (static load and holding power at 35/50/75 deg for C1S and the balanced nib)",
         "new fixture on rig R12 (tilting stage, 6-axis cell under the carrier)", "adopt c / fall back to b' or f"),
        ("EXP-B23", "G2", "Moving-coil actuator coupon: Km(x, y) over +-1.2 mm, cross-coupling, keeper pull, R, L, Km(T)",
         "rig R12 (EXP-T07 / EXP-T08)", "pole size; the firmware force map; Km x 0.7-1.0 resolved"),
        ("EXP-B24", "G2", "Nib Hall sensing with the coils driven (cross-talk vs current and PWM), 23-60 degC",
         "rig R12 (EXP-T09)", "sensor placement and the observer's noise model"),
        ("EXP-B25", "G2", "Wire suspension coupons: stiffness, clamp Kt, accelerated fatigue at the stop travel to 43.2 M "
         "cycles (and to failure on spares), 1 m drop with the axial stops", "shaker + drop fixture (new)",
         "wire diameter, clamp design, stops"),
        ("EXP-B26", "G3", "One-axis then two-axis loaded nib: disturbance rejection and bandwidth in contact at 35/50/75 deg",
         "rig R13 (EXP-T10)", "servo and observer gains; REQ-BNIB-003/005/006"),
        ("EXP-B27", "G4", "Two-axis nib with the counter-face on the tremor rig: tremor left at the tip, clean writing "
         "changed, power, 500 touchdowns, roll +-20 deg", "rig R13 (EXP-T13)", "G4 pass/fail; sim2 calibration"),
        ("EXP-B28", "G2", "IMU tilt and roll estimates while writing (20 writers' recorded strokes replayed on a robot, or "
         "study R's recordings) against motion capture, on 0 / 10 / 20 deg writing slopes (the IMU sees gravity, not the page)",
         "rig R13 + camera", "the face schedule's error budget; whether a slope setting or the slide cam is needed"),
        ("EXP-B29", "G4", "Long thermal run with the governor: 30-60 min at the design duty and at 35 deg / 2 mm in a "
         "30 degC room", "rig R13 in the chamber (EXP-T15)", "REQ-BNIB-010; battery time"),
        ("EXP-B30", "G2 (optional)", "Roll spread of a keyed (triangular) grip across 10 writers", "motion capture",
         "whether the no-motor variant c'' is good enough"),
        ("EXP-B31", "G3 (slim branch)", "Piezo bender stage coupon: force-travel line, loaded resonance, drive power with a "
         "charge-recovery driver", "pencil rig (EXP-Q04 / EXP-Q05)", "the slim core's feasibility"),
        ("EXP-B32", "G4", "Page sensor on paper with the nib moving: DeltaPen-style window errors, scale, drift, and the lift "
         "height at which it loses and regains the page (REQ-BNIB-017)",
         "rig R10 (EXP-T04)", "replace the DeltaPen-calibrated model in sim2"),
    ]
    return [{"id": a, "gate": b, "what": c, "rig": d, "decides": e} for a, b, c, d, e in E]


def bom(res: Dict) -> List[Dict]:
    rec = res["recommended"]
    x = rec.get("x") or {}
    w = x.get("w", 5.4e-3) * 1e3
    tm = x.get("t_m", 3.5e-3) * 1e3
    tc = x.get("t_c", 0.8e-3) * 1e3
    wd = x.get("wire_d", 0.148e-3) * 1e3
    wl = x.get("wire_L", 33e-3) * 1e3
    B = [
        ("refill", "ISO 12757-1 type D1 ballpoint refill (brand chosen in G1)", 1, "LIT CON-22", "any compliant D1"),
        ("refill end cap", "PEEK cap with a 3 mm Si3N4 ball (rolls on the face)", 1, "ASSUMPTION; AMF-24", "custom"),
        ("carrier", "Ti-6Al-4V tube 3.2/2.5 mm with a rolling guide for the refill at two stations (friction <= 0.01, "
         "REQ-BNIB-016; e.g. three miniature rollers per station), the coils' hub and the wire flange", 1, "AMF-21; ASSUMPTION",
         "custom"),
        ("suspension wires", f"Ti-6Al-4V (grade 5) wire {wd:.3f} mm, free length {wl:.1f} mm, laser-welded clamps (0.1 mm edge "
         "radius)", 4, "AMF-20; AMF-21", "custom from wire stock"),
        ("moving coils", f"two flat layers {tc:.2f} mm, self-bonding 0.10 mm magnet wire on a 0.1 mm polyimide former, "
         "R 2.5 ohm per axis", 2, "AMF-29; AMF-30", "custom"),
        ("pole magnets", f"NdFeB N52 cuboids {w:.2f} x {w:.2f} x {tm:.2f} mm, axially magnetised", 4, "MFR AMF-139",
         "custom size"),
        ("back plate and keeper", "AISI 1010 laser-cut plates (Hiperco 50A option: AMF-140)", 2, "ASSUMPTION", "custom"),
        ("nib position sensor", "TI TMAG5170 3-D Hall (A1 range) + 1 mm N52 cube", 1, "MFR OPT-44 / OPT-53", "TMAG5170"),
        ("coil drivers", "TI DRV8214 H-bridge with current regulation, one per axis", 2, "MFR AMF-37", "DRV8214"),
        ("face positioners", "New Scale SQL-RV-1.8 SQUIGGLE piezo screw motors (zero holding power; volume-only supply: "
         "micro-stepper lead screws as the prototype fallback)", 3, "MFR AMF-15 / AMF-106", "SQL-RV-1.8"),
        ("counter-face", "hardened steel disc 6 mm on a 301 FH cross-strip flexure; constant-force strip spring; follower "
         "stop on a lead screw", 1, "AMF-20; EXP-N06", "custom"),
        ("IMU", "ST LSM6DSV16X (on the base board)", 1, "MFR OPT-37", "LSM6DSV16X"),
        ("page sensor", "optical navigation die near the tip (PixArt PMW3610-class; DeltaPen used two P3040)", 1,
         "MFR OPT-61; LIT OPT-01", "to select (EXP-T04)"),
        ("heat spreader", "Panasonic PGS graphite sheet in the shell wall, 30 mm", 1, "MFR AMF-158", "PGS"),
        ("cell", "EEMB LIR14500 Li-ion 750 mAh (base pen)", 1, "MFR AMF-80", "LIR14500"),
        ("shell", "PEEK 450G tube 24 mm, 1 mm wall (base pen)", 1, "MFR AMF-24", "VICTREX 450G"),
    ]
    return [{"item": a, "description": b, "qty": c, "evidence": d, "part_number": e} for a, b, c, d, e in B]


# ------------------------------------------------------------------------------------------------ assemble
def assemble(S: Dict) -> Dict:
    loads, cands, opt, sim = S.get("loads") or {}, S.get("candidates") or {}, S.get("optimise") or {}, S.get("sim") or {}
    cards = {k: card(v) for k, v in cands.items() if "|" in k}
    bq = loads.get("balance_quality", {})
    cf = bq.get("c_counterface imu2", {})
    from . import interface as IF
    from . import candidates as CD
    d, x = IF.recommended_design()
    ev = CD.evaluate(d, detail=True)
    f_par = min([v for v in (ev.get("modes") or {}).get("pen_up_Hz", [])[1:2] + (ev.get("modes") or {}).get("ball_stuck_Hz", [])[1:2]]
                + [ev["modes"].get("violin_Hz", 1e9)])
    f_best = None
    a_best = None
    for pid, pr in (opt.get("problems") or {}).items():
        for run in pr.get("runs", []):
            if pid == "pen24_f" and abs(run["eps_T_mm"] - 1.0) < 1e-6 and run["feasible"]:
                f_best = run["best"]
            if pid == "pen24_a" and abs(run["eps_T_mm"] - 0.5) < 1e-6:
                a_best = run["best"]
    def hold_max(r):
        return max(max(row.get("P_hold_roll_max_W") or 0.0, row.get("P_hold_W") or 0.0) for row in r["rows"]) * 1e3
    from dataclasses import replace as _rp
    ev07 = CD.evaluate(_rp(d, km_scale=0.7), detail=False, fast=False)
    ev085 = CD.evaluate(_rp(d, km_scale=0.85), detail=False, fast=True)
    fcard = cands.get("pen24|f_translation")
    bcard = cands.get("pen24|b_bias_epm")
    f_theta_ok = None
    if fcard:
        for row in sorted(fcard["rows"], key=lambda z: z["theta_deg"]):
            if max(row.get("P_hold_roll_max_W") or 0.0, row.get("P_hold_W") or 0.0) <= 0.1:
                f_theta_ok = row["theta_deg"]
                break
    rec = {"key": "c_counterface", "grip": "pen24", "x": x, "P_cont_mW": ev["P_cont_W"] * 1e3,
           "hold_max_mW": hold_max(ev), "hold_max_km07_mW": hold_max(ev07),
           "P_cont_km085_mW": ev085["P_cont_W"] * 1e3, "P_cont_km07_mW": ev07["P_cont_W"] * 1e3,
           "f_hold_max_mW": hold_max(fcard) if fcard else float("nan"), "bepm_hold_max_mW": hold_max(bcard) if bcard else float("nan"),
           "f_theta_ok_deg": f_theta_ok if f_theta_ok is not None else float("nan"),
           "P35_mW": ev["P_mean_W_by_theta"][35.0] * 1e3, "travel_mm": ev["travel_under_load_mm"], "m_eff_g": ev["m_eff_tip_g"],
           "f_par_Hz": f_par, "SF": ev["fatigue"]["goodman_SF_full_travel"], "hall_um": ev["sensing"]["nib_hall_noise_um_1kHz"],
           "mass_g": ev["mass_g"], "od_mm": ev["od_mm"], "length_mm": ev["length_mm"], "battery_h": ev["battery_h"],
           "T_skin_C": ev["T_skin_C"], "T_coil_C": ev["T_coil_C"], "Km_tip": ev["Km_tip"], "k_tip": ev["k_tip_N_m"],
           "f_P_cont_mW": (f_best["P_cont_W"] * 1e3) if f_best else cards.get("pen24|f_translation", {}).get("P_cont_W", 0) * 1e3,
           "a_P_cont_mW": (a_best["P_cont_W"] * 1e3) if a_best else cards.get("pen24|a_long_arm", {}).get("P_cont_W", 0) * 1e3,
           "a_travel_mm": a_best["travel_mm"] if a_best else None,
           "eval": {k: v for k, v in ev.items() if k not in ("thermal",)},
           "thermal_trace": (ev.get("thermal") or {}).get("trace"),
           "unproven": [
               "The minimum reliable ink force (no source gives it; 0.15 N is 4.6 x below the lowest manufacturer test "
               "load found): EXP-B20.",
               "Km: image-method magnetics is an upper bound; the design is checked at 0.7 x (EXP-B23).",
               "That the counter-face mechanism works as modelled: a face that stays parallel to the paper from IMU "
               "estimates, a follower stop that releases on lift, rolling contact friction 0.005 (EXP-B22, EXP-B28).",
               "The friction map's load and speed shapes and the paper spread (ASSUMPTION; EXP-B21).",
               "Wire fatigue with real clamps (Kt 1.3-2.5 assumed; EXP-B25).",
               "Every tremor result is a SIMULATION on synthetic writers and tremor with a DeltaPen-calibrated page sensor "
               "measured on a tablet, not paper (EXP-B27, EXP-B32).",
               "The squiggle motors' availability (volume-only supply: micro-stepper fallback).",
           ]}
    # nonlinear flexure rigour and magnetics of the recommended design (CALC)
    from . import flexure as FX
    rec["tolerance_mc"] = FX.tolerance_mc(d.wire, d.travel, d.travel + 0.2e-3, ev["hw"]["m_move"], n=2000)
    rec["flexure"] = ev.get("flexure")
    rec["modes"] = ev.get("modes")
    rec["shock"] = ev.get("shock")
    try:
        km = IF.km_table(d)
        rec["km_map"] = {k: km[k] for k in ("xs_mm", "Km_grid", "Km0", "Km_min", "Km_max", "variation", "cross_max", "Fz_per_AT_max")}
    except Exception as ex:                                  # magpylib missing: the report still builds
        rec["km_map"] = {"error": repr(ex)}
    try:
        from . import magnetics as MG
        s_ = d.travel + 0.2e-3
        g_ = MG.ChkGeom(w=d.w, e=(CD.A.R_CARRIER + s_ + 0.3e-3) / math.sqrt(2), t_m=d.t_m, t_x=d.t_c, t_y=d.t_c, s=s_)
        rec["keeper_pull_N"] = MG.keeper_pull(g_)["pull_N"]
    except Exception:
        rec["keeper_pull_N"] = None
    from . import loads as LD
    rec["sim2j_power"] = LD.sim2j_power()
    rec["guide_friction"] = guide_friction(d, ev)
    rec["P_at_Fs"] = {}
    for F in (0.15, 0.3, 0.69, 1.0):
        dF = _rp(d, F_s=F)
        dF.balance = _rp(d.balance, F_s_nom=F)
        rec["P_at_Fs"][f"{F:g}"] = CD.evaluate(dF, detail=False, fast=True)["P_cont_W"] * 1e3
    res = {"cards": cards, "recommended": rec, "bq_residual_mN": cf.get("residual_contact_mean_N", float("nan")) * 1e3,
           "bq_ratio": cf.get("balance_ratio_mean", float("nan")), "sim": sim}
    res["decision"] = decision_draft(res)
    res["requirements"] = requirements(res)
    res["experiments"] = experiments()
    res["bom"] = bom(res)
    return res


def guide_friction(d, ev: Dict) -> Dict:
    """The refill guide under the counter-face's couple (CALC): bushing loads, the slide friction h = mu_g sum|R| and its
    lateral effect h cot(th), for a ball/roller guide (mu_g 0.005), PTFE-lined sleeves (0.05) and bare metal (0.1)
    (ASSUMPTION coefficients); B1's continuous power recomputed with the 35 deg h."""
    from dataclasses import replace as _rp
    from . import candidates as CD
    from . import loads as LD
    geo_z1, geo_z2 = 9e-3, d.z_act + 6.4e-3            # the carrier's front bushing and its flange (layout.py)
    rows = []
    for th in (35.0, 50.0, 75.0):
        t = th * D2R
        cf = LD.guide_loads(t, d.F_s, True, geo_z1, geo_z2)
        sp = LD.guide_loads(t, d.F_s, False, geo_z1, geo_z2)
        row = {"theta_deg": th, "P_static_N": cf["P_N"], "sum_R_counterface_N": cf["sum_R_N"], "sum_R_spring_N": sp["sum_R_N"],
               "couple_mNm": cf["couple_Nm"] * 1e3}
        for mu in (0.005, 0.05, 0.1):
            row[f"h_cf_mu{mu:g}_N"] = mu * cf["sum_R_N"]
            row[f"lateral_cf_mu{mu:g}_N"] = mu * cf["sum_R_N"] / math.tan(t)
            row[f"h_spring_mu{mu:g}_N"] = mu * sp["sum_R_N"]
        rows.append(row)
    P = {}
    for mu in (0.005, 0.05, 0.1):
        h35 = mu * rows[0]["sum_R_counterface_N"]
        r = CD.evaluate(d, _rp(CD.DUTY_A, h_sl=h35), detail=False, fast=True)
        P[f"{mu:g}"] = {"h_35deg_N": h35, "P_cont_W": r["P_cont_W"], "P_35deg_W": r["P_mean_W_by_theta"][35.0],
                        "stuck_offset_hold_35deg_W": (h35 / math.tan(35 * D2R) / ev["Km_tip"]) ** 2}
    k_tilt = (ev.get("flexure") or {}).get("k_tilt_Nm_rad")
    tilt = {f"{r['theta_deg']:g}": {"tilt_mrad": r["couple_mNm"] * 1e-3 / k_tilt * 1e3 if k_tilt else None,
                                    "ball_offset_mm": r["couple_mNm"] * 1e-3 / k_tilt * geo_z2 * 1e3 if k_tilt else None}
            for r in rows}
    return {"rows": rows, "P_B1": P, "k_tilt_Nm_rad": k_tilt, "couple_tilt": tilt, "bushings_z_mm": [geo_z1 * 1e3, geo_z2 * 1e3],
            "label": "CALC (statics of the refill on two bushings; friction coefficients ASSUMPTION)"}


def write_all(S: Dict, quick: bool = False, log=print) -> Dict:
    from . import evidence as EV
    from . import figures as FG
    res = assemble(S)
    out_dir = RESULTS if not quick else BUILD / "quick"
    os.makedirs(out_dir, exist_ok=True)
    FG.OUT_DIR = out_dir
    figs = []
    try:
        figs.append(FG.balance_principle())
        if S.get("loads"):
            figs.append(FG.c1s_reconciliation(S["loads"]["reconciliation"]))
            figs.append(FG.balance_quality(S["loads"]["balance_quality"]))
            figs.append(FG.ink_force(S["loads"]["inkforce"]["sensitivity"]))
        if S.get("candidates"):
            figs.append(FG.power_vs_tilt(S["candidates"], "pen24"))
            figs.append(FG.power_vs_tilt(S["candidates"], "slim14"))
        if S.get("optimise"):
            figs += FG.pareto(S["optimise"])
        traces = {"B1 counter-face": res["recommended"].get("thermal_trace")}
        if S.get("candidates"):
            for k in ("pen24|f_translation", "pen24|a_long_arm"):
                t = (S["candidates"].get(k, {}).get("thermal") or {}).get("trace")
                if t:
                    traces[k.split("|")[1]] = t
        figs.append(FG.thermal(traces))
        if S.get("sim"):
            figs.append(FG.sim_cards(S["sim"]))
    except Exception as ex:                     # a figure must not stop the report
        log(f"[report] figure failed: {ex!r}")
    ev_path = EV.write(str(out_dir / "evidence_rows.csv"))
    body = {
        "what": "Study B (round 4): the balanced two-axis nib - loads reconciled, candidates (a)-(h) for the 24 mm pen and "
                "the slim core, multi-objective design, sim2 runs of the best, the recommended nib, DEC-050 draft (resolves DEC-046)",
        "labels": {"CALC": "calculation in bnib/", "SIM": "sim2 (MuJoCo 3.6) run", "LIT/MFR": "ledger id (docs/evidence.csv or "
                   "results/bnib/evidence_rows.csv)", "ASSUMPTION": "unmeasured input", "PROPOSED DESIGN": "a design choice"},
        "loads": S.get("loads"), "candidates_cards": res["cards"], "optimisation": _opt_summary(S.get("optimise")),
        "sim": S.get("sim"), "recommended": {k: v for k, v in res["recommended"].items() if k != "thermal_trace"},
        "interface": S.get("interface"), "layout": S.get("layout"), "decision_draft": res["decision"],
        "requirements": res["requirements"], "experiments": res["experiments"], "bom": res["bom"],
        "evidence_rows": os.path.relpath(ev_path, RESULTS.parent.parent), "figures": [os.path.relpath(f, RESULTS.parent.parent) for f in figs if f],
    }
    obj = {"stabpen.provenance": provenance("CALCULATION + SIMULATION on PROPOSED DESIGNS (study B); inputs LIT/MFR/ASSUMPTION; "
                                            "nothing built or measured", seeds=[200, 201, 202, 203, 300]), **body}
    path = write_json(str(out_dir / "bnib.json"), obj)
    from . import docgen
    doc_path = docgen.write(res, S, quick=quick)
    log(f"[report] {path}; {doc_path}; {len(figs)} figures")
    return {"json": path, "doc": doc_path, "figures": len(figs)}


def _opt_summary(opt: Optional[Dict]) -> Optional[Dict]:
    if not opt:
        return None
    out = {"fronts": opt.get("fronts"), "runs": {}}
    for pid, pr in opt.get("problems", {}).items():
        out["runs"][pid] = [{k: v for k, v in r.items() if k != "polish"} | {"polish": {kk: vv for kk, vv in (r.get("polish") or {}).items()
                                                                                      if kk != "metrics_after"}}
                            for r in pr.get("runs", [])]
    out["piezo_best"] = {g: sorted([p for p in v.get("points", []) if p.get("feasible_eps")], key=lambda p: p["P_cont_W"])[:5]
                         for g, v in (opt.get("piezo") or {}).items()}
    return out
