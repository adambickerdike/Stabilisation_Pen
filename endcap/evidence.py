"""Proposed evidence-ledger rows of study K -> results/endcap/evidence_rows.csv (exact 23-column header of docs/evidence.csv).

Id ranges (plan s4): ACT-81..99, AMF-120..134, HAP-80..89, PAT-35..39, PDT-39..42.  Literature rows record only what was
read in the source actually opened (access level stated); 'this study' rows (ACT-84 onwards) are filled from the result
JSON by rows_from_results().  Retrieved 2026-09-28.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List

from . import params as P

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
          "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
          "stream", "lead_verification"]
RET = "2026-09-28"


def _r(**kw) -> Dict:
    row = {k: "" for k in HEADER}
    row.update(kw)
    row.setdefault("retrieved", RET)
    return row


LIT: List[Dict] = [
    # ------------------------------------------------------------------------------------------ HAP: pseudo-force, torque cues
    _r(id="HAP-80", topic="11 pseudo-force: asymmetric-vibration frequency and phase vs the pulling illusion (handheld pinch)",
       citation="Tanabe T, Endo H, Ino S. Effects of Asymmetric Vibration Frequency on Pulling Illusions. Sensors 2020;20(24):7086.",
       year="2020", doi_or_url="10.3390/s20247086 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC7764806/", source_type="journal",
       evidence_class="physical human study", access_level="full text (PMC)",
       task_or_setup="Voice-coil vibrator pinched with thumb, index and middle finger; acceleration x = A1 sin(wt) + A2 sin(2wt + phi0); "
                     "Exp I: 40 and 75 Hz, phi0 -180/-90/0/90 deg, A1 = A2 = 40 m/s2, 1 s stimuli, 2AFC; Exp II: 40/75/110 Hz, "
                     "A 8-40 m/s2, threshold = 50 % point of the psychometric function",
       participants_or_bench="16 + 16 adults (20-56 y)", comparator="phase and frequency conditions",
       key_quantitative_findings="Illusion occurred at phase differences 0 and -180 deg at both 40 and 75 Hz (one-sample t vs 50 %, p < 0.01); "
                                 "no main effect of frequency in Exp I (F(1,15) = 0.003, p = 0.96). Exp II: threshold lowest at 40 Hz, "
                                 "higher at 75 Hz, highest at 110 Hz (F(2,24) = 47.99, p < 0.01; all pairs p < 0.01). Threshold and "
                                 "percent-correct values are shown only as box plots (not tabulated).",
       units_and_conditions="acceleration amplitudes of the vibrator (m/s2); healthy adults; pinch grip; device mass not stated",
       locator="Sections 2-4; Figures 4 and 8", limitations="Threshold numbers not tabulated; device mass not given; healthy adults only",
       relevance_to_design="Sets the waveform (two-harmonic, phase 0 / -180 deg) and the frequency (40 Hz lowest threshold) of a pen cue",
       transferability="medium", transferability_reason="Handheld pinch similar to a pen grip; a 100-120 g pen needs more force for the same acceleration",
       design_implication="If a pseudo-force cue is tried, use a 40 Hz fundamental with a second harmonic at phase 0 or -180 deg; test threshold in the pen (EXP-K05)",
       search_query="WebSearch 'Effects of Asymmetric Vibration Frequency on Pulling Illusions' Sensors 2020 PMC; WebFetch PMC7764806", stream="HAP"),
    _r(id="HAP-81", topic="11 pseudo-force: Traxion (Force Reactor driven asymmetrically) - perceived virtual force magnitude",
       citation="Rekimoto J. Traxion: A Tactile Interaction Device with Virtual Force Sensation. SIGGRAPH 2014 Emerging Technologies (1-page abstract; full paper UIST 2013 pp. 427-432).",
       year="2014 (2013)", doi_or_url="https://history.siggraph.org/wp-content/uploads/2022/03/2014-25-Rekimoto_Traxion.pdf ; UIST paper 10.1145/2501988.2502044",
       source_type="conference", evidence_class="physical human study", access_level="full text (SIGGRAPH 2014 one-page abstract); UIST 2013 paper not opened",
       task_or_setup="ALPS Force Reactor (coil on a spring-supported plate between magnets) driven with a 2 ms current pulse then ~6 ms return",
       participants_or_bench="10 participants", comparator="-",
       key_quantitative_findings="Device about 5.2 g, 7.5 x 35.0 x 5.0 mm; direction change within 50 ms; vibration stops within 50 ms after the signal; "
                                 "user evaluation: strength of the virtual force 29.8 g (s.d. 8.5 g).",
       units_and_conditions="virtual force expressed as an equivalent weight in grams (about 0.29 N, CALC)", locator="Sections 1-2",
       limitations="One-page abstract; method of the magnitude estimate not described here", relevance_to_design="The only perceived-magnitude number found for a pseudo-force (about 0.3 N-equivalent)",
       transferability="medium", transferability_reason="Small handheld object; a pen is heavier and writing is active",
       design_implication="Expect at most a few tenths of a newton of 'felt' pull, with no real net force", search_query="WebSearch Rekimoto Traxion UIST 2013 pdf; WebFetch SIGGRAPH archive PDF (pdftotext)", stream="HAP"),
    _r(id="HAP-82", topic="12 handheld CMG haptics: two parallel double-gimbal CMGs for orientation guidance",
       citation="Walker JM, Culbertson H, Raitor M, Okamura AM. Haptic Orientation Guidance Using Two Parallel Double-Gimbal Control Moment Gyroscopes. IEEE Trans Haptics 2018;11(2):267-278.",
       year="2018", doi_or_url="10.1109/TOH.2017.2713380 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6078422/", source_type="journal",
       evidence_class="physical human study", access_level="full text (PMC author manuscript)",
       task_or_setup="Two counter-rotating flywheels (Lynxmotion 2400 KV outrunner casings) on double gimbals driven in opposite trajectories; fast 150 ms pulse then 550 ms reset",
       participants_or_bench="12 right-handed adults (23-44 y)", comparator="-",
       key_quantitative_findings="Flywheel 13.4 g, outer radius 23 mm, axial inertia 1.98e-6 kg m2, about 20 000 rpm; gimbals -36 to +36 deg; "
                                 "pulse 51.19 N mm (150 ms), reset -14.25 N mm (550 ms); device 197.7 g. Direction identification 99.3 % (286/288), mean response time 4.52 s (SD 1.51 s); "
                                 "closed-loop orientation guidance: all 60 trials completed, median 8.63 s, path 3.31x the direct path; gravity torque at 45 deg about 10 N mm.",
       units_and_conditions="N mm; healthy adults; tethered prototype", locator="Device, model and Studies I-II sections",
       limitations="Heavy (198 g), tethered; healthy users; slow closed-loop guidance", relevance_to_design="The benchmark for real torque cues: 51 mN m pulses are identified almost perfectly",
       transferability="medium", transferability_reason="Same physics; a 45 g end-cap reaches similar pulse torque with a smaller, faster rotor (CALC)",
       design_implication="A CMG end-cap can give clear direction pulses; guidance is slow (seconds), so it is a cue, not a writing drive",
       search_query="WebSearch Walker Culbertson Raitor Okamura double-gimbal CMG; Semantic Scholar API (open-access PMC link); WebFetch PMC6078422", stream="HAP"),
    _r(id="HAP-83", topic="12 handheld CMG haptics: iTorqU 2.0 ungrounded torque feedback (two-axis gimballed flywheel)",
       citation="Winfree KN, Gewirtz J, Mather T, Fiene J, Kuchenbecker KJ. A High Fidelity Ungrounded Torque Feedback Device: The iTorqU 2.0. Proc. World Haptics 2009, pp. 261-266.",
       year="2009", doi_or_url="10.1109/WHC.2009.4810866 ; https://repository.upenn.edu/bitstreams/a869a3ee-95f0-4591-baeb-b80458beb3c0/download",
       source_type="conference", evidence_class="physical bench experiment", access_level="full text",
       task_or_setup="Steel ring flywheel in a two-axis capstan-driven gimbal on a tennis-racket handle; torques measured on an AMTI 6-DOF plate",
       participants_or_bench="Bench (plate); informal demo of iTorqU 1.0 to about 50 people", comparator="iTorqU 1.0",
       key_quantitative_findings="Flywheel 416 stainless, 138 g, r 86-99 mm, 218 000 g mm2; Faulhaber 2607 T006 SR pancake motor, 6600 rpm no-load at 6 V, 16.1 g; gimbal "
                                 "motors Maxon 110045 (21 g, stall 4.78 mN m at 12 V) via 10.2:1 capstans, 540 deg range; gimballed gyroscope 486 g; "
                                 "maximum torque per gimbal axis nearly 1.2 N m. iTorqU 1.0 weighed 833 g; the earlier Gyro Moment Display (+/-50 deg) "
                                 "needed time to re-centre, limiting bandwidth; unwanted gyroscopic moments when the pose changes.",
       units_and_conditions="bench; torques from the force plate", locator="Sections 2-6, Figure 8",
       limitations="No user study in this paper; heavy", relevance_to_design="Scaling anchor: 1.2 N m needs a 0.15 N m s rotor and a 486 g device",
       transferability="low", transferability_reason="Hand-held racket scale, 10x the pen's mass",
       design_implication="Gimbal saturation and re-centring are the CMG's core limit; a pen-scale CMG has about 1/60 of this momentum (CALC)",
       search_query="WebSearch Winfree iTorqU; Semantic Scholar API (open-access UPenn copy); curl + pdftotext", stream="HAP"),
    _r(id="HAP-84", topic="13 guidance by feel: holdable skin-stretch device (4-DOF cues) and response delays",
       citation="Walker JM, Zemiti N, Poignet P, Okamura AM. Holdable Haptic Device for 4-DOF Motion Guidance. IEEE World Haptics Conference 2019 (arXiv:1903.03150).",
       year="2019", doi_or_url="https://arxiv.org/abs/1903.03150 ; https://hal-lirmm.ccsd.cnrs.fr/lirmm-02093717", source_type="conference",
       evidence_class="physical human study", access_level="full text (arXiv)",
       task_or_setup="Two 2-DOF pantographs displace thumb and index pads 3 mm over 0.2 s, pause 0.6 s, return over 0.5 s; eight cue directions",
       participants_or_bench="20 right-handed adults (22-42 y)", comparator="before vs after training",
       key_quantitative_findings="Eight cue directions discriminated > 93.3 % of the time; users moved in the cued direction even before training; "
                                 "delay to motion onset bimodal: fast responders 0.33 s, slow responders 1.56 s; 13 fast and 7 slow; rotation cues 0.119 s slower. "
                                 "Related work noted: asymmetric-vibration actuators must be attached very precisely; gyroscopic or vibration pulse patterns "
                                 "'can be unpleasant in extended use'.",
       units_and_conditions="healthy adults, hand hidden, headphones", locator="Sections I-V, Table I",
       limitations="Healthy adults; not writing", relevance_to_design="Response delay (>= 0.33 s) sets what any cue can steer; skin stretch is a strong alternative channel",
       transferability="medium", transferability_reason="Held device, similar grip scale; not a pen",
       design_implication="Cues cannot steer 0.1-0.15 s strokes; skin stretch in the grip sleeve is worth a separate study",
       search_query="WebSearch Holdable Haptic Device 4-DOF Walker; curl arXiv PDF + pdftotext", stream="HAP"),
    _r(id="HAP-85", topic="11 pseudo-force: asymmetric-vibration cue during wrist motion (velocity, agency)",
       citation="Tanabe T, Kaneko H. Illusory Directional Sensation Induced by Asymmetric Vibrations Influences Sense of Agency and Velocity in Wrist Motions. IEEE Trans Neural Syst Rehabil Eng 2024;32:1749-1756.",
       year="2024", doi_or_url="10.1109/TNSRE.2024.3393434 ; https://ieeexplore.ieee.org/document/10508247/", source_type="journal",
       evidence_class="physical human study", access_level="full text (IEEE open access PDF)",
       task_or_setup="67.4 g handle with two Foster 639897 voice coils in parallel (pseudo-torque); 75 Hz + 150 Hz, A1 = A2 = 60 m/s2, phase +/-90 deg; "
                     "reciprocal wrist flexion-extension to targets (0-60 deg); congruent, incongruent, symmetric vibration, null; blocks with 2 min breaks 'considering fatigue and adaptation'",
       participants_or_bench="20 healthy adults (20-47 y)", comparator="null and symmetric vibration",
       key_quantitative_findings="Direction discrimination before the task: median 96.86 % (IQR 7.5 %). Peak wrist angular velocity higher with congruent cues than incongruent "
                                 "(p < 0.001, d = 0.26) and null (p < 0.01, d = 0.22); congruent vs symmetric vibration p = 0.06 (d = 0.16). Sense of agency lower with congruent cues "
                                 "(chi2(3) = 47.09, p < 0.001). Velocity-iEMG correlation weakly positive (0.38 +/- 0.04 SE in extension): participants likely sped up themselves.",
       units_and_conditions="healthy adults; wrist reaching; accelerations of the vibrator", locator="Sections II-IV, Figures 3-5",
       limitations="Healthy young adults; wrist only; small effect sizes", relevance_to_design="The pull changes movement only a little (d about 0.2) and not by force",
       transferability="medium", transferability_reason="Held device and voluntary motion like writing; 60 m/s2 on 67 g is far above what a 120 g pen reaches at 1 W (CALC)",
       design_implication="Treat pseudo-force as a weak suggestion; do not expect letter-level steering from it",
       search_query="WebSearch Tanabe Kaneko TNSRE 2024; curl IEEE stampPDF (open access) + pdftotext; Europe PMC abstract", stream="HAP"),
    _r(id="HAP-86", topic="11 pseudo-force: DC-motor rotor acceleration as a vibrotactile and pseudo-torque actuator",
       citation="Yem V, Okazaki R, Kajimoto H. Vibrotactile and Pseudo Force Presentation using Motor Rotational Acceleration. IEEE Haptics Symposium 2016, pp. 47-51.",
       year="2016", doi_or_url="https://kaji-lab.jp/ja/index.php?plugin=attach&pcmd=open&file=HS2016_Yem.pdf&refer=publications", source_type="conference",
       evidence_class="physical human study", access_level="full text",
       task_or_setup="DC motors (STL HS-V1S, HS-E1S) vs Haptuator TL002-14-A and Alps Force Reactor on a fingertip glove; sawtooth voltage 10-80 Hz, 1-2 V for pseudo-torque",
       participants_or_bench="Exp 1: author only; Exp 2: 8 volunteers (21-32 y)", comparator="Haptuator, Force Reactor",
       key_quantitative_findings="Sizes/weights: Haptuator 14x14x29 mm 15 g; Force Reactor 5x8x35 mm 5 g; DC motor 1 12.4x12.4x31 mm 18 g; DC motor 2 6x8x20 mm 4 g. "
                                 "First response peaks 4 ms (Haptuator), 5 ms (Force Reactor), 3 ms (DC motors). Pseudo-torque direction about 90 % correct at 10 Hz sawtooth, "
                                 "falling at higher frequencies; 1 to 2 V did not change the correct rate. Motor case 47 degC after 1 h at nominal current (Maxon 118386).",
       units_and_conditions="fingertip-mounted actuators; 1 W for the frequency sweep", locator="Sections II-IV, Table I, Figure 10",
       limitations="Small sample; 'unknown' answer option; fingertip, not a held pen", relevance_to_design="A spinning or reaction rotor can also give pseudo-torque cues; actuator masses for the cue",
       transferability="medium", transferability_reason="Same actuator classes that fit a pen end-cap",
       design_implication="A CMG or wheel motor can double as a cue actuator; a 5 g Force Reactor-class part fits the end-cap",
       search_query="WebSearch Haptuator Mark II datasheet (found the Kajimoto-lab PDF); curl + pdftotext", stream="HAP"),
    _r(id="HAP-87", topic="12 handheld momentum haptics: reaction-wheel torque feedback device (Bi-Hap)",
       citation="Wang H, Guo H, Ba H, Li Z, Tao L. Bi-directional Momentum-based Haptic Feedback and Control System for In-Hand Dexterous Telemanipulation. arXiv:2409.20527 (v2, 2025).",
       year="2024 (2025)", doi_or_url="https://arxiv.org/abs/2409.20527", source_type="preprint", evidence_class="physical bench experiment",
       access_level="full text (arXiv, short paper)",
       task_or_setup="Flat gimbal BLDC with a 55 mm flywheel disk in a 60 mm cube; velocity-controlled wheel; torque sensor bench; tele-played game",
       participants_or_bench="Bench + 5 participants", comparator="-",
       key_quantitative_findings="Flywheel inertia 4.8e-5 kg m2 ('weight (128 g)' as printed); whole device 320 g; sinusoidal torque tracking 15 and 30 mN m at 8 and 16 rad/s: "
                                 "RMSE 2.1-9.5 mN m, latency 12.6-25.3 ms; steps 10 and 20 mN m: overshoot 27.4 % and 10.2 %, peak time 0.09 and 0.18 s. "
                                 "When the wheel saturates, the torque command is turned into vibration.",
       units_and_conditions="bench torque sensor, 500 Hz", locator="Sections II-III, Tables I-II",
       limitations="Preprint; tiny user sample", relevance_to_design="Reaction wheels reach tens of mN m only at 300 g scale; momentum saturation handled by switching to vibration",
       transferability="low", transferability_reason="Palm-sized, 7x the end-cap mass", design_implication="A pen-scale wheel gives about 1 mN m continuous (MFR AMF-120..123, CALC): not useful",
       search_query="WebSearch patent handheld haptic CMG scissored (result list); curl arXiv PDF + pdftotext", stream="HAP"),
    _r(id="HAP-88", topic="11 pseudo-force: motion-coupled asymmetric vibration reduces the felt buzz",
       citation="Sabnis N, Roche M, Wittchen D, Degraen D, Strohmeier P. Motion-Coupled Asymmetric Vibration for Pseudo Force Rendering in Virtual Reality. CHI 2025, paper 1134.",
       year="2025", doi_or_url="10.1145/3706598.3713358", source_type="conference", evidence_class="physical human study",
       access_level="abstract only (Semantic Scholar API; ACM page returned 403)",
       task_or_setup="Asymmetric vibration coupled to the user's own motion vs continuous asymmetric vibration", participants_or_bench="12 participants",
       comparator="continuous asymmetric vibration",
       key_quantitative_findings="Motion coupling attenuated the experience of vibration (equivalent to about a 30 % reduction in vibration amplitude) while preserving the "
                                 "experience of force; preferred for arrow shooting and weight lifting in VR.",
       units_and_conditions="VR tasks", locator="Abstract", limitations="Abstract only", relevance_to_design="Couple any pen cue to the writer's motion to reduce buzz",
       transferability="medium", transferability_reason="Same actuator principle; different task", design_implication="If cues are used, gate them with the pen's own motion",
       search_query="WebSearch asymmetric vibration pen stylus pseudo force; Semantic Scholar API", stream="HAP"),
    _r(id="HAP-89", topic="11 pseudo-force: asymmetry of the waveform vs perceived traction",
       citation="Asakura T, Hirasawa H. Case study: Effect of asymmetry of vibration on the perceived illusion force. Noise Control Eng J 2022;70(3):264-269.",
       year="2022", doi_or_url="10.3397/1/377020", source_type="journal", evidence_class="physical human study", access_level="abstract only",
       task_or_setup="Sawtooth waveforms with asymmetry set by the Fourier summation order n", participants_or_bench="not stated in the abstract", comparator="summation orders",
       key_quantitative_findings="Induced traction increased with the asymmetry of the sawtooth up to summation order 3; no further increase above order 4.",
       units_and_conditions="-", locator="Abstract", limitations="Abstract only; sample not stated", relevance_to_design="Two to three harmonics suffice for the cue waveform",
       transferability="medium", transferability_reason="Waveform result, device-independent in principle", design_implication="Drive the cue with 2-3 harmonics; more adds nothing",
       search_query="WebSearch asymmetric vibration adaptation; Semantic Scholar API abstract", stream="HAP"),
    # ------------------------------------------------------------------------------------------ PDT: Parkinson's and tremor
    _r(id="PDT-39", topic="Pulling illusion in neurological disorders incl. Parkinson's with tremor (preprint)",
       citation="Tanabe T, Yamamoto S, Yamada T, Ishii D, Kohno Y. Pulling Illusion in Individuals with Neurological Disorders. arXiv:2609.10566 (submitted to IEEE), 1 Sep 2026.",
       year="2026", doi_or_url="https://arxiv.org/abs/2609.10566", source_type="preprint", evidence_class="physical human study", access_level="full text (preprint)",
       task_or_setup="Handheld two-voice-coil device (Foster 639897; 53 x 28 x 27 mm, 67.4 g) suspended by a 14.0 gf constant-load spring; 75 + 150 Hz, 40 m/s2, 1 s; "
                     "40-trial 2AFC CW/CCW pseudo-torque; fingertip vibration thresholds at 75 Hz",
       participants_or_bench="25 patients (42-83 y): 7 carpal tunnel, 1 neuropathy, 1 SAH, 5 ICH, 2 cerebral infarction, 1 MSA, 2 SCD, 5 PD (2 with tremor), 1 muscular dystrophy",
       comparator="affected vs unaffected side; vibration threshold",
       key_quantitative_findings="Directional discrimination bimodal (near 100 % or near chance). GLMM: motor-related signs (hemiplegia or tremor) log-odds -1.95 "
                                 "(95 % CI -2.48 to -1.62); vibration threshold 0.08 (-0.28 to 0.64, not robust); age -1.13 (-2.11 to -0.45). Hemiplegia: affected side "
                                 "near 50 %, unaffected near 100 % (p = 0.03) although stimuli were 10-100x above detection thresholds. One PD participant with tremor "
                                 "was excluded for 22.5 % correct on one side.",
       units_and_conditions="percent correct of 40 trials per side", locator="Table I, Sections II-IV, Figures 3-5",
       limitations="Preprint; heterogeneous small cohort; only 2 PD with tremor", relevance_to_design="Pseudo-force cues may fail precisely in the pen's users (tremor)",
       transferability="high", transferability_reason="Patients with tremor, handheld device",
       design_implication="Do not rely on pseudo-force for ET/PD users without testing them (EXP-K05); prefer real torque pulses or skin stretch",
       search_query="WebSearch Culbertson asymmetric vibrations (result list); WebFetch arXiv abstract and PDF (read as images)", stream="PDT"),
    _r(id="PDT-40", topic="PD proprioception and kinaesthesia deficits (review)",
       citation="Konczak J, Corcos DM, Horak F, Poizner H, Shapiro M, Tuite P, Volkmann J, Maschke M. Proprioception and motor control in Parkinson's disease. J Mot Behav 2009;41(6):543-552.",
       year="2009", doi_or_url="10.3200/35-09-002 ; PMID 19592360", source_type="review", evidence_class="review", access_level="abstract only (Europe PMC)",
       task_or_setup="Review of kinaesthetic perception, proprioceptive-motor integration, balance and medication effects in PD", participants_or_bench="n/a", comparator="-",
       key_quantitative_findings="Proprioceptive deficits 'profoundly degrade motor performance' in PD; the authors conclude that a failure to evaluate and map proprioceptive "
                                 "information onto motor commands is integral to PD motor symptoms (abstract; no numbers).",
       units_and_conditions="-", locator="Abstract", limitations="Abstract only", relevance_to_design="Force and torque cues rely on kinaesthesia, which PD may degrade",
       transferability="medium", transferability_reason="Population-level; task not writing", design_implication="Test cue perception in PD specifically before relying on it",
       search_query="WebSearch Konczak proprioception Parkinson's J Motor Behavior 2009; Europe PMC REST abstract", stream="PDT"),
    _r(id="PDT-41", topic="PD wrist position sense and proprioceptive training (thresholds, transfer to handwriting)",
       citation="Elangovan N, Tuite PJ, Konczak J. Somatosensory Training Improves Proprioception and Untrained Motor Function in Parkinson's Disease. Front Neurol 2018;9:1053.",
       year="2018", doi_or_url="10.3389/fneur.2018.01053", source_type="journal", evidence_class="physical human study", access_level="full text",
       task_or_setup="Robot-aided wrist proprioceptive training; wrist position sense discrimination threshold (JND); untrained pointing and handwriting tracing",
       participants_or_bench="13 PD (61.7 +/- 6.8 y, mild-moderate), 13 healthy elderly (67.0 +/- 6.5 y)", comparator="healthy controls",
       key_quantitative_findings="Baseline wrist JND: PD 1.58 +/- 0.43 deg, controls 1.80 +/- 0.65 deg. After training PD 1.14 +/- 0.30 deg (-27.7 %, d = 1.24); controls -28.3 %. "
                                 "Pointing error fell 25.3 % in 10 of 13 PD; handwriting tracing/tracking did not improve significantly.",
       units_and_conditions="degrees of wrist position sense", locator="Results", limitations="Small sample; mild-moderate PD",
       relevance_to_design="In this mild PD group position sense was not worse than controls; training did not transfer to handwriting",
       transferability="medium", transferability_reason="Wrist proprioception, not pen guidance", design_implication="Do not assume cue perception is lost in mild PD; measure it (EXP-K05)",
       search_query="WebSearch Konczak proprioception (result list); WebFetch Frontiers full text", stream="PDT"),
    _r(id="PDT-42", topic="Low-cost gyroscopic + vibration glove in one PD patient (reported reductions inconsistent with its own table)",
       citation="Ahmad AN, Khokhar AS, Shajani MB. Innovative and Affordable Anti-Tremor Gyroscopic Glove Prototype for Parkinson's Patients. Int J Comput Trends Technol 2025;73(10):1-9.",
       year="2025", doi_or_url="10.14445/22312803/IJCTT-V73I10P101 ; https://ijcttjournal.org/2025/Volume-73/Issue-10/IJCTT-V73I10P101.pdf", source_type="journal",
       evidence_class="physical human study", access_level="full text",
       task_or_setup="Dorsal gyroscope (2200 rpm BLDC with a machined metal mass, PWM speed control) plus 12 finger vibration motors driven in antiphase to finger gyro signals; baseline (off) vs active",
       participants_or_bench="1 man with PD (age given as 76 and as 70 in different sections)", comparator="device off",
       key_quantitative_findings="Reported reductions: kinetic 71.6 %, postural 82.4 %, isometric 62.1 %. Its Table 1 RMS angular velocities (12.4 -> 6.5, 15.8 -> 6.7, 10.2 -> 5.8 deg/s) "
                                 "imply 48 %, 58 % and 43 % by its own formula (CALC by this ledger).",
       units_and_conditions="RMS angular velocity (deg/s), 100 Hz", locator="Abstract, Table 1, Section 3", limitations="n = 1, no blinding, internal inconsistencies, student prototype",
       relevance_to_design="Shows how weak the public evidence for small gyroscopic devices is", transferability="low", transferability_reason="Single case, glove",
       design_implication="Do not cite as efficacy; gyroscopic claims need controlled tests", search_query="WebSearch gyroscope tremor 71.6% 82.4%; WebFetch PDF + pdftotext", stream="PDT"),
    # ------------------------------------------------------------------------------------------ ACT: gyroscopic tremor devices
    _r(id="ACT-81", topic="Review of peripheral and mechanical tremor devices incl. GyroGlove rotor speed and the evidence gap",
       citation="Adabi K, Ondo WG. Shaking Up Essential Tremor: Peripheral Devices and Mechanical Strategies to Reduce Tremor. Tremor Other Hyperkinet Mov 2024;14(1):55.",
       year="2024", doi_or_url="10.5334/tohm.930", source_type="review", evidence_class="review", access_level="full text",
       task_or_setup="Narrative review (PNS, orthoses, gyroscopes, vibration, adaptive utensils), with manufacturer information", participants_or_bench="n/a", comparator="-",
       key_quantitative_findings="GyroGlove: gyroscope spinning 'up to 10,000 rev/minute'; best damps pronation-supination; controlled trial under way; bulky. WOTAS exoskeleton: "
                                 "average 40 % reduction in tremor power (up to 80 %, 2-8 Hz). Tremelo 85-90 % claim not supported by published data. No published clinical "
                                 "trial data on weighted spoons for ET; most devices have limited or no published trial data.",
       units_and_conditions="-", locator="Sections 2.2-5", limitations="Narrative review; relies partly on manufacturers", relevance_to_design="State of evidence for gyroscopic and inertial wearables",
       transferability="medium", transferability_reason="Wearables and utensils, not pens", design_implication="Treat every inertial benefit as unproven until measured on writers",
       search_query="WebSearch gyroscopic tremor suppression glove percent; WebFetch TOHM PDF + pdftotext", stream="ACT"),
    _r(id="ACT-82", topic="Gyroscopic tremor suppression: which rotor parameters matter (1-DOF wrist model)",
       citation="Allen BC. Effect of Gyroscope Parameters on Gyroscopic Tremor Suppression in a Single Degree of Freedom. MS thesis, Brigham Young University, 2018 (also J Mech Med Biol 2019).",
       year="2018", doi_or_url="https://scholarsarchive.byu.edu/etd/6782 ; 10.1142/S0219519419500246", source_type="thesis", evidence_class="numerical simulation",
       access_level="abstract only (full text returned HTTP 403)", task_or_setup="Linearised wrist 1-DOF + back-of-hand gyroscope; frequency response to a tremorogenic torque",
       participants_or_bench="none (simulation)", comparator="parameter sweeps",
       key_quantitative_findings="Flywheel inertia and spin speed should be as high as design constraints allow; distance from the wrist axis, precession stiffness and precession damping as low as possible (abstract; no numbers).",
       units_and_conditions="-", locator="Abstract", limitations="Abstract only; model study", relevance_to_design="Confirms H (inertia x speed) is the lever; a pen's rotor is small",
       transferability="low", transferability_reason="Wrist, not pen grip", design_implication="Gyroscopic stiffening scales with H w / K_rot; the pen's H is too small (CALC)",
       search_query="WebSearch Allen Charles gyroscopic tremor suppression BYU; WebFetch ScholarsArchive record", stream="ACT"),
    _r(id="ACT-83", topic="Wearable gyroscopic mechanism against axial hand tremor (simulation + prototype)",
       citation="Phan Van H, Ngo HQT. Developing an Assisting Device to Reduce the Vibration on the Hands of Elders. Appl Sci 2021;11(11):5026.",
       year="2021", doi_or_url="10.3390/app11115026", source_type="journal", evidence_class="physical bench experiment",
       access_level="abstract only (Crossref; MDPI returned HTTP 403)", task_or_setup="Gyroscopic wearable; feedback-linearised control; MATLAB model; hardware tests gyro vs non-gyro",
       participants_or_bench="not stated in the abstract", comparator="non-gyro case",
       key_quantitative_findings="System response adapted well to axial tremor at 2-6 Hz; 'effectiveness of up to 92.6 %', considerably better than without the gyro (abstract).",
       units_and_conditions="-", locator="Abstract", limitations="Abstract only; metric not defined in the abstract", relevance_to_design="Upper-end claim for wearable gyroscopes",
       transferability="low", transferability_reason="Wearable, larger rotor, undefined metric", design_implication="Not transferable to a pen end-cap without the device data",
       search_query="WebSearch Phan Van Ngo 2021 gyroscope glove 92.6%; Crossref API abstract", stream="ACT"),
    # ------------------------------------------------------------------------------------------ AMF: parts
    _r(id="AMF-120", topic="8 mm BLDC for a CMG spin rotor (Faulhaber 0824 K 006 B)",
       citation="FAULHABER. Brushless DC-Servomotors 2 Pole Technology, Series 0824 ... B (EN_0824_B_FMM).", year="n.d.",
       doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_0824_B_FMM.pdf", source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
       task_or_setup="Values at 22 degC and nominal voltage", participants_or_bench="-", comparator="AMF-78 (0620 B)",
       key_quantitative_findings="006 B: 6 V; 2.91 ohm; eta max 70 %; n0 35 100 rpm; I0 0.055 A; stall 3.28 mN m; C0 0.021 mN m; Cv 1.89e-6 mN m/rpm; kM 1.6 mN m/A; J 0.0285 g cm2; "
                                 "rated 0.89 mN m (0.66 A); speed up to 90 000 rpm; preloaded ball bearings; radial load 1.5 N at 10 000 rpm; mass 5.2 g; Rth 11.2/55.2 K/W.",
       units_and_conditions="22 degC, nominal voltage", locator="Datasheet table", limitations="Friction at speed extrapolated with C0 + Cv n",
       relevance_to_design="Spin motor of the optimised CMG end-cap", transferability="high", transferability_reason="Catalogue part",
       design_implication="Its shaft bearings cannot carry the gyroscopic moment (tens of mN m): the rotor needs its own bearings (CALC)",
       search_query="curl faulhaber.com EN_0824_B_FMM.pdf + pdftotext", stream="AMF"),
    _r(id="AMF-121", topic="12 mm BLDC (Faulhaber 1226 S 006 B) for a spin rotor or wheel",
       citation="FAULHABER. Brushless DC-Servomotors 2 Pole Technology, Series 1226 ... B (EN_1226_B_FMM).", year="n.d.",
       doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_1226_B_FMM.pdf", source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
       task_or_setup="Values at 22 degC and nominal voltage", participants_or_bench="-", comparator="AMF-120",
       key_quantitative_findings="006 B: 6 V; 2.2 ohm; n0 21 000 rpm; I0 0.07 A; stall 7.24 mN m; C0 0.073 mN m; Cv 5.3e-6 mN m/rpm; kM 2.68 mN m/A; J 0.15 g cm2; rated 2.13 mN m; "
                                 "up to 79 000 rpm; radial 5 N at 10 000 rpm; mass 13 g.",
       units_and_conditions="22 degC", locator="Datasheet table", limitations="-", relevance_to_design="Heavier spin/wheel motor option", transferability="high",
       transferability_reason="Catalogue part", design_implication="13 g each is too heavy for two in a 45 g end-cap", search_query="curl faulhaber.com EN_1226_B_FMM.pdf", stream="AMF"),
    _r(id="AMF-122", topic="26 mm flat BLDC (Faulhaber 2610 T 006 B) as a reaction-wheel motor",
       citation="FAULHABER. Brushless DC-Flat Motors 4 Pole Technology, Series 2610 ... B (EN_2610_B_DFF).", year="n.d.",
       doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_2610_B_DFF.pdf", source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
       task_or_setup="Values at 22 degC", participants_or_bench="-", comparator="AMF-123",
       key_quantitative_findings="006 B: 6 V; 6.97 ohm; n0 6400 rpm; I0 0.01 A; stall 7.543 mN m; C0 0.035 mN m; Cv 8.85e-6 mN m/rpm; kM 8.8 mN m/A; J 7.9 g cm2; rated 2.87 mN m; "
                                 "up to 40 000 rpm; plastic housing; mass 20.1 g; winding max 80 degC.",
       units_and_conditions="22 degC", locator="Datasheet table", limitations="26 mm: exactly the end-cap diameter", relevance_to_design="Reaction-wheel torque ceiling",
       transferability="high", transferability_reason="Catalogue part", design_implication="A wheel gives <= 2.9 mN m continuous for 20 g: far below a CMG (CALC)",
       search_query="curl faulhaber.com EN_2610_B_DFF.pdf", stream="AMF"),
    _r(id="AMF-123", topic="22 mm external-rotor flat BLDC (Faulhaber 2214 S BXT H) as a reaction-wheel motor",
       citation="FAULHABER. Brushless DC-Flat Motors, External rotor technology, with housing, Series 2214 ... BXT H (EN_2214_BXTH_DFF), edition 2025.", year="2025",
       doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_2214_BXTH_DFF.pdf", source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
       task_or_setup="Values at 22 degC", participants_or_bench="-", comparator="AMF-122",
       key_quantitative_findings="006 BXT H: 6 V; 2.42 ohm; n0 5760 rpm; I0 0.061 A; starting torque 23.5 mN m; kM 9.58 mN m/A; J 3.3 g cm2; rated 9.4 mN m (1.16 A); up to 10 000 rpm; mass 28.9 g.",
       units_and_conditions="22 degC", locator="Datasheet table", limitations="No friction constants published", relevance_to_design="Best torque per motor at this size",
       transferability="high", transferability_reason="Catalogue part", design_implication="Continuous 9.4 mN m costs 1.16 A (3.3 W of copper at 2.42 ohm): far over the pen's power (CALC)",
       search_query="WebSearch Faulhaber 1202 BH datasheet (result list); curl faulhaber.com EN_2214_BXTH_DFF.pdf", stream="AMF"),
    _r(id="AMF-124", topic="Voice-coil vibrotactile transducer for pseudo-force cues (Tactile Labs Haptuator Redesign TL002-14R)",
       citation="Tactile Labs. Haptuator Redesign High-Bandwidth Vibrotactile Transducer, Product Specification R1.0, 3 May 2014.", year="2014",
       doi_or_url="https://tactilelabs.com/wp-content/uploads/2023/11/HaptuatorRedesign_datasheet.pdf", source_type="datasheet", evidence_class="manufacturer statement",
       access_level="full text", task_or_setup="Manufacturer specification", participants_or_bench="-", comparator="original Haptuator",
       key_quantitative_findings="16 x 29 mm; 11 g; 2.5 G (24.5 m/s2) at 1 V, 150 Hz with a 9 g extra load (20 g total); rated band 50-500 Hz; 6.0 ohm; max 3.0 V, 0.5 A; "
                                 "not recommended below 50 Hz; above 500 Hz output becomes audible.",
       units_and_conditions="acceleration of a 20 g load", locator="Specification table and notes", limitations="Acceleration quoted for a 20 g load, not a 120 g pen",
       relevance_to_design="The actuator class used in pseudo-force studies (Amemiya, Culbertson: 40 Hz)", transferability="high", transferability_reason="Fits the end-cap",
       design_implication="On a 120 g pen its force gives only a few m/s2 at 40 Hz (CALC); a stronger coil or the reaction mass is needed", search_query="WebSearch Haptuator Mark II datasheet; curl tactilelabs PDF", stream="AMF"),
    _r(id="AMF-125", topic="Tungsten heavy alloys incl. non-magnetic grades (Plansee DENSIMET / INERMET)",
       citation="Plansee SE. W-MMC Tungsten-based metal matrix composites (brochure, 09-2021).", year="2021",
       doi_or_url="https://cdn.plansee-group.com/is/content/planseemedia/plansee/downloads/werkstoffe/W_MMC_Broschuere_Plansee_09-2021.pdf", source_type="manufacturer",
       evidence_class="manufacturer statement", access_level="full text (mechanical-strength charts read as images; values not extracted)",
       task_or_setup="Material ranges and typical properties", participants_or_bench="-", comparator="AMF-49 (Elmet ASTM B777)",
       key_quantitative_findings="DENSIMET (W-Ni-Fe, weakly ferromagnetic) D170-D188: 17.0-18.8 g/cm3 (90-98.5 % W, ASTM B777 classes 1-4); INERMET (W-Ni-Cu, paramagnetic) IT170-IT180: "
                                 "17.0-18.0 g/cm3; Young's modulus 330-385 GPa; comply with AMS-T-21014, AMS 7725, ASTM B777; better machinability than pure tungsten.",
       units_and_conditions="typical values", locator="pp. 5, 16-17", limitations="Strength charts not tabulated", relevance_to_design="Rotor and slug material; a paramagnetic grade avoids magnet and Hall interference",
       transferability="high", transferability_reason="Supplier data", design_implication="Use INERMET-class rotors near the coils and Hall sensors", search_query="WebSearch Plansee Densimet datasheet; curl brochure + pdftotext", stream="AMF"),
    _r(id="AMF-126", topic="Miniature deep-groove ball bearings for pen-scale rotors (SKF 618/4, 618/8)",
       citation="SKF 618/4 and 618/8 product data as listed by Quality Bearings Online (retailer pages).", year="n.d.",
       doi_or_url="https://www.qualitybearingsonline.com/618-4-skf-miniature-deep-groove-4x9x2-5mm/ ; https://www.qualitybearingsonline.com/618-8-skf-miniature-deep-groove-8x16x4mm/",
       source_type="website", evidence_class="manufacturer statement", access_level="secondary account", task_or_setup="Retailer product listings of SKF data",
       participants_or_bench="-", comparator="-",
       key_quantitative_findings="618/4: 4 x 9 x 2.5 mm, C 0.423 kN, C0 0.116 kN, reference speed 14 000 r/min (as listed; likely a transcription error), limiting speed 85 000 r/min, 0.7 g. "
                                 "618/8: 8 x 16 x 4 mm, C 0.819 kN, C0 0.3 kN, reference 90 000 r/min, limiting 56 000 r/min, 3 g.",
       units_and_conditions="SKF catalogue conventions", locator="Product pages", limitations="Secondary listing; SKF product pages did not render", relevance_to_design="Speed cap of the rotors",
       transferability="high", transferability_reason="Catalogue parts", design_implication="Cap rotor speed at 40 000 rpm (about half the 618/4 limiting speed)", search_query="WebSearch SKF 618/3 limiting speed; WebFetch retailer pages", stream="AMF"),
    _r(id="AMF-127", topic="Micro brushless motor for ducted-fan thrust (BETAFPV 0802SE) - mass only",
       citation="BETAFPV. 0802SE Brushless Motors product page.", year="n.d.", doi_or_url="https://betafpv.com/products/0802se-22000kv-brushless-motors",
       source_type="manufacturer", evidence_class="manufacturer statement", access_level="full text (product page; no thrust data published)",
       task_or_setup="Product specification", participants_or_bench="-", comparator="AMF-79 (1103 class)",
       key_quantitative_findings="1.83 g (19 500 KV) / 1.80 g (23 000 KV); 10.5 x 10.5 x 13.6 mm; 1S; 1 mm shaft; no thrust, current or efficiency data on the page.",
       units_and_conditions="-", locator="Specifications", limitations="No thrust data; the propeller case uses momentum theory with ASSUMPTION efficiencies",
       relevance_to_design="Mass of a propeller option (limiting case)", transferability="medium", transferability_reason="Drone part; noise and airflow unsuited to a pen",
       design_implication="Propeller thrust per watt is computed, not measured (CALC)", search_query="WebSearch BETAFPV 0802SE thrust test; WebFetch product page", stream="AMF"),
    # ------------------------------------------------------------------------------------------ PAT
    _r(id="PAT-35", topic="Pseudo force sense generation with several asymmetric vibrators on a rigid base (NTT)",
       citation="Nippon Telegraph and Telephone Corp. (inventors Shoji T, Ochiai K, Gomi H). Pseudo force sense generation apparatus. US 10,864,552 B2, granted 2020-12-15; priority 2015-12-28.",
       year="2020", doi_or_url="https://patents.google.com/patent/US10864552B2/en", source_type="patent", evidence_class="patent disclosure", access_level="full text",
       task_or_setup="Two or more vibrators fixed to a rigid base producing translational or rotational pseudo-force; motion centred near the centre of gravity",
       participants_or_bench="n/a", comparator="",
       key_quantitative_findings="Claim 1 (paraphrase): base + >= 2 vibrators at fixed positions, each giving tactile stimuli along distinct linear directions, coordinated to give a "
                                 "rotation-like sensation about near the centre of gravity. Description: 40 Hz, t1:t2 = 18 ms : 7 ms examples; rotational presentation needs about 1/10 of the power "
                                 "of translational. Status: active, expires 2037-10-20 (as displayed).",
       units_and_conditions="n/a", locator="Claim 1, description (Google Patents)", limitations="Claims read from the Google Patents display; no legal assessment",
       relevance_to_design="Freedom-to-operate item if the pen uses multi-vibrator pseudo-force", transferability="medium", transferability_reason="Handheld devices in general",
       design_implication="Attorney review before any pseudo-force product feature", search_query="WebSearch asymmetric vibration pen stylus pseudo force (patent hits); WebFetch Google Patents", stream="PAT"),
    _r(id="PAT-36", topic="Haptic stylus with a stick-slip actuated grip covering (Tampere University / Fukoku)",
       citation="Tampereen Yliopisto; Fukoku Co Ltd (inventors Evreinov G, Farooq A, Raisamo R, et al.). Haptic stylus. US 10,133,370 B2, granted 2018-11-20; priority 2015-03-27.",
       year="2018", doi_or_url="https://patents.google.com/patent/US10133370B2/en", source_type="patent", evidence_class="patent disclosure", access_level="full text",
       task_or_setup="Stylus housing, a longitudinally movable covering gripped by the fingers, and an actuator creating stick-slip friction between the covering and the fingers",
       participants_or_bench="n/a", comparator="",
       key_quantitative_findings="Claim 1 (paraphrase): stylus housing, tip, covering movable along the stylus while gripped, first actuator generating stick-slip friction; options include piezo, voice-coil, "
                                 "dielectric elastomer, a spherical or stick-slip motor in the tip. Status: expired - fee related (as displayed).",
       units_and_conditions="n/a", locator="Claim 1 (Google Patents)", limitations="No legal assessment", relevance_to_design="Prior art for skin-stretch guidance in the grip (free to use if expired)",
       transferability="medium", transferability_reason="Stylus embodiment", design_implication="Grip-sleeve skin stretch is open prior art worth a separate study", search_query="WebSearch asymmetric vibration pen stylus (patent hits); WebFetch Google Patents", stream="PAT"),
    _r(id="PAT-37", topic="Wearable scissored-pair CMG for balance assist (Honda)",
       citation="Honda Motor Co., Ltd. (inventors Chiu J, Bannai T, Goswami A). Wearable scissor-paired control moment gyroscope (SP-CMG) for human balance assist. US 9,649,242 B2, granted 2017-05-16; priority 2014-01-17.",
       year="2017", doi_or_url="https://patents.google.com/patent/US9649242B2/en", source_type="patent", evidence_class="patent disclosure", access_level="full text",
       task_or_setup="Two CMGs as a scissored pair with gimbal servos driven in opposite directions; accelerometer/gyroscope sensing", participants_or_bench="n/a", comparator="",
       key_quantitative_findings="Flywheels <= 900 g, radius <= 50 mm, tungsten alloy >= 18.5 g/cm3; <= 5000 rpm; torque >= 25 N m; gimbal +/-90 deg; actuate phase up to 267 deg/s (90 deg in 880 ms), "
                                 "reset about 44 deg/s (90 deg in 2000 ms); device <= 9 kg. Status: expired - fee related (lapsed 2025-06-23, as displayed).",
       units_and_conditions="body scale", locator="Claims and description (Google Patents)", limitations="No legal assessment", relevance_to_design="Scissored pairs and asymmetric actuate/reset phases are open prior art",
       transferability="low", transferability_reason="9 kg body-worn device", design_implication="The pulse-then-slow-reset strategy is free to use", search_query="WebSearch patent handheld haptic CMG scissored pair; WebFetch Google Patents", stream="PAT"),
    _r(id="PAT-38", topic="Hand-worn gyroscope tremor stabiliser on an adjustable splint (Kalvert)",
       citation="Kalvert MA. Adjustable and tunable hand tremor stabilizer. US 6,730,049 B2, granted 2004-05-04; priority 2002-06-24.", year="2004",
       doi_or_url="https://patents.google.com/patent/US6730049B2/en", source_type="patent", evidence_class="patent disclosure", access_level="full text",
       task_or_setup="Rigid splint with removable, repositionable gyroscopes (Kenyon KS series) strapped to hand and forearm", participants_or_bench="n/a", comparator="",
       key_quantitative_findings="Example gyroscopes run about 22 000 rpm; Kenyon KS-2 2.8 in dia x 4.5 in, 1.5 lb; KS-4 2.13 lb; KS-6 3.25 lb; KS-8 5.13 lb; 115 V 400 Hz; 5-7 min start-up. "
                                 "Status: expired - fee related (2022-08-24, as displayed).",
       units_and_conditions="n/a", locator="Description (Google Patents)", limitations="No performance data", relevance_to_design="Scale of gyroscopes that stabilise a hand: 0.7-2.3 kg, minutes to spin up",
       transferability="low", transferability_reason="Limb-scale devices", design_implication="Confirms hand-stabilising gyroscopes are two orders of magnitude above a pen end-cap", search_query="WebSearch patent pen gyroscope flywheel tremor; WebFetch Google Patents", stream="PAT"),
    _r(id="PAT-39", topic="Haptic feedback stylus with a linear actuator along a non-primary axis (Immersion)",
       citation="Immersion Corp (inventor Rosenberg LB). Haptic feedback stylus and other devices. US 7,265,750 B2, granted 2007-09-04; priority 1998-06-23.", year="2007",
       doi_or_url="https://patents.google.com/patent/US7265750B2/en", source_type="patent", evidence_class="patent disclosure", access_level="full text",
       task_or_setup="Linear actuator applying forces in unsensed directions; stylus embodiments move the body relative to the tip along its length", participants_or_bench="n/a", comparator="",
       key_quantitative_findings="Claim 1 (paraphrase): force-feedback device with a user object, sensors for its primary degrees of freedom and a single linear actuator applying force along a "
                                 "non-primary axis through the object. No quantitative data. Status: expired - fee related (2018-10-27, as displayed).",
       units_and_conditions="n/a", locator="Abstract, claim 1 (Google Patents)", limitations="No legal assessment", relevance_to_design="Old prior art for inertial/linear actuators in styluses (free to use)",
       transferability="medium", transferability_reason="Stylus embodiment", design_implication="No blocking art found for an end-cap reaction mass; Verily PAT-08/PAT-12 remain the items to clear", search_query="WebSearch patent stylus reaction wheel flywheel haptic; WebFetch Google Patents", stream="PAT"),
]


def rows_from_results(res: Dict) -> List[Dict]:
    """'This study' rows filled from results/endcap/endcap_study.json (report.build passes the assembled dict)."""
    out = []
    h = res.get("headline", {})
    for rid, key, topic in (("ACT-84", "scaling", "Physical ceilings of ungrounded end-cap devices at 1-12 Hz (this study)"),
                            ("ACT-85", "optimise", "End-cap design optimisation: reaction mass, CMG arrangements, reaction wheels, passive gyroscope (this study)"),
                            ("ACT-86", "tremor", "End-cap devices on top of the Rev H nose, causal tracker, test seeds (this study)"),
                            ("ACT-87", "steer", "Can inertia write? Letter-scale steering at 1-5 Hz in H1 (this study)"),
                            ("ACT-88", "gyro", "Gyroscopic stiffening by a passive rotor in the pen (this study)"),
                            ("ACT-89", "cue", "Pseudo-force cue in the Rev H pen: grip acceleration, ink jitter, literature channels (this study)"),
                            ("ACT-90", "recommendation", "Recommended end-cap and its budget (this study)")):
        hl = h.get(key, {})
        out.append(_r(id=rid, topic=topic, citation="This ledger's calculation and simulation: endcap/ (run_study stage " + key + ")", year="2026",
                      doi_or_url="results/endcap/endcap_study.json " + key + " ; docs/inertial_endcap.md", source_type="derived simulation" if key not in ("scaling", "optimise") else "derived calculation",
                      evidence_class="numerical simulation" if key not in ("scaling", "optimise") else "calculation", access_level="full text",
                      task_or_setup=hl.get("setup", ""), participants_or_bench="none (simulation)", comparator=hl.get("comparator", ""),
                      key_quantitative_findings=hl.get("findings", ""), units_and_conditions=hl.get("units", ""), locator="results/endcap/endcap_study.json " + key,
                      limitations=hl.get("limitations", "Model H1 hand calibrated only against HAP-26; synthetic writing and tremor; grip split unmeasured"),
                      relevance_to_design=hl.get("relevance", ""), transferability="medium", transferability_reason="Model-to-model; nothing measured",
                      design_implication=hl.get("implication", ""), retrieved="", search_query="n/a (derived)", stream="ACT"))
    return out


def write(path, res=None):
    rows = list(LIT) + (rows_from_results(res) if res else [])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows
