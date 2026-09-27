# Checkpoint — 2026-09-27

Use this file to resume work without losing assumptions. Branch: `claude/pensive-shannon-wzm6ls`. Parameter file: **v0.4.4**; all simulation, trade, thermal and drive results are regenerated on it. The pencil-class concept has its own overlay, `config/pencil.yaml` **P0.1.2** (§7).

## 1. What exists and what actually ran

| Area | Ran here | Not run or not possible here |
|---|---|---|
| Audit | Recalculation of all 37 report numbers (all reproduce); 28 corrections with severity | — |
| Evidence | 247 ledger rows; two decision-driving sources lead-verified against the primary text | Full-text access failed for some sources (listed in the ledger's limitations column) |
| Simulation | M1 coupled model, 12 tests passing; estimator tuning on seeds 100–105; nominal benchmark; 12-seed × 9 f × 3 amplitude grid; 160-sample Monte Carlo + rank sensitivity; failure cases F1–F7; design sweeps; κ_s comparison; guided-mode evaluation; contact-feedforward diagnosis; frequency-gate diagnostic | Validation against hardware (all EXP-B*) |
| Mechanics | CAD Rev A and A.1 (interference-free at full travel); flexure calculation; tolerance stacks S1–S6; mass budget; stage-A rig CAD with platen-clearance check; drawings | Physical parts; FEM of flexures and actuator |
| Electronics | KiCad 8 schematic generated deterministically; ERC (0 errors, 1 accepted warning); netlist cross-check pass (102 nets / 492 pins); BOM; drive/sense calculations with the winding headroom assessment; ngspice transient incl. coil short; placement study | PCB layout (DEC-014 open); datasheet checks behind 45 VERIFY and 3 SELECT BOM lines |
| Firmware | C control core with safety, logging, calibration and ML guard; parameters generated from the YAML with a freshness check; 60 test cases (1120 checks) on host (ASan/UBSan) and emulated Cortex-M33; nRF5340 image links (32.3 kB flash, 29.4 kB RAM) | Execution on nRF5340 hardware; cycle-accurate timing; register-level drivers (VERIFY); IMU, optics, USB, flash and BLE drivers |
| ML | Synthetic data pipeline with writer-disjoint splits; six conventional baselines; causal TCN; int8 C export without f_est, bit-exact on 20 000 windows (16.2 k MAC, 7.3 kB weights); 22 tests | Any real-data training (no recordings exist) |
| App | ICD log reader with CRC and resync; immutable note store with provenance; search with stroke citations; grounded assistant with refusal rules; capture-fidelity analysis; 137 tests | On-device recogniser (adapter specified only) |
| Validation | 29 experiment protocols; 221 acceptance criteria generated into the protocols (checker passes); prototype stages and claim gates; human study plan | Every experiment and study |

## 2. Numbers the next session must not lose

All are calculation or simulation unless stated otherwise.

- **Load.** Transverse load = N·cos θ + friction terms (COR-01).
  - Static hold at N = 1 N: 0.82 / 0.64 / 0.25 N at 35° / 50° / 75°.
  - Copper loss at the same points: 0.80 / 0.49 / 0.08 W.
  - Moving-coil allowable is 0.412 W average (120 °C coil limit, 0.50 mm air gaps), and 70 % of the envelope (θ 35–75°, N 0.2–2 N, μ 0.05–0.35) stays within it in continuous contact.
  - Coil thermal path: 145 K/W coil to structure, 157 K/W steady to ambient; Rev A coil 96.6 °C at the design load.
  - Supply headroom: at 3.3 V the 6 Ω winding cannot hold 0.5 % of the thermally allowed envelope (hot, high-force corner); 4 Ω can (DEC-012 revisited, EXP-B03).
- **Actuator.**
  - Lever: n = 3.17, L1 = 12 mm.
  - K_m = 0.293 N/√W (analytic field model, with the 0.50 mm gap).
  - Winding: 6 Ω, K_f 0.717 N/A, L ≈ 175 µH (unmeasured).
  - Drive: 40 kHz PWM; current loop crossing at 2 kHz with 55.8° phase margin (2.3 kHz is the 50° limit); design hold current 0.335 A.
- **Estimation.**
  - Oracle bound 0.22–0.32 across 4–12 Hz.
  - Kalman 1.03–1.14 at 4–9 Hz and 0.85 at 12 Hz. Since v0.4.2 the balanced and assertive objectives select the same set. At 0.15 mm tremor it adds error at every frequency.
  - Band-pass 1.1–1.5 below 7 Hz.
  - Distortion without tremor: Kalman 100 µm on 12 seeds (55 µm on 4), band-pass 168 µm. REQ-CTRL-005 (≤ 50 µm) is violated.
  - The selection is fragile: 3–6 % of the tuning objective separates an inert set from the active one, and the v0.4.2 plant change flipped it (`docs/sim_report.md` §3.2).
  - Guided mode: circle 443 → 163 µm, spiral 382 → 112 µm path distance.
- **Mechanism.** Device distortion (neutral vs rigid pen) ≈ 59 µm. Axial path 2 kN/m. γ ≈ 0.19 at 50°.
- **Budgets.**
  - Tip-equivalent inertia 13.7 g (requirement ≤ 12 g).
  - Mass 33.2 g with polymer rear barrel (requirement ≤ 35 g).
  - Centre of mass 76 mm (requirement ≤ 70 mm).
  - PCB courtyard: 779 mm² as drawn vs 517 mm² available; 0.65 density on a 41 mm board with the package plan.
- **Failures.** Power loss in contact moves the ink ≈ 0.8 mm. A frozen Hall sensor puts the stage on its stop. Coil-short trip 8.8 µs; VMOT off 22.6 µs (ngspice).

## 3. Provisional assumptions currently carried

- **Hand.** Literature impedance (HAP-26), measured in-plane and without the hand resting on paper. γ is computed from assumed normal compliances.
- **Paper contact.** Stiffness 5×10⁴ N/m; μ 0.15; LuGre parameters assumed. Friction turned out to drive estimator performance (ρ 0.51).
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
| 4 | Actuator K_m, R, L, thermal path of a moving coil, and the winding (6 Ω binds at 3.3 V in the hot high-force corner; 4 Ω does not) | **EXP-B03** coupons wound at 4 Ω and 6 Ω (K_f, R, L, coil-to-structure R_th); **EXP-B07** thermal; bench headroom at 3.3 V with a hot coil |
| 5 | Near-nib optical sensing on paper | **EXP-S01**; sensor access under NDA |
| 6 | Packaging (DEC-014) | Decide between a 41 mm board with pouch cell and a two-board split; pouch-cell supplier drawing; HDI layout attempt |
| 7 | Datasheet checks behind the VERIFY/SELECT lines | Datasheet review, with Nordic reference circuitry for the nRF5340 |
| 8 | Centre of mass and inertia above requirements | CFRP carrier; lighter stator or shorter barrel; confirm the CoM requirement against ordinary pens (EXP-M03, H02) |
| 9 | Stage-loop phase margin 35.3° against REQ-CTRL-002's 40° (unloaded model; firmware loop test) | Identify the loaded plant (**EXP-B05**), then retune: lower position bandwidth or add phase lead, and re-run the simulation chain |
| 10 | Intent separation in the controller itself: the tracker-driven frequency gate also opens on writing (14 % of tremor-free handwriting, 68 % of the feature course) | Implement the separate spectral detector with hysteresis (DEC-009 revisit); test it in simulation, then in **EXP-E01** on recorded writing |

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
- **Dependency order after a parameter or interface change.** Parameters feed the simulator, trade, thermal and drive calculations, and the firmware generator also fingerprints the ICD and the schematic generator. Run, in order:
  1. `bash sim/run_all.sh` (if simulator inputs changed);
  2. `python3 analysis/config_trade.py && python3 analysis/thermal.py && python3 electronics/calcs/drive_sense.py`;
  3. `make -C firmware params vectors test arm`. `make test` fails if any generated input is stale.
- **Firmware and ML.**
  - Firmware: `make -C firmware test` (host, ASan/UBSan, about 15 s) and `make -C firmware qemu` (emulated Cortex-M33, about 25 min).
  - ML: `python3 -m pytest ml/tests -q`; the C export is `python3 -m ml.export_c` (see `ml/README.md`).

## 7. Pencil-class concept, AI guidance and sim-to-real (added 2026-09-27)

The request was for an Apple-Pencil-class version (Ø8.9 × 166 mm) that still corrects the ink, with AI prediction, app capture, exact forces and mechanisms, a 3D simulation and sim-to-real work. Integrating report: `docs/pencil_concept.md`. 3D replay: `viewer/` (published as a private artifact).

**What exists and ran** (all calculation or simulation):
- `config/pencil.yaml` P0.1.2.
- CAD `mechanics/cad/pencil_revP.py`, Q and L layouts: fit checks, STEP, drawings.
- Mechanism study: `analysis/pencil_mechanisms.py`, 12 candidates.
- Pencil model P1: `sim/pencil/`, 10 tests, exact match with M1 when locked.
- Page-sensor rate study.
- Touchdown-tail study.
- AI prediction, guidance and autocorrect: `aiguide/` (32 tests) and `app/penapp/autocorrect.py` (app 147 tests).
- Sim-to-real twin experiments: `s2r/`, 22 tests.
- Decisions DEC-019 to DEC-023; requirements REQ-PNC-001 to 008.

**Numbers not to lose:**
- **Forces.** The stage design load is 0.170 N per axis behind the skid, against 0.758 N with a conventional nib. It scales with the axial nib force F_c (0.15 N assumed; EXP-Q02).
- **Stage.** Four custom 2.6 × 36 × 0.67 mm piezo plates, push-pull pair per axis:
  - lever 1.363;
  - ±277 µm stroke at the design load, ±162 µm at −20 % tolerance, ±48 µm at 35°;
  - 0.329 N at the nib; 192 Hz; zero static hold power.
- **Voice coil at the 7.9 mm bore.** K_m 0.080 N/√W, so holding 0.170 N costs 2.4 W against 0.31 W allowed.
- **CAD.** 12.2 g before wiring and margin; centre of mass 88 mm from the nib; all checks pass for Q. L fails on the snubber web.
- **Battery, 90 mAh.**
  - Recording only: 4.1 h.
  - Assist with 2 × DRV2700: 0.83 h.
  - Assist with a charge-recovery driver: 2.7 h, or 3.4 h at 0.3 µm Hall noise.
- **Simulated effect, pencil model P1.**
  - Oracle ratio: 0.19–0.26 at 0.1 mm tremor; 0.20–0.46 at 0.3 mm, with 16–65 % of the time at the travel limit.
  - Kalman: 0.85–0.92, and only at 8–12 Hz.
- **Touchdown tails.** 0.87 mm per touchdown with the tilt-range front stop; 0.29 mm with a tilt-adaptive stop at 0.3 mm margin (oracle ratio 0.24 → 0.30).
- **Page sensor for guided mode.** ≥ 120 Hz at ≤ 10 ms is needed (guided/neutral 0.42), against 0.76 at 30 Hz. No fitting part was found.
- **AI.**
  - Digital autocorrect: word errors 32 % → 10 % at 7 % recognition errors; ≤ 0.1 % of correct words changed.
  - Physical guidance toward AI-predicted letters gives no net benefit: break-even is 265 µm (P1) and a correct letter in the user's style is about 300 µm off.
  - Wrong templates stay at the 0.40 mm stop; 2.2 % of letters are misread at full authority, 0.3 % gated.
  - The phone must predict two letters ahead to meet the 0.3 s lead.
- **Sim-to-real.**
  - Identification recovers parameters to ≤ 1.6 % (95th percentile) in about 1.5 h of bench time per build.
  - The calibrated twin predicts the oracle ratio within ±0.1 for 14 of 15 plants, against 4–5 uncalibrated.
  - The frozen Kalman set degrades to a median of 0.88 at 9 Hz on randomised plants.
  - The existing Monte Carlo conflates plant and controller values.

**Blockers and next actions:**
1. EXP-Q02: lowest usable nib force per ink. Every stage load scales with it.
2. EXP-Q04: custom-width plates. Stroke, strength and drop with snubbers.
3. EXP-Q05: a low-power driver for 2–2.6 µF. It decides assist time.
4. EXP-Q06/Q07: loaded 1- and 2-axis stages.
5. EXP-Q08: touchdown tails with a tilt-adaptive stop (SQUIGGLE-class trim motor from the IMU tilt).
6. EXP-H03: skid feel.
7. Page sensor at ≥ 120 Hz in the nose (EXP-S01 on a candidate).
8. EXP-A02: people's letters against personal templates, before any physical AI-guidance claim.
9. Freedom to operate: the template pipeline is close to PAT-01 claim 15; attorney review.
10. Simulator: split `core.simulate` into a plant step and a controller tick. Redo the Monte Carlo and the estimator selection under fixed firmware on randomised plants (`docs/sim_to_real.md` §8, items 12–14).

**Resume.**

```bash
python3 mechanics/cad/pencil_revP.py --variant Q
python3 analysis/pencil_mechanisms.py
python3 -m sim.pencil.run_study
python3 -m sim.pencil.diag_touchdown_tails
bash aiguide/run_all.sh
bash s2r/run_all.sh
python3 viewer/build.py
```

- The pencil model reads the CAD summary, so re-run the CAD first after any geometry change.
- `sim/pencil` and `aiguide` keep their numba caches in their own `build/` directories.
