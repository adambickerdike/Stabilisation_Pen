# Human study plan

**Status: PROPOSED. No participant has been enrolled, no ethics application has been submitted, and no human data exist in this repository (2026-09-27).** Every number below is a design assumption, a literature value (evidence id from `docs/evidence.csv`) or an acceptance criterion from [`acceptance_criteria.csv`](acceptance_criteria.csv). None is a result.

Bench protocols are in [`bench_protocols.md`](bench_protocols.md). Stage gates, including the safety gate **G-S** that any powered prototype must pass before it touches a participant, are in [`prototype_stages.md`](prototype_stages.md).

Contents:

- §1 The central distinction: immediate assistance vs lasting improvement
- §2 Study overview
- §3 Elements common to all studies
- §4–§9 Studies EXP-H01…H06
- §10 Ethics, regulatory and data-protection notes
- §11 Sample-size summary

---

## 1. Immediate assistance vs lasting improvement

The pen may help a person in two different ways. The evidence, endpoints and claims for each must never be mixed (REQ-VAL-002, COR-20, DEC-002).

| | **Immediate assistance (IA)** | **Lasting improvement (LI)** |
|---|---|---|
| Question | Is writing better **while the device acts**? | Is **unassisted** writing better after practising with the device, does it last, and does it transfer? |
| Device state when the outcome is measured | ON (ASSIST_KF, ASSIST_ML or GUIDED; `docs/icd.md` §6) compared with sham (NEUTRAL_HOLD) and OFF | **OFF**, or an ordinary pen, at every outcome test |
| Timing | Within a session, minutes | Baseline → end of practice → **delayed retention** (7 days for novices, 6 weeks for PD) → **transfer** (untrained material, dual task, ordinary pen) |
| Study | **EXP-H06** | **EXP-H04** |
| Primary outcome | Tremor in the **deposited ink** (free writing) or path distance to a template (guided tasks) with the device ON vs NEUTRAL | Unassisted shape error (novices) or unassisted letter size (PD micrographia) at delayed retention |
| Main risk | Distortion of intended strokes (REQ-CTRL-005); hidden dependence on the device | Error-removing assistance can **impair** unassisted retention and transfer (HAP-09; also HAP-02, HAP-04, HAP-06) |
| Claim allowed if the study succeeds | "While the pen was in use, [metric] in [population] was reduced by [effect, CI] compared with the same pen not correcting." | "After [dose] of practice with [training mode], unassisted [metric] in [population] was [effect, CI] better than control practice at [retention interval], and transferred to [tasks]." |
| Claim **not** allowed | Anything about writing without the device, or about learning | Anything about performance while the device is active |

### Rules that enforce the separation

- **R1.** Every endpoint in every statistical analysis plan (SAP) is labelled IA or LI. No composite endpoint mixes them.
- **R2.** The device mode during each outcome test is set by the study app from the randomisation code, logged (ICD event 0x0001 "mode change") and verified from the logs before analysis. A test done in the wrong mode is a protocol deviation, not data for the other endpoint.
- **R3.** EXP-H06 ends with an unassisted block to detect after-effects (for example reliance or a transient improvement). It is labelled **exploratory** and is never evidence of LI.
- **R4.** EXP-H04 records assisted performance during practice (acquisition), but reports it separately. **Acquisition gains are not evidence of learning** (HAP-04, HAP-06, HAP-09).
- **R5.** Claims are made per user group (REQ-USR-001) and per mechanism (DEC-002):
  - nib correction → action and essential tremor, within the amplitude limits of REQ-USR-002;
  - cueing, feedback and practice → Parkinson's micrographia. A ±0.5 mm stage cannot enlarge strokes (COR-10);
  - capture and notes → everyone.
- **R6.** Device modes map to claims:

  | Claim type | Device modes |
  |---|---|
  | IA | ASSIST_KF, ASSIST_ML, GUIDED, cue-on |
  | LI (training only) | TRAINING_FADE and the fading cue schedule |
  | Outcome tests | OFF or NEUTRAL_HOLD |

### What the current evidence predicts, and why the design hedges

The simulation (synthetic handwriting) finds that no causal estimator separates tremor from intended writing below about 9 Hz (COR-11; `docs/sim_report.md` §3.2). The frequency gate (DEC-009, default 7.5 Hz) therefore keeps free-writing cancellation off for lower frequencies.

Essential tremor in a clinic sample had a frequency of 5.79 ± 1.32 Hz (Elble 2000, screened in `docs/research/notes/PDT_pd_et_handwriting.md` §1.2). If that distribution holds for writing tremor at the nib, only about 10 % of ET patients have tremor above the gate (P(f ≥ 7.5 Hz) = 0.098 for a normal distribution).

Combined with the amplitude limit (about 50 % of ET within 2 mm p-p, PDT-12), **free-writing cancellation might address only about 5 % of ET patients** (if amplitude and frequency are independent), unless:

- EXP-H01 finds a different frequency distribution at the nib; or
- EXP-E01 finds better separation on real writing than the simulation predicts.

For that reason the immediate-assistance study (EXP-H06) has two pre-specified variants: free writing (H06-F) and guided tasks (H06-G). The choice is fixed at gate G-C, before enrolment, from EXP-E01, E02 and B09 results. Guided (known-path) assistance is the credible near-term use: in simulation it cuts the path distance on circles and spirals to 0.29–0.37 of neutral (`results/sim/guided_path_distance.json`).

---

## 2. Study overview

| ID | Question | Population (n) | Design | Primary outcome | Claim type | Stage / gate |
|---|---|---|---|---|---|---|
| EXP-H01 | How large, and at what frequency, is tremor **at the nib** during natural writing? What forces, tilts and intended-motion spectra occur? | ET 20 (extendable to 40), PD 20, older adults 20, healthy adults 20 | Cross-sectional measurement with an instrumented **passive** pen; 10 per group retested | Nib tremor amplitude, major axis, p-p, during sentence copying; fraction ≤ 0.25/0.5/1/2/4 mm | none (measurement) | Stage A (no active device); ethics |
| EXP-H02 | Is the research-pen form (mass, CoM, diameter) acceptable? | 40 (10 per group: ET, PD, older, healthy incl. drawing users) | Randomised 4-pen crossover (Williams design), unpowered mock-ups, assessor-blinded | Comfort VAS; equivalence to the reference pen within ±10 mm | device burden | Stage A–B |
| EXP-H03 | Is a nose skid with a constant-force nib (configuration D) acceptable, and does it passively reduce tremor? | H03-F 22 (healthy and older, ≥ 30 % left-handed); H03-T 20 ET | Randomised, participant- and assessor-blinded paired comparison of identical-shell non-active prototypes | Feel acceptability (non-inferiority, margin 1 point); ET nib-tremor ratio | device burden; passive effect | Stage A–B; DEC-008 |
| EXP-H04 | Does practice with fading guidance, error amplification or fading cues improve **unassisted** writing, with retention and transfer? | H04-A novices 72 (3 × 24); H04-B PD with micrographia: feasibility 36 (3 × 12), then efficacy 102 (3 × 34) | Parallel randomised controlled trials, assessor-blinded | H04-A: unassisted shape error at 7 days; H04-B: unassisted letter height at 6-week retention | **LI** | Stage C (home use for H04-B); G-S, G-C |
| EXP-H05 | What ink distortions and quality changes can people perceive? | 30 raters (+ 10 writers judging their own writing); H05b haptic 16 | Psychophysics, 2AFC adaptive staircases, blinded stimuli | 75 %-correct thresholds (10th percentile across raters) | sets REQ-CTRL-005 and REQ-MECH-005 | Stage A onward |
| EXP-H06 | While active, does the pen reduce tremor in the deposited ink compared with sham and off? | 42 with action/essential tremor (+ 12 healthy for device burden) | Randomised 3-period crossover (ON / NEUTRAL / OFF), participant, operator and assessor blinded | H06-F: ink tremor amplitude in free writing; or H06-G: path distance in guided tasks. GM ratio ON/NEUTRAL | **IA** | Stage C (a pilot of 10 at Stage B); G-S |

EXP-B06 (grip impedance) is a bench study with 12 healthy participants (`bench_protocols.md` §7). It is covered by the same ethics approval and the common elements of §3.

---

## 3. Elements common to all studies

### 3.1 Group definitions (REQ-USR-001)

