# Touchdown and lift: stage feed-forward, stop margin and servo tuning (pencil model P1)

**Status: proposed design, tuned and checked in simulation only.** Nothing here was measured on hardware.
Evidence labels:
- **SIM**: pencil model P1, or the reduced torch model where stated, on synthetic handwriting;
- **CALC**: kinematics, loop margins or a field formula;
- **MFR**: a manufacturer statement, with its ledger id;
- **ASSUMPTION**: a model input nobody has measured.

Every simulation result below comes from `results/opt/touchdown.json`, `results/opt/servo.json` or the stage caches in `results/opt/logs/`, which record the provenance. Seed use:
- the searches ran on training seeds 300–319;
- test seeds 200–203 were used once, for the validation tables.

## 1. Short answer

**What happens now.** With the tilt-adaptive front stop alone (DEC-022, 0.30 mm margin), the ball still draws about 0.11 mm per stroke at touchdown and lift that a rigid pen would not draw. That is just above the 0.1 mm of REQ-PNC-006 (SIM).

**Why, and it is not the slide.** At 50° the refill's slide at this margin moves the ink 0.19 mm, which is inside the 0.2 mm tolerance. Most of the tail comes from the stage itself:
- the paper's load arrives as a step at contact (0.13 N sideways at 1 N and 50°);
- the servo integrator (25 Hz) and the 1 kHz slide signal are too slow for it;
- so the 575 N/m stage yields about 0.2 mm before it recovers (SIM, CALC).

**The fix is firmware: a stage feed-forward.** It uses the sensors P1 already has. Its parts:
- it pre-positions the stage while the refill rests on its stop;
- it cancels the measured slide, after removing the part the stage itself causes;
- it switches the contact-load bias at contact and hands the integrator's load share over;
- it detects the contact early from the stage Hall sensor.

**Result on the test seeds (tremor-free, SIM).** Extra ink at touchdown and lift, per stroke:

| Tilt | Tilt-range stop | Adaptive stop alone | Adaptive stop + feed-forward |
|---|---|---|---|
| 35° | 0.35 | 0.14 | 0.005 |
| 50° | 0.81 | 0.11 | 0.008 |
| 75° | 0.42 | 0.00 | 0.00 |

- Missing ink is unchanged at 0.009 mm per stroke at 50°. None of it is at touchdown or lift; it is all within strokes.

**What is left of the published metric.** The published metric (all extra ink, 5 s runs) goes from 1.15 (tilt-range stop) to 0.33 (adaptive stop), 0.23 (+ feed-forward) and 0.15 mm per stroke (+ tuned servo).
- The remainder is in-stroke: the skid pencil's letters sit about 0.14 mm RMS from the rigid pen's. It is not touchdown or lift ink.
- The touchdown-and-lift part of REQ-PNC-006 (at most 0.1 mm per stroke, and no missing ink at the transitions) is met in SIM at all three tilts.
- This law does not address the in-stroke missing ink (0.009 mm per stroke at 50°, 0.05 at 75°) or the published all-extra-ink metric.

**Cost to the tremor correction (oracle ratio at 6 Hz / 0.3 mm, SIM).**
- 50°: no cost. The ratio is 0.250 with the feed-forward, against 0.257–0.274 for the adaptive stop alone and 0.218 for the tilt-range stop.
- 35°: +0.03 (0.446 against 0.416). The tuned servo more than recovers it (0.354).
- 75°: no change.
- The stage spends 3 % more of its contact time at its travel limit at 50°.
- Rail power (class-B) rises by 11 mW at 50° and by 41 mW at 35°.

**Recommended.** An adaptive stop margin of **0.31 mm** with the law in §3.5:
- the stage pre-positions by 0.21 mm at 50° while the pen is in the air;
- in contact the feed-forward stays inside its dead zone.

The feed-forward makes the tails almost independent of the margin. The margin is therefore now a choice between correction and slow-touchdown behaviour, not tails (§3.2).

**Servo (SIM, CALC).** Retuned: integral corner 53 Hz, damping 0.32, derivative filter 654 Hz, reference feed-forward gain 1.10.
- Stage tracking error: 19.3 → 12.5 µm RMS. Rail power: 136 → 117 mW (training seeds, 1 µm Hall noise).
- The loop margins stay inside the rule (PM ≥ 45°, GM ≥ 10 dB, |S| ≤ 2):
  - the phase margin drops from 46.3° to 45.2° at nominal stiffness;
  - the gain margin and the peak sensitivity improve;
  - at ±20 % stiffness the phase margin is 44.2°, against P0.1.2's 44.0°.
- On the test grid it improves correction where the stage is off its travel limit: ratio 0.19–0.26 → 0.14–0.17 at 0.1 mm tremor. It changes nothing where travel limits (0.3–0.5 mm).

**What must be measured.** EXP-Q08 on the Q06 rig (§9). The inputs that matter most, all ASSUMPTIONS:
- the latency of the axial sensor;
- the stage's push-back at contact;
- real pen-down speeds.

## 2. How the feed-forward works

The stage already moves the nib sideways for the tremor correction. The feed-forward uses the same stage to cancel what the refill's slide does to the ink during touchdown and lift.

**Geometry (CALC).** With the ball on the page, the refill's slide `s` has two causes:
- the housing height `h`: the refill slides `−h / sin θ` as the housing comes down;
- the stage: moving the nib by `q1` in the tilt plane pushes the refill back by `q1 · cot θ`.

