"""docs/balanced_nib.md from the results (every number comes from bnib.json's inputs; labels on every number)."""
from __future__ import annotations

import math
import os
from typing import Dict, List

from . import BUILD, DOC, REPO_ROOT

TH = ("35.0", "50.0", "60.0", "75.0")


def f(x, nd=2):
    if x is None:
        return "-"
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "-"
    except Exception:
        return str(x)
    if isinstance(x, (int,)):
        return str(x)
    if abs(x) >= 100:
        return f"{x:.0f}"
    if abs(x) >= 10:
        return f"{x:.1f}" if nd >= 1 else f"{x:.0f}"
    return f"{x:.{nd}f}"


def mw(x, nd=1):
    return "-" if x is None else f(x * 1e3, nd)


def card_md(c: Dict) -> str:
    L = []
    L.append(f"#### {c['title']} - {c['grip']}")
    L.append("")
    L.append(f"*Verdict (CALC):* **{c['verdict']}**")
    L.append("")
    pw = c["power_by_tilt"]
    if c["family"] != "piezo":
        L.append("| power, mW (CALC, duty A) | 35 deg | 50 deg | 60 deg | 75 deg |")
        L.append("|---|---|---|---|---|")
        for key, lab in (("P_hold_W", "holding, ball on the paper"), ("P_penup_W", "pen up"), ("P_friction_W", "friction share"),
                         ("P_dynamic_W", "dynamic (inertia + suspension)"), ("P_mean_W", "mean, roll 0"),
                         ("P_mean_roll_max_W", "mean, worst roll"), ("P_hold_roll_max_W", "holding, worst roll")):
            L.append(f"| {lab} | " + " | ".join(mw(pw[t].get(key), 2 if (pw[t].get(key) or 0) < 0.01 else 1) for t in TH) + " |")
    else:
        L.append("| piezo stage (CALC) | 35 deg | 50 deg | 60 deg | 75 deg |")
        L.append("|---|---|---|---|---|")
        L.append("| static load held by the voltage offset (N) | " + " | ".join(f(pw[t].get("static_N"), 3) for t in TH) + " |")
        L.append("| usable travel left (mm) | " + " | ".join(f(pw[t].get("loaded_usable_mm"), 2) for t in TH) + " |")
        L.append("| drive power incl. boost (mW) | " + " | ".join(mw(pw[t].get("P_mean_W"), 1) for t in TH) + " |")
    L.append("")
    fat = c.get("fatigue") or {}
    items = [
        ("continuous power (mean 35-75 deg, duty A / duty B)", f"{mw(c['P_cont_W'])} / {mw(c.get('P_cont_duty_B_W'))} mW"
         + ("" if c.get("duty_B_feasible") or c["family"] == "piezo" else " (duty B beyond this nib's travel)")),
        ("peak power (12 Hz full travel, 35 deg, hot coil)", f"{f(c.get('P_peak_W'), 3)} W"),
        ("travel under load (35 deg; design)", f"+-{f(c['travel_under_load_mm'])} mm (+-{f(c['travel_design_mm'])} mm)"),
        ("tip-equivalent moving mass", f"{f(c['m_eff_tip_g'])} g"),
        ("Km at the tip (centre / worst corner)", f"{f(c.get('Km_tip'), 3)} / {f(c.get('Km_tip_min'), 3)} N/sqrt(W) (image-method upper bound)"
         if c.get("Km_tip") else "-"),
        ("bandwidth (first parasitic mode / 3)", f"{f(c['bandwidth_Hz'], 0)} Hz"),
        ("coil / skin temperature, 30-min run at 35 deg, 30 degC room, governor", f"{f(c.get('T_coil_C'), 1)} / {f(c['T_skin_C'], 1)} degC"
         + (f" (governor authority down to {f(c.get('governor_min'), 2)})" if (c.get('governor_min') or 1) < 0.999 else "")),
        ("pen mass / diameter / length / centre of mass", f"{f(c['mass_g'], 1)} g / {f(c['od_mm'], 0)} mm / {f(c['length_mm'], 0)} mm / "
         f"{f(c['com_mm'], 0)} mm from the tip"),
        ("battery time (electronics + nib)", f"{f(c['battery_h'], 1)} h"),
        ("fatigue (43.2 M cycles, full stop travel, Kt)", (f"Goodman SF {f(fat.get('goodman_SF_full_travel'), 2)}, "
         f"strain {f((c.get('strain_stop') or 0) * 1e3, 2)} x 1e-3"
         + (f", stress {f(c.get('stress_stop_MPa'), 0)} MPa" if c.get('stress_stop_MPa') else "")
         + f" with Kt {f(fat.get('Kt'), 1)} ({fat.get('material')})"
         + (f"; buckling margin {f(fat.get('buckling_SF'), 1)} x the magnet pull" if fat.get('buckling_SF') else ""))
         if fat.get("goodman_SF_full_travel") else (fat.get("note") or "-")),
        ("drop / shock", _shock(c.get("shock"))),
        ("sensing", _sens(c.get("sensing"))),
        ("manufacturability", "; ".join((c.get("manufacture") or {}).get("parts", [])[:4])),
        ("failure state (unpowered)", (c.get("failure_state") or {}).get("state", "-")),
    ]
    for k, v in items:
        L.append(f"- {k}: {v}")
    L.append("")
    return "\n".join(L)


def _shock(s):
    if not s:
        return "-"
    if "rows" in s:
        r = [x for x in s["rows"] if x["g"] == 2000.0]
        r = r[0] if r else s["rows"][-1]
        return (f"axial stops {f(s['stop_axial_um'], 0)} um: wire stress {f(r['wire_stress_MPa'], 0)} MPa at {f(r['g'], 0)} g; "
                f"buckled wires stay elastic: {s.get('buckled_elastic')}")
    return s.get("note", "-")


def _sens(s):
    if not s:
        return "-"
    return (f"nib: {s.get('nib_sensor', '-')} ({f(s.get('nib_hall_noise_um_1kHz'), 2)} um rms at 1 kHz, CALC); page: DeltaPen-class "
            f"optical flow (LIT OPT-01/02)")


def sim_md(sim: Dict) -> str:
    cards = (sim or {}).get("cards") or {}
    if not cards:
        return "The sim2 stage has not finished; no simulation results are reported here.\n"
    L = ["| SIMULATION (sim2) | " + " | ".join(f"{k}: {v['title']}" for k, v in cards.items()) + " |",
         "|---|" + "---|" * len(cards)]
    rows = [
        ("tremor left at the tip, tracker (ink error on/off, mean of cells)", "tremor_left_ratio_mean", 2, 1),
        ("tremor left at the tip, perfect knowledge (mechanism limit)", "tremor_left_ratio_oracle_mean", 2, 1),
        ("ink error, nib off / tracker / perfect knowledge (um)", None, 0, 1),
        ("readable words out of 10, nib off / tracker / perfect knowledge", None, 1, 1),
        ("clean writing changed by the nib (um rms; false correction)", "clean_moved_um_mean", 1, 1),
        ("nib power while correcting (mW)", "P_nib_mW_tremor_mean", 1, 1),
        ("writing time per charge (h)", "battery_h_tremor", 1, 1),
        ("coil / skin at the end of the runs (degC)", None, 1, 1),
    ]
    for lab, key, nd, _ in rows:
        vals = []
        for k, c in cards.items():
            if key:
                vals.append(f(c.get(key), nd))
            elif lab.startswith("ink error"):
                vals.append(f"{f(c.get('ink_err_um_off_mean'), 0)} / {f(c.get('ink_err_um_nib_mean'), 0)} / {f(c.get('ink_err_um_oracle_mean'), 0)}")
            elif lab.startswith("readable"):
                vals.append(f"{f(c.get('words_per10_off'), 1)} / {f(c.get('words_per10_nib'), 1)} / {f(c.get('words_per10_oracle'), 1)}")
            else:
                vals.append(f"{f(c.get('T_coil_end_C_max'), 1)} / {f(c.get('T_skin_end_C_max'), 1)}")
        L.append(f"| {lab} | " + " | ".join(vals) + " |")
    L.append("")
    L.append("Writing time per charge includes the electronics (34-60 mW, CALC): the 24 mm pen's LIR14500 gives 2.22 Wh "
             "usable (MFR AMF-80 x 0.8), the slim core's 10440-class cell 0.89 Wh (ASSUMPTION), hence B3's shorter time at "
             "a lower nib power than B2.")
    L.append("")
    return "\n".join(L)


