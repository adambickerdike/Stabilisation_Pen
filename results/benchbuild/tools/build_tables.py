"""Tables of the first bench build plan (study H): python3 results/benchbuild/tools/build_tables.py

Writes into results/benchbuild/:
  bom_B0_daq1.csv, bom_B1_r9_g1.csv, bom_B2_g2_coupons.csv, bom_B3_fivebar.csv, bom_B4_r10.csv
  cost_schedule.csv, cost_totals.json, test_decision_map.csv
  proposed_experiments.csv, proposed_criteria.csv (acceptance_criteria.csv columns), proposed_decisions.csv
  evidence_rows.csv (docs/evidence.csv's 23-column header, CRLF)
  templates/*.csv, templates/record_template.yaml, templates/verdict_template.yaml

Price labels: MANUFACTURER = a price and stock seen on a manufacturer or distributor page on the date given, with
its part number, URL and ledger id; ASSUMPTION = a labelled range where no price was visible (the reason is given).
EUR prices are converted with an ASSUMED 1.05-1.25 USD/EUR. Nothing here is a quote; a request for quotation pins
every ASSUMPTION line. Nothing has been bought or built.
"""
from __future__ import annotations

import csv
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results" / "benchbuild"
TPL = OUT / "templates"
SEEN = "2026-09-30"
EUR = (1.05, 1.25)            # ASSUMPTION exchange-rate range, USD per EUR

BOM_COLS = ["build", "line", "kind", "item", "manufacturer", "part_number", "supplier", "supplier_pn", "qty",
            "unit_price_seen", "currency", "unit_usd_low", "unit_usd_high", "line_usd_low", "line_usd_high",
            "price_label", "price_source", "seen", "availability", "lead_time", "ledger", "fabrication_source",
            "material", "process", "tolerance_finish", "who", "stage", "mvp", "optional_if_lab_has_it", "notes"]

# who: hobbyist (skilled hobbyist or small team, hand tools, 3-D printer, soldering), shop (machine shop: CNC,
# lathe, wire EDM, grinding/lapping), supplier (specialist service: coil winding, photo-etching, magnets, fine wire,
# heat treatment, metrology service)

ROWS = []


def seen(build, line, kind, item, mfr, pn, supplier, spn, qty, price, cur, url, avail, lead, ledger, stage, mvp,
         who="hobbyist", optional="N", notes="", fab="", material="", process="", tol=""):
    lo, hi = (price * EUR[0], price * EUR[1]) if cur == "EUR" else (price, price)
    ROWS.append(dict(build=build, line=line, kind=kind, item=item, manufacturer=mfr, part_number=pn, supplier=supplier,
                     supplier_pn=spn, qty=qty, unit_price_seen=price, currency=cur, unit_usd_low=round(lo, 2),
                     unit_usd_high=round(hi, 2), price_label="MANUFACTURER", price_source=url, seen=SEEN,
                     availability=avail, lead_time=lead, ledger=ledger, fabrication_source=fab, material=material,
                     process=process, tolerance_finish=tol, who=who, stage=stage, mvp=mvp,
                     optional_if_lab_has_it=optional, notes=notes))


def assume(build, line, kind, item, mfr, pn, supplier, qty, lo, hi, why, lead, stage, mvp, who="hobbyist",
           optional="N", ledger="", notes="", fab="", material="", process="", tol=""):
    ROWS.append(dict(build=build, line=line, kind=kind, item=item, manufacturer=mfr, part_number=pn, supplier=supplier,
                     supplier_pn="", qty=qty, unit_price_seen="", currency="USD", unit_usd_low=lo, unit_usd_high=hi,
                     price_label="ASSUMPTION", price_source=why, seen="", availability="", lead_time=lead,
                     ledger=ledger, fabrication_source=fab, material=material, process=process, tolerance_finish=tol,
                     who=who, stage=stage, mvp=mvp, optional_if_lab_has_it=optional, notes=notes))


DK = "https://www.digikey.com/en/products/"

# ------------------------------------------------------------------------------------------------ B0 DAQ-1 (shared)
B = "B0"
seen(B, 1, "purchased", "Microcontroller board Teensy 4.1 (DAQ-1 and a spare)", "PJRC", "Teensy 4.1", "SparkFun",
     "DEV-16771", 2, 31.50, "USD", "https://www.sparkfun.com/teensy-4-1.html", "In stock", "1-5 days (in stock)",
     "AMF-220 (re-seen 2026-09-30)", "S0", "Y", notes="600 MHz cycle counter is the time base (docs/measurement_rig.md s1.3)")
seen(B, 2, "purchased", "24-bit 8-channel simultaneous ADC evaluation module (EVM, PHI controller, USB cable)",
     "Texas Instruments", "ADS131M08EVM", "DigiKey", "296-ADS131M08EVM-ND", 1, 328.11, "USD",
     DK + "result?keywords=ADS131M08EVM", "2 in stock (DigiKey); TI page 'In stock', price after login",
     "1-5 days (in stock)", "AMF-300", "S0", "Y",
     notes="the PHI board is not used: J10 wired to the Teensy, AVDD/DVDD per SBAU334A (AMF-222); a second EVM only if R9 and R12 run at the same time")
seen(B, 3, "purchased", "Thermocouple amplifier breakout MAX31856", "Adafruit", "3263", "Adafruit", "3263", 4, 17.50,
     "USD", "https://www.adafruit.com/product/3263", "In stock", "1-5 days", "AMF-234 (re-seen 2026-09-30)", "S0", "Y")
assume(B, 4, "purchased", "Type-T fine-wire thermocouples, 0.08 mm class (calibrate in a dry block, +-0.5 C)",
       "class (e.g. Omega 5TC series)", "type T, 40 AWG class", "instrument distributor", 8, 15, 40,
       "omega.com returned HTTP 403 on 2026-09-30: price not seen", "1-2 weeks (ASSUMPTION)", "S0", "Y")
seen(B, 5, "purchased", "Current-sense resistor 0.1 ohm +-0.1 % 1 W, 4-terminal metal foil (2512)", "VPG Foil Resistors",
     "Y14870R10000B9R", "DigiKey", "804-1045-1-ND", 4, 13.05, "USD", DK + "result?keywords=Y14870R10000B9R",
     "0 in stock; 1,000 expected 12-Oct-2026", "about 2 weeks", "AMF-303", "S0", "Y",
     notes="coil and voice-coil currents on ADC channels (CHANNEL_MAPS)")
seen(B, 6, "purchased", "Linear power op-amp for current drive (voice coils, coupon coils), TO-220-7",
     "Texas Instruments", "OPA548T", "DigiKey", "product 266166", 2, 21.55, "USD",
     DK + "detail/texas-instruments/OPA548T/266166",
     "0 in stock, 50 expected 30-Nov-2026 (DigiKey); TI store: out of stock", ">= 9 weeks (back-order)", "AMF-301", "S1",
     "N", notes="LEAD-TIME RISK. Fallbacks: OPA564AIDWP (1.5 A, DigiKey USD 9.51, stock not shown, AMF-301) on a small board; "
     "or Pololu 4035 DRV8874 (AMF-305) at >= 40 kHz with an output LC filter for the R9 voice coil; OPA549T also back-ordered (02-Dec-2027)")
seen(B, 7, "purchased", "12 V 60 W desktop supply (driver and excitation rails)", "Mean Well", "GST60A12-P1J", "DigiKey",
     "product 7703712", 1, 19.40, "USD", DK + "result?keywords=GST60A12-P1J", "in stock (Normally Stocking)", "1-5 days",
     "AMF-308", "S0", "Y")
assume(B, 8, "purchased", "Wiring kit: headers, JST/Dupont, shielded 12-core cable, perfboard, RC filters, 10 ohm/10 uF excitation filter",
       "class", "-", "any electronics distributor", 1, 60, 150, "lot of commodity parts, not priced line by line", "1 week",
       "S0", "Y")
assume(B, 9, "fabricated", "DAQ-1 enclosure and connector panel", "-", "PROPOSED DESIGN (no CAD)", "in-house", 1, 10, 40,
       "3-D print filament and hardware", "1-3 days", "S0", "Y", material="PETG or laser-cut acrylic",
       process="FDM 3-D print / laser cut", tol="+-0.3 mm", fab="none (make to fit the EVM and Teensy)")
seen(B, 10, "instrument", "Oscilloscope 4 ch 70 MHz (bring-up loop-backs, trigger and strobe timing)", "Rigol", "DHO804",
     "DigiKey", "2211-DHO804-ND", 1, 459.00, "USD", DK + "result?keywords=DHO804", "40 in stock", "1-5 days", "AMF-321",
     "S0", "N", optional="Y")
seen(B, 11, "instrument", "6.5-digit DMM with 4-wire resistance (wire, coil and shunt resistance)", "Siglent", "SDM3065X",
     "DigiKey", "product 10455229", 1, 857.00, "USD", DK + "result?keywords=SDM3065X", "stock not shown",
     "1-2 weeks (ASSUMPTION)", "AMF-322", "S0", "N", optional="Y")
assume(B, 12, "instrument", "Dual linear bench supply 0-30 V (+-15 V for the OPA548 stage)", "class", "-", "any", 1, 150,
       450, "not priced here", "1 week", "S0", "N", optional="Y")
assume(B, 13, "tool", "Temperature-controlled soldering station", "class", "-", "any", 1, 100, 250, "not priced here",
       "1 week", "S0", "Y", optional="Y")
seen(B, 14, "tool", "Bench fume absorber (soldering; beryllium-copper joints under local exhaust, DEC-097 proposed)",
     "Hakko", "FA400-04", "DigiKey", "product 6228795", 1, 93.79, "USD", DK + "result?keywords=FA400-04",
     "stock not shown", "1-2 weeks (ASSUMPTION)", "AMF-317", "S0", "Y")
assume(B, 15, "tool", "Hand tools: calipers 0.01 mm, micrometer 0.001 mm, ESD mat, tweezers, flush cutters, loupe",
       "class", "-", "any", 1, 150, 400, "not priced here", "1 week", "S0", "Y", optional="Y")

# ------------------------------------------------------------------------------------------------ B1 R9 contact and ink (G1)
B = "B1"
seen(B, 1, "purchased", "CoreXY printer kit as the motion frame (head moves in x-y, bed only in z; chamber to 55 C)",
     "Prusa Research", "Prusa CORE One+ (Gen 2) assembly kit", "prusa3d.com", "-", 1, 925.00, "USD",
     "https://www.prusa3d.com/product/prusa-core-one/", "In stock. Preparation time: 1-3 business days",
     "1-2 weeks incl. shipping (shipping ASSUMPTION)", "AMF-231 (re-seen 2026-09-30)", "S0", "Y",
     notes="assembled USD 1,202.78 on the same page; hotend and bed heaters disconnected; payload of the 190 g head checked (EXP-BB02)")
assume(B, 2, "instrument", "3-axis force sensor +-2 N under the paper (N and friction in the page frame)",
       "ME-Messsysteme", "K3D40 +-2N", "me-systeme.de (quote)", 1, 900, 1900,
       "price behind a login (me-systeme.de HTTP 403; pm-instrumentation.com 'Log in to view prices'), 2026-09-30",
       "2-6 weeks (ASSUMPTION; order day 1)", "S0", "Y", who="supplier", ledger="AMF-224")
assume(B, 3, "instrument", "3-axis force sensor +-10 N (N and friction above the +-2 N plate's range; R12 force map; five-bar force capacity)",
       "ME-Messsysteme", "K3D40 +-10N", "me-systeme.de (quote)", 1, 900, 1900, "as line 2", "2-6 weeks (ASSUMPTION)",
       "S1", "N", who="supplier", ledger="AMF-224")
assume(B, 4, "instrument", "In-line axial load cell 100 g (1 N), 2 mV/V", "FUTEK", "LSB200 FSH03870", "futek.com (quote)", 1,
       450, 900, "FUTEK store page shows $0.00 (price not displayed), 2026-09-30", "1-4 weeks (ASSUMPTION)", "S0", "Y",
       who="supplier", ledger="AMF-225")
assume(B, 5, "purchased", "Voice coil for F_c ramps and modulation (current mode)", "Moticont", "LVCM-013-013-03",
       "moticont.com (quote)", 1, 150, 350, "product page lists specifications, no price (2026-09-30)",
       "2-6 weeks (ASSUMPTION)", "S1", "N", who="supplier", ledger="AMF-02",
       notes="MVP: dead weights on a thread over a jewel-bearing pulley (fixed F_c levels, docs/measurement_rig.md s2.9)")
assume(B, 6, "instrument", "Linear magnetic encoder LM13, 13B resolution, with MS scale (per axis)", "RLS", "LM13 (13B)",
       "RLS / Renishaw distributor (quote)", 2, 250, 700, "no price published (OPT-89)", "2-6 weeks (ASSUMPTION)", "S1", "N",
       who="supplier", ledger="OPT-89",
       notes="MVP: stroke timing from the printer's move start (marker input, pin 32) and the commanded speed; LM13 needed for R10 per-sample truth")
seen(B, 7, "purchased", "Linear Hall sensor for the cartridge slide", "Texas Instruments", "DRV5055A4QDBZR", "DigiKey",
     "296-50468-1-ND", 4, 0.87, "USD", DK + "result?keywords=DRV5055A4QDBZR", "3,538 in stock", "1-5 days", "AMF-302",
     "S0", "Y")
assume(B, 8, "purchased", "Slide target magnet, N52, about 2 mm", "class", "-", "magnet retailer", 4, 0.5, 3,
       "commodity", "1 week", "S0", "Y")
assume(B, 9, "consumable", "Refills: Schmidt S 635 M x20, easyFLOW 9000 x10, P 8126 x10, FL 6040 F x10; a second D1 oil brand x10 and a gel D1 x10 (study B's EXP-B20 set)",
       "Schmidt Technology; class", "as listed", "stationery distributors", 1, 70, 360, "prices not seen (CON-100)",
       "1-2 weeks", "S0", "Y", ledger="CON-100", notes="log brand and lot")
assume(B, 10, "consumable", "Six papers (copy 80 g/m2, recycled, school ruled, coated, tracing, card), one pack each",
       "class", "-", "stationery", 1, 60, 150, "commodity", "1 week", "S0", "Y", notes="condition 24 h at 23 C / 50 % RH")
seen(B, 11, "instrument", "Calibration weight set OIML M1, 1 g-500 g (12 pieces)", "Mettler Toledo", "30402728",
     "Scales Galore", "px60692", 1, 535.50, "USD",
     "https://www.scalesgalore.com/product/Mettler-Toledo-30402728-OIML-Class-M1-Stainless-Steel-Calibration-Weight-Set-1-g-to-500-g-px60692.cfm",
     "Available to Ship", "1-2 weeks (ASSUMPTION)", "AMF-315", "S0", "Y",
     notes="in-situ calibration at every test angle; also the MVP's dead-weight F_c")
assume(B, 12, "purchased", "Jewel-bearing pulley and thread (horizontal pulls; dead-weight F_c)", "class", "-", "any", 1,
       20, 80, "not priced here", "1-2 weeks", "S0", "Y")
assume(B, 13, "instrument", "Digital inclinometer 0.1 deg class (tilt under load)", "class", "-", "any", 1, 30, 120,
       "not priced here", "1 week", "S0", "Y")
assume(B, 14, "consumable", "Spring-steel shim 0.05 mm (guide leaves)", "class", "-", "any", 1, 20, 60, "not priced here",
       "1 week", "S0", "Y")
seen(B, 15, "instrument", "Flatbed scanner 4800 dpi optical (gap fractions for EXP-T02)", "Epson",
     "Perfection V39 II (B11B268201)", "epson.com", "B11B268201", 1, 129.99, "USD",
     "https://www.epson.com/For-Work/Scanners/Photo-and-Graphics/Epson-Perfection-V39-II-Color-Photo-and-Document-Scanner/p/B11B268201",
     "'Add to Cart' shown", "1-2 weeks", "AMF-314", "S0", "Y",
     notes="R3's 5 um (k=2) ink-path metrology for G3 needs the V850 Pro (USD 1,999, AMF-236) or a microscope: deferred")
assume(B, 16, "instrument", "USAF-1951 resolution target (scanner check before gap fractions)", "class", "-", "optics retailer",
       1, 50, 200, "not priced here", "1-2 weeks", "S0", "Y")
