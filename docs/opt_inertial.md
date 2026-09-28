# Rev H: active-nose pen with inertial options (study `opt/inertial`)

**Status: proposed design, sized and tested in simulation only.** Nothing here was built or measured on a pen or a person. Evidence labels:
- **SIM**: the hand–pen model H1 (`sim/handpen`, extended here, §3.1) with the fusion sensor models, on synthetic handwriting and synthetic tremor;
- **CALC**: formulas, design models and linear-model bounds;
- **MFR / LITERATURE**: a manufacturer or published statement, with its ledger id (`docs/evidence.csv`, or the proposed rows in `results/opt/inertial_evidence_rows.csv`);
- **ASSUMPTION**: an input or a choice nobody has measured.

All numbers come from `results/opt/inertial_opt.json` (provenance block: git revision, parameter digest, seeds, library versions). The interface files for the other Rev H work are `results/revH/tip_params.json` and `results/revH/layout.json`. Seed plan (no test leakage):
- every choice (tracker setting, actuator, add-on controllers, neural policy) used training seeds 300–315, validation seeds 316–319 and glyph training writers 330–331;
- test seeds 200–203 (lognormal writing) and glyph test writers 210–213 were used for the final tables only.

## 1. Answer

**What I chose, and why.**
- **Architecture B for the active nose.** A skid ring on the **fixed** front sleeve carries the writing force. The refill carrier (the "nose") tilts on a 2-axis flexure gimbal 45 mm behind the tip, so the ball moves up to ±3 mm relative to the hand. The refill slides axially on a soft constant-force spring so the ball stays on the paper. Two flat voice-coil pairs 79 mm behind the tip, reacting against the handle (and so against the hand), drive it; a 3-D Hall sensor reads its position.
- B beats A (a rigid nose carrying the writing load, no skid) on every simulated criterion (§4, SIM, test seeds, r_rot 0.5):
  - ceiling with perfect knowledge of the tremor: B leaves 0.09–0.24 of the ink error, A 0.15–0.77;
  - coil power: B about 0.004 W, A 0.31–1.00 W even with a bias spring (1.7–2.8 W without);
  - A changes the writing force by 0.31–0.71 N rms, because a rigid nose that tilts in the tilt plane must press the tip into the paper or lift it. B's refill slides instead (δ cot θ).
- **The rear-cap inertial module is not included in the standard Rev H.** It is a 19.8 g tungsten slug moved ±2.75 mm on two axes by flat voice coils, 27.8 g added in all. It meets the lead's guide (≤ 30 g, ≤ 0.5 W: at most 0.051 W), but:
  - on top of the nose it adds a further 17 % at r_rot 0.5 and 17 % at r_rot 0.7 (8–12 Hz, 1–2 mm; 12–20 % and 7–24 % over the four test seeds);
  - it adds only 6 % at r_rot 0.3 (15 % after a grip calibration that identifies the plant);
  - the rule I set after the first test grid (≥ 10 % on every test seed at r_rot 0.5 and 0.7) is not met at r_rot 0.7 once the pen-mass bookkeeping bug was fixed (§9.5);
  - it makes the pen 103 g with the 14500 cell, over the 100 g guide by 3 g, or 92 g with a 10440 cell (about 7–9 h of writing).
  - It stays an evaluated option: the CAD variant `--addon`, and optional components in `layout.json` marked not recommended. Re-test it on the bench (EXP-I06) if EXP-I01 finds r_rot ≥ 0.5.
  - A gyroscope (CMG) pair per axis does not fit the budget: 81 g and 0.42 W (CALC).
- **A passive weight is not recommended.** The same 27.8 g fixed in the cap, added to the nose, helps on average, but it makes 38 % (r_rot 0.5) and 42 % (r_rot 0.7) of the 8–12 Hz, 1–2 mm test cases worse than the nose alone: it lowers the hand–pen resonance into the 10–12 Hz band (the pen alone with the weight: up to 1.6 × more tremor at r_rot 0.7). This matches the literature: weights help some people with essential tremor (ACT-18, ACT-19) but not in Parkinson's disease (ACT-32).

**How much it helps (SIM; ratio = ink error with correction ÷ without; lower is better).**