def by_cell_md(sim: Dict) -> str:
    cards = (sim or {}).get("cards") or {}
    if not cards:
        return ""
    cells = sorted({c for v in cards.values() for c in v.get("by_cell", {}).keys()})
    L = ["| cell | " + " | ".join(f"{k} ratio (tracker / perfect)" for k in cards) + " | " + " | ".join(f"{k} words off -> on" for k in cards) + " |",
         "|---|" + "---|" * (2 * len(cards))]
    for c in cells:
        a = []
        b = []
        for k, v in cards.items():
            x = v["by_cell"].get(c, {})
            a.append(f"{f(x.get('ratio_mean'), 2)} / {f(x.get('ratio_oracle'), 2)}")
            w10 = lambda v: None if v is None else 10.0 * float(v)
            b.append(f"{f(w10(x.get('words_off')), 1)} -> {f(w10(x.get('words_nib')), 1)}")
        L.append(f"| {c} | " + " | ".join(a) + " | " + " | ".join(b) + " |")
    ref = (sim.get("sim2j_revJ_reference") or {}).get("cells", {})
    if ref:
        L.append("")
        L.append("Reference, the Rev J C1S nose in the same ET cells (sim2j, same writers and tracker; SIM, read-only): " + "; ".join(
            f"{k}: ratio {f(v['ratio_nose'], 2)} (perfect knowledge {f(v.get('ratio_oracle'), 2)}), nose power {f(v['P_nose_W'], 2)} W"
            for k, v in ref.items()) + ".")
    L.append("")
    return "\n".join(L)