assume(B, 17, "consumable", "Underlays (1 mm float glass, 10-sheet pad, 1 mm elastomer) and 1.5 mm CFRP sheet", "class",
       "-", "any", 1, 30, 100, "not priced here", "1 week", "S0", "Y")
assume(B, 18, "purchased", "Fasteners, dowel pins, M3 kit", "class", "-", "any", 1, 30, 80, "not priced here", "1 week",
       "S0", "Y")
assume(B, 19, "fabricated", "Tilt arc R70 (35/50/65/75 deg holes) and arc carriage: printed MVP version", "-",
       "arc_frame, arc_carriage", "in-house", 1, 10, 40, "filament", "1-3 days", "S0", "Y",
       fab="results/rig/cad/rig_contact_assembly.step (arc_frame, arc_carriage)", material="PETG or PA-CF",
       process="FDM 3-D print", tol="+-0.2 mm; tilt set and checked under load with the inclinometer",
       notes="replace by the CNC version (line 20) if the tilt drifts by > 0.1 deg under load")
assume(B, 20, "fabricated", "Tilt arc R70 and arc carriage: CNC version", "-", "arc_frame, arc_carriage",
       "machine shop", 1, 150, 600, "one-off CNC quote range", "1-3 weeks", "S1", "N", who="shop",
       fab="results/rig/cad/rig_contact_assembly.step (arc_frame, arc_carriage)", material="6061-T6",
       process="CNC milling", tol="hole pattern +-0.05 mm; arc radius +-0.05 mm", notes="bead blast; anodise optional")
assume(B, 21, "fabricated", "Cartridge frame with leaf clamps, refill holder/collet (D1 2.35 mm; G2 6 mm), Hall bracket",
       "-", "cartridge_frame, holder, hall_bracket", "machine shop", 1, 150, 500, "one-off CNC/lathe quote range",
       "1-3 weeks", "S0", "Y", who="shop",
       fab="results/rig/cad/rig_contact_assembly.step (cartridge_frame, holder, hall_bracket)",
       material="6061-T6; brass collet; printed bracket", process="CNC milling, lathe; FDM for the bracket",
       tol="+-0.02 mm on the leaf clamp faces; holder bore 2.4 H7", notes="the axial path must be straight: closure check AC-T01-01")
assume(B, 22, "fabricated", "Guide leaves 0.05 x 8 x 25 mm (x2)", "-", "guide_leaves", "in-house", 2, 0, 25,
       "from the shim of line 14", "1 day", "S0", "Y",
       fab="results/rig/cad/rig_contact_assembly.step (guide_leaves)", material="spring steel shim 0.05 mm",
       process="shear or scalpel against a template, deburr; or photo-etch", tol="+-0.05 mm, flat, no kinks")
assume(B, 23, "fabricated", "Bed adapter 120 x 100 x 6 mm and head plate to the CORE One carriage", "-",
       "bed_adapter; head plate", "machine shop", 1, 100, 350, "one-off CNC quote range", "1-3 weeks", "S0", "Y",
       who="shop", fab="results/rig/cad/rig_contact_assembly.step (bed_adapter); head plate from the CORE One's published CAD",
       material="6061-T6", process="CNC milling", tol="flatness 0.05 mm; K3D40 M3 pattern +-0.05 mm")
assume(B, 24, "fabricated", "CFRP platen 80 x 60 x 1.5 mm and paper edge clamps", "-", "platen_cfrp, clamp_nx, clamp_px",
       "supplier cut + in-house clamps", 1, 20, 100, "waterjet/CNC of a CFRP sheet by a supplier (dust)", "1-2 weeks",
       "S0", "Y", who="supplier", fab="results/rig/cad/rig_contact_assembly.step (platen_cfrp, clamp_nx, clamp_px)",
       material="CFRP 1.5 mm; PETG clamps", process="waterjet or CNC routing (supplier, dust extraction); FDM",
       tol="+-0.2 mm")
assume(B, 25, "instrument", "In-line axial load cell 250 g (2.5 N): N up to 2 N at every tilt (AC-B01-20's envelope) and G2-format refills",
       "FUTEK", "LSB200 FSH03871", "futek.com (quote)", 1, 450, 900, "price not displayed (as line 4)",
       "1-4 weeks (ASSUMPTION)", "S1", "N", who="supplier", ledger="AMF-225",
       notes="the rig design uses the 100 g cell for F_c <= 0.5 N and the 250 g cell above (docs/measurement_rig.md s2.2); "
             "EXP-B01's 4 N level needs a larger cell still (prototype_stages.md s0 open item; bench_calcs.json r9_normal_force_reach)")

# ------------------------------------------------------------------------------------------------ B2 G2 coupons
B = "B2"
# (a) force-constant coupons: EXP-T07 (study K's EXP-K22 coil; the reach candidate's winding)
seen(B, 1, "purchased", "N52 block magnets 5 x 5 x 3 mm (+-0.1 mm), magnetised through 3 mm: stock stand-in for Rev K's 5.12 x 5.12 x 3.5 mm poles",
     "Webcraft GmbH (supermagnete)", "Q-05-05-03-N52N", "supermagnete.de", "Q-05-05-03-N52N", 20, 0.35, "EUR",
     "https://www.supermagnete.de/eng/block-magnets-neodymium/block-magnet-5mm-5mm-3mm_Q-05-05-03-N52N",
     "2,120 pieces in stock; 1-3 business days", "1-2 weeks incl. shipping", "AMF-309", "S2", "N",
     notes="EUR 0.35 each at 20+ incl. VAT; predictions re-run at the as-built size (bench_protocols.md s0.2)")
seen(B, 2, "purchased", "N52 cube magnets 4.76 mm (+-0.1 mm): stock stand-in for the reach candidate's 4.81 mm poles",
     "K&J Magnetics", "B333-N52", "kjmagnetics.com", "B333-N52", 12, 0.56, "USD",
     "https://www.kjmagnetics.com/b333-n52-neodymium-block-magnet", "In Stock", "1-2 weeks", "AMF-310", "S2", "N",
     notes="Br 14,800 G on the page; 1.26 mm thicker than the 3.5 mm design pole")
assume(B, 3, "purchased", "Custom N52 poles 4.81 x 4.81 x 3.5 mm and 5.12 x 5.12 x 3.5 mm (8 of each), after AC-T07-02 passes on stock magnets",
       "custom magnet maker", "to drawing", "magnet supplier (quote)", 1, 150, 600, "custom batch, not quoted",
       "4-8 weeks (ASSUMPTION)", "S2b", "N", who="supplier", notes="deferred (DEC-095 proposed)")
assume(B, 4, "fabricated", "Back iron 0.5 mm and keeper 0.3 mm rings (reach: R 10.6/3.6 mm); Rev K back plate and keeper, and the heel variant's 1.2 mm notched pair",
       "-", "back_iron, keeper_with_front_race_surface; back_plate, keeper", "laser/EDM service", 1, 60, 300,
       "small laser or wire-EDM batch", "1-3 weeks", "S2", "N", who="shop",
       fab="results/improvement/mechanics/extended_reach_nib.step (back_iron, keeper_with_front_race_surface); results/revK/revK_pen_assembly.step (back_plate, keeper)",
       material="low-carbon steel 1008/1010 sheet", process="wire EDM or fibre-laser cut, deburr, stress relieve",
       tol="+-0.02 mm; flatness 0.02 mm")
assume(B, 5, "service", "Racetrack coil packs, bonded: 0.8 mm per layer, bundles 2.2 mm wide, rows 4.75 mm (reach) or 5.0 mm (Rev K) off axis, xy order; 2-4 sets",
       "-", "winding_pack_0/1_+-1; coil_x, coil_y", "coil-winding service (quote)", 1, 300, 1500,
       "prototype coil sets not quoted", "3-6 weeks (ASSUMPTION)", "S2", "N", who="supplier",
       fab="results/improvement/mechanics/extended_reach_nib.step (winding_pack_*); results/revK/revK_pen_assembly.step (coil_x, coil_y)",
       material="self-bonding enamelled copper wire", process="wound on a split mandrel, heat or solvent bonded",
       tol="layer thickness +-0.03 mm; outer corner inside the bore rule",
       notes="in-house alternative: hand winding with bondable wire (line 6), skilled hobbyist; record turns, R20 and L")
assume(B, 6, "consumable", "Self-bonding magnet wire 0.10-0.14 mm (in-house winding)", "class", "-", "wire distributor", 1,
       20, 60, "not priced here", "1-2 weeks", "S2", "N")
assume(B, 7, "fabricated", "Translation-coupon stator block (magnets at the 0.3 mm coil gap, 0.15 mm keeper spacer) and coil arm through the keeper hole",
       "-", "stator_plate, coupon_arm, base_plate, bridge", "machine shop", 1, 200, 700, "one-off CNC quote range",
       "1-3 weeks", "S2", "N", who="shop",
       fab="results/rig/cad/rig_coupon_assembly.step (base_plate, bridge, stator_plate, coupon_arm; goniometers locked for translation coupons)",
       material="6061-T6; PEEK or resin arm", process="CNC milling; SLA print for the arm",
       tol="+-0.02 mm on gap-setting faces; coil centred on the pole pattern within 0.05 mm")
assume(B, 8, "instrument", "Manual XYZ stage, 13-25 mm travel, 10 um graduation (coil position grid)",
       "class (Thorlabs PT3/M class)", "-", "optics retailer", 1, 400, 1600,
       "Thorlabs product pages are script-rendered and showed no price here; not seen", "1-3 weeks", "S2", "N")
assume(B, 9, "instrument", "LCR meter (coil inductance 100 Hz-10 kHz)", "class", "-", "any", 1, 100, 600,
       "not priced here", "1-2 weeks", "S2", "N", optional="Y")
# (b) wire coupons: EXP-K21 (Rev K, 26.8 mm x4) and EXP-BB04 (reach, 34 mm x8)
seen(B, 10, "purchased", "C17200 (CuBe2) wire 0.10 mm and 0.08 mm, ordered age-hardened (DEC-097 proposed)", "Goodfellow",
     "Cu98/Be2 wire (code per diameter)", "goodfellow.com", "-", 2, 279.00, "USD",
     "https://www.goodfellow.com/usa/copper-beryllium-alloy-spooled-wire-cu98-be2-group",
     "'Starting at $279.00 each' (spooled); approximate lead time 2 weeks; diameters not displayed statically",
     "about 2 weeks", "AMF-311", "S2", "N", who="supplier",
     notes="straight 1 m hard wire from USD 429.00 on the sister page; CONFIRM 0.10 mm and an aged temper (TH04/HT or AT) before ordering")
assume(B, 11, "fabricated", "Wire clamp blocks (0.12 mm solder slot, 0.1 mm exit edge radius) x24, and crimp tubes",
       "-", "PROPOSED DESIGN (no CAD)", "machine shop", 1, 200, 700, "one-off precision batch", "2-4 weeks", "S2", "N",
       who="shop", material="C360 brass (solder clamps); 304 hypodermic tube (crimp)",
       process="CNC + wire-EDM slot; exit radius polished before the wire goes in",
       tol="slot +-0.01 mm; exit radius 0.10 +-0.02 mm (sets Kt)")
assume(B, 12, "fabricated", "Multi-coupon fatigue shuttle: crank-eccentric drive (stroke 1.26 or 1.7 mm), parallel-leaf guided shuttle, >= 6 coupon stations, guard",
       "-", "PROPOSED DESIGN (no CAD)", "machine shop", 1, 300, 1200, "one-off", "2-4 weeks", "S2", "N", who="shop",
       material="6061-T6; spring-steel leaves; steel eccentric", process="CNC; ground eccentric pin",
       tol="eccentricity +-0.01 mm; shuttle straightness 0.02 mm",
       notes="drive <= 0.2 x the coupon's measured first mode (DEC-098 proposed); balanced crank; guard (pinch point)")
assume(B, 13, "purchased", "Shuttle drive motor and speed controller (3,600-9,000 rpm)", "class", "-", "any", 1, 40, 200,
       "not priced here", "1-2 weeks", "S2", "N")
assume(B, 14, "purchased", "Eight-channel constant-current source 0.10-0.16 A with 4-wire sense leads to the ADS131M08",
       "class", "PROPOSED DESIGN", "parts from any distributor", 1, 30, 100, "commodity parts", "1-2 weeks", "S2", "N")
seen(B, 15, "instrument", "Laser displacement sensor, 30 mm (shuttle amplitude; wire first mode)", "Panasonic", "HG-C1030",
     "DigiKey", "product 5215054", 1, 439.60, "USD", DK + "detail/panasonic-industry/HG-C1030/5215054",
     "26 in stock; response time 1.5 ms", "1-5 days", "AMF-318", "S2", "N", optional="Y",
     notes="the strobed OV9281 camera (B4) can replace it for the first mode")
assume(B, 16, "instrument", "Stereo microscope >= 50x with camera (wire and clamp inspection)", "class", "-", "any", 1, 300,
       1500, "not priced here", "1-2 weeks", "S2", "N", optional="Y")
assume(B, 17, "consumable", "SnAgCu solder, flux for copper alloys, IPA wipes, sealable labelled waste bags", "class", "-",
       "any", 1, 30, 80, "not priced here", "1 week", "S2", "N")
assume(B, 18, "fabricated", "Scaled Kt coupons: 1.0 mm C17200 wire in 10x clamps with 0.2 mm-grid strain gauges (Kt is geometric)",
       "-", "PROPOSED DESIGN", "in-house + shop", 1, 150, 400, "gauges, wire and clamps", "2-3 weeks", "S2", "N",
       who="shop", notes="a strain gauge cannot be bonded on a 0.10 mm wire; open item for the lead (Kt method)")
# (c) ball-guide coupons: EXP-K20 (Rev K) and EXP-BB05 (both guides, preload map)
assume(B, 19, "purchased", "Si3N4 balls 0.8 mm, grade 5", "class (Ortech Ceramics lists 0.8 mm)", "-", "ceramic-ball supplier",
       100, 0.2, 0.8, "prices not displayed (Ortech: quote; retail listings not opened)", "1-3 weeks", "S2", "N")
assume(B, 20, "fabricated", "Lapped 440C races: Rev K (16.6 mm ball circle, 2.26 mm wide) x3; reach (15.1 mm circle, 2.9 mm wide) x3; flange race inserts x4",
       "-", "front_race, rear_race; rear_race, keeper_with_front_race_surface", "precision grinding shop", 1, 400, 1500,
       "one-off hardened, ground and lapped batch", "3-6 weeks (ASSUMPTION)", "S2", "N", who="shop",
       fab="results/revK/revK_pen_assembly.step (front_race, rear_race); results/improvement/mechanics/extended_reach_nib.step (rear_race, keeper_with_front_race_surface)",
       material="440C stainless", process="turn, harden and temper (HRC 58-60, ASSUMPTION), grind, lap",
       tol="flatness <= 1 um; parallelism <= 2 um; Ra <= 0.05 um (ASSUMPTION spec)")
assume(B, 21, "fabricated", "Carrier flanges: Rev K 18.9 x 1.5 mm and reach 18 x 1.5 mm; one with 440C race inserts, one bare Ti face",
       "-", "carrier_flange; moving_flange", "machine shop", 1, 150, 600, "one-off CNC", "2-4 weeks", "S2", "N", who="shop",
       fab="results/revK/revK_pen_assembly.step (carrier_flange); results/improvement/mechanics/extended_reach_nib.step (moving_flange)",
       material="Ti-6Al-4V; 440C inserts", process="CNC turning, lapping of the faces",
       tol="faces parallel <= 2 um; thickness +-0.005 mm",
       notes="a bare Ti face sees 2.6 GPa Hertz stress (CALC): EXP-BB05 checks for marks")
assume(B, 22, "purchased", "Wave springs about 4 N at working height, several rates (preload steps 1-4 N)",
       "class (Smalley class)", "-", "spring distributor", 6, 4, 15, "not priced here", "1-3 weeks", "S2", "N")
assume(B, 23, "instrument", "Low-capacity load cell 10 g (0.1 N) for guide drag (+-0.1 % RO)", "FUTEK", "LSB200 FSH03867",
       "futek.com (quote)", 1, 450, 900, "price not displayed (as B1 line 4)", "1-4 weeks (ASSUMPTION)", "S2", "N",
       who="supplier", ledger="AMF-225", notes="the K3D40 plate cannot judge a 5 mN line (TUR < 1, bench_calcs.json)")
