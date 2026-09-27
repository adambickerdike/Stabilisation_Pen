# ACT — Active handheld stabilisation and causal tremor estimation

Stream: ACT (active tremor-cancelling / stabilised instruments; causal tremor estimation and prediction)
Ledger: `docs/research/ledger/ACT_active_stabilisation.csv` (ACT-01 … ACT-26)
Evidence retrieved: 2026-09-26 (all ledger sources). Notes finalised 2026-09-27.

Method notes
- PDFs fetched with WebFetch or `curl` were converted to text locally (pdfminer.six) and read directly; numbers in the ledger come from that text unless marked otherwise. PubMed Central, patent and web pages were read through WebFetch with prompts that asked for verbatim quotes of the numbers used.
- "abstract only" rows were read at abstract level (via Europe PMC or search-indexed abstracts) because the full text was paywalled or blocked. Blocks were not bypassed.
- The session's shared WebSearch budget ran out after query W29 (see §1.1). Later discovery used bibliographic database interfaces (Europe PMC REST, Crossref, arXiv listing pages, Unpaywall), listed exactly in §1.2–1.3.

## 1. Search log (queries run 2026-09-26; one verification re-fetch on 2026-09-27 is marked in §1.3)

### 1.1 WebSearch queries (exact strings)

| # | Query | Outcome |
|---|---|---|
| W1 | `Yang MacLachlan Riviere "six-degree-of-freedom" handheld tremor-canceling microsurgical instrument manipulator design` | PMC4235034, CMU accepted manuscript → ACT-03 |
| W2 | `"Micron: an actively stabilized handheld tool for microsurgery" IEEE Transactions on Robotics 2012 doi` | DOI 10.1109/TRO.2011.2169634 → ACT-01/02 |
| W3 | `"Manipulator Design and Operation of a Six-Degree-of-Freedom Handheld Tremor-Canceling Microsurgical Instrument" 10.1109/TMECH` | DOI 10.1109/TMECH.2014.2320858 |
| W4 | `Becker MacLachlan Riviere "State estimation and feedforward tremor suppression for a handheld micromanipulator with a Kalman filter" IROS 2011 doi` | DOI 10.1109/IROS.2011.6094935 → ACT-06 |
| W5 | `Riviere Rader Thakor 1998 "Adaptive cancelling of physiological tremor for improved precision in microsurgery" weighted-frequency Fourier linear combiner` | CMU PDF → ACT-08 |
| W6 | `Veluvolu Ang "Estimation of physiological tremor from accelerometers for real-time applications" Sensors 2011 BMFLC WFLC accuracy` | Semantic Scholar PDF → ACT-09 |
| W7 | `"Estimation and filtering of physiological tremor for real-time compensation in surgical robotics applications" Veluvolu 2010 abstract 64% 43% WFLC BMFLC` | → ACT-10 (abstract) |
| W8 | `Liftware Steady spoon Parkinson's disease study tremor reduction randomized handheld active stabilizing utensil` | Ryden 2020 (Gyenno), Sabari 2019 → ACT-18 |
| W9 | `Sabari Stefanov 2019 "Adapted Feeding Utensils" Liftware Steady participants essential tremor Parkinson's "participants"` | n not found |
| W10 | `"Liftware" Parkinson's disease tremor accelerometer study results "active cancellation of tremor" 2016 OR 2017 OR 2018 OR 2020 OR 2021 OR 2022` | press items only |
| W11 | `Pathak patent "tremor" handheld tool "motion-generating mechanism" attachment stabilize Lift Labs US patent` | US10219930B2, US8308664B2 → ACT-17 |
| W12 | `Ou Gouldstone Jaeger Sipahi "Control Design for a Hand Tremor Suppression Pen" DSCC2015-9962` | abstract text → ACT-20 |
| W13 | `"Hand Tremor Suppression Pen" Sipahi pendulum pen-rod casing active actuation abstract simulation` | abstract text; Northeastern theses (blocked) |
| W14 | `"Assistive Pen to Improve Quality Writing of Hand Tremor with Proportional-Control"` | IJMMM 2015; Sci Rep 2025 on PMC |
| W15 | `active tremor cancelling pen prototype handwriting nib actuator voice coil accelerometer essential tremor study` | same pens |
| W16 | `ijmmm.org "assistive pen" hand tremor proportional control linear voice coil actuator rig 2015 pdf` | no direct PDF |
| W17 | `Yusop As'arry Md Zain "assistive pen" tremor International Journal of Materials Mechanics and Manufacturing vol 3` | TREMORX (passive) |
| W18 | `"Assistive Pen to Improve Quality Writing of Hand Tremor" doi 10.7763/IJMMM` | DOI 10.7763/IJMMM.2015.V3.166 → ACT-21 |
| W19 | `Saxena Patel active handheld device compensation physiological tremor ionic polymer metallic composite actuator IROS 2013` | IEEE page only (no abstract) |
| W20 | `"pen-tip deviations" tremor "controller effort" pen casing pendulum Sipahi 2015` | confirms ACT-20 abstract wording |
| W21 | `"Modeling and experimental study of a hand tremor suppression system" authors journal` | wearable/emulator study; venue unverified; not used |
| W22 | `GyroGlove gyroscopic tremor glove clinical study results essential tremor Parkinson's tremor reduction percent GyroGear` | → ACT-25 |
| W23 | `Steadiwear Steadi-Two glove how it works tremor reduction percent clinical evidence FDA` | → ACT-26 |
| W24 | `ARC pen Parkinson's vibration handwriting Lucy Jung Manus Neurodynamica study micrographia results` | press accounts only (§1.5) |
| W25 | `"tremor" "pen" stabilization prototype piezoelectric OR "voice coil" OR gimbal nib "writing" 2018 OR 2019 OR 2020 OR 2021 OR 2022 OR 2023 OR 2024 paper` | US10101824 → ACT-23; CSU thesis |
| W26 | `"Writing pen for essential tremors patients" thesis California State University` | CSUS PDF → ACT-24 |
| W27 | `Riviere Ang Khosla 2003 "Toward active tremor canceling in handheld microsurgical instruments" abstract accelerometers piezoelectric error reduction` | CMU PDF → ACT-07 |
| W28 | `ITrem2 handheld active tremor compensation instrument Ang Latt Tan results tremor reduction accelerometer piezoelectric` | ITrem2 abstract (§1.5) |
| W29 | `Shahtalebi PHTNet "Characterization and Deep Mining of Involuntary Pathological Hand Tremor using Recurrent Neural Network Models" Scientific Reports 2020` | → ACT-12 |
| W30 | `Shahtalebi Atashzar Patel Mohammadi HMFP-DBRNN real-time hand motion filtering and prediction deep bidirectional RNN prediction horizon` | **Not executed**: WebSearch budget exhausted |

