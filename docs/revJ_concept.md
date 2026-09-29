# Rev J: a pen that acts at the tip, the heel and the tail

**Status: proposed design, studied in calculation and simulation only (round 1 complete; round 2: integrated layout done, whole-pen physics simulation done (`revJ_simulation.md`); round 3: Rev J.1 fixes done; round 4 running: shifting the whole pen against large tremor, real recorded data, spelling AI — `round4_plan.md`).** Nothing has been built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation on synthetic writers and synthetic tremor;
- **CALC**: a calculation;
- **LIT**: published literature, with its ledger id in `docs/evidence.csv`;
- **MFR**: a manufacturer statement, with its ledger id;
- **ASSUMPTION**: an input nobody has measured.

> **Correction, 29 September 2026: the nose design is reopened.** The refill spring presses the ball along the tilted pen, so the paper pushes it sideways. The nose's magnets sit on a short arm and must push about 7 times harder than that sideways force, so the coils spend 1.6 W at a 50° pen angle (4.7 W at 35°) just holding the ball still (CALC; confirmed by the physics simulation and an independent review). They would overheat within about a minute. **The battery and heat figures below are suspended.** A load-balanced nib is being designed (study B). See [`claims_register.md`](claims_register.md) and [`reviews/2026-09-29_review_response.md`](reviews/2026-09-29_review_response.md).

Plan: [`revJ_plan.md`](revJ_plan.md). Decisions: DEC-036 … DEC-049 in [`decisions.md`](decisions.md). Detailed reports: [`nose_v2.md`](nose_v2.md) (tip), [`grounded_drive.md`](grounded_drive.md) (heel), [`inertial_endcap.md`](inertial_endcap.md) (tail), [`ai_control_v2.md`](ai_control_v2.md) (algorithms and AI), [`sim_v2.md`](sim_v2.md) (the physics simulator), [`revJ_simulation.md`](revJ_simulation.md) (the whole Rev J pen in it).

## 1. The answer in plain words

**You asked for a pen with far more effect: one that moves the whole pen, uses inertia, and can even write for you while you hold it.** Rev J acts at three points along the pen, each doing what its physics allows.

| Where | What | What it can do (simulation or calculation) |
|---|---|---|
| **Tip** | A stronger moving nose: the ink tip moves ±6 mm (Rev H: ±2.75 mm guaranteed) | Cancels about a third of a fast (8–12 Hz) tremor of 1–2 mm, so words read go from 69 % to 100 % in the physics simulation; does nothing yet for slow (4 Hz) tremor; draws whole letters of 2.5 mm by itself while you sweep the pen along the line ("autowrite", a mode you turn on), readable up to 3 mm of tremor |
| **Heel** | A 2 mm wheel under the front ring that grips the paper | Uses the paper as ground: 0.3–0.6 N on the hand. **Retracted by default** (DEC-048): switched on during normal writing it changed the letters by 0.4 mm in the physics simulation. Used for "write big" practice, where it kept the last loop at 86 % of the target (66 % without), and for lead-through |
| **Tail** | A moving tungsten weight in a detachable end-cap | Optional. The simpler hand–pen model gave 6–18 % more tremor reduction on top of the nose; the physics simulation gave none. It must beat a plain weight of the same mass (EXP-J16). It cannot steer letters |

**Why the paper, not inertia, gives the strong push (CALC).** A pen held in the hand can push only against a mass inside it, against the hand itself, or against the paper.
- A moving mass gives F = m (2πf)² X. At handwriting frequencies (below about 5 Hz, LIT CON-24) that is tiny: the best 45 g end-cap moves the ink at most 0.21 mm, a gyroscope at most 1.06 mm, against the 2 mm needed (SIM, `inertial_endcap.md`).
- The paper is always under the pen while you write, with about 1 N of writing force (LIT CON-01). A rolling element that grips it can push with friction × load: about 0.3–0.6 N (friction ASSUMPTION, to measure in EXP-D01). That is as strong as the desk guidance board, from inside the pen, and a relaxed hand moves about 1.7 mm under 0.5 N (CALC).
- So Rev J uses the paper for force, the nose for speed and precision, and inertia for damping and cues.

