# Bench protocols

**Status: PROPOSED PROCEDURES. No experiment in this file has been executed.** On 2026-09-27 the repository holds no bench measurement of any pen, rig, actuator, refill or person. Every number below is one of three things:

- a **prediction** from calculation or simulation, cited with its file and parameter version;
- a **literature value**, cited with its evidence id from `docs/evidence.csv`;
- an **acceptance criterion or hypothesis** with an id `AC-…` from [`acceptance_criteria.csv`](acceptance_criteria.csv), which states the source of the number.

Executed results will exist only as records under [`records/`](records/README.md). None exist yet.

Human-participant studies (EXP-H01…H06) are specified in [`human_study_plan.md`](human_study_plan.md). EXP-B06 involves participants, so it is covered by the same ethics approval, but its bench procedure is written here. Stage gates and the order of experiments are in [`prototype_stages.md`](prototype_stages.md).

Contents:

- §0 Conventions shared by every protocol
- §1 Experiment index
- §2–§24 Protocols: B01–B10, S01–S02, F01–F02, M02–M03, P01–P02, E01–E02, C01–C02, A01
- §25 Pointers to the human-participant protocols

---

## 0. Conventions shared by every protocol

### 0.1 Status words

| Word | Meaning |
|---|---|
| proposed procedure | Text in this file. |
| prediction | A number from `results/` (calculation or simulation), quoted with `parameters_version`. |
| executed result | A measurement stored under `validation/records/` with its metadata. None exists yet. |
| verdict | pass / fail / inconclusive for one `AC-…` id, stated with its expanded uncertainty and the decision rule used (§0.5). |

### 0.2 Pre-registration

Before any data are taken for an experiment:

1. **Freeze** the protocol text (git commit), the `AC-…` rows it uses, the analysis script (git commit) and the prediction file.
2. **Regenerate predictions with as-built parameters.** The simulator is re-run with the parameters identified on the hardware under test (for example `m_eq`, `k_tip` and `K_f` from EXP-B03/B05; `μ(N)` from EXP-B01; hand-simulant values from EXP-B06). The prediction file carries the `stabpen.provenance` metadata (`parameters_version`, SHA-256 prefix, git revision).
   - Result files in the repository currently carry mixed parameter versions: `results/em/*` 0.2.0; `results/mechanics/*`, `results/cad/*` and most of `results/ml/*` 0.4.1; `results/sim/*`, `results/trade/config_trade.json`, `results/thermal/thermal.json` and `results/electronics/drive_sense.json` 0.4.4. The 0.4.2–0.4.4 changes (pivot stiffness, thermal path, electronics power, where the magnet tempco is applied) are not inputs of the mechanics and CAD results. The numbers quoted in this file are therefore indicative; the frozen prediction file, not this text, is the comparison reference.
3. **Deviations** are logged in the record with their reason. The frozen analysis is always reported. Analyses added later are labelled exploratory.

### 0.3 Frames, units and signs

As `docs/icd.md` §1: altitude θ, azimuth φ, roll ρ; tip-equivalent stage displacement q = (q1, q2); axial slide s; normal force N; stroke direction β relative to h (`docs/physics.md` P-5). SI units; logged values use the ICD scalings.

### 0.4 Data, time base and synchronisation

- **Pen data.** ICD §4 binary logs (36-byte header, CRC-checked records). All bench work streams research frames (type 0x01, 2 kHz, USB) plus event records (0x03). Readers: `app/penapp/logfmt.py`.
- **External instruments.** HDF5 (preferred) or CSV with a JSON sidecar, one file per run, units in the dataset names. Vendor-native raw files are kept alongside (`records/README.md`).
- **Common time base.** The rig DAQ generates a sync line: a TTL pulse every second whose width encodes an 8-bit counter. The DAQ records it, and the pen records each edge on a GPIO. ICD v1.0 has no event code for this, so edges are logged as annotation records (0x05) with the text `SYNC <n>` until the ICD adds a code (proposed change, listed in `README.md`).
- **Alignment accuracy required: ≤ 50 µs.** Basis: engineering judgement, 1 % of the 5 ms effective-delay budget (REQ-CTRL-003). It is checked at the start of every session by one step injected into both systems.

### 0.5 Metrology and decision rules

- Every instrument carries a valid calibration traceable to national standards. Certificate ids and due dates go into the record.
- Uncertainty follows JCGM 100 (GUM). Budgets are stated per record; expanded uncertainty U at k = 2.
- **Decision rule** (JCGM 106, ILAC-G8):
  - *Simple acceptance* when the test uncertainty ratio TUR = (tolerance half-width, or distance of the limit from the expected value) / U is at least 4.
  - Otherwise *guarded acceptance*: pass only if the measured value ± U lies entirely inside the limit.
  - Safety-related criteria (REQ-SAF-\*, REQ-THM-\*, EXP-F01, EXP-P02) always use guarded acceptance.
- **Check standards.** Each session starts with a check standard (dead weight, gauge block, reference coil, reference line target). Its reading is logged. The session is void if the check falls outside its control limits (3σ from the qualification data).

### 0.6 Randomisation and blinding

- Run order is randomised within blocks, with the seed logged, so that drift (temperature, ink consumption, paper batch, operator fatigue) is not confounded with a condition.
- **Ink images are analysed blind.** Files are renamed with random codes before analysis; the analyst and the automatic pipeline never see condition labels. The key is merged only after the metrics are frozen.

### 0.7 Sample-size conventions

- **Continuous outcomes.** Choose n from the precision needed: n ≥ (t₀.₉₇₅,ₙ₋₁ · s / E)², where s comes from a pilot or qualification data and E is the half-width that keeps TUR ≥ 4 against the acceptance band. Default: at least 3 repeats per cell and at least 10 in primary cells.
- **Pass/fail reliability** (zero-failure success run): n = ln(1 − C) / ln(R).
  - R = 0.90, C = 0.95 → n = 29.
  - R = 0.95, C = 0.95 → n = 59.
  - 0 failures in 100 trials demonstrates R ≥ 0.970 at C = 0.95; 0 in 200 demonstrates R ≥ 0.985.
- **Model agreement.** Confidence intervals by bootstrap over repeats, or over writers for recorded data.

### 0.8 Common metric definitions

These are the bench equivalents of `docs/physics.md` §8 and `sim/pensim/evaluate.py`, so that bench and simulation numbers are directly comparable.

| Id | Metric | Definition |
|---|---|---|
| M-e | time-aligned ink error | e(t) = p_nib(t) − p_ref(t), 2-D in the page frame. p_nib is the nib ball centre from independent metrology (rig encoders + housing sensors + nib-relative sensor), in contact. p_ref is the same quantity for the reference run. |
| M-mask | evaluation mask | Samples where both runs are in contact, t > 0.5 s after run start, excluding ±30 ms around every contact transition (as `evaluate._mask`). |
| M-rms | RMS error | √(mean \|e\|²) over the mask. |
| M-band / M-low | band-limited error | e filtered by a 4th-order Butterworth, zero-phase (offline only): 3–15 Hz band-pass (M-band) and < 2.5 Hz low-pass (M-low), then RMS over the mask. |
| M-ratio | residual ratio | M-rms(mode) / M-rms(NEUTRAL), same path and same disturbance realisation. Band ratio uses M-band. |
| M-dist | distortion (false correction in ink) | RMS of p_nib(mode) − p_nib(NEUTRAL) on the same path **without** disturbance. |
| M-dev | device distortion | RMS of p_nib(NEUTRAL) − p_nib(RIGID) without disturbance, mean offset removed (`bench.device_distortion`). |
| M-path | path distance (ink only) | RMS over in-contact ink centreline points of the distance to the nearest point of the intended path (as `sim/guided_eval.py`). Computed from scanned ink (§0.9 R3). This is what a reader sees, and it is the primary metric for guided mode. |
| M-feat | feature error | Max and RMS of \|e\| (or of the path distance) inside each feature window of the feature course (`stabpen/signals.py::feature_course`): corner_edge, dot, hatch (4 Hz), fast_stroke (≈190 mm/s peak), circle, spiral. |
| M-Nmod | normal-force modulation | RMS of the 3–15 Hz band-passed normal force measured under the paper, over the mask. |
| M-Pcu | copper loss | Mean of Σ iₖ²·R(Tₖ) over the run, with i from the calibrated shunt and R(T) from coil resistance thermometry. |
| M-delay | equivalent delay | τ_eq(f) = −∠H(f) / (2πf), where H is the transfer function from housing disturbance to nib correction with the sign of the correction removed. Reported over 3–12 Hz. |

### 0.9 Shared rigs and minimum instrument classes

| Rig | Used by | Key instruments and required accuracy |
|---|---|---|
| **R1 tribometer** | B01, B02, B08 | Pen holder on a goniometer (θ 35–80°, ≤ 0.1° resolution, verified under load with an inclinometer). Normal load by dead weight on a counterbalanced air-bearing or crossed-roller vertical slide, or a force-controlled voice-coil axis (0.05–4 N, modulation to 20 Hz). **6-axis F/T sensor, ATI Nano17 class**: ≥ ±10 N in-plane, ≥ ±15 N normal, resolution ≤ 5 mN, in-situ dead-weight calibration error ≤ 2 % of reading at 0.2–4 N, mounted resonance ≥ 500 Hz. Paper platen on an **XY linear-motor stage**: encoders ≤ 0.1 µm, 0.01–200 mm/s, velocity ripple ≤ 1 %. A flexure or voice-coil **reciprocation stage** (±0.5 mm, 1–20 Hz, capacitive or encoder feedback ≤ 0.1 µm). **Laser triangulation sensor** for indentation (≤ 0.1 µm resolution, ±1 µm linearity over 1 mm). 24-bit simultaneous-sampling DAQ ≥ 5 kS/s per channel. Environment 23 ± 2 °C, 50 ± 10 % RH (ISO 12757-1 test atmosphere, CON-21). |
| **R2 cancellation rig** | B05 (in contact), B09, E02, F01 (in contact), S02, P01 | Linear-motor XYZ "robot" carrying the hand-simulant base along intended paths (≤ ±5 µm path error at ≤ 200 mm/s). A **2-axis voice-coil disturbance stage** between robot and simulant (±1 mm, 1–30 Hz, ≥ 10 N, sensor ≤ 0.1 µm). **Hand simulant**: two-stage mass–spring–damper per page axis with interchangeable springs and eddy-current dampers covering HAP-26 ranges (k1 230–1040 N/m, b1 0.3–4.6 N·s/m, M 0.05–0.57 kg, k2 63–533 N/m, b2 3.7–27.6 N·s/m). A normal-direction spring K_n (200–3000 N/m) with a preload screw sets N; the simulant FRF must be within ±10 % of target (qualification). **Paper platen on a 3-axis force plate** (Kistler 9119/9256 or ATI Mini40 class; ≤ 5 mN resolution, ≥ 1 kHz resonance with platen). **Housing metrology**: three laser triangulation sensors on the robot carriage viewing the barrel (≥ 10 kHz, ≤ 0.5 µm resolution, ±2 µm linearity over ±2 mm). **Nib-relative metrology**: a laser Doppler vibrometer or triangulation sensor on the carrier or refill, independent of the pen's Hall sensor. |
| **R3 ink metrology** | B01, B08, B09, E02, F01, S02, H03, H05 | **Flatbed scanner at 4800 dpi nominal** (5.3 µm/pixel), 16-bit lossless TIFF, fixed exposure. Optical resolution verified on a USAF-1951 target: ≥ 40 lp/mm resolved (group 5, element 3). Geometric distortion mapped with a **certified chrome-on-glass grid** (pitch uncertainty ≤ 1 µm). Alternative: motorised microscope stitching at ≤ 2 µm/pixel. **Required: ink-centreline position uncertainty ≤ 5 µm (k = 2) within a 25 mm field and ≤ 20 µm across a page** after distortion correction (engineering judgement: TUR ≥ 4 against 20 µm-class differences). Paper carries pre-printed fiducials; a blank scan is taken before writing. Centreline extraction: background subtraction, Otsu threshold, sub-pixel ridge fit across the line every 20 µm. Versioned code, results frozen before unblinding. |
| **R4 actuator coupon fixture** | B03, B07 | 2-axis micrometre positioning stage for the coil paddle (≤ 1 µm resolution, ±1.6 mm at the actuator). 6-axis F/T sensor as R1. Precision bipolar current source (±1 A, ≤ 0.1 % accuracy) or the Rev A drive with a 0.1 %-class shunt read by a 6½-digit DMM. **LCR meter**, 4-terminal, 20 Hz–100 kHz, basic accuracy ≤ 0.1 %. 4-wire micro-ohmmeter at 20.0 ± 0.5 °C. Fine type-T thermocouples (0.08 mm, ±0.5 °C after dry-block calibration). **Thermal camera** ≥ 320 × 240, NETD ≤ 50 mK, emissivity set on black tape (ε = 0.95). Climate chamber ±0.5 °C. Small electrodynamic shaker for back-EMF tests. |
| **R5 calibration stage** | B04, B10, S01 | Crossed-roller or air-bearing XY(Z) stage, bidirectional repeatability ≤ 1 µm, accuracy ≤ ±2 µm over 10 mm (laser-interferometer verified). Piezo nanopositioner for steps (rise ≤ 0.2 ms, capacitive sensor ≤ 10 nm). Goniometer and rotary stages for θ and ρ. **Independent tip metrology**: two orthogonal laser triangulation or confocal chromatic sensors on a reference sphere at the tip, or an optical CMM with a telecentric lens (≤ 1 µm/pixel with sub-pixel edge fit). Uncertainty of tip position ≤ 1 µm (k = 2). |
| **R6 grip-impedance rig** | B06 | Pen-shaped handle (Ø15 mm, 150 mm, ~30 g) with an embedded 6-axis F/T sensor between grip sleeve and shaft, triaxial accelerometer ≥ 1 kHz, stylus tip. **Electrodynamic shaker** (≥ 10 N, 1–200 Hz) with stinger and **impedance head** at the drive point. **Vertical voice-coil platen** under the paper for normal-direction excitation (±0.3 mm, 1–50 Hz) on a force plate. Forearm support; visual feedback of normal force. |
| **R7 electronics and HIL bench** | F01, F02, P01, P02, C02, E02 (timing) | 16-channel **logic analyser** ≥ 100 MS/s. 4-channel oscilloscope ≥ 200 MHz with a **current probe** (≥ 10 MHz, ±1 %). Programmable **power supply / source-measure unit** with ≥ 10 kS/s current logging (1 µA–3 A, ±0.3 %) and ramp control for brown-out. Solid-state and relay **fault-injection board** (coil short < 1 µs, open lead, Hall supply cut, SPI line freeze). **Battery cycler**. Thermal chamber. **Medical-grade USB isolator** for any human-connected session. |
| **R8 fatigue rig** | M02, B10 | Resonant or shaker-driven flexure fatigue stations (100–300 Hz). Amplitude control by laser displacement (≤ 0.5 µm). Miniature strain gauges on sacrificial coupons. Resonance tracking for crack detection. Stereo microscope (≥ 50×). Access to SEM for fractography. Axial load frame with 0–10 N load cell (±0.1 % FS). |

### 0.10 Laboratory safety

- Beryllium–copper is formed, etched and cut under beryllium dust controls (AMF notes §2.2).
- Li-ion cells are charged and cycled in fire-safe containers. Abuse tests (short circuit, crush, over-charge) are done only at an accredited laboratory (EXP-P02).
- Laser sensors are class 2 or 3R, with signage.
- **No participant touches a powered prototype before gate G-S** (`prototype_stages.md`).

---

## 1. Experiment index

The "Gates" column lists decisions (DEC-…, `docs/decisions.md`), requirements (REQ-…, `docs/requirements.csv`) and stage gates (G-…, `prototype_stages.md`).

| ID | Title | Stage | Rig | Gates | Depends on |
|---|---|---|---|---|---|
| EXP-B01 | Refill drag and contact-reaction map (includes refill metrology) | A | R1, R3 | DEC-003, DEC-008, REQ-ACT-001, REQ-MECH-008, actuator freeze | R1 qualification |
| EXP-B02 | Friction vs speed; LuGre identification | A | R1 | contact model P-9, DEC-011 | B01 |
| EXP-B03 | Actuator coupons: force–current–position map, R, L, thermal, gap | A | R4 | DEC-003, DEC-007 rev., DEC-012, REQ-ACT-001/002, REQ-SNS-004, actuator freeze | coupons built |
| EXP-B04 | Hall and optical calibration against a motion stage; page workspace | A (rig), B (pen) | R5 | REQ-MECH-001, REQ-SNS-004, CAL_HALL | B03, B05 |
| EXP-B05 | Stage FRF, stiffness, stops, axial path, contact chatter | A, B | R2, R5 | REQ-ACT-003, REQ-CTRL-002, REQ-MECH-002/003/004, REQ-SNS-005, DEC-011 | B04 |
| EXP-B06 | Grip impedance incl. normal direction; γ identification (participants) | A (bench), B (in-pen γ) | R6 | DEC-006, REQ-CTRL-006, hand model P-13 | ethics approval |
| EXP-B07 | Coil and skin temperature | A (coupon), B, C (pen) | R4, R7 | REQ-THM-001/002, REQ-ACT-002, DEC-008, G-S | B03 |
| EXP-B08 | Ink tolerance to modulated normal force | A | R1, R3 | REQ-MECH-005, DEC-004, DEC-006 | B01 |
| EXP-B09 | Bench cancellation with injected disturbance and µm ink metrology | A (rig), B (pen) | R2, R3 | G-B, G-C, REQ-VAL-001, REQ-CTRL-003/005/006/007/008, DEC-009 | B01, B02, B04, B05, B06, B08, F01 |
| EXP-B10 | Durability: flexure cycling, refill exchange, drop | B, C | R8, R5 | REQ-MECH-002/004/006/008, G-C | M02 |
| EXP-S01 | Optical-sensor latency and accuracy | A, B | R5 | DEC-005, REQ-SNS-001/002, REQ-CTRL-003 | — |
| EXP-S02 | Capture and fusion accuracy against references | B, C | R2, R3 | REQ-CAP-001/003, COR-16 | S01, B04 |
| EXP-F01 | Hardware fault injection | A (board), B, C | R7, R2 | REQ-SAF-001/002/004, REQ-PWR-003, DEC-015, G-S | bring-up steps 1–10 |
| EXP-F02 | Firmware robustness | B, C | R7 | REQ-CTRL-001/004, REQ-SAF-001/003/004, REQ-SNS-003, DEC-010/015/016, G-S | F01 |
| EXP-M02 | Flexure fatigue coupons | A | R8 | REQ-MECH-006/007, DEC-007 | coupons |
| EXP-M03 | Mass, centre of mass and balance of built pens | B, C, D | — | REQ-FORM-001…004 | pens built |
| EXP-P01 | Power and runtime | C (and D) | R7, R2 | REQ-PWR-001, REQ-ACT-002, DEC-008 | P02 |
| EXP-P02 | Charging and battery safety pre-compliance | C | R7 | REQ-PWR-002/003, REQ-THM-001, G-C | cell samples |
| EXP-E01 | Estimator bake-off on recorded writing at matched false correction | offline, after H01 | compute | DEC-009, DEC-016, REQ-ML-001, REQ-CTRL-007, REQ-DATA-001 | H01 |
| EXP-E02 | Closed-loop replay of recorded tremor on the B09 rig | B | R2, R7 | REQ-ML-002, REQ-CTRL-005, REQ-SAF-003, DEC-016 | E01, B09 |
| EXP-C01 | Recognition accuracy (CER/WER, writer-disjoint) and search | C | compute | DEC-013, REQ-APP-001, REQ-DATA-001 | C02; H01/H06 ink |
| EXP-C02 | Capture fidelity end to end | C | R7 | REQ-CAP-001/002, DEC-017, G-C | F02 |
| EXP-A01 | AI grounding audit | C | compute + raters | REQ-APP-002, REQ-USR-003, DEC-017 | C01 |
| EXP-H01…H06 | Human-participant studies | see `human_study_plan.md` | — | REQ-USR-\*, REQ-VAL-002, DEC-002/008/009/016 | ethics |

---

## 2. EXP-B01: Refill drag and contact-reaction map

### Purpose and what it gates

This experiment measures the full contact reaction on a real D1 refill writing on real paper. The quantity of interest is its component perpendicular to the pen axis, |R⊥|, which the stage must carry (COR-01, P-5…P-7). It is measured as a function of normal force, altitude, stroke direction, ink, paper, underlay and speed, including reciprocation at 3–15 Hz.

It is research question rank 1 (`docs/research_questions.md`). The load enters the copper loss squared (P-15), and the Monte Carlo ranks normal force as the dominant driver of heat (ρ = 0.89) and μ as the dominant driver of estimator performance (ρ = 0.52, `results/sim/mc_sensitivity.json`).

- **Decisions gated:** DEC-003 (front-pivot lever; revisit trigger "EXP-B01 load map") and DEC-008 (skid and bias product candidates); the actuator freeze.
- **Requirements gated:** REQ-ACT-001.
- **Parameters replaced:** `writing.mu_eff`, `mu_static_ratio` and `paper_stiffness` in `config/parameters.yaml`.
- **Model validated:** contact model P-5…P-7 (`docs/physics.md` validation table).

**Part 0 also measures the refill itself:** mass, centre of mass and dimensions. These feed REQ-MECH-008, the Hall sense-magnet tolerance stack S5 (`mechanics/README.md`) and the `refill.*` parameters. The parameter file currently points those notes at EXP-B02; see `README.md` for this inconsistency.

### Hypotheses

- **H-B01-1.** P-6 with a per-(ink, paper, underlay) μ(N) predicts mean |R⊥| within ±15 % across the map (AC-B01-03).
- **H-B01-2.** At the design point (N = 1 N, θ = 50°, μ ≈ 0.15), mean |R⊥| ≈ 0.64 N.
  - Prediction: `results/sim/nominal/metrics.json` "static", v0.4.4: 0.638 N simulated, 0.643 N analytic.
  - This is below the 0.75 N continuous capability of REQ-ACT-001 (AC-B01-01).
- **H-B01-3.** Kinetic μ lies in 0.09–0.40 (CON-13, CON-14) and breakaway/kinetic in 1.0–2.0 (AC-B01-04, AC-B01-05).
- **H-B01-4.** Friction ripple in 3–15 Hz is ≤ 25 % of the mean (CON-15) (AC-B01-06).
- **H-B01-5.** Continuous ink needs N ≤ 0.30 N, the constant nib force assumed for configuration D in `results/thermal/thermal.json` (AC-B01-07).
- **H-B01-6.** In the tremor band, the paper under a reciprocating nib behaves as a stiffness plus damping (pre-sliding) at small amplitude and as Coulomb friction above a transition amplitude. No source quantifies this (CON notes §2.4 item 2). This hypothesis is characterised, not accepted or rejected; its parameters go to EXP-B02.

### Equipment

- Rig R1 (§0.9), with the F/T sensor between the pen holder and the fixed frame so that the sensor is not accelerated when the paper moves.
- Inks: three D1 refills of the same ball class (0.7 mm per CAD): a standard oil-based ink, a low-viscosity ("hybrid") oil ink, and a gel ink. These span CON-13's 0.09–0.17 range.
- Papers: ISO 12757-1 test paper (80 ± 5 g/m², CON-21), a 60–70 g/m² notebook paper, and a recycled copy paper.
- Underlays: hard (glass), a pad of 50 sheets, and a soft 3 mm elastomer mat (CON notes §2.4).
- Refill metrology (Part 0):
  - analytical balance, 0.1 mg;
  - knife-edge centre-of-mass fixture, ±0.2 mm;
  - digital micrometer, ±2 µm;
  - optical comparator or measuring microscope for ball diameter and protrusion, ±2 µm.

### Setup

1. Condition the paper for ≥ 24 h at 23 °C / 50 % RH.
2. Mount the refill in a stiff holder that reproduces the Rev A cone clamp (DEC-004). The holder carries fine type-T thermocouples on the refill tip body.
3. Zero the F/T sensor with the pen lifted before every condition.
4. Calibrate the F/T sensor in situ at the start of each session: dead weights 0.2–4 N applied along the pen axis and perpendicular to it, at θ = 35°, 50° and 75°.

### Procedure

- **Part 0: refill metrology.** 10 refills per ink type:
  - mass;
  - centre of mass from the ball;
  - overall length and tube diameter against ISO 12757-1 type D (length 67 +0.3/0 mm, tube Ø 2.35 0/−0.05 mm; CON-22);
  - ball diameter and protrusion.
- **Part 1: static indentation.** θ = 50°. N ramps 0 → 4 N → 0 at 0.2 N/s for each paper × underlay, three repeats. Record N and vertical displacement → contact stiffness (secant 0.5–1.5 N) and hysteresis.
- **Part 2: steady-sliding map.** A fresh track for every stroke (lateral offset ≥ 1 mm); stroke length 20 mm; the first and last 2 mm are excluded from analysis.
  - *Core grid* on the nominal ink and paper (oil-based, ISO test paper, hard underlay): N ∈ {0.2, 0.5, 1, 2, 4} N × θ ∈ {35, 45, 55, 65, 80}° × β ∈ {0, 45, …, 315}° × v ∈ {1, 10, 30, 100} mm/s. That is 800 conditions, each repeated 3 times with 3 refills (one refill per repeat), in randomised order.
  - *Reduced grid* on each of the 8 other ink × paper combinations and on the two soft underlays: N ∈ {0.5, 1, 2} × θ ∈ {45, 60} × β ∈ {0, 90, 180, 270} × v ∈ {10, 30}. That is 48 conditions × 3 repeats.
  - *Reference condition* (ISO 12757-1 write test, CON-21): 1.5 N, 75°, 75 mm/s, on every ink and paper, for comparison with manufacturer data.
- **Part 3: reciprocation.** The paper platen reciprocates along t1 (in the tilt plane) and t2 (lateral).
  - Grid: amplitude ∈ {0.02, 0.05, 0.1, 0.2, 0.5} mm × f ∈ {3, 5, 8, 10, 12, 15} Hz × N ∈ {0.5, 1, 2} N × θ ∈ {45, 60}°.
  - Each condition is run with and without a superimposed slow drift of 10 mm/s. The drift represents writing motion under tremor: the ball keeps rolling.
  - 5 s per condition, 3 repeats.
- **Part 4: ink-continuity threshold.** At v = 30 mm/s and θ = 50°, N ramps linearly from 1.0 to 0.05 N over a 100 mm line, on every ink and paper, 5 repeats. The line is scanned with R3; the threshold is the normal force at which the gap fraction first exceeds 1 %.

### Sample size and repeats

- The core grid has 3 repeats × 3 refills. It separates refill-to-refill variance from within-refill variance with a two-level random-effects model.
- To resolve the ±15 % model band with TUR ≥ 4 (per-condition half-width ≤ 3.75 % of the mean), three repeats are enough if the within-condition CV is ≤ 2.4 %: E = t₀.₉₇₅,₂ · s/√3 = 4.30 · s/1.73. If the pilot CV is larger, repeats increase to 6.
- Part 0 uses 10 refills per type: a tolerance check, 0/10 out of tolerance required (AC-B01-10).

### Data format

One HDF5 file per condition with:

- F/T (Fx, Fy, Fz, Tx, Ty, Tz) at 5 kHz;
- stage encoder x, y;
- vertical displacement;
- sync line;
- attributes: θ, β, v, N setpoint, ink lot, paper batch, underlay, refill id, T, RH.

Scans for Part 4 follow R3. Metadata and naming follow `records/README.md`.

### Analysis

