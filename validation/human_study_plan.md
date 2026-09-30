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
- §12 EXP-A02: guidance acceptance with people (pencil concept). It follows §10–§11 so that existing references to those sections stay valid.
- §13 EXP-I02: rotational share of writing tremor (inside EXP-H01 sessions)
- §14 EXP-I03: passive nose and grip options on writers (extends EXP-H03)
- §15 Rev H outcome studies: EXP-W01…W05, and EXP-G07 (the guidance board with people)
- §16 Rev J heel drive with people (DEC-037): EXP-D08 (guided writing), EXP-D09 (tremor), EXP-D11 (lead-through and autowrite with relaxed hands)
- §17 Rev J inertial end-cap with people (DEC-038): EXP-K03 (user crossover), EXP-K05 (cue perception); since DEC-051 only if an end-cap returns to the product
- §18 Rev J nose v2 with people (DEC-036, DEC-039, DEC-049): EXP-N09 (autowrite of accepted text), EXP-N10 (delayed ink); since DEC-050 the C1S nose is a bench research module, and autowrite a research mode with it
- §19 Rev J AI and control with people (DEC-042, DEC-043): EXP-L03 (ink lag; shares sessions with EXP-N10), EXP-L06 (text prediction in the app), EXP-L07 (style synthesis), EXP-L08 (guidance that fades across sessions)
- §20 Rev J integrated layout with people (DEC-044, DEC-045, DEC-048): EXP-J08 (ink visibility; superseded for Rev J.1 by EXP-J15), EXP-J09 (mass and balance, with EXP-K03), EXP-J15 (the clear window), EXP-J18 (the heel wheel on writing)
- §21 Real recorded data with people (study R; DEC-054, DEC-055): EXP-R01 (patients' own writing and tremor, the recording part of EXP-H01), EXP-R03 (a reading panel against the AI reader)
- §22 Spelling help, text prediction and clearer handwriting with people (study S; DEC-056, DEC-057): EXP-S10 (letters read while writing, inside EXP-H01/R01 sessions), EXP-S11 (a dyslexic misspelling corpus), EXP-S12 (a tick while writing), EXP-S13 (the tick's detection), EXP-S14 (personal prediction, with EXP-L06), EXP-S15 (shape assist, conditional), EXP-S17 (word recognition on the pen's recordings), EXP-S18 (suggestions at pauses against cues while writing)
- §23 Shifting the whole pen with people (study W; DEC-051…DEC-053): EXP-W10 (tremor at the ink while writing, with EXP-H01/R01), EXP-W12 (holding and writing with the collar), EXP-W16 (the cost of writing only when in reach)

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
| EXP-A02 (§12) | Do people's letters sit close enough to a personal template for AI-template guidance to help, and do people accept known- and AI-template guidance? | 60 (20 healthy, 20 ET, 20 PD) | A02-P: passive measurement; A02-G: within-subject, counterbalanced guidance conditions, reader-blinded | Legibility with gated AI templates vs none; template distance | **IA** (A02-G); measurement (A02-P) | A02-P with the passive pen (Stage A); A02-G after a G-S-equivalent gate for the build; DEC-020 |
| EXP-I02 (§13) | How much of the tremor at the nib comes from wrist or forearm rotation rather than hand translation, and about which pivot? | EXP-H01 participants (80) | Measurement inside EXP-H01 sessions; hand-dorsum IMU plus the pen's IMU and a page reference | Rotational share of nib tremor-band variance; pivot distance | none (measurement) | Stage A; DEC-024, H1 tremor model |
| EXP-I03 (§14) | Do passive nose and grip options (skid friction, soft sleeve, hand resting, heavier cap) improve writing on balance? | 20 ET (EXP-H03-T cohort) + 12 healthy | Within-subject, randomised, participant- and reader-blinded, non-active prototypes | Legibility and in-band ink tremor against the unmodified pencil | device burden; passive effect | Stage A–B; DEC-024 |
| EXP-W01…W05 (§15) | Rev H (bigger grip, DEC-029): does the 75 g pen add tremor; does the nose cut ink tremor in ET; do cues or a size assist help PD micrographia; does guided practice improve unassisted writing; does the app's spelling help reduce errors in dyslexia? | 20 ET; 20 PD with micrographia; poor-handwriting cohort; dyslexia cohort | crossovers and practice trials (§15) | tip tremor; ink tremor and words read; letter-height trend; unassisted legibility at retention; unassisted spelling errors | IA, LI, device burden | Rev H prototype after EXP-I05; ethics |
| EXP-G07 (§15) | Does practice with the guidance board improve unassisted writing, and is its extra downward pull acceptable? | adults (Touch arm, then board), later children with dysgraphia or dyslexia and PD | phases A–C (§15) | unassisted retention error; acceptance of the pull | LI | after EXP-G06 safety gate; ethics |
| EXP-D08 (§16) | Does the heel drive guide tracing, loops and reversed letters as well as the desk board, does every writer overpower it, and is unassisted retention no worse? | 12 adults, then children with dysgraphia | Randomised crossover (none, nose, board, heel steer-only, heel steered and driven), resist block, retention block after 1 day | Target error against the board with felt force at the 95th percentile; unassisted retention | IA; LI (retention block) | after the EXP-D07 safety gate; ethics |
| EXP-D09 (§16) | Does the heel's constraint and damping cut ink tremor without bending clean writing? | ≥ 8 ET + controls | Within-subject: none, nose, heel steer + brake, heel + nose; copying and free writing | Ink error; distortion of clean writing | IA | after EXP-D07 |
| EXP-D11 (§16) | Can the drive lead a relaxed hand through a sentence, and do people accept it? | 8 | Mode switched on by the participant; lead speeds 4–10 mm/s; practice sentence | Letters read at the lead speed; comfort | IA (the device writes) | after EXP-D07 |
| EXP-K03 (§17) | Does the active end-cap cut tremor more than the nose alone and more than the same weight, and is the back-heavy pen accepted? | 12 ET (+ a PD group) | Blinded crossover: nose, nose + weight, nose + active end-cap | Tip tremor amplitude (4–12 Hz); legibility; preference | IA; device burden | after EXP-K01, K02; only if an end-cap returns to the product (DEC-051) |
| EXP-K05 (§17) | Do people with ET and PD name the direction of an end-cap cue? | ET, PD with tremor, matched controls (n from a pilot, §11 rule) | Psychophysics: 8 directions, at rest and while writing | Direction named correctly; ink jitter during the cue | none (measurement) | after EXP-K01; K06 for rotor pulses; only if an end-cap returns (DEC-051) |
| EXP-N09 (§18) | Do people control and accept autowrite of accepted text, and is its ink as legible as their own writing? | healthy adults, then ET with up to 3 mm of tremor (n from a pilot, §11 rule) | Autowrite switched on by the user; accepted text (typed, dictated or an accepted suggestion) at 2.5 and 3 mm (DEC-049) | Legibility against the person's own writing; mode errors; coverage | IA (the device writes) | after EXP-N04, N05, N08 and S19; ethics; a research mode with the C1S nose (DEC-050) |
| EXP-N10 (§18) | Do writers accept ink that trails the hand? | adults (n from a pilot, §11 rule) | Within-subject: 0/50/100/150 ms delay, tablet then pen | Writing errors; acceptance of ≥ 100 ms | device burden | tablet: ethics only; pen: after EXP-N05 |
| EXP-L03 (§19) | How large an ink lag do writers notice, and does it cause errors? (only before any revival of delayed ink; shares sessions with EXP-N10) | 12 controls + 12 ET or PD | Within-subject: 0/12/25/50/100 ms on a tablet, then the ±6 mm bench nose; staircase and copy task | Just-noticeable lag; added strokes or letters per 100 letters | device burden | tablet: ethics only; pen: after EXP-N04, N05 |
| EXP-L06 (§19) | Does better text prediction save writing effort in the app? | 20 adults + 10 ET | Within-subject, counterbalanced: old n-gram against the mixture; offline scoring on own notes | Top-3 accuracy on own notes; accepted completions per 100 words; words per minute | IA (app) | ethics |
| EXP-L07 (§19) | Does synthesis from the 20 s calibration look like the user's writing? | 20 writers + 5 raters | Two-alternative forced choice and reading | Legibility; own-style choice rate | none (measurement) | ethics |
| EXP-L08 (§19) | Does guidance that fades across sessions help learning more than fixed guidance? | children with dysgraphia, or adults learning an unfamiliar script (n from a pilot, §11 rule) | Randomised: fixed partial guidance against session-level fading, 5 sessions; retention after 1 day and 1 week | Unassisted retention distance to the target letters | LI | after the bench gates of the build used; ethics |
| EXP-J08 (§20) | Can writers see the fresh ink behind the ball with the larger Rev J front? (Superseded for Rev J.1 by EXP-J15) | 10 right- and left-handed writers | Within-subject: printed Rev H and Rev J fronts on dummy pens, video from the eye | Distance behind the ball at which the ink first shows; ratings | device burden | unpowered dummies; ethics |
| EXP-J09 (§20) | Do writers accept the Rev J.1 masses and balance (84 g base, 113 g with the end-cap)? | 10 writers (with EXP-K03) | Within-subject: two dummies, 10 min each | Comfort, fatigue and acceptance | device burden | unpowered dummies; ethics |
| EXP-J15 (§20) | Can writers see the fresh ink through the clear window of the Rev J.1 front? | 10 right- and 10 left-handed writers | Within-subject: printed Rev J.1 and Rev J fronts on dummy pens, eye tracking or video from the eye | Distance behind the ball at which the ink first shows; ratings | device burden | unpowered dummies; ethics |
| EXP-J18 (§20) | Does the heel wheel distort writers' own writing, and do they adapt within 10 minutes? | healthy writers (n from a pilot, §11 rule) | Within-subject: wheel retracted, free and in its tremor mode, 10 min each | Distortion against their own writing with the wheel retracted, and its change over 10 min | device burden | EXP-D07 safety gate; ethics |
| EXP-R01 (§21) | What do ET and PD patients' own writing and tremor look like at the pen tip, with ink? | EXP-H01's participants (ET, PD, older and healthy adults) | The recording part of EXP-H01, in its sessions (the retest is the second session): ink and hover over a digitiser, the pen's IMU, REQ-DATA-009 | Tip tremor per participant in DEC-054's classes (zero-to-peak mm); writing kinematics | none (measurement) | with EXP-H01; ethics |
| EXP-R03 (§21) | Does the AI reader's "words you can read" match people? | naive readers (n from a pilot, §11 rule) | Blinded literal transcription of study R's rendered test-case ink, and EXP-R01 ink with consent | Tracker-minus-ordinary-pen words, panel against the AI reader | none (the reader's validity) | ethics |
| EXP-S10 (§22) | How early and how well does the recogniser read letters while people write on paper with the pen? | 20 adults + 10 ET/PD (inside EXP-H01/R01 sessions) | The calibration pangram and 3 notes; offline replay with and without calibration | Letters read at 50 % and 100 % of each letter; time per point on a phone | none (measurement) | with EXP-H01; ethics |
| EXP-S11 (§22) | An English corpus of dyslexic misspellings in context, with consent | 30 adults + 30 children with a dyslexia assessment | Free text and dictation by hand; transcribed and tagged; released under an open licence | Words and tagged errors | none (data) | ethics; consent for release |
| EXP-S12 (§22) | Does a tick while writing help people with dyslexia fix misspellings, and does it annoy them? | 20 adults with dyslexia + 20 controls | Within-subject, counterbalanced: no cue / tick on the suspect letter / tick + pen lift / app afterwards (shares sessions with EXP-S18) | Misspellings left on paper per 100 words; time; tolerance | IA | pen with LRA and pen lift, after EXP-N04, N05; ethics |
| EXP-S13 (§22) | Is a tick felt while writing, and how small can it be? | adults, including adults with dyslexia (n from a pilot, §11 rule) | 2AFC and yes/no detection; 5 pulse lengths, 3 amplitudes; while writing and at rest | Detection rate at the chosen pulse | none (measurement) | LRA mock-up; ethics |
| EXP-S14 (§22) | Does personal prediction on the user's own notes beat the old model? | 20 users (with EXP-L06) | 4 weeks of notes in the app; offline replay of NG0, NG1x and the personalised model | Top-3 after one letter, personalised against NG0 | IA (app) | app with logging; ethics |
| EXP-S15 (§22) | Does a shape assist make writing more legible without taking over? (only after a redesign shows a simulated gain) | ET (1–2 mm) and poor handwriting | Assist off and on, blinded order; a panel of 5 readers | Letters read by people; clean-writing motion; agency | IA | Rev J prototype; conditional (DEC-057); ethics |
| EXP-S17 (§22) | How well is writing read from the pen's own recordings, writer- and session-disjoint? | 30 writers (10 ET/PD, 10 dyslexia) | 2 sessions a week apart; a causal CTC recogniser trained on 20, tested on 10 and on held-out sessions | CER and WER with and without the language model | none (measurement) | pen with page sensor; ethics; a licence for release |
| EXP-S18 (§22) | Suggestions at pauses or cues while writing: accuracy against fluency | 24 adults with dyslexia | Within-subject, counterbalanced: app afterwards / tick at the next pause with 3 suggestions / tick on the suspect letter / opt-in automatic correction (shares sessions with EXP-S12) | Misspellings left; writing speed; harmful edits | IA | app + pen with LRA; ethics |
| EXP-W10 (§23) | How large is tremor at the ink while writing, and does anyone exceed the nose's reach (about ±6 mm)? | ET, PD action, PD re-emergent (≥ 20 each; with EXP-H01/R01) | Sentence and spirals on a digitiser with an ink pen and a 1 kHz IMU, hand resting and in free air | Tip tremor (zero-to-peak, main axis); writers beyond ±6 mm | none (measurement) | with EXP-H01; ethics |
| EXP-W12 (§23) | Can people hold and write with the collar? | tremor-free adults first (n from a pilot, §11 rule) | Collar locked and active (equal mass), random order | Comfort; felt reaction; noise; where the web rests | device burden | after EXP-W11's bench checks; ethics |
| EXP-W16 (§23) | What does "write only when in reach" cost people? | people with tremor (n from a pilot, §11 rule) | The Rev J pen with the gate on and off, random order | Words read; coverage; missing strokes; completion time | IA; device burden | after EXP-N04, N05, N08 and J17; ethics |

EXP-B06 (grip impedance) is a bench study with 12 healthy participants (`bench_protocols.md` §7). It is covered by the same ethics approval and the common elements of §3. The same holds for the Rev J bench studies with participants: EXP-K04 and EXP-K08 (`bench_protocols.md` §42), and EXP-V03 (inside EXP-H01 sessions) and EXP-V04 (§44). So does study B's EXP-B30 (the roll of a keyed grip, 10 writers with motion capture; `bench_protocols.md` §51). EXP-L01, L02 and L04 (§45) re-use EXP-H01 recordings under the consents of §3.3; EXP-L04 trains a model, so it uses only recordings whose consent covers model training (item iii). The same holds for EXP-R02 and R05 (`bench_protocols.md` §48); R05 also trains a model. EXP-S20 (`bench_protocols.md` §49) re-uses EXP-S18's data, and EXP-W15 (§50) the EXP-H01/R01 and EXP-W10 recordings, under the same consents.

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
| **Nib (or ink) tremor amplitude, excess-power method** | Displacement PSD S_p(f) of the nib (or deposited-ink) page trajectory per axis (Welch, 4 s Hann windows, 50 % overlap, pen-down segments). S_ref(f) = median PSD of the healthy-adult group for the same task, scaled to the participant's letter height; leave-one-out for healthy participants. Band = f_pk ± 1.5 Hz, where f_pk is the frequency of the largest ratio S_p/S_ref in 3–12 Hz. A_rms = √(∫_band max(0, S_p − S_ref) df); A_pp = 2√2·A_rms (sinusoid-equivalent peak-to-peak). The **major-axis** value uses the principal eigenvalue of the 2 × 2 cross-spectral matrix integrated over the band. The "per axis" limit of REQ-USR-002 is applied to the major axis (conservative). REQ-USR-002 now states its limits zero-to-peak, as DEC-054 (REQ-DATA-004): for a steady tremor A_pp is twice the peak, so its 0.5 mm peak is 1 mm p-p here. Before use, the method must recover known amplitudes injected into EXP-E01-A semi-synthetic recordings (method qualification). |
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

- **Requirements:** REQ-USR-002, whose "≤ 0.5 mm peak full / ≤ 1 mm peak partial" (1 and 2 mm p-p; restated zero-to-peak, DEC-054) is currently a literature-based estimate; REQ-MECH-001 (altitude envelope).
- **Decisions:** DEC-002 (claims by group and mechanism); DEC-009, since the frequency distribution vs the 7.5 Hz gate decides who free-writing cancellation can help.
- **Downstream uses:**
  - the recordings for EXP-E01 and E02 (causal separability on real writing);
  - the disturbance set for EXP-B09;
  - inputs to EXP-C01;
  - the eligibility criteria and **the screening yield (feasibility) of EXP-H06**.
- **Also measured:** writing force, altitude, azimuth, roll and speed distributions (CON notes §2.4 item 6), which replace assumption-based parameters.

There is no assistance and no intervention: the pen is passive.

**EXP-R01** (§21) is this study's recording part, not a separate visit: the same participants and sessions, with the retest as its second session. It adds REQ-DATA-009's recording rules (the ink path and hover over a digitiser at ≥ 200 points/s and ≤ 0.05 mm; the IMU's acquisition and availability time stamps; handedness, grip, posture, medication state and device configuration), and reports the tip tremor also in DEC-054's classes (zero-to-peak mm; the peak-to-peak values here are about twice as large for a steady tremor, REQ-DATA-004).

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

- R11's recording pen (`docs/measurement_rig.md` §4.1): the Ø24 mm body first, the Rev J grip, with its mass and centre of mass set by tungsten slugs to the Rev J.1 base pen (84.3 g, 86 mm from the tip, CALC); the 14 mm slim body becomes a second arm once study B's slim core is chosen. Grip size changes how tremor reaches the nib, so the census uses the grip being designed (the lead's decision, `prototype_stages.md` §0; the Rev A form of Ø15 mm is dropped);
- a D1 refill rigidly mounted on a 0–5 N axial load cell;
- a 6-axis IMU at ≥ 1 kHz (1.92 kHz in R11's pen), with acquisition and availability time stamps (REQ-DATA-009);
- the optical module(s) selected in EXP-S01;
- a ≤ 3 g marker cluster on the tail for motion capture;
- a USB tether through a medical-grade isolator;
- logs in the ICD research-frame format, with the stage fields set to zero.

**References:**

- optical motion capture (≥ 250 Hz, ≤ 0.05 mm accuracy in a 0.3 m volume). The nib position comes from the rigid-body transform calibrated with a pivot procedure;
- paper on an EMR digitiser that records the ink path and hover at ≥ 200 points/s and ≤ 0.05 mm (REQ-DATA-009; R11's tablet protocol, AC-T06-04);
- 4800 dpi scans of every page (bench rig R3);
- the reference chain must agree with the scanned ink to ≤ 50 µm RMS (AC-H01-08; PDT notes §2.7 require ≥ 200 Hz and 0.05 mm).

**Rig (study M).** Rig R11 instruments this study: the tablet protocol first (no build), then the recording pen, with the paper on R9's force plate so that the axial and paper-normal forces are measured apart. EXP-T06 qualifies both before the first participant ([`bench_protocols.md`](bench_protocols.md) §47; `docs/measurement_rig.md` §4). The study itself is unchanged.

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
| AC-H01-08 | — | Reference-system qualification: RMS difference between the reference chain's nib position (motion capture, or on rig R11 the tablet-recorded pen-down path after registration) and the scanned ink centreline | ≤ 50 µm | derived | PDT notes s2.7 (instrumentation ≥ 200 Hz and 0.05 mm accuracy); qualified on rig R11 in EXP-T06 (docs/measurement_rig.md s4.3), where it was proposed as AC-T06-01; the tablet's accuracy class of about ±0.25 mm (LIT CON-101) may fail it, and then the chain is registered per stroke | validity of EXP-H01; EXP-H01 on the tablet protocol |
| AC-H01-20 | REQ-ENV-001 | Fraction of in-contact writing time (sentence copying, all groups) with barrel altitude within 35-75°, per participant median and group 10th percentile | ≥ 90 % | requirement | REQ-ENV-001 range; COR-26 (paper ~50°, tablets 62 ± 7.5°) | REQ-ENV-001 range; REQ-MECH-001 low-altitude limit |
| AC-H01-21 | REQ-ENV-003 | Fraction of ET participants whose nib writing tremor lies in 3-12 Hz and ≤ 1 mm p-p (the addressable box of REQ-ENV-003), with 95 % CI | ≥ report with CI; programme review if < 20 % | hypothesis | REQ-ENV-003; PDT-12 (~30 % ≤ 1 mm) and PDT-31 (frequency 5.79 ± 1.32 Hz) | DEC-001; DEC-009 programme scope |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (10 rows for EXP-H01).
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

Is the research-pen form acceptable for comfort, fatigue, speed and legibility compared with ordinary pens? The form is Ø15 mm grip, a 16 mm bulge, 33–41 g and a centre of mass 76–81 mm from the tip (`results/mechanics/mass_budget.json`, v0.4.1).

Does moving the centre of mass forward matter enough to justify redesign? Is the writing point visible enough with the Rev A.1 nose? This informs REQ-FORM-001…004, open issue M-1 and DEC-018 (revisit trigger: visibility of the tip). It also serves as a formative usability evaluation (IEC 62366-1).

### Population

n = 40: 10 ET, 10 PD, 10 older adults, and 10 healthy adults, including at least 3 regular drawing users (REQ-USR-001 group d). Inclusion and exclusion as in §3.2.

### Design

Randomised 4-period crossover. The order follows a Williams design for 4 treatments (4 sequences, 10 participants each). The pens:

| Pen | Description |
|---|---|
| A | Research-pen form: an unpowered mass- and CoM-matched mock-up of Rev A.1 with a polymer rear barrel (≈ 33 g, CoM ≈ 76 mm) |
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
  - visibility of the writing point with the Rev A.1 nose (point protruding about 5 mm, tip Ø5.2 mm, aperture Ø4.2 mm). This is DEC-018's revisit trigger (AC-H02-06), so mock-ups A and B reproduce that nose;
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
| AC-H02-01 | REQ-FORM-003 | Comfort VAS (0-100 mm) after 10 min of writing: research-pen form (unpowered) minus the participant's reference pen, paired; 90 % CI of the difference | within ± 10 mm | hypothesis | engineering judgement (VAS minimal important difference ~10 mm convention) | REQ-FORM-003/004 revision (M-1) |
| AC-H02-02 | REQ-FORM-004 | Comfort VAS difference between CoM variants of the same shell (about 76 mm vs about 66 mm, ballast moved), paired 90 % CI | within ± 10 mm | hypothesis | engineering judgement; mechanics/README.md M-1 | REQ-FORM-004 revision |
| AC-H02-03 | REQ-FORM-001 | Proportion of participants rating grip diameter 'acceptable' or better | ≥ 80 % | hypothesis | engineering judgement | REQ-FORM-001 |
| AC-H02-04 | — | Writing speed with the research-pen form relative to the reference pen (ratio, lower 95 % bound) | ≥ 0.90 | hypothesis | engineering judgement (Micron users slowed 18-37 % with an active tool, ACT-02; the unpowered form must not add that burden) | form factor |
| AC-H02-05 | — | Hand/arm fatigue (Borg CR10) after 10 min, research form minus reference pen (mean difference) | ≤ 1 point | hypothesis | engineering judgement | mass and CoM |
| AC-H02-06 | — | Proportion of participants rating the visibility of the writing point 'acceptable or better' with the Rev A.1 nose (point protruding ~5 mm, tip 5.2 mm, aperture 4.2 mm) | ≥ 80 % | hypothesis | DEC-018 revisit trigger (H02: visibility of the tip); 80 % engineering judgement | DEC-018 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-H02).
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

The ASSIST_KF profile used for ON must have passed AC-B09-15 (gate behaviour). In simulation the balanced profile never opens its gate with tremor present (`docs/sim_report.md` §3.2); with it, ON would equal NEUTRAL by construction and the study could not detect an effect.

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
| AC-H06-05 | — | Device burden, NEUTRAL vs OFF, all participants: legibility (lower 95 % bound of the difference) / writing-speed ratio (lower 95 % bound) | ≥ -5 percentage points / ≥ 0.90 | hypothesis | engineering judgement; simulated device distortion 60-75 µm (results/sim/nominal/metrics.json) | DEC-006 (device distortion) |
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

- **Ethics approval is required before any participant is enrolled.** That includes EXP-B06 (bench, participants), H01 (passive pen), H02 and H03 (non-active mock-ups), H05 (raters), H04/H06 (active investigational device) and A02 (the passive part as H01; the guided part with an active device, handled like H04/H06 below).
- **Investigational device.**
  - A pen intended to compensate for a disability (tremor) is likely to be a **medical device** by intended purpose. For example, the EU MDR definition covers "alleviation of, or compensation for, … a disability".
  - H04, H06 and the guided part of A02 (A02-G) are therefore likely to be **clinical investigations of a medical device**: EU MDR Art. 62 ff. / UK MDR 2002 / US 21 CFR 812 (an IRB significant or non-significant risk determination).
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
- **Registration and transparency.** H04, H06 and A02-G are registered prospectively on a trial registry; H01, H02, H03, H05 and A02-P are pre-registered on OSF. Results are published per group, including null results.
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
| EXP-A02 | 60 (20 per group) | Paired legibility, σ_D 8 points, δ 4 points → 34 (t); agency non-inferiority, σ_D 1.0, margin 0.5 → 34 (t); ≈ 9000 AI-guided letters keep the upper bound of a 0.3 % misread excess below 1 % |
| EXP-I02 | EXP-H01 participants (80) | Descriptive: per-group median rotational share with a bootstrap CI; no hypothesis test |
| EXP-I03 | 20 ET + 12 healthy | Paired log-ratio of in-band ink tremor, detect 0.85 with SD 0.3, α 0.05, power 0.8 → 17 (t) + attrition → 20 ET; healthy for letter size and drag |

All assumed variances are replaced by pilot or internal-pilot estimates before the full studies. Every re-estimation rule is pre-registered.

---

## 12. EXP-A02: Guidance acceptance with people (pencil concept)

### Question and what it gates

Does physical guidance toward a template help people write, and do they accept it?

- **Known templates** (copying set text, tracing) are the credible use. In simulation an oracle template cut the pencil model P1's letter path error by 12 % (21 % on the writing alone), and the circle of the feature course from 348 to 174 µm.
- **AI-predicted templates** on free writing: the app predicts letters two ahead and draws them in the user's style. In simulation a correctly predicted letter in the user's style lay about 300 µm from what the writer meant, beyond the break-even template error of 265 µm on P1 (233–334 µm on M1). AI templates therefore gave no net benefit, while wrong templates stayed bounded by the travel (`docs/ai_guidance.md` §3.2, §4).

All of this comes from synthetic writers (glyph fonts, synthetic tremor). The break-even has to be compared with real within-writer variability.

- **Requirement:** REQ-PNC-007: guidance is limited to the travel and scaled by the calibrated confidence, and makes no more than 1 % of letters read as another letter when gated.
- **Decision:** DEC-020 (revisit trigger "EXP-A02: people's letters against personal templates").
- **Claim type:** the guided conditions are immediate assistance (IA, §1 rule R1); the template distance is a measurement. No lasting-improvement claim comes from this study.

### Two parts

| Part | Device | What it measures | Needs |
|---|---|---|---|
| **A02-P (passive)** | The EXP-H01 instrumented passive pen, no actuation. It can run inside EXP-H01 sessions under the same consent. | Within-writer letter variability: how far each unguided letter lies from the participant's personal template (AC-A02-02) | Ethics as for H01 |
| **A02-G (guided)** | A pencil build (Rev P1) that has passed a safety gate equivalent to G-S. The Rev A pen after G-S, with q_lim set to 0.30 mm, may substitute: the simulated order of the conditions was the same on P1 and on Rev A (`docs/ai_guidance.md` §4.2). | Legibility, misreads, agency, "fighting", deviation and fatigue under the guidance conditions (AC-A02-01, AC-A02-03) | A G-S-equivalent gate for the build; ethics as a device investigation (§10) |

**Pre-specified adaptive rule.** If the lower 95 % bound of the healthy adults' template distance in A02-P exceeds 265 µm, A02-G drops its plain AI-template arm and keeps the arm with deliberately wrong templates, which AC-A02-01 needs. AC-A02-03 is then not tested, and DEC-020 stands.

### Population

- Healthy adults, ET and PD (§3.1 groups; inclusion and exclusion as §3.2), **20 per group**. `docs/ai_guidance.md` §9 proposes 12–20.
- ET and PD participants are not screened on tremor amplitude. Their amplitude (§3.6 method) is recorded as a covariate.
- A02-P may also use the sentence copying of EXP-H01 participants, if their consent covers it.

### Design (A02-G)

- One session of about 90 min with breaks. Style calibration by a pangram, as in `docs/ai_guidance.md` §3.2.
- **Task C, copying known text:** no guidance vs known-template guidance (the template is the known text in the participant's calibrated style).
- **Task D, dictated sentences (free writing):**
  - no guidance;
  - AI-template guidance, gated (c_min 0.5, c_full 0.8; `config/pencil.yaml` `ai.*`);
  - the same, with 10 % of the templates replaced by the most likely wrong letter.
- Condition order is counterbalanced within each task (Williams designs). The same sentences are written in every condition of a task, in different orders, so that letters can be paired by position.
- Participants are told that "the pen may help in some blocks". The operator sees only coded conditions. Readers and the ink analysis are blinded (§3.5).
- Firmware: the guided core with the template rules T1–T8 as implemented at the time (`docs/ai_guidance.md` §7.3; T5–T7 are untested in simulation).

### Outcomes

- **Primary (IA):** legibility of Task D with gated AI templates vs no guidance: naive readers' transcription, % of words correct (§3.6). Recogniser CER is secondary.
- **Key secondary:**
  - letters newly read as another letter under gated AI guidance (AC-A02-01);
  - template distance from A02-P (AC-A02-02);
  - agency and perceived control ("the pen did what I intended", 7-point item; §3.6).
- **Secondary:**
  - path distance to the participant's own unguided letters;
  - in Task C, path distance to the known template (M-path);
  - "fighting": axial force rising during guidance, and the time at the soft limit;
  - maximum stage displacement;
  - Borg CR10 fatigue; preference.

### Sample size

- **Legibility (paired):** σ_D 8 percentage points (assumption), δ 4 points, two-sided α 0.05, power 0.8 → n = 34 (exact t), pooled over the groups.
- **Agency non-inferiority:** σ_D 1.0 point, margin 0.5, one-sided α 0.025, power 0.8 → n = 34.
- **Misreads:** ≥ 150 AI-guided letters per participant give about 9000 letters. With 4 % discordant letter pairs and a design effect of 2, a true excess of 0.3 % has an upper 95 % bound of about 0.8 % (CALCULATION), below the 1 % limit.
- **Enrolment: 60** (20 per group). This covers the above with attrition; per-group results are descriptive.

### Analysis

- Mixed models with the participant as a random effect: legibility ~ condition + order + group; agency likewise.
- Misreads are paired by letter position: excess = (misread only when guided − misread only when unguided) / AI-guided letters, with a cluster bootstrap by participant for the upper bound.
- Template distance, per participant: the RMS over letters of the distance between each unguided letter and the personal template (own exemplars, estimated style, anchored at touchdown; `aiguide/template.py`). For the tremor groups the tremor band is first removed by a zero-phase band-stop at f_pk ± 1.5 Hz (§3.6). Median per group with a bootstrap CI.
- Results are reported per group (R5, REQ-USR-001).

### Template error spectrum (A02-P data; `docs/sensor_fusion_ai.md` §5.e, §6.2)

The same unguided letters and personal templates also give the cross-track template error **along the stroke**, split into below 3 Hz and 3–15 Hz (`fusion.aieval.template_error_signal`). A template can help the pen's tremor estimate only if its error in the tremor band is well below the tremor (AC-A02-04). In simulation a correctly predicted letter in the writer's style carried 165 µm in 3–15 Hz, so the template prior made no difference and ships off by default (DEC-020).

### Adverse events and stopping

As §3.4. In addition, a participant who finds the nib motion distressing stops; every stage-at-stop event is logged; any unexpected motion is reported as a device deficiency.

### Acceptance criteria

<!-- AC-TABLE:EXP-A02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-A02-01 | REQ-PNC-007 | Letters newly read as a different letter under confidence-gated AI-template guidance (including the 10 % deliberately wrong templates): misread when guided but read correctly in the same participant's unguided copy of the same sentence, minus the reverse, over all AI-guided letters (blinded readers); upper 95 % bound | ≤ 1 % | requirement | REQ-PNC-007 (≤ 1 % of letters when gated); prediction 0.3 % gated and 2.2 % at full authority for letters under wrong templates (pencil model P1, results/ai/guidance.json safety.flips; SIMULATION, synthetic writers) | DEC-020 (AI-template guidance); REQ-PNC-007; template rules T1-T8 |
| AC-A02-02 | — | Template distance (EXP-A02-P): RMS distance between each unguided letter and the participant's personal template for it (own exemplars, estimated style, anchored at touchdown, as aiguide/template.py); median over healthy participants (reported per group; tremor groups with the tremor band removed) | ≤ 265 µm | hypothesis | break-even template error of guidance on the pencil model P1 (265 µm; 233-334 µm on M1; results/ai/guidance.json breakeven; SIMULATION); synthetic writers give 239 µm (clean ink) to about 300 µm (6 Hz 0.3 mm tremor) (results/ai/style_templates.json) -> expected FAIL for tremor groups | DEC-020 revisit trigger (people's letters against personal templates); AI arms of EXP-A02-G |
| AC-A02-03 | — | Decision rule for AI-template guidance (dictated free writing, gated vs no guidance): legibility (blinded transcription, % words correct) improves with the 95 % CI of the paired difference excluding zero, AND agency ('the pen did what I intended', 7-point) is not reduced (lower 95 % bound of the paired difference ≥ -0.5 point) | both met | hypothesis | docs/ai_guidance.md s9 decision rule; -0.5-point non-inferiority margin engineering judgement. Prediction: no net benefit (P1 gated AI guidance +2.5 % path error, recognition 0.78 vs 0.79 unguided; results/ai/guidance.json; SIMULATION) -> expected FAIL | DEC-020 (keep or drop AI-template guidance) |
| AC-A02-04 | — | Template error in the tremor band (EXP-A02-P): cross-track distance between each unguided letter and its correctly predicted personal template, along the stroke, 3-15 Hz part, RMS; median over healthy participants | ≤ 50 µm | hypothesis | a prior must know the intended path better than the tremor moves it (0.1 mm tremor about 71 µm RMS; engineering judgement); simulation: 165 µm for correctly predicted letters in the writer's style (results/fusion/context.json template_error; SIMULATION) -> expected FAIL | DEC-020 (template prior stays off by default) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-A02).
<!-- AC-TABLE:EXP-A02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Template distance ≤ 265 µm (AC-A02-02 passes) | AI templates could help in principle; A02-G decides. |
| Template distance above 265 µm (expected with tremor) | Physical guidance toward AI templates is not pursued for free writing; DEC-020 stands. |
| AC-A02-03 fails | Ship known-template guidance and digital correction only (DEC-020). |
| AC-A02-03 and AC-A02-01 pass | AI-template guidance may be offered as a gated option. Any claim needs an H06-type crossover first, and the freedom-to-operate review of PAT-01 comes before any guided-letter feature (`docs/ai_guidance.md` §8). |
| AC-A02-01 fails | REQ-PNC-007 is not met. Tighten c_min, the T3 corridor and the T5 drop rule, and re-test before any AI-template guidance. |

---

## 13. EXP-I02: Rotational share of writing tremor

### Question and what it gates

How much of the tremor at the nib during writing is hand-path translation, and how much is wrist or forearm rotation? About which pivot?

- The hand-pen model H1 drives the pen by a hand-path translation, with wrist rotation as a sweep (`docs/inertial_stabilisation.md` §4.2). Pronation–supination and wrist flexion–extension carry most essential-tremor kinetic tremor at the limb level (LIT HAP-33, abstract), but the share at the nib during writing is unmeasured.
- Gyroscopic devices act only on rotation, but H1 found them no better on rotational tremor (SIM). So this result mainly sets the tremor model of H1 and the lever-arm error of the pen's IMU (the IMU sits 78–120 mm from the nib).
- **Decision:** DEC-024 (input to the EXP-I01 re-run).

### Design

- Inside EXP-H01 sessions, under the same consent.
- Sensors: a 3-axis gyroscope and accelerometer on the dorsum of the hand (≥ 500 Hz); the pen's own IMU; the nib trajectory from a digitiser tablet under the paper, or coded paper at ≥ 120 Hz.
- Tasks: Archimedes spiral, a copied sentence, and hold-still with the nib on the paper; 3 repeats each.

### Analysis

- Coherence between the hand's angular velocity and the nib's in-plane motion in the tremor band.
- Least-squares fit of the nib motion as a translation plus a rotation about a pivot; the rotational share of the tremor-band variance and the pivot distance L_p per participant.
- Feed both to `sim.handpen.model.Tremor(amp_trans, amp_rot, L_p)`.
- Results per group (R5).

### Acceptance criteria

<!-- AC-TABLE:EXP-I02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I02-01 | — | Fraction of the nib's tremor-band (3-15 Hz) in-plane variance explained by hand rotation (translation + rotation-about-a-pivot fit), median per group, copied sentence | ≤ 0.5 | hypothesis | H1 drives the pen mainly by hand-path translation (ASSUMPTION); HAP-33 (abstract) reports pronation-supination and wrist flexion-extension carry most ET kinetic tremor at the limb level, so this may fail; H1 found gyroscopic devices no better on rotational tremor (SIMULATION) | H1 tremor model; IMU lever-arm budget |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-I02).
<!-- AC-TABLE:EXP-I02:END -->

---

## 14. EXP-I03: Passive nose and grip options on writers (extends EXP-H03)

### Question and what it gates

Do passive ways of steadying the pen at the paper or in the grip improve writing on balance? In H1, friction, damping and compliance trade tremor for writing about one for one: the net in-band error against the intended writing stays within 0.93–1.25 of the unmodified pencil (SIM, `results/pencil/inertial.json` passive). H1 has no voluntary correction and no hand on the paper, so people may do better than the model predicts. This study measures that.

- **Decision:** DEC-024 (revisit trigger "EXP-I03 shows hand resting or a passive option improves net ink error by ≥ 15 %").
- **Claim type:** device burden and passive effect (§1). No active assistance is involved.

### Conditions (blinded, randomised within subject)

- Skid friction μ ≈ 0.05, 0.12 (as designed) and 0.25: EXP-Q01 materials in identical shells.
- Grip sleeve at about 1×, 0.5× and 0.25× the grip stiffness: silicone tubes of Shore 20A–60A, stiffness measured on the EXP-I01 rig.
- Hand resting on the paper vs not resting (instructed, verified from video).
- A heavier-cap control (+10 g).

### Population

EXP-H03-T participants (20 ET) and 12 healthy adults from EXP-H03-F, in the same visits where possible. Inclusion and exclusion as §3.2.

### Outcomes

- **Primary:** legibility of copied sentences (blinded transcription, % words correct) with each option against the unmodified pencil.
- **Key secondary:**
  - in-band ink tremor (3–15 Hz, the M-band of `bench_protocols.md` §0.8);
  - letter height against the same participant's unmodified pencil;
  - drag and comfort ratings.
- Recogniser CER is secondary.

### Analysis

Mixed models with the participant as a random effect: outcome ~ option + order + group. Paired log-ratios for the tremor and letter-height outcomes.

### Acceptance criteria

<!-- AC-TABLE:EXP-I03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I03-01 | — | Legibility of copied sentences (blinded transcription, % words correct) with the best passive option (skid friction, grip sleeve, hand resting, heavier cap) minus the unmodified pencil, ET participants | ≥ 5 percentage points | hypothesis | DEC-024 revisit rule; H1 predicts no net gain from any modelled passive option (net in-band error against intended 0.93-1.25 of the unmodified pencil; results/pencil/inertial.json passive; SIMULATION) -> expected FAIL except possibly hand resting (not modelled); 5 points engineering judgement | DEC-024 |
| AC-I03-02 | — | In-band (3-15 Hz) ink tremor with skid friction 0.25 relative to 0.12, ET participants, geometric mean of paired ratios | ≤ 0.9 | hypothesis | H1 predicts 0.83-0.86 (results/pencil/inertial.json passive skid_mu_0.25; SIMULATION): a check of the model's passive friction effect | H1 validation (passive friction) |
| AC-I03-03 | — | Letter height with skid friction 0.25 relative to 0.12, same participant, copied sentences | ≥ 0.9 | hypothesis | H1 predicts 0.81 but has no voluntary correction (docs/inertial_stabilisation.md s4.5); a PASS shows the model overstates friction's shrinking of the writing | H1 hand model (voluntary correction) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-I03).
<!-- AC-TABLE:EXP-I03:END -->

### Decision

Adopt a passive option only if legibility improves (AC-I03-01) with no loss of letter size beyond AC-I03-03. The prediction is that none will, except possibly hand resting, which the model cannot evaluate.

---

## 15. Rev H outcome studies: EXP-W01…W05 and EXP-G07

The user chose a bigger grip (DEC-029). Rev H moves its whole nose, and so the ink tip, by up to ±3 mm (DEC-032). It gives cues and practice modes, and has an optional desk guidance board (DEC-031). The predictions come from `docs/handwriting_outcomes.md` and `results/handwriting/outcomes.json` (model HW1, SIMULATION; the writers' responses to cues are ASSUMPTION ranges).
- Every study scores recordings with the same definitions as the simulations: `python3 -m handwriting.score_recording trace.csv`, from a tablet (≥ 100 Hz, ≤ 0.05 mm) or the pen's own page sensor.
- The ids are EXP-HW1…HW5 in `docs/handwriting_outcomes.md` §8.

### EXP-W01: Does a 75 g, 22 mm pen transmit more tremor than a 12 g pen?
- **Design.** 20 people with ET; randomised crossover: an ordinary 12 g pen, the 75 g Rev H dummy with the nose locked, and a 72 g weighted pen.
- **Tasks.** Spiral, line and a copied sentence on a tablet. Grip stiffness is measured with a small shaker on the barrel (as HAP-26).
- **Decision.** If the Rev H dummy is worse by more than 10 %, reduce its mass or move it forward.

<!-- AC-TABLE:EXP-W01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W01-01 | REQ-RVH-001 | Tremor amplitude at the tip (handwriting.score_recording) with the 75 g Rev H dummy (nose locked) relative to an ordinary 12 g pen, ET participants, 8-10 Hz tremor, copied sentence and spiral | ≤ 1.10 | hypothesis | REQ-RVH-001 (mass); prediction +14 to +26 % at 8-10 Hz with the HAP-26 575 N/m grip and no change with a grip twice as stiff (results/handwriting/outcomes.json; SIMULATION) -> uncertain; 10 % engineering judgement | Rev H mass and mass distribution |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-W01).
<!-- AC-TABLE:EXP-W01:END -->

### EXP-W02: Does the nose cut ink tremor in essential tremor?
- **Design.** The offline part extends EXP-E01 on EXP-H01 recordings. Then a blinded crossover with Rev H (nose off against nose on) in ET writers with tremor above 7.5 Hz.
- **What it decides.** The ET claim and the frequency gate.
- **Severe-tremor setting (DEC-035).** In the offline part, also run the more aggressive tracker setting of `docs/ai_severe_tremor.md` on the same recordings. It is kept as a per-user mode, chosen by the 20 s calibration, only if AC-W02-03 passes; the simulation predicts that its false correction fails.

<!-- AC-TABLE:EXP-W02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W02-01 | REQ-RVH-006 | Tremor amplitude in the ink with the Rev H nose on against nose off (blinded crossover), ET writers with tremor above 7.5 Hz, relative reduction | ≥ 30 % | hypothesis | REQ-RVH-006; prediction 47-50 % less ink error at 10 Hz and 22-25 % at 8 Hz with the re-tuned tracker (results/handwriting/outcomes.json; SIMULATION) | ET claim; DEC-032; DEC-009 frequency gate |
| AC-W02-02 | REQ-RVH-006 | False correction of the Rev H nose on tremor-free writing of healthy controls (ink moved against nose off), RMS | ≤ 25 µm | derived | derived from AC-E01-09 / REQ-CTRL-005; prediction 22 µm (shipped tracker) and 26 µm (re-tuned) (results/handwriting/outcomes.json; SIMULATION) -> marginal | DEC-028 / Rev H tracker setting |
| AC-W02-03 | — | Severe-tremor tracker setting (DEC-035) run offline on EXP-H01 recordings: ink-error ratio against the pen held for writers with 1-2 mm tremor, AND false correction on the tremor-free writing of healthy controls (both) | both met (0.6; 25 µm) | hypothesis | DEC-035; prediction ratio 0.34 at 8-10 Hz and 0.48 at 6 Hz but false correction 263 µm (results/aiprior/aiprior.json; SIMULATION) -> predicted to fail the 25 µm bound of AC-E01-09; 0.6 engineering judgement | DEC-035 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-W02).
<!-- AC-TABLE:EXP-W02:END -->

### EXP-W03: Cues or a size assist for Parkinson's micrographia?
- **Design.** 20 people with PD and progressive micrographia. Within-subject order: plain paper, 1 cm lines, the vibration cue at > 10 % shrinkage, the adaptive vertical size assist, then the pen switched off (after-effect). Copy 3 pangrams in each condition.
- **Measurands.** Letter-height trend, normalised jerk (PDT-17) and sense of agency.

<!-- AC-TABLE:EXP-W03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W03-01 | — | Letter-height change from the first to the last quarter of copied pangrams with the vibration cue at > 10 % shrinkage, PD participants with progressive micrographia | ≥ -5 % | hypothesis | prediction +2 % with the cue (5.1 -> 5.2 mm) against -18 % without help (5.1 -> 4.2 mm), assuming the response ranges of LIT PDT-19, PDT-18, PDT-33 (results/handwriting/outcomes.json; SIMULATION with ASSUMPTION responses) | Rev H write-bigger cue |
| AC-W03-02 | — | Adaptive vertical size assist against 1 cm lines and the cue: larger end-of-task letter height with no increase of normalised jerk over 10 % and no loss of sense of agency (all three) | all three met | hypothesis | only size-assist variant worth testing (fixed gain: still shrinks 18 %, tremor +33 %, jerk x2.5); adaptive assist jerk +25 % predicted (SIMULATION) -> expected FAIL on jerk; LIT PDT-17, PDT-34, PDT-35 | Rev H size-assist mode (build or drop) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-W03).
<!-- AC-TABLE:EXP-W03:END -->

### EXP-W04: Does guided practice improve unassisted handwriting?
- **Design.** Children or adults with poor handwriting (BHK-type screening), at least 20 sessions (HAP-41).
- **Arms.** Practice alone; with a vibration cue on errors; with partial nose guidance; with the board's partial guidance, if built. Guidance fades over the sessions.
- **Outcome.** Unassisted legibility and speed at 1 day and 4 weeks.

<!-- AC-TABLE:EXP-W04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W04-01 | — | Unassisted legibility at 4-week retention (BHK-like, blinded) after ≥ 20 practice sessions with partial nose guidance, minus practice alone | ≥ 0 points (non-inferior) and a positive point estimate | hypothesis | LIT HAP-41 (≥ 20 sessions), HAP-42/43/44 (guidance effects mostly vanish when off), HAP-10 (fluency more than shape); SIM: partial nose guidance 35 % closer while on, letters read 94 % (results/handwriting/outcomes.json) -> uncertain | Rev H practice mode; DEC-031 board value |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-W04).
<!-- AC-TABLE:EXP-W04:END -->

### EXP-W05: Does the app's spelling help reduce spelling errors in dyslexia?
- **Design.** Dictation practice, 4–6 weeks. The app knows the target words, flags wrong words with a gentle buzz, shows and reads the right spelling, and keeps a corrected copy. The comparison is the same app without flags.
- **Study S (DEC-056).** The buzz is the tick at the next pause, with suggestions only at pauses (REQ-APP-008). EXP-S12 and S18 (§22) test cues while writing, and EXP-S11 may share this cohort.
- The pen never changes the ink.

<!-- AC-TABLE:EXP-W05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W05-01 | — | Spelling errors in unassisted dictation after 4-6 weeks of dictation practice with the app flagging wrong words (buzz, show and read the right spelling), relative to the same app without flags, participants with dyslexia | ≥ 20 % | hypothesis | the app flags 100 % of misspelt words with a known target at 6 % false flags (SIMULATION, results/handwriting/outcomes.json); effect on learning unknown; LIT HAP-47, HAP-48, HAP-50; 20 % engineering judgement | Rev H spelling mode in the app |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-W05).
<!-- AC-TABLE:EXP-W05:END -->

### EXP-G07: Guidance board with people
- **Phase A:** the 3D Systems Touch arm (HAP-52) with a pen adapter, comparing partial, full and lead-through guidance on adults.
- **Phase B:** the board prototype with adults.
- **Phase C:** children with dysgraphia or dyslexia, and people with PD.

Assisted and **unassisted** error, retention after 1 day and 1 week, legibility, speed, fluency, letter size (PD) and comfort with the downward pull. Only after the EXP-G06 safety gate.

<!-- AC-TABLE:EXP-G07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G07-01 | REQ-RVH-007 | Guidance board practice: unassisted retention error after 1 week relative to practice without guidance, adults (phase B), and the share of participants rating the extra downward pull acceptable | retention not worse; ≥ 70 % acceptable | hypothesis | REQ-RVH-007; board study: guided accuracy is not learning (LIT HAP-01...06); normal pull about 1.0 N while guiding (CALC, docs/guidance_board.md); 70 % engineering judgement | DEC-031 (build the board beyond the prototype) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G07).
<!-- AC-TABLE:EXP-G07:END -->

