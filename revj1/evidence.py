"""Proposed ledger rows (the 23 columns of docs/evidence.csv) for the sources this study actually opened.

Only sources whose text was read here get a row.  Sources re-read that already have a ledger id are cited by that id
and not duplicated: ECMA-287 (AMF-35: Table 5.2 and B.5 re-read), TI DRV5055 (OPT-46: ICC re-read) and TI DRV8214
(AMF-37: active-mode current IVM 1.3 / 1.9 mA re-read, not in the ledger's findings column: proposed amendment).
Searches that found a source but could not open it (an IOVS 2006 abstract on head and book position, HTTP 403) give no row.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List

from . import REPO_ROOT

HEADER = None


def header() -> List[str]:
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def _r(**kw) -> Dict:
    base = {"year": "n.d.", "source_type": "datasheet", "evidence_class": "manufacturer statement", "access_level": "full text",
            "participants_or_bench": "not applicable (manufacturer data; test method not published)", "comparator": "",
            "transferability": "high", "retrieved": "2026-09-29", "stream": "", "lead_verification": ""}
    base.update(kw)
    return base


ROWS = [
    _r(id="OPT-60", topic="MCU and radio currents for the Rev J.1 electronics budget: Nordic nRF54L15",
       citation="Nordic Semiconductor. nRF54L15, nRF54L10, and nRF54L05 Wireless SoCs, Preliminary Datasheet v0.10 (4503_018).",
       year="2025", doi_or_url="https://www.farnell.com/datasheets/4557217.pdf",
       task_or_setup="Current consumption scenarios, VDD 3 V, DC/DC, 25 degC (s11.1)",
       comparator="Rev H base electronics ASSUMPTION 0.065 W for MCU and radio",
       key_quantitative_findings=("Power highlights at 3.0 V: BLE TX 1 Mbps 0 dBm 4.8 mA, +4 dBm 6.6 mA, +8 dBm 9.8 mA; RX 1 Mbps 3.4 mA "
                                  "(2 Mbps 3.6 mA); CPU CoreMark from RRAM with cache at 128 MHz 2.6 mA (from RAM 2.9 mA); System ON "
                                  "idle with GRTC, LFXO, 256 KB RAM 3.1 uA; System OFF 0.6 uA; SAADC 2 Msps 1.4 mA; TIMER00 at 128 MHz "
                                  "450 uA; TIMER10 at 32 MHz 240 uA; 500 CoreMark (3.90 CoreMark/MHz)"),
       units_and_conditions="mA or uA at VDD 3.0 V, typical, DC/DC regulator, 25 degC",
       locator="p. 1 (power highlights); s11.1.2 CURRENT electrical specification, pp. 860-861; s11.4 CPU performance, p. 862",
       limitations="Preliminary datasheet (distributor copy); typical values; application duty cycles are not the maker's",
       relevance_to_design="Replaces the 65 mW MCU-and-radio ASSUMPTION with a bottom-up estimate",
       transferability_reason="The part named for the Rev J board",
       design_implication=("SoC 8-14 mW from the cell at 50-80 % CPU and 3-10 % radio duty (CALC): the base electronics fall from "
                           "77 mW to 34-60 mW with the two DRV5055 and two DRV8214 counted from their datasheets"),
       search_query="WebSearch: nRF54L15 datasheet current consumption CPU running 128 MHz radio TX 0 dBm; curl of the Farnell copy",
       stream="OPT"),
    _r(id="OPT-61", topic="Low-power optical navigation sensor for the page sensor: PixArt PMW3610DM-SUDU",
       citation="PixArt Imaging Inc. PMW3610DM-SUDU Low Power Laser Mouse Sensor, product datasheet (distributor copy).",
       doi_or_url="https://www.epsglobal.com/Media-Library/EPSGlobal/Products/files/pixart/PMW3610DM-SUDU.pdf",
       task_or_setup="Recommended operating conditions and DC electrical characteristics (Tables 2 and 4)",
       comparator="PMW3360 (AMF-109, OPT-54): run current 16.3-21.6 mA",
       key_quantitative_findings=("IDD_RUN 0.60 mA typical at VDD 1.8 V (average, including the laser); Rest1 36 uA, Rest2 16 uA, Rest3 "
                                  "7 uA; shutdown 3 uA; VDD 1.7-2.1 V; lens reference plane to surface 2.2-2.6 mm (2.4 typ, +-0.2 mm "
                                  "DOF); speed 24 in/s typical, 30 in/s with certain surfaces; acceleration 10 g; resolution up to 3200 "
                                  "cpi in 200 cpi steps; operating temperature 0-40 degC; 16-pin molded DIP with VCSEL"),
       units_and_conditions="typical values at 25 degC, VDD 1.8 V",
       locator="p. 1 features; Table 2 (p. 6); Table 4 (p. 7)",
       limitations="Frame rate and paper tracking accuracy are not stated; mouse-surface product; the package does not fit the "
                   "pen (a chip-on-board die with folded optics is proposed, as for Rev J)",
       relevance_to_design="A page sensor 30x lower in power keeps DEC-042's tremor-line detector running in the steady modes",
       transferability="medium", transferability_reason="Current and optics are catalogue data; accuracy on paper is not",
       design_implication=("Use a PMW3610-class die, on in every mode (about 1.3 mW with its regulator, CALC); EXP-J10 must show "
                           "<= 10 um rms at 1 kHz on paper, or autowrite keeps a PMW3360-class die"),
       search_query="WebSearch: PixArt PMW3610 datasheet run current mA frame rate low power optical navigation sensor",
       stream="OPT"),
    _r(id="AMF-155", topic="Heel motor construction: Faulhaber 0620 B housing material (magnetic shielding)",
       citation="FAULHABER. Brushless DC-Servomotors, 2 Pole Technology, Series 0620 ... B, datasheet, edition 2026 Jul. 28.",
       year="2026", doi_or_url="https://www.faulhaber.com/fileadmin/Import/Media/EN_0620_B_FMM.pdf",
       task_or_setup="Catalogue data at 22 degC, nominal voltage", comparator="AMF-100 (eshop page, same motor)",
       key_quantitative_findings=("Housing material aluminium, black anodized; magnet NdFeB; 1 pole pair; 0620K006B: R 8.8 ohm, "
                                  "static friction torque 0.011 mNm, dynamic 1.02e-6 mNm/min-1, kM 1.09 mNm/A, rotor inertia 0.0095 "
                                  "gcm2, stall 0.732 mNm, rated 0.28 mNm, L 28 uH; Rth 13.2 / 84.3 K/W; mass 2.5 g; digital Hall "
                                  "sensors; motor -20 to +100 degC, winding 125 degC max; preloaded ball bearings"),
       units_and_conditions="22 degC, nominal voltage 6 V (006 B) / 12 V (012 B)", locator="p. 1, data table and notes",
       limitations="Whether the stator has an iron return ring is not stated", relevance_to_design=
       "The aluminium housing does not shield the rotor from the C1S cap's field (Rev J assumed a steel housing would help)",
       transferability_reason="The part used", design_implication=
       "Keep the motors away from the cap (moved 10 mm back in Rev J.1) or add a soft-iron cup; EXP-J02 measures the detent",
       search_query="WebSearch: Faulhaber 0620 B brushless DC motor datasheet housing material steel magnetic return",
       stream="AMF"),
    _r(id="AMF-156", topic="Longer 14 mm cell option: 14650 Li-ion (KeepPower ICR14650)",
       citation="KeepPower (Shenzhen Keeppower Technology). 14650 Li-ion battery ICR14650 3.7 V 1100 mAh, product page.",
       source_type="manufacturer", doi_or_url="https://www.keeppower.com.cn/products_detail.php?id=384",
       task_or_setup="Product specification", comparator="AMF-80 (EEMB LIR14500, 750 mAh)",
       key_quantitative_findings=("Nominal capacity 1130 mAh typical, 1100 mAh minimum; nominal 3.7 V; charge 4.200 +-0.05 V; cut-off 2.75 V; "
                                  "max continuous discharge 1900 mA; diameter 14.5 (-0.7) mm; height 65.3 (-0.6) mm; about 27 g; "
                                  "internal resistance <= 80 mOhm at 1 kHz; 300 cycles to 80 %; charge -20 to 45 degC, discharge -20 "
                                  "to 60 degC"),
       units_and_conditions="manufacturer statement", locator="Specification table on the product page",
       limitations="Product page (no full datasheet or test report); protected versions are longer",
       relevance_to_design="+47 % usable energy for +16.8 mm and +7 g against the LIR14500",
       transferability_reason="Catalogue cell of the same diameter class",
       design_implication="Fallback if the nose power is higher than modelled; with the end-cap the pen would exceed 175 mm",
       search_query="WebSearch: 14650 Li-ion cell datasheet 1100mAh 3.7V dimensions; WebFetch keeppower product page",
       stream="AMF"),
    _r(id="AMF-157", topic="Pouch-cell energy density reference: LP503562 1200 mAh",
       citation="Hunan Sounddon New Energy Co., Ltd. Specification of Li-polymer rechargeable battery, model 503562 1200mAh, "
                "Specification No. Q/WAPL503562-1011, Edition 1.0 (distributor copy).",
       doi_or_url="https://cdn-shop.adafruit.com/datasheets/503562+1200mah.pdf", task_or_setup="Cell specification",
       comparator="AMF-80 (LIR14500)",
       key_quantitative_findings=("Nominal capacity 1200 mAh at 0.2C, 25 degC; nominal voltage 3.75 V (average at 0.2C); cell dimension max "
                                  "5.0 x 35 x 62 mm (pack 5.2 x 35.5 x 62.5 mm with PCM); weight about 22 g; 1C discharge >= 54 min"),
       units_and_conditions="25 degC", locator="Sections 2.3 and 3 (pp. 2-3)",
       limitations="A flat 35 mm wide cell: used only for its energy density (about 415 Wh/L, CALC); no pouch of the pen's "
                   "D-shaped section is catalogued",
       relevance_to_design="Bounds what a custom D-shaped pouch above the motors could hold",
       transferability="medium", transferability_reason="Energy density transfers roughly; the shape does not",
       design_implication="A custom D-pouch could hold about 1.4 x the round cell's energy in the same length: a later option",
       search_query="WebSearch: EEMB lithium polymer battery LP503562 datasheet capacity dimensions weight",
       stream="AMF"),
    _r(id="AMF-158", topic="Heat spreader material: pyrolytic graphite sheet (Panasonic PGS)",
       citation="Panasonic Electronic Device Co., Ltd. PGS (Pyrolytic Graphite Sheet) Graphite Sheet, brochure (Digi-Key copy, 2005).",
       year="2005", source_type="manufacturer",
       doi_or_url="https://media.digikey.com/pdf/Other%20Related%20Documents/Panasonic%20Other%20Doc/PGS%20Graphite%20Sheet.pdf",
       task_or_setup="Characteristics table", comparator="aluminium and copper sheet",
       key_quantitative_findings=("Thickness 0.10 and 0.05 mm; density about 1 g/cm3; thermal conductivity a-b plane 600-800 W/(m K), "
                                  "c axis about 15 W/(m K); electrical conductivity 10000 S/cm; tensile strength 19.6 MPa"),
       units_and_conditions="manufacturer statement", locator="p. 1 characteristics table",
       limitations="2005 brochure; the PDF's text layer is partly unreadable (Japanese fonts); current grades list higher "
                   "conductivities (not read here); electrically conductive, needs insulation",
       relevance_to_design="A 0.1 mm sheet spreads the coil heat as well as Rev J's 0.5 mm aluminium at a tenth of the mass",
       transferability_reason="Material data", design_implication="Graphite spreader 0.1 x 30 mm in the shell wall, 0.21 g",
       search_query="WebSearch: Panasonic PGS pyrolytic graphite sheet datasheet thermal conductivity density thickness",
       stream="AMF"),
    _r(id="AMF-159", topic="Transparent window materials: polycarbonate against PMMA",
       citation="KunststoffWissen (kunststoff-profi.de). PC vs PMMA - Optical Plastic Comparison, web page updated 2026-05-13.",
       year="2026", source_type="website", evidence_class="review", access_level="secondary account",
       doi_or_url="https://kunststoff-profi.de/en/materials/pc-vs-pmma/", task_or_setup="Property comparison table",
       comparator="sapphire (AMF-160)",
       key_quantitative_findings=("Light transmission PC 88-90 %, PMMA 92 %; pencil hardness PC HB-2H (low), PMMA 2H-4H; Charpy notched "
                                  "impact PC 60-80 kJ/m2, PMMA 1.5-2.5 kJ/m2; UV: PC yellows without coating, PMMA excellent; density "
                                  "PC 1.20-1.22, PMMA 1.17-1.20 g/cm3; hard-coated PC keeps its impact strength with scratch "
                                  "resistance comparable to PMMA"),
       units_and_conditions="typical values, test standards not all stated", locator="Comparison table",
       limitations="Secondary web source; grade-level datasheets not read", relevance_to_design=
       "Chooses the clear sleeve section: hard-coated PC (tough) over PMMA (brittle in a drop)",
       transferability="medium", transferability_reason="Generic material classes",
       design_implication="Clear sleeve window in hard-coated PC; not on the ring, which rubs on paper",
       search_query="WebSearch: PMMA polycarbonate pencil hardness light transmission datasheet comparison", stream="AMF"),
    _r(id="AMF-160", topic="Scratch-proof transparent insert: single-crystal sapphire (Kyocera)",
       citation="Kyocera Corporation. Single Crystal Sapphire, product catalogue (PDF).", source_type="manufacturer",
       doi_or_url="https://global.kyocera.com/prdct/fc/product/pdf/s_c_sapphire.pdf",
       task_or_setup="Characteristics of Kyocera's single crystal sapphire", comparator="PC and PMMA (AMF-159)",
       key_quantitative_findings="Density 3.97e3 kg/m3; Vickers hardness 22.5 GPa (HV1, 9.807 N); flexural strength 690 MPa",
       units_and_conditions="room temperature", locator="p. 5, mechanical characteristics",
       limitations="Catalogue values; cost and machining of a small C-shaped insert not stated; text layer partly unreadable",
       relevance_to_design="The only transparent option that paper fillers would not scratch at the ring",
       transferability_reason="Material data",
       design_implication="A sapphire ring insert adds only about 3 points of visibility (CALC): not chosen", stream="AMF",
       search_query="direct URL: Kyocera single crystal sapphire catalogue"),
]


def write(path: str) -> str:
    h = header()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h)
        w.writeheader()
        for r in ROWS:
            w.writerow({k: r.get(k, "") for k in h})
    return path