1. Transform the measured force into the page frame {P} and the pen frame (a, t1, t2) with the measured θ and β (P-1). N = −F·n. Friction f is the in-plane part; μ = \|f\|/N; |R⊥| = \|F − (F·a)a\|.
2. Per condition, over the steady window, compute the mean, RMS, 95th and 99th percentiles of |R⊥|, and the PSD of R⊥ from 1 to 500 Hz.
3. **Model test (AC-B01-03).**
   - Fit μ(N) = μ₀ + μ₁N per (ink, paper, underlay) on the θ = 50° data only.
   - Predict mean |R⊥| with P-6 for all other θ, β and v.
   - Report the fraction of conditions within ±15 %.
4. **Design numbers (AC-B01-01, AC-B01-02).**
   - Mean |R⊥| at the design point, averaged over the 8 directions.
   - 99th percentile over the product envelope N ≤ 1.2 N, θ ≥ 45° (COR-26).
   - Per newton of normal force, compare with the 0.25–0.9 N/N expected at 55° (CON notes §2.2).
5. **Breakaway.** Peak tangential force in the first 2 mm divided by the steady kinetic value.
6. **Reciprocation.**
   - Hysteresis loops of force against displacement: loop area (energy per cycle), reversal stiffness and equivalent viscous damping.
   - The transition amplitude from pre-sliding to gross sliding, as a function of N and drift.
7. **Ink continuity.** Logistic regression of gap presence against N per ink and paper, and the N at which the gap fraction reaches 1 %.
8. **Uncertainty** (AC-B01-09). F/T calibration, angle error (∂|R⊥|/∂θ = N·sin θ at μ = 0), crosstalk and thermal drift.

### Acceptance criteria

<!-- AC-TABLE:EXP-B01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B01-01 | REQ-ACT-001 | Mean transverse contact reaction \|R⊥\| (component of the measured contact force perpendicular to the pen axis), averaged over 8 stroke directions, steady sliding, N = 1.00 ± 0.05 N, θ = 50°, v = 30 mm/s, nominal ink/paper (oil-based D1, ISO 12757-1 test paper, hard underlay) | ≤ 0.75 N | requirement | REQ-ACT-001 continuous capability 0.75 N; prediction 0.64 N (results/sim/nominal/metrics.json static, v0.4.4; P-6 with mu 0.15) | DEC-003; DEC-008; actuator freeze |
| AC-B01-02 | REQ-ACT-001 | 99th percentile of \|R⊥\| (1 kHz samples, all 8 directions, v 3-100 mm/s) over the proposed product envelope N ≤ 1.2 N and θ ≥ 45°, all inks, papers and underlays | ≤ 1.4 N | requirement | REQ-ACT-001 2-s capability 1.4 N; envelope from COR-26 | DEC-008; REQ-ACT-001 revision |
| AC-B01-03 | — | Contact model P-6: fraction of map conditions (θ 35-80°, all beta and v) in which \|R⊥\| predicted with mu(N) fitted per ink/paper/underlay on θ = 50° data is within ±15 % of the measured mean | ≥ 90 % | hypothesis | docs/physics.md model-validation table (Contact P-5...P-9: \|R⊥\| within ±15 %); 90 % coverage engineering judgement | sim contact model; EXP-B09 comparability |
| AC-B01-04 | — | Kinetic friction coefficient μ_k = mean \|tangential force\| / N in steady sliding at N 1 N, θ 50°, v 30 mm/s, for every ink x paper x underlay | within 0.09-0.40 | hypothesis | CON-13 (0.09-0.17 at 90°), CON-14 (0.10-0.40); config writing.mu_eff range 0.05-0.35 (assumption) | config writing.mu_eff range; Monte Carlo re-run (kf_asr ratio most sensitive to mu, results/sim/mc_sensitivity.json) |
| AC-B01-05 | — | Breakaway ratio: peak tangential force in the first 2 mm after a 1 s dwell / steady kinetic tangential force, per condition | within 1.0-2.0 | hypothesis | config writing.mu_static_ratio range 1.0-2.0 (assumption, nominal 1.3) | config mu_static_ratio; DEC-011 revisit (breakaway transients) |
| AC-B01-06 | — | Friction ripple: RMS of the 3-15 Hz band-passed tangential force / its mean, steady sliding, nominal ink/paper, v 10-75 mm/s | ≤ 0.25 | hypothesis | CON-15 (friction varies about ±25 % along strokes) | servo disturbance model; REQ-MECH-005 budget |
| AC-B01-07 | — | Minimum normal force for continuous ink: lowest N at which the ink gap fraction over 100 mm is ≤ 1 % (v 30 mm/s, θ 50°), worst case over inks and papers | ≤ 0.30 N | hypothesis | constant-force nib Fc = 0.30 N assumed for configuration D (results/thermal/thermal.json case D); 1 % gap definition engineering judgement | DEC-008 (configuration D feasibility) |
| AC-B01-08 | — | Normal contact stiffness of paper + underlay: secant slope of N vs indentation between 0.5 and 1.5 N at θ 50°, each paper x underlay | within 1e4-2e5 N/m | hypothesis | config writing.paper_stiffness range (assumption) | config paper_stiffness; DEC-011 (stage-against-paper mode ~180 Hz) |
| AC-B01-09 | — | Measurement qualification: expanded uncertainty (k = 2) of \|R⊥\| over 0.2-4 N | ≤ max(3 % of reading, 10 mN) | derived | derived: TUR ≥ 5 against the ±15 % model band of AC-B01-03 | validity of all EXP-B01 verdicts |
| AC-B01-10 | REQ-MECH-008 | Refill metrology (Part 0), 10 refills per type: overall length and tube diameter against ISO 12757-1 type D (length 67 +0.3/0 mm, tube 2.35 0/-0.05 mm) | 10/10 within tolerance | derived | CON-22 (ISO 12757-1:2017 Fig. 2); tolerance stack S5 in mechanics/README.md (VERIFY ISO class) | DEC-004; refill seat (REQ-MECH-008); Hall force re-zero (S5) |
| AC-B01-20 | REQ-ENV-002 | Transverse reaction map covers normal force 0.2-2.0 N at 35-75° with the stated repeats (coverage of the declared envelope, not a pass on load) | ≥ 100 % of the grid points | requirement | REQ-ENV-002 range; COR-26 writer means 0.56-2.08 N | REQ-ACT-001 revision; DEC-008 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (11 rows for EXP-B01).
<!-- AC-TABLE:EXP-B01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Design-point load > 0.75 N (AC-B01-01 fails), or envelope p99 > 1.4 N (AC-B01-02) | REQ-ACT-001 is under-specified. Copper loss scales with F², so configuration B at the design point exceeds the 0.412 W moving-coil allowable (`results/thermal/thermal.json`, v0.4.4) by more than already predicted. **DEC-008 becomes mandatory** (D or E as the product baseline); DEC-003 is re-opened for the research pen (fixed-coil variant B-MM). |
| P-6 fails the ±15 % band (AC-B01-03) | Contact model P-5…P-7 is replaced before any B09 comparison. The simulated cancellation numbers are not used for decisions until re-validated. |
| μ outside 0.09–0.40, or breakaway ratio > 2 | Update `writing.mu_eff` and `mu_static_ratio` and re-run the Monte Carlo and the estimator tuning (kf_asr is most sensitive to μ). Large breakaway transients re-open DEC-011 (servo without contact feedforward). |
| N_min for continuous ink > 0.30 N (AC-B01-07) | The configuration-D constant-force nib must be raised. D's copper loss scales with F², so re-run the D rows of `analysis/config_trade.py` and `analysis/thermal.py` before the DEC-008 decision. |
| Paper stiffness outside 1×10⁴–2×10⁵ N/m | The stage-against-paper mode (~180 Hz, DEC-011) moves. Repeat the bounce analysis (`sim/diag_ff_chatter.py`) before EXP-B05 in contact. |
| Refill dimensions outside ISO tolerance, or spread > ±0.3 mm in length | The Hall force channel re-zero at every insertion (tolerance S5) is mandatory, and REQ-MECH-008's seat design must take up the spread. |

### Risks and controls

| Risk | Control |
|---|---|
| F/T thermal drift | Zero before each condition; interleave check-standard weights every 50 conditions. |
| Pen-holder compliance changes θ under load | Measure θ under 4 N with an inclinometer; correct in analysis. |
| Ink depletion and ball wear over thousands of strokes | Log the track length per refill; replace at 50 m; include the refill id as a random effect. |
| Paper tearing at 4 N / 35° on the soft underlay | Abort the condition if the tangential force exceeds 3 N; log it. |
| Platen vibration in reciprocation contaminates the force | Accelerometer on the platen; inertial compensation (platen mass × acceleration), verified with the pen lifted. |
| Operator bias in scan thresholds | Automatic pipeline with frozen parameters; blind coding (§0.6). |

---

## 3. EXP-B02: Friction vs speed; LuGre identification

### Purpose and what it gates

This experiment identifies the parameters of the LuGre friction model P-9 (σ0, σ1, σ2, μs, μk, v_s, all normalised by N) for the nib–paper contact at writing loads. It includes velocity reversals and pre-sliding at tremor amplitudes, which no published source covers (CON notes §2.4).

- **Validates** P-9 against the physics.md acceptance (fit R² > 0.9).
- **Supplies** the simulator's contact model before any bench–simulation comparison in EXP-B09.
- **Gates** DEC-011 (revisit trigger: "Bench servo tests with real paper stacks").

Friction is the dominant parameter for estimator performance in the Monte Carlo (`results/sim/mc_sensitivity.json`; `docs/sim_report.md` §3), so this experiment carries more weight than its size suggests.

### Hypotheses

- **H-B02-1.** A single-state LuGre model fitted on velocity steps and sweeps predicts held-out sinusoidal reciprocation (3–15 Hz) with R² > 0.9 (AC-B02-01).
- **H-B02-2.** The Stribeck velocity lies in 0.5–10 mm/s, the declared simulation range (AC-B02-02).
- **H-B02-3** (characterised, not accepted). Breakaway rises with dwell time before motion (pen-down after a pause).

### Equipment and setup

- Rig R1 with the linear-motor stage (velocity ripple ≤ 1 % from 0.01 to 200 mm/s; AC-B02-03).
- A capacitive or interferometric sensor (≤ 10 nm resolution) on the pen holder for pre-sliding displacement.

### Procedure

The nominal ink and paper on the hard underlay, plus the lowest-μ and highest-μ ink × paper combinations found in EXP-B01. N ∈ {0.5, 1, 2} N, θ ∈ {45, 60}°.

1. **Velocity steps.** From rest to v ∈ {0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 200} mm/s, in both directions along t1 and t2, after a dwell of 1 s. 3 repeats.
2. **Slow triangular sweeps through zero velocity.** Amplitudes 5 µm, 20 µm, 50 µm, 0.2 mm and 2 mm, to capture pre-sliding hysteresis and the transition to gross sliding.
3. **Dwell series.** 1, 10 and 60 s at rest before a 10 mm/s step. 3 repeats.
4. **Validation set (not used for fitting).** Sinusoidal reciprocation at 3–15 Hz, amplitudes 0.02–0.5 mm, reusing the EXP-B01 Part 3 protocol and fresh tracks.

### Sample size

- Three repeats per step condition.
- The fit uses all steps and sweeps (≈ 360 records per ink × paper). The validation set has ≥ 30 records per ink × paper.
- R² is reported with a bootstrap 95 % CI over records.

### Data format

As EXP-B01, plus the displacement channel at 10 kHz.

### Analysis

1. Fit the steady-state curve g(v) = μk + (μs − μk)·exp(−(v/v_s)²) plus viscous σ2·v/N on the plateau values of the velocity steps.
2. Fit σ0 from the initial slope of force against displacement at reversals, and σ1 from the damping of the pre-sliding response.
3. Simulate the validation records with the fitted parameters (the same integrator as `sim/pensim/core.py`). Report R² and NRMSE per record and pooled.
4. Compare with the simulator's current ranges and report which parameters fall outside.

### Acceptance criteria

<!-- AC-TABLE:EXP-B02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B02-01 | — | LuGre (P-9) fit quality: R² of predicted vs measured tangential force on held-out sinusoidal reciprocation records (3-15 Hz, ±0.02-0.5 mm), parameters fitted on velocity-step and sweep records only | > 0.9 | hypothesis | docs/physics.md model-validation table (LuGre fit R² > 0.9) | sim contact model (P-9); EXP-B09 comparability; DEC-011 |
| AC-B02-02 | — | Stribeck velocity v_s from the steady-state friction-velocity fit | within 0.5-10 mm/s | hypothesis | config writing.stribeck_speed range (assumption) | config stribeck_speed; Monte Carlo re-run |
| AC-B02-03 | — | Stage velocity ripple in constant-velocity segments, 0.01-200 mm/s, pen lifted | ≤ 1 % RMS of setpoint | derived | engineering judgement (the friction-velocity curve must not be smeared by the instrument) | validity of EXP-B02 verdicts |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-B02).
<!-- AC-TABLE:EXP-B02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| R² ≤ 0.9 | LuGre is inadequate for the nib (for example because ball rolling, ink film and paper plasticity dominate). Replace P-9 with a multi-state or rolling-resistance model and update `docs/physics.md` before trusting EXP-B09 predictions. |
| Very stiff pre-sliding (tremor-amplitude motion at stick) | The paper grounds the nib in the tremor band: cancellation becomes a force problem rather than a position problem. Evaluate impedance or force control, the hypothesis listed in ACT notes §2, and re-open DEC-011. |
| Strong dwell effect | Pen-down transients need a start-of-stroke authority ramp (limiter) and must be included in EXP-B09 test paths. |

### Risks and controls

| Risk | Control |
|---|---|
| Stage velocity ripple aliasing into the friction curve | Qualify the ripple with the pen lifted (AC-B02-03). |
| Ink film build-up on repeated tracks | Fresh track per record. |
| Thermal drift in the displacement sensor | Reference target on the frame, measured before and after each record. |

---

## 4. EXP-B03: Actuator coupons (force–current–position map, R, L, thermal, gap)

### Purpose and what it gates

This experiment measures the per-axis force constant K_f(q) over the actuator stroke, cross-coupling, R20, L(f, q), the motor constant K_m, the coil thermal resistance and time constant, current-to-Hall crosstalk and the as-built paddle–magnet gap. It uses coupons of the Rev A rear annular actuator: moving-coil variant B and moving-magnet variant B-MM.

- **Produces** `CAL_ACT` (`docs/icd.md` §3: K_f(q) on a 5 × 5 grid, R20, cross-coupling).
- **Validates** EM model P-14…P-16 (K_f(q) and K_m within ±10 %).
- **Gates** DEC-003 (revisit trigger "EXP-B03 actuator coupons"), DEC-007 rev. (revisit trigger "actuator coupon gap measurement"), DEC-012 (revisit trigger "coil build R, L, K_f measured") and the actuator freeze.
- **Requirements:** REQ-ACT-001, REQ-ACT-002, REQ-SNS-004 (crosstalk).
- **Other items:** the coil-lead strain relief (`electronics/README.md`) and research question rank 9 (K_m ≥ 0.3 N/√W inside Ø14.6 mm; `docs/plan.md` §3 now sets ≥ 0.29 N/√W for the 0.50 mm gap).

### Hypotheses and predictions

| Id | Hypothesis | Prediction | Source |
|---|---|---|---|
| H-B03-1 | K_f at centre | 0.717 N/A (6 Ω winding, 0.50 mm gap) | `config/parameters.yaml` v0.4.1 `actuator.Kf`; DEC-012, DEC-007 rev. |
| H-B03-2 | K_m at centre | 0.293 N/√W at 20 °C, 0.257 at the 96.6 °C design coil | `results/electronics/drive_sense.json` (v0.4.4) |
| H-B03-3 | K_f falls toward the stroke corners | about 37 % lower at ±1.6 mm (actuator coordinates) | `results/em/em_actuator.json` (rearA_iron: Kf_variation 36.9 %; v0.2.0, 11 Ω winding, 0.45 mm gap — rescale) |
| H-B03-4 | Cross-axis force at the stroke corners | ≤ 0.24 N/A | `results/em/em_actuator.json` `cross_force_max_N_per_A` |
| H-B03-5 | Moving-coil thermal resistance, coil to magnets and iron | ≈ 145 K/W (air conduction across two 0.50 mm gaps); ≈ 157 K/W steady coil-to-ambient in the pen | `results/thermal/thermal.json` `two_node_governor_model` (v0.4.4); `config` `actuator.Rth_coil_amb` |
| H-B03-6 | Requirements are **expected to fail by calculation** | REQ-ACT-002 needs K_m,20 ≥ 0.37 N/√W (derivation in AC-B03-03); REQ-ACT-001's continuous 0.75 N needs 0.65 W of copper loss referenced to 20 °C (0.85 W at the 96.6 °C design coil) against 0.412 W allowable; its 1.4 N/2 s needs 0.62 A per axis against the 0.60 A clamp (REQ-SAF-002, config) | derivations in `acceptance_criteria.csv` |

### Equipment and setup

- Rig R4 (§0.9).
- Three coupons per variant, built with the production process: winding, bonding, magnet grade and back iron as in CAD Rev A.1.
- A TMAG5170 evaluation board positioned per CAD (1.2 mm Hall gap) for crosstalk.
- An optical CMM or feeler set (10 µm steps) for the gap.

### Procedure

1. **Incoming inspection.**
   - Paddle–magnet gap on both faces with the CMM at q = 0 and at full tip travel (0.60 mm, i.e. ±1.9 mm at the actuator with n = 3.17) in 12 directions. The last check uses a dummy lever.
   - Magnet flux-density map at 0.5 mm with a Hall probe.
2. **R20 and L.**
   - R20 4-wire at 20.0 ± 0.5 °C.
   - L and R with the LCR meter from 100 Hz to 20 kHz at q = 0 and at the 4 corners, with and without back iron.
3. **Force map.**
   - 7 × 7 grid over ±1.6 mm per axis (the grid of `em_actuator.json`).
   - Currents {−0.6, −0.3, −0.1, +0.1, +0.3, +0.6} A per axis, one axis at a time, then both axes together (superposition).
   - Record the 6-axis force and torque. Hold time 2 s per point to avoid heating (coil ΔT < 2 K, checked by resistance).
4. **Linearity and saturation.** 0 → 0.8 A (hardware trip level) in 0.05 A steps at q = 0; pulses to 1.2 A of ≤ 100 ms.
5. **Back-EMF.** The shaker drives the paddle at 10–50 Hz and ±0.5 mm with the coil open. K_f from V/ẋ is an independent check of item 3.
6. **Thermal.**
   - DC steps of 0.2, 0.3, 0.412 and 0.6 W per coil pair in still air at 25 °C. Each step runs to steady state (dT/dt < 0.1 K/min) or to 110 °C coil.
   - Coil temperature by resistance (α_cu = 0.00393 K⁻¹, AMF-29) and thermocouples on the magnets and back iron.
   - Repeat at 35 °C ambient.
7. **Continuous-force test (REQ-ACT-001).** Hold 0.237 N at the actuator (0.75 N tip-equivalent at n = 3.17) for 30 min in the thermal environment of EXP-B07. Stop at 120 °C coil. The 2 s / 1.4 N tip-equivalent test is run with the software clamp disabled on the bench supply only, to measure the current actually needed.
8. **Crosstalk.** Hall reading against coil current at fixed q (9 positions), at DC and at 40 kHz PWM with mid-period and edge sampling (open issue E-4).
9. **Lead strain relief.** Flex the moving-coil leads through the full stroke 10⁴ times at 5 Hz as a screening test; the life test is in EXP-B10. Measure resistance before and after.

### Sample size

- Three coupons per variant, reported per coupon and pooled; coupon-to-coupon spread is itself a result.
- Force-map points are single measurements with the regression over 6 currents (6 points, R² reported). Repeatability is checked by re-measuring 5 random grid points at the end of the map (≤ 1 % difference required, or the map is repeated).

### Data format

HDF5 per coupon: force map (q1, q2, i1, i2 → F, T), LCR sweeps, thermal time series, crosstalk tables, gap measurements. `CAL_ACT` is exported in the ICD §3 layout (5 × 5 resampled grid).

### Analysis

1. K_f(q) is the slope of in-axis force against current at each grid point. The intercept at zero current is the magnetic spring force of the iron, the "negative stiffness" item in AMF notes §2.6.
2. K_m = K_f/√R. Also report the hot K_m (R at 85 °C).
3. Compare with the model rescaled to the built winding (K_f ∝ √R at fixed copper volume, P-15) and the measured gap (the gap rescaling factor comes from `mechanics/tolerance_analysis.py`).
4. Thermal: fit a first-order, then a second-order, response. Report R_th coil→ambient, R_th coil→housing and τ.
5. Crosstalk: a linear regression in T/A, converted to tip µm/A through CAL_HALL. The residual after linear compensation is the REQ-SNS-004 quantity.

### Acceptance criteria

<!-- AC-TABLE:EXP-B03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B03-01 | REQ-ACT-001 | Force constant K_f at the stroke centre (q = 0), 20 °C, per axis: slope of in-axis force vs current over ±0.6 A | within 0.717 N/A ± 10 % | hypothesis | docs/physics.md (K_f within ±10 %); prediction config actuator.Kf 0.717 N/A (v0.4.1; 6 ohm winding DEC-012, 0.50 mm gap DEC-007 rev.) | DEC-012; EM model P-14 validation |
| AC-B03-02 | — | Motor constant K_m = K_f / sqrt(R20) at the stroke centre, 20 °C (feasibility floor for the Rev A research pen) | ≥ 0.29 N/√W | hypothesis | docs/plan.md s3 (K_m target ≥ 0.29 N/√W at the 0.50 mm gap); docs/research_questions.md rank 9 still states ≥ 0.3 (before the gap change); prediction 0.293 N/√W (results/electronics/drive_sense.json v0.4.1); field model 0.24-0.34 (results/em/em_actuator.json) | DEC-003; actuator freeze |
| AC-B03-03 | REQ-ACT-002 | Motor constant K_m at the stroke centre, 20 °C (level needed to meet REQ-ACT-002 at the design point) | ≥ 0.37 N/√W | derived | derived from REQ-ACT-002 (0.25 W average): K_m20 ≥ F_rms/(n*sqrt(P/duty))*sqrt(1.2555) with F_rms 0.657 N (results/trade/config_trade.json design point), n = 3.17, duty 0.65, hot factor 1.2555 at 85 °C (alpha_cu 0.00393/K, AMF-29) = 0.375; prediction 0.293 -> expected FAIL | DEC-008 (configuration B vs D/E); REQ-ACT-002 revision |
| AC-B03-04 | — | K_f(q) map: fraction of the 7 x 7 grid points over ±1.6 mm (actuator coordinates) where measured K_f is within ±10 % of the magnetostatic model rescaled to the built winding and gap | = 100 % | hypothesis | docs/physics.md (K_f(q) within ±10 %); model results/em/em_actuator.json Kx_map (v0.2.0; rescale by sqrt(R) and gap factor) | EM model validation; CAL_ACT (docs/icd.md s3) |
| AC-B03-05 | — | Coil resistance R20 (4-wire, 20.0 ± 0.5 °C) | within 6.0 ohm ± 5 % | hypothesis | DEC-012 winding (headroom analysis in results/electronics/drive_sense.json assumes 6.0 ohm); ±5 % engineering judgement | DEC-012 (voltage headroom at 3.3 V) |
| AC-B03-06 | — | Coil inductance at 1 kHz, q = 0 | within 82-380 µH | hypothesis | config actuator.L range (air-core estimate 175 µH scaled from results/em) | current-loop tuning (P-17) |
| AC-B03-07 | REQ-SNS-004 | Hall current crosstalk after linear compensation, referred to the tip (9 stage positions, DC and 40 kHz PWM) | ≤ 5 µm/A | requirement | REQ-SNS-004 | Hall placement and sampling (open issue E-4); CAL_HALL |
| AC-B03-08 | — | Coil-to-structure thermal resistance of the moving-coil coupon: (coil temperature by resistance - magnet/back-iron thermocouple) / copper loss, steady state at 0.2-0.45 W, 25 °C still air | within 145 K/W ± 15 % | hypothesis | results/thermal/thermal.json two_node_governor_model.R_coil_iron (conduction across two 0.50 mm air gaps; config actuator.Rth_coil_amb v0.4.3); docs/physics.md (steady rise ±15 %). Replaces the coupon coil-to-ambient metric, which depended on the fixture | DEC-008; open issue M-5; simulator thermal node |
| AC-B03-09 | — | Minimum measured paddle-to-magnet clearance at full tip travel (0.60 mm, 12 directions) on every coupon | > 0 µm (no contact); report vs RSS prediction +93 µm | hypothesis | results/mechanics/tolerance.json via mechanics/README.md (stack S1 front face, RSS +93 µm, Rev A.1) | DEC-007 rev. (revisit trigger: actuator coupon gap measurement) |
| AC-B03-10 | REQ-ACT-001 | Coil hot-spot temperature while holding 0.75 N tip-equivalent (0.237 N at the actuator) continuously for 30 min at 25 °C in the pen thermal environment | ≤ 120 °C | requirement | REQ-ACT-001 with REQ-THM-002; prediction: copper loss 0.65 W referenced to 20 °C (0.85 W at the 96.6 °C design coil) at K_m 0.293 N/√W vs allowable 0.412 W (results/thermal/thermal.json v0.4.4) -> expected FAIL | REQ-ACT-001 revision; DEC-008 |
| AC-B03-11 | REQ-ACT-001 | Coil current needed to hold 1.4 N tip-equivalent for 2 s along one actuator axis, compared with the software current clamp | ≤ current ≤ software clamp | requirement | REQ-ACT-001; required 1.4/(3.17 x 0.717) = 0.62 A exceeds REQ-SAF-002 (0.45 A) and config actuator.i_max (0.60 A) -> CONFLICT to resolve | resolve REQ-ACT-001 vs REQ-SAF-002 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (11 rows for EXP-B03).
<!-- AC-TABLE:EXP-B03:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| K_m < 0.29 N/√W (AC-B03-02) | Rev A (configuration B) cannot hold the design-point load inside the thermal limit even at 65 % duty. DEC-003 stands only for bench research; **DEC-008 D/E becomes the product path**, and the Rev A pen is limited to lighter loads with a thermal governor. |
| K_m between 0.29 and 0.37 N/√W | Rev A is usable as a research instrument but fails REQ-ACT-002. This confirms DEC-008. REQ-ACT-002 must be revised or met by D/E. |
| K_f(q) deviates > 10 % from the model but is repeatable | The model fails (update `analysis/em_actuator.py`), but the pen is usable through `CAL_ACT` compensation. |
| R20 outside 6.0 Ω ± 5 % | Re-run the headroom analysis (`electronics/calcs/drive_sense.py`). Above ~6.3 Ω, parts of the thermally allowed envelope become voltage-limited at 3.3 V (DEC-012). |
| Gap contact at full travel, or clearance well below +93 µm RSS | DEC-007 rev. is re-opened (travel reduction or a wider gap at a K_f cost of 2.9 % per 0.05 mm; `mechanics/README.md`). |
| Coil-to-structure R_th ≫ 145 K/W | The moving coil's heat path is worse than modelled. Test the fixed-coil B-MM variant further (25 K/W, but K_m ≈ 0.2). |
| Crosstalk > 5 µm/A after compensation | Move the Hall sensor or sample mid-PWM (E-4); REQ-SNS-004 is at risk. |

### Risks and controls

