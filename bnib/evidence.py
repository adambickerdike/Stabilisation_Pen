"""Evidence rows this study proposes for docs/evidence.csv (results/bnib/evidence_rows.csv, the ledger's exact 23-column
header).  Only sources opened in this study; ids from the ranges given to study B (ACT-140..154, AMF-200..219,
OPT-75..84, CON-95..99, HAP-135..139, PAT-55..59).  Sources re-opened that already have a ledger row (OPT-01/02 DeltaPen
text, CON-21 ISO 12757-1, CON-23 Pentel, AMF-60 ISO 27668-1, CON-13 Hase) are cited by their existing ids, not
duplicated.  The lead verifies and merges; 'lead_verification' is left empty.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List

from . import REPO_ROOT, RESULTS

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
          "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
          "stream", "lead_verification"]

RETRIEVED = "2026-09-29"

ROWS: List[Dict] = [
    {"id": "OPT-75", "topic": "Pen-tip optical flow: DeltaPen translation error vs speed (scale error while writing)",
     "citation": "Lüthi G., Fender A.R., Holz C. (2022). DeltaPen: A Device with Integrated High-Precision Translation and "
                 "Rotation Sensing on Passive Surfaces. UIST '22, ACM. Figure 7.",
     "year": "2022", "doi_or_url": "https://doi.org/10.1145/3526113.3545655", "source_type": "conference",
     "evidence_class": "physical human study", "access_level": "full text",
     "task_or_setup": "As OPT-02 (DeltaPen coupled tip-to-tip to a Wacom pen on a Wacom Intuos 4; shapes, sentences, free "
                      "sketching); median absolute percentage error of the translation per speed bin",
     "participants_or_bench": "10 participants (as OPT-02)", "comparator": "Wacom Intuos 4 positions",
     "key_quantitative_findings": "MdAPE (read from the bar chart, X / Y): 0.625 cm/s about 2.3 % / 5.1 %; 1.25 cm/s 1.7 % / "
                                  "3.3 %; 2.5 cm/s 1.1 % / 1.7 %; 3.1-5 cm/s 0.8-1.1 % / 1.2-1.4 %; 5.6-11.9 cm/s 0.4-0.9 % / "
                                  "0.7-1.3 %. Error falls with speed; Y is worse than X.",
     "units_and_conditions": "percent of the true translation per window; speed bins 0.625-11.875 cm/s; tablet surface, not paper",
     "locator": "Fig. 7 (p. 8)",
     "limitations": "Values read from a bar chart (about +-0.1 %); tablet surface; developers' own evaluation; per-window "
                    "percentages, not stroke-level position error",
     "relevance_to_design": "Sets the scale-error part of the page-sensor model the balanced-nib simulations use (median "
                            "about 1.2 % at writing speeds; larger at the slow speeds of small tremor)",
     "transferability": "medium",
     "transferability_reason": "Measured on a tablet with a coupled stylus; paper and ink change the flow image",
     "design_implication": "Model the page sensor with a per-run scale error of median 1.2 % plus the 10 ms window error "
                           "(OPT-02); re-measure on paper with a tilt sweep (EXP-T04)",
     "search_query": "https://static.siplab.org/papers/uist2022-deltapen.pdf (re-opened; Fig. 7 rendered and read)",
     "stream": "B"},
    {"id": "CON-95", "topic": "Rollerball pens: ISO tip classes and refill types (no writing load in the preview)",
     "citation": "ISO 14145-1:2017 Roller ball pens and refills - Part 1: General use (iTeh preview); ISO 14145-2:1998 "
                 "Part 2: Documentary use (iTeh preview)",
     "year": "2017", "doi_or_url": "https://standards.iteh.ai/catalog/standards/sist/b53988d7-bfbf-481a-a97d-ec191f16974f/iso-14145-1-2017",
     "source_type": "standard", "evidence_class": "manufacturer statement", "access_level": "abstract only",
     "task_or_setup": "Preview pages: scope, normative references, tip classification, refill types",
     "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "Tip classes by ball diameter: EF < 0.55 mm, F 0.55-<0.75, M 0.75-<1.00, B >= 1.00 mm. "
                                  "Refill types A (111 +- 2 mm), B (87 +- 2 mm), C (110 +- 1 mm, 2.5 mm tip holder); others "
                                  "type D. Part 2 refers the writing angle and pitch to 5.1 of ISO 14145-1:1998. No writing "
                                  "load appears in the preview pages.",
     "units_and_conditions": "mm", "locator": "Clause 4.1 Table 1; clause 4.2 Table 2; ISO 14145-2 clause list",
     "limitations": "Preview only: the write-test clause and its load are not visible",
     "relevance_to_design": "Rollerball refills are longer (87-111 mm) than the D1 refill the nib is designed around; no "
                            "load threshold available",
     "transferability": "low", "transferability_reason": "Definitions only; no force data",
     "design_implication": "A rollerball variant needs its own refill holder length; its minimum force must be measured "
                           "(EXP-T02 / EXP-B20)",
     "search_query": "iTeh standards preview ISO 14145-1:2017 and ISO 14145-2:1998 (curl)", "stream": "B"},
    {"id": "CON-96", "topic": "Manufacturer writing-test load for a gel/water-based ink pen (spiral machine test)",
     "citation": "Onuki S, Yasuike K, Takai H, Saitou H (Pentel Co Ltd). Ink composition, writing instrument and method for "
                 "producing ink composition. US Patent 11,697,743 B2",
     "year": "2023", "doi_or_url": "https://patents.google.com/patent/US11697743B2/en", "source_type": "patent",
     "evidence_class": "patent disclosure", "access_level": "full text",
     "task_or_setup": "Ink compositions tested in ballpoint tips; spiral machine writing test; drying, bleeding and "
                      "bleed-through tests",
     "participants_or_bench": "Bench (application filed 2017-06-14; granted 2023-07-11)", "comparator": "Tip geometries, inks",
     "key_quantitative_findings": "Verbatim: 'a spiral machine written test (writing speed: 7 cm/sec, writing angle: 70 deg, "
                                  "writing load: 100 gf)' - poor ink discharge makes it 'impossible to finish writing "
                                  "completely' when the ball displacement is too small. Eraser test load 500 gf.",
     "units_and_conditions": "100 gf = 0.98 N; 70 deg; 70 mm/s", "locator": "Description (tip dimensions; spiral test)",
     "limitations": "A test load chosen for the test, not a minimum; no force sweep",
     "relevance_to_design": "Manufacturers qualify such tips near 1 N, six times the nib's 0.15 N design spring",
     "transferability": "medium", "transferability_reason": "Industrial test practice, not a threshold",
     "design_implication": "Treat 0.15 N as unverified; measure the minimum in G1 (EXP-T02 / EXP-B20)",
     "search_query": "Google Patents full text (curl)", "stream": "B"},
    {"id": "CON-97", "topic": "Lowest manufacturer writing-test load found: 70 gf start-of-writing test (oil ballpoint, 0.5 mm ball)",
     "citation": "Sanada Y, Kudou H, Fujii T (Pilot Corp). Ballpoint pen. US Patent 11,993,099 B2",
     "year": "2024", "doi_or_url": "https://patents.google.com/patent/US11993099B2/en", "source_type": "patent",
     "evidence_class": "patent disclosure", "access_level": "full text",
     "task_or_setup": "Oil-based ballpoint (ball <= 0.5 mm, 500-15000 mPa s ink); running-tester and hand writing tests",
     "participants_or_bench": "Bench (filed 2021-08-27; granted 2024-05-28)", "comparator": "Inks and tip geometries",
     "key_quantitative_findings": "Start-of-writing test: 'a writing load of 70 gf, a writing angle of 70 deg, and a writing "
                                  "speed of 4 m/min'; ink-flow stability and wear tests at 100 gf, 70 deg, 4 m/min; ink "
                                  "consumption at 200 g; hand test at 100 gf. The ball's own spring presses 5-10 gf (a seal).",
     "units_and_conditions": "70 gf = 0.69 N; 70 deg; 67 mm/s", "locator": "Examples: test methods",
     "limitations": "Test loads, not minima; no force sweep; 0.5 mm ball",
     "relevance_to_design": "The lowest writing load found in any source opened: 4.6 x the nib's 0.15 N design spring",
     "transferability": "medium", "transferability_reason": "Industrial test practice",
     "design_implication": "The nib must not depend on 0.15 N: the counter-face balance scales with the actual force; G1 "
                           "measures the minimum",
     "search_query": "Google Patents full text (curl)", "stream": "B"},
    {"id": "CON-98", "topic": "Pen plotters drive pens at set force levels (roller-ball highest)",
     "citation": "Hewlett-Packard. HP 7550A/7550B Graphics Plotter: specifications and control panel (4-page sheet, as "
                 "distributed by a test-equipment reseller)",
     "year": "n.d.", "doi_or_url": "https://testequipment.center/Product_Documents/Agilent-7550B-Specifications-3E985.pdf",
     "source_type": "manufacturer", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Plotter specification; carousel speed and force defaults per pen type",
     "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "Carousel defaults (speed cm/s, force level): transparency 10 / 2; refillable drafting 15 / "
                                  "1; disposable drafting 20 / 1; paper (fibre-tip) 50 / 2; roller-ball 60 / 6. Plotting "
                                  "speed up to 80 (7550A) / 120 cm/s (7550B).",
     "units_and_conditions": "force as a level; the level-to-gram table was not in the opened documents",
     "locator": "Control panel section, 'Carousel Speed and Force Defaults'",
     "limitations": "Relative levels only; an unverified secondary figure in grams was NOT used",
     "relevance_to_design": "Machine writing with roller-ball pens used the highest force level: tip type changes the force "
                            "needed", "transferability": "low", "transferability_reason": "Relative levels, old hardware",
     "design_implication": "Measure the minimum force per tip type (EXP-T02 / EXP-B20) rather than assume one value",
     "search_query": "curl of the reseller PDF (support.hp.com bpp01673 failed: HTTP/2 error); Internet Archive search for "
                     "HP plotter manuals (HP 7475A operation manual opened: no force table)", "stream": "B"},
    {"id": "CON-99", "topic": "Ballpoint and rollerball writing mechanism (ink film, ball rotation, wetting)",
     "citation": "Lee J, Murad S, Nikolov A. Ballpoint/Rollerball Pens: Writing Performance and Evaluation. Colloids and "
                 "Interfaces 7(2):29",
     "year": "2023", "doi_or_url": "https://doi.org/10.3390/colloids7020029", "source_type": "journal",
     "evidence_class": "physical bench experiment", "access_level": "full text",
     "task_or_setup": "Video of the ball writing (fibre-optic lens); ball rotation per unit length by a piezoelectric disk; "
                      "wetting and force-balance model of the ink film",
     "participants_or_bench": "Bench", "comparator": "Fountain pen principle",
     "key_quantitative_findings": "Qualitative: writing is 'a random rolling process comprising a normal ball-paper pressure "
                                  "stress, ball transition, ball rotation, ball-ink-paper adhesion, and ball friction'; the "
                                  "ball's downward pressure is named as a factor of line quality (white stain domains). No "
                                  "force threshold is given.",
     "units_and_conditions": "-", "locator": "Sections 2-3; Figure 4",
     "limitations": "No force measurement or minimum; review-style article",
     "relevance_to_design": "Supports treating line continuity at low force as an empirical question",
     "transferability": "low", "transferability_reason": "Mechanism description only",
     "design_implication": "G1 records gap fraction and ink density against force, angle, speed and paper (EXP-T02 / EXP-B20)",
     "search_query": "mdpi-res.com PDF (curl; the MDPI page returned 403)", "stream": "B"},
]


def rows() -> List[Dict]:
    out = []
    for r in ROWS:
        row = {k: "" for k in HEADER}
        row.update(r)
        row["retrieved"] = row.get("retrieved") or RETRIEVED
        row["lead_verification"] = ""
        out.append(row)
    return out


def check_header() -> bool:
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        head = next(csv.reader(f))
    return head == HEADER


def write(path=None) -> str:
    path = path or str(RESULTS / "evidence_rows.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows():
            w.writerow(r)
    return path
