"""Proposed rows of study P for the lead (not written into the shared files): decisions DEC-085..089, requirements
REQ-PLT-001..010, experiments EXP-PL01..PL09 with criteria AC-PL01-01...  Numbers are filled from
results/platen/platen.json, so the document and the CSV twins (results/platen/proposed_*.csv) cannot disagree."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List

from . import common as CM


def _v(b, nd=2):
    return CM.fmt_ci(b, nd)


def numbers(res: Dict) -> Dict[str, str]:
    tr = res["tremor"]["by_class"].get("all/severe", {})
    tm = res["tremor"]["by_class"].get("all/moderate", {})
    ss = res["sensitivity"].get("rows", {})
    acc = res["accepted"].get("summary", {})
    g = lambda k, m="tip_tremor_mm", nd=2: _v((tr.get(k) or {}).get(m), nd)               # noqa: E731
    s = lambda k, m="tip_tremor_mm": _v((ss.get(k) or {}).get(m))                          # noqa: E731

    def sa(k):
        x = ((res.get("accepted") or {}).get("sensitivity") or {}).get(k)
        return f"{x['engineering_complete']}/{x['n']}" if x else "n/a"

    def a(t, c, h, key="engineering_complete"):
        x = acc.get(f"{t}|{c}|{h}")
        if not x:
            return "n/a"
        return f"{x['engineering_complete']}/{x['n']}" if key == "engineering_complete" else x[key]
    return {
        "p_oracle": g("P_oracle"), "p_oracle_w": g("P_oracle", "words_read", 1), "none": g("none"),
        "none_w": g("none", "words_read", 1), "f15": g("F15_oracle"), "f15_w": g("F15_oracle", "words_read", 1),
        "f10": g("F10_oracle"), "f10_w": g("F10_oracle", "words_read", 1), "p_ar2": g("P_a_r2"), "f15_ar2": g("F15_a_r2"),
        "p_cam": g("P_cam_sep"), "p_cam_w": g("P_cam_sep", "words_read", 1), "p_e": g("P_E_chosen"),
        "p_e_w": g("P_E_chosen", "words_read", 1), "p_net": g("P_E_net"), "p_net_w": g("P_E_net", "words_read", 1),
        "n15_e": g("N15_E_chosen"), "n15_e_w": g("N15_E_chosen", "words_read", 1), "n10_e": g("N10_E_chosen"),
        "n10_e_w": g("N10_E_chosen", "words_read", 1),
        "p_oracle_force": g("P_oracle", "force_rms_N"), "p_oracle_travel": g("P_oracle", "travel_p99_mm"),
        "belt_o": s("belt_single_stage|oracle"), "belt_c": s("belt_single_stage|camera"),
        "bw15_c": s("bandwidth_15Hz|camera"), "bw25_c": s("bandwidth_25Hz|camera"), "bw80_c": s("bandwidth_80Hz|camera"),
        "base_c": s("baseline|camera"), "base_o": s("baseline|oracle"), "lat2": s("latency_2ms|camera"),
        "lat10": s("latency_10ms|camera"), "lat15": s("latency_15ms|camera"), "lat25": s("latency_25ms|camera"),
        "n0": s("noise_0um|camera"), "n30": s("noise_30um|camera"), "n60": s("noise_60um|camera"),
        "k05": s("tilt_kappa_0.05|camera"), "k10": s("tilt_kappa_0.1|camera"), "k20": s("tilt_kappa_0.2|camera"),
        "tr3": s("travel_3mm|oracle"), "tr4": s("travel_4mm|oracle"), "tr6": s("travel_6mm|oracle"),
        "slip_vac_o": s("slip_hand_on_paper_vacuum|oracle"), "slip_clip_o": s("slip_hand_on_paper_clip_only|oracle"),
        "slip_palm_o": s("slip_palm_rest_clip_only|oracle"),
        "fric_fixed": s("friction_intended|fixed"), "fric_o": s("friction_intended|oracle"),
        "fric_c": s("friction_intended|camera"),
        "se_prop_still": a("se", "proposed", "still"), "se_prop_drift": a("se", "proposed", "drift"),
        "se_prop_modpd": a("se", "proposed", "mod_PD"), "se_prop_sevpd": a("se", "proposed", "sev_PD"),
        "se_prop_sevet": a("se", "proposed", "sev_ET"), "se_cradle": a("se", "cradle", "cradle"),
        "se_relaxed": a("se", "relaxed_naive", "still"), "se_relaxed_loop": a("se", "relaxed_ink_loop", "still"),
        "se_firm_still": a("se", "firm_ideal", "still"), "lib_prop_still": a("library", "proposed", "still"),
        "lib_cradle": a("library", "cradle", "cradle"),
        "slip_pv_c": s("slip_palm_rest_vacuum|camera"),
        "slip_pv_slip": _v((ss.get("slip_palm_rest_vacuum|camera") or {}).get("paper_slip_max_mm")),
        "slip_pc_held": _v((ss.get("slip_palm_rest_clip_only|held") or {}).get("paper_slip_final_mm"), 1),
        "slip_pc_cam": _v((ss.get("slip_palm_rest_clip_only|camera") or {}).get("paper_slip_final_mm"), 1),
        "slip_hv_c": s("slip_hand_on_paper_vacuum|camera"),
        "slip_hv_force": _v((ss.get("slip_hand_on_paper_vacuum|camera") or {}).get("force_rms_N"), 1),
        "slip_hc_held": _v((ss.get("slip_hand_on_paper_clip_only|held") or {}).get("paper_slip_final_mm"), 0),
        "air_runs": f"{((res.get('accepted') or {}).get('air_ink') or {}).get('runs', 0):,}",
        "air_max": f"{((res.get('accepted') or {}).get('air_ink') or {}).get('max_air_phase_ink_mm', float('nan')):.3f}",
        "sens_n10": sa("firm_N1.0|still"), "sens_medium": sa("medium_grip_N0.5|still"),
        "sens_m07": sa("model_x0.7|still"), "sens_m13": sa("model_x1.3|still"),
        "sens_m07_pd": sa("model_x0.7|mod_PD"), "sens_m13_pd": sa("model_x1.3|mod_PD"),
        "ext": "; ".join(f"'{t}' up to {e['max_width_mm']:.0f} x {e['max_height_mm']:.0f} mm and {e['max_duration_s']:.1f} s"
                         for t, e in ((res.get("accepted") or {}).get("reference_extent") or {}).items()) or "n/a",
    }


def decisions(n: Dict[str, str]) -> List[List[str]]:
    return [
        ["DEC-085", "**Build a moving-paper platen as the project's desk research platform and comparison "
                    "architecture** for severe-tremor legibility and accepted writing; it complements, and does not "
                    "replace, the handheld pen (DEC-060's nib stays the portable product line). Alternatives: the "
                    "handheld nib only; the grounded five-bar; a pen plotter",
         f"SIM (HW1 + platen stage, real inputs, tuning split): perfect knowledge on the +-5 mm platen leaves {n['p_oracle']} "
         f"mm and {n['p_oracle_w']} words of 10 are read, where the +-1.5 mm nib leaves {n['f15']} mm ({n['f15_w']} "
         f"words) and the +-1.0 mm nib {n['f10']} mm ({n['f10_w']}); accepted 'se' with the pen held firmly "
         f"{n['se_prop_still']} and in a cradle {n['se_cradle']}, against the five-bar's 0/20 with a 200 or 500 N/m grip",
         "EXP-PL01 (stage) and EXP-PL06 (tremor replay on the bench) contradict the simulated residual; EXP-PL03 finds "
         "that writers do not cancel the tremor-band drag and no grip or decoupling restores the camera loop (part c: "
         f"{n['fric_c']} mm under the 'intended' convention); EXP-PL09 finds no user who prefers the platen to typing, "
         "dictation or a plotter"],
        ["DEC-086", "**The platen's stage is two-layer: a voice-coil fine XY stage (+-5 mm, 40 Hz, <= 0.6 kg moving, "
                    "20 N cap) on a belt H-bot coarse stage (+-40 x +-20 mm, about 8 Hz, 20 N cap)**; tremor is "
                    "cancelled on the fine stage only. Alternatives: one belt H-bot for everything; linear motors on "
                    "one long-travel stage; A6 only",
         f"SIM: the single belt stage (15 Hz) leaves {n['belt_o']} mm with perfect knowledge and {n['belt_c']} mm with "
         f"the camera, against {n['base_o']} and {n['base_c']} for the fine stage; travel +-3 / +-4 / +-6 mm leaves "
         f"{n['tr3']} / {n['tr4']} / {n['tr6']} mm; LIT: belt axes ring at about 50 Hz (CON-112); MFR: LVCM-032-025-02 "
         "(AMF-280)",
         "EXP-PL01 measures a fine-stage bandwidth below 25 Hz or a structural mode below 150 Hz"],
        ["DEC-087", "**The platen senses the pen tip in the desk frame with an absolute sensor (a global-shutter camera "
                    "at >= 250 frames/s, <= 6 ms latency, <= 15 um noise, a marker within 3 mm of the ball; EMR under "
                    "the plate as the alternative), and contact with load cells under the plate**; the pen's IMU is "
                    "used only by free-writing estimators. Alternatives: IMU clip only; EMR only; the pen's optical "
                    "page sensor",
         f"SIM (perfect separation, tuning split): camera latency 2 / 6 / 10 / 15 / 25 ms leaves {n['lat2']} / "
         f"{n['base_c']} / {n['lat10']} / {n['lat15']} / {n['lat25']} mm; noise 0 / 15 / 30 / 60 um leaves {n['n0']} / "
         f"{n['base_c']} / {n['n30']} / {n['n60']} mm; a marker whose error is 5 / 10 / 20 % of the hand tremor leaves "
         f"{n['k05']} / {n['k10']} / {n['k20']} mm; MFR camera data (AMF-281, AMF-282); EMR +-0.4 mm, 133 points/s (AMF-98)",
         "EXP-PL02 measures the camera's latency, noise or tilt error outside these bounds"],
        ["DEC-088", "**Accepted writing on the platen needs the pen held stiffly against the page's drag**: the default "
                    "is a pen cradle on the palm rest (the user's pen docked); a held pen is allowed when the hand rests "
                    "on the palm rest with a firm grip, the Z axis holds the normal force at <= 0.5 N, and the "
                    "controller decouples the drag, feeds the expected pen deflection forward and closes a loop on the "
                    "measured ink; the platen never follows a tip it cannot tell from the page's own drag. Alternatives: "
                    "tip following with any hand; the five-bar",
         f"SIM ('se', 20 UJI references): proposed {n['se_prop_still']} (still hand), {n['se_prop_drift']} (drift), "
         f"{n['se_prop_modpd']} (moderate PD), {n['se_prop_sevpd']} (severe PD), {n['se_prop_sevet']} (severe ET); cradle "
         f"{n['se_cradle']}; HW1's relaxed hand with tip following {n['se_relaxed']}, with the ink loop "
         f"{n['se_relaxed_loop']}; 'library' proposed {n['lib_prop_still']}, cradle {n['lib_cradle']}; sensitivity "
         f"(still hand): 1.0 N {n['sens_n10']}, a medium grip {n['sens_medium']}, the compliance model 30 % low / high "
         f"{n['sens_m07']} / {n['sens_m13']} (moderate PD {n['sens_m07_pd']} / {n['sens_m13_pd']})",
         "EXP-PL03 (people's pen deflection under page drag) or EXP-PL05 (bench accepted writing) disagree"],
        ["DEC-089", "**Severe-tremor legibility claims stay gated by the estimator (DEC-055, DEC-067), not by reach**: "
                    "with the platen the reach limit is gone, so every new estimator is first tested on the platen (in "
                    "simulation, then EXP-PL06) before the nib; the platen is positioned as a desk device for paper "
                    "tasks (letters, cards, forms, signing by template) and for clinics, with typing, dictation and a "
                    "plotter as the comparators. Alternatives: claim platen legibility now; drop the platen",
         f"SIM: study E's frozen design on the platen leaves {n['p_e']} mm and {n['p_e_w']} words are read (the "
         f"ordinary pen: {n['none']} mm, {n['none_w']} words); on the +-1.5 mm nib {n['n15_e']} mm, {n['n15_e_w']} "
         f"words: separation, not reach, limits today",
         "an estimator passes DEC-055 on new held-out data (EXP-E10)"],
    ]


def requirements(n: Dict[str, str]) -> List[Dict]:
    base = {"area": "platen", "source": "study P (docs/platen_concept.md)", "evidence_status": "simulated",
            "status": "proposed"}
    R = [
        ("REQ-PLT-001", "Fine-stage travel", "The fine stage gives at least +-5 mm radial usable travel on the paper "
         "(soft limit, end stops beyond), enough that perfect knowledge of severe real tremor leaves at most 0.15 mm "
         "at the tip on the tuning split", f"Platen +-5 mm {n['p_oracle']} mm; +-4 mm {n['tr4']}; +-3 mm {n['tr3']} "
         "(SIM)", "EXP-PL01; simulation rerun on the built stage's identified model"),
        ("REQ-PLT-002", "Fine-stage dynamics", "The fine stage follows position commands with >= 25 Hz bandwidth "
         "(40 Hz proposed), <= 0.6 kg moving per axis, >= 20 N peak and >= 5 N continuous per axis, first structural "
         "mode >= 150 Hz", f"Bandwidth 15 / 25 / 80 Hz with the camera: {n['bw15_c']} / {n['bw25_c']} / {n['bw80_c']} "
         f"mm (40 Hz: {n['base_c']}); force RMS with perfect knowledge {n['p_oracle_force']} N (SIM)", "EXP-PL01"),
        ("REQ-PLT-003", "Coarse stage", "The coarse stage moves the fine stage +-40 x +-20 mm at <= 50 mm/s and <= 2 "
         "m/s2 with feedforward of the accepted word's page motion; force capped at 20 N", "An accepted word up to "
         f"80 mm long passes under a still pen; the references span {n['ext']} (SIM references)", "EXP-PL01; EXP-PL05"),
        ("REQ-PLT-004", "Absolute tip sensing", "The tip sensor reports the pen tip in the desk frame with <= 6 ms "
         "latency, <= 15 um RMS noise per axis, >= 250 samples/s, a marker <= 3 mm from the ball (tilt error <= 5 % of "
         "the hand tremor) or tilt compensation", f"Latency 10 / 15 ms leaves {n['lat10']} / {n['lat15']} mm; noise 30 "
         f"um {n['n30']} mm; tilt 10 % {n['k10']} mm (SIM, perfect separation)", "EXP-PL02"),
        ("REQ-PLT-005", "Hold-down and registration", "The sheet is held against >= 3 N of shear (A5: about 240 Pa of "
         "vacuum, CALC) with no slip under the ball's drag, and registered to the platen frame within 0.2 mm",
         f"Palm rest and vacuum: the camera loop leaves {n['slip_pv_c']} mm, sheet slip {n['slip_pv_slip']} mm; palm "
         f"rest and a clip only: the sheet walks {n['slip_pc_held']} mm (page held) and {n['slip_pc_cam']} mm (camera "
         f"loop); hand on vacuum-held paper: the camera loop leaves {n['slip_hv_c']} mm at {n['slip_hv_force']} N RMS; "
         f"hand on clip-held paper: the sheet travels {n['slip_hc_held']} mm (SIM; LuGre creep inflates slip, CON-113)",
         "EXP-PL04"),
        ("REQ-PLT-006", "Palm rest", "A fixed palm-rest bridge keeps the hand off the moving paper; underside 15-35 mm "
         "above the paper (25 mm nominal, the ISO 13854 finger gap), posts outside the plate's swept envelope",
         "Design rule (CAD; ISO 13854 via CON-110); slip rows above", "EXP-PL04; EXP-PL08; EXP-PL09 (comfort)"),
        ("REQ-PLT-007", "Pen holding in accepted mode", "In accepted mode the pen is docked in a cradle, or held with "
         "the hand on the palm rest so that its tip moves <= 0.15 mm under the page's sliding drag (compliance x "
         "friction x normal force), with the normal force regulated at <= 0.5 N by the Z axis and the drag-decoupled "
         "ink-loop controller", f"'se' proposed {n['se_prop_still']}, cradle {n['se_cradle']}, relaxed hand "
         f"{n['se_relaxed']} (SIM)", "EXP-PL03; EXP-PL05"),
        ("REQ-PLT-008", "Contact and lift", "Load cells under the plate detect contact (>= 50 mN) within 2 ms; the "
         "Z-drop breaks contact within 40 ms and the page makes no air move until the break is confirmed",
         f"Air-phase ink at most {n['air_max']} mm over all {n['air_runs']} simulated words (a 40 ms drop, 200 ms in "
         "one variant, against the plan's 200 ms lift phases) (SIM); the five-bar's lift is 200 ms",
         "EXP-PL05; EXP-PL08"),
        ("REQ-PLT-009", "Safety", "Force caps 20 N (fine and coarse, in hardware current limits), speed cap 50 mm/s, "
         "moving kinetic energy <= 0.05 J, no fixed gap between 4 and 25 mm at a moving edge without a skirt, SELV "
         "supply, an emergency stop that holds the stage and drops the page; the page can only drag the pen with "
         "friction (<= 0.4 N)", "20 N is 14 % of ISO/TS 15066's 140 N for hands (CON-111); 1.8 mJ at 50 mm/s (CALC)",
         "EXP-PL08"),
        ("REQ-PLT-010", "Noise, power, size", "<= 40 dB(A) at 0.5 m while writing; <= 25 W from a 24 V adapter; A5 "
         "footprint <= 380 x 300 mm, paper surface <= 70 mm above the desk", "Budgets (CALC on ASSUMPTION ranges)",
         "EXP-PL07"),
    ]
    out = []
    for rid, title, req, est, ver in R:
        d = dict(base)
        d.update({"id": rid, "title": title, "requirement": req, "rationale": "Study P (SIMULATION and CALCULATION)",
                  "verification": ver, "current_estimate": est, "trace": "DEC-085..088; docs/platen_concept.md"})
        out.append(d)
    return out


def experiments() -> List[List[str]]:
    return [
        ["EXP-PL01", "Does the fine stage meet its travel, force, bandwidth and noise?", "Bench: the proposed fine "
         "stage with the A5 plate; step and swept-sine responses, force map over the travel, encoder noise; replay of "
         "study F's perfect-knowledge commands (severe class) and the measured page error", "REQ-PLT-001, 002, 003"],
        ["EXP-PL02", "How well does the camera see the pen tip?", "A pen tip moved by the fine stage (known motion) "
         "under the camera: latency (LED flash + stage), noise, occlusion by a hand, error from pen rotation with the "
         "marker at 3 and 10 mm above the ball; EMR digitiser as the comparator", "REQ-PLT-004"],
        ["EXP-PL03", "How far does a moving page drag a held pen, and does the writer cancel the drag?", "People (with "
         "and without tremor) hold a pen on the palm rest; the page slides and reverses at 5-30 mm/s with 0.3-1.0 N "
         "normal force; tip deflection by the camera, drag by the plate; relaxed and firm grips; the hand-compliance "
         "model fitted per person. Then free writing on a page that follows the tip with a small known error: how much "
         "of the tremor-band drag the writer's hand cancels (HW1's convention against 'intended', part c)",
         "REQ-PLT-007; DEC-085; DEC-089"],
        ["EXP-PL04", "Does the sheet stay put?", "Vacuum, tack mat and clip-only hold-downs; shear to slip with and "
         "without a hand resting on the paper; registration repeatability over 20 sheet loads", "REQ-PLT-005, 006"],
        ["EXP-PL05", "Does the platen write accepted words on paper?", "The 20 'se' and 20 'library' references written "
         "with the pen in a cradle and held by people without tremor; ink scanned at 1200 dpi and compared with the "
         "reference: coverage, RMS, extra ink, refusals", "REQ-PLT-007, 008"],
        ["EXP-PL06", "Does moving the page cancel real tremor at the ink?", "A tremor replay rig (a robot hand moving "
         "a pen with study R's recorded tremor) on the platen: perfect knowledge (the rig's own command) and the camera "
         "loop; ink scanned and read by the literal reader and by people (EXP-R03)", "DEC-085, DEC-089"],
        ["EXP-PL07", "Noise, power and heat", "Sound level at 0.5 m while writing and repositioning; input power; coil "
         "and surface temperatures after an hour of tremor duty", "REQ-PLT-010"],
        ["EXP-PL08", "Safety", "Pinch forces at the palm rest and the plate edges with a force gauge; force caps under "
         "a stalled stage; emergency stop; failed lift", "REQ-PLT-008, 009"],
        ["EXP-PL09", "Who would use it?", "Matched tasks (a letter, a form, a signature by template, accepted-word "
         "completion) against an ordinary pen, typing, dictation and a pen plotter; people with ET or PD tremor and "
         "people with dyslexia; setup time, legibility (blinded readers), effort, preference; acceptability of "
         "template signatures", "DEC-085, DEC-089"],
    ]


def criteria(n: Dict[str, str]) -> List[Dict]:
    C = [
        ("AC-PL01-01", "REQ-PLT-001", "EXP-PL01", "Page error of the fine stage replaying study F's severe perfect-"
         "knowledge commands (R's in-band measure on page minus command, delay removed), mean over the 20 tuning cases",
         "0.15 mm", "<=", f"SIM: the platen leaves {n['p_oracle']} mm with perfect knowledge", "hypothesis", "DEC-086"),
        ("AC-PL01-02", "REQ-PLT-002", "EXP-PL01", "Closed-loop -3 dB bandwidth of the fine stage with the A5 plate",
         "25 Hz", ">=", f"SIM sensitivity: 25 Hz leaves {n['bw25_c']} mm with the camera", "requirement", "DEC-086"),
        ("AC-PL02-01", "REQ-PLT-004", "EXP-PL02", "End-to-end camera latency (acquisition to position available)",
         "6 ms", "<=", "MFR: 240 fps cameras reach 4.2 ms (AMF-282); SIM latency sweep", "requirement", "DEC-087"),
        ("AC-PL02-02", "REQ-PLT-004", "EXP-PL02", "RMS position noise per axis of the tracked tip at rest", "15 um",
         "<=", f"SIM: 30 um leaves {n['n30']} mm", "requirement", "DEC-087"),
        ("AC-PL03-01", "REQ-PLT-007", "EXP-PL03", "Tip deflection under sliding page drag with the firm grip on the "
         "palm rest at 0.5 N normal force, median over participants", "0.15 mm", "<=", "ASSUMPTION: firm grip 1.37 "
         "mm/N x 0.15 x 0.5 N = 0.10 mm (CALC); HW1's relaxed hand 0.57 mm at 0.5 N", "hypothesis", "DEC-088"),
        ("AC-PL04-01", "REQ-PLT-005", "EXP-PL04", "Shear force to slip the sheet with the chosen hold-down", "3 N", ">=",
         "CALC: 3 x a resting hand's friction", "requirement", "REQ-PLT-005"),
        ("AC-PL05-01", "REQ-PLT-007", "EXP-PL05", "Accepted words meeting the five-bar's engineering criterion "
         "(coverage >= 98 %, RMS <= 0.10 mm, air ink <= 0.02 mm, no refusal), pen in a cradle", "20 of 20", ">=",
         f"SIM: cradle 'se' {n['se_cradle']}, 'library' {n['lib_cradle']}", "hypothesis", "DEC-088"),
        ("AC-PL05-02", "REQ-PLT-007", "EXP-PL05", "The same with the pen held firmly on the palm rest by people "
         "without tremor", "18 of 20", ">=", f"SIM: proposed 'se' still {n['se_prop_still']}", "hypothesis", "DEC-088"),
        ("AC-PL06-01", "", "EXP-PL06", "Tremor left at the ink with the rig's perfect knowledge, severe class", "0.25 mm",
         "<=", f"SIM {n['p_oracle']} mm; F's near-normal level 0.25 mm", "hypothesis", "DEC-085; DEC-089"),
        ("AC-PL07-01", "REQ-PLT-010", "EXP-PL07", "A-weighted sound level at 0.5 m while writing", "40 dB(A)", "<=",
         "ASSUMPTION (quiet office)", "requirement", "REQ-PLT-010"),
        ("AC-PL08-01", "REQ-PLT-009", "EXP-PL08", "Largest pinch force at any moving edge with the stage stalled",
         "20 N", "<=", "ISO/TS 15066 hands 140 N (CON-111); the cap is the design value", "requirement", "REQ-PLT-009"),
        ("AC-PL09-01", "", "EXP-PL09", "Share of participants who would choose the platen for at least one of the "
         "matched paper tasks over typing, dictation and a plotter", "25 %", ">=", "ASSUMPTION: a niche worth a "
         "product; to be set with the panel before the study", "hypothesis", "DEC-085; DEC-089"),
    ]
    return [dict(zip(["id", "requirement_id", "experiment_id", "metric", "threshold", "direction", "basis", "status",
                      "decision_gated"], c)) for c in C]


def write_csvs(res: Dict, out: Path) -> Dict[str, Path]:
    n = numbers(res)
    paths = {}
    req = requirements(n)
    cols = ["id", "area", "title", "requirement", "rationale", "source", "verification", "evidence_status",
            "current_estimate", "trace", "status"]
    for name, rows, header in (("proposed_requirements.csv", req, cols),
                               ("proposed_criteria.csv", criteria(n), ["id", "requirement_id", "experiment_id",
                                                                        "metric", "threshold", "direction", "basis",
                                                                        "status", "decision_gated"])):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header, lineterminator="\r\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
        p = out / name
        p.write_bytes(buf.getvalue().encode("utf-8"))
        paths[name] = p
    return paths


def markdown(res: Dict) -> str:
    n = numbers(res)

    def t(header, rows):
        return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] +
                         ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"
    parts = ["**Proposed decisions** (for `docs/decisions.md`)\n",
             t(["id", "Proposed decision", "Evidence", "Revisit when"], decisions(n)),
             "\n**Proposed requirements** (for `docs/requirements.csv`; CSV twin `results/platen/proposed_requirements.csv`)\n",
             t(["id", "Title", "Requirement", "Current estimate", "Verification"],
               [[r["id"], r["title"], r["requirement"], r["current_estimate"], r["verification"]] for r in requirements(n)]),
             "\n**Proposed experiments** (for `validation/bench_protocols.md`)\n",
             t(["id", "Question", "Method", "Decides"], experiments()),
             "\n**Proposed criteria** (for `validation/acceptance_criteria.csv`; CSV twin `results/platen/proposed_criteria.csv`)\n",
             t(["id", "requirement", "experiment", "metric", "threshold", "direction", "basis", "status", "decision gated"],
               [[c[k] for k in ("id", "requirement_id", "experiment_id", "metric", "threshold", "direction", "basis",
                                "status", "decision_gated")] for c in criteria(n)])]
    return "\n".join(parts)
