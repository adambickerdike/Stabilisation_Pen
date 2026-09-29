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
- §42 Rev J inertial end-cap (DEC-038): EXP-K01, K02, K04, K06, K07, K08 (K03 and K05 are in `human_study_plan.md` §17)
- §43 Rev J nose v2 and autowrite (DEC-036, DEC-039, DEC-041): EXP-N01…N08 (N09 and N10 are in `human_study_plan.md` §18)
- §44 Simulator v2 validation (DEC-040): EXP-V01…V06, with the Rev H refill front stop (REQ-RVH-008) in EXP-V02
- §45 Rev J control stack (DEC-042): EXP-L01, L02, L04, L05 (L03, L06, L07 and L08 are in `human_study_plan.md` §19)

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
| **R8 fatigue rig** | M02, B10, Q04 | Resonant or shaker-driven flexure fatigue stations (100–300 Hz). Amplitude control by laser displacement (≤ 0.5 µm). Miniature strain gauges on sacrificial coupons. Resonance tracking for crack detection. Stereo microscope (≥ 50×). Access to SEM for fractography. Axial load frame with 0–10 N load cell (±0.1 % FS). |

### 0.10 Laboratory safety

- Beryllium–copper is formed, etched and cut under beryllium dust controls (AMF notes §2.2).
- Li-ion cells are charged and cycled in fire-safe containers. Abuse tests (short circuit, crush, over-charge) are done only at an accredited laboratory (EXP-P02).
- Laser sensors are class 2 or 3R, with signage.
- Piezo drives (EXP-Q04…Q08) run at up to 60 V, and the DRV2700 boost can reach 105 V. Terminals are shrouded, and multilayer plates are shorted before handling because they hold charge.
- **No participant touches a powered prototype before gate G-S** (`prototype_stages.md`).

### 0.11 Pencil-class protocols (EXP-Q01…Q08)

The pencil-class concept (Rev P0, DEC-019; `docs/pencil_concept.md`) has its own parameter overlay and model. For EXP-Q01…Q08:

- **Predictions** come from `config/pencil.yaml` (P0.1.2, an overlay on `config/parameters.yaml` v0.4.4), from `analysis/pencil_mechanisms.py` (`results/pencil/mechanisms.json`, CALCULATION) and from the pencil model P1 (`sim/pencil`; `results/pencil/sim_metrics.json` and `touchdown_tails.json`, SIMULATION). They are regenerated with the as-built parameters and frozen as in §0.2.
- **Forces** follow `docs/pencil_mechanisms.md` §2. F_c is the axial nib-spring force. The nib normal force is N_nib = F_c / (sin θ − μ cos β cos θ). The transverse load per stage axis in the worst stroke direction is F_c·cot(θ − atan μ). The **design load** is 0.170 N per axis at F_c 0.15 N, θ 50° and μ 0.15. Strokes and loads are referred to the nib (lever 1.363). The usable correction is ±0.30 mm (servo soft limit); the stops are at ±0.40 mm.
- **Rigs** are those of §0.9: R1 for Q01 and Q02; R7 for Q03 and Q05; R4, R5 and R8 for Q04; R2 and R3 for Q06 and Q08; R5 and R2 for Q07.
- **What does not carry over from Rev A.** The pencil stage has no coil, so the copper-loss, coil-temperature and current-clamp criteria do not apply to it. Drive power and runtime are covered by EXP-Q03, EXP-Q05 and AC-P01-05.
- **People.** No pencil build is used with participants before it passes a safety gate equivalent to G-S. `prototype_stages.md` defines G-S for Rev A builds only; the pencil set is an open item (`README.md` §7).

---

## 1. Experiment index

The "Gates" column lists decisions (DEC-…, `docs/decisions.md`), requirements (REQ-…, `docs/requirements.csv`) and stage gates (G-…, `prototype_stages.md`).

