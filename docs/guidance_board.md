# The desk guidance board (study B1)

**Status: proposed design, calculation and simulation. Nothing has been built or measured.** Every number carries a label:

| Label | Meaning |
|---|---|
| CALC | calculated here (magpylib 5.2 magnetostatics, linear dynamics, plate theory) |
| SIM | simulated here (closed-loop guidance on synthetic letter paths with the HAP-26 hand model) |
| MFR (id) | manufacturer statement, with its ledger id |
| LIT (id) | literature, with its ledger id |
| ASSUMPTION | chosen here; section 8 names the experiment that measures it |

Code: [`board/`](../board/__init__.py). One command: `python3 -m board.run_study`. CAD: [`mechanics/cad/guidance_board.py`](../mechanics/cad/guidance_board.py). Results: `results/board/`. Proposed ledger rows: `results/board/evidence_rows.csv` (AMF-90…99, HAP-51…54, PAT-26…27; HAP-55 and PAT-28…30 unused).

The user asked for a way to "actually truly change the pen trajectory" and to "physically change the writing to help spelling or for people with dyslexia". A pen held in the hand cannot push the hand: it has nothing to push against. This board can. It is grounded on the desk and sits under the paper.

## 1. Short answer

**What it is.**
- A flat board, about 300 × 420 × 57 mm and 4 kg (CALC), with a 3 mm glass top.
- An A4 sheet lies on the glass.
- Under the glass, a small XY stage (like a quiet 3D printer) moves a strong permanent magnet around.
- The pen carries one small magnet (a 6.35 × 3.17 mm disc, 0.75 g, MFR AMF-91) in its front sleeve.
- The board pulls the pen's magnet where it wants the pen to go. The force goes into the pen's handle, and so into the hand.

**What it can do for the user.**

| Use | What the board does | Expected effect |
|---|---|---|
| Tracing and copying letters | Pulls the pen back toward the letter when it drifts. It does nothing inside a 1 mm band ("partial") or always pulls gently ("full"). The writer sets the speed. | Tracing error 1.49 → 1.07 mm (partial) and → 0.63 mm (full) for a relaxed writer. With the Rev H nose also correcting the ink: 0.085–0.19 mm (SIM) |
| Spelling practice by dictation (app knows the word) | Guides toward the correct letters. It resists a wrong stroke, then gives way. It can then **demonstrate** the letter: it leads a relaxed hand through it. | It cannot turn a letter the writer is set on into another letter. A reversed 'b' for 'd' stays a 'b' under full guidance (0 % of the bowl on the correct side). With the hand relaxed, lead-through writes the 'd' (94 % correct side, 0.16 mm error) (SIM) |
| Parkinson's "write big" practice | Pulls outward toward large target loops (10 mm, PDT-18). | Loop height 0.83 → 0.93 of target with full guidance (0.88 for a lightly resisting hand) (SIM) |

**What it cannot do.**
- **It cannot overpower the writer.** The usable force is 0.4 N (software cap, ASSUMPTION). A lightly resisting hand moves only 0.35 mm per 0.1 N (CALC). The writer is always in charge.
- **It guides a moving pen, not a still one.** With its magnet engaged it adds about 1 N of downward pull. Static paper friction is then about 0.39 N (CALC from ASSUMPTION μ). So the board cannot start a stationary pen at the 0.4 N cap.
- **The pen feels heavier while guiding.** The extra normal pull is about 1.0 N (CALC) at the normal guidance level, and 0.25 N with the magnet lowered.
- **Guided accuracy is not learning.** The literature shows guidance helps performance while it is on. Learning is shown only in unassisted tests, and physical guidance can hurt it (LIT HAP-01, HAP-02, HAP-05, HAP-06). The board must be used with fading and with unassisted "catch" trials.
- It covers the printable area of an A4 page (A4 minus 15 mm margins) with full force (CALC).

**Answer to "optics, sensors, weights, electromagnets, custom mechanics?"**
- **Custom mechanics:** yes. A CoreXY belt stage from catalogue parts, a glass top and a few machined or printed parts.
- **Magnets:** permanent magnets, not electromagnets. An electromagnet needs about 7 W under the paper for 0.4 N (CALC from LIT HAP-16). Air-core coils need about 390–600 W (CALC). A permanent magnet moved by the stage needs no power to hold its force.
- **Sensors:** a ring of Hall sensors that sees the pen's magnet directly. No optics are needed. A camera is optional, for therapists.
- **Weights:** no. Inertial devices cannot guide (docs/inertial_stabilisation.md §3).

**Recommendation.** Build architecture (i-a): a permanent-magnet head on a CoreXY stage under 3 mm glass, sensing the pen's own magnet with a Hall ring. Let the board do the gross path and the Rev H nose the fine path. Test the guidance laws on people first with a commercial haptic arm (3D Systems Touch, MFR HAP-52), while the board is being built.

