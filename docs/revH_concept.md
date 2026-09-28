# Rev H: the bigger-grip active pen

**Status: proposed design (DEC-029), studied in simulation only.** Nothing has been built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation on synthetic writing and tremor;
- **CALC**: a calculation;
- **LIT**: published literature, with its ledger id in `docs/evidence.csv`;
- **MFR**: a manufacturer statement, with its ledger id;
- **ASSUMPTION**: an input nobody has measured.

Detailed reports:
- [`opt_inertial.md`](opt_inertial.md): the mechanism, its optimisation, the inertial add-on, CAD and parts;
- [`handwriting_outcomes.md`](handwriting_outcomes.md): how a pen is held, and before/after writing for each condition;
- [`guidance_board.md`](guidance_board.md): the optional desk board that guides whole letters;
- [`optimisation.md`](optimisation.md): where every simulation is.

The 3-D explainer page is built by `python3 viewer/explainer/build.py`.

## 1. The answer in plain words

**What changed, and why.**
- You chose a bigger grip. The pen is now about as thick as a marker: 22 mm across, 170 mm long, about 75 g (CALC). The slim pencil moved only its ink refill, by ±0.3 mm. That covers small tremor only and cannot change a letter's shape.
- In Rev H the whole front of the pen, the **nose** holding the ink refill, tilts inside the handle. The ink tip moves up to **3 mm** in any direction: ten times more.
- Your fingers hold a soft **sleeve that does not move**. A ring at the front of the sleeve rests on the paper and takes your writing pressure. So the moving tip only has to steer, not push. This is why it needs little power: about 0.08 W in total, so the battery lasts about 27 h of continuous writing (CALC).

**How it steadies writing.**
- A motion sensor (IMU) feels the hand's shake about 2000 times a second.
- A tracker, a Kalman filter tuned by AI methods, separates the shake from your intended strokes.
- Two small electromagnets tilt the nose the opposite way to the shake, so the ink stays near the letters you meant. This is the principle of handheld tremor spoons: Liftware reduced spoon tremor by about 73 % in essential tremor (LIT ACT-16).

**What a pen can and cannot do physically.**
- A pen cannot push your hand around: it has nothing to push against, and your hand and arm are hundreds of times heavier and stronger.
- What it can do:
  - move its own tip a few millimetres against your hand;
  - give you cues (a gentle buzz);
  - add small inertial forces.
- A board on the desk can do more. It is grounded, so a magnet under the paper can pull the pen along a letter with real force (optional, §7).
- The pen never writes for you.

**What it does for each problem** (proposed; evidence levels in §8):

| Problem | Main help | How |
|---|---|---|
| Essential tremor (shaky writing) | The stabiliser | The nose moves against the shake; the tracker keeps your real strokes |
| Parkinson's (small, cramped writing) | Cues and practice | A buzz when letters shrink; practice with lines and guidance. The stabiliser helps only if there is tremor while writing: Parkinson's tremor is mostly at rest (LIT PDT-06) |
| Poor handwriting (dysgraphia) | Guided practice | The nose nudges letter shapes within 3 mm; the board guides whole letters. The evidence shows fluency improves more than shape (LIT HAP-10…14) |
| Dyslexia (spelling) | The app's AI | It recognises each word, flags a misspelling with a gentle buzz, then shows and reads the right spelling; it keeps a corrected copy of your notes. Guided practice of letter shapes when the word is known |

**How much better (SIM, pencil-and-hand model H1, test seeds; `results/opt/inertial_opt.json`).**
- With perfect knowledge of the shake, the mechanism leaves **9–24 %** of the tremor in the ink, for tremor up to 2 mm (a 76–91 % cut).
- With today's tracker on synthetic writing, it leaves **60–80 %** at 8–12 Hz and 1–2 mm (a 20–40 % cut).
- The gap between the two is the hard part: telling shake from writing, not the mechanism. It will only be settled on real writing (EXP-E01).
- The before/after writing samples for each condition are in [`handwriting_outcomes.md`](handwriting_outcomes.md) and on the explainer page.