---

## 16. Rev J heel drive with people: EXP-D08, D09, D11

The heel drive (DEC-037) uses the paper as ground. A small steered wheel at the heel guides the pen along a letter. By default it only steers, so it cannot move the pen on its own. In an explicit lead-through or autowrite mode its motor can lead a relaxed hand (DEC-039), and it never starts a stroke. The bench protocols are in `bench_protocols.md` §41. The predictions come from `docs/grounded_drive.md` and `results/drive/` (model HW1-D, synthetic writers, SIMULATION; the relaxed-writer model and the tyre friction are ASSUMPTIONS).
- **Safety.** Only after the EXP-D07 safety gate (force cap, release, stall, lift) on the exact build. Inclusion and exclusion as §3.2, including the rule on active implants for the actuated pen.
- **Claims.** Guidance while the drive is on is immediate assistance. Practice followed by an unassisted retention test is lasting improvement (§1). The two are never mixed.

### EXP-D08: Guided writing with people (tracing, loops, reversed letters, resist)
- **Design.** n = 12 adults, then children with dysgraphia (ethics approval for children). Randomised crossover: none, nose alone, desk board, heel steer-only, heel steered and driven. Tasks: tracing, "write big" loops, b–d reversal. A "resist" block: the participant writes their own letter against the template. An unassisted retention block after 1 day.
- **Measurands.** Target error; letters read by the app; felt force (instrumented handle); yields; mode logs; preference; retention.
- **Predictions (SIM).**
  - Tracing, dysgraphia-like: heel steer-only 372 µm, desk board 384 µm, nothing on 582 µm. Dyslexia-like: 491 µm against the board's 416 µm (the heel is worse here).
  - Every full guide lowers the letters read (92 % → 84–90 %).
  - Felt change 0.24–0.26 N at the 95th percentile (0.32 N for a lightly resisting hand).
  - Loops stay at 0.99 of the target height (board 0.91).
  - A writer set on 'b' kept 'b' under every device.
  - Guided accuracy did not transfer to unassisted writing in a virtual-fixture study; error amplification did (LIT HAP-67).
