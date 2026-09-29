# AI and control v2 (study L): delayed ink, tremor–intent separation, RL, prediction, synthesis, shared control

**Status: DRAFT in progress (2026-09-29).** The test-grid stages are running; sections marked *pending* are filled when they finish. Nothing was built or measured on a pen or a person.

Every number carries a label:
- **SIM**: an executed simulation of model HW1 (`handwriting/`, used unchanged) on synthetic writers and synthetic tremor;
- **CALC**: a calculation (on synthetic data or public text);
- **LIT**: published literature, with its proposed ledger id (`results/ai2/evidence_rows.csv`) or its existing id in `docs/evidence.csv`;
- **ASSUMPTION**: an input nobody has measured.

Every target here is a hypothesis until it is measured.

## Tuning results already fixed (tuning writers 100–103; rules written before any test run)

### Task 1, stage D0: which fixed-lag estimator (SIM, open loop, seed 300)

Time-aligned tremor residual at 1–2 mm, 6–10 Hz (µm RMS), by lag:

| Estimator | 0 ms | 25 ms | 50 ms | 100 ms | tremor-free output (ungated) |
|---|---|---|---|---|---|
| Fixed-lag RTS smoother, chosen (τ_decay 2 s, q_t 1e-9) | 412 | 345 | 342 | 317 | 259 |
| Fixed-lag RTS smoother, other 6 settings | 423–585 | 349–431 | 348–415 | 323–368 | 222–317 |
| Windowed zero-phase smoother (clean copy on a sliding window) | 1060 | 1291 | 1212 | 1116 | 65 |

- The smoother "listens": its tremor estimate is much better than the Rev H tracker's, but it also reads writing as tremor (259 µm on tremor-free writing, ungated). A gate is needed.

### Task 1, stage D1: the tremor-line gate (SIM, open loop)

- A running detector on the page sensor (4 s window, 2 s Welch segments, peak-to-floor ratio in 4.5–13.5 Hz) with hysteresis: open after the ratio stays above 5 for 0.5 s; close after it stays below 2.5 for 1 s.
- Chosen: never opened on any tuning writer's tremor-free writing; open 95 % of the detector's updates at 1–2 mm; at 0.3 mm open 0 % (6 Hz), 0 % (8 Hz) and 86 % (10 Hz).

### Task 1, stages D2 and D2b: the lag per nose travel (SIM, closed loop)

- D2 (no amplitude gate): every lag setting cut the 1–2 mm ink error (631 → 392–420 µm) but none passed the letters and coverage rules at 10 Hz, 0.3 mm, where the gate opens on a small line.
- D2b added an amplitude gate (the listening estimate fades in between 0.15 and 0.35 mm of detected line amplitude). Seed 300 results (Rev H tracker: 631 µm, 76 % of letters):

| Setting | Ink error 1–2 mm | Letters read | Words read | Path covered | Mean lag | Nose travel p95 | Rules R1–R4 |
|---|---|---|---|---|---|---|---|
| Gated tracker, lag 0 (±3 mm) | 428 µm | 76.0 % | 71.7 % | 83.9 % | 0 ms | 2.18 mm | pass |
| Lag ≤ 25 ms, ±3 mm (chosen for ±3 mm) | 408 µm | 76.4 % | 70.8 % | 83.8 % | 14 ms | 2.55 mm | pass |
| Lag ≤ 50 ms, ±6 mm (chosen for ±6 mm) | 402 µm | 75.3 % | 68.3 % | 83.8 % | 27 ms | 3.16 mm | pass |
| Lag ≤ 50 ms, ±3 mm | 408 µm | 74.0 % | 66.7 % | 83.6 % | 27 ms | 3.16 mm | pass |

