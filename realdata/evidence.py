"""Proposed ledger rows of study R (results/realdata/evidence_rows.csv), with the exact 23-column header of
docs/evidence.csv.  Only sources opened by this study are listed; derived rows carry this study's own calculations,
filled in from realdata.json when it is written.  The lead merges them."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
          "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions",
          "locator", "limitations", "relevance_to_design", "transferability", "transferability_reason",
          "design_implication", "retrieved", "search_query", "stream", "lead_verification"]
DATE = "2026-09-29"


def _f(x, nd=2):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "n/a"


def rows(out: Dict) -> List[Dict]:
    tl = out.get("tremor_library", {})
    cl = tl.get("classes", {})
    q = cl.get("_quantiles_mm", {})
    summ = tl.get("summary", {})
    kin = {r["set"]: r for r in ((out.get("kinematics") or {}).get("table") or [])}
    hw = (out.get("hw1") or {}).get("aggregate", {})

    def k(set_, key, nd=1):
        return _f(kin.get(set_, {}).get(key), nd)

    def sm(key, meas, stat="median", nd=2):
        return _f(((summ.get(key) or {}).get(meas) or {}).get(stat), nd)

    def words(sel, dev):
        v = ((hw.get("real") or {}).get(sel) or {}).get(dev) or {}
        return _f(v.get("words_of_10"), 1)

    def bw(var, dev, key="words_of_10", nd=1):
        v = ((hw.get("bridge") or {}).get(f"{var}/all") or {}).get(dev) or {}
        return _f(v.get(key), nd)
    cal = tl.get("newhandpd_calibration") or {}

    def pct(x, nd=1):
        try:
            return f"{100 * float(x):.{nd}f}"
        except Exception:
            return "n/a"
    sv = ((out.get("kinematics") or {}).get("unipen_survey") or {})
    survey_rows = [r for r in (sv.get("rows") or []) if r.get("measured_lines")]
    pick = {r["setup"]: r for r in survey_rows}
    survey_txt = "; ".join(f"{name} {pct(pick[key].get('share_8_12'))} % at 8-12 Hz, {_f(pick[key].get('speed_mm_s'), 1)} mm/s"
                           for key, name in (("hpp/hpb2", "hpb2 paper"), ("hpp/hpb3", "hpb3 LCD screen"),
                                             ("hpb/hpb5", "hpb5 paper, 6 writers"), ("sta/hpb1", "sta paper"),
                                             ("aga/", "aga (surface undocumented)")) if key in pick)
    cards = {(c["kind"], c["class"]): c for c in ((out.get("hw1") or {}).get("cards") or [])}

    def cw(kind, cls, dev, key="words_of_10", nd=1):
        e = (((cards.get((kind, cls)) or {}).get("pens") or {}).get(dev) or {}).get(key) or {}
        return _f(e.get("mean"), nd)

    def cwi(kind, cls, dev, key="words_of_10", nd=1):
        e = (((cards.get((kind, cls)) or {}).get("pens") or {}).get(dev) or {}).get(key) or {}
        return f"{_f(e.get('mean'), nd)} [{_f(e.get('lo'), nd)}-{_f(e.get('hi'), nd)}]"
    rc = out.get("reader") or {}
    R: List[Dict] = []
    R.append(dict(
        id="CON-80", topic="Real adult handwriting kinematics (BRUSH words, 170 writers): a timing artefact in the tremor band",
        citation="Kotani A, Tellex S, Tompkin J. Generating handwriting via decoupled style descriptors. ECCV 2020, pp. 764-780; BRUSH dataset (refined release, brownvc/decoupled-style-descriptors); kinematics computed by study R",
        year="2020", doi_or_url="https://doi.org/10.1007/978-3-030-58610-2_45 ; https://github.com/brownvc/decoupled-style-descriptors",
        source_type="dataset", evidence_class="physical human study", access_level="full text (dataset and README; paper not opened)",
        task_or_setup="Prescribed short sentences (2-4 words) written with a stylus in a 120 x 748 px box; points resampled every 10 ms by the authors (pen-down only, end-of-stroke flags); per-point character labels",
        participants_or_bench="170 writers, 27,649 samples (33,597 files incl. alternative resamplings)",
        comparator="UNIPEN hpb2 (ballpoint on paper), synthetic writers (aiguide v1, sim2j v2), LIT CON-25; one measurement function",
        key_quantitative_findings=(f"Study R (1 kHz, 20 Hz low-pass, pen-down Welch): {pct(kin.get('real_brush', {}).get('share_8_12'))} % of the pen-down velocity energy at 8-12 Hz "
                                   f"(real writing on paper 1.3-1.7 %, LIT CON-25; UNIPEN hpb2 {pct(kin.get('real_unipen', {}).get('share_8_12'))} %); mean pen-down speed {k('real_brush','speed_mm_s')} mm/s at a letter height DERIVED from LIT PDT-06; "
                                   f"median stroke {k('real_brush','stroke_ms',0)} ms; exponent {k('real_brush','beta',2)}. In HW1 the trackers took this content for tremor "
                                   "(on two tremor-free BRUSH notes the Rev H and Rev J trackers moved the ink by 160-310 um and the TCN by 440-880 um, in a stopped diagnostic run), so BRUSH was rejected as tracker input"),
        units_and_conditions="share of velocity energy; mm/s (scale DERIVED per writer); stylus on screen; pen-up moves not in the release",
        locator="results/realdata/realdata.json kinematics; fig_writer_kinematics; fig_unipen_setups",
        limitations="Screen and stylus, devices undocumented; the artefact's origin (resampling to 10 ms or the devices) is not established; licence: non-commercial research use only",
        relevance_to_design="Tracker tests on real writing need a digitiser without tremor-band artefacts: check the 8-12 Hz share of any writing data before use",
        transferability="low", transferability_reason="The 8-12 Hz content is not writing movement",
        design_implication="Do not test trackers on BRUSH timing; screen every writing data set with the kinematics check (realdata.kinematics)",
        retrieved=DATE, search_query="GitHub README brownvc/decoupled-style-descriptors; Google Drive refined_BRUSH.zip", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-81", topic="Real handwriting with a ballpoint on paper (UNIPEN hpb2): the writing input of the headline, chosen by a kinematics check",
        citation="Guyon I, Schomaker L, Plamondon R, Liberman M, Janet S. UNIPEN project of on-line data exchange and recognizer benchmarks. ICPR 1994; Unipen data set train_r01_v07 (International Unipen Foundation 1999), Zenodo record 1195803; setup hpb2 (Hewlett Packard Laboratories, Palo Alto, 1992)",
        year="1999", doi_or_url="https://doi.org/10.5281/zenodo.1195803", source_type="dataset", evidence_class="physical human study",
        access_level="full text (data and documentation files)",
        task_or_setup="hpb2: Wacom 420-510C, untethered inking pen with a ballpoint refill on preprinted paper forms, 100 samples/s, 500 points/inch (0.05 mm); copied 2-3 word pseudo-phrases; pen-up (hover) points recorded",
        participants_or_bench=f"14 writers in category 8 (hpb2); {(out.get('writing_library') or {}).get('unipen_lines', 'n/a')} lines of lower-case words; survey of all {len(survey_rows)} category-8 setups",
        comparator="LIT CON-20 (speed on paper), CON-24/25/27; BRUSH; synthetic writers",
        key_quantitative_findings=(f"Survey (study R, 60 lines of lower-case words per setup): only hpb2 passes the rule (<= 2.5 % at 8-12 Hz, <= 3 % above 12 Hz, 15-60 mm/s, >= 100 samples/s, >= 15 points/mm, >= 10 writers, paper): "
                                   f"{survey_txt}. hpb2 notes used in HW1: speed {k('real_unipen','speed_mm_s')} mm/s, median stroke {k('real_unipen','stroke_ms',0)} ms, 8-12 Hz share {pct(kin.get('real_unipen', {}).get('share_8_12'))} %, "
                                   f"cumulative 50/90/99 % below {k('real_unipen','f50')}/{k('real_unipen','f90')}/{k('real_unipen','f99')} Hz, exponent {k('real_unipen','beta',2)}. "
                                   "Every line text was written by 2-12 writers (one stack of forms): writers AND texts split (5/9 writers, 81/133 texts)"),
        units_and_conditions="mm/s (documented resolution), sample index / 100 samples/s", locator="results/realdata/realdata.json kinematics.unipen_survey; fig_unipen_setups",
        limitations="Research use only (iUF notice; Zenodo tag CC BY conflicts, stricter terms applied); 1992 healthy adult staff; form boxes, larger than everyday writing for some writers; 14 writers; writers' names in headers never copied",
        relevance_to_design="Real ink trajectories and timing on paper, with a clean digitiser, for tracker and legibility tests",
        transferability="medium", transferability_reason="Healthy adults on paper; not patients; 100 samples/s",
        design_implication="Test trackers on hpb2-class real writing (realdata.library.writing); record patients' writing for EXP-R01",
        retrieved=DATE, search_query="Zenodo record 1195803 (UNIPEN CDROM train_r01_v07)", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-82", topic="UCI Character Trajectories: file constants and real letter timing used as inputs",
        citation="Williams BH. Character Trajectories [dataset]. UCI Machine Learning Repository, 2008", year="2008",
        doi_or_url="https://doi.org/10.24432/C58G7V", source_type="dataset", evidence_class="physical human study", access_level="full text",
        task_or_setup="2858 single-stroke letters (20 letters) of one writer, WACOM tablet, 200 samples/s, velocities Gaussian smoothed (sigma 2)",
        participants_or_bench="1 writer", comparator="LIT CON-25 (the same data analysed by the CON stream)",
        key_quantitative_findings=(f"File constants: consts.units = 0.005 per x/y unit (the scale CON-25 assumed), consts.datanorm = [48.87, 74.19, 22.67], dt 0.005 s. "
                                   f"Letters composed into a test sentence at a 5.0 mm letter height: speed {k('real_chartraj','speed_mm_s')} mm/s, 8-12 Hz share {_f(100*float(kin.get('real_chartraj',{}).get('share_8_12') or float('nan')),1)} %, exponent {k('real_chartraj','beta',2)}"),
        units_and_conditions="Positions integrated from velocities x datanorm x 0.005 mm", locator="mixoutALL_shifted.mat consts; realdata/loaders.chartraj",
        limitations="One writer; isolated large letters; composition of words is ours", relevance_to_design="CC BY source of real letters with real timing for the committed pictures",
        transferability="medium", transferability_reason="Real timing, one writer", design_implication="Use for demonstrations that must be redistributable",
        retrieved=DATE, search_query="https://archive.ics.uci.edu/static/public/175/character+trajectories.zip", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-83", topic="UJI Pen Characters acquisition: no timing information, 100 units/mm",
        citation="Llorens D, Prat F, Marzal A, Vilar JM, Castro MJ, Amengual JC, Barrachina S, Castellanos A, Espana S, Gomez JA, Gorbe J, Gordo A, Palazon V, Peris G, Ramos-Garijo R, Zamora F. The UJIpenchars database: a pen-based database of isolated handwritten characters. LREC 2008",
        year="2008", doi_or_url="http://www.lrec-conf.org/proceedings/lrec2008/pdf/658_paper.pdf ; https://doi.org/10.24432/C5FG8S",
        source_type="conference", evidence_class="physical human study", access_level="full text",
        task_or_setup="Isolated characters on a Toshiba Portege M400 tablet PC with its stylus", participants_or_bench="11 writers (v1); 60 writers (v2 file)",
        comparator="n/a", key_quantitative_findings="'Only X and Y coordinate information was recorded ... without ... timing information'; runs of identical points inside strokes were kept; v2 file header: 100 units per millimetre",
        units_and_conditions="coordinates only", locator="Section 2.1 The Acquisition; ujipenchars2.txt header",
        limitations="Shapes only: timing cannot be recovered", relevance_to_design="Real letter shapes and sizes but no kinematics",
        transferability="medium", transferability_reason="Real shapes, no timing", design_implication="Do not use UJI for tracker or kinematics tests; use timed data",
        retrieved=DATE, search_query="WebSearch: UJIpenchars LREC 2008 pdf", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-84", topic="Wacom Cintiq 12WX: pixel pitch, tablet resolution, accuracy and report rate (the UCI spiral tablet)",
        citation="Wacom. Cintiq 12WX (DTZ-1200W) Installation Guide & Hardware Manual, product specifications (2007)", year="2007",
        doi_or_url="https://101.wacom.com/productsupport/cintiq_manual/cintiq12wx_usermanual_final.pdf", source_type="datasheet",
        evidence_class="manufacturer statement", access_level="full text",
        task_or_setup="Product specifications", participants_or_bench="n/a", comparator="n/a",
        key_quantitative_findings="Pixel pitch 0.204 x 0.204 mm; 1280 x 800 pixels on 261.1 x 163.2 mm; tablet resolution 0.005 mm/point; accuracy +-0.5 mm average; maximum report rate 133 points/s; reading height 5 mm; grip pen 18 g, 175 x 15 mm",
        units_and_conditions="mm, points/s, g", locator="Appendix, Product specifications pp. 56-57",
        limitations="Manufacturer data; the UCI files store screen pixels (DERIVED from their range), so 0.204 mm quantisation applies (0.059 mm RMS per axis, CALC)",
        relevance_to_design="Calibration of the only open PD pen-tip tremor recordings in mm", transferability="high",
        transferability_reason="The device that recorded the data", design_implication="Tip tremor below about 0.06 mm cannot be resolved in the UCI data",
        retrieved=DATE, search_query="WebSearch: Wacom Cintiq 12WX DTZ-1200W specifications", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-85", topic="Open children's online handwriting with dysgraphia (DiaGraMo): available, not used yet",
        citation="Zvoncakova K, Mekyska J, Klocek A, Mucha J, Galaz Z. Multimodal Czech online handwriting and cognitive data from children with and without handwriting disabilities [dataset]. Zenodo 2026, record 21236910",
        year="2026", doi_or_url="https://doi.org/10.5281/zenodo.21236910", source_type="dataset", evidence_class="physical human study",
        access_level="abstract only (record description and file list)",
        task_or_setup="16 graphomotor and writing tasks (copying, dictation, spirals, loops) on a Wacom Cintiq 16, x-y, pressure, tilt at about 167 Hz; SVC raw data",
        participants_or_bench="276 Czech children aged 8-12, 161 with dysgraphia", comparator="Typically developing children",
        key_quantitative_findings="CC BY 4.0; 1.36 GB; raw SVC per task and child plus merged JSON",
        units_and_conditions="Tablet units (Cintiq 16)", locator="Zenodo record description", limitations="Not analysed by study R; children; Czech",
        relevance_to_design="Open, redistributable real sentences with timing and hover, for the poor-handwriting and dyslexia studies",
        transferability="medium", transferability_reason="Children's writing, the target group of the practice functions",
        design_implication="Use it for study S and for the practice functions (EXP-R04)", retrieved=DATE,
        search_query="Zenodo API search: dysgraphia handwriting online tablet children Czech", stream="CON", lead_verification=""))
    R.append(dict(
        id="PDT-75", topic="Parkinson's tremor at the pen tip while drawing (UCI spiral tablet data), re-analysed: severity classes in mm",
        citation="Isenkul ME, Sakar BE, Kursun O. Improved spiral test using digitized graphics tablet for monitoring Parkinson's disease. ICEHTM 2014; UCI dataset 395 (2017); re-analysis by study R",
        year="2014", doi_or_url="https://doi.org/10.24432/C5Q01S", source_type="dataset", evidence_class="physical human study",
        access_level="full text (data; paper not opened)",
        task_or_setup="Static and dynamic spirals and circles around a point on a Wacom Cintiq 12WX; tremor line against the fitted broadband background (Welch 4 s); background-corrected major-axis amplitude",
        participants_or_bench=f"62 PD (hw_dataset 25 + new_dataset 37), 15 controls; {cl.get('_n_pd_subjects_with_line','n/a')} PD with a tremor line",
        comparator="Controls (95th percentile of the line ratio = detection threshold)",
        key_quantitative_findings=(f"Boundaries FITTED on the {cl.get('_n_fit_subjects', 'n/a')} tuning PD subjects with a tremor line (of {cl.get('_n_pd_subjects_with_line','n/a')}); checked on the "
                                   f"{(cl.get('_validation_test_subjects') or {}).get('n', 'n/a')} test subjects: mild/moderate/severe shares {pct((cl.get('_validation_test_subjects') or {}).get('share_mild'), 0)}/"
                                   f"{pct((cl.get('_validation_test_subjects') or {}).get('share_moderate'), 0)}/{pct((cl.get('_validation_test_subjects') or {}).get('share_severe'), 0)} % (expected 50/40/10). "
                                   f"Tuning PD tip tremor (peak, per subject): p10 {_f(q.get('p10'))}, p50 {_f(q.get('p50'))}, p75 {_f(q.get('p75'))}, p90 {_f(q.get('p90'))}, max {_f(q.get('max'))} mm; class representatives "
                                   f"{_f(cl.get('mild',{}).get('representative_mm'))} / {_f(cl.get('moderate',{}).get('representative_mm'))} / {_f(cl.get('severe',{}).get('representative_mm'))} mm. "
                                   f"Classes: mild {_f(cl.get('mild',{}).get('range_mm',[0,0])[0])}-{_f(cl.get('mild',{}).get('range_mm',[0,0])[1])} mm, moderate {_f(cl.get('moderate',{}).get('range_mm',[0,0])[0])}-{_f(cl.get('moderate',{}).get('range_mm',[0,0])[1])} mm, severe {_f(cl.get('severe',{}).get('range_mm',[0,0])[0])}-{_f(cl.get('severe',{}).get('range_mm',[0,0])[1])} mm. "
                                   f"Frequency median {sm('uci_spiral/PD/kinetic','f0')} Hz; envelope CV median {sm('uci_spiral/PD/kinetic','env_cv')}; frequency wander SD {sm('uci_spiral/PD/kinetic','f_sd')} Hz. "
                                   f"{len(tl.get('duplicates_removed') or [])} byte-identical duplicate recordings removed across the sources."),
        units_and_conditions="mm (screen pixels x 0.204 mm, DERIVED), Hz; kinetic (drawing)", locator="results/realdata/realdata.json tremor_library",
        limitations="Tablet surface and an 18 g stylus; pixel quantisation; people who cannot draw on a tablet are missing (severe tremor under-represented, cf. PDT-13); PD only",
        relevance_to_design="The only open calibrated pen-tip tremor recordings: the size of the job for the nose",
        transferability="medium", transferability_reason="Real patients at the pen tip, but tablet drawing and PD only",
        design_implication="Most PD tip tremor while drawing is 0.1-0.4 mm; the top 10 % reach 1-7 mm; design and claims per class",
        retrieved=DATE, search_query="https://archive.ics.uci.edu/static/public/395/...zip", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-76", topic="Smart-pen acceleration spectra in PD and healthy writers (NewHandPD BiSP signals), re-analysed",
        citation="Pereira CR, Weber SAT, Hook C, Rosa GH, Papa JP. Deep learning-aided Parkinson's disease diagnosis from handwritten dynamics. SIBGRAPI 2016; NewHandPD signals (UNESP)",
        year="2016", doi_or_url="https://wwwp.fc.unesp.br/~papa/pub/datasets/Handpd/ ; http://sibgrapi.sid.inpe.br/col/sid.inpe.br/sibgrapi/2016/07.08.22.47/doc/opf-sibgrapi16.pdf",
        source_type="dataset", evidence_class="physical human study", access_level="full text (data and paper)",
        task_or_setup=("Raw files: NewHandPD PatientSignal.zip and HealthySignal.zip (UNESP HandPD page), Signal/<task>-<P|H><n>.txt, tasks sigSp1-4 (spirals), sigMea1-4 (meanders), "
                       "circA/circB (circles), sigDiaA/B (diadochokinesis); header '#<Samplerate>1000</Samplerate>' in every file, no per-sample time stamps (time = index / 1000); "
                       "6 columns: CH1 microphone, CH2 finger grip, CH3 axial refill pressure, CH4-6 tilt and acceleration X/Y/Z (sensor at the rear end, paper Fig. 3). "
                       "Study R preprocessing: byte-identical duplicates removed, gravity calibration of CH4-6 (sphere fit), 0.5 s trimmed at both ends, Welch 4 s"),
        participants_or_bench="31 PD (372 files), 35 healthy (420 files)", comparator="Healthy group",
        key_quantitative_findings=(f"DERIVED gravity calibration of CH4-6 (study R): offsets {', '.join(_f(v) for v in cal.get('offset', []))} units, gains {', '.join(_f(v) for v in cal.get('gain_ms2_per_unit', []))} m/s^2 per unit (about 1.46 units per g), residual {_f(cal.get('residual_rms_ms2'),3)} m/s^2 RMS over {cal.get('n_samples','n/a')} quasi-static samples. "
                                   f"Tremor line share PD {_f((summ.get('newhandpd/PD/kinetic') or {}).get('detected_share'))} vs healthy {_f((summ.get('newhandpd/control/kinetic') or {}).get('detected_share'))}; "
                                   f"PD line frequency median {sm('newhandpd/PD/kinetic','f0')} Hz. The patient archive contains byte-identical files under two patient numbers (e.g. circB-P2 = circB-P25). "
                                   "The header rate (1000/s) is consistent with the recordings: spiral durations median 20 s (PD) and 11 s (healthy) and PD tremor lines at 5-6 Hz; at 200/s (Tironi et al. 2025, PDT-83) they would be 100 s, 53 s and about 1.2 Hz. "
                                   "Within the files, CH1-3 change every sample but CH4-6 (tilt/acceleration) are held for 3-4 samples: the accelerometer updates about 250-330 times per second (sample-and-hold), which may be the '200 Hz' motion rate reported by PDT-83"),
        units_and_conditions="m/s^2 (DERIVED); Hz", locator="results/realdata/realdata.json; SIBGRAPI 2016 Section III-A",
        limitations="No licence stated; controls younger (age confound, PDT-29); accelerometer at the pen's rear; no positions",
        relevance_to_design="Closest open analogue of the pen's own IMU in patients", transferability="medium",
        transferability_reason="Same sensing modality, uncalibrated by the authors", design_implication="The pen IMU sees PD tremor lines at 4-8 Hz; calibrate the pen's own IMU against gravity in the same way",
        retrieved=DATE, search_query="HandPD page (NewHealthy/HealthySignal.zip, NewPatients/PatientSignal.zip)", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-77", topic="Essential tremor waveforms: hand accelerometry at rest and posture (Zenodo), re-analysed",
        citation="Pardo-Valencia J, Ammann C, Foffani G. Accelerometry recordings from essential tremor patients [dataset]. Zenodo 2026, record 19130599",
        year="2026", doi_or_url="https://doi.org/10.5281/zenodo.19130599", source_type="dataset", evidence_class="physical human study", access_level="full text (data and README)",
        task_or_setup="One accelerometer axis on the dorsum of each hand; posture (arms extended) and rest, 100 s each; 2 Hz-2 kHz, x1000, 5 kHz",
        participants_or_bench="29 ET (58 hands); FTM total in the clinical file", comparator="Rest vs posture",
        key_quantitative_findings=(f"Posture: line frequency median {sm('zenodo_et/ET/postural','f0')} Hz, envelope CV {sm('zenodo_et/ET/postural','env_cv')}, frequency wander SD {sm('zenodo_et/ET/postural','f_sd')} Hz, second-harmonic ratio {sm('zenodo_et/ET/postural','harmonic_excess')}; "
                                   f"rest: {sm('zenodo_et/ET/rest','f0')} Hz; line detected in {_f((summ.get('zenodo_et/ET/postural') or {}).get('detected_share'))} (posture) and {_f((summ.get('zenodo_et/ET/rest') or {}).get('detected_share'))} (rest) of hands"),
        units_and_conditions="Hz; amplitude in arbitrary units (sensor sensitivity not published)", locator="acc_signal_database.mat; realdata.json tremor_library",
        limitations="Amplitude not calibrated; hand, not pen; artefacts removed by splicing (some waveforms rejected by the quality gate)",
        relevance_to_design="Real ET temporal structure for simulation inputs", transferability="medium", transferability_reason="Real ET, hand posture not writing",
        design_implication="Trackers must cope with envelope CV about 0.6 and frequency wander about 0.6 Hz, not the model's 0.3 and 0.3 Hz",
        retrieved=DATE, search_query="WebSearch: PhysioNet essential tremor accelerometer dataset open access", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-78", topic="Wrist tremor in ET, PD and healthy people across rest, postural and kinetic tasks (PADS smartwatch), re-analysed",
        citation="Varghese J, Brenner A, Plagwitz L, van Alen C, Fujarski M, Warnecke T. PADS - Parkinsons Disease Smartwatch dataset (1.0.0). PhysioNet 2024; Varghese J et al. npj Parkinsons Dis 10:9 (2024)",
        year="2024", doi_or_url="https://doi.org/10.13026/m0w9-zx22", source_type="dataset", evidence_class="physical human study", access_level="full text (data, documentation; paper not opened)",
        task_or_setup="Two Apple Watch Series 4 at 100 samples/s, 11 tasks of 10-20 s; preprocessed files (gravity removed by the authors)",
        participants_or_bench="Used: 28 ET, 80 PD (seeded random), 79 healthy", comparator="Healthy",
        key_quantitative_findings=(f"Writing-hand wrist, detected lines (controls' 95th percentile per condition): ET posture {sm('pads/ET/postural','amp_wrist_mm')} mm, ET kinetic {sm('pads/ET/kinetic','amp_wrist_mm')} mm, PD rest {sm('pads/PD/rest','amp_wrist_mm')} mm (medians, both wrists pooled in the summary); "
                                   f"detection share ET rest/posture/kinetic {_f((summ.get('pads/ET/rest') or {}).get('detected_share'))}/{_f((summ.get('pads/ET/postural') or {}).get('detected_share'))}/{_f((summ.get('pads/ET/kinetic') or {}).get('detected_share'))}, PD {_f((summ.get('pads/PD/rest') or {}).get('detected_share'))}/{_f((summ.get('pads/PD/postural') or {}).get('detected_share'))}/{_f((summ.get('pads/PD/kinetic') or {}).get('detected_share'))}"),
        units_and_conditions="mm at the wrist (band-limited double integration, CALC); 9.76 s records", locator="realdata.json tremor_library.summary",
        limitations="CC BY-NC-SA 4.0 (statistics only); watch above the wrist joint misses wrist flexion; voluntary movement contaminates kinetic tasks; short records",
        relevance_to_design="Calibrated tremor size in ET vs PD and rest vs action", transferability="low", transferability_reason="Wrist, not pen tip; lower bound",
        design_implication="Use for rest/action behaviour and frequency, not for tip amplitude", retrieved=DATE,
        search_query="physionet.org/content/parkinsons-disease-smartwatch/1.0.0/", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-79", topic="ET postural tremor frequency and the accelerometry method of the Zenodo ET recordings' lab",
        citation="Urso D, Monje MHG, Fernandez-Rodriguez B, Vela-Desojo L, Oliviero A, Foffani G, Ammann C. Transcranial static magnetic field stimulation of the primary motor cortex in essential tremor: a randomized pilot study. npj Parkinsons Dis (2025)",
        year="2025", doi_or_url="https://doi.org/10.1038/s41531-025-01182-x ; PMC12658149", source_type="journal", evidence_class="physical human study",
        access_level="full text (Europe PMC XML)", task_or_setup="Accelerometer on the dorsal hand (Z along the hand, Y perpendicular to the palm), 2 x 100 s arms outstretched, 2 Hz-2 kHz, x1000 (Digitimer D360), CED 1401",
        participants_or_bench="27 ET (23 analysed)", comparator="Before vs after tSMS",
        key_quantitative_findings="Baseline postural tremor frequency 5.5 +- 0.8 Hz (contralateral) and 5.4 +- 0.8 Hz (ipsilateral); amplitude reported in log10 arbitrary units (3.0 +- 1.1), i.e. not calibrated",
        units_and_conditions="Hz; log10 a.u.", locator="Methods (clinical outcomes); secondary outcomes table", limitations="Not a writing task; amplitude uncalibrated",
        relevance_to_design="Confirms the frequency of the ET waveforms used here and that their amplitude cannot be calibrated", transferability="medium",
        transferability_reason="Same method as the dataset", design_implication="Set ET amplitude by class, keep the waveform", retrieved=DATE,
        search_query="Europe PMC DOI:10.1038/s41531-025-01182-x", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-80", topic="Real tremor is about twice as irregular as the project's tremor model (study R calculation)",
        citation="This study's calculation (realdata/tremorlib.py) on uci_spiral, zenodo_et and PADS against stabpen.signals.TremorSpec defaults",
        year="2026", doi_or_url="results/realdata/realdata.json", source_type="derived calculation", evidence_class="calculation", access_level="full text",
        task_or_setup="Hilbert envelope and instantaneous frequency of the f0 +- 2 Hz major axis; recordings with a tremor line",
        participants_or_bench="As PDT-75, PDT-77, PDT-78", comparator="TremorSpec am_depth 0.3, f_jitter 0.3 Hz, harmonic 0.15, ellipticity 0.4",
        key_quantitative_findings=(f"Envelope CV (amplitude wander) median: PD tip {sm('uci_spiral/PD/kinetic','env_cv')}, ET hand posture {sm('zenodo_et/ET/postural','env_cv')} (model 0.3); frequency wander SD: {sm('uci_spiral/PD/kinetic','f_sd')} and {sm('zenodo_et/ET/postural','f_sd')} Hz (model 0.3 Hz); "
                                   f"ellipticity of real 2-D tip tremor median {_f((tl.get('shape_2d') or {}).get('ellipticity_median'))} (model 0.4)"),
        units_and_conditions="dimensionless; Hz", locator="realdata/tremorlib.py; fig_tremor_library", limitations="Short records inflate wander estimates for weak lines; tablet quantisation",
        relevance_to_design="Trackers tuned on the smooth model meet more irregular tremor", transferability="medium", transferability_reason="Real recordings, few ET tip data",
        design_implication="Tune and test trackers on the real-waveform library (realdata.library.tremor)", retrieved=DATE, search_query="n/a (derived)", stream="PDT", lead_verification=""))
    R.append(dict(
        id="EML-80", topic="TrOCR handwriting readers as the 'words you can read' judge (literal transcription)",
        citation="Li M, Lv T, Chen J, Cui L, Lu Y, Florencio D, Zhang C, Li Z, Wei F. TrOCR: Transformer-based optical character recognition with pre-trained models. arXiv 2109.10282 (2021); models microsoft/trocr-small-handwritten and microsoft/trocr-base-handwritten (fine-tuned on IAM; model cards: MIT for base, none stated for small)",
        year="2021", doi_or_url="https://arxiv.org/abs/2109.10282 ; https://huggingface.co/microsoft/trocr-base-handwritten", source_type="preprint",
        evidence_class="numerical simulation", access_level="secondary account (model cards read; paper not opened)",
        task_or_setup="Encoder-decoder transformer reading a line image; used locally on rendered ink (0.5 mm ink, 10 px/mm); greedy decoding, no lexicon, no spelling correction; a word counts only when it equals the intended word",
        participants_or_bench="n/a", comparator="Clean (tremor-free) ink of the same notes",
        key_quantitative_findings=(f"Reader chosen on TUNING notes by a rule fixed beforehand: small {pct((rc.get('microsoft/trocr-small-handwritten') or {}).get('share'), 0)} % vs base "
                                   f"{pct((rc.get('microsoft/trocr-base-handwritten') or {}).get('share'), 0)} % of clean words read -> {rc.get('chosen', 'n/a')}. "
                                   f"Test notes without tremor (the ceiling): {cw('PD', 'severe', 'none', 'clean_words_of_10')} of 10"),
        units_and_conditions="words read exactly after word alignment; CER per line", locator="realdata/ocr.py; realdata.json reader",
        limitations="An AI reader, not a person; its decoder has an implicit language prior from IAM text; pseudo-phrases with rare words are hard even when clean",
        relevance_to_design="A reader that has never seen the writers, closer to a person than a template reader", transferability="medium",
        transferability_reason="Standard handwriting OCR; human legibility may differ", design_implication="Confirm with a blinded human panel (EXP-R03)",
        retrieved=DATE, search_query="huggingface.co/api/models/microsoft/trocr-base-handwritten", stream="EML", lead_verification=""))
    R.append(dict(
        id="EML-81", topic="Headline pen comparison on real handwriting and real tremor, with a measured-error page sensor (study R simulation, HW1)",
        citation="This study's simulation (realdata/hw1.py): model HW1, UNIPEN hpb2 test writers, UCI PD and Zenodo ET test subjects' tremor at the data classes; page sensor ideal (bound) and DeltaPen-class (LIT OPT-02; pessimistic)",
        year="2026", doi_or_url="results/realdata/realdata.json", source_type="derived calculation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="Ordinary pen, Rev H + tracker, Rev J + gated tracker, Rev J + TCN, Rev J perfect knowledge; one note of about 10 words per test writer; 95 % bootstrap over writers",
        participants_or_bench="Simulated (real recorded inputs; 9 test writers)", comparator="Ordinary pen, same writer, note and tremor",
        key_quantitative_findings=(f"Words read of 10, ordinary pen / Rev J gated (DeltaPen-class sensor) / Rev J limit: PD severe {cwi('PD','severe','none')} / {cwi('PD','severe','revJ_gated|deltapen')} / {cwi('PD','severe','revJ_oracle')}; "
                                   f"ET severe {cwi('ET','severe','none')} / {cwi('ET','severe','revJ_gated|deltapen')} / {cwi('ET','severe','revJ_oracle')}; "
                                   f"PD moderate {cw('PD','moderate','none')} / {cw('PD','moderate','revJ_gated|deltapen')} / {cw('PD','moderate','revJ_oracle')}. "
                                   f"Tremor left at the tip, Rev J gated vs ordinary pen (amplitude ratio): PD severe {cw('PD','severe','revJ_gated|deltapen','tip_tremor_ratio',2)}, ET severe {cw('ET','severe','revJ_gated|deltapen','tip_tremor_ratio',2)}; "
                                   f"with the ideal sensor {cw('PD','severe','revJ_gated','tip_tremor_ratio',2)} and {cw('ET','severe','revJ_gated','tip_tremor_ratio',2)}. "
                                   f"Clean writing moved (false correction, tremor-free notes): Rev J gated {cw('PD','severe','revJ_gated|deltapen','false_correction_um',0)} um (DeltaPen-class) and {cw('PD','severe','revJ_gated','false_correction_um',0)} um (ideal); "
                                   f"TCN {cw('PD','severe','revJ_tcn|deltapen','false_correction_um',0)} um"),
        units_and_conditions="words of 10; mm peak at the tip in f0 +- 2 Hz; um RMS; SIMULATION", locator="results/realdata/fig_words_read.png, fig_tremor_left.png, fig_bridge_*.png",
        limitations="Simulation; the writer adapts to each pen; healthy writers' notes plus patients' tremor (not patients' writing); AI reader; Rev J is a PROPOSED DESIGN; the DeltaPen-class sensor model gives all of the reference's error to the sensor",
        relevance_to_design="What the pens change for real writing and tremor, and how much the page sensor matters", transferability="low",
        transferability_reason="Simulation with real inputs, not a measurement", design_implication="See docs/real_data.md; measure the page sensor on paper (EXP-S01) before any claim",
        retrieved=DATE, search_query="n/a (derived)", stream="EML", lead_verification=""))
    R.append(dict(
        id="EML-82", topic="OnHW sensor-pen handwriting datasets (Fraunhofer IIS): licence, handedness and timestamps checked",
        citation=("Fraunhofer IIS. Online Handwriting Recognition from Sensor-Enhanced Pens (OnHW datasets), project page and README; README reference [1]: Ott F, Ruegamer D, Heublein L, Hamann T, Barth J, Bischl B, Mutschler C. "
                  "Benchmarking online sequence-to-sequence and character-based handwriting recognition from IMU-enhanced pens; dataset paper: The OnHW dataset: online handwriting recognition from IMU-enhanced ballpoint pens with machine learning. Proc ACM IMWUT 4(3), 2020 (title and DOI from the ACM listing)"),
        year="2020", doi_or_url="https://doi.org/10.1145/3411842 ; https://www.iis.fraunhofer.de/de/ff/lv/dataanalytics/anwproj/schreibtrainer/onhw-dataset.html",
        source_type="dataset", evidence_class="physical human study", access_level="secondary account (project page and README opened; paper not opened; data not downloaded)",
        task_or_setup="STABILO DigiPen: front accelerometer and gyroscope (STM LSM6DSL), rear accelerometer (Freescale MMA8451Q), magnetometer (ALPS HSCDTD008A), force sensor (ALPS HSFPAR003A); characters, equations, words; writer-dependent and -independent 5-fold splits",
        participants_or_bench="OnHW-chars 119 writers, 31,275 characters (search-result summary of the IMWUT paper); other sets as listed on the page",
        comparator="n/a", key_quantitative_findings=("Page: 'Only right-handed recordings are released' (OnHW-chars; '_L' left-handed sets exist for some); timestamp 'Millis' = "
                                                    "'The timestamp when the data were processed on the tablet computer that the pen was connected to during recording' (not acquisition time); "
                                                    "no licence stated on the page or in the README (direct downloads)"),
        units_and_conditions="n/a", locator="Project page sections Sensors, Sensor Data, Dataset; README.pdf", limitations="No licence: permission needed before use or redistribution; recognition benchmark without page trajectory or tremor ground truth",
        relevance_to_design="The recognition-and-spelling dataset of the programme (study S), not a tremor or tracker input", transferability="medium",
        transferability_reason="Same sensing modality as the pen (IMU and force), healthy writers", design_implication="Request the licence before use (EXP-R06); keep it out of the natural-handwriting dataset",
        retrieved=DATE, search_query="WebSearch: OnHW dataset Fraunhofer IIS; https://www2.iis.fraunhofer.de/LV-OnHW/README.pdf", stream="EML", lead_verification=""))
    R.append(dict(
        id="PDT-81", topic="Primary writing tremor overlaps the frequency of normal writing oscillation",
        citation="Bain PG, Findley LJ, Britton TC, Rothwell JC, Gresty MA, Thompson PD, Marsden CD. Primary writing tremor. Brain 1995;118(6):1461-1472",
        year="1995", doi_or_url="https://doi.org/10.1093/brain/118.6.1461 ; PMID 8595477", source_type="journal", evidence_class="physical human study",
        access_level="abstract only (PubMed)", task_or_setup="Clinical and neurophysiological study: surface polymyography and accelerometry during writing",
        participants_or_bench="21 patients with primary writing tremor (20 male); healthy controls", comparator="Healthy control subjects",
        key_quantitative_findings="Accelerometry: writing tremor 4.1-7.3 Hz (median 5.5 Hz); normal subjects wrote with a 4.0-7.7 Hz oscillation (median 4.6 Hz); EMG rhythmic activity 4.1-7.3 Hz; writing speed 73.1 +- 6.6 vs 127.7 +- 6.4 letters/min (mean +- SEM)",
        units_and_conditions="Hz; letters per minute", locator="Abstract", limitations="Abstract only; task-specific tremor, small cohort; not ET or PD",
        relevance_to_design="A frequency band alone cannot separate tremor from writing movement", transferability="medium",
        transferability_reason="Writing task, accelerometry; primary writing tremor is a specific group",
        design_implication="Trackers must not rely on a 4-8 Hz notch; evaluate false correction on real writing (REQ-DATA-003)",
        retrieved=DATE, search_query="NCBI E-utilities efetch PMID 8595477", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-82", topic="Essential tremor measured in writing and drawing on a digitising tablet; weak link to wrist tremor",
        citation="Elble RJ, Brilliant M, Leffler K, Higgins C. Quantification of essential tremor in writing and drawing. Mov Disord 1996;11(1):70-78",
        year="1996", doi_or_url="https://doi.org/10.1002/mds.870110113 ; PMID 8771070", source_type="journal", evidence_class="physical human study",
        access_level="abstract only (PubMed)", task_or_setup="Cursive e's and l's on ruled paper mounted on a digitising tablet (ballpoint); Archimedes spirals (40 patients); triaxial accelerometer on the extended hand",
        participants_or_bench="87 ET patients, 15-84 years (mean 61.8)", comparator="Postural wrist accelerometry",
        key_quantitative_findings="Detectable change in 30 patients (p = 0.01, power 90 %): 36.0 % in writing acceleration amplitude and 8.3 % in frequency; wrist-writing correlations < 0.60 (amplitude) and < 0.25 (frequency); very severe tremor could not be recorded when the pen left the tablet",
        units_and_conditions="cm/s^2, Hz", locator="Abstract", limitations="Abstract only; amplitude as acceleration; missing contact biases severe cases",
        relevance_to_design="Wrist or hand tremor does not predict writing tremor well; severe cases lose contact",
        transferability="high", transferability_reason="ET writing on paper on a tablet",
        design_implication="Record ink and pen-up time at the tip (EXP-R01); treat the hand-based ET waveforms here as shape, not size",
        retrieved=DATE, search_query="NCBI E-utilities efetch PMID 8771070", stream="PDT", lead_verification=""))
    R.append(dict(
        id="PDT-83", topic="A smart-pen study that reuses the NewHandPD signals: which files, what timing",
        citation="Tironi JC, Fernandes A, Borges RC, Silva LA, Parreira WD. A smart pen prototype with adaptive algorithms for stabilizing handwriting tremor signals in Parkinson's disease. Sci Rep 2025;15:28659",
        year="2025", doi_or_url="https://doi.org/10.1038/s41598-025-14196-5 ; PMC12325923", source_type="journal", evidence_class="numerical simulation",
        access_level="full text (Europe PMC XML; CC BY-NC-ND 4.0)",
        task_or_setup="Fx-LMS, Fx-NLMS, RLS and Kalman filters simulated on NewHandPD spiral signals; Teensy 4.1 implementation; orbital shaking table; coin vibration motor",
        participants_or_bench="Signals of 31 PD patients (one trial each); no human participants in device validation",
        comparator="Between algorithms (MSE, convergence)",
        key_quantitative_findings=("'the hand tremor signals of 31 PD patients, available in the NewHandPD dataset, were used ... derived from the dynamic trajectory data recorded by the BiSP device during spiral drawing tasks'; "
                                   "'the full acquisition included motion data recorded at 200 Hz'; Data availability cites the HandPD image repository (736 JPEG images). "
                                   "The signal files carry '#<Samplerate>1000</Samplerate>', and study R's durations and tremor frequencies support 1000/s; the accelerometer channels, however, update only every 3-4 samples (about 250-330/s; PDT-76), close to the paper's 200 Hz. The paper names no file, column or preprocessing"),
        units_and_conditions="dB MSE; no amplitude in mm", locator="Materials and methods; Data availability", limitations="Signal provenance not specified beyond the task; rate stated differently from the files; MSE is not ink",
        relevance_to_design="An open algorithm baseline on the same patient signals; its timing must be reconciled before reuse", transferability="low",
        transferability_reason="Vibration motor and signal MSE, no physical ink outcome",
        design_implication="If the programme reuses NewHandPD signals, use the files' 1000/s header, name the files (sigSp1-4) and report ink outcomes",
        retrieved=DATE, search_query="Europe PMC fullTextXML PMC12325923", stream="PDT", lead_verification=""))
    return R


def write(path: Path, out: Dict) -> None:
    R = rows(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in R:
            w.writerow({h: r.get(h, "") for h in HEADER})