## 2. Architectures compared

Figures: `results/board/fig_force_vs_gap.png` (CSV twin), `fig_force_cuts.png`, `fig_force_vs_position.png`. Pen magnet: K&J D42-N52 (MFR AMF-91), 3.8 mm above the paper, axis along the pen at 50° (ASSUMPTION placement). Head: K&J D88-N52 (MFR AMF-90).

### 2.1 Lateral force against the gap (CALC)

The gap is the distance from the top of the paper to the top of the head magnet (paper + cover + running clearance). "Weakest direction" is the force the board can apply in every direction. "Best direction" is the strongest direction. These are the physical limits with the head fully raised. The software cap is 0.40 N (ASSUMPTION).

| Gap (mm) | 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | **3.7 (A4 design)** | 5.0 |
|---|---|---|---|---|---|---|---|---|
| (i-a) axial PM head, weakest direction (N) | 3.37 | 2.82 | 2.38 | 2.01 | 1.72 | 1.47 | **1.20** | 0.84 |
| (i-a) axial PM head, best direction (N) | 3.98 | 3.45 | 3.00 | 2.61 | 2.28 | 1.99 | **1.66** | 1.20 |
| (i-a) extra normal pull, head under the zero-force point (N) | 6.54 | 5.63 | 4.93 | 4.31 | 3.78 | 3.31 | **2.77** | 2.00 |
| (i-c) diametric head, force across the pen azimuth (N) | 2.52 | 2.25 | 2.00 | 1.77 | 1.57 | 1.39 | 1.18 | 0.87 |
| (i-b) electromagnet (Langerak et al.) | 0.488 N at 11 W through their tablet and paper (LIT HAP-16) | | | | | | | |
| (ii) PCB coil pair, force per √W | 0.020 N/√W at 0.8 mm; 0.0077 N/√W at 3.7 mm (CALC) | | | | | | | |

The A5 variant uses 2 mm glass: its gap is 2.7 mm, giving 1.62 N (weakest) and 2.16 N (best) (CALC).

### 2.2 The comparison

| | (i-a) PM head on a CoreXY stage **(recommended)** | (i-b) Electromagnet head (Langerak) | (i-c) Rotating diametric PM head | (ii) Planar coil array | (iii) Pantograph linkage to the pen | (iv) Macro-mini: board + Rev H nose |
|---|---|---|---|---|---|---|
| Lateral force at 0.5–3 mm | 3.37–1.47 N weakest direction; 1.20 N at the 3.7 mm A4 gap (CALC) | 0.49 N at 11 W (LIT HAP-16) | 2.52–1.39 N; 1.18 N at 3.7 mm (CALC) | 0.4 N needs 394 W per coil pair at 0.8 mm (CALC) | no gap; 0.86–0.95 N worst direction over A5 with 0.15 N·m motors (CALC); 3D Systems Touch 3.3 N peak, > 0.88 N continuous (MFR HAP-52) | as (i-a) on the handle; the nose adds 0.21 N continuous and ±3 mm at the tip (results/revH) |
| Normal pull | 2.3–2.5 × the capability chosen by the Z-lift, about 1.0 N at a 0.4 N setting (CALC) | similar per newton; zero when the coil is off | 0 across the pen azimuth; +0.93 N (up) at full force along it (CALC) | can be zero (anti-phase coils) | none, but the linkage adds about 0.10 kg apparent mass (CALC; Touch 45 g, 0.26 N backdrive friction, MFR HAP-52) | as (i-a) |
| Workspace | A4 printable area (218 × 299 mm head travel); A5 variant (CALC) | as (i-a) | as (i-a) | any; the cost scales with area | A5 with 160/220 mm links; A4 needs 220/300 mm links, 0.62–0.69 N (CALC) | as (i-a) |
| Bandwidth, latency | about 25 Hz force bandwidth; about 8 ms effective latency (CALC) | current > 100 Hz, but the carriage must still follow; about 20 ms total (LIT HAP-16) | direction set by a rotary axis, about 30 ms per 180° (ASSUMPTION) | > 100 Hz, about 2 ms | > 100 Hz, about 1 ms | board about 25 Hz; nose 80 Hz servo (results/revH) |
| Position accuracy at the ball | 0.18 mm noise (median); bias removable by calibration (CALC, §4) | tablet 6502 DPI (LIT HAP-16) | harder: the head field turns with the magnet | unproven | 0.01–0.06 mm from encoders (MFR HAP-52, LIT HAP-53) | the nose knows its own deflection |
| Power and heat | 0 W to hold the force; about 7 W average in the steppers at the back (CALC) | about 7.4 W for 0.4 N under the paper (CALC from LIT); needs a fan | as (i-a) plus a small motor | tens to hundreds of W under the paper | a few W beside the page | as (i-a); the pen spends nothing on the board's force |
| Noise | steppers and belts; the driver's quiet mode is claimed inaudible at low speed (MFR AMF-93); to be measured | fan + stage | as (i-a) | silent | quiet; some cogging | as (i-a) |
| Safety | force limited by the magnets; nothing moving above the glass; loss of power leaves only a passive pull | force off with power off | as (i-a) | heat | active device beside the hand; pinch points; tethered pen | as (i-a); the nose is held central in learning modes |
| Pen add-on (mass) | one D42-N52 disc, 0.75 g (MFR AMF-91) | a ring magnet | as (i-a) | as (i-a) | a collar and rod, 10–20 g (ASSUMPTION) | as (i-a) |
| Build difficulty | moderate: 3D-printer-class mechanics, catalogue electronics, one calibration jig | moderate; the thermal design is hard | moderate–hard: 4 axes | hard: about 165 driver channels for A4 (CALC from LIT HAP-54 pitch) | moderate for A5 (kits exist); hard for A4 | as (i-a) plus a BLE link |
| Verdict | **choose** | reject: heat under the hand | upgrade path if the normal pull is disliked | reject: power | best for lab studies of guidance laws (buy a Touch); not for home use | **how (i-a) is used** |

