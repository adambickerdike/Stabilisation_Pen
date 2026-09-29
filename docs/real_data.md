# Real recorded data in the simulations (study R)

**Status: DRAFT while the headline simulation runs.** Every number is labelled. **DATA** = a recording re-analysed
here. **SIM** = an executed simulation (model HW1) with real recorded inputs. **CALC** = a calculation. **LIT** = the
literature, with its ledger id. **MFR** = a manufacturer statement. **ASSUMPTION** = a value chosen here. Nothing here
was measured on a person or on hardware.

## The answer in plain words

(to be completed when the headline run ends)

### The tremor library: how big real tremor is at the pen tip

The only open recordings of tremor **at the pen tip, in millimetres** are the UCI spirals: Parkinson's patients
drawing on a Wacom Cintiq 12WX. The pixel pitch is 0.204 mm (MFR, CON-84). Each recording's tremor is measured as a
spectral line above its fitted broadband background (Welch 4 s). Its size is the background-corrected peak of the
major axis, one value per patient (the median of their recordings with a line).

| Class | Peak at the tip (fitted on 24 tuning patients) | Representative (used in the headline) | The plan assumed |
|---|---|---|---|
| mild | 0.03-0.16 mm (below the median) | 0.10 mm | 0.3-1 mm |
| moderate | 0.16-0.51 mm (median to 90th percentile) | 0.24 mm | 2-4 mm |
| severe | above 0.51 mm (top 10 %; largest tuning patient 3.5 mm, largest test patient 7.1 mm) | 1.72 mm | 5-10 mm |

- **The check on held-out patients.** On the 25 test patients the shares are 60 / 24 / 16 % (expected 50 / 40 / 10;
  n = 25). CALC on DATA.
- **What is missing.** People whose tremor stops them drawing on a tablet are not in these data (Elble et al. 1996,
  PDT-82: very severe tremor could not be recorded when the pen left the tablet).
- **So the classes are a floor.** They describe the patients who could draw, not everyone with tremor.
- **How the sizes compare.** The data's severe class starts where the plan's mild class sat. Most PD tip tremor while
  drawing is 0.1-0.3 mm.

**Real tremor is about twice as irregular as the model used so far.** Medians over recordings with a line (CALC on
DATA):

| | Amplitude wander (envelope CV) | Frequency wander (SD) |
|---|---|---|
| PD tip (UCI) | 0.62 | 0.68 Hz |
| ET hand, arms out (Zenodo) | 0.64 | 0.60 Hz |
| PADS ET wrist, posture | 0.36 | 0.31 Hz |
| The model (TremorSpec) | 0.3 | 0.3 Hz |

**Frequencies.**
- PD tip line: median 6.3 Hz.
- ET posture: median 5.2 Hz.
- 2-D PD tip tremor: ellipticity median 0.46 (IQR 0.35-0.57); the model uses 0.4.
- ET recordings are one axis of hand acceleration. They are made 2-D by a documented construction (ASSUMPTION): a
  Hilbert-quadrature minor axis, with the ellipticity drawn from the PD IQR and the axis at 30 +- 15 degrees.

**The generator.** It holds 47 PD tip waveforms and 28 ET waveforms: 27 PD (17 patients) and 17 ET (13 patients) in
the test split. How a waveform is extracted and scaled:
- Extraction is zero-phase: the band f0 +- 2 Hz plus the band 2 f0 +- 2 Hz. It is an INPUT only and is never shown to
  a controller.
- Each waveform is scaled by its **power amplitude** (sqrt(2) x RMS of the major axis at f0 +- 2 Hz). This is the
  class convention, and equals the model's peak amplitude for a steady tremor.
- The real wander, intermittency and frequency are kept.

### The writing library: which real writing is clean enough to test trackers on

Trackers separate tremor from writing partly by frequency. So the writing input must not carry spurious movement in
the tremor band. Real writing on paper puts 1.3-1.7 % of its pen-down velocity energy at 8-12 Hz (LIT CON-25). Every
set below is measured with the one function the project uses (`sim2j.writers.kinematics`, read-only). CALC on DATA and
SIM.