## 2. How you hold a pen, and what the pen changes

- **The grip.** Most people hold a pen in a tripod grip: the thumb, index and middle finger pads hold it 20–40 mm from the tip, and the shaft rests on the web between thumb and index.
- **Who makes which motion.**
  - The fingers make the small up-down strokes and loops of letters.
  - The wrist makes strokes and the slant.
  - The forearm and shoulder carry the hand along the line.
- **Speed of writing.** Handwriting strokes last about 0.1–0.15 s each. Their energy lies mostly below 5 Hz and fades by about 10 Hz (LIT CON-24).
- **Where the shake comes from.**
  - Essential tremor is 4–12 Hz, mostly from the wrist and forearm.
  - Parkinson's tremor is mostly at rest (4–6 Hz). The main writing problem in Parkinson's is that letters are small and shrink as you go (LIT PDT-05, PDT-06).
- **What Rev H changes.**
  - The shake moves your fingers, so the sleeve and the whole pen move with them.
  - Inside, the nose moves the tip the other way by up to 3 mm, so the ink stays nearer the stroke you meant.
  - Because writing and tremor overlap in frequency (3–7 Hz strokes, 4–12 Hz tremor), the tracker must decide what is shake. That is why it is tuned on writing, and why it holds back when unsure.

## 3. What is inside

From `results/revH/layout.json` (PROPOSED DESIGN; dimensions ASSUMPTION, masses CALC; CAD `mechanics/cad/revH_pen.py`):

| Part | What it does | Part or process | Ledger |
|---|---|---|---|
| Ink refill (D1 mini) and ball tip | Standard replaceable refill. It slides along its axis on a soft constant-force spring (about 0.15 N) so the ball stays on the paper while the nose tilts | ISO 12757-2 D1 refill; music-wire spring | DEC-004 |
| Moving nose | Thin titanium tube holding the refill; it tilts on the pivot so the tip moves up to about 3 mm against the handle | Ti-6Al-4V tube 7/6 mm, PEEK nozzle | AMF-21, AMF-24 |
| Flexure pivot (2-axis) | Laser-cut spring-steel cross flexures at 45 mm from the tip: tilt in two directions with no friction or backlash; stiff along the pen | 301 full-hard or 17-7PH, 0.1 mm | AMF-20 |
| Rear arm and magnets | Carry four NdFeB magnets behind the pivot; the tip moves the opposite way (lever 1.32) | aluminium arm, soft-iron hub, NdFeB N45 3 × 6.5 × 2.8 mm | AMF-28 |
| Flat voice coils | Four fixed coils with a soft-iron return ring: current pushes the magnets sideways, tilting the nose (up to 0.84 N peak at the tip, 0.21 N continuous) | self-bonding 0.1 mm magnet wire | AMF-29, AMF-30 |
| Position sensing | A small magnet on the arm read by a 3-D Hall sensor about 10 000 times a second | TMAG5273 or 2 × DRV5055; 1 mm magnet | OPT-45/46, AMF-72 |
| Skid ring | A C-shaped heel on the fixed sleeve that rests on the paper and carries your writing force; open at the front so you see the ink | PTFE-coated POM | – |
| Front sleeve | Where your fingers rest; it does not move | PEEK core, TPE overmould | AMF-24 |
| Motion sensor (IMU) | Measures the shake about 2000 times a second for the tracker | LSM6DSV16X | OPT-37 |
| Control board | Microcontroller with Bluetooth, two coil drivers with current sensing, charger; runs the tracker and the servo | nRF54L15 class, 2 × DRV8214 | AMF-44, AMF-37 |
| Battery | 750 mAh Li-ion, AA-sized | EEMB LIR14500 | AMF-80 |
| Vibration motor | Gentle cues: write bigger, slow down, check a word | coin LRA 8 mm | AMF-45 |
| Paper sensor (recommended) | Sees the paper beside the tip: where the tip is on the page, for guidance and for saving your writing; also helps the tracker | optical-flow class, to select | – |
| Inertial module (optional) | A moving weight or gyroscope pair in the rear that pushes the pen body against the shake (§6) | see `opt_inertial.md` | – |