- **Decision.** Pass: DEC-037 can be adopted (together with EXP-D01, D05 and D07). Heel worse than the board: keep the board for tracing. Retention worse than none: use guidance only with fading and catch trials. Not accepted: revisit DEC-037.
- **Status (DEC-048).** The heel wheel is retracted by default. It is deployed for 'write big' practice (driven) and lead-through only; its tracing arms wait for a controller that passes REQ-RVJ-C02 in sim2, or for EXP-J18. In sim2, tracing with the wheel read fewer words (97 → 70 %; `docs/revJ_simulation.md` §6.4).
- **Status (DEC-057).** Nearest-point close tracing is retired for letters. The tracing arms use guidance that advances along the letter and checks that every part is drawn, once EXP-S16 passes on the bench (`bench_protocols.md` §49); the nearest-point law stays only as EXP-S16's comparison. Letters are also read by a page reader, not only by the app's reader, which reads in writing order (study S, SIM: close tracing 92 → 79 % with the app's reader, 70 → 72 % with a page reader). DEC-057 is revisited if this study shows that close tracing helps learning despite the reader.

<!-- AC-TABLE:EXP-D08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D08-01 | — | Target error with the heel drive (steer-only, and steered and driven) relative to the desk board (full law), tracing, adults then children with dysgraphia, geometric mean ratio over participants, with the felt force (instrumented handle) at the 95th percentile (both) | both met (ratio ≤ 1.0; felt force ≤ 0.5 N) | hypothesis | pass line of the drive study; SIM: steer-only 372 µm against the board's 384 µm (dysgraphia-like) but 491 against 416 µm (dyslexia-like); felt change p95 0.24-0.26 N, 0.32 N for a resisting hand (docs/grounded_drive.md s5.1, s5.2) -> uncertain | DEC-037 (heel against board, DEC-031) |
| AC-D08-02 | REQ-DRV-002 | Resist block: participants who overpower the drive in every trial (write their own letter against the template, e.g. 'b' against a 'd' template) | all participants | derived | REQ-DRV-002 made measurable with people; SIM: a writer set on 'b' kept 'b' under every device, felt change p95 0.46 N (docs/grounded_drive.md s5.3) | DEC-037 |
| AC-D08-03 | — | Unassisted retention block after 1 day: target error after practice with the heel drive relative to practice with none (unassisted; lasting-improvement endpoint) | not worse than none | hypothesis | pass line of the drive study; guided accuracy did not transfer to unassisted writing in a virtual-fixture study, error amplification did (LIT HAP-67); guidance effects mostly vanish when off (HAP-42/43/44) | DEC-037; heel practice mode (fading, catch trials) |
| AC-D08-04 | — | Participants who rate the heel guidance acceptable (comfort and preference questionnaire at the end of the crossover) | ≥ 70 % | hypothesis | DEC-037 revisit trigger (guidance with people not accepted); 70 % engineering judgement, as AC-G07-01 | DEC-037 |
| AC-D08-05 | REQ-DRV-003 | Mode logs of every session: the drive motor pushed only in lead-through or autowrite blocks the participant had switched on, and never before a pen-down (no stroke started by the drive) | no push outside the mode; no stroke started | requirement | REQ-DRV-003; DEC-039 (assistance modes never start a stroke); met by the mode logic in SIM | DEC-037; DEC-039 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-D08).
<!-- AC-TABLE:EXP-D08:END -->