| Writing | Speed (mm/s) | Median stroke (ms) | 50 / 90 % of velocity energy below (Hz) | Share at 8-12 Hz | Speed-curvature exponent |
|---|---|---|---|---|---|
| **UNIPEN hpb2 notes (ballpoint on paper; the HW1 input)** | 26.7 | 130 | 3.4 / 5.4 | 2.4 % | 0.70 |
| UCI Character Trajectories (one writer, composed) | 29.9 | 156 | 3.4 / 4.9 | 1.3 % | 0.76 |
| BRUSH (170 writers, stylus on screens) | 39.2 | 125 | 9.3 / 15.1 | **35.6 %** | 0.78 |
| Synthetic writers used so far (aiguide v1) | 18.3 | 151 | 4.9 / 11.2 | **17.3 %** | 1.00 |
| Synthetic writers refitted (sim2j v2, read-only) | 31.0 | 105 | 3.9 / 10.7 | **10.1 %** | 0.80 |
| Literature | 30.5 +- 7.9 (CON-20) | 90-150 (CON-24) | 3.1 / 4.9 (CON-25) | 1.3-1.7 % (CON-25) | 0.67 (CON-27) |

**BRUSH and the synthetic writers put far too much movement in the tremor band.**
- BRUSH is the only large open set with letter labels, but its 36 % at 8-12 Hz is a timing artefact.
- In a first HW1 run on BRUSH notes the trackers took it for tremor. They moved tremor-free ink by 100-450 um.
- That run was stopped and kept as a labelled diagnostic in `realdata/build/cache/hw1/brush_diagnostic/`.
- The synthetic writers carry 10-17 %: 6-13 times the real share.

**The selection rule (`kinematics.unipen_survey`).** The UNIPEN writing was chosen by a rule applied to all 26
category-8 recording setups, before any HW1 run on UNIPEN. A setup must pass every check:
- at most 2.5 % of the pen-down velocity energy at 8-12 Hz, and at most 3 % above 12 Hz;
- 15-60 mm/s;
- 100-250 samples/s and at least 15 points/mm;
- at least 10 writers;
- writing on paper.

Only **hpb2** passes: HP Labs Palo Alto, 1992, a Wacom 420-510C, an inking pen with a ballpoint refill on preprinted
paper forms, 100 samples/s, 0.05 mm. Two things about the rule:
- **The first survey sampled too little.** It took 12 lines per contributor, and all 12 fell in hpb2. It measured
  1.5 %. The full survey, with 60 random lines of lower-case words per setup, measures 2.4 %.
- **The same contributor's screen setup fails.** Its hpb3 setup (Wacom HD648A LCD screen, emulated ink) has 5.4 % at
  8-12 Hz and 14 % above 12 Hz on lower-case words.

