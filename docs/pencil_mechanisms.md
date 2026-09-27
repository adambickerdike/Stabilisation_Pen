# Pencil-class pen: forces, mechanisms and simulation (Rev P0, config/pencil.yaml P0.1.2)

Task A1/A2 of the pencil study. Everything below is a calculation or a simulation from labelled inputs. **Nothing has been built or measured.**

**Labels.**

| Label | Meaning |
|---|---|
| CALC | CALCULATION (analytical, from labelled inputs) |
| SIM | SIMULATION (magpylib, finite-element, or the coupled model P1) |
| MFR (id) | MANUFACTURER STATEMENT with its ledger id |
| LIT (id) | literature with its ledger id |
| CAD | proposed design (`mechanics/cad/pencil_revP.py`) |
| ASSUMP | ASSUMPTION: range and measuring experiment given |

AMF-46/47/48 are new sources used here; they are in `docs/evidence.csv` (AMF-46 and AMF-48 lead-verified against the primary PDFs, AMF-47 from a datasheet mirror).

**Geometry.** Numbers are for CAD P0.1.2 (`mechanics/cad/pencil_revP.py`): the lead moved the plates 4 mm rearward so the decoupling leaves get their 5 mm span (§4.2), moved the gimbal to z = 62 mm (lever 62/45.5 = 1.363), and added the snubber frames and a PTFE collar liner. The analysis and the simulation were re-run on that geometry; every result moved by less than 2 % except the stroke at 35° (42 → 48 µm) and the guided spiral (253 → 202 µm).

## 1. Answer in brief

- **Mechanism.** Only one mechanism works at 8.9 mm: the **skid ring carries the writing force** and **four custom 2.6 mm PICMA-class piezo plates** move the refill ("Q" layout: a push-pull pair per axis). Each plate drives a front collar through a leaf flexure, and the refill pivots in a rear gimbal (lever 1.38).
  - It holds the static load at zero power.
  - Every electromagnetic, shape-memory, inertial and gyroscopic option fails by one to three orders of magnitude (§3).
- **Forces at the design point** (θ 50°, user force 1 N, μ 0.15; CALC):
  - A conventional nib must be held against **0.76 N** transverse (0.64 N of it is N cos θ).
  - Behind the skid, with a 0.15 N axial nib spring, the stage holds **0.126 N** (F_c cot θ, friction neglected) and up to **0.170 N** in the worst stroke direction.
  - The skid carries 0.80 N with 0.097 N of friction.
  - The fingers feel 1 N normal and 0.126 N of drag, against 0.15 N for a conventional pen.
- **Stage.**
  - Blocking force at the nib: 0.329 N. Free stroke: ±613 µm. Stops: ±0.40 mm.
  - Stroke under load: **±277 µm** at the worst-direction design load, ±353 µm friction-free (both CALC). This is ±162 µm at the −20 % catalogue tolerance and ±48 µm at 35° (CALC).
  - First resonance: **192 Hz** (lumped), 195 Hz (FE).
- **Power.** The static hold costs no power, but the driver and the sensor noise set the battery life (90 mAh, 65 mW electronics placeholder):
  - recording only: **4.1 h**;
  - tremor assist with 2 × DRV2700: **0.8 h** (1 µm Hall noise) to 1.4 h (noise-free);
  - with a charge-recovery driver: **2.7 h** to 3.6 h (all SIM).
- **Simulated benefit** (Q stage, test seeds 200–203, ratio vs the neutral pencil; SIM):
  - Oracle bound: 0.19–0.26 at 0.1 mm tremor. It is stroke-limited at larger tremor: 0.20–0.46 at 0.3 mm and 0.40–0.61 at 0.5 mm.
  - Kalman (frozen M1 set): 0.85–0.92 at 8–12 Hz and ≥ 0.3 mm. It adds error at 0.1 mm (1.10–1.22 at 8–12 Hz).
  - Guided on the feature course: circle 348 → 174 µm path distance, fast stroke 112 → 20 µm.
- **Must-fix design findings.**
  - The first CAD decoupling leaf locked the other axis and would have broken (§4.2). Fixed in CAD P0.1.2.
  - Stops alone do not save the ceramic in a sideways 1 m drop (§4.6).
  - Hall noise at 1 µm doubles to triples the drive power (§5).

## 2. Exact forces (A1a)

Inputs:

- θ, N and tremor: inherited targets (REQ-ENV-001/002/003).
- μ_nib 0.15 and μ_skid 0.12: ASSUMP (EXP-Q01; CON-13 gives 0.09–0.17 for ballpoints).
- F_c 0.15 N: ASSUMP (EXP-Q02).