assume(B, 24, "instrument", "Tilt measurement: laser lever (diode laser + position-sensitive detector); an autocollimator costs 3,000-8,000",
       "class", "-", "optics retailer", 1, 300, 900, "not priced here", "1-3 weeks", "S2", "N")
assume(B, 25, "fabricated", "Drop rig: 1 m guide tube and a dummy pen carrying the guide", "-", "PROPOSED DESIGN",
       "in-house", 1, 30, 100, "tube and filament", "1 week", "S2", "N", material="PETG body; acrylic tube",
       process="FDM", tol="+-0.3 mm")
assume(B, 26, "service", "Race surface profilometry before and after drops", "-", "-", "metrology lab", 2, 100, 400,
       "per session, not quoted", "1-2 weeks", "S2", "N", who="supplier")
# (d) anchor coupon: EXP-BB03
seen(B, 27, "purchased", "301 stainless foil, hard, 0.035 mm target (0.030/0.038 mm alternatives; measure each sheet)",
     "Goodfellow", "AISI 301 foil (code per thickness)", "goodfellow.com", "-", 1, 252.00, "USD",
     "https://www.goodfellow.com/usa/aisi-301-stainless-steel-foil-group",
     "'$252.00' starting price; thickness band 0.01-0.05 mm listed in the tolerance table", "not shown (ASSUMPTION 2 weeks)",
     "AMF-312", "S2", "N", who="supplier")
assume(B, 28, "service", "Precision photo-etching or UV-laser micromachining of the 4-beam anchor (beam width +-0.01 mm), artwork set from the measured foil",
       "-", "floating_anchor_coupon.step", "precision etcher (quote)", 1, 300, 1500, "first batch with tooling, not quoted",
       "2-4 weeks (ASSUMPTION)", "S2", "N", who="supplier",
       fab="results/improvement/mechanics/floating_anchor_coupon.step", material="301 full-hard foil",
       process="photochemical etching or UV/femtosecond laser cutting", tol="beam width +-0.01 mm; burr-free",
       notes="Ponoko's service (+-0.13 mm, minimum feature 1 mm, AMF-313) cannot make 0.5 mm beams")
assume(B, 29, "service", "Flexible interconnect for the anchor (polyimide flex, within the ~23 N/m axial allowance)", "-",
       "PROPOSED DESIGN", "flex-PCB prototype service", 1, 50, 300, "not quoted", "1-3 weeks", "S2", "N", who="supplier")
assume(B, 30, "instrument", "Precision balance, >= 1 mg readability (force by weighing: anchor stiffness, wire preload)",
       "class", "-", "lab supplier", 1, 200, 2500, "not priced here", "1-2 weeks", "S2", "N", optional="Y")
assume(B, 31, "instrument", "Micrometer head 1 um (or the XYZ stage) for the anchor hub displacement", "class", "-", "any", 1,
       80, 400, "not priced here", "1-2 weeks", "S2", "N")
assume(B, 32, "fabricated", "Anchor test frame: hub pusher, outer-ring clamp, flatness datum", "-", "PROPOSED DESIGN",
       "in-house or shop", 1, 50, 200, "not quoted", "1-2 weeks", "S2", "N", who="shop", material="6061 / PETG",
       process="CNC or FDM", tol="+-0.02 mm on the clamp datum")
# (e) counter-face bench: EXP-J17 part (c) on R9's frame
assume(B, 33, "instrument", "Second 3-axis force sensor +-2 N under the refill carrier (residual side load)",
       "ME-Messsysteme", "K3D40 +-2N", "me-systeme.de (quote)", 1, 900, 1900, "as B1 line 2", "2-6 weeks (ASSUMPTION)",
       "S2", "N", who="supplier", ledger="AMF-224",
       notes="the protocol names a 6-axis cell (ATI Nano17, price not seen, AMF-223; ASSUMPTION 5,000-9,000): the K3D40 gives forces, not the couple")
assume(B, 34, "fabricated", "Counter-face bench parts: 6 mm hardened disc on a cross-strip flexure, constant-force strip spring, follower stop, rolling refill guide and carrier",
       "-", "PROPOSED DESIGN in docs/balanced_nib.md (no STEP yet)", "machine shop", 1, 300, 1000, "one-off", "2-4 weeks",
       "S2", "N", who="shop", material="17-4PH / 440C; spring steel", process="CNC, wire EDM", tol="+-0.01 mm",
       notes="open item: the part (c) fixture has no CAD")

# ------------------------------------------------------------------------------------------------ B3 grounded five-bar
B = "B3"
seen(B, 1, "purchased", "Brushed coreless DC motor 22 mm, 12 V (two + one spare)", "Faulhaber",
     "2224U012SR (DigiKey listing: manufacturer number '2224.11000')", "DigiKey (marketplace)", "5293-2224.11000-ND", 3,
     122.60, "USD", DK + "result?keywords=5293-2224.11000-ND",
     "7 in stock; 'Will ship in approximately 5 days from Faulhaber'; USD 9 flat shipping", "about 1 week", "AMF-304",
     "S3", "N", notes="found by searching 2224U012SR; confirm the catalogue code is the 2224 U 012 SR before ordering (RS 873-4795: 12 V, 6.7 mNm, 4390 rpm)")
seen(B, 2, "purchased", "Output-shaft magnetic encoder, 14-bit, on adapter board (two + one spare)", "ams OSRAM",
     "AS5047P adapter board", "DigiKey", "4991-AS5047PADAPTERBOARD-ND", 3, 19.40, "USD",
     DK + "result?keywords=AS5047P-TS_EK_AB", "397 in stock", "1-5 days", "AMF-307", "S3", "N",
     notes="the AS5047P IC is listed as discontinued at DigiKey: buy the boards now; FiveBar assumes 16-bit (1.99 um vs 7.98 um quantisation, bench_calcs.json)")
assume(B, 3, "purchased", "Diametric encoder magnets 6 x 2.5 mm", "class", "-", "magnet retailer", 4, 2, 8,
       "not priced here", "1 week", "S3", "N")
seen(B, 4, "purchased", "Motor driver with current sense (DRV8874 carrier), current loop run in the controller Teensy",
     "Pololu", "4035", "pololu.com", "4035", 3, 11.94, "USD", "https://www.pololu.com/product/4035",
     "'Active and Preferred'", "1 week", "AMF-305", "S3", "N",
     notes="alternative: maxon ESCON Module 24/2 (466023), EUR 97.68 (1-4), NRND, current-controller mode (AMF-306)")
seen(B, 5, "purchased", "Deep-groove bearings MR63-ZZ 3 x 6 x 2.5 mm (elbows, pen joint, output shafts)",
     "class (Bearings Direct stock)", "MR63-ZZ", "Bearings Direct", "MR63-ZZ", 12, 4.38, "USD",
     "https://bearingsdirect.com/mr63-zz-mini-ball-bearing-3x6x2-5-shielded-l-630zz/",
     "684 available; usually ships in 24 hours", "1 week", "AMF-316", "S3", "N", notes="10-24 units 5 % off; ABEC grade not stated")
assume(B, 6, "purchased", "Ground shafts 3 mm h6 (dowel pins) and 2 mm set-screw hubs", "class", "-", "any", 1, 15, 40,
       "not priced here", "1 week", "S3", "N")
assume(B, 7, "consumable", "Capstan cable (braided Dyneema 0.3-0.5 mm or 7x7 stainless 0.45 mm) and tensioners", "class",
       "-", "any", 1, 15, 50, "not priced here", "1 week", "S3", "N")
assume(B, 8, "purchased", "Latching emergency stop and relay removing the motor supply", "class", "-", "any", 1, 25, 80,
       "not priced here", "1 week", "S3", "N", notes="DEC-099 proposed")
seen(B, 9, "purchased", "12 V 60 W supply for the motors", "Mean Well", "GST60A12-P1J", "DigiKey", "product 7703712", 1, 19.40,
     "USD", DK + "result?keywords=GST60A12-P1J", "in stock (Normally Stocking)", "1-5 days", "AMF-308", "S3", "N")
seen(B, 10, "purchased", "Controller board Teensy 4.1 (five-bar current and position loops; logs the DAQ sync pulse)", "PJRC",
     "Teensy 4.1", "SparkFun", "DEV-16771", 1, 31.50, "USD", "https://www.sparkfun.com/teensy-4-1.html", "In stock",
     "1-5 days", "AMF-220", "S3", "N")
assume(B, 11, "purchased", "Pen lift for the dummy pen: micro servo (first build; a voice coil if the 0.5 s lift is too slow)",
       "class", "-", "any", 1, 8, 25, "not priced here", "1 week", "S3", "N")
assume(B, 12, "purchased", "Hand-simulant springs 200 and 500 N/m on a linear guide", "class", "-", "any", 1, 20, 80,
       "not priced here", "1 week", "S3", "N")
assume(B, 13, "fabricated", "Desk reaction base 170 x 165 x 5 mm (motor and bearing bores; base spacing 50.00 mm)", "-",
       "desk_reaction_base", "machine shop", 1, 80, 300, "one-off", "1-3 weeks", "S3", "N", who="shop",
       fab="results/improvement/mechanics/grounded_fivebar.step (desk_reaction_base)", material="6061-T6 plate",
       process="waterjet + CNC finishing", tol="bores +-0.02 mm; base spacing 50.00 +-0.02 mm")
assume(B, 14, "fabricated", "Output bearing supports (x2)", "-", "output_bearing_support_0/1", "machine shop", 1, 60, 200,
       "one-off", "1-3 weeks", "S3", "N", who="shop",
       fab="results/improvement/mechanics/grounded_fivebar.step (output_bearing_support_0, _1)", material="6061-T6",
       process="lathe", tol="bearing bores H7; coaxial 0.01 mm")
assume(B, 15, "fabricated", "Capstans: output R18 mm (x2) and motor R3 mm (x2), 6:1, helical cable groove", "-",
       "output_capstan_0/1, motor_capstan_0/1", "machine shop", 1, 80, 300, "one-off", "1-3 weeks", "S3", "N", who="shop",
       fab="results/improvement/mechanics/grounded_fivebar.step (output_capstan_*, motor_capstan_*)",
       material="6061-T6 (output); brass (motor, 2 mm bore)", process="CNC turning", tol="groove pitch +-0.02 mm",
       notes="a printed first try is possible; cable routing and tensioner are unresolved in the CAD")
assume(B, 16, "fabricated", "Links: proximal 60 mm (x2) and distal 90 mm (x2), 7 x 3 mm", "-",
       "proximal_link_0/1, distal_link_0/1", "machine shop", 1, 60, 250, "one-off", "1-3 weeks", "S3", "N", who="shop",
       fab="results/improvement/mechanics/grounded_fivebar.step (proximal_link_*, distal_link_*)",
       material="6061-T6 or CFRP plate", process="waterjet or CNC", tol="pin centres +-0.02 mm; bearing seats H7")
assume(B, 17, "fabricated", "Pen holder for a 24 mm dummy pen with a breakaway magnetic coupling (release 0.5-0.8 N) and lift guide; dummy pen with refill",
       "-", "24mm_pen_holder_keepout (PROPOSED DESIGN)", "in-house", 1, 30, 120, "filament, magnets, brass", "1-2 weeks",
       "S3", "N", fab="results/improvement/mechanics/grounded_fivebar.step (24mm_pen_holder_keepout)",
       material="PETG/resin; N52 discs; brass ballast", process="FDM/SLA", tol="+-0.1 mm")
assume(B, 18, "fabricated", "Guards over the capstans and the link sweep", "-", "PROPOSED DESIGN", "in-house", 1, 20, 60,
       "acrylic", "1 week", "S3", "N", material="acrylic", process="laser cut", tol="+-0.3 mm")

# ------------------------------------------------------------------------------------------------ B4 R10 page sensing
B = "B4"
assume(B, 1, "purchased", "Page-sensor candidate PAA5100JE breakout (15-35 mm)", "Pimoroni", "PIM573",
       "shop.pimoroni.com", 1, 20, 35, "'Pre-order', no price displayed (2026-09-30)", "unknown (pre-order)", "S4", "N",
       ledger="OPT-90")
seen(B, 2, "purchased", "Page-sensor candidate PMW3360 breakout with focusing lens", "Keycapsss", "KC10125 (PMW3360DM-T2QU)",
     "keycapsss.com", "KC10125", 2, 29.90, "EUR",
     "https://keycapsss.com/keyboard-parts/parts/164/kycs-pmw3360-breakout-board-for-pixart-pmw3360-optical-mouse-sensor",
     "'Currently out of stock'", "unknown", "OPT-100", "S4", "N", notes="EUR 29.90 incl. VAT (25.13 excl.)")
assume(B, 3, "purchased", "Rev K's die class: PMW3610DM-SUDU with lens on a small assembled breakout", "PixArt",
       "PMW3610DM-SUDU", "JLCPCB assembly (C42442560, 'Extended' part)", 3, 35, 145,
       "die and lens price not displayed; board assembly not quoted", "2-6 weeks (ASSUMPTION)", "S4", "N",
       who="supplier", ledger="OPT-101; OPT-61")
assume(B, 4, "purchased", "Fallback: a commercial mouse with a known sensor, board harvested", "class", "-", "any", 1, 20, 80,
       "not priced here", "1 week", "S4", "N")
assume(B, 5, "instrument", "Global-shutter camera OV9281 UVC with external trigger (truth at 100 fps)", "Arducam", "B0332",
       "arducam.com / resellers", 1, 45, 80, "vendor and reseller pages returned HTTP 403 (2026-09-30)", "1-2 weeks", "S4",
       "N", ledger="OPT-88")
assume(B, 6, "purchased", "LED strobe: high-power LED and logic MOSFET driver", "class", "-", "any", 1, 10, 30,
       "not priced here", "1 week", "S4", "N")
assume(B, 7, "instrument", "Chrome-on-glass dot-grid distortion target", "class", "-", "optics retailer", 1, 150, 600,
       "not priced here", "1-3 weeks", "S4", "N")
assume(B, 8, "instrument", "Z micrometer stage for fine lens height (1.5-4.5 mm, 10 um)", "class", "-", "optics retailer", 1,
       100, 600, "not priced here", "1-3 weeks", "S4", "N")
assume(B, 9, "consumable", "5 mm float glass 200 x 150 mm, glossy strip, printed fiducial sheets (absolute anchor for EXP-BB08)",
       "class", "-", "any", 1, 15, 60, "not priced here", "1 week", "S4", "N")
assume(B, 10, "fabricated", "Tilt arc R45, arc carriage, roll ring +-20 deg, head plate", "-",
       "tilt_arc, arc_carriage, roll_ring, head_plate", "in-house (+ shop for the plate)", 1, 30, 200,
       "filament; one aluminium plate", "1-2 weeks", "S4", "N",
       fab="results/rig/cad/rig_pagesense_assembly.step (tilt_arc, arc_carriage, roll_ring, head_plate)",
       material="PETG/PA-CF; 6061 plate", process="FDM; CNC plate", tol="+-0.1 mm; roll and tilt verified with the inclinometer")
assume(B, 11, "fabricated", "Mode A sensor sled 14 x 12 x 3 mm and Mode B mock nose", "-", "sled; mock_nose",
       "in-house or online SLA", 1, 20, 80, "resin prints", "1-2 weeks", "S4", "N",
       fab="results/rig/cad/rig_pagesense_sled_assembly.step; results/rig/cad/rig_pagesense_assembly.step (mock_nose)",
       material="SLA resin", process="SLA print", tol="+-0.05 mm")
assume(B, 12, "fabricated", "Latency step flexure: parallel-leaf stage for 50 um steps (<= 0.5 ms rise), driven by R9's LVCM-013 voice coil",
       "-", "PROPOSED DESIGN (no CAD)", "in-house + shop", 1, 50, 200, "leaves and a small block", "1-2 weeks", "S4", "N",
       who="shop", material="spring steel leaves; 6061", process="shear/etch leaves; CNC block", tol="+-0.02 mm",
       notes="EXP-T05 names R13's stage, which is not in this build; open item")