### 1.2 Bibliographic database queries (exact strings)

Europe PMC REST (`/search`, resultType=core):
- `EXT_ID:20623480 AND SRC:MED` (ACT-10); `EXT_ID:23771303 AND SRC:MED` (ACT-11); `EXT_ID:30915973 AND SRC:MED` (ACT-18); `EXT_ID:20209026 AND SRC:MED` (ITrem sensing); `EXT_ID:29060579`, `EXT_ID:24110876`, `EXT_ID:24111117` (AND SRC:MED)
- `TITLE:"noninvasive handheld assistive device to accommodate essential tremor"` (ACT-16)
- `TITLE:"hand motion filtering and prediction"` (0 hits)
- `(TITLE:tremor) AND (TITLE:prediction OR TITLE:predict OR TITLE:forecasting) AND (ABSTRACT:LSTM OR ABSTRACT:"neural network" OR ABSTRACT:"deep learning" OR ABSTRACT:transformer OR ABSTRACT:"temporal convolutional")` (7 hits; ACT-14, ACT-15)
- `(ABSTRACT:tremor) AND (ABSTRACT:WFLC OR ABSTRACT:BMFLC OR ABSTRACT:"Fourier linear combiner") AND (ABSTRACT:"neural network" OR ABSTRACT:LSTM OR ABSTRACT:"machine learning" OR ABSTRACT:"support vector" OR ABSTRACT:"deep")` (1 hit)
- `DOI:"10.1109/TCYB.2014.2381495"`; `AUTH:"Tatinati S" AND TITLE:tremor` (7 hits; ACT-11)
- `AUTH:"Shahtalebi S"`; `(ABSTRACT:"physiological tremor") AND (ABSTRACT:prediction OR ABSTRACT:predict) AND (ABSTRACT:"handheld" OR ABSTRACT:"hand-held" OR ABSTRACT:microsurg*)`
- `DOI:"10.1016/j.isatra.2024.12.040"`; `DOI:"10.1016/j.compbiomed.2025.109814"`
- `AUTH:"Riviere CN" AND (TITLE:Micron OR TITLE:handheld OR TITLE:"hand-held" OR TITLE:tracker OR TITLE:tremor)` (38 hits; ACT-04, ACT-05)
- `(Liftware OR "active cancellation of tremor" OR "tremor-cancelling spoon" OR "tremor cancelling spoon" OR "stabilizing spoon" OR "stabilising spoon")` (22 hits; ACT-19)

