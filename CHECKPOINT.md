# Checkpoint - engineering update, 2026-09-30

Start with [the implemented improvement report](docs/engineering_improvement_2026_09_30.md) and the [publication handoff](docs/reviews/2026-09-30_astra_handoff.md). The branch was fetched and fast-forwarded to `4ad62b6acdcda1fa1102362f32780168297f5bb3`; earlier local review files were preserved and reapplied. The new code, CAD, research audits and experiment results are included in the Astra publication commit directly above that base. The report's statements about uncommitted work describe its original local delivery snapshot. The preservation stash remains available locally.

The current work develops a conditional 24 mm / 1.5 mm fine-stage candidate, a separately resized 20 mm / 1.059 mm candidate, and a desk-supported five-bar for accepted whole-letter motion. It also repairs causal sensing, sampled servo gains, RL evaluation, accepted-text execution, numerical friction integration and application correction provenance. No mechanism was manufactured, no target board was tested, and no participant outcome was measured.

The decisive remaining gaps are loaded force/friction and guide life, current-loop and contact identification, page registration through lift, complete packaging, and actual benefit under human grip. The grounded 20/20 unloaded ink/tracking result does not extend to either tested resisting grip, and no unloaded trace also passes the selected actual acceleration/jerk comparisons. No learned policy qualified for adoption. Detailed limits, frozen protocols, test logs and reproduction commands are in the report and `results/improvement/`.

**Round 5 (the lead, 30 September 2026)** develops the pass further: the lead's review and decisions DEC-070…074, the nib optimised (study N), a moving-paper platen (study P), users and market (study U), the first bench build (study H) and a re-baseline of earlier results (study X). See §10.

## Historical checkpoint, 29 September 2026

The record below is preserved for its original assumptions and experiment history. Its statements about the primary design, completed checks and regenerated results describe that earlier state, not the current improvement work.

Use this file to resume work without losing assumptions. Branch: `claude/pensive-shannon-wzm6ls`. Parameter file: **v0.4.4**; all simulation, trade, thermal and drive results are regenerated on it. The pencil-class concept has its own overlay, `config/pencil.yaml` **P0.1.2** (§7). **The primary design is now Rev J, which acts at the tip, the heel and the tail (§9); Rev H, the bigger-grip pen, is §8.**

## 1. What exists and what actually ran