**Why the magnet is on the handle, not the nose.** The Rev H nose actuator carries only 0.21 N continuously, on a 12 N/m suspension (results/revH/tip_params.json, CALC by the Rev H study). A 0.4 N board force on the nose would slam it onto its stop and drain the pen's cell. So the magnet sits in a small keel under the **fixed** front sleeve. The board's force goes straight into the handle.

**Why not the nose ring magnet.** A 5 × 2.5 × 3 mm ring on the nose was the provisional choice. It gave only 0.45–0.52 N at 2.5–3 mm gaps (CALC, `board_params_provisional.json`). The heel disc is closer to the paper and larger, and gives 2–3 times more.

**Why the magnet axis lies along the pen.** A disc magnetised along the pen axis lets the sensor ring see which way the pen points. The board needs that to place the ball, 16.5 mm in front of the magnet (§4). A vertical disc would give about twice the force (2.36 N weakest direction at 3.7 mm, CALC) but hides the pen azimuth.

**What "better idea" (iv) adds.** The board and the nose form a macro-mini pair:
- the board moves the hand along the gross path, at up to 0.4 N and 25 Hz;
- the nose moves the ink by up to ±3 mm at 80 Hz.

In the simulation, tracing error falls from 1.49 mm to 0.085 mm with both (SIM, §5). A second idea was noted but not studied: a passive "cobot" pen that steers a wheel on the paper (PAT-27, expired). It would use the paper as ground with no board.

## 3. Forces and the hand

Hand model (LIT HAP-26; config/parameters.yaml). The pen (75 g, Rev H) connects through the grip (k1 575 N/m, b1 1.3 N·s/m) to the hand and arm mass (0.21 kg). That mass connects through the arm (k2 170 N/m, b2 11 N·s/m) to where the writer means to be. The model is passive: the writer does not resist on purpose. Two further cases stand for resistance:
- "lightly resisting": the arm at the HAP-26 upper 95 % CI (533 N/m, 27.6 N·s/m), ASSUMPTION for co-contraction;
- "hand held still": only the grip yields.

Figure: `fig_hand_deflection.png` (CSV twin).

### 3.1 Deflection per 0.1 N (CALC)

| Hand | static | 1 Hz | 2 Hz | 4 Hz | 8 Hz |
|---|---|---|---|---|---|
| Relaxed (HAP-26 nominal) | 0.76 mm | 0.75 | 0.69 | 0.47 | 0.20 |
| Relaxed, soft (HAP-26 lower CI) | 2.02 | 2.22 | 2.45 | 0.67 | 0.45 |
| Lightly resisting | 0.36 | 0.35 | 0.34 | 0.30 | 0.28 |
| Hand held still (grip only) | 0.17 | 0.18 | 0.18 | 0.19 | 0.26 |

### 3.2 Nudge or steer

**A nudge** corrects the path by up to about 1 mm; the writer feels it and follows. **Steering** moves the pen by letter-sized amounts, 3 mm or more, whatever the writer does.

Force needed (CALC):

| Correction | Relaxed | Lightly resisting | Hand held still |
|---|---|---|---|
| 1 mm at 1 Hz | 0.13 N | 0.28 N | 0.57 N |
| 1 mm at 4 Hz | 0.21 N | 0.34 N | 0.53 N |
| 3 mm at 1 Hz | 0.40 N | 0.85 N | 1.72 N |
| 3 mm at 4 Hz | 0.64 N | 1.01 N | 1.59 N |

