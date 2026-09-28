# Inertial, gyroscopic, grip and paper-pivot stabilisation for the pencil (study I1, model H1)

**Status: calculation and simulation. Nothing here has been built or measured.** Every number carries a label:

| Label | Meaning |
|---|---|
| CALC | calculation from labelled inputs |
| SIM | simulation (model H1 in `sim/handpen/`, or model P1 where stated) |
| MFR (id) | manufacturer statement, ledger id |
| LIT (id) | literature, ledger id |
| ASSUMPTION | chosen here; the experiment that would measure it is named |

New ledger rows are in `results/pencil/inertial_evidence_rows.csv` (HAP-31…35, ACT-27…34, AMF-49…52). Results: `results/pencil/inertial.json`, `inertial_viz.json` (3-D replay), `fig_inertial_*.png`. Code: `sim/handpen/`.

The question from the user: *can inertial "3-axis side-to-side" masses, gyroscopes, or a pivot at the grip, the cap or the paper help a pencil-sized pen, and what combination of AI and physical help really works?* This study answers the physical half. The accelerometer and estimation half is a separate study.

## 1. The answer

### In plain language

- **Weights, gyroscopes and moving masses in the cap do not help much.** At the largest size that fits a 8.9 mm pen, and even with perfect knowledge of the tremor, they remove about 3–15 % of the ink tremor at 0.3 mm. That is a small fraction of what the piezo nib stage already removes (57–81 %). The reason is scale. The hand pushes the pen around with about 0.1–0.2 N through the fingers. A few grams moving ±1 mm inside the cap can push back with only 2–30 mN. A gyroscope pushes back only when the pen *rotates*, and in tremor the pen barely rotates (1–2 thousandths of a radian).
- **A 50 % cut would need a moving mass or gyroscope 1.4–25 times bigger than what fits** (reaction wheels: 45–95 times more torque). The only inertial device that comes close is a control-moment gyroscope: two pairs of spinning tungsten rotors on motorised gimbals. With perfect control it removes 8–24 %. But it weighs about 25 g, draws about 0.34 W and leaves no room for the battery.
- **"Pivot" ideas at the paper or in the grip filter the writing as much as the tremor.** More skid friction, a damping roller at the nose or a soft grip sleeve all lower the tremor in the ink. But tremor (4–12 Hz) and handwriting strokes (3–7 Hz) share the same frequencies, so these passive filters also shrink and delay the letters. Measured against what the writer meant to write, the net effect is close to zero (−7 % to +25 %).
- **A Liftware-style motorised grip does not fit a pencil.** It would move the whole barrel, so its motors would have to hold the paper's full sideways push (0.74 N). That costs about 2 W with the best coil the project has, and needs a grip at least 15 mm thick.
- **What does work physically is the piezo nib stage behind the skid.** It moves only the refill, not the whole pen, so it carries only 0.17 N. With perfect knowledge of the tremor it leaves 0.19–0.43 of the ink error at 0.3 mm tremor. It does not need any of the cap devices.
- **The "combination of AI and physical help" is therefore: AI decides, the nib stage acts.** No passive mechanism can tell tremor from writing, because they overlap in frequency. Only an estimator can, whether it uses accelerometers, the pen's own model or AI. The nib stage is the physical actuator that turns that decision into better ink. Cap devices would only help the stage where it runs out of travel. That happens with large tremor (0.3–0.5 mm at 8–12 Hz), and even there a cap device does not fit the envelope.

### The numbers

All values below are for 50° tilt and 1 N writing force, with the nominal grip split (§3.2, ASSUMPTION). Tremor is a 0.3 mm hand-path tremor unless stated. Results are the mean of 4 test seeds (200–203).

- **Nib stage alone** (P1 limits, perfect knowledge): ink-error ratio 0.19 / 0.23 / 0.30 / 0.38 / 0.43 at 4 / 6 / 8 / 10 / 12 Hz (SIM, H1). Model P1 gives 0.20–0.46 on the same grid (SIM, `sim_metrics.json`). H1's stage is idealised, so use P1 for the stage's absolute value and H1 for what a helper adds.
- **Best inertial helper within the 20 g target:** a 5.15 g tungsten slug in the cap, moved ±1.0 mm sideways and ±2 mm axially (3 axes, "side-to-side" plus axial). Ratio 0.97 / 0.96 / 0.93 / 0.88 / 0.85 (SIM). It uses 0.002–0.28 W and needs half the cell's space. That halves the battery (CALC).
- **Best inertial helper regardless of budget:** two scissored pairs of control-moment gyroscopes. Ratio 0.92 / 0.89 / 0.87 / 0.88 / 0.88 at 0.3 mm, and 0.76–0.83 at 0.1 mm (SIM). About 25 g and 0.34 W (CALC, MFR AMF-50/51); it does not fit beside the cell.
- **Passive gyroscope, reaction wheels, tuned mass damper, heavier cap:** tuned mass 0.92–1.07, gyroscope 0.97–1.00 (SIM), wheels 0.96–0.99 (CALC). A +10 g cap helps only at 12 Hz (0.78 in band), where it moves a pen resonance (SIM). None of these is useful, and a tuned mass or heavy cap can make some frequencies worse.
- **Stage plus helper:**
  - Stage alone 0.19–0.43 → with the tungsten reaction mass 0.17–0.31 → with the CMG pairs 0.14–0.29 (SIM).
  - Time at the stage's travel limit at 12 Hz: 62 % → 52 % (reaction mass) → 45 % (CMG) (SIM).
  - Helpers are worth more *with* the stage than alone, because they shave the peaks the stage cannot reach.
- **Wrist-rotation tremor** (0.3 mm at the nib from a wrist rotation about a pivot 150–200 mm behind the grip): reaction mass 0.93–0.99, CMG 0.84–0.93, stage 0.21–0.43 (SIM). Gyroscopic devices are not better here than on hand-path tremor.
- **Size for a 50 % cut of 0.3 mm tremor** (CALC, frictionless linear model; this is a lower bound):
  - Reaction mass: 7–42 g·mm of mass × stroke sideways and 12–71 g·mm in the tilt plane. The tungsten slug has 5.2 g·mm; the cell as the moving mass has 1.7 g·mm.
  - CMG: 63–156 µN·m·s per rotor (lateral) and 112–264 µN·m·s (tilt plane), against 40 µN·m·s for a rotor that fits.
  - Reaction wheels: 3.8–8 mN·m, against 0.084 mN·m rated for a 5 mm motor (MFR AMF-51).
  - A passive gyroscope cannot reach 50 % at any size.

### Recommended physical architecture

