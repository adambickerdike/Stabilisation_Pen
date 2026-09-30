# penapp: companion-app reference implementation (research pen Rev A)

**Status.** Reference implementation, version 0.1.0, against ICD section 4 (`docs/icd.md`, `format_version` 1). ICD v1.1 changed only section 5 (the ML contract); section 4 is unchanged from v1.0, and "ICD 1.0" in stored objects refers to that format.
**Evidence status.** Every dataset used or produced here is **synthetic**. The sources are glyph handwriting of known text and coupled-simulator traces (`results/sim/nominal/traces_*.npz`). No person was recorded and nothing was measured. The assistant is not a medical device.

The app implements the two principles the audit retained from the source report (`docs/audit.md`):

- local correction is kept separate from page capture;
- the immutable original strokes are kept separate from derived layers, and language models serve only as note tools.

## Quick start

```bash
# from the repository root; Python 3.11, numpy, jsonschema (+ scipy for synthesis; numba optional, faster)
python3 app/demo.py                    # full synthetic demo -> data/samples/, results/app/ (~30 s)
python3 -m pytest app/tests -q         # 137 tests (see "Tests")

export PYTHONPATH=app PENAPP_STORE=/tmp/penstore
python3 -m penapp import data/samples/demo_text_errands.penlog     # uses <log>.truth.json if present
python3 -m penapp search library
python3 -m penapp ask "When should I return the library books?"
python3 -m penapp render <note_id> -o note.svg --overlay text --force-width
python3 -m penapp fidelity             # -> results/app/capture_fidelity.json
python3 -m penapp list | verify | edit <note_id> <span_id> "<text>"
```

No code path in the tests, the demo or the CLI makes a network call.

## Review and accept spelling suggestions

The 30 September engineering update adds an explicit proposal/acceptance path.
Supply a local UTF-8 training corpus, one sentence per line, then inspect the
offered span IDs and before/after text in the JSON output:

```bash
export PYTHONPATH=app PENAPP_STORE=/tmp/penstore
python3 -m penapp propose-corrections <note_id> --corpus sentences.txt --out proposal.json
python3 -m penapp accept-corrections proposal.json --span-id <offered_span_id>
```

Repeat `--span-id` for additional choices. Generating a proposal leaves the note
unchanged and refuses to overwrite an existing proposal file. Acceptance records
only selected changes as `user_edit` and refreshes search. The captured ink and
literal recognition remain intact. Changed note text or a tampered proposal
invalidates acceptance; generate and review a fresh proposal instead. Existing
user-edited spans are protected. This workflow changes digital text; physical
future-stroke execution uses the separate `ai3.accepted_completion` planner.

The CLI uses a local word/character ngram research model and makes no corpus
download. Its scores are not calibrated probabilities of writer intention or
validated dyslexia outcomes. Known words are protected by default; the explicit
`--allow-known-word-changes` option enables that additional research behavior.
`--personal-word` adds vocabulary and can be repeated. The proposal records the
corpus hash, assumed recognition-error rate and score threshold. The historical
`autocorrect_note` evaluation API remains available for reproducing older studies;
new interactive work should use proposal and explicit acceptance.

Training text is normalized through the existing lowercase ASCII corpus
normalizer (including accent folding and punctuation mappings); the proposal
records both raw and normalized corpus hashes. This does not establish
multilingual support. Note tokens outside the model alphabet are kept exactly
as written. Keep the proposal JSON for the model/corpus audit trail: the accepted
note layer records the user edit, while training provenance remains in that
proposal. Its digest detects changed local proposal content, not authenticated
approval by a remote service or another person.

## Architecture

```
 pen (firmware)                               app (this package, local-first)
 ------------------                           -------------------------------------------------------
 2 kHz research frames 0x01 --USB--+
 200 Hz stroke samples 0x02 --BLE--+--> logfmt.read_log  CRC-16 per record, resync, time unwrap
 events 0x03, cal 0x04, notes 0x05-+          |
                                              v
                                   notes.NoteStore (directory of JSON, schema-validated)
                                     originals/<sha256>.json  immutable ORIGINAL layer (0444)
                                     notes/<note_id>.json     session manifest (header, events, parse report)
                                     layers/<layer_id>.json   DERIVED layers, append-only (0444)
                                       segmentation        capture.py   pen-down/up strokes, lines, words
                                       hand_path_estimate  capture.py   p_H from research frames
                                       recognition         recognize.py null | ground truth | inject errors | ML Kit spec
                                       user_edit           notes.py     corrections, keep stroke links
                                       ai_summary          grounded.py  cited answers only
                                              |
                  render.py (SVG) <-----------+-----------> search.py (SQLite FTS5, rebuildable cache)
                                                                  |
                                                     grounded.py retrieval -> LLMClient -> validator
```