Conventions:

- **F_c** is the axial spring force along the barrel (lead convention, as config_trade candidate D).
- **Friction neglected:** N_nib = F_c / sin θ and the transverse load is F_c cot θ.
- **With friction in the axial balance:** N_nib = F_c / (sin θ − μ cos β cos θ). The worst stroke direction (β = 0, pull) gives F_c cot(θ − atan μ).
- **Roll is unknown**, so each stage axis must take the full transverse load.

### 2.1 Nominal point (θ 50°, N 1 N, μ 0.15, F_c 0.15 N, tremor 8 Hz 0.3 mm)

| Quantity | Conventional pen (nib carries N) | Skid architecture | Label |
|---|---|---|---|
| Normal force at the nib | 1.00 N | 0.196 N (0.174–0.224 N over stroke direction) | CALC |
| Transverse, tilt plane, static (N cos θ) | 0.643 N | 0.126 N (F_c cot θ) | CALC |
| Transverse, tilt plane, worst direction | 0.758 N | 0.170 N | CALC |
| Transverse, sideways, worst direction (μN) | 0.150 N | 0.030 N | CALC |
| Design load per stage axis (max \|R⊥\|) | 0.758 N | **0.170 N** | CALC |
| Axial load (spring or axial path) | 0.766 N | 0.150 N | CALC |
| Skid normal force / friction | — | 0.804 N / 0.097 N | CALC |
| Nib-force band from bushing friction (μ_b 0.08, PTFE-lined) | — | ±0.031 N (±0.12 N if the Ti collar bore is left bare, μ ≈ 0.3) | CALC, ASSUMP |
| Fingers: normal / drag | 1.00 / 0.150 N | 1.00 / 0.126 N | CALC |
| Dynamic: inertia m_eq ω²q (0.385 g at the nib) | 0.29 mN | 0.29 mN | CALC |
| Dynamic: base coupling m_c ω²A (0.635 g) | 0.48 mN | 0.48 mN | CALC |
| Dynamic: parasitic stiffness (37.7 N/m at the nib) × q | 11 mN | 11 mN | CALC |
| Stage reaction felt at the fingers | 0.48 mN | 0.48 mN | CALC |

Cross-check against `results/trade/config_trade.json` candidate D (F_c 0.30 N): that file gives 0.297 N and this script reproduces 0.297 N in the same convention. With friction in the axial balance the load is 0.339 N, and the frictionless value is 0.252 N (CALC).

The skid only touches the paper when the user presses harder than N_nib (0.196 N at 50°). Below that, the nib carries the whole force.

### 2.2 Envelope (θ 35–75°, μ 0.05–0.35, N 0.2–2 N, F_c 0.08–0.30 N, tremor 4–12 Hz at 0.1–1 mm)

| Quantity | Conventional | Skid | Label |
|---|---|---|---|
| Transverse load per axis, max over β | 0.061–2.04 N | 0.026–**1.07 N** (35°, μ 0.35, F_c 0.30: friction-cone amplification cot(θ − atan μ) = 3.6) | CALC |
| Sideways component | 0.010–0.70 N | 0.004–0.21 N | CALC |
| Nib normal force | 0.2–2 N | 0.084–1.05 N | CALC |
| Skid normal force | — | 0–1.92 N | CALC |
| Dynamic inertia (4 Hz 0.1 mm to 12 Hz 1 mm) | 0.02–2.2 mN | same | CALC |
| Parasitic elastic force | 3.8–38 mN | same | CALC |

The dynamic parts are negligible (< 4 % of the static load). What the stage must hold is **N cos θ plus friction at the nib**, and behind a skid this scales with F_c. The design lever is therefore the lowest usable nib force (EXP-Q02) together with limits on the low-altitude, high-friction corner.

### 2.3 Nib reaches the paper over the tilt range (skid ring r = 1.4 mm)

| Quantity | Value | Label |
|---|---|---|
| p ≥ r cot θ (tip, ball radius neglected) | 2.00 / 1.18 / 0.38 mm at 35/50/75° | CALC |
| Exact, ball centre ahead of the ring (r_b 0.35 mm) | 1.39 / 0.72 / 0.01 mm | CALC |
| Tilt range 1.4 × (cot 35° − cot 75°) | **1.62 mm** | CALC |
| Axial slide that follows the stage (q cot θ), ±0.30 / ±0.40 mm | +0.51 / +0.68 mm | CALC |
| Travel needed: working stroke / stops (exact ball geometry: 2.25 mm) | 2.13 / 2.30 mm | CALC |
| Configured travel (was 2.1 mm) | **2.4 mm** (P0.1.1) | CALC |
| Spring-force change over the tilt range (25 N/m) | 0.041 N, lowest at 35° where cot θ is highest | CALC |

