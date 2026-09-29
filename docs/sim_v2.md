# Simulator v2 (sim2): a MuJoCo hand–pen–paper simulator (study V, Rev J)

**Status: study report, 2026-09-29.** Evidence status of every result: SIMULATION or CALCULATION. Nothing here is a measurement of hardware or people.

Labels used for every number:

- **SIM**: this study's simulation (sim2, MuJoCo 3.6.0), with the file that holds it.
- **CALC**: a calculation.
- **LIT**: literature, with its ledger id (existing ids in `docs/evidence.csv`; this study's proposed rows in `results/sim2/evidence_rows.csv`).
- **MFR**: manufacturer data (ledger id).
- **ASSUMPTION** and **PROPOSED DESIGN**: chosen values, to be measured.

## 1. Summary

**What sim2 is.** A Python package that writes a MuJoCo model of the Rev H pen, the writer's hand and the paper, runs it, and scores the ink. Other Rev J studies plug their devices and controllers into it.

- **Pen.** The Rev H handle, fixed sleeve and C-shaped skid ring (contact radius 6.75 mm, DEC-034). The nose tilts on a 2-axis flexure gimbal driven by voice coils with current, force and heat limits. The refill slides on a constant-force spring behind a front stop.
- **Plug-ins.** Heel drive, end-cap rotor or control-moment gyroscope (CMG), reaction mass, and a second actuation plane for the nose. Each one is a parametric class with one interface.
- **Hand.** Two options: H1's hand (the lumped HAP-26 hand with H1's two-zone grip), or an articulated forearm–wrist–hand chain with tremor torques and a writer controller.
- **Paper.** H1's contact law (compliant normal force and LuGre friction) by default; MuJoCo's own soft Coulomb contacts as an option.
- **Sensors.** IMU, nose Hall sensor, page optical-flow sensor, writing-force load cell and refill slide, each with noise and delay.
- **Interfaces.** A Gymnasium environment whose observations are only the pen's own sensors and whose actions are device commands, with domain randomisation over 25 factors. `run_study.py` runs every result here; `--quick` runs a reduced version.

**Headline results.**