| Module | Role |
|---|---|
| `logfmt.py` | ICD section 4 writer and reader. It handles the header, records, CRC-16/CCITT-FALSE, the fixed payloads 0x01, 0x02 and 0x03, the firmware-proposed payloads 0x04 and 0x05, byte-wise resynchronisation and timestamp unwrapping. |
| `notes.py` | Note store: content-addressed original layer, derived layers with provenance, schema validation, integrity checks, user edits, export bundle and erasure. |
| `capture.py` | Stroke table (pen-down/up), line and word grouping, hand-path layer, resampling, exact discrete Fréchet distance and the capture-fidelity analysis. |
| `render.py` | Deterministic SVG. Options: force-to-width, overlays of any derived layer, highlighting of cited strokes. |
| `recognize.py` | `Recognizer` protocol, null / ground-truth / error-injection implementations, CER/WER, and the ML Kit adapter specification. |
| `search.py` | FTS5 index over the effective text. Each hit gives matched words with stroke-id ranges and page boxes. |
| `grounded.py` | Retrieval, the `LLMClient` protocol, a deterministic local extractive default, per-sentence citation validation, refusals and storage as `ai_summary`. |
| `synth.py`, `vectors.py` | Synthetic sessions (glyph polylines timed with `stabpen.signals.PathBuilder` and `stabpen.signals.tremor`; simulator traces) and the ICD example vector. |
| `cli.py`, `__main__.py` | `python -m penapp import|render|search|ask|fidelity|list|verify|edit`. |

## Data model

### Original layer (ICD section 4.5)

- **Content.** The stroke samples (0x02) exactly as logged. In JSON this is `columns = [t_ms, stroke_id, x_um, y_um, force_mN, theta_raw, phi_raw]` with one integer row per sample, in raw logged units.
- **Address.** `sha256` over the concatenated 20-byte ICD 0x02 payloads (little-endian) in log order. This is the exact byte string in the log, so anyone can recompute it from the `.penlog` file. The test `test_content_address_is_sha256_of_logged_payloads` does so independently.
- **Immutability, enforced at every level:**
  - `OriginalLayer` raises `ImmutableOriginalError` on any attribute assignment or deletion.
  - Its sample array is a read-only numpy view of an immutable `bytes` object. numpy raises on writes and refuses to re-enable writing.
  - The store has no update path. `update_original` and `delete_original` exist only to raise.
  - Files are created exclusively (atomic hard link) and made read-only.
  - Every load re-encodes the rows and rechecks the hash; any mismatch raises `IntegrityError`. `verify()` rechecks everything.
  - A modified copy of the samples is simply a *different* original, with a different address.

### Note manifest

- One per logged session. `note_id = "note-" + sha256(device_id:session_id:original_sha256)[:16]`, so re-importing a log is idempotent.
- Contents:
  - the header, with u64 ids stored as decimal strings;
  - all events, with unwrapped 64-bit `t_us`;
  - annotations;
  - the source file SHA-256;
  - the full parse report (record counts, CRC failures, bytes skipped, wrap handling, stroke plausibility checks);
  - labels (for example `synthetic`, set automatically from a `SYNTHETIC...` annotation).
- It is write-once and protected by a digest.

### Derived layers

All derived layers are append-only and write-once. Each carries the ICD fields:

- `layer_id`, which is `<kind>-` plus 16 hex digits of SHA-256 over {kind, note_ids, created_by, inputs, params, payload}. Recomputing the same thing therefore gives the same id, and it is stored once.
- `kind`.
- `created_by`: `<algorithm>@<version>`, or `user`.
- `inputs`: a list of `{type: original, sha256, stroke_ranges}`, `{type: layer, layer_id, span_ids}`, `{type: source_file, sha256, record_type, fields}` or `{type: external_file, sha256, role}`.
- `created_utc`.
- `params`, `payload` and a `digest`.