1. **Keep the Rev P0 architecture:** skid ring on the nose to ground the writing force, and the four-plate piezo nib stage moving only the refill (docs/pencil_concept.md). Of everything evaluated, it is the only physical element with the authority to correct the ink.
2. **Add nothing inertial to the cap.** No reaction mass, tuned mass, gyroscope, CMG or reaction wheel, and no deliberately heavier cap. Keep the cell where it is: battery life is worth more than a 3–15 % tremor cut.
3. **Keep the skid friction moderate** (μ about 0.1–0.15, EXP-Q01).
   - Do not raise it to "stabilise": μ 0.25–0.40 cuts in-band tremor 14–27 % but shrinks the writing 16–19 % and raises the drag 1.7–2.5× (SIM).
   - Do not add a damped nose roller or a soft sleeve for tremor.
   - A grip sleeve for comfort is fine if it keeps at least half of the grip stiffness. In this model ×0.5 was neutral, while ×0.25 made the net error 14–25 % worse (SIM; EXP-I03).
4. **If a user group's tremor saturates the stage** (≥ 0.3 mm at 8–12 Hz), the physical fix is more stage travel or a bigger form factor, not a cap device. The CMG result shows what a cap device buys at best: 0.43 → 0.29 at 12 Hz, for 25 g, 0.34 W and the battery space.
5. **Put the effort into the estimator and the digital layer** (other study; docs/ai_guidance.md). The physical ceiling of the stage is set by its travel. How close the pen gets to that ceiling is decided entirely by how well tremor is separated from writing.
6. **Measure before revisiting.** A cap device could only matter if the grip turns out to be mostly rotational compliance (r_rot ≥ 0.6, EXP-I01). Even then it stays outside the mass and power budgets. A cheap non-device option to test is resting the hand's ulnar side on the paper (a posture "pivot"). HAP-26 did not measure it and this model cannot evaluate it (EXP-I01, EXP-I03).

## 2. Candidates and verdicts

Best-case ratio = ink error with the device under perfect-knowledge (oracle) control ÷ ink error without correction, on the same writing and tremor (harness convention of P1). Passive devices report the in-band (3–15 Hz) tremor ratio and the net in-band error against the intended path (§5.6). Ranges are over 4–12 Hz at 0.3 mm hand-path tremor.

| Item | Candidate | Best plausible size (fits Ø 8.9 mm) | Best-case ratio | Size for 50 % (CALC, lower bound) | Force / torque / stroke | Power | Pen mass, battery | Writing effect | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| a1 | Active reaction mass: **the cell** moved sideways | 3.45 g × ±0.5 mm, 2 axes (1.7 g·mm) (CAD, ASSUMPTION stroke) | linear bound 0.94–0.98 (CALC) | 7–42 g·mm sideways (4–24× larger) | 1–10 mN available (CALC) | ≈ 0.01 W (CALC) | 14.2 g; cell kept | none | **Reject**: too small |
| a2 | Active reaction mass: **tungsten slug, 3 axes** | 5.15 g WHA (MFR AMF-49), ±1.0 mm lateral, ±2 mm axial | **0.85–0.97** (SIM); 0.87–0.93 at 0.1 mm, 0.92–0.98 at 0.5 mm | 7–42 g·mm sideways, 12–71 g·mm tilt plane (1.4–14×) | 2–22 mN rms, strokes on their stops (SIM) | 0.002–0.28 W; 0.48 W at 12 Hz, 0.5 mm (SIM, K_m ASSUMPTION) | 17.7 g; half the cell, battery 4.1 h → 0.4–2 h with the device (CALC) | < 15 µm (SIM) | **Reject** alone; small help to the stage at 10–12 Hz |
| b1 | Passive tuned-mass damper | same slug, tuned 6, 8 or 10 Hz, ζ 0.1 | 0.92–1.07 (SIM) | not a useful device class (narrow band) | ±1 mm | 0 | 17.4 g; half the cell | none | **Reject**: narrow, can worsen off-tune |
| b2 | Heavier cap | +5.2 g or +10.3 g WHA at 158 mm | in band 0.93–1.00 / 0.78–1.00 (12 Hz only) (SIM) | 141 g at 4 Hz; not reached at 6–12 Hz up to 1 kg (CALC) | – | 0 | 18.6 / 23.7 g | none | **Reject** |
| c | Passive gyroscope (rotor along the axis) | WHA ring 7/2 × 6 mm (3.8 g) at 30 krpm on a 5 mm BLDC (MFR AMF-51) | 0.97–1.00 (SIM) | not reachable at any size: it only resists tilt, tremor is mostly translation (CALC) | 8 µN·m at 0.1 rad/s pen rotation (CALC) | 0.20 W (CALC, AMF-51 friction) | 17.2 g; 40 % of the cell | none | **Reject** |
| d | **Control-moment gyroscopes**, scissored pair per axis | 2 pairs: 4 WHA rotors 5.5/1.5 × 4 mm (1.6 g) at 60 krpm on 3 mm BLDCs (MFR AMF-50), gimbals ±0.6 rad, 30 rad/s | **0.87–0.92** (SIM); 0.76–0.83 at 0.1 mm | 63–156 µN·m·s per rotor lateral, 112–264 tilt plane, vs 40 (1.6–6.5×) | 1.1–1.5 mN·m rms per pair (SIM); limit 1.2–2.4 mN·m (CALC) | 0.34 W (CALC) | 25.1 g; no room left for the cell | none | **Reject for the product.** Best inertial effect, but breaks mass, power and space |
| e | Reaction wheels (2 axes) | WHA wheel on a 5 mm BLDC per axis | linear bound 0.99 (rated), 0.96–0.97 (stall) (CALC) | 3.8–8 mN·m (45–95× rated torque) | 0.084 mN·m rated, 0.4 mN·m stall (MFR AMF-51) | 0.09 W rated, 1.9 W stall (CALC) | 10.8 g, 50 mm long: does not fit | none | **Reject** |
| f | Active grip sleeve (Liftware-style gimbal) | pivot at the finger pads (27.5 mm), 2-axis actuator ring at the web end (75 mm) | at most the stage's authority | – | must hold 0.74 N transverse = 29 mN·m about the pivot, 0.43 N at the actuator, 0.52 mm stroke (CALC) | **2.1 W** to hold with the Rev A coil (K_m 0.29 N/√W, CALC) | grip ≥ 15 mm | changes the grip | **Reject**: carries the load the skid avoids (COR-01 again) |
| g1 | Compliant or viscoelastic grip sleeve | grip stiffness ×0.5 (+3 N s/m), or ×0.25 | in band 0.80–0.96 (×0.5), 0.69–0.94 (×0.25) (SIM) | – | – | 0 | +1–2 g (ASSUMPTION) | net 0.93–1.07 / 1.14–1.25 against intent; letters 7–16 % smaller, 8–18 ms lag, pen rocks 1.3–2.8× more (SIM) | **Reject** as a tremor measure |
| g2 | "Stiction filter": soft grip + skid friction | as g1 with μ 0.12 | as g1 | dead band ±F_s/k: ±0.29 mm now, ±0.57 mm at ×0.5 (CALC) | – | 0 | – | loses the same amplitude of writing at each reversal | **Reject** |
| h1 | Paper pivot: skid friction | μ 0.05 / 0.25 / 0.40 | in band 1.11–1.18 / 0.83–0.86 / 0.73–0.82 (SIM) | – | drag 0.07 / 0.20 / 0.28 N (0.115 N now) | 0 | – | net 1.04–1.07 / 1.00–1.06 / 1.07–1.17 (SIM) | **Keep μ ≈ 0.1–0.15** |
| h2 | Paper pivot: viscous nose (idealised damped roller) | 3 / 10 / 20 N s/m | in band 0.79–0.84 / 0.52–0.62 / 0.36–0.46 (SIM) | – | drag +0.03 / +0.08 / +0.13 N | 0 | a damped roller would have to be invented | net 0.96–0.99 / 0.97–1.02 / 1.01–1.07; letters −10 / −24 / −33 %, lag 3 / 11 / 16 ms (SIM) | **Reject**: filters writing as much as tremor |
| i | **Nib stage** (existing) | ±0.30 mm usable, 0.40 mm stop (CALC, P1) | **0.19–0.43** (SIM, H1); P1 0.20–0.46 | – | 0.17 N design load | ~0.1 W with charge recovery (SIM, P1) | in CAD | 30 µm with the Kalman (SIM, P1) | **Keep**: the only element with the authority |
| i | Stage + tungsten reaction mass | | 0.17–0.31; stage saturation 62 → 52 % at 12 Hz (SIM) | | | | | | Only if the envelope changes |
| i | Stage + CMG pairs | | 0.14–0.29; stage saturation 62 → 45 % at 12 Hz (SIM) | | | | | | Best physics, impossible packaging |