The ink moves along the pen's azimuth by `−h · cot θ + q1 / sin θ`. Holding the ink where it writes needs

  `q_ff = sin θ · cos θ · (s_ref − s_h)`, with `s_h = s_meas − κ · cot θ · q1,Hall`,

- `s_ref` is the working slide, about 5 µm: the skid sinks 8 µm and the ball 4 µm into the paper (CALC, `model.working_slide`).
- `κ = 1` removes the stage's own contribution from the measured slide.
- With a roll ρ the command points along `(cos ρ, −sin ρ)` in the stage axes, and the removal uses the same direction.
- These relations are tested at 35, 50 and 75° in `opt/touchdown/tests/test_touchdown.py`.

**Pre-positioning.** While the refill rests on its stop (ball in the air), the formula has a fixed point at `q_pre = (s_ref + margin) · cot θ`.
- The stage pre-deflects so the ball lands where it writes. It then returns to zero as the refill retracts, driven by the measured slide.
- At 0.30 mm margin and 50° this is 0.25 mm of the ±0.30 mm soft travel (CALC).
- The brief's 0.15 mm (`sin θ cos θ × margin`) is the law's gain on the housing-induced slide, not the pre-position. A pre-deflected ball lands higher up the descent, so it needs `margin · cot θ`.
- The search chose 81 % of it: 0.21 mm at 50°. At 35° the 0.36 mm requested is tapered at the 0.30 mm soft limit; at 75° it is 0.07 mm.
- The travel is used only in the air and during the few milliseconds of retraction, when the tremor path has no authority yet.

**Removal of the stage-induced slide.** Without it, the loop through the physical slide has gain `−cos² θ`. It is negative and stable, not the `1/sin² θ` of the brief. But the feed-forward then answers every tremor correction, because the refill slides `cot θ · q1` whenever the stage corrects.
- Test (SIM, stage cancelling a synthetic 6 Hz, 0.15 mm estimate, pen held on the page):
  - with `κ = 1`: the housing-slide estimate stays within 9 µm of `s_ref` while the stage moves 260 µm peak to peak, and the feed-forward stays at zero;
  - with `κ = 0`: the estimate swings 90 µm and the feed-forward commands up to 35 µm.
- On handwriting with tremor, dropping the removal raises the oracle ratio from 0.212 to 0.316 (held-out training seeds). **This is the one element the correction cannot do without.**
- The Hall sample is taken at the axial sample's acquisition time; the axial sensor lags 1 ms (ASSUMPTION).

**Prediction and dead zone.** The axial slide is sampled at 1 kHz with 1 ms delay (ASSUMPTION).
- An alpha-beta tracker (bandwidth `lp`) estimates `s_h` and its rate. The law can use `s_h` predicted `lead` ahead.
- A dead zone `dz` on `s_ref − s_h` keeps the law silent in steady writing.
- Without a dead zone, the sensor noise (amplified by any lead) reaches the stage command and dithers the ball's friction. With 2 ms lead at 400 Hz and no dead zone (held-out seeds, SIM):
  - in-stroke extra ink 0.18 → 1.93 mm per stroke;
  - missing ink 0.008 → 0.87 mm per stroke.
- **The search set the lead to zero** (tracker 54 Hz, dead zone 33 µm): in P1, prediction costs more in noise than it gains in latency.

**Contact-load bias.** The paper's normal force pushes the stage back by `N_nib · cos θ` at contact: 0.13 N at 1 N and 50°, 0.19 N at 35°. That is 0.22 mm against the 575 N/m stage if nothing reacts (CALC). The P0 servo's integrator (25 Hz corner) needs about 6 ms to answer.
- P1's existing static bias ramps in over 50 ms after the axial sensor reports contact 0.1 mm off the stop.
- The feed-forward instead switches it at once, on its own contact state (refill 20 µm off its stop), with gain `k_load`.
- **Load hand-over:** at that moment the integrator gives up the share of the load it already carries; at lift it drops its negative share.
- Quasi-static touchdown at 1 mm/s, ideal gains, noise off (SIM; `mechanism_checks.quasi_static_1mm_s`):
  - with the hand-over the ink point stays within 5.7 µm RMS of its working position (median 5.7 µm while the refill slides, 0.02 µm at the end), with a 24 µm transient at the contact instant;
  - without the hand-over: 15 µm RMS and a 78 µm peak;
  - without the feed-forward: 83 µm RMS and a 226 µm peak.

**Early contact detection.** A detector on the Hall error along the load direction (threshold `det_e`) switches the bias early. It switches the contact state within 0.5 ms of contact (SIM, 2 kHz record; `mechanism_checks.contact_detection_delay`). The slide alone is slower:
- at handwriting touchdowns it takes 4.5–5 ms;
- at 10 mm/s it takes 8.5 ms;
- at 1 mm/s neither fires quickly, because the load builds slowly and the servo keeps the error small.

The detector has two rules:
- it is armed only after the error has stayed inside a quiet band for `hold`;
- it fires only when the threshold is crossed within 1 ms of leaving that band.

These rules exist because a first version chattered: a bias step in the air excites the lightly damped stage, and the free oscillation re-triggered the detector. This is the failure family of DEC-011 (§6).