With 0.3 N and a writer who does not resist, the pen moves (CALC):
- 2.3 mm (static), 2.2 mm at 1 Hz and 1.4 mm at 4 Hz for a relaxed hand;
- 1.1 mm for a lightly resisting hand;
- 0.5 mm for a hand held still.

So:
- **At the 0.4 N cap the board nudges any writer and steers only a relaxed one.** This matches the guidance literature. Bluteau's springs were 0.4–0.6 N/mm (LIT HAP-10). KATIB's and Langerak's magnets gave 0.43–0.49 N (LIT HAP-15, HAP-16, HAP-51).
- **The board could steer harder.** It has 1.2 N at the lowest head position (CALC). But the normal pull then reaches 2.8 N, which is uncomfortable. The cap is a choice to test (EXP-G07).
- **Friction sets a floor.** With about 1 N of magnetic pull, the skid needs about 0.39 N to start and 0.30 N to keep sliding (CALC; μ 0.15 and a 1.3 static ratio, both ASSUMPTION). The board therefore guides a moving pen. The simulation charges this drag to the writer as an uncompensated force.

## 4. Sensing: the board must know where the pen is

| Option | Rate | Latency | Accuracy | Verdict |
|---|---|---|---|---|
| EMR digitiser under the glass (Wacom type) | 133–200 points/s (MFR AMF-98) | ≥ 5–8 ms + interface (CALC) | ±0.25 to ±0.4 mm (MFR AMF-98) | **Reject for this board.** OEM modules can be bought: Wacom sensor boards of 6–14 inch, 2.7 mm thick in a 2010 catalogue; Hanvon Ugee EMR modules for integration (MFR AMF-98). But Wacom calls a digitiser "sensor boards ... and magnetic sheets" (MFR AMF-98). A soft-magnetic sheet between the head and the pen would short the head's field, and the moving magnet and steel stage would disturb the EMR field. EMR pen coils sit on ferrite, which the head would also pull. Spare EMR refills were seen only in a search summary, not verified. |
| The pen's own sensors over BLE (Rev H paper sensor + IMU) | 1 kHz inside the pen; 67–133 Hz over BLE (ASSUMPTION) | 10–20 ms (ASSUMPTION) | relative only; drifts | **Secondary**: pen-down flag, tilt, pen-up tracking, the nose deflection |
| Camera above the page | 30–120 fps (ASSUMPTION) | 20–50 ms (ASSUMPTION) | 0.2–0.5 mm; the hand hides the tip | **Optional**: page registration and video for therapists |
| **Carriage Hall ring + stage position** | **1 kHz** | **about 1.5 ms** sensing (CALC) | 0.18 mm noise at the ball, median (CALC) | **Choose** |

**How the Hall ring works.**
- Eight 3-axis Hall sensors (TI TMAG5170A2, MFR AMF-95) sit on a ring of 18 mm radius on the carriage, just under the glass, around the head magnet.
- The head's own field is the same at every sensor on the ring, because the head is round. At the sensors it is at most 24 mT, inside the ±75 mT range (CALC).
- The firmware removes it with a per-sensor calibration at each Z-lift height, plus one common scale factor fitted on line. That factor absorbs the magnet's temperature drift (-0.12 %/K, MFR AMF-27).
- What remains is the pen magnet's field, 3–30 mT at the ring (CALC).
- A fit gives the pen magnet's position and axis relative to the head. The stage's step count, after homing, makes it absolute.
- The ball is 16.5 mm in front of the magnet, along the fitted pen azimuth.

**Monte Carlo (CALC; `board.sensing`; noise from AMF-95 with 8× averaging).**
- Magnet position noise: 0.06 mm RMS (median).
- Ball position noise: 0.18 mm median, 0.40 mm worst. The azimuth error is multiplied by the 16.5 mm lever.
- A simple point-dipole fit leaves up to 0.8 mm of bias at the ball when the head is 12–15 mm from the pen.
- The same fit with the exact disc model recovers the pose from noise-free data. So the bias comes from the model, not from the physics.
- The firmware must therefore use the closed-form cylinder field or a calibration table (EXP-G03).
- Without averaging, the ball noise is 0.44 mm (median).

**Timing (CALC; conversion times MFR AMF-95).**

| Step | Time |
|---|---|
| Sensor conversion (3 axes, 8× averaging) | 0.6 ms |
| SPI read of 8 sensors | 0.1 ms |
| Pose fit | 0.2 ms (ASSUMPTION) |
| Control | 0.1 ms |
| Step generation | 0.5 ms |
| Stage response, as an equivalent delay | 6.4 ms |
| **Effective total** | **7.9 ms** |

Langerak et al. measured about 20 ms total on a slower stage (LIT HAP-16).