### EXP-D09: Tremor: constraint and damping
- **Design.** People with ET (n ≥ 8): copying and free writing with none, nose, heel steer + brake, and heel + nose. Controls without tremor, for false correction.
- **Measurands.** Ink error; words read; distortion of clean writing.
- **Predictions (SIM; 6 ET writers, 1 mm at 4–10 Hz).**
  - Wheel steer + brake: 0.74 of the error with nothing on, but it bends clean writing by 186 µm.
  - Wheel steered along a known text: 0.73, with 68 µm on clean writing.
  - The nose's tracker: 0.77 with 18 µm (0.42 at 10 Hz, nothing at 4 Hz).
  - Ball damper + nose: 0.62 with 95 µm.
  - The heel helps at 4–6 Hz, where the tracker does nothing.
- **Decision.** As predicted (free writing fails, known text passes): offer the heel's tremor mode only for copying, tracing and dictation practice. If 4–6 Hz tremor matters more and EXP-D13 passes, reconsider the driven ball (`docs/grounded_drive.md` §6).
- **Status (DEC-048).** The heel wheel is retracted by default. In sim2 its tremor mode moved tremor-free writing by 0.40 mm, against the 25 µm of REQ-RVJ-C02, and doubled the error at 0.3 mm. Run the heel arms only after a redesigned tremor-mode controller passes REQ-RVJ-C02 in sim2, or after EXP-J18 shows that writers adapt.

<!-- AC-TABLE:EXP-D09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D09-01 | — | Free writing, ET participants (n ≥ 8): ink error with the heel's steer + brake mode relative to none, AND distortion of the tremor-free writing of controls by the same mode (ink moved against the same pen off) (both) | both met (0.8; 100 µm RMS) | hypothesis | pass line of the drive study (-20 % with ≤ 100 µm on clean writing); SIM: 0.74 at 1 mm, 4-10 Hz, but 186 µm on clean writing (166 µm for an adapted writer) (docs/grounded_drive.md s5.5) -> expected FAIL on distortion | DEC-037 (heel tremor mode; wheel or ball) |
| AC-D09-02 | — | Copying a known text, ET participants: ink error with the wheel steered along the writer's own letters relative to none, AND distortion of the controls' tremor-free copying (both) | both met (0.8; 100 µm RMS) | hypothesis | pass line of the drive study; SIM: 0.73 with 68 µm on clean writing, and 0.69-0.70 at 4-6 Hz where the nose's tracker does nothing (docs/grounded_drive.md s5.5) | DEC-037 (heel tremor mode for copying, tracing and dictation) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-D09).
<!-- AC-TABLE:EXP-D09:END -->

### EXP-D11: Lead-through and autowrite with relaxed hands
- **Design.** n = 8. The participant switches the mode on and is asked to keep the hand relaxed. Lead speeds 4–10 mm/s. The practice sentence. A comfort questionnaire.
- **Measurands.** Letters read; pen speed; force; comfort.
- **Predictions (SIM).** Wheel lead + nose: 76 % of letters and 60 % of words read at 7.2 mm/s, force up to 0.49 N. A relaxed hand led through a 'd' drew 93 % of the bowl. The relaxed-writer model (the aim follows the hand, τ 0.25 s) is an ASSUMPTION: real people may resist, over-help or tire.
- **Claim type.** IA; here the device writes, so no claim is made about the user's own writing.
- **Decision.** Pass: keep lead-through and gross-scale autowrite as explicit modes (DEC-037, DEC-039). Fail: the drive's lead stays a demonstration; the nose's autowrite (EXP-N09) does not need it.

<!-- AC-TABLE:EXP-D11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D11-01 | — | Lead-through of a relaxed hand through the practice sentence by the heel drive with the nose, mode switched on by the participant: letters read by the app's recogniser, pen speed, and discomfort reported (all three) | all three met (≥ 70 % of letters; ≥ 5 mm/s; no discomfort) | hypothesis | pass line of the drive study; SIM: wheel lead + nose 76 % of letters and 60 % of words at 7.2 mm/s, force up to 0.49 N (relaxed-writer model, ASSUMPTION; docs/grounded_drive.md s5.4) | DEC-037; DEC-039 (lead-through and autowrite modes) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D11).
<!-- AC-TABLE:EXP-D11:END -->

---

## 17. Rev J inertial end-cap with people: EXP-K03, K05

The end-cap (DEC-038) holds a 30 g tungsten slug that coils push by ±4 mm against the tremor, on top of the nose; the Rev J.1 end-cap (DEC-045) has a 17.3 g slug and weighs 29.6 g. It may also play short cues, but only in pauses and only after EXP-K05. It never writes or steers. The bench protocols are in `bench_protocols.md` §42. The predictions come from `docs/inertial_endcap.md` and `results/endcap/endcap_study.json` (H1 on the Rev H pen, SIMULATION; literature for the cues).
- **Safety.** Only after EXP-K01 and EXP-K02 on the exact build; for CMG pulses in EXP-K05, also after EXP-K06. Inclusion and exclusion as §3.2, including the rule on active implants (NdFeB tiles on the slug, and the nose magnets).
- **Superseded for the product (DEC-051, 2026-09-29).** Inertial tails are rejected for the pen, and the end-cap stays only as a bench comparison against the same mass locked (EXP-J16, W14). EXP-K03 and K05 run only if an end-cap returns to the product through REQ-WP-001 (≥ 10 % against the same pen with it locked, at three grip strengths, with coverage kept). REQ-EC-005 and 006 apply again only then; the pen's cue is now an LRA tick (EXP-S13, §22).

### EXP-K03: Does the end-cap help people?
- **Design.** Randomised crossover. 12 writers with ET, and a PD group. Blinded housings of equal look and mass: nose alone, nose + the same weight fixed, nose + active end-cap. Archimedes spirals, lines and a sentence.
- **Measurands.** Tip tremor amplitude (pen IMU, 4–12 Hz band); spiral rating; legibility; preference; fatigue.
- **Predictions (SIM, CALC).** Further reduction at 8–12 Hz, 1–2 mm: +8 / +18 / +20 % at r_rot 0.3 / 0.5 / 0.7; the same weight fixed +17 / +12 / +4 %; at 4–6 Hz +8 to +12 %. The Rev J.1 end-cap (29.6 g, DEC-045): +5.6 / +16.8 / +18.3 %, and the same mass fixed +12.6 / +11.1 / +6.7 % (SIM). On the Rev J.1 pen it takes 84.3 g to 112.7 g and moves the centre of mass from 86.0 to 102.5 mm from the tip, 10.5 mm behind the web (CALC; Rev J: 129.2 g and 108.1 mm). EXP-J09 (§20) tries the same masses as dummies.
- **Claim type.** IA and device burden.
- **Decision.** Pass: keep the end-cap as a detachable option. Active not 5 points better than the weight: fit the weight or nothing (DEC-038). Back-heavy pen rejected: revisit DEC-038.

<!-- AC-TABLE:EXP-K03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K03-01 | REQ-EC-002 | Tip tremor amplitude (pen IMU, 4-12 Hz band) with nose + active end-cap relative to nose alone, blinded housings, ET participants, spirals, lines and a sentence; reduction | ≥ 10 % | hypothesis | pass line of study K; REQ-EC-002; SIM +8 / +18 / +20 % at 8-12 Hz depending on the unmeasured grip split, +8 to +12 % at 4-6 Hz (results/endcap/endcap_study.json); the Rev J.1 end-cap (29.6 g, DEC-045) +5.6 / +16.8 / +18.3 % (SIM, results/revJ1/endcap.json) | DEC-038 (keep the end-cap as a product option) |
| AC-K03-02 | REQ-EC-003 | Tremor reduction with the active end-cap minus that with the same weight fixed (blinded housings of equal mass), ET participants | ≥ 5 points | hypothesis | REQ-EC-003; prediction depends on the grip split: -9 / +6 / +16 points at r_rot 0.3 / 0.5 / 0.7 (SIM); -7.0 / +5.7 / +11.6 points with the Rev J.1 end-cap (29.6 g, DEC-045; SIM) | DEC-038 |
| AC-K03-03 | — | Legibility of the copied sentence (blinded readers, % words correct) with nose + active end-cap relative to nose alone | no loss | hypothesis | pass line of study K; false correction on tremor-free writing 11 µm (lognormal writers) and 20-23 µm (glyph writers) with the device (SIM) | DEC-038 |
| AC-K03-04 | — | Participants who accept the back-heavy pen with the end-cap for a writing session (preference and fatigue questionnaire) | ≥ 70 % | hypothesis | DEC-038 revisit trigger (writers reject the back-heavy pen); on the Rev J.1 pen the 29.6 g end-cap takes 84.3 to 112.7 g and moves the centre of mass from 86.0 to 102.5 mm from the tip, 10.5 mm behind the web (CALC, DEC-045; Rev J: 129.2 g and 108.1 mm); EXP-J09 tries the same masses as dummies; 70 % engineering judgement, as AC-G07-01 | DEC-038 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-K03).
<!-- AC-TABLE:EXP-K03:END -->

### EXP-K05: Is a cue felt, and felt correctly, by people with tremor?
- **Design.** The pen with the end-cap playing asymmetric vibration (40 Hz + 80 Hz, phase 0 and −180°) and, with the research module, CMG pulses. Eight directions. ET, PD with tremor, and matched controls. At rest and while writing.
- **Measurands.** Direction named correctly (%); detection threshold (m/s² at the grip); reaction time; ink jitter during the cue.
- **Predictions.**
  - Healthy adults named cue directions 93–99 % of the time with hand-held devices (LIT HAP-82, HAP-84, HAP-85).
  - Sides with tremor were near chance in the only patient study found (LIT PDT-39, preprint).
  - A 0.5 N, 40 + 80 Hz cue shakes the ink by 186 µm RMS while writing (SIM).
  - People need at least 0.33 s to act on a cue, while a stroke lasts 0.09–0.15 s (LIT HAP-84, CON-24). Cues can steer drift, size and line direction, not strokes.
- **Claim type.** Measurement.
- **Decision.** Named correctly in the patient groups and the ink within 30 µm: a cue mode while writing. Named correctly but the ink shakes (as predicted): cues only in pauses or with the pen lifted. Not named correctly in a group: no directional cue for that group.

<!-- AC-TABLE:EXP-K05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K05-01 | REQ-EC-006 | Direction of end-cap cues (asymmetric 40 + 80 Hz vibration, phase 0 and -180°; CMG pulses with the research module) named correctly, 8 directions, at rest and while writing, in each patient group (ET; PD with tremor) | ≥ 90 % | requirement | REQ-EC-006; healthy adults 93-99 % with hand-held devices (LIT HAP-82, HAP-84, HAP-85); sides with tremor near chance in the only patient study (LIT PDT-39, preprint) -> uncertain; matched controls as reference | DEC-038 (cue mode only after EXP-K05) |
| AC-K05-02 | REQ-EC-005 | Ink jitter during a cue given while writing (ball on the paper), at the cue level used in AC-K05-01 | ≤ 30 µm RMS | requirement | REQ-EC-005 (rule R-C1); prediction 186 µm RMS at 0.5 N, 40 + 80 Hz (116-239 µm over the grip splits); 76 µm at 0.25 N; 31 µm at 75 Hz (SIM) -> predicted to FAIL: cues only in pauses or with the pen lifted | DEC-038 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-K05).
<!-- AC-TABLE:EXP-K05:END -->

---

## 18. Rev J nose v2 with people: EXP-N09 (autowrite) and EXP-N10 (delayed ink)

The nose v2 (DEC-036) moves the ball 6 mm in every direction. In an explicit autowrite mode (DEC-039) the pen draws text the user accepted (typed, dictated or an accepted suggestion; DEC-049, DEC-056) in the user's own style, at up to 3 mm of tremor, while the user sweeps the pen along the line. It waits when the user slows, lifts the ball when the text leaves its reach, and never pushes the hand with the nose. The bench protocols are in `bench_protocols.md` §43. The predictions come from `docs/nose_v2.md` and `results/nose2/nose2.json` (HW1 on synthetic writers, SIMULATION).
- **Safety.** Only after EXP-N04 (heat), EXP-N05 (pen lift) and EXP-N08 (bench autowrite, with the SIM gate) on the exact build, and for accepted words EXP-S19 (the writing plan, `bench_protocols.md` §49). Inclusion and exclusion as §3.2, including the rule on active implants (N52 magnets).
- **Freedom to operate.** Autowrite with a pen lift is close to claim 1 of PAT-01. Attorney review comes before any product claim (DEC-036).
- **DEC-050 (2026-09-30).** The C1S nose is not carried forward into the next prototype, Rev K, whose nib (B1, study B) reaches ±1.0 mm. The nose stays a bench research module, and autowrite a research mode with it, because an accepted word needs about ±4–6 mm of reach. EXP-N09 would therefore run with the C1S research module, and it gates no Rev K claim. EXP-N10's pen part would also use that module, for its pen lift.

