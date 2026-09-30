"""Proposed ledger rows for the sources opened in study K (results/revK/evidence_rows.csv: docs/evidence.csv's 23-column
header, CRLF line ends).  Ids AMF-250..254: the ledger's largest AMF id was AMF-238 on 2026-09-30 and no study's
results/*/evidence_rows.csv used AMF-239..254 (checked).  The lead merges them; this package never writes docs/.

A re-read of an existing row is proposed in docs/revK_design.md, not here: AMF-21 (AZoM Ti-6Al-4V) prints the volume
electrical resistivity as '170 (67)' in a column headed ohm.cm, which can only be micro-ohm cm (1.70e-6 ohm m).
"""
from __future__ import annotations

import csv
from pathlib import Path

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
          "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
          "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved",
          "search_query", "stream", "lead_verification"]

ROWS = [
    {"id": "AMF-250", "topic": "Price of the nib Hall sensor: TI TMAG5170A1QDGKR (distributor page)",
     "citation": "DigiKey product page TMAG5170A1QDGKR (Texas Instruments), price breaks, cut tape.", "year": "2026",
     "doi_or_url": "https://www.digikey.com/en/products/detail/texas-instruments/TMAG5170A1QDGKR/15284508",
     "source_type": "distributor page", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Catalogue price", "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "USD 2.67 (1), 1.97 (100), 1.80 (500), 1.74 (1,000); 3-axis Hall, +-25/50/100 mT, SPI, "
                                  "2.3-5.5 V, 8-VSSOP; 2,228 in stock",
     "units_and_conditions": "USD per unit, cut tape, 2026-09-30", "locator": "price table",
     "limitations": "One distributor on one day; prices move", "relevance_to_design": "Rev K bill of materials (nib Hall)",
     "transferability": "high", "transferability_reason": "Catalogue part",
     "design_implication": "1.74-1.97 USD per pen at 1,000 / 100", "retrieved": "2026-09-30",
     "search_query": "TMAG5170A1EQDGKR price 1ku USD", "stream": "AMF", "lead_verification": ""},
    {"id": "AMF-251", "topic": "C17200 beryllium copper: electrical conductivity (coil leads through the suspension wires)",
     "citation": "IBC Advanced Alloys. Product Data Sheet - C17200 (metric), physical and typical mechanical properties.",
     "year": "2019",
     "doi_or_url": "https://ibcadvancedalloys.com/wp-content/uploads/2019/06/C17200_Copper_Alloy_Product_Data_Sheet_METRIC.pdf",
     "source_type": "datasheet", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Material data sheet", "participants_or_bench": "not applicable", "comparator": "A(TB00) vs AT(TF00)",
     "key_quantitative_findings": "Electrical conductivity 17 % IACS min in A(TB00), 22 % IACS min in AT(TF00) (plate and "
                                  "rounds); density 8.36 g/cm3; elastic modulus 131 GPa; thermal conductivity 130 W/mK",
     "units_and_conditions": "% IACS (100 % = 1.7241 micro-ohm cm), room temperature", "locator": "p. 1 tables",
     "limitations": "Plate and rounds, not fine wire; the TH04 wire temper is not listed (Materion's strip sheet, AMF-18, "
                    "gives 22-28 % IACS for the hardened tempers)",
     "relevance_to_design": "Rev K's suspension wires carry the coil currents: 0.10 mm C17200 gives 0.27 ohm per wire",
     "transferability": "medium", "transferability_reason": "Same alloy and age-hardened state; wire form not tested",
     "design_implication": "Use C17200 (or a higher-conductivity Cu alloy) for the wires; Ti-6Al-4V (AMF-21, 170 micro-ohm "
                           "cm) cannot carry the coil current", "retrieved": "2026-09-30",
     "search_query": "C17200 beryllium copper electrical conductivity % IACS TH04 age hardened resistivity datasheet",
     "stream": "AMF", "lead_verification": ""},
    {"id": "AMF-252", "topic": "Price of the SoC: Nordic nRF54L15-QFAA-R (distributor page)",
     "citation": "DigiKey product page NRF54L15-QFAA-R (Nordic Semiconductor ASA), price breaks.", "year": "2026",
     "doi_or_url": "https://www.digikey.com/en/products/detail/nordic-semiconductor-asa/NRF54L15-QFAA-R/24773448",
     "source_type": "distributor page", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Catalogue price", "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "USD 4.64 (1), 3.49 (100), 3.18 (500), 3.06 (1,000); 2.40 per unit on a 3,000 reel; "
                                  "1,043 in stock", "units_and_conditions": "USD per unit, 2026-09-30", "locator": "price table",
     "limitations": "One distributor on one day", "relevance_to_design": "Rev K bill of materials (SoC)",
     "transferability": "high", "transferability_reason": "Catalogue part", "design_implication": "3.06-3.49 USD per pen",
     "retrieved": "2026-09-30", "search_query": "digikey NRF54L15-QFAA-R price nordic", "stream": "AMF",
     "lead_verification": ""},
    {"id": "AMF-253", "topic": "Price of the coil driver: TI DRV8214RTER (distributor page)",
     "citation": "DigiKey product page DRV8214RTER (Texas Instruments), price breaks.", "year": "2026",
     "doi_or_url": "https://www.digikey.com/en/products/detail/texas-instruments/DRV8214RTER/22077487",
     "source_type": "distributor page", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Catalogue price", "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "USD 4.13 (1), 2.59 (100), 2.46 (250), 2.45 (500); 2.24 per unit on a 3,000 reel; 11 V "
                                  "4 A H-bridge, I2C, 16-WQFN 3 x 3 mm", "units_and_conditions": "USD per unit, 2026-09-30",
     "locator": "price table", "limitations": "One distributor on one day",
     "relevance_to_design": "Rev K bill of materials (two coil drivers)", "transferability": "high",
     "transferability_reason": "Catalogue part", "design_implication": "2 x 2.24-2.59 USD per pen", "retrieved": "2026-09-30",
     "search_query": "digikey DRV8214RTER price", "stream": "AMF", "lead_verification": ""},
    {"id": "AMF-254", "topic": "Price of the IMU: ST LSM6DSV16XTR (distributor page)",
     "citation": "DigiKey product page LSM6DSV16XTR (STMicroelectronics), price breaks.", "year": "2026",
     "doi_or_url": "https://www.digikey.com/en/products/detail/stmicroelectronics/LSM6DSV16XTR/16841485",
     "source_type": "distributor page", "evidence_class": "manufacturer statement", "access_level": "full text",
     "task_or_setup": "Catalogue price", "participants_or_bench": "not applicable", "comparator": "-",
     "key_quantitative_findings": "USD 5.75 (1), 4.34 (100), 4.01 (500), 3.89 (1,000); 3.65 per unit on a 5,000 reel; "
                                  "14-VFLGA", "units_and_conditions": "USD per unit, 2026-09-30", "locator": "price table",
     "limitations": "One distributor on one day", "relevance_to_design": "Rev K bill of materials (IMU)",
     "transferability": "high", "transferability_reason": "Catalogue part", "design_implication": "3.89-4.34 USD per pen",
     "retrieved": "2026-09-30", "search_query": "digikey LSM6DSV16XTR price STMicroelectronics", "stream": "AMF",
     "lead_verification": ""},
]


def write(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(HEADER)
        for r in ROWS:
            w.writerow([r.get(k, "") for k in HEADER])
    return str(path)