## 5. Control and safety

### 5.1 Guidance law

- **Time-free progress** (LIT HAP-16). The target is the point of the letter path closest to the pen. It is searched only a little behind and ahead of the last one, so the writer sets the speed and the target never runs ahead in time.
- **Partial guidance** (LIT HAP-13/14/15, HAP-03). No force inside a 1 mm band around the path. Outside it, a spring of 0.10 N/mm pulls toward the path, with light damping (ASSUMPTION values).
- **Full guidance.** A 0.20 N/mm spring with no band. While the writer moves forward, a 0.10 N pull along the path is added (ASSUMPTION).
- **Lead-through (demonstration).** The board pulls the pen along the letter with 0.3 N while the writer relaxes. The pull must exceed the extra skid friction of about 0.15 N (CALC); the first try at 0.1 N did not move the pen (SIM).
- **Authority** g from 0 to 1 scales every force. The app sets it and fades it with practice, as in HAP-03: g ← f·g + k·error with f < 1.
- **Guidance level.** The head's height (Z-lift) sets the force available:

| Head gap | Force available (weakest direction) | Normal pull |
|---|---|---|
| 3.7 mm (fully raised) | 1.20 N | 2.77 N |
| 6 mm | 0.65 N | 1.58 N |
| 8 mm (default) | 0.41 N | 1.01 N |
| 11 mm | 0.22 N | 0.56 N |
| 15.7 mm (fully lowered, "off") | 0.10 N | 0.25 N |

All CALC. At the default the offset-to-force slope is 0.105 N/mm, so a 0.5 mm stage error changes the force by only 0.05 N (CALC).
- **Force allocation.** The firmware turns the wanted force into a head offset. It looks the offset up in a map calibrated for gap and pen tilt. Within ±24 mm offsets, 0.71 N can still be given in every direction with the normal force kept within ±0.3 N (CALC). This far-branch mode is the fallback if the 1 N pull is disliked.

### 5.2 How each practice mode uses it

- **Tracing and copying.** The template comes from the app, so the letter is *known*. docs/ai_guidance.md found that known templates help, while AI-predicted ones did not help in free writing. Default: partial guidance, then fading, then an unassisted catch letter about every fifth letter (LIT HAP-08).
- **Dictation spelling.** The app says the word and knows its letters. It shapes them in the user's style (aiguide) and anchors the word at the first pen-down.
  - Partial guidance resists a wrong first stroke.
  - The supervisor gives way when the writer insists (it yielded 4 times in the reversal run, SIM).
  - The app then speaks a cue, the board demonstrates the letter with lead-through, and the writer tries again unassisted.
  - This follows "demonstrate, assist, then unassisted" (LIT HAP-07).
  - The board never forces the letter: it cannot, and HAP-22/23 advise against it.
- **Parkinson's "write big".** Large loop targets, at least 1 cm (LIT PDT-18). The dose follows Nackaerts (30 min × 5/week × 6 weeks, LIT PDT-16). Size and fluency are scored together, because size training can cost fluency (LIT PDT-17).

### 5.3 Board and nose together

- The board acts on the **handle's** gross error. That is the ink position minus the nose deflection, which the pen reports over BLE.
- In **learning** modes the nose is held central, so the writer's own error stays visible (LIT HAP-01, HAP-05, HAP-06).
- In **assist** modes the nose moves the ink the last few millimetres.
- Tremor cancellation in the nose runs as usual in all modes.

Simulated tracing error, relaxed writer:

| | Nose held central | Nose assisting |
|---|---|---|
| No board force | 1.49 mm | 0.19 mm |
| Partial | 1.07 mm | 0.13 mm |
| Full | 0.63 mm | 0.085 mm |

### 5.4 Safety

| Hazard | Design answer | Check |
|---|---|---|
| Too much force | Software cap 0.40 N and slew limit 8 N/s (ASSUMPTION). The magnets themselves cannot exceed about 1.2 N at the 3.7 mm gap (CALC) | EXP-G06 |
| Fighting the writer | Supervisor fades the force to zero if the error stays above 4 mm for 0.3 s, and restores it slowly (LIT HAP-22/23) | SIM; EXP-G05 |
| Pen lifted | Force to zero; head lowered | EXP-G06 |
| Stall or lost steps | TMC2209 StallGuard (MFR AMF-93); step count checked against the Hall ring; stop on mismatch | EXP-G06 |
| Pinch points | All moving parts sit under the glass inside the frame. Nothing moves above the writing surface | CAD |
| Glass | 3 mm chemically strengthened glass with an anti-shatter film. It touches the head only at about 72 N of hand load (CALC). A 100 N lean gives 21 MPa of stress (CALC) | EXP-G06 |
| Magnets | 12.7 mm N52 magnet enclosed in an aluminium cup. Warning labels for implants, cards and watches. The field map around the board is to be measured (ASSUMPTION pass line: 0.5 mT at 15 cm) | EXP-G06 |
| Electrical | External 24 V adaptor certified to IEC 62368-1 (MFR AMF-97). Hardware stop button cuts the driver enables | EXP-G06 |
| Heat | No heat under the page. The steppers (about 4 W each while moving, CALC) sit in the back housing | EXP-G04 |
| Power loss | Motion stops. At most the passive magnet pull remains (about 1 N at the default level) | EXP-G06 |