def write(res: Dict, S: Dict, quick: bool = False) -> str:
    rec = res["recommended"]
    loads = S.get("loads") or {}
    sim = S.get("sim") or {}
    opt = S.get("optimise") or {}
    cards = res["cards"]
    rv = (loads.get("review_check") or {}).get("static_power_W", {})
    rc = loads.get("reconciliation") or {}
    nd = rc.get("duty_model") or {}
    bq = loads.get("balance_quality") or {}
    ik = loads.get("inkforce") or {}
    sc = sim.get("cards") or {}
    B1, B2, B3 = sc.get("B1", {}), sc.get("B2", {}), sc.get("B3", {})
    c_slim_piezo = cards.get("slim14|h_piezo", {})
    pz_best = None
    for g, v in ((opt.get("piezo") or {}).items()):
        if g == "slim":
            P = sorted([p for p in v.get("points", []) if p.get("feasible_eps") and p["key"] == "h_piezo_c"
                        and p["travel_mm"] >= 0.5], key=lambda p: p["P_cont_W"])
            pz_best = P[0] if P else None
    x = rec.get("x") or {}
    if not sim.get("deltapen_calibration"):
        try:
            from .sim import deltapen_calibration
            sim = dict(sim, deltapen_calibration=deltapen_calibration())
        except Exception:
            pass
    L: List[str] = []
    A = L.append
    A("# The answer in plain words: the balanced two-axis nib (study B, round 4)")
    A("")
    A(f"- **The review is right, and the load is bigger than the budget said.** The Rev J C1S nose holds the ball on the "
      f"paper with its coils. The refill spring pushes the ball along the tilted pen; the paper pushes back straight up, "
      f"so part of its push acts across the pen (0.15 N x cot(tilt): 0.21 N at 35 deg). The C1S lever (ball 76.5 mm, "
      f"magnets 11.5 mm from the pivot) multiplies it by 6.65, and the coils burn {f(rv.get('35', {}).get('P_W'), 2)} / "
      f"{f(rv.get('50', {}).get('P_W'), 2)} / {f(rv.get('75', {}).get('P_W'), 2)} W at 35 / 50 / 75 deg just holding still "
      f"(CALC, the review's numbers reproduced). Study N's duty model counted the ball's drag but not this sideways part "
      f"(details in section 5.1).")
    A(f"- **Balance it with the spring, not with current.** Let the ink spring push the refill from its back end through a "
      f"small face that is kept parallel to the paper. The face's push and the paper's push are then parallel and opposite: "
      f"there is nothing left across the pen for the nib to hold, at any tilt. Because the spring's own force does the "
      f"balancing, it follows the actual ink force (a new refill, another ink) without calibration, and a stop lets the face "
      f"go when the ball lifts, so nothing is held in the air (the figure below). What is left for the coils is mostly the "
      f"ball's drag on the paper, which no balance can remove and which grows with the ink force.")
    A(f"- **The nib for the first prototype (B1):** the refill rides in a titanium carrier that slides sideways +-1 mm on four "
      f"thin titanium wires; flat moving coils on the carrier sit between four fixed magnets (so there is no magnetic pull "
      f"and no negative stiffness); the counter-face sits behind the refill; the pen stays 24 mm. Continuous nib power "
      f"{f(rec['P_cont_mW'], 1)} mW at the comparison duty ({f(rec['P35_mW'], 1)} mW at 35 deg; {f(rec['P_cont_km07_mW'], 1)} mW "
      f"if the magnets are 30 % weaker), holding heat at most {f(rec['hold_max_mW'], 1)} mW (the limit is 100 mW, "
      f"REQ-RVJ-N10), +-{f(rec['travel_mm'], 2)} mm "
      f"of travel under the worst static load even if the magnets are 30 % weaker than calculated, {f(rec['m_eff_g'], 1)} g "
      f"moving at the tip, pen {f(rec['mass_g'], 0)} g, skin {f(rec['T_skin_C'], 1)} degC in a 30 degC room, about "
      f"{f(rec['battery_h'], 0)} h per charge (the electronics dominate). CALC.")
    A(f"- **The alternatives, in one line each.** The same nib without the balance: {f(rec['f_P_cont_mW'], 0)} mW on average but "
      f"{f(rec['f_hold_max_mW'], 0)} mW of holding heat at 35 deg, over the 0.1 W limit (REQ-RVJ-N10) below about "
      f"{f(rec['f_theta_ok_deg'], 0)} deg. A scheduled bias spring with a clutch that lets go at every lift (b'): "
      f"{f(rec['bepm_hold_max_mW'], 0)} mW holding at worst; without the clutch it pushes the nib over whenever the pen is "
      f"lifted. A longer lever like Rev H: {f(rec['a_P_cont_mW'], 0)} mW and only about +-{f(rec.get('a_travel_mm'), 1)} mm "
      f"once the magnets are 30 % weaker. Study W's collar carries the same load on a long lever (its actuator 42 mm behind "
      f"a pivot 50 mm from the tip): 0.16 / 0.055 / 0.006 W at 35 / 50 / 75 deg (DEC-051, study W's numbers), inside the "
      f"0.1 W limit only above about 42 deg (CALC: the holding heat scales with cot^2(tilt)). A lower ink force helps in "
      f"proportion, but nobody knows yet how low it can go. A bent tip needs a custom short cartridge. (Sections 2 and 3.)")
    A(f"- **What B1 gives up: reach.** The Rev J nose reaches +-6 mm; B1 reaches +-{f(rec['travel_mm'], 2)} mm (the same "
      f"design built for +-1.5 mm costs about twice the power, section 3). Study R's real recordings put tremor at the tip "
      f"lower than the plan assumed (severe class typically 1.7 mm peak, moderate 0.24 mm, mild 0.10 mm; docs/real_data.md), "
      f"so B1 covers the mild and moderate classes and part of the severe one. With no whole-pen actuator now (DEC-051), "
      f"tremor beyond the nib's reach stays uncorrected in the first prototype.")
    if B1:
        F = sim_findings(sim)
        by, ref, tv = F["by"], F["ref"], F["travel"]
        rr = lambda c, k="ratio_mean": f(by.get(c, {}).get(k), 2)
        jr = lambda c: f(ref.get(c, {}).get("ratio_nose"), 2)
        t82 = (tv.get("ET 8 Hz 2 mm") or {}).get("oracle") or {}
        A(f"- **In simulation** (sim2: {B1.get('n_writers')} synthetic writers, essential and Parkinsonian tremor at 0.3-2 mm, "
          f"a page sensor with DeltaPen's measured error): B1 draws {f(B1.get('P_nib_mW_tremor_mean'), 1)} mW while correcting "
          f"(the same nib without the balance: {f(B2.get('P_nib_mW_tremor_mean'), 0)} mW"
          + (f"; the Rev J C1S nose: {f(_c1s_ref_P(sim), 1)} W in sim2j's runs" if _c1s_ref_P(sim) else "") + "). "
          f"With the project's frozen tracker it leaves {rr('ET 8 Hz 1 mm')} of the tremor's ink error at 8 Hz 1 mm and "
          f"{rr('ET 12 Hz 1 mm')} at 12 Hz 1 mm (the Rev J nose: {jr('ET 8 Hz 1 mm')} and {jr('ET 12 Hz 1 mm')}), but the "
          f"tracker does not act at 4 Hz, at 0.3 mm or on the Parkinsonian tremor ({F['idle_rng']} left). With perfect "
          f"knowledge of the tremor the same nib leaves {F['o_small_rng']} up to 1 mm"
          + (f" (the Rev J nose: {_ref_rng(F, small=True)})" if _ref_rng(F, small=True) else "")
          + f" and {F['o_big_rng']} at 2 mm, where its +-1 mm reach clips"
          + (f" (the Rev J nose, +-6 mm: {_ref_rng(F, small=False)})" if _ref_rng(F, small=False) else "")
          + (f"; a +-1.5 mm version leaves {f(t82.get('ratio_B1w'), 2)} at 8 Hz 2 mm (+-1 mm: {f(t82.get('ratio_B1'), 2)}) "
             f"for {f(t82.get('P_B1w_mW'), 0)} mW" if t82 else "") + ". "
          f"Readable words out of 10: {f(B1.get('words_per10_off'), 1)} without the nib, {f(B1.get('words_per10_nib'), 1)} "
          f"with it, {f(B1.get('words_per10_oracle'), 1)} with perfect knowledge; tremor-free writing moved "
          f"{f(B1.get('clean_moved_um_mean'), 1)} um. Today the tracker, not the nib, limits the benefit, and large tremor "
          f"stays study W's collar's job. SIM (section 5.3).")
    else:
        A("- **In simulation:** the sim2 runs had not finished when this page was generated (section 5.3).")
    A(f"- **Slim 12-16 mm core:** magnet-and-coil nibs around a D1 refill do not fit (they run out of force or of travel). "
      f"Piezo benders do: " + (f"+-{f(pz_best['travel_mm'], 2)} mm with {mw(pz_best['P_cont_W'])} mW at {f(pz_best['od_mm'], 0)} mm "
      f"(with the counter-face; CALC)" if pz_best else "see the slim cards") + ". That is a separate branch, not the first prototype."
      + (f" In simulation the slim piezo stage (B3, +-{f(c_slim_piezo.get('travel_under_load_mm'), 2)} mm under load) leaves "
         f"{f(B3.get('tremor_left_ratio_mean'), 2)} of the tremor ink error with the tracker and "
         f"{f(B3.get('tremor_left_ratio_oracle_mean'), 2)} with perfect knowledge, at {f(B3.get('P_nib_mW_tremor_mean'), 0)} mW of "
         "drive power (SIM)." if B3 else ""))
    pf = rec.get("P_at_Fs") or {}
    sens = {float(k): {"P_cont_W": v * 1e-3} for k, v in pf.items()}
    A("- **Not proven, and the biggest unknown is the ink force.** Nobody has published the lowest force at which a ballpoint "
      "still writes; 0.15 N is 4.6 x below the lowest maker's test load found (0.69 N). The balance keeps its ten-fold "
      "advantage at any force, but the ball's drag grows with it: B1 needs about "
      f"{mw(sens.get(0.15, {}).get('P_cont_W'), 0)} mW at 0.15 N, {mw(sens.get(0.3, {}).get('P_cont_W'), 0)} mW at 0.3 N and "
      f"{mw(sens.get(0.69, {}).get('P_cont_W'), 0)} mW at 0.69 N (CALC). Also unproven: the real magnet strength, that the face "
      "mechanism behaves as modelled, the friction numbers, the wire fatigue with real clamps, and every tremor result "
      "(simulated). Nothing was built or measured.")
    A("- **Do next:** G1 measures the ink force and the friction (EXP-B20, EXP-B21); G2 benches the counter-face (EXP-B22), the "
      "actuator coupon (EXP-B23) and the wires (EXP-B25); then the one- and two-axis nib on the tremor rig (G3, G4).")
    A("")
    A("Evidence labels: CALC (a calculation in `bnib/`), SIM (an executed sim2 run), LIT / MFR (a ledger id in "
      "`docs/evidence.csv` or this study's `results/bnib/evidence_rows.csv`), ASSUMPTION (unmeasured), PROPOSED DESIGN. "
      "The results are in `results/bnib/bnib.json`; the nib's interface in `config/nib.yaml`.")
    A("")
    A("## 1. How the balance works")
    A("")
    A("![How the balance works](../results/bnib/fig_balance_principle.png)")
    A("")
    A("(a) Today: the spring pushes the refill along the pen from the moving carrier. The paper's push on the ball is "
      "vertical; its component across the pen, F_s cot(theta), must be held by the nib's coils whenever the ball is down. "
      "(b) Counter-face: the spring pushes a face on the handle, set parallel to the paper, against the refill's rolling rear "
      "end. The paper's push (up) and the face's push (down) are parallel, so the refill needs no sideways force from the "
      "nib; the two forces are offset along the pen, and that couple goes into the carrier's bushings and the wires' tilt "
      "stiffness, not the coils. When the nib moves, the refill translates parallel to the paper, so its end slides along the "
      "face and the face does not move. When the ball lifts, the refill moves forward, the face lands on a stop set a small "
      f"gap ({f((_rules(sim).get('chosen') or {}).get('face_gap_mm', 0.15), 2)} mm, a tuned rule) beyond its writing position "
      "and leaves the refill: nothing is held in the air. The stop and the face's "
      "orientation are set slowly (seconds) by three small screw motors with no holding power, from the pen's motion sensor "
      "and the refill-slide sensor. CALC statics; PROPOSED DESIGN.")
    A("")
    A("One limit of the IMU schedule: the motion sensor knows gravity, not the paper. On a sloped desk the face is set for a "
      "horizontal page and leaves F_n sin(slope) across the pen: about 17 / 34 / 67 mN at 5 / 10 / 20 deg of slope, i.e. "
      "about 2 / 7 / 28 mW of holding (CALC, Km upper bound), still inside the 0.1 W limit but a large share of the balance. "
      "A slope setting in the app, or the slide-cam variant (c'), whose cam reads the tilt from the refill's slide, i.e. "
      "relative to the paper, removes it; roll still needs a reference (EXP-B28 measures both).")
    A("")
    A(f"Balance quality (CALC, Monte Carlo over tilt 35-75 deg, all rolls, oil and gel ink, six papers, spring +-20 %, "
      f"IMU tilt / roll errors 1 / 2 deg): residual {f(bq.get('c_counterface imu2', {}).get('residual_contact_mean_N', 0) * 1e3, 1)} mN mean "
      f"({f(100 * bq.get('c_counterface imu2', {}).get('balance_ratio_mean', 0), 0)} % of the unbalanced "
      f"{f(bq.get('c_counterface imu2', {}).get('unbalanced_mean_N', 0) * 1e3, 0)} mN), 95th percentile "
      f"{f(bq.get('c_counterface imu2', {}).get('residual_contact_p95_N', 0) * 1e3, 1)} mN, pen-up "
      f"{f(bq.get('c_counterface imu2', {}).get('residual_penup_mean_N', 0) * 1e3, 1)} mN (the moving mass's weight). The "
      f"scheduled bias spring leaves {f(bq.get('b_bias (ungated)', {}).get('residual_contact_mean_N', 0) * 1e3, 1)} mN in "
      f"contact but {f(bq.get('b_bias (ungated)', {}).get('residual_penup_mean_N', 0) * 1e3, 0)} mN during pen-up unless a "
      f"clutch releases it; a keyed grip instead of the roll motor leaves "
      f"{f(bq.get('c_counterface keyed', {}).get('residual_contact_mean_N', 0) * 1e3, 1)} mN. "
      f"![balance quality](../results/bnib/fig_balance_quality.png)")
    A("")
    A("## 2. Results cards")
    A("")
    A("Common conditions (CALC): duty A = sinusoidal correction 0.2 mm rms per axis at 8 Hz, writing at 30.5 mm/s (LIT CON-20) "
      "in all directions, ball on the paper 70 % of the time (ASSUMPTION); duty B = 0.5 mm rms for the +-1 mm nibs; refill "
      "spring 0.15 N along the pen (ASSUMPTION); friction map (LIT CON-13 + ASSUMPTION shapes); Km at the image-method upper "
      "bound (the optimiser checks travel at 0.7 x); 30 degC room; two-node thermal model with the governor; coils 2.5 ohm at "
      "3.7 V / 1.5 A. For reference, the C1S nose's mean power (70 % contact, 1 mm rms duty): " +
      ", ".join(f"{r['theta_deg']:.0f} deg {r['P_mean_W']:.2f} W" for r in rc.get("rows", [])) + " (CALC). The cards use each "
      "candidate's hand-sized design with the same actuator (b-g); the optimised designs are in section 3.")
    A("")
    A("![power vs tilt, 24 mm](../results/bnib/fig_power_vs_tilt_pen24.png)")
    A("")
    for grip, head in (("pen24", "### 2.1 The 24 mm pen (DEC-029)"), ("slim14", "### 2.2 The slim core (14 mm; the 12-16 mm trade study)")):
        A(head)
        A("")
        for k, c in cards.items():
            if k.startswith(grip + "|"):
                A(card_md(c))
        if grip == "pen24":
            col = (S.get("candidates") or {}).get("collar") or {}
            A(f"Candidate (g)'s coarse stage is study W's pivot collar (read-only, CALC by study W): pivot {f(col.get('z_p_mm'), 0)} mm, "
              f"+-{f(col.get('travel_mm'), 1)} mm; its own holding power is study W's to report.")
            A("")
    A("## 3. Trade-offs and the recommendation")
    A("")
    A("Multi-objective search (CALC; `bnib/optimise.py`): CMA-ES on epsilon-constraint problems (minimise continuous power "
      "subject to a travel floor at Km x 0.7, the bore, Goodman >= 1.5, bandwidth >= 40 Hz, skin <= 41 degC), every "
      "evaluated point kept, fronts read off the pooled points; no weighted score. The translation family's power chain is "
      "exactly differentiable and was re-written in PyTorch; its gradient matches finite differences to "
      f"{_grad_err(opt)} and an L-BFGS polish of the CMA-ES optima lowered the power by a further few per cent (the optima "
      "sit on the bore and on the magnet and coil thickness bounds).")
    A("")
    A(_front_table(opt))
    A("")
    A(_nondom_table(opt))
    A("")
    A("![Pareto 24 mm](../results/bnib/fig_pareto_pen24.png)")
    A("")
    A("![Pareto slim](../results/bnib/fig_pareto_slim.png)")
    A("")
    A("**Recommendation: B1 (candidate c, optimised at a +-1.0 mm travel floor).** Reasons: among the +-1 mm designs that use "
      "a standard D1 refill and need no clutch, it has the lowest power and it meets the 0.1 W holding limit (REQ-RVJ-N10) "
      "by a factor of about 30 even with 30 % weaker magnets; it keeps a ten-fold advantage over the unbalanced nib at any "
      "ink force, although its own power grows with the force through the ball's drag (`fig_ink_force_sensitivity.png`: "
      "G1 sets the power and thermal budget, not the architecture); a moving coil has no negative stiffness and no pull on "
      "the suspension; unpowered it writes like a normal pen; its parts are ordinary (wires, flat coils, magnets, a face on a "
      "flexure, three small screw motors). The steeper tip (e) is as frugal but needs a custom short cartridge; the slide-cam "
      "variant (c') saves a motor if its cam can be made; (g), the same nib at +-0.5 mm under study W's collar, waits with "
      "the collar's bench experiment (DEC-051). The knee of B1's front lies between +-0.75 and +-1.25 mm: beyond that the "
      "coils must reach further and the power climbs. Fallbacks in order: the EPM-clutched bias (b'), then the unbalanced "
      "nib (f) only with a lower ink force or at tilts above about 50 deg. (a), (b) without a clutch and (d) alone do not "
      "solve the problem." + _travel_option_md(opt, sim))
    A("")
    A("## 4. The recommended nib (B1) for the first prototype")
    A("")
    A(f"Design point (PROPOSED DESIGN, `optimise.py`): poles {f(x.get('w', 0) * 1e3, 2)} mm square x "
      f"{f(x.get('t_m', 0) * 1e3, 2)} mm N52, coil layers {f(x.get('t_c', 0) * 1e3, 2)} mm, four Ti-6Al-4V wires "
      f"{f(x.get('wire_d', 0) * 1e3, 3)} mm x {f(x.get('wire_L', 0) * 1e3, 1)} mm, travel +-{f(x.get('travel', 0) * 1e3, 2)} mm. "
      f"Km {f(rec['Km_tip'], 3)} N/sqrt(W) at the tip (upper bound), suspension {f(rec['k_tip'], 1)} N/m, first parasitic "
      f"mode {f(rec['f_par_Hz'], 0)} Hz, wire Goodman SF {f(rec['SF'], 2)} (CALC). Layout: `results/bnib/layout_parts.json`; "
      "CAD: `mechanics/cad/bnib.py` -> `results/bnib/bnib_assembly.step`, `drawing_bnib.png`.")
    A("")
    A("![B1 drawing](../results/bnib/drawing_bnib.png)")
    A("")
    A("**Bill of materials** (evidence per line):")
    A("")
    A("| item | description | qty | evidence | part number |")
    A("|---|---|---|---|---|")
    for b in res["bom"]:
        A(f"| {b['item']} | {b['description']} | {b['qty']} | {b['evidence']} | {b['part_number']} |")
    A("")
    A("**What is unproven:** " + " ".join(f"({i + 1}) {u}" for i, u in enumerate(rec["unproven"])))
    A("")
    dd = res["decision"]
    A(f"### {dd['id']}: {dd['title']}")
    A("")
    for s in dd["decision"]:
        A(f"- {s}")
    A("")
    A("Because: " + " ".join(dd["because"]))
    A("")
    A("Revisit if: " + " ".join(f"({i + 1}) {s}" for i, s in enumerate(dd["revisit_if"])))
    A("")
    A("Affects: " + "; ".join(dd["supersedes_or_affects"]) + ".")
    A("")
    A("### Requirements (proposed)")
    A("")
    A("| id | requirement | value | now | verified by | gate |")
    A("|---|---|---|---|---|---|")
    for r in res["requirements"]:
        A(f"| {r['id']} | {r['title']} | {r['requirement']} | {r['status_now']} | {r['verified_by']} | {r['gate']} |")
    A("")
    A("### Experiments (proposed; mapped to gates G1-G4 and to study M's rig experiments)")
    A("")
    A("| id | gate | what | rig | decides |")
    A("|---|---|---|---|---|")
    for e in res["experiments"]:
        A(f"| {e['id']} | {e['gate']} | {e['what']} | {e['rig']} | {e['decides']} |")
    A("")
    A("## 5. Details")
    A("")
    A("### 5.1 Every load on the nib, and why the duty model missed the static term")
    A("")
    A("Vector statics at the ball (`bnib/contact.py`): the refill's axial balance fixes the normal force, "
      "N = F_s' / (sin(theta) - mu (v . a)) with F_s' = F_s -+ h_sl, and the load on each nib axis is Q_i = -F . u_i (no "
      "constant multiplier between the axial force and the normal force). With friction the tilt-plane load lies in the band "
      "F_s cot(theta -+ phi_f), tan(phi_f) = mu. Contact Jacobian: dx_ink = dq1 / sin(theta) h + dq2 t2, and the refill slides "
      "by cot(theta) dq1 along the pen. The load list (`loads.load_catalogue`):")
    A("")
    A("| load | formula | status |")
    A("|---|---|---|")
    for r in loads.get("catalogue", []):
        A(f"| {r['load']} | {r['formula']} | {r['status']} |")
    A("")
    A(f"C1S reconciliation (CALC): the review's static term reproduces exactly ({f(rv.get('35', {}).get('P_W'), 4)} / "
      f"{f(rv.get('50', {}).get('P_W'), 4)} / {f(rv.get('75', {}).get('P_W'), 4)} W; the single-node screen reaches 120 degC "
      f"in {f((loads.get('review_check') or {}).get('time_to_120C_s', {}).get('1.628W'), 1)} s at 1.63 W). Study N's duty model "
      f"(`nose2/designs.duty_forces`, read-only) predicts {f(nd.get('P_tremor_W'), 3)} W for the tremor duty; adding the static "
      f"term at 50 deg gives {f(rc.get('duty_model_plus_static_50deg_W'), 2)} W. Why it was missed: " +
      " ".join(rc.get("why_missed", [])))
    A("")
    sp = (rec.get("sim2j_power") or {}).get("split") or {}
    if sp:
        nom, nn, fc = sp.get("nominal", {}), sp.get("no_hall_noise", {}), sp.get("F_c_0.075", {})
        A(f"sim2j measured it (SIM, `results/sim2j/power_split.json`, writer 0, tremor-free, nose held centred): nominal "
          f"{f(nom.get('P_cu_mean_W'), 2)} W ({f(nom.get('P_cu_ball_on_paper_W'), 2)} W with the ball on the paper, "
          f"{f(nom.get('P_cu_lifted_W'), 2)} W lifted); without the Hall noise {f(nn.get('P_cu_mean_W'), 2)} W; with a "
          f"0.075 N spring {f(fc.get('P_cu_mean_W'), 2)} W. The lead's reading: about 1.1 W is the static side load, about "
          "0.74 W the servo reacting to unfiltered Hall noise (hence the filtered servo here, REQ-RVJ-C04), about 0.4 W "
          "friction and holding. DEC-046 (recorded by the lead) sets the principle: the static side load is carried "
          "mechanically, <= 0.1 W steady coil heat with the ball on the paper over 35-75 deg (REQ-RVJ-N10); this study "
          "proposes the mechanism (DEC-050, section 4).")
        A("")
    A("![C1S reconciliation](../results/bnib/fig_c1s_reconciliation.png)")
    A("")
    A("### 5.2 Models")
    A("")
    A("- Magnetics (`magnetics.py`, `actuators.py`): magpylib cuboids with iron images (an upper bound), full-coil Lorentz "
      "integration over the stroke; a surrogate for the optimiser calibrated to 48 magpylib maps (0.65 % rms on held-out "
      "geometries). Moving coil: constant gap, no pull, no negative stiffness; the keeper pull loads only the handle.")
    A("- Flexures (`flexure.py`): fixed-guided wires with tension/compression, root moment x Kt, Goodman at the STOP travel, "
      "buckling, violin modes; loaded eigenmodes of refill + carrier with the ink force's geometric stiffness and the ball "
      "stuck (pre-sliding stiffness); tolerance Monte Carlo; drops with axial stops. The gimbal candidate reuses "
      "`revj1/gimbal.py` (co-rotational cross-strip model) by import.")
    A("- Thermal (`thermal.py`): coil and shell nodes, the shell a PEEK fin with a graphite spreader, a governor that scales "
      "the current before the coil (110 degC) or the skin (41 degC) limit.")
    A("- Piezo (`actuators.piezo_stage`): the force-travel line of the PICMA plates at -20 % tolerance, loaded resonance, "
      "the pencil study's recovery-driver power convention.")
    A("")
    fx = rec.get("flexure") or {}
    md = rec.get("modes") or {}
    tm = rec.get("tolerance_mc") or {}
    km = rec.get("km_map") or {}
    sh = rec.get("shock") or {}
    A("B1's nonlinear flexure and magnetics checks (CALC):")
    A("")
    A(f"- Wires: lateral stiffness {f(fx.get('k_lat_N_m'), 1)} N/m at the tip (suspension mode {f(md.get('suspension_Hz'), 1)} Hz "
      f"with the moving mass), axial {f(fx.get('k_axial_N_um'), 2)} N/um, violin mode {f(md.get('violin_Hz'), 0)} Hz; full-stop "
      f"strain {f((fx.get('strain_stop') or 0) * 1e3, 2)} x 1e-3, stress {f(fx.get('stress_stop_MPa'), 0)} MPa with Kt 1.8 "
      f"-> Goodman SF {f(fx.get('goodman_SF'), 2)} at 43.2 M cycles (Ti-6Al-4V, 530 MPa x 0.85: AMF-20 low end, ASSUMPTION "
      f"knock-down); static SF at the stop {f(fx.get('static_SF_stop'), 1)}; sidesway buckling of the four wires "
      f"{f(fx.get('P_buckle_N'), 2)} N in compression (the axial stops carry drops).")
    A(f"- Loaded eigenmodes of refill + carrier (planar beam with the ink force's geometric stiffness): ball free "
      + ", ".join(f(x, 0) for x in (md.get('pen_up_Hz') or [])[:4]) + " Hz; ball stuck on the paper "
      + ", ".join(f(x, 0) for x in (md.get('ball_stuck_Hz') or [])[:4]) + " Hz. The first parasitic mode sets the bandwidth "
      "(mode / 3).")
    if tm:
        A(f"- Tolerances (Monte Carlo, wire diameter +-2 %, length +-0.05 mm, modulus +-4 %, Kt 1.3-2.5, preload 0-0.3 N; "
          f"ASSUMPTION ranges): stiffness p5/p50/p95 " + " / ".join(f(x, 1) for x in tm.get("k_lat_p5_p50_p95", [])) +
          " N/m; Goodman SF p1/p5/p50 " + " / ".join(f(x, 2) for x in tm.get("goodman_SF_p1_p5_p50", [])) + ".")
    if sh.get("rows"):
        A("- Drops: " + "; ".join(f"{f(r['g'], 0)} g -> wire stress {f(r['wire_stress_MPa'], 0)} MPa (stop engaged: {r['stop_engaged']})"
                                   for r in sh["rows"]) + f"; buckled wires stay elastic behind {f(sh.get('stop_axial_um'), 0)} um stops: "
          f"{sh.get('buckled_elastic')}.")
    gf = rec.get("guide_friction") or {}
    if gf.get("rows"):
        r35 = gf["rows"][0]
        P = gf.get("P_B1", {})
        ct = gf.get("couple_tilt", {})
        A(f"- The counter-face moves the static load, it does not delete it: the paper's and the face's pushes are parallel but "
          f"70 mm apart, a couple of {f(r35['couple_mNm'], 1)} mN m at 35 deg (N taken as F_s / sin(theta), conservative). "
          f"Inside the carrier it loads the two refill bushings with {f(r35['sum_R_counterface_N'], 2)} N in all "
          f"(the spring-along-the-pen design: {f(r35['sum_R_spring_N'], 2)} N), so the refill's slide friction h = mu_g "
          f"sum|R| grows, and h cot(theta) acts across the pen. With a ball or roller guide (mu_g 0.005, ASSUMPTION) h = "
          f"{f(r35['h_cf_mu0.005_N'] * 1e3, 1)} mN and B1 stays at {mw(P.get('0.005', {}).get('P_cont_W'))} mW; PTFE-lined "
          f"sleeves (0.05) give {f(r35['h_cf_mu0.05_N'] * 1e3, 0)} mN, {mw(P.get('0.05', {}).get('P_cont_W'))} mW and up to "
          f"{mw(P.get('0.05', {}).get('stuck_offset_hold_35deg_W'), 0)} mW of steady holding while the refill sticks; bare "
          f"metal (0.1) gives {mw(P.get('0.1', {}).get('P_cont_W'))} mW and {mw(P.get('0.1', {}).get('stuck_offset_hold_35deg_W'), 0)} "
          "mW stuck, which breaks REQ-RVJ-N10 at 35 deg. Hence REQ-BNIB-016 (a low-friction guide). The same couple tilts "
          f"the carrier on the wires' tilt stiffness ({f(gf.get('k_tilt_Nm_rad'), 1)} N m/rad): "
          + ", ".join(f"{k} deg {f(v['tilt_mrad'], 1)} mrad = {f(v['ball_offset_mm'], 2)} mm at the ball" for k, v in ct.items())
          + ": a slow, tilt-dependent offset that costs no current; the firmware can feed it forward from the IMU tilt, or "
          "the wires can sit on a larger circle (the tilt stiffness grows with its square). CALC.")
    if km.get("Km0"):
        A(f"- Actuator (magpylib map over the +-{f(rec['x'].get('travel', 0) * 1e3 + 0.2, 2)} mm stroke, iron images): Km "
          f"{f(km['Km0'], 3)} N/sqrt(W) at the centre, {f(km['Km_min'], 3)}-{f(km['Km_max'], 3)} over the stroke (variation "
          f"{f(100 * km['variation'], 0)} %), cross-coupling up to {f(100 * km['cross_max'], 1)} %; no negative stiffness "
          f"(moving coil); keeper pull {f(rec.get('keeper_pull_N'), 1)} N between two handle-fixed parts.")
    A("")
    A("### 5.3 Simulation")
    A("")
    A("sim2 (MuJoCo 3.6) and sim2j (the Rev J firmware, tracker and writers) imported read-only; `bnib/sim.py` adds: a "
      "translation nib (sim2's gimbal with a 10 m virtual pivot), the counter-face force and its follower stop, a seat "
      "spring, the nib's weight, the friction map on the ball's LuGre law, a filtered position servo (model-based observer "
      "on the noisy Hall reading), a two-node thermal model with the governor in the loop, a piezo stage servo, and a page "
      "sensor with a MEASURED-style error calibrated to DeltaPen (LIT OPT-02: per-10-ms-window translation error median "
      f"23.6 um, mean 68.3 um; held errors of lognormal size, median {f((sim.get('deltapen_calibration') or {}).get('median_m', 0) * 1e6, 1)} um, "
      f"log-sd {f((sim.get('deltapen_calibration') or {}).get('sigma'), 2)}, reproduce both; plus DeltaPen's idle drift and a 1.2 % "
      "scale error, OPT-75). The ideal 3 um sensor appears only as a labelled bound. Rules (servo bandwidth, face gap) were "
      "chosen on tuning writers 100-101 / seed 300 and frozen in `results/bnib/rules.json` before the test writers ran "
      "(B1 and B2: writers 0-3, B3: 0-2, seeds 200-203; the grid was shortened after two container restarts). Tasks: tremor-free writing (false correction), ET 4-12 Hz and PD 4.5-5.5 Hz tremor at "
      "0.3-2 mm, a thermal run at 35 deg with 2 mm tremor. The page sensor loses the page above 2 mm of lift (MFR OPT-54, "
      "as Rev J's parameters). Idealisations: the face is massless with a 5 um engagement "
      "ramp; the carrier cannot tilt (virtual pivot), so the couple's static 0.1-0.17 mm offset is not in these runs; the "
      "refill's slide friction is 10 mN (conservative for a rolling guide, optimistic for PTFE at 35 deg); gravity acts on "
      "the nib only (sim2's H1 convention for the rest of the pen); controllers: 'none' (nib held centred), the project's "
      "frozen guarded tracker (sim2j), and perfect knowledge of the handle's tremor (the mechanism's limit).")
    A("")
    A(sim_md(sim))
    A(by_cell_md(sim))
    A(sim_analysis_md(sim, cards))
    idl = sim.get("ideal") or {}
    if idl:
        A(f"Ideal page sensor (a BOUND): ink error {f(idl.get('ink_err_um_ideal'), 0)} um vs {f(idl.get('ink_err_um_deltapen'), 0)} um "
          f"with the DeltaPen-calibrated sensor in the same {idl.get('n')} cases (ratio {f(idl.get('ratio_ideal'), 2)} vs "
          f"{f(idl.get('ratio_deltapen'), 2)}). SIM.")
        A("")
    rules = sim.get("rules") or {}
    if rules:
        A(f"Frozen rules: {rules.get('chosen')} (tuning grid: " + "; ".join(
            f"fi {g['servo_fi']:g} Hz, gap {g['face_gap_mm']:g} mm: ink {g['ink_err_um']:.0f} um, moved {g['moved_um']:.1f} um, "
            f"P {g['P_nib_W'] * 1e3:.1f} mW" for g in rules.get("grid", [])) + ").")
        A("")
    A("![sim cards](../results/bnib/fig_sim_cards.png)")
    A("")
    A("### 5.4 The minimum ink force")
    A("")
    A(ik.get("finding", ""))
    A("")
    A("| source | tip | load (N) | angle (deg) | kind |")
    A("|---|---|---|---|---|")
    for s in ik.get("sources", []):
        ld = s.get("load_N")
        ld = "-" if ld is None else (f"{ld[0]:g}-{ld[1]:g}" if isinstance(ld, (list, tuple)) else f"{ld:.3g}")
        an = s.get("angle_deg")
        an = "-" if an is None else (f"{an[0]:g}-{an[1]:g}" if isinstance(an, (list, tuple)) else f"{an:g}")
        A(f"| {s['id']} | {s['tip']} | {ld} | {an} | {s['kind']} |")
    A("")
    A("![ink force](../results/bnib/fig_ink_force_sensitivity.png)")
    A("")
    A("### 5.5 The interface file")
    A("")
    A("`config/nib.yaml` is the one versioned definition of the nib's physical interface: spring and paper-normal force, "
      "tilt range, friction map, contact Jacobian, static side load, effective actuator arm, Km over the stroke (magpylib), "
      "moving mass and suspension, travel, sensors (nib Hall, the DeltaPen-calibrated page sensor, IMU), the two-node thermal "
      "parameters and governor, the counter-face, the drive, the failure state and the C1S reference values; every leaf has "
      "a unit and an evidence status. It is generated by `python3 -m bnib.run_study` and checked against the code by the tests.")
    A("")
    A("### 5.6 Thermal")
    A("")
    ev = rec.get("eval") or {}
    run = ((ev.get("thermal") or {}).get("run_35deg_30min")) if ev.get("thermal") else None
    A(f"Two-node model (CALC): B1 at 35 deg (its largest load) in a 30 degC room for 30 min: coil {f(rec.get('T_coil_C'), 1)} "
      f"degC, skin {f(rec.get('T_skin_C'), 1)} degC; the governor never acts. The unbalanced nib (f) at 35 deg: coil "
      f"{f(cards.get('pen24|f_translation', {}).get('T_coil_C'), 1)} / skin {f(cards.get('pen24|f_translation', {}).get('T_skin_C'), 1)} "
      f"degC; the long-arm gimbal (a): {f(cards.get('pen24|a_long_arm', {}).get('T_coil_C'), 1)} / "
      f"{f(cards.get('pen24|a_long_arm', {}).get('T_skin_C'), 1)} degC with the governor cutting its authority to "
      f"{f(cards.get('pen24|a_long_arm', {}).get('governor_min'), 2)}.")
    ths = [(k, v.get("thermal_35deg")) for k, v in (sim.get("cards") or {}).items() if v.get("thermal_35deg")]
    if ths:
        A("")
        A("The long thermal run (SIM + CALC): writer 0 writes the full sentence at 35 deg with 2 mm ET tremor, nib on; the "
          "simulated mean power drives the two-node model with the governor for 30 min, and the run is repeated from that "
          "hot state with the governor in the servo loop: " + "; ".join(
              f"{k}: {f(t['P_nib_mean_W'] * 1e3, 1)} mW -> after 30 min coil {f(t['T_after_30min'][0], 1)} degC, skin "
              f"{f(t['T_after_30min'][1], 1)} degC, governor authority {f(t['gov_min_hot'], 2)} (ink error {f(t['ink_err_cold_um'], 0)} "
              f"-> {f(t['ink_err_hot_um'], 0)} um cold -> hot, words {f(t['words_cold'] * 10, 0)} -> {f(t['words_hot'] * 10, 0)} of 10)"
              for k, t in ths) + ".")
    A("")
    A("![thermal](../results/bnib/fig_thermal.png)")
    A("")
    A("### 5.7 Open issues")
    A("")
    for s in open_issues(res, S):
        A(f"- {s}")
    A("")
    A("### 5.8 Files")
    A("")
    A("`bnib/` (package; `python3 -m bnib.run_study [--quick]`; tests `bnib/tests/`), `results/bnib/` (bnib.json with "
      "stabpen.provenance, figures with CSV twins, layout_parts.json, evidence_rows.csv, rules.json, the CAD outputs), "
      "`config/nib.yaml`, `mechanics/cad/bnib.py`, this page.")
    A("")
    text = "\n".join(L)
    path = DOC if not quick else BUILD / "quick" / "balanced_nib.md"
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    return str(path)