BOM_FILES = {"B0": "bom_B0_daq1.csv", "B1": "bom_B1_r9_g1.csv", "B2": "bom_B2_g2_coupons.csv",
             "B3": "bom_B3_fivebar.csv", "B4": "bom_B4_r10.csv"}
BUILD_NAMES = {"B0": "DAQ-1 (shared data acquisition, one clock)", "B1": "R9 contact and ink rig (G1)",
               "B2": "G2 coupons (force constant, wires, ball guides, anchor, counter-face bench)",
               "B3": "Grounded five-bar demonstrator", "B4": "R10 page-sensing rig"}

STAGES = [
    {"stage": "S0", "weeks": "0-2", "what": "Pre-register EXP-T01/T02/BB01/BB02 (bench_protocols.md s0.2); order every long-lead item; DAQ-1 bring-up (EXP-BB01); printer kit assembly; MVP R9 parts",
     "lead_time_drivers": "K3D40 and LSB200 quotes (ASSUMPTION 2-6 weeks); OPA548T back-ordered to 30-Nov-2026 (DigiKey); VPG shunt 12-Oct-2026",
     "skills": "hobbyist/small team (soldering, 3-D printing, firmware upload); shop for the cartridge and bed adapter",
     "decides": "DEC-058's one clock is real (EXP-BB01)"},
    {"stage": "S1", "weeks": "1-4", "what": "R9 G1 runs on the minimum viable build: EXP-BB02 frame qualification and calibrations; EXP-T02 minimum ink force (dead weights first); EXP-T01 friction and side load (nominal pair, reduced grid); EXP-BB09 contact timing. Bought in S1: the standard upgrades (+-10 N plate, 250 g axial cell, voice coil, 2 x LM13, OPA548, CNC arc) for AC-B01-20's 0.2-2.0 N envelope, EXP-T02's ramps and modulation, and per-sample speed",
     "lead_time_drivers": "K3D40 +-2 N and LSB200 100 g arrival; the +-10 N plate, 250 g cell, voice coil and LM13 only for the standard build",
     "skills": "small team; scanning and blind coding", "decides": "F_c,min per refill and paper (DEC-050's 0.3 N line); friction map; the static side load per newton (study B); DEC-058's falsifier"},
    {"stage": "S2", "weeks": "3-8", "what": "G2 coupons: EXP-T07/K22 force maps (stock magnets); EXP-K21 and EXP-BB04 wires (fatigue 3-8 days per batch); EXP-K20 and EXP-BB05 guides; EXP-BB03 anchor; EXP-J17 (c) counter-face bench on R9's frame",
     "lead_time_drivers": "coil winding (3-6 weeks), lapped 440C races (3-6 weeks), precision etching (2-4 weeks), CuBe wire (about 2 weeks), K3D40 +-10 N",
     "skills": "shop (races, clamps, stator block, fatigue shuttle); suppliers (coils, etching, wire, magnets); skilled hobbyist (soldering 0.10 mm wire under a microscope)",
     "decides": "DEC-062/063 ('Build Rev K's nib' gate of prototype_stages.md s0); DEC-072 by DEC-096's rule; DEC-050 via J17 (c)"},
    {"stage": "S2b", "weeks": "8-12", "what": "Custom-magnet coupons if AC-T07-02 passes on stock magnets", "lead_time_drivers": "custom magnets 4-8 weeks (ASSUMPTION)",
     "skills": "supplier", "decides": "absolute K_m of the chosen geometry"},
    {"stage": "S3", "weeks": "6-12", "what": "Grounded five-bar: build, EXP-BB06 qualification, EXP-BB07 accepted-word replay with a passive pen against spring hands",
     "lead_time_drivers": "Faulhaber motors about 1 week (DigiKey marketplace); CNC parts 1-3 weeks",
     "skills": "shop for base, supports, capstans and links; small team for firmware (current loops) and assembly",
     "decides": "DEC-071's grounded route with measured stiffness, force and ink; DEC-099"},
    {"stage": "S4", "weeks": "6-12", "what": "R10 on R9's frame: EXP-T04/T05 with two or three sensor candidates; EXP-BB08 page anchoring through lift and occlusion",
     "lead_time_drivers": "page-sensor boards (PAA5100JE pre-order; PMW3360 breakout out of stock; PMW3610 not at the big distributors)",
     "skills": "small team; SLA prints", "decides": "sensing build gate; die and optics (DEC-062's REQ-BNIB-017); DEC-059; DEC-065; DEC-070"},
]