## 3. Why inertial devices cannot do much in a pencil

### 3.1 The force scale

The hand holds the pen through a grip that is about 575 N/m stiff at the nib (LIT HAP-26). To keep the nib still while the hand shakes 0.3 mm, something must push the pen against the grip with about 575 × 0.3 mm = 0.17 N (CALC). A device inside the pen can only push by accelerating its own moving part: F = m ω² x. A 5 g mass moving ±1 mm gives 3 mN at 4 Hz, 13 mN at 8 Hz and 29 mN at 12 Hz (CALC). That is 2–17 % of the force, before any losses. The previous one-line rejection in `analysis/pencil_mechanisms.py` (1–10 mN against 172 mN) had the right order of magnitude. This study adds the lever geometry, the pen's rotation and the paper friction, and the conclusion stands.

### 3.2 The unmeasured grip split decides where a cap force or torque goes

HAP-26 measured the grip as one lumped spring at the stylus point (4 cm ahead of the fingers; Fu & Cavusoglu 2012, §II-B). A pen held at two zones can yield in two ways:
- it can **translate** in the grip;
- it can **tilt** about the grip.

Which one dominates has never been measured. It decides whether a force or torque applied at the cap reaches the nib (CALC, `grip.py`):

| Split (r_rot = share of the nib's compliance from tilt; rho_w = web's share of translational stiffness) | Finger / web stiffness (N/m) | Pad tilt stiffness κ_f (N·m/rad) | Nib motion from a force at the cap (141 mm), relative to the same force at the nib | Nib motion per 1 mN·m torque |
|---|---|---|---|---|
| r_rot 0.1, rho_w 0.3 | 447 / 192 | 9.72 | +0.66 | 4 µm |
| r_rot 0.3, rho_w 0.3 | 575 / 246 | 2.95 | **−0.01**: the cap point is conjugate to the nib | 13 µm |
| **r_rot 0.5, rho_w 0.3 (nominal)** | 805 / 345 | 1.46 | −0.69 | 21 µm |
| r_rot 0.7, rho_w 0.3 | 1342 / 575 | 0.52 | −1.36 | 29 µm |
| r_rot 0.5, rho_w 0.1 | 1035 / 115 | 0.96 | −1.19 | 27 µm |
| r_rot 0.7, rho_w 0.1 | 1725 / 192 | 0.47 | −2.06 | 38 µm |

Every split reproduces HAP-26 exactly at the nib: the massless-pen driving-point compliance matches HAP-26 eq. (1) within 1 × 10⁻⁵ in x, y and z over 0.6–30 Hz (CALC).

Two consequences:
1. At r_rot ≈ 0.3 a cap force does not move the nib at all (it tilts the pen about the nib).
2. A torque device (gyroscope, CMG, wheel) moves the nib 4–38 µm per mN·m, so it is useless if the grip is mostly translational.

The skin of three finger pads in shear is about 4.4 kN/m at 1 N normal force per pad, or 3.0 kN/m if 1 N is shared by the three (LIT HAP-31, power law k = 1.48 n^0.35 N/mm; earlier values in HAP-35; CALC). The calibrated finger zone is 0.45–1.7 kN/m, so the skin is about 2–10× stiffer. The finger joints, not the skin, set most of the grip compliance, and the split cannot be derived from pad data: it must be measured (EXP-I01).

### 3.3 Gyroscopes react only to rotation rate

A passive rotor with angular momentum H pushes back with H × Ω, where Ω is the pen's rotation rate (CALC). In H1 the pen tilts 0.8–2.2 mrad RMS in the tremor band (SIM), which is Ω ≈ 0.02–0.17 rad/s RMS. The 3.8 g tungsten rotor at 30 krpm has H = 79 µN·m·s and gives about 8 µN·m, against the 4–8 mN·m needed (CALC). A passive gyroscope also cannot stop translation, so it cannot reach 50 % at any size (CALC, linear sweep to 10 N·m·s).

A CMG is different. It makes its own rotation (the gimbal rate δ̇ up to 30 rad/s) and gives 2 H δ̇ cos δ. That is why it is the strongest inertial option here (§5.3). The gimbal angle limit caps it at low frequency: 2 H ω δ_max = 1.2 mN·m at 4 Hz, 2.4 mN·m from about 8 Hz (CALC).

### 3.4 Passive filters cannot tell tremor from writing

Friction, damping and compliance act on every motion in their band. Handwriting strokes (3–7 Hz, `writing.stroke_freq`) and tremor (4–12 Hz) overlap. In H1, every passive option that lowers the in-band tremor also lowers the in-band writing by a similar amount (§5.6). Separating the two needs knowledge of which motion is intended: an estimator (accelerometers, models, AI) or a known template.

## 4. Model H1

### 4.1 Structure (`sim/handpen/`)

- **Pen:** rigid body (5 DOF: 3 translations plus tilt in two planes; roll is irrelevant for an axisymmetric pen). Small tilts, exact translation. Mass properties from the CAD parts × 1.10 for wiring (CAD + ASSUMPTION): 13.42 g, centre of mass 88 mm from the nib, transverse inertia 2.99 × 10⁻⁵ kg m² about the centre of mass (radius of gyration 47 mm). Tilt 50° (35–75° available).
- **Grip:** two zones on the hand frame.
  - Finger pads at z = 27.5 mm (20–35): transverse stiffness, axial stiffness and a tilt stiffness κ_f.
  - Thumb–index web at z = 75 mm (60–90): transverse stiffness.
  - Damping is stiffness-proportional. All values are calibrated so the tip-referred impedance equals HAP-26 (575 N/m, 1.3 N s/m) in x, y and z (§3.2).
  - The normal-direction grip is therefore 575 N/m instead of the 800 N/m ASSUMPTION of `parameters.yaml`. With P1, that choice changes the housing tremor by < 0.5 % and the ink error by < 1.5 % (SIM).