## 4. How the tip moves: two ways were compared

| | A: the nose carries the writing force (no ring) | **B: a ring on the fixed sleeve carries it (chosen)** |
|---|---|---|
| What moves | The rigid nose with the refill | The nose with the refill, which slides on a soft spring |
| Correction with perfect knowledge (SIM) | leaves 15–79 % | **leaves 9–24 %** |
| Coil power (SIM, CALC) | 1.9 W, or 0.41 W with a bias spring | **about 4 mW of coil power; about 0.08 W in total** |
| Side effect | Tilting a rigid nose pushes the tip into and out of the paper: the writing force swings by ±0.38 N (SIM) | The refill slides along its axis, so the writing force stays set by its spring |
| Feel | Like a normal pen | A ring touches the paper (like some technical pens); feel and visibility must be tested (ASSUMPTION) |

Source: `results/revH/tip_params.json`, `results/opt/inertial_opt.json`.

## 5. Control and modes

- **Sense.** IMU at about 1.9 kHz (FIFO); nose position at 10 kHz (Hall); pen-down from the refill slide; the paper sensor if fitted.
- **Decide.** The accelerometer Kalman tracker (DEC-025, settings tuned by adjoint gradients, DEC-028). The Rev H setting opens its gates for the larger travel. It commands only what it is confident is shake.
- **Act.** A position servo at about 80 Hz bandwidth moves the nose (ASSUMPTION; `tip_params.json`).
- **Modes.**
  - *Steady*: cancel shake.
  - *Write bigger*: cue when letter size falls; the practice programme follows the Parkinson's cueing evidence (lines ≥ 1 cm, "write big" cues: LIT PDT-18, PDT-19).
  - *Guided practice*: when the app knows the target text (copying, dictation), the nose nudges toward the letter shape, with limited force.
  - *Capture*: record the writing for the app.
- **Safety.** Travel and force limits; authority scaled by the tracker's confidence; the pen yields to the hand; guidance is always partial and never draws a letter the user did not start.

## 6. The optional inertial module

You asked for inertial control of the pen body as well. The study (`opt_inertial.md`) sizes a reaction mass or gyroscope pair for the rear of the handle. It reports honestly how much it adds on top of the moving nose, and how that depends on how the grip gives: sliding versus tilting (r_rot), which has never been measured (EXP-I01). Its numbers are in `opt_inertial.md` §1; this section will carry them once final.

## 7. The optional guidance board

A desk board under the paper that can physically steer the pen along whole letters, for practice (DEC-031; [`guidance_board.md`](guidance_board.md)).

