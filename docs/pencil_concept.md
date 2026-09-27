# Pencil-class concept (Rev P0)

**Status: proposed design.** Every number here is a calculation, a simulation, or a manufacturer statement with a ledger id; none is a measurement of our hardware. Evidence labels: **CALC**, **SIM**, **MFR** (manufacturer statement, `docs/evidence.csv` id), **ASSUMPTION**.

Parameters: `config/pencil.yaml` (overlay on `config/parameters.yaml` v0.4.4).
Detailed reports:
- [`pencil_mechanisms.md`](pencil_mechanisms.md): forces, mechanisms, power, pencil simulation;
- [`ai_guidance.md`](ai_guidance.md): prediction, guidance, autocorrect;
- [`sim_to_real.md`](sim_to_real.md): calibration and twin experiments.

3D replay: `viewer/` (build with `python3 viewer/build.py`).

## 1. The request and the short answer

The request was for:
- an Apple-Pencil-class pen (8.9 mm × 166 mm, 19 g; AMF-41) that physically improves the ink;
- AI prediction that comes close to autocorrecting the sentence;
- recording to the app;
- the exact forces and mechanisms using existing technology;
- what has to be made;
- a 3D simulation and sim-to-real work.

The short answer, with the numbers behind it in the sections below:

1. **The Rev A mechanism cannot be shrunk.** Any stage that moves the nib across the barrel must hold the paper's reaction N·cos θ plus friction: 0.64 N + 0.15 N at 1 N and 50° (COR-01, CALC). The Rev A moving coil holds that at 0.49 W against a 0.41 W thermal allowance in a 15 mm barrel. A coil in a 7.9 mm bore is far worse (§3).
2. **The pencil works if the writing force bypasses the nib.** A skid ring on the nose grounds the user's force to the barrel (DEC-008 candidate D). The nib is pressed on by a light axial spring, so the stage only carries F_c·cot θ + friction. That is 0.13 N + 0.03 N at F_c = 0.15 N (CALC).
3. **The stage is piezo, not a coil.** A piezo bender holds a static load at almost no power. Four custom 2.6 mm multilayer plates (PICMA technology, AMF-11) fit around a D1 refill in the 7.9 mm bore. Under the design load they give ±277 µm of stroke and 0.329 N at the nib, with a 192 Hz first resonance (CALC). The best voice coil that fits needs 2.4 W to hold the same load (SIM). CAD: 12.2 g before wiring and margin, and no interference at full travel (§3, §4).
4. **What the ink can gain is bounded.** The usable correction is about ±0.3 mm at the nib (±277 µm under load). With perfect knowledge of intent the pencil cuts the ink error to 0.19–0.26 of the uncorrected value for 0.1 mm tremor. It reaches 0.20–0.46 at 0.3 mm, where it hits its travel limit (SIM). With the pen's own tremor estimator it achieves 0.85–0.92, and only at 8–12 Hz; at lower frequencies it cannot tell tremor from writing. That estimator is the same open problem as in Rev A (§3, §10).
5. **AI autocorrect works digitally, not physically.** In the app, a language-model corrector cuts word errors from 32 % to 10 % at a 7 % recognition error rate. It changes ≤ 0.1 % of correct words and leaves the original ink untouched (CALC). Physically, the pen can pull the nib toward an AI-predicted letter drawn in the user's style. But such a template is itself about 300 µm off, which is right at the 230–330 µm break-even. So AI templates give no net benefit on free handwriting, although wrong predictions are safely bounded by the travel (SIM). Physical guidance pays off when the template is known, as in tracing, copying or drawing aids (§6).
6. **Recording on paper needs a new sensor.** Nothing off the shelf fits the nose. The simulation sets the requirement: a page sensor of ≥ 120 Hz with ≤ 10 ms latency, fused with the IMU. The chip-scale camera that does fit runs at 30 fps and loses most of the guided-mode benefit (§5).
7. **Sim-to-real.** The calibration pipeline is built and tested on twin experiments. It predicts how much bench time each parameter needs, and what the calibrated simulator will and will not predict (§8).

