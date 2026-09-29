### T1. Letters recognised while being written (20 UJI test writers, 1,040 letters; CALC)

| Recogniser and letters | 30 % written | 50 % | 70 % | whole letter | top-3, whole letter |
|---|---|---|---|---|---|
| New writer, clean | 32 % | 52 % | 70 % | 82 % | 94 % |
| New writer, 0.3 mm tremor | 30 % | 48 % | 67 % | 80 % | 93 % |
| New writer, 1 mm tremor | 17 % | 37 % | 55 % | 73 % | 90 % |
| Calibrated (writer's own letters), clean | 38 % | 60 % | 75 % | 86 % | n/a |
| Calibrated, 1 mm tremor | 20 % | 41 % | 61 % | 76 % | n/a |
| Other writer and tablet (Character Trajectories, 2,858 letters) | 28 % | 46 % | 55 % | 40 % | 65 % |

Commit rule (O2, tau 0.9): 59 % of letters committed before or at their end, commits right 94.3 %, median 70 % of the letter written at commit.
Calibrated: 22 % committed, right 99.1 %, median 78 % written; committed before the letter's end: 19 %.
With the text predictor's next-letter prior (beta 0.5, rule O3), letters in Tatoeba test sentences: half letter 54 % -> 74 %, whole letter 82 % -> 88 % (7255 letters).
Size and speed: 114,842 parameters (112 kB int8, 449 kB float32); 113,568 multiply-accumulates per point; 0.19 ms per point on this container's CPU (one thread), 7.5 ms for a median letter; 1.79 ms per point on a 128 MHz Cortex-M33 (int8, CALC).

Variants on the test writers, for information only (the choice was made on tuning writers, rule O1): whole-letter top-1 clean / 1 mm tremor: base 81 % / 41 %; tremor 82 % / 73 %; full 83 % / 74 %

### T2. The spelling checker on 11 test children's real writing (Holbrook; CALC)

| Measure | Value |
|---|---|
| Misspelled words (scored) | 1879 |
| Correctly spelled words | 12242 |
| Caught (flag while writing or at the word's end) | 63 % |
| False alarms per 100 correct words | 2.3 |
| Caught non-word errors | 1028 of 1116 |
| Caught real-word errors | 156 of 763 |
| Flag on the first wrong letter / one letter later / two or more later | 42 % / 28 % / 28 % |
| Right word first / in the top 3 (caught single words) | 59 % / 77 % |
| With the next word as context (one word later) | caught 67 %, 2.9 false alarms per 100 |
| Pen-lift threshold (mid-word only, rule S3) | caught 35 %, 0.29 false lifts per 100 |

Earliest letter (single-word errors, n = 1773): the first wrong letter is letter 3 (median; 75 % of the word); 17 % of errors only show at the word's end (the child wrote the start of the right word); the written letters stop being the start of ANY dictionary word at letter 5 (median), and 51 % never do (real-word errors).

Rules: alpha 0.063 (tuning children's error share); p_oov 0.01; theta 0.3; theta_w 0.9999. Lexicon 32,531 words, covering 98.4 % of the children's intended words; 10.3 ms per letter on this CPU.

Birkbeck test misspellings placed in CC0 sentences (3068 words, 4 % misspelled): caught 82 %, 6.3 false alarms per 100, right word in the top 3 81 %.
Letters read by the recogniser (writer_independent, 19 % letter errors): caught 77 %, 40.6 false alarms per 100 correct words (724 errors, 4767 correct words).
Letters read by the recogniser (calibrated, 15 % letter errors): caught 76 %, 38.7 false alarms per 100 correct words (724 errors, 4767 correct words).

| Test child | Words misspelled | Caught | False alarms per 100 |
|---|---|---|---|
| Nigel Thrush | 12 % | 63 % | 3.1 |
| George Green | 14 % | 71 % | 3.8 |
| John Young | 9 % | 66 % | 1.4 |
| Roger Scott | 12 % | 59 % | 1.9 |
| James Carr | 16 % | 69 % | 1.5 |
| Tom Sullivan | 8 % | 49 % | 2.4 |
| Rose Jameson | 17 % | 70 % | 1.5 |
| Kenneth Prime | 23 % | 62 % | 1.2 |
| Gerald Goodchild | 13 % | 24 % | 2.2 |
| Pat Johnson | 5 % | 57 % | 3.3 |
| Michael Holmes | 10 % | 55 % | 3.3 |

### T3. Physical cues (11 test children's real errors; writer responses ASSUMED; SIM)

| Cue | Mistakes caught per 10 | Fixed on paper per 10 (low - high) | False cues per 100 correct | Correct words made wrong per 100 | Extra time | Cues felt mid-word per 100 words | Suggestion lists read per 100 words | Letters drawn by the pen per 100 words | Wrong-letter fragments per 100 words |
|---|---|---|---|---|---|---|---|---|---|
| No cue | 0.0 | 0.0 (0.0 - 0.0) | 0.0 | 0.00 | +0 % | 0.0 | 0.0 | 0.0 | 0.0 |
| App underlines afterwards (no physical cue) | 6.1 | 0.0 (0.0 - 0.0) | 2.3 | 0.25 | +5 % | 0.0 | 10.1 | 0.0 | 0.0 |
| LRA tick on the suspect letter | 6.1 | 2.6 (1.4 - 3.4) | 2.3 | 0.16 | +16 % | 7.4 | 6.4 | 0.0 | 0.0 |
| LRA tick before a risky letter | 0.0 | 0.0 (0.0 - 0.0) | 0.0 | 0.00 | +0 % | 0.0 | 0.0 | 0.0 | 0.0 |
| Pen lift: the wrong letter is not drawn | 3.6 | 2.3 (1.8 - 2.7) | 0.3 | 0.03 | +8 % | 4.8 | 4.8 | 0.0 | 1.0 |
| Tick, plus pen lift when very sure | 6.1 | 3.4 (2.4 - 4.1) | 2.3 | 0.16 | +15 % | 7.7 | 8.0 | 0.0 | 1.0 |
| Show me (opt-in): nose draws the next letter | 6.1 | 2.7 (1.5 - 4.0) | 2.3 | 0.22 | +9 % | 7.4 | 0.0 | 4.4 | 0.0 |
| Heel wheel steers toward the right letter | 0.0 | 0.6 (0.2 - 1.0) | 1.9 | 0.09 | +0 % | 8.3 | 0.0 | 0.0 | 0.0 |
| Tick at the next pause + suggestions | 6.1 | 3.0 (1.6 - 4.0) | 2.3 | 0.15 | +17 % | 0.0 | 6.4 | 0.0 | 0.0 |

Rule S4 (tuning children): recommended **tick_lift** (fragile: False); admissible: tick_after, tick_before, withhold, tick_lift, heel_steer, pause_offer. Rule S5: theta_b 0.02. Recogniser commit before a letter's end: 19 %. Next letter within the nose's reach: 47 % (median farthest point 5.6 mm).

With letters from the recogniser (writer_independent), nominal responses: tick_after fixed 2.1/10, false cues 40.6/100; tick_lift fixed 2.2/10, false cues 40.6/100; withhold fixed 0.1/10, false cues 0.1/100
With letters from the recogniser (calibrated), nominal responses: tick_after fixed 2.3/10, false cues 38.7/100; tick_lift fixed 2.3/10, false cues 38.7/100; withhold fixed 0.1/10, false cues 0.1/100

### T4. Text prediction on the user's own notes (test journals; CALC)

| Journal | Model | Next word top-1 / top-3 | After 1 letter top-1 / top-3 | After 2 letters top-1 / top-3 | Letters saved (top-1 / top-3 list) | p95 latency |
|---|---|---|---|---|---|---|
| 11579 | NG0 (as used so far) | 11 % / 20 % | 30 % / 46 % | 45 % / 59 % | 29 % / 41 % | 0.3 ms |
| 11579 | NG1x (larger corpus) | 12 % / 21 % | 31 % / 47 % | 48 % / 62 % | 31 % / 44 % | 0.8 ms |
| 11579 | personalised (chosen) | 14 % / 24 % | 37 % / 56 % | 55 % / 70 % | 37 % / 50 % | 3.0 ms |
| 2024 | NG0 (as used so far) | 10 % / 20 % | 31 % / 47 % | 46 % / 61 % | 28 % / 41 % | 0.3 ms |
| 2024 | NG1x (larger corpus) | 11 % / 21 % | 31 % / 49 % | 48 % / 63 % | 30 % / 44 % | 1.0 ms |
| 2024 | personalised (chosen) | 12 % / 22 % | 33 % / 52 % | 50 % / 64 % | 32 % / 46 % | 2.2 ms |

Rule P1 chose {'base': 'NG1x', 'lc': 0.1, 'half_life': 500.0, 'lb': 0.4, 'score': 0.5267777777777778}; rule P2 chose p_offer 0.7.

Journal 11579, autowrite completion on request (offers at p >= 0.7): -7.1 s per 100 letters for a typical writer (-16 % of writing time), +2.7 s (3 %) for a slow writer.
Journal 2024, autowrite completion on request (offers at p >= 0.7): -6.9 s per 100 letters for a typical writer (-15 % of writing time), +1.3 s (1 %) for a slow writer.

### T5. Why close tracing lowers legibility (drive study's runs, 6 test writers x 4 seeds; SIM)

| Learners | Condition | Ink to target | Letters read by the app (writing order) | Read as a picture (order-free) | Share of each letter left undrawn (> 1 mm from any ink) | Ink running backwards along the letter | Newly misread by the app / by both readers | ...app reads them again if drawn in the letter's own order / if the missing part is added |
|---|---|---|---|---|---|---|---|---|
| dysgraphia | none | 447 um | 92 % | 70 % | 2 % | 7 % | 0 / 0 | n/a / n/a |
| dysgraphia | nose_partial | 268 um | 94 % | 77 % | 1 % | 8 % | 13 / 4 | 69 % / 23 % |
| dysgraphia | wheel_path | 277 um | 84 % | 73 % | 3 % | 6 % | 67 / 22 | 48 % / 54 % |
| dysgraphia | nose_nogate | 83 um | 86 % | 73 % | 3 % | 10 % | 75 / 44 | 69 % / 20 % |
| dysgraphia | wheel_path+nose | 68 um | 79 % | 72 % | 4 % | 7 % | 123 / 60 | 58 % / 41 % |
| dyslexia | none | 412 um | 83 % | 77 % | 6 % | 6 % | 0 / 0 | n/a / n/a |
| dyslexia | nose_partial | 274 um | 84 % | 79 % | 6 % | 6 % | 7 / 3 | 71 % / 0 % |
| dyslexia | wheel_path | 293 um | 81 % | 73 % | 8 % | 5 % | 19 / 15 | 53 % / 32 % |
| dyslexia | nose_nogate | 82 um | 77 % | 73 % | 7 % | 8 % | 53 / 37 | 58 % / 2 % |
| dyslexia | wheel_path+nose | 72 um | 76 % | 72 % | 8 % | 6 % | 59 / 54 | 56 % / 20 % |

### T7. Word recognition: character and word error rates (20 held-out UJI writers; SIM on real letters)

| Recogniser | Spacing | CER no LM | CER with LM | WER no LM | WER with LM |
|---|---|---|---|---|---|
| new writer (writer-disjoint) | normal | 22.9 % | 9.1 % | 55 % | 20 % |
| calibrated on the other session (session-disjoint) | normal | 20.1 % | 9.2 % | 51 % | 20 % |
| segmentation errors per letter | normal | 2.8 % | | | |
| new writer (writer-disjoint) | tight | 23.9 % | 10.5 % | 56 % | 22 % |
| calibrated on the other session (session-disjoint) | tight | 21.1 % | 10.6 % | 52 % | 23 % |
| segmentation errors per letter | tight | 3.5 % | | | |

Rule W1 (tuning writers): language weight beta_w = 0.75. Words: Tatoeba test sentences written with each writer's letters from one session; spacing N(0.25, 0.12) x-height (normal) and N(0.08, 0.12) (tight), ASSUMPTION.

### T8. Spelling help with the pen's own reading of the letters (the review's score; 11 test children; SIM)

| Recogniser | Caught | False alarms per 100 correct | Suggestion shown / right when shown | Misread words put right / right readings changed | Unusual correct words kept | ECE raw / calibrated | Auto mode: errors fixed / correct words changed per 100 |
|---|---|---|---|---|---|---|---|
| independent, as planned (W2, temperature) (lambda_r 0.5, T 13.63, theta_c 0.8, p_s 0.7) | 1 % | 1.3 | 0 % / 0 % | 36 % / 2.3 % | 100 % | 0.224 / 0.353 | 0.0 / 0.00 |
| calibrated, as planned (W2, temperature) (lambda_r 0.5, T 10.42, theta_c 0.85, p_s 0.7) | 3 % | 1.1 | 0 % / 0 % | 40 % / 2.7 % | 100 % | 0.193 / 0.334 | 0.0 / 0.00 |
| letters known exactly, same words (task 2's checker) | 63 % | 1.8 | right word first 59 % | n/a | n/a | n/a | n/a |

Letters seen through real held-out letters (test pool): read right 82 % (new writer), 86 % (calibrated).

### T9. Writing an accepted word with the pen (kinematic planner, rule C1; SIM)

| Hand | +-1 mm | +-2 mm | +-3 mm | +-4 mm | +-6 mm | half letters per 100 (point by point / whole letter) at +-6 mm | time vs own writing |
|---|---|---|---|---|---|---|---|
| steady | 0 % | 0 % | 4 % | 23 % | 95 % | 4 / 0 | 1.01 |
| slow | 0 % | 0 % | 16 % | 42 % | 98 % | 2 / 0 | 1.23 |
| fast | 0 % | 0 % | 0 % | 0 % | 1 % | 99 / 8 | 1.01 |
| pause | 0 % | 0 % | 0 % | 8 % | 24 % | 58 / 8 | 1.01 |
| still | 0 % | 0 % | 0 % | 0 % | 2 % | 97 / 0 | 1.01 |

100 completions (the rest of words of 5+ letters after 40-60 % written); rest-of-word extent median 11.8 mm (90th percentile 19.1 mm); the hand's usual advance 7.4 mm/s.