### 5.5 Firmware sketch (nRF54L15, 1 kHz)

```
every 1 ms:
  B = read_ring(8 x TMAG5170)                         # 0.7 ms incl. conversion
  pose = fit(B - s*Bhead_cal[z_lift], init=pose)      # x, y, z, alt, az (+ s)
  ball = stage_xy + pose.xy - lever*dir(pose.az) + nose_q_from_pen   # BLE, 7.5-15 ms old
  if not pen_down(pose.z, pen_force_flag): F = 0; lower_head(); continue
  s, g_pt, t, n = template.project(ball - nose_q, s_prev)             # time-free progress
  F = law[mode](e = handle - g_pt, n, t, v) * authority
  F = supervisor(F)                                   # cap, slew, override fade
  offset = allocation_map[z_lift, tilt](F)            # calibrated force -> head offset
  step_targets(stage_xy_target = magnet_xy + offset)  # input-shaped moves, <= 300 mm/s
  watchdog(); log(ICD)
every 20 ms: set z_lift from the guidance level (servo, current-based position mode)
```

## 6. Recommended design

### 6.1 Bill of materials (catalogue parts)

| Item | Qty | Part | Key data | Ledger | Price seen |
|---|---|---|---|---|---|
| Head magnet | 1 | K&J D88-N52, 12.7 × 12.7 mm, axial | N52, Br max 1.48 T, 12.07 g, 80 °C | AMF-90 | USD 4.78 (2026-09-28) |
| Pen magnet (in the pen) | 1 | K&J D42-N52, 6.35 × 3.17 mm, axial | N52, 0.75 g, 80 °C | AMF-91 | USD 0.52 (qty 1–49) |
| Stage motors | 2 | StepperOnline 17HS19-2004S1 NEMA 17 | 0.59 N·m, 2.0 A, 1.40 Ω, 3.0 mH, 82 g·cm², 0.40 kg | AMF-92 | – |
| Motor drivers | 2 | ADI/Trinamic TMC2209 | 2 A RMS, 2.8 A peak, 4.75–29 V, StealthChop2, StallGuard4 | AMF-93 | – |
| Guides | 2 + 1 | HIWIN MGN12H (Y), MGN9H (X) | H 13 / 10 mm; blocks 54 / 26 g; rails 0.65 / 0.38 kg/m | AMF-94 | – |
| Hall sensors | 8 | TI TMAG5170A2 | ±75/150/300 mT; 10 MHz SPI; 160 µT RMS noise (28 µT with 32×) | AMF-95 | – |
| Z-lift servo | 1 | ROBOTIS XL330-M288-T | 0.52 N·m stall at 5 V; 12-bit encoder; current-based position mode; 18 g | AMF-96 | – |
| MCU + Bluetooth LE | 1 | Nordic nRF54L15 (same family as the pen) | 128 MHz Cortex-M33, 256 KB RAM | AMF-44 (existing) | – |
| Power supply | 1 | MEAN WELL GST60A24-P1J (external) | 24 V 2.5 A, 90.5 % efficiency, IEC 62368-1 | AMF-97 | – |
| Belts, pulleys, idlers | set | GT2 6 mm, 20T pulleys (to select) | belt stiffness not published: ASSUMPTION 15–40 kN | – | – |
| Variant only | (1) | K&J D8X0DIA, 12.7 × 25.4 mm, N42, diametric | 24.14 g | AMF-99 | USD 8.05 |

No cost class is claimed for the whole board. Only the magnet prices were seen.

### 6.2 Custom parts