Crossref (`query.bibliographic`): `An active handheld device for compensation of physiological tremor using an ionic polymer metallic composite actuator`; `Vision Aided Active Error Canceling in Handheld Microsurgical Instrument`; `WAKE: Wavelet decomposition coupled with adaptive Kalman filtering for pathological tremor extraction`.

Semantic Scholar Graph API: `DOI:10.1109/iros.2013.6696969` and `DOI:10.1115/DSCC2015-9962` (abstracts elided by publisher); `DOI:10.1016/j.proeng.2012.07.170` (wrong paper, discarded); `DOI:10.1016/j.proeng.2012.07.236` (ITrem2 abstract); search `HMFP-DBRNN hand motion filtering prediction` (HTTP 429).

arXiv: export API queries `all:"hand motion filtering" AND all:tremor`, `ti:tremor AND (ti:prediction OR ti:estimation OR ti:extraction)`, `ti:tremor AND ti:prediction`, `ti:tremor` all returned HTTP 406. Listing pages fetched instead: `https://arxiv.org/search/?query=tremor+prediction&searchtype=all&abstracts=show&order=-announced_date_first&size=50` (found WAKE, arXiv:1711.06815); `…query=tremor+suppression+OR+tremor+compensation+OR+tremor+cancellation…` (1 irrelevant hit); `…query=tremor+estimation…` (WAKE and 2 others).

Unpaywall (`api.unpaywall.org/v2/<doi>`): 10.1109/TNSRE.2021.3097007; 10.1109/jbhi.2022.3209316; 10.1016/j.compbiomed.2025.109814; 10.3390/s24227359; 10.1109/tbme.2013.2264546; 10.1109/TCYB.2014.2381495.

ClinicalTrials.gov API v2: `studies/NCT05958030` (GyroGlove trial).

### 1.3 URLs fetched (WebFetch unless noted)
Used: Micron_TRO_final.pdf (brief URL); PMC4235034; TMECH_Yang_accepted.pdf; Becker_IROS11.pdf (brief URL); riviere_cameron_1998_1.pdf; pdfs.semanticscholar.org/d510/84d791520cd5c79ca4f409793db0c659ffc9.pdf; PMC4156033 (x3); PMC7313572; patents.google.com US8308664B2, US10219930B2 (x2), US10101824B2; news.northeastern.edu/2013/01/02/hand-tremors-capstone; PMC12325923 (x3); journals.utm.my/jurnalteknologi/article/view/9205; neurologycongress.com (GyroGlove abstract); steadiwear.com validation and technology pages; PMC7010677 (x2); PMC11598486; PMC4641839; PMC5891151; PMC3801264 (x2); PMC11782133; PMC12839506; PMC11568799 (plus one verbatim re-check on 2026-09-27). By `curl`: doi.org/10.7763/IJMMM.2015.V3.166 → ijmmm.org/vol3/166-CR2007.pdf; scholars.csus.edu thesis PDF; ri.cmu.edu riviere_cameron_2003_1.pdf; arxiv.org/pdf/1711.06815; nature.com/articles/s41598-020-58912-9 (+ /tables/2, /tables/3); uwo.scholaris.ca accepted manuscript of Ibrahim 2021 (via ir.lib.uwo.ca/mechanicalpub/23).