| ID | Title | Stage | Rig | Gates | Depends on |
|---|---|---|---|---|---|
| EXP-B01 | Refill drag and contact-reaction map (includes refill metrology) | A | R1, R3 | DEC-003, DEC-008, DEC-023, REQ-ACT-001, REQ-MECH-008, actuator freeze | R1 qualification |
| EXP-B02 | Friction vs speed; LuGre identification | A | R1 | contact model P-9, DEC-011, DEC-023 | B01 |
| EXP-B03 | Actuator coupons: force–current–position map, R, L, thermal, gap | A | R4 | DEC-003, DEC-007 rev., DEC-012, DEC-023, REQ-ACT-001/002, REQ-SNS-004, actuator freeze | coupons built |
| EXP-B04 | Hall and optical calibration against a motion stage; page workspace | A (rig), B (pen) | R5 | REQ-MECH-001, REQ-SNS-004, CAL_HALL | B03, B05 |
| EXP-B05 | Stage FRF, stiffness, stops, axial path, contact chatter | A, B | R2, R5 | REQ-ACT-003, REQ-CTRL-002, REQ-MECH-002/003/004, REQ-SNS-005, DEC-011, DEC-023 | B03, B04 |
| EXP-B06 | Grip impedance incl. normal direction; γ identification (participants) | A (bench), B (in-pen γ) | R6 | DEC-006, REQ-CTRL-006, hand model P-13 | ethics approval |
| EXP-B07 | Coil and skin temperature | A (coupon), B, C (pen) | R4, R7 | REQ-THM-001/002, REQ-ACT-002, DEC-008, G-S | B03 |
| EXP-B08 | Ink tolerance to modulated normal force | A | R1, R3 | REQ-MECH-005, DEC-004, DEC-006 | B01 |
| EXP-B09 | Bench cancellation with injected disturbance and µm ink metrology | A (rig), B (pen) | R2, R3 | G-B, G-C, REQ-VAL-001, REQ-CTRL-003/005/006/007/008, DEC-009, DEC-023 | B01, B02, B03, B04, B05, B06, B08, S01, F01 |
| EXP-B10 | Durability: flexure cycling, refill exchange, drop | B, C | R8, R5 | REQ-MECH-002/004/006/008, G-C | M02 |
| EXP-S01 | Optical-sensor latency and accuracy | A, B | R5 | DEC-005, DEC-021, REQ-SNS-001/002, REQ-CTRL-003, REQ-PNC-004 | — |
| EXP-S02 | Capture and fusion accuracy against references | B, C | R2, R3 | REQ-CAP-001/003, COR-16 | S01, B04 |
| EXP-F01 | Hardware fault injection | A (board), B, C | R7, R2 | REQ-SAF-001/002/004, REQ-PWR-003, DEC-015, G-S | bring-up steps 1–10 |
| EXP-F02 | Firmware robustness | B, C | R7 | REQ-CTRL-001/004, REQ-SAF-001/003/004, REQ-SNS-003, DEC-010/015/016, G-S | F01 |
| EXP-M02 | Flexure fatigue coupons | A | R8 | REQ-MECH-006/007, DEC-007 | coupons |
| EXP-M03 | Mass, centre of mass and balance of built pens | B, C, D | — | REQ-FORM-001…004, REQ-PNC-001 | pens built |
| EXP-P01 | Power and runtime | C (and D) | R7, R2 | REQ-PWR-001, REQ-ACT-002, REQ-PNC-005, DEC-008 | P02 |
| EXP-P02 | Charging and battery safety pre-compliance | C | R7 | REQ-PWR-002/003, REQ-THM-001, G-C | cell samples |
| EXP-E01 | Estimator bake-off on recorded writing at matched false correction | offline, after H01 | compute | DEC-009, DEC-016, REQ-ML-001, REQ-CTRL-007, REQ-DATA-001 | H01 |
| EXP-E02 | Closed-loop replay of recorded tremor on the B09 rig | B | R2, R7 | REQ-ML-002, REQ-CTRL-005, REQ-SAF-003, DEC-016 | E01, B09 |
| EXP-C01 | Recognition accuracy (CER/WER, writer-disjoint) and search | C | compute | DEC-013, REQ-APP-001, REQ-DATA-001 | C02; H01/H06 ink |
| EXP-C02 | Capture fidelity end to end | C | R7 | REQ-CAP-001/002, DEC-017, G-C | F02 |
| EXP-A01 | AI grounding audit | C | compute + raters | REQ-APP-002, REQ-USR-003, DEC-017 | C01 |
| EXP-A03 | Autocorrect on real notes | C | compute + app | REQ-PNC-008, DEC-020 | C01; consented notes |
| EXP-Q01 | Skid friction (pencil) | A | R1 | REQ-PNC-002, DEC-019, skid material for H03 | R1 qualification |
| EXP-Q02 | Low-force ink line quality; sets the nib-spring force F_c | A | R1, R3 | REQ-PNC-002, DEC-019 (stage load) | B01 Part 4 method; Q01 (Part B) |
| EXP-Q03 | Pencil cell pulse discharge | A | R7 | REQ-PNC-005, cell choice | cell samples; Q05 load profiles |
| EXP-Q04 | Bender characterisation and strength | A | R4, R5, R8 | REQ-PNC-003, DEC-019 | custom plates |
| EXP-Q05 | Piezo driver efficiency and quiescent power | A | R7 | REQ-PNC-005, driver choice | Q04 |
| EXP-Q06 | Loaded 1-axis rig: PL128.10, D1 refill, skid nose | A | R2, R3 | REQ-PNC-002/003, DEC-019 | Q01, Q02, Q04 |
| EXP-Q07 | Two-axis Q stage in a 7.9 mm bore | A | R5, R2 | REQ-PNC-003, DEC-019, Rev P1 build | Q04, Q05, Q06 |
| EXP-Q08 | Touchdown and lift tails; tilt-adaptive front stop | A | R2, R3 | REQ-PNC-006, DEC-022 | Q06 |
| EXP-I01 | Grip compliance split: translation vs tilt of a pen grasp (participants) | A | R6 + second stinger | DEC-024, hand-pen model H1 | B06 session, ethics |
| EXP-I04 | Nib stage plus an inertial helper on the loaded rig (only if EXP-I01 finds r_rot ≥ 0.6); superseded by EXP-I06 for Rev H | A | R2, R3 | DEC-024 | I01, Q06 |
| EXP-I05 | Rev H active nose on the bench: force constant, travel, bandwidth, power, writing-force change | A | R2 with a 2-axis shaker, R3 | REQ-RVH-001…005, DEC-032 | nose prototype |
| EXP-I06 | Rev H rear inertial module on a hand simulant with the nose on | A | EXP-I05 rig + EXP-I01 compliance | DEC-033 | I01, I05 |
| EXP-I07 | Rev H tracker on recorded tremor writing (offline replay) | C | compute | REQ-RVH-006, DEC-028, DEC-032 | E01 recordings |
| EXP-G01…G06 | Guidance board: force map, stage and latency, localisation, noise and heat, hand simulant, safety | A | board prototype, 3-axis load cell | REQ-RVH-007, DEC-031 | board prototype |
| EXP-D01 | Heel drive: tyre–paper friction on six papers | A | R1, climate box | REQ-DRV-004, DEC-037 | R1 qualification |
| EXP-D02 | Heel drive: tyre lateral stiffness and relaxation length | A | micrometre stage, 3-axis force sensor | REQ-DRV-005 (slip threshold), DEC-037 | D01 |
| EXP-D03 | Heel drive: holding the sheet | A | load cell, 3 desk types | REQ-DRV-011 | heel pod |
| EXP-D04 | Heel drive: geometry, roll, preload and steering | A | R5 (tilt–roll fixture), load cell | REQ-DRV-004/006/007/008, DEC-036/037 (front end) | printed heel, 0620 B motors |
| EXP-D05 | Heel drive: slip detection | A | linear stage, page-sensor board, encoder, high-speed camera | REQ-DRV-005, DEC-037 | D01, D02 |
| EXP-D06 | Heel drive: noise, heat, power and runtime | A | R7, sound level meter | REQ-DRV-009/010, REQ-THM-001 | D04; N04 and N08 power logs |
| EXP-D07 | Heel drive: force cap, stall and lift safety (gate before D08, D09, D11) | A | 3-axis load cell, R7 | REQ-DRV-001/002/013, DEC-037 | D04, D05 |
| EXP-D10 | Heel drive: ink smear and wheel track | A | R3, microscope camera | REQ-DRV-012 | D01 |
| EXP-D12 | Heel drive: durability, cleaning and replacement | A | rolling rig, R1 | REQ-DRV-012 | D01 |
| EXP-D13 | Driven-ball fallback: roller drag and wear | A | bench ball drive, force sensor | DEC-037 (ball as the bench alternative) | rollers made |
| EXP-K01 | End-cap: reaction-mass actuator against its model; envelope, power, permeability | A | R4 (6-axis F/T) | REQ-EC-001/008/009, DEC-038 | end-cap prototype |
| EXP-K02 | End-cap: tremor on top of the nose on a hand–pen rig (extends I06) | A | EXP-I06 rig, R3 | REQ-EC-002/003, DEC-038 | K01; I01 or K08 |
| EXP-K04 | End-cap: can inertia steer the ink? (rig, then 6 healthy writers) | A | EXP-K02 rig | REQ-EC-004, DEC-038 | K02; K06 for a rotor |
| EXP-K06 | End-cap rotor safety (only if a rotor is kept) | A | containment enclosure, drop rig, sound level meter | REQ-EC-007, DEC-038 | CMG research module |
| EXP-K07 | Does spin itself steady the pen? | A | EXP-K02 rig | DEC-038 | K02 rig, rotor end-cap |
| EXP-K08 | Grip split with the end-cap fitted (participants) | A | R6 + second stinger | DEC-038 | I01 method; ethics |
| EXP-N01 | Nose v2 magnetics coupons, and Rev H's force constant | A | R4 | REQ-RVJ-N02, REQ-RVH-003, DEC-036, DEC-041 | coupons built |
| EXP-N02 | Nose v2: travel and front-end closure over 35–75° | A | R5 (tilt jig), side camera | REQ-RVJ-N01, DEC-036 | nose prototype |
| EXP-N03 | Nose v2: servo bandwidth and parasitic modes | A | R5, laser vibrometer | REQ-RVJ-N02, DEC-036 | N01, N02 |
| EXP-N04 | Nose v2: heat at the autowrite duty | A | R4 instruments, IR camera | REQ-RVJ-N03, DEC-036 | N01, N03 |
| EXP-N05 | Pen lift; strokes kept separate at 50–70° | A | R7, high-speed camera, writing robot | REQ-RVJ-N04, DEC-036, DEC-041 | pen-lift module |
| EXP-N06 | Refill force element fatigue | A | R8 | REQ-RVJ-N05, DEC-036, DEC-041 | candidate springs |
| EXP-N07 | Page sensor under the pen | A | R5 motion stage | REQ-RVJ-N06, DEC-036, DEC-037 (slip) | sensor board |
| EXP-N08 | Autowrite on the bench, with the SIM gate | A | R2, R3 | REQ-RVJ-N08, DEC-039 | N02…N07 |
| EXP-V01 | Simulator v2: paper contact of the Rev H front end | A | R1 | DEC-040 | B02, Q01 methods |
| EXP-V02 | Simulator v2: identify the assembled pen; refill front stop | A | R4, R5, R7 | DEC-040, REQ-RVH-008, DEC-041 | I05 build |
| EXP-V03 | Simulator v2: real writing and tremor at the pen (inside EXP-H01) | offline, after H01 | compute | DEC-040 (writer refit) | H01 recordings |
| EXP-V04 | Simulator v2: pen-grasp impedance while writing (participants) | A | R6 | DEC-040 | I01 or B06 sessions; ethics |
| EXP-V05 | Simulator v2: device effect on a bench against the frozen model | A | R2, R3 | DEC-040, REQ-SIM-001…005 | V01, V02, V04; frozen firmware |
| EXP-V06 | Simulator v2: population prediction against people | offline, after a human study | compute | DEC-040 | V05; W02 or D09 data |
| EXP-L01 | Control stack: the tremor-line gate on real tremor-free writing; causality of the stack | offline, after H01; then A | compute; bench pen | REQ-CTRL-009/010, DEC-042 | H01 recordings |
| EXP-L02 | Control stack: gated tracker against the Rev H tracker on real writing and on the bench | offline, after H01; then A | compute; R2 (EXP-I05 tremor rig), R3 | REQ-CTRL-011, DEC-042 | L01 |
| EXP-L04 | Control stack: learned estimator against REQ-ML-001 on real data; MCU timing; shadow mode | offline, after H01; then A | compute; R7 | REQ-ML-001, REQ-ML-003, DEC-042 | H01 recordings; E01 protocol |
| EXP-L05 | Control stack: RL arbiter in the sim2 closed loop, then on the bench | offline; then A | compute (sim2); EXP-V05 rig | REQ-ML-004, DEC-042 | V05 (REQ-SIM-005) |
| EXP-H01…H06, A02, I02, I03, W01…W05, G07, D08, D09, D11, K03, K05, N09, N10, L03, L06, L07, L08 | Human-participant studies | see `human_study_plan.md` | — | REQ-USR-\*, REQ-VAL-002, REQ-PNC-007, REQ-RVH-\*, REQ-DRV-002/003, REQ-EC-002/003/005/006, REQ-RVJ-N07, REQ-CTRL-012/013, REQ-APP-003/004, DEC-002/008/009/016/020/024/031/035…039/042/043 | ethics |

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
4. Calibrate the F/T sensor in situ at the start of each session: dead weights 0.2–4 N applied along the pen axis and perpendicular to it, **at every altitude used in the session** (35–80° here; 45° and 60° in EXP-B02). Fit the per-axis gains and the cross-axis terms to ±0.2 %.
   - Why: with the protocol-class ±2 % gains, part of the normal force appears on the friction axes. In twin experiments the correct friction model's held-out error reached 0.24–0.45 of μ_k·N for inks with μ_k 0.065–0.035 ([`sim_to_real.md`](sim_to_real.md) §6 item 3; SIMULATION).
   - If R1 has its own tangential load cell, friction may be analysed from it instead.

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

- **Validates** P-9 against the physics.md acceptance (fit R² > 0.9, applied after per-record mean removal), together with two model-form tests that R² misses (AC-B02-04, AC-B02-05).
- **Supplies** the simulator's contact model before any bench–simulation comparison in EXP-B09.
- **Gates** DEC-011 (revisit trigger: "Bench servo tests with real paper stacks").

Friction is the dominant parameter for estimator performance in the Monte Carlo (`results/sim/mc_sensitivity.json`; `docs/sim_report.md` §3), so this experiment carries more weight than its size suggests.

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

### Hypotheses