| Group | Definition for inclusion | Claims it can support |
|---|---|---|
| (a) Everyday handwriting difficulty | Self-reported difficulty, no neurological diagnosis | Capture, notes, feel (H02, C01, A01) |
| (b) Essential or action tremor | Clinician diagnosis of ET per the 2018 consensus classification (isolated bilateral upper-limb action tremor ≥ 3 years; PDT-07), or other action tremor affecting writing; medication recorded | Tremor correction (IA), within REQ-USR-002 limits |
| (c) Parkinson's disease | Clinician-confirmed PD, Hoehn & Yahr 1–3. Sub-typed tremor-dominant vs akinetic-rigid/PIGD. Medication state recorded (ON by default) | Micrographia cueing and practice (LI); tremor census only |
| (d) Drawing and art users | Regular drawing practice, no neurological diagnosis | Feel, capture (H02, C01) |
| Older adults | ≥ 65 years, no neurological diagnosis | Normative data (H01), feel (H02, H03) |
| Healthy adults | 18–64 years, no neurological diagnosis | Normative spectra (H01), mechanism studies (H04-A, H05, B06) |

**The pen never infers or displays a group or diagnosis** (REQ-USR-003; PDT notes §2.5). Group membership comes only from clinician diagnosis or self-report at enrolment.

### 3.2 Common inclusion and exclusion

- **Inclusion:**
  - age ≥ 18;
  - able to hold a pen and write for 20 min with breaks;
  - normal or corrected vision for reading at 35 cm;
  - literate in the study language's script;
  - able to give informed consent.
- **Exclusion:**
  - neurological conditions affecting the writing hand other than the group's own (stroke, dystonia or writer's cramp, CON-09), unless enrolled in a dedicated stratum;
  - severe arthritis, or hand surgery in the last 6 months;
  - open skin lesions on the writing hand;
  - inability to consent. Cognitive screening (MoCA) is recorded; exclusion is only for lack of capacity or inability to follow task instructions;
  - **for studies with the actuated pen (H04, H06, B06 in-pen part):** active implantable medical devices (pacemaker, ICD, deep-brain stimulator) until a documented magnetic-field assessment against the device manufacturers' guidance permits inclusion. The pen contains NdFeB magnets of about 1–1.4 g each (CAD Rev A). Participants with DBS may join EXP-H01 (the passive pen carries only a small sense magnet), with the stimulator setting recorded and never changed for the study.

### 3.3 Consent, capacity and participant information

- Written informed consent before any procedure. Plain-language information states that:
  - the device is investigational and has no proven benefit;
  - it does not diagnose;
  - participants may stop at any time;
  - which data are collected, including handwriting samples, which can be identifying.
- Separate, **optional** consent items:
  - (i) re-use of recordings in future research;
  - (ii) sharing de-identified datasets with other researchers;
  - (iii) use of recordings to train or evaluate commercial models. Licensed or self-collected data with consent covering training are the only route to a shipped recogniser or predictor (COR-22; OPT notes §2.3).
- Large-print forms and extra time for participants with PD.

### 3.4 Safety: definitions, monitoring and stopping rules

- **Definitions (ISO 14155):**
  - adverse event (AE);
  - adverse device effect (ADE);
  - serious AE / serious ADE (SAE / SADE);
  - unanticipated serious ADE (USADE);
  - device deficiency.
- **Foreseeable risks with a powered pen:**
  - warm surfaces (limit 41 °C design, 43 °C absolute; REQ-THM-001);
  - hand or arm fatigue or pain;
  - perceptible vibration or reaction forces (COR-24: 0.1 N moves the barrel 0.1–0.2 mm, well above the 26 µm detection threshold, HAP-27);
  - unexpected nib motion on a fault (up to about 0.8 mm without mitigation, results/sim F3/F4);
  - frustration;
  - battery hazards for untethered pens.
  For PD OFF-medication sessions: discomfort, reduced mobility, falls.
- **Mitigations:**
  - gate G-S passed for the exact build;
  - the thermal governor, with surface temperature logged by the pen and checked by IR camera at the start of each session;
  - a USB isolator for tethered pens connected to mains-powered computers;
  - breaks every 15 min;
  - an investigator present for all laboratory sessions.
- **Participant-level stopping:**
  - on request;
  - heat or pain reported at ≥ 3/10;
  - skin redness persisting > 30 min;
  - any unexpected nib motion that the participant finds distressing;
  - Borg CR10 fatigue ≥ 7.
- **Study-level stopping:**
  - any SADE or USADE: halt, report to the ethics committee (and the competent authority where required) within the regulatory timelines, root-cause analysis, restart only after approval;
  - two or more related ADEs of the same type: pause and review by the independent safety monitor;
  - any logged held-surface temperature ≥ 43 °C, or any unexplained actuation fault: pause device use until fixed and G-S is re-verified.
- **Independent safety monitor** for H04 and H06: a clinician not otherwise involved, reviewing blinded AE listings every 10 participants and after any SAE.

### 3.5 Randomisation and blinding

- Computer-generated allocation with concealment (a web system, or sealed opaque envelopes prepared by a person not involved in enrolment). Block sizes vary at random. Stratification is as stated per study.
- The **study app sets device modes from coded allocation**, so the investigator in the room can be blinded to ON vs NEUTRAL.
- **Outcome assessors are always blinded:** scans and videos are coded and shown in random order; hands only, no faces.
- Participant blinding is assessed after each period (a guess plus confidence) and summarised with Bang's blinding index.

### 3.6 Outcome-measure definitions

| Measure | Definition |
|---|---|
| **Nib (or ink) tremor amplitude, excess-power method** | Displacement PSD S_p(f) of the nib (or deposited-ink) page trajectory per axis (Welch, 4 s Hann windows, 50 % overlap, pen-down segments). S_ref(f) = median PSD of the healthy-adult group for the same task, scaled to the participant's letter height; leave-one-out for healthy participants. Band = f_pk ± 1.5 Hz, where f_pk is the frequency of the largest ratio S_p/S_ref in 3–12 Hz. A_rms = √(∫_band max(0, S_p − S_ref) df); A_pp = 2√2·A_rms (sinusoid-equivalent peak-to-peak). The **major-axis** value uses the principal eigenvalue of the 2 × 2 cross-spectral matrix integrated over the band. The "per axis" limit of REQ-USR-002 is applied to the major axis (conservative). Before use, the method must recover known amplitudes injected into EXP-E01-A semi-synthetic recordings (method qualification). |
| Tremor frequency | f_pk as above; also the tracked frequency f_est from the pen's estimator (ICD research frame). |
| Path distance (guided tasks) | RMS over in-contact ink points of the distance to the nearest template point (as `sim/guided_eval.py`), from scans registered to the page. |
| Clinical ratings | **Fahn–Tolosa–Marín** (FTM) part B handwriting and drawing (spiral) items; **TETRAS** performance items for spirals, handwriting and dot approximation (PDT-14). Rated from scans or video by a movement-disorders clinician blinded to condition. MDS-UPDRS Part III (PD) and Part II item 2.7 (handwriting, patient-reported) as descriptors. |
| Micrographia | Mean x-height of a standard sentence (mm, from scans). Progressive slope = linear regression of stroke or letter height over serial position (PDT-05, PDT-06). Consistent micrographia is flagged by the −2 SD criterion of PDT-06. |
| SOS-test | Systematic Screening of Handwriting Difficulties, PD version (PDT-27): score (MDC 2.2 points) and speed (letters per 5 min, MDC 62 letters). |
| Legibility | Naive readers transcribe coded samples. Legibility = % of words transcribed correctly. Also a 1–5 rating. |
| Writing speed | Letters per minute (sentence copy); mean pen-down speed (mm/s). |
| Fluency | Normalised jerk and velocity peaks per stroke (HAP-10, PDT-17). |
| Shape error (novices) | Dynamic-time-warping distance between the written glyph and the template, normalised to glyph height. |
| User-reported | Comfort VAS 0–100 mm; Borg CR10 hand/arm fatigue; sense of control and agency (7-point item, "the pen did what I intended"); NASA-TLX; QUEST 2.0 (satisfaction with assistive technology, end of study); preference ranking; free comments. |
| Device logs | ICD research frames or stroke samples: mode, authority g, gate state, f_est, N_mod, copper loss, t_coil, faults. |

### 3.7 Statistical principles

- The SAP for each study is written and pre-registered before enrolment.
  - H04 and H06 are registered as trials (ClinicalTrials.gov or ISRCTN).
  - H01, H02, H03 and H05 are pre-registered on OSF.
- Estimands are defined per ICH E9(R1). Intercurrent events are listed per study (device fault → safe state, protocol mode errors, drop-out).
- Missing data: mixed models under MAR, with sensitivity analyses (per-protocol, and multiple imputation with delta adjustment).
- Multiplicity: pre-specified hierarchical (fixed-sequence) testing, or Holm, as stated per study.
- Reporting: STROBE (H01), CONSORT with the crossover extension (H06) or parallel (H04), with results **per user group**. Negative results are published.

---

## 4. EXP-H01: Tremor-at-nib census with an instrumented passive pen

### Question and what it gates