### EXP-N09: Autowrite with people
- **Status (DEC-050, 2026-09-30).** A research mode on the bench with the C1S nose; it gates no Rev K claim. The C1S module still pays its static side load (4.7 / 1.6 / 0.17 W at 35 / 50 / 75°, CALC; DEC-036).
- **Design.** Healthy adults first, then people with ET with up to 3 mm of tremor (DEC-049; ethics approval). The user switches autowrite on and chooses the text: typed, dictated, or a suggestion accepted with one action (DEC-049, DEC-056 (f); REQ-APP-008). The pen writes it at 2.5 and 3 mm x-height through the plan of REQ-CTRL-014, while the user sweeps along the line. The same person also writes the text by hand. Questionnaires on control and trust (users were frustrated when a tool disobeyed, LIT HAP-62).
- **Measurands.** Legibility by blinded readers; words written in full, half letters and hand-backs (coverage and completion time, REQ-WP-011); sweep speed chosen; perceived pull; mode errors; mode logs; the pen-written label in the app and the stroke record.
- **Predictions (SIM).**
  - nose2 (HW1): 99.2 % of letters and every word read with up to 1 mm of tremor; 98 % of words at 2 mm; 3.7 letters per second at a 9.5 mm/s sweep. One of six test writers needed a slower sweep; the pen now sets the speed per line (DEC-039). An uneven sweep (±30 %) and a drifting hand (±1 mm) were tolerated.
  - sim2 (DEC-049; 6 test writers, 3 mm peak at the hand, 5 and 8 Hz, a known text): 82 and 88 % of letters and 80 and 97 % of words read (after autocorrect), against 4 % of words with the ordinary pen; ink 67–83 µm from the planned letters. The nose used 6.55 of its 6.57 mm, so 3 mm is about its limit.
  - Study S (kinematics only): an accepted word at a 3 mm x-height is written in full in 95 % of cases at ±6 mm with the hand advancing, and in 23 % at ±4 mm (`bench_protocols.md` EXP-S19).
- **Claim type.** IA; the device writes, so no claim is made about the user's own writing. The app labels the text pen-written (DEC-049).
- **Decision.** Pass: autowrite of accepted text stays an explicit mode, up to 3 mm (DEC-039, DEC-049). Legibility worse than the person's own writing, mode errors, or reports of the pen "taking over": revisit DEC-039 and DEC-049.
- **Hardware.** DEC-049's hardware claim waits for DEC-046 (the nose's static load, EXP-J17) and for a page sensor that does not drift (REQ-RVJ-C05, EXP-J10). Since DEC-050 there is no autowrite hardware in the next prototype, and DEC-046 is resolved by B1, which the C1S module does not have.

<!-- AC-TABLE:EXP-N09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N09-01 | — | Legibility of the autowritten text (accepted text: typed, dictated or an accepted suggestion; DEC-049) minus that of the same person's own handwritten version (blinded readers, % words correct), 2.5 and 3 mm letters, healthy adults then people with ET with up to 3 mm of tremor; coverage, half letters and completion time reported beside it (REQ-WP-011) | ≥ 0 points | hypothesis | pass line of the nose v2 study; SIM: 99.2 % of letters and every word read with up to 1 mm tremor, 98 % of words at 2 mm (synthetic writers, docs/nose_v2.md s5.3); DEC-049 (sim2, 6 writers, 3 mm peak at the hand): letters 82 / 88 % and words (after autocorrect) 80 / 97 % at 5 / 8 Hz, against 4 % of words with the ordinary pen (results/sim2j/autowrite.json) | DEC-039; DEC-049 (revisit if users do not accept or control pen-written text); DEC-050: autowrite is a bench research mode with the C1S nose |
| AC-N09-02 | REQ-RVJ-N07 | Mode conformity: the pen drew letters only in the autowrite mode the participant switched on and only text the participant accepted (logs); the app and the stroke record label it pen-written; it wrote through the plan of REQ-CTRL-014 (no letter started that did not fit, no half letter); it never pushed the hand with the nose; and no participant reports the pen 'taking over' outside the mode (questionnaire) (all) | all met | requirement | REQ-RVJ-N07 (DEC-039; widened by DEC-049 and DEC-056 (f): accepted text, up to 3 mm, the pen-written label, the writing plan); users were frustrated when a handheld tool disobeyed (LIT HAP-62) | DEC-039; DEC-049; DEC-050: autowrite is a bench research mode with the C1S nose |
| AC-N09-03 | — | Participants who complete the accepted text in autowrite without a mode error and rate it acceptable (control and trust questionnaire) | ≥ 70 % | hypothesis | DEC-039 and DEC-049 revisit triggers (users do not accept or control pen-written text); 70 % engineering judgement, as AC-G07-01 | DEC-039; DEC-049; DEC-050: autowrite is a bench research mode with the C1S nose |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N09).
<!-- AC-TABLE:EXP-N09:END -->

### EXP-N10: Delayed ink acceptance
- **Status and overlap.** DEC-042 does not adopt delayed ink, so this test is needed only before any revival. It overlaps EXP-L03 (§19): run the two as one session design, with the shared tablet and copy-task blocks run once and scored for both.
- **Design.** Delayed ink at 0/50/100/150 ms, first on a tablet (no hardware needed), then with the nose and the pen lift. Randomised order within each participant; copied sentences.
- **Measurands.** Writing errors (duplicated or inserted strokes); change of letter size; preference.
- **Predictions.**
  - People notice 50–61 ms of inking latency (LIT HAP-90).
  - Delayed visual feedback raised duplicated strokes (LIT HAP-91) and caused inserted strokes and larger letters (LIT HAP-92); both abstracts only.
  - 100 ms of delayed ink needs about 4.5–5.3 mm of travel, and 40–55 % of the ink is laid after the hand has lifted, so it needs the pen lift (CALC).
- **Claim type.** Device burden.
- **Decision.** Fail (as expected): delayed ink stays off (DEC-039, DEC-042). Pass, together with EXP-L03 and a refill that holds contact on its own: delayed ink may be reconsidered, with the pen lift (DEC-042 revisit).

<!-- AC-TABLE:EXP-N10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N10-01 | — | Writing errors (duplicated or inserted strokes) with delayed ink at 50, 100 and 150 ms relative to 0 ms, copied sentences, tablet then pen; ratio of error rates at each delay | ≤ 1.0 | hypothesis | pass line of the nose v2 study (no increase over 0 ms); delayed visual feedback raised duplicated and inserted strokes (LIT HAP-91, HAP-92, abstracts only); inking latency is noticed from 50-61 ms (LIT HAP-90) -> may fail at ≥ 100 ms | DEC-039; DEC-042 (no delayed ink; reconsidered only with EXP-L03) |
| AC-N10-02 | — | Users who accept a delay of 100 ms or more (preference after the delayed-ink blocks) | ≥ 50 % | hypothesis | pass line of the nose v2 study; 100-200 ms of delay will be seen (LIT HAP-90); 40-55 % of delayed ink is laid after the hand lifts, so the pen lift is needed (CALC) | DEC-042 (delayed ink only if revived, with EXP-L03 and the pen lift) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N10).
<!-- AC-TABLE:EXP-N10:END -->

---

## 19. Rev J AI and control with people: EXP-L03, L06, L07, L08

Study L sets the Rev J control stack (DEC-042) and the app's AI (DEC-043). The pen's default tremor estimator listens harder only while a tremor line is present. The ink never trails the hand. Guided practice uses partial guidance that fades across sessions. The app completes words and can write in the user's style, always labelled as synthetic. The bench and offline protocols are in `bench_protocols.md` §45. The predictions come from `docs/ai_control_v2.md` and `results/ai2/ai2.json` (model HW1 on synthetic writers, SIMULATION; text and synthesis, CALCULATION).
- **Safety.** Tablet and app sessions need no powered pen. Sessions with the pen only after the bench gates of the build used: EXP-I05 for Rev H; EXP-N04, N05 and N08 for nose v2. Inclusion and exclusion as §3.2, including the rule on active implants.
- **Notes as data.** EXP-L06 and EXP-L07 use participants' own writing; the optional consents of §3.3 apply, and no note leaves the device without them.

### EXP-L03: Ink lag: is it noticed, and does it cause errors? (conditional; shares sessions with EXP-N10)
- **Status.** DEC-042 does not adopt delayed ink. This test is needed only before any revival, which would also need a refill that holds contact on its own (study L).
- **Overlap with EXP-N10 (§18).** Both test delayed ink on a tablet first, then with the nose. Run them as one session design: the tablet, the copy task and the lags are shared (EXP-N10: 0/50/100/150 ms; EXP-L03: 0/12/25/50/100 ms), and each shared block is run once and scored for both. EXP-L03 adds the just-noticeable-difference staircase and the pen-side lag limits of REQ-CTRL-012. The three delayed-ink papers are in the ledger once, as HAP-90, HAP-91 and HAP-92.
- **Design.** 12 controls and 12 people with ET or PD. A tablet with controlled inking latency (0, 12, 25, 50, 100 ms) and a stylus; then the ±6 mm bench nose. A staircase against 7 ms while writing words (the method of HAP-90). A copy task scored for added strokes and letters (HAP-91).
- **Measurands.** Just-noticeable lag (ms); added strokes or letters per 100 letters; letter size; writing time; in the pen part, the lag, its return to 0 and the hand–ink distance.
- **Predictions.**
  - People noticed added inking latency above a median of 50 ms (range 32–87 ms), and 59 ms with the hand visible (LIT HAP-90).
  - Delayed visual feedback made writers repeat strokes and letters, more with longer delays (LIT HAP-91, HAP-92; abstracts only).
  - SIM: a lag of up to 25 ms cut the ink error by 4 % and read no more words. The ball would trail the pen by a median 0.26–0.35 mm at 25 ms (CALC).
- **Claim type.** Device burden.
- **Decision.** Pass, with a refill that holds contact on its own: delayed ink may be reconsidered (DEC-042 revisit). Otherwise it stays out.

<!-- AC-TABLE:EXP-L03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L03-01 | — | Just-noticeable inking lag while writing words (staircase against 7 ms, tablet with controlled latency), median over participants (12 controls + 12 with ET or PD) | ≥ 25 ms | hypothesis | pass line of study L (the lag that would be used); people noticed added inking latency above a median of 50 ms (range 32-87 ms, n = 12) and 59 ms with the hand visible (LIT HAP-90) | DEC-042 (delayed ink reconsidered only if EXP-L03 passes and a refill holds contact on its own) |
| AC-L03-02 | — | Added strokes or letters per 100 letters in the copy task at a 25 ms lag, minus at 0 ms | < 1 per 100 letters | hypothesis | pass line of study L; delayed visual feedback made writers repeat strokes and letters, more with longer delays (LIT HAP-91, HAP-92; abstracts only) | DEC-042 |
| AC-L03-03 | REQ-CTRL-012 | Only if delayed ink is revived, bench-nose part (±6 mm nose): ink lag while writing, time for the lag to return to 0 after the hand stops or lifts, and share of pen-down time with the hand-ink distance inside the usable nose travel (all) | all met (≤ 25 ms; ≤ 5 ms; ≥ 99 %) | requirement | REQ-CTRL-012; SIM: mean lag 15 ms at ≤ 25 ms; the command exceeded 3 mm for 3.5 % of pen-down time at 25 ms (so a ±3 mm nose fails) and 6 mm for at most 0.65 % at any lag (docs/ai_control_v2.md s3.5) | DEC-042 (no delayed ink); DEC-036 (nose travel) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-L03).
<!-- AC-TABLE:EXP-L03:END -->

### EXP-L06: Does better prediction save writing effort in the app?
- **Design.** 20 adults and 10 people with ET write their own notes in the app with word completion, from the old n-gram (NG0) and from the mixture (within-subject, counterbalanced). Every model is also scored offline on their notes.
- **Continued in EXP-S14 (§22).** The same participants keep notes for 4 weeks, and study S's personalised model is scored on them as well: AC-L06-01 scores it against the 30 % line, and AC-S14-01 its gain over NG0.
- **Measurands.** Top-1 and top-3 accuracy on their own notes (word completion after the first letters; next word before its first letter, reported separately); accepted completions per 100 words; words per minute; latency per suggestion on the phone.
- **Predictions (CALC).**
  - The mixture (character transformer 0.3 + larger-corpus n-gram 0.7), letter two ahead, top-1: 41.0 % against 39.8 % (Tatoeba) and 40.7 % against 32.9 % (Common Voice); no gain on the app's note lines.
  - Next word before its first letter: 9–15 % top-1 and 18–28 % top-3 for every model.
  - Per next-word query on the study's CPU: 1.1 ms (larger-corpus n-gram) and 115 ms (mixture).
  - Weak suggestions cost more than they save (LIT EML-63).
  - Study S (CALC on two journals standing in for notes): word completion after one letter reached 52–56 % top-3 with the personalised model and 46–47 % with NG0, in 2.2–3.0 ms.
- **Claim type.** IA for note-taking in the app; no claim about handwriting.
- **Decision.** Below 30 % top-3 on their own notes: suggestions stay off by default (DEC-043 revisit). The mixture too slow on the phone: use the n-gram alone (DEC-043).

<!-- AC-TABLE:EXP-L06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L06-01 | REQ-APP-003 | Word completion after the first letters (the default suggestion, DEC-043), scored offline on each participant's own notes: top-3 accuracy, and latency per suggestion on the phone (both); next-word guessing before the first letter reported separately | both met (≥ 30 % top-3; ≤ 20 ms) | requirement | REQ-APP-003; next word before its first letter 18-28 % top-3 for every model (CALC, below 30 %); word completion not yet measured; per next-word query on the study's CPU 1.1 ms (larger-corpus n-gram) and 115 ms (mixture) (CALC) -> the mixture may miss 20 ms; study S (CALC on two journals): word completion after one letter 46-47 % top-3 with NG0 and 52-56 % with the personalised model (EXP-S14), 2.2-3.0 ms at the 95th percentile (docs/spelling_and_clarity.md T4) -> completions pass | DEC-043 (revisit if < 30 % top-3) |
| AC-L06-02 | — | Accepted completions per 100 words with the mixture, and words per minute against the old n-gram (NG0), within-subject and counterbalanced, 20 adults and 10 with ET (both) | both met (≥ 10 per 100 words; no loss in words per minute) | hypothesis | pass line of study L; weak suggestions cost more than they save (LIT EML-63: keystroke savings 50 % with advanced prediction against 18 % with basic); top-1 two letters ahead, mixture against NG0: 41.0 against 39.8 % (Tatoeba), 40.7 against 32.9 % (Common Voice), 27.1 against 28.3 % on app note lines (CALC) | DEC-043 (prediction mixture with word completion) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-L06).
<!-- AC-TABLE:EXP-L06:END -->

