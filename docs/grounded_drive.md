# Paper-grounded heel drive (Rev J, study D)

**Status: proposed design, calculation and simulation. Nothing has been built or measured.** Every number carries a label:

| Label | Meaning |
|---|---|
| CALC | calculated here (contact mechanics, geometry, catalogue drive trains, the differentiable design model) |
| SIM | simulated here: model HW1-D (the handwriting study's HW1 pen-hand-paper model plus a heel element), test writers 0–5, rules frozen before the test |
| MFR (id) | manufacturer statement, with its ledger id |
| LIT (id) | literature, with its ledger id |
| ASSUMPTION | chosen here; section 9 names the experiment that measures it |

Code: [`drive/`](../drive/__init__.py). One command: `python3 -m drive.run_study` (`--quick` for a 1-minute check of the test stage on one writer). Tests: `pytest drive/tests -q` (about 10 s). CAD: [`mechanics/cad/heel_drive.py`](../mechanics/cad/heel_drive.py). Results: `results/drive/`. Proposed ledger rows: `results/drive/evidence_rows.csv` (HAP-60…70, AMF-100…118, CON-36…38, PAT-30…34; 38 sources opened). Layout parts for the 3-D explainer: `results/drive/layout_parts.json`.

**The question.** Using the paper as ground, which small actuator at the heel can push, steer or brake the pen (and so the hand) with the most useful force, safely?

<!-- ANSWER -->

## 2. What limits any drive at the heel

### 2.1 The force comes from friction on the paper

- The pen presses on the paper with the writer's force. The ball carries 0.15 N / sin 50° = 0.196 N of it (refill spring, CALC). The heel carries the rest.
- A sprung element in the heel gets min(P, heel load), where P is its spring preload. The skid ring takes any extra.
- The element can push sideways with at most μ × (its load). μ is the tyre-paper friction.
- Writers differ (LIT CON-01): mean force 1.01 N, SD 0.43 N between writers, 0.18 N within a word. In the model the writers' mean forces are 0.54 / 0.91 / 1.57 N at the 10th / 50th / 90th percentile (CALC).
- Friction of rubber on paper: polyurethane paper-feed rollers have 1.30–2.20 when new and 1.05–1.52 after 300 000 sheets (LIT AMF-111). A tiny heel tyre meets ink, dust and many papers, so the design range is 0.6–1.2 (ASSUMPTION). Paper friction tests agree only within 24–27 % between laboratories (LIT AMF-113). This must be measured (EXP-D01).

**T1. Traction the paper gives at preload P = 0.55 N (CALC over 1000 model writers)**

| μ | mean over writers (N) | weakest 10 % of writers (N) | writers whose mean force keeps the element fully loaded |
|---|---|---|---|
| 0.6 | 0.30 | 0.21 | 70 % |
| 0.9 | 0.45 | 0.31 | 70 % |
| 1.2 | 0.61 | 0.42 | 70 % |

- So a heel drive gives about **0.3–0.6 N**: as much as the desk board's 0.4 N cap (docs/guidance_board.md), from inside the pen.
- A writer who lightens the pen gets less. A pen in the air gets nothing: lifting always frees the writer.
- A higher preload does not help light writers: they do not press hard enough to load it (fig_traction_capacity).

### 2.2 Tyre, rolling drag and slip

**T2. The 2 mm wheel's O-ring tyre (0.6 mm cord) on paper (CALC; Hertz contact; rolling friction after LIT AMF-112; Mindlin tangential stiffness; tyre E 8 MPa, loss tangent 0.12, ASSUMPTION)**

| load (N) | contact radius (mm) | mean pressure (MPa) | rolling resistance coefficient | rolling drag (mN) | tangential stiffness (N/mm) |
|---|---|---|---|---|---|
| 0.3 | 0.23 | 1.87 | 0.066 | 20 | 2.06 |
| 0.5 | 0.27 | 2.22 | 0.078 | 39 | 2.58 |
| 0.6 | 0.27 | 2.62 | 0.092 | 55 | 2.61 |

- Rolling along the letter costs about 46 mN at 0.55 N (CALC; 0.6 mm O-ring cord). The simulation used 0.066 × load (36 mN), from an earlier cord size; the difference is small against the 0.1–0.5 N guidance forces. The Rev H skid slides with about 0.1 N (0.12 × 0.8 N, ASSUMPTION μ_skid).
- Across the heading the tyre acts as a stiff spring before it slides: 1.5 N/mm with the fork and paper in series (ASSUMPTION, EXP-D02). At 0.66 N it deflects about 0.44 mm (CALC).
- Slip is detected by comparing the paper sensor's motion with the wheel's own motion (MFR AMF-109 class sensor). The rule flags slip when the pen travels over the wheel surface by more than the tyre can deflect (1.5 × 1.2 × load / k_lat plus 8 mm/s × 4 ms; ASSUMPTION). Each new flag lowers the traction estimate by 10 %; it recovers over about 2 s (ASSUMPTION, EXP-D05).

### 2.3 Where the drive can sit: outside the swinging nose

- In Rev H the nose swings to 5.29 mm from the axis in the ring plane; the ring's lip is 1.16 mm thick at 6.75 mm (docs/opt_inertial.md 8.6). There is no room inside the ring.
- A drive element and whatever steers or drives it must sit outside the nose's envelope, at the bottom of the heel (paper side). It must also be the lowest point of the heel at every tilt from 35° to 75°.

**T3. Heel contact radius needed (CALC; drive/geometry.py; 0.3 mm wall, 0.3 mm clearance to the nose at its stop)**

| element radius (mm) | element alone (mm) | wheel + steering ring (mm) | ball + two rollers r 0.6 mm (mm) |
|---|---|---|---|
| 0.75 | 7.12 | 8.14 | 8.05 |
| 1.00 | 7.61 | 8.68 | 8.47 |
| 1.25 | 8.11 | 9.21 | 8.89 |
| 1.50 | 8.60 | 9.75 | 9.31 |
| 2.00 | 9.59 | 10.82 | 10.15 |

- The chosen wheel is 2 mm across (radius 1.0 mm): the smallest that takes a replaceable O-ring tyre (ASSUMPTION).
- **Chosen heel (CALC):** contact radius **8.75 mm** (Rev H 6.75), skid ring 8.40 mm; the wheel sticks out 0.35 mm beyond the ring; spring travel 0.54 mm; the wheel keeps contact up to **±20° of pen roll**.

**T4. What the bigger heel costs the front end (CALC; the method of opt/inertial/front_end.py)**

| | Rev H (ring 6.75 mm) | with the heel drive (ring 8.40 mm) |
|---|---|---|
| front sleeve diameter at the heel | 15.0 mm | 18.3 mm |
| ball ahead of the heel at 50° | 5.21 mm | 6.59 mm |
| ball ahead at 35° / 75° | 9.03 / 1.45 mm | 11.39 / 1.89 mm |
| refill slide over 35–75° (with corrections) | 13.5 mm | 15.5 mm |

- The front is larger but stays well inside the Rev J envelope (Ø ≤ 24 mm where held, docs/revJ_plan.md 6).
- The refill spring must allow 2.0 mm more slide.
- **Ink stays visible.** The wheel sits at the bottom of the heel, on the paper side, 6.6 mm behind the ball along the pen. The ring stays open 120° on top, as in Rev H.

### 2.4 Pen roll, pen-up gaps, paper holding

- **Roll.** Rolling the pen moves the wheel up the side of the heel. The 0.54 mm spring travel keeps it on the paper up to ±20° (CALC). The IMU knows the roll and turns the steering and force directions with it (ASSUMPTION).
- **Pen-up gaps.** Lifting the pen lifts the wheel: the drive has nothing to push against and its torque goes to zero when the wheel load falls below 0.02 N (SIM rule). During a lift the controller turns the wheel toward the next stroke, so it is ready at touchdown. Dysgraphic writers stop and lift more often (LIT CON-38).
- **The paper must be held.** A loose sheet slides when the drive's push exceeds the sheet's grip on the desk: with 1 N of writing load, no resting hand and paper-desk μ 0.25, a 0.5 N push moves the sheet (CALC; μ 0.25–0.5 ASSUMPTION). With the writing hand resting (1 N) and μ 0.5 it holds 1.0 N. The other hand or a clip must hold the sheet (EXP-D03).
- **Heading rates.** Letters turn fast. The direction of the intended path turns at up to 71 rad/s (90th percentile) and 283 rad/s (99th percentile) on the synthetic writers (CALC on tuning writers; LIT CON-37 explains why tight curves are slow). Smoothed over 2 mm, as a wheel that leaves the detail to the nose would follow, the 99th percentile is 40 rad/s (CALC).

## 3. Candidates at the heel (CALC with catalogue parts)

**T5. Candidates (CALC; catalogue parts; preload 0.55 N; μ 0.6–1.2 ASSUMPTION; 'as 3' = as the steer-only wheel)**

| concept | actuators | force on the pen (N) | force note | speed at the contact (m/s) | power (W) | mass (g) | heel size | when not driving | safety | ledger |
|---|---|---|---|---|---|---|---|---|---|---|
| **Driven ball (trackball in reverse)** | 2 motors (Faulhaber 0620 B) on shafts to 2 rollers r 0.40 mm (bevel 1:1), 1 idler, preload spring | 0.33-0.66 | traction-limited (mu 0.6-1.2 x P 0.55 N); motor limit 0.57 N continuous | 1.26 | 0.081 (2 motors, 0.15 N RMS) | 6.7 | ball d 2 mm with rollers: heel contact radius >= 8.03 mm (Rev H 6.75) | reflected mass 6 g per axis; back-drive 0.03 N plus the orthogonal roller's axial slip about 0.22 N with smooth rollers -> retract when off | force <= mu_max x P = 0.6 N by physics; lift = zero force; current cap; slip detection | AMF-100,AMF-103,AMF-117,AMF-118 |
| **Two micro omni-wheels** | 2 motors (maxon DCX 6 M + GP 6 A 3.9:1) + 2 custom omni-wheels d 6 mm (smallest commercial found: 11.5 mm, AMF-110) | 0.17-0.47 | each wheel carries about half the heel load, so along one wheel's axis only half the traction pushes (0.5-0.71 x mu P, CALC) | 1.74 | 0.127 | 9.2 | 6 mm wheels: heel contact radius >= 11.4 mm; 11.5 mm commercial wheels: >= 16 mm (does not fit) | reflected mass 3 g per wheel; the rollers clog with paper dust (ASSUMPTION) | as the ball | AMF-101,AMF-102,AMF-110 |
| **Steered wheel, steer only (cobot)** | 1 steering motor (Faulhaber 0620 B, transfer gears, crown 2:1 on the fork) + Hall angle sensor at the fork; free wheel d 2 mm with an O-ring tyre | 0.33-0.66 across the path (constraint); 0 along it | cannot push; the across-path force is a reaction, up to mu x P; along the path only rolling resistance 46 mN (CALC, Persson AMF-112) | steering 1569 rad/s no-load (needed: p90 71, p99 283 rad/s on synthetic letters) | about 0.005-0.02 (steering only; power is supplied by the writer) | 3.8 | wheel d 2 mm with steering ring: heel contact radius >= 8.68 mm | when not guiding, the wheel must follow the writer's direction (free mode, LIT HAP-60 eq. 2) or retract | intrinsically passive: cannot move the pen by itself (LIT HAP-60, PAT-27); across-path force <= mu_max P | HAP-60,AMF-112,AMF-100,AMF-103 |
| **Steered wheel with an axle brake** | steering motor + a hub-train motor used as a generator (short-circuit or PWM braking) or a friction brake | 0.33-0.66 across; along the path up to mu x P as braking only | motor braking 0.4 N s/m at full short (Faulhaber 0620 B, 2:1, r 1.0 mm); more with a higher ratio | as 3 | < 0.02 (braking recovers energy) | 6.8 | as 3 plus the hub train | as 3 | passive (can only resist) | AMF-100,AMF-103 |
| **Steered and driven wheel (powered cobot)** | steering motor + drive motor (both Faulhaber 0620 B) in the handle; two 0.8 mm shafts in a keel to the heel pod; crown 2:1 for steering, bevels 2:1 to the axle | 0.33-0.66 in any direction after steering | traction-limited; motor limit 0.41 N continuous, 0.67 N peak (0620 B at 3.7 V, 2:1, three meshes, r 1.0 mm) | 1.57 | 0.078 drive + steering | 7.2 | wheel d 2 mm with steering ring: heel contact radius >= 8.68 mm | reflected mass along the heading 3.8 g; back-drive 30 mN (so it can stay down and follow the writer) | force <= mu_max x P by physics; current cap; slip detection; lift = zero | HAP-60,AMF-100,AMF-103 |
| **Braked ball (variable damping)** | 1 brake (solenoid pad as the Reflective Haptics stylus, HAP-68; or MR fluid AMF-108; or a SQUIGGLE-pressed pad AMF-106) | 0-0.66 opposing motion only | isotropic: it cannot tell writing from tremor, so it resists both | n/a (passive) | 0.02-0.3 (solenoid holding current, ASSUMPTION) | 3-6 (ASSUMPTION) | ball d 2 mm: heel contact radius >= 7.6 mm plus the brake | a free ball: light | passive; brake force <= mu P | HAP-68,AMF-106,AMF-108 |
| **Controllable friction pads** | high-voltage electrode pad; or a piezo pad; or a pad on a steering motor | electroadhesion 0.014-0.072 extra friction | a 24 mm2 pad at 1-5 kPa on paper adds 0.024-0.120 N of normal force (dielectric targets: pre-contact pressure 1-100 x below release, AMF-114); ultrasonic squeeze films need a smooth, airtight contact (AMF-115; paper is porous); anisotropic pads (AMF-116) slide with 3-6 x the drag of a rolling wheel (ASSUMPTION ratio) | n/a | 0.01-0.1 (400-2000 V converter; ASSUMPTION) | 1-3 | a pad on the heel | none | high voltage at the fingertips (EA) | AMF-114,AMF-115,AMF-116 |

**Verdicts.**
- **Driven ball** (a trackball run backwards). Pushes in any direction at once, 0.33–0.66 N (CALC). But whenever one roller drives, the other must slip along its axis (LIT AMF-117): 0.03 N of internal drag with omni-type rollers (ASSUMPTION) or about 0.22 N with smooth rollers (CALC: 0.3 × 0.75 N roller preload). Balls collect ink and paper dust and wear (LIT AMF-117, PAT-33). **Fallback.**
- **Two micro omni-wheels.** Each wheel carries half the load, so along one wheel only half the traction pushes: 0.17–0.47 N (CALC). The smallest commercial omni-wheel is 11.5 mm across (MFR AMF-110); even custom 6 mm wheels need a heel contact radius of about 11.4 mm (CALC). **Rejected.**
- **Steered wheel, steer only (cobot).** A free wheel rolls along its heading and grips across it. It channels the writer's own motion along the letter with the full traction across the path (0.33–0.66 N) and almost no power; it cannot move the pen on its own (LIT HAP-60, PAT-27). **Recommended default mode.**
- **Steered wheel with a brake.** Adds along-path damping from the drive motor used as a generator: 0.4 N·s/m with the winding shorted (CALC), more with PWM braking of the powered motor. **Recommended tremor mode.**
- **Steered and driven wheel ("powered cobot").** Adds a push along the heading, up to the traction, and can lead a relaxed hand. Motor limit 0.41 N continuous and 0.67 N peak through three gear meshes (CALC; 0.9 per mesh ASSUMPTION). **Recommended: the same wheel with its drive motor, used only in an explicit lead-through or autowrite mode.**
- **Braked ball.** Resists in every direction; it cannot tell writing from tremor. A stylus with an electromagnetically braked ball exists (LIT HAP-68, PAT-31). **Tremor only; not pursued** (the wheel's brake does the same along the path and the wheel also constrains across it).
- **Controllable friction pads.** Electroadhesion: 1–5 kPa on a 24 mm² pad adds only 0.024–0.12 N of normal force, so 0.014–0.07 N of friction (CALC from LIT AMF-114). Ultrasonic squeeze films need a smooth, closed contact (LIT AMF-115); paper is porous. Direction-dependent skins slide with drag (LIT AMF-116). **Rejected.**
- **Others.** A piezo "walking foot" on paper (the paper's compliance absorbs micrometre steps, ASSUMPTION); a 4 mm hub motor (0.40 N continuous only with an assumed 100:1 head, 73 mm/s no-load: too slow, CALC from MFR AMF-104); asymmetric vibration (a felt pull, no net force: study K); the desk board (keeps its role at a desk). **Not pursued.**

## 4. The recommended design (proposed design)

### 4.1 What it is

<!-- FIGCAD -->

- A **2 mm wheel** with a 0.6 mm O-ring tyre sits in a slot at the bottom of a larger skid ring.
- It is **steered about the paper normal through its contact point** (the cobot rule, LIT HAP-60): steering then needs almost no torque and never pushes the pen.
- It is **driven about its axle** through a 2:1 bevel.
- Two **Faulhaber 0620 B** brushless motors (Ø6 × 20 mm, 2.5 g each, MFR AMF-100) sit in the handle between the gimbal and the coils, beside the nose's rear arm.
- Transfer gears and two 0.8 mm shafts in a keel under the front sleeve carry their motion to the heel pod.
- The pod hangs on a leaf flexure that presses the wheel down with 0.55 N. A Hall sensor reads the flexure's bend (the wheel's load); another reads the wheel's heading at the fork.
- The Rev H paper sensor becomes mandatory: it sees slip.

**T6. Heel-drive parts (PROPOSED DESIGN; masses CALC from volumes and catalogue; `results/drive/layout_parts.json`)**

| id | part | where (z from the ball tip, mm) | what it does | catalogue / make | mass (g) |
|---|---|---|---|---|---|
| `drive_skid_ring` | Skid ring with wheel slot | 6.6–8.1 | Rests on the paper like the Rev H ring, but larger, with a slot at the bottom through which the drive wheel reaches the paper. | custom (PTFE-coated POM, contact radius 8.40 mm, open 120 deg on top) | 0.08 |
| `drive_wheel` | Drive wheel with O-ring tyre | 6.9–7.9 | A 2 mm wheel that rolls on the paper: steered, it lets the pen move only along the letter; driven, it pushes the pen along it. | custom brass hub d 0.8 mm + NBR O-ring 0.8 x 0.6 mm (tyre); axle d 0.3 mm in jewel bearings (AMF-111,AMF-112) | 0.01 |
| `drive_fork` | Steering fork and crown | 8.0–9.0 | Holds the wheel and turns it about the paper normal through its contact point; carries the crown gear, the axle bevel and a tiny magnet for the steering-angle sensor. | custom (hardened steel fork, brass crown gear module 0.1, bevel 2:1 to the axle) | 0.08 |
| `drive_pod` | Heel pod (sprung) | 8.1–12.1 | Bearing block for the fork, the two bevel pinions and the sensors; it hangs on a flexure so a 0.55 N preload presses the wheel onto the paper. | custom (PEEK housing, two jewel bearings) | 0.07 |
| `drive_spring` | Preload flexure | 12.1–17.1 | Leaf spring that lets the pod move 0.54 mm toward the paper and presses it with about 0.55 N; the ring takes any extra writing force. | custom (17-7PH leaf 0.1 mm, laser-cut) | 0.01 |
| `drive_load_sensor` | Wheel-load sensor | 15.6–16.6 | Hall sensor that reads the flexure's bend: the wheel's load, which sets how much force can be used before the wheel slips. | linear Hall IC (DRV5055 class) + 1 mm magnet (OPT-46) | 0.02 |
| `drive_steer_sensor` | Steering-angle sensor | 8.8–9.8 | Reads the wheel's heading from a magnet on the fork, right at the wheel (so shaft twist does not matter). | 3-D Hall IC (TMAG5273 class) + diametric magnet d 1 mm (OPT-45) | 0.02 |
| `drive_shaft_drive` | Drive shaft | 10.2–49.2 | Thin steel shaft in a PTFE liner that carries the drive motor's turning to the heel pod. | custom (stainless shaft d 0.8 mm, PTFE liner d 1.2 mm; 40 deg bevel pinion at the pod) | 0.15 |
| `drive_shaft_steering` | Steering shaft | 10.2–49.2 | Thin steel shaft in a PTFE liner that carries the steering motor's turning to the heel pod. | custom (stainless shaft d 0.8 mm, PTFE liner d 1.2 mm; 40 deg bevel pinion at the pod) | 0.15 |
| `drive_keel` | Shaft keel | 10.2–47.2 | Ridge under the front sleeve (toward the paper) that houses the two shafts either side of the paper sensor. | PEEK / TPE, part of the sleeve moulding (AMF-24) | 0.37 |
| `drive_paper_sensor` | Paper sensor (needed by the drive) | 14.0–20.0 | Optical sensor that sees the paper: it detects wheel slip (pen motion that the wheel did not make) and gives the page position. | optical flow sensor, to select (mouse-class performance as PMW3360: 1 kHz reports, 12 000 frames/s; its own package is too large) (AMF-109) | 0.30 |
| `drive_transfer` | Transfer gears | 47.2–49.2 | Two small spur-gear pairs that move each motor's output out to its shaft, around the gimbal. | module 0.1 spur gears (33 teeth, 1:1, centre distance 3.3 mm), brass | 0.12 |
| `drive_motor` | Wheel drive motor | 49.5–69.5 | Turns the wheel so the pen is pushed along the letter (up to about 0.5 N at the wheel). | Faulhaber 0620 B brushless DC, 6 x 20 mm (drive: bevel 2:1 at the wheel; steering: crown 2:1) (AMF-100) | 2.50 |
| `steer_motor` | Steering motor | 49.5–69.5 | Turns the wheel's heading to follow the letter. | Faulhaber 0620 B brushless DC, 6 x 20 mm (drive: bevel 2:1 at the wheel; steering: crown 2:1) (AMF-100) | 2.50 |
| `drive_drivers` | Motor drivers | 99.5–103.0 | Two three-phase drivers with current sensing that set each motor's torque 2000 times a second. | 3-phase micro BLDC driver x2 (to select; DRV8311 class) | 0.15 |

**Fit checks (CALC; `drive/layout.fit_checks`).** All pass:
- motors to the nose's rear arm at its stop: 0.26 mm
- motor pocket in the 1 mm handle shell (wall left 0.60 mm): 0.40 mm
- motors to the coils' iron ring (along the pen): 2.48 mm
- motors to the gimbal (along the pen): 3.00 mm
- shafts outside the gimbal ring: 0.45 mm
- keel's front edge above the paper at 35°: 0.20 mm
- heel pod to the nose envelope at its stop: 0.41 mm
- paper sensor to the nose envelope: 0.69 mm

**What it replaces in Rev H.** The skid ring (larger, slotted), the front sleeve (larger front), the optional paper sensor (now required) and the optional board magnet and its keel (the shaft keel takes their place; the heel drive does the board's job without a board).

### 4.2 Sizing by optimisation (CALC)

- **Model.** Continuous design variables: element radius, gear ratio (relaxed to a continuous value), spring preload and, for the ball, roller radius. Discrete: the motor (enumerated from the catalogue). Terms: traction each model writer gets (CON-01 force distribution, μ 0.6), share of writers with full load, motor force, speed, reflected mass, back-drive force, copper loss at 0.15 N RMS, heel size (from the geometry of 2.3, including the steering ring or rollers), rolling drag (Persson, LIT AMF-112) and, for the ball, the rollers' internal scrub.
- **Method.** The model is smooth, cheap and analytic, so reverse-mode automatic differentiation (torch autograd, the adjoint of the model) gives exact gradients; Adam from 6 starts finds the optimum; the ratio is then snapped to catalogue options and the rest re-optimised. Gradients agree with central finite differences to a relative error of 1e-10 (CALC). **Bayesian optimisation is used instead for the control gains** (section 5), where every evaluation is a noisy, non-smooth closed-loop simulation with a recogniser.

**T7. Optimised builds (CALC; autograd optimum, ratio snapped to the catalogue options, 6 mm motors only)**

| | steered + driven wheel | driven ball |
|---|---|---|
| motor | fh0620B (Faulhaber 0620 B, MFR AMF-100) | fh0620B (Faulhaber 0620 B) |
| gear (snapped; continuous optimum) | bevel 2:1 only (1.86:1) | bevel 1:1 only (0.99:1) |
| element radius (mm) | 1.00 | 1.00 |
| roller radius (mm) | - | 0.40 |
| preload P (N) | 0.57 | 0.57 |
| motor force at the contact, continuous (N) | 0.53 | 0.71 |
| no-load speed (m/s) | 1.57 | 1.24 |
| usable force, mean writer, μ 0.6 (N) | 0.31 | 0.31 |
| usable force, weakest 10 % of writers (N) | 0.22 | 0.22 |
| writers with full load | 68 % | 68 % |
| reflected mass (g) | 3.8 | 6.1 |
| back-drive force (mN) | 23 | 28 |
| internal scrub of the rollers (mN) | 0 | 225 (smooth rollers) |
| rolling drag (mN) | 46 | 31 |
| copper loss at 0.15 N RMS (mW) | 46 | 26 |
| heel contact radius (mm) | 8.67 | 8.02 |
| mass of motors and gears (g) | 7.4 | 7.0 |

Objective of each motor (lower is better; CALC): wheel/fh0620B 0.039; wheel/mxDCX6M 0.053; wheel/mxDCX8M -0.047 (does not fit); ball/fh0620B 0.801; ball/mxDCX6M 0.862; ball/mxDCX8M 1.038 (does not fit)
Gradient check: largest relative error wheel 1.0e-10, ball 8.7e-10 (CALC).

- **The force is set by traction, not by size.** Across the size-weight sweep the usable force stays at 0.31 N (mean writer, μ 0.6) and 0.22 N (weakest 10 %) whatever the wheel size (CALC, fig_design_pareto). So the smallest wheel wins.
- **A low ratio wins.** A 2:1 bevel (no gearhead) keeps the reflected mass at 3.8 g and the back-drive force at 23–30 mN, so the wheel can stay down and follow the writer when it is not driving (CALC).
- The model's 2:1 efficiency (0.95) is optimistic for the real path (spur transfer + 40° bevel + 2:1 bevel, 0.73 at 0.9 per mesh, ASSUMPTION). With that path: 0.41 N continuous and 0.67 N peak at the wheel, 30 mN back-drive, 3.5 W/N² copper loss (CALC). The simulation used 24 mN; the difference is inside the gear-friction uncertainty.
- An 8 mm motor scores higher in the model, but it does not fit beside the nose's rear arm (CALC fit check), and its friction torque is not in the catalogue extract (ASSUMPTION). It is excluded.

### 4.3 Modes and control (SIM-tuned; gains frozen in `results/drive/rules.json`)

| mode | what the wheel does | control law (gains tuned on tuning writers) |
|---|---|---|
| steer-only guidance | channels the writer's motion along the template; the writer supplies all motion | Stanley law: heading = template tangent 0.40 mm ahead + atan(15.4 s⁻¹ × cross-track error / speed); chosen over pure pursuit by the tuning (objective 0.65 vs 0.82) |
| steer-only, free in a band | free (follows the writer) within 0.3 mm of the template, steered outside | as above, band chosen by grid |
| steer + drive guidance ("full") | as steer-only plus a small push along the path while the writer moves forward | board law's lead term, 0.036 × the along-path error force (tuned) |
| steer + brake (tremor) | follows the writer's intended direction (free mode, LIT HAP-60 eq. 2) and brakes along the path above the writing band | free mode with apparent mass 0.05 kg, heading from the force low-passed at 9.3 Hz, brake 2.0 N·s/m (tuned) |
| steer + drive lead ("lead-through", "autowrite") | leads a relaxed hand along the letter | push 0.17 N + 6.3 N·s/m × (20 mm/s − speed along the path), capped; stops at the stroke end (tuned) |
| off | free wheel, or retracted | — |

**Supervisor (every mode; ASSUMPTION values, tested in SIM).**
- Force cap: min(0.5 N, 0.8 × μ̂ × measured wheel load). μ̂ starts at 0.8 (the controller does not know the paper) and falls with slip flags.
- Force slew limit 20 N/s.
- Yield: if the pen stays more than 4 mm from the template for 0.3 s, the drive fades out (the board's rule).
- Zero torque when the wheel load is below 0.02 N (pen lifted).
- Physics caps everything: the wheel can never push harder than μ × 0.55 N (0.33–0.66 N), whatever the software does.

### 4.4 Safety

- **Force.** At most 0.66 N by physics, 0.5 N by software (T1; REQ-DRV-001). Handwriting-guidance devices used 0.43–0.49 N (LIT HAP-15, HAP-16, HAP-51). ISO/TS 15066 allows 140 N quasi-static on the hand (LIT HAP-70): the drive is two orders of magnitude below any injury limit. The limit that matters is comfort and trust.
- **The writer always wins** (SIM, section 5.3): a writer set on a letter still writes it.
- **Passive by default.** Steer-only and brake modes cannot move the pen. Driving needs an explicit mode, and the drive never starts a stroke: the writer puts the pen down.
- **Stall and slip.** The paper sensor detects slip; the cap follows the traction estimate; stall is limited by the current cap.
- **Pinch points.** The wheel slot is on the paper side; the wheel turns at up to 1.6 m/s no-load (CALC) but with at most 0.67 N of rim force (CALC). ASSUMPTION: no pinch hazard; check in EXP-D07.
- **Heat.** Copper loss is 35–80 mW at 0.10–0.15 N RMS (CALC, 3.5 W/N²); winding rise 5–11 K with 146 K/W (MFR AMF-100 Rth 97.5 K/W × 1.5 enclosed, ASSUMPTION). Motors sit inside the handle, away from the finger pads (z 50–70 mm vs pads at 26–38 mm).
- **Magnets and implants.** Only the motors' own small rotor magnets; far weaker than the Rev H actuator magnets.

### 4.5 Power, mass, noise, cost

<!-- POWER -->

- **Mass.** Heel-drive parts 6.6 g plus about 2.5 g for the larger front sleeve (CALC): Rev H 75 g becomes about 84 g (Rev J envelope ≤ 120 g).
- **Noise.** Two 6 mm motors and watch-scale gears may whine. Not quantified (EXP-D06).
- **Cost class.** High: two precision micromotors, custom module-0.1 gears and a sealed pod.

<!-- SIM -->