On write the store checks:

- every stroke range against the original, so links cannot point at strokes that do not exist;
- that every text span links to at least one stroke;
- that `user_edit` keeps the edited span's stroke links and is `created_by: user`;
- that every `ai_summary` sentence has at least one citation pointing to `recognition` or `user_edit` spans;
- that assistant output can never become an input to note-content layers.

| kind | payload (schema `$defs/payload_<kind>`) | producer |
|---|---|---|
| `segmentation` | stroke table (index range, times, bbox, length, flags `short`, `single_sample`, `dropout`, `non_contiguous`, `no_pen_*_event`) + line/word spans as stroke ranges | `capture.add_segmentation_layer` |
| `hand_path_estimate` | per stroke: housing path p_H at the stroke-sample times, with the origin alignment used | `capture.add_hand_path_layer` (needs 0x01 frames) |
| `recognition` | line and word spans with `text`, `stroke_ranges`, `bbox_um`, `confidence` | `recognize.run_recognizer` |
| `user_edit` | `target_layer`, edits {span_id, text, previous_text, stroke_ranges} | `NoteStore.add_user_edit` |
| `ai_summary` | question, cited sentences, sources shown to the model, model id/version/locality, validation settings, disclaimer | `grounded.GroundedAssistant` |

**Effective text.** The effective text is the most recent `recognition` layer plus the `user_edit` layers that target it. Edits that target an older recognition layer are reported as stale; they are not silently re-applied.

**Schema.** The schema is `data/schema/note_store.schema.json` (JSON Schema 2020-12).

- The root is an export bundle (`NoteStore.export_bundle`).
- Each stored object is validated against its own `$defs` entry.
- For originals, jsonschema checks the envelope and up to 200 rows. Every row's integer range is also checked in vectorised form when the layer is loaded, because per-row jsonschema checking of an hour of samples (720 k rows) would take minutes.

**Erasure.** `purge_note(note_id, confirm=note_id)` deletes a note, every derived layer that used it (including cross-note answers) and its original if no other note shares it. It exists for the user's right to erase their data. It is explicit, confirmed deletion, not modification.

## ICD interpretations and ambiguities

The firmware sources were read (not modified) to check each interpretation against what the firmware actually does. The reader parses the firmware team's `firmware/tests/vectors/golden_log_v1.bin` in strict mode with zero issues; its decoded values match their C generator (`test_golden_vector.py`).