| Area | Ran here | Not run or not possible here |
|---|---|---|
| Audit | Recalculation of all 37 report numbers (all reproduce); 28 corrections with severity | — |
| Evidence | 795 ledger rows; two decision-driving sources lead-verified against the primary text | Full-text access failed for some sources (listed in the ledger's limitations column) |
| Simulation | M1 coupled model, 12 tests passing; estimator tuning on seeds 100–105; nominal benchmark; 12-seed × 9 f × 3 amplitude grid; 160-sample Monte Carlo + rank sensitivity; failure cases F1–F7; design sweeps; κ_s comparison; guided-mode evaluation; contact-feedforward diagnosis; frequency-gate diagnostic | Validation against hardware (all EXP-B*) |
| Mechanics | CAD Rev A and A.1 (interference-free at full travel); flexure calculation; tolerance stacks S1–S6; mass budget; stage-A rig CAD with platen-clearance check; drawings | Physical parts; FEM of flexures and actuator |
| Electronics | KiCad 8 schematic generated deterministically; ERC (0 errors, 1 accepted warning); netlist cross-check pass (102 nets / 492 pins); BOM; drive/sense calculations with the winding headroom assessment; ngspice transient incl. coil short; placement study | PCB layout (DEC-014 open); datasheet checks behind 45 VERIFY and 3 SELECT BOM lines |
| Firmware | C control core with safety, logging, calibration and ML guard; parameters generated from the YAML with a freshness check; 60 test cases (1120 checks) on host (ASan/UBSan) and emulated Cortex-M33; nRF5340 image links (32.3 kB flash, 29.4 kB RAM) | Execution on nRF5340 hardware; cycle-accurate timing; register-level drivers (VERIFY); IMU, optics, USB, flash and BLE drivers |
| ML | Synthetic data pipeline with writer-disjoint splits; six conventional baselines; causal TCN; int8 C export without f_est, bit-exact on 20 000 windows (16.2 k MAC, 7.3 kB weights); 22 tests | Any real-data training (no recordings exist) |
| App | ICD log reader with CRC and resync; immutable note store with provenance; search with stroke citations; grounded assistant with refusal rules; capture-fidelity analysis; 137 tests | On-device recogniser (adapter specified only) |
| Validation | 200 experiments with criteria (146 bench/offline, 54 human); 687 acceptance criteria against 190 requirements, generated into the protocols (checker passes); prototype stages and claim gates; human study plan | Every experiment and study |

## 2. Numbers the next session must not lose

All are calculation or simulation unless stated otherwise.

- **Load.** Transverse load = N·cos θ + friction terms (COR-01).
  - Static hold at N = 1 N: 0.82 / 0.64 / 0.25 N at 35° / 50° / 75°.
  - Copper loss at the same points: 0.80 / 0.49 / 0.08 W.
  - Moving-coil allowable is 0.412 W average (120 °C coil limit, 0.50 mm air gaps), and 70 % of the envelope (θ 35–75°, N 0.2–2 N, μ 0.05–0.35) stays within it in continuous contact.
  - Coil thermal path: 145 K/W coil to structure, 157 K/W steady to ambient; Rev A coil 96.6 °C at the design load.
  - Supply headroom: at 3.3 V the 6 Ω winding cannot hold 0.5 % of the thermally allowed envelope (hot, high-force corner); 4 Ω can (DEC-012 revisited, EXP-B03).
- **Actuator.**
  - Lever: n = 3.17, L1 = 12 mm.
  - K_m = 0.293 N/√W (analytic field model, with the 0.50 mm gap).
  - Winding: 6 Ω, K_f 0.717 N/A, L ≈ 175 µH (unmeasured).
  - Drive: 40 kHz PWM; current loop crossing at 2 kHz with 55.8° phase margin (2.3 kHz is the 50° limit); design hold current 0.335 A.
- **Estimation.**
  - Oracle bound 0.22–0.32 across 4–12 Hz.
  - Kalman 1.03–1.14 at 4–9 Hz and 0.85 at 12 Hz. Since v0.4.2 the balanced and assertive objectives select the same set. At 0.15 mm tremor it adds error at every frequency.
  - Band-pass 1.1–1.5 below 7 Hz.
  - Distortion without tremor: Kalman 100 µm on 12 seeds (55 µm on 4), band-pass 168 µm. REQ-CTRL-005 (≤ 50 µm) is violated.
  - The selection is fragile: 3–6 % of the tuning objective separates an inert set from the active one, and the v0.4.2 plant change flipped it (`docs/sim_report.md` §3.2).
  - Guided mode: circle 443 → 163 µm, spiral 382 → 112 µm path distance.
- **Mechanism.** Device distortion (neutral vs rigid pen) ≈ 59 µm. Axial path 2 kN/m. γ ≈ 0.19 at 50°.
- **Budgets.**
  - Tip-equivalent inertia 13.7 g (requirement ≤ 12 g).
  - Mass 33.2 g with polymer rear barrel (requirement ≤ 35 g).
  - Centre of mass 76 mm (requirement ≤ 70 mm).
  - PCB courtyard: 779 mm² as drawn vs 517 mm² available; 0.65 density on a 41 mm board with the package plan.
- **Failures.** Power loss in contact moves the ink ≈ 0.8 mm. A frozen Hall sensor puts the stage on its stop. Coil-short trip 8.8 µs; VMOT off 22.6 µs (ngspice).

## 3. Provisional assumptions currently carried

- **Hand.** Literature impedance (HAP-26), measured in-plane and without the hand resting on paper. γ is computed from assumed normal compliances.
- **Paper contact.** Stiffness 5×10⁴ N/m; μ 0.15; LuGre parameters assumed. Friction turned out to drive estimator performance (ρ 0.51).
- **Optics.** Latency 2 ms, noise 3 µm, 1 kHz on paper at the nib (unmeasured; EXP-S01).
- **Writing and tremor.** Synthetic handwriting and tremor. Real separability is unknown.
- **Cell.** 200 mAh ≥ 5 C pouch; no supplier drawing yet.
- **nRF5340 DEC-pin values and RF matching.** Not retrieved from Nordic this session; marked VERIFY.

## 4. Blockers (exact measurement or external action)

| # | Blocker | What resolves it |
|---|---|---|
| 1 | Transverse load and friction on real paper and ink | **EXP-B01/B02**: 6-axis F/T sensor under a platen; θ 35–80°, N 0.2–4 N, 8 directions, 1–100 mm/s, 3 papers × 3 inks |
| 2 | Whether tremor is causally separable from real writing | **EXP-H01** (ethics approval, then instrumented passive pen, n ≈ 20 per group), then **EXP-E01** estimator bake-off |
| 3 | Loaded cancellation and ink tolerance | Stage-A rig build (`mechanics/cad/bench_rig.py`), then **EXP-B09** and **EXP-B08** |
| 4 | Actuator K_m, R, L, thermal path of a moving coil, and the winding (6 Ω binds at 3.3 V in the hot high-force corner; 4 Ω does not) | **EXP-B03** coupons wound at 4 Ω and 6 Ω (K_f, R, L, coil-to-structure R_th); **EXP-B07** thermal; bench headroom at 3.3 V with a hot coil |
| 5 | Near-nib optical sensing on paper | **EXP-S01**; sensor access under NDA |
| 6 | Packaging (DEC-014) | Decide between a 41 mm board with pouch cell and a two-board split; pouch-cell supplier drawing; HDI layout attempt |
| 7 | Datasheet checks behind the VERIFY/SELECT lines | Datasheet review, with Nordic reference circuitry for the nRF5340 |
| 8 | Centre of mass and inertia above requirements | CFRP carrier; lighter stator or shorter barrel; confirm the CoM requirement against ordinary pens (EXP-M03, H02) |
| 9 | Stage-loop phase margin 35.3° against REQ-CTRL-002's 40° (unloaded model; firmware loop test) | Identify the loaded plant (**EXP-B05**), then retune: lower position bandwidth or add phase lead, and re-run the simulation chain |
| 10 | Intent separation in the controller itself: the tracker-driven frequency gate also opens on writing (14 % of tremor-free handwriting, 68 % of the feature course) | Implement the separate spectral detector with hysteresis (DEC-009 revisit); test it in simulation, then in **EXP-E01** on recorded writing |

## 5. Next actions, in order

For Rev A. The Rev H order is in §8.

1. Build the stage-A rig. Run EXP-B01 and B02; re-fit the contact and friction parameters (`config/parameters.yaml`, status → measured); re-run `sim/run_all.sh`.
2. Submit the EXP-H01 ethics application. Build the passive instrumented pen from the Rev A sensing subset.
3. Commission the Rev A electronics at bench scale on the rig; bring-up steps 1–12 (`electronics/README.md`).
4. Run EXP-B09 and B08. Decide the Phase B gate, DEC-008 (product configuration) and DEC-014 (packaging).

## 6. How to resume

- **Python.** `python3 -m pip install -r requirements.txt`, then `python3 -m pytest sim/tests -q`. The first run compiles numba (about a minute); later runs hit the cache.
- **KiCad 8 on Ubuntu 24.04 without `add-apt-repository`.**
  - Add the Launchpad key `FDA854F61C4D0D9572BB95E5245D5502FAD7A805` to `/usr/share/keyrings/kicad8.gpg`.
  - Add `deb [signed-by=/usr/share/keyrings/kicad8.gpg] https://ppa.launchpadcontent.net/kicad/kicad-8.0-releases/ubuntu noble main`.
  - Run `apt install kicad`.
  - Copy `/usr/share/kicad/template/{sym,fp}-lib-table` to `~/.config/kicad/8.0/`.
- **Long simulation runs.** Do not edit `sim/`, `stabpen/` or `config/` while `sim/run_all.sh` runs: worker processes re-import modules.
- **Generated files.** Regenerate from their scripts rather than editing outputs: `electronics/kicad/*`, `results/*`, `mechanics/mass_budget.csv`.
- **Dependency order after a parameter or interface change.** Parameters feed the simulator, trade, thermal and drive calculations, and the firmware generator also fingerprints the ICD and the schematic generator. Run, in order:
  1. `bash sim/run_all.sh` (if simulator inputs changed);
  2. `python3 analysis/config_trade.py && python3 analysis/thermal.py && python3 electronics/calcs/drive_sense.py`;
  3. `make -C firmware params vectors test arm`. `make test` fails if any generated input is stale.
- **Firmware and ML.**
  - Firmware: `make -C firmware test` (host, ASan/UBSan, about 15 s) and `make -C firmware qemu` (emulated Cortex-M33, about 25 min).
  - ML: `python3 -m pytest ml/tests -q`; the C export is `python3 -m ml.export_c` (see `ml/README.md`).

## 7. Pencil-class concept, AI guidance and sim-to-real (added 2026-09-27)

The request was for an Apple-Pencil-class version (Ø8.9 × 166 mm) that still corrects the ink, with AI prediction, app capture, exact forces and mechanisms, a 3D simulation and sim-to-real work. Integrating report: `docs/pencil_concept.md`. 3D replay: `viewer/` (published as a private artifact).

**What exists and ran** (all calculation or simulation):
- `config/pencil.yaml` P0.1.2.
- CAD `mechanics/cad/pencil_revP.py`, Q and L layouts: fit checks, STEP, drawings.
- Mechanism study: `analysis/pencil_mechanisms.py`, 12 candidates.
- Pencil model P1: `sim/pencil/`, 10 tests, exact match with M1 when locked.
- Page-sensor rate study.
- Touchdown-tail study.
- AI prediction, guidance and autocorrect: `aiguide/` (32 tests) and `app/penapp/autocorrect.py` (app 147 tests).
- Sim-to-real twin experiments: `s2r/`, 22 tests.
- Decisions DEC-019 to DEC-023; requirements REQ-PNC-001 to 008.

**Numbers not to lose:**
- **Forces.** The stage design load is 0.170 N per axis behind the skid, against 0.758 N with a conventional nib. It scales with the axial nib force F_c (0.15 N assumed; EXP-Q02).
- **Stage.** Four custom 2.6 × 36 × 0.67 mm piezo plates, push-pull pair per axis:
  - lever 1.363;
  - ±277 µm stroke at the design load, ±162 µm at −20 % tolerance, ±48 µm at 35°;
  - 0.329 N at the nib; 192 Hz; zero static hold power.
- **Voice coil at the 7.9 mm bore.** K_m 0.080 N/√W, so holding 0.170 N costs 2.4 W against 0.31 W allowed.
- **CAD.** 12.2 g before wiring and margin; centre of mass 88 mm from the nib; all checks pass for Q. L fails on the snubber web.
- **Battery, 90 mAh.**
  - Recording only: 4.1 h.
  - Assist with 2 × DRV2700: 0.83 h.
  - Assist with a charge-recovery driver: 2.7 h, or 3.4 h at 0.3 µm Hall noise.
- **Simulated effect, pencil model P1.**
  - Oracle ratio: 0.19–0.26 at 0.1 mm tremor; 0.20–0.46 at 0.3 mm, with 16–65 % of the time at the travel limit.
  - Kalman: 0.85–0.92, and only at 8–12 Hz.
- **Touchdown tails.** About 1.1 mm of extra ink per stroke against a rigid pen with the tilt-range front stop; 0.33 mm with a tilt-adaptive stop at 0.3 mm margin (oracle ratio 0.24 → 0.30).
- **Page sensor for guided mode.** ≥ 120 Hz at ≤ 10 ms is needed (guided/neutral 0.42), against 0.76 at 30 Hz. No fitting part was found.
- **AI.**
  - Digital autocorrect: word errors 32 % → 10 % at 7 % recognition errors; ≤ 0.1 % of correct words changed.
  - Physical guidance toward AI-predicted letters gives no net benefit: break-even is 265 µm (P1) and a correct letter in the user's style is about 300 µm off.
  - Wrong templates stay at the 0.40 mm stop; 2.2 % of letters are misread at full authority, 0.3 % gated.
  - The phone must predict two letters ahead to meet the 0.3 s lead.
- **Sim-to-real.**
  - Identification recovers parameters to ≤ 1.6 % (95th percentile) in about 1.5 h of bench time per build.
  - The calibrated twin predicts the oracle ratio within ±0.1 for 14 of 15 plants, against 4–5 uncalibrated.
  - The frozen Kalman set degrades to a median of 0.88 at 9 Hz on randomised plants.
  - The existing Monte Carlo conflates plant and controller values.

**Blockers and next actions:**
1. EXP-Q02: lowest usable nib force per ink. Every stage load scales with it.
2. EXP-Q04: custom-width plates. Stroke, strength and drop with snubbers.
3. EXP-Q05: a low-power driver for 2–2.6 µF. It decides assist time.
4. EXP-Q06/Q07: loaded 1- and 2-axis stages.
5. EXP-Q08: touchdown tails with a tilt-adaptive stop (SQUIGGLE-class trim motor from the IMU tilt).
6. EXP-H03: skid feel.
7. Page sensor at ≥ 120 Hz in the nose (EXP-S01 on a candidate).
8. EXP-A02: people's letters against personal templates, before any physical AI-guidance claim.
9. Freedom to operate: the template pipeline is close to PAT-01 claim 15; attorney review.
10. Simulator: split `core.simulate` into a plant step and a controller tick. Redo the Monte Carlo and the estimator selection under fixed firmware on randomised plants (`docs/sim_to_real.md` §8, items 12–14).

**Added 2026-09-28: accelerometer, AI and inertial help** (`docs/pencil_concept.md` §11).
- **Inertial helpers.** Hand–pen model H1 (`sim/handpen/`, 21 tests), with perfect knowledge of the tremor at 0.3 mm:
  - the best cap device within 20 g (a 5.15 g tungsten slug on 3 axes) leaves 0.85–0.97 of the ink error and takes half the cell;
  - gyroscope pairs leave 0.87–0.92, at 25 g and 0.34 W;
  - the stage alone leaves 0.18–0.43;
  - passive pivots trade writing for tremor (net 0.93–1.25);
  - a grip sleeve would hold 0.74 N (2.1 W).

  The study recommended nothing inertial in the pen (DEC-024); at the user's direction that is reopened (see below). The grip's slide/tilt split r_rot is unmeasured (EXP-I01).
- **Sensing and estimation.** `fusion/` (25 tests); `sim/pencil` gained `Controller(mode="external")` and filtered housing acceleration. The acceleration-domain Kalman filter with gyroscope compensation, on the P1 test grid:
  - mean tremor-band ratio 0.78, against 0.85 for the frozen filter;
  - personalised by a 20 s calibration: 0.58–0.71 at 8–12 Hz, 0.3 mm;
  - robust set: 5 µm distortion, 21 µm on sharp writers (the frozen filter moved them 123 µm);
  - perfect tremor-band knowledge would give 0.26.

  The template prior changed nothing. The GRU's gain is simulated friction drift. In P1 most of the tremor-induced error is a friction drift (316 against 173 µm) (DEC-025; DEC-020 and DEC-021 updated).
- **Validation.** EXP-I01…I04 and 12 criteria: 268 criteria, 43 experiments.
- **Next.**
  - EXP-B06 + I01: grip split.
  - EXP-H01 + I02: record raw IMU (proposed ICD 0x07), ρ, and the target groups' normal writing.
  - EXP-E01: AKF sets and calibration on real writing.
  - EXP-B01/B02 with superimposed vibration.
  - EXP-S01: IMU latency.

**Added 2026-09-28: touchdown optimisation** (`docs/opt_touchdown.md`, `opt/touchdown/`, 29 tests).
- Most of the tail left by the adaptive stop is the stage yielding to the contact-load step. A stage feed-forward (pre-position in the air, cancel the measured slide, switch the load bias at contact with integrator hand-over, Hall early detection) brings tail ink to 0.005 / 0.008 / 0.000 mm per stroke at 35 / 50 / 75° (SIM, test seeds). The structure was chosen with adjoint gradients of a differentiable reduced model and the 11 parameters by ParEGO on P1 (DEC-026).
- Servo retune (DEC-027, proposed; defaults unchanged): tracking 19.3 → 12.5 µm at 136 → 117 mW, margins kept.
- Open: bounce (1.7 against 1.2 contact transitions per pen-down), the axial sensor's latency, tilt changes during a run (P1 has constant θ). Validation: AC-Q08-01 split to tail ink; AC-Q08-04…07; 272 criteria.

**Added 2026-09-28: tracker optimisation** (`docs/opt_tracker.md`, `opt/tracker/`, 15 tests).
- The AKF was made differentiable (matches the numba filter to 1e-13) with a hand-written adjoint (2e-11 against autograd, 40× faster). Gradient descent on the random search's own robust objective gives the proposed default (DEC-028): tremor-band ratio 0.86 against 0.91, 0.67 against 0.79 at 8–12 Hz, sharp-writer shift 18 against 21 µm (SIM, test seeds).
- The adjoint sweep maps the trade-off: no setting has both the smooth-writing benefit (0.78) and ≤ 30 µm on sharp writers. The band-target GRU and the AKF + learned gate are not shipped; per-writer gradient tuning stays an option (about 2 %).
- Next: EXP-E01 on recorded writing through `opt/tracker/realdata.py`.

**Added 2026-09-28: slim pencil hardware optimisation** (`docs/opt_hardware.md`, `opt/hardware/`, 14 tests). P0.2 (DEC-030, proposed): custom PICMA-class plates 3.23 × 39.8 × 0.96 mm, C17200 leaves 38 µm, gimbal at 65.5 mm, LT8365 charge-recovery drive, 2 × DRV5055A4. Worst-case stroke 0 → 212 µm, resonance 192 → 213 Hz, assist life 0.50 → 2.73 h, mass 14.6 g (CALC); P1 worst corner 0.375 → 0.281 (SIM). It is now the slim variant: the user chose a bigger grip (DEC-029, Rev H).

**Added 2026-09-28: inertial control of the pen body, at the user's direction.** DEC-024 is superseded by DEC-033; the study is finished and its results are in §8.

**Resume.**

```bash
python3 mechanics/cad/pencil_revP.py --variant Q
python3 analysis/pencil_mechanisms.py
python3 -m sim.pencil.run_study
python3 -m sim.pencil.diag_touchdown_tails
python3 -m sim.handpen.run_study
python3 -m fusion.run_study --workers 2
python3 -m opt.hardware.run_study
python3 -m opt.tracker.run_study
python3 -m opt.touchdown.run_study
bash aiguide/run_all.sh
bash s2r/run_all.sh
python3 viewer/build.py
```

- The pencil model reads the CAD summary, so re-run the CAD first after any geometry change.
- `sim/pencil` and `aiguide` keep their numba caches in their own `build/` directories.

## 8. Rev H, the bigger-grip pen (added 2026-09-28)

The user chose a bigger grip, asked for inertial control of the whole pen and not only the nib, and asked how the pen would change handwriting for Parkinson's, poor handwriting and dyslexia. Integrating report: `docs/revH_concept.md`. 3-D explainer: `viewer/explainer/` (published as a private artifact).

- **Design (DEC-029, DEC-032; proposed).** Ø22 × 170 mm, 75 g. The fingers hold a fixed sleeve; its C-shaped front ring rests on the paper and carries the writing force. The nose (titanium refill carrier, PEEK nozzle, aluminium rear arm) tilts on a laser-cut two-axis spring-steel gimbal at 45 mm, so the ball moves ±3 mm (stop 3.5 mm). The refill slides on a 0.15 N constant-force spring. Four NdFeB magnets on the arm and four flat voice coils at 79 mm drive it (Km 0.47 N/√W at the magnets, 0.36 at the tip; 0.84 N peak, 0.21 N continuous at the tip). A TMAG5273 3-D Hall reads the nose at 10 kHz; LSM6DSV16X IMU; nRF54L15 with 2 × DRV8214; EEMB LIR14500. 0.081 W, about 27 h (CALC).
- **Inertial module (DEC-033).** 19.8 g tungsten slug (ASTM B777), ±2.75 mm, two axes, 27.8 g added, ≤ 0.051 W; fitted in the first prototype at the user's direction. On top of the nose: a further 6 / 17 / 17 % at r_rot 0.3 / 0.5 / 0.7 (SIM). The product keeps it if EXP-I01 and EXP-I06 confirm ≥ 10 %. No passive weight (it worsened 38–42 % of 8–12 Hz cases), no gyroscope pair (81 g, 0.42 W).
- **Results (SIM).** With perfect knowledge of the tremor the nose leaves 0.17–0.18 of the ink error (words read 98–100 %). With the tracker: 0.64 / 0.70 / 0.76 at 8–12 Hz, 1–2 mm; words read at 10 Hz, 1 mm 54 → 87 %; nothing at 4–6 Hz (the tracker locks onto the second harmonic). The tracker is the limit, not the mechanism.
- **Handwriting (SIM, `docs/handwriting_outcomes.md`).** Parkinson's: a vibration cue keeps the x-height at 5.2 mm instead of shrinking to 4.2 mm, if people respond as small studies suggest. Poor handwriting: partial nose guidance brings the ink 35 % closer with slightly better reading; full guidance reads worse. Dyslexia: no guidance turned a wrong letter into the right one (0 %); the app flags misspelt words when it knows the target.
- **Guidance board (DEC-031).** CoreXY stage under 3 mm glass with a K&J D88-N52 magnet head; a D42-N52 disc (0.75 g) in the pen's keel, 16.5 mm behind the ball; 1.2 N available, 0.4 N cap; about 25 Hz. Open: the keel limits tilt to ≥ 51°; up to 48 µm crosstalk at the nose Hall; board commands below about 3 Hz; about 1 N extra normal pull.
- **AI help for severe tremor (DEC-035, `docs/ai_severe_tremor.md`).** Letter prediction does not steer free writing: as a tracker prior it closed 0 % of the gap at 1–2 mm, as nose guidance 1 % (SIM). The app's clean copy reads 97 % of words at 1–2 mm (digital only). A severe-tremor tracker setting closes 55 % of the gap but moves tremor-free writing by 263 µm: test it offline on recordings (AC-W02-03).
- **Front end closed (DEC-034).** The first layout drew the skid ring about 1.5–3 mm below the paper, and its 5.5 mm contact radius left no room for the ring's wall. `opt/inertial/front_end.py` sizes it over 35–75°: contact radius 6.75 mm, nozzle face in the ring plane, refill slide about 13.5 mm on a constant-force strip spring (new design item). The dynamics change by at most 0.004 in ratio (SIM), so the study's results stand; layout, CAD and the explainer were regenerated.

**Next for Rev H, in order.**
1. EXP-I01: grip split r_rot on a Ø22 handle (decides where the inertial module acts, and whether it stays).
2. EXP-I05: the active nose on the bench (stroke, force, bandwidth, Hall, writing force unchanged).
3. EXP-H01 recordings, then EXP-I07 / EXP-W02: the tracker on real tremor writing (decides the stabiliser claim and whether 4–6 Hz is reachable), with the severe-tremor setting offline (AC-W02-03); EXP-A03 with the clean copy on the same recordings (AC-A03-04/05).
4. EXP-I06: the inertial module on a hand simulant with the nose on.
5. EXP-W01…W05 and EXP-G01…G07 as the prototype and the board become available.

**Resume.**

```bash
python3 -m opt.inertial.run_study          # about 35 min; --quick about 2 min
python3 -m opt.inertial.front_end --sens   # front-end closure (CALC) and its H1 sensitivity check, about 1 min
python3 mechanics/cad/revH_pen.py --addon
python3 -m handwriting.run_study           # results/handwriting/_cache is regenerable and git-ignored
python3 -m board.run_study
python3 -m aiprior.run_study               # about 20 min; --quick about 5 min
python3 mechanics/cad/guidance_board.py
python3 viewer/explainer/build.py          # smoke test: viewer/explainer/smoke_test.js (Playwright; see its README)
python3 validation/check_criteria.py
```

## 9. Rev J, a pen that acts at the tip, the heel and the tail (added 2026-09-29)

The user asked for far more physical effect on the writing: more advanced tip manipulation, movement and tilt of the whole pen, a clever inertial system (for example at the end of the pen), a pen that can "somewhat write for you" while held, better algorithms and AI (smoothing, prediction, adaptation, RL), and more realistic physics simulation with proper sim-to-real practice. Plan: `docs/revJ_plan.md`. Plain-words account: `docs/revJ_concept.md`. Integrated design: `docs/revJ_design.md`. Decisions DEC-036…044.

- **Physics that decided the architecture (CALC).** A handheld pen can push the hand only against a mass inside it, against the hand, or against the paper. A reaction mass gives F = m(2πf)²X: at writing frequencies (below about 5 Hz) the best 45 g end-cap moves the ink at most 0.21 mm and a gyroscope 1.06 mm, against 2 mm needed (SIM, study K). The paper, through a wheel at the heel, gives μ·N ≈ 0.3–0.6 N (friction ASSUMPTION, EXP-D01), and a relaxed hand moves about 0.35 mm per 0.1 N.
- **Round 1 (five parallel studies, all executed; SIM and CALC).**
  - *N, nose v2 (DEC-036):* short-arm gimbal 76.5 mm behind the ball, 2 × 2 N52 checkerboard across a spherical gap; ±6.0 mm guaranteed over 35–75° (6.57 mm at 50°); pen lift with an electro-permanent brake and latch; autowrite of a known text 99.2 % of letters and 100 % of words read up to 1 mm of tremor.
  - *D, heel drive (DEC-037):* 2 mm steered and driven wheel; steer-only by default; driven only in lead-through and autowrite (DEC-039); force cap min(0.5 N, 0.8 μ̂ × load) with a lateral release. PD loops 0.78 → 0.99 of the target height; tracing 582 → 76 µm with the nose, but letters read 92 → 79 %.
  - *K, end-cap (DEC-038):* 30.4 g tungsten, ±4 mm, 5 Hz flexures, detachable; +8 / 18 / 20 % at grip splits 0.3 / 0.5 / 0.7 on top of the nose; a fixed mass gives 17 / 12 / 4 % but worsens 29–42 % of hard cases. It cannot steer letters.
  - *L, AI and control (DEC-042, DEC-043):* tremor-line detector with hysteresis plus a fixed-lag Kalman (RTS) listening tracker: 1–2 mm at 6–10 Hz, 830 → 430 µm (Rev H tracker 627 µm), words 31 → 74 %. Causal TCN 278 µm, shadow mode only. No delayed ink; RL offline only (arbitration α = α_max · c_conf · c_need · c_agree); word completion and labelled style synthesis in the app.
  - *V, simulator v2 (DEC-040):* MuJoCo 3.6 with the H1 contact law at 25 µs; on H1's 56 test cases the uncorrected ink error is within 3.1 % in every case, the perfect-knowledge ratio within ±0.03 in 52 and the tracker ratio within ±0.05 in 50 (misses: the Rev H tracker's frequency lock); convergence, energy and gyroscope checks; MyoSuite impedance; Gymnasium environment with domain randomisation. Synthetic writers are at half adult speed with about ten times the measured 8–12 Hz content: refit on recordings (EXP-V03). Context of use COU-1 (ranking designs) until EXP-V01/V02/V04/V05.
