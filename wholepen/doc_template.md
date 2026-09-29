# Moving the whole pen against large tremor (study W)

## The answer in plain words

*Study W, 29 September 2026. Nothing here was built or measured on a pen or a person. Every number is labelled SIM
(simulation), CALC (calculation), LIT or MFR with its ledger id, ASSUMPTION or PROPOSED DESIGN; the simulator ranks ideas
and is not evidence of benefit to people (sim2 context of use COU-1, DEC-040).*

<!-- W:answer -->
**The short answer.**

- **If the whole pen is to shift, the strongest compact way is a collar.** You hold a sleeve (the collar); the whole inner
  pen swings inside it on a small two-way hinge 50 mm behind the tip, pushed by a flat coil in the collar's back wall that
  pushes back on the collar and so on your fingers — the Liftware spoon's principle (LIT ACT-16, ACT-17). It fits the
  review's envelope: 21.7 mm across, about 40 g, ±4 mm at the tip, about «HOLD50» W to hold still at a normal 50° slant
  where Rev J's nose needs 1.6 W (PROPOSED DESIGN, CALC).
  Weights, gyroscopes and pushing on the paper cannot do this job in a pen (§3).
- **But in the simulator, shifting the whole pen did not make the pen better than Rev J's moving nose,** which already
  moves the ink further (±6.57 mm) with far less moving mass. Carrying the whole 87 g Rev J pen, the collar changed the
  tremor left by 0–5 % against the same pen with the collar held still (the review's gate asks for at least 10 %), and
  with perfect knowledge of the tremor, sharing the work with it was worse than letting the nose do it all. With a light
  inner pen (24 g, closer to the design) it became as precise as the nose, and at 8 mm PD it lowered the tremor left by
  «LIGHT_GAIN_PD8» % — but it laid less ink («PD_severe|light_nose|coverage|0» % against
  «PD_severe|light_locked_nose|coverage|0» %), so no more words were read; and as the main corrector behind a small ±1 mm
  nib (the compact design) no stable causal control law was found (§4.4).
- **What would make the pen much better is knowing the tremor.** With the pen's best causal tremor estimate the nose
  leaves «ET_moderate|nose|tip_mm|1» mm (ET) and «PD_moderate|nose|tip_mm|1» mm (PD) of a 3 mm tremor, and the app reads
  «ET_moderate|nose|words10» and «PD_moderate|nose|words10» of 10 words. With perfect knowledge the same nose would leave
  «ET_moderate|nose_oracle|tip_mm|2» and «PD_moderate|nose_oracle|tip_mm|2» mm and all «ET_moderate|nose_oracle|words10»
  words would be read; even at 8 mm it would leave about 2 mm («ET_severe|nose_oracle|words10» and
  «PD_severe|nose_oracle|words10» of 10 words). The gap between the two is the estimate, not the mechanics.
- **At the tremor sizes recorded from real PD patients** (study R: 0.24 mm moderate, 1.72 mm severe) no extra travel is
  needed at all; the collar stayed still.

**Recommendation.** Keep the moving nose as the part that shifts the ink, and put the effort where the simulator says the
benefit is: the tremor estimate (EXP-W15) and keeping the ball on the paper during large corrections (EXP-W13). Keep the
collar as the reference design for shifting the whole pen and build it only as a bench mock-up (EXP-W11); adopt it only if
it beats the same pen with the collar held still by at least 10 % — for example for people whose tremor at the ink
exceeds the nose's reach, if EXP-W10 finds them. Gyroscopic and weighted tails stay out (proposed DEC-051).

**How the two ways of moving the ink work.**

1. **Moving nose (Rev J, what exists).** Only the front of the pen moves. The refill sits in a carrier that tilts on a
   small hinge far back inside the pen; magnets on the carrier and coils in the body tilt it, so the ball can move up to
   ±6.57 mm on the paper while the body stays in your hand. The pen measures the tremor and moves the ball the opposite
   way, like a steady-cam for the ink point. Its weakness: your writing pressure pushes the ball sideways, and the coils
   must hold against it all the time (1.6 W at a normal 50° slant, CALC; study B's balanced nib addresses this).
2. **Whole-pen collar (this study's design).** The part you hold becomes a sleeve that rests in the web between thumb and
   index finger and slides on the paper on a ring at its front; the ring carries your writing pressure. The whole inner
   pen — refill, a small fast nib, battery and electronics — hangs inside on a two-way hinge 50 mm behind the tip. A flat
   coil in the collar's back wall pushes on magnets on the inner pen's end, swinging it up to 4.6° each way: the tip moves
   up to 4 mm (5.2 mm across the page in the direction the pen leans). Because the ring, not the ball, takes the writing
   pressure, holding still costs about «HOLD50» W at 50° (CALC). The collar moves only at the tremor's own rhythm, only while a tremor
   is detected, and only for the part the nib cannot reach, so it never drags your letters: with it on, tremor-free
   writing moved at most «clean|collar_nose|moved» µm (SIM; the programme's rule is 25 µm). Why it did not help more: it
   swings a whole pen against your grip, and how far the ink then moves depends on how you hold the pen, which the pen
   cannot know exactly; the nose moves a light carrier against the heavy pen, which your grip barely affects.
3. **Why weights and gyroscopes cannot do it.** A weight can only push by being thrown the other way: 30 g moving ±4 mm
   pushes 0.12 N at 5 Hz, while your grip passes on about 0.6 N for every millimetre of tremor (CALC). A gyroscope strong
   enough to matter stores 5–18 J in its spinning rotors — like dropping the pen from 5–18 m — and in the simulator it
   only undid the harm its own 100 g did (SIM). The paper can push back with at most 0.3–1.4 N of friction against
   1.7–4.6 N of tremor force at 3–8 mm (CALC).

**What the simulator says** (two synthetic test writers, ten words; the tables below; "perfect knowledge" is a limit, not a
result anyone can have today):

- **Moderate tremor, 3 mm.** No help: «ET_moderate|none|tip_mm|1» mm (ET) and «PD_moderate|none|tip_mm|1» mm (PD) at the
  tip, «ET_moderate|none|words10» and «PD_moderate|none|words10» of 10 words. Rev J nose: «ET_moderate|nose|tip_mm|1» and
  «PD_moderate|nose|tip_mm|1» mm. Collar + nose: «ET_moderate|collar_nose|tip_mm|1» and «PD_moderate|collar_nose|tip_mm|1»
  mm — exactly what the same collar pen gave with the collar held still («ET_moderate|collar_locked_nose|tip_mm|1» and
  «PD_moderate|collar_locked_nose|tip_mm|1» mm): at 3 mm the nose covers the tremor and the collar stays still.
- **Severe tremor, 8 mm.** The nose leaves «ET_severe|nose|tip_mm|1» mm (ET) and «PD_severe|nose|tip_mm|1» mm (PD) and
  «ET_severe|nose|words10»–«PD_severe|nose|words10» of 10 words are read; with the collar «ET_severe|collar_nose|tip_mm|1» and
  «PD_severe|collar_nose|tip_mm|1» mm. About a quarter to a half of the ink goes missing whenever anything corrects this
  hard (ink laid «ET_severe|nose|coverage|0» % with the nose, «ET_severe|collar_nose|coverage|0» % with the collar, ET),
  because swinging the ball ±8 mm five or six times a second keeps lifting it off the paper. Perfect knowledge with the
  nose alone: «ET_severe|nose_oracle|tip_mm|1» and «PD_severe|nose_oracle|tip_mm|1» mm.
- **PD tremor that returns in pauses (8 mm).** It is mostly absent while the hand moves, so the ink shakes less than the
  class size («PD_reemergent_severe|none|tip_mm|1» mm with no help, «PD_reemergent_severe|nose|tip_mm|1» mm with the nose);
  with perfect knowledge the nose would leave «PD_reemergent_severe|nose_oracle|tip_mm|2» mm and every word would be read:
  the case where a better estimate pays most.
- **Real tremor sizes (study R's recorded PD tremor).** Moderate (0.24 mm): the pen's tremor detector never switched on,
  nothing moved and every word was read with any pen. Severe (1.72 mm, recorded at 7.9–8.5 Hz): no help
  «REAL_PD_severe|none|tip_mm|1» mm and «REAL_PD_severe|none|words10» of 10 words; Rev J nose «REAL_PD_severe|nose|tip_mm|1» mm
  and «REAL_PD_severe|nose|words10»; the collar pen with the nose «REAL_PD_severe|collar_nose|tip_mm|1» mm and
  «REAL_PD_severe|collar_nose|words10» (the collar pen with the collar held still and the nose working:
  «REAL_PD_severe|collar_locked_nose|tip_mm|1» mm and «REAL_PD_severe|collar_locked_nose|words10» — the gain is the collar
  pen's extra mass, not its motion); perfect knowledge «REAL_PD_severe|collar_nose_oracle|tip_mm|1» mm and
  «REAL_PD_severe|collar_nose_oracle|words10».

**What is honestly impossible, and why:**

- **Moving the ink ±10 mm from inside a 22 mm grip.** The collar gives ±4 mm (±5.2 mm in the tilt plane); ±5 mm needs a
  23.6 mm collar, ±6 mm 25.5 mm, and ±10 mm about 33 mm around Rev J's nose (CALC, §3d).
- **Much better writing from better mechanics alone.** The mechanics' own limit (perfect knowledge) is already far better
  than what the pen achieves; what separates them is the tremor estimate. More travel or a stronger actuator does not
  close that gap (SIM).
- **Knowing the tremor exactly while writing**, because tremor (4–8 Hz) and fast handwriting strokes (4–7.7 Hz) overlap
  (the review's point 7). A better estimate can narrow the gap; it cannot close it.
- **Readable writing through 8 mm of continuous tremor today**: 0–2 words of 10 with any mechanism and today's estimate;
  even perfect knowledge gives 4–6 of 10 and loses about a quarter of the ink (SIM; whether a real refill stays on the
  paper better is EXP-W13). For severe tremor the realistic routes to legible words are the pen writing a known text by
  itself (autowrite, DEC-049) or a surface that steadies the hand.
- **A gyroscope or a weight in a pen that beats the same mass held still**, robustly: they must twist the pen against your
  fingers, and within about 100 g they cannot (CALC, SIM, §3b–3c).
<!-- /W:answer -->

### One number per tremor class and design: the tremor left at the pen tip (mm, peak)

Mean of the two test writers (SIM). "No help" is the Rev J pen with nothing moving. "Perfect knowledge" rows show what the
mechanism could do if the pen knew the tremor exactly: the limit of the mechanics, not a result anyone can have today.

<!-- W:table_tip -->
<!-- /W:table_tip -->

### The same cases: words the app can read (out of 10)

The app's handwriting recogniser reading each test writer's five-word sentence ("return library books by friday"), two
writers, words read correctly, summed; no language-model rescue (SIM). Two writers and one seed each: a ranking, not a
population estimate.

<!-- W:table_words -->
<!-- /W:table_words -->

### At the real tremor sizes (study R)

Study R measured tremor at the pen tip in recorded PD spirals (fitted on 24 tuning patients, checked on 25 test patients):
mild 0.03–0.16 mm, moderate 0.16–0.51 mm, severe above 0.51 mm, typically 1.72 mm — far below the 5–10 mm this study
was asked to design for (the tablet recordings, with the hand resting, may understate free-air tremor, and the severe class
rests on three tuning patients). The same designs with recorded PD tremor from study R's library (test split) at its
representative moderate (0.24 mm) and severe (1.72 mm) amplitudes (SIM, test writers 0–1):

<!-- W:table_real_tip -->
<!-- /W:table_real_tip -->

Words read (out of 10):

<!-- W:table_real_words -->
<!-- /W:table_real_words -->

**What changes at the real sizes.** Nothing needs more reach: 1.72 mm is well inside the nose's ±6.57 mm and the
collar's ±4 mm. In the simulator, at 0.24 mm the pen's tremor detector never switched on — nothing moved, and every word
was read with any pen. At 1.72 mm (recorded at 7.9–8.5 Hz, faster than the 5 Hz assumed for PD above) the nose took the tip
tremor from «REAL_PD_severe|none|tip_mm|2» to «REAL_PD_severe|nose|tip_mm|2» mm (words «REAL_PD_severe|none|words10» →
«REAL_PD_severe|nose|words10» of 10); the collar did not swing (its share is zero inside the nose's reach), and the collar
pen's extra gain («REAL_PD_severe|collar_nose|tip_mm|2» mm; «REAL_PD_severe|collar_locked_nose|tip_mm|2» mm with the collar
held still) came from its extra 22 g. Perfect knowledge would give «REAL_PD_severe|collar_nose_oracle|tip_mm|2» mm and
«REAL_PD_severe|collar_nose_oracle|words10» of 10 words: again the estimate is the limit. Study R, on real writing with its
own writer model, found the same pattern more starkly (0.2–0.5 of 10 words with causal trackers, 7 of 10 with perfect
knowledge). So at these sizes the collar's reason to exist disappears, the "write only when in reach" gate never triggers
and the gyroscope and weights stay pointless. A paper-grounded force becomes relatively stronger (the grip passes on about
1 N at 1.7 mm, comparable with the paper's 0.3–1.4 N of friction, CALC), so an amplitude-gated paper force (EXP-W17) is
worth more here than at 8 mm. The whole-pen collar is relevant only for people whose tremor at the ink exceeds the nose's
reach, whom the recordings did not contain (EXP-W10 must look for them).

How to read a ratio: the tremor left divided by the tremor with no help. **0.5 means half the amplitude, which is 75 %
less tremor power (−6 dB); it is not "75 % less tremor".** The ratios are in §4.4.

### Before and after

![The same writer, sentence and tremor with each pen (SIM)](../results/wholepen/fig_w_writing.png)

*SIMULATION: test writer 0, the first two words, grey = the letters the writer meant, black = the ink; true scale on 8 mm
lines. Rows: ET 3 mm, ET 8 mm, PD 8 mm. Columns: no help, the Rev J nose, the whole-pen collar with the nose, the nose with
perfect knowledge of the tremor (the mechanism's limit). Under each: the tremor left, the words of writer 0's five read by
the app, the share of the ink laid. The pictures are synthetic; they carry this label wherever they are shown.*

![Tremor left and words read per class: no help, the Rev J nose, the collar with the nose, the nose with perfect knowledge (SIM)](../results/wholepen/fig_w_headline.png)

*SIMULATION, two test writers per bar (bars missing where a design was not run on both). The perfect-knowledge bars are
the mechanism's limit, not a result anyone can have today.*

### The whole-pen collar in one picture

![The whole-pen collar (PROPOSED DESIGN)](../results/wholepen/fig_w_system.png)

<!-- W:recommend -->
**The whole-pen collar: the reference design for shifting the whole pen** (PROPOSED DESIGN; CALC unless marked; a bench
experiment, not adopted for the product: §5). How it moves over one tremor cycle is in `results/wholepen/animation.json`
(keyframes from the simulation) and its parts in `results/wholepen/layout_parts.json`.

| | |
|---|---|
| What you hold | a collar 21.7 mm across, about 100 mm long (PA12-CF, 1.2 mm wall), resting in the thumb-index web, with a skid ring on the paper at its front that carries the writing force and a load cell that measures it |
| What moves | the inner pen (12 mm aluminium tube, 92 mm): refill and a small fast nib (±1 mm assumed; study B's draft finds only about ±0.56 mm fits a 12 mm core, with a piezo bender), board and IMU, a 10280 Li-ion cell behind the pivot so the pen balances on it |
| How it moves | a two-axis cross-strip flexure pivot 50 mm behind the tip; ±4.6° swing → ±4 mm at the tip, ±5.2 mm across the page in the tilt plane (the ball slides on its refill spring to stay on the paper); the refill's front stop follows the paper while the ring is loaded and lifts with the pen when it is not |
| What pushes | magnets on the inner pen's end face over a two-axis coil plate in the collar's rear wall, 42 mm behind the pivot (Rev J's C1S actuator principle at 3.6 × its lever); reaction into the collar and the hand. Two geared 8 mm motors (MFR AMF-120) do not fit beside the swinging pen |
| Control | the gated listening tremor estimate with the guarded fallback; the collar takes only the share of the estimated tremor the nib cannot reach, at the tremor line only; the nib is commanded on what the collar leaves at the ink |
| Mass | collar 18.3 g, inner pen 21.9 g, **40.1 g** in total |
| Power | holding: «HOLD35» / «HOLD50» / «HOLD75» W at 35 / 50 / 75° (the refill spring's side load at the ball times the 50 mm lever, «HOLDM35» / «HOLDM50» / «HOLDM75» mN·m, at 27 mN·m/√W; Rev J's nose: 4.72 / 1.63 / 0.17 W); swinging for 8 mm tremor: about «CALC_SWING_W» W more (CALC, light inner pen). The simulated collar carried the 87 g Rev J pen as its inner pen, with the actuator modelled at 42 mN·m/√W: 0.12–0.13 W during tremor-free writing, 0.2–0.35 W at 3 mm, 0.8–2.4 W at 8 mm (SIM; up to 3.0 W with perfect knowledge) |
| Safety | the moving pen is inside the collar (no pinch point for the fingers); force at the tip ≤ the motor's peak; a limiter keeps the pivot off its stops (REQ-WP-008: the simulator reached the stops at 8 mm); unpowered, a centring latch must hold the pen (the flexure alone is soft: open issue); no stored energy beyond the cell |
| Feel | the grip-force change the writer feels (SIM, Rev J pen as the inner pen): 0.03–0.04 N rms with the causal law (the collar mostly still); with perfect knowledge 0.08–0.12 N rms at 3 mm and 0.22–0.38 N rms at 8 mm |
<!-- /W:recommend -->

### Results cards (one per population and mode; the review's §13)

<!-- W:cards -->
<!-- /W:cards -->

---

## Details

This study answers the user's request for "much better mechanics" to shift and pivot the whole pen against hand tremor of
1–10 mm, and the independent review of 29 September (§§5, 6, 12; the lead's response
`docs/reviews/2026-09-29_review_response.md`). SIM means MuJoCo sim2 with the sim2j firmware in the loop and synthetic
writers.

### 1 Tremor at the pen tip: the targets (task 1)

Amplitude convention everywhere: **peak** = half the peak-to-peak excursion of a sine of the same power along the
tremor's main axis, at the ink, in the page plane. The classes are ASSUMPTION built on the sources below and stay
hypotheses until EXP-W10 measures pen-tip tremor while writing (`wholepen/targets.py`, `results/wholepen/targets.json`).

| Class | Peak at the tip (range) | Value simulated | Basis |
|---|---|---|---|
| ET mild | 0.5–1.5 mm | 1 mm at 6 Hz | spiral rating FTM about 1 gives 1.1 mm peak on a tablet (LIT PDT-12: log10 T(cm p-p) = 0.6 FTM − 1.27, 18 ET patients); cohort median about 1 mm |
| ET moderate | 2–4.5 mm | 3 mm at 6 Hz (and 9 Hz) | FTM about 2: 4.3 mm peak (PDT-12) |
| ET severe | 5–17 mm | 8 mm at 6 Hz | FTM 2.5–3: 8–17 mm peak (PDT-12); tablets lose very severe tremor (PDT-13) |
| PD action mild | 0.2–1 mm | 1 mm at 5 Hz | recorded drawing tremor 0.3–1.4 mm at the pen's sensor in 4 of 26 NewHandPD patients; UCI spirals ≤ 0.45 mm (REAL DATA, LIT PDT-67, PDT-30) |
| PD action moderate | 2–4 mm | 3 mm at 5 Hz | MDS-UPDRS 2 (1–3 cm maximal amplitude at the limb, LIT PDT-68); ASSUMPTION at the pen |
| PD action severe | 5–10 mm | 8 mm at 5 Hz | rest-tremor amplitudes re-emerging in pauses and slow strokes off medication (PDT-09, PDT-65); ASSUMPTION |
| PD re-emergent | 5–10 mm | 8 mm at 5 Hz, suppressed by movement, re-emerging over about 3 s in pauses | PDT-09 (12 of 18 PD with rest tremor, latency 9.4 ± 10.7 s, about 5.5 Hz); PDT-65 (25 % of PD with tremor have lagged mixed tremor) |
| PD recorded | 3 mm | a recorded NewHandPD patient's tremor line (5.37 Hz, its own amplitude and frequency wander), scaled | REAL DATA (PDT-67) |

The 8 mm classes stand for the 5–10 mm band the brief asked for; 10 mm itself was not simulated, because at 8 mm every
mechanism already runs out of paper contact and of estimate (§4.4). Study R's recorded classes (0.24 and 1.72 mm) are
simulated separately (above, "At the real tremor sizes").

How often PD tremor matters while writing (LIT): action tremor in 36–39 % and rest tremor in 52–69 % of PD in three
cohorts (PDT-08); 96.2 % of de novo PD show some tremor within 7 years (PDT-66); writing tremor proper in 10 % of 100
consecutive PD patients, 26 % of those with postural or kinetic tremor, task-specific in 4 of 10 (PDT-63). ET tremor while
writing is kinetic, usually 4–8 Hz and often along one axis (PDT-56, PDT-36). Recorded data (REAL DATA, CALC; `results/wholepen/realdata.json`):
the UCI spiral archive shows PD tremor of at most about 0.45 mm (pixel pitch 0.204 mm, MFR AMF-180, ASSUMPTION that the
coordinates are pixels); NewHandPD's pen accelerations show a tremor line (4.4–5.9 Hz) in 4 of 26 patients while drawing,
about 0.3–1.4 mm at the pen's sensor and bursty. **Most PD writers have small tremor at the pen; the 3–8 mm classes are a
minority, but they are the people this study is about.**

### 2 The grip: how freely a held pen can pivot (task 2)

The model every simulation here uses is H1's two-zone grip (identical to study K's): finger pads at 32 mm from the tip,
the thumb-index web at 92 mm, calibrated so the tip sees the measured stylus-grip impedance of LIT HAP-26 (575 N/m,
1.3 N·s/m). What is not measured is how that compliance splits between the pen sliding and the pen rotating in the fingers
(r_rot, EXP-I01); every result is given at r_rot 0.3 / 0.5 / 0.7 and, new in this study, at grip stiffness 0.5 / 1 / 2 ×
(HAP-26's own range is 228–1043 N/m). Bounds used (CALC on LIT; `results/wholepen/grip.json`): three finger pads give
about 5.8 kN/m of skin shear stiffness (HAP-31 power law at the digit forces of CON-04); finger joints 0.45–0.71 N·m/rad
while tapping and 1.0–1.7 N·m/rad expected at higher forces (HAP-115); the wrist 1.3–1.7 N·m/rad (HAP-32).

**What this means for "pivoting the pen in the hand":** a pen held in the fingers resists being tilted in the grip with
about 1.0–4.8 N·m/rad (CALC, nominal 2.9 N·m/rad: about 50 mN·m per degree, or 29–96 mN·m per millimetre of tip motion
by tilting). Tilting the pen *against the skin* is therefore expensive and grip-dependent. Tilting it *in a bearing inside
something the fingers hold* (a collar) costs only the pen's own inertia and the ball's drag: «CMPC_TQMIN»–«CMPC_TQMAX» mN·m per
millimetre for a light inner pen (CALC, §3d). That difference is the whole argument for the collar.

### 3 The candidates, designed (task 3)

Three places a pen can push against, and what each can do at tremor speed:

| Push against | Example | What limits it | Verdict |
|---|---|---|---|
| the hand (the motor reacts on what the fingers hold) | Rev J's moving nose; **the whole-pen collar** | travel inside the grip; knowing the tremor | the only way to move the ink by millimetres at 4–10 Hz in a pen |
| a mass inside the pen (inertia) | gyroscopic tail, reaction or tuned mass | force = m ω² X; a gyroscope's stored energy | cannot beat the same mass locked in closed loop (§3b, §3c, §4.5) |
| the paper | heel wheel, a hand-rest sled | friction μN ≈ 0.3–1.4 N against the hand's much larger tremor force | trims a little; the heel wheel stays retracted by default (the review) |

#### 3a Rev J baseline and its static load (the review's point 1)

The Rev J nose (C1S) tilts only the refill carrier, on a gimbal 76.5 mm behind the ball, ±6.57 mm at 50°. Its magnets
sit on an 11.5 mm arm, so the refill spring's side load at the ball, F_c cot θ, reaches the coils 6.65 × larger. CALC
(`wholepen/calc.py nose_static`, reproducing the review): **4.72 / 1.63 / 0.17 W at 35 / 50 / 75°** while the ball is on
the paper. Every Rev J result in this study counts it: the simulated nose power (P_nose, SIM, sim2j's coil model with the
contact-gated bias) is 1.9–2.8 W per pen (median 2.2 W) in every design that keeps the Rev J nose, whether or not it
corrects (up to 4.4 W where the light collar's clipped nose was driven hard, and 6.7 W in its unstable re-tuned law). The collar
design below does not carry this load (its ball rides on a light refill spring and the writing force goes through a skid
ring on the collar); its fine nib is assumed to be a balanced nib without the static load (ASSUMPTION). Study B's draft
(`docs/balanced_nib.md`, in progress when this was written; CALC there) reproduces the 4.72 / 1.63 / 0.17 W, balances the
load with a counter-face for a ±1 mm coil nib in a 24 mm pen (8–18 mW), and finds that magnet-and-coil nibs around a D1
refill do not fit a 12–16 mm core, where a piezo bender gives about ±0.56 mm: **the collar's 12 mm inner pen would carry
about ±0.5 mm of fine nib, not ±1 mm**, unless the barrel grows (open issue 3).

#### 3b The gyroscopic tail (severe-tremor candidate)

A detachable tail behind the thumb-index web (it may be up to 30 mm across; the held part stays ≤ 24 mm), with **one
scissored pair of control-moment gyroscopes on a turret** (two tungsten rings spinning in opposite senses, gimbals tipped
in opposite senses by one motor through scissor gears so their twists add on one axis and cancel on the others, LIT
PAT-37; the turret turns that axis to the tremor's main direction at ≤ 1 rad/s). Sized in `designs.cmg_design` (CALC,
PROPOSED DESIGN): for a 100 g module, two 26.7 g rings (r 6.25–12.5 mm, 4.0 mm thick) at 25 000 rpm, h = 6.8 mN·m·s per
rotor, pair torque 0.38 N·m at 5 Hz with ±1 rad gimbals (2 h ω 2 J₁(1)); spin power 0.52 W; tone 417 Hz; rim 32.7 m/s,
hoop stress 19 MPa (margin 38 on the alloy's 724 MPa, MFR AMF-49), bearings at 0.29 × their listed limit (MFR AMF-126);
spin-up 4.5 s; module 64 × 28.6 mm. **Stored energy 17.8 J** — the energy of a 100 g pen dropped from 18 m. A seized
bearing would dump the rotor's momentum as a 0.68 N·m jolt over 10 ms (CALC, ASSUMPTION 10 ms).

The review's examples, recomputed (CALC, `calc.cmg_sizing`, `results/wholepen/calc.json`; plotted in
`results/wholepen/fig_w_cmg_energy.png`):

| Rotor | h per rotor | Stored (all rotors) | Largest tip tremor it could cancel at 5 Hz (perfect knowledge) |
|---|---|---|---|
| review: solid 20 g, r 6 mm, 30 000 rpm | 1.13 mN·m·s | 1.78 J | 1.9 mm (one rotor as a pair's worth: 12.4 mN·m at 5 Hz with 20°, matching the review) |
| review: solid 20 g, 25.2 mm diameter, 30 000 rpm | 5.0 mN·m·s | 7.8 J | 8.6 mm |
| study W pair, 60 g module | 1.7 mN·m·s | 4.6 J | 3.0 mm |
| study W pair, 80 g module | 4.3 mN·m·s | 11.2 J | 9.8 mm |
| study W pair, 100 g module | 6.8 mN·m·s | 17.8 J | 17 mm (9.8 mm at 9 Hz) |

The torque a gyroscope must make is large because it has to *rotate the pen in the grip* against the fingers and the
pen's own tail-heavy inertia: 22–69 mN·m per millimetre of tip tremor (CALC). Two further limits: the gimbal motor must
carry 2 h Ω, the gyroscopic reaction of the writer's own pen rotation (20–41 mN·m at 1.5–3 rad/s for the 100 g module,
CALC), and a passive spinning rotor (gimbals locked, one rotor) cross-couples axes and is not a damper (the review; the
scissored pair's net momentum is zero, so locked it is just a mass). **Containment:** a burst ring in three pieces carries
about 68 % of its energy as translation (CALC); a pen wall cannot be relied on to contain 5–18 J, so a burst must be
excluded by design (stress margin ≥ 3, over-speed trip, balance grade G1, ASSUMPTION practice), and the tail is a bench
experiment only.

With perfect knowledge the linear model says a 100 g pair would pass the review's gate by a wide margin (42–86 %
better than the same 100 g locked, CALC, `tail_gate`; the conditions are hand-path tremor of 3 and 8 mm at 5–9 Hz). In the
closed loop (SIM, §4.3): the 100 g tail, locked, makes the pen harder to correct (its mass moves the pen's rocking into the
tremor band and the ball leaves the paper more often); the rate-damping law recovers that, which passes the gate against
the locked tail but gives nothing against having no tail. The phasor feed-forward and the adaptive law did worse than
damping (the grip's response at the tail changes with the writer, so a large torque cannot be phased reliably).

What gyroscopic tremor devices show (LIT): they are worn on the hand or forearm, where they have a large lever and the
limb's own inertia to work with — the GyroGlove (about 580 g, rotor up to 10 000 rpm) reported the writing task 48 %
better than no device and 40 % better than placebo in a small study (ACT-25, ACT-61, ACT-81); a 145 g gyroscope glove
reduced a 4–7 Hz swept tremor on a bench by more than half (ACT-27); a hand-held gyroscope patent claims about 92 % less
angular velocity (ACT-28); a low-cost glove prototype 43–72 % (PDT-42, with its own table implying the lower numbers);
parameter studies ask for as much flywheel inertia and speed as the design allows (ACT-82). Haptic CMG devices at hand
scale use 13–138 g flywheels at 6 600–20 000 rpm in 0.2–0.8 kg devices (HAP-82, HAP-83, HAP-87), and scissored pairs for
the body are kilogram-scale (PAT-37, PAT-38). Study K found spin gave nothing over the same mass not spinning on the Rev J
end-cap (ACT-88). None of this transfers to a pen held in the fingers, where the device must twist the pen *against the
grip* and within about 100 g.

#### 3c Tuned and reaction masses

A mass m moving ±X on a fixed base pushes with at most m ω² X: 30 g over ±4 mm gives 0.118 N at 5 Hz and 0.474 N at
10 Hz; 0.5 N at 1 Hz would need ±422 mm (CALC, matching the review's table). A coil must also carry the flexure:
F_coil = X √((k − mω²)² + (cω)²) (CALC, `calc.reaction_mass`). Against the same mass locked (CALC, perfect knowledge,
`tail_gate`, grips 0.5–2 ×, splits 0.3–0.7, 5–9 Hz):

- **Tuned (passive) 40 g at the tail:** worse than the same 40 g locked in most conditions (−92 % to +23 %; passes the
  10 % gate in 18 % of them). A tuned mass pins the tail and the pen then pivots about its tail, so the tip moves *more*.
  The simulator agrees (SIM, tuning writer: tip 3.98 mm with the tuned mass against 3.56 mm for the base pen; semi-active
  retuning 3.95 mm).
- **Active reaction mass 30 g, ±4 mm, 0.6 N:** +16 % on average over the locked mass with perfect knowledge, but only
  in 56 % of conditions, and −25 % at 8 mm where its stroke runs out.

These match the review (§5) and study K: an internal mass is a high-frequency trim, not a way to move the ink by
millimetres at 5 Hz.

![Tail modules against the same mass locked (CALC, perfect knowledge: an upper bound)](../results/wholepen/fig_w_tail_gate.png)

#### 3d The whole-pen collar (the review's option B): the strongest way to shift the whole pen

**What it is.** The fingers hold a collar (a sleeve about 21.7 mm across) that also rests in the thumb-index web and carries
a skid ring on the paper at its front. The whole inner pen — a 12 mm barrel with the refill, a small fine nib, the cell and
the board — hangs in the collar on a two-axis flexure pivot 50 mm behind the tip. A two-axis magnet-and-coil actuator in
the collar's rear wall swings the inner pen: magnets on the inner pen's end face, 42 mm behind the pivot, slide over a flat
coil plate (Rev J's C1S actuator principle at 3.6 × its lever); it pushes back on the collar and so on the hand (the
Liftware principle, LIT ACT-16, ACT-17, PAT-08, PAT-12). Geared motors were the first choice, but two 8 mm motors (the
Faulhaber 0824 B, MFR AMF-120) do not fit beside a swinging 12 mm pen inside a 21.7 mm sleeve (CALC).

**How it moves.** A pivot angle of 4.6° moves the tip 4 mm (the review: 2.3° for 2 mm). Sideways, the ink moves exactly
z_p × angle; in the tilt plane the ball also slides along the pen on its refill spring to stay on the paper, which adds
cot θ: the ink moves z_p × angle / sin θ, 1.3 × more at 50° (CALC; the simulator confirms both within 2–3 %,
`verification.json collar_v2_transmission`). The rear of the inner pen swings the other way, ±3.4 mm at its end face 42 mm
behind the pivot — inside the sleeve, over the coil plate (the whole Rev J pen used in the simulation, 145 mm long, swings
±7.6 mm at its cap, in free air behind the web).

**Why V2 (skid ring on the collar) and not V1 (the whole pen, skid ring included, swinging).** In V1 the writing force
passes through the pivot to the tip: its moment N z_p cos θ = 32 mN·m at 1 N must be held by the actuators (0.59–1.24 W,
CALC), and tilting the pen presses the skid ring into the paper or lifts it (SIM, development runs of V1 on tuning writer
100: the ink was laid only 44–64 % of the time under correction). In V2 the skid ring carries the writing force and the ball only its 0.15 N refill spring: the
moment is F_c cot θ z_p = «HOLDM50» mN·m at 50° («HOLD35» / «HOLD50» / «HOLD75» W at 35 / 50 / 75° with the coil plate, CALC). The refill's front stop must follow the paper while the skid ring is
loaded (a load cell tells), bounded to 3 mm, and lift with the pen otherwise, so strokes do not join (PROPOSED DESIGN;
SIM: with a ±0.05 rad, 6 Hz swing the ball stayed on the paper 99.8 % of the time with this stop and 70 % with a stop that
follows only the pivot angle, development runs; `verification.json` repeats the first).

**Geometry** (CALC, `calc.collar_geometry`, PROPOSED DESIGN; 12 mm barrel, 0.8 mm wall, 0.3 mm running gap):

| Pivot from tip | Tip travel | Swing | Collar across | Fits 22 mm? |
|---|---|---|---|---|
| 50 mm | ±3 mm | ±3.4° | 19.8 mm | yes |
| 50 mm | ±4 mm | ±4.6° | 21.7 mm | yes |
| 50 mm | ±5 mm | ±5.7° | 23.6 mm | no |
| 56 mm | ±4 mm | ±4.1° | 20.8 mm | yes |
| 56 mm | ±5 mm | ±5.1° | 22.4 mm | no (by 0.4 mm) |

So a compact collar gives **±4 mm of body travel** (±5.2 mm of ink in the tilt plane); combined with a ±1 mm fine nib the
reach is about ±5 mm. For more, the collar must grow (±6 mm needs 25.5 mm) or keep Rev J's ±6.57 mm nose inside a larger
barrel.

**Mass** (CALC from volumes and placements, PROPOSED DESIGN; `calc.collar_masses`): collar «M_COLLAR» g (PA12-CF sleeve
1.2 mm wall, flexure, skid ring, load cell, coil plate and back iron), inner pen «M_INNER» g (0.5 mm aluminium tube, refill
and fine-nib stage, a 10280 Li-ion cell, board, magnets on the end face), **«M_TOTAL» g in total**, inside the review's
40–65 g target; its centre of mass «ZG_INNER» mm from the tip, «ZG_DIFF» the 50 mm pivot. With two geared 0824 B motors
instead of the coil plate it would be «M_GEARED» g, but they do not fit (above).

**Does it stay controllable across grip strengths, and does the web lock the barrel?** (the review's decisive question;
CALC, `calc.collar_control`, grip 0.5–2 ×, split 0.3–0.7, 4–10 Hz; the controller's model assumes grip 1 ×, split 0.5 and
the web on the collar)

<!-- W:collar_control -->
<!-- /W:collar_control -->

![How much of the ideal lever reaches the ink, compact pen (CALC)](../results/wholepen/fig_w_collar_transmission_compact.png)

It stays controllable: with one fixed model the loop keeps a positive margin in every condition (≥ «CMPC_MARGIN» for the
compact pen with the web on the collar). **The web does not lock the barrel, but where it rests on the barrel it takes part
of the motion** (the ink then moves «CMPB_TMIN»–«CMPB_TMAX» × the ideal lever, depending on the grip), and that share
depends on the writer; the design therefore puts the web on the collar (a saddle to z 97 mm) and the heavy parts close to
the pivot. The Rev J pen is too heavy and tail-heavy to be the inner pen: the controller's model is then off by up to
«RVJC_PH»° against «CMPC_PH»° for the compact pen — and the simulator agreed (§4.4: with the Rev J pen inside, perfect
knowledge through the collar did worse than through the nose; with a light inner pen, as well as the nose). Actuator
torque for the
compact pen: «CMPC_TQMIN»–«CMPC_TQMAX» mN·m per millimetre of tip tremor (CALC; «CALC_TAU8» mN·m peak for 8 mm at 6 Hz,
nominal grip), so the tremor itself costs about «CALC_SWING_W» W with the coil plate, and holding against the refill spring
«HOLD50» W at 50° (CALC). The reaction the fingers feel is that torque (SIM grip-force change in the recommend table above).

**Coarse and fine, and not chasing strokes.** The collar only moves at the tremor frequency: its command is a phasor at the
tracked tremor line, gated by the tremor-line detector, so it never follows the slow shape of letters (no template, no
consent needed for a motion it never makes). It takes only the share of the estimated tremor that the fine nib cannot
cover (`collar_alloc = "overflow"`: at 3 mm with Rev J's nose it stays almost still; at 8 mm it takes about half), and the
nib is commanded on what the collar leaves *at the ink* (§4.1).

**What the simulator says about it** (§4.4). Mechanically it does what the calculation says: a prescribed swing moved the
ink within 1–3 % of the linear model with the ball on the paper 99.8–100 % of the time (`verification.json`). As an
addition to the Rev J nose it changed little: 0–5 % against the same pen with the collar held still and the nose working
(the review's gate asks for 10 %), because the nose already covers tremor up to about 6 mm at the ink and the estimate, not
the travel, limits the result; and with perfect knowledge, handing half of the correction to the collar was worse than
letting the nose do it all (the grip makes the collar's effect at the ink uncertain). With a light (24 g) inner pen it
is as precise as the nose (perfect knowledge at 3 mm ET: «ET_moderate|light_nose_oracle|tip_mm|2» mm against the nose
alone's «ET_moderate|nose_oracle|tip_mm|2» mm) and at 8 mm PD it adds reach, but it lays less ink (§4.4).

#### 3e Paper-grounded force

The heel wheel stays retracted by default (the review; DEC-048). The whole-pen simulation study found its present tremor
mode helps only where the tremor is large or slow (4 Hz × 2 mm: 0.73 of the device-off ink error, where the nose alone
does nothing) but doubles the error of 0.3 mm tremor, moves tremor-free writing 0.40 mm and is felt at 167 mN rms (SIM,
sim2j, `docs/revJ_simulation.md` §6, §8.2). In this study's development runs (SIM, tuning writer 100, ET 3 mm at 6 Hz,
an earlier firmware configuration; not part of the frozen campaign) an idealised omni-directional heel pushing 0.37 N in
any direction removed about 15 % of the tip tremor, and a hand-rest sled carrying 2 N of the hand's weight onto a braked
element removed about half only with perfect knowledge of the tremor and nothing causally. The reason is simple (CALC):
the paper can push back with at most its friction, μN ≈ 0.3–1.4 N, while the hand's tremor drives the pen through the grip
with about 575 N/m × 3 mm ≈ 1.7 N at 3 mm and 4.6 N at 8 mm. Paper grounding can trim tremor; it cannot hold the ink still
against a large one. An amplitude-gated paper force (on only above about 2 mm of detected tremor) is worth one experiment
(EXP-W17).

#### 3f Write only when in reach

The pen lift raises the ball while the estimated tremor exceeds the nose's reach minus a margin, so ink is laid only where
the nose can cancel. The review's warning holds: the ink error falls because ink goes missing. Every such result carries
coverage (share of the letters' ink laid), missing strokes (strokes less than half inked) and completion time (if the pen
re-traced the lost ink afterwards at the writer's own speed, plus 0.2 s per lost piece: CALC on SIM). The writer model
does not wait for the pen, so the task time itself is unchanged; a real writer might slow down.

What it costs (SIM, from the saved records; the strokes are the writer's 42 intended strokes of the test sentence;
writer 0, and writer 1 at ET 8 mm; at 3 mm no pen lost more than «MOD_MISS_MAX» of the 42 strokes):

<!-- W:strokes -->
<!-- /W:strokes -->

At 8 mm the gate lowered the tremor in the ink that was laid (ET «ET_severe|nose_gate|tip_mm|1» mm against
«ET_severe|nose|tip_mm|1» mm with the nose alone, writer 0 only for the gate), but «GATE_ET_MISS» of the 42 strokes (ET)
and «GATE_PD_MISS» (PD) were then less than half inked, against «NOSE_ET_MISS» and «NOSE_PD_MISS» with the nose alone, and
re-tracing the lost ink would add «GATE_ET_EXTRA» s and «GATE_PD_EXTRA» s to a «TASK_S» s sentence. No word more was read.
Moving the ink more (nose or collar, even with perfect knowledge) also costs ink at 8 mm, though far less than the gate.

![Write only when in reach at 8 mm: what it costs (SIM, writer 0)](../results/wholepen/fig_w_gate.png)

#### 3g Combinations and optimisation

- **Gyroscope tail design** (CMA-ES over rotor radius, speed, gimbal range and gimbal-motor torque at a fixed 100 g,
  «CMB_EVALS» evaluations, perfect knowledge, `optimise.optimise_combo`, CALC): the optimum spins slower («CMB_RPM» rpm,
  rotor radius «CMB_RO» mm, ±«CMB_DMAX» rad gimbals, «CMB_TQ» mN·m gimbal torque), storing «CMB_E» J instead of
  «CMB_E0» J at the starting design, and its objective is only «CMB_GAIN» % better: the ceiling is set by the gimbal torque
  and the grip, not by the stored momentum. Exact torch gradient of the residual with respect to the tail mass «CMB_GRAD» (central
  difference). It does not change the closed-loop verdict (§4.5).
- **Collar design** (CMA-ES over the pivot position, servo stiffness and damping and the inner pen's centre of mass,
  «OPT_EVALS» evaluations, minimising the tremor left after the collar and a ±1 mm fine nib over 5–9 Hz, 3–8 mm, grips
  0.5–2 × and splits 0.3–0.7, with the 22 mm envelope setting the travel and a torque penalty; `optimise.optimise_collar`,
  CALC): the optimum moves the pivot back to «OPT_ZP» mm (±«OPT_TRAVEL» mm at the tip inside 22 mm, against
  ±«OPT_TRAVEL0» mm at 50 mm) and the inner pen's centre of mass forward to «OPT_ZG» mm, with a «OPT_KS» N·m/rad,
  «OPT_CS» N·m·s/rad servo, and lowers the objective by «OPT_GAIN» %. Both positions sit at the layout's bounds (pivot
  40–60 mm, centre of mass 40–60 mm), so the direction — a longer lever and a nose-heavy inner pen — is the result, not the
  values; it was not simulated. Exact torch gradient of the residual with respect to the pivot position «OPT_GRAD»
  (central difference).

### 4 Simulation (task 4)

#### 4.1 Method

sim2 (MuJoCo 3.6) with the sim2j firmware in the loop at 2 kHz (tracker, nose servo, pen lift), the H1 hand (HAP-26 +
two-zone grip) and, for a subset, the articulated arm; the H1 contact law; 50 µs steps (25 µs checked). New devices in
`wholepen/devices.py` (the CMG tail, tuned mass, the collar as an MJCF patch: the grip joints move to the collar body, the
pen hangs from it on two hinges driven by torque actuators with a 22 Hz position servo and the writing force's static moment
from the load cell; V2 moves the skid ring and its contact point to the collar). Device laws in `wholepen/control.py`, run
inside the firmware's tick (`wholepen/stepper.py`, a copy of sim2j's step with the insertions marked). The tremor is the
same hand tremor for every pen (its hand-path amplitude set on the Rev J pen with nothing moving), so a heavier pen shows
what its mass does. **Page sensor:** sim2j's measured-style model (DeltaPen per-window statistics, LIT OPT-02: lognormal
error per 10 ms window, median 23.6 µm, mean 68.3 µm, errors adding up); sim2j's 3 µm white noise is used only where
marked. **Tracker (the tremor estimate every causal device uses):** chosen on the tuning writer among sim2j's frozen
guarded tracker (G4), ai2's gated listening tracker with the Rev H tracker as its fallback (DEC-042), and the gated
listening tracker with the guarded tracker as its fallback, by ink error among those that move tremor-free writing by at
most 25 µm (sim2j's rule): the last was chosen. **Collar law:** the internal-model phasor law with the controller's model of the collar at grip 1 ×
and split 0.5; the nose is re-commanded on what the collar leaves at the ink (the measured barrel tip and the ink differ
by (G − G_ink) u because the ball slides on its refill).

Metrics: tremor left at the tip (§ conventions above), ink error against the writer's tremor-free letters, letters and
words read by the app's recogniser, coverage and missing strokes, the grip-force change the writer feels, power (the nose's
copper loss from sim2j's coil model; the devices' from `designs.py` electrical models on the simulated mechanics).

#### 4.2 Verification of the simulator for each new device

<!-- W:verify -->
(filled from `results/wholepen/verification.json`)
<!-- /W:verify -->

#### 4.3 Tuning and frozen rules

Rules were chosen on tuning writer 100, seed 300 only, and frozen in `results/wholepen/rules.json` (with its time stamp)
before any test run:

<!-- W:rules -->
<!-- /W:rules -->

The light collar with a ±1 mm nib (§4.4) got its own law, re-tuned on tuning writer 100 (ET 3 mm, seed 300) and frozen in
`results/wholepen/rules_light.json` before its test runs: «LF_RULE». The comparators added after the main test campaign
(the collar held still with the nose working, the nose alone with perfect knowledge, the light collar) used these frozen
rules unchanged.

The tuning cases (SIM, tuning writer 100, seed 300, five words; "Ink laid" = coverage; the collar's pivot has its hard
stop at 0.12 rad):

<!-- W:tuning -->
<!-- /W:tuning -->

What the tuning showed (SIM, writer 100 only):

- **The estimator matters more than any mechanism.** On this writer the pens with nothing moving leave about 3.3 mm
  (the 3 mm class) and 10.6 mm (the 8 mm class) at the tip (the collar pen locked). With sim2j's guarded tracker (G4) the
  Rev J nose left 3.12 mm and 11.06 mm; with the gated listening estimate 1.08 mm and 5.39 mm (but only 70 % of the ink
  laid at 8 mm). The
  listening estimate with the Rev H tracker as its fallback moved tremor-free writing by 135 µm (rule 25 µm); with the
  guarded tracker as its fallback, 5 µm and the same tremor results — that is the frozen choice.
- **The collar adds reach where the nose runs out.** At 3 mm it stays almost still (the nose covers it; same result). At
  8 mm it lowered the tremor left from 5.39 to 3.97 mm, but the pivot reached its hard stops (0.174 rad against 0.12) and
  less ink was laid (62 % against 70 %). The gentler setting (gain 0.5, share ≤ 0.6, reference ≤ 65 % of the range) was
  chosen; none avoided the stops at 8 mm.
- **The gyroscopic tail passes the gate only by curing its own harm.** The 100 g tail, locked, made the pen worse to
  correct (2.44 mm left with the nose, 64 % of the ink laid, against 1.08 mm and 94 % without a tail); its rate-damping
  law brought it back to 1.20 mm (82 % laid): 51 % better than the same mass locked (passes G5), still no better than no
  tail at all.
- **Write only when in reach** at 8 mm ET: 2.5 mm left instead of 3.6 mm, but only a third of the letters' ink laid.

#### 4.4 Test results

Test writers 0 and 1 (five words each), seeds 200 and 201, H1 hand, rules frozen before any test run. Ratios to "no help"
(SIM):

<!-- W:table_ratio -->
<!-- /W:table_ratio -->

**What the collar adds on top of the nose** (SIM, the same test writers; the comparator rows — the collar pen with the
collar held still and the nose working, and the nose alone with perfect knowledge — were run after the main test campaign
with the same frozen rules):

<!-- W:collar_increment -->
<!-- /W:collar_increment -->

Read across a row: with today's estimate the collar and the collar held still give the same result wherever the tremor is
inside the nose's reach (3 mm, the re-emergent class): the collar does not move, by design. At 8 mm it helps by a few per
cent — below the review's 10 % gate. With perfect knowledge, handing half of the correction to the collar (the
"collar + nose, perfect knowledge" column) is clearly worse than letting the nose do it all: the collar moves a whole pen
against the grip, so how far the ink moves depends on the writer's grip, which the controller's model only approximates
(the CALC model error of §3d, up to 53° with the Rev J pen inside); the nose moves a light carrier against the heavy pen,
which the grip barely affects. (A better split would give the collar only what the nose cannot reach; with Rev J's
±6.57 mm nose that is almost nothing below 8 mm.)

**A lighter inner pen** (the review's design point; SIM, the same test writers, ET 3 mm and PD 8 mm). The simulated collar
above carried the whole 87 g Rev J pen. Here the inner pen is the Rev J nose and refill in a 6 g barrel — 24 g, its centre
of mass 13 mm behind the pivot (the proposed compact pen is 22 g at the pivot) — with the servo damping scaled to it; the
"fine nib" rows clip the Rev J nose to ±1 mm as a stand-in for study B's nib:

<!-- W:light_compare -->
<!-- /W:light_compare -->

With a light inner pen the collar is as precise as the nose: with perfect knowledge, collar and nose leave
«ET_moderate|light_nose_oracle|tip_mm|2» mm of the 3 mm ET tremor (the nose alone «ET_moderate|nose_oracle|tip_mm|2» mm; with
the 87 g pen inside, «ET_moderate|collar_nose_oracle|tip_mm|2» mm), and at 8 mm PD «PD_severe|light_nose_oracle|tip_mm|2» mm
against the nose alone's «PD_severe|nose_oracle|tip_mm|2» mm. With today's estimate it stays still at 3 mm, as designed, and
at 8 mm PD it passes the review's gate on tremor («PD_severe|light_nose|tip_mm|2» mm against
«PD_severe|light_locked_nose|tip_mm|2» mm with the collar held still: «LIGHT_GAIN_PD8» % less) but not on ink:
«PD_severe|light_nose|coverage|0» % of the ink was laid against «PD_severe|light_locked_nose|coverage|0» % — the ball lifts when
the whole pen swings that far — so no more words were read. The fine-nib rows show the law's limits: with the main rules
(gain 0.5, collar share ≤ 0.6, chosen for the collar with Rev J's nose) the collar is far too timid to take the most of
the tremor a ±1 mm nib leaves to it («ET_moderate|light_fine|tip_mm|2» mm at 3 mm ET). «LF_PARAGRAPH»

#### 4.5 Against the same mass locked, at three grip strengths (the review's gate G5)

<!-- W:gate_sim -->
<!-- /W:gate_sim -->

![Each device against the same mass locked, three grip strengths (SIM, tuning writer)](../results/wholepen/fig_w_grips_sim.png)

Read: the gyroscopic tail passes the gate against its own locked mass at the soft and nominal grips on the tuning writer
(«GT_G05» % and «GT_G1» %) but not at the stiff grip («GT_G2» %) nor on test writer 0 («GT_TEST» %), and it never beat the pen
without a tail (§4.3). The collar with the Rev J pen inside never passes (from «COL_GMIN» % to «COL_GMAX» % against the same pen
with the collar locked and the nose working, at three grip strengths and on the test writers); with the light inner pen
it passes at 8 mm PD on tremor, but with less ink laid (§4.4). The nose's own row against the pen with nothing moving is
given for scale.

#### 4.6 The articulated arm

<!-- W:arm -->
(filled from `results/wholepen/arm.json`)
<!-- /W:arm -->

### 5 Proposed decision (number to be assigned by the lead)

<!-- W:decision -->
**DEC-051 (proposed): no whole-pen actuator in the product now; the moving nose stays the part that shifts the ink; the
whole-pen collar is the reference design for shifting the whole pen and stays a bench experiment; inertial tails are
rejected for the pen.** The collar (V2) is a held sleeve (≤ 22 mm across, resting in the thumb-index web, carrying the
skid ring and the writing force) with the inner pen on a two-axis flexure pivot about 50 mm behind the tip, swung ±4.6° by
a coil plate in the sleeve's rear wall that reacts on the sleeve (±4 mm at the tip, ±5.2 mm across the page in the tilt
plane). Why not now: in the simulator it changed the tremor left by 0–5 % against the same pen with the collar held still
and the nose working (the review's gate asks for 10 %), and with perfect knowledge sharing the correction with it was worse
than the nose alone (§4.4); with a light inner pen it became as precise as the nose and at 8 mm PD left «LIGHT_GAIN_PD8» %
less tremor than when held still, but laid about «LIGHT_COV_LOSS» points less ink, so no more words were read; and no causal law was found with which the collar is the main corrector behind a small ±1 mm nib (its loop became
unstable). Gyroscopic, tuned and reaction-mass tail modules cannot beat the same mass locked
robustly (CALC; SIM §4.5) and a gyroscope that could matter stores 5–18 J.
Alternatives considered: the collar in the product now (fails the gate); the gyroscopic tail as the severe-tremor device
(fails G5 in the closed loop, stores 5–18 J); a tuned or driven tail mass (worse than or no better than the same mass
locked); paper-grounded force (friction far below the hand's tremor force); a V1 collar in which the whole pen with its
skid ring swings (the actuators hold the writing force: 0.6–1.2 W, and the ring rocks off the paper); a bigger Rev J nose
(the refill spring's static load grows with the lever, the review's point 1).
Evidence: this document §§3–4 (CALC; SIM on synthetic writers). Revisit if EXP-W10 finds writers whose tremor at the ink
exceeds the nose's reach (about ±6 mm) while writing, or if the collar mock-up beats the same pen with the collar locked
by ≥ 10 % on the hand phantom (EXP-W11).

**DEC-052 (proposed): large-tremor modes use the gated listening estimate with the guarded fallback, and the estimate is
the priority for improving the pen.** On the tuning writer the gated listening estimate removed about two thirds of 3 mm
tremor at 6 Hz with the Rev J nose where the guarded tracker removed about a tenth (SIM), and the guarded fallback keeps
tremor-free writing within the 25 µm rule (§4.3). On the test writers the gap between this estimate and perfect knowledge
(3 mm: «ET_moderate|nose|tip_mm|1»–«PD_moderate|nose|tip_mm|1» mm left against «PD_moderate|nose_oracle|tip_mm|2»–«ET_moderate|nose_oracle|tip_mm|2» mm; «PD_moderate|nose|words10»–«ET_moderate|nose|words10» against «ET_moderate|nose_oracle|words10» of 10 words) is far larger than anything a mechanism added.
Revisit with EXP-W15 on recorded writing.

**DEC-053 (proposed): every device added to shift the pen is reported against the same pen with that device locked and
the existing corrector working, at three grip strengths, on a measured-style page sensor, with coverage, missing strokes
and completion time for any gated mode, and with power including the nib's static load.**
<!-- /W:decision -->

### 6 Proposed requirements

<!-- W:requirements -->
REQ-WP-001 applies to anything that would shift the pen; REQ-WP-002 to 009 apply to the collar mock-up (EXP-W11 to W13) and
to any product collar that later passes REQ-WP-001.

| Id | Requirement (PROPOSED) | Verified by |
|---|---|---|
| REQ-WP-001 | A device added to shift the pen (collar, tail module, paper force) enters the product only if it lowers the tremor left at the tip by ≥ 10 % against the same pen with that device locked and the existing corrector working, at grip 0.5, 1 and 2 × nominal, in the simulator and on the hand phantom, without lowering coverage by more than 5 points | SIM (§4.4, §4.5); EXP-W11; EXP-W14 |
| REQ-WP-002 | Collar ≤ 22 mm across; inner barrel ≤ 12 mm; tip travel ≥ ±4 mm at 4–10 Hz under a 1 N writing load; pen ≤ 55 g in total | CAD fit checks (`mechanics/cad/wholepen.py`); EXP-W11 |
| REQ-WP-003 | The writing force goes through the collar's skid ring; the inner pen carries only its refill spring; static holding power ≤ 0.2 W at 35° and ≤ 0.06 W at 50° (CALC «HOLD35» / «HOLD50» W; Rev J's nose 4.7 / 1.6 W) | EXP-W11 (current at rest while writing) |
| REQ-WP-004 | The refill follows the paper through the swing while the skid ring is loaded (bounded extension ≥ z_p × swing × cot θ_min + 0.3 mm, about 3.3 mm at 35°), and lifts with the pen when the ring unloads, so strokes do not join | EXP-W13 |
| REQ-WP-005 | The thumb-index web rests on the collar (a saddle to z ≥ 97 mm); the swinging barrel clears the web and the sleeve at full swing (fit margin ≥ 0.3 mm) | CAD fit checks; EXP-W12 |
| REQ-WP-006 | With one fixed controller model, the loop stays stable and removes ≥ 50 % of a 3 mm, 5–9 Hz tremor at grip 0.5–2 × nominal, web on the collar | EXP-W11 (hand phantom) |
| REQ-WP-007 | The collar moves only at a detected tremor line and only by the share beyond the nib's reach; it never follows letter shapes; tremor-free writing moves ≤ 25 µm with it enabled | SIM rule (§4.3); EXP-W15 |
| REQ-WP-008 | The pivot never reaches its hard stops in use: the reference stays ≤ 65 % of the range and a stop-approach limiter backs the servo off (the SIM hit the stops at 8 mm) | EXP-W11 (8 mm, 5 Hz) |
| REQ-WP-009 | The reaction the fingers feel stays ≤ 0.5 N rms grip-force change (SIM 0.03–0.38 N rms); noise ≤ 35 dBA at 30 cm (ASSUMPTION target); unpowered, a latch centres the inner pen | EXP-W12 |
| REQ-WP-010 | A tail module is tested only against the same mass locked (G5) at three grip strengths; a gyroscope stores ≤ 2 J and excludes a burst by design (stress margin ≥ 3, over-speed trip) | EXP-W14 |
| REQ-WP-011 | Every gated or ink-only-when-correct mode reports coverage, missing strokes and completion time beside its error | every report; EXP-W16 |
| REQ-WP-012 | Whole-pen results use the measured-style page sensor (OPT-02 statistics) by default; 3 µm white noise only as a labelled bound | every report |
<!-- /W:requirements -->

### 7 Proposed experiments (EXP-W10 onward)

<!-- W:experiments -->
| Id | Question | Set-up and measurements | Decides |
|---|---|---|---|
| EXP-W10 | How large is tremor at the ink while writing, per population? Does anyone exceed the nose's reach? | ET, PD-action and PD-re-emergent writers (≥ 20 each, reviewed protocol and consent) write the study's sentence and spirals on a digitising tablet with an ink pen and a 1 kHz IMU on the pen; ink amplitude along the main axis (peak, 2.5–20 Hz), frequency, axis, share of time with a line; free-air and hand-resting | the classes (§1); whether any whole-pen travel is needed (DEC-051 revisit) |
| EXP-W11 | Does the collar move the ink as calculated, across grip strengths, and does it beat the same pen with it locked? | V2 mock-up (3D-printed sleeve, cross-strip flexure pivot at 50 mm, a two-axis coil plate under magnets on the barrel's end face, 12 mm barrel with a refill and the paper-following front stop); a hand phantom with swappable grip springs (300 / 575 / 1100 N/m, split variants) on a shaker; paper on a force plate; optical ground truth of the ink; swept 2–12 Hz, ±1–5 mm; web on the collar vs on the barrel; collar active vs locked with the same nib working; current at rest while writing | REQ-WP-001/002/003/006/008; DEC-051 |
| EXP-W12 | Can people hold and write with it? | tremor-free adults first: comfort, felt reaction, noise, the web's contact, writing speed, with the collar locked and active (equal mass) | REQ-WP-005/009 |
| EXP-W13 | Does the ball stay on the paper during large corrections, for the nose and for the collar? | the Rev J nose and the mock-up's collar swung ±4–8 mm at 5–6 Hz on paper at 35 / 50 / 75°; ball load and contact continuity (the simulator lost a quarter to a half of the ink at 8 mm); the collar's paper-following stop; lifts between strokes | REQ-WP-004; whether severe-tremor correction can keep the ink |
| EXP-W14 | Do tail modules beat the same mass locked (G5)? | on the EXP-W11 phantom: tuned mass (40 g), driven reaction mass (30 g), gyroscope pair (≤ 2 J, in a burst-test housing) against the same masses locked, three grip strengths, 4–10 Hz | REQ-WP-010 |
| EXP-W15 | How close can a causal estimate get to perfect knowledge on real writing? | replay EXP-W10 recordings (and the NewHandPD / UCI data, study R's library) through the firmware estimators; tremor removed at the ink in the replay model against the perfect-knowledge limit; false correction on tremor-free writing ≤ 25 µm | DEC-052; REQ-WP-007 |
| EXP-W16 | What does "write only when in reach" cost people? | the Rev J pen with the gate on and off: legibility (blinded transcription), coverage, missing strokes, completion time, preference | REQ-WP-011 |
| EXP-W17 | Is an amplitude-gated paper force useful? (the lead's note) | the heel wheel's tremor mode enabled only above a detected tremor amplitude (e.g. ≥ 1–2 mm); clean-writing movement and the error at 1–3 mm and at 8 mm | whether paper grounding joins the severe mode |
<!-- /W:experiments -->

### 8 Open issues

<!-- W:open -->
1. **Ink contact under large, fast corrections.** At 8 mm tremor the ball stayed on the paper only 44–77 % of the time
   whenever the nose or the collar corrected hard, even with perfect knowledge (SIM; 88–96 % with nothing moving). Whether
   a real refill does better, and what keeps it on the paper, is the bench's question (EXP-W13) before any severe-tremor
   claim.
2. **The collar's own contribution is small and grip-dependent.** With the Rev J pen inside it added 0–5 % (fails the 10 %
   gate); with perfect knowledge a fixed 50/50 split with the nose was worse than the nose alone. An allocation that gives
   the collar only what the nose cannot reach was used causally but not simulated with perfect knowledge. As the main
   corrector behind a ±1 mm nib (the compact design) the collar's causal loop became unstable at the gains it needs
   (§4.4); a law that works there (for example with the collar's own pivot sensing in the loop, or a lower-bandwidth
   coarse stage) is still to be found.
3. **The simulated inner pen**: the main campaign used the 87 g Rev J pen; the light (24 g) variant ran on two classes
   only (§4.4). The proposed 22 g compact pen is CALC only, and its ±1 mm fine nib is an assumption: study B's draft finds
   that only about ±0.56 mm (a piezo bender) fits a 12–16 mm core.
4. **The pivot reached its hard stops at 8 mm** with the Rev J pen inside (peaks 0.16–0.18 rad against the 0.12 rad stop at
   ET 8 mm, 0.15 rad at PD 8 mm with perfect knowledge) even with the reference held to 65 % of the range; a stop-approach
   limiter is needed (REQ-WP-008).
5. **The causal estimate is the main limit.** The chosen one (gated listening, guarded fallback) was tuned on one writer
   and tested on two synthetic writers with one seed each; the gap to perfect knowledge (§4.4) is the programme's largest
   lever (EXP-W15).
6. **Unpowered state:** the flexure is soft (0.02 N·m/rad); a centring latch or detent is needed and not designed.
7. **Actuator detail:** the coil plate's force constant at a 42 mm lever is scaled from the Rev J nose's image-method value
   (itself contested, DEC-041); the simulated collar used a 42 mN·m/√W torque source with an 80 mN·m limit (geared-motor
   values); measure the coil plate (EXP-W11).
8. **The class amplitudes are not calibrated at the tip:** the same hand tremor is applied to every pen and the achieved
   no-help tip tremor is reported (larger than the class value for the 8 mm classes; smaller for the re-emergent class,
   whose tremor is suppressed while the hand moves).
9. **Real tremor sizes:** study R's recordings (tablet spirals, hand resting) put severe PD tremor at about 1.7 mm; the
   8 mm classes here are ASSUMPTION built on clinical scales. Only two recorded draws per class were simulated.
10. **Arm model:** only a small subset was run on the articulated arm (§4.6).
<!-- /W:open -->

### 9 Files and how to reproduce

- Package `wholepen/` — `python3 -m wholepen.run_study [--quick] [--stages ...]`; stages in order: targets, realdata,
  grip, calc, optimise, verify, tune, freeze, test, limits, light, light2, real, grips, arm, summary, figures (the
  simulation stages keep one row per case in `wholepen/build/rows/` and resume from it); `python3 -m wholepen.report`
  writes this document from `wholepen/doc_template.md`, filling every generated table and result number from the result
  files (edit the template, not this file). Tests: `pytest wholepen/tests -q` (15 tests, a few seconds).
- Results `results/wholepen/` (each JSON with `stabpen.provenance`, in `meta` for the explainer files): `targets.json`,
  `realdata.json`, `grip.json`, `calc.json`, `optimise.json`, `verification.json`, `tuning.json`, `rules.json`,
  `rules_light.json`, `test.json` (with the comparator rows of the limits stage), `light.json`, `real.json`, `grips.json`,
  `arm.json`, `summary.json` (the tables, the results cards, the collar's increment, the light-pen comparison and the
  stroke metrics from the saved records); figures `fig_w_*.png` with CSV twins; `animation.json` (keyframes from the
  simulation: time, part, position, angle), `layout_parts.json` (the explainer's schema), `evidence_rows.csv` (proposed
  ledger rows in the ledger's 23 columns).
- CAD: `python3 mechanics/cad/wholepen.py` → `results/wholepen/cad/` (STEP, drawing with CSV twin and the fit checks:
  the swung inner pen clears the sleeve by 0.72–1.00 mm and the coil plate by 0.52 mm).
- Data outside the repository: the UCI spiral archive and NewHandPD signals (paths in `wholepen/realdata.py`); study R's
  tremor library (`realdata.library`, read-only).
- The per-row fields `missing_strokes`, `missing_stroke_rate`, `autowrite_extra_s` and `completion_time_ratio` in the
  simulation rows count contact flicker as strokes and overstate the loss; the reported stroke metrics (§3f) come from the
  saved records (`summary.json strokes_from_traces`).