| # | ICD text | Issue | Implemented interpretation |
|---|---|---|---|
| A1 | 0x02 `theta, phi` u8, "0.5° (θ 0–90°, φ 0–360° as φ/2)" | φ does not fit a u8 at 0.5° | θ_raw = round(θ/0.5°), clipped 0–180; φ_raw = round(φ/2°) mod 180 (2° LSB). The firmware made the same choice (its D5). Values of θ_raw above 180 are flagged. |
| A2 | "crc16" | byte order not stated | Little-endian, like every field (firmware agrees). |
| A3 | "crc16 (CCITT-FALSE over type..payload)" | coverage | Covers the type, length and payload bytes (firmware agrees). |
| A4 | "wrap counter in events" (0x0009) | `arg` meaning | The firmware logs `arg = 0` as a marker on the first tick after the wrap. The reader accepts `arg = 0` as a marker and `arg >= 1` as a wrap count, plus backward-jump detection, without double counting. **Proposal:** use the count, because it survives lost events and silent gaps. |
| A5 | 0x02 `t_ms` u32 "ms since session start" | the firmware writes `t_us / 1000` from the **32-bit** µs counter | `t_ms` restarts every 4 294 967.296 ms (71.6 min), not after 49.7 days. The reader detects this from the wrap events (or the value pattern), corrects it to within 1 ms and reports `t_ms_follows_t_us_wrap`. **Proposal:** derive `t_ms` from a 64-bit time. |
| A6 | 0x04 calibration snapshot, 0x05 annotation | payloads undefined | The firmware-proposed layouts are adopted: `cal_type u8, cal_version u16, record` and `t_us u32, UTF-8`. Raw bytes are always kept. |
| A7 | 0x01 `p_Hx, p_Hy` "page frame" vs 0x02 `x, y` "page origin = first contact" | origins | The firmware logs p_H in its fusion frame, with no page-origin offset. The hand-path layer estimates the offset by least squares from the firmware relation ink = p_H + J·q − origin over all stroke samples. The layer records the fitted offset, a 2×2 J estimate and the residual. |
| A8 | 0x02 at 200 Hz | derivation not specified | The firmware takes a point sample on every 10th 2 kHz tick. The analysis assumes point sampling; a boxcar decimator is reported as a sensitivity case. |
| A9 | stroke samples, `stroke_id` "monotonically increasing" | hover samples? start value? contiguity? | Samples are logged only in contact (firmware agrees). The id increments at pen-down, and the firmware's first stroke is 1. Ids can be skipped when a contact has no sample on the 5 ms grid; this occurs in the simulator session. The app never assumes contiguity. |
| A10 | "first contact of the page session" | no page id and no page-change event; origin instant | One session is treated as one page. The firmware sets the origin at the first emitted sample, so that sample is exactly (0, 0). |
| A11 | event `arg` of pen down/up and mode change; mode numbering | undefined | The firmware writes 0 for pen events and `new | old << 8` for mode change, with section 6 order numbering (OFF = 0 ... SAFE_PASSIVE = 7). The synthetic logs follow the firmware. **Proposal:** use pen-event `arg = stroke_id`. |
| A12 | "list of stroke samples exactly as logged, content-addressed" | what is hashed | The SHA-256 covers only the concatenated 0x02 payloads. The header, framing and other records go in the manifest. |
| A13 | note store "(app side, JSON)" | store technology | A directory of JSON documents. SQLite is used only for the rebuildable search index. |
| A14 | 0x02 `force` "mN (axial)" | the simulator has the normal force N only | The synthetic sessions use N·sin θ (μ = 0) as an axial proxy, documented in the sample metadata. |
| A15 | research frame 2 kHz | the simulator traces are 1 kHz | The synthetic simulator session writes 0x01 frames at 1 kHz. The reader does not assume a rate. |
| A16 | one header per stream | concatenated sessions (for example a BLE reconnect) | Not defined. One header per file is required. |

## Capture fidelity of the 200 Hz / 1 µm stroke format

**Command.** `python -m penapp fidelity` writes `results/app/capture_fidelity.json`. The file lists the SHA-256 of every input trace, because other jobs regenerate those files.

**Reference.**

- The reference is the deposited-ink position (`tip`) of the coupled-simulator traces, at 1 kHz in float32. `sim/run_nominal.py` decimated them from 2 kHz.
- Scenario: seed 200, 9 Hz 0.3 mm tremor, altitude 50°, 1 N.
- Strokes are the contact runs. The page origin is the first-contact ink position.
- Traces with identical content are counted once: `neutral` is byte-identical to `kf_bal` in the current results.
- The analysis therefore covers 6 traces: 18 strokes of at least 50 ms and 12 short contacts, each evaluated at all five 1 ms sampling phases of the 5 ms grid.

**Metrics per stroke:**

- **Time-aligned deviation.** Captured samples are linearly interpolated at the reference times. Reference points before the first or after the last captured sample are compared with that endpoint (end truncation). This coupling is an upper bound on the Fréchet distance.
- **Exact discrete Fréchet distance** (Eiter–Mannila), computed after densifying both polylines to edges of 2 µm or less, so the continuous Fréchet distance lies within 2 µm below the reported value. It is computed by a banded dynamic programme around the time correspondence. The result is *certified*: if any coupling leaving the band would be worse than the banded optimum, that optimum is global; otherwise the band is widened. It is cross-checked against a plain O(nm) implementation in the tests.
- **Consistency check.** Every interior maximum is compared with the linear-interpolation bound a_max·T²/8 + 0.71 µm. It holds for 90/90 stroke evaluations.