| Check | Result | Label |
|---|---|---|
| Reproduces H1 (Rev H-B, H1's test seeds, 56 cases) | Unmodified ink error within 3.1 % of H1 in every case (tolerance 10 %). Perfect-knowledge ("oracle") ratio within ±0.03 of H1 in 52 of 56 cases; worst +0.037. Causal-tracker ratio within ±0.05 in 50 of 56 cases; the misses come from the tracker's frequency lock, not the plant (§5.1) | SIM, `results/sim2/verification.json` |
| Time step | [[CONV_SUMMARY]] | SIM |
| Energy balance | Residual ≤ 6.8 × 10⁻⁴ of the energy scale in conservative, damped and actuated tests, for all four MuJoCo integrators | SIM |
| Gyroscopic torque | Rotor reaction torque equals h × ω within 1.3 × 10⁻⁴ (relative) | SIM |
| Contact closed forms | MuJoCo contact stiffness and stick creep match their closed forms within 0.3 % (stiff setting); H1 law pre-sliding stiffness within 0.5 % | SIM |
| Sensor models | Accelerometer noise density 58.5–59.6 µg/√Hz against fusion's 60 µg/√Hz (MFR OPT-37); page-sensor latency 2.0 ms at 1 kHz as set | SIM |
| Gym speed (one core, shared machine) | [[ENV_SPEED]] | SIM |

**What we found on the way** (details in §5–§7; each is a finding about the model or the design, not a measurement):

1. **Front stop.** When the nose tilts, the ball rises or falls by about q·z_p·cot θ. A refill front stop fixed 0.3 mm beyond contact lifts the ball off the paper during large corrections. H1 assumed an ideal refill and did not see this (§5.8).
2. **Native contacts chatter.** MuJoCo's stiff soft contact (0.5 ms, impratio 10) creeps least in stick but chatters when the pen slides (normal-force variation 2.6–3.0 times the mean). A softer setting slides cleanly but creeps about 30 µm/s in stick. H1's law is therefore the default for ink studies (§5.2).
3. **Causal ratio is bistable.** The largest sim2–H1 differences in the causal ratio are the tracker locking onto the tremor or not, on nearly identical inputs (§5.1).
4. **MyoSuite arm.** With constant co-contraction the Hill-type MyoArm cannot hold the pen-grasp posture on its own (7 slowly diverging modes). Its pen-point impedance at 8 Hz is 1.1–5.6 times HAP-26's (§7.3).
5. **Synthetic writers.** [[WRITER_SUMMARY]] (§6).
6. **Passive rotor.** A 1.2 mN·m·s rotor spinning passively in the end cap did not lower the ink error with a translational hand tremor (+1.3 %, one case, §5.9).
7. **Code fix.** A new unit test found a sign error in sim2's own C-ring contact point (it used the arc end instead of the lowest point). It was fixed before the results in this report. The H1 check used H1's fixed skid point and was not affected.

**What sim2 does not model** (§9): muscles in the writer model, reflexes, grip force, skin sliding in the fingers, ink and paper deformation, electromagnetic fields, flexure non-linearity, electronics beyond the coil's electrical time constant.

## 2. What sim2 models

### 2.1 Pen (PROPOSED DESIGN inputs from `results/revH/layout.json` and `opt/inertial/revh.py`)

| Element | Model in MuJoCo | Values (label) |
|---|---|---|
| Handle + fixed sleeve | One rigid body; mass and inertia summed from the Rev H part list | 67.1 g (CALC from PROPOSED DESIGN), wiring +10 % (ASSUMPTION) |
| Skid ring (DEC-034) | C ring, contact radius 6.75 mm, tube radius 0.6 mm, 120° opening on the top. H1 law: the analytic lowest point of the arc. Native: 31 capsules | radius PROPOSED DESIGN; tube ASSUMPTION |
| Nose | Body on two hinges at the gimbal (45 mm from the tip), flexure stiffness 0.025 N·m/rad per axis, structural damping ratio 0.02 | 6.96 g; 6.0 × 10⁻⁶ kg·m² about the pivot (CALC); stiffness ASSUMPTION |
| Voice coils | One actuator per axis at 79 mm: current input with the coil's L/R time constant, force = K_f·I, limits 1.5 A and 3.7 V minus back-EMF, copper loss and a first-order coil temperature | Km 0.47 N/√W, R 2.47 Ω, K_f 0.74 N/A (CALC), L 100 µH, 100 K/W, 0.5 J/K (ASSUMPTION) |
| Nose servo | H1's second-order reference follower (80 Hz, ζ 0.7, 0.6 m/s slew) realised by an inverse-dynamics + PD + integral inner loop at 400 Hz, updated at 10 kHz; bias torque for the static ball load | ASSUMPTION (`results/revH/tip_params.json`) |
| Refill | Slide joint with a constant-force spring (0.15 N), front stop that follows the nose deflection 0.3 mm beyond contact (§5.8) | F_c ASSUMPTION (EXP-Q02); D1 refill 0.84 g (DEC-004) |
| Tilt | 50° writing altitude | LIT CON-02; DR 40–60° |

### 2.2 Plug-ins (`sim2/plugins.py`; every default is ASSUMPTION until studies D, K and N hand over)

One interface: model hooks (`modify_handle_parts`, `mjcf_handle`, `mjcf_nose`, `mjcf_nose_joints`, `mjcf_world`, `mjcf_actuators`, `mjcf_sensors`), runtime hooks (`bind`, `reset`, `commands`, `apply`, `observe`, `power`, `record`) and `describe()` with labels. The Gym action space grows by each plug-in's `commands()`.

| Plug-in | What it is | Default |
|---|---|---|
| `HeelDrive` | Driven ball, steered wheel or omni pair at the sleeve's heel, pressed on the paper by a suspension spring; native contact with rubber friction | ball r 1.5 mm, μ 0.6, preload 0.3 N, 0.2 mN·m per axis |
| `EndCapRotor` | Rotor(s) on gimbal joints in the rear cap: passive gyroscope, reaction wheel, single or scissored-pair CMG. Gyroscopic torques are MuJoCo's rigid-body dynamics | 18.1 g tungsten, Ø16 × 5 mm, 20 000 rpm, h 1.2 mN·m·s (CALC) |
| `ReactionMass` | Slug on 2–3 slides with stops, driven by coils | Rev H module: 19.8 g, ±2.75 mm (PROPOSED DESIGN) |
| `MultiPlaneNose` | Second actuation plane: the gimbal pivot rides on two lateral slides with a centring flexure and its own coils, so the tip gets translation and tilt | ±3 mm pivot stroke, 50 N/m, 0.74 N/A |

### 2.3 Hand and arm

**H1 hand (`hand_model='h1'`, default).** The HAP-26 hand mass (0.21 kg) on the arm spring (170 N/m, 11 N·s/m) to the imposed hand path, with inertial feed-forward. The grip is H1's two-zone grip (finger-pad zone and thumb–index web) calibrated to the tip-referred HAP-26 impedance (575 N/m, 1.3 N·s/m) with the split r_rot. In sim2 it is five grip joints at the grip's elastic centre with stiffness-proportional damping. LIT HAP-26 via H1; split ASSUMPTION (EXP-I01).

**Arm (`hand_model='arm'`).** A chain in the page frame (every geometric value ASSUMPTION, `params.Arm`):

- arm base: three slides at the elbow (shoulder and elbow positioning), with the arm's stiffness and damping;
- forearm pronation–supination hinge;
- wrist flexion–extension and radial–ulnar deviation hinges (hand 0.42 kg, 3 × 10⁻³ kg·m² about the wrist);
- the pen in H1's two-zone grip at the fingers.

Joint impedance = passive stiffness (LIT HAP-32) × a co-contraction factor, with a constant damping ratio (LIT HAP-97, abstract). The writer controller plans the intended path: below 1 Hz with the arm base, letters with the wrist and forearm (Newton inverse kinematics on a 1 kHz grid, cubic-spline interpolation). It adds feed-forward torques from inverse dynamics, the writing force and the expected paper drag. The joint impedance is fitted to H1's pen-tip impedance (§7.1).

### 2.4 Tremor (`sim2/tremor.py`)

Narrow-band torque generators at the forearm and wrist (and optionally a force at the arm base), with frequency wander (OU process), amplitude wander, a second harmonic and optional broadband content. Channel shares and phases are ASSUMPTION; the ranges come from the literature.

| Profile | Frequency | Behaviour | Source |
|---|---|---|---|
| ET | 4–12 Hz, default 6 Hz | Present while writing (kinetic) | LIT PDT-56, PDT-07, PDT-31 |
| PD rest | 4–6 Hz, default 5 Hz | Suppressed while the pen moves (gate 0.15, 0.15 s), re-emerges over 3 s after it stops | LIT PDT-56, PDT-07, PDT-09 |
| PD action | 4–6 Hz | Present while writing | LIT PDT-08 |
| Physiological | 8–12 Hz, broadband | About 30 µm rms at the hand | LIT PDT-56, PDT-15 |

`tremor.calibrate()` sets the torque amplitudes so the lifted pen tip moves with a chosen peak amplitude at f0 (CALC on the linearised arm). In the H1-hand mode the tremor is H1's imposed hand-path displacement (and optional wrist rotation), as in `opt/inertial`.

### 2.5 Paper contact

| Mode | What it does | When to use |
|---|---|---|
| `'h1'` (default) | Compliant penalty normal force (10⁵ N/m, 10 N·s/m at the skid; 10⁵ N/m, 2 N·s/m at the ball) and LuGre friction normalised by N (μ_s/μ_k 1.3, Stribeck 2 mm/s, pre-sliding 10 µm) at the skid's lowest point and the ball's lowest point, applied as wrenches every step; compiled with numba | Ink metrics (micrometres) |
| `'mujoco'` | MuJoCo soft contacts with Coulomb friction on elliptic cones; default solref 2 ms, solimp 0.95/0.99/0.1 mm, impratio 1 | Coarse RL runs, geometry-rich plug-ins (heel drive) |

Friction coefficients: ball 0.15 (ASSUMPTION; CON-13 0.09–0.165), skid 0.12 (ASSUMPTION; EXP-Q01), rubber 0.6 (ASSUMPTION).

### 2.6 Sensors (`sim2/sensors.py`)

| Sensor | Model | Values (label) |
|---|---|---|
| IMU (LSM6DSV16X class) | Specific force and rate at the IMU site from MuJoCo's kinematics, anti-alias filter, then fusion's reading models (noise density, ODR, bias drift, scale, misalignment, quantisation) and the firmware's gyro compensation | 60 µg/√Hz, 2.8 mdps/√Hz, 3840 Hz (MFR OPT-37) |
| Nose Hall | Nose angle as tip deflection, noise and 50 µs delay | 5 µm rms (ASSUMPTION from MFR OPT-45) |
| Page sensor | Optical flow at the handle tip: 1 kHz, 2 ms latency, 3 µm noise, valid below 0.8 mm lift | ASSUMPTION (EXP-S01) |
| Writing force | Skid-ring load cell: 1 kHz, 5 mN, 1 ms | ASSUMPTION |
| Refill slide | Hall: 1 kHz, 2 µm, 1 ms; contact flag at the front stop + 0.1 mm | ASSUMPTION |

Offline streams feed `fusion`'s AKF exactly as `opt/inertial` does; online readings feed the Gym environment.

## 3. Numerical method

- **Step and integrator.** 25 µs, `implicitfast` (MuJoCo's recommended integrator; LIT CON-58). Justified by the convergence and energy results in §5.3–§5.4.
- **Order inside a step.** `mj_step1` → hand drive → paper contact wrenches → nose reference at 2 kHz (oracle, external estimate, policy, or environment action) → nose servo at 10 kHz → record at 4 kHz → `mj_step2`. Controllers therefore act on the state at the start of the step, as H1 does.
- **Why not native contacts for ink.** MuJoCo's soft contacts are regularised: a sticking contact creeps and a stiff contact chatters (LIT CON-56, CON-57, confirmed in §5.2). Ink errors of interest are micrometres, and friction transitions drive them.
- **Speed.** A 5 s Rev H case (200 000 steps) takes about 11 s on an idle core with the H1 law (SIM, measured during development); the machine was shared by five studies, so the tables give wall times under load.

## 4. How to use it

```python
import sim2
from sim2 import params as P, builder as B, sim as S, plugins as PL
cfg = P.Config(plugins=[PL.EndCapRotor(mode="cmg")])      # Rev H pen, H1 hand, H1 contact law
pm = B.build(cfg)                                           # MJCF text in pm.xml, MuJoCo model pm.m
from opt.inertial import scen as SC
res = S.run(pm, SC.get(300, SC.tremor(8.0, 1e-3)))         # recorded channels, sim/handpen/evaluate-compatible
```

- **Configurations.** `params.Config` (every parameter labelled in `params.LABELS`); `h1_check_config()` reproduces H1's settings; `calibrated_arm()` loads the fitted arm; `from_identified()` builds a configuration from identified bench parameters (§8.6).
- **Gym environment** (`sim2/env.py`, `PenEnv`):
  - observation (16 values with no plug-in): IMU specific force (3) and rate (3), nose Hall deflection (2), page-sensor displacement (2) and its valid flag, writing force, refill slide, contact flag, previous action; every sensor with its noise, bias and delay;
  - action: nose tip reference (t₁, t₂) scaled to the travel (through the servo's soft limit, slew limit and force limits), then each plug-in's commands;
  - reward: −(e/0.1 mm)² per tick while the ball touches the paper, e = ink deviation from the tremor-free ink of the same plant and writing, minus small action-rate and saturation penalties;
  - episode: 3 s of sigma-lognormal writing with a sampled tremor at 1 kHz control; domain randomisation per episode (table in §7.4).
- **Study.** `python3 -m sim2.run_study [--quick] [--stages ...]`. Stages: h1check, diagnose, contact, convergence, frontstop, energy, gyro, sensors, native, arm, myo, validate, env, plugins, report.
- **Tests.** `python3 -m pytest sim2/tests -q` (fast, about 15 s); `--runslow` adds MyoArm, one H1 case and a quick stage.

## 5. Verification (code and calculation verification, ASME V&V 40 sense)

### 5.1 Reproduction of H1 (SIM, `results/sim2/verification.json` → `h1check`, figure `fig_sim2_h1check.png`)

**Method.** The same cases, scenarios and metrics as `opt/inertial` (Rev H-B): tremor-free reference, unmodified run, perfect-knowledge correction ("oracle") and the Rev H AKF tracker on the pen's own IMU and page-sensor streams ("causal"). Ratio = ink error with correction ÷ without, against the reference. H1 is rerun with `opt.inertial.evaluate.RevHEval` (read-only code) on the same cases. Test seeds 200–203 are H1's own test cases.

**Tolerances.** Written into `sim2/h1compare.py` before the grid ran, after one debugging case (seed 200, 10 Hz, 1 mm): unmodified ink error within ±10 %; oracle ratio within ±0.03; causal ratio within ±0.05.

| Grip split r_rot | Cases | Unmodified: max difference | Oracle: mean / rms / max difference, pass | Causal: mean / rms / max difference, pass |
|---|---|---|---|---|
| 0.5 | 40 (4 seeds × 4, 8, 12 Hz × 0.3, 1, 2 mm; + 4 wrist) | 1.5 % | +0.006 / 0.013 / 0.037; 37 of 40 | +0.011 / 0.053 / 0.304; 37 of 40 |
| 0.3 | 8 (2 seeds × 8, 12 Hz × 1, 2 mm) | 1.1 % | −0.001 / 0.014 / 0.030; 7 of 8 | −0.002 / 0.032 / 0.070; 7 of 8 |
| 0.7 | 8 | 3.1 % | +0.010 / 0.013 / 0.021; 8 of 8 | +0.053 / 0.112 / 0.273; 6 of 8 |

Means over seeds, r_rot 0.5 (SIM; "published" = `results/opt/inertial_opt.json`):

| Tremor | Oracle: published / H1 rerun / sim2 | Causal: published / H1 rerun / sim2 |
|---|---|---|
| 4 Hz, 0.3 / 1 / 2 mm | 0.086 / 0.086 / 0.086; 0.087 / 0.087 / 0.085; 0.096 / 0.096 / 0.096 | 1.004 / 1.004 / 1.001; 1.001 / 1.001 / 1.001; 1.004 / 1.004 / 1.002 |
| 8 Hz, 0.3 / 1 / 2 mm | 0.097 / 0.097 / 0.096; 0.123 / 0.123 / 0.127; 0.158 / 0.158 / 0.164 | 0.953 / 0.953 / 0.969; 0.799 / 0.799 / 0.811; 0.724 / 0.723 / 0.769 |
| 12 Hz, 0.3 / 1 / 2 mm | 0.099 / 0.100 / 0.103; 0.205 / 0.204 / 0.231; 0.241 / 0.240 / 0.265 | 0.931 / 0.933 / 0.933; 0.732 / 0.736 / 0.746; 0.641 / 0.646 / 0.648 |
| Wrist rotation, 8 Hz 1 mm | 0.128 / 0.129 / 0.129 | 0.785 / 0.784 / 0.808 |

What the differences mean:

- **Unmodified ink error** agrees within 3.1 % everywhere (SIM). sim2's plant (MuJoCo rigid bodies, grip joints, dynamic nose and sliding refill) reproduces H1's.
- **Oracle** misses are all at 12 Hz, 1–2 mm (+0.031 to +0.037, r_rot 0.5). sim2's nose and refill are dynamic bodies with a finite-bandwidth servo; H1's stage is kinematic. [[DIAG_ORACLE]]
- **Causal** misses are the tracker's frequency lock. For seed 201, 8 Hz, 2 mm (H1 0.750, sim2 1.054) H1's AKF settled at 7.75 Hz and sim2's at 14.5 Hz on streams that correlate at 0.97. [[DIAG_CAUSAL]]

### 5.2 Paper contact (SIM, `verification.json` → `contact`; figure `fig_sim2_contact.png`)

MuJoCo soft contact, 20 g sphere on a plane (closed forms from LIT CON-59):

| Setting | Static stiffness (measured / closed form) | Creep in stick at ½μN (measured / closed form) | Sliding friction ÷ normal (μ = 0.12) | Gliding gap at 20 mm/s (measured / (dt+τ)μv, LIT CON-56) |
|---|---|---|---|---|
| Stiff: 0.5 ms, 0.99/0.999, impratio 10 | 7.86 × 10⁶ / 7.86 × 10⁶ N/m | 0.148 / 0.148 µm/s | 0.120 (contact flickers at nanometre penetration) | 0.02 / 1.26 µm |
| MuJoCo default: 20 ms, 0.9/0.95/1 mm | 1.22 × 10³ / 449 N/m (penetration beyond the solimp width) | 498 / 621 µm/s | 0.120 | 74 / 48 µm |
| Default in sim2: 2 ms, 0.95/0.99/0.1 mm, impratio 1 | 9.53 × 10⁴ / 9.21 × 10⁴ N/m | 30.5 / 30.7 µm/s | 0.120 | 2.1 / 4.9 µm |

The Rev H pen dragged at 20 mm/s with native contacts (H1 hand, rigid nose, 1 N):

| Setting | Skid normal force: std ÷ mean | Apparent μ at the skid |
|---|---|---|
| Stiff (0.5 ms, impratio 10), with or without noslip | 2.6–3.0 | 0.55–1.72 (should be 0.12) |
| MuJoCo default (20 ms) | 0.001 | 0.120 |
| sim2 default (2 ms, impratio 1) | 0.24–0.30 | 0.120 |

H1 contact law (LuGre), point mass (CALC closed forms):

- pre-sliding stiffness 15 522 N/m against μ_s N / x_pre = 15 600 N/m;
- sliding force at 20 mm/s equals μ_k N (0.1200 N);
- spring-driven stick–slip: peak force 0.1538 N (μ_s N = 0.156 N), trough 0.0876 N (Coulomb 2μ_k N − μ_s N = 0.084 N), period 0.456 s (Coulomb limit cycle 0.391 s; the Stribeck curve smooths the drop and lengthens the cycle).

**Decision in the model.** H1's law stays the default for ink metrics. The native default moved from the stiff to the 2 ms setting (correct sliding friction, 30 µm/s creep in stick).

### 5.3 Time step and integrator (SIM, `verification.json` → `convergence`; figure `fig_sim2_convergence.png`)

Rev H case, training seed 300, 8 Hz, 1 mm, first 3 s; ink path difference against the finest step (12.5 µs):

[[CONV_TABLE]]

### 5.4 Energy balance (SIM, `verification.json` → `energy`)

Pen in the air, arm springs as joint springs. Energy change against the work of dampers and actuators:

| Case | Residual ÷ energy scale (implicitfast, implicit, Euler, RK4) |
|---|---|
| Conservative (initial deflection, no damping) | −2.7 × 10⁻⁴ for all four |
| Damped (grip, arm, flexure damping) | +1.9 × 10⁻⁴ for all four |
| Actuated (30 Hz coil current) | −6.8 × 10⁻⁴ for all four |

The residual is the midpoint power estimate's own error; the integrators do not differ here because there are no contacts and few velocity-dependent forces.

### 5.5 Gyroscopic torque (SIM, `verification.json` → `gyro`)

18.1 g rotor (Ø16 × 5 mm tungsten) on a gimbal driven at a constant rate, reaction torque at the base against h × ω: 9 cases (5000–20 000 rpm × 2–10 rad/s), maximum relative error 1.25 × 10⁻⁴. At 20 000 rpm and 5 rad/s: 5.92 mN·m (h = 1.21 mN·m·s, CALC).

### 5.6 Sensors (SIM, `verification.json` → `sensors`)

- Accelerometer reading, pen held still, 20–200 Hz: 59.6 and 58.5 µg/√Hz (x, y) against fusion's setting of 60 µg/√Hz (MFR OPT-37); ODR 3840 Hz as set.
- With the firmware's lever-arm compensation (r × dω/dt) the page-frame estimate carries 294–372 µg/√Hz in the same band: the derivative of gyro noise times the 91 mm lever. This is a property of the compensation, not a model error.
- MuJoCo's native accelerometer against differentiated site velocity and positions in the 3–15 Hz band: correlation 0.9997; rms difference 2.4 % (SIM).
- Page sensor: 1 kHz, 2.0 ms latency as set.

### 5.7 Native against H1 contact on the Rev H cases (SIM, `verification.json` → `native`)

[[NATIVE_TABLE]]

### 5.8 Refill front stop: a design interaction (SIM, `verification.json` → `frontstop`)

Tilting the nose by q moves the ball along t₁ and changes its height, so the refill must extend by about q·z_p·cot θ to stay on the paper. H1 treated the refill as an ideal constant force and never met a stop.

[[FRONTSTOP_TABLE]]

### 5.9 Plug-in smoke runs (SIM, `results/sim2/plugins.json`)

| Plug-in | Test | Result |
|---|---|---|
| Reaction mass (19.8 g) | 0.1 N at 8 Hz for 0.8 s, pen writing still | Stroke 5.5 mm peak to peak against 4.0 mm for a free slug: it drifts without a centring loop (the Rev H module used a 5 Hz centring loop) |
| End-cap rotor, passive (h 1.21 mN·m·s) | Seed 300, 8 Hz, 1 mm hand tremor | Unmodified ink error 813 µm spinning against 802 µm not spinning (+1.3 %) |
| CMG | 5 rad/s gimbal rate for 0.1 s | Gimbal reached 0.50 rad; spin held within 10⁻¹⁰; expected torque 6.1 mN·m (CALC) |
| Heel drive (ball) | 0.2 mN·m drive torque | Traction 0.1334 N = τ/r; heel normal force 0.297 N (preload 0.3 N); the skid then carries 0.48 N instead of 0.8 N; tip moved 0.37 mm in 0.6 s against the hand |
| Multi-plane nose | 0.1 N on the pivot slide | Pen lifted: slide 2.03 mm (F/k = 2.0 mm). On paper: slide did not move (0.015 mm at the ink), because the ball sticks and the tilt servo holds the nose angle. The two planes need one coordinated controller (study N) |

## 6. Validation against the literature (SIM against LIT; `results/sim2/validation.json`)

| Quantity | sim2 | Literature | Status |
|---|---|---|---|
[[VALIDATION_TABLE]]

## 7. Hand models and the MyoSuite check

### 7.1 Arm fitted to H1's pen-tip impedance (SIM fit, `results/sim2/arm_calibration.json`, figure `fig_sim2_arm.png`)

[[ARM_CAL]]

### 7.2 The Rev H nose in the articulated arm against the H1 hand (SIM, training seeds)

[[ARM_VS_H1]]

### 7.3 MyoSuite MyoArm at a pen grasp (SIM, `results/sim2/myo_impedance.json`, figure `fig_sim2_myo.png`)

**Method.** MyoSuite 2.12.2's MyoArm (38 joints, 63 Hill-type muscles; LIT HAP-100) in a writing posture: shoulder elevation 0.35 rad, plane of elevation 0.9 rad, elbow 1.6 rad, forearm semi-pronated, wrist slightly extended (ASSUMPTION). Thumb, index and middle fingers are closed on a 22 mm pen by inverse kinematics (pads 11.0 mm from the pen axis). A 5 g pen is welded to the three distal phalanges. Every muscle is held at activation c (0–0.3), gravity is off, and the posture's net torque is balanced by a constant applied torque. The model is linearised about that posture (`mjd_transitionFD`) and the pen-point compliance is computed at 0.05–30 Hz in the page axes. The posture's shoulder couplings are set exactly first (without that, the equality constraints alone give 2000 rad/s² of spurious acceleration).

**Results** (|Z| = 1/|compliance| at the pen point):

| Axis (HAP-26 axis) | 4 Hz, c = 0 → 0.3 | 8 Hz, c = 0 → 0.3 | 12 Hz, c = 0 → 0.3 | HAP-26 nominal at 4 / 8 / 12 Hz (LIT) | H1 at 4 / 8 / 12 Hz |
|---|---|---|---|---|---|
| x, left–right (X) | 329 → 487 N/m | 1289 → 1594 | 2698 → 3430 | 139 / 607 / 532 | 234 / 584 / 746 |
| y, fore–aft (Z) | 480 → 1432 | 1382 → 3763 | 2473 → 6209 | 356 / 669 / 881 | 234 / 584 / 746 |
| z, vertical (Y) | 228 → 454 | 657 → 1064 | 1188 → 1857 | 177 / 759 / 802 | 234 / 584 / 746 |

HAP-26's structure (grasp spring k₁‖b₁ in series with arm mass M and arm spring k₂‖b₂) fitted to MyoArm over 1–20 Hz (SIM; rms log error 0.02–0.10):

| c | Arm part M (kg) x / y / z | k₂ (N/m) x / y / z | b₂ (N·s/m) x / y / z |
|---|---|---|---|
| 0 | 0.52 / 0.49 / 0.23 | 71 / 22 / 12 | 9.0 / 14.0 / 7.0 |
| 0.1 | 0.61 / 0.92 / 0.23 | 136 / 87 / 18 | 13.0 / 31.0 / 10.5 |
| 0.3 | 0.59 / 1.15 / 0.24 | 203 / 180 / 27 | 18.7 / 57.6 / 17.6 |
| HAP-26 nominal (LIT) | 0.22 / 0.20 / 0.27 | 79 / 272 / 105 | 4.6 / 18.1 / 6.4 |

What this says:

- **Stability.** At c = 0 the linearised posture is marginally stable (spectral radius 1.00000). For c ≥ 0.02 it has 7 slowly diverging modes (growth 1.0–3.5 per second; ring finger, wrist deviation with pen roll, shoulder). A Hill-type arm at constant activation cannot hold the posture; a real writer holds it with short-range stiffness and feedback, which MyoArm lacks (LIT HAP-101: Hill-type models underestimate short-range stiffness; RMSD 0.204 against 0.103 for cross-bridge models).
- **Magnitude.** With rigid pad welds, MyoArm's pen point is 1.1–5.6 times stiffer than HAP-26 at 8 Hz, because HAP-26's grasp compliance (k₁ 380–770 N/m) is missing and MyoArm's finger joint damping (0.05–1.05 N·m·s/rad, a model parameter) is large at small lever arms.
- **Trend.** From c = 0 to 0.3 the arm-part stiffness rises 2.9× (x), 8× (fore–aft) and 2.3× (vertical); damping 2.1×, 4.1× and 2.5×. The effective mass hardly changes. This matches the literature's qualitative picture: impedance magnitude rises with co-contraction and damping follows stiffness (LIT HAP-96, HAP-97, abstracts).

### 7.4 Domain randomisation (`sim2/env.py`, table in `results/sim2/env_benchmark.json`)

[[DR_TABLE]]

**Change from the MyoSuite check.** The arm damping range is widened from 3.7–27.6 N·s/m (HAP-26's 95 % interval) to 3.7–60 N·s/m (MyoArm's fore–aft b₂ at c = 0.3). Stiffness and mass keep HAP-26's intervals: MyoArm's stiffness is not credible (no short-range stiffness), and writers rest the forearm on the desk.

## 8. Sim-to-real plan and credibility (FDA 2023 framework, ASME V&V 40)

Sources: LIT CON-63 (FDA guidance, full text), CON-64 (ASME V&V 40 scope; standard not read), CON-65 (Viceconti et al. 2021).

### 8.1 Question of interest and contexts of use (COU)

| COU | Question | Model influence | Decision consequence | Model risk |
|---|---|---|---|---|
| COU-1 | Which Rev J device concepts and controllers to build and bench-test next (ranking by predicted ink-error ratio, power, force) | Medium: bench tests follow before any claim | Low: wasted prototype effort; no user exposure | **Low–medium** |
| COU-2 | Train and select firmware policies (trackers, RL) for bench and human tests | High for the policy; gated by bench tests (REQ-ML-001) | Medium: a bad policy reaches a bench or a supervised session | **Medium** |
| COU-3 | Evidence of benefit or safety for users | High | High | **High: not supported by sim2 now** |

### 8.2 Credibility factors and goals

| Factor (V&V 40 / FDA category) | Goal for COU-1 | Goal for COU-2 | Status now |
|---|---|---|---|
| Code verification | Unit tests of every closed form; independent re-implementation where possible | Same | Met: closed forms (§5.2–§5.6), compiled kernel = Python reference (tests), H1 cross-check (§5.1) |
| Calculation verification | Ink path difference at the production step ≤ 1 µm rms against half the step; observed order reported | Same, plus the RL step | [[CRED_CALC]] |
| Model inputs (calibration) | Nominal values with ranges from literature; DR over them | Identified values with uncertainty from EXP-V01, V02, V04 | Literature and ASSUMPTION only |
| Model form | Two contact laws and two hand models compared on the COU's metrics | Residual diagnostics on bench data (s2r model-form checks) | Contact: native vs H1 law (§5.7); hand: arm vs H1 (§7.2) |
| Bench validation (comparator) | Not required before ranking | EXP-V05: ratio within ±0.05 (causal), ±0.03 (known disturbance), ≥ 80 % of conditions; rank order Spearman ≥ 0.9 | Not started (no hardware) |
| In vivo / population validation | Not required | EXP-V03, EXP-V06 | Not started |
| Applicability | Validation conditions cover 35–75° tilt, 4–12 Hz, 0.3–2 mm, writing speeds of real writers | Same | Writers are slower and smoother than measured writing (§6); widen before COU-2 |
| Uncertainty quantification | Results reported over seeds and DR | Prediction intervals from identified parameter uncertainty | Seeds and DR only |

### 8.3 Parameter → experiment map

| Parameter (sim2 field) | Now (label) | Experiment | Identification |
|---|---|---|---|
| Ball and skid friction μ, μ_s/μ_k, Stribeck speed, pre-sliding (`contact.*`) | 0.15, 0.12, 1.3, 2 mm/s, 10 µm (ASSUMPTION) | **EXP-V01** (with EXP-B02, EXP-Q01) | LuGre grey-box fit (s2r `exp_b01b02`) |
| Contact normal stiffness and damping (`k_sk`, `c_sk`, `k_ball`) | 10⁵ N/m, 10 N·s/m (ASSUMPTION) | EXP-V01 (indentation) | Least squares with covariance (s2r `ident`) |
| Rubber heel friction (`mu_rubber`) | 0.6 (ASSUMPTION) | EXP-V01 (rubber element) | As above |
| Nose flexure k_r, ζ; coil K_f, R, L, R_th, C_th; Hall delay (`nose.*`) | 0.025 N·m/rad, 0.02; 0.74 N/A, 2.47 Ω, 100 µH, 100 K/W, 0.5 J/K; 50 µs | **EXP-V02** (EXP-B03, EXP-B05 methods on the Rev H nose, with EXP-I05) | s2r `exp_b03`, `exp_b05`: blocked force, voltage step, FRF with second-order-plus-delay fit |
| Refill spring F_c, slide friction, front-stop margin | 0.15 N, 0, 0.3 mm | EXP-V02 part B (with EXP-Q02) | Force–displacement loop |
| Masses and inertias of handle, nose, plug-ins | CALC from CAD part lists | EXP-V02 part A | Weighing, bifilar pendulum |
| Grip: k_nib, b_nib, r_rot, ρ_w, k_roll; hand M, k_arm, b_arm | HAP-26 (LIT), split ASSUMPTION | **EXP-V04** (with EXP-I01, EXP-B06) | FRF of force at the pen, fitted with `hand.calibrate_to_h1`-type fits and a stochastic grey-box model (LIT EML-72) |
| Arm joint impedance and co-contraction range (`Arm.*`) | Fitted to H1 (SIM) | EXP-V04 | Same fit on measured tip impedance |
| Tremor profiles (f0, amplitude, shares, wander, gating) | LIT ranges | **EXP-V03** (inside EXP-H01, with EXP-I02) | Spectral fits per writer |
| Writer (speed, stroke timing, sigma-lognormal parameters) | Synthetic (§6) | EXP-V03 | Sigma-lognormal extraction per stroke (LIT CON-60/61) |
| IMU noise and bias, page-sensor latency and noise, Hall noise | MFR OPT-37, ASSUMPTION | EXP-V02 (with EXP-S01, EXP-B04) | Allan variance; cross-correlation latency |
| Device effect (the output) | SIM | **EXP-V05**, **EXP-V06** | Comparator, not identification |

### 8.4 Grey-box identification procedure

1. **Order.** Follow the s2r protocol order: actuator coupons (EXP-B03) → nose FRF (EXP-B05/V02) → friction (EXP-B01/B02/V01) → hand (EXP-V04) → writers and tremor (EXP-V03). Each step fixes parameters the next one needs.
2. **Model.** For each experiment, write the relevant sim2 sub-model as a state-space model with process noise and measurement noise (LIT EML-72, stochastic grey-box). Use the same equations as sim2, not a new model.
3. **Estimate.** Maximum likelihood with an extended Kalman filter over several independent recordings; report parameters with 95 % intervals (s2r `ident.py` already does least squares with Laplace covariance and bootstrap).
4. **Check model form.** Residual whiteness (Ljung–Box), cross-correlation with the input, band misfit (s2r `modelform.py`). If the residual is structured, extend the model (for example a learned actuator model, LIT OPT-58) before randomising.
5. **Randomise what is left.** Narrow the DR ranges to the identified intervals (LIT OPT-57); keep randomising what cannot be identified per user (grip split, tremor). Update the DR distribution from a few real roll-outs (SimOpt-style, LIT EML-71).
6. **Freeze and validate.** Freeze parameters and the firmware, then run EXP-V05 against the frozen sim2 (pre-registered pass lines). Do not refit on the validation data.

### 8.5 Validation experiments (proposed)

| ID | Purpose | Method | Measurand | Pass line |
|---|---|---|---|---|
| **EXP-V01** | Calibrate and validate the paper contact of the Rev H front end | Sled/tribometer with the Rev H lip and ball on 80 g/m² paper: normal indentation; friction vs speed 0.1–50 mm/s; velocity reversals; drags at 35°, 50°, 75° with 0.5–2 N; high-rate force (≥ 2 kHz) and displacement (LDV) | μ_s, μ_k, Stribeck speed, pre-sliding distance, normal stiffness; normal-force variation while sliding; rubber element μ | sim2's H1 law with the identified parameters predicts friction force vs speed within ±10 % rms over 0.5–50 mm/s and pre-sliding displacement within ±30 %; the native setting is accepted only if its sliding chatter index is within 2× the measured one |
| **EXP-V02** | Identify the assembled pen (nose, refill, sensors, masses) | Handle clamped: current-step and chirp to each coil; Hall and LDV at the ball; refill force–displacement loop; weighing and pendulum; IMU still and on a rate table; page sensor on a motion stage | Coil K_f, R, L, thermal; flexure k_r, ζ; Hall delay; F_c and slide friction; masses and inertias; sensor noise densities, bias, latency | sim2 with identified parameters reproduces the measured nose FRF within ±1 dB and ±10° over 1–200 Hz, step responses within ±10 % rms, sensor noise within ±20 % |
| **EXP-V03** | Record real writing and tremor at the pen (inputs of sim2) | Inside EXP-H01 sessions: instrumented passive pen (IMU, page sensor, force) plus a wrist IMU; standard sentence, loops, spirals; ET, PD and controls | Tremor peak frequency, amplitude and bandwidth at the pen and wrist; writing speed, stroke durations, velocity spectrum, power-law exponent; writing force | sim2's tremor and writer models, with DR, cover ≥ 90 % of recorded writers on every measurand (each recorded value inside the simulated 5–95 % range) |
| **EXP-V04** | Identify the pen-grasp impedance while writing | Small random force (0.5–30 Hz, ≤ 0.2 N) at the pen via a stinger or the pen's own nose/reaction mass as an exciter, while participants hold a writing posture at 2–3 instructed co-contraction levels; forearm on the desk | Tip-referred compliance in 3 axes; grip split r_rot; roll stiffness | sim2's H1 hand (and the fitted arm) reproduce each participant's compliance within ±20 % magnitude and ±15° phase over 1–20 Hz; the DR ranges cover ≥ 90 % of participants |
| **EXP-V05** | Validate the device effect on a bench | Hand simulant (EXP-G05) or a robot-held pen with injected tremor 4–12 Hz, 0.3–2 mm, ink metrology (EXP-B09); frozen firmware | Ink error ratio: known disturbance and causal tracker | sim2 (identified parameters, same disturbance) predicts the measured ratios within ±0.03 (known disturbance) and ±0.05 (causal) in ≥ 80 % of conditions; Spearman rank correlation ≥ 0.9 across conditions |
| **EXP-V06** | Check sim2's population prediction against people | Inside the human study: ink error with and without assistance | Distribution of the ratio across writers | The measured median ratio lies inside sim2's 80 % prediction interval (DR over hand and tremor); the rank order of conditions matches |

### 8.6 How `s2r/` calibrates sim2

- `s2r` already runs the identification pipeline in protocol order (B03 → B05 → B01/B02) on a virtual bench with hidden plants and scores the recovered parameters (`results/s2r/c1_identification.json`).
- `sim2.params.from_identified(values)` maps s2r's parameter names (`actuator.Kf`, `actuator.R20`, `stage.k_tip`, `writing.mu_eff`, `friction.x_presliding`, `hand.grip_stiffness`, `sensing.opt_delay`, …) onto a sim2 configuration. It was tested on s2r's revealed truths (unit test `test_from_identified_maps_s2r_names`).
- Next step (round 2): point s2r's virtual bench at sim2 instead of M1, so the same pipeline identifies sim2's hidden parameters from simulated EXP-V01/V02 records in the `s2r-bench-1` file format. That tests the identification end to end before hardware exists.
- When bench data exist, the same pipeline reads them, `from_identified` builds the calibrated sim2, and the DR narrows to the identified intervals (§8.4 step 5).

## 9. What sim2 does not model

- Muscles, reflexes and short-range stiffness in the writer model (MyoArm is used only as a check).
- Grip force and its coupling to impedance (LIT CON-07: grip about 4.3 times the normal force; CON-08: 5–20 N); the grip is a linear impedance.
- Skin sliding and rolling of the pen in the fingers beyond a torsional spring.
- Ink deposition, paper deformation and paper texture; friction is a law with fitted parameters.
- Flexure non-linearity, magnetic fields and forces from position-dependent coil gaps, eddy currents.
- Electronics other than the coil's L/R and current and voltage limits; sampling jitter of the firmware (except the tick structure).
- Visual feedback and the writer's corrections of the ink.

## 10. Open issues

1. **Oracle gap at 12 Hz.** [[OPEN_ORACLE]]
2. **Causal comparisons need many tracker-noise seeds.** The AKF's frequency lock makes single-seed differences large. Compare trackers over ≥ 5 noise seeds.
3. **Front stop.** The Rev H refill needs a stop that follows the nose (as modelled) or a margin of about travel × cot θ (2.5 mm at 50°, 4.3 mm at 35°, CALC). A mechanism has not been designed.
4. **Native contacts** still chatter at stiff settings; a physically parameterised compliant contact (LIT CON-56) would remove the trade-off.
5. **Arm fit anisotropy.** [[OPEN_ARM]]
6. **MyoArm** has no short-range stiffness or reflexes and rigid pad welds; its absolute impedance is not the writer's.
7. **Writers.** [[OPEN_WRITER]]
8. **Speed.** [[OPEN_SPEED]]

## 11. Proposed decision, requirements and experiments

**Proposed decision (the lead assigns the number).** *Simulator v2 is the Rev J reference simulator for device and controller studies.*

- Ink metrics use H1's contact law at 25 µs with `implicitfast`.
- Native MuJoCo contacts are used only for speed-limited RL runs and geometry-rich plug-ins (2 ms, impratio 1), and such results are cross-checked with H1's law.
- H1 stays the fast regression reference: after any change, sim2 must pass the H1 check (REQ-SIM-001).
- Device results are reported with both hand models and over the domain randomisation.
- Until EXP-V01, V02 and V04 calibrate it and EXP-V05 validates it, sim2's results rank concepts (COU-1) and are not evidence of benefit.
- Alternatives considered: keep H1 only (fast, but no plug-in bodies, no native gyroscopics, no articulated hand); MuJoCo native contacts everywhere (creep or chatter, §5.2).
- Revisit when EXP-V05 reports.

**Proposed requirements** (new area SIM; the lead places them):

| ID | Requirement | Verification |
|---|---|---|
| REQ-SIM-001 | After any change, sim2 reproduces H1 on H1's test grid: unmodified ink error within ±10 %, oracle ratio within ±0.03 in ≥ 90 % of cases | `run_study --stages h1check` |
| REQ-SIM-002 | At the production step, the ink path differs by ≤ 1 µm rms from the half step; energy residual ≤ 10⁻³ of the energy scale | `run_study --stages convergence,energy` |
| REQ-SIM-003 | Every parameter carries a label and source (`params.LABELS`); every result file carries `stabpen.provenance` metadata | code review; tests |
| REQ-SIM-004 | The Gym observation holds only the pen's own sensor readings with their noise, bias and delay; every DR range cites its source | code review |
| REQ-SIM-005 | sim2 results are used only for COU-1 until EXP-V01, V02, V04 calibrate it and EXP-V05 passes | design review |
| REQ-RVH (proposed, for the lead) | The Rev H refill's front stop follows the nose deflection, or allows at least the usable travel × cot θ_min + 0.3 mm of extension | CAD check; EXP-V02 part B; sim2 `frontstop` stage |

**Proposed experiments:** EXP-V01 to EXP-V06 (§8.5).

## 12. Files

| Path | What |
|---|---|
| `sim2/params.py` | Labelled parameters, `Config`, `h1_check_config`, `calibrated_arm`, `from_identified` |
| `sim2/builder.py` | MJCF generation, model build, reset |
| `sim2/contact.py` | H1 contact law (numba kernel and Python reference) |
| `sim2/sim.py` | Stepper, nose servo, recording, `run` |
| `sim2/sensors.py` | Offline streams (fusion), online sensors |
| `sim2/hand.py` | Articulated arm, writer controller, FRF tools, fit to H1 |
| `sim2/tremor.py` | Tremor profiles, generator, calibration |
| `sim2/plugins.py` | Plug-in interface and the four plug-ins |
| `sim2/myo.py` | MyoSuite MyoArm pen-grasp impedance |
| `sim2/h1compare.py` | H1 comparison and diagnosis |
| `sim2/verify.py` | Contact, convergence, energy, gyroscope, sensor checks |
| `sim2/validate.py` | Literature validation and hand-model studies |
| `sim2/env.py` | Gymnasium environment and DR |
| `sim2/run_study.py`, `sim2/report.py`, `sim2/evidence.py` | Study stages, report, ledger rows |
| `sim2/tests/` | Fast tests (≈15 s) and slow tests (`--runslow`) |
| `results/sim2/sim2.json` | Headline numbers of every stage |
| `results/sim2/verification.json`, `validation.json`, `myo_impedance.json`, `env_benchmark.json`, `plugins.json`, `arm_calibration.json` | Stage results |
| `results/sim2/fig_sim2_*.png` + `.csv` | Figures with their data |
| `results/sim2/evidence_rows.csv` | Proposed ledger rows (23 columns) |
| `results/sim2/viz_sim2.json` | Replay in the viewer's format (seed 300, 8 Hz, 1 mm: unmodified, oracle, causal) |

## 13. Sources opened by this study

Full text unless marked. Ledger rows in `results/sim2/evidence_rows.csv`.

- MuJoCo and contact: CON-53 Todorov et al. 2012; CON-54 Todorov 2014; CON-55 Erez et al. 2015; CON-56 Castro et al.; CON-57 Le Lidec et al.; CON-58, CON-59 MuJoCo documentation.
- Handwriting: CON-60 Plamondon 1995 (abstract only); CON-61 Plamondon & Djioua 2006 (abstract only); CON-62 Mergl et al. 1999 (abstract only).
- Credibility: CON-63 FDA 2023 guidance; CON-64 ASME V&V 40-2018 (product page only); CON-65 Viceconti et al. 2021.
- Hand and muscle: HAP-95 Mussa-Ivaldi et al. 1985 (abstract only); HAP-96 Gomi & Osu 1998 (abstract only); HAP-97 Perreault et al. 2004 (abstract only); HAP-98 Milner & Franklin 1998 (abstract only); HAP-99 Burdet et al. 2001 (abstract only); HAP-100 Caggiano et al. 2022 (MyoSuite); HAP-101 van der Zee et al. 2026.
- Tremor: PDT-53 Corie & Charles 2019; PDT-54 Timmer et al. 1993 (abstract only); PDT-55 Elble 2003 (abstract only); PDT-56 Hess & Pullman 2012; PDT-57 Gallego et al. 2010.
- Sim-to-real: OPT-55 Tobin et al. 2017; OPT-56 Peng et al. 2018; OPT-57 Tan et al. 2018; OPT-58 Hwangbo et al. 2019; EML-70 Muratore et al. 2022; EML-71 Chebotar et al. 2019; EML-72 Kristensen et al. 2004.
- Existing ledger rows used as comparators: HAP-26, HAP-32, HAP-33, CON-01, CON-02, CON-07, CON-08, CON-13, CON-20, CON-24, CON-25, CON-27, PDT-07, PDT-08, PDT-09, PDT-15, PDT-31, OPT-37, OPT-45.
- Derived rows of this study: CON-66 to CON-69, HAP-102, HAP-103, PDT-58, OPT-59, EML-73.