## 2. Forces at the nib

Full tables: [`pencil_mechanisms.md`](pencil_mechanisms.md) §2 (`analysis/pencil_mechanisms.py`, `results/pencil/mechanisms.json`).

Inputs:
- θ 50°, user force 1 N, nib friction μ 0.15, skid friction 0.12 (ASSUMPTION, EXP-Q01);
- axial nib spring F_c 0.15 N (ASSUMPTION, EXP-Q02).

The ink cannot tell which one carries the force, but the actuator can. All values CALC:

| Quantity | Pencil-form pen, nib carries the force | Skid architecture |
|---|---|---|
| Normal force at the nib | 1.00 N | 0.196 N (F_c / sin θ) |
| Load the stage must hold, tilt plane (N cos θ or F_c cot θ) | 0.643 N | 0.126 N |
| Design load per stage axis, worst stroke direction, with friction | **0.758 N** | **0.170 N** |
| Skid normal force / friction | — | 0.804 N / 0.097 N |
| Drag the fingers feel | 0.150 N | 0.126 N |
| Inertia and base-coupling forces at 8 Hz, 0.3 mm | < 1 mN | < 1 mN |

Findings:
- The static reaction dominates. The dynamic forces are under 4 % of it over the whole envelope (4–12 Hz, 0.1–1 mm).
- The stage load scales with F_c. The lowest nib force that still writes well (EXP-Q02) is therefore the most important number still to be measured.
- The skid carries force only when the user presses harder than N_nib, which is 0.196 N at 50°.
- The worst corner is 1.07 N per axis, at 35°, μ 0.35 and F_c 0.30 N. Friction amplifies the load there as cot(θ − atan μ).
- **Nib travel.** The nib must travel 2.3 mm axially to reach the paper from 35° to 75° and to follow the stage (2.4 mm configured). That requires a skid ring radius ≥ 1.4 mm (CAD).

## 3. Mechanisms with existing technology

Verdicts at the design load of 0.170 N per axis, for a usable correction of ±0.30 mm at the nib. Full table in [`pencil_mechanisms.md`](pencil_mechanisms.md) §3. MFR rows cite the ledger.

| Mechanism | What it can do in the 7.9 mm bore | Verdict |
|---|---|---|
| **Four custom 2.6 mm multilayer piezo plates, push-pull pair per axis** (PICMA technology, AMF-11), lever 1.363 | ±277 µm stroke under the design load; 0.329 N blocking force at the nib; 192 Hz first resonance; zero static hold power | **Recommended** (CALC) |
| Two 3.5 mm plates in an L | ±143 µm under load, 25 µm at −20 % tolerance, 0 µm at 35° | Fallback only |
| PL128.10 catalogue bender (6.15 mm wide) | Only one fits the bore | Bench part for a 1-axis rig |
| Other PL1xx benders; APA stacks (AMF-14) | 9.6–11 mm wide; 10.3 mm diagonal and 150 V | Do not fit |
| Moving-magnet voice coil (magpylib model at the bore) | K_m 0.080 N/√W: holding 0.170 N costs **2.4 W**, against 0.31 W allowed; about 0.1 h per charge | Reject (SIM) |
| Ultrasonic piezo motor (SQUIGGLE, AMF-15) | 1 M-cycle life is 35 h of assist at 8 Hz | Reject |
| SMA wire | Thermal pole 0.47 Hz, 17× too slow for 8 Hz; 1.6 % efficient | Reject |
| Gyroscope (3.3 g rotor at 50 000 rpm) | 32 µN·m against a 1.4 mN·m hand torque (2 %); does not resist translation | Reject |
| Reaction mass or active tuned-mass damper | 1–10 mN against 172 mN needed | Reject |
| 6 mm LRA (AMF-45) | Cannot move the nib; haptics only | Optional; the stage itself can cue (§7) |

The piezo stage wins because its static hold is capacitive. Every electromagnetic option fails on P = (F/K_m)², even behind the skid. The stroke budget is the weak point:
- ±162 µm at −20 % part tolerance and ±48 µm at 35° (CALC);
- tremor of 0.3 mm or more drives even a perfect controller onto the travel limit 16–65 % of the time (SIM).