| Part | Dimensions (mm) | Material, process | Why |
|---|---|---|---|
| Glass writing surface | 300 × 372 × 3 (A5 variant: 2) | chemically strengthened glass, anti-shatter film; cut and edge-ground | Stiff (0.07 mm under 10 N), thin enough for the field |
| Base plate | 300 × 420 × 3 | aluminium 5052/6061, laser-cut | non-magnetic ground |
| Frame walls and glass rim | 3 mm walls, 42 mm high | aluminium sheet; PA12 corners | carry the glass edge; enclose all moving parts |
| Gantry beam | 280 × 20 × 10 tube | aluminium 6063 | carries the MGN9 rail |
| Carriage plate and cantilever | about 33 × 65 × 3, with a Ø20 hole | aluminium | holds the head 25 mm in front of the X rail, so it can drop 12 mm beside the beam |
| Z parallelogram and magnet cup | cup Ø16; two 40 mm links | aluminium cup; POM or PA12 links; brass pins | keeps the magnet upright over 12 mm; keeps it ≥ 20 mm from the steel rail (≤ 0.8 N pull, CALC image-dipole bound) |
| Hall ring PCB | OD 44, ID 20, 1.0 thick; sensors at r 18 | FR4, 4 layers | pen localisation |
| Main PCB | 100 × 40 | FR4, 4 layers | nRF54L15, 2 × TMC2209, 24 → 5/3.3 V, servo bus, stop input |
| Pen keel (for the Rev H team) | pocket Ø6.45 × 3.3; magnet centre 13.5 mm along the axis and 10.2 mm off-axis toward the paper | PEEK front sleeve | puts the D42 3.8 mm above the paper and 16.5 mm behind the ball at 50°, outside the nose bore (r 6.47 mm) |
| Paper stop, underlay, arm-rest wedge | L-stop 2 mm high; 0.2 mm PET; wedge 300 × 80, 0 → 50 | PA12, PET, PU foam | registers printed sheets; smooth feel; the surface is 45 mm above the desk |

### 6.3 Electronics

- **Supply:** 24 V from the external adaptor, fused, reverse-protected, with a buck converter to 5 V (servo, sensors) and 3.3 V (MCU).
- **Drivers:** 2 × TMC2209 in step/dir mode. StealthChop at low speed. Run current 1.2 A RMS with standby reduction.
- **Sensors:** 8 × TMAG5170 on one SPI bus at 10 MHz, each with its own chip select.
- **Other:** servo on its TTL bus; BLE to the pen and to the phone; hardware stop button in series with the driver enables.
- **Power (CALC from MFR data, ASSUMPTION duty):** 6.9 W average, 7.6 W at the wall, 18 W peak. The magnets need nothing to hold their force.

### 6.4 CAD and size

- **CAD:** `mechanics/cad/guidance_board.py` writes `results/cad/guidance_board_assembly.step`, `guidance_board_summary.json` and `drawing_guidance_board.png` (copied to `results/board/fig_cad_drawing.png`, with a CSV of every component).
- **Size (CALC):** 300 × 420 × 57 mm. The writing surface is 45 mm above the desk.
- **Mass (CALC):** about 4.1 kg. Catalogue masses were used where known; everything else is volume × density (ASSUMPTION).
- **Checks (CALC):** no interference at the working and lowered head heights, nor at the four corners of the head travel (36–254 × 25–324 mm).
- **Stage performance (CALC):** top speed about 510 mm/s; acceleration 157–273 m/s² at 200 mm/s, against about 18 m/s² needed to follow writing and change the force.

## 7. Assumptions that matter most

| Assumption | Value | Why it matters | Measured by |
|---|---|---|---|
| Pen magnet placement | 3.8 mm above paper, 16.5 mm behind the ball, axis along the pen | Force scales steeply with height | Rev H CAD; EXP-G01 |
| Magnet grades | Br 1.45 T (N52 lower bound, AMF-28) | ±2 % force per % Br | EXP-G01 |
| Pen tilt | 50° nominal; 35–75° gives 1.03–1.41 N (weakest direction, 3.7 mm gap, CALC) | Force map and zero point move with tilt | EXP-G01 |
| Hand impedance | HAP-26 nominal and CI; no voluntary resistance | Sets nudge vs steer | EXP-G05, EXP-G07 |
| Skid friction | μ 0.15, static 1.3× | Floor under which the board cannot move a still pen | EXP-G05 |
| Belt stiffness | 25 kN per unit strain (15–40) | Belt mode 75 Hz, bandwidth 25 Hz | EXP-G02 |
| Sensor calibration residual | 20 µT; head-field scale error 0.5 % | Ball accuracy | EXP-G03 |
| Force cap and gains | 0.40 N; 0.10 / 0.20 N/mm; 1 mm band | Comfort and effect | EXP-G07 |
| Users accept about 1 N extra normal pull | – | If not, use the far-branch allocation or the diametric head | EXP-G07 |
| Guided area | A4 minus 15 mm margins | Head travel and board size | – |

## 8. Bench experiments (measurand, method, pass line)

Dependencies to run everything here: Python 3.11 with numpy, scipy, matplotlib, magpylib 5.2.3 and cadquery 2.8.0 (`requirements.txt`). The pass lines are proposals.

