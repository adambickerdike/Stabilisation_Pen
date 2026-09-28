# Pencil-class concept (Rev P0)

**Status: proposed design.** Every number here is a calculation, a simulation, or a manufacturer statement with a ledger id; none is a measurement of our hardware. Evidence labels: **CALC**, **SIM**, **MFR** (manufacturer statement, `docs/evidence.csv` id), **ASSUMPTION**.

Parameters: `config/pencil.yaml` (overlay on `config/parameters.yaml` v0.4.4).
Detailed reports:
- [`pencil_mechanisms.md`](pencil_mechanisms.md): forces, mechanisms, power, pencil simulation;
- [`ai_guidance.md`](ai_guidance.md): prediction, guidance, autocorrect;
- [`sim_to_real.md`](sim_to_real.md): calibration and twin experiments;
- [`inertial_stabilisation.md`](inertial_stabilisation.md): weights, gyroscopes and pivots in the cap, the grip and at the paper;
- [`sensor_fusion_ai.md`](sensor_fusion_ai.md): the accelerometer, the tremor tracker and AI in the estimator.

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
2. **The pencil works if the writing force bypasses the nib.** A skid ring on the nose grounds the user's force to the barrel (DEC-008 candidate D). The nib is pressed on by a light axial spring, so the stage only carries F_c·cot θ plus friction. At F_c = 0.15 N that is 0.126 N, or 0.170 N in the worst stroke direction, against 0.758 N for a conventional nib (CALC).
3. **The stage is piezo, not a coil.** A piezo bender holds a static load at almost no power. Four custom 2.6 mm multilayer plates (PICMA technology, AMF-11) fit around a D1 refill in the 7.9 mm bore. Under the design load they give ±277 µm of stroke and 0.329 N at the nib, with a 192 Hz first resonance (CALC). The best voice coil that fits needs 2.4 W to hold the same load (SIM). CAD: 12.2 g before wiring and margin, and no interference at full travel (§3, §4).
4. **What the ink can gain is bounded.** The usable correction is about ±0.3 mm at the nib (±277 µm under load). With perfect knowledge of intent the pencil cuts the ink error to 0.19–0.26 of the uncorrected value for 0.1 mm tremor. It reaches 0.20–0.46 at 0.3 mm, where it hits its travel limit (SIM). With the pen's own tremor estimator it achieves 0.85–0.92, and only at 8–12 Hz; at lower frequencies it cannot tell tremor from writing. That estimator is the same open problem as in Rev A (§3, §10).
5. **AI autocorrect works digitally, not physically.** In the app, a language-model corrector cuts word errors from 32 % to 10 % at a 7 % recognition error rate. It changes ≤ 0.1 % of correct words and leaves the original ink untouched (CALC). Physically, the pen can pull the nib toward an AI-predicted letter drawn in the user's style. But such a template is itself about 300 µm off, which is right at the 230–330 µm break-even. So AI templates give no net benefit on free handwriting, although wrong predictions are safely bounded by the travel (SIM). Physical guidance pays off when the template is known, as in tracing, copying or drawing aids (§6).
6. **Recording on paper needs a new sensor.** Nothing off the shelf fits the nose. The simulation sets the requirement: a page sensor of ≥ 120 Hz with ≤ 10 ms latency, fused with the IMU. The chip-scale camera that does fit runs at 30 fps and loses most of the guided-mode benefit (§5).
7. **Sim-to-real is ready before the hardware.** A calibration pipeline follows the bench protocols. On 15 blind simulated plants it recovers every model parameter to ≤ 1.6 % in about 1.5 h of bench time per build. The calibrated twin then predicts the physical-limit ratio within ±0.1 for 14 of 15 plants, against 4–5 uncalibrated. The same work found that the frozen tremor estimator is fragile across plants, and that the existing Monte Carlo lets the simulated controller see true plant values (§8).