How large is tremor at the nib during natural writing, per axis and in millimetres, and at what frequency, for people with ET, people with PD, older adults and healthy adults? No study provides this. Spirals on tablets (n = 18) are the only per-patient displacement data (PDT-12), and tablets are accurate only to ±0.25 mm.

It is research question rank 2. The census sets the addressable population and the stage travel.

- **Requirements:** REQ-USR-002, whose "≤ 1 mm p-p full / ≤ 2 mm partial" is currently a literature-based estimate; REQ-MECH-001 (altitude envelope).
- **Decisions:** DEC-002 (claims by group and mechanism); DEC-009, since the frequency distribution vs the 7.5 Hz gate decides who free-writing cancellation can help.
- **Downstream uses:**
  - the recordings for EXP-E01 and E02 (causal separability on real writing);
  - the disturbance set for EXP-B09;
  - inputs to EXP-C01;
  - the eligibility criteria and **the screening yield (feasibility) of EXP-H06**.
- **Also measured:** writing force, altitude, azimuth, roll and speed distributions (CON notes §2.4 item 6), which replace assumption-based parameters.

There is no assistance and no intervention: the pen is passive.

### Population

- **ET: n = 20**, extendable to 40 by the adaptive rule below. Stratified by self-reported writing difficulty (yes/no). Usual medication, with the time of the last dose, caffeine and alcohol recorded.
- **PD: n = 20**: 10 tremor-dominant and 10 akinetic-rigid/PIGD, tested ON medication.
  - Optional OFF sub-study, n ≈ 10: practically defined OFF (≥ 12 h without dopaminergic medication) under neurologist supervision, with separate consent.
  - Only 3 of 10 OFF patients showed 4.4–8 Hz tremor while writing in PDT-10, so the OFF data are descriptive.
- **Older adults (≥ 65, no neurological diagnosis): n = 20.**
- **Healthy adults (18–64): n = 20**, balanced by sex and handedness where possible. They provide the normative writing spectrum S_ref and the control recordings for EXP-E01 false correction.
- **Retest:** 10 per group within 2 weeks, for reliability.
- Inclusion and exclusion as in §3.2. Participants with DBS may take part; the stimulator setting is recorded and not changed.

### Instrumentation

**The instrumented passive pen (to be built; no actuator):**

- the Rev A form: Ø15 mm, 150 mm, 30–35 g, CoM about 75 mm from the tip, so that grip and mass match the future device;
- a D1 refill rigidly mounted on a 0–5 N axial load cell;
- a 6-axis IMU at ≥ 1 kHz;
- the optical module(s) selected in EXP-S01;
- a ≤ 3 g marker cluster on the tail for motion capture;
- a USB tether through a medical-grade isolator;
- logs in the ICD research-frame format, with the stage fields set to zero.

**References:**

- optical motion capture (≥ 250 Hz, ≤ 0.05 mm accuracy in a 0.3 m volume). The nib position comes from the rigid-body transform calibrated with a pivot procedure;
- paper on an EMR digitiser for timing;
- 4800 dpi scans of every page (bench rig R3);
- the reference chain must agree with the scanned ink to ≤ 50 µm RMS (AC-H01-08; PDT notes §2.7 require ≥ 200 Hz and 0.05 mm).

### Tasks (about 90 min including consent and ratings)

1. Standard sentence copying, 3 repetitions, at natural size; then on 1.0 cm guide lines (PDT-18).
2. Free writing for 2 min: describing a neutral picture. Participants are asked not to write personal information.
3. Archimedes spirals: template-free and traced on a printed template, with the dominant hand and the pen; both hands on plain paper for FTM/TETRAS ratings.
4. Line drawing between targets.
5. Dot-hold: nib held on a dot for 10 s, 3 times. Hover: 5 mm above the paper for 5 s, 3 times.
6. Human feature course: corners, dots, hatching, fast strokes, circle and spiral, as `stabpen/signals.py::feature_course`, printed as a template.
7. "el" loops, 2 lines (a PD micrographia task, PDT-17/20).
8. Numbers and dates, for EXP-C01.
9. Optional: the EXP-B06 impedance module (subset, exploratory).

The order is fixed, with tasks 1 and 3 repeated at the end to measure fatigue drift.

### Outcomes

- **Primary:** per participant, nib tremor amplitude during sentence copying, major principal axis, peak-to-peak (§3.6 excess-power method). Per group, the fraction at ≤ 0.25, 0.5, 1, 2 and 4 mm p-p (PDT notes §2.7), with 95 % CIs.
- **Secondary:**
  - tremor peak frequency, and the fraction ≥ 7.5 Hz (the DEC-009 gate);
  - per-axis amplitudes (page x, y; pen t1, t2) and 3–12 Hz RMS;
  - dot-hold, hover and spiral amplitudes. Spirals are also analysed with the Elble & Ellenbogen tablet method for comparison with PDT-12;
  - the healthy intended-motion velocity spectrum (4–7 Hz fraction; COR-28 rests on a single writer);
  - axial force: mean, SD, p95, p99, and drift over the session;
  - altitude, azimuth and roll distributions, and regrip events;
  - letter height and progressive slope (PD);
  - writing speed;
  - FTM and TETRAS ratings and their relation to nib amplitude (the rating-to-mm calibration missing in the literature, PDT notes §2.6 item 2);
  - test–retest ICC(2,1) of nib amplitude.

### Sample size

- The quantity with a decision attached is the fraction of ET participants within 1 mm p-p (REQ-USR-002), and the addressable fraction (≤ 2 mm and f ≥ gate; AC-H01-04).
- With the PDT-12 log-normal model (geometric mean 2 mm, σ_log10 = 0.65, expected fraction 0.32), the 95 % CI of the fraction ≤ 1 mm at n = 20 is:
  - 0.18–0.50 by the delta method on the log-normal fit;
  - 0.16–0.54 by the Wilson method.
- This is no narrower than today's literature range (15–50 %), although it is the first measurement **at the nib during writing**.
- At n = 40 the CIs are 0.22–0.45 (log-normal) and 0.20–0.48 (Wilson). At n = 60, 0.23–0.42.
- **Adaptive rule (pre-specified, estimation only, so no α adjustment):** after 20 ET participants, if the 95 % CI of the addressable fraction straddles the decision threshold of AC-H01-04, recruitment continues to 40 ET.
- The frequency fraction is expected to be small (about 10 %). With 20 ET participants the expected count above the gate is 2, so the H06-F screening yield will only be estimated roughly. This is another reason for the extension.
- The other groups (n = 20) are sized for descriptive distributions and the normative spectrum.

### Analysis

1. Descriptive statistics per group: log-normal fit and empirical CDF; fractions below the thresholds with bootstrap CIs.
2. Mixed model: log amplitude ~ task × group + (1 | participant).
3. Frequency histograms against the gate; the joint amplitude–frequency distribution (the addressable region).
4. Relation of FTM/TETRAS ratings to log nib amplitude, compared with the spiral slope of PDT-12 (log₁₀ T = 0.6·FTM − 1.27).
5. ICC(2,1) from the retest subset.
6. **Dataset creation for EXP-E01 under REQ-DATA-001:** participant-level splits made before any windowing, hashes recorded, the test split locked.

### Adverse events and stopping

Minimal risk: writing tasks and fatigue. The optional OFF sub-study carries OFF-state discomfort and fall risk. It is supervised by a neurologist, the participant stays seated, the session stops on request or on any distress, and medication is given immediately at the end.

### Acceptance criteria

