# Validation records

This directory holds **executed** results only. **On 2026-09-27 it contains no records: no experiment has been executed.** Anything in `validation/` outside this directory is a proposed procedure, a prediction or an acceptance criterion.

The rules below apply to every bench record. That includes the electronics bring-up results, which `electronics/README.md` sends here "with the board serial". They also apply to the non-identifying summaries of human studies. Human raw data follow the same structure but live in the access-controlled store (§6).

## 1. Layout

```
validation/records/
  README.md                         this file
  instruments.csv                   instrument register (created with the first record)
  <EXP-ID>/
    <record-id>/
      record.yaml                   metadata (§3), mandatory
      MANIFEST.sha256               SHA-256 of every file, raw and derived
      raw/                          instrument and pen files exactly as produced (§4); read-only
      pen/                          ICD binary logs (*.penlog), unmodified
      scans/                        16-bit lossless TIFF and scanner profile
      analysis/                     derived data, figures, the verdict file
      notes.md                      operator log: timeline, deviations, anomalies
```

Large files are **not** committed to git (§5). The record directory in git always holds `record.yaml`, `MANIFEST.sha256`, `notes.md` and `analysis/verdict.yaml`. It also holds either the raw files or a pointer to them (§5).

## 2. Naming

- **Record id:** `<EXP-ID>_<YYYYMMDD>_<DUT>_<run-group>_<nn>`, for example `EXP-B01_20261103_RIG1-REF3_core_01`.
  - `<DUT>` names the device under test, joined with `-`: pen serial, board serial, actuator coupon id, refill lot or paper batch as relevant.
  - `<run-group>` is the block of the test matrix defined in the protocol (for example `core`, `reduced`, `recip`, `primary`, `seed07`).
  - `<nn>` counts sessions of the same group on the same day.
- **Files inside a record:** `<record-id>_<condition-code>_<rep>.<ext>`. The condition code is defined in the protocol's test matrix, for example `N1.0_T50_B090_V30`.
- **Dates and times** are ISO 8601 in UTC (`2026-11-03T14:05:22Z`). The local time zone is recorded once in `record.yaml`.
- **Participants** are pseudonymised ids only: `<study>-P<nnn>`, for example `H01-P017`. No names, initials, dates of birth or faces anywhere in this repository.

## 3. Mandatory metadata (`record.yaml`)

```yaml
record_id: EXP-B01_20261103_RIG1-REF3_core_01
experiment_id: EXP-B01
status: executed            # executed | aborted | superseded (with superseded_by)
protocol:
  file: validation/bench_protocols.md
  git_commit: <hash at which the protocol was frozen>
acceptance_criteria:
  file: validation/acceptance_criteria.csv
  git_commit: <hash>
  ids: [AC-B01-01, AC-B01-03, AC-B01-09]
prediction:                 # frozen prediction used for comparison (bench_protocols.md §0.2)
  file: <path>
  parameters_version: 0.4.1
  parameters_sha256_16: <from stabpen.provenance>
analysis_code:
  path: <script path>
  git_commit: <hash>
operators: [<initials or staff id>]
location: <lab, rig id>
start_utc: 2026-11-03T09:12:00Z
end_utc: 2026-11-03T17:40:00Z
environment: {temperature_C: 23.1, rh_pct: 48, notes: ""}
dut:
  pen_serial: null
  board_serial: RIG1-BB-003
  firmware: {git_commit: <hash>, build_id: <id>, test_build: true}
  calibration_records: {CAL_HALL: null, CAL_ACT: null, CAL_ISNS: <cal_version>, CAL_AXIAL: null}
  refill: {type: D1-oil, lot: <lot>, ids: [R07, R08, R09]}
  paper: {type: ISO12757-1-test, batch: <batch>, conditioning_h: 26}
instruments:                # ids from instruments.csv; certificate and due date checked at session start
  - {id: FT-01, model_class: "6-axis F/T, Nano17 class", cal_cert: <id>, cal_due: 2027-05-01}
check_standards:            # session check (bench_protocols.md §0.5)
  - {id: DW-0500, nominal: 0.500 N, measured: 0.498 N, within_control_limits: true}
sync: {method: "TTL 1 Hz coded", alignment_check_us: 18}
randomisation: {seed: 20261103, order_file: raw/run_order.csv}
blinding: {image_codes_file: <path to key, stored outside the analysis tree>, unblinded_utc: null}
human:                      # only for studies with participants
  study_id: null
  ethics_approval: null
  consent_version: null
  participant_ids: []
deviations: []              # each: {time_utc, description, impact, approved_by}
verdicts_file: analysis/verdict.yaml
```