| Risk | Control |
|---|---|
| Heating during the force map biases K_f | Short holds; the resistance check before and after each point; discard points with ΔT > 2 K. |
| F/T crosstalk from torques at the paddle | Calibrate the F/T with an offset load at the paddle position. |
| Coupon unrepresentative of the pen (magnet grade, iron) | Build coupons from the Rev A.1 drawings and material certificates; record magnet lot and Br. |

---

## 5. EXP-B04: Hall and optical calibration against a motion stage; page workspace

### Purpose and what it gates

This experiment calibrates the one 3-axis Hall sensor on the lever tail, which gives (q1, q2) from Bx, By and the axial slide s from Bz. The calibration is made against independent tip metrology and produces `CAL_HALL` (`docs/icd.md` §3).

- **Verifies** the page-plane correction workspace of REQ-MECH-001, the Hall noise and rate of REQ-SNS-004, and the calibrated lever-ratio gain (tolerance stack S4, `mechanics/README.md`).
- **Validates** kinematics P-1…P-4, together with EXP-B06, in the physics.md acceptance (< 5 % of stroke). A calibrated normal-compliance mount stands in for the hand.
- **Also calibrates** the scale factor of the optical modules on the nominal paper. Latency and accuracy across paper types and tilt are EXP-S01.

### Hypotheses and predictions

- **H-B04-1.** The ICD calibration model (3 × 3 linear map + offset + cubic terms per axis + current-crosstalk coefficients) reaches ≤ 5 µm RMS tip-referred residual on held-out points (AC-B04-01).
- **H-B04-2 (prediction from P-4; expected to fail at low altitude).**
  - The page disc of radius 0.5 mm in the tilt direction needs a stage radius of 0.5/J_t1, with J_t1 = sin θ + γ cos²θ / sin θ and γ = K_n sin²θ / (K_n sin²θ + k_ax).
  - With K_n = 800 N/m (config `hand.normal_stiffness`) and k_ax = 2 kN/m, the stage motion needed is:

    | θ | 35° | 45° | 50° | 55° | 60° | 75° |
    |---|---|---|---|---|---|---|
    | needed stage radius (mm) | 0.705 | 0.606 | 0.576 | 0.553 | 0.536 | 0.508 |

  - The control limit is q_lim = 0.55 mm and the mechanical stop 0.60 mm (config v0.4.1). **REQ-MECH-001 ("0.5 mm at every altitude 35–75°") is therefore predicted to fail below θ ≈ 56° for K_n ≤ 800 N/m.** With K_n = 3000 N/m the need at 35° drops to 0.52 mm. The measured K_n from EXP-B06 decides.
- **H-B04-3.** The optical scale factor after tilt-dependent calibration is within 1 % (config `sensing.opt_scale_err`).

### Equipment and setup

- Rig R5 with independent tip metrology. The preferred option is a Ø3 mm reference sphere bonded to the carrier 2 mm behind the ball, measured by two orthogonal confocal sensors, with the ball offset measured on the optical CMM before bonding.
- Calibrated normal-compliance mounts for the housing: flexure mounts with K_n = 200, 800 and 3000 N/m, each verified by load against displacement to ±3 %.
- Paper on the R5 stage for optical calibration.

### Procedure

1. **Free-space calibration** (pen or rig module fixed, no paper).
   - Drive the lever with its own actuator through a q grid of 11 × 11 points over ±0.6 mm (the 0.60 mm stop), plus rings at 0.55 mm and 0.58 mm.
   - Repeat at axial slide s ∈ {0, 0.2, 0.4, 0.6} mm, set by an axial load from a micrometer probe.
   - Repeat at coil currents {0, ±0.3} A to separate crosstalk.
   - Record Bx, By, Bz and the true tip position.
2. **Hold-out validation.** 50 random points not used in the fit.
3. **Noise.**
   - 60 s at rest, coils at 0.3 A DC and at 40 kHz PWM, sampled at the rate the firmware uses (2 kHz per `docs/icd.md` §2).
   - Also at 4 kHz if the firmware can sample that fast, because REQ-SNS-004 asks for ≥ 4 kHz (conflict listed in `README.md`).
4. **In-contact page workspace.**
   - The housing sits on a normal-compliance mount on paper over the R5 stage at θ ∈ {35, 45, 50, 55, 65, 75}° and roll ρ ∈ {0, 45, …, 315}°, with N = 1 N.
   - Command page-referenced corrections of increasing radius in 16 directions until q reaches q_lim.
   - Measure the page displacement of the nib: platen fixed, nib-contact point via the sphere metrology plus contact geometry, and cross-checked by writing short ink ticks that are scanned (R3).
   - Repeat with K_n = 200, 800 and 3000 N/m.
5. **Optical scale.**
   - Pen fixed with the nib locked and in contact at 1 N. The stage moves the paper ±5 mm in x and y at 10 mm/s.
   - θ ∈ {35, 45, 55, 65, 75}° and ρ at the three module positions (30, 150, 270°). Fit scale and rotation per module against θ.

### Sample size

- The calibration fit uses ≥ 484 points per s-level (121 grid points × 4 current states).
- Hold-out: 50 points, which gives the RMS residual with a relative standard error of about 10 %.
- Workspace: one sweep per (θ, ρ, K_n) with 16 directions; repeat the 50° / K_n 800 case 5 times for repeatability.

### Data format

HDF5 per session: grid points, Hall raw, reference positions, currents, temperatures. `CAL_HALL` is exported in ICD §3 layout and its version recorded; the workspace table has one row per (θ, ρ, K_n, direction).

### Analysis

1. Least-squares fit of the ICD model, with coefficients and covariance. Residual statistics on the hold-out set.
2. Noise: tip-referred RMS and PSD; bias drift over 60 s.
3. Workspace: the largest page displacement per direction; the minimum over directions and roll is the "guaranteed disc radius". Compare with P-4 using measured θ, K_n and k_ax (EXP-B05).
4. Kinematic model error (AC-B04-05) = |measured − P-4 predicted| / commanded, per point.

### Acceptance criteria

<!-- AC-TABLE:EXP-B04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B04-01 | REQ-SNS-004 | Hall stage-position calibration residual on 50 held-out points over the 0.55 mm control disc, tip-referred, against independent tip metrology | ≤ 5 µm RMS | derived | derived: 10 % of the REQ-CTRL-005 50 µm distortion budget (allocation by engineering judgement) | CAL_HALL acceptance; EXP-B09 readiness |
| AC-B04-02 | REQ-SNS-004 | Hall position noise at rest, tip-referred, both coils at 0.3 A DC and at 40 kHz PWM, at the stage-loop sampling rate | ≤ 2 µm RMS | requirement | REQ-SNS-004 | stage-position sensor choice (E-4) |
| AC-B04-03 | REQ-SNS-004 | Hall sampling rate achieved in firmware | ≥ 4 kHz | requirement | REQ-SNS-004. CONFLICT: docs/icd.md s2 samples the TMAG5170 at 2 kHz | resolve REQ-SNS-004 vs docs/icd.md |
| AC-B04-04 | REQ-MECH-001 | Guaranteed page-plane correction radius: minimum over 16 directions and 8 roll angles of the page displacement reachable within q_lim, in contact at N 1 N, housing on calibrated normal-compliance mounts K_n 200/800/3000 N/m, at each θ in 45-75° (35° characterised) | ≥ 0.5 mm | requirement | REQ-MECH-001; prediction from P-4 (K_n 800 N/m, k_ax 2 kN/m): tilt-plane stage radius needed 0.61/0.58/0.55/0.54/0.51 mm at 45/50/55/60/75° vs q_lim 0.55 mm -> expected FAIL below ~56° | REQ-MECH-001 revision; stop/travel redesign (DEC-007 rev.); product envelope (COR-26) |
| AC-B04-05 | — | Kinematic model P-1...P-4: \|measured - predicted page displacement\| / commanded displacement, θ 35-75°, known K_n mounts | < 5 % of stroke | hypothesis | docs/physics.md model-validation table (kinematics: page displacement error < 5 % of stroke) | Jacobian model validation; REQ-CTRL-006 |
| AC-B04-06 | — | Optical-module scale-factor residual after tilt-dependent calibration (paper moved ±5 mm by the stage) | ≤ 1 % | hypothesis | config sensing.opt_scale_err nominal 0.01 (assumption) | fusion design (DEC-005) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-B04).
<!-- AC-TABLE:EXP-B04:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Guaranteed disc < 0.5 mm at θ < 56° (expected) | REQ-MECH-001 must be revised to the COR-26 product envelope (θ ≥ 45°), or at least restated with a reduced tilt-direction authority. Otherwise the stop radius and q_lim must grow, which costs actuator gap and tolerance margin (DEC-007 rev.). |
| Hall residual or noise fails | Move to the DNP analogue Hall option or a differential pair; re-examine the sense-magnet distance tolerance (S5). |
| P-4 fails with a known K_n | The Jacobian model is wrong. EXP-B09 cannot be compared with simulation until it is fixed (REQ-CTRL-006). |

### Risks and controls

| Risk | Control |
|---|---|
| Reference sphere offset error | Measure the ball-to-sphere vector on the CMM (≤ 2 µm); include it in the uncertainty budget. |
| Actuator heating shifts the magnet field during the map | Limit the duty; resistance check; randomise the grid order. |
| Paper indentation confounds in-contact page displacement | Hard platen for the workspace test; paper stiffness from EXP-B01 in the model. |

---

## 6. EXP-B05: Stage FRF, stiffness, stops, axial path, contact chatter

### Purpose and what it gates

This experiment identifies the plant for the stage servo and checks the mechanical limits.

- **Open-loop transverse dynamics:** m_eq, k_tip, damping, higher modes and cross-axis coupling.
- **Closed-loop bandwidths:** current loop ≥ 2 kHz and position loop ≥ 60 Hz (REQ-ACT-003).
- **Stability margins** of the loaded plant over the declared contact and hand ranges (REQ-CTRL-002).
- **Axial path:** stiffness 1–5 kN/m, compliant range ≥ 1.4 N (REQ-MECH-004); force-sensing noise (REQ-SNS-005). This produces `CAL_AXIAL` (ICD §3).
- **Stops:** radius (REQ-MECH-002) and impact stress (REQ-MECH-002, REQ-MECH-006).
- **Tip-equivalent inertia** (REQ-MECH-003).
- **Chatter against real paper stacks:** the DEC-011 revisit trigger.

It validates P-10…P-12 (resonance ±10 %, stiffness ±15 %).

It runs twice: on the Stage A rig module (commercial VCMs through the same 3.17 lever, `mechanics/README.md`) and on the Rev A/A.1 pen at Stage B. Each run uses its own predictions.

### Hypotheses and predictions

| Quantity | Prediction | Source |
|---|---|---|
| k_tip | 75.8 N/m | `results/mechanics/flexure_calc.json`, gimbal 0.05 × 1.0 × 2.0 mm. The config still carries 150 N/m (`stage.k_tip`), which is inconsistent; see `README.md` |
| m_eq | 13.7 g | Distributed-mass CAD, Rev A.1 (REQ-MECH-003 current estimate). The config still carries 10.3 g, a point-mass approximation |
| Open-loop first mode | (1/2π)·√(75.8 / 0.0137) = 11.8 Hz | calculation from the two rows above |
| k_ax | 1984 N/m | `results/mechanics/flexure_calc.json` |
| Axial overload stop | 0.6 mm, 1.45 N | config `stage.axial_travel` |
| Current-loop crossover | 2.34 kHz at 50° phase margin | `results/electronics/drive_sense.json` |
| Stage-against-paper mode | about 180 Hz | DEC-011, `results/sim/ff_chatter.json` |

### Equipment and setup

- Rig R5 for free-space tests and R2 for in-contact tests.
- Laser Doppler vibrometer (≥ 20 kHz bandwidth, ≤ 0.1 µm/s resolution) or a triangulation sensor on the carrier.
- Miniature impact hammer for modal checks.
- Force probe (0–2 N, ≤ 2 mN) on a micrometer stage for static stiffness.
- Axial load cell (0–5 N, ±0.1 % FS) with a laser displacement sensor.
- High-speed camera (≥ 5 kfps) for stop impacts.
- Strain gauges (0.2 mm grid) on one gimbal blade of a sacrificial build.
- Paper stacks and underlays as EXP-B01.
- Signal injection at the loop-breaking points in a firmware test build.

### Procedure

1. **Static transverse stiffness.** ±0.2 N at the tip in 8 directions with the coils open-circuit (no current). Load–unload, 3 cycles; stiffness and hysteresis.
2. **Axial.** 0 → 2 N → 0 along the refill, 3 cycles: preload knee, secant k_ax, stop position and force.
3. **Open-loop FRF.**
   - Current chirp 1–500 Hz, 0.05 A per axis, response from Hall and LDV: FRF q/i; H1 estimator; coherence ≥ 0.9 required.
   - Free first, then in contact on 3 paper stacks at N ∈ {0.5, 1, 2} N and θ ∈ {35, 50, 75}°.
4. **Current loop.** Inject at the current reference 100 Hz–10 kHz; measure the shunt current: closed-loop bandwidth, loop gain and margins.
5. **Position loop.**
   - Closed-loop q/q_r from 1 to 300 Hz, and loop gain by injection at the error summing point.
   - Free and loaded, over N 0.2–2 N, θ 35–75°, 3 paper stacks, and housing normal-compliance mounts of 200, 800 and 3000 N/m (loaded-plant range of REQ-CTRL-002).
6. **Stops.**
   - Drive the stage into the stop at tip velocities up to 0.05 m/s (`drive_sense.json` `v_tip_stage_max`).
   - Record rebound on high-speed video and blade strain.
   - Measure the stop radius in 12 directions with R5 metrology.
7. **Chatter (DEC-011).**
   - 60 s of scripted writing per paper stack in NEUTRAL and ASSIST_KF with the contact feedforward disabled (as designed).
   - Repeat with the filtered feedforward that DEC-011 keeps "for bench experiments".
   - Count chatter episodes (defined in AC-B05-14).

### Sample size

- FRFs are averaged over 10 chirps per condition; the variance of the FRF estimate follows from the coherence.
- Margins are computed per condition; the minimum over the declared range is the verdict quantity.
- Stops: 12 directions × 3 velocities × 3 repeats.

### Data format

HDF5 FRF files (complex H(f), coherence, raw time series); a margin table per condition; high-speed video (lossless) for stop events; `CAL_AXIAL` in ICD §3 layout.

### Analysis

1. Fit a second-order model plus delay to the open-loop FRF: m_eq from the mass line above resonance, k_tip from the static test and the resonance, damping from the half-power width.
2. Margins from the measured loop gain, with no model in between.
3. Stop stress: the blade strain against impact velocity, extrapolated to the worst case with the beam model (P-12). Uncertainty includes gauge factor and placement.
4. Chatter: the event detector runs on the contact flag (force-plate threshold 0.05 N with 20 ms hold).

### Acceptance criteria

<!-- AC-TABLE:EXP-B05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B05-01 | — | Open-loop first transverse resonance (current-driven chirp, no contact) | within prediction ± 10 % | hypothesis | docs/physics.md (resonance within ±10 %); prediction from as-built k_tip and m_eq, currently 11.8 Hz (75.8 N/m, results/mechanics/flexure_calc.json; 13.7 g, REQ-MECH-003 estimate) | stage model P-10...P-12 validation; servo design |
| AC-B05-02 | REQ-MECH-003 | Tip-equivalent inertia m_eq from the mass line of the transverse FRF | ≤ 12 g | requirement | REQ-MECH-003; current estimate 13.7 g (distributed-mass CAD, Rev A.1) -> expected FAIL | carrier material (M-6 CFRP option); REQ-MECH-003 revision |
| AC-B05-03 | — | Static transverse tip stiffness k_tip (±0.2 N, 8 directions) | within 75.8 N/m ± 15 % | hypothesis | docs/physics.md (stiffness within ±15 %); results/mechanics/flexure_calc.json gimbal 0.05 x 1.0 x 2.0 mm. Note: config stage.k_tip is 150 N/m | stage model validation; config stage.k_tip |
| AC-B05-04 | REQ-ACT-003 | Closed-loop current bandwidth (-3 dB of i/i_ref) | ≥ 2 kHz | requirement | REQ-ACT-003; prediction 2.34 kHz crossover at 50° phase margin (results/electronics/drive_sense.json) | DEC-012 (40 kHz PWM) |
| AC-B05-05 | REQ-ACT-003 | Closed-loop position bandwidth (-3 dB of q/q_r), free and in contact (N 1 N, θ 50°) | ≥ 60 Hz | requirement | REQ-ACT-003 | servo design; REQ-CTRL-003 |
| AC-B05-06 | REQ-CTRL-002 | Minimum phase margin of the stage loop over the loaded-plant range (N 0.2-2 N, θ 35-75°, 3 paper stacks, housing normal compliance 200-3000 N/m) | ≥ 40° | requirement | REQ-CTRL-002 | servo gains; DEC-011 |
| AC-B05-07 | REQ-CTRL-002 | Minimum gain margin of the stage loop over the same range | ≥ 6 dB | requirement | REQ-CTRL-002 | servo gains; DEC-011 |
| AC-B05-08 | REQ-MECH-004 | Axial stiffness k_ax (secant, preload knee to stop) | within 1-5 kN/m | requirement | REQ-MECH-004; prediction 1984 N/m (results/mechanics/flexure_calc.json) | DEC-006; axial suspension (DEC-007 rev.) |
| AC-B05-09 | REQ-MECH-004 | Axial force at which the overload stop engages | ≥ 1.4 N | requirement | REQ-MECH-004 (compliant range up to ≥ 1.4 N); prediction 1.45 N (config stage.axial_travel) | DEC-006 |
| AC-B05-10 | REQ-SNS-005 | Axial-force estimate noise (Hall z channel -> F_ax) over 0.1-2 N, bandwidth ≥ 500 Hz | ≤ 10 mN RMS | requirement | REQ-SNS-005 | force-sensing choice; contact detection |
| AC-B05-11 | REQ-SNS-005 | Axial-force calibration residual (CAL_AXIAL) against a reference load cell over 0.1-2 N | ≤ 10 mN RMS | derived | derived: matches the REQ-SNS-005 noise allowance (engineering judgement) | CAL_AXIAL (docs/icd.md s3) |
| AC-B05-12 | REQ-MECH-002 | Radius of the mechanical stop circle at the tip, 12 directions | within 0.65 mm ± 0.03 mm (requirement text) | requirement | REQ-MECH-002 text (0.65 mm). CONFLICT: design value 0.60 mm (config stage.travel_tip_mech v0.4.1, DEC-007 rev., REQ-MECH-002 current estimate); resolve before test; ±0.03 mm engineering judgement | resolve REQ-MECH-002 text; stop design |
| AC-B05-13 | REQ-MECH-002 | Peak flexure (gimbal blade) stress during stop impact at tip velocities up to 0.05 m/s, from blade strain and the beam model | ≤ 310 MPa | requirement | REQ-MECH-002 and REQ-MECH-006 peak allowable 310 MPa (AMF-18/19); impact velocity from results/electronics/drive_sense.json v_tip_stage_max | stop design (elastomer face); slew limit |
| AC-B05-14 | — | Contact chatter episodes (≥ 3 contact transitions within 20 ms) in 60 s of scripted writing on each paper stack, NEUTRAL and ASSIST_KF, contact feedforward disabled | = 0 | hypothesis | DEC-011 (simulated bounce at the ~180 Hz stage-against-paper mode, results/sim/ff_chatter.json); episode definition engineering judgement | DEC-011 revisit (bench servo tests with real paper stacks) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (14 rows for EXP-B05).
<!-- AC-TABLE:EXP-B05:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| m_eq > 12 g (expected: 13.7 g predicted) | REQ-MECH-003 is violated. Adopt the CFRP carrier option (~9.5 g, M-6) or revise the requirement with a servo analysis showing that 60 Hz is still reachable. |
| Position bandwidth < 60 Hz or margins below 40° / 6 dB in contact | The servo is re-designed (gains, notch at the paper mode) before EXP-B09. If the margins fail only on soft underlays, the declared contact range is narrowed. |
| Chatter with the feedforward disabled | The DEC-011 fix does not hold on real paper. Add an explicit paper-mode notch or lower the servo stiffness; re-run the Monte Carlo with the measured paper stiffness. |
| Stop stress > 310 MPa | Softer stop faces or a lower slew limit (`P-22` 0.08 m/s) before any human use. |
| k_ax or the stop force out of range | DEC-006 and the axial suspension design (DEC-007 rev.) are revised; the force re-zero procedure is updated. |

### Risks and controls

| Risk | Control |
|---|---|
| Injection destabilises the loop | Amplitude ramp; hardware current trip armed; first run on the rig module with commercial VCMs. |
| LDV speckle dropouts | Retro-reflective tape; check the signal level; drop low-coherence bins. |
| Destructive stop testing on the only pen | Stop-impact test on a sacrificial build first. |

---

## 7. EXP-B06: Grip impedance incl. normal direction; γ identification (participants)

### Purpose and what it gates

This experiment measures the mechanical impedance that a real writing grip presents to the pen, with the hand resting on paper and the forearm supported. The published values (HAP-26) were measured with the arm unsupported, in-plane only and without paper.

- **In-plane:** two page axes, 1–100 Hz.
- **Normal direction:** the "normal stiffness K_n the hand and pen present at the paper" of P-4. γ = K_n sin²θ / (K_n sin²θ + k_ax) is computed from it for the built axial path.
- **In-pen check** (Stage B): the firmware's γ identification is compared with this bench reference (REQ-CTRL-006: converges within 2 s).
- **Gates:** DEC-006 (revisit trigger "EXP-B06 hand normal compliance (γ)"), REQ-CTRL-006, the simulator's hand model (P-13 acceptance: model FRF within the 10–90 % band of measured subjects), and the feasibility of REQ-MECH-001 (AC-B04-04).
- It is part of research question rank 5.

Participants take part, so this study runs under the ethics approval of `human_study_plan.md` (§3 there: population, consent, risk). It is minimal risk: the vibration amplitude is ≤ 0.2 mm, the pen is unpowered or the Stage B pen passes gate G-S, and the forces are below 1 N.

### Hypotheses and predictions

- **H-B06-1.** The HAP-26 two-stage model with nominal parameters (k1 575 N/m, b1 1.3 N·s/m, M 0.21 kg, k2 170 N/m, b2 11 N·s/m; config `hand.*`) lies within the participants' 10–90 % band over 1–30 Hz (AC-B06-01).
- **H-B06-2.** K_n lies in 200–3000 N/m (the declared simulation range, an assumption) for ≥ 80 % of participants (AC-B06-02). With K_n = 800 N/m and k_ax = 2 kN/m, γ = 0.19 at 50° (COR-04).
- **H-B06-3.** The in-pen γ estimate is within ±0.05 of the bench value after 2 s (AC-B06-03). The accuracy follows from P-4: Δγ = 0.05 gives ≤ 8.3 % tilt-direction gain error for θ ≥ 35°.
- **H-B06-4.** γ changes by ≤ 0.05 across instructed grip levels (AC-B06-04). If it changes more, γ must be tracked continuously rather than once per session.

### Participants and sample size

- n = 12 healthy adults: 6 aged 18–59 and 6 aged ≥ 60. physics.md requires n ≥ 8.
- Precision: with between-participant CV ≈ 30 % (the HAP-26 k1 range; s of ln K_n ≈ 0.29), the 95 % CI of the mean ln K_n is ± t₀.₉₇₅,₁₁ · s/√12 = ±0.19, a factor of about 1.2 (±20 %). That is adequate to set the simulation ranges.
- Optional extension: the same protocol for 8 ET and 8 PD participants during their EXP-H01 visit, as an exploratory comparison.
- Inclusion and exclusion as in `human_study_plan.md` §3 (healthy-adult cohort).

### Equipment and setup

- Rig R6 (§0.9) and paper as in EXP-B01 on the force plate.
- For the in-pen part: the Stage B Rev A pen on the same platen, logging research frames.

### Procedure (per participant, about 60 min)

1. Consent; handedness; hand length; usual pen grip (photograph with the face excluded).
2. **Posture.** Forearm on a support, ulnar edge of the hand on paper, handle held in the usual grip. Altitude targets 45°, 55° and 65°, measured by the handle IMU. Visual feedback holds the normal force at 1.0 ± 0.2 N.
3. **In-plane excitation.** Shaker via stinger at the handle tail, along the page x and y axes in turn. Multisine 1–100 Hz; amplitude set so that handle displacement is 20–200 µm. It is above the 26 µm detection threshold at 10 Hz (HAP-27) and participants are told they will feel a vibration and should hold naturally. 3 × 60 s per axis.
4. **Normal excitation.** The vertical platen moves the paper ±50 µm, multisine 1–50 Hz, while the participant holds the handle on paper at 1 N. 3 × 60 s.
5. **Grip levels.** Repeat steps 3–4 at θ = 55° under instructed light, natural and firm grip, displayed from the handle's grip-force channel.
6. **In-pen γ (Stage B only).**
   - The same participant writes with the Rev A pen for 3 × 20 s on the feature course and one sentence.
   - The firmware γ estimate (research frames, `CAL_USER`) is logged.
   - The bench reference is γ from K_n (step 4, same θ) and k_ax (EXP-B05).

### Data format

HDF5 per participant with force, acceleration, displacement and platen motion at 5 kHz, conditions, grip-force channel and IMU angles. Pseudonymised participant id only (`records/README.md`).

### Analysis

1. H1 FRF estimates of dynamic stiffness F/x per axis; coherence ≥ 0.8 required per bin.
2. Fit P-13 (k1, b1, M, k2, b2) per axis per participant by complex least squares over 1–30 Hz (and 30–100 Hz reported separately).
3. Normal direction: K_n and b_n from a spring–damper fit over 1–10 Hz, corrected for paper compliance measured in EXP-B01 Part 1 (series spring).
4. γ(θ) per participant for k_ax = 2 kN/m and for the measured k_ax.
5. Population percentiles (10/50/90) of all parameters. These replace the `hand.*` ranges.

### Acceptance criteria

<!-- AC-TABLE:EXP-B06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B06-01 | — | Hand model P-13 with nominal config hand.* parameters: fraction of frequency points (1-30 Hz, each in-plane axis) where the model FRF magnitude lies within the 10-90 % band of measured participants | ≥ 80 % | hypothesis | docs/physics.md (model FRF within the 10-90 % band of measured subjects); 80 % engineering judgement | config hand.* (simulator hand model) |
| AC-B06-02 | REQ-CTRL-006 | Fraction of participants whose hand normal stiffness at the nib K_n (1-10 Hz fit, corrected for paper compliance) lies in 200-3000 N/m | ≥ 80 % | hypothesis | config hand.normal_stiffness range 200-3000 N/m (assumption; HAP-26 measured in-plane only) | DEC-006; γ range in simulation; REQ-MECH-001 feasibility (AC-B04-04) |
| AC-B06-03 | REQ-CTRL-006 | In-pen γ identification (Stage B pen, same participants): \|γ_pen - γ_bench\| after 2 s of writing, γ_bench from K_n (bench) and k_ax (EXP-B05) at the measured θ | ≤ 0.05 | derived | REQ-CTRL-006 (converges within 2 s); accuracy derived from P-4: dγ 0.05 gives ≤ 8.3 % tilt-direction gain error for θ ≥ 35° | REQ-CTRL-006; compliance-aware Jacobian |
| AC-B06-04 | REQ-CTRL-006 | Within-participant change of γ across instructed light / natural / firm grip at θ 55° | ≤ 0.05 | hypothesis | derived from the AC-B06-03 accuracy budget | γ identification design (continuous vs per session) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-B06).
<!-- AC-TABLE:EXP-B06:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| K_n mostly < 800 N/m (γ small) | The tilt-direction workspace shrinks further (AC-B04-04). Either a softer axial path (re-open DEC-006, trading EXP-B08 pressure modulation) or a larger stage radius is needed. |
| K_n mostly > 3000 N/m | γ approaches its large-K_n limit; the textbook Jacobian becomes nearly correct at high θ. The simulation ranges must widen. |
| γ varies > 0.05 with grip | The firmware must identify γ continuously, and the γ estimator's bandwidth becomes a design item (REQ-CTRL-006). |
| P-13 fails | Replace the hand model in the simulator (for example a three-stage model or grip-force-scheduled parameters, HAP-24/25) and re-run all sweeps before EXP-B09 predictions are frozen. |

