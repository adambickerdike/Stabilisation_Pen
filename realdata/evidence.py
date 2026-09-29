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
    R: List[Dict] = []
    R.append(dict(
        id="CON-80", topic="Real adult handwriting kinematics (words, 170 writers): BRUSH dataset, re-analysed",
        citation="Kotani A, Tellex S, Tompkin J. Generating handwriting via decoupled style descriptors. ECCV 2020, pp. 764-780; BRUSH dataset (refined release, brownvc/decoupled-style-descriptors); kinematics computed by study R",
        year="2020", doi_or_url="https://doi.org/10.1007/978-3-030-58610-2_45 ; https://github.com/brownvc/decoupled-style-descriptors",
        source_type="dataset", evidence_class="physical human study", access_level="full text (dataset and README; paper not opened)",
        task_or_setup="Prescribed short sentences (2-4 words) written with a stylus in a 120 x 748 px box; points resampled every 10 ms by the authors (pen-down only, end-of-stroke flags); per-point character labels",
        participants_or_bench="170 writers, 27,649 samples (33,597 files incl. alternative resamplings)",
        comparator="Synthetic writers (aiguide v1, sim2j v2) measured with the same function",
        key_quantitative_findings=(f"Study R, same measurement as sim2 (1 kHz, 20 Hz low-pass): mean pen-down speed {k('real_brush','speed_mm_s')} mm/s at a letter height DERIVED from LIT PDT-06; "
                                   f"median stroke {k('real_brush','stroke_ms',0)} ms; 8-12 Hz share of velocity energy {_f(100*float(kin.get('real_brush',{}).get('share_8_12') or float('nan')),1)} %; "
                                   f"cumulative velocity energy 50/90/99 % below {k('real_brush','f50')}/{k('real_brush','f90')}/{k('real_brush','f99')} Hz; power-law exponent {k('real_brush','beta',2)}. "
                                   "2676 lower-case word recordings; writers split 40/60 tuning/test by a hash of the writer id."),
        units_and_conditions="mm/s (scale DERIVED per writer), ms, Hz, share; stylus on screen; pen-up moves not in the release (added as ASSUMPTION in-air moves)",
        locator="results/realdata/realdata.json kinematics; realdata/kinematics.py",
        limitations="Screen and stylus, not paper; devices differ per writer and the pixel size is undocumented (speed in mm/s depends on the assumed letter height); pen-up timing lost; licence: non-commercial research use only",
        relevance_to_design="Real writing movement that trackers must leave alone: how much of it lies in the tremor band",
        transferability="medium", transferability_reason="Many adult writers and real timing, but stylus on glass and derived scale",
        design_implication="Simulate trackers and pens on real writing (this library), not on glyph writers, before trusting false-correction and tremor-separation numbers",
        retrieved=DATE, search_query="GitHub README brownvc/decoupled-style-descriptors; Google Drive refined_BRUSH.zip", stream="CON", lead_verification=""))
    R.append(dict(
        id="CON-81", topic="Real handwriting speed on paper and tablets (UNIPEN train_r01_v07), re-analysed",
        citation="Guyon I, Schomaker L, Plamondon R, Liberman M, Janet S. UNIPEN project of on-line data exchange and recognizer benchmarks. ICPR 1994; Unipen data set train_r01_v07 (International Unipen Foundation 1999), Zenodo record 1195803",
        year="1999", doi_or_url="https://doi.org/10.5281/zenodo.1195803", source_type="dataset", evidence_class="physical human study",
        access_level="full text (data and documentation files)",
        task_or_setup="Category 8 text lines from contributors recording >= 100 samples/s at >= 10 points/mm (e.g. dar2: CalComp DrawingBoard II, ballpoint on A4 paper, 200 samples/s, 0.01 mm/unit)",
        participants_or_bench="Many writers of several institutions (see contributors in realdata.json)", comparator="Synthetic writers; LIT CON-20",
        key_quantitative_findings=(f"Study R: mean pen-down speed {k('real_unipen','speed_mm_s')} mm/s; median stroke {k('real_unipen','stroke_ms',0)} ms; 8-12 Hz share {_f(100*float(kin.get('real_unipen',{}).get('share_8_12') or float('nan')),1)} %; "
                                   f"cumulative 50/90/99 % below {k('real_unipen','f50')}/{k('real_unipen','f90')}/{k('real_unipen','f99')} Hz; exponent {k('real_unipen','beta',2)}"),
        units_and_conditions="mm/s with each contributor's documented resolution; sample index / documented rate as time",
        locator="results/realdata/realdata.json kinematics", limitations="Research use only (iUF notice; Zenodo tag CC BY conflicts, stricter terms applied); 1990s digitisers; writers' names in headers never copied",
        relevance_to_design="Physical writing speeds on real devices, including ballpoint on paper",
        transferability="high", transferability_reason="Adults, real text, physical units", design_implication="Writer models and trackers must be tested at these speeds",
        retrieved=DATE, search_query="Zenodo search: online handwriting dataset sentences stylus timestamps", stream="CON", lead_verification=""))
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
        key_quantitative_findings=(f"PD tip tremor (peak, per subject): p10 {_f(q.get('p10'))}, p50 {_f(q.get('p50'))}, p75 {_f(q.get('p75'))}, p90 {_f(q.get('p90'))}, max {_f(q.get('max'))} mm. "
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
        task_or_setup="BiSP pen at 1000 samples/s: CH1 microphone, CH2 finger grip, CH3 axial refill pressure, CH4-6 tilt and acceleration X/Y/Z (sensor at the rear end, paper Fig. 3); spirals, meanders, circles",
        participants_or_bench="31 PD (372 files), 35 healthy (420 files)", comparator="Healthy group",
        key_quantitative_findings=(f"DERIVED gravity calibration of CH4-6 (study R): offsets {', '.join(_f(v) for v in cal.get('offset', []))} units, gains {', '.join(_f(v) for v in cal.get('gain_ms2_per_unit', []))} m/s^2 per unit (about 1.46 units per g), residual {_f(cal.get('residual_rms_ms2'),3)} m/s^2 RMS over {cal.get('n_samples','n/a')} quasi-static samples. "
                                   f"Tremor line share PD {_f((summ.get('newhandpd/PD/kinetic') or {}).get('detected_share'))} vs healthy {_f((summ.get('newhandpd/control/kinetic') or {}).get('detected_share'))}; "
                                   f"PD line frequency median {sm('newhandpd/PD/kinetic','f0')} Hz. The patient archive contains byte-identical files under two patient numbers (e.g. circB-P2 = circB-P25)."),
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
        id="EML-80", topic="TrOCR handwriting reader used as the 'words you can read' judge",
        citation="Li M, Lv T, Chen J, Cui L, Lu Y, Florencio D, Zhang C, Li Z, Wei F. TrOCR: Transformer-based optical character recognition with pre-trained models. arXiv 2109.10282 (2021); model microsoft/trocr-small-handwritten (fine-tuned on IAM)",
        year="2021", doi_or_url="https://arxiv.org/abs/2109.10282 ; https://huggingface.co/microsoft/trocr-small-handwritten", source_type="preprint",
        evidence_class="numerical simulation", access_level="secondary account (model card read; paper not opened)",
        task_or_setup="Encoder-decoder transformer reading a line image; used locally on rendered simulated ink (0.5 mm ink, 10 px/mm), greedy decoding",
        participants_or_bench="n/a", comparator="Clean (tremor-free) ink of the same writing",
        key_quantitative_findings=(f"Study R: reads {_f(10*float(((hw.get('clean') or {}).get('clean_real') or {}).get('none',{}).get('words_share') or float('nan')),1)} of 10 clean real words (BRUSH test writers) and 8.2 of 10 on tuning writers; the reader's own ceiling is reported with every result"),
        units_and_conditions="words read exactly after word alignment", locator="realdata/ocr.py", limitations="An AI reader, not a person; trained on IAM (English); model card states no licence (code MIT)",
        relevance_to_design="A reader that has never seen the writer, closer to a person than a template reader", transferability="medium",
        transferability_reason="Standard handwriting OCR; human legibility may differ", design_implication="Confirm with human readers (EXP-R03)",
        retrieved=DATE, search_query="huggingface_hub list_repo_files microsoft/trocr-small-handwritten", stream="EML", lead_verification=""))
    R.append(dict(
        id="EML-81", topic="Headline pen comparison on real handwriting and real tremor (study R simulation, HW1)",
        citation="This study's simulation (realdata/hw1.py): model HW1 with BRUSH test writers and UCI/Zenodo test tremor recordings",
        year="2026", doi_or_url="results/realdata/realdata.json", source_type="derived calculation", evidence_class="numerical simulation", access_level="full text",
        task_or_setup="Ordinary pen, Rev H + tracker, Rev J + gated tracker, Rev J + TCN, Rev J perfect knowledge; data severity classes; words read by the AI reader",
        participants_or_bench="Simulated (real recorded inputs)", comparator="Ordinary pen",
        key_quantitative_findings=(f"Words read of 10 (ordinary / Rev J gated / Rev J limit): PD moderate {words('PD/moderate','none')} / {words('PD/moderate','revJ_gated')} / {words('PD/moderate','revJ_oracle')}; "
                                   f"PD severe {words('PD/severe','none')} / {words('PD/severe','revJ_gated')} / {words('PD/severe','revJ_oracle')}; "
                                   f"ET severe {words('ET/severe','none')} / {words('ET/severe','revJ_gated')} / {words('ET/severe','revJ_oracle')}. "
                                   f"Bridge at 1 mm: ordinary pen {bw('syn_syn','none')} (synthetic inputs) -> {bw('real_real','none')} (real inputs); Rev J gated {bw('syn_syn','revJ_gated')} -> {bw('real_real','revJ_gated')}"),
        units_and_conditions="words of 10; SIMULATION", locator="results/realdata/fig_words_read.png, fig_bridge_words.png",
        limitations="Simulation; writer adapted to each pen; no human reader; Rev J is a PROPOSED DESIGN", relevance_to_design="What the pens change for real writing and tremor",
        transferability="low", transferability_reason="Simulation with real inputs, not a measurement", design_implication="See docs/real_data.md",
        retrieved=DATE, search_query="n/a (derived)", stream="EML", lead_verification=""))
    return R


def write(path: Path, out: Dict) -> None:
    R = rows(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in R:
            w.writerow({h: r.get(h, "") for h in HEADER})