## 4. Packaging (CAD)

`mechanics/cad/pencil_revP.py` builds the concept from `config/pencil.yaml` and writes `results/cad/pencil_revP{Q,L}_summary.json`, a STEP assembly and the viewer primitives. `mechanics/cad/pencil_drawing.py` draws the sections (`results/cad/drawing_pencil_revPQ.png`). Dimensions are nominal and parts rigid; the checks are geometric.

**Layout from the nib** (CAD P0.1.2, four-plate "Q" stage; z in mm from the ball, pen in contact at 50°):

| z (mm) | Part |
|---|---|
| 0 | ball of the D1-format gel refill |
| 1.2–1.6 | skid ring (PTFE-filled POM), contact radius 1.4 mm |
| 15–18 | front collar on the refill: PTFE liner, 1 mm magnet, 3-D Hall sensor in the nose wall |
| 18–23 | four C17200 decoupling leaves (30 µm × 1.2 mm, 5 mm free span) |
| 23–59 | four 2.6 × 36 × 0.67 mm piezo plates 2.55 mm off-axis: free length 28 mm, clamp 51–59; four PEEK snubber frames at z 28.6, 34.2, 39.8, 45.4 (gaps 237/157/91/46 µm) |
| 62 | flexure gimbal with a slide bushing: the refill pivots here and slides axially |
| 68–77 | soft nib spring (axial force F_c) and its seat |
| 78–120 | rigid-flex board: nRF54L15 CSP (AMF-44), IMU, piezo drivers, PMIC |
| 121–161 | 6.5 × 40 mm Li-ion cylinder, about 90 mAh (ASSUMPTION, AMF-42/43) |
| 161–166 | plastic cap (antenna window) |

The lever from collar to nib is 62/(62 − 16.5) = **1.363** (CALC).

**Results** (CALC, CAD):

| Check | Q: four 2.6 mm plates (baseline) | L: two 3.5 mm plates (fallback) |
|---|---|---|
| Mass before wiring, adhesive and margin | 12.2 g | 11.57 g |
| Piezo plates / cell / barrel | 1.96 / 3.45 / 2.72 g | 1.32 / 3.45 / 2.72 g |
| Centre of mass from the nib | 88.0 mm | 90.6 mm |
| Plate corner to bore, tips at the ±0.40 mm stops | 0.417 mm | 0.26 mm |
| Plate to plate | 0.515 mm | 0.215 mm |
| Plate to refill | 0.892 mm | 0.492 mm |
| Thinnest snubber web (needs ≥ 0.2 mm) | 0.488 mm | **0.088 mm** |
| Collar magnet to Hall face at full travel | 0.15 mm | 0.15 mm |
| Refill cone to skid aperture at 35° with full travel | 0.106 mm | 0.106 mm |
| Nib assembly swept through ±0.40 mm in 8 directions | no interference | no interference |
| All checks | **pass** | fail (snubber web) |

**Packaging findings:**
- **Plate width is capped by the bore.** Two 4.0 mm plates in an L collide at the corner and with the wall once the tips sweep to the stops. 3.5 mm (L) or four 2.6 mm plates (Q) fit. Only Q leaves room for snubber frames with a manufacturable web, which is a second reason Q is the baseline.
- **Three changes from the mechanism analysis are in the CAD** ([`pencil_mechanisms.md`](pencil_mechanisms.md) §4):
  - the leaves need a 5 mm free span, so the plates moved 4 mm rearward and the gimbal to z = 62 mm;
  - the snubbers are needed for drop survival;
  - the collar bore is PTFE-lined to keep the nib-force band to ±0.03 N.
  The compliant nose is not designed yet.
- **Skid ring radius 1.4 mm.** At 35° the refill cone plus ±0.40 mm travel otherwise leaves only 0.026 mm to the aperture.
- **Mass has margin; balance does not.** About 12 g leaves 7–8 g for wiring, grip features and margin under the 20 g target. The centre of mass sits at 53 % of the length because the cell is at the back. Swapping cell and board would move it about 8 mm forward (CALC).