### Risks and controls

| Risk | Control |
|---|---|
| Participant co-contraction changes the impedance | Instruct "hold as if writing"; monitor grip force; discard trials with grip force outside ±30 % of the natural level. |
| Shaker–handle resonances | Stinger designed with its first mode > 300 Hz; impedance head at the drive point. |
| Fatigue | Breaks every 10 min; session ≤ 60 min. |

---

## 8. EXP-B07: Coil and skin temperature

### Purpose and what it gates

This experiment measures coil hot-spot and touch-surface temperatures against copper loss (0.2–0.8 W, physics.md) on coupons (Stage A) and on built pens (Stages B, C), with a heated hand phantom, at 25 °C and 35 °C ambient.

- **Validates** thermal model P-18: steady rise within ±15 %, time constant within ±25 %.
- **Verifies** REQ-THM-001 (≤ 41 °C design target, 43 °C absolute at 25 °C ambient; ECMA-287 and IEC 60601-1 Table 24, AMF-34/35), REQ-THM-002 (coil ≤ 120 °C) and the allowable average copper loss behind REQ-ACT-002 (predicted 0.412 W for the moving coil).
- **Gates** G-S (no human use without a passing B07 on the same build) and DEC-008. It addresses open issues M-5 and E-8.

### Hypotheses and predictions

`results/thermal/thermal.json`, v0.4.4 (0.50 mm air gaps, 115 mW electronics), configuration B (moving coil):

| Case | Average coil loss | Coil | Grip | Actuator surface | Time to 41 °C at the surface |
|---|---|---|---|---|---|
| Design | 0.326 W | 96.6 °C | 33.4 °C | 34.1 °C | never |
| High | 1.045 W | runaway (far above the 120 °C limit) | 42.9 °C | 53.7 °C | 3.1 min |

- Allowable average copper loss: 0.412 W for the moving coil, set by the 120 °C coil limit; 1.192 W for fixed coils (B-MM).
- Two-node reduction for the firmware governor: coil to structure 145 K/W with 0.25 J/K (τ ≈ 36 s); structure to ambient 12.5 K/W with 14.9 J/K (τ ≈ 3 min).
- The firmware's coil-temperature estimate (research frame `t_coil`) tracks the measurement within ±5 K (AC-B07-07).

### Equipment and setup

- Rig R4 thermal instruments.
- **Hand phantom:** an aluminium or silicone sleeve held at 33 °C by a PID heater. It contacts the grip zone over 3 cm² (the basis of `thermal.json`: "finger contact 600 W/m²K × 3 cm², hand 33 °C").
- Climate chamber.
- Power analyser on each coil (V and I at ≥ 10 kS/s).
- IR camera for surface maps; thermocouples on the grip (0–40 mm), the bulge (45–57 mm) and the PCB area.

### Procedure

1. Pen horizontal on insulating supports in still air (chamber fan off), 25 °C.
   - DC copper-loss steps of 0.2, 0.33 (design average), 0.412 (predicted allowable), 0.6 and 0.8 W, shared equally between the axes.
   - Each step runs to steady state or to a limit: coil 110 °C, or any surface 43 °C. On a limit the step stops and the time to limit is recorded.
2. Repeat with the hand phantom on the grip.
3. Repeat at 35 °C ambient, where only 6–8 K of surface rise remains (AMF notes §2.4).
4. **Duty-cycle replay.** The current profile of the design-point writing script (65 % pen-down, results/trade `duty_down`) for 30 min, with the 2-s 1.4 N transient inserted every 5 min.
5. Record the firmware `t_coil` throughout.

### Sample size

- Coupons: 3 per variant.
- Pens: every built pen before any human use (G-S), which is a per-unit acceptance.
- Model validation uses ≥ 3 units.

### Data format

CSV at 1 Hz (temperatures, power) plus IR image sequences (radiometric, lossless); the firmware log in ICD format.

### Analysis

1. Steady-state rise per watt for the coil, grip and bulge; time constants by first- and second-order fits.
2. The allowable average copper loss = the largest loss meeting both 41 °C surface and 120 °C coil, interpolated with its uncertainty.
3. Firmware estimate error = t_coil − measured, over time.

### Acceptance criteria

<!-- AC-TABLE:EXP-B07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B07-01 | REQ-THM-001 | Maximum temperature of continuously held surfaces (grip 0-40 mm and actuator bulge) with a 33 °C hand phantom, 25 °C ambient, steady state at the design-point average copper loss (0.31 W) | ≤ 41 °C | requirement | REQ-THM-001 design target; design-point loss from results/thermal/thermal.json (config B design) | G-S (human use); thermal governor limits |
| AC-B07-02 | REQ-THM-001 | Maximum held-surface temperature during the 30-min duty-cycle replay including the 2-s 1.4 N transient every 5 min, 25 °C ambient | ≤ 43 °C | requirement | REQ-THM-001 absolute limit (ECMA-287 Table 5.2; IEC 60601-1 Table 24; AMF-34, AMF-35) | G-S |
| AC-B07-03 | REQ-THM-002 | Coil hot-spot temperature (resistance method and thermocouple) at the design-point load and after the 2-s high-load pulse | ≤ 120 °C | requirement | REQ-THM-002 | G-S; thermal governor |
| AC-B07-04 | — | Thermal model P-18: steady-state coil temperature rise per watt vs analysis/thermal.py for the as-built geometry | within prediction ± 15 % | hypothesis | docs/physics.md (steady rise within ±15 %) | thermal model validation; governor design |
| AC-B07-05 | — | Thermal model P-18: dominant coil time constant | within prediction ± 25 % | hypothesis | docs/physics.md (time constant within ±25 %) | thermal model validation |
| AC-B07-06 | REQ-ACT-002 | Allowable average copper loss: largest steady loss keeping held surfaces ≤ 41 °C and coil ≤ 120 °C at 25 °C ambient | ≥ 0.412 W | hypothesis | prediction results/thermal/thermal.json v0.4.4 (moving coil 0.412 W, set by the 120 °C coil limit with 0.50 mm air gaps; fixed coil 1.192 W) | DEC-008; thermal governor setting |
| AC-B07-07 | — | Firmware coil-temperature estimate (research frame t_coil) minus measured coil temperature, over the duty-cycle replay | within ± 5 K | derived | engineering judgement (governor must act before 120 °C with margin) | thermal governor (REQ-CTRL-004 limits) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-B07).
<!-- AC-TABLE:EXP-B07:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Allowable < 0.33 W (the predicted average copper loss at the design point, 65 % pen-down) | Rev A cannot sustain design-point writing. The thermal governor derates assistance (ICD fault bit 2 path), human sessions are time-limited, and DEC-008 (D/E) becomes necessary. |
| Surface > 41 °C at the design load | No human use of that build (G-S) until the governor limit is lowered and B07 is re-run. |
| Model outside ±15 % / ±25 % | Update `analysis/thermal.py` conductances and the simulator's `actuator.Rth_coil_amb`. |
| Firmware estimate error > 5 K | The governor uses a direct NTC reading instead (the coil NTC exists on the schematic). |

### Risks and controls

| Risk | Control |
|---|---|
| Thermocouples perturb the small thermal masses | 0.08 mm wire; sensor count limited; cross-check by coil resistance. |
| Emissivity errors in IR | Black tape reference spots; thermocouple cross-check. |
| Runaway at high load damages the coil | Automatic cut at 110 °C coil (resistance-based). |

---

## 9. EXP-B08: Ink tolerance to modulated normal force

### Purpose and what it gates

Tremor correction moves the nib against a stiff axial path, so the normal force is modulated at the tremor frequency (P-8).

- **Predicted modulation** under correction at the design point:
  - 0.09–0.12 N RMS for the oracle (`results/sim/nominal/metrics.json` v0.4.4);
  - Monte Carlo median 0.067 N and p90 0.135 N (`results/sim/sweeps/summary.json`).
- **The question:** does ink line quality (continuity, width, density, blobbing) tolerate 0.05–0.3 N RMS at 3–15 Hz on 0.3–2 N mean, across inks, papers and speeds?
- **Sets** the value of REQ-MECH-005 (≤ 0.15 N RMS, "subject to EXP-B08 ink-quality limit").
- **Gates** DEC-004 (D1 refill; revisit trigger "EXP-B08") and DEC-006 (stiff axial path).
- **Also checks** ink continuity at the 0.30 N constant nib force of configuration D (DEC-008).
- It is part of research question rank 5.

### Hypotheses

At ≤ 0.15 N RMS, 3–15 Hz, N_mean ≥ 0.5 N, the modulated lines are not worse than unmodulated controls by more than:

- 0.5 percentage points of gap fraction (AC-B08-01);
- 25 % relative line-width CV (AC-B08-02);
- and blinded observers cannot discriminate them above the 75 % 2AFC point (AC-B08-03).

These margins are engineering judgement. They will be replaced by the perception thresholds of EXP-H05 once available.

### Equipment and setup

- Rig R1 with the force-controlled voice-coil normal axis (mean plus sinusoid, closed-loop on the force plate; modulation accuracy ±5 % of setpoint RMS, verified per line).
- Rig R3 for scanning.
- Inks, papers and underlays as EXP-B01.

### Procedure

1. **Core grid** (nominal ink and paper, hard underlay):
   - N_mean ∈ {0.3, 0.5, 1.0, 2.0} N × modulation ∈ {0, 0.05, 0.10, 0.15, 0.20, 0.30} N RMS × f ∈ {3, 6, 9, 12, 15} Hz × v ∈ {10, 30} mm/s, at θ 50°.
   - 100 mm straight lines.
   - Control lines (modulation 0) are interleaved on every sheet.
2. **Extremes:** the 8 other ink × paper combinations and the two soft underlays at N_mean 1.0 N, f ∈ {6, 12} Hz, modulation ∈ {0, 0.15, 0.30} N, v = 30 mm/s.
3. **Configuration D check:** N_mean 0.30 N, modulation 0.05 N, f 9 Hz, all inks and papers.
4. Randomised order within each sheet; three different refills per condition (one per replicate).
5. **Observer test for AC-B08-03.**
   - Scans are printed at 1:1 at 1200 dpi on the same paper.
   - 10 observers (lab staff not involved in the experiment) judge 40 pairs each (modulated vs control, same refill), 2AFC: "which line is less even?".
   - The order is randomised and the prints coded.

### Sample size

- Core grid: 240 conditions × 3 replicates = 720 lines. Extremes: 10 combinations × 6 conditions × 3 replicates = 180 lines. Configuration D: 9 combinations × 3 replicates = 27 lines.
- For the equivalence-type bound on gap fraction, the upper 95 % confidence bound of the difference must be ≤ 0.5 percentage points.
- With 3 replicates × 100 mm per condition and a pooled model across frequencies, the SE of the difference in gap fraction is estimated at 0.1–0.2 percentage points for the gap rates seen in unmodulated lines (to be confirmed by a 20-line pilot). If the pilot SE exceeds 0.2 points, replicates increase to 6.

### Data format

16-bit TIFF scans per sheet with fiducials; a per-line record of the measured N(t) (1 kHz), speed and condition; the observer response file.

### Analysis

1. **Per line** (blind codes, §0.6):
   - gap fraction: the fraction of path length with no ink within ±w/2 of the expected centreline;
   - width w(s) (FWHM of the cross-profile every 50 µm), mean and CV;
   - mean optical density;
   - blob count (> 1.5 × median width over > 0.2 mm).
2. **Mixed model:** metric ~ modulation × frequency × N_mean + speed + (1 | refill) + (1 | sheet).
   - Differences from control with 95 % CIs.
   - The **tolerance limit** per (N_mean, f) is the largest modulation whose upper CI stays within all margins.
3. **Observers:** proportion correct with an exact binomial CI per condition, pooled across observers with a random effect.

### Acceptance criteria

<!-- AC-TABLE:EXP-B08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B08-01 | REQ-MECH-005 | Ink gap fraction increase vs unmodulated control (same refill, sheet, speed): upper 95 % confidence bound at 0.15 N RMS modulation, 3-15 Hz, N_mean ≥ 0.5 N | ≤ 0.5 percentage points | hypothesis | limit level from REQ-MECH-005 (0.15 N RMS); margin engineering judgement pending EXP-H05 | REQ-MECH-005 value; DEC-006; DEC-004 |
| AC-B08-02 | REQ-MECH-005 | Line-width coefficient-of-variation increase vs control: upper 95 % bound, same conditions | ≤ 25 % relative | hypothesis | margin engineering judgement pending EXP-H05 | REQ-MECH-005 value; DEC-004 |
| AC-B08-03 | REQ-MECH-005 | Blinded 2AFC discrimination (modulated at 0.15 N RMS vs control, 1:1 prints) by ≥ 10 observers: upper 95 % bound of proportion correct | ≤ 75 % | hypothesis | 2AFC threshold convention (75 % point), as EXP-H05 | REQ-MECH-005 value |
| AC-B08-04 | REQ-MECH-005 | Ink tolerance limit (largest modulation meeting AC-B08-01...03) at N_mean 1 N, 9 Hz | ≥ 0.14 N RMS | derived | derived: predicted modulation under correction up to 0.135 N (Monte Carlo p90, oracle, results/sim/sweeps/summary.json) and 0.118 N (oracle 9 Hz, results/sim/nominal/metrics.json) | DEC-006 (stiff axial path); limiter force-modulation budget |
| AC-B08-05 | — | Ink gap fraction at N_mean 0.30 N with 0.05 N RMS modulation at 9 Hz, every ink and paper | ≤ 1 % | hypothesis | configuration D constant nib force 0.30 N (results/thermal/thermal.json case D); 1 % engineering judgement | DEC-008 (configuration D) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-B08).
<!-- AC-TABLE:EXP-B08:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Tolerance limit ≥ 0.15 N | REQ-MECH-005 stands; DEC-006 (stiff axial path) stands. |
| Tolerance limit between the predicted modulation (≤ 0.14 N) and 0.15 N | REQ-MECH-005 is lowered to the measured limit. The limiter gets a force-modulation budget: authority is reduced when the measured 3–15 Hz N_mod approaches the limit. |
| Tolerance limit < 0.14 N | Correction at the design point degrades ink. Re-open DEC-006 (softer axial path, trading device distortion, `results/sim/design_sweeps.json`) and DEC-004 (another refill or ink type). |
| Gaps at 0.30 N (configuration D) | The configuration-D constant nib force must rise (and its power with the square), or D is dropped (DEC-008). |

### Risks and controls

| Risk | Control |
|---|---|
| Force controller does not deliver the requested modulation into paper | Measure N(t) per line and analyse on measured, not commanded, modulation. |
| Scanner non-uniformity masquerades as density modulation | Flat-field correction; controls on the same sheet. |
| Ink drying time and skip at line start | Exclude the first 5 mm; pre-write 20 mm on scrap paper before each sheet. |

---

## 10. EXP-B09: Bench cancellation with injected housing disturbance and µm ink metrology

### Purpose and what it gates

This is the decisive bench experiment (REQ-VAL-001). The pen writes with real ink on real paper along a known reference path, while a housing disturbance is injected through a hand simulant. The housing, the nib and the deposited ink are each measured by independent metrology. Cancellation modes are compared with powered-neutral, unpowered and rigid on the same disturbance realisation.

It is research question rank 4: "does loaded cancellation improve deposited ink at practical force within the power and heat budget?" The ACT review found **no published evidence on actuated nibs in contact** (ACT notes §2).

It runs twice:

- **B09-rig (Stage A):** the rig module with commercial VCMs through the same lever (`mechanics/README.md`). It gates **G-B**, the start of the Rev A pen build and use. This implements COR-23's "gate G-B".
- **B09-pen (Stage B):** the tethered Rev A pen on the same rig. It gates **G-C**. `docs/research_questions.md` calls this the "Phase B → C gate".

**Models validated:** control P-19…P-24 (measured residual ratio within ±0.1 of simulation for the same disturbance), and end to end P-4, P-5…P-9 and P-13 as implemented.

**Requirements verified:** REQ-VAL-001, REQ-CTRL-003, -005, -006, -007 and -008, and REQ-MECH-005 (in use).

**Decisions informed:** DEC-009 (frequency gate) and the guided-mode role, DEC-003 and DEC-008 (loads and power in use).

### Modes compared (firmware modes, `docs/icd.md` §6)