### EXP-L07: Does synthesis from the 20 s calibration look like the user's writing?
- **Design.** 20 writers write the calibration pangram. The app synthesises 10 words in each writer's style (sigma-lognormal, from 1–3 of their own letters). The writer and 5 raters judge the writer's own synthetic word against another writer's (two-alternative forced choice) and read the words.
- **Measurands.** Legibility (raters and the app's recogniser); how often writers choose their own style; the synthetic label on every line.
- **Predictions (CALC).** 96 % legible to the app's recogniser. Writer identified among six in 92–96 % of cases, on synthetic, font-based writers (which flatters identification). A learned generator on real letter shapes carried little style (65 % against 59 % for the class mean).
- **Claim type.** Measurement; no assistance claim.
- **Decision.** Fail: autowrite and templates use the calibration letters themselves only (DEC-043 revisit).

<!-- AC-TABLE:EXP-L07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L07-01 | REQ-APP-004 | Letters of the synthesised words (10 words per writer, sigma-lognormal from the writer's own calibration letters) read correctly by the app's recogniser and by 5 raters | ≥ 95 % | requirement | REQ-APP-004; prediction 96 % legible to the app's recogniser (CALC, synthetic glyph writers) | DEC-043 |
| AC-L07-02 | — | Trials in which the writer chooses their own synthetic word against another writer's (2AFC) | ≥ 70 % | hypothesis | pass line of study L; writer identified among six in 92-96 % of cases on synthetic, font-based writers, which flatters identification; a learned generator on real shapes carried little style (65 % against 59 % for the class mean) (CALC) | DEC-043 (revisit if style judged by people fails) |
| AC-L07-03 | REQ-APP-004 | App and record review: every synthesised line the app shows, stores or exports is labelled as synthetic, including the digital record of autowritten lines | conforms | requirement | REQ-APP-004; DEC-043; DEC-017 (immutable originals and provenance) | DEC-043 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-L07).
<!-- AC-TABLE:EXP-L07:END -->

### EXP-L08: Does guidance that fades across sessions help learning more than fixed guidance?
- **Design.** Children with dysgraphia, or adults learning an unfamiliar script. Guided copying over 5 sessions, randomised to fixed partial guidance (0.5) or to guidance that fades across sessions with the learner's own error. Retention without guidance after 1 day and after 1 week.
- **Measurands.** Unassisted retention distance to the target letters; letters read; the device's share of the ink motion over sessions; drop-rule events (logs).
- **Predictions.**
  - SIM (passive hand; learning is not modelled): partial guidance brought the ink 29 % closer (582 → 413 µm) with no loss of letters read. A per-letter assistance-as-needed law reacted one letter late.
  - LIT: the robot must relax its help faster than the learner learns (HAP-94); guidance effects mostly vanish when it is off (HAP-42/43/44).
- **Claim type.** LI (retention without guidance). Assisted performance during practice is reported separately (R4 of §1).
- **Decision.** Fading no worse at retention: fading becomes the practice default (DEC-042). Worse: keep fixed partial guidance, with catch trials.

<!-- AC-TABLE:EXP-L08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L08-01 | — | Unassisted retention distance to the target letters after 1 day and after 1 week: session-level fading relative to fixed partial guidance (0.5), children with dysgraphia (or adults learning an unfamiliar script) | ≤ 1.0 | hypothesis | pass line of study L (fading no worse than fixed); SIM cannot test learning (passive hand); the robot must relax its help faster than the learner learns (LIT HAP-94); guidance effects mostly vanish when off (HAP-42/43/44) | DEC-042 (guided practice fades across sessions) |
| AC-L08-02 | REQ-CTRL-013 | Session logs: the guidance level falls across sessions as the learner's own error falls (forgetting factor below 1, tolerance band), and guidance drops to 0 within 60 ms whenever the writer stays more than 2.5 mm from the target (every logged event) (both) | both met | requirement | REQ-CTRL-013; the drop rule T5 of HW1's guide mode; a per-letter assistance-as-needed law reacted one letter late (SIM) and is not used | DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-L08).
<!-- AC-TABLE:EXP-L08:END -->

---

## 20. Rev J integrated layout with people: EXP-J08, J09, J15, J18

DEC-044 joins the Rev J designs into one Ø24 mm pen. Its front is bigger than Rev H's, and with the end-cap it is heavier and back-heavy. DEC-045 (Rev J.1) adds a clear window to the front and a lighter end-cap: 84.3 g, and 112.7 g with the end-cap. EXP-J08, J09 and J15 use unpowered, printed dummies (from `results/revJ/revJ_pen_assembly.step` and `results/revJ1/revJ1_pen_assembly.step`, with and without the end-cap), so they need no safety gate beyond §3. EXP-J18 uses a powered heel-drive prototype, so it runs only after the EXP-D07 safety gate on the exact build (as §16). The bench protocols are in `bench_protocols.md` §46. The predictions come from `docs/revJ_design.md`, `docs/revJ1_design.md`, `results/revJ/` and `results/revJ1/` (CALCULATION), and for EXP-J18 from `docs/revJ_simulation.md` (SIMULATION).

### EXP-J08: Can writers see the ink?
- **Design.** 10 right- and left-handed writers. Printed fronts on dummy pens: Rev H; Rev J; Rev J with the C opening carried 10 mm into the sleeve (the chosen design); Rev J with a clear front sleeve. Randomised order; each writer copies lines at their own tilt; video from the eye (head-mounted camera); ratings.
- **Measurands.** How far behind the ball the fresh ink first shows (from the eye video); the writer's own tilt; visibility ratings.
- **Predictions (CALC, eye position ASSUMPTION).** From an eye 55° above the paper and 30° to the left of the pen's back direction, the Rev J front with the C opening shows the ink from 0.5 mm at 35° (88 % of directions) but not within 6 mm at 50–75°. Rev H showed it from 5 mm at 50°. Seen from the side, 0.5 mm at 35° and 50°. Real writers move their heads.
- **Claim type.** Device burden.
- **Decision.** Rev J no worse than Rev H: keep the front (DEC-044). Worse: consider the clear front sleeve, a wider opening, or a smaller ring (DEC-044 revisit).
- **Superseded for Rev J.1 (2026-09-29).** DEC-045 keeps the C opening and adds a clear window over the top 240° of the sleeve's first 15 mm. That front is tested in EXP-J15, which can share these sessions; EXP-J08's Rev H and Rev J fronts are then its comparisons.

<!-- AC-TABLE:EXP-J08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J08-01 | REQ-RVJ-I06 | Writers (10, right- and left-handed) who see the fresh ink within 3 mm behind the ball at their own tilt with the Rev J front (C opening carried 10 mm into the sleeve), from video at the eye | > 50 % | derived | REQ-RVJ-I06 ('most writers', read as more than half); superseded for Rev J.1 by AC-J15-01 (DEC-045: the clear window); over REQ-RVJ-I06's eye range this front shows the ink within 3 mm in 36 % of tilt x eye cases (CALC, results/revJ1/visibility.json); from the single assumed eye: 0.5 mm at 35°, not within 6 mm at 50-75° -> may fail, though real writers move their heads | DEC-044 (ink visibility) |
| AC-J08-02 | — | Visibility rating of the Rev J front with the C opening against the Rev H front, paired per writer | no worse than Rev H | hypothesis | pass line of the integrated design study; from the assumed eye Rev H showed the ink from 5 mm at 50° and Rev J not within 6 mm (CALC); superseded for Rev J.1 by EXP-J15 | DEC-044 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J08).
<!-- AC-TABLE:EXP-J08:END -->

### EXP-J09: Mass and balance
- **Design.** 10 writers, together with EXP-K03 where possible. Dummies of the Rev J.1 pen (DEC-045): 84 g (centre of mass 86 mm from the tip, the base pen) and 113 g (102.5 mm, with the end-cap). 10 min of writing with each, in random order.
- **Measurands.** Comfort and fatigue ratings (§3.6); acceptance of each dummy for a writing session.
- **Predictions (CALC).** The Rev J.1 base pen is 84.3 g with its centre of mass 6 mm in front of the thumb–index web. With the 29.6 g end-cap it is 112.7 g, 10.5 mm behind the web (Rev J: 129.2 g, 16 mm behind). The Rev H pen was 75 g, and a Rev H study declined a 28 g module partly because it took the pen over 100 g (DEC-024).
- **Claim type.** Device burden.
- **Decision.** Accepted: the 120 g limit with the end-cap in REQ-EC-001 stands (with EXP-K03). Not accepted: a lighter end-cap (in study K's family the 28.0 g member still passed rule R-T1 in SIM) or no end-cap (DEC-038, DEC-045).
- **Status (DEC-051).** The end-cap is out of the product. The 113 g dummy now stands only for a possible return through REQ-WP-001; the 84 g base pen is the product's.

<!-- AC-TABLE:EXP-J09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J09-01 | REQ-EC-001 | Writers (10) who rate the 113 g dummy (centre of mass 102.5 mm from the tip, the Rev J.1 pen with the end-cap) acceptable for writing after 10 min, with the 84 g dummy (86 mm, the base pen) as the comparison (comfort and fatigue ratings, with EXP-K03) | ≥ 70 % | hypothesis | checks the 120 g limit with the end-cap of REQ-EC-001 (DEC-045 dropped the provisional 130 g of DEC-044); prediction 112.7 g with the centre of mass 10.5 mm behind the web (CALC, results/revJ1/budgets.json); 70 % engineering judgement, as AC-K03-04 | REQ-EC-001 limit with the end-cap; DEC-038; DEC-045 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-J09).
<!-- AC-TABLE:EXP-J09:END -->

### EXP-J15: The clear window: can writers see the ink?
- **Design.** 10 right- and 10 left-handed writers; for left-handed writers the eye positions mirror. Printed fronts on dummy pens: the Rev J.1 front (the C opening and a clear hard-coated PC window over the top 240° of the sleeve's first 15 mm, DEC-045) and Rev J's front (the C opening only). Randomised order; each writer copies lines at their own tilt; eye tracking, or video from the eye (head-mounted camera); ratings. It can share sessions with EXP-J08: the same dummy pens, writers and cameras, with EXP-J08's Rev H front as a further comparison. The window's wear test is in `bench_protocols.md` §46.
- **Measurands.** How far behind the ball the fresh ink first shows; the writer's tilt and eye position (height above the paper, angle to the writer's side); visibility ratings.
- **Predictions (CALC, eye range ASSUMPTION).** Over tilts of 35–75° and eyes 40–70° above the paper and 0–60° to the writer's side, the Rev J.1 front shows the ink within 3 mm in 61 % of cases and within 1 mm in 47 % (Rev J: 36 % and 22 %). At 50° with the eye 55° up and 30° to the side: from 3.0 mm (Rev J: not within 6 mm). A clear top on the ring would add only 3 points; a 30 mm window with a clear ring reaches 75 % within 3 mm, but a window longer than 15 mm sits under the finger pads. No writing-posture source with eye angles could be opened.
- **Claim type.** Device burden.
- **Decision.** Most writers see the ink within 3 mm: keep the window (DEC-045). Not: a longer window or a clear ring (DEC-045 revisit). The window hazes in the wear test: another hard coat.

<!-- AC-TABLE:EXP-J15:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J15-01 | REQ-RVJ-I06 | Writers (10 right- and 10 left-handed) who see the fresh ink within 3 mm behind the ball at their own tilt with the Rev J.1 front (the C opening and a clear hard-coated PC window over the top 240° of the sleeve's first 15 mm, DEC-045), from eye tracking or video at the eye | > 50 % | derived | REQ-RVJ-I06 ('most writers', read as more than half; eye range 40-70° up and 0-60° to the writer's side); prediction: ink within 3 mm in 61 % and within 1 mm in 47 % of tilt x eye cases (Rev J 36 % and 22 %) (CALC, results/revJ1/visibility.json; eye range ASSUMPTION) -> narrow | DEC-045 (the window) |
| AC-J15-02 | — | Visibility rating of the Rev J.1 front against Rev J's front (C opening only), paired per writer | better than Rev J's front | hypothesis | prediction: ink within 3 mm in 61 against 36 % of tilt x eye cases, median first view 1.75 against 4.25 mm behind the ball (CALC, results/revJ1/visibility.json); engineering judgement | DEC-045 (the window) |
| AC-J15-03 | — | Haze of hard-coated PC window coupons after the abrasion test (Taber or steel wool), the pocket-key test and wiping with common cleaners (haze meter; uncoated PC and PMMA as references) | ≤ 5 % | hypothesis | pass line of the Rev J.1 study; coated PC scratches about like PMMA (2H-4H), uncoated HB-2H (LIT AMF-159, a secondary source); no prediction of haze | DEC-045 (the window material) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-J15).
<!-- AC-TABLE:EXP-J15:END -->

### EXP-J18: Does the heel wheel distort writing, and do writers adapt?
- **Design.** Healthy writers (n from a pilot, §11 rule). Each writes their own text with the heel wheel retracted, free (steer-only) and in its tremor mode, in random order, for 10 min in each mode; the same text at the start and at the end of each mode. The Rev J heel-drive prototype, after the EXP-D07 safety gate on the exact build; the page-sensor log; R3 scans.
- **Measurands.** Letter distortion against the writer's own writing with the wheel retracted (the same text, RMS after alignment), less the writer's own repeat-to-repeat distance with the wheel retracted; its change over the 10 min (adaptation); felt force; ratings.
- **Predictions (SIM, `docs/revJ_simulation.md` §6.1, §8.2).** sim2's writer, who does not adapt, was moved 324–503 µm (mean 403) by the tremor mode: the wheel steers after the pen with a lag and its tyre resists sideways motion (1500 N/m), so fast turns in the letters are pulled out of shape. The grip-force change was 167 mN rms, against 21 mN with the nose alone. A writer who has learned the wheel was not simulated.
- **Claim type.** Device burden.
- **Decision.** A mode within 25 µm after adaptation may be offered in free writing (DEC-048 revisit). Otherwise the wheel stays retracted by default (DEC-048).

<!-- AC-TABLE:EXP-J18:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J18-01 | REQ-RVJ-C02 | Healthy writers' own tremor-free writing with the heel wheel free and in its tremor mode, after 10 min of writing with it: letter distortion against their own writing with the wheel retracted (the same text; page-sensor log and R3 scans; RMS after alignment), less their own repeat-to-repeat distance with the wheel retracted; each mode | ≤ 25 µm | hypothesis | REQ-RVJ-C02 applied to people after adaptation; sim2's writer, who did not adapt, was moved 324-503 µm (mean 403) by the tremor mode (SIM, results/sim2j/et.json) -> predicted to FAIL without adaptation; adaptation within 10 min is untested | DEC-048 (revisit if writers adapt within 10 min) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-J18).
<!-- AC-TABLE:EXP-J18:END -->

---

## 21. Real recorded data with people: EXP-R01, R03 (study R; DEC-054, DEC-055)

Study R (`docs/real_data.md`) tested the pens in simulation on real handwriting of healthy adults and real tremor of patients, composed in the model's hand. Two questions need people: what patients' own writing and tremor look like with the pen (EXP-R01), and whether the AI reader's "words you can read" match what people read (EXP-R03). The offline and bench parts (EXP-R02, R04…R07) are in `bench_protocols.md` §48.
- **DEC-054.** Real recorded inputs and the results card are the standard test. Tremor classes are named in mm at the tip (peak = √2 × RMS of the major axis in f0 ± 2 Hz): mild 0.03–0.16 mm, moderate 0.16–0.51 mm, severe above 0.51 mm, typically 1.7 mm. These are zero-to-peak values. EXP-H01 reports peak-to-peak, about twice as large for a steady tremor; REQ-USR-002 is now stated zero-to-peak (REQ-DATA-004).
- **DEC-055.** No legibility claim at severe tremor until a causal tracker passes on real inputs (AC-R02-01): at least 2 more readable words out of 10 than the ordinary pen, with the 95 % interval above 0, and ≤ 25 µm of change to clean real writing as the mean over the test writers, with no writer above 50 µm.
- **Ethics.** Both studies are covered by EXP-H01's approval and the common elements of §3. EXP-R01's recordings are EXP-H01's. Showing a participant's ink to a reading panel (EXP-R03) needs the optional consent of §3.3.