## 3. Mechanism verdicts (A1b)

The design load is 0.170 N per axis at the nib (skid, worst direction) and the usable correction target is ±0.30 mm.

| Candidate | Nib stroke under load | Force at nib | f₁ / bandwidth | Hold power | Dyn. power 8 Hz 0.3 mm (1 axis, rail) | ΔT | Fits 7.9 mm | Mass | Drop/stops | Availability | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PL128.10 as-is, 6.15 mm (MFR AMF-11) | ±349 µm (±226 at −20 %) | 0.39 N | 199 Hz | ≈ 0 | 44 mW class-B, 6.5 mW recovery | < 1 mK | **one axis only**: refill must sit 1.06 mm off-axis | 1.16 g | as below | catalogue | Bench part for the 1-axis rig (EXP-Q06), not the product |
| Custom 4.0 mm L pair (P0.1.0) | ±199 µm (±81) | 0.26 N | 173 Hz | ≈ 0 | 30 / 4.4 mW | < 1 mK | **no**: corners collide at ±0.40 mm (CAD) | 1.5 g | — | custom | Reject |
| Custom 3.5 mm L pair | ±143 µm (±25); 0 at 35° | 0.22 N | 165 Hz | ≈ 0 | 26 / 3.9 mW | < 1 mK | yes, 0.215 mm corner gap (CAD) | 1.3 g | stops alone fracture (§4.6) | custom | Second choice |
| **Custom 2.6 mm quad (Q)** | **±277 µm** (±162); ±48 at 35° | **0.329 N** | **192 Hz** | ≈ 0 | 39 / 5.9 mW | < 1 mK | yes, 0.115 mm plate gap (CAD) | 2.0 g | needs snubbers and a soft nose | custom plates | **Recommended** |
| PL112/122/127/140 (MFR AMF-11) | — | — | — | — | — | — | **no**: 9.6–11.0 mm wide | — | — | catalogue | Reject (width) |
| APA50XS amplified stack (MFR AMF-14) | 66 µm × 4.5 lever | 3.5 N | 2.7 kHz before lever | ≈ 0 | 150 V drive | — | **no**: 5 × 9 mm section, 10.3 mm diagonal | 4 g | — | catalogue | Reject (fit, 150 V) |
| Moving-magnet voice coil (SIM magpylib, em_planar topology) | ±300 µm | K_m 0.080 N/√W (n 1.38) | ≈ 60 Hz closed loop | **2.4 W** (1.3 W friction-free; 47.5 W without skid) | 16 mW | coil 118 °C, surface 98 °C at hold | yes | 0.69 g active | robust | make | **Reject**: 8× the 0.31 W thermal allowance, 0.11 h per charge |
| SQUIGGLE SQL-RV-1.8 (MFR AMF-15) | 11 mm/s needed vs > 10 mm/s at 25 g | 0.3 N stall | speed-limited | 0 | ~1 W | — | yes (2.8 mm) | 0.16 g | friction drive wears | OEM only | Reject: 1 M-cycle life = **35 h** of assist at 8 Hz |
| SMA wire, 50 µm NiTi (CALC, ASSUMP properties; PAT-06) | — | 0.3 N | thermal pole **0.47 Hz** (17× short at 8 Hz) | continuous heating | — | wire above A_f | yes | — | — | buy | Reject: efficiency 1.6 % |
| LRA 6 mm as corrector (MFR AMF-45) | moves no nib | 0.12 mN at 8 Hz | 150–250 Hz | — | — | — | yes | — | — | buy | Reject: needs 0.17 N; useful for haptics only |
| Gyroscope (3.3 g brass rotor, 50 000 rpm; ASSUMP) | — | torque 32 µN·m vs 1.4 mN·m hand torque (2.3 %) | — | spin-up | — | — | yes | 3.3 g | — | make | Reject: does not resist translation |
| Reaction mass / active TMD (3.45 g cell, ±0.5 mm) | — | 1.1–9.8 mN (4–12 Hz) vs 172 mN needed | — | — | — | — | yes | — | — | make | Reject: would need about 68 g·mm |

Notes on the table:

- **Hold power.** The piezo row's ≈ 0 excludes the driver's quiescent power (§5).
- **Voice-coil thermal model.** 1-D barrel conduction: PA-GF30 over a stainless tube, h 10 W/m²K, fingers 600 W/m²K on the grip (ASSUMP). Coil to ambient is 36 K/W. This supersedes the 580 K/W hand scaling and the 0.13 N/√W length^1.5 estimate.
- **Why a voice coil fails.** Every electromagnetic candidate fails on P = (F/K_m)², even behind the skid. The piezo wins because its static hold is capacitive.

