# Where the simulations are, and how they were optimised

**Status: proposed designs, optimised in simulation only (2026-09-28).** Nothing here has been measured on hardware or on people. Labels:
- **SIM**: an executed simulation on synthetic writing and tremor;
- **CALC**: a calculation;
- **MFR**: a manufacturer statement, with its ledger id in `docs/evidence.csv`;
- **ASSUMPTION**: an input nobody has measured.

## 1. Where to see them

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
| Rev A model M1 | The earlier, larger voice-coil pen | `sim/pensim/` | `results/sim/` |

## 2. What was optimised, and how

| Study | What it optimises | Methods | Report |
|---|---|---|---|
| Touchdown and lift | Stage feed-forward law (11 parameters), front-stop margin, stage servo (5 parameters) | Adjoint gradients of a differentiable reduced model (PyTorch, backpropagation through time) to choose the law's structure; ParEGO Bayesian optimisation and CMA-ES on the full pencil model P1; loop-margin constraints by calculation | [`opt_touchdown.md`](opt_touchdown.md) |
| Tremor tracker | All 23 settings of the accelerometer Kalman filter; learned trackers; per-writer tuning | The filter rewritten in PyTorch and differentiated exactly (a hand-written numba adjoint, 40× faster than autograd); Adam on domain-randomised writers; GRU and learned-gate training on the tremor band; Pareto sweep against false correction | [`opt_tracker.md`](opt_tracker.md) |
| Slim pencil nib-stage hardware (now the secondary variant) | Plate geometry and count, leaves, lever, nib force, driver and Hall sensors, from real catalogue parts or supplier-standard custom plates | Differentiable copy of the design model (PyTorch; exact against `design.py` and the CAD), adjoint gradients with Bayesian optimisation and CMA-ES over discrete part choices; finalists ranked in P1 | [`opt_hardware.md`](opt_hardware.md) |
| Inertial control of the pen body | Reaction-mass, gyroscope (CMG) and grip-pivot modules with their control, combined with the nib stage, over envelope tiers | Differentiable hand–pen dynamics, causal and learned controllers trained by backpropagation through time, Bayesian optimisation over real parts | in progress (`opt/inertial/`); added at the user's direction (DEC-024 reopened) |

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

### 3.4 Inertial control of the pen body

In progress. The user asked for "properly inertial control and movement of the pen … not just the nib moving". The earlier study (`inertial_stabilisation.md`) found that inside the 20 g pencil a cap device removes only 3–15 % of the ink tremor. It therefore remains the pencil-envelope data point. The new study treats size, mass and battery as trade-offs and optimises the modules and their control together with the nib stage.

## 4. What must be measured first

| Question | Experiment |
|---|---|
| Does the touchdown feed-forward bounce? What is the axial sensor's latency? | EXP-Q08 (step 0, then the feed-forward on and off) |
| Which tracker settings ship, on real writing | EXP-E01 with recorded writing (`opt/tracker/realdata.py`) |
| How the grip splits between translation and tilt (decides where inertial devices act) | EXP-I01 |
| Stage stiffness and damping, then the servo retune | EXP-Q04 / Q07 |
| Friction under vibration (the largest model uncertainty for the tremor error) | EXP-B01 / B02 with superimposed vibration |
