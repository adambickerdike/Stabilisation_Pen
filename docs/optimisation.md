# Where the simulations are, and how they were optimised

**Status: proposed designs, optimised in simulation only (2026-09-28).** Nothing here has been measured on hardware or on people. Labels:
- **SIM**: an executed simulation on synthetic writing and tremor;
- **CALC**: a calculation;
- **MFR**: a manufacturer statement, with its ledger id in `docs/evidence.csv`;
- **ASSUMPTION**: an input nobody has measured.

## 1. Where to see them

- **3-D explainer of the bigger-grip pen, Rev H** (`viewer/explainer/index.html`; rebuild with `python3 viewer/explainer/build.py`; published as a private artifact). It shows every component in 3-D, how the nose and the inertial module move, and before/after writing for each condition.
- **3D replay page** (`viewer/index.html`; rebuild with `python3 viewer/build.py --variant Q`; published as a private artifact). It has four parts:
  - recorded simulation runs replayed in 3D: the pen, the hand's shake, the nib stage, the ink against the intended letters, and the forces;
  - a gallery of every study's charts;
  - the optimisation results;
  - the engineering tables.
- **The simulators** are Python in this repository. Each re-runs with one command (README.md, "Reproduce"):

| Model | What it simulates | Code | Results |
|---|---|---|---|
| Pencil model P1 | The pencil writing on paper, in 25 µs steps: hand, nose skid, spring-loaded refill, two-axis piezo stage with its Hall servo, sensors, paper contact and friction | `sim/pencil/` | `results/pencil/` |
| Hand–pen model H1 | Pen tilt in a two-zone grip; weights, gyroscopes and pivots | `sim/handpen/` | `results/pencil/inertial*.json` |
| Sensors and trackers | 6-axis IMU and page-sensor models; Kalman trackers, learned networks, the 20 s calibration | `fusion/`, `opt/tracker/` | `results/fusion/`, `results/opt/` |
| AI guidance | Letter prediction, style templates, guided writing, autocorrect | `aiguide/` | `results/ai/` |
| Design models and CAD | Loads, stroke, resonance, stress and fit of the stage; the pencil's CAD | `sim/pencil/design.py`, `analysis/`, `mechanics/cad/` | `results/pencil/`, `results/cad/` |
| Twin experiments | A virtual bench that calibrates the simulator before hardware exists | `s2r/` | `results/s2r/` |
| Rev H pen in H1 | The bigger-grip pen: fixed sleeve with a skid ring, the nose tilting on its gimbal, the voice coils, the rear inertial module, in a two-zone grip | `sim/handpen/`, `opt/inertial/` | `results/opt/inertial_opt.json`, `results/revH/` |
| Handwriting model HW1 | 2-D letters and words with tremor, shrinking letters, poor letter shapes and spelling errors; ink error, and letters and words read by the app's recogniser | `handwriting/` | `results/handwriting/` |
| Guidance board | Magnet force maps, the XY stage, how far a hand gives way, Hall sensing, guided practice | `board/`, `mechanics/cad/guidance_board.py` | `results/board/`, `results/cad/` |
| Rev A model M1 | The earlier, larger voice-coil pen | `sim/pensim/` | `results/sim/` |

## 2. What was optimised, and how

