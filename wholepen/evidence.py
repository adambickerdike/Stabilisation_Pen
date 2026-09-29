r"""Proposed ledger rows of study W (results/wholepen/evidence_rows.csv), with the exact 23-column header of
docs/evidence.csv.  Literature rows only for sources this study opened (abstract, full text or, where stated, a web
search summary); 'derived simulation' / 'calculation' rows for this study's own results, their numbers filled in from
the result files at write time.  Ids only from the ranges given to study W: ACT-120...139, AMF-180...199,
HAP-115...129, PDT-63...74, CON-75...79, PAT-50...54, OPT-70...74.  Existing ledger rows are cited, not duplicated
(Gupta 2020 is PDT-08, Lin 2022 CON-04, Buki 2018 ACT-29, DeltaPen OPT-01/02, the GyroGlove sources ACT-25/28/61/81).
"""
from __future__ import annotations

import csv
import json
import os
from typing import Dict, List

from . import RESULTS, ROOT

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
          "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions",
          "locator", "limitations", "relevance_to_design", "transferability", "transferability_reason",
          "design_implication", "retrieved", "search_query", "stream", "lead_verification"]
RET = "2026-09-29"


def _lit() -> List[Dict]:
    R = []
    A = R.append
    A(dict(id="PDT-63", topic="PD: how often tremor affects writing itself",
           citation="Mascia MM, Orofino G, Cimino P, Cadeddu G, Ercoli T, Defazio G. Writing tremor in Parkinson's disease: frequency and associated clinical features. J Neural Transm (Vienna) 2022 (PMID 36289110)",
           year="2022", doi_or_url="https://doi.org/10.1007/s00702-022-02551-z", source_type="journal", evidence_class="physical human study",
           access_level="abstract only", task_or_setup="Clinical assessment of rest, action and writing tremor (on medication); a standardised sensory trick in those with action tremor",
           participants_or_bench="100 consecutive idiopathic PD patients", comparator="Other tremor types in the same patients",
           key_quantitative_findings="Writing tremor in 10 % of patients (26 % of those with postural/kinetic tremor); task-specific in 4/10, not task-specific in 6/10; severity not correlated with other tremor variants; sensory trick helped writing tremor in 2 patients; action tremor 'in up to 46 %' of PD (cited background)",
           units_and_conditions="% of patients; clinical ratings, on condition; no amplitudes", locator="Abstract (Europe PMC / publisher)",
           limitations="Abstract only; on medication; one centre; no displacement amplitude",
           relevance_to_design="Sets how many PD users need tremor correction while writing (a minority) versus rest/re-emergent tremor in pauses",
           transferability="medium", transferability_reason="Writing assessed directly, but no mm amplitudes",
           design_implication="Treat PD writing tremor as a minority need; design the PD mode around re-emergent tremor in pauses and slow strokes as well",
           retrieved=RET, search_query="WebSearch/Europe PMC: 'Writing tremor in Parkinson's disease: frequency and associated clinical features'", stream="PDT", lead_verification=""))
    A(dict(id="PDT-65", topic="PD tremor types (rest, mixed with lag = re-emergent, action)",
           citation="Gironell A, Pascual-Sedano B, Aracil I, Marin-Lahoz J, Pagonabarraga J, Kulisevsky J. Tremor Types in Parkinson Disease: A Descriptive Study Using a New Classification. Parkinsons Dis 2018:4327597",
           year="2018", doi_or_url="https://doi.org/10.1155/2018/4327597", source_type="journal", evidence_class="physical human study",
           access_level="abstract only", task_or_setup="Clinical classification of tremor type (I rest; II mixed same frequency, II-R with a time lag, II-C without; III action; IV mixed different frequencies)",
           participants_or_bench="315 consecutive PD patients with tremor", comparator="Between types",
           key_quantitative_findings="Type I 30 %; type II 50 % (II-R 25 %, II-C 25 %); type III 19 %; type IV 1 %; no association with the clinical variables studied",
           units_and_conditions="% of PD patients with tremor", locator="Abstract (Europe PMC, PMID 30363956)",
           limitations="Abstract only; clinical phenomenology, no amplitudes; one centre",
           relevance_to_design="A quarter of PD patients with tremor show re-emergent (lagged) tremor, which appears in pauses and slow strokes while writing",
           transferability="medium", transferability_reason="Types, not writing amplitudes",
           design_implication="Include a re-emergent class (tremor gated by movement) in every PD test", retrieved=RET,
           search_query="Europe PMC: Tremor Types in Parkinson Disease new classification", stream="PDT", lead_verification=""))
    A(dict(id="PDT-66", topic="PD: tremor over 7 years from diagnosis (PPMI)",
           citation="Pasquini J, Deuschl G, Pecori A, Salvadori S, Ceravolo R, Pavese N. The Clinical Profile of Tremor in Parkinson's Disease. Mov Disord Clin Pract 2023;10:1496-1506",
           year="2023", doi_or_url="https://doi.org/10.1002/mdc3.13845", source_type="journal", evidence_class="physical human study",
           access_level="abstract only", task_or_setup="Longitudinal MDS-UPDRS rest, postural and kinetic tremor scores, off and on medication, baseline to 7 years",
           participants_or_bench="397 de novo PD (PPMI)", comparator="Time; medication state",
           key_quantitative_findings="382 (96.2 %) showed tremor and 346 (87.2 %) rest tremor in at least one assessment over 7 years; off-state scores rose over time; tremor unresponsive to in-clinic dopaminergic medication in >= 20 % (rest), 30 % (postural), 38 % (kinetic) at each assessment",
           units_and_conditions="% of participants; clinical scores", locator="Abstract (Europe PMC, PMID 37868914)",
           limitations="Abstract only; clinical ratings; writing not assessed",
           relevance_to_design="Nearly every PD user will have some tremor at some point; a third of kinetic tremor does not respond to medication",
           transferability="medium", transferability_reason="Large cohort but clinical items, not writing", design_implication="PD tremor correction is worth designing for, with medication-resistant kinetic tremor the target",
           retrieved=RET, search_query="Europe PMC: clinical profile of tremor in Parkinson's disease PPMI", stream="PDT", lead_verification=""))
    A(dict(id="PDT-67", topic="NewHandPD: pen signals from PD patients and controls (the data set)",
           citation="Pereira CR, Weber SAT, Hook C, Rosa GH, Papa JP. Deep Learning-aided Parkinson's Disease Diagnosis from Handwritten Dynamics. SIBGRAPI 2016 (the NewHandPD data set, Sao Paulo State University)",
           year="2016", doi_or_url="http://sibgrapi.sid.inpe.br/col/sid.inpe.br/sibgrapi/2016/07.08.22.47/doc/opf-sibgrapi16.pdf", source_type="conference",
           evidence_class="physical human study", access_level="full text",
           task_or_setup="BiSP smart pen: CH1 microphone, CH2 finger grip, CH3 axial refill pressure, CH4-6 tilt and acceleration x, y, z; spirals and meanders drawn on a form",
           participants_or_bench="Paper: 35 individuals (14 PD, 21 controls); the downloaded archives hold 31 patient and 35 healthy folders (this study)",
           comparator="Controls",
           key_quantitative_findings="Channel order and tasks as above; this study found a tremor line (4.4-5.9 Hz) in 4 of 26 patients' meanders/spirals, about 0.3-1.4 mm at the pen's sensor, bursty (REAL DATA analysis, results/wholepen/realdata.json)",
           units_and_conditions="Uncalibrated volts; accelerometer sensitivity not published", locator="Section III (data set), Fig. 3",
           limitations="Uncalibrated accelerations; small cohort; displacement only by double integration in a band",
           relevance_to_design="Real PD pen-tip tremor while drawing is usually small; the recorded waveform is used as a real tremor input",
           transferability="medium", transferability_reason="Real pens and patients; calibration unknown",
           design_implication="Use the recorded tremor line's shape and wander, scaled to the class amplitude, as one test input", retrieved=RET,
           search_query="NewHandPD dataset page (fc.unesp.br/~papa/pub/datasets/Handpd); sibgrapi16 PDF", stream="PDT", lead_verification=""))
    A(dict(id="PDT-68", topic="MDS-UPDRS tremor amplitude anchors (items 3.15-3.17)",
           citation="MDS-UPDRS part III items 3.15-3.17 amplitude anchors as quoted by Smid A et al. Intraoperative Quantification of MDS-UPDRS Tremor Measurements Using 3D Accelerometry: A Pilot Study. J Clin Med 2022;11:2275, and a web search summary of the scale's scoring instructions",
           year="2022", doi_or_url="https://doi.org/10.3390/jcm11092275", source_type="journal", evidence_class="review",
           access_level="secondary account", task_or_setup="Scale definitions (maximal amplitude by eye)", participants_or_bench="n/a", comparator="n/a",
           key_quantitative_findings="Upper limb: 0 none; 1 <= 1 cm; 2 > 1 but < 3 cm; 3 3-10 cm; 4 > 10 cm maximal amplitude",
           units_and_conditions="cm, maximal amplitude judged by eye", locator="Scoring instructions as summarised (web search); Smid 2022 methods",
           limitations="Secondary account; the MDS-UPDRS document itself not opened; limb amplitude, not pen tip",
           relevance_to_design="Anchors the PD moderate/severe classes (1-3 cm and 3-10 cm at the limb)", transferability="low",
           transferability_reason="Limb amplitude by eye, not ink amplitude while writing", design_implication="Keep the PD classes as ASSUMPTION until EXP-W10 measures pen-tip tremor",
           retrieved=RET, search_query="WebSearch: MDS-UPDRS 3.15 postural tremor 3.16 kinetic tremor amplitude scoring", stream="PDT", lead_verification=""))
    A(dict(id="HAP-115", topic="Finger joint stiffness and damping during a tapping contact",
           citation="Jindrich DL, Balakrishnan AD, Dennerlein JT. Finger joint impedance during tapping on a computer keyswitch. J Biomech 2004;37:1589-1596",
           year="2004", doi_or_url="https://doi.org/10.1016/j.jbiomech.2004.01.001", source_type="journal", evidence_class="physical human study",
           access_level="full text", task_or_setup="Lumped impedance of the MCP and IP joints fitted to the contact phase of keyswitch taps",
           participants_or_bench="15 subjects", comparator="MCP vs IP joints; loading vs unloading",
           key_quantitative_findings="Joint stiffness while loading the keyswitch: 540 +/- 430, 710 +/- 540 and 450 +/- 340 N mm/rad (the three joints' fitted k, mean +/- SD, results table); the discussion quotes 1010-1732 N mm/rad expected for an extended posture at higher forces",
           units_and_conditions="N mm/rad; dynamic tapping, not a sustained pen grip", locator="Results table (k rows) and Discussion",
           limitations="Tapping, not holding; short contacts; posture differs from a tripod pen grasp",
           relevance_to_design="Bounds the rotational stiffness the fingers give a pen or a collar (grip.py sensitivity range)",
           transferability="low", transferability_reason="Different task and posture", design_implication="Sweep the grip's rotational stiffness 0.5-2 x in every whole-pen test",
           retrieved=RET, search_query="Finger joint impedance during tapping on a computer keyswitch (Harvard CDC PDF)", stream="HAP", lead_verification=""))
    A(dict(id="AMF-180", topic="Wacom Cintiq 12WX pixel pitch (UCI spiral data units)",
           citation="Wacom Cintiq 12WX (DTZ-1200W) specifications as summarised from retailer and review pages (drawingtablet.info, controlgraf.com, layersmagazine.com)",
           year="n.d.", doi_or_url="https://www.drawingtablet.info/tablets/wacom-cintiq-12wx-dtz1200w", source_type="website",
           evidence_class="manufacturer statement", access_level="secondary account", task_or_setup="Display specification",
           participants_or_bench="n/a", comparator="n/a",
           key_quantitative_findings="Active area 261.1 x 163.2 mm; 1280 x 800 pixels (WXGA); pixel pitch 0.204 x 0.204 mm",
           units_and_conditions="mm; pixels", locator="Specification tables (search summary)",
           limitations="Secondary pages; whether the UCI data's x/y are screen pixels is an ASSUMPTION",
           relevance_to_design="Converts the UCI spiral coordinates to mm (realdata.py)", transferability="medium",
           transferability_reason="Conversion only", design_implication="Report UCI tremor amplitudes as ASSUMPTION-scaled",
           retrieved=RET, search_query="WebSearch: Wacom Cintiq 12WX specifications active area 261 mm 1280 x 800 pixel pitch", stream="AMF", lead_verification=""))
    A(dict(id="ACT-120", topic="Passive joint-damping orthosis for ET (STIL), randomised crossover",
           citation="Mugge W, Elstgeest LEM, van Ginkel M, et al. Essential Tremor Suppression with a Novel Anti-Tremor Orthosis: A Randomized Crossover Trial. Mov Disord 2025;40:445-455",
           year="2025", doi_or_url="https://doi.org/10.1002/mds.30082", source_type="journal", evidence_class="physical human study",
           access_level="abstract only", task_or_setup="Forearm orthosis that passively damps joints; seven TETRAS tasks; baseline, sham and orthosis in randomised order, single-blind",
           participants_or_bench="24 ET patients (hospital)", comparator="No orthosis; sham device",
           key_quantitative_findings="TETRAS 19.0 +/- 3.2 (baseline), 13.7 +/- 3.9 (sham), 9.9 +/- 3.6 (orthosis); tremor power -87.4 % vs baseline and -59.5 % vs sham across tasks; 71 % (very) satisfied; 12.5 % minor adverse events",
           units_and_conditions="Video-scored TETRAS; accelerometer tremor power", locator="Abstract (Europe PMC, PMID 39838596)",
           limitations="Abstract only; single session; a large sham effect; worn on the forearm, not in a pen",
           relevance_to_design="Grounding the damping to the arm (not the pen) is what makes large tremor reduction possible; a pen alone has no such ground",
           transferability="low", transferability_reason="A forearm device, reaction on the limb itself",
           design_implication="For severe ET a limb orthosis is the benchmark a pen must be compared against; a pen-only device should not promise the same",
           retrieved=RET, search_query="Europe PMC: essential tremor anti-tremor orthosis randomized crossover", stream="ACT", lead_verification=""))
    A(dict(id="ACT-121", topic="Passive T/V-beam tuned absorber for hand tremor (single axis bench)",
           citation="Shah M, Goode D, Mohammadi D, Mohammadi H. A passive T/V-beam absorber architecture for single-axis experimental hand tremor attenuation. Med Eng Phys 2026;147",
           year="2026", doi_or_url="https://doi.org/10.1088/1873-4030/ae7112", source_type="journal", evidence_class="physical bench experiment",
           access_level="abstract only", task_or_setup="Passive beam absorbers tuned by a constrained parametric procedure; 1-DOF mannequin tremor simulator, 3.0-6.5 Hz",
           participants_or_bench="Mannequin-based tremor simulator", comparator="Uncontrolled condition",
           key_quantitative_findings="Up to 85 % reduction of steady-state peak-to-peak displacement (single axis); the double V-beam strongest",
           units_and_conditions="Peak-to-peak displacement, steady state, 3.0-6.5 Hz", locator="Abstract (Europe PMC, PMID 42167291)",
           limitations="Abstract only; single axis; mannequin; steady-state sine",
           relevance_to_design="A tuned absorber works on a resonant limb segment; the pen in the grip is not that",
           transferability="low", transferability_reason="Limb mounting and steady sines", design_implication="Do not expect a pen-tail tuned mass to repeat bench absorber numbers (study W: a tuned tail mass is worse than the same mass locked)",
           retrieved=RET, search_query="Europe PMC: passive absorber hand tremor attenuation", stream="ACT", lead_verification=""))
    A(dict(id="ACT-122", topic="Passive tuned mass dampers driven by a measured postural tremor (simulation)",
           citation="Gebai S, Cumunel G, Hammoud M, Foret G, Roze E, Hainque E. Design and Simulation of a Passive Absorber to Reduce Measured Postural Tremor Signal. J Biomech Eng 2022;144:091003",
           year="2022", doi_or_url="https://doi.org/10.1115/1.4053998", source_type="journal", evidence_class="numerical simulation",
           access_level="abstract only", task_or_setup="Upper-limb model excited by one patient's IMU postural tremor; cantilever TMDs with an adjustable screw mass; optimised positions and damping",
           participants_or_bench="One patient's recorded signal; model", comparator="Without absorbers",
           key_quantitative_findings="Three TMDs of 28.64 g total effective mass reduced the PSD of wrist angular displacement by 83.1 %",
           units_and_conditions="PSD reduction (power), simulated", locator="Abstract (Europe PMC, PMID 35237796)",
           limitations="Abstract only; simulation; postural tremor; on the limb", relevance_to_design="Quoted power reductions are not amplitude reductions (83 % power = 59 % amplitude)",
           transferability="low", transferability_reason="Limb, not pen", design_implication="Report tremor reductions as amplitude ratios and say what they mean",
           retrieved=RET, search_query="Europe PMC: passive absorber measured postural tremor", stream="ACT", lead_verification=""))
    A(dict(id="ACT-123", topic="Dual dynamic vibration absorber for PD rest tremor (model)",
           citation="Gebai S, Hammoud M, Hallal A, Khachfe H. Tremor Reduction at the Palm of a Parkinson's Patient Using Dynamic Vibration Absorber. Bioengineering (Basel) 2016;3:E18",
           year="2016", doi_or_url="https://doi.org/10.3390/bioengineering3030018", source_type="journal", evidence_class="numerical simulation",
           access_level="abstract only", task_or_setup="3-DOF arm model with dual-harmonic rest tremor; single and dual cantilever DVAs on the forearm",
           participants_or_bench="Model", comparator="Single vs dual DVA; none",
           key_quantitative_findings="Dual DVA reduced 98.3-99.5 % (shoulder), 97.0-97.3 % (elbow) and 97.4-97.5 % (wrist) of the tremor amplitude in the model",
           units_and_conditions="Amplitude, model at the tuned frequencies", locator="Abstract (Europe PMC, PMID 28952580)",
           limitations="Model only; exactly tuned harmonic excitation", relevance_to_design="Model results at exact tuning overstate what a detuned absorber does",
           transferability="low", transferability_reason="Idealised model", design_implication="Test tuned devices with wandering frequency and amplitude (study W does)",
           retrieved=RET, search_query="Europe PMC: dynamic vibration absorber Parkinson palm", stream="ACT", lead_verification=""))
    A(dict(id="ACT-124", topic="Tremor-suppression orthoses: weight, DOF and comfort",
           citation="ChiGan M, Chen M, Jing M. Designs of Upper Limb Tremor Suppression Orthoses: Efficacy and Wearer's Comfort. J Med Devices 2025;19:020801",
           year="2025", doi_or_url="https://doi.org/10.1115/1.4066968", source_type="journal", evidence_class="review",
           access_level="abstract only", task_or_setup="Review of mechanisms, DOF, weight and effectiveness", participants_or_bench="n/a", comparator="Between designs",
           key_quantitative_findings="Weight is a major factor in comfort; mechanism and number of suppressed directions drive weight; balancing the three is the key open problem (no numbers in the abstract)",
           units_and_conditions="Qualitative", locator="Abstract (Europe PMC, PMID 39845265)", limitations="Abstract only; review",
           relevance_to_design="Added mass is a cost users feel; every tail module must beat the same mass locked", transferability="medium",
           transferability_reason="General device lesson", design_implication="Report grams next to every benefit; the review's gate G5",
           retrieved=RET, search_query="Europe PMC: upper limb tremor suppression orthoses comfort", stream="ACT", lead_verification=""))
    return R