The hpb2 notes:
- **Size.** 14 writers, one note of about 10 words per writer, in their recorded size. Letter height (the mean of
  'T', 'p' and 'a') is about 3-6 mm, median 4.4 mm (estimate from the line's ink, ASSUMPTION). That is close to
  healthy adults on paper (median 5.0 mm, LIT PDT-06). One test writer writes tall, narrow letters of about 15 mm.
- **Timing.** The recorded timing is kept. So are the recorded hover paths between strokes: 75-95 % of in-air moves,
  median 91 %. Only line changes and the few moves out of the tablet's range are added moves (ASSUMPTION). A note
  lasts 33-63 s (median 44 s).
- **Split.** 5 tuning and 9 test writers. Because every line text was written by 2-12 writers, the texts are split
  too (81 tuning, 133 test). No test note repeats a tuning text.

### The page sensor: from 3 um of white noise to a DeltaPen-class error

**What every earlier tracker result assumed.** The pen's page sensor read at 1 kHz, with 2 ms latency and 3 um of white
noise (fusion default, ASSUMPTION).

**What has been measured.** The one published pen-tip optical-flow pen, DeltaPen (OPT-01, OPT-02), was measured on a
Wacom surface, not paper. Its translation error per 10 ms window has a **median of 23.6 um and a mean of 68.3 um**.

**The model used here** (`realdata/sensors.py`; the review's R14 and response row 8):
- **Window error.** Each 10 ms window gets an error that grows with the window's movement (exponent 0.5, ASSUMPTION)
  with a log-normal spread. c = 20.5 um and sigma = 1.35 are fitted on the tuning notes so that the median and mean
  match OPT-02 (CALC). The error accumulates, as it does in a relative sensor.
- **Other errors.** Idle drift 43.75 um/s per axis (OPT-02). Scale error N(0, 3 %) (ASSUMPTION). 4.23 um counts
  (OPT-01).
- **Lost samples.** 0.05 % outliers (OPT-01). Dropouts at 0.2 per second, 20-150 ms each (ASSUMPTION).
- **Timing.** Latency 2 ms plus 0-1 ms jitter (ASSUMPTION). Acquisition and availability times are kept separately.

**Why it is pessimistic.** It gives all of DeltaPen's measured error to the sensor, although part belongs to the Wacom
reference.

**It reproduces the target.** On the simulated test runs the window error has a median of 25 um and a mean of 72-89 um,
against 23.6 and 68.3. The trackers are used as built (tuned for the ideal sensor). The ideal sensor stays as a labelled
bound (open circles and "ideal sensor" rows).

### Roles, splits and leakage

- **Split first.**
  - Subjects are split per source and group, stratified by a detection-free amplitude, before anything is fitted:
    UCI, Zenodo, PADS and NewHandPD. All of a person's recordings, tasks and sessions go to one split.
  - UNIPEN writers are split 5/9 by rank of a hash, and the line texts 81/133. UNIPEN files hold one session per
    writer.
- **Calibration** uses device documents or calibration data only:
  - the Cintiq pixel pitch (MFR);
  - UNIPEN resolutions from the headers;
  - the NewHandPD gravity fit, which is used only for its spectra, never as HW1 input.
- **Fitting** uses tuning data only:
  - the tremor-line thresholds (95th percentile of the tuning controls);
  - the severity classes (tuning PD patients);
  - the page-sensor model and the reader choice (tuning writers).
- **Validation.** The classes are checked on the test patients. Nothing is refitted.
- **Final test.** HW1 uses test writers, test texts and test patients only. Intervals are over writers, the
  participant level.
- **What cannot leak.** No model is trained on these data. The TCN is ai2's, trained on synthetic writers.
- **What differs by device and cannot be separated here.** Writing is from one digitiser (Wacom 420-510C), PD tremor
  from one tablet, and ET from one accelerometer set-up.
- **Time stamps.** The loaders' time is the acquisition time: UCI tablet time stamps, otherwise sample index / the
  documented rate. No dataset records availability times. The simulated sensors carry both.
- **No ground truth for spontaneous writing.** None exists for tremor-free writing by patients. Here the "intended"
  writing is by construction a healthy person's real note, and the tremor a patient's real recording, so the
  simulation knows the truth. Known shapes (the UCI spirals) give the tremor sizes. Nothing here claims to see a
  patient's hidden intent.
## The data behind the inputs

### Datasets and licences (opened 2026-09-29; raw files in `realdata/build/raw/`, git-ignored)

| Dataset | What it is | Licence | May go into `results/` | Used here for |
|---|---|---|---|---|
| **UNIPEN train_r01_v07**, setup **hpb2** (International Unipen Foundation 1999; Zenodo 10.5281/zenodo.1195803; HP Labs Palo Alto 1992) | 14 adults copying 2-3 word phrases onto paper forms with a **ballpoint refill** on a Wacom 420-510C; 100 points/s, 0.05 mm; hover points recorded | research use only (iUF notice in the data; the Zenodo page tags CC BY 4.0: the stricter terms are applied) | statistics only | **the writing of the headline comparison** (real words, real timing, real size on paper) |
| UNIPEN, the other 25 category-8 setups | text lines from many labs and devices | as above | statistics only | the kinematics survey that selected hpb2 |
| UCI Parkinson Disease Spiral Drawings (Isenkul et al. 2014; 10.24432/C5Q01S) | 62 PD + 15 controls drawing spirals on a Wacom Cintiq 12WX; X, Y, pressure, grip angle, time | CC BY 4.0 | short attributed excerpts, statistics | PD tremor at the pen tip in mm; the severity classes; the PD tremor waveforms |
| Zenodo ET accelerometry (Pardo-Valencia, Ammann, Foffani 2026; 10.5281/zenodo.19130599) | 29 ET patients, both hands, rest and arms out, one axis, 5 kHz | CC BY 4.0 | excerpts, statistics | ET tremor waveforms (shape, frequency, wander); amplitude set by the class |
| NewHandPD smart-pen signals (Pereira et al., SIBGRAPI 2016) | 31 PD + 35 healthy; BiSP pen: microphone, grip, refill force, 3-axis tilt/acceleration at the pen's rear; 1000 samples/s (file headers) | none stated (cite the paper) | statistics only | pen acceleration spectra; gravity calibration |
| PADS smartwatch (Varghese et al. 2024; 10.13026/m0w9-zx22) | 469 people (276 PD, 28 ET, 79 healthy); two watches, 100 Hz; rest, postural, kinetic tasks | CC BY-NC-SA 4.0 | statistics only | wrist tremor size; rest against action |
| UCI Character Trajectories (Williams 2008; 10.24432/C58G7V) | 2858 letters of one adult, 200 Hz | CC BY 4.0 | excerpts, statistics | the letters of the **committed** pictures |
| UJI Pen Characters v2 (Llorens et al., LREC 2008; 10.24432/C5FG8S) | 11,640 letters of 60 writers | CC BY 4.0 | excerpts, statistics | checked: no timing in the data, so not used |
| BRUSH (Kotani, Tellex, Tompkin, ECCV 2020) | 27,649 short sentences of 170 writers, stylus on screens, 10 ms points | non-commercial research use only | statistics only | **rejected as tracker input**: 36 % of its pen-down movement energy sits at 8-12 Hz (real writing on paper: 1.3-1.7 %, LIT CON-25), a timing artefact the trackers take for tremor |
| Wacom Cintiq 12WX manual (MFR) | pixel pitch 0.204 mm, 133 points/s, accuracy +-0.5 mm, pen 18 g | manufacturer document | numbers cited | the mm calibration of the UCI spirals |
| TrOCR handwritten, base and small (Li et al. 2021) | handwriting-reading transformers trained on IAM | base: MIT (model card); small: none stated; code MIT | not redistributed | the "words you can read" judge (base, chosen on tuning notes) |
| DeltaPen (Lüthi, Fender, Holz, UIST 2022; ledger OPT-01, OPT-02) | pen-tip optical flow, measured on a Wacom surface: 68.3 um mean and 23.6 um median error per 10 ms window | paper | numbers cited | the page-sensor error model |

**Not obtained.**
- IAM-OnDB: needs registration, which was not done (as instructed). It is the dataset to request for English sentences with timing.
- PaHaW: PD handwriting, licence agreement on request.
- DiaGraMo: CC BY 4.0, 276 Czech children (161 with dysgraphia), found late (1.36 GB). It is the natural source for the poor-handwriting and dyslexia work.
- OnHW (Fraunhofer IIS): the project page and README were opened. They state no licence, so permission is needed before use. OnHW-chars releases right-handed writers only. Its timestamp is when the connected tablet processed the data, not when the sample was taken. It is a recognition benchmark for study S, with no tremor or page trajectory.
- ET at the pen tip: no open recording exists in what was searched. Elble et al. 1996 (PDT-82) measured it on a tablet but did not release the data.
## How other studies use the library

```python
from realdata import library as RL

RL.classes()                                   # severity classes (mm at the pen tip, peak), fitted on tuning subjects
tr = RL.tremor("severe", seed=3, kind="PD", split="test", duration=20.0)       # real PD tip tremor, severe class
tr = RL.tremor("moderate", seed=3, kind="ET", split="tuning", t=my_t)          # real ET waveform on your time grid
tr = RL.tremor("moderate", seed=3, kind="PD", amp_mm=1.0)                       # a fixed size instead of a draw
syn = RL.synthetic_like(tr)                    # the old model (TremorSpec) at the same frequency and size
wr = RL.writing("test", seed=3)                # a real note: UNIPEN hpb2, ballpoint on paper, about 10 words
wr = RL.writing("test", seed=0, source="chartraj")          # the CC BY writer's letters composed into a sentence
scn = RL.hw1_scenario(wr, tr)                  # handwriting.plant.Scenario (model HW1)
s2 = RL.sim2_scenario(wr, tr)                  # sim.pensim Scenario for sim2's H1 hand (pref, vref, fpush, lift)
RL.RealWriter("unipen/0").write(seed=0)        # writer-interface parity with aiguide/sim2j

from realdata import sensors as RS, hw1 as H
st2 = RS.degrade_page(streams, H.page_model(), seed=1)   # DeltaPen-class page sensor on any fusion Streams
from realdata import ocr as OC
OC.reader_choice(); OC.words_read(result, wr)  # literal words read by the AI reader (TrOCR base)
```

- `tr.d` is an (n, 2) array in metres on the page (x along the line, y up). `tr.meta` records the recording, its
  frequency, the class, the amplitude convention (peak = sqrt(2) x RMS of the major axis at f0 +- 2 Hz) and the
  construction used.
- `wr` is an `aiguide.writer.Written` (`text`, `intended` = `stabpen.signals.Intended`, `letters`, `dt`) with
  `wr.real` holding the source, writer, lines, line time spans, recordings, device, pen, surface, split and licence.
  UNIPEN strokes carry their recorded hover paths between strokes. Line changes are added moves (ASSUMPTION).
  UNIPEN has no letter labels, so each stroke is one pseudo-letter.
- Choose `split="tuning"` while designing and `split="test"` only for final numbers. Subjects, writers and (for
  UNIPEN) line texts are split before any evaluation.
- Everything that uses the future of a recording (the zero-phase tremor extraction) is an INPUT only. Trackers must
  see only the simulated sensor streams.
## Proposed requirements (for the lead to merge into `docs/requirements.csv`)

| id | Requirement | Rationale | Verification |
|---|---|---|---|
| REQ-DATA-002 | Every tracker or pen claim about writing is also evaluated on **real recorded writing and real recorded tremor** (this library or better), on test writers and test subjects only, and reported next to the synthetic result | The synthetic writers and tremor model differ from real ones in ways that change the results (bridge, this doc) | results card with both input sets |
| REQ-DATA-003 | False correction ("clean writing changed") is measured on **real tremor-free writing recorded on paper with a clean digitiser**, i.e. <= 2.5 % of its pen-down velocity energy at 8-12 Hz | BRUSH's timing artefact made the trackers move clean ink by 100-450 um | kinematics check (realdata.kinematics) before use |
| REQ-DATA-004 | Claims name the **tremor class in mm at the tip** (peak = sqrt(2) x RMS of the major axis in f0 +- 2 Hz) and the population, never "tremor" alone | The data's severe class starts at about 0.5 mm, far below the plan's assumed 5-10 mm | review of every claim |
| REQ-DATA-005 | Inputs built with non-causal (zero-phase) filters are **never** given to a controller or estimator | The tremor extraction uses the future of the recording | code review; library docstrings |
| REQ-DATA-006 | Datasets are used and redistributed only within their licences; results hold statistics only for research-only and non-commercial sources | UNIPEN, BRUSH, PADS, NewHandPD terms | sources.py registry test |
| REQ-DATA-007 | Every simulation that reports tracker performance also reports it with a **measured-error page-sensor model** (for now the DeltaPen-class model); the ideal sensor only as a labelled bound | Review 2026-09-29 R14; this study's sensor results | results card has both columns |
| REQ-DATA-008 | Words-you-can-read results use a **literal** reader (no lexicon, no spelling correction, greedy decoding) and report the clean-ink ceiling of the same notes and a 95 % interval over writers | Review s13 | results card |
| REQ-DATA-009 | EXP-H01 recordings: ink on paper over a digitiser (>= 200 points/s, <= 0.05 mm, hover tracked), the pen's IMU with **acquisition and availability time stamps**, handedness, grip, posture, medication state, device configuration; participant- and session-level splits | Review s11; this study's gaps | protocol review |

## Proposed experiments

EXP-R01 is also used in `docs/revH_concept.md` (line 193, "bench active nose", proposed). The lead should rename one
of the two. The ids below follow the round-4 plan.

| id | Question | Method | Decides |
|---|---|---|---|
| EXP-R01 | What do ET and PD patients' **own** writing and tremor look like at the pen tip, with ink? | Sentences on ruled paper over a digitiser (>= 200 points/s, hover), plus the instrumented pen's IMU; ET, PD, age-matched controls; two sessions; REQ-DATA-009 (the recording part of EXP-H01) | Replaces the healthy writers + patient tremor composition; class sizes in writing, not spirals |
| EXP-R02 | Do the trackers leave real clean writing alone and remove real tremor? | Offline replay of EXP-R01/EXP-H01 recordings through the Rev H, Rev J gated and TCN estimators with measured sensor streams | Tracker choice (with EXP-L01) |
| EXP-R03 | Does the AI reader's "words you can read" match people? | Blinded human panel transcribes the rendered ink of this study's test cases (and EXP-R01 ink); literal scoring; compare with TrOCR | Whether words-read numbers can stand for people |
| EXP-R04 | Poor handwriting and dyslexia inputs | DiaGraMo (CC BY 4.0, 276 children, 161 with dysgraphia) through this library's loaders | Study S and the practice functions |
| EXP-R05 | Does a learned tracker trained on real inputs keep clean writing still? | Retrain the TCN on real writing (UNIPEN hpb2 tuning + EXP-R01 training participants) with real tremor; test writer-disjoint | REQ-ML-001 on real data |
| EXP-R06 | Get the missing data sets | Request IAM-OnDB (registration), PaHaW (licence), OnHW (licence) | Larger real-writing test sets |
| EXP-R07 | Is DeltaPen's window error the sensor's or the reference's? | Pen-tip flow sensor and a motion-capture or stage reference on paper; 10 ms window error, latency, dropouts (with EXP-S01) | Replaces the pessimistic page model |
