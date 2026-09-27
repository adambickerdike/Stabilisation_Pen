# Audit of "AI assisted pen development — technical feasibility and engineering roadmap" (26 Sep 2026)

**Scope.** Full text, all 19 tables, all 12 equations (OMML objects extracted separately because plain text extraction drops them), all 7 figures and the 39 references of the supplied report. The two uploaded `.docx` files are byte-identical (MD5 `5fee9382…`).
**Method.** (1) Independent recalculation of every worked number under the report's own assumptions (`analysis/audit_recalc.py`); (2) physics re-derivation from explicit frames (`stabpen/frames.py`, `stabpen/contact.py`, `docs/physics.md`); (3) literature and datasheet checks through eight research streams (`docs/evidence.csv`), with the two most decision-driving numbers re-verified by me against the primary sources; (4) coupled simulation (`sim/`), field modelling (`analysis/em_*.py`), CAD (`mechanics/cad/`) and flexure analysis (`mechanics/flexure_calc.py`).
**Machine-readable register:** [`docs/corrections.csv`](corrections.csv) (28 entries with evidence, status and design consequence).

## Verdict

The report is careful in tone. It separates targets from demonstrations, flags uncertainty, and most of its qualitative warnings are correct: tilt coupling, delay, intent ambiguity, capture vs correction, and learning vs assistance. **All 37 of its worked numbers reproduce exactly under its stated assumptions** (`results/audit/audit_checks.csv`).

Its engineering conclusions do not survive the physics, though. Four findings change the architecture:

1. **The actuator load is dominated by a term the report omitted (COR-01).** A laterally actuated nib must carry the transverse component of the *whole* paper reaction. That includes the normal force N·cos θ, which is quasi-static and 1.5–4× larger than the friction term the report used. At the report's own N = 0.75 N and μ = 0.2, the mean load is 0.62 / 0.44 / 0.22 N at 35° / 55° / 75°, against the report's 0.15 N.
2. **Direct drive near the tip is therefore infeasible (COR-02).** Holding power scales as (F/K_m)² regardless of wire gauge, and a front direct-drive module that fits reaches only K_m ≈ 0.19 N/√W (field model). That gives about 12 W at the design point.
   - A front-pivot lever with a rear annular actuator (Rev A) brings this to about 0.5 W.
   - Carrying the user's force on a nose skid, or a slow zero-hold-power bias actuator, brings it to 0.02–0.07 W.
3. **The report's paper-plane Jacobian is a special case (COR-04).** Its 1/sin θ gain assumes the pen's suspension absorbs all tilt-coupled axial motion. The general gain is sin θ + γ cos²θ / sin θ, where γ is set by the suspension-to-hand compliance ratio. A controller using the textbook Jacobian under-corrected tilt-direction tremor by about 35 % in simulation.
4. **Intent separation, not mechanics, limits benefit in free writing (COR-11).** In simulation on synthetic handwriting (parameters v0.4.4, 12 test seeds, 3 amplitudes), no causal estimator helped below about 9 Hz: the tuned Kalman stays at 1.03–1.14 of the powered-neutral error at 4–9 Hz, and band-pass cancellation is harmful below 8 Hz. That compares with a mechanical (oracle) bound of 0.22–0.32 across 4–12 Hz (0.18–0.23 at the nominal 0.3 mm case; Monte Carlo median 0.45 over the declared parameter ranges). A learned predictor trained on synthetic data reached 0.48 in distribution but about 0.73 on simulator housing motion (open loop). Current numbers: `docs/sim_report.md` §3.2 and `ml/README.md`.

Two further findings narrow the clinical scope:

- **Addressable population (COR-10).** About 30 % (15–50 %) of essential-tremor patients have spiral tremor small enough for ±0.5 mm. Parkinson's writing problems are mainly micrographia, which local correction cannot address.
- **Learning (COR-20).** Error-removing assistance can impair unassisted retention.

## What the report got right (retain)