| ID | What | Method | Pass line |
|---|---|---|---|
| **EXP-G01** Force map | Lateral and normal force on the pen magnet against head offset, gap and tilt | D42 in a Rev H front-sleeve dummy on a 3-axis load cell (Nano17 class, as in the bench rig) above the D88 head on a manual XY/Z stage. Glass and paper in between. Grid ±16 mm at 0.5 mm; gaps 3.7, 5, 8, 11 mm; tilts 35/50/75° | Within ±15 % of `fig_force_vs_gap.csv` and `fig_force_cuts.csv`; normal pull within ±20 % |
| **EXP-G02** Stage and latency | Head position response and delay from sensing to force | Chirp and steps on the stage (laser displacement sensor); timestamp from Hall-ring sample to step output (GPIO + scope); replay recorded writing trajectories | Position bandwidth ≥ 15 Hz; effective latency ≤ 12 ms; tracking error ≤ 0.2 mm RMS on writing trajectories |
| **EXP-G03** Localisation | Ball position error of the Hall ring | Pen dummy with the D42 on a calibrated XY stage (or a CNC), 3 tilts, 4 azimuths, head fixed; then head moving | ≤ 0.3 mm RMS and ≤ 0.6 mm max over offsets ≤ 12 mm, after one calibration |
| **EXP-G04** Noise and heat | Sound level; temperatures | Sound level meter at 0.5 m, A-weighted, during tracing replay; thermocouples on motors, drivers, glass | ≤ 35 dB(A) at 0.5 m (ASSUMPTION target); glass top ≤ 5 K above ambient after 30 min; motor case ≤ 60 °C |
| **EXP-G05** Hand simulant | Guidance accuracy against SIM | A two-stage spring–mass–damper "hand" set to HAP-26 nominal and to the stiff-arm case, holding a Rev H dummy pen. A second stage drives it along "intended" paths with 1.5 mm RMS errors (the SIM paths) | Full guidance cuts the ink error by ≥ 40 % (relaxed setting); results within ±30 % of `board.json` → simulation; supervisor yields within 0.5 s when the simulant is stiffened |
| **EXP-G06** Safety | Force cap, faults, stop, glass, stray field | Load cell under fault injection (sensor dropout, wrong template, stall, BLE loss); stop button timing; 100 N lean test; field map with a gaussmeter | Force never > 0.44 N; stop < 50 ms; power loss = no motion; no glass–head contact at 70 N; field ≤ 0.5 mT at 15 cm from the case (ASSUMPTION threshold, to confirm with the applicable standard) |
| **EXP-G07** People | Effect and acceptance | Phase A: 3D Systems Touch (MFR HAP-52) with a pen adapter to compare partial, full and lead-through on adults. Phase B: board prototype with adults. Phase C: children with dysgraphia or dyslexia, and people with PD, with ethics approval. Measure assisted and **unassisted** error, retention after 1 day and 1 week, legibility, speed, fluency (velocity peaks, jerk), letter size (PD), SOS score (LIT PDT-27), comfort with the normal pull | Unassisted retention better than practice without guidance (an effect size to be set in the protocol); no increase in fatigue; normal pull rated acceptable by most participants |

## 9. Files

| File | What |
|---|---|
| `board/params.py` | every design value with its label and source |
| `board/magnetics.py` | force maps (magpylib), coil and electromagnet options, dipole cross-check |
| `board/hand.py` | HAP-26 hand model: deflection, nudge/steer, forces needed, friction |
| `board/stage.py` | CoreXY: torque–speed, modes, bandwidth, latency, power, glass plate |
| `board/sensing.py` | Hall-ring Monte Carlo; sensing options |
| `board/control.py` | guidance law, supervisor, closed-loop simulation, practice scenarios |
| `board/architectures.py` | comparison table; five-bar pantograph model |
| `board/bom.py` | BOM, custom parts, proposed ledger rows |
| `board/layout.py` | geometry for the CAD and `layout.json` |
| `board/run_study.py` | `python3 -m board.run_study` (about 2–3 min; `--no-cad`, `--quick`) |
| `board/tests/` | `python3 -m pytest board/tests -q` (19 tests) |
| `mechanics/cad/guidance_board.py` | CadQuery model → `results/cad/guidance_board_assembly.step`, `guidance_board_summary.json`, `drawing_guidance_board.png` |
| `results/board/board.json` | all results with provenance |
| `results/board/board_params.json` | interface for the handwriting-outcomes study (supersedes `board_params_provisional.json`) |
| `results/board/layout.json` | components for the 3-D explainer (board frame, `carriage_travel`, `pen_magnet`) |
| `results/board/evidence_rows.csv` | proposed ledger rows (23-column header of docs/evidence.csv) |
| `results/board/fig_force_vs_gap.png`, `fig_force_vs_position.png`, `fig_force_cuts.png`, `fig_hand_deflection.png`, `fig_guidance_sim.png`, `fig_cad_drawing.png` | figures, each with a `.csv` twin |
