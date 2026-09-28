# Active stabilisation pen: engineering programme

A pen that actively moves its ink tip, and steadies its own body, to counter unwanted hand motion, supports people with Parkinson's-related writing difficulty, assists everyday handwriting and drawing, and captures notes with source-grounded AI assistance.

This repository holds the research and development package: the audit of the source report, evidence, requirements, physics, simulation, mechanics, electronics, firmware, ML, app, validation plans and decisions.

**Evidence status.** Everything here is **calculation, simulation, literature or proposed design**. Nothing has been built, and there are **no physical or human measurements**. Every figure carries a stamp saying what it is, and every result file records its code revision, parameter version, seeds and command.

## Start here

| If you want… | Read |
|---|---|
| **The current design, Rev H (bigger grip):** what is inside, how the tip and the pen body are moved, how much it helps each condition, what to measure first | [`docs/revH_concept.md`](docs/revH_concept.md); the 3-D explainer [`viewer/explainer/`](viewer/explainer/build.py) |
| The recommended route: what to build, where custom hardware and our own data are unavoidable, what evidence each benefit needs | [`docs/recommendation.md`](docs/recommendation.md) |
| The slim pencil variant (Ø8.9 × 166 mm): exact forces, mechanisms with existing parts, what to make, AI guidance and autocorrect, sim-to-real, 3D replay | [`docs/pencil_concept.md`](docs/pencil_concept.md), [`viewer/`](viewer/build.py) |
| The verdict on the source report | [`docs/audit.md`](docs/audit.md), [`docs/corrections.csv`](docs/corrections.csv) |
| Current state, blockers and next actions | [`CHECKPOINT.md`](CHECKPOINT.md) |
| The system and its budgets | [`docs/architecture.md`](docs/architecture.md), [`docs/icd.md`](docs/icd.md) |
| Why things are the way they are | [`docs/decisions.md`](docs/decisions.md) (DEC-001…033) |
| What the simulations say | [`docs/sim_report.md`](docs/sim_report.md) |
| What may be claimed for each feature | [`docs/features.md`](docs/features.md) |
| The riskiest open questions | [`docs/research_questions.md`](docs/research_questions.md) |
| How to proceed | [`docs/plan.md`](docs/plan.md), [`validation/`](validation/README.md) |

## Key conclusions so far

1. **The transverse load is dominated by N·cos θ, not friction** (COR-01). Holding power (F/(n·K_m))² therefore rules out direct drive at the tip (about 12 W). A front-pivot lever with a rear annular actuator brings it to about 0.5 W in contact at the design point. That is **above the 0.412 W a moving coil can dissipate continuously** (within it on average at 65 % pen-down). Skid and bias-actuator variants remain the product path (DEC-003, DEC-008; route in `docs/recommendation.md`).
2. **Intent separation, not mechanics or latency, limits free-writing assistance.**
   - In simulation, the mechanism could remove 70–80 % of tremor-induced ink error (oracle bound 0.22–0.32).
   - The causal estimators tested give no benefit below ~9 Hz on synthetic handwriting.
   - Guided (template) tasks work in simulation: circle 443 → 163 µm, spiral 382 → 112 µm.
   - Whether real handwriting is more separable is the decisive open question (EXP-H01 → E01).
3. **Parkinson's writing difficulty is mainly micrographia.** A ±0.5 mm stage cannot enlarge letters. PD support means cueing, feedback and practice, measured for lasting unassisted benefit, not immediate correction (DEC-002).
4. **Design errors found and fixed in this package** (calculation and simulation):
   - Nib-bounce instability from a measured-force contact feedforward (DEC-011).
   - Voltage-limited 11 Ω coil, rewound to 6 Ω (DEC-012). A later, fuller headroom check found 6 Ω still binds at 3.3 V in the hot, high-force corner (0.5 % of the thermal envelope) and 4 Ω does not; open until EXP-B03 winds both.
   - A thermal model left at the old 0.45 mm air gap: the moving-coil allowable is 0.412 W, not 0.455 W (v0.4.3).
   - Interface errors found by the firmware review: the ICD printed the inverse Jacobian and the wrong actuator-force sign (fixed in ICD v1.3; the simulator and firmware were right). Tilt-dependent γ is now computed from a stored stiffness ratio.
   - An axial suspension layout that closes the actuator gap: the refill now slides in the carrier (DEC-007 rev.).
   - A nose that touched the paper at every writing angle: the refill point now protrudes 5 mm (DEC-018).
   - Inertia understated by a point-mass approximation: 13.7 g, above the 12 g requirement.
   - The research circuit does not fit the 29 mm board in the CAD envelope. The package plan and a 41 mm board fit at 0.65 density (DEC-014, open).