- At least one candidate meets REQ-SNS-001 on matte paper at 35–75° (AC-S01-01…03).
- With 3 modules at 120°, ≥ 99 % of samples at any roll have a valid module (AC-S01-04).
- Per-window error on paper is no worse than DeltaPen's median on a tablet (AC-S01-06).
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
- **Pencil builds** (Rev P1 onwards, DEC-019) are weighed and balanced with the same procedure against REQ-PNC-001: diameter ≤ 9.0 mm, length ≤ 170 mm, mass ≤ 24 g including wiring and margin (AC-M03-07). REQ-FORM-001…004 are Rev A requirements and do not apply to them. CAD P0.1.2 predicts 12.2 g before wiring, adhesive and margin, with the centre of mass 88 mm from the nib (`results/cad/pencil_revPQ_summary.json`).

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

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (7 rows for EXP-M03).
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

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-P01).
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
6. **Clean copy (DEC-035).** For notes of writers with 1–2 mm tremor and for tremor-free notes of healthy controls, make the app's clean copy from the recorded tip path (`aiprior/cleancopy.py`, settings frozen). Blinded readers transcribe the clean copy and, in a separate session, the raw ink of other notes. Log whether a tremor line was detected, and every letter read correctly in the raw ink but wrongly in the clean copy. The clean copy is a derived layer shown next to the untouched ink (DEC-017).

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
| AC-A03-04 | — | Clean copy (DEC-035) of recorded notes of ET writers with 1-2 mm tremor: words correctly transcribed by blinded readers from the clean copy (readers never see the raw ink of the same note first); point estimate, writer bootstrap | ≥ 90 % | hypothesis | DEC-035; prediction 97 % of words read by the app's recogniser at 1-2 mm and 6-10 Hz, against 30-59 % in the ink (results/aiprior/aiprior.json; SIMULATION on synthetic writers); 90 % engineering judgement for human readers and real tremor | DEC-035 |
| AC-A03-05 | — | Clean copy does no harm: letters read correctly in the raw ink but wrongly in the clean copy (blinded readers, per 1000 letters), AND the clean copy of tremor-free notes from healthy controls equals the recording (no tremor line detected) in at least 95 % of notes (both) | both met (1 per 1000; 95 %) | hypothesis | DEC-035; prediction: no tremor line detected on tremor-free writing, which is left unchanged (28 µm = the recorder's noise) (results/aiprior/aiprior.json; SIMULATION); thresholds engineering judgement | DEC-035 |

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

EXP-B06 (grip impedance, §7) and EXP-I01 (grip compliance split, §35) also involve participants and are covered by the same ethics approval. So do EXP-K04 (6 healthy writers) and EXP-K08 (§42), and EXP-V03 (inside EXP-H01 sessions) and EXP-V04 (§44). EXP-L01, L02 and L04 (§45) re-use EXP-H01 recordings under the consents of `human_study_plan.md` §3.3.

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

DEC-037 adds a paper-grounded drive at the heel. A 2 mm wheel with an O-ring tyre sits in a slot at the bottom of a larger skid ring. It is steered about the paper normal through its contact point (the cobot principle, LIT HAP-60), and a 2:1 bevel drives it. Two Faulhaber 0620 B motors in the handle turn two 0.8 mm shafts that reach a sprung heel pod (0.55 N preload).
- **Modes.** Steer-only by default: the wheel cannot move the pen. The drive motor pushes only in an explicit lead-through or autowrite mode (DEC-039), and it never starts a stroke.
- **Supervisor.** Commands are capped at min(0.5 N, 0.8 × μ̂ × wheel load). A lateral release turns the wheel toward a push above the cap. The page sensor detects slip.
- **What it gates.** DEC-037 is adopted only after EXP-D01, D05, D07 and D08. EXP-D07 is the safety gate before any participant uses the drive. Requirements: REQ-DRV-001…013.
- **Predictions** come from `docs/grounded_drive.md` and `results/drive/` (model HW1-D; test writers 0–5, seeds 200–203; tyre friction drawn from 0.6–1.2 per case; CALC and SIM). The tyre friction, the tyre stiffness, the steering servo and the relaxed-writer model are ASSUMPTIONS.
- **Front end.** The heel was sized on the Rev H front end (contact radius 6.75 → 8.75 mm, sleeve Ø15.0 → Ø18.3 mm at the heel). The nose v2 front end (DEC-036) already has a 10.0 mm skid ring and a Ø21.5 mm sleeve front. Re-run `drive/geometry.py` with the nose v2 envelope before the heel is built (AC-D04-04).
- Work with people (EXP-D08, D09, D11) is in [`human_study_plan.md`](human_study_plan.md) §16.

### EXP-D01: Tyre–paper friction on six papers

- **Purpose and gates.** Replace the assumed traction range (0.6–1.2) with measurements, and pick the tyre compound. Gates REQ-DRV-004 and DEC-037.
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
  - Contact up to ±20° of roll with 0.54 mm of spring travel (CALC).
  - Steering about 1570 rad/s no-load (0620 B, crown 2:1, 3.7 V; CALC). The SIM used a 40 Hz, 500 rad/s servo (ASSUMPTION). Letter headings turn at up to 71 rad/s (p90) and 283 rad/s (p99) (CALC).
  - Heel contact radius 8.75 mm and sleeve Ø18.3 mm on the Rev H front end (CALC, PROPOSED DESIGN). Not yet sized for nose v2.
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
| AC-D04-01 | REQ-DRV-007 | Wheel contact with the paper (wheel load above 0.02 N) in the tilt-roll fixture at θ 35/50/75° and pen roll -20 to +20° in 5° steps | contact at every setting | requirement | REQ-DRV-007; prediction contact to ±20° of roll with 0.54 mm of spring travel (CALC, drive/geometry.py) | DEC-037 |
| AC-D04-02 | REQ-DRV-006 | Steering servo closed-loop bandwidth (-3 dB, chirps, Hall angle sensor at the fork) and rate limit (step responses) at the wheel | ≥ 40 Hz and 300 rad/s | requirement | REQ-DRV-006; prediction about 1570 rad/s no-load (0620 B + crown 2:1 at 3.7 V; CALC); SIM assumed 40 Hz and 500 rad/s; letter headings turn at up to 71 rad/s (p90) and 283 rad/s (p99) (CALC) | DEC-037 |
| AC-D04-03 | REQ-DRV-004 | Heel pod preload: wheel load at the working deflection (load cell under the paper) at θ 35/50/75° | within 0.55 N ± 10 % | requirement | REQ-DRV-004; design 0.55 N (continuous optimum 0.57 N, CALC drive/design_opt.py) | DEC-037 |
| AC-D04-04 | REQ-DRV-008 | Front end with the heel drive (printed heel and CAD review): heel contact radius and front sleeve at the heel on the Rev H front end; on the front end actually built (nose v2, DEC-036): sleeve diameter where held; opening on top for the ink (all) | all met (Rev H front end: ≤ 9.0 mm and ≤ 18.5 mm at the heel; any front end: ≤ 24 mm where held; open 120° on top) | requirement | REQ-DRV-008; prediction 8.75 mm and 18.3 mm on the Rev H front end (CALC, PROPOSED DESIGN); not yet sized for nose v2, whose skid ring alone has a 10.0 mm contact radius and a 21.5 mm sleeve front (docs/nose_v2.md s4.4) -> re-run drive/geometry.py before the build | DEC-037; DEC-036 (front end holds the heel drive within 24 mm) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-D04).
<!-- AC-TABLE:EXP-D04:END -->

- **Decision rule.** Contact lost within ±20°: more spring travel. Steering too slow: change the ratio or the motor. Heel or sleeve too large for the chosen front end: re-run `drive/geometry.py`. If the heel drive cannot fit the nose v2 front end within Ø24 mm, revisit DEC-036 and DEC-037.

### EXP-D05: Slip detection

- **Purpose and gates.** Test the slip rule: page sensor against wheel odometry. Gates REQ-DRV-005 and DEC-037.
- **Predictions.** In SIM the tyre truly slid for less than 0.1 % of contact time. Yet the simple rule raised 3–40 false flags per sentence, and each flag lowers the force cap for about 2 s (SIM). A model-based detector that uses the tyre-deflection estimate is needed (`docs/grounded_drive.md` §10).
- **Set-up.** The heel pod on a linear stage over the six EXP-D01 papers. The page-sensor board and the wheel encoder logged at 1 kHz. A high-speed camera as the slip reference.
- **Procedure.**
  1. Impose gross slips by lowering the preload or raising the command: at least 29 per paper (§0.7).
  2. Replay recorded writing motion without slip, 10 min per paper, to count false flags.
  3. Run the simple rule and the model-based detector on the same records.
- **Measurands.** Detection latency; false flags per 10 s of normal writing motion.

<!-- AC-TABLE:EXP-D05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D05-01 | REQ-DRV-005 | Time from the start of an imposed gross wheel slip (lowered preload or raised command, six papers; high-speed camera reference) to the slip flag and the lowered command; every imposed slip (≥ 29 per paper) | ≤ 50 ms | requirement | REQ-DRV-005; paper sensor against wheel odometry at 1 kHz (MFR AMF-109 class sensor); detection rule ASSUMPTION (docs/grounded_drive.md s2.2) | DEC-037 (revisit if slip detection is unreliable) |
| AC-D05-02 | REQ-DRV-005 | False slip flags per 10 s of replayed normal writing motion without true sliding (camera reference), six papers; simple rule and model-based detector reported separately | < 1 per 10 s | requirement | REQ-DRV-005; SIM: true sliding < 0.1 % of contact time, yet the simple rule raised 3-40 false flags per sentence (docs/grounded_drive.md s5.1) -> the simple rule is predicted to FAIL; a model-based detector using the tyre deflection is needed | DEC-037 (revisit if slip detection is unreliable) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-D05).
<!-- AC-TABLE:EXP-D05:END -->

- **Decision rule.** Keep the detector that passes. If neither passes, the traction estimate cannot be trusted: revisit DEC-037.

### EXP-D06: Noise, heat and power

- **Purpose and gates.** Check the power budget, heat and noise. Gates REQ-DRV-009, REQ-DRV-010 and REQ-THM-001 for the drive.
- **Predictions.**
  - Drive power 0–1 mW steer-only, 6 mW when guiding with a push, 84 mW while leading (SIM). Paper sensor 30–80 mW (CALC, MFR AMF-109). Drivers and Hall sensors 10–20 mW (ASSUMPTION).
  - Winding rise 5–11 K at 146 K/W (CALC).
  - 12–18 h of writing while guiding and 8–10 h while leading, on the Rev H base load of 0.08 W (CALC). With the nose v2 base load this is not yet shown (DEC-036: coil loss 0.16–0.18 W with 1 mm tremor).
  - Noise not modelled.
- **Set-up.** The bench drive in a handle. Recorded drive commands from the SIM tasks. A sound level meter at 30 cm in a quiet room (A-weighted). Thermocouples on the windings and on the sleeve. Supply current logging (R7).
- **Procedure.** Replay each mode (steer-only guidance, guidance with a push, lead-through, autowrite) for 30 min. Log power, winding and surface temperatures and sound level (background subtracted). Compute the runtime with the measured base load of the Rev J pen (EXP-N04 and EXP-N08 power logs).
- **Measurands.** Mean electrical power per mode; winding rise; surface temperature; dB(A); runtime.