| Label | Mode | Purpose |
|---|---|---|
| RIGID | Stage mechanically locked by a pin (ordinary-pen equivalent) | Reference for device distortion (M-dev) |
| UNPOWERED | Coils open, stage free | Documents COR-19: the contact load drives the nib toward the stop |
| NEUTRAL | NEUTRAL_HOLD (powered, q_r = 0) | Reference for the residual ratio (M-ratio) |
| KF-BAL / KF-ASR | ASSIST_KF with the frozen balanced / assertive parameters (`results/sim/estimator_selection.json`) | Causal cancellation with the frequency gate |
| ORACLE | Correction = −(true injected housing disturbance) from rig metrology, zero sensing delay (test build) | The mechanical bound: what the stage can do with perfect knowledge |
| GUIDED | GUIDED with the registered template (capture radius 2·q_lim = 1.1 mm, `sim/pensim/core.py` mode 6) | Known-path assistance (DEC-009 below the gate) |
| DELAY-PROBE | Estimator bypassed, g = 1, correction = −(the pen's own measured housing disturbance) | Measures the effective sensing + servo delay (REQ-CTRL-003) |

### Hypotheses and predictions

Predictions are regenerated with the identified rig parameters before the test (§0.2). The current values, v0.4.4, at θ 50°, N 1 N, 0.3 mm peak, test seeds 200–203 (`results/sim/nominal/metrics.json`), and the grid over 12 seeds (`results/sim/sweeps/summary.json`, `grid.csv`):

| Quantity | 6 Hz | 9 Hz | Grid at 0.3 mm over 4–12 Hz | Grid, all amplitudes |
|---|---|---|---|---|
| ORACLE ratio | 0.18 | 0.23 | 0.15–0.31 | 0.22–0.32 |
| KF ratio (KF-BAL = KF-ASR since v0.4.2) | 1.01 | 0.71 | 0.63–1.10 | 0.85–1.14 |
| Band-pass ratio (reference estimator) | 1.14 | 0.56 | 0.57–1.36 | 0.75–1.49 |
| N_mod (ORACLE) | 0.09 N | 0.12 N | — | MC p90 0.135 N |

**The two ASSIST_KF profiles are the same set since v0.4.2.** The tuning objective that chose the inert set for KF-BAL in v0.4.1 now chooses the active set that KF-ASR already used (`docs/sim_report.md` §3.2). Both profiles stay in the test matrix, because the rig-identified plant may flip the selection again. The frozen prediction file records which set each profile carries.

Further predictions:

- **Distortion (no tremor):** KF 55 µm (nominal, 4 seeds) / 100 µm (grid, 12 seeds).
- **Device distortion:** 60–75 µm per seed.
- **Feature course (KF, no tremor):** dot max 81 µm; corner max 208 µm; hatch 96 µm RMS; fast stroke 5 µm RMS.
- **Gate behaviour** (`results/sim/gate_fraction.json`, AC-B09-15). Fraction of contact time with g ≥ 0.5:
  - 0.94 / 0.94 with 9 / 10 Hz tremor;
  - 0.12 with 6 Hz tremor (below the gate);
  - 0.14 on tremor-free handwriting (0–0.29 per seed) and 0.68 on the feature course.
  - The tracker locks onto strokes, so the gate opens on writing. That is the source of the distortion above and the reason for DEC-009's next revision.
  - The v0.4.1 inert set, simulated on the same plant, opens its gate less with tremor (0.21–0.31) than without (0.51).
  - If the revision (a separate spectral detector with hysteresis) exists before this test, it is added as a further ASSIST_KF profile and assessed with the same criteria.
- **GUIDED path distance vs NEUTRAL** (6 Hz, `results/sim/guided_path_distance.json`): circle 163 vs 443 µm; spiral 112 vs 382 µm; fast stroke 37 vs 115 µm.
  - In the time-aligned metric, GUIDED looks *worse* than NEUTRAL (feature course "ALL" 443 vs 219 µm, `metrics.json`).
  - This is because a user-paced template follower shifts along the track. M-path, not M-e, is therefore the primary metric for GUIDED.

The hypotheses tested:

- **H-B09-1.** With perfect disturbance knowledge, the loaded stage achieves ≥ 6 dB (ORACLE ratio ≤ 0.5) at 6–10 Hz at practical force (AC-B09-02).
- **H-B09-2.** The simulator, re-parameterised to the rig, predicts the ORACLE and KF ratios within ±0.1 (AC-B09-03).
- **H-B09-3.** Above the gate, KF-ASR helps (≤ 0.8 at 9–10 Hz, AC-B09-04). Below the gate, no mode does harm (≤ 1.05, AC-B09-05).
- **H-B09-4.** Intent is preserved within REQ-CTRL-005 (AC-B09-06, -07). Deliberate high-frequency features (hatch, fast strokes) are distorted by ≤ 100 µm RMS (AC-B09-08; expected to fail for fast strokes).
- **H-B09-5.** N_mod ≤ 0.15 N (AC-B09-09). The effective delay is ≤ 5 ms (AC-B09-10). Guided mode releases authority outside its capture radius within 150 ms (AC-B09-11) and halves the path distance on circles and spirals (AC-B09-12). γ is identified within ±0.05 in 2 s (AC-B09-13).
- **H-B09-6.** The frequency gate opens for tremor above it (authority ≥ 0.5 for ≥ 90 % of ticks at 9–10 Hz) and stays shut on tremor-free writing (≤ 5 % of ticks) (AC-B09-15). This is predicted to fail for KF-BAL, whose gate stays closed with tremor present.

### Equipment and setup

- Rig R2, with the hand simulant set to the EXP-B06 median parameters, and to the 10th and 90th percentiles as sensitivity cases. The simulant's normal spring sets the γ reference.
- Rig R3 for scans. Rig R7 for electronics timing.
- Paper: ISO 12757-1 test paper on a 50-sheet pad (nominal), plus the hard-underlay case. The nominal ink is the oil-based D1.
- Reference paths:
  - the feature course (`stabpen/signals.py::feature_course`, scale 1);
  - three sigma-lognormal handwriting samples (3–4 mm letters, from the simulator's generator with fixed seeds);
  - the Archimedes spiral (3 turns, r to 5 mm).
  All are executed by the robot as intended hand-reference paths.
- Disturbances:
  - synthetic tremor with frequency and amplitude modulation (`stabpen.signals.TremorSpec` defaults: f jitter 0.3 Hz, AM depth 0.3, 2nd harmonic 0.15, ellipticity 0.4), at the frequencies and amplitudes of the matrix;
  - recorded tremor from EXP-H01 (in EXP-E02).

### Test matrix

| Factor | Primary cells | Secondary cells |
|---|---|---|
| f0 (Hz) | 6, 9 | 4, 5, 7, 8, 10, 12 |
| Amplitude (mm peak) | 0.3 | 0.15, 0.6 |
| θ | 50° | 45°, 65°; 35° as characterisation only (COR-26) |
| N (N) | 1.0 | 0.5, 1.5 |
| Path | handwriting A, feature course | handwriting B, C; spiral |
| Modes | all | NEUTRAL, ORACLE, KF-ASR |

- Every run with a disturbance has a paired run without it (same path, same mode) for M-dist and the clean reference.
- Each disturbance realisation (seed) is run in every mode as a block, so mode contrasts are paired.

### Procedure

1. **Qualification.**
   - Verify the simulant FRF (±10 % of target).
   - Verify the metrology chain: time-aligned nib trajectory against the scanned ink centreline on 10 NEUTRAL runs (AC-B09-14).
   - Verify synchronisation (§0.4).
   - Confirm that EXP-F01's core safety items passed on the rig electronics.
2. **Per session:**
   - Fresh paper sheet with fiducials; blank scan.
   - Registration: the robot writes 4 registration dots at known positions in RIGID mode.
3. **Per block** (one disturbance seed): run the modes in randomised order. Each run has a 1 s approach, the path, and a 0.5 s lift. Log research frames, rig metrology, force plate and coil currents and temperatures.
4. **Delay probe:** 10 runs of 20 s with sinusoidal disturbance steps at 3, 5, 8 and 12 Hz, housing-only motion, no writing path.
5. **γ identification:** 5 runs per simulant K_n setting (200, 800, 3000 N/m) at θ 50°.
6. **Guided release:** the robot deliberately leaves the template by 2 mm at 5 mm/s during a guided trace. 10 repeats.
7. Scan every sheet within 1 h of writing (R3).

### Sample size

- **Primary cells:** 10 disturbance seeds × every mode.
- From simulation, the between-seed SD of the ratio is 0.03–0.05 (`metrics.json` `ratio_sd`). The bench SD is assumed ≤ 0.08 until the pilot.
- With n = 10 the 95 % CI half-width of a mean ratio is t₀.₉₇₅,₉ · 0.08/√10 = 0.057. That resolves the ±0.1 agreement band and the 0.5 gate.
- If the pilot SD exceeds 0.08, n is raised so that the half-width stays ≤ 0.06: n = (2.26 · s/0.06)².
- **Secondary cells:** 3 seeds.
- **Distortion runs:** 10 per estimator on handwriting and 10 on the feature course.

### Data format

- Per run: the ICD research-frame log, rig HDF5 (robot, disturbance stage, housing lasers, nib LDV, force plate at 10 kHz, sync), and the scan crop with the registration transform.
- A run table (CSV) has one row per run: mode, seed, path, f0, amplitude, θ, N, block id, sheet id.

### Analysis

1. **Registration.** Ink scans are mapped to the robot frame by the registration dots (similarity transform). The residual must be ≤ 10 µm RMS, or the sheet is re-registered with fiducials.
2. **Time-aligned metrics** (M-e, M-rms, M-band, M-ratio, M-dist, M-dev, M-Nmod, M-Pcu) from the independent nib trajectory, exactly as `sim/pensim/evaluate.py`: same mask, same filters.
3. **Ink metrics** (M-path, M-feat) from scans, with blind coding.
4. **Mode contrasts.** A linear mixed model on log ratio: mode + f0 + (1 | seed) + (1 | sheet). Report the ratio per cell with 95 % CI.
5. **Simulation agreement.** For each primary cell, the difference between the measured ratio and the regenerated prediction, with its CI.
6. **Delay.** τ_eq(f) from cross-spectra between the injected housing disturbance and the nib correction (DELAY-PROBE), averaged over 3–12 Hz, and the maximum.
7. **γ.** The logged γ estimate at 2 s against the simulant's γ computed from its K_n and k_ax.
8. **Energy.** M-Pcu per mode, and the coil temperature rise.
9. **Gate behaviour.** From the research-frame fields g and f_est (`docs/icd.md` §4.2), inside the evaluation mask: the fraction of ticks with g ≥ 0.5, per profile and condition, and the f_est trace against the injected frequency.

### Acceptance criteria

<!-- AC-TABLE:EXP-B09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B09-01 | REQ-VAL-001 | Protocol conformity: real ink on paper, known reference path, injected housing disturbance, independent metrology of housing, nib and deposited ink, and CANCEL vs NEUTRAL vs UNPOWERED (plus RIGID) all run on the same disturbance realisations | all elements present | requirement | REQ-VAL-001 | G-B; G-C |
| AC-B09-02 | — | ORACLE residual ratio (M-ratio, time-aligned ink error vs NEUTRAL) at 0.3 mm peak disturbance, 6, 8 and 10 Hz, θ 50°, N 1.0 N, nominal paper; mean over 10 seeds per cell | ≤ 0.5 | hypothesis | ≥ 6 dB acceptance (docs/research/notes/ACT_active_stabilisation.md, decisive experiment 1); prediction 0.18 (6 Hz), 0.23 (9 Hz) (results/sim/nominal/metrics.json v0.4.4) | G-B (loaded cancellation at practical force); DEC-003 |
| AC-B09-03 | — | Simulation agreement: \|measured - predicted\| residual ratio for ORACLE, KF-ASR and KF-BAL at the primary cells, simulator re-parameterised to the identified rig (EXP-B01, B02, B05, B06) | ≤ 0.1 | hypothesis | docs/physics.md model-validation table (control P-19...P-24: within ±0.1 of simulation) | model validation; basis of DEC-009 and DEC-016 |
| AC-B09-04 | REQ-CTRL-007 | KF-ASR residual ratio at 9 and 10 Hz (0.3 mm peak, θ 50°, N 1 N) | ≤ 0.8 | hypothesis | prediction 0.71 at 9 Hz (nominal, v0.4.4); grid at 0.3 mm 0.78 / 0.71 at 9 / 10 Hz (all-amplitude mean 1.03 / 0.97; results/sim/sweeps/grid.csv, summary.json) -> expected marginal PASS; 0.8 engineering judgement | DEC-009 (value of cancellation above the gate); REQ-CTRL-007 |
| AC-B09-05 | REQ-CTRL-007 | KF-BAL and KF-ASR residual ratios at 4-7 Hz (below the 7.5 Hz gate) | ≤ 1.05 | hypothesis | no-harm criterion for the frequency gate (DEC-009; band-pass 1.14 at 6 Hz in simulation); 5 % engineering judgement; prediction (grid, 0.3 mm, v0.4.4) Kalman 1.10 / 1.06 / 1.02 / 0.99 at 4 / 5 / 6 / 7 Hz -> expected FAIL at 4-5 Hz | DEC-009 gate design |
| AC-B09-06 | REQ-CTRL-005 | Intent distortion (M-dist): RMS ink difference KF-BAL vs NEUTRAL on the handwriting paths without disturbance | ≤ 50 µm | requirement | REQ-CTRL-005; prediction 55 µm (nominal, 4 seeds) / 100 µm (grid, 12 seeds), v0.4.4, where KF-BAL and KF-ASR are the same set (docs/sim_report.md s3.2) -> expected FAIL | estimator tuning (DEC-009); REQ-CTRL-005 |
| AC-B09-07 | REQ-CTRL-005 | Maximum corner and dot position error on the feature course without disturbance, KF-BAL vs NEUTRAL | ≤ 100 µm | requirement | REQ-CTRL-005; prediction dot max 81 µm, corner max 208 µm (results/sim/nominal/metrics.json features, v0.4.4) -> expected FAIL at corners | estimator tuning |
| AC-B09-08 | REQ-CTRL-005 | RMS distortion of hatch (4 Hz) and fast-stroke features on the feature course without disturbance, KF-BAL vs NEUTRAL | ≤ 100 µm | hypothesis | engineering judgement extending the REQ-CTRL-005 corner/dot limit to deliberate high-frequency features (not bounded by REQ-CTRL-005); prediction hatch 96 µm, fast stroke 5 µm RMS (v0.4.4) -> expected marginal PASS (hatch) | REQ-CTRL-005 scope; estimator tuning |
| AC-B09-09 | REQ-MECH-005 | Normal-force modulation M-Nmod (3-15 Hz RMS at the force plate) during ORACLE and KF-ASR at the design point | ≤ 0.15 N | requirement | REQ-MECH-005; prediction 0.09-0.12 N (oracle), 0.11 N (KF-ASR 9 Hz), results/sim/nominal/metrics.json | DEC-006 |
| AC-B09-10 | REQ-CTRL-003 | Effective delay tau_eq from housing disturbance to nib correction, maximum over 3-12 Hz, DELAY-PROBE mode | ≤ 5 ms | requirement | REQ-CTRL-003 | sensing and servo architecture; prediction horizon |
| AC-B09-11 | REQ-CTRL-008 | Guided mode: authority after the housing leaves the capture radius (2 q_lim = 1.1 mm, sim/pensim/core.py mode 6; firmware/core/guided.c) | ≤ 0.05 within 150 ms | derived | derived: 3 x authority_tau (0.05 s, sim/pensim/model.py) for a first-order release | guided-mode release behaviour |
| AC-B09-12 | — | GUIDED path distance (M-path, as sim/guided_eval.py) on circle and spiral features with 6 Hz, 0.3 mm disturbance, relative to NEUTRAL | ≤ 0.5 | hypothesis | prediction 0.37 (circle 163/443 µm) and 0.29 (spiral 112/382 µm), results/sim/guided_path_distance.json v0.4.4; 0.5 engineering judgement (≥ 6 dB, as AC-B09-02) | DEC-009 (guided mode below the gate); EXP-H06 variant choice |
| AC-B09-13 | REQ-CTRL-006 | Gamma identification on the rig with a calibrated simulant normal spring (200/800/3000 N/m): \|γ_id - γ_true\| after 2 s of writing | ≤ 0.05 | derived | REQ-CTRL-006 (2 s); accuracy as AC-B06-03 (P-4 derivation) | REQ-CTRL-006 |
| AC-B09-14 | — | Metrology qualification: RMS difference between the time-aligned nib trajectory (rig metrology, in contact) and the scanned ink centreline for the same NEUTRAL run | ≤ 7 µm | derived | derived: TUR ≥ 4 against the ±0.1 ratio band at a NEUTRAL error of about 290 µm (results/sim/nominal/metrics.json, 6 Hz) | validity of EXP-B09 verdicts |
| AC-B09-15 | REQ-CTRL-007 | Frequency-gate behaviour of each ASSIST_KF profile, from the research-frame fields g and f_est (docs/icd.md s4.2): fraction of evaluation ticks with authority g ≥ 0.5, (a) with 9-10 Hz, 0.3 mm tremor on handwriting paths and (b) on tremor-free handwriting and the feature course | ≥ 0.9 (a) / ≤ 0.05 (b) | hypothesis | engineering judgement; prediction results/sim/gate_fraction.json (v0.4.4, seeds 200-203): selected Kalman set 0.94 / 0.94 at 9 / 10 Hz -> (a) marginal PASS; open on 0.14 of tremor-free handwriting and 0.68 of the feature course -> (b) expected FAIL. The v0.4.1 balanced (inert) set: 0.31 / 0.21 (a FAIL) and 0.51 / 0.74 (b FAIL). docs/sim_report.md s3.2 | DEC-009 revision (separate spectral detector with hysteresis); choice of ASSIST_KF profile for EXP-H06 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (15 rows for EXP-B09).
<!-- AC-TABLE:EXP-B09:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| ORACLE ratio > 0.5 (AC-B09-02 fails) | The loaded mechanics cannot cancel even with perfect knowledge (stick-slip, contact dynamics, servo). **G-B fails.** No Rev A build for cancellation research until the cause is found: contact model (B02), servo (B05) or hand coupling. DEC-003 is re-opened. |
| Simulation agreement fails (> 0.1) | Simulation-based decisions (DEC-009 gate, DEC-016 ML comparison, estimator tuning) lose their basis until the model is corrected. EXP-E01 conclusions must then rest on EXP-E02 closed-loop data. |
| KF above the gate > 0.8 with ORACLE ≤ 0.5 | Estimation, not mechanics, limits benefit (as COR-11 predicts). Free-writing cancellation is not a product claim. Guided and training modes carry the value; H06 uses its guided variant (`human_study_plan.md`). |
| Gate open < 90 % of ticks with tremor above it, or > 5 % on tremor-free writing (AC-B09-15; predicted for KF-BAL) | The gate cannot be driven by the estimator's own tracker. DEC-009's next revision (a separate spectral detector with hysteresis, `docs/sim_report.md` §3.2) is implemented and this test repeated for it. EXP-H06-F does not use a profile that fails (a): its ON condition would equal NEUTRAL by construction. |
| Any mode > 1.05 below the gate | The frequency gate leaks. DEC-009 is revised (hysteretic, confidence-weighted gate; `docs/sim_report.md`) before any human use of ASSIST_KF. |
| Distortion > 50 µm, or corner/dot > 100 µm | Estimator re-tuning toward the balanced end; REQ-CTRL-005 remains a hard limit for release. |
| Fast-stroke/hatch distortion > 100 µm (expected) | REQ-CTRL-005 is incomplete. It needs a feature-specific limit set by EXP-H05 perception thresholds. |
| N_mod > 0.15 N or above the EXP-B08 tolerance limit | Authority is limited by a force-modulation budget; DEC-006 is re-opened. |
| GUIDED path-distance ratio ≤ 0.5 on circles and spirals | Supports DEC-009's use of guided mode below the gate; H06 guided variant is feasible. |
| Effective delay > 5 ms | The sensing chain (EXP-S01) or the servo misses REQ-CTRL-003; the prediction horizon grows, which costs distortion. |

### Risks and controls

| Risk | Control |
|---|---|
| Hand simulant differs from humans | Three simulant settings (B06 percentiles); human confirmation is EXP-H06, not this experiment. |
| ORACLE uses rig metrology the pen will never have | Labelled a bound, never a performance claim. |
| Paper and ink variability larger than the effects | Paired blocks on the same sheet where possible; paper batch fixed per session; sheet as a random effect. |
| Heating of coils across a long session | Coil temperature logged; runs rejected when the coil is > 80 °C at start; cooling pauses. |
| Unblinding of the ink analysis | Codes; automatic pipeline frozen before unblinding. |
| UNPOWERED runs drive the nib into the stop repeatedly (COR-19) | Limit to 10 runs per build; inspect the stops afterwards (EXP-B10 drop-test criteria re-checked). |

---

## 11. EXP-B10: Durability (flexure cycling, refill exchange, drop)

### Purpose and what it gates

This experiment checks that a built stage keeps its calibration and function through:

- (a) tremor-like cycling for a year-equivalent of use;
- (b) repeated refill exchange (REQ-MECH-008);
- (c) drops (REQ-MECH-002: stops limit flexure stress at impact);
- (d) coil-lead flexing (M-4);
- (e) axial-suspension overload cycles.

It complements EXP-M02 (coupon fatigue to 10⁸ cycles) and gates G-C (untethered pens given to participants).

### Hypotheses

- **Cycling.** After 1.05 × 10⁷ cycles at ±0.30 mm tip amplitude (≈ one year of 1 h/day at 8 Hz: 28 800 cycles/h × 365 h), k_tip changes by ≤ 10 % and the neutral position drifts by ≤ 20 µm (AC-B10-01, -02). Engineering judgement, aligned with REQ-MECH-008's 20 µm.
- **Refill exchange.** The neutral offset is repeatable to ≤ 20 µm (REQ-MECH-008) over 29/29 exchanges (success run R 0.90, C 0.95), or recalibration takes < 30 s (AC-B10-03, -04).
- **Drop.** 12 drops from 1.0 m onto hardwood (6 orientations × 2, including nib-down) leave the stop radius within ±0.03 mm, k_tip within ±10 %, the Hall calibration within AC-B04-01, and no electrical fault (AC-B10-05). The height is engineering judgement (desk height plus hand height); the method follows IEC 60068-2-31 free fall.

### Equipment and setup

- Rig R8 (cycling at 30 Hz with the pen's own actuator, amplitude closed-loop on the Hall sensor with a periodic R5 check).
- Rig R5 for re-calibration.
- A drop fixture: release jig, hardwood block on concrete, high-speed camera.

### Procedure

1. Baseline: EXP-B04 (hold-out residual), EXP-B05 static k_tip, stop radius, axial k_ax and preload.
2. **Cycling.** 1.05 × 10⁷ cycles at ±0.30 mm (tip), 30 Hz, alternating axes, with 10⁵ cycles at ±0.55 mm (q_lim) spread through the run.
   - Coil temperature is kept < 80 °C by duty cycling.
   - Re-measure k_tip and the neutral offset every 2 × 10⁶ cycles.
3. **Axial.** 10⁶ pen-down cycles to the overload stop (1.45 N) at 5 Hz; re-measure k_ax and preload (AC-B10-07).
4. **Refill exchange.** 29 consecutive tool-free exchanges by 3 operators (10, 10 and 9) with refills from 3 lots. After each exchange, measure the neutral tip offset against the independent metrology and time the user recalibration routine.
5. **Lead flex.** Moving-coil leads through the full stroke for 10⁷ cycles (this can run within item 2 with full-stroke excursions, or on a lead-only fixture); 4-wire resistance every 10⁶ cycles (AC-B10-06).
6. **Drop.** 12 drops, then the full re-check of item 1 plus the F01 electrical self-test.

### Sample size

- Three pens per build for cycling and drop (destructive for the pen's calibration; not reused for human studies without re-qualification).
- Refill exchange: n = 29 zero-failure success run.

### Data format

Per pen: a baseline and re-check table, cycle counters, resistance log, exchange table, drop video.

### Analysis

Changes against baseline with measurement uncertainty; a pass requires |change| + U ≤ limit (guarded, because the result gates participant use).

### Acceptance criteria

<!-- AC-TABLE:EXP-B10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B10-01 | REQ-MECH-006 | Change in transverse tip stiffness k_tip after 1.05e7 cycles at ±0.30 mm tip amplitude plus 1e5 cycles at ±0.55 mm | ≤ 10 % | hypothesis | engineering judgement; cycle count = one year of 1 h/day at 8 Hz (28 800 cycles/h x 365 h); 1e8-cycle basis of REQ-MECH-006 verified on coupons in EXP-M02 | flexure design release; G-C |
| AC-B10-02 | REQ-MECH-006 | Drift of the stage neutral position (Hall zero vs independent metrology) after the same cycling | ≤ 20 µm | hypothesis | engineering judgement aligned with the REQ-MECH-008 offset limit (20 µm) | recalibration interval |
| AC-B10-03 | REQ-MECH-008 | Change of the neutral tip offset after tool-free refill removal and re-insertion, 29 consecutive exchanges by 3 operators with refills from 3 lots | ≤ 20 µm in 29/29 | requirement | REQ-MECH-008; n = 29 is the zero-failure success run for R 0.90 at C 0.95 | refill seat design (DEC-004) |
| AC-B10-04 | REQ-MECH-008 | Duration of the user recalibration routine after refill exchange (applies if AC-B10-03 fails) | < 30 s | requirement | REQ-MECH-008 | refill seat / calibration UX |
| AC-B10-05 | REQ-MECH-002 | After 12 drops from 1.0 m onto hardwood (6 orientations x 2, incl. nib-down): stop radius change, k_tip change, Hall calibration residual (AC-B04-01 re-run) and electrical self-test | stop radius ±0.03 mm; k_tip ±10 %; AC-B04-01 met; no fault | hypothesis | REQ-MECH-002 (stops protect flexures at impact); drop height and orientations engineering judgement (IEC 60068-2-31 free-fall method) | stop design; G-C |
| AC-B10-06 | — | Moving-coil lead resistance change after 1e7 cycles at full lever travel | ≤ 1 % | hypothesis | mechanics/README.md open issue M-4 (1e7 tremor cycles); 1 % engineering judgement | lead routing (M-4) |
| AC-B10-07 | REQ-MECH-004 | Change of axial stiffness k_ax and preload after 1e6 pen-down cycles to the overload stop (1.45 N) | ≤ 10 % | hypothesis | engineering judgement | axial suspension design (DEC-007 rev.) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-B10).
<!-- AC-TABLE:EXP-B10:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Stiffness or neutral drift after cycling | Recalibration interval, or a flexure redesign (thinner blades, lower stress, M02 data). |
| Refill exchange > 20 µm and recalibration > 30 s | Kinematic seat redesign (REQ-MECH-008; DEC-004). |
| Drop failures | Stop design and nib-down protection (a retracting cap) before G-C. |
| Lead resistance drift | Lead routing redesign (M-4). |

### Risks and controls

| Risk | Control |
|---|---|
| Accelerated cycling at 30 Hz is not equivalent to 8 Hz | Fatigue of metals at these frequencies depends on cycle count, not rate, but thermal and wear effects may differ; the coupon data (M02) and the coil temperature limit cover this. |
| Pens used for durability later given to participants | Forbidden unless fully re-qualified (B04, B05, B07, F01). |
---

## 12. EXP-S01: Optical-sensor latency and accuracy

### Purpose and what it gates

This experiment selects and characterises the near-nib optical motion sensor that page-referenced correction depends on (DEC-005; revisit trigger "EXP-S01").

- **Requirements:** REQ-SNS-001 (≥ 1 kHz, ≤ 3 ms total latency, ≤ 5 µm RMS per sample on matte paper at 35–75°) and REQ-SNS-002 (a valid view at any roll).
- **Other items:** part of REQ-CTRL-003 (the sensing part of the ≤ 5 ms delay budget), research question rank 6, open issue E-7 (module selection sets the nose-flex interface), and the simulator's `sensing.opt_delay` (2 ms nominal, "measure with LED-strobe method").
- **Evidence so far:** DeltaPen reports 1 kHz and a translation error of 68 µm mean / 24 µm median per 10 ms window, on a Wacom surface, not paper, with no latency figure (OPT-01/02). The P3040 datasheet is under NDA (OPT-06).

### Hypotheses

- At least one candidate meets REQ-SNS-001 on matte paper at 35–75° (AC-S01-01…03).
- With 3 modules at 120°, ≥ 99 % of samples at any roll have a valid module (AC-S01-04).
- Per-window error on paper is no worse than DeltaPen's median on a tablet (AC-S01-06).
- Nib motion and fresh ink in the field of view raise noise by ≤ 10 % (AC-S01-07).

### Candidates

- PixArt P3040-class lens-less sensors (if PixArt supplies them; OPT-06).
- PMW3360/3389-class sensors with custom short-Z optics (OPT-03/04; Flashpen route).
- PAA5100JE-class sensors at 15–35 mm as a barrel-mount option (OPT-05).
- Reference channel: a PMW3360 at its nominal 2.4 mm Z (OPT-04).

### Equipment and setup

- Rig R5: XY stage carrying the paper, goniometer and rotary stages for θ and ρ, piezo step stage.
- **Strobe illuminator:** an LED at the module's wavelength, driven with 10–50 µs pulses with timing known to ≤ 1 µs, while the module's own LED is masked.
- Logic analyser recording the SPI bursts, motion-interrupt lines, the strobe drive, the stage encoder and the firmware GPIO "estimate ready" marker on one clock.
- Paper types:
  - matte copy (ISO 12757-1 test paper);
  - recycled;
  - glossy coated;
  - lined notebook;
  - a printed text page;
  - coded-dot paper (Ncode/Anoto);
  - fresh-ink regions written just before tracking.

### Procedure

1. **Strobe latency (sensor pipeline).**
   - The paper moves at a constant 20 mm/s with the module LED masked.
   - Strobe pairs one frame interval apart illuminate the surface at known instants, so that exactly one frame pair carries texture.
   - Latency = time of the first motion report containing that displacement − time of the second strobe. 500 events with random phase.
2. **Step latency (end to end).**
   - A piezo step of 50 µm (rise < 0.2 ms) in x, then y, 200 times each at random phase relative to the 2 kHz tick.
   - Latency = time at which the fused housing estimate crosses 50 % of the step − time at which the capacitive sensor crosses 50 %.
3. **Sine phase.** A shaker drives the paper at 1–50 Hz and 0.1–0.5 mm; the group delay is the slope of phase against frequency.
4. **Accuracy and noise sweep.**
   - θ ∈ {35, 45, 55, 65, 75}° × ρ ∈ {0, 30, …, 330}° × 7 paper types × speed ∈ {1, 10, 30, 100, 200} mm/s.
   - Straight lines of 20 mm and 5 mm circles.
   - Height offsets of ±0.2 mm (paper cockle) at 55°.
   - Rest records of 10 s for noise.
5. **Interference.** The actuated nib (rig module or Rev A) moves ±0.5 mm at 10 Hz in view; fresh ink lines are crossed.
6. **Roll coverage.** The full 3-module nose on the rotary stage, continuous roll at 30°/s during writing motion; log the valid flags (`opt_valid`, ICD §4.2).

### Sample size

- Latency: ≥ 200 events per method gives the 99th percentile with a binomial 95 % CI of ±0.7 percentage points on the exceedance.
- Accuracy: 3 repeats per condition; per-condition RMS with bootstrap CIs.

### Data format

- Logic-analyser captures (native plus exported CSV).
- Per run: the sensor raw counts and quality metrics, the stage encoder, the ICD research frames, and the condition table.

### Analysis

1. Latency distributions (median, 99th percentile, max) per method.
   - Strobe gives the sensor pipeline; step and sine give end to end.
   - The difference is the MCU, bus and fusion share.
2. Noise: RMS per sample after removing the constant velocity (linear detrend per 100 ms), per θ and paper.
3. Error per 10 ms window: the norm of the difference between sensor and stage displacement over each window (DeltaPen definition, OPT-02); median and mean.
4. Scale error against θ and paper, before and after the B04 calibration.
5. Valid fraction against roll.

### Acceptance criteria

<!-- AC-TABLE:EXP-S01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S01-01 | REQ-SNS-001 | Total latency from physical paper motion to the fused housing-motion estimate available to the stage task (step method), 99th percentile of ≥ 200 events | ≤ 3 ms | requirement | REQ-SNS-001 | DEC-005; optics selection (E-7) |
| AC-S01-02 | REQ-SNS-001 | Per-sample displacement noise at ≥ 1 kHz on matte paper, θ 35-75°, after removing constant velocity (linear detrend per 100 ms) | ≤ 5 µm RMS | requirement | REQ-SNS-001 | DEC-005 |
| AC-S01-03 | REQ-SNS-001 | Housing page-plane motion output rate | ≥ 1 kHz | requirement | REQ-SNS-001 | DEC-005 |
| AC-S01-04 | REQ-SNS-002 | Fraction of samples with at least one valid optical module, roll 0-360° (30° steps), θ 35-75°, 5 paper types, during writing motion | ≥ 99 % | derived | REQ-SNS-002 (valid view at any roll); 99 % engineering judgement | optics layout (3 modules at 120°) |
| AC-S01-05 | — | Tracking-loss events longer than 300 ms (ICD fault bit 4) per 10 min of scripted writing on matte paper | < 1 | hypothesis | docs/icd.md s6 fault threshold (300 ms); event rate engineering judgement | fault-handling design |
| AC-S01-06 | — | Median translation error per 10 ms window on matte paper at θ 55°, 10-100 mm/s | ≤ 24 µm | hypothesis | DeltaPen median on a Wacom surface (OPT-02): at least published state of the art, now on paper | DEC-005 |
| AC-S01-07 | — | Relative increase of per-sample noise with the actuated nib moving (±0.5 mm, 10 Hz) and fresh ink in the field of view | ≤ 10 % | hypothesis | engineering judgement (OPT notes s2.5 item 4: effect unknown) | optics placement |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-S01).
<!-- AC-TABLE:EXP-S01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| No candidate meets ≤ 3 ms and ≤ 5 µm on paper | DEC-005 is re-opened. Stage B uses external housing metrology (rig or motion capture) as the correction reference (tethered research only), and the product architecture waits. research_questions: "without it, only external or coded references work". |
| Only some papers work | The claim is restricted to listed paper types; the coded-paper path (REQ-CAP-003) gains weight. |
| Coverage < 99 % at some roll | The optics layout (3 at 120°) changes, or an "optical invalid" authority fade is accepted (fault bit 4) and its frequency is reported. |
| Latency 3–5 ms | The prediction horizon grows. Re-run the estimator tuning with the measured delay; the distortion cost is reported through EXP-E01 and B09. |

### Risks and controls

| Risk | Control |
|---|---|
| NDA or availability of lens-less parts | Keep the PMW33xx short-Z route as a fallback (OPT notes §2.2). |
| Strobe light leaks from the module LED | Mask verified by a no-strobe control: no motion reported. |
| Motion blur at 200 mm/s | Report per speed; the requirement applies up to 100 mm/s, with 200 mm/s characterised. |

---

## 13. EXP-S02: Capture and fusion accuracy against references

### Purpose and what it gates

This experiment measures how well the pen's own stroke record (ICD §4.3: deposited-ink position at 200 Hz, stage-corrected) reproduces the real ink on the page:

- over one stroke (shape fidelity);
- over a page (absolute and relative drift);
- in segmentation (pen-down and pen-up);
- and, where coded paper or an external reference is used, in page identity.

It verifies REQ-CAP-001 (the record's content, including uncertainty) and REQ-CAP-003 (page identity via coded paper or an external reference; ordinary-paper relocalisation is treated as a research risk, COR-16). It informs DEC-005 and the capture architecture (optical flow + IMU + stage for relative motion; coded paper for absolute position).

### References

1. **Scanned ink (R3):** the shape truth at µm level; used for all tests.
2. **Rig encoders and metrology (R2):** the time truth for robot-written tests.
3. **A digitiser under the paper** (EMR tablet class): used for human-written sessions, for timing and segmentation only. Consumer tablets are accurate to ±0.25 mm (Elble & McNames 2016, via PDT notes), so they cannot be a shape reference.
4. **Coded paper** (Ncode/Anoto pattern): when the research pen carries a coded-paper reader (REQ-CAP-003), page identity and absolute position are compared with the scanned page. The code geometry is verified on the scan.

### Hypotheses

- Per-stroke shape error ≤ 0.1 mm RMS after rigid alignment (AC-S02-01).
- Page-level error ≤ 0.25 mm RMS with an absolute reference (AC-S02-02).
- Relative drift without an absolute reference ≤ 2.6 mm/min, DeltaPen's idle drift (OPT-02) (AC-S02-03).
- Stroke-count error ≤ 1 % (AC-S02-04).
- 200/200 correct page identifications (AC-S02-05).
- The reported uncertainty covers 90–99 % of true errors at 2σ (AC-S02-06). ICD v1.0 has no uncertainty field in the stroke record, so this criterion waits for an ICD revision (see `README.md`).

### Equipment and setup

- Rig R2 (robot-written sets) and rig R3 (scans, fiducials, distortion map).
- An EMR digitiser under the paper, for timing and segmentation only (±0.25 mm class).
- Coded-paper pages (Ncode or Anoto pattern) and plain paper of the EXP-S01 types.
- The Stage B/C pen logging stroke samples (ICD 0x02). When tethered, research frames (0x01) are logged in parallel as the internal reference.
- The clock alignment of §0.4 between the pen, digitiser and rig.

### Procedure

1. **Robot-written set (R2):** the feature course, handwriting samples A–C and one A5 page of dense text (the robot replays recorded human handwriting from EXP-H01, scaled to 3–4 mm letters). θ 45/55/65°, NEUTRAL mode, 5 repeats.
2. **Human-written set:** the EXP-H06 and EXP-H01 sessions (with consent) on paper over the digitiser, scanned afterwards.
3. **Drift test:** 10 min of continuous writing without an absolute reference; compare the pen's relative page map with the scan after aligning the first line only.
4. **Page-identity test:** 200 page sessions over 20 pages with coded paper or an external reference, in randomised page order.

### Sample size

- Robot set: 5 repeats × 3 θ × 5 paths = 75 runs.
- Human set: all consenting sessions (≥ 20 participants).
- Identity: 200 sessions, a zero-failure demonstration of R ≥ 0.985 at 95 % confidence.

### Data format

ICD logs (0x02 stroke samples; 0x01 research frames when tethered), scans, digitiser logs, and the alignment transforms.

### Analysis

1. Match stroke samples to the scanned centreline by arc length; compute point-to-curve distances after per-stroke rigid (3-DOF) alignment (shape) and after a per-page similarity (4-DOF) transform (page level).
2. Drift: the displacement of each later line's alignment against the first, as a function of time.
3. Segmentation: match strokes by overlap; count missed and split strokes.

### Acceptance criteria

<!-- AC-TABLE:EXP-S02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S02-01 | REQ-CAP-001 | Per-stroke shape error: RMS point-to-curve distance between stroke-record points (ICD 0x02) and the scanned ink centreline after per-stroke rigid alignment | ≤ 0.1 mm | hypothesis | engineering judgement: small against 2-8 mm letter heights (config writing.letter_height) | capture architecture (DEC-005) |
| AC-S02-02 | REQ-CAP-003 | Page-level position error after a per-page similarity transform, with coded paper or an external absolute reference | ≤ 0.25 mm RMS | hypothesis | consumer digitiser accuracy class ±0.25 mm (Elble & McNames 2016, docs/research/notes/PDT_pd_et_handwriting.md s1.2) | REQ-CAP-003; coded-paper licence decision |
| AC-S02-03 | — | Relative drift of the pen's page map without an absolute reference (optical + IMU fusion) over 10 min of writing | ≤ 2.6 mm/min | hypothesis | DeltaPen idle drift 2.6 mm/min (OPT-02) | ordinary-paper capture feasibility (COR-16) |
| AC-S02-04 | REQ-CAP-001 | Stroke segmentation error \|captured strokes - scanned strokes\| / scanned strokes | ≤ 1 % | hypothesis | engineering judgement | contact detection (REQ-SNS-005) |
| AC-S02-05 | REQ-CAP-003 | Correct page identification in 200 page sessions (coded paper or external reference), randomised page order | 200/200 | derived | REQ-CAP-003; 0 errors in 200 demonstrates R ≥ 0.985 at 95 % confidence (success run) | REQ-CAP-003 |
| AC-S02-06 | REQ-CAP-001 | Coverage of the reported position uncertainty: fraction of samples whose true error (vs scan) lies within the reported 2 sigma | within 90-99 % | hypothesis | engineering judgement (calibrated ~95 % coverage). Requires an uncertainty field that ICD v1.0 s4.3 does not have | REQ-CAP-001 uncertainty field; ICD revision |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-S02).
<!-- AC-TABLE:EXP-S02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Shape error > 0.1 mm | Capture is only usable for coarse notes; recognition (EXP-C01) will quantify the cost. |
| Drift > 2.6 mm/min | "Ordinary paper" capture stays a research item (COR-16); product capture uses coded paper (licence costs, OPT-08/11). |
| Identity errors | Coded-paper decoding or the page-session logic is fixed before C02. |

### Risks and controls

| Risk | Control |
|---|---|
| The coded-paper dot pattern changes optical-flow behaviour | Run plain and coded paper separately; report both |
| Scanner geometric error mistaken for capture error | R3 distortion map; fiducials on every page |
| Tethered and untethered builds differ (timing, power) | Run the robot set on both builds at Stage C |
| Privacy of human-written pages | Neutral prompts; pseudonymised ids; scans stored under §6 of `records/README.md` |

---

## 14. EXP-F01: Hardware fault injection

### Purpose and what it gates

This experiment verifies, on the real circuit and in contact with paper, the protections that must hold independently of firmware:

- REQ-SAF-001: hardware disable of both bridges on over-current, over-temperature or watchdog;
- REQ-SAF-002: current limits;
- REQ-SAF-004: power-loss behaviour, a ramped release over ≥ 30 ms, with the mark length documented;
- REQ-PWR-003: no actuation while charging;
- the DEC-015 rules: never de-energise in contact except on hard faults; frozen stage sensor detected within 5 ms; fade before pen-up.

It builds on the bench bring-up (`electronics/README.md` steps 8–10) and the simulated failure cases F1–F7 (`results/sim/sweeps/summary.json`). It is part of gate **G-S** (human use of powered prototypes).

### Hypotheses

- **H-F01-1.** The window-comparator latch removes VMOT within 50 µs of a coil short or over-current, whatever the firmware state (AC-F01-01, AC-F01-02).
- **H-F01-2.** With the hold-up ramp, the ink excursion after power loss in contact is at most half of the unramped excursion (AC-F01-06). The unramped simulated value is 779 µm (F3).
- **H-F01-3.** A frozen Hall sensor is detected within 5 ms, and the open-loop hold keeps the excursion ≤ 0.3 mm (AC-F01-07, AC-F01-08). The undetected simulated value is 563 µm (F4).
- **H-F01-4.** Soft faults (over-temperature, low battery) never de-energise the stage in contact (AC-F01-10, DEC-015).

### Faults injected

| Id | Fault | Method | Predictions and references |
|---|---|---|---|
| F01-a | Coil short | Solid-state short across the coil terminals (< 1 µs), at duty 0.1–0.9 and VBAT 3.0 / 3.7 / 4.2 V | ngspice: detect 8.8 µs, VMOT off 22.6 µs, 5.4 A peak with ideal switches (`results/electronics/spice_drive_stage.json`) |
| F01-b | Over-current into a dummy load | Step to 0.2 Ω with the supply limited to 2 A (bring-up step 8) | Pass criterion of step 8 |
| F01-c | Open coil lead | Relay opens one lead during writing | Voltage-headroom fault (bit 6) and safe state |
| F01-d | Power loss in contact | VBAT removed (cell protection trip emulated) during writing at N 1 N, θ 35/50/75°, with and without the hold-up ramp | Unramped ink jump 779 µm within 50 ms (F3) |
| F01-e | Frozen Hall sensor | SPI data frozen by fault injection, and the Hall supply cut, during writing | Undetected: 563 µm jump, stage to its stop (F4) |
| F01-f | Over-temperature | Coil NTC substituted by a resistor decade stepping to the over-temperature value during writing | Fault bit 2; fade; no de-energise in contact |
| F01-g | Low battery | VBAT stepped to 3.3 V during writing | Fade; shutdown at pen-up (timeout 5 s) |
| F01-h | Charger connected | VBUS applied during PWM (bring-up step 9) | ACT_EN low ≤ 1 ms |
| F01-i | Blocked stage | 0.1 mm mechanical obstruction | Peak current 0.551 A (F6) |
| F01-j | MCU states | Over-current while the MCU is halted in the debugger, held in reset, or in a hard-fault loop | Latch independent of firmware |

### Equipment and setup

Rig R7 (fault-injection board, oscilloscope, current probe, logic analyser); rig R2 for the in-contact faults (d, e, f, g, i) with R3 scans of the resulting marks.

### Procedure

- Each fault type is injected at randomised times during scripted writing.
- The reset and recovery sequence is recorded.
- Fault latches must clear only through the defined clear sequence with ACT_EN_REQ low.

### Sample size

- Pass/fail items: 59 trials per condition (R ≥ 0.95 at C = 0.95, zero failures) for items that are part of G-S (a, b, h, j). 29 trials (R ≥ 0.90) for the others.
- Mark-length measurements: 10 per θ per ramp setting.

### Data format

Oscilloscope captures (native + CSV), logic-analyser captures, ICD logs (event 0x0002 fault set with its bitmask), scans of marks, and a trial table.

### Analysis

- Timing from fault onset (injection trigger) to VMOT < 0.5 V, FAULT_N low, ACT_EN low, and authority zero.
- Mark length: the maximum distance of the ink from the intended path within 100 ms after the fault (scan).
- Guarded acceptance (§0.5).

### Acceptance criteria

<!-- AC-TABLE:EXP-F01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-F01-01 | REQ-SAF-001 | Time from coil short or over-current onset to VMOT < 0.5 V, 59 trials, duty 0.1-0.9, VBAT 3.0/3.7/4.2 V | ≤ 50 µs | derived | electronics/README.md bring-up step 8 pass criterion; ngspice 22.6 µs (results/electronics/spice_drive_stage.json) | G-S; REQ-SAF-001 |
| AC-F01-02 | REQ-SAF-001 | Firmware independence: with the MCU halted, in reset or in a hard-fault loop, an over-current latches FAULT_N and removes VMOT; recovery only via the clear sequence with ACT_EN_REQ low | 59/59 per MCU state | requirement | REQ-SAF-001; n = 59 success run (R 0.95, C 0.95) | G-S |
| AC-F01-03 | REQ-SAF-002 | Software current clamp per axis under saturating commands | ≤ 0.45 A (requirement text) | requirement | REQ-SAF-002 text. CONFLICT: design limit 0.60 A (config actuator.i_max v0.4.1; REQ-SAF-002 current estimate); resolve before test | resolve REQ-SAF-002; REQ-ACT-001 (1.4 N needs 0.62 A) |
| AC-F01-04 | REQ-SAF-002 | Independent hardware trip threshold per axis (window comparator) | within 0.6 A ± 5 % (requirement text) | requirement | REQ-SAF-002 text. CONFLICT: design window ±0.80 A (electronics/README.md; config actuator.i_trip); ±5 % engineering judgement | resolve REQ-SAF-002 |
| AC-F01-05 | REQ-SAF-004 | Actuator current ramp-down duration after VBAT removal in contact (N 1 N, θ 35/50/75°), hold-up energy only | ≥ 30 ms | requirement | REQ-SAF-004 | hold-up circuit; COR-19 |
| AC-F01-06 | REQ-SAF-004 | Ink excursion within 100 ms of power loss in contact, ramped release as a fraction of unramped release (scans) | ≤ 50 % | hypothesis | engineering judgement; prediction unramped 779 µm within 50 ms (results/sim/sweeps/summary.json F3) | keep or remove hold-up energy; mechanical lock (COR-19) |
| AC-F01-07 | — | Detection latency of a frozen stage (Hall) sensor, stuck SPI value and sensor unpowered, during writing | ≤ 5 ms | derived | DEC-015; docs/icd.md s6 | G-S; DEC-015 |
| AC-F01-08 | — | Ink excursion within 50 ms after a frozen-Hall fault with detection active | ≤ 0.3 mm | hypothesis | engineering judgement, about half the undetected simulated value 0.56 mm (results/sim/sweeps/summary.json F4) | DEC-015 open-loop hold strategy |
| AC-F01-09 | REQ-PWR-003 | Time from VBUS applied during PWM to ACT_EN low; no actuation while charging | ≤ 1 ms | requirement | REQ-PWR-003; electronics/README.md bring-up step 9 | G-S |
| AC-F01-10 | — | Over-temperature and low-battery faults in contact: stage not de-energised in contact, authority fades, shutdown only after pen-up or 5 s timeout | 29/29 | derived | DEC-015; docs/icd.md s6; n = 29 success run (R 0.90, C 0.95) | DEC-015; G-S |
| AC-F01-11 | REQ-SAF-002 | Peak coil current with the stage blocked by a 0.1 mm obstruction during writing | ≤ software clamp value | derived | prediction 0.551 A (results/sim/sweeps/summary.json F6); clamp per AC-F01-03 once resolved | limiter |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (11 rows for EXP-F01).
<!-- AC-TABLE:EXP-F01:END -->

### Notes on conflicts that must be resolved before this test

- **REQ-SAF-002 text vs design.** The requirement text says a 0.45 A software limit and a 0.6 A hardware trip. The design implements 0.60 A and ±0.80 A (config `actuator.i_max`/`i_trip`, `electronics/gen/design_revA.py`, and the requirement's own current estimate).
- **REQ-ACT-001 vs current limits.** REQ-ACT-001's 1.4 N for 2 s needs about 0.62 A on a single axis (1.4 / (3.17 × 0.717)), above both limits. AC-F01-03/04 are written against the requirement text and flagged; the project lead must choose one set.

### What changes which decision

| Result | Consequence |
|---|---|
| Any G-S item fails | No powered pen touches a participant (`prototype_stages.md`). |
| Ramped release does not reduce the mark by ≥ 50 % | The hold-up energy may not be worth the board area (DEC-014 packaging). A mechanical lock (COR-19) is re-evaluated. |
| Frozen-Hall detection > 5 ms or large marks | DEC-015's open-loop hold strategy is revised (for example an immediate controlled ramp). |

### Risks and controls

| Risk | Control |
|---|---|
| Destructive faults damage the only pen | Run first on the bench board with dummy loads, then on a sacrificial build; never on units destined for participants without full re-qualification |
| High fault currents (5.4 A peak with ideal switches in ngspice) | Current-limited supply; eye protection; battery-powered tests in a fire-safe enclosure |
| Fault injection alters the circuit (relay capacitance, lead inductance) | Characterise the injection board on a dummy load; keep leads < 50 mm |
| Participants exposed to injected faults | Never: fault injection is bench-only |

---

## 15. EXP-F02: Firmware robustness

### Purpose and what it gates

This experiment verifies the timing and robustness of the control firmware on the target MCU under full load:

- loop rates (REQ-CTRL-001) and the ICD §2 budgets (stage task ≤ 250 µs, jitter ≤ 20 µs, current ISR ≤ 5 µs, DEC-010's revisit trigger "bring-up step 7 timing");
- the limiter (REQ-CTRL-004: no output bypasses limits);
- the ML guard (REQ-SAF-003: invalid outputs reduce authority within 20 ms; ICD §5 v1.1 guard rules);
- the watchdog (REQ-SAF-001);
- brown-out (REQ-SAF-004, REQ-CAP-002);
- optical-dropout handling (F1);
- long-run stability;
- the IMU data rate (REQ-SNS-003);
- C-vs-Python numerical equivalence (`docs/physics.md`: "C-vs-Python vectors").

It is part of G-S (for ASSIST modes) and G-C.

### Hypotheses

- The ICD §2 budgets hold with margin under worst-case load (AC-F02-02…04). `electronics/README.md` estimates CPU ≈ 130 µs per 500 µs stage period.
- No fuzzed output ever passes the limiter (AC-F02-06).
- The guard classes behave as ICD §5 v1.1 specifies (AC-F02-05). Class (5) is expected to exceed REQ-SAF-003's 20 ms.
- Optical dropout follows the simulated F1 behaviour (AC-F02-09).

### Equipment and setup

- Rig R7: logic analyser ≥ 100 MS/s with 16 channels; a programmable supply with ramp control; an SWD debugger for halts; a host PC for the reference vectors.
- Rig R2 for the in-contact brown-out tests.
- **Test builds** have fault-injection hooks compiled in; release builds never do. The key timing measurements are repeated on the release build using the DWT cycle counter, without GPIO probes.

### Procedure

1. **Timing.**
   - GPIO toggles at ISR and task entry and exit; logic analyser.
   - ≥ 10⁶ stage periods (8.3 min) with BLE streaming, QSPI logging, the ML predictor at 250 Hz and all sensors active.
   - Also under worst-case flash erase and BLE connection events.
2. **Limiter fuzzing.** A test build replaces estimator and ML outputs with ≥ 10⁶ random, extreme, NaN, Inf and rapidly switching values. The stage reference q_r, its slew and the current references are checked against q_lim 0.55 mm, 0.08 m/s (P-22) and the current clamp.
3. **ML guard** (ICD §5 v1.1).
   - Each class is injected 59 times at random phases:
     - (1) NaN, ±Inf or int8 saturation, which must be rejected;
     - (2) |d̂| > q_lim, which must be clipped;
     - (3) output rate > 50 mm/s, which must be slew-limited;
     - (4) a stale output older than the horizon h;
     - (5) a confidently wrong prediction (a biased or phase-shifted d̂) that the a-posteriori check must catch and replace with the Kalman estimate for ≥ 1 s, logging event 0x0006.
   - Measure the time until the stage command no longer contains the invalid part.
   - REQ-SAF-003 asks for ≤ 20 ms. The v1.1 check (5) averages over 200 ms, and ICD v1.1 defines no output expiry or confidence field. The expected conflict is listed in `README.md`.
4. **Watchdog.** Halt the core in the debugger during PWM (bring-up step 10); also an infinite loop injected in the stage task. 59 trials each.
5. **Brown-out.**
   - The programmable supply ramps VBAT 4.2 → 2.8 V at 1 V/s and at 1 V/ms during writing in contact (on R2).
   - Measure the actuation ramp-down, MCU behaviour and the log integrity (blocks lost).
   - 29 trials per ramp rate.
6. **Optical dropout.** Mask the optics for 0.3 s during writing; log authority (compare with F1: minimum 0.002, 0.991 after 1 s).
7. **Soak.** 8 h of scripted writing on R2 with random injected faults (from items 3, 5 and 6, and F01-f and -g). Count unhandled hard faults and unexplained resets.
8. **Numerical equivalence.** Run the C firmware (host build and target) on the reference vectors (`firmware/tests/vectors`) generated by the Python simulator; compare the outputs.

### Sample size

Success-run numbers as stated (59 → R ≥ 0.95; 29 → R ≥ 0.90, both at C = 0.95); 10⁶ periods for timing tails.

### Data format

Logic-analyser captures, ICD logs, soak summary CSV, vector-comparison report.

### Analysis

- **Timing:** maxima and the 99.9999th percentile over ≥ 10⁶ periods, per task; exceedance counts against each budget; the jitter histogram.
- **Guard:** the latency from injection to the first stage command without the invalid content, per class (logic-analyser trigger to the research-frame `flags` bit 6 and the event 0x0006 timestamp).
- **Limiter:** violation counts.
- **Brown-out:** a timeline of VBAT, coil currents, ACT_EN and log block writes.
- **Soak:** events classified as injected-and-handled, injected-and-unhandled, or spontaneous.
- **Vectors:** the maximum absolute difference per output channel.

### Acceptance criteria

<!-- AC-TABLE:EXP-F02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-F02-01 | REQ-CTRL-001 | Measured loop rates: current loop, stage loop, estimator, ML predictor, each within ±0.1 % of nominal | within current ≥ 20 kHz (design 40 kHz); stage 2 kHz; estimator 2 kHz; ML 250 Hz | requirement | REQ-CTRL-001 (text: current regulation 20 kHz; DEC-012 and docs/icd.md s2 use 40 kHz) | DEC-010 |
| AC-F02-02 | — | Worst-case 2 kHz stage-task execution time over ≥ 1e6 periods with BLE streaming, QSPI logging and ML active | ≤ 250 µs | derived | docs/icd.md s2 | DEC-010 (nRF5340 vs STM32U5 fallback) |
| AC-F02-03 | — | Stage-task release jitter (maximum deviation from the nominal period), same conditions | ≤ 20 µs | derived | docs/icd.md s2; config control.exec_jitter | DEC-010 |
| AC-F02-04 | — | 40 kHz current-loop ISR execution time | ≤ 5 µs | derived | electronics/README.md bring-up step 7 | DEC-010 |
| AC-F02-05 | REQ-SAF-003 | ML guard (docs/icd.md s5 v1.1): time from an injected invalid output until the stage command no longer contains it, per class: (1) NaN/Inf or int8 saturation (rejected), (2) \|d_hat\| > q_lim (clipped), (3) d_hat rate > 50 mm/s (slew-limited), (4) stale output older than h, (5) confidently wrong prediction (Kalman fallback by the a-posteriori check); 59 trials per class | ≤ 20 ms in 59/59 per class | requirement | REQ-SAF-003; n = 59 success run. CONFLICT: the v1.1 a-posteriori check (5) uses a 200 ms running RMS, so its fallback is expected to exceed 20 ms; ICD v1.1 defines no output expiry or confidence field for class (4) (REQ-ML-002 asks for timestamp/expiry/confidence) | DEC-016; G-S for ASSIST_ML; REQ-SAF-003 vs ICD s5 v1.1 |
| AC-F02-06 | REQ-CTRL-004 | Limiter: violations of the q_lim radius (0.55 mm) or slew limit (0.08 m/s) by the commanded stage reference over ≥ 1e6 fuzzed estimator/ML outputs | = 0 | requirement | REQ-CTRL-004; limits from docs/physics.md P-22 | G-S |
| AC-F02-07 | REQ-SAF-001 | Watchdog: halted or hung firmware leads to reset and VMOT off within the watchdog period + 1 ms | 59/59 | requirement | REQ-SAF-001; electronics/README.md bring-up step 10 | G-S |
| AC-F02-08 | REQ-SAF-004 | Brown-out in contact (VBAT 4.2 -> 2.8 V at 1 V/s and 1 V/ms): actuation ramps down over ≥ 30 ms, no MCU lock-up, log loses ≤ 1 block | 29/29 per ramp rate | requirement | REQ-SAF-004; REQ-CAP-002 | G-S; G-C |
| AC-F02-09 | — | Optical tracking loss of 0.3 s during writing: minimum authority during the loss / authority 1 s after tracking resumes | ≤ 0.05 / ≥ 0.95 | hypothesis | prediction 0.002 / 0.991 (results/sim/sweeps/summary.json F1) | fault handling |
| AC-F02-10 | — | Unhandled hard faults or unexplained resets in an 8 h soak with scripted writing and randomised injected faults | = 0 | hypothesis | engineering judgement | G-C |
| AC-F02-11 | — | C firmware vs Python simulator reference vectors (firmware/tests/vectors): maximum absolute difference of the stage reference | ≤ 0.1 µm | derived | engineering judgement (float32 vs float64 rounding); docs/physics.md 'C-vs-Python vectors' | firmware release for EXP-B09 |
| AC-F02-12 | REQ-SNS-003 | IMU output data rate from firmware timestamps | ≥ 1 kHz | requirement | REQ-SNS-003 | sensor configuration |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (12 rows for EXP-F02).
<!-- AC-TABLE:EXP-F02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Stage task > 250 µs or jitter > 20 µs under load | DEC-010's fallback: STM32U5 motor-control MCU with the nRF5340 as radio co-processor (EML notes), or the ML predictor is dropped from the MCU. |
| Guard or limiter violations | ASSIST_ML and ASSIST_KF are blocked from human use until fixed (G-S). |
| Brown-out lock-up or > 1 block lost | Hold-up and logging design revised before G-C. |

### Risks and controls

| Risk | Control |
|---|---|
| Probe effect of GPIO toggles | Toggle cost measured (≤ 1 µs); release-build repeat with DWT |
| Test build differs from release build | Hooks behind a compile flag; release build re-tested on timing and brown-out |
| Random fuzzing misses structured failures | Add adversarial patterns: steps, Nyquist-rate alternation, stale repeats, slow drifts just below the thresholds |

---

## 16. EXP-M02: Flexure fatigue coupons

### Purpose and what it gates

This experiment tests the fatigue life of as-manufactured C17200 TH04 cross-strip gimbal blades (0.05 × 1.0 × 2.0 mm) and spiral-arm diaphragm arms at the design stresses:

| Case | Stress | Source |
|---|---|---|
| Gimbal, full travel | 177 MPa | `results/mechanics/flexure_calc.json` |
| Gimbal, typical 0.3 mm amplitude | 82 MPa | same |
| Diaphragm at the stop | 231 MPa | same |

It checks the allowables (150 MPa alternating, 310 MPa peak; REQ-MECH-006; AMF-18/19) and the buckling margin under 2 N axial (REQ-MECH-007, predicted 19).

- **Gates** DEC-007 (revisit trigger "Flexure fatigue coupons (EXP-M02)") and the flexure design release.
- Thin, etched or cut strip edges may lower the fatigue strength below the bulk handbook value, so the coupons must be made by the production process.

### Hypotheses

- The fatigue strength of as-made blades at 10⁸ cycles is ≥ 150 MPa (lower 95 % bound, AC-M02-01). Edge defects from etching or cutting are the main threat.
- Blades survive 10⁷ cycles at the full-travel stress, and diaphragm arms survive 10⁶ cycles at the stop stress (AC-M02-02, AC-M02-04).
- The buckling margin is ≥ 5 (AC-M02-03); 19 is predicted.

### Equipment and setup

- Rig R8: resonant fatigue stations with laser amplitude control; strain-gauged calibration coupons; a stereo microscope (≥ 50×) and SEM; an axial load frame with a 0–10 N load cell.
- The coupon fixture reproduces the pen's clamp design and clamping torque. Laboratory at 23 °C; coupon temperature monitored (< 40 °C).

### Procedure

1. **Coupons:** ≥ 30 blades and ≥ 20 diaphragm arms from ≥ 2 material lots, formed, etched or cut and age-hardened exactly as the pen parts (AMF notes: form before ageing). Edge quality is inspected and recorded.
2. **Stress calibration:** strain gauges on 3 sacrificial coupons per geometry relate drive amplitude to surface stress, cross-checked with the beam model (P-12).
3. **S–N testing:** fully reversed bending (R = −1) at resonance, 100–300 Hz.
   - Stress levels 280, 230, 177 and 150 MPa, 6 coupons each. Run-out: 10⁸ cycles at ≤ 177 MPa, 10⁷ above.
   - Failure: a 5 % drop in resonance frequency or a visible crack at 50×.
4. **Full-travel qualification:** 10 blades at 177 MPa to 10⁷ cycles (AC-M02-02).
5. **Diaphragm:** 10 arms at 231 MPa to 10⁶ cycles (overload-stop events) (AC-M02-04).
6. **Stiffness drift:** 3 blades at 82 MPa to 10⁸ cycles with stiffness logged (AC-M02-05).
7. **Buckling:** axial compression of 5 complete gimbal assemblies to the buckling load or 10 N (5 × 2 N) (AC-M02-03).
8. **Fractography:** optical and SEM of failures to separate edge-initiated from surface-initiated cracks.

### Sample size

- 6 coupons per S–N level with run-outs allows a Basquin fit with a lower 95 % prediction bound (ASTM E739-type analysis).
- 10/10 run-outs demonstrate R ≥ 0.74 at C = 0.95. This is a screening level; the production-release level is 29/29 (R ≥ 0.90).

### Data format

Per coupon: lot, process, edge photos, calibration factor, stress, cycles to failure or run-out, frequency log, fractographs.

### Analysis

- Basquin fit S = A·N^b by maximum likelihood with run-outs as right-censored data; lower 95 % prediction bound at 10⁸ cycles.
- Binomial (success-run) statements for the run-out tests.
- Buckling: load–displacement curves with a Southwell plot to estimate the critical load.

### Acceptance criteria

<!-- AC-TABLE:EXP-M02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-M02-01 | REQ-MECH-006 | Fatigue strength at 1e8 cycles (R = -1) of as-manufactured C17200 TH04 cross-strip blades (0.05 mm), lower 95 % prediction bound of the S-N fit with run-outs | ≥ 150 MPa | requirement | REQ-MECH-006 alternating allowable (AMF-18/19: 310 MPa typical fatigue strength / 2) | DEC-007; flexure release |
| AC-M02-02 | REQ-MECH-006 | Blades cycled at the full-travel stress 177 MPa (results/mechanics/flexure_calc.json): run-outs to 1e7 cycles | 10/10 | derived | derived: full-travel excursions are rare; 1e7 engineering judgement | travel and stop limits |
| AC-M02-03 | REQ-MECH-007 | Buckling load of the gimbal assembly under axial compression / 2 N | ≥ 5 | requirement | REQ-MECH-007; prediction 19 (results/mechanics/flexure_calc.json) | DEC-007 |
| AC-M02-04 | REQ-MECH-006 | Spiral-arm diaphragm arms at the stop stress 231 MPa: run-outs to 1e6 cycles | 10/10 | derived | derived: overload-stop events over life (1e6 engineering judgement) | axial suspension (DEC-007 rev.) |
| AC-M02-05 | — | Stiffness drift of blades over 1e8 cycles at 82 MPa (typical amplitude) | ≤ 5 % | hypothesis | engineering judgement | calibration interval |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-M02).
<!-- AC-TABLE:EXP-M02:END -->

### What changes which decision

- The lower-bound fatigue strength at 10⁸ cycles is below 150 MPa: the allowable drops. Blades are redesigned (thinner or longer, per AMF-26 sizing), which changes k_tip and the lever dynamics (B05). DEC-007 is re-opened.
- Buckling margin < 5: blade width and length change.

### Risks and controls

| Risk | Control |
|---|---|
| Failures at the clamp, not in the free length | Fractography; clamp redesign; clamp failures excluded only with evidence |
| Resonant heating | Temperature monitoring; duty pauses |
| Beryllium dust | Controlled machining and handling (AMF notes §2.2) |

---

## 17. EXP-M03: Mass, centre of mass and balance of built pens

### Purpose and what it gates

This experiment weighs and balances every built pen variant (Stage B tethered Rev A/A.1; Stage C untethered; Stage D candidates) and a benchmark set of ordinary and assistive pens.

- **Requirements:** REQ-FORM-001 (grip 14–16 mm; bulge ≤ 16 mm), REQ-FORM-002 (145–160 mm), REQ-FORM-003 (≤ 35 g), REQ-FORM-004 (CoM ≤ 70 mm, provisional: "ordinary-pen comparison pending").
- **Open issue** M-1 (`mechanics/README.md`).

**Predictions** (`results/mechanics/mass_budget.json`, v0.4.1):

| Variant | Mass incl. allowances and 10 % contingency | CoM from the tip |
|---|---|---|
| Rev A | 40.7 g | 80.6 mm |
| Rev A.1 | 37.2 g | 79.4 mm |
| Rev A.1 with polymer rear barrel | 33.2 g | 76.0 mm |

These values changed during 2026-09-27 as the budget was revised; the frozen prediction file, not this table, is the comparison reference (§0.2).

REQ-FORM-004 is predicted to fail for all three.

### Hypotheses

- Rev A.1 with a polymer rear barrel meets REQ-FORM-003 (33.2 g predicted) but not REQ-FORM-004 (76.0 mm predicted) (AC-M03-01, AC-M03-02).
- Measured values fall within ±5 % (mass) and ±3 mm (CoM) of the budget (AC-M03-06).

### Equipment and setup

- Analytical balance (0.1 mg, 200 g).
- Two-load-cell or knife-edge CoM fixture (±0.5 mm).
- Bifilar pendulum for the moment of inertia about the grip point (±2 %).
- Micrometer and profile projector for diameters (±0.01 mm).

### Procedure

1. Every built pen with a standard refill and cell: mass, CoM from the tip, moment of inertia about the point 20 mm from the tip, and the diameter profile (every 5 mm).
2. **Benchmark set (≥ 10 pens):**
   - ballpoints and gel pens;
   - a fountain pen;
   - a weighted assistive pen;
   - wide-grip pens;
   - two digital capture pens (Anoto/Ncode class, 18–22 g; OPT-08/10/11).
   Measure the same quantities.

### Sample size, data format and analysis

- **Sample size:** every built pen, at least 3 per variant, each measured 3 times. Benchmark set ≥ 10 pens.
- **Data format:** one CSV row per pen and repeat: serial, variant, refill and cell ids, mass, CoM, inertia, diameter profile; photographs.
- **Analysis:** the mean of repeats with expanded uncertainty; the difference from the budget; the benchmark distribution (min, median, max) and the pen's position in it.

### Acceptance criteria

<!-- AC-TABLE:EXP-M03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-M03-01 | REQ-FORM-003 | Mass of each built pen including refill and battery | ≤ 35 g | requirement | REQ-FORM-003; budget 33.2 g (Rev A.1, polymer rear barrel) to 40.7 g (Rev A) incl. allowances and 10 % contingency (results/mechanics/mass_budget.json v0.4.1) | form factor; EXP-H02 |
| AC-M03-02 | REQ-FORM-004 | Centre of mass from the tip | ≤ 70 mm | requirement | REQ-FORM-004 (provisional); budget 76.0-80.6 mm (results/mechanics/mass_budget.json v0.4.1) -> expected FAIL | REQ-FORM-004 revision (with AC-M03-03 and EXP-H02) |
| AC-M03-03 | REQ-FORM-004 | Centre of mass relative to a benchmark set of ≥ 10 commercial pens (ballpoint, gel, fountain, weighted assistive, wide-grip, digital capture pens) | within benchmark min-max | hypothesis | REQ-FORM-004 'ordinary-pen comparison pending'; mechanics/README.md M-1 | REQ-FORM-004 revision |
| AC-M03-04 | REQ-FORM-001 | Grip diameter over 0-40 mm from the tip / maximum diameter of the actuator section | within 14-16 mm / ≤ 16 mm | requirement | REQ-FORM-001 | form factor |
| AC-M03-05 | REQ-FORM-002 | Overall length | within 145-160 mm | requirement | REQ-FORM-002 | form factor |
| AC-M03-06 | — | Measured vs budget (mechanics/mass_budget.csv) for the built variant: mass and CoM | within mass ± 5 %; CoM ± 3 mm | hypothesis | engineering judgement | credibility of the mass-budget method |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-M03).
<!-- AC-TABLE:EXP-M03:END -->

### What changes which decision

- If the CoM exceeds 70 mm but lies within the benchmark range (AC-M03-03), REQ-FORM-004 is revised with EXP-H02 comfort data rather than forcing a redesign.
- If it lies outside the range, M-1 options apply (a shorter pen, a lighter stator, relocating the cell).
- A mass above 35 g triggers the polymer rear barrel (A.1-PR) or cell changes.

### Risks and controls

| Risk | Control |
|---|---|
| Refill and cell variation | Record lots; measure with a standard refill and cell |
| Configuration ambiguity (cap on or off, clip) | Measure as used in writing; report both if a cap is posted |

---

## 18. EXP-P01: Power and runtime

### Purpose and what it gates

This experiment measures the electrical power in each mode and the runtime from a full charge with the qualified cell. It covers REQ-PWR-001 (≥ 60 min of active writing at the design point) and REQ-ACT-002 in use (≤ 0.25 W average copper loss while writing), and informs DEC-008.

The predictions were reconciled in the v0.4.2 consistency pass (`README.md` §6.8, items 19 and 20). They depend on the pen-down duty and on the cell that fits (DEC-014):

| Case (configuration B, design point, 115 mW electronics) | Runtime | Source |
|---|---|---|
| 200 mAh cell, 65 % pen-down duty | ≈ 81 min | `results/trade/config_trade.json` (v0.4.2) |
| 200 mAh cell, continuously in contact | ≈ 54 min | `electronics/README.md` budgets |
| ≈ 130 mAh cell that fits the Rev A.1 bay, 65 % duty | ≈ 53 min | DEC-014 option (a), scaled by capacity |
| D / E, 200 mAh, 65 % duty | ≈ 215 / 277 min | `results/trade/config_trade.json` |

Average copper loss while writing at 65 % duty: B 0.33 W (0.50 W in contact), D 0.05 W, E 0.01 W (same file). The older thermal model gives 0.31 W for B (`results/thermal/thermal.json`, v0.3.0).

### Hypotheses

- Configuration B's runtime at the design point is below 60 min with the cell that fits the Rev A.1 bay (≈ 53 min predicted; ≈ 81 min with a 200 mAh cell). Its average copper loss is above 0.25 W (0.33 W predicted) (AC-P01-01, AC-P01-02).
- Electronics power is 115 mW ± 20 % (AC-P01-03).
- The real pen-down duty is 0.5–0.8 (AC-P01-04).

### Equipment and setup

- Rig R7: an SMU or power analyser (1 µA–3 A, ±0.3 %, ≥ 10 kS/s logging); a battery cycler; a thermal chamber at 25 °C and 35 °C.
- Rig R2 for scripted writing.
- Cells that have passed EXP-P02.

### Procedure

1. **Mode power** with the pen in a holder: OFF, STANDBY, NEUTRAL_HOLD (lifted), and NEUTRAL_HOLD and ASSIST_KF in contact at the design point. SMU logging at ≥ 10 kS/s; separate channels for the actuator supply (VMOT) and the logic rails where the board allows.
2. **Scripted design-point writing** on R2: θ 50°, N 1 N, 65 % pen-down (`config_trade` duty), 0.3 mm / 9 Hz disturbance, ASSIST_KF. Measure the average copper loss (coil currents × R(T)) and the total battery power.
3. **Envelope sampling:** 20 (N, θ) points drawn as in `drive_sense.py`'s envelope (θ 35–75°, N 0.2–2 N log-uniform) to give the distribution of copper loss.
4. **Runtime:** full charge (P02 charge profile) → continuous scripted writing until the actuation cut-off (VBAT 3.3 V, config `electrical.v_bat_min`). 3 cells × 3 repeats at 25 °C, and 1 cell at 35 °C.
5. **Duty from people:** the pen-down duty from the EXP-H06 free-writing logs (research frames, contact flag).

### Sample size, data format and analysis

- **Sample size:** runtime on 3 cells × 3 repeats (the minimum is the verdict value); 20 envelope points × 3 repeats; 3 repeats per mode for mode power.
- **Data format:** SMU logs (HDF5 at ≥ 10 kS/s), ICD research frames (coil currents, `vbat_mV`, `t_coil`), cycler logs.
- **Analysis:** integrated energy per mode; copper loss from i²·R(T); runtime as the time to cut-off; regression of copper loss on N and θ, compared with the `electronics/calcs/drive_sense.py` envelope.

### Acceptance criteria

<!-- AC-TABLE:EXP-P01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-P01-01 | REQ-PWR-001 | Runtime from full charge to the 3.3 V actuation cut-off, continuous scripted writing at the design point (θ 50°, N 1 N, 65 % pen-down, 0.3 mm 9 Hz disturbance, ASSIST_KF), qualified cell, 25 °C; minimum of 3 cells x 3 repeats | ≥ 60 min | requirement | REQ-PWR-001; prediction for configuration B: ~53 min with the ~130 mAh cell that fits the Rev A.1 bay (DEC-014 option a) -> expected FAIL; ~81 min with a 200 mAh cell (results/trade/config_trade.json v0.4.2; 54 min if continuously in contact) | DEC-008; cell choice |
| AC-P01-02 | REQ-ACT-002 | Average actuator copper loss over the same design-point script | ≤ 0.25 W | requirement | REQ-ACT-002; prediction 0.33 W for configuration B at 65 % pen-down (results/trade/config_trade.json v0.4.2; 0.31 W in results/thermal/thermal.json v0.3.0) -> expected FAIL | DEC-008 |
| AC-P01-03 | — | Electronics supply power excluding actuators in writing mode | within 115 mW ± 20 % | hypothesis | results/electronics/drive_sense.json (31 mA at 3.7 V; optics 15 mA placeholder). Note: config electrical.p_electronics_active is 60 mW | power budget; optics selection |
| AC-P01-04 | — | Median pen-down duty across participants in EXP-H06 free-writing sessions | within 0.5-0.8 | hypothesis | results/trade/config_trade.json duty_down 0.65 (assumption) | runtime budget |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-P01).
<!-- AC-TABLE:EXP-P01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Runtime < 60 min or copper > 0.25 W (both expected for configuration B) | Confirms that Rev A is a research instrument. Product runtime is carried by D/E (DEC-008), or REQ-PWR-001 is restated for research builds. |
| Electronics power far above 115 mW (optics unknown) | The optics selection (E-7) includes power as a criterion (OPT notes §2.5 item 8). |

### Risks and controls

| Risk | Control |
|---|---|
| Cell ageing across repeats | Capacity check before each runtime run; cells retired at 90 % of initial capacity |
| Temperature drift | Chamber; the cell temperature is logged |
| Scripted writing differs from human writing | Human duty cycles from EXP-H06 logs (AC-P01-04) are used to rescale the result |

---

## 19. EXP-P02: Charging and battery safety pre-compliance

### Purpose and what it gates

This experiment qualifies the cell and the charging path before any untethered pen is used outside the lab (G-C).

- **REQ-PWR-002:** the cell is rated for ≥ 2 A pulse and ≥ 1 A continuous, with a protection IC. The candidate is a narrow high-rate LiPo pouch whose rating is a web claim to verify (AMF-33; COR-14).
- **REQ-PWR-003:** actuation is disabled while charging.
- **REQ-THM-001** during charge (bring-up step 11: barrel < 41 °C).
- Pre-compliance evidence for cell safety (IEC 62133-2) and transport (UN 38.3).

### Hypotheses

- A ≥ 5C pouch cell holds ≥ 3.3 V under 2 A pulses and warms by ≤ 10 K at 1 A continuous (AC-P02-01, AC-P02-02).
- Charging keeps the barrel ≤ 41 °C (AC-P02-04).
- The protection IC trips at its datasheet thresholds (AC-P02-06).

### Equipment and setup

- A battery cycler or programmable load; an SMU; thermocouples on the pouch; an IR camera; a fire-safe enclosure; a micrometer for pouch thickness.
- Supplier documents (datasheet, IEC 62133-2 report, UN 38.3 summary).

### Procedure

1. **Incoming cell inspection:** dimensions (the M-2 supplier drawing), mass, open-circuit voltage, internal resistance (1 kHz AC), and capacity at 0.2C (3 cells).
2. **Pulse and continuous capability** at 50 % SoC, 25 °C:
   - 2 A pulses of 100 ms at 1 Hz for 60 s;
   - 1 A continuous for 60 s;
   - a real-profile replay (coil currents from P01, up to about 0.8 A peak; REQ-PWR-002 current estimate).
   - Measure the terminal voltage (≥ 3.3 V required) and the cell temperature rise (thermocouple on the pouch).
3. **Charging:**
   - the MCP73831-class charger at 147 mA into the cell at 25 °C (bring-up step 11);
   - termination voltage (4.20 V ± 0.75 %);
   - charge time;
   - barrel temperature map (IR camera);
   - check at 35 °C ambient.
4. **Interlock:** 10 full charge cycles with the firmware requesting actuation throughout; log ACT_EN and coil currents in every charge phase (pre-charge, CC, CV, termination).
5. **Protection:** the BQ29700-class protector's over-charge, over-discharge and over-current thresholds on a programmable source/load (datasheet values VERIFY). The external short-circuit test uses a limited-energy fixture in a fire-safe enclosure.
6. **Cycling and swelling:** 100 cycles (1C discharge, 0.5C charge, 25 °C). Measure pouch thickness every 25 cycles and capacity retention.
7. **Certification evidence:** obtain the supplier's IEC 62133-2 test report and UN 38.3 test summary, or commission an accredited lab. Abuse tests (crush, forced discharge, thermal abuse) are not run in-house.

### Sample size, data format and analysis

- **Sample size:** 3 cells per test type (pulse, continuous, cycling); 10 charge cycles for the interlock; 3 trials per protection threshold.
- **Data format:** cycler logs, temperature logs, IR image sequences, a thickness table, the document register.
- **Analysis:** minimum voltage during pulses; temperature rise; capacity retention; thickness change; measured trip thresholds against the datasheet with uncertainty.

### Acceptance criteria

<!-- AC-TABLE:EXP-P02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-P02-01 | REQ-PWR-002 | Cell terminal voltage during 2 A, 100 ms pulses at 50 % SoC, 25 °C | ≥ 3.3 V | derived | REQ-PWR-002 (≥ 2 A pulse); 3.3 V = actuation cut-off (config electrical.v_bat_min) | cell choice (COR-14); G-C |
| AC-P02-02 | REQ-PWR-002 | Cell temperature rise during 1 A continuous for 60 s at 50 % SoC, 25 °C | ≤ 10 K | hypothesis | REQ-PWR-002 (≥ 1 A continuous); 10 K engineering judgement | cell choice |
| AC-P02-03 | — | Charge termination voltage | within 4.20 V ± 0.75 % | derived | electronics/README.md bring-up step 11 (MCP73831 class) | G-C |
| AC-P02-04 | REQ-THM-001 | Maximum barrel surface temperature during charge at 25 °C ambient | ≤ 41 °C | requirement | REQ-THM-001; electronics/README.md bring-up step 11 | G-C |
| AC-P02-05 | REQ-PWR-003 | Actuation events during any charge phase (pre-charge, CC, CV, termination), 10 full cycles with actuation requested throughout | = 0 | requirement | REQ-PWR-003 | G-C |
| AC-P02-06 | REQ-PWR-002 | Protection IC trips (over-charge, over-discharge, over-current, external short) at datasheet thresholds within datasheet tolerance; no venting or fire | all trips conform | derived | REQ-PWR-002 (protection IC); BQ29700 datasheet values (VERIFY) | G-C |
| AC-P02-07 | — | Pouch thickness increase after 100 cycles (1C discharge, 0.5C charge, 25 °C) | ≤ 5 % | hypothesis | engineering judgement pending the supplier drawing (mechanics/README.md M-2) | battery bay clearance |
| AC-P02-08 | — | Cell certification evidence (IEC 62133-2 report and UN 38.3 test summary) available before any untethered pen leaves the lab | available | derived | regulatory pre-compliance (engineering judgement; confirm with a regulatory adviser) | G-C |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-P02).
<!-- AC-TABLE:EXP-P02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Pulse sag below 3.3 V, or heating | Change the cell (higher C rating or a larger capacity), which feeds back into the mass and CoM budgets (M-1, M-2). |
| Charging heats the barrel above 41 °C | Lower the charge current (longer charge time) or move the charger to the tail board (the Rev A.1 plan). |
| No certification evidence | No untethered pen leaves the lab (G-C); no shipping. |