5. **A pencil-sized version is possible only if the writing force bypasses the nib** (`docs/pencil_concept.md`, DEC-019 to DEC-022).
   - A nose skid carries the user's force and a light spring sets the nib force. The stage then holds 0.17 N instead of 0.76 N.
   - Four custom 2.6 mm piezo plates fit the 7.9 mm bore. They give ±277 µm of stroke under load at zero static power, in 12.2 g of CAD before wiring. A voice coil that fits would need 2.4 W.
   - The stroke margin is thin (±162 µm at −20 % tolerance). Tremor estimation is the same open problem as in Rev A. Re-optimising the stage with real parts (P0.2: custom plates, thicker leaves, charge-recovery drive) gives 212 µm in the worst corner instead of none and 2.7 h of assist instead of 0.5 h (`docs/opt_hardware.md`, DEC-030).
   - **The user has since chosen a bigger grip (DEC-029): the primary concept is now Rev H, where the whole front of the pen tilts to move the tip about ±3 mm. The pencil is the slim variant.**
   - The skid causes touchdown and lift tails: about 1.1 mm of extra ink per stroke. A tilt-adaptive front stop cuts this to 0.33 mm. A stage feed-forward in firmware, tuned by adjoint gradients and Bayesian search, then brings the ink at the transitions to 0.005–0.008 mm per stroke; bounce is its open risk (`docs/opt_touchdown.md`, DEC-026).
   - Paper capture needs a ≥ 120 Hz page sensor that does not yet exist at this size.
   - AI helps as a digital autocorrect (word errors 32 % → 10 %). Physical guidance toward AI-predicted letters does not help free writing: a correct prediction is already about 300 µm off, beyond break-even. Guidance toward known templates does help.
   - Weights, gyroscopes or a motorised grip inside the 20 g pencil leave 0.85–0.97 of the ink error with perfect knowledge, against 0.18–0.43 for the nib stage (`docs/inertial_stabilisation.md`). At the user's direction the bigger-grip pen has active inertial control of its body (item 7, DEC-033).
   - The accelerometer now drives the tremor tracker directly, with gyroscope compensation. It leaves 0.78 of the tremor-band error on average, against 0.85 before, and 0.58–0.71 at 8–12 Hz once calibrated per writer. Separating tremor from writing is still the limit (`docs/sensor_fusion_ai.md`, DEC-025). Re-optimising its settings with exact adjoint gradients gives 0.86 instead of 0.91 for the default set, and 0.67 instead of 0.79 at 8–12 Hz; learned trackers were not better at equal false correction (`docs/opt_tracker.md`, DEC-028).
6. **The simulator can be calibrated from the planned bench work, and the twin experiments say how well** (`docs/sim_to_real.md`, DEC-023).
   - On 15 blind simulated plants the protocol experiments recover every model parameter to ≤ 1.6 % in about 1.5 h of bench time per build.
   - The calibrated twin then predicts the oracle ratio within ±0.1 for 14 of 15 plants, against 4–5 uncalibrated.
   - The same work found that the frozen tremor estimator degrades on randomised plants (median ratio 0.88 at 9 Hz), and that the existing Monte Carlo lets the controller see true plant values.

