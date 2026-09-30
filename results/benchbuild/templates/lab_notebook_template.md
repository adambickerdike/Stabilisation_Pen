# Lab notebook page: [record id]

Copy this page for each session. Write in ink or in a dated file, and never back-date an entry. A late entry carries both the event date and the entry date (`validation/records/README.md` §7). Numbers carry their unit and their label: MEASURED, CALCULATION or ASSUMPTION.

## 1. Session

| Field | Entry |
|---|---|
| Record id | `EXP-…_YYYYMMDD_<DUT>_<run-group>_<nn>` |
| Experiment and criteria (AC ids) | |
| Build and rig | B0 DAQ-1 / B1 R9 / B2 coupon (which) / B3 five-bar / B4 R10 |
| Operator(s) | |
| Start and end (UTC) | |
| Protocol commit / analysis commit / firmware build | |
| Frozen prediction file and parameters version | |
| Device under test (serials, coupon ids, refill lot, paper batch, magnet lot, wire lot) | |

## 2. Before starting

| Check | Result | Initials |
|---|---|---|
| Instruments in calibration (ids from `instruments.csv`) | | |
| Safety walk-through (plan §11; checklist A) | | |
| Environment: T (°C), RH (%) | | |
| Check standard (id, nominal, reading, within limits?) | | |
| Sync check residual (µs) | | |
| Randomisation seed and order file | | |
| Blinding key location (never in the analysis tree) | | |

## 3. Set-up notes

Record the configuration here: tilt, roll, height, underlay, preload, stroke, drive frequency, current limits, channel map, gains and sample rate. Add a photo reference for each change to the set-up.

## 4. Run log

| Time (UTC) | Condition code / marker | Action or observation | File(s) written | Initials |
|---|---|---|---|---|
| | | | | |
| | | | | |

## 5. Deviations from the protocol

| Time | What differed | Why | Impact on which AC id | Approved by |
|---|---|---|---|---|
| | | | | |

## 6. Anomalies and safety events

List everything unexpected: noise, drift, a coupon broken while handling, a guard opened, a magnet chipped, a hot coil, an emergency stop, or beryllium-copper waste handled.

## 7. End of session

| Check | Result |
|---|---|
| Check standard repeated (reading, within limits?) | |
| Environment again | |
| Raw files set read-only; SHA-256 in `MANIFEST.sha256` | |
| Analysis run (script, commit) and verdict file written | |
| Physical samples labelled with the record id and stored (sheets flat, in the dark; coupons bagged) | |

## 8. Result summary (after analysis)

| AC id | Measured value | U (k = 2) | TUR | Rule (simple or guarded) | Verdict | Prediction |
|---|---|---|---|---|---|---|
| | | | | | | |

Sign-off (operator, date) and review (second person, date).