8. **Weights and gyroscopes in the cap do not help; the nib stage stays the only physical corrector.** A hand–pen model with the pen tilting in the grip tested moving and tuned masses, gyroscopes, control-moment gyroscopes and reaction wheels in the cap, a motorised grip sleeve and passive pivots. With perfect knowledge of the tremor:
   - the best that fits the 20 g target leaves 0.85–0.97 of the ink error at 0.3 mm and takes half the cell;
   - the strongest (gyroscope pairs) leaves 0.87–0.92, at 25 g and 0.34 W;
   - the stage alone leaves 0.18–0.43.

   The grip passes about 0.17 N of tremor force and a cap device can push back with 2–30 mN (SIM, CALC, §11, DEC-024).
9. **The accelerometer now drives the tremor tracker, and AI helps most by personalising it.**
   - A Kalman filter reading the 6-axis IMU directly, with gyroscope compensation of the pen's rotation, leaves 0.78 of the tremor-band ink error, against 0.85 for the previous filter.
   - Set by a 20 s calibration per writer, it leaves 0.58–0.71 at 8–12 Hz (0.3 mm).
   - AI letter predictions do not help the tracker: they are off by as much as the tremor, at the same frequencies.
   - Separating tremor from writing, not sensing, is still the limit (SIM, §11, DEC-025).

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

**Physical guidance on free writing** (SIM; path error to the intended letters, µm RMS, 6 synthetic writers × 4 tremor frequencies). The main result is on the pencil model P1, with the skid, the spring-loaded refill and the piezo stage. "Writing only" leaves out the touchdown and lift tails described below. The M1 columns keep the Rev A plant for comparison.

| Condition | P1, all ink | P1, writing only | M1, Rev A limits | M1, pencil-like limits |
|---|---|---|---|---|
| No guidance | 243 | 196 | 209 | 176 |
| Oracle template (the true intended path) | 213 (−12 %) | 155 (−21 %) | 167 | 158 |
| AI template, letter predicted correctly | 265 (+9 %) | 222 (+13 %) | 234 | 182 |
| AI prediction, confidence-gated | 249 (+2.5 %) | 204 (+4 %) | 217 | 177 |
| Wrong letter at full authority | 274 (+13 %) | 234 (+20 %) | 253 | 184 |

What the table shows:
- **Break-even.** Guidance stops helping once the template is 265 µm from the intended path in P1, and 230–330 µm in M1. A correctly predicted letter in the user's style is about 300 µm off, so realistic AI templates give **no net benefit on free handwriting**. Even a perfect template barely changes legibility (recognition +0.00 to +0.02).
- **Oracle templates do help the path.** On slow shapes the gain is larger: circle 348 → 174 µm on P1's feature course. Physical guidance is useful when the template is **known**: tracing, copying set text, drawing aids.
- **Wrong predictions are safe.** The stage reaches its 0.40 mm stop and no further, and the ink moves at most 0.51 mm from the unguided run. 2.2 % of letters newly read as the wrong letter at full authority, and 0.3 % when gated. The next word is not disturbed.
- **Micrographia is not restored physically**, in line with COR-10 and DEC-002.

**Touchdown and lift tails: a finding for the mechanism.** The AI rerun on P1 showed that the pen draws a tail each time the nib lands and each time it lifts (SIM).
- **Cause.** The refill's front stop covers the whole tilt range. At 50° the unloaded refill therefore stands 1.34 mm proud of where it writes. The ball lands first and slides by up to 1.34 × cos 50° ≈ 0.86 mm while the refill retracts, and does the same in reverse at lift.
- **Size.** Measured against a rigid pen on the same writing, this adds about **1.1 mm of ink per stroke**. It distorts letters more than the tremor does: unguided recognition is 0.79 with the tails and 0.93 without.
- **Mitigation tested:** a front stop that follows the tilt, at the protrusion the current tilt needs plus a margin (`sim/pencil/diag_touchdown_tails.py`, `results/pencil/touchdown_tails.json`; SIM, 4 seeds; tilt constant, so tracking is perfect):

| Front stop | Extra ink per stroke, against a rigid pen | Missing ink per stroke | Correction ratio, perfect intent, 6 Hz 0.3 mm |
|---|---|---|---|
| Tilt-range stop (P0.1.2) | 1.15 mm | 0.01 mm | 0.24 |
| Tilt-adaptive, 0.30 mm margin | 0.33 mm | 0.01 mm | 0.30 |
| Tilt-adaptive, 0.20 mm margin | 0.28 mm | 0.01 mm | 0.45 |
| Tilt-adaptive, 0.10 mm margin | 0.31 mm | 0.09 mm | 0.69 |