**Travel sharing.** The feed-forward bypasses the 50 ms authority ramp of the tremor path. It shares the ±0.30 mm soft travel with the tremor command by one of three rules:
- shared: the sum is tapered;
- feed-forward first: the tremor command gets what is left;
- tremor first.

The code is in `sim/pencil/core.py` (td_* path). The parameters are `PencilConfig(touchdown_ff={...})`, and they are off by default.

## 3. What the optimisation found

### 3.1 Adjoint gradients on a reduced model: which parts matter

`opt/touchdown/reduced.py` is a planar, differentiable touchdown model in torch with P1's parameters:
- hand impedance, skid, refill slide on its spring and stop;
- ball contact with regularised friction;
- a second-order stage;
- sampled sensors, the servo, and the law with P1's taper.

Gradients come from backpropagation through time (the discrete adjoint). They agree with central finite differences within 0.2 % at a step of 0.001 (test `test_reduced_model_adjoint_gradient_matches_finite_differences`).

The loss is rough at the scale of a few percent of a gain, because contact and stop switching make it jump. Central differences at a 2 % step give −17 against the adjoint's −29 for the gain, and they converge to it as the step shrinks. The adjoint gradient is therefore local: it guides Adam, and it cannot find a global optimum. This is one reason the P1 values come from the Bayesian search.

It reproduces P1 on a down-up event (ideal law): touchdown at 33.7 ms against 33.8 ms, and slide RMS difference 6 µm over a 338 µm range (SIM; `fig_td_adjoint.png`).

Adam on the adjoint gradient, loss = RMS ink deviation in contact over down-up events at 0 and 20 mm/s (SIM, reduced model):

| Law structure | RMS ink deviation (µm) |
|---|---|
| no feed-forward | 91 |
| ideal law, gains 1 | 37 |
| fitted, full structure | 24 |
| fitted, no pre-positioning | 70 |
| fitted, no lead | 24 |
| fitted, no slide removal | 22 |
| fitted, no integrator hand-over | 28 |

**What this showed.**
- Pre-positioning is the element that matters most.
- The lead adds nothing once the gains are fitted.
- The hand-over is worth a few µm.
- The slide removal is irrelevant without tremor. It matters for the correction under tremor, which this loss does not see.

**Moved into P1 (held-out training seeds), the reduced model's optimum is a different trade-off, not a better law.** Against the Bayesian pick:
- slow touchdowns are better: peak 37 / 18 µm against 65 / 70 µm at 1 / 10 mm/s;
- the handwriting tail is larger: 0.020 against 0.012 mm per stroke;
- correction is worse: ratio 0.251 against 0.212;
- it makes three contact transitions in the 1 mm/s descent (a bounce);
- its gains sit on the P1 search bounds (gain 1.3, κ 0.5, pre 1.2), a sign of model mismatch.

The adjoint model therefore set the structure and the bounds, and the Bayesian search on P1 set the values.

### 3.2 Bayesian optimisation on P1: law and margin together

`opt/touchdown/study_bo.py` searches 11 parameters jointly with ParEGO: a Gaussian process with its own Matérn-5/2 ARD kernel and expected improvement. The parameters are:
- the margin, 0.10–0.40 mm;
- gain, κ, pre-positioning, lead, tracker bandwidth, dead zone, load-bias gain;
- the Hall threshold, hold time, and an assumed descent speed.

124 P1 evaluations were run on search seeds 300–309 at 50°. Each evaluation is ten 5.2 s handwriting runs, tremor-free and 6 Hz / 0.3 mm with the oracle.

**Objectives.**
- Touchdown objective:
  - tail ink at 0.2 mm tolerance;
  - plus a quarter of it at 0.1 mm;
  - plus missing ink beyond 0.03 mm (×2);
  - plus a guard on in-stroke drift;
  - plus half the mean peak contact-point deviation of slow touchdowns at 1 and 10 mm/s.
- Correction objective: the oracle ratio, plus the contact time at the travel limit beyond 13 %.

**Pick rule.** The three lowest touchdown objectives whose ratio is at most the adaptive stop's 0.266 + 0.01 were re-scored on held-out seeds 310–319, and the best was kept. The second and third candidates (0.33 mm margin) were close. The pick scored:
- tail 0.012 mm per stroke;
- 0.068 mm at 0.1 mm tolerance;
- missing 0.008 mm;
- ratio 0.212.

**Pareto front: tail ink against correction ratio, with the margin (SIM, search seeds 300–309, 50°; `fig_td_pareto.png`).** The feed-forward rows are the non-dominated laws in (ratio, tail). The slow touchdowns are the hand lowering the pen at 1 and 10 mm/s.

| Front stop and law | Oracle ratio | Tail ink (mm per stroke) | Slow touchdown peak, 1 / 10 mm/s (µm) | Contact time at the travel limit |
|---|---|---|---|---|
| stop alone, 0.10 mm | 0.70 | 0.015 | 103 / 164 | 0.02 |
| stop alone, 0.20 mm | 0.43 | 0.065 | 165 / 250 | 0.06 |
| stop alone, 0.30 mm | 0.27 | 0.117 | 228 / 312 | 0.14 |
| stop alone, 0.40 mm | 0.20 | 0.151 | 290 / 374 | 0.28 |
| tilt-range stop | 0.20 | 0.874 | 882 / 917 | 0.28 |
| feed-forward, 0.40 mm | 0.20 | 0.020 | 53 / 142 | 0.29 |
| feed-forward, 0.35–0.36 mm | 0.23 | 0.007–0.013 | 140–148 / 124–166 | 0.11–0.13 |
| feed-forward, 0.32 mm | 0.25 | 0.006 | 145 / 100 | 0.09 |
| feed-forward, 0.26 mm | 0.31 | 0.002 | 101 / 132 | 0.09 |
| feed-forward, 0.17 mm | 0.51 | 0.000 | 99 / 114 | 0.04 |
| **the pick, 0.31 mm** | **0.24** | **0.010** | **65 / 70** | **0.16** |

