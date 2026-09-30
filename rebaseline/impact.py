"""Task 1: the impact register (CALCULATION on the documents; no simulation).

Every row of docs/claims_register.md's PRESERVED UPSTREAM REGISTER (the tables under "## Tremor", "## Writing help",
"## Hardware" and "## Simulation"), plus the headline statements of its preamble, with:
  model          which model produced the number (the vocabulary is MODELS below)
  faults         which of the engineering pass's findings touch that model (FAULTS below)
  classification UNAFFECTED | AFFECTED_RERUN (affected and rerun here) | AFFECTED_NOT_RERUN (with the reason) |
                 SUPERSEDED_ASTRA (the engineering pass already replaced it) | NOT_SIM (listed for completeness only)
A register row that mixes models is split into sub-rows (a, b, ...), one model and one classification each.
Classifications are this study's reading of the code paths (named in model_detail); where a row is marked
AFFECTED_RERUN the new number is in the named results file.
"""
from __future__ import annotations

import csv
import io
from typing import Dict, List

from . import RESULTS_DIR

MODELS: Dict[str, str] = {
    "sim2j-legacy": ("sim2 / MuJoCo whole Rev J pen (study sim2j): nib servo with the exact simulator velocity "
                     "(legacy_true), the true ball force as its contact gate (legacy_force), a 400 Hz inner loop, and "
                     "an immediate firmware contact flag"),
    "sim2-bnib": ("bnib/sim.py (study B's set-up in sim2): observer servo on the Hall reading (causal velocity), the "
                  "true contact as the servo's authority gate, the immediate firmware contact flag, linear wire "
                  "suspension, no guide drag; its CALC side used the quadrature harmonic load (bnib/loads.py)"),
    "sim2-revk-servo": "revk/servo_sim.py through bnib/sim.py (as sim2-bnib, with Rev K's Km and wire stiffness)",
    "wholepen-sim2j-legacy": ("study W's stepper (wholepen/stepper.py, a copy of sim2j's step that still passes the "
                              "true contact to the servo) with sim2's nib servo on legacy sensing when it ran"),
    "hw1-real-v1": ("model HW1 (handwriting/: 2-D hand-pen-paper, idealised inverse-dynamics tip servo) with study R's "
                    "real recorded inputs; trackers on fusion sensor streams degraded by realdata/sensors.py VERSION 1 "
                    "(DeltaPen-class page model with future-window noise and recovery of unobserved motion)"),
    "hw1-real-nopage": ("model HW1 with real recorded inputs and NO page-sensor dependence (ordinary pen, perfect "
                        "knowledge, residual constructions on perfect knowledge, or the ideal page-sensor bound)"),
    "hw1-real-revj-plant": ("model HW1 with real inputs, perfect knowledge, and the Rev J nose's servo and mass with "
                            "its travel cut (readable/reach.py)"),
    "hw1-synthetic": "model HW1 with synthetic writers and synthetic tremor (fusion's ideal page sensor)",
    "hw1-d": "model HW1-D (the drive study's hand-pen-wheel model)",
    "h1": "model H1 (opt/inertial: hand-pen model of the inertial and nose studies)",
    "sim2-h1check": "sim2's H1-consistency configuration (sim2.params.h1_check_config, now explicitly legacy/optimistic)",
    "writer-model": "the synthetic writer model (sim2j/writers.py) checked against literature (CALC on writing)",
    "ai3-kinematic": "the accepted-word completion planner (ai3), kinematics only",
    "sim2j-rl": "sim2j's Gymnasium RL environment (reward before the repair)",
    "letters-lm": "letter recognition / language model / spelling pipeline on recorded letters (no plant)",
    "calc": "a calculation, not a simulation",
}

FAULTS: Dict[str, str] = {
    "F1": "sim2 nib servo used exact simulator velocity and the true ball force (legacy_true / legacy_force)",
    "F2": "sim2's old 400 Hz inner loop is unstable with causal sensing (80 Hz selected)",
    "F3": "sim2j's firmware contact flag was immediate (now sampled at 1 kHz and delivered 1 ms late; NO flag restores it)",
    "F4": "realdata/sensors.py page model v1 leaked the future and recovered motion lost in dropouts",
    "F5": "balanced-nib harmonic load summed spring and inertia in quadrature (bnib/loads.py)",
    "F6": "Rev K's wires gain tension under the stiff 10,000 N/m anchor (18.2 mN at the stop, not 2 mN)",
    "F7": "the ball guide's 4 N preload gives about 8 mN rolling drag, not 2.6 mN",
    "F8": "DEC-066: B1/Rev K servo must be 40 Hz position loop, inner loop <= 46 Hz",
    "F9": "RL reward stopped charging tracking error when the ball lost contact",
    "F10": "plant mismatch: a result computed on the Rev J nose's servo and mass is quoted for the balanced nib",
    "F11": "old kinematic completion planner ignored actual velocity/acceleration/jerk limits",
    "F12": "readable/e11.py calibration notes chosen by a seed stride that need not keep the writer",
}

