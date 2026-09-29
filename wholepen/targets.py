r"""Task 1: tremor at the pen tip for mild, moderate and severe essential tremor (ET) and Parkinson's disease (PD) while
writing and drawing (LIT with ledger ids, REAL DATA from realdata.py, CALC; the class values are ASSUMPTION built on
them and stay hypotheses until EXP-W10 measures them).

Amplitude convention used everywhere in this study: 'peak' = half the peak-to-peak excursion of a sine of the same
power along the tremor's major axis (sqrt(2) x rms), in the page plane at the ink.  Rating-scale anchors are quoted
in their own convention (TETRAS limb items: cm; MDS-UPDRS: 'maximal amplitude'; tablet studies: peak-to-peak).
"""
from __future__ import annotations

import math
from typing import Dict

from . import ROOT  # noqa: F401


def ftm_spiral_to_mm(ftm: float) -> Dict[str, float]:
    """LIT PDT-12 (Elble & Ellenbogen 2017, 18 ET patients, tablet spirals): log10 T = 0.6 FTM - 1.27, T peak-to-peak
    in cm (r = 0.94).  Returns peak-to-peak and peak in mm (CALC)."""
    T_cm = 10 ** (0.6 * ftm - 1.27)
    return {"ftm": ftm, "pp_mm": T_cm * 10.0, "peak_mm": T_cm * 5.0}


def rating_ratio(alpha: float) -> float:
    """LIT PDT-11 (Elble 2006, 928 patients, 5 labs): T2/T1 = 10^(alpha (TRS2 - TRS1)); writing alpha 0.414-0.441."""
    return 10 ** alpha


# prevalence of tremor in PD, and in writing (LIT; ids from results/wholepen/evidence_rows.csv)
PD_PREVALENCE = [
    {"what": "rest tremor / action tremor at baseline, 3 cohorts (PPMI 423, BioFIND 118, PDBP 873)", "value": "58.2 % / 39.0 %",
     "src": "PDT-64"},
    {"what": "any tremor at least once over 7 years (PPMI, de novo, 397)", "value": "96.2 %; rest tremor 87.2 %",
     "src": "PDT-66"},
    {"what": "writing tremor in 100 consecutive PD patients (on medication)", "value": "10 % (26 % of those with postural/kinetic tremor); task-specific in 4 of 10",
     "src": "PDT-63"},
    {"what": "tremor types in 315 PD patients with tremor", "value": "pure rest 30 %; mixed rest + action at the same frequency 50 % (with a lag, i.e. re-emergent, 25 %); pure action 19 %; different frequencies 1 %",
     "src": "PDT-65"},
    {"what": "re-emergent tremor", "value": "12 of 18 PD with rest tremor; latency 9.4 +- 10.7 s; about 5.5 Hz",
     "src": "PDT-09"},
    {"what": "action tremor 'in nearly half' of PD patients when drawing (clinical review)", "value": "about half",
     "src": "PDT-36"},
]

# rating-scale anchors (LIT)
ANCHORS = [
    {"scale": "TETRAS upper-limb items (postural/kinetic)", "anchors": "1 barely visible; 1.5 < 1 cm; 2 1-3 cm; 2.5 3-5 cm; 3 5-10 cm; 3.5 10-20 cm; 4 > 20 cm", "src": "PDT-14"},
    {"scale": "TETRAS spiral / handwriting items", "anchors": "spiral: 1 barely visible, 2 obvious, 3 portions not recognisable, 4 not recognisable; handwriting: 1 untidy, 2 legible but considerable tremor, 3 parts illegible, 4 completely illegible", "src": "PDT-14"},
    {"scale": "MDS-UPDRS 3.15-3.17 (postural, kinetic, rest)", "anchors": "1 <= 1 cm; 2 > 1 but < 3 cm; 3 3-10 cm; 4 > 10 cm 'maximal amplitude'", "src": "PDT-68"},
    {"scale": "FTM spiral on a tablet (ET)", "anchors": "log10 T(cm, p-p) = 0.6 FTM - 1.27; FTM 1: 2.1 mm, 2: 8.5 mm, 3: 34 mm peak-to-peak", "src": "PDT-12"},
]


