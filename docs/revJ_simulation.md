# Rev J in the physics simulator: closed-loop study, round 2

Status: DRAFT while the test runs finish (sections marked (pending)).

**Evidence status.** Every number here is a SIMULATION (sim2, MuJoCo 3.6) or a CALCULATION on synthetic writers and
synthetic tremor, on a PROPOSED DESIGN. Nothing was built or measured. sim2 ranks concepts (context of use COU-1,
`docs/sim_v2.md` §8.1) until EXP-V01, EXP-V02 and EXP-V04 calibrate it and EXP-V05 validates it. None of these numbers
is evidence of benefit to people. Labels: SIM (sim2 run), CALC (calculation), LIT/MFR (ledger id), ASSUMPTION,
PROPOSED DESIGN.

## 1. The answer in plain words

(pending)

## 2. What was simulated

- **Simulator.** sim2: H1 contact law at the ball and the skid ring, the H1 hand (HAP-26 lumped grip and arm) and, for
  a subset, sim2's articulated 'arm' hand. Step 50 µs (sim2 §5.3: 0.66 µm against 12.5 µs; 25 µs check in §9).
- **Pen.** The lead's Rev J integration, read at run time from `results/revJ/sim_params.json` and
  `results/revJ/layout.json` (CALC on a PROPOSED DESIGN). Each result file records the version used (`pen_source`:
  generation time and SHA-256). The file changed during the study (last 13:28 UTC); the changes (heel-drive force
  0.369 N continuous / 0.603 N peak, Hall noise) do not touch the nose-only runs, and every wheel run used the last file.

