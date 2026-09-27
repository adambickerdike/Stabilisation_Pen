# Engineering recommendation: the credible route to a slim assistive pen with useful notes

**Status: engineering judgement (proposed), 2026-09-27.** Nothing has been built or measured. Each number below is tagged **calc** (calculation), **sim** (executed simulation), **lit** (literature) or **CAD**, and cites the file it comes from. The recommendation changes if the named experiment disagrees.

Brief §20 asks four things:

- the most credible route;
- where custom hardware is unavoidable;
- which AI functions need our own data and which can use existing models;
- what evidence each user benefit needs, including the limiting calculation wherever targets conflict.

## 1. The route, in order of evidence

Build one platform, but release capabilities in the order the evidence supports them.

1. **Capture and notes, for everyone, first.** A pen that writes like a pen and keeps an immutable stroke record. Recognition uses an existing on-device recogniser; the assistant answers only from cited strokes (DEC-013, DEC-017). Build on coded paper first; ordinary-paper page capture stays a research track until EXP-S01 and EXP-C02 report.
2. **Guided assistance and practice, second.**
   - Template-following correction for tracing, drawing and rehabilitation. Where the intended path is known, the stage removes most of the tremor: path distance circle 443 → 164 µm, spiral 382 → 112 µm (**sim**, `results/sim/guided_path_distance.json`).
   - Cueing, feedback and practice modes for Parkinson's micrographia, judged by lasting unassisted improvement, not by correction (DEC-002).
3. **Free-writing tremor cancellation, last, and only if recorded writing shows it is separable** (EXP-H01 → EXP-E01).
   - The mechanism could remove 70–80 % of tremor-induced ink error: oracle bound 0.22–0.32 of the powered-neutral error (**sim**).
   - No causal estimator tested separates tremor from synthetic writing below about 9 Hz. The tuned Kalman runs at 1.03–1.14 of the neutral error there, with 55–101 µm distortion of tremor-free writing, against REQ-CTRL-005's 50 µm (**sim**, `docs/sim_report.md` §3.2).
   - Its frequency gate opens on 15 % of tremor-free handwriting and 52 % of the feature course (**sim**, `results/sim/gate_fraction.json`).

The lever-and-stage research pen (configuration B, Rev A/A.1) is **the instrument that answers these questions, not the product** (DEC-001). The product path uses configurations D or E, which carry the static contact load passively or with a slow unpowered-hold actuator (DEC-008, §3).

## 2. Targets that cannot coexist

