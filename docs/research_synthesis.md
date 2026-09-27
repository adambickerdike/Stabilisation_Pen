# Research synthesis (initial, 27 Sep 2026)

**Source ledger:** [`docs/evidence.csv`](evidence.csv). It has 246 rows from eight streams: ACT, CON, PDT, HAP, AMF, OPT, EML, PAT. Access levels: 190 full text, 34 abstract only, 22 secondary accounts. Every row carries its evidence class, locator, limitations and a separate transferability rating. Search logs, with exact queries and dates, are in [`docs/research/notes/`](research/notes/).

**Verification.** Two decision-driving numbers were re-verified by me against their primary sources:

- **PDT-12:** ET spiral tremor amplitude.
- **ACT-01:** Micron delay, bandwidth and attenuation.

The shared web-search quota ran out during the streams. Later retrieval used publisher, DOI and scholarly-API access; each stream logs what it could not reach.

**Evidence labels used below:** *[human]* physical human study · *[bench]* physical bench experiment · *[sim]* numerical simulation · *[mfr]* manufacturer statement · *[patent]* · *[ours-calc]* our calculation · *[ours-sim]* our simulation.

---

## 1. Active handheld instruments (ACT)

- **Micron microsurgery tool:**
  - 2 ms pure delay; 84–123 Hz closed-loop bandwidth; ±400 µm travel; ≥15 dB hand-motion attenuation in free space *[bench, ACT-01, lead-verified]*.
  - In users, error fell only 32–52 %, and handle motion rose *[human, ACT-02]*.
  - The 6-DOF version holds 6–17 µm RMS error up to 0.25 N side load and degrades at 0.30 N *[bench, ACT-03]*. That is the bottom of our load range.
- **Liftware stabilising spoon:** 71–76 % ET tremor reduction, measured in free space and in a company-run study *[human, ACT-16]*. Severe tremor fell outside its range, and a passive deep-bowl spoon scored comparably *[human, ACT-19]*.
- **Pens:**
  - No published active pen moves its nib under paper contact in human use.
  - The only physical rig is a single-axis voice-coil test cutting an 8.7 Hz peak by 57 % *[bench, ACT-21]*.
  - The 2025 *Scientific Reports* "smart pen" does not move the nib and had no human participants *[bench/sim, ACT-22]*.
- **What transfers:** delay-limited cancellation physics; Kalman and oscillator estimators; feedforward.
- **What does not transfer:** loads (mN vs our 0.3–2 N); external optical tracking at 2 kHz; slow-voluntary-motion filters (1.5 Hz), which would erase handwriting.
- **Must measure:** loaded nib dynamics under stick-slip (EXP-B01, B05, B09).

## 2. Pen–paper contact and writing kinematics (CON)

- **Normal and axial force:**
  - Axial writing force: 1.0 N mean for healthy adults; writer means range 0.56–2.08 N; within-word SD 0.18 N *[human, CON-01]*.
  - Normal force ≈ 0.8 × axial.
  - Heavy writers reach about 4 N (derived high case).
- **Altitude:** about 50° on paper (n = 4) and 62 ± 7.5° on tablets; altitude varies only ±2.5° while writing *[human, CON-02, CON-12]*.
- **Ballpoint drag μ:** 0.09–0.17 depending on ink at 90° *[bench, CON-13]*; 0.10–0.40 rising with load and paper sinking *[patent, CON-14]*; roughly ±25 % ripple along a stroke *[patent, CON-15]*.
- **Speed and spectrum:**
  - Phrase writing runs at 30 ± 8 mm/s *[human, CON-20]*.
  - About 17 % of intended-velocity energy lies in 4–7 Hz and about 1.5 % in 8–12 Hz (one-writer re-analysis, derived: CON-25; CON-24).
- **Our addition *[ours-calc, COR-01]*:** the stage must react N·cos θ plus friction, a transverse load of 0.25–0.9 N per newton of normal force.
- **Gaps (must measure, EXP-B01):**
  - reciprocating friction at 3–15 Hz, breakaway and stick-slip;
  - push/pull asymmetry;
  - minimum force for continuous ink;
  - paper indentation vs load;
  - refill mass.

## 3. Actuators, flexures, cells (AMF)

- **Commercial voice-coil motor constants *[mfr, ours-calc]*:**

  | Motor | Size | K_m (N/√W) |
  |---|---|---|
  | Moticont 9.5 mm | 9.5 mm | 0.21 |
  | Moticont 12.7 mm | 12.7 mm | 0.50–0.83 |
  | Akribis AVM12 | 12.7 mm | 0.54 (25.6 K/W published) |

  AMF-01 to AMF-04. None of these fits transversely in a 14–16 mm pen.
