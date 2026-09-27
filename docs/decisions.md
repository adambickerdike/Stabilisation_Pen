# Decision log

Each decision is **provisional** until the named experiment closes it. "Evidence" gives the strongest support available now and its status:

- calculation;
- simulation;
- literature;
- CAD;
- design check.

None of the evidence is a physical measurement of our hardware. Revisit a decision when its trigger fires.

| ID | Decision | Alternatives considered | Evidence | Status | Revisit trigger |
|---|---|---|---|---|---|
| DEC-001 | Build a **bench-capable research pen** first. Product architecture decisions wait for its measurements. All numerical targets are hypotheses carried in `config/parameters.yaml` with a status field. | Go straight to a product-form prototype | Audit ([`audit.md`](audit.md)): the decisive quantities (transverse load, tremor at the nib, separability) are unmeasured | accepted | — |
| DEC-002 | **Claims are split by user group and mechanism.** Active nib correction targets action/essential tremor at ≤ 1 mm p-p at the nib. Parkinson's micrographia is addressed by cueing, feedback and practice modes, not correction. Capture and notes are for everyone. No diagnostic claims. | One "tremor pen" claim for PD and ET | COR-10 (about 30 % of ET within 1 mm p-p, literature fit); PD writing impairment is mainly micrographia; ±0.5 mm stage cannot enlarge strokes | accepted | EXP-H01 census |
| DEC-003 | **Front-pivot lever**: pivot 12 mm behind the ball, annular actuator 38 mm behind the pivot (n = 3.17). The stage carries the transverse reaction through the lever. | Direct drive at the tip (A); amplified piezo (C) | Direct drive ≈ 12 W at the design point, Km ≈ 0.19 N/√W (field model); lever ≈ 0.5 W (COR-02; `results/trade/config_trade.json`) — calculation | accepted for Rev A | EXP-B03 actuator coupons; EXP-B01 load map |
| DEC-004 | **Standard D1 mini refill** (Ø2.35 mm, 67 mm) in a titanium carrier tube, clamped at the cone. | Custom short cartridge | Availability, user-replaceable ink; CAD Rev A fits (`results/cad/pen_revA_summary.json`) — CAD | provisional | EXP-B08 ink tolerance to force modulation |
| DEC-005 | **Page-referenced correction**: near-nib optical tracking fused with the IMU. Hall stage sensing and axial-force sensing sit on the lever. IMU-only correction and capture are ruled out. | IMU-only; external tablet | COR-07/08: 0.1° attitude error gives 8.6 mm in 1 s — calculation; DeltaPen-class optical flow 24–68 µm per 10 ms — literature | accepted | EXP-S01 optical latency and accuracy |
| DEC-006 | **Stiff axial path** (k_ax ≈ 2 kN/m) with the axial force *measured*, not absorbed. | Soft suspension (200 N/m) with deflection compensation | Soft path: writing-force changes move the ink (ball slides s·cos θ), ~1 mm pen-down hooks; stiff path trades this for more normal-force modulation. Sweep: [`results/sim/design_sweeps.json`](../results/sim/design_sweeps.json), `fig_axial_sweep.png` — simulation | provisional | EXP-B06 hand normal compliance (γ); EXP-B08 ink vs modulated force |
| DEC-007 | **Cross-strip gimbal** (BeCu 0.05 mm strips) at the pivot. Spiral-arm diaphragm axial suspension **behind** the pivot, so the whole lever slides and the lever arm does not change with axial deflection (κ_s = 0). | Wire flexures; axial suspension in the carrier | Wire pivots fail on stress or buckling; short diaphragms over-stressed; gimbal 177/82 MPa, buckling margin 19 (`results/mechanics/flexure_calc.json`) — calculation. κ_s = 1 caused a load-dependent lever gain (sim) | accepted for Rev A | Flexure fatigue coupons (EXP-M02) |
| DEC-008 | Carry two **product-path candidates** alongside the Rev A research pen: (D) nose skid with constant-force nib (0.07 W); (E) slow zero-hold bias actuator (0.02 W). | Rev A architecture as the product | Rev A holding power 0.48 W at the design point, at the moving-coil thermal limit (`results/thermal/thermal.json`, `electronics/README.md`) — calculation | open | EXP-H03 skid feel and smear study |
| DEC-009 | **Frequency-gated authority**: cancellation only when the tracked tremor frequency is ≥ a per-user gate (default 7.5 Hz). Below it, assistance is guided-mode or training only. | Always-on cancellation; band-pass cancellation | Intended writing has ~17 % of velocity energy in 4–7 Hz (COR-28); estimators help only above ~8 Hz (COR-11); band-pass harms writing below 6 Hz (ratio 1.24 at 6 Hz, 160 µm distortion) — simulation, synthetic writing | provisional; the gate is fragile (distortion 5–45 µm across small plant changes) | EXP-E01 estimator bake-off on recorded writing |
| DEC-010 | **nRF5340** for the research pen (BLE, USB, QSPI, 128 MHz M33 with FPU, SAADC). STM32U5 is the fallback if the SAADC or PWM limits bite. | STM32U5, nRF52840, nRF54L | COR-13; sampling plan fits (`results/electronics/drive_sense.json`) — calculation. Its single SAR ADC limits dual-edge current sampling to 160 kS/s aggregate (VERIFY 200 kS/s limit) | accepted for Rev A | Bring-up step 7 timing |
| DEC-011 | **No measured-force contact feedforward** in the stage servo; integral action carries the contact load. The filtered path stays for bench experiments. | Unfiltered, first-order-filtered, or second-order-filtered feedforward | The feedforward from the delayed axial-force signal made the nib bounce in 3/160 Monte Carlo samples (unfiltered) and 6/160 (filtered, with tremor) at low altitude. Removing it fixed all cases for +9 µm servo error (`sim/diag_ff_chatter.py`, `sim/diag_ff_options.py`, `results/sim/ff_options.json`) — simulation | accepted | Bench servo tests with real paper stacks |
| DEC-012 | **Coil wound to 6 Ω** (Kf 0.739 N/A) to match the single-cell supply. **40 kHz centre-aligned PWM** with the current loop at the PWM rate. | 11 Ω winding at 20 kHz; boost converter for VMOT | 11 Ω is voltage-limited at 3.3 V for 3.7 % of the thermally allowed envelope; 20 kHz gives ±100 mA ripple and a 1.3 kHz current loop (`electronics/calcs/drive_sense.py`, ngspice `results/electronics/spice_drive_stage.json`) — calculation, simulation | accepted | EXP-B03 coil build (R, L, Kf measured) |
| DEC-013 | **Handwriting recognition uses an off-the-shelf on-device recogniser first** (ML Kit Digital Ink class), behind a recogniser interface. No custom recognition training until licences and accuracy are established. | Train on IAM-OnDB and similar | Common datasets are non-commercial (COR-22); ML Kit publishes no accuracy numbers — literature | provisional | Recognition evaluation on writer-disjoint data (app/README) |
| DEC-014 | **Electronics packaging is open.** The Rev A circuit as drawn needs 779 mm² of courtyard against 517 mm² available in the CAD envelope. The Rev A.1 package plan on a 41 mm board with a pouch cell reaches 0.65 density (HDI). A two-board split is the alternative. | — | `electronics/gen/placement_study.py`, `results/electronics/placement_study.json` — calculation | open (E-1) | Layout attempt; pouch-cell supplier drawing |
| DEC-015 | **Firmware safety rules**, independent of mode. Hardware interlock ACT_EN = REQ·FAULT_N·NOCHG. Never de-energise the stage in contact except on hard faults. Frozen stage sensor detected within 5 ms. Assistance fades on low battery, heat or lost optical tracking before pen-up. | Firmware-only protection | Failure cases F1–F7 (`results/sim/sweeps/summary.json`): power loss in contact moves the ink ~0.8 mm; a frozen Hall sensor drives the stage to its stop — simulation | accepted | Bench fault-injection tests (validation/bench_protocols.md EXP-F01/F02) |
| DEC-016 | A **learned disturbance predictor** is deployed only if, on held-out recorded writers, it beats the Kalman oscillator and BMFLC at matched false-correction. Until then the Kalman estimator is the product default, and ML stays behind `ml_guard`. | Ship a learned predictor first | Synthetic-data results in `results/ml/`; no real recordings yet — simulation | provisional | EXP-E01 on EXP-H01 recordings |
| DEC-017 | **Immutable original stroke layer; derived layers carry provenance; local-first notes.** AI output is stored only as a cited `ai_summary` layer. | Editable ink; cloud-first | Report s19 (retained, audit.md); `docs/icd.md` §4.5 — design check | accepted | Privacy review |