### 1.4 Access failures (not bypassed)
HTTP 403: mdpi.com (Veluvolu 2011; read via Semantic Scholar copy), Wiley rcs.340, ResearchGate (Ou 2015), ASME Digital Collection (Ou 2015), repository.library.northeastern.edu (two pen theses, WebFetch and curl), scholarworks.calstate.edu, sciencedirect.com (ITrem2 HTML and PDF). reCAPTCHA: pubmed.ncbi.nlm.nih.gov/25419103, PMC HTML via curl. Bot challenge: digital.csic.es (Pascual-Valdunciel 2022). HTTP 418: ieeexplore PDFs. HTTP 500: Europe PMC full-text XML PMC4156033. HTTP 503 / TLS name mismatch: liftware.com. Empty: ieeexplore.ieee.org/document/6696969. Failed Google results page via WebFetch (`google.com/search?q=%22Assistive+Pen…%22+ijmmm`). Two wrong-ID fetches (PMC3269767; arxiv.org/abs/1811.07469) returned unrelated papers and were discarded.

### 1.5 Consulted but not ledgered (to stay within 12–25 core rows; abstract- or secondary-level unless stated)
- Ryden LE et al. 2020, Ann Indian Acad Neurol, doi 10.4103/aian.AIAN_251_19 (full text): Gyenno active spoon in PD, n=10 (2 excluded), mostly rest tremor; less rice transferred with device on in the 60-s task (p=0.0138); 3-attempt task not significant. **Negative result.**
- Aye YN et al. 2012, Procedia Eng 41:729-736 (ITrem2; IMU + camera + BMFLC + piezo): error amplitude −67% in a 1-DOF oscillation test (abstract).
- Adhikari K et al. EMBC 2017 (recursive SSA): tremor-estimation accuracy up to 85% offline; ≥70% in real time with ≈72 ms delay, one-tenth the delay of a linear-phase band-pass for similar performance (abstract). Rasheed A et al. ISA Trans 2025 (RSSA-RVFL): 79.03% vs 70.40% benchmark with a nine-sample delay (abstract).
- Tatinati S et al. IEEE Trans Cybern 2015 (LS-SVM multi-step; horizon need not be known a priori); Tan GY et al. Comput Biol Med 2025 (self-attention TCN, multi-step PD tremor): abstracts give no horizon or accuracy numbers.
- Chen J et al. Sensors 2024 (EEMD-IWOA-LSTM, full text): one-step, 12-sample input, MSE 0.1148 / 0.0062; sampling rate and causality of EEMD not stated; no robot test.
- US 8,308,664 B2 (Univ. Michigan; Pathak, Luntz, Brei et al.; priority 2009): SMA-wire 2-axis stabiliser for handheld objects explicitly including "pens, pencils"; targets 1–4 Hz, ≤1 mm p-p; bench 82% p-p / 80% RMS at 1 Hz, 61% RMS at 3 Hz; 12.1 W (patent text).
- MacLachlan RA et al. 2016 (PMC5891151): electromagnetic tracker for Micron, 1,500 samples/s, 300 Hz bandwidth, 1.5 ms latency, 6.4 µm RMS position noise; not yet usable for real-time control.
- Saxena & Patel IROS 2013 (IPMC handheld compensator, doi 10.1109/IROS.2013.6696969): no abstract retrievable; no numbers recorded.
- Adabi & Ondo 2024 review (TOHM, PMC11568799): for Liftware Steady states verbatim "There is no published data." (re-checked 2026-09-27), which conflicts with the peer-reviewed Pathak 2014 pilot (ACT-16); for GYENNO: "One small study did not show benefit in patients with Parkinson' disease but there are no clinical trials or published data in ET".
- Northeastern capstone (news, 2013): instrumented pen found grip force "increases threefold" during EMS-simulated tremor (student project). ARC pen (press, 2015): vibration-stimulation pen for micrographia, 14 users, "86%" writing improvement claimed; not tremor cancellation.