def _whole_usd(x: float) -> int:
    return int(Decimal(repr(round(x, 6))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def write_boms():
    for b, fn in BOM_FILES.items():
        rows = [r for r in ROWS if r["build"] == b]
        for r in rows:
            # line totals in whole dollars (half up), so every total in the plan is an exact sum of these columns
            r["line_usd_low"] = _whole_usd(r["unit_usd_low"] * r["qty"])
            r["line_usd_high"] = _whole_usd(r["unit_usd_high"] * r["qty"])
        with open(OUT / fn, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=BOM_COLS)
            w.writeheader()
            w.writerows(rows)


def totals():
    out = {"currency": "USD", "eur_rate_assumption": EUR, "note": "sums of line ranges; MANUFACTURER lines enter at the seen "
           "price (EUR lines at the rate range); ASSUMPTION lines at their range; shipping, tax, duty and labour excluded",
           "by_build": {}, "by_stage": {}, "mvp": {}}
    for b in BOM_FILES:
        rs = [r for r in ROWS if r["build"] == b and r["stage"] != "S2b"]
        core = [r for r in rs if r["optional_if_lab_has_it"] == "N"]
        opt = [r for r in rs if r["optional_if_lab_has_it"] == "Y"]
        out["by_build"][b] = {"name": BUILD_NAMES[b],
                              "core_low": round(sum(r["line_usd_low"] for r in core)),
                              "core_high": round(sum(r["line_usd_high"] for r in core)),
                              "instruments_if_lab_lacks_low": round(sum(r["line_usd_low"] for r in opt)),
                              "instruments_if_lab_lacks_high": round(sum(r["line_usd_high"] for r in opt)),
                              "share_of_core_priced_as_MANUFACTURER": round(
                                  sum(r["line_usd_low"] for r in core if r["price_label"] == "MANUFACTURER") /
                                  max(1e-9, sum(r["line_usd_low"] for r in core)), 3),
                              "n_lines": len(rs)}
    for s in ("S0", "S1", "S2", "S2b", "S3", "S4"):
        rs = [r for r in ROWS if r["stage"] == s]
        core = [r for r in rs if r["optional_if_lab_has_it"] == "N"]
        opt = [r for r in rs if r["optional_if_lab_has_it"] == "Y"]
        c_lo, c_hi = round(sum(r["line_usd_low"] for r in core)), round(sum(r["line_usd_high"] for r in core))
        # the with-instruments figure is the sum of the two rounded parts, so the printed tables add up exactly
        out["by_stage"][s] = {"core_low": c_lo, "core_high": c_hi,
                              "with_instruments_low": c_lo + round(sum(r["line_usd_low"] for r in opt)),
                              "with_instruments_high": c_hi + round(sum(r["line_usd_high"] for r in opt))}
    mvp = [r for r in ROWS if r["mvp"] == "Y"]
    mvp_core = [r for r in mvp if r["optional_if_lab_has_it"] == "N"]
    out["mvp"] = {"what": "DAQ-1 + R9 minimum viable G1 build (dead-weight F_c, no encoders, printed arc; K3D40 +-2 N and LSB200 100 g)",
                  "core_low": round(sum(r["line_usd_low"] for r in mvp_core)),
                  "core_high": round(sum(r["line_usd_high"] for r in mvp_core)),
                  "with_hand_tools_low": round(sum(r["line_usd_low"] for r in mvp)),
                  "with_hand_tools_high": round(sum(r["line_usd_high"] for r in mvp)),
                  "manufacturer_priced_low": round(sum(r["line_usd_low"] for r in mvp_core if r["price_label"] == "MANUFACTURER")),
                  "largest_assumption_lines": sorted(
                      [(r["item"][:60], r["line_usd_low"], r["line_usd_high"]) for r in mvp_core if r["price_label"] == "ASSUMPTION"],
                      key=lambda x: -x[2])[:4]}
    allc = [r for r in ROWS if r["stage"] != "S2b" and r["optional_if_lab_has_it"] == "N"]
    out["all_builds_core_low"] = round(sum(r["line_usd_low"] for r in allc))
    out["all_builds_core_high"] = round(sum(r["line_usd_high"] for r in allc))
    allo = [r for r in ROWS if r["stage"] != "S2b" and r["optional_if_lab_has_it"] == "Y"]
    out["all_builds_instruments_low"] = round(sum(r["line_usd_low"] for r in allo))
    out["all_builds_instruments_high"] = round(sum(r["line_usd_high"] for r in allo))
    return out


def write_cost_schedule(tot):
    cols = ["stage", "weeks", "what", "cost_core_usd_low", "cost_core_usd_high", "cost_with_instruments_usd_low",
            "cost_with_instruments_usd_high", "lead_time_drivers", "skills", "decides"]
    with open(OUT / "cost_schedule.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for s in STAGES:
            t = tot["by_stage"][s["stage"]]
            w.writerow({"stage": s["stage"], "weeks": s["weeks"], "what": s["what"], "cost_core_usd_low": t["core_low"],
                        "cost_core_usd_high": t["core_high"], "cost_with_instruments_usd_low": t["with_instruments_low"],
                        "cost_with_instruments_usd_high": t["with_instruments_high"],
                        "lead_time_drivers": s["lead_time_drivers"], "skills": s["skills"], "decides": s["decides"]})
    (OUT / "cost_totals.json").write_text(json.dumps(tot, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ test-to-decision map
MAP_COLS = ["build", "experiment", "criteria", "pass_fail_line", "decision_fed", "gate", "if_it_fails"]
MAP = [
    ("B0", "EXP-BB01 (proposed)", "AC-BB01-01...05", "0 CRC errors and 0 missing frames in 10 min at 8 kSPS; ADC noise <= 2.4 uV RMS at gain 128; sync residual <= 50 us; 0 encoder counts lost; current step <= 2 ms", "DEC-058 (one clock for every instrument)", "order 0 of prototype_stages.md s0 (all gates)", "fix firmware or wiring before any record; a device whose clock fit misses 50 us is logged on DAQ-1 directly"),
    ("B1", "EXP-BB02 (proposed)", "AC-BB02-01", "plate stack first mode >= 100 Hz (tap test)", "DEC-058 (revisit trigger)", "G1", "stiffer bed adapter, lighter platen or the +-10 N plate; persistent: DEC-058 revisited"),
    ("B1", "EXP-BB02 (proposed)", "AC-BB02-02...04", ">= 95 % of the steady window within +-20 % of the speed; plate residual <= 0.2 % FS; guide stiffness 17.9-33.3 N/m", "validity of EXP-T01/T02", "G1", "lower accelerations or head mass; recalibrate at the angle; re-cut the leaves"),
    ("B1", "EXP-T02", "AC-T02-01", "F_c,min <= 0.3 N for Rev K's refill at every tilt, speed and paper", "DEC-050 (F_s set point; revisit above 0.3 N), DEC-062", "G1", "another refill; above 0.3 N DEC-050's revisit (B1's power passes 30 mW)"),
    ("B1", "EXP-T02", "AC-T02-02; AC-T02-04", "U(F_c,min) <= 12 mN; report per tip type and paper", "REQ-BNIB-014 (F_s frozen only after G1)", "G1", "more lines per cell or guarded acceptance"),
    ("B1", "EXP-T02", "AC-T02-03", "gaps <= 1 % under +-0.03 N modulation at 3-15 Hz (needs the voice coil)", "REQ-MECH-005", "G1", "spring rate and bore friction of the ink-force element"),
    ("B1", "EXP-T01", "AC-T01-01; AC-T01-02", "closure <= max(3 mN, 3 % F_c); U(N) <= 5 mN", "validity of every G1 verdict (DEC-058)", "G1", "recalibrate in situ at the angle; DEC-058 revisited if closure fails persistently"),
    ("B1", "EXP-T01", "AC-T01-04; AC-T01-05; AC-B01-03", "mu_drag 0.09-0.40; |mu_cross|/mu_drag <= 0.2; P-6 within +-15 % in >= 90 % of strokes", "sim2 friction and config/nib.yaml (DEC-050 via EXP-B21); study B's balance mechanism; DEC-066 (pre-sliding stiffness sets the stuck mode)", "G1, G-B", "widen the simulator's friction range and re-run; add a direction-dependent balance term; replace the contact model"),
    ("B1", "EXP-T01 (EXP-B01 re-specified)", "AC-B01-20", "the 0.2-2.0 N normal-force envelope at 35-75 deg covered (100 % of grid points)", "REQ-ENV-002; REQ-ACT-001 revision; DEC-008", "G1", "coverage, not a load pass: it needs S1's 250 g cell and +-10 N plate (the first build reaches about 0.5 N at 75 deg in every direction, bench_calcs.json); EXP-B01's 4 N level needs a larger cell (open item of prototype_stages.md s0)"),
    ("B1", "EXP-BB09 (proposed)", "AC-BB09-01...03", "contact-channel delay <= 5 ms (99th percentile); <= 0.1 false events per minute; lift command to ink stop <= 50 ms", "DEC-070 (contact model), DEC-071 (lift for accepted writing)", "sensing and contact (report s9 step 2)", "change threshold and filtering of the contact channel; faster lift actuator; re-run the supervisor studies with the measured delay"),
    ("B2", "EXP-J17 part (c)", "AC-J17-04", "residual side load <= 10 % mean and <= 25 % at the 95th percentile of F_s cot(theta)", "DEC-050, DEC-064, and DEC-072 through DEC-096's rule", "G1 (prototype_stages.md s0 lists EXP-J17 under G1); 'Build the Rev K pen' (AC-J17-04)", "DEC-050: the clutched bias b', then the unbalanced nib f"),
    ("B2", "EXP-J17 part (c)", "AC-J17-05; AC-J17-06; AC-J17-07", "pen-up residual <= 10 % within 20 ms and touchdown travel <= 1.0/0.6 mm; guide friction <= 0.01; ink force within +-20 % of the set value", "DEC-050, DEC-064 (float brake), REQ-BNIB-016, REQ-BNIB-008", "G1 (EXP-J17)", "float brake; a rolling refill guide; spring set point"),
    ("B2", "EXP-T07 (with study K's EXP-K22)", "AC-T07-01; AC-T07-05", "K_m >= 0.7 x model at every node; Rev K coil >= 0.7 x 0.334 (x) and 0.7 x 0.272 (y) N/sqrt(W)", "DEC-050 (pole size), DEC-062 (buildable coil)", "G2; 'Build Rev K's nib' (prototype_stages.md s0)", "larger poles (24 mm bore is the limit); DEC-062 revisited"),
    ("B2", "EXP-T07", "AC-T07-02; AC-T07-03; AC-T07-04", ">= 90 % of nodes within +-10 % of the model; ripple <= 15 % (predicted to FAIL); force and back-EMF routes agree", "trust in the magnetic model (study N's search); firmware force map", "G2", "fix the model (iron images) before any custom magnet order; the firmware uses the measured map"),
    ("B2", "EXP-K21", "AC-K21-01...04", "<= 0.3 ohm per wire; no failure in 43.2 M cycles at 0.1 A; preload <= 0.05 N; Goodman >= 1.5", "DEC-063 (C17200 wire leads)", "G2; 'Build Rev K's nib'", "0.08 mm wire (fails 0.3 ohm) or a beryllium-free alloy (DEC-063 revisited); rework the anchor before fatigue counts"),
    ("B2", "EXP-BB04 (proposed)", "AC-BB04-01...05", "lead <= 0.3 ohm; no failure in 43.2 M cycles at the 1.7 mm stop; Goodman >= 1.5; wire heating within +-25 % of the model; drive <= 0.2 x first mode", "DEC-072 through DEC-096 (the reach candidate)", "G2", "the reach candidate is dropped; the 1.059 mm candidate stays"),
    ("B2", "EXP-K20", "AC-K20-01...03", "rolling friction <= 5 mN; tilt <= 0.2 mrad and no wire compressed beyond 0.5 x buckling; no race marks after ten 1 m drops, friction within +-20 %", "DEC-063 (the ball guide), REQ-RVK-003", "G2; 'Build Rev K's nib'", "lower preload or another guide (DEC-063 revisited); stiffer guide; sprung races and stops redesigned"),
    ("B2", "EXP-BB05 (proposed)", "AC-BB05-01...03", "reach guide drag 5.6-10.5 mN at 4 N; a preload with tilt <= 0.2 mrad and drag <= 5 mN; no marks on the bare Ti face", "DEC-063 (preload), DEC-072 through DEC-096", "G2", "hardened race inserts on the flange; a different preload or guide topology (study N)"),
    ("B2", "EXP-BB03 (proposed)", "AC-BB03-01...03", "beam stiffness within +-15 % of 4 E w t^3/L^3; anchor with interconnect 80-120 N/m; assembly tension <= 5 mN", "DEC-072 (the soft anchor replaces Rev K's 10,000 N/m), DEC-063", "G2", "re-etch with the beam width set from the measured foil; a softer interconnect; shim the hub"),
    ("B3", "EXP-BB06 (proposed)", "AC-BB06-01...04", "endpoint <= 50 um RMS against camera truth; continuous force >= 0.40 N; stiffness >= 4 N/mm; force cap <= 0.4 N and coupling release 0.5-0.8 N (guarded)", "DEC-071 (grounded route), DEC-099", "none yet (a G-S-type gate for the five-bar is an open item)", "16-bit encoders or a camera-referenced loop; larger motors or ratio; stiffer links or bearings; fix the cap before any other test"),
    ("B3", "EXP-BB07 (proposed)", "AC-BB07-01...03", ">= 18 of 20 accepted suffixes meet the grounded gate without a spring hand; <= 0.5 mm ink after a refusal with 200/500 N/m springs; acceleration and jerk reported", "DEC-071", "none yet", "the moving-paper platen (study P) as the alternative; a faster, positively sensed lift"),
    ("B4", "EXP-T04 (with EXP-S01, J04, J10, N07, B32)", "AC-T04-01; AC-T04-03; AC-T04-05; AC-S01-02", ">= 1 kHz and <= 10 um RMS at 35-75 deg, +-20 deg roll, six papers; truth U <= 2.5 um per window; dropouts <= 1 % and none > 300 ms; <= 5 um RMS per sample", "sensing build gate; DEC-005/DEC-036 triggers; the die and optics (DEC-062)", "sensing build gate", "another die or optics; external truth stays in the loop"),
    ("B4", "EXP-T04", "AC-T04-07; AC-T04-08", "lift cut-off >= 2 mm (predicted FAIL with a mouse-class die); >= +-20 deg roll beside the heel pod (predicted FAIL)", "REQ-BNIB-017 and DEC-062; 'Build the Rev K pen'; DEC-065", "sensing build gate; 'Build the Rev K pen'", "other die/optics or a changed REQ-BNIB-017; the heel stays a bench module"),
    ("B4", "EXP-T04 (EXP-J10's addition)", "AC-J10-04", "accumulated drift <= 0.1 mm per 2 s; window error median <= 24 um and mean <= 68 um (DeltaPen's metric)", "REQ-RVJ-C05, DEC-059, DEC-049", "sensing build gate", "DEC-049 revisited; sim2j re-run with the measured page model (its owner)"),
    ("B4", "EXP-T05", "AC-T05-01; AC-T05-02", "latency <= 2 ms (99th percentile); step rise <= 0.5 ms", "the estimator's horizon; REQ-RVJ-N06", "sensing build gate", "a faster sensor mode; a stiffer step source"),
    ("B4", "EXP-BB08 (proposed)", "AC-BB08-01...03", "0 silent recoveries of the absolute anchor in >= 100 outages; re-anchored position <= 0.1 mm (95th percentile); lost motion reported", "DEC-070 (page model v2), DEC-071 (registration for accepted writing), REQ-CAP-003", "sensing build gate", "no accepted writing across an outage without a verified anchor; another anchor method (coded paper, camera)"),
]


def write_map():
    with open(OUT / "test_decision_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(MAP_COLS)
        w.writerows(MAP)


# ------------------------------------------------------------------------------------------------ proposed rows
EXPS = [
    ("EXP-BB01", "all (order 0)", "DAQ-1", "DAQ-1 bring-up and time-base qualification",
     "frame integrity at 8 kSPS; ADC noise with inputs shorted; sync-pulse clock fit of a second device; encoder loop-back; current-output step",
     "whether every later record can share one clock (DEC-058)", "REQ-DATA-001",
     "none: docs/measurement_rig.md s1.3 lists bring-up steps without an experiment id or criteria"),
    ("EXP-BB02", "G1", "R9", "R9 frame qualification: plate mode, motion quality, in-situ calibrations",
     "tap-test first mode of the plate stack; head speed stability with the 190 g head; plate matrix residuals; guide stiffness",
     "DEC-058's falsifier (plate mode below 100 Hz); validity of EXP-T01/T02", "REQ-ENV-002",
     "none: DEC-058 names the tap test as its falsifier but no criterion judges it"),
    ("EXP-BB03", "G2", "R12 bench + precision balance", "Axially soft wire anchor coupon (the pass's floating anchor)",
     "axial stiffness of the etched 4-beam anchor alone and with its interconnect; assembly tension of the wires",
     "DEC-072 (the reach candidate's fatigue margin rests on 80-120 N/m and <= 5 mN)", "REQ-BNIB-007",
     "none: EXP-K21 measures preload on Rev K's diaphragm, not the anchor's stiffness"),
    ("EXP-BB04", "G2", "R8-type fatigue shuttle + DAQ-1", "The reach candidate's eight 34 mm C17200 wires at the 1.7 mm stop",
     "lead resistance; fatigue at the 1.7 mm stop with 0.1 A per wire; Goodman factor with measured Kt and tension; Joule heating above the clamps; the coupon's first mode",
     "DEC-072 (keep or drop the 1.5 mm candidate)", "REQ-RVK-004; REQ-BNIB-007",
     "EXP-K21's criteria fix 26.8 mm wires at Rev K's stop; the reach candidate's length, stop, count and anchor differ"),
    ("EXP-BB05", "G2", "R12 stage + 10 g cell + laser lever", "Ball-guide drag and tilt against preload, both guides",
     "drag (forward/return half-difference) and carrier tilt at 1-4 N preload under the 35 deg couple, for Rev K's and the reach candidate's guides; marks on a bare Ti flange face",
     "the preload that meets both REQ-RVK-003's tilt and DEC-063's 5 mN drag; the drag entering the duty re-run (DEC-096)",
     "REQ-RVK-003", "EXP-K20 tests Rev K's guide at one preload; the pass predicts 8.07 mN at 4 N, above K20's 5 mN line"),
    ("EXP-BB06", "none yet (grounded route)", "five-bar + K3D40 +-10 N + camera", "Five-bar qualification: kinematics, force, stiffness, force cap",
     "endpoint from output encoders against camera truth; continuous force disk; stiffness and lost motion at the holder; force cap and breakaway release",
     "whether the rigid, ideal model of the grounded study describes the hardware (DEC-071); the safety features of DEC-099", "",
     "none: no experiment tests the five-bar"),
    ("EXP-BB07", "none yet (grounded route)", "five-bar + passive pen + R3 scans", "Accepted-word replay on paper with a passive pen against spring hands",
     "the 20 accepted 'se' suffixes written by the five-bar: grounded-gate completions without a spring hand; ink after refusal with 200/500 N/m springs; acceleration and jerk",
     "DEC-071 (whole letters need a grounded stage); lift and refusal design", "",
     "none: the grounded results are SIM only (results/improvement/mechanics/grounded_batch.json)"),
    ("EXP-BB08", "sensing build gate", "R10 + camera truth", "Page anchoring through lift and occlusion",
     "absolute-anchor validity flag through lifts, occlusions and glossy strips; absolute error after re-anchoring; lost relative motion",
     "whether accepted writing can resume after an outage (DEC-070, DEC-071)", "REQ-RVJ-C05; REQ-CAP-003",
     "EXP-T04 judges the lift cut-off height and dropouts, not the absolute re-anchoring"),
    ("EXP-BB09", "sensing and contact", "R9", "Contact-channel delay, false contacts and lift timing on R9",
     "delay of the pen-side contact decision against the plate's normal force; false contact/lift rate; command-to-ink-stop time of a voice-coil lift",
     "the delayed contact channel of DEC-070's causal models; the lift a refusal needs (DEC-071)", "REQ-CTRL-003",
     "none: AC-B05-10 judges axial-force noise, not the contact decision's delay"),
]

CRIT = [
    # id, req, exp, metric, threshold, direction, basis, status, gated
    ("AC-BB01-01", "", "EXP-BB01", "Ten minutes at 8 kSPS with every channel of the rig enabled: CRC errors and missing frames in session.json stats (rig.logger)", "both met (0 CRC errors; 0 missing frames)", "pass/fail", "docs/measurement_rig.md s1.3 bring-up step 3; SIM: the parser rejects every corrupted frame (rig.selftest)", "derived", "every rig verdict (one clock)"),
    ("AC-BB01-02", "", "EXP-BB01", "Input-referred noise of each ADS131M08 channel at PGA 128, inputs shorted, 4 kSPS, RMS over 60 s", "2.4 uV", "<=", "2 x the manufacturer's 1.20 uV RMS at 4 kSPS and gain 128 (MFR AMF-221/222, Table 7-1); the factor 2 for layout and excitation noise is PROPOSED", "hypothesis", "the force-channel budgets of rig.uncertainty"),
    ("AC-BB01-03", "", "EXP-BB01", "Mapping of a device clock onto DAQ-1's by the coded sync pulse (loop-back sync out to DUT in, then the five-bar controller): largest residual of rig.sync.fit_clock over >= 10 min", "50 us", "<=", "bench_protocols.md s0.4 alignment requirement; SIM 6 us with 20 ppm drift (rig.selftest)", "derived", "any record that combines DAQ-1 with another clock"),
    ("AC-BB01-04", "", "EXP-BB01", "Quadrature loop-back from a signal generator into each encoder input at 0.5 M counts/s (LM13 13B at 100 mm/s is about 0.41 M counts/s): counts lost over 10^6 counts", "0", "=", "PROPOSED; LM13 13B resolution about 0.244 um (MFR OPT-89)", "hypothesis", "encoder truth of R9, R10 and the five-bar"),
    ("AC-BB01-05", "", "EXP-BB01", "Current output chain (12-bit PWM, RC filter, current amplifier) into R9's voice coil: 10-90 % step time and DC error at 0.1-0.5 A (both)", "both met (<= 2 ms; <= 1 % of full scale)", "pass/fail", "PROPOSED: F_c ramps of EXP-T02 and the reversal steps of EXP-T07 need ms settling", "hypothesis", "EXP-T02 ramp lines; EXP-T07 current steps"),
    ("AC-BB02-01", "", "EXP-BB02", "First mode of the plate stack on the bed (K3D40, platen, underlay, paper) by tap test, lowest over the three underlays", "100 Hz", ">=", "DEC-058's falsifier (a plate mode below 100 Hz); CALC 151 Hz (+-2 N) and 338 Hz (+-10 N) without the sensor's own top mass (results/rig/cad/rig_contact_summary.json)", "derived", "DEC-058; validity of EXP-T01's ripple and EXP-T03"),
    ("AC-BB02-02", "", "EXP-BB02", "Head speed during EXP-T01 strokes with the 190 g head at 3-100 mm/s: fraction of each steady window within +-20 % of its median speed (rig.contact.analyse_stroke's rule)", "95 %", ">=", "the analysis's steady-window rule; the CORE One page gives no payload or speed accuracy (MFR AMF-231); 95 % PROPOSED", "hypothesis", "EXP-T01 validity; the printer frame as motion source (DEC-058)"),
    ("AC-BB02-03", "", "EXP-BB02", "In-situ plate calibration at the test angle (rig.calib.fit_plate): residual RMS per axis over the calibration loads, as a share of full scale", "0.2 %", "<=", "relative linearity error 0.2 % FS (MFR AMF-224)", "hypothesis", "AC-T01-02's uncertainty budget"),
    ("AC-BB02-04", "", "EXP-BB02", "Axial stiffness of the leaf-guided cartridge fitted with the refill off the paper (rig.calib.fit_guide_stiffness)", "17.9-33.3 N/m", "within", "CALC 25.6 N/m +-30 % (results/rig/cad/rig_contact_summary.json; E 200 GPa ASSUMPTION)", "hypothesis", "the guide-force correction of F_c in EXP-T01/T02"),
    ("AC-BB03-01", "", "EXP-BB03", "Axial stiffness of the etched 301 four-beam anchor alone (hub pushed 0-100 um in 10 um steps, force by a >= 1 mg balance), as a ratio to 4 E w t^3 / L^3 with the coupon's measured thickness and beam width", "0.85-1.15", "within", "CALC 76.6 N/m at 35 um x 0.5 mm x 6 mm (results/improvement/mechanics/cad_summary.json; E 193 GPa ASSUMPTION); a 1 um thickness error moves it 8.6 % (bench_calcs.json); 15 % PROPOSED", "hypothesis", "the anchor model of revk/feasibility.py (wire tension at the stop)"),
    ("AC-BB03-02", "", "EXP-BB03", "Total axial stiffness of the anchor with its flexible interconnect and terminations as assembled", "80-120 N/m", "within", "the pass's target range (cad_summary.json: nominal 100 N/m including about 23.4 N/m for the cable); the Goodman factor 1.70 was computed with 120 N/m at the worst corner", "derived", "DEC-072 (the reach candidate's wire fatigue margin)"),
    ("AC-BB03-03", "REQ-BNIB-007", "EXP-BB03", "Axial tension on the eight wires after assembly: the anchor hub's offset from its free position (microscope) times the measured stiffness", "5 mN", "<=", "assembly_tension_max 0.005 N in the reach candidate's fatigue screen (results/improvement/mechanics/mechanics_study.json)", "derived", "DEC-072; EXP-BB04's Goodman factor"),
    ("AC-BB04-01", "REQ-RVK-004", "EXP-BB04", "Resistance of each lead of the reach candidate (two 0.10 mm x 34 mm C17200 wires in parallel, clamp to clamp, 4-wire, 20 C), before and after the cycling of AC-BB04-02", "0.3 ohm", "<=", "REQ-RVK-004; CALC 0.339 ohm per wire, 0.17 ohm per lead (mechanics_study.json, 22 % IACS as MFR AMF-251)", "requirement", "DEC-072"),
    ("AC-BB04-02", "REQ-BNIB-007", "EXP-BB04", "Cycles at the 1.7 mm stop with the anchor at 80-120 N/m, each wire carrying 0.1 A, at least 3 coupons per clamp type, drive at no more than 0.2 x the coupon's measured first mode: an open circuit or a > 2 % resistance step counts as failure", "no failure in 43.2 M cycles", "pass/fail", "REQ-BNIB-007's life and REQ-RVK-004's 0.1 A; CALC Goodman 1.70 at the worst corner (Kt 2.5, 120 N/m, 5 mN)", "derived", "DEC-072 (the reach candidate)"),
    ("AC-BB04-03", "REQ-BNIB-007", "EXP-BB04", "Goodman safety factor at the 1.7 mm stop with the clamp's measured stress concentration and the measured assembly tension", "1.5", ">=", "REQ-BNIB-007; CALC 1.696 at the worst corner (mechanics_study.json)", "requirement", "DEC-072"),
    ("AC-BB04-04", "", "EXP-BB04", "Rise of a wire above its clamps at 0.16 A continuous by 4-wire resistance thermometry (the wire's resistance coefficient calibrated in the printer chamber at 20-50 C), as a ratio to dT0 = I^2 rho L^2 / (8 kappa A^2)", "0.75-1.25", "within", "CALC 45 K at 0.160 A (wire_continuous_rms_current_A in mechanics_study.json; 105 W/mK is Materion's rod value used as an ASSUMPTION for a 0.10 mm wire)", "hypothesis", "the wire-heat limit of the duty screen"),
    ("AC-BB04-05", "", "EXP-BB04", "Validity of every fatigue run on wire coupons (EXP-BB04, K21, B25): drive frequency divided by the first transverse mode measured on that coupon", "0.2", "<=", "CALC: at 200 Hz the clamp stress of a 34 mm wire rises about 90 % over quasi-static, of a 26.8 mm wire 12-33 %; at 0.2 x f1 about 7 % (results/benchbuild/bench_calcs.json); DEC-098 (proposed)", "derived", "validity of AC-BB04-02/03, AC-K21-02/04 and AC-B25-01"),
    ("AC-BB05-01", "", "EXP-BB05", "Rolling drag of the reach candidate's full-ring guide (15.1 mm ball circle, 2 x 6 Si3N4 0.8 mm balls, lapped 440C races) at the 4 N design preload and the 35 deg couple, swept +-1.5 mm at 8 Hz; drag from the forward/return half-difference on a 10 g cell", "5.6-10.5 mN", "within", "CALC 8.07 mN +-30 % (rolling coefficient 0.001 ASSUMPTION; docs/mechanics_improvement_audit.md)", "hypothesis", "DEC-072's duty re-run (DEC-096)"),
    ("AC-BB05-02", "REQ-RVK-003", "EXP-BB05", "For each guide (Rev K's and the reach candidate's), preload stepped 1, 2, 3, 4 N: at the lowest preload whose carrier tilt under the 35 deg couple stays within 0.2 mrad, the drag (both)", "both met (tilt <= 0.2 mrad; drag <= 5 mN)", "pass/fail", "REQ-RVK-003's tilt line; DEC-063's 5 mN trigger (AC-K20-01); the pass calculates 8.07 mN at 4 N", "derived", "DEC-063 (the preload); DEC-072"),
    ("AC-BB05-03", "", "EXP-BB05", "Marks on a bare Ti-6Al-4V flange face after the EXP-K20 drop series, against a flange with 440C race inserts (profilometer)", "none", "pass/fail", "CALC Hertz 2.64 GPa on the flange face (mechanics audit) against Ti-6Al-4V yield 0.91-1.11 GPa (LIT AMF-20): indentation expected (ASSUMPTION)", "hypothesis", "the flange's material (hardened race inserts or not)"),
    ("AC-BB06-01", "", "EXP-BB06", "Endpoint position from the two 14-bit output encoders through forward kinematics (link lengths and encoder offsets fitted on 20 poses) against camera dot-grid truth on 35 other poses over the 60 x 40 mm patch", "50 um RMS", "<=", "PROPOSED: a third of the 150 um position tube of the pass's observer study; CALC quantisation 8 um (bench_calcs.json); SIM 11.6 um RMS in the pipeline check", "hypothesis", "the rigid-link assumption of wholepen/grounded_replay.py; DEC-071"),
    ("AC-BB06-02", "", "EXP-BB06", "Continuous force at a clamped pen holder with both motors at rated current (K3D40 +-10 N), lowest over 8 directions at 9 poses", "0.40 N", ">=", "the controller's 0.4 N cap; CALC minimum 0.480 N over the sampled patch (Faulhaber 2224 U 012 SR sheet; 6:1 and 80 % efficiency ASSUMPTION)", "derived", "DEC-071; EXP-BB07"),
    ("AC-BB06-03", "", "EXP-BB06", "Stiffness of the linkage at the pen holder with both joints servo-held, lowest over directions and poses; lost motion on reversal reported", "4 N/mm", ">=", "PROPOSED: 0.1 mm deflection at the 0.4 N cap, the grounded gate's 0.10 mm RMS ink line; the model assumes rigid links", "hypothesis", "the rigid-link assumption of the grounded replay"),
    ("AC-BB06-04", "", "EXP-BB06", "Force cap and release with the holder blocked, at every pose and command: steady endpoint force under the software cap, and the breakaway force of the pen holder's magnetic coupling (both; guarded acceptance)", "both met (<= 0.4 N; release between 0.5 and 0.8 N)", "pass/fail", "the 0.4 N cap is the pass's ASSUMPTION, not a clinical limit; at rated current the linkage can push up to about 1.06 N at the worst pose and direction while its guaranteed disk is 0.48 N (CALC, bench_calcs.json), so a current limit alone cannot enforce 0.4 N: the coupling is the physical backstop; 0.5-0.8 N PROPOSED (DEC-099)", "derived", "DEC-099; any test of the five-bar with a hand"),
    ("AC-BB07-01", "", "EXP-BB07", "The 20 accepted 'se' suffixes of results/improvement/writing/grounded_accepted written on paper by the five-bar with a passive 24 mm dummy pen, no resisting spring, feedforward plus feedback: suffixes meeting the grounded gate from scans (no refusal or stop hit; >= 98 % requested-ink coverage; <= 0.10 mm RMS during requested ink; <= 0.02 mm ink path in air transfer)", "18", ">=", "SIM 20 of 20 in the rigid, ideal-current-loop model (results/improvement/mechanics/grounded_batch.json); 18 PROPOSED to allow two scan or registration failures", "hypothesis", "DEC-071 (the grounded route for whole words)"),
    ("AC-BB07-02", "", "EXP-BB07", "The same references with 200 and 500 N/m spring hands: ink path laid after the refusal command (scans), largest over the suffixes", "0.5 mm", "<=", "PROPOSED; SIM: 0 of 20 completions and partial erroneous ink during the 200 ms retraction (the pass's unmet interaction target)", "hypothesis", "DEC-071; the lift and refusal design; DEC-099"),
    ("AC-BB07-03", "", "EXP-BB07", "Peak tip acceleration and sampled jerk of every suffix from the output encoders (1 kHz) and the camera, with the fraction within 2 m/s^2 and 300 m/s^3", "reported for every suffix", "pass/fail", "SIM: none of the 20 unloaded suffixes met both limits (grounded_derivative_check.json); the limits are the planner's ASSUMPTIONS", "derived", "the smoothness claim of any grounded writing"),
    ("AC-BB08-01", "", "EXP-BB08", "During lifts beyond the sensor's cut-off, occlusions and glossy strips: outages in which the page estimate keeps an absolute position without re-anchoring (silent recoveries), over >= 100 outages", "0", "=", "the causal page model v2 (DEC-070): lost motion stays lost and the absolute anchor is invalid until restored; the old model recovered 2.02 mm from the hidden truth (docs/integration_improvement_audit.md)", "derived", "DEC-070; the accepted-writing supervisor's anchor check"),
    ("AC-BB08-02", "REQ-RVJ-C05", "EXP-BB08", "Absolute page position after re-anchoring with the method under test (printed fiducials seen by the camera, or coded paper), 95th percentile over >= 100 lifts of 2 mm and 0.5 s with the pen displaced up to 5 mm", "0.1 mm", "<=", "REQ-RVJ-C05's 0.1 mm budget applied to the re-anchored position", "derived", "DEC-071 (page registration for accepted writing); REQ-CAP-003"),
    ("AC-BB08-03", "", "EXP-BB08", "Lost relative motion during each outage, with its duration and cause", "reported for every outage", "pass/fail", "report; SIM example: 2.02 mm lost over 100 invalid reports at 20 mm/s (docs/integration_improvement_audit.md)", "derived", "the supervisor's outage handling"),
    ("AC-BB09-01", "REQ-CTRL-003", "EXP-BB09", "Delay from the plate's normal force crossing 20 mN (truth) to the pen-side contact decision (in-line axial cell; slide Hall), touchdowns and lifts, 99th percentile over >= 200 events at 35, 50 and 75 deg", "5 ms", "<=", "REQ-CTRL-003's 5 ms delay budget applied to the contact channel; the replay studies assumed 20-200 ms lift/lower delays (ai3/run_completion_robustness.py)", "derived", "DEC-070 (the contact model); ink gating by the supervisor"),
    ("AC-BB09-02", "", "EXP-BB09", "False contact or lift decisions per minute of continuous writing on the six papers (plate truth)", "0.1", "<=", "PROPOSED", "hypothesis", "the contact threshold and its hysteresis"),
    ("AC-BB09-03", "", "EXP-BB09", "Command-to-ink-stop time of R9's voice-coil lift (refill retracted 0.5 mm) at 30 mm/s, and ink resumption after the lower command, from scans and the plate", "50 ms", "<=", "PROPOSED; CALC for Rev K's follower lift: ink stops after 43-72 ms (DEC-064); the grounded study's 200 ms retraction left erroneous ink", "hypothesis", "the lift a refusal needs (DEC-071)"),
]

DECS = [
    ("DEC-095", "The first bench build is DAQ-1 plus R9 (G1), ordered in week 1 together with every long-lead item for the G2 coupons, the five-bar and R10. G1 runs in weeks 1-4, EXP-T02's minimum ink force first (dead weights if the voice coil is late), then EXP-T01. No coupon geometry is frozen before G1's F_c,min and side load are known; the first force-constant coupons use stock magnets with predictions regenerated at the as-built size (bench_protocols.md s0.2), and custom magnets are ordered only after AC-T07-02 passes",
     "Coupons or the five-bar first; a 6-axis F/T sensor for G1 (EXP-B01 as first written); custom magnets now",
     "report s9 order; DEC-058; DEC-072 ('the choice waits for measured load and friction'); this plan's lead times (K3D40/LSB200 quotes, coils 3-6 weeks, OPA548T back-ordered to 30-Nov-2026 at DigiKey, AMF-301)",
     "a lead time beyond 6 weeks for the K3D40 or the LSB200 (then the low-cost G1 build of docs/measurement_rig.md s2.9 starts first)"),
    ("DEC-096", "DEC-072's choice is made by re-running the pass's duty screen (python -m revk.improve) with measured inputs: the residual lateral load at the carrier (EXP-J17 (c), 95th percentile over 35-75 deg and roll, plus the moving mass's weight across the axis, CALC 29.5 mN at 35 deg), the K_m map (EXP-T07), the guide drag at the chosen preload (EXP-K20, EXP-BB05) and the anchor stiffness (EXP-BB03). The 1.5 mm candidate is taken only if its re-run worst copper loss stays within the 0.15 W allocation and EXP-BB04 passes. Provisional reading (CALC, interpolation of the pass's own points): 0.15 W is reached at about 34 mN of residual load for the 1.5 mm candidate and about 53 mN for the 1.059 mm candidate; the screen's residual_N bundles contact, balance and guide loads and models no gravity (revk/improve.py matched_force_duty), and the calculated parts at 35 deg sum to about 49-51 mN (gravity 29.5, face residual at the 95th percentile 11.2-13.1, guide drag 8.1; a conservative sum of magnitudes)",
     "Choose on the calculated 20 mN screen now; choose on EXP-T01's side load alone",
     "results/improvement/mechanics/mechanics_study.json (20/40/80 mN points); results/benchbuild/bench_calcs.json; DEC-072",
     "the duty screen disagrees with the first nib's measured coil heat (EXP-J17 (b), EXP-T12) by more than 20 %"),
    ("DEC-097", "Beryllium-copper wire on the bench is bought already age-hardened, so no heat treatment is done in-house; it is cut with shears or flush cutters only, never abrasive-cut, ground, sanded, pickled or acid-cleaned; joints are soldered under a bench fume absorber or crimped; nothing is welded; offcuts, broken coupons and wipes go into sealed labelled bags; no food or drink at the bench; hands washed after handling",
     "Age-harden in-house; laser-weld clamps as study B did for titanium; abrasive cut-off",
     "NGK Metals SDS s2.1 lists heat treating, pickling, chemical cleaning, abrasive cutting, welding, grinding, sanding and polishing among the exposure routes (AMF-319); OSHA PEL 0.2 ug/m3, STEL 2.0 ug/m3 (AMF-320); AMF-18; DEC-063",
     "no supplier can deliver aged 0.10 mm wire (then a supplier with beryllium controls heat-treats it)"),
    ("DEC-098", "Wire fatigue coupons (EXP-K21, EXP-B25, EXP-BB04) are driven at no more than 0.2 x the first transverse mode measured on each coupon; failure is detected by 4-wire resistance (an open circuit or a > 2 % step) in current-carrying wires; several coupons run in parallel on one crank-driven shuttle; 43.2 M cycles then take 3-8 days per batch (about 3.3-5.2 days for 26.8 mm wires, 6.7-7.5 days for 34 mm wires; CALC)",
     "200 Hz as bench_protocols.md suggests (about 60 h); resonance tracking only",
     "CALC (bench_calcs.json): first modes about 336-373 Hz for 34 mm wires and 487-763 Hz for 26.8 mm wires; at 200 Hz the clamp stress rises about 90 % and 12-33 % over the quasi-static stress the pen sees",
     "two drive frequencies on the same coupon lot give the same cycles to failure"),
    ("DEC-099", "The grounded five-bar is benched with a passive 24 mm dummy pen and spring hand simulants, never with a person's hand, until a safety gate like G-S is written for it. Its first build includes a hardware current limit at the motors' rated current, the 0.4 N cap in software (at rated current the linkage can still push about 1.06 N at the worst pose and direction, CALC), a breakaway magnetic pen coupling that releases between 0.5 and 0.8 N as the physical backstop, guards over the capstans and a latching emergency stop that removes motor power. Accepted-word results are claimed only from its measured replay (EXP-BB06, EXP-BB07), not from the rigid model",
     "Attach the fine nib first; test with a hand holding the pen",
     "DEC-071; the pass's 0 of 20 with 200 and 500 N/m grips and the erroneous ink during retraction; prototype_stages.md's G-S principle",
     "EXP-BB06 and BB07 pass and a G-S-type gate for the five-bar exists"),
]


def write_proposed():
    with open(OUT / "proposed_experiments.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "gate", "rig", "title", "measures", "decision", "requirements", "why_no_existing_experiment_covers_it"])
        w.writerows(EXPS)
    with open(OUT / "proposed_criteria.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "requirement_id", "experiment_id", "metric", "threshold", "direction", "basis", "status", "decision_gated"])
        w.writerows(CRIT)
    with open(OUT / "proposed_decisions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "decision", "alternatives", "basis", "revisit_if"])
        w.writerows(DECS)


# ------------------------------------------------------------------------------------------------ evidence rows
EV_HEADER = None


def ev(id_, topic, citation, year, url, stype, eclass, access, task, bench, comparator, findings, units, locator,
       limits, relevance, transf, reason, implication, query="direct URL", stream="AMF"):
    return [id_, topic, citation, year, url, stype, eclass, access, task, bench, comparator, findings, units, locator,
            limits, relevance, transf, reason, implication, SEEN, query, stream, ""]


NA = "not applicable (catalogue data; test method not published)"
EVID = [
    ev("AMF-300", "DAQ ADC evaluation module: TI ADS131M08EVM price, stock and kit contents", "Texas Instruments. ADS131M08EVM evaluation module, tool page; DigiKey listing 296-ADS131M08EVM-ND.", "n.d.",
       "https://www.ti.com/tool/ADS131M08EVM ; https://www.digikey.com/en/products/result?keywords=ADS131M08EVM", "manufacturer web page", "manufacturer statement", "product page",
       "Kit contents, stock and distributor price", NA, "none",
       "TI page: the kit contains 'ADS131M08 evaluation module', 'PHI controller board' and 'USB cable'; 'In stock'; price only after login. DigiKey 296-ADS131M08EVM-ND: USD 328.11 (qty 1), 2 in stock (seen 2026-09-30).",
       "USD as displayed", "TI tool page (order section); DigiKey search result", "Price and stock change; the PHI board is not used by the rig", "Price of DAQ-1's ADC, 'not seen' in AMF-222",
       "high", "catalogue data for the part used", "Budget USD 328 per ADC board; order in week 1"),
    ev("AMF-301", "Linear current amplifiers: OPA548T back-ordered; OPA549T and OPA564 as alternatives", "DigiKey product pages for Texas Instruments OPA548T (266166), OPA549T (307860) and OPA564AIDWP; TI OPA548T part-details page.", "n.d.",
       "https://www.digikey.com/en/products/detail/texas-instruments/OPA548T/266166 ; https://www.digikey.com/en/products/detail/texas-instruments/OPA549T/307860 ; https://www.ti.com/product/OPA548/part-details/OPA548T",
       "manufacturer web page", "manufacturer statement", "product page", "Distributor price and stock", NA, "none",
       "OPA548T: USD 21.55 (qty 1), 0 in stock, '50 expected' 30-Nov-2026 (DigiKey); TI part page 'Out of stock', no price. OPA549T: USD 34.44, 0 in stock, '25 expected in stock on 02-Dec-2027'. OPA564AIDWP (1.5 A, 20-HSOIC): USD 9.51, stock not shown (seen 2026-09-30).",
       "USD as displayed", "DigiKey product pages; TI part-details page", "Stock changes daily; other distributors not checked", "DAQ-1's current drive (OPA548, AMF-233) for voice coils and coupon coils",
       "high", "catalogue data for the parts named", "Treat the OPA548 as a lead-time risk; plan the OPA564 or a PWM driver with filtering"),
    ev("AMF-302", "Slide Hall sensor: TI DRV5055A4QDBZR price and stock", "DigiKey listing for Texas Instruments DRV5055A4QDBZR (296-50468-1-ND).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=DRV5055A4QDBZR", "manufacturer web page", "manufacturer statement", "product page", "Distributor price and stock", NA, "none",
       "USD 0.87 (cut tape, qty 1); 3,538 in stock (seen 2026-09-30).", "USD as displayed", "DigiKey search result", "Price and stock change", "R9's slide sensor (OPT-46)",
       "high", "catalogue data", "Order with the DAQ parts"),
    ev("AMF-303", "Current shunt: VPG Y14870R10000B9R (0.1 ohm, 0.1 %, 4-terminal foil) price and stock", "DigiKey listing for VPG Foil Resistors Y14870R10000B9R (804-1045-1-ND).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=Y14870R10000B9R", "manufacturer web page", "manufacturer statement", "product page", "Distributor price and stock", NA, "none",
       "'100 mOhms +-0.1% 1W Chip Resistor 2512 ... Current Sense ... Metal Foil', 4 terminations; USD 13.05 (qty 1); 0 in stock, '1,000 expected in stock on 12-Oct-2026' (seen 2026-09-30).",
       "USD as displayed", "DigiKey search result", "Price and stock change; TCR not read here", "DAQ-1's coil and voice-coil current channels",
       "high", "catalogue data", "Order in week 1 (arrives mid-October)"),
    ev("AMF-304", "Five-bar motor: Faulhaber 2224 U 012 SR price, stock and ratings at distributors", "DigiKey marketplace listing 5293-2224.11000-ND (Faulhaber, manufacturer number 2224.11000); RS Components 873-4795 (Faulhaber 2224U012SR).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=5293-2224.11000-ND ; https://int.rsdelivers.com/product/faulhaber/2224u012sr/faulhaber-brushed-dc-motor-405-w-12v-dc-67-mnm-2/8734795",
       "manufacturer web page", "manufacturer statement", "product page", "Distributor price, stock and headline ratings", NA, "none",
       "DigiKey (found by searching '2224U012SR'): 'Brushed DC Motor Standard 4390 RPM 8.5W 12VDC', USD 122.60 (qty 1), 7 in stock, marketplace product, 'Will ship in approximately 5 days from Faulhaber', USD 9.00 flat shipping. RS 873-4795 (2224U012SR): 4.05 W, 12 V dc, 6.7 mNm, 4390 rpm, 2 mm shaft; price on application (seen 2026-09-30).",
       "USD as displayed", "DigiKey product listing; RS product page", "The DigiKey page does not state that catalogue code 2224.11000 is the SR 012 winding; the two pages give different powers (8.5 W, 4.05 W)",
       "Price and lead time of the five-bar's motors (wholepen/grounded.py uses the 2224 U 012 SR sheet)", "high", "catalogue data for the motor used by the model", "Budget USD 123 per motor; confirm the code before ordering"),
    ev("AMF-305", "Brushed DC motor driver with current sense: Pololu DRV8874 carrier (item 4035)", "Pololu. DRV8874 Single Brushed DC Motor Driver Carrier, item 4035, product page.", "n.d.",
       "https://www.pololu.com/product/4035", "manufacturer web page", "manufacturer statement", "product page", "Price and specifications", NA, "none",
       "USD 11.94 (1 unit); 'Active and Preferred'; motor supply 4.5-37 V; '2.1 A continuous (3.5 A default current limit)'; current-sense feedback about 1.1 V/A; current regulation cycle-by-cycle or fixed off time (seen 2026-09-30).",
       "USD as displayed", "product page", "PWM ripple matters for force control; the 1.1 V/A output needs its own calibration", "Current loops of the five-bar (and an OPA548 fallback)",
       "high", "catalogue data", "Two drivers plus a spare; the current loop runs in the controller Teensy"),
    ev("AMF-306", "Current-mode servo controller: maxon ESCON Module 24/2 (466023)", "maxon. ESCON Module 24/2, 4-Q servo controller for DC/EC motors, 2/6 A, 10-24 VDC, part 466023, shop page.", "n.d.",
       "https://www.maxongroup.com/maxon/view/product/control/4-Q-Servokontroller/466023", "manufacturer web page", "manufacturer statement", "product page", "Price, status and specifications", NA, "none",
       "EUR 97.68 (1-4), 91.37 (5-19), 84.52 (20-49); status 'NRND (Not Recommended for New Designs)'; 10-24 VDC; 2 A continuous, 6 A peak (max. 4 s); modes include current controller; 12-bit +-10 V differential analog set value, PWM set value (seen 2026-09-30).",
       "EUR as displayed", "product page", "NRND; needs a carrier board", "Alternative current drive for the five-bar motors",
       "high", "catalogue data", "Use if the Teensy current loop proves noisy"),
    ev("AMF-307", "Five-bar output encoder: ams AS5047P (14-bit) and its adapter board", "DigiKey listings: AS5047P adapter board (4991-AS5047PADAPTERBOARD-ND) and AS5047P-ATSM-TSSOP14.", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=AS5047P-TS_EK_AB ; https://www.digikey.com/en/products/result?keywords=AS5047P-ATSM", "manufacturer web page", "manufacturer statement", "product page",
       "Price, stock, resolution", NA, "none",
       "Adapter board ('AS5047P - Magnetic, Rotary Position Sensor Evaluation Board', 360 deg, SPI, 3.3/5 V): USD 19.40, 397 in stock. AS5047P-ATSM-TSSOP14: resolution 14-bit, USD 9.38 (1), listed as discontinued at DigiKey; an Infineon-listed variant 0 in stock (seen 2026-09-30).",
       "USD as displayed", "DigiKey search results", "Integral non-linearity not read; wholepen/grounded.py assumes 16-bit", "Output-shaft encoders of the five-bar",
       "high", "catalogue data", "Buy the boards now; quantisation 8 um worst 1 sigma at the endpoint (CALC)"),
    ev("AMF-308", "12 V 60 W supply: Mean Well GST60A12-P1J", "DigiKey listing for Mean Well GST60A12-P1J (product 7703712).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=GST60A12-P1J", "manufacturer web page", "manufacturer statement", "product page", "Distributor price and stock", NA, "none",
       "'AC/DC DESKTOP ADAPTER 12V 60W', USD 19.40, listed under Normally Stocking (seen 2026-09-30).", "USD as displayed", "DigiKey search result", "Stock quantity not shown", "Driver rails of DAQ-1 and the five-bar",
       "high", "catalogue data", "One per build that drives motors"),
    ev("AMF-309", "Stock N52 block magnets 5 x 5 x 3 mm: supermagnete Q-05-05-03-N52N", "Webcraft GmbH (supermagnete.de). Block magnet 5 x 5 x 3 mm N52, article Q-05-05-03-N52N, product page.", "n.d.",
       "https://www.supermagnete.de/eng/block-magnets-neodymium/block-magnet-5mm-5mm-3mm_Q-05-05-03-N52N", "manufacturer web page", "manufacturer statement", "product page", "Price, tolerance, stock", NA, "none",
       "5 x 5 x 3 mm, +-0.1 mm; N52; magnetised heightwise (3 mm); Ni-Cu-Ni; EUR 0.35 (20 pcs), 0.30 (60+), 0.27 (140+), 0.24 (360+) each incl. VAT; 'promptly deliverable', 2,120 pieces in stock, 1-3 business days; Br not stated (seen 2026-09-30).",
       "EUR incl. VAT", "product page", "Br not stated: measure it (pull or Gaussmeter) before the model re-run", "Stock stand-in for Rev K's 5.12 x 5.12 x 3.5 mm poles in EXP-T07/K22",
       "high", "catalogue data", "First coupons with stock magnets; predictions regenerated at the as-built size"),
    ev("AMF-310", "Stock N52 cube magnets 4.76 mm: K&J Magnetics B333-N52", "K&J Magnetics. B333-N52, 3/16 inch cube, product page.", "n.d.",
       "https://www.kjmagnetics.com/b333-n52-neodymium-block-magnet", "manufacturer web page", "manufacturer statement", "product page", "Price, tolerance, Br, stock", NA, "none",
       "4.76 x 4.76 x 4.76 mm, tolerance +-0.004 in (+-0.1 mm); N52; Br 14,800 Gauss; Ni-Cu-Ni; USD 0.56 each (1-49) to 0.50 (1,000-2,499); In Stock (seen 2026-09-30).",
       "USD as displayed", "product page", "1.26 mm thicker than the 3.5 mm design pole", "Stock stand-in for the reach candidate's 4.81 mm poles",
       "high", "catalogue data", "Second stock coupon; model re-run at the as-built size"),
    ev("AMF-311", "C17200 (CuBe2) fine wire source: Goodfellow Cu98/Be2 wire", "Goodfellow. Copper/Beryllium Wire (Spooled) and (Straight), Cu98/Be2 alloy, group pages.", "n.d.",
       "https://www.goodfellow.com/usa/copper-beryllium-alloy-spooled-wire-cu98-be2-group ; https://www.goodfellow.com/usa/copper-beryllium-alloy-straight-wire-cu98-be2-group", "manufacturer web page", "manufacturer statement", "product page",
       "Starting prices and lead time", NA, "none",
       "Spooled wire: 'Starting at $279.00 each'; approximate lead time 2 weeks; composition Cu 98/Be 2; tensile strength 500-1300 MPa. Straight wire: 'Starting at $429.00 each', 1 m lengths, Hard temper. The diameter table loads dynamically and was not visible, so 0.10 mm is not confirmed (seen 2026-09-30).",
       "USD as displayed", "group pages", "Diameter, temper (aged or not) and price per diameter not visible", "The wire of EXP-K21 and EXP-BB04 (DEC-063)",
       "medium", "a named source for the alloy, not yet for the 0.10 mm aged wire", "Request a quote for 0.10 and 0.08 mm in an aged temper"),
    ev("AMF-312", "301 stainless foil source: Goodfellow AISI 301 foil", "Goodfellow. AISI 301 Stainless Steel Foil/Sheet, group page.", "n.d.",
       "https://www.goodfellow.com/usa/aisi-301-stainless-steel-foil-group", "manufacturer web page", "manufacturer statement", "product page", "Starting price and tolerances", NA, "none",
       "Starting price USD 252.00; temper 'Hard'; the tolerance table lists thickness bands <0.01 mm, 0.01-0.05 mm and >0.05 mm; 'No Minimum order'; lead time not shown (seen 2026-09-30).",
       "USD as displayed", "group page", "Exact thicknesses and their tolerances not visible", "Foil for the anchor coupon (EXP-BB03)",
       "medium", "source of the alloy and temper; thickness to confirm", "Measure every sheet; set the beam width from the measured thickness"),
    ev("AMF-313", "Photo-etching capability limits: Ponoko metal photo etching", "Ponoko. Metal photo etching service page.", "n.d.",
       "https://www.ponoko.com/photo-etching/metal", "manufacturer web page", "manufacturer statement", "product page", "Service capability", NA, "none",
       "'Material thickness 0.03 - 0.76mm'; 'Dimensional accuracy of +-0.13mm'; minimum feature size '1x material thickness (min 1mm)'; kerf '0.18mm'; minimum lead time '10 days'; price from an instant quote only (seen 2026-09-30).",
       "mm as stated", "service page", "One service only; precision etchers were not priced", "Process choice for the anchor coupon's 0.5 mm beams",
       "high", "the stated limits apply directly", "Use a precision etcher or laser micromachining (+-0.01 mm), not this class of service"),
    ev("AMF-314", "Low-cost scanner for gap fractions: Epson Perfection V39 II", "Epson. Perfection V39 II Color Photo and Document Scanner (B11B268201), product page.", "n.d.",
       "https://www.epson.com/For-Work/Scanners/Photo-and-Graphics/Epson-Perfection-V39-II-Color-Photo-and-Document-Scanner/p/B11B268201", "manufacturer web page", "manufacturer statement", "product page",
       "Price and resolution", NA, "none", "USD 129.99; '4800 dpi optical resolution'; bit depth not shown in the text read (seen 2026-09-30).",
       "USD as displayed", "product page", "Optical resolution is not effective resolution: check with a USAF target", "EXP-T02 gap fractions in the minimum viable build",
       "medium", "adequate for gap presence; not qualified for R3's 5 um", "Buy for G1; the V850 Pro (AMF-236) waits for G3"),
    ev("AMF-315", "Calibration weights: Mettler Toledo 30402728 OIML M1 set 1 g-500 g", "Scales Galore. Mettler Toledo 30402728 OIML Class M1 Stainless Steel Calibration Weight Set, 1 g to 500 g, product page.", "n.d.",
       "https://www.scalesgalore.com/product/Mettler-Toledo-30402728-OIML-Class-M1-Stainless-Steel-Calibration-Weight-Set-1-g-to-500-g-px60692.cfm", "manufacturer web page", "manufacturer statement", "product page",
       "Price, contents, availability", NA, "none",
       "USD 535.50; 'Available to Ship'; 12 cylindrical weights with knobs: 1, 2, 2 (marked), 5, 10, 20, 20 (marked), 50, 100, 200, 200 (marked), 500 g (seen 2026-09-30).",
       "USD as displayed", "product page", "Reseller price; certificate options not read", "In-situ calibration of R9 (and the MVP's dead-weight F_c)",
       "high", "catalogue data", "Budget USD 536"),
    ev("AMF-316", "Five-bar bearings: MR63-ZZ 3 x 6 x 2.5 mm (Bearings Direct)", "Bearings Direct. MR63-ZZ mini ball bearing 3x6x2.5 shielded (L-630ZZ), product page.", "n.d.",
       "https://bearingsdirect.com/mr63-zz-mini-ball-bearing-3x6x2-5-shielded-l-630zz/", "manufacturer web page", "manufacturer statement", "product page", "Price and stock", NA, "none",
       "USD 4.38 per bearing; 10-24 units 5 % off, 25-49 10 %, 50+ 15 %; '684 available' in Glendale, California; 'Usually ships in 24 hours'; ABEC grade not stated (seen 2026-09-30).",
       "USD as displayed", "product page", "Precision grade not stated: backlash and stiffness are measured (EXP-BB06)", "Five-bar joints",
       "high", "catalogue data", "Twelve bearings"),
    ev("AMF-317", "Soldering fume absorber: Hakko FA400-04", "DigiKey listing for American Hakko Products FA400-04 (product 6228795).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=FA400-04", "manufacturer web page", "manufacturer statement", "product page", "Distributor price", NA, "none",
       "'FUME ABSORBER BENCH TOP', USD 93.79; stock quantity not shown (seen 2026-09-30).", "USD as displayed", "DigiKey search result", "Filter performance not read", "Local exhaust at the soldering station (DEC-097 proposed)",
       "medium", "a bench absorber, not a certified beryllium exhaust", "Use for every C17200 joint; keep the SDS's other operations off the bench"),
    ev("AMF-318", "Laser displacement sensor: Panasonic HG-C1030", "DigiKey product page for Panasonic Industry HG-C1030 (5215054).", "n.d.",
       "https://www.digikey.com/en/products/detail/panasonic-industry/HG-C1030/5215054", "manufacturer web page", "manufacturer statement", "product page", "Price, stock, key specifications", NA, "none",
       "USD 439.60 (qty 1); 26 in stock; sensing distance 30 mm; response time 1.5 ms; red laser 655 nm; 12-24 V; NPN open collector (seen 2026-09-30).",
       "USD as displayed", "DigiKey product page", "Resolution and repeatability not shown on the page read", "Fatigue-shuttle amplitude and the wires' first mode",
       "medium", "optional instrument", "Optional; the strobed camera can replace it"),
    ev("AMF-319", "Beryllium-copper handling: NGK Metals Copper Beryllium Wrought Alloys SDS (includes alloy 25, C17200)", "NGK Metals Corporation. Copper Beryllium Wrought Alloys, Safety Data Sheet according to the Hazard Communication Standard (HazCom 2012), version 1.0, issue and revision date 16 January 2023.", "2023",
       "https://www.ngkmetals.com/wp-content/uploads/Copper-Beryllium-Wrought-Alloys-EN-OSHA-GHS-SDS-2023-01-16-Final.pdf", "datasheet", "manufacturer statement", "full text",
       "Hazards, exposure operations, limits and controls", "not applicable", "none",
       "S2.1: 'Metallic product which poses little or no immediate hazard in solid form. Exposure ... can occur when melting, casting, dross handling, pickling, chemical cleaning, heat treating, abrasive cutting, welding, grinding, sanding, polishing, milling, crushing, or otherwise heating or abrading the surface of this material in a manner which generates particulate.' GHS classes include Resp. Sens. 1, Carc. 1A, Repr. 1B, STOT RE 1. S8.1: OSHA PEL (TWA) 0.2 ug/m3 and OSHA PEL (Ceiling) 2 ug/m3 for beryllium. S8.2: 'Ensure good ventilation of the work station. If applicable, use process enclosures, local exhaust ventilation or other engineering controls...'. Product codes include 25 (C17200).",
       "ug/m3", "Sections 1.1, 2.1, 2.2, 8.1, 8.2", "Generic for wrought alloys; soldering is not named in the list; the SDS of the wire actually bought takes precedence",
       "Bench rules for cutting, joining, heat treating and cleaning C17200 wire (DEC-063; DEC-097 proposed)", "high", "applies to the alloy used",
       "Buy aged wire; shear-cut; no pickling, abrasive cutting or welding; solder under local exhaust; bag offcuts"),
    ev("AMF-320", "Beryllium exposure limits: OSHA beryllium standard FAQ", "Occupational Safety and Health Administration. Beryllium and Beryllium Compounds - Frequently Asked Questions (rulemaking).", "n.d.",
       "https://www.osha.gov/beryllium/rulemaking/faq", "website", "standard", "full text (web page)", "Regulatory limits", "not applicable", "none",
       "8-hour TWA PEL 0.2 ug/m3; STEL 2.0 ug/m3 over 15 minutes; action level 0.1 ug/m3 (8-hour TWA); materials containing less than 0.1 % beryllium by weight are exempt only with objective data showing exposure stays below the action level (seen 2026-09-30).",
       "ug/m3", "FAQ answers on the limits and on the exemption", "US regulation; other jurisdictions differ; C17200 (about 2 % Be, AMF-311) is not exempt",
       "Why the bench keeps particulate-generating operations on C17200 off the bench", "high", "regulatory limit", "No abrasive or thermal processing of C17200 at the bench"),
    ev("AMF-321", "Bench oscilloscope: Rigol DHO804", "DigiKey listing for Rigol DHO804 (2211-DHO804-ND).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=DHO804", "manufacturer web page", "manufacturer statement", "product page", "Distributor price and stock", NA, "none",
       "USD 459.00; 40 in stock; '70MHz, 1.25GSa/s, 4 channels', 25 Mpts (seen 2026-09-30).", "USD as displayed", "DigiKey search result", "Price and stock change", "DAQ-1 bring-up (EXP-BB01)",
       "high", "catalogue data", "Only if the lab has no scope"),
    ev("AMF-322", "6.5-digit DMM: Siglent SDM3065X", "DigiKey listing for Siglent SDM3065X (product 10455229).", "n.d.",
       "https://www.digikey.com/en/products/result?keywords=SDM3065X", "manufacturer web page", "manufacturer statement", "product page", "Distributor price", NA, "none",
       "USD 857.00; stock quantity not shown (seen 2026-09-30).", "USD as displayed", "DigiKey search result", "Accuracy specifications not read here", "4-wire resistance of wires, coils and shunts",
       "medium", "catalogue data", "Only if the lab has no 4-wire meter"),
    ev("OPT-100", "Near-field page-sensor board availability: PMW3360 breakout (Keycapsss KC10125)", "Keycapsss. KYCS-PMW3360 Breakout Board for Pixart PMW3360 Optical Mouse Sensor, KC10125, product page.", "n.d.",
       "https://keycapsss.com/keyboard-parts/parts/164/kycs-pmw3360-breakout-board-for-pixart-pmw3360-optical-mouse-sensor", "manufacturer web page", "manufacturer statement", "product page",
       "Price, stock and contents", NA, "none",
       "EUR 29.90 incl. VAT (25.13 excl.); 'Currently out of stock'; 'Assembled and tested'; 'Focusing lens included'; sensor PMW3360DM-T2QU (seen 2026-09-30). Pimoroni's PAA5100JE (OPT-90) showed 'Pre-order' the same day.",
       "EUR as displayed", "product page", "Stock changes; JACK Enterprises' boards are retired (OPT-91)", "R10's sensor candidates (EXP-T04)",
       "high", "availability of the candidate class", "Order candidates in week 1; plan a harvested-mouse fallback", stream="OPT"),
    ev("OPT-101", "Rev K's page-sensor die availability: PMW3610DM-SUDU at JLCPCB", "JLCPCB parts library. PixArt PMW3610DM-SUDU, part C42442560.", "n.d.",
       "https://jlcpcb.com/partdetail/PixArt-PMW3610DMSUDU/C42442560", "manufacturer web page", "manufacturer statement", "product page", "Availability for assembly", NA, "none",
       "Listed as an 'Extended' part; unit price and stock were not displayed in the content read (seen 2026-09-30).",
       "none", "parts-library page", "No price or stock seen; the die needs its lens and a board", "Rev K's die class (OPT-61) on R10",
       "medium", "listing only", "Treat the PMW3610 as a lead-time risk", stream="OPT"),
]


def write_evidence():
    with open(ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert len(header) == 23, header
    for r in EVID:
        assert len(r) == 23, (r[0], len(r))
    with open(OUT / "evidence_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(EVID)


# ------------------------------------------------------------------------------------------------ data templates
TEMPLATES = {
    "instruments.csv": (["instrument_id", "model_class", "manufacturer", "part_number", "serial", "range", "cal_cert", "cal_due", "location", "notes"],
                        ["# instrument register (validation/records/README.md s1): one row per instrument; certificate and due date checked at session start"]),
    "run_order_EXP-T01.csv": (["order", "condition_code", "theta_deg", "beta_deg", "v_mm_s", "Fc_N", "refill_type", "refill_id", "refill_lot", "paper", "paper_batch", "underlay", "repeat", "marker_value", "seed"],
                              ["# randomised run order (bench_protocols.md s0.6); marker_value is sent with the MARK command and cuts the session (rig.convert.split_by_markers)"]),
    "r9_axial_cell_calibration.csv": (["load_N", "reading_mVV", "direction", "theta_deg", "T_C", "note"],
                                      ["# dead weights on the cartridge at the test angle; direction +1 loading, -1 unloading -> rig.calib.fit_bridge"]),
    "r9_plate_calibration.csv": (["Fx_N", "Fy_N", "Fz_N", "raw_x_mVV", "raw_y_mVV", "raw_z_mVV", "pos_x_mm", "pos_y_mm", "theta_deg"],
                                 ["# page frame, force ON the platen (weights: Fz negative); horizontal pulls over the jewel-bearing pulley -> rig.calib.fit_plate / apply_plate"]),
    "r9_guide_stiffness.csv": (["slide_m", "force_N", "note"], ["# refill off the paper; voice coil moves the holder -> rig.calib.fit_guide_stiffness"]),
    "r9_tap_test.csv": (["tap_id", "underlay", "f1_Hz", "zeta", "method", "session_dir"], ["# EXP-BB02 AC-BB02-01: plate stack first mode (>= 100 Hz, DEC-058)"]),
    "ink_scan_register.csv": (["sheet_code", "blind_code", "record_id", "refill_type", "paper", "theta_deg", "v_mm_s", "Fc_profile", "line_id", "p0_row", "p0_col", "p1_row", "p1_col", "dpi", "scanner", "scan_utc", "scan_file_sha256"],
                              ["# blind codes kept outside the analysis tree (bench_protocols.md s0.6); p0/p1 from fiducial registration -> rig.ink.analyse_line"]),
    "t07_force_map.csv": (["node_id", "x_mm", "y_mm", "I_A", "Fx_N", "Fy_N", "Fz_N", "R_coil_ohm", "T_coil_C", "t_s", "coupon_id", "magnet_lot"],
                          ["# reversal order of currents at each node, 0.2 s holds, >= 30 s cooling above 0.3 I_max -> rig.coupon.km_map (pipeline_check step C)"]),
    "wire_mode_check.csv": (["coupon_id", "wire_length_mm", "tension_N", "f1_measured_Hz", "method", "drive_Hz", "ratio_drive_over_f1"],
                            ["# AC-BB04-05 / DEC-098: every fatigue coupon, drive <= 0.2 x f1"]),
    "k21_wire_log.csv": (["coupon_id", "wire_id", "clamp_type", "wire_diameter_mm", "free_length_mm", "stop_mm", "cycles", "R_4w_ohm", "T_clamp_C", "I_A", "drive_Hz", "status", "note"],
                         ["# failure = open circuit or > 2 % resistance step over the running median (pipeline_check.wire_failure); 50x inspection at every stop"]),
    "anchor_stiffness.csv": (["coupon_id", "foil_thickness_um", "beam_width_um", "beam_length_mm", "with_interconnect", "disp_um", "balance_reading_g", "direction", "T_C"],
                             ["# hub pushed in 10 um steps; force = reading x g -> rig.calib.fit_guide_stiffness (slope = axial stiffness)"]),
    "guide_drag_sweep.csv": (["coupon_id", "guide", "preload_N", "couple_mNm", "cycle", "x_mm", "F_lat_mN", "direction", "v_mm_s"],
                             ["# drag = half the forward/return difference at the same x (pipeline_check.guide_drag); 10 g cell"]),
    "guide_tilt.csv": (["coupon_id", "guide", "preload_N", "couple_mNm", "tilt_urad", "method", "note"], ["# laser lever or autocollimator; AC-K20-02 / AC-BB05-02"]),
    "thermal_run.csv": (["t_s", "P_W", "R_coil_ohm", "T_coil_C", "T_web_C", "T_amb_C"], ["# coil temperature from resistance (rig.thermal.coil_temperature) -> rig.thermal.fit_1node / fit_2node"]),
    "fivebar_encoder_truth.csv": (["pose_id", "enc0_counts", "enc1_counts", "cam_x_mm", "cam_y_mm", "T_C", "fit_or_holdout"],
                                  ["# 20 fit poses + 35 held-out poses; forward kinematics as pipeline_check.fivebar_fk -> AC-BB06-01"]),
    "fivebar_force_map.csv": (["pose_x_mm", "pose_y_mm", "dir_deg", "i0_A", "i1_A", "Fx_N", "Fy_N", "note"], ["# holder clamped on the K3D40 +-10 N; tau = J^T F check -> AC-BB06-02"]),
    "fivebar_word_replay.csv": (["trial", "suffix_id", "hand_k_N_m", "controller", "completed", "refused", "stop_hit", "coverage_pct", "rms_ink_mm", "air_ink_mm", "ink_after_refusal_mm", "peak_acc_m_s2", "peak_jerk_m_s3", "scan_code"],
                                ["# AC-BB07-01...03; scans analysed blind"]),
    "r10_pose_matrix.csv": (["run_id", "sensor", "mode", "theta_deg", "roll_deg", "height_mm", "paper", "motion", "speed_mm_s", "truth", "order", "seed"],
                            ["# EXP-T04/T05 pose and motion plan -> rig.pagesense.qualify / sim2j_page_model"]),
    "r10_reanchor_trials.csv": (["trial", "sensor", "outage_type", "lift_height_mm", "outage_s", "displacement_mm", "anchor_invalid_t_s", "reanchor_method", "reanchor_t_s", "abs_error_um", "lost_motion_mm"],
                                ["# EXP-BB08: a silent recovery is an absolute position output before re-anchoring"]),
    "contact_timing.csv": (["event_id", "type", "theta_deg", "paper", "t_plate_s", "t_channel_s", "delay_ms", "threshold_mN", "false_event"],
                           ["# EXP-BB09: plate truth crossing 20 mN against the pen-side decision"]),
}

RECORD_YAML = """# record.yaml template (validation/records/README.md s3). Fill every field; 'null' only where the README allows it.
record_id: EXP-T01_YYYYMMDD_R9-<plate serial>-<refill lot>_core_01
experiment_id: EXP-T01
status: executed            # executed | aborted | superseded (with superseded_by)
protocol:
  file: validation/bench_protocols.md
  git_commit: <hash at which the protocol was frozen>
acceptance_criteria:
  file: validation/acceptance_criteria.csv
  git_commit: <hash>
  ids: [AC-T01-01, AC-T01-02, AC-T01-04, AC-T01-05, AC-B01-03]
prediction:
  file: <frozen prediction file>
  parameters_version: <from stabpen.provenance>
  parameters_sha256_16: <from stabpen.provenance>
analysis_code:
  path: rig/contact.py
  git_commit: <hash>
operators: [<initials or staff id>]
location: <lab>, rig R9 on DAQ-1
start_utc: YYYY-MM-DDThh:mm:ssZ
end_utc: YYYY-MM-DDThh:mm:ssZ
environment: {temperature_C: null, rh_pct: null, notes: ""}
dut:
  refill: {type: D1-oil, lot: <lot>, ids: [<ids>]}
  paper: {type: copy-80gsm, batch: <batch>, conditioning_h: 24}
  underlay: hard
instruments:                # ids from instruments.csv
  - {id: K3D40-2N-01, model_class: "3-axis force sensor +-2 N", cal_cert: <id>, cal_due: YYYY-MM-DD}
  - {id: LSB200-100g-01, model_class: "in-line axial cell 1 N", cal_cert: <id>, cal_due: YYYY-MM-DD}
  - {id: DAQ-1, model_class: "Teensy 4.1 + ADS131M08EVM", firmware_commit: <hash>}
check_standards:
  - {id: DW-0050, nominal: 0.4903 N, measured: null, within_control_limits: null}
sync: {method: "TTL 1 Hz coded", alignment_check_us: null}
calibration_files: [analysis/r9_axial_cell_calibration.csv, analysis/r9_plate_calibration.csv, analysis/r9_guide_stiffness.csv]
tap_test: {f1_Hz: null, file: analysis/r9_tap_test.csv}
randomisation: {seed: null, order_file: raw/run_order_EXP-T01.csv}
blinding: {image_codes_file: null, unblinded_utc: null}
deviations: []              # each: {time_utc, description, impact, approved_by}
verdicts_file: analysis/verdict.yaml
"""

VERDICT_YAML = """# analysis/verdict.yaml template (validation/records/README.md s3): one entry per criterion
- id: AC-T01-01
  measured_value: null
  unit: mN
  expanded_uncertainty_k2: null
  budget_ref: rig/uncertainty.py axial_force_budget
  decision_rule: simple      # simple (TUR >= 4) | guarded (bench_protocols.md s0.5)
  tur: null
  verdict: null              # pass | fail | inconclusive (rig.uncertainty.decide)
  prediction: {file: null, value: null}
  analysis_commit: null
  notes: ""
"""


def write_templates():
    TPL.mkdir(parents=True, exist_ok=True)
    for name, (cols, comments) in TEMPLATES.items():
        with open(TPL / name, "w", newline="", encoding="utf-8") as f:
            for c in comments:
                f.write(c + "\n")
            csv.writer(f).writerow(cols)
    (TPL / "record_template.yaml").write_text(RECORD_YAML)
    (TPL / "verdict_template.yaml").write_text(VERDICT_YAML)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_boms()
    tot = totals()
    write_cost_schedule(tot)
    write_map()
    write_proposed()
    write_evidence()
    write_templates()
    print(json.dumps({k: v for k, v in tot.items() if k in ("by_build", "mvp", "all_builds_core_low", "all_builds_core_high",
                                                             "all_builds_instruments_low", "all_builds_instruments_high")}, indent=1))
    print("stages:", json.dumps(tot["by_stage"]))


if __name__ == "__main__":
    main()