- **Hand:** HAP-26 mass 0.21 kg with arm stiffness 170 N/m and damping 11 N s/m to the imposed hand path, which carries the tremor. This is the convention of models M1 and P1. The hand frame can also rotate by an imposed angle (wrist tremor).
- **Paper:**
  - Skid-ring point: penalty normal 10⁵ N/m and 10 N s/m, with LuGre friction μ 0.12 normalised by N.
  - Ball: constant spring force F_c/sin θ = 0.196 N inside a 0.3 mm protrusion margin (the tilt-adaptive front stop), LuGre μ 0.15.
  - Optional viscous nose term.
  - All contact values are those of model P1 (ASSUMPTION, EXP-Q01).
- **Devices** (`devices.py`):
  - active reaction mass: a separate body with actuator force limit, centring loop and stroke stops; axes with zero stroke are locked;
  - passive tuned mass;
  - fixed cap mass;
  - passive rotor (gyroscopic coupling −H(β̇₁t₁ + β̇₂t₂));
  - scissored-pair CMG per axis, with gimbal angle, rate and 100 Hz servo limits.
- **Nib stage:** kinematic with P1's limits: 0.30 mm soft limit with taper, 0.40 mm stop, 2 kHz reference, slew limit, contact-gated authority, and a 150 Hz second-order follower.
  - The stage is idealised: no Hall noise, hysteresis or piezo servo. That is why its ratio at 0.1 mm (0.07–0.09) is below P1's (0.19–0.26).
  - **Use P1 for the stage's absolute value, and H1 for the change a helper makes.**
- **Integration:** semi-implicit Euler, 25 µs. Recording at 2 kHz, as P1. A 5 s run takes about 0.07 s.

### 4.2 Tremor

- **Hand-path tremor:** `stabpen.signals.TremorSpec(f0, amp_pk)` on the hand path, exactly as P1 (0.1 / 0.3 / 0.5 mm; ellipse at 0.6 rad, ellipticity 0.4, AM 0.3, 0.3 Hz jitter, 15 % second harmonic). The unmodified pen's nib moves 0.31–0.33 mm peak for 0.3 mm (CALC, linear model).
- **Wrist-rotation tremor:** the hand frame rotates about the page normal (flexion–extension with a semi-pronated hand) through a pivot 150, 175 or 200 mm behind the grip. The amplitude gives 0.3 mm at the nib. Variants:
  - "mixed": 0.21 mm of each;
  - "pitch": axis along the page y, pivot 40 mm above the page. This one mainly pushes the pen into the paper; in-plane ink error is only 42 µm (SIM).

  Forearm pronation–supination and wrist flexion–extension carry most essential-tremor kinetic tremor (LIT HAP-33, abstract). The share in writing is unmeasured (EXP-I02).

### 4.3 Oracle control (perfect disturbance knowledge; estimation excluded)

- **Stage:** cancels the ball's true deviation from its clean path (P1's oracle).
- **Reaction mass and CMG:** iterative learning on the true disturbance, 6 iterations.
  - Each iteration runs the full nonlinear simulation and updates the device input by the inverse of the frictionless linear model in the 2–20 Hz band.
  - The input is then projected onto the device limits (force, stroke, gimbal angle and rate) at a chosen percentile; peaks above it are clipped by the device's own limits in the simulation.
  - The best of 4 projection settings is reported.
- **Check of the method** (seed 200, 8 and 12 Hz, `inertial.json` → `oracle_method_check`):
  - On a pure sine without friction, the CMG reaches 0.72 / 0.55 against a linear bound of 0.68 / 0.50 (SIM, CALC). The reaction mass reaches 0.84 / 0.75 against 0.78 / 0.55; its axial and lateral strokes sit on their stops.
  - With the default tremor (amplitude modulation, frequency jitter) and paper friction, the same devices give 0.95 / 0.86 (reaction mass) and 0.88 / 0.88 (CMG).
  - Each of the two lowers what a force-, stroke- or torque-limited device can do, because the tremor peaks exceed its authority and the stuck nib ignores small pushes (§5.1 vs §5.3).

### 4.4 Agreement with model P1 (unmodified pen, same scenarios)

SIM, seeds 200–203, 9 conditions (4–12 Hz at 0.3 mm; 6 and 10 Hz at 0.1 and 0.5 mm). Normal grip 575 N/m, 1.3 N s/m in both models.

| Comparison | Housing (nib-point) tremor, 3–15 Hz | Ink error against the clean reference |
|---|---|---|
| H1 with tilt locked vs P1 (same physics) | +0.0 to +1.4 % | −1.1 to +1.5 % |
| H1 with the nominal grip split vs P1 | −0.2 to −10 % (lower at 10–12 Hz) | −6.4 to +3.6 % |
| P1 with its own normal grip (800 N/m, 3 N s/m) vs 575 N/m | < 0.5 % | < 1.5 % |

With tilt locked, H1 reproduces P1 to about 1 %. Letting the pen tilt in the grip lowers high-frequency housing tremor by up to 10 %: the pen pivots about the nib held by friction.

### 4.5 Limitations

1. **The hand model has no voluntary correction and no hand resting on the paper** (HAP-26 was measured without either).
   - Under steady friction, the soft arm spring (170 N/m in series with 575 N/m) lets the pen lag the hand. In H1 the unmodified pencil's clean ink sits 118 µm RMS in band from the intended path, and its 0.5–8 Hz letter motion is 0.63 of the intended.
   - P1 shares this, because it uses the same hand model and compares against the pen's own clean ink.
   - Real writers compensate slow drag, so absolute "writing size" effects of friction options are overstated. The in-band comparisons in §5.6 exclude the slow part.
   - A simple 1 Hz visual correction loop was tried and did not help (it acts at the stroke rate with a delay). It is left in the code switched off.
2. **The hand's rotation is imposed.** The device torque cannot rotate the hand. Steadying the hand itself would need the wrist's impedance: passive stiffness 1.2–1.8 N·m/rad (LIT HAP-32) plus inertia (about 7 N·m/rad at 8 Hz for 2.8 × 10⁻³ kg m², ASSUMPTION; HAP-34 reports stiffness as the main wrist impedance in everyday movements, with inertia mattering in fast ones, abstract only). That is far above the mN·m a pen device makes.
3. **The grip split, zone positions and contact values are assumptions.**
4. **The oracle is an upper bound.** Any real estimator does worse.
5. **Device packaging (strokes, K_m, frames) is a proposed design,** not CAD-checked.

## 5. Results

### 5.1 Linear oracle bounds (CALC; nominal split; 0.3 mm)

Frictionless linear model, single frequency, each input optimally phased and limited by its force/stroke or gimbal limits (`linear.py`). This is an optimistic ceiling.