## 2. Critical synthesis

**Evidence base.** The 26 rows contain 9 human studies (largest n = 20; most n ≤ 15), 7 bench experiments, 7 simulation or offline-algorithm studies, 2 patents and 1 manufacturer statement. Only two classes of active handheld stabiliser are characterised quantitatively. The first is Micron (microsurgery, free space, external optical tracker). The second is Liftware-type utensils (cm-scale travel, free space). The only active pens found are a single-axis voice-coil bench rig (ACT-21) and a simulation (ACT-20). The 2025 "smart pen" (ACT-22) does not move the nib; it filters a digital signal and drives a vibration motor.

**What transfers.**
1. *Delay is the binding constraint.* Below ~30 Hz, Micron's servo behaves as a pure delay, and its authors state that rejection improves only by cutting delay or predicting (ACT-01). From that delay-only model we derive (our calculation, not a published result) the residual after perfect-gain cancellation, 2|sin(πfτ)|:

| delay τ | 4 Hz | 6 Hz | 8 Hz | 10 Hz |
|---|---|---|---|---|
| 3 ms | 0.08 | 0.11 | 0.15 | 0.19 |
| 5 ms | 0.13 | 0.19 | 0.25 | 0.31 |
| 10 ms | 0.25 | 0.37 | 0.50 | 0.62 |
| 20 ms | 0.50 | 0.74 | 0.96 | 1.18 |
| 30 ms | 0.74 | 1.07 | 1.37 | 1.62 |

   An uncompensated 16–20 ms latency, reported as "unavoidable" in IMU-plus-pre-filter pipelines (ACT-11), leaves residuals of 0.78–0.96 at 8 Hz and 0.96–1.18 at 10 Hz: little or no benefit, with amplification above ~10 Hz. Keeping ≥10 dB at 8–10 Hz without prediction needs ≲5 ms end-to-end latency; otherwise the controller must predict over the measured delay (ACT-06, ACT-11, ACT-14).
2. *Estimators.* A 15-state Kalman filter with velocity feedforward halved residual error (ACT-06). BMFLC-type multi-frequency models beat single-frequency WFLC in real time: 64% vs 43% (ACT-10). WAKE improves on BMFLC offline (ACT-13). All are computationally light, but only Kalman/RLS tremor tracking has actually been shown running on a pen-sized MCU (Teensy 4.1; ACT-22).
3. *Saturation management* (ACT-01) and *human adaptation* transfer. With cancellation on, Micron users moved the handle 35% more and took 37% longer (ACT-02), so the pen should expect writing to slow down.

**What needs modification.**
- *Voluntary/tremor separation.* Micron's goal filters (1.5 Hz low-pass; 0.15–2 Hz scaling; 1 mm/s velocity limit) and the ML ground truths (voluntary motion ≤2–3 Hz; ACT-12, ACT-14) assume slow voluntary motion (90% of Micron tip speeds were <2 mm/s; ACT-02). Handwriting is not slow, and how far its strokes overlap the 4–12 Hz tremor band is not established by these sources and must be measured. Tremor-band predictive cancellation is needed rather than low-pass goal filtering. When voluntary motion is preserved, Micron's benefit fell from 89% (fixed goal) to 34–57% RMS (ACT-03 vs ACT-04).
- *Reference frame.* Micron's world reference is a 2 kHz external tracker. An IMU-only Micron reached a noise floor of ~30 µm p-p and could not cancel low-frequency motion (ACT-07). With ±0.5 mm travel, the pen can only address tremor-band motion unless it senses motion relative to the paper.
- *Actuators.* Piezo benders gave ±0.4 mm actuator travel (~0.4 mm usable tip cube) but need −240/+480 V (ACT-01). Ultrasonic stick-slip motors chattered at 50–100 Hz (ACT-03/04). A voice coil is plausible, but its magnetic field corrupted the in-pen accelerometer (ACT-21).