<!-- AC-TABLE:EXP-D06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-D06-01 | REQ-DRV-009 | Mean electrical power of the heel drive (motors, drivers and paper sensor) while replaying the recorded SIM drive commands of each mode for 30 min (steer-only guidance, steered and driven guidance, lead-through, autowrite) | ≤ 0.15 W | requirement | REQ-DRV-009; prediction drive 0-1 mW steer-only, 6 mW guiding with a push, 84 mW leading (SIM); paper sensor 30-80 mW (CALC, MFR AMF-109); drivers and Hall sensors 10-20 mW (ASSUMPTION) | DEC-037 |
| AC-D06-02 | REQ-DRV-009 | Winding temperature rise of the two 0620 B motors (thermocouples) after 30 min of the lead-through replay | < 10 K | requirement | REQ-DRV-009; prediction 5-11 K at 0.10-0.15 N RMS with 146 K/W (MFR AMF-100 Rth x 1.5 enclosed, ASSUMPTION; CALC) -> marginal | DEC-037 |
| AC-D06-03 | REQ-THM-001 | Handle surface temperature over the motor pocket after 30 min of the lead-through replay, referred to 25 °C ambient; guarded acceptance | ≤ 41 °C | requirement | REQ-THM-001 design target (AMF-34, AMF-35); pass line of the drive study; the motors sit at z 50-70 mm, behind the finger pads at z 26-38 mm (docs/grounded_drive.md s4.4) | DEC-037; safety before EXP-D08 |
| AC-D06-04 | REQ-DRV-010 | A-weighted sound level of the heel drive at 30 cm in a quiet room while guiding (steer-only and steered and driven replays), background subtracted | ≤ 35 dB(A) | requirement | REQ-DRV-010 (ASSUMPTION threshold, quiet classroom); noise not modelled | DEC-037 |
| AC-D06-05 | REQ-DRV-009 | Writing time per charge with assistance on: 2.22 Wh usable (Rev H cell, MFR AMF-80) divided by the measured heel-drive power plus the measured base load of the Rev J pen it is fitted to (nose, electronics, pen lift; EXP-N04 and EXP-N08 power logs), steer-only guidance and leading | ≥ 8 h | requirement | REQ-DRV-009; prediction 12-18 h guiding and 8-10 h leading on the Rev H base load of 0.08 W (CALC, docs/grounded_drive.md s4.5) -> at risk with nose v2: its coil loss is 0.16-0.18 W with 1 mm tremor (DEC-036) and autowrite with 1 mm tremor alone gives 7.1 h (SIM, docs/nose_v2.md s5.3) | DEC-037; DEC-036; Rev J power budget |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (5 rows for EXP-D06).
<!-- AC-TABLE:EXP-D06:END -->

- **Decision rule.** Power over 0.15 W: review the page sensor and the drivers. Surface over 41 °C: move or derate the motors (guarded acceptance, §0.5). Noise over 35 dB(A): better gear finish or a speed limit. Runtime under 8 h: the lead balances the Rev J power budget (DEC-036, DEC-037).

### EXP-D07: Force cap, stall and lift safety

- **Purpose and gates.** Show that the drive never exceeds its caps and always lets go. Gates REQ-DRV-001, REQ-DRV-002, REQ-DRV-013 and DEC-037. **It is the safety gate before EXP-D08, D09 and D11.**
- **Predictions.**
  - Commands were capped in every SIM run.
  - The steer-only wheel's hold across its heading is a reaction, not a command: up to 0.66 N without the release. With the release the 95th percentile was 0.43–0.50 N and the maximum 0.49–0.56 N (tuning writers after the test, μ 1.2; SIM, `results/drive/release_tuning.json`).
  - Physics caps any force at the static traction, 0.36–0.73 N (CALC). The wheel turns at up to 1.6 m/s no-load, with at most 0.67 N of rim force (CALC).
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

DEC-038 fits a detachable rear end-cap to the first Rev J prototype. Four arc coils push a 30.4 g tungsten slug (non-magnetic grade) by ±4 mm in two axes, on two 5 Hz flexures. The end-cap is Ø26 × 24 mm, sits behind the cell (pen 175 mm) and weighs 43 g. The tracker's feed-forward drives it on top of the nose (gain 0.75).
- **Inertia steadies and cues; it does not write.** Cues are played only in pauses, and only after EXP-K05. No rotor goes in the product; a CMG end-cap stays a research module for torque-pulse cues.
- **What it gates.** DEC-038 is revisited if EXP-K02 gives less than 10 % further reduction at the measured grip split, or the fixed weight comes within 5 points; if EXP-K01 misses the force model by more than 20 %; if EXP-I01 or K08 find r_rot outside 0.3–0.7; if writers reject the back-heavy pen (EXP-K03). Requirements: REQ-EC-001…009.
- **Predictions** come from `docs/inertial_endcap.md` and `results/endcap/endcap_study.json` (H1 with the causal Rev H tracker; test seeds 200–203; grip splits r_rot 0.3 / 0.5 / 0.7; CALC and SIM). They were run on the **Rev H** pen and nose (75 g, Ø22 mm), not on nose v2 (DEC-036: 83.5 g, Ø24 mm).
- Work with people (EXP-K03, K05) is in [`human_study_plan.md`](human_study_plan.md) §17. EXP-K04 and EXP-K08 include participants; they are covered by the same ethics approval as EXP-B06 and EXP-I01.

### EXP-K01: Reaction-mass actuator against its model

- **Purpose and gates.** Check the actuator, the envelope, the power and the slug's material before any tremor test. Gates REQ-EC-001, REQ-EC-008, REQ-EC-009 and DEC-038.
- **Predictions.**
  - K_m 0.735 N/√W; 0.52 N per axis at 0.5 W; ±4.0 mm stroke on 5 Hz flexures (CALC).
  - Power: 1.0 W peak and 0.145 W average in the design model; 0.029 W average in the test runs, drivers included (CALC, SIM).
  - End-cap Ø26 × 24 mm, 43.3 g. Pen about 115 g on the Rev H pen; about 134–136 g with every Rev J module (CALC, DEC-038).
  - 9.8–20 h of writing on the Rev H base load of 0.081 W (CALC).
  - ET95NM relative permeability ≤ 1.05 (MFR AMF-49).
- **Set-up.** The end-cap clamped to a 6-axis load cell (ATI Nano17 class, R4). Coil current and slug position (Hall) logged. A permeability meter. A balance.
- **Procedure.**
  1. Incoming inspection: permeability of every tungsten part that sits within 20 mm of a Hall sensor or coil.
  2. Weigh and measure the end-cap, and the pen with every Rev J module fitted.
  3. Drive each axis with sines of 1–15 Hz at 0.1–1 W.
  4. Drive the slug to ±4 mm and check for contact.
  5. Log the power during the EXP-K02 tremor runs with the nose on.
- **Measurands.** Net force on the housing; K_m; stroke; flexure frequency and damping; power; mass and size; permeability.

<!-- AC-TABLE:EXP-K01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K01-01 | — | Net force on the housing per axis (end-cap clamped to a 6-axis load cell), sines 1-15 Hz at 0.1-1 W, against the model (endcap/design.py; rm_coil_cap in endcap/sim.py) | within ±20 % of the model | hypothesis | pass line of study K; DEC-038 is revisited if EXP-K01 misses the force model by more than 20 %; model net push about 0.9 x m x omega^2 x X at the slug's limit (CALC) | DEC-038 |
| AC-K01-02 | — | Coil force constant K_m per axis (force and current) and slug stroke: ±4 mm reached in both axes without contact (both) | both met (K_m ≥ 90 % of 0.735 N/√W; ±4 mm without contact) | hypothesis | pass line of study K; design K_m 0.735 N/√W, 0.52 N per axis at 0.5 W, ±4.0 mm on two 5 Hz flexures (CALC, docs/inertial_endcap.md s9.1); in the test runs the slug reached its stops in 39 of 180 cases (SIM): soft end-stops | DEC-038 |
| AC-K01-03 | REQ-EC-001 | Built end-cap: diameter, length and mass; peak and average electrical power (drivers included) logged during the EXP-K02 tremor runs | ≤ 26 mm, 45 mm, 45 g; 1 W peak, 0.3 W average | requirement | REQ-EC-001; prediction Ø26 x 24 mm, 43.3 g; 1.0 W peak and 0.145 W average (design model), 0.029 W average in the test runs (CALC, SIM; results/endcap/endcap_study.json) | DEC-038 |
| AC-K01-04 | REQ-EC-001 | Pen with every Rev J module fitted (nose v2, heel drive, end-cap): length and mass (weighing) | ≤ 175 mm and 120 g | requirement | REQ-EC-001; prediction about 134-136 g (CALC, DEC-038: nose v2 pen 83.5 g + heel drive 9.1 g + end-cap 43.3 g, less the rear cap it replaces) -> predicted to FAIL on mass; the end-cap stays detachable | DEC-038 (detachable end-cap); Rev J envelope |
| AC-K01-05 | REQ-EC-008 | Writing time per charge with the end-cap active: 2.22 Wh usable (MFR AMF-80) divided by the end-cap's measured mean power in the EXP-K02 runs plus the measured base load of the pen it is fitted to, nose on | ≥ 8 h | requirement | REQ-EC-008; prediction 9.8 h (design model, 0.145 W) to 20 h (test runs, 0.029 W) on the Rev H base load of 0.081 W (CALC) -> at risk with the nose v2 base load (DEC-036: coil loss 0.16-0.18 W with 1 mm tremor), not included in the prediction | DEC-038; Rev J power budget |
| AC-K01-06 | REQ-EC-009 | Relative magnetic permeability of every tungsten part within 20 mm of a Hall sensor or coil (incoming inspection, permeability meter) | ≤ 1.05 | derived | REQ-EC-009 made measurable: ET95NM relative permeability ≤ 1.05 (MFR AMF-49); INERMET grades paramagnetic (MFR AMF-125) | DEC-038; Hall sensor bias |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (6 rows for EXP-K01).
<!-- AC-TABLE:EXP-K01:END -->

- **Decision rule.** Force model missed by more than 20 %: re-fit `endcap/design.py` and re-run study K (DEC-038 revisit). Pen over 120 g with every module (as predicted): the end-cap stays detachable (DEC-038). Runtime under 8 h: the lead balances the Rev J power budget. A magnetic tungsten part: reject it.

