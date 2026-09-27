# AI prediction, physical guidance and digital autocorrect (pencil-class concept)

**Status: proposed design, first study (2026-09-27); closed-loop results (§4) re-run on the pencil model P1, with M1 kept for comparison.** Every number here is a **SIM** (simulation) or **CALC** (calculation) on **synthetic** handwriting (glyph-font writers with synthetic tremor) and on a **public-domain text corpus**. No person was recorded; nothing was measured. Labels: **SIM**, **CALC**, **ASSUMPTION** (an allocation or design value, not a result).

Code: [`aiguide/`](../aiguide/README.md) and [`app/penapp/autocorrect.py`](../app/penapp/autocorrect.py). Results: `results/ai/`. Parent report: [`pencil_concept.md`](pencil_concept.md) §6.

## 1. The request, the bound, and the short answer

The request was for "advanced AI prediction models almost to autocorrect the sentence", in a small pencil that helps writing and records to an app, with simulations showing it.

**The physics bound.** The nib stage can move the ink by at most its usable travel: ±0.30 mm in the pencil concept (`config/pencil.yaml` `stage.travel_nib`) and ±0.55 mm in Rev A. Letters are 2–4 mm tall. The pen can reshape strokes by a fraction of a letter; it cannot change one letter or word into another. Digital correction in the app is unbounded, and the original ink is never overwritten. "Autocorrect" therefore has two layers:

1. **Physical micro-guidance.** The app predicts the next letters, synthesises them in the user's style and sends them to the pen as templates. The existing guided mode pulls the nib toward the template, with authority scaled by the calibrated confidence (ICD §5 rule 5) and bounded by the travel.
2. **Digital autocorrect.** The app corrects the recognised text with a language model. The result is a derived layer that cites stroke ids, optionally re-rendered in the user's own handwriting.

**Short answer (SIM, CALC; synthetic data only):**

- **Digital autocorrect works and is the main benefit.** Word error rate (WER) at an injected character error rate (CER) of about 7 % falls from 32 % to 10 % on held-out corpus text and from 30 % to 16 % on note-like text. Correct words are changed in ≤ 0.1 % of cases. The weak spot is names and rare words: 6–14 % of them are wrongly "corrected" until a personal dictionary is added (§6).
- **Physical guidance toward AI templates gives no net benefit on free handwriting, in the pencil model P1 as in M1, but it is safe** (§4). P1 has the skid, the spring-loaded refill and the piezo stage; M1 results are kept for comparison.
  - **Even a perfect (oracle) template helps little.** It reduces the letters' ink path error by 12 % in P1, 21 % on the writing alone (without the touchdown and lift tails below), and 10–20 % in M1. That compares with 63 % on the slow circle of the feature course (443 → 163 µm). In P1, legibility barely moves: DTW −1 to −4 %, recognition +0.00 to +0.02.
  - **Correct AI templates are worse than none.** A correctly predicted letter drawn in the user's estimated style is about 300 µm RMS from what the user intended. That is beyond the break-even template error at which guidance stops helping: 265 µm in P1, 230–330 µm in M1. Guidance toward correct AI templates is 9 % *worse* than none in P1 (13 % on the writing alone; 3–12 % in M1).
  - **Realistic, gated predictions end up slightly worse than none.** Predictions are right for only 40 % of letters two ahead (27 % on the study sentence), so the confidence gate keeps authority low. The result is 2.5 % worse than no guidance in P1 and 0.4–4.3 % worse in M1.
  - **Wrong templates are bounded.** At full authority they cost 8–13 % in path error in P1 (3.5–21.5 % in M1). Gated by their confidence, they cost 0.5–2 %.
    - The stage reached its stop and went no further (0.40 mm in P1).
    - 2.2 % of letters were newly read as the wrongly predicted letter at full authority, and 0.3 % when gated (M1: at most 1.8 %).
- **Finding for the mechanism study: P1 draws a tail at every touchdown and lift.**
  - The unloaded refill protrudes 1.34 mm beyond its working point. The ball stays on the paper while the refill travels, and writes about 0.87 mm along the pen azimuth at each end of a stroke.
  - This, not tremor, is the largest letter-level distortion in P1. Unguided recognition is 0.79 with the tails and 0.93 without them. Guidance cannot remove it (§4.1, §4.3).
- **Micrographia is not corrected physically.** In no configuration, P1 included, did the templates enlarge letters beyond the user's own intended size (§4.6). This agrees with COR-10 and DEC-002.
- **Prediction must run two letters ahead.** A template must reach the pen before the nib lands on that letter. With an allocated 0.18 s end-to-end latency (0.3 s allowed), it must be predicted from text two letters back. Next-glyph top-1 accuracy is 56 % one letter ahead but 40 % two ahead (§5).
- **Freedom to operate.** The template pipeline (recognition → character identifiers → character shapes → commands to the pen) is structurally close to claim 15 of BIC's US 12,026,327 B2 (PAT-01). Attorney review is recommended before any guided-letter feature (§8).

**Recommendation.**
- Ship the digital layer: autocorrect, personal dictionary and re-rendering.
- Keep physical guidance for tasks whose template is *known* (tracing, copying set text, drawing aids; `docs/features.md` "Guided tracing"), where the oracle numbers apply.
- Do not claim AI-predicted physical correction of free writing. Revisit it only if EXP-A02 (§9) shows people's intended letters are closer to a personal template than about 230–330 µm (265 µm in P1), and after the firmware changes in §7.3.
- Pass the touchdown and lift tails of P1 to the mechanism study (free refill protrusion, §4.1). They matter for any writing with the pencil, guided or not.

## 2. Architecture and where each part runs