def _rules(sim: Dict) -> Dict:
    r = (sim or {}).get("rules") or {}
    if not r:
        import json
        p = os.path.join(REPO_ROOT, "results", "bnib", "rules.json")
        if os.path.exists(p):
            try:
                r = json.load(open(p))
            except Exception:
                r = {}
    return r


def _parse_cell(k: str):
    kind, f0, _, amp, _ = k.split()
    return kind, float(f0), float(amp)


def sim_findings(sim: Dict) -> Dict:
    """What the B1 runs show, read off the cards (no new numbers): the cells where the tracker acts, where it does not,
    perfect knowledge up to 1 mm and at 2 mm, and the Rev J reference."""
    cards = (sim or {}).get("cards") or {}
    by = (cards.get("B1") or {}).get("by_cell") or {}
    act, idle, o_small, o_big = [], [], [], []
    for k, v in by.items():
        if v.get("ratio_mean") is None:
            continue
        kind, f0, amp = _parse_cell(k)
        (act if v["ratio_mean"] < 0.95 else idle).append((k, v["ratio_mean"]))
        if v.get("ratio_oracle") is not None:
            (o_small if amp <= 1.0 else o_big).append((k, v["ratio_oracle"]))
    rng = lambda L: (f"{min(x for _, x in L):.2f}-{max(x for _, x in L):.2f}" if len(L) > 1 else
                     (f"{L[0][1]:.2f}" if L else "-"))
    return {"by": by, "ref": ((sim or {}).get("sim2j_revJ_reference") or {}).get("cells") or {},
            "active": sorted(act, key=lambda x: x[1]), "idle": idle, "o_small": o_small, "o_big": o_big,
            "idle_rng": rng(idle), "o_small_rng": rng(o_small), "o_big_rng": rng(o_big),
            "travel": ((sim or {}).get("travel") or {}).get("cells") or {}, "diag": (sim or {}).get("oracle_diagnosis") or {}}


