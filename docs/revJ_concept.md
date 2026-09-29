# Rev J: a pen that acts at the tip, the heel and the tail

**Status: proposed design, studied in calculation and simulation only (round 1 complete; round 2 integration running).** Nothing has been built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation on synthetic writers and synthetic tremor;
- **CALC**: a calculation;
- **LIT**: published literature, with its ledger id in `docs/evidence.csv`;
- **MFR**: a manufacturer statement, with its ledger id;
- **ASSUMPTION**: an input nobody has measured.

Plan: [`revJ_plan.md`](revJ_plan.md). Decisions: DEC-036 … DEC-043 in [`decisions.md`](decisions.md). Detailed reports: [`nose_v2.md`](nose_v2.md) (tip), [`grounded_drive.md`](grounded_drive.md) (heel), [`inertial_endcap.md`](inertial_endcap.md) (tail), [`ai_control_v2.md`](ai_control_v2.md) (algorithms and AI), [`sim_v2.md`](sim_v2.md) (the physics simulator).

## 1. The answer in plain words

**You asked for a pen with far more effect: one that moves the whole pen, uses inertia, and can even write for you while you hold it.** Rev J acts at three points along the pen, each doing what its physics allows.

| Where | What | What it can do (simulation or calculation) |
|---|---|---|
| **Tip** | A stronger moving nose: the ink tip moves ±6 mm (Rev H: ±2.75 mm guaranteed) | Cancels tremor up to 2 mm; draws whole letters of 2.5 mm by itself while you sweep the pen along the line ("autowrite", a mode you turn on) |
| **Heel** | A 2 mm wheel under the front ring that grips the paper | Uses the paper as ground: 0.3–0.6 N on the hand. By default it only steers (it keeps your hand on the letter's path and cannot move the pen by itself); in a mode you turn on, it leads a relaxed hand |
| **Tail** | A moving tungsten weight in a detachable end-cap | Adds 8–20 % more tremor reduction on top of the nose; gives short cues in pauses. It cannot steer letters |

**Why the paper, not inertia, gives the strong push (CALC).** A pen held in the hand can push only against a mass inside it, against the hand itself, or against the paper.
- A moving mass gives F = m (2πf)² X. At handwriting frequencies (below about 5 Hz, LIT CON-24) that is tiny: the best 45 g end-cap moves the ink at most 0.21 mm, a gyroscope at most 1.06 mm, against the 2 mm needed (SIM, `inertial_endcap.md`).
- The paper is always under the pen while you write, with about 1 N of writing force (LIT CON-01). A rolling element that grips it can push with friction × load: about 0.3–0.6 N (friction ASSUMPTION, to measure in EXP-D01). That is as strong as the desk guidance board, from inside the pen, and a relaxed hand moves about 1.7 mm under 0.5 N (CALC).
- So Rev J uses the paper for force, the nose for speed and precision, and inertia for damping and cues.

**The pen never takes over without your say.** Steadying and steer-only guidance cannot start a stroke. Autowrite and lead-through are modes you turn on; they follow your sweep, wait when you slow, and a writer who resists always wins (DEC-037, DEC-039).

## 2. How much better (SIM on synthetic writers; nothing measured)

| Condition | Help | Result | Source |
|---|---|---|---|
| Essential tremor, 1–2 mm, 6–10 Hz | Nose + **gated tracker** (new default) | Ink error 830 → 430 µm (ordinary pen → Rev J); Rev H's tracker 627 µm. Words read 31 % → 74 % (Rev H 49 %). Clean writing moved 26 µm, as before | `ai_control_v2.md` |
| Tremor at 6 Hz, 1–2 mm (where Rev H did nothing) | Gated tracker | 822 → 540 µm | `ai_control_v2.md` |
| Same, a learned estimator (candidate, shadow mode) | Causal TCN | 278 µm and 81 % of words; waits for real recordings | `ai_control_v2.md` |
| Tremor, on top of the nose | Tungsten end-cap | A further 8 / 18 / 20 % at grip splits 0.3 / 0.5 / 0.7 (8–12 Hz, 1–2 mm); the same mass fixed gives 17 / 12 / 4 %, better at split 0.3, but it worsens 29–42 % of the hard cases (the moving slug 4–12 %) | `inertial_endcap.md` |
| Writing for you (known text) | Autowrite with the ±6 mm nose | 99.2 % of letters and 100 % of words read with up to 1 mm of tremor; 98 % of words at 2 mm; 3.7 letters/s | `nose_v2.md` |
| Parkinson's "write big" loops | Heel wheel, steer only | Loop height 0.99 of the target (0.78 with nothing; 0.93–0.94 for a resisting hand) | `grounded_drive.md` |
| Tracing and copying (poor handwriting) | Heel wheel + nose | Distance to the target 582 → 76 µm while guided; letters read 79 % | `grounded_drive.md` |
| Leading a relaxed hand through a letter | Heel wheel, driven | In the reversed-letter demo, the 'd' bowl was drawn within 0.3 mm in 93 % of runs (3 % with nothing) | `grounded_drive.md` |
| A letter the writer is set on (e.g. a reversed b) | Any guidance | 0 % turned into another letter: the writer always wins | `grounded_drive.md`, `handwriting_outcomes.md` |
| Severe tremor, notes | The app's clean copy (digital) | 97 % of words readable; the paper keeps the pen's ink | `ai_severe_tremor.md` |

**What the AI does and does not do (SIM, CALC).**
- *Helps:* the tremor-line detector that switches the listening tracker on (above); the learned estimator in shadow mode; the clean copy; spelling help; letter shapes in your own style for autowrite (96 % legible from 1–3 of your letters, on synthetic writers); prediction as word completion in the app.
- *Does not help:* guessing your next letter and steering the tip toward it (0–1 % of the gap closed); letting the ink trail the hand for look-ahead smoothing (−4 % at 25 ms; longer lags lose stroke ends); reinforcement learning driving the nose directly (it read more words but moved clean writing too much). RL is used offline to design how the pen shares control (DEC-042).

## 3. What is inside (proposed design; integration round 2 running)

| Part | What it does | Study |
|---|---|---|
| Moving nose v2 | Refill carrier on a 2-axis flexure gimbal 76.5 mm behind the ball; a 2 × 2 magnet checkerboard on a spherical iron cap faces a spherical coil plate (0.77 mm gap at every tilt); the ball moves 6.6 × as far as the magnets | DEC-036 |
| Pen lift | A drum at the gimbal with a fatigue-rated spiral spring sets the 0.15 N ink force through a tendon; an electro-permanent brake and latch lift the ball 0.5 mm with no holding power (so strokes do not join) | DEC-036, DEC-041 |
| Heel wheel | 2 mm wheel with an O-ring tyre in a slot at the bottom of the skid ring, steered through its contact point, driven through a 2:1 bevel; two Faulhaber 0620 B motors and thin shafts; 0.55 N sprung preload | DEC-037 |
| Page sensor | Optical sensor at the front: required for autowrite (1 kHz), slip detection and the tremor-line detector | DEC-036, DEC-037, DEC-042 |
| Motion sensor, board, battery | As Rev H (IMU LSM6DSV16X, nRF54L15, 14500 cell), with more drivers | revH_concept.md |
| End-cap (detachable) | 30.4 g tungsten slug pushed ±4 mm on two axes by arc coils on 5 Hz flexures, behind the cell; pen length 175 mm | DEC-038 |

**Open integration items (round 2, `revj/`):** the bigger nose and the heel wheel both widen the front (skid contact radius 10 mm for the nose alone; the wheel's pod must sit outside the nose's swing), and the drive motors must move away from the new gimbal; the mass with every module is about 134–136 g against a 120 g target (so the end-cap stays detachable); the battery life per mode must be recomputed with the nose v2 coil loss (0.16–0.18 W at 1 mm of tremor).

## 4. Modes

| Mode | Tip | Heel | Tail | Who moves the pen |
|---|---|---|---|---|
| Steady | Cancels tremor (gated tracker) | Free, or brake along the path | Reaction mass against tremor | You |
| Guide (practice, tracing, big writing) | Partial nudge toward the letter (fading across sessions) | Steer only: keeps you on the path | Off, or cues in pauses | You |
| Lead-through (turn on) | Detail | Driven: leads a relaxed hand along the letter | Off | The pen leads; you can always resist or lift |
| Autowrite (turn on) | Draws the letters of a known text within ±6 mm | Steer only, or leads the sweep | Off | You sweep; the pen writes |
| Capture | Records | – | – | You; the app keeps the ink and a labelled clean copy |

## 5. Can it "write for you"? (the honest answer)

- **Yes, inside the nose's reach, for a known text** (SIM): typed, dictated or copied in the app, written in your own style, while you sweep the pen along the line. Letters are 2.5 mm high by default (3 mm possible); larger letters need more travel than a 24 mm handle can give within its heat limit.
- **At gross scale, the heel wheel can lead a relaxed hand** (SIM: 60 % of words read with the Rev H nose adding detail; the integrated Rev J run is in round 2).
- **Not by inertia, and not against you.** No inertial device can move a letter; a writer who resists always wins; the pen never writes text you did not choose.
- **Prior art to clear:** an actuated-nib pen that scribes predefined characters with a lift (LIT PAT-01), handheld robots and cobots (LIT PAT-27, HAP-60, HAP-62). A freedom-to-operate review is needed before building autowrite with a pen lift.

## 6. Simulation you can trust (and how far)

- **Simulator v2** (`sim_v2.md`, DEC-040): MuJoCo physics of the pen, its moving nose, refill, paper contact and plug-ins (heel wheel, end-cap, gyroscopes natively), with two hand models, several tremor types and the pen's own sensors. It reproduces the earlier hand–pen model on 56 test cases within tolerances fixed in advance, converges in time step, conserves energy, and matches the gyroscopic torque formula (SIM, CALC).
- **What it found:** the synthetic writers write at half adult speed and have about ten times the measured 8–12 Hz velocity content (LIT CON-20, CON-25), which makes tremor separation look harder than it probably is; they must be refitted to recorded writing (EXP-V03).
- **How far to trust it:** until bench identification (EXP-V01, V02, V04) calibrates it and EXP-V05 validates it, its results rank designs (context of use COU-1, following ASME V&V 40); they are not evidence of benefit.

## 7. What to build and test first

1. **Magnetics coupons** (EXP-N01): measure the nose v2 and Rev H force constants. An image-method model gives 0.19 N/√W for Rev H, not 0.47 (DEC-041).
2. **Tyre friction on six papers** (EXP-D01) and the heel bench with its force cap and release (EXP-D04, D07).
3. **Recordings of real writing with tremor** (EXP-H01), then the tremor-line gate and the gated tracker offline (EXP-L01, L02) and the learned estimator (EXP-L04); refit the simulator's writers (EXP-V03).
4. **Grip split** on the Ø24 mm handle with and without the end-cap (EXP-I01, K08): it decides whether the moving slug beats a plain weight.
5. **Spring fatigue and the pen lift** (EXP-N05, N06).
6. **People:** guidance and lead-through (EXP-D08), autowrite (EXP-N09), end-cap acceptance and cues (EXP-K03, K05). Acceptance is the question no simulation answers.

## 8. Evidence levels

| Claim | Level |
|---|---|
| Heel traction 0.3–0.6 N | CALC on ASSUMPTION friction (to measure, EXP-D01) |
| Nose v2 travel, force constant, heat | CALC (magnetics are an upper bound) |
| Tremor, autowrite, guidance and end-cap results | SIM on synthetic writers and tremor, test seeds only |
| Inertia cannot write | CALC and SIM (physical limit) |
| Perception of inking lag, guidance and learning | LIT |
| Anything about real users | Not yet known |
