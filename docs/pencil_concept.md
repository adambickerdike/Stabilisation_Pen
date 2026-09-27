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
3. **The stage is piezo, not a coil.** A piezo bender holds a static load at almost no power. Custom-width multilayer benders (PICMA technology, AMF-11) fit beside a D1 refill in the 7.9 mm bore. CAD: 11.5 g before wiring and margin (L layout), and no interference at full travel (§4).
4. **What the ink can gain is bounded.** The usable correction is about ±0.3 mm at the nib. That is enough to remove tremor of that size when the intended stroke is known, and to pull strokes toward a predicted template. It cannot turn one word into another. The pen corrects shapes physically; the app corrects spelling and words digitally (§6).
5. **AI prediction is used as a template.** The app predicts the next letters, synthesises them in the user's own style, and sends the template to the pen. Guided mode pulls the nib toward it, with authority scaled by confidence and bounded by travel. A wrong prediction therefore costs at most the travel limit (§6).
6. **Recording on paper needs a new sensor.** Nothing off the shelf fits the nose. The simulation sets the requirement: a page sensor of ≥ 120 Hz with ≤ 10 ms latency, fused with the IMU. The chip-scale camera that does fit runs at 30 fps and loses most of the guided-mode benefit (§5).
7. **Sim-to-real.** The calibration pipeline is built and tested on twin experiments. It predicts how much bench time each parameter needs, and what the calibrated simulator will and will not predict (§8).

## 2. Forces at the nib (pending: `pencil_mechanisms.md` §1)

## 3. Mechanisms with existing technology (pending: `pencil_mechanisms.md` §2)

## 4. Packaging (CAD)

`mechanics/cad/pencil_revP.py` builds the concept from `config/pencil.yaml`. It writes `results/cad/pencil_revP{L,Q}_summary.json`, a STEP assembly and the viewer primitives, and `mechanics/cad/pencil_drawing.py` draws the sections (`results/cad/drawing_pencil_revPL.png`). Nominal dimensions and rigid parts throughout; the checks are geometric.

Layout from the nib (z in mm from the ball, pen in contact at 50°):

| z (mm) | Part |
|---|---|
| 0 | ball of the D1-format gel refill |
| 1.1–1.5 | skid ring (PTFE-filled POM); contact radius 1.3 mm in P0.1.0; ≥ 1.4 mm needed (below) |
| 15–18 | front collar on the refill; 1 mm magnet; 3-D Hall sensor in the nose wall |
| 19–55 | piezo benders: free length 28 mm, clamp 47–55 |
| 60 | flexure gimbal with a slide bushing: the refill pivots here and slides axially |
| 68–77 | soft nib spring (axial force F_c) and its seat |
| 78–120 | rigid-flex board: nRF54L15 CSP (AMF-44), IMU, piezo drivers, PMIC |
| 121–161 | 6.5 × 40 mm Li-ion cylinder, about 90 mAh (ASSUMPTION, AMF-42/43) |
| 161–166 | plastic cap (antenna window) |

The lever from collar to nib is 60/(60 − 16.5) = **1.38** (CALC).

Results (CALC, CAD):

| Check | L: two 3.5 mm plates | Q: four 2.6 mm plates |
|---|---|---|
| Mass before wiring, adhesive and margin | 11.48 g | 12.12 g |
| Largest parts | cell 3.45 g, barrel 2.72 g, Ti clamp 1.40 g, board 1.34 g, refill 0.84 g, benders 1.32 g | benders 1.96 g |
| Centre of mass from the nib | 90.1 mm (54 % of length) | 87.3 mm |
| Plate corner to bore, tips at the ±0.40 mm stops | 0.26 mm | 0.79 mm |
| Plate to plate | 0.215 mm | 0.115 mm |
| Plate to refill | 0.51 mm | 0.51 mm |
| Collar magnet to Hall face at full travel | 0.15 mm | 0.15 mm |
| Refill cone to skid aperture at 35° with full travel | **0.026 mm** (needs ≥ 0.10) | same |
| Nib assembly swept through ±0.40 mm in 8 directions | no interference | no interference |

Packaging findings:
- **Plate width is capped by the bore.** Two 4.0 mm plates in an L collide at the corner and with the wall once the tips sweep to the stops. 3.5 mm (L) or four 2.6 mm plates (Q) fit. Blocking force scales with width: about 0.31 N per axis (L) or 2 × 0.23 N per axis (Q), against PL128.10's 0.55 N at 6.15 mm (AMF-11).
- **Skid ring radius 1.4 mm, not 1.3 mm.** At 35° the refill protrudes 1.86 mm beyond the skid plane, and its cone plus ±0.40 mm travel leaves only 0.026 mm to the aperture. A 1.4 mm ring restores the 0.10 mm clearance (`skid_ring_radius_required`).
- **Mass has margin; balance does not.** 11.5 g leaves about 7 g for wiring, grip features and margin under the 20 g target. The centre of mass sits at 54 % of the length because the cell is at the back. Swapping cell and board would move it about 8 mm forward (CALC).

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

## 6. AI prediction, guidance and autocorrect (pending: `ai_guidance.md`)

## 7. Power and battery (pending: `pencil_mechanisms.md`)

## 8. Sim-to-real (pending: `sim_to_real.md`)

## 9. What to make, what to buy, what to do (pending)

## 10. Open risks (pending)
