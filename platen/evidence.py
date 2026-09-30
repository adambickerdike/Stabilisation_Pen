"""Proposed ledger rows of study P (results/platen/evidence_rows.csv): the 23-column header of docs/evidence.csv,
CRLF line endings, ids ACT-170..189 (derived results), AMF-280..299 (components) and CON-110..119 (constraints).
Numbers in the derived rows are filled from the study's own results; nothing is copied by hand."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
          "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions",
          "locator", "limitations", "relevance_to_design", "transferability", "transferability_reason",
          "design_implication", "retrieved", "search_query", "stream", "lead_verification"]
RETRIEVED = "2026-09-30"
SIM_BENCH = ("Simulated (real recorded inputs: UNIPEN hpb2 writers, UCI PD tip tremor, Zenodo ET hand tremor; study R's "
             "tuning split, study E's selection set)")
SIM_LIM = "Simulation with real inputs and an AI reader, not a measurement of people or of a device"


def _f(b, nd=2, scale=1.0):
    if not b or b.get("mean") is None:
        return "n/a"
    return f"{b['mean'] * scale:.{nd}f} [{b['lo'] * scale:.{nd}f}-{b['hi'] * scale:.{nd}f}]"


def derived_rows(res: Dict) -> List[Dict]:
    tr = (res.get("tremor") or {}).get("by_class", {}).get("all/severe", {})
    tm = (res.get("tremor") or {}).get("by_class", {}).get("all/moderate", {})
    cl = (res.get("tremor") or {}).get("clean", {})
    acc = (res.get("accepted") or {}).get("summary", {})
    ss = (res.get("sensitivity") or {}).get("rows", {})
    g = lambda k, m: (tr.get(k) or {}).get(m)             # noqa: E731
    rows = []

    def row(**kw):
        base = {k: "" for k in HEADER}
        base.update({"year": "2026", "source_type": "derived simulation", "evidence_class": "numerical simulation",
                     "access_level": "full text", "participants_or_bench": SIM_BENCH, "transferability": "low",
                     "transferability_reason": SIM_LIM, "retrieved": RETRIEVED, "search_query": "n/a (derived)",
                     "stream": "ACT", "locator": "docs/platen_concept.md"})
        base.update(kw)
        rows.append(base)

    row(id="ACT-170", topic="Moving-paper platen with perfect knowledge of severe real tremor (study P simulation, HW1 "
        "+ platen stage)", citation="This study's simulation (platen/tremor.py): model HW1's hand and ordinary pen, the "
        "page moved by the proposed fine stage (0.59 kg, +-5 mm, 40 Hz, 20 N cap)",
        doi_or_url="results/platen/platen.json (tremor)",
        task_or_setup="The page follows the true tip tremor of the fixed-page run, previewed by the stage's group delay "
                      "(6.07 ms); severe class (1.72 mm at the tip), PD and ET; words read by study R's literal reader",
        comparator="Ordinary pen on a fixed page; the Rev J nose at +-6 / +-1.5 / +-1.0 mm with perfect knowledge "
                   "(study F, same cases)",
        key_quantitative_findings=(f"Tip tremor left: platen {_f(g('P_oracle', 'tip_tremor_mm'))} mm, words read "
                                   f"{_f(g('P_oracle', 'words_read'), 1)} of 10; ordinary pen {_f(g('none', 'tip_tremor_mm'))} "
                                   f"mm, {_f(g('none', 'words_read'), 1)}; nib +-1.5 mm {_f(g('F15_oracle', 'tip_tremor_mm'))} "
                                   f"mm, {_f(g('F15_oracle', 'words_read'), 1)}; nib +-1.0 mm {_f(g('F10_oracle', 'tip_tremor_mm'))} mm, "
                                   f"{_f(g('F10_oracle', 'words_read'), 1)}; scaled to F's +2 residual the platen keeps "
                                   f"{_f(g('P_a_r2', 'tip_tremor_mm'))} mm (nib +-1.5 mm: {_f(g('F15_a_r2', 'tip_tremor_mm'))})"),
        units_and_conditions="mm (sqrt(2) x RMS of the major axis of ink - intended in contact, f0 +- 2 Hz); words of "
                             "10; means over 5 tuning writers with 95 % writer-bootstrap intervals; SIMULATION",
        limitations="Tuning split only (the test split is spent); perfect knowledge is a limit, not a design; the pen "
                    "follows HW1's writer convention (the writer cancels the paper drag)",
        relevance_to_design="Whether reach limits severe-tremor legibility once the correction is moved off the pen",
        design_implication="A desk platen removes the reach limit of the handheld nib; the estimator remains the limit")
    row(id="ACT-171", topic="Study E's causal estimators driving the platen: separation, not reach, limits the result "
        "(study P simulation)", citation="This study's simulation (platen/tremor.py) with study E's frozen designs "
        "(results/realtrack/frozen.json) on the ordinary pen's own sensor streams (IMU + ideal position stream)",
        doi_or_url="results/platen/platen.json (tremor)",
        task_or_setup="E's frozen design (ai2's TCN + soft size gate) and E's real-data TCN + gate, extrapolated to the "
                      "platen's 6.07 ms command lag; the same designs on the Rev J nose at +-6 / +-1.5 / +-1.0 mm",
        comparator="Perfect knowledge on the same platen; the same estimators on the nib",
        key_quantitative_findings=(f"Severe, tip tremor left / words read: platen + E's design {_f(g('P_E_chosen', 'tip_tremor_mm'))} "
                                   f"mm / {_f(g('P_E_chosen', 'words_read'), 1)}; platen + real-data TCN "
                                   f"{_f(g('P_E_net', 'tip_tremor_mm'))} mm / {_f(g('P_E_net', 'words_read'), 1)}; nib +-1.5 mm + "
                                   f"E's design {_f(g('N15_E_chosen', 'tip_tremor_mm'))} mm / {_f(g('N15_E_chosen', 'words_read'), 1)}; "
                                   f"nib +-1.0 mm + E's design {_f(g('N10_E_chosen', 'tip_tremor_mm'))} mm / "
                                   f"{_f(g('N10_E_chosen', 'words_read'), 1)}. Clean writing moved on the platen: E's design "
                                   f"{_f((cl.get('P_E_chosen') or {}).get('mean_over_writers'), 1)} um, real-data TCN "
                                   f"{_f((cl.get('P_E_net') or {}).get('mean_over_writers'), 1)} um"),
        units_and_conditions="mm, words of 10, um; tuning split; SIMULATION",
        limitations="E's estimators were built for the Rev J pen's streams; tuning split only",
        relevance_to_design="What the platen buys with today's estimators",
        design_implication="Do not expect legibility gains from a platen until an estimator separates tremor from writing")
    row(id="ACT-172", topic="Sensing limit of a camera-tracked platen (study P simulation)",
        citation="This study's simulation (platen/sensitivity.py): perfect separation (the clean path known), the tip "
                 "sensed by a camera-class sensor and a tuned linear predictor",
        doi_or_url="results/platen/platen.json (sensitivity)",
        task_or_setup="Camera latency 2-25 ms, noise 0-60 um RMS, rate 125-500 Hz; the multi-horizon AR predictor "
                      "refitted on the tuning split for every setting",
        comparator="Perfect knowledge (no sensing)",
        key_quantitative_findings="; ".join(f"{k.split('|')[0]} {_f(v.get('tip_tremor_mm'))} mm" for k, v in ss.items()
                                            if k.endswith("|camera") and (k.startswith("latency") or k.startswith("noise")
                                                                          or k.startswith("baseline"))),
        units_and_conditions="mm tip tremor left, severe class, tuning split; SIMULATION",
        limitations="White camera noise; a pooled linear predictor (an adaptive one could do better)",
        relevance_to_design="Choice of the platen's absolute tip sensor (REQ-PLT-004)",
        design_implication="Keep the camera latency and noise low enough for the near-normal target, or accept the +2 target")
    a = lambda t, c, h, m: (acc.get(f"{t}|{c}|{h}") or {}).get(m)          # noqa: E731
    parts = []
    for cfg in ("proposed", "firm_ideal", "relaxed_naive", "cradle"):
        for hk in (("cradle",) if cfg == "cradle" else ("still", "mod_PD", "sev_PD", "sev_ET")):
            v = a("se", cfg, hk, "engineering_complete")
            if v is not None:
                parts.append(f"{cfg}/{hk} {v}/{a('se', cfg, hk, 'n')} (RMS {a('se', cfg, hk, 'median_rms_mm'):.3f} mm)")
    row(id="ACT-173", topic="Accepted words written by moving the page under a held pen (study P simulation; the "
        "grounded five-bar's references)", citation="This study's simulation (platen/accepted.py) of the independent "
        "pass's accepted references (20 'se' suffixes; 20 'library' rewrites rebuilt with ai3's functions)",
        doi_or_url="results/platen/platen.json (accepted)",
        task_or_setup="HW1 hand holding the pen still (drift, real tremor of tuning patients), the two-layer stage, "
                      "camera 250 Hz / 6 ms / 15 um, 40 ms Z-drop lift, the five-bar's supervisor and criterion",
        comparator="The grounded five-bar (results/improvement/mechanics/grounded_batch.json): 20/20 unloaded, 0/20 "
                   "with 200 or 500 N/m grips",
        key_quantitative_findings="'se' words complete: " + "; ".join(parts),
        units_and_conditions="words of 20 meeting coverage >= 98 %, RMS <= 0.10 mm, air ink <= 0.02 mm, no refusal; SIMULATION",
        limitations="UJI glyphs already used in development; hand compliance, grip and friction are assumptions; "
                    "the relaxed hand is HW1's",
        relevance_to_design="Accepted-word completion (dyslexia) and signatures by template",
        design_implication="The pen must be held stiffly against the page's drag (firm grip on the palm rest, low normal "
                           "force) or docked; tremor then limits through the camera")
    row(id="ACT-174", topic="The page drags the pen: stick-slip coupling of a moving page and a compliant hand "
        "(study P simulation)", citation="This study's simulation (platen/accepted.py, relaxed-hand and hand-stiffness "
        "variants)", doi_or_url="results/platen/platen.json (accepted, accepted sensitivity)",
        task_or_setup="HW1's relaxed hand (7.6 mm/N at the tip) with no drag compensation; a firm grip (1.37 mm/N); "
                      "normal force 0.3-1.0 N; tip-following and ink-loop controllers",
        comparator="The same with the hand cancelling the drag (HW1's writer convention)",
        key_quantitative_findings="; ".join(f"{k}: {v['engineering_complete']}/{v['n']}" for k, v in
                                            ((res.get('accepted') or {}).get('sensitivity') or {}).items()),
        units_and_conditions="words of 20 complete ('se'); SIMULATION",
        limitations="LuGre friction with HW1's constants; linear hand model; no reflexes",
        relevance_to_design="Pen holding, Z force control and the controller of the accepted mode",
        design_implication="Specify the pen-holding stiffness and the normal force (REQ-PLT-007); offer a pen cradle")
    row(id="ACT-175", topic="Platen sensitivity: stage bandwidth and travel, paper slip under the hand, pen tilt, "
        "friction convention, pen mass (study P simulation)", citation="This study's simulation (platen/sensitivity.py)",
        doi_or_url="results/platen/platen.json (sensitivity)",
        task_or_setup="One change at a time from the baseline, severe class, tuning split; perfect knowledge and camera",
        comparator="The baseline platen",
        key_quantitative_findings="; ".join(f"{k} {_f(v.get('tip_tremor_mm'))} mm" for k, v in ss.items()
                                            if not (k.startswith("latency") or k.startswith("noise"))),
        units_and_conditions="mm tip tremor left; SIMULATION", limitations=SIM_LIM,
        relevance_to_design="Stage, hold-down, palm rest and sensor requirements",
        design_implication="See REQ-PLT-001..010")
    return rows


def source_rows() -> List[Dict]:
    """Components and constraints read here (MANUFACTURER / LITERATURE)."""
    base = {"year": "n.d.", "access_level": "product page", "participants_or_bench": "not applicable (manufacturer "
            "data; test method not published)", "transferability": "high", "retrieved": RETRIEVED, "lead_verification": ""}
    R = []

    def row(**kw):
        d = {k: "" for k in HEADER}
        d.update(base)
        d.update(kw)
        R.append(d)
    row(id="AMF-280", topic="Fine-stage voice coil: Moticont LVCM-032-025-02 drawing data (electrical and mass)",
        citation="Moticont. LVCM-032-025-02 linear voice coil motor, drawing/data sheet (rev 1).",
        doi_or_url="https://www.moticont.com/pdf/lvcm-032-025-02.pdf", source_type="datasheet",
        evidence_class="manufacturer statement", access_level="full text", task_or_setup="Data sheet (values at 25 C)",
        comparator="AMF-232 (the family's force and stroke)",
        key_quantitative_findings="Stroke 12.7 mm; continuous force 9.3 N; intermittent 29.3 N at 10 % duty; force "
                                  "constant 3.9 N/A; back-EMF 3.9 V/(m/s); coil resistance 2.5 ohm; inductance 1.3 mH at "
                                  "120 Hz; coil assembly 28 g; body 127 g; max continuous power 14.0 W; housing 31.8 mm "
                                  "dia x 25.4 mm (38.1 mm with the coil at mid-stroke); coil clearance 0.38 mm per side; "
                                  "continuous force falls to about 6 N at the stroke ends (curve)",
        units_and_conditions="N, N/A, ohm, mH, g, W at 25 C", locator="Drawing table and continuous-force curve",
        limitations="No thermal resistance or price; force curve read from the plot",
        relevance_to_design="Fine XY stage of the platen (tremor cancellation, +-5 mm)",
        transferability_reason="Manufacturer data sheet of the proposed part",
        design_implication="Km = 3.9 / sqrt(2.5) = 2.47 N/sqrt(W) (CALC): 1-2 N RMS tremor duty costs 0.2-0.7 W per axis",
        search_query="direct URL (product page link)", stream="AMF")
    row(id="AMF-281", topic="Global-shutter camera modules for tip tracking: OV9281 and IMX296 frame rates",
        citation="InnoMaker. Raspberry Pi global shutter cameras (OV9281, OV7251, IMX296), product page.",
        doi_or_url="https://www.inno-maker.com/gs-camera/", source_type="manufacturer web page",
        evidence_class="manufacturer statement", task_or_setup="Product page",
        comparator="AMF-282 (motion-capture camera latency)",
        key_quantitative_findings="OV9281 (mono, 1 MP): 1280 x 800 at 120 fps (Raspberry Pi OS), 144 fps and 640 x 400 at "
                                  "253 fps with the maker's driver; IMX296 (1.58 MP): 1456 x 1088 at 60 fps; OV7251 "
                                  "640 x 480 up to 153 fps. No latency or price stated",
        units_and_conditions="frames per second at the stated resolutions", locator="Sensor sections",
        limitations="No latency, noise or price", relevance_to_design="Platen tip sensor (250 fps region of interest)",
        transferability_reason="Manufacturer data", design_implication="A 250 fps region of interest is available off the shelf",
        search_query="WebSearch: Raspberry Pi Global Shutter Camera IMX296 frame rate; InnoMaker page", stream="AMF")
    row(id="AMF-282", topic="Motion-capture camera latency: OptiTrack Prime 13",
        citation="OptiTrack (NaturalPoint). Prime 13 camera, specifications.",
        doi_or_url="https://optitrack.com/cameras/prime-13/specs.html", source_type="manufacturer web page",
        evidence_class="manufacturer statement", task_or_setup="Product specifications (read in a search listing)",
        comparator="AMF-281", key_quantitative_findings="240 fps capture; 4.2 ms latency; 1.3 MP; 3D precision to 0.2 mm "
                                                          "at close range (0.5 mm at long range)",
        units_and_conditions="fps, ms, mm", locator="Specifications",
        limitations="Search listing, not the page itself; a system camera, not a low-cost module",
        relevance_to_design="The latency a well-engineered marker camera reaches (lower bound for the platen's 6 ms)",
        transferability_reason="Manufacturer data of a different class of camera", transferability="medium",
        design_implication="4-8 ms is a realistic camera latency band", search_query="WebSearch: OptiTrack Prime 13 latency",
        stream="AMF", lead_verification="search summary only")
    row(id="AMF-287", topic="Bluetooth LE connection interval: 7.5 ms minimum, 375 us with Core 6.2's Shorter "
        "Connection Intervals (radio latency of a wireless pen sensor)",
        citation="Bluetooth SIG. Bluetooth Core 6.2 feature overview; blog 'How Bluetooth Shorter Connection Intervals "
                 "will impact the next generation of wireless innovations'.",
        doi_or_url="https://www.bluetooth.com/bluetooth-core-6-2-feature-overview/ ; "
                   "https://www.bluetooth.com/blog/how-bluetooth-shorter-connection-intervals-will-impact-the-next-"
                   "generation-of-wireless-innovations/",
        source_type="standards body web page", evidence_class="manufacturer statement",
        task_or_setup="Feature overview of the Bluetooth Core Specification 6.2",
        comparator="Wired or proprietary 2.4 GHz links (ASSUMPTION 1-2 ms)",
        key_quantitative_findings="Shorter Connection Intervals reduce the minimum Bluetooth LE connection interval "
                                  "from 7.5 ms to 375 us (a factor of 20), in steps of 125 us; report rates above "
                                  "2 kHz over a secure connection",
        units_and_conditions="ms, us; specification feature (both ends must support Core 6.2)",
        locator="Feature overview; blog", limitations="Read in a search listing; silicon support in 2026 is limited; "
        "the interval is a lower bound on the added latency, not the latency",
        relevance_to_design="The latency a clip-on IMU or a stylus adds over Bluetooth LE (sensing options, section 2.4)",
        transferability_reason="Specification of the link layer", transferability="high",
        design_implication="Budget 7.5-15 ms for a Bluetooth LE pen sensor unless both ends support Core 6.2; prefer a "
                           "wire or a proprietary link for the pen's IMU",
        search_query="WebSearch: Bluetooth Core 6.2 shorter connection interval 375 microseconds", stream="AMF",
        lead_verification="search summary only")
    row(id="AMF-283", topic="Pen plotter as a comparator for accepted writing: AxiDraw V3",
        citation="Evil Mad Scientist Laboratories. AxiDraw V3, product page; Adafruit listing (discontinued).",
        doi_or_url="https://shop.evilmadscientist.com/productsmenu/846 ; https://www.adafruit.com/product/3509",
        source_type="manufacturer web page", evidence_class="manufacturer statement", task_or_setup="Product page",
        comparator="The platen's accepted-writing mode",
        key_quantitative_findings="Usable pen travel 300 x 218 mm (just over A4); vertical pen travel 17 mm; max XY speed "
                                  "38 cm/s; writes with ordinary pens; 'signature machine' use named by the maker; "
                                  "USD 475 (Adafruit listing, marked discontinued, seen 2026-09-30)",
        units_and_conditions="mm, cm/s, USD as displayed", locator="Specifications section; listing price",
        limitations="Price from a reseller listing marked discontinued",
        relevance_to_design="Product fit: a plotter already writes accepted text with a real pen; the platen's value is "
                            "the user's own hand on the pen and tremor cancellation in free writing",
        transferability_reason="Consumer product", transferability="medium",
        design_implication="Price and footprint benchmark for the accepted-writing function",
        search_query="WebSearch: AxiDraw V3 price specifications", stream="AMF")
    row(id="AMF-284", topic="Paper hold-down on a moving carrier: Cricut LightGrip adhesive mat",
        citation="Cricut. LightGrip Machine Mat, 12 in x 12 in, product page.",
        doi_or_url="https://cricut.com/en-us/tools-accessories/machine-tools/machine-mats/lightgrip-machine-mat-12-x-12/2001976.html",
        source_type="manufacturer web page", evidence_class="manufacturer statement", task_or_setup="Product page",
        comparator="Low vacuum; electroadhesion (AMF-114)",
        key_quantitative_findings="Low-tack reusable adhesive carrier sheet that holds printer paper, vellum and light "
                                  "card while a cutting machine moves it; releases the sheet cleanly (no force values)",
        units_and_conditions="qualitative", locator="Product description",
        limitations="No holding force, life or cleaning data",
        relevance_to_design="A silent hold-down alternative to vacuum for the platen",
        transferability_reason="Consumer product in a machine that moves paper",
        design_implication="Offer a tack-mat carrier as the silent hold-down option", search_query="WebSearch: Cricut "
        "LightGrip mat printer paper", stream="AMF")
    row(id="AMF-285", topic="Small DC blower for low-vacuum hold-down: Delta BFB1012M-A",
        citation="Delta Electronics. BFB1012M-A DC blower, product page.",
        doi_or_url="https://www.delta-fan.com/products/BFB1012M-A.html", source_type="manufacturer web page",
        evidence_class="manufacturer statement", task_or_setup="Product page", comparator="Tack mat (AMF-284)",
        key_quantitative_findings="97.2 x 94.4 mm blower, 12 V DC, 0.55 A, 6.6 W, 3200 rpm, 0.777 m3/min (27.44 CFM); "
                                  "static pressure and noise not on the page",
        units_and_conditions="V, A, W, rpm, m3/min", locator="Specification line",
        limitations="No static pressure or noise stated (a search listing gives 64 dB(A) for the faster VH model)",
        relevance_to_design="Vacuum hold-down (about 240 Pa needed for 3 N on A5, CALC) and the noise budget",
        transferability_reason="Manufacturer data", design_implication="Budget up to 6.6 W and measure the noise (EXP-PL07)",
        search_query="WebSearch: Delta BFB1012 blower static pressure", stream="AMF")
    row(id="AMF-286", topic="Closed-loop NEMA 17 steppers for the coarse H-bot (StepperOnline 17E1K series)",
        citation="StepperOnline. P-series NEMA 17 closed-loop stepper motors with 1000-line encoders, product pages.",
        doi_or_url="https://www.omc-stepperonline.com/nema-17-closed-loop-stepper-motor", source_type="manufacturer web page",
        evidence_class="manufacturer statement", task_or_setup="Product pages (read in a search listing)",
        comparator="AMF-92 (open-loop 17HS19-2004S1)",
        key_quantitative_findings="17E1K-07: 72 N cm holding, 2.0 A, 1.75 ohm, 4.0 mH, 1000 PPR; 17E1K-05: 48 N cm, 2.0 A, "
                                  "1.35 ohm, 2.8 mH, 1000 PPR (4000 CPR) magnetic encoder",
        units_and_conditions="N cm, A, ohm, mH, pulses per revolution", locator="Product specification tables",
        limitations="Search listing, not the page itself (the site blocked direct retrieval)",
        relevance_to_design="Coarse stage drive (8 Hz, 20 N cap)", transferability_reason="Manufacturer data",
        design_implication="Stall force through a 20-tooth GT2 pulley about 75-110 N per motor (CALC): cap it in software",
        search_query="WebSearch: NEMA 17 closed loop stepper 1000 line StepperOnline 17E1K", stream="AMF",
        lead_verification="search summary only")
    row(id="CON-110", topic="Minimum gaps to avoid crushing (ISO 13854) and the force / energy screen",
        citation="ISO 13854:2017 Safety of machinery - Minimum gaps to avoid crushing of parts of the human body; as "
                 "summarised by ZT Grassberger (machinery-directive guidance page).",
        doi_or_url="https://www.zt-grassberger.at/en/r/MD/Moving_Parts.html", source_type="website",
        evidence_class="standard", access_level="secondary summary", task_or_setup="Standard (secondary summary)",
        participants_or_bench="n/a", comparator="ISO/TS 15066 (CON-111)",
        key_quantitative_findings="Minimum gaps: whole body 500 mm, head 300, leg 180, foot and arm 120, hand and fist 100, "
                                  "toes 50, finger 25 mm; an actuator that stays below 75 N, 4 J and 25 N/cm2 poses no "
                                  "crushing hazard (as stated on the page)",
        units_and_conditions="mm, N, J, N/cm2", locator="Crushing hazard section",
        limitations="Secondary summary; the 75 N / 4 J / 25 N/cm2 values are the page's, the standard was not read",
        relevance_to_design="Gaps between the moving plate, the palm rest and the frame; force caps",
        transferability_reason="Machinery standard applied to a consumer desk device", transferability="medium",
        design_implication="Coarse and fine force caps of 20 N and a moving mass of 1.4 kg at 50 mm/s (1.8 mJ) sit far "
                           "below the screen; keep fixed gaps below 4-6 mm or above 25 mm", search_query="WebSearch: ISO 13854 minimum gaps fingers",
        stream="CON")
    row(id="CON-111", topic="ISO/TS 15066 body model for hands and fingers (quasi-static contact)",
        citation="Ghanbarzadeh A, Najafi E. Safe Physical Human-Robot Interaction through Variable Impedance Control based "
                 "on ISO/TS 15066. arXiv:2311.13814, 2023, Table 1 (reproducing ISO/TS 15066).",
        doi_or_url="https://arxiv.org/abs/2311.13814", source_type="preprint", evidence_class="standard",
        access_level="full text", task_or_setup="Table of the body-model parameters", participants_or_bench="n/a",
        comparator="CON-110", key_quantitative_findings="Hands and fingers: maximum permissible force 140 N, effective "
                                                        "spring constant 75 N/mm, effective mass 0.6 kg",
        units_and_conditions="N, N/mm, kg", locator="Table 1, p. 3",
        limitations="Reproduced in a preprint; the standard itself not read; limits are for industrial collaborative robots",
        relevance_to_design="Pinch between the moving plate and the palm rest or frame",
        transferability_reason="Industrial standard; conservative for a desk device", transferability="medium",
        design_implication="A 20 N cap is 14 % of the hand and finger limit", search_query="WebSearch: ISO/TS 15066 hands fingers 140 N",
        stream="CON")
    row(id="CON-112", topic="Belt-axis ringing of desktop motion machines (Klipper resonance guide)",
        citation="Klipper documentation. Resonance compensation.",
        doi_or_url="https://www.klipper3d.org/Resonance_Compensation.html", source_type="documentation",
        evidence_class="manufacturer statement", access_level="full text", task_or_setup="Tuning guide",
        participants_or_bench="n/a", comparator="n/a",
        key_quantitative_findings="An axis ringing below about 20-25 Hz calls for a stiffer frame or a lower moving mass; "
                                  "one worked example measures 49.4 Hz; the bed of a bed-slinger slows as mass is added",
        units_and_conditions="Hz", locator="Ringing frequency section",
        limitations="Printers, not a paper platen; no stiffness values", relevance_to_design="Why the coarse belt stage "
        "cannot cancel tremor (a 40 Hz position loop needs structural modes well above 100 Hz)",
        transferability_reason="Same class of belt mechanism", transferability="medium",
        design_implication="Tremor cancellation on a voice-coil fine stage; the belt stage only repositions (8 Hz)",
        search_query="direct URL", stream="CON")
    row(id="CON-113", topic="Nonphysical drift of single-state (LuGre-type) friction models under oscillating loads "
        "below breakaway (why simulated sheet creep is not evidence of slip)",
        citation="Dupont P, Hayward V, Armstrong B, Altpeter F. Single state elastoplastic friction models. IEEE "
                 "Transactions on Automatic Control 47(5):787-792, 2002",
        year="2002", doi_or_url="10.1109/TAC.2002.1000274", source_type="journal", evidence_class="theory and simulation",
        access_level="abstract", task_or_setup="Analysis of single-state friction models (Dahl, LuGre) and an "
        "elastoplastic class that limits presliding drift", participants_or_bench="n/a", comparator="LuGre, Dahl",
        key_quantitative_findings="Existing single-state models exhibit a nonphysical drift when the applied force "
                                  "oscillates below the breakaway force, because presliding is modelled as a combination "
                                  "of elastic and plastic displacement; elastoplastic presliding substantially reduces "
                                  "the drift",
        units_and_conditions="qualitative (model property)", locator="Abstract",
        limitations="Read in a search summary; no numbers for this plant", relevance_to_design="Part (c): the hold-down "
        "and the hand-on-paper contacts are LuGre contacts; the simulated sheet creeps by millimetres over a note under "
        "loads well below the hold's capacity (part c, the 'held' rows), which this property explains",
        transferability_reason="A property of the friction law used here", transferability="high",
        design_implication="Measure sheet slip on the bench (EXP-PL04); an elastoplastic friction law would be needed "
                           "to simulate creep credibly", search_query="WebSearch: Dupont Hayward Armstrong Altpeter "
        "single state elastoplastic friction models drift", stream="CON", retrieved="2026-09-30",
        lead_verification="search summary only")
    return R


def _key(r: Dict):
    pre, num = r["id"].split("-")
    return ({"ACT": 0, "AMF": 1, "CON": 2}.get(pre, 3), int(num))


def write(res: Dict, path: Path) -> List[Dict]:
    rows = sorted(derived_rows(res) + source_rows(), key=_key)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADER, lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in HEADER})
    Path(path).write_bytes(buf.getvalue().encode("utf-8"))
    return rows
