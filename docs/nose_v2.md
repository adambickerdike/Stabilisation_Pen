# Rev J study N: nose v2 — a larger-travel tip, and a pen that writes letters by itself

**Status: calculation and simulation only, 2026-09-28.** Nothing here was built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation of model HW1 (`handwriting/`, used read-only through its public API; wrapper `nose2/autowrite.py`), on **synthetic** writers (`aiguide`) and **synthetic** tremor;
- **CALC**: a calculation (planner, front-end geometry, magnetics with magpylib, design models in `nose2/`);
- **LIT (id)** / **MFR (id)**: a published or manufacturer statement with its ledger id (`docs/evidence.csv`, or the rows this study proposes in `results/nose2/evidence_rows.csv`);
- **ASSUMPTION**: an input nobody has measured;
- **PROPOSED DESIGN**: a dimensioned concept (layout, CAD).

Numbers come from `results/nose2/nose2.json` (with its `stabpen.provenance` block) unless a ledger id is given. Tuning used writers 100–103 and seeds 300–303 only; every autowrite result in the tables uses the test writers 0–5 and test seeds 200–203, after the rules were frozen.

⟨SECTION1⟩

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
- At a guaranteed 6 mm the ring's contact radius is about 9.5 mm (front diameter about 20.5 mm, against 15 mm in Rev H) and the refill slides about 26 mm over 35–75° (19–20 mm over 40–70°), against 13.5 mm in Rev H. The skid ring stays C-shaped and open on the top, so the ink stays visible (DEC-034).

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
| C1 | Rev H scaled: 2-axis flexure gimbal, four magnet pole pairs on a hub behind the pivot, flat coils in a soft-iron ring (radial gap) | differentiable model + optimiser | ⟨C1⟩ |
| C1+ | Same gimbal, but a 2 × 2 checkerboard of poles faces a flat two-layer coil plate **across** the pen axis (axial gap): lateral motion slides the poles along the coils | differentiable model + optimiser | ⟨C1p⟩ |
| C1S | As C1+, with the magnet cap and coil plate on **spheres centred on the gimbal**: the gap stays constant as the nose tilts (prior art: arc-shaped magnets centred on the tilt axis, PAT-42) | differentiable model + optimiser | ⟨C1S⟩ |
| C2 | Two actuation planes: a front coil set around the carrier (grip zone) and a rear set on the arm; the carrier on two flexure planes, so it pivots about a virtual point | differentiable model + optimiser (optimal force split) | ⟨C2⟩ |
| C3 | Coarse–fine: C1S as the coarse stage plus a ±1 mm fine stage at the carrier front for tremor | model; fine stage with assumed values | ⟨C3⟩ |
| C4a | Translating carrier on four superelastic nitinol wires, no lever, axial-gap actuator | differentiable model + optimiser | ⟨C4a⟩ |
| C4b | Galvanometer (rotary moving-magnet) scanner per axis | datasheet screening (MFR AMF-137) | Rejected: 13–18 g each, Ø12.7 mm bodies do not fit side by side; ⟨GALVO⟩ |
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