"Extra" is ink more than 0.2 mm from anything the rigid pen drew, divided by the rigid pen's stroke count. It includes short bridges where a quick lift no longer leaves the paper, which is why fewer pen-downs are registered with the adaptive stop. "Missing" is rigid-pen ink the pencil did not draw.

- **The margin cannot be small.** The refill must also slide q·cot θ while the stage corrects in the tilt plane (±0.25 mm at 50°). About **0.3 mm** is the working margin:
  - it cuts the extra ink about 3.5-fold and keeps most of the correction;
  - at 0.1 mm the pen starts to lose ink.
- **How to build it.** A slow trim actuator can set the stop from the IMU's tilt. A SQUIGGLE-class screw motor fits (2.8 × 2.8 × 6 mm, holds with power off; AMF-15). It was rejected as the tremor actuator because 1 M cycles last 35 h at 8 Hz, but tilt tracking uses only a few cycles a minute.
- **Remaining.** About 0.3 mm of extra ink per stroke is still visible. Two firmware options could remove it: stage compensation of the axial slide during touchdown (Rev A's M1 has one; P1 does not) and an ink-aware touchdown profile. Both are untested.

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

## 8. Sim-to-real

Sources:
- [`sim_to_real.md`](sim_to_real.md), the report;
- [`../validation/sim_to_real.md`](../validation/sim_to_real.md): bench workflow, data formats, gap metrics G1–G9 and the hardware-in-the-loop plan;
- `s2r/` (22 tests) and `results/s2r/`.

These are **twin experiments**. Hidden "true" plants, some outside the declared ranges, are measured through models of the instruments the protocols name. The identification sees only the recorded data. This shows that the method works and what it costs. It cannot show that the simulator's structure is right about a real pen; only the bench can (SIM, CALC).

**Calibration pipeline**, run in protocol order (EXP-B03 → B05 → B01/B02) on 15 blind plants:
- **Recovery.** Every model parameter is recovered to ≤ 1.6 % at the 95th percentile: K_f 0.9 %, m_eq 1.4 %, μ_k 1.2 %, paper stiffness 1.6 %. The stated uncertainties cover the truth for 93–100 % of plants.
- **The exception** is the Stribeck speed. It cannot be identified when the friction curve has no dip, and its uncertainty says so.

**Bench time for that accuracy:**
- about 15 min per actuator coupon;
- about 40 min per stage build;
- about 33 min per ink × paper × underlay.

That is about 1.5 h per build against 2.5 h at the protocol settings. The accuracy floor is instrument calibration (force-sensor gain, vibrometer scale, bath temperature), not test duration. K_f needs the back-EMF method (uncertainty 2.3 % → 1.0 %).

**How well a calibrated twin predicts the plant:**

| Prediction | Uncalibrated | Calibrated (B03, B05, B01/B02; hand simulant known to ±10 %) |
|---|---|---|
| Oracle ratio within ±0.1 (AC-B09-03) | 4–5 of 15 plants | **14 of 15** |
| Kalman ratio at 9 Hz within ±0.1 | 5 of 15 | 9 of 15 (14 of 15 once the sensor parameters, EXP-S01/B04, are identified) |
| Static hold power | — | within 2.3 % |
| No-correction ink error | — | within 15 % |
| Writing distortion | — | only within a factor of 2 |

What the twin experiments also found:
- **Model-form diagnostics.**
  - Each missing effect the study planted is flagged by a different mix of residual tests: a flexure mode, extra delay, pivot friction, backlash, friction memory, and a hand resting on the paper.
  - The correct model passes all of them.
  - Two existing criteria miss most of these defects and should be replaced: resonance within ±10 % (AC-B05-01) and friction-model R² (AC-B02-01).
- **Pencil piezo stage.** Hysteresis is manageable:
  - An inverse model fitted from one 8 s sweep tracks a 0.2 mm sine to 2.8–3.1 % open loop, against 7 % for a linear gain.
  - With Hall feedback it tracks to 0.5–1.6 %.
  - Under a 0.1 N nib load the drive saturates at 30 V. That is a stroke-budget problem, consistent with §3.
- **Estimator robustness.**
  - The frozen Kalman set degrades from a ratio of 0.70 on the nominal plant to a median of 0.88 on randomised held-out plants; 7 of 16 meet AC-B09-04.
  - A set tuned on randomised plants (the v0.4.1 one) is better on 15 of 16.
  - Estimator selection should be done on randomised plants under fixed firmware (DEC-009 revisit).
- **A flaw in the existing Monte Carlo.** When `sim/run_sweeps.py` varies a plant parameter, the simulated controller receives the true value as well. Real firmware keeps the constants it was generated with. Under fixed firmware, K_f and k_tip rank 2nd and 3rd for the Kalman ratio at 9 Hz; the existing sensitivity file ranks them last. `s2r/twin.py` separates the two. The simulator split is proposed (`sim_to_real.md` §8, items 12–13).

**Hardware in the loop.** `validation/sim_to_real.md` §7 specifies running the real MCU against M1 as the plant. It needs the core split into a plant step and a controller tick (item 12).

## 9. What to make, what to buy, what to do

**Buy:**
- D1-format low-force refills, selected by EXP-Q02;
- PL128.10 benders for the 1-axis bench rig;
- DRV2700 evaluation modules;
- a 3-D Hall sensor and magnet;
- nRF54L15;
- a 6-axis IMU (LSM6DSV16X class; accelerometer and gyroscope both used by the tremor tracker, §11);
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
- the fusion, guided mode and ML guard carry over; the frozen Kalman estimator is replaced by the acceleration-domain Kalman filter with gyroscope compensation and a per-user calibration (§11, DEC-025).

**Experiments, in order** (from [`pencil_mechanisms.md`](pencil_mechanisms.md) §9; new ones are EXP-Q):
1. EXP-Q01: skid friction (tribometer).
2. EXP-H03: skid feel, smear and passive tremor. This is the existing blinded study that gates DEC-008.
3. EXP-Q02: low-force ink line quality. It sets F_c.
4. EXP-Q04: bender characterisation and strength (stroke, blocking force, hysteresis, creep, capacitance, tip load to failure on diced 2.6 mm plates, drop with and without snubbers).
5. EXP-Q05: driver efficiency and quiescent power on 2–2.6 µF.
6. EXP-Q03: cell pulse discharge.
7. EXP-Q06: loaded 1-axis rig (PL128.10, D1 refill, skid nose) on the stage-A rig, with the EXP-B09 cancellation protocol.
8. EXP-Q07: 2-axis demonstrator in a 7.9 mm bore. It gates Rev P1.
9. EXP-Q08 (new): touchdown and lift tails. Measure the ink at pen-down and pen-up on the EXP-Q06 rig with the tilt-range stop, then with a tilt-adaptive stop (a SQUIGGLE-class trim motor driven by the IMU tilt) at 0.2–0.4 mm margin. Compare with a rigid reference pen on the same robot paths (extra and missing ink per stroke) and include the correction ratio.
10. The claims studies: EXP-H01/E01 (separability), EXP-H02 (form factor), EXP-H06.
11. From §11: EXP-I01 (how the grip gives, inside EXP-B06), EXP-I02 (rotational share of tremor, inside EXP-H01) and EXP-I03 (passive nose and grip options, with EXP-H03). EXP-I04 runs only if EXP-I01 calls for it. Add IMU latency to EXP-S01 and superimposed vibration to EXP-B01/B02.

## 10. Open risks

1. **Stroke margin.** The margin is thin:
   - ±277 µm nominal, but ±162 µm at −20 % part tolerance and ±48 µm at 35°;
   - large tremor saturates the stage even with perfect intent.

   The pencil suits small tremor and guided writing.
2. **Touchdown and lift tails.** With the tilt-range front stop, the ball slides up to 0.86 mm at every touchdown and lift. That adds about 1.1 mm of ink per stroke against a rigid pen (SIM, P1), and it matters more for legibility than the tremor. A tilt-adaptive stop with a 0.3 mm margin cuts it to 0.33 mm, at a small cost in correction. It needs a slow trim actuator and firmware, and what remains is still visible (§6).
3. **Intent separation.** It remains the main limit.
   - The accelerometer tracker (§11) leaves 0.78 of the tremor-band error on average, and 0.58–0.71 at 8–12 Hz once calibrated per writer. It no longer adds error on small tremor.
   - At 4–6 Hz no tracker separates tremor from writing.
   - Sharp, fast writing is misread as tremor unless the robust setting is used, and that setting gives up most of the gain.
   - Free-writing tremor cancellation still waits on EXP-H01/E01.
   - Guided writing toward a *known* template (tracing, copying, drawing aids) is the credible first use. AI-predicted templates did not help on free writing, neither as a pull nor as a hint to the tracker (§6, §11).
4. **Drop survival.** Without snubbers and a compliant nose the plates fracture in a sideways 1 m drop. The PICMA material and diced-edge strength are unknown (EXP-Q04).
5. **Driver.** No catalogue part is both low-power and rated for 2–2.6 µF. Until one is qualified, assist time is under 1.5 h.
6. **Paper capture.** No sensor that fits meets ≥ 120 Hz at ≤ 10 ms latency (§5).
7. **Feel.** Behind the skid, the pen writes differently: 116 µm of device distortion comes from the skid's contact and drag alone (SIM). EXP-H03 decides whether users accept it.
8. **Assumed, not measured:**
   - the pen's rotation in the grip (ρ = 0.5) and the IMU's latency (1.4 ms);
   - servo rate and Hall sampling (10 kHz);
   - stage damping;
   - piezo hysteresis (12 %);
   - skid contact values;
   - the hand model, which was measured in-plane without the hand resting on the paper (HAP-26).
9. **Friction under vibration.** In the pencil model most of the tremor-induced ink error is a slow drift: the tremor makes the skid and nib slide more freely (§11.3). If real friction behaves differently, every estimator's result moves. EXP-B01/B02 with superimposed vibration decide it.
10. **Grip mechanics.** How much the pen tilts rather than slides in the fingers (r_rot) is unmeasured. It decides whether anything in the cap could ever matter (EXP-I01), and how much pen rotation the IMU must compensate (EXP-I02).

## 11. Accelerometer, AI and inertial help (added 2026-09-28)

The request was for accelerometer data, pivot or inertial stabilisation ("3-axis side-to-side") in the grip or the cap, and a combination of AI and physical help. Two studies answer it:
- [`inertial_stabilisation.md`](inertial_stabilisation.md): hand–pen model H1, `sim/handpen/`;
- [`sensor_fusion_ai.md`](sensor_fusion_ai.md): `fusion/` on model P1.

Both are simulation and calculation on synthetic writing and tremor; nothing was measured.

### 11.1 Physical help: where it can come from

| Where | What was tested | Best result with perfect knowledge of the tremor (0.3 mm, 4–12 Hz) | Cost | Verdict |
|---|---|---|---|---|
| Nib (current design) | Piezo stage moving the refill behind the skid | 0.18–0.43 of the ink error left | in the CAD | **Keep: the only element with the authority** |
| Cap | Tungsten slug pushed on 3 axes (best within 20 g) | 0.85–0.97 alone; 0.17–0.31 with the stage | half the cell; 0.002–0.48 W | reject |
| Cap | Two pairs of control-moment gyroscopes | 0.87–0.92 alone; 0.13–0.29 with the stage | 25 g, 0.34 W, no cell | reject |
| Cap | Passive gyroscope, tuned mass, heavier cap, reaction wheels | 0.78–1.07 | – | reject |
| Grip | Motorised sleeve (Liftware-style) | at most the stage's authority | holds 0.74 N: 2.1 W, grip ≥ 15 mm | reject |
| Grip, paper | Soft sleeve, more skid friction, damped nose | tremor 0.36–0.96 of the pen as designed, but net error against the intended writing 0.93–1.25 | drag up to 2.5× | reject for tremor |

Why:
- **Cap devices lack force.** The grip passes about 0.17 N of tremor force at the nib, while a few grams moving ±1 mm in the cap push with 2–30 mN.
- **A gyroscope resists only rotation,** and the pen tilts just 0.8–2.2 mrad in the grip.
- **Passive pivots cannot choose what they filter.** Handwriting strokes (3–7 Hz) and tremor (4–12 Hz) share frequencies, so every passive filter shrinks and delays the letters about as much as it removes tremor.
- **Recommendation (DEC-024).** Nothing inertial in the cap. Skid friction stays near 0.1–0.15. If a user group's tremor saturates the stage, give the stage more travel.
- **What to measure.** The grip's split between sliding and tilting (EXP-I01) could reopen the cap line, but only if tilting dominates (r_rot ≥ 0.6). Resting the hand on the paper is the one cheap "pivot" worth testing (EXP-I03).

### 11.2 Sensing: what the accelerometer does

- **It is used directly now.** The board's 6-axis IMU (LSM6DSV16X class, 60 µg/√Hz, MFR OPT-37) is read through its FIFO at about 2 kHz into an acceleration-domain Kalman filter (AKF). The filter tracks intended motion, a tremor oscillator with a harmonic, and the accelerometer bias. It applies late page-sensor samples by rolling back, and its output passes a low-pass whose delay is predicted ahead.
- **Noise is not a limit.** Every candidate resolves 0.1 mm of tremor at 4 Hz with an SNR of 25–76 (CALC). A part with three times the noise gave the same result (SIM).
- **It is fast.** About 1.4 ms from motion to the estimate, against 2–10 ms plus a frame for the page sensor (ASSUMPTION built on MFR OPT-37/40; EXP-S01 measures it).
- **Pen rotation must be compensated.** The IMU sits about 100 mm from the nib, so wrist tremor that tilts the pen spoils its reading of the nib: 36–58 % tremor-band error at the assumed rotation (ρ = 0.5). The gyroscope in the same chip brings that to 2–4 %. A nose accelerometer (BMA530 class, 1.2 × 0.8 mm) is needed only if EXP-I02 finds ρ ≥ 1 (SIM).
- **Output jitter near the stage's 192 Hz resonance is harmful.** 5 µm of 200–900 Hz noise in the command costs more than the whole tremor-band gain and quadruples the drive power (SIM). The previous filter, which has no such low-pass, drew 203 mW on the grid against 132–138 mW for the new ones.

### 11.3 Estimation: what the tracker achieves

Ink error left in the tremor band, as a fraction of no correction (pencil model P1, test seeds 200–203; SIM):

| Tracker | 0.3 mm at 8 / 10 / 12 Hz | Mean over 4–12 Hz, 0.1–0.5 mm | Moves tremor-free writing (smooth / sharp writers) |
|---|---|---|---|
| Previous filter (Kalman on the page position, frozen) | 0.58 / 0.49 / 0.54 | 0.85 (adds error at 0.1 mm: 0.93–1.09) | 34 / 123 µm |
| AKF tuned on smooth writing | 0.61 / 0.56 / 0.57 | 0.78 | 21 / 146 µm |
| AKF robust setting (default) | 0.90 / 0.82 / 0.77 | 0.91 | 5 / 21 µm |
| **AKF set by a 20 s calibration** | **0.71 / 0.61 / 0.58** | **0.80** | 20 µm / not tested |
| Perfect knowledge of the tremor band (limit) | 0.18 / 0.19 / 0.25 | 0.26 | – |

- **The limit is separation, not sensing.** Every tracker is near 1.0 at 4 Hz and gains little at 6 Hz (0.82–1.0 at 0.3 mm), where tremor and strokes overlap most. The best new trackers gain most at 8–12 Hz and 0.5 mm: 0.44–0.47.
- **Writing that looks like tremor is the main risk.** Sharper writers (the aiguide glyph writers, 3–4× more intended motion in 3–15 Hz) made the smooth-tuned filters move tremor-free ink by 123–146 µm. The robust setting keeps it to 21 µm by learning the tremor amplitude only during slow motion, and gives up most of the gain. Real writing of the target groups (EXP-H01) decides which setting ships.
- **In this model most of the "disturbance" is friction, not tremor.** The tremor makes the skid and nib slide more freely, so the pen follows the hand differently. That slow part (316 µm below 3 Hz, against 173 µm in 3–15 Hz) cannot be told from writing. Cancelling it moves the ink away from the intended letters: with perfect knowledge of the whole disturbance the ink is 283 µm from the intended path, against 258 µm uncorrected and 225 µm with perfect tremor-band knowledge. Friction under vibration is therefore the biggest open model question (EXP-B01/B02).
- **The learned network** (GRU, trained on the simulator) reaches 0.69 on the headline ratio, but moves the ink further from the intended letters (282 µm). It learned the simulated pen's friction behaviour. It stays behind the ICD §5 guard (DEC-016).

### 11.4 AI and physical help together

| AI element | Where it runs | Effect (SIM, CALC) | Status |
|---|---|---|---|
| Personal calibration: 20 s of drawing known shapes sets the tracker's frequency window, gates and noise levels | phone (seconds), then CAL_USER to the pen | tremor-band error at 8–12 Hz, 0.3 mm: 0.58–0.71 against 0.77–0.90 for the population setting | **ship** (proposed CAL_USER v3 fields) |
| Known-template guidance: tracing, copying set text, drawing aids | phone makes the template; pen pulls the nib within its travel | path error to the no-tremor level (155 µm against 196 µm uncorrected) | **ship for known templates** (DEC-020) |
| Digital autocorrect, recognition, search, re-rendering | phone | word errors 32 % → 10 % at 7 % recognition errors; ink never changed | **ship** (DEC-020) |
| Letter prediction as a hint inside the tracker (prior) | pen, with templates from the phone | no change (193 µm with or without any template), because a correctly predicted letter in the writer's style is off by 165 µm in 3–15 Hz | implemented, **off by default** |
| Pulling the nib toward predicted letters in free writing | pen | worse (222 µm; a wrong letter at full confidence flipped 9 of 624 letters) | **never** |
| Learned tracker (GRU, TCN) | pen | gains in simulation are model-specific | behind the ICD §5 guard until EXP-E01 |

So the combination that works is:
- **physical:** the nib stage;
- **sensing:** a 6-axis IMU read directly, with gyroscope compensation;
- **per-user AI:** the calibration;
- **task AI:** known templates for tracing and copying;
- **digital AI:** recognition and autocorrect in the app.

AI-predicted letters help in the app, not at the nib.

### 11.5 What changes in the design and the plan

- **Electronics.** The IMU's FIFO is read at ≥ 1.9 kHz, the gyroscope is kept on during assist, and every page-sensor and IMU sample carries its acquisition time. The nose accelerometer is a placeholder on the nose flex, fitted only after EXP-I02.
- **Firmware.**
  - The AKF replaces the frozen filter: about 4–5 % CPU on the nRF54L15 class (CALC, `results/fusion/budget.json`).
  - The robust set is the default; the personal set is used when its calibration check passes.
  - Output low-pass with predicted delay.
  - Proposed ICD changes (`docs/sensor_fusion_ai.md` §8): CAL_USER v3, a PRIOR flag and σ_T in the template record 0x06, and a raw IMU research record 0x07 (the 1 mg research frame is too coarse).
- **Page sensor.**
  - With the AKF, 120 Hz / 10 ms is workable: all-band 0.94 and in band 0.81, against 0.93 and 0.78 at 1 kHz.
  - The previous filter did nothing at 120 Hz (0.998).
  - REQ-PNC-004 stays at ≥ 120 Hz, ≤ 10 ms; 1 kHz / ≤ 2 ms is preferred if a part allows it (DEC-021).
- **Validation (`validation/`).**
  - New experiments: EXP-I01 (grip compliance split, inside EXP-B06), EXP-I02 (rotational share of tremor, inside EXP-H01), EXP-I03 (passive options on writers) and EXP-I04 (conditional bench).
  - New criteria in existing experiments: IMU latency (AC-S01-09), false correction for fast writers (AC-E01-09), template error in the tremor band (AC-A02-04) and command jitter (AC-Q06-05).
  - EXP-E01 adds the AKF sets, the calibration, the GRU and the prior.
- **Configuration note.** `config/parameters.yaml` gives the LSM6DSV16X noise as 70 µg/√Hz ("verify"). The datasheet gives 60 (OPT-37). The simulations keep 70 (conservative) until the next parameter version.