| Study | What it optimises | Methods | Report |
|---|---|---|---|
| Touchdown and lift | Stage feed-forward law (11 parameters), front-stop margin, stage servo (5 parameters) | Adjoint gradients of a differentiable reduced model (PyTorch, backpropagation through time) to choose the law's structure; ParEGO Bayesian optimisation and CMA-ES on the full pencil model P1; loop-margin constraints by calculation | [`opt_touchdown.md`](opt_touchdown.md) |
| Tremor tracker | All 23 settings of the accelerometer Kalman filter; learned trackers; per-writer tuning | The filter rewritten in PyTorch and differentiated exactly (a hand-written numba adjoint, 40× faster than autograd); Adam on domain-randomised writers; GRU and learned-gate training on the tremor band; Pareto sweep against false correction | [`opt_tracker.md`](opt_tracker.md) |
| Slim pencil nib-stage hardware (now the secondary variant) | Plate geometry and count, leaves, lever, nib force, driver and Hall sensors, from real catalogue parts or supplier-standard custom plates | Differentiable copy of the design model (PyTorch; exact against `design.py` and the CAD), adjoint gradients with Bayesian optimisation and CMA-ES over discrete part choices; finalists ranked in P1 | [`opt_hardware.md`](opt_hardware.md) |
| Rev H: moving nose and inertial control of the pen body | The nose actuator (pivot, arm, magnets, coils, travel; 7 variables); the tracker for ±3 mm travel (10 settings); the rear reaction mass, a gyroscope pair and a passive weight with their control; tip design A against B | Adjoint (autograd) design of the actuator, checked against finite differences; ParEGO multi-objective Bayesian optimisation of the tracker; a neural reaction-mass controller trained by backpropagation through time; linear screens, then time-domain tests in H1 | [`opt_inertial.md`](opt_inertial.md); added at the user's direction (DEC-024 superseded by DEC-032, DEC-033) |
| Guidance board | Magnet sizes and gap, stage and sensing for a board that moves a magnet under the paper | Force maps (magpylib, checked by a dipole model); architecture comparison by calculation; Monte Carlo of the Hall ring; closed-loop guidance simulations | [`guidance_board.md`](guidance_board.md) (DEC-031) |
| AI help for severe tremor | Letter prediction as a tracker prior and as nose guidance; a more aggressive tracker setting; the app's clean copy | Settings chosen on tuning writers with rules fixed before the test (twelve tracker settings, four prior and four guidance settings); safety rules on wrong letters, small tremor and false correction | [`ai_severe_tremor.md`](ai_severe_tremor.md) (DEC-035) |
| Handwriting outcomes | What each function changes in the ink, per condition | Tracker settings re-tuned on training writers only; results on test writers, cross-checked against P1; legibility scored by the app's recogniser | [`handwriting_outcomes.md`](handwriting_outcomes.md) |

**Why these methods.** The simulators have friction, contact and saturation, so their exact gradients are rough. Each study used gradients (the adjoint) where they are exact and smooth: a reduced model, the filter recursion or the design equations. It then used Bayesian optimisation or CMA-ES on the full simulator, and judged every result on test seeds that were never used for tuning.

## 3. Results so far (SIM unless stated)

### 3.1 Touchdown and lift (DEC-026, DEC-027; proposed)

Ink at touchdown and lift that a rigid pen would not draw, per stroke (test seeds 200–203):

| Pen | 35° | 50° | 75° | Correction left, 6 Hz 0.3 mm, 50° |
|---|---|---|---|---|
| Tilt-range front stop (P0.1.2) | 0.35 mm | 0.81 mm | 0.42 mm | 0.22 |
| Tilt-adaptive stop alone | 0.14 mm | 0.11 mm | 0.00 mm | 0.27 |
| Adaptive stop + optimised feed-forward | **0.005 mm** | **0.008 mm** | **0.000 mm** | 0.25 |

- The feed-forward uses only sensors the pen already has. Its open risk is bounce: 1.7 contact transitions per pen-down against 1.2.
- **Servo retuned:** tracking error 19.3 → 12.5 µm at 136 → 117 mW, with the loop margins kept.
- **Optional faster slide sensor** (DRV5055 or TMR2615 with a 1 mm magnet, MFR AMF-70…72): it adds almost nothing in P1. It is a fallback if the bench shows the axial sensor slower than assumed.

### 3.2 Tremor tracker (DEC-028; proposed)

| Tracker | Tremor-band error left, mean | 8–12 Hz at 0.3–0.5 mm | Moves tremor-free writing (smooth / sharp writers) |
|---|---|---|---|
| Previous default (random search, robust) | 0.91 | 0.79 | 5 / 21 µm |
| **Re-optimised by adjoint gradients (proposed default)** | **0.86** | **0.67** | 7 / 18 µm |
| Tuned on smooth writing (random search) | 0.78 | 0.52 | 21 / 146 µm |
| Learned GRU on the tremor band | 0.80 | 0.61 | 14 / 57 µm |
| Limit: perfect knowledge of the tremor band | 0.26 | 0.25 | – |