def sim_analysis_md(sim: Dict, cards: Dict) -> str:
    """The paragraphs under the simulation tables: what the runs show, one case taken apart, the travel variant."""
    F = sim_findings(sim)
    sc = (sim or {}).get("cards") or {}
    B1, B2, B3 = sc.get("B1") or {}, sc.get("B2") or {}, sc.get("B3") or {}
    if not F["by"]:
        return ""
    L = []
    act = "; ".join(f"{k} {v:.2f}" for k, v in F["active"])
    idle = ", ".join(k for k, _ in F["idle"])
    L.append(f"What the runs show (SIM). The tracker acts where it detects the tremor ({act}; the ratio is the ink error "
             f"with the nib over the ink error with the nib held centred) and stays off in {idle} ({F['idle_rng']}), as in "
             f"sim2j's Rev J runs at 4 Hz and 0.3 mm; sim2j did not run the Parkinsonian model (ASSUMPTION shape: 4.5-5.5 Hz, "
             f"frequency jitter, waxing and waning). With perfect knowledge the same nib leaves {F['o_small_rng']} up to 1 mm "
             f"and {F['o_big_rng']} at 2 mm. B1 draws {f(B1.get('P_nib_mW_tremor_mean'), 1)} mW while correcting and "
             f"{f(B1.get('P_nib_mW_clean_mean'), 1)} mW in tremor-free writing; the unbalanced B2 draws "
             f"{f(B2.get('P_nib_mW_tremor_mean'), 1)} mW for the same correction (ratio {f(B2.get('tremor_left_ratio_mean'), 2)} "
             f"vs {f(B1.get('tremor_left_ratio_mean'), 2)}): the balance changes the power, not the correction. "
             f"Tremor-free writing moved {f(B1.get('clean_moved_um_mean'), 1)} um on average (max "
             f"{f(B1.get('clean_moved_um_max'), 1)} um): the frozen tracker makes no false correction here. "
             + (f"The slim piezo stage B3 (+-{f((cards.get('slim14|h_piezo') or {}).get('travel_under_load_mm'), 2)} mm under "
                f"load) leaves {f(B3.get('tremor_left_ratio_mean'), 2)} with the tracker and "
                f"{f(B3.get('tremor_left_ratio_oracle_mean'), 2)} with perfect knowledge at "
                f"{f(B3.get('P_nib_mW_tremor_mean'), 0)} mW of drive power (the pencil study's recovery-driver convention)."
                if B3 else ""))
    L.append("")
    dd = F["diag"] or {}
    d = dd.get("B1") or {}
    dw = dd.get("B1w") or {}
    ref = F["ref"].get(d.get("cell", ""), {}) if d else {}
    if d and d.get("writing"):
        wr = d["writing"]
        gx, gy = (d.get("page_gain_xy") or [None, None])[:2]
        lx, ly = (d.get("lag_ms_xy") or [None, None])[:2]
        ww = dw.get("writing") or {}
        gain_w = ((wr["ink_oracle_um"] - ww["ink_oracle_um"]) / wr["ink_oracle_um"]
                  if ww.get("ink_oracle_um") and wr.get("ink_oracle_um") else None)
        L.append(f"One case taken apart ({d['cell']}, writer {d['w']}, seed {d['seed']}; SIM, `sim.oracle_diagnosis`). The nib "
                 f"reproduces the commanded page offset with gain {f(gx, 3)} / {f(gy, 3)} (x / y) and a {f(lx, 1)} / {f(ly, 1)} ms "
                 f"lag (the oracle previews {f(d.get('preview_ms'), 1)} ms). While the letters are written the handle's tremor at "
                 f"its tip point is {f((wr.get('handle_tremor_rms_um') or 0) * 1e-3, 2)} mm rms (95th percentile "
                 f"{f(wr.get('handle_tremor_p95_mm'), 2)} mm) and passes B1's +-{f(d['reach_mm'], 2)} mm reach "
                 f"{f(100 * (wr.get('share_beyond_reach') or 0), 1)} % of the time. Of the {f(wr.get('ink_oracle_um'), 0)} um left "
                 f"(rms deviation of the ink from the tremor-free run; {f(wr.get('ink_none_um'), 0)} um with the nib held centred) "
                 f"the clipped peaks account for {f(wr.get('clip_residual_um'), 0)} um and the seed-to-seed floor for "
                 f"{f(wr.get('floor_um'), 0)} um (in quadrature)"
                 + (f"; the +-1.5 mm variant clips {f(ww.get('clip_residual_um'), 0)} um and leaves {f(ww.get('ink_oracle_um'), 0)} um, "
                    f"{f(100 * gain_w, 0)} % less" if gain_w is not None else "")
                 + f". The command falls below half its intended size in {f(100 * d['gated_share'], 1)} % of the samples inside "
                 f"the reach (a median {f(d.get('gated_ms_after_touchdown_median'), 0)} ms after a touchdown: the firmware fades "
                 f"its authority back in over 50 ms whenever the page sensor has lost the page). The pen-up handle lift in this "
                 f"run is {f(d.get('handle_lift_up_median_mm'), 2)} mm median ({f(d.get('handle_lift_up_p90_mm'), 2)} mm at the "
                 f"90th percentile) against the sensor's {f(d.get('page_lift_max_mm'), 1)} mm cut-off. The Rev J nose's +-6 mm "
                 f"(its usable tip travel, sim2j/revj.py) never clips"
                 + (f" (its perfect-knowledge ratio in this cell: {f(ref.get('ratio_oracle'), 2)}, B1's: "
                    f"{f((F['by'].get(d['cell']) or {}).get('ratio_oracle'), 2)})" if ref else "") + ".")
        L.append("")
    ls = ((sim or {}).get("lift_cutoff_sensitivity") or {}).get("designs") or {}
    if ls.get("B1"):
        b = ls["B1"]
        n_, o_ = b.get("nose") or {}, b.get("oracle") or {}
        L.append(f"The page sensor's lift range matters (SIM, the same {n_.get('n')} cases run twice). A first run of the whole "
                 f"grid used sim2's default page lift cut-off, 0.8 mm, instead of the sensor's 2 mm (MFR OPT-54, as Rev J's "
                 f"parameters). The H1 writer lifts the handle by more than 0.8 mm between strokes, so the firmware lost the page "
                 f"at every lift and faded its authority back in over 50 ms after each touchdown, at the start of every stroke. "
                 f"With the 0.8 mm cut-off B1's tracker left {f(n_.get('ratio_lift08'), 2)} of the tremor (2 mm: "
                 f"{f(n_.get('ratio_lift2'), 2)}) and perfect knowledge {f(o_.get('ratio_lift08'), 2)} ("
                 f"{f(o_.get('ratio_lift2'), 2)}); readable words out of 10 with the tracker {f(n_.get('words10_lift08'), 1)} "
                 f"({f(n_.get('words10_lift2'), 1)}). The rules were re-tuned and the grid re-run with 2 mm; the first grid is "
                 f"kept in `bnib/build/sim_rows_lift08.json`. A page sensor that keeps the page through the lifts between strokes "
                 f"is part of the nib's performance (REQ-BNIB-017).")
        L.append("")
    tv = F["travel"]
    if tv:
        L.append("The travel variant (SIM, writers 0-2 with their test seeds; B1w = the optimiser's counter-face point at the "
                 "1.5 mm travel floor, the same frozen rules; case by case against B1):")
        L.append("")
        L.append("| cell | tracker ratio, +-1.0 / +-1.5 mm | perfect knowledge, +-1.0 / +-1.5 mm | words out of 10 with the tracker, +-1.0 / +-1.5 mm | nib power with the tracker, mW, +-1.0 / +-1.5 mm |")
        L.append("|---|---|---|---|---|")
        for cell, v in tv.items():
            n_, o_ = v.get("nose") or {}, v.get("oracle") or {}
            L.append(f"| {cell} | {f(n_.get('ratio_B1'), 2)} / {f(n_.get('ratio_B1w'), 2)} | {f(o_.get('ratio_B1'), 2)} / "
                     f"{f(o_.get('ratio_B1w'), 2)} | {f(n_.get('words10_B1'), 1)} / {f(n_.get('words10_B1w'), 1)} | "
                     f"{f(n_.get('P_B1_mW'), 1)} / {f(n_.get('P_B1w_mW'), 1)} |")
        L.append("")
        tsum = (sim or {}).get("travel") or {}
        if tsum.get("clean_moved_um_B1w") is not None:
            L.append(f"B1w in tremor-free writing: moved {f(tsum['clean_moved_um_B1w'], 1)} um, {f(tsum.get('clean_P_mW_B1w'), 1)} mW.")
            L.append("")
    return "\n".join(L)