- **Rev H corrections (DEC-041).** The nose actuator's force constant is 0.19 N/√W by an image-method model, not 0.47 (REQ-RVH-003/004 and AC-I05-01/04 marked contested); the ink-force spring needs a fatigue rating; a free refill follows lifts; the refill's front stop must follow the nose (REQ-RVH-008).
- **Round 2 integration (DEC-044; CALC).** Ø24 mm; contact radius 11.65 mm, wheel at 12.0 mm; sleeve front Ø23.3 mm; 144.7 mm and 87.0 g, or 165.7 mm and 129.2 g with the end-cap (target ≤ 120 g); refill slide 26.6 mm; 38 fit checks pass.
- **Round 3, Rev J.1 fixes (DEC-045; CALC, `docs/revJ1_design.md`, `revj1/`, `results/revJ1/`).** 143.9 / 161.9 mm, 84.3 / 112.7 g (base / with end-cap); 44 fit checks pass.
  - Gimbal: study N's 50 µm strips buckle at 16.4 N under a 12.4–22.2 N magnet pull; strips in tension fail fatigue; 75 µm strips in compression with shock stops: buckling 55.3 N, Goodman factor 2.0.
  - Battery: the tremor-line detector (DEC-042) needs the page sensor, so it stays on as a PMW3610-class die (1.3–1.9 mW; 1 kHz accuracy on paper unknown, EXP-J10; PMW3360 fallback for autowrite). Electronics 34–60 mW from datasheets. Steady 1 mm tremor 8.5–9.7 h; lead-through 7.5–8.8 h; autowrite 6.5–7.4 h (1 mm), 3.8–4.1 h (2 mm).
  - Heat: 0.1 mm graphite sheet in the shell wall; web 35.9 °C at 1 mm tremor in a 30 °C room (limit 43 °C, AMF-35).
  - End-cap: 9 mm tungsten slug, 29.6 g, 21 mm; +5.6 / 16.8 / 18.3 % at splits 0.3 / 0.5 / 0.7 (SIM, H1).
  - Clear 15 mm PC window over the top 240° of the sleeve; heel motors 10 mm further back (detent 0.66 × friction, free space).
