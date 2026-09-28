"""Proposed evidence-ledger rows (results/fusion/evidence_rows.csv) in the exact column format of docs/evidence.csv.

Ids used (and only these): OPT-37..OPT-42 datasheets read for this study (manufacturer statements),
PDT-32 literature on the distribution of tremor over the upper-limb joints, and derived rows for this
study's own calculations and simulations: OPT-43 (pen rotation / lever arm), ACT-40..ACT-44 (closed-loop
results on P1), EML-31..EML-32 (firmware cost, learned estimator).  Derived rows take their numbers
from results/fusion/*.json when those exist, so the ledger and the results cannot disagree.
docs/evidence.csv itself is not edited (the lead integrates).
"""
from __future__ import annotations

import csv
import json
import os

from . import RESULTS, ROOT

RETRIEVED = "2026-09-28"


def header():
    with open(os.path.join(ROOT, "docs", "evidence.csv"), encoding="utf-8") as f:
        return next(csv.reader(f))


def _j(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p)) if os.path.exists(p) else None


def _fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def rows():
    R = []

    def add(**kw):
        R.append(kw)

    add(id="OPT-37", topic="IMU for tremor sensing on the pencil board: ST LSM6DSV16X noise, ODR, filtering, current, package",
        citation="STMicroelectronics. LSM6DSV16X - 6-axis IMU with embedded sensor fusion, AI, Qvar for high-end applications. Datasheet DS13510 Rev 3, March 2023.",
        year="2023", doi_or_url="https://www.st.com/resource/en/datasheet/lsm6dsv16x.pdf ; copy read: https://cdn.sparkfun.com/assets/4/1/8/e/2/lsm6dsv16x.pdf",
        source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
        task_or_setup="Mechanical and electrical characteristics, typical values at Vdd 1.8 V, 25 C",
        participants_or_bench="LSM6DSV16X (typical device)", comparator="high-performance vs normal vs low-power modes",
        key_quantitative_findings=("Accelerometer noise density 60 ug/sqrt(Hz) in high-performance mode (FS +-2 to +-16 g, independent of ODR), "
                                   "100 ug/sqrt(Hz) in normal mode; gyroscope rate noise density 2.8 mdps/sqrt(Hz); accelerometer and gyroscope "
                                   "ODR up to 7.68 kHz; analog anti-aliasing filter active in high-performance and normal modes, digital LPF1 cut-off "
                                   "ODR/2, optional LPF2 ODR/4 to ODR/800; zero-g offset +-12 mg after calibration, +-0.07 mg/C; zero-rate level "
                                   "+-1 dps, +-0.006 dps/C; supply current 0.65 mA accelerometer + gyroscope high-performance, 190 uA accelerometer "
                                   "only; LGA-14L 2.5 x 3.0 x 0.83 mm; 1.71-3.6 V"),
        units_and_conditions="typical values (not guaranteed), Vdd 1.8 V, 25 C",
        locator="Table 3 (mechanical characteristics, p. 11-12); Table 4 (electrical characteristics, p. 13); s6.2 accelerometer power modes; Table 69 accelerometer bandwidth configurations",
        limitations="Typical values; the filter group delay (latency) is not stated; the offset figures are after calibration",
        relevance_to_design="config/parameters.yaml sensing.imu_acc_noise_density is 70 ug/sqrt(Hz) marked 'verify datasheet'; the datasheet says 60 (high-performance mode). fusion/ uses 60.",
        transferability="high", transferability_reason="The part named in config/parameters.yaml sensing and docs/icd.md s2",
        design_implication=("Accelerometer noise is not what limits tremor estimation (displacement-equivalent 0.9 um/sqrt(Hz) at 4 Hz, 0.1 at 12 Hz); keep the "
                            "6-axis part because the gyroscope removes the pen-rotation errors (OPT-43); measure the digital filter latency on the bench"),
        retrieved=RETRIEVED, search_query="WebSearch: LSM6DSV16X datasheet accelerometer noise density ODR 7.68 kHz current consumption; st.com PDF returned HTTP 503, SparkFun copy of DS13510 Rev 3 read with pdftotext",
        stream="OPT", lead_verification="")
    add(id="OPT-38", topic="Alternative board IMU: TDK ICM-45686 noise, current, package",
        citation="TDK InvenSense. ICM-45686 product page (invensense.tdk.com/en-us/products/6-axis/icm-45686), citing datasheet DS-000577 v1.0.",
        year="2026", doi_or_url="https://www.invensense.tdk.com/en-us/products/6-axis/icm-45686", source_type="manufacturer web page",
        evidence_class="manufacturer statement", access_level="product page (datasheet not retrievable here)",
        task_or_setup="Product specification summary", participants_or_bench="ICM-45686", comparator="none",
        key_quantitative_findings="Accelerometer noise 70 ug/rtHz; gyroscope noise 3.8 mdps/rtHz; 6-axis low-noise mode current 0.42 mA; package 0.81 x 2.50 x 3.00 mm",
        units_and_conditions="as listed on the product page (mode and conditions not stated there)", locator="product page specification table",
        limitations="The datasheet PDF URL returned a search page; ODR range, filter latency and offset not verified; a third-party page (pcbsync.com) quoting DS-000577 gives max ODR 6.4 kHz (unverified)",
        relevance_to_design="Lower current than the LSM6DSV16X combo (0.42 vs 0.65 mA) at similar noise; a second source for the board IMU",
        transferability="medium", transferability_reason="Same class and package as the LSM6DSV16X; datasheet details unverified",
        design_implication="Acceptable second source for the board IMU if its filter latency (unstated here) is <= 1 ms; verify on DS-000577",
        retrieved=RETRIEVED, search_query="WebSearch: ICM-45686 datasheet accelerometer noise density ODR package size current; WebFetch of the TDK product page",
        stream="OPT", lead_verification="")
    add(id="OPT-39", topic="Alternative board IMU: TDK ICM-42688-P noise, current, package",
        citation="TDK InvenSense. ICM-42688-P product page (invensense.tdk.com/en-us/products/6-axis/icm-42688-p), citing datasheet DS-000347 v1.9.",
        year="2026", doi_or_url="https://www.invensense.tdk.com/en-us/products/6-axis/icm-42688-p", source_type="manufacturer web page",
        evidence_class="manufacturer statement", access_level="product page (datasheet returned HTTP 403)",
        task_or_setup="Product specification summary", participants_or_bench="ICM-42688-P", comparator="none",
        key_quantitative_findings="Accelerometer noise 70 ug/rtHz; gyroscope noise 2.8 mdps/rtHz; 6-axis low-noise mode current 0.88 mA; package 0.91 x 2.50 x 3.00 mm",
        units_and_conditions="as listed on the product page", locator="product page specification table",
        limitations="Max ODR (32 kHz) and the programmable 2nd-order anti-alias filter appear only in a search snippet of DS-000347 v1.6; not read in full",
        relevance_to_design="Same noise class as the LSM6DSV16X at higher current", transferability="medium",
        transferability_reason="Same class; datasheet details unverified", design_implication="No advantage over the LSM6DSV16X for this use; keep as a fallback",
        retrieved=RETRIEVED, search_query="WebSearch: ICM-42688-P datasheet DS-000347 accelerometer noise; WebFetch of the TDK product page",
        stream="OPT", lead_verification="")
    add(id="OPT-40", topic="Alternative board IMU: Bosch BMI323 noise, bandwidth, stated group delay, current",
        citation="Bosch Sensortec. BMI323 Datasheet, document BST-BMI323-DS000-13, revision 1.7 (15 Apr 2026).",
        year="2026", doi_or_url="https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi323-ds000.pdf",
        source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
        task_or_setup="Accelerometer and gyroscope specifications; power modes; group delay in high-performance mode",
        participants_or_bench="BMI323 (typical)", comparator="high-performance vs normal vs low-power mode",
        key_quantitative_findings=("Accelerometer noise density 180 ug/sqrt(Hz) (high-performance, 8 g); gyroscope 0.007 dps/sqrt(Hz); ODR 12.5-6400 Hz; "
                                   "3 dB bandwidth 674/1181/1677 Hz at ODR 1600/3200/6400 Hz; accelerometer group delay 0.63/0.47/0.39 ms at "
                                   "ODR 1600/3200/6400 Hz (ODR/2 filter); zero-g offset +-35 mg soldered, TCO +-0.3 mg/K; current 790 uA IMU, "
                                   "145 uA accelerometer only (high-performance); LGA 2.5 x 3.0 x 0.83 mm"),
        units_and_conditions="typical values", locator="accelerometer/gyroscope specification tables (p. 9-10); Table 10 (power modes); Table 11 (accelerometer group delay)",
        limitations="Typical values", relevance_to_design="The only candidate whose datasheet states the digital-filter latency: 0.4-0.6 ms at the rates used here, consistent with the 0.35 ms read latency assumed on top of the 1.04 ms anti-aliasing filter",
        transferability="high", transferability_reason="Same package class; used here for the latency assumption and as a lower-cost option",
        design_implication="3x the LSM6DSV16X noise density: still adequate for the tremor band above ~6 Hz (displacement noise 0.7 um/sqrt(Hz) at 8 Hz), marginal at 4 Hz for 0.1 mm tremor",
        retrieved=RETRIEVED, search_query="WebSearch: BMI323 datasheet accelerometer noise density ODR 6.4 kHz package; PDF read with pdftotext",
        stream="OPT", lead_verification="")
    add(id="OPT-41", topic="Nose accelerometer candidate: Bosch BMA530 (1.2 x 0.8 mm WLCSP)",
        citation="Bosch Sensortec. BMA530 product flyer, BST-BMA530-FL000-02, version 1.2 (03/2024).",
        year="2024", doi_or_url="https://www.bosch-sensortec.com/media/boschsensortec/downloads/product_flyer/bst-bma530-fl000.pdf",
        source_type="product flyer", evidence_class="manufacturer statement", access_level="full text (flyer)",
        task_or_setup="Technical data summary", participants_or_bench="BMA530", comparator="none",
        key_quantitative_findings="Noise density 120 ug/sqrt(Hz); ODR ~1.56 Hz to 6.4 kHz; offset +-75 mg soldered over life, TCO +-0.5 mg/K; current 125 uA high performance continuous, 18 uA low power at 100 Hz; WLCSP 1.2 x 0.8 x 0.55 mm; I3C/I2C/SPI",
        units_and_conditions="typical values from the flyer", locator="flyer p. 2 technical data table",
        limitations="Flyer, not the datasheet: filter bandwidth and latency not stated",
        relevance_to_design="Small enough for the flex near the nose Hall sensor (7.9 mm bore) at 17 mm from the nib",
        transferability="medium", transferability_reason="Flyer values only",
        design_implication="Enables the dual-accelerometer lever-arm cancellation (OPT-43) without a gyroscope; its noise (2x the board IMU) is what limits that option at 4 Hz",
        retrieved=RETRIEVED, search_query="WebSearch: Bosch BMA530 accelerometer datasheet noise density package; flyer PDF read with pdftotext",
        stream="OPT", lead_verification="")
    add(id="OPT-42", topic="Micropower accelerometer: ADI ADXL367 noise, ODR ceiling, current, package",
        citation="Analog Devices. ADXL367 Micropower, 3-Axis, +-2 g/+-4 g/+-8 g Digital Output MEMS Accelerometer. Data Sheet Rev. 0 (3/2022).",
        year="2022", doi_or_url="https://www.analog.com/media/en/technical-documentation/data-sheets/adxl367.pdf ; copy read: https://www.farnell.com/datasheets/4097458.pdf",
        source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
        task_or_setup="Specifications table", participants_or_bench="ADXL367", comparator="normal vs low-noise mode",
        key_quantitative_findings="Noise density 370 ug/sqrt(Hz) normal, 200 ug/sqrt(Hz) low-noise mode, 170 ug/sqrt(Hz) at 400 Hz ODR; 2-pole anti-aliasing filter -3 dB at ODR/2; ODR 12.5-400 Hz; 0.89 uA at 100 Hz ODR (normal), 1.77 uA low noise; 0 g offset TC 0.6 mg/C; 2.2 x 2.3 x 0.87 mm",
        units_and_conditions="typical, 2.0 V supply", locator="Specifications table p. 4 (noise performance, bandwidth, power supply)",
        limitations="Typical values at 2.0 V; revision history: 3/2022 Revision 0 (initial version)",
        relevance_to_design="The 400 Hz ODR ceiling (200 Hz bandwidth) and 2.8x noise make it unsuitable for the 2 kHz estimator; fine as a wake-up / pen-pick-up detector",
        transferability="high", transferability_reason="Datasheet values", design_implication="Do not use for tremor estimation; possible always-on wake sensor",
        retrieved=RETRIEVED, search_query="WebSearch: ADXL367 datasheet noise density ultralow noise mode ODR current package; Farnell copy of Rev. 0 read with pdftotext",
        stream="OPT", lead_verification="")
    add(id="PDT-32", topic="Which joints carry essential tremor: distribution over the upper-limb degrees of freedom (supports pen rotation, not only translation)",
        citation="Pigg AC, Thompson-Westra J, Mente K, Maurer CW, Haubenberger D, Hallett M, Charles SK. Distribution of tremor among the major degrees of freedom of the upper limb in subjects with Essential Tremor. Clin Neurophysiol 2020;131(11):2700-2712.",
        year="2020", doi_or_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7606740 ; https://www.sciencedirect.com/science/article/abs/pii/S1388245720304624",
        source_type="journal", evidence_class="physical human study", access_level="full text (PMC author manuscript) via summary tool; ScienceDirect HTTP 403",
        task_or_setup="Electromagnetic motion capture (trakSTAR, 360 samples/s) on sternum, upper arm, forearm and hand during postural and kinetic tasks in several limb configurations; tremor as 4-12 Hz power per degree of freedom",
        participants_or_bench="22 people with essential tremor (25 enrolled, 3 excluded)", comparator="postural vs kinetic tasks; limb configurations",
        key_quantitative_findings="Kinetic tremor greatest in forearm pronation-supination and wrist flexion-extension, intermediate in shoulder internal-external rotation and wrist radial-ulnar deviation, lower in shoulder and elbow flexion-extension, least in shoulder abduction-adduction; distal kinetic tremor about 122x the postural value (41x proximal)",
        units_and_conditions="4-12 Hz band power per DOF (deg^2/s^4); Figure 3D ranking, Table 1 subject powers",
        locator="Abstract; Figure 3D; Table 1",
        limitations="No handwriting task; joint-angle power, not pen-tip displacement; how wrist and forearm rotation map onto the pen depends on the grip",
        relevance_to_design="Tremor at the pen is largely rotational (wrist and forearm), so the pen rotates as well as translates; an IMU 100 mm up the barrel does not see the nib's motion",
        transferability="medium", transferability_reason="ET only, arm tasks without a pen",
        design_implication="Model pen rotation (fusion/sensors.py rho_t) and compensate the IMU with the gyroscope; measure the rotation ratio at the pen in EXP-H01 (IMU + nib reference)",
        retrieved=RETRIEVED, search_query="WebSearch: Distribution of tremor among the major degrees of freedom of the upper limb in subjects with essential tremor Pigg Charles 2020; WebFetch PMC7606740",
        stream="PDT", lead_verification="")
    # ---------------------------------------------------------------- derived rows (numbers from results/fusion)
    S = _j("sensors.json")
    ol = {}
    if S:
        for r in S["leverarm_open_loop"]["rows"]:
            ol.setdefault((r["comp"], r["rho"]), []).append(r["band_error_rel"])
    def olm(c, rho):
        v = ol.get((c, rho))
        return None if not v else sum(v) / len(v)
    cl = S["leverarm_closed_loop"]["summary"] if S else {}
    def clm(k):
        return cl.get(k, {}).get("ratio_mean")
    add(id="OPT-43", topic="Pen rotation corrupts the board IMU's view of the nib; gyroscope or nose accelerometer compensation (this study)",
        citation="This ledger's calculation and simulation: fusion/sensors.py (kinematic pen rotation on P1 housing motion), results/fusion/sensors.json",
        year="2026", doi_or_url="results/fusion/sensors.json; fusion/sensors.py", source_type="derived calculation / simulation",
        evidence_class="numerical simulation", access_level="full text",
        task_or_setup="P1 housing motion (4 kHz) plus a kinematic small rotation of the rigid pen proportional to the hand tremor and finger strokes (rho = displacement 100 mm up the barrel per unit nib displacement); IMU 100 mm, nose accelerometer 17 mm from the nib; LSM6DSV16X / BMA530 noise, bias, scale, misalignment",
        participants_or_bench="none (simulation)", comparator="no compensation; nose only; nose + board (rigid-body extrapolation); board 6-axis with gyroscope (attitude and lever arm); translation-only reference",
        key_quantitative_findings=(f"Tremor-band error of the nib acceleration estimate relative to the truth, mean over 4-12 Hz at rho 0.5: none {_fmt(olm('none', 0.5))}, "
                                   f"nose only {_fmt(olm('nose', 0.5))}, dual {_fmt(olm('dual', 0.5))}, gyro {_fmt(olm('gyro', 0.5))}, reference {_fmt(olm('ideal', 0.5))}; "
                                   f"at rho 1.0: none {_fmt(olm('none', 1.0))}, gyro {_fmt(olm('gyro', 1.0))}. Closed-loop AKF ratio (4/8/12 Hz, 0.3 mm, rho 0.5) with the 120 Hz page sensor: "
                                   f"none {_fmt(clm('120_none_rho0.5'))}, gyro {_fmt(clm('120_gyro_rho0.5'))}, dual {_fmt(clm('120_dual_rho0.5'))}; with the 1 kHz page sensor none {_fmt(clm('1k_none_rho0.5'))}, gyro {_fmt(clm('1k_gyro_rho0.5'))}"),
        units_and_conditions="ratio of RMS values, 3-15 Hz band; seeds 5000 (open loop), 200-201 (closed loop)",
        locator="results/fusion/sensors.json leverarm_open_loop, leverarm_closed_loop",
        limitations="The rotation ratio rho and its phase are ASSUMPTIONS (no measurement of pen rotation during writing tremor); roll about the barrel and centripetal terms neglected; rigid pen",
        relevance_to_design="Decides the sensor set: a 6-axis IMU (gyroscope) or a second accelerometer in the nose",
        transferability="medium", transferability_reason="Kinematic model on a simulated pen",
        design_implication="Ship the 6-axis IMU with gyroscope compensation of attitude and lever arm; a nose accelerometer is the gyroscope-free alternative; never use the board accelerometer uncompensated",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="OPT", lead_verification="")
    G = _j("grid.json")
    def gm(lab, key="ratio_mean"):
        return (G or {}).get("summary", {}).get(lab, {}).get("overall", {}).get(key)
    def dm(lab):
        return (G or {}).get("distortion_um", {}).get(lab, {}).get("mean")
    add(id="ACT-40", topic="Closed-loop tremor estimators with accelerometer data on the pencil model P1 (this study)",
        citation="This ledger's simulation: fusion/ (estimators, harness), results/fusion/grid.json",
        year="2026", doi_or_url="results/fusion/grid.json; docs/sensor_fusion_ai.md", source_type="derived simulation",
        evidence_class="numerical simulation", access_level="full text",
        task_or_setup="P1 grid 4-12 Hz x 0.1/0.3/0.5 mm x seeds 200-203, harness convention of sim/pencil/run_study.py; causal estimators on sensor models (page sensor 1 kHz/2 ms or 120 Hz/10 ms, LSM6DSV16X-class IMU with gyroscope compensation) injected through Controller(mode='external')",
        participants_or_bench="none (simulation)", comparator="no correction; oracle; tremor-band oracle; frozen Kalman (core)",
        key_quantitative_findings=(f"Mean ink error ratio over the 60 conditions: oracle {_fmt(gm('oracle'))}, tremor-band oracle {_fmt(gm('oracle_band'))}, frozen Kalman {_fmt(gm('kfosc_internal'))}, "
                                   f"AKF {_fmt(gm('akf'))}, AKF 120 Hz page {_fmt(gm('akf_120'))}, BMFLC {_fmt(gm('bmflc'))}, WFLC {_fmt(gm('wflc'))}, GRU {_fmt(gm('gru'))}, personalised AKF {_fmt(gm('akf_personal'))}; "
                                   f"band (3-15 Hz) ratio AKF {_fmt(gm('akf', 'band_ratio_mean'))} vs frozen {_fmt(gm('kfosc_internal', 'band_ratio_mean'))}; distortion AKF {_fmt(dm('akf'), 0)} um, frozen {_fmt(dm('kfosc_internal'), 0)} um, GRU {_fmt(dm('gru'), 0)} um"),
        units_and_conditions="ratio of ink-error RMS against the tremor-free neutral pen; distortion in um RMS", locator="results/fusion/grid.json summary",
        limitations="Synthetic handwriting and tremor; one simulator; the pen rotation and friction parameters are assumptions; open-loop hand",
        relevance_to_design="Sets the achievable free-writing benefit with realistic sensing",
        transferability="low", transferability_reason="Simulation only; the friction-dither part of the target depends on the LuGre parameters (EXP-B02)",
        design_implication="See docs/sensor_fusion_ai.md: ship the AKF (6-axis IMU + page sensor) as the default estimator; the learned model stays behind the guard until EXP-E01",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="ACT", lead_verification="")
    add(id="ACT-41", topic="In P1 most of the oracle's disturbance is a tremor-induced friction (dither) shift of the housing path, not tremor-band motion (this study)",
        citation="This ledger's simulation: fusion/harness.py (tremor-band oracle), results/fusion/grid.json",
        year="2026", doi_or_url="results/fusion/grid.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="The oracle's disturbance d = p_H(tremor) - p_H(clean) split into < 3 Hz and 3-15 Hz; the true 3-15 Hz part injected as an external estimate (zero-phase, not causal); frictionless-skid control",
        participants_or_bench="none (simulation)", comparator="full oracle",
        key_quantitative_findings=(f"Mean ink error ratio: oracle {_fmt(gm('oracle'))}, tremor-band oracle {_fmt(gm('oracle_band'))}. With the skid friction set to zero (and nib friction 0.02) the < 3 Hz part of d nearly vanishes "
                                   "(seed 200, 6 Hz 0.3 mm: 247 -> 15 um RMS) and the two oracles coincide (0.18 vs 0.18)"),
        units_and_conditions="um RMS in contact; ratios as ACT-40", locator="results/fusion/grid.json (oracle, oracle_band); docs/sensor_fusion_ai.md s3",
        limitations="LuGre friction parameters of skid and nib are assumptions; the open-loop hand does not adapt to friction",
        relevance_to_design="No tremor-band estimator can reach the harness 'physical limit': its target includes re-creating the pen's tremor-free stick-slip",
        transferability="low", transferability_reason="Depends on the friction model",
        design_implication="Report the tremor-band limit next to the oracle; measure skid and nib friction under vibration (EXP-B01/B02) before treating the oracle ratio as a target",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="ACT", lead_verification="")
    J = (S or {}).get("jitter_check", {}).get("summary", {})
    def jm(lab, key="ratio_mean"):
        return J.get(lab, {}).get(key)
    add(id="ACT-42", topic="Estimate jitter near the stage resonance dithers the pen's friction and costs cancellation and power (this study)",
        citation="This ledger's simulation: fusion/run_study.py jitter check, results/fusion/sensors.json jitter_check",
        year="2026", doi_or_url="results/fusion/sensors.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="Tremor-band oracle plus band-limited random jitter, seeds 200-201, 8 Hz 0.3 mm, P1 (stage first resonance 192 Hz)",
        participants_or_bench="none (simulation)", comparator="tremor-band oracle without jitter",
        key_quantitative_findings=(f"Ratio {_fmt(jm('tremor-band oracle'))} without jitter; {_fmt(jm('+ 10 um jitter 20-200 Hz'))} with 10 um RMS at 20-200 Hz; "
                                   f"{_fmt(jm('+ 5 um jitter 200-900 Hz'))} with 5 um and {_fmt(jm('+ 10 um jitter 200-900 Hz'))} with 10 um at 200-900 Hz; class-B rail power "
                                   f"{_fmt(jm('tremor-band oracle', 'P_rail_classB_mW_mean'), 0)} -> {_fmt(jm('+ 10 um jitter 200-900 Hz', 'P_rail_classB_mW_mean'), 0)} mW"),
        units_and_conditions="ink error ratio; mW", locator="results/fusion/sensors.json jitter_check",
        limitations="Friction model assumptions (LuGre, P-9); one tremor condition",
        relevance_to_design="High-rate accelerometer noise must not reach the stage command",
        transferability="medium", transferability_reason="The resonance and servo are the P1 design; the friction coupling is model-dependent",
        design_implication="Low-pass every estimator output at <= 60 Hz with the group delay predicted ahead (fusion/estimators.py), or shape the servo; include the stage command spectrum in EXP-B09",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="ACT", lead_verification="")
    C = _j("context.json")
    def cs(lab, key="wo_path_rms_um"):
        return (C or {}).get("summary", {}).get(lab, {}).get(key, {}).get("mean")
    te = (C or {}).get("template_error", {})
    def tem(c, k):
        return te.get(c, {}).get(k, {}).get("mean")
    add(id="ACT-43", topic="AI + physical: the phone's letter template as an intent prior inside the tremor estimator (this study)",
        citation="This ledger's simulation: fusion/context.py, fusion/aieval.py, results/fusion/context.json",
        year="2026", doi_or_url="results/fusion/context.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="aiguide writers 0-5, 'return library books by friday', 0.3 mm tremor 4-10 Hz, P1 (pencil_P1); templates oracle / AI-correct / AI-predicted (confidence-gated) / wrong letter; template as a cross-track pseudo-measurement with a template-bias state, confidence-scaled noise, gating and a drop rule",
        participants_or_bench="none (simulation)", comparator="no correction; frozen Kalman; the old template pull (guided mode); AKF without template",
        key_quantitative_findings=(f"Template error (AI-correct): total {_fmt(tem('ai_correct', 'total'), 0)} um, after per-letter offset {_fmt(tem('ai_correct', 'after_offset'), 0)} um, "
                                   f"after per-letter affine {_fmt(tem('ai_correct', 'after_affine'), 0)} um, 3-15 Hz along the stroke {_fmt(tem('ai_correct', 'band_3_15Hz_rms_um'), 0)} um. "
                                   f"Path RMS to intended (writing only): no correction {_fmt(cs('neutral'), 0)}, pull AI-correct {_fmt(cs('pull_ai_correct'), 0)}, "
                                   f"AKF {_fmt(cs('akf'), 0)}, prior AI-correct {_fmt(cs('ctx_ai_correct'), 0)}, prior AI-predicted {_fmt(cs('ctx_ai_predicted'), 0)}, prior wrong letter full {_fmt(cs('ctx_wrong_letter_full'), 0)} um"),
        units_and_conditions="um RMS; mean over 24 scenarios", locator="results/fusion/context.json summary, template_error",
        limitations="Synthetic glyph writers and templates; one sentence; open-loop hand; pen anchoring emulated from the neutral run",
        relevance_to_design="Decides how the phone's predictions should reach the pen",
        transferability="low", transferability_reason="Simulation on synthetic writers",
        design_implication="Send templates to the pen as priors for the estimator (record 0x06), never as pull targets; keep confidence gating and the drop rule",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="ACT", lead_verification="")
    P = (G or {}).get("summary", {}).get("akf_personal", {}).get("overall", {})
    add(id="ACT-44", topic="Per-writer calibration of the tremor estimator from a 20 s known-template task (this study)",
        citation="This ledger's simulation: fusion/personal.py, results/fusion/grid.json (akf_personal)",
        year="2026", doi_or_url="results/fusion/grid.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="Spiral, circle and lines with the writer's tremor (independent realisation), page sensor minus the known template band-passed 3-15 Hz; frequency, amplitude, harmonic; choice among 12 AKF variants around the population set",
        participants_or_bench="none (simulation)", comparator="population AKF parameters",
        key_quantitative_findings=f"Mean ink error ratio over the 60 test conditions: personalised {_fmt(P.get('ratio_mean'))} vs population {_fmt(gm('akf'))}; distortion {_fmt(dm('akf_personal'), 0)} vs {_fmt(dm('akf'), 0)} um",
        units_and_conditions="as ACT-40", locator="results/fusion/grid.json summary akf_personal",
        limitations="The calibration tremor has the same frequency and amplitude as the test tremor (stationary writer); day-to-day variability not modelled",
        relevance_to_design="CAL_USER content and the calibration task", transferability="low", transferability_reason="Simulation; real tremor varies within and between sessions",
        design_implication="Add a 20 s calibration (spiral + lines) that sets the estimator's frequency window and amplitude gate; re-run it when the tracked frequency drifts",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="ACT", lead_verification="")
    B = _j("budget.json")
    def bm(k, key):
        return (B or {}).get("p1_default_page_1kHz", {}).get(k, {}).get(key)
    add(id="EML-31", topic="Firmware cost of the tremor estimators on an nRF54L15-class Cortex-M33 (this study)",
        citation="This ledger's calculation: fusion/budget.py, results/fusion/budget.json (inputs AMF-44)",
        year="2026", doi_or_url="results/fusion/budget.json", source_type="derived calculation", evidence_class="calculation", access_level="full text",
        task_or_setup="MAC counts of the implementations (dense and block-structured covariance), memory, CPU share at 128 MHz with an assumed 2 cycles per float MAC",
        participants_or_bench="none", comparator="frozen Kalman filter",
        key_quantitative_findings=(f"CPU share (structured, float32): frozen Kalman {_fmt(100 * (bm('kfosc', 'cpu_fraction_f32') or 0), 1)} %, AKF {_fmt(100 * (bm('akf', 'cpu_fraction_f32') or 0), 1)} %, "
                                   f"context filter {_fmt(100 * (bm('context', 'cpu_fraction_f32') or 0), 1)} %, BMFLC {_fmt(100 * (bm('bmflc', 'cpu_fraction_f32') or 0), 1)} %, GRU float {_fmt(100 * (bm('gru', 'cpu_fraction_f32') or 0), 1)} % "
                                   f"(int8 CMSIS-NN {_fmt(100 * (bm('gru', 'cpu_fraction_int8_cmsis') or 0), 1)} %)"),
        units_and_conditions="1 kHz page sensor; accelerometer averaged to 1.92 kHz", locator="results/fusion/budget.json",
        limitations="Cycle model assumed (1.5-3 cycles per float MAC); no profiling on the target", relevance_to_design="Whether each estimator fits the 0.5 ms stage tick and the RAM next to the servo, the ML guard and BLE",
        transferability="medium", transferability_reason="Instruction-level costs to be measured on hardware",
        design_implication="AKF fits with margin; the joint context filter needs the structured implementation or a lower template rate",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="EML", lead_verification="")
    Lj = _j("learned.json")
    mi = ((Lj or {}).get("models", {}) or {}).get("gru48_1k", {})
    add(id="EML-32", topic="Learned GRU tremor estimator trained on P1 runs with IMU + page-sensor inputs (this study)",
        citation="This ledger's simulation: fusion/learned.py, results/fusion/learned.json and results/fusion/model/",
        year="2026", doi_or_url="results/fusion/learned.json", source_type="derived simulation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup=f"GRU({mi.get('n_in', 7)} -> {mi.get('hidden', 48)}) + linear head at 1 kHz; {mi.get('n_train_pairs', 'n/a')} domain-randomised P1 run pairs (hand impedance, tremor 3-14 Hz 0.05-0.6 mm, tilt, force, friction, writing), false-correction penalty",
        participants_or_bench="none (simulation)", comparator="AKF; frozen Kalman",
        key_quantitative_findings=f"Mean ink error ratio {_fmt(gm('gru'))} (AKF {_fmt(gm('akf'))}); distortion {_fmt(dm('gru'), 0)} um; {mi.get('macs_per_step', 'n/a')} MAC per step, {mi.get('params', 'n/a')} parameters; training {_fmt((mi.get('total_s') or 0) / 60, 0)} min on 2 threads",
        units_and_conditions="as ACT-40", locator="results/fusion/learned.json; results/fusion/grid.json",
        limitations="Trained and tested on the same generators (sigma-lognormal handwriting, synthetic tremor, P1); the aiguide glyph writers are the only out-of-distribution check",
        relevance_to_design="Whether a learned estimator should ship", transferability="low", transferability_reason="Generator-specific (ml/README.md c.4)",
        design_implication="Keep behind the ICD s5 guard; decide on EXP-E01 real data",
        retrieved=RETRIEVED, search_query="n/a (derived)", stream="EML", lead_verification="")
    return R


def write(path=None):
    path = path or os.path.join(RESULTS, "evidence_rows.csv")
    head = header()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        for r in rows():
            w.writerow([r.get(k, "") for k in head])
    return path


if __name__ == "__main__":
    print(write())