<!-- AC-TABLE:EXP-H01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H01-01 | REQ-USR-002 | Fraction of ET participants with nib tremor ≤ 1 mm p-p (major principal axis, excess-power method, sentence copying), with 95 % CI | within 15-50 % | hypothesis | PDT-12 log-normal fit (~30 %, plausible 15-50 %; spirals, tablet) | REQ-USR-002; DEC-002 |
| AC-H01-02 | REQ-USR-002 | Fraction of ET participants with nib tremor ≤ 2 mm p-p (same method) | within about 50 % (report with CI) | hypothesis | PDT-12 log-normal fit (derived ~50 %) | REQ-USR-002 partial-correction claim |
| AC-H01-03 | REQ-CTRL-007 | Fraction of ET participants whose writing-tremor peak frequency at the nib is ≥ 7.5 Hz (DEC-009 default gate) | ≤ 20 % | hypothesis | derived: ET frequency 5.79 ± 1.32 Hz (Elble 2000, screened in docs/research/notes/PDT_pd_et_handwriting.md s1.2) gives P(f ≥ 7.5 Hz) ~ 10 % | DEC-009; scope of free-writing cancellation |
| AC-H01-04 | — | Fraction of ET participants in the addressable region for free-writing cancellation (nib tremor ≤ 2 mm p-p AND peak frequency ≥ f_gate) | ≥ 25 % (placeholder; lead to confirm before unblinding) | hypothesis | engineering judgement placeholder for a programme decision threshold | DEC-001, DEC-008, DEC-009 programme scope |
| AC-H01-05 | — | Fraction of participants whose 99th-percentile axial writing force is ≤ 4 N | ≥ 95 % | hypothesis | CON-01 and COR-26 (heavy writers to about 4 N axial, derived high case) | REQ-ACT-001 envelope; EXP-B01 sweep range |
| AC-H01-06 | — | 2.5-97.5 % range of pen altitude during writing, pooled across participants | within 35-80° | hypothesis | CON-12 (47-77° on tablets), CON-02 (~50° on paper); config writing.tilt_deg 35-75° | config writing.tilt_deg; REQ-MECH-001 envelope (COR-26) |
| AC-H01-07 | — | Median fraction of intended velocity energy in 4-7 Hz in healthy participants' sentence copying | within 0.10-0.25 | hypothesis | CON-25 (single writer, derived ~17 %); CON-10 (36 % of angular-velocity power in 4-7 Hz in older adults); range engineering judgement | DEC-009; EXP-E01 benchmark |
| AC-H01-08 | — | Reference-system qualification: RMS difference between motion-capture-derived nib position and the scanned ink centreline | ≤ 50 µm | derived | PDT notes s2.7 (instrumentation ≥ 200 Hz and 0.05 mm accuracy) | validity of EXP-H01 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-H01).
<!-- AC-TABLE:EXP-H01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| ET fraction ≤ 1 mm far below 15 % | REQ-USR-002's population is too small for a correction product. DEC-002 narrows the claims; the programme weight shifts to guided, training and capture features (DEC-001, DEC-008). |
| Addressable fraction (≤ 2 mm and ≥ gate) below the AC-H01-04 threshold | Free-writing cancellation is not a product feature unless EXP-E01 lowers the gate. EXP-H06 runs its guided variant (H06-G). |
| PD tremor at the nib mostly < 0.1 mm while writing | PD claims stay limited to micrographia cueing and practice (EXP-H04-B). |
| Altitude or force distributions outside the configured ranges | Update `config/parameters.yaml` (`writing.*`), the EXP-B01 grid and REQ-MECH-001's envelope, then re-run the Monte Carlo. |
| Healthy 4–7 Hz velocity fraction ≫ 17 % | Separability is worse than simulated. This supports DEC-009 and lowers the expectation for EXP-E01. |

---

## 5. EXP-H02: Form factor and writing feel with the unpowered pen

### Question and what it gates

Is the research-pen form acceptable for comfort, fatigue, speed and legibility compared with ordinary pens? The form is Ø15 mm grip, a 16 mm bulge, 34–40 g and a centre of mass 74–81 mm from the tip (`results/mechanics/mass_budget.json`).

Does moving the centre of mass forward matter enough to justify redesign? This informs REQ-FORM-001…004 and open issue M-1. It also serves as a formative usability evaluation (IEC 62366-1).

### Population

n = 40: 10 ET, 10 PD, 10 older adults, and 10 healthy adults, including at least 3 regular drawing users (REQ-USR-001 group d). Inclusion and exclusion as in §3.2.

### Design

Randomised 4-period crossover. The order follows a Williams design for 4 treatments (4 sequences, 10 participants each). The pens:

| Pen | Description |
|---|---|
| A | Research-pen form: an unpowered mass- and CoM-matched mock-up of Rev A.1 with a polymer rear barrel (≈ 34 g, CoM ≈ 74 mm) |
| B | The same shell with the ballast moved forward (CoM ≈ 66 mm, ≈ 30 g) |
| C | A standard ballpoint (≈ 10 g), the reference |
| D | A wide-grip weighted assistive pen |

- Each period: 10 min of copying text, plus a 2 min drawing task, then ratings.
- Participants are not told the hypotheses. Assessors (legibility, scans) are blinded.
- ET participants use the H01 sensor package inside the mock-ups (A, B), so that nib tremor with each mass distribution is measured. This is exploratory: PDT-21 found that a weighted pen *increased* variability in PD, while inertial loading reduced postural tremor in ET (PDT-22).

### Outcomes

- **Primary:** comfort VAS (0–100 mm) after each pen. Key contrast: A − C.
- **Secondary:**
  - B − A (the effect of the centre of mass);
  - Borg CR10 fatigue;
  - preference ranking (Bradley–Terry);
  - writing speed;
  - legibility;
  - grip-diameter acceptability;
  - nib tremor (ET, exploratory).

### Sample size

- Equivalence of A and C (TOST), paired.
- Assumptions: SD of the paired difference σ_D = 20 mm (engineering judgement); equivalence margin ±10 mm (VAS minimal important difference convention); α = 0.05 per one-sided test; power 0.80 at a true difference of 0.
- Normal approximation: n = (z₀.₉₅ + z₀.₉₀)² · (σ_D/Δ)² = (1.645 + 1.282)² × 4 = 34.3.
- Exact t-based TOST: n = 36. With 10 % attrition → **40**.
- A blinded internal pilot re-estimates σ_D after 12 participants.

### Analysis

- Mixed model: VAS ~ pen + period + (1 | participant) + group.
- TOST 90 % CI for A − C; CI for B − A.
- Per-group descriptive results (not powered).

### Acceptance criteria