**The pen never takes over without your say.** Steadying and steer-only guidance cannot start a stroke. Autowrite and lead-through are modes you turn on; they follow your sweep, wait when you slow, and a writer who resists always wins (DEC-037, DEC-039).

## 2. How much better (SIM on synthetic writers; nothing measured)

**In the physics simulation of the whole Rev J pen** (`revJ_simulation.md` §1; study sim2j; 6 test writers; **synthetic tremor**: on real recorded tremor the trackers have not helped yet, see below). "Ordinary pen" is the same pen with every device off. Readable words are those the app reads correctly, out of 10.

| Who (tremor at the hand, peak) | What Rev J does | Readable words out of 10: ordinary pen → Rev J | Error left at the tip |
|---|---|---|---|
| Essential tremor, mild (0.3 mm) | Stays out of the way | 10 → 10 | 0.13 → 0.13 mm rms |
| Essential tremor, 1 mm, 8–12 Hz | Cancels the tremor it detects (guarded tracker G4, DEC-047) | 10 → 10 (letters 9.4 → 9.8) | 0.41 → 0.28 mm |
| Essential tremor, 2 mm, 8–12 Hz | As above | 5.4 → 10 | 0.93 → 0.54 mm |
| Slow tremor, 4 Hz, 1–2 mm | Nothing yet: it cannot tell a 4 Hz tremor from the writing itself (with perfect knowledge it would remove 90 %) | 5.4 → 5.4 | 0.69 → 0.69 mm |
| Severe tremor, 3 mm, writing through it | Cancels what it can | 0.4 → 3.8 | 1.47 → 1.15 mm |
| Severe tremor, 3 mm, a text you chose | Writes it (autowrite, DEC-049) | 0.4 → 8.8 | 0.08 mm from the planned letters |
| Parkinson's, five 10 mm practice loops that shrink | The driven heel wheel pushes along the loops | not scored | Last loop 6.6 → 8.6 mm (7.4 mm with a lightly resisting hand) |
| Dysgraphia, copying a sentence | The nose pulls the ink half-way toward the copybook letter | 9.7 → 9.7 | 0.83 → 0.64 mm from the copybook letters |
| Dyslexia, led through the right spelling | The driven heel wheel pushes a relaxed hand | 5.8 → 6.7 (letters distorted, slow) | 0.70 → 0.50 mm from the right letters |
| Anyone, a text you chose, no tremor | Autowrite | – → 10 | 0.04 mm |
| Anyone, no tremor | Should change nothing | – | 0 mm with the nose; 0.41 mm if the heel wheel is on |

Writing time per charge is **suspended** in every row: in this simulation the nose draws about 2.3 W (§3).