| Device | Hand-path tremor, 4 / 6 / 8 / 10 / 12 Hz | Wrist-rotation tremor, 4 / 6 / 8 / 10 / 12 Hz |
|---|---|---|
| Reaction mass: the cell, 2 axes | 0.98 / 0.98 / 0.97 / 0.96 / 0.94 | 0.99 / 0.98 / 0.97 / 0.96 / 0.95 |
| Reaction mass: slug, 2 axes | 0.95 / 0.91 / 0.86 / 0.79 / 0.70 | 0.96 / 0.92 / 0.87 / 0.81 / 0.72 |
| Reaction mass: slug, 3 axes | 0.90 / 0.85 / 0.78 / 0.69 / 0.55 | as 2 axes (the axial axis acts only along x) |
| Tuned mass 8 Hz | 1.00 / 0.97 / 0.99 / 1.05 / 1.06 | 1.00 / 0.98 / 0.99 / 1.04 / 1.04 |
| Heavier cap +10.3 g | 1.00 / 0.97 / 0.93 / 0.88 / 0.81 | 1.00 / 0.98 / 0.95 / 0.91 / 0.83 |
| Passive gyroscope 30 krpm | 1.00 / 0.99 / 0.98 / 0.97 / 0.95 | 1.00 / 0.99 / 0.99 / 0.98 / 0.96 |
| CMG, lateral pair only | 0.95 / 0.92 / 0.88 / 0.86 / 0.84 | 0.91 / 0.85 / 0.78 / 0.75 / 0.70 |
| CMG, 2 pairs | 0.90 / 0.80 / 0.68 / 0.60 / 0.50 | 0.91 / 0.83 / 0.72 / 0.63 / 0.49 |
| Reaction wheels, rated torque | 0.99 at all frequencies | 0.99 |
| Reaction wheels, stall torque | 0.96–0.97 | 0.97 |

Across the six swept splits, the 3-axis slug ranges 0.20–0.77 at 12 Hz and the 2-pair CMG ranges 0.37–1.02. Both reach their best only at r_rot ≥ 0.5 with a soft web (`inertial.json` → `linear_screen`). At 8–12 Hz the time-domain oracle realises about a quarter to a half of these linear gains (§5.3), because the real tremor is amplitude-modulated and the nib is held by friction part of the time.

### 5.2 Size needed for a 50 % reduction (CALC; nominal split; 0.3 mm; lateral / tilt plane)

| Tremor | Frequency | Reaction mass: mass × stroke (g·mm) | Torque (mN·m) | CMG H per rotor (µN·m·s) |
|---|---|---|---|---|
| hand path | 4 Hz | 42 / 71 | 4.7 / 8.0 | 156 / 264 |
| hand path | 8 Hz | 14 / 24 | 4.2 / 7.2 | 71 / 120 |
| hand path | 12 Hz | 7 / 12 | 3.8 / 6.8 | 63 / 113 |
| wrist rotation | 8 Hz | 22 (lateral) | 6.6 | 110 |
| **Available** | | slug 5.2, cell 1.7 | wheel 0.084 rated, 0.4 stall (MFR AMF-51) | 40 (1.6 g WHA rotor at 60 krpm) |

These are lower bounds: the linear model has no friction and no amplitude modulation. For a 50 % cut, the slug would have to be 10–40 g moving ±1.5–2 mm, and each CMG rotor 2–7 times heavier or faster, inside a 7.9 mm bore. A passive gyroscope cannot reach 50 % at any size. A fixed cap mass reaches it only at 4 Hz, with 141 g.

### 5.3 Time domain, hand-path tremor (SIM; 4 seeds; ink-error ratio against no correction)

| Amplitude | Case | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz |
|---|---|---|---|---|---|---|
| 0.1 mm | tungsten reaction mass (3 axes) | 0.93 | 0.89 | 0.92 | 0.89 | 0.87 |
| 0.1 mm | CMG, 2 pairs | 0.83 | 0.76 | 0.76 | 0.79 | 0.79 |
| 0.1 mm | nib stage (H1, idealised) | 0.070 | 0.080 | 0.074 | 0.083 | 0.089 |
| 0.1 mm | stage + CMG | 0.058 | 0.062 | 0.057 | 0.059 | 0.057 |
| **0.3 mm** | tungsten reaction mass (3 axes) | 0.97 | 0.96 | 0.93 | 0.88 | 0.85 |
| **0.3 mm** | CMG, 2 pairs | 0.92 | 0.89 | 0.87 | 0.88 | 0.88 |
| **0.3 mm** | nib stage | 0.19 | 0.23 | 0.30 | 0.38 | 0.43 |
| **0.3 mm** | stage + reaction mass | 0.17 | 0.20 | 0.26 | 0.29 | 0.31 |
| **0.3 mm** | stage + CMG | 0.14 | 0.16 | 0.20 | 0.27 | 0.29 |
| 0.5 mm | tungsten reaction mass | 0.98 | 0.97 | 0.95 | 0.93 | 0.92 |
| 0.5 mm | CMG, 2 pairs | 0.95 | 0.93 | 0.92 | 0.93 | 0.91 |
| 0.5 mm | nib stage | 0.39 | 0.45 | 0.51 | 0.55 | 0.57 |
| 0.5 mm | stage + reaction mass | 0.38 | 0.42 | 0.47 | 0.49 | 0.50 |
| 0.5 mm | stage + CMG | 0.34 | 0.38 | 0.43 | 0.48 | 0.47 |

Unmodified ink error at 0.3 mm: 251 / 297 / 374 / 450 / 502 µm; in band 158–192 µm (SIM).

What the devices did (SIM, 0.3 mm):
- **Reaction mass:** force 2–22 mN rms on the busiest axis. Its strokes reach their ±1 mm / ±2 mm stops.
- **CMG:** 1.1–1.5 mN·m rms per pair. The gimbals sit at their ±0.6 rad limit, with rates of 14–20 rad/s rms.

### 5.4 Time domain, wrist-rotation tremor (SIM; 0.3 mm at the nib; pivot 175 mm)

| Case | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz |
|---|---|---|---|---|---|
| tungsten reaction mass | 0.99 | 0.98 | 0.98 | 0.96 | 0.93 |
| CMG, 2 pairs | 0.93 | 0.90 | 0.88 | 0.84 | 0.86 |
| nib stage | 0.21 | 0.26 | 0.33 | 0.37 | 0.43 |
| stage + reaction mass | 0.20 | 0.24 | 0.30 | 0.32 | 0.35 |
| stage + CMG | 0.15 | 0.19 | 0.24 | 0.24 | 0.28 |

- **Pivot distance** (150 / 175 / 200 mm at 8 Hz): no effect (reaction mass 0.976 / 0.976 / 0.973; CMG 0.884 / 0.884 / 0.883).
- **Mixed tremor:** reaction mass 0.87–0.98, CMG 0.83–0.92.
- **Pitch-axis rotation** (mostly normal to the page): CMG 0.75, stage 0.08, on a small in-plane error (42 µm).
- A pen-mounted gyroscopic device is not specially suited to the rotational component: the pen follows the hand's rotation through the grip, and its authority is the same mN·m.