# classification codes
UN, RR, NR, SA, NS = "UNAFFECTED", "AFFECTED_RERUN", "AFFECTED_NOT_RERUN", "SUPERSEDED_ASTRA", "NOT_SIM"

ROWS: List[Dict] = [
    # ------------------------------------------------------------------ preamble headline statements
    dict(id="P-01", section="preamble", claim="Study R: no tracker helps on real tremor (severe: ordinary 0.5, Rev H 0.4, "
         "Rev J gated 0.4, TCN 0.2 words of 10; perfect knowledge 7.0)", evidence="SIM", status="CURRENT",
         model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json (R's |deltapen trackers with page v2)",
         note="ordinary pen and perfect knowledge use no page sensor and are unaffected"),
    dict(id="P-02", section="preamble", claim="Study E's best causal tracker: severe tip tremor 0.69x, words 0.5, clean "
         "writing moved 68 um mean / 493 um worst writer", evidence="SIM", status="CURRENT", model="hw1-real-v1",
         faults="F4", classification=RR, rerun="results/rebaseline/page_v2.json (E's revJ_new|deltapen with page v2)",
         note="the test split is spent: a re-analysis, not a new test"),
    dict(id="P-03", section="preamble", claim="Study F: +2 words needs <= 0.55 mm left (0.25 mm near-normal); best "
         "estimator leaves 1.1 mm; prediction is not the problem, separation is", evidence="SIM; CALC",
         status="CURRENT", model="hw1-real-nopage", faults="F4 (the 1.1 mm and the separation rows only)",
         classification=RR, rerun="results/rebaseline/page_v2.json (F gap rows, E's 1.12 mm)",
         note="the target (E13 curve) uses perfect-knowledge residuals and is unaffected"),
    dict(id="P-04", section="preamble", claim="Study F reach: Rev K's +-1 mm nib gains 1.4 words with perfect knowledge "
         "at the severe class; about +-1.5 mm needed", evidence="SIM", status="CURRENT",
         model="hw1-real-revj-plant", faults="F10, F8", classification=RR,
         rerun="results/rebaseline/reach_b1.json (B1's 40/46 Hz servo and moving mass)"),
    dict(id="P-05", section="preamble", claim="Big correction: in the physics simulation the Rev J nose drew 2.25 W in "
         "tremor-free writing (1.1 W static load, 0.74 W servo noise, 0.4 W friction/holding)", evidence="SIM",
         status="CURRENT (Rev J SUSPENDED for battery)", model="sim2j-legacy", faults="F1, F2", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (power of the same pen, nose held and G4, causal servo)",
         note="the three-way split itself (power_split) was not rerun; the total power is"),
    dict(id="P-06", section="preamble", claim="B1 balanced nib: holding heat <= 1.6 mW, continuous 7.6 mW, about 38 h "
         "(CALC; 33.5 h in simulation)", evidence="CALC; SIM", status="CURRENT (7.6 mW SUPERSEDED by Rev K)",
         model="sim2-bnib", faults="F5, F6, F7, F8", classification=RR,
         rerun="results/rebaseline/bnib_rerun.json (SIM power and battery hours with DEC-066 servo and corrected loads)",
         note="the CALC 7.6 mW used the quadrature load (F5); Rev K's CALC budgets REQUIRE RECOMPUTATION per the pass"),
    dict(id="P-07", section="preamble", claim="Rev K writes 23.5-48.6 h per charge with 1 mm tremor; 2.2x study B's "
         "copper loss", evidence="CALC", status="CURRENT", model="calc", faults="F5, F6, F7",
         classification=NS, rerun="", note="CALC; the engineering pass marks Rev K budgets REQUIRES RECOMPUTATION"),
    # ------------------------------------------------------------------ Tremor
    dict(id="T-01a", section="Tremor", claim="Perfect knowledge removes most ink error: Rev H 87-99 % up to 2 mm (H1)",
         evidence="SIM", status="CURRENT, mechanism limit only", model="h1", faults="", classification=UN, rerun=""),
    dict(id="T-01b", section="Tremor", claim="Perfect knowledge, Rev J in sim2j: 0.10-0.20 of the ordinary pen's error at "
         "8-12 Hz, 0.07-0.12 at 4 Hz", evidence="SIM", status="CURRENT, mechanism limit only", model="sim2j-legacy",
         faults="F1, F2, F3", classification=RR, rerun="results/rebaseline/sim2j_cards.json (oracle column)"),
    dict(id="T-02a", section="Tremor", claim="HEADLINE: Rev J + G4, ET 1-2 mm at 8-12 Hz: ink error 0.63 (0.59-0.66), "
         "0.41->0.28 mm at 1 mm, 0.93->0.54 mm at 2 mm; words 77->100 %, letters 79->94 %", evidence="SIM (sim2j)",
         status="CURRENT, synthetic tremor only", model="sim2j-legacy", faults="F1, F2, F3", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (causal, legacy_flags, legacy_exact; paired)"),
    dict(id="T-02b", section="Tremor", claim="On real inputs G4 acts no more than a nib held still (1.07-1.08x) and "
         "leaves clean writing alone (study E)", evidence="SIM (HW1 real)", status="CURRENT", model="hw1-real-v1",
         faults="F4", classification=RR, rerun="results/rebaseline/page_v2.json (revJ_g4|deltapen)"),
    dict(id="T-03a", section="Tremor", claim="Real severe tremor: trackers Rev H 0.4 / Rev J gated 0.4 / TCN 0.2 words; "
         "tip tremor 1.06x / 0.96x / 0.71x; E's best 0.69x, words 0.5, clean 68/493 um", evidence="SIM (HW1 real)",
         status="CURRENT: no legibility benefit yet", model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json"),
    dict(id="T-03b", section="Tremor", claim="Real severe tremor: ordinary pen 0.5, perfect knowledge 7.0, no tremor 6.8 "
         "words", evidence="SIM (HW1 real)", status="CURRENT", model="hw1-real-nopage", faults="",
         classification=UN, rerun=""),
    dict(id="T-04", section="Tremor", claim="A tremor network trained on real recordings: severe tip tremor 0.60x, "
         "clean 2.5 um mean (19 um worst) (information only)", evidence="SIM (HW1 real), information only",
         status="UNPROVEN (EXP-E10)", model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json (E's information row 'net' with page v2)"),
    dict(id="T-05a", section="Tremor", claim="Readable target: +2 words at 0.65 mm (tuning) / 0.55 mm (test); 80 % of "
         "tremor-free words at 0.25-0.26 mm", evidence="SIM (HW1 real); CALC", status="CURRENT (DEC-067)",
         model="hw1-real-nopage", faults="", classification=UN, rerun="",
         note="E13 residuals are built on perfect knowledge; no page sensor, no sim2"),
    dict(id="T-05b", section="Tremor", claim="... study E's best causal tracker leaves 1.12 mm", evidence="SIM (HW1 real)",
         status="CURRENT", model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json (revJ_new|deltapen severe tip tremor)"),
    dict(id="T-06", section="Tremor", claim="Per-user gates (E11): largest clean change 493 -> 19.1 um; real-data "
         "network 18.9 um; no words gained; lowering rule moved one writer 60.5 um", evidence="SIM (HW1 real), "
         "information only", status="CURRENT, information only (DEC-068)", model="hw1-real-v1", faults="F4, F12",
         classification=NR, rerun="",
         note=("not rerun: information only on a spent split, and two faults touch it (page v1 and the calibration-note "
               "selection repaired by the pass); a rerun must refit its gate on v2 streams with the repaired note "
               "choice (proposed EXP-X07)")),
    dict(id="T-07a", section="Tremor", claim="Gap: prediction over 4.9 ms leaves 0.03 mm; accelerometer on tremor alone "
         "0.29 mm; ideal drift-free position sensor 0.11-0.12 mm", evidence="SIM; CALC", status="CURRENT (DEC-069)",
         model="hw1-real-nopage", faults="", classification=UN, rerun="",
         note="IMU and ideal page-sensor paths do not use the DeltaPen-class model"),
    dict(id="T-07b", section="Tremor", claim="Gap: with writing present the estimators leave 0.97-1.12 mm (DeltaPen-class "
         "page streams); page AR on the tremor alone with the DeltaPen-class sensor 1.03-1.14 mm; page sensing check "
         "0.59 mm", evidence="SIM; CALC", status="CURRENT (DEC-069)", model="hw1-real-v1", faults="F4",
         classification=RR, rerun="results/rebaseline/page_v2.json (F gap page rows)"),
    dict(id="T-08", section="Tremor", claim="Reach: perfect knowledge with +-1.0 mm leaves 1.00 mm, +1.4 words; "
         "+-1.5 mm leaves 0.67 mm, +3.2 words; command > 1 mm 61 % of the time", evidence="SIM (HW1 real; Rev J nose "
         "with travel cut)", status="CURRENT, one model", model="hw1-real-revj-plant", faults="F10, F8",
         classification=RR, rerun="results/rebaseline/reach_b1.json"),
    dict(id="T-09a", section="Tremor", claim="Real moderate/mild: Rev J words 5.5 (moderate)", evidence="SIM (HW1 real)",
         status="CURRENT", model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json (revJ_gated|deltapen moderate/mild)"),
    dict(id="T-09b", section="Tremor", claim="Real moderate/mild: ordinary pen 5.7, perfect knowledge 6.9; mild reads as "
         "no tremor", evidence="SIM (HW1 real)", status="CURRENT", model="hw1-real-nopage", faults="",
         classification=UN, rerun=""),
    dict(id="T-10", section="Tremor", claim="Tremor size classes at the pen tip", evidence="DATA, CALC",
         status="CURRENT", model="calc", faults="", classification=NS, rerun=""),
    dict(id="T-11", section="Tremor", claim="Rev J, mild tremor (0.3 mm): 1.01 of the ordinary pen (no gain, no harm)",
         evidence="SIM (sim2j)", status="CURRENT, synthetic only", model="sim2j-legacy", faults="F1, F2, F3",
         classification=RR, rerun="results/rebaseline/sim2j_cards.json (et_mild card)"),
    dict(id="T-12", section="Tremor", claim="Rev J, slow tremor (4 Hz, 1-2 mm): 1.00 (detector listens from 4.5 Hz)",
         evidence="SIM (sim2j)", status="CURRENT", model="sim2j-legacy", faults="F1, F2, F3", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (slow_4hz card)"),
    dict(id="T-13a", section="Tremor", claim="Rev J + G4 moved tremor-free writing 0 mm (6 synthetic writers)",
         evidence="SIM (sim2j)", status="CURRENT", model="sim2j-legacy", faults="F1, F2, F3", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (clean_writing)"),
    dict(id="T-13b", section="Tremor", claim="On real writing the Rev H and Rev J gated trackers moved it 25 um (gate "
         "shut 99.8 %)", evidence="SIM (HW1 real writing)", status="CURRENT", model="hw1-real-v1", faults="F4",
         classification=RR, rerun="results/rebaseline/page_v2.json (clean notes)"),
    dict(id="T-14a", section="Tremor", claim="Gated listening tracker, ET 1-2 mm at 6-10 Hz: 830 -> 430 um, words 31 -> "
         "74 % (HW1, Rev H nose, synthetic)", evidence="SIM (HW1)", status="CONTESTED", model="hw1-synthetic",
         faults="", classification=UN, rerun=""),
    dict(id="T-14b", section="Tremor", claim="... in sim2j it moved tremor-free writing 59 um and raised the 0.3 mm error "
         "to 1.14x", evidence="SIM (sim2j)", status="CONTESTED", model="sim2j-legacy", faults="F1, F2, F3",
         classification=NR, rerun="",
         note="not rerun: the tracker is not adopted (DEC-042 superseded by G4) and the row is already CONTESTED; its "
              "verdict (fails the 25 um rule) is a tracker property the causal servo is unlikely to rescue"),
    dict(id="T-14c", section="Tremor", claim="... with real writing and real tremor it left 1.03x (study R bridge, ideal "
         "page sensor)", evidence="SIM (HW1 real)", status="CONTESTED", model="hw1-real-nopage", faults="",
         classification=UN, rerun="", note="the DeltaPen-class bridge row (1.04x) is rerun in page_v2.json"),
    dict(id="T-15", section="Tremor", claim="Gated listening at 6 Hz: 822 -> 540 um (HW1)", evidence="SIM (HW1)",
         status="CONTESTED", model="hw1-synthetic", faults="", classification=UN, rerun=""),
    dict(id="T-16a", section="Tremor", claim="TCN: 278 um and 81 % of words in HW1", evidence="SIM (HW1)",
         status="shadow mode only", model="hw1-synthetic", faults="", classification=UN, rerun=""),
    dict(id="T-16b", section="Tremor", claim="TCN in sim2j: moved tremor-free writing 150 um (206 max), 0.3 mm error "
         "1.26-1.38x", evidence="SIM (sim2j)", status="shadow mode only", model="sim2j-legacy", faults="F1, F2, F3",
         classification=NR, rerun="", note="not rerun: shadow mode only; the replay's failure is in the estimator, "
                                            "the servo change does not bear on the adoption decision"),
    dict(id="T-16c", section="Tremor", claim="TCN on real inputs: 0.71x severe tip tremor, moved clean real writing "
         "170 um, -1 word", evidence="SIM (HW1 real)", status="shadow mode only", model="hw1-real-v1", faults="F4",
         classification=RR, rerun="results/rebaseline/page_v2.json (revJ_tcn|deltapen)"),
    dict(id="T-17", section="Tremor", claim="Telling tremor from writing by frequency alone is not reliable",
         evidence="LIT", status="CURRENT", model="calc", faults="", classification=NS, rerun=""),
    dict(id="T-18a", section="Tremor", claim="End-cap on top of the nose (H1, Rev J.1): 5.6/16.8/18.3 % (locked mass "
         "12.6/11.1/6.7 %)", evidence="SIM (H1)", status="CONTESTED; rejected (DEC-051)", model="h1", faults="",
         classification=UN, rerun=""),
    dict(id="T-18b", section="Tremor", claim="End-cap in sim2j: no gain (0.67 with, 0.65 without), fewer letters",
         evidence="SIM (sim2j)", status="CONTESTED; rejected (DEC-051)", model="sim2j-legacy", faults="F1, F2, F3",
         classification=NR, rerun="", note="not rerun: rejected for the product (DEC-051)"),
    dict(id="T-19", section="Tremor", claim="First end-cap design, 43 g: 8/18/20 %", evidence="SIM (H1)",
         status="SUPERSEDED upstream", model="h1", faults="", classification=UN, rerun=""),
    dict(id="T-20a", section="Tremor", claim="Inertia cannot move letters: end-cap 0.21 mm, gyroscope 1.06 mm below "
         "5 Hz; a useful gyroscope stores 5-18 J", evidence="CALC", status="CURRENT (physics)", model="calc",
         faults="", classification=NS, rerun=""),
    dict(id="T-20b", section="Tremor", claim="Study W: gyroscopic and weighted tails never robustly beat the same mass "
         "locked (+15/+51/-14 % against locked with the nose)", evidence="SIM (study W)", status="CURRENT (physics)",
         model="wholepen-sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun: tails are out of the product (DEC-051); comparisons are against a locked mass on the same "
              "servo, and wholepen/stepper.py's own step copy still passes the true contact (patch proposal in the doc)"),
    dict(id="T-21", section="Tremor", claim="Rev J, severe tremor (3 mm at 5 and 8 Hz), writing through it: words "
         "4 -> 38 %, ink 1.47 -> 1.15 mm", evidence="SIM (sim2j)", status="CURRENT, synthetic only",
         model="sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun here (compute given to the four headline tasks); proposed EXP-X03"),
    dict(id="T-22", section="Tremor", claim="The nose runs out of travel at about 3 mm in autowrite (6.55 of 6.57 mm); "
         "at 8 mm any pen reads 0-2 of 10", evidence="SIM (sim2j, study W); DATA", status="CURRENT",
         model="sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun: autowrite is a C1S bench mode with no hardware in the next prototype (DEC-050); EXP-X03"),
    dict(id="T-23", section="Tremor", claim="Collar (whole pen shifts): -5 to +5 % against locked; light inner pen 17 % "
         "less at 8 mm, 17 points less ink", evidence="CALC; SIM (study W)", status="CURRENT: not adopted",
         model="wholepen-sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun: not adopted (DEC-051); its bench test EXP-W11 decides"),
    # ------------------------------------------------------------------ Writing help
    dict(id="W-01a", section="Writing help", claim="Autowrite in HW1: 99.2 % letters, 100 % words up to 1 mm; 98 % at "
         "2 mm", evidence="SIM (HW1)", status="CURRENT as mechanism result", model="hw1-synthetic", faults="F11",
         classification=UN, rerun="",
         note="HW1 unchanged; the pass's motion-rate screen (F11) was applied to ai3's planner, not to nose2's HW1 "
              "autowrite, so the rate caution applies by analogy"),
    dict(id="W-01b", section="Writing help", claim="Autowrite in sim2j: 88 % of words at 3 mm tremor (4 % ordinary), "
         "100 % with no tremor", evidence="SIM (sim2j)", status="CURRENT as mechanism result; no hardware (DEC-050)",
         model="sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun: the +-6 mm C1S nose has no hardware in the next prototype; EXP-X03 (autowrite under causal "
              "sensing) proposed"),
    dict(id="W-02", section="Writing help", claim="Autowrite with a realistic page sensor: 2-4x ink error, still "
         "readable; accumulating errors: 7 of 10 words", evidence="SIM (sim2j, writers 0-1)", status="CURRENT",
         model="sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun, for the same reason as W-01b; sim2j's own page-error model is causal (held/walk draws), so "
              "only the servo sensing touches this row"),
    dict(id="W-03a", section="Writing help", claim="PD write-big loops: driven heel wheel keeps the last loop 6.6 -> "
         "8.6 mm (relaxed), 7.4 mm (resisting)", evidence="SIM (sim2j)", status="CURRENT (synthetic)",
         model="sim2j-legacy", faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun: the wheel does the work; the nib servo only holds the nose centred (small effect expected)"),
    dict(id="W-03b", section="Writing help", claim="HW1-D steering reach 0.99 of target", evidence="SIM (HW1-D)",
         status="CONTESTED", model="hw1-d", faults="", classification=UN, rerun=""),
    dict(id="W-04a", section="Writing help", claim="Tracing: nose half-way pull 0.83 -> 0.64 mm, words 9.7 of 10; strong "
         "guidance 0.27 mm, words 6.3", evidence="SIM (sim2j)", status="CURRENT", model="sim2j-legacy",
         faults="F1, F2, F3", classification=NR, rerun="",
         note="not rerun (compute); the nose's guidance goes through the servo, so a rerun is proposed (EXP-X04)"),
    dict(id="W-04b", section="Writing help", claim="Tracing in HW1-D: 582 -> 76 um, letters 92 -> 79 %",
         evidence="SIM (HW1-D)", status="CURRENT", model="hw1-d", faults="", classification=UN, rerun=""),
    dict(id="W-05a", section="Writing help", claim="Lead-through HW1-D: bowl within 0.3 mm in 93 % of runs",
         evidence="SIM (HW1-D)", status="CURRENT", model="hw1-d", faults="", classification=UN, rerun=""),
    dict(id="W-05b", section="Writing help", claim="Lead-through in sim2j (dyslexia): words 5.8 -> 6.7 of 10",
         evidence="SIM (sim2j)", status="CURRENT (synthetic)", model="sim2j-legacy", faults="F1, F2, F3",
         classification=NR, rerun="", note="not rerun: wheel-driven; lead-through already judged of little help"),
    dict(id="W-06", section="Writing help", claim="Heel wheel in free writing: moved clean writing 0.41 mm, doubled the "
         "0.3 mm error; helped only at 8 Hz x 2 mm and 4 Hz x 2 mm", evidence="SIM (sim2j)",
         status="CURRENT: wheel retracted (DEC-048)", model="sim2j-legacy", faults="F1, F2, F3", classification=NR,
         rerun="", note="not rerun: the wheel stays retracted by default (DEC-048)"),
    dict(id="W-07", section="Writing help", claim="A writer set on a letter is never turned into another: 0 %",
         evidence="SIM (HW1-D)", status="CURRENT", model="hw1-d", faults="", classification=UN, rerun=""),
    dict(id="W-08", section="Writing help", claim="App's digital clean copy at 1-2 mm: 97 % words (HW1); letters 41 -> 83 %",
         evidence="SIM (HW1)", status="CURRENT (synthetic)", model="hw1-synthetic", faults="", classification=UN, rerun=""),
    dict(id="W-09", section="Writing help", claim="Spelling help: misspellings caught 63 % / 34 %", evidence="CALC, SIM",
         status="CURRENT, UNPROVEN", model="letters-lm", faults="", classification=UN, rerun=""),
    dict(id="W-10", section="Writing help", claim="Spelling help fixed on paper: 3.0-3.4 of 10", evidence="SIM, ASSUMED "
         "responses", status="UNPROVEN", model="letters-lm", faults="", classification=UN, rerun=""),
    dict(id="W-11", section="Writing help", claim="Reading letters while written: 82 %", evidence="CALC and SIM on real "
         "letters", status="CURRENT", model="letters-lm", faults="", classification=UN, rerun=""),
    dict(id="W-12", section="Writing help", claim="Word completion: top-3 after one letter 52-56 %", evidence="CALC",
         status="CURRENT", model="calc", faults="", classification=NS, rerun=""),
    dict(id="W-13", section="Writing help", claim="Shape assist: letters 41.4 -> 41.9 %", evidence="SIM (HW1)",
         status="CURRENT: not adopted", model="hw1-synthetic", faults="", classification=UN, rerun=""),
    dict(id="W-14", section="Writing help", claim="The pen writing an accepted word: 95 % at +-6 mm, 23 % at +-4 mm, 0 % at "
         "+-1-2 mm", evidence="SIM (kinematics only)", status="CURRENT", model="ai3-kinematic", faults="F11",
         classification=SA, rerun="",
         note="the pass: every historic completion fails the sampled motion screen; bounded references admitted "
              "0/520 at 1.059 mm, 5/520 at 1.5 mm, 495/520 at 6 mm (references, not execution)"),
    # ------------------------------------------------------------------ Hardware
    dict(id="H-01", section="Hardware", claim="The nib's reach at the ball: B1 +-1.06 mm (+-1.5 mm option)",
         evidence="CALC", status="CURRENT as geometry", model="calc", faults="", classification=NS, rerun="",
         note="the pass adds a 24 mm / 1.5 mm conditional candidate (CALC)"),
    dict(id="H-02a", section="Hardware", claim="Rev K coil power 17.8-36.3 mW with 1 mm tremor (CALC)", evidence="CALC",
         status="CURRENT (unproven)", model="calc", faults="F5, F6, F7", classification=NS, rerun="",
         note="the pass: REQUIRES RECOMPUTATION; this study reports the SIM power of the corrected nib instead"),
    dict(id="H-02b", section="Hardware", claim="B1 drew 14.8 mW while correcting in study B's simulation; -29 % at "
         "40/46 Hz", evidence="SIM (sim2, bnib)", status="CURRENT", model="sim2-bnib", faults="F5, F6, F7, F8",
         classification=RR, rerun="results/rebaseline/bnib_rerun.json"),
    dict(id="H-02c", section="Hardware", claim="Rev J (C1S) measured about 2.3 W in every mode in the physics simulator",
         evidence="SIM (sim2j)", status="SUSPENDED", model="sim2j-legacy", faults="F1, F2", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (P_total, P_nose)"),
    dict(id="H-03a", section="Hardware", claim="Rev K 23.5-48.6 h per charge (CALC)", evidence="CALC",
         status="CURRENT (unproven)", model="calc", faults="F5, F6, F7", classification=NS, rerun="",
         note="the pass: REQUIRES RECOMPUTATION"),
    dict(id="H-03b", section="Hardware", claim="Study B 33.5 h in simulation", evidence="SIM (bnib)",
         status="SUPERSEDED by the Rev K range", model="sim2-bnib", faults="F5, F6, F7, F8", classification=RR,
         rerun="results/rebaseline/bnib_rerun.json (battery_h from the simulated nib power)"),
    dict(id="H-03c", section="Hardware", claim="Rev J at the simulated 2.3 W: the 2.22 Wh cell lasts about 1 h",
         evidence="CALC on SIM (sim2j)", status="SUSPENDED", model="sim2j-legacy", faults="F1, F2", classification=RR,
         rerun="results/rebaseline/sim2j_cards.json (P_total under causal sensing; hours = 2.22 Wh / P)"),
    dict(id="H-04a", section="Hardware", claim="Rev J.1 at the simulated 2.68 W: C1S coil passes 120 C after about 22 s",
         evidence="CALC; SIM (sim2j)", status="SUSPENDED", model="sim2j-legacy", faults="F1, F2", classification=NR,
         rerun="", note="not rerun: the C1S nose is not carried forward (DEC-050); sim2j_cards.json gives the causal "
                        "servo's power for the same pen, which a thermal update can use"),
    dict(id="H-04b", section="Hardware", claim="Study B's two-node model: skin 30.6 C; coil 31.2 C after 30 min at 35 deg "
         "with 2 mm tremor (at the simulated nib power)", evidence="CALC; SIM (bnib thermal run)",
         status="CURRENT (Rev K unproven)", model="sim2-bnib", faults="F5, F6, F7, F8", classification=NR, rerun="",
         note="not rerun: the thermal run was not repeated; the coil rise scales with the nib power, which task 3 "
              "re-simulates (bnib_rerun.json), so a CALC update follows from it"),
    dict(id="H-04c", section="Hardware", claim="Rev K: web of the hand 30.6 C; front finger pad 35.9 / 37.6 C (fin model)",
         evidence="CALC", status="CURRENT (unproven)", model="calc", faults="F5, F6, F7", classification=NS, rerun="",
         note="the engineering pass marks Rev K budgets REQUIRES RECOMPUTATION"),
    dict(id="H-05", section="Hardware", claim="Mass and length", evidence="CALC", status="CURRENT", model="calc",
         faults="", classification=NS, rerun=""),
    dict(id="H-06", section="Hardware", claim="Gimbal strength", evidence="CALC", status="CURRENT", model="calc",
         faults="", classification=NS, rerun=""),
    dict(id="H-07", section="Hardware", claim="Heel-wheel push on the hand", evidence="CALC", status="UNPROVEN",
         model="calc", faults="", classification=NS, rerun=""),
    dict(id="H-08", section="Hardware", claim="Rev K fit checks", evidence="CALC; PROPOSED DESIGN", status="CURRENT",
         model="calc", faults="F6", classification=NS, rerun=""),
    dict(id="H-09", section="Hardware", claim="Servo bandwidth: Rev K 46 Hz at the worst stuck-ball mode; at 40/46 Hz the "
         "corrected ink error rose 7 % and power fell 29 % (2 tuning writers, one seed)", evidence="CALC; SIM",
         status="CURRENT (marginal)", model="sim2-revk-servo", faults="F6, F7, F3", classification=RR,
         rerun="results/rebaseline/bnib_rerun.json (servo ladder: 80/100 against 40/46 Hz, corrected loads)"),
    dict(id="H-10", section="Hardware", claim="Seeing the fresh ink (Rev K)", evidence="CALC", status="UNPROVEN",
         model="calc", faults="", classification=NS, rerun=""),
    dict(id="H-11", section="Hardware", claim="Rev K pen lift", evidence="CALC", status="UNPROVEN", model="calc",
         faults="", classification=NS, rerun=""),
    dict(id="H-12", section="Hardware", claim="Unit cost", evidence="MFR; ASSUMPTION", status="UNPROVEN", model="calc",
         faults="", classification=NS, rerun=""),
    dict(id="H-13", section="Hardware", claim="Beryllium in the nib's wires", evidence="MFR/LIT", status="CURRENT",
         model="calc", faults="", classification=NS, rerun=""),
    dict(id="H-14", section="Hardware", claim="Page sensor: for the trackers on real inputs a DeltaPen-class sensor "
         "changed results by at most 0.1 word and 0.01 mm (study R)", evidence="ASSUMPTION; SIM",
         status="UNPROVEN", model="hw1-real-v1", faults="F4", classification=RR,
         rerun="results/rebaseline/page_v2.json (ideal vs v1 vs v2)"),
    dict(id="H-15", section="Hardware", claim="Km: at 0.7x the C1S nose sags under the static load (4.2 W; 62 % letters "
         "in tremor-free writing, SIM)", evidence="CALC; SIM", status="UNPROVEN, contested", model="sim2j-legacy",
         faults="F1, F2", classification=NR, rerun="", note="not rerun: C1S nose not carried forward (DEC-050)"),
    # ------------------------------------------------------------------ Simulation
    dict(id="S-01", section="Simulation", claim="sim2 matches the earlier hand-pen model: 56/56 within 3.1 %",
         evidence="SIM against SIM", status="CURRENT as verification", model="sim2-h1check", faults="",
         classification=UN, rerun="",
         note="the H1 check keeps the legacy optimistic settings on purpose (h1_check_config); the pass reran the H1 "
              "comparison (slow test) and it passes; it is verification, not validation"),
    dict(id="S-02a", section="Simulation", claim="Synthetic writers v2: speed and 2/3 law match literature; 8-12 Hz share "
         "10-12 % against 1.3-1.7 %", evidence="SIM against LIT", status="Known flaw", model="writer-model",
         faults="", classification=UN, rerun=""),
    dict(id="S-02b", section="Simulation", claim="On v2 writers the listening estimators lost more than G4",
         evidence="SIM (sim2j)", status="Known flaw", model="sim2j-legacy", faults="F1, F2, F3", classification=NR,
         rerun="", note="not rerun: a ranking of estimators on the same servo; minor"),
    dict(id="S-03", section="Simulation", claim="RL for the nose in the physics simulator: not trained (smoke run only)",
         evidence="SIM (smoke)", status="No result", model="sim2j-rl", faults="F9, F1, F2", classification=SA, rerun="",
         note="the pass trained six PPO policies in two protocols with the repaired reward; none qualified"),
]

FIELDS = ("id", "section", "claim", "evidence", "status", "model", "model_detail", "faults", "classification",
          "rerun", "note")


def rows() -> List[Dict]:
    out = []
    for r in ROWS:
        d = {k: r.get(k, "") for k in FIELDS}
        d["model_detail"] = MODELS[r["model"]]
        out.append(d)
    return out


def check() -> List[str]:
    """Integrity of the register (used by the tests): unique ids, known codes, a reason for every not-rerun row, a
    results file for every rerun row, no unknown model or fault."""
    errs = []
    ids = [r["id"] for r in ROWS]
    if len(ids) != len(set(ids)):
        errs.append("duplicate ids")
    for r in ROWS:
        if r["classification"] not in (UN, RR, NR, SA, NS):
            errs.append(f"{r['id']}: unknown classification")
        if r["model"] not in MODELS:
            errs.append(f"{r['id']}: unknown model {r['model']}")
        for f in [x.strip().split(" ")[0] for x in r.get("faults", "").split(",") if x.strip()]:
            if f not in FAULTS:
                errs.append(f"{r['id']}: unknown fault {f}")
        if r["classification"] == NR and not r.get("note", "").startswith("not rerun"):
            errs.append(f"{r['id']}: AFFECTED_NOT_RERUN needs a 'not rerun: why' note")
        if r["classification"] == RR and "results/rebaseline/" not in r.get("rerun", ""):
            errs.append(f"{r['id']}: AFFECTED_RERUN needs the results file")
        if r["classification"] in (RR, NR) and not r.get("faults"):
            errs.append(f"{r['id']}: affected row without a fault")
    return errs


def to_csv() -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows():
        w.writerow(r)
    return buf.getvalue()


def summary() -> Dict:
    c: Dict[str, int] = {}
    for r in ROWS:
        c[r["classification"]] = c.get(r["classification"], 0) + 1
    sim = [r for r in ROWS if r["classification"] != NS]
    return {"n_rows": len(ROWS), "n_sim_rows": len(sim), "by_classification": c,
            "by_model": {m: sum(1 for r in sim if r["model"] == m) for m in MODELS if any(r["model"] == m for r in sim)}}


def markdown_table(include_not_sim: bool = False) -> str:
    lines = ["| Id | Claim (short) | Model | Faults | Classification | Rerun / reason |", "|---|---|---|---|---|---|"]
    esc = lambda s: str(s).replace("|", "\\|")          # noqa: E731  (a '|' inside a cell ends the cell)
    for r in ROWS:
        if r["classification"] == NS and not include_not_sim:
            continue
        why = r.get("rerun") or r.get("note") or ""
        lines.append(f"| {r['id']} | {esc(r['claim'])} | {r['model']} | {esc(r['faults'] or '-')} | "
                     f"{r['classification']} | {esc(why)} |")
    return "\n".join(lines)


def write(out_dir=RESULTS_DIR) -> Dict:
    from . import common as CM
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "impact_register.csv").write_text(to_csv())
    body = {"what": "impact register of the preserved upstream claims register (docs/claims_register.md)",
            "evidence": "CALCULATION (a reading of documents and code paths); no simulation",
            "models": MODELS, "faults": FAULTS, "summary": summary(), "rows": rows()}
    CM.write_result("impact_register", body, body["evidence"],
                    inputs=("docs/claims_register.md", "rebaseline/impact.py"))
    return body["summary"]


if __name__ == "__main__":
    import json
    errs = check()
    print(json.dumps(write(), indent=1))
    print("integrity:", errs or "ok")
