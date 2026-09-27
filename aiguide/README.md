# aiguide: AI prediction for physical guidance and digital autocorrect

**Evidence status.** Everything here is **SIMULATION** or **CALCULATION** on **synthetic** handwriting (glyph-font writers with synthetic tremor) and on a **public-domain text corpus**. No person was recorded and nothing was measured. The report is [`docs/ai_guidance.md`](../docs/ai_guidance.md); results are in [`results/ai/`](../results/ai/).

**The bound.** The nib stage can move the ink by at most its usable travel: ±0.30 mm in the pencil concept (`config/pencil.yaml` `stage.travel_nib`), ±0.55 mm in Rev A. Letters are 2–4 mm tall. The pen can only nudge strokes toward a predicted template; it cannot change one letter or word into another. Digital correction in the app is unbounded, and it never overwrites the original ink.

## Data

| Item | Source | Licence | Where |
|---|---|---|---|
| Text corpus | Tatoeba English sentences, CC0 subset: `https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_CC0.tsv.bz2` (retrieved 2026-09-27; 41 512 sentences, 3.3 M characters; SHA-256 `88741ad3…`) | CC0 1.0 (public-domain dedication; Tatoeba downloads page, "Sentences (CC0)") | `aiguide/data/tatoeba_eng_sentences_CC0.tsv.bz2` (snapshot; `corpus.ensure_corpus()` re-downloads only if it is missing) |
| Glyph font | single-line font of `app/penapp/synth.py` | repository code | imported, not copied |
| Writers, tremor | `aiguide/writer.py`, `stabpen.signals.tremor` | synthetic | generated per seed |

The rest of Tatoeba is CC BY 2.0 FR and is **not** used. The corpus is conversational example-sentence English (with a strong "Tom" bias and some opinionated quotations), not personal notes: every accuracy figure is a proxy for the user's own text.

## Modules

| Module | Role |
|---|---|
| `corpus.py` | Provenance, normalisation to the glyph alphabet (a–z, 0–9, `.,:-/'`, space), deterministic 80/10/10 split by hashed sentence id |
| `lm.py` | `CharKN`: interpolated modified Kneser–Ney character 7-gram, integer-coded n-grams counted with numpy (checked against a brute-force reference in the tests). `WordKN`: word bigram KN. `TextPredictor`: mixture, temperature calibration, `glyph_ahead(text, d)` (the d-th next *written* glyph), word prediction and completion |
| `adapter.py` | `TextPredictorProtocol`, the local `NgramAdapter`, `LLMPredictorSpec` (on-phone and cloud large-model adapter: specification only), `LatencyBudget` |
| `glyphs.py` | Font access and geometry helpers |
| `writer.py` | Synthetic writers: style, writer-specific allographs, per-instance variability, minimum-jerk timing, micrographia |
| `style.py` | Online style estimation: per-letter affine fit (ridge prior for degenerate glyphs, 10 ICP iterations), robust aggregation, baseline, spacing, speed, the user's own exemplars |
| `template.py` | Letter templates in the user's style (own exemplars, else font), app placement or pen anchoring at touchdown, stage-rate template tracks |
| `stroke_predict.py` | On-device stroke continuation: hold, constant velocity / acceleration (FIR), constant turn rate (circumcircle), 2×64 MLP (torch); Cortex-M33 MAC budget |
| `metrics.py` | Per-letter path distance, DTW legibility proxy, size-normalised DTW template-matching recogniser, travel-limit time |
| `guidance.py` | Closed loop on the **unmodified** M1 simulator (`model.run(..., tmpl=...)`): configurations, splice emulation of per-letter authority, nib-offset reference, metrics |
| `icd_template.py` | Proposed ICD record 0x06 (template segment): reference encoder/decoder, framing through `penapp.logfmt`, bandwidth |
| `run_*.py` | One script per study (below) |

The app-side part of B3 is [`app/penapp/autocorrect.py`](../app/penapp/autocorrect.py) (noisy-channel correction stored as a derived `recognition` layer that keeps every span's stroke links, plus optional re-rendering in the writer's style); its tests are `app/tests/test_autocorrect.py`.

## Run

From the repository root, Python 3.11 with `requirements.txt` (torch CPU only for B1.3). Each script writes JSON through `stabpen.provenance` (git revision, parameter digest, seeds, command) and figures stamped with their evidence status.

| Study | Command | Output | Runtime here |
|---|---|---|---|
| B1.1 text predictor | `python3 -m aiguide.run_text` | `text_predictor.json`, `fig_text_calibration.png` | ~2.5 min (+2 min first build of the cached model in `aiguide/build/`) |
| B1.2 style templates | `python3 -m aiguide.run_style` | `style_templates.json`, `fig_style_template_error.png`, `fig_style_example.png` | ~5 min |
| B1.3 stroke continuation | `python3 -m aiguide.run_stroke` | `stroke_prediction.json`, `fig_stroke_prediction.png` | ~0.5 min |
| B2 closed-loop guidance | `python3 -m aiguide.run_guidance` (2 processes) | `guidance.json`, `viz_guided.json`, `fig_guidance_*.png`, `fig_micrographia.png` | ~4 min |
| B3 autocorrect | `python3 -m aiguide.run_autocorrect` | `autocorrect.json`, `fig_autocorrect.png`, `autocorrect_rerender.svg` | ~1 min |
| B4 deployment | `python3 -m aiguide.run_deploy` | `deployment.json`, `fig_lead_time.png` | ~10 s |
| all | `bash aiguide/run_all.sh` | all of the above, then the tests | ~14 min (+2 min on the first run) |

Tests: `python3 -m pytest -q -p no:cacheprovider aiguide/tests` (29 tests, about 6 s) and `python3 -m pytest -q app/tests` (147 tests including the 10 of `test_autocorrect.py`, about 9 s).

Caches (git-ignored through `build/`): `aiguide/build/pred_o7_*.pkl` (trained predictor) and `aiguide/build/numba_cache/` (numba cache of the simulator core, kept out of `sim/`, which other jobs use). Nothing here writes into `sim/`, `stabpen/`, `config/`, `ml/`, `firmware/` or existing `app/` files.

## Conventions

- Seeds are fixed in every script and recorded in the result metadata. Writers are seeded by index; the simulator's sensor noise by writer; tremor by writer and frequency.
- Path distances are to the *ideal-pen ink path*: the intended path plus the static axial nib offset of the configuration (`guidance.nib_offset`), because the guided core servoes the housing datum and a constant offset of all writing does not affect legibility.
- The M1 guided core has binary confidence. Per-letter authority c = min(1, ĉ/c_full), zero below c_min, is emulated by segment-wise runs at quantised `Controller.g_assist` levels spliced at the pen-up gaps; the splice discontinuity is measured and a one-run (mean authority) cross-check is reported.