| Variant (strokes of at least 50 ms; worst case over traces and phases) | max dev. µm | RMS µm | interior max µm | interior RMS µm | end truncation µm | Fréchet median / p95 / max µm |
|---|---|---|---|---|---|---|
| **ICD 0x02 as specified** (point sample every 5 ms, 1 µm) | **120.6** | **3.6** | 75.6 | 3.0 | 120.6 | 45.6 / 112.1 / 120.6 |
| sampling only (no rounding) | 120.7 | 3.6 | 76.0 | 3.0 | 120.7 | 46.0 / 112.5 / 120.7 |
| quantisation only (1 kHz rounded to 1 µm) | 0.70 | 0.409 (theory 0.408) | 0.70 | 0.409 | 0 | 1.08 / 1.12 / 1.13 (2 µm densification bound) |
| centred 5 ms boxcar instead of point sampling | 121.1 | 3.9 | 55.5 | 3.4 | 121.1 | 44.9 / 103.4 / 121.1 |
| **+ extra samples at pen-down/up instants** (proposal) | **81.5** | **3.0** | 81.5 | 3.0 | 0 | **9.4 / 33.0 / 76.0** |

**Reading (simulation-derived; not a measurement):**

1. The RMS error of the format is a few µm. The 1 µm LSB contributes at most 0.7 µm; the error is set by temporal sampling.
2. **End truncation dominates the maximum.** The first or last sample can land up to 4 ms inside the contact while the pen moves, giving up to 121 µm. It also inflates the Fréchet distance (median 46 µm).
3. **Short contacts are lost.** Of the 60 short-contact evaluations (simulated bounces under 50 ms), 22 produced no sample at all and 38 produced a single sample.
4. Emitting one extra sample at pen-down and one at pen-up (off-grid timestamps) removes truncation and loss. The Fréchet median falls to 9.4 µm and the p95 to 33 µm.
5. The largest remaining interior deviations sit within 50 ms of touchdown in 52 of 90 evaluations. These are simulated contact transients with accelerations that a 200 Hz point sampler cannot follow. The simulator's contact model is unidentified, so their size on paper is unknown.
6. A discrete Fréchet on the raw vertices (1 kHz against 200 Hz) gives a median of 111 µm. That figure measures vertex spacing, not capture error, which is why the densified value is reported.
7. For scale, DeltaPen optical-flow tracking reports 0.068 mm mean absolute error per 10 ms window (ledger OPT-02). Sensing, not the format, is expected to dominate capture error.
8. None of this says anything about sensor accuracy; that needs the bench protocol.

**Recommendations for ICD v1.1:**

- endpoint samples at pen-down/up;
- a specified decimation (point sample and timestamp convention);
- a 64-bit-derived `t_ms`;
- a wrap-count `arg`;
- a defined p_H origin (or a logged page origin);
- a page identifier.

## Segmentation and hand path

- **Strokes** come from the logged `stroke_id` runs. They are cross-checked against pen-down/up events and flagged, never corrected.
- **Lines** start when a stroke's vertical centre leaves the running median of the current line by more than 1.1 x-heights.
- **Words** start at horizontal gaps above 0.6 x-heights. The x-height is estimated as the median height of non-trivial strokes. This is a left-to-right heuristic.
- **Results on the synthetic notes:**
  - 16/16 and 14/14 words recovered with exactly the ground-truth stroke ids;
  - 3/3 lines in both notes.
- **Resampling.** `resample_time`, `resample_arclength` and `densify` serve recogniser adapters and the metrics; they never touch the original.
- **Hand path in the simulator session:**
  - ink minus hand-path estimate: RMS 225 µm, max 462 µm. This is the stage correction of the simulated assertive Kalman run.
  - origin fit residual: 23 µm RMS. The residual is non-zero because the simulated ink also carries passive compliance that q does not measure. The fitted constant offset absorbs its mean, so the estimate means "ink path without active correction".

## Rendering

`render_svg` and `render_note` produce deterministic SVG:

- page µm are mapped to mm with y flipped, so the page frame reads y up;
- each stroke is a polyline, and a single-sample stroke is drawn as a dot;
- a force-to-width option quantises widths into 8 levels over 0–2 N;
- overlays: hand-path estimate, segmentation boxes, or recognised or effective text (user edits in orange);
- strokes cited by an answer can be highlighted, with a caption;
- a legend gives the original's SHA-256 and the overlay layer ids;
- labelled notes carry a red "SYNTHETIC DATA" banner;
- `data-stroke-id`, `data-span-id` and `data-layer-id` attributes keep the SVG machine-traceable.