- Its contact-dominated sizing argument ("design sized only from acceleration could be wrong by two orders of magnitude"). The magnitude is actually larger than it showed.
- Separating local correction from page capture, and the warning that IMU-only capture is impossible (COR-08 strengthens it).
- The travel-limit argument that a ±0.5 mm stage cannot enlarge strokes: micrographia needs cueing and practice.
- The delay formula, as an idealised bound (COR-07 extends it).
- Keeping the fast loop local and treating language models as note tools only.
- The immutable-original-stroke data model and the separation of derived layers.
- Its evidence and regulatory caution: claims determine obligations; the pen is not a diagnostic device.

## Corrections by severity

| Severity | IDs | Theme |
|---|---|---|
| Critical | COR-01, COR-02, COR-11 | Omitted normal-load term; infeasible direct-drive power; free-writing intent separation |
| Major | COR-04, 05, 06, 07, 10, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24 | Jacobian with compliance; axial suspension; inertia; servo delay; addressable users; current sensing; MCU ADC/PWM; cell current; optics; packaging; flexures; power-loss direction; learning; edge AI; dataset licences; gate definition; hand impedance |
| Minor | COR-03, 08, 09, 15, 25 | Page- vs transverse-referenced travel; IMU example; sample size; bench actuator choice; reference details |
| Major (late research streams) | COR-26, COR-27, COR-28 | Writing-force, tilt and friction envelope; patent claim scope; measured intended-motion spectrum |

## Recalculation summary (report assumptions, `results/audit/audit_checks.csv`)

| Report quantity | Report | Recomputed | Note |
|---|---|---|---|
| Axial accommodation, 0.5 mm transverse at 35° | 0.71 mm | 0.714 mm | page-referenced value is 0.41 mm (COR-03) |
| Peak velocity / acceleration, 0.5 mm at 8 Hz | 25.1 mm/s, 1.26 m/s² | 25.13, 1.263 | ✓ |
| Force sum | 176 mN | 176.3 mN | physics incomplete (COR-01) |
| Stage mode, 50 N/m and 1 g | 35.6 Hz | 35.59 Hz | mass optimistic (COR-06) |
| Delay residual at 8 Hz: 5 / 10 / 20 ms | 0.25 / 0.50 / 0.96 | 0.251 / 0.497 / 0.964 | idealised (COR-07) |
| Runtime at 80 / 180 / 300 mA | 105 / 34 / 14 min | 105.3 / 34.5 / 13.8 | force constant unspecified (COR-02) |
| IMU 1 mg over 1 s | 4.9 mm | 4.903 mm | understated (COR-08) |
| Storage per hour at 200 Hz × 24 B | 17.28 MB | 17.28 MB | ✓ |
| Paired n (σ = 2δ) | ≈ 32 | 31.4 (normal); 34 (t-test) | COR-09 |

## Consequences carried into the design package

- The requirements register (`docs/requirements.csv`) replaces force, travel, runtime and user-group targets with page-referenced, load-aware and population-bounded versions.
- The decision log (`docs/decisions.md`) records:
  - DEC-003: front-pivot lever;
  - DEC-006: stiff axial path with force sensing;
  - DEC-007: cross-strip gimbal and suspension behind the pivot;
  - DEC-008: skid and bias variants as product candidates;
  - DEC-009: frequency-gated authority;
  - DEC-010: MCU choice.
- New decisive experiments, listed in `validation/bench_protocols.md`:
  - EXP-B01: refill drag and normal-reaction map;
  - EXP-B06: hand normal compliance and γ;
  - EXP-B08: tolerance of ink to pressure modulation;
  - EXP-H01: tremor amplitude census at the nib;
  - EXP-H03: skid writing-feel acceptance.

## Limits of this audit

- The physics corrections are analytical and simulated. None is a physical measurement.
- The simulation relies on:
  - a synthetic handwriting model (sigma-lognormal strokes);
  - a literature hand model measured in-plane and without the hand resting on paper;
  - an unidentified contact model.

  The quantitative estimator findings may shift once the handwriting spectrum and the tremor-at-nib distribution are measured. The qualitative separability limit will not.
- Datasheet values are manufacturer statements; part availability and revisions must be rechecked before ordering.
- Patent observations (COR-27) are not legal opinions; statuses are as displayed on Google Patents.