### 5.5 Combination with the nib stage (SIM; 0.3 mm)

Time with the stage at its travel limit (P1 definition):

| Case | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz |
|---|---|---|---|---|---|
| stage alone | 19 % | 30 % | 46 % | 55 % | 62 % |
| stage + reaction mass | 18 % | 27 % | 42 % | 47 % | 52 % |
| stage + CMG | 15 % | 20 % | 32 % | 43 % | 45 % |

A helper removes the tremor peaks that push the stage onto its limit. So it improves the stage's ratio more than its own ratio would suggest: at 12 Hz, the reaction mass alone gives 0.85, but stage + reaction mass gives 0.31 against 0.43. The gain is largest where the stage saturates (0.3–0.5 mm, 8–12 Hz). It vanishes at 0.1 mm, where the stage does not saturate (≤ 2 %).

### 5.6 Passive options (SIM; 0.3 mm hand-path tremor; 4 seeds)

"In-band tremor" is the 3–15 Hz ink error against each pen's own tremor-free ink, relative to the unmodified pencil. "Net against intent" is the 3–15 Hz ink error against the writer's intended path, relative to the unmodified pencil. It counts both the tremor that gets through and the writing detail that is filtered away; slow lag is excluded because writers compensate it. "Letters" is the 0.5–8 Hz ink motion without tremor, relative to the unmodified pencil.

| Option | In-band tremor, 4–12 Hz | Net against intent, 4–12 Hz | Letters | Lag | Drag (N) | Pen tilt in band |
|---|---|---|---|---|---|---|
| unmodified (μ 0.12, grip 575 N/m) | 1 | 1 | 1 | 0 | 0.115 | 1.39 mrad |
| frictionless nose (reference) | 1.29–1.61 | 1.23–1.37 | 1.60 | −11 ms | 0 | 0.37 mrad |
| skid μ 0.05 | 1.11–1.18 | 1.04–1.07 | 1.24 | −5 ms | 0.066 | 0.90 mrad |
| skid μ 0.25 | 0.83–0.86 | 1.00–1.06 | 0.81 | 4 ms | 0.195 | 2.02 mrad |
| skid μ 0.40 | 0.73–0.82 | 1.07–1.17 | 0.84 | 4 ms | 0.283 | 2.43 mrad |
| viscous nose 3 N s/m | 0.79–0.84 | 0.96–0.99 | 0.90 | 3 ms | 0.146 | 1.69 mrad |
| viscous nose 10 N s/m | 0.52–0.62 | 0.97–1.02 | 0.76 | 11 ms | 0.195 | 2.13 mrad |
| viscous nose 20 N s/m | 0.36–0.46 | 1.01–1.07 | 0.67 | 16 ms | 0.245 | 2.45 mrad |
| soft sleeve, grip ×0.5 | 0.83–0.96 | 0.96–1.07 | 0.93 | 8 ms | 0.111 | 2.43 mrad |
| soft sleeve, grip ×0.25 | 0.69–0.94 | 1.14–1.25 | 0.84 | 18 ms | 0.109 | 3.95 mrad |
| viscoelastic sleeve ×0.5, +3 N s/m | 0.80–0.94 | 0.93–1.06 | 0.92 | 8 ms | 0.108 | 1.84 mrad |
| heavier cap +5.2 g / +10.3 g | 0.93–1.00 / 0.78–1.00 | 0.95–1.00 / 0.86–1.01 | 1.00 | ≤ 1 ms | 0.115 | 1.59 / 1.82 mrad |
| tuned mass 6 / 8 / 10 Hz | 0.92–1.07 | 0.95–1.06 | 1.00 | 0 | 0.115 | 1.2–1.6 mrad |
| passive gyroscope 30 / 100 krpm | 0.97–1.00 | 0.98–1.00 | 1.00 | 0 | 0.115 | 1.51 mrad |

Reading:
- Friction, damping and compliance trade tremor for writing about one for one. The net effect against the intended path stays within 0.93–1.25.
- The best passive entry (viscous 3 N s/m, net 0.96–0.99) is a 1–4 % net change for 27 % more drag, and needs an invented damped roller.
- A heavier cap helps only at 12 Hz (+10 g: 0.86 net), where it moves a pen resonance. It sits at the 24 g bound.
- The "stiction filter" dead band across the grip alone is ±F_s/k: ±0.29 mm now (0.164 N static friction over 575 N/m) and ±0.57 mm at half the grip stiffness (CALC; the arm in series makes it larger in this model). That is exactly the tremor amplitude it would block, and it takes the same amount from each writing stroke.

### 5.7 Sensitivity to the grip split (SIM; oracle; 0.3 mm; seeds 200–201)

| Split | Reaction mass 8 / 12 Hz | CMG 8 / 12 Hz |
|---|---|---|
| r_rot 0.1, rho_w 0.3 | 0.95 / 0.96 | 0.98 / 0.98 |
| r_rot 0.3, rho_w 0.3 | 0.96 / 0.94 | 0.94 / 0.93 |
| r_rot 0.5, rho_w 0.3 (nominal) | 0.93 / 0.85 | 0.87 / 0.87 |
| r_rot 0.7, rho_w 0.3 | 0.90 / 0.79 | 0.84 / 0.84 |
| r_rot 0.5, rho_w 0.1 | 0.89 / 0.76 | 0.83 / 0.84 |
| r_rot 0.5, rho_w 0.6 | 0.96 / 0.92 | 0.92 / 0.92 |

Even at the most favourable split the best device stays above 0.76. The verdict does not depend on the split; the size of the small gain does.

### 5.8 Budgets (CALC; MFR where marked)

| Device | Pen mass | Cell left | Length taken | Power | Other |
|---|---|---|---|---|---|
| Reaction mass, cell | 14.2 g | 100 % | coils in the 0.7 mm annulus (ASSUMPTION) | ≈ 0.01 W | stroke ±0.5 mm (radial clearance 0.7 mm) |
| Reaction mass, slug 3 axes | 17.7 g | 50 % (about 45 mAh) | 20 mm | 0.002–0.48 W (SIM forces, K_m 0.06 N/√W ASSUMPTION) | recording plus device: 0.4–2 h instead of 4.1 h |
| Heavier cap +10.3 g | 23.7 g | 100 % | 17 mm of tungsten | 0 | over the 20 g target, under the 24 g bound |
| Passive gyroscope, 30 krpm | 17.2 g | 40 % | 25 mm | 0.20 W (0515 B friction 0.053 mN·m at 30 krpm, AMF-51; windage 3 mW) | imbalance 30 mN at 500 Hz for grade G2.5 (ASSUMPTION; grade classes from secondary summaries of ISO 21940-11, AMF-52, standard not read) = 0.18 µm pen vibration: invisible in the ink, near the felt threshold (HAP-27), audible; spin-up about 1 s at rated torque (longer, since friction takes 60 % of it) |
| CMG, lateral pair only | 18.4 g | 25 % | 30 mm | 0.17 W | limited to lateral tremor |
| CMG, 2 pairs | 25.1 g | 0 % (needs about 20 mm more length) | about 60 mm | 0.34 W | spin motors 0308 B at 60 krpm: friction 0.0083 mN·m against 0.013 mN·m rated, so little margin (AMF-50); spin-up 8.6 s; 1 kHz tone; imbalance 25 mN per rotor (G2.5), 0.025 µm vibration |
| Reaction wheels, 2 axes | 10.8 g of wheels and motors | – | 50 mm: does not fit | 0.09 W (rated) to 1.9 W (stall) | 0.084 mN·m rated per axis (AMF-51) |
| Active grip sleeve | – | – | grip ≥ 15 mm OD | 2.1 W to hold the paper's reaction | 0.52 mm actuator stroke for 0.3 mm at the nib |