- **Confirmation on seed 301 (SIM):** tracker 603 µm; gated lag 0 413 µm (passes all rules); lag 25 ms (±3 mm) 394 µm and lag 50 ms (±6 mm) 388 µm, but **both fail R3** (letters: 74.4 % and 74.7 % against the gated tracker's 76.8 %). So on tuning data delayed ink lowers the ink error by about 5 % but does not read better, and it is **not adopted**; the test grid shows it for information.

### Task 2: learned estimators (SIM, open loop, tuning writers 100–103, seed 300)

Trained on 320 domain-randomised synthetic writers (13 min each on one CPU thread). J = mean residual at 1–2 mm over lags 0/25/50 ms + 2 × (tremor-free output above 25 µm).

| Estimator | J | Residual 1–2 mm, lags 0 / 25 / 50 ms | 0.3 mm | Tremor-free output | Parameters | MAC per 2 ms step |
|---|---|---|---|---|---|---|
| Hybrid Kalman–network | 382 µm | 389 / 325 / 315 µm | 206 µm | 44 µm | 34 440 | 33 888 |
| TCN + 20 s calibration (true tremor as context) | 384 µm | 460 / 343 / 348 µm | 178 µm | 12 µm | 33 864 | 33 312 |
| TCN | 389 µm | 457 / 360 / 350 µm | 188 µm | 23 µm | 33 800 | 33 248 |
| Transformer (under-trained: 489 steps in 13 min) | 861 µm | 802 / 824 / 730 µm | 251 µm | 63 µm | 23 656 | 47 456 |
| Model-based stack (gate + RTS + Rev H fallback) | 588 µm | 592 / 559 / 556 µm | 238 µm | 34 µm | – | – |
| Fixed-lag RTS, ungated | 814 µm | 412 / 343 / 335 µm | 275 µm | 251 µm | – | – |

- The model-based stack's open-loop residual is large mainly because its gate needs 4.5 s of each 20 s recording to open; after 5 s its lag-0 residual is 444 µm against the ungated smoother's 409 µm (CALC on the same arrays).
## M1. What was simulated (SIM)

**The pen and the hand.** Model HW1 of the handwriting study, used read-only through the aiprior study's conventions (`aiprior/core.py`):
- Rev H: ±3 mm nose, 80 Hz servo, 0.84 N peak; the nose acts while the tip is within 2 mm of the page.
- A ±6 mm nose for the delayed-ink runs: the same servo, force and moving mass with double the travel (ASSUMPTION; it stands for study N's bigger nose).
- The HAP-26 hand, adapted to the pen; LuGre friction at the tip.
- The pen's own sensors (fusion sensor models): IMU in the handle (3.84 kHz, 0.35 ms latency), page sensor (1 kHz, 2 ms latency, 3 µm noise), axial contact sensor (1 ms latency).
- The Rev H tracker: the accelerometer Kalman filter re-tuned for Rev H (the handwriting study's tracker).

**The replay convention** (as aiprior). Every estimator runs on the sensor streams of the run with the nose held. Its command is then replayed in closed loop on the same hand, writing and tremor. The "perfect knowledge" row uses the true tremor.

**Writers and seeds.**
- Test: aiguide writers 0–5, seeds 200–203, tremor 6/8/10 Hz × 0.3/1/2 mm peak at the hand (216 scenarios per variant), plus each writer's tremor-free writing. Used once, for the final tables.
- Tuning: writers 100–103, seed 300 (seed 301 to confirm). Every choice. Rules written in code before the test ran (`ai2/tuning.py`, `ai2/stage_cl.py`, `ai2/stage_rl.py`, `ai2/stage_learn.py`).
- Training (learned models and RL): 320 synthetic writers (ids 1000+) writing random 3–5 word CC0 phrases, with randomised tremor, hand, grip and sensors (`ai2/data.py`).

**Causality.** Every command at a control tick uses only sensor data available at that tick. Unit tests change future samples and check that no earlier output changes (`ai2/tests/`).
### Delayed ink: how it works (proposed design; SIM)

- The nose command is q(t) = [x̂_h(s) − x̂_h(t+δ)] − g·d̂(s) − (1−g)·d̂_RevH(t−λ), with s = t + δ − λ.
  - x̂_h is the handle position and d̂ the tremor, both smoothed with a fixed lag (RTS backward pass, LIT EML-47);
  - δ = 3.4 ms is the servo's delay (CALC from the Rev H servo);
  - g is the tremor-line gate (below); when it is closed the pen falls back to the Rev H tracker, delayed by the same λ.
- So the ball draws the hand's path, cleaned of tremor, λ seconds late. The nose absorbs the hand–ink distance.
- **The lag is not constant.** It grows while the hand writes a stroke (at most λ_max) and collapses fast when the hand stops or starts to lift (speed below 4 mm/s for 4 ms, or the refill slide sensing lift). Otherwise the ball would leave the paper before it has drawn the end of the stroke.
- **Estimators compared** (open loop, tuning data; stage D0):
  - the fixed-lag RTS Kalman smoother (forward Kalman filter over merged IMU and page-sensor samples, stored gains, backward pass per output; Särkkä 2013 Algorithm 10.7, LIT EML-47);
  - a windowed zero-phase smoother (the app's clean copy on a sliding window, with autoregressive padding at the window's end);
  - a fixed-lag Wiener filter;
  - the learned models of task 2 (outputs at lags 0, 25, 50 and 100 ms).

### Shared control: one arbitration law for every kind of help (proposed design)

Every assistance the pen gives has the same form (policy blending, LIT HAP-23; review LIT EML-58):

  u_nose = α(t) · u_assist(t),   α = α_max(mode) × c_conf × c_need × c_agree   (slew-limited)

| Factor | What it measures | Stabilisation | Guidance (known text) | Autowrite |
|---|---|---|---|---|
| α_max | the mode's ceiling | 1 | the practice level (0.5 partial, 1.0 full) | the user's setting |
| c_conf | confidence that the help is right | the tremor-line gate × amplitude gate (or the RL arbiter) | 1 for a known text; the predictor's calibrated confidence otherwise (aiprior rule 5: nothing below 0.5) | 1 for a known text |
| c_need | assistance as needed | 1 | per-letter gain from the writer's own recent error, with a forgetting factor (LIT HAP-94, EML-59) | 1 |
| c_agree | hand-back | 1 | 0 when the writer stays > 2.5 mm from the target for 60 ms (the drop rule, T5) or pushes against the nose (force channel) | same |

Invariants: the pen never starts a stroke (no pen-down, no help); it never scales letters (T8); its reach is the nose travel; the writer can always override (the nose is weaker than the hand: 0.84 N peak).

## Files and how to run

```
python3 -m ai2.run_study [--quick] [--workers 1] [--stages d01 d2 d2b learn_data learn rl cl test text synth shared report]
python3 -m pytest -q ai2/tests          # 18 tests, about 30 s on one core
```

`--quick` (fewer writers, seeds, samples and minutes; about 45 minutes in all) writes to `ai2/build/quick/` and never overwrites the results. Stage caches, trained models and policies, corpora and training data are in `ai2/build/` (git-ignored); every stage re-creates what it needs.

| File | What it does |
|---|---|
| `smoothers.py` | Fixed-lag RTS Kalman smoother (numba), windowed zero-phase smoother, fixed-lag Wiener filter, the causal tremor-line detector |
| `delayed.py` | Delayed ink: estimates on a scenario, the lag policies (catch-up, hold, limit), the causal nose command, closed-loop runs and metrics (coverage, travel needed, ink-timeline false correction) |
| `tuning.py` | Stages D0, D1, D2, D2b on tuning data, with the rules |
| `data.py`, `stage_learn_data.py` | Domain-randomised training samples and the tuning arrays |
| `learned.py`, `stage_learn.py` | TCN, calibrated TCN, hybrid Kalman-network, transformer; time-boxed training; the causal estimator wrapper |
| `rl_env.py`, `stage_rl.py` | Gymnasium environments (arbiter, residual) with a swappable backend; SB3 PPO and SAC; a fast numpy policy |
| `candidates.py`, `stage_cl.py` | The task 2–3 candidates in closed loop; the closed-loop tuning check (rules R1–R4) |
| `stage_test.py` | The test grid for tasks 1–3 |
| `textpred.py`, `stage_text.py` | Corpora, n-gram and transformer predictors, evaluation (task 4) |
| `synth.py`, `stage_synth.py` | Sigma-lognormal extraction and synthesis; the UJI few-shot generator (task 5) |
| `shared.py`, `stage_shared.py` | Guided practice with fixed and assistance-as-needed gains (task 6) |
| `report.py`, `evidence.py` | Figures and CSV twins, `ai2.json`, `samples.json`, proposed ledger rows |
| `run_study.py` | The one command |
| `tests/test_ai2.py` | Causality (smoother, detector, learned models, extrapolation, policies), the gate on writing vs tremor, the RL environments' API, sigma-lognormal recovery, the AAN law, the ledger rows, output schemas |

## Experiments (proposed; nothing here is measured)

| Id | Purpose | Method | Measurand | Pass line (hypothesis) |
|---|---|---|---|---|
| **EXP-L01** | Does the tremor-line gate stay shut on real tremor-free writing and open on real tremor? | Replay the instrumented-pen recordings of EXP-H01 (ET/PD writers and controls; tip camera as reference) through the Rev J estimator stack offline; then on the bench pen | Gate-open share of tremor-free writing time; time to open after tremor onset; gate-open share at 1–2 mm | Open ≤ 1 % of tremor-free time for every control writer; open ≥ 80 % of pen-down time at 1–2 mm tremor after the first 5 s |
| **EXP-L02** | Does the gated listening tracker beat the Rev H tracker on real writing without moving tremor-free writing? | Same recordings; paired comparison per writer; then closed loop on the bench pen with a tremor-generating hand simulator (EXP-I07 rig) | Ink error vs tip-camera intent at 1–2 mm; letters read by the app; false correction on the controls' writing | Ink error ≤ 0.8 × Rev H's at 1–2 mm (paired 95 % CI below 1); false correction ≤ Rev H's + 2 µm; no worse at 0.3 mm |
| **EXP-L03** | How large an ink lag do writers notice, and does it cause writing errors? | Tablet with controlled inking latency (0, 12, 25, 50, 100 ms) and a stylus, then the ±6 mm bench nose; JND staircase against 7 ms while writing words (Annett 2014 method, LIT HAP-90); copy task scored for added strokes and letters (Tamada 1995, LIT HAP-91) | JND (ms); added strokes or letters per 100 letters; letter size; writing time | Delayed ink stays an option only if the median JND ≥ the lag used (25 ms) and added errors rise by < 1 per 100 letters |
| **EXP-L04** | Does a learned estimator pass REQ-ML-001 on real data? | Train on synthetic + EXP-H01 training participants; test on held-out participants against the gated model-based stack | Residual ratio by band; false correction; spikes | REQ-ML-001 (as written), with the gated stack as the conventional comparator |
| **EXP-L05** | Does the RL arbiter survive a closed-loop simulator and the bench? | Train the arbiter in sim2 (MuJoCo, closed loop, the pen's own sensors) with the estimators run online; test on held-out sim2 seeds, then on the bench rig | Ink error vs the model-based gate; false correction; gate chatter | ≥ 5 % lower ink error than the model-based gate at 1–2 mm with false correction ≤ gate's + 2 µm; otherwise keep the model-based gate |
| **EXP-L06** | Does better prediction save writing effort in the app? | 20 adults (and 10 with ET) write notes in the app with next-word completion from NG0 vs the mixture model (within-subject, counterbalanced); offline scoring on their own notes | Top-1/top-3 next-word accuracy on own notes; accepted completions per 100 words; words per minute | Accepted completions ≥ 10 per 100 words and no loss in words per minute |
| **EXP-L07** | Does synthesis from a 20 s calibration look like the user's writing? | 20 writers write the calibration pangram; the app synthesises 10 words in their style; the writer and 5 raters judge own vs synthetic (2AFC) and legibility | Legibility (recogniser and raters); own-style identification | Legibility ≥ 95 %; writers pick the synthetic word as "mine" ≥ 60 % of the time against another writer's |
| **EXP-L08** | Does assistance-as-needed fade help without hurting learning? | Guided practice (dysgraphia-like children or adults learning an unfamiliar script) with fixed partial vs AAN guidance; retention test without guidance after 1 day | Retention error vs target; device share over sessions | Retention error with AAN ≤ fixed guidance; device share falls over sessions |

## Closed-loop tuning check of the task 2–3 candidates (SIM; stage cl; tuning writers 100–103, seeds 300 and 301)

Rev H tracker on the same runs: 617 µm at 1–2 mm (6–10 Hz), tremor-free writing moved 33.5 µm.

| Candidate (lag 0, ±3 mm nose) | Ink error 1–2 mm | Tremor-free moved | Ink error 0.3 mm | Letters read 1–2 mm | Words read 1–2 mm | R1 R2 R3 R4 |
|---|---|---|---|---|---|---|
| Learned TCN (**adopted by the rules**) | 281 µm | 21.3 µm | 129 µm | 83.1 % | 78.7 % | ✓ ✓ ✓ ✓ |
| Learned TCN + 20 s calibration | 293 µm | 21.1 µm | 155 µm | 83.5 % | 81.2 % | ✓ ✓ ✓ ✓ |
| Hybrid Kalman–network | 255 µm | 51.3 µm | 145 µm | 86.3 % | 82.1 % | ✗ ✓ ✓ ✓ |
| RL arbiter (PPO, false-correction-weighted reward) | 297 µm | 60.9 µm | 168 µm | 87.0 % | 85.8 % | ✗ ✗ ✗ ✓ |
| Residual RL on the command | 383 µm | 166.9 µm | 154 µm | 77.6 % | 72.1 % | ✗ ✗ ✗ ✗ |
| Gated listening tracker (model-based) | 419 µm | 33.5 µm | 166 µm | 76.4 % | 73.3 % | ✓ ✓ ✓ ✓ |
| Learned transformer (under-trained) | 492 µm | 62.3 µm | 171 µm | 61.9 % | 44.6 % | ✗ ✗ ✗ ✗ |

- The hybrid and the RL arbiter fail on one writer's tremor-free writing (writer 101: 123 and 128 µm moved, against the tracker's 34 µm). Both lean on the listening smoother, which reads that writer's writing rhythm as tremor. The RL arbiter's mean weight on that writing was only 0.043 in replay (rule RL1 passed): it opens rarely but fully. The closed-loop check caught what the replay rule missed.
- The learned TCN moves tremor-free writing less than the Rev H tracker on 3 of 4 writers (13.8, 16.6, 18.4 µm) and slightly more on writer 101 (36.4 against 33.6 µm).
