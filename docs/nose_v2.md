# Rev J study N: nose v2 — a larger-travel tip, and a pen that writes letters by itself

**Status: calculation and simulation only, 2026-09-29.** Nothing here was built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation of model HW1 (`handwriting/`, used read-only through its public API; wrapper `nose2/autowrite.py`), on **synthetic** writers (`aiguide`) and **synthetic** tremor;
- **CALC**: a calculation (planner, front-end geometry, magnetics with magpylib, design models in `nose2/`);
- **LIT (id)** / **MFR (id)**: a published or manufacturer statement with its ledger id (`docs/evidence.csv`, or the rows this study proposes in `results/nose2/evidence_rows.csv`);
- **ASSUMPTION**: an input nobody has measured;
- **PROPOSED DESIGN**: a dimensioned concept (layout, CAD).

Numbers come from `results/nose2/nose2.json` (with its `stabpen.provenance` block) unless a ledger id is given. Tuning used writers 100–103 and seeds 300–303 only; every autowrite result in the tables uses the test writers 0–5 and test seeds 200–203, after the rules were frozen.

## 1. The answer in plain words

**Best mechanism (PROPOSED DESIGN, CALC).** Keep Rev H's idea — the skid ring carries the writing force and the refill carrier tilts on a two-axis flexure gimbal — but change where the parts sit and how the magnets face the coils:
- **Pivot far back, magnets close to it.** The gimbal moves back to 76.5 mm from the ball (Rev H: 45 mm). The magnets sit on a short arm only 11.5 mm behind it, just behind the refill's rearmost end. When the ball moves 6.5 mm the magnets move only 1.05 mm (lever 6.6).
- **A spherical gap.** The magnets are a 2 × 2 checkerboard on a soft-iron cap whose face is a sphere centred on the gimbal. They face two coil layers on a concentric spherical plate. Tilting slides the poles along the coils at a constant 0.77 mm gap. This is what makes the travel possible: in Rev H's layout the gap has to grow with the travel, and the force falls with it.
- **Handle Ø24 mm** where held (the Rev J limit). **Guaranteed ball travel 6.0 mm in every direction over 35–75° of tilt** (6.5 mm at 50°), more than twice Rev H's 2.75 mm.
- **Numbers (CALC):** 0.099 N/√W per axis at the tip; 2.1 g moving mass at the tip; coil loss 0.18 W while autowriting with 1 mm rms tremor on top (18 K coil rise; limit 20 K) and 0.16 W while only stabilising 1 mm rms tremor; 19 g added; first parasitic mode 790 Hz; 0.03 N rms reaction on the hand; pen 83 g, Ø24 × 175 mm.
- **The alternatives fall short** in the same handle and under the same rules: Rev H's radial-gap actuator scaled up (C1) reaches 5 mm; a flat axial gap (C1+) 4 mm; two actuation planes (C2) 5 mm at 38 g; a translating carrier (C4a) cannot keep its coils over its magnets. Galvanometers, ultrasonic piezo motors, SMA and planar flexure stages fail on datasheet numbers. A coarse–fine nose (C3) could halve the coil loss if a light ±1 mm fine stage can be built at the nozzle: the next thing to study.

**Autowrite works in the simulation (SIM: HW1, synthetic writers and tremor, test writers 0–5, seeds 200–203).** The hand only sweeps the pen along the line; the pen draws "return library books by friday" in the writer's own style with 2.5 mm x-height:
- no tremor: ink 29 µm rms from the target letters; the app's recogniser reads 99.2 % of the letters (the clean target letters: 100 %) and the app's reader gets every word;
- 1 mm tremor (4, 8, 12 Hz): 36 µm, 99.2 % of letters, every word; 2 mm tremor: 60 µm, 98.3 % of letters, 98 % of words;
- 3.7 letters per second at a 9.5 mm/s sweep; 3 mm letters work as well (28–36 µm up to 1 mm tremor);
- one of the six test writers (a wider style) did not fit the reach at the tuned sweep speed; slowing the sweep for that line (post hoc) fixes it. The pen knows the text, so it can choose the speed per line;
- total pen power 0.24 W without tremor and 0.31 W with 1 mm tremor: about 7–9 h of autowriting per charge; with 2 mm tremor the coil runs twice as warm as its design point (short texts only);
- every test writer fits 3.0 mm letters at the nominal sweep (CALC, planner). Rev H's ±3 mm nose cannot autowrite the test text at the tuned speed, even at 0.75 mm.

**What the pen needs besides the nose.**
- **A pen lift** (a drum at the gimbal driving the refill through a tendon loop, with a brake and a bistable latch; about 0.07 W while autowriting, CALC). Without it the letters are still read, but every pen-up move is inked and the ink error doubles (59 against 29 µm). Rev H's free refill also follows ordinary pen lifts at 50–70° of tilt, joining strokes (section 3).
- **A fast page sensor** (1 kHz, 2 ms). With the 120 Hz, 10 ms page sensor the fusion study proposed, every word is still read but the ink error more than doubles (72 against 30 µm).
- **A low, fatigue-rated ink force.** The ball's drag is the nose's largest load: 0.3 N instead of 0.15 N more than doubles the coil loss. Stock constant-force springs are rated for 2 500–25 000 cycles (MFR AMF-144): about an hour of tremor stabilisation.
- **A bigger front end**: skid-ring contact radius 10.0 mm (Rev H 6.75 mm); the refill slides 24 mm over 35–75° (Rev H 13.5 mm).

**Findings about Rev H (section 7).** Its stated force constant looks about 2.5 times too high (0.19, not 0.47 N/√W at the magnets, CALC); its 3 mm poles are narrow for their 2.3 mm stroke; its free refill joins strokes at 50–70°; its refill spring may fatigue within hours.

**Open.** Everything here is model-to-model: synthetic writers, synthetic tremor, a model recogniser, an assumed page sensor. The magnetics are an upper bound (measure Km first, EXP-N01). Autowrite with a pen lift is close to claim 1 of an active BIC patent (PAT-01): attorney review first. Whether people accept a pen that writes for them is untested (EXP-N09).

## 2. What the tip must do: travel from the tasks

The travel is the radius the ball can move relative to the handle, in the page plane. Four tasks set it (CALC on synthetic writers, `nose2/tasks.py`; tuning writers and seeds).

| Task | Travel needed (mm) | Basis | Label |
|---|---|---|---|
| tremor cancellation, 0.3 mm at the hand | 0.67 | peak of the tremor model (30 % amplitude modulation, 15 % harmonic), 4–12 Hz, tuning seeds | CALC |
| tremor cancellation, 1 mm at the hand | 2.18 | peak of the tremor model (30 % amplitude modulation, 15 % harmonic), 4–12 Hz, tuning seeds | CALC |
| tremor cancellation, 2 mm at the hand | 4.59 | peak of the tremor model (30 % amplitude modulation, 15 % harmonic), 4–12 Hz, tuning seeds | CALC |
| guided shaping, dysgraphia-like learner, 3 mm letters | 2.24 | p99 distance of the learner's letters to the copybook letters (practice-study error model) | CALC |
| autowrite, 2.5 mm x-height, no tremor | 4.07 | planner's minimum reach, worst of the 4 tuning writers, nominal sweep speed | CALC |
| autowrite, 3 mm x-height, no tremor | 4.95 | planner's minimum reach, worst of the 4 tuning writers, nominal sweep speed | CALC |
| autowrite, 3.5 mm x-height, no tremor | 5.74 | planner's minimum reach, worst of the 4 tuning writers, nominal sweep speed | CALC |
| autowrite, 4 mm x-height, no tremor | 6.52 | planner's minimum reach, worst of the 4 tuning writers, nominal sweep speed | CALC |
| delayed ink 50 ms | 2.85 | p99 of the distance between p(t) and p(t − τ) on inked samples; synthetic writers' own speed (20–34 mm/s) | CALC |
| delayed ink 50 ms at adult phrase speed | 3.81 | the same paths rescaled to a 30.5 mm/s mean (LIT CON-20) | CALC |
| delayed ink 100 ms | 4.53 | p99 of the distance between p(t) and p(t − τ) on inked samples; synthetic writers' own speed (20–34 mm/s) | CALC |
| delayed ink 100 ms at adult phrase speed | 5.26 | the same paths rescaled to a 30.5 mm/s mean (LIT CON-20) | CALC |
| delayed ink 150 ms | 5.27 | p99 of the distance between p(t) and p(t − τ) on inked samples; synthetic writers' own speed (20–34 mm/s) | CALC |
| delayed ink 150 ms at adult phrase speed | 7.73 | the same paths rescaled to a 30.5 mm/s mean (LIT CON-20) | CALC |
| delayed ink 200 ms | 6.69 | p99 of the distance between p(t) and p(t − τ) on inked samples; synthetic writers' own speed (20–34 mm/s) | CALC |
| delayed ink 200 ms at adult phrase speed | 9.15 | the same paths rescaled to a 30.5 mm/s mean (LIT CON-20) | CALC |