### EXP-K02: Tremor on top of the nose, on a bench (extends EXP-I06)

- **Purpose and gates.** Measure the further reduction that the end-cap adds on top of the nose, and compare it with the same mass fixed. Gates REQ-EC-002, REQ-EC-003 and DEC-038.
- **Predictions (SIM).**
  - Further reduction at 8–12 Hz, 1–2 mm: +8 / +18 / +20 % at r_rot 0.3 / 0.5 / 0.7 (seed spread +4 to +25 %).
  - The same 45 g fixed: +17 / +12 / +4 %. So the motion adds −9 / +6 / +16 points.
  - At 4–6 Hz: +8 to +12 %.
  - The fixed weight makes 29–42 % of the hard cases worse than the nose alone at r_rot 0.5–0.7; the moving slug 4–12 %.
  - The slug reached its stops in 39 of 180 test cases: soft end-stops are needed.
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
- **Set-up.** An instrumented pen with a 6-axis load cell between the front and rear grip zones (R6 with a second stinger, as EXP-I01), with and without the 45 g end-cap. 20 writers.
- **Procedure.** As EXP-I01, once with and once without the end-cap, in random order.
- **Measurands.** Rotational stiffness about the grip; r_rot with its 95 % interval.

<!-- AC-TABLE:EXP-K08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-K08-01 | — | Grip split r_rot (rotational share of the grip compliance about the grip, EXP-I01 method) with and without the 45 g end-cap, 20 writers: median with its 95 % interval | within 0.3-0.7 | hypothesis | DEC-038 revisit trigger (r_rot outside 0.3-0.7); study K reported every result at r_rot 0.3 / 0.5 / 0.7 (split ASSUMPTION; H1 grip calibrated to HAP-26) | DEC-038; grip-split setting of EXP-K02; weight mode |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-K08).
<!-- AC-TABLE:EXP-K08:END -->

- **Decision rule.** Outside 0.3–0.7: re-run study K (`python3 -m endcap.run_study`) with the measured value (DEC-038 revisit). Near 0.3, where the fixed weight did better in SIM: test the held "weight mode" (a proposal, not simulated).

---

## 43. Rev J nose v2 and autowrite: EXP-N01…N08

### Purpose and what it gates

DEC-036 keeps architecture B: the skid ring on the fixed sleeve carries the writing force. The gimbal moves to 76.5 mm behind the ball, with the magnets on an 11.5 mm arm behind it. The magnets are a 2 × 2 N52 checkerboard on a spherical iron cap that faces a coil plate on a concentric sphere (0.77 mm gap at every tilt).
- **Numbers.** Handle Ø24 mm. Ball travel 6.0 mm in every direction over 35–75° (6.5 mm at 50°). Skid contact radius 10.0 mm. Refill slide 24 mm.
- **Pen lift.** A module at the gimbal sets the 0.15 N ink force through a tendon and lifts the ball 0.5 mm, with no holding power. A page sensor (1 kHz, ≤ 2 ms, ≤ 10 µm) is required.
- **Autowrite (DEC-039).** In an explicit mode the pen draws a known text inside the nose's reach while the user sweeps the pen along the line.
- **Corrections to Rev H (DEC-041).** The image-method magnetics give the Rev H nose 0.19 N/√W at the magnets, not 0.47 (EXP-N01 measures both). A stock constant-force refill spring may last about an hour of tremor stabilisation (EXP-N06). A free refill follows ordinary pen lifts at 50–70° (EXP-N05).
- **What it gates.** DEC-036 is revisited if EXP-N01 measures K_m below 0.85 × the design value, EXP-N04 exceeds 20 K or 41 °C, or EXP-N07 cannot give a 1 kHz page position. Requirements: REQ-RVJ-N01…N08, and REQ-RVH-003 for the Rev H coupon.
- **Predictions** come from `docs/nose_v2.md` and `results/nose2/nose2.json`: design models optimised by CMA-ES and adjoint L-BFGS (CALC), and autowrite in model HW1 on synthetic writers and tremor (test writers 0–5, seeds 200–203; SIM). The magnetics are an upper bound (ideal iron).
- **Freedom to operate.** Autowrite with a pen lift is close to claim 1 of PAT-01. Attorney review comes before any product claim (DEC-036).
- Work with people (EXP-N09, N10) is in [`human_study_plan.md`](human_study_plan.md) §18.

### EXP-N01: Magnetics before building a nose (and Rev H's K_m)

- **Purpose and gates.** Measure the force constant of the recommended actuator, and settle Rev H's. Gates DEC-036, DEC-041 item 1, REQ-RVJ-N02 and REQ-RVH-003.
- **Predictions.**
  - C1S spherical-gap unit: 0.66 N/√W per axis at the magnets, 0.099 N/√W at the tip; gap flux 0.75 T (image method, an upper bound; CALC).
  - Rev H radial unit: 0.47 N/√W by the lumped adjoint model, against 0.19 N/√W and 0.12 T by the image method (CALC).
  - A large-stroke Lorentz actuator in the literature varied by 21.6–30.9 % over ±5 mm (LIT AMF-143).
- **Set-up.** Two coupons on R4. One Rev H radial unit: 3.0 × 6.5 × 2.8 mm N45 magnets, 1.43 mm coil, 2.77 mm gap. One C1S unit in the recommended geometry: a machined spherical Hiperco or 1010 cap and plate, 0.2 mm self-bonding wire. A 0–2 N load cell (0.5 mN resolution), a bench supply, a gaussmeter, a micro-ohmmeter at 20 °C.
- **Procedure.**
  1. Coil resistance at 20 °C.
  2. Gaussmeter map of the gap.
  3. Force per ampere over the stroke grid, both axes: the C1S unit over ±1.05 mm of magnet stroke, the Rev H unit over its 2.3 mm.
- **Measurands.** K_m (N/√W) per axis over the stroke; gap flux (T); force ripple (%).

<!-- AC-TABLE:EXP-N01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N01-01 | REQ-RVJ-N02 | Force constant of the C1S spherical-gap coupon per axis over the whole magnet stroke (±1.05 mm; load cell and coil current), as a fraction of the CALC value (0.66 N/√W at the magnets, 0.099 N/√W at the tip); lowest point of the map | ≥ 0.85 | requirement | REQ-RVJ-N02; image-method magnetics with ideal iron, an upper bound (gap flux 0.75 T; CALC, results/nose2/nose2.json) | DEC-036 (revisit if below 0.85 x the design value) |
| AC-N01-02 | — | Force ripple of the C1S coupon over the magnet stroke ((max - min) / mean of the force per ampere) | ≤ 15 % | hypothesis | pass line of the nose v2 study; a large-stroke 2-DOF Lorentz actuator varied 21.6-30.9 % over ±5 mm (LIT AMF-143): if higher, calibrate a force map | DEC-036 |
| AC-N01-03 | REQ-RVH-003 | Force constant of the Rev H radial-gap coupon (3.0 x 6.5 x 2.8 mm N45, 1.43 mm coil, 2.77 mm gap) per axis at the magnets, mapped over its 2.3 mm stroke | ≥ 0.40 N/√W | requirement | REQ-RVH-003; lumped adjoint model 0.47 N/√W (results/revH/tip_params.json) against 0.19 N/√W with 0.12 T by the image method (CALC, docs/nose_v2.md s4.2) -> contested, likely to FAIL (DEC-041 item 1); the Rev H coil loss would rise from 0.004 to about 0.027 W | DEC-041 (confirm 0.47 N/√W); DEC-032 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N01).
<!-- AC-TABLE:EXP-N01:END -->

- **Decision rule.** C1S below 0.85 × the CALC value: revisit DEC-036 (re-run `python3 nose2/run_study.py` with the measured flux; the radial-gap C1 reaches 5 mm). Rev H below 0.40 N/√W (as predicted): REQ-RVH-003 fails, and the Rev H coil loss while writing rises from 0.004 to about 0.027 W (DEC-041). Ripple above 15 %: calibrate a force map in the firmware.

### EXP-N02: Travel and front-end closure over 35–75°

- **Purpose and gates.** Check the guaranteed travel and the front end. Gates REQ-RVJ-N01 and DEC-036.
- **Predictions (CALC, PROPOSED DESIGN; `results/nose2/layout.json` fit checks).** 6.0 mm guaranteed and 6.5 mm at 50°. Skid-ring contact radius 10.0 mm. Refill slide 24.4 mm over 35–75°. Nozzle 0.71 mm above its 0.3 mm clearance; ring lip 0.26 mm above its 1.0 mm minimum; sleeve front 0.25 mm above the paper at 35°.
- **Set-up.** The nose built to `results/nose2/layout.json`, with its skid ring. A tilt jig at 35/50/75° (R5). A side camera. Feeler gauges.
- **Procedure.** At each tilt, drive the nose to its travel in 24 directions on paper. Photograph the ball. Measure the nozzle and sleeve clearances and the refill slide.
- **Measurands.** Guaranteed ball travel; nozzle and sleeve clearance to the paper; ring lip; refill slide.

<!-- AC-TABLE:EXP-N02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N02-01 | REQ-RVJ-N01 | Guaranteed ball travel relative to the handle with the skid ring on paper, 24 directions, θ 35/50/75° (photographs of the ball); smallest value | ≥ 6.0 mm | requirement | REQ-RVJ-N01; prediction 6.0 mm guaranteed and 6.5 mm at 50° (PROPOSED DESIGN, CALC, results/nose2/layout.json) | DEC-036 |
| AC-N02-02 | — | Front end at the travel limit, θ 35/50/75°, 24 directions: nozzle clearance to the paper, ring lip wall, and refill slide within the refill force element's working range (feeler gauges, side camera) (all) | all met (nozzle ≥ 0.3 mm; lip ≥ 1.0 mm; slide within range) | derived | DEC-036 front-end rules (DEC-034 generalised); prediction: margins 0.71 mm (nozzle) and 0.26 mm (lip) over these limits, sleeve front 0.25 mm above the paper at 35°, refill slide 24.4 mm (CALC, results/nose2/layout.json fit_checks) | DEC-036 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N02).
<!-- AC-TABLE:EXP-N02:END -->

