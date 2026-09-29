"""Bill of materials for rigs R9-R14 and the shared DAQ (results/rig/bom.csv).

Prices appear only where a price was displayed on the page cited in `source` on 2026-09-29
(currency as shown, excluding tax and shipping unless the page said otherwise). Everything else
reads "not seen". Part numbers are the manufacturer's, as shown on the page opened (ledger id in
`ledger`); "class" rows name a specification, not a product, and say so.
"""
from __future__ import annotations

import csv
from typing import Dict, List

COLUMNS = ["rig", "build", "part", "supplier", "part_number", "qty", "unit_price", "currency", "price_seen_on",
           "source", "ledger", "role", "notes"]

NS = "not seen"


def _b(rig, build, part, supplier, pn, qty, price=NS, cur="", seen="", source="", ledger="", role="", notes=""):
    return dict(rig=rig, build=build, part=part, supplier=supplier, part_number=pn, qty=qty, unit_price=price,
                currency=cur, price_seen_on=seen, source=source, ledger=ledger, role=role, notes=notes)


D = "2026-09-29"
ROWS: List[Dict] = [
    # ---------------------------------------------------------------- shared DAQ-1 (one per rig in use; two in all)
    _b("DAQ-1", "all", "Teensy 4.1 microcontroller board", "SparkFun (PJRC)", "DEV-16771", 2, "31.50", "USD", D,
       "https://www.sparkfun.com/teensy-4-1.html", "AMF-220", "one clock: cycle-counter time stamps; SPI to the ADC; 4 hardware quadrature decoders; USB 480 Mbit/s"),
    _b("DAQ-1", "standard", "ADS131M08 evaluation module, used without its PHI controller", "Texas Instruments", "ADS131M08EVM", 2,
       source="https://www.ti.com/lit/ug/sbau334a/sbau334a.pdf", ledger="AMF-222",
       role="8 simultaneous 24-bit channels (bridges, shunts, Hall sensors)", notes="wire J10 to the Teensy; AVDD via JP12/TP2; DVDD via TP1 with R67 removed (SBAU334A section 4)"),
    _b("DAQ-1", "low-cost", "NAU7802 24-bit bridge ADC breakout", "Adafruit", "4538", 4, "5.95", "USD", D,
       "https://www.adafruit.com/product/4538", "AMF-228", "quasi-static bridge channels only (R9 low-cost build)", "rate not verified here"),
    _b("DAQ-1", "all", "Thermocouple amplifier breakout MAX31856", "Adafruit", "3263", 4, "17.50", "USD", D,
       "https://www.adafruit.com/product/3263", "AMF-234", "magnet, housing, web, room temperatures"),
    _b("DAQ-1", "all", "Type-T fine-wire thermocouple, 0.08 mm class", "class (any calibrated supplier)", "class", 8,
       notes="calibrate in a dry block to +-0.5 C (bench_protocols.md R4)"),
    _b("DAQ-1", "all", "Precision shunt 0.1 ohm, 0.1 %, 3 W, 4-terminal", "class", "class", 4, role="coil and voice-coil currents"),
    _b("DAQ-1", "all", "USB power bank (battery) for isolated recording sessions", "class", "class", 1,
       role="no mains path during human sessions (R11)"),
    # ---------------------------------------------------------------- ground-truth kit (shared)
    _b("GT", "standard", "Linear magnetic encoder readhead LM13, resolution option 13B (about 0.244 um), with MS magnetic scale", "RLS",
       "LM13 (13B option; order code per data sheet LM13D02_05)", 4, source="https://www.renishaw.com/resourcecentre/download/lm13-magnetic-encoder-system--103312?userLanguage=en",
       ledger="OPT-89", role="head position truth on the CoreXY (2) and the disturbance stage (2)", notes="accuracy grade +-10 um MS scale; hysteresis < 4 um"),
    _b("GT", "low-cost", "Global-shutter camera OV9281, UVC, external trigger", "Arducam", "OV9281 UVC global-shutter camera board", 1,
       source="https://docs.arducam.com/UVC-Camera/Appilcation-Note/External-Trigger-Mode/OV9281-Global-Shutter/", ledger="OPT-88",
       role="strobed dot tracking at up to 100 fps (10 ms, DeltaPen's window)", notes="vendor shop pages refused the fetch: price not seen"),
    _b("GT", "low-cost", "LED strobe: high-power LED + logic MOSFET driver, 20-50 us pulses", "class", "class", 1,
       role="freezes motion inside the exposure; the strobe edge is the image time stamp"),
    _b("GT", "all", "Dot/line calibration grid, chrome on glass, 1 um pitch uncertainty class", "class", "class", 1,
       role="camera scale and distortion; scanner distortion map (R3)"),
    _b("GT", "reference", "Linear motor stage X-LDM110C-AE54D12 (1 nm encoder, 1 um accuracy)", "Zaber Technologies",
       "X-LDM110C-AE54D12", 2, "9255", "USD", D, "https://www.zaber.com/products/linear-stages/X-LDM-AE/specs?part=X-LDM110C-AE54D12",
       "AMF-229", "reference XY truth for page-sensor qualification (R10)"),
    _b("GT", "all", "Flatbed scanner Perfection V850 Pro (4800/6400 dpi)", "Epson", "B11B224201", 1, "1999.00", "USD", D,
       "https://epson.com/For-Work/Scanners/Photo-and-Graphics/Epson-Perfection-V850-Pro-Photo-Scanner/p/B11B224201", "AMF-236",
       "ink continuity and ink-path metrology (R3)", "any 2400 dpi flatbed is enough for gap fractions"),
    # ---------------------------------------------------------------- R9 contact and ink rig (G1)
    _b("R9", "all", "CoreXY 3-D printer as the motion frame (kit)", "Prusa Research", "Prusa CORE One+ (Gen 2), kit", 1,
       "925", "USD", D, "https://www.prusa3d.com/product/prusa-core-one/", "AMF-231",
       "head moves in XY, bed (force plate) still in XY; Z sets the pen height; chamber to 55 C", "assembled: USD 1,202.78 (same page)"),
    _b("R9", "standard", "3-axis force sensor K3D40 +-2 N (ink-threshold series)", "ME-Messsysteme", "K3D40 +-2N", 1,
       source="https://www.instrumentation.it/gallery/6977/id_3-Axis_Force_Sensor_K3D40_20161005.pdf", ledger="AMF-224",
       role="paper-normal and friction forces in the page frame", notes="price not seen (shop behind a bot check)"),
    _b("R9", "standard", "3-axis force sensor K3D40 +-10 N (friction map to 4 N)", "ME-Messsysteme", "K3D40 +-10N", 1,
       source="https://www.instrumentation.it/gallery/6977/id_3-Axis_Force_Sensor_K3D40_20161005.pdf", ledger="AMF-224"),
    _b("R9", "reference", "6-axis F/T sensor Nano17, calibration SI-12-0.12", "ATI Industrial Automation", "Nano17 SI-12-0.12", 1,
       source="https://www.ati-ia.com/products/ft/ft_models.aspx?id=Nano17", ledger="AMF-223", role="reference plate / check of the K3D40"),
    _b("R9", "standard", "Miniature S-beam load cell LSB200, 100 g (1 N)", "FUTEK", "FSH03870", 1,
       source="https://media.futek.com/content/futek/files/pdf/productdrawings/lsb200.pdf", ledger="AMF-225",
       role="axial refill force F_c, in line behind the refill"),
    _b("R9", "standard", "Miniature S-beam load cell LSB200, 250 g (2.5 N)", "FUTEK", "FSH03871", 1,
       source="https://media.futek.com/content/futek/files/pdf/productdrawings/lsb200.pdf", ledger="AMF-225", role="axial force for G2-format refills and heavy runs"),
    _b("R9", "low-cost", "Mini load cell 100 g, straight bar (TAL221)", "SparkFun", "SEN-14727", 2, "14.50", "USD", D,
       "https://www.sparkfun.com/mini-load-cell-100g-straight-bar-tal221.html", "AMF-227", "axial force (low-cost build, through a bell crank)"),
    _b("R9", "standard", "Moving-coil voice coil LVCM-013-013-03 (refill-force axis)", "Moticont", "LVCM-013-013-03", 1,
       source="https://www.moticont.com/pdf/lvcm-013-013-03M.pdf", ledger="AMF-02", role="programmable F_c (ramps for the ink threshold)",
       notes="low-cost build: dead weights on a thread over a jewel-bearing pulley"),
    _b("R9", "all", "Power op-amp OPA548 (linear current drive)", "Texas Instruments", "OPA548", 2,
       source="https://www.ti.com/product/OPA548", ledger="AMF-233", role="F_c voice coil; later R12/R13 coils"),
    _b("R9", "all", "Refill: ballpoint, ISO D format, M", "Schmidt Technology", "S 635 M", 20,
       source="https://www.schmidttechnology.de/en/products/writing-instruments-technology-2/refills/", ledger="CON-100", role="G1 refill type 1 (12-16 mm core format)"),
    _b("R9", "all", "Refill: hybrid ink, G2 format, 0.8 mm", "Schmidt Technology", "easyFLOW 9000 (0.8 mm)", 10,
       source="https://www.schmidttechnology.de/en/products/writing-instruments-technology-2/refills/", ledger="CON-100", role="G1 refill type 2 (24 mm pen format)"),
    _b("R9", "all", "Refill: capless ceramic rollerball 0.6 mm, 97.5 mm", "Schmidt Technology", "P 8126", 10,
       source="https://www.schmidttechnology.de/en/products/writing-instruments-technology-2/refills/", ledger="CON-100", role="G1 refill type 3"),
    _b("R9", "all", "Refill: fineliner 0.8 mm, spring-loaded tip", "Schmidt Technology", "FL 6040 F", 10,
       source="https://www.schmidttechnology.de/en/products/writing-instruments-technology-2/refills/", ledger="CON-100", role="G1 refill type 4"),
    _b("R9", "all", "Refill: gel ink, ISO D1 format", "class (maker to choose)", "class", 10, role="optional 5th type",
       notes="no gel D refill in the Schmidt range (CON-100)"),
    _b("R9", "all", "Papers: copy 80 g/m2, recycled, school ruled, coated, tracing, card", "class (log brand and batch)", "class",
       "1 ream each", role="the six reference papers of EXP-D01 / EXP-J04", notes="condition 24 h at 23 C / 50 % RH"),
    _b("R9", "all", "Dead-weight set 1 g-500 g, OIML class M1", "class", "class", 1, role="in-situ calibration at every test angle"),
    _b("R9", "all", "Digital inclinometer, 0.1 deg class", "class", "class", 1, role="verifies the tilt under load"),
    # ---------------------------------------------------------------- R10 page-sensor rig
    _b("R10", "all", "Page-sensor candidates: PMW3610-class die with folded optics (Rev J.1), PMW3360/3389 boards, PAA5100JE breakout",
       "various", "PIM573 (Pimoroni PAA5100JE)", "1 each", source="https://shop.pimoroni.com/products/paa5100je-optical-tracking-spi-breakout",
       ledger="OPT-90; OPT-91; OPT-61", role="devices under test", notes="JACK Enterprises PMW3360/3389 boards are retired (OPT-91)"),
    _b("R10", "all", "Tilt-roll-height fixture: printed arc 35-75 deg, roll ring +-20 deg, micrometer Z 1.5-4.5 mm", "PROPOSED DESIGN",
       "mechanics/cad/rig_pagesense.py", 1, role="sensor pose over the paper"),
    # ---------------------------------------------------------------- R11 recording pen and tablet protocol
    _b("R11", "tablet", "Pen tablet with ink pens (Paper Edition), medium", "Wacom", "PTH-660P", 1,
       source="https://estore.wacom.com/media/sebwite/productdownloads/i/n/intuos_pro_factsheet_en_weg_2.pdf", ledger="OPT-86",
       role="EXP-H01 tablet protocol: real ink, nib x/y, pressure, tilt", notes="availability in 2026 to check (OPT-87 lists no paper mode)"),
    _b("R11", "tablet", "Finetip Pen (0.4 mm gel) and Ballpoint Pen (1.0 mm oil) for the tablet", "Wacom", "Finetip Pen; Ballpoint Pen", "1 each",
       source="https://estore.wacom.com/media/sebwite/productdownloads/i/n/intuos_pro_factsheet_en_weg_2.pdf", ledger="OPT-86"),
    _b("R11", "pen", "Button load cell LLB130, 1000 g (slim 12-16 mm pen)", "FUTEK", "LLB130 (1000 g)", 1,
       source="https://media.futek.com/content/futek/files/pdf/productdrawings/llb130.pdf", ledger="AMF-226", role="axial force in the slim recording pen"),
    _b("R11", "pen", "Miniature S-beam load cell LSB200, 250 g (24 mm pen)", "FUTEK", "FSH03871", 1,
       source="https://media.futek.com/content/futek/files/pdf/productdrawings/lsb200.pdf", ledger="AMF-225", role="axial force in the 24 mm recording pen"),
    _b("R11", "pen", "6-axis IMU breakout, LSM6DSV16X", "class (any breakout exposing SPI and INT1)", "LSM6DSV16X", 2,
       ledger="OPT-37; OPT-92", role="pen motion at 1.92 kHz, in the pen tail"),
    _b("R11", "pen", "12-core ultra-flexible cable, 1.5 m, shielded", "class", "class", 2, role="pen head to the desk box (no electronics in the pen but the IMU)"),
    # ---------------------------------------------------------------- R12 coupon bench (G2)
    _b("R12", "standard", "3-axis force sensor K3D40 +-50 N (parasitic pull 12-36 N)", "ME-Messsysteme", "K3D40 +-50N", 1,
       source="https://www.instrumentation.it/gallery/6977/id_3-Axis_Force_Sensor_K3D40_20161005.pdf", ledger="AMF-224", role="stator force: pull and Lorentz force"),
    _b("R12", "standard", "3-axis force sensor K3D40 +-10 N (force-current map)", "ME-Messsysteme", "K3D40 +-10N", 1,
       source="https://www.instrumentation.it/gallery/6977/id_3-Axis_Force_Sensor_K3D40_20161005.pdf", ledger="AMF-224"),
    _b("R12", "all", "XYZ manual micrometre stage, 13-25 mm travel, 10 um graduation", "class", "class", 1, role="magnet position grid"),
    _b("R12", "all", "Two-axis goniometer, centre of rotation set to the coupon's pivot", "class", "class", 1, role="spherical-gap (C1S-type) coupons tilt about the pivot"),
    _b("R12", "all", "Thermal camera Lepton 3.5 (radiometric, 160 x 120)", "GroupGets (FLIR)", "500-0771-01", 1, "172.00", "USD", D,
       "https://groupgets.com/products/flir-lepton-3-5", "AMF-235", "hot-spot maps (temperatures from thermocouples and resistance)"),
    _b("R12", "all", "Linear Hall sensors as designed (DRV5055-A4) on the design's board geometry", "Texas Instruments", "DRV5055A4", 4,
       ledger="OPT-46", role="Hall interference test in their real neighbourhood"),
    # ---------------------------------------------------------------- R13 loaded-nib rig (G3, G4)
    _b("R13", "all", "Voice coil LVCM-032-025-02 (12.7 mm stroke, 9.3 N cont., 29.3 N peak)", "Moticont", "LVCM-032-025-02", 2,
       source="https://www.moticont.com/voice-coil-motor.htm", ledger="AMF-232", role="disturbance stage, one per axis"),
    _b("R13", "all", "Parallel-leaf flexure stage (spring-steel leaves, aluminium carriage)", "PROPOSED DESIGN", "mechanics/cad/rig_nib.py", 2,
       role="frictionless +-3 mm disturbance axis"),
    _b("R13", "standard", "One-axis linear table under R9's force plate (>= 100 mm travel, >= 100 mm/s, encoder), with a fixed bridge for the stage",
       "class", "class", 1, role="moves the paper under the fixed R13 stage for G3's straight strokes",
       notes="the rig hung from the printer head would weigh about 1.06 kg (CALC, rig_nib_summary.json); price not seen"),
    _b("R13", "all", "OPA548 current amplifiers for the disturbance voice coils", "Texas Instruments", "OPA548", 2, source="https://www.ti.com/product/OPA548", ledger="AMF-233"),
    _b("R13", "G4", "Chamber at 30 C for the long thermal run (the CORE One+ chamber, up to 55 C)", "Prusa Research", "(R9 frame)", 0,
       source="https://www.prusa3d.com/product/prusa-core-one/", ledger="AMF-231", notes="qualify its air speed and stability first"),
    # ---------------------------------------------------------------- R14 grip simulant (G5)
    _b("R14", "all", "Grip simulant: three pads with platinum-silicone skin, squeeze spring, translation springs, torsion spring", "PROPOSED DESIGN",
       "mechanics/cad/rig_grip.py", 1, role="grip translation and rotation compliance at 3 squeeze levels"),
    _b("R14", "all", "Mini load cell TAL221, 1000 g variant, for the squeeze force (2-8 N; the 100 g SEN-14727 would overload)",
       "HTC Sensor (via a distributor)", "TAL221 1000 g", 2, source="https://cdn.sparkfun.com/assets/9/9/a/f/3/TAL221.pdf",
       ledger="AMF-227", notes="data sheet lists 100-1500 g capacities; 1000 g price not seen"),
    _b("R14", "all", "Dummy module of equal mass, CoM and inertia (locked condition)", "PROPOSED DESIGN", "mechanics/cad/rig_grip.py", 1,
       role="the review's 'same mass locked' comparator"),
]


def write(path: str) -> int:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    return len(ROWS)


def seen_totals() -> Dict[str, float]:
    """Sum of the prices seen, per rig and build (a floor: unseen prices are not included)."""
    out: Dict[str, float] = {}
    for r in ROWS:
        if r["unit_price"] != NS and r["currency"] == "USD":
            try:
                q = float(r["qty"])
            except (TypeError, ValueError):
                q = 1.0
            key = f"{r['rig']}:{r['build']}"
            out[key] = out.get(key, 0.0) + q * float(r["unit_price"])
    return out