What this means:
- **Tremor alone** needs about 2.2 mm for 1 mm tremor and 4.6 mm for 2 mm tremor. These are the peaks of the project's tremor model at the hand (with its 30 % amplitude modulation and harmonic), an upper bound. Rev H found that, with perfect knowledge of 1–2 mm tremor, ±1.5–2 mm of travel captures most of the benefit (ink-error ratio 0.22 at ±1.5 mm and 0.18 at ±2 mm, against 0.16 at ±3 mm; SIM, `docs/opt_inertial.md` §5.3).
- **Guided letter shaping** needs 2.2 mm (p99 of a dysgraphia-like learner's error at 3 mm letters): Rev H's ±3 mm is enough.
- **Autowrite** needs 4.1 mm of reach for 2.5 mm letters (the worst tuning writer), 5.0 mm for 3 mm letters and 6.5 mm for 4 mm letters, at the nominal sweep speed. Letters have ascenders and descenders (twice the x-height), and the pen must also make the pen-up moves.
- **Sweeping faster** costs reach fast: at 1.4× the nominal speed, 2.5 mm letters need 8.4–9.7 mm, because the drawing speed is capped at 45 mm/s (ASSUMPTION) and the pen falls behind.
- **Delayed ink** (ink trailing the hand by a fixed delay) needs 4.5 mm at 100 ms and 6.7 mm at 200 ms on the synthetic writers' own speed (20–34 mm/s), and 5.3 / 9.2 mm at the adult phrase-writing speed of 30.5 mm/s (LIT CON-20). About 40–55 % of the delayed ink is laid **after** the hand has lifted for the next stroke. Delayed ink therefore needs the pen lift (section 6). People notice 50–60 ms of inking delay (LIT OPT-50), and delayed visual feedback made writers duplicate strokes and write larger (LIT OPT-51, OPT-52; abstracts only). Delayed ink is a human question first.

**Requirement set by rule R1 (`nose2/choose.py`):** autowrite of 2.5 mm letters for the worst tuning writer (4.07 mm) plus 1.0 mm kept free for tremor = 5.07 mm, rounded up to the sweep's 1 mm grid: **a guaranteed travel of 6 mm** in every direction over 35–75° of pen tilt. This also covers 3 mm letters (4.95 + 1.0 mm) and delayed ink of 100 ms at adult speed (5.3 mm). These targets are hypotheses: they rest on synthetic writers.

## 3. The front end at larger travel (DEC-034 generalised)

DEC-034 closed Rev H's front end over 35–75° of tilt: the skid ring's front outer edge is the only part of the handle on the paper, the nose swings inside its lip, and the refill slides so the ball stays on the paper. `nose2/frontend.py` re-implements `opt/inertial/front_end.py` in vectorised form (same rules, `FrontRules`, read-only) and checks it against the original: identical at 3 mm and 6 mm (difference 0.0 mm on every quantity compared; the vectorised code runs about 100 times faster).

| Nominal travel at 50° (mm) | Guaranteed travel, 35–75° (mm) | Skid-ring contact radius (mm) | Front diameter (mm) | Refill slide 35–75° (mm) | Refill slide 40–70° (mm) | Ring lip wall (mm) | Nozzle above paper (mm) |
|---|---|---|---|---|---|---|---|
| 3 | 2.75 | 6.75 | 15.0 | 13.5 | 10.5 | 1.16 | 0.80 |
| 4 | 3.62 | 7.50 | 16.5 | 16.7 | 13.0 | 1.12 | 0.88 |
| 5 | 4.48 | 8.25 | 18.0 | 20.0 | 15.7 | 1.11 | 0.99 |
| 6 | 5.31 | 9.00 | 19.5 | 23.7 | 18.5 | 1.13 | 1.12 |
| 7 | 6.13 | 9.75 | 21.0 | 27.6 | 21.5 | 1.18 | 1.27 |
| 8 | 6.91 | 10.50 | 22.5 | 31.8 | 24.6 | 1.25 | 1.45 |

CALC, pivot 45 mm behind the ball (Rev H). Other pivots (35–65 mm) change the contact radius by at most 0.5 mm and the slide by at most 2.4 mm (`results/nose2/nose2.json` → frontend.rows). The first row is Rev H (DEC-034: 6.75 mm, 13.5 mm).

What this means (CALC):
- Every extra mm of nominal travel costs about **0.75 mm of skid-ring contact radius** and **3.3–4.1 mm of refill slide**.
- The guaranteed travel (the smallest over 35–75° and every direction) is about 0.88–0.90 of the nominal travel at 50°. Autowrite can only count on the guaranteed value.
- A longer pivot distance (z_p) barely changes the ring or the slide. The ring is set by the swing of the nozzle near the paper, not by the pivot.
- For the recommended nose (guaranteed 6.0 mm, pivot 76.5 mm) the ring's contact radius is 10.0 mm (Rev H 6.75 mm), the sleeve's front is 21.5 mm across (Rev H 15 mm), and the refill slides 24.4 mm over 35–75° (19.3 mm over 40–70°; Rev H 13.5 and 10.5 mm). At 35° the ball sits 13.7 mm ahead of the ring plane. The skid ring stays C-shaped and open on the top, so the ink stays visible (DEC-034).

**Finding about architecture B's free refill (CALC, proposed AMF-152).** In Rev H the refill slides freely on a 0.15 N constant-force spring so that the ball stays on the paper. If its forward stop is set for 35°, then at a steeper tilt the refill has spare extension, and it follows an ordinary pen lift instead of leaving the paper:

| Pen tilt (°) | Spare refill extension (mm) | Pen lift the ball follows (mm) |
|---|---|---|
| 40 | 1.5 | 1.0 |
| 50 | 3.8 | 2.9 |
| 60 | 5.5 | 4.8 |
| 70 | 6.9 | 6.5 |
| 75 | 7.6 | 7.3 |

CALC for Rev H's ring (contact radius 6.75 mm), forward stop set so the ball reaches the paper at 35° with the nose centred; a deflected nose leaves even more extension.

The synthetic writers lift the pen 1.5 mm between strokes (aiguide's writer model, ASSUMPTION). So at 50–70° a freely sliding refill keeps the ball on the paper through ordinary pen lifts: strokes are joined by ink, in Rev H as well as in any larger-travel nose. This is why the Rev J nose needs a controlled refill: a **pen lift** (section 6).

## 4. Tip mechanisms: candidates, models and results

### 4.1 The candidates

| Id | Mechanism | How it was evaluated | Result |
|---|---|---|---|
| C1 | Rev H scaled: 2-axis flexure gimbal, four magnet pole pairs on a hub behind the pivot, flat coils in a soft-iron ring (radial gap) | differentiable model + optimiser | Reaches 5 mm in the 24 mm handle (0.14 W, 30 g); 6 mm needs 0.20 W, over the heat limit. In Rev H's 22 mm handle it is the only chosen-from candidate to reach 5 mm, at the heat limit (0.198 W) |
| C1+ | Same gimbal, but a 2 × 2 checkerboard of poles faces a flat two-layer coil plate **across** the pen axis (axial gap): lateral motion slides the poles along the coils | differentiable model + optimiser | Reaches only 4 mm (0.19 W): the flat plate opens the gap at the disc's rim as the nose tilts |
| C1S | As C1+, with the magnet cap and coil plate on **spheres centred on the gimbal**: the gap stays constant as the nose tilts (prior art: arc-shaped magnets centred on the tilt axis, PAT-42) | differentiable model + optimiser | **Recommended.** 6 mm at 0.18 W, 19 g (24 mm handle) |
| C2 | Two actuation planes: a front coil set around the carrier (grip zone) and a rear set on the arm; the carrier on two flexure planes, so it pivots about a virtual point | differentiable model + optimiser (optimal force split) | Reaches 5 mm (0.19 W) but weighs 38 g: two actuator sets for one set of force |
| C3 | Coarse–fine: C1S as the coarse stage plus a ±1 mm fine stage at the carrier front for tremor | model; fine stage with assumed values | 6 mm at 0.09 W, 20 g, but only with an assumed fine stage (0.25 g, 0.05 N/√W): reported, not chosen; the best refinement to study next |
| C4a | Translating carrier on four superelastic nitinol wires, no lever, axial-gap actuator | differentiable model + optimiser | No feasible design: without a lever the magnets move the full travel, and the coil legs cannot stay over the poles |
| C4b | Galvanometer (rotary moving-magnet) scanner per axis | datasheet screening (MFR AMF-137) | Rejected: 13–18 g each, Ø12.7 mm bodies do not fit side by side; 0.032 N/√W at the tip (CALC from the datasheet torque constant), about 7 W for the autowrite force |
| C4c | Ultrasonic piezo motors | datasheet screening (MFR AMF-138) | Rejected: 5 W driver per axis, 120 Vpp, self-locking (cannot yield to the writer) |
| C4d | Shape-memory wire | datasheet (MFR AMF-77) | Reference only: cooling 0.15 s, about 3 Hz, below the 4–12 Hz tremor band |
| C4e | Planar parallel flexure stage | literature scale (LIT AMF-135) | Rejected: 10 × 10 mm range needs a 255 mm flexure bearing |
| C5 | Axial DOF (pen lift) | force, flux and coil-loss calculation | Needed: section 6 |

### 4.2 Magnetics: the gap flux, and Rev H recalibrated

Rev H's actuator model (`opt/inertial/adjoint.py`) takes the gap flux as 0.55 × B_r t_m / (t_m + gap + coil) (the 0.55 is an ASSUMPTION). This study computed the flux with magpylib's exact cuboid magnets and the soft iron as infinitely permeable planes (method of images, three periods; image convention checked to 4 × 10⁻¹⁶ T). That is an upper bound: real iron is finite and saturates.

- The fitted flux factor ("eta", 11 terms, log-quadratic) matches magpylib within **6.6 % rms** (95th percentile 14 %, worst 27 %) over 720 radial-gap geometries and within **5.9 % rms** (13 %, 22 %) over 240 axial-gap geometries (CALC). The optimiser uses this fit (differentiable).
- **Rev H's force constant is probably 2.5 times lower than stated.** With Rev H's own geometry (3.0 × 6.5 × 2.8 mm N45 magnets, 1.43 mm coils, 2.77 mm gap), the lumped formula gives 0.29 T in the gap and 0.46 N/√W at the magnets (Rev H states 0.47). The image calculation gives **0.12 T and 0.19 N/√W** (0.14 N/√W at the tip, against 0.355 stated) (CALC). The reason: the gap plus coil (4.2 mm) is larger than the magnet's width (3 mm), so most of the flux closes sideways. Consequences for Rev H: REQ-RVH-003 (≥ 0.40 N/√W) would fail; the coil loss while writing rises about 6.4-fold, from 0.004 W to about 0.027 W, and the total from 0.081 W to about 0.10 W, at the REQ-RVH-004 limit (CALC). EXP-I05 should measure Km first.
- **Rev H's poles are narrow for its stroke.** This study's actuator rule keeps each active coil leg over its pole over the whole stroke (active leg width = pole width − 2 × stroke ≥ 0.6 mm). Rev H's 3 mm poles move 2.3 mm at its usable travel (2.6 mm at the stop), so the rule cannot hold: either the coils are wider than the poles (then Km is lower still) or the force changes strongly along the stroke (CALC). EXP-I05 should map force against position, not only at the centre.

### 4.3 Optimisation

- **Model** (`nose2/designs.py`, PyTorch): tip travel (nominal and guaranteed, from the front-end fit), force per √W at the tip, tip-equivalent moving mass, suspension stiffness, first parasitic mode (arm and carrier bending), peak force within the 3.7 V / 1.5 A drive (Rev H assumption), coil loss for two duties, coil temperature (100 K/W, ASSUMPTION), flexure strain and buckling, actuator envelope, length, reaction on the hand, added mass.
- **The refill has to fit.** The 67 mm D1 refill reaches back to 67 mm plus its backward slide plus a 6 mm holder (about 79–80 mm from the tip at 6 mm of travel). If that lies behind the magnet cap's front face, the refill runs in a thin titanium channel (4.0/3.4 mm) through a central hole in the cap and the coil plate (the pole units move outward by the hole, which must also clear the channel's swing), and the channel's end swings in the handle bore. The pen-lift and ink-force module (2 g) sits within 5 mm of the gimbal; the refill holder and its pulley (0.5 g) at the refill's end. All of this is in the moving mass (ASSUMPTION values).
- **Duties**: (a) stabilising 1 mm rms tremor at 8 Hz; (b) autowriting 3 mm letters (the planner's nose motion: 1.35 mm rms per axis, 4.7 m/s² at the 99.9th percentile, inking 64 % of the time) with 1 mm tremor on top. The effective accelerations (10.6 m/s² for the tremor duty, 4.5 m/s² for autowrite) were calibrated on HW1 runs (tuning writer 100, seed 300): they include the servo's high-frequency force from ball-friction reversals. The ball drag is μ 0.15 × 0.196 N while inking (ASSUMPTION within LIT CON-13).
- **Real parts**: magnet grade (N42SH, N48SH, N52; MFR AMF-28, AMF-139), flexure alloy and shim thickness (301 full hard, 17-7PH, Ti-6Al-4V, C17200, superelastic NiTi; AMF-19–21, AMF-141–142), magnet wire (0.08–0.20 mm), back iron (1010 or Hiperco 50A, AMF-140).
- **Constraints** (a design is feasible only if all hold): guaranteed travel; fits the handle bore (22 or 24 mm handle, 1 mm wall), including the refill channel's swing; parasitic modes ≥ 3 × the 80 Hz servo; peak force; flexure strain within fatigue (÷ 1.5) and static limits; flexure strips ≥ 50 µm thick and not buckling under 3 × the 0.15 N refill force (ASSUMPTIONS for handling and shock); **coil temperature rise ≤ 20 K** while autowriting with tremor (about 0.2 W at 100 K/W, ASSUMPTION; meant to keep the grip at or below 41 °C, LIT AMF-34; EXP-N04 checks both); actuator within 100 mm of the tip.
- **Search**: CMA-ES (own implementation) over the continuous variables and the part choices, then an **adjoint (reverse-mode) L-BFGS polish** of the continuous variables. The gradients match central differences (worst relative error 8.5 × 10⁻⁸). Objective: autowrite coil loss + μ × added mass (μ = 1 and 4 W/kg). Swept over the required travel (4–8 mm), both handles, 3 seeds for the four main candidates (1 for C3 and C4a): 280 optimisations, 24 599 feasible designs kept for the Pareto fronts (travel, force per √W, added mass, power).

**Results (CALC).** The best design of each candidate in the 24 mm handle, at the required 6 mm or, where that is not feasible, at its largest feasible travel (the μ = 4 W/kg runs; `results/nose2/nose2.json` → main_table):

| Mechanism | Status | Guaranteed travel (mm) | Force per √W at the tip (N/√W) | Moving mass at the tip (g) | Added mass (g) | Coil loss, autowrite + 1 mm tremor (W) | Coil loss, 1 mm tremor only (W) | Coil rise (K) | Peak tip force (N) | Reaction on the hand, rms (N) | Bandwidth the modes allow (Hz) | Actuator radius (mm) | Ring contact radius (mm) | Refill slide (mm) | Pivot (mm) | Magnet stroke (mm) | Gap (mm) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Rev H nose (±3 mm nominal) | 3 mm nominal travel | 2.75 | 0.140 | 2.97 | – | 0.176 | 0.145 | 18 | 0.33 | 0.042 | – | 10.0 | 6.75 | 13.5 | 45 | 2.27 | 2.77 |
| **C1S spherical-gap gimbal (recommended)** | feasible at 6 mm | 6.00 | 0.099 | 2.10 | 19.3 | 0.182 | 0.164 | 18 | 0.23 | 0.030 | 263 | 11.0 | 9.87 | 24.5 | 76 | 1.05 | 0.77 |
| C1 radial-gap gimbal (Rev H type) | not feasible at 6 mm; largest feasible travel 5 mm | 5.00 | 0.115 | 2.23 | 29.9 | 0.143 | 0.128 | 14 | 0.27 | 0.031 | 304 | 11.0 | 8.89 | 20.9 | 70 | 0.94 | 2.11 |
| C1+ flat axial-gap gimbal | not feasible at 6 mm; largest feasible travel 4 mm | 4.00 | 0.098 | 2.16 | 16.3 | 0.188 | 0.168 | 19 | 0.23 | 0.030 | 286 | 11.0 | 8.00 | 17.2 | 73 | 0.94 | 1.37 |
| C2 two actuation planes | not feasible at 6 mm; largest feasible travel 5 mm | 5.00 | 0.104 | 2.19 | 37.9 | 0.185 | 0.165 | 18 | 0.25 | 0.032 | 200 | 11.0 | 8.71 | 22.2 | 50 | 1.23 | 2.34 |
| C3 coarse-fine | feasible at 6 mm | 6.00 | 0.097 | 2.11 | 20.0 | 0.088 | 0.006 | 9 | 0.23 | 0.030 | 268 | 11.0 | 10.86 | 24.5 | 76 | 1.15 | 0.79 |
| C4a translating carrier on wires | no feasible design at 4-8 mm in the 24 mm handle | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |

The design model uses a smooth fit of the front-end closure (contact radius 9.87 mm for C1S); the layout sizes the ring in 0.25 mm steps (10.0 mm). Rev H's row uses its own stated moving mass (2.97 g) and suspension (12.35 N/m) under this study's duties, with the force constant recalibrated by the image method (0.140 N/√W at the tip); with its stated 0.355 N/√W the same duties would cost 0.023 W (tremor only) and 0.027 W (autowrite). The duties here are harsher than Rev H's test-grid average (1 mm rms per axis at 8 Hz, continuous, with the ball inking 64 % of the time).

What the optimisation shows:
- **Only the spherical-gap gimbal (C1S) reaches 6 mm within the heat limit** in a 24 mm handle: 0.182 W while autowriting with 1 mm tremor (18.2 K coil rise), 19.3 g added. In the 22 mm handle (Rev H's) only C1 (and C3) reach 5 mm, C1 at the heat limit (0.198 W); C1S reaches 4 mm there, because its pole disc must fit a 10 mm bore radius.
- **Rev H's layout scaled up (C1)** stops at 5 mm (0.143 W, 29.9 g): its gap must clear the other axis's stroke, so it grows with the travel, and each pole pair needs a hub face. At 6 mm it needs 0.204 W (over the 0.2 W limit).
- **A flat axial gap (C1+)** stops at 4 mm: the flat plate opens the gap at the disc's rim as the nose tilts.
- **Two actuation planes (C2)** stop at 5 mm and weigh about twice as much (37.9 g): two actuator sets for one set of force.
- **Coarse–fine (C3)** reaches 6 mm with half the coil loss (0.088 W), because a light fine stage takes the tremor. Its fine stage is not designed: the model assumes 0.25 g moving and 0.05 N/√W at the tip. It is reported, not chosen (rule R2). It is the most promising refinement for round 2 if such a stage fits at the nozzle.
- **A translating carrier (C4a)** has no lever: its magnets move the full 6 mm, and a 2 × 2 checkerboard cannot keep its coil legs over the poles over that stroke (poles ≥ 2 × stroke + 0.6 mm wide would not fit the bore). No feasible design.
- **Galvanometers, piezo motors, SMA and planar flexure stages** fail on datasheet numbers (section 4.1): the galvo pair gives 0.032 N/√W at the tip and weighs 36 g.
- **Force per √W falls with travel for every candidate**: the price of travel is either a larger gap (radial), a smaller active coil (the legs must stay over the poles over a longer stroke), or a longer lever.
- The per-candidate Pareto fronts (travel, force per √W, added mass, power) hold 2 587 non-dominated designs out of the 24 599 feasible ones kept (every second feasible evaluation; `fig_nose2_pareto.png`). Every run's best design was re-evaluated with the final model code (largest change in coil loss 0.000 W).

### 4.4 The recommended mechanism

Rule R1–R4 (`nose2/choose.py`) picks **C1S, the short-arm gimbal with a spherical-gap actuator, in a 24 mm handle, at a guaranteed 6 mm** (lowest J; the other two rule variants pick the same design). PROPOSED DESIGN; every number CALC unless marked.

| Part | Value |
|---|---|
| Gimbal | 2-axis cross-strip flexure 76.5 mm behind the ball: 301 full-hard steel, 50 µm strips, 2.55 mm wide, 3.80 mm long (AMF-20). Bending stiffness 0.0028 N·m/rad (0.48 N/m at the tip). Strain 0.0011 at the usable travel (fatigue allowable 0.0018); buckling load 14.5 N per strip (needed 0.45 N) |
| Arm | 11.5 mm from the gimbal to the magnet face; the ball moves 6.6 × as far as the magnets |
| Magnets | 2 × 2 checkerboard of N52 poles, 6.3 × 6.3 × 3.3 mm (AMF-139), on a spherical Hiperco 50A cap (AMF-140) |
| Coils | two layers (x and y), 0.55 mm thick in all, 0.20 mm wire, on a concentric spherical soft-iron plate |
| Gap | 0.77 mm (0.5 mm clearance + half the coil), constant at every tilt; gap flux 0.75 T (image method, upper bound) |
| Magnet stroke | 1.05 mm at the stop |
| Force constant | 0.66 N/√W per axis at the magnets, **0.099 N/√W at the tip** |
| Peak tip force | 0.23 N at 3.7 V / 1.5 A (the duty needs 0.058 N) |
| Moving mass at the tip | **2.10 g** (magnets and cap 9.8 g; titanium carrier 7/6 mm, refill, nozzle, arm, pen lift) |
| Coil loss | **0.182 W** autowriting 3 mm letters with 1 mm rms tremor; 0.164 W stabilising 1 mm rms tremor only (design duties; the SIM values are in section 5) |
| Coil rise | 18.2 K at 100 K/W (limit 20 K) |
| First parasitic mode | 788 Hz (carrier bending): servo bandwidth up to 263 Hz; 80 Hz used |
| Reaction on the hand | 0.030 N rms per axis while autowriting |
| Actuator radius | 11.0 mm (the 24 mm handle's bore radius is 11 mm: 1 mm wall) |
| Added mass | 19.3 g (moving 9.8 g, coils and plate 8.7 g, flexure) |
| Refill | D1 refill slides 24.4 mm over 35–75° and the travel; its holder reaches back to 79.9 mm, 2.4 mm in front of the magnet cap, so no hole is needed |
| Front end | skid-ring contact radius 10.0 mm (ring Ø20.0 mm); sleeve front Ø21.5 mm outside, Ø18.8 mm bore; ball 7.9 mm ahead of the ring plane at 50°, 13.7 mm at 35° |
| Pen | Ø24 × 175 mm, 83.5 g (nose 18.2 g, handle 65.3 g; +10 % wiring, CALC); centre of mass 102 mm from the tip |
| Fit checks | all pass (`results/nose2/layout.json` → fit_checks): carrier clears the front opening by 0.50 mm; ring lip 0.26 mm above its 1.0 mm minimum; nozzle 0.71 mm above the 0.3 mm paper clearance; sleeve front 0.25 mm above the paper at 35°; carrier 0.09 mm clear at the stop; coil plate 0.005 mm inside the bore (the optimiser uses the whole bore); 2.3 mm of length left in 175 mm; refill holder 2.4 mm in front of the magnet cap |

Why it works (CALC):
- **Travel is an angle.** The ball moves 6.5 mm (nominal) at 76.5 mm from the gimbal: 4.9° of tilt. Magnets 11.5 mm behind the gimbal then move only 1.05 mm.
- **The gap does not grow with the travel.** On spheres centred on the gimbal, the magnet cap slides over the coil plate at a constant 0.77 mm. In Rev H's radial layout the gap must clear the other axis's stroke.
- **Short stroke, strong flux.** A 0.77 mm gap over 3.3 mm magnets gives about 0.75 T in the coils; the active coil legs (6.3 − 2 × 1.05 mm wide) stay over their poles over the whole stroke.
- **The lever costs force but saves mass.** The tip force is the magnet force ÷ 6.6; but the magnets' inertia at the tip also falls by 6.6² ≈ 44, so the heavy actuator hardly moves the tip mass.
- **The magnets sit behind the refill.** With the gimbal at 76.5 mm and the magnet cap starting at 82.3 mm, the 67 mm refill and its holder (rearmost 79.9 mm) stay in front of the magnets at every tilt and travel, so the actuator needs no central hole. (The optimiser found this itself. Passing the refill through the cap needs a central hole: with the same poles the disc would grow to about 14–15 mm radius, beyond the 11 mm bore radius (CALC: the recommended design with the gimbal moved forward to 60–74 mm).)

Drawings: `results/nose2/drawing_nose2.png` (side view, sections, component table in `drawing_nose2.csv`), `results/nose2/fig_nose2_front_end.png` (the nose at rest and at ± travel at 35/50/75°), `results/nose2/nose2_assembly.step` (CadQuery), `results/nose2/layout.json` (Rev H schema, for the 3-D explainer).

## 5. Autowrite in HW1: can the pen write letters by itself?

### 5.1 How autowrite works in the simulation

The scene (SIM, model HW1 in `handwriting/`, used read-only; wrapper `nose2/autowrite.py`):
- The writer holds the pen with the skid ring on the paper. The hand only sweeps the pen along the line at a steady speed. Tremor may be added (the project's tremor model: 0.3, 1 or 2 mm at 4, 8 or 12 Hz).
- The pen knows the text in advance ("return library books by friday", the sentence of the earlier handwriting studies). A synthetic writer from `aiguide` sets the style: size, slant, letter shapes.
- The hand model is HW1's (HAP-26 impedance). It does not compensate the pen's drag (ASSUMPTION; a sensitivity case lets it).

What the pen does (all causal; every 0.5 ms tick):
1. **Plan the line before it is written** (`nose2/planner.py`, CALC). The text becomes one path: strokes plus pen-up moves. Dynamic programming picks *when* each point is drawn so that it stays within the reach of the sweeping hand. Drawing speed stays between 4 and 45 mm/s; pen-up moves up to 90 mm/s (ASSUMPTIONS). Each stroke starts and ends with a short dwell (15 ms and 10 ms), as the writers do, so dots leave ink.
2. **Know where the handle is.** A complementary estimator joins the page sensor (1 kHz, 2 ms latency, 3 µm noise: the fusion study's model, ASSUMPTION) and the IMU (LSM6DSV16X model). It predicts the handle one servo delay ahead.
3. **Follow the user.** The plan's clock is the hand's position along the line, filtered. If the hand slows, the pen waits. It never pulls the hand forward (HAP-62).
4. **Draw.** Nose command = planned ink point − predicted handle position. HW1's servo (80 Hz, travel, force and slew limits of the design) moves the ball.
5. **Lift and lower the ball** along the plan's pen-down flags, with an 8 ms switching delay (ASSUMPTION; the pen commands one delay ahead). Without the axial DOF, the ball stays on the paper for the whole line and the pen-up moves are inked.

The handle motion depends a little on the nose (reaction and ball drag), so each case runs as a fixed point: the causal command is recomputed from the previous run's sensor streams until it changes by less than 5 µm rms (at most 6 passes).

Metrics per case: ink error to the target letters (µm rms, HW1's letter metric); letters read by the app's recogniser (HW1 `recognizer_for`); words read after the app's reader; the same recogniser on the clean target letters (**the ceiling**: some synthetic letter shapes are misread even when drawn perfectly); letters per second; coil loss; force; time at the travel limit; handle deviation.

### 5.2 Settings chosen on tuning data

The rules T1–T5 (`nose2/tuning.py`) were written before any test run and applied mechanically on the tuning writers 100–103 and seeds 300–301: no tremor and 1 mm tremor at 4, 8 and 12 Hz, 2.5 mm letters, the recommended nose (32 cases per setting; SIM).

| Rule | What was tried (mean over the tuning cases) | Chosen |
|---|---|---|
| T1 handle observer bandwidth | 10 Hz: ink error 79 µm; 25 Hz: 45 µm; 50 Hz: 36 µm; 100 Hz: 33 µm | 100 Hz |
| T2 progress filter | 0.4 Hz: 32 µm; 0.8 Hz: 33 µm; 1.6 Hz: 36 µm | 0.4 Hz |
| T3 extra prediction lead | 0 ms: 32 µm; 1 ms: 56 µm; 2 ms: 87 µm | 0 ms |
| T4 reach kept free for tremor | 0.5, 1.0 and 1.5 mm: at the travel limit ≤ 0.13 % of the time in every 1 mm tremor case, no failed plan | 0.5 mm (the smallest that meets the rule) |
| T5 sweep speed | 0.8 ×: 31 µm, letters 97.1 % (ceiling 97.1 %); 1.0 ×: 32 µm, 97.0 %; 1.25 ×: 34 µm, 97.2 %; no failed plan | 1.25 × (the fastest that meets the rule) |

Frozen settings: plan reach 5.5 mm (6.0 mm − 0.5 mm), observer 100 Hz, progress filter 0.4 Hz, no extra lead, sweep 1.25 × the line speed (planner, `line_speed`: the hand speed at which drawing at up to 45 mm/s takes 80 % of the time). A 1 ms step of extra lead makes the ink worse because the servo delay is already predicted.

### 5.3 Results on the test writers and seeds

**Frozen rules, test writers 0–5, seeds 200–203** (SIM; means over the cases whose plan fitted; tremor rows are means over 4, 8 and 12 Hz; total power = coil loss + 0.077 W electronics (ASSUMPTION, Rev H) + 0.071 W pen lift (CALC); battery = 2.22 Wh (MFR AMF-80) ÷ total power):

| Pen | x-height (mm) | Tremor (mm, mean of 4/8/12 Hz) | Ink error (µm rms) | Letters read (%) | Ceiling (%) | Worst writer, letters (%) | Words read by the app (%) | Letters per s | Coil loss (W) | Total power (W) | Battery (h) | Time at travel limit (%) | Plan failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Rev H nose (±3 mm) | 0.75 | 0 | – | – | – | – | – | – | – | – | – | – | 24 of 24 |
| Rev H nose (±3 mm) | 0.75 | 0.3 | – | – | – | – | – | – | – | – | – | – | 72 of 72 |
| Rev H nose (±3 mm) | 0.75 | 1 | – | – | – | – | – | – | – | – | – | – | 72 of 72 |
| Rev H nose (±3 mm) | 0.75 | 2 | – | – | – | – | – | – | – | – | – | – | 72 of 72 |
| Rev J nose, pen lift | 2.5 | 0 | 29 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.089 | 0.237 | 9.4 | 0.00 | 4 of 24 |
| Rev J nose, pen lift | 2.5 | 0.3 | 30 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.096 | 0.244 | 9.1 | 0.01 | 12 of 72 |
| Rev J nose, pen lift | 2.5 | 1 | 36 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.166 | 0.314 | 7.1 | 0.14 | 12 of 72 |
| Rev J nose, pen lift | 2.5 | 2 | 60 | 98.3 | 100.0 | 96.2 | 98 | 3.66 | 0.376 | 0.523 | 4.2 | 1.51 | 12 of 72 |
| Rev J nose, pen lift | 3 | 0 | 28 | 99.2 | 100.0 | 96.2 | 100 | 3.08 | 0.088 | 0.236 | 9.4 | 0.00 | 4 of 24 |
| Rev J nose, pen lift | 3 | 0.3 | 29 | 99.2 | 100.0 | 96.2 | 100 | 3.08 | 0.095 | 0.243 | 9.1 | 0.05 | 12 of 72 |
| Rev J nose, pen lift | 3 | 1 | 36 | 99.4 | 100.0 | 96.8 | 100 | 3.08 | 0.164 | 0.312 | 7.1 | 0.38 | 12 of 72 |
| Rev J nose, pen lift | 3 | 2 | 67 | 98.6 | 100.0 | 95.8 | 99 | 3.08 | 0.370 | 0.518 | 4.3 | 2.24 | 12 of 72 |
| Rev J nose, no pen lift | 2.5 | 0 | 59 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.119 | 0.196 | 11.3 | 0.00 | 4 of 24 |
| Rev J nose, no pen lift | 2.5 | 0.3 | 59 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.125 | 0.202 | 11.0 | 0.01 | 12 of 72 |
| Rev J nose, no pen lift | 2.5 | 1 | 63 | 99.2 | 100.0 | 96.2 | 100 | 3.66 | 0.193 | 0.270 | 8.2 | 0.15 | 12 of 72 |
| Rev J nose, no pen lift | 2.5 | 2 | 80 | 98.0 | 100.0 | 94.5 | 98 | 3.66 | 0.390 | 0.467 | 4.8 | 1.48 | 12 of 72 |

By tremor frequency (Rev J nose with pen lift, 2.5 mm letters):

| Tremor (mm) | Frequency (Hz) | Ink error (µm rms) | Letters read (%) | Words read by the app (%) | Coil loss (W) | Time at travel limit (%) |
|---|---|---|---|---|---|---|
| 0 | – | 29 | 99.2 | 100 | 0.089 | 0.00 |
| 0.3 | 4 | 29 | 99.2 | 100 | 0.095 | 0.00 |
| 0.3 | 8 | 30 | 99.2 | 100 | 0.096 | 0.00 |
| 0.3 | 12 | 31 | 99.2 | 100 | 0.097 | 0.02 |
| 1 | 4 | 31 | 99.2 | 100 | 0.159 | 0.07 |
| 1 | 8 | 33 | 99.2 | 100 | 0.163 | 0.09 |
| 1 | 12 | 45 | 99.2 | 100 | 0.176 | 0.27 |
| 2 | 4 | 37 | 98.7 | 99 | 0.348 | 0.60 |
| 2 | 8 | 53 | 99.2 | 99 | 0.366 | 0.79 |
| 2 | 12 | 92 | 97.1 | 97 | 0.412 | 3.15 |

What this means:
- **The pen writes the sentence legibly while the hand only sweeps.** At 2.5 mm x-height the app's recogniser reads 99.2 % of the letters (the clean target letters: 100 %) and the app's reader gets every word, with no tremor and with 0.3 or 1 mm of tremor. The ink stays within 29–36 µm rms of the target letters. With 2 mm tremor: 60 µm, 98.3 % of letters, 98 % of words.
- **Speed:** 3.7 letters per second at a 9.5 mm/s sweep (2.5 mm letters), 3.1 letters/s at 3 mm.
- **One test writer's line did not fit at the tuned speed.** Writer 4 needs 6.3 mm of reach at 1.25 × (CALC, planner); the plan reach is 5.5 mm. So 4 of 24 (no tremor) and 12 of 72 (per tremor amplitude) cases had no plan. The four tuning writers all fitted at 1.25 ×: the rule T5 was too optimistic for a wider style. These cases count as failures of the frozen rules.
- **Post hoc** (not a frozen rule; `nose2/evaluate.fallback`): if the pen slows the sweep to 1.0 × for that line, writer 4's text fits and is read like its target (ink 27 / 28 / 33 / 56 µm at 0 / 0.3 / 1 / 2 mm tremor; with up to 1 mm tremor letters 96.2 %, its own ceiling 96.2 %, words 100 %; with 2 mm, 93.6 % and 97 %; 2.8 letters/s). The pen knows the text, so it can choose the sweep speed per line and cue the user: proposed as a firmware rule, to be tested on new writers.
- **The weakest writer** (writer 0) loses one letter in every condition ("return" is read "refurn"): 96.2 % against its ceiling of 100 %; the app's reader still gets the word.
- **Without the pen lift** the letters and words are read just as well, but the ink error doubles (59 µm without tremor) because every pen-up move is inked: the words are joined by lines (`fig_nose2_autowrite_example.png`).
- **Tremor costs power, not legibility.** Coil loss 0.09 W without tremor, 0.17 W with 1 mm and 0.38 W with 2 mm (the design point was 0.18 W for 1 mm rms per axis). Severe tremor at 12 Hz is the hardest case: 92 µm, 97 % of letters, 3 % of the time at the travel limit.
- **Heat:** 0.38 W is about twice the 20 K design point. Autowrite with 2 mm tremor is for short texts (a line takes about 7 s); the coil's thermal time constant is unknown (EXP-N04).
- **Rev H cannot autowrite this text.** Its plan reach is 2.5 mm; at the tuned speed not even 0.75 mm letters fit. Post hoc, at 0.8–1.0 × it writes 0.75 mm letters (ink 34 µm, letters 98 % without tremor) but not with 2 mm tremor (letters 64 %). Part of this is the speed rule: the planner's line speed counts the drawing time but not the 25 ms dwells at the ends of each stroke, which add about 55 % to the drawing time of 0.75 mm letters and 16 % at 2.5 mm (CALC, writer 0), so 1.25 × is relatively faster for small letters. A line speed that includes the dwells is a simple fix for the firmware.
- The closed loop converged: the causal command changed by 2–3 µm rms between the last two passes (3–5 passes per case).

`fig_nose2_autowrite_grid.png` shows ink error, letters read and coil loss against tremor; `fig_nose2_autowrite_example.png` shows the hand's path and the ink for test writer 0, seed 200, 1 mm tremor at 8 Hz.

### 5.4 How large and how fast

| Pen or reach | Plan reach (mm) | Largest x-height every test writer fits (mm) | Fastest sweep at 2.5 mm (× nominal) | Letters per s at that speed |
|---|---|---|---|---|
| Rev J nose (plan reach = travel − margin) | 5.50 | 3 | 1 | 2.97 |
| Rev H nose | 2.50 | 0 | 0 | 0.00 |
| reach 2.0 mm | 2.00 | 0 | 0 | 0.00 |
| reach 3.0 mm | 3.00 | 1 | 0 | 0.00 |
| reach 4.0 mm | 4.00 | 2 | 0.8 | 2.41 |
| reach 5.0 mm | 5.00 | 2.5 | 1 | 2.98 |
| reach 6.0 mm | 6.00 | 3.5 | 1 | 2.97 |
| reach 7.0 mm | 7.00 | 4 | 1.25 | 3.61 |

CALC (planner feasibility on the six test writers, seed 200; `fig_nose2_size_speed.png`). What the reach buys:
- With the tuned 0.5 mm margin the Rev J nose plans within 5.5 mm: **every test writer fits 3.0 mm letters** at the nominal sweep, and 2.5 mm letters at up to 1.0 × (3.0 letters/s). The tuned 1.25 × fits five of the six writers (section 5.3).
- Each extra millimetre of reach adds about 0.5–1 mm of x-height: 3 mm of reach → 1.0 mm letters; 4 → 2.0; 5 → 2.5; 6 → 3.5; 7 → 4.0 mm.
- Rev H's 2.5 mm plan reach fits no size for every test writer (writer 4 needs 2.6 mm even at 1 mm letters).
- 4 mm letters for every writer would need about 7 mm of plan reach (7.5 mm guaranteed travel): no candidate fits the 24 mm handle within the heat limit at 7 mm or more (section 4.3).

### 5.5 What matters (one factor at a time)

One factor at a time on the recommended nose (SIM; test writers 0–5, seed 200; no tremor, and 1 mm tremor at 4 and 8 Hz; 2.5 mm letters; writer 4's three cases have no plan at the tuned speed in every variant):

| Variant (one factor changed) | Ink error (µm rms) | Letters read (%) | Words read by the app (%) | Coil loss (W) | Time at travel limit (%) | Failed plans |
|---|---|---|---|---|---|---|
| nominal | 30 | 99.2 | 100 | 0.136 | 0.04 | 3 of 18 |
| page sensor 120 Hz, 10 ms (fusion page_120) | 72 | 99.2 | 100 | 0.145 | 0.04 | 3 of 18 |
| hand compensates the drags (writer_comp drag) | 30 | 99.2 | 100 | 0.135 | 0.03 | 3 of 18 |
| servo 40 Hz | 44 | 99.2 | 100 | 0.091 | 0.04 | 3 of 18 |
| gel ink, mu 0.095 (LIT CON-13) | 30 | 99.2 | 100 | 0.097 | 0.04 | 3 of 18 |
| refill force 0.3 N | 30 | 99.2 | 100 | 0.330 | 0.05 | 3 of 18 |
| axial switching delay 20 ms | 31 | 99.2 | 100 | 0.138 | 0.04 | 3 of 18 |
| no axial DOF (ball down for the whole line) | 59 | 99.2 | 100 | 0.165 | 0.04 | 3 of 18 |
| uneven sweep: speed +-30 % at 0.5 Hz | 31 | 99.2 | 100 | 0.137 | 0.07 | 3 of 18 |
| hand drifts +-1 mm across the line at 0.2 Hz | 30 | 99.2 | 100 | 0.137 | 0.03 | 3 of 18 |

What this means:
- **A 120 Hz page sensor** (the fusion study's proposed minimum: 120 Hz, 10 ms) still reads every word, but the ink error more than doubles (72 µm against 30 µm). A 1 kHz, 2 ms page sensor is worth having for autowrite.
- **A 40 Hz servo** raises the ink error to 44 µm; the letters are still read.
- **The ink force drives the power.** Doubling the refill force to 0.3 N raises the coil loss 2.4-fold (0.33 W), because the ball's drag is the largest force the nose makes. A gel ink (μ 0.095 instead of 0.15, LIT CON-13) cuts it by 29 %. Keep the ink force low (REQ-RVJ-N05).
- **User behaviour is tolerated**: a sweep whose speed varies ±30 % at 0.5 Hz, or a hand drifting ±1 mm across the line, leaves the ink error at 30–31 µm (the pen follows the measured hand).
- **A slower pen lift** (20 ms instead of 8 ms) changes nothing that the recogniser sees (31 µm).
- A hand that compensates the drags (HW1 `writer_comp` "drag") changes nothing.

## 6. The pen lift (axial degree of freedom)

Why the pen needs it:
- A freely sliding refill follows ordinary pen lifts at 50–70° (section 3): strokes get joined.
- Without it, autowrite inks every pen-up move. The recogniser still reads most letters, but the ink error doubles or more (section 5.3), and dots join their stems.
- Delayed ink lays 40–55 % of its ink after the hand has lifted (section 2).

Proposed mechanism (PROPOSED DESIGN, CALC `nose2/designs.axial_dof`; inputs ASSUMPTION unless noted):
- The ink force (0.15 N) comes from a small drum just in front of the gimbal. A closed tendon loop (a capstan drive) runs from the drum forward beside the refill, over a small pulley, to the refill holder and back, so the drum moves the holder either way wherever it has slid. A fatigue-rated spiral spring in the drum sets the ink force (it replaces Rev H's constant-force strip).
- For a pen-up, an **electro-permanent brake** locks the drum and a **bistable reluctance latch** turns it by a small angle, pulling the refill back 0.5 mm (CalComp's plotter pen lift moved 0.5–0.64 mm at 40–50 lifts per second, LIT PAT-41). Neither needs power to hold. For a pen-down, both release.
- The module weighs about 2 g but sits within 5 mm of the gimbal, so it adds about 0.01 g at the tip (the design model includes it). A brake that clamped the refill itself would have to sit where the refill always is, about 30 mm in front of the gimbal: there the same 2 g would add 0.3 g at the tip and raise the coil loss about 30 %, over the heat limit (CALC).
- The pulleys and the tendon's routing are not designed yet (ASSUMPTION).

| Quantity | Value | Label |
|---|---|---|
| Lift stroke | 0.5 mm | ASSUMPTION (LIT PAT-41: 0.5–0.64 mm) |
| Switching time | 5 ms (8 ms command-to-contact in the SIM) | ASSUMPTION |
| Moving mass (refill + holder) | 1.2 g | ASSUMPTION (refill 0.84 g) |
| Force to lift (spring 0.15 N + acceleration) | 0.25 N | CALC |
| Flux density at the pole (Ø3 mm, gap 0.6 mm) | 0.30 T | CALC |
| Ampere-turns | 141 A·t | CALC |
| Coil loss during a pulse (1.5 × 4 mm window) | 1.5 W | CALC |
| Energy per lift cycle (lift, release, brake on and off at 3 mJ each) | 17 mJ | CALC (brake energy ASSUMPTION) |
| Pen lifts per second while autowriting | 4.2 (4.4 worst tuning writer) | CALC (planner, tuning writers, 3 mm letters) |
| **Average pen-lift power while autowriting** | **0.07 W** | CALC |
| Holding power (up or down) | 0 | design choice (bistable latch, electro-permanent brake) |
| Mass | about 2 g, within 5 mm of the gimbal (about 0.01 g at the tip) | ASSUMPTION |

The pen lift is a quarter to a third of the autowrite power (0.071 of 0.24–0.31 W). A larger pole, a longer switching time or a lighter brake would lower it; EXP-N05 measures it. In normal writing (stabiliser on, the writer lifts the pen), the pen lift works the other way round: when the refill-slide sensor (Rev H's 1 mm target magnet, AMF-72) sees the refill start to follow a lift, the brake locks it, so the ball leaves the paper with the pen. The brake alone does this (about 6 mJ per stroke, ASSUMPTION).

**Refill spring fatigue (finding for Rev H too).** The refill slide changes with every correction of the nose: about 0.65 mm of slide per mm of ball travel in the tilt plane at 50°, almost none sideways (CALC, `nose2/frontend.poses`). Stock constant-force springs are rated for 2 500–25 000 cycles (MFR AMF-144). Stabilising 8 Hz tremor is about 29 000 cycles per hour, and autowrite about 15 000–36 000 (CALC: 4–10 slide reversals per second). A strip that winds on a drum bends and unbends the same short section on every small cycle, so the rated life is the relevant order of magnitude (ASSUMPTION; the maker rates full strokes). The refill force element should be a fatigue-rated part: the spiral spring of the drum above (designed below its endurance limit), a long soft helical spring, or a magnetic spring (EXP-N06).

## 7. Findings about Rev H for the lead

1. **Force constant** (section 4.2): the image calculation gives 0.19 N/√W at the magnets, not 0.47. REQ-RVH-003 would fail and REQ-RVH-004 would sit at its limit (CALC). Measure first (EXP-I05).
2. **Pole width against stroke** (section 4.2): Rev H's 3 mm poles move 2.3–2.6 mm, more than this study's constant-force rule allows (CALC). Map force against position in EXP-I05.
3. **Free refill follows pen lifts** at 50–70° (section 3): strokes joined in normal writing, not only in autowrite (CALC).
4. **Refill spring fatigue** (section 6): a stock constant-force spring may last about an hour of tremor stabilisation (CALC on MFR AMF-144).
5. **Ledger reference**: `docs/revJ_plan.md` cites PAT-27 for "an actuated-nib pen that scribes predefined characters". In `docs/evidence.csv` PAT-27 is the Northwestern cobot patent; the BIC actuated-nib pen is **PAT-01**. Proposed fix in the plan's text.
6. **HAP-18 amendment**: its transferability text says the range differs (±0.5 mm against ±6.35 mm). With the Rev J nose (±6 mm guaranteed) the ranges now match; propose "range now comparable (Rev J ±6 mm guaranteed vs ±6.35 mm)". The same paper's rule (range = twice the user's error) supports the reach margin used here.

## 8. Proposed decision

Proposed rows for `docs/decisions.md` (the lead assigns the numbers and edits the log; this study does not).

**DEC-N1 (proposed): Rev J nose v2 — a short-arm gimbal with a spherical-gap actuator, 6.0 mm guaranteed, and a pen lift.**
- Decision: keep Rev H's architecture B (the skid ring on the fixed sleeve carries the writing force; the refill carrier tilts on a 2-axis flexure gimbal). Put the gimbal 76.5 mm behind the ball and the magnets on a short arm 11.5 mm behind it (the ball moves 6.6 times as far as the magnets). The magnets are a 2 × 2 checkerboard (6.3 mm poles, N52) on a spherical soft-iron cap facing a two-layer coil plate on a concentric sphere, so the gap stays 0.77 mm at every tilt. The refill and its holder stay in front of the magnet cap at every tilt and travel, so the actuator needs no central hole. Handle Ø24 mm. Guaranteed ball travel 6.0 mm in every direction over 35–75° (nominal 6.5 mm at 50°); skid-ring contact radius 10.0 mm; refill slide 24 mm. Add a pen-lift module at the gimbal: a drum whose fatigue-rated spiral spring sets the 0.15 N ink force through a tendon to the refill holder, an electro-permanent brake and a bistable latch (0.5 mm lift, no holding power). A page sensor (1 kHz, ≤ 2 ms, ≤ 10 µm) is required for autowrite.
- Alternatives considered: C1 (Rev H radial gap, scaled): feasible only to 5 mm in a 24 mm handle; C1+ (flat axial gap): 4 mm; C2 (two actuation planes): 5 mm at 38 g; C3 (coarse–fine): its fine stage is not designed; C4 (translating carrier, galvanometers, ultrasonic piezo, SMA, planar flexure stage): rejected (section 4.1).
- Evidence: this document, `results/nose2/nose2.json` — calculation (design models, optimised), simulation (HW1, test writers 0–5, seeds 200–203).
- Status: proposed.
- Revisit if: EXP-N01 measures Km below 0.85 × the design value; EXP-N04 exceeds 20 K or 41 °C; EXP-N07 cannot give a 1 kHz page position; the freedom-to-operate review of PAT-01 blocks a pen lift in autowrite (then autowrite without the lift, strokes joined).

**DEC-N2 (proposed): Autowrite ("the pen writes for you") is an explicit mode.**
- Decision: the pen draws letters of a known text (typed, dictated or copied in the app) inside the nose's reach while the user sweeps the pen along the line. It follows the user's sweep and waits when the user slows; it lifts the ball and stops when the text leaves its reach; it never pushes the hand. Default letter size 2.5 mm x-height; the pen chooses the sweep speed per line, 1.0–1.25 × the planner's line speed (about 7–10 mm/s, 3.0–3.7 letters/s), and cues the user.
- Alternatives: assistance only (no autowrite); delayed ink (needs the pen lift and a human-factors test first, EXP-N10).
- Evidence: section 5 (SIM).
- Status: proposed. Revisit if EXP-N09 shows users do not accept or control it.

**DEC-N3 (proposed; affects Rev H): measure the Rev H nose's force constant and the refill spring's life before building on them.**
- The image calculation gives 0.19 N/√W at the magnets, not 0.47 (section 4.2); a stock constant-force spring may last about an hour of tremor stabilisation (section 6); a free refill follows pen lifts at 50–70° (section 3).
- Status: proposed (EXP-I05 extended with a force map over the stroke; EXP-N06).

## 9. Proposed requirements

Proposed rows for `docs/requirements.csv` (the lead adds them; ids provisional). Values are hypotheses from this study's calculations and simulations.

| Id | Title | Requirement | Rationale | Verification |
|---|---|---|---|---|
| REQ-RVJ-N01 | Guaranteed tip travel | Ball travel relative to the handle ≥ 6.0 mm in every direction over 35–75° of tilt with the skid ring on the paper | Autowrite of 2.5 mm letters needs 4.1 mm for the worst tuning writer, plus 1 mm for tremor (CALC, section 2) | EXP-N02 |
| REQ-RVJ-N02 | Nose force and bandwidth | Force constant at the tip ≥ 0.85 × the design value (0.099 N/√W per axis, so ≥ 0.084) over the whole travel; closed-loop bandwidth ≥ 60 Hz; first parasitic mode ≥ 240 Hz | The design's power and heat margins rest on Km; the magnetics are an upper bound (CALC, section 4.2) | EXP-N01, EXP-N03 |
| REQ-RVJ-N03 | Heat | Coil temperature rise ≤ 20 K and grip surface ≤ 41 °C while autowriting with 1 mm tremor for 30 min | Skin contact (LIT AMF-34, AMF-35) | EXP-N04 |
| REQ-RVJ-N04 | Pen lift | The pen lifts the ball ≥ 0.3 mm off the paper and lowers it within 8 ms of the command, holds either state with no power, ≥ 10⁷ cycles | Strokes stay separate at 50–70° (section 3); autowrite and delayed ink need it (sections 5, 2) | EXP-N05 |
| REQ-RVJ-N05 | Refill force element | Ink force 0.15 N ± 20 % over the whole refill slide (24.4 mm for the recommended nose), never above 0.2 N; no fatigue failure within 10⁸ small cycles | Stock constant-force springs are rated 2 500–25 000 cycles (MFR AMF-144); tremor stabilisation cycles the slide about 29 000 times per hour | EXP-N06 |
| REQ-RVJ-N06 | Page sensor | Handle position on the page at ≥ 1 kHz, ≤ 2 ms latency, ≤ 10 µm rms, while writing at 35–75° | Autowrite's estimator and the SIM results assume it (section 5; sensitivity 5.5) | EXP-N07 |
| REQ-RVJ-N07 | Autowrite is a mode the user turns on | The pen draws letters on its own only in an explicit autowrite mode; it follows the user's sweep and waits when the user slows; it lifts the ball and stops drawing when the text leaves its reach; it never pushes the hand along the line | docs/revJ_plan.md section 6; LIT HAP-62 (users were frustrated when a handheld robot disobeyed); ACT-100 (Origin retracts when out of bounds). Amends REQ-RVH-007 for this mode | Design review; EXP-N09 |
| REQ-RVJ-N08 | Autowrite legibility (SIM gate before hardware) | On the HW1 test set (writers 0–5, seeds 200–203) at 2.5 mm letters with ≤ 1 mm tremor: mean letters read ≥ the mean clean-target ceiling − 2 points; mean ink error ≤ 45 µm rms; every writer's line is planned (the pen may slow the sweep for a line) | The SIM result of section 5.3 (99.2 % against 100 %, 29–36 µm), kept as a regression gate for firmware changes | nose2 test grid; EXP-N08 on the bench |

## 10. Experiments

Each experiment names what is missing today, the exact dependency, and a pass line. The pass lines are the targets of this study; treat them as hypotheses.

| Id | Purpose | Method | Measurand | Pass line |
|---|---|---|---|---|
| EXP-N01 | Check the magnetics before building a nose (and settle Rev H's Km) | Bench actuator coupons: one Rev H radial unit (3.0 × 6.5 × 2.8 mm N45, 1.43 mm coil, 2.77 mm gap) and one C1S spherical-gap unit (the recommended geometry, section 4.4). Force per ampere with a load cell over the stroke grid; coil resistance at 20 °C; gaussmeter map of the gap. Needs: magnets, a machined spherical Hiperco or 1010 cap and plate, 0.2 mm self-bonding magnet wire, a 0–2 N load cell (0.5 mN resolution), a bench supply. | Km (N/√W) per axis over the stroke; gap flux (T); force ripple (%) | Km ≥ 0.85 × the CALC value over the whole stroke; ripple ≤ 15 % (LIT AMF-143 measured 22–31 % over ±5 mm in a different actuator: calibrate if higher) |
| EXP-N02 | Travel and front-end closure over 35–75° | Build the nose (layout `results/nose2/layout.json`) with the skid ring; tilt jig at 35/50/75°; drive the nose to its travel in 24 directions on paper; photograph the ball; feeler gauges for the clearances | guaranteed ball travel (mm); nozzle and sleeve clearance to the paper (mm); refill slide (mm) | guaranteed travel ≥ 6.0 mm in every direction; nozzle ≥ 0.3 mm above the paper; ring lip ≥ 1.0 mm; slide within the refill spring's range |
| EXP-N03 | Servo bandwidth and parasitic modes | Swept-sine on the nose with the 3-D Hall sensor (TMAG5170, ±50 mT range, OPT-53) and a laser vibrometer on the ball | −3 dB bandwidth; phase margin; first parasitic mode | ≥ 60 Hz with ≥ 45° margin; first parasitic mode ≥ 240 Hz |
| EXP-N04 | Heat at the autowrite duty | Drive the coils with the recorded HW1 force histories of the test grid (1 mm tremor case) for 30 min in the handle; thermocouples on the coil and the shell | coil rise (K); shell surface temperature (°C) | coil rise ≤ 20 K; grip surface ≤ 41 °C at 23 °C ambient (IEC 60601-1: no justification needed at or below 41 °C, 43 °C limit for ≥ 10 min contact, LIT AMF-34; 43 °C for continuously held parts, LIT AMF-35) |
| EXP-N05 | Pen lift | Build the pen-lift module (drum with spiral spring, tendon loop, electro-permanent brake, bistable latch; section 6); drive it at 4 lifts/s for 10⁶ cycles; high-speed video of the ball; current probe | lift height (mm); switching time (ms); energy per cycle (mJ); holding power; cycles to failure | lift ≥ 0.3 mm within 8 ms; energy ≤ 20 mJ per cycle; zero holding power; ≥ 10⁷ cycles projected |
| EXP-N06 | Refill force element fatigue | Cycle four candidates (stock constant-force spring AMF-144; the drum's spiral spring; long helical spring; magnetic spring) at ±1 mm, 8 Hz and at ±5 mm, 3 Hz | force vs slide (N); cycles to failure | force 0.15 N ± 20 % over the slide; no failure within 10⁸ small cycles (about 3 years of 8 h days with tremor) |
| EXP-N07 | Page sensor under the pen | A PMW3360-class sensor (OPT-54) behind a flat window 2.4 mm above the paper beside the skid ring; the pen swept by a motion stage with 1 mm tremor added; ground truth from the stage encoders | position error (µm rms); latency (ms); drop-outs on lined, grid and glossy paper | ≤ 10 µm rms at 1 kHz, ≤ 2 ms latency, no drop-out on the test papers (the model's inputs: fusion study) |
| EXP-N08 | Autowrite on the bench | The pen on a motion stage that sweeps at the planner's speed, with tremor from a shaker (0.3/1/2 mm at 4/8/12 Hz); the text of the HW1 test set; scan the ink | ink error to the target (µm rms); letters and words read by the app's recogniser and reader; coil power | within 1.5 × the SIM values of section 5.3 at the same conditions; letters read ≥ the clean-target ceiling − 5 points |
| EXP-N09 | Autowrite with people | Healthy adults first, then people with ET (ethics approval, validation/human_study_plan.md); autowrite mode switched on by the user; copy a known sentence at 2.5 and 3 mm; questionnaires on control and trust (LIT HAP-62: frustration when the tool disobeys) | legibility by blinded readers; sweep speed chosen; perceived pull; mode errors | readers score autowrite ≥ the person's own writing; no participant reports the pen "taking over" outside the mode |
| EXP-N10 | Delayed ink acceptance | Delayed ink at 0/50/100/150 ms on a tablet first (no hardware needed), then with the nose; LIT OPT-50–52 predict it is noticed and may cause duplications | writing errors (duplicated or inserted strokes); letter size change; preference | no increase in errors over 0 ms; ≥ 50 % of users accept ≥ 100 ms |

## 11. What the literature says (sources opened by this study)

All rows are proposed for the ledger in `results/nose2/evidence_rows.csv` (exact 23-column header). "Abstract only" and "secondary account" are stated where that is all that was read.

**Mechanisms and parts**

| Id | Source | What it shows (numbers as published) | What it means for the nose |
|---|---|---|---|
| AMF-135 | Awtar & Parmar 2013, large-range XY flexure stage (full text) | 10 × 10 mm range needs 47.5 mm beams, a 255 × 255 mm flexure bearing; first mode about 18 Hz | A planar parallel flexure stage at pen scale cannot give ±5 mm: rejected (C4) |
| AMF-136 | Optotune MR-15-30 two-axis tilt mirror (datasheet) | ±25° per axis, 30 mm housing, 29.3 g, full-scale bandwidth 20 Hz, 1.5 W max | Two-axis voice-coil tilt stages exist as products, but not at pen size and power |
| AMF-137 | Cambridge Technology 62xxH galvanometers (datasheet) | 13.3–18 g each, about 12.7 mm body, 100–130 µs small step | Two galvos (one per axis) weigh 27–36 g and do not fit side by side: rejected (C4b) |
| AMF-138 | PI PILine ultrasonic motors (catalogue) | P-661: 10 g, 2 N, 500 mm/s, 120 Vpp motor, 12 V / 5 W driver, self-locking | Driver power 10 W for two axes, and a self-locking drive cannot yield to the writer: rejected (C4c) |
| AMF-139 | Arnold N52 (datasheet) | B_r 1.42–1.48 T, 7.6 g/cm³, −0.12 %/°C, 80 °C class | Magnet input of the models |
| AMF-140 | Hiperco 50A (product page) | 2.4 T saturation | Thinner flux return than 1010 steel (the optimiser may choose it) |
| AMF-141 / AMF-142 | Superelastic nitinol (FWM page; Pelton 2008, full text) | 8 % recoverable strain; fatigue limit ±0.4 % strain amplitude at 10⁷ cycles | The wire-flexure translating carrier (C4a) is sized to ±0.4 % / 1.5 |
| AMF-143 | Yang et al. 2020, 2-DOF Lorentz actuator (full text) | Force constant varies 21.6–30.9 % over ±5 mm / ±10° | A large-stroke voice coil needs its force map calibrated (EXP-N01) |
| AMF-144 | Lee Spring constant-force springs (catalogue) | Rated life 2 500, 4 000, 13 000 or 25 000 cycles; smallest stock spring 2.9 N | Rev H's refill spring would be cycled by every correction: fatigue risk (section 6) |
| AMF-145 | Takano latching solenoid (product page) | Holds ≥ 3 N with no power; smallest 16 × 16 × 35.7 mm | Zero-power holding is standard; the pen needs a much smaller custom latch |
| PAT-42 | Thorlabs US11960143B2 (patent page) | Arc-shaped magnets centred on the tilt axis keep the voice-coil gap constant; ±8° per axis | Prior art for the spherical-gap actuator (C1S); active until 2042: freedom-to-operate check needed |
| PAT-43 | Raytheon US11441598B2 (patent page) | Dual-axis flexure gimbal with four voice coils (tip-tilt) | Prior art for the gimbal-plus-four-coils layout; active until 2040 |

**Handheld tools that correct or write while swept**

| Id | Source | What it shows | Meaning |
|---|---|---|---|
| HAP-18 (existing) | Rivers, Moyer & Durand 2012 (re-read) | Correction range = twice the user's error (±6.35 mm); constant-speed mode stops at the range edge until the user catches up | The same control split as autowrite; its range is now the same size as the Rev J nose (amendment proposed in section 7) |
| ACT-100 | Shaper Origin (product pages) | Corrects within a 12.7 mm range; retracts the cutter when out of bounds | Autowrite should lift the ball when the text leaves the reach |
| PAT-40 | Shaper US2021/0034032A1 (patent page) | Coarse (user) + fine (device) positioning, fine range about 12.7 mm | Prior art for the coarse–fine split |
| HAP-62 | Stolzenwald & Mayol-Cuevas 2019 (full text) | Users were more frustrated when the tool disobeyed ("rebel" mode) | Autowrite follows the user's sweep and waits; it never pulls the hand |
| ACT-102 | Hasegawa et al. 2015 (full text) | A stylus moved through 7–14 mm letters at 1 letter/s was read by the hand at 85–91 % | Moving a held stylus through letters is feasible; up/down by a solenoid |
| AMF-149 | PrinCube hand-swept printer (secondary account) | Prints a 14.3 mm line while swept | "Writes as you sweep" products exist (inkjet) |
| PAT-44 | HP US5927872A (patent page) | Hand-held printer tracked by optical navigation sensors on the page | Prior art for page-tracked writing |
| PAT-41 | CalComp US3340541A (patent page) | Solenoid pen lift 0.5–0.64 mm at 40–50 lifts/s | Prior art and size of the pen lift |
| PAT-01 (existing) | BIC US12026327B2 (ledger) | Claim 1: nib moved in XP/YP **and ZP** by an actuated manipulator, an IMU, and an ECU that scribes predefined characters | The closest claim to autowrite with a pen lift: attorney review before any product (section 12) |

**Sensing, delay and handwriting**

| Id | Source | What it shows | Meaning |
|---|---|---|---|
| OPT-53 | TI TMAG5170 (datasheet) | ±25/50/100 mT ranges, 20 kSPS | The larger magnet stroke needs the ±50 mT range for the position servo |
| OPT-54 | PixArt PMW3360 (datasheet) | Up to 12 000 frames/s; lens 2.4 mm above the surface; lift cut-off 2–3 mm | A mouse-class sensor can be the 1 kHz page sensor if a flat window sits near the paper |
| AMF-153 | PAA5100JE (secondary account) | Far-field flow sensor, 10–35 mm range | Too slow for a 1 kHz page sensor |
| OPT-50 | Annett et al. 2014 (full text) | Just-noticeable inking latency 50–61 ms (median 53 ms) | Delayed ink of 100–200 ms will be seen |
| OPT-51 | Tamada 1995 (abstract only) | Delayed visual feedback raised writing errors (duplicated strokes) | Delayed ink may disturb the writer: a human question |
| OPT-52 | Morikiyo 1990 (abstract only) | Delay caused inserted strokes and larger letters | Same |
| AMF-146 | Teulings & Schomaker 1993 (abstract only) | Vertical stroke size is the most invariant feature | Autowrite must keep letter heights exact |
| AMF-147 | Zago et al. 2018 (full text) | Speed follows curvature^(−1/3) (two-thirds law) | A natural-looking plan slows in curves (not yet in the planner) |
| AMF-148 | Dziedzic 2026 (abstract only) | Poor line quality below about 20 mm/s | Drawing speed cap 45 mm/s is within the good-quality range |

## 12. Open issues and limits

- **Everything is model-to-model.** The writers, their tremor and the recogniser are synthetic; HW1's hand is a linear impedance (HAP-26). Real handwriting, real paper and real people may differ. No number here is a measurement.
- **Magnetics are an upper bound.** The image method assumes ideal iron. Saturation and finite iron lower the flux. The design keeps heat margin, but Km must be measured first (EXP-N01). Rev H's stated Km looks about 2.5 times too high by the same calculation.
- **The spherical-gap actuator is custom.** Curved magnet faces (ground, or segmented blocks) and coils bonded on a formed soft-iron plate. Prior art exists (PAT-42), but no supplier was contacted. The flat-coil fallback (C1, Rev H type) reaches only 5 mm within the heat limit in the 24 mm handle (6 mm needs 0.204 W, just over the 0.2 W limit), with about 55 % more added mass (CALC).
- **Freedom to operate.** Autowrite with a pen lift moves the nib in XP/YP **and ZP** under an ECU and an IMU to scribe predefined characters: this is close to claim 1 of BIC's US 12,026,327 B2 (PAT-01, active to about 2043). Dependent claims cover an optical displacement sensor and contact detection. Autowrite without the pen lift avoids the ZP element but joins strokes. The tip-tilt voice-coil patents (PAT-42 Thorlabs, to 2042; PAT-43 Raytheon, to 2040) and Shaper's coarse–fine patent (PAT-40) also need review. Not a legal opinion: attorney review before any product claim.
- **The page sensor is assumed.** Autowrite depends on knowing the handle's position on the page at 1 kHz within a few µm (fusion study's model). A mouse-class sensor needs a flat window about 2.4 mm from the paper beside the ring (OPT-54); at 35–75° of tilt that window's height and angle change. EXP-N07.
- **The refill force element.** A stock constant-force spring may fatigue within hours (section 6). The proposed replacement, a fatigue-rated spiral spring in the pen-lift drum driving the refill holder through a tendon loop, is a concept only: the spring, the tendon, its pulleys and their friction (which adds hysteresis to the ink force) are not designed (EXP-N05, EXP-N06).
- **The pen lift's energy** (about 17 mJ per lift cycle, about 0.07 W in autowrite) rests on assumed brake and latch values. A brake-only variant could lift the ball with the nose itself: with the refill braked, moving the ball in one direction of the tilt plane lifts it off the paper by about 0.5 mm per mm of travel at 50° (CALC, `nose2/frontend.poses`); it costs reach and was not simulated.
- **Refill replacement.** The D1 refill slides 24.4 mm over 35–75° and the travel (CALC). At its rearmost its holder passes the pen-lift module and the gimbal and enters the arm, 79.9 mm from the ball and 2.4 mm in front of the magnet cap (`layout.json`); the actuator has no central hole. Proposed: the nozzle unscrews, the tendon unhooks from the holder, and the refill with its holder comes out at the front (ASSUMPTION; not drawn in detail).
- **Letter shapes.** The recogniser misreads some clean synthetic letters (the ceiling is below 100 %); the ceiling is reported beside every result.
- **The plan's speed profile** is not the two-thirds law of human writing (LIT AMF-147): the ink may look mechanical. Not evaluated.
- **Human factors.** Whether people accept a pen that writes for them, trust it, and sweep steadily enough is unknown (EXP-N09). "Writes for you" stays an explicit mode (docs/revJ_plan.md section 6).
- **Drop and shock.** The flexure's strain is checked at the stop; a drop onto the tip loads the stops and the ring. Not analysed.
- **The tuned sweep speed was too fast for one test writer.** Rule T5 chose 1.25 × the planner's line speed from the four tuning writers; test writer 4 needs 6.3 mm of reach at that speed, more than the 5.5 mm plan reach, so none of its 40 test cases at 2.5 mm (4 seeds × 10 tremor conditions) had a plan (section 5.3). The fix (the pen chooses the speed per line, 1.0–1.25 ×) was checked only after the test (post hoc, section 5.3), and a new set of test writers should confirm it.
- **Coil heat at 2 mm tremor.** With 2 mm rms tremor the coil loss while autowriting is 0.38 W, about twice the 0.182 W design point (SIM): about 38 K at 100 K/W if sustained. The 100 K/W thermal resistance is an ASSUMPTION and the coil's thermal time constant is unknown, so how long such a text may run is open (EXP-N04). The firmware should limit the duty (short texts, or slower sweeps).
- **Wires past the actuator.** The optimiser used the whole 11 mm bore radius for the fixed coil plate (0.005 mm margin). The plate can be bonded into the shell, but the wires from the page sensor at the front and from the pen-lift module on the moving nose must pass it (a groove in the shell wall or a notch in the plate), and the pen lift's leads must cross the gimbal without adding stiffness or friction. Not modelled (ASSUMPTION).
- **Coarse–fine (C3) is not designed.** Its fine stage is an assumed 0.25 g moving mass with 0.05 N/√W at the tip; C3 halves the coil loss in the model, so it is the first refinement to design for round 2.
- **Compute.** One process on the shared machine: the full pipeline ran in about 40 min (optimisation 280 runs, 17 min; tuning 512 runs, 7 min; test grid 8 min; post-hoc fallback 4 min).

## 13. Files and how to run

**Code** (`nose2/`, Python; PyTorch, numba, magpylib, CadQuery):

| File | What it does |
|---|---|
| `nose2/tasks.py` | Travel from the tasks: tremor peaks, guided shaping, autowrite reach, delayed ink, autowrite kinematics |
| `nose2/planner.py` | The look-ahead autowrite planner (dynamic-programming time warp within the reach) |
| `nose2/frontend.py` | DEC-034 front-end closure, vectorised and generalised (checked against `opt/inertial/front_end.py`) |
| `nose2/magnetics.py` | magpylib gap flux with iron images; the surrogate grid, fit and check |
| `nose2/designs.py` | Differentiable models of every candidate; the pen-lift sizing; datasheet screening |
| `nose2/optimise.py` | CMA-ES + adjoint L-BFGS, the sweep, Pareto fronts, gradient check |
| `nose2/choose.py` | The selection rule (R1–R4) |
| `nose2/autowrite.py` | Autowrite in HW1: scenario, causal estimator, progress, command, pen lift, metrics |
| `nose2/tuning.py`, `nose2/evaluate.py` | Tuning rules (tuning writers and seeds) and the test grid (test writers and seeds), limits, sensitivities, the post-hoc slower-sweep check (`fallback`) |
| `nose2/layout.py` | `results/nose2/layout.json` in the Rev H schema |
| `nose2/figures.py`, `nose2/report.py`, `nose2/evidence.py` | Figures with CSV twins, `nose2.json`, proposed ledger rows |
| `nose2/run_study.py` | The pipeline, stage by stage |
| `nose2/tests/` | 18 fast tests (about 7 s): front end against the original, image convention, surrogate, adjoint gradients against finite differences, CMA-ES, Pareto filter, planner, selection rule, autowrite smoke test, ledger header |
| `mechanics/cad/nose2.py` | CadQuery assembly (STEP), drawing and front-end views of the recommended nose |

**Results** (`results/nose2/`): `nose2.json` (every number, with its label and the `stabpen.provenance` block), `layout.json` (Rev H schema), `evidence_rows.csv` (proposed ledger rows), `nose2_assembly.step`, `drawing_nose2.png` (+ `.csv`, the component table), `fig_nose2_front_end.png` (+ `.csv`), `nose2_cad_summary.json`, and the figures `fig_nose2_*.png`, each with its CSV twin.

**Run** (one process; about 40 min for every stage, about 1.5 min for `--quick`):

```
python3 nose2/run_study.py                      # every stage; caches in nose2/build/cache (git-ignored)
python3 nose2/run_study.py --quick              # a tiny subset of every stage, written to nose2/build/quick (about 1.5 min)
python3 nose2/run_study.py --stages test,report  # selected stages from the caches
python3 mechanics/cad/nose2.py                   # CAD only (reads results/nose2/nose2.json)
python3 -m pytest nose2/tests -q                 # fast tests
```