def classes(realdata: Dict = None) -> Dict:
    """The study's tremor classes at the pen tip (ASSUMPTION built on the LIT and REAL DATA above)."""
    f = ftm_spiral_to_mm
    et = {
        "mild": {"peak_mm": (0.5, 1.5), "sim_mm": 1.0, "basis": f"FTM spiral about 1: {f(1)['peak_mm']:.1f} mm peak (PDT-12); cohort median 1 mm peak (PDT-12)"},
        "moderate": {"peak_mm": (2.0, 4.5), "sim_mm": 3.0, "basis": f"FTM about 2: {f(2)['peak_mm']:.1f} mm peak (PDT-12); about a third of the ET cohort above 2 mm peak (PDT-12 lognormal)"},
        "severe": {"peak_mm": (5.0, 17.0), "sim_mm": 8.0, "basis": f"FTM 2.5-3: {f(2.5)['peak_mm']:.0f}-{f(3)['peak_mm']:.0f} mm peak (PDT-12); tablets lose very severe tremor (PDT-13)"},
        "f_Hz": {"range": (4.0, 12.0), "typical": (5.0, 8.0), "sim": (6.0, 9.0), "basis": "PDT-56 (4-12 Hz, typically 4-8, falling with age); PDT-36 (8-12 Hz in spirals, often unidirectional)"},
        "while_writing": "kinetic tremor: present while writing, often larger than postural (PDT-56); mostly one axis (PDT-36)",
    }
    pd = {
        "mild": {"peak_mm": (0.2, 1.0), "sim_mm": 1.0, "basis": "the typical PD writer with tremor: recorded drawing tremor 0.3-1.4 mm at the pen's sensor in 4 of 26 NewHandPD patients; UCI spirals <= 0.45 mm (REAL DATA, realdata.py)"},
        "moderate": {"peak_mm": (2.0, 4.0), "sim_mm": 3.0, "basis": "action or re-emergent tremor while writing in tremor-dominant PD (MDS-UPDRS 2: 1-3 cm maximal amplitude at the limb, PDT-68); ASSUMPTION at the pen"},
        "severe": {"peak_mm": (5.0, 10.0), "sim_mm": 8.0, "basis": "re-emergent tremor at rest-tremor amplitudes in pauses and slow strokes, off medication (PDT-09, PDT-65); ASSUMPTION at the pen"},
        "f_Hz": {"action": (5.0, 8.0), "rest_reemergent": (4.0, 6.0), "sim": (5.0,), "basis": "PDT-56; PDT-09 (re-emergent about 5.5 Hz); recorded lines 4.4-5.9 Hz (REAL DATA)"},
        "while_writing": "rest tremor is suppressed by movement and re-emerges after a latency (PDT-09, PDT-56); action tremor persists; writing tremor proper in 10 % of PD (PDT-63)",
    }
    out = {"convention": __doc__.split("Amplitude convention")[1].split("\n\n")[0].strip(),
           "ET": et, "PD": pd, "prevalence": PD_PREVALENCE, "anchors": ANCHORS,
           "ftm_table": [f(x) for x in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)],
           "writing_alpha": {"alpha": (0.414, 0.441), "ratio_per_point": (rating_ratio(0.414), rating_ratio(0.441)), "src": "PDT-11"},
           "plan_classes_mm": {"mild": (0.3, 1.0), "moderate": (2.0, 4.0), "severe": (5.0, 10.0), "src": "docs/round4_plan.md section 6 (ASSUMPTION)"},
           "label": "LIT (ledger ids) + REAL DATA (realdata.py) + CALC; the class values are ASSUMPTION to be measured (EXP-W10)"}
    if realdata:
        out["realdata_summary"] = realdata
    return out