| Part | Runs on | Why there | Size / cost (CALC) |
|---|---|---|---|
| Guided core (nearest-point template follower, capture gate 2·q_lim), q_lim clip, slew, ICD §5 guard incl. rule 5 | pen MCU (existing `firmware/core/guided.c`, `ml_guard.c`) | 2 kHz loop, safety | existing |
| Template buffer, anchoring at touchdown, validity and expiry, template a-posteriori check (§7.3) | pen MCU | must act within one stroke; needs the nib position | < 2 kB RAM for a few letters |
| Stroke continuation (optional; bridges ≤ 20 ms) | pen MCU | kinematic, no language | MLP 7.8 k MAC ≈ 0.1 ms at 128 MHz; CV 30 MAC |
| Tremor predictor (existing TCN, ICD §5) | pen MCU | unchanged | 16.2 k MAC |
| Handwriting recogniser | phone | model size, vendor SDK (ML Kit adapter spec, `app/penapp/recognize.py`) | unmeasured (EXP-C01) |
| Text predictor: character 7-gram + word bigram, calibrated | phone | 5.8 MB + 10.9 MB; 10 ms per depth-2 prediction here | CALC |
| Style estimation, exemplars, template synthesis | phone | needs the note history | 2.7 ms and 0.7 ms per letter here |
| Autocorrect, re-rendering, note store | phone | derived layers (`app/`) | ~14 ms per line here |
| Larger language model (optional) | phone NPU or cloud with consent | adapter specified, not run (`aiguide/adapter.py`) | budget below |

Data flow: stroke samples (ICD 0x02) go up over BLE; recognition, prediction and synthesis produce a template segment (proposed ICD 0x06, §7); the pen anchors, gates and follows it. Autocorrect runs on the recognised text and never feeds the pen.

## 3. B1 Prediction pipeline

### 3.1 Text predictor (CALC)

**Corpus.** Tatoeba English sentences released under CC0 1.0 (`https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_CC0.tsv.bz2`, retrieved 2026-09-27, SHA-256 `88741ad3…`, 1.3 MB).
- 41 512 sentences, normalised to the glyph alphabet.
- 80/10/10 split by hashed sentence id: 2.69 M training characters, 0.33 M test.
- The rest of Tatoeba (CC BY 2.0 FR) is not used.
- It is example-sentence English, not notes, so it is a domain proxy.

**Model** (`aiguide/lm.py`):
- Interpolated modified Kneser–Ney character 7-gram with 1.37 M n-grams, checked against a brute-force reference in the tests;
- word bigram Kneser–Ney with 38 622 words;
- mixture weight λ = 0.5 and temperatures chosen on validation (T = 1.00 for the next character; 0.97 and 1.00 for glyph depth 1 and 2).

The prediction a template needs is the **d-th next written glyph** (spaces are gaps, not glyphs): `glyph_ahead(text, d)`.

Test split (331 843 positions; glyph rows 6000 sampled positions each). Source: `results/ai/text_predictor.json`, figure `fig_text_calibration.png`.

| Prediction | Top-1 | Top-3 | Calibration (ECE) |
|---|---|---|---|
| Next character (char model only: 59.7 %, 80.5 %) | 61.3 % | 81.0 % | 0.006 |
| … letter inside a word / first letter of a word / space | 65.9 % / 22.6 % / 92.3 % | | |
| Next glyph, depth 1 | 56.1 % | 75.5 % | 0.012 |
| **Next glyph, depth 2** (what the lead time needs, §5) | **39.8 %** | **60.5 %** | 0.025 |
| Next word before its first letter | 13.8 % | 22.5 % | |
| Word completion after 1 / 2 / 3 letters | 31.5 / 41.4 / 50.0 % | 47.3 / 58.4 / 69.3 % | |
| Synthetic note lines (18 lines, out of domain): next glyph depth 1 / 2 | 31–50 % / 19–32 % | | 0.05–0.19 |

- Bits per character: 1.80.
- Out-of-vocabulary token rate: 4.6 % (test) and 1–24 % on the note and rare-word lines.
- **In domain the confidence is calibrated. On note text it is over-confident** (ECE up to 0.19). Rule 5's c_min and c_full must therefore be set on each user's own notes.

Authority at glyph depth 2 with c_full = 0.8 (`config/pencil.yaml` `ai.confidence_full`), c = min(1, ĉ/c_full), and zero below c_min:

| c_min | Letters guided | Correct when guided | Share of authority spent on wrong letters |
|---|---|---|---|
| 0.3 | 50 % | 61 % | 31 % |
| **0.5 (used in B2)** | **27 %** | **81 %** | **17 %** |
| 0.6 | 21 % | 88 % | 12 % |

A larger model plugs in behind `TextPredictorProtocol` (`aiguide/adapter.py`, `LLMPredictorSpec`). Requirements:
- The next-glyph distribution comes from token log-probabilities (top-k ≥ 50, with token healing at the partial word).
- The model is calibrated on the user's notes and mixed with the n-gram, so the lexicon and the personal dictionary still act.
- An on-phone model must return the depth-2 distribution within 50 ms p95. A cloud model (hundreds of ms per round trip, consent via `CloudConsent`) serves only autocorrect and next-word suggestions, never letter templates.
- A timeout gives ĉ = 0.

### 3.2 Style-conditioned templates (SIM)

**Method** (`aiguide/writer.py`, `style.py`, `template.py`).

Synthetic writers are generated from the font:
- a style: x-height 2.0–3.2 mm, slant 0–22°, width, spacing, baseline slope and wander, speed;
- writer-specific smooth allograph deformations (0.04–0.10 x-height);
- per-instance deformation (0.015–0.035), size jitter (3–6 %) and minimum-jerk timing.

Each writer first writes a pangram (calibration: one instance of every letter). Before each later letter, the style is estimated online from the ink written so far, sampled at 200 Hz (clean, or with 6 Hz 0.3 mm tremor):
- a per-letter affine fit to the glyph (ridge prior for degenerate glyphs, 10 ICP iterations);
- median size, width and slant; baseline, spacing and speed;
- the user's own **exemplars** (instances mapped back to glyph units).

The *correct* letter's template is then synthesised and placed, and its distance to the writer's intended path is measured. This measures **style mismatch only**.

24 writers, 2040 letters (`results/ai/style_templates.json`, `fig_style_template_error.png`, `fig_style_example.png`):