**Contact changes the problem (key transferability judgement).** Every active stabiliser with quantified performance worked in free space or at ≤16 mN tissue loads (ACT-05); the one exception, the single-axis pen rig (ACT-21), did not report its nib load. Micron-6DOF's error rose from 17 to 47 µm RMS between 0.25 and 0.30 N of lateral load (ACT-03), while the pen's nib carries 0.2–2 N normal load plus friction. In free space, tip error equals handle motion plus the actuator correction. In contact, static friction holds the nib, so during stick the ink does not move. Errors then come from slip events and from the actuator pushing the nib. A passive decoupled pen showed both effects: friction plus inertia grounded the nib, but it "tends to release, uncontrollably" on curves (ACT-24). A Micron-style position servo would fight the paper during stick and jerk at breakaway. Impedance/force control with nib-load sensing is the hypothesis to test; no source establishes it. Overall judgement: the quantitative device results transfer at low–medium level, the algorithms at medium–high, and there is no evidence at all on actuated nibs in contact.

**What the literature does not establish.**
- There are no human data for any pen that actively moves its nib.
- Nib actuation performance, stability or stick–slip at 0.2–2 N has not been reported.
- Pathological tremor displacement at the nib during writing, compared with ±0.5 mm, is unknown. Liftware (cm travel) excluded severe tremor, and Micron studied physiological tremor only.
- Causal, multi-step predictor accuracy on handwriting data, at pen latency, on a microcontroller, has not been measured.
- Latency and bandwidth of Liftware or Gyenno are undocumented.
- Whether an active pen beats passive pens on trace metrics is untested.

**Conflicting and negative results.**
- *Active vs passive.* A passive deep-bowl spoon transferred more food than the active Gyenno spoon (93.6% vs 88.9%; significance not reported in our extraction) (ACT-19). The Gyenno spoon reduced food transfer in PD (p = 0.0138; §1.5). Liftware was preferred about as much as a weighted spoon (ACT-18).
- *Liftware.* The manufacturer-authored pilot reports 71–76% reduction (ACT-16), but a 2024 review states "There is no published data."
- *Bench vs human.* Micron's ≥15 dB bench attenuation became a 10–52% error reduction in humans (ACT-01/02).
- *Inflated accuracies.* BMFLC-KF's 0.003 µm error came from non-causal pre-filtered data (ACT-09). PHTNet was tested on synthetic voluntary signals (ACT-12). Ibrahim's accuracy metric rests on a ≤2 Hz ground truth (ACT-14). In real-time loops the numbers are lower: WFLC 43–69% vs 64–94% for newer models (ACT-10, ACT-14).
- *Simulation vs bench.* The simulated pen claims −47 dB (ACT-20). The only physical pen rig reduced the tremor spectral peak by ~57% (ACT-21).

**Decisive experiments.**
1. *Latency audit.* Measure IMU-to-nib latency on the prototype electronics. Accept the design only if cancellation at the dominant tremor frequency is ≥6 dB with the chosen predictor horizon.
2. *Nib-in-contact bench.* Mount a 2-axis actuated nib on paper over a force plate, with normal load 0.2, 0.5, 1 and 2 N. Drive the housing with recorded ET/PD writing tremor. Measure the ink trace (scanner or microscope) and the nib forces. Compare position-servo, impedance and passive-compliant modes, and quantify stick-slip.
3. *Nib tremor census.* Record amplitude and spectra at the nib during writing in ET/PD patients, and compute the fraction within ±0.5 mm (the saturation rate).
4. *Voluntary/tremor overlap.* Record handwriting with an IMU and a digitiser, and measure how much voluntary stroke power lies in 4–12 Hz.
5. *Causal estimator bake-off on pen data.* Compare WFLC, BMFLC-KF, KF-feedforward, WAKE and LSTM/TCN at 5–30 ms horizons, including microcontroller latency and memory.
6. *Blinded crossover trial.* Compare active, sham and passive weighted pens on trace error, legibility, writing speed and handle motion, with a pre-registered margin.