## Recognition

### Interface and implementations

`Recognizer.recognize(original, segmentation) -> RecognitionResult`. The result holds line and word spans with text, stroke ranges and boxes. `run_recognizer` stores it as a `recognition` layer, with `created_by = <id>@<version>` and the inputs used.

- `NullRecognizer` records that nothing was recognised.
- `GroundTruthRecognizer` passes through the generator's transcript of a **synthetic** session. It is labelled `GROUND-TRUTH PASSTHROUGH`; its CER is 0 by construction. Strokes lost to log corruption are dropped from the links and reported.
- `ErrorInjectingRecognizer(base, cer, seed)` produces seeded character substitutions, deletions and insertions. The achieved CER is measured and stored, and it runs below the target because spaces are never corrupted. It implements the CER-band stress test recommended in `docs/research/notes/OPT_tracking_capture_recognition.md` section 2.4.
- `MLKitDigitalInkAdapter` is a **specification**. It is not runnable here, because ML Kit Digital Ink is an Android/iOS SDK. The stroke mapping `to_ink` is implemented and tested:
  - mm, with y negated for screen coordinates;
  - epoch-ms timestamps;
  - one `Ink` per segmentation line.

  ML Kit returns text without stroke alignment, so the adapter links whole line spans. It forms word spans only when the recognised and segmented word counts agree. Recognising raises until the user has consented to ML Kit's usage-metric reporting to Google.

### Evaluation protocol (to run on real ink; nothing here is a recognition result)

**Metrics.**

- CER = Levenshtein character edits / reference characters. WER is the same on whitespace tokens.
- Both are micro-averaged over lines (`recognize.evaluate_lines`), against a double-keyed human transcript (normalised case and whitespace, punctuation kept).
- Report per writer and pooled, with 95 % bootstrap CIs resampled **by writer**.
- Report separately for:
  1. relative-only capture versus pattern-anchored (Anoto/Ncode) capture;
  2. each tremor severity band (EXP-H01 census);
  3. the ML Kit, MyScript and research recogniser variants.

**Splits.** Splits must be **writer-disjoint**: no writer appears in more than one of train, validation and test, and sessions of one writer never straddle splits. Recogniser settings and language models are frozen before the test split is opened. Report the writer count and characters per split.

**Datasets and licences** (ledger OPT-15, OPT-28 to OPT-31):

- IAM-OnDB, DeepWriting (CC BY-NC-SA 4.0 plus IAM-OnDB registration), MathWriting (CC BY-NC-SA 4.0) and BRUSH (non-commercial research only) may be used **only for non-commercial benchmarking**.
- The licences of OnHW, CASIA and CROHME are unverified; do not use them until they are verified.
- Shipped models must come from a vendor licence or from self-collected data whose consent covers training.
- Record each dataset's licence and version in `created_by`/`params`.

**Error chain.** Recognition CER, then the assistant's faithfulness to the recognised text, then correctness against the human transcript. A summary can be faithful to misrecognised text and still be wrong.

**Current synthetic stress test** (`demo_report.json`, `cer_stress_test`; 2 notes, 5 seeds per band):

| mean achieved CER | word-search recall (mean / min) | answerable questions answered, correct citation (of 2) |
|---|---|---|
| 0 | 1.00 / 1.00 | 2.0 |
| 0.028 | 0.83 / 0.67 | 1.8 |
| 0.061 | 0.69 / 0.46 | 1.6 |
| 0.143 | 0.43 / 0.29 | 1.6 |
| 0.232 | 0.23 / 0.04 | 0.8 |

Every answer that was given cited the correct line. As errors grow, the assistant's recall falls; its precision does not.

## Search

- **Index.** SQLite FTS5 with the `porter unicode61 remove_diacritics 2` tokenizer, one row per recognised line of the effective text.
- **Query safety.** User queries are converted to quoted terms and phrases, so FTS5 operators and SQL fragments are inert (tested).
- **Hits.** Each hit returns the line, a BM25 score, the layer ids (recognition plus user edits) and, for each matched word, its stroke-id ranges and page bounding box.
- The index is a derived cache: `rebuild()` recreates it from the store, and `is_stale()` detects new layers. Assistant output is never indexed.