Battery: 90 mAh, 0.266 Wh usable, 65 mW electronics (ASSUMPTION, `config/pencil.yaml`).

## 6. Prior art: inertial and active tremor devices

| Device (ledger id) | What moves or resists | Scale | Reported result | Scale against the pen |
|---|---|---|---|---|
| Micron microsurgical tool (ACT-01/02/03) | piezo or ultrasonic manipulator moves the tool tip relative to the handle | 40–70 g handpiece; ±0.4 mm (3-DOF) to 4 mm (6-DOF) travel; side load 0.15–0.2 N | ≥ 15 dB hand-motion attenuation on the bench; handheld pointing 112 → 12 µm RMS; human tasks −32 to −52 % error | Same principle as the nib stage. Its side-load limit (0.15–0.2 N) is the stage's design load (0.17 N) |
| Liftware (ACT spoon) (ACT-16/17) | two DC motors with yokes move the spoon against the tremor; accelerometer in the spoon base | about 100 g, 40 × 50 × 175 mm, > 90 min | tremor amplitude −71 to −76 % in ET (for example 1.2–2 cm → 0.2–0.6 cm), n = 15 | Free-space tool with no contact load; 5× the pen's mass |
| Gyenno spoon (ACT-31, ACT-33) | two motors (longitudinal, transverse) | – | manufacturer claims 85 %; PD pilot (n = 8): less rice transferred with it on (p = 0.014) | Active stabilisation does not help every tremor type |
| Active vs passive spoons (ACT-19) | weighted 350 g spoon, deep bowl, active spoon | – | the weighted and deep-bowl spoons outperformed the active spoon in ET | Benchmark the pen against passive pens too |
| GyroGlove (ACT-25, ACT-28) | gyroscopes on the back of the hand precess against hand rotation | module on the hand; rotor data not disclosed (press reports of 10–20 krpm are unverified) | patent bench test 6 → 0.5 deg/s; ET pilot writing task −48 % (abstract) | Acts on the hand's rotation with a hand-scale rotor |
| Gyroscopic glove, bench (ACT-27) | motor-driven brass disc on a glove | 145 g gyroscope | > 50 % at 4–7 Hz on a mannequin hand | 20× the pen's whole mass margin |
| Tuned vibration absorbers: Tremelo, Vib-bracelet, arm model (ACT-29/30/33) | tuned mass on the forearm | limb scale | 80–85 % on mechanical models; 85 % in one PD patient | They work on a resonant limb segment. The pen on its grip is not resonant in the tremor band (§5.1) |
| Steadiwear (ACT-26) | passive damped glove | – | manufacturer rating-scale claims | – |
| Weighted utensils in PD (ACT-32) | +140 to +470 g on the spoon or wrist | – | no change in PD postural tremor amplitude or frequency (n = 16) | A few grams in a cap will not change the tremor itself |
| Anti-tremor pens (ACT-20/21) | pendulum pen-rod actuated in a casing; in-pen voice coil moving the point | – | −47 dB in a control simulation; 44–57 % lower acceleration peak on a bench on paper | Nib-moving, like the stage |
| Spring-isolated weighted pen (ACT-24) | weighted inner assembly on springs inside a 42.5 mm shell | 226 g inner weight | "the tip does not vibrate" at 227 g; no numbers | Passive isolation needed about 17× the pen's mass |
| Hand-held gyroscope patent (ACT-34) | gyroscope held in the hand | – | no performance values (abstract only) | Freedom-to-operate note only |

**Pattern.** The inertial devices that work are hand-scale or limb-scale: 100–500 g on the hand or forearm, acting on the limb's own resonance or rotation. The devices that work at pen scale move the tool tip relative to the handle: Micron, Liftware, and this project's nib stage. The pen has 7 g of mass margin and 0.27 Wh; that is the wrong scale for the first group.

## 7. Assumptions that matter most

1. **Grip split between translational and rotational compliance** (r_rot 0.5, rho_w 0.3; swept 0.1–0.7 and 0.1–0.6). It decides whether a cap force or torque reaches the nib at all (§3.2). Measure it with EXP-I01.
2. **The hand model** (HAP-26 lumped, imposed path, in-plane, no hand on paper, no voluntary correction).
   - It overstates friction's shrinking of the writing (§4.5).
   - It cannot represent a hand resting on the paper, the most obvious real-world "pivot".
3. **Tremor composition:** translation vs wrist rotation, amplitude modulation and jitter. The devices do best on a pure sine without friction. Measure with EXP-I02.
4. **Skid and nib friction** (μ 0.12 / 0.15; LuGre with 10 µm presliding) and contact stiffness (EXP-Q01).
5. **Device packaging:** strokes, voice-coil K_m, frame masses and cell removal are ASSUMPTION. Motors (AMF-50/51) and tungsten (AMF-49) are MFR.
6. **Oracle control** is an upper bound. Any real estimator gives less; the other study quantifies how much less.

## 8. Experiments needed (proposed procedures)

Conventions as `validation/bench_protocols.md` §0: pre-registration, GUM uncertainty, blind ink analysis, HDF5 with a JSON sidecar. These protocols are proposed text; none has been executed.

### EXP-I01: Grip compliance split (translational vs rotational) of a pen grasp

- **Purpose and what it gates.** Identify the 2 × 2 grip stiffness per plane (translation, tilt) and the elastic centre z_c. This gives r_rot and rho_w, the inputs that decide whether any cap device can matter (§3.2, §5.7). It also re-checks the tip-referred 575 N/m (HAP-26) in a real pen grasp, with the nib on paper and with the hand resting.
- **Hypotheses.**
  - H1: the tip-referred in-plane stiffness lies in 230–1040 N/m at 1–3 N grip force (HAP-26 range).
  - H2: r_rot lies in 0.3–0.7. The decision threshold for revisiting cap devices is r_rot ≥ 0.6.
  - H3: resting the ulnar side of the hand on the paper raises the grip-referred stiffness by more than 2×.