## 5. Recording on paper in a pencil envelope

Options found (MFR):
- Rev A's near-nib optical navigation module (PAA5100JE with lens, 6 × 6 × 3.08 mm; OPT-05) does not fit the pencil nose.
- Camera pens that read dot-pattern paper are 10.4–11.5 mm in diameter (Neo smartpen M1+ and N2, OPT-10/11; Nuwa, OPT-13). The Neo N2 camera samples at 120 per second.
- The smallest camera found, OVM6948, does fit: 0.65 × 0.65 × 1.16 mm, 200 × 200 px, but **30 fps** (OPT-36).

How fast must the page sensor be? The M1 guided mode estimates the housing position as the last page-sensor sample plus the IMU-integrated motion since then. Sweeping rate and latency (latency = one frame + 2 ms, ASSUMPTION) on the feature course with 6 Hz, 0.3 mm tremor (SIM, `sim/diag_page_sensor_rate.py`, `results/sim/page_sensor_rate.json`):

| Page sensor | Guided path error, RMS | Relative to no correction (322 µm) |
|---|---|---|
| 30 Hz, 35 ms | 243 µm | 0.76 |
| 60 Hz, 19 ms | 167 µm | 0.52 |
| 120 Hz, 10 ms | 137 µm | 0.42 |
| 250 Hz, 6 ms | 125 µm | 0.39 |
| 1 kHz, 3 ms | 125 µm | 0.39 |
| 1 kHz, 2 ms (parameter default) | 139 µm | 0.43 |

**Requirement (proposed): page sensor ≥ 120 Hz with ≤ 10 ms latency, fused with the IMU.** At 30 fps, two-thirds of the guided-mode benefit is lost.

The 1 kHz rows are not monotonic in latency. The alignment of optical and IMU delays in the fusion matters at the 10 % level, which is an open point for the estimator.

No existing part meets the requirement inside 8.9 mm, so capture on paper is a development item. The candidates are:
- a faster chip-scale camera with dot-pattern paper, as a partner development;
- a custom near-nib optical flow sensor (EXP-S01).

Tablet capture through an active-stylus protocol is the fallback product path. There the correction acts on glass and the digital ink can be corrected in software anyway.

## 6. AI prediction, guidance and autocorrect

Source: [`ai_guidance.md`](ai_guidance.md) (`aiguide/`, `app/penapp/autocorrect.py`, `results/ai/`). The data are synthetic: glyph-font writers with synthetic tremor, and CC0 text from Tatoeba. No person was recorded.

**What "autocorrect" can mean for a pen.** The physical correction is bounded by the stage travel (±0.30 mm usable) on letters 2–4 mm tall. The pen can reshape strokes; it cannot change a letter into another letter. So there are two layers:
1. **Physical micro-guidance.** The app predicts the next letters, draws them in the user's style and sends them to the pen as templates. Guided mode pulls the nib toward them, with authority scaled by the prediction's confidence (ICD §5 rule 5) and bounded by the travel.
2. **Digital autocorrect.** It works on the recognised text and has no bound. It is written as a derived layer that cites stroke ids; the original ink is never changed (DEC-017).

**Prediction** (CALC, held-out text):
- Next character: 61 % top-1, 81 % top-3, calibration error 0.006.
- The template must reach the pen before the nib lands on the letter, so the phone has to predict **two letters ahead** within a 0.3 s lead (latency budget 182 ms, allocated). Two letters ahead is right only 40 % of the time, and 19–32 % on note-like text.
- A correctly predicted letter drawn in the user's estimated style is still about **300 µm RMS** from what they meant (SIM, 24 writers). The writer's own earlier letters give a floor of 239 µm.

**Physical guidance on free writing** (SIM; path error, µm RMS; M1 plant with Rev A and pencil-like limits, 6 writers × 4 tremor frequencies):