- **How it works.** Under a 3 mm glass top, a quiet XY stage (like a 3D printer's) moves a strong permanent magnet. The pen carries one small magnet (6.35 mm, 0.75 g) in a keel under its fixed sleeve. The board pulls the pen, and so the hand, along the letter. The pen's nose still makes the fine ±3 mm corrections of the ink.
- **Force and speed (CALC).**
  - 1.2 N available in every direction on A4, capped at 0.4 N in software.
  - No power to hold the force.
  - About 25 Hz and 8 ms.
  - Size: 300 × 420 × 57 mm, about 4 kg.
- **What 0.4 N does to a hand (CALC).** A relaxed hand moves about 0.76 mm per 0.1 N; a lightly resisting one about 0.35 mm. So the board leads a relaxed hand and only nudges a firm one. **The writer is always in charge.**
- **Practice results (SIM):**
  - tracing error 1.49 → 0.63 mm with full guidance, and 0.085–0.19 mm with the nose correcting the ink as well;
  - Parkinson's "write big" loops reach 0.93 of the target instead of 0.83;
  - in dictation spelling practice it cannot turn a letter you are set on into another (a 'b' stays a 'b'), but with a relaxed hand it can **demonstrate** the right letter (94 % of a 'd' on the correct side).
- **Limits.**
  - While guiding, the pen is pulled down by about 1 N extra.
  - It guides a moving pen, not a still one.
  - Learning must be shown without the board: guidance fades, with unassisted catch letters (LIT HAP-01…06).
- **Before building it:** test the guidance laws on people with a commercial haptic arm (3D Systems Touch, HAP-52).

## 8. Do we need optics, sensors, weights, electromagnets, custom mechanics?

| Technology | Needed? | What for |
|---|---|---|
| Motion sensor (IMU) | Yes | Measures the shake; the tracker separates it from writing |
| Optics (paper sensor) | Yes, in the bigger pen | Where the tip is on the page: needed for guidance and capture; helps the tracker |
| Electromagnets (voice coils) | Yes, in the pen | Move the nose, and so the ink tip, by up to 3 mm, fast enough to cancel shake |
| Custom mechanics | Yes | The flexure pivot, the nose, the skid ring and the fixed sleeve |
| Force and position sensors | Yes | Pen-down, writing force, nose position |
| Vibration motor | Yes | Cues |
| Weights | Maybe | A heavier handle damps some shake for some people with essential tremor (LIT ACT-18, ACT-19) but not Parkinson's tremor (LIT ACT-32). The active inertial module adds a little (§6) |
| Guidance board (permanent magnet under the paper) | Optional, for practice | Real guiding force over whole letters; permanent magnets, not electromagnets (no holding power) |
| AI in the phone app | Yes | Reads the writing, spots spelling, gives cues, keeps corrected notes |

**Evidence levels for the benefits.**
- *Tremor cancellation:* handheld active stabilisers work for eating in essential tremor (LIT ACT-16), but not consistently in Parkinson's (LIT ACT-31). Writing is harder, because the tip touches the paper and writing overlaps the tremor band. Pen results are simulation only.
- *Parkinson's size cues:* supported for writing size, with a speed and fluency cost to watch (LIT PDT-17…PDT-21).
- *Haptic guidance for handwriting learning:* mainly fluency, not shape, and retention must be tested (LIT HAP-10…HAP-14).
- *Dyslexia:* spelling help is a language task. The pen's physical guidance helps letter formation practice at most; the app's recognition and feedback carry the spelling help.

## 9. What to build and test first

1. **Grip split.** How the grip gives, by sliding versus tilting (EXP-I01). It decides where inertial devices act and how the nose's reaction reaches the hand.
2. **Bench active nose (EXP-R01, proposed):** pivot, coils and Hall sensing on a shaker with a hand simulant. Measure:
   - tip travel;
   - bandwidth;
   - force;
   - power;
   - the ring's feel and friction.
3. **Tracker on real writing (EXP-E01):** recorded writing of people with essential tremor and Parkinson's, and of healthy writers. It decides how much of the 76–91 % mechanical limit the pen can actually reach.
4. **The board's force map and latency (EXP-G01, EXP-G02),** then guided practice with people.
5. **Comparators in every trial:** a weighted pen and a thick-grip pen (LIT ACT-18, ACT-19).

## 10. What carries over from the pencil work

- The accelerometer tracker and its adjoint-tuned settings (DEC-025, DEC-028).
- The AI app: recognition, autocorrect, cues.
- The touchdown and lift ideas (DEC-026): they must be re-tuned for Rev H's sliding refill.
- The sim-to-real method (DEC-023).
- The slim pencil (P0.2, DEC-030) stays as a secondary variant for people who prefer a normal-sized pen and have small tremor.