## Source-grounded assistant

**Pipeline:**

1. Scope screen.
2. Retrieval: FTS5 OR-query of the question's content words. A passage is kept only if it covers at least 50 % of those words.
3. `LLMClient.complete(LLMRequest)`. The request carries only the question and the numbered excerpt *texts*: no ink, no timing, no identifiers.
4. Validation.
5. Storage as an `ai_summary` layer.

**Enforced properties (all tested in `tests/test_grounded.py`):**

- **Refusal without support.** If no note supports the question, the assistant refuses with `no_supporting_notes` and the model is not called.
- **Every sentence is cited.** Every sentence must end with `[S#]` markers naming sources that were actually provided.
- **Support checks.** The sentence's content words must be at least 75 % present in the cited sources, and every number must appear there exactly.
- **All-or-nothing.** Any violation rejects the *whole* answer and nothing is stored. Rejected cases include:
  - a sentence without a citation;
  - an unknown source;
  - an unsupported claim;
  - a wrong number;
  - two sentences sharing one citation;
  - a bare citation;
  - empty output.
- **Traceable citations.** Each citation resolves to note id, layer ids, span id, stroke-id ranges and page box.
- **Provenance and storage.** Answers are stored only as `ai_summary` layers, with provenance: model id and version, locality, determinism, retrieval settings, the sources shown and any consent record. Originals are byte-identical before and after (tested).
- **Consent before cloud use.** A non-local model raises `ConsentRequiredError` unless an explicit `CloudConsent` for that model id exists. The default is `ExtractiveLLM`: deterministic, local, quoting the best-matching note lines verbatim. `RemoteLLMClientSpec` shows the plug-in point and makes no call.
- **No clinical inference.** Questions asking for clinical inferences about tremor, handwriting or health are refused (`out_of_scope_clinical`). The screen is a conservative keyword filter, not a classifier; false refusals are preferred.

**Limitations.** The lexical support test is necessary but not sufficient for faithfulness.

**Evaluation plan** (per the OPT notes, section 2.4):

- AIS two-stage human judgement per sentence, with Krippendorff's α;
- ALCE-style citation recall and precision from an NLI judge, revalidated on our own noisy notes;
- FActScore atomic-fact precision against both the recognised text and the human transcript;
- all of the above reported as a function of CER band.

## Privacy and safety

- **Local-first.**
  - Logs, the note store and the index stay on the user's device.
  - Recognition and the default assistant run locally.
  - Nothing in this package opens a network connection.
- **Explicit consent before any cloud processing:**
  - A non-local `LLMClient` needs a `CloudConsent(granted, model_id, granted_utc, scope)`. The consent is stored with each answer it enabled.
  - The ML Kit adapter needs consent to Google's usage-metric reporting.
  - Consent is per model and can be withheld without losing any local function.
- **Data minimisation.** Models receive recognised text excerpts only. Stroke kinematics (timing, force, tremor content) never leave the note store for assistant purposes, because they are health-relevant data.
- **Not a medical device.**
  - The assistant makes no clinical inferences from handwriting, strokes, tremor or force. It refuses such questions.
  - Every stored answer carries that disclaimer.
  - Hand-path and fidelity outputs are engineering diagnostics, not assessments of a person.
- **Integrity and control.**
  - Originals are immutable and verifiable.
  - Every derived item names its inputs and producer.
  - The user can correct text (`user_edit`) without touching the ink.
  - The user can erase a note completely (`purge_note`, confirmed).
- **Synthetic labelling.** Synthetic sessions carry a `SYNTHETIC` annotation that becomes a `synthetic` label and a red banner on renders. Every results file carries an evidence-status field.

## Implemented vs design-only

