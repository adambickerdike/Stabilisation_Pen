"""Proposed ledger rows (results/readable/evidence_rows.csv): the 23-column header of docs/evidence.csv, CRLF line endings.

Only DERIVED rows (this study's own simulation and calculation); no new literature was used.  Ids checked against
docs/evidence.csv and every results/*/evidence_rows.csv at the time of writing (see ID_NOTE); the lead may renumber.
"""
from __future__ import annotations

import csv
import io
from typing import Dict, List

import numpy as np

from . import REPO_ROOT
from . import common as CM

ID_NOTE = ("ids chosen above the highest in docs/evidence.csv (ACT-144, EML-103 at the time of writing) and not used in "
           "any results/*/evidence_rows.csv")


def header() -> List[str]:
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def _f(x, nd=2):
    try:
        x = float(x)
    except Exception:
        return "-"
    return f"{x:.{nd}f}" if np.isfinite(x) else "-"


def _ci(b, nd=2):
    if not b:
        return "-"
    return f"{_f(b.get('mean'), nd)} [{_f(b.get('lo'), nd)}-{_f(b.get('hi'), nd)}]"


def rows(out: Dict) -> List[Dict]:
    a = out.get("answers") or {}
    e13 = a.get("e13") or {}
    tun, tci = e13.get("tuning") or {}, e13.get("tuning_ci95") or {}
    tst, sci = e13.get("test") or {}, e13.get("test_ci95") or {}

    def thr(v, c):
        s = _f(v)
        if c and c.get("lo") is not None:
            s += f" [{_f(c.get('lo'))}-{_f(c.get('hi'))}]"
        return s
    common = {"year": "2026", "source_type": "derived calculation", "evidence_class": "numerical simulation",
              "access_level": "full text", "participants_or_bench": "Simulated (real recorded inputs: UNIPEN hpb2 "
              "writers, UCI PD tip tremor, Zenodo ET hand tremor; study R's tuning and test splits)",
              "transferability": "low", "transferability_reason": "Simulation with real inputs and an AI reader, not "
              "a measurement of people or of a pen", "retrieved": "2026-09-30", "search_query": "n/a (derived)",
              "lead_verification": ""}
    g = e13.get("gain_at_r_plus2_test") or {}
    r1 = dict(common, id="EML-104",
              topic="How much tremor may be left at the pen tip for words to be readable (EXP-E13, study F simulation, "
                    "HW1)",
              citation="This study's simulation (readable/): model HW1, study R's real-input library and reader; the "
                       "curve fitted on R's tuning split, frozen, confirmed once on R's test split",
              doi_or_url="results/readable/readable.json (e13); results/readable/frozen.json",
              task_or_setup="The Rev J nose driven by perfect knowledge made imperfect three ways: (a) the tremor scaled "
                            "(amplitude error), (b) the perfect estimate delayed 5.2-25 ms (lag error), (c) perfect + "
                            "band-limited noise (f0 +- 2 Hz); severe (1.72 mm) and moderate (0.24 mm) classes; words "
                            "read by TrOCR base (literal) against R's tip-tremor measure; log-logistic fit with a "
                            "writer bootstrap",
              comparator="Ordinary pen; the same notes without tremor",
              key_quantitative_findings=(
                  f"Tuning split: residual for +2 words over the ordinary pen (DEC-055's words line) "
                  f"{thr(tun.get('r_plus2_mm'), tci.get('r_plus2_mm'))} mm; for 80 % of the tremor-free words "
                  f"{thr(tun.get('r_80_mm'), tci.get('r_80_mm'))} mm; within 1 word of the clean notes "
                  f"{thr(tun.get('r_within1_mm'), tci.get('r_within1_mm'))} mm (ordinary pen {_f(tun.get('w_ord_severe'))}, "
                  f"clean {_f(tun.get('w_clean'))} words of 10). Test split: +2 words at "
                  f"{thr(tst.get('r_plus2_mm'), sci.get('r_plus2_mm'))} mm; 80 % at "
                  f"{thr(tst.get('r_80_mm'), sci.get('r_80_mm'))} mm; at the level aimed at the tuning +2 residual the "
                  f"test gain was {_ci(g.get('gain'))} words"),
              units_and_conditions="mm (peak = sqrt(2) x RMS of the major axis of ink - intended in contact, f0 +- 2 Hz); "
                                   "words of 10; SIMULATION",
              locator="docs/readable_target.md; results/readable/fig_e13_curve.png",
              limitations="Simulation; composed inputs (healthy writers' notes + patients' tremor); AI reader stands in "
                          "for people (EXP-R03); 5 tuning and 9 test writers; residuals are idealised shapes; R's tremor "
                          "waveforms keep only f0 +- 2 Hz and 2 f0 +- 2 Hz",
              relevance_to_design="The target any tremor estimator must reach at the severe class",
              design_implication="An estimator must leave no more than the +2-words residual at the tip at the severe "
                                 "class to meet DEC-055's words line; the test split confirms the order of magnitude",
              stream="EML")
    e11 = (a.get("e11") or {}).get("by_design") or {}

    def e11txt(k):
        v = e11.get(k) or {}
        return (f"{k}: clean writing moved mean {_f(v.get('clean_um_mean'), 1)} um, worst writer "
                f"{_f(v.get('clean_um_worst_writer'), 1)} um ({v.get('writers_over_50um')} over 50 um); severe words gain "
                f"{_ci(v.get('severe_words_gain'))}; severe tip tremor x ordinary {_ci(v.get('severe_ratio_to_ordinary'))}")
    r2 = dict(common, id="EML-105",
              topic="Per-writer calibration of the tremor estimator's authority gate on the user's own clean writing "
                    "(EXP-E11, REQ-CTRL-016; study F simulation, HW1; information only)",
              citation="This study's simulation (readable/e11.py): rule chosen on R's tuning split (each tuning note "
                       "calibrated on its writer's other note), applied once to R's test writers (calibrated on a "
                       "different note of the same writer)",
              doi_or_url="results/readable/readable.json (e11)",
              task_or_setup="Study E's frozen ai2 TCN + soft size gate (D1), the real-data TCN + gate (D2), the listening "
                            "AKF + confidence gate (D3); the gate's opening threshold set from the quantile of the "
                            "estimate's size on the writer's own clean note (grid of 24 rules)",
              comparator="The same designs with study E's frozen gates",
              key_quantitative_findings="; ".join(e11txt(k) for k in ("D1|cal", "D2|cal", "D1|frozen", "D2|frozen")
                                                   if k in e11),
              units_and_conditions="um RMS on the notes without tremor; words of 10; SIMULATION",
              locator="docs/readable_target.md; results/readable/fig_e11_clean.png",
              limitations="Study E has already seen the test split: a feasibility check only; one clean calibration note "
                          "per writer; a severe-tremor user has no tremor-free writing to calibrate on; EXP-R01 "
                          "shadow-mode data are needed",
              relevance_to_design="REQ-CTRL-016 (per-user gates) and DEC-061's revisit trigger",
              design_implication="Calibrate the gate on the user's own writing and only ever raise its threshold: it "
                                 "kept every simulated test writer within 50 um for both networks; it adds no tremor "
                                 "removal, so no words are gained (docs/readable_target.md s5)",
              stream="EML")
    gp = (a.get("gap") or {}).get("chains") or {}
    tt = gp.get("test") or gp.get("tuning") or {}

    def chain(k):
        st = tt.get(k) or []
        return " -> ".join(f"{s['config']} {_f((s.get('tip_tremor_mm') or {}).get('mean'))} mm"
                           f" ({_f((s.get('words_via_curve') or {}).get('mean'), 1)} words)" for s in st)
    r3 = dict(common, id="EML-106",
              topic="Where the gap between causal tremor estimators and perfect knowledge lies: prediction, sensing or "
                    "separating tremor from writing (study F simulation, HW1)",
              citation="This study's simulation and calculation (readable/gap.py) on R's tuning and test splits",
              doi_or_url="results/readable/readable.json (gap)",
              task_or_setup="Severe class: perfect knowledge; a causal linear (AR) predictor on the true tremor over the "
                            "pen's horizon (4.9 ms); estimators fed the pen's sensor streams of the tremor alone; the "
                            "same estimators on tremor + writing; each estimate drives the nose on the full case; "
                            "residuals mapped to words through the frozen E13 curve",
              comparator="Perfect knowledge; study E's estimators",
              key_quantitative_findings=("Test split, tip tremor (words via the curve): " + " | ".join(
                  f"{k}: {chain(k)}" for k in ("fir_raw", "ai2tcn_gated", "net_gated") if k in tt)),
              units_and_conditions="mm (R's measure); words of 10 via the curve (CALC); SIMULATION",
              locator="docs/readable_target.md; results/readable/fig_gap.png",
              limitations="R's tremor waveforms are band-limited by construction (a broadband check on raw ET "
                          "recordings is reported); the linear filter is one estimator design; composed inputs",
              relevance_to_design="Whether to invest in prediction or in sensing and separation",
              design_implication="Invest in separating tremor from writing first and in a drift-free position reference "
                                 "in the tremor band second; prediction and latency need no investment "
                                 "(docs/readable_target.md s7)",
              stream="EML")
    bb = ((out.get("gap") or {}).get("predictor") or {})
    r4 = dict(common, id="ACT-145",
              topic="Predicting real tremor over the pen's 4.9 ms horizon is not the limit (study F calculation)",
              citation="This study's calculation (readable/gap.py) on the true handle tremor of R's tuning cases and on "
                       "raw Zenodo ET tuning recordings (broadband check)",
              doi_or_url="results/readable/readable.json (gap.predictor); readable/build/cache/gap/predictor.json",
              evidence_class="numerical simulation and calculation on recorded data",
              task_or_setup="Direct least-squares AR predictor (Delta and order chosen on the tuning split, cross-fitted "
                            "by fold): newest sample 1.52 ms old (IMU path), prediction to the servo delay (3.39 ms); "
                            "hold (no prediction) as comparator; horizons 3.4-10 ms",
              comparator="No prediction (hold)",
              key_quantitative_findings=(f"Cross-fitted in-band residual on the severe tuning cases: AR "
                                         f"{_f((bb.get('choice') or {}).get('cv_residual_mm', np.nan) * 1e3, 1)} um, "
                                         f"hold {_f((bb.get('hold_cv_residual_mm') or np.nan) * 1e3, 1)} um (at 1.72 mm)"
                                         + _bb_txt(bb)),
              units_and_conditions="um (R's measure on the prediction error); CALC",
              locator="docs/readable_target.md",
              limitations="Band-limited library waveforms; broadband check on ET hand recordings only (PD tip data are "
                          "pixel-quantised)",
              relevance_to_design="The prediction horizon of the Rev J/Rev K command path",
              design_implication="Prediction does not need investment; the estimate itself does",
              stream="ACT")
    rc = out.get("reach") or {}
    rr = rc.get("rows") or {}
    rs = [r1, r2, r3, r4]
    if rr:
        def t(k):
            return _ci((rr.get(k) or {}).get("tip_tremor_mm"))
        qm = rc.get("q_oracle_contact") or {}
        r5 = dict(common, id="EML-107",
                  topic="Reach a nib needs for the readable target at the severe class (study F simulation, HW1; "
                        "tuning split)",
                  citation="This study's simulation (readable/reach.py): the Rev J nose with its usable travel limited "
                           "to +-3, +-2, +-1.5 and +-1.0 mm, driven with perfect knowledge on R's tuning cases",
                  doi_or_url="results/readable/readable.json (reach); results/readable/fig_reach.png",
                  task_or_setup="Severe class (1.72 mm), 20 tuning cases (5 writers, PD and ET); perfect knowledge and "
                                "perfect knowledge scaled to the frozen +2-words residual; tip tremor (R's measure); "
                                "words read for perfect knowledge at +-1.5 and +-1.0 mm",
                  comparator="The same runs with the +-6 mm Rev J nose",
                  key_quantitative_findings=(
                      f"Perfect knowledge leaves at the tip: +-6 mm {t('6|oracle')} mm; +-3 mm {t('3|oracle')}; "
                      f"+-2 mm {t('2|oracle')}; +-1.5 mm {t('1.5|oracle')}; +-1.0 mm {t('1|oracle')}. Words read "
                      f"at +-1.5 mm {_ci((rr.get('1.5|oracle') or {}).get('words_read'), 1)} of 10 (gain over the "
                      f"ordinary pen {_ci((rr.get('1.5|oracle') or {}).get('gain_read'), 1)}), at +-1.0 mm "
                      f"{_ci((rr.get('1|oracle') or {}).get('words_read'), 1)} (gain "
                      f"{_ci((rr.get('1|oracle') or {}).get('gain_read'), 1)}): below DEC-055's +2 at +-1.0 mm. An "
                      f"estimate that leaves the +2 residual at full reach leaves {t('1.5|a_r2')} mm at +-1.5 mm, "
                      f"{t('2|a_r2')} at +-2 mm, {t('3|a_r2')} at +-3 mm. The "
                      f"perfect-knowledge command in contact: 99th percentile of its 2-D magnitude "
                      f"{_f((qm.get('p99_mm') or {}).get('mean'), 1)} mm, above 1.0 mm "
                      f"{_f(100 * ((qm.get('share_above_1mm') or {}).get('mean') or np.nan), 0)} % of the time"),
                  units_and_conditions="mm (R's measure); words of 10; SIMULATION",
                  locator="docs/readable_target.md s8",
                  limitations="The Rev J nose's mass and servo with its travel cut, not the B1 nib's own dynamics; "
                              "tuning split only; one seed per case",
                  relevance_to_design="DEC-050 / DEC-060 (the nib's reach) against the readable target",
                  design_implication="At the severe class a +-1.0 mm nib cannot meet DEC-055's words line even with "
                                     "perfect knowledge; +-1.5 mm can with perfect knowledge; an estimator with its own "
                                     "error needs about +-2-3 mm (docs/readable_target.md s8)",
                  stream="EML")
        rs.append(r5)
    return rs


def _bb_txt(bb: Dict) -> str:
    b = ((bb.get("broadband") or {}).get("by_horizon") or {}).get("imu") or {}
    if not b:
        return ""
    return (f"; on {(bb.get('broadband') or {}).get('n_records')} raw ET recordings made displacement in a broad band "
            f"(f0 - 2 Hz to 20 Hz) the AR's in-band error at 4.9 ms is "
            f"{_f(100 * ((b.get('broad') or {}).get('ar_inband_share_mean') or np.nan), 2)} % of the tremor, "
            f"{_f(100 * ((b.get('broad') or {}).get('hold_inband_share_mean') or np.nan), 1)} % with no prediction")


def write(out: Dict, path) -> int:
    h = header()
    rs = rows(out)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(h)
    for r in rs:
        w.writerow([str(r.get(k, "")) for k in h])
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return len(rs)