def _derived() -> List[Dict]:
    """This study's own results as ledger rows (numbers from the result files; absent files -> the row is omitted)."""
    R = []

    def load(n):
        p = os.path.join(RESULTS, n)
        return json.load(open(p)) if os.path.exists(p) else None
    calc = load("calc.json")
    summ = load("summary.json")
    if calc:
        tg = calc["tail_gate"]["summary"]
        R.append(dict(id="ACT-130", topic="Tail modules against the same mass locked (the review's gate G5), perfect knowledge",
                      citation="This ledger's calculation: wholepen/calc.py tail_gate (results/wholepen/calc.json)", year="2026",
                      doi_or_url="results/wholepen/calc.json", source_type="derived calculation", evidence_class="calculation",
                      access_level="full text", task_or_setup="Linear model (lin.py): H1 hand, grip 0.5/1/2 x, split 0.3/0.5/0.7; 5 and 6 Hz at 3 and 8 mm, 9 Hz at 3 mm; perfect knowledge of the tremor",
                      participants_or_bench="Model", comparator="Same mass locked; no module",
                      key_quantitative_findings="; ".join(f"{k}: gain vs locked mean {v['gain_vs_locked_mean']:.2f} (min {v['gain_vs_locked_min']:.2f}), passes >= 10 % in {100 * v['share_passing_gate']:.0f} % of conditions" for k, v in tg.items()),
                      units_and_conditions="1 - tip tremor active / tip tremor locked", locator="calc.json tail_gate.summary",
                      limitations="Perfect knowledge (an upper bound); linear; the closed-loop simulation decides (grips.json, test.json)",
                      relevance_to_design="Which tail modules could pass G5 at all", transferability="medium", transferability_reason="Model verified against MuJoCo (verification.json)",
                      design_implication="Only an active module can pass; a passive tuned mass is worse than the same mass locked",
                      retrieved=RET, search_query="n/a", stream="ACT", lead_verification=""))
        rows = calc["cmg_sizing"]["rows"]
        R.append(dict(id="ACT-131", topic="Gyroscope sizing with stored energy (the review's examples included)",
                      citation="This ledger's calculation: wholepen/calc.py cmg_sizing and designs.py cmg_design (results/wholepen/calc.json)", year="2026",
                      doi_or_url="results/wholepen/calc.json", source_type="derived calculation", evidence_class="calculation", access_level="full text",
                      task_or_setup="Scissored pair, +-1 rad gimbal swing, fundamental torque 2 h w 2 J1(1); torque needed per mm of tip tremor from lin.py (perfect knowledge, grip 1 x, split 0.5)",
                      participants_or_bench="Model", comparator="Between rotor designs",
                      key_quantitative_findings="; ".join(f"{r['name']}: h {r['h_Nms'] * 1e3:.2f} mN m s, stored {r['E_J_total']:.1f} J, cancels at best {r.get('tip_tremor_cancellable_5Hz_mm', float('nan')):.1f} mm at 5 Hz" for r in rows),
                      units_and_conditions="N m s; J; mm peak at the tip", locator="calc.json cmg_sizing",
                      limitations="Perfect knowledge; the gimbal motor and the writer's own pen rotation limit it further; rotor burst excluded by design, not contained",
                      relevance_to_design="A pen-sized gyroscope that could cancel severe tremor stores 5-18 J", transferability="medium", transferability_reason="Physics; parameters PROPOSED",
                      design_implication="Keep the gyroscope an optional bench experiment (G5), never the severe-tremor solution",
                      retrieved=RET, search_query="n/a", stream="ACT", lead_verification=""))
    if summ:
        head = summ.get("headline", {}).get("rows", []) + (summ.get("headline_real") or {}).get("rows", [])

        def cell(c, d, k="tip_mm"):
            r = next((x for x in head if x["class"] == c and x["design"] == d), None)
            return "n/a" if r is None or r.get(k) is None else r.get(k)
        txt = []
        for c in ("ET_moderate", "PD_moderate", "ET_severe", "PD_severe", "PD_reemergent_severe"):
            txt.append(f"{c}: no help {cell(c, 'none')} mm, Rev J nose {cell(c, 'nose')} mm, collar+nose {cell(c, 'collar_nose')} mm, "
                       f"collar+nose perfect knowledge {cell(c, 'collar_nose_oracle')} mm (words of 10: {cell(c, 'none', 'words10')} / "
                       f"{cell(c, 'nose', 'words10')} / {cell(c, 'collar_nose', 'words10')} / {cell(c, 'collar_nose_oracle', 'words10')}; "
                       f"ink laid with collar+nose {cell(c, 'collar_nose', 'coverage')})")
        inc = summ.get("collar_increment") or []
        itx = [f"{r['class']}: collar+nose vs collar locked+nose {100 * r['collar_gain_vs_locked']:.0f} %"
               + (f", with perfect knowledge collar+nose vs nose {100 * r['oracle_collar_gain']:.0f} %" if r.get("oracle_collar_gain") is not None else "")
               for r in inc if r.get("collar_gain_vs_locked") is not None]
        lcmp = summ.get("light_compare") or {}
        for r in lcmp.get("rows", []):
            if r["design"].startswith("light_"):
                for c in lcmp.get("classes", []):
                    v = r.get(c)
                    if v:
                        itx.append(f"light (24 g) inner pen {r['design']} {c}: {v['tip_mm']:.2f} mm, ink laid {100 * v['coverage']:.0f} %")
        R.append(dict(id="ACT-132", topic="Whole-pen collar (V2) with the Rev J nose in the closed loop, test writers",
                      citation="This ledger's simulation: wholepen/run_study.py stages test and limits (results/wholepen/test.json, summary.json)", year="2026",
                      doi_or_url="results/wholepen/summary.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
                      task_or_setup="sim2 (MuJoCo) + sim2j firmware at 2 kHz; H1 hand; test writers 0-1, 5 words each, seeds 200/201; measured-style page sensor (OPT-02 statistics); gated listening tremor estimate with the guarded fallback (frozen on tuning writer 100)",
                      participants_or_bench="Synthetic writers; synthetic tremor (ET 6 Hz, PD 5 Hz) and a recorded NewHandPD waveform", comparator="No help; Rev J nose alone; collar pen with the collar locked and the nose working; perfect knowledge",
                      key_quantitative_findings="; ".join(txt + itx), units_and_conditions="Peak ink tremor (mm) along the main axis, 2.5-20 Hz, while inking, mean of 2 writers; words read by the app's recogniser",
                      locator="summary.json headline, collar_increment", limitations="Two synthetic writers x one seed; the simulated inner pen is the Rev J pen (heavier than the proposed 22 g inner pen); the ball-contact model decides the 8 mm coverage; nothing measured",
                      relevance_to_design="What moving the whole pen adds to the Rev J nose, and the mechanism's limit", transferability="low",
                      transferability_reason="Simulation ranks concepts only (sim2 COU-1)", design_implication="The tremor estimate, not the travel, limits the result below about 5 mm; build the collar as a bench experiment (EXP-W11) under the 10 % gate before it enters the product",
                      retrieved=RET, search_query="n/a", stream="ACT", lead_verification=""))
        rtx = []
        for c in ("REAL_PD_moderate", "REAL_PD_severe"):
            rtx.append(f"{c}: no help {cell(c, 'none')} mm, Rev J nose {cell(c, 'nose')} mm, collar+nose {cell(c, 'collar_nose')} mm, "
                       f"perfect knowledge {cell(c, 'collar_nose_oracle')} mm (words of 10: {cell(c, 'none', 'words10')} / {cell(c, 'nose', 'words10')} / "
                       f"{cell(c, 'collar_nose', 'words10')} / {cell(c, 'collar_nose_oracle', 'words10')})")
        if any("n/a" not in t for t in rtx):
            R.append(dict(id="ACT-133", topic="Whole-pen collar and Rev J nose at study R's real PD tremor classes",
                          citation="This ledger's simulation: wholepen/run_study.py stage real (results/wholepen/real.json, summary.json)", year="2026",
                          doi_or_url="results/wholepen/real.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
                          task_or_setup="As ACT-132, with recorded PD tremor from study R's library (realdata.library, test split) at its representative moderate (0.24 mm) and severe (1.72 mm) amplitudes, frequency from the recording",
                          participants_or_bench="Synthetic writers 0-1; recorded patients' tremor (test split)", comparator="No help; perfect knowledge",
                          key_quantitative_findings="; ".join(rtx), units_and_conditions="As ACT-132",
                          locator="summary.json headline_real", limitations="Two writers x one recorded draw each; the recordings are tablet spirals (may understate free-air tremor)",
                          relevance_to_design="Whether whole-pen travel matters at the tremor sizes the recordings show", transferability="low",
                          transferability_reason="Simulation ranks concepts only (sim2 COU-1)", design_implication="At real sizes travel is not the limit; the estimate and the detector's threshold are",
                          retrieved=RET, search_query="n/a", stream="ACT", lead_verification=""))
    return R


def write_rows() -> str:
    rows = _lit() + _derived()
    path = os.path.join(RESULTS, "evidence_rows.csv")
    os.makedirs(RESULTS, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})
    return path