- **Independent review (2026-09-29, `docs/reviews/`).** Commissioned by the user outside the repository. Its central finding is confirmed by the lead and by sim2j: the refill spring's static side load at the ball (F_c·cot θ) makes the C1S nose's holding loss 4.717 / 1.628 / 0.166 W at 35 / 50 / 75° (CALC). DEC-036 is reopened; the battery and heat conclusions of DEC-032, DEC-044 and DEC-045 are suspended. The adopted order is: balanced nib (study B), then a motorised collar (study W), then a tail only if it beats a locked mass, then a grounded surface; language help runs in parallel (study S). Rigs for the review's gates G1–G5 are in study M. `docs/claims_register.md` lists every headline claim with its status.
- **Open problems (the next session must not lose these).**
  1. **Nose-coil power (confirmed).** The static side load dominates: 1.6 W at 50° for the C1S nose (CALC; about 1.1 W in sim2j's writing run, SIM, plus a 0.7 W servo-noise artefact). Rev J's battery and heat claims stay suspended. **Fixed on paper** by the balanced nib B1 (study B, DEC-050) and laid out as Rev K (study K, DEC-062…066): 145.1 mm, 66.4 g, 23.5–48.6 h per charge with 1 mm tremor (CALC). Unproven until EXP-J17 (c), EXP-T07/K22 (the buildable coil), EXP-K20 (ball guide) and EXP-K21 (C17200 wire leads).
  2. Low-power page sensor accuracy at 1 kHz on paper (EXP-J10) and the detector on its stream (EXP-L01 extension).
  3. The pull's size (12.4–22.2 N, ideal iron; EXP-J01) and the shock stops (not designed).
  4. The TCN may fail REQ-ML-001 (34.8 µm on the worst writer).
  5. Autowrite with a pen lift needs a freedom-to-operate review against an actuated-nib pen that scribes predefined characters (LIT PAT-01).
  6. The synthetic writers are unrealistic; every tremor-separation result waits on EXP-H01 recordings (round 4 study R brings in public recordings meanwhile).
  7. **No causal tracker helps on real tremor yet** (studies R and E, DEC-060): perfect knowledge would make about 7 of 10 words readable at the severe size, against 0.5 today. Study F set the target (DEC-067: at most about 0.55 mm left at the tip; the best tracker leaves 1.12 mm) and located the gap in separating tremor from writing, not in prediction (DEC-069). The next candidate (a network trained on real recordings, DEC-061) needs new held-out recordings for EXP-E10: EXP-R06's registrations (IAM-OnDB, PaHaW) or EXP-R01.
  8. **Rev K's failing fit checks** (`docs/revK_design.md` §4): the page sensor tracks only ±0.2 mm of lift (REQ-BNIB-017 asks 2 mm; EXP-T04); the touchdown travel before the balance returns is 0.98 mm (REQ-BNIB-002 relaxed by DEC-064 unless a float brake is fitted); the grip sits 3.3 mm closer to the paper at 35° than an ordinary pen (EXP-K24); the fresh ink is seen within 1 mm in 19 % of cases (Rev J.1 47 %; EXP-J15).
  9. **Beryllium.** Rev K's C17200 wire leads must be soldered or crimped, never welded or ground without fume extraction (AMF-18, DEC-063); a beryllium-free alternative is still to be found.
  10. **Reach for severe tremor** (study F, SIM): with Rev K's ±1 mm nib even perfect knowledge gains only 1.4 words at the severe class (DEC-055 needs 2); ±1.5 mm gains 3.2; a real tracker would need about ±2–3 mm. Rev K makes no severe-tremor legibility claim for its nib; EXP-E23 checks the B1 nib's own reach in sim2.
- **Done in round 4 (2026-09-29/30):** sim2j (whole Rev J pen in simulator v2), studies R (real recordings), E (tracking real tremor), S (spelling, prediction, clarity), W (shifting the whole pen), B (the balanced nib), M (measurement rigs), K (the Rev K layout) and F (the readable target); validation passes 5–11; the explainer (v10).
- **Running.** See §10 (round 5). Study F finished on 2026-09-30 (`docs/readable_target.md`, DEC-067…069).

**Next, in order (`validation/prototype_stages.md` §0; the Rev J list in `docs/revJ_concept.md` §7 is superseded).**
1. DAQ-1 bring-up, then rig R9 (gate G1): EXP-T01, T02 (friction; the lowest ink force, which sets B1's power) and EXP-J17 (the static side load; part (c) the counter-face bench, with EXP-K23's head mock-up).
2. Rig R10: page sensing on paper (EXP-T04, T05), including the lift range Rev K fails on paper.
3. People, as soon as ethics allows: EXP-H01 recordings (with T06), EXP-V07.
4. Gate G2 coupons: EXP-T07 with Rev K's buildable coil (EXP-K22), C17200 wires carrying current (EXP-K21), the ball thrust guide (EXP-K20), EXP-B25 and B28.
5. Gates G3/G4: the one- and two-axis nib on R13 (EXP-T10…T15): servo bandwidth, the stuck-ball mode, heat.
6. Offline, in parallel: EXP-E10 on new recordings (needs EXP-R06's registrations or EXP-R01); EXP-E13 and E11 (study F); EXP-K25 (Rev K in sim2j).

**Resume.**

```bash
python3 -m drive.run_study            # about 50 min; --quick about 5 min
python3 -m endcap.run_study           # about 75 min; --quick about 2.5 min
python3 nose2/run_study.py            # about 2-3 h; --quick about 1.5 min
python3 -m ai2.run_study --workers 1  # about 4 h; --quick about 40 min
python3 -m sim2.run_study             # about 3 h; --quick
python3 -m revj.run                   # about 25 s
python3 mechanics/cad/revJ_pen.py     # --no-endcap for the base pen
python3 -m pytest -q drive/tests endcap/tests nose2/tests ai2/tests sim2/tests revj/tests
python3 validation/check_criteria.py --check
```

The studies' dependencies are pinned in `requirements.txt` (mujoco 3.6.0, MyoSuite 2.12.2, gymnasium 1.2.3, stable-baselines3 2.9.0); see `ENVIRONMENT.md`.

## 10. Round 5: developing the independent pass further (added 2026-09-30)

The user asked for the independent engineering pass (commit `e09a15f`, `docs/engineering_improvement_2026_09_30.md`) to be developed further, in full. The lead's review is in `docs/reviews/2026-09-30_lead_review_of_astra.md`: the full suite was rerun on Linux (886 passed, 4 slow skipped, 1 failure). The failure was a defect in the pass's writer-split check, now fixed and covered by a test. Decisions DEC-070…099. Five studies ran in parallel, each writing only to its own folders.

- **The lead's decisions on the pass (DEC-070…074).**
  - Causal sensing is the default, and closed-loop results computed with ideal sensing are suspended as device evidence until study X reruns them.
  - The fine nib makes local corrections; whole words need a grounded stage or a moving page.
  - Two nib candidates go to the bench.
  - No learned policy drives the nib.
  - Corrections are proposed, then explicitly accepted.
- **Study N, the nib optimised** (DEC-080…084; CALC; `docs/nib_optimisation.md`, `nibopt/`).
  - *One matched model* for every nib: the force constant at its weakest point × 0.7. The ball's writing drag makes about two thirds of the heat.
  - *Rev K's B1, matched:* about 65 mW typical and 0.168 W at worst, 18.1–46.5 h per charge. Its wire anchor fails fatigue (Goodman 0.71).
  - *The recommended balanced candidate:* ±1.50 mm, Ø24.0 mm, 157.1 mm, 70.4 g; 37.9 mW typical and 0.107 W at worst; skin 33.7 °C; 22.8 h at the conservative end.
  - *Magnets and reach limits:* two magnet arrays are needed beyond ±1.25 mm; ±2 mm needs a body of at least 27.5 mm.
  - *Length:* REQ-RVK-001's 150 mm stays until a 157 mm dummy pen has been tried in the hand (lead note on DEC-083).
  - *Next:* the actuator coupon, EXP-NB01.
- **Study P, the moving-paper platen** (DEC-085…089, proposed; SIM with real recorded inputs on the tuning split; `docs/platen_concept.md`, `platen/`).
  - *Reach:* with perfect knowledge the ±5 mm platen leaves 0.02 mm and 8.3 words of 10 are read, against the ±1.5 mm nib's 0.67 mm and 4.0 words.
  - *The estimator still decides:* study E's frozen design leaves 1.04 mm (0.7 words). A tip camera with perfect separation leaves 0.09 mm (7.9 words).
  - *Accepted writing:* with the pen docked, 20/20 "se" and 19/19 "library". With the pen held, only a firm, calm hand succeeds.
  - *The largest uncertainty:* the ball's friction coupling between the page and the pen (EXP-PL03).
  - *Cost and size:* BOM USD 895–2,160; retail USD 1,500–3,000 (ASSUMPTION); a 380 × 300 mm desk device.
- **Study U, users and market** (DEC-090…094; LIT and CALC; `docs/market_and_users.md`).
  - *Handwriting is still used:* 62 % of GB adults aged 65+ write lists by hand weekly.
  - *Tremor affects the alternatives too:* 80 % of a tremor charity's surveyed members had writing affected and 54 % typing.
  - *No shown benefit yet:* the active pen has 0 users with a shown benefit.
  - *Plan:* discovery first, with the go/no-go criteria GNG-1…10 fixed in advance. Typing and dictation are mandatory comparators. A measuring pen and a practice tool come before the active pen.
- **Study H, the first bench build** (DEC-095…099; `docs/bench_build_plan.md`, `results/benchbuild/`).
  - *Cost:* DAQ-1 and R9 cost USD 4,350–7,750 over 4 weeks; all five builds cost USD 14,000–35,400 over 12 weeks.
  - *Side load:* the calculated side load, about 49–51 mN, favours the 1.059 mm nib unless measured lower. Study N's two-array ±1.5 mm design passes at matched loads; DEC-096 decides on the measured loads.
  - *Fatigue coupons:* driven at no more than 0.2 × their first mode.
  - *Safety:* beryllium handling rules (DEC-097), and the five-bar is used on the bench only (DEC-099).
- **Study X, the re-baseline** (DEC-075…079): running. It reruns sim2j's cards, B1 in sim2, study F's reach check and the page-sensor rows under causal sensing, the corrected loads and page model v2.
- **Validation.** Pass 13 (U and H) is done; pass 14 (N, P and DEC-070…074) is running.
- **Open problems changed by round 5** (the numbers refer to §9).
  1. *Nose-coil power:* study N's balanced candidate replaces Rev K's B1 as the next nib. It is unproven until the coupon and rig experiments EXP-NB01…09.
  2. *Reach for severe tremor (10):* two answers exist on paper. Study N's ±1.5 mm nib fits in 24 mm (157 mm long), and study P's platen removes the reach limit at a desk. Both still wait on problem 7, the estimator.
  3. *New:* how far a moving page drags a held pen through the ball (EXP-PL03). This decides the platen's accepted-writing mode.
  4. *New:* no benefit has been shown to any user. Discovery (EXP-U01…U06) and the comparison study (EXP-U07) come before any product claim (DEC-090…092).

**Next, in order (round 5; `validation/prototype_stages.md` §0 for the gates).**
1. Discovery, in parallel with the bench because it is cheap: the survey and interviews, EXP-U01…U05, scored against GNG-1…5.
2. DAQ-1 and rig R9 (G1): EXP-T02 (the minimum ink force), EXP-T01 and EXP-J17 (c). The measured side load decides DEC-096 between the two nib candidates.
3. EXP-NB01: the balanced candidate's actuator coupon (force map, K_m at its weakest point), then the G2 coupons.
4. Rig R10 (page sensing), the EXP-H01 recordings and EXP-E10 on new recordings.
5. For the platen, EXP-PL03 first: a sliding page under a held pen with a force sensor, before any platen is built.