| # | Conflict | Limiting calculation | Consequence and revised target |
|---|---|---|---|
| T1 | A Ø15 mm pen whose actuated nib carries the contact load, stays comfortable to hold, and runs ≥ 60 min (REQ-FORM-001, REQ-ACT-001/002, REQ-PWR-001) | Transverse load is N·cos θ plus friction: 0.64 N at 50° and 1 N (COR-01, **calc**). Holding power is P = (F_tip / (n·K_m))². Direct drive (n = 1, K_m 0.19 N/√W) needs ≈ 12 W. The lever (n = 3.17, K_m 0.293) needs 0.50 W in contact, against 0.412 W allowable for a moving coil (41 °C surface, 120 °C coil; the coil limit binds). 70 % of the writing envelope is within the limit in continuous contact (**calc**, `results/trade/config_trade.json`, `results/thermal/thermal.json`) | At the design point B exceeds the limit in continuous contact (0.50 vs 0.412 W) and is within it on average at 65 % pen-down duty (0.33 W, coil ≈ 97 °C). REQ-ACT-002 (≤ 0.25 W average) fails, and 30 % of the envelope exceeds the limit. B stays a research pen. Product candidates: **D** (nose skid + constant-force nib, 0.08 W in contact) and **E** (slow bias actuator carrying 80 % of the static load, 0.02 W) (**calc**) |
| T2 | 200 mAh cell and the Rev A.1 board in the same Ø15 × 150 mm body (DEC-014) | The circuit needs 779 mm² of courtyard against 517 mm² in the envelope. A 41 mm HDI board fits at 0.65 density, leaving a 32 mm bay that holds ≈ 130 mAh at the ledgered cell's energy density. Runtime at 65 % pen-down duty with 130 mAh: B ≈ 53 min, D ≈ 140 min, E ≈ 180 min (scaled from 81 / 215 / 277 min at 200 mAh) (**calc**, `results/electronics/placement_study.json`) | B fails REQ-PWR-001 (≥ 60 min) in the slim body; D and E pass with margin. This is a second, independent reason the product path is D or E |
| T3 | Cancelling tremor below ~9 Hz in free writing while preserving intended strokes (REQ-CTRL-005 ≤ 50 µm) | Intended writing puts ~17 % of velocity energy in 4–7 Hz (COR-28, **lit**/**calc**). The tuned Kalman gives 1.03–1.14 of the neutral error at 4–9 Hz, with 55–101 µm distortion (**sim**). The tuning selection flips between an inert and an active set on small plant changes (`docs/sim_report.md` §3.2). A synthetic-data TCN reaches 0.48 in distribution but 0.73 against 0.77 under realistic mismatch (**sim**, `ml/README.md`) | Frequency-gated authority (DEC-009), guided mode below the gate, and no free-writing claim before EXP-E01 on recorded writers (DEC-016) |
| T4 | A ±0.5 mm stage vs Parkinson's writing difficulty | Micrographia is a size deficit (50–63 % prevalence, PDT-01, **lit**). A stage limited to ±0.55 mm cannot enlarge letters by millimetres. Tremor while writing is uncommon in PD (3 of 10 OFF-medication, PDT-10, **lit**) | PD support is cueing (guide lines 1.0 cm apart help, PDT-18/20), size feedback and amplitude practice (7–17 % larger writing, retained, PDT-16/17), judged by claim gate C-LI |
| T5 | ±0.5 mm correction vs the tremor population | About 30 % of essential-tremor patients have ≤ 1 mm peak-to-peak spiral tremor, derived from a log-normal fit to PDT-12 (**lit**/**calc**). No study reports tremor at the nib during writing | REQ-USR-002 limits active-correction claims to writers measured ≤ 1 mm p-p at the nib. EXP-H01 measures the addressable share |
| T6 | Ordinary paper and page-registered capture | IMU-only position is unobservable (17–35 % character error for IMU-only recognition). Relative optical flow drifts (DeltaPen idle drift ≈ 2.6 mm/min). Every capture pen with verified specifications reads coded paper (OPT-01…19, **lit**) | Coded paper for the research builds (REQ-CAP-003). On ordinary paper the working hypothesis is word-level stroke capture, with page structure from page events. Drift within a word is ≈ 0.09 mm (2.6 mm/min over a ~2 s word, **calc**). It is **untested**: AC-C01-04 gates any ordinary-paper claim |
| T7 | Slim form, centre of mass ≤ 70 mm and tip inertia ≤ 12 g (REQ-FORM-004, REQ-MECH-003) | Rev A.1: 33.2 g (meets ≤ 35 g), centre of mass 76 mm, tip-equivalent inertia 13.7 g (**CAD**, `results/mechanics/mass_budget.json`) | A CFRP carrier brings inertia to ≈ 9.5 g (**calc**). The centre-of-mass requirement should be checked against ordinary pens (EXP-M03, H02) before the design is bent to meet it |

## 3. Recommended configuration and its trade-offs

**Research pen (now): Rev A.1, configuration B.** It is the one configuration that can measure everything the product decisions need:

- loaded cancellation (EXP-B09);
- ink tolerance to force modulation (EXP-B08);
- tremor at the nib, in its passive sensing form (EXP-H01);
- the guided mode.

A tethered supply removes the runtime limit (T2). The thermal governor and time-limited sessions keep it inside the thermal limit at high loads (T1).

**Product candidate (after EXP-H03): configuration D on the same actuator, with E as the fallback.** D comes first because it adds no actuator and may reduce tremor passively; E has the lower power but adds a second, life-limited actuator.

| | D: nose skid + constant-force nib | E: slow unpowered-hold bias actuator |
|---|---|---|
| Copper loss in contact / average while writing | 0.08 W / 0.05 W | 0.02 W / 0.01 W (**calc**) |
| Runtime with ≈ 130 mAh (DEC-014 option a) | ≈ 140 min | ≈ 180 min (**calc**) |
| What it costs | The skid touches the paper: writing feel, smear and paper marking risk. May passively reduce tremor at the nib by friction (research question rank 7, AC-H03-03, hypothesis) | A second actuator. The catalogue unpowered-hold part in the ledger is too slow for tremor but fast enough for a bias. Its life of about 300 k cycles is the risk, and it is OEM-only (AMF-15, **lit**). Its feasibility test for G-D is not yet specified |
| Decided by | EXP-H03 skid feel and smear study | A bias-actuator feasibility test (validation/README.md §7) |

