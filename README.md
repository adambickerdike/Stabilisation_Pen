# Active stabilisation pen: engineering programme

A compact pen that actively moves its nib to counter unwanted hand motion, supports people with Parkinson's-related writing difficulty, assists everyday handwriting and drawing, and captures notes with source-grounded AI assistance.

This repository holds the research and development package: the audit of the source report, evidence, requirements, physics, simulation, mechanics, electronics, firmware, ML, app, validation plans and decisions.

**Evidence status.** Everything here is **calculation, simulation, literature or proposed design**. Nothing has been built, and there are **no physical or human measurements**. Every figure carries a stamp saying what it is, and every result file records its code revision, parameter version, seeds and command.

## Start here

| If you want… | Read |
|---|---|
| The verdict on the source report | [`docs/audit.md`](docs/audit.md), [`docs/corrections.csv`](docs/corrections.csv) |
| Current state, blockers and next actions | [`CHECKPOINT.md`](CHECKPOINT.md) |
| The system and its budgets | [`docs/architecture.md`](docs/architecture.md), [`docs/icd.md`](docs/icd.md) |
| Why things are the way they are | [`docs/decisions.md`](docs/decisions.md) (DEC-001…018) |
| What the simulations say | [`docs/sim_report.md`](docs/sim_report.md) |
| What may be claimed for each feature | [`docs/features.md`](docs/features.md) |
| The riskiest open questions | [`docs/research_questions.md`](docs/research_questions.md) |
| How to proceed | [`docs/plan.md`](docs/plan.md), [`validation/`](validation/README.md) |

## Key conclusions so far

1. **The transverse load is dominated by N·cos θ, not friction** (COR-01). Holding power (F/(n·K_m))² therefore rules out direct drive at the tip (about 12 W). A front-pivot lever with a rear annular actuator brings it to about 0.5 W at the design point. That is still **at the moving-coil thermal limit**. Skid and bias-actuator variants remain the product path (DEC-003, DEC-008).
2. **Intent separation, not mechanics or latency, limits free-writing assistance.**
   - In simulation, the mechanism could remove 70–80 % of tremor-induced ink error (oracle bound 0.22–0.32).
   - The causal estimators tested give no benefit below ~9 Hz on synthetic handwriting.
   - Guided (template) tasks work in simulation: circle 442 → 165 µm, spiral 382 → 111 µm.
   - Whether real handwriting is more separable is the decisive open question (EXP-H01 → E01).
3. **Parkinson's writing difficulty is mainly micrographia.** A ±0.5 mm stage cannot enlarge letters. PD support means cueing, feedback and practice, measured for lasting unassisted benefit, not immediate correction (DEC-002).
4. **Design errors found and fixed in this package** (calculation and simulation):
   - Nib-bounce instability from a measured-force contact feedforward (DEC-011).
   - Voltage-limited 11 Ω coil, rewound to 6 Ω (DEC-012).
   - An axial suspension layout that closes the actuator gap: the refill now slides in the carrier (DEC-007 rev.).
   - A nose that touched the paper at every writing angle: the refill point now protrudes 5 mm (DEC-018).
   - Inertia understated by a point-mass approximation: 13.7 g, above the 12 g requirement.
   - The research circuit does not fit the 29 mm board in the CAD envelope. The package plan and a 41 mm board fit at 0.65 density (DEC-014, open).

## Completion table

States: **drafted** (text or design, not run) · **executable** (code runs, results depend on unverified inputs) · **executed** (run here; outputs in `results/`) · **hardware pending** · **measured** (none yet).