| Item | Status |
|---|---|
| ICD section 4 reader/writer, CRC, resync, wrap handling, firmware conventions (A4–A7) | implemented, tested, cross-checked on the firmware golden vector |
| Note store, schema, provenance, immutability, integrity verification, export, erasure | implemented, tested |
| Segmentation (strokes, lines, words), resampling, hand-path layer | implemented, tested on synthetic data |
| Capture-fidelity analysis | implemented; results are simulation-derived |
| SVG rendering | implemented, tested |
| Recogniser interface; null / ground-truth / error-injection recognisers; CER/WER | implemented, tested |
| ML Kit Digital Ink adapter | **design-only** (data mapping implemented and tested) |
| MyScript iink (math/diagrams) | **design-only**, licence negotiation first (OPT-22) |
| FTS5 search with stroke/box links | implemented, tested |
| Grounded assistant, extractive local model, validator, consent gate, scope screen | implemented, tested |
| Cloud LLM client | **design-only** (`RemoteLLMClientSpec`; no network code) |
| NLI/AIS faithfulness evaluation, human recognition evaluation | **protocol only** (needs real ink and raters) |
| Mobile UI, BLE transport, encryption at rest, sync/backup | **not implemented** |

## Demo outputs (synthetic)

- `data/samples/`:
  - `demo_text_errands.*` and `demo_text_project.*` (log, ground-truth transcript, metadata);
  - `demo_sim_kf_asr.*` (0x02 + 0x01 + events from the Kalman-assertive trace);
  - `icd_v1_example.penlog` + `.json`: every record type, extremes, both wrap forms and three corruption cases with the reader's expected behaviour, for cross-team parser checks.
- `results/app/`:
  - `demo_report.json`;
  - `capture_fidelity.json`;
  - SVGs: force width, recognised-text overlay, simulator hand-path overlay, answer highlight, user-edit overlay;
  - `demo_store/`: the note store itself, with a fixed synthetic clock so that it is reproducible.

## Tests

`python3 -m pytest app/tests -q` runs 137 tests, all passing, including the cross-check against the firmware's golden log and its JSON decode (ICD v1.3: CAL_USER v2 snapshot, pen-up boundary sample, timestamp-wrap event, model hash 0xa57d81f6). The suite takes about 6 s. Coverage includes:

- byte layouts checked by hand against an independent bitwise CRC;
- resync fuzzing: no false record is ever accepted;
- all wrap cases, including the firmware `t_ms` restart;
- immutability and tamper detection;
- link and provenance validation;
- segmentation against ground truth;
- Fréchet implementations agreeing, with the band certificate;
- analytic fidelity cases: straight line, circle chord, uniform-rounding RMS;
- SVG geometry;
- recogniser contracts;
- search links and hostile queries;
- all assistant properties;
- the CLI and `python -m penapp`.

## Open issues

1. **ICD v1.1 decisions needed.** A4, A5 and A7 are firmware/ICD mismatches; A1, A6, A8–A11 and A16 are undefined in the ICD; the endpoint-sample proposal is in "Capture fidelity".
2. **Firmware `t_ms` restart.** The firmware's `t_ms = t_us / 1000` restarts at 71.6 min (A5). The reader corrects it to within 1 ms, but the firmware should be fixed.
3. **Hand-path J model.** The estimate assumes a constant J over the session, while tilt changes J (COR-04). A time-varying fit, or logging J / γ, would tighten it.
4. **No real recogniser runs here.** Recognition quality, and therefore search and assistant quality on real ink, is unknown until the protocol above is executed.
5. **Segmentation heuristics.** They assume left-to-right lines and are tuned on synthetic glyphs. They need evaluation on real ink, including delayed strokes, other scripts and diagrams.
6. **Stale user edits.** Edits do not follow a re-run recogniser. A span-alignment step is needed to carry corrections across.
7. **Assistant support check.** The check is lexical and the extractive model cannot paraphrase or combine. A local NLI verifier and a small on-device generator are the next step, with the evaluation plan above.
8. **Clinical-scope screen.** It is keyword-based and should be replaced by a validated classifier with a documented false-refusal rate.
9. **Reader performance.** The pure-Python reader handles 200 Hz logs comfortably, but a 2 kHz research log of 1 h (about 400 MB) needs a vectorised fast path.
10. **Store limitations.** There is no encryption at rest, no multi-device sync and no concurrent-writer locking.
11. **Moving simulator inputs.** The simulator traces are regenerated by other jobs. The fidelity JSON pins the input SHA-256 values, so rerun `python -m penapp fidelity` after simulator changes. In the current traces, `traces_kf_bal.npz` equals `traces_neutral.npz` (seed 200 at 9 Hz; `metrics.json` also shows ratio 1.000), so the balanced estimator did not engage in that run.
