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