def _ref_rng(F: Dict, small: bool = True) -> str:
    """The Rev J nose's perfect-knowledge ratios (sim2j, paired writers) in the cells up to 1 mm / at 2 mm."""
    v = []
    for k, r in (F.get("ref") or {}).items():
        if r.get("ratio_oracle") is None:
            continue
        amp = _parse_cell(k)[2]
        if (amp <= 1.0) == small:
            v.append(r["ratio_oracle"])
    if not v:
        return ""
    return f"{min(v):.2f}-{max(v):.2f}" if len(v) > 1 else f"{v[0]:.2f}"


def _c1s_ref_P(sim: Dict):
    cells = ((sim or {}).get("sim2j_revJ_reference") or {}).get("cells") or {}
    P = [v["P_nose_W"] for v in cells.values() if v.get("P_nose_W")]
    return sum(P) / len(P) if P else None


def _grad_err(opt: Dict) -> str:
    errs = []
    for pr in (opt.get("problems") or {}).values():
        for r in pr.get("runs", []):
            gc = (r.get("polish") or {}).get("gradient_check") or {}
            errs += [v["rel_err"] for v in gc.values()]
    return f"{max(errs):.0e} (relative, worst of {len(errs)} checks)" if errs else "-"


def _travel_option_md(opt: Dict, sim: Dict) -> str:
    """The travel is DEC-050's open parameter: the +-1.5 mm point on the same front (CALC) and what the simulation says."""
    b15 = None
    for r in ((opt.get("problems") or {}).get("pen24_c") or {}).get("runs", []):
        if abs(r["eps_T_mm"] - 1.5) < 1e-6 and r["feasible"]:
            b15 = r["best"]
    if not b15:
        return ""
    out = (f" The travel is the one parameter to settle before the build: the same architecture at the +-1.5 mm floor draws "
           f"{mw(b15['P_cont_W'])} / {mw(b15.get('P_cont_km070_W'))} mW (Km x 0.85 / 0.7) with {f(b15['m_eff_g'])} g moving "
           f"(CALC)")
    tv = (((sim or {}).get("travel") or {}).get("cells") or {})
    c2 = [(k, v["oracle"]) for k, v in tv.items() if v.get("oracle") and k.endswith("2 mm")]
    c2n = [(k, v["nose"]) for k, v in tv.items() if v.get("nose") and k.endswith("2 mm")]
    if c2:
        o1 = sum(v["ratio_B1"] for _, v in c2) / len(c2)
        o15 = sum(v["ratio_B1w"] for _, v in c2) / len(c2)
        n1 = sum(v["ratio_B1"] for _, v in c2n) / len(c2n) if c2n else None
        n15 = sum(v["ratio_B1w"] for _, v in c2n) / len(c2n) if c2n else None
        out += (f"; in the 2 mm cells it leaves {o15:.2f} of the tremor with perfect knowledge against {o1:.2f} at +-1.0 mm, "
                f"and {f(n15, 2)} against {f(n1, 2)} with today's tracker (SIM, section 5.3)")
    return out + (". Build +-1.0 mm for the demonstrator (G3-G4 test the balance and the power); choose +-1.5 mm if G4's "
                  "tremor set includes study R's severe class and a better estimate (DEC-052) is on the way.")