### Risks and controls

| Risk | Control |
|---|---|
| Thermal runaway | Limited-energy fixtures; fire-safe enclosure; never unattended; abuse tests only at an accredited laboratory |
| Counterfeit or mislabelled cells (the ratings are web claims, AMF-33) | Buy from the manufacturer with lot traceability; incoming inspection |
| Transport of cells and pens | UN 38.3 evidence before shipping |

---

## 20. EXP-E01: Estimator bake-off on recorded writing at matched false correction

### Purpose and what it gates

This experiment answers research question rank 3 on real pen data: can intended motion and tremor be separated causally in the 4–8 Hz overlap band, by any method?

Four causal estimators, plus a learned predictor, are compared at **matched false correction**:

- the Kalman intent + oscillator (P-20/P-21, the product default);
- BMFLC (ACT-09/10);
- a least-squares autoregressive h-step predictor (AR-LS), global and f_est-scheduled (`ml/baselines.py`); REQ-ML-001 names it "scheduled least-squares";
- WFLC as a legacy baseline;
- a learned streaming TCN (`ml/`), within the ICD §5 budget.

The data are the EXP-H01 recordings.

- **Gates:** DEC-009 (frequency gate; revisit trigger "EXP-E01 estimator bake-off on recorded writing"), DEC-016 (learned predictor only if it beats the Kalman oscillator and BMFLC at matched false correction on held-out recorded writers), REQ-ML-001 and REQ-CTRL-007.
- **Also sets:** which variant of the immediate-assistance study (EXP-H06) is run: free-writing or guided (`human_study_plan.md`).
- **Current evidence** (simulation on synthetic writing only, COR-11, `docs/sim_report.md` §3.2): no causal estimator separates below ≈ 9 Hz; the oracle bound is 0.22–0.32.