<!-- AC-TABLE:EXP-H02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H02-01 | REQ-FORM-003 | Comfort VAS (0-100 mm) after 10 min of writing: research-pen form (unpowered) minus the participant's reference pen, paired; 90 % CI of the difference | within within ± 10 mm | hypothesis | engineering judgement (VAS minimal important difference ~10 mm convention) | REQ-FORM-003/004 revision (M-1) |
| AC-H02-02 | REQ-FORM-004 | Comfort VAS difference between CoM variants of the same shell (74 mm vs 66 mm, ballast moved), paired 90 % CI | within within ± 10 mm | hypothesis | engineering judgement; mechanics/README.md M-1 | REQ-FORM-004 revision |
| AC-H02-03 | REQ-FORM-001 | Proportion of participants rating grip diameter 'acceptable' or better | ≥ 80 % | hypothesis | engineering judgement | REQ-FORM-001 |
| AC-H02-04 | — | Writing speed with the research-pen form relative to the reference pen (ratio, lower 95 % bound) | ≥ 0.90 | hypothesis | engineering judgement (Micron users slowed 18-37 % with an active tool, ACT-02; the unpowered form must not add that burden) | form factor |
| AC-H02-05 | — | Hand/arm fatigue (Borg CR10) after 10 min, research form minus reference pen (mean difference) | ≤ 1 point | hypothesis | engineering judgement | mass and CoM |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-H02).
<!-- AC-TABLE:EXP-H02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| A equivalent to C | REQ-FORM-003 and REQ-FORM-004 may be relaxed to the measured acceptable range (with EXP-M03's benchmark). The CoM target ≤ 70 mm becomes "within ordinary-pen range". |
| B better than A by > 10 mm | Invest in the M-1 CoM options (a shorter pen, a lighter stator, moving the cell). |
| A worse than C beyond the margin | Form redesign before Stage C; H06 and H04 would otherwise be confounded by discomfort. |

---

## 6. EXP-H03: Skid feel and smear, blinded

### Question and what it gates

Configuration D has a nose skid that carries the user's writing force, with a constant-force nib (0.30 N in `results/thermal/thermal.json`). It would cut the actuator's holding power from about 0.48 W to about 0.07 W in contact (DEC-008).

Is it acceptable in writing feel, ink smear and paper marking? And does the skid's friction passively reduce tremor at the nib (research question rank 7; ACT-24 describes a passive pen whose friction and inertia grounded the nib)?

This study gates **DEC-008** (revisit trigger "EXP-H03 skid feel and smear study"). The prototypes are **non-active**: no actuator and no powered parts.

### Prototypes

Identical external shells (form A of EXP-H02):

| Prototype | Description |
|---|---|
| S1 | Skid ring (Ø ≈ 6 mm nose, low-friction polymer) + constant-force nib 0.30 N |
| S2 | Skid ring + 0.50 N nib |
| C | Control: the same shell, skid retracted 0.5 mm above the paper, rigid nib |

Skid material and geometry are design inputs (engineering judgement); two skid geometries may replace S2 if the pilot favours one force.

### Populations

- **H03-F (feel and smear), n = 22:** healthy adults and older adults (balanced), with **≥ 30 % left-handed writers**. Left-handers push the nose through fresh ink, which is the worst smear case.
- **H03-T (passive tremor), n = 20 ET** with measurable writing tremor (≥ 0.25 mm p-p at the nib in a screening recording). Instrumentation: the EXP-H01 sensor package in the shells.

### Design

- Randomised order (Latin square across S1, S2, C), two rounds. Each round: 3 min of copying a standard text and 1 min of drawing, per prototype.
- Participants are told only that "the pens differ in their tips"; the shells are identical.
- The operator hands the pens over from coded boxes.
- Smear and skid-mark assessment from scans is blinded.

### Outcomes

- **Primary H03-F:** writing-feel acceptability (0–10) after each prototype; contrast S1 − C.
- **Primary H03-T:** geometric-mean ratio of nib tremor amplitude, S1 / C (§3.6).
- **Secondary:**
  - perceived drag and stability ratings;
  - 2AFC preference within pairs;
  - smear index (ink area outside the nominal line band per mm of line);
  - visible skid marks;
  - writing speed;
  - legibility.

### Sample size

- **H03-F (non-inferiority, paired).** Assumptions: σ_D = 1.5 points (engineering judgement); margin 1.0 point; one-sided α = 0.025; power 0.80; true difference 0.
  - Normal approximation: n = (1.960 + 0.842)² × (1.5/1.0)² = 17.7.
  - Exact t: **n = 20**. With 10 % attrition → **22**.
  - `docs/research_questions.md` proposes n ≈ 12. Under these assumptions n = 12 has only **56 % power**.
  - A blinded internal pilot at n = 8 re-estimates σ_D.
- **H03-T (paired, log scale).** Detect a 20 % reduction (ratio 0.8) with an SD of log-ratio 0.3 (assumption), two-sided α = 0.05, power 0.80.
  - Normal approximation: 14.2. Exact t: **n = 17**. With attrition → **20**.

### Analysis

- Paired t (or Wilcoxon with a Hodges–Lehmann CI) for the rating difference, with the one-sided 97.5 % lower bound compared to −1.0.
- Log-ratio paired t for tremor and smear.
- Mixed models with round and order effects.

### Acceptance criteria

<!-- AC-TABLE:EXP-H03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H03-01 | — | Writing-feel acceptability (0-10) of the skid prototype vs identical-shell control, paired: one-sided 97.5 % lower bound of the difference | > -1.0 point | hypothesis | non-inferiority margin engineering judgement; sample size in human_study_plan.md | DEC-008 (configuration D) |
| AC-H03-02 | — | Smear index (ink area outside the nominal line band per mm of line, blinded scan analysis), skid / control, upper 95 % bound | ≤ 1.2 | hypothesis | engineering judgement | DEC-008 |
| AC-H03-03 | — | Passive tremor effect in ET: geometric-mean ratio of nib tremor amplitude, skid / control | ≤ 0.8 | hypothesis | research question rank 7 (hypothesis that skid friction passively reduces tremor); ACT-24 (friction and inertia grounded the nib in a passive pen) | DEC-008 value case |
| AC-H03-04 | — | Samples with skid marks visible on paper (blinded rater, 1:1 scan) | ≤ 10 % | hypothesis | engineering judgement | DEC-008 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-H03).
<!-- AC-TABLE:EXP-H03:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| S1 non-inferior, smear and marks acceptable | Configuration D proceeds to an actuated Stage D prototype (DEC-008). This also depends on EXP-B01 N_min ≤ 0.30 N and EXP-B08 at 0.30 N. |
| Feel inferior or smear unacceptable | D is dropped. E (slow zero-hold bias actuator) or B remains, with its thermal limits (DEC-008). |
| Passive tremor ratio ≤ 0.8 | A passive-assistance value case for D, to be confirmed in an EXP-H06-type crossover with D prototypes. |

---

## 7. EXP-H04: Training and lasting improvement

### Question and what it gates

Does practice with the pen's training modes improve **unassisted** writing, with retention and transfer? And does error-removing assistance impair it, as the guidance literature warns (HAP-09: error-minimising channel guidance gave the worst unassisted retention and transfer; HAP-02, HAP-04, HAP-06)?

This is the **lasting-improvement** evidence (REQ-VAL-002). It gates any training-mode claim, and the design of TRAINING_FADE (`docs/icd.md` §6) and of the cueing features for PD micrographia (DEC-002).

There are two parallel trials:

- **H04-A (mechanism, healthy novices):** does fading guidance or error amplification change unassisted learning of unfamiliar glyphs?
- **H04-B (clinical, PD with micrographia):** does practice with the pen's fading size cues, or with error-amplified size feedback, increase unassisted letter size at retention compared with matched conventional practice?

The nib cannot enlarge strokes (±0.5 mm), so H04-B uses cueing and feedback, not correction (COR-10).

### H04-A: novices learning unfamiliar glyphs

**Population.** Healthy adults aged 18–64, naive to the chosen script: 20 glyphs from a script unfamiliar to the local population, presented at 6–8 mm height. Exclusions as in §3.2.

**Arms (parallel, 1:1:1):**

| Arm | Practice condition |
|---|---|
| Control | Same practice with the pen in NEUTRAL, template shown, knowledge of results after each trial |
| Faded guidance (FG) | GUIDED / TRAINING_FADE: template-following correction whose gain fades with performance, P_i = f·P_(i−1) + g·e_i with f < 1 (HAP-03); a continuous gain from 0 to 1 (HAP-21); 20 % catch trials without assistance (HAP-08) |
| Error amplification (EA) | The nib displaces the ink away from the template by (k − 1) × the current deviation, with k = 1.5, capped by the ±0.5 mm workspace. This is visual error augmentation through the nib, which is untested (HAP notes §2.2 rule 5) |

FG and EA need page registration (coded paper or an external reference).

**Schedule.**

| Day | Activities |
|---|---|
| 1 | Baseline test (unassisted); practice session 1 (30 min) |
| 2 | Practice session 2 (30 min); immediate retention test |
| 9 | **Delayed retention** (7 days after practice) and transfer tests: untrained glyphs; mirror-image glyphs; the trained glyphs with an **ordinary pen** |

**All tests are unassisted**, with the research pen in NEUTRAL_HOLD so the instrument is held constant, except the ordinary-pen transfer test.

**Outcomes.**

- **Primary (LI):** unassisted shape error (normalised DTW) at 7-day retention.
- **Secondary:**
  - immediate retention;
  - the three transfer tests;
  - velocity peaks per glyph (fluency);
  - movement time;
  - pen lifts;
  - legibility by naive raters;
  - interest and enjoyment (IMI subscale; error amplification lowered enjoyment in Marchal-Crespo 2017, HAP notes §1).
- Acquisition (assisted) performance is reported **separately** and labelled IA-during-practice (rule R4).

**Sample size.**

- Two primary comparisons (EA vs control; FG vs control), with Holm.
- Planning α = 0.025 two-sided per comparison. Standardised effect d = 1.0: a conservative reading of HAP-09's group effects, partial η² 0.29–0.36, n = 9 per group. Power 0.80.
- Normal approximation: n per arm = 2 · (z₀.₉₈₇₅ + z₀.₈₀)² / d² = 2 × (2.241 + 0.842)² = 19.0.
- Exact t: **21 per arm**. With 10 % attrition → **24 per arm, 72 in total**.

**Analysis.**

- ANCOVA: shape error at 7 days ~ arm + baseline shape error.
- EA vs control: superiority (AC-H04-02).
- FG vs control: **non-inferiority** with a 0.3 SD margin (AC-H04-03). FG is not expected to help; the risk being tested is harm.
- Holm across the two primary tests.
- ITT with multiple imputation; per-protocol sensitivity analysis.

### H04-B: PD with micrographia (feasibility first, then efficacy)

**Population.** Clinician-confirmed PD, Hoehn & Yahr 1–3, on stable medication for ≥ 4 weeks, tested ON.

- Micrographia is present: consistent (mean x-height below −2 SD of age-matched norms, PDT-06 criterion) or progressive (size-decrement slope beyond −2 SD; PDT-05, PDT-06).
- MoCA recorded. Participants must be able to follow the home programme (PDT-17 found that jerk increases after amplitude training correlated with lower MMSE).
- Exclusions as in §3.2, plus: DBS programming changes planned during the study; tremor that prevents pen–paper contact.

**Arms (parallel, 1:1:1):**

| Arm | Practice condition |
|---|---|
| Control | Matched conventional practice: the same daily writing programme with the pen unpowered on paper with **1.0 cm target lines**, the evidence-based cue (PDT-18: 1.0 cm lines improve size immediately; 0.6 cm lines shrink writing) |
| Faded cueing (FC, "fading guidance" for size) | The pen's haptic cue (ERM) and a post-stroke app cue when letter height falls below the participant's target. Cue frequency fades with performance, with 20 % cue-free catch blocks (HAP-08). Feedback is delivered **after** strokes, not during them (HAP-30) |
| Error-amplified feedback (EAF) | Post-stroke visual feedback in the app shows the size shortfall amplified (k = 1.5). This tests error amplification for amplitude (HAP-05: dynamic transformations can profit from error-amplifying information) |