Both keep the Rev A.1 stage, actuator, sensing and firmware, so research-pen measurements carry over.

## 4. Where custom hardware is unavoidable

| Item | Why it must be custom | What closes it |
|---|---|---|
| Two-axis stage actuator around the refill | The best catalogue VCM in the bore has K_m ≈ 0.83 N/√W (AMF-02, **lit**/**calc**), but it is single-axis and solid-cored: two of them do not fit around a refill in a Ø15 mm barrel. Through a 3:1 lever such a part reflects about 49 g at the tip, against REQ-MECH-003's 12 g (AMF note §2.1, **calc**). Hence the annular moving-coil sandwich: K_m 0.293 N/√W (field model 0.24–0.34), tip inertia 13.7 g (**calc**, **CAD**). Its winding is not settled: at 3.3 V a 6 Ω coil cannot hold the hot high-force corner (0.5 % of the thermal envelope) and 4 Ω can, so EXP-B03 winds both (DEC-012). Piezo parts hold at zero power but lack the work: about 0.5 mN·m available in the bore against ≥ 3.2 mN·m needed (AMF note, **calc**) | EXP-B03 coupons (K_f, R, L, gap), EXP-B07 thermal; quotations for coils, quadrant magnet rings and back iron (`docs/plan.md` §4) |
| Pivot and axial flexures | 0.05 mm BeCu cross-strip gimbal and 0.22 mm spiral diaphragm sized to this lever (177/82 MPa, buckling margin 19; **calc**, `results/mechanics/flexure_calc.json`) | Etched-part quotation; EXP-M02 fatigue coupons |
| Near-nib optical sensing | The sensor must see paper beside a moving nib at 35–75° tilt. The candidate die is under NDA, and mouse-class optics need 2.4 ± 0.2 mm working distance (OPT-04…06, **lit**) | EXP-S01 latency, noise and dropout on paper; sensor access |
| Carrier tube, HDI board and cell | Titanium or CFRP carrier. 6–8-layer via-in-pad board for the aQFN94 MCU at 0.65 density. A 5 × 12 × 32 mm-class ≥ 5 C pouch cell with a supplier drawing and IEC 62133 report | DEC-014 layout attempt; supplier drawings |
| Stage-A bench rig | About 35 custom parts around catalogue instruments (F/T sensor, XY stage, laser heads, 12.7 mm VCMs, which suit the rig because it has no size limit) | `mechanics/cad/bench_rig.py`; instrument quotations |

**Catalogue parts suffice** for:

- the MCU (nRF5340), bridge drivers (DRV8212P), current-sense amplifiers (INA241A1), 3-axis Hall sensor (TMAG5170), IMU, charger and load switch (`electronics/bom_revA.csv`, with 45 VERIFY and 3 SELECT lines outstanding);
- the ink: a standard D1 mini refill (DEC-004).

## 5. Which AI functions need our own data

| Function | Our own data needed? | Why | Starting point | Evidence gate |
|---|---|---|---|---|
| Learned tremor/intent predictor for free-writing correction | **Yes**, recorded writing with tremor at the nib, from the target groups | No study in the evidence ledger reports tremor at the nib during writing (research synthesis, gap 1), let alone housing and nib motion together. Synthetic-data advantage vanishes under realistic mismatch (0.73 vs 0.77) (**sim**) | Pipeline, int8 export and MCU budget ready: 16.2 k MAC, 7.3 kB weights, bit-exact C, no f_est input (`ml/`) | REQ-ML-001 on held-out writers (EXP-E01, DEC-016) |
| Per-user calibration (tremor frequency, gate, authority cap, γ, refill re-zero) | The user's own session data, on-device | Estimation and identification, not model training | Firmware calibration module (`firmware/core/calib.c`) | AC-E01-06 (gate from a 60 s calibration within 1 Hz of optimal); AC-B09-13 (γ identification) |
| Hand-path reconstruction for honest capture | Our sensor calibration, not training data | Deterministic fusion: ink minus stage offset. Needs the nib-offset and uncertainty fields of ICD format v2 | `app/` capture-fidelity analysis | AC-S02-06, AC-C02-08 |
| Handwriting recognition | **No** for the first builds | The common datasets are non-commercial or unverified (COR-22) | Existing on-device recogniser behind an interface (DEC-013) | EXP-C01 character/word error on writer-disjoint data; custom training only with licensed or consented data |
| Search | No | Full-text search is not ML | SQLite FTS5 with stroke citations (`app/`) | EXP-C01 search part |
| Note summaries and questions | No training; existing language models | Must be grounded: every answer cites strokes, and unsupported, uncited or clinical answers are refused | Grounded assistant with refusal rules (`app/`) | EXP-A01 grounding audit (attribution, citation precision and recall, faithfulness vs recognition error) |
| Guided-mode template matching | No, initially | Deterministic registration to a known template | Firmware guided mode; simulator mode 6 | AC-B09-11/12 |
| Diagnosis or disease scoring | **Not offered** | Outside the claims (DEC-002, REQ-USR-003) | — | — |

## 6. Evidence each user benefit needs

Claim gates C-IA, C-LI and C-CAP are defined in `validation/prototype_stages.md`. Immediate assistance and lasting improvement are measured separately (`validation/human_study_plan.md` §1).

| Benefit | Users | Decisive evidence | What the current evidence predicts |
|---|---|---|---|
| Writes like an ordinary pen | Everyone | EXP-H02 form and writing feel; EXP-H05 perception thresholds | Device distortion ≈ 59 µm RMS vs a rigid pen (**sim**). Vibrotactile threshold in a pen grip is 26 µm at 10 Hz (HAP-27, **lit**), so perceptibility is plausible and must be measured |
| Guided tracing and drawing (immediate) | Tremor, rehabilitation, art | AC-B09-12 on the bench, then the guided variant of the crossover, EXP-H06-G (claim gate C-IA) | Path distance ratio 0.37 (circle) and 0.29 (spiral) (**sim**) |
| Free-writing tremor reduction (immediate) | Action/essential tremor ≤ 1 mm p-p at the nib | EXP-H01 → EXP-E01 → EXP-B09 → EXP-H06 crossover (C-IA) | Benefit only above ~9 Hz on synthetic writing (0.78 / 0.71 at 9 / 10 Hz, 0.3 mm), harm below it (**sim**) |
| Larger, steadier unassisted writing (lasting) | Parkinson's micrographia; novice learners | EXP-H04 training with retention and transfer (C-LI) | Amplitude training: 7–17 % larger writing, retained (PDT-16/17, **lit**). Error-minimising guidance gave the worst unassisted retention (HAP-09, **lit**), so practice modes fade guidance |
| Faithful capture, recognition and search | Everyone | EXP-S01, S02, C01, C02 (C-CAP); AC-C01-04 for ordinary paper | Format and resampling error measured on simulated traces only (`results/app/`) |
| Trustworthy note assistance | Everyone | EXP-A01 grounding audit (C-CAP) | Refusal and citation rules tested on synthetic notes (137 app tests) |

## 7. What would change this recommendation

| If this happens | Then |
|---|---|
| EXP-B01 finds a transverse load well below N·cos θ | Revisit T1: configuration B might become a product candidate |
| EXP-H01/E01 shows real writing is separable below 9 Hz (REQ-ML-001 met) | Free-writing cancellation moves ahead of guided mode, with the learned predictor behind `ml_guard` |
| EXP-H03 rejects the skid | E becomes the product path, subject to its feasibility test |
| EXP-S01 fails on paper at the nib | DEC-005 is revised: external reference or coded paper for correction; capture continues on coded paper |
| EXP-H01 finds most target writers above 1 mm p-p at the nib | The stage travel requirement is revisited against T1's power law. Power scales with the square of force, not travel, but travel costs inertia and packaging |

## 8. Next actions

These are the same three actions as `CHECKPOINT.md` §5. They share no hardware, so they run in parallel.

1. Build the stage-A rig and run EXP-B01/B02 (transverse load and friction on real paper and ink).
2. Submit the ethics application for EXP-H01 and build the passive instrumented pen.
3. Secure near-nib optical sensor access for EXP-S01.
