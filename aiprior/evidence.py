"""Proposed ledger rows (ACT-76...ACT-80, EML-40...EML-42) with the exact 23-column header of docs/evidence.csv.

Every row is this study's own SIMULATION or CALCULATION (derived, low transferability); the numbers are filled from
aiprior.json at build time.  The lead merges them; docs/evidence.csv is not edited here.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from . import REPO_ROOT

RETRIEVED = "2026-09-28"
TRANSFER = "Simulation on synthetic glyph writers, synthetic tremor and assumed hand, grip, sensor and device parameters (model HW1)"


def header() -> List[str]:
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def _g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return default
        d = d[k]
    return d


def _f(x, fmt="{:.0f}"):
    return "n/a" if x is None else fmt.format(x)


def rows(doc: Dict) -> List[Dict[str, str]]:
    agg = doc.get("aggregate") or {}
    h = agg.get("headlines", {})
    hi, hf, six, lo = h.get("6_10Hz_1_2mm", {}), h.get("8_10Hz_1_2mm", {}), h.get("6Hz_1_2mm", {}), h.get("0.3mm", {})
    free = agg.get("tremor_free", {})
    bk = "tracker_rt" if (doc.get("config") or {}).get("base") else "tracker"
    t1 = _g(doc, "tuning", "t1", "selection") or {}
    t2 = _g(doc, "tuning", "t2", "selection") or {}
    sev_cfg = (doc.get("config") or {}).get("sev")

    def ink(g, v):
        return _f(_g(g, v, "ink_err_um"))

    def pct(g, v, k):
        x = _g(g, v, k)
        return "n/a" if x is None else f"{x:.0%}"
    common = {"year": "2026", "source_type": "derived simulation", "evidence_class": "numerical simulation",
              "access_level": "full text", "participants_or_bench": "none (simulation)", "transferability": "low",
              "transferability_reason": TRANSFER, "retrieved": RETRIEVED, "search_query": "n/a (derived)", "lead_verification": "",
              "doi_or_url": "results/aiprior/aiprior.json"}
    setup = ("aiguide test writers 0-5, 'return library books by friday', hand tremor 6/8/10 Hz x 0.3/1/2 mm peak, seeds 200-203; "
             "model HW1 (adapted writer, drag compensated, hover gating); fusion sensor models; text predictor = aiguide Tatoeba-CC0 n-gram, "
             "top-1 two glyphs ahead; style from the app's clean copy")
    out = [
        dict(common, id="ACT-76", topic="AI letter prediction as a prior inside the Rev H tremor tracker, severe tremor (this study)",
             citation="This ledger's simulation: aiprior/study.py prior_* variants (fusion.context filter on the T0 tracker); results/aiprior/aiprior.json",
             task_or_setup=setup + "; template prior = tremor-referenced cross-track pseudo-measurement, confidence-scaled noise, drop rule T5",
             comparator=f"The same filter without template ({bk}); perfect knowledge",
             key_quantitative_findings=(f"6-10 Hz, 1-2 mm: ink error {bk} {ink(hi, bk)} um; + prior, predicted letters {ink(hi, 'prior_ai_predicted')}; "
                                        f"correct letters {ink(hi, 'prior_ai_correct')}; known text {ink(hi, 'prior_oracle')}; perfect knowledge {ink(hi, 'oracle')} um. "
                                        f"Words read {pct(hi, bk, 'word_acc_app')} -> {pct(hi, 'prior_ai_predicted', 'word_acc_app')}. "
                                        f"Tuning rule T1 adopted: {t1.get('adopted')}"),
             units_and_conditions="Ink error = RMS nearest-point distance of in-contact ink to the intended letters (um); words = app reader with lexicon correction",
             locator="aiprior.json aggregate.headlines; tuning.t1",
             limitations="Synthetic writers and tremor; lumped pen; passive hand; the prior filter's tremor states are the tracker's; estimates from the nose-held run's sensor streams",
             relevance_to_design="Whether the app's predicted letters can help the pen tell tremor from writing in real time",
             design_implication="See key findings: the template prior gives little beyond the tracker it sits on; keep it off by default until real writing (EXP-E01) shows otherwise",
             stream="ACT"),
        dict(common, id="ACT-77", topic="Partial nose guidance toward AI-predicted letter templates, severe tremor (this study)",
             citation="This ledger's simulation: aiprior/guide.py, aiprior/study.py guide_* variants; results/aiprior/aiprior.json",
             task_or_setup=setup + "; guidance = (template - tracker-corrected position) minus a slow per-letter offset, authority = confidence gate x tremor-amplitude gate x capture gate, drop rule",
             comparator=f"{bk} alone; perfect knowledge",
             key_quantitative_findings=(f"6-10 Hz, 1-2 mm: ink error {bk} {ink(hi, bk)} um; + guidance, predicted letters {ink(hi, 'guide_ai_predicted')}; "
                                        f"correct letters {ink(hi, 'guide_ai_correct')}; known text {ink(hi, 'guide_oracle')} um. AI share of ink motion "
                                        f"{pct(hi, 'guide_ai_predicted', 'ai_share')} (predicted) / {pct(hi, 'guide_ai_correct', 'ai_share')} (correct). "
                                        f"Wrong letters introduced at full confidence: {_g(hi, 'guide_wrong_full', 'flips')} of {_g(hi, 'guide_wrong_full', 'n_letters')}. "
                                        f"Tuning rule T2 adopted: {t2.get('adopted')}"),
             units_and_conditions="As ACT-76; AI share = path length of (ink - ink with the tracker alone) / (that + the tracker-alone ink path)",
             locator="aiprior.json aggregate.headlines; tuning.t2",
             limitations="Passive hand (neither follows nor resists); the recogniser is lenient; templates learnt from the clean copy of the handle track",
             relevance_to_design="Whether AI templates may steer the ink when tremor is large",
             design_implication="Guidance toward known text (tracing, copying) is the case with a clear benefit; free-writing guidance needs agency and flip tests (EXP-A02)",
             stream="ACT"),
        dict(common, id="ACT-78", topic="A severe-tremor setting of the Rev H accelerometer tracker, without AI (this study; rejected by its safety rules)",
             citation="This ledger's simulation: aiprior/tuning.py stage T0 (tuning writers 100-103, seed 300); test grid variant tracker_sev in results/aiprior/aiprior.json",
             task_or_setup=setup + f"; the Rev H AKF with more tremor-state process noise and output gain {sev_cfg}; the T0 candidate with the lowest 1-2 mm ink error on tuning data",
             comparator="The Rev H tracker of results/opt/inertial_tracker_revh.json (handwriting study)",
             key_quantitative_findings=(f"8-10 Hz, 1-2 mm: ink error {ink(hf, 'tracker')} -> {ink(hf, 'tracker_sev')} um, words {pct(hf, 'tracker', 'word_acc_app')} -> {pct(hf, 'tracker_sev', 'word_acc_app')}; "
                                        f"6 Hz, 1-2 mm: {ink(six, 'tracker')} -> {ink(six, 'tracker_sev')} um, words {pct(six, 'tracker', 'word_acc_app')} -> {pct(six, 'tracker_sev', 'word_acc_app')}; "
                                        f"0.3 mm: {ink(lo, 'tracker')} -> {ink(lo, 'tracker_sev')} um; false correction on tremor-free writing "
                                        f"{_f(_g(free, 'tracker', 'false_correction_um'))} -> {_f(_g(free, 'tracker_sev', 'false_correction_um'))} um. "
                                        "On tuning data every such candidate failed the false-correction (<= 30 um) and 0.3 mm rules"),
             units_and_conditions="As ACT-76; false correction = RMS ink displacement vs the nose held on tremor-free writing",
             locator="aiprior.json aggregate.headlines (tracker_sev), aggregate.tremor_free, tuning.t0",
             limitations="Tuned on 4 synthetic writers and one seed; the setting trades tremor removal against false correction on real writing, which is unmeasured",
             relevance_to_design="The largest lever in this study is the tracker's own setting, not the AI; its cost is moving the writer's own strokes",
             design_implication="Test a severe-tremor mode, switched on only by the 20 s calibration for large tremor, on recorded ET writing (EXP-W02); not adopted",
             stream="ACT"),
        dict(common, id="ACT-79", topic="Digital clean copy of the recorded tip path (non-causal, app only), severe tremor (this study)",
             citation="This ledger's simulation: aiprior/cleancopy.py (non-causal Wiener smoother, zero-phase band-stop); results/aiprior/aiprior.json",
             task_or_setup=setup + "; the recorded tip path = page sensor + Hall sensor with noise; the app estimates the tremor line from the recording",
             comparator="The causal pen's ink",
             key_quantitative_findings=(f"6-10 Hz, 1-2 mm: clean copy of the {bk} ink {ink(hi, 'clean_' + bk)} um, letters {pct(hi, 'clean_' + bk, 'recognition')}, "
                                        f"words {pct(hi, 'clean_' + bk, 'word_acc_app')} (paper ink {ink(hi, bk)} um, words {pct(hi, bk, 'word_acc_app')}); "
                                        f"clean copy of the nose-held ink {ink(hi, 'clean_revH_off')} um; 0.3 mm {ink(lo, 'clean_' + bk)} um"),
             units_and_conditions="As ACT-76, on the digital copy",
             locator="aiprior.json aggregate.headlines (clean_*)",
             limitations="Synthetic tremor is a narrow line with 0.3 Hz wander; real tremor can be broader and change with posture; digital only",
             relevance_to_design="What the notes can look like in the app, independent of the physical correction",
             design_implication="Ship the clean copy as a derived layer next to the untouched ink (DEC-020 conventions); measure on recorded notes (EXP-A03)",
             stream="ACT"),
        dict(common, id="ACT-80", topic="Safety of AI help at small tremor, with wrong predictions and on tremor-free writing (this study)",
             citation="This ledger's simulation: aiprior/study.py (flips, broken letters, false correction); results/aiprior/aiprior.json",
             task_or_setup=setup,
             comparator=f"{bk} alone",
             key_quantitative_findings=(f"0.3 mm ink error: {bk} {ink(lo, bk)}, prior {ink(lo, 'prior_ai_predicted')}, guidance {ink(lo, 'guide_ai_predicted')} um. "
                                        f"Wrong letter at full confidence, 1-2 mm: flips prior {_g(hi, 'prior_wrong_full', 'flips')}, guidance {_g(hi, 'guide_wrong_full', 'flips')} "
                                        f"of {_g(hi, 'guide_wrong_full', 'n_letters')} letters. False correction: prior {_f(_g(free, 'prior_ai_predicted', 'false_correction_um'))}, "
                                        f"guidance {_f(_g(free, 'guide_ai_predicted', 'false_correction_um'))} um"),
             units_and_conditions="Flips = letters newly read as the wrongly predicted letter against the tracker underneath",
             locator="aiprior.json aggregate.headlines, aggregate.tremor_free",
             limitations="The recogniser is lenient; a person may read hybrids differently",
             relevance_to_design="The pen must not write a letter the user did not start",
             design_implication="Keep the amplitude gate, the capture gate and the drop rule in any AI mode; test with deliberately wrong templates (EXP-A02)",
             stream="ACT"),
    ]
    te = agg.get("template_error", {})
    pr = agg.get("prediction", {})
    out += [
        dict(common, id="EML-40", topic="Letter templates in the writer's style at severe tremor, learnt from the app's clean copy (this study)",
             citation="This ledger's calculation: aiprior/core.py templates, template_error_um; results/aiprior/aiprior.json aggregate.template_error",
             source_type="derived calculation", evidence_class="calculation", task_or_setup=setup,
             comparator="The intended letters",
             key_quantitative_findings="; ".join(f"{c} at {a}: total {_f(v.get('total_um'))} um, after per-letter offset {_f(v.get('after_offset_um'))}, 3-15 Hz {_f(v.get('band_3_15Hz_um'))}"
                                                 for c, d in te.items() for a, v in d.items() if c == "ai_correct"),
             units_and_conditions="RMS over intended pen-down points of the nearest template point of the same letter (um)",
             locator="aiprior.json aggregate.template_error", evidence_class_note="",
             limitations="Synthetic allographs; anchoring at the tracker-corrected touchdown carries residual tremor",
             relevance_to_design="The template's own error sets how much a prior or guidance can add",
             design_implication="Template error at the letter-detail scale stays at the tremor-band scale (fusion finding) even with the clean copy",
             transferability="low", stream="EML"),
        dict(common, id="EML-41", topic="Text predictor on the study sentence: accuracy and gating two letters ahead (this study)",
             citation="This ledger's calculation: aiguide.lm cached predictor via aiprior/core.py predictions()",
             source_type="derived calculation", evidence_class="calculation", task_or_setup="aiguide Tatoeba-CC0 character 7-gram + word bigram, calibrated; depth 2",
             comparator="none",
             key_quantitative_findings=(f"top-1 correct {_f(pr.get('top1_correct'), '{:.0%}')}; letters guided (c >= 0.5) {_f(pr.get('letters_guided'), '{:.0%}')}; "
                                        f"correct when guided {_f(pr.get('correct_when_guided'), '{:.0%}')}; mean authority {_f(pr.get('mean_authority'), '{:.2f}')}"),
             units_and_conditions="26 letters of 'return library books by friday'", locator="aiprior.json aggregate.prediction",
             limitations="One sentence; example-sentence corpus, not notes", relevance_to_design="How often the AI can act at all",
             design_implication="Most letters get no template; AI help acts on a minority of letters in free writing", stream="EML"),
    ]
    for r in out:
        r.pop("evidence_class_note", None)
    return out


def write_rows(path: Path, doc: Dict) -> None:
    hdr = header()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        for r in rows(doc):
            w.writerow([r.get(k, "") for k in hdr])