**With real recorded tremor** (study R, `real_data.md`; the simpler hand–pen model HW1 with real handwriting of 9 held-out writers, real Parkinson's and essential tremor, and a realistic page sensor): **no tracker built so far makes the writing more readable.** Real tremor at the pen tip was smaller than assumed (severe typically 1.7 mm, not 5–10 mm) and far more irregular. At the severe size, readable words out of 10: ordinary pen 0.5, Rev J gated tracker 0.4, the learned TCN 0.2; with perfect knowledge of the tremor the same nose gives 7.0 (no tremor 6.8). The nose has the reach; estimating real tremor in time is the missing piece (DEC-054, DEC-055). The chosen tracker G4 has not been run on real inputs yet.

**Where the earlier, simpler models disagree** (see `claims_register.md`):
- The gated listening tracker (HW1: ink 830 → 430 µm, words 31 → 74 % at 1–2 mm, 6–10 Hz) moved tremor-free writing by 59 µm in the physics simulation, over the 25 µm rule; the guarded tracker G4 replaces it there (DEC-047). The learned TCN moved it by 150 µm (shadow mode stays).
- The end-cap: 5.6 / 16.8 / 18.3 % more in H1; no gain in the physics simulation (0.67 of the ordinary pen's error with it, 0.65 without).
- Parkinson's loops: in HW1-D steering alone brought the loops to 0.99 of the target; in the physics simulation steering enlarged the early loops but not the last one, and only the driven wheel kept it big.
- Tracing agrees: in both, ink pulled closer to a template is not easier to read (physics simulation: nose and wheel 0.27 mm from the copybook letters, but words read 9.7 → 6.3 of 10).
- Lead-through helped less in the physics simulation (words 5.8 → 6.7 of 10) than the HW1-D demo suggested (the 'd' bowl within 0.3 mm in 93 % of runs). Autowrite of the right spelling reads 10 of 10.
- Not re-run in the physics simulation: the app's clean copy (97 % of words readable at 1–2 mm, HW1) and "a letter the writer is set on is never turned into another" (0 %, HW1-D).

**What the AI does and does not do (SIM, CALC).**
- *Helps:* the guarded tracker (G4) that cancels fast tremor and leaves normal writing alone (above); the learned estimator in shadow mode; the clean copy; spelling help; letter shapes in your own style for autowrite (96 % legible from 1–3 of your letters, on synthetic writers); prediction as word completion in the app.
- *Does not help:* guessing your next letter and steering the tip toward it (0–1 % of the gap closed); letting the ink trail the hand for look-ahead smoothing (−4 % at 25 ms; longer lags lose stroke ends); reinforcement learning driving the nose directly (it read more words but moved clean writing too much). RL is used offline to design how the pen shares control (DEC-042); in the physics simulator its environment runs but it has not been trained yet (about 2.4 CPU hours).

## 3. What is inside (proposed design; Rev J.1)

| Part | What it does | Study |
|---|---|---|
| Moving nose v2 | Refill carrier on a 2-axis flexure gimbal 76.5 mm behind the ball; a 2 × 2 magnet checkerboard on a spherical iron cap faces a spherical coil plate (0.77 mm gap at every tilt); the ball moves 6.6 × as far as the magnets | DEC-036 |
| Pen lift | A drum at the gimbal with a fatigue-rated spiral spring sets the 0.15 N ink force through a tendon; an electro-permanent brake and latch lift the ball 0.5 mm with no holding power (so strokes do not join) | DEC-036, DEC-041 |
| Heel wheel | 2 mm wheel with an O-ring tyre in a slot at the bottom of the skid ring (wheel at 12.0 mm from the axis), steered through its contact point, driven through a 2:1 bevel; two Faulhaber 0620 B motors under the cell and two 80 mm shafts in grooves of the bottom wall; 0.55 N sprung preload; 0.37 N continuous, 0.60 N peak at the tyre | DEC-037, DEC-044 |
| Page sensor | Optical sensor at the front: required for autowrite (1 kHz), slip detection and the tremor-line detector | DEC-036, DEC-037, DEC-042 |
| Motion sensor, board, battery | As Rev H (IMU LSM6DSV16X, nRF54L15, 14500 cell), with more drivers | revH_concept.md |
| End-cap (detachable) | A tungsten slug pushed ±4 mm on two axes by arc coils on 5 Hz flexures; it replaces the rear cap. Rev J.1: 9 mm slug, 29.6 g end-cap, 21 mm long (pen 161.9 mm with it, 143.9 mm without); Rev J: 43.3 g | DEC-038, DEC-044, DEC-045 |

**Integrated layout (round 2, `docs/revJ_design.md`, DEC-044; CALC):** one Ø24 mm pen. The skid ring's contact radius is 11.65 mm and the sleeve front Ø23.3 mm, flush with the ring; the ball sits 9.3 mm ahead of the ring at 50°; the refill slides 26.6 mm. The board lies on top, the cell behind the coil plate, the heel motors under the cell. All 38 fit checks pass.

**Rev J.1 fixes (round 3, `docs/revJ1_design.md`, DEC-045; CALC unless stated).** The first integration found six problems. Rev J.1 fixes five and states the limit of the sixth:

| Problem found in the integrated layout | Rev J.1 fix | Result |
|---|---|---|
| The nose magnets pull the gimbal with 12–22 N; its 50 µm strips buckle at about 16 N | 75 µm strips, still in compression, with shock stops (strips in tension fail fatigue) | Buckling 55 N; fatigue safety factor 2.0 |
| Battery 6.1–7.3 h at 1 mm tremor (target 8 h) | Electronics counted from datasheets; a low-power page sensor left on (the tremor detector needs it); heel drivers asleep in steady mode | 8.5–9.7 h at 1 mm tremor; lead-through 7.5–8.8 h; autowrite 6.5–7.4 h |
| Skin at the web 45.7 °C in a 30 °C room | 0.1 mm graphite sheet in the shell wall (0.2 g) | 35.9 °C (limit 43 °C) |
| 129.2 g with the end-cap (target 120 g) | Lighter end-cap (9 mm tungsten slug, 29.6 g) and a thinner back iron | 112.7 g; the end-cap still adds 5.6 / 16.8 / 18.3 % in H1 (SIM; no gain in the physics simulation) |
| Ink hidden near the ball at 50–75° | A clear 15 mm window in the front sleeve | Ink seen within 1 mm in 47 % of tilt × eye cases (was 22 %; eye range assumed) |
| The nose magnets drag on the heel motors (detent) | Motors 10 mm further back | 0.66 × the motor's own friction (free-space bound) |

| Budget (CALC) | Base pen | With the end-cap |
|---|---|---|
| Length | 143.9 mm | 161.9 mm |
| Mass (target ≤ 120 g) | 84.3 g | 112.7 g |
| Battery, steady with 1 mm of tremor (target ≥ 8 h) | 8.5–9.7 h | 6.4–8.6 h |
| Skin at the web, 1 mm tremor, 30 °C room (limit 43 °C) | 35.9 °C | as base |

**The big caveat, now confirmed.** Every battery and heat number above rests on the nose-coil power of study N's model, which left out the static side load. In the physics simulation the nose drew 2.25 W in tremor-free writing: about 1.1 W to hold the ball against the static side load, 0.74 W for its servo reacting to an unfiltered position sensor (mostly a model artefact), and 0.4 W for friction and holding (SIM, `revJ_simulation.md` §8.1). At that power the 2.22 Wh cell lasts about an hour and the coil passes its 120 °C limit after about 22 s of continuous writing (CALC). DEC-046: the static load must be carried mechanically (≤ 0.1 W); study B is designing the balanced nib.

## 4. Modes

| Mode | Tip | Heel | Tail | Who moves the pen |
|---|---|---|---|---|
| Steady | Cancels fast tremor (guarded tracker G4, DEC-047) | Retracted (DEC-048) | Optional reaction mass (no gain shown in the physics simulation) | You |
| Guide (practice, tracing) | Half-way nudge toward the letter (fading across sessions) | Retracted | Off, or cues in pauses | You |
| Write big (Parkinson's practice) | Off | Driven along the loops | Off | You, with the wheel pushing |
| Lead-through (turn on) | Detail | Driven: leads a relaxed hand along the letter | Off | The pen leads; you can always resist or lift |
| Autowrite (turn on) | Draws the letters of a text you chose within ±6 mm; the severe-tremor mode up to 3 mm (DEC-049) | Retracted, or leads the sweep | Off | You sweep; the pen writes |
| Capture | Records | – | – | You; the app keeps the ink and a labelled clean copy |

## 5. Can it "write for you"? (the honest answer)

- **Yes, inside the nose's reach, for a known text** (SIM): typed, dictated or copied in the app, written in your own style, while you sweep the pen along the line. Letters are 2.5 mm high by default (3 mm possible); larger letters need more travel than a 24 mm handle can give within its heat limit.
- **At gross scale, the heel wheel can lead a relaxed hand, but poorly** (SIM: in the physics simulation of Rev J, words read rose only from 5.8 to 6.7 of 10, with distorted letters at 8 mm/s; autowrite of the same text reads 10 of 10).
- **Not by inertia, and not against you.** No inertial device can move a letter; a writer who resists always wins; the pen never writes text you did not choose.
- **Prior art to clear:** an actuated-nib pen that scribes predefined characters with a lift (LIT PAT-01), handheld robots and cobots (LIT PAT-27, HAP-60, HAP-62). A freedom-to-operate review is needed before building autowrite with a pen lift.

## 6. Simulation you can trust (and how far)

- **Simulator v2** (`sim_v2.md`, DEC-040): MuJoCo physics of the pen, its moving nose, refill, paper contact and plug-ins (heel wheel, end-cap, gyroscopes natively), with two hand models, several tremor types and the pen's own sensors. Against tolerances fixed in advance, on the earlier hand–pen model's 56 test cases, it reproduces the uncorrected ink error within 3.1 % in every case, the perfect-knowledge ratio within ±0.03 in 52 cases (worst 0.040) and the tracker's ratio within ±0.05 in 50 cases; the misses come from the Rev H tracker's frequency lock, which sits on a knife edge, not from the plant. It converges in time step, conserves energy, and matches the gyroscopic torque formula (SIM, CALC).
- **What it found:** the synthetic writers wrote at half adult speed and had about ten times the measured 8–12 Hz velocity content (LIT CON-20, CON-25). The refitted v2 writers now match adult speed (27–31 mm/s) and the speed–curvature law, but still have 6–8 times the 8–12 Hz content; their letters look like crude print. Recorded writing is being brought in (study R, EXP-V03, EXP-V07).
- **The whole Rev J pen in it** (`revJ_simulation.md`): the results in §2 above, the power problem in §3, and a page-sensor check: with a DeltaPen-like error (LIT OPT-02) the tremor tracker was unaffected, autowrite stayed readable if the errors do not add up, and letters drifted 1.5–3 mm apart if they do.
- **How far to trust it:** until bench identification (EXP-V01, V02, V04) calibrates it and EXP-V05 validates it, its results rank designs (context of use COU-1, following ASME V&V 40); they are not evidence of benefit.

## 7. What to build and test first

1. **The nib's static side load and holding power** (EXP-J17) at 35°, 50° and 75°, first on the C1S nose to confirm the model, then on the balanced nib (study B, DEC-046). And the **magnetics coupons** (EXP-N01): the nose v2 and Rev H force constants. An image-method model gives 0.19 N/√W for Rev H, not 0.47 (DEC-041).
2. **Page-sensor drift on paper** (EXP-J10): autowrite and guidance depend on it (REQ-RVJ-C05).
3. **Tyre friction on six papers** (EXP-D01) and the heel bench with its force cap and release (EXP-D04, D07); healthy writers with the wheel retracted, free and on (EXP-J18).
4. **Recordings of real writing with tremor** (EXP-H01), then the tremor-line gate and the gated tracker offline (EXP-L01, L02) and the learned estimator (EXP-L04); refit the simulator's writers (EXP-V03).
5. **Grip split** on the Ø24 mm handle with and without the end-cap (EXP-I01, K08): it decides whether the moving slug beats a plain weight.
6. **Spring fatigue and the pen lift** (EXP-N05, N06).
7. **People:** guidance and lead-through (EXP-D08), autowrite (EXP-N09), end-cap acceptance and cues (EXP-K03, K05). Acceptance is the question no simulation answers.

## 8. Evidence levels

| Claim | Level |
|---|---|
| Heel traction 0.3–0.6 N | CALC on ASSUMPTION friction (to measure, EXP-D01) |
| Nose v2 travel, force constant, heat | CALC (magnetics are an upper bound) |
| Tremor, autowrite, guidance and end-cap results | SIM on synthetic writers and tremor, test seeds only |
| Inertia cannot write | CALC and SIM (physical limit) |
| Perception of inking lag, guidance and learning | LIT |
| Anything about real users | Not yet known |