| Template (correct letter) | Clean ink: RMS / p95 (µm) | Tremor ink: RMS / p95 (µm) | Shape only, after best translation (tremor) |
|---|---|---|---|
| Font glyph, writer's *true* global style, perfect start point | 260 / 545 | 260 / 545 | 175 |
| Font, estimated style, perfect start point | 266 / 555 | 262 / 547 | 179 |
| Own exemplars, estimated style, perfect start point | 239 / 501 | 268 / 547 | 181 |
| **Font, anchored at the pen's touchdown** | 266 / 555 | **298 / 604** | 184 |
| **Own exemplars, anchored at touchdown** | 239 / 501 | **302 / 611** | 185 |
| Own exemplars, placed by the app after the previous letter (depth 1 / 2) | 356 / 400 | 378 / 426 | 193 / 197 |

Style estimates after the pangram (tremor ink):
- size +0.9 ± 3.9 %;
- slant +1.2 ± 1.9°;
- width +3.4 ± 8.1 %.

Reading:
- **A template for a correctly predicted letter is ≈ 300 µm RMS from the user's intent**, the same size as the pencil travel and as a 0.3 mm tremor.
- The floor (260 µm with a perfect style estimate) is the writer's letter-to-letter variability plus their allograph, which the font does not know.
- Style estimation error is negligible by comparison.
- Own exemplars help only with clean ink (239 vs 266 µm): a single tremor-laden exemplar adds as much noise as it removes.
- Anchoring at the touchdown beats app placement by 75–125 µm, but carries the tremor offset at touchdown (+35 µm).
- Exemplars must be learnt from the unassisted hand path (ink minus stage offset, ICD 4.6 v2), never from guided ink. Otherwise the template converges to itself.

### 3.3 Stroke continuation on the pen (SIM; budget CALC)

**Method.**
- 40 / 10 / 10 writer-disjoint synthetic writers writing corpus sentences.
- Input: pen position at 200 Hz (3 µm noise), clean or with random 4–10 Hz 0.3 mm tremor.
- Target: intended position h ahead.
- Fit windows chosen on validation.
- MLP: 2 × 64, torch, 30 epochs.

Median error (µm) on test writers, clean / tremor input (`results/ai/stroke_prediction.json`, `fig_stroke_prediction.png`):

| Horizon | Hold (= distance travelled) | Constant velocity | Constant acceleration | Constant turn rate | MLP |
|---|---|---|---|---|---|
| 20 ms | 387 / 434 | 204 / 597 | 538 / 750 | 385 / 351 | **101 / 235** |
| 50 ms | 1032 / 1038 | 903 / 1325 | 1439 / 1778 | 1072 / 999 | 475 / 645 |
| 100 ms | 1703 / 1720 | 2235 / 2499 | 3241 / 4031 | 1926 / 2032 | 1171 / 1278 |
| 200 ms | 1901 / 1926 | 4015 / 4035 | 8758 / 10409 | 2143 / 2433 | 1478 / 1538 |