| Tremor at the hand, 8–12 Hz | r_rot 0.3 | r_rot 0.5 | r_rot 0.7 |
|---|---|---|---|
| Nose, perfect knowledge (the mechanism's ceiling) | 0.18 | 0.18 | 0.17 |
| **Nose, causal** (IMU tracker, Rev H setting), 1–2 mm | **0.64** | **0.70** | **0.76** |
| Nose + rear reaction mass, causal, 1–2 mm | 0.61 | 0.59 | 0.63 |
| Nose, causal, 0.3 mm | 0.89 | 0.93 | 0.96 |
| Nose, causal, wrist tremor 1 mm at 8 Hz | 0.75 | 0.78 | 0.80 |

- The mechanism can remove 76–91 % of tremor up to 2 mm. With today's tracker the pen removes **12–48 % of 1–2 mm tremor at 8–12 Hz** (24–36 % on average), 3–12 % of 0.3 mm tremor, and **nothing at 4–6 Hz**. The gap is the tracker (telling tremor from writing on an IMU), not the mechanism, the travel or the servo (§5.3).
- At 4–6 Hz the tracker does not lock onto the tremor: its frequency estimate sits at 8–11 Hz (8.0 Hz for a 4 Hz, 2 mm tremor: the second harmonic). A per-user calibrated frequency band removes the lock and gives 0.87–0.93 at 6 Hz (1–2 mm), but nothing at 4 Hz, and with the band set for 4.4 Hz it moves tremor-free writing by 34 µm (§5.2). Parkinson's rest tremor at 4–6 Hz is therefore not a stabiliser target for Rev H; it is a target for cues and practice (other Rev H work).
- False correction (tremor-free writing moved by the nose, closed loop): 10.4 µm on lognormal writers and 12.9 µm on sharp glyph writers with the Rev H tracker setting (shipped setting: 2.7 / 8.5 µm).

**Mass, size, power, battery (CALC, PROPOSED DESIGN).**
- Handle Ø22 × 170 mm; 75.0 g without the module (handle 67.1 g, moving nose 7.9 g; 2.97 g effective at the tip); centre of mass 93 mm from the tip. All fit checks pass (`layout.json` `fit_checks`).
- The guidance board's pen magnet adds 1.2 g. At the board study's placement its keel limits the writing tilt to ≥ 51° (§8.4).
- Power while writing: 0.081 W (0.065 W electronics and radio, 0.012 W drivers and Hall, about 0.004 W of coil loss: the nose only steers, the skid carries the load). With the EEMB LIR14500 (750 mAh, AMF-80) that is about **27 h of continuous writing**; with the module in the worst test case, 17 h.

**Methods and what each contributed.**
- **Adjoint (autograd) design optimisation** of the nose actuator (§7.1): pivot position, arm, magnet and coil sizes. It found that the magnet gap must clear the other axis's stroke; that halves the flux and sets Km 0.47 N/√W at the magnets (0.36 at the tip). Gradients agree with central differences to 1e-8.
- **Multi-objective Bayesian optimisation (ParEGO)** of the tracker for Rev H (§7.2): it moved the frequency gate from 5.88 to 3 Hz and the amplitude cap from 2.43 to 5.7 for the larger travel. Tremor-band ratio 0.71 against 0.85 for the shipped set on training seeds, within the pre-declared false-correction rule. On the test grid it turns the shipped set's 0.88 into 0.70 (r_rot 0.5, 8–12 Hz, 1–2 mm).
- **Neural controller trained through a differentiable model** (backpropagation through time, §7.3) for the reaction mass. It matches the model-based feed-forward but does not beat it (nose + module 0.69 against 0.68 at r_rot 0.5) and moves glyph writing more (29 µm). Ship the model-based law.
- Datasheet checks (MFR): commercial wideband haptic actuators cannot act as a 4–12 Hz reaction mass, because their suspension resonance (65–320 Hz) returns the force (AMF-74, AMF-75). SMA wire is too slow (AMF-77).

**Figures.** `results/opt/fig_in_arch.png` (A vs B), `fig_in_splits.png`, `fig_in_calib.png`, `fig_in_addon.png`, `fig_in_sweep.png`, `fig_in_tracker.png`, `fig_in_adjoint.png`, `fig_in_neural.png`, `fig_in_time.png`, `fig_in_cad.png` and `fig_in_cad_addon.png`. Each has a CSV twin with the plotted numbers. 3-D replay: `results/opt/viz_inertial_opt.json` (8 Hz, 0.3 mm) and `viz_inertial_opt_1mm.json` (10 Hz, 1 mm), in the `viewer/` format.

## 2. How the pen is held and what moves

- **Held.** Tripod grip on the fixed front sleeve (finger pads at z 26–38 mm from the tip, web of the thumb at z ≈ 92 mm; the grip zone is z 20–45 mm). The pen rests at about 50° (35–75° allowed).
- **What carries the writing force.** A C-shaped heel skid ring (contact radius 5.5 mm, open at the front so the writer sees the ink) on the fixed sleeve. The ball protrudes 4.2 mm ahead of the ring plane at 50°. The refill's constant-force spring sets the ink force (0.15 N, ASSUMPTION from the pencil study).
- **What moves.** The nose: a titanium refill carrier (Ø7 mm) with a PEEK nozzle, an aluminium rear arm and four NdFeB magnets (7.9 g in all). It tilts on a laser-cut cross-strip gimbal at z 45 mm. The magnets at z 79 mm move 2.27 mm when the ball moves 3 mm (lever 1.32). Four flat coils with a soft-iron return ring sit in the handle around the magnets.
- **What it reacts against.** The coils push on the handle, so the reaction goes into the hand. The ball moves relative to the hand; the hand is hundreds of times heavier, so its motion changes little. Because the skid on the fixed sleeve rests on the paper, the ball can move across the paper without changing the writing force.
- **The evaluated inertial module (rear cap, z 151–169 mm; not fitted as standard, §6).** A tungsten slug (Ø10 × 14 mm, 19.8 g, ASTM B777 non-magnetic grade, AMF-49) on flexures, moved sideways ±2.75 mm by four flat coils, with a 5 Hz centring loop. Its reaction pushes the handle, so it moves the **whole pen** against the shake. The nose then corrects what is left at the tip.
- **Why a nib-only stage is not enough (the user's concern).** The pencil moved only its refill by ±0.3 mm. Rev H moves the whole nose by ±3 mm, which covers 1–2 mm tremor with room to spare (at its limit at most 4.4 % of the time in the test grid). The evaluated inertial module would move the pen body itself. Neither can pull the hand along a letter: a pen has nothing to push against except the hand. That needs the grounded guidance board (other Rev H work).

## 3. Model, sensing and control

### 3.1 Model H1, extended (SIM)

- H1 (`sim/handpen`): rigid pen with 5 degrees of freedom, a two-zone grip (finger pads and web) calibrated to the tip-referred hand impedance of HAP-26 (575 N/m), a hand mass, LuGre paper friction at the skid and the ball, and a kinematic nib stage. It integrates at 25 µs and records at 2–4 kHz. The grip split r_rot (the share of grip compliance that is rotational) is unmeasured, so every headline result is given at 0.3, 0.5 and 0.7 (EXP-I01).
- Extensions made for this study (backward compatible; §9.7):
  - an optional grip-sleeve body on an actuated 2-axis pivot (for architecture A);
  - a stage command source: oracle (true disturbance), external estimate, or in-loop controller;
  - an in-loop controller hook at its own rate: an IMU model (400 Hz anti-aliasing, latency, noise), a linear state-space block, a small tanh MLP and an adaptive narrow-band block;
  - body mass changes for the Rev H parts and the skid geometry of the bigger nose.
- The Rev H pen is H1's pen with the CAD parts replaced by the Rev H parts (`opt/inertial/revh.py`: 75.0 g, centre of mass 93 mm).
- The nose of B is H1's kinematic stage with the Rev H travel (±3 mm usable, 3.5 mm stop), an 80 Hz 2nd-order servo and a 0.6 m/s slew limit. Its coil forces are computed from the simulated trajectory: moving mass, suspension, ball loads, bias.
- A is a sleeve on an actuated pivot carrying the writing load, with a PID Hall servo and a bias spring.

### 3.2 Estimator: the accelerometer tracker

- The fusion AKF (`fusion.estimators.akf`, read-only) runs on the H1 records.
  - The IMU streams are built from the true pen motion and rotation of H1, through fusion's own sensor models (noise, bias, scale, misalignment, gyroscope compensation of gravity and lever arm): `opt/inertial/tracker.py`.
  - The page sensor is assumed at 1 kHz, 2 ms latency, 3 µm (ASSUMPTION).
- Two settings were tested:
  - the shipped adjoint-tuned set (`results/opt/tracker_models/akf_ship.json`);
  - the Rev H setting chosen by ParEGO (§7.2; `results/opt/inertial_tracker_revh.json`).
- In closed loop the IMU sees the corrected motion. The add-on study therefore re-estimates on the closed-loop run.

### 3.3 Controllers

- **Nose (B):** the reference is minus the tracker's estimate of the handle-tip disturbance, followed by the 80 Hz servo (ASSUMPTION; sensitivity in §5.3).
- **Rear reaction mass**, three causal laws (`opt/inertial/addon.py`):
  - **(a) tracker-driven feed-forward:** at the tracked frequency the force is Re(H)·e(t) − Im(H)·e(t − T/4), where H = −G⁻¹ is the inverse of the linear model's tip response. The force is capped at 0.7 m ω² × stroke. G is the model at r_rot 0.5, or at the true split after a grip calibration (ASSUMPTION: a 2 s probe identifies it).
  - **(b) adaptive narrow-band feedback (phasor LMS)** at the tracked frequency, on the IMU's tip acceleration, with a per-frequency amplitude cap and an authority gate.
  - **(d) a neural policy**: MLP 10–12–2 on the tracker outputs and the mass position (§7.3).
- **(c) LQG / H2 / MPC with allocation.** Not pursued as a separate controller:
  - the plant for the nose is a stiff position servo, so allocation between nose and mass reduces to "mass first, nose on the rest", which the cascade already does;
  - the law in (a) is the H2-optimal single-frequency inverse within the force cap.
- **Architecture A:** PID position servo at 80 Hz on the Hall reading, integral corner 10 Hz, derivative filter 800 Hz, 5 kHz rate; the bias spring holds the static writing load.

## 4. Architecture A vs B (SIM, test seeds 200–203, r_rot 0.5)

| Tremor | f (Hz) | B perfect | B causal (Rev H tracker) | A perfect | A causal (shipped tracker) | A coil loss with bias (W) | A writing-force change (N rms) | B coil loss (W) |
|---|---|---|---|---|---|---|---|---|
| 0.3 mm | 4 | 0.09 | 1.00 | 0.17 | 1.00 | 0.31 | 0.31 | 0.0042 |
| 0.3 mm | 6 | 0.10 | 1.01 | 0.29 | 1.00 | 0.31 | 0.31 | 0.0041 |
| 0.3 mm | 8 | 0.10 | 0.95 | 0.54 | 0.93 | 0.31 | 0.31 | 0.0043 |
| 0.3 mm | 10 | 0.10 | 0.91 | 0.72 | 0.87 | 0.31 | 0.32 | 0.0042 |
| 0.3 mm | 12 | 0.10 | 0.93 | 0.77 | 0.87 | 0.31 | 0.32 | 0.0041 |
| 1 mm | 4 | 0.09 | 1.00 | 0.16 | 1.00 | 0.31 | 0.31 | 0.0041 |
| 1 mm | 6 | 0.10 | 0.98 | 0.28 | 1.01 | 0.32 | 0.31 | 0.0040 |
| 1 mm | 8 | 0.12 | 0.80 | 0.46 | 0.84 | 0.33 | 0.34 | 0.0040 |
| 1 mm | 10 | 0.16 | 0.72 | 0.52 | 0.75 | 0.45 | 0.41 | 0.0035 |
| 1 mm | 12 | 0.21 | 0.73 | 0.63 | 0.85 | 0.56 | 0.48 | 0.0035 |
| 2 mm | 4 | 0.10 | 1.00 | 0.15 | 1.00 | 0.32 | 0.31 | 0.0040 |
| 2 mm | 6 | 0.12 | 1.00 | 0.25 | 1.00 | 0.33 | 0.32 | 0.0042 |
| 2 mm | 8 | 0.16 | 0.72 | 0.24 | 1.00 | 0.36 | 0.38 | 0.0040 |
| 2 mm | 10 | 0.20 | 0.60 | 0.22 | 0.71 | 0.66 | 0.55 | 0.0038 |
| 2 mm | 12 | 0.24 | 0.64 | 0.29 | 0.63 | 1.00 | 0.71 | 0.0063 |

- A was evaluated at its earlier actuator design point (pivot 38 mm, Km at the tip 0.54 N/√W). The final B actuator (0.36 N/√W at the tip) would only raise A's power.
- Why A loses:
  - a rigid nose tilting in the tilt plane moves the ball along the pen axis's normal, so it pushes into or lifts off the paper, and the writing force changes by 0.3–0.7 N rms;
  - its actuator carries the writing load, so it needs a bias spring and still 0.3–1.0 W;
  - its result with perfect knowledge is worse at 8–12 Hz (0.22–0.77). A's run feeds the true handle motion to its servo in two passes; the rigid tip is held by paper friction and must be dragged (interpretation, not isolated in a separate run).
- The skid of B changes the feel of writing (the pencil study found 116 µm of device distortion from skid drag alone, `docs/pencil_mechanisms.md`). This is an ASSUMPTION to test in the EXP-H03 extension.

## 5. Rev H-B performance

### 5.1 Grip split, amplitude, frequency, wrist tremor (SIM, test seeds)

Causal = Rev H tracker setting; perfect = the stage cancels the true disturbance.

| Tremor | f (Hz) | causal r_rot 0.3 | causal r_rot 0.5 | causal r_rot 0.7 | perfect r_rot 0.5 | shipped tracker r_rot 0.5 |
|---|---|---|---|---|---|---|
| 0.1 mm | 4 | 1.03 | 1.02 | 1.01 | 0.09 | 1.00 |
| 0.1 mm | 6 | 1.00 | 1.01 | 1.01 | 0.11 | 1.00 |
| 0.1 mm | 8 | 0.98 | 1.00 | 1.01 | 0.12 | 1.00 |
| 0.1 mm | 10 | 1.00 | 1.00 | 1.00 | 0.14 | 0.99 |
| 0.1 mm | 12 | 1.05 | 1.02 | 1.01 | 0.13 | 0.99 |
| 0.3 mm | 4 | 1.00 | 1.00 | 1.00 | 0.09 | 1.00 |
| 0.3 mm | 6 | 0.99 | 1.01 | 1.01 | 0.10 | 1.00 |
| 0.3 mm | 8 | 0.93 | 0.95 | 0.97 | 0.10 | 0.99 |
| 0.3 mm | 10 | 0.88 | 0.91 | 0.96 | 0.10 | 0.96 |
| 0.3 mm | 12 | 0.88 | 0.93 | 0.95 | 0.10 | 0.97 |
| 1 mm | 4 | 1.00 | 1.00 | 1.00 | 0.09 | 1.00 |
| 1 mm | 6 | 0.97 | 0.98 | 1.00 | 0.10 | 1.00 |
| 1 mm | 8 | 0.76 | 0.80 | 0.88 | 0.12 | 1.00 |
| 1 mm | 10 | 0.68 | 0.72 | 0.79 | 0.16 | 0.84 |
| 1 mm | 12 | 0.66 | 0.73 | 0.76 | 0.21 | 0.83 |
| 2 mm | 4 | 1.00 | 1.00 | 1.00 | 0.10 | 1.00 |
| 2 mm | 6 | 0.96 | 1.00 | 1.03 | 0.12 | 1.00 |
| 2 mm | 8 | 0.69 | 0.72 | 0.74 | 0.16 | 1.01 |
| 2 mm | 10 | 0.55 | 0.60 | 0.68 | 0.20 | 0.87 |
| 2 mm | 12 | 0.52 | 0.64 | 0.72 | 0.24 | 0.76 |

Wrist (rotational) tremor about a pivot 175 mm behind the grip:

| Tremor | f (Hz) | causal r_rot 0.3 | causal r_rot 0.5 | causal r_rot 0.7 | perfect r_rot 0.5 | shipped tracker r_rot 0.5 |
|---|---|---|---|---|---|---|
| 0.3 mm | 4 | 1.00 | 1.00 | 1.00 | 0.09 | 1.00 |
| 0.3 mm | 8 | 0.89 | 0.93 | 0.94 | 0.12 | 0.97 |
| 0.3 mm | 12 | 0.98 | 1.01 | 1.00 | 0.14 | 0.96 |
| 1 mm | 8 | 0.75 | 0.78 | 0.80 | 0.13 | 0.88 |

- The ceiling barely depends on the split. The causal result is best at r_rot 0.3 (interpretation: more of the tremor appears as handle translation, which the IMU sees best).
- The nose was at its ±3 mm travel limit at most 4.4 % of the time (2 mm tremor at 10–12 Hz, mostly at r_rot 0.3); elsewhere essentially never.
- Tip force: 0.016–0.022 N rms per axis, mostly the static ball load. Copper loss about 0.004 W.

### 5.2 Per-user tremor band (SIM, test seeds, calibration 10 % high)

- The tracker's frequency search is limited to 0.75–1.3 × the user's calibrated frequency (`run_study.calibrated_params`). The calibration is assumed to identify the frequency within 10 %.
- On training seeds the exact calibration was at most 0.015 better than a 10 % error.

| Tremor | f (Hz) | open band r_rot 0.5 | calibrated r_rot 0.3 | calibrated r_rot 0.5 | calibrated r_rot 0.7 | frequency read (Hz), r_rot 0.5 |
|---|---|---|---|---|---|---|
| 0.3 mm | 4 | 1.00 | 1.00 | 1.01 | 1.01 | 5.2 |
| 0.3 mm | 6 | 1.01 | 0.98 | 0.98 | 0.99 | 6.3 |
| 0.3 mm | 8 | 0.95 | 0.94 | 0.96 | 0.97 | 8.1 |
| 0.3 mm | 10 | 0.91 | 0.89 | 0.92 | 0.97 | 10.1 |
| 0.3 mm | 12 | 0.93 | 0.87 | 0.93 | 0.96 | 12.0 |
| 1 mm | 4 | 1.00 | 0.99 | 1.00 | 0.99 | 4.6 |
| 1 mm | 6 | 0.98 | 0.92 | 0.93 | 0.95 | 6.0 |
| 1 mm | 8 | 0.80 | 0.77 | 0.80 | 0.83 | 8.0 |
| 1 mm | 10 | 0.72 | 0.68 | 0.74 | 0.81 | 10.0 |
| 1 mm | 12 | 0.73 | 0.66 | 0.74 | 0.77 | 12.0 |
| 2 mm | 4 | 1.00 | 0.99 | 0.99 | 0.99 | 4.4 |
| 2 mm | 6 | 1.00 | 0.87 | 0.87 | 0.88 | 6.0 |
| 2 mm | 8 | 0.72 | 0.69 | 0.73 | 0.74 | 8.0 |
| 2 mm | 10 | 0.60 | 0.58 | 0.61 | 0.69 | 10.0 |
| 2 mm | 12 | 0.64 | 0.53 | 0.64 | 0.72 | 12.0 |

- False correction on tremor-free writing, with the band set for each frequency (lognormal / glyph writers): 4.4 Hz: 33.8 / 4.8 µm; 6.6 Hz: 14.7 / 1.0 µm; 8.8 Hz: 7.5 / 2.2 µm; 11.0 Hz: 2.6 / 10.2 µm; 13.2 Hz: 4.9 / 14.8 µm.
- **Use:** only for tremor at about 5.5–7 Hz. There it turns no correction into 0.87–0.95 (1–2 mm, three splits). At 4 Hz nothing is gained, and writing is moved by 34 µm. At ≥ 8 Hz the open band is as good.

### 5.3 Travel and servo bandwidth (SIM, training seeds 300–303, r_rot 0.5, 6–12 Hz × 1–2 mm)

| Usable travel (± mm) | perfect, servo 30 Hz | perfect, 80 Hz | perfect, 150 Hz | causal, 30 Hz | causal, 80 Hz | causal, 150 Hz |
|---|---|---|---|---|---|---|
| 1 | 0.46 | 0.33 | 0.31 | 0.89 | 0.81 | 0.80 |
| 1.5 | 0.41 | 0.22 | 0.17 | 0.88 | 0.79 | 0.78 |
| 2 | 0.40 | 0.18 | 0.12 | 0.88 | 0.79 | 0.77 |
| 3 | 0.40 | 0.16 | 0.10 | 0.88 | 0.78 | 0.77 |
| 4 | 0.40 | 0.16 | 0.10 | 0.88 | 0.78 | 0.76 |

- With perfect knowledge, ±1.5–2 mm of travel and an 80 Hz servo capture most of the benefit: 0.22 at ±1.5 mm and 0.18 at ±2 mm against 0.16 at ±3 mm; 30 Hz is too slow (0.40).
- Causally, travel beyond ±1.5 mm and a servo beyond 80 Hz change the result by ≤ 0.03. ±3 mm is kept as margin for 2 mm tremor at the stops, for touchdown, and for later letter-shape nudges (other Rev H work).

## 6. Inertial options on top of the nose

### 6.1 Screen (CALC, frictionless linear model, optimally phased single-frequency input within limits)

- **Reaction mass** (27.8 g added): leaves 0.00–0.44 of 0.3 mm tremor at 4–12 Hz and 0.00–0.81 of 1 mm, over the three splits.
- **CMG** (two scissored pairs, 16 mm tungsten discs at 20 krpm on Faulhaber 0620 B motors, AMF-78): as strong on paper, but 81 g and 0.42 W (spin 0.09 W per rotor). Over the 30 g guide by a factor of 2.7, so it was not simulated further.
- **Passive weight** (27.8 g in the cap): 0.69–1.00 at r_rot 0.3; up to 2.2× amplification at 10–12 Hz at r_rot 0.5–0.7.
- **Wideband haptic actuators** (Actronika HFBA121238 / "Mark II-D", Alps AFT14A903A): unusable below their suspension resonance. They pass 0.4–3.5 % of the coil force at 4–12 Hz (CALC from AMF-74/75).

### 6.2 Time domain (SIM, test seeds, all three splits)

Mean ink error ratio against the Rev H pen with neither the module nor correction (so the module is credited with its mass and its control):

| Conditions | r_rot | nose (Rev H) | nose + passive weight | nose + module, feed-forward | nose + module, FF after grip calibration | nose + module, adaptive (AFC) | module alone, perfect knowledge | passive weight alone |
|---|---|---|---|---|---|---|---|---|
| 8–12 Hz, 1–2 mm | 0.3 | 0.64 | 0.56 | 0.61 | 0.55 | 0.60 | 0.65 | 0.79 |
| 8–12 Hz, 1–2 mm | 0.5 | 0.70 | 0.63 | 0.59 | 0.59 | 0.62 | 0.68 | 0.98 |
| 8–12 Hz, 1–2 mm | 0.7 | 0.76 | 0.71 | 0.63 | 0.65 | 0.67 | 0.78 | 1.23 |
| 0.3 mm, 4–12 Hz | 0.3 | 0.93 | 0.84 | 0.84 | 0.76 | 0.80 | 0.44 | 0.88 |
| 0.3 mm, 4–12 Hz | 0.5 | 0.96 | 0.87 | 0.80 | 0.80 | 0.83 | 0.42 | 0.92 |
| 0.3 mm, 4–12 Hz | 0.7 | 0.98 | 0.92 | 0.84 | 0.85 | 0.91 | 0.46 | 0.99 |
| 4–6 Hz, all amplitudes | 0.3 | 0.99 | 0.97 | 0.93 | 0.92 | 0.94 | 0.77 | 0.98 |
| 4–6 Hz, all amplitudes | 0.5 | 1.00 | 0.96 | 0.91 | 0.91 | 0.94 | 0.71 | 0.96 |
| 4–6 Hz, all amplitudes | 0.7 | 1.01 | 0.90 | 0.90 | 0.89 | 0.91 | 0.64 | 0.91 |
| wrist, 8 Hz | 0.3 | 0.82 | 0.81 | 0.74 | 0.69 | 0.69 | – | 0.94 |
| wrist, 8 Hz | 0.5 | 0.86 | 0.71 | 0.67 | 0.67 | 0.69 | – | 0.80 |
| wrist, 8 Hz | 0.7 | 0.87 | 0.60 | 0.64 | 0.67 | 0.72 | – | 0.63 |

- Feed-forward: false correction on tremor-free writing 10.8 µm (lognormal) / 10.3 µm (glyph). The adaptive (AFC) law: 22.0 / 20.8 µm. Ship the feed-forward.
- The module's copper loss: mean 0.008 W, at most 0.039 W (+0.012 W driver/Hall, ASSUMPTION).
- Stroke: the slug reaches its ±2.75 mm stops (peaks up to 2.8 mm) at 1–2 mm tremor and ≥ 8 Hz; at 0.3 mm the peaks stay at 1.3 mm (mostly the writing motion). The stops need soft bumpers, and the firmware should cap the command near the stops.
- With perfect knowledge (iterative learning), the module alone could remove 54–58 % of 0.3 mm tremor. The causal feed-forward removes 14–19 %. Again the tracker is the limit.

### 6.3 Decision

- **Not fitted in the standard Rev H.** `layout.json` keeps `rm_frame`, `rm_mass` and `rm_coils` as optional components with `meta.inertial_addon_recommended: false`; the CAD has the `--addon` variant.
- The criterion for "measurable" was set after the first grid, not before: at least 10 % further reduction at 8–12 Hz, 1–2 mm on every test seed at r_rot 0.5 and 0.7, and no split worse on average.
  - On the first grid, whose pen body was 7 g light (§9.5), it was met.
  - On the corrected run it fails at r_rot 0.7: one seed gives 7 %.
  - I did not move the threshold after seeing the new numbers.
- The mean benefit is real in the simulation (6 / 17 / 17 % at r_rot 0.3 / 0.5 / 0.7), but it is small against the tracker's gap to perfect knowledge, it costs 28 g, and it pushes the pen over 100 g.
- **Revisit if** EXP-I01 finds r_rot ≥ 0.5 and the bench test EXP-I06 shows ≥ 10 % with the nose on, or if a better tracker (EXP-E01) raises what the module's feed-forward can use.

## 7. Optimisation methods

### 7.1 Adjoint design of the nose actuator (CALC, `opt/inertial/adjoint.py`)

- A differentiable (PyTorch) lumped model: gap flux from magnet thickness, coil thickness and gap; force constant from the air-gap flux and the copper volume; moving mass and inertia; copper loss for the design tip force; penalties for stroke, peak force, travel and bore.
- The magnet–coil gap includes the other axis's stroke (a magnet moving sideways must clear its coil).
- Seven variables: pivot position, arm length, magnet width, length and thickness, coil thickness, travel. Objective: copper loss + μ × actuator mass, for μ = 0.5–20.
- Gradients by autograd; they agree with central finite differences to 1e-8 (`grad_check`).

| Mass weight μ | pivot z_p (mm) | arm (mm) | magnet w × l × t (mm) | coil (mm) | Km magnets (N/√W) | Km tip (N/√W) | copper (mW) | actuator mass (g) | mass at tip (g) |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 53.4 | 43.1 | 7.4 × 7.4 × 2.64 | 1.44 | 0.73 | 0.59 | 6.6 | 15.1 | 5.03 |
| 2 | 48.7 | 39.3 | 4.1 × 6.8 × 2.69 | 1.39 | 0.53 | 0.42 | 12.2 | 9.5 | 3.54 |
| 5 | 45.4 | 33.9 | 3.0 × 6.5 × 2.82 | 1.43 | 0.47 | 0.35 | 18.1 | 7.5 | 2.73 |
| 10 | 43.2 | 27.0 | 3.0 × 5.7 × 3.08 | 1.55 | 0.50 | 0.31 | 23.1 | 6.8 | 2.13 |
| 20 | 42.3 | 21.2 | 3.0 × 5.0 × 3.32 | 1.67 | 0.52 | 0.26 | 32.8 | 6.2 | 1.70 |

- Chosen: μ = 5, rounded to z_p 45 mm, z_a 79 mm, magnets 3.0 × 6.5 × 2.8 mm, coils 1.43 mm, travel 3 mm.
- The magnet width sits at its lower bound (3 mm). A narrower magnet would lower the mass further, at more copper loss.

### 7.2 Tracker setting by ParEGO (SIM, `opt/inertial/tracker_tune.py`)

- Ten AKF parameters (gain, frequency gate and width, amplitude gates, cap, slow-motion speed, harmonic weight, output filter, maximum frequency).
- 14 initial points and 36 Bayesian-optimisation iterations; objectives: the tremor-band ratio and the false correction.
- Training seeds 300–301 (lognormal) and glyph writers 330–331.
- Pre-declared rule: the lowest band ratio with lognormal distortion ≤ 15 µm and glyph ≤ 30 µm.
- Result: band ratio 0.71 against 0.85 for the shipped set; distortion 13.7 / 14.8 µm (lognormal / glyph). Changed settings: output gain 2 → 2.44; frequency gate (Hz) 5.88 → 3; gate width (Hz) 2.1 → 4; amplitude gate low (m) 2.36e-05 → 3.21e-05; amplitude gate high (m) 0.000133 → 0.000115; cap 2.43 → 5.7; slow-motion speed (m/s) 0.0153 → 0.028; harmonic weight 0 → 0.883; output low-pass (Hz) 36.2 → 64.1; maximum frequency (Hz) 14.2 → 14.7. At their bounds: frequency gate (Hz), gate width (Hz).

### 7.3 Neural reaction-mass controller (SIM, `opt/inertial/neural.py`)

- Model: the linear Rev H + hand + mass model at r_rot 0.5 with viscous paper, discretised at 2 kHz.
- Policy: MLP 10 → 12 (tanh) → 2. Inputs: the tracker estimate, two low-passed copies, the frequency, the authority and the mass position (Hall).
- Training data: tracker outputs from H1 runs on training seeds 300–311.
- Training:
  1. behaviour cloning of the phasor feed-forward: rms error 0.019 N of 0.078 N;
  2. BPTT fine-tuning of the ratio loss, with force, stroke and false-correction terms, 60 iterations;
  3. model selection on validation windows (seeds 316–317).
- Result: BPTT did not improve on the cloned policy on validation (0.951 after cloning; 0.959–0.965 during fine-tuning), so the cloned policy was kept.

| r_rot | nose alone | nose + feed-forward | nose + neural | feed-forward alone | neural alone | neural copper (W) |
|---|---|---|---|---|---|---|
| 0.3 | 0.76 | 0.72 | 0.73 | 0.88 | 0.89 | 0.012 |
| 0.5 | 0.80 | 0.68 | 0.69 | 0.77 | 0.78 | 0.008 |
| 0.7 | 0.85 | 0.70 | 0.72 | 0.82 | 0.83 | 0.007 |

Test seeds 200–203; six conditions: 6 Hz / 1 mm, 8 Hz / 0.3 and 1 mm, 10 Hz / 1 and 2 mm, 12 Hz / 1 mm. False correction of the neural policy: 11.4 µm (lognormal) / 28.9 µm (glyph), against 10.8 / 10.3 µm for the feed-forward.

- Cost: 182 multiply-accumulates and 12 tanh per 0.5 ms tick, about 0.9 % of the nRF54L15 (CALC, 2 cycles per MAC, 20 cycles per tanh, ASSUMPTION).
- Learning did not beat the model-based law: the information limit is the tracker's estimate, not the control law. A learned policy becomes interesting once recorded tremor exists (EXP-E01).

### 7.4 Slim envelope tiers T0–T2 (CALC, linear bounds only)

- Cap reaction mass, 0.3 mm tremor, 4–12 Hz, three splits:
  - T0 (5.2 g slug, Ø8.9 pencil): 0.48–0.95;
  - T1 (10.2 g, Ø11): 0.00–0.87;
  - T2 (19.5 g, Ø16 cap bulb): 0.00–0.63.
- These single-frequency bounds are optimistic: the time-domain oracle realised a quarter to a half of them in study I1.
- The slim tiers need ≥ 10 g of moving mass to matter, which is why the bigger grip (Rev H) is the primary product.

## 8. Hardware

### 8.1 Bill of materials

Buy (with ledger ids):

| Item | Part | Ledger |
|---|---|---|
| Ink refill and ball | ISO 12757-2 D1 mini refill | DEC-004 |
| Cell | EEMB LIR14500, 750 mAh, 1.5 A (option LIR10440, 320 mAh) | AMF-80 (AMF-31) |
| MCU and radio | Nordic nRF54L15 | AMF-44 |
| Coil drivers | TI DRV8214 × 2 (× 4 with the module) | AMF-37 |
| Motion sensor | ST LSM6DSV16X | OPT-37 |
| Nose position | TI TMAG5273 3-D Hall (20 kSPS single axis) or 2 × DRV5055, with a 1 × 1 mm N45 magnet (supermagnete S-01-01-N) | OPT-45, OPT-46, AMF-72 |
| Nose magnets | 4 × NdFeB N45 blocks 3.0 × 6.5 × 2.8 mm | AMF-28 |
| Cue motor (optional) | 8 mm coin LRA | AMF-45 |
| Module slug (optional) | tungsten heavy alloy ASTM B777 class 3, non-magnetic grade, Ø10 × 14 mm | AMF-49 |
| USB-C receptacle, charger | to select | – |
| Paper sensor (optional) | optical-flow class, to select | – |

Make (custom):

| Part | Material | Notes |
|---|---|---|
| Refill carrier | Ti-6Al-4V tube 7/6 mm (AMF-21) | 35.5 mm |
| Nose nozzle, rear cap | PEEK (AMF-24) | |
| Rear arm | aluminium 6061 | carries the magnet hub |
| Magnet hub, return ring | soft iron / 1010 steel, nickel plated | 14 mm ring around the coils |
| Flexure gimbal (2-axis cross-strip) | 301 full-hard or 17-7PH, 0.1 mm, laser cut (AMF-20) | bending stiffness 0.025 N m/rad (ASSUMPTION) |
| Four flat coils (nose) | self-bonding 0.1 mm magnet wire, IEC class 155 (AMF-29, AMF-30) | 1.43 mm thick |
| Front sleeve | PEEK core + TPE overmould | fixed grip |
| C-shaped heel skid ring | PTFE-coated POM | contact radius 5.5 mm |
| Constant-force refill spring | music wire, long soft spring | 0.15 N (ASSUMPTION) |
| Handle shell | PEEK or glass-filled nylon, 1 mm wall | Ø22 × 120 mm |
| Module frame, flexures, four coils (optional) | aluminium; 17-7PH; magnet wire | z 151–169 mm |

- No prices or lead times are quoted: none were seen on a page.
- CAD: `mechanics/cad/revH_pen.py` builds the whole pen (STEP `results/cad/revH_pen_assembly.step`, drawing `results/cad/drawing_revH_pen.png`, with `--addon` the module variant). It uses the same layout source as `results/revH/layout.json` (`opt/inertial/geometry.py`).

### 8.2 Drive electronics and power (CALC)

- Nose coils:
  - each axis pair on one DRV8214 H-bridge (current mirror for current control) from the 3.7 V cell;
  - Km 0.47 N/√W per axis at the magnets;
  - peak tip force 0.84 N (3.7 V × 1.5 A), continuous 0.21 N (0.35 W per axis, ASSUMPTION thermal);
  - needed: about 0.02 N rms.
- Module coils: two more DRV8214; Km 0.9 N/√W (ASSUMPTION, scaled from AMF-02/AMF-73); 0.5 N force limit.
- Power: 0.081 W typical (base 0.065 W ASSUMPTION); the module adds at most 0.051 W. The LIR14500 gives 2.2 Wh usable (80 %, ASSUMPTION): about 27 h, or 17 h with the module in the worst case.

### 8.3 Firmware sketch

- Rates:
  - IMU FIFO and tracker at 2 kHz;
  - nose servo at 10 kHz on the Hall reading (PID, 80 Hz bandwidth);
  - module feed-forward at 2 kHz.
- States:
  - off;
  - idle (nose held centred at low gain);
  - calibrate (20–30 s: tremor frequency, grip probe for the module's plant);
  - write (pen down: tracker + nose; module if fitted);
  - lift (pen up: nose re-centres at ≤ 0.6 m/s);
  - fault (over-travel, over-current or low cell: nose centred, coils off).
- MCU load on the nRF54L15 (CALC):

| Task | Load |
|---|---|
| Tracker (AKF) | 6.2 % |
| Nose PID at 10 kHz | about 1 % |
| Module phasor feed-forward | about 0.3 % |
| Neural policy, if used instead | 0.9 % |

### 8.4 The guidance board's pen magnet (added at the lead's request; CALC, `opt/inertial/board_magnet.py`)

- **What.** The board study (`docs/guidance_board.md`) steers the pen through one disc magnet: K&J D42-N52, 6.35 × 3.17 mm, 0.75 g (MFR AMF-91), magnetised along the pen axis.
  - It sits in a keel under the fixed front sleeve, 13.5 mm along the axis from the ball and 10.2 mm off the axis toward the paper (3.8 mm above the paper at 50°).
  - It is in `layout.json` and the CAD as the optional components `board_magnet` (group `magnet`) and `board_keel`; the checks are in `layout.json` → `board_magnet_checks`.
- **Fit against the sleeve.** The wall between the magnet and the swinging carrier is 1.1 mm: it fits.
- **Fit against the paper (the problem).** The keel (0.5 mm walls, ASSUMPTION), measured from the paper plane through the skid-ring heel, clears the paper by:

| Pen tilt | 35° | 40° | 45° | 50° | 60° | 75° |
|---|---|---|---|---|---|---|
| Keel clearance (mm) | −2.7 | −1.8 | −0.8 | 0.17 | 2.1 | 4.8 |

- So at this placement the keel rubs at the nominal 50° and hits the paper below about 49°. With the magnet fitted, the usable tilt is ≥ 51° (0.3 mm clearance). Options, for the board study to re-run its force model:
  - (a) keep it, and write at ≥ 52° in board mode;
  - (b) move it 5.3 mm rearward (13.5 → 18.8 mm): clears 35°, but the magnet centre rises from 3.8 to 7.9 mm above the paper;
  - (c) turn the disc to face the paper (radial magnetisation) at 15.8 mm, 8.6 mm off the axis: clears 35°, centre at 6.6 mm.
- **Clash with the optional paper sensor.** The keel overlaps the place of the optional optical paper sensor (z 14–20 mm, paper side). If both are fitted, the paper sensor moves to the side.
- **Crosstalk** (magpylib; no shielding counted, so an upper bound):

| Field source | At the nose Hall sensor | At the IMU |
|---|---|---|
| Pen magnet (static in the pen) | 60 µT: a constant offset, removed by calibration (the TMAG5273's noise is 110–125 µT rms at default averaging, OPT-45) | 47 µT |
| Board head (D88-N52 3.7 mm under the surface, ±24 mm around the pen, raised or retracted) | 240–810 µT, changing by up to 660 µT. With the position magnet's 16 mT/mm slope, that reads as up to 48 µm of false nose position at the tip | 200–650 µT |

  - The IMU (LSM6DSV16X) has no magnetometer, so neither field enters its readings.
  - The coil's soft-iron back ring around the Hall sensor will shield part of the head field (not modelled).
  - Mitigation, if EXP-I05 / EXP-G03 confirm the error: the board sends its head position and the pen subtracts a calibrated field map, or a second Hall sensor works as a gradiometer.
- **Mass.** +1.2 g (0.75 g magnet, 0.3 g keel ASSUMPTION, +10 %): 76.1 g.
- **Board forces on the pen.**
  - The board's normal pull (about 1 N while guiding) adds to the writing force on the skid ring. In architecture B the skid carries it, not the nose actuator; skid friction rises by about 0.15 N (μ 0.15).
  - The board's force bandwidth (25 Hz) overlaps the tremor band. The IMU tracker would read board-driven handle motion as disturbance, and the nose would partly undo the guidance at 3–15 Hz. Either band-limit the board's command below about 3 Hz while the stabiliser runs, or send the board's force command to the pen so the tracker can exclude it.
  - Neither effect was simulated here.

### 8.5 Patents to clear (no legal assessment here)

- The active nose is close in structure to two Verily patents in the ledger:
  - **PAT-12** (US 11,944,216 B2): a housing held by the hand; a motion-generating mechanism in it; an attachment arm moved relative to the housing; a motion sensor; a controller; dependent claims with a relative-motion sensor;
  - **PAT-08** (US 9,943,430 B2): IMU feedback, 2-axis actuators, actuator position sensors.
- The ledger marks PAT-12 as a priority freedom-to-operate item for an attorney. Points for the attorney, not conclusions:
  - whether a refill carrier is an "attachment arm ... for a user-assistive device";
  - whether a flexure gimbal driven by flat voice coils is a "motion-generating mechanism" (the dependent claims name motors, bearings and gear reductions);
  - that the writing load goes through a skid on the fixed sleeve;
  - the expiry of the 2011 priority chain and any live continuations.

## 9. Decision, acceptance, experiments, limits, files

### 9.1 Proposed decision text (revises DEC-024; the lead merges)

> **DEC-024 (revised 2026-09-28): the active nose is the physical corrector; no inertial helper in the standard Rev H.** In Rev H (DEC-029) the nose (refill carrier on a 2-axis flexure gimbal at 45 mm, ±3 mm at the ball, flat voice coils at 79 mm reacting against the handle) moves the tip; a C-shaped skid ring on the fixed front sleeve carries the writing force (architecture B). A rear-cap tungsten reaction mass (19.8 g, ±2.75 mm, 2 axes, 27.8 g added, driven by the tracker's feed-forward) was evaluated and is not fitted: it adds 6 / 17 / 17 % at r_rot 0.3 / 0.5 / 0.7 for 28 g and takes the pen over 100 g; it stays an option to re-test (EXP-I06). No passive weight, CMG, gyroscope or grip gimbal. The tracker uses the Rev H setting; a per-user frequency band is used only for tremor at 5.5–7 Hz. **Alternatives:** A (rigid nose carrying the load); CMG pair; passive weight; neural RM controller; AFC. **Evidence:** `docs/opt_inertial.md`, `results/opt/inertial_opt.json` (H1, test seeds 200–203, three grip splits): B ceiling 0.09–0.24 against A 0.15–0.77; B coil loss ≈ 0.004 W against A 0.31–1.00 W; causal 0.64 / 0.70 / 0.76 at 8–12 Hz, 1–2 mm (r_rot 0.3/0.5/0.7), nothing at 4–6 Hz; the module adds 6 / 17 / 17 % at ≤ 0.051 W, below the ≥ 10 %-on-every-seed rule at r_rot 0.7; the passive weight worsens 38–42 % of the 8–12 Hz, 1–2 mm cases at r_rot 0.5–0.7 (ACT-62…69, OPT-48, OPT-49) — simulation, calculation. **Status:** proposed. **Revisit if:** EXP-I05 misses Km or bandwidth; EXP-H03 rejects the skid ring (then A); EXP-I01 finds r_rot ≥ 0.5 and EXP-I06 shows ≥ 10 % (then fit the module); EXP-E01 shows a tracker that closes the gap to perfect knowledge (then revisit travel and module size).

### 9.2 Acceptance criteria (proposed)

| Id | Criterion | Pass line | Test |
|---|---|---|---|
| AC-I05-1 | Nose force constant per axis at the magnets | ≥ 0.40 N/√W over ±2.3 mm magnet stroke | EXP-I05 |
| AC-I05-2 | Usable ball travel with the skid on paper, 35–75° | ≥ ±2.5 mm, cross-coupling ≤ 10 % | EXP-I05 |
| AC-I05-3 | Closed-loop nose bandwidth (−3 dB) with Hall noise | ≥ 60 Hz, phase margin ≥ 45° | EXP-I05 |
| AC-I05-4 | Coil + driver power while writing on a tremor rig (1 mm, 10 Hz) | ≤ 0.1 W | EXP-I05 |
| AC-I05-5 | Writing-force change caused by the nose | ≤ 0.05 N rms | EXP-I05 |
| AC-I06-1 | Module on the hand simulant at r_rot from EXP-I01, 10 Hz, 1 mm | ≥ 10 % further reduction with the nose on | EXP-I06 |
| AC-I07-1 | Tracker on recorded tremor, 8–12 Hz, ≥ 1 mm | ratio ≤ 0.8, distortion ≤ 15 µm | EXP-I07 / EXP-E01 |

### 9.3 Experiments (what to measure first)

1. **EXP-I05 (new): active-nose bench.**
   - Build: the nose, gimbal, coils and skid on a rigid handle clamped to a 2-axis shaker.
   - Measure: Km and its map over the stroke (force gauge, current), the gimbal stiffness, the travel at 35/50/75°, the servo bandwidth with the real Hall noise, power, and the writing-force change (force plate under the paper).
   - Pass lines: AC-I05-1…5.
   - It gates the whole design.
2. **EXP-I01 (existing): grip split r_rot**, extended to the Ø22 Rev H handle. It decides whether the module is worth fitting (6 % at r_rot 0.3 against 17 % and 17 % at 0.5 and 0.7).
3. **EXP-E01 / EXP-I07: the tracker on recorded tremor writing**, with the Rev H setting and the calibrated band. It decides the causal numbers, which are the weakest link.
4. **EXP-H03 extension: C-shaped skid feel, visibility and smear** with Rev H at 35–75°.
5. **EXP-I06 (replaces EXP-I04): rear module on the hand simulant.**
   - Setup: the EXP-I05 rig with the module in the cap and the EXP-I01 compliance.
   - Measure: stroke use, end-stop impacts (sound and acceleration) and power.

### 9.4 Assumptions (all untested)

- **Hand and grip:** hand impedance HAP-26 in a Ø22 grip; the grip split (swept 0.3–0.7).
- **Contact:** skid friction 0.1–0.15; ball friction 0.15; refill spring 0.15 N.
- **Nose mechanics:** gimbal stiffness 0.025 N m/rad; the 80 Hz servo as a 2nd-order follower.
- **Electronics:** base electronics 0.065 W; driver/Hall 0.012 W.
- **Module:** Km 0.9 N/√W; module coil and frame mass 8 g.
- **Sensing:** page sensor at 1 kHz, 2 ms, 3 µm.
- **Tremor and writing:** a single-frequency tremor (fixed frequency); synthetic writing.
- **Calibration:** the grip calibration identifies the plant; the tremor frequency is calibrated within 10 %.

### 9.5 Limits

- **Model-to-model.** Every ratio is from H1, whose hand is calibrated only against a tip-referred impedance (HAP-26).
- **Tracker.** The tracker sees H1's true motion through fusion's sensor models, not real IMU data.
- **Design state.** A was run at its earlier actuator design point; the adjoint actuator model is lumped (no FEM).
- **A bookkeeping bug found and fixed during the study.** Three Rev H parts shared names with parts of the pencil CAD (pcb, skid_ring, refill_D1). H1 adds the new parts before it removes the old ones, so the three were dropped: the simulated Rev H pen weighed 67.9 g instead of 75.0 g.
  - Found by the study's own test (`test_revh.py::test_masses_and_body_mod`); fixed by prefixing the Rev H parts.
  - The tracker tuning and every B, add-on, sweep, calibration and neural result were then re-run. The ink ratios moved by at most 0.015. That was enough to move one seed below the module rule's 10 % line at r_rot 0.7 (10.1 % → 6.8 %).
  - The architecture-A rows were not re-run: their moving nose lacked the 0.9 g refill.
- **Skid ring detail.** The skid ring is drawn as a plain tube. A heel contact at 5.5 mm radius (as simulated) leaves little room for the tapered nozzle at full travel (rough CALC: about 0.3 mm); check in the detailed CAD.
- **Seeds.** Four test seeds; distortion on four lognormal and four glyph writers.

### 9.6 Files, how to run, tests, run times

| What | Command | Time (4 shared cores, one process) |
|---|---|---|
| Whole study | `python3 -m opt.inertial.run_study` | about 35 min |
| Quick check (outputs to `results/opt/_cache/quick/`; final results untouched) | `python3 -m opt.inertial.run_study --quick` | about 2 min |
| One stage | `--stages nose_adjoint,tracker,grid,sweep,addon,calib,neural,tiers,report` | adjoint 22 s; tracker (ParEGO, 51 evaluations) 4 min; grid 7 min; sweep 67 s; addon 9.5 min; calib 3.7 min; neural 8 min; report 8 s |
| CAD | `python3 mechanics/cad/revH_pen.py [--addon]` | about 5 s per variant |
| Tests | `python3 -m pytest -q opt/inertial/tests` | about 8 s (43 tests) |

- **Code:** `opt/inertial/` (revh, geometry, catalog, linear_ext, control, tracker, tracker_tune, evaluate, addon, addon_eval, adjoint, neural, scen, figures, report, viz, evidence, run_study).
- **Results:** `results/opt/inertial_opt.json`, `results/opt/inertial_tracker_revh.json`, `results/opt/fig_in_*.png` (+ `.csv`), `results/opt/viz_inertial_opt*.json`, `results/opt/inertial_evidence_rows.csv` (ACT-61…69, AMF-73…80, HAP-36…38, OPT-48…49), `results/revH/tip_params.json`, `results/revH/layout.json`, `results/cad/revH_pen*`.
- **Stage caches:** `results/opt/_cache/inertial_stage_*.json`.

### 9.7 Changes to `sim/handpen` and proof that the default is unchanged

- **What was appended** (backward compatible):
  - to `core.py`: parameter names at the end of `NAMES` and record channels after the original 57;
  - to `params.py`: `Config` fields defaulting to off (`sleeve=None`, `stage_src=0`, `ctl=None`, `body_mod=None`, `skid_geom=None`, `stage_slew=0.08`), and the `Sleeve` dataclass;
  - to `model.py`: one packing call.
- **Proof** (`opt/inertial/tests/test_h1_regression.py`):
  - 23 cases covering every device, the stage, the oracle and the linear model, recorded before the change;
  - after the change: bit-for-bit equal hashes of the original 57 channels, the feed-forward inputs and the frequency responses;
  - all appended channels exactly zero.
- **Other checks** (`test_core_ext.py`):
  - a stiff sleeve equals the same mass fixed to the pen;
  - the pivot carries N cos θ z_p/(z_a − z_p);
  - the linear extension reproduces the original matrices;
  - external and in-loop stage commands give identical ink;
  - the IMU model matches the kinematics (correlation > 0.995);
  - the ZOH controller embedding integrates exactly.
- The required suite `python3 -m pytest -q sim/handpen sim/pencil fusion opt/touchdown` passes (86 passed in 67 s).