**Dose.** 30 min/day, 5 days/week, 6 weeks at home with the untethered pen (Stage C), plus a weekly supervised session. This mirrors the intensive programme of PDT-16. Adherence is logged by the pen.

**Tests (all unassisted, with an ordinary ballpoint on the digitiser, then scanned):**

- baseline;
- end of training (week 6);
- **retention at week 12** (6 weeks after the end);
- transfer tasks: untrained sentences; dual-task writing (writing while counting backwards); a daily-life sample (a shopping list); the SOS-test.

**Outcomes.**

- **Primary (LI):** change from baseline in mean x-height of a standard sentence written unassisted with an ordinary pen at 6-week retention.
- **Secondary:**
  - size-decrement slope;
  - SOS-test score (MDC 2.2 points) and speed (MDC 62 letters per 5 min; PDT-27);
  - writing speed;
  - fluency: normalised jerk. Amplitude training can reduce fluency (PDT-17), hence the fluency-guard criterion AC-H04-05;
  - legibility;
  - MDS-UPDRS II item 2.7;
  - adherence;
  - QUEST 2.0;
  - AEs.
- **An immediate cueing effect** (cue on vs off within the baseline session) is recorded as an **IA** measure. It is reported separately and is never used for the LI claim.

**Sample size (efficacy trial).**

- Assumptions (to be replaced by feasibility data):
  - between-arm difference in letter-height change at retention δ = 10 % of baseline size (within PDT-16's 7–17 %);
  - SD of change σ = 15 %;
  - baseline–outcome correlation ρ = 0.6, so ANCOVA multiplies the variance by 1 − ρ² = 0.64 and the effective SD is 12 %, giving d = 0.83;
  - α = 0.025 two-sided per comparison (Holm, 2 comparisons); power 0.80.
- Normal approximation: 2 × (2.241 + 0.842)² / 0.83² = 27.4. Exact t: **29 per arm**. With 15 % attrition → **34 per arm, 102 in total**.
- Without the ANCOVA gain: 45 per arm.
- **Feasibility trial first:** 12 per arm (36). It is not powered for efficacy. Progression criteria to the efficacy trial:
  - recruitment ≥ 3 per month per site;
  - adherence ≥ 70 % of prescribed sessions;
  - retention ≥ 85 % at week 12;
  - no SADE;
  - an SD estimate for the efficacy sample size.

**Analysis.** ANCOVA and MMRM (visits: week 6, week 12); Holm; ITT with multiple imputation; per-protocol sensitivity analysis; fluency guard.

### Adverse events and stopping (H04)

- Hand pain or fatigue, frustration, and device heat (logged by the pen; the governor limits it).
- Home use requires the untethered pen to have passed G-S and G-C (battery safety, EXP-P02).
- The independent safety monitor reviews at 50 % and 100 % of the feasibility trial. Stopping rules as in §3.4.

### Acceptance criteria

<!-- AC-TABLE:EXP-H04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H04-01 | REQ-VAL-002 | Protocol conformity: primary outcome measured unassisted (device off or ordinary pen) at delayed retention; assisted performance reported separately and never pooled with it | conforms | requirement | REQ-VAL-002 | training-mode (lasting improvement) claims |
| AC-H04-02 | — | H04-A primary: unassisted shape error (DTW) at 7-day retention, error-amplification arm vs control (ANCOVA on baseline, Holm-adjusted) | 95 % CI excludes 0 in favour of EA | hypothesis | HAP-09 (error-reducing guidance gave the worst retention; error amplification better), HAP-08 (skill-dependent) | training-mode design; lasting-improvement claim |
| AC-H04-03 | — | H04-A: unassisted shape error at 7-day retention, faded-guidance arm vs control: non-inferiority, upper 95 % bound of the standardised difference | ≤ 0.3 SD | hypothesis | HAP-02/HAP-09 (guidance can harm retention); margin 0.3 SD engineering judgement | whether faded guidance may be offered as training |
| AC-H04-04 | — | H04-B primary (PD micrographia): unassisted letter-height change from baseline at 6-week retention, each active arm vs control (ANCOVA, Holm) | 95 % CI excludes 0 in favour of the active arm | hypothesis | PDT-16 (7-17 % size gains with amplitude training, retained 6 weeks, with transfer) | lasting-improvement claim for PD cueing/practice |
| AC-H04-05 | — | Fluency guard: normalized-jerk change vs control at retention (upper 95 % bound of the standardised difference) | ≤ 0.3 SD | hypothesis | PDT-17 (amplitude training increased jerk and stroke duration); margin engineering judgement | training-mode design |
| AC-H04-06 | — | Mean SOS-test improvement in the best active arm at retention | ≥ 2.2 points | derived | PDT-27 (SOS-test MDC 2.218 points) | clinical relevance of a lasting-improvement claim |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-H04).
<!-- AC-TABLE:EXP-H04:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| FG worse than control at retention | Error-removing training is harmful as the literature warns. TRAINING_FADE is not offered as a learning mode; assistance is presented only as IA. |
| EA better than control | Error amplification becomes the training mode, with enjoyment and acceptance monitored. |
| H04-B active arm superior at retention with SOS gain ≥ MDC | A lasting-improvement claim for PD micrographia with that training programme (per group, per dose). |
| No difference from matched conventional practice | The pen offers no training advantage over paper and target lines. Training claims are dropped; the conventional programme remains the recommendation. |

---

## 8. EXP-H05: Perception thresholds for ink distortion, blinded pairs

### Question and what it gates

What changes to handwriting can people see? This study sets the numbers that are engineering judgement today:

- REQ-CTRL-005: 50 µm RMS intended-path distortion; 100 µm corner/dot error;
- REQ-MECH-005 and the EXP-B08 margins: ink-quality modulation;
- the value of partial tremor removal (REQ-USR-002 up to 2 mm; PDT notes §2.7 item 4).

An optional haptic part (H05b) measures the detection of barrel reaction forces during writing (COR-24; HAP notes §2.5 item 4).

### Population

- **H05a raters, n = 30:** adults aged 18–80 with normal or corrected vision, ≥ 10 of them aged ≥ 60.
- Optional: 10 writers from EXP-H01 judge their own writing.
- **H05b, n = 16:** healthy adults.

### Stimuli (H05a)

Scanned handwriting from EXP-H01 (healthy and ET) and feature-course scans from EXP-B09, manipulated in software:

1. **Intended-path distortion:** spatially smooth random displacement fields with the spectral content of estimator false corrections (from EXP-B09/E01 distortion outputs), 10–300 µm RMS on a log scale.
2. **Corner rounding and dot displacement:** 25–400 µm.
3. **Hatch smoothing.**
4. **Ink-quality modulation:** EXP-B08 scans at 0–0.3 N RMS.
5. **Tremor removal:** 0 / 25 / 50 / 100 % of the tremor component removed from ET samples with 1–2 mm p-p nib tremor.

Presentation: printed at 1:1 and 1200 dpi on the original paper type; viewing at about 35 cm under 500 lx; a calibrated display at 1:1 as secondary.

### Method

- 2AFC: "which of the two was altered?", with the unaltered original shown as reference.
- Adaptive staircase (a Bayesian adaptive method such as QUEST+ or Psi) targeting 75 % correct, about 60 trials per manipulation type per rater.
- Stimuli coded; raters naive to the hypotheses; trial order randomised.
- Plus a legibility and preference rating block.

### H05b (haptic, optional)

- The Stage B pen (after G-S) or the R6 shaker applies in-plane barrel vibrations at 5, 10, 20 and 50 Hz during writing, as a 2-interval forced-choice detection task.
- Annoyance ratings at 1×, 2× and 4× threshold.
- Hypothesis: median about 26 µm at 10 Hz (HAP-27, axial excitation).

### Sample size

- 30 raters give a 95 % CI of ±0.37 SD on the mean log-threshold (t₀.₉₇₅,₂₉/√30).
- The design limit is the **10th percentile** across raters (the most sensitive viewers), estimated from a log-normal fit to the per-rater thresholds.
- H05b with 16 participants is descriptive.

### Analysis

- Per-rater psychometric fits (Weibull, lapse 2 %) → thresholds.
- Mixed model of log-threshold ~ manipulation × age group.
- Population percentiles with bootstrap CIs.

### Acceptance criteria