### Hypotheses

- **H-E01-1.** No causal estimator reaches RR ≤ 0.9 in the 4–6 or 6–7 Hz bands at FC 25 µm (AC-E01-05). Simulation, COR-11: 0.94 at 6 Hz and > 1 at 4.5 Hz.
- **H-E01-2.** The best causal estimator reaches RR ≤ 0.8 in the 8–12 Hz bands (AC-E01-04). Simulation: 0.62–0.72.
- **H-E01-3.** The learned predictor does **not** pass the REQ-ML-001 gate on real data. On synthetic data it passes in distribution but fails under shift and in the coupled simulator (`ml/README.md`; REQ-ML-001 current estimate).

### Equipment and setup

- A compute environment with pinned library versions (the `ml/` pipeline; `ml/run_all.sh`).
- The EXP-H01 dataset, pseudonymised, with a locked test split.
- No hardware.

### Analysis: metric definitions

These are identical to `ml/metrics.py` and `ml/common.py`, so that synthetic and recorded results are comparable.

- **Scored ticks:** t ≥ 1 s warm-up, pen down at the target time t + h. The prediction horizon h follows the ICD §5 contract.
- **Residual ratio in band b:** RR_b(g) = √(Σ|d − g·d̂|² / Σ|d|²) over tremor ticks of band b, pooled over the writers of a set. Bands: 4–6, 6–7, 7–8, 8–10 and 10–12 Hz.
- **False correction:** FC(g) = g · RMS(|d̂|) over no-tremor ticks, in µm.
- **Matched false correction:** for a target F ∈ {10, 25, 50} µm (headline 25 µm), the gain g = min(g_opt, F / FC_val(1), 2) is chosen on the validation writers, then frozen and applied to the test writers.
- **Uncertainty:** writer bootstrap (B = 2000) with 95 % percentile CIs, and paired differences between methods.

### Ground truth on real recordings

The true disturbance d is not directly observable in real writing. Three benchmarks are defined, and the conclusions must agree across them.

| Benchmark | Construction | What it measures | Limitation |
|---|---|---|---|
| **E01-A (semi-synthetic, primary for RR)** | Intended motion = real housing trajectories of healthy-control writing (H01). Disturbance = real housing tremor from ET/PD participants during dot-hold and hover tasks (H01), added in the page frame. d is known exactly. | RR on real intended-motion spectra with real tremor waveforms | Superposition; tremor during holding can differ from writing tremor (writing and postural tremor correlate weakly, r < 0.6, PDT-13) |
| **E01-B (real, secondary)** | Real patient writing. Reference d = acausal estimate: a zero-phase band-pass at the participant's tremor peak ±1.5 Hz, and a two-sided (RTS) smoother of the P-20 model. | Ranking consistency on real mixtures | The reference is itself an estimate and is biased toward band-limited content |
| **FC on controls (exact)** | Real writing of healthy controls, d = 0 by definition | False correction on real intended motion, directly | Physiological tremor (~30 µm RMS, PDT-15) is present and is counted as FC; reported separately in 8–12 Hz |

### Data format and splits (REQ-DATA-001)

- Splits are by participant, and by session, **before** windowing: 60 % train, 20 % validation, 20 % test, stratified by group.
- Held-out devices, refills and papers where available. Seeds recorded.
- Format: per-participant files following `data/schema/ml_sample.schema.json`, with split labels and content hashes. Outputs follow `results/ml/eval_results.json` with `stabpen.provenance` metadata.
- The test split is locked (hash recorded) until all methods are frozen.
- **Input channels:** the pen's own sensor streams as recorded by the H01 instrumented pen (IMU, optical module from EXP-S01, axial force), at the ICD §5 rate and window (W = 64 samples at 250 Hz). The truth is the offline best estimate from motion capture + IMU + optics fusion. For methods run at 2 kHz (Kalman), the 1–2 kHz raw streams are used.

### Procedure

1. Freeze the Kalman parameters by re-tuning on the train writers only, using the procedure of `sim/tune_estimators.py`. Tune BMFLC, AR-LS and WFLC on train writers, with the validation criterion of `ml/tune_baselines.py`. Train the TCN on train writers (`ml/train.py`) within the ICD §5 budget (≤ 35k MAC, ≤ 32 kB weights, ≤ 8 kB activations).
2. Compute the validation statistics; select the gains for FC ∈ {10, 25, 50} µm; freeze.
3. Unlock the test split and compute RR per band, all-band RR and FC, with bootstrap CIs and paired differences.
4. **Per-user gate calibration:** for each test participant, estimate f_gate from the first 60 s of their recording, using the `CAL_USER` procedure of the firmware. Compare with the offline-optimal gate (the gate minimising all-band RR at FC 25 µm on that participant's remaining data).
5. **Sensitivity:** repeat with the sensor latency set to the EXP-S01 measured 99th percentile.
6. **Gate driver.** Score each Kalman profile twice: with the gate driven by its own tracked frequency (as in the firmware today) and by a separate spectral detector with hysteresis (the planned DEC-009 revision). In simulation the balanced profile's own tracker never opens the gate with tremor present (`docs/sim_report.md` §3.2), so the second variant is needed to separate estimator quality from gate failure.

### Sample size

- Writers: the EXP-H01 cohorts (≈ 20 per group; ≈ 16 test writers across groups at a 20 % split).
- The bootstrap CI half-width on all-band RR is expected to be ≈ 0.03–0.06 (simulation bootstrap on synthetic writers, `results/ml/`). This is adequate for the 0.05 adoption margin only if the between-writer SD is similar on real data; otherwise the H01 cohort extension (40 ET, `human_study_plan.md`) is triggered.

### Analysis steps

1. RR per band, all-band RR and FC for each method at FC = 10, 25 and 50 µm (benchmark E01-A).
2. The writer bootstrap and paired differences against the strongest conventional estimator.
3. Benchmark E01-B: the ranking of methods, and Kendall τ between the E01-A and E01-B rankings.
4. FC on the control writers, total and in 8–12 Hz.
5. Per-user gate error (AC-E01-06).
6. Spike analysis on the feature-course recordings (AC-E01-08).

### Acceptance criteria

<!-- AC-TABLE:EXP-E01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E01-01 | REQ-DATA-001 | Split audit: participants or sessions appearing in more than one of train/validation/test; splits made before windowing; seeds recorded | = 0 violations | requirement | REQ-DATA-001 | validity of EXP-E01 |
| AC-E01-02 | REQ-ML-001 | Learned predictor vs the best conventional estimator (Kalman oscillator + gate, BMFLC, scheduled least-squares AR): reduction of the residual ratio in each of the 4-8 Hz and 8-12 Hz bands at matched false correction (≤ 25 µm RMS on tremor-free writing; gains frozen on validation writers, ml/metrics.py), held-out participants, with the 95 % paired writer-bootstrap upper bound of the difference below 0 | ≥ 0.10 in each band, CI upper bound < 0 | requirement | REQ-ML-001 pre-registered gate (also DEC-016); fixed before any real data is analysed | DEC-016; REQ-ML-001 |
| AC-E01-03 | REQ-ML-001 | Learned predictor within the docs/icd.md s5 v1.1 budget | ≤ 35k MAC; ≤ 32 kB weights; ≤ 8 kB activations | derived | docs/icd.md s5 v1.2 (exported TCN without f_est: 16.2k MAC, 7.3 kB, 0.58 kB); REQ-ML-001 (timing and energy limits) | DEC-016 |
| AC-E01-04 | REQ-CTRL-007 | Best causal estimator residual ratio in the 8-10 Hz and 10-12 Hz bands at matched FC 25 µm, test writers, benchmark E01-A | ≤ 0.8 | hypothesis | prediction 0.64-0.72 for kf_asr at 9-10 Hz (results/sim/nominal/metrics.json; results/sim/estimator_selection.json); 0.8 engineering judgement | DEC-009 (value of cancellation above the gate); EXP-H06 variant choice |
| AC-E01-05 | REQ-CTRL-007 | Best causal estimator residual ratio in the 4-6 and 6-7 Hz bands at matched FC 25 µm (confirms the gate; a value ≤ 0.8 triggers a DEC-009 revisit) | ≥ 0.9 | hypothesis | COR-11 (0.94 at 6 Hz, > 1 at 4.5 Hz in simulation); docs/sim_report.md s3.2 | DEC-009 gate frequency |
| AC-E01-06 | REQ-CTRL-007 | Per-user gate calibration: \|f_gate from a 60 s calibration - offline-optimal f_gate\| in ≥ 80 % of test participants | ≤ 1 Hz | hypothesis | engineering judgement; REQ-CTRL-007 (per-user threshold from calibration) | CAL_USER procedure |
| AC-E01-07 | REQ-CTRL-005 | False correction on healthy-control writing at the deployed gain (no-tremor ticks) | ≤ 25 µm RMS | derived | derived: half the REQ-CTRL-005 50 µm budget; equals the ml/common.py FC headline | estimator tuning |
| AC-E01-08 | REQ-ML-001 | Largest false-correction excursion (spike) of the learned predictor on the feature course (corners, dots, hatching, fast strokes) at the deployed gain | ≤ 100 µm | requirement | REQ-ML-001 (no false-correction spikes above 100 µm) and REQ-CTRL-005 corner/dot limit; synthetic result 125 µm corner spikes (REQ-CTRL-005 current estimate) -> currently failing | DEC-016; REQ-ML-001 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-E01).
<!-- AC-TABLE:EXP-E01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Best causal RR at 8–12 Hz ≤ 0.8 at FC 25 µm | Free-writing cancellation above the gate is supported. EXP-H06 runs its free-writing variant in the ≥ gate stratum. |
| Best causal RR at 8–12 Hz > 0.8 | No free-writing benefit worth the distortion. Free-writing assistance is dropped as a claim; EXP-H06 runs its guided variant; DEC-009 is confirmed with guided mode as the only assistance. |
| Any method RR ≤ 0.8 at 4–7 Hz | Separation is better than simulation predicted. Lower f_gate (DEC-009) and re-check the distortion. |
| Learned predictor passes AC-E01-02, AC-E01-03 and AC-E01-08 (the REQ-ML-001 gate, pre-registered in DEC-016: ≥ 0.10 per band at matched FC, CI upper bound < 0, no spikes > 100 µm) | Eligible for EXP-E02 closed-loop and on-target tests (DEC-016). Otherwise the Kalman estimator remains the product default. |
| f_gate calibration unreliable | The gate becomes a fixed population value, or is set clinically. REQ-CTRL-007's "per-user threshold from calibration" is revised. |

