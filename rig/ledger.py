"""Proposed evidence-ledger rows for study M (results/rig/evidence_rows.csv).

Only sources opened in this study on 2026-09-29 are listed; numbers are copied from what was
read (manufacturer pages and data sheets, a conference paper, a journal method section, a
PubMed abstract). The 23 columns match docs/evidence.csv exactly. Ids: AMF-220...238,
OPT-85...92, CON-100...101, HAP-140...141 (inside the ranges assigned to study M).
"""
from __future__ import annotations

import csv
from typing import Dict, List

COLUMNS = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
           "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings",
           "units_and_conditions", "locator", "limitations", "relevance_to_design", "transferability",
           "transferability_reason", "design_implication", "retrieved", "search_query", "stream",
           "lead_verification"]

MFR = dict(source_type="datasheet", evidence_class="manufacturer statement", access_level="full text",
           participants_or_bench="not applicable (manufacturer data; test method not published)", retrieved="2026-09-29",
           lead_verification="")


def _r(**kw) -> Dict[str, str]:
    row = {c: "" for c in COLUMNS}
    row.update(kw)
    return row


ROWS: List[Dict[str, str]] = [
    _r(id="AMF-220", topic="Rig DAQ microcontroller: PJRC Teensy 4.1",
       citation="PJRC. Teensy 4.1 Development Board, product page; SparkFun Electronics, Teensy 4.1 product page (DEV-16771).",
       year="n.d.", doi_or_url="https://www.pjrc.com/store/teensy41.html ; https://www.sparkfun.com/teensy-4-1.html",
       task_or_setup="Product specifications and a retail price", comparator="none",
       key_quantitative_findings="'ARM Cortex-M7 at 600 MHz'; '4 special timers are meant for decoding quadrature signals'; "
       "'A 32 bit counter increments every CPU clock cycle (600 MHz)'; USB device 480 Mbit/s; 7936K flash, 1024K RAM; "
       "55 digital I/O; on-chip ADC 'up to 12 bits ... only up to 10 bits are normally usable due to noise'; SDIO microSD. "
       "SparkFun DEV-16771: USD 31.50, in stock (seen 2026-09-29).",
       units_and_conditions="USD as displayed on the retailer page", locator="PJRC page, Technical Specifications; SparkFun product page",
       limitations="Price and stock change; the on-chip ADC is too coarse for bridge sensors",
       relevance_to_design="One clock for every rig channel (cycle counter); hardware quadrature decoding of the encoders; fast USB",
       transferability="high", transferability_reason="Catalogue data for the part used",
       design_implication="Stamp every sample with the cycle counter; read bridges with an external 24-bit ADC (AMF-221/222)",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items() if k != "source_type"}, source_type="manufacturer"),
    _r(id="AMF-221", topic="24-bit simultaneous-sampling ADC for the rig bridges: TI ADS131M04",
       citation="Texas Instruments. ADS131M04 4-Channel, Simultaneously-Sampling, 24-Bit, Delta-Sigma ADC. Data sheet SBAS890D (March 2019, revised May 2021); product page.",
       year="2021", doi_or_url="https://www.ti.com/lit/ds/symlink/ads131m04.pdf ; https://www.ti.com/product/ADS131M04",
       task_or_setup="Data sheet noise table and features", comparator="ADS131M08 (AMF-222), same noise table",
       key_quantitative_findings="4 simultaneously sampled differential inputs; data rate up to 64 kSPS; PGA 1-128; "
       "input-referred noise (Table 7-1, fCLKIN 8.192 MHz): 0.77 uVrms at 1 kSPS and 1.20 uVrms at 4 kSPS at gain 128 "
       "(3.38 and 5.35 uVrms at gain 1); 102 dB dynamic range at gain 1, 4 kSPS; crosstalk -120 dB; 3.3 mW; input "
       "impedance >= 1 MOhm at gains 8-128; channel phase calibration 244 ns steps. No price on the pages fetched.",
       units_and_conditions="TA 25 C, inputs shorted", locator="Features p.1; Table 7-1 (noise); product page",
       limitations="Noise with inputs shorted; bridge excitation noise and drift add; price not seen",
       relevance_to_design="Sets the electronic noise of the axial cell and the force plate (rig.uncertainty)",
       transferability="high", transferability_reason="Manufacturer specification of the proposed ADC family",
       design_implication="0.12 mN RMS per sample for a 1 N, 2 mV/V cell at 3.3 V (CALC); simultaneous sampling keeps channels aligned",
       search_query="direct URL; WebFetch of the product page", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-222", topic="ADS131M08 register map, SPI frame and the EVM used standalone",
       citation="Texas Instruments. ADS131M08 data sheet SBAS950B (October 2019, revised February 2021); ADS131M08 Evaluation Module user's guide SBAU334A (August 2019, revised December 2019).",
       year="2021", doi_or_url="https://www.ti.com/lit/ds/symlink/ads131m08.pdf ; https://www.ti.com/lit/ug/sbau334a/sbau334a.pdf",
       task_or_setup="Register map, SPI protocol, EVM headers, clock and supplies", comparator="ADS131M04 (AMF-221)",
       key_quantitative_findings="SPI mode 1 (CPOL 0, CPHA 1); a frame is 10 words (response, 8 channel words, CRC); "
       "default word 24 bit; CLOCK register 03h reset FF0Eh (all channels on, OSR 1024, high-resolution); OSR 128-16256; "
       "GAIN1/GAIN2 hold a 3-bit PGAGAIN per channel (111b = 128); commands RESET 0011h, STANDBY 0022h, WAKEUP 0033h, "
       "RREG 101a aaaa annn nnnn, WREG 011a aaaa annn nnnn; noise table as the ADS131M04. EVM: onboard 8.192 MHz CMOS "
       "oscillator (JP10 1-2, HR mode); digital header J10: SYNC/RESET, DIN, CLK, CS, SCLK, DRDY, DOUT, GND; AVDD external "
       "via JP12/TP2, DVDD via TP1 with R67 removed. No price on the pages fetched.",
       units_and_conditions="fCLKIN 8.192 MHz: data rate = 4.096 MHz / OSR", locator="SBAS950B Tables 8-12, 8-17, 8-18, 7-1; SBAU334A sections 2.2, 3.3, 4, Tables 4 and 6",
       limitations="EVM price not seen; the standalone wiring is a proposal to check at assembly",
       relevance_to_design="Firmware register values (rig_daq.ino) and the DAQ wiring",
       transferability="high", transferability_reason="Manufacturer documentation of the proposed parts",
       design_implication="Use the ADS131M08EVM without its PHI: Teensy SPI to J10, onboard oscillator, external 3.3 V supplies",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-223", topic="Reference 6-axis force sensor for R9/R12: ATI Nano17 calibrations",
       citation="ATI Industrial Automation. F/T Sensor Nano17, product page (calibration tables).", year="n.d.",
       doi_or_url="https://www.ati-ia.com/products/ft/ft_models.aspx?id=Nano17", task_or_setup="Calibration ranges and resolutions",
       comparator="ME K3D40 (AMF-224)",
       key_quantitative_findings="SI-12-0.12: Fx,Fy 12 N, Fz 17 N, Tx,Ty,Tz 120 N mm, resolution 1/320 N and 1/64 N mm; "
       "SI-25-0.25: 25 / 35 N, 1/160 N; SI-50-0.5: 50 / 70 N, 1/80 N. Resonance, overload and price not on the page fetched.",
       units_and_conditions="SI calibrations", locator="Calibration tables", limitations="Resolution, not accuracy; price not seen",
       relevance_to_design="The class named by bench_protocols.md R1/R4; the reference option of R9",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Keep as the reference build; the standard build uses the K3D40 3-axis plate under the paper",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-224", topic="3-axis force plate under the paper: ME-Messsysteme K3D40",
       citation="ME-Messsysteme GmbH. 3-Axis Force Sensor K3D40, variants +-2 N, +-10 N, +-20 N, +-50 N, data sheet 'Stand 5 Oct 2016' (distributor copy, Instrumentation Devices Srl).",
       year="2016", doi_or_url="https://www.instrumentation.it/gallery/6977/id_3-Axis_Force_Sensor_K3D40_20161005.pdf",
       task_or_setup="Technical data", comparator="ATI Nano17 (AMF-223)",
       key_quantitative_findings="40 x 40 x 20 mm, M3 threads, aluminium alloy; accuracy class 0.5 %; relative linearity error "
       "0.2 % FS; zero-signal hysteresis 0.1 % FS; temperature effect on zero 0.05 % FS/K, on characteristic value 0.05 % RD/K; "
       "creep 0.05 % FS; crosstalk x<->y 0.5 % FS, z->x/y 1 % FS; eccentric load 0.5 % FS/100 mm; rated displacement 0.1 mm; "
       "operating force 200 % FS; rated excitation 2.5-5 V; exact sensitivity only in the test report. Price not seen (the "
       "manufacturer shop page was behind a bot check).",
       units_and_conditions="Rated temperature -20 to 60 C", locator="Data sheet pp. 1, 3, 4",
       limitations="2016 distributor copy; sensitivity per unit; price not seen",
       relevance_to_design="Sets the uncertainty of the paper-normal and friction forces on R9 (rig.uncertainty)",
       transferability="high", transferability_reason="Manufacturer specification of the proposed sensor",
       design_implication="+-2 N variant for the ink-threshold series (U about 3.6 mN, CALC), +-10 N for the friction map; calibrate in situ at every angle",
       search_query="WebSearch: ME-Messsysteme K3D40 3-axis force sensor specifications; curl of the distributor PDF", stream="AMF",
       **{k: v for k, v in MFR.items()}),
    _r(id="AMF-225", topic="In-line axial refill-force cell: FUTEK LSB200 (10-250 g)",
       citation="FUTEK Advanced Sensor Technology. Model LSB200 Low Capacity Miniature S-Beam Jr. Load Cell, drawing FI1455-B.",
       year="n.d.", doi_or_url="https://media.futek.com/content/futek/files/pdf/productdrawings/lsb200.pdf",
       task_or_setup="Specifications and capacity table", comparator="FUTEK LLB130 (AMF-226), TAL221 (AMF-227)",
       key_quantitative_findings="Nonlinearity +-0.1 % RO; hysteresis +-0.1 % RO; nonrepeatability +-0.05 % RO; capacities "
       "10 g (0.1 N, 0.5 mV/V, 0.10 mm, 140 Hz), 20 g (0.2 N, 1 mV/V, 0.20 mm, 140 Hz), 50 g (0.5 N, 0.25 mm, 200 Hz), "
       "100 g (1.0 N, 2 mV/V, 0.20 mm, 300 Hz), 250 g (2.5 N, 0.18 mm, 530 Hz), item numbers FSH03867-FSH03871; safe overload "
       "1000 % RO; 19.3 g; 19.05 x 16.5 x 6.7 mm; temperature shift zero 0.018 % RO/C, span 0.036 % of load/C; 10 V max "
       "excitation; 1000 Ohm bridge. Price not seen.",
       units_and_conditions="Calibration at 5 VDC", locator="Drawing pages 1-3", limitations="Rated output of the 50 g and 250 g cells not legible in the extracted text",
       relevance_to_design="Measures the axial force F_c apart from the paper-normal force (review G1)",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="100 g cell for F_c <= 0.5 N (U about 1.9 mN after in-situ calibration, CALC); 250 g for heavier refills",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-226", topic="Button load cell for the slim recording pen: FUTEK LLB130",
       citation="FUTEK. Model LLB130 Miniature Load Button Load Cell, product drawing (2025 terms).", year="2025",
       doi_or_url="https://media.futek.com/content/futek/files/pdf/productdrawings/llb130.pdf", task_or_setup="Specifications",
       comparator="LSB200 (AMF-225)",
       key_quantitative_findings="Diameter 9.5 mm, height 3.3 mm; nonlinearity +-0.5 % RO; hysteresis +-0.5 % RO; "
       "nonrepeatability +-0.1 % RO; rated output 2 mV/V, 1 mV/V for 1000 g and 5 lb; deflection 0.013 mm nominal; 8.5 g; "
       "safe overload 150 % RO; 17-4 PH steel; IP64. Price not seen.",
       units_and_conditions="5 VDC calibration", locator="Drawing page 2", limitations="+-0.5 % of 1000 g is +-49 mN: adequate for writing-force statistics, not for ink thresholds",
       relevance_to_design="Axial force in a 12-16 mm recording pen where the LSB200 does not fit",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Use in the slim recording pen only; ink-force thresholds are measured on R9 with the LSB200",
       search_query="WebSearch: FUTEK LLB130 subminiature load button; curl of the drawing", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-227", topic="Low-cost bridge load cell: TAL221 (100-1500 g)",
       citation="HTC Sensor. TAL221 Miniature Load Cell data sheet (via SparkFun); SparkFun Mini Load Cell - 100g, Straight Bar (TAL221), SEN-14727.",
       year="n.d.", doi_or_url="https://cdn.sparkfun.com/assets/9/9/a/f/3/TAL221.pdf ; https://www.sparkfun.com/mini-load-cell-100g-straight-bar-tal221.html",
       task_or_setup="Specifications and retail price", comparator="LSB200 (AMF-225)",
       key_quantitative_findings="Rated output 0.6 +- 0.15 mV/V (100-200 g), 0.7 (300-750 g), 1.0 (1000-1500 g); combined "
       "error 0.05 % FS; non-linearity, hysteresis, repeatability +-0.05 % FS; creep +-0.05 % FS/3 min; zero balance +-0.1 % FS; "
       "temperature coefficients +-0.1 % FS/10 C; excitation <= 6 V; safe overload 150 %; 47 x 12 x 6 mm (SparkFun). "
       "SEN-14727 (100 g): USD 14.50 (seen 2026-09-29).",
       units_and_conditions="USD as displayed", locator="Data sheet specification table; SparkFun page",
       limitations="Parallel-beam cell; load must be perpendicular to its length; no traceable calibration",
       relevance_to_design="Low-cost axial and squeeze-force channels (R9 low-cost build, R14 grip squeeze)",
       transferability="medium", transferability_reason="Hobby-grade part; performance to be checked in situ",
       design_implication="Acceptable where a 0.5 mN-class combined error suffices after in-situ calibration",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-228", topic="Low-cost bridge ADC: Adafruit NAU7802 breakout",
       citation="Adafruit Industries. Adafruit NAU7802 24-Bit ADC - STEMMA QT / Qwiic, product 4538.", year="n.d.",
       doi_or_url="https://www.adafruit.com/product/4538", task_or_setup="Product page", comparator="ADS131M08 (AMF-222)",
       key_quantitative_findings="24-bit differential ADC with gain and calibration circuitry for Wheatstone bridges; 2 channels; "
       "I2C; USD 5.95 (seen 2026-09-29). Maximum sample rate and noise not on the page (NAU7802 data sheet not opened).",
       units_and_conditions="USD as displayed", locator="Product page", limitations="Rate and noise unverified here",
       relevance_to_design="Low-cost build of the quasi-static channels (ink thresholds at constant speed)",
       transferability="medium", transferability_reason="Retail page only",
       design_implication="Use only for quasi-static channels; dynamic channels need the ADS131M08",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-229", topic="Reference XY truth stage for page sensing: Zaber X-LDM110C",
       citation="Zaber Technologies. X-LDM110C-AE54D12 linear motor stage, specifications page.", year="n.d.",
       doi_or_url="https://www.zaber.com/products/linear-stages/X-LDM-AE/specs?part=X-LDM110C-AE54D12",
       task_or_setup="Specifications and list price", comparator="X-LSM100A-E03 (AMF-230)",
       key_quantitative_findings="USD 9,255; travel 110 mm; linear analog encoder, 1 nm count; accuracy 1 um unidirectional; "
       "repeatability < 0.08 um; maximum speed 1200 mm/s; peak thrust 60 N; maximum acceleration 24.5 m/s^2; 4.84 kg, moving "
       "mass 2.29 kg; maximum centred load 185 N; built-in controller.",
       units_and_conditions="USD list price as displayed (seen 2026-09-29)", locator="Specifications page",
       limitations="List price; the encoder is read through the controller (not verified that it can be tapped by the rig DAQ)",
       relevance_to_design="Page-sensor truth with TUR >> 4 against 10 um (CALC)",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Reference build of R10: two stacked stages; otherwise LM13 encoders or a strobed camera",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-230", topic="Rejected stage: Zaber X-LSM100A-E03 (too slow for writing speeds)",
       citation="Zaber Technologies. X-LSM100A-E03 linear stage, specifications page.", year="n.d.",
       doi_or_url="https://www.zaber.com/products/linear-stages/X-LSM-E/specs?part=X-LSM100A-E03",
       task_or_setup="Specifications and list price", comparator="X-LDM110C (AMF-229)",
       key_quantitative_findings="USD 2,871; 101.6 mm; rotary quadrature encoder 200 CPR; accuracy 35 um; repeatability < 3 um; "
       "backlash < 12 um; maximum speed 26 mm/s; thrust 25 N continuous, 55 N peak; built-in controller.",
       units_and_conditions="USD list price as displayed (seen 2026-09-29)", locator="Specifications page",
       limitations="List price", relevance_to_design="Writing speeds reach about 100 mm/s (LIT CON-20); 26 mm/s is too slow",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Not used for R9/R10 writing motion", search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}),
    _r(id="AMF-231", topic="Low-cost writing-motion frame: Prusa CORE One+ (CoreXY)",
       citation="Prusa Research. Prusa CORE One+ (Gen 2), product page.", year="n.d.",
       doi_or_url="https://www.prusa3d.com/product/prusa-core-one/", task_or_setup="Product page", comparator="Zaber stages (AMF-229, AMF-230)",
       key_quantitative_findings="CoreXY with dual fixed motors and a continuous belt loop; build volume 250 x 220 x 270 mm; "
       "USD 925 (kit), USD 1,202.78 (assembled) (seen 2026-09-29); open-source firmware on GitHub, CAD published; active "
       "chamber temperature control up to 55 C. No speed, acceleration or accuracy figures on the page.",
       units_and_conditions="USD as displayed", locator="Product page", limitations="No motion accuracy stated; belt drive",
       relevance_to_design="The head moves in XY while the bed (force plate) stays still in XY: the R9/R10/R13 frame",
       transferability="medium", transferability_reason="Consumer machine used as a motion frame",
       design_implication="Replace the print head by the rig heads; measure motion with LM13 encoders (OPT-89); the heated chamber can host the 30 C thermal runs",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-232", topic="Voice coils for the disturbance stage and the refill-force axis: Moticont LVCM family",
       citation="Moticont. Voice coil motor index page (housed linear voice coil motors).", year="n.d.",
       doi_or_url="https://www.moticont.com/voice-coil-motor.htm", task_or_setup="Catalogue listing", comparator="AMF-02 (LVCM-013 family)",
       key_quantitative_findings="LVCM-032-025-02: 31.8 mm housing, 0.50 in stroke, 9.3 N continuous, 29.3 N peak; "
       "LVCM-025-038-01: 0.37 in, 11 N / 34.7 N; LVCM-038-038-02: 0.38 in, 24.9 N / 78.8 N; LVCM-019-022-02: 0.5 in, "
       "2.3 N / 7.1 N. No prices listed.",
       units_and_conditions="Catalogue ratings", locator="Voice coil motor page, 19-38 mm housings",
       limitations="Force constant and resistance are on each drawing (not read here); no prices",
       relevance_to_design="R13 disturbance stage force budget (CALC in rig.frf.envelope_limits)",
       transferability="high", transferability_reason="Manufacturer catalogue",
       design_implication="LVCM-032-025-02 per disturbance axis: 12.7 mm stroke covers +-2 mm with margin",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-233", topic="Linear current amplifier for coils and voice coils: TI OPA548",
       citation="Texas Instruments. OPA548 High-Voltage, High-Current Operational Amplifier, product page.", year="n.d.",
       doi_or_url="https://www.ti.com/product/OPA548", task_or_setup="Key features", comparator="DRV8214 PWM driver (AMF-37)",
       key_quantitative_findings="3 A continuous, 5 A peak; single supply 8-60 V or dual +-4 to +-30 V; slew 10 V/us; GBW 1 MHz; "
       "current limit adjustable 0-5 A by resistor or digitally; thermal shutdown with an enable/status pin; TO-220-7 and DDPAK. No price shown.",
       units_and_conditions="Typical values", locator="Product page features", limitations="Linear dissipation must be heat-sunk",
       relevance_to_design="A PWM-free current source for the coupon map and the Hall-interference baseline",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Howland-type or sense-resistor current loop per axis; the pen's own driver is tested separately",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-234", topic="Thermocouple interface: Adafruit MAX31856 breakout",
       citation="Adafruit Industries. Universal Thermocouple Amplifier MAX31856 Breakout, product 3263.", year="n.d.",
       doi_or_url="https://www.adafruit.com/product/3263", task_or_setup="Product page", comparator="coil resistance thermometry",
       key_quantitative_findings="Types K, J, N, R, S, T, E, B; resolution 0.0078125 C; SPI; cold-junction compensation; USD 17.50 (seen 2026-09-29).",
       units_and_conditions="USD as displayed", locator="Product page", limitations="Accuracy depends on the thermocouple (the page quotes +-2 to +-6 C for many thermocouples)",
       relevance_to_design="Magnet, housing and web temperatures (G2, G4 thermal run)", transferability="high",
       transferability_reason="Retail product page", design_implication="Type-T fine wire, calibrated in a dry block; coil by resistance",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-235", topic="Low-cost thermal camera: FLIR Lepton 3.5",
       citation="GroupGets. FLIR Lepton 3.5, product page (part 500-0771-01).", year="n.d.",
       doi_or_url="https://groupgets.com/products/flir-lepton-3-5", task_or_setup="Product page", comparator="R4 class (>= 320 x 240, NETD <= 50 mK)",
       key_quantitative_findings="USD 172.00 (seen 2026-09-29); 160 x 120 pixels; 57 deg lens; radiometric. NETD, frame rate and radiometric accuracy not on the page.",
       units_and_conditions="USD as displayed", locator="Product page", limitations="Below the protocol's 320 x 240 class; accuracy not stated here",
       relevance_to_design="Hot-spot maps only; temperatures from thermocouples and coil resistance", transferability="medium",
       transferability_reason="Retail page", design_implication="Low-cost build: map, do not measure, with it",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-236", topic="Ink scanner: Epson Perfection V850 Pro (V600 discontinued)",
       citation="Epson America. Perfection V850 Pro Photo Scanner (B11B224201) and Perfection V600 (B11B198011) product pages.", year="n.d.",
       doi_or_url="https://epson.com/For-Work/Scanners/Photo-and-Graphics/Epson-Perfection-V850-Pro-Photo-Scanner/p/B11B224201 ; https://epson.com/For-Home/Scanners/Photo-Scanners/Epson-Perfection-V600-Photo-Scanner/p/B11B198011",
       task_or_setup="Product pages", comparator="bench_protocols.md R3 (4800 dpi, >= 40 lp/mm)",
       key_quantitative_findings="V850 Pro: USD 1,999.00; 6400 dpi optical with dual lenses (4800 and 6400 dpi); hardware "
       "4800 x 9600 and 6400 x 9600 dpi; 48 bit; 8.5 x 11.7 in; Dmax 4.0. V600: discontinued (no price), 6400 dpi optical.",
       units_and_conditions="USD as displayed (seen 2026-09-29)", locator="Product pages", limitations="Nominal resolution; R3 requires a USAF-1951 check",
       relevance_to_design="Ink continuity and ink path metrology (R3)", transferability="high", transferability_reason="Manufacturer pages",
       design_implication="V850 Pro for path metrology; any 2400 dpi flatbed suffices for gap fractions",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-237", topic="Firmware toolchain: Teensyduino 1.62",
       citation="PJRC. Teensyduino download and install page.", year="n.d.", doi_or_url="https://www.pjrc.com/teensy/td_download.html",
       task_or_setup="Toolchain versions", comparator="none",
       key_quantitative_findings="Current version Teensyduino 1.62; Arduino IDE 2.0.4 and later supported, 2.3.10 or later "
       "recommended; Boards Manager URL https://www.pjrc.com/teensy/package_teensy_index.json; legacy installers for Arduino 1.8.x.",
       units_and_conditions="Seen 2026-09-29", locator="Download page", limitations="Versions change",
       relevance_to_design="Exact dependency for building rig/firmware", transferability="high", transferability_reason="Vendor page",
       design_implication="Build the sketches with Teensyduino 1.62 in Arduino IDE >= 2.3.10",
       search_query="direct URL", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="AMF-238", topic="Hardware quadrature decoding on the Teensy 4.1: QuadEncoder library",
       citation="Teensy-4.x-Quad-Encoder-Library, README (github.com/PaulStoffregen/Teensy-4.x-Quad-Encoder-Library).", year="n.d.",
       doi_or_url="https://github.com/PaulStoffregen/Teensy-4.x-Quad-Encoder-Library", task_or_setup="Library README and header name",
       comparator="PJRC Encoder library (interrupt based)",
       key_quantitative_findings="4 hardware encoder channels; Teensy 4.1 pins 0-8, 30, 31, 33 and 37; pins 0, 5 and 37 share a "
       "crossbar connection (exclusive), so do 1/36; constructor QuadEncoder(encoder_ch, PhaseA_pin, PhaseB_pin, pin_pus, "
       "index_pin, home_pin, trigger_pin); setInitConfig(), init(), read(), write(). The README example includes "
       "'Quadencoder.h', but the file in the repository is QuadEncoder.h (raw URL checked: 200 for QuadEncoder.h, 404 for "
       "Quadencoder.h).",
       units_and_conditions="Seen 2026-09-29", locator="README lines 4-21 and example", limitations="Whether Teensyduino 1.62 bundles it was not verified",
       relevance_to_design="Encoder counts latched in the ADC interrupt on one clock", transferability="high", transferability_reason="Library source",
       design_implication="#include <QuadEncoder.h> (case matters on Linux); encoders on pins 2/3, 4/7, 8/30, 31/33",
       search_query="WebFetch of the GitHub page; curl of the raw README and header", stream="AMF", **{k: v for k, v in MFR.items()}, ),
    _r(id="OPT-85", topic="DeltaPen's translation-error metric: what is compared per 10 ms window",
       citation="Luethi G, Fender AR, Holz C (2022). DeltaPen: A Device with Integrated High-Precision Translation and Rotation Sensing on Passive Surfaces. UIST '22 (section 4.4, Translation errors).",
       year="2022", doi_or_url="https://doi.org/10.1145/3526113.3545655 ; https://static.siplab.org/papers/uist2022-deltapen.pdf",
       source_type="conference", evidence_class="physical human study", access_level="full text",
       task_or_setup="Offline comparison of DeltaPen motion with the Wacom Intuos 4 position differences",
       participants_or_bench="10 participants; 209,986 data points after cleaning (as OPT-02)",
       comparator="Wacom tablet deltas (translation); OptiTrack (angle)",
       key_quantitative_findings="Verbatim: 'When reading movements (DeltaPen) and taking the position differences (Wacom) at "
       "every 10 ms, then the Mean Absolute Error (MAE) for the magnitude of the translation is 0.0683 mm (Median = 0.0236).' "
       "'As opposed to the magnitude error above, the X and Y separation is inherently dependent of the pen rotation', so X "
       "and Y errors were computed after compensating the absolute pen rotation. Flow sensors at 1000 Hz, 6000 dpi nominal; "
       "data kept only within about 1 cm of the surface with a clear OptiTrack view.",
       units_and_conditions="mm per 10 ms window; Wacom surface, not paper", locator="Sec. 4.1, 4.3, 4.4 (p. 8), Sec. 3.1",
       limitations="Reading of the metric: the magnitude error is rotation-invariant, i.e. | |d_pen| - |d_wacom| |, not the norm of the vector difference; the text does not give a formula",
       relevance_to_design="Like-for-like comparison of our page sensor with DeltaPen",
       transferability="medium", transferability_reason="Tablet surface; the metric definition transfers",
       design_implication="Report both the magnitude error (DeltaPen's) and the vector error (EXP-S01's) per 10 ms window, plus per-sample and stroke errors (rig.pagesense)",
       retrieved="2026-09-29", search_query="curl https://static.siplab.org/papers/uist2022-deltapen.pdf", stream="OPT", lead_verification=""),
    _r(id="OPT-86", topic="Tablet protocol hardware: Wacom Intuos Pro Paper Edition and ink pens",
       citation="Wacom. Wacom Intuos Pro fact sheet (FS_PTH_EN_WEG_19C).", year="n.d.",
       doi_or_url="https://estore.wacom.com/media/sebwite/productdownloads/i/n/intuos_pro_factsheet_en_weg_2.pdf",
       source_type="manufacturer", evidence_class="manufacturer statement", access_level="full text",
       task_or_setup="Model table and accessories", participants_or_bench="not applicable (manufacturer data)", comparator="Intuos Pro (2025) (OPT-87)",
       key_quantitative_findings="Paper Edition medium PTH-660P and large PTH-860P (A5 / A4, up to 10 sheets); Wacom Finetip Pen: "
       "pressure-sensitive, 0.4 mm gel ink, 8,192 levels (included with Paper Editions); Wacom Ballpoint Pen: pressure-sensitive, "
       "1.0 mm oil ink, 8,192 levels (sold separately); Pro Pen 2 8192 levels; pen tilt '+-60 levels / 60 degrees'; active area "
       "224 x 148 mm (M). No report rate or accuracy in the fact sheet.",
       units_and_conditions="Catalogue", locator="Pages 1-2, model and accessory tables", limitations="Availability in 2026 not checked; no rate or accuracy",
       relevance_to_design="Real ink on real paper with the nib position, pressure and tilt recorded: no build needed",
       transferability="medium", transferability_reason="Consumer tablet; not our grip or mass",
       design_implication="Tablet protocol (rig/tablet/tablet_recorder.html) for EXP-H01 before the recording pen exists",
       retrieved="2026-09-29", search_query="WebSearch: Wacom Intuos Pro Paper Edition Finetip; curl of the fact sheet", stream="OPT", lead_verification=""),
    _r(id="OPT-87", topic="Current Wacom Intuos Pro (2025): no paper mode listed",
       citation="Wacom. Wacom Intuos Pro (2025) product page.", year="2025", doi_or_url="https://www.wacom.com/en-us/products/pen-tablets/wacom-intuos-pro",
       source_type="manufacturer", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Specifications",
       participants_or_bench="not applicable (manufacturer data)", comparator="Paper Edition (OPT-86)",
       key_quantitative_findings="Models PTK470/670/870; Pro Pen 3; 8,192 pressure levels; +-60 deg tilt; 5,080 lpi; active area "
       "187 x 105 / 263 x 148 / 349 x 195 mm. No paper mode or ink pen, report rate, accuracy or price on the page.",
       units_and_conditions="Catalogue", locator="Product page", limitations="Page summary only",
       relevance_to_design="The tablet protocol needs the Paper Edition (or another EMR tablet with an inking pen)",
       transferability="medium", transferability_reason="Consumer product page", design_implication="Buy a Paper Edition while available, or use any EMR tablet with an ink pen of the same technology (to verify)",
       retrieved="2026-09-29", search_query="direct URL", stream="OPT", lead_verification=""),
    _r(id="OPT-88", topic="Camera ground truth: OV9281 global-shutter camera in external-trigger mode",
       citation="Arducam. OV9281 Global Shutter: external trigger mode (UVC camera application note).", year="n.d.",
       doi_or_url="https://docs.arducam.com/UVC-Camera/Appilcation-Note/External-Trigger-Mode/OV9281-Global-Shutter/",
       source_type="manufacturer", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Application note",
       participants_or_bench="not applicable (manufacturer data)", comparator="encoder truth (OPT-89), Zaber (AMF-229)",
       key_quantitative_findings="Frame output on the rising edge of the trigger; trigger pulse width >= 2 us; 'the frame rate "
       "of the camera module can reach 100fps in external trigger mode' with manual, shortest exposure; trigger on pin F, ground on pin G. "
       "No latency or jitter figure; no price seen (vendor shop pages refused the fetch).",
       units_and_conditions="External trigger mode", locator="Application note", limitations="Exposure delay after the trigger not stated: calibrate with the strobe",
       relevance_to_design="100 fps matches DeltaPen's 10 ms windows; the DAQ triggers the frames on its clock",
       transferability="medium", transferability_reason="Vendor note", design_implication="Strobe the LED inside the exposure; stamp the strobe time",
       retrieved="2026-09-29", search_query="WebSearch: Arducam OV9281 external trigger", stream="OPT", lead_verification=""),
    _r(id="OPT-89", topic="Encoder truth on the CoreXY and the disturbance stage: RLS LM13",
       citation="RLS (Renishaw associate company). LM13 incremental magnetic encoder system, data sheet LM13D02_05, Issue 5, 16 May 2018.",
       year="2018", doi_or_url="https://www.renishaw.com/resourcecentre/download/lm13-magnetic-encoder-system--103312?userLanguage=en",
       source_type="datasheet", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Technical specifications",
       participants_or_bench="not applicable (manufacturer data)", comparator="Zaber X-LDM encoder (AMF-229)",
       key_quantitative_findings="Pole length 2 mm; resolutions about 0.244 um (13B, 8192 counts per 2 mm) to 250 um; maximum speed "
       "per resolution and minimum edge separation (13B: 1.82 m/s at 0.07 us); MS scale accuracy grade +-10 um (up to 20 m), +-20 or "
       "+-40 um; repeatability better than the resolution in the same direction; hysteresis < 4 um up to 0.5 mm ride height; "
       "scale expansion about 17e-6/K; readhead 80 g. Sub-divisional error not found in the pages read; no price.",
       units_and_conditions="Linear application, digital output", locator="Technical specifications table (p. 4)",
       limitations="SDE not stated; hysteresis matters at tremor reversals",
       relevance_to_design="Low-cost truth: U about 2.6 um per 10 ms window (CALC), TUR 3.8 against 10 um",
       transferability="high", transferability_reason="Manufacturer specification",
       design_implication="Use 13B resolution; qualify SDE and hysteresis against the Zaber stage or an interferometer once",
       retrieved="2026-09-29", search_query="WebSearch: RLS LM13 datasheet; curl of the Renishaw copy", stream="OPT", lead_verification=""),
    _r(id="OPT-90", topic="Page-sensor candidate board: Pimoroni PAA5100JE breakout (PIM573)",
       citation="Pimoroni. PAA5100JE Near Optical Flow SPI Breakout, product page (PIM573).", year="n.d.",
       doi_or_url="https://shop.pimoroni.com/products/paa5100je-optical-tracking-spi-breakout", source_type="manufacturer",
       evidence_class="manufacturer statement", access_level="full text", task_or_setup="Product page",
       participants_or_bench="not applicable (manufacturer data)", comparator="PAA5100JE data sheet (OPT-05); PMW3360 (OPT-54)",
       key_quantitative_findings="Tracking range 15-35 mm; 242 frames/s; maximum speed 1.14 m/s at 25 mm; field of view 42 deg; SPI; "
       "6 mA; two white LEDs; about 24 x 24.5 x 5 mm. Price not displayed (out of stock or pre-order when seen).",
       units_and_conditions="Seen 2026-09-29", locator="Product page", limitations="Far-field optics: not a near-nib sensor",
       relevance_to_design="A ready board for the barrel-mount option in R10's candidate list", transferability="medium",
       transferability_reason="Retail page", design_implication="Test at 15-35 mm heights only", retrieved="2026-09-29",
       search_query="direct URL", stream="OPT", lead_verification=""),
    _r(id="OPT-91", topic="Availability of mouse-sensor boards: JACK Enterprises PMW3360 and PMW3389 boards retired",
       citation="Tindie listings 'PMW3360 Motion Sensor' and 'PMW3389 Motion Sensor' (JACK Enterprises).", year="n.d.",
       doi_or_url="https://www.tindie.com/products/jkicklighter/pmw3360-motion-sensor/ ; https://www.tindie.com/products/jkicklighter/pmw3389-motion-sensor/",
       source_type="marketplace", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Marketplace listings",
       participants_or_bench="not applicable", comparator="PMW3360 data sheet (OPT-54)",
       key_quantitative_findings="Both listings retired, 'no longer available for sale', with a pointer to another vendor; last price "
       "USD 29.99 (1-2 units). PMW3360 board: up to 250 ips, 100-12,000 CPI, 50 g; PMW3389 board: up to 16,000 CPI, 400 ips, 50 g; "
       "both with focusing lens and regulator; SPI with motion interrupt.",
       units_and_conditions="Seen 2026-09-29", locator="Listing pages", limitations="Marketplace; availability only",
       relevance_to_design="R10 must accept sensor boards from any source (driver hooks, not one board)", transferability="medium",
       transferability_reason="Availability changes", design_implication="Keep the sensor interface generic (SPI + motion line)",
       retrieved="2026-09-29", search_query="direct URL", stream="OPT", lead_verification=""),
    _r(id="OPT-92", topic="IMU registers for the recording pen: ST lsm6dsv16x-pid driver header",
       citation="STMicroelectronics. lsm6dsv16x-pid platform-independent driver, lsm6dsv16x_reg.h (GitHub).", year="n.d.",
       doi_or_url="https://github.com/STMicroelectronics/lsm6dsv16x-pid", source_type="manufacturer", evidence_class="manufacturer statement",
       access_level="full text", task_or_setup="Register definitions", participants_or_bench="not applicable", comparator="LSM6DSV16X data sheet (OPT-37)",
       key_quantitative_findings="WHO_AM_I 0x0F reads 0x70; CTRL1 0x10 (odr_xl bits 3:0, op_mode_xl bits 6:4); CTRL2 0x11 (odr_g); "
       "CTRL3 0x12 (sw_reset bit 0, if_inc bit 2, bdu bit 6, boot bit 7); CTRL6 0x15 (fs_g bits 3:0; 1000 dps 0x3, 2000 dps 0x4); "
       "CTRL8 0x17 (fs_xl bits 1:0; 4 g 0x1, 16 g 0x3); STATUS_REG 0x1E; OUT_TEMP_L 0x20; OUTX_L_G 0x22; OUTX_L_A 0x28; ODR codes "
       "0x9 960 Hz, 0xA 1.92 kHz, 0xB 3.84 kHz, 0xC 7.68 kHz.",
       units_and_conditions="Register map", locator="lsm6dsv16x_reg.h lines 188-764 and the ODR/full-scale enums",
       limitations="Sensitivities (mg/LSB, mdps/LSB) not in the header; the ST data sheet download was refused here",
       relevance_to_design="rig_daq.ino IMU option (recording pen)", transferability="high", transferability_reason="Vendor driver source",
       design_implication="Scale factors from the data sheet (OPT-37) before use; the firmware logs raw counts",
       retrieved="2026-09-29", search_query="curl raw.githubusercontent.com/STMicroelectronics/lsm6dsv16x-pid/main/lsm6dsv16x_reg.h",
       stream="OPT", lead_verification=""),
    _r(id="CON-100", topic="Refill types and formats for the G1 matrix: Schmidt refill range",
       citation="Schmidt Technology GmbH. Refills (writing instruments technology), product page.", year="n.d.",
       doi_or_url="https://www.schmidttechnology.de/en/products/writing-instruments-technology-2/refills/",
       source_type="manufacturer", evidence_class="manufacturer statement", access_level="full text", task_or_setup="Product range",
       participants_or_bench="not applicable (manufacturer data)", comparator="ISO 12757-1 formats (CON-21, CON-22)",
       key_quantitative_findings="Ballpoint S 635 (D format, M/F) and P 900 (G2); hybrid easyFLOW 9000 (G2, 0.8 or 1.0 mm TC ball); "
       "capless ceramic rollerball P 8126 (0.6 mm, 97.5 mm long) and Mini Capless 8126 (0.6 mm, 76 mm); safety ceramic rollerball "
       "SRC 5888 F/M (110.6 mm); fineliner FL 6040 F/M (0.8/1.0 mm extruded, spring-loaded, 110.6 mm); pressurised S 620 (D format).",
       units_and_conditions="Catalogue", locator="Refills page", limitations="No writing-force, line-width or ink-flow data; no gel D1 refill in the range",
       relevance_to_design="Four ink systems in D and G2 formats from one maker for the G1 matrix",
       transferability="high", transferability_reason="Real refills that fit study B's candidates (D in a 12-16 mm core, G2/capless in the 24 mm pen)",
       design_implication="G1 refill set: S 635 (ballpoint, D), easyFLOW 9000 (hybrid, G2), P 8126 (rollerball), FL 6040 F (fineliner); add a gel D1 refill from another maker",
       retrieved="2026-09-29", search_query="WebSearch: Schmidt refill ISO 12757-2 D1; WebFetch of the refills page", stream="CON", lead_verification=""),
    _r(id="CON-101", topic="Axial and normal pen force measured separately: Schomaker and Plamondon's method",
       citation="Schomaker LRB, Plamondon R (1990). The relation between pen force and pen-point kinematics in handwriting. Biological Cybernetics 63:277-289 (author preprint, Introduction and Methods).",
       year="1990", doi_or_url="https://doi.org/10.1007/BF00203451 ; https://www.ai.rug.nl/~lambert/papers/pen-pressure.pdf",
       source_type="journal", evidence_class="physical human study", access_level="full text",
       task_or_setup="Axial pen force from a strain-gauge stylus on a Calcomp 9000 tablet; a modified controller gave pen angle",
       participants_or_bench="Main study as CON-01; APF-NPF check on 4 subjects", comparator="Normal pen force under the writing surface",
       key_quantitative_findings="APF: transducer in the pen, along its longitudinal axis; NPF: transducer under the writing surface; "
       "eq. (1) F_N(t) = -F_A(t) sin(phi(t)), phi the pen-to-plane angle. Stylus: strain-gauge transducer 0-10 N, normal ballpoint refill "
       "in tight contact, second-order Butterworth -3 dB at 17.5 Hz, 10-bit ADC; tablet 105.2 Hz, 0.025 mm resolution, 0.25 mm "
       "accuracy. With pen angle known to 3 deg, 'Recordings (T=9 s) never revealed correlations below 0.96 between axial and normal pen force' (N = 4); pen-angle variation about 2.5 deg around 50 deg.",
       units_and_conditions="N; Hz; mm", locator="Preprint pp. 2-3 (definitions, eq. 1), p. 7 (Materials), p. 16 (APF-NPF check)",
       limitations="Eq. (1) assumes the whole pen force acts along the axis; a spring-loaded refill in a guided nib does not satisfy it (P-7)",
       relevance_to_design="The review's instruction to keep axial and normal forces separate",
       transferability="high", transferability_reason="Measurement method transfers directly",
       design_implication="R9 and the recording pen measure F_a in the pen and N under the paper; rig.contact.apf_npf reports the residual of eq. (1)",
       retrieved="2026-09-29", search_query="curl https://www.ai.rug.nl/~lambert/papers/pen-pressure.pdf", stream="CON", lead_verification=""),
    _r(id="HAP-140", topic="Grip force relative to writing force: grip-to-normal ratio",
       citation="Chau T, Ji J, Tam C, Schwellnus H (2006). A novel instrument for quantifying grip activity during handwriting. Arch Phys Med Rehabil 87(11):1542-1547.",
       year="2006", doi_or_url="https://doi.org/10.1016/j.apmr.2006.08.328 ; PMID 17084133", source_type="journal",
       evidence_class="physical human study", access_level="abstract", task_or_setup="Instrumented writing utensil recording barrel grip forces and normal force",
       participants_or_bench="6 children with spastic hemiplegic cerebral palsy and 6 without handwriting difficulties", comparator="between groups",
       key_quantitative_findings="Correlation between normal and grip forces 0.55 +- 0.16; delay between normal and grip forces "
       "97.7 +- 16 ms; 'a consistent grip-to-normal force ratio (4.3 +- 1.5), across all participants'.",
       units_and_conditions="ratio of forces", locator="Abstract (PubMed E-utilities)", limitations="Children, small sample, abstract only",
       relevance_to_design="Sets the grip-strength levels of the R14 simulant relative to the writing force",
       transferability="low", transferability_reason="Children; adult values unknown here",
       design_implication="Simulant squeeze 2, 4 and 8 N (about 4.3 x 0.5, 1 and 2 N of writing force; derived), to be replaced by EXP-B06/I01 measurements",
       retrieved="2026-09-29", search_query="WebSearch: grip normal force ratio handwriting; efetch PMID 17084133", stream="HAP", lead_verification=""),
    _r(id="HAP-141", topic="Instrumented pen with barrel grip sensors: method precedent",
       citation="Ghali B, Thalanki Anantha N, Chan J, Chau T (2013). Variability of grip kinetics during adult signature writing. PLoS ONE 8(5):e63216.",
       year="2013", doi_or_url="https://doi.org/10.1371/journal.pone.0063216", source_type="journal", evidence_class="physical human study",
       access_level="full text", task_or_setup="Signatures with a barrel-sensing pen on a Wacom Cintiq 12WX",
       participants_or_bench="20 adults; 11,040 signatures over 10 days", comparator="within and between participants",
       key_quantitative_findings="64 Tekscan 9811 force sensors on the barrel (32 analysed) sampled at 250 Hz; pen 24 g, 1.3 cm diameter, "
       "14 cm long; the Cintiq recorded axial force, tip position and angles at 105 Hz; each sensor calibrated by loading and unloading "
       "(6 repetitions) with a second-order polynomial. No mean grip force in newtons found in the text read.",
       units_and_conditions="Hz, g, cm", locator="Methods (instrumentation, calibration)", limitations="Signatures, not writing tasks; no force values extracted",
       relevance_to_design="Grip sensing and calibration practice for the recording pen and the R14 simulant pads",
       transferability="medium", transferability_reason="Adults, pen-sized instrument",
       design_implication="Calibrate barrel sensors in situ with a loading/unloading cycle; log the tablet's own axial force alongside",
       retrieved="2026-09-29", search_query="WebSearch: pen grip force during handwriting instrumented pen; curl of the PLoS page", stream="HAP", lead_verification=""),
]


# vocabulary of docs/evidence.csv for web pages and documentation
_OVERRIDE = {
    "manufacturer web page|product page": ["AMF-220", "AMF-228", "AMF-229", "AMF-230", "AMF-231", "AMF-232", "AMF-233",
                                           "AMF-234", "AMF-235", "AMF-236", "OPT-87", "OPT-90"],
    "documentation|full text (web page)": ["AMF-237", "AMF-238", "OPT-88", "OPT-92"],
    "website|product page": ["OPT-91"],
    "manufacturer web page|full text (web page)": ["CON-100"],
}
for _k, _ids in _OVERRIDE.items():
    _st, _al = _k.split("|")
    for _r0 in ROWS:
        if _r0["id"] in _ids:
            _r0["source_type"], _r0["access_level"] = _st, _al
for _r0 in ROWS:
    if _r0["id"] == "HAP-140":
        _r0["access_level"] = "abstract only"


def write(path: str) -> int:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in ROWS:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    return len(ROWS)