| Part | Value used (label) |
|---|---|
| Handle incl. heel drive | 68.89 g, centre of mass 89.8 mm from the tip, 8.53·10⁻⁵ kg·m² transverse (CALC; the lead's budget to 0.1 %) |
| Moving nose (C1S gimbal at 76.48 mm) | 16.6 g without the refill; refill, holder, ink drum and spring 1.74 g; tip-equivalent mass 1.50 g (CALC; study N's model: 2.10 g) |
| Nose flexure and actuator | 0.0028 N·m/rad; Km 0.656 N/√W at the magnets (image method, an upper bound); 2.47 Ω, 1.5 A, 3.7 V; 80 Hz servo (CALC / ASSUMPTION) |
| Nose travel | 6.57 mm at 50° (soft limit), stop at 7.07 mm (CALC) |
| Refill | 0.15 N spring, −2.19 N/m, 0.01 N friction; front stop follows the nose 0.3 mm beyond contact; pen lift 0.5 mm after 8 ms (ASSUMPTION) |
| Skid ring | contact radius 11.65 mm, open 120° on top (CALC / ASSUMPTION) |
| Heel wheel | 2 mm wheel at 12.0 mm in the ring plane (0.35 mm beyond the ring); 0.55 N preload on 200 N/m; tyre–paper μ drawn 0.6–1.2 per case; bristle tyre 1500 N/m; rolling 0.078; back-drive 0.03 N; 0.603 N peak, 0.369 N continuous; copper loss 4.30 W/N² (CALC from the motor data) |
| End-cap (optional) | 30.39 g slug at 152.7 mm, ±4 mm, 5 Hz flexures, damping ratio 0.05, Km 0.735 N/√W, 1 W peak; fixed parts in the handle (pen 129.4 g, CALC) |
| Sensors | IMU at 56.25 mm, 8.42 mm off the axis (LSM6DSV16X model); page sensor 1 kHz, 2 ms, 3 µm, valid to 2 mm lift; nose Hall 5.9 µm rms; refill slide 1 kHz, 2 µm |

- **Writers.** The v2 writers of §3 (the v1 writers of the handwriting study for comparison). Test writers 0–5, test
  seeds 200–203. Every rule was fixed first on tuning writers 100–103, seed 300 (`results/sim2j/rules.json`, frozen
  14:02 UTC before any test run). RL trained on writers 1000–1399 only.
- **Tremor.** The project's tremor model on the hand path (H1), 4–12 Hz, 0.3–2 mm peak (severe: 3 mm); for the 'arm'
  hand, sim2's ET torque profile at the forearm and wrist, calibrated to the peak at the lifted tip.
- **Start of each ET run.** The pen rests on the paper for 4 s before writing, tremor on (ASSUMPTION: a person places
  the pen before writing; the tremor detectors need 2–4 s of signal). The ink of the rest is not scored.
- **Writer adaptation.** As in round 1, the writer has learned the pen: the hand path is corrected by iterative learning
  on the tremor-free run (3 passes, 10 Hz, time-advanced by the measured lag). sim2's stick-slip still leaves
  60–130 µm between the tremor-free ink and the intended letters (SIM). So the ink error is measured against the
  writer's own tremor-free ink letters ("clean ink"), and letters and words are read on the ink.
- **Metrics** (as the handwriting study). Ink error: rms distance of the in-contact ink to the clean-ink letters.
  Letters read: share read as the intended letter by the app's recogniser. Words: share read correctly after the app's
  autocorrect. Device share: share of the ink motion that comes from the device. Felt force: rms change of the grip
  force on the hand. Power: mean electrical power incl. 0.077 W electronics; battery 2.22 Wh usable. False correction:
  rms ink moved on tremor-free writing against the device-off pen with the same seed (project rule ≤ 25 µm).

## 3. Writer model v2 (CALC on synthetic writing)

- **What it is** (`sim2j/writers.py`). The handwriting study's glyph writers, re-timed. Along each pen-down piece the
  speed follows the two-thirds power law v = K (κ + κ₀)^(−1/3) (LIT CON-27), with an acceleration cap and smoothing in
  time; the writer stops at sharp corners (above 74°). Each writer draws a target speed from N(30.5, 7.9) mm/s, clipped
  to 18–45 mm/s (LIT CON-20); K is calibrated so the mean pen-down speed meets it. Letters have an x-height of 3.65 mm
  (CALC from LIT PDT-06's 5.0 mm median letter height).
- **Fit.** Seven shape parameters by Nelder–Mead on fitting writers 1000–1009 against CON-20, CON-24, CON-25 and CON-27
  (`results/sim2j/writer_fit.json`). Checked on held-out writers 1010–1019 and on test writers 0–5
  (`results/sim2j/writers.json`, `fig_writers.png`).

| Quantity (pen-down, intended path, "return library books by friday") | Target (LIT) | v1, test 0–5 | v2, held-out 1010–1019 | v2, test 0–5 |
|---|---|---|---|---|
| Mean speed | 30.5 mm/s (CON-20) | 18.3 mm/s | 26.8 mm/s | 31.0 mm/s |
| Median stroke (between speed minima) | 90–150 ms (CON-24) | 151 ms | 118 ms | 105 ms |
| Share of velocity energy at 8–12 Hz | 1.3–1.7 % (CON-25) | 17.3 % | 12.2 % | 10.1 % |
| 50 % / 90 % of that energy below | 3.1 / 4.9 Hz (CON-25) | 4.9 / 11.2 Hz | 4.4 / 10.7 Hz | 3.9 / 10.7 Hz |
| Speed–curvature exponent (fitted slope) | 2/3 (CON-27) | 1.00 | 0.80 | 0.80 |

- **What the refit fixed.** Speed (18 → 27–31 mm/s) and the speed–curvature law (slope 1.00 → 0.80). Stroke times stay
  in range.
- **What it did not fix.** The spectrum: 10–12 % of the velocity energy at 8–12 Hz, six to eight times the target
  (v1: 17 %).
  - Likely reason (not tested): CON-25 recorded large characters (about 14 mm), whose strokes are slower. At 3.65 mm and
    30 mm/s the glyphs' tight turns carry more fast motion. The target may not apply to small letters.
  - Consequence: tremor-free writing contains spectral lines a tremor detector can take for tremor. On the intended
    paths alone ai2's detector reaches peak ratios of 4–6 on v2 writers and 14 on one v1 writer (threshold 5; CALC).
    sim2's touchdown adds a 9.4 Hz line at the start of writing (SIM, tuning writer 100).
- **How the refit changes tremor separation** (`results/sim2j/writer_cmp.json`; test writers 0–2, their first test
  seed, 8 Hz × 1 mm and tremor-free writing, the same pen and tremor; SIM):

| Ratio to the device-off pen (lower is better) | v1 writers | v2 writers |
|---|---|---|
| Device off: ink error / letters read | 472 µm / 85 % | 434 µm / 92 % |
| Chosen tracker G4 | 0.69 | 0.73 |
| The same tracker without the runaway guard (detector gate kept) | 0.69 | 0.73 |
| ai2's gated listening tracker (GL) | 0.65 | 0.83 |
| Perfect knowledge (limit of the mechanism) | 0.10 | 0.14 |
| False correction on tremor-free writing: G4 / GL | 0 / 35 µm | 0 / 62 µm |

- On the refitted writers the guarded tracker loses a little (0.69 → 0.73) and ai2's listening tracker loses more
  (0.65 → 0.83), and its false correction almost doubles (35 → 62 µm). The listening model takes more of the faster
  v2 writing for tremor. Findings on v1 writers (round 1 and ai2) are therefore optimistic for listening estimators.

## 4. Controllers, and the rules fixed before the test

### 4.1 Tremor estimation: what was compared (tuning writers 100–103, seed 300; SIM)

- **G0: the Rev H tracker as built** (AKF re-tuned in round 1). On tremor-free v2 writing its frequency estimate runs
  to its bound and it moves the ink by 51–141 µm (4 writers; rule ≤ 25 µm).
- **G3/G4: the guarded tracker** (this study, `sim2j/akf_online.py`). The same AKF, run tick by tick (bit-exact against
  fusion's batch version), plus a runaway guard (re-seed the frequency at the detector's line or at 6.3 Hz, then lock
  it within ±1 Hz of the line) and ai2's tremor-line detector as a gate on the output. G3 uses ai2's threshold (open
  above a peak ratio of 5 for 0.5 s); G4 a stricter one (open above 8, close below 4).
- **GL: ai2's gated listening tracker (DEC-042), as built.** ai2's detector and amplitude gate weight a listening AKF;
  the Rev H tracker as built is the fallback.
- **GLG: gated listening with G4 as the fallback** (this study).
- The detectors see page-sensor samples taken while the ball is on the paper. The Rev J page sensor stays valid up to
  2 mm lift; with air moves in its input ai2's detector opened on tremor-free writing (SIM, tuning writer 100).

| Tuning cell (4 writers) | Device off: ink error | G3 | **G4 (chosen)** | GL (ai2, as built) | GLG |
|---|---|---|---|---|---|
| 6 Hz, 1 mm | 414 µm | 0.96 | 0.96 | 1.00 | 0.99 |
| 8 Hz, 0.3 mm | 117 µm | 1.03 | 1.02 | 1.16 | 1.02 |
| 8 Hz, 1 mm | 425 µm | 0.71 | 0.77 | 0.82 | 0.85 |
| 8 Hz, 2 mm | 892 µm | 0.58 | 0.58 | 0.55 | 0.55 |
| 10 Hz, 1 mm | 411 µm | 0.56 | 0.56 | 0.75 | 0.75 |
| False correction, mean (max) | – | 0 (0) µm | 0 (0) µm | 76 (141) µm | 0 (0) µm |
| Rules R1 (≤ 25 µm) and R2 (0.3 mm ratio ≤ 1.02) | – | R2 fails | pass | both fail | pass |

Ratios are ink error with the controller / ink error of the device-off pen in the same case (SIM). Rule (written
before the runs, `sim2j/tuning.py`): among the variants that pass R1 and R2, the lowest mean ratio at 1–2 mm. **G4**
(0.72) beat GLG (0.78). Letters read at 8 Hz, 2 mm: 67 % device off, 94 % with G4 (SIM).

- **ai2's gated listening does not hold in sim2 as built.** Its fallback (the Rev H tracker as built) fails the
  false-correction rule on v2 writing, and its 0.3 mm result is worse than the device-off pen. With the guarded
  fallback it passes, but it is worse than G4 at 1 mm.
- **The unfiltered listening output cannot be followed by the C1S nose.** At lag 0 the listening prediction carries
  15–200 Hz content (p99 command speed 0.33 m/s at 10 Hz, 1 mm; SIM). The nose then missed its command by 890 µm rms and
  the ink moved 1.6× more than with the device off (tuning writer 100). With the Rev H tracker's 64 Hz output filter
  (its delay added to the prediction horizon) it helps; the table uses that version. ai2's HW1 nose model did not show
  this.
- **ai2's causal TCN (DEC-043 shadow candidate)** was run on the pen's own sensor record and replayed as the nose
  command (`sim2j/learned_replay.py`; valid here because the nose's action leaves the handle's motion unchanged within
  1 %). Without retraining, on tuning writer 100: 0.66 at 10 Hz 1 mm and 0.73 at 8 Hz 1 mm, but 1.56 at 0.3 mm and
  184 µm false correction on tremor-free writing (HW1: 19.3 µm). It does not transfer. Test results in §6.1.
- **Delayed ink** was not re-run: ai2 found it not worth its cost (DEC-042/043 context) and the lead asked for at most
  25 ms or none.

### 4.2 The other controllers

- **Coordinated nose + wheel (ET).** The heel wheel in its tremor mode: it steers to follow the pen's low-passed
  direction of travel and brakes along it (study D's gains); the nose cancels what the tracker still sees.
- **End-cap.** Phasor feed-forward on the tracker's estimate through the end-cap's linearised plant (internal model),
  gain 0.75 (study K's rule).
- **Guidance (dysgraphia tracing, PD loops).** The nose pulls the ink toward the template (capture 2 mm, drop after
  2.5 mm for 60 ms, HW1's law); the wheel steers along the template (Stanley law, study D's gains); both together.
- **Lead-through (dyslexia).** A relaxed writer (the arm's aim follows the hand in 0.25 s while the pen is down: the
  drive study's model); the driven wheel pushes along the target letters (0.167 N + speed loop to 20 mm/s); the nose adds
  the detail.
- **Autowrite.** nose2's planner and firmware (plan inside 5.5 mm of reach, 1.25× the line speed, pen lift 0.5 mm with
  8 ms switching); the hand sweeps along the line.
- **Supervisor.** Wheel force cap min(0.5 N, 0.603 N, 0.8 μ̂ N), slew 20 N/s, yield after 4 mm for 0.3 s, slip detection.

### 4.3 Model fixes made during this study (all in `sim2j/`)

- IMU lever arm: the firmware removes α × r with the IMU's full position (56.25 mm along, 8.42 mm across the axis).
- Detector input: ball-on-paper samples only (see 4.1).
- Stroke matching: a touchdown starts the template stroke whose start is nearest (sim2 starts with the ball on the
  paper and bounces at touchdown, so counting touchdowns skipped strokes and the lead-through followed the wrong stroke).
- False correction and device share are measured against the device-off run with the same seed (the Hall noise enters
  the physics; stick-slip amplifies any difference).

## 5. Verification against round 1 (SIM against SIM; `results/sim2j/verify.json`)

The same tasks, writers (v1, as round 1) and seed (200) in sim2 and in the round-1 models. HW1 is 2-D: the nose moves
the ink in the page plane, with no tilt, no refill spring geometry, no rotation in the grip and a simpler contact.
sim2 is 3-D with the H1 contact law and the pen's mass properties.

**Autowrite** ("return library books by friday" at 2.5 mm, test writers 0–5):

| | nose2 in HW1 (Rev J, results/nose2) | sim2, round-1 C1S pen (study N, no heel drive) | sim2, the lead's Rev J pen |
|---|---|---|---|
| No tremor: ink error | 29 µm | 41 µm | 46 µm |
| No tremor: letters / words read | 99 % / 100 % | 98 % / 100 % | 98 % / 100 % |
| 1 mm at 8 Hz: ink error | 36 µm | 48 µm | 54 µm |
| 1 mm at 8 Hz: letters / words read | 99 % / 100 % | 97 % / 93 % | 97 % / 97 % |
| Nose coil power | 0.09–0.17 W | 1.33 W | 2.13 W |

- Agreement: the order of the ink error (tens of µm) and near-ceiling reading hold in both simulators.
- Differences: sim2's ink error is 1.4–1.6× HW1's. The likely reasons are the ball's stick-slip on the paper and the
  refill's slide and front stop, which HW1 does not have. The coil power is 8–24× HW1's because sim2 includes the
  refill spring's side load at the ball (§8), which HW1 does not model.

**Dysgraphia tracing** (the drive study's task a, v1 learners; HW1-D: 48 cases, sim2: 6 writers):

| | HW1-D: target error | letters / words read | sim2: target error | letters / words read |
|---|---|---|---|---|
| Nothing on | 599 µm | 87 % / 76 % | 563 µm | 94 % / 90 % |
| Wheel steers along the template | 432 µm | 83 % / 69 % | 392 µm | 76 % / 57 % |
| Wheel + nose guidance | 87 µm | 77 % / 58 % | 228 µm | 66 % / 52 % |

- Agreement: the same ranking, and in both the guidance pulls the ink toward the template while fewer letters are read
  (the template letters are the copybook's, not the learner's own: the recogniser was built on the learner's writing).
- Differences: the nose's fine correction removes less in sim2 (228 against 87 µm). In sim2 the nose also fights the
  ball's stick-slip and the static ball load. Area-coverage agrees (0.86 against 0.87).

## 6. Outcomes per condition (test writers 0–5, seeds 200–203; SIM)

### 6.1 Essential tremor (pending)

### 6.2 Severe tremor: writing through it or letting the pen write (pending)

### 6.3 PD "write big" loops (pending)

### 6.4 Dysgraphia tracing (pending)

### 6.5 Dyslexia: lead-through and autowrite of a known text (pending)

### 6.6 The other hand model and the domain randomisation (pending)

## 7. RL in the physics simulator (`sim2j/rl.py`; ai2's EXP-L05 in closed loop)

- **Environment** (Gymnasium on sim2, 50 µs physics, the firmware and online sensors exactly as in the test). An episode:
  the pen rests on the paper for 3 s with the chosen tracker running (the policy's action held at 0), then writes 5 s
  of a training writer's sentence (writers 1000–1399 only) while the policy acts at 250 Hz. One episode in three is
  tremor-free. Three episodes share a plant draw and one tremor-free, nose-held reference run.
- **Domain randomisation.** sim2's 25 factors (grip, hand, tremor 4–12 Hz and 0.1–2 mm, friction, sensors, tolerances,
  posture; `sim2/env.py`) mapped onto Rev J, plus the lead's Rev J factors: refill spring 0.12–0.18 N, Km scale 0.7–1.0,
  magnetic negative stiffness 0–0.00165 N·m/rad, tyre friction, wheel preload (`results/revJ/sim_params.json`).
- **Observation** (19 values, the pen's own signals only): the tracker's estimate and its ungated oscillator, frequency,
  authority and amplitude; the detector's gate, log peak ratio and line frequency; page-sensor velocity (raw and 3 Hz);
  ball contact; page-sensor validity; the previous action.
- **Action** (3 values in [−1, 1], a residual on the model-based tracker): a gain (1 + a₀) on the gated estimate, a
  weight max(0, a₁) on the ungated oscillator (an arbiter that can act before the gate opens), and a quarter-period
  phase term 0.5 a₂. a = 0 is the model-based controller.
- **Reward.** −(|ink − reference ink| / 0.3 mm)² while the ball is on the paper, − 0.005 |a|². In tremor-free episodes
  this is the false correction itself: the closed-loop false-correction constraint of EXP-L05, as a penalty in training
  and as a hard rule in selection.
- **Training.** Stable-Baselines3 PPO, MLP 64-64 tanh, 600 000 steps, one process (pending: compute).
- **Selection** (rule frozen in `results/sim2j/rules.json` before any test run): the last checkpoints on tuning writers
  100–103, seeds 300–303; pass S1 (false correction ≤ 25 µm mean, every case ≤ 50 µm) and S2 (no worse than the
  model-based tracker at 0.3 mm); among those, the lowest ink error at 1–2 mm; otherwise RL is not adopted.
- **Results** (pending).

## 8. Power: the static ball load (CALC and SIM)

- The refill spring (0.15 N, along the nose) presses the ball on the paper. At tilt θ the paper pushes back with a side
  component F_c·cot θ at the ball: 0.126 N at 50° (CALC).
- The C1S gimbal is soft (0.0028 N·m/rad), so the coils hold it: 9.6 mN·m at 50°. With Km 0.656 N/√W on the 11.5 mm
  magnet arm this costs 1.62 W while the ball is on the paper (CALC). sim2 applies it as a contact-gated bias current
  (sim2's H1 convention).
- Rev H's longer arm needed about 0.13 W for the same load (CALC). The lead's budget has 0.06 W for "writing without
  tremor" (`results/revJ/budgets.json`): the load is missing there.
- sim2, tremor-free writing, writer 0 (4 s rest + 7.5 s of writing): nose copper loss 2.25 W mean, 2.68 W while the ball
  is on the paper, 1.20 W while lifted; coil current 1.0 A rms in contact; coil temperature 25 → 61.5 °C in 11.5 s (SIM).
  The static load alone needs 0.81 A; the rest is ball friction and the servo's work against the handle's motion.
- **Heat (CALC on the SIM power).** With the coil's 100 K/W and 0.5 J/K (ASSUMPTION, as Rev H), 2.68 W would settle
  268 K above ambient. The coil would pass 120 °C after about 22 s of continuous writing. The lead's thermal check
  (16.8 K at 1 mm tremor, DEC-044) did not include this load.
- **Battery.** At 2.3 W total the 2.22 Wh cell lasts about 1 h (CALC), against 5.3–11 h in the lead's budget.
- (pending: sensitivity to the spring force, Km and tilt from `results/sim2j/power.json`)

## 9. Checks (pending)

## 10. Proposed decisions, requirements and experiments

Proposals only; the lead decides. Identifiers are the next free ones in the ledgers.

**Proposed decisions**

- **DEC-045 (proposed): carry the ball's static side load passively, or re-size the C1S actuator for it.** Until then the
  Rev J nose cannot write for more than about 20–30 s without passing its coil limit (CALC on SIM). Options, in order of
  expected power: (a) a bias element that loads the nose against F_c·cot θ only while the refill is extended (a spring
  or magnet acting through the refill slide, so it vanishes when the ball lifts); (b) a longer actuator arm or a higher
  Km (Rev H's 34 mm arm needs about 0.13 W, CALC); (c) a lower refill spring force (power ∝ F_c², §8), limited by ink
  laydown (EXP-Q02). Re-run nose2's optimiser with the static load in its duty (not done here).
- **DEC-046 (proposed): the sim2 default tremor estimator for Rev J is the guarded tracker G4** (Rev H AKF run tick by
  tick, runaway guard, ai2's detector with a stricter threshold, ball-on-paper input; `results/sim2j/rules.json`). It
  refines DEC-042 for sim2: ai2's gated listening tracker as built failed the false-correction rule on v2 writing in
  sim2 (its Rev H fallback), and with the guarded fallback it was worse than G4 at 1 mm (tuning writers). The gated
  listening estimate stays a candidate (it did best at 2 mm); the TCN stays in shadow mode until retrained on sim2 and
  real recordings. (Test-set confirmation in §6.1.)
- (pending: the wheel in ET, autowrite in severe tremor, RL)

**Proposed requirements**

- **REQ-RVJ-N09:** With the refill spring at its nominal force and the ball on the paper at 35–75° tilt, the nose's
  steady coil heat shall be ≤ 0.1 W (ASSUMPTION target; now 1.6 W at 50°, CALC).
- **REQ-RVJ-C01:** The nose command shall be band-limited to what the nose servo follows (the Rev H tracker's 64 Hz
  second-order output filter or equivalent, with its delay inside the prediction horizon).
- **REQ-RVJ-C02:** Every controller, the heel wheel's modes included, shall move tremor-free writing by ≤ 25 µm rms
  (the project rule), checked in sim2 against the device-off pen with the same noise.
- **REQ-RVJ-C03:** The tremor-line detector shall not open on the tremor-free writing of the tuning writers of every
  writer model in use (v1 and v2), with its input restricted to page samples taken while the ball is on the paper.

**Proposed experiments** (equipment and data missing here; executable files in `sim2j/`)

- **EXP-J10 (nose static load):** N-rig with the C1S nose and a 0.15 N refill spring; ball on paper at 35°, 50°, 75°;
  measure coil current and coil temperature for 60 s; compare with 0.81 A and 1.62 W at 50° (CALC). Pass: within 20 %.
  Dependency: the C1S nose prototype (study N), a current probe, a thermocouple on the coil.
- **EXP-V07 (small handwriting kinematics):** 12 healthy adults write "return library books by friday" at their own
  size on a tablet (≥ 200 Hz); compute the 8–12 Hz share of velocity energy, speed and stroke times with
  `sim2j/writers.kinematics`; refit the v2 writers. Dependency: a pen tablet (e.g., Wacom-class, 200 Hz), consent.
- **EXP-J11 (wheel on writing):** healthy writers write with the heel wheel retracted, free, and in its tremor mode;
  measure letter distortion against their own writing and how it changes over 10 minutes (adaptation). Dependency: a
  Rev J heel-drive prototype (study D) and the page sensor log.
- **EXP-L05 (ai2's, closed-loop RL in sim2):** this study's RL environment (`sim2j/rl.py`) runs it; §7 gives the first
  result.

## 11. Open issues

- The v2 writers' velocity spectrum is 6–8× the literature's 8–12 Hz share (§3); results on false detection are
  therefore conservative, and the ranking of estimators may change with realistic small writing (EXP-V07).
- The writer does not relearn the pen with the heel wheel or the end-cap engaged (the adaptation was done with both
  off); the wheel's effect on tremor-free writing (§6.1) may shrink with practice (EXP-J11).
- The TCN was not retrained on sim2 streams; the domain shift (HW1 → sim2, Rev H → Rev J IMU position) is the likely
  reason it fails the false-correction rule here.
- The nose's static load (§8) is modelled as a contact-gated bias current (sim2's H1 convention); a passive bias is not
  modelled.
- The heel motors' magnetic detent and the pen's roll in the hand (the lead's added DR factors) are not modelled.
- Delayed ink was not re-run in sim2 (ai2: not worth its cost).
- sim2 results rank concepts only (COU-1) until EXP-V01/V02/V04 and EXP-V05.

## 12. Files and reproduction (pending)