- **Piezo:**
  - Benders can reach only about ±77 µm against 1.6 N even with an ideal lever *[ours-calc from AMF-11]*.
  - Amplified piezo stacks (APA50XS) give 66 µm with 16 N blocked force but need 150 V and a ~17:1 amplifier *[mfr, AMF-14]*.
  - The SQUIGGLE motor holds at 0 mW but reaches only 0.3 N stall (1.8 mm model) *[mfr, AMF-15]*.
- **Flexure material:** C17200 TH04, E = 131 GPa, about 310 MPa fatigue at 10⁸ cycles *[mfr, AMF-18/19]*. Allowables: 150 MPa alternating, 310 MPa peak.
- **Cells:** 10440 Li-ion is limited to 1C (0.32 A) *[mfr, AMF-31]*. Narrow high-rate LiPo pouches (20–30C) fit a 13 mm bore; their rating is a web claim *[mfr, AMF-33]*.
- **Touch temperature:** 43 °C continuously held (ECMA-287; IEC 60601-1 Table 24), with a 41 °C design target *[standard, AMF-34/35]*.
- **Drivers and current sense:** DRV8212 has no current sense. INA240/INA241A are PWM-rejecting inline sensors; INA181 is not one *[mfr, AMF-36..40]*.

## 4. Handwriting impairment in PD and ET, and interventions (PDT)

- **ET spiral tremor:**
  - Geometric mean 0.20 cm peak-to-peak, n = 18, drug-free *[human, PDT-12, lead-verified]*.
  - Log-normal fit (derived): about 32 % of patients ≤ 1 mm p-p, which ±0.5 mm could fully cancel, and about 50 % ≤ 2 mm.
  - Writing tremor correlates weakly with limb tremor *[human, PDT-13]*.
- **PD:**
  - Micrographia prevalence is 50–63 % depending on measure *[human, PDT-01]*.
  - Tremor while writing is uncommon: 3 of 10 OFF-medication patients showed 4.4–8 Hz tremor while writing *[human, PDT-10]*.
  - No mm-level tremor-at-nib data exist.
- **Interventions:**
  - Intensive amplitude training (RCT, n = 38): 7–17 % larger writing, retained and transferred, but less fluent *[human, PDT-16/17]*.
  - Guide lines 1.0 cm apart help; 0.6 cm apart shrink writing *[human, PDT-18/20]*.
  - A weighted pen increased stroke variability *[human, PDT-21]*.
- **Implication:** active nib correction addresses a subset of action tremor. PD micrographia belongs to the cueing and practice modes. Claims must be kept separate by user group (REQ-USR-001/002).

## 5. Guidance, shared control, motor learning, hand impedance (HAP)

- **Learning:**
  - Error-minimising channel guidance gave the worst unassisted retention and transfer (n = 9 per group) *[human, HAP-09]*.
  - Guidance improves fluency but not shape *[human, HAP-10]*.
  - The benefit depends on skill *[human, HAP-08]*.
  - Confident-but-wrong assistance is the worst case *[human, HAP-23]*.
- **Position-correcting tools:** these set range to about 2× user error (Rivers 2012) *[human, HAP-18]*. Unguided novice shape error is 3.8–5.1 mm (Langerak) *[human, HAP-16]*. So ±0.5 mm can polish strokes but not form a novice's letters.
- **Hand impedance (stylus grip) *[human, HAP-26]*:**
  - grip stiffness k1 = 380–770 N/m; grip damping b1 = 0.8–1.8 N·s/m;
  - hand mass M = 0.2 kg; arm stiffness k2 = 79–272 N/m; arm damping b2 = 4.6–18 N·s/m.
  - Pen-hold vibrotactile threshold: 26 µm at 10 Hz *[human, HAP-27]*.
  - These values are adopted in the simulator (config v0.3).

## 6. Local sensing and capture (OPT)

- **DeltaPen** (two lensless PixArt P3040 sensors, 1 kHz) *[bench, OPT-01/02]*:
  - translation error 68 µm mean / 24 µm median per 10 ms window;
  - evaluated on a Wacom surface, not paper;
  - no latency figure; 10 × 12 mm tip board.
