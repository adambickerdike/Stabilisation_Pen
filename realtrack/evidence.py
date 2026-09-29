"""Proposed ledger rows of study E (results/realtrack/evidence_rows.csv), with the exact 23-column header of
docs/evidence.csv and its CRLF line endings.  Only sources opened by this study are listed (with the access level
actually obtained); derived rows carry this study's own simulations and calculations, filled in from realtrack.json.
Ids: ACT-140...144, EML-100...109 (PDT-90...94 and OPT-95...99 unused).  The lead merges them."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
          "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions",
          "locator", "limitations", "relevance_to_design", "transferability", "transferability_reason",
          "design_implication", "retrieved", "search_query", "stream", "lead_verification"]
DATE = "2026-09-29"


def _f(x, nd=2):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "n/a"


def rows(out: Dict) -> List[Dict]:
    R = []
    R.append(dict(
        id="ACT-140", topic="Causal phase and amplitude tracking of tremor with locking and resonant oscillators",
        citation="Rosenblum M, Pikovsky A, Kuehn AA, Busch JL. Real-time estimation of phase and amplitude with application to neural data. Sci Rep. 2021;11:18037",
        year="2021", doi_or_url="https://doi.org/10.1038/s41598-021-97560-5 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC8433321/",
        source_type="journal", evidence_class="numerical simulation and re-analysis of recorded data", access_level="full text (PMC)",
        task_or_setup="Three causal estimators of instantaneous phase and amplitude: a phase-locking oscillator (theta' = omega - eps sin(theta) s(t), frequency updated omega -> omega + K (nu_e - omega) from a linear fit over one to two cycles), a resonant linear oscillator with an integrating unit (x'' + alpha x' + omega^2 x = s(t), mu z' + z = x'), a non-resonant oscillator pair",
        participants_or_bench="Artificial signals; ET accelerometer tremor sampled at 2048 Hz; beta-band brain activity",
        comparator="Hilbert-transform (non-causal) phase and envelope",
        key_quantitative_findings="Tremor parameters: omega ~ 2 pi 4.5 rad/s, eps 30, K 0.5; resonant oscillator alpha = 0.3 omega, mu 500. Cost per sample on a desktop 3.7e-7 (resonant) to 6.7e-7 s (locking). The locking technique works for narrow-band signals like tremor without a band-pass; the causal amplitude of the resonant oscillator follows the envelope better than the Hilbert one at outliers; 'no additional delay' beyond a required causal filter",
        units_and_conditions="rad, s", locator="Methods; tremor example figure", limitations="Phase and amplitude only, no displacement prediction for cancellation; one ET recording; no voluntary motion in the tremor band",
        relevance_to_design="The adaptive-oscillator / PLL family of causal tremor trackers (this study's EPLL candidate)",
        transferability="medium", transferability_reason="Same signal type (tremor acceleration); handwriting adds voluntary motion in the tremor band",
        design_implication="Oscillator trackers are cheap enough for the pen (well under 1 % of the MCU); their limit on real writing is telling tremor from letter-forming motion, not cost",
        retrieved=DATE, search_query="enhanced phase-locked loop tremor frequency amplitude estimation real time", stream="ACT", lead_verification=""))
    R.append(dict(
        id="ACT-141", topic="Adaptive Hopf-oscillator combiner separating tremor from voluntary motion in real time (PD)",
        citation="Xiao F, Zhong B, Wu Y, Wang Y. A Real-Time Bionic Method Inspired by Neural Oscillators for Estimation and Extraction of Pathological Tremor. IEEE J Biomed Health Inform. 2023;27(2):1129-1139",
        year="2023", doi_or_url="https://doi.org/10.1109/JBHI.2022.3222299 ; PMID 36378794", source_type="journal",
        evidence_class="physical human study (recorded signals) and simulation", access_level="abstract only (PubMed E-utilities)",
        task_or_setup="RTBNO: multiple adaptive modified Hopf oscillators in a linear combiner, one part for tremor and one for voluntary motion, updated iteratively in real time",
        participants_or_bench="Simulated action tremor; 20 Parkinson's disease patients", comparator="Existing methods (not named in the abstract)",
        key_quantitative_findings="Rest tremor RMSE 0.0272 +- 0.0077; voluntary motion RMSE 0.0360 +- 0.0097 (pick and put) and 0.0380 +- 0.0083 (drawing); 0.0478 s to process 10 s of data; 'no phase delay'",
        units_and_conditions="units of the recorded signal (not stated in the abstract)", locator="Abstract",
        limitations="Abstract only; units and the voluntary movement's frequency content not given; no handwriting",
        relevance_to_design="Oscillator combiners that model voluntary motion explicitly: the idea behind the AKF's intent states",
        transferability="low", transferability_reason="Drawing and pick-and-place, not handwriting; no ink outcome",
        design_implication="Test on real handwriting before any claim; letter-forming motion shares the tremor band",
        retrieved=DATE, search_query="adaptive oscillator pathological tremor estimation real-time Hopf", stream="ACT", lead_verification=""))
    R.append(dict(
        id="ACT-142", topic="Enhanced phase-locked loop (EPLL): the standard amplitude, frequency and phase loops",
        citation="Abrar S. Design and Analysis of a Higher-Order Enhanced Phase-Locked Loop via the Ahmadi-Chaudhry-Zhang Newton Framework. arXiv:2607.13752 (2026); restates the EPLL of Karimi-Ghartemani and Iravani (IEEE Trans Power Deliv 2002;17(2):617-622) and Wu and Bodson (IEEE Trans Autom Control 2003;48(4):612-618), which were not opened",
        year="2026", doi_or_url="https://arxiv.org/abs/2607.13752", source_type="preprint", evidence_class="analytical and numerical",
        access_level="full text (arXiv HTML)", task_or_setup="Standard EPLL: e = u - rho sin(phi); rho' = mu1 e sin(phi); omega' = mu2 rho e cos(phi); phi' = omega + mu3 rho e cos(phi)",
        participants_or_bench="n/a", comparator="Higher-order EPLL variants",
        key_quantitative_findings="The three coupled loops (amplitude, frequency, phase with a proportional term); the paper addresses slow convergence and undesired oscillation of existing EPLLs",
        units_and_conditions="n/a", locator="Section on the standard EPLL", limitations="Power-systems context; the originals were not opened",
        relevance_to_design="The structure of this study's EPLL tracker (shared phase and frequency, per-axis amplitudes, 2nd harmonic)",
        transferability="medium", transferability_reason="Generic sinusoid tracking; tremor wanders more than grid voltage",
        design_implication="Implementable in a few hundred operations per millisecond on the pen's MCU",
        retrieved=DATE, search_query="Karimi-Ghartemani enhanced phase-locked loop EPLL", stream="ACT", lead_verification=""))
    te = (out.get("test") or {})
    d55 = (te.get("dec055") or {}).get("chosen") or {}
    tab = {(r["kind"], r["class"]): r for r in (te.get("one_number_table") or [])}

    def wd(kind, cls, key):
        v = (tab.get((kind, cls)) or {}).get(key) or {}
        return f"{_f(v.get('mean'), 1)} [{_f(v.get('lo'), 1)}-{_f(v.get('hi'), 1)}]" if v else "n/a"
    fz = out.get("frozen") or {}
    R.append(dict(
        id="EML-100", topic="The best causal tremor tracker found on real inputs, tested once on held-out writers and patients (study E simulation, HW1)",
        citation="This study's simulation (realtrack/): model HW1, study R's real-input library; every choice on R's tuning split, frozen, then R's test split run once",
        year="2026", doi_or_url="results/realtrack/realtrack.json", source_type="derived calculation", evidence_class="numerical simulation",
        access_level="full text", task_or_setup=f"Chosen design: {fz.get('chosen_name')} ({fz.get('why')}); DeltaPen-class page sensor; R's measures and writer bootstrap",
        participants_or_bench="Simulated (real recorded inputs; 9 test writers; PD and ET test patients)", comparator="Ordinary pen, R's Rev J gated tracker, sim2j's G4, perfect knowledge",
        key_quantitative_findings=(f"Readable words of 10 (ordinary / best causal / perfect): severe pooled {wd('all', 'severe', 'ordinary')} / "
                                   f"{wd('all', 'severe', 'best_causal')} / {wd('all', 'severe', 'perfect')}; gain {_f(d55.get('words_gain_mean'), 2)} "
                                   f"[{_f(d55.get('words_gain_lo'), 2)}, {_f(d55.get('words_gain_hi'), 2)}]; clean writing moved {_f(d55.get('clean_change_um_mean'), 1)} um; "
                                   f"DEC-055 passed: {d55.get('passes')}"),
        units_and_conditions="words of 10; um RMS; SIMULATION", locator="docs/real_tracker.md; results/realtrack/fig_words_read.png",
        limitations="Simulation; composed inputs (healthy writers' notes + patients' tremor); AI reader; PROPOSED DESIGN; the tracker sees the nose-held run's sensor streams (R's convention)",
        relevance_to_design="Whether a causal estimator on the pen can deliver the legibility the Rev J nose could give",
        transferability="low", transferability_reason="Simulation with real inputs, not a measurement",
        design_implication="See docs/real_tracker.md (DEC-060/061 proposals)", retrieved=DATE, search_query="n/a (derived)", stream="EML", lead_verification=""))
    sep = out.get("separability") or {}
    k1 = "line ratio, page track 4 s (ai2's detector)"
    s1 = (sep.get(k1) or {}).get("_share_above") or {}
    R.append(dict(
        id="EML-101", topic="Real handwriting and real tremor look alike to a tremor-line detector (study E, tuning split)",
        citation="This study's calculation (realtrack/analysis.py separability) on study R's tuning split",
        year="2026", doi_or_url="results/realtrack/realtrack.json (separability)", source_type="derived calculation", evidence_class="numerical simulation",
        access_level="full text", task_or_setup="ai2's running detector (Welch over 4 s, line ratio over the running-median floor) on the page track and on an accelerometer-only track; the listening estimate's amplitude",
        participants_or_bench="Simulated (5 tuning writers, tuning patients)", comparator="Same notes without tremor",
        key_quantitative_findings=(f"Share of pen-down time with a line ratio > 5 (page track): no tremor {_f((s1.get('clean') or {}).get('5'), 2)}, "
                                   f"moderate {_f((s1.get('moderate') or {}).get('5'), 2)}, severe {_f((s1.get('severe') or {}).get('5'), 2)}"),
        units_and_conditions="shares of pen-down time; DeltaPen-class page sensor", locator="fig_detector_separability.png",
        limitations="Healthy writers' notes; the detector's floor is a running median over +-3 Hz", relevance_to_design="Why the gated trackers rarely open on real tremor",
        transferability="medium", transferability_reason="Real writing and real tremor recordings", design_implication="Gate on size and consistency, not on a spectral line; measure patients' own writing (EXP-R01)",
        retrieved=DATE, search_query="n/a (derived)", stream="EML", lead_verification=""))
    dl = out.get("delay") or {}
    dc = (dl.get("decompose") or {}).get("levels") or {}
    R.append(dict(
        id="ACT-143", topic="Why 'Rev H makes it worse' on real tremor: the heavier pen, not the delay (study E)",
        citation="This study's simulation and calculation (realtrack/delay.py) on study R's tuning split",
        year="2026", doi_or_url="results/realtrack/realtrack.json (delay)", source_type="derived calculation", evidence_class="numerical simulation",
        access_level="full text", task_or_setup="Ordinary 12 g pen vs Rev J (83.5 g) with the nose held vs Rev J + Rev H tracker; horizon sweep -3 ... +10 ms; the command path's lag",
        participants_or_bench="Simulated (tuning writers, real tremor)", comparator="Ordinary pen",
        key_quantitative_findings=(f"Tip tremor of the nose-held Rev J vs the ordinary pen: severe {_f((dc.get('severe') or {}).get('held'), 3)}, "
                                   f"mild {_f((dc.get('mild') or {}).get('held'), 3)}; with the Rev H tracker: severe {_f((dc.get('severe') or {}).get('revh'), 3)}; "
                                   f"command path lag {_f(((dl.get('servo_lag') or {}).get('rows') or [{}])[3].get('delay_ms'), 2)} ms at 6 Hz; IMU-to-tip chain {_f((dl.get('budget') or {}).get('imu_to_tip_ms'), 2)} ms"),
        units_and_conditions="amplitude ratios; ms", locator="fig_delay.png", limitations="HW1's hand-grip model (HAP-26 values); simulated pen masses",
        relevance_to_design="Nose-pen mass and the tracker's own authority set the baseline, not only latency",
        transferability="medium", transferability_reason="Mechanical model, literature hand impedance", design_implication="Report every tracker against the nose-held pen as well as the ordinary pen",
        retrieved=DATE, search_query="n/a (derived)", stream="ACT", lead_verification=""))
    mc = out.get("chosen_mcu") or {}
    R.append(dict(
        id="ACT-144", topic="MCU cost of the chosen causal tracker per 1 kHz step (study E, CALC)",
        citation="This study's calculation (realtrack/mcu.py) with fusion/budget.py's cycle model",
        year="2026", doi_or_url="results/realtrack/realtrack.json (mcu)", source_type="derived calculation", evidence_class="analytical calculation",
        access_level="full text", task_or_setup="Operation counts of the chosen estimator and its authority; Cortex-M33 at 128 MHz (nRF54L15 / nRF5340 application core)",
        participants_or_bench="n/a", comparator="The AKF of DEC-025, G4, the TCN",
        key_quantitative_findings=f"{mc.get('summary', 'n/a')}", units_and_conditions="MAC and cycles per 1 ms; bytes",
        locator="docs/real_tracker.md MCU section", limitations="Cycle model is an ASSUMPTION (2 cycles per float MAC); to be profiled",
        relevance_to_design="Fits the pen's MCU next to the servo", transferability="high", transferability_reason="Operation counts",
        design_implication="Profile with DWT CYCCNT on the board (firmware O2)", retrieved=DATE, search_query="n/a (derived)", stream="ACT", lead_verification=""))
    ln = out.get("learned") or {}
    R.append(dict(
        id="EML-102", topic="Learned tremor estimators trained on real inputs vs ai2's TCN trained on synthetic writers (study E)",
        citation="This study's simulation (realtrack/learned.py, netmodel.py): TCN (about 17 k parameters) and a linear FIR trained on real tuning writers and patients, cross-fitted by writer and patient",
        year="2026", doi_or_url="results/realtrack/realtrack.json (learned)", source_type="derived calculation", evidence_class="numerical simulation",
        access_level="full text", task_or_setup="Same tuning cases, DeltaPen-class page sensor, surrogate of the HW1 command path",
        participants_or_bench="Simulated (5 tuning writers; tuning patients)", comparator="ai2's TCN; the listening AKF",
        key_quantitative_findings=f"{ln.get('summary', 'n/a')}", units_and_conditions="amplitude ratios; um RMS",
        locator="docs/real_tracker.md learned section", limitations="5 tuning writers and 20 tuning patients; simulation targets",
        relevance_to_design="Whether training on real data removes the TCN's domain shift", transferability="low",
        transferability_reason="Composed inputs; no patient's own writing", design_implication="Collect EXP-R01 recordings before any learned estimator drives the nose",
        retrieved=DATE, search_query="n/a (derived)", stream="EML", lead_verification=""))
    return R


def write(path: Path, out: Dict) -> None:
    R = rows(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in R:
            w.writerow({h: r.get(h, "") for h in HEADER})
