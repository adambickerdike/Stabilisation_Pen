"""Proposed ledger rows (results/opt/inertial_evidence_rows.csv, exact header of docs/evidence.csv) for this study.
Reserved ids: ACT-61..70, AMF-73..89, HAP-36..40, OPT-48..49.  Part and literature rows describe what was read (URL, document id
or revision, date); the study rows carry the simulation and calculation results with their seeds.  The lead merges them."""
from __future__ import annotations

import csv
import os
from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
          "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
          "stream", "lead_verification"]
R = "2026-09-28"


def _row(**kw) -> Dict:
    r = {k: "" for k in HEADER}
    r.update(kw)
    r.setdefault("retrieved", R)
    return r


def static_rows() -> List[Dict]:
    rows = []
    rows.append(_row(id="AMF-73", topic="VCM - Moticont LVCM-013-013-01 and LVCM-016-010-01 (15.9 mm, highest Km per volume checked)",
        citation="Moticont. Linear voice coil motor drawings LVCM-013-013-01 and LVCM-016-010-01 (Rev 1); undated; PDF drawings with specification tables.",
        year="n.d.", doi_or_url="https://www.moticont.com/pdf/LVCM-013-013-01.pdf ; https://www.moticont.com/pdf/LVCM-016-010-01.pdf",
        source_type="datasheet", evidence_class="manufacturer statement", access_level="full text (drawing tables read as images)",
        task_or_setup="Manufacturer specification table, all values at 25 degC", participants_or_bench="not applicable", comparator="AMF-01, AMF-02",
        key_quantitative_findings=("LVCM-013-013-01: body 12.7 x 12.7 mm (19.8 mm at mid-stroke); peak 2.35 N; continuous 0.74 N; Kf 0.61 N/A; "
                                   "back-EMF 0.61 V/(m/s); stroke 5 mm; coil clearance 0.33 mm/side; coil 6 g; body 7 g; 1.7 ohm; 280 uH at 120 Hz; "
                                   "2.5 W max continuous. LVCM-016-010-01 (Rev 1): 15.9 x 9.5 mm (15.9 mm at mid-stroke); 5.2 N at 10 % duty; "
                                   "1.6 N continuous; Kf 1.1 N/A; 1.1 V/(m/s); stroke 3.2 mm; 0.32 mm/side; coil 5 g; body 7 g; 1.8 ohm; 0.2 mH at "
                                   "1 kHz; 4.0 W. MY CALC Km = Kf/sqrt(R): 0.47 and 0.82 N/sqrt(W)."),
        units_and_conditions="N, N/A, ohm, g, mm", locator="Specification table on each drawing",
        limitations="Axial (single-axis) housed actuators; no thermal resistance; force at stroke ends lower (curves)",
        relevance_to_design="Scale reference for the Rev H flat-coil actuators and the rear-cap reaction-mass coils",
        transferability="medium", transferability_reason="Custom planar moving-magnet coils are used instead; the catalogue units calibrate Km per volume",
        design_implication="Km 0.5-0.85 N/sqrt(W) is realistic for 12-16 mm actuator volumes; Rev H's adjoint design lands at 0.47 N/sqrt(W) with the gap that clears the other axis",
        search_query="WebSearch: smallest voice coil actuator Moticont LVCM; curl https://www.moticont.com/pdf/<part>.pdf", stream="AMF"))
    rows.append(_row(id="AMF-74", topic="Wideband haptic actuator (file 'Mark II-D' on tactilelabs.com): Actronika HFBA121238 datasheet",
        citation="Actronika SAS. Standard Actuator HFBA121238 datasheet STACDA0010 V1.0 (hosted at tactilelabs.com as MarkII_D_datasheet_TL.pdf; PDF created 2023-10-14).",
        year="2023", doi_or_url="https://tactilelabs.com/wp-content/uploads/2023/11/MarkII_D_datasheet_TL.pdf", source_type="datasheet",
        evidence_class="manufacturer statement", access_level="full text", task_or_setup="Actuator on a 100 g suspended test mass, Kistler accelerometer",
        participants_or_bench="bench (manufacturer)", comparator="AMF-75",
        key_quantitative_findings=("11.5 x 12 x 37.7 mm; total 8.7 g; moving mass 4.4 g; 4.5 ohm; 128 uH; resonance 65 Hz with a 100 g load; 8 g-pp at "
                                   "max AC and 11.4 g-pp impulse (100 g); rated 1.41 Vrms / 147.8 mArms; max DC 2 V; max AC 9 V; lag 6 ms, rise 14 ms. "
                                   "MY CALC: a spring-suspended mass driven below its suspension resonance passes (f/f_n)^2/(1-(f/f_n)^2) of the coil "
                                   "force to the housing: 0.4 % at 4 Hz, 1.5 % at 8 Hz, 3.5 % at 12 Hz (f_n 65 Hz)."),
        units_and_conditions="Datasheet conditions: 100 g load, 20 degC", locator="Section 1 tables; section 2 bandwidth plot",
        limitations="The document title and file name differ (Actronika part sold by Tactile Labs); unloaded resonance not given",
        relevance_to_design="Candidate list of the task (Haptuator class) for a reaction mass", transferability="high",
        transferability_reason="Physics of any resonant (spring-suspended) haptic actuator",
        design_implication="Wideband haptic actuators are unusable as 4-12 Hz reaction masses: the internal spring returns the force; a soft (1-5 Hz) actively centred mass is needed",
        search_query="WebSearch: Tactile Labs Haptuator Mark II-D datasheet moving mass", stream="AMF"))
    rows.append(_row(id="AMF-75", topic="Wideband haptic actuator: Alps Alpine AFT14A903A HAPTIC Reactor Hybrid specification",
        citation="Alps Alpine. Product specification AFT14A903A, Ver. 4.00 (revision MAR. 6, 2026; original MAR. 28, 2019).", year="2026",
        doi_or_url="https://tech.alpsalpine.com/cms.media/product_spec_aft14a903a_ja_en_zh_hans_eb8d1ebc58.pdf", source_type="datasheet",
        evidence_class="manufacturer statement", access_level="full text", task_or_setup="Mounted on a 0.1 kg ABS block, 3.0 V pulse drive",
        participants_or_bench="bench (manufacturer)", comparator="AMF-74",
        key_quantitative_findings="W 9 x H 10 (10.4) x D 22.6 mm; 5.5 g; 8 ohm +/-10 %; rated 3.0 V, max 3.3 V; resonance points 160 Hz and 320 Hz; 29.4 +/- 9.8 m/s^2 at 160 Hz and 22.3 +/- 9.8 m/s^2 at 320 Hz on 0.1 kg (3 pulses).",
        units_and_conditions="3.0 V, 0.1 kg ABS block", locator="Sections 3.1-3.2", limitations="Pulse specification only; no low-frequency data",
        relevance_to_design="Candidate list of the task (Alps wideband actuators)", transferability="high", transferability_reason="Resonant actuator",
        design_implication="As AMF-74: resonances at 160/320 Hz make it useless at 4-12 Hz", search_query="WebSearch: Alps Alpine Haptic Reactor AFT14 specification", stream="AMF"))
    rows.append(_row(id="AMF-76", topic="Wideband haptic actuator: Titan Haptics (Nanoport) TacHammer Carlton (secondary)",
        citation="All About Circuits news 'Titan Haptics' Dev Kit Puts Tactile Feedback Options at Your Fingertips' (search-result summary); Titan Haptics product pages. Datasheet links returned HTTP 404/410.",
        year="n.d.", doi_or_url="https://www.allaboutcircuits.com/news/titan-haptics-development-puts-tactile-feedback-options-at-your-fingertips/ ; https://titanhaptics.com/carlton/",
        source_type="website", evidence_class="manufacturer statement", access_level="secondary account", task_or_setup="-", participants_or_bench="-", comparator="AMF-74",
        key_quantitative_findings="Double-ended 14 mm x 34 mm linear magnetic ram (magnetic suspension); 5 G steady-state, 25 G impulse; 10-300 Hz response (summary). Ram mass and suspension resonance not retrieved.",
        units_and_conditions="-", locator="search summary", limitations="No datasheet read; values unverified", relevance_to_design="Candidate list of the task",
        transferability="low", transferability_reason="Values unverified", design_implication="Not used; ASSUMPTION-level only", search_query="WebSearch: Titan Haptics TacHammer Carlton datasheet", stream="AMF"))
    rows.append(_row(id="AMF-77", topic="SMA actuator wire speed limit (Dynalloy Flexinol technical data)",
        citation="Dynalloy Inc. Technical Characteristics of Flexinol Actuator Wires, F1140 Rev M.", year="2025",
        doi_or_url="https://dynalloy.com/wp-content/uploads/2025/03/TCF1140.pdf", source_type="datasheet", evidence_class="manufacturer statement",
        access_level="full text", task_or_setup="Static air, vertical wire, room temperature", participants_or_bench="-", comparator="voice coils, piezo",
        key_quantitative_findings="0.025 mm wire: 1425 ohm/m, 8.9 g pull (172 MPa), 45 mA for 1 s contraction, cooling 0.18 s (70 degC LT) / 0.15 s (90 degC HT); 0.10 mm: 143 g, 1.1 / 0.9 s. Stroke about 3-4.5 %.",
        units_and_conditions="Static air", locator="Wire size table", limitations="Cooling can be sped up with heat sinks or liquid (manufacturer text)",
        relevance_to_design="The task asks to check SMA for the grip pivot", transferability="high", transferability_reason="Physics of thermal actuation",
        design_implication="A heat-cool cycle of >= 0.15-0.2 s caps the thinnest wire at about 3-5 Hz with grams of force: SMA cannot follow 4-12 Hz tremor; usable only as a slow trim",
        search_query="WebSearch: Dynalloy Flexinol technical characteristics cycle rate", stream="AMF"))
    rows.append(_row(id="AMF-78", topic="Micro BLDC motors for a Rev H CMG or gimbal (Faulhaber 0620 K 006 B, 1509 T 006 B)",
        citation="FAULHABER. Brushless DC-Servomotors 2 Pole Technology Series 0620 ... B (EN_0620_B_FMM); Brushless DC-Flat Motors 4 Pole Series 1509 ... B (EN_1509_B_DFF).",
        year="n.d.", doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_0620_B_FMM.pdf ; https://www.faulhaber.com/fileadmin/Import/Media/EN_1509_B_DFF.pdf",
        source_type="datasheet", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Values at 22 degC and nominal voltage",
        participants_or_bench="-", comparator="AMF-50, AMF-51",
        key_quantitative_findings=("0620 K 006 B: 6 V; 8.8 ohm; eta 51 %; n0 48 600 rpm; I0 0.056 A; stall 0.732 mNm; C0 0.011 mNm; Cv 1.02e-6 mNm/rpm; "
                                   "kM 1.09 mNm/A; 28 uH; J 0.0095 g cm2; 2.5 g; up to 100 000 rpm; ball bearings; rated 0.28 mNm. 1509 T 006 B: 6 V; 22 ohm; "
                                   "n0 15 000 rpm; stall 0.953 mNm; C0 0.019 mNm; Cv 3.42e-6 mNm/rpm; kM 3.56 mNm/A; J 0.69 g cm2; 6.9 g; up to 40 000 rpm."),
        units_and_conditions="22 degC, nominal voltage", locator="Datasheet tables", limitations="Friction at speed is extrapolated with C0 + Cv n",
        relevance_to_design="CMG spin and gimbal motors for the rear-cap inertial option", transferability="high", transferability_reason="Catalogue parts",
        design_implication="A CMG pair with 16 mm WHA discs at 20 krpm needs 0.09 W per rotor (CALC); two pairs weigh about 80 g: over the 30 g add-on budget",
        search_query="WebSearch: Faulhaber 0620 B datasheet; curl faulhaber.com EN_*_DFF/FMM.pdf", stream="AMF"))
    rows.append(_row(id="AMF-79", topic="Drone outrunner (1103 class) data available for a CMG spin motor",
        citation="BETAFPV 1103 11000KV brushless motor product and retailer pages (search summary).", year="n.d.",
        doi_or_url="https://betafpv.com/products/1103-brushless-motors", source_type="manufacturer", evidence_class="manufacturer statement",
        access_level="secondary account", task_or_setup="-", participants_or_bench="-", comparator="AMF-78",
        key_quantitative_findings="13.5 x 13.5 x 16 mm; 3.25 g; 11 000 rpm/V; 2S (7.4 V); 1.5 mm shaft. No friction torque, resistance at speed, rotor inertia or bearing life data.",
        units_and_conditions="-", locator="Product page summary", limitations="Hobby data only", relevance_to_design="Task asked what data exist",
        transferability="low", transferability_reason="No loss data", design_implication="Only usable with a bench characterisation (spin-down test for friction)", search_query="WebSearch: 1103 brushless outrunner specifications", stream="AMF"))
    rows.append(_row(id="AMF-80", topic="Cell - 14500 (AA-size) Li-ion for the Rev H handle (EEMB LIR14500)",
        citation="EEMB Co., Ltd. LIR14500 Lithium Ion Battery Brief Datasheet (distributor copy jm.pl).", year="n.d.",
        doi_or_url="https://jm.pl/gfx-base/s_1/orgs/18/LIR14500-EEMB.pdf ; https://www.eemb.com/product-19", source_type="datasheet",
        evidence_class="manufacturer statement", access_level="full text", task_or_setup="Brief datasheet", participants_or_bench="-", comparator="AMF-31 (LIR10440)",
        key_quantitative_findings="Nominal 3.7 V; 750 mAh typical and minimum (0.2C); charge 4.20 V, standard 375 mA, max 750 mA; max discharge 1500 mA; cut-off 2.75 V; internal impedance < 80 mOhm; > 300 cycles to 80 %; about 20 g; drawing 14.1 x 48.5 mm; charge 0-45 degC, discharge -20 to 60 degC.",
        units_and_conditions="25 degC", locator="Sections 1-3", limitations="Brief datasheet; another EEMB version lists 800 mAh and 1600 mA (search summary)",
        relevance_to_design="Rev H cell", transferability="high", transferability_reason="Catalogue part",
        design_implication="2.2 Wh usable (80 %, ASSUMPTION) gives about 27 h of continuous correction at 0.081 W (SIM/CALC); 1.5 A covers the coil peaks", search_query="WebSearch: EEMB LIR14500 specification pdf", stream="AMF"))
    rows.append(_row(id="ACT-61", topic="GyroGlove status (2025-2026): device mass, architecture, trial record",
        citation="ClinicalTrials.gov NCT05958030 'Effectiveness and Safety of GyroGlove in Stabilising Hand Tremors in Essential Tremor' (API v2 record, last update 2025-03-14); Practical Neurology, 'An Update on Devices for Essential Tremor Treatment', Sep-Oct 2026.",
        year="2026", doi_or_url="https://clinicaltrials.gov/api/v2/studies/NCT05958030 ; https://practicalneurology.com/archives/sept-oct-2026-issue/an-update-on-devices-for-essential-tremor-treatment/70087/",
        source_type="registry; review", evidence_class="secondary review", access_level="full text (registry); web article", task_or_setup="Multicentre single-blind placebo-controlled trial (planned)",
        participants_or_bench="30 planned (ET)", comparator="placebo glove (same hardware, weight, noise)",
        key_quantitative_findings="Registry: sponsor GyroGear Ltd; status NOT_YET_RECRUITING; estimated start 2025-07, primary completion 2025-10; primary outcome TETRAS composite change to day 14; no results posted. Review: medium glove about 580 g; spinning gyroscope on the back of the hand, battery pack at the elbow; Class I device without 510(k) clearance.",
        units_and_conditions="-", locator="Registry fields; review GyroGlove section", limitations="No rotor speed, angular momentum or kinematic efficacy published (ACT-25 abstract, ACT-28 patent bench example remain the only numbers)",
        relevance_to_design="The task asked what is published about GyroGlove", transferability="low", transferability_reason="Hand-mounted, 580 g, rotation not translation",
        design_implication="A gyroscopic stabiliser at pen scale has no published basis; Rev H uses translation authority (active nose) and a reaction mass instead", search_query="WebSearch: GyroGlove NCT05958030 results; ClinicalTrials.gov API", stream="ACT"))
    rows.append(_row(id="HAP-36", topic="Weighted pen in Parkinson's disease (handwriting kinematics)",
        citation="Latimer N, Reelfs A, Halbert J, Hansen J, Miller A, Barton C, Stuhr J, Zaman A, Stegemoller EL. The effects of auditory cues and weighted pens on handwriting in individuals with Parkinson's disease. J Hand Ther. 2024;37(1):144-152.",
        year="2024", doi_or_url="https://doi.org/10.1016/j.jht.2023.08.004 ; PMID 37778882", source_type="journal", evidence_class="physical human study", access_level="abstract only",
        task_or_setup="Continuous cursive 'l' for 10 s on 1.5 cm lines, standard vs weighted pen, 4 auditory conditions; pen-tip sensors, EMG", participants_or_bench="8 older adults with PD",
        comparator="standard pen", key_quantitative_findings="The weighted pen increased the variability of the distance between letter peaks (0.187 +/- 0.010 vs 0.482 +/- 0.065, p = 0.033) and of letter time (0.176 +/- 0.010 vs 0.187 +/- 0.016, p = 0.042); 'weighted pens may not improve handwriting in novice users'.",
        units_and_conditions="Variability indices as reported", locator="Abstract (PubMed)", limitations="Pilot, n = 8, novice users, micrographia not tremor",
        relevance_to_design="Rev H is 75 g: a heavier pen is not automatically better", transferability="medium", transferability_reason="Population overlaps; task simple",
        design_implication="Keep the Rev H handle light and test writing with the device off vs a plain pen of the same mass (sham control) in EXP-H03/H04", search_query="PubMed E-utilities: weighted pens handwriting Parkinson", stream="HAP"))
    rows.append(_row(id="HAP-37", topic="Pen barrel diameter (13, 17, 21 mm) and grip kinetics",
        citation="Kuo LC, Tsai CH, Hsu CH, Lin CF, Hsu HY, Liu CW, Lin YC. Are the shapes and sizes of pen barrel the factors to influence handwriting kinetics? Appl Ergon. 2025;129:104595.",
        year="2025", doi_or_url="https://doi.org/10.1016/j.apergo.2025.104595 ; PMID 40618453", source_type="journal", evidence_class="physical human study", access_level="abstract only",
        task_or_setup="Tracing with circular and triangular pens of 13, 17 and 21 mm grip diameter; force acquisition pen", participants_or_bench="12 children, 18 adults (healthy)",
        comparator="shapes and sizes", key_quantitative_findings="Adults showed stable force control (lower coefficient of variation of force) across grip sizes; in children triangular pens gave lower force ratios at 13 and 17 mm.",
        units_and_conditions="AF, CVF, FR", locator="Abstract", limitations="Healthy participants, tracing task", relevance_to_design="Rev H handle Ø22 mm",
        transferability="medium", transferability_reason="No tremor patients", design_implication="A 20-22 mm grip is within the range adults handle without loss of force control; confirm in EXP-H03 with target users",
        search_query="WebSearch: effect of pen barrel diameter grip force; PubMed", stream="HAP"))
    rows.append(_row(id="HAP-38", topic="Pen shape and size vs drawing accuracy and preference",
        citation="Goonetilleke RS, Hoffmann ER, Luximon A. Effects of pen design on drawing and writing performance. Appl Ergon. 2009;40(2):292-301.",
        year="2009", doi_or_url="https://doi.org/10.1016/j.apergo.2008.04.015 ; PMID 18501332", source_type="journal", evidence_class="physical human study", access_level="abstract only",
        task_or_setup="Maze drawing with 9 pens; writing with 36 bare-bodied pens", participants_or_bench="27 (drawing), 20 (writing)", comparator="pen shapes/sizes",
        key_quantitative_findings="The 8 mm equivalent-diameter pen gave the best drawing accuracy (lowest speed); users preferred larger pens but their accuracy with them tended to be lower.",
        units_and_conditions="movement time, accuracy", locator="Abstract", limitations="Healthy young adults", relevance_to_design="Bigger grip trade-off",
        transferability="medium", transferability_reason="No tremor", design_implication="Rev H trades fine accuracy for grip and actuation space: measure accuracy with the device off (EXP-H03)",
        search_query="WebSearch: effects of pen design on drawing and writing performance", stream="HAP"))
    return rows