`analysis/verdict.yaml` holds one entry per acceptance criterion:

- measured value;
- expanded uncertainty U (k = 2) with the budget reference;
- the decision rule applied (simple or guarded; `bench_protocols.md` §0.5);
- the verdict: `pass`, `fail` or `inconclusive`;
- the prediction it is compared with.

A record without a verdict file is incomplete, not a pass.

## 4. Raw data

- **Raw means as produced by the instrument or the pen:** vendor-native files, ICD `.penlog` binaries, scanner TIFFs, logic-analyser captures, video. Where the vendor format is proprietary, an open export (HDF5 or CSV with a JSON sidecar giving units) is stored **as well**, never instead.
- **Raw files are write-once.** They are set read-only after the session. Their SHA-256 goes into `MANIFEST.sha256` before any analysis starts. Corrections are made in `analysis/` by scripts, never by editing raw files.
- **Derived data** must be regenerable from raw data plus the analysis code at the recorded commit. The analysis writes provenance metadata in the same form as `stabpen.provenance`: git revision, parameter version and hash, command, library versions.
- **Pen logs** follow `docs/icd.md` §4 and are read with `app/penapp/logfmt.py`. Parse issues are reported, not dropped.
- **ICD gaps that affect bench records:**
  - ICD v1.1 has no event code for the rig sync pulses, so they are logged as annotation records (0x05, text `SYNC <n>`);
  - the payload layouts of 0x04 (calibration snapshot) and 0x05 (annotation) are not defined.
  Both are listed for the ICD owner in `validation/README.md`.

## 5. Storage and retention

- **In git:** metadata, manifests, notes, verdicts, small derived tables (< 1 MB per file), and figures used in reports.
- **In the project data archive** (institutional or cloud object store with versioning and access control): everything larger. The record keeps a `raw/POINTER.yaml` with the archive URI, the object versions and the SHA-256 of each object. Records are checked by recomputing the hashes (`sha256sum -c`).
- **Backups:** two copies in different locations; restoration tested once per year.
- **Retention:**
  - bench records and raw data are kept for the life of the programme and at least 10 years after the last related design decision or product release;
  - records that support a clinical investigation or a regulatory submission follow the longer of that rule and the regulatory requirement (for example EU MDR Annex XV: at least 10 years after the end of the investigation). The regulatory adviser confirms the period for the jurisdiction;
  - human raw data follow the retention period in the ethics approval and the data protection impact assessment, which may be shorter for identifying material (video, handwriting scans).
- **Superseding:** a record is never deleted. If it is wrong, `status: superseded` and `superseded_by` point to the replacement, and `notes.md` explains why.
- **Physical samples** (ink sheets, coupons, failed flexures, fracture specimens) carry labels with the record id and are stored flat, in the dark, at 23 °C / 50 % RH (paper), or in labelled bags (coupons), for the same retention period.

## 6. Human-participant data

- Raw human data (pen logs, scans of handwriting, video, questionnaires) are stored **only** in the access-controlled store approved by the ethics committee. They are never stored in this repository.
- This repository may hold aggregate, non-identifying results: summary statistics per group, and verdicts.
- The key linking participant ids to identities is held by the principal investigator, separately from the data.
- Handwriting is personal data and can identify a person. Scans are shared only under the consent options in `validation/human_study_plan.md` §3.3.
- Records of human studies list the consent version and the optional consents given (re-use, sharing, model training) per participant id. Data are used only within those consents.

## 7. Engineering record-keeping

- Dated records of design choices and their evidence (this directory, `docs/decisions.md`) also serve the freedom-to-operate review recommended in `docs/research/notes/PAT_patents.md`: "keep dated design records". Records are therefore never back-dated. Late entries carry both the event date and the entry date.
- Every result reported outside the team (report, paper, presentation) cites record ids and verdict files. A number that cannot be traced to a record is labelled as a prediction or an assumption.