<!-- AC-TABLE:EXP-H05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H05-01 | REQ-CTRL-005 | 2AFC detection threshold (75 % correct) for intended-path distortion (RMS) of handwriting at normal viewing, 10th percentile across raters | ≥ 50 µm | hypothesis | REQ-CTRL-005 (the 50 µm limit is adequate only if imperceptible) | REQ-CTRL-005 value |
| AC-H05-02 | REQ-CTRL-005 | 2AFC threshold for corner and dot displacement, 10th percentile across raters | ≥ 100 µm | hypothesis | REQ-CTRL-005 | REQ-CTRL-005 value |
| AC-H05-03 | REQ-MECH-005 | 2AFC threshold for ink-quality modulation (EXP-B08 stimuli), expressed as normal-force modulation, 10th percentile across raters | ≥ 0.15 N RMS | hypothesis | REQ-MECH-005 | REQ-MECH-005 value; EXP-B08 margins |
| AC-H05-04 | REQ-USR-002 | Proportion of raters who detect 50 % synthetic tremor removal on ET writing samples at 1 mm p-p tremor | ≥ 50 % | hypothesis | PDT notes s2.7 item 4 (perceptual threshold for partial removal); 50 % engineering judgement | value of partial correction (REQ-USR-002 up to 2 mm) |
| AC-H05-05 | — | Haptic detection threshold of in-plane barrel reaction during writing at 10 Hz (H05b), median across participants | within 26 µm ± factor 2 | hypothesis | HAP-27 (26 µm at 10 Hz, axial, pen-hold) | reaction shaping; COR-24 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-H05).
<!-- AC-TABLE:EXP-H05:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Distortion threshold (10th percentile) < 50 µm | REQ-CTRL-005 is too loose. Estimator tuning becomes more conservative, and the benefit shrinks (DEC-009). |
| Distortion threshold ≫ 50 µm | Assertive tuning becomes acceptable where it helps (for example KF-ASR at ≥ 9 Hz). |
| Ink-modulation threshold < 0.15 N | REQ-MECH-005 is lowered (EXP-B08, DEC-006). |
| 50 % removal of 1–2 mm tremor rarely detected | Partial correction (REQ-USR-002 up to 2 mm) has little visible value; claims restrict to full correction. |
| Haptic threshold ≪ predicted reactions | Reaction shaping becomes a controller requirement (HAP notes §2.3). |

---

## 9. EXP-H06: Immediate-assistance efficacy (device on vs neutral vs off)

### Question and what it gates

**With the device active**, is tremor in the deposited ink reduced compared with the same device powered but not correcting (a sham), and compared with the device off? This is the **immediate-assistance** evidence (REQ-VAL-002). It gates any IA claim (claim gate C-IA in `prototype_stages.md`) and informs DEC-008 (the value of active correction vs the product variants).

### Two pre-specified variants (the choice is fixed at gate G-C, before enrolment)

| Variant | Chosen if | Population | Primary task and outcome |
|---|---|---|---|
| **H06-F (free writing)** | EXP-E01 AC-E01-04 and EXP-E02 AC-E02-04 pass: causal cancellation above the gate works on recorded writing | ET or action tremor with nib tremor ≤ 2 mm p-p (major axis) **and** tracked tremor frequency ≥ f_gate | Standard sentence copying: ink tremor amplitude (§3.6 excess-power method applied to the deposited-ink trajectory from the stroke record, validated against scans) |
| **H06-G (guided tasks)** | otherwise, provided EXP-B09 AC-B09-12 passes | ET with nib tremor ≤ 2 mm p-p, any frequency | Guided tracing on registered pages (spiral, letter templates, writing inside form boxes): path distance to the template (M-path) |

- Each variant includes the other's tasks as secondary outcomes. In H06-G, free writing is a **no-harm** check: the gate must keep the device neutral below its frequency.
- **Feasibility note.** H06-F needs participants whose writing tremor is ≥ 7.5 Hz. From the ET frequency distribution (5.79 ± 1.32 Hz; about 10 % above the gate) and the amplitude distribution (about 50 % ≤ 2 mm), about 5 % of screened ET patients qualify if the two are independent. Enrolling 42 would need about **860 screened**. Unless EXP-H01 finds a higher yield or EXP-E01 lowers the gate, **H06-G is the realistic primary study.**

### Conditions

| Condition | Device state |
|---|---|
| ON | ASSIST_KF (H06-F), or GUIDED plus ASSIST_KF (H06-G) |
| NEUTRAL | NEUTRAL_HOLD: powered sham with the same warmth and sound, q_r = 0 |
| OFF | Actuation off, **stage mechanically locked** (rigid pen) |

The OFF condition needs a stage lock or a mass-matched rigid replica. Without a lock the unpowered nib rests at its stop under the contact load (COR-19). This is a Stage C design input.

### Design

- Randomised **3-period crossover**, Williams design (6 sequences for 3 conditions), in one session: a 5 min practice run-in, then three periods of about 12 min separated by 5 min rests.
- Task order is fixed within each period.
- A final **unassisted exploratory block** (OFF) tests after-effects (rule R3).
- A **pilot of 10 participants at Stage B** (tethered pen) checks procedures, blinding and variance before the full study at Stage C.

### Blinding

- Participants are not told which condition is active. ON and NEUTRAL are designed to be indistinguishable in heat and sound. Reaction forces may betray ON (COR-24), so the participant's guess is recorded after each period.
- The operator sees only coded conditions set by the app.
- Clinical raters and the ink analysis are blinded to condition.
- The primary outcome is kinematic and computed automatically, which limits bias from imperfect participant blinding.

### Population and eligibility

- **Tremor cohort (n = 42).** Adults aged 18–85 with clinician-diagnosed ET or other action tremor affecting writing, stable medication for ≥ 4 weeks.
  - A 2 min screening recording (EXP-H01 method) shows nib tremor between 0.25 and 2 mm p-p, major axis. The lower limit keeps the effect measurable; the upper limit is REQ-USR-002.
  - For H06-F, the tracked frequency must also be ≥ f_gate.
  - Exclusions: §3.2, plus tremor severe enough to prevent contact.
  - PD participants with action tremor may join an exploratory stratum. Tremor while writing is uncommon in PD (PDT-10), and PD claims are separate (R5).
- **Device-burden cohort (n = 12 healthy adults).** NEUTRAL vs OFF only, to test that the powered-but-idle device does not degrade normal writing. The simulated device distortion is 60–75 µm RMS (`results/sim/nominal/metrics.json`).

### Outcomes and testing hierarchy

1. **Primary (IA):** GM ratio ON / NEUTRAL of the variant's primary outcome (AC-H06-02). Descriptive wording thresholds are in AC-H06-03.
2. **Key secondary**, tested in sequence only if 1 succeeds (fixed-sequence testing preserves α):
   - (a) ON vs OFF, same metric;
   - (b) NEUTRAL vs OFF non-inferiority for device burden (legibility, speed; AC-H06-05).
3. **Secondary** (not in the hierarchy):
   - blinded FTM/TETRAS spiral and handwriting ratings (AC-H06-04);
   - legibility and speed;
   - the other variant's tasks;
   - sense of control and agency, comfort, preference, NASA-TLX, QUEST 2.0;
   - device logs: authority, gate state, N_mod, copper loss, temperature (AC-H06-07).
4. **Exploratory:** the unassisted block after the device periods; subgroups by amplitude (≤ 1 mm vs 1–2 mm) and frequency.

### Sample size (shown step by step)

- **Outcome:** y = ln(tremor measure); within-participant contrast D = y_ON − y_NEUTRAL.
- **Effect to detect:** a 30 % reduction, δ = ln(1/0.7) = 0.357. By PDT-11 (one rating point ≈ 2.6–2.8 × amplitude) this is about 0.35 rating points. By PDT-12 the tablet minimum detectable change is 51 % of the geometric mean for a single measurement; averaging over tasks and repetitions within a period reduces the noise.
- **Variability:** σ_D = 2δ = 0.71. This is the audit's planning assumption (COR-09).
- **Error rates:** α = 0.05 two-sided; power 0.80.

| Step | Calculation | Result |
|---|---|---|
| 1. Normal approximation | n = ((z₀.₉₇₅ + z₀.₈₀) · σ_D / δ)² = ((1.960 + 0.842) × 2)² | 31.4 → 32 |
| 2. Exact paired t (non-central t, iterated) | n = 34, achieved power 0.808 | **34** (matches `results/audit/audit_corrections.json` COR-09) |
| 3. Attrition, 15 % | 34 / 0.85 | 40 |
| 4. Sequence balance (6 Williams sequences) | round up to a multiple of 6 | **42** |
| 5. Sensitivity to σ_D | σ_D = 1.5δ → 20; 2δ → 34; 2.5δ → 52; 3δ → 73 | — |

- A crossover-period model uses the same within-participant variance, so these numbers apply to the mixed-model analysis.
- **Blinded sample-size re-estimation** at 50 % of enrolment uses the pooled within-participant SD; the effect is not unblinded. The maximum is capped at 73.