| Brief area | Deliverable | State | Evidence |
|---|---|---|---|
| 1 Research | Audit and recalculation of the report (37/37 numbers reproduce; 28 corrections) | executed | `analysis/audit_recalc.py` → `results/audit/` |
| 1 Research | Evidence ledger (246 sources, 8 streams) and synthesis | drafted | `docs/evidence.csv`, `docs/research_synthesis.md` |
| 1 Research | Ranked research questions with decisive experiments | drafted | `docs/research_questions.md` |
| 2 Mechanics | Parametric CAD (Rev A, Rev A.1) with interference checks, STEP, drawings | executed | `mechanics/cad/`, `results/cad/` |
| 2 Mechanics | Flexures, tolerance stacks (S1–S6), mass/CoM budget, configuration trade | executed | `mechanics/`, `results/mechanics/`, `results/trade/` |
| 2 Mechanics | Stage-A loaded bench rig (dimensioned concept CAD) | executed (design) · hardware pending | `mechanics/cad/bench_rig.py`, `results/cad/drawing_bench_rig.png` |
| 3 Electronics | KiCad 8 schematic: 11 sheets; ERC 0 errors; netlist cross-check pass; PDF; BOM with VERIFY/SELECT | executed | `electronics/kicad/`, `electronics/bom_revA.csv` |
| 3 Electronics | Drive/sense calculations; ngspice drive stage incl. fault; placement study | executed | `electronics/calcs/`, `electronics/spice/`, `results/electronics/` |
| 3 Electronics | PCB layout and fabrication outputs | **not started** (blocked by DEC-014) | `electronics/README.md` E-1 |
| 4 Simulation | Coupled pen–hand–paper model M1: 12 verification tests; tuning/test split; grid, Monte Carlo, sensitivity, failures, design sweeps | executed | `sim/`, `results/sim/`, `docs/sim_report.md` |
| 4 Simulation | EM field models, thermal network | executed | `analysis/`, `results/em/`, `results/thermal/` |
| 4 Simulation | Validation plan per model | drafted | `docs/physics.md` (table), `validation/` |
| 5 ML | Synthetic data pipeline with writer-disjoint splits; six conventional baselines tuned on validation; causal TCN; int8 quantisation (no loss); C export bit-exact with the Python reference, also on emulated Cortex-M33; MCU budget (16.7 k MAC, 7.3 kB weights); model and dataset cards; 15 tests | executed (synthetic only) · real data pending (EXP-H01) | `ml/README.md`, `results/ml/` |
| 6 Firmware | Control core, safety, logging, host tests, ARM build | see `firmware/README.md` | `firmware/`, `results/firmware/` |
| 6 Product | ICD log reader/writer with CRC and resync (parses the firmware's golden log with zero issues); immutable content-addressed note store with provenance-carrying derived layers; segmentation; SVG rendering; recogniser interface (on-device adapter specified); FTS5 search with stroke citations; grounded assistant that refuses unsupported, uncited or clinical answers; capture-fidelity analysis; 136 tests | executed (synthetic data) · real recogniser pending | `app/README.md`, `results/app/` |
| 7 Validation | 29 experiments (23 bench/offline, 6 human) with procedures, equipment, uncertainty and decision rules; 221 acceptance criteria (77 requirement, 35 derived, 109 hypothesis; checker passes); prototype stages A–D with gates; human study plan separating immediate assistance from lasting improvement; review of 33 document inconsistencies, now resolved or recorded | drafted · hardware and participants pending | `validation/README.md` |
| — | Interfaces, decisions, plan, environment | drafted | `docs/icd.md`, `docs/decisions.md`, `docs/plan.md`, `ENVIRONMENT.md` |

## Reproduce

Environment: [`ENVIRONMENT.md`](ENVIRONMENT.md) (Python 3.11 with `requirements.txt`; KiCad 8.0.9; ngspice 42; arm-none-eabi-gcc 13.2; QEMU 8.2).

```bash
python3 -m pip install -r requirements.txt
python3 analysis/audit_recalc.py                    # report recalculation
python3 -m pytest sim/tests -q                      # simulator verification
bash sim/run_all.sh                                 # simulation evidence chain (10-25 min)
python3 mechanics/cad/pen_revA.py --variant A1      # CAD, mass, interference
python3 mechanics/tolerance_analysis.py && python3 mechanics/mass_budget.py
python3 electronics/gen/design_revA.py              # schematic; then kicad-cli ERC/netlist (electronics/README.md)
python3 electronics/calcs/drive_sense.py
(cd electronics/spice && ngspice -b drive_stage.cir && python3 plot_drive_stage.py)
```

Firmware, ML and app have their own build and test commands in their READMEs.

## Repository map

`config/parameters.yaml` holds every parameter with unit, range, status and source (v0.4.1). The directories:

| Directory | Contents |
|---|---|
| `stabpen/` | Shared physics |
| `analysis/` | Audit, EM, thermal, trade |
| `sim/` | Coupled simulator |
| `mechanics/` | CAD, flexures, tolerances, mass |
| `electronics/` | Schematic, calculations, SPICE, BOM |
| `firmware/` | Embedded control core |
| `ml/`, `data/` | Learned predictor pipeline, schemas |
| `app/` | Companion software |
| `validation/` | Experiments and studies |
| `docs/` | Everything written |
| `results/` | Generated outputs with provenance |
