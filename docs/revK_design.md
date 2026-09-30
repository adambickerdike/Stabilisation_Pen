# Rev K: the integrated layout (study K, round 4)

**Status: proposed design, 2026-09-30.** Nothing here was built or measured on a pen or a person. Every target below is a hypothesis for the tests named.

**Labels.**
- **CALC**: a calculation in this study's package `revk/` (or in the read-only package named: `bnib/`, `revj/`, `revj1/`).
- **SIM**: an executed simulation. Here only the servo-bandwidth check of section 5.6 (study B's sim2 set-up, tuning writers only). Other SIM numbers are quoted from studies B and S with their files.
- **MFR / LIT**: a manufacturer or published statement, with its ledger id. AMF-250…254 are proposed in `results/revK/evidence_rows.csv`.
- **ASSUMPTION**: an input nobody has measured; the test that pins it is named.
- **PROPOSED DESIGN**: a dimension or choice made here.

**Where things are.** Code in `revk/`, results in `results/revK/`, CAD in `mechanics/cad/revK_pen.py`. Section 10 says how to run it; section 11 holds the proposed rows for the lead.

---

## 1. The answer in plain words

**What Rev K is.** Rev K is the next prototype pen. It keeps the Rev J body: a 24 mm handle, a skid ring that rests on the paper, a page sensor near the tip, and the same electronics and cell. In place of Rev J's C1S nose it carries study B's balanced nib B1 (DEC-050). The refill slides up to ±1.06 mm sideways on four thin wires. Flat coils between fixed magnets move it. A face at the refill's rear end pushes it toward the paper, parallel to the paper. So the paper's push and the face's push cancel, and the coils do not have to hold the refill's spring force. The heel wheel is not in the base pen; it becomes a separate front-end module (section 6). There is no tail and no end-cap (DEC-051). Rev K does not autowrite: B1's reach is ±1 mm, and autowrite needs ±4–6 mm (DEC-050).

**What changed from study B's B1, and why.** Study B designed B1 as a nib. Putting it into a pen showed five things it could not do as drawn (all CALC):

| Problem found | Study B's B1 | Rev K's fix | Result |
|---|---|---|---|
| The coils do not fit the bore | Its coil model has end turns of zero width. At the stop its corner reaches 10.81 mm from the axis; a buildable coil with the same legs reaches 12.9 mm (bore 11.0 mm) | A coil that can be wound, sized to stay 0.3 mm inside the bore at the stop | Force constant 0.334 N/√W (x) and 0.272 (y), 83 % and 68 % of study B's 0.40. About 1.8 × the copper loss |
| The coils have no leads | The moving coils need four wires across the moving carrier. Titanium suspension wires cannot carry the current (7 Ω per coil loop, 2.8 × the coil) | The four suspension wires become the coil leads, in 0.10 mm beryllium copper (C17200), as in optical pickups | 0.27 Ω per wire, +21 % copper loss |
| The face's push bends the carrier | The paper's push and the face's push are parallel but 68 mm apart: a couple of 10.9 mN·m at 35°. The four wires would carry it as 0.70 N of compression, 81 × their buckling load | A ball thrust guide on both faces of the carrier's flange takes the couple; the wires only centre the carrier and carry current | Ball load 2.6 N, rolling friction 2.6 mN, carrier tilt fixed |
| The face must follow the pen | Study B drew a 6 mm disc behind the refill | A counter-face head: a roll cage (±30°), a tilt hinge, a float and a captive shoe, moved by three piezo screw motors | 10.2 × 7.9 mm face; follower moves only 0.46 mm over 35–75° |
| The wire anchor sat where the face must swing | — | The actuator moves 4.5 mm toward the tip | 2.1 mm clear |

**Size and mass (CALC).** 145.1 mm long (the envelope allows 175 mm). 24 mm where the fingers hold it, from 20 mm behind the tip. The front is 12 mm across at the skid ring and widens to 24 mm over 14 mm. The base pen weighs 66.4 g with its balance point 74.9 mm from the tip; with the heel module, 73.4 g and 77.4 mm. Rev J.1 weighed 84.3 g (balance point 86.0 mm). Study B estimated 68.8 g (74.2 mm).

**Battery (CALC).** On the LIR14500 cell (2.22 Wh usable), writing lasts 23.5–48.6 h with 1 mm of tremor, 24.2–50.1 h with none, 21.0–48.4 h with 2 mm, 23.2–48.9 h guiding, and 23.7–50.0 h with spelling cues and pen lifts. With the heel module, lead-through lasts 10.8–15.0 h. Every mode passes REQ-RVJ-I01 (8 h; lead-through 7.5 h). The low end assumes magnets 30 % weaker than modelled and the electronics at the top of their datasheet range. The electronics take about half the power; the nib takes the other half, mostly to hold the moving parts up against gravity. Rev J.1 claimed 8.5–9.7 h, but that number is suspended (it left out the refill's side load; with it, about 1 h). Study B estimated 38 h (CALC) and 33.5 h (SIM).

**Heat (CALC).** In a 30 °C room the web of the hand stays at 30.6 °C. The front finger pad sits over the coils and reaches 35.9 °C with 1 mm of tremor and 37.6 °C with 2 mm, at the worst tilt (35°) and with weak magnets. This is below the 41 °C design target.

**Nib stiffness against the controller (CALC).** DEC-050 asks that the nib's lowest structural mode be at least 2.5 × the servo bandwidth, with the ball free and with the ball stuck on the paper. Rev K's lowest mode is 115 Hz in the worst case (ball stuck, 35°, soft refill, 20 µm pre-sliding) and 163 Hz nominally. So the servo may run at up to 46 Hz (65 Hz nominally). REQ-BNIB-006 asks at least 40 Hz. It passes, but with little margin. The simulation check (section 5.6, tuning writers only) found that dropping study B's 80 Hz position loop to 40 Hz changes the ink error by 0.5 %. Slowing its 100 Hz inner loop to 46 Hz as well raises it by 7 % but cuts the nib's power by 29 % (SIM).

**Cost (MFR for five chips, the rest ASSUMPTION).** About 810–1,930 USD per pen for 100 pens and 225–500 USD per pen for 1,000 pens, plus 28,000–70,000 USD of tooling. The three piezo motors, hand assembly and calibration, the counter-face head and the titanium carrier dominate. The catalogue chips are only 2–6 % of it. The heel module adds about 200–360 USD per pen at 1,000.

**What is open.** Four requirements cannot be met as written and need the lead's decision (sections 9 and 11):
- **Touchdown (REQ-BNIB-002).** The face must float 0.56 mm to follow the ±2.5° wobble of real writing, so the refill travels up to 0.98 mm before the balance returns; the requirement asks 0.25 mm.
- **Unpowered centring (REQ-BNIB-011).** The unpowered nib cannot centre within 0.1 mm: gravity pushes it onto its soft stop, 1.26 mm off centre. It still writes.
- **Page sensor range (REQ-BNIB-017).** The low-power page sensor sees the page only within ±0.2 mm of its lens height; the requirement asks for 2 mm of lift.
- **Heel module and page sensor.** A heel pod at the bottom of the ring forces the page sensor to its side, where it tolerates only 0.5° of pen roll.

The biggest unknowns are the buildable coil's real force constant (EXP-T07), whether C17200 wires survive as leads (EXP-B25), the ball guide (a new experiment), the counter-face head as a whole (EXP-J17 part c), and the grip: at 35° the 24 mm grip sits 3.3 mm closer to the paper than an ordinary pen's.

---

## 2. Rev K against the envelope and against Rev J.1 and study B

| Quantity | Rev J.1 (CALC) | Study B's Rev K estimate (CALC) | Rev K (this study) | Envelope or requirement |
|---|---|---|---|---|
| Length | 143.9 mm | 148 mm | **145.1 mm** (CALC) | ≤ 175 mm |
| Diameter where held | 24 mm | 24 mm | **24 mm** from z 20 mm; front 12 mm (PROPOSED DESIGN) | 24 mm (DEC-029) |
| Mass, base pen | 84.3 g | 68.8 g | **66.4 g** (CALC) | ≤ 120 g |
| Mass with the heel module | 84.3 g (heel always fitted) | — | **73.4 g** (CALC) | ≤ 120 g |
| Balance point from the tip | 86.0 mm | 74.2 mm | **74.9 mm** (base), 77.4 mm (heel) (CALC) | — |
| Transverse inertia about the balance point | 97,600 g·mm² | — | 118,900 g·mm² (base) (CALC) | — |
| Steady writing, 1 mm tremor | 8.5–9.7 h (suspended) | 38.35 h | **23.5–48.6 h** (CALC) | ≥ 8 h (REQ-RVJ-I01) |
| Web skin, 30 °C room, 1 mm tremor | 35.9 °C (suspended) | 30.6 °C | **30.6 °C** web; 35.9 °C at the front finger pad (CALC) | ≤ 41 °C target, 43 °C limit |
| Nib's lowest mode, ball free / stuck | — | 362 / 109 Hz | **1,206 / 163 Hz** nominal; stuck 115 Hz worst (CALC) | ≥ 2.5 × servo bandwidth (DEC-050) |
| Servo bandwidth allowed | — | 43.6 Hz from 109 Hz (study B ran 80 Hz) | **46 Hz** worst, 65 Hz nominal (CALC) | ≥ 40 Hz (REQ-BNIB-006) |
| Unit cost at 1,000 | classes only | not priced | **226–501 USD** + tooling (MFR + ASSUMPTION) | — |

**Why Rev K differs from study B's own estimate.**
- *Mass (−2.4 g).* The head is heavier than study B's face (4.8 g against 1.2 g, CALC). But the aluminium coil housing is gone, the coils are lighter (0.77 against 1.20 g of copper) and the heat spreader is gone.
- *Battery (38 h → 23.5–48.6 h).* Study B used one mid value: electronics 47 mW and nib 7.6 mW / 0.85. Rev K keeps a range and adds four things. The nib Hall runs at up to full duty (2.5–12.6 mW). A face-position sensor takes 4–8 mW (Rev J's value). The buildable coil costs 1.80 × study B's copper loss, and the wire leads 1.21 ×. The low end also takes magnets 30 % weaker.
- *Skin.* Study B's two-node model spread the coil heat over the whole shell. Rev K's fin model puts the worst-tilt coil power under the front finger pad. That is conservative.
- *Modes.* Study B's carrier carried its tilt on the wires. Rev K's ball guide locks the tilt, which raises the ball-free mode from 395 to 1,206 Hz. The ball-stuck mode rises less (122 → 163 Hz nominal), because it is set by the refill's bending and the paper's grip on the ball.

---

## 3. The layout

### 3.1 The axial stack (PROPOSED DESIGN; positions from `results/revK/layout.json`)

z is measured from the ball tip at 50° with the nib centred, toward the back. x points away from the paper.

| z (mm) | Part | Notes |
|---|---|---|
| 0–3 | Ball and tip cone | the ball is 4.58 mm ahead of the ring at 50°, 7.96 mm at 35°, 1.25 mm at 75° (CALC) |
| 4.6–6.1 | Skid ring, contact radius 6.0 mm, open 120° on top | bore 2.73 mm radius, lip 3.27 mm (CALC) |
| 6.1–8.1 | Page-sensor lens and 45° mirror block, at the bottom of the ring | lens 4.72 mm from the axis, 2.05 mm behind the ring plane |
| 6.1–20 | Front cone, Ø12 → Ø24 (23° half-angle); the first 15 mm clear hard-coated PC over the top 240° (the ink window) | |
| 9–11 | Carrier's front rolling guide station | the refill slides 6.7 mm over 35–75° plus ±1.5 mm of correction (CALC) |
| 10.2–15.2 | Page-sensor die (PMW3610 class) on a flex | |
| 16.5–18.5 | Lateral stop bush round the carrier (Ti, on three spokes) | the stop for the whole moving nib |
| 20–45 | Grip sleeve Ø24 (finger pads at z 26, 32 and 38) | |
| 21.4–29.9 | Actuator: back plate, four N52 poles, two coil layers (26.7–28.3), keeper | study B's stack moved 4.5 mm toward the tip |
| 29.9–33.6 | Ball thrust guide: front race (on the keeper), 6 balls, carrier flange Ø18.9, 6 balls, rear race on four posts | Si3N4 balls Ø0.8 mm on a 16.6 mm circle |
| 32.5–33.5 | Position magnet (1 mm N52 cube, on the flange at x 4.5 mm) | magnetised along the pen |
| 34.2–35.3 | Nib Hall sensor TMAG5170 | die 1.7 mm behind the magnet's centre |
| 31.8–58.6 | Four C17200 wires, Ø0.10 mm, on a 5.5 mm circle | suspension and coil leads |
| 35.5–58.3 | Main board on top (x 7–8 mm), IMU at z 50 | |
| 58.6–60.1 | Wire anchor ring on an axially soft diaphragm | |
| 60.7–85.0 | Counter-face head: carriage, roll cage, face (drawn at 50°: z 66–73), float, shoe, tilt motor and balance spring (z 78–84) | |
| 65.8–69.0 | Refill holder: cup on the refill's end, stem, 1.2 mm joint ball | the refill's end moves between z 63.6 (35°) and 70.3 (75°) |
| 85.3–91.3 | Roll and follower motors (SQL-RV-1.8), head flex | |
| 91.8–92.6 | Bulkhead | takes the refill's blow in a drop |
| 93.1–141.6 | LIR14500 cell (axis 3 mm up); cue LRA under it at z 93.6–101.6 | |
| 142.1–145.1 | Rear cap with two gold charging pads | |

The side view is `results/revK/layout_side_revK.png` (CSV twin). The CAD drawing with six cross-sections is `results/revK/drawing_revK_pen.png`.

### 3.2 The front end (CALC; `revk/frontend.py`)

Without a heel pod, B1 itself is not what sets the ring's size: a 4 mm ring would clear the nib. The page sensor sets it. Its lens must stay 2.2–2.6 mm above the paper over 35–75° (MFR OPT-61, PMW3610). Its folded optics (a 2 × 2 × 2 mm lens-and-mirror block, ASSUMPTION as Rev J) must clear the nib's envelope at the stop by 0.3 mm. The smallest ring on the 0.25 mm grid that passes every rule, with the window at the bottom, has a contact radius of **6.0 mm**. At the bottom of the ring the window height does not change with roll to first order. The lens stays in its band up to **21° of roll** (REQ-RVJ-N06 asks ±20°): 2.22–2.42 mm with no roll, 2.22–2.58 mm at ±20°. The cone stays 0.86 mm above the paper at 35° (rule 0.3 mm). The carrier's front stays 4.9 mm above it.

**Ink visibility (CALC, ray casting as Rev J.1; eye positions ASSUMPTION).** With the clear window, the fresh ink is visible within 1 mm of the ball in 19 % of tilt × eye cases and within 3 mm in 56 % (median 2.6 mm). With the ring's opening alone, 17 % and 50 %. Rev J.1's front reached 47 % and 61 %. The small front puts the refill and the carrier closer to the line of sight. EXP-J15 must be repeated on the Rev K front.

**The hand (CALC; hand model ASSUMPTION, Rev H).** All three finger pads sit on the full 24 mm grip. At 35° the grip's underside at the front pad is 7.4 mm above the paper. On an ordinary 9 mm pen held 25 mm from its tip it is 10.7 mm, and on Rev J it was 9.3 mm. So Rev K's fingers sit 3.3 mm closer to the paper. The fit check marks this as a failure against the ordinary pen (L3). Whether writers notice is a feel question (EXP-K24, proposed).

### 3.3 The nib in the pen (CALC; `revk/nib.py`, study B's models read-only)

**The coil against the bore.** Study B's force model (`bnib/magnetics.py`) gives each racetrack coil zero-width end turns. So its coil corner sits at the pole's edge: 9.55 mm from the axis at rest, 10.81 mm at the 1.26 mm stop. The bore is 11.0 mm, and the running rule leaves 10.7 mm. A coil that can actually be wound spreads its end turns over the same width as its legs: with study B's legs, its corner would reach 12.9 mm at the stop (1.9 mm beyond the bore) and its inner end runs would cross the carrier. Study B's layout drew the coils as a 20 mm disc inside a 21.6 mm aluminium ring and never moved them to the stop.

Rev K searches concentric racetracks (309 candidates, magpylib with study B's magnets and iron images, an upper bound like study B's) whose outer corner stays inside 11.0 − 1.26 − 0.3 = 9.44 mm and whose inner edge clears the carrier. The best: bundles 2.2 mm wide, rows centred 5.0 mm off the axis. Its force constant is **0.331 N/√W on the x layer and 0.270 on the y layer**. That is 0.83 × and 0.68 × study B's idealised coil computed the same way (0.397); scaled to study B's calibrated 0.400, Rev K's tip values are **0.334 and 0.272 N/√W**. The x layer loses 25 % toward the corners of the stroke (0.249 at the worst corner). Cross-coupling reaches 0.28. Copper: 0.77 g (study B 1.20 g). Averaged over both axes, the copper loss is 1.80 × study B's. The y layer is weaker because it sits 0.8 mm further from the magnets. Interleaving the layers would even them out; this is not done here. EXP-T07 (AC-T07-01) measures K_m on a coupon, and should use this coil.

**The coil leads.** The two coils need four leads across the moving carrier. Study B's Ti-6Al-4V wires cannot be the leads. Their resistivity is 170 µΩ·cm (MFR AMF-21 re-read: the page prints "170" in a column headed ohm·cm, which can only be µΩ·cm), so each wire has 3.5 Ω, which triples the coil loop and caps the current at 0.34 A at 3.3 V. Rev K makes the four wires in C17200 beryllium copper (22 % IACS minimum, MFR AMF-251; AMF-18 gives 22–28 %), 0.10 mm in diameter: the way optical-disc pickup actuators commonly feed their coils through their suspension wires (practice; no ledger row). Each wire has **0.27 Ω**; the coil loop rises from 2.5 to 3.03 Ω (+21 % copper loss). The current limit at 3.3 V is 1.0 A (study B designed for 1.5 A at 3.7 V). Suspension stiffness 1.56 N/m at the tip (study B 3.79 N/m).

Fatigue at the stop (bnib/flexure, C17200 fatigue strength MFR AMF-19 × 0.85): Goodman safety factor **2.18** at Kt 1.8 and 1.57 at Kt 2.5. But C17200's fatigue strength is well below Ti-6Al-4V's. Over study B's tolerance draws (diameter, length, modulus, Kt 1.3–2.5, and 0–0.3 N of axial preload from assembly), the 5th percentile falls to **0.92**. The preload is the main cause, and Rev K's ball guide makes it worse: it fixes the flange axially, so any axial mismatch between the flange and the anchor ring strains the wires directly (0.15 N per µm). Rev K therefore mounts the anchor ring on an axially soft diaphragm. With ≤ 0.05 N of preload, the 5th percentile is **1.40** (marginal against 1.5). A 0.08 mm C17200 wire reaches 1.50, but costs +33 % on the coil loop. EXP-B25's coupons must be repeated in C17200, carrying current. Welding, grinding or laser-cutting beryllium copper can release airborne beryllium, which can cause serious lung disease (AMF-18). So the clamps are soldered or crimped, not laser-welded (study B welded its Ti wires), or the work is done under fume extraction. A beryllium-free copper alloy with a similar fatigue strength is the alternative to look for; none is in the ledger yet.

**The couple and the ball thrust guide.** The face's push on the refill's rear end and the paper's push on the ball are parallel (both along the paper normal, F_n = 0.196 N) and 67.8 mm apart along the refill. They make a couple M = F_n·L·cos θ: **10.9 mN·m at 35°**, 8.5 at 50°, 3.4 at 75°. Study B named this couple (docs/balanced_nib.md s5.2) and took it as a tilt of the carrier on the wires. Four wires carry a tilt as axial forces, tension on one side and compression on the other: M / (2√2 r_w) = **0.70 N per wire at 35°**. A fixed-guided 0.128 mm Ti wire buckles sideways at 0.021 N, and a 0.10 mm C17200 wire at 0.009 N. So the compressed pair buckles; its post-buckling bow would be 0.53–0.64 mm, and the flange's rim moves 21–31 µm axially, into study B's 20 µm axial stops. With the compressed pair buckled, the tension pair alone carries the tilt, and the modes drop (the ball-stuck mode to 86 Hz worst, 34 Hz of servo allowed, below REQ-BNIB-006).

Rev K adds a **planar ball thrust guide** on both faces of the carrier flange. Six Si3N4 balls (Ø0.8 mm) run on each face, on a 16.6 mm circle, between the flange and two lapped 440C races. The front race sits on the keeper. The rear race stands on four posts. Each race sits on its seat under a wave spring preloaded to 4 N, about 1.5 × the couple's ball load. The carrier then translates on the balls with its tilt and axial position fixed. The wires only centre it and carry the current. Loads (CALC): 2.6 N on the loaded balls at 35°, rolling friction **2.6 mN** (rolling resistance 0.001, ASSUMPTION). Hertz stress: 2.66 GPa at the couple's load, 3.05 GPa at the springs' release load (the most a drop can put on a ball; ≤ 4 GPa static for 440C, ASSUMPTION). Rigid races would see 7.6 GPa in a 2,000 g drop and brinell, hence the springs; hard stops sit 20 µm behind the races. The balls roll half the flange's stroke, 0.63 mm. The races (2.26 mm wide) clear the wires' envelope by 0.36 mm and the flange's rim clears the bore by 0.31 mm at the stop (both marginal).

**Modes against DEC-050's 2.5 × rule** (bnib/flexure.loaded_modes, read-only: the refill as a planar beam in two guide stations at z 10 and 31.8 mm, the carrier on its suspension, the ink force as a compressive stiffness, the stuck ball as a pre-sliding stiffness μ_s·F_n / x_pre with x_pre 5 / 10 / 20 µm, ASSUMPTION; refill EI 0.09–0.385 N·m², tilt 35 / 50 / 75°):

| Suspension | Ball free, first structural (nominal) | Ball stuck, lowest (nominal / worst) | Servo bandwidth allowed (nominal / worst) | Cases ≥ 40 Hz |
|---|---|---|---|---|
| Study B's four Ti wires, in the Rev K layout | 395 Hz | 122 / 102 Hz | 48.7 / 40.8 Hz | 100 % |
| The same with the compressed pair buckled | 284 Hz | 96 / 86 Hz | 38.6 / 34.4 Hz | 56 % |
| **Rev K: C17200 wires + ball guide** | **1,206 Hz** | **163 / 115 Hz** | **65.2 / 46.0 Hz** | 100 % |

Study B's own numbers (362 Hz free, 109 Hz stuck; DEC-050) sit between the first two rows: its carrier, refill position and ring differ slightly. For Rev K the worst case is the stuck ball at 35° with the soft brass refill and 20 µm of pre-sliding. The rule allows at most 46 Hz. That is only 1.15 × REQ-BNIB-006's 40 Hz floor. EXP-T10 (AC-T10-02) measures the bandwidth and both modes; EXP-T01 measures the pre-sliding stiffness.

**The nib Hall sensor (CALC, magpylib in free space).** A 1 mm N52 cube on the flange, magnetised along the pen, sits 1.7 mm in front of the TMAG5170's die. A magnet magnetised across the pen gives no first-order signal for motion along one of the two axes, so it must point along the pen. The largest field component over the stroke is 44.9 mT. The pole magnets add 11.7 mT (free space, no keeper: an upper bound). That makes 56.6 mT, inside the A1 range of ±100 mT. Gradient 38.3 mT/mm, so the sensor's 140 µT rms noise at 20 kSPS (MFR OPT-44) is 3.7 µm at the tip, or 0.82 µm in a 1 kHz band. The coils' field is 0.86 mT per ampere of drive, 22 µm/A before the current calibration (EXP-T09, AC-T09-03). The Earth's field is 1.3 µm.

**Drop (CALC, energy method; stop stiffness ASSUMPTION).** The moving nib (3.44 g) hits its lateral stop at 4.4 m/s from 1 m. With a TPE or PEEK stop (2 × 10⁴ – 10⁵ N/m) the stop yields 0.8–1.8 mm, more than the coil's 0.3 mm clearance at the stop, so the coils would strike the bore. Rev K's stop is a titanium bush round the carrier tube inside the cone (10⁶ N/m, ASSUMPTION). It yields 0.26 mm (260 N, about 7,700 g), and the coils stay off the bore by 0.04 mm (marginal). The wires stay elastic (static safety factor 6.6 at 1.52 mm of deflection). Axially, the balls and the sprung races carry the drop (above); the wires see at most the 20 µm before the hard stops, 95 MPa, far inside C17200's elastic range (bnib/flexure.shock; study B's Ti wires: 66 MPa at 100 g without a stop, REQ-BNIB-012). The refill (0.9 g) hits the counter-face head with 9 mJ; the bulkhead behind the head takes it (18–90 N over 1–0.2 mm), not the piezo motors, whose axial load rating is not in the datasheets seen (AMF-15/106).

### 3.4 The counter-face head (CALC and PROPOSED DESIGN; `revk/counterface.py`)

**What the head must do.** The face must stay parallel to the paper (its normal 15–55° from the pen axis, at any roll). It must follow the refill's rear end, which slides 6.7 mm along the pen over 35–75° (Rev K's 6.0 mm ring). It must float over the ±2.5° tilt wobble of real writing (LIT CON-02) without losing the balance. And it must let go when the ball lifts.

**Where the hinge goes (CALC).** The face sits on a tilt hinge. The hinge's line runs across the pen at a distance x_h from the axis toward the paper, and the face is L_O behind the hinge along the paper normal. In closed form, the contact point on the face moves by u = ((L_O + r) cos θ − x_h) / sin θ, and the follower must set the hinge at z_O = z_c(θ) + (L_O + r − x_h cos θ) / sin θ (r: the joint's height above the face). With the hinge on the ring's paper-side generator (x_h = −R_s) and L_O = −(r_b + r), z_O does not change with tilt at all: the face turns about a line parallel to the one the pen tilts about, so tilting needs no follower. A sweep over x_h and L_O (8 × 31 layouts) keeps the heads whose follower travel, lift, the refill-length spread (0.3 mm, ASSUMPTION) and 0.5 mm leave 1.5 mm of a SQL-RV-1.8's 6 mm unused and whose swept face stays 0.3 mm inside the bore. Among those, it takes a face within 0.5 mm of the shortest, then the one with the least follower motion. The result: **x_h = −9 mm, L_O = −6 mm**. The face is **10.2 × 7.9 mm**, the follower moves **0.46 mm** over 35–75° (3.1 mm of travel needed with the lift and margins), and the swept face stays within 9.30 mm of the axis. A hinge on the pen axis (study B's picture) would need a 14.7 mm face that sweeps to 11.6 mm, into the wall.

**The parts (PROPOSED DESIGN).**
- A **carriage** (Ti tube, 21.4 / 20.8 mm) slides in the bore. It is moved by the **follower** SQL-RV-1.8, which is fixed to the shell.
- A **roll cage** (PEEK-CF, 20.2 / 19.2 mm) turns ±30° in the carriage, driven by the second SQL-RV-1.8 on a 5.5 mm crank. ±30° is REQ-RVJ-N06's ±20° of pen roll plus margin. The page sensor already fixes the pen's down side (it tolerates 21° of roll), so the head need not follow a full turn.
- A **tilt hinge** on the cage at x_h = −9 mm is driven by the third SQL-RV-1.8 on a 6 mm crank. A **torsion balance spring** carries the mean moment F_n·u (1.63 N·mm), so the motor moves only the residual.
- The **face**: a 0.3 mm sapphire tray on a Ti-6Al-4V bracket. It **floats** ±0.56 mm along its normal on a parallel-strip flexure, pushed by a constant-force strip spring (the ink force F_n), between two stops; the front stop is study B's follower stop. A face-position Hall sensor (TMAG5273 class) watches the float.
- A **captive shoe** (Ø4 mm) rides on three 0.5 mm Si3N4 balls on the sapphire, parallel to the face and under the tray's rim with 0.1 mm clearance. The refill's end carries a vented PEEK cup with a stem and a 1.2 mm ball. The ball snaps into an asymmetric slotted socket in the shoe, which lets the refill lean 15–55° from the face's normal. The shoe is a free body on rolling balls, so the face's push reaches the refill along the paper normal. A flange on the refill's own axis (a first idea) cannot run under a rim that is tilted 15–55° to it.

**Loads (CALC; stall force MFR AMF-15).** Tilt: residual 0.49 N·mm on the 6 mm crank, 0.082 N, 3.6 × margin to the 0.30 N stall; without the balance spring 0.35 N, which the motor cannot move. Roll: 0.23 N·mm, 0.042 N on the crank, 7.1 ×. Follower during a lift: 0.20 N, **1.51 ×** (marginal). The SQUIGGLE holds with zero power; its holding force against back-driving is not in the datasheets (EXP-J17 part c must measure it).

**Face-parallelism tolerance (CALC, Monte Carlo of 20,000 draws; contributors ASSUMPTION).** The contributors: IMU tilt 1° and roll 2° (1 σ, REQ-BNIB-015), the calibrated IMU-to-axis residual 0.2°, roll-cage play 0.3°, hinge 0.2°, face 0.1°, linkage backlash ±0.2° and the re-set deadband ±1.5°. The face is off parallel by 1.66° on average (3.28° at the 95th percentile). That leaves a side load of **5.7 mN mean and 11.2 mN at the 95th percentile**: 5.9 % and 13.6 % of the unbalanced F_s·cot θ. Both pass REQ-BNIB-001 (≤ 10 % mean, ≤ 25 % at the 95th percentile); study B had 5.3 mN. Holding it costs 0.37 mW on average. The ±2.5° wobble the face does not follow adds 8.5 mN dynamically (0.33 mW). A 10° desk slope adds 34 mN; that is an app setting.

**The pen lift (CALC; speed–force line of the SQL-RV-1.8 ASSUMPTION between MFR points).** DEC-050's first candidate works as follows. The follower pulls the head back along the pen. The float's front stop meets the face after g / sin θ. Then the face, the shoe and the refill retreat together until the ball is **0.5 mm** off the paper; the ring stays on the paper. The stroke along the pen is 1.10–1.85 mm (75°–35°). The time up is **0.155–0.18 s** and down 0.08–0.14 s. The ink stops after 43–72 ms. Energy per lift is **0.08–0.31 J** (the motor draws 0.34–1 W while moving, MFR AMF-15). Holding a lift costs no energy. It serves the spelling cue (EXP-S12/S18). It is too slow to withhold the rest of a letter: at 30 mm/s, about 2 mm more ink goes down before it stops. It cannot serve a gated mode (EXP-W16). For that, a latching lift coil on the float (8 ms, 0.01 J, +0.6 g; ASSUMPTION from Rev J's pen lift) is the option.

**Touchdown and the float (CALC).** The float's gap must cover the wobble: the refill's end moves 0.46 mm along the face normal at 35° when the pen tilts 2.5°, plus a 0.1 mm margin, so g = 0.56 mm. At a touchdown the refill therefore travels g / sin θ = **0.98 mm at 35°** (0.58 mm at 75°) before the face engages. REQ-BNIB-002 asks 0.25 mm. That would allow only 0.04 mm of wobble. The ink tail after a natural lift is g × v_lateral / v_lift = 0.28–1.1 mm. An electro-permanent brake on the float that locks when the face sensor sees a lift (Rev J's rule) cuts the tail to about 0.3 mm (12–60 mW, ASSUMPTION).

**Positioner power (CALC; re-set rate ASSUMPTION, EXP-B28).** A re-set runs when the estimated mean tilt or roll drifts beyond 1.5°, 2–6 times a minute, 0.05 s of motion each. With the drivers asleep between re-sets, that is **0.75–5.1 mW** (study B 2 mW).

**Changing the refill (PROPOSED DESIGN; forces ASSUMPTION, EXP-J17 part c with three refill brands).**
1. The user chooses "change refill" in the app, or holds the button for 3 s. The pen centres the nib, sets the face to its steepest position (hinge 15°) and moves the head to its rear position.
2. The user pulls the old refill out through the ring by its tip. The cup's ball unsnaps from the shoe at 0.1–0.2 N; the shoe stays captive under the tray's rim.
3. The user moves the cup to the new metal-bodied D1 refill (or fits a new cup) and pushes the refill in until it clicks (about 0.2 N). The carrier's guides centre it, and the shoe's funnelled slot takes the ball.
4. The pen reads the float with the head at its front position. A refill outside the float window (unseated, or too short) makes the app ask again.
5. The user writes a line for 5 s. The nib's holding current at the known tilt shows the new refill's balance. The face needs no calibration: the float spring sets the ink force.

No tool, about 30 s. The grip holds the refill at 12 × its weight.

### 3.5 Nib centring (CALC; `revk/tolerance.py`, tolerances ASSUMPTION)

*Sensing* moves the ink. The error sources are the Hall zero after factory calibration (5 µm, 1 σ), its offset drift over 15 K (1 µT/K, ASSUMPTION: EXP-T09 measures it), the Earth's field and the coil cross-talk left after calibration (5 %). Together the zero error is 4 µm mean and 13 µm at the 99th percentile. The magnet's Br drifts −0.12 %/K, a gain error of 1.8 % over 15 K (19 µm at the full travel). Both stay under REQ-RVJ-C02's 25 µm.

*Mechanics* does not move the ink, since the servo holds whatever the sensor calls zero. It does eat travel and clearances. The allowances are ±0.05 mm for the carrier's rest, the magnets and the coils, ±0.03 mm for the ring and the anchor, ±0.01 mm for the guides and ±0.05 mm for the optics. The stops then sit up to 0.072 mm (99th percentile) off the magnetic centre. The usable travel in the worst direction falls to 0.99 mm at the 1st percentile (0.98 mm at worst), just under G4's ±1.0 mm (DEC-060). The 0.3 mm running clearances fall to 0.21–0.26 mm at the 99th percentile: the coil against the bore to 0.21 mm, the ring bore and the plate holes to 0.26 mm, the optics block to 0.25 mm. All stay above 0.2 mm. Either the clearances grow by 0.1 mm, or these tolerances are held (a machining and assembly question for the build).

### 3.6 Electronics, cell, cue and charging (PROPOSED DESIGN)

The main board is a 4-layer board, 1 × 14 × 22.8 mm, on top above the wires at z 35.5–58.3. Its components clear the wires' envelope by 0.6 mm. It carries the nRF54L15, two DRV8214 coil drivers, the charger, fuel gauge and regulators, and the three NSD-2101 piezo drivers (MFR AMF-15). The LSM6DSV16X IMU sits on it at z 50. The TMAG5170 nib Hall sits on a flex tab carried by the rear race.

The LIR14500 cell sits at z 93–142 with its axis 3 mm up (Rev J.1). The cue LRA (8 mm coin, on edge) sits under the cell. The rear cap carries two gold charging pads for a pogo-pin cradle, which replaces Rev J.1's USB connector. There is no heat spreader: at 0.05–0.1 W none is needed.

---

## 4. Fit checks

59 checks, each a margin beyond its rule (0.3 mm running, 0.2 mm fixed, as Rev J; "marginal" below 0.1 mm or below 1.5 × on forces). **29 pass, 21 are marginal, 9 fail** (CALC). The full list is in `results/revK/layout.json` → `fit_checks`.

**Failures.**

| Check | Value | Rule | What it means |
|---|---|---|---|
| F5 page sensor's lift range | 0.2 mm tracked | ≥ 2.0 mm (REQ-BNIB-017) | A conflict for any mouse-class die (OPT-61: ±0.2 mm depth of field). EXP-T04 (AC-T04-07) measures the real cut-off on paper |
| H6 touchdown refill travel | 0.98 mm at 35° | ≤ 0.25 mm (REQ-BNIB-002) | The float must span the tilt wobble; see section 9 |
| N22 unpowered rest | rests on its stop, 1.26 mm off centre (the wires alone would let it sag 18 mm) | centred within 0.1 mm (REQ-BNIB-011) | No wire suspension soft enough for B1's power can hold 3.4 g against gravity. Study B's 3.8 N/m would sag 7 mm too. It still writes like a normal pen |
| L3 grip height at 35° | 7.4 mm | ≥ an ordinary pen's 10.7 mm | A feel question (EXP-K24, proposed) |
| V1 heel variant: page sensor roll | 0.5° | ≥ 20° | The pod takes the bottom of the ring |
| V4 heel variant: shafts vs back plate and keeper | 0.3 mm overlap | ≥ 0.2 mm clear | Needs 1.2 mm notches in both plates (EXP-T07 checks K_m with them) |
| N3, N14, N17 | — | — | For the record, study B's B1 as drawn: the idealised coil at the stop (10.81 > 10.7 mm), the couple on the wires (0.70 N against 0.009 N), Ti wires as leads (0.34 A). Rev K's fixes are N1, N7/N15 and N16 |

**Marginal (0–0.1 mm, or below 1.5 ×).** These are:
- F2 optics block against the nib (0.02 mm), F3 lens band (0.02 mm), F4 roll (1°) and F10 optics block in the cone wall (0.02 mm);
- N1 coil corner at the stop, N4 plate holes and H1/H8 head gaps (0.00 mm, sized to the rule);
- N2 coil against the carrier (0.03), N5 flange rim (0.01), N6 race against the wires (0.06), N7 balls on the flange (0.05), N10 Hall against a wire (0.08), N12 board against the anchor (0.07);
- N21 the coil in a sideways drop (0.04 mm with a 10⁶ N/m stop);
- N16b wire fatigue at the 5th percentile (1.40 ×), N18 servo bandwidth (46 Hz, 1.15 × the 40 Hz floor), N19 study B's wires (1.02 ×);
- H5 follower force (1.51 ×);
- V3 heel shafts against the cage and V7 the heel's rear transfer against the LRA.

**CAD solid checks** (`mechanics/cad/revK_pen.py`). These are boolean intersections larger than 0.001 mm³, with a list of intended contacts. **None** at rest. **None** with the moving nib at its stop in eight directions (the refill, its holder and the shoe also slide along the pen, as they do). The wires bend and the balls roll, so they are left out. The heel-module variant placed on the base front **collides** with the ring, cone, page optics, page-sensor die, sleeve, shell, carriage and bulkhead (22 pairs, listed in `revK_cad_summary.json`). That is expected: the module needs its own front (below).

---

## 5. Budgets

### 5.1 Mass and balance (CALC; +10 % wiring and adhesive as Rev J)

| | Base pen | With the heel module |
|---|---|---|
| Mass | **66.4 g** | **73.4 g** (+7.0 g) |
| Balance point from the tip | **74.9 mm** | 77.4 mm |
| Transverse inertia about it | 118,900 g·mm² | 129,900 g·mm² |
| Axial inertia | 4,270 g·mm² | — |

By group (base, with wiring): cell 22.0 g, structure 11.4 g, actuator iron and coils 9.3 g, electronics 5.8 g, counter-face head 4.7 g, grip and window 4.4 g, magnets 3.1 g, moving nib 1.8 g, haptic 1.1 g, ball guide and wires 1.0 g, refill 0.9 g, sensors 0.6 g, skid ring 0.1 g. The moving mass at the tip is 3.44 g (study B 3.49 g). The balance point sits 17 mm in front of the web of the hand (z 92), close to study B's.

### 5.2 Power and battery hours per mode (CALC; `revk/budgets.py`)

| Mode (REQ-RVJ-I01) | Nib coils | Total | Hours on 2.22 Wh | Target |
|---|---|---|---|---|
| Steady, no tremor | 16.5–33.6 mW | 44.3–91.7 mW | **24.2–50.1 h** | ≥ 8 h |
| Steady, 1 mm tremor | 17.8–36.3 mW | 45.7–94.4 mW | **23.5–48.6 h** | ≥ 8 h |
| Steady, 2 mm tremor (the nib clips) | 17.9–47.6 mW | 45.8–105.7 mW | **21.0–48.4 h** | (short texts) |
| Guide (nudges within reach + 0.5–1 cue/s) | 16.8–34.2 mW | 45.4–95.8 mW | **23.2–48.9 h** | ≥ 8 h |
| Spelling cue (lifts and ticks at study S's rates) | 16.5–33.6 mW | 44.4–93.6 mW | **23.7–50.0 h** | — |
| Lead-through (heel module) | 16.8–34.2 mW | 148.0–205.6 mW | **10.8–15.0 h** | ≥ 7.5 h |
| Guide with the heel steering (heel module) | 16.8–34.2 mW | 56.4–121.8 mW | 18.2–39.4 h | ≥ 8 h |
| Held, not writing (nib off on its stop) | 0 | 4.9–17.3 mW | 128–456 h | — |
| On the desk (standby) | 0 | 0.1–0.3 mW | 7,400–22,200 h | self-discharge limits it |

What makes up steady writing at 1 mm (low–high):
- **Electronics 21.9–43.1 mW.** Rev J.1's datasheet count (MFR OPT-60, OPT-37, AMF-37, duty ASSUMPTION), with the TMAG5170 at a 0.2–1.0 duty (2.5–12.6 mW, MFR OPT-44) in place of Rev J.1's two DRV5055 (14.8–29.6 mW).
- **Page sensor 1.3–1.9 mW** (PMW3610 class, MFR OPT-61, always on).
- **Face sensor 4–8 mW** (Rev J's value, ASSUMPTION).
- **Positioners 0.75–5.1 mW.**
- **Nib 17.8–36.3 mW.**

The nib's power is study B's duty model (bnib/candidates.evaluate: 7.6 mW mean over 35–75° with Km at 1.0 ×) × 1.80 (buildable coil) × 1.21 (leads), with Km at 1.0–0.7 × the upper-bound model. Most of it holds the 3.4 g moving mass against gravity across the pen: 28 mN at 35°. The tremor correction itself adds only 1–3 mW. The spelling cue's lifts cost 0.1–1.9 mW, because a lift is rare (0.3–2.3 per 100 words, SIM study S).

**Against Rev J.1 and study B.** Rev J.1's 8.5–9.7 h at 1 mm is suspended: it left out the C1S nose's static side load (DEC-046); with it, about 1 h. Study B gave 38.35 h (CALC) and 33.5 h (SIM), from one mid value: electronics 47 mW and nib 7.6 / 0.85 + 2 mW. Rev K's mid-range sits near study B's; the range is wider for the four reasons in section 2. A smaller cell would still pass REQ-RVJ-I01 with margin: a 10440-size cell (about a third of the energy, ASSUMPTION) would give roughly 8–16 h. Rev K keeps the LIR14500 for continuity.

### 5.3 Skin temperature in a 30 °C room (CALC; Rev J's fin model: PEEK shell, h 10 W/m²K ASSUMPTION, k MFR AMF-24; no hand contact counted)

Heat spreads only 5.4 mm along the thin PEEK shell (the fin length constant), so each source warms the skin right over it. At the high end (35° nib power with Km 0.7 ×, high electronics), writing with 1 mm tremor:

| Where | Temperature |
|---|---|
| Web of the hand (z 92, over the bulkhead) | **30.6 °C** |
| Front finger pad (z 26, over the coils) | **35.9 °C** |
| Middle / rear pads (z 32 / 38) | 34.7 / 33.0 °C |
| Hottest point on the shell | 36.2 °C |
| Coil | 37.1 °C |

With 2 mm tremor the hottest point is **37.9 °C** (front pad 37.6 °C). Lead-through with the heel module puts the web at 36.7 °C. All are below the 41 °C design target (LIT AMF-34) and the 43 °C limit (LIT AMF-35). A lift heats the piezo motor 3.8 K for 0.3 J (0.16 g, 0.5 J/gK, ASSUMPTION), which is harmless at the lift rate. For comparison: Rev J.1's web 35.9 °C (suspended), study B 30.6 °C.

### 5.4 Cost and bill of materials (catalogue chips MFR AMF-250…254, DigiKey 2026-09-30; everything else ASSUMPTION ranges: a request for quotation pins them)

| | 100 units | 1,000 units |
|---|---|---|
| Base Rev K, per pen | **812–1,929 USD** | **226–501 USD** |
| With the heel module | 1,202–2,629 USD | 426–861 USD |
| Tooling (moulds, fixtures, coil tooling), not in the unit cost | — | 28,000–70,000 USD (28–70 USD per pen over 1,000) |

The largest lines at 1,000:
- the three SQL-RV-1.8 with their drivers, 75–180 USD. They are sold only to volume customers (AMF-15); a micro-stepper lead screw is the prototype fallback;
- assembly, calibration and test, 40–80 USD;
- the counter-face head, 30–70 USD;
- the titanium carrier with its rolling guides, 15–35 USD;
- the main board, 10–20 USD.

The five catalogue chips come to 15.0 USD at 100 and 13.2–13.6 USD at 1,000: the nRF54L15 at 3.49 / 3.06, two DRV8214 at 2.59 / 2.24–2.45, the TMAG5170 at 1.97 / 1.74 and the LSM6DSV16X at 4.34 / 3.89 (MFR). That is only 2–6 % of the low estimate. Rev J.1 gave cost classes only, and study B a bill of materials without prices, so neither can be compared line by line. The heel drive and the custom micro-mechanisms dominate, as Rev J's classes said.

### 5.5 Nib structural modes against the 2.5 × rule

See section 3.3. In short, Rev K allows **46 Hz worst case, 65 Hz nominal** (CALC). Free: 1,206 Hz, 30 × 40 Hz. Stuck: 163 Hz nominal (4.1 × 40 Hz), 115 Hz worst (2.9 ×).

### 5.6 What the lower servo bandwidth costs (SIM, tuning writers only)

`revk/servo_sim.py` runs study B's sim2 set-up read-only (bnib/sim.py; its build folder is never written) with B1's pen and Rev K's nib constants (K_m 0.334 N/√W, 1.56 N/m). It uses tuning writers 100–101, seed 300, study B's tuning cells (ET 8 Hz × 1 mm and PD 5 Hz × 1 mm) and tremor-free writing, at three controller settings. The sim2 model has no carrier structural modes, so this measures only what the lower bandwidth costs in tracking; the stability margin is the CALC above.

| Setting | Position loop / inner loop | Ink error, nib held (mean of 4 cases) | Ink error, nib correcting | Ratio | Tremor-free writing moved | Nib power while correcting |
|---|---|---|---|---|---|---|
| A: study B's frozen setting | 80 / 100 Hz | 529 µm | 466 µm | 0.87 | 0 µm | 21.1 mW |
| B: position loop inside the rule | 40 / 100 Hz | 529 µm | 469 µm (+0.5 %) | 0.87 | 0 µm | 20.9 mW |
| C: both loops inside the rule | 40 / 46 Hz | 569 µm | 498 µm (+7 %) | 0.86 | 0 µm | 15.0 mW (−29 %) |

(SIM, 2 writers × 2 cells each, one seed: `results/revK/servo_bandwidth_sim.json`.) Halving the position loop's bandwidth costs almost nothing: the estimator, not the servo, limits the correction, as DEC-052 found. Slowing the inner loop as well holds the nib less stiffly against the paper's forces. The ink error with the nib held still rises by 40 µm, and the corrected ink error by 7 %, while the ratio to that baseline stays 0.86–0.87. It also cuts the nib's power by 29 %, because the servo reacts less to sensor noise. DEC-050's rule is about the closed-loop bandwidth, so the position loop must stay ≤ 46 Hz. Whether the inner loop must too depends on how it is built (a notch at the stuck mode, or the inner loop acting only on current). EXP-T10 (AC-T10-02) decides. Rev K's sim_params carry 40 Hz with the inner loop at 46 Hz (setting C), the conservative reading. The test writers, and several seeds, remain to be run (proposed EXP-K25).

---

## 6. The heel module (DEC-048's heel, as a separate front)

DEC-048 retracts the heel wheel by default and deploys it only for "write big" practice and lead-through. Rev K goes one step further and proposes to leave the heel drive out of the base pen, because the geometry forces a choice (CALC):
- **The page sensor.** The pod needs the bottom of the ring, which is where the page sensor is roll-insensitive. With the pod, the window moves beside it (azimuth 31°, 2.7 mm off the tilt plane). There the lens height tolerates only **0.5° of roll** (REQ-RVJ-N06 asks ±20°), while the smallest ring that fits the pod is 5.75 mm (wheel contact 6.1 mm).
- **The shafts.** Study D's straight shafts cannot run through Rev K's small cone. Rev K's variant uses short inner shafts in grooves of the cone (1.5 mm of skin), a transfer mesh where the sleeve reaches Ø23.2 mm, and outer shafts in grooves of the bottom wall (r 10.9 mm). Those shafts need 1.2 mm notches in the back plate and the keeper (V4), a slot in the carriage and a clear path past the anchor ring's spokes.
- **The motors.** The two Faulhaber 0620 motors sit under the cell behind the LRA (z 104–124 mm, 0.30 mm inside the bore).

The heel module weighs 7.0 g (CALC). It adds 200–360 USD per pen at 1,000 (ASSUMPTION) and makes lead-through possible: 10.8–15.0 h. In the CAD it collides with the base front in 22 places, which is why it is a different front (ring with a wheel slot, cone with a pod pocket, the page sensor beside the pod), not a bolt-on. **Proposed:** the base Rev K has no heel. The heel module is built as a bench front-end for write-big practice and lead-through (with study D's EXP-D tests). It goes into a pen only if EXP-T04 shows a page sensor that tolerates roll beside the pod, or if lead-through is judged worth a sensor that works only with the pen held square.

---

## 7. Parameters for the whole-pen simulator

`results/revK/sim_params.json` follows `results/revJ/sim_params.json`, block by block: handle, skid_ring, nose, refill, heel_wheel, endcap, sensors and domain randomisation. It adds a native `nib` block. B1 is a translation nib, so the `nose` block maps it onto sim2j's two-hinge nose with a virtual pivot 10 m behind the tip (every carrier point moves within 0.7 % of the ball, as study B's sim did). The position servo is 40 Hz and the inner loop 46 Hz (the 2.5 × rule allows 46 Hz). The refill block carries the counter-face: F_n along the paper normal, the float gap and the pen lift. The heel wheel is `fitted: false`. The end-cap is absent. The file lists what sim2j/revj.py must change to load it (it reads `refill_holder`, which Rev K keeps as the id of the puck; it also reads `ec_shell` and the layout's `pivot_z`, which Rev K's layout.json carries as the virtual pivot).

---

## 8. Provisional decisions made in this study (each a proposal for the lead)

| # | Decision (PROPOSED DESIGN) | Alternatives considered | Why |
|---|---|---|---|
| K1 | Base Rev K has **no heel drive**; the heel is a separate front-end module | Heel in every Rev K; no heel at all | The page sensor loses its roll tolerance beside the pod (0.5°); +7 g and +200–360 USD for two modes |
| K2 | **C17200 0.10 mm wires as the coil leads**, the anchor on an axially soft diaphragm | Ti-6Al-4V (cannot carry current); C17200 0.128 mm (SF 1.70, tolerance p5 0.95); C17200 0.08 mm (p5 1.50, +33 % loop loss); Ti wires plus flex jumpers | The only lead path across the moving carrier that adds no new spring element |
| K3 | A **planar ball thrust guide** carries the counter-face couple; sprung races | Wires alone (buckle); pre-tensioned wires (30 × stiffer); blade flexures (two stages, longer) | 0.70 N per wire against 0.009 N of buckling load |
| K4 | **Buildable concentric racetrack coils** inside the bore at the stop | Study B's coil (does not fit); a 26 mm shell; less travel | Km 0.334 / 0.272 N/√W (upper bound) |
| K5 | The **actuator 4.5 mm toward the tip** | Shorter wires (+25 % stress) | The wire anchor must clear the swept face |
| K6 | The **counter-face head**: roll cage ±30°, hinge 9 mm toward the paper, face 6 mm behind it, balance spring, float, captive shoe, three SQL-RV-1.8 | Hinge on the axis (does not fit the bore); full-turn roll (pinion, 1.2 × force margin); a fixed face | Follower motion 0.46 mm over 35–75°; 10.2 × 7.9 mm face |
| K7 | **Pen lift by the follower** (0.5 mm, 0.18 s, 0.08–0.31 J, no holding energy) | A latching lift coil on the float (8 ms) | DEC-050's first candidate; enough for the spelling cue, not for gated modes |
| K8 | **Page sensor at the bottom of a 6.0 mm ring**; the clear window over the top 240° | A larger ring | The smallest ring that passes every rule |
| K9 | **LIR14500** kept | A 10440 cell (about 8–16 h, ASSUMPTION) | Continuity with Rev J.1; 3 × the hours target |
| K10 | **Position servo at 40 Hz, inner loop at ≤ 46 Hz** (the rule allows 46 Hz worst case) | 80 / 100 Hz as study B ran it; 40 / 100 Hz | DEC-050's 2.5 × rule; SIM on the tuning cells: +0.5 % (40 / 100) or +7 % ink error and −29 % nib power (40 / 46) |
| K11 | **Unpowered, the nib rests on its soft stop** (≤ 1.3 mm off centre) and writes as a normal pen | A stiffer suspension (the coil power grows with k²) | REQ-BNIB-011 cannot hold with any suspension soft enough for B1's power |

---

## 9. Open items, with the test or data that closes each

1. **The buildable coil's force constant.** CALC 0.334 / 0.272 N/√W, an upper bound. *EXP-T07* (AC-T07-01) on a coupon of this coil, with the heel variant's notched plates as a second coupon.
2. **C17200 wire leads: fatigue with current and the assembly preload.** *EXP-B25* repeated in C17200 0.10 mm (and 0.08 mm), carrying current, with the anchor diaphragm; target: no failure in 43.2 M cycles at the stop travel. Proposed *EXP-K21*.
3. **The ball thrust guide.** Rolling friction under the couple, race wear, brinelling after drops, the preload springs' release load. Proposed *EXP-K20*.
4. **The counter-face head as a whole.** Follower range, float, lift time, positioner holding force against back-driving, the shoe's capture, the refill change with three brands. *EXP-J17 part (c)* (study B's EXP-B22), extended by proposed *EXP-K23*.
5. **Servo bandwidth and the modes.** *EXP-T10* (AC-T10-02) measures the closed-loop bandwidth and both modes; *EXP-T01* the pre-sliding stiffness that sets the stuck mode (x_pre 5–20 µm assumed).
6. **The page sensor's lift range.** *EXP-T04* (AC-T04-07) on paper with the Rev K window; REQ-BNIB-017 stays unmet until then.
7. **REQ-BNIB-002 against the tilt wobble.** A float brake, or a changed requirement (section 11). *EXP-J17 part (c)* measures the touchdown travel; *EXP-B28* the real wobble.
8. **REQ-BNIB-011.** Reword (section 11); *EXP-T13* (AC-T13-05) checks that the unpowered pen writes.
9. **Grip height at 35°.** Proposed *EXP-K24* (mock-up handles).
10. **Ink visibility with the small front.** *EXP-J15* repeated on the Rev K front.
11. **Centring tolerances.** The clearances fall to 0.21–0.26 mm at the 99th percentile, and the usable travel to 0.99 mm. The first build's measured offsets (EXP-B25 jig) decide whether the clearances grow by 0.1 mm.
12. **The SQUIGGLE supply.** Sold only in volume (AMF-15). A request for quotation, or the micro-stepper fallback, is needed; the fallback changes the lift time and the head's power.
13. **Costs.** Every ASSUMPTION line needs a request for quotation.
14. **Whole-pen simulation of Rev K.** sim2j needs the adapter listed in `sim_params.json`; a test-grid run was not attempted here (proposed EXP-K25).
15. **Beryllium in manufacture.** The C17200 wires must be joined without releasing beryllium: solder or crimp them, or weld under fume extraction (AMF-18). A beryllium-free copper alloy with a fatigue strength near C17200's would remove the issue; a literature search for one is needed.
16. **Face sensor power.** 4–8 mW is Rev J's value for a Hall sampled at 1 kHz. The face only needs touchdown and lift detection, so a lower rate may do (*EXP-J12*'s power log).

---

## 10. Files, commands and run times

| File | What |
|---|---|
| `revk/params.py`, `nib.py`, `frontend.py`, `counterface.py`, `tolerance.py`, `layout.py`, `budgets.py`, `simparams.py`, `figures.py`, `evidence.py`, `servo_sim.py`, `run.py` | the package |
| `revk/tests/test_revk.py` | 17 tests (closed forms, schemas, formats, an end-to-end quick run) |
| `results/revK/revK.json` | every number, with the `stabpen.provenance` block (git revision, the read-only inputs' sha256, parameters, command, versions) |
| `results/revK/layout.json` | the Rev J layout schema: components, fit checks, heel variant, virtual pivot |
| `results/revK/budgets.json` | mass, power, hours, heat, cost |
| `results/revK/sim_params.json` | for sim2 / sim2j |
| `results/revK/evidence_rows.csv` | AMF-250…254 (23 columns, CRLF) |
| `results/revK/servo_bandwidth_sim.json` | section 5.6 (SIM) |
| `results/revK/*.png` + `.csv` | layout side view, mass, power, battery hours |
| `mechanics/cad/revK_pen.py` → `results/revK/revK_pen_assembly.step`, `revK_pen_assembly_heel.step`, `drawing_revK_pen.png` + `.csv`, `revK_cad_summary.json` | the CAD |

Commands (from the repository root):
- `python3 -m revk.run` writes the results in about 15 s (one process). `python3 -m revk.run --quick` runs on coarse grids into the git-ignored `revk/build/quick/` in about 8 s.
- `python3 mechanics/cad/revK_pen.py --heel` builds both STEP files, the drawing and the solid checks in about 7 s.
- `python3 -m pytest revk/tests -q` runs 17 tests in about 11 s.
- `python3 -m revk.servo_sim --variant A|B|C` then `--collect`: 9, 9 and 6 minutes per setting (15 minutes in all on two processes, alongside another study's two).

Caches go in `revk/build/` (git-ignored). Nothing outside `revk/`, `results/revK/`, `mechanics/cad/revK_pen.py` and this file was written.

---

## 11. Proposed rows for the lead

Ranges checked on 2026-09-30:
- decisions: DEC-001…061 are used, so these start at **DEC-062**;
- requirements: no REQ-RVK- prefix exists, so **REQ-RVK-001…**;
- experiments: EXP-K01…K08 are used, so **EXP-K20…** (EXP-B up to B32 and EXP-T up to T17 are used and not touched);
- acceptance criteria: AC-K01…K08 are used, so **AC-K20-01…**;
- evidence: the ledger's largest AMF id is AMF-238, and no study's evidence_rows.csv uses AMF-239…254, so **AMF-250…254** (in `results/revK/evidence_rows.csv`).

### 11.0 Evidence rows

- **New:** AMF-250…254 in `results/revK/evidence_rows.csv` (23 columns, CRLF). AMF-250, 252, 253 and 254 are distributor prices of the TMAG5170A1QDGKR, NRF54L15-QFAA-R, DRV8214RTER and LSM6DSV16XTR (DigiKey, 2026-09-30). AMF-251 is the IBC Advanced Alloys C17200 data sheet (AT(TF00) 22 % IACS minimum).
- **Amendment proposed to AMF-21** (AZoM, Ti-6Al-4V). Add to its findings: "volume electrical resistivity printed as '170 (67)' under ohm.cm (ohm.in), read as 170 µΩ·cm = 1.70 × 10⁻⁶ Ω·m". The unit on the page cannot be ohm·cm.

### 11.1 Decisions

| Id | Decision | Alternatives | Evidence | Revisit if |
|---|---|---|---|---|
| DEC-062 | **Rev K integrated layout** (proposed; refines DEC-050). The Rev J body (24 mm where held, from z 20 mm) with B1 (buildable coils, C17200 wire leads, a ball thrust guide), a 6.0 mm skid ring with the page sensor at its bottom and a clear window, the counter-face head behind the refill, the LIR14500, a cue LRA and charging pads: 145.1 mm, 66.4 g, balance point 74.9 mm | Study B's concept layout (coils do not fit the bore; no coil leads; the couple buckles the wires) | `docs/revK_design.md`, `results/revK/` (CALC; 59 fit checks: 29 pass, 21 marginal, 9 fail, listed; CAD: no solid interference at rest or at the stop) | EXP-T07 gives K_m below 0.7 × 0.334 N/√W; EXP-K20 or K21 fails |
| DEC-063 | **B1's suspension in Rev K**: four 0.10 mm C17200 wires carry the coil currents, on an axially soft anchor; a sprung planar ball thrust guide at the flange carries the counter-face couple and the axial load | Ti-6Al-4V wires (3.5 Ω each); wires alone (0.70 N against 0.009 N of buckling load); pre-tensioned wires; flex jumpers | section 3.3 (CALC) | EXP-K21 (fatigue with current) or EXP-K20 (friction > 5 mN, brinelling) fails |
| DEC-064 | **The counter-face head**: roll cage ±30°, tilt hinge 9 mm toward the paper with the face 6 mm behind it and a balance spring, a float of ±0.56 mm, a captive shoe with a ball joint, three SQL-RV-1.8; the pen lift by the follower (0.5 mm in 0.18 s, no holding energy) | Hinge on the axis; full-turn roll; a lift coil on the float | section 3.4 (CALC) | EXP-J17 (c) / EXP-K23: residual > 25 % of F_s·cot θ, lift > 0.25 s, back-driving under 0.2 N |
| DEC-065 | **No heel drive in the base Rev K**; the heel is a bench front-end module for write-big practice and lead-through (refines DEC-048) | Heel in every Rev K | V1: page sensor roll tolerance 0.5° beside the pod (CALC); +7.0 g, +200–360 USD | EXP-T04 shows a page sensor that tolerates ±20° of roll beside the pod |
| DEC-066 | **Rev K's position servo runs at 40 Hz and its inner loop at ≤ 46 Hz**, inside DEC-050's 2.5 × rule (46 Hz allowed at the worst stuck mode). Study B's SIM ran 80 / 100 Hz; on the tuning writers 40 / 100 Hz costs 0.5 % of ink error and 40 / 46 Hz costs 7 % but saves 29 % of nib power | 80 / 100 Hz (breaks the rule: study B's own 109 Hz stuck mode allows 43.6 Hz) | sections 3.3, 5.6 (CALC; SIM on tuning writers 100–101) | EXP-T10 measures a stuck mode below 100 Hz; EXP-K25 on the test writers loses more than 0.05 of the tremor ratio |

### 11.2 Requirement changes

| Id | Change | Why |
|---|---|---|
| REQ-RVK-001 (new) | Rev K envelope: ≤ 24 mm where held, ≤ 150 mm long, ≤ 75 g with every module | CALC 145.1 mm, 66.4 / 73.4 g; leaves room for the build |
| REQ-RVK-002 (new) | Rev K battery on the LIR14500 at 23 °C: ≥ 16 h in every writing mode up to 2 mm tremor, spelling cue included; ≥ 8 h in lead-through with the heel module; the page sensor on in every mode | CALC low ends: 21.0 h (2 mm), 10.8 h (lead-through); replaces REQ-RVJ-I01's rows for Rev K. Test: EXP-P01 (AC-P01-06) |
| REQ-RVK-003 (new) | The nib's suspension carries the counter-face couple (≥ 11 mN·m at 35°) without any wire in compression beyond 0.5 × its buckling load, and without the carrier tilting by more than 0.2 mrad | N14 (study B's wires: 81 ×); test EXP-K20 |
| REQ-RVK-004 (new) | The moving coils' leads: ≤ 0.3 Ω each and no fatigue failure in 43.2 M cycles at the stop travel while carrying 0.1 A | Section 3.3; test EXP-K21 |
| REQ-RVK-005 (new) | The coils stay ≥ 0.2 mm off the bore at the stop after the centring tolerances (99th percentile), and ≥ 0 mm in a 1 m sideways drop | Section 3.5 (0.21 mm), N21 (0.04 mm) |
| REQ-BNIB-002 (edit) | "at touchdown the full balance returns within 1.0 mm of refill travel at 35° (0.6 mm at 75°), or within 0.25 mm with a float brake" | The float must span the ±2.5° wobble (H6) |
| REQ-BNIB-011 (edit) | "Unpowered, the nib rests on its soft stop (≤ 1.3 mm off centre) and the pen writes like a normal pen" | N22: gravity sags any B1-soft suspension onto its stop |
| REQ-BNIB-017 (note) | Keep as the page sensor's selection requirement; the PMW3610 class gives ±0.2 mm (F5) | EXP-T04 (AC-T04-07) |
| REQ-RVJ-N06 (note) | Rev K meets roll ±20° only with the page sensor at the bottom of the ring (21° tolerance); the heel module breaks it (0.5°) | V1 |
| REQ-RVJ-I01 (note) | For Rev K, see REQ-RVK-002; the autowrite rows apply only to the C1S bench module | DEC-050 |

### 11.3 Experiments (proposed)

| Id | What | Acceptance (proposed) |
|---|---|---|
| EXP-K20 | Ball thrust guide coupon: the carrier flange between two sprung races on 2 × 6 Si3N4 balls, loaded with the 35° couple; lateral sweeps ±1.26 mm at 8 Hz; ten 1 m drops of a dummy pen | AC-K20-01 rolling friction ≤ 5 mN; AC-K20-02 carrier tilt ≤ 0.2 mrad under the couple; AC-K20-03 no race marks after the drops (profilometer), friction unchanged within 20 % |
| EXP-K21 | C17200 wire coupons (0.10 and 0.08 mm, 26.8 mm, the anchor diaphragm) cycled at the stop travel while carrying 0.1 A, as EXP-B25 | AC-K21-01 R ≤ 0.3 Ω per wire; AC-K21-02 no failure in 43.2 M cycles; AC-K21-03 axial preload after assembly ≤ 0.05 N |
| EXP-K22 | The buildable coil in the EXP-T07 coupon (and the notched plates of the heel variant) | AC-K22-01 K_m ≥ 0.7 × 0.334 N/√W (x) and 0.7 × 0.272 (y) over the map |
| EXP-K23 | The counter-face head mock-up on EXP-J17 (c)'s tilting stage: follower range, float, lift, positioner holding, shoe capture, refill change | AC-K23-01 lift 0.5 mm within 0.25 s; AC-K23-02 each positioner moves under its load and holds ≥ 0.2 N unpowered; AC-K23-03 refill change without tools in ≤ 60 s for three brands; AC-K23-04 touchdown travel measured against REQ-BNIB-002 |
| EXP-K24 | Grip-height mock-ups (Rev K's 12 → 24 mm front against an ordinary pen and Rev J's), 20 writers at their own tilt | AC-K24-01 ≥ 80 % of writers never touch the paper with a finger while writing a sentence |
| EXP-K25 | sim2j (or bnib/sim) on the test writers and several seeds with Rev K's sim_params: 40 / 46 Hz against 80 / 100 Hz (after the adapter) | AC-K25-01 the tremor ratio at 8 Hz × 1 mm within 0.05 of the 80 / 100 Hz run; AC-K25-02 tremor-free writing moved ≤ 25 µm |

### 11.4 Gate criteria (proposed)

- **Build Rev K's nib** when EXP-K22 (K_m ≥ 0.7 ×), EXP-K21 (no wire failure) and EXP-K20 (friction ≤ 5 mN, no brinelling) pass.
- **Build the Rev K pen** when EXP-J17 (c) and EXP-K23 pass (residual ≤ 25 % of F_s·cot θ at the 95th percentile; lift ≤ 0.25 s), EXP-T10 measures a stuck mode ≥ 100 Hz, and EXP-T04 shows the page kept through the lifts (or REQ-BNIB-017 is changed).
- **Fit the heel module to a pen** only after EXP-T04 shows a page sensor that tolerates ±20° of roll beside the pod.