- The adjoint found better optima of the same objectives, and mapped the trade-off. No setting has both the smooth-writing benefit and a small shift on sharp writing: telling tremor from writing remains the limit, not the sensor or the optimiser.
- The learned trackers were not better at equal false correction and are not shipped.

### 3.3 Slim pencil hardware (DEC-030; proposed)

| | Current pencil (P0.1.2) | Optimised (P0.2) |
|---|---|---|
| Worst-case usable stroke (−20 % parts, 35°) | 0 µm | 212 µm |
| Loaded stroke in typical writing (50°) | 277 µm | 477 µm (servo capped at 300) |
| Force at the nib | 0.33 N | 0.64 N |
| First resonance | 192 Hz | 213 Hz |
| Battery life with assist (worst 0.3 mm case) | 0.50 h | 2.73 h |
| Mass including 10 % | 13.4 g | 14.6 g |

- CALC, from the differentiable design model; P1 confirms the loaded stroke to 0.00 % and the resonance to 0.1 %.
- In P1, the worst corner's error left with perfect knowledge falls from 0.375 to 0.281 (SIM). At 0.3–0.5 mm tremor both designs are held by the same ±0.30 mm servo limit.
- Five changes: custom PICMA-class plates, thicker C17200 leaves, the gimbal 3.5 mm further back, an LT8365 charge-recovery drive, and two DRV5055A4 Hall sensors.
- This matters for the slim variant only. The bigger-grip pen (Rev H, DEC-029) moves the whole tip by about ±3 mm instead.

### 3.4 Rev H: moving nose and inertial control of the pen body (DEC-032, DEC-033; proposed)

Ratio = ink error with correction ÷ without, lower is better. Tremor at the hand 8–12 Hz; test seeds 200–203; r_rot is the unmeasured share of the grip that tilts the pen (EXP-I01).

