# Mechanics and packaging

**Evidence status:**

- **Proposed design:** CAD concept at nominal geometry.
- **Calculation:** flexures, tolerances, mass, trade study, thermal network.
- **Simulation:** field models, coupled dynamics.

No part has been made or measured. Measured values replace these rows in EXP-B03, B05, M02 and M03 (`validation/bench_protocols.md`).

## Architecture (Rev A baseline, configuration B)

- **Nib carrier.** The refill is carried in a titanium carrier tube. The tube pivots about a virtual centre on the axis **L1 = 12 mm** behind the ball (DEC-003).
- **Axial suspension (DEC-007, revised).** The refill slides inside the carrier on a spiral-arm diaphragm suspension (k_ax ≈ 2 kN/m, DEC-006), so the carrier and coil paddle do **not** slide axially (κ_s = 1).
  - The lever arm changes with the slide, L1 − s. The controller compensates this from the measured slide.
  - Rejected layout: the whole lever sliding (κ_s = 0) consumes the actuator's axial gap (see Tolerances).
- **Actuator.** A rear annular sandwich Lorentz actuator, 38 mm behind the pivot (n = L2/L1 = 3.17). A moving-coil paddle on the carrier sits between two fixed quadrant-magnet rings with back iron. Each side has a 0.50 mm axial gap (Rev A.1).
- **Stage and force sensing.** A sense magnet on the refill's rear plug is read by a 3-axis Hall sensor on a tail flex. The x/y channels give the lever angle; z gives the axial slide and hence the writing force.
- **Optics.** Three chip-scale optical modules sit in the nose flanks at 30/150/270°, so one faces the page at any roll angle.
- **Envelope.** Barrel Ø15 mm, with a local Ø16 mm bulge over the actuator; length 150 mm.

## Files

| Path | What it does | Output |
|---|---|---|
| `cad/bench_rig.py` | Stage-A loaded bench mechanism (pen-scale nib, lever and gimbal; two commercial VCMs; hand-simulant disturbance stage; goniometer; dead-weight normal force; F/T-sensed platen on an XY stage) with platen-clearance check | `results/cad/bench_rig_*`, `drawing_bench_rig.png` |
| `cad/pen_revA.py` | Parametric CadQuery model with swept-workspace interference check at full tip travel in 12 directions, fixed-vs-fixed check, and mass/CoM table. `--variant A1` applies the Rev A.1 packaging and tolerance changes | `results/cad/pen_revA*_summary.json`, STEP assembly and parts |
| `drawings/make_drawings.py` | Section and cross-section drawings from the model | `results/cad/drawing_revA_*.png/svg` |
| `flexure_calc.py` | Wire-pivot candidates (all fail on stress or buckling), cross-strip gimbal, spiral-arm diaphragm | `results/mechanics/flexure_calc.json` |
| `tolerance_analysis.py` | Clearance stacks S1–S5: worst case, RSS and Monte Carlo | `results/mechanics/tolerance.json`, `fig_gap_budget.png` |
| `mass_budget.py` | CAD masses plus allowances plus 10 % contingency for Rev A, A.1, and A.1 with a polymer rear barrel | `mass_budget.csv`, `results/mechanics/mass_budget.json` |
| `../analysis/config_trade.py` | Configurations A–F at design/high/bench-corner loads | `results/trade/config_trade.json` |
| `../analysis/em_actuator.py`, `em_planar.py` | magpylib field models of the actuator candidates | `results/em/*.json` |
| `../analysis/thermal.py` | Lumped thermal network | `results/thermal/thermal.json` |

Regenerate:

```bash
python3 mechanics/cad/pen_revA.py
python3 mechanics/cad/pen_revA.py --variant A1
python3 mechanics/flexure_calc.py
python3 mechanics/tolerance_analysis.py
python3 mechanics/mass_budget.py
```

Dependencies: CadQuery 2.8, magpylib 5.2, numpy, scipy, matplotlib.

## Key numbers (calculation unless stated)

| Quantity | Rev A | Rev A.1 | Source |
|---|---|---|---|
| Modelled mass (solids × density) | 31.6 g | 28.5 g | CAD |
| Mass with allowances + 10 % contingency | 40.7 g | 37.2 g; **33.2 g** with polymer rear barrel | `mass_budget.json` (REQ-FORM-003 ≤ 35 g) |
| Centre of mass from the tip | 80.6 mm | 79.4 mm; **76.0 mm** with polymer rear barrel | REQ-FORM-004 ≤ 70 mm: **still violated** |
| Moving mass / tip-equivalent inertia | 1.93 g / **13.4 g** | 1.96 g / **13.7 g** | CAD distributed-mass integration (the earlier 10.3 g point-mass figure understated it); REQ-MECH-003 ≤ 12 g **violated**. The simulator already uses 13.7 g |
| Mechanical tip travel / lever tilt | 0.65 mm / 3.11° | 0.60 mm / 2.87° | tolerance analysis |
| Pivot stiffness at the tip | cross-strip gimbal 75.8 N/m; stress 177/82 MPa (full travel / typical); buckling margin 19 | same | `flexure_calc.json` |
| Axial suspension | spiral-arm diaphragm 1984 N/m, 231 MPa at the 0.6 mm stop | same | `flexure_calc.json` |
| Holding power at the design point (θ 50°, N 1 N) | 0.48 W (coil ≈ 85 °C) | +6 % for the wider gap | trade, thermal, tolerance |
| Interferences at full travel (nominal geometry) | none | none | CAD check |

Model inconsistency: the CAD still models the pivot with three inclined wires. The flexure analysis replaced them with a cross-strip gimbal at the same virtual centre. The mass difference (~0.1 g) is carried as an allowance; the gimbal geometry is a CAD to-do (M-3).