### Analysis

- Linear mixed model: ln(outcome) ~ condition + period + sequence + (1 | participant). The primary contrast ON − NEUTRAL is reported as a GM ratio with a 95 % CI.
- First-order carryover is checked. If it is material, a first-period-only (parallel) analysis is a sensitivity analysis.
- **Estimand** (ICH E9(R1)):
  - population: per the variant;
  - variable: the primary outcome;
  - intercurrent events: a device fault or safe-state entry during a period is handled "while on treatment" (the outcome uses data before the event; the event is reported). Missing periods are handled under MAR.
  - summary: GM ratio.
- The blinding index is reported; a sensitivity analysis excludes periods where the participant guessed the condition with high confidence.
- Results are reported per user group (REQ-USR-001).

### Adverse events and stopping

- As in §3.4. The session thermal log is checked for AC-H06-07.
- Any unexpected nib motion is reported as a device deficiency.
- The independent safety monitor reviews after the Stage B pilot and after every 10 participants.

### Acceptance criteria

<!-- AC-TABLE:EXP-H06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-H06-01 | REQ-VAL-002 | Protocol conformity: only immediate-assistance endpoints (performance with the device active); no lasting-improvement claim derived from H06 | conforms | requirement | REQ-VAL-002 | immediate-assistance claim |
| AC-H06-02 | REQ-USR-002 | Primary: geometric-mean ratio ON / NEUTRAL of the primary tremor outcome in the pre-specified variant (free-writing ink tremor amplitude, or guided-task path distance), upper 95 % CI bound | < 1.0 | hypothesis | superiority at two-sided alpha 0.05; sample size from COR-09 (n = 34 pairs for sigma_D = 2 delta) | immediate-assistance claim (C-IA); DEC-008 |
| AC-H06-03 | REQ-USR-002 | Primary outcome point estimate (GM ratio ON / NEUTRAL) needed to describe the effect as clinically meaningful | ≤ 0.7 | hypothesis | design effect size; about 0.4 FTM rating points via PDT-11 (one point ~ 2.6-2.8 x amplitude); engineering judgement | wording of the immediate-assistance claim |
| AC-H06-04 | — | Blinded FTM/TETRAS spiral and handwriting item ratings, ON vs NEUTRAL: median paired improvement | ≥ 0.5 point | hypothesis | PDT-11, PDT-12 (a 50 % amplitude reduction is about 0.7 rating points); engineering judgement | clinical corroboration of C-IA |
| AC-H06-05 | — | Device burden, NEUTRAL vs OFF, all participants: legibility (lower 95 % bound of the difference) / writing-speed ratio (lower 95 % bound) | ≥ ≥ -5 percentage points / ≥ 0.90 | hypothesis | engineering judgement; simulated device distortion 60-75 µm (results/sim/nominal/metrics.json) | DEC-006 (device distortion) |
| AC-H06-06 | — | Serious adverse device effects | = 0 | derived | ISO 14155 safety reporting; stopping rules in human_study_plan.md | study continuation |
| AC-H06-07 | REQ-THM-001 | Maximum logged grip temperature during sessions | ≤ 41 °C design / 43 °C absolute | requirement | REQ-THM-001 | G-S |
| AC-H06-08 | REQ-USR-001 | Results reported and claimed per user group; no pooled cross-group claim | conforms | requirement | REQ-USR-001 | claims |
| AC-H06-09 | REQ-USR-003 | Diagnostic or disease-scoring output shown to participants | = 0 | requirement | REQ-USR-003 | regulatory scope |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (9 rows for EXP-H06).
<!-- AC-TABLE:EXP-H06:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Primary succeeds (upper CI < 1) | An IA claim for the variant's task type and population (claim gate C-IA). It says nothing about learning. |
| Primary fails, with good blinding and device function | No IA benefit for that population at this design. DEC-008 weighs product variants and non-correction features. |
| NEUTRAL worse than OFF (device burden) | The suspended nib or the feel degrades writing. Re-open DEC-006 (axial path) and the form factor, whatever the result of ON. |
| Participants reliably detect ON | Blinding claims are weakened; report it. Reaction shaping (H05b) becomes a design priority. |

---

## 10. Ethics, regulatory and data-protection notes

These notes are for planning. The project lead must confirm each item with the institution's ethics office, a regulatory adviser and a data-protection officer for the jurisdiction where the studies run.

- **Ethics approval is required before any participant is enrolled.** That includes EXP-B06 (bench, participants), H01 (passive pen), H02 and H03 (non-active mock-ups), H05 (raters) and H04/H06 (active investigational device).
- **Investigational device.**
  - A pen intended to compensate for a disability (tremor) is likely to be a **medical device** by intended purpose. For example, the EU MDR definition covers "alleviation of, or compensation for, … a disability".
  - H04 and H06 are therefore likely to be **clinical investigations of a medical device**: EU MDR Art. 62 ff. / UK MDR 2002 / US 21 CFR 812 (an IRB significant or non-significant risk determination).
  - They follow **ISO 14155** (good clinical practice for device investigations). The device's risk file follows **ISO 14971**; firmware follows an **IEC 62304**-style process; usability follows **IEC 62366-1** (H02 and H03 serve as formative evaluations).
  - Electrical and thermal safety: **IEC 60601-1** or **IEC 62368-1**, as determined. Touch temperature ≤ 43 °C (AMF-34/35). The IEC 62368-1 table is still to be verified (AMF notes).
  - Skin-contact materials: **ISO 10993-1** evaluation for intact skin, limited or prolonged contact, or materials with a documented history of safe use.
  - Battery: IEC 62133-2 and UN 38.3 (EXP-P02).
- **No diagnostic claims** (REQ-USR-003).
  - The pen and app do not diagnose, score disease or infer a group (PDT notes §2.5).
  - Study measurements are research data and are not reported to participants as clinical findings.
  - Incidental-findings policy: if a healthy participant shows marked tremor, a scripted recommendation to consult their doctor is given, with no diagnostic statement.
- **Data protection** (for example GDPR / UK GDPR; health data are a special category).
  - A data protection impact assessment is done before the first study.
  - Pseudonymised participant ids, with the key held by the principal investigator, separate from the data.
  - Data minimisation: standard prompts; no personal content in free writing; video framed on hands only; no signatures (a pseudo-signature task instead).
  - Access-controlled storage in the approved jurisdiction; retention periods per `records/README.md`; participants' rights explained.
  - Optional consents as in §3.3, including model training. Withdrawal is honoured for data not yet incorporated into a released model, as stated in the consent.
- **Registration and transparency.** H04 and H06 are registered prospectively on a trial registry; H01, H02, H03 and H05 are pre-registered on OSF. Results are published per group, including null results.
- **Participant burden and accessibility.** Sessions ≤ 90 min with breaks; large-print materials; travel reimbursement; home visits for H04-B where needed.

---

## 11. Sample-size summary

| Study | n | Basis |
|---|---|---|
| EXP-B06 | 12 (≥ 8 per physics.md) | 95 % CI of mean ln K_n within about ±20 % at a between-participant CV of 30 % |
| EXP-H01 | 20 per group (ET extendable to 40) | Precision of the ET fraction ≤ 1 mm: CI 0.18–0.50 at n = 20, 0.22–0.45 at n = 40 (log-normal delta method) |
| EXP-H02 | 40 | TOST, σ_D 20 mm, margin ±10 mm, α 0.05, power 0.8 → 36 (t) + 10 % |
| EXP-H03-F | 22 | Non-inferiority, σ_D 1.5, margin 1.0, one-sided α 0.025, power 0.8 → 20 (t) + 10 %; n = 12 gives 56 % power |
| EXP-H03-T | 20 | Paired log-ratio, detect 0.8 with SD 0.3, α 0.05, power 0.8 → 17 (t) + attrition |
| EXP-H04-A | 72 (3 × 24) | d = 1.0, α 0.025 per comparison (Holm), power 0.8 → 21 per arm (t) + 10 % |
| EXP-H04-B | feasibility 36 (3 × 12); efficacy 102 (3 × 34) | δ 10 %, σ 15 %, ANCOVA ρ 0.6, α 0.025 per comparison, power 0.8 → 29 per arm (t) + 15 % |
| EXP-H05 | 30 raters (+ 16 haptic) | ±0.37 SD precision on the mean log-threshold; 10th percentile from a log-normal fit |
| EXP-H06 | 42 (+ 12 healthy) | Paired, δ = ln(1/0.7), σ_D = 2δ (COR-09) → 34 (t) + 15 %, rounded to 6 Williams sequences |

All assumed variances are replaced by pilot or internal-pilot estimates before the full studies. Every re-estimation rule is pre-registered.