- **Kinematics cannot supply letter templates.** The best predictor stays within the 300 µm travel for 86 % (clean) or 64 % (tremor) of samples at 20 ms, 30 % / 17 % at 50 ms, and ≤ 6 % at 100 ms. Small letters turn by more than 180° in 100 ms, and minimum-jerk pieces stop at corners.
- The on-device class bridges only actuation latency (the TCN's 6 ms) and short template gaps.
- On a different generator (sigma-lognormal scribble) the ranking holds.

**Cortex-M33 budget** (128 MHz, single-precision FPU at 1.5 cycles per MAC, ASSUMPTION):
- MLP: 7 808 MAC (7 946 parameters), ≈ 0.09 ms, 2.3 % CPU at 250 Hz. With int8 CMSIS-NN at 0.5 MAC/cycle it is ≈ 0.13 ms.
- Constant velocity: 30 MAC. Turn rate: 120 MAC.
- All are far inside the ICD §5 budget (≤ 35 k MAC, ≤ 1 ms).

## 4. B2 Closed-loop guidance on the unmodified simulators: pencil model P1, with M1 for comparison (SIM)

### 4.1 Set-up

**Writing.** A synthetic writer writes "return library books by friday" (26 letters, 44 strokes, ≈ 18 s) after a calibration pangram. There are 6 writers; tremor is 0.3 mm peak at 4, 6, 8 and 10 Hz. `model.run(scn, Controller(mode="guided", ...), tmpl=...)` is called exactly as `sim/guided_eval.py` does, with no change to `sim/`.

**Plants and configurations** (`aiguide/guidance.py` `CONFIGS`):
- **Pencil model P1** (`pencil_P1`, the main result): `sim.pencil.model.run`. It has the skid–paper LuGre contact, the spring-loaded refill (F_c 0.15 N), and the four-plate piezo stage with lever, driver and Bouc–Wen hysteresis (`docs/pencil_mechanisms.md` §6).
  - Settings: `Controller(q_lim=0.30e-3)`; stage stop 0.40 mm.
  - The scenario's N0 = 1.0 N is the user's force. P1 splits it into 0.80 N on the skid and 0.20 N on the nib.
  - No preload override is needed and the nib does not bounce: 44 contacts for 44 strokes unguided, 46 with oracle guidance.
  - P1's guided core is the same code as M1's.
- **M1 for comparison** (`sim/pensim`, results unchanged from the first revision):
  - **Rev A**: Controller defaults, q_lim 0.55 mm, stop 0.60 mm, N0 = 1.0 N.
  - **Pencil-like**: `Controller(q_lim=0.30e-3)`, overrides `stage.travel_tip_mech = 0.40e-3`, N0 = 0.15 N, plus `stage.axial_preload = 0.05 N`. M1 declares contact when the axial force exceeds F_pre + 20 mN. With the Rev A preload of 0.25 N, a 0.15 N nib force never registers contact, so the guided mode never engages (checked: mean authority 0.004).
  - **Pencil limits at 0.3 N** (supplementary): as pencil-like, but at 0.3 N.
  - M1 has no skid, so at 0.15 N its stiff 2 kN/m axial path turns lateral stage motion into normal-force changes larger than 0.15 N, and the nib bounces: 88 contacts for 44 strokes unguided, 345 with oracle guidance.

**Static ink offset.** Path distances are measured to the ideal-pen ink path, which is the intended path plus the static ink offset from the housing datum. The guided core servoes the housing datum, and a constant offset of all writing does not affect legibility.
- M1: the axial-slide formula s₀·cos θ, 166 µm in Rev A and 21 µm pencil-like.
- P1: measured on the same writing without tremor, in neutral mode (median of ink − housing datum while nib and skid touch): 4–7 µm. P1's housing datum is the nominal ball centre.

**P1 draws a tail at every touchdown and lift** (a model result for the mechanism study).
- The unloaded refill protrudes up to 1.34 mm beyond its working point (P1 `s_min`).
- While the refill travels between its front stop and the working point, the ball stays on the paper, pushed by the 0.15 N spring. It writes a line of (s_work − s_min)·cos θ ≈ 0.87 mm along the pen azimuth.
- This happens at both ends of every stroke. It takes about 28 ms and accounts for 1.8 mm of the 5.6 mm of ink per stroke on the study sentence (one writer, no tremor).
- The guided core cannot prevent it: the tail is the refill's axial travel, and the core counts itself in contact for 86 % of it.
- P1 results are therefore given twice:
  - **all ink**, as the plant draws it;
  - **writing only**: nib contact while the skid is also on the paper (`guidance.writing_only`). This bridges the skid's 2.5 ms impact bounce at touchdown.

**Template conditions:**

| Condition | Template |
|---|---|
| oracle | true intended path (the core's default) |
| ai_correct | correct letters from own exemplars, estimated style, anchored at the neutral run's touchdown housing position |
| ai_correct, ideal anchor | same shapes anchored at the intended start |
| ai_predicted | the predictor's top-1 letter at glyph depth 2; authority min(1, ĉ/0.8), zero below 0.5 |
| wrong_letter | most likely *wrong* letter for every letter, full authority and gated by its own ĉ |
| wrong_word | the predictor's next word ("to") for "library" |
| a_for_o | an "a" template on each "o" |
| no prediction | neutral stage, and Kalman free mode (assertive set from `results/sim/estimator_selection.json`) |
| no tremor, neutral | the same writing without tremor and without guidance: the device's own error |

**Confidence scaling.** The guided core has only a binary gate (template within 2·q_lim). Per-letter authority is therefore emulated:
- the sentence is simulated once per authority level (quantised to 0, 0.25, 0.5, 0.75 and 1 via `Controller.g_assist`);
- the runs are spliced letter by letter at the middle of the pen-up gaps;
- the housing discontinuity at the splice points (median of per-run maxima) is 19 µm in P1 (max 42 µm). In M1 it is 9 µm pencil-like, 19 µm at 0.3 N and 85 µm in Rev A (max 195 µm), because the compliant hand lets runs diverge;
- a cross-check with one run at the mean authority (0.18) agrees within 3 µm of path RMS in P1 and 3–6 µm in M1.

**Metrics:**
- **Path distance** from each in-contact ink sample to the same letter's intended path plus the static ink offset.
- **Legibility:**
  - DTW to the clean letter after removing the centroid offset;
  - template-matching recognition among 26 size-normalised glyphs in the writer's estimated style. Intended letters read 100 %.
- **Time at the soft limit:** |q_ref| ≥ 0.95 q_lim while in contact.
- **Maximum stage displacement**, and in P1 the time at the piezo driver's voltage limit.
- **Maximum ink deviation** from the unguided run with the same tremor and seed.

### 4.2 Results (mean ± SD over 6 writers × 4 frequencies; `results/ai/guidance.json`, `fig_guidance_summary.png`, `fig_guidance_frequency.png`, `fig_guidance_example.png`)

Ink path distance, RMS (µm), with the p95 in brackets:

| Condition | **P1, all ink** | **P1, writing only** | M1 Rev A | M1 pencil-like | M1 0.3 N |
|---|---|---|---|---|---|
| No tremor, no guidance (device only) | 212 | 155 | 168 | 57 | 65 |
| No guidance (neutral) | 243 ± 15 (485) | 196 ± 22 (398) | 209 ± 27 (423) | 176 ± 16 (341) | 165 ± 15 (321) |
| Kalman free mode | 242 | 195 | 204 (416) | 169 (330) | 158 (309) |
| **Oracle template** | **213 (488)** | **155 (373)** | **167 (370)** | **158 (341)** | **132 (292)** |
| Oracle, 10 ms authority fade-in | 199 | 136 | 174 | 156 | 121 |
| AI template, correct letter | 265 (525) | 222 (442) | 234 (462) | 182 (362) | 174 (346) |
| AI template, correct letter, ideal anchor | 258 | 214 | 224 | 179 | 169 |
| **AI predicted, confidence-gated** | **249 (503)** | **204 (413)** | **217 (439)** | **177 (345)** | **165 (322)** |
| Wrong letter, gated by its confidence | 247 | 200 | 213 | 177 | 166 |
| Wrong letter, full authority | 274 (551) | 234 (470) | 253 (500) | 184 (366) | 179 (354) |
| Wrong next word | 262 | 220 | 230 | 183 | 174 |

Relative to no guidance in P1 (all ink / writing only):
- oracle −12 / −21 %; with a 10 ms fade-in, −18 / −31 %;
- AI correct +9 / +13 %;
- AI predicted +2.5 / +4 %;
- wrong letter +13 / +20 % at full authority, and +1.4 / +2 % when gated.

Legibility and limits, P1:

| Condition | DTW to clean letter, µm (all ink / writing only) | Recognised (all ink / writing only) | Time at soft limit |
|---|---|---|---|
| No tremor, no guidance | 307 / 191 | 0.76 / 0.97 | 0 |
| Neutral | 307 / 197 | 0.79 / 0.93 | 0 |
| Oracle | 304 / 189 | 0.79 / 0.95 | 12 % |
| AI correct | 321 / 224 | 0.76 / 0.91 | 21 % |
| AI predicted | 315 / 206 | 0.78 / 0.93 | 4 % |
| Wrong letter, full | 332 / 243 | 0.74 / 0.86 | 25 % |

The piezo driver was at its voltage limit for at most 0.1 % of contact time (mean over runs) in any condition.

Legibility and limits, M1:

| Condition | DTW to clean letter, µm (Rev A / pencil-like / 0.3 N) | Recognised (same order) | Time at soft limit (same order) |
|---|---|---|---|
| Neutral | 210 / 160 / 150 | 0.92 / 0.97 / 0.97 | 0 |
| Oracle | 176 / 164 / 131 | 0.97 / 0.96 / 0.98 | 11 / 11 / 13 % |
| AI correct | 220 / 178 / 158 | 0.93 / 0.94 / 0.97 | 24 / 19 / 27 % |
| AI predicted | 216 / 164 / 152 | 0.91 / 0.97 / 0.96 | 5 / 3 / 5 % |
| Wrong letter, full | 250 / 181 / 168 | 0.87 / 0.94 / 0.95 | 32 / 22 / 29 % |

The order oracle < no guidance < AI predicted < AI correct < wrong letter at full authority holds at every tremor frequency from 4 to 10 Hz in P1 and in Rev A (`by_frequency`). At M1's pencil limits, AI predicted and no guidance are within 2 µm of each other.

### 4.3 Why letters gain so little, even with the oracle

These are diagnostics of the guided core on handwriting, which is the same code in P1 and M1. They point to firmware changes (§7.3) and, for P1, to the mechanism.

- **P1: the tails** (§4.1) are the largest letter-level distortion. They lower unguided recognition from 0.93 to 0.79 and raise the DTW from 197 to 307 µm, and no template condition changes them.
- **P1: the pen's own error at the user's 1 N is larger than the tremor's share.** Without tremor, P1's writing is already 155 µm from intent; with tremor it is 196 µm. This is consistent with friction drag through the compliant grip: M1 shows the same dependence on force, with 168 µm at 1 N in Rev A and 57–65 µm at 0.15–0.3 N.
  - The oracle template brings it back to 155 µm: it removes about the tremor's share and none of the pen's own error.
  - Unguided letters come out 17 % smaller than intended (§4.6).
- **Short strokes against a 50 ms fade-in.** Authority fades in over 50 ms after contact detection, so mean authority in contact with the oracle is only 0.69 in P1 (0.50–0.74 in M1). A 10 ms fade-in helps: P1 writing only 155 → 136 µm; M1 0.3 N 132 → 121 µm.
- **Hooks at the lift.** Authority drops when contact detection ends while the nib still touches, and the stage then returns across the paper. During authority ramps the guided error was *above* neutral (188 vs 137 µm in an M1 diagnostic run).
- **Travel saturation.** The soft limit is reached 12–13 % of the time in P1 and 11–13 % in M1 even with the oracle.
- **Bounce at 0.15 N** in M1 without a skid (§4.1). P1 does not bounce.
- **Open-loop hand** in both models. The hand follows a fixed reference path, so users neither exploit nor fight the guidance.

### 4.4 Break-even template error (`fig_guidance_breakeven.png`)

The intended letters were warped by a smooth random field with the start point kept, to set the template error, and guided at full authority (writers 0–3, 6 Hz).

| | **P1, all ink** | **P1, writing only** | M1 Rev A | M1 pencil-like | M1 0.3 N |
|---|---|---|---|---|---|
| Unguided path RMS | 244 µm | 197 µm | 204 µm | 185 µm | 173 µm |
| Guided with a perfect template | 207 µm | 143 µm | 161 µm | 168 µm | 139 µm |
| Template error at which guided = unguided (path) | **265 µm** | **267 µm** | **291 µm** | **233 µm** | **334 µm** |
| Same for the DTW legibility proxy | none: a perfect template does not improve it (305 vs 303 µm) | 121 µm | 232 µm | (below 30 µm: bounce) | 257 µm |

Realistic AI templates (≈ 300 µm, §3.2) sit beyond break-even in P1 as in M1. For physical guidance to keep most of the oracle's gain on free writing, templates would need to be within about 100–150 µm of intent. Templates built from the writer's own earlier instances did not get there even on clean ink (239 µm), because every instance of a letter differs.

### 4.5 Wrong predictions: bounded, and letters stay readable

| | **P1** (all ink / writing only) | M1 Rev A | M1 pencil-like | M1 0.3 N |
|---|---|---|---|---|
| Letters newly read as the wrongly predicted letter: full authority / gated (of 624) | 14 / 2 (16 / 2) | 11 / 1 | 0 / 0 | 2 / 1 |
| … read as that letter already without guidance (of 624) | 13 (2) | 2 | 0 | 0 |
| "a" template on "o": read as "a" (of 48) | 0 (0) | 0 | 0 | 0 |
| Max stage displacement, any guided case, over all runs (stop) | 0.40 mm (0.40) | 0.62 mm (0.60) | 0.40 mm (0.40) | 0.41 mm (0.40) |
| Max ink deviation from the unguided pen, wrong letter at full authority: mean of per-run maxima / largest | 0.47 / 0.51 mm | 0.73 / 1.09 mm | 0.36 / 0.39 mm | 0.38 / 0.45 mm |
| Path error on the wrong word's letters vs neutral | 258 vs 240 µm | 220 vs 191 µm | 176 vs 170 µm | 169 vs 159 µm |

- The stage reached but did not pass its mechanical stop. It pressed at most 1 µm into it in P1 and up to 20 µm into the elastomer stop in Rev A.
- The ink can deviate from the unguided run by more than the stage travel: up to 0.51 mm in P1 and 1.09 mm in Rev A. The stage sits on its stop, and the compliant hand and housing drift further under the changed contact forces.
- The capture gate (2·q_lim) disengages guidance once the user's letter departs from the template.
- In P1, the unguided ink already reads 13 of 624 letters as the predicted wrong letter, because the tails distort letters. Guidance at full authority makes 14 further letters read that way (2.2 %); gated, 2 (0.3 %).
- **No knock-on into the next word.** On the letters of the word after the wrong one, path RMS was about the same as when both words were predicted correctly:

  | Plant | After the wrong word | Both words correct | Unguided |
  |---|---|---|---|
  | P1 | 267 µm | 271 µm | 244 µm |
  | M1 Rev A | 256 µm | 261 µm | 227 µm |
  | M1 pencil-like | 189 µm | 188 µm | 182 µm |
  | M1 0.3 N | 185 µm | 188 µm | 171 µm |

  The extra error there is the ordinary cost of correct-but-imperfect AI templates (§4.2), not a consequence of the wrong word. Rule T5 (§7.3) still bounds how long any wrong segment can act.

### 4.6 Micrographia (`fig_micrographia.png`)

Set-up: a 35 % linear size decrement along the line, no tremor, and templates at the calibration size. The mean deficit is 0.69 mm (template 3.46 mm vs intended 2.83 mm).

| Height change relative to the user's intended letter (fraction of the deficit) | **P1** | M1 Rev A | M1 pencil-like | M1 0.3 N |
|---|---|---|---|---|
| Unguided ink | −0.66 (the pen shrinks letters 17 %) | −0.83 (M1 lag shrinks letters 21 %) | +0.06 | −0.11 |
| Guided toward oracle shapes at full size | −0.63 | −0.51 | +0.07 | −0.03 |
| Guided toward AI templates at full size | −0.58 | −0.46 | +0.06 | −0.02 |

- **Guidance never made letters larger than the user intended.** It recovered only part of the pen's own shrinkage (at 1 N in P1 and in Rev A).
- The travel bound would allow up to q_lim ≈ 0.3 mm of the 0.69 mm deficit (43 %). The nearest-point core cannot use it, because it corrects toward the *nearest* template point; a smaller letter lies close to parts of the larger template.
- Micrographia support stays cueing and feedback (DEC-002). The app can report size drift from the captured ink.

### 4.7 3D view

`results/ai/viz_guided.json` (1.0 MB) follows the requested schema: `meta`, `units` {mm, s}, and `cases` with `key`, `label`, `t`, `intended`, `template`, `housing` [x, y, z], `ink`, `contact`, `confidence` and `metrics`.

- The plant is the pencil model P1, so the page can show it with the pencil CAD.
  - `meta.plant` names the model; `meta.case_group` is "AI guidance: a written sentence (pencil model P1)".
  - `housing` is P1's housing datum (the nominal ball centre); `ink` is the page projection of the ball centre.
- Sampling: 100 Hz, 1 µm resolution.
- Extra fields:
  - `authority` (g_eff), `template_pen_down` and `config`;
  - `skid_contact`: contact without the skid is a touchdown or lift tail;
  - `metrics_writing_only`: the metrics with the tails excluded.
- The template includes its pen-up moves. For `ai_predicted`, only letters whose confidence reached c_min are included.
- It holds eight cases on the same sentence, writer and tremor (6 Hz): neutral, Kalman, oracle, AI predicted, AI correct, wrong letter, wrong word, and "a" for "o".
- The viewer compares every AI case with the first case keyed `neutral`, so a single configuration is exported.

## 5. B4 Lead time, latency and bandwidth (CALC; `results/ai/deployment.json`, `fig_lead_time.png`)

**Writing timing** (synthetic writers):
- letter duration median 0.51 s (p10 0.27 s, p90 0.82 s);
- pen-up gap between letters median 157 ms (p10 126 ms).

The template for letter k must be on the pen before the nib lands on letter k, because the pen anchors it at the touchdown. If it is predicted from the text up to letter k − d with end-to-end latency L, the fraction of letters served in time is:

| L | Depth 1 | Depth 2: letter done at its last lift | Depth 2: done only at the next touchdown | Depth 3 |
|---|---|---|---|---|
| 0.10 s | 100 % | 100 % | 100 % | 100 % |
| 0.15 s | 61 % | 100 % | 100 % | 100 % |
| 0.20 s | 11 % | 100 % | 100 % | 100 % |
| **0.30 s** (`ai.template_lead`) | **0 %** | **100 %** | **100 %** | 100 % |
| 0.60 s | 0 % | 91 % | 63 % | 100 % |

If a letter is only known to be finished when the next one starts (a "t" bar or an "i" dot may follow), depth 1 never makes it. **Depth 2 is necessary and sufficient at 0.3 s**, and prediction accuracy drops from 56 % to 40 %.

Latency budget (allocations, ASSUMPTION; `aiguide.adapter.LatencyBudget`):

| BLE uplink | Recogniser | Prediction | Synthesis | BLE downlink | Pen | Total | Margin to 0.3 s |
|---|---|---|---|---|---|---|---|
| 30 ms | 60 ms | 50 ms | 10 ms | 30 ms | 2 ms | **182 ms** | 118 ms |

- Measured here (Python, this container, not a phone): depth-2 prediction 10 ms median (14 ms p95); style update 2.7 ms per letter; synthesis 0.7 ms per letter.
- The recogniser latency is unmeasured and dominates the uncertainty (EXP-C01).
- A cloud round trip does not fit letter templates.

**Bandwidth** of the proposed 0x06 record, with points every 100 µm along the path:
- per letter: 1.7 records, 81 points, 206 bytes;
- at 1.45 letters/s: **117 points/s, 0.30 kB/s**, or 0.9 kB/s if every template is re-sent three times as predictions are revised.
- The stroke uplink (ICD 0x02 at 200 Hz) is 4.8 kB/s, so templates add < 20 %.

## 6. B3 Digital autocorrect in the app (CALC; `results/ai/autocorrect.json`, `fig_autocorrect.png`, `autocorrect_rerender.svg`)

**Pipeline** (`app/penapp/autocorrect.py`):

1. Recognition layer.
2. Candidates within two edits (SymSpell-style delete index over words seen at least twice), plus the observed word itself.
3. Scoring:
   - prior: word bigram Kneser–Ney. An out-of-vocabulary word gets p_oov × its character-model spelling probability, so names are not impossible.
   - channel: a weighted edit distance matching the recogniser's error process.
4. Forward–backward posteriors per word. A word is changed only if another candidate's posterior exceeds 0.9.
5. The result is stored as a new `recognition` layer (`created_by: penapp.autocorrect@0.1.0`):
   - every span keeps exactly the stroke ranges and box of the span it corrects, with the posterior as `confidence`;
   - `params.changes` lists each change (from, to, posterior, stroke ranges);
   - inputs name the base layer, the original and the corpus (SHA-256 and licence).
6. The original ink and the base layer are untouched (tested).

**Optional re-rendering.** The corrected words are drawn in the writer's own style: size, slant and exemplars fitted on the note's own correctly recognised words, placed on each word's baseline. This is a derived drawing only (`autocorrect_rerender.svg`).

**Evaluation.**
- Synthetic sessions of 60 held-out corpus sentences (371 words), 18 note-like lines (111 words) and 10 lines with names and rare words (54 words, 16 out of the lexicon).
- Errors injected by `ErrorInjectingRecognizer` at target CER 2, 5, 10 and 15 % (achieved 1.7, 3.1, 7.3 and 11.3 %); 5 seeds.
- Threshold 0.9.

| Text | WER before → after, CER 1.7 / 3.1 / 7.3 / 11.3 % | Correct words changed | Rare words kept / fixed |
|---|---|---|---|
| Held-out corpus sentences | 8.7→2.1 / 15.0→4.3 / 32.1→10.5 / 46.4→17.2 % | 0.0–0.1 % | 100 % / 0 % |
| Note-like lines | 7.2→2.9 / 12.6→6.3 / 29.5→16.0 / 43.8→24.7 % | 0 % | 100 % / 0 % |
| Lines with names and rare words | 8.9→6.3 / 15.9→13.3 / 33.0→22.6 / 49.6→34.8 % | 1.6–3.0 % | **86–94 %** / 0 % |
| Same, with a personal dictionary (the names) | 8.9→0.4 / 15.9→5.6 / 33.0→10.0 / 49.6→17.8 % | 0 % | 100 % / 79–91 % |

- The threshold trades fixes against over-correction. At 0.5, held-out WER at 7 % CER reaches 7.3 %, but 1.3 % of correct words and 12 % of words in the name lines are wrongly changed. 0.9 is the default.
- **Names and rare words are the failure mode.** The fix is a personal dictionary built from the user's contacts and earlier accepted notes. Low-confidence changes should be shown with the original ink (AC-A01-07).
- Some changes are wrong but plausible ("testb" → "tests" for "test"). Every change is therefore a visible suggestion that cites its strokes.
- **Schema proposal.** Add layer kinds `text_correction` (so a correction does not silently become the effective text) and `rerender` (polylines citing stroke ids) to `data/schema/note_store.schema.json` and ICD §4.5.
  - Until then, the autocorrect layer is written only on request.
  - It becomes the effective text like any re-run recogniser; user edits on the base layer become stale (app open issue 6).

## 7. Proposed ICD additions (proposal only; `docs/icd.md` is not edited)

### 7.1 Record 0x06: template segment (phone → pen, and loggable)

The record uses the §4.1 framing: `type 0x06 | length | payload | CRC-16`. Reference encoder and decoder: `aiguide/icd_template.py`. Today's app reader keeps it as raw bytes with an `unknown_type` notice (tested).

| Field | Type | Meaning |
|---|---|---|
| seg_id | u16 | one predicted letter; monotonic per session |
| part | u8 | stroke index (bits 0–6); bit 7 = last stroke of the segment |
| flags | u8 | bit0 ANCHOR (points relative to the nib at the first contact after t_valid_from); bit1 SUPERSEDE (drop pending segments with id ≥ seg_id); bit2 CANCEL; bit3 SYNTHETIC |
| glyph | u8 | predicted character (ASCII) |
| confidence | u8 | calibrated ĉ × 255 (rule 5) |
| t_valid_from, t_valid_to | u32, u32 | session ms (ICD 4.3 clock); validity window and expiry |
| x0, y0 | i32, i32 | µm: stroke start (page frame, or relative to the anchor) |
| speed | u8 | nominal mm/s, so the pen times the template at the stage rate |
| n, points | u8, n × (i8, i8) | successive differences in 10 µm steps with error feedback; ≤ 115 points per record |

The header is 24 bytes. An example "t" is 2 records of 116 + 52 framed bytes (`deployment.json` holds the hex).

### 7.2 Where the record goes

The same bytes go over a BLE characteristic (downlink) and into the research log. The pen logs every accepted or rejected segment with event 0x0006 and a reason code.

### 7.3 Pen-side rules for templates (extend the ICD §5 guard)

- **T1.** Accept a segment only with a valid CRC, t_valid_to in the future and ĉ ≥ c_min. Otherwise ignore it.
- **T2.** If ANCHOR is set, translate the segment so that its first point is the nib position at the first contact after t_valid_from.
- **T3.** Authority = rule 5 (min(1, ĉ/c_full), slewed within 20 ms) × the existing capture gate. Also consider a corridor of about 150 µm, the writer's own variability (§3.2), inside which the template does not correct.
- **T4.** Expire at t_valid_to, or at the lift after the last stroke. SUPERSEDE replaces revised predictions.
- **T5.** A-posteriori check: if the hand path stays more than ~1.5·q_lim from the segment for more than ~60 ms, drop the segment *and* re-acquire the next one from its own anchor. This bounds how long a wrong segment acts (§4.5).
- **T6.** At a stroke end, hold the stage command until the nib is off the paper (optical height, or axial force below threshold for 10 ms), then return with the slew limit. This addresses the hooks (§4.3).
- **T7.** When an anchored segment is pending and the nib hovers within ~1 mm, start the authority ramp before touchdown. This addresses the 50 ms fade-in on short strokes.
- **T8.** Templates never scale letters. Size support is a cue (haptic or visual), not a correction (DEC-002).

T5–T7 are firmware and simulator changes. They were **not** tested here, because `sim/` was not modified.

## 8. Freedom to operate against PAT-01 (not legal advice)

PAT-01 is US 12,026,327 B2 (BIC; active as displayed, expiry 2043), with a withdrawn EP family member (PAT-02). Claim elements are as recorded in `docs/evidence.csv` and `docs/research/notes/PAT_patents.md` §9.

| Claim element (independent claims) | This design | Assessment for the attorney |
|---|---|---|
| Cl. 1: nib manipulator moving the nib end portion in XP/YP **and ZP** | Two actively controlled in-plane axes only. Axial motion is passive (Rev A suspension; pencil nib spring and skid). A pivoting refill adds a small coupled Z (q²/2L₁) | Key differentiator; PAT notes Q1 |
| Cl. 1: IMU measuring the position of axis A relative to the writing surface | The IMU estimates tilt θ, φ for the Jacobian and tremor fusion | Probably *met*; PAT notes Q3 |
| Cl. 1: ECU obtains segment formation commands and actuates the manipulator "to scribe a predefined character defined by the commands" | The template is a *predicted* letter in the user's own style. The **user's hand** produces the letter; the stage adds bounded corrections (≤ 0.3 mm, about 10 % of letter height) only while the nib is within 2·q_lim of the template, at confidence-scaled authority. A still hand writes nothing | Central question: does bounded, user-led guidance toward a template "scribe"? PAT notes Q2 |
| Cl. 15 (method): sample → recognition → character identifiers → **predefined character store** → segment formation commands to the pen | Handwriting recognition → identifiers of what was written → a language model predicts the **next** characters → templates from the user's **own exemplars** (font only as a fallback) → template segments (0x06) | **Structurally close.** Differences: the identifiers sent are predictions, not the recognised content; the shapes come from the user's handwriting; the pen does not scribe |
| Cl. 18 (system): pen + external processor + wireless network with recognition and character store | Pen + phone + BLE | Depends on the claim-1 pen (ZP) and on the "character store" reading |

**Design choices to record (DEC entry proposed):**
- no active ZP;
- user-led motion with bounded local correction;
- confidence-scaled authority with a capture gate;
- templates from the user's own exemplars, with the font as a fallback only;
- digital correction kept in the app.

A design-around for claim 15 is available: disable the font fallback, so that letters never seen from this user get no template. The cost is small, because a pangram calibration covers all letters.

**Other references** for the same review: PAT-03 (CN, pending: guidance force along a preset stroke track toward a target font) and PAT-25 (vibration guidance to a selected letter), from `PAT_patents.md` feature g.

**Recommendation.** Attorney review of PAT-01 claims 1, 15 and 18 against §7's template path before any guided-letter feature is built or published. The digital autocorrect and the tremor modes do not use the template path.

## 9. Limits and open experiments

**Limits** (most decisive first):

1. **No human data.** Writers, allographs, variability and tremor are generator settings. The break-even of 230–330 µm (265 µm in P1) must be compared with real within-writer variability.
2. **P1 is a model of the pencil, not the pencil.**
   - Its skid, refill and stage parameters include ASSUMPTION values (`docs/pencil_mechanisms.md`).
   - The touchdown and lift tails follow from the refill's 1.34 mm free protrusion and from the model hand lifting the pen straight up from the page. A lift that moves back along the pen axis would shorten them; only a prototype can say by how much.
   - In both P1 and M1 the hand is an open-loop reference path that neither follows nor resists guidance.
   - M1 has no skid or piezo stage, and its contact at 0.15 N bounces.
3. **The guided core was used as is.** Its binary gate, nearest-point progress, 50 ms fade-in and fade at contact loss shape the results. T5–T7 are untested.
4. **The text domain is a proxy.** Tatoeba is not personal notes. Calibration degrades on notes (ECE up to 0.19), and names are the main autocorrect risk.
5. **Recognition is simulated** by error injection. Real recogniser errors are not uniform edits.
6. **Splice emulation of per-letter authority** carries up to 0.2 mm housing discontinuity in Rev A and 42 µm in P1. The one-run cross-check agrees.
7. **Print-style writing only.** Letter segmentation for recognition and anchoring assumes pen lifts between letters. Cursive needs online segmentation.

**Open experiments** (EXP-C01 already covers recognition CER on real ink; it now also feeds the predictor's calibration):

- **EXP-A02 (proposed): guidance acceptance with people.**
  - Participants: healthy adults, ET and PD, 12–20 per group.
  - Tasks: copying known text (template = the known text) and free writing of dictated sentences (AI templates).
  - Conditions, within subjects and counter-balanced: no guidance; known-template guidance; AI-template guidance; AI guidance with 10 % deliberately wrong templates. Participants are blinded to the condition where possible.
  - Measures:
    - blinded legibility ratings and recogniser CER;
    - path distance to each participant's own unguided letters;
    - within-writer letter variability (the break-even input, §4.4);
    - sense of agency and perceived control (questionnaire);
    - force and "fighting" signs from the axial force channel;
    - maximum imposed deviation;
    - fatigue.
  - **Decision rule (proposed):** keep AI-template guidance only if it improves legibility with a 95 % CI excluding zero, *and* does not reduce agency ratings, *and* wrong templates never make a letter unreadable. Otherwise ship known-template guidance and digital correction only.
- **EXP-A03 (proposed): autocorrect on real notes.**
  - Recogniser output on consented notes. Report WER before and after, over-correction, name handling with and without the personal dictionary, and the acceptance rate of suggestions.
- **Simulator follow-up.** The main case now runs on P1 (§4). Still open:
  - P1 with a shorter free refill protrusion (the tails);
  - a firmware-faithful guided core with T5–T7;
  - a closed-loop hand model.

## 10. Reproduce

`bash aiguide/run_all.sh` takes about 16 minutes here (plus 2 minutes on the first run to build the cached text model) and uses at most two processes. B2 (P1 and M1) alone takes about 6 minutes. Each study has its own script (`aiguide/README.md`).

Tests:
- `python3 -m pytest -q -p no:cacheprovider aiguide/tests`: 32 tests, 3 of them on the P1 dispatch, static offset and tails;
- `python3 -m pytest -q app/tests`: 147 tests, the 137 existing plus 10 for autocorrect.

Every JSON records the git revision, parameter digest, seeds and command. Every figure is stamped with its evidence status.