- **Equipment.**
  - Dummy pen, 8.9 × 166 mm, 13–20 g, rigid (first bending mode > 500 Hz), with a thin-film grip-force sensor at the finger zone.
  - A stinger to a 2-axis voice-coil shaker (0.5 N, 0.5–40 Hz), attachable at the nib (z = 0) or the cap (z = 150 mm).
  - Six-axis force sensor at the stinger (Nano17 class).
  - Two optical markers (nib, cap) tracked at ≥ 1 kHz with ≤ 5 µm noise, or two laser triangulation sensors.
  - Paper on a low-friction film for the "nib on paper" condition.
- **Procedure.**
  - Seated writing posture; tilt 50° ± 5° checked from the markers.
  - Three grip-force targets: 1, 2, 3 N.
  - For each plane (lateral, tilt plane) and each input point (nib, cap): 20 s of band-limited random force, 0.6–30 Hz and ≤ 0.3 N rms.
  - Four conditions: arm unsupported / forearm supported / ulnar side of the hand resting on the paper; nib in air / on paper.
  - Randomised order, 60 s rest between trials.
- **Sample size.** 12 healthy adults for method qualification, then 12 people with ET or PD (after ethics approval, as `validation/human_study_plan.md`).
- **Data format.** HDF5 per trial: force (6), marker positions (2 × 3), grip force, condition tags; 2 kHz.
- **Analysis.**
  1. Estimate the 2 × 2 receptance matrix per plane from the two input points (H1 estimator, coherence > 0.8).
  2. Fit `sim/handpen/grip.py` (k_f, k_w, κ_f with the hand mass and arm) with confidence intervals by bootstrap over trials.
  3. Report r_rot, rho_w and z_c. Re-run `python3 -m sim.handpen.run_study` with the fitted values.
- **Decision.**
  - If r_rot < 0.6 for most participants, close the cap-device line for good.
  - If r_rot ≥ 0.6 and the re-run predicts a stage saturation cut of ≥ 25 % at 10–12 Hz, a CMG or reaction-mass bench study (EXP-I04) may be considered, knowing it breaks the envelope.
- **Risks.** Grip adapts to the shaker (keep forces random and small); marker occlusion; the tilt changes with grip force.

### EXP-I02: Rotational share of writing tremor

- **Purpose.** Split nib tremor into hand-path translation and wrist or forearm rotation during real writing. Estimate the effective pivot distance (150–200 mm assumed).
- **Setup.**
  - Three-axis gyroscope and accelerometer on the dorsum of the hand (≥ 500 Hz).
  - The pen's own IMU.
  - Nib trajectory from a digitiser tablet under paper, or coded paper at ≥ 120 Hz (§5 of `pencil_concept.md`).
- **Tasks.** Archimedes spiral, a copied sentence, and hold-still with the nib on paper; 3 repeats each.
- **Participants.** As EXP-H01 (same recordings if scheduled together).
- **Analysis.**
  - Coherence between the hand's angular velocity and the nib's in-plane motion in the tremor band.
  - Least-squares fit of the nib motion as translation plus rotation about a pivot.
  - Report the rotational share and L_p. Feed both to `HM.Tremor(amp_trans, amp_rot, L_p)`.
- **Decision.** Only relevant if EXP-I01 keeps cap devices open.

### EXP-I03: Passive nose and grip options on writers (extends EXP-H03)

- **Purpose.** Measure the in-band tremor vs legibility trade-off of the passive options (§5.6) on people, including the compensation the model lacks.
- **Conditions (blinded, randomised).**
  - Skid μ about 0.05, 0.12 and 0.25 (EXP-Q01 materials).
  - Grip sleeve at ≈ 1×, 0.5× and 0.25× the grip stiffness (silicone Shore 20A–60A tubes, stiffness measured on EXP-I01's rig).
  - Hand resting vs not resting.
  - A heavier-cap control (+10 g).
- **Measures.**
  - In-band tremor of the ink (3–15 Hz, M-band of `bench_protocols.md` §0.8).
  - Letter height ratio against the participant's own tremor-free baseline.
  - Recognition accuracy.
  - Drag and comfort ratings.
- **Decision.** Adopt a passive option only if the net in-band ink error against the intended text improves by ≥ 15 % with no loss in recognition. The prediction here is that none will, except possibly hand resting, which the model cannot predict.

### EXP-I04 (conditional): Stage plus helper on the loaded rig

Run only if EXP-I01 shows r_rot ≥ 0.6. Mount a CMG pair or a reaction-mass module on the EXP-Q06 rig's pen body, with a hand simulant that has the EXP-I01 two-zone compliance. Run the EXP-B09 cancellation protocol with and without the helper at 8–12 Hz and 0.3–0.5 mm. Compare stage saturation and the oracle ratio with `inertial.json` → `time_domain.translational`.

## 9. Files, commands, tests

| What | Command | Time |
|---|---|---|
| Full study → `results/pencil/inertial.json`, `inertial_viz.json` (1.6 MB), `fig_inertial_*.png` | `python3 -m sim.handpen.run_study` (2 processes) | about 5 min |
| Redraw the figures from the JSON | `python3 -m sim.handpen.run_study --figures-only` | seconds |
| Tests (21) | `python3 -m pytest sim/handpen/tests -q` | about 3 s after the numba cache is warm |

The tests check:
- the calibration against HAP-26 for four splits;
- the split definition;
- the energy structure of the linear model (symmetric mass and stiffness, skew gyroscopic part, positive dissipation);
- static equilibrium in the compiled core;
- the core against the linear model on a frictionless page (nib amplitude within 3 %, tilt within 5 %);
- the rotation-locked pen against model P1 (housing tremor within 5 %, ink error within 8 %);
- every device formula against a hand calculation (reaction force, tungsten mass, ring inertia, gyroscope and CMG torque, CMG limit, wheel speed, imbalance, motor friction from the datasheets, spin-up, coil loss, sleeve load);
- the reaction mass's force and stroke in the core;
- the CMG's torque and gimbal swing in the core;
- the stage's travel stop.

Code map:
- `params.py`: labelled inputs and CAD mass properties.
- `grip.py`: two-zone calibration.
- `linear.py`: frequency-domain model and bounds.
- `devices.py`: candidates, sizing and budgets.
- `core.py`: compiled time-domain model.
- `model.py`: packing, runs, rotational tremor and the ILC oracle.
- `evaluate.py`: metrics, including the ink-against-intent measure.
- `run_study.py`: the study.

The numba cache goes to `sim/handpen/build/` (git-ignored).

**3-D replay.** `results/pencil/inertial_viz.json` holds 2.5 s at 200 Hz (seed 200, 8 Hz, 0.3 mm) for six cases:
- the unmodified pen;
- the tungsten reaction mass;
- the nib stage;
- stage + reaction mass;
- the CMG pairs;
- stage + CMG.

Each case records:
- the nib (x, y, z);
- the pen axis unit vector and tilt angles;
- the finger-zone grip point;
- the ink with a pen-down flag;
- the device state: reaction-mass displacement and force in the pen frame, CMG gimbal angles and torques with the rotor speed, and the stage deflection.

The file also carries the intended path and metadata (frames, geometry, evidence labels, case descriptions).