## 4. Recommended stage (A1c): 2.6 mm quad, push-pull pair per axis

### 4.1 Beam model and lever (CALC from MFR AMF-11 and CAD)

- **Beam model.** Each plate is a cantilever with free length L 28 mm and thickness t 0.67 mm:
  - uniform piezo moment M_p = 2EIδ_f/L² = 4.34 mN·m at full drive;
  - tip deflection δ = M_pL²/(2EI) − FL³/(3EI), which is δ_f(V) − F/k_b;
  - k_b = 517 N/m per plate, and EI = kL³/3 gives E_eff = 58 GPa.
- **Plate resonance check.** The bare-plate first mode is 376 Hz (Euler–Bernoulli) against 360 Hz ± 20 % in the datasheet. The density, 7.8 g/cm³, is an assumption.
- **Per axis (pair).**
  - At the collar: F_b = 0.465 N and k = 1033 N/m.
  - At the nib, through the 62/45.5 = **1.363** lever and the leaves in series: F_b 0.329 N, k_b 536 N/m, parasitic 38.6 N/m (other axis' leaves plus gimbal), m_eq 0.395 g, coupling mass 0.652 g.
- **Load line.** The stroke is symmetric about the housing-fixed centre because roll is unknown: q = (F_b,nib − |F|)/(k_b + k_par).
  - The optimum lever n* = F_b,col/(2F) is 1.37 at 0.170 N, and the curve is flat: 277 µm at n 1.3, 276 µm at 1.4 and 272 µm at 1.5.
  - Over the 9 θ × 3 F_c × 3 μ grid, 49 % of cases keep ≥ ±300 µm.
  - It fails at low altitude combined with stiff springs or high friction (fig_stroke_under_load.png).

### 4.2 Decoupling leaves (CALC; material MFR AMF-18/19; buckling factor ASSUMP, confirm by FEA)

| Leaf | Cross stiffness | Drive stiffness | Buckling SF at plate F_b | Stress at the stops | Loaded stroke |
|---|---|---|---|---|---|
| First CAD leaf (P0.1.0–P0.1.1): 25 µm × 0.45 mm stainless, **1 mm** free span | **1357 N/m (2.6× the axis)** | 440 kN/m | 19 | **4.2 GPa** | **84 µm** |
| Recommended, in CAD P0.1.2: C17200, 30 µm × 1.2 mm (radial), **5 mm** span | 34 N/m (7 %) | 54 kN/m | 2.4 | 138 MPa (104 MPa at ±0.30 mm) | 277 µm |

Design rule: the leaf must satisfy all four at once:

1. across ≤ 5 % of the axis stiffness;
2. along ≥ 20×;
3. lateral-torsional buckling SF ≥ 2;
4. alternating stress ≤ 150 MPa (AMF-19).

A single leaf meets these only with about 4.5–5 mm of free axial span. **Done in CAD P0.1.2**: the collar stays at z = 15–18 mm (the nose Hall sensor needs the wider part of the nose), the plates start at z = 23 mm and the gimbal moves to z = 62 mm, so the leaves span 5 mm and the lever is 1.363 with the loaded stroke unchanged within 1 %. (Moving the collar forward to z ≈ 12–13 mm would also work, at n 1.26–1.28, but leaves no room for the Hall sensor.)

### 4.3 Resonance, sensor, servo

- **First resonance.** 192 Hz lumped and 195 Hz FE (14 elements; the next modes are 1.77 and 5.5 kHz). CALC.
- **Position sensor.** A 3-D Hall sensor in the nose faces a 0.6 × 1 × 1 mm NdFeB magnet on the collar (SIM magpylib).
  - Sensitivity is 190 / 95 mT/mm (x/y) at the centre and 34 mT/mm at the worst point of the travel.
  - With 0.1 mT noise (ASSUMP) that is 1.4 µm (centre) to 4 µm (worst) at the nib.
  - The piezo drive carries no coil current, so there is no crosstalk.
- **Servo.** Runs at 10 kHz (Hall at ≥ 10 kSPS, ASSUMP). It combines:
  - feedforward k·q_ref + (c + K_d)·q̇_ref + m·q̈_ref;
  - a constant contact-gated bias for the expected N_nib cos θ (not a measured-force feedforward, so DEC-011 does not apply);
  - integral action with a 25 Hz corner;
  - damping on the measurement (ζ 0.4, 600 Hz filter).
- **Servo margins** (CALC). PM ≥ 52° and GM 14.8 dB for open-loop damping 0.05; PM ≥ 46° for 0.02–0.1. |S(8 Hz)| is 0.31. At a 2 kHz servo rate the damping loop keeps only about 6° of phase margin, which is why the rate is 10 kHz.

### 4.4 Ceramic stress at the stops

The strength basis is LIT (proposed AMF-48): poled multilayer PZT, σ₀ 124 MPa (elastic), Weibull m 8, scaled to the plate's effective volume, which gives about 181 MPa. **The PICMA material and diced custom edges are UNKNOWN (EXP-Q04).**

| Case | Clamp stress | P_fail per event | Label |
|---|---|---|---|
| Rated blocking force | 33.5 MPa | 1.4 × 10⁻⁶ | CALC |
| Pushed onto a stop, unpowered | 21.6 MPa | 4 × 10⁻⁸ | CALC |
| Pushed onto a stop while driven the other way | 55.0 MPa | 7 × 10⁻⁵ | CALC |

### 4.5 Drive electronics

See §5 for power.

- **Prototype driver:** 2 × DRV2700 at 60 V (MFR AMF-16). The quiescent current is 9.8 mA × 2 by interpolation, which is 72 mW. The driver drives µF loads (3.3 µF up to 30 Hz).
- **Product driver:** a shared low-Iq boost (LT8330 class, 6 µA, 60 V switch; MFR proposed AMF-47) at about 55 V, plus one discrete charge-recovery half-bridge per axis.
  - A 55 V rail costs 17 % of the loaded stroke: 229 against 277 µm (CALC).
- **Integrated alternative:** the BOS1921/1931 CapDrive (MFR proposed AMF-46) has energy recovery. Its rating is ≤ 820 nF at 100 Vpp/130 Hz against our 2.0–2.6 µF per axis, and it draws 3.7 mA at DC. It needs vendor qualification.

### 4.6 One-metre drop onto the nib

SIM: FE plate with the collar share as a tip mass, unilateral stops and a transverse half-sine pulse with Δv 6.2 m/s. The pulse assumes a 1 m drop with restitution 0.4 (ASSUMP); the floor and nose compliance are unknown.

| Pulse | Peak | Stops only | + 2 snubbers | + 4 snubbers (P_fail) |
|---|---|---|---|---|
| 0.2 ms | 4970 g | 604 MPa | 234 MPa | 235 MPa (≈ 1) |
| 0.35 ms | 2840 g | 451 MPa | 146 MPa | 144 MPa (0.15) |
| 0.5 ms | 1990 g | 377 MPa | 135 MPa | 111 MPa (0.02) |
| 1 ms | 990 g | 234 MPa | 101 MPa | 77 MPa (1 × 10⁻³) |
| 2 ms | 500 g | 139 MPa | 64 MPa | 49 MPa (3 × 10⁻⁵) |

- **Axial drop** (nib first, 0.35 ms): 6.9 MPa, benign.
- **Sideways drop.** Stops alone leave the plates to whip: fracture is near-certain below 2 ms. **Required:**
  - snubbers along each plate, with gaps equal to the operating shape plus 30 µm;
  - a compliant nose that stretches the pulse to ≥ 2 ms (CALC/SIM);
  - a drop test (EXP-Q04).

### 4.7 Haptic cue from the stage (CALC; threshold LIT HAP-27)

The reaction of 0.63 g × ω²A acts on the 13.3 g pen at 200 Hz. The threshold there is about 0.08 µm, which is 0.13 m/s².

| Nib amplitude | Barrel acceleration | Above threshold |
|---|---|---|
| 20 µm (in contact) | 0.11 Grms | 21 dB |
| 100 µm (pen up) | 0.54 Grms | 35 dB |
| 300 µm (pen up) | 1.6 Grms | 45 dB |

A 6 mm LRA gives 3.4–6.8 Grms (MFR AMF-45, 50–100 g jig ASSUMP). **The stage can cue; the LRA is optional.** Keep bursts near 20 µm in contact so the ink wiggle stays inside the line.

## 5. Power and battery (90 mAh, 3.7 V, 80 % usable = 0.266 Wh; electronics 65 mW ASSUMP incl. 50 mW optics placeholder)

**Analytic drive table** (CALC). One axis at 0.3 mm plus the other at 0.12 mm (ellipticity 0.4). C is 2.03 µF × 1.3 large-signal (ASSUMP). V amplitude 15.5 V.

| f (Hz) | Reactive, major axis (mVA) | DRV2700: rail / battery (mW) | Recovery: rail / battery (mW) |
|---|---|---|---|
| 4 | 8.0 | 27 / 109 | 4.1 / 6.2 |
| 8 | 16.0 | 55 / 146 | 8.2 / 11.3 |
| 12 | 23.8 | 82 / 182 | 12.3 / 16.4 |

Real power is class-B charging: f·C·V_pp·V_rail. The recovery column uses η 0.85 per direction and an 80 % boost (ASSUMP, EXP-Q05). The DRV2700 figures include its 72 mW quiescent power.

**Battery life from the simulation** (SIM). Model P1, mean of 4 seeds, 0.3 mm tremor.

| Mode | Hall noise | DRV2700: power / life | Recovery: power / life |
|---|---|---|---|
| Recording only (drivers off) | — | 65 mW / **4.1 h** | 65 mW / **4.1 h** |
| Stage held (neutral) | 1 µm | 308 mW / 0.87 h | 97 mW / 2.8 h |
| Tremor assist, full correction (oracle), 6 Hz | 1 µm | 320 mW / **0.83 h** | 97 mW / **2.7 h** |
| Tremor assist, oracle, 10 Hz | 1 µm | 328 mW / 0.81 h | 98 mW / 2.7 h |
| Tremor assist, Kalman, 10 Hz | 1 µm | 520 mW / 0.51 h | 133 mW / 2.0 h |
| Guided assist, 6 Hz tremor | 1 µm | 386 mW / 0.69 h | 110 mW / 2.4 h |
| Oracle, 6 Hz | 0.3 µm | 216 mW / 1.23 h | 80 mW / **3.35 h** |
| Oracle, 6 Hz | 0 | 188 mW / 1.42 h | 75 mW / 3.57 h |

Energy per hour equals the power column (for example 97 mWh per hour of assisted writing with recovery).

Hall noise matters because the damping servo turns 1 µm of sensor noise into about 110 mW of class-B drive power (24 mW with recovery). **Target ≤ 0.3 µm** at 10 kSPS, from a quieter sensor, averaging or an observer-based damping loop.

Barrel temperature, from the same 1-D model (CALC): 32.5 °C maximum for recording or recovery drive, and 37.4 °C with 2 × DRV2700. The limit is 41 °C.

## 6. Simulation results (A2, model P1)

**Model P1** (`sim/pencil/`) couples:

- the two-stage hand (HAP-26) and synthetic handwriting and tremor (M1 scenario builders);
- the housing with a skid–paper LuGre contact, switchable;
- the spring-loaded refill with a LuGre ball contact and bushing friction;
- the two-axis piezo stage (force source k_b·δ_free(V) with parasitics and stops), the driver lag and slew, the 0–60 V limit and Bouc–Wen hysteresis (12 %, ASSUMP);
- Hall, optical, IMU and axial-slide sensing with the parameters.yaml noise and delays;
- the M1 estimators.

Integration is symplectic Euler at 25 µs. The fastest modes are the ball–paper contact at 1.2 kHz and the stage at 192 Hz, so ω·dt ≤ 0.19.

Protocol (harness convention):

- **Reference:** the same pencil in neutral mode on the same writing without tremor.
- **Ratio:** controller error ÷ neutral error, both against that reference.
- **Oracle:** fed the clean housing path.
- **Kalman:** frozen `estimator_selection.json` set (q_j 0.1, q_t 10⁻⁸, 7 Hz, gate 7.5 Hz).
- **Seeds:** test seeds 200–203.

Ink-error ratio vs neutral (mean of 4 seeds; sd ≤ 0.04). SIM:

| Tremor | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz |
|---|---|---|---|---|---|
| Neutral error, 0.3 mm (µm) | 240 | 295 | 374 | 462 | 528 |
| Oracle 0.1 / 0.3 / 0.5 mm | 0.19 / 0.20 / 0.40 | 0.21 / 0.24 / 0.45 | 0.25 / 0.32 / 0.52 | 0.25 / 0.40 / 0.57 | 0.26 / 0.46 / 0.61 |
| Time at the travel limit, oracle 0.3 mm | 16 % | 27 % | 39 % | 57 % | 65 % |
| Kalman 0.1 / 0.3 / 0.5 mm | 1.12 / 1.01 / 1.00 | 1.03 / 1.00 / 0.99 | 1.10 / 0.89 / 0.85 | 1.22 / 0.86 / 0.87 | 1.21 / 0.88 / 0.92 |
| Guided (time-aligned) 0.1 / 0.3 / 0.5 mm | 1.51 / 1.04 / 1.00 | 1.41 / 1.01 / 0.99 | 1.23 / 0.99 / 0.96 | 1.23 / 0.99 / 0.95 | 1.16 / 0.97 / 0.94 |

Other results (SIM):

- **Distortion without tremor.** Kalman 30 µm, guided 92 µm.
- **Guided mode on the feature course** (path distance to the template, 6 Hz 0.3 mm, 4 seeds, as `sim/guided_eval.py`):

  | Feature | Neutral → guided |
  |---|---|
  | Circle | 348 → 174 µm |
  | Spiral | 334 → 202 µm |
  | Fast stroke | 112 → 20 µm |
  | Dots | 155 → 90 µm |
  | Corners | 188 → 161 µm |
  | Hatching | 175 → 158 µm |

  Guided pulls toward the template, not the reference ink, so its time-aligned ratio on free writing is ≈ 1.
- **Skid on/off, passive effect on housing tremor** (3–15 Hz band, stage held, vs a conventional pen that carries 1 N at μ 0.15):
  - skid μ 0.12: **1.04–1.07×**, with in-band ink error 1.09×;
  - frictionless skid: **1.23–1.50×**, in-band ink error 1.33–1.53×.

  Nose friction damps housing tremor about as much as a conventional nib. The skid neither adds nor removes that. A slippery skid would raise housing tremor 23–50 %.
- **Device distortion vs a rigid conventional pen:** 119 µm. Of this, 116 µm is the skid's different contact and drag (a changed feel, EXP-H03) and 16 µm is the servo's compliance.
- **Sensitivity** (oracle ratio 6 / 10 Hz, 0.3 mm, seeds 200–201):

  | Case | Ratio (6 / 10 Hz) | Voltage saturated (6 Hz) |
  |---|---|---|
  | Q nominal | 0.22 / 0.36 | 0 % |
  | L pair | 0.24 / 0.37 | 1 % |
  | L at −20 % tolerance | 0.25 / 0.37 | 16 % |
  | **L at 35°** | **0.51 / 0.47** | 51 % |
  | Q at 35° | 0.29 / 0.38 | 10 % |
  | Q at 35° and −20 % | 0.37 / 0.37 | 39 % |
  | F_c 0.30 N | 0.29 / 0.39 | 27 % |
  | μ_nib 0.35 | 0.29 / 0.44 | 2 % |
  | θ 75° | 0.38 / 0.46 | 0 % |
  | No hysteresis, Hall 0.3 µm or 55 V rail | unchanged within 0.01 | 0 % |

## 7. Verification

`python3 -m pytest sim/pencil/tests -q`: **10 passed** (about 11 s).

- **Statics against A1** at 35, 50 and 75°:
  - N_nib sin θ = spring force (2 %);
  - stage force = N_nib cos θ (3 %);
  - skid force = N − N_nib (3 %);
  - servo holds q < 5 µm.
- **Load line.** Open-loop full drive against 0.17 N matches `design.stroke_under_load` (2 %).
- **Free stage resonance.** Matches √(k/m_eff) (2 %).
- **Servo tracking in air.** 10 Hz sine: gain 1 ± 0.05 and phase < 10°. Class-B power bookkeeping matches f·C·V_pp·V_rail (10 %).
- **Cross-check against M1.** Stage and slide locked, skid off, M1 masses:
  - the pencil model reproduces `sim/pensim` rigid-mode ink **exactly** (0.0 µm RMS difference);
  - locked-pen ink error is 280.6 µm in both;
  - `_kf_step` is identical to M1's.
- **Regression guards.** Oracle ratio < 0.4 (6 Hz, 0.1 mm), plus the A1 load and protrusion formulas.
- **Model consistency** (CALC):
  - FE static stress within 0.1 % of the closed form;
  - lumped 192 Hz against FE 195 Hz;
  - bare-plate 376 Hz against the datasheet 360 Hz ± 20 %.

## 8. Make vs buy

| Item | Decision |
|---|---|
| D1 low-force refills | buy; select by EXP-Q02 |
| PL128.10 benders (1-axis rig) | buy (AMF-11) |
| Custom 2.6 × 36 × 0.67 mm multilayer plates (×4) | make, as a supplier custom part |
| C17200 leaves; collar; etched cross-strip gimbal; PTFE-lined bushings; POM-PTFE skid; nose with snubbers; PA-GF30 barrel over a stainless tube | make |
| Prototype driver: 2 × DRV2700 EVM | buy (AMF-16) |
| Product driver: LT8330-class boost + charge-recovery half-bridges | make from catalogue parts, or qualify a CapDrive part |
| 3-D Hall sensor and magnet; nRF54L15 (AMF-44); IMU; optics | buy |
| Rigid-flex board, firmware (piezo servo, estimators, safety) | make |
| Cell: custom 6.5 × 40 mm cell (~90 mAh), or 3 × CG-425A | make (custom cell); CG-425A buy (AMF-43) |

## 9. Development steps and experiments (in order)

1. **Skid.**
   - EXP-Q01: skid friction coefficient on a bench tribometer (POM-PTFE, PTFE and sapphire on 3 papers; N 0.2–2 N; 1–100 mm/s; static and kinetic). It gates μ_skid and the passive damping.
   - EXP-H03: skid feel, smear and passive tremor (existing blinded study; DEC-008).
2. **Nib force.** EXP-Q02: low-force ink line quality (line width, skips and density against nib force 0.05–0.5 N). It sets F_c, which scales every stage load.
3. **Benders.** EXP-Q04 (new): bender characterisation and strength:
   - stroke, blocking force, hysteresis (Bouc–Wen fit) and creep;
   - large-signal capacitance and leakage;
   - tip-load-to-failure on diced 2.6 mm plates (σ₀, m);
   - drop test with and without snubbers.
4. **Drive.**
   - EXP-Q05 (new): piezo driver efficiency and quiescent power. Compare DRV2700 against a charge-recovery stage on 2–2.6 µF at 4–12 Hz and in 200 Hz bursts, including Hall-noise-driven power.
   - EXP-Q03: cell pulse discharge.
5. **Loaded 1-axis rig.** EXP-Q06 (new): PL128.10 with a D1 refill and a skid nose on the stage-A rig. Measure:
   - stroke under load against θ and μ;
   - leaf cross-stiffness and the bushing nib-force band;
   - resonance and closed-loop tracking;
   - cancellation with injected disturbance (EXP-B09 protocol).
6. **Two-axis demonstrator.** EXP-Q07 (new): Q stage in a 7.9 mm bore. FRF, cross-coupling and stops (EXP-B05 protocol), then repeat EXP-Q04 on the assembly. This gates Rev P1.
7. **Claims.** EXP-H01/E01 (separability; decisive for free-writing assist), EXP-H02 (form factor), EXP-H06 (crossover).

## 10. Open risks

1. **Stroke margin.**
   - ±277 µm at the worst-direction design load, ±162 µm at −20 % tolerance, ±48 µm at 35°.
   - Tremor ≥ 0.3 mm hits the limit 16–65 % of the time even for the oracle.
   - The pencil corrects small tremor well and larger tremor partly.
2. **Decoupling leaf.** The first CAD leaf failed; the recommended leaf and its 5 mm span are in CAD P0.1.2. Its buckling factor is assumed (FEA).
3. **Drop.** Fracture is likely without snubbers and a compliant nose. The ceramic strength of the PICMA material and diced edges is unknown (EXP-Q04).
4. **Driver.** No off-the-shelf part is both low-power and rated for 2–2.6 µF. The DRV2700 alone limits assist to under 1.5 h.
5. **Sensor noise and servo.**
   - Hall noise dominates drive power.
   - The 10 kHz servo rate and 10 kSPS Hall sensing are assumptions.
   - Open-loop damping (0.05) and hysteresis (12 %) are assumed (EXP-Q04/Q07).
6. **Nib-force band.** The band from the bushings needs PTFE-lined bores. The CAD collar bore is bare titanium on brass.
7. **Physics still unmeasured.** Low-force ink quality (EXP-Q02), skid feel and smear (EXP-H03), skid contact stiffness and friction (ASSUMP), and a hand model measured in-plane without paper (HAP-26).
8. **Intent separation is unchanged from M1.** The Kalman helps only at ≥ 8 Hz and ≥ 0.3 mm (EXP-H01/E01). Guided tasks remain the credible use.
9. **Electronics power.** The 50 mW optics placeholder dominates recording-only power (EXP-P01).

## 11. Files and how to run

| What | Command | Runtime |
|---|---|---|
| A1 analysis → `results/pencil/mechanisms.json`, `fig_*.png`, `proposed_evidence_rows.csv` | `python3 analysis/pencil_mechanisms.py` | ≈ 90 s (magpylib on 2 processes); `--fast` ≈ 20 s with the cached sweep |
| A2 study → `results/pencil/sim_metrics.json`, `viz_trace.json` (1.1 MB), `fig_sim_*.png` | `python3 -m sim.pencil.run_study` | ≈ 95 s on 2 processes |
| Tests | `python3 -m pytest sim/pencil/tests -q` | ≈ 11 s |

Code:

- `sim/pencil/design.py`: shared design model.
- `sim/pencil/power.py`: drive power and battery.
- `sim/pencil/core.py`, `model.py`, `evaluate.py`: model P1.

The numba cache for this package goes to `sim/pencil/build/`, never `sim/pensim/`.