## Decision records for the three decisions made in this iteration

### DEC-011: contact feedforward removed

- **Context.** The stage servo originally added a contact-load feedforward, F = N̂ cos θ with N̂ = F_ax / sin θ from the axial-force signal (1 kHz, 1 ms delay).
- **Evidence (simulation, model M1).**
  - The v0.3 Monte Carlo (160 samples) returned no evaluable ink in 3 samples because the powered pen bounced (> 1000 contact transitions in 3 s). A rigid or unpowered pen with the same parameters did not bounce.
  - Mechanism: the feedforward acts on the stage as −cos²θ·K_n·H(s), where K_n is the paper in series with the axial path and H(s) the delayed force-sensing path. Its quadrature part is a negative damper at the stage-against-paper mode (~180 Hz); the analytic estimate is 10.4 against 5.4 N·s/m of servo damping.
  - A second-order 60 Hz filter fixed the no-tremor cases. With tremor, 6/160 samples still bounced; they disappeared only with the feedforward removed.
- **Consequences.** Neutral servo error rises 20 → 29 µm RMS and device distortion 51 → 59 µm (tuning seeds). The oracle bound improves slightly (0.175 → 0.128 at 9 Hz); Kalman results are unchanged.

### DEC-012: 6 Ω winding and 40 kHz PWM

See `electronics/README.md`, "Decisions carried by the circuit". The parameter file moved to v0.4.0, and every simulation was re-run on it.

### DEC-014: packaging open

The placement study is an area calculation from library courtyards, not a layout. It shows the as-drawn Rev A circuit cannot fit the CAD envelope. The options and their consequences for mass, centre of mass and battery are listed in `electronics/README.md` (open issue E-1) and `mechanics/README.md`.