## Tolerances

`tolerance_analysis.py` uses the nominal CAD geometry. Tolerances are assumed at ±3σ for ground or bonded precision parts; each is listed with its basis in the JSON.

| Stack | Rev A nominal | Rev A.1 (gap 0.50, travel 0.60, κ_s = 1) | Consequence |
|---|---|---|---|
| S1 paddle–magnet, front face (tilt) | RSS +14 µm (worst −185 µm) | RSS **+93 µm** (worst −106 µm) | Gap 0.45 → 0.50 mm costs about 2.9 % of K_f (6 % power) |
| S1 rear face, whole lever slides (κ_s = 0) | contact probability 0.97 at design load, 1.0 at the axial stop | 0.56 / 1.0 | κ_s = 0 **rejected** (DEC-007 rev.) |
| S1 rear face, refill slides (κ_s = 1) | RSS +125 µm | RSS **+188 µm** | — |
| S2 carrier through magnet bore at full swing | RSS +16 µm | RSS **+174 µm** | Travel limited to 0.60 mm (control limit 0.55 mm) |
| S3 ball/cone in 3.6 mm aperture | RSS +0.48 mm | +0.53 mm | Not critical |
| S4 lever-ratio gain | ±0.87 % RSS | same | Calibrated out (EXP-B04) |
| S5 Hall sense-magnet distance vs refill length (±0.3 mm, VERIFY ISO class) | field ×0.65 … ×1.65 | same | Firmware re-zeroes the force channel at every refill insertion |
| S6 nose-to-paper clearance, worst stage position | **−2.1 mm at 35°, −1.2 mm at 50°: the nose touches the paper** (tip Ø6 mm, 1 mm behind the ball) | +0.60 / +2.1 / +4.4 mm at 35 / 50 / 75° (tip Ø5.2 mm, 5 mm behind the ball, aperture 4.2 mm) | The refill point must protrude about 5 mm, as on an ordinary ballpoint; the optics at z 14.2 mm still fit inside the nose (CAD check) |

Simulation of the κ_s choice (`sim/diag_kappa.py`, `results/sim/kappa_compare.json`) shows κ_s = 1 with compensation matches κ_s = 0. Device distortion is 59–61 µm in both. The oracle ratio is 0.27 vs 0.31 at 35° and 0.127 vs 0.131 at 50°.

## Bench rig concept (prototype stage A)

The rig tests the physics (EXP-B01, B03, B05, B06, B08, B09) before the miniature pen exists. It has a dimensioned parametric CAD: `cad/bench_rig.py` → `results/cad/bench_rig_assembly.step`, `bench_rig_summary.json`, `drawing_bench_rig.png`. The model checks that the module clears the platen from 35° to 75°. That check forced the module to adopt the pen's slim nose, with the wide VCM frame starting 40 mm up the axis.

1. **Nib and lever module at pen scale, oversized actuation.**
   - A real D1 refill in a titanium carrier on a cross-strip gimbal, L1 = 12 mm.
   - Driven through the same 3.17:1 lever by two commercial 12.7 mm moving-coil VCMs (Moticont LVCM-013 class, K_m ≈ 0.8 N/√W; AMF-02), in place of the custom annular actuator.
   - This removes actuator risk from the first cancellation experiments. EXP-B03 then qualifies the custom actuator separately.
2. **Housing held by a hand simulant or a real hand.**
   - The rig housing is either (a) mounted on a 2-axis voice-coil shaker that injects recorded or synthetic tremor with a two-stage impedance matching HAP-26, or (b) held by participants for the EXP-B06 grip identification.
3. **Page and reference metrology.**
   - Paper on a 6-axis force/torque sensor (Nano17 class, ~3 mN resolution) on a motorised XY stage for the writing motion. A goniometer sets θ from 35° to 75° and φ.
   - Housing motion by laser triangulation (µm class, ≥ 10 kHz).
   - Deposited ink scanned at ≥ 2400 dpi (10.6 µm per pixel) for the ink-error metrics defined in `docs/physics.md` §8.
4. **Electronics.** Rev A drive, sense and interlock circuit (`electronics/`) on a bench-size board, streaming research frames over USB (`docs/icd.md` §4.2). Timing and fault behaviour are therefore exercised on the real control path.

Prototype stage B (the tethered research pen) starts only after stage A shows these results:

- loaded cancellation at practical force (EXP-B09 gate);
- ink tolerance to the resulting force modulation (EXP-B08).

## Open issues

- **M-1.** The centre of mass is 76 mm even with a polymer rear barrel, against ≤ 70 mm. The requirement itself is provisional: compare with ordinary pens in EXP-M03 and H02. Options: 140 mm length, lighter stator (reduced back iron, at a K_m cost), cell moved forward of the PCB (then RF moves).
- **M-2.** Rev A.1 needs a 41 mm PCB and a ~32 mm pouch cell (DEC-014). Obtain a supplier drawing for a 5 × 12 × 32 mm cell rated ≥ 5 C.
- **M-3.** Replace the wire pivots with the cross-strip gimbal in the CAD; model the diaphragm; model the three optical windows.
- **M-4.** Moving-coil leads cross the pivot: flex-life of the coil leads over 10⁷ tremor cycles (EXP-M02, B10).
- **M-6.** Tip-equivalent inertia is 13.7 g, above the ≤ 12 g requirement. A CFRP carrier tube (1.55 g/cm³ against titanium's 4.43 g/cm³) would bring it to about 9.5 g (calculation). The price is stiffness and bond-joint risk at the gimbal and paddle.
- **M-5.** The thermal path from a moving coil in an air gap (~130 K/W) sets the holding-power limit. Measure it early (EXP-B07).
