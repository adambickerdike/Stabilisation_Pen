"""Every tuning rule of the study, written down before any test number was computed (task 5).

Each rule names the data it may use (tuning writers, tuning passages, tuning journals), the quantity it optimises and
its constraint.  Test stages record the sha256 of this RULES text in their outputs; the doc lists them.  A rule is never
changed after its task's test ran; where a rule turned out badly on the test data, that is reported, not re-tuned.
"""
from __future__ import annotations

import hashlib
import json

RULES = {
    # ---------------------------------------------------------------- task 1: online recogniser
    "O1_variant": ("Three augmentation variants are trained for the same number of steps (5,470 batches of 48 letters; "
                   "first written as 'the same time budget', changed before the choice because the shared machine "
                   "stalled one variant) on the 34 UJI training writers: "
                   "'base' (affine + jitter), 'tremor' (+ tremor 4-12 Hz up to 0.4 x-height) and 'full' (+ sigma-"
                   "lognormal variation).  Choose the one with the highest mean top-1 accuracy on the UJI tuning writers "
                   "over the fractions 0.3-1.0 of the letter, averaged over clean letters and letters with 0.33 x-height "
                   "tremor (1 mm at a 3 mm x-height).  Ties within 0.5 points: the simpler variant."),
    "O2_commit": ("Commit threshold tau: the smallest value in {0.5, 0.6, 0.7, 0.8, 0.9, 0.95} whose commits are "
                  "correct >= 97 % of the time on clean tuning letters (letters never committed are decided at their end)."),
    "O3_beta": ("Language-context weight beta in {0, 0.25, 0.5, 0.75, 1.0}: the one with the highest top-1 at half of the "
                "letter on tuning writers' letters in Tatoeba validation sentences, provided top-1 at the full letter does "
                "not fall by more than 0.5 points against beta = 0."),
    "O4_calibration": ("Writer calibration (the app holds one sample of every letter from the calibration pangram; here "
                       "the writer's other UJI repetition): fused posterior = GRU^a x exp(-DTW/tau), a in {0.3, 0.5, 0.7}, "
                       "tau in {0.05, 0.1, 0.2} x-height; choose the pair with the highest mean top-1 over the fractions "
                       "0.3-1.0 on the tuning writers."),
    # ---------------------------------------------------------------- task 2: spell checker
    "S1_channel": ("The spelling-error (channel) model is estimated from Birkbeck pairs whose target word falls in the "
                   "training bucket (sha256 bucket >= 20 of 100); pairs with target buckets < 10 are the tuning pairs, "
                   "10-19 the test pairs.  Holbrook passages: the 19 children are split by sha256 of the name into "
                   "tuning (bucket < 40) and test children."),
    "S2_detect": ("Word-level flag threshold theta (posterior probability that the word as written so far is not what "
                  "the writer intends to spell) and the out-of-vocabulary prior p_oov in {0.01, 0.03, 0.1, 0.3}: for "
                  "each p_oov the lowest theta on a grid 0.30-0.9999 whose false alarms on correctly spelled words of the "
                  "tuning children stay <= 2 per 100 correct words; the pair with the highest detection rate wins.  The "
                  "error prior (share of misspelled words) is set to the tuning children's measured rate.  A word "
                  "written with a capital inside a sentence is taken as a name and never flagged (added before the "
                  "test: in a first look at 4 tuning children, 12 of 43 false alarms were names and 7 of 123 errors "
                  "were capitalised)."),
    "S3_withhold": ("Ink withholding (pen lift on the letter being written) uses a stricter threshold theta_w: the lowest "
                    "value whose false withholdings on correct words of the tuning children stay <= 0.2 per 100 correct "
                    "words, and it acts only on a letter the online recogniser has committed to (rule O2)."),
    "S4_policy": ("The recommended physical cue is the one with the most words finally spelled right per 100 words on "
                  "tuning simulated writers, subject to: false physical interventions <= 2 per 100 correct words, no word "
                  "ever changed by the pen outside an opt-in mode, and extra writing time <= 25 %.  Writer-response "
                  "parameters are ASSUMPTIONS and are varied in a sensitivity table; the choice must hold at the "
                  "low end of the ranges or it is reported as fragile."),
    "S5_warn": ("Warning before a risky letter (tick_before, heel_steer): theta_b = the lowest value in {0.02, 0.03, "
                "0.05, 0.08, 0.12} whose warnings on correctly spelled words of the tuning children stay <= 5 per 100 "
                "correct words."),
    # ---------------------------------------------------------------- task 3: prediction
    "P1_personal": ("Personalisation settings (base model in {NG0, NG1x}; cache weight lc in {0, 0.05, 0.1, 0.2, 0.3}; "
                    "cache half-life in words {500, 5000, inf}; user-bigram weight lb in {0, 0.2, 0.4}) are chosen by the "
                    "highest mean top-3 accuracy (next word before its first letter, and completion after 1 and 2 letters, "
                    "averaged) over the tuning journals, evaluated online on 1500 words after the first half of each "
                    "journal (the model adapts as the user writes).  Latency <= 20 ms per suggestion is a hard constraint."),
    "P2_offer": ("A completion is offered physically (haptic tick, or ghost word) only when its calibrated probability is "
                 ">= p_offer, p_offer in {0.3, 0.4, 0.5, 0.6, 0.7}: the value with the most letters saved on tuning "
                 "journals with an acceptance cost of one gesture (ASSUMPTION: 0.6 s) and a checking cost of 0.25 s per "
                 "offer read."),
    # ---------------------------------------------------------------- task 4: shape assist
    "A1_shape": ("Shape-assist settings (confidence gate c_min in {0.6, 0.8, 0.9}, gain g in {0.25, 0.5, 0.75}, nose "
                 "limit q_max in {0.15, 0.3, 0.5} mm, dead band d0 in {0.05, 0.1, 0.2} x-height) are chosen on UJI "
                 "tuning writers by the largest gain in letters read by the independent offline judge, subject to: "
                 "clean well-formed letters (judge-read, no tremor) moved <= 25 um RMS; no letter read as another letter "
                 "that was read correctly without assist (net-harm share <= 0.5 %); device share of ink motion <= 25 %."),
    "A2_cleancopy": ("Clean-copy v2 (re-rendering low-confidence letters from the writer's own calibration letters) is "
                     "adopted only if on tuning writers it reads >= 2 points more words than the aiprior clean copy and "
                     "every re-rendered letter is marked as synthetic (REQ-APP-004)."),
}


def rules_sha256() -> str:
    return hashlib.sha256(json.dumps(RULES, sort_keys=True).encode()).hexdigest()[:16]