**What the front shows.**
- Without feed-forward the margin trades tails against correction.
- With it the tails stay at 0.002–0.02 mm across margins. A 0.40 mm stop with the feed-forward matches the tilt-range stop's correction (0.20) with 2 % of its tail.
- The pick has the best slow touchdowns of the laws on the front: a mean peak of 68 µm over the two speeds, against 97–196 µm for the others.
- At 0.38–0.40 mm the stage sits at its travel limit for 28–29 % of the contact time, as with the tilt-range stop.
- **If correction matters more than slow touchdowns, a 0.35–0.40 mm margin is the alternative**, at about twice the slow-touchdown deviation. It was not re-checked on held-out seeds. The test seeds point the same way for correction and tails (§4.4).

### 3.3 What each element buys (held-out training seeds 310–319, 50°, SIM)

| Removed from the pick | Tail 0.2 / 0.1 mm tol. (mm per stroke) | Missing | Oracle ratio | Slow touchdown peak, 1 / 10 mm/s (µm) |
|---|---|---|---|---|
| nothing (the pick) | 0.012 / 0.068 | 0.008 | 0.212 | 65 / 70 |
| Hall contact detection | 0.012 / 0.130 | 0.008 | 0.212 | 65 / 154 |
| pre-positioning | 0.033 / 0.142 | 0.007 | 0.211 | 236 / 239 |
| lead (already zero) | 0.012 / 0.068 | 0.008 | 0.212 | 65 / 70 |
| dead zone | 0.007 / 0.067 | 0.012 | 0.216 | 65 / 70 |
| slide removal | 0.015 / 0.083 | 0.008 | **0.316** | 85 / 88 |
| integrator hand-over | 0.022 / 0.075 | 0.008 | 0.212 | 161 / 70 |
| bias switch (P1's 50 ms ramp instead) | 0.049 / 0.193 | 0.010 | 0.223 | 65 / 173 |
| (added) 10 kHz, 0.1 ms slide sensor | 0.011 / 0.064 | 0.008 | 0.206 | 65 / 70 |

For comparison, the stop alone on the search seeds: 0.30 mm gives tail 0.117 / 0.262 and slow peaks 228 / 312 µm; the tilt-range stop gives 0.874 / 1.036 and 882 / 917 µm.

**What each element is for.**
- **Pre-positioning and the switched load bias make the tail.**
- **The slide removal protects the correction.**
- **The hand-over and the Hall detection protect slow touchdowns.**
- The dead zone costs a little tail but keeps the in-stroke ink and the missing ink down; the dither check above shows what happens without it.
- A faster slide sensor adds almost nothing once the Hall detection is in.

### 3.4 Travel sharing

The three priority rules gave the same result on the search seeds: ratio 0.2391 / 0.2389 / 0.2387 and tail 0.0101 mm (SIM). The two commands rarely overlap:
- the feed-forward acts in the air and in the first milliseconds of contact, before the tremor path's 50 ms authority ramp;
- in steady writing it sits in its dead zone.

**Feed-forward first** is kept because it is the simplest to reason about, and the pre-position is never cut by the tremor command.

### 3.5 Recommended law (PROPOSED DESIGN, tuned in SIM)

| Parameter | Value | Meaning |
|---|---|---|
| margin | 0.313 mm | adaptive front stop beyond the protrusion the current tilt needs |
| gain | 0.958 | on `sin θ cos θ (s_ref − s_h)` |
| κ (`kappa`) | 0.887 | removal of the stage-induced slide |
| pre | 0.811 | fraction of `q_pre` held in the air (0.21 mm at 50°) |
| lead | 0 ms | no prediction beyond the tracker |
| lp | 54 Hz | alpha-beta tracker bandwidth |
| dz | 33 µm | dead zone on the slide error |
| k_load | 1.147 | contact-load bias, × `N_nib0 cos θ`, switched at contact |
| det_s | 20 µm | refill off its stop = contact (fixed) |
| det_e | 30 µm | Hall error along the load direction = early contact |
| hold | 1 ms | quiet time before the Hall detector is armed |
| v_td | 0 | no assumed descent speed after a Hall detection |
| prio / bias / handover | 1 / 1 / 1 | feed-forward first; bias switched; integrator hand-over |

In code: `opt.touchdown.law.TouchdownLaw(**touchdown.json['recommended']['law'], **fixed).pencil_config()`.

## 4. Validation on the test seeds (200–203, first use, SIM)

### 4.1 50°, tremor-free (`fig_td_tails.png`)

Ink in mm per rigid pen-down. The "published metric" is `sim/pencil/diag_touchdown_tails.py` on 5 s runs.

| Configuration | Tail at touchdown and lift | In-stroke extra | All extra | Published metric | Missing | Oracle ratio | Kalman ratio | Oracle time at limit |
|---|---|---|---|---|---|---|---|---|
| Tilt-range stop (P0.1.2) | 0.813 | 0.157 | 0.970 | 1.15 | 0.009 | 0.218 | 0.99 | 0.27 |
| Adaptive stop 0.30 mm alone (DEC-022) | 0.114 | 0.166 | 0.280 | 0.33 | 0.010 | 0.274 | 1.00 | 0.14 |
| Adaptive stop 0.31 mm alone | 0.117 | 0.169 | 0.285 | 0.34 | 0.010 | 0.257 | 1.00 | 0.16 |
| **Adaptive 0.31 mm + feed-forward** | **0.008** | 0.171 | 0.179 | 0.23 | 0.009 | 0.250 | 1.00 | 0.17 |
| + tuned servo (§5) | 0.009 | 0.087 | 0.096 | 0.15 | 0.010 | 0.249 | 1.00 | 0.18 |
| + 10 kHz slide sensor (option, §7) | 0.007 | 0.179 | 0.186 | 0.23 | 0.012 | 0.245 | 1.00 | 0.17 |

**Notes on the table.**
- At 0.1 mm tolerance the tails are 0.949 / 0.242 / 0.059 mm per stroke (tilt-range / adaptive / + feed-forward).
- None of the missing ink is within 30 ms of a contact transition.
- The in-stroke column counts ink more than 0.2 mm from the rigid pen's, on a distortion of about 0.14 mm RMS. It reacts strongly to small changes: the tuned servo halves it by lowering the in-stroke RMS only from 135.9 to 133.4 µm. Treat that halving as fragile.
- The frozen Kalman gives no correction at 6 Hz / 0.3 mm here (0.99–1.00; the published P1 grid has 0.996).

### 4.2 35° and 75° (`fig_td_tilt.png`)

Each cell: tail / missing ink (mm per stroke) / oracle ratio.

| Configuration | 35° | 50° | 75° |
|---|---|---|---|
| Tilt-range stop | 0.347 / 0.000 / 0.27 | 0.813 / 0.009 / 0.22 | 0.419 / 0.056 / 0.41 |
| Adaptive stop 0.30 mm alone | 0.135 / 0.000 / 0.42 | 0.114 / 0.010 / 0.27 | 0.000 / 0.051 / 0.28 |
| Adaptive 0.31 mm + feed-forward | 0.005 / 0.000 / 0.45 | 0.008 / 0.009 / 0.25 | 0.000 / 0.050 / 0.28 |
| + tuned servo | 0.012 / 0.003 / 0.35 | 0.009 / 0.010 / 0.25 | 0.000 / 0.028 / 0.28 |

**What changes with tilt.**
- At 75° the slide at this margin moves the ink only `margin · cos θ` = 0.08 mm, so the adaptive stop alone has no tail.
- The missing ink at 75° is in-stroke and present in every configuration.
- The feed-forward's correction cost appears at 35° (+0.03). The likely causes are that the pre-position is cut there by the travel limit and that the load step is larger (0.19 N); this was not isolated. The tuned servo recovers it.
- Rail power (class-B, oracle) with the feed-forward against the adaptive stop alone: +11 mW at 50° (144 against 133 mW), +41 mW at 35° (172 against 131 mW), +5 mW at 75°.

### 4.3 Under 6 Hz / 0.3 mm tremor

Against the rigid pen's tremor-free ink, 50°, mm per stroke (SIM). Each cell: tail / all extra / missing.

| Configuration | Oracle | Frozen Kalman |
|---|---|---|
| Tilt-range stop | 0.824 / 1.89 / 0.50 | 0.993 / 5.61 / 2.49 |
| Adaptive stop 0.30 mm alone | 0.160 / 1.55 / 0.65 | 0.266 / 4.88 / 2.52 |
| Adaptive 0.31 mm + feed-forward | 0.140 / 1.38 / 0.62 | 0.156 / 4.75 / 2.47 |
| + tuned servo | 0.126 / 1.27 / 0.61 | 0.153 / 4.69 / 2.47 |

**Reading this table.**
- With tremor, the residual tremor error dominates every column, and it also lands near the transitions.
- The feed-forward still cuts the tails with a live estimator driving the stage (Kalman: 0.27 → 0.16).
- At 50° it does not degrade the tremor correction (§4.1).

### 4.4 Tilt changes

P1 cannot run a tilt that changes during a run:
- θ is one scalar per run;
- the housing frame, the nominal protrusion, the initial height and the stop position are set once;
- there is no model of the trim actuator or of the IMU's tilt estimate.

**What a tilt sweep needs:**
- P1 with θ(t) as a scheduled input (frame vectors and contact geometry per step);
- a trim-actuator model (rate limit and position error; SQUIGGLE class, AMF-15) driving `s_min(t)`;
- the IMU tilt estimate (latency, noise) feeding the stop and the law's `sin θ cos θ` and `cot θ`.

**The proxy that stands in.** A stop that lags a tilt change is a stop set for the wrong tilt. So the test seeds were run at 50° with the stop set for 50° ± 2° and ± 5°: 0.035 mm of margin per degree at 50° (CALC).

| Stop set for | Effective margin | Adaptive stop alone: tail / ratio | + feed-forward: tail / ratio |
|---|---|---|---|
| 45° | 0.50 mm | 0.197 / 0.219 | 0.015 / 0.219 |
| 48° | 0.39 mm | 0.139 / 0.218 | 0.011 / 0.219 |
| 52° | 0.25 mm | 0.093 / 0.357 | 0.007 / 0.352 |
| 55° | 0.15 mm | 0.027 / 0.540 | 0.001 / 0.545 |

**With the feed-forward, a loose stop is harmless and a tight stop costs correction.**
- The trim actuator should err loose.
- The same test shows a looser nominal margin (0.39–0.50 mm) keeping tails at 0.011–0.015 mm with the tilt-range stop's correction. This agrees with the training Pareto front (§3.2). Slow touchdowns were not part of this test, and it was not used to pick the margin.

### 4.5 Contact events

With the feed-forward the pencil makes more contact transitions per rigid pen-down: 1.7 at 50°, against 1.2 for the adaptive stop alone.

The extra events are short re-contacts right after lift-off, when the bias drops and the stage moves to its pre-position. Training seeds 300–303 (SIM; `mechanism_checks.contact_events_training`):

| Tilt | Pen | Touchdowns | Contact gaps under 30 ms | Longest gap | Highest separation |
|---|---|---|---|---|---|
| 50° | feed-forward | 16 | 7, all single re-contacts just after lift-off | 0.5 ms | 1 µm |
| 50° | adaptive stop alone | 12 | 3 | 0.5 ms | 0.3 µm |
| 35° | feed-forward | 21 | 12, mostly short chains after lift-off | 2 ms | 16 µm |
| 35° | adaptive stop alone | 10 | 1 | 0.5 ms | 0.1 µm |
| both | rigid pen (touchdown bounce) | 18 | 9 | 2.5 ms | 17 µm |

Their ink is inside the tails above. A bias ramp of a few milliseconds at lift would likely remove them (untested). EXP-Q08 must count contact events.

## 5. Servo

**What was tuned.**
- The integral corner `servo_bw`, 10–150 Hz.
- The damping `servo_zeta`, 0.2–1.
- The derivative filter `d_filt_hz`, 200–3000 Hz.
- The reference feed-forward gain `ff_ref`, 0.8–1.1.
- A new proportional term `servo_kp`, 0–0.6 × k. It is a new `PencilConfig` field, 0 by default.

**Objectives.** Stage tracking error in contact (the mean of the oracle run and the tremor-free neutral run) against the class-B rail power. Training seeds 300–305 at 1 µm and 0.3 µm Hall noise, ParEGO with 56 evaluations each.

**Constraint (CALC, `opt/touchdown/servo.py`, same loop model as `sim/pencil/run_study.servo_check`).**
- Loop model: ZOH, 0.1 ms Hall delay, 2 kHz driver pole.
- Every proposal must meet, at open-loop damping 0.02–0.1 and nominal stiffness: phase margin ≥ 45°, gain margin ≥ 10 dB, peak |S| ≤ 2.
- The picks must also keep at ±20 % stage stiffness a phase margin no lower than P0.1.2's own worst case (44.0°).
- A first pick under the nominal rule alone (bw 62 Hz) fell to 41.8° there. It was replaced; its test results are kept in `servo.json` (`nominal_rule_pick_test_results`).
- One front point at 0.3 µm noise had only 7° at ±20 %. The robustness check is not optional.

**Results (training seeds, SIM; `fig_td_servo.png`).**

| Hall noise | Servo | bw (Hz) | ζ | D filter (Hz) | ff_ref | Tracking (µm RMS) | Rail power class-B / recovery (mW) | PM nominal / ±20 % (°) | GM (dB) | peak \|S\| |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 µm | P0.1.2 | 25 | 0.40 | 600 | 1.00 | 19.3 | 136 / 25 | 46.3 / 44.0 | 14.3 | 1.62 |
| 1 µm | **tuned (recommended)** | **53.3** | **0.321** | **654** | **1.10** | **12.5** | **117 / 21** | 45.2 / 44.2 | 16.5 | 1.56 |
| 1 µm | lowest power at default tracking | 44.5 | 0.256 | 657 | 1.10 | 13.9 | 93 / 17 | 46.3 / 44.2 | 18.9 | 1.50 |
| 0.3 µm | P0.1.2 | 25 | 0.40 | 600 | 1.00 | 19.8 | 57 / 11 | 46.3 / 44.0 | 14.3 | 1.62 |
| 0.3 µm | tuned | 60.4 | 0.336 | 692 | 1.10 | 12.0 | 56 / 10 | 45.1 / 44.2 | 16.2 | 1.55 |
| 0.3 µm | lowest power at default tracking | 26.1 | 0.255 | 541 | 0.94 | 19.7 | 42 / 8 | 47.3 / 45.8 | 18.5 | 1.53 |

The proportional term `servo_kp` stayed at or near zero in the picks (at most 0.006 k); it appears only at the high-power end of the front. `ff_ref` sits at its upper bound (1.10), so the true optimum may lie above it; the cause is not identified.

**Test grid (tilt-range stop as in the P1 study; 4–12 Hz × 0.1 / 0.3 / 0.5 mm × seeds 200–203, SIM), 1 µm Hall noise.**
- The mean oracle ratio goes 0.356 → 0.328 with the tuned servo, at 139 → 121 mW class-B (25 → 22 mW with charge recovery).
- The time at the travel limit is unchanged (0.369 → 0.370).
- The gain is all at 0.1 mm tremor, where the stage is off its limit: ratio 0.19–0.26 → 0.135–0.17.
- At 0.3 and 0.5 mm the ratio is set by the travel and moves by at most ±0.013.
- At 0.3 µm Hall noise: 0.360 → 0.327 at the same power (61 → 62 mW).

With the feed-forward (§4) the tuned servo also brings the 35° oracle ratio from 0.446 to 0.354.

## 6. Firmware: what the pen must sense and compute

| Task | Input | Rate | Work |
|---|---|---|---|
| Housing-slide estimate | axial slide `s` (1 kHz, 1 ms delay assumed); Hall `q` at the matching time (ring buffer at 10 kHz) | 1 kHz | `s_h = s − κ cot θ (u·q)`; alpha-beta update |
| Law | `s_h`; tilt θ and roll ρ from the IMU (slow); the stop margin | 2 kHz (outer loop) | dead zone, `q_ff`; in the air `pre · q_pre`; feed-forward-first taper with the tremor command; slew limit |
| Contact state and load bias | `s` against the stop; Hall error along the load direction | 10 kHz (servo) | two thresholds, quiet and debounce timers; at each switch the integrator hand-over |
| Working slide `s_ref` | `s` during steady writing | slow | median of `s` while the skid carries the pen, or the static value (5 µm) |

**Cost and needs.**
- A few tens of operations per millisecond (CALC).
- No new sensor: the axial contact sensor, the stage Hall sensors and the IMU tilt are in P1 already.
- Calibrate per pen:
  - `s_ref`;
  - the stop position against the IMU tilt;
  - the contact-load direction (from the roll);
  - the Hall zero.
- The servo settings of §5 replace the P0.1.2 ones, after the stage is identified on the bench (EXP-Q04/Q07).

**Relation to DEC-011.** DEC-011 removed a contact feed-forward from the delayed measured axial force, because it made the nib bounce. The load bias here is different:
- it is a fixed value, `k_load · N_nib0 cos θ` from the tilt, switched by the contact state;
- the integrator hands over its share, so the total force does not step twice.

It works on the same mechanism, though. The Hall-detector chatter met during development and the lift-off re-contacts of §4.5 belong to the same family. **Bench bounce counts decide.**

## 7. Hardware option: a faster slide sensor

In P1 a slide sensor on the servo's 10 kHz, 0.1 ms path adds almost nothing to the recommended law:
- test seeds: tail 0.007 against 0.008 mm per stroke;
- held-out seeds: 0.011 against 0.012, slow touchdowns unchanged.

The Hall contact detection already covers the contact instant. The sensor is a **fallback** in two cases:
- if the bench shows the axial sensor slower than assumed;
- if the Hall detection proves unreliable.

**Candidate parts.**
- A 1 × 1 mm N45 magnet on the refill collar (AMF-72).
- Read by a linear Hall sensor: DRV5055, 20 kHz, 2 mA (AMF-70).
- Or read by a TMR sensor: TMR2615x, 30 kHz, 240 µA, 1.6 × 1.6 mm (AMF-71).

At 1.5 mm from the magnet the field is 21 mT and its gradient about 32 mT/mm (CALC, on-axis cylinder formula). The DRV5055's noise density (MFR, AMF-70) then corresponds to about 0.5 µm RMS of slide over 5 kHz (CALC), against 2 µm assumed for today's sensor. Over ±0.5 mm of slide around the 1.5 mm stand-off the field spans about 11–50 mT (CALC), so choose the sensitivity grade whose range covers it.

**Risks:**
- the magnet's field at the stage Hall sensors (crosstalk);
- the TMR part's 2 %FS hysteresis;
- the Hall part's 6.6 mW.

## 8. Assumptions (every one untested)

| Assumption | Value in P1 | Why it matters here | Checked by |
|---|---|---|---|
| Axial slide sensor | 1 kHz, 1 ms delay, 2 µm noise | latency of the feed-forward's contact state and slide signal | EXP-Q08 step 0 |
| Stage Hall sensing | 10 kSPS, 0.1 ms delay, 1 µm (and 0.3 µm) noise | early contact detection; servo noise power | EXP-Q04, Q06 |
| Stage | 575 N/m, 0.40 g at the nib, open-loop damping 0.05, Bouc-Wen hysteresis (≈12 % loop width) | how far the contact load pushes the stage before the servo answers; the servo margins | EXP-Q04, Q06, Q07 |
| Refill | spring 25 N/m with 0.15 N preload, bushing friction 0.08, axial damping ratio 0.3 | when the refill leaves its stop; the load while it retracts | EXP-Q06 (axial load cell) |
| Contact | paper 50 kN/m, skid 100 kN/m, LuGre friction (μ 0.15 nib, 0.12 skid) | the load step at contact, the ball's stick, the device distortion | EXP-Q01, B01 |
| Hand and writing | two-stage impedance; pen-down as a 60 ms, 1.5 mm ramp, which reaches the page at 54–60 mm/s (SIM, `contact_events_training.pen_down_speed_mm_s`); slow touchdowns tested separately at 1 and 10 mm/s | the speed of touchdown | EXP-H01 |
| Tilt | constant within a run; the adaptive stop sits exactly at its margin | the margin is exact; a lagging stop is only approximated (§4.4) | EXP-Q08 tilt sweep |
| Writing force | 1 N; the skid carries 0.80 N at 50° | the working slide `s_ref` and the load step | EXP-Q06 |

## 9. Experiments needed

**EXP-Q08 on the Q06 rig: proposed additions.** `validation/bench_protocols.md` §33 stays the source of truth.

**Conditions.**
- Adaptive stop at 0.31 mm and at 0.40 mm, each with the feed-forward on and off.
- The tilt-range stop, for reference.
- θ 35, 50 and 75°.
- Servo at the P0.1.2 and at the tuned settings.

**Pen-downs.**
- The robot's pen-down speed at 1, 10 and 50 mm/s, besides writing strokes.
- Lifts straight up and along the axis.

**Step 0: identify the latencies.** Log the axial sensor, the stage Hall and an LDV on the collar at 20 kHz during 50 touchdowns. Measure:
- the axial sensor's delay;
- the time from contact to the refill leaving its stop;
- the stage's push-back at contact, without and with the switched bias.

Put these into P1:
- the axial rate and delay through `PencilConfig(overrides={"ax_decim": n, "ax_delay": n})`;
- the stage stiffness and damping in `config/pencil.yaml`.

Then re-run `python3 -m opt.touchdown.run_study` before the scans.

**Measurands (as §33, plus):**
- tail ink per touchdown and per lift, separately (R3 scans, blind, against the rigid holder's ink);
- peak contact-point deviation in the slow pen-downs (camera or LDV on the ball holder);
- contact events per pen-down (electrical continuity through a conductive trace, or acoustic);
- the stage command's travel at touchdown;
- rail power.

**AC-Q08-01 as written counts all extra ink.** With the feed-forward its prediction is 0.23 mm per stroke (0.15 with the tuned servo), still above 0.1 mm, because of the in-stroke distortion; the tails alone are 0.008 mm (SIM). Split the measurand into tails (within 30 ms of a transition) and in-stroke ink, so the requirement tests what it is about.

**Acceptance (proposed, beside AC-Q08-01..03):**
- tail ink ≤ 0.1 mm per stroke at the 95th percentile with the feed-forward (REQ-PNC-006);
- no missing ink within 30 ms of a transition;
- peak contact-point deviation ≤ 50 µm at 1 and 10 mm/s;
- no more contact events per pen-down than the rigid reference;
- oracle ratio no worse than the adaptive stop alone by more than 0.02.

**Dependencies:**
- the Q06 rig with a second axis or the Q07 two-axis stage;
- firmware with the td_* law (reference implementation `sim/pencil/core.py`);
- the axial sensor;
- the trim actuator of DEC-022;
- for the hardware option, a DRV5055 or TMR2615 on the collar with a 1 × 1 mm magnet (AMF-70..72).

**Also needed.**
- EXP-H01: real pen-down speeds and lift directions of the target writers.
- EXP-Q04/Q07: stage stiffness and damping, which set the push-back and the servo retune.

## 10. Files, how to run, tests

| What | Where |
|---|---|
| Feed-forward in the simulator (default off) | `sim/pencil/core.py` (td_* path), `sim/pencil/layout.py` (td_* parameters, recorded `qff1`, `qff2`, `td_sh`, `td_state`), `sim/pencil/model.py` (`PencilConfig.touchdown_ff`, `servo_kp`, `working_slide`) |
| Default runs unchanged, bit for bit | `sim/pencil/tests/test_default_regression.py` against `sim/pencil/tests/data/p1_default_baseline.npz` (recorded before any change, git 410a173) |
| Law and kinematics, metrics, P1 runs | `opt/touchdown/law.py`, `metrics.py`, `runs.py` |
| GP / ParEGO / CMA-ES; searches | `opt/touchdown/bo.py`, `study_bo.py` |
| Reduced model and adjoint study | `opt/touchdown/reduced.py` |
| Servo margins and scoring | `opt/touchdown/servo.py` |
| The study | `python3 -m opt.touchdown.run_study`: stages adjoint, baseline, bo, servo, validate, checks, viz, figures, report; about 1.5 h on 2 processes; `--stages` to pick; `--quick` for a smoke run. Caches and BO logs are in `results/opt/logs/`. |
| Fast tests | `python3 -m pytest -q opt/touchdown/tests` |
| Results | `results/opt/touchdown.json`, `results/opt/servo.json`, `results/opt/fig_td_{tails,pareto,event,tilt,adjoint,servo}.png` |
| 3-D replay | `results/opt/viz_touchdown.json`: viz_trace schema, seed 200, 50°, no tremor, 1.4–4.4 s with two lifts and two touchdowns; tilt-range stop, adaptive stop alone, adaptive stop + feed-forward |
| Ledger rows | `results/opt/touchdown_evidence_rows.csv` (ACT-56..60, AMF-70..72), for the lead to merge into `docs/evidence.csv` |

**For the lead to update (not edited here):**
- REQ-PNC-006 status: tails 0.005–0.008 mm per stroke with the feed-forward (SIM); the published metric 0.23 (0.15 with the tuned servo);
- DEC-022: margin 0.31 mm with the feed-forward, and err loose;
- `config/pencil.yaml` servo entries.