- **Sensor parts:** the P3040 datasheet is under NDA; mouse sensors need 2.4 ± 0.2 mm working distance *[mfr, OPT-04..06]*.
- **Capture systems:** Anoto 75 fps and Ncode 120 fps both carry licensing costs. Nuwa's ordinary-paper claim is unverified and its commercial status conflicts *[mfr, OPT-07..13]*.
- **IMU-only recognition:** 17–35 % character error rate; absolute position is unobservable *[bench, OPT-15..19]*.
- **Implication:** local optical sensing next to a moving nib is a custom-optics problem (EXP-S01). Ordinary-paper page capture is a research risk; coded paper is used for research builds.

## 7. Causal prediction (ACT, EML, ours)

- **Published estimators:**
  - WFLC removed 66.9 % of 6–16 Hz power on a bench *[bench, ACT-08]*.
  - In real time, BMFLC reached 64 % against WFLC's 43 % *[bench, ACT-10, abstract]*.
  - A 1D-CNN predicting 50 ms ahead reached 93.8 % against WFLC's 68.8 %, assuming voluntary motion below 2 Hz *[bench, ACT-14]*.
- **None of these was tested on handwriting, where voluntary motion reaches 5–10 Hz.**
- **Our simulation *[ours-sim, COR-11]*:** conventional estimators help only above about 9 Hz (v0.4.2 grid). The frequency gate is meant to prevent harm below that. But the tracker that drives it also opens it on 15 % of tremor-free handwriting and on 52 % of the feature course, and the tuned selection flips between an inert and an active set with small plant changes. The mechanical bound is 0.22–0.32 (`docs/sim_report.md` §3.2).

## 8. Edge ML deployment (EML)

- **nRF5340:** M33 at 128 MHz with FPU and DSP; 512 kB RAM; one multiplexed 12-bit ADC; 16 MHz PWM clock *[mfr, EML-01..06]*.
- **Inference efficiency:** MLPerf Tiny on M33 runs at about 0.5 MAC/cycle; a dilated TCN on M4 at 0.15 MAC/cycle *[bench, EML-20..24]*.
- **Toolchain:**
  - TFLM (LiteRT Micro) with CMSIS-NN v8.0.0: int8 per-channel; dilated convolutions run on the generic kernel.
  - ST Edge AI does not support dilation ≠ 1.
  - microTVM has been removed *[doc, EML-11..29]*.
- **Budget:** ≤ 35k MAC per 4 ms step, streaming.

## 9. Recognition, datasets, grounded AI (OPT)

- **ML Kit Digital Ink:** free, on-device, 300+ languages, no published accuracy *[doc, OPT-20]*.
- **MyScript:** needs a commercial agreement *[doc, OPT-21/22]*.
- **Datasets:** IAM-OnDB, DeepWriting, MathWriting and BRUSH are non-commercial or unverified *[doc, OPT-28..31]*.
- **Research accuracy:** character error 2.5–4 % on IAM-OnDB *[bench, OPT-25]*.
- **Evaluation of grounded summaries:** AIS-style human attribution plus span citation recall/precision, and faithfulness plotted against recognition error *[doc, OPT-32..35]*.

## 10. Prior art (PAT, not legal advice)

- **US12026327B2:** claim 1 requires XP, YP and ZP nib actuation, plus an IMU and predefined-character scribing.
- **EP4250070A1:** shown as withdrawn.
- **CN121979402A:** exists and is pending. It claims translation-only X-Y refill drive, eccentric-mass counter-moments and guided strokes.
- **Needing review:** Verily active-pen and arm patents.
- **Not found in claims:** predictive cancellation, confidence-based authority, a pivoting refill (PAT-01..25).

---

## Unresolved disagreements and gaps (ordered by decision impact)

1. **Tremor amplitude at the nib during real writing (mm per axis),** by group (ET, PD subtype, older adults). It sets the addressable population and the stage travel. No study provides it; tablets have ±0.25 mm accuracy.
2. **Intended-motion spectrum of fast cursive and of impaired writers.** The 17 % in 4–7 Hz comes from a single writer. It decides where estimation can work.
3. **Friction dynamics at small reciprocating amplitude** (3–15 Hz, stick-slip, breakaway), and whether ink quality tolerates pressure modulation of about 0.1 N.
4. **Hand normal compliance and γ** with the hand resting on paper (HAP-26 was in-plane with the arm unsupported).
5. **Optical local sensing on paper** at 35–75°: latency, noise and dropout.
6. **Whether any learned model beats the frequency-gated Kalman estimator** on causal pen data at equal distortion.
7. **Whether a nose skid (configuration D) is acceptable** for writing feel and smear.

Evidence conflicts noted:

- Friction for special-oil ink disagrees between two figures of CON-13.
- Nuwa shipping status is contradictory.
- Liftware effect sizes come from a manufacturer-run study; a passive spoon comparator performed similarly.