def write(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})


def _f(x, n=2):
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return "n/a"


def study_rows(out) -> List[Dict]:
    """SIM / CALC rows of this study (numbers taken from results/opt/inertial_opt.json)."""
    rows = []
    common = dict(year="2026", access_level="full text", participants_or_bench="none (simulation)", search_query="n/a (derived)",
                  lead_verification="")
    ar = out["architecture"]["ranges"]
    rows.append(_row(id="ACT-62", topic="Rev H active nose: architecture B (skid on the fixed sleeve carries the load) vs A (rigid nose carries the load) (this study)",
        citation="This ledger's simulation: opt/inertial (evaluate.py, run_study.py stage grid), model H1 extended (sim/handpen core sleeve/pivot, stage source, controller hook)",
        doi_or_url="results/opt/inertial_opt.json architecture; results/opt/fig_in_arch.png", source_type="derived simulation",
        evidence_class="numerical simulation", task_or_setup=("Model H1 Rev H handle 22 mm x 170 mm, 75 g, tripod grip on the fixed front sleeve (HAP-26 impedance, "
                                                                "split r_rot 0.5); tremor 0.3-2 mm at 4-12 Hz on lognormal handwriting; A: nose on a pivot 38 mm "
                                                                "from the tip carrying the writing force, PID Hall servo 80 Hz, bias spring; B: skid ring carries the force, "
                                                                "the refill carrier tilts +/-3 mm, servo 80 Hz; perfect-knowledge (oracle) and causal (accelerometer tracker)"),
        comparator="A vs B; Rev H without correction", key_quantitative_findings=(
            f"Ink error ratio with perfect knowledge: B {_f(ar['B_oracle'][0])}-{_f(ar['B_oracle'][1])}, A {_f(ar['A_oracle'][0])}-{_f(ar['A_oracle'][1])}; "
            f"causal (shipped tracker): B {_f(ar['B_causal_ship'][0])}-{_f(ar['B_causal_ship'][1])}, A {_f(ar['A_causal_ship'][0])}-{_f(ar['A_causal_ship'][1])}; "
            f"causal (Rev H tracker) B {_f(ar['B_causal_revh'][0])}-{_f(ar['B_causal_revh'][1])}. Coil copper loss: A {_f(ar['A_P_cu_W'][0])}-{_f(ar['A_P_cu_W'][1])} W with the bias "
            f"({_f(ar['A_P_cu_no_bias_W'][0], 1)}-{_f(ar['A_P_cu_no_bias_W'][1], 1)} W without), B {_f(ar['B_P_cu_W'][0], 4)}-{_f(ar['B_P_cu_W'][1], 4)} W. "
            f"A modulates the writing force by {_f(ar['A_N_std_N'][0])}-{_f(ar['A_N_std_N'][1])} N rms."),
        units_and_conditions="ratio of RMS ink deviation from the tremor-free reference (same pen) with / without correction; test seeds 200-203; 5 s runs",
        locator="results/opt/inertial_opt.json architecture.by_condition", limitations=(
            "Model-to-model; hand impedance and grip split unmeasured (EXP-I01); the skid-ring feel and the A nose feel are not modelled; ball-paper "
            "friction 0.15 and a constant-force refill spring are ASSUMPTIONS"),
        relevance_to_design="Decides the Rev H nose architecture", transferability="medium",
        transferability_reason="Kinematic and power conclusions are robust (pure rotation moves the tip normal to the axis; A's actuator carries the writing load)",
        design_implication="Build architecture B; keep A only as a fallback if the skid ring is rejected on feel (EXP-H03 extension)",
        stream="ACT", **common))
    B = out["rev_h_B"]
    bb = B["band_8_12Hz_1_2mm"]
    rows.append(_row(id="ACT-63", topic="Rev H-B active nose at three grip splits: causal vs perfect knowledge, false correction, power and battery (this study)",
        citation="This ledger's simulation and calculation: opt/inertial (evaluate.py, tracker.py, run_study stage grid)",
        doi_or_url="results/opt/inertial_opt.json rev_h_B, rev_h_B_table, power_battery; results/opt/fig_in_splits.png", source_type="derived simulation",
        evidence_class="numerical simulation", task_or_setup="As ACT-62, architecture B; splits r_rot 0.3/0.5/0.7; translational and wrist tremor; shipped and Rev H tracker settings",
        comparator="Rev H without correction; perfect knowledge (oracle)", key_quantitative_findings=(
            "Mean ink error ratio at 8-12 Hz, 1-2 mm: " + "; ".join(f"r_rot {rr}: causal {_f(bb[f'revh_r{rr}']['causal'])} (oracle {_f(bb[f'revh_r{rr}']['oracle'])})"
                                                                for rr in (0.3, 0.5, 0.7)) +
            f". No causal correction at 4-6 Hz (ratio ~1.0: the tracker locks onto the second harmonic, OPT-49). False correction on tremor-free "
            f"writing: Rev H tracker {_f(B['distortion']['revh']['lognormal_um'], 1)} um (lognormal) / {_f(B['distortion']['revh']['glyph_um'], 1)} um (glyph), "
            f"shipped {_f(B['distortion']['ship']['lognormal_um'], 1)} / {_f(B['distortion']['ship']['glyph_um'], 1)} um. Power {_f(out['power_battery']['P_total_W_typical'], 3)} W "
            f"typical -> {_f(out['power_battery']['life_h'], 0)} h on the {out['power_battery']['cell']}."),
        units_and_conditions="ratios of RMS ink deviation; um RMS detrended distortion; W; h continuous writing",
        locator="results/opt/inertial_opt.json", limitations="As ACT-62; base electronics power 0.065 W ASSUMPTION; tracker sees H1's true rotation through fusion's sensor models",
        relevance_to_design="Headline performance of the Rev H pen", transferability="medium", transferability_reason="Simulated tremor and grip",
        design_implication="Expect 15-48 % less tremor in the ink at 8-12 Hz and 1-2 mm (25-35 % on average), little at 0.3 mm and none at 4-6 Hz; the estimator, not the mechanism, is the limit",
        stream="ACT", **common))
    dec = out["choice"]["inertial_module"]
    g = dec["gain_band_8_12Hz_1_2mm"]; gw = dec["passive_weight_gain"]; gc = dec["gain_with_grip_calibration"]
    scr = out["inertial_screen"]
    rows.append(_row(id="ACT-64", topic="Rear-cap inertial module (tungsten reaction mass) on top of the Rev H active nose; passive weighted-handle comparator; CMG screen (this study)",
        citation="This ledger's simulation: opt/inertial (addon.py, addon_eval.py, run_study stage addon)",
        doi_or_url="results/opt/inertial_opt.json inertial_module, inertial_screen; results/opt/fig_in_addon.png", source_type="derived simulation",
        evidence_class="numerical simulation", task_or_setup=(f"{dec['module']}; 5 Hz centring; +{_f(dec['added_mass_g'], 1)} g total; tracker-driven phasor feed-forward "
                                                                "(model inverse at the nominal split, or after a grip calibration) and adaptive narrow-band feedback (AFC); "
                                                                "nose re-estimated on the closed-loop motion; passive comparator = same mass fixed in the cap"),
        comparator="Rev H nose alone; passive weight; RM with perfect knowledge (iterative learning)", key_quantitative_findings=(
            "Further reduction of the ink error by the module in the 8-12 Hz, 1-2 mm band (mean over seeds; min seed): " +
            "; ".join(f"r_rot {rr}: {_f(100 * g[rr]['mean'], 0)} % ({_f(100 * g[rr]['seed_min'], 0)} %), after grip calibration {_f(100 * gc[rr]['mean'], 0)} %"
                      for rr in ("0.3", "0.5", "0.7")) +
            ". Passive weight: " + "; ".join(f"r_rot {rr} {_f(100 * gw[rr]['mean'], 0)} % with {_f(100 * gw[rr]['frac_conditions_worse'], 0)} % of conditions worse"
                                            for rr in ("0.3", "0.5", "0.7")) +
            f". Module power <= {_f(dec['power_W']['module_total_max_W'], 3)} W. CMG screen: {scr['cmg']['label']} needs {_f(scr['cmg']['added_g'], 0)} g and "
            f"{_f(scr['cmg']['power']['P_total_W'], 2)} W (CALC) - over the 30 g budget."),
        units_and_conditions="relative change of the RMS ink deviation; test seeds 200-203", locator="results/opt/inertial_opt.json inertial_module.by_split",
        limitations="Actuator constant Km 0.9 N/sqrt(W) and centring ASSUMPTIONS; end-stop impacts at >= 1 mm, >= 8 Hz; the 'measurable' criterion was set after the grid",
        relevance_to_design="Whether the rear-cap module earns its 28 g", transferability="medium", transferability_reason="Model-to-model; grip unmeasured",
        design_implication=(("Offer the module as an option for large (>= 1 mm) tremor" if dec["include"] else
                             "Do not fit the module in the standard Rev H (the post-hoc rule of >= 10 % on every seed at r_rot 0.5 and 0.7 is not met, and it takes the pen over 100 g); re-test on the bench (EXP-I06) if EXP-I01 finds r_rot >= 0.5")
                            + "; do not add passive weight (it amplifies 10-12 Hz at r_rot 0.5-0.7)"),
        stream="ACT", **common))
    adj = out.get("adjoint_nose") or {}
    ch = [r for r in adj.get("front", []) if r.get("mu_mass") == adj.get("chosen_mu")]
    rows.append(_row(id="ACT-65", topic="Rev H nose actuator sized by adjoint (autograd) optimisation of a magnet-coil model (this study)",
        citation="This ledger's calculation: opt/inertial/adjoint.py (torch autograd; gradients checked by central differences)",
        doi_or_url="results/opt/inertial_opt.json adjoint_nose; results/opt/fig_in_adjoint.png", source_type="derived calculation",
        evidence_class="calculation", task_or_setup="Pivot position, arm length, magnet width/length/thickness, coil thickness, travel; copper loss for the design tip force + mass weight; penalties for stroke, peak force, travel, bore",
        comparator="front over the mass weight 0.5-20", key_quantitative_findings=(
            f"Chosen (mass weight {adj.get('chosen_mu')}): Km {_f(ch[0]['out']['Km'], 2)} N/sqrt(W) at the magnets, {_f(ch[0]['out']['Km_tip'], 2)} at the tip, "
            f"copper {_f(1e3 * ch[0]['out']['P'], 1)} mW for the design force, actuator mass {_f(1e3 * ch[0]['out']['mass'], 1)} g" if ch else "see file"),
        units_and_conditions="CALC; NdFeB N45 from the AMF-28 grade table (Br 1.33 T), copper (AMF-29); leakage, fill and end-turn factors ASSUMPTION", locator="adjoint_nose.front",
        limitations="Lumped magnetic model (no FEM); thermal limits assumed", relevance_to_design="Actuator dimensions in layout.json",
        transferability="low", transferability_reason="Model-level sizing; verify by FEM and a coil bench test", design_implication="Build the flat coils and magnets to the chosen sizes; measure Km first (EXP-I05, proposed)",
        stream="ACT", **common))
    sw = out.get("sweep") or {"rows": []}
    s80 = {r["travel_mm"]: r for r in sw["rows"] if r["servo_hz"] == 80.0}
    rows.append(_row(id="ACT-66", topic="Rev H nose travel and servo bandwidth sensitivity (this study)",
        citation="This ledger's simulation: opt/inertial/run_study.py stage sweep", doi_or_url="results/opt/inertial_opt.json sweep; results/opt/fig_in_sweep.png",
        source_type="derived simulation", evidence_class="numerical simulation", task_or_setup="Travel 1-4 mm x servo 30/80/150 Hz, 6-12 Hz x 1-2 mm, training seeds 300-303, r_rot 0.5",
        comparator="design point 3 mm / 80 Hz", key_quantitative_findings=(
            "Perfect knowledge (mean): " + ", ".join(f"{k:g} mm {_f(v['oracle'])}" for k, v in sorted(s80.items())) +
            " at 80 Hz; causal: " + ", ".join(f"{k:g} mm {_f(v['causal'])}" for k, v in sorted(s80.items()))),
        units_and_conditions="ink error ratio", locator="sweep.rows", limitations="Training seeds; servo modelled as a 2nd-order follower",
        relevance_to_design="Travel and servo requirements", transferability="medium", transferability_reason="Model-to-model",
        design_implication="+/-2-3 mm usable travel and >= 80 Hz servo; beyond that the tracker limits the causal result", stream="ACT", **common))
    nn = out.get("neural")
    if nn:
        t5 = nn["test_h1"].get("0.5", {})
        rows.append(_row(id="ACT-67", topic="Neural reaction-mass controller trained by backpropagation through time (this study)",
            citation="This ledger's simulation: opt/inertial/neural.py (torch; behaviour cloning of the phasor feed-forward, then BPTT on the linear model; run in H1 via the MLP hook)",
            doi_or_url="results/opt/inertial_opt.json neural; results/opt/fig_in_neural.png", source_type="derived simulation", evidence_class="numerical simulation",
            task_or_setup="MLP 10-12-2 (tanh) on the tracker estimate, two low-passed copies, frequency, authority and the mass position; training seeds 300-311, validation 316-319, test 200-203",
            comparator="phasor feed-forward (model inverse)", key_quantitative_findings=(
                f"Test, r_rot 0.5: RM alone ratio nn {_f(t5.get('nn'))} vs feed-forward {_f(t5.get('ff'))}; with the nose nn {_f(t5.get('nose+nn'))} vs {_f(t5.get('nose+ff'))}. "
                f"Cost {nn['cost']['macs_per_tick']} MAC per 0.5 ms tick ({_f(nn['cost']['mcu_load_pct_nrf54l15'], 2)} % of the nRF54L15)."),
            units_and_conditions="ink error ratio vs Rev H without correction", locator="neural.test_h1", limitations="Small network; trained on a linear model; the information limit is the tracker's estimate",
            relevance_to_design="Whether learning beats the model-based law", transferability="low", transferability_reason="Model-to-model",
            design_implication="Ship the model-based feed-forward; keep the learned policy as a research option once real data exist", stream="ACT", **common))
    tr = out.get("tracker_setting") or {}
    if tr:
        rows.append(_row(id="OPT-48", topic="Rev H tracker setting chosen by multi-objective Bayesian optimisation (ParEGO) on the Rev H pen (this study)",
            citation="This ledger's simulation: opt/inertial/tracker_tune.py (ParEGO from opt/touchdown/bo.py; fusion AKF shipped set as the start)",
            doi_or_url="results/opt/inertial_tracker_revh.json; results/opt/fig_in_tracker.png", source_type="derived simulation", evidence_class="numerical simulation",
            task_or_setup="10 AKF parameters (gain, frequency gate, amplitude gate, cap, slow-motion speed, harmonic weight, output filter, max frequency); 51 evaluations; training seeds 300-301, glyph 330-331",
            comparator="shipped AKF set", key_quantitative_findings=(
                f"Training band ratio {_f(tr['training']['band_ratio'])} vs shipped {_f(tr['ship_on_training']['band_ratio'])}; false correction {_f(tr['training']['false_corr_um'], 1)} um vs "
                f"{_f(tr['ship_on_training']['false_corr_um'], 1)} um; distortion lognormal {_f(tr['training']['dist_lognormal_um'], 1)} um, glyph {_f(tr['training']['dist_glyph_um'], 1)} um "
                f"(rule <= 15 / 30 um). Parameters at their bounds: {', '.join(tr.get('at_bounds', []))}."),
            units_and_conditions="ratio of RMS 3-15 Hz ink error; um", locator="inertial_tracker_revh.json", limitations="Two training seeds per writer; three parameters at bounds",
            relevance_to_design="Firmware tracker setting for Rev H", transferability="medium", transferability_reason="Simulated sensors",
            design_implication="Use the Rev H setting with the per-user band (OPT-49); re-tune on recorded data", stream="OPT", **common))
    cb = out.get("calibrated_band")
    if cb:
        t5 = [r for r in cb["test"] if r["r_rot"] == 0.5]
        lo = {(r["amp_mm"], r["f0"]): r["causal"] for r in t5}
        rows.append(_row(id="OPT-49", topic="Tracker frequency lock at 4-6 Hz and a per-user calibrated tremor band (this study)",
            citation="This ledger's simulation: opt/inertial/run_study.py stage calib (fusion AKF with the frequency search limited to 0.75-1.3 x f_cal)",
            doi_or_url="results/opt/inertial_opt.json calibrated_band; results/opt/fig_in_calib.png", source_type="derived simulation", evidence_class="numerical simulation",
            task_or_setup="Rev H-B nose, Rev H tracker; band set from a calibration 10 % above the true tremor frequency; development on training seeds 300-303, test seeds 200-203",
            comparator="open-band Rev H tracker", key_quantitative_findings=(
                "Open band: mean frequency estimate 8.0 Hz for 4 Hz tremor and 12.0 Hz for 6 Hz at 2 mm (second-harmonic lock), no correction. Calibrated band, r_rot 0.5: " +
                ", ".join(f"{a:g} mm {f:g} Hz {_f(v)}" for (a, f), v in sorted(lo.items()) if f <= 6.0) +
                ". False correction with the band set for " + ", ".join(f"{k} Hz: {_f(v['lognormal'], 1)} / {_f(v['glyph'], 1)} um" for k, v in cb["distortion"].items())),
            units_and_conditions="ink error ratio; um lognormal / glyph", locator="calibrated_band", limitations="Calibration accuracy assumed (+10 %); tremor frequency drift within a session not modelled",
            relevance_to_design="Parkinson's rest and action tremor lie at 4-7 Hz", transferability="medium", transferability_reason="Simulated tremor with a fixed frequency",
            design_implication="Offer the calibrated band only for tremor at about 5.5-7 Hz (below that it moves tremor-free writing by 35 um); test on recorded tremor (EXP-I07, proposed, with EXP-E01)", stream="OPT", **common))
    try:
        from . import board_magnet as BM
        from . import geometry as GE
        from . import revh as RH
        bm = BM.summary(GE.layout(RH.RevH()))
        cl = bm["paper_clearance_mm_by_tilt"]; ct = bm["crosstalk"]
        rows.append(_row(id="ACT-69", topic="Guidance-board pen magnet on the Rev H sleeve: fit, paper clearance and magnetic crosstalk (this study)",
            citation="This ledger's calculation: opt/inertial/board_magnet.py (magpylib 5), placement from results/board/board_params.json",
            doi_or_url="results/revH/layout.json board_magnet_checks", source_type="derived calculation", evidence_class="calculation",
            task_or_setup="K&J D42-N52 (AMF-91) in a keel with 0.5 mm walls under the fixed front sleeve, 13.5 mm along the axis, 10.2 mm off it toward the paper; paper plane through the skid-ring heel; board head D88-N52 (AMF-90) 3.7 mm below the surface, +/-24 mm around the pen, raised or retracted 12 mm",
            comparator="alternative placements (rearward; radial disc)", key_quantitative_findings=(
                "Keel clearance above the paper: " + ", ".join(f"{k} deg {v:+.2f} mm" for k, v in cl.items()) +
                f"; usable tilt >= {bm['min_tilt_deg_for_0.3mm_clearance']:.0f} deg. Wall to the carrier swing {bm['wall_to_carrier_swing_mm']:.1f} mm. "
                f"Pen-magnet field {ct['pen_magnet_field_uT']['hall3d']:.0f} uT at the nose Hall sensor (static), {ct['pen_magnet_field_uT']['imu']:.0f} uT at the IMU; "
                f"board head {ct['head_field_uT']['hall3d']['min']:.0f}-{ct['head_field_uT']['hall3d']['max']:.0f} uT at the Hall sensor, changing by up to "
                f"{ct['head_field_uT']['hall3d']['max_change_any_component']:.0f} uT -> up to {ct['hall_signal']['apparent_tip_error_um_unshielded']:.0f} um apparent tip error "
                f"(unshielded). Added mass {bm['added_mass_g']:.2f} g."),
            units_and_conditions="mm, uT, um; CALC", locator="layout.json board_magnet_checks",
            limitations="No soft-iron shielding modelled; keel wall and placement ASSUMPTION; board forces on the pen not simulated in H1",
            relevance_to_design="Integration of the optional guidance board with the Rev H pen", transferability="medium",
            transferability_reason="Magnetostatics of catalogue magnets; geometry proposed",
            design_implication="Move the magnet (rearward or radial) or restrict board-mode tilt to >= 52 deg; calibrate the static offset; check the head-field error on the nose Hall sensor (EXP-I05/EXP-G03)",
            stream="ACT", **common))
    except Exception:
        pass
    tiers = out.get("tiers_T0_T2")
    if tiers:
        rows.append(_row(id="ACT-68", topic="Slim tiers T0-T2 with a cap reaction mass: linear bounds (this study)",
            citation="This ledger's calculation: opt/inertial/run_study.py stage tiers (opt/inertial/linear_ext.py)", doi_or_url="results/opt/inertial_opt.json tiers_T0_T2",
            source_type="derived calculation", evidence_class="calculation", task_or_setup="Best cap slug per tier (T0 5.2 g, T1 10.2 g, T2 19.5 g), 0.3 mm, 4-12 Hz, three splits, 0.5 N",
            comparator="no device", key_quantitative_findings=("T0 ratio 0.48-0.95, T1 0.00-0.87, T2c 0.00-0.63 over 4-12 Hz and splits (optimistic single-frequency bound)"),
            units_and_conditions="ratio of linear-model tip amplitude", locator="tiers_T0_T2", limitations="Frictionless linear bound; the time-domain oracle realised a quarter to a half of these gains (study I1)",
            relevance_to_design="Secondary slim variants", transferability="low", transferability_reason="Bounds only",
            design_implication="Slim tiers need >= 10 g of moving mass to matter; Rev H's bigger grip is the primary product", stream="ACT", **common))
    return rows