| Condition | Rev A limits | Pencil-like limits |
|---|---|---|
| No guidance | 209 | 176 |
| Oracle template (the true intended path) | 167 | 158 |
| AI template, letter predicted correctly | 234 | 182 |
| AI prediction, confidence-gated | 217 | 177 |
| Wrong letter at full authority | 253 | 184 |

What the table shows:
- **Break-even.** Guidance stops helping once the template is 230–330 µm from the intended path. Realistic AI templates sit right at that break-even, so they give **no net benefit on free handwriting**.
- **Oracle templates do help.** They reduce letter-level error by 10–26 %, and by up to 63 % on slow shapes such as a circle. Physical guidance is useful when the template is **known**: tracing, copying set text, drawing aids.
- **Wrong predictions are safe.** The stage stays within its stops. At most 1.9 % of letters read as the wrongly predicted letter, and the next word is not disturbed.
- **Micrographia is not restored physically**, in line with COR-10 and DEC-002.

The M1 runs lack the pencil's skid and piezo stage. A rerun on the pencil model P1 is in progress and will be added here.

**Digital autocorrect** (CALC; injected recognition errors; threshold 0.9):
- At a character error rate of about 7 %, word error falls from **32 % to 10 %** on held-out sentences and from **30 % to 16 %** on note-like lines.
- Correct words are changed in ≤ 0.1 % of cases.
- Names and rare words are the failure mode: 6–14 % are wrongly changed until a personal dictionary is added, and then 0 %.
- Corrected words can be re-drawn in the user's own handwriting as a derived drawing.

**Deployment.** The pen MCU runs the guided core, the template buffer with its checks and an optional stroke predictor (7.8 k MAC). The phone runs recognition, prediction, style synthesis and autocorrect. Templates add 0.3 kB/s over BLE. A proposed ICD record 0x06 (template segment with validity window and confidence) and pen-side rules T1–T8 are in `ai_guidance.md` §7, not yet in `docs/icd.md`.

**Freedom to operate.** The template pipeline (recognition → characters → shapes → commands to the pen) is structurally close to claim 15 of BIC's US 12,026,327 B2 (PAT-01). Attorney review is needed before any guided-letter feature. This is not legal advice.

**Recommendation** (from the study):
- Ship the digital layer first: autocorrect, personal dictionary and re-rendering.
- Use physical guidance where the template is known.
- Do not claim AI-predicted physical correction of free writing unless a study with people (EXP-A02) shows their intended letters sit closer than about 250 µm to a personal template.

## 7. Power and battery

90 mAh, 3.7 V, 80 % usable = 0.266 Wh (ASSUMPTION). Electronics are 65 mW, including a 50 mW optics placeholder (ASSUMPTION). Source: [`pencil_mechanisms.md`](pencil_mechanisms.md) §5 (SIM, model P1).

| Mode | Two DRV2700 drivers (prototype, AMF-16) | Charge-recovery driver (product) |
|---|---|---|
| Recording only | 65 mW, **4.1 h** | 65 mW, **4.1 h** |
| Tremor assist, full correction, 6 Hz, Hall noise 1 µm | 320 mW, **0.83 h** | 97 mW, **2.7 h** |
| Guided assist, 6 Hz tremor | 389 mW, 0.69 h | 111 mW, 2.4 h |
| Tremor assist with Hall noise 0.3 µm | 216 mW, 1.2 h | 80 mW, **3.4 h** |

Drivers and sensor noise:
- The DRV2700's quiescent draw (72 mW for two) makes it a bench part. The product needs a charge-recovery stage behind a low-Iq boost (AMF-47 class), or an energy-recovery driver qualified for 2–2.6 µF per axis.
- The BOS1921/1931 datasheet states its limit as a 5.3 kΩ load impedance at 190 Vpp (AMF-46, lead-verified). Our 2.6 µF plates at 12 Hz present 5.1 kΩ, so the tremor band may be within its envelope. That is a vendor check (EXP-Q05).
- Hall-sensor noise is converted into drive power by the damping loop. The target is ≤ 0.3 µm at 10 kSPS.

Barrel temperature stays ≤ 37.4 °C in every mode (CALC).

