# Checkpoint — 2026-09-27

Use this file to resume work without losing assumptions. Branch: `claude/pensive-shannon-wzm6ls`. Parameter file: **v0.4.3** (simulation results are v0.4.2; the only simulator input that changed is worth 0.2–0.3 K of coil temperature).

## 1. What exists and what actually ran

| Area | Ran here | Not run or not possible here |
|---|---|---|
| Audit | Recalculation of all 37 report numbers (all reproduce); 28 corrections with severity | — |
| Evidence | 247 ledger rows; two decision-driving sources lead-verified against the primary text | Full-text access failed for some sources (listed in the ledger's limitations column) |
| Simulation | M1 coupled model, 12 tests passing; estimator tuning on seeds 100–105; nominal benchmark; 12-seed × 9 f × 3 amplitude grid; 160-sample Monte Carlo + rank sensitivity; failure cases F1–F7; design sweeps; κ_s comparison; guided-mode evaluation; contact-feedforward diagnosis | Validation against hardware (all EXP-B*) |
| Mechanics | CAD Rev A and A.1 (interference-free at full travel); flexure calculation; tolerance stacks S1–S6; mass budget; stage-A rig CAD with platen-clearance check; drawings | Physical parts; FEM of flexures and actuator |
| Electronics | KiCad 8 schematic generated; ERC (0 errors, 1 accepted warning); netlist cross-check pass (102 nets / 492 pins); BOM; drive/sense calculations; ngspice transient incl. coil short; placement study | PCB layout (DEC-014 open); datasheet checks behind 45 VERIFY and 3 SELECT BOM lines |
| Firmware | see `firmware/README.md` | Execution on nRF5340 hardware |
| ML | see `ml/README.md` | Any real-data training (no recordings exist) |
| App | see `app/README.md` | On-device recogniser (adapter specified only) |
| Validation | see `validation/README.md` | Every experiment and study |

## 2. Numbers the next session must not lose

All are calculation or simulation unless stated otherwise.

- **Load.** Transverse load = N·cos θ + friction terms (COR-01).
  - Static hold at N = 1 N: 0.82 / 0.64 / 0.25 N at 35° / 50° / 75°.
  - Copper loss at the same points: 0.81 / 0.49 / 0.08 W.
  - Moving-coil allowable is 0.412 W average (120 °C coil limit, 0.50 mm air gaps), and 70 % of the envelope (θ 35–75°, N 0.2–2 N, μ 0.05–0.35) stays within it in continuous contact.
  - Coil thermal path: 145 K/W coil to structure, 157 K/W steady to ambient; Rev A coil 96.6 °C at the design load.
  - Supply headroom: at 3.3 V the 6 Ω winding cannot hold 0.5 % of the thermally allowed envelope (hot, high-force corner); 4 Ω can (DEC-012 revisited, EXP-B03).
- **Actuator.**
  - Lever: n = 3.17, L1 = 12 mm.
  - K_m = 0.293 N/√W (analytic field model, with the 0.50 mm gap).
  - Winding: 6 Ω, K_f 0.717 N/A, L ≈ 175 µH (unmeasured).
  - Drive: 40 kHz PWM; current loop 2.3 kHz; design hold current 0.335 A.
- **Estimation.**
  - Oracle bound 0.22–0.32 across 4–12 Hz.
  - Kalman 1.03–1.14 at 4–9 Hz and 0.85 at 12 Hz. Since v0.4.2 the balanced and assertive objectives select the same set. At 0.15 mm tremor it adds error at every frequency.
  - Band-pass 1.1–1.5 below 7 Hz.
  - Distortion without tremor: Kalman 101 µm on 12 seeds (55 µm on 4), band-pass 168 µm. REQ-CTRL-005 (≤ 50 µm) is violated.
  - The selection is fragile: 3–5 % of the tuning objective separates an inert set from the active one, and the v0.4.2 plant change flipped it (`docs/sim_report.md` §3.2).
  - Guided mode: circle 443 → 164 µm, spiral 382 → 112 µm path distance.
- **Mechanism.** Device distortion (neutral vs rigid pen) ≈ 59 µm. Axial path 2 kN/m. γ ≈ 0.19 at 50°.
- **Budgets.**
  - Tip-equivalent inertia 13.7 g (requirement ≤ 12 g).
  - Mass 33.2 g with polymer rear barrel (requirement ≤ 35 g).
  - Centre of mass 76 mm (requirement ≤ 70 mm).
  - PCB courtyard: 779 mm² as drawn vs 517 mm² available; 0.65 density on a 41 mm board with the package plan.
- **Failures.** Power loss in contact moves the ink ≈ 0.8 mm. A frozen Hall sensor puts the stage on its stop. Coil-short trip 8.8 µs; VMOT off 22.6 µs (ngspice).

## 3. Provisional assumptions currently carried

- **Hand.** Literature impedance (HAP-26), measured in-plane and without the hand resting on paper. γ is computed from assumed normal compliances.
- **Paper contact.** Stiffness 5×10⁴ N/m; μ 0.15; LuGre parameters assumed. Friction turned out to drive estimator performance (ρ 0.52).
- **Optics.** Latency 2 ms, noise 3 µm, 1 kHz on paper at the nib (unmeasured; EXP-S01).
- **Writing and tremor.** Synthetic handwriting and tremor. Real separability is unknown.
- **Cell.** 200 mAh ≥ 5 C pouch; no supplier drawing yet.
- **nRF5340 DEC-pin values and RF matching.** Not retrieved from Nordic this session; marked VERIFY.

## 4. Blockers (exact measurement or external action)

| # | Blocker | What resolves it |
|---|---|---|
| 1 | Transverse load and friction on real paper and ink | **EXP-B01/B02**: 6-axis F/T sensor under a platen; θ 35–80°, N 0.2–4 N, 8 directions, 1–100 mm/s, 3 papers × 3 inks |
| 2 | Whether tremor is causally separable from real writing | **EXP-H01** (ethics approval, then instrumented passive pen, n ≈ 20 per group), then **EXP-E01** estimator bake-off |
| 3 | Loaded cancellation and ink tolerance | Stage-A rig build (`mechanics/cad/bench_rig.py`), then **EXP-B09** and **EXP-B08** |
| 4 | Actuator K_m, R, L and thermal path of a moving coil | **EXP-B03** coupons; **EXP-B07** thermal |
| 5 | Near-nib optical sensing on paper | **EXP-S01**; sensor access under NDA |
| 6 | Packaging (DEC-014) | Decide between a 41 mm board with pouch cell and a two-board split; pouch-cell supplier drawing; HDI layout attempt |
| 7 | Datasheet checks behind the VERIFY/SELECT lines | Datasheet review, with Nordic reference circuitry for the nRF5340 |
| 8 | Centre of mass and inertia above requirements | CFRP carrier; lighter stator or shorter barrel; confirm the CoM requirement against ordinary pens (EXP-M03, H02) |

## 5. Next actions, in order

1. Build the stage-A rig. Run EXP-B01 and B02; re-fit the contact and friction parameters (`config/parameters.yaml`, status → measured); re-run `sim/run_all.sh`.
2. Submit the EXP-H01 ethics application. Build the passive instrumented pen from the Rev A sensing subset.
3. Commission the Rev A electronics at bench scale on the rig; bring-up steps 1–12 (`electronics/README.md`).
4. Run EXP-B09 and B08. Decide the Phase B gate, DEC-008 (product configuration) and DEC-014 (packaging).

## 6. How to resume

- **Python.** `python3 -m pip install -r requirements.txt`, then `python3 -m pytest sim/tests -q`. The first run compiles numba (about a minute); later runs hit the cache.
- **KiCad 8 on Ubuntu 24.04 without `add-apt-repository`.**
  - Add the Launchpad key `FDA854F61C4D0D9572BB95E5245D5502FAD7A805` to `/usr/share/keyrings/kicad8.gpg`.
  - Add `deb [signed-by=/usr/share/keyrings/kicad8.gpg] https://ppa.launchpadcontent.net/kicad/kicad-8.0-releases/ubuntu noble main`.
  - Run `apt install kicad`.
  - Copy `/usr/share/kicad/template/{sym,fp}-lib-table` to `~/.config/kicad/8.0/`.
- **Long simulation runs.** Do not edit `sim/`, `stabpen/` or `config/` while `sim/run_all.sh` runs: worker processes re-import modules.
- **Generated files.** Regenerate from their scripts rather than editing outputs: `electronics/kicad/*`, `results/*`, `mechanics/mass_budget.csv`.