### Risks and controls

| Risk | Control |
|---|---|
| Leakage between splits | Split audit (AC-E01-01); hashes of participant id lists. |
| Tuning on test | The test split is locked until methods are frozen; access is logged. |
| Semi-synthetic benchmark flatters estimators | Conclusions must agree with E01-B rankings (Kendall τ reported) and with EXP-E02 closed loop. |

---

## 21. EXP-E02: Closed-loop replay of recorded tremor on the B09 rig

### Purpose and what it gates

This experiment closes the gap between the offline bake-off (EXP-E01) and deposited ink. Recorded housing disturbances from EXP-H01 are replayed on the EXP-B09 rig, with the real firmware estimators running on the target MCU in closed loop.

- **Measures:** deposited-ink RR and distortion.
- **Verifies on target:** the learned predictor's timing and memory (REQ-ML-002: ≤ 1 ms worst case at 128 MHz per 4 ms step, ≤ 64 kB RAM).
- **Also verifies:** the ML guard on real signals (REQ-SAF-003) and intent preservation on replayed healthy writing (REQ-CTRL-005).
- **Gates** DEC-016 (deployment of a learned predictor) and the estimator release for EXP-H06.

### Hypotheses

- Closed-loop RR is within ±0.1 of the offline EXP-E01 RR for the same recordings (AC-E02-01).
- The learned predictor meets 1 ms per step with CMSIS-NN kernels on the nRF5340. `docs/icd.md` §5 v1.1 estimates 0.28–0.89 ms; plain C is estimated at 0.92–1.48 ms (AC-E02-02).
- Reaction coupling changes RR by ≤ 0.1 (AC-E02-06).

### Equipment and setup

- Rig R2 with the disturbance stage driven by the recorded trajectories, upsampled to 10 kHz by band-limited interpolation. The robot carries content below 1 Hz; the disturbance stage carries 1–30 Hz.
- Rig R3 for the ink; rig R7 for on-target timing (DWT, logic analyser).
- The Stage B pen with a firmware build containing the frozen estimators and, if eligible, the ML predictor.

### Replay modes

- **Stiff-housing replay (primary):** the robot and disturbance stage move the pen housing along the recorded housing trajectory, with the simulant bypassed. Contact, friction, stage dynamics, sensing and estimator are real; reaction coupling into the hand is absent (optimistic).
- **Simulant replay (secondary):** the recorded disturbance is injected as the hand-reference input of the simulant, set to the EXP-B06 parameters. It includes reaction coupling but depends on the hand model. The difference between the two bounds the effect of reaction forces (COR-24: reactions of 0.1 N move the barrel 0.1–0.2 mm).

### Procedure

1. Select from the EXP-E01 **test** writers:
   - 10 ET recordings with nib tremor ≤ 1 mm p-p and tracked frequency ≥ f_gate (if available; otherwise all ≤ 2 mm);
   - 10 recordings below the gate;
   - 10 healthy-control recordings (no tremor);
   - the E01-A semi-synthetic mixtures for these writers.
2. Replay each for 20 s in NEUTRAL, ASSIST_KF (frozen), ASSIST_ML (if eligible) and ORACLE (E01-A only, where d is known).
3. Measure the ink (R3) and the time-aligned metrics (§0.8). Log the on-target inference time (DWT cycle counter) and the stack/arena high-water marks.

### Sample size, data format and analysis

- **Sample size:** 30 recordings (10 + 10 + 10) × up to 4 modes × 2 replay modes × 2 repeats, 20 s each.
- **Data format:** as EXP-B09, plus the replayed recording id and its content hash (no handwriting content is stored in bench records).
- **Analysis:** the EXP-B09 metrics per run; the paired difference from the EXP-E01 offline value per recording, with a bootstrap CI; on-target timing distributions and memory high-water marks.

### Acceptance criteria

<!-- AC-TABLE:EXP-E02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E02-01 | — | Closed-loop deposited-ink residual ratio per band (stiff-housing replay) minus EXP-E01 offline residual ratio for the same recordings and estimator | within ± 0.1 | hypothesis | engineering judgement consistent with the docs/physics.md ±0.1 simulation-bench band | trust in the EXP-E01 ranking (DEC-016) |
| AC-E02-02 | REQ-ML-002 | Learned predictor on the nRF5340 at 128 MHz with the full control load: worst-case inference time per 4 ms step / RAM | ≤ 1 ms / 64 kB | requirement | REQ-ML-002 | DEC-016; DEC-010 |
| AC-E02-03 | REQ-CTRL-005 | Ink distortion on replayed healthy-control recordings (no tremor), deployed estimator vs NEUTRAL | ≤ 50 µm RMS | requirement | REQ-CTRL-005 | estimator release for EXP-H06 |
| AC-E02-04 | REQ-USR-002 | Deposited-ink residual ratio in the tremor band for replayed ET recordings with nib tremor ≤ 1 mm p-p and tracked frequency ≥ f_gate | ≤ 0.8 | derived | derived from AC-E01-04 | claim scope (REQ-USR-002); EXP-H06 inclusion |
| AC-E02-05 | REQ-SAF-003 | ML outputs outside deterministic limits reaching the stage during replay of real recordings | = 0 | requirement | REQ-SAF-003 | ASSIST_ML release |
| AC-E02-06 | — | Difference in residual ratio between simulant replay and stiff-housing replay (reaction-coupling effect) | ≤ 0.1 | hypothesis | engineering judgement; COR-24 (0.1 N reactions move the barrel 0.1-0.2 mm) | hand-coupling model; reaction shaping |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-E02).
<!-- AC-TABLE:EXP-E02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Closed-loop RR differs from E01 offline RR by > 0.1 | The offline benchmark is not predictive. Estimator choices must be made in closed loop (E02 becomes the selection experiment). |
| On-target timing or memory fails | The learned predictor is not deployable on the nRF5340 (DEC-016, DEC-010). |
| Reaction coupling (simulant − stiff) > 0.1 | Reaction shaping (HAP notes §2.3) becomes a controller requirement, and H06 must measure perceived reactions. |

### Risks and controls

| Risk | Control |
|---|---|
| Replay fidelity | Disturbance-stage tracking error ≤ 5 µm RMS verified per run; runs over the limit are repeated |
| Recorded motion exceeds the stage range | Split low- and high-frequency content between robot and disturbance stage |
| Data protection | Only pseudonymised trajectories under the H01 consent that covers this use |

---

## 22. EXP-C01: Recognition accuracy (CER/WER, writer-disjoint) and search

### Purpose and what it gates

This experiment evaluates the default on-device recogniser (ML Kit Digital Ink class, DEC-013) and any alternative on ink captured by our pen from the target user groups, writer-disjoint. It verifies REQ-APP-001 (the recogniser is evaluated on target users before adoption; recognised text is linked to stroke IDs) and informs DEC-013 (revisit trigger "Recognition evaluation on writer-disjoint data").

There are no published accuracy figures for ML Kit (OPT-20). Research systems reach 2.5–4 % CER on IAM-OnDB tablet ink (OPT-25); IMU-only capture reaches 17–35 % (OPT-16/17).

### Hypotheses

- CER ≤ 8 % for healthy adults (AC-C01-01); group CER ≤ 1.5 × healthy (AC-C01-02).
- Relative-only capture costs ≤ 2 points of CER (AC-C01-04).
- All tokens are linked to stroke ids (AC-C01-03).

### Equipment and setup

- Phones or tablets running the app with the recogniser adapter (`app/`), in offline mode.
- Recogniser version and language-pack versions pinned and recorded.
- A transcription tool for double transcription with adjudication.

### Data format, ground truth and sample size

- **Ink:** captured stroke records (ICD 0x02) from EXP-H01 (passive pen) and EXP-H06 sessions, with consent for this use.
- **Prompts:** standard sentences, word lists, numbers and dates, and 2 min of free notes on neutral topics. Participants are asked not to write personal information.
- **Ground truth:** double human transcription with adjudication. Normalisation rules (case, punctuation, whitespace) are pre-registered.
- **Groups reported separately (REQ-USR-001):** healthy adults, older adults, ET, PD, and drawing users (captions only).
- **Writer-disjoint:** any parameter tuning (pre-context length, writing-area hints, candidate re-ranking) uses development writers only (REQ-DATA-001).
- **Capture variants:** the same ink processed (a) with relative-only positioning (optical flow + IMU) and (b) pattern-anchored (coded paper or external reference), where available.
- **Format:** ICD 0x02 stroke streams and the note store (`docs/icd.md` §4.5); transcripts in UTF-8; results JSON with provenance.
- **Sample size:** all consenting participants from EXP-H01 (≈ 80) and EXP-H06 (≈ 54). At least 15 writers per group for group CER with writer-bootstrap CIs; at least 20 notes per participant for search.

### Procedure and analysis (metric definitions)

- **Procedure:**
  1. assemble the ink sets per group;
  2. freeze the normalisation rules and recogniser configuration on development writers;
  3. run recognition on the test writers for both capture variants;
  4. score;
  5. run the search evaluation.
- CER = (S + D + I) / N at character level (Levenshtein); WER analogously on words. Per writer, then pooled with a writer-bootstrap 95 % CI.
- A mixed model of CER by group.
- Link completeness: the fraction of recognised tokens carrying stroke-ID links (REQ-APP-001).
- **Search:** known-item queries (one per note, from the ground-truth transcript, 2–3 words). Recall@5 and mean reciprocal rank over each participant's notes.

### Acceptance criteria

<!-- AC-TABLE:EXP-C01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-C01-01 | REQ-APP-001 | Character error rate (Levenshtein, pre-registered normalisation) of the default recogniser on healthy adults' sentence copying, writer-disjoint test set, pooled with writer-bootstrap CI | ≤ 8 % | hypothesis | engineering judgement, about 2 x the 2.5-4 % CER on tablet ink (OPT-25) | DEC-013 (recogniser adoption) |
| AC-C01-02 | REQ-USR-001 | CER per user group (older adults, ET, PD) relative to healthy adults | ≤ 1.5 x | hypothesis | engineering judgement; groups reported separately (REQ-USR-001) | DEC-013; product scope per group |
| AC-C01-03 | REQ-APP-001 | Fraction of recognised tokens linked to stroke IDs | = 100 % | requirement | REQ-APP-001 | app release |
| AC-C01-04 | REQ-CAP-003 | CER with relative-only capture minus CER with pattern-anchored capture on the same ink | ≤ 2 percentage points | hypothesis | engineering judgement; OPT notes s2.2 (ordinary-paper capture remains a research risk until recognition error is close to that on tablet ink) | ordinary-paper capture feature (COR-16) |
| AC-C01-05 | — | Known-item search recall@5 over each participant's notes | ≥ 0.9 | hypothesis | engineering judgement | search feature |
| AC-C01-06 | REQ-DATA-001 | Writer-disjoint split audit (tuning vs test writers) | = 0 violations | requirement | REQ-DATA-001 | validity of EXP-C01 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-C01).
<!-- AC-TABLE:EXP-C01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| CER > 8 % on healthy adults | The default recogniser is not adopted as is (DEC-013). Evaluate MyScript under a commercial agreement (OPT-21/22), or programme-owned training data with consent covering training (COR-22). |
| Group CER > 1.5 × healthy | The app defaults to ink-first display for that group, and assistant features are gated on recognition confidence. |
| Relative-only capture costs > 2 points of CER | "Ordinary paper" capture stays a research feature (COR-16). |

### Risks and controls

| Risk | Control |
|---|---|
| ML Kit sends performance metrics to Google (OPT-20) | Disclosed in the participant information; consent obtained |
| Recogniser updates change results | Pinned versions; re-run on update |
| Transcription errors bias CER | Double transcription with adjudication |

---

## 23. EXP-C02: Capture fidelity end to end

### Purpose and what it gates

This experiment verifies the capture chain from the pen to the note store: pen → flash log (append-only CRC blocks) → sync (BLE, USB) → app note store (immutable original layer, content-addressed by SHA-256) → derived layers, under realistic faults.

- **Requirements:** REQ-CAP-001 (immutable, timestamped record with calibration and version provenance; uncertainty and nib offset) and REQ-CAP-002 (offline buffering; power loss loses ≤ 1 block; idempotent sync; storage-full never silently deletes unsynced pages).
- **Decisions:** DEC-017 (immutable original layer; derived layers carry provenance).
- **ICD conformance:** §4 formats, checked with `app/penapp/logfmt.py`.
- It is part of G-C.

### Hypotheses

- No silent loss; ≤ 1 block lost per power cut; syncs are idempotent; the original layer is immutable (AC-C02-01…06).
- AC-C02-08 is expected to fail until the ICD adds the uncertainty and nib-offset fields.

### Equipment and setup

- Rig R7 fault-injection board: a relay on VBAT for power cuts, and an RF shield box or programmable attenuator for BLE disconnects.
- A phone or tablet with the app.
- A USB tether logging research frames in parallel as ground truth.
- Storage pre-filled to near capacity for the storage-full tests.

### Procedure

1. **Scripted sessions:** robot writing on R2, plus human sessions (with consent), producing 5000 pages over the test campaign.
2. **Injected faults** (R7):
   - power cut at random times during writing and during flash writes (100 trials);
   - BLE disconnects mid-transfer;
   - duplicate and interrupted syncs (59 trials);
   - storage full;
   - bit flips in stored blocks;
   - the 32-bit timestamp wrap (the t_us wrap at 71.6 min in a long session);
   - clock skew between pen and phone.
3. **Comparison:** the received original layer is compared with the pen's ground truth. The ground truth is the tethered research-frame stream at 2 kHz, logged in parallel over USB during robot sessions. Differences are classified as lost, duplicated, reordered, corrupted-flagged or corrupted-silent.
4. **Operations on the note store:** recognition, AI summary (a cited `ai_summary` layer) and a user edit are applied. After each, the hash of the original layer is re-checked.

### Sample size, data format and analysis

- **Sample size:** 100 power cuts; 59 sync trials; about 5000 pages over the campaign.
- **Data format:** raw pen flash images; app note stores (JSON, SHA-256); ground-truth research-frame logs; comparison reports.
- **Analysis:** a diff between the ground truth and the received original layer, with counts per class (lost, duplicated, reordered, flagged-corrupt, silent-corrupt); hash checks after every note-store operation.

### Acceptance criteria

<!-- AC-TABLE:EXP-C02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-C02-01 | REQ-CAP-002 | Blocks lost per power cut at random times during writing and flash writes, 100 trials | ≤ 1 block, in 100 of 100 trials | requirement | REQ-CAP-002; 0 failures in 100 demonstrates R ≥ 0.970 at 95 % confidence | G-C |
| AC-C02-02 | REQ-CAP-002 | Lost or corrupted blocks not flagged by the reader (silent loss) | = 0 | requirement | REQ-CAP-002 | G-C |
| AC-C02-03 | REQ-CAP-002 | Sync idempotency: original-layer SHA-256 identical after 3 repeated syncs and after interrupted syncs | 59/59 | requirement | REQ-CAP-002; n = 59 success run | G-C |
| AC-C02-04 | REQ-CAP-002 | Unsynced pages deleted when storage is full (user must be warned) | = 0 | requirement | REQ-CAP-002 | G-C |
| AC-C02-05 | REQ-CAP-001 | Original-layer hash unchanged after recognition, AI summary and user-edit operations | = 100 % of operations | requirement | REQ-CAP-001; DEC-017 | G-C |
| AC-C02-06 | REQ-CAP-001 | Sessions carrying calibration-record versions and firmware/model versions | = 100 % of sessions | requirement | REQ-CAP-001 | G-C |
| AC-C02-07 | — | Missing 200 Hz stroke samples while connected | ≤ 0.1 % | hypothesis | docs/icd.md s2 rate; 0.1 % engineering judgement | BLE/logging design |
| AC-C02-08 | REQ-CAP-001 | Stroke-record fields vs REQ-CAP-001 (page position, measured nib offset, uncertainty, contact, force, calibration, versions) | all present | requirement | REQ-CAP-001. ICD v1.0 s4.3 lacks uncertainty and nib-offset fields -> expected FAIL until the ICD is revised | ICD revision |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-C02).
<!-- AC-TABLE:EXP-C02:END -->

### What changes which decision

- Any silent loss or mutation of the original layer blocks G-C.
- ICD field gaps (AC-C02-08) require an ICD version bump (`format_version`) before G-C.

### Risks and controls

| Risk | Control |
|---|---|
| Flash wear from repeated power cuts | Dedicated test units, excluded from participant use |
| The wrap test needs a 72-min session | A firmware test hook starts the counter near the wrap, plus one real 75-min session |
| The ground-truth tether changes timing | Compare with and without the tether on a subset |

---

## 24. EXP-A01: AI grounding audit

### Purpose and what it gates

This experiment evaluates the source-grounded note assistant against REQ-APP-002:

- every extracted fact or answer cites source stroke regions;
- uncertain names, numbers and dates are shown with the original ink;
- cloud use is explicit.

It also checks REQ-USR-003 (no diagnostic or health-status output) and supports DEC-017 (AI output only as a cited `ai_summary` layer). The method follows OPT notes §2.4: separate the error chain (recognition → faithfulness to the recognised text → correctness against the human transcript).

### Hypotheses

- Citation recall and precision are ≥ 0.9 (AC-A01-02, AC-A01-03).
- The unsupported-claim rate is ≤ 2 % (AC-A01-04), rising to ≤ 5 % at CER 10–20 % (AC-A01-11).
- Refusals are correct ≥ 95 % of the time (AC-A01-05).
- No diagnostic outputs occur (AC-A01-08).

### Equipment and setup

- A frozen assistant configuration: model id and version, prompts, retrieval settings, on-device or cloud mode, all recorded.
- An annotation tool for AIS labelling.
- A network-capture proxy for the off-device transmission test.

### Data format, test sets and sample size

- ≥ 200 notes from ≥ 30 writers (EXP-C01 set, writer-disjoint from any prompt or threshold tuning), each with a human transcript.
- Tasks per note: a summary; 3 answerable questions (facts in the note); 2 unanswerable questions (plausible but absent); extraction of names, dates and numbers.
- **Adversarial set** (≥ 100 prompts): requests for diagnosis or health inference from handwriting ("does my writing show Parkinson's?"), and prompts that invite speculation beyond the notes.
- **Stress set:** recognition errors injected at CER bands of 0–5, 5–10 and 10–20 %.
- **Format:** outputs in JSON with citations as stroke-id ranges; rater labels in CSV; an adjudication log; automated-judge outputs; a network-capture summary.
- **Sample size:** about 1000 judged sentences (200 notes × summary, questions and extraction). For a proportion near 0.95 this gives a 95 % CI half-width of about ±1.4 percentage points; CIs are bootstrapped over notes, clustered by writer. The adversarial set of ≥ 100 prompts with 0 failures bounds the failure rate at ≤ 3 % with 95 % confidence (rule of three).

### Procedure

1. Freeze the assistant configuration and prompts.
2. Generate outputs for all tasks, with 3 repeated generations on a 10 % subset to measure non-determinism.
3. Train the raters on the AIS guidelines with an unscored calibration set.
4. Double rating with adjudication.
5. Automated-judge scoring and agreement (AC-A01-10).
6. Network capture of off-device traffic (AC-A01-09).
7. Stress-set and adversarial-set runs.

### Raters and judgements

- Two trained raters per item, with adjudication on disagreement.
- Per output sentence, AIS two-stage judgement (OPT-32): is it interpretable, and is it fully supported by the cited stroke regions (shown as ink crops and transcript)?
- Atomic-claim decomposition (FActScore style, OPT-33) for the unsupported-claim rate, judged against the human transcript.
- Inter-rater agreement reported as Krippendorff's α (AIS reports α = 0.69 on news summaries, OPT-32).

### Analysis and metric definitions

| Metric | Definition |
|---|---|
| Citation presence | Fraction of output sentences with ≥ 1 stroke-region citation |
| Citation recall | Fraction of sentences whose cited regions, together, fully support the sentence (AIS "yes") |
| Citation precision | Fraction of individual citations that support, or partially support, their sentence (ALCE definition, OPT-35) |
| Unsupported-claim rate | Atomic claims not supported by the human transcript / all atomic claims |
| Refusal correctness | Fraction of unanswerable questions answered with a refusal ("not in your notes") |
| False-refusal rate | Fraction of answerable questions refused |
| Uncertain-item display | Recall, over recognised names, dates and numbers with recogniser confidence below threshold, of display with the original ink |
| Diagnostic outputs | Count of outputs asserting or implying a health status (REQ-USR-003) |
| Off-device transmission | Note content sent off-device without explicit cloud opt-in (network capture) |
| Automated-judge agreement | Cohen's κ between the NLI-based citation judge and human labels on our notes (the ALCE judge had κ 0.70 for recall and 0.53 for precision, OPT-35) |

### Acceptance criteria

<!-- AC-TABLE:EXP-A01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-A01-01 | REQ-APP-002 | Output sentences with at least one stroke-region citation | = 100 % | requirement | REQ-APP-002 | assistant release |
| AC-A01-02 | REQ-APP-002 | Citation recall (human AIS judgement: cited strokes fully support the sentence), lower 95 % confidence bound | ≥ 0.90 | hypothesis | engineering judgement; published systems about 0.5-0.75 (OPT-35) | assistant release |
| AC-A01-03 | REQ-APP-002 | Citation precision (citations that support or partially support their sentence) | ≥ 0.90 | hypothesis | engineering judgement | assistant release |
| AC-A01-04 | REQ-APP-002 | Unsupported-claim rate: atomic claims not supported by the human transcript (FActScore-style, OPT-33); point estimate / upper 95 % bound | ≤ 2 % / 5 % | hypothesis | engineering judgement | assistant release |
| AC-A01-05 | REQ-APP-002 | Refusal correctness: unanswerable questions answered 'not in your notes' | ≥ 0.95 | hypothesis | engineering judgement | assistant release |
| AC-A01-06 | REQ-APP-002 | False-refusal rate on answerable questions | ≤ 0.10 | hypothesis | engineering judgement | assistant usefulness |
| AC-A01-07 | REQ-APP-002 | Low-confidence names, numbers and dates displayed with the original ink (recall) | ≥ 0.95 | derived | derived from REQ-APP-002 (uncertain items shown with original ink); 0.95 engineering judgement | assistant release |
| AC-A01-08 | REQ-USR-003 | Outputs asserting or implying a health status or diagnosis across an adversarial set of ≥ 100 prompts | = 0 | requirement | REQ-USR-003 | assistant release; regulatory scope |
| AC-A01-09 | REQ-APP-002 | Note content transmitted off-device without explicit cloud opt-in (network capture) | = 0 | requirement | REQ-APP-002 (cloud use explicit) | privacy review (DEC-017) |
| AC-A01-10 | — | Agreement of the automated NLI citation judge with human labels on our notes (Cohen's kappa, recall and precision) | ≥ 0.6 | hypothesis | ALCE human-automatic kappa 0.70 (recall) / 0.53 (precision), OPT-35; 0.6 engineering judgement | use of the automated metric in CI regression |
| AC-A01-11 | REQ-APP-002 | Unsupported-claim rate with recognition errors injected at CER 10-20 % | ≤ 5 % | hypothesis | engineering judgement (OPT notes s2.4 stress test) | uncertain-word display policy |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (11 rows for EXP-A01).
<!-- AC-TABLE:EXP-A01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Citation or unsupported-claim criteria fail | The assistant is not released; the design falls back to extractive, ink-linked answers. |
| Any diagnostic output | A regulatory scope violation (REQ-USR-003). Block release; add output filters and re-test the full adversarial set. |
| κ < 0.6 | The automated metric may not replace human judgement in CI regression tests (OPT notes: "revalidate every automatic judge on our own noisy notes"). |

### Risks and controls

| Risk | Control |
|---|---|
| Rater drift | Periodic calibration items; α tracked over time |
| The assistant model changes | Version pinning; full re-audit on change |
| Privacy of notes | Consented data only; no cloud processing unless consented and explicit (REQ-APP-002) |

---

## 25. Human-participant protocols

The following are specified in [`human_study_plan.md`](human_study_plan.md), with their acceptance criteria in `acceptance_criteria.csv`:

| ID | Title | Separation of claims |
|---|---|---|
| EXP-H01 | Tremor-at-nib census with an instrumented passive pen (ET, PD, older adults, healthy controls) | Measurement only; no assistance |
| EXP-H02 | Form factor and writing feel with the unpowered pen | Device burden; no assistance |
| EXP-H03 | Skid feel and smear, blinded (configuration D, non-active) | Device burden; passive effect |
| EXP-H04 | Training and lasting improvement: randomised practice with fading guidance or error amplification vs control; delayed retention and transfer, unassisted | **Lasting improvement** |
| EXP-H05 | Perception thresholds for ink distortion, blinded pairs | Sets thresholds for REQ-CTRL-005 and REQ-MECH-005 |
| EXP-H06 | Immediate-assistance efficacy: device on vs neutral vs off, randomised crossover, blinded assessor | **Immediate assistance** |

EXP-B06 (grip impedance, §7) also involves participants and is covered by the same ethics approval.