def _front_table(opt: Dict) -> str:
    L = ["| problem | travel floor (mm) | feasible | continuous power (mW, Km x 0.85 / x 0.7) | travel at Km x 0.7 (mm) | pen mass (g) | "
         "moving mass (g) | skin (degC) |", "|---|---|---|---|---|---|---|---|"]
    for pid, pr in (opt.get("problems") or {}).items():
        for r in pr.get("runs", []):
            b = r["best"]
            L.append(f"| {pid} | {r['eps_T_mm']:.2f} | {'yes' if r['feasible'] else 'no'} | {mw(b['P_cont_W'])} / "
                     f"{mw(b.get('P_cont_km070_W'))} | {f(b['travel_mm'])} | {f(b['mass_g'], 1)} | {f(b['m_eff_g'])} | {f(b['T_skin_C'], 1)} |")
    for g, v in (opt.get("piezo") or {}).items():
        P = sorted([p for p in v.get("points", []) if p.get("feasible_eps")], key=lambda p: -p["travel_mm"])[:3]
        for p in P:
            xx = p["x"]
            L.append(f"| {g} piezo {p['key']} ({xx['plate']} x {xx['n_p']} per axis, lever {xx['lam']:g}, {f(p['od_mm'], 0)} mm) | - "
                     f"| yes | {mw(p['P_cont_W'])} | {f(p['travel_mm'])} | {f(p['mass_g'], 1)} | {f(p['m_eff_g'])} | {f(p['T_skin_C'], 1)} |")
    return "\n".join(L)


