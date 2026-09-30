# Bench protocols

**Status: PROPOSED PROCEDURES. No experiment in this file has been executed.** On 2026-09-27 the repository holds no bench measurement of any pen, rig, actuator, refill or person. Every number below is one of three things:

- a **prediction** from calculation or simulation, cited with its file and parameter version;
- a **literature value**, cited with its evidence id from `docs/evidence.csv`;
- an **acceptance criterion or hypothesis** with an id `AC-…` from [`acceptance_criteria.csv`](acceptance_criteria.csv), which states the source of the number.

Executed results will exist only as records under [`records/`](records/README.md). None exist yet.

Human-participant studies (EXP-H01…H06, and EXP-A02 for the pencil concept) are specified in [`human_study_plan.md`](human_study_plan.md). EXP-B06 involves participants, so it is covered by the same ethics approval, but its bench procedure is written here. Stage gates and the order of experiments are in [`prototype_stages.md`](prototype_stages.md).

Contents:

- §0 Conventions shared by every protocol (§0.11: pencil-class protocols)
- §1 Experiment index
- §2–§24 Protocols: B01–B10, S01–S02, F01–F02, M02–M03, P01–P02, E01–E02, C01–C02, A01
- §25 EXP-A03: autocorrect on real notes
- §26–§33 Pencil-class protocols (Rev P0): EXP-Q01…Q08
- §34 Pointers to the human-participant protocols
- §35 EXP-I01: grip compliance split (translation vs tilt), run inside EXP-B06 sessions
- §36 EXP-I04 (conditional): nib stage plus an inertial helper on the loaded rig (superseded by EXP-I06 for Rev H)
- §37–§39 Rev H (bigger grip, DEC-029): EXP-I05 active nose on the bench, EXP-I06 rear inertial module on a hand simulant, EXP-I07 tracker on recorded tremor writing
- §40 Guidance board (DEC-031): EXP-G01…G06
- §41 Rev J heel drive (DEC-037): EXP-D01…D07, D10, D12, D13 (the studies with people, D08, D09 and D11, are in `human_study_plan.md` §16)
- §42 Rev J inertial end-cap (DEC-038; since DEC-051 a bench comparison only): EXP-K01, K02, K04, K06, K07, K08 (K03 and K05 are in `human_study_plan.md` §17)
- §43 Rev J nose v2 and autowrite (DEC-036, DEC-039, DEC-041): EXP-N01…N08 (N09 and N10 are in `human_study_plan.md` §18); since DEC-050 the C1S nose is a bench research module, and autowrite a research mode with it
- §44 Simulator v2 validation (DEC-040): EXP-V01…V07, with the Rev H refill front stop (REQ-RVH-008) in EXP-V02, and small handwriting on a tablet (with participants) in EXP-V07
- §45 Rev J control stack (DEC-042): EXP-L01, L02, L04, L05 (L03, L06, L07 and L08 are in `human_study_plan.md` §19); EXP-L04 also times study E's real-data TCN (EXP-E14)
- §46 Rev J integrated layout (DEC-044): EXP-J01…J07; Rev J.1 (DEC-045): EXP-J10…J14, J16 and the wear part of EXP-J15; the nib's static load (DEC-046): EXP-J17 (J08, J09, J18 and J15's writers are in `human_study_plan.md` §20); the per-mode battery is AC-P01-06 in EXP-P01 (§18), against Rev K's REQ-RVK-002 since DEC-062; since DEC-050 the C1S parts are a bench research module, and EXP-J17's part (c) benches B1's counter-face (study B's EXP-B22) and, with study K's EXP-K23, Rev K's head (§53)
- §47 Measurement rigs R9–R14 (study M; DEC-058, DEC-059): EXP-T01…T17, where the existing experiments now run, and which proposed criteria were kept under existing ids; study B's EXP-B20, B21, B23, B24, B26, B27, B29 and B32 run inside EXP-T experiments (§51); EXP-T10 also measures the command path's lag (study E's EXP-E15), and EXP-T07 carries study K's EXP-K22 (Rev K's buildable coil)
- §48 Real recorded data (study R; DEC-054, DEC-055): EXP-R02, R04…R07 (R01 and R03 are in `human_study_plan.md` §21); study E did EXP-R05's retraining, and its test on new data is EXP-E10 (§52)
- §49 Spelling help, prediction and clearer handwriting (study S; DEC-056, DEC-057): EXP-S16, S19, S20, S21 (S10…S15, S17 and S18 are in `human_study_plan.md` §22)
- §50 Shifting the whole pen (study W; DEC-051…DEC-053): EXP-W11, W13, W14, W15, W17 (W10, W12 and W16 are in `human_study_plan.md` §23)
- §51 The balanced nib B1 (study B; DEC-050): EXP-B25, B28, B30, B31, and where study B's other experiments run (B22 is EXP-J17's part (c); B20, B21, B23, B24, B26, B27, B29 and B32 run inside EXP-T experiments); Rev K's C17200 wires are tested in EXP-K21 (§53)
- §52 A causal tremor tracker on real data (study E; DEC-060, DEC-061): EXP-E10, E11, E12, E13, E17, and where study E's other experiments run (E14 in EXP-L04, E15 in EXP-T10, E16 in EXP-W01 with people); study F ran EXP-E13 and E11 in simulation (§54)
- §53 The Rev K layout (study K; DEC-062…066): EXP-K20, K21, K23, K25, and where study K's other experiments run (K22 in EXP-T07; K24 with people, `human_study_plan.md` §24)
- §54 The readable target and where the gap lies (study F; DEC-067…069): EXP-E21, E22, E23, and where study F's other experiments run (E13 and E11 in §52; E20 with people, `human_study_plan.md` §25)
- §55 The first bench build (study H; DEC-095…099): EXP-BB01…BB09, the builds B0–B4 with their gates and weeks, and the existing experiments each build runs (EXP-T01, T02, T04, T05, T07, K20, K21 and EXP-J17 (c)); study U's EXP-U01…U09 are with people (`human_study_plan.md` §26)

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
| **R1 tribometer** | B01, B02, B08, Q01, Q02 | Pen holder on a goniometer (θ 35–80°, ≤ 0.1° resolution, verified under load with an inclinometer). Normal load by dead weight on a counterbalanced air-bearing or crossed-roller vertical slide, or a force-controlled voice-coil axis (0.05–4 N, modulation to 20 Hz). **6-axis F/T sensor, ATI Nano17 class**: ≥ ±10 N in-plane, ≥ ±15 N normal, resolution ≤ 5 mN, in-situ dead-weight calibration error ≤ 2 % of reading at 0.2–4 N, mounted resonance ≥ 500 Hz. For friction (B01, B02, Q01) the per-axis gains and cross-axis terms are calibrated **at each test angle** to ±0.2 % ([`sim_to_real.md`](sim_to_real.md) §6 item 3). Paper platen on an **XY linear-motor stage**: encoders ≤ 0.1 µm, 0.01–200 mm/s, velocity ripple ≤ 1 %. A flexure or voice-coil **reciprocation stage** (±0.5 mm, 1–20 Hz, capacitive or encoder feedback ≤ 0.1 µm). **Laser triangulation sensor** for indentation (≤ 0.1 µm resolution, ±1 µm linearity over 1 mm). 24-bit simultaneous-sampling DAQ ≥ 5 kS/s per channel. Environment 23 ± 2 °C, 50 ± 10 % RH (ISO 12757-1 test atmosphere, CON-21). |
| **R2 cancellation rig** | B05 (in contact), B09, E02, F01 (in contact), S02, P01, Q06, Q07 (in contact), Q08 | Linear-motor XYZ "robot" carrying the hand-simulant base along intended paths (≤ ±5 µm path error at ≤ 200 mm/s). A **2-axis voice-coil disturbance stage** between robot and simulant (±1 mm, 1–30 Hz, ≥ 10 N, sensor ≤ 0.1 µm). **Hand simulant**: two-stage mass–spring–damper per page axis with interchangeable springs and eddy-current dampers covering HAP-26 ranges (k1 230–1040 N/m, b1 0.3–4.6 N·s/m, M 0.05–0.57 kg, k2 63–533 N/m, b2 3.7–27.6 N·s/m). A normal-direction spring K_n (200–3000 N/m) with a preload screw sets N; the simulant FRF must be within ±10 % of target (qualification). **Paper platen on a 3-axis force plate** (Kistler 9119/9256 or ATI Mini40 class; ≤ 5 mN resolution, ≥ 1 kHz resonance with platen). **Housing metrology**: three laser triangulation sensors on the robot carriage viewing the barrel (≥ 10 kHz, ≤ 0.5 µm resolution, ±2 µm linearity over ±2 mm). **Nib-relative metrology**: a laser Doppler vibrometer or triangulation sensor on the carrier or refill, independent of the pen's Hall sensor. |
| **R3 ink metrology** | B01, B08, B09, E02, F01, S02, H03, H05, Q02, Q06, Q08 | **Flatbed scanner at 4800 dpi nominal** (5.3 µm/pixel), 16-bit lossless TIFF, fixed exposure. Optical resolution verified on a USAF-1951 target: ≥ 40 lp/mm resolved (group 5, element 3). Geometric distortion mapped with a **certified chrome-on-glass grid** (pitch uncertainty ≤ 1 µm). Alternative: motorised microscope stitching at ≤ 2 µm/pixel. **Required: ink-centreline position uncertainty ≤ 5 µm (k = 2) within a 25 mm field and ≤ 20 µm across a page** after distortion correction (engineering judgement: TUR ≥ 4 against 20 µm-class differences). Paper carries pre-printed fiducials; a blank scan is taken before writing. Centreline extraction: background subtraction, Otsu threshold, sub-pixel ridge fit across the line every 20 µm. Versioned code, results frozen before unblinding. |
| **R4 actuator coupon fixture** | B03, B07, Q04 | 2-axis micrometre positioning stage for the coil paddle (≤ 1 µm resolution, ±1.6 mm at the actuator). 6-axis F/T sensor as R1. Precision bipolar current source (±1 A, ≤ 0.1 % accuracy) or the Rev A drive with a 0.1 %-class shunt read by a 6½-digit DMM. **LCR meter**, 4-terminal, 20 Hz–100 kHz, basic accuracy ≤ 0.1 %. 4-wire micro-ohmmeter at 20.0 ± 0.5 °C. Fine type-T thermocouples (0.08 mm, ±0.5 °C after dry-block calibration). **Thermal camera** ≥ 320 × 240, NETD ≤ 50 mK, emissivity set on black tape (ε = 0.95). Climate chamber ±0.5 °C. Small electrodynamic shaker for back-EMF tests. |
| **R5 calibration stage** | B04, B10, S01, Q04, Q07 | Crossed-roller or air-bearing XY(Z) stage, bidirectional repeatability ≤ 1 µm, accuracy ≤ ±2 µm over 10 mm (laser-interferometer verified). Piezo nanopositioner for steps (rise ≤ 0.2 ms, capacitive sensor ≤ 10 nm). Goniometer and rotary stages for θ and ρ. **Independent tip metrology**: two orthogonal laser triangulation or confocal chromatic sensors on a reference sphere at the tip, or an optical CMM with a telecentric lens (≤ 1 µm/pixel with sub-pixel edge fit). Uncertainty of tip position ≤ 1 µm (k = 2). |
| **R6 grip-impedance rig** | B06 | Pen-shaped handle (Ø15 mm, 150 mm, ~30 g) with an embedded 6-axis F/T sensor between grip sleeve and shaft, triaxial accelerometer ≥ 1 kHz, stylus tip. **Electrodynamic shaker** (≥ 10 N, 1–200 Hz) with stinger and **impedance head** at the drive point. **Vertical voice-coil platen** under the paper for normal-direction excitation (±0.3 mm, 1–50 Hz) on a force plate. Forearm support; visual feedback of normal force. |
| **R7 electronics and HIL bench** | F01, F02, P01, P02, C02, E02 (timing), Q03, Q05 | 16-channel **logic analyser** ≥ 100 MS/s. 4-channel oscilloscope ≥ 200 MHz with a **current probe** (≥ 10 MHz, ±1 %). Programmable **power supply / source-measure unit** with ≥ 10 kS/s current logging (1 µA–3 A, ±0.3 %) and ramp control for brown-out. Solid-state and relay **fault-injection board** (coil short < 1 µs, open lead, Hall supply cut, SPI line freeze). **Battery cycler**. Thermal chamber. **Medical-grade USB isolator** for any human-connected session. |
| **R8 fatigue rig** | M02, B10, Q04 | Resonant or shaker-driven flexure fatigue stations (100–300 Hz). Amplitude control by laser displacement (≤ 0.5 µm). Miniature strain gauges on sacrificial coupons. Resonance tracking for crack detection. Stereo microscope (≥ 50×). Access to SEM for fractography. Axial load frame with 0–10 N load cell (±0.1 % FS). **Wire coupons (DEC-098):** EXP-B25, K21 and BB04 run on study H's crank-driven shuttle instead (§55), at no more than 0.2 × the first transverse mode measured on each coupon; a failure is an open circuit or a step of more than 2 % in the 4-wire resistance, not a resonance shift. |

**R9–R14** (study M; DEC-058) are specified in `docs/measurement_rig.md` and summarised in §47. They take over from R1 for G1 (R9), from R5 for page sensing (R10), from R4 for coupons (R12) and from R2 for loaded nibs (R13), and add a recording pen and tablet protocol (R11) and a grip simulant (R14). One acquisition box, DAQ-1, puts every instrument on one clock. R3, R7 and R8 stay as above. Each existing protocol names the rig and the EXP-T experiment it now runs on.

### 0.10 Laboratory safety

- Beryllium–copper is formed, etched and cut under beryllium dust controls (AMF notes §2.2). Airborne beryllium can cause serious lung disease (AMF-18). The alloy's safety data sheet names heat treating, pickling, chemical cleaning, abrasive cutting, welding, grinding, sanding and polishing as exposure routes (AMF-319). OSHA's limits are 0.2 µg/m³ averaged over 8 h and 2.0 µg/m³ over 15 min (AMF-320). For the C17200 wires (EXP-K21, BB04; DEC-063, DEC-097):
  - the wire is bought already age-hardened, so no heat treatment is done at the bench;
  - it is cut with shears or flush cutters only, and never abrasive-cut, ground, sanded, pickled or acid-cleaned;
  - joints are soldered under a bench fume absorber, or crimped; nothing is welded;
  - gloves are worn, because the alloy can sensitise skin (AMF-319); offcuts, broken coupons and wipes go into sealed, labelled bags;
  - there is no food or drink at the bench, and hands are washed after handling.

  *Was (DEC-063, before DEC-097):* Rev K's C17200 wires are soldered or crimped, and never welded, ground or laser-cut without fume extraction.
- Li-ion cells are charged and cycled in fire-safe containers. Abuse tests (short circuit, crush, over-charge) are done only at an accredited laboratory (EXP-P02).
- Laser sensors are class 2 or 3R, with signage.
- Piezo drives (EXP-Q04…Q08) run at up to 60 V, and the DRV2700 boost can reach 105 V. Terminals are shrouded, and multilayer plates are shorted before handling because they hold charge.
- **The grounded five-bar** (study H's B3; DEC-099) is benched only with a passive 24 mm dummy pen and spring hand simulants (200 and 500 N/m), never with a person's hand, until a safety gate like G-S is written for it. It has a hardware current limit at the motors' rated current, the 0.4 N cap in software, a breakaway magnetic pen coupling that releases between 0.5 and 0.8 N as the physical backstop (AC-BB06-04), guards over the capstans and the sweep of the links, and a latching emergency stop that removes motor power. At rated current the linkage can push about 1.06 N at its worst pose and direction (CALC), so the current limit alone cannot hold the cap.
- The wire-fatigue shuttle's crank turns at 4,000–9,000 rpm: it is balanced and guarded (DEC-098; §55).
- **No participant touches a powered prototype before gate G-S** (`prototype_stages.md`).

### 0.11 Pencil-class protocols (EXP-Q01…Q08)

The pencil-class concept (Rev P0, DEC-019; `docs/pencil_concept.md`) has its own parameter overlay and model. For EXP-Q01…Q08:

- **Predictions** come from `config/pencil.yaml` (P0.1.2, an overlay on `config/parameters.yaml` v0.4.4), from `analysis/pencil_mechanisms.py` (`results/pencil/mechanisms.json`, CALCULATION) and from the pencil model P1 (`sim/pencil`; `results/pencil/sim_metrics.json` and `touchdown_tails.json`, SIMULATION). They are regenerated with the as-built parameters and frozen as in §0.2.
- **Forces** follow `docs/pencil_mechanisms.md` §2. F_c is the axial nib-spring force. The nib normal force is N_nib = F_c / (sin θ − μ cos β cos θ). The transverse load per stage axis in the worst stroke direction is F_c·cot(θ − atan μ). The **design load** is 0.170 N per axis at F_c 0.15 N, θ 50° and μ 0.15. Strokes and loads are referred to the nib (lever 1.363). The usable correction is ±0.30 mm (servo soft limit); the stops are at ±0.40 mm.
- **Rigs** are those of §0.9: R1 for Q01 and Q02; R7 for Q03 and Q05; R4, R5 and R8 for Q04; R2 and R3 for Q06 and Q08; R5 and R2 for Q07. Since study M, Q01 and Q02 run on R9, and Q06 and Q08 on R13 (§47).
- **What does not carry over from Rev A.** The pencil stage has no coil, so the copper-loss, coil-temperature and current-clamp criteria do not apply to it. Drive power and runtime are covered by EXP-Q03, EXP-Q05 and AC-P01-05.
- **People.** No pencil build is used with participants before it passes a safety gate equivalent to G-S. `prototype_stages.md` defines G-S for Rev A builds only; the pencil set is an open item (`README.md` §7).

---

## 1. Experiment index

The "Gates" column lists decisions (DEC-…, `docs/decisions.md`), requirements (REQ-…, `docs/requirements.csv`) and stage gates (G-…, `prototype_stages.md`).

| ID | Title | Stage | Rig | Gates | Depends on |
|---|---|---|---|---|---|
| EXP-B01 | Refill drag and contact-reaction map (includes refill metrology) | A | R9 (EXP-T01…T03; DEC-058), R3 | DEC-003, DEC-008, DEC-023, REQ-ACT-001, REQ-MECH-008, actuator freeze | R9 qualification (closure check, plate tap test) |
| EXP-B02 | Friction vs speed; LuGre identification | A | R9 with the R13 stage (EXP-T03) | contact model P-9, DEC-011, DEC-023 | B01 |
| EXP-B03 | Actuator coupons: force–current–position map, R, L, thermal, gap | A | R12 (EXP-T07…T09) | DEC-003, DEC-007 rev., DEC-012, DEC-023, REQ-ACT-001/002, REQ-SNS-004, actuator freeze | coupons built |
| EXP-B04 | Hall and optical calibration against a motion stage; page workspace | A (rig), B (pen) | R5; R10 for the optical scale (EXP-T04) | REQ-MECH-001, REQ-SNS-004, CAL_HALL | B03, B05 |
| EXP-B05 | Stage FRF, stiffness, stops, axial path, contact chatter | A, B | R2, R5; R13 in contact (EXP-T10) | REQ-ACT-003, REQ-CTRL-002, REQ-MECH-002/003/004, REQ-SNS-005, DEC-011, DEC-023 | B03, B04 |
| EXP-B06 | Grip impedance incl. normal direction; γ identification (participants) | A (bench), B (in-pen γ) | R6 | DEC-006, REQ-CTRL-006, hand model P-13 | ethics approval |
| EXP-B07 | Coil and skin temperature | A (coupon), B, C (pen) | R12 (coupon, EXP-T08), R13 (pen, EXP-T15), R7 | REQ-THM-001/002, REQ-ACT-002, DEC-008, G-S | B03 |
| EXP-B08 | Ink tolerance to modulated normal force | A | R9 (EXP-T02), R3 | REQ-MECH-005, DEC-004, DEC-006 | B01 |
| EXP-B09 | Bench cancellation with injected disturbance and µm ink metrology | A (rig), B (pen) | R13 (EXP-T10, T13), R3 | G-B, G-C, REQ-VAL-001, REQ-CTRL-003/005/006/007/008, DEC-009, DEC-023 | B01, B02, B03, B04, B05, B06, B08, S01, F01 |
| EXP-B10 | Durability: flexure cycling, refill exchange, drop | B, C | R8, R5 | REQ-MECH-002/004/006/008, G-C | M02 |
| EXP-S01 | Optical-sensor latency and accuracy | A, B | R10 (EXP-T04, T05) | DEC-005, DEC-021, REQ-SNS-001/002, REQ-CTRL-003, REQ-PNC-004 | — |
| EXP-S02 | Capture and fusion accuracy against references | B, C | R2, R3 | REQ-CAP-001/003, COR-16 | S01, B04 |
| EXP-F01 | Hardware fault injection | A (board), B, C | R7, R2; R13 in contact (EXP-T11) | REQ-SAF-001/002/004, REQ-PWR-003, DEC-015, G-S | bring-up steps 1–10 |
| EXP-F02 | Firmware robustness | B, C | R7; R13 for page-sensor faults (EXP-T14) | REQ-CTRL-001/004, REQ-SAF-001/003/004, REQ-SNS-003, DEC-010/015/016, G-S | F01 |
| EXP-M02 | Flexure fatigue coupons | A | R8 | REQ-MECH-006/007, DEC-007 | coupons |
| EXP-M03 | Mass, centre of mass and balance of built pens | B, C, D | — | REQ-FORM-001…004, REQ-PNC-001, REQ-RVK-001 (DEC-062) | pens built |
| EXP-P01 | Power and runtime | C (and D) | R7, R2; R13 for the nib's power (EXP-T15) | REQ-PWR-001, REQ-ACT-002, REQ-PNC-005, REQ-RVJ-I01, REQ-RVK-002, DEC-008, DEC-044, DEC-045, DEC-062 | P02 |
| EXP-P02 | Charging and battery safety pre-compliance | C | R7 | REQ-PWR-002/003, REQ-THM-001, G-C | cell samples |
| EXP-E01 | Estimator bake-off on recorded writing at matched false correction | offline, after H01 | compute | DEC-009, DEC-016, REQ-ML-001, REQ-CTRL-007, REQ-DATA-001 | H01 |
| EXP-E02 | Closed-loop replay of recorded tremor on the B09 rig | B | R2, R7 | REQ-ML-002, REQ-CTRL-005, REQ-SAF-003, DEC-016 | E01, B09 |
| EXP-C01 | Recognition accuracy (CER/WER, writer-disjoint) and search | C | compute | DEC-013, REQ-APP-001, REQ-DATA-001 | C02; H01/H06 ink |
| EXP-C02 | Capture fidelity end to end | C | R7 | REQ-CAP-001/002, DEC-017, G-C | F02 |
| EXP-A01 | AI grounding audit | C | compute + raters | REQ-APP-002, REQ-USR-003, DEC-017 | C01 |
| EXP-A03 | Autocorrect on real notes | C | compute + app | REQ-PNC-008, DEC-020 | C01; consented notes |
| EXP-Q01 | Skid friction (pencil) | A | R9 with a skid head (EXP-T01) | REQ-PNC-002, DEC-019, skid material for H03 | R9 qualification |
| EXP-Q02 | Low-force ink line quality; sets the nib-spring force F_c | A | R9 (Part A in EXP-T02), R3 | REQ-PNC-002, DEC-019 (stage load) | B01 Part 4 method; Q01 (Part B) |
| EXP-Q03 | Pencil cell pulse discharge | A | R7 | REQ-PNC-005, cell choice | cell samples; Q05 load profiles |
| EXP-Q04 | Bender characterisation and strength | A | R4, R5, R8 | REQ-PNC-003, DEC-019 | custom plates |
| EXP-Q05 | Piezo driver efficiency and quiescent power | A | R7 | REQ-PNC-005, driver choice | Q04 |
| EXP-Q06 | Loaded 1-axis rig: PL128.10, D1 refill, skid nose | A | R13 (EXP-T10), R3 | REQ-PNC-002/003, DEC-019 | Q01, Q02, Q04 |
| EXP-Q07 | Two-axis Q stage in a 7.9 mm bore | A | R5, R2 | REQ-PNC-003, DEC-019, Rev P1 build | Q04, Q05, Q06 |
| EXP-Q08 | Touchdown and lift tails; tilt-adaptive front stop | A | R13 (EXP-T11), R3 | REQ-PNC-006, DEC-022 | Q06 |
| EXP-I01 | Grip compliance split: translation vs tilt of a pen grasp (participants) | A | R6 + second stinger | DEC-024, hand-pen model H1 | B06 session, ethics |
| EXP-I04 | Nib stage plus an inertial helper on the loaded rig (only if EXP-I01 finds r_rot ≥ 0.6); superseded by EXP-I06 for Rev H and by EXP-T16 | A | R2, R3 | DEC-024 | I01, Q06 |
| EXP-I05 | Rev H active nose on the bench: force constant, travel, bandwidth, power, writing-force change | A | R2 with a 2-axis shaker, R3; R13 (EXP-T10) and R12 (EXP-T07) | REQ-RVH-001…005, DEC-032 | nose prototype |
| EXP-I06 | Rev H rear inertial module on a hand simulant with the nose on | A | R14 (EXP-T16) | DEC-033 | I01, I05 |
| EXP-I07 | Rev H tracker on recorded tremor writing (offline replay) | C | compute | REQ-RVH-006, DEC-028, DEC-032 | E01 recordings |
| EXP-G01…G06 | Guidance board: force map, stage and latency, localisation, noise and heat, hand simulant, safety | A | board prototype, 3-axis load cell | REQ-RVH-007, DEC-031 | board prototype |
| EXP-D01 | Heel drive: tyre–paper friction on six papers | A | R9 with a wheel head (EXP-T01), climate box | REQ-DRV-004, DEC-037 | R9 qualification |
| EXP-D02 | Heel drive: tyre lateral stiffness and relaxation length | A | micrometre stage, 3-axis force sensor | REQ-DRV-005 (slip threshold), DEC-037 | D01 |
| EXP-D03 | Heel drive: holding the sheet | A | load cell, 3 desk types | REQ-DRV-011 | heel pod |
| EXP-D04 | Heel drive: geometry, roll, preload and steering | A | R5 (tilt–roll fixture), load cell | REQ-DRV-004/006/007/008, DEC-036/037/044 (front end) | printed heel, 0620 B motors |
| EXP-D05 | Heel drive: slip detection | A | linear stage, page-sensor board, encoder, high-speed camera | REQ-DRV-005, DEC-037 | D01, D02 |
| EXP-D06 | Heel drive: noise, heat, power and runtime | A | R7, sound level meter | REQ-DRV-009/010, REQ-THM-001, REQ-RVJ-I01 | D04; N04, N08 and J12 power logs |
| EXP-D07 | Heel drive: force cap, stall and lift safety (gate before D08, D09, D11) | A | 3-axis load cell, R7 | REQ-DRV-001/002/013, DEC-037 | D04, D05 |
| EXP-D10 | Heel drive: ink smear and wheel track | A | R3, microscope camera | REQ-DRV-012 | D01 |
| EXP-D12 | Heel drive: durability, cleaning and replacement | A | rolling rig, R1 | REQ-DRV-012 | D01 |
| EXP-D13 | Driven-ball fallback: roller drag and wear | A | bench ball drive, force sensor | DEC-037 (ball as the bench alternative) | rollers made |
| EXP-K01 | End-cap: reaction-mass actuator against its model; envelope, power, permeability | A | R12: a clamp fixture with a 6-axis F/T (net force); the force constant in EXP-T07 | REQ-EC-001/008/009, DEC-038, DEC-045 | end-cap prototype |
| EXP-K02 | End-cap: tremor on top of the nose on a hand–pen rig (extends I06) | A | R14 (EXP-T16), R3 | REQ-EC-002/003, DEC-038 | K01; I01 or K08 |
| EXP-K04 | End-cap: can inertia steer the ink? (rig, then 6 healthy writers) | A | EXP-K02 rig | REQ-EC-004, DEC-038 | K02; K06 for a rotor |
| EXP-K06 | End-cap rotor safety (only if a rotor is kept) | A | containment enclosure, drop rig, sound level meter | REQ-EC-007, DEC-038 | CMG research module |
| EXP-K07 | Does spin itself steady the pen? | A | R14 (EXP-T16) | DEC-038 | K02 rig, rotor end-cap |
| EXP-K08 | Grip split with the end-cap fitted (participants) | A | R6 + second stinger | DEC-038 | I01 method; ethics |
| EXP-N01 | Nose v2 magnetics coupons, and Rev H's force constant | A | R12 (EXP-T07) | REQ-RVJ-N02, REQ-RVH-003, DEC-036, DEC-041 | coupons built |
| EXP-N02 | Nose v2: travel and front-end closure over 35–75° | A | R13 (EXP-T13), side camera | REQ-RVJ-N01, DEC-036, DEC-044 | nose prototype; J01 (gimbal load) |
| EXP-N03 | Nose v2: servo bandwidth and parasitic modes | A | R13 (EXP-T10); R12 for the modes (EXP-T08) | REQ-RVJ-N02, DEC-036 | N01, N02 |
| EXP-N04 | Nose v2: heat at the autowrite duty | A | R13 in the 30 °C chamber (EXP-T15), IR camera | REQ-RVJ-N03, DEC-036, DEC-045 | N01, N03 |
| EXP-N05 | Pen lift; strokes kept separate at 50–70° | A | R7, high-speed camera; R13 for step 4 (EXP-T11) | REQ-RVJ-N04, DEC-036, DEC-041 | pen-lift module |
| EXP-N06 | Refill force element fatigue | A | R8 | REQ-RVJ-N05, DEC-036, DEC-041 | candidate springs; J06 cycles the drum's spring |
| EXP-N07 | Page sensor under the pen | A | R10 (EXP-T04); R13 in the pen (EXP-T14) | REQ-RVJ-N06, DEC-036, DEC-037 (slip), DEC-044 | sensor board; J04 (height band) |
| EXP-N08 | Autowrite on the bench, with the SIM gate | A | R13 after EXP-T13, R3 | REQ-RVJ-N08, DEC-039, DEC-049, DEC-050 (a research mode with the C1S nose) | N02…N07 |
| EXP-V01 | Simulator v2: paper contact of the Rev H front end | A | R9 (EXP-T01) | DEC-040 | B02, Q01 methods |
| EXP-V02 | Simulator v2: identify the assembled pen; refill front stop | A | R4, R5, R7 | DEC-040, REQ-RVH-008, DEC-041 | I05 build |
| EXP-V03 | Simulator v2: real writing and tremor at the pen (inside EXP-H01) | offline, after H01 | compute; R11 recordings (EXP-T06) | DEC-040 (writer refit) | H01 recordings |
| EXP-V04 | Simulator v2: pen-grasp impedance while writing (participants) | A | R6 | DEC-040 | I01 or B06 sessions; ethics |
| EXP-V05 | Simulator v2: device effect on a bench against the frozen model | A | R13 after EXP-T13, R3 | DEC-040, REQ-SIM-001…005 | V01, V02, V04; frozen firmware |
| EXP-V06 | Simulator v2: population prediction against people | offline, after a human study | compute | DEC-040 | V05; W02 or D09 data |
| EXP-V07 | Simulator v2: small handwriting on a tablet (participants) | tablet session; then offline | R11 tablet protocol (≥ 200 Hz, AC-T06-04) | DEC-040 (writer refit), REQ-RVJ-C03 | consent; ethics |
| EXP-L01 | Control stack: the tremor-line gate on real tremor-free writing; causality of the stack; the gate on the low-power page sensor's stream and on the IMU alone | offline, after H01; then A | compute; bench pen | REQ-CTRL-009/010, REQ-RVJ-C03, DEC-042, DEC-045, DEC-047 | H01 recordings; J10 (the low-power die's stream); sim2 (the SIM gate) |
| EXP-L02 | Control stack: gated tracker and G4 against the Rev H tracker on real writing and on the bench; the command's band limit; the SIM gate for every controller | offline, after H01; then A | compute; R2 (EXP-I05 tremor rig), R3 | REQ-CTRL-011, REQ-RVJ-C01, REQ-RVJ-C02, DEC-042, DEC-047, DEC-048 | L01; sim2 (the SIM gate) |
| EXP-L04 | Control stack: learned estimator against REQ-ML-001 on real data; MCU timing; shadow mode | offline, after H01; then A | compute; R7 | REQ-ML-001, REQ-ML-003, DEC-042, DEC-061 (study E's EXP-E14) | H01 recordings; E01 protocol |
| EXP-L05 | Control stack: RL arbiter in the sim2 closed loop, then on the bench | offline; then A | compute (sim2); EXP-V05 rig | REQ-ML-004, DEC-042, DEC-047 | V05 (REQ-SIM-005); the environment in `sim2j/rl.py` |
| EXP-J01 | Integrated layout: axial magnetic pull on the gimbal, and centring | A | R12 (EXP-T08) | REQ-RVJ-I02, DEC-044, DEC-045, DEC-036 | C1S cap and plate dummy |
| EXP-J02 | Integrated layout: heel-motor cogging from the C1S magnets, at the Rev J.1 place | A | torque sensor (0.001 mN·m); plate dummy with a 1.5 mm back iron, and cap | REQ-RVJ-I03, REQ-RVJ-I04, DEC-044, DEC-045, DEC-037 | 0620 B motor |
| EXP-J03 | Integrated layout: nose Hall sensors among the magnets, motors, brake and coils | A | R12 (EXP-T09) | REQ-RVJ-I04, DEC-044 | board, J02 set-up |
| EXP-J04 | Integrated layout: page-sensor working band over tilt, roll and height | A | R10 (EXP-T04) | REQ-RVJ-N06, REQ-DRV-005, DEC-044 | folded optics; EXP-D01 papers |
| EXP-J05 | Integrated layout: heat at the web, bare and with the graphite sheet (DEC-045) | A | heater in a PEEK shell, IR camera, thermocouples; R13 chamber (EXP-T15) | REQ-RVJ-N03, DEC-044, DEC-045 | printed and moulded shell |
| EXP-J06 | Integrated layout: ink-force drum, spring and front stop | A | linear stage, R8, R3 | REQ-RVJ-N05, REQ-RVJ-N09, DEC-041, DEC-044, DEC-045 | drum module |
| EXP-J07 | Integrated layout: field outside the pen | A | gaussmeter on a scanning stage | REQ-RVJ-I05, DEC-044 | magnetic mock-up |
| EXP-J10 | Rev J.1: a low-power page sensor (PMW3610 class) in every mode | A | R10 (EXP-T04), current probe | REQ-RVJ-N06, REQ-RVJ-I07, REQ-RVJ-C05, REQ-DRV-005, DEC-042, DEC-045, DEC-049 | folded optics; EXP-D01 papers |
| EXP-J11 | Rev J.1: the 75 µm gimbal under the pull, fatigue and drops | A | R12 for the stiffness (EXP-T08), R8, drop rig | REQ-RVJ-I02, DEC-045 | J01 (measured pull) |
| EXP-J12 | Rev J.1: electronics power, then the pen's power per mode | A; then C | R7 | REQ-RVJ-I01, DEC-045 | main board and firmware loop; P01 set-up |
| EXP-J13 | Rev J.1: heat with the graphite sheet | A | EXP-J05 shell, IR camera, thermocouples, hand phantom; R13 chamber (EXP-T15) | REQ-RVJ-N03, REQ-THM-001, DEC-045 | J05 |
| EXP-J14 | Rev J.1: K_m and pull with the 1.5 mm back iron | A | R12 (EXP-T07, T08), Hall probe | REQ-RVJ-N02, DEC-045 | N01 and J01 coupons |
| EXP-J15 (wear part) | Rev J.1: wear of the clear window (the writers are in `human_study_plan.md` §20) | A | Taber abraser or steel wool, haze meter | REQ-RVJ-I06, DEC-045 | coated PC coupons |
| EXP-J16 | Rev J.1: the 29.6 g end-cap on top of the nose (EXP-K02 repeated) | A | R14 (EXP-T16), R3 | REQ-EC-002/003, DEC-038, DEC-045 | K01; I01 or K08 |
| EXP-J17 | The nib's static side load and holding power (the C1S nose; the B1 nib of DEC-050); part (c), study B's EXP-B22: the counter-face bench | A | R9 frame (EXP-T12 part A), coil current, coil thermocouple; part (c) on a new R12 fixture (tilting stage, 6-axis cell, high-speed camera) | REQ-RVJ-N10, REQ-RVJ-C04, REQ-BNIB-001/002/008/016, DEC-046, DEC-050, DEC-064 (Rev K's head, with EXP-K23) | nib prototype; refill springs; part (c): the counter-face and a refill guide |
| EXP-T01 | Rig R9: axial and paper-normal force apart; friction vector map; static side load | A | R9 | G1 (review), DEC-058, REQ-ENV-001/002, REQ-ACT-001, REQ-RVJ-N05, DEC-050 (study B's EXP-B21) | DAQ-1 bring-up; R9 built; plate tap test |
| EXP-T02 | Rig R9: minimum reliable ink force and ink continuity | A | R9, R3 | G1, REQ-BNIB-014, DEC-050 (study B's EXP-B20), REQ-RVJ-N05, REQ-PNC-002, REQ-MECH-005, REQ-ENV-001 | T01 (same frame and calibration) |
| EXP-T03 | Rig R9 (optional): friction dynamics at tremor amplitudes | A | R9 with the R13 stage | G1 (optional), P-9, DEC-011, DEC-040 | T01, T02 |
| EXP-T04 | Rig R10: page-relative sensing (accuracy, noise, scale, working band, dropout; EXP-J10's page-noise model) | A | R10 | sensing build gate, REQ-SNS-001/002, REQ-RVJ-N06, REQ-RVJ-I07, REQ-RVJ-C05, REQ-DRV-005, DEC-059, REQ-BNIB-017 (study B's EXP-B32), DEC-062, DEC-065 (the heel module's page sensor) | R9 frame; truth qualified (AC-T04-03) |
| EXP-T05 | Rig R10: page-sensor latency (step and phase methods) | A | R10 with the R13 stage | sensing build gate, REQ-SNS-001, REQ-RVJ-N06, REQ-CTRL-003 | T04 set-up |
| EXP-T06 | Rig R11: recording pen and tablet protocol; the real force split | A (bench); used in H01 | R11, R9 plate | EXP-H01, EXP-V07, REQ-USR-002, REQ-ENV-001/002, REQ-DATA-001 | tablet; recording pen built |
| EXP-T07 | Rig R12: coupon force map and K_m(position) | A | R12 | G2, REQ-BNIB-003, DEC-050 (study B's EXP-B23), DEC-062 (study K's EXP-K22), REQ-ACT-002 | study B's and study K's coupons |
| EXP-T08 | Rig R12: magnetic pull, negative stiffness, loaded modes at temperature | A | R12, heated box | G2, REQ-RVJ-I02 and REQ-RVJ-N02 (magnet-loaded suspensions: the C1S module), DEC-050 (study B's EXP-B23: keeper pull, K_m(T)) | T07 |
| EXP-T09 | Rig R12: Hall-sensor interference | A | R12 | G2, REQ-RVJ-I04, REQ-SNS-004, REQ-BNIB-009 (study B's EXP-B24) | T07 |
| EXP-T10 | Rig R13: one-axis loaded nib, rejection and bandwidth in contact | A | R13 (one axis), R9 plate, R3 | G3, REQ-BNIB-003/005/006 (study B's EXP-B26), REQ-CTRL-002/003/005, REQ-VAL-001, the estimator's prediction horizon (study E's EXP-E15), DEC-066 | G2 (T07–T09); one-axis nib |
| EXP-T11 | Rig R13: large excursions, bounded current, pen lift | A | R13 (one axis), R3 | G3, REQ-SAF-002, REQ-BNIB-002, REQ-RVJ-N04, REQ-RVJ-N09 | T10 |
| EXP-T12 | Static side load and holding power over tilt, roll and direction (part B; part A is EXP-J17) | A | R13 | G3, REQ-RVJ-N10, REQ-RVJ-N03, DEC-046, DEC-050 | J17; the B1 nib |
| EXP-T13 | Rig R13: two-axis nib; sharp turns, repeated contacts, full roll and tilt | A | R13 (two axes), R3 | G4, REQ-CTRL-005, REQ-VAL-001, REQ-ENV-001, REQ-BNIB-004/011/013 (study B's EXP-B27), DEC-062 (REQ-BNIB-011 reworded) | T10, T11 |
| EXP-T14 | Rig R13: optical dropout while writing, in closed loop | A | R13, R10 fixtures | G4, REQ-SAF-003, REQ-CTRL-005, REQ-RVJ-N06 | T13; T04 |
| EXP-T15 | Rig R13: long thermal run with the governor | A | R13 in a 30 °C chamber | G4, REQ-BNIB-010 (study B's EXP-B29), REQ-RVJ-N03, REQ-THM-001/002 | T13 |
| EXP-T16 | Rig R14: collar and tail on a grip simulant (none, same mass locked, unpowered, active) | A | R14 on the R13 stage, R3 | G5, REQ-WP-001, REQ-EC-002/003 | T17 |
| EXP-T17 | Rig R14: grip simulant qualification | A | R14 | G5 (validity of T16), inputs of REQ-SIM-005 | R14 built |
| EXP-R02 | Real data: every tracker on real inputs, as results cards; DEC-055's line at the severe class | offline; then on H01/R01 recordings | compute (realdata, HW1); the EXP-L01, L02, L04 replay harness | REQ-DATA-002/003/004/007/008, DEC-054, DEC-055, DEC-042, DEC-047, REQ-CTRL-017, DEC-060 | realdata library; H01/R01 recordings (later) |
| EXP-R04 | Real data: children's handwriting with and without dysgraphia (DiaGraMo) | offline | compute | REQ-DATA-006, study S | the data set downloaded |
| EXP-R05 | Real data: a tracker trained on real inputs; does it keep clean writing still? | offline | compute (realdata, HW1) | REQ-ML-001, REQ-DATA-005, DEC-042, DEC-055, DEC-061 (study E did the retraining; its test is EXP-E10) | realdata tuning split; R01 training participants (later) |
| EXP-R06 | Real data: get the missing data sets (IAM-OnDB, PaHaW, OnHW) | offline | — | REQ-DATA-006 | registration and agreements |
| EXP-R07 | Real data: the page sensor's window error on paper against a fine reference; the page model refitted | A | R10 (inside EXP-T04, T05) | REQ-DATA-007, REQ-RVJ-C05, DEC-059 | T04, T05 |
| EXP-S16 | Study S: close tracing with guidance that advances along the letter (EXP-D08's task on the bench) | A | R14 on R13's stage, R3; heel drive and nose | DEC-057, DEC-037 | D07; the heel-drive and nose prototype |
| EXP-S19 | Study S: writing an accepted word with a reach-limited nib while the hand moves | A | R13 after EXP-T13 (EXP-N08's set-up), R3 | REQ-CTRL-014, REQ-RVJ-N07/N08, DEC-049, DEC-056, DEC-050 (a research mode with the C1S nose) | N08's SIM gate (AC-N08-01, N08-03) |
| EXP-S20 | Study S: is the spelling score calibrated for new users and devices? | offline, after S18 | compute | REQ-APP-007, DEC-056 | S18 data |
| EXP-S21 | Study S: shape assist and spelling cues on children's handwriting with dysgraphia (DiaGraMo) | offline | compute (HW1) | DEC-057 | R04 (DiaGraMo in the library) |
| EXP-W11 | Study W: the collar mock-up: transmission, holding power, stability, fit and stops; its G5 part in EXP-T16 | A | R14 on R13's stage (EXP-T16), R9 plate, R3 | REQ-WP-001 (AC-T16-01), REQ-WP-002/003/005/006/008, DEC-051 | T17; the mock-up built |
| EXP-W13 | Study W: does the ball stay on the paper during large corrections, with Rev K's B1 nib and with the collar? | A | R13 over R9's plate (EXP-J17 and T12 set-up), R3 | REQ-WP-004, DEC-051, DEC-050 | T13 (the two-axis B1 nib), T11; the W11 mock-up |
| EXP-W14 | Study W: tail modules against the same mass locked (G5) | A | R14 (EXP-T16) | REQ-WP-010, REQ-WP-001 (AC-T16-01), DEC-051 | T17; K06 methods for the gyroscope |
| EXP-W15 | Study W: causal estimates against perfect knowledge on real writing; the collar's command on clean writing | offline; then on H01/R01 and W10 recordings | compute (study W's simulator, HW1; EXP-R02's replays) | REQ-WP-007, REQ-WP-012, DEC-052 | R02 replays; study E |
| EXP-W17 | Study W: an amplitude-gated paper force (the heel wheel's tremor mode above a detected amplitude) | offline (sim2); then A | compute (sim2); R14 with the heel drive | REQ-WP-001, REQ-RVJ-C02 (AC-L02-05), DEC-048 | D07 safety gate |
| EXP-B25 | Study B: wire suspension coupons: stiffness, clamp stress, fatigue at the stop travel, 1 m drops | A | study H's fatigue shuttle (DEC-098; was R8), a drop fixture, R12's stage | G2, REQ-BNIB-007, REQ-BNIB-012, DEC-050, REQ-RVK-005 (Rev K's offsets and drops) | wire coupons and clamps; for AC-B25-04, the first Rev K nib |
| EXP-B28 | Study B: the IMU's tilt and roll error for the face schedule, level and on 10 and 20° slopes | A | R13 with a camera; R11 recordings (EXP-T06) or study R's | G2, REQ-BNIB-015, DEC-050 | T06 recordings; the face schedule's firmware |
| EXP-B30 | Study B (optional): the roll spread of a keyed grip, 10 writers (participants) | A | motion capture | G2 (optional), REQ-BNIB-015 (variant c''), DEC-050 | ethics approval (as EXP-B06) |
| EXP-B31 | Study B (slim branch): piezo bender stage coupon: force-travel line, loaded resonance, drive power | A | the pencil rigs of EXP-Q04 and Q05 | the slim core's feasibility (a trade study), DEC-050 | Q04 and Q05 methods |
| EXP-E10 | Study E: the real-data TCN, frozen, tested once on new held-out data against DEC-055 | offline | compute (realtrack, HW1) | DEC-060, DEC-061, DEC-055 (AC-R02-01), REQ-CTRL-015, REQ-CTRL-017, REQ-CTRL-018 (DEC-067) | R06's sets or the R01 recordings |
| EXP-E11 | Study E: a gate calibrated on the user's own clean writing | offline; then on R01's shadow-mode logs | compute (HW1) | REQ-CTRL-016, DEC-061, REQ-CTRL-019 (DEC-068; study F ran it in simulation) | R01 recordings (later) |
| EXP-E12 | Study E: more real training data, or a GRU | offline | compute | DEC-061 (the estimator's design), REQ-CTRL-015 | R06's sets |
| EXP-E13 | Study E: how much tremor may be left for words to be readable | offline | compute (HW1, literal reader) | DEC-060 (the target for any estimator), DEC-067 (study F ran it in simulation) | the realdata tuning notes |
| EXP-E17 | Study E: the frozen and the real-data designs in sim2 on more writers | offline (sim2) | compute (sim2) | REQ-RVJ-C02, REQ-SIM-005, DEC-047, DEC-060 | sim2j's test grid |
| EXP-K20 | Study K: the ball thrust guide coupon: tilt and wire loads under the counter-face couple, rolling friction, drops | A | R12's stage with a force sensor, an autocollimator; a drop rig; a profilometer | G2, REQ-RVK-003, DEC-063 | the guide's races, balls and springs; a carrier flange with Rev K's wires |
| EXP-K21 | Study K: C17200 wire coupons carrying the coil current: resistance, assembly preload, fatigue at the stop travel | A | study H's fatigue shuttle (DEC-098; was R8) with a current source and 4-wire resistance logging; R12's stage | G2, REQ-RVK-004, REQ-BNIB-007, DEC-063 | wire coupons, clamps and the anchor's diaphragm; the beryllium rule (§0.10, DEC-097) |
| EXP-K23 | Study K: the counter-face head mock-up: follower, float, pen lift, the positioners' holding, the shoe's capture, the refill change | A | EXP-J17 (c)'s tilting stage at R12, high-speed camera; R9's plate or R13 with R3 for the touchdown ink | G4 (before the Rev K pen), REQ-RVJ-N04, REQ-BNIB-002 (with AC-J17-05), DEC-064 | J17 (c)'s fixture; the head mock-up; SQL-RV-1.8 motors (or micro-stepper lead screws) |
| EXP-K25 | Study K: Rev K in sim2 on the test writers, the servo at 40 / 46 Hz against 80 / 100 Hz | offline (sim2) | compute (sim2j or bnib/sim) | DEC-066, REQ-RVJ-C02 | sim2j's adapter for `results/revK/sim_params.json` |
| EXP-E21 | Study F: how accurate a position reference must be in the tremor band | offline; then A | compute (readable, HW1); R10 with EXP-R07's refit | REQ-SNS-006, DEC-069 | T04's chosen die |
| EXP-E22 | Study F: a gate calibrated with the tremor present | offline; then on R01's shadow-mode logs | compute (HW1) | REQ-CTRL-019, DEC-068 | R01 recordings (later) |
| EXP-E23 | Study F: the B1 nib's own reach against the readable target | offline (sim2) | compute (bnib/sim or sim2j) | DEC-050, DEC-060 (the reach), REQ-BNIB-003 | EXP-K25's set-up (sim2j's adapter) |
| EXP-BB01 | Study H: DAQ-1 bring-up and time-base qualification | A | DAQ-1 (build B0) | DEC-058 (one clock), order 0 of every gate, REQ-DATA-001 | DAQ-1 assembled; its firmware compiled for the Teensy |
| EXP-BB02 | Study H: R9 frame qualification: plate mode, motion quality, in-situ calibrations | A | R9 (B1) | G1, DEC-058 (its tap-test trigger), REQ-ENV-002 | BB01; R9 built |
| EXP-BB03 | Study H: the axially soft wire anchor (the pass's floating anchor) | A | R12's bench and a precision balance (B2) | G2, DEC-072, DEC-096, REQ-BNIB-007 | the etched anchor and its interconnect |
| EXP-BB04 | Study H: the reach candidate's eight 34 mm C17200 wires at the 1.7 mm stop | A | the fatigue shuttle (DEC-098) and DAQ-1 (B2) | G2, DEC-072, DEC-096, DEC-098, REQ-RVK-004, REQ-BNIB-007 | BB03; the wire coupons and clamps; the beryllium rule (§0.10, DEC-097) |
| EXP-BB05 | Study H: ball-guide drag and tilt against preload, both guides | A | R12's stage, a 10 g cell and a laser lever (B2) | G2, DEC-063, DEC-072, DEC-096, REQ-RVK-003 | the races, balls and flanges; EXP-K20's drop rig |
| EXP-BB06 | Study H: five-bar qualification: kinematics, force, stiffness, force cap | A | the five-bar (B3), K3D40 ±10 N, camera | none yet (the grounded route): DEC-071, DEC-099 | the five-bar built; its controller firmware |
| EXP-BB07 | Study H: accepted-word replay on paper with a passive pen against spring hands | A | the five-bar (B3), R3 | none yet: DEC-071, DEC-099 | BB06 |
| EXP-BB08 | Study H: page anchoring through lift and occlusion | A | R10 (B4), camera | sensing build gate, DEC-070, DEC-071, REQ-RVJ-C05, REQ-CAP-003 | T04's chosen die |
| EXP-BB09 | Study H: contact-channel delay, false contacts and lift timing | A | R9 (B1) | G1, DEC-070, DEC-071, REQ-CTRL-003 | BB01, BB02; R9's voice-coil lift for part 3 |
| EXP-H01…H06, A02, I02, I03, W01…W05, G07, D08, D09, D11, K03, K05, N09, N10, L03, L06, L07, L08, J08, J09, J15, J18, R01, R03, S10…S15, S17, S18, W10, W12, W16, K24, E20, U01…U09 | Human-participant studies | see `human_study_plan.md` | — | REQ-USR-\*, REQ-VAL-002, REQ-PNC-007, REQ-RVH-\*, REQ-DRV-002/003, REQ-EC-001/002/003/005/006, REQ-RVJ-N07, REQ-RVJ-I06, REQ-RVJ-C02, REQ-RVK-001, REQ-CTRL-012/013/018, REQ-APP-001/003…008, REQ-DATA-004/008/009, REQ-WP-005/009/011, REQ-MKT-\*, DEC-002/008/009/016/020/024/031/035…039/042…045/048/049/051…057/062/067/090…094 | ethics |

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

**Rig (study M, DEC-058).** Parts 1–2 run on R9 as EXP-T01, Part 4 as EXP-T02 and Part 3 as EXP-T03 (§47; `docs/measurement_rig.md` §2). R9 measures the axial force and the paper-normal force apart. The single F/T sensor on the pen holder is retired for this experiment, and the equipment, set-up, procedure and data below are re-specified for R9.

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

- Rig R9 (§47; `docs/measurement_rig.md` §2), which replaces R1 here (DEC-058). A 3-axis force plate under the paper (ME K3D40: ±2 N for the low loads and the ink lines, ±10 N for the map) gives N and the friction vector in the page frame. An in-line axial cell (FUTEK LSB200: 100 g for F_c ≤ 0.5 N, 250 g above) behind a leaf-guided refill gives F_c, which a voice coil sets in current mode. A Hall sensor reads the refill's slide, so the leaf guide's force is subtracted. The printer bed that carries the plate does not move in x–y, so the plate is never accelerated.
- The single F/T sensor on the pen holder (R1) is retired here: it cannot separate the axial and the paper-normal forces (DEC-058).
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
3. Zero the plate and the axial cell with the pen lifted before every condition.
4. Calibrate in situ at the start of each session, **at every altitude used in the session** (35–80° here; 45° and 60° in EXP-B02). Dead weights of 5–500 g at nine positions on the platen and horizontal pulls over a jewel-bearing pulley fit the plate's 3 × 3 matrix, offsets and eccentricity. Dead weights on the cartridge fit the axial cell. The guide stiffness is fitted with the refill off the paper (`docs/measurement_rig.md` §2.4).
   - Why: with the protocol-class ±2 % gains, part of the normal force appears on the friction axes. In twin experiments the correct friction model's held-out error reached 0.24–0.45 of μ_k·N for inks with μ_k 0.065–0.035 ([`sim_to_real.md`](sim_to_real.md) §6 item 3; SIMULATION).
   - Closure check: with the refill free to slide, F_c must equal the plate force projected on the pen axis (P-7). It runs live; a persistent failure retires R9 for G1 (AC-T01-01, DEC-058).
   - Friction at the lowest loads is the weak line: about 4.3 mN of expanded uncertainty on the ±2 N plate, a TUR of 1.4 against ±20 % of 30 mN at N 0.2 N (CALC). Those verdicts use guarded acceptance, or a finer tangential stage is fitted.

### Procedure

**On R9 (DEC-058).** The voice coil sets F_c, read by the in-line cell; the plate measures N and the friction. The normal-force levels below are reached by setting F_c, and they are measured, not imposed. Up to 2 N is reachable at every tilt with the 250 g cell; the 4 N level needs a larger in-line cell at most tilts (CALC, N = F_c / (sin θ − μ cos β cos θ), §0.11; open, §47). Parts 1–2 run as EXP-T01, which adds a grid at the spring-loaded refill's forces (F_c 0.08, 0.15 and 0.30 N); Part 4 runs within EXP-T02 and Part 3 as EXP-T03.

- **Part 0: refill metrology.** 10 refills per ink type:
  - mass;
  - centre of mass from the ball;
  - overall length and tube diameter against ISO 12757-1 type D (length 67 +0.3/0 mm, tube Ø 2.35 0/−0.05 mm; CON-22);
  - ball diameter and protrusion.
- **Part 1: static indentation.** θ = 50°. N ramps 0 → 2 N → 0 at 0.2 N/s for each paper × underlay, three repeats (R9's indentation ramp; the secant of AC-B01-08 needs only 0.5–1.5 N). Record N and vertical displacement → contact stiffness (secant 0.5–1.5 N) and hysteresis.
- **Part 2: steady-sliding map.** A fresh track for every stroke (lateral offset ≥ 1 mm); stroke length 20 mm; the first and last 2 mm are excluded from analysis.
  - *Core grid* on the nominal ink and paper (oil-based, ISO test paper, hard underlay): N ∈ {0.2, 0.5, 1, 2, 4} N × θ ∈ {35, 45, 55, 65, 80}° × β ∈ {0, 45, …, 315}° × v ∈ {1, 10, 30, 100} mm/s. That is 800 conditions, each repeated 3 times with 3 refills (one refill per repeat), in randomised order.
  - *Reduced grid* on each of the 8 other ink × paper combinations and on the two soft underlays: N ∈ {0.5, 1, 2} × θ ∈ {45, 60} × β ∈ {0, 90, 180, 270} × v ∈ {10, 30}. That is 48 conditions × 3 repeats.
  - *Reference condition* (ISO 12757-1 write test, CON-21): 1.5 N, 75°, 75 mm/s, on every ink and paper, for comparison with manufacturer data.
- **Part 3: reciprocation** (EXP-T03, optional, after G1). R13's disturbance stage on R9's head reciprocates the pen along t1 (in the tilt plane) and t2 (lateral).
  - Grid: amplitude ∈ {0.02, 0.05, 0.1, 0.2, 0.5} mm × f ∈ {3, 5, 8, 10, 12, 15} Hz × N ∈ {0.5, 1, 2} N × θ ∈ {45, 60}°.
  - Each condition is run with and without a superimposed slow drift of 10 mm/s. The drift represents writing motion under tremor: the ball keeps rolling.
  - 5 s per condition, 3 repeats.
- **Part 4: ink-continuity threshold.** At v = 30 mm/s and θ = 50°, N ramps linearly from 1.0 to 0.05 N over a 100 mm line, on every ink and paper, 5 repeats. The line is scanned with R3; the threshold is the normal force at which the gap fraction first exceeds 1 %. On R9 it runs within EXP-T02, whose fixed-force lines confirm the threshold; it is reported both as N and as F_c.

### Sample size and repeats

- The core grid has 3 repeats × 3 refills. It separates refill-to-refill variance from within-refill variance with a two-level random-effects model.
- To resolve the ±15 % model band with TUR ≥ 4 (per-condition half-width ≤ 3.75 % of the mean), three repeats are enough if the within-condition CV is ≤ 2.4 %: E = t₀.₉₇₅,₂ · s/√3 = 4.30 · s/1.73. If the pilot CV is larger, repeats increase to 6.
- Part 0 uses 10 refills per type: a tolerance check, 0/10 out of tolerance required (AC-B01-10).

### Data format

On R9, DAQ-1 records one session per block; MARK events cut the conditions, and the records follow the `s2r-bench-1` layout (`docs/measurement_rig.md` §2.5):

- the axial force F_a (in-line cell) and the plate forces F_x, F_y, F_z at 4 kS/s, on one clock;
- the head encoders x, y;
- the slide Hall signal and the voice coil's current reference;
- vertical displacement (Part 1; R9's spec names no sensor for it yet, an open item of §47);
- the sync pulse;
- attributes: θ, β, v, F_c setpoint, ink lot, paper batch, underlay, refill id, T, RH.

Scans for Part 4 follow R3. Metadata and naming follow `records/README.md`.

### Analysis

1. The plate measures the contact force in the page frame {P}: N = −F·n, and friction f is the in-plane part (steady window: the first and last 2 mm excluded, speed within 20 %). Transform into the pen frame (a, t1, t2) with the measured θ and β (P-1): μ = \|f\|/N; |R⊥| = \|F − (F·a)a\|. The axial part closes against F_c from the in-line cell (`rig.contact.analyse_stroke`).
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
8. **Uncertainty** (AC-B01-09). Plate and cell calibration, angle error (∂|R⊥|/∂θ = N·sin θ at μ = 0), crosstalk and thermal drift. The budgets are in `docs/measurement_rig.md` §2.4: R⊥ about 4.3 mN, so the 10 mN floor of AC-B01-09 is judged with guarded acceptance (TUR 2.4).

### Acceptance criteria

<!-- AC-TABLE:EXP-B01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B01-01 | REQ-ACT-001 | Mean transverse contact reaction \|R⊥\| (component of the measured contact force perpendicular to the pen axis), averaged over 8 stroke directions, steady sliding, N = 1.00 ± 0.05 N, θ = 50°, v = 30 mm/s, nominal ink/paper (oil-based D1, ISO 12757-1 test paper, hard underlay) | ≤ 0.75 N | requirement | REQ-ACT-001 continuous capability 0.75 N; prediction 0.64 N (results/sim/nominal/metrics.json static, v0.4.4; P-6 with mu 0.15) | DEC-003; DEC-008; actuator freeze |
| AC-B01-02 | REQ-ACT-001 | 99th percentile of \|R⊥\| (1 kHz samples, all 8 directions, v 3-100 mm/s) over the proposed product envelope N ≤ 1.2 N and θ ≥ 45°, all inks, papers and underlays | ≤ 1.4 N | requirement | REQ-ACT-001 2-s capability 1.4 N; envelope from COR-26 | DEC-008; REQ-ACT-001 revision |
| AC-B01-03 | — | Contact model P-6: fraction of map conditions (θ 35-80°, all beta and v) in which \|R⊥\| predicted with mu(N) fitted per ink/paper/underlay on θ = 50° data is within ±15 % of the measured mean; on rig R9 (EXP-T01, DEC-058) F_c is set and N measured, so the check is made on R_perp/F_c against P-6/P-7 | ≥ 90 % | hypothesis | docs/physics.md model-validation table (Contact P-5...P-9: \|R⊥\| within ±15 %); 90 % coverage engineering judgement; proposed on R9 as AC-T01-03 (docs/measurement_rig.md s2.6) | sim contact model; EXP-B09 comparability |
| AC-B01-04 | — | Kinetic friction coefficient μ_k = mean \|tangential force\| / N in steady sliding at N 1 N, θ 50°, v 30 mm/s, for every ink x paper x underlay | within 0.09-0.40 | hypothesis | CON-13 (0.09-0.17 at 90°), CON-14 (0.10-0.40); config writing.mu_eff range 0.05-0.35 (assumption) | config writing.mu_eff range; Monte Carlo re-run (kf_asr ratio most sensitive to mu, results/sim/mc_sensitivity.json) |
| AC-B01-05 | — | Breakaway ratio: peak tangential force in the first 2 mm after a 1 s dwell / steady kinetic tangential force, per condition | within 1.0-2.0 | hypothesis | config writing.mu_static_ratio range 1.0-2.0 (assumption, nominal 1.3) | config mu_static_ratio; DEC-011 revisit (breakaway transients) |
| AC-B01-06 | — | Friction ripple: RMS of the 3-15 Hz band-passed tangential force / its mean, steady sliding, nominal ink/paper, v 10-75 mm/s | ≤ 0.25 | hypothesis | CON-15 (friction varies about ±25 % along strokes) | servo disturbance model; REQ-MECH-005 budget |
| AC-B01-07 | — | Minimum normal force for continuous ink: lowest N at which the ink gap fraction over 100 mm is ≤ 1 % (v 30 mm/s, θ 50°), worst case over inks and papers | ≤ 0.30 N | hypothesis | constant-force nib Fc = 0.30 N assumed for configuration D (results/thermal/thermal.json case D); 1 % gap definition engineering judgement | DEC-008 (configuration D feasibility) |
| AC-B01-08 | — | Normal contact stiffness of paper + underlay: secant slope of N vs indentation between 0.5 and 1.5 N at θ 50°, each paper x underlay | within 1e4-2e5 N/m | hypothesis | config writing.paper_stiffness range (assumption) | config paper_stiffness; DEC-011 (stage-against-paper mode ~180 Hz) |
| AC-B01-09 | — | Measurement qualification: expanded uncertainty (k = 2) of \|R⊥\| over 0.2-4 N | ≤ max(3 % of reading, 10 mN) | derived | derived: TUR ≥ 5 against the ±15 % model band of AC-B01-03 | validity of all EXP-B01 verdicts |
| AC-B01-10 | REQ-MECH-008 | Refill metrology (Part 0), 10 refills per type: overall length and tube diameter against ISO 12757-1 type D (length 67 +0.3/0 mm, tube 2.35 0/-0.05 mm) | 10/10 within tolerance | derived | CON-22 (ISO 12757-1:2017 Fig. 2); tolerance stack S5 in mechanics/README.md (VERIFY ISO class) | DEC-004; refill seat (REQ-MECH-008); Hall force re-zero (S5) |
| AC-B01-20 | REQ-ENV-002 | Transverse reaction map covers normal force 0.2-2.0 N at 35-75° with the stated repeats (coverage of the declared envelope, not a pass on load); on rig R9 (EXP-T01, DEC-058) N is reached by setting F_c, and EXP-T01's own grid (θ 35/50/75° x 8 directions x 4 speeds x 3 F_c on the nominal refill-paper pair, a reduced grid on the other 23 pairs) is covered too | ≥ 100 % of the grid points | requirement | REQ-ENV-002 range; COR-26 writer means 0.56-2.08 N; proposed on R9 as AC-T01-06 for EXP-T01's grid alone, whose F_c of 0.08-0.30 N gives N of only about 0.1-0.7 N (CALC, mu 0.15; docs/measurement_rig.md s2.5) | REQ-ACT-001 revision; DEC-008 |

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
| Plate and axial-cell thermal drift | Zero before each condition; interleave check-standard weights every 50 conditions. |
| Pen-holder compliance changes θ under load | Measure θ under 4 N with an inclinometer; correct in analysis. |
| Ink depletion and ball wear over thousands of strokes | Log the track length per refill; replace at 50 m; include the refill id as a random effect. |
| Paper tearing at 4 N / 35° on the soft underlay | Abort the condition if the tangential force exceeds 3 N; log it. |
| The axial cell reads the head's acceleration (about 19 mN per m/s² from the 19 g of moving parts, CALC) | The slide signal is logged, so the analysis bounds it (`docs/measurement_rig.md` §2.2). On R9 the platen never moves; in Part 3 the pen does. |
| Operator bias in scan thresholds | Automatic pipeline with frozen parameters; blind coding (§0.6). |

---

## 3. EXP-B02: Friction vs speed; LuGre identification

### Purpose and what it gates

This experiment identifies the parameters of the LuGre friction model P-9 (σ0, σ1, σ2, μs, μk, v_s, all normalised by N) for the nib–paper contact at writing loads. It includes velocity reversals and pre-sliding at tremor amplitudes, which no published source covers (CON notes §2.4).

- **Validates** P-9 against the physics.md acceptance (fit R² > 0.9, applied after per-record mean removal), together with two model-form tests that R² misses (AC-B02-04, AC-B02-05).
- **Supplies** the simulator's contact model before any bench–simulation comparison in EXP-B09.
- **Gates** DEC-011 (revisit trigger: "Bench servo tests with real paper stacks").

Friction is the dominant parameter for estimator performance in the Monte Carlo (`results/sim/mc_sensitivity.json`; `docs/sim_report.md` §3), so this experiment carries more weight than its size suggests.

**Rig (study M).** Runs on R9 with the R13 disturbance stage on its head, as EXP-T03 (optional, after G1; §47, `docs/measurement_rig.md` §2.5). `s2r.exp_b01b02.identify` reads the records unchanged.

### Hypotheses

- **H-B02-1.** A single-state LuGre model fitted on velocity steps and sweeps predicts held-out sinusoidal reciprocation (3–15 Hz). Three tests judge this together:
  - R² > 0.9 after removing each record's mean (AC-B02-01);
  - a small-amplitude force error ≤ 0.10 of μ_k·N (AC-B02-04);
  - a pre-sliding length that does not drift with sweep amplitude (AC-B02-05).

  In twin experiments the raw pooled R² first used here passed a friction-memory truth and failed the correct model on a low-friction ink ([`sim_to_real.md`](sim_to_real.md) §5, §6 item 4; SIMULATION).
- **H-B02-2.** The Stribeck velocity lies in 0.5–10 mm/s, the declared simulation range (AC-B02-02). It is judged only where the Stribeck dip is resolved.
- **H-B02-3** (characterised, not accepted). Breakaway rises with dwell time before motion (pen-down after a pause).

### Equipment and setup

- Rig R1 with the linear-motor stage (velocity ripple ≤ 1 % from 0.01 to 200 mm/s; AC-B02-03).
- The F/T sensor calibrated at 45° and 60° as in EXP-B01 set-up item 4 (per-axis gains and cross-axis terms to ±0.2 %).
- A capacitive or interferometric sensor (≤ 10 nm resolution) on the pen holder for pre-sliding displacement.

### Procedure

The nominal ink and paper on the hard underlay, plus the lowest-μ and highest-μ ink × paper combinations found in EXP-B01. N ∈ {0.5, 1, 2} N, θ ∈ {45, 60}°.

1. **Velocity steps.** From rest to v ∈ {0.01, 0.03, 0.1, 0.3, 0.56, 1, 1.8, 3.2, 5.6, 10, 18, 32, 100, 200} mm/s, in both directions along t1 and t2, after a dwell of 1 s. 3 repeats.
   - The quarter-decade speeds 0.56–32 mm/s replace 3 and 30 mm/s, so that the Stribeck transition has enough points.
   - In twin experiments on the reduced grid (1 N, 50°), the half-decade speeds left `writing.stribeck_speed` at 11 % error (95th percentile); quarter-decade speeds brought it to about 4 % ([`sim_to_real.md`](sim_to_real.md) §2 item 8; `docs/sim_to_real.md` §3.2; SIMULATION).
2. **Slow triangular sweeps through zero velocity.** Amplitudes 5 µm, 20 µm, 50 µm, 0.2 mm, 1 mm and 2 mm, to capture pre-sliding hysteresis and the transition to gross sliding. The 5 µm–1 mm sweeps carry the pre-sliding drift test (AC-B02-05), as in the twin experiments.
3. **Dwell series.** 1, 10 and 60 s at rest before a 10 mm/s step. 3 repeats.
4. **Validation set (not used for fitting).** Sinusoidal reciprocation at 3–15 Hz, amplitudes 0.02–0.5 mm, reusing the EXP-B01 Part 3 protocol and fresh tracks.

### Sample size

- Three repeats per step condition.
- The fit uses all steps and sweeps (≈ 500 step records per ink × paper with the 14 speeds). The validation set has ≥ 30 records per ink × paper.
- R² is reported with a bootstrap 95 % CI over records.

### Data format

As EXP-B01, plus the displacement channel at 10 kHz.

### Analysis

1. Fit the steady-state curve g(v) = μk + (μs − μk)·exp(−(v/v_s)²) plus viscous σ2·v/N on the plateau values of the velocity steps.
2. Fit σ0 from the initial slope of force against displacement at reversals, and σ1 from the damping of the pre-sliding response.
3. Simulate the validation records with the fitted parameters (the same integrator as `sim/pensim/core.py`). Remove each record's mean from the measured and the predicted force before scoring: the F/T cross-axis offset enters as a record mean and is not friction dynamics. Report:
   - the pooled R² (AC-B02-01);
   - the median NRMSE, relative to μ_k·N, on the records ≤ 50 µm (AC-B02-04);
   - the per-record values, and the raw pooled R² for continuity only.
4. Fit x_pre separately on each triangular-sweep amplitude and apply the drift test: χ² constancy at p < 0.01 with a 10 % practical margin (AC-B02-05).
5. Judge v_s only when the static/kinetic friction ratio − 1 exceeds 3 × its U95. Otherwise report it as not identifiable (AC-B02-02).
6. Compare with the simulator's current ranges and report which parameters fall outside.

Steps 3–5 are implemented in `s2r.exp_b01b02.identify` ([`sim_to_real.md`](sim_to_real.md) §3).

### Acceptance criteria

<!-- AC-TABLE:EXP-B02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B02-01 | — | LuGre (P-9) fit quality: R² of predicted vs measured tangential force pooled over the held-out sinusoidal reciprocation records (3-15 Hz, ±0.02-0.5 mm) after removing each record's mean; parameters fitted on velocity-step and sweep records only | > 0.9 | hypothesis | docs/physics.md model-validation table (LuGre fit R² > 0.9), applied after per-record mean removal (validation/sim_to_real.md s6 item 4c). The raw pooled R² first written here passed a friction-memory truth (0.987) and failed the correct model for a low-friction ink (0.77 at μ_k 0.035) because the F/T cross-axis offset enters as a record mean; mean-removed: ≥ 0.978 on 15 hidden plants, 0.989 for friction memory (results/s2r/c1_identification.json, c3_modelform.json; SIMULATION). Not a friction-memory detector: AC-B02-04 and AC-B02-05 are | sim contact model (P-9); EXP-B09 comparability; DEC-011; DEC-023 |
| AC-B02-02 | — | Stribeck velocity v_s from the steady-state friction-velocity fit, judged only when the Stribeck dip is resolved (static/kinetic friction ratio - 1 > 3 x its U95); otherwise reported as not identifiable | within 0.5-10 mm/s | hypothesis | config writing.stribeck_speed range (assumption). Identifiability rule (proposed, from twin experiments): validation/sim_to_real.md s6 item 6; without a dip v_s is unidentifiable (virtual-bench U95 > 1000 %) and does not affect predictions (results/s2r/c1_identification.json; SIMULATION) | config stribeck_speed; Monte Carlo re-run |
| AC-B02-03 | — | Stage velocity ripple in constant-velocity segments, 0.01-200 mm/s, pen lifted | ≤ 1 % RMS of setpoint | derived | engineering judgement (the friction-velocity curve must not be smeared by the instrument) | validity of EXP-B02 verdicts |
| AC-B02-04 | — | Small-amplitude friction dynamics (G4): median over held-out reciprocation records with amplitude ≤ 50 µm of RMS(F_pred - F_meas) / (μ_k N), each record's mean removed | ≤ 0.10 | hypothesis | validation/sim_to_real.md s4 G4 and s6 item 4a (proposed design value from twin experiments, not a measurement): correct structure 0.024 (C3 control) and ≤ 0.077 on 15 hidden plants down to μ_k 0.035 (C1); friction-memory (Maxwell-slip) truth 0.101, only just above (results/s2r/c3_modelform.json, c1_identification.json; SIMULATION) | sim contact model (P-9); DEC-011; DEC-023 |
| AC-B02-05 | — | Pre-sliding memory test: x_pre fitted separately on each triangular-sweep amplitude (5 µm to 1 mm, where resolved); drift flagged when the chi-square constancy test gives p < 0.01 and the relative spread exceeds 10 % | no drift flagged | hypothesis | validation/sim_to_real.md s5 and s6 item 4b (proposed design value from twin experiments, not a measurement; the 10 % practical margin is a design choice): LuGre control spread < 0.1 % (p 0.98); Maxwell-slip friction-memory truth 9.2 / 15.7 / 16.3 µm from the 50 / 200 / 1000 µm sweeps, spread 55 % (p < 1e-10) (results/s2r/c3_modelform.json; SIMULATION) | sim contact model (P-9: single-state LuGre vs multi-state friction); DEC-011; DEC-023 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-B02).
<!-- AC-TABLE:EXP-B02:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| AC-B02-01 or AC-B02-04 fails | LuGre is inadequate for the nib (for example because ball rolling, ink film and paper plasticity dominate). Replace P-9 with a multi-state or rolling-resistance model and update `docs/physics.md` before trusting EXP-B09 predictions. |
| The pre-sliding length drifts with sweep amplitude (AC-B02-05) | Friction memory, which a single-state LuGre model cannot represent. Use a multi-state (Maxwell-slip class) model. The drift test is the detector here: in the twin, R² barely moved (0.987 against 0.993). |
| v_s not identifiable (no Stribeck dip) | Keep `writing.stribeck_speed` at its declared range. Without a dip it does not affect the predictions. |
| Very stiff pre-sliding (tremor-amplitude motion at stick) | The paper grounds the nib in the tremor band: cancellation becomes a force problem rather than a position problem. Evaluate impedance or force control, the hypothesis listed in ACT notes §2, and re-open DEC-011. |
| Strong dwell effect | Pen-down transients need a start-of-stroke authority ramp (limiter) and must be included in EXP-B09 test paths. |

### Risks and controls

| Risk | Control |
|---|---|
| Stage velocity ripple aliasing into the friction curve | Qualify the ripple with the pen lifted (AC-B02-03). |
| F/T cross-talk dominates the friction signal of low-friction inks | Gains and cross-axis terms calibrated at 45° and 60° (Equipment); scoring on mean-removed records (Analysis). |
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

**Rig (study M).** The force map, back-EMF, R and L run on R12 as EXP-T07, the thermal steps as EXP-T08 and the Hall crosstalk as EXP-T09; R12 takes the coupons of study B's actuator too (§47; `docs/measurement_rig.md` §5.3).

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
   - L from voltage steps on the blocked coil: 16 averaged scope records, with the coil terminal voltage recorded at ≥ 12 bit; L = τ·R with R from the 4-wire reading. An 8-bit record misses the ≈ 8 mV source sag and biases L by about R_src/R ([`sim_to_real.md`](sim_to_real.md) §2 item 7).
   - Cross-check: L and R with the LCR meter from 100 Hz to 20 kHz at q = 0 and at the 4 corners, with and without back iron.
3. **Force map.**
   - 7 × 7 grid over ±1.6 mm per axis (the grid of `em_actuator.json`).
   - Currents {−0.6, −0.3, −0.1, +0.1, +0.3, +0.6} A per axis, one axis at a time, then both axes together (superposition).
   - Record the 6-axis force and torque. **Hold 0.2 s per point, and let the coil cool for ≥ 30 s after each point at ±0.3 A or more** (heating scales with I²); check ΔT by resistance. Alternatively, use longer holds with ΔT logged per point; K_f is then reported for a warm coil (K_f follows the magnet temperature, not the coil's).
   - Why: 2 s holds at ±0.6 A heat the coil by about 13 K (CALCULATION, one-node coil, median over the declared C_th range), so the ΔT < 2 K rule cannot be met with them. In twin experiments the 0.5 s-hold level matched the protocol accuracy without that heating ([`sim_to_real.md`](sim_to_real.md) §2 item 5; `results/s2r/c1_identification.json`).
4. **Linearity and saturation.** 0 → 0.8 A (hardware trip level) in 0.05 A steps at q = 0; pulses to 1.2 A of ≤ 100 ms.
5. **Back-EMF (required K_f estimate).** The shaker drives the paddle at 10, 20 and 50 Hz and ±0.5 mm with the coil open; velocity by LDV. K_f = V/ẋ shares no instrument with the force route of item 3 (F/T gain against LDV scale).
   - In twin experiments the F/T route alone gave U95 ≈ 2.3 % for K_f (TUR 4.3 against AC-B03-01's ±10 %, barely above the §0.5 minimum of 4). With back-EMF it was ≈ 1.0 % (TUR 9.6) ([`sim_to_real.md`](sim_to_real.md) §2 item 6; `docs/sim_to_real.md` §3.2).
   - The two estimates must agree within their combined U95 (G3). If they do not, the K_f verdict is inconclusive until the cause is found.
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

HDF5 per coupon: force map (q1, q2, i1, i2 → F, T), LCR sweeps, voltage-step records (≥ 12 bit), back-EMF records (terminal voltage and LDV velocity), thermal time series, crosstalk tables, gap measurements. `CAL_ACT` is exported in the ICD §3 layout (5 × 5 resampled grid).

### Analysis

1. K_f(q) is the slope of in-axis force against current at each grid point. The intercept at zero current is the magnetic spring force of the iron, the "negative stiffness" item in AMF notes §2.6. At q = 0 the force-route and back-EMF estimates are combined (weighted mean) when they agree (G3). The centre K_f (both routes), R20, L and the thermal pair are identified by `s2r.exp_b03.identify` ([`sim_to_real.md`](sim_to_real.md) §3).
2. K_m = K_f/√R. Also report the hot K_m (R at 85 °C).
3. Compare with the model rescaled to the built winding (K_f ∝ √R at fixed copper volume, P-15) and the measured gap (the gap rescaling factor comes from `mechanics/tolerance_analysis.py`).
4. Thermal: fit a first-order, then a second-order, response. Report R_th coil→ambient, R_th coil→housing and τ.
5. Crosstalk: a linear regression in T/A, converted to tip µm/A through CAL_HALL. The residual after linear compensation is the REQ-SNS-004 quantity.

### Acceptance criteria

<!-- AC-TABLE:EXP-B03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B03-01 | REQ-ACT-001 | Force constant K_f at the stroke centre (q = 0), 20 °C, per axis, from the blocked-force slope over ±0.6 A and from back-EMF (both required; they must agree within their combined U95, G3) | within 0.717 N/A ± 10 % | hypothesis | docs/physics.md (K_f within ±10 %); prediction config actuator.Kf 0.717 N/A (v0.4.1; 6 ohm winding DEC-012, 0.50 mm gap DEC-007 rev.). Back-EMF brings U95 from 2.3 % (F/T only, TUR 4.3) to 1.0 % (TUR 9.6) in twin experiments (validation/sim_to_real.md s2 item 6; results/s2r/c1_bench_time.json; SIMULATION) | DEC-012; EM model P-14 validation |
| AC-B03-02 | — | Motor constant K_m = K_f / sqrt(R20) at the stroke centre, 20 °C (feasibility floor for the Rev A research pen) | ≥ 0.29 N/√W | hypothesis | docs/plan.md s3 (K_m target ≥ 0.29 N/√W at the 0.50 mm gap); docs/research_questions.md rank 9 still states ≥ 0.3 (before the gap change); prediction 0.293 N/√W (results/electronics/drive_sense.json v0.4.1); field model 0.24-0.34 (results/em/em_actuator.json) | DEC-003; actuator freeze |
| AC-B03-03 | REQ-ACT-002 | Motor constant K_m at the stroke centre, 20 °C (level needed to meet REQ-ACT-002 at the design point) | ≥ 0.37 N/√W | derived | derived from REQ-ACT-002 (0.25 W average): K_m20 ≥ F_rms/(n*sqrt(P/duty))*sqrt(1.2555) with F_rms 0.657 N (results/trade/config_trade.json design point), n = 3.17, duty 0.65, hot factor 1.2555 at 85 °C (alpha_cu 0.00393/K, AMF-29) = 0.375; prediction 0.293 -> expected FAIL | DEC-008 (configuration B vs D/E); REQ-ACT-002 revision |
| AC-B03-04 | — | K_f(q) map: fraction of the 7 x 7 grid points over ±1.6 mm (actuator coordinates) where measured K_f is within ±10 % of the magnetostatic model rescaled to the built winding and gap | = 100 % | hypothesis | docs/physics.md (K_f(q) within ±10 %); model results/em/em_actuator.json Kx_map (v0.2.0; rescale by sqrt(R) and gap factor) | EM model validation; CAL_ACT (docs/icd.md s3) |
| AC-B03-05 | — | Coil resistance R20 (4-wire, 20.0 ± 0.5 °C) | within 6.0 ohm ± 5 % | hypothesis | DEC-012 winding (headroom analysis in results/electronics/drive_sense.json assumes 6.0 ohm); ±5 % engineering judgement | DEC-012 (voltage headroom at 3.3 V) |
| AC-B03-06 | — | Coil inductance at 1 kHz, q = 0 | within 82-380 µH | hypothesis | config actuator.L range (air-core estimate 175 µH scaled from results/em) | current-loop tuning (P-17) |
| AC-B03-07 | REQ-SNS-004 | Hall current crosstalk after linear compensation, referred to the tip (9 stage positions, DC and 40 kHz PWM) | ≤ 5 µm/A | requirement | REQ-SNS-004; measured on rig R12 in EXP-T09 at 9 fixed positions with the linear amplifier (DC) and the pen's own PWM driver (docs/measurement_rig.md s5.3), where it was proposed as AC-T09-02 | Hall placement and sampling (open issue E-4); CAL_HALL |
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
| Heating during the force map biases K_f | 0.2 s holds with cooling after high-current points (procedure 3); the resistance check before and after each point; discard points with ΔT > 2 K, or report K_f for the logged coil temperature. |
| F/T crosstalk from torques at the paddle | Calibrate the F/T with an offset load at the paddle position. |
| Coupon unrepresentative of the pen (magnet grade, iron) | Build coupons from the Rev A.1 drawings and material certificates; record magnet lot and Br. |

---

## 5. EXP-B04: Hall and optical calibration against a motion stage; page workspace

### Purpose and what it gates

This experiment calibrates the one 3-axis Hall sensor on the lever tail, which gives (q1, q2) from Bx, By and the axial slide s from Bz. The calibration is made against independent tip metrology and produces `CAL_HALL` (`docs/icd.md` §3).

- **Verifies** the page-plane correction workspace of REQ-MECH-001, the Hall noise and rate of REQ-SNS-004, and the calibrated lever-ratio gain (tolerance stack S4, `mechanics/README.md`).
- **Validates** kinematics P-1…P-4, together with EXP-B06, in the physics.md acceptance (< 5 % of stroke). A calibrated normal-compliance mount stands in for the hand.
- **Also calibrates** the scale factor of the optical modules on the nominal paper. Latency and accuracy across paper types and tilt are EXP-S01.

**Rig (study M).** The optical scale (procedure 5) runs on R10 in EXP-T04 (§47; `docs/measurement_rig.md` §3.5); the Hall calibration stays with the nib build.

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

It validates P-10…P-12 (resonance ±10 %, stiffness ±15 %) and, through the model-form diagnostics of AC-B05-15, the structure of the stage model. In twin experiments the ±10 % resonance check alone passed every structural defect tried except a collapsed fit ([`sim_to_real.md`](sim_to_real.md) §5; SIMULATION).

It runs twice: on the Stage A rig module (commercial VCMs through the same 3.17 lever, `mechanics/README.md`) and on the Rev A/A.1 pen at Stage B. Each run uses its own predictions.

**Rig (study M).** The in-contact FRF (procedure 3) and the loaded margins (procedure 5) run on R13 in EXP-T10 (§47; `docs/measurement_rig.md` §6.3). The free-space parts stay with the nib build, and the `s2r.exp_b05` methods are unchanged.

### Hypotheses and predictions

| Quantity | Prediction | Source |
|---|---|---|
| k_tip | 75.8 N/m | `results/mechanics/flexure_calc.json`, gimbal 0.05 × 1.0 × 2.0 mm. The config carries 80 N/m since v0.4.2 (`stage.k_tip`: the gimbal plus a coil-lead allowance; `README.md` §6.8) |
| m_eq | 13.7 g | Distributed-mass CAD, Rev A.1 (REQ-MECH-003 current estimate); `stage.m_eq` 13.7 g in the config since v0.4.2 |
| Open-loop first mode | (1/2π)·√(75.8 / 0.0137) = 11.8 Hz | calculation from the two rows above |
| k_ax | 1984 N/m | `results/mechanics/flexure_calc.json` |
| Axial overload stop | 0.6 mm, 1.45 N | config `stage.axial_travel` |
| Current-loop crossover | 2.0 kHz as implemented (55.8° phase margin); 2.34 kHz is the limit for 50° | `results/electronics/drive_sense.json` |
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

1. **Static transverse stiffness.** ±0.03 N at the tip in 8 directions with the coils open-circuit (no current), or a probe force set from the pilot FRF (item 3, run first) so that |q| ≤ 0.8 × the stop radius; fit only points inside that radius. Load–unload, 3 cycles; stiffness and hysteresis. A ±0.2 N load would deflect the tip about 2.5 mm at 80 N/m, four times the stop radius ([`sim_to_real.md`](sim_to_real.md) §2 item 2).
2. **Axial.** 0 → 2 N → 0 along the refill, 3 cycles: preload knee, secant k_ax, stop position and force.
3. **Open-loop FRF** ([`sim_to_real.md`](sim_to_real.md) §2 items 1, 3, 4, 9 and 10):
   - **Shaped chirps, not a flat 0.05 A chirp.** A flat 0.05 A chirp from 1 Hz would drive the free stage into its stops: n·K_f·0.05 A / k_tip ≈ 1.4 mm static against a 0.60 mm stop, and about 10 times more at the 11.8 Hz resonance (CALCULATION).
   - **Pilot and amplitude ladder.** A pilot chirp shaped for 5 µm on the nominal plant; then chirps at 5 % and 25 % of the target amplitude, each shaped on the FRF of the previous one; all capped at 0.05 A. Abort any chirp whose Hall peak exceeds 0.8 × the stop radius. In twin experiments with 0.3 mN of pivot friction, a chirp shaped on the pilot alone reached 0.65–6.8 mm; with the ladder every chirp stayed within 0.39 mm.
   - **Three excitation levels**, about 10, 30 and 100 µm at the tip in the flat part of the spectrum. Each level has 3 estimation chirps and 1 held-out chirp of 10 s, 1–500 Hz, for the model-form diagnostics (AC-B05-15).
   - **Logging.** The injected current reference is logged as float32 (test-build record or annotation), not only through the 0.1 mA research frame: a 30 µm shaped chirp needs only 0.1–0.2 mA in the resonance band.
   - **Estimator.** H = S_ry/S_ru against the known digital excitation r (instrumental variable), not H1: current-measurement noise biases H1 low near the resonance, and the IV ratio also cancels the clock offset between the pen and the rig DAQ. Response from Hall and LDV; coherence ≥ 0.9 required.
   - Free first, then in contact on 3 paper stacks at N ∈ {0.5, 1, 2} N and θ ∈ {35, 50, 75}° (mid level, 3 + 1 chirps per condition).
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

- Free FRF: the pilot and the ladder, then 3 levels × (3 estimation + 1 held-out) chirps. This takes about 5 min, against 3 min for a pilot plus 10 chirps at one level. At protocol noise, two 10 s chirps per level identified k_tip, m_eq and ζ as well as ten in twin experiments (`docs/sim_to_real.md` §3.2). The variance of the FRF estimate follows from the coherence.
- Margins are computed per condition; the minimum over the declared range is the verdict quantity.
- Stops: 12 directions × 3 velocities × 3 repeats.

### Data format

HDF5 FRF files (complex H(f), coherence, raw time series including the float32 current reference, one group per chirp and level; the `s2r-bench-1` layout of [`sim_to_real.md`](sim_to_real.md) §3 maps one to one); a margin table per condition; high-speed video (lossless) for stop events; `CAL_AXIAL` in ICD §3 layout.

### Analysis

1. Fit a second-order model plus delay to the open-loop FRF (IV estimate): m_eq from the mass line above resonance (it needs n·K_f from EXP-B03), k_tip from the static test and the resonance, damping from the half-power width. Compute the loop delay within the pen's own clock domain (command against Hall in the pen log): the §0.4 synchronisation bound (±50 µs) is as large as the delay being measured. Code: `s2r.exp_b05.identify`.
2. Margins from the measured loop gain, with no model in between.
3. Stop stress: the blade strain against impact velocity, extrapolated to the worst case with the beam model (P-12). Uncertainty includes gauge factor and placement.
4. Chatter: the event detector runs on the contact flag (force-plate threshold 0.05 N with 20 ms hold).
5. **Model-form diagnostics** (AC-B05-15; [`sim_to_real.md`](sim_to_real.md) §5, code `s2r.modelform`): band χ²/dof in seven bands from 2 to 300 Hz; the G1 band ratios; the held-out output error against the sensor noise of the record's quiet tail, with whiteness; the drift of f_n, ζ, m_eq and Hall delay across the three levels; the Hall delay against design (G2). In twin experiments each constructed defect left a different pattern (flexure mode, extra delay, pivot friction, backlash; table in [`sim_to_real.md`](sim_to_real.md) §5).

### Acceptance criteria

<!-- AC-TABLE:EXP-B05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B05-01 | — | Open-loop first transverse resonance (current-driven chirp, no contact) | within prediction ± 10 % | hypothesis | docs/physics.md (resonance within ±10 %); prediction from as-built k_tip and m_eq, currently 11.8 Hz (75.8 N/m, results/mechanics/flexure_calc.json; 13.7 g, REQ-MECH-003 estimate) | stage model P-10...P-12 validation; servo design |
| AC-B05-02 | REQ-MECH-003 | Tip-equivalent inertia m_eq from the mass line of the transverse FRF | ≤ 12 g | requirement | REQ-MECH-003; current estimate 13.7 g (distributed-mass CAD, Rev A.1) -> expected FAIL | carrier material (M-6 CFRP option); REQ-MECH-003 revision |
| AC-B05-03 | — | Static transverse tip stiffness k_tip (probe force ±0.03 N, or set from the pilot FRF so that \|q\| ≤ 0.8 x stop radius, fitting only points inside that radius; 8 directions) | within 75.8 N/m ± 15 % | hypothesis | docs/physics.md (stiffness within ±15 %); results/mechanics/flexure_calc.json gimbal 0.05 x 1.0 x 2.0 mm; config stage.k_tip 80 N/m since v0.4.2 (gimbal plus coil-lead allowance). Probe force per validation/sim_to_real.md s2 item 2: ±0.2 N would deflect the tip about 2.5 mm, beyond the 0.60 mm stop; with ±0.03 N the twin recovered k_tip to 0.54 % (95th percentile, results/s2r/c1_identification.json; SIMULATION) | stage model validation; config stage.k_tip |
| AC-B05-04 | REQ-ACT-003 | Closed-loop current bandwidth (-3 dB of i/i_ref) | ≥ 2 kHz | requirement | REQ-ACT-003; prediction: crossover 2.0 kHz as implemented, 55.8° phase margin (results/electronics/drive_sense.json); the firmware step test's 125 µs rise implies about 2.8 kHz closed-loop bandwidth (0.35/t_r, results/firmware/test_report.txt) -> expected PASS | DEC-012 (40 kHz PWM) |
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
| AC-B05-15 | — | Stage model-form diagnostics on the shaped open-loop chirps at three excitation levels (about 10, 30 and 100 µm at the tip): (i) noise-normalised FRF chi-square/dof ≤ 4 in each of seven bands 2-300 Hz; (ii) G1: band-mean \|H_meas/H_twin\| off resonance ≤ 1 dB and 5°, within f_n/1.3 to 1.3 f_n ≤ 3 dB and 20°; (iii) held-out output-error RMS ≤ 1.3 x the sensor noise of the record's quiet tail (whiteness reported, not judged); (iv) no drift of f_n, zeta, m_eq or Hall delay across levels beyond 1 %, 5 %, 1 % or 5 µs where the chi-square constancy test gives p < 0.01; (v) Hall loop delay within design ± 25 µs (G2) | all five pass at every level | hypothesis | validation/sim_to_real.md s4 (G1, G1chi, G2) and s5 (proposed design values from twin experiments, not measurements; the drift margins were set after the first control run):the M1-structure control passes all five at all levels; a 220 Hz flexure mode, 150 µs extra loop delay, 0.3 mN pivot friction and ±2 µm backlash each fail at least one, while AC-B05-01 (resonance ±10 %) passes all of them except the collapsed flexure fit (results/s2r/c3_modelform.json; SIMULATION with ASSUMED effect sizes) | stage model P-10...P-12 validation (with AC-B05-01, AC-B05-03); frozen EXP-B09 predictions; DEC-023 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (15 rows for EXP-B05).
<!-- AC-TABLE:EXP-B05:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| m_eq > 12 g (expected: 13.7 g predicted) | REQ-MECH-003 is violated. Adopt the CFRP carrier option (~9.5 g, M-6) or revise the requirement with a servo analysis showing that 60 Hz is still reachable. |
| Position bandwidth < 60 Hz or margins below 40° / 6 dB in contact | The servo is re-designed (gains, notch at the paper mode) before EXP-B09. If the margins fail only on soft underlays, the declared contact range is narrowed. |
| Chatter with the feedforward disabled | The DEC-011 fix does not hold on real paper. Add an explicit paper-mode notch or lower the servo stiffness; re-run the Monte Carlo with the measured paper stiffness. |
| Model-form diagnostics fail (AC-B05-15), even with the resonance inside ±10 % | The stage has physics the model lacks; the failing tests point to which (a mode in the fit band, extra delay, pivot friction, backlash). Model it and re-identify before the EXP-B09 predictions are frozen. A mode inside the fit band is a reason to model it, not to narrow the band. |
| Stop stress > 310 MPa | Softer stop faces or a lower slew limit (`P-22` 0.08 m/s) before any human use. |
| k_ax or the stop force out of range | DEC-006 and the axial suspension design (DEC-007 rev.) are revised; the force re-zero procedure is updated. |

### Risks and controls

| Risk | Control |
|---|---|
| Injection destabilises the loop | Amplitude ramp; hardware current trip armed; first run on the rig module with commercial VCMs. |
| An open-loop chirp drives the stage into its stops | 5 µm pilot and the 5 % / 25 % ladder; 0.05 A cap; abort at 0.8 × the stop radius (procedure 3). |
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

**Rig (study M).** The coupon part runs on R12 in EXP-T08 and the pen part on R13 in EXP-T15 (§47; `docs/measurement_rig.md` §5.3, §6.3).

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
| AC-B07-01 | REQ-THM-001 | Maximum temperature of continuously held surfaces (grip 0-40 mm and actuator bulge) with a 33 °C hand phantom, 25 °C ambient, steady state at the design-point average copper loss (0.31 W), referred to the rated 30 °C room (measured - room + 30 °C, ECMA-287 B.5) | ≤ 41 °C | requirement | REQ-THM-001 design target (DEC-045: 41 °C in a rated 30 °C room; was 41 °C at 25 °C ambient); design-point loss from results/thermal/thermal.json (config B design) | G-S (human use); thermal governor limits |
| AC-B07-02 | REQ-THM-001 | Maximum held-surface temperature during the 30-min duty-cycle replay including the 2-s 1.4 N transient every 5 min, 25 °C ambient, referred to the rated 30 °C room (measured - room + 30 °C, ECMA-287 B.5) | ≤ 43 °C | requirement | REQ-THM-001 absolute limit in a rated 30 °C room (DEC-045; was 43 °C at 25 °C ambient) (ECMA-287 Table 5.2 and B.5; IEC 60601-1 Table 24; AMF-34, AMF-35) | G-S |
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

**Rig (study M).** The modulated-force lines run on R9 as the optional part of EXP-T02, with the voice coil modulating F_c (§47; `docs/measurement_rig.md` §2.5).

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

**Rig (study M).** The one-axis precursor runs on R13 as EXP-T10 and the two-axis test as EXP-T13 (§47; `docs/measurement_rig.md` §6.3). The elements of REQ-VAL-001 are kept.

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

Predictions are regenerated with the identified rig parameters before the test (§0.2), in the order of [`sim_to_real.md`](sim_to_real.md) §2: EXP-B03 → B05 → B01/B02, the sensor values from EXP-S01/B04, and the hand at the R2 simulant's as-set values (not its targets). The frozen prediction runs the firmware constants of the tested build (fixed firmware, DEC-023). The current values, v0.4.4, at θ 50°, N 1 N, 0.3 mm peak, test seeds 200–203 (`results/sim/nominal/metrics.json`), and the grid over 12 seeds (`results/sim/sweeps/summary.json`, `grid.csv`):

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
- **H-B09-2.** The simulator, re-parameterised to the rig, predicts the ORACLE and KF ratios within ±0.1 (AC-B09-03), the NEUTRAL error within 15 % and the hold copper loss within 5 % (AC-B09-16, AC-B09-17), and the Kalman distortion within a factor of 2 with the same verdict against AC-B09-06 (AC-B09-18). In twin experiments the calibrated twin met the ±0.1 for the ORACLE ratio on 14 of 15 hidden plants, and for the Kalman ratio only once the sensor values were identified (`docs/sim_to_real.md` §4; SIMULATION).
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
5. **Simulation agreement** (G5–G9 of [`sim_to_real.md`](sim_to_real.md) §4). For each primary cell:
   - the measured minus predicted ratio for ORACLE, KF-ASR and KF-BAL, with its CI (AC-B09-03);
   - the relative gap of the NEUTRAL M-rms (AC-B09-16) and of the static hold copper loss (AC-B09-17);
   - the measured / predicted M-dist, with both verdicts against AC-B09-06 (AC-B09-18).

   A hand resting on the paper is a condition to control and record (simulant with or without palm support), not a parameter to fit. In the twin it moved the ratios by less than 0.1 but failed the NEUTRAL-error check.
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
| AC-B09-03 | — | Simulation agreement (G5/G6): \|measured - predicted\| residual ratio for ORACLE, KF-ASR and KF-BAL at the primary cells; twin re-parameterised from EXP-B03, B05, B01/B02 and the sensor experiments EXP-S01/B04, hand at the R2 simulant's as-set values (within its ±10 % qualification; EXP-B06 percentiles set the simulant), run with the firmware constants of the tested build | ≤ 0.1 | hypothesis | docs/physics.md model-validation table (control P-19...P-24: within ±0.1 of simulation). Twin experiments (validation/sim_to_real.md s4 G5/G6, s6 items 1-2; results/s2r/c2_twin.json; SIMULATION): after B03/B05/B01-B02 and the simulant as set, ORACLE within 0.1 for 14/15 hidden plants at 6 and 9 Hz (7-8/15 with the hand nominal); Kalman ratio at 9 Hz 9/15 with the sensor keys nominal, 14/15 with them identified. The ±0.1 band is unchanged; the twin evidence is simulation, not measurement | model validation; basis of DEC-009 and DEC-016; DEC-023 |
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
| AC-B09-16 | — | Simulation agreement (G7, with AC-B09-03): \|predicted / measured - 1\| of NEUTRAL M-rms (the ratio denominator) at the primary cells, same twin as AC-B09-03 | ≤ 15 % | hypothesis | validation/sim_to_real.md s4 G7 (proposed design value from twin experiments, not a measurement): 95th percentile of the gap over 15 hidden plants 15.0 % / 13.1 % at 6 / 9 Hz with the sensor keys nominal, 8.2 % / 11.2 % with them identified (results/s2r/c2_twin.json gaps; SIMULATION). A hand resting on the paper fails it (19 % / 61 %, c3_modelform.json) | model validation (with AC-B09-03); DEC-023 |
| AC-B09-17 | — | Simulation agreement (G8, with AC-B09-03): \|predicted / measured - 1\| of the static hold copper loss M-Pcu at N 1 N, θ 50° (NEUTRAL hold in contact) | ≤ 5 % | hypothesis | validation/sim_to_real.md s4 G8 (proposed design value from twin experiments, not a measurement): worst 2.3 % over 15 hidden plants once K_f and R20 from EXP-B03 are in the twin, 113 % uncalibrated (results/s2r/c2_twin.json; SIMULATION) | thermal and power predictions (DEC-008); DEC-023 |
| AC-B09-18 | — | Simulation agreement (G9, with AC-B09-03): measured / predicted Kalman M-dist (handwriting paths, no disturbance) and the verdicts of measurement and prediction against AC-B09-06 (50 µm); both below the NEUTRAL-vs-NEUTRAL repeatability floor counts as agreement | within 0.5-2, same verdict | hypothesis | validation/sim_to_real.md s4 G9 (proposed design value from twin experiments, not a measurement): with the sensor keys identified 15/15 hidden plants within a factor of 2 and 14/15 with the same verdict; with them nominal 12/15 and 13/15 (results/s2r/c2_twin.json; SIMULATION). An absolute band is not achievable: one plant's gate never opens (0 µm) while its sensor-nominal twin predicts 410 µm | distortion predictions behind DEC-009 and REQ-CTRL-005 tuning; DEC-023 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (18 rows for EXP-B09).
<!-- AC-TABLE:EXP-B09:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| ORACLE ratio > 0.5 (AC-B09-02 fails) | The loaded mechanics cannot cancel even with perfect knowledge (stick-slip, contact dynamics, servo). **G-B fails.** No Rev A build for cancellation research until the cause is found: contact model (B02), servo (B05) or hand coupling. DEC-003 is re-opened. |
| Simulation agreement fails (AC-B09-03, or AC-B09-16…18) | A failed agreement metric is a model-form result. Run the residual diagnostics of [`sim_to_real.md`](sim_to_real.md) §5 on the EXP-B01/B02/B05 data and the B09 data, fix the model structure, re-freeze the predictions and re-test on fresh disturbance seeds. Parameters are never tuned to EXP-B09 data. Until then, simulation-based decisions (DEC-009 gate, DEC-016 ML comparison, estimator tuning) lose their basis, and EXP-E01 conclusions must rest on EXP-E02 closed-loop data. |
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
- **Pencil (DEC-021, REQ-PNC-004).** A candidate chip-scale page sensor that fits the 8.9 mm nose is tested with the same strobe and step methods against ≥ 120 Hz and ≤ 10 ms (AC-S01-08). The simulation that set this requirement modelled latency as one frame + 2 ms, so the verdict uses the median latency and reports the 99th percentile (`results/sim/page_sensor_rate.json`). The only fitting part found, the OVM6948 camera (OPT-36), runs at 30 fps and is expected to fail.

**Rig (study M).** The accuracy and noise parts (procedure 4) run on R10 as EXP-T04, and the latency parts (procedures 1–3) as EXP-T05; the strobe method stays an option (§47; `docs/measurement_rig.md` §3.5). The error per 10 ms window is judged by DeltaPen's own metric, with the vector metric beside it (DEC-059).

### Hypotheses

- At least one candidate meets REQ-SNS-001 on matte paper at 35–75° (AC-S01-01…03).
- With 3 modules at 120°, ≥ 99 % of samples at any roll have a valid module (AC-S01-04).
- Per-window error on paper is no worse than DeltaPen's median on a tablet, by DeltaPen's own metric (AC-S01-06, DEC-059).
- Nib motion and fresh ink in the field of view raise noise by ≤ 10 % (AC-S01-07).

### Candidates

- PixArt P3040-class lens-less sensors (if PixArt supplies them; OPT-06).
- PMW3360/3389-class sensors with custom short-Z optics (OPT-03/04; Flashpen route).
- PAA5100JE-class sensors at 15–35 mm as a barrel-mount option (OPT-05).
- For the pencil: the OVM6948-class chip-scale camera (OPT-36) and any faster chip-scale candidate that fits the 8.9 mm nose (DEC-021).
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
7. **IMU latency (pencil sensing, `docs/sensor_fusion_ai.md` §4).** The same piezo step and sine drive move the pen body with its IMU. Measure the accelerometer's and the gyroscope's group delay and the FIFO read latency at 3.84 and 7.68 kHz, from the capacitive reference to the sample's arrival in the firmware (AC-S01-09). The acceleration-domain Kalman filter compensates 1.04 ms of filter delay plus 0.35 ms of read latency (ASSUMPTION); the LSM6DSV16X datasheet states no latency, the BMI323 states 0.39–0.63 ms of group delay (OPT-40).

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
3. Error per 10 ms window, two ways (DEC-059). DeltaPen's own metric, the absolute difference of the translation lengths | |Δs| − |Δg| | (LIT OPT-85), median and mean: this one is judged against DeltaPen (AC-S01-06). And the norm of the vector difference |Δs − Δg| (median, mean and 95th percentile), reported beside it; it is always the larger. This step first named the vector norm as DeltaPen's definition.
4. Scale error against θ and paper, before and after the B04 calibration.
5. Valid fraction against roll.

### Acceptance criteria

<!-- AC-TABLE:EXP-S01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S01-01 | REQ-SNS-001 | Total latency from physical paper motion to the fused housing-motion estimate available to the stage task (step method), 99th percentile of ≥ 200 events | ≤ 3 ms | requirement | REQ-SNS-001 | DEC-005; optics selection (E-7) |
| AC-S01-02 | REQ-SNS-001 | Per-sample displacement noise at ≥ 1 kHz on matte paper, θ 35-75°, after removing constant velocity (linear detrend per 100 ms) | ≤ 5 µm RMS | requirement | REQ-SNS-001; measured on rig R10 in EXP-T04 (docs/measurement_rig.md s3.6), where it was proposed as AC-T04-04 | DEC-005 |
| AC-S01-03 | REQ-SNS-001 | Housing page-plane motion output rate | ≥ 1 kHz | requirement | REQ-SNS-001 | DEC-005 |
| AC-S01-04 | REQ-SNS-002 | Fraction of samples with at least one valid optical module, roll 0-360° (30° steps), θ 35-75°, 5 paper types, during writing motion | ≥ 99 % | derived | REQ-SNS-002 (valid view at any roll); 99 % engineering judgement | optics layout (3 modules at 120°) |
| AC-S01-05 | — | Tracking-loss events longer than 300 ms (ICD fault bit 4) per 10 min of scripted writing on matte paper | < 1 | hypothesis | docs/icd.md s6 fault threshold (300 ms); event rate engineering judgement | fault-handling design |
| AC-S01-06 | — | Median error per 10 ms window on matte paper at θ 55°, 10-100 mm/s, by DeltaPen's metric: the difference of the translation lengths \| \|ds\| - \|dg\| \| (DEC-059); the vector metric \|ds - dg\| is reported beside it | ≤ 24 µm | hypothesis | DeltaPen median on a Wacom surface (OPT-02): at least published state of the art, now on paper; DeltaPen's metric is the error of the translation length (LIT OPT-85), so the comparison is like for like (DEC-059; the analysis first written here used the vector norm, which is always larger); measured on rig R10 in EXP-T04 (docs/measurement_rig.md s3.6) | DEC-005; DEC-059 |
| AC-S01-07 | — | Relative increase of per-sample noise with the actuated nib moving (±0.5 mm, 10 Hz) and fresh ink in the field of view | ≤ 10 % | hypothesis | engineering judgement (OPT notes s2.5 item 4: effect unknown) | optics placement |
| AC-S01-08 | REQ-PNC-004 | Candidate chip-scale page sensor that fits inside the pencil nose (8.9 mm envelope): page-referenced position rate / latency from paper motion to the position available to the fusion (step method as AC-S01-01, median of ≥ 200 events; 99th percentile reported) | ≥ 120 Hz / ≤ 10 ms | requirement | REQ-PNC-004 and DEC-021; guided path error 0.42 of no correction at 120 Hz / 10 ms vs 0.76 at 30 Hz (results/sim/page_sensor_rate.json; SIMULATION, latency modelled as one frame + 2 ms). No part found that fits and meets it (OPT-05 too large, OPT-36 30 fps) | DEC-021 (paper capture for the pencil vs tablet fallback) |
| AC-S01-09 | — | IMU latency: accelerometer and gyroscope group delay plus FIFO read latency at the chosen ODR (3.84 or 7.68 kHz), from the capacitive reference to the sample's arrival in the firmware, 99th percentile of ≥ 200 steps | ≤ 1.5 ms | hypothesis | the acceleration-domain Kalman filter compensates 1.04 ms filter delay + 0.35 ms read latency (ASSUMPTION, docs/sensor_fusion_ai.md s4.2); LSM6DSV16X states no latency (OPT-37); BMI323 states 0.39-0.63 ms group delay (OPT-40) | AKF delay compensation (DEC-025) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (9 rows for EXP-S01).
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

**Rig (study M).** The over-current tests in contact run on R13 in EXP-T11 (§47; `docs/measurement_rig.md` §6.3).

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

**Rig (study M).** The page-sensor fault part runs on R13 in EXP-T14 (§47; `docs/measurement_rig.md` §6.3).

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
- **Pencil builds** (Rev P1 onwards, DEC-019) are weighed and balanced with the same procedure against REQ-PNC-001: diameter ≤ 9.0 mm, length ≤ 170 mm, mass ≤ 24 g including wiring and margin (AC-M03-07). REQ-FORM-001…004 are Rev A requirements and do not apply to them. CAD P0.1.2 predicts 12.2 g before wiring, adhesive and margin, with the centre of mass 88 mm from the nib (`results/cad/pencil_revPQ_summary.json`).
- **Rev K builds** (DEC-062) are weighed and measured with the same procedure against REQ-RVK-001: ≤ 24 mm across where held, ≤ 150 mm long and ≤ 75 g with every module fitted (AC-M03-08). Study K predicts 145.1 mm and 66.4 g with the balance point 74.9 mm from the tip, and 73.4 g (77.4 mm) with the heel module (CALC, `results/revK/budgets.json`). REQ-FORM-001…004 do not apply to them.

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
| AC-M03-07 | REQ-PNC-001 | Pencil builds (Rev P1 onwards): maximum barrel diameter / overall length / mass with refill, cell, wiring and adhesive | ≤ 9.0 mm / 170 mm / 24 g | requirement | REQ-PNC-001 (targets 8.9 mm and 20 g; AMF-41: 8.9 x 166 mm, 19.15 g); CAD P0.1.2: 8.9 x 166 mm, 12.2 g before wiring, adhesive and margin, centre of mass 88 mm from the nib (results/cad/pencil_revPQ_summary.json) | DEC-019 (pencil envelope); EXP-H02 (form factor) |
| AC-M03-08 | REQ-RVK-001 | Rev K builds (DEC-062): largest diameter where held (the grip from 20 mm behind the tip) / overall length / mass with every module fitted (the heel module included, when built) | ≤ 24 mm / 150 mm / 75 g | requirement | REQ-RVK-001 (DEC-062); CALC: 24 mm from z 20 mm (the front 12 mm at the ring, widening over 14 mm), 145.1 mm, 66.4 g for the base pen and 73.4 g with the heel module, balance point 74.9 / 77.4 mm (docs/revK_design.md s2, s5.1) | the Rev K envelope (DEC-062) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-M03).
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

**Pencil builds** (Rev P, DEC-019) run the same runtime procedure with the pencil's modes against REQ-PNC-005: ≥ 2 h of assisted writing and ≥ 4 h of recording (AC-P01-05). With the 90 mAh cell, P1 predicts 4.1 h of recording and 0.83 h of assist with 2 × DRV2700, or 2.7 h with a charge-recovery driver (`results/pencil/sim_metrics.json`, SIMULATION). The driver and cell behind these numbers are qualified in EXP-Q05 and EXP-Q03.

**Rev J.1 builds** (DEC-045) would run the same runtime procedure per mode against REQ-RVJ-I01, with the page sensor on in every mode: ≥ 8 h in the steady modes up to 1 mm tremor and in guide, ≥ 7.5 h in lead-through, ≥ 6 h in autowrite up to 1 mm tremor and ≥ 3.5 h at 2 mm. The end-cap row (≥ 8 h at its measured duty, ≥ 6 h at its design power) is AC-K01-05. With 2.22 Wh usable (MFR AMF-80) the Rev J.1 design predicts: steady 8.5–9.7 h at 1 mm tremor (14.8–18.9 h without); guide 12.1–16.1 h; lead-through 7.5–8.8 h; autowrite 6.5–7.4 h at 1 mm and 3.8–4.1 h at 2 mm (CALC, `results/revJ1/budgets.json`). The electronics, counted from datasheets, take 34–60 mW (EXP-J12) and the low-power page sensor 1.3–1.9 mW (EXP-J10). Every figure rests on study N's nose-coil power: at 2 × it, steady writing at 1 mm tremor lasts 4.9–5.3 h. Rev J (DEC-044) had predicted 6.1–7.3 h there.

**Rev K builds** (DEC-062) run it against REQ-RVK-002 (AC-P01-06, which judged REQ-RVJ-I01 before): ≥ 16 h in every writing mode up to 2 mm of tremor, the spelling cue included, and ≥ 8 h of lead-through with the heel module (DEC-065), with the page sensor on in every mode. Study K predicts 24.2–50.1 h with no tremor, 23.5–48.6 h at 1 mm and 21.0–48.4 h at 2 mm, 23.2–48.9 h guiding and 23.7–50.0 h with the spelling cue, and 10.8–15.0 h of lead-through with the heel module (CALC, `results/revK/budgets.json`). The low ends take magnets 30 % weaker than modelled and the electronics at the top of their datasheet range. The electronics take about half the power, and the nib the other half, mostly to hold the moving parts against gravity.

**Rig (study M).** The nib's power part runs on R13 in EXP-T15 (§47; `docs/measurement_rig.md` §6.3).

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
| AC-P01-05 | REQ-PNC-005 | Pencil builds (Rev P): runtime from full charge to the cut-off with scripted handwriting and tremor assist on (6 Hz, 0.3 mm disturbance, as the P1 battery runs) / recording only; minimum of 3 cells x 3 repeats, 25 °C | ≥ 2 h / 4 h | requirement | REQ-PNC-005; prediction with the 90 mAh cell: assist 0.83 h with 2 x DRV2700, 2.7 h with a charge-recovery driver; recording 4.1 h (results/pencil/sim_metrics.json battery; SIMULATION) -> expected FAIL with DRV2700, marginal for recording; proposed P0.2 (DEC-030): assist 2.73 h in the worst 0.3 mm case (results/opt/hardware.json; CALCULATION) -> expected PASS | product driver and cell (DEC-019); REQ-PNC-005; DEC-030 |
| AC-P01-06 | REQ-RVK-002 | Rev K builds (DEC-062): runtime from full charge to the cut-off in each writing mode (scripted writing on R2), the page sensor on in every mode: steady with no tremor and with 1 mm and 2 mm of tremor, guide, and the spelling cue with its lifts and ticks; lead-through with the heel module (DEC-065); minimum of 3 cells x 3 repeats, 25 °C | ≥ 16 h (every writing mode up to 2 mm tremor, spelling cue included) / 8 h (lead-through with the heel module) | requirement | REQ-RVK-002 (DEC-062; for Rev K it replaces REQ-RVJ-I01's rows); prediction (2.22 Wh usable, 23 °C): steady 24.2-50.1 h with no tremor, 23.5-48.6 h at 1 mm and 21.0-48.4 h at 2 mm; guide 23.2-48.9 h; spelling cue 23.7-50.0 h; lead-through with the heel module 10.8-15.0 h (CALC, docs/revK_design.md s5.2; the low ends take magnets 30 % weaker and the electronics at the top of their datasheet range). Was, against REQ-RVJ-I01 on the Rev J.1 build with the C1S nose: 8 h (steady, guide) / 7.5 h (lead-through) / 6 h (autowrite to 1 mm) / 3.5 h (autowrite at 2 mm), predicted 8.5-9.7 h steady at 1 mm (CALC, results/revJ1/budgets.json), figures that DEC-046 suspended | DEC-062 (Rev K's battery per mode); DEC-065 (lead-through only with the heel module) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-P01).
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
- a learned streaming TCN (`ml/`), within the ICD §5 budget;
- from the pencil sensing study (`docs/sensor_fusion_ai.md`, `fusion/`): the acceleration-domain Kalman filter (AKF) in its grid-tuned and robust sets, the per-user AKF set chosen by the 20 s calibration, the IMU-input GRU and the template prior. They run unchanged on recorded streams converted to `fusion.sensors.Streams`. Report the 3–15 Hz band residual and the false correction on tremor-free writing, including the fastest-writing quartile (AC-E01-09), next to the all-band ratio: in simulation the estimators tuned on smooth writing moved sharp writers' tremor-free ink by 123–146 µm.

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
| AC-E01-02 | REQ-ML-001 | Learned predictor vs the best conventional estimator (Kalman oscillator + gate, BMFLC, scheduled least-squares AR): reduction of the residual ratio in each of the 4-8 Hz and 8-12 Hz bands at matched false correction (≤ 25 µm RMS on tremor-free writing; gains frozen on validation writers, ml/metrics.py), held-out participants, with the 95 % paired writer-bootstrap upper bound of the difference below 0 | ≥ 0.10 in each band, CI upper bound < 0 | requirement | REQ-ML-001 pre-registered gate (also DEC-016); fixed before any real data is analysed; simulation 2026-09-28: the GRU trained on the tremor band is 0.067 better than the adjoint-tuned AKF at 57 µm false correction on sharp writers, so it fails this gate even in simulation (results/opt/tracker.json; docs/opt_tracker.md) | DEC-016; REQ-ML-001 |
| AC-E01-03 | REQ-ML-001 | Learned predictor within the docs/icd.md s5 v1.1 budget | ≤ 35k MAC; ≤ 32 kB weights; ≤ 8 kB activations | derived | docs/icd.md s5 v1.2 (exported TCN without f_est: 16.2k MAC, 7.3 kB, 0.58 kB); REQ-ML-001 (timing and energy limits) | DEC-016 |
| AC-E01-04 | REQ-CTRL-007 | Best causal estimator residual ratio in the 8-10 Hz and 10-12 Hz bands at matched FC 25 µm, test writers, benchmark E01-A | ≤ 0.8 | hypothesis | prediction 0.64-0.72 for kf_asr at 9-10 Hz (results/sim/nominal/metrics.json; results/sim/estimator_selection.json); 0.8 engineering judgement | DEC-009 (value of cancellation above the gate); EXP-H06 variant choice |
| AC-E01-05 | REQ-CTRL-007 | Best causal estimator residual ratio in the 4-6 and 6-7 Hz bands at matched FC 25 µm (confirms the gate; a value ≤ 0.8 triggers a DEC-009 revisit) | ≥ 0.9 | hypothesis | COR-11 (0.94 at 6 Hz, > 1 at 4.5 Hz in simulation); docs/sim_report.md s3.2 | DEC-009 gate frequency |
| AC-E01-06 | REQ-CTRL-007 | Per-user gate calibration: \|f_gate from a 60 s calibration - offline-optimal f_gate\| in ≥ 80 % of test participants | ≤ 1 Hz | hypothesis | engineering judgement; REQ-CTRL-007 (per-user threshold from calibration) | CAL_USER procedure |
| AC-E01-07 | REQ-CTRL-005 | False correction on healthy-control writing at the deployed gain (no-tremor ticks) | ≤ 25 µm RMS | derived | derived: half the REQ-CTRL-005 50 µm budget; equals the ml/common.py FC headline | estimator tuning |
| AC-E01-08 | REQ-ML-001 | Largest false-correction excursion (spike) of the learned predictor on the feature course (corners, dots, hatching, fast strokes) at the deployed gain | ≤ 100 µm | requirement | REQ-ML-001 (no false-correction spikes above 100 µm) and REQ-CTRL-005 corner/dot limit; synthetic result 125 µm corner spikes (REQ-CTRL-005 current estimate) -> currently failing | DEC-016; REQ-ML-001 |
| AC-E01-09 | REQ-CTRL-005 | False correction of the chosen causal estimator at its deployed gain on the tremor-free writing of the fastest-writing quartile of healthy participants (tremor-band content of intended motion highest) | ≤ 25 µm RMS | derived | derived from AC-E01-07 (half the REQ-CTRL-005 50 µm budget); simulation on sharp glyph writers: frozen Kalman 123 µm and grid-tuned AKF 146 µm (fail), robust AKF 21 µm (results/fusion/context.json; SIMULATION); the adjoint-re-optimised robust set proposed by DEC-028 18 µm, the band-target GRU 57 µm and the AKF + learned gate 53 µm (results/opt/tracker.json; SIMULATION) | DEC-025 (which AKF set ships); DEC-028 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (9 rows for EXP-E01).
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

EXP-S17 (`human_study_plan.md` §22) tests the pen's own streaming recogniser (study S, DEC-056) on the pen's recordings, with sessions held out as well as writers (REQ-APP-006). Its CER line (AC-S17-03) is the same 8 % as AC-C01-01.

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

## 25. EXP-A03: Autocorrect on real notes

### Purpose and what it gates

This experiment runs the app's autocorrect (`app/penapp/autocorrect.py`) on real, consented notes and on their real recogniser output. The evaluation so far injected uniform edit errors into corpus and note-like text (`results/ai/autocorrect.json`, CALCULATION). Real recogniser errors are not uniform edits, and names and rare words are the known failure mode (`docs/ai_guidance.md` §6, §9).

- **Requirement:** REQ-PNC-008. Autocorrect changes only derived layers that cite stroke ids; the original ink and the base recognition layer are never modified; every change is visible and reversible; a change needs a posterior ≥ 0.9 by default.
- **Decision:** DEC-020 (revisit trigger "EXP-A03 autocorrect on real notes"): digital autocorrect is the first AI feature of the pencil.
- **Predictions** (CALCULATION on synthetic notes, threshold 0.9):
  - word error 29.5 % → 16.0 % on note-like lines at 7.3 % CER, and 32.1 % → 10.5 % on corpus sentences;
  - correct words changed in 0–0.1 % of cases;
  - names and rare words wrongly changed in 6–14 % of cases without a personal dictionary, and 0 % with one.

### Set-up and equipment

- The EXP-C01 set-up (§22): recogniser adapter with pinned versions in offline mode, and double transcription with adjudication.
- Autocorrect pinned: its version (`created_by`), the default threshold 0.9, and the language model and corpus recorded by SHA-256 as inputs of the layer.
- A personal dictionary per participant, built only from sources the participant consented to (contacts, earlier accepted notes).
- **Notes:** the EXP-C01 free notes from EXP-H01 and EXP-H06 sessions, plus notes that Stage C participants write in their own use. Consent must cover this analysis (`human_study_plan.md` §3.3). The optional review of suggestions is a user task under the same ethics approval.

### Procedure

1. Freeze the recogniser and autocorrect configuration on development writers (writer-disjoint, REQ-DATA-001).
2. For each test note, record the SHA-256 of the original stroke layer and of the base recognition layer. Run autocorrect without and with the personal dictionary, then record the hashes again.
3. For every change, check that the derived layer lists from, to, posterior and stroke ranges, that the app shows it as a suggestion, and that reverting it restores the base text.
4. Score word error before and after against the adjudicated transcript. Classify every change as fixed, broken (a correct word changed) or changed but still wrong, and tag names and out-of-lexicon words.
5. Optional: participants review the suggestions on their own notes (accept or reject each), which gives the acceptance rate.
6. **Clean copy (DEC-035).** For notes of writers with 1–2 mm tremor and for tremor-free notes of healthy controls, make the app's clean copy from the recorded tip path (`aiprior/cleancopy.py`, settings frozen). Blinded readers transcribe the clean copy and, in a separate session, the raw ink of other notes. Log whether a tremor line was detected, and every letter read correctly in the raw ink but wrongly in the clean copy. The clean copy is a derived layer shown next to the untouched ink (DEC-017). Study S (SIM on real letters of 20 new writers in HW1; `docs/spelling_and_clarity.md` T6): the clean copy raised the letters read on screen from 41 to 83 % at 1 mm and 8 Hz (words 4 → 45 %), and from 47 to 52 % with real ET tremor; its tremor detector switched on for 27 % of clean words, so DEC-057 asks for a stricter detector before this step is run (AC-A03-04, AC-A03-05).

### Measurands and uncertainty

| Measurand | Definition | Uncertainty |
|---|---|---|
| WER before and after | Word-level Levenshtein against the adjudicated transcript, with the EXP-C01 normalisation | Writer-bootstrap 95 % CI |
| Over-correction | Correctly recognised words that autocorrect changes / all correctly recognised words; names and rare words also separately | Writer-clustered 95 % CI (Clopper–Pearson with a design effect) |
| Integrity | Hash equality of the original and base layers; completeness of the change list; the revert test | Exact (pass or fail) |
| Acceptance rate (optional) | Accepted / shown suggestions, per participant | Writer bootstrap |

**Sample size:** ≥ 200 notes from ≥ 30 writers (as EXP-A01), about 10 000 words. A true over-correction rate of 0.1 % then gives an upper 95 % bound of about 0.2 % with a design effect of 2 (CALCULATION).

### Acceptance criteria

<!-- AC-TABLE:EXP-A03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-A03-01 | REQ-PNC-008 | Conformity on real notes: autocorrect writes only a derived layer that cites stroke ids; original stroke layer and base recognition layer byte-identical (SHA-256) before and after; every change listed with from, to, posterior and strokes, visible and reversible in the app; default threshold posterior ≥ 0.9 | all notes conform | requirement | REQ-PNC-008; DEC-017; tested so far on synthetic notes only (app/tests/test_autocorrect.py) | autocorrect release (DEC-020) |
| AC-A03-02 | REQ-PNC-008 | Over-correction on real notes with the personal dictionary on: correctly recognised words changed by autocorrect (names and rare words also reported separately, with and without the dictionary); point estimate / upper 95 % bound, writer-clustered | ≤ 0.1 % / 0.5 % | hypothesis | prediction 0.0-0.1 % on held-out corpus text, 0 % on note-like lines, 0 % of names with a personal dictionary vs 6-14 % without (results/ai/autocorrect.json; CALCULATION with injected recognition errors); 0.5 % upper bound engineering judgement | autocorrect default threshold and dictionary (DEC-020) |
| AC-A03-03 | — | Word error rate after / before autocorrect on real notes at the recogniser's native error rate (writer-disjoint, double-transcribed ground truth as EXP-C01); upper 95 % bound, writer bootstrap | ≤ 0.8 | hypothesis | prediction 0.50-0.54 on note-like lines at 3-7 % CER and 0.33 on corpus sentences (results/ai/autocorrect.json; CALCULATION with uniform injected edits, not real recogniser errors); 0.8 engineering judgement (at least a 20 % relative reduction) | DEC-020 (digital autocorrect first) |
| AC-A03-04 | — | Clean copy (DEC-035) of recorded notes of ET writers with 1-2 mm tremor: words correctly transcribed by blinded readers from the clean copy (readers never see the raw ink of the same note first); point estimate, writer bootstrap | ≥ 90 % | hypothesis | DEC-035; prediction 97 % of words read by the app's recogniser at 1-2 mm and 6-10 Hz, against 30-59 % in the ink (results/aiprior/aiprior.json; SIMULATION on synthetic writers); 90 % engineering judgement for human readers and real tremor; study S on real letters of 20 new writers in HW1 (SIM): the clean copy raised the letters read on screen from 41 to 83 % and the words from 4 to 45 % at 1 mm, 8 Hz, and the letters from 47 to 52 % with real ET tremor (docs/spelling_and_clarity.md T6) -> may fail for words | DEC-035; DEC-057 |
| AC-A03-05 | — | Clean copy does no harm: letters read correctly in the raw ink but wrongly in the clean copy (blinded readers, per 1000 letters), AND the clean copy of tremor-free notes from healthy controls equals the recording (no tremor line detected) in at least 95 % of notes (both) | both met (1 per 1000; 95 %) | hypothesis | DEC-035; prediction: no tremor line detected on tremor-free writing, which is left unchanged (28 µm = the recorder's noise) (results/aiprior/aiprior.json; SIMULATION); thresholds engineering judgement; study S (SIM): the clean copy's tremor detector switched on for 27 % of clean words and lowered the clean letters read from 88 to 85 % (docs/spelling_and_clarity.md T6) -> part (b) predicted to fail as built; DEC-057 asks for a stricter detector | DEC-035; DEC-057 (a stricter detector) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-A03).
<!-- AC-TABLE:EXP-A03:END -->

### Decision rule and what changes

AC-A03-01 is a conformity check: a failure on any note fails it. The other two use the upper confidence bounds stated in the criteria.

| Result | Consequence |
|---|---|
| Integrity fails on any note (AC-A03-01) | Autocorrect is not released until the layer handling is fixed (REQ-PNC-008, DEC-017). |
| Over-correction above AC-A03-02 | Raise the default threshold (0.97 was the next step in the synthetic study), or make the personal dictionary a precondition of release. |
| WER ratio not below 0.8 (AC-A03-03) | Autocorrect adds little on real recogniser errors. Refit its error model to the real error statistics before release, and re-examine DEC-020's "digital first". |
| Suggestions mostly rejected | Autocorrect stays a list of suggestions and is never applied automatically. |

---

## 26. EXP-Q01: Skid friction

### Purpose and what it gates

The pencil grounds the user's writing force through a skid ring on the nose (DEC-019). The skid's friction on paper is the drag the fingers feel, and it damps housing tremor as a conventional nib does. In P1, a skid at μ 0.12 changes 3–15 Hz housing tremor by 1.04–1.07× relative to a conventional pen, while a frictionless skid raises it by 1.23–1.50× (`results/pencil/sim_metrics.json` `skid_passive`, SIMULATION). The value in use, `skid.mu` = 0.12 (range 0.05–0.25), is an assumption that this experiment replaces.

- **Requirement:** REQ-PNC-002 (the skid carries the writing force).
- **Decisions:** DEC-019; the skid material for the EXP-H03 skid prototypes.

**Rig (study M).** Runs on R9 with a skid head in place of the refill cartridge, as a head variant of EXP-T01 (§47; `docs/measurement_rig.md` §2.8). The criteria are unchanged.

### Set-up and equipment

- Rig R1 (§0.9). The pen holder carries skid-ring coupons in place of a refill: ring radius 1.4 mm (CAD P0.1.2), in POM-PTFE, PTFE and sapphire.
- The F/T sensor is calibrated at each test angle, per-axis gains and cross-axis terms to ±0.2 % (§0.9 R1). Low friction coefficients are where cross-axis error matters most (AC-Q01-02).
- Papers: ISO 12757-1 test paper, a 60–70 g/m² notebook paper and a recycled copy paper, conditioned as in EXP-B01; hard underlay and a 50-sheet pad.

### Procedure

1. **Steady sliding.** N ∈ {0.2, 0.5, 1, 2} N × v ∈ {1, 10, 30, 100} mm/s × θ ∈ {35, 50, 75}° × 4 directions. A fresh track for every 20 mm stroke, with 2 mm excluded at each end; 3 repeats; randomised order (§0.6).
2. **Breakaway.** Peak tangential force in the first 2 mm after a 1 s dwell, per condition.
3. **Check standard.** The nominal EXP-B01 refill at 1 N, 50°, 30 mm/s on the ISO paper, at the start and end of each session.

### Measurands and uncertainty

| Measurand | Definition | Target U (k = 2) |
|---|---|---|
| Kinetic skid friction μ | Mean \|tangential force\| / N over the steady window | ≤ 0.015 absolute (AC-Q01-02) |
| Breakaway ratio | Peak / steady tangential force | ≤ 5 % of reading |
| Speed and load dependence | Regression of μ on v and N, per material × paper | CI from the repeats |

The budget covers the F/T gains and cross-axis terms at the test angle, the goniometer angle (±0.1°), thermal drift and the paper batch.

### Acceptance criteria

<!-- AC-TABLE:EXP-Q01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q01-01 | REQ-PNC-002 | Kinetic skid-paper friction coefficient (tangential / normal force on the skid ring) of each candidate skid material (POM-PTFE, PTFE, sapphire) on each of 3 papers, steady sliding, N 0.5-2 N, v 10-100 mm/s, θ 35-75° | within 0.05-0.25 | hypothesis | config/pencil.yaml skid.mu 0.12, range 0.05-0.25 (assumption, EXP-Q01 measures); in P1 a frictionless skid raises 3-15 Hz housing tremor by 23-50 %, against 4-7 % at mu 0.12 (results/pencil/sim_metrics.json skid_passive; SIMULATION) | config skid.mu and P1 re-run; skid material for EXP-H03; DEC-019 |
| AC-Q01-02 | — | Measurement qualification: expanded uncertainty (k = 2) of the kinetic friction coefficient at N 0.5 N, including F/T gains and cross-axis terms calibrated at the test angle, angle error and drift | ≤ 0.015 | derived | derived: TUR ≥ 4 against the 0.07 between the 0.12 design value and the 0.05 bound of AC-Q01-01. F/T calibration at the test angle per validation/sim_to_real.md s6 item 3: with protocol-class ±2 % gains the correct friction model's held-out error reached 0.24-0.45 of μ_k N at μ_k 0.065-0.035 in twin experiments (SIMULATION) | validity of EXP-Q01 verdicts |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-Q01).
<!-- AC-TABLE:EXP-Q01:END -->

### Decision rule and what changes

AC-Q01-02 is checked first; without it the other verdicts are void. AC-Q01-01 uses simple acceptance when TUR ≥ 4, otherwise guarded acceptance (§0.5).

| Result | Consequence |
|---|---|
| μ outside 0.05–0.25 | Update `skid.mu` in `config/pencil.yaml`. Re-run P1 (`python3 -m sim.pencil.run_study`) and the skid-passive case before EXP-H03 and EXP-Q06. |
| μ near the low end of the range for a material | That material loses the passive damping a nib provides (a frictionless skid raised housing tremor by 23–50 % in P1). Prefer a higher-friction material for EXP-H03. |
| μ above 0.25, or a breakaway ratio above 2 | More finger drag and stick-slip at the nose. Drop the material, or take it to EXP-H03 only with this noted. |

---

## 27. EXP-Q02: Low-force ink line quality (sets F_c)

### Purpose and what it gates

Behind the skid, a light axial spring presses the nib on. Every stage load scales with that spring force F_c, so the lowest F_c that still writes well is the most important number still to be measured for the pencil (`docs/pencil_concept.md` §2). This experiment measures line continuity, width and density of candidate low-force D1-format refills against nib force.

- **Requirement:** REQ-PNC-002 (F_c ≤ 0.2 N, value fixed by EXP-Q02).
- **Decisions:** DEC-019 (revisit trigger "EXP-Q02 lowest usable nib force"); the refill choice.
- **Why F_c matters** (CALCULATION, the load line of `docs/pencil_mechanisms.md` §4.1 at θ 50° and μ 0.15; `results/pencil/mechanisms.json` `load_line_grid`): the loaded stroke of the Q stage is ±277 µm at F_c 0.15 N, about ±180 µm at 0.20 N, and zero at 0.30 N. REQ-PNC-003's ±0.30 mm needs F_c ≤ 0.14 N even at nominal part tolerance.

**Rig (study M).** Part A runs on R9 in EXP-T02 (§47; `docs/measurement_rig.md` §2.5); Part B needs a skid nose on R9's head.

### Set-up and equipment

- Rig R1 with the force-controlled voice-coil normal axis (0.05–0.5 N), and R3 for scans.
- Refills: at least three low-force D1-format candidates (gel, hybrid, fineliner type), 10 of each, plus the EXP-B01 oil-based refill as reference.
- Papers and conditioning as in EXP-B01.
- **Part B:** the spring-loaded refill behind the EXP-Q06 skid nose (skid material from EXP-Q01), with springs giving F_c ∈ {0.08, 0.10, 0.15, 0.20, 0.30} N and a load cell in the axial path.

### Procedure

1. **Part A, threshold.** For each refill type, paper, θ ∈ {35, 50, 75}° and v ∈ {10, 30, 100} mm/s: a 100 mm line with the nib normal force ramped from 0.5 to 0.05 N (as EXP-B01 Part 4), then 100 mm lines at fixed N_nib ∈ {0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50} N. 5 repeats on fresh tracks.
2. **Nib-force band.** At the selected F_c, N_nib is modulated by ±0.03 N at 3, 6, 9 and 15 Hz, on top of the static change of the spring force over 35–75° (AC-Q02-02).
3. **Part B, confirmation behind the skid.** The selected refill and spring in the skid nose; user force 0.5, 1 and 2 N; θ 35, 50 and 75°; 4 stroke directions.
4. Scan every sheet (R3) within 1 h, with blind coding (§0.6).

### Measurands and uncertainty

| Measurand | Definition | Target U (k = 2) |
|---|---|---|
| Gap fraction | Unfilled length / line length along the centreline (AC-B01-07 definition) | ±0.2 percentage points |
| N_nib,min | Lowest normal force with gap fraction ≤ 1 %, from a logistic fit | ±5 mN |
| F_c,min | N_nib,min × max over θ of (sin θ + μ cos θ): the spring force that keeps N_nib ≥ N_nib,min in the pushing direction (β = 180°) | Propagated, with μ from EXP-B01 |
| Line width, optical density | Per 1 mm of line | ±5 µm; ±0.02 OD |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q02-01 | REQ-PNC-002 | Lowest axial nib-spring force F_c at which the selected low-force D1-format refill writes a continuous line (ink gap fraction ≤ 1 % over 100 mm, AC-B01-07 definition) at every θ 35-75°, stroke direction and speed 10-100 mm/s on the 3 papers: F_c = N_nib,min x max(sin θ + mu cos θ), confirmed behind the skid nose (Part B) | ≤ 0.14 N | requirement | REQ-PNC-002 (F_c ≤ 0.14 N, derived from REQ-PNC-003); design value 0.15 N (config/pencil.yaml nib.spring_force, assumption 0.08-0.30 N). The stage load scales with F_c: loaded stroke about ±300 µm at 0.14 N, ±277 µm at 0.15 N, ±180 µm at 0.20 N, 0 at 0.30 N (θ 50°, mu 0.15; results/pencil/mechanisms.json load_line_grid; CALCULATION) | DEC-019 (nib force and stage load); refill choice; REQ-PNC-003 design load |
| AC-Q02-02 | — | Ink gap fraction at the selected F_c with the nib-force band applied: ±0.03 N modulation at 3-15 Hz plus the 0.04 N spring-force change over θ 35-75°, every paper, v 30 mm/s | ≤ 1 % | hypothesis | docs/pencil_mechanisms.md s2.1 (bushing band ±0.031 N with PTFE-lined bores, ±0.12 N if bare) and s2.3 (0.041 N spring-force change over the tilt range) (CALCULATION); analogue of AC-B08-05; 1 % engineering judgement | collar liner and spring rate (DEC-019 CAD); F_c selection |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-Q02).
<!-- AC-TABLE:EXP-Q02:END -->

### Decision rule and what changes

AC-Q02-01 uses simple acceptance if U(F_c,min) ≤ 12 mN: TUR 4 against the 0.05 N between the 0.15 N design value and the 0.2 N limit. Otherwise guarded acceptance applies (§0.5).

| Result | Consequence |
|---|---|
| F_c,min ≤ 0.14 N | The Q stage can keep ±0.30 mm at 50° at nominal tolerance; the Q layout stands (DEC-019). |
| 0.14 N < F_c,min ≤ 0.2 N | REQ-PNC-002 passes, but REQ-PNC-003 fails at 50° even at nominal tolerance. REQ-PNC-003 is restated or the stage redesigned before Rev P1; plate width is capped by the bore (`docs/pencil_concept.md` §4). |
| F_c,min > 0.2 N | REQ-PNC-002 fails and the loaded stroke collapses (zero at 0.30 N). Another ink or a stronger stage is needed; DEC-019 is re-opened. |
| Gaps under the nib-force band (AC-Q02-02) | Line the collar bore (PTFE, as in CAD P0.1.2) and lower the spring rate before EXP-Q06. |

---

## 28. EXP-Q03: Pencil cell pulse discharge

### Purpose and what it gates

Every pencil runtime prediction assumes a custom 6.5 × 40 mm Li-ion cylinder of about 90 mAh with 80 % usable, 0.266 Wh (`config/pencil.yaml` `battery`; ASSUMPTION, AMF-42/43 class). The cell feeds a piezo driver whose input current is pulsed. This experiment measures the usable energy and the voltage sag of candidate cells under that load. Safety and charging tests of the same cells belong to EXP-P02.

- **Requirement:** REQ-PNC-005 (runtime), through its predictions.
- **Decisions:** the cell of the pencil concept (DEC-019): the custom cell or the fallback of 3 × Panasonic CG-425A (AMF-43).

### Set-up and equipment

- Rig R7: battery cycler with ≥ 1 kS/s logging (±0.1 % current, ±1 mV), an SMU for pulse profiles, a thermal chamber at 10, 25 and 35 °C.
- At least 3 cells per candidate.
- Load profiles: 65 mW constant (recording only); the battery-current waveforms measured in EXP-Q05 for the assist cases, including the worst one (12 Hz, 0.5 mm, both axes, DRV2700) with 200 Hz haptic bursts.

### Procedure

1. Capacity at C/5 to the cell's rated cut-off, 25 °C.
2. Usable energy to 3.3 V under the recording profile and under the assist profile, 25 °C.
3. DC internal resistance (10 s pulses) at 10, 50 and 90 % state of charge, at 10 and 25 °C.
4. The worst pulse train at 10 % state of charge and 10 °C, 100 repetitions, with the minimum terminal voltage logged.

### Measurands and uncertainty

| Measurand | Target U (k = 2) |
|---|---|
| Usable energy to 3.3 V | ≤ 1 % |
| DC internal resistance | ≤ 5 % |
| Minimum terminal voltage under pulses | ≤ 5 mV, sampled at ≥ 10 kS/s |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q03-01 | REQ-PNC-005 | Usable energy of the pencil cell from full charge to the 3.3 V cut-off under the assist load profile (65 mW electronics plus the EXP-Q05 drive-current waveform), 25 °C, minimum over ≥ 3 cells | ≥ 0.266 Wh | hypothesis | config/pencil.yaml battery: 90 mAh x 3.7 V x 0.8 usable = 0.266 Wh (assumption, AMF-42/43 class), behind every REQ-PNC-005 runtime prediction (results/pencil/sim_metrics.json battery); cut-off config electrical.v_bat_min 3.3 V (inherited) | cell choice (custom 6.5 x 40 mm vs 3 x CG-425A); REQ-PNC-005 predictions |
| AC-Q03-02 | — | Minimum cell terminal voltage during the worst EXP-Q05 drive-current pulse train (12 Hz, 0.5 mm assist plus 200 Hz haptic bursts) at 10 % state of charge and 10 °C, 100 repetitions | ≥ 3.3 V | derived | derived: config electrical.v_bat_min 3.3 V (actuation cut-off, inherited by config/pencil.yaml); protects AC-Q03-01 from an early cut-off under pulses | cell choice; driver input filtering |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-Q03).
<!-- AC-TABLE:EXP-Q03:END -->

### Decision rule and what changes

| Result | Consequence |
|---|---|
| Usable energy below 0.266 Wh | Every REQ-PNC-005 runtime prediction scales down with it. Re-run the P1 battery table with the measured energy before Rev P1. |
| Sag below 3.3 V under the worst pulses | Add input bulk capacitance, limit the driver's input current, or take the CG-425A fallback. |

---

## 29. EXP-Q04: Bender characterisation and strength

### Purpose and what it gates

The Q stage uses four custom 2.6 × 36 × 0.67 mm multilayer plates made with PICMA technology (AMF-11). Their stroke, blocking force, hysteresis, creep and capacitance are data-sheet class values scaled by width. Their strength is unknown: the design uses a literature strength for poled multilayer PZT (AMF-48) scaled to the plate volume. The drop simulation shows that stops alone do not save the plates in a sideways 1 m drop (`docs/pencil_mechanisms.md` §4.6).

- **Requirement:** REQ-PNC-003 (stroke under load).
- **Decisions:** DEC-019 (revisit trigger "EXP-Q04 plate strength"); the plate supplier; snubbers and the compliant nose.
- **Model inputs replaced:** `stage.bender_free_stroke`, `bender_block_force` and `bender_capacitance` (large-signal factor 1.3 assumed), and P1's Bouc–Wen hysteresis (12 %, ASSUMPTION).

### Set-up and equipment

- Rig R4 fixture with a clamp that copies the CAD clamp (free length 28 mm), and R5 tip metrology (≤ 1 µm).
- A stiff force sensor at the tip for blocked force (≤ 2 mN).
- A linear amplifier or DRV2700 EVM, 0–60 V differential; LCR meter; electrometer for leakage at 60 V.
- R8 axial load frame (0–10 N) for tip load to failure; stereo microscope (≥ 50×) and SEM access.
- Drop rig: 1 m free fall onto hardwood, with a pen mock-up carrying the stage in a nose, an accelerometer on the nose for the pulse, and a high-speed camera.
- At least 40 custom plates from one lot (≥ 10 for characterisation, ≥ 30 for strength), and 3 PL128.10 as reference.

### Procedure

1. **Stroke and force.** Free stroke against voltage (0–60 V differential), quasi-static and at 1–50 Hz; blocked force at the tip; the load line (tip deflection against tip load 0–0.3 N) at full drive.
2. **Hysteresis and creep.** One 8 s decaying sine sweep for a Prandtl–Ishlinskii inverse (as `s2r/piezo.py`); major loops at 0.1–10 Hz; steps held for 100 s.
3. **Capacitance.** Small signal (1 kHz) and large signal (60 V, 10 Hz); leakage current at 60 V DC after 60 s.
4. **Bare-plate first resonance** (prediction 376 Hz; data sheet 360 Hz ± 20 %).
5. **Strength.** Tip load to failure on ≥ 30 plates, clamp stress from the beam model, Weibull fit; fractography of the origins (diced edge or bulk).
6. **Drop** (on the EXP-Q07 assembly when available). Sideways 1 m drops of stage assemblies with four snubber frames and a compliant nose, spread over ≥ 3 assemblies. A few sacrificial drops without snubbers confirm the failure mode. After each drop: capacitance, a stroke re-check, and the microscope.

### Measurands and uncertainty

| Measurand | Target U (k = 2) |
|---|---|
| Free stroke, per plate | ≤ 2 µm |
| Blocked force, per plate | ≤ 3 mN |
| Major-loop hysteresis width; creep per decade | ≤ 1 percentage point |
| Capacitance (small and large signal); leakage | ≤ 1 %; ≤ 10 % |
| Weibull σ₀ and m | 90 % CI from ≥ 30 failures (likelihood ratio) |
| Drop pulse duration and peak | ≤ 10 % |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q04-01 | REQ-PNC-003 | Free tip stroke (0-60 V differential, quasi-static) and blocked tip force of every custom 2.6 x 36 x 0.67 mm plate of the lot, clamped at the CAD free length (28 mm) | ≥ ±360 µm and 0.186 N (-20 % of the AMF-11 class, width-scaled) | hypothesis | config/pencil.yaml stage.bender_free_stroke (AMF-11 PL128.10 ±450 µm, ±20 %) and stage.bender_block_force (0.55 N x 2.6/6.15 = 0.2325 N, ±20 %). At the -20 % corner the loaded nib stroke is ±162 µm (results/pencil/mechanisms.json load_line_grid; CALCULATION); if DEC-030 is adopted, the lot is the P0.2 plates (3.23 x 39.8 x 0.96 mm, 36.3 mm free length, 3.5 mm clamp zone) and the thresholds come from results/opt/hardware.json recommended (custom-plate scaling checked against the PICMA and CTS families within ±20 %, AMF-63) | plate lot acceptance; DEC-019 stroke budget; REQ-PNC-003; DEC-030 |
| AC-Q04-02 | — | Characteristic strength of the diced custom plates: Weibull scale sigma_0 (clamp stress at tip-load failure, beam model) and modulus m from ≥ 30 plates; point estimates, 90 % CI reported | ≥ 181 MPa and m 8 | hypothesis | LITERATURE AMF-48 (poled multilayer PZT, 4-point bending: sigma_0 124 MPa, m 8) scaled to the plate's effective volume = 181 MPa (results/pencil/mechanisms.json c_stage_check_Q26 stops; CALCULATION); the PICMA material and diced edges are unknown. At these values a plate driven onto a stop fails with P 7.5e-5 per event | stop and drop design (snubbers, stop travel); DEC-019 |
| AC-Q04-03 | — | Sideways 1 m drops of stage assemblies with four snubber frames per plate stack and the compliant nose (pulse measured), spread over ≥ 3 assemblies: drops without plate fracture (capacitance within 5 % of the pre-drop value, no crack at 50x) | 29/29 (R ≥ 0.90 at C 0.95, s0.7) | hypothesis | docs/pencil_mechanisms.md s4.6: P_fail 3e-5 per drop with 4 snubbers and a pulse ≥ 2 ms, 1e-3 at 1 ms; stops alone fracture below 2 ms (results/pencil/mechanisms.json drop; SIMULATION, restitution 0.4 ASSUMPTION). The compliant nose is not yet designed | snubbers and compliant nose (DEC-019); Rev P1 use outside the lab |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-Q04).
<!-- AC-TABLE:EXP-Q04:END -->

### Decision rule and what changes

AC-Q04-01 is a lot-acceptance check on every plate, with guarded acceptance: a plate within U of the limit counts as failed. AC-Q04-02 is judged on the point estimates, with the CI reported. AC-Q04-03 is a zero-failure success run (§0.7).

| Result | Consequence |
|---|---|
| Plates below −20 % of the class (AC-Q04-01) | Reject the lot. At the −20 % corner the loaded nib stroke is ±162 µm, far below REQ-PNC-003. |
| σ₀ or m below the design values (AC-Q04-02) | Re-run the stop and drop analysis with the measured Weibull parameters; reduce the stop travel or add snubbers before EXP-Q07. |
| Any fracture in the drop run (AC-Q04-03) | Redesign the compliant nose or the snubber gaps. No Rev P1 build is used outside the lab. |
| Hysteresis or creep outside the assumed class (10–15 %; 1 % per decade) | Re-run P1 and the `s2r` piezo study with the measured values. Closed-loop Hall sensing stays in any case (`docs/sim_to_real.md` §5.4). |

---

## 30. EXP-Q05: Piezo driver efficiency and quiescent power

### Purpose and what it gates

The piezo stage holds its load at no power. The pencil's battery life is therefore set by the driver, and by the sensor noise that the damping servo turns into drive power (`docs/pencil_mechanisms.md` §5). Two DRV2700 prototype drivers draw 72 mW quiescent between them (interpolated from AMF-16), which alone limits assist to under 1.5 h. The product needs a charge-recovery stage behind a low-Iq boost (AMF-47 class), or a qualified energy-recovery part: the BOS1921/1931 (AMF-46) is rated for ≤ 820 nF, against our 2.0–2.6 µF.

- **Requirement:** REQ-PNC-005 (≥ 2 h of assisted writing).
- **Decisions:** the product driver (DEC-019); the vendor check of AMF-46 at 2–2.6 µF.

### Set-up and equipment

- Rig R7: power analyser on the battery input (±0.3 %, ≥ 10 kS/s), differential probes on both outputs, thermal camera.
- Drivers: 2 × DRV2700 EVM at 60 V; a charge-recovery half-bridge prototype per axis behind an LT8330-class boost at about 55 V; a BOS1921/1931 EVM if available.
- Loads: the real plates from EXP-Q04 (2.03 µF small signal per axis), and film capacitors of 2.0 and 2.6 µF.
- Drive profiles:
  - sine at 4, 8 and 12 Hz for 0.1, 0.3 and 0.5 mm at the nib (5.2–21 V amplitude), both axes with ellipticity 0.4;
  - the P1 drive-voltage profiles behind the battery table of `results/pencil/sim_metrics.json` (neutral; oracle at 6 and 10 Hz; Kalman at 10 Hz; guided at 6 Hz; Hall noise 1 and 0.3 µm), exported from the P1 runs;
  - 200 Hz haptic bursts (20 µm in contact; 0.1 and 0.3 mm pen up).

### Procedure

1. Quiescent battery power of each driver, enabled at 0 V output.
2. Sine drive, 60 s per point, 3 repeats.
3. Replay of the P1 profiles, 60 s each, 3 repeats, with the output-voltage tracking error logged.
4. Haptic bursts.
5. Record the battery-current waveform of each profile for EXP-Q03.

### Measurands and uncertainty

| Measurand | Target U (k = 2) |
|---|---|
| Battery-side power, per driver and profile | ≤ 1 % or 0.3 mW |
| Quiescent power | ≤ 0.1 mW |
| Output tracking error (V RMS) | ≤ 1 % of the amplitude |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q05-01 | REQ-PNC-005 | Battery-side drive power, both axes, replaying the P1 drive-voltage profile of 'tremor assist, full correction, 6 Hz, 0.3 mm' (Hall noise as built) into the plates, per driver (2 x DRV2700; charge-recovery stage) | ≤ 68 mW | derived | derived from REQ-PNC-005 (≥ 2 h assist): 0.266 Wh / 2 h - 65 mW electronics (config/pencil.yaml battery, electronics.p_active) = 68 mW. Prediction 32 mW with charge recovery, 255 mW with 2 x DRV2700 (results/pencil/sim_metrics.json battery, 1 µm Hall noise; SIMULATION) -> DRV2700 expected FAIL; proposed P0.2 (DEC-030, LT8365 boost with charge-recovery half-bridges at 58 V, 3.6 uF per axis): rail power 16-19 mW at 0.3 mm and 0.3 µm Hall noise, 31-33 mW at 1 µm (P1; results/opt/hardware.json; SIMULATION) | product driver choice (DEC-019); REQ-PNC-005; DEC-030 |
| AC-Q05-02 | — | Measured / modelled battery-side drive power for sine drive at 4, 8 and 12 Hz and 0.1, 0.3 and 0.5 mm nib amplitude, each driver, real plates (2.0-2.6 uF per axis) | within model ± 20 % | hypothesis | model: docs/pencil_mechanisms.md s5 analytic table and sim/pencil/power.py (class-B f C V_pp V_rail plus quiescent; recovery efficiency 0.85 per direction, boost 80 %, capacitance x 1.3 large-signal, DRV2700 quiescent 72 mW interpolated: all ASSUMPTIONS); ±20 % engineering judgement | P1 power model; REQ-PNC-005 runtime predictions |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-Q05).
<!-- AC-TABLE:EXP-Q05:END -->

### Decision rule and what changes

AC-Q05-01 uses guarded acceptance if the measured power lies within U of 68 mW (§0.5).

| Result | Consequence |
|---|---|
| Charge-recovery stage ≤ 68 mW on the assist profile | The product driver path holds. Runtime is then set by the cell (EXP-Q03) and confirmed by AC-P01-05. |
| Only the DRV2700 path works, or the recovery stage exceeds 68 mW | REQ-PNC-005 cannot be met. Prototypes stay tethered or bench-only, and a driver development is scheduled before Rev P1. |
| Model outside ±20 % (AC-Q05-02) | Update `sim/pencil/power.py` (large-signal capacitance, efficiencies) and re-run the battery table. |
| Hall-noise-driven power dominates | A quieter sensor, averaging or an observer-based damping loop (target ≤ 0.3 µm at 10 kSPS, `electronics.hall_noise_target`). |

---

## 31. EXP-Q06: Loaded 1-axis rig (PL128.10, D1 refill, skid nose)

### Purpose and what it gates

This is the first loaded test of the pencil mechanism. One catalogue bender (PL128.10, AMF-11) moves a D1 refill through a collar, a decoupling leaf and a rear gimbal, behind a skid nose, on the Stage A cancellation rig. It tests the load line that sizes the Q stage; the claim that the skid carries the writing force while the spring sets the nib force; and loaded cancellation along one axis.

- **Requirements:** REQ-PNC-002, REQ-PNC-003.
- **Decisions:** DEC-019 (revisit trigger "EXP-Q06/Q07 loaded stages"); the go-ahead for the two-axis demonstrator EXP-Q07.
- **Predictions (CALCULATION, `results/pencil/mechanisms.json`):** PL128.10 gives ±349 µm under the 0.170 N design load (±226 µm at −20 %), 0.39 N at the nib and 199 Hz. The nib-force band is ±0.031 N with PTFE-lined bores.

**Rig (study M).** Runs on R13 with the pencil stage in the nib holder, as part of EXP-T10 (§47; `docs/measurement_rig.md` §6.2).

### Set-up and equipment

- Rig R2 (§0.9) with the hand simulant at the EXP-B06 median settings, the disturbance stage, housing metrology and the force plate; R3 for scans.
- The 1-axis module: PL128.10; a C17200 leaf (30 µm × 1.2 mm, 5 mm span); a Ti collar with PTFE liner and magnet; the 3-D Hall sensor in the nose; an etched gimbal with a slide bushing; the second axis locked. Skid ring from EXP-Q01; nib spring at the F_c selected in EXP-Q02.
- A load cell (0–1 N, ≤ 2 mN) in the axial path between spring and refill; an LDV on the collar; a DRV2700 driver; a bench MCU running the 10 kHz servo.
- Qualification as in EXP-B09 (simulant FRF, metrology chain, synchronisation). Chirps follow the EXP-B05 pilot and amplitude ladder (§6).

### Procedure

1. **Load line.** Lifted: static probe loads of 0–0.3 N at the nib at full drive, in both directions. In contact: the stroke reached under the contact load at θ ∈ {35, 45, 50, 60, 75}° on 3 papers, in the worst stroke direction.
2. **Leaf and parasitic stiffness.** A static load across the locked axis; the stiffness of the actuated axis with the plate open-circuit.
3. **Nib-force band.** Writing strokes at user force 0.5, 1 and 2 N and θ 35–75°, with the stage moving at 6 Hz and 0.3 mm; axial force logged at 2 kHz.
4. **Resonance and tracking.** Open-loop FRF; closed-loop tracking at 1–50 Hz.
5. **Cancellation** by the EXP-B09 method on the actuated axis: NEUTRAL, ORACLE and KF-ASR; 6 and 10 Hz; 0.1 and 0.3 mm peak; θ 50°; 10 seeds per primary cell; paired blocks; ink scanned blind.
6. **Command jitter** (`docs/sensor_fusion_ai.md` §3.3). Repeat the ORACLE cell at 8 Hz and 0.3 mm with 5 µm RMS of 200–900 Hz noise added to the stage command, and log the rail power (AC-Q06-05). In simulation this took the tremor-band oracle from 0.82 to 0.96 and the rail power from 138 to 606 mW, which is why every estimator ends in an output low-pass.

### Measurands and uncertainty

| Measurand | Target U (k = 2) |
|---|---|
| Nib stroke under load | ≤ 3 µm |
| Axial nib force | ≤ 5 mN |
| Cross and parasitic stiffness | ≤ 5 % |
| First resonance | ≤ 1 % |
| M-ratio (ORACLE, KF-ASR) | 95 % CI over seeds, as EXP-B09 |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q06-01 | REQ-PNC-003 | Load line of the loaded 1-axis rig (PL128.10, D1 refill, skid nose): \|measured - predicted\| / predicted nib stroke under transverse load (static probe 0-0.3 N, lifted; contact load at θ 35-75° on 3 papers), predicted from the EXP-Q04 plate data and the as-built lever and leaf | ≤ 15 % | hypothesis | docs/pencil_mechanisms.md s4.1 load line q = (F_b - \|F\|)/(k_b + k_par) (CALCULATION; PL128.10 ±349 µm under the 0.170 N design load, results/pencil/mechanisms.json b_candidates); ±15 % engineering judgement, as the physics.md stiffness band | DEC-019 (the Q-stage sizing rests on the load line); go-ahead for EXP-Q07 |
| AC-Q06-02 | REQ-PNC-002 | Axial nib force at the refill during writing strokes behind the skid nose, user force 0.5, 1 and 2 N, θ 35-75°, stage moving: range about the spring setting F_c | within F_c ± 0.03 N | hypothesis | REQ-PNC-002 (writing force carried by the skid, nib force set by the spring); band ±0.031 N with PTFE-lined bores (mu_b 0.08), ±0.12 N if the Ti collar bore is left bare (docs/pencil_mechanisms.md s2.1; config/pencil.yaml nib.bushing_mu, assumption; CALCULATION) | collar liner (DEC-019 CAD); modulation case of EXP-Q02 |
| AC-Q06-03 | — | ORACLE residual ratio (M-ratio, EXP-B09 method) of the loaded 1-axis rig along its actuated axis, 6 and 10 Hz, 0.1 and 0.3 mm peak, θ 50°, user force 1 N; mean over 10 seeds per cell | ≤ 0.5 | hypothesis | ≥ 6 dB, as AC-B09-02. Prediction for the Q stage 0.21 / 0.25 at 6 / 10 Hz and 0.1 mm, 0.24 / 0.40 at 0.3 mm (P1, results/pencil/sim_metrics.json; SIMULATION); to be regenerated for the PL128.10 rig (s0.2) | DEC-019 (go-ahead for the two-axis demonstrator EXP-Q07) |
| AC-Q06-05 | — | Increase of the ORACLE residual ratio when 5 µm RMS of 200-900 Hz noise is added to the stage command (8 Hz, 0.3 mm, θ 50°) | ≥ 0.05 | hypothesis | simulation: tremor-band oracle 0.82 -> 0.96 and rail power 138 -> 606 mW (results/fusion/sensors.json jitter_check; SIMULATION); a pass confirms the output low-pass rule of every estimator | estimator output filtering (DEC-025) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-Q06).
<!-- AC-TABLE:EXP-Q06:END -->

### Decision rule and what changes

| Result | Consequence |
|---|---|
| Load line within ±15 % (AC-Q06-01) | The Q-stage sizing stands; build EXP-Q07. |
| Load line off by more than 15 % | Re-derive the stroke budget from the measured blocking force and stiffnesses before any custom plates are ordered for EXP-Q07. |
| Nib force outside F_c ± 0.03 N, or rising with the user force (AC-Q06-02) | The skid does not carry the force as designed, or the bushings bind. Fix the liner or the nose geometry; REQ-PNC-002 is at risk. |
| ORACLE ratio above 0.5 (AC-Q06-03) | The loaded piezo stage cannot cancel even with perfect knowledge; DEC-019 is re-opened before Rev P1. |

---

## 32. EXP-Q07: Two-axis Q-stage demonstrator in a 7.9 mm bore

### Purpose and what it gates

The full Q stage (four custom plates in push-pull pairs, leaves, collar, gimbal and snubbers) is assembled in a 7.9 mm bore as in CAD P0.1.2 and characterised with the EXP-B05 methods. It verifies the three clauses of REQ-PNC-003 and gates the first pencil build (Rev P1).

- **Requirement:** REQ-PNC-003: ≥ ±0.30 mm under the design load over θ 35–75°, zero static hold power, first resonance ≥ 150 Hz.
- **Decisions:** DEC-019 (revisit trigger "EXP-Q06/Q07 loaded stages"); the Rev P1 build.
- **Predictions (CALCULATION, `results/pencil/mechanisms.json`):** ±277 µm under the design load at 50°, ±162 µm at −20 % part tolerance, ±48 µm at 35°; 192 Hz lumped, 195 Hz FE; hold power ≈ 0 apart from leakage. **The stroke clause of REQ-PNC-003 is therefore expected to fail.**

### Set-up and equipment

- The Q-stage assembly in a stainless bore tube of 7.9 mm, with the nose Hall sensor; drivers from EXP-Q05; the 10 kHz servo.
- Rig R5 for free-space stroke, FRF and stops; R2 with the skid nose for in-contact tests; an electrometer for leakage.

### Procedure

1. **Fit.** Sweep to the ±0.40 mm stops in 8 directions and check for contact of plates, leaves or collar with the bore (electrical continuity to the tube; video).
2. **FRF** per axis and across axes by the EXP-B05 procedure (pilot, amplitude ladder, IV estimator, three levels; §6), then the model-form diagnostics of AC-B05-15 adapted to the piezo stage.
3. **Stroke under load.** In contact at θ ∈ {35, 45, 50, 60, 75}° with the selected F_c, worst stroke direction, 8 directions; lifted with a static probe load of 0.170 N per axis.
4. **Static hold.** The design load held for 60 s on both axes, with the leakage current and the driver output power logged.
5. **Stops and cross-coupling**; then EXP-Q04 items 1, 3 and 6 on the assembly.

### Measurands and uncertainty

| Measurand | Target U (k = 2) |
|---|---|
| Correction reachable under load, per direction and θ | ≤ 3 µm |
| First resonance; cross-axis coupling | ≤ 1 %; ≤ 1 dB |
| Hold power at the plates | ≤ 0.1 mW |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q07-01 | REQ-PNC-003 | Two-axis nib correction reachable under the contact load at each θ (F_c cot(θ - atan mu), worst stroke direction; 0.170 N per axis at F_c 0.15 N, θ 50°, mu 0.15), Q stage in the 7.9 mm bore: minimum over 8 directions and over θ 35, 45, 50, 60 and 75° | ≥ ±0.30 mm | requirement | REQ-PNC-003; prediction ±277 µm at θ 50°, ±162 µm at -20 % part tolerance, ±48 µm at 35° (results/pencil/mechanisms.json c_stage_check_Q26; CALCULATION) -> expected FAIL; proposed P0.2 (DEC-030): worst case ±212 µm (-20 % parts, 35°, mu 0.15), ±477 µm nominal at 50° with the servo capped at ±300 µm (results/opt/hardware.json; CALCULATION) -> still expected FAIL in the worst corner (±0.30 mm needs F_c ≤ 0.10 N) | Rev P1 build (DEC-019); REQ-PNC-003 revision (tilt range, F_c); DEC-030 |
| AC-Q07-02 | REQ-PNC-003 | First transverse resonance of the assembled Q stage, each axis, free (pen lifted), from the open-loop FRF | ≥ 150 Hz | requirement | REQ-PNC-003; prediction 192 Hz lumped, 195 Hz FE (results/pencil/mechanisms.json resonance; CALCULATION) | servo design (10 kHz loop); Rev P1 build |
| AC-Q07-03 | REQ-PNC-003 | Static hold power: electrical power into the plates (leakage current x voltage, electrometer) while holding the 0.170 N design load on both axes for 60 s, excluding driver quiescent power | ≤ 1 mW | derived | derived from REQ-PNC-003 ('zero static hold power'); 1 mW is the engineering-judgement quantification, under 1 % of the 97 mW assist budget (results/pencil/sim_metrics.json) and against 2.4 W for the best voice coil that fits (docs/pencil_mechanisms.md s3; SIMULATION) | DEC-019 (piezo vs voice coil) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-Q07).
<!-- AC-TABLE:EXP-Q07:END -->

### Decision rule and what changes

AC-Q07-01 and AC-Q07-02 are requirement verdicts, with guarded acceptance where TUR < 4 (§0.5).

| Result | Consequence |
|---|---|
| Stroke below ±0.30 mm (expected: ±277 µm at 50°, ±48 µm at 35°) | REQ-PNC-003 is restated to the reachable stroke and tilt range, or the stage is redesigned before Rev P1 (compare COR-26 for the Rev A envelope). Recorded in DEC-019. |
| Resonance below 150 Hz | Redo the 10 kHz servo design and the drop analysis with the measured modes. |
| All pass | The Rev P1 build proceeds with the measured stroke budget. |

---

## 33. EXP-Q08: Touchdown and lift tails; tilt-adaptive front stop

### Purpose and what it gates

In P1 the refill's front stop covers the whole tilt range, so at 50° the unloaded refill stands 1.34 mm proud of its working point. The ball lands first and slides while the refill retracts, and does the same at lift. The tail ink is 13 % of all ink and lowers unguided recognition from 0.93 to 0.79 (`docs/pencil_mechanisms.md` §12; `docs/ai_guidance.md` §4). A tilt-adaptive stop (DEC-022) sets the stop from the IMU tilt with a margin. Too small a margin starves the axial slide q·cot θ that the stage needs.

- **Requirement:** REQ-PNC-006: extra ink at touchdown and lift, beyond what a rigid pen draws on the same writing, ≤ 0.1 mm per stroke; no missing ink.
- **Decisions:** DEC-022 (revisit trigger EXP-Q08): whether to build the adaptive stop, and at what margin. DEC-026: whether the touchdown and lift feed-forward goes into the firmware (bounce counts decide). DEC-027: whether the retuned servo replaces P0.1.2's.
- **Predictions (SIMULATION, P1 with the tilt held constant, θ 50°, straight-up lifts, 4 seeds with 18 strokes in all; means per stroke against a rigid pen on the same writing, 0.2 mm tolerance; `results/pencil/touchdown_tails.json`):**

  | Front stop | Extra ink per stroke | Missing ink per stroke | ORACLE ratio, 6 Hz 0.3 mm |
  |---|---|---|---|
  | Tilt-range (P0.1.2) | 1.15 mm | 0.011 mm | 0.24 |
  | Adaptive, 0.30 mm margin | 0.33 mm | 0.013 mm | 0.30 |
  | Adaptive, 0.20 mm margin | 0.28 mm | 0.013 mm | 0.45 |
  | Adaptive, 0.10 mm margin | 0.31 mm | 0.090 mm | 0.69 |

- **Predictions with the touchdown feed-forward (SIMULATION, P1, test seeds 200–203, tilt constant; `docs/opt_touchdown.md` §4, `results/opt/touchdown.json`).** The table above counts all extra ink, including the skid's in-stroke distortion. The criteria now separate tail ink (within 30 ms of a touchdown or lift) from in-stroke ink.

  | Configuration | Tail ink per stroke, 35° / 50° / 75° | In-stroke extra ink, 50° | Missing ink, 50° | ORACLE ratio, 6 Hz 0.3 mm, 35° / 50° |
  |---|---|---|---|---|
  | Tilt-range stop (P0.1.2) | 0.35 / 0.81 / 0.42 mm | 0.16 mm | 0.009 mm | 0.27 / 0.22 |
  | Adaptive stop 0.30 mm alone | 0.14 / 0.11 / 0.00 mm | 0.17 mm | 0.010 mm | 0.42 / 0.27 |
  | Adaptive 0.31 mm + feed-forward (DEC-026) | 0.005 / 0.008 / 0.000 mm | 0.17 mm | 0.009 mm | 0.45 / 0.25 |
  | + retuned servo (DEC-027) | 0.012 / 0.009 / 0.000 mm | 0.09 mm | 0.010 mm | 0.35 / 0.25 |

  Slow pen-downs with the feed-forward (held-out training seeds): peak contact-point deviation 65 / 70 µm at 1 / 10 mm/s (236 / 239 µm without pre-positioning). Contact events (training seeds 300–303): 16 touchdowns at 50° and 21 at 35° with the feed-forward, against 18 for the rigid pen and 12 / 10 for the adaptive stop alone; the extra ones are re-contacts within 30 ms after lift-off.

**Rig (study M).** Runs on R13 as part of EXP-T11 (§47; `docs/measurement_rig.md` §6.3).

### Set-up and equipment

- The EXP-Q06 rig (R2, R3).
- Front stops:
  - (a) the fixed tilt-range stop of P0.1.2 (ball-centre protrusion 2.06 mm);
  - (b) an adaptive stop set from the pen's IMU tilt by a SQUIGGLE-class trim motor (AMF-15), at margins of 0.2, 0.3 and 0.4 mm. An LDV on the refill measures the stop position.
  - (c) the rigid reference: the same refill in a rigid holder at the same tilt, on the same robot paths.
- Firmware: the touchdown feed-forward of DEC-026 (reference implementation: the td_* path of `sim/pencil/core.py`, parameters in `results/opt/touchdown.json` `recommended`), switchable on and off; the servo at the P0.1.2 settings and, once the stage is identified (EXP-Q04/Q07), at settings retuned by the DEC-027 method.
- Extra sensing: an LDV on the refill collar; the pen's axial sensor and stage Hall sensors logged at 20 kHz; a conductive trace or contact microphone for contact events.
- The robot writes strokes of 3–20 mm with pen-downs and lifts at θ 35, 50 and 75°, and also makes slow pen-downs at 1, 10 and 50 mm/s without writing. Lifts go straight up (as P1's model hand) and along the pen axis, because the tails depend on the lift direction (`docs/ai_guidance.md` §9).

### Procedure

0. **Latencies first.** During 50 touchdowns, log the axial sensor, the stage Hall sensors and the collar LDV at 20 kHz. Measure the axial sensor's delay, the time from contact to the refill leaving its stop, and the stage's push-back at contact without and with the switched load bias. Enter them in P1 (`PencilConfig(overrides={"ax_decim": n, "ax_delay": n})`, stage stiffness and damping in `config/pencil.yaml`), re-run `python3 -m opt.touchdown.run_study` and freeze the predictions before step 1.
1. For each stop and margin (adaptive stop at 0.31 and 0.40 mm, each with the feed-forward on and off), and for the rigid reference: ≥ 200 strokes per θ and lift type in NEUTRAL; then ORACLE with 6 Hz, 0.3 mm disturbance (10 seeds, as EXP-Q06).
2. A slow tilt sweep (35 → 75° over 10 s) while writing, to check that the trim motor follows the tilt.
2a. Slow pen-downs at 1, 10 and 50 mm/s, 20 per speed and condition, feed-forward on and off.
3. Scan every sheet (R3). Extra and missing ink are measured blind against the rigid reference's ink on the same path (0.2 mm tolerance), per stroke, and split into tail ink (within 30 ms of a touchdown or lift, each reported separately) and in-stroke ink.

### Measurands and uncertainty

| Measurand | Definition | Target U (k = 2) |
|---|---|---|
| Extra ink per stroke | Pencil ink farther than 0.2 mm from the rigid reference's ink, touchdown and lift together (also reported per event) | ≤ 10 µm |
| Missing-ink strokes | Strokes with a gap longer than 0.3 mm in the reference ink that has no pencil ink within 0.2 mm / all strokes | Binomial CI |
| ORACLE ratio | As EXP-Q06 | 95 % CI over seeds |
| Stop tracking error | Stop position minus the target set from the tilt, during the sweep | ≤ 5 µm |
| Tail ink per stroke | Extra ink within 30 ms of a touchdown or lift, per event and per stroke | ≤ 10 µm |
| In-stroke extra ink per stroke | Extra ink more than 30 ms from any transition | ≤ 10 µm |
| Peak contact-point deviation | Slow pen-downs: largest distance of the ball from its working position, LDV or camera | ≤ 5 µm |
| Contact events per pen-down | Transitions of the continuity trace (gaps from 0.2 ms), per robot pen-down | Count |
| Stage travel at touchdown | Hall-measured stage position in the 30 ms after contact | ≤ 5 µm |

### Acceptance criteria

<!-- AC-TABLE:EXP-Q08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-Q08-01 | REQ-PNC-006 | Tail ink per stroke: pencil ink farther than 0.2 mm from the ink of a rigid reference pen on the same robot path (same refill in a rigid holder at the same tilt) and within 30 ms of a touchdown or lift, per intended stroke (R3 scans), tilt-adaptive front stop at its selected margin with the touchdown feed-forward (DEC-026) and, as the comparator, without it; θ 35/50/75°, straight-up and along-axis lifts; 95th percentile over ≥ 200 strokes per condition. In-stroke extra ink (more than 30 ms from any transition) is reported separately (AC-Q08-04) | ≤ 0.1 mm | requirement | REQ-PNC-006 (touchdown and lift); prediction (mean per stroke, test seeds 200-203, straight-up lifts, θ 35/50/75°): 0.005 / 0.008 / 0.000 mm with the adaptive stop at 0.31 mm and the feed-forward, 0.14 / 0.11 / 0.00 mm with the adaptive stop alone, 0.35 / 0.81 / 0.42 mm with the tilt-range stop (results/opt/touchdown.json validation_test_seeds; SIMULATION, tilt constant) -> expected PASS with the feed-forward, marginal FAIL without; 95th percentile not predicted. Split from the earlier all-extra-ink metric (1.15 / 0.33 / 0.23 mm per stroke, results/pencil/touchdown_tails.json), which is dominated by the skid's in-stroke distortion | DEC-022 (adaptive stop and margin); DEC-026 (touchdown feed-forward); REQ-PNC-006 |
| AC-Q08-02 | — | Increase of the ORACLE residual ratio (6 Hz, 0.3 mm peak, θ 50°, EXP-Q06 rig) with the adaptive stop at the selected margin over the same rig with the tilt-range stop | ≤ 0.1 | hypothesis | DEC-022 trade-off: P1 oracle ratio 0.24 (tilt-range stop), 0.30 / 0.45 / 0.69 at 0.30 / 0.20 / 0.10 mm margin, because a small margin starves the axial slide the stage needs (results/pencil/touchdown_tails.json; SIMULATION); with the feed-forward (DEC-026) at 0.31 mm: 0.250 against 0.218 for the tilt-range stop on the test seeds (increase 0.03; results/opt/touchdown.json; SIMULATION); 0.1 engineering judgement | DEC-022 margin choice |
| AC-Q08-03 | REQ-PNC-006 | Missing ink with the adaptive stop: intended strokes (robot pen-downs) with a gap longer than 0.3 mm in the rigid reference's ink that has no pencil ink within 0.2 mm (lost starts, early lifts, bounces), all conditions | ≤ 1 % | hypothesis | REQ-PNC-006 (no missing ink), made measurable: missing ink averages 0.013 mm per stroke at 0.30 mm margin and 0.09 mm at 0.10 mm; P1 registers 0.875 of the rigid pen's pen-downs at 0.30 mm because short lifts merge (results/pencil/touchdown_tails.json; SIMULATION, 18 strokes); with the feed-forward 0.009 mm per stroke at 50°, none of it within 30 ms of a transition, 0.05 mm at 75° (in-stroke, in every configuration) (results/opt/touchdown.json; SIMULATION); 0.3 mm and 1 % engineering judgement | DEC-022; firmware touchdown profile |
| AC-Q08-04 | — | In-stroke extra ink per stroke (pencil ink farther than 0.2 mm from the rigid reference's ink and more than 30 ms from any transition), adaptive stop with the feed-forward, θ 50°, tremor-free: servo retuned on the identified stage by the DEC-027 method / P0.1.2 servo, same strokes | ≤ 0.8 | hypothesis | DEC-027; prediction 0.087 / 0.171 mm per stroke = 0.51 (results/opt/touchdown.json per_θ 50 adaptive_ff_tuned_servo vs adaptive_ff; SIMULATION). Fragile: the in-stroke ink counts excursions beyond 0.2 mm of a 0.14 mm RMS distortion, and the halving comes from 135.9 -> 133.4 µm RMS; 0.8 engineering judgement | DEC-027 (servo retune) |
| AC-Q08-05 | — | Peak contact-point deviation from its working position during slow robot pen-downs at 1 and 10 mm/s (LDV or camera on the ball holder), adaptive stop at the selected margin with the feed-forward, θ 50°, 20 pen-downs per speed; maximum of the per-speed means | ≤ 0.1 mm | hypothesis | DEC-026; prediction 65 / 70 µm at 1 / 10 mm/s with the recommended law, 236 / 239 µm without pre-positioning, 65 / 173 µm with a ramped load bias (held-out training seeds 310-319; results/opt/touchdown.json search.ablations; SIMULATION); 0.1 mm = half the 0.2 mm ink tolerance, engineering judgement | DEC-026 (pre-positioning, switched load bias) |
| AC-Q08-06 | — | Contact transitions per robot pen-down (electrical continuity through a conductive trace, or acoustic; a gap counts from 0.2 ms), adaptive stop with the feed-forward, θ 35/50/75°: ratio to the rigid reference on the same paths | ≤ 1.0 | hypothesis | DEC-026 bounce risk (DEC-011 family); prediction on training seeds 300-303 (SIMULATION; results/opt/touchdown.json mechanism_checks.contact_events_training): touchdowns 16 at 50° and 21 at 35° with the feed-forward against 18 for the rigid pen and 12 / 10 for the adaptive stop alone; the extra events are re-contacts within 30 ms after lift-off (gaps 0.5-2 ms, separation 1-16 µm) -> PASS at 50°, FAIL at 35°; engineering judgement | DEC-026 (bias release at lift); DEC-011 |
| AC-Q08-07 | — | ORACLE residual ratio (6 Hz, 0.3 mm peak, EXP-Q06 rig) with the feed-forward minus the same adaptive stop without it, θ 35/50/75°, same servo | ≤ 0.02 | hypothesis | DEC-026 cost to the correction; prediction (test seeds, SIMULATION; results/opt/touchdown.json): 50° 0.250 - 0.257 = -0.007, 35° 0.446 - 0.416 = +0.03 (FAIL; the tuned servo of DEC-027 brings it to 0.354), 75° 0.00; 0.02 engineering judgement | DEC-026; DEC-027 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-Q08).
<!-- AC-TABLE:EXP-Q08:END -->

### Decision rule and what changes

| Result | Consequence |
|---|---|
| Tails ≤ 0.1 mm at a margin whose ratio increase is ≤ 0.1 | Build the adaptive stop at that margin (DEC-022 accepted). |
| Tails above 0.1 mm at every margin that keeps the ratio without the feed-forward (expected) and ≤ 0.1 mm with it | Adopt DEC-026 if AC-Q08-05…07 also pass. |
| Feed-forward adds contact events (AC-Q08-06 fails) | Add a bias ramp of a few ms at lift (untested in SIM), re-run the P1 study with the measured latencies, and repeat. If the events stay, keep the adaptive stop alone and restate REQ-PNC-006 at the measured tails. |
| Tails above 0.1 mm with the feed-forward | Check the step-0 latencies against P1's assumptions; fit the 10 kHz slide sensor option (AMF-70…72, `docs/opt_touchdown.md` §7) if the axial sensor is slower than assumed. |
| The retuned servo lowers in-stroke ink (AC-Q08-04) without failing AC-Q08-07 | Adopt the DEC-027 settings for the identified stage. |
| Stroke starts lost (AC-Q08-03) | Raise the margin or change the touchdown detection; measure the effect on recognition in EXP-C01. |
| Tails depend strongly on the lift direction | P1's straight-up lift over- or understates the tails. People's lift kinematics are taken from the EXP-H01 recordings. |

---

## 34. Human-participant protocols

The following are specified in [`human_study_plan.md`](human_study_plan.md), with their acceptance criteria in `acceptance_criteria.csv`:

| ID | Title | Separation of claims |
|---|---|---|
| EXP-H01 | Tremor-at-nib census with an instrumented passive pen (ET, PD, older adults, healthy controls) | Measurement only; no assistance |
| EXP-H02 | Form factor and writing feel with the unpowered pen | Device burden; no assistance |
| EXP-H03 | Skid feel and smear, blinded (configuration D, non-active) | Device burden; passive effect |
| EXP-H04 | Training and lasting improvement: randomised practice with fading guidance or error amplification vs control; delayed retention and transfer, unassisted | **Lasting improvement** |
| EXP-H05 | Perception thresholds for ink distortion, blinded pairs | Sets thresholds for REQ-CTRL-005 and REQ-MECH-005 |
| EXP-H06 | Immediate-assistance efficacy: device on vs neutral vs off, randomised crossover, blinded assessor | **Immediate assistance** |
| EXP-A02 | Guidance acceptance with people (pencil concept): template distance from unguided writing (passive), then known- and AI-template guidance | Measurement (passive part); **immediate assistance** (guided part) |
| EXP-I02 | Rotational share of writing tremor (inside EXP-H01 sessions) | Measurement only |
| EXP-I03 | Passive nose and grip options on writers (extends EXP-H03) | Device burden; passive effect |
| EXP-W01…W05, G07 | Rev H outcome studies and the guidance board with people (§15) | **Immediate assistance**, **lasting improvement** and device burden, per study |
| EXP-D08 | Guided writing with the heel drive: tracing, loops, reversed letters, resist; unassisted retention after 1 day | **Immediate assistance**; retention block **lasting improvement** |
| EXP-D09 | Tremor: the heel's constraint and damping | **Immediate assistance** |
| EXP-D11 | Lead-through and autowrite with relaxed hands | **Immediate assistance** (the device writes) |
| EXP-K03 | End-cap crossover: nose alone, nose + weight, nose + active end-cap | **Immediate assistance**; device burden |
| EXP-K05 | Cue perception by people with tremor | Measurement only |
| EXP-N09 | Autowrite with people | **Immediate assistance** (the device writes) |
| EXP-N10 | Delayed ink acceptance (only before any revival of delayed ink; shares sessions with EXP-L03) | Device burden |
| EXP-L03 | Ink lag: noticed, and does it cause writing errors? (only before any revival of delayed ink; shares sessions with EXP-N10) | Device burden |
| EXP-L06 | Text prediction in the app on users' own notes | **Immediate assistance** (app) |
| EXP-L07 | Handwriting synthesis in the user's style, judged by people | Measurement only |
| EXP-L08 | Guidance that fades across sessions against fixed guidance; unassisted retention | **Lasting improvement** |
| EXP-J08 | Can writers see the ink? Printed Rev H and Rev J fronts on dummy pens (superseded for Rev J.1 by EXP-J15) | Device burden |
| EXP-J09 | Mass and balance: 84 g and 113 g dummies of the Rev J.1 pen (with EXP-K03) | Device burden |
| EXP-J15 | The clear window: can writers see the ink through the Rev J.1 front? (its wear test on coupons is in §46) | Device burden |
| EXP-J18 | The heel wheel on writing: distortion, and adaptation over 10 minutes (DEC-048) | Device burden |
| EXP-R01 | Patients' own writing and tremor at the pen tip, with ink and the pen's IMU (the recording part of EXP-H01, in its sessions) | Measurement only |
| EXP-R03 | A blinded panel of readers against the AI reader's "words you can read" | Measurement only (the reader's validity) |
| EXP-S10 | Letters read while people write on paper with the pen (inside EXP-H01/R01 sessions) | Measurement only |
| EXP-S11 | An English corpus of dyslexic misspellings in context, with consent for release | Measurement only (data) |
| EXP-S12 | A tick while writing for people with dyslexia (shares sessions with EXP-S18) | **Immediate assistance** |
| EXP-S13 | Detection of a tick in a pen while writing | Measurement only |
| EXP-S14 | Personal text prediction on users' own notes over 4 weeks (continues EXP-L06) | **Immediate assistance** (app) |
| EXP-S15 | Shape assist with real writers (only after a redesign shows a simulated gain) | **Immediate assistance** |
| EXP-S17 | Word recognition on the pen's own recordings, writer- and session-disjoint | Measurement only |
| EXP-S18 | Suggestions at pauses against cues while writing (shares sessions with EXP-S12) | **Immediate assistance** |
| EXP-W10 | Tremor at the ink while writing, per population; does anyone exceed the nose's reach? (with EXP-H01/R01) | Measurement only |
| EXP-W12 | Holding and writing with the collar mock-up | Device burden |
| EXP-W16 | The cost of writing only when in reach | **Immediate assistance**; device burden |
| EXP-K24 | Grip height with Rev K's front: do writers' fingers touch the paper? (study K, DEC-062) | Device burden |
| EXP-E20 | People read study F's E13 inks: the tremor left at the tip for readable words (inside EXP-R03's panel; DEC-067) | Measurement only (the target's validity) |
| EXP-U01…U05 | Customer discovery (study U; DEC-090…094): a screening survey; interviews with people with ET or PD, with clinicians, and with parents or teachers; honest waitlist pages | None (market evidence); no benefit claim |
| EXP-U06 | The no-device pilot: an ordinary pen, a weighted pen, typing with accessibility settings and dictation on six everyday tasks | None (feasibility) |
| EXP-U07 | The full comparison: the device on, locked with matched mass and unpowered, against the ordinary and weighted pens, typing and dictation (extends EXP-H06's conditions; DEC-092) | **Immediate assistance** (task level) |
| EXP-U08 | A measuring pen: test-retest reliability, agreement with clinical ratings and assessment time | Measurement only |
| EXP-U09 | A practice tool's usability and adherence at home or school over 4 weeks | None (feasibility); no lasting-improvement claim |

EXP-B06 (grip impedance, §7) and EXP-I01 (grip compliance split, §35) also involve participants and are covered by the same ethics approval. So do EXP-K04 (6 healthy writers) and EXP-K08 (§42), EXP-V03 (inside EXP-H01 sessions), EXP-V04 and EXP-V07 (§44), and study B's EXP-B30 (10 writers, motion capture; §51). EXP-L01, L02 and L04 (§45) re-use EXP-H01 recordings under the consents of `human_study_plan.md` §3.3, and so do EXP-R02 and R05 (§48). EXP-S20 (§49) re-uses EXP-S18's data, and EXP-W15 (§50) the EXP-H01/R01 and EXP-W10 recordings, under the same consents.

Study H's five-bar experiments (EXP-BB06, BB07; §55) have no participants: DEC-099 keeps the five-bar on the bench, with a passive dummy pen and spring hand simulants, until a safety gate like G-S is written for it.

---

## 35. EXP-I01: Grip compliance split (translation vs tilt) of a pen grasp

### Purpose and what it gates

EXP-B06 measures the grip impedance from one input point, the handle tail. The inertial study (`docs/inertial_stabilisation.md` §3.2) showed that the unmeasured split of the grip's compliance between **translation** and **tilt** decides whether any force or torque applied in the cap can reach the nib:

- at r_rot ≈ 0.3 a force at the cap does not move the nib at all;
- a torque device moves the nib 4–38 µm per mN·m across the plausible splits (CALC).

This experiment adds a second input point (the nib) and a hand-resting condition to EXP-B06. It identifies the 2 × 2 grip stiffness per plane, the share r_rot of the nib's compliance that comes from tilt, the web's share rho_w of the translational stiffness, and the elastic centre z_c.

- **Decision:** DEC-024 (revisit trigger "EXP-I01 measures r_rot ≥ 0.6 …").
- **Model:** the two-zone grip of the hand-pen model H1 (`sim/handpen/grip.py`); nominal r_rot 0.5, rho_w 0.3 (ASSUMPTION).
- **Runs inside EXP-B06 sessions:** same participants, consent and ethics approval, rig R6 plus a second stinger. It adds about 45 min.

### Hypotheses and predictions

- **H-I01-1.** The tip-referred in-plane stiffness lies in 230–1040 N/m at 1–3 N grip force (HAP-26 range; AC-I01-01).
- **H-I01-2.** r_rot < 0.6 in most participants (AC-I01-02). At the nominal split H1 predicts that the best cap device leaves 0.85–0.97 of the ink error; at r_rot 0.7 it reaches 0.79 at 12 Hz (SIM, `results/pencil/inertial.json` split sensitivity).
- **H-I01-3.** Resting the ulnar side of the hand on the paper raises the grip-referred in-plane stiffness by more than 2× (AC-I01-03). HAP-26 measured the arm unsupported and without paper; H1 cannot represent a hand on the paper.

### Equipment

- Rig R6 (§0.9).
- Dummy pen: Ø8.9 × 166 mm, 13–20 g, rigid (first bending mode > 500 Hz), with a thin-film grip-force sensor at the finger zone.
- Two stingers from a 2-axis voice-coil shaker (0.5 N, 0.5–40 Hz), attachable at the nib (z = 0) or the cap (z = 150 mm).
- Six-axis force sensor at the stinger (Nano17 class).
- Two optical markers (nib and cap) tracked at ≥ 1 kHz with ≤ 5 µm noise, or two laser triangulation sensors.
- Paper on a low-friction film for the "nib on paper" condition.

### Procedure (per participant, about 45 min after EXP-B06)

1. Tilt 50° ± 5°, checked from the markers.
2. Grip-force targets 1, 2 and 3 N, shown from the grip-force channel.
3. For each plane (lateral, tilt plane) and each input point (nib, cap): 20 s of band-limited random force, 0.6–30 Hz, ≤ 0.3 N rms.
4. Conditions:
   - arm unsupported, forearm supported, or ulnar side of the hand resting on the paper;
   - nib in air or on paper.

   If time is short, run the three "nib on paper" conditions first.
5. Randomised order; 60 s rest between trials.

### Data format

HDF5 per trial, as EXP-B06: force (6), marker positions (2 × 3), grip force and condition tags at 2 kHz.

### Analysis

1. H1 estimate of the 2 × 2 receptance matrix per plane from the two input points (coherence > 0.8 per bin).
2. Fit `sim/handpen/grip.py` (k_f, k_w, κ_f with the hand mass and arm) per participant and condition. Confidence intervals by bootstrap over trials.
3. Report r_rot, rho_w and z_c (10/50/90 % over participants).
4. Re-run `python3 -m sim.handpen.run_study` with the fitted distribution in place of the six assumed splits.

### Measurands and uncertainty

| Measurand | Definition | Target U (k = 2) |
|---|---|---|
| Tip-referred in-plane stiffness | Driving-point stiffness at the nib, 1–10 Hz fit | ≤ 10 % |
| r_rot | Share of the nib's compliance due to tilt of the pen in the grip | ≤ 0.05 (absolute) |
| z_c | Elastic centre of the grip along the pen axis | ≤ 5 mm |

### Acceptance criteria

<!-- AC-TABLE:EXP-I01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I01-01 | — | Tip-referred in-plane grip stiffness (nib input, 1-10 Hz fit, nib on paper, forearm supported), median over participants at 1-3 N grip force | within 230-1040 N/m | hypothesis | HAP-26 range (k1 sweep 230-1040 N/m; LITERATURE); the calibration target of sim/handpen/grip.py | hand model ranges (with EXP-B06); H1 calibration |
| AC-I01-02 | — | Share of the nib's in-plane compliance due to tilt of the pen in the grip (r_rot, from the 2 x 2 receptance with nib and cap inputs), median over participants | < 0.6 | hypothesis | DEC-024 revisit threshold; H1 assumes r_rot 0.5 (ASSUMPTION); at r_rot 0.7 the best cap device reaches 0.79 at 12 Hz (results/pencil/inertial.json split sensitivity; SIMULATION) | DEC-024 (cap devices stay closed if met) |
| AC-I01-03 | — | Grip-referred in-plane stiffness with the ulnar side of the hand resting on the paper, relative to the arm unsupported (same participant, nib input) | > 2 | hypothesis | hypothesis of docs/inertial_stabilisation.md EXP-I01 H3 (engineering judgement); HAP-26 measured without paper or hand support | H1 hand-on-paper extension; EXP-I03 hand-resting arm |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-I01).
<!-- AC-TABLE:EXP-I01:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| r_rot < 0.6 for most participants | Close the cap-device line; DEC-024 stands. |
| r_rot ≥ 0.6 and the H1 re-run predicts ≥ 25 % less stage time at the travel limit at 10–12 Hz | Run EXP-I04, knowing any helper breaks the mass and power budgets. |
| Hand resting raises the stiffness > 2× | Add a hand-on-paper contact to H1 and re-run the passive options; the hand-resting arm of EXP-I03 becomes its primary comparison. |
| Tip-referred stiffness outside 230–1040 N/m | Replace the `hand.*` ranges (with EXP-B06) and re-run P1 and H1. |

### Risks and controls

- The grip adapts to the shaker: keep the forces random and small.
- Marker occlusion: two markers, redundant camera.
- The tilt changes with grip force: log it and include it as a covariate.

---

## 36. EXP-I04 (conditional): Nib stage plus an inertial helper on the loaded rig

### Purpose and what it gates

Run only if EXP-I01 finds r_rot ≥ 0.6 and the H1 re-run predicts that a helper cuts the stage's time at its travel limit by ≥ 25 % at 10–12 Hz (DEC-024). The inertial study found helpers matter only where the stage saturates: at 12 Hz and 0.3 mm the stage sits at its limit 62 % of the time, 52 % with a 5.15 g tungsten reaction mass and 45 % with two control-moment-gyroscope pairs (SIM, H1, perfect knowledge).

### Set-up

- The EXP-Q06 rig (R2, R3) with the pen body held by a hand simulant that has the EXP-I01 two-zone compliance.
- The helper module in the cap position: a CMG pair or a tungsten reaction mass on voice coils (`docs/inertial_stabilisation.md` §5.8 for sizes).

### Procedure

The EXP-B09 cancellation protocol with an injected disturbance at 8, 10 and 12 Hz and 0.3–0.5 mm, with and without the helper, 10 seeds each, ORACLE control of both.

### Measurands

- Stage time at the travel limit (definition as P1: command ≥ 95 % of the soft limit, drive saturated, or on the stop).
- ORACLE ink-error ratio.
- Helper electrical power; for a CMG, vibration at the spin frequency.

### Acceptance criteria

<!-- AC-TABLE:EXP-I04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I04-01 | — | Relative reduction of the stage's time at its travel limit with the helper (CMG pair or reaction mass) at 10-12 Hz, 0.3 mm injected disturbance, ORACLE control, hand simulant with the EXP-I01 compliance | ≥ 25 % | hypothesis | DEC-024 revisit threshold; H1 predicts 16 % (tungsten reaction mass) and 27 % (CMG pairs) at 12 Hz (62 % -> 52 % / 45 %; results/pencil/inertial.json; SIMULATION) | DEC-024 (conditional on EXP-I01) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-I04).
<!-- AC-TABLE:EXP-I04:END -->

### What changes which decision

| Result | Consequence |
|---|---|
| Reduction ≥ 25 % | Re-open DEC-024 for a larger form factor only; the pencil envelope still has no room (mass, power, cell). |
| Reduction < 25 % | Close the helper line. |

**Superseded for Rev H (2026-09-28).** The user chose a bigger grip (DEC-029) and asked for inertial control (DEC-033). The Rev H module is tested in EXP-I06 instead.

**Superseded by EXP-T16 (2026-09-29).** Study M's grip simulant R14 asks the same question for any collar or tail module: no module, the same mass locked, unpowered and active, at three grip strengths (§47; `docs/measurement_rig.md` §7.3). EXP-I06 had already superseded it for Rev H.

---

## 37. EXP-I05: Rev H active nose on the bench

### Purpose and what it gates

Rev H moves the whole nose, and so the ball, by up to ±3 mm relative to the handle (DEC-032, architecture B). A skid ring on the fixed sleeve carries the writing force.
- **Why this experiment gates everything:** it decides whether the nose is strong, fast and frugal enough, and whether the writing force stays undisturbed.
- **Predictions (CALC, SIM; `results/revH/tip_params.json`, `docs/opt_inertial.md`):**
  - Km 0.47 N/√W at the magnets;
  - ±3.0 mm usable travel at 50°, at least 2.75 mm in every direction over 35–75° (front end, DEC-034);
  - only the skid ring on the paper at every tilt and correction, the nozzle at least 0.8 mm above it, and about 13.5 mm of refill slide at 0.15 N (DEC-034, `results/revH/front_end.json`);
  - an 80 Hz servo (ASSUMPTION);
  - about 0.004 W of coil loss;
  - no writing-force change;
  - with perfect knowledge of the disturbance, ink-error ratio 0.17–0.18 at 8–12 Hz and 1–2 mm.

**Rig (study M).** The bandwidth and tremor-rig parts (procedure 3–4) run on R13 in EXP-T10, and the K_m map on R12 in EXP-T07 (§47; `docs/measurement_rig.md` §5.3, §6.3).

### Set-up

- The nose, gimbal, magnets, coils, Hall sensor and skid ring in a rigid Ø22 mm handle clamped to a 2-axis shaker (R2).
- A force plate under the paper, and R3 scans.
- A force gauge on the ball for the Km map.
- A coil-current and supply-power logger.

### Procedure

1. **Km map.** Map Km (force per √W) and the gimbal stiffness over the magnet stroke, both axes.
2. **Travel and front end.** Measure the travel with the skid ring on paper at θ 35/50/75°, in 8 directions. At each tilt and direction, with the nose at its usable travel, check from a side camera and with a feeler gauge that only the ring touches the paper, and log the ball's normal force on the force plate over the refill's full slide.
3. **Bandwidth.** Measure the closed-loop frequency response with the real Hall noise.
4. **Tremor rig.** Inject 1 mm tremor at 8, 10 and 12 Hz through the shaker while a writing robot draws letters. The nose is driven from the rig reference (ORACLE). Record power and the paper-normal force. Scan the ink.
5. **Weigh and measure** the built pen.

### Measurands

- Km (N/√W).
- Travel and cross-coupling.
- −3 dB bandwidth and phase margin.
- Power (W).
- RMS change of the normal force (N).
- Ink-error ratio against the nose held.
- Mass and envelope.

### Acceptance criteria

<!-- AC-TABLE:EXP-I05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I05-01 | REQ-RVH-003 | Nose force constant per axis at the magnets, mapped over the ±2.3 mm magnet stroke (force gauge and coil current, both axes) | ≥ 0.40 N/√W | requirement | REQ-RVH-003; prediction 0.47 N/√W (adjoint design, results/revH/tip_params.json; CALCULATION); CONTESTED by DEC-041: 0.19 N/√W by the image-method model (docs/nose_v2.md s4.2), predicted to fail; see AC-N01-03 | DEC-032 |
| AC-I05-02 | REQ-RVH-002 | Usable ball travel relative to the handle with the skid ring on paper, 8 directions, θ 35/50/75°, ≥ ±2.5 mm, with cross-coupling between axes ≤ 10 % (both) | both met | requirement | REQ-RVH-002; prediction ±3.0 mm usable at 50° and ≥ 2.75 mm in every direction over 35-75°, 3.5 mm stop (PROPOSED DESIGN, CALC, results/revH/front_end.json) | DEC-032; DEC-034 |
| AC-I05-03 | REQ-RVH-003 | Closed-loop nose bandwidth (-3 dB of tip position over reference) with the real Hall noise, and phase margin | ≥ 60 Hz and 45° | requirement | REQ-RVH-003; 80 Hz servo assumed in SIM (results/revH/tip_params.json; ASSUMPTION) | DEC-032 |
| AC-I05-04 | REQ-RVH-004 | Coil plus driver power while the nose corrects 1 mm, 10 Hz injected tremor during writing on the tremor rig | ≤ 0.1 W | requirement | REQ-RVH-004; prediction about 0.004 W coil loss, 0.081 W total with electronics (CALC on SIM forces); CONTESTED by DEC-041: about 0.027 W coil loss with the image-method force constant (docs/nose_v2.md s4.2) | DEC-032 |
| AC-I05-05 | REQ-RVH-005 | Change of the paper-normal writing force caused by the nose (force plate under the paper) while correcting 1 mm, 10 Hz tremor | ≤ 0.05 N RMS | requirement | REQ-RVH-005; architecture B: no change by construction (SIM); architecture A predicted 0.31-0.71 N RMS | DEC-032 (B over A) |
| AC-I05-06 | — | Ink-error ratio on the tremor rig (1 mm injected tremor at 8, 10, 12 Hz; ORACLE nose command from the rig reference) against the nose held | ≤ 0.3 | hypothesis | prediction 0.17-0.18 with perfect knowledge at 8-12 Hz, 1-2 mm (results/opt/inertial_opt.json; SIMULATION); 0.3 engineering judgement for rig losses | DEC-032 |
| AC-I05-07 | REQ-RVH-001 | Built Rev H prototype: grip diameter, length and mass, weighed without and with the rear inertial module | ≤ 24 mm, 175 mm, 80 g / 110 g | requirement | REQ-RVH-001; prediction Ø22 x 170 mm, 75.0 g / 103 g (CALC, results/revH/tip_params.json) | DEC-029; DEC-033 |
| AC-I05-08 | REQ-RVH-002 | Front end at θ 35/50/75° with the nose at its usable travel in 8 directions: only the skid ring touches the paper (side camera, feeler gauge), and the ball normal force stays 0.15 N ± 20 % over the refill's full slide (force plate) | both met | derived | DEC-034; prediction nozzle ≥ 0.80 mm above the paper, sleeve front ≥ 0.25 mm, refill slide 13.5 mm (results/revH/front_end.json; CALCULATION); ±20 % engineering judgement | DEC-034 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-I05).
<!-- AC-TABLE:EXP-I05:END -->

### Decision rule

| Result | Consequence |
|---|---|
| All pass | Build the Rev H prototype with this nose (DEC-032 accepted for the prototype). |
| Km or bandwidth short | Re-run the adjoint actuator design (`opt/inertial/adjoint.py`) with the measured losses; consider larger magnets. |
| Normal force disturbed | Check the refill's constant-force spring and the skid-ring contact before considering architecture A. |
| Nozzle or sleeve touches the paper, or the ink force varies by more than 20 % over the slide | Restrict full function to 40–70° (10.5 mm of slide) or rework the refill drive; re-run `python3 -m opt.inertial.front_end` with the measured parts (DEC-034). |

---

## 38. EXP-I06: Rev H rear inertial module on a hand simulant

### Purpose and what it gates

DEC-033 fits the rear-cap module (19.8 g tungsten, ±2.75 mm, 2 axes) in the first Rev H prototype at the user's request. The product keeps it only if it adds at least 10 % reduction on top of the nose at the grip split that EXP-I01 measures.
- **Predictions (SIM):** 6 / 17 / 17 % at r_rot 0.3 / 0.5 / 0.7 (15 % at 0.3 after a grip calibration), at ≤ 0.051 W.

**Rig (study M).** Runs on R14, the grip simulant on R13's stage, as part of EXP-T16 (§47; `docs/measurement_rig.md` §7.3).

### Set-up

The EXP-I05 rig with the module in the cap and a hand simulant set to the EXP-I01 two-zone compliance.

### Procedure

Inject 1 mm tremor at 10 Hz; causal control (IMU tracker, Rev H setting). Run the nose alone, then the nose with the module, 10 seeds each. Log the module's stroke, end-stop impacts (accelerometer and sound) and power.

### Acceptance criteria

<!-- AC-TABLE:EXP-I06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I06-01 | — | Further relative reduction of the ink-error ratio when the rear inertial module is on, with the nose on (causal), hand simulant with the EXP-I01 grip split, 10 Hz, 1 mm | ≥ 10 % | hypothesis | DEC-033 product rule; prediction 6 / 17 / 17 % at r_rot 0.3 / 0.5 / 0.7 (15 % at 0.3 after a grip calibration) (results/opt/inertial_opt.json; SIMULATION) | DEC-033 (keep the module in the product) |
| AC-I06-02 | REQ-RVH-004 | Module electrical power and end-stop impacts during 60 s of 10 Hz, 1 mm tremor writing | ≤ 0.051 W and 0 impacts | derived | REQ-RVH-004; prediction ≤ 0.051 W, stroke ±2.75 mm with a 5 Hz centring loop (CALC, SIM) | DEC-033 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-I06).
<!-- AC-TABLE:EXP-I06:END -->

---

## 39. EXP-I07: Rev H tracker on recorded tremor writing

### Purpose and what it gates

The mechanism can remove 76–91 % of tremor up to 2 mm; the tracker decides how much the writer gets. This is an offline replay of the EXP-E01 recordings through the Rev H tracker setting (ParEGO, `results/opt/inertial_tracker_revh.json`) and the nose model.
- **Predictions (SIM, synthetic writers):** 0.64–0.76 at 8–12 Hz, 1–2 mm, with 10–13 µm false correction; nothing at 4–6 Hz.

### Procedure

`opt/tracker/realdata.py` format for the recordings. Replay through `opt/inertial` with the Rev H nose limits. Report by tremor frequency, amplitude and writer group.

### Acceptance criteria

<!-- AC-TABLE:EXP-I07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-I07-01 | REQ-RVH-006 | Offline replay of recorded tremor writing (8-12 Hz, ≥ 1 mm at the tip) through the Rev H tracker setting and the nose model: ink-error ratio against the nose held, and false correction on tremor-free recorded writing | ≤ 0.8 and 15 µm RMS | requirement | REQ-RVH-006; prediction 0.64-0.76 with 10-13 µm on synthetic writers (results/opt/inertial_opt.json; SIMULATION) | DEC-032; DEC-028 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-I07).
<!-- AC-TABLE:EXP-I07:END -->

---

## 40. Guidance board: EXP-G01…G06

### Purpose and what it gates

The optional desk board (DEC-031) steers the pen along whole letters with a permanent magnet under 3 mm glass. It is capped at 0.4 N and always yields to the writer.
- These bench tests check the board's physics and safety before any participant uses it.
- Work with people (EXP-G07) is in `human_study_plan.md`.
- Methods and predictions: `docs/guidance_board.md` §8, `results/board/board.json`.

### EXP-G01: Force map

A D42 magnet in a Rev H sleeve dummy on a 3-axis load cell, above the D88 head on a manual XY/Z stage, with glass and paper in between. Grid ±16 mm at 0.5 mm; gaps 3.7, 5, 8 and 11 mm; tilts 35/50/75°.

<!-- AC-TABLE:EXP-G01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G01-01 | — | Lateral force on the pen magnet (Rev H sleeve dummy) against head offset, gap (3.7-11 mm) and tilt (35/50/75°), and normal pull, 3-axis load cell | within ±15 % of the prediction (lateral), ±20 % (normal pull) | hypothesis | prediction results/board/fig_force_vs_gap.csv and fig_force_cuts.csv (magpylib; CALCULATION): 1.20 N every direction at the A4 gap | DEC-031 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G01).
<!-- AC-TABLE:EXP-G01:END -->

### EXP-G02: Stage and latency

- Chirps and steps on the stage, measured with a laser displacement sensor.
- Timestamps from a Hall-ring sample to the step output (GPIO and scope).
- Replay of recorded writing trajectories.

<!-- AC-TABLE:EXP-G02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G02-01 | — | Board head position bandwidth ≥ 15 Hz, effective latency from Hall-ring sample to force ≤ 12 ms, and tracking error on replayed writing trajectories ≤ 0.2 mm RMS (all three) | all three met | hypothesis | prediction about 25 Hz and 8 ms effective (belt stiffness ASSUMPTION; docs/guidance_board.md); pass lines proposed by the board study | DEC-031 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G02).
<!-- AC-TABLE:EXP-G02:END -->

### EXP-G03: Localisation

A pen dummy on a calibrated XY stage, at 3 tilts and 4 azimuths, first with the head fixed and then with it moving.

<!-- AC-TABLE:EXP-G03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G03-01 | — | Ball position error of the Hall-ring localisation after one calibration, offsets ≤ 12 mm, 3 tilts x 4 azimuths, head fixed and moving | ≤ 0.3 mm RMS and 0.6 mm max | hypothesis | prediction about 0.18 mm noise at the ball; a dipole fit leaves up to 0.8 mm bias without the calibration table (CALC) | DEC-031 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G03).
<!-- AC-TABLE:EXP-G03:END -->

### EXP-G04: Noise and heat

A sound level meter at 0.5 m (A-weighted) during a tracing replay; thermocouples on the motors, drivers and glass after 30 min. Targets from the board study: ≤ 35 dB(A), glass ≤ 5 K above ambient, motor case ≤ 60 °C (ASSUMPTION; recorded, no criterion yet).

### EXP-G05: Hand simulant

A two-stage spring–mass–damper hand at the HAP-26 nominal and a stiff-arm setting holds a Rev H dummy pen. A second stage drives it along "intended" paths with 1.5 mm RMS errors. The supervisor must yield within 0.5 s when the simulant is stiffened.

<!-- AC-TABLE:EXP-G05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G05-01 | — | Ink-error reduction with full guidance on the hand simulant (HAP-26 nominal, relaxed setting) against no guidance, on paths with 1.5 mm RMS error | ≥ 40 % | hypothesis | prediction 1.49 -> 0.63 mm (58 %) with full guidance (results/board/board.json; SIMULATION) | DEC-031 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G05).
<!-- AC-TABLE:EXP-G05:END -->

### EXP-G06: Safety (a gate before any participant)

- A load cell under fault injection: sensor dropout, a wrong template, a stall, BLE loss.
- Stop-button timing.
- Motion on power loss.
- A 100 N lean on the glass.
- A field map with a gaussmeter.

<!-- AC-TABLE:EXP-G06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-G06-01 | REQ-RVH-007 | Board lateral force under fault injection (sensor dropout, wrong template, stall, BLE loss); stop latency; motion on power loss | ≤ 0.44 N; 50 ms; none | requirement | REQ-RVH-007 (0.4 N cap with 10 % margin); proposed by the board study | DEC-031 (safety gate before any participant) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-G06).
<!-- AC-TABLE:EXP-G06:END -->

---

## 41. Rev J heel drive: EXP-D01…D07, D10, D12, D13

### Purpose and what it gates

DEC-037 adds a paper-grounded drive at the heel. A 2 mm wheel with an O-ring tyre sits in a slot at the bottom of a larger skid ring. It is steered about the paper normal through its contact point (the cobot principle, LIT HAP-60), and a 2:1 bevel drives it. Two Faulhaber 0620 B motors turn two 0.8 mm shafts that reach a sprung heel pod (0.55 N preload). In the Rev J layout (DEC-044) the motors sit under the cell, and 80 mm shafts run in grooves of the bottom wall.
- **Modes.** Steer-only by default: the wheel cannot move the pen. The drive motor pushes only in an explicit lead-through or autowrite mode (DEC-039), and it never starts a stroke.
- **Supervisor.** Commands are capped at min(0.5 N, 0.8 × μ̂ × wheel load). A lateral release turns the wheel toward a push above the cap. The page sensor detects slip.
- **What it gates.** DEC-037 is adopted only after EXP-D01, D05, D07 and D08. EXP-D07 is the safety gate before any participant uses the drive. Requirements: REQ-DRV-001…013.
- **Predictions** come from `docs/grounded_drive.md` and `results/drive/` (model HW1-D; test writers 0–5, seeds 200–203; tyre friction drawn from 0.6–1.2 per case; CALC and SIM). The tyre friction, the tyre stiffness, the steering servo and the relaxed-writer model are ASSUMPTIONS.
- **Front end.** Study D sized the heel on the Rev H front end (contact radius 8.75 mm, sleeve Ø18.3 mm at the heel). The Rev J layout (DEC-044) fits it to the nose v2 front end: the wheel at 12.0 mm, the skid ring at 11.65 mm, the sleeve front Ø23.3 mm flush with the ring, and 24 mm where held with no margin left (AC-D04-04). A fourth gear mesh lowers the wheel force to 0.37 N continuous and 0.60 N peak (CALC).
- Work with people (EXP-D08, D09, D11) is in [`human_study_plan.md`](human_study_plan.md) §16.

### EXP-D01: Tyre–paper friction on six papers

- **Purpose and gates.** Replace the assumed traction range (0.6–1.2) with measurements, and pick the tyre compound. Gates REQ-DRV-004 and DEC-037.
- **Rig (study M).** Runs on R9 with a wheel head, on the same six papers, as a head variant of EXP-T01 (§47; `docs/measurement_rig.md` §2.8).
- **Predictions.** Design range μ 0.6–1.2 (ASSUMPTION). Polyurethane paper-feed rollers have 1.30–2.20 when new and 1.05–1.52 after 300 000 sheets (LIT AMF-111). Paper friction tests agree only within 24–27 % between laboratories (LIT AMF-113). At μ 0.6 the mean writer gets 0.30 N of traction and the weakest 10 % get 0.21 N (CALC, 0.55 N preload).
- **Set-up.** R1 tribometer (TAPPI T 549 adapted) with a 2 mm wheel, locked and rolling; a 0.01 N-class load cell; a climate box. Tyres of NBR 70, PU 80 and silicone 50 Shore A. Papers: copy 80 g/m², recycled, school ruled, coated, tracing and card.
- **Procedure.**
  1. Qualify R1 at 0.3 and 0.6 N.
  2. For each tyre, paper, load (0.3 and 0.6 N) and humidity (40 and 60 % RH), in random order, 5 repeats: static and kinetic friction with the wheel locked; rolling resistance with the wheel rolling.
  3. Report the spread (max/min) per tyre.
- **Measurands.** Static and kinetic friction coefficients; rolling resistance coefficient; spread across papers.

<!-- AC-TABLE:EXP-D01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D01-01 | REQ-DRV-004 | Kinetic tyre-paper friction coefficient of the chosen tyre compound (2 mm wheel, locked and rolling, R1 tribometer, TAPPI T 549 adapted) on each of the six reference papers (copy 80 g/m2, recycled, school ruled, coated, tracing, card) at 0.3 and 0.6 N, at 40 and 60 % RH; lowest cell mean | ≥ 0.6 | requirement | REQ-DRV-004; design range 0.6-1.2 (ASSUMPTION, drive/params.py); PU paper-feed rollers 1.30-2.20 new and 1.05-1.52 after 300 000 sheets (LIT AMF-111); paper friction tests agree within 24-27 % between labs (LIT AMF-113) | DEC-037 (revisit if below 0.6); tyre compound |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D01).
<!-- AC-TABLE:EXP-D01:END -->

- **Decision rule.** Choose the compound with the highest lowest-cell kinetic μ. If none reaches 0.6 on every paper, the drive gives proportionally less force on those papers: revisit DEC-037 and the papers the pen supports.

### EXP-D02: Tyre lateral stiffness and relaxation length

- **Purpose and gates.** Check the tyre's lateral stiffness. The model's 1.5 N/mm sets the slip threshold and the passive hold. Gates the slip rule (REQ-DRV-005) and the lateral release.
- **Predictions.** 1.5 N/mm with the fork and paper in series (ASSUMPTION). 2.1–2.6 N/mm for the tyre alone at 0.3–0.6 N (CALC, Mindlin). At 0.66 N the tyre deflects about 0.44 mm (CALC).
- **Set-up.** The wheel on paper at 0.55 N; a micrometre stage moves it sideways by 0–1 mm; a 3-axis force sensor under the paper.
- **Procedure.**
  1. Quasi-static lateral sweeps: 3 wheels × 5 repeats.
  2. Rolling at 5–20 mm/s with a step in heading, to find the relaxation length.
- **Measurands.** Lateral force against deflection (slope over 0–0.3 mm); relaxation length.

<!-- AC-TABLE:EXP-D02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D02-01 | — | Lateral stiffness of the 2 mm wheel's tyre on paper at 0.55 N, fork and paper in series (lateral displacement 0-1 mm, 3-axis force sensor under the paper), slope over 0-0.3 mm | ≥ 1.0 N/mm | hypothesis | pass line of the drive study; the model used 1.5 N/mm (ASSUMPTION) for the slip threshold and the passive hold; Mindlin tangential stiffness of the tyre alone 2.1-2.6 N/mm at 0.3-0.6 N (CALC, docs/grounded_drive.md s2.2) | DEC-037; slip rule (REQ-DRV-005) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D02).
<!-- AC-TABLE:EXP-D02:END -->

- **Decision rule.** Below 1.0 N/mm: set the slip threshold from the measured stiffness and re-run the release tuning (`python3 -m drive.run_study --stages release`).

### EXP-D03: Holding the sheet

- **Purpose and gates.** Know when the drive drags the paper instead of the pen. Gates REQ-DRV-011 (the drive's force stays below the sheet's holding force; instructions and app text).
- **Predictions.** A loose sheet under 1 N of writing load slides at 0.25–0.5 N. With the writing hand resting (1 N) and paper–desk μ 0.5 it holds 1.0 N (CALC; paper–desk μ 0.25–0.5 ASSUMPTION).
- **Set-up.** The heel drive pulls 0.1–0.6 N on a sheet lying on wood, laminate and a writing pad; a load cell or spring scale.
- **Procedure.** Ramp the drive force until the sheet slides: with no hand on the sheet; with the writing hand resting (1 N); with the other hand holding the sheet. 5 repeats per desk and condition.
- **Measurands.** Force at which the sheet slides.

<!-- AC-TABLE:EXP-D03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D03-01 | REQ-DRV-011 | Lateral force from the heel drive at which the sheet slides, with the writing hand resting (1 N writing load), on wood, laminate and a writing pad; lowest desk | ≥ 0.6 N | derived | REQ-DRV-011 (drive force below the sheet's holding force) with the 0.5 N cap of REQ-DRV-001 plus 0.1 N margin (pass line of the drive study); prediction 1.0 N with the hand resting and paper-desk mu 0.5, 0.25-0.5 N for a loose sheet without it (CALC, drive/contact.py; mu ASSUMPTION) | DEC-037; instructions and app text (REQ-DRV-011) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D03).
<!-- AC-TABLE:EXP-D03:END -->

- **Decision rule.** Below 0.6 N with the hand resting on a desk type: on that desk the app asks for a clip or a pad, or the cap is lowered below the measured holding force.

### EXP-D04: Heel geometry, roll and steering bench

- **Purpose and gates.** Contact over tilt and roll; steering speed and bandwidth; preload; the size of the front end. Gates REQ-DRV-004 (preload), REQ-DRV-006, REQ-DRV-007, REQ-DRV-008 and the front-end integration of DEC-036 and DEC-037.
- **Predictions.**
  - Contact up to ±20° of roll with 0.75 mm of spring travel on the Rev J ring (0.54 mm on the Rev H front end) (CALC, DEC-044).
  - Steering about 1570 rad/s no-load (0620 B, crown 2:1, 3.7 V; CALC). The SIM used a 40 Hz, 500 rad/s servo (ASSUMPTION). Letter headings turn at up to 71 rad/s (p90) and 283 rad/s (p99) (CALC).
  - Rev J front end (DEC-044): wheel 12.0 mm, ring 11.65 mm, sleeve front Ø23.3 mm flush, 24 mm where held with a 0.00 mm margin (CALC, PROPOSED DESIGN). Study D had 8.75 mm and Ø18.3 mm on the Rev H front end.
- **Set-up.** A 3-D printed heel with the sprung wheel pod and the two 0620 B motors, on the front end it will be built into. A tilt–roll fixture (R5 goniometer) for 35–75° and ±25° of roll. A load cell under the paper. The Hall angle sensor at the fork.
- **Procedure.**
  1. Measure the heel contact radius, the sleeve diameters and the opening on top (calipers, CAD review).
  2. At θ 35/50/75° and roll −25…+25° in 5° steps, log contact and wheel load.
  3. Measure the preload at the working deflection.
  4. Steering steps (rate limit) and chirps from 1 to 100 Hz (−3 dB bandwidth).
- **Measurands.** Contact (yes/no) and wheel load; preload; steering bandwidth and rate limit; dimensions.

<!-- AC-TABLE:EXP-D04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D04-01 | REQ-DRV-007 | Wheel contact with the paper (wheel load above 0.02 N) in the tilt-roll fixture at θ 35/50/75° and pen roll -20 to +20° in 5° steps | contact at every setting | requirement | REQ-DRV-007; prediction on the Rev J front end: contact to ±20° of roll with 0.75 mm of spring travel (CALC, DEC-044; 0.54 mm on the Rev H front end, study D) | DEC-037; DEC-044 |
| AC-D04-02 | REQ-DRV-006 | Steering servo closed-loop bandwidth (-3 dB, chirps, Hall angle sensor at the fork) and rate limit (step responses) at the wheel | ≥ 40 Hz and 300 rad/s | requirement | REQ-DRV-006; prediction about 1570 rad/s no-load (0620 B + crown 2:1 at 3.7 V; CALC); SIM assumed 40 Hz and 500 rad/s; letter headings turn at up to 71 rad/s (p90) and 283 rad/s (p99) (CALC) | DEC-037 |
| AC-D04-03 | REQ-DRV-004 | Heel pod preload: wheel load at the working deflection (load cell under the paper) at θ 35/50/75° | within 0.55 N ± 10 % | requirement | REQ-DRV-004; design 0.55 N (continuous optimum 0.57 N, CALC drive/design_opt.py) | DEC-037 |
| AC-D04-04 | REQ-DRV-008 | Front end with the heel drive, built to the Rev J layout (printed heel and CAD review): wheel and skid-ring contact radii, front sleeve diameter at the ring and where held, and the top opening (all) | all met (wheel ≤ 12.0 mm; ring ≤ 11.65 mm; sleeve front ≤ 23.3 mm, flush; ≤ 24 mm where held; open 120° on top and 10 mm into the sleeve) | requirement | REQ-DRV-008 (DEC-044; was ≤ 9.0 mm and ≤ 18.5 mm at the heel on the Rev H front end); prediction wheel 12.0 mm, ring 11.65 mm, sleeve front 23.3 mm, and 24 mm where held with a 0.00 mm margin (CALC, PROPOSED DESIGN, results/revJ/frontend.json and layout.json fit checks) -> at the limit | DEC-044; DEC-037; DEC-036 (front end holds the heel drive within 24 mm) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-D04).
<!-- AC-TABLE:EXP-D04:END -->

- **Decision rule.** Contact lost within ±20°: more spring travel. Steering too slow: change the ratio or the motor. Heel or sleeve larger than REQ-DRV-008 allows: re-run `revj/frontend.py` with the measured parts. If the heel drive cannot fit within Ø24 mm, revisit DEC-044 (and DEC-036, DEC-037).

### EXP-D05: Slip detection

- **Purpose and gates.** Test the slip rule: page sensor against wheel odometry. Gates REQ-DRV-005 and DEC-037.
- **Predictions.** In SIM the tyre truly slid for less than 0.1 % of contact time. Yet the simple rule raised 3–40 false flags per sentence, and each flag lowers the force cap for about 2 s (SIM). A model-based detector that uses the tyre-deflection estimate is needed (`docs/grounded_drive.md` §10). The page sensor's lens stays in its band only within about ±1.5° of roll (CALC, DEC-044), so slip detection is at risk with the pen rolled.
- **Set-up.** The heel pod on a linear stage over the six EXP-D01 papers, with the page sensor in its Rev J place beside the wheel (folded optics, DEC-044), at 0 and ±20° of pen roll. The page-sensor board and the wheel encoder logged at 1 kHz. A high-speed camera as the slip reference.
- **Procedure.**
  1. Impose gross slips by lowering the preload or raising the command: at least 29 per paper (§0.7).
  2. Replay recorded writing motion without slip, 10 min per paper, to count false flags.
  3. Run the simple rule and the model-based detector on the same records.
- **Measurands.** Detection latency; false flags per 10 s of normal writing motion.

<!-- AC-TABLE:EXP-D05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D05-01 | REQ-DRV-005 | Time from the start of an imposed gross wheel slip (lowered preload or raised command, six papers; high-speed camera reference) to the slip flag and the lowered command, page sensor in its Rev J place beside the wheel, at 0 and ±20° of pen roll; every imposed slip (≥ 29 per paper) | ≤ 50 ms | requirement | REQ-DRV-005; paper sensor against wheel odometry at 1 kHz (MFR AMF-109 class sensor; DEC-045 fits a PMW3610-class die, MFR OPT-61, whose rate on paper EXP-J10 measures); detection rule ASSUMPTION (docs/grounded_drive.md s2.2); the page sensor's lens stays in its band only within about ±1.5° of roll (CALC, DEC-044) -> at risk with the pen rolled | DEC-037 (revisit if slip detection is unreliable); DEC-044 |
| AC-D05-02 | REQ-DRV-005 | False slip flags per 10 s of replayed normal writing motion without true sliding (camera reference), six papers, at 0 and ±20° of pen roll; simple rule and model-based detector reported separately | < 1 per 10 s | requirement | REQ-DRV-005; SIM: true sliding < 0.1 % of contact time, yet the simple rule raised 3-40 false flags per sentence (docs/grounded_drive.md s5.1) -> the simple rule is predicted to FAIL; a model-based detector using the tyre deflection is needed; page-sensor dropouts with the pen rolled beyond about ±1.5° (CALC, DEC-044) add flags | DEC-037 (revisit if slip detection is unreliable); DEC-044 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-D05).
<!-- AC-TABLE:EXP-D05:END -->

- **Decision rule.** Keep the detector that passes. If neither passes, the traction estimate cannot be trusted: revisit DEC-037.

### EXP-D06: Noise, heat and power

- **Purpose and gates.** Check the power budget, heat and noise. Gates REQ-DRV-009, REQ-DRV-010 and REQ-THM-001 for the drive.
- **Predictions.**
  - Drive power 0–1 mW steer-only, 6 mW when guiding with a push, 84 mW while leading (SIM). Paper sensor 30–80 mW for a PMW3360-class die (CALC, MFR AMF-109); DEC-045 uses a PMW3610-class die at 1.3–1.9 mW, counted under REQ-RVJ-I07. Drivers and Hall sensors 10–20 mW (ASSUMPTION).
  - Winding rise 5–11 K at 146 K/W (CALC).
  - On the Rev J.1 layout (DEC-045): heel drive 0–2 mW in the steady mode (drivers asleep), 11–26 mW guiding and 103–113 mW leading (with the fourth mesh and the motor drivers). Pen runtime 12.1–16.1 h guiding and 7.5–8.8 h in lead-through (CALC). Rev J (DEC-044) had 0.14–0.19 W with its page sensor while leading, and 8.0–10.5 h and 5.9–6.9 h.
  - Noise not modelled.
- **Set-up.** The bench drive in a handle. Recorded drive commands from the SIM tasks. A sound level meter at 30 cm in a quiet room (A-weighted). Thermocouples on the windings and on the sleeve. Supply current logging (R7).
- **Procedure.** Replay each mode (steer-only guidance, guidance with a push, lead-through, autowrite) for 30 min. Log power, winding and surface temperatures and sound level (background subtracted). Compute the runtime with the measured base load of the Rev J.1 pen (EXP-N04, EXP-N08 and EXP-J12 power logs).
- **Measurands.** Mean electrical power per mode; winding rise; surface temperature; dB(A); runtime.

<!-- AC-TABLE:EXP-D06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D06-01 | REQ-DRV-009 | Mean electrical power of the heel drive (motors and drivers; the page sensor is REQ-RVJ-I07's) while replaying the recorded SIM drive commands of each mode for 30 min (steer-only guidance, steered and driven guidance, lead-through, autowrite) | ≤ 0.15 W | requirement | REQ-DRV-009 (DEC-045: the heel drive itself; was with the paper sensor); prediction on the Rev J.1 layout: 0-2 mW in the steady mode with the drivers asleep, 11-26 mW guiding and 103-113 mW leading (84 mW SIM / 0.9 for the fourth gear mesh, plus 10-20 mW of motor drivers, ASSUMPTION) (CALC, results/revJ1/budgets.json); with the PMW3610-class page sensor 0.105-0.115 W | DEC-037; DEC-044; DEC-045 |
| AC-D06-02 | REQ-DRV-009 | Winding temperature rise of the two 0620 B motors (thermocouples) after 30 min of the lead-through replay | < 10 K | requirement | REQ-DRV-009; prediction 5-11 K at 0.10-0.15 N RMS with 146 K/W (MFR AMF-100 Rth x 1.5 enclosed, ASSUMPTION; CALC) -> marginal | DEC-037 |
| AC-D06-03 | REQ-THM-001 | Handle surface temperature over the motor pocket after 30 min of the lead-through replay, referred to the rated 30 °C room (measured - room + 30 °C, ECMA-287 B.5); guarded acceptance | ≤ 41 °C | requirement | REQ-THM-001 design target (AMF-34, AMF-35; DEC-045: 41 °C in a rated 30 °C room, was referred to 25 °C); in the Rev J layout the motors sit under the cell (Rev J.1 moves them 10 mm further back), and the surface over them reached at most 27.0 °C in a 23 °C room (CALC, docs/revJ_design.md s6.4); study D had them at z 50-70 mm, behind the finger pads at z 26-38 mm (docs/grounded_drive.md s4.4) | DEC-037; safety before EXP-D08 |
| AC-D06-04 | REQ-DRV-010 | A-weighted sound level of the heel drive at 30 cm in a quiet room while guiding (steer-only and steered and driven replays), background subtracted | ≤ 35 dB(A) | requirement | REQ-DRV-010 (ASSUMPTION threshold, quiet classroom); noise not modelled | DEC-037 |
| AC-D06-05 | REQ-RVJ-I01 | Writing time per charge with assistance on: 2.22 Wh usable (MFR AMF-80) divided by the measured heel-drive power plus the measured base load of the Rev J.1 pen (nose, electronics, page sensor, pen lift; EXP-N04, EXP-N08, EXP-J12 and EXP-P01 power logs), guide and lead-through modes | ≥ 8 h (guide) / 7.5 h (lead-through) | requirement | REQ-RVJ-I01 (DEC-045 moved the hours here from REQ-DRV-009); prediction on the Rev J.1 layout: 12.1-16.1 h guiding and 7.5-8.8 h in lead-through (CALC, results/revJ1/budgets.json) -> lead-through marginal (7.55 h at the pessimistic end); every figure rests on study N's nose-coil power | DEC-037; DEC-045; Rev J power budget; DEC-050: measured on the Rev J.1 build with the C1S nose; Rev K's per-mode battery is REQ-RVK-002 (AC-P01-06), with lead-through only on DEC-065's heel module |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-D06).
<!-- AC-TABLE:EXP-D06:END -->

- **Decision rule.** Power over 0.15 W: review the motors and the drivers. Surface over 41 °C, referred to the rated 30 °C room: move or derate the motors (guarded acceptance, §0.5). Noise over 35 dB(A): better gear finish or a speed limit. Runtime under the targets of REQ-RVJ-I01: revisit the power budget (DEC-045).

### EXP-D07: Force cap, stall and lift safety

- **Purpose and gates.** Show that the drive never exceeds its caps and always lets go. Gates REQ-DRV-001, REQ-DRV-002, REQ-DRV-013 and DEC-037. **It is the safety gate before EXP-D08, D09 and D11.**
- **Predictions.**
  - Commands were capped in every SIM run.
  - The steer-only wheel's hold across its heading is a reaction, not a command: up to 0.66 N without the release. With the release the 95th percentile was 0.43–0.50 N and the maximum 0.49–0.56 N (tuning writers after the test, μ 1.2; SIM, `results/drive/release_tuning.json`).
  - Physics caps any force at the static traction, 0.36–0.73 N (CALC). The wheel turns at up to 1.6 m/s no-load, with at most 0.60 N of rim force through the Rev J gear train (0.67 N with study D's three meshes) (CALC, DEC-044).
- **Set-up.** The handle clamped to a 3-axis load cell over paper (the lowest- and highest-friction EXP-D01 papers). The R7 fault-injection board.
- **Procedure.**
  1. Command forces up to saturation in 8 directions.
  2. Stall the wheel.
  3. Push across the heading of the steer-only wheel with a force-controlled probe up to 1 N (release test).
  4. Lift the pen in the middle of a push.
  5. Hold the pen 4 mm off the template for 0.3 s; push against the drive with more than 0.5 N for 0.3 s.
  6. Inject faults: sensor loss, motor short.
  7. Check the wheel slot for pinch points.
- **Measurands.** Peak and steady force; time to zero after a lift, a stall or a yield trigger; heading during lifts.

<!-- AC-TABLE:EXP-D07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D07-01 | REQ-DRV-001 | Steady force of the heel drive on the pen (handle clamped to a 3-axis load cell over paper, lowest- and highest-friction EXP-D01 papers): commands up to saturation in 8 directions, wheel stalled, and the steer-only hold across the heading with the lateral release (force-controlled push up to 1 N) | ≤ 0.5 N | requirement | REQ-DRV-001; SIM: commands capped in every run; steer-only hold up to 0.66 N without the release, 95th percentile 0.43-0.50 N and maximum 0.49-0.56 N with it (tuning writers after the test, mu 1.2; results/drive/release_tuning.json) -> the release decides it | DEC-037 (revisit if the cap or the release fails); safety gate before EXP-D08, D09, D11 |
| AC-D07-02 | — | Peak force on the pen in the same runs and under fault injection (sensor loss, motor short, R7 board) | ≤ 0.6 N | derived | derived from the 0.5 N cap of REQ-DRV-001 with 0.1 N for transients (pass line of the drive study); physics caps any force at the static traction, static friction x 0.55 N = 0.36-0.73 N (CALC); guarded acceptance | DEC-037; safety gate before EXP-D08, D09, D11 |
| AC-D07-03 | REQ-DRV-013 | Time from the wheel load falling below 0.02 N (pen lifted mid-push) to zero drive torque (motor current), every lift (≥ 29) | ≤ 20 ms | requirement | REQ-DRV-013; met in SIM (drive/plant.py) | DEC-037; safety gate before EXP-D08, D09, D11 |
| AC-D07-04 | REQ-DRV-002 | Time to zero force after each yield trigger: pen held more than 4 mm off the template for 0.3 s; writer's force against the drive above 0.5 N for 0.3 s; wheel stalled; and no continued push against a stalled pen (≥ 29 trials per trigger) | ≤ 0.1 s | requirement | REQ-DRV-002; SIM: a writer set on 'b' overpowered a push of at most 0.37-0.47 N and the yield rule never had to act (docs/grounded_drive.md s5.3) | DEC-037; safety gate before EXP-D08, D09, D11 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-D07).
<!-- AC-TABLE:EXP-D07:END -->

- **Decision rule.** Any failure: no participant uses the drive. Fix the supervisor or the release and repeat. If the release cannot cap the hold, revisit DEC-037.

### EXP-D10: Ink smear and wheel track

- **Purpose and gates.** Make sure the wheel does not smear ink or mark the paper. Gates REQ-DRV-012 (clean contact) and the tyre compound.
- **Predictions.** Not modelled. The wheel runs 6.6 mm behind the ball, on the paper side (PROPOSED DESIGN). Rolling contacts on paper collect dust and ink (LIT AMF-117, PAT-33).
- **Set-up.** The wheel at 0.55 N on a linear stage; fresh gel and ballpoint ink; a microscope camera; R3 scans.
- **Procedure.** Roll over fresh lines 1, 5 and 30 s after writing. Write one page with the drive in each mode. Image the tyre and the paper. Blinded viewers look for a track at 30 cm.
- **Measurands.** Smear length; ink on the tyre; visible track.

<!-- AC-TABLE:EXP-D10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D10-01 | REQ-DRV-012 | Wheel rolled at 0.55 N over fresh gel and ballpoint ink (1, 5 and 30 s after writing) and over one page of writing in each mode: ink on the tyre (microscope camera) and a wheel track seen at 30 cm by blinded viewers | no ink pick-up; no visible track | hypothesis | pass line of the drive study; rolling contacts on paper collect dust and ink (LIT AMF-117, PAT-33); the wheel runs 6.6 mm behind the ball on the paper side (PROPOSED DESIGN); not modelled | DEC-037; tyre compound |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D10).
<!-- AC-TABLE:EXP-D10:END -->

- **Decision rule.** Ink pick-up or a visible track: change the tyre compound or lower the preload, then repeat EXP-D01 for that compound.

### EXP-D12: Durability

- **Purpose and gates.** Tyre wear and friction drift; cleaning and replacement by the user. Gates REQ-DRV-012 and the tyre change interval.
- **Predictions.** Not modelled. Polyurethane paper-feed rollers lost about 20–30 % of their friction over 300 000 sheets (LIT AMF-111).
- **Set-up.** A rolling rig: the wheel on copy paper at 0.55 N. The EXP-D01 tribometer.
- **Procedure.**
  1. Roll 10 km (about 5000 pages, ASSUMPTION). Re-measure friction and diameter every 1 km.
  2. A user who follows the instructions cleans and replaces the tyre and the pod.
  3. Inspect the inside of the pod for dust and ink.
- **Measurands.** Friction drift; diameter loss; dust and ink inside the pod; cleaning and replacement done without help.

<!-- AC-TABLE:EXP-D12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D12-01 | — | Tyre after 10 km of rolling on copy paper at 0.55 N (about 5000 pages, ASSUMPTION): kinetic friction relative to new (re-measured every 1 km) and diameter loss (both) | both met (within 20 % of new; < 0.05 mm) | hypothesis | pass line of the drive study; PU paper-feed rollers lost about 20-30 % of their friction over 300 000 sheets (1.30-2.20 -> 1.05-1.52, LIT AMF-111) | DEC-037; tyre compound and change interval |
| AC-D12-02 | REQ-DRV-012 | After the 10 km run: the tyre and the heel pod are cleaned and replaced by a user following the instructions, and no paper dust or ink is found inside the pod (microscope inspection) (both) | both met | requirement | REQ-DRV-012; pod sealing not yet designed | DEC-037 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-D12).
<!-- AC-TABLE:EXP-D12:END -->

- **Decision rule.** Friction outside 20 % of new, or wear over 0.05 mm: set a tyre change interval or choose another compound. Dust or ink in the pod: improve the seal.

### EXP-D13: Driven-ball fallback: roller drag and wear

- **Purpose and gates.** Decide whether the driven ball can be built with low internal drag. In SIM it traced and damped tremor better than the wheel. Gates the ball as the bench alternative of DEC-037.
- **Predictions.** The SIM assumed 30 mN of roller drag (omni-type rollers, ASSUMPTION). Smooth rollers give about 0.22 N (CALC: 0.3 × 0.75 N roller preload). The ball traced at 288 µm against the wheel's 372 µm (SIM).
- **Set-up.** A bench ball drive: a 2 mm urethane-coated ball, two rollers of r 0.4 mm, smooth and micro omni-type (if they can be made); a force sensor.
- **Procedure.** Push the ball along each roller axis and across it. Roll 1 km on paper. Repeat the drag test. Image wear and dust.
- **Measurands.** Internal drag across the driven axis; drive force; wear; dust pick-up.

<!-- AC-TABLE:EXP-D13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D13-01 | — | Internal drag of the driven ball across the driven axis after 1 km of rolling on paper (2 mm urethane-coated ball, two rollers r 0.4 mm), smooth and micro omni-type rollers reported separately | ≤ 50 mN | hypothesis | pass line of the drive study; the SIM assumed 30 mN (omni-type rollers, ASSUMPTION); smooth rollers about 0.22 N (CALC: 0.3 x 0.75 N roller preload) -> smooth rollers predicted to FAIL | DEC-037 (driven ball as the bench alternative) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-D13).
<!-- AC-TABLE:EXP-D13:END -->

- **Decision rule.** Pass: build the ball as the bench alternative for EXP-D08 and D09. Fail: drop the ball.

---

## 42. Rev J inertial end-cap: EXP-K01, K02, K04, K06, K07, K08

### Purpose and what it gates

DEC-038 fits a detachable rear end-cap to the first Rev J prototype. Four arc coils push a 30.4 g tungsten slug (non-magnetic grade) by ±4 mm in two axes, on two 5 Hz flexures. The end-cap is Ø26 × 24 mm, sits behind the cell in place of the rear cap (z 141.7–165.7 in the Rev J layout, DEC-044, so the pen is 165.7 mm) and weighs 43 g. The tracker's feed-forward drives it on top of the nose (gain 0.75). DEC-045 (Rev J.1) makes it lighter: a 9 mm tungsten slug (17.3 g), 29.6 g and Ø26 × 21 mm, so the pen with it is 161.9 mm and 112.7 g. It runs only while a tremor line is detected, and EXP-J16 (§46) repeats EXP-K02 with it.
- **Inertia steadies and cues; it does not write.** Cues are played only in pauses, and only after EXP-K05. No rotor goes in the product; a CMG end-cap stays a research module for torque-pulse cues.
- **Superseded for the product (DEC-051, 2026-09-29).** Inertial tails are rejected for the pen, and the end-cap stays only as a bench comparison against the same mass locked (EXP-J16, and EXP-W14 on R14 in EXP-T16). REQ-EC-001, 002 and 003 are bench-only. REQ-EC-004, 005, 006 and 008 apply again only if an end-cap returns through REQ-WP-001 (≥ 10 % against the same pen with it locked, at three grip strengths, with coverage kept; AC-T16-01). So EXP-K01, K02, K07 and K08 stay bench comparisons; EXP-K03, K05 and K04's review of product text run only if an end-cap returns; EXP-K06's methods serve the gyroscope pair of EXP-W14 (REQ-WP-010: ≤ 2 J).
- **What it gates.** DEC-038 is revisited if EXP-K02 gives less than 10 % further reduction at the measured grip split, or the fixed weight comes within 5 points; if EXP-K01 misses the force model by more than 20 %; if EXP-I01 or K08 find r_rot outside 0.3–0.7; if writers reject the back-heavy pen (EXP-K03). Requirements: REQ-EC-001…009.
- **Predictions** come from `docs/inertial_endcap.md` and `results/endcap/endcap_study.json` (H1 with the causal Rev H tracker; test seeds 200–203; grip splits r_rot 0.3 / 0.5 / 0.7; CALC and SIM). They were run on the **Rev H** pen and nose (75 g, Ø22 mm), not on the Rev J pen (Ø24 mm; 87.0 g in DEC-044, 84.3 g in Rev J.1, DEC-045). The Rev J.1 end-cap family ran on the same Rev H model (EXP-J16).
- Work with people (EXP-K03, K05) is in [`human_study_plan.md`](human_study_plan.md) §17. EXP-K04 and EXP-K08 include participants; they are covered by the same ethics approval as EXP-B06 and EXP-I01.

### EXP-K01: Reaction-mass actuator against its model

- **Purpose and gates.** Check the actuator, the envelope, the power and the slug's material before any tremor test. Gates REQ-EC-001, REQ-EC-008, REQ-EC-009 and DEC-038.
- **Rig (study M).** The force-constant part runs on R12 in EXP-T07 (§47; `docs/measurement_rig.md` §5.3). The net force on the housing (AC-K01-01) stays this experiment's own bench test, on a clamp fixture at R12; EXP-T16 does not measure it (the lead's decision, `prototype_stages.md` §0).
- **Predictions.**
  - K_m 0.735 N/√W; 0.52 N per axis at 0.5 W; ±4.0 mm stroke on 5 Hz flexures (CALC).
  - Power: 1.0 W peak and 0.145 W average in the design model; 0.029 W average in the test runs, drivers included (CALC, SIM).
  - End-cap Ø26 × 24 mm, 43.3 g (study K). Rev J.1 end-cap (DEC-045): Ø26 × 21 mm, 29.6 g, K_m 0.598 N/√W, 0.082 W average in the design model and 0.028 W in the SIM test runs. Rev J.1 pen: 84.3 g base and 112.7 g with the end-cap, centre of mass 102.5 mm from the tip (CALC); REQ-EC-001 allows 120 g with the end-cap fitted (Rev J had 129.2 g).
  - With the end-cap active only while a tremor line is detected, on the Rev J.1 base load: 7.7–8.6 h at 1 mm tremor at the SIM power and 6.4–7.1 h at the design power (CALC, DEC-045). Rev J had 4.3–6.6 h, and the Rev H base load of 0.081 W gave 9.8–20 h.
  - ET95NM relative permeability ≤ 1.05 (MFR AMF-49).
- **Set-up.** The end-cap clamped to a 6-axis load cell (ATI Nano17 class) on a clamp fixture at R12. Coil current and slug position (Hall) logged. A permeability meter. A balance.
- **Procedure.**
  1. Incoming inspection: permeability of every tungsten part that sits within 20 mm of a Hall sensor or coil.
  2. Weigh and measure the end-cap, and the Rev J.1 pen with the end-cap fitted.
  3. Drive each axis with sines of 1–15 Hz at 0.1–1 W.
  4. Drive the slug to ±4 mm and check for contact.
  5. Log the power during the EXP-K02 tremor runs with the nose on.
- **Measurands.** Net force on the housing; K_m; stroke; flexure frequency and damping; power; mass and size; permeability.

<!-- AC-TABLE:EXP-K01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K01-01 | — | Net force on the housing per axis (end-cap clamped to a 6-axis load cell), sines 1-15 Hz at 0.1-1 W, against the model (endcap/design.py; rm_coil_cap in endcap/sim.py) | within ±20 % of the model | hypothesis | pass line of study K; DEC-038 is revisited if EXP-K01 misses the force model by more than 20 %; model net push about 0.9 x m x omega^2 x X at the slug's limit (CALC) | DEC-038 |
| AC-K01-02 | — | Coil force constant K_m per axis (force and current) and slug stroke: ±4 mm reached in both axes without contact (both) | both met (K_m ≥ 90 % of the design value: 0.598 N/√W for the Rev J.1 end-cap, 0.735 for study K's; ±4 mm without contact) | hypothesis | pass line of study K; design K_m 0.735 N/√W, 0.52 N per axis at 0.5 W, ±4.0 mm on two 5 Hz flexures (CALC, docs/inertial_endcap.md s9.1); in the test runs the slug reached its stops in 39 of 180 cases (SIM): soft end-stops; the Rev J.1 end-cap (DEC-045, 9 mm slug): K_m 0.598 N/√W, 0.42 N, ±4.0 mm on 5 Hz flexures (CALC, results/revJ1/sim_params.json) | DEC-038 |
| AC-K01-03 | REQ-EC-001 | Built end-cap: diameter, length and mass; peak and average electrical power (drivers included) logged during the EXP-K02 tremor runs | ≤ 26 mm, 45 mm, 45 g; 1 W peak, 0.3 W average | requirement | REQ-EC-001; prediction for the Rev J.1 end-cap (DEC-045): Ø26 x 21 mm, 29.6 g; 0.082 W average in the design model and 0.028 W in the SIM test runs; peak not recomputed (CALC, SIM; results/revJ1/endcap.json); study K's end-cap Ø26 x 24 mm, 43.3 g, 1.0 W peak and 0.145 W average (results/endcap/endcap_study.json) | DEC-038 |
| AC-K01-04 | REQ-EC-001 | Rev J.1 pen as built, weighed and measured, with the end-cap fitted | ≤ 175 mm and 120 g | requirement | REQ-EC-001 (DEC-045: ≤ 120 g with the end-cap fitted; was 120 g base and a provisional 130 g with the end-cap); prediction 143.9 mm and 84.3 g base, 161.9 mm and 112.7 g with the 29.6 g end-cap (CALC, results/revJ1/budgets.json): 7.3 g under 120 g | DEC-038 (detachable end-cap); DEC-045; Rev J envelope |
| AC-K01-05 | REQ-EC-008 | Writing time per charge in the steady mode at 1 mm tremor with the end-cap active only while a tremor line is detected: 2.22 Wh usable (MFR AMF-80) divided by the measured base load of the Rev J.1 pen plus (a) the end-cap's measured mean power at its measured duty (EXP-K02 or EXP-J16 runs) and (b) its design power (both) | both met (≥ 8 h at the measured duty; ≥ 6 h at the design power) | requirement | REQ-EC-008 (DEC-045 folded it into REQ-RVJ-I01 as its end-cap row; DEC-051 took the end-cap out of the product, so it is judged only if an end-cap returns through REQ-WP-001; was ≥ 8 h with the end-cap active); prediction on the Rev J.1 base load: 7.7-8.6 h at the SIM power of 27.6 mW (8.6 h only with the typical electronics) and 6.4-7.1 h at the design power of 82 mW (CALC, SIM; results/revJ1/budgets.json) -> the 8 h part is marginal | DEC-038; DEC-045; Rev J power budget |
| AC-K01-06 | REQ-EC-009 | Relative magnetic permeability of every tungsten part within 20 mm of a Hall sensor or coil (incoming inspection, permeability meter) | ≤ 1.05 | derived | REQ-EC-009 made measurable: ET95NM relative permeability ≤ 1.05 (MFR AMF-49); INERMET grades paramagnetic (MFR AMF-125) | DEC-038; Hall sensor bias |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-K01).
<!-- AC-TABLE:EXP-K01:END -->

- **Decision rule.** Force model missed by more than 20 %: re-fit `endcap/design.py` and re-run study K (DEC-038 revisit). Pen with the end-cap over 120 g (112.7 g predicted): the end-cap stays detachable (DEC-038, DEC-045). Runtime under the end-cap row of REQ-RVJ-I01: log the end-cap's duty and revisit the power budget (DEC-045). A magnetic tungsten part: reject it.

### EXP-K02: Tremor on top of the nose, on a bench (extends EXP-I06)

- **Purpose and gates.** Measure the further reduction that the end-cap adds on top of the nose, and compare it with the same mass fixed. Gates REQ-EC-002, REQ-EC-003 and DEC-038.
- **Rig (study M).** Runs on R14, the grip simulant on R13's stage, as part of EXP-T16 (§47; `docs/measurement_rig.md` §7.3).
- **Predictions (SIM).**
  - Further reduction at 8–12 Hz, 1–2 mm: +8 / +18 / +20 % at r_rot 0.3 / 0.5 / 0.7 (seed spread +4 to +25 %).
  - The same 45 g fixed: +17 / +12 / +4 %. So the motion adds −9 / +6 / +16 points.
  - At 4–6 Hz: +8 to +12 %.
  - The fixed weight makes 29–42 % of the hard cases worse than the nose alone at r_rot 0.5–0.7; the moving slug 4–12 %.
  - The slug reached its stops in 39 of 180 test cases: soft end-stops are needed.
  - The Rev J.1 end-cap (29.6 g, DEC-045) is tested the same way in EXP-J16 (§46): +5.6 / +16.8 / +18.3 % (SIM).
- **Set-up.** The EXP-I06 rig. The nose (Rev H, as simulated, or nose v2 once built) and the end-cap on a hand–pen rig with an HAP-26-like spring–mass hand. Three grip-split settings, one of them nearest the value that EXP-I01 or EXP-K08 measures. A shaker injecting 4–12 Hz at 0.3–2 mm. Writing on paper by a 2-axis stage. R3 scans or a digitiser.
- **Procedure.** Four configurations in random order: nose alone; nose and the same mass fixed; nose and the active end-cap (causal tracker, gain 0.75); nose and the end-cap switched off. 10 seeds per condition. Log slug stroke, stop impacts and power.
- **Measurands.** RMS ink error against the tremor-free trace; further reduction against the nose alone; stroke; stop impacts.

<!-- AC-TABLE:EXP-K02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K02-01 | REQ-EC-002 | Further reduction of the RMS ink error with the active end-cap on top of the nose (causal tracker, gain 0.75), hand-pen rig with an HAP-26-like hand and shaker tremor at 8-12 Hz, 1-2 mm, at the grip-split setting nearest the measured split (EXP-I01 or EXP-K08); 10 seeds | ≥ 10 % | requirement | REQ-EC-002 (rule R-T1; DEC-033 bar); prediction +8 / +18 / +20 % at r_rot 0.3 / 0.5 / 0.7 on the Rev H nose, seed spread +4 to +25 % (SIM, results/endcap/endcap_study.json) -> marginal at r_rot 0.3 | DEC-038 (revisit if below 10 % at the measured split) |
| AC-K02-02 | REQ-EC-002 | Further reduction with the active end-cap at the other two grip-split settings (8-12 Hz, 1-2 mm), and the mean over all tremor conditions at every setting | ≥ 5 % (other splits) and 0 % (mean at every split) | requirement | REQ-EC-002 (rule R-T1: ≥ 5 % at the other splits, never worse on average); prediction: no split worse on average; 4-6 Hz +8 to +12 % (SIM) | DEC-038 |
| AC-K02-03 | REQ-EC-003 | Further reduction with the active end-cap minus that with the same mass fixed in the end-cap (nose + weight), same rig and conditions, at the measured grip split | ≥ 5 points | requirement | REQ-EC-003; prediction -9 / +6 / +16 points at r_rot 0.3 / 0.5 / 0.7 (SIM) -> FAILS at r_rot 0.3 (then fit the weight or nothing); the fixed weight worsens 29-42 % of hard cases at r_rot 0.5-0.7, the slug 4-12 % | DEC-038 (revisit if the weight comes within 5 points) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-K02).
<!-- AC-TABLE:EXP-K02:END -->

- **Decision rule.** Pass: keep the end-cap in the prototype; EXP-K03 decides the product. Under 10 % at the measured split, or the weight within 5 points: fit the weight or nothing (DEC-038 revisit).

### EXP-K04: Can an end-cap steer the ink?

- **Purpose and gates.** Confirm that inertia can nudge the ink but not write. Gates REQ-EC-004 (no writing claim) and the use of the end-cap for cues.
- **Predictions (SIM).** No device reaches 2 mm at 1–3 Hz: the reaction mass at most 0.21 mm, the CMG at most 1.06 mm (rule R-S1). One 150 ms pulse shifts the ink by 0.38–0.46 mm (reaction mass) or 0.23–0.54 mm (CMG), and the ink returns to within 0.005 mm after the reset.
- **Set-up.** The EXP-K02 rig, then 6 healthy writers. The reaction-mass end-cap and, if built, the CMG research module (only after EXP-K06).
- **Procedure.** Open-loop sines at 1–5 Hz at 90 % of the device limit, in the tilt plane and sideways, while the rig or the writer writes lines. Single 150 ms pulses. The same runs with the device idle.
- **Measurands.** Ink displacement caused by the device (the difference to the idle run), peak and in band.

<!-- AC-TABLE:EXP-K04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K04-01 | REQ-EC-004 | Largest ink displacement caused by the end-cap (difference to the same run with the device idle) under open-loop sines at 1-3 Hz at 90 % of the device limit, any direction, on the rig and in 6 healthy writers writing lines | < 2 mm | derived | REQ-EC-004 (rule R-S1: 'can write' is ≥ 2 mm at 1-3 Hz); prediction reaction mass ≤ 0.21 mm, CMG ≤ 1.06 mm (SIM) -> expected to hold (no writing claim) | DEC-038 (never described as writing or steering) |
| AC-K04-02 | — | Ink shift caused by one 150 ms end-cap pulse while writing lines (rule R-S1 'can nudge'), and the shift left 1 s after the reset | ≥ 0.2 mm | hypothesis | prediction 0.38-0.46 mm (reaction mass push-pull) and 0.23-0.54 mm (CMG pulse), back within 0.005 mm after the return (SIM) | DEC-038 (cue use) |
| AC-K04-03 | REQ-EC-004 | Review of product text, modes and app screens after the EXP-K04 result: none claims that the end-cap moves, steers or writes letters; it is described as a steadier and a cue | conforms | requirement | REQ-EC-004; DEC-038 | DEC-038 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-K04).
<!-- AC-TABLE:EXP-K04:END -->

- **Decision rule.** Below 2 mm (as predicted): REQ-EC-004 stands, and the product text is reviewed (AC-K04-03). At or above 2 mm: stop, and reopen the question with the lead before any writing claim.

### EXP-K06: Rotor safety and comfort (only if a rotor is kept)

- **Purpose and gates.** Make the CMG research module safe before anyone holds it. Gates REQ-EC-007. It is a gate before any participant uses a rotor (EXP-K04, K05).
- **Predictions (CALC).** Stored energy 3.0 J (the cap); spin-up 8.1 s; a 466 Hz tone; rotor centre stress 3.9 MPa against ≥ 724 MPa (factor 184); imbalance 0.16 N at G2.5 and 0.026 N at G0.4; a seizure within 10 ms kicks with about 0.2 N m. The 2 s stop time is a target (ASSUMPTION).
- **Set-up.** A containment test enclosure; a 1 m drop rig; a sound level meter at 30 cm; speed and power logging.
- **Procedure.** Spin to 1.2 × the design speed. Drop from 1 m with the rotor running. Burst containment test. Stop time after a detected drop. Spin-up time and spin power. Sound level and tone.
- **Measurands.** Containment (pass/fail); stop time; spin-up time; stored energy (from the measured speed and inertia); balance grade; sound level.

<!-- AC-TABLE:EXP-K06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K06-01 | REQ-EC-007 | CMG research module: burst containment at 1.2 x the design speed and after a 1 m drop with the rotor running (no fragment escapes); rotor stop time after a detected drop; spin-up time; stored energy from the measured speed and inertia; balance grade (all) | all met (no fragment; ≤ 2 s; ≤ 10 s; ≤ 3 J; G1 or better) | requirement | REQ-EC-007; prediction 3.0 J (at the cap), spin-up 8.1 s, centre stress 3.9 MPa against ≥ 724 MPa (AMF-49), imbalance 0.16 N at G2.5 and 0.026 N at G0.4 (CALC); 2 s stop time is a target (ASSUMPTION); guarded acceptance | DEC-038 (CMG as a research module only); gate before any participant holds a rotor |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-K06).
<!-- AC-TABLE:EXP-K06:END -->

- **Decision rule.** Any failure: no participant uses a rotor. The acceptable sound level is agreed with users before the test (no criterion yet).

### EXP-K07: Does spin itself steady the pen?

- **Purpose and gates.** Test gyroscopic stiffening directly. Gates DEC-038 (no passive gyroscope in the product).
- **Rig (study M).** Runs on R14 as the rotor condition of EXP-T16, only if a rotor is kept (§47; `docs/measurement_rig.md` §7.3).
- **Predictions (SIM).** Rule R-G1 fails: spin made the ink error 0.7 % larger than the same mass not spinning. Thirty times more spin did not help.
- **Set-up.** The EXP-K02 rig without the nose; a rotor end-cap, spinning and not spinning (same mass).
- **Procedure.** 4, 8 and 12 Hz at 1 mm; three grip splits; 10 seeds; random order.
- **Measurands.** RMS ink error.

<!-- AC-TABLE:EXP-K07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K07-01 | — | RMS ink error at 4, 8 and 12 Hz, 1 mm, on the EXP-K02 rig without the nose: rotor end-cap spinning relative to the same rotor not spinning (same mass), r_rot 0.5 setting | ≤ 0.9 | hypothesis | rule R-G1 (≥ 10 % lower with spin); prediction 1.007 (spin made the ink error 0.7 % larger) and 30 x more spin did not help (SIM) -> expected FAIL | DEC-038 (no passive gyroscope in the product) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-K07).
<!-- AC-TABLE:EXP-K07:END -->

- **Decision rule.** Fail (as predicted): no passive gyroscope. Pass: reopen the rotor options with the lead.

### EXP-K08: Grip split with the end-cap fitted

- **Purpose and gates.** Measure r_rot on the Rev J pen with the method of EXP-I01 (§35). Every end-cap result is given at r_rot 0.3, 0.5 and 0.7. Gates DEC-038 and the grip-split setting of EXP-K02.
- **Predictions.** Unknown. The study assumed 0.3–0.7 (H1 grip calibrated to HAP-26; split ASSUMPTION).
- **Set-up.** An instrumented pen with a 6-axis load cell between the front and rear grip zones (R6 with a second stinger, as EXP-I01), with and without the end-cap (29.6 g in Rev J.1, DEC-045; study K's was 45 g). 20 writers.
- **Procedure.** As EXP-I01, once with and once without the end-cap, in random order.
- **Measurands.** Rotational stiffness about the grip; r_rot with its 95 % interval.

<!-- AC-TABLE:EXP-K08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K08-01 | — | Grip split r_rot (rotational share of the grip compliance about the grip, EXP-I01 method) with and without the end-cap (the 29.6 g Rev J.1 end-cap, DEC-045), 20 writers: median with its 95 % interval | within 0.3-0.7 | hypothesis | DEC-038 revisit trigger (r_rot outside 0.3-0.7); study K reported every result at r_rot 0.3 / 0.5 / 0.7 (split ASSUMPTION; H1 grip calibrated to HAP-26) | DEC-038; grip-split setting of EXP-K02; weight mode |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-K08).
<!-- AC-TABLE:EXP-K08:END -->

- **Decision rule.** Outside 0.3–0.7: re-run study K (`python3 -m endcap.run_study`) with the measured value (DEC-038 revisit). Near 0.3, where the fixed weight did better in SIM: test the held "weight mode" (a proposal, not simulated).

---

## 43. Rev J nose v2 and autowrite: EXP-N01…N08

### Purpose and what it gates

DEC-036 keeps architecture B: the skid ring on the fixed sleeve carries the writing force. The gimbal moves to 76.5 mm behind the ball, with the magnets on an 11.5 mm arm behind it. The magnets are a 2 × 2 N52 checkerboard on a spherical iron cap that faces a coil plate on a concentric sphere (0.77 mm gap at every tilt).
- **Numbers.** Handle Ø24 mm. Ball travel 6.0 mm in every direction over 35–75°. In the Rev J layout (DEC-044) the nominal travel is 6.57 mm at 50°, the skid ring 11.65 mm with the heel wheel at 12.0 mm, and the refill slide 26.6 mm (study N alone: 6.5 mm, 10.0 mm, 24 mm).
- **Pen lift.** A module at the gimbal sets the 0.15 N ink force through a tendon and lifts the ball 0.5 mm, with no holding power. A page sensor (1 kHz, ≤ 2 ms, ≤ 10 µm) is required. DEC-044 details them: a spiral spring in the drum, front and rear pulleys, a front stop by the drum brake (EXP-J06), and the page sensor beside the heel wheel (EXP-J04).
- **Autowrite (DEC-039).** In an explicit mode the pen draws a known text inside the nose's reach while the user sweeps the pen along the line.
- **Corrections to Rev H (DEC-041).** The image-method magnetics give the Rev H nose 0.19 N/√W at the magnets, not 0.47 (EXP-N01 measures both). A stock constant-force refill spring may last about an hour of tremor stabilisation (EXP-N06). A free refill follows ordinary pen lifts at 50–70° (EXP-N05).
- **What it gates.** DEC-036 is revisited if EXP-N01 measures K_m below 0.85 × the design value, EXP-N04 exceeds 20 K or 41 °C, or EXP-N07 cannot give a 1 kHz page position. Requirements: REQ-RVJ-N01…N08, and REQ-RVH-003 for the Rev H coupon.
- **DEC-050 (2026-09-30).** The C1S nose is not carried forward into the next prototype, Rev K, whose fast core is study B's balanced nib B1 (§51). The nose stays a bench research module, and autowrite (DEC-049) becomes a research mode on the bench with it: an accepted word needs about ±4–6 mm of reach, and B1 has ±1.0 mm. REQ-RVJ-N01…N04 and N09 now describe the research module; REQ-RVJ-N05 is superseded for the product (by REQ-BNIB-014 and REQ-BNIB-008); REQ-RVJ-N07, N08 and REQ-CTRL-014 describe the research mode. The C1S criteria of EXP-N01…N06, and those of EXP-N08, say so in their gates.
- **Predictions** come from `docs/nose_v2.md` and `results/nose2/nose2.json`: design models optimised by CMA-ES and adjoint L-BFGS (CALC), and autowrite in model HW1 on synthetic writers and tremor (test writers 0–5, seeds 200–203; SIM). The magnetics are an upper bound (ideal iron).
- **Freedom to operate.** Autowrite with a pen lift is close to claim 1 of PAT-01. Attorney review comes before any product claim (DEC-036).
- Work with people (EXP-N09, N10) is in [`human_study_plan.md`](human_study_plan.md) §18.

### EXP-N01: Magnetics before building a nose (and Rev H's K_m)

- **Purpose and gates.** Measure the force constant of the recommended actuator, and settle Rev H's. Gates DEC-036, DEC-041 item 1, REQ-RVJ-N02 and REQ-RVH-003.
- **Rig (study M).** Runs on R12 as part of EXP-T07 (§47; `docs/measurement_rig.md` §5.3).
- **Predictions.**
  - C1S spherical-gap unit: 0.66 N/√W per axis at the magnets, 0.099 N/√W at the tip; gap flux 0.75 T (image method, an upper bound; CALC).
  - Rev H radial unit: 0.47 N/√W by the lumped adjoint model, against 0.19 N/√W and 0.12 T by the image method (CALC).
  - A large-stroke Lorentz actuator in the literature varied by 21.6–30.9 % over ±5 mm (LIT AMF-143).
- **Set-up.** Two coupons on R4. One Rev H radial unit: 3.0 × 6.5 × 2.8 mm N45 magnets, 1.43 mm coil, 2.77 mm gap. One C1S unit in the recommended geometry: a machined spherical Hiperco or 1010 cap and plate, 0.2 mm self-bonding wire, with the Rev J bottom flat and notch for the drive shafts and 2.37 mm of back iron (DEC-044; the notch's effect on K_m is not computed), and a second plate with the 1.5 mm back iron of DEC-045 (compared in EXP-J14). A 0–2 N load cell (0.5 mN resolution), a bench supply, a gaussmeter, a micro-ohmmeter at 20 °C.
- **Procedure.**
  1. Coil resistance at 20 °C.
  2. Gaussmeter map of the gap.
  3. Force per ampere over the stroke grid, both axes: the C1S unit over ±1.05 mm of magnet stroke, the Rev H unit over its 2.3 mm.
- **Measurands.** K_m (N/√W) per axis over the stroke; gap flux (T); force ripple (%).

<!-- AC-TABLE:EXP-N01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N01-01 | REQ-RVJ-N02 | Force constant of the C1S spherical-gap coupon per axis over the whole magnet stroke (±1.05 mm; load cell and coil current), as a fraction of the CALC value (0.66 N/√W at the magnets, 0.099 N/√W at the tip); lowest point of the map | ≥ 0.85 | requirement | REQ-RVJ-N02; image-method magnetics with ideal iron, an upper bound (gap flux 0.75 T; CALC, results/nose2/nose2.json) | DEC-036 (revisit if below 0.85 x the design value); DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N01-02 | — | Force ripple of the C1S coupon over the magnet stroke ((max - min) / mean of the force per ampere) | ≤ 15 % | hypothesis | pass line of the nose v2 study; a large-stroke 2-DOF Lorentz actuator varied 21.6-30.9 % over ±5 mm (LIT AMF-143): if higher, calibrate a force map | DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N01-03 | REQ-RVH-003 | Force constant of the Rev H radial-gap coupon (3.0 x 6.5 x 2.8 mm N45, 1.43 mm coil, 2.77 mm gap) per axis at the magnets, mapped over its 2.3 mm stroke | ≥ 0.40 N/√W | requirement | REQ-RVH-003; lumped adjoint model 0.47 N/√W (results/revH/tip_params.json) against 0.19 N/√W with 0.12 T by the image method (CALC, docs/nose_v2.md s4.2) -> contested, likely to FAIL (DEC-041 item 1); the Rev H coil loss would rise from 0.004 to about 0.027 W | DEC-041 (confirm 0.47 N/√W); DEC-032 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N01).
<!-- AC-TABLE:EXP-N01:END -->

- **Decision rule.** C1S below 0.85 × the CALC value: revisit DEC-036 (re-run `python3 nose2/run_study.py` with the measured flux; the radial-gap C1 reaches 5 mm). Rev H below 0.40 N/√W (as predicted): REQ-RVH-003 fails, and the Rev H coil loss while writing rises from 0.004 to about 0.027 W (DEC-041). Ripple above 15 %: calibrate a force map in the firmware.

### EXP-N02: Travel and front-end closure over 35–75°

- **Purpose and gates.** Check the guaranteed travel and the front end. Gates REQ-RVJ-N01 and DEC-036.
- **Rig (study M).** Runs on R13 as part of EXP-T13 (§47; `docs/measurement_rig.md` §6.3).
- **Predictions (CALC, PROPOSED DESIGN; `results/revJ/layout.json` fit checks, DEC-044).** 6.00 mm guaranteed and 6.57 mm at 50°. Skid-ring contact radius 11.65 mm, heel wheel 12.0 mm. Refill slide 26.6 mm over 35–75°. Margins over the rules: nozzle 1.15 mm, ring lip 1.97 mm, carrier to the ring 0.09 mm, heel pod to the nose 0.10 mm. Sleeve front 0.86 mm above the paper at 35°.
- **Set-up.** The nose built to the Rev J layout (`results/revJ/layout.json`, DEC-044), with its skid ring and the heel pod, once EXP-J01 has cleared the gimbal. A tilt jig at 35/50/75° (R5). A side camera. Feeler gauges.
- **Procedure.** At each tilt, drive the nose to its travel in 24 directions on paper. Photograph the ball. Measure the nozzle and sleeve clearances, the carrier and heel-pod clearances at the stop, and the refill slide.
- **Measurands.** Guaranteed ball travel; nozzle and sleeve clearance to the paper; ring lip; refill slide.

<!-- AC-TABLE:EXP-N02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N02-01 | REQ-RVJ-N01 | Guaranteed ball travel relative to the handle with the skid ring on paper, 24 directions, θ 35/50/75° (photographs of the ball); smallest value | ≥ 6.0 mm | requirement | REQ-RVJ-N01; prediction on the Rev J front end (DEC-044): 6.00 mm guaranteed (margin 0.00 mm) and 6.57 mm at 50° (PROPOSED DESIGN, CALC, results/revJ/frontend.json) | DEC-036; DEC-044; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N02-02 | — | Front end at the travel limit, θ 35/50/75°, 24 directions: nozzle clearance to the paper, ring lip wall, carrier and heel pod clearance to the nose at its stop, and refill slide within the refill force element's working range (feeler gauges, side camera) (all) | all met (nozzle ≥ 0.3 mm; lip ≥ 1.0 mm; carrier and pod ≥ 0.3 mm; slide within range) | derived | DEC-036 front-end rules (DEC-034 generalised) with the heel pod (DEC-044); prediction on the Rev J front end: margins 1.15 mm (nozzle), 1.97 mm (lip), 0.09 mm (carrier to the ring) and 0.10 mm (heel pod to the nose) over these limits; sleeve front 0.86 mm above the paper at 35°; refill slide 26.6 mm (CALC, results/revJ/layout.json fit_checks) -> tight at the carrier and the pod | DEC-036; DEC-044; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N02).
<!-- AC-TABLE:EXP-N02:END -->

- **Decision rule.** Travel short: plan autowrite with the measured reach (a plan reach of 5.0 mm still fits 2.5 mm letters at 1.0 × the line speed for every test writer; CALC). A clearance fails: re-run `nose2/frontend.py` with the measured parts.

### EXP-N03: Servo bandwidth and parasitic modes

- **Purpose and gates.** Gates REQ-RVJ-N02 and DEC-036.
- **Rig (study M).** The closed loop runs on R13 in EXP-T10, and the modes on R12 in EXP-T08 (§47; `docs/measurement_rig.md` §5.3, §6.3).
- **Predictions.** First parasitic mode 788 Hz (carrier bending), which allows a servo up to 263 Hz; 80 Hz was used in SIM (CALC). A 40 Hz servo raised the autowrite ink error from 30 to 44 µm, and the letters were still read (SIM).
- **Set-up.** The EXP-N02 nose in a clamped handle. The nose's position sensors: two linear Hall sensors (DRV5055-A4) on the main board over a magnet on the carrier (DEC-044; they replace study N's 3-D Hall). A laser vibrometer on the ball.
- **Procedure.** Swept sines from 1 to 1000 Hz, open loop (modes) and closed loop (bandwidth and phase margin), both axes, at the centre of travel and at 3 mm.
- **Measurands.** −3 dB bandwidth; phase margin; first parasitic mode.

<!-- AC-TABLE:EXP-N03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N03-01 | REQ-RVJ-N02 | Closed-loop nose bandwidth (-3 dB of ball position over reference, swept sine, 3-D Hall sensor and laser vibrometer on the ball) and first parasitic mode (open loop), both axes | ≥ 60 Hz and 240 Hz | requirement | REQ-RVJ-N02; prediction first parasitic mode 788 Hz (carrier bending), which allows a servo up to 263 Hz; 80 Hz used in SIM (CALC) | DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N03-02 | — | Phase margin of the nose servo at the tuned bandwidth, both axes | ≥ 45° | derived | pass line of the nose v2 study; the same margin as REQ-RVH-003 for the Rev H nose (DEC-036 extends DEC-032) | DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N03).
<!-- AC-TABLE:EXP-N03:END -->

- **Decision rule.** Short: stiffen the carrier or retune, and re-run the HW1 autowrite grid with the measured servo.

### EXP-N04: Heat at the autowrite duty

- **Purpose and gates.** Gates REQ-RVJ-N03 and DEC-036 (revisit above 20 K or 41 °C).
- **Rig (study M).** Runs on R13 in the 30 °C chamber as part of EXP-T15 (§47; `docs/measurement_rig.md` §6.3).
- **Predictions.** 0.182 W of coil loss while autowriting 3 mm letters with 1 mm rms tremor, and 18.2 K at 100 K/W (thermal resistance ASSUMPTION; CALC). With 2 mm tremor the coil loss is 0.38 W, about twice the design point (SIM). Rev J (DEC-044): 16.6 K at 1 mm tremor and the web over the coil plate at 45.5 °C in a 30 °C room. Rev J.1 (DEC-045), with the 0.1 mm graphite sheet in the shell wall: 8.7 K and the web at 35.9 °C in a 30 °C room; autowrite with 2 mm tremor 20.0 K and 43.7 °C (CALC, fin model). At 2 × study N's coil power the web reaches 42.3 °C at 1 mm tremor.
- **Set-up.** The nose in its handle with the graphite sheet in the wall (DEC-045), in a 30 °C room (REQ-RVJ-N03), and at 23 °C for comparison. Thermocouples on the coil and on the shell at the web over the coil plate; coil-resistance thermometry; an IR camera (R4 instruments).
- **Procedure.**
  1. Drive the coils for 30 min with the recorded HW1 force histories of the test grid (1 mm tremor).
  2. From cold, drive them with the 2 mm histories until the coil reaches 20 K. This gives the thermal time constant for the firmware's duty limit.
- **Measurands.** Coil rise; web surface temperature; coil loss at the duty; thermal time constant.

<!-- AC-TABLE:EXP-N04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N04-01 | REQ-RVJ-N03 | Coil temperature rise (thermocouple and coil resistance) and skin-side surface temperature at the web over the coil plate after 30 min of the recorded HW1 force histories (autowrite, 1 mm tremor) in the handle with the 0.1 mm graphite sheet in its wall (DEC-045), in a 30 °C room; guarded acceptance | ≤ 20 K and 43 °C | requirement | REQ-RVJ-N03 (DEC-045: held surfaces ≤ 43 °C absolute in a rated 30 °C room, 41 °C design target; was 41 °C, DEC-044); prediction coil rise 8.7 K and web 35.9 °C with the sheet (CALC, fin model, results/revJ1/budgets.json); 42.3 °C at 2 x study N's coil power; limits LIT AMF-35 (ECMA-287) and AMF-34 (IEC 60601-1) | DEC-036 (revisit above 20 K or 41 °C); DEC-045; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-N04).
<!-- AC-TABLE:EXP-N04:END -->

- **Decision rule.** Above 20 K or 43 °C: fail (REQ-RVJ-N03). Above 41 °C, the design target: revisit DEC-036 (a duty limit, or the coarse–fine C3, which halves the coil loss in the model). A coil loss well above study N's model: revisit DEC-045's battery and heat targets. Safety-related: guarded acceptance (§0.5). The 2 mm time constant sets how long a text may run with severe tremor.

### EXP-N05: Pen lift

- **Purpose and gates.** Gates REQ-RVJ-N04, the pen lift of DEC-036 and DEC-041 item 3 (a free refill joins strokes).
- **Rig (study M).** Step 4 runs on R13 in EXP-T11 (§47; `docs/measurement_rig.md` §6.3); the module's life test stays here.
- **Predictions.**
  - 0.5 mm lift; 5 ms switching (8 ms from command to contact in SIM); 17 mJ per cycle; 0.07 W while autowriting at 4.2 lifts per second; no holding power (CALC; brake and latch values ASSUMPTION).
  - A free refill follows 2.9 mm of pen lift at 50° and 6.5 mm at 70° (CALC). In normal writing the brake locks the refill when the slide sensor sees it follow a lift (about 6 mJ per stroke, ASSUMPTION).
- **Set-up.** The pen-lift module (drum with spiral spring, tendon loop, electro-permanent brake, bistable latch) on the nose. A high-speed camera on the ball. A current probe (R7). The EXP-N02 tilt jig and a writing robot for ordinary pen lifts.
- **Procedure.**
  1. Lift and lower on command; measure the height and the times.
  2. Measure the holding current in each state.
  3. Cycle at 4 lifts per second for 1e6 cycles and project the life.
  4. With the stabiliser on, the robot writes and lifts the pen 1.5 mm between strokes at 50/60/70°.
- **Measurands.** Lift height; switching time; energy per cycle; holding power; cycles to failure; joined strokes.

<!-- AC-TABLE:EXP-N05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N05-01 | REQ-RVJ-N04 | Pen-lift module: ball lift off the paper and time from command to lift and to contact (high-speed video), holding power in either state, and life projected from 1e6 cycles at 4 lifts/s (all) | all met (≥ 0.3 mm; ≤ 8 ms; 0 W holding; ≥ 1e7 cycles) | requirement | REQ-RVJ-N04; prediction 0.5 mm lift, 5 ms switching, 8 ms command to contact in SIM, no holding power (CALC on ASSUMPTION brake and latch values; docs/nose_v2.md s6) | DEC-036 (pen lift); DEC-050: the C1S nose is a bench research module, not in Rev K; Rev K's pen lift is AC-K23-01 (DEC-064) |
| AC-N05-02 | — | Energy per lift cycle (lift, release, brake on and off; current probe) | ≤ 20 mJ | hypothesis | pass line of the nose v2 study; prediction 17 mJ per cycle, 0.07 W while autowriting at 4.2 lifts/s (CALC; brake energy ASSUMPTION) | DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N05-03 | REQ-RVJ-N04 | Ordinary pen lifts of 1.5 mm between strokes by the writing robot at θ 50/60/70° with the stabiliser on (brake locks the refill when the slide sensor sees it follow a lift): strokes joined by ink | none | derived | DEC-041 item 3; a free refill follows 2.9 mm of pen lift at 50° and 6.5 mm at 70° (CALC, docs/nose_v2.md s3); the brake alone does it (about 6 mJ per stroke, ASSUMPTION) | DEC-041 (pen lift or refill lock); DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N05).
<!-- AC-TABLE:EXP-N05:END -->

- **Decision rule.** Fail: redesign the lift. Without a lift, autowrite inks its pen-up moves (ink error 59 against 29 µm, SIM), and the pen needs a refill lock (DEC-041).

### EXP-N06: Refill force element fatigue

- **Purpose and gates.** Gates REQ-RVJ-N05, the refill drive of DEC-036, and DEC-041 item 2.
- **Predictions.** Stock constant-force springs are rated for 2 500–25 000 cycles (MFR AMF-144). Tremor stabilisation cycles the slide about 29 000 times per hour (CALC). A 0.3 N ink force raised the coil loss 2.4-fold (SIM).
- **Set-up.** R8 fatigue stations with a 0–10 N load cell. Four candidates: the stock constant-force spring (AMF-144), the drum's spiral spring, a long helical spring and a magnetic spring. The drum's spring in its DEC-044 form (38 µm × 2.6 × 139 mm) is cycled in EXP-J06; its results count here too.
- **Procedure.** Force against slide over 26.6 mm (27.4 mm of tendon travel in the Rev J drum, DEC-044). Cycle at ±1 mm, 8 Hz and at ±5 mm, 3 Hz. Re-measure the force at every decade of cycles.
- **Measurands.** Force against slide; cycles to failure.

<!-- AC-TABLE:EXP-N06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N06-01 | REQ-RVJ-N05 | Chosen refill force element (the Rev J drum's spiral spring, DEC-044): ink force along the refill over the whole refill slide (26.6 mm; 27.4 mm of tendon travel), and cycles without failure at ±1 mm, 8 Hz and at ±5 mm, 3 Hz (both) | both met (0.15 N ± 20 %, never above 0.2 N; no failure within 1e8 small cycles) | requirement | REQ-RVJ-N05; prediction 0.12-0.18 N along the refill and a Goodman safety factor of 1.73 at 1e8 small cycles (CALC, DEC-044); 1e8 small cycles is about 3 years of 8 h days with tremor (docs/nose_v2.md s10); a 0.3 N ink force raised the coil loss 2.4-fold (SIM) | DEC-036 (refill drive); DEC-041 item 2; DEC-044; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-N06-02 | — | Stock constant-force spring (MFR AMF-144, the Rev H type) cycled at ±1 mm, 8 Hz: cycles to failure | ≥ 1e8 cycles | hypothesis | DEC-041 item 2 (revisit if a stock spring passes EXP-N06); rated 2 500-25 000 full-stroke cycles (MFR AMF-144) while tremor stabilisation cycles the slide about 29 000 times per hour (CALC) -> predicted to FAIL | DEC-041; Rev H refill spring (DEC-034) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N06).
<!-- AC-TABLE:EXP-N06:END -->

- **Decision rule.** Use the first candidate that passes. If the stock spring fails (as predicted), Rev H needs the fatigue-rated element too (DEC-041).

### EXP-N07: Page sensor under the pen

- **Purpose and gates.** Gates REQ-RVJ-N06, DEC-036, and the slip detection of DEC-037.
- **Rig (study M).** The sensor runs on R10 in EXP-T04, and in the pen on R13 in EXP-T14 (§47; `docs/measurement_rig.md` §3.5, §6.3).
- **Predictions.** The SIM assumed 1 kHz, 2 ms and 3 µm of noise (fusion study model, ASSUMPTION). With a 120 Hz, 10 ms sensor autowrite still read every word, but the ink error rose from 30 to 72 µm (SIM). A PMW3360-class sensor reports at up to 12 000 frames/s with its lens 2.4 mm above the surface (MFR OPT-54). DEC-045's PMW3610-class die draws 1.3–1.9 mW; its frame rate and accuracy on paper are not stated (MFR OPT-61). In its Rev J place the lens stays in its 2.2–2.6 mm band only within about ±1.5° of roll (1.59–4.11 mm at ±20°; CALC, DEC-044).
- **Set-up.** The page sensor in its Rev J place (DEC-044): folded optics beside the heel wheel, the window 24° round from the bottom, a PMW3610-class die (DEC-045; EXP-J10 checks it first) or, for autowrite if EXP-J10 fails, a PMW3360-class die. The pen swept by a motion stage (R5) with 1 mm tremor added; ground truth from the stage encoders. Lined, grid and glossy paper. Tilts 35–75° and pen roll up to ±20°. EXP-J04 measures the sensor's height band first.
- **Procedure.** Sweeps at 5–30 mm/s with tremor at 4–12 Hz, on each paper and tilt. Latency by cross-correlation with the encoders.
- **Measurands.** Position error (µm rms); report rate; latency; drop-outs.

<!-- AC-TABLE:EXP-N07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N07-01 | REQ-RVJ-N06 | Page sensor in its Rev J place (folded optics beside the heel wheel, DEC-044) against the motion-stage encoders, 1 mm tremor added, θ 35-75° and pen roll up to ±20°, lined, grid and glossy paper: report rate, latency (cross-correlation), position error and drop-outs (all) | all met (≥ 1 kHz; ≤ 2 ms; ≤ 10 µm RMS; no drop-out) | requirement | REQ-RVJ-N06 (roll ±20° added by DEC-044); SIM assumed 1 kHz, 2 ms, 3 µm noise (fusion study model, ASSUMPTION); with 120 Hz and 10 ms the autowrite ink error rose from 30 to 72 µm (SIM); the lens stays in its 2.2-2.6 mm band (MFR OPT-54) only within about ±1.5° of roll (CALC) -> predicted to FAIL at larger roll; DEC-045 fits a PMW3610-class die (MFR OPT-61), whose rate and accuracy on paper EXP-J10 measures first | DEC-036 (revisit if no 1 kHz page position); DEC-037 (slip detection); DEC-044 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-N07).
<!-- AC-TABLE:EXP-N07:END -->

- **Decision rule.** No 1 kHz position within 2 ms and 10 µm: revisit DEC-036 (autowrite with a slower sensor still reads the words, with twice the ink error) and the slip detector of DEC-037.

### EXP-N08: Autowrite on the bench

- **Purpose and gates.** Gates REQ-RVJ-N08 (the SIM gate on the firmware), DEC-039, and the go-ahead for EXP-N09.
- **DEC-049 and DEC-056 (2026-09-29).** Autowrite now writes accepted text (typed, dictated or an accepted suggestion) at up to 3 mm of tremor, through the plan of REQ-CTRL-014, and the app labels it pen-written. The SIM gate gains DEC-049's 3 mm run in sim2 (AC-N08-03), and the bench adds 3 mm of tremor. EXP-S19 (§49) tests the accepted-word plan on this set-up, in the same sessions.
- **DEC-050 (2026-09-30).** Autowrite is a research mode on the bench with the C1S nose, because it needs about ±4–6 mm of reach and the product's B1 nib has ±1.0 mm. This experiment tests the research mode; it gates no Rev K claim.
- **Rig (study M).** Runs on R13 after EXP-T13 (§47; `docs/measurement_rig.md` §6.5).
- **Predictions (SIM).** Ink error 29 µm without tremor, 36 µm with 1 mm and 60 µm with 2 mm. Letters read 99.2 % (98.3 % at 2 mm) against a 100 % ceiling. 3.7 letters per second at a 9.5 mm/s sweep. Total power 0.24 W without tremor and 0.31 W with 1 mm. One test writer needed a slower sweep for its line (post hoc); DEC-039 lets the pen set the sweep speed per line. In sim2 at 3 mm peak at the hand (DEC-049): letters read 82 / 88 % and ink 67 / 83 µm at 5 / 8 Hz; the nose used 6.55 of its 6.57 mm.
- **Set-up.** The pen on a motion stage that sweeps at the planner's speed (R2). Tremor from a shaker (0.3/1/2 mm at 4/8/12 Hz, and 3 mm at 5 and 8 Hz for DEC-049). The text of the HW1 test set, and accepted words for EXP-S19. R3 scans; the app's recogniser and reader; coil power logging.
- **Procedure.**
  1. Run the SIM gate on the firmware under test.
  2. Write the test sentence at 2.5 and 3 mm x-height under each tremor condition, in random order.
  3. Scan and score blind.
- **Measurands.** Ink error to the target; letters and words read; coverage, missing strokes and completion time (REQ-WP-011); coil power.

<!-- AC-TABLE:EXP-N08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N08-01 | REQ-RVJ-N08 | SIM gate on the firmware under test before each bench session: HW1 test set (writers 0-5, seeds 200-203), 2.5 mm letters, ≤ 1 mm tremor: mean letters read, mean ink error, and every writer's line planned (all) | all met (≥ ceiling - 2 points; ≤ 45 µm RMS; every line planned) | requirement | REQ-RVJ-N08; SIM 99.2 % against a 100 % ceiling, 29-36 µm; writer 4 had no plan at the frozen 1.25 x sweep (12 of 72 cases per tremor amplitude) and passes only with the per-line sweep speed of DEC-039 (post hoc; results/nose2/nose2.json) | DEC-039; firmware for EXP-N08 and EXP-N09; DEC-050: autowrite is a bench research mode with the C1S nose |
| AC-N08-02 | — | Autowrite on the motion stage with shaker tremor (0.3/1/2 mm at 4/8/12 Hz), text of the HW1 test set, 2.5 and 3 mm letters: ink error to the target relative to the SIM value at the same conditions, and letters read by the app's recogniser against the clean-target ceiling (both) | both met (≤ 1.5 x SIM; ≥ ceiling - 5 points) | hypothesis | pass line of the nose v2 study; SIM 29 / 36 / 60 µm at 0 / 1 / 2 mm tremor (2.5 mm letters), letters 98.3-99.2 % against a 100 % ceiling (docs/nose_v2.md s5.3) | DEC-039; DEC-036; DEC-050: autowrite is a bench research mode with the C1S nose |
| AC-N08-03 | REQ-RVJ-N08 | SIM gate (b) on the firmware under test, for DEC-049's range: sim2, test writers 0-5, 3 mm peak tremor at the hand at 5 and 8 Hz, 2.5 mm letters, accepted text written through the plan of REQ-CTRL-014: mean letters read at each frequency, and letters left half-written (both); reported with the measured-error page model beside the ideal one | both met (no more than 2 points below DEC-049's result: 82 % at 5 Hz, 88 % at 8 Hz; no half letter) | requirement | REQ-RVJ-N08 (b) (DEC-049; DEC-056 (f)); DEC-049's result with nose2's planner and a known text: letters 82 / 88 %, words (after autocorrect) 80 / 97 %, ink 67 / 83 µm, the nose at 6.55 of its 6.57 mm (SIM, results/sim2j/autowrite.json); not yet run with the plan of REQ-CTRL-014 (study S, T9: 0-8 half letters per 100 completions, kinematics only) | DEC-049 (autowrite up to 3 mm); firmware for EXP-N08, N09 and S19; DEC-050: autowrite is a bench research mode with the C1S nose |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N08).
<!-- AC-TABLE:EXP-N08:END -->

- **Decision rule.** SIM gate fails: no bench or participant session with that firmware. Bench lines fail: identify the pen (EXP-V02) and retune in the calibrated simulator.

---

## 44. Simulator v2 validation: EXP-V01…V07

### Purpose and what it gates

DEC-040 makes sim2 (MuJoCo) the Rev J reference simulator, with H1 as the regression check. Until EXP-V01, V02 and V04 calibrate it and EXP-V05 validates it, sim2's results rank concepts (context of use COU-1) and are not evidence of benefit (REQ-SIM-005).
- **Order** (`docs/sim_v2.md` §8.4, as the s2r protocol): actuator coupons (EXP-B03) → nose frequency response (EXP-B05 methods, EXP-V02) → friction (EXP-B01/B02, V01) → hand (V04) → writers and tremor (V03) → freeze → EXP-V05 → EXP-V06 with human data.
- **Identification.** Stochastic grey-box models with the same equations as sim2. Maximum likelihood with an extended Kalman filter over several recordings; parameters with 95 % intervals; residual checks (s2r `modelform.py`). The domain-randomisation (DR) ranges then narrow to the identified intervals. Parameters are frozen before EXP-V05 and never refitted on validation data.
- **What it gates.** DEC-040 is revisited if EXP-V05 fails its pass lines, or if a device result depends on the contact law beyond the stated tolerance. Requirements: REQ-SIM-001…005 (checked on the frozen model in EXP-V05) and REQ-RVH-008 (EXP-V02 part B).
- **Predictions (SIM, `results/sim2/`).** sim2 reproduces H1 on 56 Rev H cases: unmodified ink error within 3.1 %, oracle ratio within ±0.03 in 52 of 56. A 25 µs step is converged (0.22 µm against 12.5 µs). Energy residual ≤ 6.8 × 10⁻⁴. All of this is model to model; no bench or human data exist.
- EXP-V03 runs inside EXP-H01 sessions, and EXP-V04 and EXP-V07 with participants; all are covered by the same ethics approval. EXP-V06 is an offline analysis of human-study data.

### EXP-V01: Paper contact of the Rev H front end

- **Purpose and gates.** Calibrate and validate the contact law. Gates DEC-040: H1's law for ink metrics, native contacts only for geometry-rich plug-ins.
- **Rig (study M).** Runs on R9 in EXP-T01, with the Rev H lip as one more head (§47; `docs/measurement_rig.md` §2.8).
- **Predictions.** The parameters are ASSUMPTIONS today: ball and skid friction 0.15 and 0.12, static/kinetic ratio 1.3, Stribeck speed 2 mm/s, pre-sliding 10 µm, normal stiffness 10⁵ N/m. The H1 law matches its closed forms within 0.5 %. Stiff native contacts chatter while sliding (normal-force std/mean 2.6–3.0); the sim2 default gives 0.24–0.30 (SIM).
- **Set-up.** R1 sled or tribometer with the Rev H lip and ball on 80 g/m² paper; high-rate force (≥ 2 kHz) and displacement (laser Doppler vibrometer).
- **Procedure.** Normal indentation; friction against speed from 0.1 to 50 mm/s; velocity reversals; drags at 35/50/75° with 0.5–2 N; the rubber heel element. Share the runs with EXP-B02 and EXP-Q01 where the rigs overlap.
- **Measurands.** Static and kinetic friction, Stribeck speed, pre-sliding distance, normal stiffness; normal-force variation while sliding; rubber friction.

<!-- AC-TABLE:EXP-V01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V01-01 | — | sim2's H1 contact law with the identified parameters against the sled measurement with the Rev H lip and ball on 80 g/m2 paper: friction force against speed over 0.5-50 mm/s, and pre-sliding displacement (both) | both met (±10 % RMS; ±30 %) | hypothesis | pass line of study V; parameters now ASSUMPTION (ball and skid friction 0.15 and 0.12, static/kinetic ratio 1.3, Stribeck speed 2 mm/s, pre-sliding 10 µm; docs/sim_v2.md s8.3); the H1 law matches its closed forms within 0.5 % (SIM) | DEC-040 (H1's law for ink metrics) |
| AC-V01-02 | — | Native MuJoCo contact setting: sliding chatter index (std / mean of the normal force while sliding at θ 35/50/75°) relative to the measured one | ≤ 2 | hypothesis | pass line of study V (native contacts accepted only within 2 x the measured chatter); SIM: stiff setting 2.6-3.0, sim2 default 0.24-0.30 (docs/sim_v2.md s5.2) | DEC-040 (native contacts only for geometry-rich plug-ins) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-V01).
<!-- AC-TABLE:EXP-V01:END -->

- **Decision rule.** Fail: extend the contact model (for example a physically parameterised compliant contact, LIT CON-56) before randomising. Native contacts fail their chatter check: they stay limited to geometry-rich plug-ins and are cross-checked with H1's law.

### EXP-V02: Identify the assembled pen

- **Purpose and gates.** Identify the nose, refill, sensors and masses of the assembled pen, and check the refill's front stop. Gates DEC-040 and REQ-RVH-008 (DEC-041 item 4).
- **Predictions.**
  - Nose parameters now come from the Rev H design: K_f 0.74 N/A, R 2.47 Ω, L 100 µH, 100 K/W, flexure 0.025 N m/rad with damping ratio 0.02, Hall delay 50 µs (ASSUMPTION or CALC).
  - Refill 0.15 N with no slide friction; front stop 0.3 mm beyond contact, following the nose.
  - A fixed 0.3 mm stop kept the ball on the paper only 63–73 % of pen-down time under correction. A stop that follows the nose kept 0.908–1.000; a fixed stop at 3.2 mm 0.984–1.000 (SIM). A fixed stop needs the usable travel × cot θ_min + 0.3 mm: 2.8 mm at 50° and 4.6 mm at 35° for 3.0 mm of usable travel (CALC).
- **Set-up.** The Rev H pen (the EXP-I05 build), clamped. Current steps and chirps to each coil; Hall sensor and laser vibrometer at the ball. A force–displacement rig for the refill (part B). A balance and a bifilar pendulum. The IMU at rest and on a rate table; the page sensor on a motion stage.
- **Procedure.**
  - **Part A:** masses and inertias; coil K_f, R, L and thermal values; flexure stiffness and damping; frequency response 1–200 Hz; Hall delay; sensor noise and latency.
  - **Part B:** refill force against slide; slide friction; the front stop's position against the nose deflection, with the nose at its usable travel in 8 directions at 35/50/75°.
- **Measurands.** The parameters with 95 % intervals; frequency response, step responses and noise densities against sim2 with the identified values; front-stop extension.

<!-- AC-TABLE:EXP-V02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V02-01 | — | sim2 with the identified parameters against the assembled Rev H pen (handle clamped): nose FRF over 1-200 Hz, step responses, and sensor noise densities (all) | all met (±1 dB and ±10°; ±10 % RMS; ±20 %) | hypothesis | pass line of study V; nose parameters now from the Rev H design (K_f 0.74 N/A, R 2.47 ohm, L 100 µH, 100 K/W, flexure 0.025 N m/rad, zeta 0.02, Hall delay 50 µs; ASSUMPTION or CALC, docs/sim_v2.md s8.3) | DEC-040 |
| AC-V02-02 | REQ-RVH-008 | Refill front stop of the assembled pen (part B), nose at its usable travel in 8 directions, θ 35/50/75°: the stop follows the nose deflection, or the spare extension beyond contact is at least the usable travel x cot(θ_min) + 0.3 mm | conforms | requirement | REQ-RVH-008; DEC-041 item 4; fixed margin needed 4.6 mm at 35° and 2.8 mm at 50° for 3.0 mm usable travel (CALC); a fixed 0.3 mm stop kept the ball on the paper only 63-73 % of pen-down time under correction (SIM, docs/sim_v2.md s5.8) | DEC-041; DEC-034 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-V02).
<!-- AC-TABLE:EXP-V02:END -->

- **Decision rule.** Model fails: extend the actuator model (for example a learned actuator model, LIT OPT-58) before randomising. Front stop fails REQ-RVH-008: redesign the stop. A fixed long stop also needs the pen lift or a refill lock, or the refill joins strokes (DEC-041 item 3).

### EXP-V03: Real writing and tremor at the pen (inside EXP-H01)

- **Purpose and gates.** Record the inputs of sim2's writer and tremor models. Gates DEC-040 (refit the synthetic writers) and every causal-tracker result.
- **Rig (study M).** Its inputs come from R11's recordings, qualified in EXP-T06 (§47; `docs/measurement_rig.md` §4).
- **Predictions.** The synthetic writers differ from measured writing. The sigma-lognormal writer is about half as fast as adults writing a phrase (14.5 against 30.5 mm/s, LIT CON-20). The glyph writer has about ten times the measured 8–12 Hz velocity content (14 % against 1.3–1.7 %, LIT CON-25) (SIM).
- **Set-up.** EXP-H01 sessions: the instrumented passive pen (IMU, page sensor, force) plus a wrist IMU. ET, PD and controls.
- **Procedure.** Standard sentence, loops and spirals. Fit tremor spectra per writer and sigma-lognormal strokes (LIT CON-60, CON-61). Compare with sim2's models under DR.
- **Measurands.** Tremor peak frequency, amplitude and bandwidth at the pen and the wrist; writing speed, stroke durations, velocity spectrum, power-law exponent; writing force.

<!-- AC-TABLE:EXP-V03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V03-01 | — | Recorded writers (ET, PD, controls; inside EXP-H01 sessions) covered by sim2's tremor and writer models with domain randomisation (value inside the simulated 5-95 % range), for every measurand: tremor peak frequency, amplitude and bandwidth at pen and wrist; writing speed, stroke durations, velocity spectrum, power-law exponent; writing force | ≥ 90 % | hypothesis | pass line of study V; the sigma-lognormal writer is about half as fast as adults writing a phrase (14.5 against 30.5 mm/s, LIT CON-20) and the glyph writer has about ten times the measured 8-12 Hz velocity content (14 % against 1.3-1.7 %, LIT CON-25) (docs/sim_v2.md s6) -> predicted to FAIL before the writer refit DEC-040 requires | DEC-040 (refit the synthetic writers); causal-tracker results |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-V03).
<!-- AC-TABLE:EXP-V03:END -->

- **Decision rule.** Fail (as expected before the refit): refit the writers to the recordings and repeat the check before any causal-tracker number is trusted.

### EXP-V04: Pen-grasp impedance while writing

- **Purpose and gates.** Identify the grasp impedance that sim2's hand models must reproduce. Gates DEC-040 and the grip split used by every Rev J study.
- **Predictions (SIM).** The fitted arm matches H1's tip impedance to 0.227 rms relative error, with two stiffness multipliers at their bound. MyoArm's pen-point impedance at 8 Hz is 1.1–5.6 × HAP-26. The grip split is an ASSUMPTION.
- **Set-up.** R6 with a stinger, or the pen's own nose or reaction mass as the exciter. A small random force of 0.5–30 Hz, ≤ 0.2 N. Forearm on the desk. Share sessions with EXP-I01 and EXP-B06 where possible.
- **Procedure.** Participants hold a writing posture at 2–3 instructed levels of co-contraction; excitation in 3 axes.
- **Measurands.** Tip-referred compliance in 3 axes; grip split r_rot; roll stiffness.

<!-- AC-TABLE:EXP-V04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V04-01 | — | sim2's H1 hand (and the fitted arm) against each participant's tip-referred compliance over 1-20 Hz in 3 axes at 2-3 co-contraction levels: magnitude and phase error, and the share of participants inside the DR ranges (all) | all met (±20 %; ±15°; ≥ 90 % of participants) | hypothesis | pass line of study V; the fitted arm matches H1's tip impedance to 0.227 RMS relative error with two stiffness multipliers at their bound; MyoArm impedance 1.1-5.6 x HAP-26 at 8 Hz (SIM); grip split ASSUMPTION | DEC-040; grip split of the Rev J studies |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-V04).
<!-- AC-TABLE:EXP-V04:END -->

- **Decision rule.** Fail: refit the arm's masses and stiffnesses to the measured impedance, and widen the DR ranges to cover the participants.

### EXP-V05: Validate the device effect on a bench

- **Purpose and gates.** The validation step of DEC-040. Gates any use of sim2 beyond ranking (REQ-SIM-005).
- **Rig (study M).** The bench part runs on R13 after EXP-T13, with the predictions frozen first (§0.2). See §47 and `docs/measurement_rig.md` §6.5.
- **Predictions.** None from hardware. In the model-to-model check sim2 reproduced H1's oracle ratio within ±0.03 in 52 of 56 cases. The Rev H tracker's frequency lock makes single-seed causal comparisons unstable, so each condition uses at least 5 tracker-noise seeds (SIM).
- **Set-up.** The EXP-G05 hand simulant or a robot-held pen (R2) with injected tremor at 4–12 Hz and 0.3–2 mm; ink metrology as EXP-B09 (R3); frozen firmware; sim2 frozen with the identified parameters.
- **Procedure.**
  1. Check the frozen sim2 against REQ-SIM-001…005 and record its version.
  2. Predict every condition with the same disturbance before the bench runs, and freeze the predictions (§0.2).
  3. Run the bench with the known disturbance and with the causal tracker.
  4. Compare. Do not refit on these data.
- **Measurands.** Measured and predicted ink-error ratios (known disturbance, causal); rank order across conditions.

<!-- AC-TABLE:EXP-V05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V05-01 | — | Frozen sim2 (identified parameters, same disturbance, predictions made before the bench runs) against bench ink-error ratios (hand simulant or robot-held pen, injected tremor 4-12 Hz, 0.3-2 mm, ink metrology, frozen firmware, ≥ 5 tracker-noise seeds): share of conditions within ±0.03 (known disturbance) and within ±0.05 (causal tracker) | ≥ 80 % | hypothesis | pass line of study V and DEC-040 revisit trigger; model-to-model only so far: sim2 reproduced H1 within ±0.03 in 52 of 56 cases, and the Rev H tracker's frequency lock makes single-seed causal ratios bistable (SIM, docs/sim_v2.md s5.1) | DEC-040 (sim2 beyond ranking, COU-2) |
| AC-V05-02 | — | Spearman rank correlation between predicted and measured ink-error ratios across the EXP-V05 conditions | ≥ 0.9 | hypothesis | pass line of study V | DEC-040 |
| AC-V05-03 | REQ-SIM-001 | Check of the frozen sim2 before the comparison: H1 regression on H1's test grid, unmodified ink error within ±10 % and oracle ratio within ±0.03 in ≥ 90 % of cases (both) | both met | requirement | REQ-SIM-001; SIM: unmodified within 3.1 %, oracle within ±0.03 in 52 of 56 cases (93 %) (results/sim2/verification.json) | DEC-040 |
| AC-V05-04 | REQ-SIM-002 | Check of the frozen sim2: ink-path difference between the production step and half the step, and energy residual (both) | both met (≤ 1 µm RMS; ≤ 1e-3 of the energy scale) | requirement | REQ-SIM-002; SIM 0.22 µm at 25 µs against 12.5 µs; energy residual ≤ 6.8e-4 (results/sim2/verification.json) | DEC-040 |
| AC-V05-05 | REQ-SIM-003 | Check of the frozen sim2 (code review and tests): every parameter carries a label and source (params.LABELS), identified values name their EXP-V record, and every result file carries stabpen.provenance | conforms | requirement | REQ-SIM-003 | DEC-040 |
| AC-V05-06 | REQ-SIM-004 | Check of the frozen sim2 (code review): the Gym observation holds only the pen's own sensor readings with noise, bias and delay, and every DR range cites its source | conforms | requirement | REQ-SIM-004 | DEC-040 |
| AC-V05-07 | REQ-SIM-005 | Use of sim2 results (document review): none is cited as evidence of benefit or safety, or used to train or select policies for bench or human tests, before EXP-V01, V02 and V04 calibrate sim2 and AC-V05-01 and AC-V05-02 pass | conforms | requirement | REQ-SIM-005; DEC-040 (COU-1 only until validated; docs/sim_v2.md s8.1) | DEC-040 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-V05).
<!-- AC-TABLE:EXP-V05:END -->

- **Decision rule.** Pass: sim2 may be used to train and select policies for bench and human tests (COU-2). Fail: sim2 stays at COU-1, and DEC-040 is revisited.

### EXP-V06: Population prediction against people

- **Purpose and gates.** Check sim2's population prediction against a human study. Gates any population claim made from sim2.
- **Predictions.** None yet: there are no human data.
- **Set-up.** Offline. The ink error with and without assistance from a human study (for example EXP-W02 or EXP-D09). sim2 with DR over hand and tremor.
- **Procedure.** Before unblinding, compute sim2's 80 % prediction interval for the median ratio and its predicted rank order of conditions. Then compare.
- **Measurands.** The distribution of the ratio across writers; the rank order.

<!-- AC-TABLE:EXP-V06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V06-01 | — | Measured median ink-error ratio across writers (with against without assistance, from a human study such as EXP-W02 or EXP-D09) against sim2's 80 % prediction interval (DR over hand and tremor, computed before unblinding), and the rank order of conditions (both) | both met (median inside the interval; same rank order) | hypothesis | pass line of study V; no human data yet | DEC-040 (population claims from sim2) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-V06).
<!-- AC-TABLE:EXP-V06:END -->

- **Decision rule.** Fail: no population claims from sim2; refit the DR distributions from EXP-V03 and V04.

### EXP-V07: Small handwriting on a tablet (participants)

- **Purpose and gates.** Measure the speed, stroke times and spectrum of small real handwriting, and refit sim2's v2 writers to them. Gates DEC-040's writer model and, through the detector's tuning writers, REQ-RVJ-C03.
- **Rig (study M).** Runs on R11's tablet protocol once AC-T06-04 shows a median pen report rate of at least 200 Hz, coalesced samples included. The recorder's CSV goes through `rig.tablet.load_recording` into `sim2j/writers.kinematics` (§47; `docs/measurement_rig.md` §4.2).
- **Real writing now (study R).** UNIPEN hpb2 (14 adults, a ballpoint on paper, 100 samples/s, letters about 3–6 mm, 2.4 % of the velocity energy at 8–12 Hz) can refit sim2's writers below about 12 Hz now (`realdata.library.writing("tuning", ...)`; `docs/real_data.md`). This experiment's recordings (≥ 200 Hz, small writing) are still needed above that band and for small letters.
- **Predictions (LIT, CALC).**
  - The literature's target: 1.3–1.7 % of the velocity energy at 8–12 Hz, with 50 % and 90 % of it below 3.1 and 4.9 Hz (LIT CON-25). Mean speed 30.5 mm/s (LIT CON-20); median stroke 90–150 ms (LIT CON-24).
  - CON-25 recorded large characters, about 14 mm. At 3.65 mm and 30 mm/s the v2 writers carry 10.1–12.2 % at 8–12 Hz (v1: 17.3 %), so the target may not hold for small letters (CALC, `docs/revJ_simulation.md` §3).
- **Set-up.** 12 healthy adults, with consent (covered by the ethics approval of EXP-H01). A pen tablet sampling at ≥ 200 Hz (Wacom class). The sentence "return library books by friday".
- **Procedure.** Each participant writes the sentence at their own size. Compute the 8–12 Hz share of velocity energy, the speed and the stroke times with `sim2j/writers.kinematics`. Refit the v2 writers (`sim2j/writers.py`) to the measurements.
- **Measurands.** Letter size; mean pen-down speed; median stroke time; share of velocity energy at 8–12 Hz, and the frequencies below which 50 % and 90 % of it lie.

<!-- AC-TABLE:EXP-V07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-V07-01 | — | Share of velocity energy at 8-12 Hz of pen-down writing ('return library books by friday' at the writer's own size, pen tablet ≥ 200 Hz), median over 12 healthy adults, computed with sim2j/writers.kinematics | within 1.3-1.7 % | hypothesis | LIT CON-25, recorded on large characters (about 14 mm; docs/revJ_simulation.md s3); sim2's v2 writers carry 10.1-12.2 % and v1 17.3 % (CALC), and the target may not hold for small letters; the v2 writers are refitted to the measurement either way | DEC-040 (sim2's writer model); REQ-RVJ-C03 (the detector's tuning writers) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-V07).
<!-- AC-TABLE:EXP-V07:END -->

- **Decision rule.** Share far from 1.3–1.7 %: the literature's target does not hold for small writing. Either way, the refitted writers replace v2 in sim2, and the detector's tuning (REQ-RVJ-C03) and the ET grid are re-run on them.

---

## 45. Rev J control stack: EXP-L01, L02, L04, L05

### Purpose and what it gates

DEC-042 sets the Rev J control stack.
- **Default estimator.** A causal tremor-line detector on the page sensor looks at the last 4 s every 50 ms (peak-to-floor ratio in 4.5–13.5 Hz, hysteresis 5/2.5, amplitude gate 0.15–0.35 mm; its state kept across lines). It opens a listening fixed-lag Kalman estimate at lag 0 only while a tremor line is present. Otherwise the Rev H tracker runs.
- **Successor in shadow mode.** A causal TCN (34 k parameters, int8) logs its estimate beside the default. It drives the nose only after REQ-ML-001 passes on held-out real recordings.
- **No delayed ink; RL offline only; one arbitration law.** The ink never trails the hand. RL designs the arbitration offline; no RL policy drives the nose. Every assistance uses α = α_max × c_conf × c_need × c_agree, slew-limited, with the hand-back rules.
- **What it gates.** DEC-042 is revisited if EXP-L01 or EXP-L02 fail, if EXP-L04 passes (then the TCN may take over), or if EXP-L05 passes its rules. DEC-045 is revisited if EXP-L01 shows that the detector needs the 1 kHz page-sensor stream. Requirements: REQ-CTRL-009, REQ-CTRL-010, REQ-CTRL-011, REQ-ML-003 and REQ-ML-004.
- **Predictions** come from `docs/ai_control_v2.md` and `results/ai2/ai2.json` (model HW1; test writers 0–5, seeds 200–203; rules R1–R4 fixed on tuning seeds 300–301; SIM and CALC). The learned models and RL policies were trained and tested inside one simulator family.
- **Data.** EXP-L01, L02 and L04 replay the EXP-H01 recordings (instrumented passive pen, tip camera as the reference), with the participant splits of REQ-DATA-001 and the EXP-E01 protocol.
- The studies with people (EXP-L03, L06, L07, L08) are in [`human_study_plan.md`](human_study_plan.md) §19.

### EXP-L01: Does the tremor-line gate stay shut on real tremor-free writing?

- **Purpose and gates.** Check the gate on real writing: shut on tremor-free writing, open on real tremor. Check that the stack is causal. For DEC-045, check the gate on the low-power page sensor's stream at 250 Hz, and on the IMU alone as the fallback. For DEC-047, replay the guarded tracker G4, sim2's default, beside DEC-042's gated listening tracker. Gates REQ-CTRL-009, REQ-CTRL-010, REQ-RVJ-C03, DEC-042, DEC-045 and DEC-047.
- **Predictions (SIM).**
  - The gate never opened on the tremor-free writing of any tuning or test writer. Tremor-free writing moved 26.3 µm, the same as with the Rev H tracker.
  - At 1–2 mm it was open for 51–73 % of a 20 s recording, because it needs about 4.5 s to open (4 s window + 0.5 s). Once open on tuning data, it stayed open for 95 % of the detector's updates.
  - At 0.3 mm it was open for 0.1–12.9 % of the time.
  - The detector already works on a 250 Hz grid (a Welch spectrum of the last 4 s every 50 ms). No prediction exists for the low-power die's stream or for an IMU-only gate. The IMU carries the tremor estimate: without the page sensor the listening smoother's residual was 421 µm, against 412 µm with it (SIM, study L).
  - sim2 (DEC-047; v2 writers, test writers 0–4): ai2's gated listening tracker moved tremor-free writing by 59 µm (36–85): its fallback, the Rev H tracker as built, locks onto the writing's own 8–12 Hz content. The guarded tracker G4, with a stricter detector threshold and ball-on-paper input, moved it by 0 µm.
  - Real inputs (study R, HW1; `docs/real_data.md`): the gate was open 28 % (PD) and 4 % (ET) of the time at 1 mm, against 62 % and 28 % with model tremor, and 21–42 % at the severe size (1.72 mm), because real tremor wanders about twice as much as the model. Real tremor-free writing moved 25 µm, with the gate shut 99.8 % of the time.
- **Set-up.** Offline: the EXP-H01 recordings of ET, PD and control writers. The Rev J estimator stack as firmware code, run in a replay harness. Then the bench pen with recorded hand motion.
- **Procedure.**
  1. SIM gate (REQ-RVJ-C03): run the detector build in sim2 on the tremor-free writing of the tuning writers of writer models v1 and v2; it must never open. Check that its input takes page samples only while the ball is on the paper.
  2. Test the causality of the stack build: change sensor samples after their availability time and check that no earlier command changes.
  3. Replay every recording, keeping the detector's state across lines within a session, as the firmware does, with DEC-042's gated listening tracker and with G4 (DEC-047).
  4. Log the gate, the detector's ratio and amplitude, and the commanded correction.
  5. Replay again with the detector on the low-power die's stream at 250 Hz (recorded with the die where available, otherwise the 1 kHz stream reduced to 250 Hz and to the die's 7.9 µm counts), and a third time on the IMU alone (DEC-045).
  6. Repeat on the bench pen.
- **Measurands.** Gate-open share of tremor-free writing time per writer; time to open after tremor onset; open share at 1–2 mm after the first 5 s; tremor-free writing moved (the commanded correction on the controls' writing), judged against the absolute 25 µm bound on these real recordings (`README.md` §2), with the difference to the Rev H tracker alone reported. For DEC-045: the agreement of the 250 Hz and IMU-only gates with the 1 kHz gate per 50 ms decision, and their openings on tremor-free writing.

<!-- AC-TABLE:EXP-L01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L01-01 | REQ-CTRL-010 | Gate-open share of tremor-free writing time for every control writer (EXP-H01 recordings replayed offline through the Rev J estimator stack, detector state kept across lines; tip camera as reference) | ≤ 1 % | requirement | REQ-CTRL-010 (closed ≥ 99 %); SIM: never open on the tremor-free writing of any tuning or test writer (results/ai2/ai2.json) | DEC-042 (revisit if the gate fails on real writing) |
| AC-L01-02 | REQ-CTRL-010 | Tremor-free writing moved by the gated stack on the controls' real recordings (commanded correction, every control writer, RMS); the difference to the Rev H tracker alone is reported | ≤ 25 µm | derived | false-correction convention (validation/README.md s2): on real recordings the absolute bound of AC-E01-09 applies; REQ-CTRL-010's relative bound (Rev H + 2 µm) is for simulation on synthetic writers, which carry about ten times the measured 8-12 Hz content (DEC-040); SIM 26.3 µm with both trackers on synthetic writers; in sim2 false correction is measured against the device-off pen with the same noise (REQ-RVJ-C02): ai2's gated listening tracker moved tremor-free v2 writing by 59 µm (36-85) and the guarded tracker G4 by 0 µm (SIM, test writers 0-4, DEC-047) | DEC-042; DEC-047 |
| AC-L01-03 | — | Gate-open share of pen-down time after the first 5 s of writing, writers with 1-2 mm tremor at the tip | ≥ 80 % | hypothesis | pass line of study L; SIM: open for 51-73 % of a whole 20 s recording because the detector needs about 4.5 s to open, and for 95 % of its updates at 1-2 mm once open on tuning data (docs/ai_control_v2.md s3.4, s4.1); with real tremor (study R, HW1 with real inputs, whole notes) the gate was open 28 % (PD) and 4 % (ET) of the time at 1 mm, against 62 % and 28 % with model tremor, and 21-42 % at the severe size, because real tremor wanders (docs/real_data.md) -> predicted to FAIL on real tremor until the detector is re-tuned on real data | DEC-042 |
| AC-L01-04 | REQ-CTRL-009 | Causality test of the estimator stack used in the replay (firmware build): changing any sensor sample after its availability time (acquisition + latency) changes no earlier nose command, and every estimator output at a tick uses only samples available at that tick | conforms (bit-exact) | requirement | REQ-CTRL-009; study L found and fixed two look-ahead leaks before its test (docs/ai_control_v2.md s13 item 3); unit tests in ai2/tests | DEC-042 |
| AC-L01-05 | — | Tremor-line gate computed on the low-power page sensor's stream at 250 Hz (DEC-045) against the gate on the 1 kHz page-sensor stream, per 50 ms decision on the EXP-H01 recordings (all writers), and its openings on the controls' tremor-free writing (both) | both met (≥ 95 % of decisions agree; never open on tremor-free writing) | hypothesis | pass line of the Rev J.1 study (docs/revJ1_design.md s4.2); the detector already works on a 250 Hz grid (DEC-042); no prediction for the low-power die's stream (EXP-J10) | DEC-045 (revisit if the detector needs the 1 kHz stream) |
| AC-L01-06 | — | IMU-only tremor-line detector (the fallback pre-detector for a gated PMW3360-class die): tremor lines found by the 1 kHz page-sensor gate that it misses, and its openings on the controls' tremor-free writing (both) | both met (no line missed; never open on tremor-free writing) | hypothesis | pass line of the Rev J.1 study, needed only if EXP-J10 shows the low-power die cannot serve the detector; the IMU carries the tremor estimate (listening-smoother residual 421 µm without the page sensor against 412 µm with it; SIM, study L); no prediction for an IMU-only gate | DEC-045 (fallback: a PMW3360-class die gated by an IMU pre-detector) |
| AC-L01-07 | REQ-RVJ-C03 | SIM gate on the detector build under test, before the replays: the tremor-line detector run in sim2 on the tremor-free writing of the tuning writers of every writer model in use (v1 and v2), and a firmware review that its input takes page samples only while the ball is on the paper (both) | both met (never opens; conforms) | requirement | REQ-RVJ-C03 (DEC-047); G4's stricter threshold (open above a peak ratio of 8, close below 4) with ball-on-paper input stayed shut on every tuning and test writer (SIM, results/sim2j/rules.json); ai2's threshold (5) is reached on the intended paths of v2 writers (peak ratios 4-6) and of one v1 writer (14) (CALC) | DEC-047; DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-L01).
<!-- AC-TABLE:EXP-L01:END -->

- **Decision rule.** The gate opens on real tremor-free writing: revisit DEC-042 (re-tune the thresholds on training participants only, or keep the Rev H tracker). It opens too little on real tremor: re-tune the detector; the 20 s calibration can arm its band. The 250 Hz gate disagrees with the 1 kHz gate: revisit DEC-045 (a PMW3360-class die, gated by the IMU-only detector if that one misses no line). The SIM gate fails: that detector build is not replayed (REQ-RVJ-C03). The two trackers differ on real recordings: revisit DEC-042 and DEC-047 with the result.

### EXP-L02: Does the gated tracker beat the Rev H tracker on real writing?

- **Purpose and gates.** Compare the default with the Rev H tracker, offline on real writing and in closed loop on the bench, with G4, sim2's default (DEC-047), as a third arm. Check the nose command's band limit, and keep any controller that fails the sim2 false-correction gate off the bench. Gates REQ-CTRL-011, REQ-RVJ-C01, REQ-RVJ-C02, DEC-042, DEC-047 and DEC-048.
- **Predictions (SIM).** At 1–2 mm and 6–10 Hz: 430 against 627 µm (0.69; paired −197 µm, 95 % CI −206 to −188). At 6 Hz, where the Rev H tracker does nothing: 818 → 540 µm. Letters read 64 → 78 %, words 49 → 74 %. 0.3 mm tremor unchanged (161 against 162 µm).
- **Predictions (sim2, DEC-047; v2 writers, test writers 0–4).** G4: 0.63 of the device-off ink error at 8–12 Hz × 1–2 mm (0.59–0.68), 1.02 at 0.3 mm, 0 µm on tremor-free writing. ai2's gated listening tracker: 0.67, 1.14 and 59 µm. The heel wheel in its tremor mode moved tremor-free writing by 0.40 mm (DEC-048). Without the 64 Hz output filter the listening prediction made the ink 1.6 × worse than the device-off pen (SIM).
- **Predictions (real inputs, study R; SIM).** At the severe class (1.72 mm) the gated tracker left 0.96 × and the Rev H tracker 1.06 × the ordinary pen's tip tremor, and both read 0.4 of 10 words; at 1 mm, 1.03–1.04 × against 1.08 ×. The Rev H tracker made the tip tremor larger than an ordinary pen's in 56 % of the severe notes (`docs/real_data.md`). EXP-R02 scores the same replays as results cards.
- **Set-up.** Offline: the EXP-H01 recordings, paired per writer, with the tip camera as the intended path. Bench: the Rev J pen in closed loop on the EXP-I05 tremor rig (R2 with a 2-axis shaker) with recorded hand paths; R3 scans.
- **Procedure.**
  1. Before the bench: the SIM gate on the firmware under test (every controller in it moves tremor-free writing by ≤ 25 µm against the device-off pen in sim2, REQ-RVJ-C02), and a review of the nose command's band limit (REQ-RVJ-C01).
  2. Replay the recordings through the trackers: the gated listening tracker, G4 and the Rev H tracker. Score the ink error against the tip-camera intent, the letters read by the app, and the false correction on the controls' writing.
  3. Bench: 0.3, 1 and 2 mm at 6, 8 and 10 Hz, each tracker, 10 seeds each, in random order.
- **Measurands.** Ink error; letters and words read; false correction; paired differences per writer.

<!-- AC-TABLE:EXP-L02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L02-01 | REQ-CTRL-011 | Ink error against the tip-camera intent with the gated tracker relative to the Rev H tracker at 1-2 mm tremor, 6-10 Hz (EXP-H01 recordings replayed offline, paired per writer); geometric mean ratio, with the paired 95 % upper bound below 1 | ≤ 0.8 | requirement | REQ-CTRL-011; SIM 430 against 627 µm (0.69), paired -197 µm (95 % CI -206 to -188); 6 Hz 818 -> 540 µm (results/ai2/ai2.json); with real inputs (study R, SIM) the gated tracker left 0.96 x and the Rev H tracker 1.06 x of the ordinary pen's tip tremor at the severe class (a ratio of about 0.9), and 1.03-1.04 x against 1.08 x at 1 mm (docs/real_data.md) -> predicted to FAIL on real tremor. These replays use the Rev J nose's reach, so a pass would not carry over to Rev K's nib: with Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F, docs/readable_target.md s8: the Rev J nose with its travel cut, tuning split), so Rev K's nib makes no severe-tremor legibility claim (DEC-060) | DEC-042 (revisit if it fails) |
| AC-L02-02 | REQ-CTRL-011 | Letters read by the app with the gated tracker minus with the Rev H tracker at every tremor condition, and ink error at 0.3 mm relative to the Rev H tracker (both) | both met (≥ -1 point; ≤ 1.02) | requirement | REQ-CTRL-011; SIM letters 78 against 64 % at 1-2 mm; 0.3 mm 161 against 162 µm | DEC-042 |
| AC-L02-03 | — | Closed loop on the bench pen with the EXP-I05 tremor rig (R2 with a 2-axis shaker), 1-2 mm at 6-10 Hz, 10 seeds: ink error with the gated tracker relative to the Rev H tracker (R3 scans) | ≤ 0.8 | hypothesis | pass line of study L; SIM 0.69, model to model only | DEC-042 |
| AC-L02-04 | REQ-RVJ-C01 | Firmware under test (review), checked on the EXP-L02 bench runs: the nose command passes the Rev H tracker's 64 Hz second-order output filter or an equivalent band limit no wider than the nose servo's measured bandwidth (EXP-N03), and the filter's delay is counted inside the prediction horizon (both) | conforms | requirement | REQ-RVJ-C01 (DEC-047); without the filter the listening prediction carried 15-200 Hz, the C1S nose missed its command by 890 µm rms, and the ink moved 1.6 x the device-off pen's (SIM, tuning writer 100; docs/revJ_simulation.md s4.1) | DEC-047; DEC-042 |
| AC-L02-05 | REQ-RVJ-C02 | SIM gate on the firmware under test, before the bench runs: tremor-free writing moved by each controller that can drive the nose, the heel wheel or the end-cap, against the device-off pen with the same noise and seed in sim2, tuning writers of v1 and v2 (RMS, every writer) | ≤ 25 µm | requirement | REQ-RVJ-C02 (DEC-048); sim2, test writers 0-4: G4 0 µm; ai2's gated listening tracker 36-85 µm; the TCN replayed 107-206 µm; nose + heel wheel in its tremor mode 324-503 µm (SIM, results/sim2j/et.json) -> FAILS for the wheel's tremor mode (DEC-048 keeps the wheel retracted) and for the gated listening tracker | DEC-048 (the wheel stays retracted until its controller passes); DEC-047 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-L02).
<!-- AC-TABLE:EXP-L02:END -->

- **Decision rule.** Pass: the gated tracker stays the default (DEC-042). Fail: revisit DEC-042; the Rev H tracker stays. G4 better than the gated tracker on real writing: revisit DEC-042 with DEC-047. A controller that fails the SIM gate does not run on the bench or with people (for the heel wheel, DEC-048).

### EXP-L04: Does a learned estimator pass REQ-ML-001 on real data?

- **Purpose and gates.** Test the TCN against the gate for learned models, and check its cost on the pen. Gates REQ-ML-001, REQ-ML-003 and the TCN's move from shadow mode to the nose (DEC-042).
- **DEC-061 (2026-09-30).** ai2's TCN, trained on synthetic writers, is retired as a candidate for driving the nib. The candidate is a small causal network trained on real writing and tremor (study E's real-data TCN), with its gate calibrated on the user's own writing (REQ-CTRL-016). It enters here only after EXP-E10 passes DEC-055's line on new held-out data (AC-R02-01). Study E's EXP-E14 is step 3: both int8 networks are timed on the pen's MCU, and study E's cycle model is checked (AC-L04-04).
- **Predictions.**
  - SIM: 278 µm at 1–2 mm (−152 µm against the gated tracker, 95 % CI −164 to −141), 307 µm at 6 Hz, 127 µm at 0.3 mm. Tremor-free writing moved 19.3 µm on average, but 34.8 µm for the worst writer, above REQ-ML-001's 25 µm. The 20 s calibration as an extra input did not help (290 µm).
  - CALC: 33 248 multiply-accumulates per 2 ms step; 33 kB of int8 weights and about 16 kB of history; about 0.56 ms per step on a 128 MHz Cortex-M33 (28 % of one core; MCU model ASSUMPTION, LIT EML-13).
  - Real inputs (study R, SIM): trained on synthetic writers, the TCN moved clean real writing 172 µm (93–286) and left 0.71 × the ordinary pen's tip tremor at the severe class. EXP-R05 retrains it on real inputs first (AC-R05-01).
  - CALC (study E, `docs/real_tracker.md` §13; the cycle model is an ASSUMPTION): ai2's TCN 16,658 multiply-accumulates per ms, 28.1 % of a 128 MHz Cortex-M33, 33.4 kB of weights; the real-data TCN 4,180, 7.5 %, 17.0 kB. Against the network contract of `docs/icd.md` §5 (v1.2), ai2's TCN does not fit; the real-data TCN fits the budget, but its inputs and outputs differ from the contract's.
- **Set-up.** EXP-H01 recordings with the Hall and grip-force channels, split by participant (REQ-DATA-001); only recordings whose consent covers model training (`human_study_plan.md` §3.3, item iii). The gated model-based stack as the conventional comparator (EXP-E01 protocol). The pen MCU on R7 for timing.
- **Procedure.**
  1. Train on synthetic data plus the training participants, then freeze.
  2. Test on held-out participants against the gated stack (paired bootstrap per band).
  3. Time each int8 build on the MCU (logic analyser or the DWT cycle counter; worst case over 10⁵ steps), ai2's TCN and the real-data TCN (study E's EXP-E14, on the nRF54L15 with int8 CMSIS-NN), and run the causality test of EXP-L01.
  4. Check the shadow-mode wiring: the TCN's output is logged and never reaches the nose command.
- **Measurands.** Residual ratio by band; false correction on tremor-free writing; spikes; worst-case step time; memory.

<!-- AC-TABLE:EXP-L04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L04-01 | REQ-ML-001 | Learned estimator (DEC-061: a small causal network trained on real writing and tremor, such as study E's real-data TCN, retrained with the EXP-H01 training participants; ai2's synthetic-trained TCN is retired as a nib driver) on held-out participants against the gated model-based stack as the conventional comparator: residual-ratio reduction in each of the 4-8 Hz and 8-12 Hz bands (paired bootstrap), false correction on tremor-free writing, and spikes (all, as REQ-ML-001) | all met (≥ 0.10 with the 95 % upper bound below 0; ≤ 25 µm RMS; no spike > 100 µm) | requirement | REQ-ML-001 as written, with the DEC-042 default as the comparator; SIM: 278 against 430 µm at 1-2 mm (paired -152 µm, 95 % CI -164 to -141); tremor-free writing 19.3 µm on average but 34.8 µm for the worst writer (docs/ai_control_v2.md s4.5) -> may fail on that writer; with real inputs (study R, SIM) the TCN as built moved clean real writing 172 µm (93-286) -> FAILS the 25 µm part until it is retrained on real inputs (EXP-R05, AC-R05-01); DEC-061 retires ai2's TCN as a nib driver: on real inputs it moved one test writer's clean writing 0.49-0.58 mm with and without a gate (SIM, study E) | DEC-042 (the TCN drives the nose only if this passes); DEC-061 |
| AC-L04-02 | REQ-ML-003 | Each int8 TCN (ai2's, 2 ms step; study E's real-data TCN, 4 ms step at 250 Hz; study E's EXP-E14) on the pen MCU (nRF54L15 or another 128 MHz Cortex-M33; logic analyser or DWT cycle counter, worst case over 1e5 steps): compute time per 2 ms of real time, weight memory, and causality (test of AC-L01-04) (all) | all met (≤ 2 ms per 2 ms step; ≤ 64 kB of weights; causal) | requirement | REQ-ML-003; prediction about 0.56 ms per step (28 % of one core) and 33 kB of int8 weights plus about 16 kB of history (CALC; MCU model ASSUMPTION, LIT EML-13); REQ-ML-002 allows ≤ 1 ms per 4 ms step; study E (CALC, cycle model ASSUMPTION): ai2's TCN 1.12 ms per 4 ms and 33.4 kB of weights (28.1 % of the core), the real-data TCN 0.30 ms per 4 ms and 17.0 kB (7.5 %) (docs/real_tracker.md s13) -> both predicted to pass | DEC-042 (TCN in shadow mode) |
| AC-L04-03 | REQ-ML-003 | Shadow mode (firmware review and logs): the TCN's estimate is computed and logged beside the default, and never reaches the nose command until AC-L04-01 passes | conforms | requirement | REQ-ML-003; DEC-042 | DEC-042 |
| AC-L04-04 | — | Each int8 TCN (ai2's; study E's real-data TCN) profiled on the pen's MCU (nRF54L15, Cortex-M33 at 128 MHz, int8 CMSIS-NN, DWT cycle counter; study E's EXP-E14): cycles per 1 ms of real time against study E's cycle model (fusion/budget.py: 0.5 multiply-accumulates per cycle plus 300 cycles per layer call) | within ±20 % of the model | hypothesis | the project's pass line for a model check (as AC-Q05-02); CALC with the cycle model (an ASSUMPTION, to be profiled): ai2's TCN 16,658 multiply-accumulates per ms, 28.1 % of the core; the real-data TCN 4,180, 7.5 % (docs/real_tracker.md s13; LIT ACT-144) | ACT-144's cycle model; the MCU budget (the firmware alone takes at least 31 % of the core) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-L04).
<!-- AC-TABLE:EXP-L04:END -->

- **Decision rule.** Pass: the TCN may drive the nose (DEC-042 revisit). Fail: it stays in shadow mode, and is retrained with more real data.

### EXP-L05: Does an RL arbiter survive a closed-loop simulator and the bench?

- **Purpose and gates.** Test RL arbitration where the replay results broke down: in closed loop. Gates REQ-ML-004 and DEC-042 (RL offline only).
- **Predictions (SIM, replay-trained policy).** The PPO arbiter read 89 % of words at 298 µm. But it moved tremor-free writing by 30.7 µm (60.9 µm on tuning data, 128 µm for one tuning writer) and was worse than Rev H at 10 Hz, 0.3 mm, so it failed rules R1 and R2. Its replay rule (mean weight ≤ 0.05) missed brief full openings. Residual RL on the command moved tremor-free writing by 165 µm.
- **Set-up.** sim2 (MuJoCo, closed loop, the pen's own sensors) with the estimators run online: the lag-0 smoother as a forward Kalman filter, the recursive Rev H filter, and the detector every 50 ms on a ring buffer. The Gymnasium arbiter environment (`ai2/rl_env.py`) with sim2 as its backend. Then the EXP-V05 bench rig.
- **Dependency.** Training a policy in sim2 for bench tests is context of use COU-2. It needs sim2 validated first (EXP-V05, REQ-SIM-005).
- **Status (2026-09-29).** The closed-loop environment is ready in `sim2j/rl.py`: Gymnasium on sim2 at 50 µs, with the firmware and online sensors of the whole-pen study; the action is a residual on the guarded tracker G4 (DEC-047); domain randomisation over sim2's 25 factors and the Rev J ones. Training, selection and test were not run: about 2.4 CPU hours are needed (`python3 -m sim2j.run_study --stages rl_train rl_select rl_test`). The selection rule is frozen in `results/sim2j/rules.json` (`docs/revJ_simulation.md` §7).
- **Procedure.**
  1. Before training, fix a selection rule on the closed-loop false correction or the peak weight.
  2. Train with a closed-loop false-correction constraint.
  3. Test on held-out sim2 writers and seeds against the model-based gate.
  4. Only if it passes, and EXP-V05 has passed: run the frozen policy on the bench rig.
- **Measurands.** Ink error against the model-based gate; tremor-free writing moved; gate chatter (weight changes per second).

<!-- AC-TABLE:EXP-L05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L05-01 | REQ-ML-004 | RL arbiter trained in sim2's closed loop (estimators run online, closed-loop false-correction constraint), on held-out sim2 writers and seeds: ink error at 1-2 mm relative to the model-based gate, and tremor-free writing moved minus the gate's, with REQ-CTRL-010 and REQ-CTRL-011 met (all) | all met (≤ 0.95; ≤ 2 µm RMS; REQ-CTRL-010 and -011) | requirement | REQ-ML-004 (beats the gate by ≥ 5 %); replay-trained PPO: 298 µm and 89 % of words, but 30.7 µm on tremor-free writing and worse at 10 Hz, 0.3 mm, so it failed rules R1 and R2 (SIM, docs/ai_control_v2.md s5.3); the closed-loop environment is ready in sim2j/rl.py (a residual on the guarded tracker G4, DEC-047), and training, selection and test were not run (docs/revJ_simulation.md s7) | DEC-042 (RL offline only; revisit if it passes) |
| AC-L05-02 | — | The frozen arbiter on the bench rig (EXP-V05 set-up), 1-2 mm tremor: ink error relative to the model-based gate, and tremor-free writing moved minus the gate's (both); gate chatter reported | both met (≤ 0.95; ≤ 2 µm RMS) | hypothesis | pass line of study L; the bench part is policy training for bench tests (COU-2), allowed only after EXP-V05 passes (REQ-SIM-005) | DEC-042; DEC-040 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-L05).
<!-- AC-TABLE:EXP-L05:END -->

- **Decision rule.** Fail: keep the model-based gate (DEC-042). Pass in sim2 and on the bench: RL arbitration may be proposed for the pen (DEC-042 revisit).

---

## 46. Rev J integrated layout: EXP-J01…J07; Rev J.1 and the whole-pen simulation: EXP-J10…J17

### Purpose and what it gates

DEC-044 joins the round-1 designs into one Ø24 mm pen.
- **Front.** The C1S nose (gimbal 76.5 mm behind the ball) with its nominal travel raised to 6.57 mm at 50°, so that 6.0 mm stays guaranteed over 35–75°. A C-shaped skid ring of contact radius 11.65 mm, open 120° on top and 10 mm into the sleeve, with the heel wheel in a slot at 12.0 mm. The sleeve front is Ø23.3 mm, flush with the ring. The page sensor looks at the paper beside the wheel through folded optics.
- **Middle.** The main board on top (z 50–72) carries the IMU and two linear Hall sensors that read a magnet on the carrier. The pen-lift and ink-force drum sits in front of the gimbal, with a rear pulley.
- **Rear.** The cell sits behind the coil plate (z 92.7–141.2, axis 3 mm up), with the two heel motors under it and 80 mm shafts in grooves of the bottom wall. The detachable end-cap replaces the rear cap. The desk-board magnet is removed.
- **What it gates.** DEC-044 is revisited if detailed CAD loses the 0.04–0.14 mm margins, if an EXP-J test fails (gimbal axial load, motor cogging, nose sensing near the magnets, stray field, ink visibility, heat), or if the battery cannot reach 8 h in the steady modes with the page sensor duty-cycled (EXP-P01, AC-P01-06). Requirements: REQ-RVJ-I01…I06, and the updated REQ-RVJ-N03, N05, N06 and REQ-EC-001.
- **DEC-050 (2026-09-30).** The C1S nose is not carried forward. The next prototype, Rev K, is the Rev J body with study B's B1 nib, the heel wheel retracted and no tail; study K laid it out (DEC-062…066, §53). EXP-J01…J03, J05…J07, J11, J13 and J14 test C1S parts or the field around them: they stay as bench research on the C1S module, and their criteria say so. EXP-J17 gains part (c), study B's counter-face bench (EXP-B22). REQ-RVJ-I02…I05 are re-scoped for Rev K: EXP-J02, J03 and J07 are to be repeated on Rev K's layout (DEC-062), which did not recompute their quantities, so their predictions still come from the Rev J.1 layout; B1's suspension is checked in EXP-T08 (AC-T08-04).
- **Predictions** come from `docs/revJ_design.md` and `results/revJ/` (CALC on the round-1 designs; 38 of 38 fit checks pass). No new closed-loop simulation was run; SIM numbers are quoted from the round-1 studies. The magnetic fields are free-space calculations without iron or motor housings, so the stray fields are upper bounds.
- **Mock-ups** are printed from `results/revJ/revJ_pen_assembly.step` and `revJ_pen_assembly_no_endcap.step`.
- Work with people (EXP-J08 ink visibility, EXP-J09 mass and balance, EXP-J15's writers, and EXP-J18, the heel wheel on writing) is in [`human_study_plan.md`](human_study_plan.md) §20. The Rev J.1 fixes (DEC-045) and their tests follow EXP-J07; EXP-J17, the nib's static load (DEC-046), comes last.

### EXP-J01: Axial pull and centring of the actuator

- **Purpose and gates.** Measure the magnet cap's axial pull on the gimbal and the effect of an off-centre sphere, before a nose is built for EXP-N02…N05. Gates REQ-RVJ-I02, DEC-044, DEC-045 (revisited above 27 N) and the gimbal of DEC-036. The gimbal itself is tested in EXP-J11.
- **Rig (study M).** Runs on R12 as part of EXP-T08 (§47; `docs/measurement_rig.md` §5.3).
- **Predictions (CALC).**
  - The cap pulls toward the coil plate's iron with 16.5 N (image method with ideal iron, an upper bound; a cruder uniform-gap estimate gives 36 N).
  - The pull depends on where the iron face is taken: 12.4–22.2 N (CALC, DEC-045); Rev J.1 designs the gimbal for 22.2 N. Study N's 50 µm strips buckle at 16.4 N in compression by a co-rotational beam model, a safety factor of about 1.0 (Rev J's 1.24 used Euler buckling per strip). DEC-045's 75 µm strips buckle at 55.3 N.
  - An axial offset of the spheres' centre changes the pivot stiffness by 0.83 mN·m/rad at 0.05 mm (its sign follows the offset): 29 % of study N's 2.8 mN·m/rad, but 3.6 % of the 75 µm pivot's 22.7. A sideways offset costs 2 / 12 / 48 mW of holding power at 0.02 / 0.05 / 0.1 mm.
- **Set-up.** The C1S cap and a Hiperco plate dummy on an x-y-z stage over a load cell (±50 N, 0.01 N resolution). Then the assembled nose with the 75 µm gimbal (DEC-045), the coil plate seated on a shim chosen after measuring the unpowered nose's stiffness.
- **Procedure.**
  1. Pull against gap (0.6–1.2 mm) and tilt (±5.3°).
  2. Torque against axial and sideways offsets of 0–0.1 mm.
  3. Measure the centring of the spheres on the pivot in the assembled nose. The gimbal's buckling, fatigue and drops are EXP-J11.
- **Measurands.** Axial pull; offset torque; centring error.

<!-- AC-TABLE:EXP-J01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J01-01 | — | Axial pull of the C1S magnet cap on a Hiperco plate dummy (x-y-z stage over a load cell, ±50 N, 0.01 N resolution) over gaps 0.6-1.2 mm and tilt ±5.3°, and the torque from axial and sideways offsets of 0-0.1 mm, against revj magnetics.axial_pull | within ±20 % of the prediction | hypothesis | pass line of the integrated design study; prediction 16.5 N at the design gap, 12.4-22.2 N by where the iron face is taken (image method with ideal iron, an upper bound; a cruder uniform-gap estimate gives 36 N) (CALC, results/revJ/magnetics.json, results/revJ1/magnetics.json); DEC-045 designs the gimbal for 22.2 N | DEC-044; DEC-045 (revisit above 27 N: 100 µm x 5 mm strips); DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J01-02 | REQ-RVJ-I02 | Offset of the spheres' centre from the pivot in the assembled nose, axially and sideways (the coil plate seated on a shim chosen after measuring the unpowered nose's stiffness); the buckling, fatigue and drop parts of REQ-RVJ-I02 are AC-J11-01 and AC-J11-02 | ≤ 0.05 mm | requirement | REQ-RVJ-I02 (DEC-045); an axial offset of 0.05 mm changes the pivot stiffness by 0.83 mN m/rad (its sign follows the offset), 3.6 % of the 75 µm pivot's 22.7, and a sideways one a steady 0.83 mN m that the coils hold with 12 mW (CALC, results/revJ1/magnetics.json) | DEC-045; DEC-044; DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J01).
<!-- AC-TABLE:EXP-J01:END -->

- **Decision rule.** Pull above 27 N: 100 µm × 5 mm strips (DEC-045 revisit; strips in tension and thrust pivots were rejected). Pull outside ±20 % of the model: update `revj/magnetics.py` and the design's heat and power numbers. Centre off by more than 0.05 mm: re-shim the plate.

### EXP-J02: Heel-motor cogging from the C1S magnets

- **Purpose and gates.** Measure the detent that the actuator's magnets add at the heel motors, at their Rev J.1 place (re-specified for DEC-045). Gates REQ-RVJ-I03, REQ-RVJ-I04 (the motors' field at the nose Hall sensors), DEC-045 and DEC-037's drive.
- **Predictions (CALC, free space).** Only the transverse field turns a rotor. At the Rev J.1 place (the motors and gears 10 mm further back): 0.0073 mN·m, 0.66 × the motor's 0.011 mN·m friction torque. At Rev J's place: 0.062 mN·m, 5.6 × (Rev J's bound of 0.080 counted the axial field too), or 0.12 N at the tyre against a 0.03 N backdrive. The housing is black-anodised aluminium and does not shield (MFR AMF-155). The plate's back iron lies between the cap and the motors, so free space is an upper bound. A soft-iron cup does not fit. Moving the motors back also lowers their ripple at the nose Hall sensors from 15.4 to 10.2 µm.
- **Set-up.** A Faulhaber 0620 B at its Rev J.1 place, and at Rev J's for comparison, behind a C1S cap and a coil-plate dummy with a 1.5 mm Hiperco back iron; the cap at rest and at its stops in four directions. A torque sensor with 0.001 mN·m resolution on the motor shaft.
- **Procedure.**
  1. Unpowered, turn the shaft slowly: cogging torque against rotor angle at each cap position, with the cap in place and removed; log the motor's own Hall signals.
  2. No-load current and speed (iron near the rotor would add loss).
  3. With the rotor turning, the motor's field at the nose Hall sensors' place (for EXP-J03).
  4. The same with a 0.1 mm low-carbon steel cup, if a later layout finds room.
- **Measurands.** Added detent torque at each cap position; no-load current and speed; the motor's field at the nose Hall sensors.

<!-- AC-TABLE:EXP-J02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J02-01 | REQ-RVJ-I03 | Detent torque added at a Faulhaber 0620 B at its Rev J.1 place (10 mm further back than Rev J's, DEC-045), behind a C1S cap and a coil-plate dummy with a 1.5 mm Hiperco back iron, against rotor angle (torque sensor with 0.001 mN m resolution, unpowered, turned slowly), with the cap at rest and at its stops in four directions; largest over the cap positions | ≤ 0.011 mN m | requirement | REQ-RVJ-I03 (the motor's friction torque, MFR AMF-100, AMF-155); prediction 0.0073 mN m at the Rev J.1 place (0.66 x the friction) and 0.062 mN m at Rev J's, from the transverse field only (CALC, free space, an upper bound: the plate's back iron lies between; the aluminium housing does not shield, MFR AMF-155; rotor magnet ASSUMPTION; results/revJ1/magnetics.json) -> predicted to pass; a soft-iron cup does not fit | DEC-045 (revisit above the friction torque: motors 15 mm back); DEC-037 (cogging); DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-J02).
<!-- AC-TABLE:EXP-J02:END -->

- **Decision rule.** Above the friction torque at any cap position: move the motors 15 mm back (0.0024 mN·m, CALC) and repeat (DEC-045 revisit).

### EXP-J03: Nose position sensing near the magnets

- **Purpose and gates.** Check the two linear Hall sensors in their real neighbourhood. Gates REQ-RVJ-I04 and DEC-044.
- **Rig (study M).** The coil-current part runs on R12 in EXP-T09 (§47; `docs/measurement_rig.md` §5.3); AC-J03-01 also needs the heel motors running and the brake switching.
- **Predictions (CALC).**
  - Noise 5.6 µm (x) and 6.1 µm (y) rms at the tip (MFR OPT-46); a 3-D Hall would give 24 / 49 µm at full rate (MFR OPT-53).
  - The cap's own field: 2.8 µm in y, a fixed map of the nose position that can be calibrated out.
  - Unshielded heel motors: 10.2 µm in x at their Rev J.1 place (15.4 µm at Rev J's), turning with the rotor: just over 10 µm until it is subtracted by rotor angle. The Earth's field: 16.8 µm in x, slow.
  - Not computed: the pen-lift brake's field when it switches, and the coils' own fields.
- **Set-up.** The board with two DRV5055-A4 sensors over the carrier's 2 × 2 × 1 mm magnet on a 2-axis micrometre stage (R5), with the cap, plate and coils, the two heel motors and the pen-lift brake at their Rev J.1 places (DEC-045: the motors 10 mm further back).
- **Procedure.**
  1. Map the sensor outputs against the magnet position and fit the calibration, including the cap's field map.
  2. Measure the error at fixed positions with the motors running at lead-through speeds, the brake switching, and coil currents stepped from 0 to 1.5 A.
  3. Subtract the motors' field by rotor angle (from the motors' own Hall signals), and repeat with shields if needed.
- **Measurands.** Position error at the tip, rms over the servo band and as steps; its parts from each source.

<!-- AC-TABLE:EXP-J03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J03-01 | REQ-RVJ-I04 | Nose position error at the tip from the two DRV5055-A4 sensors over the carrier magnet on a 2-axis micrometre stage, over the servo band, with the heel motors running, the pen-lift brake switching and coil currents of 0-1.5 A, after calibration of the cap's field map | ≤ 10 µm RMS | requirement | REQ-RVJ-I04; prediction 5.6-6.1 µm of noise; unshielded heel motors 10.2 µm of ripple at their Rev J.1 place (15.4 µm at Rev J's), to subtract by rotor angle or shield; brake and coil fields not computed (CALC, results/revJ/magnetics.json, results/revJ1/magnetics.json) | DEC-044; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-J03).
<!-- AC-TABLE:EXP-J03:END -->

- **Decision rule.** Above 10 µm: subtract or shield the largest source and repeat. Still above: revisit the sensor layout (DEC-044).

### EXP-J04: Page-sensor working band

- **Purpose and gates.** Measure the height band in which the page sensor works, with the folded optics in their Rev J place. Gates REQ-RVJ-N06, REQ-DRV-005 and DEC-044. It shares the sensor board with EXP-N07, which then tests the position error in writing sweeps.
- **Rig (study M).** Runs on R10 in EXP-T04 with the nose insert, for the height and roll band (§47; `docs/measurement_rig.md` §3.2, §3.5).
- **Predictions (CALC).**
  - The lens sits 2.23–2.45 mm above the paper over 35–75° with no roll: inside the lens's 2.2–2.6 mm reference band (MFR OPT-54).
  - With ±5° of roll it spans 2.06–2.74 mm; with ±20°, 1.59–4.11 mm. The band holds only within about ±1.5° of roll.
  - A writer pressing less than the wheel's 0.55 N preload lifts the ring by up to 0.32 mm (height up to 2.71 mm).
- **Set-up.** The optical-flow die with the folded optics on a tilt, roll and height stage over the six EXP-D01 papers; an encoder stage as the reference. Both candidate dies: the PMW3610 class (DEC-045) and the PMW3360 class (the autowrite fallback); both have the same 2.2–2.6 mm lens plane (MFR OPT-61, OPT-54).
- **Procedure.** Heights 1.5–4.2 mm, roll 0–20° and tilt 35–75°, at writing speeds; log position error and dropouts at each point.
- **Measurands.** Usable height band; position error; dropouts.

<!-- AC-TABLE:EXP-J04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J04-01 | REQ-RVJ-N06 | Page sensor with the folded optics beside the wheel, on a tilt, roll and height stage over the six EXP-D01 papers against an encoder stage: position error and dropouts over tilt 35-75° and pen roll up to ±20° (both) | both met (≤ 10 µm RMS; no dropout) | requirement | REQ-RVJ-N06 (DEC-044: roll ±20° and the lens in its band); prediction lens 2.23-2.45 mm above the paper with no roll, inside the 2.2-2.6 mm band (MFR OPT-54), but 1.59-4.11 mm at ±20° of roll (CALC) -> predicted to FAIL beyond about ±1.5° of roll | DEC-044; DEC-036 (page sensor); DEC-037 (slip detection) |
| AC-J04-02 | — | Measured usable lens-height band of the folded optics (heights with ≤ 10 µm RMS and no dropout, heights 1.5-4.2 mm) against the heights the Rev J pen reaches over 35-75° and ±20° of roll | covers 1.59-4.11 mm | hypothesis | pass line of the integrated design study (the band measured; a redesign if it is too narrow); the lens's reference band is 2.2-2.6 mm (MFR OPT-54) -> predicted to FAIL without more depth of field; options: such a lens, the wheel's odometry to bridge short dropouts, or a window near the tilt-invariant point (docs/revJ_design.md s3.7) | DEC-044 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J04).
<!-- AC-TABLE:EXP-J04:END -->

- **Decision rule.** Band too narrow (as predicted): choose a lens with more depth of field, bridge short dropouts with the wheel's odometry, or move the window near the tilt-invariant point, then repeat. The page position and slip detection stay at risk until then (REQ-RVJ-N06, REQ-DRV-005).

### EXP-J05: Heat at the web

- **Purpose and gates.** Measure the skin temperature at the thumb–index web, which lies over the coil plate. Gates REQ-RVJ-N03, the spreader, DEC-044 and DEC-045. It complements EXP-N04, which runs the real coils; EXP-J13 extends it over power, room and a hand phantom.
- **Rig (study M).** Runs as part of EXP-T15 on R13, the heater shell first (§47; `docs/measurement_rig.md` §6.3).
- **Predictions (CALC).** Rev J (DEC-044): the fin model gave 93.5 K/W from the plate to the skin, and the web 45.7 °C in a 30 °C room at 1 mm tremor. Rev J's 0.5 mm aluminium sleeve inside the bore does not fit: it would hit the swinging magnet cap and the motors. Rev J.1 (DEC-045): a 0.1 mm graphite sheet, 30 mm long, in a recess of the shell wall (+0.21 g). At 0.17 W the web rises 5.9 K with it and 17.8 K bare: 35.9 °C and 47.8 °C in a 30 °C room. Every spreader is nearly isothermal, so its length, not its material, sets the result.
- **Set-up.** A PEEK shell with a heater in place of the coil plate (0.06–0.38 W), bare and with the graphite sheet; 23 °C and 30 °C rooms; still air; an IR camera and thermocouples.
- **Procedure.** 30 min at each power, room and shell; read the web and the other held surfaces.
- **Measurands.** Web surface temperature; the plate-to-skin resistance.

<!-- AC-TABLE:EXP-J05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J05-01 | REQ-RVJ-N03 | Web surface temperature over the coil plate: PEEK shell with a heater in place of the plate at 0.17 W, still air, 30 min, in a 30 °C room, with the 0.1 mm graphite sheet in the shell wall (DEC-045; the bare shell as the baseline) (IR camera and thermocouples); guarded acceptance | ≤ 43 °C | requirement | REQ-RVJ-N03 (DEC-045: held surfaces ≤ 43 °C absolute in a rated 30 °C room, 41 °C design target; was 41 °C, DEC-044); prediction at 0.17 W: web rise 5.9 K with the sheet (35.9 °C) and 17.8 K bare (47.8 °C) (CALC, fin model, docs/revJ1_design.md s5.2); Rev J's 0.5 mm aluminium sleeve inside the bore does not fit (it would hit the magnet cap and the motors) | DEC-045 (heat); DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-J05).
<!-- AC-TABLE:EXP-J05:END -->

- **Decision rule.** Above 43 °C with the sheet: a longer sheet (40 mm gives 27 K/W) or a lower cap on the coil loss in warm rooms (DEC-045). Safety-related: guarded acceptance (§0.5).

### EXP-J06: Ink-force drum, spring and front stop

- **Purpose and gates.** Test the fatigue-rated ink-force spring and the front stop that follows the nose (DEC-041 items 2 and 4). Gates REQ-RVJ-N05, REQ-RVJ-N09 (the front stop, DEC-045) and DEC-044. The drum's spiral spring is also a candidate in EXP-N06: run its cycling here once, and keep EXP-N06 for the other candidates and the stock spring.
- **Predictions (CALC).**
  - A 301 full-hard strip, 38 µm × 2.6 × 139 mm, gives 0.12–0.18 N along the refill over the 27.4 mm tendon travel, and 0.19–0.21 N normal at the ball at every tilt.
  - Goodman safety factor 1.73 at 10⁸ small cycles (±1.3 mm) and 1.30 at full travel (fatigue strength LIT AMF-20 with 0.8 ASSUMPTION).
  - Front stop: the brake locks when the slide runs 0.3 mm past the contact. At a 30 mm/s lift, detection takes 7.7 ms and the brake 3 ms (both ASSUMPTION): about 0.33 mm of ink tail.
- **Set-up.** The drum, the spring, the electro-permanent brake, the slide Hall and the tendon loop with its two pulleys on a linear stage with a force sensor (R8 for the long cycling); a writing robot for the lifts.
- **Procedure.**
  1. Force against travel over 27.4 mm.
  2. 10⁸ cycles at ±1.3 mm and 10⁵ full-travel cycles (ASSUMPTION); re-measure the force at every decade.
  3. Pen lifts at 30 mm/s at 35/50/75°; log the slide at which the brake locks (slide Hall) and measure the ink tail on R3 scans.
- **Measurands.** Force against travel; fracture; slide at which the brake locks; ink tail.

<!-- AC-TABLE:EXP-J06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J06-01 | REQ-RVJ-N05 | Ink-force drum with the 38 µm spiral spring and the tendon loop on a linear stage: force along the refill over the 27.4 mm tendon travel, and fracture after 1e8 cycles at ±1.3 mm and 1e5 full-travel cycles (both) | both met (0.12-0.18 N; no fracture) | requirement | REQ-RVJ-N05 (0.15 N ± 20 % along the refill); prediction 0.12-0.18 N; Goodman safety factor 1.73 at 1e8 small cycles and 1.30 at full travel (CALC, results/revJ/refill.json; fatigue strength LIT AMF-20 with 0.8 ASSUMPTION; 1e5 full cycles ASSUMPTION) | DEC-044; DEC-041 item 2; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J06-02 | REQ-RVJ-N09 | Front stop by the drum brake: slide beyond the ball's contact position at which the brake locks (slide Hall), and the ink tail after a pen lift at 30 mm/s, at 35/50/75° (both) | both met (≤ 0.3 mm; ≤ 0.5 mm) | requirement | REQ-RVJ-N09 (DEC-045; was a pass line of the integrated design study); rule 0.3 mm past the computed contact, and a 0.5° tilt error moves the computed contact by 0.17 mm -> at risk from the tilt estimate; prediction 0.33 mm of ink tail (detection 7.7 ms and brake 3 ms, both ASSUMPTION; CALC, docs/revJ_design.md s5.3) | DEC-041 item 4; DEC-044; DEC-045; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J06).
<!-- AC-TABLE:EXP-J06:END -->

- **Decision rule.** Force out of band or a fracture: resize the spring (thicker strip, longer drum) and repeat. Ink tail over 0.5 mm: a faster brake, or a tighter tilt estimate.

### EXP-J07: Field outside the pen

- **Purpose and gates.** Measure the field around the pen for the manual's implant warning. Gates REQ-RVJ-I05 and DEC-044.
- **Predictions (CALC, free space).** Largest field at 5 / 10 / 20 / 30 / 50 mm from the surface: 13.3 / 5.3 / 1.35 / 0.52 / 0.14 mT. The unshielded heel motors dominate; the magnet cap alone falls to 1 mT at about 10 mm, all sources at about 23 mm. The 1 mT level is an ASSUMPTION until ISO 14117 and the makers' guidance are read.
- **Set-up.** A magnetic mock-up of the Rev J pen: the magnet cap, the coil plate, the two heel motors and the end-cap's tiles at their places; a 3-axis gaussmeter on a scanning stage.
- **Procedure.** Scan 5–50 mm from the surface along the pen and round it, with and without the end-cap; the motors at rest in their worst rotor angle.
- **Measurands.** Largest field against distance; the distance to the implant limit.

<!-- AC-TABLE:EXP-J07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J07-01 | — | Largest field 5-50 mm from the surface of a magnetic mock-up (magnet cap, coil plate, two heel motors, end-cap tiles), gaussmeter scan, against revj magnetics.outside_field | within ±30 % of the prediction | hypothesis | pass line of the integrated design study (otherwise the measurement replaces the model); prediction 13.3 / 5.3 / 1.35 / 0.52 / 0.14 mT at 5 / 10 / 20 / 30 / 50 mm (CALC, free space; motor housings ignored, so an upper bound) | DEC-044; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J07-02 | REQ-RVJ-I05 | Distance from the pen's surface at which the measured field falls to the implant limit set from ISO 14117, stated in the user manual (document review) | measured and stated | requirement | REQ-RVJ-I05; prediction 1 mT at about 23 mm (the magnet cap alone about 10 mm) (CALC); the 1 mT level is an ASSUMPTION until ISO 14117 and the makers' guidance are read | DEC-044; the manual's implant warning; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J07).
<!-- AC-TABLE:EXP-J07:END -->

- **Decision rule.** The measurement replaces the model where they differ by more than 30 %. The manual states the measured distance at the limit set from ISO 14117.

### Rev J.1 fixes (DEC-045): what changes and what it gates

DEC-045 keeps the Rev J layout and fixes the loads and budgets that Rev J failed (`docs/revJ1_design.md` §1).
- **Gimbal.** Study N's cross strips stay in compression, but 75 µm thick (301 full-hard). Axial shock stops engage within 5 µm behind and 20 µm in front. The sphere centre sits on the pivot within 0.05 mm. Strips in tension and thrust pivots are not used.
- **Magnetics.** The coil plate's back iron is 1.5 mm (Rev J: 2.37 mm). The heel motors and their gears sit 10 mm further back.
- **Power.** A PMW3610-class page sensor stays on in every mode, because DEC-042's detector runs on it. A PMW3360-class die stays the fallback for autowrite until EXP-J10. The electronics are counted from datasheets (34–60 mW; duty cycles ASSUMED). The heel drivers sleep in the steady mode. The end-cap runs only while a tremor line is detected. The cell stays the LIR14500. One set of battery targets is in REQ-RVJ-I01.
- **Heat.** A 0.1 mm graphite sheet, 30 mm long, sits in the shell wall over the coil plate and the web. One skin rule: held surfaces ≤ 43 °C in a rated 30 °C room, with 41 °C as the design target (REQ-THM-001, REQ-RVJ-N03).
- **Mass and view.** A 29.6 g end-cap with a 9 mm tungsten slug: the pen is 84.3 g, and 112.7 g with the end-cap. The first 15 mm of the front sleeve are clear hard-coated PC over the top 240°.
- **What it gates.** DEC-045 is revisited if:
  - EXP-J01 measures a pull above 27 N (then 100 µm × 5 mm strips);
  - EXP-J10 shows that the low-power die cannot give autowrite's 1 kHz and 10 µm;
  - EXP-L01 shows that the detector needs the 1 kHz stream;
  - EXP-N01, EXP-N04 or the whole-pen simulation confirm a nose-coil power ≥ 2 × study N's model;
  - EXP-J02 measures a detent above the motor friction;
  - EXP-J16 gives less than 10 % further reduction with the 29.6 g end-cap at the measured grip split.
- **Requirements.** REQ-RVJ-I01 (with REQ-EC-008 folded in), I02, I06, I07; REQ-RVJ-N03 and N09; REQ-THM-001; REQ-EC-001; REQ-DRV-009.
- **Predictions** come from `docs/revJ1_design.md` and `results/revJ1/`: CALC (a co-rotational beam model of the pivot, magpylib with ideal iron, the fin model, ray casting, datasheet budgets; 44 of 44 fit checks) and SIM (study K's model H1 for the end-cap family). Mock-ups are printed from `results/revJ1/revJ1_pen_assembly.step` and `revJ1_pen_assembly_no_endcap.step`.
- **The big caveat.** Every battery and heat prediction rests on study N's nose-coil power. The whole-pen simulation has reported 1.3–2.4 W in some tremor runs (unconfirmed). At 2 × study N's power, steady writing at 1 mm tremor lasts 4.9–5.3 h and the web reaches 42.1 °C; at 5 ×, 2.0–2.1 h and 63.8 °C. EXP-N01 (K_m), EXP-N04 (heat at the duty), EXP-J12 and EXP-P01 measure the parts of it.
- EXP-J02 above is re-specified for Rev J.1. EXP-J15's writers are in [`human_study_plan.md`](human_study_plan.md) §20, where EXP-J15 supersedes EXP-J08 for Rev J.1.

### EXP-J10: Can a low-power page sensor serve every mode?

- **Purpose and gates.** Test the PMW3610-class die in the folded optics, and its power. Gates REQ-RVJ-N06 (autowrite), REQ-RVJ-I07, REQ-RVJ-C05 (drift), the slip detection of REQ-DRV-005, DEC-042's detector, DEC-045 and DEC-049.
- **Rig (study M).** Runs on R10 in EXP-T04 with the nose insert, with power logging. Its addition, the window errors and their correlation in sim2j's form, is `rig.pagesense.sim2j_page_model`, judged by AC-J10-04; AC-J10-03 (power) is unchanged (§47; `docs/measurement_rig.md` §3.6).
- **Predictions.**
  - 0.60 mA at 1.8 V; 1.3–1.9 mW with its polling and the regulator (MFR OPT-61; × 1.5 ASSUMPTION; CALC).
  - 3200 cpi (7.9 µm counts), 24–30 in/s and 10 g, with the same 2.2–2.6 mm lens plane as the PMW3360 (MFR OPT-61). Its frame rate and its accuracy on paper are not stated: no prediction.
  - What the modes need: autowrite 1 kHz, ≤ 2 ms and ≤ 10 µm (REQ-RVJ-N06); the detector a 250 Hz grid (DEC-042); guide and lead-through ≥ 120 Hz and ≤ 10 ms.
  - Drift (REQ-RVJ-C05). DeltaPen (LIT OPT-02, on a tablet surface, not paper) had 68.3 µm mean and 23.6 µm median error per 10 ms window, and 2.6 mm/min of drift at rest. In sim2, errors like that which do not add up left autowrite readable with 2–4 × the ink error; errors that add up drifted the letters 1.5–3 mm apart (SIM, `results/sim2j/page_noise.json`).
- **Set-up.** The die with the folded optics on the EXP-J04 stage; the six EXP-D01 papers; lens heights 2.0–2.8 mm, tilt 35–75°, roll 0–5°; polled at 1 kHz; the encoder as ground truth; a current probe on the sensor's supply. A PMW3360-class die as the reference.
- **Procedure.** Writing sweeps with 1 mm of tremor added, at each paper, height, tilt and roll. Latency by cross-correlation with the encoder. Supply current at the polling of each mode. At writing speeds, log the error of each 10 ms window and its correlation over time, in the form `sim2j/sensing.py` uses; then re-run `python3 -m sim2j.run_study --stages page_noise` with the measured model. `rig.pagesense.sim2j_page_model` fits the structure function V(L) = 2·E|h|² + L·E|w|² to separate the held part h from the walking part w, and `patch_sim2j` loads the measured model into sim2j for one run, which sim2j's owner makes.
- **Measurands.** Report rate; latency; position error; dropouts; power; error per 10 ms window (DeltaPen's metric, with the vector metric beside it) and its correlation over time; the accumulated (walking) part of the error over 2 s of writing, from the structure function, with the raw 2 s difference beside it (DEC-059).

<!-- AC-TABLE:EXP-J10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J10-01 | REQ-RVJ-N06 | PMW3610-class die with the folded optics, polled at 1 kHz on the EXP-J04 stage, six EXP-D01 papers, lens 2.0-2.8 mm above the paper, tilt 35-75°, roll 0-5°, 1 mm tremor added, against the encoder: report rate, latency and position error (all); the roll range of REQ-RVJ-N06 is tested in EXP-J04 | all met (≥ 1 kHz; ≤ 2 ms; ≤ 10 µm RMS) | requirement | REQ-RVJ-N06 (autowrite's needs); the die's frame rate and accuracy on paper are not stated (MFR OPT-61: 3200 cpi, so 7.9 µm counts; 24-30 in/s; the PMW3360's 2.2-2.6 mm lens plane): no prediction; a PMW3360-class die stays the autowrite fallback (DEC-045) | DEC-045 (revisit if the low-power die cannot give autowrite's 1 kHz and 10 µm) |
| AC-J10-02 | — | Same set-up at the needs of DEC-042's detector and the slip detector: report rate and position error (both) | both met (≥ 250 Hz; ≤ 50 µm RMS) | hypothesis | pass line of the Rev J.1 study; the detector works every 50 ms on a 250 Hz grid (DEC-042); guide and lead-through need ≥ 120 Hz and ≤ 10 ms (CHECKPOINT s7); 50 µm engineering judgement; no prediction | DEC-045 (the page sensor on in every mode); DEC-042; DEC-037 (slip detection) |
| AC-J10-03 | REQ-RVJ-I07 | Page-sensor power from the cell (current probe on its supply, regulator included) at the polling each mode uses, the sensor on in every mode | ≤ 3 mW | requirement | REQ-RVJ-I07; prediction 1.3-1.9 mW (0.60 mA at 1.8 V, MFR OPT-61, x 1.5 for polling and the regulator, ASSUMPTION; CALC, results/revJ1/budgets.json); a PMW3360-class die takes 34-80 mW (MFR AMF-109) | DEC-045 |
| AC-J10-04 | REQ-RVJ-C05 | Page sensor (the PMW3610-class die) on paper at writing speeds (rig R10 in EXP-T04 with the nose insert; six EXP-D01 papers, tilt 35-75°, writing sweeps of 5-100 mm/s against the encoder): (a) the accumulated (walking) part of the position error over 2 s of writing, sqrt(200 var_w) from the structure function V(L) = 2 E\|h\|^2 + L E\|w\|^2 of the 10 ms window errors (rig.pagesense), with the raw \|P(t + 2 s) - P(t)\| (95th percentile) reported beside it; (b) the error of each 10 ms window by DeltaPen's metric \| \|ds\| - \|dg\| \|, median and mean, with the vector metric \|ds - dg\| reported beside it (both) | both met (accumulated part ≤ 0.1 mm per 2 s; per 10 ms window, median ≤ 24 µm and mean ≤ 68 µm) | requirement | REQ-RVJ-C05 (DEC-049, DEC-059); DeltaPen (LIT OPT-02, OPT-85, on a tablet surface): 23.6 µm median and 68.3 µm mean per 10 ms window by its own metric, the error of the translation length, and 2.6 mm/min drift at rest; no measurement on paper; with errors that add up, the autowritten letters drifted 1.5-3 mm apart (SIM, results/sim2j/page_noise.json). The raw 2 s difference is not judged: a held error of sim2j's DeltaPen-like size alone gives a raw 95th percentile of 416 µm with nothing accumulating, and a 5 µm walk step under it gives 70 µm of accumulated drift (SIM, docs/measurement_rig.md s3.6). Was (DEC-049): the accumulated position error over each 2 s, and the window error with no metric named. Proposed on R10 as AC-T04-06 (drift) and AC-T04-02 (window error) | DEC-049 (revisit if the accumulated drift exceeds 0.1 mm per 2 s); DEC-045; DEC-059 (the sim2j page_noise re-run with the measured model) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-J10).
<!-- AC-TABLE:EXP-J10:END -->

- **Decision rule.** Meets autowrite's line: one low-power die for every mode (DEC-045). Meets only the detector's line: the PMW3360-class die for autowrite. Meets neither: the steady mode needs EXP-L01 to back an IMU pre-detector (DEC-045 revisit). Accumulated drift above 0.1 mm per 2 s (DEC-059): revisit DEC-049 (autowrite, guidance and tracing place the ink by the measured position).

### EXP-J11: The 75 µm gimbal under the pull, and shock

- **Purpose and gates.** Test the gimbal that DEC-045 chose: buckling, stiffness under the pull, fatigue and drops. Gates REQ-RVJ-I02 and DEC-045.
- **Rig (study M).** The stiffness against preload (step 1) runs on R12 in EXP-T08 (§47; `docs/measurement_rig.md` §5.3); fatigue and drops stay on R8.
- **Predictions (CALC, `revj1/gimbal.py`).**
  - Buckling 55.3 N (study N's 50 µm strips: 16.4 N).
  - Pivot stiffness 9.4 mN·m/rad unloaded; 19.5, 22.7 and 26.3 mN·m/rad at 12, 16.5 and 22.2 N of axial preload.
  - Goodman safety factor 2.0 at 16.5 N and 1.7 at 22.2 N (1.0 at the crude 36 N), taking full-travel tilt as fully reversed (material LIT AMF-20).
  - A tail-first drop buckles the pivot above 222 g. Buckled strips stay elastic if the rear stop engages within 5 µm of the loaded position (peak strain 0.0045 against 0.0054 at yield), but not at 10 µm.
- **Set-up.** The gimbal (75 µm × 2.55 × 3.8 mm strips crossing at mid-length) with its axial stops; a load frame with a rotary stage and a torque sensor; R8 for the cycling; a 1 m drop rig onto hardwood.
- **Procedure.**
  1. Rotational stiffness at 0, 12, 16.5 and 22 N of axial preload.
  2. Axial load from 0 to 60 N until buckling, on a spare gimbal.
  3. At the pull measured in EXP-J01: 10⁸ tilt cycles of ±0.017 rad about offsets of ±0.086 rad, then 10⁵ full-travel cycles. Stiffness and rest position at every decade.
  4. 1 m drops with the stops fitted, tip-first and tail-first. Stiffness and rest position after each.
- **Measurands.** Stiffness against preload; buckling load; fracture; rest position and stiffness after the drops.

<!-- AC-TABLE:EXP-J11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J11-01 | REQ-RVJ-I02 | 75 µm gimbal (301 full-hard, 2.55 x 3.8 mm strips crossing at mid-length) on a load frame: axial load at buckling as a multiple of the pull measured in EXP-J01, and the Goodman fatigue safety factor at full-travel tilt under the measured pull, recomputed with the measured strip thickness and pull (both) | both met (≥ 2 x the measured pull; ≥ 1.5) | requirement | REQ-RVJ-I02 (DEC-045); prediction buckling 55.3 N against a 12.4-22.2 N pull; safety factor 2.0 at 16.5 N and 1.7 at 22.2 N (1.0 at the crude 36 N) (CALC, revj1/gimbal.py, results/revJ1/gimbal.json; material LIT AMF-20); study N's 50 µm strips buckle at 16.4 N | DEC-045 (revisit if EXP-J01 measures a pull above 27 N: 100 µm x 5 mm strips); DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J11-02 | REQ-RVJ-I02 | Fatigue and shock at the pull measured in EXP-J01: 1e8 tilt cycles of ±0.017 rad about ±0.086 rad offsets and 1e5 full-travel cycles; then 1 m drops onto hardwood, tip-first and tail-first, with the axial stops fitted: fracture, and permanent set of the strips (rest position and stiffness before and after) (all) | all met (no fracture; no permanent set) | requirement | REQ-RVJ-I02 (DEC-045: axial stops so that a 1 m drop leaves the strips elastic); a tail-first drop buckles the pivot above 222 g; buckled strips stay elastic if the rear stop engages within 5 µm of the loaded position (peak strain 0.0045 against 0.0054 at yield) but not at 10 µm; the front stop within 20 µm (CALC; the stops are not yet designed) | DEC-045; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J11-03 | — | Pivot rotational stiffness at 0, 12, 16.5 and 22 N of axial preload against revj1 gimbal.json | within ±20 % of the prediction | hypothesis | pass line of the Rev J.1 study; prediction 9.4 / 19.5 / 22.7 / 26.3 mN m/rad (CALC, co-rotational beam model matching the closed form E b t^3 / (6 L)); the stiffness under the pull costs +3.1 mW of coil power at 1 mm tremor | DEC-045; the nose's coil-power model; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-J11).
<!-- AC-TABLE:EXP-J11:END -->

- **Decision rule.** Buckling below 2 × the measured pull, a fracture, or a strip that takes a set in a drop: 100 µm × 5 mm strips or tighter stops (DEC-045 revisit). Stiffness off by more than 20 %: update `revj1/gimbal.py` and the coil-power numbers.

### EXP-J12: Electronics power

- **Purpose and gates.** Replace the electronics budget, counted from datasheets with assumed duty cycles, by a measurement. Gates REQ-RVJ-I01 through the base load, and DEC-045.
- **Predictions (CALC; duty cycles ASSUMPTION).**
  - nRF54L15 7.9–14.1 mW (CPU at 50–80 %, radio at 3–10 %; MFR OPT-60). The TCN in shadow mode alone takes 28 % of the core (DEC-042).
  - IMU 1.4 mW (MFR OPT-37); two DRV5055 Hall sensors 14.8–29.6 mW (MFR OPT-46); two DRV8214 coil drivers 9.6–14.1 mW (MFR AMF-37); charger, fuel gauge and regulators 0.5–1.0 mW.
  - Total 34.2–60.2 mW (Rev J assumed 77 mW). The page sensor adds 1.3–1.9 mW (EXP-J10).
  - Per-mode totals of the whole pen: 117–150 mW steady without tremor, 230–263 mW at 1 mm tremor, 254–294 mW in lead-through, 539–579 mW in autowrite at 2 mm (`docs/revJ1_design.md` §4.4).
- **Set-up.** The main board (nRF54L15, 2 × DRV5055, 2 × DRV8214, LSM6DSV16X) and the page sensor, running the firmware loop at 2 kHz with the TCN in shadow mode and a BLE log link; the coils and motors on dummy loads; an SMU at 3.7 V (R7). Then the built pen on the EXP-P01 set-up.
- **Procedure.** 10 min in each mode on dummy loads, with the page sensor's current logged apart. Then scripted writing with the built pen in each mode and tremor level.
- **Measurands.** Base electronics power per mode; per-mode total power of the pen.

<!-- AC-TABLE:EXP-J12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J12-01 | — | Base electronics power from the cell at 3.7 V (nRF54L15, 2 x DRV5055, 2 x DRV8214, LSM6DSV16X; the page sensor logged apart) running the firmware loop at 2 kHz with the TCN in shadow mode and a BLE log link, coils and motors on dummy loads, in each mode | ≤ 60 mW | hypothesis | pass line of the Rev J.1 study; prediction 34.2-60.2 mW from datasheets (MFR OPT-60, OPT-37, OPT-46, AMF-37) with a CPU duty of 50-80 % and a radio duty of 3-10 % (ASSUMPTION) -> at the limit at the pessimistic end; Rev J assumed 77 mW | DEC-045 (electronics budget; REQ-RVJ-I01) |
| AC-J12-02 | — | Per-mode total power of the built Rev J.1 pen (EXP-P01 set-up, scripted writing: steady at 0, 0.3 and 1 mm tremor, guide, lead-through, autowrite at 0, 1 and 2 mm) against docs/revJ1_design.md s4.4 | within ±15 % of the prediction | hypothesis | pass line of the Rev J.1 study; prediction 117-150 mW (steady, no tremor) to 539-579 mW (autowrite at 2 mm) (CALC, results/revJ1/budgets.json); every row rests on study N's nose-coil power, and the whole-pen simulation has reported 1.3-2.4 W in some tremor runs (unconfirmed) | DEC-045 (revisit if the nose-coil power is ≥ 2 x study N's model) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J12).
<!-- AC-TABLE:EXP-J12:END -->

- **Decision rule.** Base above 60 mW: lower the CPU or radio duty, and re-count the battery per mode (REQ-RVJ-I01). Per-mode totals off by more than 15 %: update `revj1/power.py`. A nose-coil power ≥ 2 × study N's model: revisit DEC-045.

### EXP-J13: Heat with the graphite spreader

- **Purpose and gates.** Check the spreader that DEC-045 chose, and the model behind the skin rule. Gates REQ-RVJ-N03, REQ-THM-001 and DEC-045. It uses EXP-J05's heated shell.
- **Rig (study M).** Runs as part of EXP-T15 on R13 (§47; `docs/measurement_rig.md` §6.3).
- **Predictions (CALC, fin model).**
  - The 0.1 mm graphite sheet (z 80–110, in a 0.1 mm recess of the shell wall; 600–800 W/mK in plane, MFR AMF-158) cuts the resistance from 99.6 to 32.9 K/W.
  - In a 30 °C room the web reaches 35.9 °C at 1 mm tremor (0.18 W) and 43.7 °C in autowrite with 2 mm tremor (0.42 W).
  - The coils may dissipate 0.395 W for 43 °C and 0.334 W for 41 °C. No heat into the hand is counted, so the model is conservative.
- **Set-up.** EXP-J05's PEEK shell with a heater in place of the coil plate (0.06–0.42 W) and the graphite sheet in its wall; 23 °C and 30 °C rooms; still air; with and without a 33 °C hand phantom; an IR camera and thermocouples.
- **Procedure.** 30 min at each power, room and phantom condition; read the web and the other held surfaces.
- **Measurands.** Web temperature; web rise per watt; other held surfaces.

<!-- AC-TABLE:EXP-J13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J13-01 | REQ-RVJ-N03 | Web surface temperature over the coil plate, PEEK shell with the 0.1 x 30 mm graphite sheet in its wall and a heater in place of the plate, still air, 30 min, 30 °C room: at 0.18 W (1 mm tremor) and at 0.39 W (the proposed firmware cap on the coil loss) (both); guarded acceptance | both met (≤ 41 °C at 0.18 W; ≤ 43 °C at 0.39 W) | derived | REQ-RVJ-N03 and REQ-THM-001 (DEC-045: 43 °C absolute in a rated 30 °C room, 41 °C design target), applied at the coil loss of 1 mm tremor and at the cap; prediction 35.9 °C at 0.18 W, and 43 °C is reached at 0.395 W (41 °C at 0.334 W) (CALC, fin model, docs/revJ1_design.md s5.3) -> at the limit at the cap | DEC-045 (heat); DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J13-02 | — | Web rise per watt with the graphite sheet (0.06-0.42 W, 23 and 30 °C rooms), without and with a 33 °C hand phantom, against the fin model | within ±20 % of the prediction | hypothesis | prediction 32.9 K/W from the spreader to the room with the sheet, 99.6 K/W bare (CALC, fin model; no heat into the hand counted, so the phantom should lower the rise); ±20 % engineering judgement, as AC-J01-01 | DEC-045; the thermal model behind REQ-RVJ-N03; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J13).
<!-- AC-TABLE:EXP-J13:END -->

- **Decision rule.** Above 41 °C at 0.18 W or above 43 °C at 0.39 W: a lower firmware cap on the coil loss, or a longer sheet (40 mm gives 27 K/W) (DEC-045). Safety-related: guarded acceptance (§0.5).

### EXP-J14: K_m and pull with the 1.5 mm back iron

- **Purpose and gates.** Check that the thinner back iron costs no force. Gates DEC-045 (the plate) and, through K_m, REQ-RVJ-N02.
- **Rig (study M).** Runs on R12 in EXP-T07 (K_m) and EXP-T08 (pull) (§47; `docs/measurement_rig.md` §5.3).
- **Predictions (CALC, ideal iron; crowding factor 1.5 ASSUMPTION).** Each pole passes 2.35 × 10⁻⁵ Wb, half through each return path: about 1.24 T mean in 1.5 mm of Hiperco and 1.9 T at the crowded peak, against 2.4 T at saturation (MFR AMF-140). The thinner plate saves 2.7 g. Ideal iron does not saturate: if the real plate does, flux, pull and K_m fall together.
- **Set-up.** The EXP-N01 and EXP-J01 coupons with a 2.37 mm and a 1.5 mm Hiperco plate; the R4 force map; the EXP-J01 load-cell stage for the pull; a Hall probe at the plate rim.
- **Procedure.** Force map per axis over the stroke with each plate; axial pull over the gap; field at the plate rim.
- **Measurands.** K_m with the thin plate as a fraction of the thick plate's; pull; rim field.

<!-- AC-TABLE:EXP-J14:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J14-01 | — | Force constant K_m of the C1S coupon with the 1.5 mm Hiperco back iron as a fraction of that with the 2.37 mm plate (same coupon, R4 force map, both axes, lowest point of the map) | ≥ 0.97 | hypothesis | pass line of the Rev J.1 study; prediction no loss: about 1.24 T mean and 1.9 T at the crowded peak in 1.5 mm, against 2.4 T saturation (CALC, magpylib with ideal iron, crowding factor 1.5 ASSUMPTION; MFR AMF-140); protects REQ-RVJ-N02 (≥ 0.85 x the design K_m) | DEC-045 (the 1.5 mm plate); DEC-036; DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J14-02 | — | Axial pull of the cap on the 1.5 mm plate over the gap (EXP-J01 stage) against revj1 magnetics.json | within ±20 % of the prediction | hypothesis | pass line of the Rev J.1 study; prediction 16.5 N at the design gap, 12.4-22.2 N by where the iron face is taken (ideal iron does not model the thickness, so saturation would lower the pull together with K_m) (CALC, results/revJ1/magnetics.json) | DEC-045; DEC-050: the C1S nose is a bench research module, not in Rev K |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J14).
<!-- AC-TABLE:EXP-J14:END -->

- **Decision rule.** K_m below 0.97 × the thick plate's: go back to the 2.37 mm plate (+2.9 g with the wiring allowance). Pull outside ±20 %: update `revj1/magnetics.py`.

### EXP-J15 (wear part): Does the clear window stay clear?

- **Purpose and gates.** Check that the hard-coated PC window survives hands, pockets and cleaning. Gates DEC-045 (the window) and, through the view, REQ-RVJ-I06. The writers' part of EXP-J15 is in [`human_study_plan.md`](human_study_plan.md) §20, with the criteria table of the whole experiment.
- **Predictions (LIT, a secondary source).** PC transmits 88–90 % of light. Uncoated it scratches at HB–2H; hard-coated, about like PMMA (2H–4H) (LIT AMF-159). Paper would haze PC or PMMA on the ring, so the ring stays PEEK. No prediction of haze.
- **Set-up.** Coupons of PC with the chosen hard coat; uncoated PC and PMMA as references; a Taber abraser or a steel-wool rig; a pocket-key tumble test; common cleaners; a haze meter.
- **Procedure.** Haze and transmission before and after the abrasion cycles, the key test and wiping with the cleaners.
- **Measurands.** Haze (%); transmission.
- **Criterion.** AC-J15-03, in the table of EXP-J15 (`human_study_plan.md` §20).
- **Decision rule.** Haze above 5 %: another hard coat (DEC-045 revisit).

### EXP-J16: The light end-cap on top of the nose

- **Purpose and gates.** Repeat EXP-K02 with the Rev J.1 end-cap. Gates REQ-EC-002, REQ-EC-003 and DEC-045 (revisited below 10 % at the measured grip split).
- **DEC-051 (2026-09-29).** The end-cap is out of the product; this is its bench comparison against the same mass locked. Its runs are also EXP-W14's driven reaction mass (§50), and AC-T16-01 (REQ-WP-001) judges the G5 gate for any return.
- **Rig (study M).** Runs on R14, the grip simulant on R13's stage, as part of EXP-T16 (§47; `docs/measurement_rig.md` §7.3).
- **Predictions (SIM, study K's model H1 on the Rev H pen and tracker; test seeds 200–203).**
  - The 31.6 g member of the end-cap family, 29.6 g in Rev J.1's packaging (9 mm tungsten slug, 17.3 g): +5.6 / +16.8 / +18.3 % further reduction at grip splits 0.3 / 0.5 / 0.7. Study K's 45 g end-cap gave +8.0 / +18.2 / +19.5 %.
  - The same mass fixed: +12.6 / +11.1 / +6.7 %. So the moving slug adds −7.0 / +5.7 / +11.6 points.
  - Rule R-T1 passes, by 0.6 points at split 0.3. End-cap power 28 mW in the test runs.
- **Set-up.** EXP-K02's rig and conditions, with the 29.6 g end-cap and a fixed dummy of the same mass. The grip-split setting nearest the value that EXP-I01 or EXP-K08 measures.
- **Procedure.** As EXP-K02: nose alone; nose and the same mass fixed; nose and the active end-cap. 10 seeds per condition, in random order.
- **Measurands.** RMS ink error; further reduction against the nose alone; the difference to the fixed mass; stroke; stop impacts; power.

<!-- AC-TABLE:EXP-J16:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J16-01 | REQ-EC-002 | Further reduction of the RMS ink error with the 29.6 g Rev J.1 end-cap (9 mm tungsten slug, DEC-045) on top of the nose, EXP-K02's rig and conditions (8-12 Hz, 1-2 mm), at the grip-split setting nearest the measured split (EXP-I01 or EXP-K08); 10 seeds | ≥ 10 % | requirement | REQ-EC-002 (rule R-T1); prediction +5.6 / +16.8 / +18.3 % at r_rot 0.3 / 0.5 / 0.7 (SIM, study K's model H1 on the Rev H pen, test seeds 200-203; results/revJ1/endcap.json) -> FAILS if the measured split is 0.3 | DEC-045 (revisit if below 10 % at the measured split); DEC-038 |
| AC-J16-02 | REQ-EC-003 | Further reduction with the 29.6 g active end-cap minus that with the same mass fixed, same rig and conditions, at the measured grip split | ≥ 5 points | requirement | REQ-EC-003; prediction -7.0 / +5.7 / +11.6 points at r_rot 0.3 / 0.5 / 0.7 (the same mass fixed +12.6 / +11.1 / +6.7 %; SIM, results/revJ1/endcap.json) -> FAILS at r_rot 0.3 and passes by 0.7 points at 0.5 | DEC-045; DEC-038 (fit the weight or nothing if the weight comes within 5 points) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-J16).
<!-- AC-TABLE:EXP-J16:END -->

- **Decision rule.** Below 10 % at the measured split, or the fixed mass within 5 points: revisit DEC-045 (a heavier end-cap costs the 120 g limit) and DEC-038 (fit the weight or nothing).

### EXP-J17: Static side load and holding power of the nib

- **Purpose and gates.** Measure what the coils pay to hold the ball's static side load, and the holding power of the balanced nib that replaces them. Gates REQ-RVJ-N10, REQ-RVJ-C04 and DEC-046. Until part (b) passes, every Rev J nose power, battery and heat claim stays suspended (DEC-046). It also serves gates G1 and G2 of the independent review (`docs/reviews/2026-09-29_review_response.md` §4).
- **DEC-050 (2026-09-30).** Study B chose the mechanism, so DEC-046 is resolved: B1, a translation nib whose contact-driven counter-face balances the paper's push. Build (b) is B1, and AC-J17-02 carries its CALC. Part (c) is new: study B's EXP-B22, the counter-face on a bench fixture before B1's actuator exists (REQ-BNIB-001, 002, 008 and 016; AC-J17-04…07). DEC-050 is revisited if part (c) measures a residual above 25 % of F_s·cot θ or a face that does not release within 20 ms. Build (a), the C1S nose, stays as the research module's load-path check. The battery and heat claims stay suspended until B1 is measured.
- **Study K (DEC-064, 2026-09-30).** Part (c)'s stage also carries Rev K's counter-face head mock-up, study K's EXP-K23 (§53), and AC-J17-04 and J17-05 judge the head as well as study B's disc. DEC-064 amends REQ-BNIB-002: the face floats ±0.56 mm to follow the ±2.5° wobble of real writing, so the refill travels up to 0.98 mm at 35° (0.58 mm at 75°) before the balance returns. AC-J17-05 now allows 1.0 mm at 35° (0.6 mm at 75°) without a float brake, or 0.25 mm with one; study K's AC-K23-04 (the touchdown travel against REQ-BNIB-002) is this criterion. For the head, study K's Monte Carlo leaves 5.7 mN mean and 11.2 mN at the 95th percentile of side load (5.9 % and 13.6 % of F_s·cot θ; CALC).
- **Study H (DEC-095, DEC-096).** In the first bench build, part (c) runs on R9's frame (study H's counter-face bench, in build B2): study B's face on R9's tilt arc, with a second K3D40 ±2 N under the carrier for the residual side load, in place of the 6-axis cell. Its fixture has no CAD yet. Its residual at the 95th percentile over 35–75° and roll, plus the moving mass's weight across the axis (29.5 mN at 35°, CALC), is the measured load of DEC-096's duty re-run, which chooses DEC-072's fine stage (§55). Parts (a) and (b) need a built nose or nib, so G1 cannot close in the first build.
- **Rig (study M).** This is EXP-T12 part A: the nose module on R9's head, the ball on the force plate at 35, 50 and 75°, 60 s each (§47; `docs/measurement_rig.md` §2.5). The plate measures the side load and friction at the same time, so a miss can be traced to the load (friction, angle) or to the actuator (K_m, lever). The roll and stroke-direction part is EXP-T12 part B on R13; its line is in AC-J17-02.
- **Predictions (CALC, SIM; `docs/revJ_simulation.md` §8).**
  - The refill spring (0.15 N) presses the ball on the paper. At 50° the paper pushes back sideways with F_c·cot θ = 0.126 N. The soft C1S gimbal leaves this to the coils: 9.6 mN·m, or 0.81 A and 1.62 W with K_m 0.656 N/√W on the 11.5 mm magnet arm. At 35° it is 4.7 W, at 75° 0.17 W. It grows with F_c² and cot²θ (CALC).
  - sim2 (writer 0, tremor-free writing): 2.25 W mean. About 1.1 W is this load, 0.7 W the servo reacting to unfiltered Hall noise, and 0.4 W friction and holding (SIM).
  - With 100 K/W and 0.5 J/K (ASSUMPTION), the C1S coil passes 100 °C after about 10 s at 35° and 30 s at 50° (CALC).
  - B1 (DEC-050; CALC, `docs/balanced_nib.md` §1, §4): holding heat at most 1.6 mW at the worst tilt and roll, 3.2 mW with K_m × 0.7, against REQ-RVJ-N10's 0.1 W.
  - The counter-face (part (c); CALC Monte Carlo over 35–75°, all rolls, two inks, six papers, spring ±20 % and the IMU's errors): residual 5.3 mN mean (6 % of the unbalanced 96 mN), 13.1 mN at the 95th percentile, and 16.6 mN pen-up (the moving mass's weight). SIM: the face engaged 99.8 % of the contact time and 6.7 % of the pen-up time. A rolling refill guide (friction 0.005, ASSUMPTION) keeps B1 at 7.3 mW; PTFE sleeves (0.05) double its power, and bare metal (0.1) breaks REQ-RVJ-N10 at 35°.
- **Set-up.** The nib prototype in a tilt fixture over paper at 35°, 50° and 75°; the refill springs to test (0.15 N nominal, and the others); a current probe on each coil; a thermocouple on the coil and coil-resistance thermometry. Two builds: (a) the C1S nose (study N) with a 0.15 N refill spring; (b) the B1 nib of DEC-050. Part (c), before (b): the counter-face (a 6 mm hardened steel disc on a cross-strip flexure, the constant-force strip spring and the follower stop) behind a refill in its carrier, on a new fixture at R12: a tilting stage and a roll ring, a 6-axis cell under the carrier and a high-speed camera; three refills; F_s 0.1–0.7 N.
- **Procedure.**
  1. Ball lifted, nose held centred by the servo as built: coil power for 60 s at each tilt. This is the baseline of gravity holding and sensor noise.
  2. Ball on the paper: coil current, coil power and coil temperature for 60 s at each tilt. Stop any run when the coil reaches 100 °C.
  3. Repeat with each refill spring.
  4. Part (c): at each tilt (35–75°), roll (0–360°), F_s (0.1–0.7 N) and refill, with the ball on the paper, the residual side load at the carrier, the ink force at the ball and the slide force in the refill guide. Then lifts and touchdowns, filmed at high speed with the carrier's cell: the release time and the refill travel to the full balance.
- **Measurands.** Coil current and power with the ball lifted and on the paper; coil temperature against time. Part (c): the residual side load as a share of F_s·cot θ; the pen-up residual 20 ms after a lift and the travel to the full balance at touchdown; the ink force at the ball; the guide's friction coefficient.

<!-- AC-TABLE:EXP-J17:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-J17-01 | — | (a) The C1S nose with a 0.15 N refill spring, ball on paper at 35, 50 and 75°, 60 s each or until the coil reaches 100 °C: steady coil current and coil power, against the static-load model (F_c cot(θ) at the ball on the 76.5 / 11.5 mm lever, K_m 0.656 N/√W); on rig R9's head, with the ball on the force plate, which measures the side load and friction at the same time (the load-path check) | within ±20 % of the prediction | hypothesis | pass line of the whole-pen simulation study; prediction 0.81 A and 1.62 W at 50°, 4.7 W at 35° and 0.17 W at 75° (CALC, results/sim2j/power_split.json); the image-method K_m is an upper bound, so the power may be higher; at 4.7 W the coil reaches 100 °C in about 10 s (CALC, 100 K/W and 0.5 J/K ASSUMPTION); runs on rig R9 as EXP-T12 part A (docs/measurement_rig.md s2.5), where it was proposed as AC-T12-03 (0.81 A and 1.62 W at 50°, each within ±20 %) | DEC-046 (revisit if the static power is far from the CALC: the load path differs from the model); DEC-050: the C1S nose is a bench research module, not in Rev K |
| AC-J17-02 | REQ-RVJ-N10 | (b) The balanced nib B1 of DEC-050 (study B's counter-face nib) with the nominal refill spring and the balance on, ball on paper at 35, 50 and 75°, 60 s each (rig R9), and over roll ±20° and 8 stroke directions (rig R13, EXP-T12 part B): steady coil heat (current and coil resistance; thermocouple on the coil), largest over the tilts, rolls and directions | ≤ 0.1 W | requirement | REQ-RVJ-N10 (DEC-046; the 0.1 W target is an ASSUMPTION); B1 (DEC-050, CALC): holding at most 1.6 mW at the worst tilt and roll, 3.2 mW with 30 % weaker magnets; the C1S nose as it stands takes 4.7 / 1.6 / 0.17 W at 35 / 50 / 75° (CALC) -> fails without a passive bias; part B was proposed as AC-T12-01 with the same 0.10 W against REQ-ACT-002 (the review's provisional allocation for nib motion); REQ-RVJ-N10 is kept (docs/measurement_rig.md s6.3) | DEC-050 (the B1 nib; DEC-046 resolved); the battery and heat claims stay suspended until B1 is measured |
| AC-J17-03 | REQ-RVJ-C04 | Coil loss added by the position-sensor noise: coil power with the ball lifted and the nose held centred by the servo as built (with its position filter), 60 s at each tilt, less the gravity-holding power at that tilt (CALC) | ≤ 50 mW | requirement | REQ-RVJ-C04 (DEC-046: the servo filters its position signal); sim2's unfiltered servo (Hall 5.9 µm rms at 10 kHz): 1.20 W with the ball lifted against 0.31 W without the noise (SIM, results/sim2j/power_split.json); gravity holding 0.8-8.3 mW over 75-35° (CALC, docs/revJ1_design.md s9.3) | DEC-046 (the filtered servo) |
| AC-J17-04 | REQ-BNIB-001 | (c) Counter-face bench (study B's EXP-B22; a new fixture at R12: a tilting stage with a 6-axis cell under the carrier), with study B's face and with Rev K's head mock-up (EXP-K23, DEC-064): residual static side load at the carrier as a share of F_s cot(θ), over tilt 35-75°, roll 0-360°, F_s 0.1-0.7 N and three refills: the mean and the 95th percentile (both) | both met (≤ 10 % mean; ≤ 25 % at the 95th percentile) | requirement | REQ-BNIB-001 (DEC-050, whose revisit trigger is 25 %); CALC Monte Carlo (35-75°, all rolls, two inks, six papers, spring ±20 %, IMU errors): 5.3 mN mean (6 % of the unbalanced 96 mN), 13.1 mN at the 95th percentile (docs/balanced_nib.md s1). Rev K's head (DEC-064, CALC Monte Carlo of 20,000 draws, contributors ASSUMPTION): 5.7 mN mean and 11.2 mN at the 95th percentile (5.9 % and 13.6 %) (docs/revK_design.md s3.4) | DEC-050 (adopt the counter-face, or fall back to b' then f); DEC-064 (the head: revisit above 25 % at the 95th percentile); DEC-072 through DEC-096 (the measured residual load, at the 95th percentile, enters the duty re-run) |
| AC-J17-05 | REQ-BNIB-002 | (c) Release on lift and return at touchdown (high-speed camera and the carrier's force cell), with study B's face and with Rev K's head mock-up (EXP-K23): the pen-up residual as a share of the contact balance force 20 ms after the ball lifts, and the refill travel from touchdown to the full balance, over the tilts and rolls of AC-J17-04 (both) | both met (≤ 10 % within 20 ms; ≤ 1.0 mm at 35° and ≤ 0.6 mm at 75° without a float brake, or ≤ 0.25 mm with one) | requirement | REQ-BNIB-002 as DEC-064 amends it (DEC-050's revisit trigger: a face that does not release within 20 ms); Rev K's head (DEC-064, CALC): the face floats ±0.56 mm, so the refill travels 0.98 mm at 35° and 0.58 mm at 75° before the balance returns (fit check H6, docs/revK_design.md s3.4) -> marginal at 35°; study K's AC-K23-04 (the touchdown travel against REQ-BNIB-002) is this criterion. Study B's face: the follower stop sits 0.25 mm beyond the writing position (a tuned rule, CALC); SIM: the face engaged 99.8 % of the contact time and 6.7 % of the pen-up time (docs/balanced_nib.md s1, s4). Was both met (≤ 10 % within 20 ms; ≤ 0.25 mm) | DEC-050 (b' or f if the face does not release); DEC-064 (the float brake, with AC-K23-05) |
| AC-J17-06 | REQ-BNIB-016 | (c) Friction coefficient of the refill guide under the counter-face's couple (the slide force against the bushing loads, 1.0 / 0.6 / 0.19 N in all at 35 / 50 / 75° by CALC), at the three tilts | ≤ 0.01 | requirement | REQ-BNIB-016; ASSUMPTION mu_g 0.005 (a rolling guide): B1 at 7.3 mW; PTFE sleeves (0.05) double B1's power and bare metal (0.1) breaks REQ-RVJ-N10 at 35° (CALC, docs/balanced_nib.md s5.2) | the refill guide's design (DEC-050) |
| AC-J17-07 | REQ-BNIB-008 | (c) Ink force at the ball with the balance engaged (R9's plate, or the fixture's cell), over 35-75°, at the set value of the refill spring | within ±20 % of the set value | requirement | REQ-BNIB-008 (DEC-050); with the face engaged the paper-normal force equals the face's push (CALC); the set value comes from EXP-T02 (REQ-BNIB-014) | the spring's set value in config/nib.yaml (DEC-050) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-J17).
<!-- AC-TABLE:EXP-J17:END -->

- **Decision rule.** (a) More than 20 % off the model: the load path differs from the model; re-run `python3 -m sim2j.run_study --stages power_split` with the measured values and revisit DEC-046. (b) Above 0.1 W at any tilt: study B's mechanism fails; re-size the actuator or limit the angle range (DEC-046 revisit). Noise loss above 50 mW: filter the position signal harder (REQ-RVJ-C04). (c) A residual above REQ-BNIB-001's lines, or a face that does not release within 20 ms: DEC-050's revisit (the clutched bias b', then the unbalanced nib f). Guide friction above 0.01: a rolling guide before B1 is built. With Rev K's head, a residual above 25 % of F_s·cot θ at the 95th percentile is DEC-064's revisit, and touchdown ink above AC-K23-05's line fits the float brake.

---

## 47. Measurement rigs R9–R14, study M: EXP-T01…T17

### Purpose and what it gates

The independent review of 29 September 2026 asks for experiments that decide the design (its §12, gates G1–G5; the lead's response §4). Study M specifies six rigs for them, around one data-acquisition box, in `docs/measurement_rig.md`. The CAD, the DAQ firmware, the logger and every analysis are in `rig/`, `mechanics/cad/rig_*.py` and `results/rig/`. **Nothing has been built or measured.** The analyses were checked on synthetic data only (SIM, `python3 -m rig.selftest`), and the firmware was written but not compiled for its board or run.

| Rig | What it is | Gate | Takes over from | Spec |
|---|---|---|---|---|
| DAQ-1 | Teensy 4.1 with a 24-bit simultaneous-sampling ADC (ADS131M08), encoder inputs, a camera trigger and a coded sync pulse: every instrument on one clock | all | — | `docs/measurement_rig.md` §1 |
| R9 | Contact and ink rig on a CoreXY printer frame whose bed does not move in x–y: a 3-axis force plate under the paper (K3D40) and an in-line axial cell (LSB200) behind a leaf-guided refill, with F_c set by a voice coil | G1, and G2's static part | R1 for G1 (DEC-058) | §2 |
| R10 | Page-sensor rig on the same frame: tilt arc, roll ring ±20° and fine height; truth from linear encoders (LM13), Zaber stages or a strobed camera | sensing build gate | R5 for page sensing | §3 |
| R11 | Recording pen and tablet protocol: an EMR tablet with an inking pen and a browser recorder (no build), then a passive pen with an axial cell and an IMU, with the paper on R9's plate | EXP-H01 | — | §4 |
| R12 | Actuator coupon bench: the stator on a K3D40, the magnet part on a 3-axis micrometre stage and a goniometer centred on the pivot; a heated box | G2 | R4 for coupons | §5 |
| R13 | Loaded-nib rig: a parallel-leaf disturbance stage driven by a voice coil in closed loop, one axis then two; a nib holder with a roll ring and a tilt arc; the paper on R9's plate | G3, then G4 | R2 for loaded nibs | §6 |
| R14 | Grip simulant on R13's stage: three padded fingers with a set squeeze; translation and rotation stiffness set by leaves and strips | G5 | — | §7 |

- **Conventions.** §0 applies: frozen predictions (§0.2), frames (§0.3), the decision rules (§0.5: simple acceptance at TUR ≥ 4, otherwise guarded), blind ink scans (§0.6) and the record rules of `records/README.md`. R3 (ink scans), R7 (electronics) and R8 (fatigue) are used as in §0.9.
- **DEC-058.** Gate G1 is measured on R9. EXP-B01's single F/T sensor on the pen holder is retired for G1, because it cannot separate the axial and the paper-normal forces. The decision is revisited if the closure check AC-T01-01 fails persistently, or if the plate's first mode (tap test) is below 100 Hz.
- **DEC-059.** Page-sensor acceptance compares like with like. The DeltaPen comparison uses DeltaPen's own metric per 10 ms window, the absolute difference of the translation lengths, with the vector difference reported beside it. Drift is judged on the accumulated (walking) part of the error, fitted from the structure function, not on raw 2 s differences (AC-J10-04, REQ-RVJ-C05).
- **One id per experiment.** EXP-T12 part A is EXP-J17, which keeps its id; EXP-T12 covers part B only. The existing experiments keep their ids and criteria and run on the rigs; each names its rig and EXP-T experiment in one line. The table below lists them all.
- **One id per check.** Where a proposed criterion had the same requirement, threshold and measured quantity as an existing one, under the same conditions, the existing id is kept and notes the rig. The second table lists the nine merged ids. The other 41 proposed criteria keep their proposed ids (`results/rig/proposed_criteria.csv`), so the numbering has gaps.
- **Order of building** (spec, "The answer in plain words"): DAQ-1; R9; R10 and the tablet protocol; then R12, R13 and R14 as study B's parts arrive.

### Where the existing experiments run

From `results/rig/experiment_merge_map.csv` (42 rows), with three more parts named in `results/rig/proposed_experiments.csv` (EXP-F01, F02, P01). The last five rows are studies S and W (§49, §50). Study B's experiments are placed in §51.

| Existing | Rig | Runs as | Note |
|---|---|---|---|
| EXP-B01 | R9 | re-specified by DEC-058: Parts 1–2 in EXP-T01, Part 4 in EXP-T02, Part 3 in EXP-T03 | the plate under the paper and the in-line axial cell replace the F/T sensor on the holder |
| EXP-B02 | R9 + R13 stage | EXP-T03 (optional, after G1) | `s2r.exp_b01b02.identify` reads the records unchanged |
| EXP-B08 | R9 | the modulated-force part of EXP-T02 | |
| EXP-Q01 | R9 | EXP-T01, with a skid head | criteria unchanged |
| EXP-Q02 | R9 | Part A in EXP-T02 | Part B needs a skid nose |
| EXP-V01 | R9 | EXP-T01 | the Rev H lip is one more head |
| EXP-D01 | R9 | EXP-T01, with a wheel head | the same six papers |
| EXP-J17 | R9 frame | is EXP-T12 part A | keeps its id; the plate measures the side load as well |
| EXP-S01 | R10 | accuracy and noise in EXP-T04; latency in EXP-T05 | the strobe method stays an option |
| EXP-B04 | R10 | the optical scale (procedure 5) in EXP-T04 | the Hall calibration stays with the nib build |
| EXP-N07 | R10, R13 | EXP-T04 (the sensor); EXP-T14 (in the pen) | |
| EXP-J04 | R10 | EXP-T04 | height and roll band |
| EXP-J10 | R10 | EXP-T04, with power logging | its addition is `rig.pagesense.sim2j_page_model`, judged by AC-J10-04; AC-J10-03 unchanged |
| EXP-H01 | R11 | instrumented by R11; EXP-T06 qualifies it | the study itself is unchanged |
| EXP-V03 | R11 | its inputs come from R11's recordings | |
| EXP-V07 | R11 (tablet) | on the tablet protocol once AC-T06-04 shows ≥ 200 Hz | the recorder's CSV goes through `rig.tablet.load_recording` into `sim2j/writers.kinematics`; consent as EXP-H01 |
| EXP-B03 | R12 | force map, back-EMF, R and L in EXP-T07; thermal steps in EXP-T08; crosstalk in EXP-T09 | R12 takes study B's coupons too |
| EXP-N01 | R12 | EXP-T07 | |
| EXP-J01 | R12 | EXP-T08 | |
| EXP-J03 | R12 | EXP-T09 | AC-J03-01 also needs the heel motors and the brake |
| EXP-J11 | R12, R8 | the stiffness against preload (step 1) in EXP-T08 | fatigue and drops stay on R8 |
| EXP-J14 | R12 | EXP-T07 (K_m) and EXP-T08 (pull) | |
| EXP-K01 | R12 | the force-constant part in EXP-T07 | the net force on the housing stays its own test, on a clamp fixture at R12, not in EXP-T16 (the lead, `prototype_stages.md` §0) |
| EXP-B07 | R12, R13 | the coupon part in EXP-T08; the pen part in EXP-T15 | |
| EXP-I05 | R13, R12 | bandwidth and tremor rig (procedure 3–4) in EXP-T10; K_m in EXP-T07 | |
| EXP-N03 | R13, R12 | the closed loop in EXP-T10; the modes in EXP-T08 | |
| EXP-B05 | R13 | the in-contact FRF and margins in EXP-T10 | the free-space parts stay with the nib build; the `s2r.exp_b05` methods are unchanged |
| EXP-B09 | R13 | one-axis precursor EXP-T10; two-axis EXP-T13 | REQ-VAL-001's elements kept |
| EXP-Q06 | R13 | EXP-T10, with the pencil stage in the nib holder | |
| EXP-N05 | R13 | step 4 in EXP-T11 | the module's life test stays |
| EXP-Q08 | R13 | EXP-T11 | |
| EXP-F01 | R13 | over-current in contact in EXP-T11 | not in the merge map |
| EXP-N02 | R13 | EXP-T13 | |
| EXP-N08 | R13 | after EXP-T13 | |
| EXP-V05 | R13 | its bench part, after EXP-T13 | predictions frozen first (§0.2) |
| EXP-F02 | R13 | the page-sensor faults in EXP-T14 | not in the merge map |
| EXP-N04 | R13 | EXP-T15 | |
| EXP-J05 | R13 | EXP-T15, the heater shell first | |
| EXP-J13 | R13 | EXP-T15 | |
| EXP-P01 | R13 | the nib-power part in EXP-T15 | not in the merge map |
| EXP-I06 | R14 | EXP-T16 | |
| EXP-K02 | R14 | EXP-T16 | |
| EXP-J16 | R14 | EXP-T16 | |
| EXP-K07 | R14 | EXP-T16 (the rotor condition) | only if a rotor is kept |
| EXP-I04 | R14 | superseded by EXP-T16 | as EXP-I06 superseded it for Rev H |
| EXP-W11 | R14, R9 plate | its G5 part in EXP-T16 (the collar condition) | the transmission, holding power, fit and stops are its own runs (§50) |
| EXP-W13 | R13, R9 plate | in EXP-J17's and EXP-T12's set-up; extends EXP-T11's ladder | §50 |
| EXP-W14 | R14 | EXP-T16 (the tail conditions) | its driven reaction mass is EXP-J16's end-cap |
| EXP-S16 | R14, R13 | EXP-D08's tracing task on the grip simulant | §49 |
| EXP-S19 | R13 | with EXP-N08, after EXP-T13 | §49 |

### Proposed criteria kept under existing ids

| Proposed id | Kept id | The same check |
|---|---|---|
| AC-T01-03 | AC-B01-03 | the P-6 model check over the map, re-stated for F_c set and N measured (DEC-058) |
| AC-T01-06 | AC-B01-20 | coverage of REQ-ENV-002's envelope, 100 %; EXP-T01's own F_c grid (0.08–0.30 N) gives N of only about 0.1–0.7 N, so EXP-B01's grid on R9 covers 0.2–2.0 N |
| AC-T04-02 | AC-J10-04 | REQ-RVJ-C05: the error per 10 ms window by DeltaPen's metric (DEC-059) |
| AC-T04-06 | AC-J10-04 | REQ-RVJ-C05: the accumulated error ≤ 0.1 mm over 2 s (DEC-059) |
| AC-T04-04 | AC-S01-02 | REQ-SNS-001: per-sample noise ≤ 5 µm RMS on matte paper at 35–75° |
| AC-T06-01 | AC-H01-08 | the reference chain against the scanned ink, ≤ 50 µm RMS |
| AC-T09-02 | AC-B03-07 | REQ-SNS-004: current crosstalk ≤ 5 µm/A after compensation, 9 positions, DC and PWM |
| AC-T12-01 | AC-J17-02 | the balanced nib's static coil heat ≤ 0.1 W; the proposal named REQ-ACT-002, REQ-RVJ-N10 is kept, and part B's roll and stroke directions are added |
| AC-T12-03 | AC-J17-01 | the C1S nose's static current and power within ±20 % of the model (the proposal judged 50° only; AC-J17-01 judges every tilt) |

**Kept apart**, because the rig line adds a new load case, condition or article: AC-T01-04 (μ at F_c 0.15 N; AC-B01-04 is at N 1 N); AC-T02-03 (REQ-MECH-005; AC-Q02-02 is the pencil's refill); AC-T04-01 and AC-T05-01 (REQ-RVJ-N06 on the bare sensor; AC-J04-01, J10-01 and N07-01 on the nose insert or in the pen); AC-T04-05 (with AC-S01-04 and S01-05); AC-T07-01, T07-03 and T08-01 (study B's coupon; AC-N01-01, N01-02 and J01-01 are the C1S's); AC-T08-03 (REQ-RVJ-N02 at temperature; AC-N03-01) and AC-T10-02 (REQ-RVJ-N02 in contact, REQ-BNIB-006 since DEC-050); AC-T09-01 (REQ-RVJ-I04 on R12, without the heel motors and brake of AC-J03-01); AC-T10-03 (with AC-B05-06/07 and AC-N03-02); AC-T11-03 (with AC-N05-03); AC-T13-02 (with AC-B09-06/07); AC-T15-01 and T15-02 (the balanced nib with the governor; AC-N04-01 and AC-B07-03); AC-T16-01 and T16-02 (three grip strengths; AC-K02-02/03 and AC-J16-01/02). Since DEC-050, AC-T02-01, T07-01, T10-02, T11-03 and T15-01 judge the B1 nib against study B's lines (§51); their old lines are in their bases.

**Statuses brought in line with the status rule of [`README.md`](README.md) §2** (requirement only when the threshold is the linked requirement's own): AC-T10-03 (45°, stricter than REQ-CTRL-002's 40°), AC-T11-03 and AC-T14-01 are derived; AC-T16-01 (the review's 10 %, where REQ-EC-003 asks 5 points) was made a hypothesis; REQ-WP-001 (DEC-051, DEC-053) has since made the 10 % a requirement, with coverage, and AC-T16-01 is now its requirement criterion. AC-T02-01's threshold now starts with its number. Rows with no requirement (rig validity, model checks) keep an empty requirement id; the checker allows it.

### Open items

- No rig exists (the spec is `docs/measurement_rig.md`). The DAQ firmware is written but not compiled for its board or run; its bring-up comes first (spec §1.3; §11 items 1 and 3).
- EXP-B01 on R9: the 4 N level needs a larger in-line cell than the 250 g LSB200 at most tilts, and the spec names no sensor for the indentation of Part 1 (AC-B01-08). Both are open for the rig design, to be specified before R9 is built (`prototype_stages.md` §0).
- Friction at the lowest ink forces has a TUR of 1.4 on the K3D40 plate: guarded acceptance, or a finer tangential stage (spec §11 item 6).
- The LM13 encoders' sub-divisional error is unknown, so page-sensing verdicts on LM13 truth are guarded until it is qualified; the camera truth rests on assumed centroid noise and distortion (spec §11 items 4–5).
- The excess-power method needs a variant for sentence copying (spec §11 item 7).
- R13 hung from the printer head would weigh about 1.06 kg, so it hangs from a bridge until the head is shown to carry it; its 2 mm sines at 25–30 Hz exceed the coil's continuous rating (spec §11 items 10–11).
- The sim2j page-noise re-run with a measured model is left to sim2j's owner (spec §11 item 14).

### EXP-T01: Axial and paper-normal force apart; friction vector map; static side load

- **Rig and gate.** R9. Gate G1 (DEC-058). Requirements: REQ-ENV-001, REQ-ENV-002, REQ-ACT-001, REQ-RVJ-N05.
- **Measures.** The axial force F_c (in-line cell) and, apart from it, the paper-normal force N and the friction vector f (plate under the paper), at θ 35, 50, 65 and 75°, 8 stroke directions, 1–100 mm/s and F_c 0.05–0.5 N; indentation.
- **Decision it enables.** The static balance range the nib must carry per newton of F_c (study B); the friction parameters of sim2; whether P-6 and P-7 hold.
- **Procedure.** Nominal pair (a ballpoint D refill on copy paper, hard underlay): θ 35, 50, 65 and 75° × 8 directions × v 3, 10, 30 and 100 mm/s × F_c 0.08, 0.15 and 0.30 N, 20 mm strokes on fresh tracks, 3 repeats with 3 refills. A reduced grid on the other 23 refill × paper pairs. Indentation ramps 0 → 2 → 0 N on each paper and underlay. The plate and the cell are calibrated in situ at every test angle; the closure check (F_c against the plate force on the pen axis, P-7) runs live. The main output is not a pass: it is R⊥/F_c per tilt, direction and speed, handed to study B.
- **Existing experiments it runs.** EXP-B01 Parts 1–2 (re-specified), EXP-V01 (the Rev H lip), and EXP-Q01 (skid) and EXP-D01 (wheel) as other heads. Study B's EXP-B21 (DEC-050): the friction vector map and the six-paper spread, which go into `config/nib.yaml` (REQ-BNIB-013).
- **Criteria.** Its own are below. AC-B01-03 and AC-B01-20, proposed here as AC-T01-03 and AC-T01-06, stay with EXP-B01.
- **Study H (DEC-095).** EXP-T01 runs after EXP-T02 in the first build. With its ±2 N plate and 100 g cell (F_c ≤ 0.5 N), N reaches about 0.5 N at 75° and 0.7 N at 35° (CALC). That covers this grid (F_c 0.08–0.30 N), but not AC-B01-20's 0.2–2.0 N envelope, which waits for the 250 g cell and the ±10 N plate (`docs/bench_build_plan.md` §4.5). Without encoders the head's position comes from the commanded path and a marker the printer toggles at each stroke start; no helper for this exists yet. No coupon geometry is frozen before this side load and EXP-T02's F_c,min are known.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §2.2–§2.7.

<!-- AC-TABLE:EXP-T01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T01-01 | — | Axial closure: median over steady strokes of \|F_c - R.a\|, F_c from the in-line cell (guide force subtracted), R.a from the plate forces projected on the pen axis | ≤ max(3 mN, 3 % of F_c) | derived | Rig validity: two independent sensors must agree on the axial balance (P-7); synthetic check 0.13 mN (SIM, rig.selftest) | validity of every EXP-T01/T02 verdict |
| AC-T01-02 | — | Expanded uncertainty (k = 2) of the paper-normal force N over 0.05-1 N from the ±2 N plate after in-situ calibration | ≤ 5 mN | derived | EXP-Q02 target U(N_nib,min) ±5 mN; budget 3.6 mN (CALC, rig.uncertainty, MFR AMF-224) | EXP-T02 verdicts |
| AC-T01-04 | — | Kinetic friction coefficient mu_drag (steady sliding, 30 mm/s, 50°, F_c 0.15 N) for every refill x paper | within 0.09-0.40 | hypothesis | AC-B01-04 range (CON-13, CON-14) | config writing.mu_eff range; study B FRICTION table |
| AC-T01-05 | — | Side component of friction: \|mu_cross\| / mu_drag (friction vector off the drag direction), per refill x paper x tilt | ≤ 0.2 | hypothesis | ASSUMPTION of every model so far (friction opposes the velocity); if larger, the balance needs a direction-dependent term | study B balance mechanism (b) or (c) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-T01).
<!-- AC-TABLE:EXP-T01:END -->

### EXP-T02: Minimum reliable ink force and ink continuity

- **Rig and gate.** R9 with R3 scans. Gate G1. Requirements: REQ-BNIB-014 (DEC-050), REQ-RVJ-N05 (the C1S module's), REQ-PNC-002, REQ-MECH-005, REQ-ENV-001.
- **Measures.** The gap fraction along force-ramp and fixed-force lines, for at least three refill types (four ink systems proposed) × six papers × 35/50/75° × 10/30/100 mm/s × 5 repeats; line width and density.
- **Decision it enables.** F_c,min per refill and paper; the refill choice; the bottom of the static balance range.
- **Procedure.** Five lines of 100 mm with F_c ramped 0.30 → 0.02 N, then 100 mm lines at fixed F_c of 0.05, 0.08, 0.10, 0.12, 0.15 and 0.20 N around the threshold. Optionally ±0.03 N of modulation at 3–15 Hz from the voice coil (EXP-B08's part). Sheets are scanned within 1 h and coded blind (§0.6). The threshold is the force where the gap fraction first exceeds 1 % (AC-B01-07's definition); the fixed-force lines confirm it, because the estimate from a ramp is biased low by up to half the force span of a window.
- **Existing experiments it runs.** EXP-B01 Part 4; EXP-Q02 Part A; EXP-B08 (the modulated-force part, optional); study B's EXP-B20 (DEC-050).
- **Study B (DEC-050).** EXP-B20 adds five tip types (two D1 oil refills, a gel, a rollerball and a fineliner) and the speeds 5 and 60 mm/s, since REQ-BNIB-014 asks 5–60 mm/s. Rev K's refill spring force is frozen only after this. AC-T02-01 now judges DEC-050's revisit line: a minimum reliable force above about 0.3 N for Rev K's refill, where B1's power passes 30 mW (about 184 mW at 0.69 N, CALC). AC-T02-04 is the report per tip type and paper that REQ-BNIB-014 asks. No source gives a minimum for any tip type: 0.15 N is 4.6 × below the lowest maker's test load found (0.69 N at 70°, LIT CON-97).
- **Study H (DEC-095).** EXP-T02 runs first in the first build, before EXP-T01. If the voice coil is late, dead weights set F_c: fixed-force lines only, with no ramps and no modulation, so AC-T02-03 waits for the voice coil. No coupon geometry is frozen before F_c,min is known.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §2.4–§2.7.

<!-- AC-TABLE:EXP-T02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T02-01 | REQ-BNIB-014 | Lowest axial force F_c,min with gap fraction ≤ 1 % (AC-B01-07 definition) at every θ 35/50/75°, speed 5/10/30/60 mm/s (study B's EXP-B20 range; 100 mm/s reported) and paper (6), for the refill chosen for Rev K (a D1 refill, the brand chosen in G1; every type of study B's EXP-B20 set is reported: two D1 oil refills, a gel, a rollerball and a fineliner) | ≤ 0.3 N | derived | DEC-050's revisit trigger (a minimum reliable force above about 0.3 N: B1's power then passes 30 mW, and reaches about 184 mW at 0.69 N; CALC), so derived; at 0.3 N B1's continuous power (about 30 mW) is already above REQ-BNIB-004's 20 mW; no source gives a minimum: 0.15 N is 4.6 x below the lowest maker's test load found (0.69 N at 70°, LIT CON-97); the speeds follow EXP-B20 (5-60 mm/s). Was ≥ 3 refill types with F_c,min ≤ 0.12 N at 10/30/100 mm/s, the low end of REQ-RVJ-N05's 0.15 N ±20 % (the C1S drum spring; the static side load scales with F_c, review section 4) | the F_s set point (DEC-050); refill choice |
| AC-T02-02 | — | Expanded uncertainty (k = 2) of F_c,min per cell (in-line cell + threshold statistics, bootstrap over 5 lines) | ≤ 12 mN | derived | EXP-Q02 decision rule (TUR 4 against 0.05 N); axial budget 1.9 mN (CALC) | simple vs guarded acceptance of AC-T02-01 |
| AC-T02-03 | REQ-MECH-005 | Gap fraction at the selected F_c with ±0.03 N modulation at 3, 6, 9, 15 Hz from the voice coil, every paper, 30 mm/s | ≤ 1 % | hypothesis | AC-Q02-02 / AC-B08 analogue | spring rate and bore friction of the ink-force element |
| AC-T02-04 | REQ-BNIB-014 | Report before the refill spring force is frozen (review): the minimum reliable ink force F_c,min (gap fraction ≤ 1 %) per tip type (two D1 oil refills, a gel, a rollerball and a fineliner; study B's EXP-B20) and per paper (six), over 35-75° and 5-60 mm/s, with its uncertainty (AC-T02-02) | conforms | requirement | REQ-BNIB-014 (DEC-050: the spring force is frozen only after G1); no source gives a minimum for any tip type (docs/balanced_nib.md s5.4) | the F_s set point in config/nib.yaml (DEC-050) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-T02).
<!-- AC-TABLE:EXP-T02:END -->

### EXP-T03 (optional): Friction dynamics at tremor amplitudes

- **Rig and gate.** R9 with R13's disturbance stage on its head. Gate G1, optional, after EXP-T01 and T02. Model validation P-9.
- **Measures.** Reciprocation of 0.02–0.5 mm at 3–15 Hz, with and without drift; velocity steps at quarter-decade speeds; slow triangular sweeps of 5 µm–1 mm.
- **Decision it enables.** LuGre or multi-state friction in sim2 (DEC-011, DEC-040).
- **Procedure.** As EXP-B01 Part 3 and EXP-B02, with the load path of DEC-058. `s2r.exp_b01b02.identify` analyses the `s2r-bench-1` records unchanged.
- **Existing experiments it runs.** EXP-B01 Part 3; EXP-B02.
- **Criteria.** None of its own: EXP-B02's (AC-B02-01…05) judge it.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §2.5–§2.6.

### EXP-T04: Page-relative sensing: accuracy, noise, scale, working band, dropout

- **Rig and gate.** R10. The sensing build gate of the review. Requirements: REQ-SNS-001, REQ-SNS-002, REQ-RVJ-N06, REQ-RVJ-I07, REQ-DRV-005, REQ-RVJ-C05 (DEC-059), REQ-BNIB-017 (DEC-050).
- **Measures.** The sensor against encoder (or camera) truth: DeltaPen's 10 ms window errors (the magnitude metric, judged, and the vector metric, reported), per-sample noise, stroke error after calibration, scale and rotation against tilt, height and roll, and dropouts; six papers plus glossy paper, printed text and fresh ink; with tremor added.
- **Decision it enables.** Whether ordinary-paper sensing is good enough to replace external truth; which die and optics; which papers are supported.
- **Procedure.** Poses θ 35–75° in 10° steps × roll 0, ±5, ±10 and ±20° × heights about the band centre (then 1.5–4.5 mm in 0.25 mm steps at 55°) × the papers. Straight lines at 1–200 mm/s in 8 directions, 5 mm circles, and writing-like paths with 4–12 Hz, 0.1–1 mm tremor added; 10 s rests for noise. Lift steps of 0.1–3 mm; a glossy strip and an ink crossing in the path. Mode A holds the bare die, lens and a small carrier; mode B holds the nose insert as in the pen (EXP-J04, J10). `rig.pagesense.qualify` fits the latency and a 2 × 2 scale-rotation matrix on the first 30 % of each run and scores the rest. EXP-J10's addition: `rig.pagesense.sim2j_page_model` fits the structure function of the 10 ms window errors, V(L) = 2·E|h|² + L·E|w|², which separates the held part h from the walking part w, and exports the page-noise model in sim2j's form; `patch_sim2j` loads it into sim2j for one run, which sim2j's owner makes. The sensor's supply current is logged at each polling mode (AC-J10-03).
- **Existing experiments it runs.** EXP-S01 (accuracy and noise); EXP-B04 procedure 5 (optical scale); EXP-N07 (the sensor); EXP-J04 (height and roll band); EXP-J10, with its addition; study B's EXP-B32 (DEC-050).
- **Criteria.** Its own are below. AC-J10-04 (the window error and the accumulated drift, proposed here as AC-T04-02 and AC-T04-06) and AC-S01-02 (per-sample noise, AC-T04-04) stay with their experiments. With LM13 truth the TUR against 10 µm is 3.8, so verdicts near that line are guarded until the encoder's sub-divisional error is qualified.
- **Study B (DEC-050).** EXP-B32 runs here at G4, with Rev K's page sensor in its place and the nib moving. The window errors, scale and drift refit sim2's DeltaPen-calibrated page model (with EXP-R07). The lift steps give the height at which the sensor loses and regains the page (AC-T04-07; REQ-BNIB-017: ≥ 2 mm). SIM: with a 0.8 mm cut-off B1's tracker left 0.87 of the tremor instead of 0.83. DEC-050 is revisited if the sim2 ranking reverses with the page sensor measured on paper.
- **Study K (DEC-062, DEC-065).** Rev K puts the page sensor at the bottom of a 6.0 mm skid ring, where its lens stays in the band up to 21° of roll (AC-T04-01). Its PMW3610-class die tracks only ±0.2 mm of lens height (MFR OPT-61), against REQ-BNIB-017's 2 mm (fit check F5), so AC-T04-07 is predicted to fail with a mouse-class die. REQ-BNIB-017 stays the selection requirement, and this experiment chooses the die and optics (DEC-062). The heel module's front puts the sensor beside the pod, where it tolerates 0.5° of roll (CALC, fit check V1); the module goes into a pen only if a sensor there keeps the page over ±20° of roll (AC-T04-08, DEC-065).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §3.2–§3.7.

<!-- AC-TABLE:EXP-T04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T04-01 | REQ-RVJ-N06 | Held-out stroke error after the per-pose 2x2 calibration, report rate: at tilt 35-75°, roll ±20°, six papers, in the sensor's height band (both) | ≥ 1 kHz and ≤ 10 µm RMS | requirement | REQ-RVJ-N06; synthetic check 3.8 µm per-sample (SIM); Rev K's base front (DEC-062): the lens stays in its band up to 21° of roll with the sensor at the bottom of the ring (CALC, fit check F4 marginal); beside the heel module's pod 0.5° (AC-T04-08) | page sensor choice; DEC-036 revisit trigger |
| AC-T04-03 | — | Ground-truth expanded uncertainty per 10 ms window (encoder or camera), from the truth qualification | ≤ 2.5 µm | derived | TUR ≥ 4 against 10 µm (section 0.5); Zaber build 0.38 µm, LM13 2.6 µm, camera 2.1 µm (CALC, partly ASSUMPTION) | simple vs guarded acceptance of AC-T04-01 |
| AC-T04-05 | REQ-SNS-002 | Dropouts during writing motion in the height band: invalid fraction and events longer than 300 ms per 10 min | ≤ 1 % and 0 events | hypothesis | AC-S01-05 (ICD fault bit 4 at 300 ms) | optics layout; authority fade |
| AC-T04-07 | REQ-BNIB-017 | Lift cut-off of the page sensor chosen for Rev K, in its place with the nib moving (study B's EXP-B32): the height above the writing height at which it loses the page on EXP-T04's lift steps (0.1-3 mm), with the page regained on return | ≥ 2 mm | requirement | REQ-BNIB-017 (DEC-050); OPT-54 class (MFR); SIM: with a 0.8 mm cut-off B1's tracker left 0.87 of the tremor instead of 0.83, and perfect knowledge 0.40 instead of 0.28; the H1 writer lifts the handle 1.20 mm (median) between strokes (docs/balanced_nib.md s5.3). Rev K (DEC-062): the PMW3610-class die tracks the page only within ±0.2 mm of its lens height (MFR OPT-61; fit check F5, CALC) -> predicted to FAIL with a mouse-class die; REQ-BNIB-017 stays the selection requirement, so EXP-T04 chooses the die and optics | page sensor choice and place in Rev K; DEC-062 (REQ-BNIB-017 kept); building the Rev K pen (prototype_stages.md s0) |
| AC-T04-08 | REQ-RVJ-N06 | The page sensor in the heel module's front (beside the pod: azimuth 31°, 2.7 mm off the tilt plane; DEC-065), in its place: the pen roll over which the lens stays in its working band and the sensor keeps the page, at 35-75° | ≥ ±20° | requirement | REQ-RVJ-N06's roll range; DEC-065 fits the heel module to a pen only if EXP-T04 shows a sensor that tolerates ±20° of roll beside the pod; CALC: 0.5° with a PMW3610-class die and folded optics beside the pod (fit check V1, docs/revK_design.md s6) -> predicted to FAIL | DEC-065 (the heel module in a pen; prototype_stages.md s0) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-T04).
<!-- AC-TABLE:EXP-T04:END -->

### EXP-T05: Page-sensor latency (step and phase methods)

- **Rig and gate.** R10, with R13's flexure stage for fast steps. The sensing build gate. Requirements: REQ-SNS-001, REQ-RVJ-N06, REQ-CTRL-003.
- **Measures.** Latency from a voice-coil step (the encoder's 50 % crossing to the sensor's, ≥ 200 steps) and from the phase slope under multitone motion.
- **Decision it enables.** The estimator's prediction horizon; whether the 5 ms delay budget of REQ-CTRL-003 holds.
- **Procedure.** At least 200 steps of 50 µm at random phase; the encoder checks that each step rises (10–90 %) within 0.5 ms. Then the phase slope under multitone motion. The latency and the sensor's axes are fitted together: in the synthetic check a sensor a few degrees off the truth axes biased the latency by 0.13 ms until the two fits were alternated (SIM). EXP-S01's strobe method stays an option.
- **Existing experiments it runs.** EXP-S01 procedures 1–3.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §3.4–§3.7.

<!-- AC-TABLE:EXP-T05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T05-01 | REQ-RVJ-N06 | Latency from paper motion to the sensor's reported motion, 99th percentile of ≥ 200 steps (step method), and phase-slope latency 1-40 Hz | ≤ 2 ms | requirement | REQ-RVJ-N06 (2 ms); REQ-SNS-001 (3 ms total) | estimator horizon |
| AC-T05-02 | — | 10-90 % rise time of the step source measured by the encoder | ≤ 0.5 ms | derived | the step must be 4 x faster than the 2 ms being judged | validity of AC-T05-01 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-T05).
<!-- AC-TABLE:EXP-T05:END -->

### EXP-T06: Recording pen and tablet protocol: qualification and the real force split

- **Rig and gate.** R11, with R9's plate for the recording pen. It supports EXP-H01 and EXP-V07. Requirements: REQ-USR-002, REQ-ENV-001, REQ-ENV-002, REQ-DATA-001.
- **Measures.** The tablet protocol (ink on paper on an EMR tablet): sampling rate and jitter, and position against the scanned ink. The recording pen: axial force and IMU, with the paper-normal force from R9's plate. The excess-power method on injected amplitudes.
- **Decision it enables.** Whether EXP-H01 can start on the tablet protocol before the recording pen exists; real axial and paper-normal force distributions for the balance range.
- **Procedure.** The tablet protocol needs no build. Paper lies on an EMR tablet whose pen writes real ink; `rig/tablet/tablet_recorder.html` logs every pen sample the browser receives and saves a CSV with a pseudonymous code only; four taps on printed fiducials map the tablet to the page. Then the recording pen (Ø24 mm, and a 14 mm slim body; mass and centre of mass set with tungsten slugs): the refill on an axial cell, an IMU at 1.92 kHz, a cable to DAQ-1. Semi-synthetic recordings with injected tremor of 0.1–4 mm at 4–12 Hz qualify the excess-power method of `human_study_plan.md` §3.6. Sessions with people run from a battery or through a medical-grade isolator (R7).
- **Existing experiments it runs.** EXP-H01's instrumentation; EXP-V03's inputs; EXP-V07, on the tablet protocol once AC-T06-04 passes.
- **Criteria.** Its own are below. AC-H01-08 (proposed here as AC-T06-01) stays with EXP-H01. The tablet's accuracy class, about ±0.25 mm (LIT CON-101), may fail its 50 µm; then the chain is registered per stroke. Sentence copying rarely gives the ≥ 4 s pen-down runs the excess-power method needs: a pooled-run variant is open, and the same injection test qualifies it.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §4.1–§4.3.

<!-- AC-TABLE:EXP-T06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T06-02 | REQ-USR-002 | Excess-power method (human_study_plan.md s3.6) on semi-synthetic recordings: recovered major-axis A_pp relative to the injected amplitude, 0.1-4 mm, 4-12 Hz | within ±10 % | derived | method qualification required by s3.6; SIM check 0.80 vs 0.80 mm (rig.selftest) | EXP-H01 primary outcome |
| AC-T06-03 | — | Axial-force channel of the recording pen: expanded uncertainty over 0.2-5 N (LSB200 in the 24 mm pen; LLB130 in the slim pen) | ≤ 10 mN (24 mm) and ≤ 60 mN (slim) | derived | MFR AMF-225 (±0.1 % RO), AMF-226 (±0.5 % RO) after in-situ calibration | use of the force data |
| AC-T06-04 | — | Median pen report rate seen by rig/tablet/tablet_recorder.html (coalesced samples included) on the tablet and browser used, pen down on paper | ≥ 200 Hz | derived | EXP-V07's dependency (docs/revJ_simulation.md: a ≥ 200 Hz tablet) | EXP-V07 on this tablet; otherwise another tablet |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-T06).
<!-- AC-TABLE:EXP-T06:END -->

### EXP-T07: Actuator coupon: 2-D force map and K_m(position)

- **Rig and gate.** R12. Gate G2. Requirements: REQ-BNIB-003 (through K_m at 0.7 ×; DEC-050), REQ-ACT-002. The C1S coupon's REQ-RVJ-N02 stays with EXP-N01.
- **Measures.** The force vector against current (with current reversals) on a grid over the whole magnet stroke, by translation or by tilt about the pivot, in each axis and both together; back-EMF K_f; R20 and L.
- **Decision it enables.** The voice-coil geometry; rejecting force models that miss by more than 10 % (review G2); the firmware's force map.
- **Procedure.** 7 × 7 (or 11 × 11) nodes. At each node, currents from −0.6 to 0.6 of I_max in reversal order, with 0.2 s holds and ≥ 30 s of cooling above 0.3 I_max; one axis, the other, then both. Back-EMF K_f at the centre with R13's stage shaking the magnet part (±0.5 mm at 10, 20 and 50 Hz), an independent route. R20 by 4-wire; L by a voltage step. The goniometer centre is set on the pivot within 0.05 mm, using the zero-current pull map.
- **Existing experiments it runs.** EXP-B03 (force map, back-EMF, R and L); EXP-N01; EXP-J14 (K_m); EXP-K01 (force constant). They keep their criteria for their coupons; this experiment's lines are for study B's coupon. Study B's EXP-B23 (DEC-050): B1's moving-coil coupon; its keeper pull and K_m(T) are measured in EXP-T08.
- **Study B (DEC-050).** B1's coupon is mapped over ±1.2 mm in both axes, with the cross-coupling. AC-T07-01 now judges DEC-050's line: K_m at least 0.7 × the image-method model at every point (below it: larger poles, and the 24 mm bore is then the limit). Prediction (magpylib, CALC): 0.397 N/√W at the centre and 0.312–0.397 over the ±1.26 mm stroke (22 %), cross-coupling up to 27.5 %. So AC-T07-03 (ripple ≤ 15 %) is predicted to fail, and the firmware uses the measured force map.
- **Study K (DEC-062).** Study K's EXP-K22 runs here: the coupon carries Rev K's buildable coil (concentric racetracks, bundles 2.2 mm wide, rows 5.0 mm off the axis, sized to stay 0.3 mm inside the bore at the stop), and a second coupon has the heel variant's back plate and keeper with 1.2 mm notches (fit check V4). Prediction (CALC, an upper bound): 0.334 (x) and 0.272 (y) N/√W at the centre, with the x layer at 0.249 at the worst corner of the stroke and cross-coupling up to 0.28. AC-T07-05 judges DEC-062's line (K_m ≥ 0.7 × 0.334 N/√W on the x layer and 0.7 × 0.272 on the y layer), and AC-T07-01 the ratio to the model at each point. Below the line DEC-062 is revisited.
- **Study H (DEC-095, DEC-096).** The first force-constant coupons use stock N52 magnets (5 × 5 × 3 mm, AMF-309; 4.76 mm cubes, AMF-310), with the predictions regenerated at the as-built size and the measured Br (§0.2). Custom magnets are ordered only after AC-T07-02 passes. A second coupon carries the reach candidate's poles and winding (DEC-072: weakest sampled force constant 0.158 N/√W, CALC), mapped over ±1.5 mm. The measured K_m map enters DEC-096's duty re-run (§55).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §5.2–§5.4.

<!-- AC-TABLE:EXP-T07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T07-01 | REQ-BNIB-003 | B1's moving-coil coupon (study B's EXP-B23; since DEC-062 with Rev K's buildable coil, study K's EXP-K22): the lowest ratio over the map (±1.2 mm) of the measured K_m to the image-method model at the same point (bnib magnetics; revk/nib.py for Rev K's coil) | ≥ 0.7 | derived | DEC-050's revisit trigger (K_m below 0.7 x the image-method value -> larger poles; the 24 mm bore is then the limit), so derived; REQ-BNIB-003's travel is sized at K_m x 0.7; magpylib: 0.397 N/√W at the centre and 0.312-0.397 over the stroke (CALC, docs/balanced_nib.md s5.2). Was ≥ 0.85 x study B's design value from REQ-RVJ-N02 (the C1S rule, now a bench research module); Rev K's coil (DEC-062): 0.334 / 0.272 N/√W at the centre (x / y), the x layer 0.249 at the worst corner (CALC, docs/revK_design.md s3.3); DEC-062's absolute line is AC-T07-05 | pole size (DEC-050); the firmware force map; DEC-072 through DEC-096 (the measured K_m map enters the duty re-run) |
| AC-T07-02 | — | Fraction of map nodes where K_f is within ±10 % of the magnetostatic model (bnib.magnetics) | ≥ 90 % | hypothesis | AC-B03-04, AC-N01-01 analogues; review G2 'reject models that miss force materially' | trust in study B's Pareto fronts; custom magnets are ordered only after it passes (DEC-095) |
| AC-T07-03 | — | Force ripple (max - min) / mean of K_f over the stroke of study B's coupon | ≤ 15 % | hypothesis | AC-N01-02 (LIT AMF-143: 21.6-30.9 % over ±5 mm in a large-stroke actuator); the C1S coupon keeps AC-N01-02; B1 (DEC-050): K_m 0.312-0.397 N/√W over the ±1.26 mm stroke (22 %) and cross-coupling up to 27.5 % (magpylib, CALC) -> predicted to FAIL: the firmware uses the measured force map (study B's EXP-B23) | firmware force map |
| AC-T07-04 | — | K_f at the centre from the force route and from back-EMF agree within their combined U95 | agree | derived | s2r G3 (validation/sim_to_real.md s2 item 6) | validity of AC-T07-01 |
| AC-T07-05 | REQ-BNIB-003 | Rev K's buildable coil (DEC-062; study K's EXP-K22) in EXP-T07's coupon: the lowest measured K_m over the map (±1.2 mm) for the x and the y layer; the heel variant's notched back plate and keeper (1.2 mm notches) as a second coupon, reported | ≥ 0.7 x 0.334 N/√W (x layer) and 0.7 x 0.272 N/√W (y layer) | derived | DEC-062's revisit trigger (K_m below 0.7 x 0.334 N/√W) with study K's line for the y layer (docs/revK_design.md s11.3), so derived; CALC (magpylib with study B's magnets and iron images, an upper bound, scaled to study B's calibrated 0.400): 0.334 (x) and 0.272 (y) N/√W at the centre; the x layer falls 25 % toward the corners of the stroke (0.249 at the worst corner, 1.06 x the line: marginal); cross-coupling up to 0.28 (s3.3); the point-by-point ratio to the model is AC-T07-01 on the same map | DEC-062 (the buildable coil); building Rev K's nib (prototype_stages.md s0) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-T07).
<!-- AC-TABLE:EXP-T07:END -->

### EXP-T08: Magnetic pull, negative stiffness and loaded modes at temperature

- **Rig and gate.** R12, with the heated box or R9's chamber. Gate G2. Requirements: REQ-RVJ-I02, REQ-RVJ-N02 (for magnet-loaded suspensions: the C1S module since DEC-050).
- **Measures.** The axial pull against gap and offset; the zero-current lateral force map (negative stiffness); the current-to-position frequency response of the magnet-loaded suspension at 23, 35 and 50 °C; K_f and R against temperature.
- **Decision it enables.** Whether the flexure survives the pull (buckling margin, stiffness balance); the thermal derating of K_f.
- **Procedure.** Gap 0.5–1.5 mm and lateral offset ±0.1 mm at zero current; the lateral map gives the negative stiffness. Then multitone frequency responses (20–2000 Hz from the coil; position from the Hall pair, or the camera at low frequency) at 23, 35 and 50 °C.
- **Existing experiments it runs.** EXP-J01; EXP-J11 step 1 (stiffness against preload); EXP-J14 (pull); EXP-B03 item 6 and EXP-B07's coupon part (thermal); EXP-N03's modes; study B's EXP-B23 (DEC-050): B1's keeper pull and K_m(T).
- **Study B (DEC-050).** B1's moving coil keeps the magnetic gap constant: no pull and no negative stiffness on its suspension. The keeper pull (9.1 N, magpylib, CALC) acts between two handle-fixed parts. So AC-T08-02 and T08-03 apply to magnet-loaded suspensions (the C1S module) only. For B1 this experiment gives the keeper pull (AC-T08-01) and K_m against temperature, and it checks REQ-RVJ-I02's Rev K clause: the wires' buckling load against any axial magnetic force on the carrier (AC-T08-04; the force on the position sensor's 1 mm magnet was not computed). B1's loaded modes are measured in EXP-T10 (AC-T10-02).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §5.3–§5.4.

<!-- AC-TABLE:EXP-T08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T08-01 | — | Axial pull at the design gap against study B's magnetics model | within ±20 % | hypothesis | AC-J01-01 analogue; B1 (DEC-050): the keeper pull, 9.1 N between two handle-fixed parts, loads only the handle, not the suspension (moving coil; magpylib, CALC) | flexure buckling margin (REQ-RVJ-I02) |
| AC-T08-02 | REQ-RVJ-I02 | Suspension stiffness divided by the measured negative magnetic stiffness, lowest over the stroke and both axes | ≥ 2 | derived | PROPOSED margin (mirrors REQ-RVJ-I02's 2 x pull on buckling) | flexure design; DEC-050: magnet-loaded suspensions only (the C1S bench module); B1's moving coil puts no pull on its suspension |
| AC-T08-03 | REQ-RVJ-N02 | First loaded mode of the magnet-loaded suspension at 23 and 50 °C | ≥ 240 Hz | requirement | REQ-RVJ-N02 (first parasitic mode ≥ 240 Hz) | servo bandwidth; DEC-050: magnet-loaded suspensions only (the C1S bench module); B1's moving coil puts no pull on its suspension |
| AC-T08-04 | REQ-RVJ-I02 | B1 coupon on R12 (study B's EXP-B23): the four wires' sideways buckling load (measured in EXP-B25) as a multiple of the largest axial magnetic force on the moving carrier over the stroke, at zero and at full current | ≥ 2 | requirement | REQ-RVJ-I02 re-scoped for Rev K (DEC-050); CALC: B1's magnets and keeper are handle-fixed and its coils move, so no actuator magnet rides on the suspension; the four wires buckle sideways at 0.08 N in compression (docs/balanced_nib.md s5.2); the force on the position sensor's 1 mm magnet on the carrier was not computed: no prediction; in Rev K the ball thrust guide carries the carrier's axial load (DEC-063), so the wires see it only through the assembly preload (AC-K21-03) | the wires' set tension and axial stops; the sensor magnet's place (DEC-050) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-T08).
<!-- AC-TABLE:EXP-T08:END -->

### EXP-T09: Hall-sensor interference in the real magnetic neighbourhood

- **Rig and gate.** R12. Gate G2. Requirements: REQ-RVJ-I04, REQ-SNS-004, REQ-BNIB-009 (DEC-050).
- **Measures.** Hall output at fixed positions against coil current (DC from the linear amplifier; PWM from the pen's own driver), magnet position and temperature.
- **Decision it enables.** Sensor placement and compensation; whether the position sensor meets its error budget.
- **Procedure.** At 9 fixed positions, coil current 0 → 1.5 A with the linear amplifier and with the pen's PWM driver, magnets present and absent, at two temperatures.
- **Existing experiments it runs.** EXP-B03 item 8 (crosstalk); EXP-J03; study B's EXP-B24 (DEC-050).
- **Criteria.** AC-B03-07 (proposed here as AC-T09-02) stays with EXP-B03. AC-T09-01 checks REQ-RVJ-I04 on R12 only; AC-J03-01 also needs the heel motors running and the brake switching.
- **Study B (DEC-050).** EXP-B24: B1's 3-D Hall sensor (TMAG5170 class) over a 1 mm magnet on the carrier, with the coils driven by DC and PWM (0–1.5 A) at 23–60 °C. The cross-talk is calibrated against current, and the residual is referred to the tip (AC-T09-03; REQ-BNIB-009: ≤ 2 µm rms at 1 kHz; CALC 0.99 µm). A firmware review checks that the servo acts on the observer's estimate, never on the raw reading.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §5.3–§5.4.

<!-- AC-TABLE:EXP-T09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T09-01 | REQ-RVJ-I04 | Nib position error at the tip from the Hall sensors with coil currents 0-1.5 A (linear and PWM drive) after calibration, over the servo band | ≤ 10 µm RMS | requirement | REQ-RVJ-I04; AC-J03-01 | sensor layout |
| AC-T09-03 | REQ-BNIB-009 | B1's 3-D Hall sensor (TMAG5170 class) with the coils driven (DC and PWM, 0-1.5 A) at 23-60 °C, after the cross-talk calibration (study B's EXP-B24): tip-referred position noise at 1 kHz; and a firmware review that the servo acts on the observer's estimate, never on the raw reading (both) | both met (≤ 2 µm rms; conforms) | requirement | REQ-BNIB-009 (with REQ-RVJ-C04); CALC 0.99 µm; SIM: the filtered servo in every sim2 run (docs/balanced_nib.md s4) | sensor placement; the observer's noise model (DEC-050) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-T09).
<!-- AC-TABLE:EXP-T09:END -->

### EXP-T10: One-axis loaded nib: disturbance rejection and bandwidth in contact

- **Rig and gate.** R13, one axis, with R9's plate under the paper and R3 scans. Gate G3. Requirements: REQ-BNIB-003, REQ-BNIB-005 and REQ-BNIB-006 (DEC-050; REQ-RVJ-N02 before it), REQ-CTRL-002, REQ-CTRL-003, REQ-CTRL-005, REQ-VAL-001.
- **Measures.** Swept-sine and multitone housing disturbance at 1–30 Hz and 0.25–2 mm peak (acceleration-capped), in contact at 35/50/75° on three paper stacks; housing truth (LM13), ink truth (camera and scans) and the nib current.
- **Decision it enables.** A useful correction bandwidth under contact (review G3).
- **Procedure.** Amplitude ladder 0.25, 0.5, 1 and 2 mm. Periodic multitones of 10 s (24 log-spaced tones at 1–30 Hz, Schroeder phases, peak acceleration capped at 40 m/s², an ASSUMPTION) and log sweeps. The nib locked, then on with the oracle reference (the stage encoder), then with its own estimator. Clean writing without disturbance for false correction. The stage hangs from a fixed bridge and the paper moves on a one-axis table until the printer head is shown to carry the rig (about 1.06 kg, CALC). The 2 mm sines at 25–30 Hz need 10–18 N against the coil's 9.3 N continuous rating: bursts only, or a larger coil (CALC).
- **Existing experiments it runs.** EXP-I05 procedure 3–4; EXP-N03 (closed loop); EXP-B05 (in-contact FRF and margins); EXP-B09 (the one-axis precursor); EXP-Q06 (the pencil stage in the nib holder); study B's EXP-B26 (DEC-050); study E's EXP-E15 (the command path's lag).
- **Study B (DEC-050).** EXP-B26: the one-axis B1 nib, then the two-axis nib, which continues in EXP-T13. Added: the usable travel under the 35° static load at 12 Hz, with the coil 90 K above ambient and a 3.3 V supply (AC-T10-05); the tip-equivalent moving mass (AC-T10-06); and the lowest structural mode with the ball free and stuck, against the bandwidth (AC-T10-02). Predictions (CALC): ±1.06 mm with K_m × 0.7; 3.49 g; loaded modes 6 (the suspension), 362 and 2445 Hz with the ball free, and 109 (the suspension on the stuck ball), 568 and 2509 Hz with the ball stuck. DEC-050 sets the rule: the lowest structural mode stays at least 2.5 × the servo bandwidth with the ball free (362 Hz) and stuck (109 Hz), so with the ball stuck the bandwidth may not exceed about 44 Hz (REQ-BNIB-006, AC-T10-02).
- **Study E (DEC-060).** EXP-E15: sinusoidal nib commands at 3–14 Hz, with the tip's motion from an optical sensor, give the command path's equivalent delay (M-delay's definition applied from command to tip). Study E's HW1 model of the Rev J command path predicts 3.52–3.55 ms (80 Hz follower, ζ 0.7, 0.6 ms latency, 2 kHz ticks; CALC); there is no prediction for B1. The estimator predicts ahead by the lag it assumes, and study E's delay sweep was flat within ±3 ms of it (SIM), so AC-T10-07 allows ±3 ms. The same runs serve B1 and the C1S module (EXP-N03).
- **Study K (DEC-066).** Rev K's nib (C17200 wires and a ball thrust guide, DEC-063) has its ball-free mode at 1,206 Hz and its ball-stuck mode at 163 Hz nominally and 115 Hz in the worst case (35°, soft refill, 20 µm of pre-sliding; CALC). The rule then allows a servo of up to 46 Hz (65 Hz nominally), so Rev K's position servo runs at 40 Hz and its inner loop at no more than 46 Hz (DEC-066); 46 Hz is only 1.15 × REQ-BNIB-006's 40 Hz floor. AC-T10-02 judges the rule on Rev K's nib, and AC-T10-08 DEC-066's trigger (a stuck mode below 100 Hz), which is also study K's gate for building the Rev K pen. EXP-T01 measures the pre-sliding stiffness that sets the stuck mode. With Rev K's centring tolerances the usable travel (AC-T10-05) falls to 0.99 mm at the 1st percentile (CALC).
- **Study F (DEC-060's reach).** With Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F §8: the Rev J nose with its travel cut, tuning split). So Rev K's nib makes no severe-tremor legibility claim (DEC-060). AC-T10-05 checks the travel; EXP-E23 (§54) checks what the reach does to the words, in sim2.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §6.2–§6.5.

<!-- AC-TABLE:EXP-T10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T10-01 | REQ-VAL-001 | Reduction of the 3-12 Hz band ink-error RMS against the locked nib, same multitone seeds, 0.25-1 mm, 4-12 Hz, in contact at 50°, oracle reference (then the causal estimator) | ≥ 30 % | hypothesis | review section 12 G3/G4 (PROPOSED engineering gate) | G3; study B build |
| AC-T10-02 | REQ-BNIB-006 | B1 nib in contact at 35-75° (study B's EXP-B26): closed-loop -3 dB bandwidth (position / reference), and the lowest structural mode with the ball free and with the ball stuck on the paper, as a multiple of the measured bandwidth (both) | both met (≥ 40 Hz; lowest structural mode ≥ 2.5 x the measured bandwidth, ball free and stuck) | requirement | REQ-BNIB-006 (DEC-050); CALC loaded eigenmodes: ball free 6 (the suspension), 362, 2445 Hz; ball stuck 109 (the suspension on the stuck ball), 568, 2509 Hz; study B counts 362 Hz as the first parasitic mode (docs/balanced_nib.md s5.2). Was ≥ 60 Hz from REQ-RVJ-N02 (the C1S nose, now a bench research module, EXP-N03); DEC-050's mode rule (the lead, 2026-09-30): at least 2.5 x the servo bandwidth with the ball free (362 Hz) and stuck (109 Hz); at 40 Hz that is 9.1 x and 2.7 x (CALC), so the bandwidth may not exceed about 44 Hz with the ball stuck. Was both met (≥ 40 Hz; ≥ 120 Hz). Rev K (DEC-066; study K, CALC): with the C17200 wires and the ball thrust guide, ball free 1206 Hz, ball stuck 163 Hz nominal and 115 Hz worst (35°, soft refill, 20 µm of pre-sliding), so the servo may run at up to 46 Hz (65 Hz nominally); Rev K's position servo runs at 40 Hz and its inner loop at ≤ 46 Hz, 1.15 x the 40 Hz floor (marginal); DEC-066's 100 Hz trigger is AC-T10-08 (docs/revK_design.md s3.3, s5.5) | G3; DEC-066 (Rev K's servo at 40 / 46 Hz) |
| AC-T10-03 | REQ-CTRL-002 | Phase margin and gain margin of the nib loop, lowest over tilt, three paper stacks and two hand-simulant settings | ≥ 45° and ≥ 6 dB | derived | REQ-CTRL-002 (≥ 40° and ≥ 6 dB); 45° is the nose's margin of AC-N03-02, stricter than REQ-CTRL-002, so derived; review section 9 | servo tuning |
| AC-T10-04 | REQ-CTRL-005 | False correction: RMS ink displacement on clean writing (no disturbance), nib on vs locked, from scanned ink | ≤ 25 µm | derived | AC-E01-09 bound on real data; stage/ink truth U 3-5 µm (CALC) gives TUR ≥ 5 | G3 |
| AC-T10-05 | REQ-BNIB-003 | Usable travel of the B1 nib under the 35° static load at 12 Hz, with the coil heated 90 K above ambient and a 3.3 V supply, both axes (study B's EXP-B26) | ≥ ±1.0 mm | requirement | REQ-BNIB-003 (DEC-050: ±1.0 mm for G3; the G4 nib at ±1.5 mm only if study E finds an estimator that uses it); CALC ±1.06 mm under the 35° load with Km x 0.7, a hot coil and 3.3 V; the bench nib has its real Km, measured in EXP-T07; DEC-060 (study E): no causal estimator uses reach beyond ±1 mm on real tremor, so the G4 nib is ±1.0 mm too. Rev K (DEC-062; tolerances ASSUMPTION): the stops sit up to 0.072 mm off the magnetic centre at the 99th percentile, so the usable travel in the worst direction falls to 0.99 mm at the 1st percentile (0.98 mm at worst) (CALC, docs/revK_design.md s3.5) -> marginal. Reach: with Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F, docs/readable_target.md s8: the Rev J nose with its travel cut, tuning split), so Rev K's nib makes no severe-tremor legibility claim (DEC-060); EXP-E23 checks B1's own reach in sim2 | G3; G4; DEC-050 and DEC-060 (the travel) |
| AC-T10-06 | REQ-BNIB-005 | Tip-equivalent moving mass of the B1 nib, from the mass line of its measured frequency response (and by weighing the moving parts) | ≤ 4.5 g | requirement | REQ-BNIB-005 (DEC-050); CALC 3.49 g | G3 |
| AC-T10-07 | — | Command path's lag (study E's EXP-E15): sinusoidal nib commands at 3-14 Hz, tip motion by an optical sensor: equivalent delay (minus the phase over 2 pi f) of tip position over command, for each nib under test (B1; the C1S research module in EXP-N03's runs), against the delay that the estimator's prediction assumes for that nib | within ±3 ms | hypothesis | study E asks whether the Rev J command path's lag is 3.5 ms on hardware and gives no pass line (docs/real_tracker.md s9, s18), so a hypothesis; CALC on HW1's command path (80 Hz follower, zeta 0.7, 0.6 ms latency, 2 kHz ticks): 3.52-3.55 ms at 3-14 Hz; no prediction for B1; from 3 ms less to 3 ms more prediction the frozen design's severe ratio stayed at 0.65-0.66 and its mild ratio at 0.999-1.001, rising only from +5 ms (SIM, tuning split) | the estimator's prediction horizon (DEC-060) |
| AC-T10-08 | REQ-BNIB-006 | Rev K's nib (DEC-062, DEC-063: C17200 wires and the ball thrust guide) in contact at 35-75° with the softest refill: the lowest structural mode with the ball stuck on the paper | ≥ 100 Hz | derived | DEC-066's revisit trigger (a stuck mode below 100 Hz) and study K's gate for building the Rev K pen (prototype_stages.md s0), so derived; CALC: 163 Hz nominal and 115 Hz worst (35°, soft brass refill, 20 µm of pre-sliding: ASSUMPTION, which EXP-T01 measures); ball free 1206 Hz (docs/revK_design.md s3.3) | DEC-066 (the servo at 40 / 46 Hz); building the Rev K pen (prototype_stages.md s0) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (8 rows for EXP-T10).
<!-- AC-TABLE:EXP-T10:END -->

### EXP-T11: Large excursions, bounded current and stable pen lift

- **Rig and gate.** R13, one axis. Gate G3. Requirements: REQ-SAF-002, REQ-BNIB-002 (DEC-050), and REQ-RVJ-N04 and REQ-RVJ-N09 for the C1S module's pen lift and front stop.
- **Measures.** An amplitude ladder to saturation; peak current against the limit; recovery; 1.5 mm pen lifts at 50/60/70° and touchdowns; ink tails.
- **Decision it enables.** Graceful limits and the lift design.
- **Procedure.** The ladder goes beyond the usable travel, up to 2 mm and 30 Hz (acceleration-capped). Recovery is timed after the disturbance returns inside the travel. Then 1.5 mm lifts at 50, 60 and 70° with touchdowns, and scans of the ink tails. The current limit is a safety line: guarded acceptance.
- **Existing experiments it runs.** EXP-N05 step 4; EXP-Q08; EXP-F01 (over-current in contact).
- **Study B (DEC-050).** B1 has no pen-lift module. On a lift the face lands on its follower stop, 0.25 mm beyond the writing position, and leaves the refill, so the ball leaves the paper. AC-T11-03 judges the joined strokes and the ink tails on the loaded B1 nib. The release and the return are timed in EXP-J17 part (c) (AC-J17-05).
- **Study K (DEC-064).** In Rev K the face floats ±0.56 mm, so on an ordinary lift the ball follows the paper until the pen has risen by the float's gap. The ink tail after a natural lift is then 0.28–1.1 mm, and about 0.3 mm with a float brake (CALC; the brake ASSUMPTION), so AC-T11-03's 0.5 mm tail is at risk without the brake. Rev K's commanded pen lift, the head's follower, is tested in EXP-K23 (AC-K23-01).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §6.3–§6.5.

<!-- AC-TABLE:EXP-T11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T11-01 | REQ-SAF-002 | Peak coil current during the amplitude ladder up to 2 mm and 30 Hz (acceleration-capped) | ≤ software limit of the driver under test | requirement | REQ-SAF-002; guarded acceptance (safety) | G-S before any participant |
| AC-T11-02 | — | After the disturbance returns inside the usable travel: time until the residual ratio is back within 10 % of its steady value; no limit cycle | ≤ 0.2 s | hypothesis | PROPOSED (graceful saturation) | limiter design |
| AC-T11-03 | REQ-BNIB-002 | Strokes joined by ink across 1.5 mm pen lifts at 50/60/70°, and ink tail after a 30 mm/s lift | none; ≤ 0.5 mm | derived | AC-N05-03 (joined strokes) and AC-J06-02 (the ink tail of REQ-RVJ-N09) applied to the loaded B1 nib: with the counter-face the refill runs at most 0.25 mm past its writing position on a lift (REQ-BNIB-002), so the ball leaves the paper; neither line is REQ-BNIB-002's text, so derived (it derived from REQ-RVJ-N04, the C1S module's pen lift, before DEC-050). Rev K (DEC-064): the face floats ±0.56 mm, so on a lift the ball follows the paper until the pen has risen by the float's gap, and the ink tail after a natural lift is 0.28-1.1 mm, about 0.3 mm with the float brake (CALC and ASSUMPTION, docs/revK_design.md s3.4) -> the tail is at risk without the brake | lift design; the face's follower stop (DEC-050); DEC-064 (the float) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-T11).
<!-- AC-TABLE:EXP-T11:END -->

### EXP-T12: Static side load and holding power over tilt, roll and stroke direction (part B)

- **Rig and gate.** R13. Gate G3. Part A, on R9's frame, is EXP-J17 (§46), which keeps its id. Requirements: REQ-RVJ-N10 and REQ-BNIB-004's holding part (through AC-J17-02), REQ-RVJ-N03 (the C1S module's).
- **Measures.** Holding current and copper loss with the ball on the paper at 35–75°, roll ±20°, 8 stroke directions and F_c 0.08–0.2 N, with the balance mechanism on and off.
- **Decision it enables.** Whether the balanced nib removes the holding load of the review's §4 (study B's design question). Part A decides whether the C1S load path matches its model (DEC-046).
- **Procedure.** The nib in R13's holder with the ball on the paper, at each tilt, roll, direction and refill spring, with the balance on and off: holding current and copper loss. The static term was missing from every earlier protocol.
- **Existing experiments it runs.** EXP-J17 is its part A.
- **Criteria.** AC-J17-02 now covers part B's roll and directions (proposed here as AC-T12-01), and AC-J17-01 is the C1S line (AC-T12-03). EXP-T12 keeps AC-T12-02. AC-T12-02 carries B1's design values (DEC-050): 5.3 mN mean residual and 13.1 mN at the 95th percentile (CALC). Study M mapped study B's EXP-B28 onto this experiment and EXP-T06; it keeps its own id (§51) and uses this experiment's roll ring and tilt arc.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §2.5 (part A) and §6.3 (part B).

<!-- AC-TABLE:EXP-T12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T12-02 | — | Measured holding force at 35/50/75° against study B's balance model | within ±20 % | hypothesis | PROPOSED (the model must be trustworthy for the Pareto fronts); B1 (DEC-050): residual 5.3 mN mean (6 % of the unbalanced 96 mN) and 13.1 mN at the 95th percentile over 35-75° and all rolls (CALC, Monte Carlo) | bnib model |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-T12).
<!-- AC-TABLE:EXP-T12:END -->

### EXP-T13: Two-axis nib: sharp turns, repeated contacts, full roll and tilt

- **Rig and gate.** R13 with a second stage at 90°, and R3 scans. Gate G4. Requirements: REQ-CTRL-005, REQ-VAL-001, REQ-ENV-001, REQ-BNIB-004, REQ-BNIB-011, REQ-BNIB-013 (DEC-050).
- **Measures.** The feature course (corners, dots, hatching, fast strokes) under multitone tremor; 500 touchdowns; tilt 35–75° and roll ±20°; scanned ink.
- **Decision it enables.** Whether the core stays useful outside a short ideal trace (review G4).
- **Procedure.** The feature course on the two Zaber stages (reference build) or on the printer head, with the tremor of EXP-T10; the touchdown series; the full tilt and roll range.
- **Existing experiments it runs.** EXP-B09 (two-axis); EXP-N02; study B's EXP-B27 (DEC-050). EXP-N08 and the bench part of EXP-V05 follow it on the same rig.
- **Study B (DEC-050).** EXP-B27: the two-axis B1 nib with the counter-face on the tremor rig, roll ±20°. Added: the continuous nib power at duty A (0.2 mm rms, 8 Hz, 70 % contact) at 35, 50, 65 and 75° (AC-T13-04; CALC 7.6 mW, 17.6 mW at 35°; SIM 14.8 mW while correcting); the unpowered nib (AC-T13-05); and a review that `config/nib.yaml` carries the measured values and sim2 is re-run from it (AC-T13-06). The power grows with the ink force (about 8 / 30 / 184 mW at 0.15 / 0.3 / 0.69 N, CALC), so AC-T13-04 is judged at G1's set value (EXP-T02).
- **Study K (DEC-062).** REQ-BNIB-011 is reworded: unpowered, the nib rests on its soft stop, ≤ 1.3 mm off centre, and the pen writes like a normal pen. No wire suspension soft enough for B1's power can hold its 3.4 g against gravity, so Rev K's unpowered nib rests on its stop 1.26 mm off centre (CALC, fit check N22). AC-T13-05 checks where it rests and the feature course written with it.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §6.2–§6.5.

<!-- AC-TABLE:EXP-T13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T13-01 | REQ-VAL-001 | Reduction of the ink-error metric against the locked nib on the feature course with multitone tremor, tilt 35-75°, roll ±20° | ≥ 30 % | hypothesis | review section 12 G4 | G4 |
| AC-T13-02 | REQ-CTRL-005 | Clean-writing distortion (RMS) and corner/dot error on the feature course | ≤ 50 µm RMS and ≤ 100 µm | requirement | REQ-CTRL-005 | G4 |
| AC-T13-03 | — | Contact chatter episodes (≥ 3 transitions within 20 ms) over 500 touchdowns | = 0 | hypothesis | AC-B05-14 definition | contact handling |
| AC-T13-04 | REQ-BNIB-004 | Continuous nib power of the two-axis B1 nib with the counter-face at duty A (0.2 mm rms, 8 Hz, 70 % contact; coil current and resistance) at 35, 50, 65 and 75°: the mean over the tilts (study B's EXP-B27) | ≤ 20 mW | requirement | REQ-BNIB-004 (DEC-050); CALC 7.6 mW (10.5 / 15.4 mW with Km at 0.85 / 0.7 x; 17.6 mW at 35°); SIM 14.8 mW while correcting; it grows with the ink force (about 8 / 30 / 184 mW at 0.15 / 0.3 / 0.69 N), so it is judged at G1's set value; the holding part is AC-J17-02 | G4; the power and battery budget (DEC-050) |
| AC-T13-05 | REQ-BNIB-011 | Unpowered B1 nib (driver off), ball on the paper at 35-75°: where the nib rests (on its soft stop; its offset from the centre in both axes), and the feature course written with it (both) | both met (on its soft stop, ≤ 1.3 mm off centre; the feature course within AC-T13-02's lines) | requirement | REQ-BNIB-011 as DEC-062 rewords it; CALC (study K): gravity rests the unpowered nib on its soft stop 1.26 mm off centre, since the wires alone would let it sag 18 mm (fit check N22), and the stops sit up to 0.072 mm off the magnetic centre at the 99th percentile (tolerances ASSUMPTION; docs/revK_design.md s3.5, s4) -> marginal. Was both met (≤ 0.1 mm off centre; the feature course within AC-T13-02's lines), with study B's CALC: centred by the wires (3.8 N/m at the tip), the face still balancing | the failure state; G-S before any participant; DEC-062 |
| AC-T13-06 | REQ-BNIB-013 | Review at G4, and at each earlier gate: the nib's measured values (the spring's set point from EXP-T02, the friction map from EXP-T01, the Km map from EXP-T07, the suspension and modes from EXP-T10, the thermal parameters from EXP-T15) entered in config/nib.yaml with their evidence status and version, and sim2 re-run from that file | conforms | requirement | REQ-BNIB-013 (DEC-050); config/nib.yaml is generated by bnib and checked against the code by bnib/tests (study B) | sim2 calibration (DEC-040); G4 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-T13).
<!-- AC-TABLE:EXP-T13:END -->

### EXP-T14: Two-axis nib with its own page sensor: optical dropout while writing

- **Rig and gate.** R13 with R10's fixtures. Gate G4. Requirements: REQ-SAF-003, REQ-CTRL-005, REQ-RVJ-N06.
- **Measures.** Forced dropouts (a glossy strip, an ink crossing, a 2 mm lift, occlusion) during tremor writing; the authority fade and re-acquisition; ink excursions.
- **Decision it enables.** The page sensor's fault handling in closed loop.
- **Procedure.** Each dropout type is forced during writing with tremor; authority and ink are logged through the loss and the recovery.
- **Existing experiments it runs.** EXP-N07 (in the pen); EXP-F02 (the page-sensor faults).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §6.3–§6.5.

<!-- AC-TABLE:EXP-T14:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T14-01 | REQ-SAF-003 | On a forced page-sensor dropout: time to reduce authority, and the largest ink excursion caused | ≤ 20 ms and ≤ 100 µm | derived | REQ-SAF-003 (20 ms authority reduction); REQ-CTRL-005 (100 µm corner bound); the 100 µm is not REQ-SAF-003's, so derived | fault handling |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-T14).
<!-- AC-TABLE:EXP-T14:END -->

### EXP-T15: Long thermal run with the governor

- **Rig and gate.** R13 in a 30 °C chamber. Gate G4. Requirements: REQ-BNIB-010 (DEC-050), REQ-THM-001, REQ-THM-002; REQ-RVJ-N03 for the C1S module (EXP-N04).
- **Measures.** 30–60 min of the design duty and of a worst-case duty (35°, 2 mm tremor) in a 30 °C room: coil temperature by resistance, magnets and web by thermocouple, an IR map, and the governor's state.
- **Decision it enables.** The heat and runtime of the balanced nib; the governor's limits.
- **Procedure.** As above. A two-node thermal model is fitted on the first 10 min and predicts the rest (AC-T15-03). Coil temperature by resistance has an uncertainty of about 2.5 K, so the 20 K line is guarded (TUR 2.0 at a 15 K rise, CALC); it is a safety line anyway.
- **Existing experiments it runs.** EXP-N04; EXP-J05 (the heater shell first); EXP-J13; EXP-B07 (the pen part); EXP-P01 (the nib's power); study B's EXP-B29 (DEC-050).
- **Study B (DEC-050).** EXP-B29: B1 at 35° with 2 mm tremor for 30–60 min in a 30 °C room, governor on. AC-T15-01 now judges REQ-BNIB-010: ≤ 41 °C at the web after 30 min (SIM + CALC: skin 30.8 °C, coil 31.2 °C, the governor never acting). The 20 K coil line of REQ-RVJ-N03 stays with the C1S module (EXP-N04, AC-N04-01).
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §6.3–§6.5.

<!-- AC-TABLE:EXP-T15:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T15-01 | REQ-BNIB-010 | B1 with the governor in a 30 °C room (study B's EXP-B29): skin temperature at the web after 30 min at 35° with 2 mm tremor, with the coil rise (resistance) reported; guarded acceptance | ≤ 41 °C | requirement | REQ-BNIB-010 (DEC-050; REQ-THM-001's design target); SIM + CALC: coil 31.2 °C and skin 30.8 °C after 30 min, the governor never acting (docs/balanced_nib.md s5.6). Was ≤ 20 K and ≤ 43 °C at the design duty from REQ-RVJ-N03 (the C1S module's autowrite rule, EXP-N04) | G4; battery and heat claims (DEC-050) |
| AC-T15-02 | REQ-THM-002 | Coil hot spot at the worst duty (35°, 2 mm tremor) with the governor; guarded acceptance | ≤ 120 °C | requirement | REQ-THM-002 | governor limits |
| AC-T15-03 | — | Two-node thermal model (fitted on the first 10 min) predicts the web rise over the rest of the run | within ±20 % | hypothesis | AC-J13-02 analogue | thermal model behind REQ-BNIB-010 (study B's two-node model) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-T15).
<!-- AC-TABLE:EXP-T15:END -->

### EXP-T16: Collar and tail on a grip simulant: none, same mass locked, unpowered, active

- **Rig and gate.** R14 on R13's stage, with R3 scans. Gate G5. Requirements: REQ-WP-001 (AC-T16-01), REQ-EC-002 (AC-T16-02) and REQ-EC-003 (EXP-K02, J16).
- **Measures.** The same tasks and disturbance seeds in four conditions, at three grip strengths (a squeeze of 2, 4 and 8 N): ink error; the pen's translation and rotation; the module's power.
- **Decision it enables.** The benefit of an active module per added gram, watt and grip effort (review G5: at least 10 % over the same mass locked, with no subgroup harmed).
- **REQ-WP-001 (DEC-051, DEC-053).** The G5 gate is now a requirement for any device that would shift the pen: ≥ 10 % against the same pen with the device locked and the existing corrector working, at 0.5, 1 and 2 × the nominal grip, without lowering coverage by more than 5 points. AC-T16-01 is its criterion. REQ-WP-001's grip strengths are stiffness multiples (study W's phantom springs: 300, 575 and 1100 N/m); R14 sets squeezes of 2, 4 and 8 N, and its leaf sets give 211, 500 and 977 N/m (CALC). The rig design picks the settings (`README.md` §7).
- **Procedure.** The four conditions in random order, 10 disturbance seeds each, the EXP-K02 tasks. A camera tracks dots at the front and rear of the pen (translation at the grip and rotation about it); the pen's IMU adds angular rate at 1.92 kHz. A printed dummy with tungsten inserts, of the same mass, centre of mass and inertia, is the locked condition. `rig.collar.g5_decision` pairs the conditions per seed and uses the lower 95 % bound.
- **Existing experiments it runs.** EXP-I06; EXP-K02; EXP-J16; EXP-K07 (the rotor condition, only if a rotor is kept); study W's EXP-W11 (the collar, its G5 part) and EXP-W14 (the tails; its driven reaction mass is EXP-J16's end-cap). It supersedes EXP-I04.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §7.2–§7.3.

<!-- AC-TABLE:EXP-T16:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T16-01 | REQ-WP-001 | Any module added to shift the pen, on the hand phantom (R14 on R13's stage): the collar of EXP-W11, the tail modules of EXP-W14, the end-cap of EXP-K02 and EXP-J16: relative reduction of the band ink-error RMS (the tremor left at the tip), active module against the same pen with the module locked and the nose working, same seeds, at every grip strength (R14's squeezes of 2, 4 and 8 N, with leaf sets for 0.5, 1 and 2 x the nominal grip stiffness), lower 95 % bound; and coverage (share of the intended ink laid) against the locked condition (both) | both met (≥ 10 % at every grip strength; coverage no more than 5 points lower) | requirement | REQ-WP-001 (DEC-051, DEC-053: the review's G5 made a requirement for product entry, with coverage); it was a hypothesis on REQ-EC-003, whose own bar is ≥ 5 points over the same mass fixed (AC-K02-03, AC-J16-02); SIM: the collar with the Rev J pen inside -5 % to +5 % (fails), the light collar +17 % at 8 mm PD but 17 points less ink (fails on coverage), the 100 g gyroscopic tail 15 / 51 / -14 % at grips 0.5 / 1 / 2 x on the tuning writer (fails) (docs/whole_pen_shift.md s4.5); rig.collar.g5_decision uses the lower 95 % bound (SIM check: passes at a 16 % margin, fails at 6 %) | DEC-051 (revisited if the collar mock-up passes); a module enters the product only after a pass (DEC-053) |
| AC-T16-02 | REQ-EC-002 | Mean ink error with the active module relative to no module, at every grip strength | never higher | requirement | REQ-EC-002 ('never raises it on average'); review G5 'no subgroup harmed materially' | module |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-T16).
<!-- AC-TABLE:EXP-T16:END -->

### EXP-T17: Grip simulant qualification

- **Rig and gate.** R14. Gate G5 (the validity of EXP-T16). Inputs to REQ-SIM-005.
- **Measures.** The simulant's frequency response in translation and rotation, 1–20 Hz, at each squeeze setting, against HAP-26 until EXP-B06, I01 and V04 measure people.
- **Decision it enables.** Whether R14's results can be read as grip-dependent at all.
- **Procedure.** Before EXP-T16, with R2's rule of §0.9 (within ±10 % of the target). Three leaf sets (0.15, 0.20 and 0.25 mm) span HAP-26's k1 interval; strips set the rotational share r_rot at 0.3, 0.5 and 0.7.
- **Full procedure, instruments and uncertainty.** `docs/measurement_rig.md` §7.2–§7.3.

<!-- AC-TABLE:EXP-T17:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-T17-01 | — | Simulant FRF (translation and rotation, 1-20 Hz) against its target at each squeeze setting | within ±10 % | derived | R2 simulant qualification band (bench_protocols.md s0.9) | validity of EXP-T16 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-T17).
<!-- AC-TABLE:EXP-T17:END -->

---

## 48. Real recorded data: EXP-R02, R04…R07 (study R; DEC-054, DEC-055)

### Purpose and what it gates

Study R (`docs/real_data.md`) tests the pens in simulation (model HW1) on real recorded inputs. The writing is real handwriting on paper (UNIPEN hpb2: 14 adults with a ballpoint on paper forms). The tremor is real: Parkinson's at the pen tip from spirals on a tablet (UCI), essential tremor from the hand (Zenodo). The page sensor has DeltaPen-class errors. Test writers, texts and patients were set aside before anything was tuned. **Nothing was measured on a person or on hardware.**
- **DEC-054.** Real recorded inputs and the results card are the standard test. Every claimed benefit is reported on held-out real inputs as a results card: words read by a literal reader out of 10 with 95 % writer-bootstrap intervals, tremor left at the tip in mm, and how much clean writing changed. Tremor classes are named in mm at the tip: mild 0.03–0.16 mm, moderate 0.16–0.51 mm, severe above 0.51 mm (typically 1.7 mm).
- **DEC-055.** No legibility claim at severe tremor until a causal tracker passes on real inputs: at least 2 more readable words out of 10 than the ordinary pen at the severe class, with the 95 % interval above 0, and ≤ 25 µm of change to clean real writing as the mean over the test writers, with no single writer above 50 µm (AC-R02-01; clarified by the lead, 2026-09-29). Until then the help for severe tremor is autowrite of accepted text (DEC-049) and the app's clean copy. DEC-060 (2026-09-30, study E): no causal tracker passes yet, and the line stays unchanged; the help for severe tremor is the app's clean copy, spelling help and word completion (autowrite of accepted text is a bench research mode, DEC-050).
- **What the study found (SIM with real inputs).** At the severe class (1.72 mm), readable words out of 10: ordinary pen 0.5, Rev H 0.4, Rev J gated 0.4, TCN 0.2. The same Rev J nose with perfect knowledge of the tremor gives 7.0, and the same notes without tremor 6.8. So the nose is big enough; the tremor estimate is the limit. Real tremor wanders about twice as much as the model, so the gate opens only 21–42 % of the time at the severe size. The TCN moved clean real writing by 172 µm. A realistic page sensor changed the results by at most 0.1 word.
- **Requirements.** REQ-DATA-002…009 (study R's), with REQ-ML-001, REQ-CTRL-009…011 and REQ-RVJ-C05.
- **Studies with people.** EXP-R01 (patients' own writing, the recording part of EXP-H01) and EXP-R03 (a human panel against the AI reader) are in [`human_study_plan.md`](human_study_plan.md) §21.
- **One run, several scorings.** EXP-R02 shares the replay runs of EXP-L01, L02 and L04 on the EXP-H01/R01 recordings and scores them as results cards. EXP-R05's model enters EXP-L04 for REQ-ML-001. EXP-R07 runs inside EXP-T04 and T05 on rig R10 (§47). EXP-W15 (§50) scores the same runs for the gap to perfect knowledge, with study W's GLG and the collar (DEC-052). EXP-E10 (§52) is scored here too (AC-R02-01, AC-R02-07), and by EXP-R05's AC-R05-01.
- **Data rules.** Splits as REQ-DATA-001; licences as REQ-DATA-006; the library's zero-phase tremor extraction is an input only (REQ-DATA-005).

### EXP-R02: Do the trackers leave real clean writing alone and remove real tremor?

- **Purpose and gates.** Score every tracker on real inputs as a results card (DEC-054), and apply DEC-055's line at the severe class. Gates DEC-055 (a legibility claim at severe tremor), the tracker choice with EXP-L01 and L02 (DEC-042, DEC-047), and REQ-DATA-002, 003, 004, 007 and 008.
- **Predictions (SIM with real inputs; `results/realdata/realdata.json`).**
  - Severe class, 1.72 mm (PD and ET pooled), readable words out of 10: ordinary pen 0.5, Rev H 0.4, Rev J gated 0.4, TCN 0.2; perfect knowledge 7.0; the same notes without tremor 6.8. Tremor left at the tip: Rev H 1.06 ×, Rev J gated 0.96 ×, TCN 0.71 × the ordinary pen's. So every tracker as built fails DEC-055's line.
  - Moderate class, 0.24 mm: 5.7 of 10 with an ordinary pen and 5.5 with Rev J; the gate stays shut (under 1 % of the time).
  - Clean real writing moved: Rev H and Rev J gated 25 µm (14–42); TCN 172 µm (93–286).
  - The Rev H tracker made the tip tremor larger than an ordinary pen's in 56 % of the severe notes and in every moderate and mild note, as the pure-delay limit predicts (review s9).
  - Study E (SIM, the same test split, one test after a freeze; `docs/real_tracker.md` §2–§3): the frozen design (ai2's TCN with a soft size gate) left 0.69 × the ordinary pen's severe tip tremor, but gained −0.05 words (−0.15 to 0.00), and it moved clean writing 68 µm on average and 493 µm for one writer. G4 left 1.07–1.08 × at every class and moved clean writing 0.1 µm; the pen with the nose held left 1.08 ×. No design passes DEC-055 (DEC-060).
- **Set-up.** Now: the realdata test split (UNIPEN hpb2 test writers and texts; UCI and Zenodo test patients at DEC-054's classes), model HW1, with the DeltaPen-class page sensor and the ideal sensor as a labelled bound (`python3 -m realdata.run`). Later: the EXP-H01/R01 recordings, replayed through the same trackers in the harness of EXP-L01, L02 and L04 (the same runs), with the recorded sensor streams.
- **Procedure.**
  1. Check the clean writing before use (REQ-DATA-003).
  2. Run each tracker on the test split at every class: Rev H, Rev J gated, G4 (DEC-047), study W's GLG (DEC-052) and the TCN, as built and as re-tuned (EXP-R05; EXP-L01 for the detector), with perfect knowledge as the mechanism's limit.
  3. Score the results card per class and population: literal words read with the clean-ink ceiling, tremor left at the tip in mm, clean writing changed, all with 95 % intervals over writers; the ideal-sensor rows as a bound.
  4. Repeat on the recordings when they exist.
  5. Score EXP-E10's run on new held-out data the same way (AC-R02-01, AC-R02-07; §52).
- **Measurands.** Readable words out of 10; tremor left at the tip (peak, √2 × RMS of the major axis in f0 ± 2 Hz); clean writing changed (µm; the mean over the test writers and the largest writer); gate-open share; the same with the ideal sensor; the pen with the nib held beside the ordinary pen, with per-writer ratios against it (REQ-CTRL-017).

<!-- AC-TABLE:EXP-R02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R02-01 | REQ-DATA-002 | Severe tremor class (DEC-054: above 0.51 mm at the tip, representative 1.72 mm), PD and ET pooled, on the real-input test split (realdata: UNIPEN hpb2 test writers and texts, UCI and Zenodo test patients; model HW1; the measured-error page sensor), on the EXP-H01/R01 recordings when they exist, and on EXP-E10's new held-out data (study E's real-data TCN, frozen and tested once): readable words out of 10 (literal reader) with the causal tracker under test minus with the ordinary pen, with its 95 % writer-bootstrap interval; and clean real writing changed by that tracker (the same notes without tremor): the mean over the test writers (the results card) and the largest single writer (all) | all met (≥ 2 more words, with the 95 % interval above 0; ≤ 25 µm as the mean over the test writers; no writer above 50 µm) | derived | DEC-055's pass line, from the decision log, so derived (clarified by the lead: ≤ 25 µm as the mean over the test writers, with no single writer above 50 µm); REQ-DATA-002 (DEC-054); SIM with real inputs at 1.72 mm, readable words out of 10: ordinary pen 0.5, Rev H 0.4, Rev J gated 0.4, TCN 0.2, perfect knowledge 7.0, the same notes without tremor 6.8; clean real writing moved 25 µm (14-42) by Rev H and Rev J gated and 172 µm (93-286) by the TCN (docs/real_data.md; results/realdata/realdata.json) -> every tracker as built FAILS; study E (SIM, the same test split, one test after a freeze): its frozen design (ai2's TCN with a soft size gate) -0.05 words (-0.15 to 0.00), clean writing 68 µm mean and 493 µm for one writer; G4 -0.17 (0.1 µm); R's gated tracker -0.16 (25.5 µm, worst 85) (docs/real_tracker.md s2) -> FAILS (DEC-060). Reach: with Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F, docs/readable_target.md s8: the Rev J nose with its travel cut, tuning split), so Rev K's nib makes no severe-tremor legibility claim (DEC-060) | DEC-055 (a legibility claim at the severe class only after a pass; until then autowrite of accepted text, DEC-049, and the app's clean copy); DEC-042 (tracker choice, with EXP-L01 and L02); DEC-060 (none passes yet: the help for severe tremor is the app's clean copy, spelling help and word completion, with autowrite a bench research mode, DEC-050); DEC-061 (a learned estimator leaves shadow mode only after it passes this line in EXP-E10) |
| AC-R02-02 | REQ-DATA-002 | Every tracker results card of EXP-R02 and of the tracker studies it scores (document review): the result on real inputs (test writers, texts and subjects only) reported next to the synthetic one, and results on synthetic writers or tremor labelled as model-input results | conforms | requirement | REQ-DATA-002 (DEC-054); the bridge at 1 mm: Rev J gated left 0.68 x the ordinary pen's tip tremor with synthetic inputs and 1.04 x with real writing, real tremor and the DeltaPen-class sensor (SIM, docs/real_data.md) | DEC-054 |
| AC-R02-03 | REQ-DATA-003 | Clean writing used for 'clean writing changed' (the UNIPEN hpb2 test notes now; the controls' EXP-H01/R01 recordings later), checked with sim2j.writers.kinematics before use: share of pen-down velocity energy at 8-12 Hz | ≤ 2.5 % | requirement | REQ-DATA-003; UNIPEN hpb2 2.4 % (passes) and UCI letters 1.3 %; BRUSH 35.6 % and the synthetic writers 10.1-17.3 % fail, and on BRUSH the trackers moved clean ink by 160-880 µm (CALC on DATA, SIM; docs/real_data.md); real writing on paper 1.3-1.7 % (LIT CON-25) | validity of every 'clean writing changed' result (AC-R02-01, AC-R05-01) |
| AC-R02-04 | REQ-DATA-004 | Results cards of EXP-R02 and every claim that cites them (document review): the tremor class named in mm at the tip (peak = sqrt(2) x RMS of the major axis in f0 ± 2 Hz; DEC-054's classes) with the population; peak-to-peak values (EXP-H01, REQ-USR-002) labelled as such | conforms | requirement | REQ-DATA-004 (DEC-054); the round-4 plan's 0.3-1 / 2-4 / 5-10 mm classes are replaced; REQ-USR-002's 1 mm p-p is about 0.5 mm peak (human_study_plan.md s3.6: A_pp = 2 sqrt(2) A_rms) | DEC-054 |
| AC-R02-05 | REQ-DATA-007 | Every tracker results card of EXP-R02 (review): results with the measured-error page-sensor model (the DeltaPen-class model until EXP-R07 replaces it), and the ideal sensor only as a labelled bound | conforms | requirement | REQ-DATA-007 (DEC-054; review R14); with the DeltaPen-class model the results changed by at most 0.1 word and 0.01 mm against the ideal sensor (SIM, docs/real_data.md) | DEC-054 |
| AC-R02-06 | REQ-DATA-008 | Words read in every results card of EXP-R02 (review): a literal reader (no lexicon, no spelling correction, greedy decoding), with the clean-ink ceiling of the same notes and a 95 % interval over writers | conforms | requirement | REQ-DATA-008 (review s13; DEC-054); TrOCR base, literal, chosen on the tuning notes, reads 6.8 of 10 words of the clean real test notes (SIM); EXP-R03 checks it against people (AC-R03-01) | DEC-054; DEC-055 |
| AC-R02-07 | REQ-CTRL-017 | Every tracker results card of EXP-R02, EXP-E10's run included: the nose-held pen (the same pen with the nib held) reported beside the ordinary pen, and, per held-out writer, the tip tremor with the tracker at the mild and moderate classes against the nose-held pen (both) | both met (reported; ≤ 1.02 x for every writer) | requirement | REQ-CTRL-017 (DEC-060); test split (SIM, study E): the nose-held Rev J pen 1.08 x the ordinary pen at every class, G4 1.07-1.08 x; the frozen design up to 4.6 x the nose-held pen at the mild class for one writer and 1.13 x for another (docs/real_tracker.md s3, s15) -> the frozen design FAILS | any tracker's acceptance (DEC-060, DEC-061) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-R02).
<!-- AC-TABLE:EXP-R02:END -->

- **Decision rule.** A causal tracker passes AC-R02-01: a legibility claim is allowed at the severe class (DEC-055), and that tracker becomes the candidate default (DEC-042 revisit, with EXP-L01 and L02). None passes: no legibility claim at severe tremor; the help stays autowrite of accepted text (DEC-049) and the app's clean copy.

### EXP-R04: Poor handwriting and dyslexia inputs

- **Purpose and gates.** Bring children's handwriting, with and without dysgraphia, into the library for study S and the practice functions (spelling help, guided practice). Gates REQ-DATA-006 for the new source.
- **Set-up.** DiaGraMo (CC BY 4.0; 276 Czech children, 161 with dysgraphia; 1.36 GB; LIT CON-85) through the library's loaders.
- **Procedure.** Record the licence and attribution in the source registry. Split the children by participant, stratified by dysgraphia, before any use (REQ-DATA-001). Measure the kinematics with `sim2j.writers.kinematics` (speed, stroke time, velocity spectrum, 8–12 Hz share), and report them against the adult writers.
- **Measurands.** Kinematics per group; the share of pen-down velocity energy at 8–12 Hz, which decides whether its writing may also serve as clean writing (REQ-DATA-003).
- **Predictions.** None: the set was found late and is not yet used.

<!-- AC-TABLE:EXP-R04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R04-01 | REQ-DATA-006 | DiaGraMo in the library (review and the source registry test): its licence (CC BY 4.0) and attribution recorded, with what may go into results/, and the children split by participant, stratified by dysgraphia, before any use (REQ-DATA-001) | conforms | requirement | REQ-DATA-006; DiaGraMo: CC BY 4.0, 276 Czech children, 161 with dysgraphia (LIT CON-85; found late, not yet used); realdata/tests checks that every source has a licence and a redistribution rule | study S and the practice functions' use of children's writing |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-R04).
<!-- AC-TABLE:EXP-R04:END -->

- **Decision rule.** Loaded under its licence: study S and the practice studies with children (EXP-W05, EXP-L08, EXP-G07) may use it as input.

### EXP-R05: Does a tracker trained on real inputs keep clean writing still?

- **Purpose and gates.** Retrain the TCN on real inputs, and check that it leaves clean real writing alone, before any test on people's recordings. Gates the TCN's entry to EXP-L04 (REQ-ML-001) and EXP-R02 (DEC-055), and REQ-DATA-005.
- **Study E (DEC-061).** Study E did the retraining in simulation: the real-data TCN (16,960 weights, `realtrack/netmodel.py`), frozen as "net" in `results/realtrack/frozen.json`. Its result on the realdata test split was seen after the freeze and is information only, so the test split is spent: steps 3 and 4 now run on new held-out data as EXP-E10 (§52), and AC-R05-01 is judged there.
- **Predictions (SIM).** As built (trained on synthetic writers) the TCN moved clean real writing 172 µm (93–286), against 17 µm on the synthetic writers, and left 0.71 × the ordinary pen's tip tremor at the severe class; 1.1 mm of tremor still made the words unreadable. No prediction for the retrained model from the test split. Study E, cross-fitted on the tuning split (SIM): 4.3 µm on average and 19.7 µm on the worst note, with 0.76 / 0.58 × the ordinary pen's severe tip tremor (PD / ET).
- **Set-up.** The realdata tuning split: UNIPEN hpb2 tuning writers (5) and texts (81) with the UCI and Zenodo tuning patients' tremor; later the EXP-R01 training participants whose consent covers model training (`human_study_plan.md` §3.3, item iii). The DeltaPen-class page sensor. The test is writer-disjoint, on the test split.
- **Procedure.**
  1. Build the training inputs from the simulated sensor streams only: the zero-phase tremor extraction drives the simulated hand, never the model (REQ-DATA-005).
  2. Retrain the TCN, then freeze it.
  3. Test on the test split in HW1: the results card, with clean writing changed per test writer.
  4. Hand the frozen model to EXP-R02 (DEC-055's line) and EXP-L04 (REQ-ML-001 on the held-out EXP-H01/R01 participants).
- **Measurands.** Clean writing changed; tremor left at the tip; words read; the spread over writers.
- The gated tracker's detector is re-tuned on real data in EXP-L01 (study R's open issue 5).

<!-- AC-TABLE:EXP-R05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R05-01 | REQ-ML-001 | TCN retrained on the realdata tuning split (UNIPEN hpb2 tuning writers and texts with the UCI and Zenodo tuning patients' tremor; later the EXP-R01 training participants), frozen (study E's real-data TCN, DEC-061), on new held-out data in HW1 with the DeltaPen-class page sensor (EXP-E10's run; the realdata test split is spent): clean real writing changed (the same notes without tremor): the mean over the test writers and the largest single writer (both) | both met (≤ 25 µm as the mean over the test writers; no writer above 50 µm) | derived | REQ-ML-001's false-correction limit (≤ 25 µm RMS on tremor-free writing) applied in simulation on real inputs, as the entry check to EXP-L04, so derived; as built (trained on synthetic writers) the TCN moved clean real writing 172 µm (93-286), against 17 µm on the synthetic writers (SIM, docs/real_data.md): no prediction for the retrained model; the per-writer cap is DEC-055's clarified line, since this model enters EXP-R02; study E retrained it (the real-data TCN, 16,960 weights; cross-fitted on the tuning split in the full plant: 4.3 µm mean, 19.7 µm on the worst note, SIM); its result on the test split was seen after the freeze and is information only (DEC-061), so this line is judged on EXP-E10's new data. Was: on the realdata test split | the TCN's entry to EXP-L04 and EXP-R02; DEC-042 (shadow mode until REQ-ML-001 passes); DEC-055; DEC-061 |
| AC-R05-02 | REQ-DATA-005 | Training and test pipeline of the retrained TCN, and every tracker replay of EXP-R02 (code review, and a test that no controller or estimator input is read from the library's tremor or writing arrays): only simulated or recorded sensor streams reach a controller or estimator | conforms | requirement | REQ-DATA-005; the library's tremor extraction is zero-phase (it uses future samples) and marked for inputs and statistics only (realdata/dsp.py); REQ-CTRL-009 is the command-side rule (AC-L01-04) | DEC-054; DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-R05).
<!-- AC-TABLE:EXP-R05:END -->

- **Decision rule.** Pass: the model enters EXP-L04 and EXP-R02. Fail: the TCN stays in shadow mode (DEC-042) until more real training data exist (EXP-R01, EXP-R06).

### EXP-R06: Get the missing data sets

- **Purpose and gates.** Obtain the real-writing sets that need registration, an agreement or permission, for larger test sets. Gates REQ-DATA-006.
- **Procedure.** Request IAM-OnDB (registration; English sentences with timing), PaHaW (Parkinson's handwriting; a licence agreement) and OnHW (no licence stated, so permission first; right-handed writers only, and its time stamps are the tablet's processing times, LIT EML-82). Record each licence in the registry before any use.
- **Measurands.** Licence obtained and recorded, per set.

<!-- AC-TABLE:EXP-R06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R06-01 | REQ-DATA-006 | IAM-OnDB, PaHaW and OnHW (review): used only after the registration, licence agreement or permission is obtained and recorded in the source registry; results from research-only or non-commercial sources hold statistics only | conforms | requirement | REQ-DATA-006; IAM-OnDB needs registration, PaHaW a licence agreement, and OnHW states no licence (LIT EML-82); UNIPEN, BRUSH, PADS and NewHandPD are already held to statistics only (docs/real_data.md) | larger real-writing test sets (DEC-054) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-R06).
<!-- AC-TABLE:EXP-R06:END -->

- **Decision rule.** Obtained: the set joins the library under its licence, for a larger test split. Refused: it stays out.

### EXP-R07: Is DeltaPen's window error the sensor's or the reference's?

- **Purpose and gates.** Measure a pen-tip optical-flow sensor on paper against a finer reference than DeltaPen's Wacom, and replace the pessimistic DeltaPen-class page model with the measured one. Gates REQ-DATA-007 and, through the model, every tracker results card.
- **Runs inside EXP-T04 and EXP-T05 on rig R10** (§47): the same sessions and records, no separate runs, with EXP-J10's addition. R10's truth is 0.38 µm per 10 ms window with the Zaber stages and 2.6 µm with the LM13 encoders (`docs/measurement_rig.md` §3.4), far finer than a Wacom's (about ±0.4 mm class, MFR AMF-98), so the error it measures is the sensor's. The window error uses DeltaPen's own metric, with the vector metric beside it (DEC-059), as AC-J10-04.
- **Predictions.** The DeltaPen-class model gives all of DeltaPen's error (median 23.6 µm, mean 68.3 µm per 10 ms window, on a Wacom surface, LIT OPT-02) to the sensor, so it is pessimistic. No measurement on paper exists.
- **Procedure.** From EXP-T04's records of the die chosen for the pen: fit the library's page model (`realdata/sensors.py`: window error against movement and its spread, drift, scale error, dropouts; latency from EXP-T05) on half of the runs, and check it on the other half. Then re-run EXP-R02 with it, keeping the DeltaPen-class model as the pessimistic bound.
- **Measurands.** Window error (median and mean) per movement class; latency; dropouts; the refitted model's parameters.

<!-- AC-TABLE:EXP-R07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-R07-01 | REQ-DATA-007 | Page model of the realdata library refitted on half of the EXP-T04 records of the chosen die on paper (window error against movement and its spread; drift, scale error and dropouts; latency from EXP-T05): the 10 ms window error it predicts on the other half, by DeltaPen's metric (DEC-059), median and mean | within ±20 % of the measured values | hypothesis | engineering judgement: with the DeltaPen-class model the trackers' results changed by at most 0.1 word against the ideal sensor (SIM); that model gives all of DeltaPen's error (LIT OPT-02, on a Wacom surface) to the sensor and reproduced 27 and 76 µm against 23.6 and 68.3 µm on the clean test notes (CALC); R10's truth is 0.38-2.6 µm per window (docs/measurement_rig.md s3.4) | REQ-DATA-007 (the measured model replaces the DeltaPen-class one in every tracker simulation) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-R07).
<!-- AC-TABLE:EXP-R07:END -->

- **Decision rule.** Pass: the measured model replaces the DeltaPen-class one in every tracker simulation (REQ-DATA-007). Fail: a richer model, such as sim2j's held-and-walking model from EXP-J10's addition.

---

## 49. Spelling help, prediction and clearer handwriting: EXP-S16, S19, S20, S21 (study S; DEC-056, DEC-057)

### Purpose and what it gates

Study S (`docs/spelling_and_clarity.md`) built the language layer of the pen and the app: a causal streaming recogniser, spelling help trained on real misspellings, personal text prediction, and a writing plan for accepted words. It also explained why close tracing made letters harder to read, and tested a shape assist. **Nothing was measured on people or on a pen.** The numbers are CALC on real letters of held-out writers and real misspellings of held-out children, or SIM with the writers' responses ASSUMED.
- **DEC-056.** Language help is a separate layer with three outputs: the ink record, the transcript and the pen's writing plan are kept apart (REQ-APP-005). A causal streaming recogniser, calibrated on the user's own letters, reads the letters. Spelling help scores several readings, abstains when unsure, and never flags names, numbers or words the writer marks (REQ-APP-007). The default cue is a tick at the next pause, and completions come only at pauses (REQ-APP-008). The pen writes only accepted text, through a plan that starts a letter only when all of it fits within reach (REQ-CTRL-014). This feeds DEC-049's autowrite.
- **DEC-057.** Nearest-point close tracing is retired for letters. Guidance advances along the letter and checks that every part is drawn (EXP-S16, then EXP-D08). The shape assist is not adopted (EXP-S15 and S21 come only after a redesign). Clearer text on screen comes from the app's clean copy, whose tremor detector must be made stricter (EXP-A03, AC-A03-04 and AC-A03-05).
- **What the study found.** The recogniser names 82 % of letters by the end of the letter (86 % calibrated). With a language model one word in five is still read wrong. With the letters known, the checker catches 63 % of children's real misspellings at 2.3 false alarms per 100 correct words; with the pen's own reading, 34 % at 1.7 (a post-hoc design). A tick at the next pause gets 3.0 of 10 misspellings fixed on paper, and a tick plus a pen lift 3.4. Completion after one letter is in the top 3 52–56 % of the time. An accepted word is written in full at ±6 mm of reach in 95 % of cases, and at ±4 mm in 23 %.
- **Studies with people.** EXP-S10…S15, S17 and S18 are in [`human_study_plan.md`](human_study_plan.md) §22.
- **One run, several scorings.** EXP-S19 runs on EXP-N08's set-up with the same firmware and SIM gate. EXP-S20 uses EXP-S18's data. EXP-S21 needs EXP-R04 (DiaGraMo in the library) first.

### EXP-S16: Close tracing with guidance that advances along the letter

- **Purpose and gates.** Test whether a guidance law that advances along the letter and checks that every part is drawn keeps letters readable, against the nearest-point law. Gates DEC-057 and EXP-D08's tracing arms.
- **Relation to EXP-D08.** The same tracing task and learner profiles. This bench run comes first; the chosen law then becomes an arm of EXP-D08 with people (`human_study_plan.md` §16).
- **Predictions (SIM; the drive study's runs, 6 test writers × 4 seeds; `docs/spelling_and_clarity.md` T5).**
  - With nearest-point close tracing (heel wheel and nose), the app read 79 % of letters against 92 % unguided, but a page reader read 72 % against 70 %. The app's reader reads letters in writing order, so it reacts to how the ink was laid down.
  - 4.2 % of each letter's path was left undrawn (2.0 % unguided). Redrawing the drawn parts in the letter's own order recovered 58 % of the lost letters; snapping the ink onto the letter, 9 %.
  - The progress-aligned law has not been simulated.
- **Set-up.** The heel drive and nose prototype, after EXP-D07. R14's grip simulant on R13's stage moves the pen along the drive study's learner paths, as a passive hand. R3 scans. The app's reader and an order-free page reader.
- **Procedure.** Three conditions in random order: unguided, the nearest-point law, the progress-aligned law (DEC-057). 4 seeds per learner profile. Scan; read blind with both readers; measure each letter's undrawn share.
- **Measurands.** Share of each letter's path with no ink within 1 mm; letters read by both readers; ink running backwards along the letter.

<!-- AC-TABLE:EXP-S16:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S16-01 | — | EXP-D08's tracing task on the bench (heel drive and nose; the stage moves the pen along the learner profiles' paths): with the progress-aligned guidance law, the share of each letter's path with no ink within 1 mm, and the letters read by the app's reader and by a page reader relative to unguided (both) | both met (≤ 5 % undrawn; letters read no fewer than unguided) | hypothesis | pass line of study S; SIM with nearest-point close tracing: 4.2 % undrawn (2.0 % unguided), letters read 92 -> 79 % by the app's order-sensitive reader and 70 -> 72 % by a page reader (docs/spelling_and_clarity.md T5); the progress-aligned law not yet simulated | DEC-057 (guidance for letters); EXP-D08's tracing arms |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S16).
<!-- AC-TABLE:EXP-S16:END -->

- **Decision rule.** Pass: the progress-aligned law becomes the guidance law for letters, and EXP-D08 uses it (DEC-057). Fail: guidance for letters stays off until a law passes, and EXP-D08's tracing arms wait.

### EXP-S19: Writing an accepted word with a reach-limited nib while the hand moves

- **Purpose and gates.** Check the writing plan of REQ-CTRL-014 on the bench. An accepted word is written in full only with enough reach and a moving hand, and a hand-back must never leave half a letter. Gates REQ-CTRL-014, DEC-056 (f) and DEC-049's autowrite of accepted words (REQ-RVJ-N07, N08).
- **Relation to EXP-N08.** It runs on EXP-N08's set-up (R13 after EXP-T13), with the same firmware and SIM gate (AC-N08-01, AC-N08-03). EXP-N08 writes a known line while the stage sweeps; EXP-S19 writes accepted words while the stage replays recorded hand advances. The two share sessions.
- **DEC-050 (2026-09-30).** Autowrite of accepted words is a research mode on the bench with the C1S nose. The product's B1 nib reaches ±1.0 mm, which writes no accepted word in full (none at ±1–2 mm, below). This experiment tests the research mode; REQ-CTRL-014 now says so.
- **Predictions (SIM, kinematics only; `docs/spelling_and_clarity.md` T9).**
  - 100 completions (the rest of words of 5 or more letters) in 20 test writers' own letters at a 3 mm x-height. The part the pen writes is 11.8 mm long (median).
  - Written in full with a steady hand: 95 % at ±6 mm, 23 % at ±4 mm, 4 % at ±3 mm, none at ±1–2 mm. With a still hand, 2 % at ±6 mm; with a hand that runs ahead, 1 %.
  - Letter admission leaves no half letter per 100 completions with steady, slow or still hands, and 8 with hands that pause or run ahead (point by point: 2–99).
  - With a steady hand the pen takes 1.01 × the writer's own time.
- **Set-up.** The nose on R13 (usable reach ±6.0 mm, REQ-RVJ-N01; a software stop at ±4 mm for the smaller reach). The stage replays recorded hand advances: steady, slow, pausing, running ahead, still. Accepted words in the writer's own letters, from the calibration pangram. A camera or digitiser for the ink; the plan's logs.
- **Procedure.** Each hand profile at each reach, 20 words each, in random order. Scan and read blind. Count the words written in full, the half letters and the ink gaps. Log the plan's waits, lifts and hand-backs.
- **Measurands.** Words written in full (coverage); half letters and ink gaps (missing strokes); reach used; time against the writer's own (completion time), as REQ-WP-011 asks.

<!-- AC-TABLE:EXP-S19:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S19-01 | REQ-CTRL-014 | Accepted words written in full with a steady hand advance at the design reach (the stage replaying recorded hand advances; the nose's guaranteed ±6.0 mm, REQ-RVJ-N01), 3 mm x-height, in the writer's own letters | ≥ 90 % | hypothesis | pass line of study S; SIM, kinematics only: 95 % at ±6 mm, 23 % at ±4 mm and 4 % at ±3 mm with a steady hand (docs/spelling_and_clarity.md T9) -> passes only at the Rev J nose's reach | DEC-049 and DEC-056 (f) (autowrite of accepted words); DEC-050: autowrite is a bench research mode with the C1S nose |
| AC-S19-02 | REQ-CTRL-014 | Every hand profile (steady, slow, pausing, running ahead, still) with letter admission: half letters left on the page (R3 scans); and the plan's logs: a letter starts only when all of it fits the usable reach, the nib slows or waits when the hand lags, lifts after 0.5 s without progress, and hands back after 2 s without progress or when the hand runs ahead (both) | both met (no half letter; conforms) | requirement | REQ-CTRL-014 (rule C1); SIM, kinematics only: with letter admission 0 half letters per 100 completions with steady, slow or still hands and 8 with hands that pause or run ahead (2-99 point by point) (docs/spelling_and_clarity.md T9) -> predicted to FAIL for pausing and running-ahead hands | DEC-056 (f); EXP-N09 with accepted words; DEC-050: autowrite is a bench research mode with the C1S nose |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-S19).
<!-- AC-TABLE:EXP-S19:END -->

- **Decision rule.** Pass: this plan writes accepted words in autowrite (DEC-056 (f), DEC-049). Fewer than 90 % in full at the design reach: autowrite of accepted words waits for more reach or a slower sweep. Any half letter: fix the admission rule before EXP-N09 uses accepted words.

### EXP-S20: Is the spelling score calibrated for new users and devices?

- **Purpose and gates.** Confirm the post-hoc rule W5 and the calibration of P(misspelled) on new users and devices, offline on EXP-S18's data. Gates REQ-APP-007 (ECE ≤ 0.05) and DEC-056, which is revisited if W5 or the calibration is not confirmed.
- **Predictions (SIM, 11 test children, the pen's own reading; `docs/spelling_and_clarity.md` T8).** 34 % of misspellings caught at 1.7 false alarms per 100 correct words with the new-writer recogniser, and 28 % at 2.3 when calibrated. ECE 0.06–0.08 raw and 0.03 after Platt scaling. W5 was written after the planned rule failed (1–3 % caught), so these numbers are post hoc.
- **Set-up.** EXP-S18's recordings and transcripts, with consent for this use (`human_study_plan.md` §3.3). The frozen W5 score, with Platt scaling fitted on other users, per device.
- **Procedure.** Score each user's words. Draw reliability diagrams per user and per device. Refit the temperature per user after 200 words and score the rest. Find the detection at ≤ 2 false alarms per 100 correct words.
- **Measurands.** ECE per user and device, and pooled; detection at ≤ 2 false alarms per 100 correct words; suggestions shown, and right when shown.

<!-- AC-TABLE:EXP-S20:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S20-01 | REQ-APP-007 | Expected calibration error of P(misspelled) on held-out users (EXP-S18's data; the W5 score with Platt scaling fitted on other users), pooled | ≤ 0.05 | requirement | REQ-APP-007 (DEC-056 (c)); SIM on 11 test children: 0.06-0.08 raw and 0.03 after Platt scaling (post-hoc rule W5; docs/spelling_and_clarity.md T8) | DEC-056 (revisited if not confirmed) |
| AC-S20-02 | REQ-APP-007 | Users (and devices) whose own ECE of P(misspelled) is ≤ 0.05, with the temperature refitted per user after 200 words | ≥ 80 % | hypothesis | pass line of study S; no per-user result exists (the SIM pooled 11 test children; docs/spelling_and_clarity.md T8) | DEC-056 |
| AC-S20-03 | — | Misspellings caught at ≤ 2 false alarms per 100 correct words with the pen's own reading and the W5 score, new users (EXP-S18's data), with the 95 % interval over users | the interval's upper bound reaches W5's result (34 % with the new-writer recogniser; 28 % calibrated) | hypothesis | confirms the post-hoc rule W5, written after the planned rule W2 caught 1-3 % (DEC-056 is revisited if EXP-S20 fails to confirm it); SIM: 34 % at 1.7 and 28 % at 2.3 false alarms per 100 correct words (docs/spelling_and_clarity.md T8) | DEC-056 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-S20).
<!-- AC-TABLE:EXP-S20:END -->

- **Decision rule.** Pass: the calibrated score stays the spelling layer's (DEC-056). Fail: the cue stays at the next pause, suggestions come only on request, the automatic mode stays off, and DEC-056 is revisited.

### EXP-S21: Shape assist and spelling cues on children's handwriting with dysgraphia

- **Purpose and gates.** Test the shape assist and the spelling layer offline on real children's handwriting, with and without dysgraphia. Gates DEC-057 (the shape assist stays out unless a redesign helps here) and the practice functions for children (EXP-W05, EXP-L08, EXP-G07).
- **Needs EXP-R04 first:** DiaGraMo (CC BY 4.0) in the library, with its licence recorded and the children split before any use (AC-R04-01).
- **Predictions.** None: the set is not yet used. On adults' real letters the shape assist changed the letters read by less than one point (`docs/spelling_and_clarity.md` T6).
- **Set-up.** DiaGraMo through the task-1 recogniser, calibrated on each child's letters (a recogniser with the Czech diacritics, or a letter subset), and the shape assist in model HW1. Letters read by study R's word reader and by the per-letter reader.
- **Procedure.** Replay each test child's writing with and without the assist. Score the letters and words read, and the ink moved on the children's clean letters.
- **Measurands.** Letters and words read with and without the assist; ink moved on clean letters.

<!-- AC-TABLE:EXP-S21:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-S21-01 | — | DiaGraMo test children (with and without dysgraphia) replayed in HW1 through the recogniser calibrated on each child's letters: letters read with the shape assist against without (study R's word reader and the per-letter reader), and ink moved on the children's clean letters (both) | both met (≥ 10 % more letters read; ≤ 25 µm) | hypothesis | EXP-S15's line applied offline (pass line of study S); no prediction: the set is not yet used (EXP-R04); on adults' real letters the assist changed the letters read by under one point (docs/spelling_and_clarity.md T6) | DEC-057 (a redesigned assist before EXP-S15); the practice functions for children |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-S21).
<!-- AC-TABLE:EXP-S21:END -->

- **Decision rule.** Pass: a redesigned assist may go to EXP-S15 with people. Fail: the shape assist stays out for children too (DEC-057).

---

## 50. Shifting the whole pen: EXP-W11, W13, W14, W15, W17 (study W; DEC-051…DEC-053)

### Purpose and what it gates

Study W (`docs/whole_pen_shift.md`) asked whether shifting the whole pen could handle larger tremor than the moving nose. Its strongest design is a collar: a held sleeve, 21.7 mm across and 40.1 g in total, with the inner pen on a two-axis flexure pivot about 50 mm behind the tip. A coil plate in the sleeve's rear wall swings the inner pen ±4.6°, reacting on the sleeve, which gives ±4 mm at the tip. **Nothing was built or measured.** The numbers are CALC, and SIM on two synthetic test writers with one seed each and at study R's real tremor sizes.
- **DEC-051.** No whole-pen actuator in the product now; the moving nose stays the part that shifts the ink; inertial tails are rejected for the pen. The collar stays a bench experiment (EXP-W11). The end-cap stays only as a bench comparison against the same mass locked (EXP-J16, W14). DEC-051 is revisited if EXP-W10 finds writers whose tremor at the ink exceeds the nose's reach (about ±6 mm) while writing, or if the collar mock-up beats the same pen with it locked by ≥ 10 % without losing ink.
- **DEC-052.** The tremor estimate is the priority. In every study the gap between today's causal estimates and perfect knowledge of the tremor is far larger than anything added mechanics gave. Study E chooses the estimator on real inputs under DEC-055; DEC-047's G4 stays the default meanwhile; study W's candidate (GLG) goes into study E (EXP-W15).
- **DEC-053.** Any added device is judged against the same pen with that device locked and the existing corrector working, at three grip strengths, on a measured-style page sensor, with coverage, missing strokes and completion time for any gated mode, and with power that includes the nib's static load (REQ-WP-001, WP-011, WP-012).
- **What the study found (SIM).** With the 87 g Rev J pen inside, the collar changed the tremor left by −5 % to +5 % against the same pen with it locked and the nose working. With perfect knowledge, sharing the correction with it was worse than the nose alone (3 mm ET: 0.66 against 0.24 mm). With a light 24 g inner pen it left 17 % less tremor at 8 mm PD but laid 17 points less ink, so no more words were read. At study R's real sizes no extra travel was needed. With the pen's best causal estimate the nose left 1.1–1.4 mm of a 3 mm tremor; with perfect knowledge, 0.14–0.24 mm.
- **Requirements.** REQ-WP-001 applies to anything that would shift the pen. REQ-WP-002…009 apply to the collar mock-up, and to any product collar that later passes REQ-WP-001. REQ-WP-010 applies to tail modules, and REQ-WP-011 and 012 to every report.
- **Studies with people.** EXP-W10, W12 and W16 are in [`human_study_plan.md`](human_study_plan.md) §23.
- **Rigs (study M).** The G5 comparisons of the collar (EXP-W11) and the tails (EXP-W14) are conditions of EXP-T16 on R14 (§47), judged by AC-T16-01 (now REQ-WP-001's criterion), as the end-cap's are (EXP-K02, J16). EXP-W13 runs on R13 over R9's plate, in the set-up of EXP-J17 and T12.

### EXP-W11: Does the collar move the ink as calculated, and does it beat the same pen with it locked?

- **Purpose and gates.** Build the V2 collar as a bench mock-up and check its transmission, holding power, stability, fit and stops. Its G5 comparison decides DEC-051's revisit. Gates REQ-WP-001 (through AC-T16-01), REQ-WP-002, 003, 005, 006 and 008, and DEC-051.
- **Rig (study M).** The phantom is R14's grip simulant on R13's stage, and the G5 part (collar active against the collar locked, with the same nib working, at three grip strengths) is a condition of EXP-T16 (§47), judged by AC-T16-01. REQ-WP-001 sets the grip strengths at 0.5, 1 and 2 × nominal (study W's phantom springs: 300, 575 and 1100 N/m); R14 sets them by squeeze (2, 4 and 8 N), and its leaf sets give 211, 500 and 977 N/m (CALC). The rig design picks the settings (open, `README.md` §7). The paper lies on R9's plate, so the force path can be checked.
- **Predictions (CALC, SIM; `docs/whole_pen_shift.md` §3d, §4).**
  - Collar 21.7 mm across, 12 mm barrel, 40.1 g in total; ±4 mm at the tip (±5.2 mm across the page in the tilt plane). The swung inner pen clears the sleeve by 0.72–1.00 mm and the coil plate by 0.52 mm (CALC on the CAD).
  - Holding power with the ball on the paper: 0.16 / 0.055 / 0.006 W at 35 / 50 / 75° (Rev J's nose: 4.72 / 1.63 / 0.17 W).
  - A prescribed swing moved the ink within 1–3 % of the linear model, with the ball on the paper 99.8–100 % of the time (SIM).
  - With one fixed model the loop keeps a margin ≥ 0.93 over grip 0.5–2 × and split 0.3–0.7, with the web on the collar (CALC). With the web on the barrel the ink moves 0.58–1.23 × the ideal lever.
  - Against the same pen with the collar locked and the nose working: −5 % to +5 % (SIM). The pivot reached its stops at 8 mm (0.16–0.18 rad against 0.12).
- **Set-up.** The V2 mock-up: a 3D-printed sleeve, a cross-strip flexure pivot at 50 mm, a two-axis coil plate under magnets on the barrel's end face, and a 12 mm barrel with a refill and the paper-following front stop. The phantom with swappable grip springs and split variants, on the shaker (R13). Paper on R9's plate. Optical ground truth of the ink (R13's camera, R3 scans).
- **Procedure.**
  1. Weigh and measure; check the fit at full swing (feeler gauges, or CT of the assembly).
  2. Transmission: swept sines at 2–12 Hz and ±1–5 mm at the tip, ball on the paper, at 35, 50 and 75°; web on the collar, then on the barrel.
  3. Current at rest while writing with the ring loaded, at each tilt.
  4. Closed loop with one fixed controller model: 3 mm tremor at 5–9 Hz on the phantom, three grip strengths. First the phantom's known tremor as the reference (oracle), then the causal estimator.
  5. 8 mm at 5 Hz with the stop-approach limiter: pivot angle and stop contacts.
  6. The G5 conditions in EXP-T16: collar active against locked, the same nib working, the same seeds, three grip strengths.
- **Measurands.** Ink moved against the model; tip travel; holding current and power; loop margins; tremor removed; pivot angle and stop contacts; coverage.

<!-- AC-TABLE:EXP-W11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W11-01 | REQ-WP-002 | Collar mock-up as built: collar diameter, inner barrel diameter, mass (with dummy masses for the parts it lacks, such as the cell and board), and tip travel at 4-10 Hz under a 1 N writing load (optical ink truth) (all) | all met (≤ 22 mm; ≤ 12 mm; ≤ 55 g; ≥ ±4 mm) | requirement | REQ-WP-002 (DEC-051); PROPOSED DESIGN (CALC): 21.7 mm, 12 mm barrel, 40.1 g, ±4 mm at the tip for ±4.6° (docs/whole_pen_shift.md s3d) | DEC-051 (the collar mock-up) |
| AC-W11-02 | REQ-WP-003 | Static holding power (coil power holding the inner pen centred against the refill spring's side load, ball on the paper, skid ring loaded, 60 s) at 35 and 50°; and the force path (the refill's axial load at the ball equals its spring's force; the rest of the writing force goes through the skid ring, R9's plate) (all) | all met (≤ 0.2 W at 35°; ≤ 0.06 W at 50°; conforms) | requirement | REQ-WP-003 (DEC-051); CALC 0.16 / 0.055 / 0.006 W at 35 / 50 / 75° with the coil plate, against Rev J's nose 4.72 / 1.63 / 0.17 W (docs/whole_pen_shift.md s3a, s3d); the coil plate's force constant is scaled from the Rev J nose's contested image-method value (open issue 7) | DEC-051; DEC-053 (power with the nib's static load) |
| AC-W11-03 | REQ-WP-006 | Closed loop on the hand phantom with one fixed controller model, web on the collar, 3 mm tremor at 5-9 Hz, grip 0.5, 1 and 2 x nominal: stability (no limit cycle, margins from the loop's response) and the tremor removed at the ink, with the reference from the phantom's known tremor (as EXP-T10's oracle); the causal estimator reported beside it (both) | both met (stable at every grip; ≥ 50 % removed) | requirement | REQ-WP-006 (DEC-051); CALC: margin ≥ 0.93 over grip 0.5-2 x and split 0.3-0.7 with the web on the collar; SIM with perfect knowledge the collar alone removed 64 % of a 3 mm, 6 Hz tremor (tuning writer); as the main corrector behind a ±1 mm nib with today's estimate the loop became unstable (docs/whole_pen_shift.md s3d, s4.4) | DEC-051 |
| AC-W11-04 | REQ-WP-008 | 8 mm tremor at 5 Hz on the phantom (three grip strengths) with the stop-approach limiter on: the pivot reference as a share of its range, and hard-stop contacts (pivot sensing, contact switch) (both) | both met (≤ 65 %; 0 contacts) | requirement | REQ-WP-008 (DEC-051); SIM without a limiter the pivot reached its 0.12 rad stops at 8 mm (peaks 0.16-0.18 rad), even with the reference held to 65 % (docs/whole_pen_shift.md s4.3, open issue 4) -> fails until a limiter is designed | DEC-051 |
| AC-W11-05 | REQ-WP-005 | Fit of the mock-up at full swing: clearance between the swinging barrel and the sleeve and web saddle (feeler gauges or CT of the assembly), and the saddle's reach along the pen (both) | both met (≥ 0.3 mm; saddle to z ≥ 97 mm) | requirement | REQ-WP-005 (DEC-051); CALC on the CAD: the swung inner pen clears the sleeve by 0.72-1.00 mm and the coil plate by 0.52 mm (docs/whole_pen_shift.md s9) | DEC-051 |
| AC-W11-06 | — | Ink moved by a prescribed swing (open loop, sines 2-12 Hz, ±1-5 mm at the tip, ball on the paper at 35, 50 and 75°, web on the collar) against the linear model (z_p x angle sideways; z_p x angle / sin(θ) in the tilt plane) | within ±20 % of the model | hypothesis | the project's pass line for a model check (as AC-K01-01, AC-J17-01); SIM: within 1-3 % of the linear model with the ball on the paper 99.8-100 % of the time (docs/whole_pen_shift.md s3d; results/wholepen/verification.json) | DEC-051 (the collar's model); the simulator's collar |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-W11).
<!-- AC-TABLE:EXP-W11:END -->

- **Decision rule.** AC-T16-01 passes with the collar (≥ 10 % over locked at every grip strength, without losing ink): DEC-051 is revisited. Otherwise the collar stays the bench reference for shifting the whole pen. The lines here judge the mock-up, not a product.

### EXP-W13: Does the ball stay on the paper during large corrections?

- **Purpose and gates.** Measure ball contact when Rev K's B1 nib corrects at its full travel (±1.0 mm; DEC-050, DEC-060) and when the collar corrects ±4–8 mm at tremor rates, and check the collar's paper-following front stop. Gates REQ-WP-004, and any severe-tremor correction claim (whether it can keep the ink).
- **Rig (study M).** R13 with the paper on R9's plate, in the set-up of EXP-J17 and EXP-T12 (the same tilts, plate and nib holder), which measure the static side load; the plate's normal force gives the ball's load and contact. B1's runs sit within EXP-T11's amplitude ladder (up to 2 mm), and the collar's large swings extend it. They share sessions.
- **Predictions (SIM; §3d, §4.4 and open issue 1).**
  - At 8 mm the ball stayed on the paper only 44–77 % of the time whenever the nose or the collar corrected hard, even with perfect knowledge, against 88–96 % with nothing moving.
  - Those runs used the Rev J nose (±6 mm). B1 (DEC-050): its ball contact under ±1.0 mm corrections was not simulated; in study B's sim2 runs its counter-face stayed engaged 99.8 % of the contact time (SIM).
  - With the paper-following stop and a ±0.05 rad, 6 Hz swing the ball stayed on the paper 99.8 % of the time; with a stop that follows only the pivot angle, 70 % (development runs).
  - REQ-WP-004's formula gives about 6.0 mm of extension at the full ±4.6° swing and 35°. Its text says about 3.3 mm, and the simulated stop was bounded to 3 mm (open, `README.md` §7).
- **Set-up.** Rev K's two-axis B1 nib (EXP-T13's build) and the collar mock-up of EXP-W11 in R13's holder, over paper on R9's plate at 35, 50 and 75°. For B1 the stage moves up to ±2 mm at 5–6 Hz, so that the nib corrects at its full ±1.0 mm; for the collar it swings ±4–8 mm. A load cell on the collar's skid ring (the stop logic). R3 scans.
- **Procedure.** At each tilt, while writing lines, with and without correction (the same pen not correcting is the reference): B1 at disturbances of ±0.5, 1 and 2 mm; the collar at swings of ±4, 6 and 8 mm; both at 5 and 6 Hz. Then pen lifts with the ring unloaded, and scans for joined strokes.
- **Measurands.** Ball normal force and the contact share of pen-down time; the refill's extension; ink laid (coverage) and missing strokes; strokes joined across lifts.

<!-- AC-TABLE:EXP-W13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W13-01 | REQ-WP-004 | Collar mock-up swung ±4-8 mm at 5-6 Hz on paper at 35, 50 and 75° with the skid ring loaded: the refill's extension along the pen as it follows the paper; and pen lifts with the ring unloaded: strokes joined across the lifts (R3 scans) (both) | both met (extension ≥ z_p x swing x cot(θ_min) + 0.3 mm; no joined strokes) | requirement | REQ-WP-004 (DEC-051); SIM development runs: the ball stayed on the paper 99.8 % of the time with this stop and 70 % with a stop that follows only the pivot angle (docs/whole_pen_shift.md s3d); the formula gives about 6.0 mm at the full ±4.6° swing and 35°, the requirement's text says about 3.3 mm, and the simulated stop was bounded to 3 mm (validation/README.md s7) | DEC-051; the collar's front stop |
| AC-W13-02 | — | Ball contact with the paper (plate normal force above half the refill spring's force) as a share of pen-down time while correcting at 5-6 Hz, Rev K's B1 nib at its full travel (±1.0 mm, DEC-050) and the collar mock-up at ±4-8 mm, at 35, 50 and 75°, each against the same pen not correcting | no more than 5 points lower | hypothesis | the 5 points of REQ-WP-001's coverage bound applied to contact (engineering judgement); SIM at 8 mm: 44-77 % whenever the nose or the collar corrected hard, even with perfect knowledge, against 88-96 % with nothing moving (docs/whole_pen_shift.md open issue 1) -> predicted to FAIL at 8 mm. Re-pointed to Rev K (DEC-050): was the Rev J nose and the collar at ±4-8 mm; the 8 mm prediction above is study W's, with the Rev J nose; B1: no simulation of ball contact under correction; its counter-face stayed engaged 99.8 % of the contact time in study B's sim2 runs (SIM, docs/balanced_nib.md s1). Reach: with Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F, docs/readable_target.md s8: the Rev J nose with its travel cut, tuning split), so Rev K's nib makes no severe-tremor legibility claim (DEC-060) | any severe-tremor correction claim (whether it keeps the ink); DEC-050 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-W13).
<!-- AC-TABLE:EXP-W13:END -->

- **Decision rule.** Contact kept: severe-tremor correction can keep the ink, and every severe-tremor claim carries its coverage (REQ-WP-011). Contact lost, as predicted: no severe-tremor correction claim beyond the nib's comfortable range until the refill's force element or front stop is redesigned.

### EXP-W14: Do tail modules beat the same mass locked?

- **Purpose and gates.** Test tail modules only against the same mass locked (G5), at three grip strengths. Gates REQ-WP-010 and DEC-051 (tails rejected for the pen).
- **Rig (study M).** The tail conditions of EXP-T16 on R14 (§47), judged by AC-T16-01 (REQ-WP-001). The driven reaction mass is the 29.6 g end-cap of EXP-J16, so those runs serve both (one run, two scorings). The gyroscope pair runs only after its burst test and the checks of EXP-K06.
- **Predictions (CALC, SIM; §3b, §3c, §4.5).**
  - A tuned or a driven tail mass did no better than the same mass locked.
  - The 100 g gyroscopic tail beat its locked mass by 15 / 51 / −14 % at grips 0.5 / 1 / 2 × on the tuning writer, and by 9 % on test writer 0. It never beat the pen without a tail.
  - A gyroscope that could matter stores 5–18 J; the optimum at 100 g stores 6.4 J (CALC). Spin itself did not steady the pen (EXP-K07).
- **Set-up.** R14 on R13's stage. The tuned mass (40 g), the driven reaction mass (30 g: the end-cap) and the gyroscope pair (≤ 2 J, in a burst-test housing), each with a locked dummy of the same mass, centre of mass and inertia.
- **Procedure.** Before any run, the gyroscope pair's burst test at 1.2 × its design speed and a test of its over-speed trip. Then EXP-T16's conditions (none, locked, unpowered, active) at three grip strengths, 4–10 Hz, 10 seeds, in random order.
- **Measurands.** Tremor left at the tip; coverage; power; stored energy.

<!-- AC-TABLE:EXP-W14:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W14-01 | REQ-WP-010 | Gyroscope pair before any run: stored energy from the measured speed and inertia, the stress margin at 1.2 x the design speed (a burst excluded by design; burst-test housing), and the over-speed trip tested; guarded acceptance (all) | all met (≤ 2 J; ≥ 3; trips) | requirement | REQ-WP-010 (DEC-051); the simulated 100 g gyroscopic tail stored 17.8 J at its starting design and 6.4 J at its optimum, and one that could matter stores 5-18 J (CALC, docs/whole_pen_shift.md s3b, s3g); REQ-EC-007 allows 3 J for the end-cap's CMG research module | gate before any gyroscope runs on the rig (with EXP-K06's methods) |
| AC-W14-02 | REQ-WP-010 | Test plan and records of every tail module (tuned mass 40 g; driven reaction mass 30 g, the 29.6 g end-cap of EXP-J16; gyroscope pair): compared only against the same mass locked (a dummy of the same mass, centre of mass and inertia), same seeds, at three grip strengths, 4-10 Hz | conforms | requirement | REQ-WP-010 (DEC-051, DEC-053); the G5 verdict itself is AC-T16-01 (REQ-WP-001) | DEC-051 (tails rejected for the pen) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-W14).
<!-- AC-TABLE:EXP-W14:END -->

- **Decision rule.** No tail passes AC-T16-01, as predicted: DEC-051 stands. One passes: the tail question is reopened with the lead (DEC-051 revisit).

### EXP-W15: How close can a causal estimate get to perfect knowledge on real writing?

- **Purpose and gates.** Measure the gap between the firmware's causal estimates and perfect knowledge on recorded writing, offline; this gap is the programme's largest lever (DEC-052). Check that the collar's command leaves clean writing alone. Gates DEC-052, REQ-WP-007 and REQ-WP-012.
- **One run, several scorings.** It uses EXP-R02's replays: study R's library now, and the EXP-H01/R01 and EXP-W10 recordings later. It adds study W's candidate estimate (GLG: the gated listening estimate with the guarded tracker as its fallback) and the collar's overflow command. DEC-052's verdict is AC-R02-01 (DEC-055's line), judged in EXP-R02; study E chooses the estimator.
- **Predictions (SIM).**
  - On study W's tuning writer, GLG removed about two thirds of a 3 mm, 6 Hz tremor where G4 removed about a tenth, and moved tremor-free writing 5 µm (with the Rev H tracker as its fallback, 135 µm).
  - On the test writers the nose left 1.1–1.4 mm of a 3 mm tremor with GLG, against 0.14–0.24 mm with perfect knowledge.
  - With the collar enabled, tremor-free writing moved at most 8 µm.
  - On real inputs at the severe class every tracker as built failed DEC-055's line (EXP-R02).
- **Set-up.** Study W's simulator (the Rev J nose and the collar) and model HW1, with the measured-style page sensor (REQ-WP-012). Study R's test split; later the recordings.
- **Procedure.** Replay each estimator (G4, GLG, the gated tracker, and the TCN of EXP-R05) with the nose, and with the collar and nose; perfect knowledge as the limit. Replay the test writers' tremor-free writing, checked by REQ-DATA-003, for false correction.
- **Measurands.** Tremor left at the tip, and its share of the perfect-knowledge limit; words read; clean writing moved with the collar enabled.

<!-- AC-TABLE:EXP-W15:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W15-01 | REQ-WP-007 | In the replay model (study W's simulator with the collar and the measured-style page sensor), real tremor-free writing of the test writers (checked by REQ-DATA-003), collar enabled: clean writing moved; and a firmware review that the collar is commanded only at a detected tremor line, only by the share beyond the nib's reach, never from letter shapes (both) | both met (≤ 25 µm; conforms) | requirement | REQ-WP-007 (DEC-051); SIM on synthetic writers: at most 8 µm with the collar enabled; the command is a phasor at the tracked tremor line, gated by the detector (docs/whole_pen_shift.md s3d, s4.3) | DEC-051; DEC-052 |
| AC-W15-02 | REQ-WP-012 | Every whole-pen result of EXP-W15 and study W's results cards (review): the measured-style page sensor (OPT-02 statistics) by default; 3 µm white noise only as a labelled bound | conforms | requirement | REQ-WP-012 (DEC-053; as REQ-DATA-007 for tracker results); study W used sim2j's DeltaPen-like walking model by default (results/wholepen/rules.json) | DEC-053 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-W15).
<!-- AC-TABLE:EXP-W15:END -->

- **Decision rule.** A causal estimate passes AC-R02-01: it becomes the candidate default, with study E (DEC-052). None passes: the help for severe tremor stays autowrite of accepted text and the app's clean copy (DEC-055).

### EXP-W17: Is an amplitude-gated paper force useful?

- **Purpose and gates.** Test the heel wheel's tremor mode switched on only above a detected tremor amplitude (the lead's note). Gates REQ-WP-001 for the paper force, and whether paper grounding joins a severe-tremor mode. DEC-048 keeps the wheel retracted by default.
- **Predictions (CALC, SIM; §3e).**
  - The paper can push back with at most its friction, 0.3–1.4 N, against about 1.7 N of tremor force through the grip at 3 mm and 4.6 N at 8 mm (CALC).
  - In development runs an idealised heel pushing 0.37 N in any direction removed about 15 % of a 3 mm tremor (SIM, tuning writer, an earlier firmware).
  - The present tremor mode helps only where the tremor is large or slow (4 Hz × 2 mm: 0.73 of the device-off error) and moves tremor-free writing 0.40 mm (sim2).
- **Set-up.** First sim2, where AC-L02-05 (REQ-RVJ-C02) judges the gated mode's clean writing. Then the heel-drive prototype on R14 over R13's stage, after the EXP-D07 safety gate.
- **Procedure.** Amplitude thresholds of 1 and 2 mm, chosen in sim2 first. Tremor at 1–3 mm and 8 mm, three grip strengths. The same pen with the wheel retracted and the nose working is the comparison. Tremor-free writing for false correction.
- **Measurands.** Tremor left at the tip; coverage; clean writing moved; felt force.

<!-- AC-TABLE:EXP-W17:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-W17-01 | REQ-WP-001 | Amplitude-gated heel wheel (tremor mode on only above a detected amplitude of 1-2 mm) with the nose, against the same pen with the wheel retracted and the nose working, same seeds, at 1-3 mm and 8 mm tremor, three grip strengths, in sim2 and then on R14: tremor left at the tip (lower 95 % bound) and coverage (both) | both met (≥ 10 % lower at every grip strength; coverage no more than 5 points lower) | requirement | REQ-WP-001 (DEC-051, DEC-053) for the paper force; CALC: paper friction 0.3-1.4 N against 1.7 N of tremor force through the grip at 3 mm and 4.6 N at 8 mm; development runs: an idealised heel pushing 0.37 N in any direction removed about 15 % of a 3 mm tremor (SIM, tuning writer, an earlier firmware) (docs/whole_pen_shift.md s3e) -> uncertain; the clean-writing line is AC-L02-05 (REQ-RVJ-C02) | DEC-048 (the wheel retracted by default); paper grounding in a severe-tremor mode |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-W17).
<!-- AC-TABLE:EXP-W17:END -->

- **Decision rule.** Pass (AC-W17-01, and AC-L02-05 on clean writing): the gated paper force may join the severe-tremor mode (DEC-048 revisit). Otherwise the wheel stays retracted in tremor modes.

---

## 51. The balanced nib B1: EXP-B25, B28, B30, B31, and where study B's other experiments run (study B; DEC-050)

### Purpose and what it gates

Study B (`docs/balanced_nib.md`) designed a nib that carries the ball's static side load with the ink spring instead of coil current (DEC-046). **Nothing was built or measured.** The numbers are CALC in `bnib/` (`results/bnib/bnib.json`) unless marked SIM (sim2: four synthetic writers, the project's frozen tracker, a page sensor calibrated to DeltaPen on a tablet, not on paper).
- **DEC-050 (2026-09-30).** The fast core of the next prototype is the B1 nib. The refill slides ±1 mm on two axes in a titanium carrier on four Ti-6Al-4V wires. Flat moving coils on the carrier sit between fixed N52 magnets, so there is no magnetic pull and no negative stiffness. A contact-driven counter-face balances the paper's push: the ink spring pushes the refill's rear end through a face kept parallel to the paper, so nothing is left across the pen at any tilt or roll. A follower stop releases the face when the ball lifts. The pen with B1, the heel wheel retracted (DEC-048) and no tail (DEC-051) is **Rev K**; study K laid it out (DEC-062…066, §53). Travel is ±1.0 mm for G3. The G4 nib is ±1.5 mm only if study E finds a causal estimator that uses the extra reach, else ±1.0 mm; study E found none, so it is ±1.0 mm (DEC-060). The refill spring force is frozen only after G1. DEC-046 is resolved. The C1S nose (DEC-036) is not carried forward: it stays a bench research module, and autowrite (DEC-049) a research mode with it (§43). The lead added on 2026-09-30: Rev K keeps a pen lift (the counter-face's follower-stop screw is the first candidate to lift the refill about 0.5 mm), and the nib's lowest structural mode stays at least 2.5 × the servo bandwidth with the ball free (362 Hz) and stuck (109 Hz) (REQ-BNIB-006). Study K rebuilt B1 for the pen: buildable coils, C17200 wire leads and a ball thrust guide (DEC-063), a counter-face head whose follower is the pen lift (DEC-064), and a 40 / 46 Hz servo (DEC-066).
- **Predictions.** Holding heat at most 1.6 mW at the worst tilt and roll (3.2 mW with K_m × 0.7), against REQ-RVJ-N10's 100 mW. Continuous power 7.6 mW at duty A (17.6 mW at 35°). Balance residual 5.3 mN mean (6 % of the unbalanced 96 mN), 13.1 mN at the 95th percentile. Travel ±1.06 mm under the 35° load with K_m × 0.7. 3.5 g moving at the tip; first parasitic mode 362 Hz; wire Goodman safety factor 3.25 for 43.2 M cycles. Pen 69 g; skin 30.6 °C in a 30 °C room; about 38 h per charge. SIM: B1 draws 14.8 mW while correcting and leaves 0.66 / 0.47 of the tremor's ink error at 8 / 12 Hz × 1 mm; readable words out of 10 rise from 6.4 to 8.1. The ink force drives the power: about 8 / 30 / 184 mW at 0.15 / 0.3 / 0.69 N.
- **What it gates.** DEC-050 is revisited if EXP-J17 part (c) (study B's EXP-B22) measures a residual side load above 25 % of F_s·cot θ or a face that does not release within 20 ms (→ the clutched bias b', then the unbalanced nib f); if EXP-T07 (B23) measures K_m below 0.7 × the model (→ larger poles); if EXP-T02 (B20) finds a minimum reliable ink force above about 0.3 N; if EXP-B25's wire coupons fail before 43.2 M cycles; if the sim2 ranking reverses with a page sensor measured on paper (EXP-T04, B32); or if EXP-W10 finds more than 25 % of the writers in a population with tremor at the ink beyond ±1.5 mm (AC-W10-02). Requirements: REQ-BNIB-001…017, with REQ-RVJ-N10 and REQ-RVJ-C04.
- **One id per experiment.** Study B proposed EXP-B20…B32 (`docs/balanced_nib.md` §4), mapped to gates G1–G4 and to study M's rigs. Nine are the same tests as existing experiments and run inside them; study M had placed four of its ids already (`docs/measurement_rig.md` §8.1). Four keep study B's ids and are specified below: EXP-B25, B28, B30 and B31. The table lists all thirteen.
- **Participants.** EXP-B30 records 10 writers with motion capture. It is covered by the ethics approval of EXP-B06 (§34).

### Where study B's experiments run

| Study B | Gate | Runs as | B1's criteria there | Note |
|---|---|---|---|---|
| EXP-B20 | G1 | EXP-T02 (R9, R3) | AC-T02-01 (DEC-050's 0.3 N line), AC-T02-04 (REQ-BNIB-014) | five tip types; 5 and 60 mm/s added to the speeds |
| EXP-B21 | G1 | EXP-T01 (R9) | EXP-T01's own (AC-T01-04, T01-05) | study M's mapping; the friction map goes into `config/nib.yaml` |
| EXP-B22 | G2 | EXP-J17 part (c), on a new fixture at R12 | AC-J17-04…07 (REQ-BNIB-001, 002, 016, 008) | study B: "extends EXP-J17"; B1's holding heat stays AC-J17-02 |
| EXP-B23 | G2 | EXP-T07 (force map, K_m, cross-coupling, R, L); EXP-T08 (keeper pull, K_m(T)) | AC-T07-01 (DEC-050's 0.7 × line), T07-02…04; AC-T08-01; study K's EXP-K22 adds AC-T07-05 | study M's mapping |
| EXP-B24 | G2 | EXP-T09 (R12) | AC-T09-03 (REQ-BNIB-009) | 23–60 °C |
| EXP-B25 | G2 | its own: R8 and a drop fixture (below) | AC-B25-01…04 (REQ-BNIB-007, 012; REQ-RVK-005) | study M's mapping: R8 fatigue; since DEC-098 the fatigue runs on study H's shuttle at no more than 0.2 × each coupon's first mode (§55) |
| EXP-B26 | G3 | EXP-T10 (R13, one axis, then two) | AC-T10-02 (REQ-BNIB-006), T10-05, T10-06 (REQ-BNIB-003, 005), T10-08 (DEC-066) | the two-axis part continues in EXP-T13 |
| EXP-B27 | G4 | EXP-T13 (R13, two axes) | AC-T13-04…06 (REQ-BNIB-004, 011, 013) | tremor left, clean writing and 500 touchdowns are AC-T13-01…03 |
| EXP-B28 | G2 | its own: R13 with a camera (below) | AC-B28-01, B28-02 (REQ-BNIB-015) | study M mapped it onto EXP-T06/T12; neither measures the IMU's error, so it keeps its id and uses their recordings and set-up |
| EXP-B29 | G4 | EXP-T15 (R13 in the 30 °C chamber) | AC-T15-01 (REQ-BNIB-010), T15-02, T15-03 | |
| EXP-B30 | G2 (optional) | its own: motion capture, with participants (below) | AC-B30-01 | the no-motor variant c'' |
| EXP-B31 | G3 (slim branch) | its own: the pencil rigs of EXP-Q04 and Q05 (below) | AC-B31-01 | a trade study, not the first prototype |
| EXP-B32 | G4 | EXP-T04 (R10), with EXP-R07's refit | AC-T04-07 (REQ-BNIB-017) | replaces the DeltaPen-calibrated page model in sim2 |

### EXP-B25: Do the wires survive the stop travel and a drop?

- **Purpose and gates.** Check that B1's four wires survive the stop travel for the pen's life and a 1 m drop, and measure the suspension's stiffness with real clamps. Gates REQ-BNIB-007 and REQ-BNIB-012, the wire diameter, the clamp design and the stops (G2), and DEC-050's revisit (a wire failure before 43.2 M cycles).
- **Rig (study M; DEC-098).** Study H's crank-driven fatigue shuttle (§55), at no more than 0.2 × each coupon's measured first mode. A drop fixture (new). The stiffness on R12's stage. *Was (before DEC-098):* R8's fatigue stations (§0.9), unchanged, as study M mapped it.
- **Predictions (CALC; `docs/balanced_nib.md` §5.2).**
  - Wires 0.128 mm × 26.8 mm free length, Ti-6Al-4V: lateral stiffness 3.8 N/m at the tip; suspension mode 5.2 Hz with the moving mass; violin mode 808 Hz.
  - At the stop travel: strain 0.68 × 10⁻³ and 139 MPa with Kt 1.8, so a Goodman safety factor of 3.25 for 43.2 M cycles (fatigue strength 530 MPa × 0.85: the low end of AMF-20 with an ASSUMPTION knock-down). With Kt 1.3–2.5 and the other tolerances (ASSUMPTION ranges), 1.62 / 1.77 / 2.49 at the 1st / 5th / 50th percentile.
  - The four wires buckle sideways at 0.08 N of compression, so any assembly preload dominates their stiffness: 0.3 N of tension triples it. The tolerance Monte Carlo gives 4.4 / 10.3 / 16.2 N/m at the 5th / 50th / 95th percentile. Study B proposes a set tension of about 0.1 N.
  - Drops: at 500 and 2000 g the 20 µm axial stops engage and the wires take 85 MPa; buckled wires stay elastic.
- **Set-up.** Wire coupons (Ti-6Al-4V grade 5, 0.128 mm) in laser-welded clamps with a 0.1 mm edge radius, and crimped clamps as the alternative. Study H's fatigue shuttle, with several coupons on one crank, a ground eccentric that sets the stroke, and each coupon's 4-wire resistance logged for crack detection (DEC-098); strain gauges on sacrificial coupons. Assembled four-wire suspensions with a carrier of B1's mass. The nib module in a handle for the drops. *Was (before DEC-098):* R8's stations with laser amplitude control and resonance tracking for crack detection.
- **Procedure.**
  1. The clamp's stress concentration from strain-gauged coupons at the stop travel.
  2. Stiffness at the tip, both axes, at zero tension and at the set tension (AC-B25-03).
  3. Each coupon's first transverse mode (a sine sweep or a tap). Fatigue at the stop travel to 43.2 M cycles, driven at no more than 0.2 × that mode (DEC-098; AC-BB04-05), at least 3 coupons per clamp type (§0.7); spares to failure. An open circuit or a step of more than 2 % in the 4-wire resistance stops a coupon for inspection at 50×.

     *Was (before DEC-098):* "Fatigue at the stop travel to 43.2 M cycles (about 60 h at 200 Hz), at least 3 coupons per clamp type (§0.7); spares to failure. A resonance shift stops a coupon for inspection at 50×." Driven near a wire's own resonance, the clamp sees stress the pen never does: study H calculates rises of 12–33 % at 200 Hz for 26.8 mm C17200 wires (first modes about 487–763 Hz) and about 90 % for 34 mm wires (`results/benchbuild/bench_calcs.json`); study B predicts an 808 Hz violin mode for these titanium wires.
  4. 1 m drops onto a hard floor in several orientations. After each drop: the axial stop travel, the stiffness and travel re-measured, and the face and its positioners inspected.
- **Measurands.** Kt; cycles without failure; the Goodman safety factor with the measured Kt; stiffness at the tip; stop travel; stiffness, travel and damage after the drops.
- **Study K (DEC-062, DEC-063).** Rev K's wires are C17200 and carry the coil currents; their coupons are EXP-K21 (§53), which repeats this procedure with current. This jig also measures the first Rev K build's offsets (the carrier's rest, the stops, the magnets and the coils), and the nib in its front, with the titanium stop bush, is dropped sideways from 1 m: AC-B25-04 (REQ-RVK-005). Prediction (CALC, tolerances ASSUMPTION): the running clearances fall to 0.21–0.26 mm at the 99th percentile, and in the drop the coils stay 0.04 mm off the bore (both marginal).

<!-- AC-TABLE:EXP-B25:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B25-01 | REQ-BNIB-007 | Ti-6Al-4V wire coupons (0.128 mm, 26.8 mm free length, laser-welded clamps) cycled at the stop travel at no more than 0.2 x each coupon's measured first transverse mode (DEC-098): cycles without failure (an open circuit or a step of more than 2 % in the 4-wire resistance), and the Goodman safety factor with the clamp's measured stress concentration (both) | both met (no failure in 43.2 M cycles; ≥ 1.5) | requirement | REQ-BNIB-007 (DEC-050's revisit trigger: a failure before 43.2 M cycles); CALC: Goodman safety factor 3.25 with Kt 1.8, and 1.62 / 1.77 / 2.49 at the 1st / 5th / 50th percentile of the tolerance Monte Carlo (Kt 1.3-2.5, ASSUMPTION; docs/balanced_nib.md s5.2); DEC-098: the drive is at most 0.2 x the first mode (AC-BB04-05; was about 200 Hz, about 60 h, with resonance tracking) | wire diameter and clamp design (DEC-050); DEC-063: Rev K's wires are C17200, tested in EXP-K21 (AC-K21-02, K21-04); validity: AC-BB04-05 |
| AC-B25-02 | REQ-BNIB-012 | 1 m drops onto a hard floor of the nib module in a handle, several orientations: axial stop travel, whether the wires stay elastic, and damage to the face and its positioners (inspection; stiffness and travel re-measured) (all) | all met (stops ≤ 20 µm; wires elastic; no damage) | requirement | REQ-BNIB-012; CALC (flexure.shock): at 500 and 2000 g the 20 µm stops engage and the wires take 85 MPa; buckled wires stay elastic (docs/balanced_nib.md s5.2); Rev K (DEC-063): the ball guide's sprung races carry the axial drop and the wires see at most the 20 µm before the hard stops, 95 MPa; the lateral titanium stop yields 0.26 mm (AC-B25-04) (CALC, docs/revK_design.md s3.3) | stops and snubbers (DEC-050) |
| AC-B25-03 | — | Lateral stiffness of the assembled four-wire suspension at the tip, at the set assembly tension (about 0.1 N) | within 4.4-16.2 N/m | hypothesis | the tolerance Monte Carlo's 5th-95th percentile (wire diameter ±2 %, length ±0.05 mm, modulus ±4 %, Kt 1.3-2.5, preload 0-0.3 N; ASSUMPTION ranges); 3.8 N/m at zero tension, and 0.3 N of tension triples it (CALC, docs/balanced_nib.md s5.2, s5.7); Rev K's 0.10 mm C17200 wires (DEC-063): 1.56 N/m at the tip (CALC, docs/revK_design.md s3.3), measured in EXP-K21 by the same method | the assembly tension; the servo's plant model |
| AC-B25-04 | REQ-RVK-005 | Rev K's nib as first built (DEC-062): the offsets of the carrier's rest, the stops, the magnets and the coils measured on EXP-B25's jig and propagated to the coil's clearance to the bore at the stop (99th percentile over the builds); and 1 m sideways drops of the nib in its front with the titanium stop bush: contact between a coil and the bore (witness coating, inspection) (both) | both met (≥ 0.2 mm at the 99th percentile; ≥ 0 mm, no contact, in the drops) | requirement | REQ-RVK-005 (DEC-062); CALC (tolerances ASSUMPTION): the 0.3 mm running clearances fall to 0.21-0.26 mm at the 99th percentile, the coil against the bore to 0.21 mm (s3.5); in a 1 m sideways drop the stop (1e6 N/m, ASSUMPTION) yields 0.26 mm and the coils stay 0.04 mm off the bore (fit check N21) (docs/revK_design.md s3.3) -> both marginal; the first build's offsets decide whether the clearances grow by 0.1 mm (s9) | the clearances and the stop (DEC-062); building Rev K's nib (prototype_stages.md s0) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-B25).
<!-- AC-TABLE:EXP-B25:END -->

- **Decision rule.** A failure before 43.2 M cycles, or a safety factor below 1.5 with the measured Kt: DEC-050's revisit (a thicker or longer wire, or another clamp). Stiffness outside 4.4–16.2 N/m: set the assembly tension and refit the servo's plant model. A wire that yields in a drop: stiffer stops or snubbers. Rev K's coil clearance below 0.2 mm at the 99th percentile, or a coil that touches the bore in a drop: the clearances grow by 0.1 mm, or the tolerances are held (study K §3.5).

### EXP-B28: Is the IMU good enough to set the face?

- **Purpose and gates.** The face is set from the pen's IMU. Measure the IMU's tilt and roll errors while writing, and the error on a sloped desk, where the IMU sees gravity but not the page. Gates REQ-BNIB-015, the face schedule's error budget, and whether a slope setting in the app or the slide cam (c') is needed (G2).
- **Rig (study M).** Study M mapped it onto EXP-T06 and T12 (`docs/measurement_rig.md` §8.1). It keeps its own id, because neither of those measures the IMU's error. It uses R11's recordings (EXP-T06) or study R's, and R13's tilt arc and roll ring (EXP-T12's set-up), with a camera for truth.
- **Predictions (CALC, ASSUMPTION; `docs/balanced_nib.md` §1, §5.7).**
  - The balance Monte Carlo assumed errors of 1° in tilt and 2° in roll (1 sigma); with them the residual is 5.3 mN mean.
  - The pen's tilt wobbles by about ±2.5° while writing (LIT CON-02). With a 0.2 s response the schedule lags it by about 2° at 1 Hz (about 5 % residual); a 0.05 s response halves that.
  - On a sloped desk the face is set for a level page. It leaves about 17 / 34 / 67 mN across the pen at 5 / 10 / 20° of slope, or about 2 / 7 / 28 mW of holding: inside REQ-RVJ-N10's 100 mW, but a large share of the balance.
- **Set-up.** The IMU on a board mounted as in the pen, with markers for the camera (or motion capture). The pen motions of 20 writers, with their tilt and roll wobble, replayed by a robot (R11's recording pen, EXP-T06), or study R's recordings where they carry a pose reference. Writing surfaces level and at 10 and 20° of slope. The face schedule's firmware, logging its commands.
- **Procedure.** Replay each writer on the level surface, then on the 10 and 20° slopes, in random order. Log the IMU's estimates, the schedule's commands and the truth. Repeat with the schedule's response at 0.2 s and at 0.05 s.
- **Measurands.** Tilt and roll errors of the schedule against the truth (1 sigma, per writer and pooled); the lag at 1 Hz; the tilt error relative to the page on the slopes.

<!-- AC-TABLE:EXP-B28:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B28-01 | REQ-BNIB-015 | IMU tilt and roll estimates of the face schedule while writing on a level desk: 20 writers' recorded strokes (R11, EXP-T06, or study R's recordings) replayed on R13's tilt arc and roll ring, against camera or motion-capture truth: 1 sigma errors (both) | both met (tilt ≤ 1°; roll ≤ 2°) | requirement | REQ-BNIB-015 (DEC-050); ASSUMPTION in the balance Monte Carlo (1 and 2°); the schedule lags the pen's tilt wobble (about ±2.5°, LIT CON-02) by about 2° at 1 Hz with a 0.2 s response (CALC, docs/balanced_nib.md s5.7) | the face schedule's error budget |
| AC-B28-02 | REQ-BNIB-015 | Tilt error of the face schedule relative to the page on 10 and 20° writing slopes, without a slope setting (the same replays) | ≤ 1° | derived | REQ-BNIB-015's 1° applied relative to the page, so derived; the IMU sees gravity, not the page: without a slope setting the error is the slope, leaving about 34 / 67 mN across the pen at 10 / 20° (7 / 28 mW of holding, within REQ-RVJ-N10's 100 mW) (CALC, docs/balanced_nib.md s1) -> predicted to FAIL: then a slope setting in the app or the slide cam (c') | a slope setting or the slide cam (c') |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-B28).
<!-- AC-TABLE:EXP-B28:END -->

- **Decision rule.** Level desk within the lines: the IMU schedule stands. Outside them: a faster schedule or better sensor fusion, and the balance Monte Carlo re-run with the measured errors. On the slopes (AC-B28-02, predicted to fail): a slope setting in the app, or the slide cam (c'), which reads the tilt relative to the paper.

### EXP-B30 (optional): How much does the pen roll in the hand with a keyed grip?

- **Purpose and gates.** The no-motor variant c'' drops the roll positioner and relies on a keyed (triangular) grip to hold the pen's roll. Measure the roll spread of a keyed grip across writers. Gates whether c'' is good enough (G2, optional).
- **Predictions (CALC; `docs/balanced_nib.md` §1, §2.1).** A keyed grip instead of the roll motor leaves 25.4 mN of mean residual, against 5.3 mN with the positioners; the grip's roll spread was ASSUMED. Variant c'' draws 15.2 mW at duty A and holds at most 21.0 mW at 35°. No measurement.
- **Set-up.** Unpowered dummy pens, 24 mm, with a keyed grip and with a round one; markers on the pen. Motion capture. 10 writers, right- and left-handed, under the ethics approval of EXP-B06 (§34).
- **Procedure.** Each writer copies a sentence and writes freely with each dummy, in random order. Motion capture records the pen's roll about its axis.
- **Measurands.** Roll spread (1 sigma) per writer and pooled, keyed and round; each writer's mean roll.

<!-- AC-TABLE:EXP-B30:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B30-01 | REQ-BNIB-015 | Roll of the pen in the hand with a keyed (triangular) grip while writing, 10 writers (motion capture): the spread (1 sigma) per writer and pooled | ≤ 2° | derived | REQ-BNIB-015's roll budget applied to the keyed grip, so derived; CALC: a keyed grip instead of the roll motor leaves 25.4 mN of mean residual against 5.3 mN with the positioners (the grip's roll spread ASSUMED); no measurement | the no-motor variant c'' |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-B30).
<!-- AC-TABLE:EXP-B30:END -->

- **Decision rule.** Pass: c'' (no roll motor) stays a candidate, with its residual re-computed from the measured spread. Fail: B1 keeps its roll positioner.

### EXP-B31 (slim branch): Piezo bender stage coupon

- **Purpose and gates.** A 12–16 mm core cannot hold a magnet-and-coil nib around a D1 refill; piezo benders fit. Check a bender stage's force-travel line, loaded resonance and drive power against study B's piezo model. Gates the slim core's feasibility: a trade study, not the first prototype (DEC-050).
- **Rig.** The pencil rigs of EXP-Q04 (the benders' stroke, force and strength) and EXP-Q05 (the driver's power) (§29, §30).
- **Predictions (CALC, SIM; `docs/balanced_nib.md` §2.2, §3).**
  - With the counter-face the slim stage reaches ±0.56 mm with 29.7 mW (CALC).
  - The 14 mm card (h'): ±0.47 mm under load and 35.3 mW with the boost; bandwidth (first parasitic mode / 3) 49 Hz; pen 31.8 g (CALC).
  - SIM: the slim stage (B3, ±0.32 mm under load) left 0.86 of the tremor's ink error with the tracker and 0.50 with perfect knowledge, at 32 mW of drive power.
- **Set-up.** A one-axis stage coupon: PICMA-class plates on a lever-2 stage, a D1 refill under its static load, the counter-face behind it. EXP-Q04's methods for stroke and force; EXP-Q05's charge-recovery driver and current logging.
- **Procedure.** Free stroke and blocked force at the lever (0–60 V); travel under the static load at 35–75°; the loaded resonance by a swept sine; drive power at the design duty. Each against the model at the same conditions.
- **Measurands.** Free stroke, blocked force, loaded travel, loaded resonance, drive power.

<!-- AC-TABLE:EXP-B31:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-B31-01 | — | Slim-core piezo stage coupon (PICMA-class plates on a lever-2 stage per axis, the refill under load): free stroke and blocked force at the lever, loaded travel under the static load, loaded resonance, and drive power with a charge-recovery driver, against study B's piezo model (all) | all within ±20 % of the model | hypothesis | the project's pass line for a model check (as AC-Q05-02); CALC: the slim branch reaches ±0.56 mm with 29.7 mW (with the counter-face); SIM: the slim stage (B3, ±0.32 mm under load) left 0.86 of the tremor with the tracker and 0.50 with perfect knowledge at 32 mW (docs/balanced_nib.md s3, s5.3) | the slim core's feasibility (a trade study, DEC-050) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-B31).
<!-- AC-TABLE:EXP-B31:END -->

- **Decision rule.** Within ±20 % of the model: the slim branch's trade study uses the model. Otherwise refit the piezo model before any slim design is compared.

---

## 52. A causal tremor tracker on real data: EXP-E10…E13, E17, and where study E's other experiments run (study E; DEC-060, DEC-061)

### Purpose and what it gates

Study E (`docs/real_tracker.md`) looked for a causal tremor tracker, small enough for the pen's microcontroller, that makes real tremor-affected writing more readable and leaves clean real writing alone. **Nothing was built or measured on a pen or a person.** The numbers are SIM in model HW1 with study R's real inputs (tuned on 5 tuning writers, frozen at 2026-09-30T00:22:50Z, then tested once on 9 held-out writers) or CALC; sim2 was checked on one synthetic writer.
- **DEC-060 (2026-09-30).** No causal tracker drives the nib at severe tremor yet, and DEC-055's line stays unchanged (AC-R02-01). No design tested on real inputs passes it: the study's frozen design (ai2's TCN with a soft size gate), sim2j's G4, study R's gated tracker and ai2's TCN. G4 (DEC-047) stays the default because it leaves clean writing alone (0–1 µm), although on real tremor it acts no more than a nib held still. Help for severe tremor comes from the page side for now: the app's clean copy, spelling help and word completion (autowrite of accepted text is a bench research mode, DEC-050). Because no causal estimator uses reach beyond ±1 mm on real tremor, the two-axis nib (G4) is ±1.0 mm.
- **DEC-061 (2026-09-30).** Tremor estimators are learned from real recordings and gated per user. ai2's TCN, trained on synthetic writers, is retired as a candidate for driving the nib. The candidate is a small causal network trained on real writing and tremor, with its gate calibrated on the user's own clean writing (REQ-CTRL-016), tested once on new held-out data (EXP-E10) before it may leave shadow mode.
- **What the study found (SIM).** At the severe class (1.72 mm at the tip) the frozen design left 0.69 × the ordinary pen's tip tremor, but readable words out of 10 stayed at 0.5 (perfect knowledge: 7.0). It moved one test writer's clean writing 0.49 mm (68 µm on average): that writer's letters were twice as large and 1.5 × as fast as any tuning writer's. Real writing shares the 4–8 Hz band with tremor, and real tremor wanders, so line gates seldom open. The 3.5 ms servo lag is not the cause; most of "Rev H makes it worse" is the heavier pen (1.08 × with the nib held).
- **Information only.** The TCN trained on real data was frozen with the design and run once on the test split, but it was not the pre-registered choice, so its test-split result cannot be claimed (DEC-061). No criterion uses it; EXP-E10 tests it on new data.
- **What it gates.** DEC-060 is revisited if EXP-E10 passes DEC-055's line on new held-out data: that estimator may then leave shadow mode, and the ±1.5 mm nib is reconsidered. DEC-061 is revisited if EXP-E10 fails, or if EXP-E11 shows that per-user gates cannot keep every writer under 50 µm. Requirements: REQ-CTRL-015…017, with DEC-055's line (AC-R02-01), REQ-ML-001, REQ-ML-003 and REQ-RVJ-C02.
- **One id per experiment.** Study E proposed EXP-E10…E17 (`docs/real_tracker.md` §18). Three are parts of existing experiments and run there: E14 in EXP-L04 (the networks' timing on the MCU), E15 in EXP-T10 (the command path's lag) and E16 in EXP-W01 (pen mass, with people; `human_study_plan.md` §15). Five keep study E's ids and are specified below: EXP-E10, E11, E12, E13 and E17. Study R's EXP-R05 (retrain the TCN on real inputs) was done by study E in simulation; its test on new data is EXP-E10.
- **One run, several scorings.** EXP-E10's run is scored by its own lines (AC-E10-01, E10-02), by EXP-R02's (DEC-055's line AC-R02-01, and AC-R02-07) and by EXP-R05's (AC-R05-01).
- **Data rules.** Splits as REQ-DATA-001. Only simulated or recorded sensor streams reach an estimator (REQ-DATA-005, AC-R05-02). The realdata test split is spent for DEC-055's question (study E §19).
- **Study F (DEC-067…069, 2026-09-30).** Study F ran EXP-E13 and EXP-E11 in simulation (the results are in AC-E13-01, AC-E11-01 and AC-E11-02; E11 information only) and proposed EXP-E20…E23 (§54). DEC-067 sets the target for any estimator: at most 0.55 mm of tremor left at the tip at the severe class (REQ-CTRL-018), scored on EXP-E10's run (AC-E10-03). DEC-068 makes the per-user gate raise-only (REQ-CTRL-019).

### Where study E's experiments run

| Study E | Runs as | Its criteria | Note |
|---|---|---|---|
| EXP-E10 | its own (below), on EXP-R06's writers or the EXP-R01 recordings | AC-E10-01…03; on the same run AC-R02-01 (DEC-055), AC-R02-07 and AC-R05-01 | the test of EXP-R05's retrained model on new data |
| EXP-E11 | its own (below), in simulation, then on the EXP-R01 shadow-mode logs | AC-E11-01…03 | REQ-CTRL-016, REQ-CTRL-019; study F ran it in simulation (information only) |
| EXP-E12 | its own (below), offline | AC-E12-01 | needs EXP-R06's sets |
| EXP-E13 | its own (below), offline | AC-E13-01 | study F ran it in simulation; people read the inks in EXP-E20 |
| EXP-E14 | EXP-L04 (step 3, the MCU timing) | AC-L04-02 (both networks), AC-L04-04 | the same test as EXP-L04's timing |
| EXP-E15 | EXP-T10 (R13) | AC-T10-07 | the command-to-tip response that EXP-T10 already measures |
| EXP-E16 | EXP-W01 (`human_study_plan.md` §15) | AC-W01-02 | the same crossover of pen masses, with an 84 g dummy and PD participants added |
| EXP-E17 | its own (below), offline in sim2 | AC-E17-01, E17-02 | sim2j's replay method |

### EXP-E10: Does the real-data TCN pass DEC-055 on new held-out data?

- **Purpose and gates.** Test the TCN trained on real data once, on data that study E never used, against DEC-055's line. Gates DEC-060 and DEC-061 (whether a learned estimator may leave shadow mode, and whether the ±1.5 mm nib is reconsidered), REQ-CTRL-015 and REQ-CTRL-017, and reports DEC-067's line (REQ-CTRL-018).
- **Relation to EXP-R05 and EXP-R02.** Study E did EXP-R05's retraining in simulation (the real-data TCN); this is its writer-disjoint test on new data. EXP-R02 scores the same run as a results card (AC-R02-01, AC-R02-07), and EXP-R05's AC-R05-01 is judged on it too.
- **Predictions (SIM; tuning split, cross-fitted, full HW1 plant; `docs/real_tracker.md` §7).** The real-data TCN with its soft size gate: severe tip tremor 0.76 × (PD) and 0.58 × (ET) the ordinary pen's; 0.987 × (moderate) and 1.000 × (mild) the nose-held pen's; clean writing 4.3 µm on average and 19.7 µm on the worst note. It has 16,960 weights and costs 7.5 % of a 128 MHz Cortex-M33 (CALC). There is no prediction for words read, and none is taken from the test split (above).
- **Set-up.** The model exactly as frozen (`results/realtrack/frozen.json`, "net", with its checksums), run causally in HW1 with the DeltaPen-class page sensor (the ideal sensor only as a labelled bound). New held-out data: further UNIPEN or IAM-OnDB writers from EXP-R06 with held-out tremor, or the EXP-R01 recordings. The literal reader (REQ-DATA-008) and the results card (DEC-054).
- **Procedure.**
  1. Before the new data are opened: record the model's checksum, the tuning writers' statistics and the scoring code (§0.2).
  2. Check the new clean writing (REQ-DATA-003).
  3. Run the model once at every class, with the ordinary pen, the nose-held pen and perfect knowledge beside it. Change nothing after the run.
  4. Score the results card: words read at the severe class with the 95 % writer-bootstrap interval; tip tremor per class and per writer, against the ordinary pen and the nose-held pen; clean writing changed per writer; the writers' letter sizes and speeds against the tuning set's.
- **Measurands.** Words gained at the severe class; tip tremor per class and writer, and at the severe class against DEC-067's 0.55 mm (AC-E10-03); clean writing changed (the mean and the largest writer); the writers' statistics.

<!-- AC-TABLE:EXP-E10:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E10-01 | REQ-CTRL-015 | The real-data TCN with its soft size gate (study E; frozen in results/realtrack/frozen.json as 'net'), tested once on new held-out data (further UNIPEN or IAM-OnDB writers from EXP-R06 with held-out tremor, or the EXP-R01 recordings): the largest single held-out writer's clean-writing change, and the letter sizes and speeds of its tuning writers against the held-out writers' 5-95 % range (writer statistics) (both) | both met (≤ 50 µm; the tuning writers span at least the 5-95 % range) | requirement | REQ-CTRL-015 (DEC-061); the frozen design met 18 µm mean and 40 µm worst on 5 tuning writers but moved one test writer's clean writing 493 µm, a writer with letters about 2 x larger and 1.5 x faster than any tuning writer's (SIM, docs/real_tracker.md s7, s15); the real-data TCN, cross-fitted on the tuning split in the full plant: 4.3 µm mean, 19.7 µm on the worst note (SIM); its result on study E's test split was seen after the freeze and is information only (DEC-061), so no prediction is taken from it; its 5 tuning writers wrote 3.4-7.4 mm letters, slowly -> the coverage part is at risk until more writers are added (EXP-E12) | DEC-061 (the learned estimator leaves shadow mode only after EXP-E10); DEC-060 |
| AC-E10-02 | REQ-DATA-001 | Pre-registration of EXP-E10 (review of the records): the model run is the one frozen before the new data were opened (the checksums in results/realtrack/frozen.json); the held-out writers and tremor were used nowhere in study E or in its choices; the test ran once, and nothing was changed after it (all) | conforms | derived | DEC-061 (tested once on new held-out data before it may leave shadow mode) and study E's data discipline (every choice on the tuning split, frozen, then tested once; docs/real_tracker.md s16), with REQ-DATA-001's held-out splits, so derived; study E's test split is spent for this question (s19) | validity of EXP-E10's verdict (DEC-060, DEC-061) |
| AC-E10-03 | REQ-CTRL-018 | The real-data TCN as frozen, on EXP-E10's new held-out data: tremor left at the tip at the severe class (study R's measure), mean over writers, PD and ET pooled and each reported, reported beside DEC-055's lines (AC-R02-01) | ≤ 0.55 mm | requirement | REQ-CTRL-018 (DEC-067): study F's +2-words level, 0.55 mm on the test split (0.47-0.64; PD 0.46, ET 0.62) and 0.65 mm on the tuning split (0.56-0.70) (SIM, HW1 with real inputs, the literal AI reader; docs/readable_target.md s3), so derived; study E's best causal tracker left 1.12 mm on the test split, and the real-data TCN 0.58-0.76 x the ordinary pen's severe tip tremor on the tuning split (SIM, docs/real_tracker.md s7) -> predicted to FAIL. HW1 has the Rev J nose's reach: with Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, study F, docs/readable_target.md s8: the Rev J nose with its travel cut, tuning split), so Rev K's nib makes no severe-tremor legibility claim (DEC-060) | DEC-067; DEC-060 (a ±1.5-3 mm balanced nib once an estimator nears 0.55 mm and EXP-E23 confirms the reach check) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-E10).
<!-- AC-TABLE:EXP-E10:END -->

- **Decision rule.** AC-R02-01, AC-R02-07 and AC-E10-01 pass: the estimator may leave shadow mode (DEC-061; EXP-L04 then tests REQ-ML-001 on people's recordings), and the ±1.5 mm nib is reconsidered (DEC-060). Otherwise it stays in shadow mode (DEC-042), DEC-061 is revisited, and more writers come first (EXP-E12). AC-E10-03 does not change this verdict (DEC-055 stays the pass line), but an estimator near 0.55 mm, with EXP-E23 confirming study F's reach check, starts the design of a ±1.5–3 mm balanced nib (DEC-060).

### EXP-E11: Does a gate calibrated on the user's own clean writing keep every writer under 50 µm?

- **Purpose and gates.** Set the authority gate for each user from that user's own clean writing, and check that it keeps every writer's clean writing within 50 µm. Gates REQ-CTRL-016 and DEC-061's revisit (per-user gates cannot keep every writer under 50 µm).
- **Predictions (SIM).** Study E had none for per-user gates; study F's results are below. The frozen gate, set on 5 tuning writers, was on average half open (mean authority 0.50) on one test writer's clean note and moved it 0.49 mm; ai2's TCN without a gate moved the 9 test writers' clean writing by 40–583 µm (`docs/real_tracker.md` §7, §15).
- **Set-up.** Simulation first (HW1, real inputs, the DeltaPen-class page sensor): for each test writer, a threshold from one clean note, scored on another note of the same writer. Then the EXP-R01 shadow-mode logs, where the estimate is computed and logged but never drives the nib.
- **Procedure.** For each writer: set the gate's opening threshold above the estimator's output on the calibration note; run the scored note and the tremor cases; log the gate's state. Repeat on the EXP-R01 shadow-mode data when it exists.
- **Measurands.** Clean writing moved per writer; each writer's threshold; tremor left with the gate at the severe and moderate classes.
- **Study F (DEC-068; SIM, information only, because study E had seen the test writers; `docs/readable_target.md` §4–§5).** Rules chosen on the tuning writers, each test writer calibrated on another of their own notes. With raise-only rules the largest clean-writing change over the 9 test writers was 19.1 µm for ai2's TCN (493.0 µm with its frozen gate) and 18.9 µm for the real-data TCN. The worst writer's mild-tremor ratio to the held nib fell from 2.89 to 1.004. No words were gained at the severe class (−0.22 and +0.11). The listening AKF's rule, which could also lower the threshold, lowered it for 4 of the 9 writers and moved one writer 60.5 µm. So DEC-068 makes calibration raise-only (REQ-CTRL-019, AC-E11-03). The real answer needs EXP-R01's shadow-mode logs. Users who cannot write without tremor are EXP-E22 (§54).

<!-- AC-TABLE:EXP-E11:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E11-01 | REQ-CTRL-016 | Gate calibration (firmware review and logs): before the nib may act, the authority gate's opening threshold is set from the user's own clean writing (a short tremor-free or low-tremor sample, or the first minutes of use in shadow mode), above the estimator's output on that writing; in simulation per test writer from a clean note other than the one scored, then on the EXP-R01 shadow-mode logs | conforms | requirement | REQ-CTRL-016 (DEC-061); size thresholds fixed on a few writers did not transfer: ai2's TCN without a gate moved the 9 test writers' clean writing by 40-583 µm, and the frozen gate, set on 5 tuning writers, was on average half open on one test writer's clean note (SIM, docs/real_tracker.md s7, s15). Study F (SIM, information only: study E had seen the test writers; docs/readable_target.md s5): conforms in simulation; ai2's TCN's rule sits at the 99th percentile of the estimate's size on the calibration note, so 1 % of that writing lies above the threshold, and the real-data TCN's at 2 x its maximum | DEC-061 (per-user gates) |
| AC-E11-02 | REQ-CTRL-016 | Clean real writing moved by the estimator with per-user gates, per writer, on a clean note other than the calibration note (HW1 with the measured-error page sensor; then the EXP-R01 shadow-mode data): the largest single writer | ≤ 50 µm | derived | DEC-061's revisit trigger (per-user gates cannot keep every writer under 50 µm) and DEC-055's per-writer cap, so derived; the frozen design's gate, set on 5 tuning writers, moved one test writer's clean writing 493 µm (SIM, docs/real_tracker.md s15); study F (SIM, information only: study E had seen the test writers; docs/readable_target.md s5): 19.1 µm (ai2's TCN) and 18.9 µm (the real-data TCN) with raise-only rules, met; 60.5 µm with a rule that could also lower the threshold (the listening AKF), not met; hence DEC-068's raise-only rule (REQ-CTRL-019) | DEC-061 (revisit if per-user gates cannot keep every writer under 50 µm); REQ-CTRL-016; DEC-068 |
| AC-E11-03 | REQ-CTRL-019 | Gate calibration rule (firmware review, and the EXP-R01 shadow-mode logs): the calibrated opening threshold is the larger of the design's own threshold and the calibrated value (a high quantile, or a multiple of the maximum, of the estimate's size on the user's own writing, the rule fixed per design on tuning writers); calibration never lowers it | conforms | requirement | REQ-CTRL-019 (DEC-068); study F (SIM, information only: study E had seen the test writers): the raise-only rules kept every test writer's clean writing within 19.1 µm, and a rule that could also lower the threshold moved one writer 60.5 µm (docs/readable_target.md s5) | DEC-068 (raise-only calibration) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-E11).
<!-- AC-TABLE:EXP-E11:END -->

- **Decision rule.** Every writer within 50 µm: per-user calibration becomes the rule for any learned estimator (REQ-CTRL-016, DEC-061). Any writer above it: DEC-061 is revisited.

### EXP-E12: Do more real training data, or a GRU, close the gap to perfect knowledge?

- **Purpose and gates.** Retrain the real-data TCN on more writers, with larger and faster writing, and train a GRU of the same size. See whether either leaves less severe tremor without moving clean writing. Gates the learned estimator's design (DEC-061) and the tuning set that REQ-CTRL-015 asks for.
- **Predictions (SIM; tuning split, cross-fitted; `docs/real_tracker.md` §7, §10).** The 5-writer TCN: 0.71 × the ordinary pen's severe tip tremor raw and 0.67 × with its soft size gate; clean writing 32 µm raw and 4 µm gated (20 µm on the worst note). Perfect knowledge leaves 0.02 ×. A GRU was not trained.
- **Set-up.** The EXP-R06 sets under their licences (REQ-DATA-006), with the realdata tuning writers. Study E's training recipe (`realtrack/netmodel.py`): writer-disjoint cross-fitting, and the clean-writing penalty fixed before training.
- **Procedure.** Retrain the TCN, and train a GRU of the same size, on the larger writer set; score each held-out fold; report the worst writer.
- **Measurands.** Severe tip tremor left per fold and writer; clean writing changed per writer; the writers' letter sizes and speeds.

<!-- AC-TABLE:EXP-E12:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E12-01 | — | The real-data TCN retrained on more writers (the EXP-R06 sets, with larger and faster writing), and a GRU of the same size, writer-disjoint and cross-fitted: severe tip tremor left (x the ordinary pen) against the TCN trained on the 5 tuning writers, and the largest single writer's clean-writing change (both) | both met (lower than the 5-writer model's; ≤ 50 µm for every writer) | hypothesis | study E asks whether more real data or a GRU closes the gap to perfect knowledge and gives no pass line (docs/real_tracker.md s10, s18), so a hypothesis; the 5-writer model, cross-fitted on the tuning split: 0.71 x raw and 0.67 x with its soft size gate, clean writing 32 µm raw and 4 µm gated (20 µm on the worst note); perfect knowledge leaves 0.02 x (SIM); the per-writer cap is DEC-055's | the learned estimator's design (DEC-061) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-E12).
<!-- AC-TABLE:EXP-E12:END -->

- **Decision rule.** Pass: the better network is frozen for a new held-out test, as EXP-E10. Fail: more data, or other inputs, before any new test.

### EXP-E13: How much tremor may be left for words to be readable?

- **Purpose and gates.** Find the residual tip tremor at which words become readable: the target for any estimator. Gates DEC-060's target for estimators.
- **Predictions (SIM; `docs/real_tracker.md` §15, §18).** Words are read at 0.24 mm of tip tremor (the moderate class: 5–6 of 10) but not at about 1 mm, which the best causal estimates leave. Study E expects the target near 0.2–0.3 mm.
- **Set-up.** Study R's tuning notes with PD and ET tremor, in HW1 with perfect knowledge scaled so that a chosen share of the tremor is left at the tip; the literal reader.
- **Procedure.** Sweep the residual between the mild and the severe class (about 0.1–1.7 mm at the tip); read every note at each step; fit words read against the residual.
- **Measurands.** Words read out of 10 against the residual tip tremor; the residual at which words reach the ordinary pen's plus 2 (DEC-055's words line), and the residual at which they come within 1 word of the clean notes.
- **Study F (DEC-067; SIM, HW1 with real inputs, the literal AI reader; `docs/readable_target.md` §2–§3).** Words read fall along one curve as tremor is left at the tip, for three kinds of residual (a scaled copy of the tremor, a late copy and random error). DEC-055's +2 words needs no more than 0.65 mm on the tuning split (0.56–0.70); the scaled residual alone 0.73 mm (0.62–0.78). The test split confirmed it once (a gain of 1.98 words at 0.65 mm), and its own curve gives 0.55 mm (0.47–0.64; PD 0.46, ET 0.62). Near-normal reading (80 % of the tremor-free words) needs about 0.25 mm. AC-E13-01 is met in simulation, and DEC-067 sets the target at 0.55 mm (REQ-CTRL-018). The levels were found with the Rev J nose's ±6 mm; with ±1.0 mm even perfect knowledge falls short (§54). People read the same inks in EXP-E20 (`human_study_plan.md` §25).

<!-- AC-TABLE:EXP-E13:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E13-01 | — | Residual tip tremor (peak along the main axis, mm; perfect knowledge scaled) at which the literal reader's words out of 10 at the severe class reach the ordinary pen's plus 2 (DEC-055's words line), on study R's tuning notes, PD and ET | within 0.24-1.0 mm | hypothesis | study E: words are read at 0.24 mm of tip tremor (the moderate class, 5-6 of 10) but not at about 1 mm, which the best causal estimates leave; it expects the target near 0.2-0.3 mm and gives no pass line (docs/real_tracker.md s15, s18), so a hypothesis; the AI reader stands in for people (EXP-R03). Study F (SIM, HW1 with real inputs, the literal AI reader; docs/readable_target.md s3): 0.73 mm for the scaled residual on the tuning split (0.62-0.78), 0.65 mm pooled over the residual kinds (0.56-0.70) -> within; the test split's own curve gave 0.55 mm (0.47-0.64), which DEC-067 takes as the target (REQ-CTRL-018); found with the Rev J nose's ±6 mm (with ±1.0 mm even perfect knowledge falls short, s8); people's reading is EXP-E20 | the target for any estimator (DEC-060); DEC-067 (0.55 mm) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-E13).
<!-- AC-TABLE:EXP-E13:END -->

- **Decision rule.** The measured residual becomes the target that an estimator must reach at the severe class (DEC-060). The AI reader stands in for people until EXP-R03 checks it.

### EXP-E17: Do the frozen and the real-data designs hold in sim2 on more writers?

- **Purpose and gates.** Run study E's frozen design and the real-data TCN over sim2's test grid, so that sim2 backs any claim with more writers and seeds. Gates the sim2 side of any claim (sim2 ranks controllers until it is validated, REQ-SIM-005) and REQ-RVJ-C02.
- **Predictions (SIM in sim2; synthetic writer 0, seed 200; `docs/real_tracker.md` §14).** The frozen design behaved like G4: 0.98–1.01 of the device-off ink error at 0.3 mm, 0.65–0.99 at 1 mm and 0.54–0.84 at 2 mm, against 0.06–0.44 with perfect knowledge. It moved clean synthetic writing 6.4 µm (G4 0.0 µm; ai2's TCN without a gate 154.6 µm). The real-data TCN has not been run in sim2.
- **Set-up.** sim2j's ET grid: test writers 0–5, 4 seeds, 4, 8 and 12 Hz at 0.3, 1 and 2 mm. Each design runs causally on the sensor samples the pen recorded in the device-off run, and its output is replayed as the nib command in a second run with the same seed (sim2j's learned-replay method). G4 and perfect knowledge come from sim2j's rows. sim2's IMU delay (0.25 ms) is shorter than HW1's chain (1.04 ms); study E found this within the flat part of its delay sweep.
- **Procedure.** Run both designs over the grid and on the same writers' tremor-free writing; score with sim2j's measures.
- **Measurands.** Ink error against the device-off pen per cell; tremor-free writing moved per writer and seed; words read by the app's reader.

<!-- AC-TABLE:EXP-E17:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E17-01 | REQ-RVJ-C02 | sim2's test grid (sim2j's ET grid: test writers 0-5, 4 seeds): the frozen design and the real-data TCN run causally on the pen's recorded sensor samples and replayed as nib commands (sim2j's learned-replay method, study E s14): tremor-free writing moved against the device-off pen with the same noise and seed (RMS, every writer and seed) | ≤ 25 µm | requirement | REQ-RVJ-C02; SIM (sim2, writer 0, seed 200): the frozen design moved clean synthetic writing 6.4 µm, G4 0.0 µm and ai2's TCN without a gate 154.6 µm (docs/real_tracker.md s14); the real-data TCN has not been run in sim2 | the sim2 side of any claim (DEC-060, DEC-061) |
| AC-E17-02 | — | The same grid: ink error against the device-off pen at 8-12 Hz x 1-2 mm, each design relative to G4 in the same cells (geometric mean over writers, seeds and cells) | ≤ 1.05 | hypothesis | study E gives no pass line, so a hypothesis; 0.05 mirrors DEC-047's revisit margin; SIM (sim2, writer 0, seed 200): the frozen design 0.76 / 0.65 at 8 / 12 Hz x 1 mm and 0.54 / 0.71 at 2 mm, against G4's 0.86 / 0.58 and 0.54 / 0.62 (docs/real_tracker.md s14): a geometric mean of 1.03 x G4 (CALC) | the sim2 side of any claim; DEC-047 (G4 stays the default, DEC-060) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-E17).
<!-- AC-TABLE:EXP-E17:END -->

- **Decision rule.** Pass: sim2 supports the design's claim, within sim2's context of use (REQ-SIM-005). Clean writing above 25 µm: the design does not run on the bench (as AC-L02-05). Worse than G4: G4 stays the default (DEC-047, DEC-060).

---

## 53. The Rev K layout: EXP-K20, K21, K23, K25, and where study K's other experiments run (study K; DEC-062…066)

### Purpose and what it gates

Study K (`docs/revK_design.md`) put study B's balanced nib B1 into a pen: Rev K. **Nothing was built or measured on a pen or a person.** The numbers are CALC in `revk/` (`results/revK/`), with the CAD in `mechanics/cad/revK_pen.py`. The only new simulation is the servo-bandwidth check (SIM, study B's sim2 set-up, two tuning writers, one seed).
- **DEC-062 (2026-09-30).** Rev K is the Rev J body, 24 mm where held from 20 mm behind the tip. It carries B1 as study K rebuilt it, a 6.0 mm skid ring with the page sensor at its bottom and a clear ink window over the top 240°, the counter-face head behind the refill, the LIR14500 cell, a cue LRA and charging pads. It is 145.1 mm long and weighs 66.4 g, with its balance point 74.9 mm from the tip. Unpowered, the nib rests on its soft stop (REQ-BNIB-011 reworded). REQ-BNIB-017 stays the page sensor's selection requirement. Of 59 fit checks, 29 pass, 21 are marginal and 9 fail (below).
- **DEC-063.** Four 0.10 mm C17200 beryllium-copper wires centre the carrier and carry the coil currents (0.27 Ω each), on an axially soft anchor. A sprung ball thrust guide on the carrier's flange carries the counter-face couple (10.9 mN·m at 35°) and the axial load, so no wire is in compression. The wires are soldered or crimped, never welded, ground or laser-cut without fume extraction (AMF-18; §0.10). Since DEC-097 nothing is welded, and the wire is bought age-hardened and cut only with shears or flush cutters.
- **DEC-064.** The counter-face head has a roll cage (±30°), a tilt hinge 9 mm toward the paper with the face 6 mm behind it and a balance spring, a face that floats ±0.56 mm, a captive shoe and three SQL-RV-1.8 piezo motors. The pen lift is the follower pulling the head back: 0.5 mm at the ball in 0.16–0.18 s, with no holding energy. It serves the spelling cue (EXP-S12, S18); a gated mode (EXP-W16) needs a faster lift, which is not designed. REQ-BNIB-002 becomes 1.0 mm of touchdown travel at 35° without a float brake, or 0.25 mm with one. The brake is fitted only if EXP-K23 or EXP-J17 (c) shows that the touchdown transient marks the ink.
- **DEC-065.** The base Rev K has no heel drive. The heel is a bench front-end module; it goes into a pen only if EXP-T04 finds a page sensor that tolerates ±20° of roll beside its pod (AC-T04-08).
- **DEC-066.** The position servo runs at 40 Hz and the inner loop at no more than 46 Hz, inside DEC-050's 2.5 × rule: the ball-stuck mode is 163 Hz nominally and 115 Hz in the worst case (CALC).
- **What it gates.**
  - DEC-062 is revisited if EXP-T07 (study K's EXP-K22) gives K_m below 0.7 × 0.334 N/√W, if EXP-K20 or K21 fails, if EXP-J15 on the Rev K front shows the ink hidden for most writers, or if EXP-K24 finds writers touching the paper with a finger.
  - DEC-063 is revisited if EXP-K21 or K20 fails.
  - DEC-064 is revisited if EXP-J17 (c) or EXP-K23 finds a residual above 25 % of F_s·cot θ at the 95th percentile, a lift slower than 0.25 s, a positioner that back-drives under 0.2 N or a refill change that fails for a common brand.
  - DEC-066 is revisited if EXP-T10 measures a stuck mode below 100 Hz (AC-T10-08), or if EXP-K25 loses more than 0.05 of the tremor ratio.
  - Requirements: REQ-RVK-001…005, REQ-BNIB-002 and 011 as amended, REQ-BNIB-006, 007 and 017, REQ-RVJ-N04, N06 and I06. The gates for building Rev K's nib and pen are in `prototype_stages.md` §0.
- **One id per experiment.** Study K proposed EXP-K20…K25 (`docs/revK_design.md` §11.3). EXP-K22 is EXP-T07's test on another coupon, so it runs there (AC-T07-05). EXP-K24 is with people (`human_study_plan.md` §24). EXP-K20, K21, K23 and K25 keep study K's ids, because DEC-062…066 name them; they are specified below. Study K's AC-K23-04 (the touchdown travel against REQ-BNIB-002) is AC-J17-05, so the AC-K23 numbers skip 04.
- **Existing experiments that test Rev K.** EXP-M03 weighs it (AC-M03-08) and EXP-P01 runs its battery per mode (AC-P01-06). EXP-B25's jig measures its offsets and drops (AC-B25-04). EXP-T04 tests its page sensor (AC-T04-07, T04-08), EXP-T10 its modes and bandwidth (AC-T10-02, T10-08) and EXP-T13 its unpowered state (AC-T13-05). With people (`human_study_plan.md` §15, §20): EXP-J15 on the Rev K front (AC-J15-04), and a 66 g dummy of the Rev K pen in EXP-J09 and EXP-W01 (AC-J09-02, AC-W01-03).

### The fit checks that fail, and what closes each

| Check | Value (CALC) | Rule | What closes it |
|---|---|---|---|
| F5 page sensor's lift range | ±0.2 mm tracked | ≥ 2 mm (REQ-BNIB-017) | EXP-T04 chooses a die and optics (AC-T04-07); REQ-BNIB-017 stays the selection requirement (DEC-062) |
| H6 touchdown refill travel | 0.98 mm at 35° | ≤ 0.25 mm (REQ-BNIB-002 before DEC-064) | DEC-064: 1.0 mm without a float brake (AC-J17-05); the brake only if the touchdown marks the ink (AC-K23-05) |
| N22 unpowered rest | on its stop, 1.26 mm off centre | centred within 0.1 mm (REQ-BNIB-011 before DEC-062) | REQ-BNIB-011 reworded (DEC-062); EXP-T13 checks that the pen writes (AC-T13-05) |
| L3 grip height at 35° | 7.4 mm | ≥ an ordinary pen's 10.7 mm | EXP-K24 with writers (AC-K24-01) |
| V1 heel variant: page sensor roll | 0.5° | ≥ 20° (REQ-RVJ-N06) | the heel stays a bench module (DEC-065) until EXP-T04 passes AC-T04-08 |
| V4 heel variant: shafts against the back plate and keeper | 0.3 mm overlap | ≥ 0.2 mm clear | 1.2 mm notches in both plates; EXP-T07 measures K_m with them (AC-T07-05) |
| N3, N14, N17: study B's B1 as drawn | the coil at the stop 10.81 mm from the axis (limit 10.7 mm); the couple as 0.70 N on wires that buckle at 0.009 N; Ti leads cap the current at 0.34 A | — | kept for the record; Rev K's fixes (N1 the buildable coil, N7/N15 the ball guide, N16 the C17200 leads) are tested in EXP-T07 (AC-T07-05), EXP-K20 and EXP-K21 |

### Where study K's experiments run

| Study K | Gate | Runs as | Its criteria | Note |
|---|---|---|---|---|
| EXP-K20 | G2 | its own (below): R12's stage and a drop rig | AC-K20-01…03 (REQ-RVK-003) | the ball thrust guide |
| EXP-K21 | G2 | its own (below): study H's fatigue shuttle at no more than 0.2 × each coupon's first mode (DEC-098), with current | AC-K21-01…04 (REQ-RVK-004, REQ-BNIB-007) | the beryllium rule (§0.10; DEC-097) |
| EXP-K22 | G2 | EXP-T07 (R12): Rev K's buildable coil, and the heel variant's notched plates as a second coupon | AC-T07-05 (DEC-062's line); AC-T07-01…04 on the same map | the same test on another coupon |
| EXP-K23 | G4, before the Rev K pen | its own (below): EXP-J17 (c)'s tilting stage | AC-K23-01…03, K23-05; AC-J17-04 and J17-05 for the head | study K's AC-K23-04 is AC-J17-05 |
| EXP-K24 | before the Rev K pen | `human_study_plan.md` §24, with people | AC-K24-01 | unpowered grip mock-ups |
| EXP-K25 | — | its own (below), offline in sim2 | AC-K25-01, K25-02 (REQ-RVJ-C02) | needs sim2j's adapter for Rev K |

### EXP-K20: Does the ball thrust guide carry the couple with little friction, and survive drops?

- **Purpose and gates.** Check that the sprung ball thrust guide carries the counter-face couple without tilting the carrier or compressing a wire, that it rolls with little friction, and that it survives drops. Gates REQ-RVK-003, DEC-063 (revisited if the friction exceeds 5 mN or the races brinell) and building Rev K's nib (G2).
- **Predictions (CALC; `docs/revK_design.md` §3.3).**
  - The couple is 10.9 mN·m at 35° (8.5 at 50°, 3.4 at 75°). The loaded balls carry 2.6 N, and the rolling friction is 2.6 mN (rolling resistance 0.001, ASSUMPTION).
  - Each race sits on a wave spring preloaded to 4 N, about 1.5 × the couple's ball load, so the carrier's tilt and axial position stay fixed and no wire is in compression. Without the guide the couple would put 0.70 N of compression on a wire that buckles at 0.009 N (fit check N14).
  - Hertz stress is 2.66 GPa at the couple's load and 3.05 GPa at the springs' release load, the most a drop can put on a ball (≤ 4 GPa static for 440C, ASSUMPTION). Rigid races would see 7.6 GPa in a 2,000 g drop and brinell; hard stops sit 20 µm behind the races.
  - The balls roll half the flange's stroke, 0.63 mm. The races clear the wires' envelope by 0.36 mm, and the flange's rim clears the bore by 0.31 mm at the stop (both marginal).
- **Set-up.** A coupon: the carrier's flange (Ø18.9 mm) between two lapped 440C races on 2 × 6 Si3N4 balls (Ø0.8 mm) on a 16.6 mm circle, each race on its wave spring, with the four C17200 wires and the anchor as in Rev K. A dead weight or a force actuator applies the couple and the ink force. R12's stage sweeps the flange, with a force sensor between the stage and the flange; an autocollimator on the flange; strain gauges on the wires. A drop rig for a dummy pen that carries the guide; a profilometer.
- **Procedure.**
  1. With the couple of the 35° case (≥ 11 mN·m) and the ink force applied: the carrier's tilt and the wires' axial forces, at rest and across the stroke.
  2. Sweeps of ±1.26 mm at 8 Hz in both axes: the rolling friction (the lateral force less the wires' spring force), at the couples of 35, 50 and 75°.
  3. Ten 1 m drops of the dummy pen in several orientations. Then the races under the profilometer, and step 2 again.
- **Measurands.** The carrier's tilt; the wires' axial forces against their buckling load; the rolling friction before and after the drops; marks on the races.

<!-- AC-TABLE:EXP-K20:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K20-01 | — | Ball thrust guide coupon (study K; DEC-063): the carrier flange between two sprung 440C races on 2 x 6 Si3N4 balls (0.8 mm), loaded with the couple of the 35° case (10.9 mN m) and the ink force, swept ±1.26 mm at 8 Hz in both axes: rolling friction (the lateral force to move the flange, less the wires' spring force) | ≤ 5 mN | derived | DEC-063's revisit trigger (rolling friction above 5 mN), so derived; CALC 2.6 mN with 2.6 N on the loaded balls at 35° (rolling resistance 0.001, ASSUMPTION; docs/revK_design.md s3.3); the independent pass counts both races' 4 N preload: about 8 mN (8.07 mN in its opposed-guide model, rolling coefficient 0.001, ASSUMPTION; docs/mechanics_improvement_audit.md; DEC-072) -> predicted to FAIL at the 4 N preload; EXP-BB05 steps the preload (AC-BB05-02) | DEC-063 (the ball guide); building Rev K's nib (prototype_stages.md s0); DEC-072 through DEC-096 (the measured guide drag enters the duty re-run, with EXP-BB05) |
| AC-K20-02 | REQ-RVK-003 | The same coupon loaded with a couple of ≥ 11 mN m (the 35° case): the carrier's tilt (autocollimator on the flange), and the axial force in each wire (strain-gauged wires) as a share of its buckling load (both) | both met (≤ 0.2 mrad; no wire compressed beyond 0.5 x its buckling load) | requirement | REQ-RVK-003 (DEC-063); CALC: the sprung races (4 N, about 1.5 x the couple's ball load) fix the carrier's tilt and axial position, so no wire is in compression; on the wires alone the couple would put 0.70 N of compression on a wire that buckles at 0.009 N (fit check N14); no tilt value was computed (docs/revK_design.md s3.3) | DEC-063 (the ball guide); building Rev K's nib (prototype_stages.md s0) |
| AC-K20-03 | — | After ten 1 m drops of a dummy pen carrying the guide: marks on the races (profilometer), and the rolling friction of AC-K20-01 against its value before the drops (both) | both met (no race marks; within ±20 %) | derived | DEC-063's revisit trigger (brinelling after drops), so derived; the 20 % is study K's proposed line (docs/revK_design.md s11.3); CALC: Hertz stress 2.66 GPa at the couple's load and 3.05 GPa at the springs' release load, the most a drop can put on a ball, against ≤ 4 GPa static for 440C (ASSUMPTION); rigid races would see 7.6 GPa in a 2000 g drop and brinell, hence the springs, with hard stops 20 µm behind the races (s3.3) | DEC-063 (the sprung races); building Rev K's nib (prototype_stages.md s0) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-K20).
<!-- AC-TABLE:EXP-K20:END -->

- **Decision rule.** Friction above 5 mN, or marks on the races after the drops: DEC-063 is revisited. A tilt above 0.2 mrad, or a wire compressed beyond half its buckling load: REQ-RVK-003 fails.

### EXP-K21: Do C17200 wires survive as the coil leads?

- **Purpose and gates.** Check that 0.10 mm C17200 wires can be both the suspension and the coil leads: their resistance, their fatigue at the stop travel while carrying current, and the assembly preload that sets their fatigue margin. Gates REQ-RVK-004, REQ-BNIB-007 for Rev K's wires, DEC-063 (revisited if they fail) and building Rev K's nib (G2).
- **Beryllium (DEC-097).** Welding, grinding or laser-cutting beryllium copper can release airborne beryllium, which can cause serious lung disease (AMF-18). The wire is bought already age-hardened, so no heat treatment is done at the bench. It is cut with shears or flush cutters only, and never abrasive-cut, ground, sanded, pickled or acid-cleaned. The clamps are soldered under a bench fume absorber, or crimped; nothing is welded. Gloves are worn. Offcuts, broken coupons and wipes go into sealed, labelled bags. There is no food or drink at the bench, and hands are washed after handling (§0.10; AMF-319, AMF-320). *Was (DEC-063):* "The clamps are soldered or crimped. No coupon is welded, ground or laser-cut without fume extraction (DEC-063), and offcuts and broken coupons are handled under the dust controls of §0.10."
- **Predictions (CALC; `docs/revK_design.md` §3.3).**
  - A 0.10 mm wire has 0.27 Ω at 22 % IACS minimum (MFR AMF-251; AMF-18 gives 22–28 %). The coil loop rises from 2.5 to 3.03 Ω (+21 % copper loss), and the current limit at 3.3 V is 1.0 A. The suspension's stiffness at the tip is 1.56 N/m.
  - Fatigue at the stop (fatigue strength MFR AMF-19 × 0.85): Goodman safety factor 2.18 at Kt 1.8 and 1.57 at Kt 2.5. Over the tolerance draws the 5th percentile is 1.40 with ≤ 0.05 N of assembly preload, and 0.92 with up to 0.3 N. The preload dominates: the ball guide fixes the flange axially, so each µm of mismatch loads the wires by 0.15 N. Hence the axially soft anchor.
  - A 0.08 mm wire reaches 1.50 at the 5th percentile but adds 33 % to the coil loop. It would have about 0.42 Ω per wire, above REQ-RVK-004's 0.3 Ω (0.27 Ω scaled by the diameter squared, a check made here).
- **Set-up.** Wire coupons of 0.10 mm (the design) and 0.08 mm C17200, 26.8 mm of free length, in soldered and in crimped clamps, with the anchor on its axially soft diaphragm. Study H's crank-driven fatigue shuttle (§55; several coupons on one crank), driven at no more than 0.2 × the first transverse mode measured on each coupon (DEC-098), with a current source that drives 0.1 A through each wire and 4-wire resistance logging. Strain gauges on sacrificial coupons; a load cell under the anchor. A gauge cannot be bonded on a 0.10 mm wire, so study H proposes 10× scaled coupons for Kt (1.0 mm C17200 in scaled clamps); the lead is to confirm the method. *Was (before DEC-098):* R8's fatigue stations (§0.9), as EXP-B25.
- **Procedure.**
  1. The resistance of each wire, clamp to clamp, at 20 °C (AC-K21-01).
  2. The axial preload after assembly (AC-K21-03), and the clamp's stress concentration from strain-gauged coupons at the stop travel.
  3. The stiffness at the tip in both axes, as EXP-B25 step 2.
  4. Each coupon's first transverse mode (a sine sweep or a tap). Fatigue at the stop travel to 43.2 M cycles with 0.1 A in each wire, driven at no more than 0.2 × that mode (DEC-098; AC-BB04-05): about 3.3–5.2 days per batch. At least 3 coupons per clamp type (§0.7), and spares to failure. An open circuit or a step of more than 2 % in the 4-wire resistance stops a coupon for inspection at 50×. Then the resistance again.

     *Was (before DEC-098):* "Fatigue at the stop travel to 43.2 M cycles with 0.1 A in each wire, at least 3 coupons per clamp type (§0.7), and spares to failure. An open circuit, a step in resistance or a resonance shift stops a coupon for inspection at 50×." The fatigue was planned on R8 as EXP-B25, at about 200 Hz. The 26.8 mm wires' first modes are about 487–763 Hz, so at 200 Hz the clamp stress rises 12–33 % above what the pen sees (CALC, `results/benchbuild/bench_calcs.json`).
- **Measurands.** Resistance before and after the cycling; the preload; Kt; the stiffness; cycles without failure; the Goodman safety factor with the measured Kt and preload.

<!-- AC-TABLE:EXP-K21:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K21-01 | REQ-RVK-004 | C17200 wire coupons (0.10 mm, the design wire; 0.08 mm reported), 26.8 mm free length, soldered or crimped clamps, the anchor on its axially soft diaphragm: resistance of each wire from clamp to clamp (4-wire, 20 °C), before and after the cycling of AC-K21-02 | ≤ 0.3 ohm | requirement | REQ-RVK-004 (DEC-063); CALC 0.27 ohm for a 0.10 mm wire at 22 % IACS minimum (MFR AMF-251; AMF-18 gives 22-28 %), the coil loop 3.03 ohm against 2.5 (docs/revK_design.md s3.3); the 0.08 mm alternative (+33 % on the coil loop, s3.3) has about 0.42 ohm per wire (0.27 ohm scaled by the diameter squared, a check made here), so it would fail this line | DEC-063 (the wire leads) |
| AC-K21-02 | REQ-RVK-004 | The same coupons cycled at the stop travel on the fatigue shuttle (several coupons on one crank; DEC-098) at no more than 0.2 x each coupon's measured first transverse mode, while each wire carries 0.1 A: cycles without failure (an open circuit or a step of more than 2 % in the 4-wire resistance), at least 3 coupons per clamp type | no failure in 43.2 M cycles | requirement | REQ-RVK-004 (DEC-063, which is revisited if EXP-K21 fails); CALC for the 0.10 mm wire: Goodman safety factor 2.18 at Kt 1.8 and 1.57 at Kt 2.5, and 1.40 at the 5th percentile with ≤ 0.05 N of assembly preload (docs/revK_design.md s3.3); not tested with current; DEC-098: the drive is at most 0.2 x the first mode (AC-BB04-05), because at about 200 Hz the clamp stress of a 26.8 mm wire rises 12-33 % over quasi-static (CALC, first modes about 487-763 Hz, results/benchbuild/bench_calcs.json); a batch of 43.2 M cycles takes about 3.3-5.2 days. Was: R8 as EXP-B25, about 200 Hz, a resonance shift also counted as failure | DEC-063 (the wire leads); building Rev K's nib (prototype_stages.md s0); validity: AC-BB04-05 |
| AC-K21-03 | REQ-BNIB-007 | Axial preload on the wires after assembly with the anchor on its axially soft diaphragm (the anchor's load cell, or strain-gauged wires), each assembled suspension | ≤ 0.05 N | derived | the preload on which DEC-063's fatigue margin rests (the 5th percentile 1.40 with ≤ 0.05 N, 0.92 with up to 0.3 N; the ball guide fixes the flange axially, so each um of mismatch loads the wires by 0.15 N), so derived; it protects AC-K21-04 (docs/revK_design.md s3.3) | the anchor diaphragm and the assembly (DEC-063) |
| AC-K21-04 | REQ-BNIB-007 | The 0.10 mm coupons: Goodman safety factor at the stop travel for 43.2 M cycles, with the clamp's measured stress concentration (strain-gauged coupons) and the measured assembly preload | ≥ 1.5 | requirement | REQ-BNIB-007 applied to Rev K's C17200 wires (DEC-063); CALC (fatigue strength MFR AMF-19 x 0.85): 2.18 at Kt 1.8 and 1.57 at Kt 2.5; 1.40 at the 5th percentile of the tolerance draws with ≤ 0.05 N of preload -> marginal; a 0.08 mm wire reaches 1.50 (docs/revK_design.md s3.3); study B's Ti wires are AC-B25-01 | the wire diameter and clamps (DEC-063) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-K21).
<!-- AC-TABLE:EXP-K21:END -->

- **Decision rule.** A failure before 43.2 M cycles, or a safety factor below 1.5: DEC-063 is revisited. Study K names two options: a 0.08 mm wire, which fails the 0.3 Ω line, and a beryllium-free copper alloy of similar fatigue strength, none of which is in the ledger yet. A resistance above 0.3 Ω: REQ-RVK-004 fails. A preload above 0.05 N: the anchor's diaphragm or the assembly is reworked before any fatigue run counts. A drive above 0.2 × the coupon's measured first mode voids the run (AC-BB04-05; DEC-098).

### EXP-K23: Does the counter-face head follow, float, lift and hold?

- **Purpose and gates.** Test Rev K's counter-face head as a mock-up on EXP-J17 (c)'s tilting stage: the follower's range, the float, the pen lift, the positioners' holding, the shoe's capture and the refill change. Gates DEC-064, Rev K's pen lift (REQ-RVJ-N04; AC-K23-01 is its criterion), REQ-BNIB-002's float brake (AC-K23-05) and building the Rev K pen (`prototype_stages.md` §0). The residual side load and the touchdown travel are EXP-J17's AC-J17-04 and J17-05, judged on the head in the same runs.
- **Predictions (CALC and PROPOSED DESIGN; `docs/revK_design.md` §3.4).**
  - The follower moves only 0.46 mm over 35–75°; with the lift and margins it needs 3.1 mm of travel. The face is 10.2 × 7.9 mm.
  - Loads (stall force MFR AMF-15): the tilt motor pushes 0.082 N on its 6 mm crank against the 0.30 N stall (3.6 ×) with the balance spring, and would need 0.35 N without it, which it cannot give. Roll takes 0.042 N (7.1 ×), and the follower 0.20 N during a lift (1.51 ×, marginal). The SQUIGGLE's holding force against back-driving is not in its datasheets.
  - Face parallelism (Monte Carlo, contributors ASSUMPTION): 1.66° off on average (3.28° at the 95th percentile), which leaves 5.7 mN mean and 11.2 mN at the 95th percentile of side load (5.9 % and 13.6 % of F_s·cot θ).
  - The pen lift: the follower pulls the head back until the ball is 0.5 mm off the paper, with the ring on the paper. Up in 0.155–0.18 s and down in 0.08–0.14 s; the ink stops after 43–72 ms; 0.08–0.31 J per lift; no holding energy. The speed–force line of the SQL-RV-1.8 between its MFR points is an ASSUMPTION.
  - Touchdown: the float's gap (0.56 mm) spans the ±2.5° wobble, so the refill travels 0.98 mm at 35° (0.58 mm at 75°) before the balance returns. The ink tail after a natural lift is 0.28–1.1 mm; an electro-permanent brake on the float (12–60 mW, ASSUMPTION) cuts it to about 0.3 mm.
  - The refill change: no tool, about 30 s. The cup's ball unsnaps at 0.1–0.2 N and clicks in at about 0.2 N (forces ASSUMPTION).
- **Set-up.** EXP-J17 (c)'s fixture at R12 (the tilting stage, the roll ring, the 6-axis cell under the carrier and the high-speed camera), with the head mock-up in place of study B's disc. The mock-up has the carriage, the roll cage, the tilt hinge with its balance spring, the floating face with its constant-force spring and face-position Hall sensor, the captive shoe, and three SQL-RV-1.8 motors with their drivers. If the SQL-RV-1.8 cannot be bought for prototypes, micro-stepper lead screws take their place (DEC-064), and the lift time is predicted again first. Three refill brands (metal-bodied D1) with cups. For the touchdown ink: paper on R9's plate or on R13, and R3 scans.
- **Procedure.**
  1. The follower over 35–75° and the roll cage over ±30°: range and force; the tilt motor with and without the balance spring.
  2. Each positioner unpowered: the force at which it back-drives (AC-K23-02).
  3. Lifts at 35, 50 and 75°: the time from the command until the ball is 0.5 mm off the paper, and the power while lifted (AC-K23-01).
  4. The residual side load and the touchdown travel over the tilts and rolls of AC-J17-04 and J17-05, with the head.
  5. Strokes with touchdowns over paper at 35, 50 and 75° without a float brake; R3 scans against a rigid reference pen on the same path (AC-K23-05).
  6. Refill changes by the procedure of `docs/revK_design.md` §3.4: three brands, 10 changes each (AC-K23-03).
- **Measurands.** The follower's and the roll cage's ranges and forces; the back-driving forces; the lift time and holding power; the residual side load; the touchdown travel; the touchdown ink; whether each refill change completes, and its time.

<!-- AC-TABLE:EXP-K23:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K23-01 | REQ-RVJ-N04 | Pen lift by the follower on the head mock-up (EXP-J17 (c)'s tilting stage, 35-75°, the ring on the paper): time from the command until the ball is 0.5 mm off the paper (high-speed camera), and the holding power while lifted (both) | both met (≤ 0.25 s; no holding power) | derived | DEC-064's revisit trigger (a lift slower than 0.25 s) and study K's proposed line, so derived; DEC-064's lift holds with no power; CALC (the SQL-RV-1.8's speed-force line ASSUMPTION between MFR points, AMF-15): a stroke of 1.10-1.85 mm along the pen (75-35°), up in 0.155-0.18 s and down in 0.08-0.14 s, the ink stopped after 43-72 ms, 0.08-0.31 J per lift (docs/revK_design.md s3.4); a micro-stepper fallback would change the lift time | DEC-064 (the pen lift); the spelling cue's lift (EXP-S12, S18); REQ-RVJ-N04 (Rev K's pen lift) |
| AC-K23-02 | — | The head mock-up's three SQL-RV-1.8 positioners (roll, tilt with its balance spring, follower): each moves its load over its range, and, unpowered, the force at which it back-drives (both) | both met (moves; ≥ 0.2 N) | derived | DEC-064's revisit trigger (a positioner that back-drives under 0.2 N), so derived; the SQUIGGLE's holding force against back-driving is not in its datasheets; CALC (stall force MFR AMF-15): tilt 0.082 N on its crank against the 0.30 N stall (3.6 x) with the balance spring (0.35 N without it, which the motor cannot move), roll 0.042 N (7.1 x), follower during a lift 0.20 N (1.51 x, marginal) (docs/revK_design.md s3.4) | DEC-064 (the head's positioners) |
| AC-K23-03 | — | Refill change on the head mock-up without tools, by the procedure of docs/revK_design.md s3.4, with three refill brands (metal-bodied D1), 10 changes each: every change completes (the float window read correctly), and the time per change (both) | both met (every change completes; ≤ 60 s) | hypothesis | study K's proposed line (s11.3), so a hypothesis; DEC-064 is revisited if a refill change fails for a common refill brand; PROPOSED DESIGN: no tool, about 30 s; the cup's ball unsnaps at 0.1-0.2 N and clicks in at about 0.2 N (forces ASSUMPTION) | DEC-064 (the captive shoe and the refill change) |
| AC-K23-05 | REQ-BNIB-002 | Touchdown transient with Rev K's head and no float brake (strokes over paper at 35, 50 and 75°; R3 scans): ink laid from touchdown until the full balance returns (the carrier's force cell), farther than 0.2 mm from the ink of a rigid reference pen on the same path, per stroke (95th percentile over ≥ 200 strokes) | ≤ 0.1 mm | derived | REQ-BNIB-002 as DEC-064 amends it: the float brake is fitted only if EXP-K23 or EXP-J17 (c) shows that the touchdown transient marks the ink, and no line is given; the line is the project's tail-ink metric (AC-Q08-01, REQ-PNC-006: ≤ 0.1 mm per stroke beyond 0.2 mm from a rigid pen), so derived; CALC: the refill travels 0.98 mm at 35° (0.58 mm at 75°) before the balance returns (fit check H6); the mark itself was not predicted (docs/revK_design.md s3.4) | DEC-064 and REQ-BNIB-002 (the float brake, 12-60 mW, is fitted if it fails) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-K23).
<!-- AC-TABLE:EXP-K23:END -->

- **Decision rule.** A lift slower than 0.25 s, a positioner that back-drives under 0.2 N, a refill change that fails for a common brand, or (with AC-J17-04) a residual above 25 % of F_s·cot θ at the 95th percentile: DEC-064 is revisited. A change slower than 60 s fails AC-K23-03, and the change procedure is reworked. Touchdown ink above AC-K23-05's line: the float brake is fitted, and AC-J17-05 is then judged at 0.25 mm (REQ-BNIB-002).

### EXP-K25: Does Rev K's lower servo bandwidth hold on the test writers?

- **Purpose and gates.** Run Rev K in sim2 on the test writers and several seeds, with the servo at 40 / 46 Hz (DEC-066) against study B's 80 / 100 Hz. Gates DEC-066 (revisited if the tremor ratio loses more than 0.05) and REQ-RVJ-C02 for Rev K. Until it runs, study B's sim2 results are read as slightly optimistic (DEC-066).
- **Predictions (SIM; tuning writers 100–101, seed 300, study B's tuning cells; `docs/revK_design.md` §5.6).** At study B's 80 / 100 Hz the tremor ratio was 0.87. At 40 / 100 Hz it was 0.87, with the corrected ink error 0.5 % higher. At 40 / 46 Hz it was 0.86, with the corrected ink error 7 % higher and the nib's power 29 % lower. Tremor-free writing moved 0 µm in all three. sim2 has no structural modes of the carrier, so this measures only what the lower bandwidth costs in tracking.
- **Set-up.** sim2j (or bnib/sim) with `results/revK/sim_params.json`, after the adapter that the file lists: sim2j/revj.py reads `refill_holder`, `ec_shell` and the layout's `pivot_z`, which Rev K carries as a virtual pivot. sim2j's test writers and seeds (as EXP-E17: writers 0–5, 4 seeds), at ET 8 Hz × 1 mm and PD 5 Hz × 1 mm, and tremor-free writing.
- **Procedure.** Run the three settings (80 / 100, 40 / 100 and 40 / 46 Hz) on the same writers, seeds and cells, with the nib held and correcting. Then run tremor-free writing at 40 / 46 Hz against the device-off pen.
- **Measurands.** Ink error with the nib held and correcting; the tremor ratio; tremor-free writing moved; the nib's power.

<!-- AC-TABLE:EXP-K25:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K25-01 | — | sim2j (or bnib/sim) with Rev K's sim_params (results/revK/sim_params.json, after the adapter it lists) on the test writers and several seeds: the tremor ratio (ink error with the nib correcting over the nib held) at 8 Hz x 1 mm with the servo at 40 / 46 Hz (DEC-066), less the same ratio at 80 / 100 Hz | ≤ 0.05 | derived | DEC-066's revisit trigger (more than 0.05 of the tremor ratio lost on the test writers against 80 / 100 Hz), so derived; SIM (study K, tuning writers 100-101, one seed, study B's sim2 set-up without carrier modes): the ratio 0.87 at 80 / 100 Hz and 0.86 at 40 / 46 Hz, with the corrected ink error +7 % and the nib's power -29 % at 40 / 46 Hz (docs/revK_design.md s5.6) -> predicted to pass | DEC-066 (the servo bandwidth); study B's sim2 results are read as slightly optimistic until this run |
| AC-K25-02 | REQ-RVJ-C02 | The same grid at 40 / 46 Hz: tremor-free writing moved against the device-off pen with the same noise and seed (RMS), every test writer and seed | ≤ 25 µm | requirement | REQ-RVJ-C02; SIM (study K, tuning writers 100-101, one seed): 0 µm at 80 / 100, 40 / 100 and 40 / 46 Hz (docs/revK_design.md s5.6) | DEC-066; the sim2 side of Rev K's claims |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-K25).
<!-- AC-TABLE:EXP-K25:END -->

- **Decision rule.** A ratio at 40 / 46 Hz more than 0.05 above the ratio at 80 / 100 Hz: DEC-066 is revisited; its named alternative is 40 / 100 Hz, with an inner loop that acts on current alone or has a notch at the stuck mode. Tremor-free writing moved more than 25 µm: the setting does not run on the bench (REQ-RVJ-C02).

---

## 54. The readable target and where the gap lies: EXP-E21, E22, E23, and where study F's other experiments run (study F; DEC-067…069)

### Purpose and what it gates

Study F (`docs/readable_target.md`) asked three questions: how much tremor may be left at the pen tip for words to be readable, whether gates calibrated on each user's own writing keep clean writing still, and whether the gap to perfect knowledge lies in predicting the tremor or in telling it from writing. **Nothing was built or measured on a pen or a person.** The numbers are SIM in model HW1 with study R's real inputs, with the literal AI reader standing in for people, or CALC. Every choice was made on the tuning split and frozen before one run on the test split.
- **DEC-067 (2026-09-30).** The readable target for a severe-tremor tracker: at most 0.55 mm of tremor left at the tip (study R's measure), about a third of the severe class's 1.72 mm, and about 0.25 mm for near-normal reading (REQ-CTRL-018). Every tracker result reports its tip tremor against these lines. DEC-055 stays the pass line, because a correction that moves the writing can meet a tip-tremor number and still lose every word.
- **DEC-068.** The per-user gate is calibrated raise-only: the opening threshold is the larger of the design's own threshold and the calibrated value, and calibration never lowers it (REQ-CTRL-019; refines DEC-061 and REQ-CTRL-016).
- **DEC-069.** Estimator effort goes to separating tremor from writing first, then to a drift-free position reference in the tremor band, and not to prediction or latency (REQ-SNS-006; refines DEC-052 and DEC-061).
- **The reach (the lead's notes on DEC-050 and DEC-060).** With Rev K's ±1.0 mm even perfect knowledge gains only 1.4 (0.8 to 1.9) words at the severe class, below DEC-055's +2 (SIM, the Rev J nose with its travel cut, tuning split). ±1.5 mm gains 3.2, and an estimator's own error needs about ±2–3 mm. The lead keeps ±1.0 mm for Rev K, whose nib makes no severe-tremor legibility claim (DEC-060). EXP-E23 checks this with B1's own reach and dynamics.
- **What the study found (SIM).**
  - DEC-055's +2 words needs no more than 0.65 mm of tremor at the tip on the tuning split (0.56–0.70). The test split confirmed it once, and its own curve gives 0.55 mm (0.47–0.64). Study E's best causal tracker leaves 1.12 mm.
  - Predicting the tremor over the pen's 4.9 ms horizon leaves 0.03 mm, as perfect knowledge does.
  - With the tremor alone, a linear filter on the pen's IMU leaves 0.29–0.31 mm, and an ideal drift-free position sensor 0.11–0.12 mm. With writing, the estimators leave 0.97–1.12 mm, or keep acting and move clean writing by about 2 mm.
  - Raise-only per-user gates kept every test writer's clean writing within 19.1 µm, but gained no words (information only).
- **What it gates.**
  - DEC-067 is revisited if EXP-E20 (people reading the inks) or EXP-R01 (patients' own writing) moves the +2 level outside 0.47–0.70 mm.
  - DEC-068 is revisited on EXP-R01's shadow-mode logs, or by EXP-E22.
  - DEC-069 is revisited if an estimator reaches DEC-067's target with clean writing inside DEC-055 (EXP-E10), by EXP-E21, or if broadband recordings of tremor at the pen tip (EXP-R01) make prediction harder.
  - DEC-050's and DEC-060's reach is revisited when EXP-E23 confirms study F's reach check and an estimator nears 0.55 mm; then a ±1.5–3 mm balanced nib is designed.
  - Requirements: REQ-CTRL-018, REQ-CTRL-019 and REQ-SNS-006, with REQ-CTRL-016, REQ-BNIB-003 and DEC-055's line (AC-R02-01).
- **One id per experiment.** Study F ran two of study E's experiments in simulation: EXP-E13 and EXP-E11 (§52); their results are in AC-E13-01, AC-E11-01 and AC-E11-02. It proposed EXP-E20…E23 (`docs/readable_target.md` §12). EXP-E20 is with people, inside EXP-R03's panel (`human_study_plan.md` §25). EXP-E21, E22 and E23 are specified below. DEC-067's line is also scored on EXP-E10's run (AC-E10-03).
- **Data rules.** Splits as REQ-DATA-001. Studies E and F have both used study R's test split, so any estimator aimed at the 0.55 mm target needs new held-out data (EXP-E10). UNIPEN-derived inks are for research use only (REQ-DATA-006).

### Where study F's experiments run

| Study F | Runs as | Its criteria | Note |
|---|---|---|---|
| EXP-E13 | §52, run in simulation by study F | AC-E13-01 (met in simulation) | DEC-067's number; people check it in EXP-E20 |
| EXP-E11 | §52, run in simulation by study F (information only) | AC-E11-01…03 | the real answer needs EXP-R01's shadow-mode logs |
| EXP-E20 | `human_study_plan.md` §25, inside EXP-R03's panel | AC-E20-01 (REQ-CTRL-018) | people read the E13 inks |
| EXP-E21 | its own (below): simulation, then R10 with EXP-R07's refit | AC-E21-01 (REQ-SNS-006) | the position reference's accuracy in the tremor band |
| EXP-E22 | its own (below): simulation, then the EXP-R01 shadow-mode logs | AC-E22-01 (REQ-CTRL-019) | a gate calibrated with the tremor present |
| EXP-E23 | its own (below), offline in sim2 | AC-E23-01 (REQ-BNIB-003) | B1's own reach; the set-up of EXP-K25 |
| DEC-067's line on a tracker | EXP-E10 | AC-E10-03 (REQ-CTRL-018) | reported beside DEC-055's line (AC-R02-01) |

### EXP-E21: How accurate must a position reference be in the tremor band?

- **Purpose and gates.** Find how accurate a position reference (the page sensor) must be in the tremor band for the tremor estimate to reach near-normal reading with the tremor alone. Then check the chosen die against it. Gates REQ-SNS-006's number and DEC-069.
- **Predictions (SIM and CALC; tuning split, the tremor alone; `docs/readable_target.md` §7.1).**
  - The ideal page sensor (3 µm, 2 ms; a bound) with a causal predictor leaves 0.055 mm in the tremor band and 0.11 mm at the tip (test split 0.12 mm).
  - The DeltaPen-class model (study R's pessimistic model of the one measured pen-tip sensor) has 0.286 mm in band, but its drift carries the nib away, and 1.14 mm is left at the tip. With a causal 1.5 Hz high-pass it leaves 0.59 mm.
  - The pen's IMU with a linear filter leaves 0.31 mm at the tip, and a perfect accelerometer 0.29 mm: the limit is turning acceleration into position with a fixed filter, not the sensor.
- **Set-up.** Simulation first: study F's tremor-alone sensing check (`readable/gap.py`), with the page sensor's error model swept (in-band error, drift), and a fused IMU and page estimator. Then the die chosen in EXP-T04 on rig R10, with its error model refitted (EXP-R07).
- **Procedure.**
  1. Sweep the page sensor's in-band error and drift; for each, find the tremor left at the tip with the tremor alone.
  2. Find the in-band error that reaches 0.25 mm at the tip: REQ-SNS-006's number.
  3. Run the chosen die's refitted model (EXP-T04, R07) through the same check (AC-E21-01).
- **Measurands.** The reference's error in the tremor band (study R's measure) and its drift; the tremor left at the tip with the tremor alone.

<!-- AC-TABLE:EXP-E21:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E21-01 | REQ-SNS-006 | Tremor left at the tip at the severe class with the tremor alone (no writing), estimated from the chosen page sensor's refitted error model (EXP-R07) after drift removal, with study F's sensing check, tuning split; the reference's in-band error reported against REQ-SNS-006's 0.15 mm | ≤ 0.25 mm | hypothesis | DEC-067's near-normal reading level, proposed by study F for the tremor alone, so a hypothesis; study F (SIM, tuning split, docs/readable_target.md s7.1): the ideal page sensor (3 µm, 2 ms) 0.11 mm; the DeltaPen-class model 1.14 mm (its drift), 0.59 mm high-passed; the IMU alone 0.31 mm -> predicted to FAIL with a DeltaPen-class sensor | DEC-069; REQ-SNS-006's number |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-E21).
<!-- AC-TABLE:EXP-E21:END -->

- **Decision rule.** Pass: the chosen die can be the position reference in the tremor band, and step 2 sets REQ-SNS-006's number. Fail: it cannot, and DEC-069 is revisited with EXP-E21's result.

### EXP-E22: Can a gate be calibrated when the user cannot write without tremor?

- **Purpose and gates.** A person with severe tremor has no tremor-free writing to calibrate the gate on. Calibrate the raise-only gate on writing with the tremor present, and check that it still keeps clean writing within DEC-055's 50 µm. Gates REQ-CTRL-019 for such users, and DEC-068.
- **Predictions (SIM, information only; `docs/readable_target.md` §5, §11).** Calibrated raise-only on clean writing, the gate kept every test writer within 19.1 µm (ai2's TCN) and 18.9 µm (the real-data TCN). Calibrating with the tremor present raises the threshold by the tremor itself, so the gate may stay shut and remove little tremor. Not simulated.
- **Set-up.** Simulation on the tuning split first (HW1, real inputs, the DeltaPen-class page sensor), then the EXP-R01 shadow-mode logs. The gate is calibrated on writing with the tremor present, from the estimate's size outside the tremor band or from low-tremor periods. A separate clean note of the same writer is scored.
- **Procedure.** For each writer: calibrate the raise-only gate on writing with severe tremor, by each candidate method (fixed on tuning writers); score the separate clean note and the tremor cases.
- **Measurands.** Clean writing moved per writer; each writer's threshold, against the one set from clean writing; the tremor left and the words read at the severe class.

<!-- AC-TABLE:EXP-E22:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E22-01 | REQ-CTRL-019 | Clean real writing moved with the raise-only gate calibrated on the same writer's writing with severe tremor present (the scored clean note separate), in simulation on the tuning split, then on the EXP-R01 shadow-mode logs: the largest single writer | ≤ 50 µm | derived | DEC-055's per-writer cap, as AC-E11-02, so derived; raise-only calibration on clean writing gave 19.1 µm (SIM, information only); calibrating with the tremor present raises the threshold by the tremor itself (docs/readable_target.md s11): not simulated, no prediction | DEC-068 (for users who cannot write without tremor) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-E22).
<!-- AC-TABLE:EXP-E22:END -->

- **Decision rule.** Every writer within 50 µm: the method becomes the calibration for users who cannot write without tremor (REQ-CTRL-019). Any writer above it: DEC-068 is revisited for those users.

### EXP-E23: Does the B1 nib's own reach deliver the readable target?

- **Purpose and gates.** Study F's reach check kept the Rev J nose's mass and servo and only cut its travel. Repeat it with the B1 nib's own reach and dynamics in sim2. Gates DEC-050's and DEC-060's reach, and REQ-BNIB-003's travel.
- **Predictions (SIM; the Rev J nose with its travel cut, tuning split, 20 severe cases; `docs/readable_target.md` §8).**
  - With ±1.0 mm, perfect knowledge leaves 1.00 mm and gains 1.4 (0.8 to 1.9) words read; with the full reach, 8.3 words are read. With ±1.5 mm it leaves 0.67 mm and gains 3.2 (2.6 to 3.7) words.
  - The nib sits at its travel limit 64 % of the writing time at ±1.0 mm and 40 % at ±1.5 mm.
  - An estimate that itself leaves the +2 residual keeps it only with about ±2–3 mm: 0.65 mm at ±3, 0.71 mm at ±2, 0.82 mm at ±1.5 and 1.04 mm at ±1.0 mm.
  - Clipping costs about a word less than the curve says, so the words read decide.
- **Set-up.** sim2 with the B1 nib: study B's set-up (bnib/sim), or sim2j with Rev K's `sim_params.json` after its adapter (as EXP-K25), with the servo at 40 / 46 Hz (DEC-066). Study R's real inputs at the severe class, PD and ET; the literal reader.
- **Procedure.** Run perfect knowledge and the E13 amplitude levels at ±1.0 and ±1.5 mm, and read every note.
- **Measurands.** The tremor left at the tip; the share of time at the travel limit; the words read against the ordinary pen.

<!-- AC-TABLE:EXP-E23:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-E23-01 | REQ-BNIB-003 | Words out of 10 gained over the ordinary pen at the severe class with perfect knowledge and the B1 nib at its design reach (Rev K's ±1.0 mm; ±1.5 mm also run), in sim2 with B1's own dynamics (40 / 46 Hz, DEC-066), study R's real inputs and the literal reader: the mean over writers | ≥ 2 words, 95 % interval above 0 | hypothesis | DEC-055's words line; REQ-BNIB-003's travel is what it decides; study F (SIM, the Rev J nose with its travel cut, tuning split, docs/readable_target.md s8): 1.4 (0.8 to 1.9) words at ±1.0 mm and 3.2 (2.6 to 3.7) at ±1.5 mm -> predicted to FAIL at ±1.0 mm | DEC-050; DEC-060 (the nib's reach) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-E23).
<!-- AC-TABLE:EXP-E23:END -->

- **Decision rule.** Below DEC-055's +2 at ±1.0 mm, as predicted: Rev K's nib keeps making no severe-tremor legibility claim (DEC-060). If it confirms study F's reach check and an estimator nears DEC-067's 0.55 mm (EXP-E10, AC-E10-03), a ±1.5–3 mm balanced nib is designed (DEC-060).

---

## 55. The first bench build: EXP-BB01…BB09, the builds B0–B4 and their gates (study H; DEC-095…099)

### Purpose and what it gates

Study H (`docs/bench_build_plan.md`) turned study M's rigs, the gates of `prototype_stages.md` §0, Rev K's layout, and the independent engineering pass's fine-stage candidates (DEC-072) and five-bar (DEC-071) into five builds that a small team can order and run. It gives bills of materials with sourced prices, fabrication, safety, a test-to-decision map, a budget and a schedule, data templates and a check of the data pipeline (`results/benchbuild/`). **Nothing has been bought, built or measured.** Prices seen on 2026-09-30 are MANUFACTURER (AMF-300…322, OPT-100…101). The force sensors, machined parts and specialist services are ASSUMPTION ranges. Loads, modes and stiffnesses are CALC (`results/benchbuild/bench_calcs.json`). The pipeline check ran synthetic data through `rig/` (SIM, 11 of 11 steps).
- **DEC-095 (2026-09-30).** The first bench build is DAQ-1 plus R9 (G1). It is ordered in week 1, together with every long-lead item for the G2 coupons, the five-bar and R10. G1 runs in weeks 1–4: EXP-T02's minimum ink force first (with dead weights if the voice coil is late), then EXP-T01. No coupon geometry is frozen before G1's F_c,min and side load are known. The first force-constant coupons use stock magnets, with the predictions regenerated at the as-built size (§0.2); custom magnets are ordered only after AC-T07-02 passes. The minimum first build costs about USD 4,350–7,750, or USD 6,070–10,150 with the instruments a bare lab lacks; all five builds about USD 14,000–35,400.
- **DEC-096.** DEC-072's choice between the reach candidate (±1.5 mm) and the margin candidate (±1.059 mm) is made by re-running the pass's duty screen (`python -m revk.improve`) with measured inputs:
  - the residual lateral load at the carrier (EXP-J17 (c): the 95th percentile over 35–75° and roll, plus the moving mass's weight across the axis, 29.5 mN at 35° by CALC);
  - the K_m map (EXP-T07);
  - the guide drag at the chosen preload (EXP-K20, BB05);
  - the anchor's stiffness (EXP-BB03).

  The 1.5 mm candidate is taken only if its re-run worst copper loss stays within the 0.15 W allocation and EXP-BB04 passes. Provisional reading (CALC): 0.15 W is reached at about 34 mN of residual load for the 1.5 mm candidate and about 53 mN for the 1.059 mm candidate. The calculated loads at 35° sum to about 49–51 mN (gravity 29.5, the face's residual at the 95th percentile 11.2–13.1, guide drag 8.1). So the 1.059 mm stage goes forward unless the measured loads are lower.
- **DEC-097.** Beryllium-copper wire is bought already age-hardened, and no heat treatment is done at the bench. The handling rules are in §0.10 and EXP-K21.
- **DEC-098.** Wire fatigue coupons (EXP-K21, B25, BB04) are driven at no more than 0.2 × the first transverse mode measured on each coupon. Failure is an open circuit or a step of more than 2 % in the 4-wire resistance. Several coupons run in parallel on one crank-driven shuttle, so 43.2 M cycles take 3–8 days per batch: about 3.3–5.2 days for 26.8 mm wires and 6.7–7.5 days for 34 mm wires (CALC). At the 200 Hz that the protocols named before, the wires' own resonance adds stress the pen never sees: the clamp stress rises 12–33 % for 26.8 mm wires (first modes about 487–763 Hz) and about 90 % for 34 mm wires (about 336–373 Hz) (CALC).
- **DEC-099.** The five-bar is benched with a passive 24 mm dummy pen and spring hand simulants, never with a person's hand, until a safety gate like G-S is written for it. Its first build has a hardware current limit at the motors' rated current, the 0.4 N cap in software, a breakaway magnetic pen coupling that releases between 0.5 and 0.8 N as the physical backstop, guards over the capstans, and a latching emergency stop that removes motor power. At rated current the linkage can still push about 1.06 N at its worst pose and direction (CALC), so the current limit alone cannot hold the cap. Accepted-word results are claimed only from its measured replay (EXP-BB06, BB07), not from the rigid model.
- **What it gates.**
  - DEC-095 is revisited if the K3D40 or LSB200 lead time is over 6 weeks. Then the low-cost G1 build of `docs/measurement_rig.md` §2.9 starts first.
  - DEC-096 is revisited if the duty screen misses the first nib's measured coil heat (EXP-J17 (b), EXP-T12) by more than 20 %.
  - DEC-097 is revisited if no supplier can deliver aged 0.10 mm wire. Then a supplier with beryllium controls heat-treats it.
  - DEC-098 is revisited if two drive frequencies on the same coupon lot give the same cycles to failure.
  - DEC-099 is revisited once EXP-BB06 and BB07 pass and a G-S-type gate for the five-bar exists.
  - Requirements: REQ-DATA-001, REQ-ENV-002, REQ-BNIB-007, REQ-RVK-003, REQ-RVK-004, REQ-RVJ-C05, REQ-CAP-003 and REQ-CTRL-003.
- **One id per experiment.** Study H proposed EXP-BB01…BB09 only where no existing experiment covers the need (`docs/bench_build_plan.md` §14.2). The rest of the build runs existing experiments: EXP-T01, T02, T04, T05, T07 (with study K's K22), K20, K21 and EXP-J17 (c). The two-letter prefix keeps these ids apart from study B's EXP-B20…B32; `check_criteria.py` accepts one or two letters.
- **No participants.** Every build is bench-only, so gate G-S does not arise. Its principle still stands (`prototype_stages.md` §1).

### The builds, their gates and their experiments

| Build | What it is | Gate (`prototype_stages.md` §0) | Weeks (DEC-095) | Study H's experiments | Existing experiments it runs |
|---|---|---|---|---|---|
| **B0 DAQ-1** | A Teensy 4.1 and an ADS131M08 evaluation board, thermocouple amplifiers and a current drive: every instrument on one clock | all (order 0) | 0–2 | EXP-BB01 | — |
| **B1 R9** | The contact and ink rig on a Prusa CORE One+ frame. First build: dead-weight F_c, no encoders, a printed tilt arc, the K3D40 ±2 N plate and the LSB200 100 g cell | G1 (order 1) | 1–4 | EXP-BB02, BB09 | EXP-T02 first, then T01; the frame later carries EXP-J17 (c) (B2) and R10 (B4) |
| **B2 G2 coupons** | Force-constant coupons with stock magnets (Rev K's coil; the reach candidate's winding); C17200 wire coupons on a crank-driven fatigue shuttle; ball-guide coupons (both guides); the floating anchor; the counter-face bench on R9's frame | G2 (order 4); "Build Rev K's nib"; DEC-072 through DEC-096 | 3–8 (the G2 meeting in week 8) | EXP-BB03, BB04, BB05 | EXP-T07 (with K22), K21, K20, EXP-J17 (c) |
| **B3 five-bar** | The pass's desk-grounded demonstrator (Faulhaber 2224 motors, 6:1 capstans, 14-bit output encoders), bench only (DEC-099) | none yet (the grounded route, DEC-071) | 6–12 | EXP-BB06, BB07 | — |
| **B4 R10** | The page-sensing rig on R9's frame, with a strobed camera as truth | sensing build gate (order 2) | 6–12 (a meeting in week 12) | EXP-BB08 | EXP-T04, T05 |

Not in this first build: R11's recording pen (it waits for ethics approval); R13 and R14 (they need a working nib); Rev K's head mock-up (EXP-K23: its motors are sold only in volume); Hall interference (EXP-T09); EXP-T08's keeper pull (it needs a sensor above about 11 N); and EXP-J17 (a) and (b) (they need a built nose or nib).

### EXP-BB01: Does DAQ-1 keep every record on one clock?

- **Purpose and gates.** Bring DAQ-1 up and qualify its time base before any record counts: frame integrity, ADC noise, the mapping of another device's clock, encoder counting and the current output. Gates DEC-058 (one clock) and order 0 of every gate. REQ-DATA-001.
- **Predictions.** ADC noise 1.20 µV RMS at gain 128 and 4 kSPS with the inputs shorted (MFR AMF-221/222); the line allows twice that for layout and excitation noise. SIM (`rig.selftest`): the parser rejected every corrupted frame, and the sync fit's worst residual was 6 µs with 20 ppm of drift. The LM13 13B at 100 mm/s gives about 0.41 M counts/s (MFR OPT-89).
- **Set-up.** DAQ-1 as assembled (`docs/bench_build_plan.md` §3.3). Its firmware is compiled for the Teensy here for the first time. A signal generator for the encoder loop-back; the five-bar's controller as a second device with its own clock; R9's voice coil for the current step.
- **Procedure.**
  1. Ten minutes at 8 kSPS with every channel enabled: CRC errors and missing frames in the logger's statistics (AC-BB01-01).
  2. Inputs shorted at gain 128 and 4 kSPS for 60 s: the noise of each channel (AC-BB01-02).
  3. Sync out looped to the device input, then the second device: its clock fitted onto DAQ-1's over at least 10 min (AC-BB01-03).
  4. Quadrature from the signal generator at 0.5 M counts/s into each encoder input, over 10⁶ counts (AC-BB01-04).
  5. The current output chain into R9's voice coil at 0.1–0.5 A: the 10–90 % step time and the DC error (AC-BB01-05).
- **Measurands.** CRC errors; missing frames; noise; the clock fit's worst residual; lost counts; the step time and DC error.

<!-- AC-TABLE:EXP-BB01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB01-01 | — | Ten minutes at 8 kSPS with every channel of the rig enabled: CRC errors and missing frames in session.json stats (rig.logger) | both met (0 CRC errors; 0 missing frames) | derived | docs/measurement_rig.md s1.3 bring-up step 3; SIM: the parser rejects every corrupted frame (rig.selftest) | every rig verdict (one clock) |
| AC-BB01-02 | — | Input-referred noise of each ADS131M08 channel at PGA 128, inputs shorted, 4 kSPS, RMS over 60 s | ≤ 2.4 uV | hypothesis | 2 x the manufacturer's 1.20 uV RMS at 4 kSPS and gain 128 (MFR AMF-221/222, Table 7-1); the factor 2 for layout and excitation noise is PROPOSED | the force-channel budgets of rig.uncertainty |
| AC-BB01-03 | — | Mapping of a device clock onto DAQ-1's by the coded sync pulse (loop-back sync out to DUT in, then the five-bar controller): largest residual of rig.sync.fit_clock over ≥ 10 min | ≤ 50 µs | derived | bench_protocols.md s0.4 alignment requirement; SIM 6 µs with 20 ppm drift (rig.selftest) | any record that combines DAQ-1 with another clock |
| AC-BB01-04 | — | Quadrature loop-back from a signal generator into each encoder input at 0.5 M counts/s (LM13 13B at 100 mm/s is about 0.41 M counts/s): counts lost over 10^6 counts | = 0 | hypothesis | PROPOSED; LM13 13B resolution about 0.244 µm (MFR OPT-89) | encoder truth of R9, R10 and the five-bar |
| AC-BB01-05 | — | Current output chain (12-bit PWM, RC filter, current amplifier) into R9's voice coil: 10-90 % step time and DC error at 0.1-0.5 A (both) | both met (≤ 2 ms; ≤ 1 % of full scale) | hypothesis | PROPOSED: F_c ramps of EXP-T02 and the reversal steps of EXP-T07 need ms settling | EXP-T02 ramp lines; EXP-T07 current steps |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-BB01).
<!-- AC-TABLE:EXP-BB01:END -->

- **Decision rule.** Any failure: fix the firmware or the wiring, and repeat. No other record counts until EXP-BB01 passes. The current step (AC-BB01-05) is needed only once the voice coil replaces the dead weights.

### EXP-BB02: Is R9's frame good enough for G1?

- **Purpose and gates.** Qualify R9's frame: the plate stack's first mode (DEC-058's revisit trigger), the head's speed with the 190 g head, the plate's calibration in situ and the refill guide's stiffness. Gates DEC-058 and the validity of EXP-T01 and T02. REQ-ENV-002.
- **Predictions (CALC; `results/rig/cad/rig_contact_summary.json`).** The plate stack's first mode is 151 Hz with the ±2 N plate and 338 Hz with the ±10 N plate, without the sensor's own top mass. The guide stiffness is 25.6 N/m ±30 % (E 200 GPa, ASSUMPTION). The plate's linearity error is 0.2 % of full scale (MFR AMF-224). The printer's page gives no payload or speed accuracy (AMF-231).
- **Set-up.** R9 as built (`docs/bench_build_plan.md` §4.4): the K3D40 ±2 N plate, the platen, three underlays and paper. The LM13 encoders for AC-BB02-02 (standard build).
- **Procedure.**
  1. A tap test of the plate stack on each underlay (AC-BB02-01).
  2. EXP-T01's strokes at 3–100 mm/s with the 190 g head: the speed in each steady window (AC-BB02-02; it waits for the encoders).
  3. The plate calibrated in situ at each test angle (`rig.calib.fit_plate`): the residual per axis (AC-BB02-03).
  4. The cartridge's axial stiffness with the refill off the paper (`rig.calib.fit_guide_stiffness`; AC-BB02-04).
- **Measurands.** The first mode; speed stability; the calibration residual; the guide stiffness.

<!-- AC-TABLE:EXP-BB02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB02-01 | — | First mode of the plate stack on the bed (K3D40, platen, underlay, paper) by tap test, lowest over the three underlays | ≥ 100 Hz | derived | DEC-058's falsifier (a plate mode below 100 Hz); CALC 151 Hz (+-2 N) and 338 Hz (+-10 N) without the sensor's own top mass (results/rig/cad/rig_contact_summary.json) | DEC-058; validity of EXP-T01's ripple and EXP-T03 |
| AC-BB02-02 | — | Head speed during EXP-T01 strokes with the 190 g head at 3-100 mm/s: fraction of each steady window within +-20 % of its median speed (rig.contact.analyse_stroke's rule) | ≥ 95 % | hypothesis | the analysis's steady-window rule; the CORE One page gives no payload or speed accuracy (MFR AMF-231); 95 % PROPOSED | EXP-T01 validity; the printer frame as motion source (DEC-058) |
| AC-BB02-03 | — | In-situ plate calibration at the test angle (rig.calib.fit_plate): residual RMS per axis over the calibration loads, as a share of full scale | ≤ 0.2 % | hypothesis | relative linearity error 0.2 % FS (MFR AMF-224) | AC-T01-02's uncertainty budget |
| AC-BB02-04 | — | Axial stiffness of the leaf-guided cartridge fitted with the refill off the paper (rig.calib.fit_guide_stiffness) | within 17.9-33.3 N/m | hypothesis | CALC 25.6 N/m +-30 % (results/rig/cad/rig_contact_summary.json; E 200 GPa ASSUMPTION) | the guide-force correction of F_c in EXP-T01/T02 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-BB02).
<!-- AC-TABLE:EXP-BB02:END -->

- **Decision rule.** A first mode below 100 Hz: stiffen the stack or use the ±10 N plate; a persistent failure reopens DEC-058. Speed or calibration outside their lines: the affected EXP-T01 and T02 verdicts wait until they pass. A guide stiffness outside its band: the guide-force correction of F_c is refitted before EXP-T01 and T02 count.

### EXP-BB03: Is the soft wire anchor as soft as designed?

- **Purpose and gates.** The reach candidate's wire fatigue margin rests on an axially soft anchor: 80–120 N/m in all, and at most 5 mN of assembly tension on the wires. It replaces Rev K's 10,000 N/m anchor (DEC-072). Measure the etched four-beam anchor alone and with its interconnect, and the tension it leaves on the wires. Gates DEC-072, DEC-096 (the anchor's stiffness enters the duty re-run) and EXP-BB04's Goodman factor. REQ-BNIB-007.
- **Predictions (CALC).** The beams alone give 76.6 N/m at 35 µm × 0.5 mm × 6 mm (E 193 GPa, ASSUMPTION; `results/improvement/mechanics/cad_summary.json`). A 1 µm thickness error moves this by 8.6 % (`bench_calcs.json`). The interconnect adds about 23.4 N/m, for about 100 N/m in all. The Goodman factor of 1.70 was computed with 120 N/m and 5 mN at the worst corner.
- **Set-up.** The etched 301-foil coupon (`floating_anchor_coupon.step`). The foil is measured at five points per sheet, and the beam width is set from that. The anchor's frame on a precision balance (at least 1 mg readability); a 1 µm micrometer; a microscope.
- **Procedure.**
  1. The hub pushed 0–100 µm in 10 µm steps, with the force from the balance; the stiffness is the slope (AC-BB03-01).
  2. The same with the flexible interconnect and its terminations fitted (AC-BB03-02).
  3. After assembly with the eight wires: the hub's offset from its free position under the microscope, times the measured stiffness (AC-BB03-03).
- **Measurands.** The beam stiffness against 4 E w t³/L³ with the measured t and w; the total stiffness; the assembly tension.

<!-- AC-TABLE:EXP-BB03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB03-01 | — | Axial stiffness of the etched 301 four-beam anchor alone (hub pushed 0-100 µm in 10 µm steps, force by a ≥ 1 mg balance), as a ratio to 4 E w t^3 / L^3 with the coupon's measured thickness and beam width | within 0.85-1.15 | hypothesis | CALC 76.6 N/m at 35 µm x 0.5 mm x 6 mm (results/improvement/mechanics/cad_summary.json; E 193 GPa ASSUMPTION); a 1 µm thickness error moves it 8.6 % (bench_calcs.json); 15 % PROPOSED | the anchor model of revk/feasibility.py (wire tension at the stop) |
| AC-BB03-02 | — | Total axial stiffness of the anchor with its flexible interconnect and terminations as assembled | within 80-120 N/m | derived | the pass's target range (cad_summary.json: nominal 100 N/m including about 23.4 N/m for the cable); the Goodman factor 1.70 was computed with 120 N/m at the worst corner | DEC-072 (the reach candidate's wire fatigue margin) |
| AC-BB03-03 | REQ-BNIB-007 | Axial tension on the eight wires after assembly: the anchor hub's offset from its free position (microscope) times the measured stiffness | ≤ 5 mN | derived | assembly_tension_max 0.005 N in the reach candidate's fatigue screen (results/improvement/mechanics/mechanics_study.json) | DEC-072; EXP-BB04's Goodman factor |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-BB03).
<!-- AC-TABLE:EXP-BB03:END -->

- **Decision rule.** A beam stiffness off the calculation: re-etch with a corrected beam width. Outside 80–120 N/m with the interconnect: a softer interconnect. A tension above 5 mN: the assembly is reworked before any fatigue run of EXP-BB04 counts.

### EXP-BB04: Do the reach candidate's wires survive the 1.7 mm stop?

- **Purpose and gates.** The reach candidate has eight 0.10 mm C17200 wires of 34 mm, two in parallel per lead, a 1.7 mm stop and the soft anchor. EXP-K21's criteria fix Rev K's 26.8 mm wires and stop, so this is its own test. Measure the lead resistance, the fatigue at the stop with current, the Goodman factor with the measured Kt and tension, and the wires' heating. Gates DEC-072 (keep or drop the 1.5 mm candidate) through DEC-096. REQ-RVK-004 and REQ-BNIB-007. AC-BB04-05 also judges the validity of every wire fatigue run (EXP-K21, B25; DEC-098).
- **Predictions (CALC).** 0.339 Ω per wire and 0.17 Ω per lead (22 % IACS, MFR AMF-251; `mechanics_study.json`). A Goodman factor of 1.696 at the worst corner (Kt 2.5, 120 N/m, 5 mN). The wire rises 45 K above its clamps at 0.160 A continuous (105 W/m·K is Materion's rod value, an ASSUMPTION for a 0.10 mm wire). The first mode is about 336 Hz at 5 mN of tension and 373 Hz at 11 mN, so the drive is 67–75 Hz and a batch takes 160–180 h (`bench_calcs.json`).
- **Set-up.**
  - Wire coupons soldered under the fume absorber into brass clamps with a 0.12 mm slot and a 0.10 ± 0.02 mm exit radius (crimp tubes as the alternative), on the anchor at 80–120 N/m (EXP-BB03). The beryllium rules of §0.10 apply (DEC-097).
  - The crank-driven fatigue shuttle (PROPOSED DESIGN, no CAD yet): six or more stations, and a ground eccentric that sets the 1.7 mm stroke. The crank turns at 4,000–9,000 rpm, so it is balanced and guarded.
  - An eight-channel constant-current source at 0.1 A per wire, with each wire's 4-wire resistance logged on DAQ-1.
  - A gauge cannot be bonded on a 0.10 mm wire, so Kt comes from 10× scaled coupons: 1.0 mm C17200 in scaled clamps with 0.2 mm-grid gauges. The lead is to confirm the method (open item).
- **Procedure.**
  1. The resistance of each lead, clamp to clamp, 4-wire at 20 °C (AC-BB04-01).
  2. Each coupon's first transverse mode, by a sine sweep or a tap, read with a laser sensor or the camera. The drive is then set at no more than 0.2 × that mode (AC-BB04-05).
  3. Kt on the scaled coupons, and the assembly tension (EXP-BB03): the Goodman factor (AC-BB04-03).
  4. Fatigue at the 1.7 mm stop to 43.2 M cycles with 0.1 A in each wire, at least 3 coupons per clamp type (§0.7), and spares to failure. An open circuit or a step of more than 2 % in the 4-wire resistance stops a coupon for inspection at 50× (AC-BB04-02). Then the resistance again.
  5. The wire's heating at 0.16 A by resistance thermometry, with its resistance coefficient calibrated in the printer chamber at 20–50 °C (AC-BB04-04).
- **Measurands.** Lead resistance before and after the cycling; the first mode and the drive frequency; Kt; the tension; cycles without failure; the Goodman factor; the heating.

<!-- AC-TABLE:EXP-BB04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB04-01 | REQ-RVK-004 | Resistance of each lead of the reach candidate (two 0.10 mm x 34 mm C17200 wires in parallel, clamp to clamp, 4-wire, 20 °C), before and after the cycling of AC-BB04-02 | ≤ 0.3 ohm | requirement | REQ-RVK-004; CALC 0.339 ohm per wire, 0.17 ohm per lead (mechanics_study.json, 22 % IACS as MFR AMF-251) | DEC-072 |
| AC-BB04-02 | REQ-RVK-004 | Cycles at the 1.7 mm stop with the anchor at 80-120 N/m, each wire carrying 0.1 A, at least 3 coupons per clamp type, drive at no more than 0.2 x the coupon's measured first mode: an open circuit or a > 2 % resistance step counts as failure | no failure in 43.2 M cycles | requirement | REQ-RVK-004 (no lead fails in 43.2 M cycles at the stop travel while carrying 0.1 A), as AC-K21-02 for Rev K's wires; REQ-BNIB-007's life; CALC Goodman 1.70 at the worst corner (Kt 2.5, 120 N/m, 5 mN); DEC-098 for the drive and the failure test | DEC-072 (the reach candidate) |
| AC-BB04-03 | REQ-BNIB-007 | Goodman safety factor at the 1.7 mm stop with the clamp's measured stress concentration and the measured assembly tension | ≥ 1.5 | requirement | REQ-BNIB-007; CALC 1.696 at the worst corner (mechanics_study.json) | DEC-072 |
| AC-BB04-04 | — | Rise of a wire above its clamps at 0.16 A continuous by 4-wire resistance thermometry (the wire's resistance coefficient calibrated in the printer chamber at 20-50 °C), as a ratio to dT0 = I^2 rho L^2 / (8 kappa A^2) | within 0.75-1.25 | hypothesis | CALC 45 K at 0.160 A (wire_continuous_rms_current_A in mechanics_study.json; 105 W/mK is Materion's rod value used as an ASSUMPTION for a 0.10 mm wire) | the wire-heat limit of the duty screen |
| AC-BB04-05 | — | Validity of every fatigue run on wire coupons (EXP-BB04, K21, B25): drive frequency divided by the first transverse mode measured on that coupon | ≤ 0.2 | derived | CALC: at 200 Hz the clamp stress of a 34 mm wire rises about 90 % over quasi-static, of a 26.8 mm wire 12-33 %; at 0.2 x f1 about 7 % (results/benchbuild/bench_calcs.json); DEC-098 | validity of AC-BB04-02/03, AC-K21-02/04 and AC-B25-01 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-BB04).
<!-- AC-TABLE:EXP-BB04:END -->

- **Decision rule.** A failure, a Goodman factor below 1.5 or a lead above 0.3 Ω: the reach candidate is dropped, and the 1.059 mm candidate stays (DEC-096). A drive above 0.2 × the coupon's first mode voids the run. Heating outside ±25 % of the model: the duty screen's wire-heat limit is refitted.

### EXP-BB05: How much drag does the ball guide add, and at what preload?

- **Purpose and gates.** The pass calculates 8.07 mN of rolling drag for the reach candidate's full-ring guide at the 4 N preload, above EXP-K20's 5 mN line. Measure the drag and the carrier's tilt against preload for both guides, Rev K's and the reach candidate's, and whether a bare titanium flange face survives. Gates DEC-063 (the preload), DEC-072 through DEC-096 (the drag enters the duty re-run), and the flange's material. REQ-RVK-003.
- **Predictions (CALC; `docs/mechanics_improvement_audit.md`).** 8.07 mN ±30 % at 4 N and the 35° couple (rolling coefficient 0.001, ASSUMPTION). A peak Hertz pressure of 2.64 GPa on the flange face, against Ti-6Al-4V's 0.91–1.11 GPa yield strength (LIT AMF-20), so the face is expected to indent (ASSUMPTION). Rev K's guide: 2.6 mN at the couple's ball load (EXP-K20).
- **Set-up.** The lapped 440C races of both guides on wave springs over the K3D40 ±10 N, whose Fz channel reads the preload; 0.8 mm Si3N4 balls; two flanges, one with 440C race inserts and one with a bare titanium face; the couple from a dead weight on a lever; R12's stage sweeping the flange through a 10 g LSB200 cell; a laser lever for the tilt; profilometry at a metrology lab. The K3D40 cannot judge a 5 mN line (TUR 0.56–0.71), so the 10 g cell measures the drag (TUR 12–15; CALC).
- **Procedure.**
  1. For each guide, the preload stepped through 1, 2, 3 and 4 N with a micrometer screw, read on Fz.
  2. At each preload, with the 35° couple applied: the carrier's tilt; then sweeps of ±1.26 mm (Rev K) or ±1.5 mm (reach) at 8 Hz. The drag is half the forward-minus-return force at the same position (AC-BB05-01 at 4 N; AC-BB05-02 at the lowest preload that holds the tilt).
  3. EXP-K20's drop series with both flanges, then the faces under the profilometer (AC-BB05-03).
  4. The CAD has no ball retainer, so the coupon starts without one and records whether the balls migrate.
- **Measurands.** Drag and tilt against preload, per guide; marks on the faces; ball migration.

<!-- AC-TABLE:EXP-BB05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB05-01 | — | Rolling drag of the reach candidate's full-ring guide (15.1 mm ball circle, 2 x 6 Si3N4 0.8 mm balls, lapped 440C races) at the 4 N design preload and the 35° couple, swept +-1.5 mm at 8 Hz; drag from the forward/return half-difference on a 10 g cell | within 5.6-10.5 mN | hypothesis | CALC 8.07 mN +-30 % (rolling coefficient 0.001 ASSUMPTION; docs/mechanics_improvement_audit.md) | DEC-072's duty re-run (DEC-096) |
| AC-BB05-02 | REQ-RVK-003 | For each guide (Rev K's and the reach candidate's), preload stepped 1, 2, 3, 4 N: at the lowest preload whose carrier tilt under the 35° couple stays within 0.2 mrad, the drag (both) | both met (tilt ≤ 0.2 mrad; drag ≤ 5 mN) | derived | REQ-RVK-003's tilt line; DEC-063's 5 mN trigger (AC-K20-01); the pass calculates 8.07 mN at 4 N | DEC-063 (the preload); DEC-072 |
| AC-BB05-03 | — | Marks on a bare Ti-6Al-4V flange face after the EXP-K20 drop series, against a flange with 440C race inserts (profilometer) | none | hypothesis | CALC Hertz 2.64 GPa on the flange face (mechanics audit) against Ti-6Al-4V yield 0.91-1.11 GPa (LIT AMF-20): indentation expected (ASSUMPTION) | the flange's material (hardened race inserts or not) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-BB05).
<!-- AC-TABLE:EXP-BB05:END -->

- **Decision rule.** No preload that meets both the tilt and 5 mN: another guide topology (study N), and DEC-063 is revisited. Marks on the bare face: hardened race inserts in the pen's flange. The measured drag at the chosen preload goes into DEC-096's re-run.

### EXP-BB06: Is the five-bar what its model says, and is it safe?

- **Purpose and gates.** No experiment has tested the five-bar. Check that the rigid, ideal model of the grounded study describes the hardware (endpoint accuracy, continuous force, stiffness), and check DEC-099's safety features before any motion test. Gates DEC-071 (whole letters need a grounded stage) and DEC-099. No requirement.
- **Bench only (DEC-099).** A passive 24 mm dummy pen, with a refill and brass ballast, sits in a holder with a breakaway magnetic coupling. Springs of 200 and 500 N/m on a linear guide stand in for a resisting hand. No person's hand is used until a safety gate like G-S is written for the five-bar (`prototype_stages.md` §1, principle 4). The first build has a hardware current limit at rated current, the 0.4 N cap in software, the coupling that releases at 0.5–0.8 N as the physical backstop, guards over the capstans and the sweep of the links, and a latching emergency stop that removes motor power.
- **Predictions (CALC; `wholepen/grounded.py`, `bench_calcs.json`).** Motors 50 mm apart; links of 60 and 90 mm; a 60 × 40 mm writing patch centred 90 mm from the motor line; 6:1 capstans (80 % efficiency, ASSUMPTION). The continuous force is at least 0.480 N over the sampled patch; at rated current the linkage can push up to about 1.06 N at the worst pose and direction; the reflected mass is 93–105 g. The 14-bit encoders quantise the endpoint to 8.0 µm (1σ, worst case), against 2.0 µm at the model's 16 bits. SIM: 11.6 µm RMS with 14-bit counts in the pipeline check.
- **Set-up.** The five-bar as built (`docs/bench_build_plan.md` §6.4). Its controller Teensy with current loops and the 0.4 N cap (this firmware is not written yet), on DAQ-1's clock through the sync pulse. The K3D40 ±10 N at a clamped or blocked holder; the strobed OV9281 camera with a dot grid as endpoint truth.
- **Procedure.**
  1. **Safety first** (checklist G): the emergency stop removes motor power; with the holder blocked, the steady force stays at or below 0.4 N at every pose and command; the coupling releases between 0.5 and 0.8 N (AC-BB06-04, guarded acceptance). Nothing else runs until this passes.
  2. Link lengths and encoder offsets fitted on 20 camera poses; the endpoint judged on 35 other poses over the patch (AC-BB06-01).
  3. The continuous force at the clamped holder with both motors at rated current, in 8 directions at 9 poses (AC-BB06-02).
  4. The stiffness at the holder with both joints servo-held, and the lost motion on reversal (AC-BB06-03).
- **Measurands.** The force cap and the release force; the endpoint error; the force disk; the stiffness and lost motion.

<!-- AC-TABLE:EXP-BB06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB06-01 | — | Endpoint position from the two 14-bit output encoders through forward kinematics (link lengths and encoder offsets fitted on 20 poses) against camera dot-grid truth on 35 other poses over the 60 x 40 mm patch | ≤ 50 µm RMS | hypothesis | PROPOSED: a third of the 150 µm position tube of the pass's observer study; CALC quantisation 8 µm (bench_calcs.json); SIM 11.6 µm RMS in the pipeline check | the rigid-link assumption of wholepen/grounded_replay.py; DEC-071 |
| AC-BB06-02 | — | Continuous force at a clamped pen holder with both motors at rated current (K3D40 +-10 N), lowest over 8 directions at 9 poses | ≥ 0.40 N | derived | the controller's 0.4 N cap; CALC minimum 0.480 N over the sampled patch (Faulhaber 2224 U 012 SR sheet; 6:1 and 80 % efficiency ASSUMPTION) | DEC-071; EXP-BB07 |
| AC-BB06-03 | — | Stiffness of the linkage at the pen holder with both joints servo-held, lowest over directions and poses; lost motion on reversal reported | ≥ 4 N/mm | hypothesis | PROPOSED: 0.1 mm deflection at the 0.4 N cap, the grounded gate's 0.10 mm RMS ink line; the model assumes rigid links | the rigid-link assumption of the grounded replay |
| AC-BB06-04 | — | Force cap and release with the holder blocked, at every pose and command: steady endpoint force under the software cap, and the breakaway force of the pen holder's magnetic coupling (both; guarded acceptance) | both met (≤ 0.4 N; release between 0.5 and 0.8 N) | derived | the 0.4 N cap is the pass's ASSUMPTION, not a clinical limit; at rated current the linkage can push up to about 1.06 N at the worst pose and direction while its guaranteed disk is 0.48 N (CALC, bench_calcs.json), so a current limit alone cannot enforce 0.4 N: the coupling is the physical backstop; 0.5-0.8 N PROPOSED (DEC-099) | DEC-099; any test of the five-bar with a hand |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-BB06).
<!-- AC-TABLE:EXP-BB06:END -->

- **Decision rule.** The cap or the release fails: it is fixed before anything else runs. Endpoint error above 50 µm: 16-bit encoders or a camera-referenced loop. Stiffness below 4 N/mm: stiffer links. A continuous force below 0.40 N: the model's force disk is refitted before EXP-BB07 (the capstans' 80 % efficiency is an ASSUMPTION).

### EXP-BB07: Does the five-bar write accepted words on paper, and stop when a hand resists?

- **Purpose and gates.** The grounded results are SIM only. Replay the 20 accepted 'se' suffixes on paper with the passive pen: first with no resisting spring, then against 200 and 500 N/m spring hands, measuring the ink laid after a refusal. Gates DEC-071 (the grounded route for whole words), the lift and refusal design, and DEC-099. No requirement.
- **Bench only (DEC-099).** As EXP-BB06: a passive 24 mm dummy pen, spring hand simulants, the current limit, the 0.4 N cap, the breakaway coupling, guards and the latching emergency stop. Accepted-word results are claimed only from this measured replay, not from the rigid model.
- **Predictions (SIM; `results/improvement/mechanics/grounded_batch.json`, `grounded_derivative_check.json`).** In the rigid model with ideal current loops, 20 of 20 suffixes met the grounded gate with no resisting hand. Against a 200 or 500 N/m grip 0 of 20 did, and the 200 ms retraction left erroneous ink. None of the 20 met both the 2 m/s² and the 300 m/s³ smoothness limits, which are the planner's ASSUMPTIONS.
- **Set-up.** The five-bar after EXP-BB06, with feedforward plus feedback; the micro-servo pen lift; paper under the writing patch; R3 scans; the springs on a linear guide; the camera, and the output encoders at 1 kHz.
- **Procedure.**
  1. The 20 accepted suffixes (`results/improvement/writing/grounded_accepted`) on paper with no spring. The scans are judged by the grounded gate: no refusal or stop hit; at least 98 % of the requested ink laid; at most 0.10 mm RMS during requested ink; at most 0.02 mm of ink path in air transfers (AC-BB07-01).
  2. The same references against the 200 and 500 N/m springs: the ink laid after the refusal command, from the scans (AC-BB07-02).
  3. The peak tip acceleration and jerk of every suffix, from the encoders and the camera, with the share within 2 m/s² and 300 m/s³ (AC-BB07-03).
- **Measurands.** Suffixes that meet the gate; ink after a refusal; acceleration and jerk.

<!-- AC-TABLE:EXP-BB07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB07-01 | — | The 20 accepted 'se' suffixes of results/improvement/writing/grounded_accepted written on paper by the five-bar with a passive 24 mm dummy pen, no resisting spring, feedforward plus feedback: suffixes meeting the grounded gate from scans (no refusal or stop hit; ≥ 98 % requested-ink coverage; ≤ 0.10 mm RMS during requested ink; ≤ 0.02 mm ink path in air transfer) | ≥ 18 | hypothesis | SIM 20 of 20 in the rigid, ideal-current-loop model (results/improvement/mechanics/grounded_batch.json); 18 PROPOSED to allow two scan or registration failures | DEC-071 (the grounded route for whole words) |
| AC-BB07-02 | — | The same references with 200 and 500 N/m spring hands: ink path laid after the refusal command (scans), largest over the suffixes | ≤ 0.5 mm | hypothesis | PROPOSED; SIM: 0 of 20 completions and partial erroneous ink during the 200 ms retraction (the pass's unmet interaction target) | DEC-071; the lift and refusal design; DEC-099 |
| AC-BB07-03 | — | Peak tip acceleration and sampled jerk of every suffix from the output encoders (1 kHz) and the camera, with the fraction within 2 m/s^2 and 300 m/s^3 | reported for every suffix | derived | SIM: none of the 20 unloaded suffixes met both limits (grounded_derivative_check.json); the limits are the planner's ASSUMPTIONS | the smoothness claim of any grounded writing |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-BB07).
<!-- AC-TABLE:EXP-BB07:END -->

- **Decision rule.** Fewer than 18 of 20: the moving-paper platen (study P) is weighed as the alternative route for whole words (DEC-071). More than 0.5 mm of ink after a refusal: a faster, positively sensed lift. The acceleration and jerk decide whether any grounded writing may be called smooth.

### EXP-BB08: Does the page estimate re-anchor honestly after an outage?

- **Purpose and gates.** EXP-T04 judges the lift cut-off height and dropouts, not absolute re-anchoring. Check that through lifts, occlusions and glossy strips the page estimate never keeps an absolute position without re-anchoring, and that re-anchoring restores it. Gates DEC-070 (the causal page model), DEC-071 (page registration for accepted writing) and the supervisor's anchor check. REQ-RVJ-C05 and REQ-CAP-003.
- **Predictions.** The causal page model (version 2, DEC-070) keeps lost motion lost and marks the absolute anchor invalid until it is restored. The old model recovered 2.02 mm from the hidden truth over 100 invalid reports at 20 mm/s (SIM, `docs/integration_improvement_audit.md`). There is no prediction for re-anchoring by fiducials or coded paper.
- **Set-up.** R10 on R9's frame (the Mode A sled with the chosen die) and the camera with a dot grid as truth; lifts beyond the sensor's cut-off, occluders and glossy strips; printed fiducials or coded paper for re-anchoring.
- **Procedure.**
  1. At least 100 outages (lifts, occlusions, glossy strips): whether the estimate keeps an absolute position without re-anchoring (AC-BB08-01).
  2. At least 100 lifts of 2 mm for 0.5 s with the pen displaced by up to 5 mm: the absolute position after re-anchoring with the method under test (AC-BB08-02).
  3. For each outage, the lost relative motion, its duration and its cause (AC-BB08-03).
- **Measurands.** Silent recoveries; the re-anchored error; the lost motion.

<!-- AC-TABLE:EXP-BB08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB08-01 | — | During lifts beyond the sensor's cut-off, occlusions and glossy strips: outages in which the page estimate keeps an absolute position without re-anchoring (silent recoveries), over ≥ 100 outages | = 0 | derived | the causal page model v2 (DEC-070): lost motion stays lost and the absolute anchor is invalid until restored; the old model recovered 2.02 mm from the hidden truth (docs/integration_improvement_audit.md) | DEC-070; the accepted-writing supervisor's anchor check |
| AC-BB08-02 | REQ-RVJ-C05 | Absolute page position after re-anchoring with the method under test (printed fiducials seen by the camera, or coded paper), 95th percentile over ≥ 100 lifts of 2 mm and 0.5 s with the pen displaced up to 5 mm | ≤ 0.1 mm | derived | REQ-RVJ-C05's 0.1 mm budget applied to the re-anchored position | DEC-071 (page registration for accepted writing); REQ-CAP-003 |
| AC-BB08-03 | — | Lost relative motion during each outage, with its duration and cause | reported for every outage | derived | report; SIM example: 2.02 mm lost over 100 invalid reports at 20 mm/s (docs/integration_improvement_audit.md) | the supervisor's outage handling |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-BB08).
<!-- AC-TABLE:EXP-BB08:END -->

- **Decision rule.** Any silent recovery: the page model or the supervisor is fixed, and no accepted writing continues across an outage without a verified anchor. A re-anchored error above 0.1 mm: another re-anchoring method.

### EXP-BB09: How late is the contact decision, and how fast does a lift stop the ink?

- **Purpose and gates.** AC-B05-10 judges the axial-force noise, not the delay of the contact decision. Measure that delay against the plate's normal force, the rate of false contacts and lifts, and the time a voice-coil lift takes to stop the ink. Gates DEC-070 (the delayed contact channel of the causal models; study X's reruns) and the lift a refusal needs (DEC-071). REQ-CTRL-003.
- **Predictions.** The replay studies assumed lift and lower delays of 20–200 ms (`ai3/run_completion_robustness.py`). For Rev K's follower lift the ink stops after 43–72 ms (CALC, DEC-064). There is no prediction for the contact channel.
- **Set-up.** R9, with the in-line axial cell and the slide Hall making the pen-side contact decision, and the plate as truth; the six papers; R9's voice-coil lift (the refill retracted 0.5 mm) for step 3; R3 scans.
- **Procedure.**
  1. At least 200 touchdowns and lifts at 35, 50 and 75°: the delay from the plate's normal force crossing 20 mN to the contact decision (AC-BB09-01).
  2. Continuous writing on the six papers: false contact or lift decisions per minute, against the plate (AC-BB09-02).
  3. Lift commands at 30 mm/s: the time from the command until the ink stops, and the ink's resumption after the lower command, from the scans and the plate (AC-BB09-03).
- **Measurands.** The contact delay; false decisions; the lift time.

<!-- AC-TABLE:EXP-BB09:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-BB09-01 | REQ-CTRL-003 | Delay from the plate's normal force crossing 20 mN (truth) to the pen-side contact decision (in-line axial cell; slide Hall), touchdowns and lifts, 99th percentile over ≥ 200 events at 35, 50 and 75° | ≤ 5 ms | derived | REQ-CTRL-003's 5 ms delay budget applied to the contact channel; the replay studies assumed 20-200 ms lift/lower delays (ai3/run_completion_robustness.py) | DEC-070 (the contact model); ink gating by the supervisor |
| AC-BB09-02 | — | False contact or lift decisions per minute of continuous writing on the six papers (plate truth) | ≤ 0.1 | hypothesis | PROPOSED | the contact threshold and its hysteresis |
| AC-BB09-03 | — | Command-to-ink-stop time of R9's voice-coil lift (refill retracted 0.5 mm) at 30 mm/s, and ink resumption after the lower command, from scans and the plate | ≤ 50 ms | hypothesis | PROPOSED; CALC for Rev K's follower lift: ink stops after 43-72 ms (DEC-064); the grounded study's 200 ms retraction left erroneous ink | the lift a refusal needs (DEC-071) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-BB09).
<!-- AC-TABLE:EXP-BB09:END -->

- **Decision rule.** A delay above 5 ms, or more false decisions: the contact channel's threshold and filtering are changed. The measured delay goes into the causal models either way (DEC-070). A lift slower than 50 ms: a faster lift.