7. **Rev H, the bigger-grip pen, is now the primary design** (DEC-029, DEC-032, DEC-033; `docs/revH_concept.md`). All simulation and calculation.
   - Ø22 × 170 mm, 75 g, or 103 g with the inertial module. The fingers hold a fixed sleeve whose front ring rests on the paper and carries the writing force. The whole front of the pen (the nose, holding the refill) tilts on a flexure gimbal, driven by two pairs of flat voice coils, so the ink tip moves up to ±3 mm: ten times the pencil's stage. About 0.08 W, about 27 h of writing.
   - A rear inertial module (19.8 g tungsten slug moved ±2.75 mm on two axes) pushes the whole pen against the shake. On top of the nose it adds 6–17 % further reduction depending on the grip. It is fitted in the first prototype; the product keeps it if the grip measurement (EXP-I01) and the bench test (EXP-I06) confirm ≥ 10 %. A plain weight made the ink worse in 38–42 % of 8–12 Hz cases and is not used.
   - With perfect knowledge of the tremor the nose removes 87–99 % of the ink error up to 2 mm, and the app reads 98–100 % of words. With today's accelerometer tracker: 22–50 % at 8–10 Hz (words read at 10 Hz, 1 mm: 54 → 87 %), and nothing at 4–6 Hz. **The tracker, not the mechanism, is the limit** (`docs/opt_inertial.md`, `docs/handwriting_outcomes.md`).
   - Parkinson's shrinking letters: a "write bigger" vibration cue kept letters at 5.2 mm instead of 4.2 mm, if people respond as small studies suggest. Poor handwriting: guidance brings the ink 24–61 % closer to the target letters while it is on (partial nose guidance 35 %, reading slightly better; full guidance reads worse); lasting benefit needs a human study (EXP-W04). Dyslexia: guidance never turned a wrong letter into the right one; the help is the app's spelling check, read-back and clean copy.
   - An optional desk board moves a permanent magnet under the paper to pull the pen along whole letters (0.4 N cap; `docs/guidance_board.md`, DEC-031).

**Where the simulations are, and what the optimisation studies found:** [`docs/optimisation.md`](docs/optimisation.md). The 3D replay page is `viewer/index.html` (`python3 viewer/build.py --variant Q`); the Rev H explainer is `viewer/explainer/index.html` (`python3 viewer/explainer/build.py`).

## Completion table

States: **drafted** (text or design, not run) · **executable** (code runs, results depend on unverified inputs) · **executed** (run here; outputs in `results/`) · **hardware pending** · **measured** (none yet).