| Corrector | r_rot 0.3 | r_rot 0.5 | r_rot 0.7 |
|---|---|---|---|
| Nose, perfect knowledge of the tremor (the mechanism's limit) | 0.18 | 0.18 | 0.17 |
| **Nose with the accelerometer tracker, 1–2 mm** | **0.64** | **0.70** | **0.76** |
| Nose + rear inertial module, tracker, 1–2 mm | 0.61 | 0.59 | 0.63 |
| Nose with the tracker, 0.3 mm | 0.89 | 0.93 | 0.96 |

- **Design B was chosen** (DEC-032). A ring on the fixed sleeve carries the writing force; the nose only steers. Against a rigid nose that carries the load (A) it needs about 0.004 W of coil power instead of 0.3–1.0 W, and it does not change the writing force.
- **Adjoint design of the actuator** (CALC): Km 0.47 N/√W at the magnets, 0.36 at the tip. It found that the magnet gap must clear the other axis's stroke.
- **ParEGO tracker for ±3 mm** (SIM): tremor-band ratio 0.85 → 0.71 on training seeds, within the pre-declared false-correction limit.
- **The inertial module** (19.8 g tungsten slug, ±2.75 mm, 27.8 g added, ≤ 0.051 W) adds a further 6 / 17 / 17 % on top of the nose (SIM). It is fitted in the first prototype at the user's direction (DEC-033); the product keeps it if EXP-I01 and EXP-I06 confirm ≥ 10 %.
- **Not used:** a passive weight (it made 38–42 % of the 8–12 Hz cases worse, because the hand–pen resonance falls into the tremor band); a gyroscope pair (81 g, 0.42 W, CALC). The neural controller matched the model-based law but did not beat it.
- **At 4–6 Hz nothing helps yet.** The tracker locks onto the second harmonic. Parkinson's tremor is a target for cues and practice, not the stabiliser.
- The earlier study inside the 20 g pencil (`inertial_stabilisation.md`, 3–15 % from a cap device) remains the slim-envelope data point.

### 3.5 Handwriting per condition (SIM, model HW1)

| Condition | Help | Result |
|---|---|---|
| Essential tremor, 8–10 Hz, 1–2 mm | Nose + tracker | Ink error 835 → 531 µm; words read 31 % → 59 % |
| Essential tremor, 10 Hz, 1 mm | Nose + tracker | Words read 54 % → 87 % |
| Tremor at 4–6 Hz | Nose + tracker | No benefit (−2 to +9 %) |
| Parkinson's shrinking letters | Vibration cue "write bigger" | x-height 5.1 → 5.2 mm instead of 4.2 mm, *if* people respond as small studies suggest; +11 % writing time |
| Poor handwriting, practice | Partial nose guidance | Ink 35 % closer to the target letters while guided |
| Poor handwriting, practice | Guidance board | Ink 24–34 % closer while guided |
| Dyslexia, reversed or wrong letters | Any guidance | 0 % turned into the right letter |
| Dyslexia, spelling | App AI with a known target word | Flags all misspelt words (6 % false flags) |

Guidance changes the ink only while it is on. Whether it teaches is a human-study question (EXP-W04), and the literature says effects mostly vanish when guidance is switched off.

### 3.6 Guidance board (DEC-031; proposed)

- A permanent magnet moved by a CoreXY stage under 3 mm glass pulls a 0.75 g disc magnet in the pen's sleeve: 1.2 N available in every direction at the A4 gap, capped at 0.4 N in software (CALC).
- Tracing error 1.49 → 1.07 mm (partial guidance) and → 0.63 mm (full) for a relaxed writer; with the nose also correcting, 0.085–0.19 mm (SIM).
- Open issues: the pen magnet's keel limits tilt to ≥ 51°; up to 48 µm crosstalk into the nose's Hall sensor; board commands must stay below about 3 Hz.

### 3.7 AI help for severe tremor (DEC-035; SIM, model HW1)

At 8–10 Hz and 1–2 mm (test writers 0–5, seeds 200–203):

| Variant | Ink error | Words read | Share of the tracker's gap closed |
|---|---|---|---|
| Ordinary pen | 835 µm | 31 % | – |
| Rev H with its tracker | 531 µm | 59 % | – |
| + AI prior, predicted letters | 530 µm | 59 % | 0 % |
| + AI guidance, predicted letters | 526 µm | 60 % | 1 % |
| + guidance toward a known text (copying) | 475 µm | 65 % | 12 % |
| Severe-tremor tracker setting (rejected: moves clean writing 263 µm) | 281 µm | 88 % | 55 % |
| The app's digital clean copy (not the ink) | 189 µm | 97 % | 76 % |
| Perfect knowledge (the mechanism's limit) | 79 µm | 99 % | 100 % |

- A correct predicted letter is 535–938 µm off at 1–2 mm tremor because it is placed where the shaking tip lands, and only 6 of 26 letters reach the confidence gate.
- No AI variant changed anything at 0.3 mm or on tremor-free writing. A wrong prediction at full confidence made 3–8 of 3744 letters read wrongly, so guidance toward predicted letters is not used.

## 4. What must be measured first

| Question | Experiment |
|---|---|
| Does the touchdown feed-forward bounce? What is the axial sensor's latency? | EXP-Q08 (step 0, then the feed-forward on and off) |
| Which tracker settings ship, on real writing | EXP-E01 with recorded writing (`opt/tracker/realdata.py`) |
| How the grip splits between translation and tilt (decides where inertial devices act) | EXP-I01, then the module on a hand simulant (EXP-I06) |
| Can the tracker separate tremor from writing on real recordings, and at which frequencies? | EXP-W02 (extends EXP-E01) |
| Does guided practice improve unassisted handwriting? | EXP-W04 (at least 20 sessions, retention tests) |
| Is the clean copy readable to people, and is a severe-tremor setting worth its false correction? | EXP-A03 (AC-A03-04/05), EXP-W02 offline (AC-W02-03) |
| Stage stiffness and damping, then the servo retune | EXP-Q04 / Q07 |
| Friction under vibration (the largest model uncertainty for the tremor error) | EXP-B01 / B02 with superimposed vibration |