## 8. Sim-to-real (pending: `sim_to_real.md`)

## 9. What to make, what to buy, what to do

**Buy:**
- D1-format low-force refills, selected by EXP-Q02;
- PL128.10 benders for the 1-axis bench rig;
- DRV2700 evaluation modules;
- a 3-D Hall sensor and magnet;
- nRF54L15;
- an IMU;
- Panasonic CG-425A cells as the fallback battery.

**Make, or have made to our drawing:**
- four custom 2.6 × 36 × 0.67 mm multilayer plates, as a supplier custom part;
- the mechanical parts:
  - C17200 leaves;
  - Ti collar with a PTFE liner;
  - etched cross-strip gimbal with a slide bushing;
  - PEEK snubber frames;
  - POM-PTFE skid ring and a compliant nose;
  - PA-GF30 barrel over a stainless tube;
- a rigid-flex HDI board;
- a custom 6.5 × 40 mm cell;
- the charge-recovery piezo driver;
- the page sensor for paper (§5).

**Firmware.** The Rev A control core keeps its structure. `servo.c` already outputs a tip-equivalent force. Only `current_loop.c` and the coil model in `thermal.c` are coil-specific. The pencil replaces them with a piezo drive module, with these changes:
- the drive module maps force to voltage through the blocked force per volt, with slew and voltage limits;
- it watches for bender cracks through a capacitance plausibility check;
- the servo moves to 10 kHz with measurement damping;
- the estimators, fusion, guided mode and ML guard carry over.

**Experiments, in order** (from [`pencil_mechanisms.md`](pencil_mechanisms.md) §9; new ones are EXP-Q):
1. EXP-Q01: skid friction (tribometer).
2. EXP-H03: skid feel, smear and passive tremor. This is the existing blinded study that gates DEC-008.
3. EXP-Q02: low-force ink line quality. It sets F_c.
4. EXP-Q04: bender characterisation and strength (stroke, blocking force, hysteresis, creep, capacitance, tip load to failure on diced 2.6 mm plates, drop with and without snubbers).
5. EXP-Q05: driver efficiency and quiescent power on 2–2.6 µF.
6. EXP-Q03: cell pulse discharge.
7. EXP-Q06: loaded 1-axis rig (PL128.10, D1 refill, skid nose) on the stage-A rig, with the EXP-B09 cancellation protocol.
8. EXP-Q07: 2-axis demonstrator in a 7.9 mm bore. It gates Rev P1.
9. The claims studies: EXP-H01/E01 (separability), EXP-H02 (form factor), EXP-H06.

## 10. Open risks

1. **Stroke margin.** The margin is thin:
   - ±277 µm nominal, but ±162 µm at −20 % part tolerance and ±48 µm at 35°;
   - large tremor saturates the stage even with perfect intent.

   The pencil suits small tremor and guided writing.
2. **Intent separation.** It is unchanged from Rev A. The Kalman estimator helps only at 8 Hz and above with tremor of 0.3 mm or more (ratio 0.85–0.92), and it adds error on small tremor. Free-writing tremor cancellation still waits on EXP-H01/E01. Guided writing toward a known or predicted template is the credible first use (§6).
3. **Drop survival.** Without snubbers and a compliant nose the plates fracture in a sideways 1 m drop. The PICMA material and diced-edge strength are unknown (EXP-Q04).
4. **Driver.** No catalogue part is both low-power and rated for 2–2.6 µF. Until one is qualified, assist time is under 1.5 h.
5. **Paper capture.** No sensor that fits meets ≥ 120 Hz at ≤ 10 ms latency (§5).
6. **Feel.** Behind the skid, the pen writes differently: 116 µm of device distortion comes from the skid's contact and drag alone (SIM). EXP-H03 decides whether users accept it.
7. **Assumed, not measured:**
   - servo rate and Hall sampling (10 kHz);
   - stage damping;
   - piezo hysteresis (12 %);
   - skid contact values;
   - the hand model, which was measured in-plane without the hand resting on the paper (HAP-26).