| Brief area | Deliverable | State | Evidence |
|---|---|---|---|
| 1 Research | Audit and recalculation of the report (37/37 numbers reproduce; 28 corrections) | executed | `analysis/audit_recalc.py` → `results/audit/` |
| 1 Research | Evidence ledger (384 sources, 8 streams) and synthesis | drafted | `docs/evidence.csv`, `docs/research_synthesis.md` |
| 1 Research | Ranked research questions with decisive experiments | drafted | `docs/research_questions.md` |
| 2 Mechanics | Parametric CAD (Rev A, Rev A.1) with interference checks, STEP, drawings | executed | `mechanics/cad/`, `results/cad/` |
| 2 Mechanics | Flexures, tolerance stacks (S1–S6), mass/CoM budget, configuration trade | executed | `mechanics/`, `results/mechanics/`, `results/trade/` |
| 2 Mechanics | Stage-A loaded bench rig (dimensioned concept CAD) | executed (design) · hardware pending | `mechanics/cad/bench_rig.py`, `results/cad/drawing_bench_rig.png` |
| 3 Electronics | KiCad 8 schematic: 11 sheets, regenerated deterministically; ERC 0 errors; netlist cross-check pass; PDF; BOM with VERIFY/SELECT | executed | `electronics/kicad/`, `electronics/bom_revA.csv` |
| 3 Electronics | Drive/sense calculations, including the supply-headroom assessment of the winding (6 Ω binds at 3.3 V in the hot, high-force corner; 4 Ω does not); ngspice drive stage incl. fault; placement study | executed | `electronics/calcs/`, `electronics/spice/`, `results/electronics/` |
| 3 Electronics | PCB layout and fabrication outputs | **not started** (blocked by DEC-014) | `electronics/README.md` E-1 |
| 4 Simulation | Coupled pen–hand–paper model M1: 12 verification tests; tuning/test split; grid, Monte Carlo, sensitivity, failures, design sweeps, frequency-gate diagnostic | executed | `sim/`, `results/sim/`, `docs/sim_report.md` |
| 4 Simulation | EM field models; thermal network with a two-node reduction for the firmware governor | executed | `analysis/`, `results/em/`, `results/thermal/` |
| 4 Simulation | Validation plan per model | drafted | `docs/physics.md` (table), `validation/` |
| 5 ML | Synthetic data pipeline with writer-disjoint splits; six conventional baselines tuned on validation; causal TCN; int8 quantisation (no loss); C export bit-exact with the Python reference, also on emulated Cortex-M33; MCU budget (exported model without f_est: 16.2 k MAC, 7.3 kB weights, 0.58 kB RAM); model and dataset cards; 22 tests | executed (synthetic only) · real data pending (EXP-H01) | `ml/README.md`, `results/ml/` |
| 6 Firmware | C control core: 40 kHz current loop, 2 kHz stage task, Kalman and band-pass estimators, guided mode, Jacobian with tilt-dependent γ, two-node thermal governor, safety state machine, ML guard (ICD §5 v1.2), calibration records, ICD log writer. Parameters generated from the YAML with a freshness check; golden vectors and replays from the simulator; 60 test cases (1120 checks) pass on host (ASan/UBSan) and on emulated Cortex-M33; nRF5340 image builds (32.3 kB flash). Register-level drivers are stubs marked VERIFY | executed (host, emulator, build) · hardware pending | `firmware/README.md`, `results/firmware/` |
| 6 Product | ICD log reader/writer with CRC and resync (parses the firmware's golden log with zero issues); immutable content-addressed note store with provenance-carrying derived layers; segmentation; SVG rendering; recogniser interface (on-device adapter specified); FTS5 search with stroke citations; grounded assistant that refuses unsupported, uncited or clinical answers; capture-fidelity analysis; digital autocorrect as a derived layer; 147 tests | executed (synthetic data) · real recogniser pending | `app/README.md`, `results/app/` |
| 7 Validation | 57 experiments with criteria (42 bench/offline, 15 human) with procedures, equipment, uncertainty and decision rules; 295 acceptance criteria (94 requirement, 42 derived, 159 hypothesis; checker passes); prototype stages A–D with gates; human study plan separating immediate assistance from lasting improvement; review of 33 document inconsistencies, now resolved or recorded | drafted · hardware and participants pending | `validation/README.md` |
| Pencil | Pencil-class concept: CAD (Q and L layouts, fit checks, STEP, drawings), mechanism study (forces, 12 mechanisms, drive power, drop), pencil model P1 (skid, spring-loaded refill, piezo stage; exact match with M1 when locked), page-sensor rate study, touchdown tails | executed (design, calculation, simulation) · hardware pending | `docs/pencil_concept.md`, `docs/pencil_mechanisms.md`, `mechanics/cad/pencil_revP.py`, `sim/pencil/`, `results/pencil/` |
| Pencil | AI prediction and guidance (text predictor, style templates, stroke continuation, closed loop on P1 and M1, deployment and ICD proposal) and app autocorrect | executed (synthetic data) · people pending (EXP-A02/A03) | `docs/ai_guidance.md`, `aiguide/`, `results/ai/` |
| Pencil | Inertial and pivot stabilisation study: hand-pen model H1 with pen tilt in a two-zone grip; weights, gyroscopes, CMGs, reaction wheels, grip sleeve, passive pivots | executed (simulation, calculation) · grip measurement pending (EXP-I01) | `docs/inertial_stabilisation.md`, `sim/handpen/`, `results/pencil/inertial*.json` |
| Pencil | Sensing and AI estimation: IMU parts and lever arm, acceleration-domain Kalman, WFLC/BMFLC, learned GRU, template prior, 20 s personal calibration, closed loop on P1 | executed (simulation) · real data pending (EXP-H01/E01) | `docs/sensor_fusion_ai.md`, `fusion/`, `results/fusion/` |
| Pencil | Slim pencil hardware optimisation (P0.2): differentiable design model (exact against design.py and the CAD), adjoint gradients, Bayesian optimisation and CMA-ES over real and supplier-standard parts, finalists ranked in P1, BOM, CAD with STEP | executed (calculation, simulation) · custom plates to quote (EXP-Q04) | `docs/opt_hardware.md`, `opt/hardware/`, `results/opt/hardware.json` |
| Pencil | Tracker optimisation: differentiable accelerometer Kalman filter (PyTorch, and a hand-written numba adjoint), tuning of all 23 settings by backpropagation through time, Pareto front against false correction, learned trackers on the tremor band, per-writer gradient tuning; recorded-data pipeline | executed (simulation) · real writing pending (EXP-E01) | `docs/opt_tracker.md`, `opt/tracker/`, `results/opt/tracker.json` |
| Pencil | Touchdown and lift optimisation: stage feed-forward, stop margin and servo retune; adjoint gradients of a differentiable reduced model (torch), ParEGO Bayesian optimisation and CMA-ES on P1; faster slide-sensor option | executed (simulation) · bench pending (EXP-Q08) | `docs/opt_touchdown.md`, `opt/touchdown/`, `results/opt/` |
| Pencil | 3D replay page of the simulated pencil with generated tables | executed | `viewer/` (`python3 viewer/build.py`) |
| Rev H | Bigger-grip pen: tip design A against B, adjoint design of the nose actuator, ParEGO tracker for ±3 mm, rear inertial module, gyroscope and passive-weight options, neural reaction-mass controller, envelope tiers, CAD with STEP (with and without the module), BOM, power; H1 extended with regression tests | executed (calculation, simulation) · grip and bench pending (EXP-I01, I05, I06) | `docs/opt_inertial.md`, `opt/inertial/`, `mechanics/cad/revH_pen.py`, `results/opt/inertial_opt.json`, `results/revH/` |
| Rev H | Handwriting outcomes per condition (essential tremor, Parkinson's micrographia, poor handwriting, dyslexia) in model HW1, cross-checked against P1; scorer for real recordings | executed (simulation) · people pending (EXP-W01…W05) | `docs/handwriting_outcomes.md`, `handwriting/`, `results/handwriting/` |
| Rev H | Guidance board: architecture comparison, magnet force maps, stage, Hall sensing, guidance control, CAD, BOM | executed (calculation, simulation) · hardware pending (EXP-G01…G07) | `docs/guidance_board.md`, `board/`, `mechanics/cad/guidance_board.py`, `results/board/` |
| Rev H | 3-D explainer: components, how it moves, before/after writing, evidence level of every number; smoke test | executed | `viewer/explainer/` (`python3 viewer/explainer/build.py`) |
| 4 Simulation | Sim-to-real: virtual bench with instrument models, blind identification of 15 plants in protocol order, bench-time study, calibrated-twin prediction gap, model-form diagnostics, piezo hysteresis identification, domain randomisation, hardware-in-the-loop specification; 22 tests | executed (twin experiments) · bench pending | `docs/sim_to_real.md`, `validation/sim_to_real.md`, `s2r/`, `results/s2r/` |
| — | Engineering recommendation: route, conflicting targets with limiting calculations, custom hardware, AI data needs, evidence per benefit | drafted | `docs/recommendation.md` |
| — | Interfaces, decisions, plan with effort ranges (100–174 pw) and quotation list, environment lock | drafted | `docs/icd.md`, `docs/decisions.md`, `docs/plan.md`, `ENVIRONMENT.md`, `requirements.txt` |

## Reproduce

Environment: [`ENVIRONMENT.md`](ENVIRONMENT.md) (Python 3.11 with `requirements.txt`; KiCad 8.0.9; ngspice 42; arm-none-eabi-gcc 13.2; QEMU 8.2).

```bash
python3 -m pip install -r requirements.txt
python3 analysis/audit_recalc.py                    # report recalculation
python3 -m pytest sim/tests -q                      # simulator verification
bash sim/run_all.sh                                 # simulation evidence chain (10-25 min)
python3 mechanics/cad/pen_revA.py --variant A1      # CAD, mass, interference
python3 mechanics/tolerance_analysis.py && python3 mechanics/mass_budget.py
python3 electronics/gen/design_revA.py              # schematic; then kicad-cli ERC/netlist (electronics/README.md)
python3 electronics/calcs/drive_sense.py
(cd electronics/spice && ngspice -b drive_stage.cir && python3 plot_drive_stage.py)
```

Pencil concept:

```bash
python3 mechanics/cad/pencil_revP.py --variant Q      # pencil CAD, fit checks, mass (also --variant L)
python3 analysis/pencil_mechanisms.py                 # forces, mechanisms, power (about 90 s)
python3 -m sim.pencil.run_study                       # pencil model P1 (about 95 s); tests: python3 -m pytest sim/pencil/tests -q
python3 -m sim.pencil.diag_touchdown_tails            # touchdown tails and the tilt-adaptive stop
bash aiguide/run_all.sh                               # AI prediction, guidance and autocorrect (about 15 min)
bash s2r/run_all.sh                                   # sim-to-real twin experiments (about 30 min on 2 processes)
python3 -m sim.handpen.run_study                      # weights, gyroscopes and pivots (about 5 min); tests: python3 -m pytest sim/handpen/tests -q
python3 -m fusion.run_study --workers 2               # accelerometer tracker and AI estimation (tests: python3 -m pytest fusion/tests -q)
python3 -m fusion.viz                                 # 3D replay of the tracker
python3 -m opt.hardware.run_study                     # slim pencil hardware optimisation (P0.2); tests: python3 -m pytest opt/hardware/tests -q
python3 -m opt.tracker.run_study                      # tracker tuned by adjoint and learned trackers (3-4 h on 2 cores); tests: python3 -m pytest opt/tracker/tests -q
python3 -m opt.touchdown.run_study                    # touchdown feed-forward and servo optimisation (about 1.5 h on 2 processes; --quick smoke run); tests: python3 -m pytest opt/touchdown/tests -q
python3 viewer/build.py                               # 3D replay page from the results
```

Rev H (bigger grip):

```bash
python3 -m opt.inertial.run_study                     # nose, tracker, inertial module (about 35 min; --quick about 2 min); tests: python3 -m pytest -q opt/inertial/tests
python3 mechanics/cad/revH_pen.py [--addon]           # Rev H CAD, fit checks, STEP (--addon: with the inertial module)
python3 -m handwriting.run_study                      # before/after writing per condition (--quick smoke run); tests: python3 -m pytest -q handwriting/tests
python3 -m board.run_study                            # guidance board (about 2-3 min); tests: python3 -m pytest -q board/tests
python3 mechanics/cad/guidance_board.py               # board CAD and drawing
python3 viewer/explainer/build.py                     # 3-D explainer page from the results
```

Firmware, ML and app have their own build and test commands in their READMEs.

## Repository map

`config/parameters.yaml` holds every parameter with unit, range, status and source (v0.4.4); `config/pencil.yaml` overlays it for the pencil concept (P0.1.2). The directories:

| Directory | Contents |
|---|---|
| `stabpen/` | Shared physics |
| `analysis/` | Audit, EM, thermal, trade |
| `sim/` | Coupled simulator (M1 in `sim/pensim/`, pencil model P1 in `sim/pencil/`) |
| `mechanics/` | CAD, flexures, tolerances, mass |
| `electronics/` | Schematic, calculations, SPICE, BOM |
| `firmware/` | Embedded control core |
| `ml/`, `data/` | Learned predictor pipeline, schemas |
| `app/` | Companion software |
| `aiguide/` | AI prediction, templates and guidance studies (pencil concept) |
| `fusion/` | Sensor models and tremor trackers |
| `opt/` | Optimisation studies: touchdown, tracker, slim hardware, Rev H inertial |
| `handwriting/` | Handwriting outcomes model HW1 and the recording scorer |
| `board/` | Guidance board study |
| `s2r/` | Sim-to-real: virtual bench, identification, calibrated twin |
| `viewer/` | 3D replay page; `viewer/explainer/` the Rev H 3-D explainer |
| `validation/` | Experiments and studies |
| `docs/` | Everything written |
| `results/` | Generated outputs with provenance |