- **Decision rule.** Travel short: plan autowrite with the measured reach (a plan reach of 5.0 mm still fits 2.5 mm letters at 1.0 × the line speed for every test writer; CALC). A clearance fails: re-run `nose2/frontend.py` with the measured parts.

### EXP-N03: Servo bandwidth and parasitic modes

- **Purpose and gates.** Gates REQ-RVJ-N02 and DEC-036.
- **Predictions.** First parasitic mode 788 Hz (carrier bending), which allows a servo up to 263 Hz; 80 Hz was used in SIM (CALC). A 40 Hz servo raised the autowrite ink error from 30 to 44 µm, and the letters were still read (SIM).
- **Set-up.** The EXP-N02 nose in a clamped handle. The 3-D Hall sensor (TMAG5170, ±50 mT range, MFR OPT-53). A laser vibrometer on the ball.
- **Procedure.** Swept sines from 1 to 1000 Hz, open loop (modes) and closed loop (bandwidth and phase margin), both axes, at the centre of travel and at 3 mm.
- **Measurands.** −3 dB bandwidth; phase margin; first parasitic mode.

<!-- AC-TABLE:EXP-N03:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N03-01 | REQ-RVJ-N02 | Closed-loop nose bandwidth (-3 dB of ball position over reference, swept sine, 3-D Hall sensor and laser vibrometer on the ball) and first parasitic mode (open loop), both axes | ≥ 60 Hz and 240 Hz | requirement | REQ-RVJ-N02; prediction first parasitic mode 788 Hz (carrier bending), which allows a servo up to 263 Hz; 80 Hz used in SIM (CALC) | DEC-036 |
| AC-N03-02 | — | Phase margin of the nose servo at the tuned bandwidth, both axes | ≥ 45° | derived | pass line of the nose v2 study; the same margin as REQ-RVH-003 for the Rev H nose (DEC-036 extends DEC-032) | DEC-036 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N03).
<!-- AC-TABLE:EXP-N03:END -->

- **Decision rule.** Short: stiffen the carrier or retune, and re-run the HW1 autowrite grid with the measured servo.

### EXP-N04: Heat at the autowrite duty

- **Purpose and gates.** Gates REQ-RVJ-N03 and DEC-036 (revisit above 20 K or 41 °C).
- **Predictions.** 0.182 W of coil loss while autowriting 3 mm letters with 1 mm rms tremor, and 18.2 K at 100 K/W (thermal resistance ASSUMPTION; CALC). With 2 mm tremor the coil loss is 0.38 W, about twice the design point (SIM).
- **Set-up.** The nose in its handle at 23 °C ambient. Thermocouples on the coil and the shell; coil-resistance thermometry; an IR camera (R4 instruments).
- **Procedure.**
  1. Drive the coils for 30 min with the recorded HW1 force histories of the test grid (1 mm tremor).
  2. From cold, drive them with the 2 mm histories until the coil reaches 20 K. This gives the thermal time constant for the firmware's duty limit.
- **Measurands.** Coil rise; grip surface temperature; thermal time constant.

<!-- AC-TABLE:EXP-N04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N04-01 | REQ-RVJ-N03 | Coil temperature rise (thermocouple and coil resistance) and grip surface temperature after 30 min of the recorded HW1 force histories (autowrite, 1 mm tremor) in the handle at 23 °C ambient; guarded acceptance | ≤ 20 K and 41 °C | requirement | REQ-RVJ-N03; prediction 18.2 K at 100 K/W (thermal resistance ASSUMPTION) with 0.182 W (CALC) -> marginal; grip limit 41 °C (IEC 60601-1, LIT AMF-34, AMF-35) | DEC-036 (revisit above 20 K or 41 °C) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-N04).
<!-- AC-TABLE:EXP-N04:END -->

- **Decision rule.** Above 20 K or 41 °C: revisit DEC-036 (a duty limit, or the coarse–fine C3, which halves the coil loss in the model). Safety-related: guarded acceptance (§0.5). The 2 mm time constant sets how long a text may run with severe tremor.

### EXP-N05: Pen lift

- **Purpose and gates.** Gates REQ-RVJ-N04, the pen lift of DEC-036 and DEC-041 item 3 (a free refill joins strokes).
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
| AC-N05-01 | REQ-RVJ-N04 | Pen-lift module: ball lift off the paper and time from command to lift and to contact (high-speed video), holding power in either state, and life projected from 1e6 cycles at 4 lifts/s (all) | all met (≥ 0.3 mm; ≤ 8 ms; 0 W holding; ≥ 1e7 cycles) | requirement | REQ-RVJ-N04; prediction 0.5 mm lift, 5 ms switching, 8 ms command to contact in SIM, no holding power (CALC on ASSUMPTION brake and latch values; docs/nose_v2.md s6) | DEC-036 (pen lift) |
| AC-N05-02 | — | Energy per lift cycle (lift, release, brake on and off; current probe) | ≤ 20 mJ | hypothesis | pass line of the nose v2 study; prediction 17 mJ per cycle, 0.07 W while autowriting at 4.2 lifts/s (CALC; brake energy ASSUMPTION) | DEC-036 |
| AC-N05-03 | REQ-RVJ-N04 | Ordinary pen lifts of 1.5 mm between strokes by the writing robot at θ 50/60/70° with the stabiliser on (brake locks the refill when the slide sensor sees it follow a lift): strokes joined by ink | none | derived | DEC-041 item 3; a free refill follows 2.9 mm of pen lift at 50° and 6.5 mm at 70° (CALC, docs/nose_v2.md s3); the brake alone does it (about 6 mJ per stroke, ASSUMPTION) | DEC-041 (pen lift or refill lock); DEC-036 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-N05).
<!-- AC-TABLE:EXP-N05:END -->

- **Decision rule.** Fail: redesign the lift. Without a lift, autowrite inks its pen-up moves (ink error 59 against 29 µm, SIM), and the pen needs a refill lock (DEC-041).

### EXP-N06: Refill force element fatigue

- **Purpose and gates.** Gates REQ-RVJ-N05, the refill drive of DEC-036, and DEC-041 item 2.
- **Predictions.** Stock constant-force springs are rated for 2 500–25 000 cycles (MFR AMF-144). Tremor stabilisation cycles the slide about 29 000 times per hour (CALC). A 0.3 N ink force raised the coil loss 2.4-fold (SIM).
- **Set-up.** R8 fatigue stations with a 0–10 N load cell. Four candidates: the stock constant-force spring (AMF-144), the drum's spiral spring, a long helical spring and a magnetic spring.
- **Procedure.** Force against slide over 24.4 mm. Cycle at ±1 mm, 8 Hz and at ±5 mm, 3 Hz. Re-measure the force at every decade of cycles.
- **Measurands.** Force against slide; cycles to failure.

<!-- AC-TABLE:EXP-N06:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N06-01 | REQ-RVJ-N05 | Chosen refill force element: ink force over the whole refill slide (24.4 mm) and cycles without failure at ±1 mm, 8 Hz and at ±5 mm, 3 Hz (both) | both met (0.15 N ± 20 %, never above 0.2 N; no failure within 1e8 small cycles) | requirement | REQ-RVJ-N05; 1e8 small cycles is about 3 years of 8 h days with tremor (docs/nose_v2.md s10); a 0.3 N ink force raised the coil loss 2.4-fold (SIM) | DEC-036 (refill drive); DEC-041 item 2 |
| AC-N06-02 | — | Stock constant-force spring (MFR AMF-144, the Rev H type) cycled at ±1 mm, 8 Hz: cycles to failure | ≥ 1e8 cycles | hypothesis | DEC-041 item 2 (revisit if a stock spring passes EXP-N06); rated 2 500-25 000 full-stroke cycles (MFR AMF-144) while tremor stabilisation cycles the slide about 29 000 times per hour (CALC) -> predicted to FAIL | DEC-041; Rev H refill spring (DEC-034) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N06).
<!-- AC-TABLE:EXP-N06:END -->

- **Decision rule.** Use the first candidate that passes. If the stock spring fails (as predicted), Rev H needs the fatigue-rated element too (DEC-041).

### EXP-N07: Page sensor under the pen

- **Purpose and gates.** Gates REQ-RVJ-N06, DEC-036, and the slip detection of DEC-037.
- **Predictions.** The SIM assumed 1 kHz, 2 ms and 3 µm of noise (fusion study model, ASSUMPTION). With a 120 Hz, 10 ms sensor autowrite still read every word, but the ink error rose from 30 to 72 µm (SIM). A PMW3360-class sensor reports at up to 12 000 frames/s with its lens 2.4 mm above the surface (MFR OPT-54).
- **Set-up.** A PMW3360-class sensor behind a flat window 2.4 mm above the paper, beside the skid ring. The pen swept by a motion stage (R5) with 1 mm tremor added; ground truth from the stage encoders. Lined, grid and glossy paper. Tilts 35–75°.
- **Procedure.** Sweeps at 5–30 mm/s with tremor at 4–12 Hz, on each paper and tilt. Latency by cross-correlation with the encoders.
- **Measurands.** Position error (µm rms); report rate; latency; drop-outs.

<!-- AC-TABLE:EXP-N07:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N07-01 | REQ-RVJ-N06 | Page sensor (PMW3360 class behind a flat window 2.4 mm above the paper beside the skid ring) against the motion-stage encoders, 1 mm tremor added, θ 35-75°, lined, grid and glossy paper: report rate, latency (cross-correlation), position error and drop-outs (all) | all met (≥ 1 kHz; ≤ 2 ms; ≤ 10 µm RMS; no drop-out) | requirement | REQ-RVJ-N06; SIM assumed 1 kHz, 2 ms, 3 µm noise (fusion study model, ASSUMPTION); with 120 Hz and 10 ms the autowrite ink error rose from 30 to 72 µm (SIM); PMW3360 up to 12 000 frames/s with its lens 2.4 mm above the surface (MFR OPT-54) | DEC-036 (revisit if no 1 kHz page position); DEC-037 (slip detection) |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (1 rows for EXP-N07).
<!-- AC-TABLE:EXP-N07:END -->