def _nondom_table(opt: Dict) -> str:
    L = ["Non-dominated designs over all eight objectives (continuous and peak power, travel under load, pen mass, moving "
         "mass, diameter, skin temperature, nib sensor noise; every one fails benign), a sample per grip class (CALC):", "",
         "| grip | candidate | P cont (mW) | P peak (W) | travel (mm) | pen (g) | moving (g) | OD (mm) | CoM (mm) | skin (degC) | "
         "Hall noise (um) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for g, fr in (opt.get("fronts") or {}).items():
        P = sorted(fr.get("pareto_all", []), key=lambda p: p["P_cont_W"])
        n = len(P)
        pick = P[:: max(n // 6, 1)][:7] if n else []
        for p in pick:
            L.append(f"| {g} | {p['key']} | {mw(p['P_cont_W'])} | {f(p.get('P_peak_W'), 3)} | {f(p['travel_mm'])} | {f(p['mass_g'], 1)} | "
                     f"{f(p['m_eff_g'])} | {f(p['od_mm'], 0)} | {f(p.get('com_mm'), 0)} | {f(p['T_skin_C'], 1)} | {f(p.get('hall_noise_um'), 2)} |")
        L.append(f"| {g} | ({n} non-dominated of {fr.get('n_feasible')} feasible points) | | | | | | | | | |")
    return "\n".join(L)


def open_issues(res: Dict, S: Dict) -> List[str]:
    return [
        "The minimum reliable ink force is unknown (G1). The design value 0.15 N is below every test load found.",
        "Km is an image-method upper bound; the optimiser guards travel at 0.7 x, but power scales as 1/Km^2 (x 2 at 0.7).",
        "The counter-face is a new mechanism: its follower stop, the face flexure's friction and the IMU-based orientation "
        "are modelled, not demonstrated (EXP-B22, EXP-B28). The slide-cam and keyed variants trade motors for error.",
        "The refill's axial slide friction (0.01 N, ASSUMPTION) acts across the pen through cot(theta) whatever the balance; "
        "a low-friction bushing is part of the design.",
        "The piezo slim branch's packaging (several plates around a 2.35 mm refill in a 10-13 mm bore) was checked only by a "
        "width rule; no CAD.",
        "sim2 is not calibrated to hardware; the page sensor model is calibrated to DeltaPen on a Wacom tablet, not paper.",
        "The tracker, not the nib, limits the simulated benefit (as DEC-052 records for the programme): the estimator is "
        "study E's; B1's mechanism limit is what a better estimate can use.",
        "Reach: B1 has +-1.06 mm (a +-1.5 mm build of the same architecture costs about twice the power); the Rev J nose "
        "has +-6 mm. Study R's real tremor is smaller than the plan assumed (severe class typically 1.7 mm peak at the tip, "
        "moderate 0.24 mm; docs/real_data.md), so B1 covers the mild and moderate classes and part of the severe one; with "
        "no whole-pen actuator now (DEC-051), tremor beyond the nib's reach stays uncorrected in the first prototype.",
        "DEC-053 asks devices to be judged at three grip strengths: these runs used one (sim2's H1 writer, r_rot 0.5); the "
        "power includes the nib's static load, and the baseline is the same nib held centred.",
        "The Rev J reference (sim2j) is read from sim2j/build/et_rows.json at report time; sim2j's own runs set it.",
        "Squiggle motors are sold only in volume (AMF-15): a micro-stepper lead-screw fallback needs its own layout.",
        "Study W's collar (candidate g) was taken read-only and DEC-051 keeps it a bench experiment (EXP-W11); the combined "
        "coarse/fine controller was not simulated here.",
        "The IMU-scheduled face assumes a horizontal page: on a 10 deg writing slope it leaves about 34 mN across the pen "
        "(7 mW); a slope setting or the paper-referenced slide cam (c') is needed for sloped desks.",
        "The face schedule must follow the pen's tilt wobble while writing (about +-2.5 deg, LIT CON-02): with a 0.2 s "
        "response it lags by about 2 deg at 1 Hz (about 5 % residual); a 0.05 s response halves it.",
        "The counter-face's couple loads the refill guide (about 1 N in all at 35 deg); with PTFE sleeves the slide "
        "friction doubles B1's power and with bare metal it breaks REQ-RVJ-N10 at 35 deg: the guide must roll (REQ-BNIB-016, "
        "EXP-B22). The couple also tilts the carrier by up to 4.5 mrad (0.17 mm at the ball, static): a feed-forward item.",
        "The 0.13 mm wires are soft (3.8 N/m) and buckle sideways at 0.08 N of compression for all four: any assembly "
        "preload dominates their stiffness (0.3 N of tension triples it, tolerance Monte Carlo). Proposed: assemble with a "
        "set tension of about 0.1 N and keep the 20 um axial stops; EXP-B25 checks both.",
        "The actuator's cross-coupling reaches 27 % at the stroke corners (magpylib): the firmware needs the measured force "
        "map (EXP-B23), not a diagonal Km.",
    ]