- **Model** (`nose2/designs.py`, PyTorch): tip travel (nominal and guaranteed, from the front-end fit), force per √W at the tip, tip-equivalent moving mass, suspension stiffness, first parasitic mode (arm and carrier bending), peak force within the 3.7 V / 1.5 A drive (Rev H assumption), coil loss for two duties, coil temperature (100 K/W, ASSUMPTION), flexure strain, actuator envelope, length, reaction on the hand, added mass.
- **Duties**: (a) stabilising 1 mm rms tremor at 8 Hz; (b) autowriting 3 mm letters (the planner's nose motion: 1.35 mm rms per axis, 4.7 m/s² at the 99.9th percentile, inking 64 % of the time) with 1 mm tremor on top. The effective accelerations (10.6 m/s² for the tremor duty, 4.5 m/s² for autowrite) were calibrated on HW1 runs (tuning writer 100, seed 300): they include the servo's high-frequency force from ball-friction reversals. The ball drag is μ 0.15 × 0.196 N while inking (ASSUMPTION within LIT CON-13).
- **Real parts**: magnet grade (N42SH, N48SH, N52; MFR AMF-28, AMF-139), flexure alloy and shim thickness (301 full hard, 17-7PH, Ti-6Al-4V, C17200, superelastic NiTi; AMF-19–21, AMF-141–142), magnet wire (0.08–0.20 mm), back iron (1010 or Hiperco 50A, AMF-140).
- **Constraints** (a design is feasible only if all hold): guaranteed travel; fits the handle bore (22 or 24 mm handle, 1 mm wall); parasitic modes ≥ 3 × the 80 Hz servo; peak force; flexure strain within fatigue (÷ 1.5) and static limits; **coil temperature rise ≤ 20 K** while autowriting with tremor (about 0.2 W; keeps the shell near skin temperature, ASSUMPTION); actuator within 100 mm of the tip.
- **Search**: CMA-ES (own implementation) over the continuous variables and the part choices, then an **adjoint (reverse-mode) L-BFGS polish** of the continuous variables. The gradients match central differences (worst relative error ⟨GRAD⟩). Objective: autowrite coil loss + μ × added mass (μ = 1 and 4 W/kg). Swept over the required travel (4–8 mm), both handles, 3 seeds for the four main candidates (1 for C3 and C4a): ⟨NRUNS⟩ optimisations, ⟨NFEAS⟩ feasible designs kept for the Pareto fronts (travel, force per √W, added mass, power).

⟨OPTRESULTS⟩

### 4.4 The recommended mechanism

⟨RECOMMENDED⟩

## 5. Autowrite in HW1: can the pen write letters by itself?

### 5.1 How autowrite works in the simulation

The scene (SIM, model HW1 in `handwriting/`, used read-only; wrapper `nose2/autowrite.py`):
- The writer holds the pen with the skid ring on the paper. The hand only sweeps the pen along the line at a steady speed. Tremor may be added (the project's tremor model: 0.3, 1 or 2 mm at 4, 8 or 12 Hz).
- The pen knows the text in advance ("return library books by friday", the sentence of the earlier handwriting studies). A synthetic writer from `aiguide` sets the style: size, slant, letter shapes.
- The hand model is HW1's (HAP-26 impedance). It does not compensate the pen's drag (ASSUMPTION; a sensitivity case lets it).

What the pen does (all causal; every 0.5 ms tick):
1. **Plan the line before it is written** (`nose2/planner.py`, CALC). The text becomes one path: strokes plus pen-up moves. Dynamic programming picks *when* each point is drawn so that it stays within the reach of the sweeping hand. Drawing speed stays between 4 and 45 mm/s; pen-up moves up to 90 mm/s (ASSUMPTIONS). Each stroke starts and ends with a short dwell (15 ms and 10 ms), as the writers do, so dots leave ink.
2. **Know where the handle is.** A complementary estimator joins the page sensor (1 kHz, 2 ms latency, 3 µm noise: the fusion study's model, ASSUMPTION) and the IMU (LSM6DSV16X model). It predicts the handle one servo delay ahead.
3. **Follow the user.** The plan's clock is the hand's position along the line, filtered. If the hand slows, the pen waits. It never pulls the hand forward (ACT-101).
4. **Draw.** Nose command = planned ink point − predicted handle position. HW1's servo (80 Hz, travel, force and slew limits of the design) moves the ball.
5. **Lift and lower the ball** along the plan's pen-down flags, with an 8 ms switching delay (ASSUMPTION; the pen commands one delay ahead). Without the axial DOF, the ball stays on the paper for the whole line and the pen-up moves are inked.

The handle motion depends a little on the nose (reaction and ball drag), so each case runs as a fixed point: the causal command is recomputed from the previous run's sensor streams until it changes by less than 5 µm rms (at most 6 passes).

Metrics per case: ink error to the target letters (µm rms, HW1's letter metric); letters read by the app's recogniser (HW1 `recognizer_for`); words read after the app's reader; the same recogniser on the clean target letters (**the ceiling**: some synthetic letter shapes are misread even when drawn perfectly); letters per second; coil loss; force; time at the travel limit; handle deviation.

### 5.2 Settings chosen on tuning data

⟨TUNING⟩

### 5.3 Results on the test writers and seeds

⟨AWRESULTS⟩

### 5.4 How large and how fast

⟨LIMITS⟩

### 5.5 What matters (one factor at a time)

⟨SENS⟩

## 6. The pen lift (axial degree of freedom)

Why the pen needs it:
- A freely sliding refill follows ordinary pen lifts at 50–70° (section 3): strokes get joined.
- Without it, autowrite inks every pen-up move. The recogniser still reads most letters, but the ink error doubles or more (section 5.3), and dots join their stems.
- Delayed ink lays 40–55 % of its ink after the hand has lifted (section 2).

Proposed mechanism (PROPOSED DESIGN, CALC `nose2/designs.axial_dof`; inputs ASSUMPTION unless noted):
- While writing, a spring keeps the ball on the paper, as in Rev H.
- For a pen-up, an **electro-permanent brake** locks the refill holder to the carrier, and a **bistable reluctance latch** (a soft-iron plunger with a permanent-magnet detent) pulls the refill back 0.5 mm (CalComp's plotter pen lift moved 0.5–0.64 mm at 40–50 lifts per second, LIT PAT-41). Neither needs power to hold.
- For a pen-down, both release.

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
| Mass | about 2 g, just in front of the gimbal (0.02 g at the tip) | ASSUMPTION |

The pen lift is about a third of the autowrite power budget. A larger pole, a longer switching time or a lighter brake would lower it; EXP-N05 measures it. In normal writing (stabiliser on, the writer lifts the pen), the pen lift works the other way round: when the refill-slide sensor (Rev H's 1 mm target magnet, AMF-72) sees the refill start to follow a lift, the brake locks it, so the ball leaves the paper with the pen. The brake alone does this (about 6 mJ per stroke, ASSUMPTION).

**Refill spring fatigue (finding for Rev H too).** The refill slide changes with every correction of the nose: about 0.65 mm of slide per mm of ball travel in the tilt plane at 50°, almost none sideways (CALC, `nose2/frontend.poses`). Stock constant-force springs are rated for 2 500–25 000 cycles (MFR AMF-144). Stabilising 8 Hz tremor is about 29 000 cycles per hour, and autowrite about 15 000–36 000. A strip that winds on a drum bends and unbends the same short section on every small cycle, so the rated life is the relevant order of magnitude (ASSUMPTION; the maker rates full strokes). The refill force element should be a fatigue-rated part: a long, soft helical spring below its endurance limit, or a magnetic spring (EXP-N06).

## 7. Findings about Rev H for the lead

1. **Force constant** (section 4.2): the image calculation gives 0.19 N/√W at the magnets, not 0.47. REQ-RVH-003 would fail and REQ-RVH-004 would sit at its limit (CALC). Measure first (EXP-I05).
2. **Free refill follows pen lifts** at 50–70° (section 3): strokes joined in normal writing, not only in autowrite (CALC).
3. **Refill spring fatigue** (section 6): a stock constant-force spring may last about an hour of tremor stabilisation (CALC on MFR AMF-144).
4. **Ledger reference**: `docs/revJ_plan.md` cites PAT-27 for "an actuated-nib pen that scribes predefined characters". In `docs/evidence.csv` PAT-27 is the Northwestern cobot patent; the BIC actuated-nib pen is **PAT-01**. Proposed fix in the plan's text.
5. **HAP-18 amendment**: its transferability text says the range differs (±0.5 mm against ±6.35 mm). With the Rev J nose (±6 mm guaranteed) the ranges now match; propose "range now comparable (Rev J ±6 mm guaranteed vs ±6.35 mm)". The same paper's rule (range = twice the user's error) supports the reach margin used here.

## 8. Proposed decision

⟨DECISION⟩

## 9. Proposed requirements

Proposed rows for `docs/requirements.csv` (the lead adds them; ids provisional). Values are hypotheses from this study's calculations and simulations.

| Id | Title | Requirement | Rationale | Verification |
|---|---|---|---|---|
| REQ-RVJ-N01 | Guaranteed tip travel | Ball travel relative to the handle ≥ 6.0 mm in every direction over 35–75° of tilt with the skid ring on the paper | Autowrite of 2.5 mm letters needs 4.1 mm for the worst tuning writer, plus 1 mm for tremor (CALC, section 2) | EXP-N02 |
| REQ-RVJ-N02 | Nose force and bandwidth | Force constant at the tip ≥ 0.85 × the design value ⟨KM⟩ N/√W per axis over the whole travel; closed-loop bandwidth ≥ 60 Hz; first parasitic mode ≥ 240 Hz | The design's power and heat margins rest on Km; the magnetics are an upper bound (CALC, section 4.2) | EXP-N01, EXP-N03 |
| REQ-RVJ-N03 | Heat | Coil temperature rise ≤ 20 K and grip surface ≤ 41 °C while autowriting with 1 mm tremor for 30 min | Skin contact (LIT AMF-34, AMF-35) | EXP-N04 |
| REQ-RVJ-N04 | Pen lift | The pen lifts the ball ≥ 0.3 mm off the paper and lowers it within 8 ms of the command, holds either state with no power, ≥ 10⁷ cycles | Strokes stay separate at 50–70° (section 3); autowrite and delayed ink need it (sections 5, 2) | EXP-N05 |
| REQ-RVJ-N05 | Refill force element | Ink force 0.15 N ± 20 % over the whole refill slide (about 26 mm at 6 mm travel); no fatigue failure within 10⁸ small cycles | Stock constant-force springs are rated 2 500–25 000 cycles (MFR AMF-144); tremor stabilisation cycles the slide about 29 000 times per hour | EXP-N06 |
| REQ-RVJ-N06 | Page sensor | Handle position on the page at ≥ 1 kHz, ≤ 2 ms latency, ≤ 10 µm rms, while writing at 35–75° | Autowrite's estimator and the SIM results assume it (section 5; sensitivity 5.5) | EXP-N07 |
| REQ-RVJ-N07 | Autowrite is a mode the user turns on | The pen draws letters on its own only in an explicit autowrite mode; it follows the user's sweep and waits when the user slows; it lifts the ball and stops drawing when the text leaves its reach; it never pushes the hand along the line | docs/revJ_plan.md section 6; LIT ACT-101 (users were frustrated when a handheld robot disobeyed); ACT-100 (Origin retracts when out of bounds). Amends REQ-RVH-007 for this mode | Design review; EXP-N09 |
| REQ-RVJ-N08 | Autowrite legibility (SIM gate before hardware) | On the HW1 test set (writers 0–5, seeds 200–203) at 2.5 mm letters with ≤ 1 mm tremor: letters read ≥ the clean-target ceiling − 2 points; ink error ≤ 60 µm rms | The SIM result of section 5.3, kept as a regression gate for firmware changes | nose2 test grid; EXP-N08 on the bench |

## 10. Experiments

Each experiment names what is missing today, the exact dependency, and a pass line. The pass lines are the targets of this study; treat them as hypotheses.

| Id | Purpose | Method | Measurand | Pass line |
|---|---|---|---|---|
| EXP-N01 | Check the magnetics before building a nose (and settle Rev H's Km) | Bench actuator coupons: one Rev H radial unit (3.0 × 6.5 × 2.8 mm N45, 1.43 mm coil, 2.77 mm gap) and one C1S spherical-gap unit (the recommended geometry, section 4.4). Force per ampere with a load cell over the stroke grid; coil resistance at 20 °C; gaussmeter map of the gap. Needs: magnets, a 3-D printed or machined spherical cap and plate, 0.1 mm magnet wire, a 0–2 N load cell (0.5 mN resolution), a bench supply. | Km (N/√W) per axis over the stroke; gap flux (T); force ripple (%) | Km ≥ 0.85 × the CALC value over the whole stroke; ripple ≤ 15 % (LIT AMF-143 measured 22–31 % over ±5 mm in a different actuator: calibrate if higher) |
| EXP-N02 | Travel and front-end closure over 35–75° | Build the nose (layout `results/nose2/layout.json`) with the skid ring; tilt jig at 35/50/75°; drive the nose to its travel in 24 directions on paper; photograph the ball; feeler gauges for the clearances | guaranteed ball travel (mm); nozzle and sleeve clearance to the paper (mm); refill slide (mm) | guaranteed travel ≥ 6.0 mm in every direction; nozzle ≥ 0.3 mm above the paper; ring lip ≥ 1.0 mm; slide within the refill spring's range |
| EXP-N03 | Servo bandwidth and parasitic modes | Swept-sine on the nose with the 3-D Hall sensor (TMAG5170, ±50 mT range, OPT-53) and a laser vibrometer on the ball | −3 dB bandwidth; phase margin; first parasitic mode | ≥ 60 Hz with ≥ 45° margin; first parasitic mode ≥ 240 Hz |
| EXP-N04 | Heat at the autowrite duty | Drive the coils with the recorded HW1 force histories of the test grid (1 mm tremor case) for 30 min in the handle; thermocouples on the coil and the shell | coil rise (K); shell surface temperature (°C) | coil rise ≤ 20 K; grip surface ≤ 41 °C at 23 °C ambient (IEC 60601-1: no justification needed at or below 41 °C, 43 °C limit for ≥ 10 min contact, LIT AMF-34; 43 °C for continuously held parts, LIT AMF-35) |
| EXP-N05 | Pen lift | Build the brake + latch module (section 6); drive it at 4 lifts/s for 10⁶ cycles; high-speed video of the ball; current probe | lift height (mm); switching time (ms); energy per cycle (mJ); holding power; cycles to failure | lift ≥ 0.3 mm within 8 ms; energy ≤ 20 mJ per cycle; zero holding power; ≥ 10⁷ cycles projected |
| EXP-N06 | Refill force element fatigue | Cycle three candidates (stock constant-force spring AMF-144; long helical spring; magnetic spring) at ±1 mm, 8 Hz and at ±5 mm, 3 Hz | force vs slide (N); cycles to failure | force 0.15 N ± 20 % over the slide; no failure within 10⁸ small cycles (about 3 years of 8 h days with tremor) |
| EXP-N07 | Page sensor under the pen | A PMW3360-class sensor (OPT-54) behind a flat window 2.4 mm above the paper beside the skid ring; the pen swept by a motion stage with 1 mm tremor added; ground truth from the stage encoders | position error (µm rms); latency (ms); drop-outs on lined, grid and glossy paper | ≤ 10 µm rms at 1 kHz, ≤ 2 ms latency, no drop-out on the test papers (the model's inputs: fusion study) |
| EXP-N08 | Autowrite on the bench | The pen on a motion stage that sweeps at the planner's speed, with tremor from a shaker (0.3/1/2 mm at 4/8/12 Hz); the text of the HW1 test set; scan the ink | ink error to the target (µm rms); letters and words read by the app's recogniser and reader; coil power | within 1.5 × the SIM values of section 5.3 at the same conditions; letters read ≥ the clean-target ceiling − 5 points |
| EXP-N09 | Autowrite with people | Healthy adults first, then people with ET (ethics approval, validation/human_study_plan.md); autowrite mode switched on by the user; copy a known sentence at 2.5 and 3 mm; questionnaires on control and trust (LIT ACT-101: frustration when the tool disobeys) | legibility by blinded readers; sweep speed chosen; perceived pull; mode errors | readers score autowrite ≥ the person's own writing; no participant reports the pen "taking over" outside the mode |
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
| HAP-18 (existing) | Rivers, Moyer & Durand 2012 (re-read) | Correction range = twice the user's error (±6.35 mm); constant-speed mode stops at the range edge until the user catches up | The same control split as autowrite; its range is now the same size as the Rev J nose (amendment proposed in section 8) |
| ACT-100 | Shaper Origin (product pages) | Corrects within a 12.7 mm range; retracts the cutter when out of bounds | Autowrite should lift the ball when the text leaves the reach |
| PAT-40 | Shaper US2021/0034032A1 (patent page) | Coarse (user) + fine (device) positioning, fine range about 12.7 mm | Prior art for the coarse–fine split |
| ACT-101 | Stolzenwald & Mayol-Cuevas 2019 (full text) | Users were more frustrated when the tool disobeyed ("rebel" mode) | Autowrite follows the user's sweep and waits; it never pulls the hand |
| ACT-102 | Hasegawa et al. 2015 (full text) | A stylus moved through 7–14 mm letters at 1 letter/s was read by the hand at 85–91 % | Moving a held stylus through letters is feasible; up/down by a solenoid |
| AMF-149 | PrinCube hand-swept printer (secondary account) | Prints a 14.3 mm line while swept | "Writes as you sweep" products exist (inkjet) |
| PAT-44 | HP US5927872A (patent page) | Hand-held printer tracked by optical navigation sensors on the page | Prior art for page-tracked writing |
| PAT-41 | CalComp US3340541A (patent page) | Solenoid pen lift 0.5–0.64 mm at 40–50 lifts/s | Prior art and size of the pen lift |
| PAT-01 (existing) | BIC US12026327B2 (ledger) | Claim 1: nib moved in XP/YP **and ZP** by an actuated manipulator, an IMU, and an ECU that scribes predefined characters | The closest claim to autowrite with a pen lift: attorney review before any product (section 9) |

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
- **The spherical-gap actuator is custom.** Curved magnet faces (ground, or segmented blocks) and coils bonded on a formed soft-iron plate. Prior art exists (PAT-42), but no supplier was contacted. The flat-coil fallback (C1, Rev H type) reaches the same travel only with more mass and at the heat limit.
- **Freedom to operate.** Autowrite with a pen lift moves the nib in XP/YP **and ZP** under an ECU and an IMU to scribe predefined characters: this is close to claim 1 of BIC's US 12,026,327 B2 (PAT-01, active to about 2043). Dependent claims cover an optical displacement sensor and contact detection. Autowrite without the pen lift avoids the ZP element but joins strokes. The tip-tilt voice-coil patents (PAT-42 Thorlabs, to 2042; PAT-43 Raytheon, to 2040) and Shaper's coarse–fine patent (PAT-40) also need review. Not a legal opinion: attorney review before any product claim.
- **The page sensor is assumed.** Autowrite depends on knowing the handle's position on the page at 1 kHz within a few µm (fusion study's model). A mouse-class sensor needs a flat window about 2.4 mm from the paper beside the ring (OPT-54); at 35–75° of tilt that window's height and angle change. EXP-N07.
- **The refill force element** (constant-force spring) may fatigue within hours (section 6). Its replacement (long helical or magnetic spring) is not designed yet.
- **The pen lift's energy** (about 17 mJ per lift cycle, about 0.07 W in autowrite) rests on assumed brake and latch values. A brake-only variant could lift the ball with the nose itself: with the refill braked, moving the ball in one direction of the tilt plane lifts it off the paper by about 0.5 mm per mm of travel at 50° (CALC, `nose2/frontend.poses`); it costs reach and was not simulated.
- **Refill replacement.** The D1 refill slides about 26 mm and passes through the gimbal, the arm and the actuator's central hole. Proposed: the nozzle unscrews and the refill with its holder comes out at the front (ASSUMPTION; not drawn in detail).
- **Letter shapes.** The recogniser misreads some clean synthetic letters (the ceiling is below 100 %); the ceiling is reported beside every result.
- **The plan's speed profile** is not the two-thirds law of human writing (LIT AMF-147): the ink may look mechanical. Not evaluated.
- **Human factors.** Whether people accept a pen that writes for them, trust it, and sweep steadily enough is unknown (EXP-N09). "Writes for you" stays an explicit mode (docs/revJ_plan.md section 6).
- **Drop and shock.** The flexure's strain is checked at the stop; a drop onto the tip loads the stops and the ring. Not analysed.
- **Compute.** The optimisation (280 runs), tuning (512 runs) and the test grid ran on one core; the full pipeline takes about 2 h.

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
| `nose2/tuning.py`, `nose2/evaluate.py` | Tuning rules (tuning writers and seeds) and the test grid (test writers and seeds), limits, sensitivities |
| `nose2/layout.py` | `results/nose2/layout.json` in the Rev H schema |
| `nose2/figures.py`, `nose2/report.py`, `nose2/evidence.py` | Figures with CSV twins, `nose2.json`, proposed ledger rows |
| `nose2/run_study.py` | The pipeline, stage by stage |
| `nose2/tests/` | 18 fast tests (about 30 s): front end against the original, image convention, surrogate, adjoint gradients against finite differences, CMA-ES, Pareto filter, planner, selection rule, autowrite smoke test, ledger header |
| `mechanics/cad/nose2.py` | CadQuery assembly (STEP), drawing and front-end views of the recommended nose |

**Results** (`results/nose2/`): `nose2.json` (every number, with its label and the `stabpen.provenance` block), `layout.json` (Rev H schema), `evidence_rows.csv` (proposed ledger rows), `nose2_assembly.step`, `drawing_nose2.png` (+ `.csv`, the component table), `fig_nose2_front_end.png` (+ `.csv`), `nose2_cad_summary.json`, and the figures `fig_nose2_*.png`, each with its CSV twin.

**Run** (one process; about 2 h on one core):

```
python3 nose2/run_study.py                      # every stage; caches in nose2/build/cache (git-ignored)
python3 nose2/run_study.py --quick              # a tiny subset of every stage, written to nose2/build/quick (minutes)
python3 nose2/run_study.py --stages test,report  # selected stages from the caches
python3 mechanics/cad/nose2.py                   # CAD only (reads results/nose2/nose2.json)
python3 -m pytest nose2/tests -q                 # fast tests
```
