"""Evidence rows proposed by study N (results/nibopt/evidence_rows.csv): docs/evidence.csv's 23 columns, CRLF line
endings, ids AMF-260 onward (checked unused on 2026-09-30).  Only sources opened in this study; read on 2026-09-30."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator",
          "limitations", "relevance_to_design", "transferability", "transferability_reason", "design_implication",
          "retrieved", "search_query", "stream", "lead_verification"]

ROWS: List[Dict[str, str]] = [
    {"id": "AMF-260", "topic": "Rolling bearings: the contact stress behind the basic static load rating (ISO 76 basis)",
     "citation": "MinebeaMitsumi. Engineering information: Load rating and rating life (miniature and small ball bearings).",
     "year": "2026", "doi_or_url": "https://product.minebeamitsumi.com/en/technology/bearing/ballbearings_cat-3_004-06.html",
     "source_type": "manufacturer web page", "evidence_class": "manufacturer statement", "access_level": "full text (web page)",
     "task_or_setup": "Definition of the basic static radial load rating for ball bearings", "participants_or_bench": "not applicable",
     "comparator": "-",
     "key_quantitative_findings": "Basic static load rating = the static load at which the calculated contact stress at the centre "
                                  "of the most heavily loaded ball-track contact is 4,200 MPa; the total permanent deformation "
                                  "is then about 0.0001 of the ball diameter",
     "units_and_conditions": "MPa; hardened bearing steel races and balls", "locator": "basic static load rating paragraph",
     "limitations": "A rating convention for conforming grooves in bearing steel, not a fatigue limit; a sphere on a flat 440C race "
                    "with Si3N4 balls is outside its scope",
     "relevance_to_design": "Sets the Hertz allowable of study N's ball thrust guide (with AMF-261's static safety factors)",
     "transferability": "medium", "transferability_reason": "Same contact physics; different race geometry and steel",
     "design_implication": "Allowable peak Hertz pressure 4.2 GPa / s0^(1/3): 3.33 GPa sustained (s0 2), 3.67 GPa drop (s0 1.5)",
     "retrieved": "2026-09-30", "search_query": "\"4 200 MPa\" basic static load rating ball bearings contact stress permanent "
                                               "deformation 0.0001 rolling element diameter", "stream": "AMF",
     "lead_verification": ""},
    {"id": "AMF-261", "topic": "Rolling bearings: minimum static safety factor by type of operation (after ISO 76)",
     "citation": "NES Bearing Company (A. Hvizdzak, T. Asquith). Calculating Static Safety Factor - ISO 76. Technical note (PDF).",
     "year": "2024", "doi_or_url": "https://nesbearings.com/wp-content/uploads/2024/04/Static-Safety-Factor-002.pdf",
     "source_type": "manufacturer", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Bearing selection note: s0 = C0 / P0", "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "Ball bearings, s0 minimum: 2 for quiet-running (smooth, vibration-free, high rotational "
                                  "accuracy), 1 for normal running, 1.5 for pronounced shock loads; roller bearings 3 / 1.5 / 3; "
                                  "at C0 the permanent deformation is about 0.0001 of the rolling element diameter",
     "units_and_conditions": "dimensionless load ratio; assumes proper mounting, conventional loading and hardened bearing steel",
     "locator": "p. 1, tables 'Type of Operation for Ball Bearings' and '... Roller Bearings'",
     "limitations": "Selection guidance for rotating bearings; the s0 values are load ratios (the contact stress scales with the "
                    "cube root of the load for a ball)",
     "relevance_to_design": "Converts the 4,200 MPa rating stress (AMF-260) into study N's sustained (s0 2) and drop (s0 1.5) "
                            "Hertz allowables for the nib's ball guide",
     "transferability": "medium", "transferability_reason": "Oscillating sphere-on-flat contact in 440C, not a rotating bearing",
     "design_implication": "Hertz <= 3.33 GPa under the writing load and <= 3.67 GPa at the race springs' release load; EXP-NB05 "
                           "checks the races after the duty and the drops",
     "retrieved": "2026-09-30", "search_query": "ISO 76 static load rating contact stress 4200 MPa ball bearings 4600 MPa "
                                               "self-aligning", "stream": "AMF", "lead_verification": ""},
    {"id": "AMF-262", "topic": "Rolling friction coefficients of rolling-element linear guides (ball slides, cross-roller guides)",
     "citation": "THK Co., Ltd. General Catalog, Selection Criteria: Friction Coefficient (page B0-15 / 515-1E), Table 4 and Fig. 7.",
     "year": "2026", "doi_or_url": "https://tech.thk.com/es/products/pdf/en_b00_015.pdf", "source_type": "datasheet",
     "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Frictional resistance of each type of LM system under normal conditions", "participants_or_bench": "not applicable",
     "comparator": "sliding guides (1/20-1/40 of them)",
     "key_quantitative_findings": "Friction coefficient: linear ball slide LS 0.0006-0.0012; LM stroke 0.0006-0.0012; cross-roller "
                                  "guide / table VR, VRU, VRT 0.001-0.0025; LM Guide 0.002-0.003 (SRG, SRN 0.001-0.002); linear "
                                  "bushing 0.001-0.003; Fig. 7: the coefficient rises steeply as the applied load falls below "
                                  "about 2 % of the dynamic rating (seal and lubricant resistance)",
     "units_and_conditions": "dimensionless, normal conditions, with the catalogue's seals and lubrication", "locator": "Table 4, Fig. 7",
     "limitations": "Commercial guides with recirculation, seals and grease; the nib's guide is an unsealed planar race pair "
                    "with 0.8-1.5 mm balls, far below the catalogue's loads",
     "relevance_to_design": "Bounds the rolling resistance 0.001 that study K and the pass assumed for the nib's ball thrust guide; "
                            "warns that light preload may not reduce the drag in proportion",
     "transferability": "low", "transferability_reason": "Different scale, no recirculation, no seals; the light-load rise may dominate",
     "design_implication": "Keep mu_roll 0.001 with a x2 sensitivity; measure drag against preload on the coupon (EXP-NB05)",
     "retrieved": "2026-09-30", "search_query": "crossed roller guide coefficient of friction 0.001 THK linear motion rolling "
                                               "friction coefficient catalog", "stream": "AMF", "lead_verification": ""},
]


def write(path: Path) -> Path:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADER, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in ROWS:
        w.writerow({k: r.get(k, "") for k in HEADER})
    path.write_bytes(buf.getvalue().encode("utf-8"))
    return path


def check(path: Path) -> Dict:
    raw = path.read_bytes()
    txt = raw.decode("utf-8")
    rows = list(csv.reader(io.StringIO(txt, newline="")))
    ids = [r[0] for r in rows[1:]]
    return {"header_ok": rows[0] == HEADER, "n_columns": [len(r) for r in rows], "crlf": b"\r\n" in raw and b"\n" not in
            raw.replace(b"\r\n", b""), "ids": ids,
            "ids_in_range": all(i.startswith("AMF-2") and 260 <= int(i.split("-")[1]) <= 279 for i in ids)}