### EXP-R01: Patients' own writing and tremor at the pen tip, with ink (the recording part of EXP-H01)
- **Relation to EXP-H01.** Not a separate visit. EXP-R01 is the recording part of EXP-H01 (§4): the same participants (ET, PD, older and healthy adults), the same sessions and tasks, with EXP-H01's retest as the second session. It adds REQ-DATA-009's recording rules and reports the tip tremor in DEC-054's classes beside EXP-H01's peak-to-peak values.
- **Design.** Sentences on ruled paper over a digitiser that records the ink path and hover at ≥ 200 points/s (R11's tablet protocol, `bench_protocols.md` §47), with the instrumented pen's IMU (R11's Ø24 mm recording pen first). Handedness, grip, posture, medication state and device configuration are recorded. Participant- and session-level splits are fixed before any analysis (REQ-DATA-001, REQ-DATA-009).
- **Measurands.** Writing speed, stroke times, letter size (micrographia) and velocity spectrum; each participant's tip tremor in DEC-054's convention and its class; the pen's IMU spectra; the controls' tremor-free writing checked against REQ-DATA-003 before it serves as clean writing.
- **Predictions (CALC on recorded data).** PD tip tremor while drawing spirals is mostly 0.1–0.3 mm. DEC-054's boundaries are the median (0.16 mm) and 90th percentile (0.51 mm) of 24 tuning PD patients' spirals; on 25 test patients the shares were 60/24/16 % against 50/40/10. Spirals on a tablet are a floor: patients who could not draw are missing (LIT PDT-82). No open recording of ET at the pen tip exists, so ET's sizes here are the first. The composed inputs use healthy writers' letters; patients write slower and smaller, and adapt to their tremor.
- **Claim type.** None (measurement).
- **Decision.** The recordings replace the composed inputs in EXP-R02 and in the tracker studies (EXP-L01, L02, L04). Class boundaries in writing outside AC-R01-02: revisit DEC-054's classes.

<!-- AC-TABLE:EXP-R01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R01-01 | REQ-DATA-009 | EXP-R01/H01 recordings (protocol and data review before any analysis): ink on paper over a digitiser with hover tracked, at the stated rate and resolution; the pen's IMU with acquisition and availability time stamps; handedness, grip, posture, medication state and device configuration recorded; participant- and session-level splits fixed before analysis (all) | all met (≥ 200 points/s; ≤ 0.05 mm; conforms) | requirement | REQ-DATA-009 (DEC-054; independent review s11); R11's tablet recorder logs every pen sample with time stamps, and AC-T06-04 must show a median ≥ 200 Hz; the tablet reports 0.01 mm but is accurate to about ±0.25 mm (LIT CON-101), so AC-H01-08 registers the chain per stroke | DEC-054 (the recordings replace the composed inputs); EXP-R02, EXP-L01, L02, L04 |
| AC-R01-02 | REQ-DATA-004 | Median and 90th percentile of the PD participants' tip tremor during sentence copying (EXP-R01, DEC-054's convention: peak = sqrt(2) x RMS of the major axis in f0 ± 2 Hz, by the realdata tremor-library method on pen-down runs), each with a 95 % bootstrap interval over participants | both intervals include DEC-054's boundaries (0.16 mm; 0.51 mm) | hypothesis | DEC-054's classes are the median (0.16 mm) and 90th percentile (0.51 mm) of 24 tuning PD patients' tip tremor while drawing spirals, checked on 25 test patients (60/24/16 % against 50/40/10; CALC on DATA, UCI); spirals on a tablet are a floor (patients who could not draw are missing, LIT PDT-82) and writing is not spirals: no prediction for writing | DEC-054 (the classes move if a census in writing gives other boundaries) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-R01).
<!-- AC-TABLE:EXP-R01:END -->

### EXP-R03: Does the AI reader's "words you can read" match people?
- **Design.** A blinded panel of naive readers (n from a pilot, §11 rule) transcribes the rendered ink of study R's test cases (every pen and class) and, with consent, EXP-R01 ink. Each note is read by several readers, in random order, blind to pen and class. Scoring is literal, as the AI reader's: exact words, no correction.
- **Measurands.** Words read out of 10 per note by the panel (the median reader) and by the AI reader (TrOCR base, literal); the tracker-minus-ordinary-pen difference in words, panel against reader; the clean-ink ceiling for each.
- **Predictions (SIM).** The AI reader reads 6.8 of 10 words of the clean real test notes, and 0.3–0.7 of 10 at the severe class with an ordinary pen. Its decoder has a language prior from its training text, and the test phrases include rare words. No prediction for people. UNIPEN writing is for research use only: the panel may see it, and results hold statistics only (REQ-DATA-006).
- **Claim type.** None (the reader's validity).
- **Decision.** Within AC-R03-01: the reader's words stand for people in DEC-055 and in the results cards. Outside: DEC-055 is judged by the panel, and the results cards report the panel's reads.

<!-- AC-TABLE:EXP-R03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R03-01 | REQ-DATA-008 | Tracker-minus-ordinary-pen difference in words read out of 10, the literal AI reader (TrOCR base) against the blinded human panel (literal scoring, median reader), paired per note, on study R's test cases at the severe and moderate classes: the 95 % interval of the mean difference between reader and panel | within ±1 word | derived | made to protect AC-R02-01: half of DEC-055's +2-word line, so the reader alone cannot flip DEC-055's verdict (derived); REQ-DATA-008 (a literal reader); the reader reads 6.8 of 10 words of the clean real test notes, and its decoder has a language prior from its training text (SIM, docs/real_data.md); no measurement with people | DEC-055 (judged by the reader or by the panel); DEC-054 (the results card) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-R03).
<!-- AC-TABLE:EXP-R03:END -->

---

## 22. Spelling help, text prediction and clearer handwriting with people: EXP-S10…S15, S17, S18 (study S; DEC-056, DEC-057)

Study S (`docs/spelling_and_clarity.md`) built the language layer of the pen and the app (DEC-056) and set how guidance keeps letters whole (DEC-057). Its numbers are CALC and SIM on real letters of held-out writers and real misspellings of held-out children, with the writers' responses ASSUMED. Nothing was measured on people or on a pen. The offline and bench parts (EXP-S16, S19, S20, S21) are in `bench_protocols.md` §49.
- **DEC-056.** The ink record, the transcript and the pen's writing plan are kept apart (REQ-APP-005). A causal streaming recogniser reads the letters, calibrated on the user's own. Spelling help abstains when unsure and never flags names, numbers or words the writer marks (REQ-APP-007). The default cue is a tick at the next pause; a tick on the suspect letter plus a pen lift comes only once mid-word flags are reliable, and EXP-S18 decides. Suggestions and completions come only at pauses (REQ-APP-008). The pen writes only accepted text (REQ-CTRL-014; EXP-N09 in §18).
- **DEC-057.** Guidance keeps letters whole (EXP-D08 in §16, after EXP-S16). The shape assist is not adopted, so EXP-S15 runs only after a redesign shows a gain in simulation.
- **Safety.** App and tablet sessions need no powered pen. Sessions with the pen's LRA tick or pen lift only after the bench gates of the build used (EXP-N04 and N05 on the exact build). Inclusion and exclusion as §3.2, including the rule on active implants.
- **Shared sessions.** EXP-S10 records inside EXP-H01/R01 sessions. EXP-S12 and S18 share sessions: the app-afterwards block and the tick-on-the-suspect-letter block are run once and scored for both. EXP-S14 continues EXP-L06 with the same participants. EXP-S17's writers come from EXP-S10 and EXP-S11 where possible.
- **Writing and notes as data.** The consents of §3.3 apply. EXP-S11 releases a corpus, so its consent must cover release under an open licence. Training a model (EXP-S17) uses only recordings whose consent covers it (item iii).

### EXP-S10: Letters read while people write on paper with the pen
- **Relation to EXP-H01 and R01.** Not a separate visit where it can be avoided. The calibration pangram and three short notes are added to the tasks of EXP-H01/R01 sessions (about 10 min) for 20 healthy adults and 10 writers with ET or PD, with the same digitiser and pen (R11). The recognition is offline.
- **Design.** Each writer writes the calibration pangram (one sample of every letter), then three notes. The pen's page sensor, or the digitiser under the paper, records. Offline replay through the streaming recogniser, with and without the writer's calibration letters. The recogniser's time per point is measured on a mid-range phone.
- **Measurands.** Letters named correctly at 50 % and 100 % of each letter; the commit point; time per point on the phone.
- **Predictions (CALC on real letters of 20 held-out UJI writers on a tablet; T1).** New writers: 82 % at the letter's end and 52 % halfway. Calibrated: 86 % and 60 %. With 1 mm of tremor: 73 % (new writer) and 76 % (calibrated) at the end. With the next-letter prior: 88 % and 74 % (uncalibrated). On another tablet and writer only 40 %, so the capture convention matters. 0.19 ms per point on the study's CPU; about 1.8 ms on a 128 MHz Cortex-M33.
- **Claim type.** None (measurement).
- **Decision.** Pass: the recogniser feeds spelling help and completions (DEC-056 (b)). Fail: more calibration or the language prior first, and mid-word cues stay off.

<!-- AC-TABLE:EXP-S10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S10-01 | REQ-APP-001 | Letters named correctly by the streaming recogniser, calibrated with the writer's own pangram letters, in offline replay of the notes recorded on paper (EXP-S10: 20 adults and 10 writers with ET or PD): at the letter's end and at half the letter (both) | both met (≥ 90 % at the end; ≥ 70 % at half) | hypothesis | pass line of study S; CALC on real letters of 20 held-out UJI writers on a tablet: calibrated 86 % at the end and 60 % halfway, new writers 82 % and 52 %, 73-76 % at the end with 1 mm tremor; with the next-letter prior 88 % and 74 % (uncalibrated) (docs/spelling_and_clarity.md T1; results/ai3/ai3.json) -> predicted to FAIL both lines unless writing on paper reads better than tablet letters | DEC-056 (b) (the recogniser feeds spelling help and completions); mid-word cues |
| AC-S10-02 | — | Recogniser time per pen sample on a mid-range phone (the app's build) | ≤ 5 ms | hypothesis | pass line of study S; 0.19 ms per point on the study's CPU (one thread) and about 1.8 ms on a 128 MHz Cortex-M33 (int8, CALC; docs/spelling_and_clarity.md T1) | DEC-056 (b) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-S10).
<!-- AC-TABLE:EXP-S10:END -->

### EXP-S11: An English corpus of dyslexic misspellings in context, with consent
- **Design.** 30 adults and 30 children with a dyslexia assessment write free text and dictation by hand. Two people transcribe. Every misspelling is tagged with its target (Mitton's format). The corpus is released under an open licence. Recruitment can share the dyslexia cohorts of EXP-W05, S12 and S18.
- **Measurands.** Errors per word; the shares of non-word, real-word and word-boundary errors; the position of the first wrong letter.
- **Predictions.** No open English dyslexic corpus with consent was found. In Holbrook's collection of 1960s schoolchildren (used by study S with the Birkbeck lists; neither states a licence), the test children misspelled 5–23 % of their words; the first wrong letter was typically letter 3, and 17 % of errors showed only at the word's end (CALC, T2).
- **Claim type.** None (data).
- **Decision.** Released: it replaces Birkbeck and Holbrook for tuning and testing the checker (rule S1). Not released: the checker stays on sources without a stated licence, used for evaluation only.

<!-- AC-TABLE:EXP-S11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S11-01 | — | Corpus of handwritten free text and dictation from 30 adults and 30 children with a dyslexia assessment: words transcribed by two people, every misspelling tagged with its target (Mitton's format), and consent for release under an open licence (all) | all met (≥ 20 000 words; ≥ 2 000 tagged errors; release consented) | hypothesis | pass line of study S; no open English dyslexic corpus with consent was found, and the Birkbeck lists and Holbrook's 1960s schoolchildren state no licence (docs/spelling_and_clarity.md, assumptions); Holbrook's test children misspelled 5-23 % of their words (CALC, T2) | the checker's tuning and test data (rule S1); REQ-DATA-006 for the release |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S11).
<!-- AC-TABLE:EXP-S11:END -->

### EXP-S12: Does a tick while writing help people with dyslexia fix misspellings, and does it annoy them?
- **Design.** Within subject, counterbalanced: no cue; a tick on the suspect letter; a tick plus a pen lift when very sure; the app afterwards. Free writing and dictation with the pen. 20 adults with dyslexia and 20 controls. Shares sessions with EXP-S18.
- **Measurands.** Misspellings left on paper per 100 words; writing time; false alarms and how well they are tolerated (NASA-TLX, a sense-of-agency questionnaire); the share of ticks noticed; wrong-letter fragments after a lift; coverage and missing strokes when the pen lifts (REQ-WP-011).
- **Predictions (SIM on 11 test children's real errors; responses ASSUMED; T3).** With the letters known: the tick on the suspect letter fixed 2.6 of 10 misspellings on paper (1.4–3.4) at +16 % time; the tick plus lift 3.4 (2.4–4.1) at +15 %; 2.3 false cues per 100 correct words; a wrong-letter fragment about once per 100 words. When the pen reads the letters itself, mid-word cues fire about 40 times per 100 correct words, so DEC-056 (d) keeps them off until mid-word flags use the recognition-aware score.
- **Claim type.** IA (spelling on paper while the pen cues); no LI claim.
- **Decision.** Pass: the mid-word tick may become an option (with EXP-S18; DEC-056 (d)). Fail: the cue stays at the next pause.

<!-- AC-TABLE:EXP-S12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S12-01 | — | Misspellings left on paper per 100 words with the tick on the suspect letter, relative to no cue (within subject, 20 adults with dyslexia, free writing and dictation with the pen), with the writing time and the share of ticks noticed (all) | all met (≥ 30 % fewer; time no more than 20 % longer; ≥ 85 % noticed) | hypothesis | pass line of study S; SIM with the letters known (11 test children's real errors, writer responses ASSUMED): the tick on the suspect letter fixed 2.6 of 10 misspellings (1.4-3.4) at +16 % time; with the pen's own reading 2.1-2.3 of 10 at about 40 false cues per 100 correct words (docs/spelling_and_clarity.md T3) -> predicted to FAIL the 30 % | DEC-056 (d) (mid-word cues only once reliable); with EXP-S18 |
| AC-S12-02 | REQ-APP-007 | Spelling help in the EXP-S12 sessions (the pen's own reading, the calibrated score): false alarms per 100 correct words, and names, numbers and words the writer marked that were flagged (both) | both met (≤ 2 per 100; none flagged) | requirement | REQ-APP-007 (DEC-056 (c)); SIM: word-level 1.7 (new writer) and 2.3 (calibrated) false alarms per 100 correct words with the post-hoc W5 score; mid-word flags with raw recognised letters about 40 per 100 (docs/spelling_and_clarity.md T3, T8) -> the mid-word arms fail unless they use the recognition-aware score | DEC-056; spelling help on by default |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-S12).
<!-- AC-TABLE:EXP-S12:END -->

### EXP-S13: Is a tick felt while writing, and how small can it be?
- **Design.** An LRA in a pen body. A two-alternative forced choice and a yes/no detection task, while writing at 3 cm/s and at rest. 5 pulse lengths and 3 amplitudes. Adults, including adults with dyslexia (n from a pilot, §11 rule).
- **Measurands.** Detection rate; reaction time; the smallest pulse detected in 95 % of trials while writing; ink jitter during the tick.
- **Predictions.** None measured for a tick in a pen while writing. Study S's cue simulation assumed that writers notice it.
- **Claim type.** None (measurement).
- **Decision.** The pen uses the smallest tick detected in ≥ 95 % of trials while writing. None reaches it: cues stay on the phone.

<!-- AC-TABLE:EXP-S13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S13-01 | — | Detection of an LRA tick in a pen body while writing at 3 cm/s (yes/no task) at the chosen pulse, the smallest of 5 pulse lengths and 3 amplitudes that reaches the line (2AFC and yes/no, while writing and at rest) | ≥ 95 % | hypothesis | pass line of study S; no measurement of a tick in a pen while writing; the cue simulation assumed that writers notice it (rule S4; docs/spelling_and_clarity.md T3) | the pen's physical cue (DEC-056 (d)); REQ-APP-008 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S13).
<!-- AC-TABLE:EXP-S13:END -->

### EXP-S14: Personal text prediction on the user's own notes
- **Relation to EXP-L06 (§19).** The same participants and notes where consent allows: EXP-L06's session is followed by 4 weeks of notes in the app, and every model is replayed offline on them. REQ-APP-003's 30 % line is AC-L06-01, which scores the personalised model too; this study adds its gain over NG0.
- **Design.** 20 users keep notes in the app for 4 weeks. Offline replay of NG0, NG1x and the personalised model on their own notes, the model adapting as they write.
- **Measurands.** Top-3 accuracy after 0, 1 and 2 letters; letters saved; latency.
- **Predictions (CALC on two public-domain journals standing in for notes; T4).** After one letter, top 3: personalised 56 % and 52 %, NG0 46 % and 47 % (+10 and +5 points). The next word before its first letter: 22–24 %. 2.2–3.0 ms at the 95th percentile on the study's CPU. Letters saved from a top-3 list: 46–50 %.
- **Claim type.** IA (the app); no handwriting claim.
- **Decision.** Pass: the personalised model is the default for completions (DEC-056 (e)). Fail: NG1x without personalisation.

<!-- AC-TABLE:EXP-S14:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S14-01 | REQ-APP-003 | Top-3 accuracy of word completion after one letter on each user's own notes over 4 weeks (offline replay, the model adapting as the user writes): the personalised model minus NG0 | ≥ 5 points | hypothesis | pass line of study S; CALC on two public-domain journals standing in for notes: 56 against 46 % and 52 against 47 % (+10 and +5 points; docs/spelling_and_clarity.md T4) -> marginal on one; the ≥ 30 % line of REQ-APP-003 is AC-L06-01, which scores this model too | DEC-056 (e); the personalised model as the default for completions |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S14).
<!-- AC-TABLE:EXP-S14:END -->

### EXP-S15: Shape assist with real writers (only after a redesign shows a simulated gain)
- **Status.** DEC-057 does not adopt the shape assist: within safe limits it changed the letters read by less than one point. This study runs only after a redesign shows a gain in simulation (for example on children's writing, EXP-S21).
- **Design.** Writers with ET (1–2 mm tremor) and writers with poor handwriting write words with the pen, the assist off and on in blinded order. A panel of 5 readers transcribes the ink.
- **Measurands.** Letters read by people; RMS nose motion on clean writing; sense of agency; after-effect with the assist off.
- **Predictions (SIM on real letters of 20 new writers in HW1; T6).** Letters read without and with the assist: 41.4 and 41.9 % at 1 mm and 8 Hz; 47.0 and 47.3 % with real ET tremor. Clean writing moved 23 µm on average, 121 µm in the worst word.
- **Claim type.** IA; the after-effect block is exploratory (§1, R3).
- **Decision.** Pass: the shape assist may be offered (DEC-057 revisit). Fail: it stays out.

<!-- AC-TABLE:EXP-S15:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S15-01 | — | Shape assist on and off in blinded order, writers with ET (1-2 mm tremor): letters read by a panel of 5 readers; RMS nose motion on clean writing; sense of agency (all) | all met (≥ 10 % more letters read; ≤ 25 µm on clean writing; no loss of agency) | hypothesis | pass line of study S; SIM on real letters of 20 new writers in HW1: letters read 41.4 -> 41.9 % at 1 mm, 8 Hz and 47.0 -> 47.3 % with real ET tremor; clean writing moved 23 µm on average and 121 µm in the worst word (docs/spelling_and_clarity.md T6) -> predicted to FAIL; runs only after a redesign shows a simulated gain (DEC-057) | DEC-057 (the shape assist stays out unless this passes) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S15).
<!-- AC-TABLE:EXP-S15:END -->

### EXP-S17: Word recognition on the pen's own recordings, print and joined-up
- **Design.** 30 writers (10 with ET or PD, 10 with dyslexia) write two sessions a week apart on paper with the pen (page sensor and IMU). Two people transcribe literally. A causal CTC recogniser is trained on 20 writers and tested on 10 held-out writers and on the held-out sessions of the calibrated writers. Writers come from EXP-S10 and S11 where possible.
- **Relation to EXP-C01.** EXP-C01 tests the app's default recogniser on EXP-H01/H06 ink (AC-C01-01: CER ≤ 8 %). This study tests the pen's own streaming recogniser, with sessions held out as well as writers (REQ-APP-006).
- **Measurands.** CER and WER with and without the language model; latency; segmentation errors; print and joined-up separately.
- **Predictions (SIM on real letters of 20 held-out UJI writers, words assembled with ASSUMED print spacing; T7).** With the language model: CER 9.1 % and WER 19.8 % (writer-disjoint), 9.2 % and 20.2 % (session-disjoint). Without it: CER 20–23 %, WER 51–55 %. With tight spacing: 10.5 % and 22.5 %. Joined-up writing not tested.
- **Claim type.** None (measurement).
- **Decision.** The report comes before any spelling cue is on by default (REQ-APP-006). More than 20 % of words read wrong: DEC-056 is revisited; the cue stays at the pause, and suggestions come only on request.

<!-- AC-TABLE:EXP-S17:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S17-01 | REQ-APP-006 | Recognition report before any spelling cue is on by default (review): CER and WER of the pen's streaming recogniser on held-out writers and on held-out sessions of the calibrated writers, each with and without the language model, print and joined-up separately | conforms | requirement | REQ-APP-006 (DEC-056; the review's G7); EXP-C01 reports the app's default recogniser (AC-C01-01) | spelling cues on by default (DEC-056) |
| AC-S17-02 | — | Word error rate of the causal recogniser, calibrated, with the language model, on print, on held-out writers and on held-out sessions of the pen's own recordings | ≤ 20 % | derived | DEC-056's revisit trigger (EXP-S17 reads more than 20 % of words wrong), so derived; study S proposed 25 % as the pass line; SIM on real UJI letters with ASSUMED print spacing: 19.8 % (writer-disjoint) and 20.2 % (session-disjoint), 22.5 % with tight spacing (docs/spelling_and_clarity.md T7) -> marginal | DEC-056 |
| AC-S17-03 | REQ-APP-001 | Character error rate of the same recogniser, calibrated, with the language model, on print, held-out writers and sessions | ≤ 8 % | hypothesis | pass line of study S, the same 8 % as AC-C01-01 for the app's default recogniser; SIM on real UJI letters: 9.1 % (writer-disjoint) and 9.2 % (session-disjoint), 10.5 % with tight spacing (docs/spelling_and_clarity.md T7) -> predicted to FAIL narrowly | DEC-056 (b); comparison with the app's default recogniser (DEC-013) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-S17).
<!-- AC-TABLE:EXP-S17:END -->

### EXP-S18: Suggestions at pauses or cues while writing: accuracy against fluency
- **Relation to EXP-N09, N10 and S12.** EXP-S18, N09 and N10 are the tests of DEC-049's condition that users accept and control pen-written text: N09 with autowrite of accepted text, N10 with delayed ink, and S18 with suggestions and cues on the writer's own writing. They use the same control and trust questionnaire and the same mode logs. A suggestion accepted here is the kind of text that N09's autowrite writes (DEC-056 (f)); in S18 the writer writes it by hand. S18 shares sessions with EXP-S12.
- **Design.** Within subject, 24 adults with dyslexia, counterbalanced: the app afterwards; a tick at the next pause with up to 3 suggestions (read aloud if wanted); a tick on the suspect letter (with the pen lift when very sure, as EXP-S12); opt-in automatic correction. Dictation and free writing.
- **Measurands.** Misspellings left on paper; suggestion lists read per 100 words; pauses and writing speed; harmful edits (correct words made wrong); NASA-TLX; preference; the app's and the pen's logs (the three outputs, REQ-APP-005).
- **Predictions (SIM on 11 test children's real errors; responses ASSUMED; T3, T8).** The tick at the next pause fixed 3.0 of 10 misspellings on paper (1.6–4.0), with 6.4 suggestion lists read per 100 words, +17 % writing time and 0.15 correct words made wrong per 100. The app afterwards fixes none on paper (+5 %). The tick plus lift fixed 3.4 of 10, with 7.7 cues felt mid-word per 100 words. The opt-in automatic correction changed no correct word and fixed almost nothing at today's reading accuracy.
- **Claim type.** IA (spelling while writing); no LI claim.
- **Decision.** Pause offers pass (AC-S18-01): they stay the default cue (DEC-056 (d)). Mid-word cues better without costing flow (AC-S18-02): they become an option. Pause offers fail: spelling help stays in the app afterwards.

<!-- AC-TABLE:EXP-S18:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S18-01 | REQ-APP-008 | Tick at the next pause with up to 3 suggestions against the app afterwards (within subject, 24 adults with dyslexia, dictation and free writing): misspellings left on paper per 100 words, writing speed, and correct words made wrong per 100 words (all) | all met (fewer left; no more than 10 % slower; ≤ 0.5 harmful edits per 100 words) | hypothesis | pass line of study S; SIM (11 test children's real errors, responses ASSUMED): the pause offer fixed 3.0 of 10 misspellings on paper (1.6-4.0) and the app afterwards none, at +17 % against +5 % writing time (about 11 % slower), with 0.15 correct words made wrong per 100 (docs/spelling_and_clarity.md T3) -> the speed line is marginal | DEC-056 (d) (the default cue); REQ-APP-008 |
| AC-S18-02 | — | Tick on the suspect letter (with the pen lift when very sure) against the tick at the next pause, same sessions: misspellings left on paper per 100 words, writing speed, and workload (NASA-TLX) (all) | all met (fewer left; no more than 10 % slower; workload no higher) | hypothesis | DEC-056 (d): mid-word cues only once mid-word flags are reliable, and EXP-S18 decides; the 10 % is AC-S18-01's line (engineering judgement); SIM with the letters known: tick plus lift 3.4 of 10 fixed at +15 % against 3.0 at +17 %, with 7.7 cues felt mid-word per 100 words; with raw recognised letters mid-word cues fire about 40 times per 100 correct words (docs/spelling_and_clarity.md T3) | DEC-056 (d) (tick plus lift as an option) |
| AC-S18-03 | REQ-APP-007 | Opt-in automatic correction in EXP-S18: correct words changed per 100 correct words (every change logged and reversible) | ≤ 0.5 | requirement | REQ-APP-007 (DEC-056 (c)); SIM with the post-hoc W5 score: the automatic mode changed no correct word and fixed almost nothing (0.4 errors per 100 with the new-writer recogniser, 0 calibrated; docs/spelling_and_clarity.md T8) | the opt-in automatic mode (DEC-056) |
| AC-S18-04 | REQ-APP-005 | Logs of every EXP-S18 session and the app build (review and tests): the ink record is append-only and its hash chain verifies; every transcript change (accepted suggestion, automatic correction, edit) is logged and can be undone; no writing plan exists for text the participant did not accept (all) | all met | requirement | REQ-APP-005 (DEC-056 (a), (f)); ai3/tests/test_layers.py checks each rule on the specification (test) | DEC-056 (the three outputs) |
| AC-S18-05 | REQ-APP-008 | App logs of the EXP-S18 sessions: suggestions and completions offered only at natural pauses (none while a letter was being written), at most 3 at a time, each accepted with one action (tap, key or pen gesture) (all) | all met | requirement | REQ-APP-008 (DEC-056 (d), (e)); the prototype offers completions at pauses (28 of 28 smoke-test checks) | DEC-056 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-S18).
<!-- AC-TABLE:EXP-S18:END -->

---

## 23. Shifting the whole pen with people: EXP-W10, W12, W16 (study W; DEC-051…DEC-053)

Study W (`docs/whole_pen_shift.md`) found in simulation that shifting the whole pen did not beat the moving nose (DEC-051), and that the tremor estimate matters far more than added mechanics (DEC-052). Three questions need people: how large tremor at the ink is while writing (EXP-W10), whether people can hold and write with the collar (EXP-W12), and what "write only when in reach" costs them (EXP-W16). The bench and offline parts (EXP-W11, W13, W14, W15, W17) are in `bench_protocols.md` §50.
- **Convention.** Tremor at the ink is given zero-to-peak along the main axis, as DEC-054 (REQ-DATA-004).
- **DEC-053.** Any gated mode is reported with its coverage, missing strokes and completion time (REQ-WP-011), and any added device against the same pen with it locked (REQ-WP-001).
- **Safety.** EXP-W10 uses a passive pen (EXP-H01's). EXP-W12 uses the collar mock-up only after its bench checks (EXP-W11: current, stops and the unpowered latch). EXP-W16 uses the Rev J nose, so it runs only after EXP-N04, N05 and N08 on the exact build, and after EXP-J17 settles the nose's static load (DEC-046). Inclusion and exclusion as §3.2, including the rule on active implants.
- **Ethics.** EXP-W10's recordings are EXP-H01/R01's where the same people take part, under the same approval and the consents of §3.3; its added groups and tasks need an amendment.

### EXP-W10: How large is tremor at the ink while writing, and does anyone exceed the nose's reach?
- **Relation to EXP-H01 and R01 (§4, §21).** Not separate visits where they can be avoided. The ET and PD participants of EXP-H01/R01 are recorded with the same pen, digitiser and IMU. EXP-W10 adds a group with PD re-emergent tremor, the spirals, and writing with the hand resting and in free air, and brings each population to at least 20.
- **Design.** Writers with ET, with PD action tremor and with PD re-emergent tremor (≥ 20 each; a reviewed protocol and consent). They write the study's sentence and spirals on a digitising tablet with an ink pen and a 1 kHz IMU on the pen, with the hand resting and in free air.
- **Measurands.** Ink amplitude along the main axis (peak, 2.5–20 Hz; also in DEC-054's convention); frequency; axis; the share of time with a tremor line.
- **Predictions.** Recorded PD tip tremor while drawing spirals is mostly 0.1–0.3 mm; severe (the top 10 %) from 0.51 mm, typically 1.72 mm; the largest UCI test patient 7.1 mm (CALC on recorded data, study R). NewHandPD's pen accelerations show a tremor line in 4 of 26 patients while drawing, about 0.3–1.4 mm (study W). Study W's 5–10 mm classes are ASSUMPTION built on clinical scales (ET: 8–17 mm peak on a tablet at a rating of 2.5–3, LIT PDT-12). No open recording of ET at the pen tip exists.
- **Claim type.** None (measurement).
- **Decision.** Nobody beyond about ±6 mm: no whole-pen travel is needed, and DEC-051 stands. Writers beyond it: DEC-051 is revisited, with the collar (EXP-W11) or a larger stage. DEC-050 is revisited if many writers are beyond ±1.5 mm, B1's largest reach: the share beyond ±1.0 and ±1.5 mm is reported, and no line is set.

<!-- AC-TABLE:EXP-W10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W10-01 | — | Writers per population (ET, PD with action tremor, PD with re-emergent tremor; ≥ 20 each) whose tremor at the ink while writing exceeds the nose's reach: peak along the main axis (2.5-20 Hz; also in DEC-054's convention) above 6 mm | none | hypothesis | DEC-051's premise and revisit trigger (writers beyond the nose's reach, about ±6 mm; REQ-RVJ-N01 guarantees 6.0 mm); study R (CALC on recorded data): PD tip tremor while drawing spirals mostly 0.1-0.3 mm, severe from 0.51 mm (typically 1.72 mm), but the largest UCI test patient 7.1 mm -> at risk; study W's 5-10 mm classes are ASSUMPTION from clinical scales (ET FTM 2.5-3: 8-17 mm peak on a tablet, LIT PDT-12) | DEC-051 (revisit: whole-pen travel needed) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-W10).
<!-- AC-TABLE:EXP-W10:END -->

### EXP-W12: Can people hold and write with the collar?
- **Design.** Tremor-free adults first (n from a pilot, §11 rule). The collar mock-up of EXP-W11, with the collar locked and active (equal mass), in random order. Copying and free writing, 10 min each.
- **Measurands.** Comfort; the felt reaction (grip-force change, force-sensing pads on the collar); noise at 30 cm; where the web rests (video, contact sensing on the barrel); writing speed.
- **Predictions (SIM, CALC).** Grip-force change 0.03–0.38 N rms (SIM). Noise not estimated. The web rests on a saddle reaching z 97 mm, and the barrel clears the sleeve by 0.72–1.00 mm (CALC on the CAD). The latch that centres the unpowered inner pen is not designed.
- **Claim type.** Device burden.
- **Decision.** Accepted, with the web on the saddle: the collar may go to people with tremor if it ever passes REQ-WP-001 on the bench (EXP-W11). Not: redesign the saddle or the sleeve.

<!-- AC-TABLE:EXP-W12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W12-01 | REQ-WP-009 | Collar active against locked, tremor-free adults writing: grip-force change (force-sensing pads on the collar), sound level at 30 cm, and the latch centring the inner pen with the power off (all) | all met (≤ 0.5 N rms; ≤ 35 dBA; conforms) | requirement | REQ-WP-009 (DEC-051; the 35 dBA is an ASSUMPTION target); SIM grip-force change 0.03-0.38 N rms; noise not estimated; no latch designed (docs/whole_pen_shift.md open issue 6) | DEC-051; the collar with people with tremor |
| AC-W12-02 | REQ-WP-005 | Participants whose thumb-index web rests on the collar's saddle and never touches the swinging barrel while writing with the collar active (contact sensing on the barrel, video) | all participants | derived | REQ-WP-005 made measurable with people, so derived: with the web on the collar the ink moves 0.78-1.21 x the ideal lever, with the web on the barrel 0.58-1.23 x (CALC, docs/whole_pen_shift.md s3d) | DEC-051 (the saddle design) |
| AC-W12-03 | — | Participants who rate the collar pen acceptable for a writing session, collar active and locked (comfort and preference questionnaire) | ≥ 70 % | hypothesis | engineering judgement, as AC-G07-01 and AC-K03-04; no prediction | DEC-051 (the collar with people with tremor) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-W12).
<!-- AC-TABLE:EXP-W12:END -->

### EXP-W16: What does "write only when in reach" cost people?
- **Design.** People with tremor (n from a pilot, §11 rule) write with the Rev J pen, the gate on and off, in random order; copying. The gate lifts the ball while the estimated tremor exceeds the nose's reach minus a margin (0.3 mm), so ink is laid only where the nose can cancel.
- **Measurands.** Legibility (blinded literal transcription); coverage (the share of the intended ink laid); missing strokes (strokes less than half inked); completion time; preference.
- **Predictions (SIM at 8 mm; `docs/whole_pen_shift.md` §3f).** The gate lowered the tremor in the ink laid (ET: 2.9 against 3.2 mm), but laid 55 % of the intended ink against 80 % (ET) and 42 % against 76 % (PD). 20 and 27 of 42 strokes were less than half inked, against 1 and 0 with the nose alone. Re-tracing the lost ink would add 15–18 s to a 15.7 s sentence. No word more was read. At study R's real tremor sizes the gate would rarely act.
- **Claim type.** IA; device burden.
- **Decision.** Pass (AC-W16-02): the gate may be offered as an option, always reported with its coverage. Fail, as predicted: the gate stays off, and its cost is reported as REQ-WP-011 asks.

<!-- AC-TABLE:EXP-W16:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W16-01 | REQ-WP-011 | Every result of a gated or ink-only-when-correct mode (review): EXP-W16's gate; DEC-049's autowrite of accepted text (EXP-N08, N09, S19); the spelling cue's pen lift (EXP-S12, S18): coverage (share of the intended ink laid), missing strokes (strokes less than half inked) and completion time reported beside the error | conforms | requirement | REQ-WP-011 (DEC-053); study W's results cards carry coverage, and its stroke metrics come from the saved records (docs/whole_pen_shift.md s3f) | DEC-053; every claim for a gated mode |
| AC-W16-02 | — | Words read by blinded readers (literal transcription) with the gate on minus off, the same writers and texts (people with tremor, the Rev J pen), and coverage with the gate on against off (both) | both met (more words read; coverage no more than 5 points lower) | hypothesis | the 5 points of REQ-WP-001's coverage bound applied to a mode (engineering judgement); SIM at 8 mm: coverage 55 against 80 % (ET) and 42 against 76 % (PD), 20 and 27 of 42 strokes less than half inked, no word more read (docs/whole_pen_shift.md s3f) -> predicted to FAIL | the gate as an option (DEC-053) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-W16).
<!-- AC-TABLE:EXP-W16:END -->