- **Decision rule.** No 1 kHz position within 2 ms and 10 µm: revisit DEC-036 (autowrite with a slower sensor still reads the words, with twice the ink error) and the slip detector of DEC-037.

### EXP-N08: Autowrite on the bench

- **Purpose and gates.** Gates REQ-RVJ-N08 (the SIM gate on the firmware), DEC-039, and the go-ahead for EXP-N09.
- **Predictions (SIM).** Ink error 29 µm without tremor, 36 µm with 1 mm and 60 µm with 2 mm. Letters read 99.2 % (98.3 % at 2 mm) against a 100 % ceiling. 3.7 letters per second at a 9.5 mm/s sweep. Total power 0.24 W without tremor and 0.31 W with 1 mm. One test writer needed a slower sweep for its line (post hoc); DEC-039 lets the pen set the sweep speed per line.
- **Set-up.** The pen on a motion stage that sweeps at the planner's speed (R2). Tremor from a shaker (0.3/1/2 mm at 4/8/12 Hz). The text of the HW1 test set. R3 scans; the app's recogniser and reader; coil power logging.
- **Procedure.**
  1. Run the SIM gate on the firmware under test.
  2. Write the test sentence at 2.5 and 3 mm x-height under each tremor condition, in random order.
  3. Scan and score blind.
- **Measurands.** Ink error to the target; letters and words read; coil power.

<!-- AC-TABLE:EXP-N08:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-N08-01 | REQ-RVJ-N08 | SIM gate on the firmware under test before each bench session: HW1 test set (writers 0-5, seeds 200-203), 2.5 mm letters, ≤ 1 mm tremor: mean letters read, mean ink error, and every writer's line planned (all) | all met (≥ ceiling - 2 points; ≤ 45 µm RMS; every line planned) | requirement | REQ-RVJ-N08; SIM 99.2 % against a 100 % ceiling, 29-36 µm; writer 4 had no plan at the frozen 1.25 x sweep (12 of 72 cases per tremor amplitude) and passes only with the per-line sweep speed of DEC-039 (post hoc; results/nose2/nose2.json) | DEC-039; firmware for EXP-N08 and EXP-N09 |
| AC-N08-02 | — | Autowrite on the motion stage with shaker tremor (0.3/1/2 mm at 4/8/12 Hz), text of the HW1 test set, 2.5 and 3 mm letters: ink error to the target relative to the SIM value at the same conditions, and letters read by the app's recogniser against the clean-target ceiling (both) | both met (≤ 1.5 x SIM; ≥ ceiling - 5 points) | hypothesis | pass line of the nose v2 study; SIM 29 / 36 / 60 µm at 0 / 1 / 2 mm tremor (2.5 mm letters), letters 98.3-99.2 % against a 100 % ceiling (docs/nose_v2.md s5.3) | DEC-039; DEC-036 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-N08).
<!-- AC-TABLE:EXP-N08:END -->

- **Decision rule.** SIM gate fails: no bench or participant session with that firmware. Bench lines fail: identify the pen (EXP-V02) and retune in the calibrated simulator.

---

## 44. Simulator v2 validation: EXP-V01…V06

### Purpose and what it gates

DEC-040 makes sim2 (MuJoCo) the Rev J reference simulator, with H1 as the regression check. Until EXP-V01, V02 and V04 calibrate it and EXP-V05 validates it, sim2's results rank concepts (context of use COU-1) and are not evidence of benefit (REQ-SIM-005).
- **Order** (`docs/sim_v2.md` §8.4, as the s2r protocol): actuator coupons (EXP-B03) → nose frequency response (EXP-B05 methods, EXP-V02) → friction (EXP-B01/B02, V01) → hand (V04) → writers and tremor (V03) → freeze → EXP-V05 → EXP-V06 with human data.
- **Identification.** Stochastic grey-box models with the same equations as sim2. Maximum likelihood with an extended Kalman filter over several recordings; parameters with 95 % intervals; residual checks (s2r `modelform.py`). The domain-randomisation (DR) ranges then narrow to the identified intervals. Parameters are frozen before EXP-V05 and never refitted on validation data.
- **What it gates.** DEC-040 is revisited if EXP-V05 fails its pass lines, or if a device result depends on the contact law beyond the stated tolerance. Requirements: REQ-SIM-001…005 (checked on the frozen model in EXP-V05) and REQ-RVH-008 (EXP-V02 part B).
- **Predictions (SIM, `results/sim2/`).** sim2 reproduces H1 on 56 Rev H cases: unmodified ink error within 3.1 %, oracle ratio within ±0.03 in 52 of 56. A 25 µs step is converged (0.22 µm against 12.5 µs). Energy residual ≤ 6.8 × 10⁻⁴. All of this is model to model; no bench or human data exist.
- EXP-V03 runs inside EXP-H01 sessions and EXP-V04 with participants; both are covered by the same ethics approval. EXP-V06 is an offline analysis of human-study data.

### EXP-V01: Paper contact of the Rev H front end

- **Purpose and gates.** Calibrate and validate the contact law. Gates DEC-040: H1's law for ink metrics, native contacts only for geometry-rich plug-ins.
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

---

## 45. Rev J control stack: EXP-L01, L02, L04, L05

### Purpose and what it gates

DEC-042 sets the Rev J control stack.
- **Default estimator.** A causal tremor-line detector on the page sensor looks at the last 4 s every 50 ms (peak-to-floor ratio in 4.5–13.5 Hz, hysteresis 5/2.5, amplitude gate 0.15–0.35 mm; its state kept across lines). It opens a listening fixed-lag Kalman estimate at lag 0 only while a tremor line is present. Otherwise the Rev H tracker runs.
- **Successor in shadow mode.** A causal TCN (34 k parameters, int8) logs its estimate beside the default. It drives the nose only after REQ-ML-001 passes on held-out real recordings.
- **No delayed ink; RL offline only; one arbitration law.** The ink never trails the hand. RL designs the arbitration offline; no RL policy drives the nose. Every assistance uses α = α_max × c_conf × c_need × c_agree, slew-limited, with the hand-back rules.
- **What it gates.** DEC-042 is revisited if EXP-L01 or EXP-L02 fail, if EXP-L04 passes (then the TCN may take over), or if EXP-L05 passes its rules. Requirements: REQ-CTRL-009, REQ-CTRL-010, REQ-CTRL-011, REQ-ML-003 and REQ-ML-004.
- **Predictions** come from `docs/ai_control_v2.md` and `results/ai2/ai2.json` (model HW1; test writers 0–5, seeds 200–203; rules R1–R4 fixed on tuning seeds 300–301; SIM and CALC). The learned models and RL policies were trained and tested inside one simulator family.
- **Data.** EXP-L01, L02 and L04 replay the EXP-H01 recordings (instrumented passive pen, tip camera as the reference), with the participant splits of REQ-DATA-001 and the EXP-E01 protocol.
- The studies with people (EXP-L03, L06, L07, L08) are in [`human_study_plan.md`](human_study_plan.md) §19.

### EXP-L01: Does the tremor-line gate stay shut on real tremor-free writing?

- **Purpose and gates.** Check the gate on real writing: shut on tremor-free writing, open on real tremor. Check that the stack is causal. Gates REQ-CTRL-009, REQ-CTRL-010 and DEC-042.
- **Predictions (SIM).**
  - The gate never opened on the tremor-free writing of any tuning or test writer. Tremor-free writing moved 26.3 µm, the same as with the Rev H tracker.
  - At 1–2 mm it was open for 51–73 % of a 20 s recording, because it needs about 4.5 s to open (4 s window + 0.5 s). Once open on tuning data, it stayed open for 95 % of the detector's updates.
  - At 0.3 mm it was open for 0.1–12.9 % of the time.
- **Set-up.** Offline: the EXP-H01 recordings of ET, PD and control writers. The Rev J estimator stack as firmware code, run in a replay harness. Then the bench pen with recorded hand motion.
- **Procedure.**
  1. Test the causality of the stack build: change sensor samples after their availability time and check that no earlier command changes.
  2. Replay every recording, keeping the detector's state across lines within a session, as the firmware does.
  3. Log the gate, the detector's ratio and amplitude, and the commanded correction.
  4. Repeat on the bench pen.
- **Measurands.** Gate-open share of tremor-free writing time per writer; time to open after tremor onset; open share at 1–2 mm after the first 5 s; tremor-free writing moved (the commanded correction on the controls' writing) against the Rev H tracker alone.

<!-- AC-TABLE:EXP-L01:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L01-01 | REQ-CTRL-010 | Gate-open share of tremor-free writing time for every control writer (EXP-H01 recordings replayed offline through the Rev J estimator stack, detector state kept across lines; tip camera as reference) | ≤ 1 % | requirement | REQ-CTRL-010 (closed ≥ 99 %); SIM: never open on the tremor-free writing of any tuning or test writer (results/ai2/ai2.json) | DEC-042 (revisit if the gate fails on real writing) |
| AC-L01-02 | REQ-CTRL-010 | Tremor-free writing moved (commanded correction on the controls' recordings) with the gated stack minus that with the Rev H tracker alone, every control writer, RMS | ≤ 2 µm | requirement | REQ-CTRL-010; SIM 26.3 µm with both (test grid), because the gate stays shut | DEC-042 |
| AC-L01-03 | — | Gate-open share of pen-down time after the first 5 s of writing, writers with 1-2 mm tremor at the tip | ≥ 80 % | hypothesis | pass line of study L; SIM: open for 51-73 % of a whole 20 s recording because the detector needs about 4.5 s to open, and for 95 % of its updates at 1-2 mm once open on tuning data (docs/ai_control_v2.md s3.4, s4.1) | DEC-042 |
| AC-L01-04 | REQ-CTRL-009 | Causality test of the estimator stack used in the replay (firmware build): changing any sensor sample after its availability time (acquisition + latency) changes no earlier nose command, and every estimator output at a tick uses only samples available at that tick | conforms (bit-exact) | requirement | REQ-CTRL-009; study L found and fixed two look-ahead leaks before its test (docs/ai_control_v2.md s13 item 3); unit tests in ai2/tests | DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (4 rows for EXP-L01).
<!-- AC-TABLE:EXP-L01:END -->

- **Decision rule.** The gate opens on real tremor-free writing: revisit DEC-042 (re-tune the thresholds on training participants only, or keep the Rev H tracker). It opens too little on real tremor: re-tune the detector; the 20 s calibration can arm its band.

### EXP-L02: Does the gated tracker beat the Rev H tracker on real writing?

- **Purpose and gates.** Compare the default with the Rev H tracker, offline on real writing and in closed loop on the bench. Gates REQ-CTRL-011 and DEC-042.
- **Predictions (SIM).** At 1–2 mm and 6–10 Hz: 430 against 627 µm (0.69; paired −197 µm, 95 % CI −206 to −188). At 6 Hz, where the Rev H tracker does nothing: 818 → 540 µm. Letters read 64 → 78 %, words 49 → 74 %. 0.3 mm tremor unchanged (161 against 162 µm).
- **Set-up.** Offline: the EXP-H01 recordings, paired per writer, with the tip camera as the intended path. Bench: the Rev J pen in closed loop on the EXP-I05 tremor rig (R2 with a 2-axis shaker) with recorded hand paths; R3 scans.
- **Procedure.**
  1. Replay the recordings through both trackers. Score the ink error against the tip-camera intent, the letters read by the app, and the false correction on the controls' writing.
  2. Bench: 0.3, 1 and 2 mm at 6, 8 and 10 Hz, both trackers, 10 seeds each, in random order.
- **Measurands.** Ink error; letters and words read; false correction; paired differences per writer.

<!-- AC-TABLE:EXP-L02:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L02-01 | REQ-CTRL-011 | Ink error against the tip-camera intent with the gated tracker relative to the Rev H tracker at 1-2 mm tremor, 6-10 Hz (EXP-H01 recordings replayed offline, paired per writer); geometric mean ratio, with the paired 95 % upper bound below 1 | ≤ 0.8 | requirement | REQ-CTRL-011; SIM 430 against 627 µm (0.69), paired -197 µm (95 % CI -206 to -188); 6 Hz 818 -> 540 µm (results/ai2/ai2.json) | DEC-042 (revisit if it fails) |
| AC-L02-02 | REQ-CTRL-011 | Letters read by the app with the gated tracker minus with the Rev H tracker at every tremor condition, and ink error at 0.3 mm relative to the Rev H tracker (both) | both met (≥ -1 point; ≤ 1.02) | requirement | REQ-CTRL-011; SIM letters 78 against 64 % at 1-2 mm; 0.3 mm 161 against 162 µm | DEC-042 |
| AC-L02-03 | — | Closed loop on the bench pen with the EXP-I05 tremor rig (R2 with a 2-axis shaker), 1-2 mm at 6-10 Hz, 10 seeds: ink error with the gated tracker relative to the Rev H tracker (R3 scans) | ≤ 0.8 | hypothesis | pass line of study L; SIM 0.69, model to model only | DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-L02).
<!-- AC-TABLE:EXP-L02:END -->

- **Decision rule.** Pass: the gated tracker stays the default (DEC-042). Fail: revisit DEC-042; the Rev H tracker stays.

### EXP-L04: Does a learned estimator pass REQ-ML-001 on real data?

- **Purpose and gates.** Test the TCN against the gate for learned models, and check its cost on the pen. Gates REQ-ML-001, REQ-ML-003 and the TCN's move from shadow mode to the nose (DEC-042).
- **Predictions.**
  - SIM: 278 µm at 1–2 mm (−152 µm against the gated tracker, 95 % CI −164 to −141), 307 µm at 6 Hz, 127 µm at 0.3 mm. Tremor-free writing moved 19.3 µm on average, but 34.8 µm for the worst writer, above REQ-ML-001's 25 µm. The 20 s calibration as an extra input did not help (290 µm).
  - CALC: 33 248 multiply-accumulates per 2 ms step; 33 kB of int8 weights and about 16 kB of history; about 0.56 ms per step on a 128 MHz Cortex-M33 (28 % of one core; MCU model ASSUMPTION, LIT EML-13).
- **Set-up.** EXP-H01 recordings with the Hall and grip-force channels, split by participant (REQ-DATA-001); only recordings whose consent covers model training (`human_study_plan.md` §3.3, item iii). The gated model-based stack as the conventional comparator (EXP-E01 protocol). The pen MCU on R7 for timing.
- **Procedure.**
  1. Train on synthetic data plus the training participants, then freeze.
  2. Test on held-out participants against the gated stack (paired bootstrap per band).
  3. Time the int8 build on the MCU (logic analyser; worst case over 10⁵ steps) and run the causality test of EXP-L01.
  4. Check the shadow-mode wiring: the TCN's output is logged and never reaches the nose command.
- **Measurands.** Residual ratio by band; false correction on tremor-free writing; spikes; worst-case step time; memory.

<!-- AC-TABLE:EXP-L04:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L04-01 | REQ-ML-001 | Learned estimator (TCN trained on synthetic data and the EXP-H01 training participants) on held-out participants against the gated model-based stack as the conventional comparator: residual-ratio reduction in each of the 4-8 Hz and 8-12 Hz bands (paired bootstrap), false correction on tremor-free writing, and spikes (all, as REQ-ML-001) | all met (≥ 0.10 with the 95 % upper bound below 0; ≤ 25 µm RMS; no spike > 100 µm) | requirement | REQ-ML-001 as written, with the DEC-042 default as the comparator; SIM: 278 against 430 µm at 1-2 mm (paired -152 µm, 95 % CI -164 to -141); tremor-free writing 19.3 µm on average but 34.8 µm for the worst writer (docs/ai_control_v2.md s4.5) -> may fail on that writer | DEC-042 (the TCN drives the nose only if this passes) |
| AC-L04-02 | REQ-ML-003 | Int8 TCN on the pen MCU (128 MHz Cortex-M33 class; logic analyser, worst case over 1e5 steps): time per 2 ms step, weight memory, and causality (test of AC-L01-04) (all) | all met (≤ 2 ms per 2 ms step; ≤ 64 kB of weights; causal) | requirement | REQ-ML-003; prediction about 0.56 ms per step (28 % of one core) and 33 kB of int8 weights plus about 16 kB of history (CALC; MCU model ASSUMPTION, LIT EML-13); REQ-ML-002 allows ≤ 1 ms per 4 ms step | DEC-042 (TCN in shadow mode) |
| AC-L04-03 | REQ-ML-003 | Shadow mode (firmware review and logs): the TCN's estimate is computed and logged beside the default, and never reaches the nose command until AC-L04-01 passes | conforms | requirement | REQ-ML-003; DEC-042 | DEC-042 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (3 rows for EXP-L04).
<!-- AC-TABLE:EXP-L04:END -->

- **Decision rule.** Pass: the TCN may drive the nose (DEC-042 revisit). Fail: it stays in shadow mode, and is retrained with more real data.

### EXP-L05: Does an RL arbiter survive a closed-loop simulator and the bench?

- **Purpose and gates.** Test RL arbitration where the replay results broke down: in closed loop. Gates REQ-ML-004 and DEC-042 (RL offline only).
- **Predictions (SIM, replay-trained policy).** The PPO arbiter read 89 % of words at 298 µm. But it moved tremor-free writing by 30.7 µm (60.9 µm on tuning data, 128 µm for one tuning writer) and was worse than Rev H at 10 Hz, 0.3 mm, so it failed rules R1 and R2. Its replay rule (mean weight ≤ 0.05) missed brief full openings. Residual RL on the command moved tremor-free writing by 165 µm.
- **Set-up.** sim2 (MuJoCo, closed loop, the pen's own sensors) with the estimators run online: the lag-0 smoother as a forward Kalman filter, the recursive Rev H filter, and the detector every 50 ms on a ring buffer. The Gymnasium arbiter environment (`ai2/rl_env.py`) with sim2 as its backend. Then the EXP-V05 bench rig.
- **Dependency.** Training a policy in sim2 for bench tests is context of use COU-2. It needs sim2 validated first (EXP-V05, REQ-SIM-005).
- **Procedure.**
  1. Before training, fix a selection rule on the closed-loop false correction or the peak weight.
  2. Train with a closed-loop false-correction constraint.
  3. Test on held-out sim2 writers and seeds against the model-based gate.
  4. Only if it passes, and EXP-V05 has passed: run the frozen policy on the bench rig.
- **Measurands.** Ink error against the model-based gate; tremor-free writing moved; gate chatter (weight changes per second).

<!-- AC-TABLE:EXP-L05:BEGIN -->
| ID | Req. | Metric | Threshold | Status | Basis | Gates |
|---|---|---|---|---|---|---|
| AC-L05-01 | REQ-ML-004 | RL arbiter trained in sim2's closed loop (estimators run online, closed-loop false-correction constraint), on held-out sim2 writers and seeds: ink error at 1-2 mm relative to the model-based gate, and tremor-free writing moved minus the gate's, with REQ-CTRL-010 and REQ-CTRL-011 met (all) | all met (≤ 0.95; ≤ 2 µm RMS; REQ-CTRL-010 and -011) | requirement | REQ-ML-004 (beats the gate by ≥ 5 %); replay-trained PPO: 298 µm and 89 % of words, but 30.7 µm on tremor-free writing and worse at 10 Hz, 0.3 mm, so it failed rules R1 and R2 (SIM, docs/ai_control_v2.md s5.3) | DEC-042 (RL offline only; revisit if it passes) |
| AC-L05-02 | — | The frozen arbiter on the bench rig (EXP-V05 set-up), 1-2 mm tremor: ink error relative to the model-based gate, and tremor-free writing moved minus the gate's (both); gate chatter reported | both met (≤ 0.95; ≤ 2 µm RMS) | hypothesis | pass line of study L; the bench part is policy training for bench tests (COU-2), allowed only after EXP-V05 passes (REQ-SIM-005) | DEC-042; DEC-040 |

Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) (2 rows for EXP-L05).
<!-- AC-TABLE:EXP-L05:END -->

- **Decision rule.** Fail: keep the model-based gate (DEC-042). Pass in sim2 and on the bench: RL arbitration may be proposed for the pen (DEC-042 revisit).
