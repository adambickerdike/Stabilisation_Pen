# The first bench build plan (study H)

**Status: PROPOSED PLAN, 30 September 2026. Nothing has been bought, built or measured.** This plan turns study M's rigs, the gates of `validation/prototype_stages.md`, Rev K's layout and the independent engineering pass's proposed nib and five-bar into a build that a small team can order and run.

**Labels.** Every number carries one of these:
- **MANUFACTURER**: a manufacturer's or distributor's statement, with its part number, source page, date seen and ledger id. Prices were seen on 2026-09-30. Rows AMF-300…322 and OPT-100…101 are in `results/benchbuild/evidence_rows.csv`; earlier rows are in `docs/evidence.csv`.
- **LITERATURE**: a published source, with its ledger id.
- **CALCULATION**: a calculation, with its file.
- **ASSUMPTION**: an input nobody has measured, or a labelled price range where no price was visible. The reason is given.
- **SIM**: synthetic data run through the analysis code. It checks the software, not a device.

---

## Plain-language summary

**What to buy and build first.** Start with the minimum viable first build: the data box DAQ-1 and the contact-and-ink rig R9.
- DAQ-1 is a Teensy 4.1 board and TI's 24-bit ADS131M08 evaluation board. Every instrument is time-stamped on its one clock.
- R9 is built on a Prusa CORE One+ printer kit, which moves the pen head over a fixed bed.
- Under the paper sits a ±2 N three-axis force sensor. Behind the refill sits a 1 N load cell, and dead weights set the refill force.
- The rest is refills, six papers, a calibration weight set and a 4800 dpi scanner.

Order every long-lead item for the later builds in the same week: the force sensors, the coil winding, the lapped races, the etched anchor, the beryllium-copper wire and the page-sensor boards.

**What it costs.**
- **First build: about USD 4,350–7,750.** Parts whose price was visible enter at that price (MANUFACTURER). The force sensors and machined parts enter as ASSUMPTION ranges, because their makers show prices only on request. Add about USD 1,700–2,400 if the lab has no oscilloscope, 4-wire meter, bench supply, soldering station or hand tools.
- **All five builds: about USD 14,000–35,400.** This covers the DAQ, R9 and its upgrades, the coupons, the five-bar and the page-sensing rig. Add USD 2,800–7,500 of instruments if the lab has none. The spread is wide because most coupon hardware is custom and has no visible price.
- Shipping, tax, duty and labour are excluded.

**How long it takes.**
- **Weeks 0–2:** ordering, pre-registration and the DAQ bring-up.
- **Weeks 1–4:** the first G1 answers, provided the force sensors arrive within about three weeks. Their lead time is not published: ASSUMPTION 2–6 weeks, so order them on day 1.
- **Weeks 3–8:** the G2 coupons. Coil winding, lapped races and precision etching take about 3–6 weeks (ASSUMPTION). Each batch of wire-fatigue coupons then runs for 3–8 days.
- **Weeks 6–12:** the five-bar and page sensing.
- **Decision meetings:** at week 8 (G2) and week 12.

**What it will decide.**
1. **G1: how hard the refill must press to write without gaps on each paper, and what the paper pushes back.** This number sets the refill spring (DEC-050 is revisited above 0.3 N). With the friction map, it gives the side load the nib must carry. G1 also lists EXP-J17: only its counter-face part (c) runs in this build, because parts (a) and (b) need a built nose or nib.
2. **G2: whether Rev K's nib can be built, and which fine-stage candidate goes forward.**
   - The "Build Rev K's nib" gate of `validation/prototype_stages.md` §0 has three conditions:
     - the force constant is at least 0.7 × the model on Rev K's coil;
     - the beryllium-copper leads survive 43.2 M cycles;
     - the ball guide rolls with no more than 5 mN of friction.
   - DEC-072's choice between the 1.5 mm and the 1.059 mm stage waits for the measured load.
   - By the pass's own duty screen, the 1.5 mm candidate reaches the assumed 0.15 W copper allocation at about 34 mN of residual load (CALCULATION). Gravity on the moving nib alone is about 29.5 mN at 35° (CALCULATION).
   - Adding the other calculated loads gives about 49–51 mN at 35°: the face's residual of 11–13 mN at the 95th percentile and the guide drag of 8 mN (CALCULATION, a conservative sum of magnitudes). Unless the measured loads are lower, the 1.059 mm stage goes forward.
3. **The five-bar: whether a desk-grounded linkage writes accepted letters on real paper, and what happens when a hand resists it** (DEC-071).
4. **R10: whether a small optical sensor keeps its place on real paper, including through lifts.** This is the sensing build gate, and it chooses the die for Rev K.

**What changed while planning this.**
- **Supply risks.** The current amplifier the rigs were drawn around, TI's OPA548T, is back-ordered: none in stock at DigiKey, with 50 expected on 30 November 2026 (MANUFACTURER, AMF-301). A cheaper substitute (OPA564) and a PWM driver are listed. The page-sensor boards are out of stock or on pre-order (OPT-100, OPT-90).
- **The fatigue drive frequency.** bench_protocols.md runs EXP-B25's fatigue step at about 200 Hz (about 60 h), and EXP-K21 cycles its wires the same way. At 200 Hz the wires' own resonance adds stress the pen never sees (CALCULATION):
  - Rev K's 26.8 mm wires have first modes of about 487–763 Hz, and their clamp stress rises 12–33 %;
  - the reach candidate's 34 mm wires have first modes of about 336–373 Hz, and their clamp stress rises 66–90 %.
  - The plan drives each coupon at no more than 0.2 × its measured first mode (DEC-098 proposed).
- **The ball-guide preload.** The pass's 4 N preload is calculated to give about 8 mN of rolling drag, above EXP-K20's 5 mN line. The plan measures drag and tilt against preload (EXP-BB05).
- **The five-bar force cap.** A motor current limit cannot enforce the five-bar's 0.4 N cap. At rated current the linkage can push about 1.06 N at its worst pose (CALCULATION). A breakaway pen coupling is therefore part of the build (DEC-099 proposed).
- **Beryllium copper.** The alloy's safety data sheet names heat treating, pickling, abrasive cutting, welding and grinding as exposure routes (AMF-319). The wire is bought already hardened, cut with shears and soldered under local exhaust (DEC-097 proposed).

---

## 1. Scope and where things are

This plan covers five builds.

| Build | What it is | Gate (`prototype_stages.md`) | Main experiments |
|---|---|---|---|
| **B0 DAQ-1** | Teensy 4.1 + ADS131M08EVM + thermocouple amplifiers + current drive; one clock (`docs/measurement_rig.md` §1) | all (order 0) | EXP-BB01 (proposed) |
| **B1 R9** | Contact and ink rig on a CoreXY printer frame (`docs/measurement_rig.md` §2) | **G1** | EXP-T01, T02, BB02, BB09; hosts EXP-J17 (c) |
| **B2 G2 coupons** | Force-constant coupons (Rev K's coil, EXP-K22 in EXP-T07; the reach candidate's winding); C17200 wire coupons with a fatigue shuttle (EXP-K21, BB04); ball-guide coupons (EXP-K20, BB05); the floating anchor (EXP-BB03); the counter-face bench (EXP-J17 (c)) | **G2**; "Build Rev K's nib" | as listed |
| **B3 five-bar** | The pass's grounded demonstrator (`mechanics/cad/grounded_stage.py`) with Faulhaber 2224 motors | none yet | EXP-BB06, BB07 (proposed) |
| **B4 R10** | Page-sensor rig on R9's frame (`docs/measurement_rig.md` §3) | sensing build gate | EXP-T04, T05, BB08 |

Not in this first build:
- R11: the tablet protocol needs no build, and the recording pen waits for ethics approval.
- R13 and R14, which need a working nib.
- Rev K's counter-face head with its three SQL-RV-1.8 motors (EXP-K23). These are sold only to volume customers (AMF-15).
- Hall interference (EXP-T09), which needs a TMAG5170 board.

**Files** (all under `results/benchbuild/`):

| Purpose | Files |
|---|---|
| Bills of materials | `bom_B0_daq1.csv`, `bom_B1_r9_g1.csv`, `bom_B2_g2_coupons.csv`, `bom_B3_fivebar.csv`, `bom_B4_r10.csv`: every line with part number, supplier, price and label, source, date, stock, lead time, ledger id, STEP source, material, process, tolerance, who can make it, stage |
| Cost and schedule | `cost_schedule.csv`, `cost_totals.json` |
| Test-to-decision map | `test_decision_map.csv` |
| Proposed rows | `proposed_experiments.csv`, `proposed_criteria.csv` (the columns of `validation/acceptance_criteria.csv`), `proposed_decisions.csv` |
| Evidence | `evidence_rows.csv` (25 rows, 23 columns, CRLF) |
| First session | `first_measurement_checklist.md`, `templates/` (20 CSV data templates, a record and a verdict template, the lab-notebook page) |
| Checks and calculations | `pipeline_check.json`, `bench_calcs.json`, and the scripts in `tools/` that make every table (§15) |

**Other studies running now.**
- **Study N** (nibopt/) may change the fine-stage geometry. The coupon fixtures below take either candidate: the coil packs, races and anchor are drawn per candidate, and the magnets are stock stand-ins. Freeze the coil and race drawings when study N reports.
- **Study P** (platen/) studies a moving-paper platen, the alternative to the five-bar (DEC-071).
- **Study X** (rebaseline/) re-runs simulations with causal sensing (DEC-070). The contact-timing experiment EXP-BB09 feeds it.

## 2. The builds at a glance

The cost columns are sums of the BOM line ranges, taken from `cost_totals.json`. Line totals are rounded to whole dollars, so every total is an exact sum of its lines.

| Build | Core cost, USD | Instruments and tools if the lab has none, USD | Share of core (low end) priced from a seen page | Longest lead item | Who |
|---|---|---|---|---|---|
| B0 DAQ-1 | 859–1,179 | 1,716–2,416 | 78 % | OPA548T back-order to 30-Nov-2026 (AMF-301); not needed for the first build | small team |
| B1 R9 | 5,686–11,746 (the first build is 3,536–6,596 of it; §9.1) | — | 28 % | K3D40 and LSB200 (ASSUMPTION 2–6 weeks, quote) | small team + machine shop |
| B2 G2 coupons | 5,808–17,936 | 1,040–5,040 | 14 % | coil winding, lapped 440C races (ASSUMPTION 3–6 weeks) | machine shop + suppliers |
| B3 five-bar | 987–2,103 | reuses B1/B4 instruments | 57 % | CNC parts (ASSUMPTION 1–3 weeks); motors about 1 week (AMF-304) | machine shop + small team |
| B4 R10 | 628–2,475 | reuses B1 | 10 % | page-sensor boards (out of stock or pre-order, OPT-100, OPT-90) | small team |
| **All five** | **13,968–35,439** | **2,756–7,456** | | | |

---

## 3. B0: DAQ-1, the shared data box

**Purpose.** Every rig reads its instruments through DAQ-1. Each sample is stamped with the Teensy's 600 MHz cycle counter in one interrupt. A device with its own clock records the coded sync pulse and is mapped onto DAQ-1's clock (`docs/measurement_rig.md` §1.3; `rig/sync.py`).

### 3.1 Purchased parts

| Part | Manufacturer part number | Supplier (supplier part number) | Unit price, date seen, stock (label, ledger) | Qty |
|---|---|---|---|---|
| Microcontroller board | PJRC Teensy 4.1 | SparkFun (DEV-16771) | USD 31.50, 2026-09-30, in stock (MANUFACTURER, AMF-220) | 2 (+1 in B3) |
| 24-bit 8-channel ADC evaluation module | TI ADS131M08EVM | DigiKey (296-ADS131M08EVM-ND) | USD 328.11, 2 in stock; TI's page says in stock, price after login (MANUFACTURER, AMF-300) | 1 |
| Thermocouple amplifier | Adafruit 3263 (MAX31856) | Adafruit | USD 17.50, in stock (MANUFACTURER, AMF-234) | 4 |
| Type-T thermocouple, 0.08 mm class | class | instrument distributor | USD 15–40 each (ASSUMPTION: omega.com returned HTTP 403) | 8 |
| Current shunt 0.1 Ω ±0.1 %, 4-terminal foil | VPG Y14870R10000B9R | DigiKey (804-1045-1-ND) | USD 13.05; 0 in stock, 1,000 expected 12-Oct-2026 (MANUFACTURER, AMF-303) | 4 |
| Power op-amp for current drive | TI OPA548T | DigiKey | USD 21.55; 0 in stock, 50 expected 30-Nov-2026; TI store out of stock (MANUFACTURER, AMF-301) | 2 |
| 12 V 60 W supply | Mean Well GST60A12-P1J | DigiKey | USD 19.40 (MANUFACTURER, AMF-308) | 1 |
| Wiring, connectors, 12-core shielded cable, RC filters | class | any | USD 60–150 (ASSUMPTION) | 1 lot |

**The OPA548 problem.** The first build does not need it, because dead weights set the refill force. For R9's voice coil (under 0.5 A) and the coupon coils, there are two substitutes:
- OPA564AIDWP, a 1.5 A linear amplifier: DigiKey USD 9.51, stock not shown (AMF-301).
- A Pololu DRV8874 carrier driven at 40 kHz or more, with an output LC filter: USD 11.94 (AMF-305).

OPA549T is back-ordered to 2 December 2027 (AMF-301).

### 3.2 Fabricated parts, instruments and tools

- **Enclosure and connector panel.** PETG print or laser-cut acrylic, ±0.3 mm (hobbyist). There is no CAD: make it to fit the boards.
- **Instruments, if the lab has none:**
  - oscilloscope Rigol DHO804, USD 459.00, 40 in stock (MANUFACTURER, AMF-321);
  - 6.5-digit DMM with 4-wire ohms, Siglent SDM3065X, USD 857.00 (MANUFACTURER, AMF-322);
  - dual linear bench supply, USD 150–450 (ASSUMPTION).
- **Tools:**
  - temperature-controlled soldering station, USD 100–250 (ASSUMPTION);
  - bench fume absorber Hakko FA400-04, USD 93.79 (MANUFACTURER, AMF-317);
  - calipers, a 1 µm micrometer, tweezers, flush cutters and an ESD mat, USD 150–400 (ASSUMPTION).

### 3.3 Assembly

The steps follow `docs/measurement_rig.md` §1.2–§1.3 and the rig BOM's notes.
1. On the ADS131M08EVM, power AVDD through JP12/TP2 and DVDD through TP1 with R67 removed (TI SBAU334A §4; AMF-222). Wire the J10 header to the Teensy:
   - SPI0: pins 10 CS, 11 MOSI, 12 MISO and 13 SCK;
   - DRDY on pin 9, SYNC/RESET on pin 6.
2. Wire the remaining signals:
   - encoders to the QuadEncoder pins 2/3, 4/7, 8/30 and 31/33;
   - camera trigger 24, strobe 25, sync out 28, DUT sync in 29, marker in 32;
   - PWM pins 22 and 23 through RC filters to the current amplifiers;
   - the MAX31856 boards on chip selects 0, 1, 14 and 15;
   - the page sensor on SPI1 (26, 27, 39; chip select 36; motion line 34).
3. Feed the bridge excitation from the EVM's 3.3 V through 10 Ω and 10 µF, and read it ratiometrically on a spare channel.
4. Build `rig/firmware/rig_daq/rig_daq.ino` with Arduino IDE ≥ 2.3.10, Teensyduino 1.62 and QuadEncoder (AMF-237, AMF-238). The firmware has only been checked against stubs on a PC; this is its first compile for the board (§13).
5. Bring it up as EXP-BB01 (§14; checklist B). Nothing else is recorded until EXP-BB01 passes.

### 3.4 Safety

- The build is low-voltage.
- The OPA548 or OPA564 needs a heat sink and its current limit set below the coil's rating.
- Handle the boards on an ESD mat.
- No person is connected to this equipment: the first build is bench-only.

---

## 4. B1: R9, the contact and ink rig (G1)

**Purpose (`docs/measurement_rig.md` §2).** R9 measures two forces separately:
- the axial force the refill spring applies, F_c, from an in-line cell behind a leaf-guided refill;
- the force the ball applies to the paper, N plus friction, from a three-axis plate under the paper.

It then maps friction against speed, tilt and direction, and finds the lowest force that writes without gaps. The same frame later carries EXP-J17 (c) and R10.

### 4.1 Purchased parts and instruments

| Part | Manufacturer part number | Supplier | Unit price, date, stock (label, ledger) | Qty | First build? |
|---|---|---|---|---|---|
| CoreXY printer kit (motion frame) | Prusa CORE One+ (Gen 2) kit | prusa3d.com | USD 925; "In stock. Preparation time: 1–3 business days"; assembled USD 1,202.78 (MANUFACTURER, AMF-231, re-seen 2026-09-30) | 1 | yes |
| 3-axis force sensor ±2 N | ME-Messsysteme K3D40 ±2N | me-systeme.de | USD 900–1,900 (ASSUMPTION: price behind a login; AMF-224 has the specifications) | 1 | yes |
| 3-axis force sensor ±10 N | ME-Messsysteme K3D40 ±10N | me-systeme.de | USD 900–1,900 (ASSUMPTION) | 1 | no (N above the ±2 N plate's range; reused by B2 and B3) |
| In-line axial cell 100 g (1 N), 2 mV/V | FUTEK LSB200 FSH03870 | futek.com | USD 450–900 (ASSUMPTION: the store page shows $0.00; AMF-225 has the specifications) | 1 | yes |
| In-line axial cell 250 g (2.5 N) | FUTEK LSB200 FSH03871 | futek.com | USD 450–900 (ASSUMPTION, as above; AMF-225) | 1 | no (N up to 2 N at every tilt; G2-format refills) |
| Voice coil for F_c ramps | Moticont LVCM-013-013-03 | moticont.com | USD 150–350 (ASSUMPTION: no price on the page; AMF-02) | 1 | no (dead weights first) |
| Linear encoder with MS scale | RLS LM13, 13B | RLS distributor | USD 250–700 per axis (ASSUMPTION; OPT-89) | 2 | no (move timing first) |
| Slide Hall sensor | TI DRV5055A4QDBZR | DigiKey (296-50468-1-ND) | USD 0.87, 3,538 in stock (MANUFACTURER, AMF-302) | 4 | yes |
| Calibration weights OIML M1, 1 g–500 g | Mettler Toledo 30402728 | Scales Galore | USD 535.50, "Available to Ship" (MANUFACTURER, AMF-315) | 1 | yes |
| Scanner, 4800 dpi optical | Epson Perfection V39 II (B11B268201) | epson.com | USD 129.99 (MANUFACTURER, AMF-314) | 1 | yes |
| Refills: S 635 M ×20, easyFLOW 9000 ×10, P 8126 ×10, FL 6040 F ×10; a second D1 oil brand ×10 and a gel D1 ×10 | Schmidt Technology; class | stationery | USD 70–360 in all (ASSUMPTION; CON-100) | 1 lot | yes |
| Papers: copy 80 g/m², recycled, school ruled, coated, tracing, card | class | stationery | USD 60–150 (ASSUMPTION) | 1 pack each | yes |
| Jewel-bearing pulley and thread; inclinometer (0.1°); 0.05 mm spring-steel shim; USAF-1951 target; underlays and CFRP sheet; fasteners | class | any | USD 20–80; 30–120; 20–60; 50–200; 30–100; 30–80 (ASSUMPTION) | 1 each | yes |

**The scanner.** The V39 II is enough to find gaps in EXP-T02. R3's 5 µm (k = 2) ink-path metrology for G3 needs the Epson V850 Pro, USD 1,999 (MANUFACTURER, AMF-236), or a microscope. That purchase waits until G3.

### 4.2 Fabricated parts

All are taken from `results/rig/cad/rig_contact_assembly.step`, made by `mechanics/cad/rig_contact.py`.

| Part (solid name) | Material | Process | Tolerance and finish | Who | Cost (ASSUMPTION) |
|---|---|---|---|---|---|
| Tilt arc R 70 mm with holes at 35/50/65/75° (`arc_frame`) and its carriage (`arc_carriage`), first-build version | PETG or PA-CF | FDM 3-D print | ±0.2 mm; tilt set and read under load with the inclinometer | hobbyist | USD 10–40 |
| The same, standard version | 6061-T6 | CNC milling | hole pattern and radius ±0.05 mm; bead blast | machine shop | USD 150–600 |
| Cartridge frame with leaf clamps (`cartridge_frame`), refill holder and collet for D1 2.35 mm or G2 6 mm (`holder`), Hall bracket (`hall_bracket`) | 6061-T6; brass collet; printed bracket | CNC, lathe; FDM | ±0.02 mm on the leaf clamp faces; holder bore 2.4 H7 | machine shop | USD 150–500 |
| Guide leaves 0.05 × 8 × 25 mm ×2 (`guide_leaves`) | spring-steel shim | shear against a template, or photo-etch; deburr | ±0.05 mm, flat, no kinks | hobbyist | USD 0–25 |
| Bed adapter 120 × 100 × 6 mm (`bed_adapter`) and a head plate to the CORE One carriage | 6061-T6 | CNC milling | flatness 0.05 mm; K3D40 M3 pattern ±0.05 mm | machine shop | USD 100–350 |
| CFRP platen 80 × 60 × 1.5 mm (`platen_cfrp`), paper edge clamps (`clamp_nx`, `clamp_px`) | CFRP; PETG | waterjet or CNC routing by a supplier (CFRP dust); FDM | ±0.2 mm | supplier + hobbyist | USD 20–100 |

The head plate is taken from the CORE One's published CAD (AMF-231 says the CAD is published). No drawing of it exists in this repository.

### 4.3 Instruments and tools

- K3D40 ±2 N; LSB200 100 g; DAQ-1.
- Dead weights, pulley and inclinometer.
- The scanner with a USAF-1951 target.
- Thermocouples for room and paper temperature.
- Standard build adds the LM13 encoders, the voice coil, the ±10 N plate and the 250 g axial cell.

### 4.4 Assembly

1. **Printer.** Build the CORE One+ kit by the maker's manual and run its self-test.
   - Leave the extruder's electronics connected but park the extruder off the carriage on a bracket.
   - Its thermistors then read room temperature, and the heater targets stay at 0 (PROPOSED).
   - Confirm that the printer's firmware accepts this; the firmware is open source (AMF-231).
2. **Plate stack.** Fit the bed adapter on the bed, then the K3D40 ±2 N, then the CFRP platen. Put an underlay under the paper (glass, pad or elastomer) and clamp the paper at its edges.
3. **Head.** Fit the head plate on the X carriage, then:
   - the tilt arc and carriage;
   - the cartridge frame with both leaves clamped flat and parallel;
   - the holder, collet and refill;
   - the LSB200 in line behind the holder;
   - the magnet on the slide and the DRV5055 on its bracket.
   In the first build, the refill force comes from a thread over the jewel-bearing pulley to a dead weight. The standard build replaces this with the voice coil.
4. **Wiring.** Route the cables through the printer's cable path with strain relief. The cell's cable must not load the axial path; the guide-stiffness calibration includes whatever it adds.
5. **Channels.** Wire the bridges to the ADC channels as `rig.convert.CHANNEL_MAPS['R9']` expects:
   - ch0: axial cell;
   - ch1–3: plate x, y, z;
   - ch4: coil shunt;
   - ch5: slide Hall.
6. **Stroke timing.**
   - Standard build: the encoders give position.
   - First build: a printer output toggled from the G-code at each stroke start, for example the part-cooling fan output through an optocoupler, goes to the marker input (pin 32). The head position is then rebuilt from the commanded path. Check that the CORE One's firmware can do this; no helper for this exists yet (§10.2).
7. **Checks** (checklist C):
   - tilt at each angle under load;
   - clearances at every tilt (the CAD's fit checks: 9.7 mm at 35°);
   - guide stiffness;
   - axial cell and plate calibrations at each test angle;
   - tap test of the plate stack.

### 4.5 What the first build gives up

The first build can still answer G1's two main questions: F_c,min per refill and paper, and the side load at 35, 50 and 75°.

| Standard feature | First-build version | Consequence |
|---|---|---|
| Voice-coil F_c | dead weights | only fixed-force lines, no ramps: EXP-T02's threshold comes from the lines around it, which the protocol uses to confirm the ramp anyway; no modulation, so AC-T02-03 waits for the voice coil |
| LM13 encoders | commanded path plus marker | AC-BB02-02 (speed stability) and per-sample friction ripple wait for the encoders |
| ±10 N plate and 250 g axial cell | ±2 N plate and 100 g cell (F_c ≤ 0.5 N, the rig design's limit for that cell) | N reaches about 0.5 N at 75° and 0.7 N at 35° in every stroke direction (CALCULATION, N = F_c / (sin θ − μ cos β cos θ) with μ 0.15; `bench_calcs.json → r9_normal_force_reach`). That covers EXP-T01's grid (F_c 0.08–0.30 N) but not AC-B01-20's 0.2–2.0 N envelope, which waits for the 250 g cell and the ±10 N plate. EXP-B01's 4 N level needs a larger axial cell still (open item of `prototype_stages.md` §0) |

### 4.6 Safety

- **Pinch points.** The printer's belts and gantry are enclosed; close the door while the head moves. The printer's stop and power switch are the emergency stop.
- **Heat.** The bed and hotend heaters are never on. The chamber reaches up to 55 °C in thermal runs (AMF-231), so its surfaces are hot then.
- **Glass.** Edge-ground underlays only.
- **Dust.** CFRP dust: the platen is cut by a supplier.
- **Weights.** Keep the dead weights clear of the moving head.

---

## 5. B2: the G2 coupons

The five coupons below answer the G2 items of the brief. Each comes with its experiment, its fixture and its instruments. The full lines are in `bom_B2_g2_coupons.csv`.

### 5.1 Force-constant coupons (EXP-T07 with study K's EXP-K22; the reach candidate's winding)

**What is built.** Two translation coupons on the R12 bench (`docs/measurement_rig.md` §5, used with its goniometers locked). In each, a stator holds four N52 poles, the back iron and the keeper, at the model's gaps: 0.3 mm from magnet to coil and 0.15 mm from coil to keeper. The stator sits on a K3D40 ±10 N. The moving coil pack rides on an arm through the keeper's hole and is set by a manual XYZ stage.
- **Rev K coil** (DEC-062; study K's EXP-K22):
  - concentric racetracks, bundles 2.2 mm wide, rows 5.0 mm off the axis;
  - study B's poles are 5.12 × 5.12 × 3.5 mm (`results/bnib/bnib.json`, recommended design);
  - prediction 0.334 / 0.272 N/√W for the x and y layers at the centre (CALCULATION, `docs/revK_design.md` §3.3).
- **Reach candidate** (DEC-072 (a)):
  - poles 4.81 × 4.81 × 3.5 mm;
  - two 0.8 mm winding layers (x then y), bundles 2.2 mm wide, rows 4.75 mm off the axis;
  - weakest sampled force constant 0.158 N/√W (CALCULATION, `results/improvement/mechanics/mechanics_study.json`).

**Stock magnets first (DEC-095 proposed).** The design sizes are not stock items. The first coupons use stock stand-ins, and the models are re-run at the as-built size and measured Br before comparison (`bench_protocols.md` §0.2):
- 5 × 5 × 3 mm N52, ±0.1 mm, supermagnete Q-05-05-03-N52N: EUR 0.35 each at 20, 2,120 in stock (MANUFACTURER, AMF-309);
- 4.76 mm N52 cubes, K&J B333-N52: USD 0.56 each, in stock, Br 14,800 G on the page (MANUFACTURER, AMF-310).

Custom poles are ordered only after AC-T07-02 passes on the stock coupon: USD 150–600 per batch and 4–8 weeks (ASSUMPTION).

**Fabricated parts.**

| Part | STEP source | Material, process | Tolerance | Who, cost |
|---|---|---|---|---|
| Back iron 0.5 mm and keeper 0.3 mm rings (reach: R 10.6/3.6 mm); Rev K's back plate and keeper, and the heel variant's 1.2 mm notched pair | `extended_reach_nib.step` (`back_iron`, `keeper_with_front_race_surface`); `revK_pen_assembly.step` (`back_plate`, `keeper`) | 1008/1010 sheet; wire EDM or fibre laser, deburr, stress relief | ±0.02 mm, flat to 0.02 mm | laser/EDM service, USD 60–300 (ASSUMPTION) |
| Bonded racetrack coil packs, 2–4 sets | `extended_reach_nib.step` (`winding_pack_*`); `revK_pen_assembly.step` (`coil_x`, `coil_y`) | self-bonding enamelled wire, wound on a split mandrel, heat- or solvent-bonded | layer thickness ±0.03 mm | coil-winding service, USD 300–1,500, 3–6 weeks (ASSUMPTION); or wound by hand by a skilled hobbyist with bondable wire (USD 20–60) |
| Stator block with magnet pocket and keeper spacer; coil arm | `rig_coupon_assembly.step` (`base_plate`, `bridge`, `stator_plate`, `coupon_arm`) | 6061-T6 CNC; PEEK or SLA resin arm | ±0.02 mm on gap-setting faces | machine shop, USD 200–700 (ASSUMPTION) |

**Instruments.**
- K3D40 ±10 N.
- XYZ stage with 13–25 mm travel and 10 µm graduation: USD 400–1,600 (ASSUMPTION; Thorlabs' pages showed no price here).
- DAQ-1 with the OPA548 or OPA564 current drive.
- A 4-wire DMM for R20 and an LCR meter for L (USD 100–600, ASSUMPTION).
- Thermocouple on the coil.

**Assembly.**
1. Measure every magnet: dimensions, and Br by a pull test or a Gaussmeter. Mark the polarities.
2. Place the four poles in a checkerboard in the pocket one at a time, with a brass jig and eye protection. Bond them, and fit the back iron and the keeper spacer.
3. Mount the coil pack on its arm, and the arm on the XYZ stage.
4. Centre the coil by the symmetry of the zero-current force, to within 0.05 mm (the tolerance of DEC-044).
5. Map 7 × 7 (or 11 × 11) nodes over ±1.2 mm (Rev K) or ±1.5 mm (reach), with currents in reversal order (EXP-T07's procedure).

EXP-T08's keeper pull (AC-T08-01, 9.1 N predicted, to within ±20 %) needs a sensor rated above about 11 N, such as R12's K3D40 ±50 N, which is not in this BOM. It waits for the next build (§13).

**Criteria.** AC-T07-01 to AC-T07-05 (§8).

### 5.2 Wire coupons and the fatigue shuttle (EXP-K21; EXP-BB04 proposed)

**Wire.**
- **Rev K** (EXP-K21): four 0.10 mm C17200 wires of 26.8 mm, which carry the coil current (DEC-063); a 0.08 mm variant for comparison.
- **Reach candidate** (EXP-BB04): eight 0.10 mm wires of 34 mm, two in parallel per lead, with a 1.7 mm stop and an axially soft anchor of about 100 N/m. Its stress calculation assumed a total axial stiffness of 80–120 N/m and at most 5 mN of assembly tension.

**Source.** Goodfellow's Cu98/Be2 wire (AMF-311):
- spooled wire "starting at $279.00", about 2 weeks' lead time;
- straight wire of 1 m, hard temper, "starting at $429.00".

The diameter table did not load, so ask for a quote that confirms 0.10 and 0.08 mm in an aged temper (TH04/HT or AT). Condition data are in AMF-18 and AMF-19; conductivity in AMF-251.

**Fatigue drive frequency (CALCULATION, `results/benchbuild/bench_calcs.json`).** The first transverse mode of a clamped wire, by the Rayleigh method with E 127.6 GPa and density 8.26 g/cm³ (MFR AMF-19):

| Wire | First mode | 0.2 × first mode | Clamp stress rise at 200 Hz | 43.2 M cycles at 0.2 × first mode |
|---|---|---|---|---|
| 34 mm | about 336 Hz at 5 mN tension; 373 Hz at 11 mN | 67–75 Hz | about 90 % (66 % at 11 mN) | 160–180 h |
| 26.8 mm | about 487 Hz without preload; 763 Hz at 0.05 N | 97–153 Hz | 12–33 % | 80–125 h |

The clamp stress rise is a single-mode estimate of base excitation, and is an ASSUMPTION. `validation/bench_protocols.md` gives EXP-B25's fatigue step as "about 60 h at 200 Hz", and EXP-K21 cycles its coupons "as EXP-B25" (AC-K21-02). At that frequency the wire's own dynamics would inflate the stress the pen never sees, because the pen moves at tremor frequencies of 12 Hz or less. The plan therefore:
- measures each coupon's first mode before cycling (`templates/wire_mode_check.csv`);
- drives at no more than 0.2 × that mode (AC-BB04-05; DEC-098 proposed);
- runs several coupons in parallel.

**The fatigue shuttle (PROPOSED DESIGN, no CAD).** A crank-eccentric drive moves a leaf-guided shuttle through the stop travel: 1.26 mm for Rev K, 1.7 mm for the reach candidate. The shuttle carries six or more coupon stations.
- The protocol's R8 stations call for laser amplitude control. A ground eccentric sets the amplitude geometrically (±0.01 mm), so it needs no loop.
- Each wire carries 0.1 A from an eight-channel constant-current source (REQ-RVK-004). Its 4-wire resistance is logged on the ADS131M08.
- A failure is an open circuit or a step of more than 2 % above the running median (`tools/pipeline_check.py → wire_failure`). This replaces resonance tracking.
- The shuttle needs a balanced crank and a guard.
- Cost: shop USD 300–1,200, drive motor USD 40–200, current source USD 30–100 (ASSUMPTION).
- Optional: a Panasonic HG-C1030 laser sensor to check amplitude and measure the first mode, USD 439.60, 26 in stock (MANUFACTURER, AMF-318). The strobed camera of B4 can do the same.

**Clamps.**
- Brass solder clamps with a 0.12 mm slot and a polished exit radius of 0.10 ± 0.02 mm, which sets Kt. Crimp tubes of 304 hypodermic tube are the alternative.
- Machine shop with wire EDM, USD 200–700 (ASSUMPTION).
- **Kt cannot be measured with a gauge on a 0.10 mm wire.** The plan proposes 10× scaled coupons: 1.0 mm C17200 in scaled clamps with 0.2 mm-grid gauges. Kt depends on the geometry, so it scales (§13).

**Assembly** (checklist F):
1. Cut the wire with shears or flush cutters and wipe it with IPA.
2. Solder it into the clamp under the fume absorber, with gloves, while a fixture holds it straight and without tension.
3. Inspect the clamp exit at 50×.
4. Measure R20 by 4-wire. Mount the coupon on the shuttle and measure its first mode.
5. Set the stroke and start the cycling, with the current on.

**Criteria.** AC-K21-01…04; AC-BB04-01…05 (§8, §14).

### 5.3 Ball-guide coupons (EXP-K20; EXP-BB05 proposed)

**What is built.**
- **Rev K's guide:** the carrier flange (18.9 mm diameter) between two lapped 440C races on 2 × 6 Si3N4 balls of 0.8 mm, on a 16.6 mm circle. Each race sits on a wave spring preloaded to 4 N. The couple is 10.9 mN·m at 35° (CALCULATION, `docs/revK_design.md` §3.3).
- **The reach candidate's full-ring guide:** a 15.1 mm ball circle and 2.9 mm races on the same balls. At the 4 N preload the pass calculates 8.07 mN of rolling drag and 2.64 GPa of peak Hertz pressure (CALCULATION, `docs/mechanics_improvement_audit.md`).

Both figures use a rolling coefficient of 0.001 (ASSUMPTION). The drag is above EXP-K20's 5 mN line, so EXP-BB05 steps the preload through 1, 2, 3 and 4 N, and looks for a preload that holds the carrier's tilt within 0.2 mrad (REQ-RVK-003) with no more than 5 mN of drag.

**Fabricated parts.**

| Part | STEP source | Material, process | Tolerance | Who, cost |
|---|---|---|---|---|
| Races: Rev K's ×3, the reach candidate's ×3; race inserts for the flange ×4 | `revK_pen_assembly.step` (`front_race`, `rear_race`); `extended_reach_nib.step` (`rear_race`, `keeper_with_front_race_surface`) | 440C: turn, harden (HRC 58–60, ASSUMPTION), grind, lap | flat ≤ 1 µm, parallel ≤ 2 µm, Ra ≤ 0.05 µm (ASSUMPTION specification) | precision grinding shop, USD 400–1,500, 3–6 weeks (ASSUMPTION) |
| Carrier flanges: Rev K 18.9 × 1.5 mm, reach 18 × 1.5 mm; one with 440C inserts, one with a bare titanium face | `revK_pen_assembly.step` (`carrier_flange`); `extended_reach_nib.step` (`moving_flange`) | Ti-6Al-4V CNC turning, faces lapped | faces parallel ≤ 2 µm; thickness ±0.005 mm | machine shop, USD 150–600 (ASSUMPTION) |
| Drop rig: a 1 m tube and a dummy pen carrying the guide | PROPOSED | PETG, acrylic | ±0.3 mm | hobbyist, USD 30–100 |

**The flange face.** In the CAD the balls run directly on the titanium flange. The calculated 2.6 GPa Hertz stress is well above Ti-6Al-4V's 0.91–1.11 GPa yield strength (LIT AMF-20), so the face is likely to indent (ASSUMPTION). The coupon therefore tests hardened inserts against a bare face (AC-BB05-03).

**No ball retainer.** The CAD has none. The coupon starts without a cage and records whether the balls migrate (§13).

**Purchased parts.**
- Si3N4 balls, 0.8 mm, grade 5: USD 0.2–0.8 each (ASSUMPTION: Ortech lists the size but shows no price).
- Wave springs of about 4 N, several rates: USD 4–15 each (ASSUMPTION).

**Instruments.**
- **Drag:** a 10 g (0.1 N) FUTEK LSB200 FSH03867, USD 450–900 (ASSUMPTION; AMF-225). The K3D40 cannot judge a 5 mN line: its test uncertainty ratio is 0.56–0.71, against 12–15 for the 10 g cell (CALCULATION, `bench_calcs.json`).
- **Preload:** the K3D40 ±10 N (its Fz channel).
- **Tilt:** a laser lever (diode laser and position-sensitive detector), USD 300–900; an autocollimator costs USD 3,000–8,000 (ASSUMPTION).
- **Race profilometry:** a metrology lab, USD 100–400 per session (ASSUMPTION).

**Assembly.**
1. Clean the races and balls with IPA.
2. Stack them in this order: lower race on its wave spring over the K3D40, balls, flange, balls, upper race on its wave spring.
3. Set the preload with a micrometer screw while reading Fz.
4. Apply the couple with a dead weight on a lever.
5. Sweep ±1.26 mm (Rev K) or ±1.5 mm (reach) at 8 Hz through the 10 g cell.
6. Compute the drag as half the forward-minus-return force at the same position (`tools/pipeline_check.py → guide_drag`).

### 5.4 The floating-anchor coupon (EXP-BB03 proposed)

**What is built.** The pass's axially soft anchor is four fixed-guided beams, 6 × 0.5 mm, in 35 µm full-hard 301 foil (`results/improvement/mechanics/floating_anchor_coupon.step`). The beams alone are calculated at 76.6 N/m (CALCULATION, E 193 GPa ASSUMPTION). The flexible interconnect is budgeted at about 23.4 N/m, for 80–120 N/m in all.

**Thickness sensitivity (CALCULATION, `bench_calcs.json`).** The beam stiffness goes as w t³ / L³, so a ±1 µm thickness error moves it by ±8.6 %. A 35 µm foil is not a US shim gauge. At 0.5 mm beam width:

| Foil | Stiffness | Beam width that gives 76.6 N/m |
|---|---|---|
| 25.4 µm | 29.3 N/m | 1.31 mm |
| 30 µm | 48.3 N/m | 0.79 mm |
| 35 µm | 76.6 N/m | 0.50 mm |
| 38.1 µm | 98.8 N/m | 0.39 mm |
| 40 µm | 114.4 N/m | 0.34 mm |

The foil is therefore measured at five points on each sheet, and the artwork's beam width is set from that measurement. The beams' bending stress at the 50 µm anchor motion is 28 MPa, far below 301 full-hard's 540 MPa fatigue strength (CALCULATION; LIT AMF-20).

**Process.** Precision photochemical etching or UV-laser micromachining, holding the beam width to ±0.01 mm: USD 300–1,500 for a first batch, 2–4 weeks (ASSUMPTION). A service with ±0.13 mm and a 1 mm minimum feature cannot make these beams, for example Ponoko (MANUFACTURER, AMF-313).

**Materials.**
- Foil: Goodfellow AISI 301, hard, "$252.00" starting price; the thickness band 0.01–0.05 mm appears in its tolerance table (MANUFACTURER, AMF-312).
- Interconnect: a polyimide flex board from a prototype service, USD 50–300 (ASSUMPTION).

**Measurement.** The anchor's frame sits on a precision balance with at least 1 mg readability (USD 200–2,500, ASSUMPTION). A 1 µm micrometer pushes the hub 0–100 µm in 10 µm steps. The stiffness is the slope, fitted by `rig.calib.fit_guide_stiffness`. The pipeline check recovered 96.0 against 96 N/m (SIM). The measurement is repeated with the interconnect fitted. The wires' assembly tension is the hub's offset times this stiffness (AC-BB03-03, at most 5 mN).

### 5.5 The counter-face bench (EXP-J17 part (c)) on R9's frame

**What is built.** Study B's face is carried on R9's tilt arc: a 6 mm hardened disc on a cross-strip flexure, a constant-force strip spring, a follower stop, and a rolling refill guide in a carrier.
- A second K3D40 ±2 N sits under the carrier and measures the residual side load (USD 900–1,900, ASSUMPTION).
- The protocol's six-axis ATI Nano17 would also give the couple: USD 5,000–9,000 (ASSUMPTION; AMF-223, price not seen).
- Release and return are timed from the carrier's force at 4 kSPS.
- The inputs are three refills and F_s of 0.1–0.7 N.

**Missing CAD.** This fixture has no CAD (§13). Its parts are a shop job: USD 300–1,000 (ASSUMPTION).

**What it decides.** Its residual load and friction are the measured inputs that DEC-072 and DEC-096 need (AC-J17-04…07).

**Rev K's head.** Rev K's head mock-up (EXP-K23) waits for its motors, or for the micro-stepper lead-screw fallback of DEC-064.

### 5.6 Safety for B2

- **Beryllium copper** (DEC-063; DEC-097 proposed; AMF-18, AMF-319, AMF-320).
  - The wire arrives already aged; no heat treatment is done at the bench.
  - Cut with shears or flush cutters only: no abrasive cutting, grinding, sanding, pickling or acid cleaning.
  - Solder under the fume absorber, or crimp. Nothing is welded.
  - Wear gloves: the SDS lists skin sensitisation among the hazards, and a 0.1 mm sliver can pierce skin (AMF-319). Wear eye protection.
  - Bag and label offcuts, broken coupons and wipes. No food or drink at the bench; wash hands after handling.
- **Magnets.** N52 blocks snap together: assemble them one at a time in a non-magnetic jig, with eye protection against chipped magnet. Keep them away from pacemakers and from magnetic media. The heated runs stay below the supplier's stated maximum temperature, which has not yet been read.
- **Fatigue shuttle.** The eccentric turns at 4,000–9,000 rpm: guard it, and balance the crank.
- **Drops.** Balls and fragments fly: wear eye protection.
- **Foil.** Etched foil edges are sharp: wear gloves.

---

## 6. B3: the grounded five-bar demonstrator

**Design** (the pass; `mechanics/cad/grounded_stage.py`, `wholepen/grounded.py`; all CALCULATION or ASSUMPTION).
- **Geometry.** Two motors on a desk-mounted base 50 mm apart. Proximal links are 60 mm and distal links 90 mm. The writing patch is 60 × 40 mm, centred 90 mm from the motor line.
- **Drive.** 6:1 capstans: an 18 mm output radius driven from a 3 mm motor radius. The 80 % efficiency is an ASSUMPTION.
- **Motors.** Faulhaber 2224 U 012 SR: 6.21 mN·m rated torque, 14.6 mN·m/A, 8.77 Ω (the pass's datasheet reading).
- **Force.** The continuous force disk has a sampled minimum of 0.480 N. The controller's cap is 0.4 N, an ASSUMPTION rather than a clinical limit. Reflected mass is 93–105 g.
- **Encoders.** The model assumes 16-bit output encoders. The build uses 14-bit AS5047P encoders, which quantise the endpoint to 8.0 µm (1σ, worst case) against 2.0 µm at 16 bits (CALCULATION, `bench_calcs.json`).
- **Force at rated current.** With both motors at rated current, the linkage can push up to 1.06 N at its worst pose and direction (CALCULATION). The 0.4 N cap is therefore software, and a breakaway coupling is the physical backstop (DEC-099 proposed).

### 6.1 Purchased parts

| Part | Manufacturer part number | Supplier | Unit price, date, stock (label, ledger) | Qty |
|---|---|---|---|---|
| Brushed coreless motor, 22 mm, 12 V | Faulhaber 2224U012SR; the DigiKey listing's manufacturer number is "2224.11000" | DigiKey marketplace (5293-2224.11000-ND) | USD 122.60, 7 in stock, "ships in approximately 5 days from Faulhaber", USD 9 shipping (MANUFACTURER, AMF-304) | 3 (one spare) |
| Output-shaft encoder, 14-bit, on adapter board | ams AS5047P adapter board | DigiKey (4991-AS5047PADAPTERBOARD-ND) | USD 19.40, 397 in stock; the AS5047P IC itself is listed as discontinued (MANUFACTURER, AMF-307) | 3 |
| Motor driver with current sense (1.1 V/A) | Pololu 4035 (DRV8874 carrier) | pololu.com | USD 11.94 (MANUFACTURER, AMF-305); alternative maxon ESCON Module 24/2 (466023), EUR 97.68, NRND, current-controller mode (AMF-306) | 3 |
| Bearings 3 × 6 × 2.5 mm | MR63-ZZ | Bearings Direct | USD 4.38 each, 684 available, ships in 24 h; ABEC grade not stated (MANUFACTURER, AMF-316) | 12 |
| Controller board | Teensy 4.1 | SparkFun (DEV-16771) | USD 31.50 (MANUFACTURER, AMF-220) | 1 |
| 12 V 60 W supply | Mean Well GST60A12-P1J | DigiKey | USD 19.40 (MANUFACTURER, AMF-308) | 1 |
| Diametric encoder magnets; 3 mm h6 shafts; capstan cable (Dyneema or 7×7 stainless) and tensioners; latching emergency stop and relay; micro-servo pen lift; 200 and 500 N/m springs on a linear guide | class | any | USD 2–8 each; 15–40; 15–50; 25–80; 8–25; 20–80 (ASSUMPTION) | as needed |

Confirm before ordering that DigiKey's "2224.11000" is the 2224 U 012 SR. RS 873-4795 lists the 2224U012SR at 12 V, 6.7 mN·m and 4,390 rpm, the same speed as DigiKey's listing (AMF-304).

### 6.2 Fabricated parts

All are taken from `results/improvement/mechanics/grounded_fivebar.step`.

| Part (solid names) | Material, process | Tolerance | Who, cost (ASSUMPTION) |
|---|---|---|---|
| Base 170 × 165 × 5 mm (`desk_reaction_base`) | 6061-T6 plate; waterjet and CNC finishing | bores ±0.02 mm; base spacing 50.00 ± 0.02 mm | machine shop, USD 80–300 |
| Output bearing supports ×2 (`output_bearing_support_0/1`) | 6061-T6, lathe | bearing bores H7; coaxial to 0.01 mm | machine shop, USD 60–200 |
| Capstans: output R 18 mm ×2, motor R 3 mm ×2 (`output_capstan_*`, `motor_capstan_*`) | 6061 output drums with a helical cable groove; brass motor drums with a 2 mm bore | groove pitch ±0.02 mm | machine shop, USD 80–300 (a printed first try is possible) |
| Links: 60 mm ×2 and 90 mm ×2, 7 × 3 mm (`proximal_link_*`, `distal_link_*`) | 6061-T6 or CFRP plate, waterjet or CNC | pin centres ±0.02 mm; bearing seats H7 | machine shop, USD 60–250 |
| Pen holder for a 24 mm dummy pen: breakaway magnetic coupling releasing at 0.5–0.8 N, lift guide, dummy pen with refill and brass ballast (from the keep-out solid `24mm_pen_holder_keepout`) | PETG or SLA resin; N52 discs | ±0.1 mm | hobbyist, USD 30–120 |
| Guards over the capstans and the sweep of the links | laser-cut acrylic | ±0.3 mm | hobbyist, USD 20–60 |

The pass's CAD leaves several things unresolved, and they are resolved during this build: the cable routing and tensioner, the output encoder mounts, the bearing preload, the pen gimbal and lift, and the emergency force release.

### 6.3 Instruments

- The K3D40 ±10 N from B1, for the force map and the force cap.
- The OV9281 camera with a dot grid from B4, as endpoint truth.
- DAQ-1, which receives the controller's clock through the sync pulse.
- The oscilloscope.

### 6.4 Assembly

1. Press the bearings into the links and supports, and fit the h6 shafts.
2. Mount the motors on the base and fix the motor drums on the 2 mm shafts.
3. Wind each capstan cable with a fixed number of turns, anchor it at both ends, and pretension it with the tensioner.
4. Fit the diametric magnets on the output shaft ends, and the AS5047P boards below them at the air gap the data sheet gives.
5. Assemble the four links and the pen holder, with the breakaway coupling, the lift servo and the dummy pen.
6. Electronics:
   - the controller Teensy, two DRV8874 carriers and the 12 V supply, with the emergency-stop relay on the motor supply;
   - encoders on SPI;
   - DAQ-1's sync pulse into a controller input.
   The controller firmware does not exist yet (§13). It needs current loops using the 1.1 V/A sense output, a Cartesian controller with τ = Jᵀ F, the 0.4 N cap and logging.
7. Before any motion test, run AC-BB06-04 (checklist G):
   - the emergency stop removes motor power;
   - with the holder blocked, the force stays at or below 0.4 N;
   - the coupling releases between 0.5 and 0.8 N.
8. Calibrate the encoder offsets and link lengths on 20 camera poses, then judge on 35 others (AC-BB06-01).

### 6.5 Safety

- **Pinch points** at the capstans and the link sweep: fit guards, and keep hands out of the workspace while the motors are enabled.
- **Stops.** A latching emergency stop. The hardware current limit is at rated current, with the 0.4 N cap in software and the breakaway coupling as backstop.
- **No person's hand** is used until a safety gate like G-S is written for this device (DEC-099 proposed; `prototype_stages.md` §1 principle 4).
- **Hand simulants.** Springs of 200 and 500 N/m stand in for a resisting hand, as in the pass's simulation.

---

## 7. B4: R10, the page-sensing rig

**Design** (`docs/measurement_rig.md` §3; `mechanics/cad/rig_pagesense.py`). The sensor fixture rides on R9's CoreXY head in place of the contact head:
- a tilt arc of R 45 mm (30–88°);
- a roll ring of ±20°;
- a micrometre Z stage for fine height.

The paper lies on 5 mm float glass. Mode A holds the bare die and lens on a 14 × 12 mm sled. Mode B holds a printed mock nose.

**Truth.** The first choice is the strobed OV9281 camera at 100 fps. It is enough for 10 ms windows: TUR 4.8 against 10 µm, resting on an ASSUMED centroid noise until qualified (`docs/measurement_rig.md` §3.4). The standard build adds R9's LM13 encoders for per-sample noise.

### 7.1 Parts

| Part | Manufacturer part number | Supplier | Price and availability (label, ledger) | Qty |
|---|---|---|---|---|
| PAA5100JE breakout (15–35 mm) | Pimoroni PIM573 | shop.pimoroni.com | "Pre-order", no price shown: USD 20–35 (ASSUMPTION; OPT-90) | 1 |
| PMW3360 breakout with lens | Keycapsss KC10125 (PMW3360DM-T2QU) | keycapsss.com | EUR 29.90 incl. VAT, "Currently out of stock" (MANUFACTURER, OPT-100) | 2 |
| Rev K's die class: PMW3610DM-SUDU with lens, on a small assembled board | PixArt PMW3610DM-SUDU | JLCPCB assembly (C42442560, "Extended" part) | no price or stock shown: USD 35–145 (ASSUMPTION; OPT-101, OPT-61) | 3 |
| Fallback: a commercial mouse with a known sensor, board harvested | class | any | USD 20–80 (ASSUMPTION) | 1 |
| Global-shutter camera with external trigger | Arducam OV9281 UVC (B0332) | arducam.com and resellers | USD 45–80 (ASSUMPTION: the pages returned HTTP 403; OPT-88 documents the trigger mode) | 1 |
| LED strobe; chrome-on-glass dot grid; Z micrometre stage; float glass, glossy strip, printed fiducial sheets | class | any | USD 10–30; 150–600; 100–600; 15–60 (ASSUMPTION) | 1 each |

### 7.2 Fabricated parts

| Part | Source | Material, process, tolerance | Who, cost (ASSUMPTION) |
|---|---|---|---|
| Tilt arc R 45, arc carriage, roll ring, head plate | `rig_pagesense_assembly.step` (`tilt_arc`, `arc_carriage`, `roll_ring`, `head_plate`) | PETG or PA-CF by FDM, and a 6061 plate; ±0.1 mm | hobbyist + shop, USD 30–200 |
| Mode A sled; Mode B mock nose | `rig_pagesense_sled_assembly.step`; `rig_pagesense_assembly.step` (`mock_nose`) | SLA resin, ±0.05 mm | hobbyist or online, USD 20–80 |
| Latency step flexure: 50 µm steps with ≤ 0.5 ms rise, driven by R9's LVCM-013 voice coil | PROPOSED DESIGN (no CAD) | spring-steel leaves, 6061 block | shop, USD 50–200 |

The step flexure is needed because EXP-T05 names R13's stage as its step source, and R13 is not in this build (§13).

### 7.3 Assembly and safety

**Assembly.**
1. Take R9's contact head off and fit R10's head plate. The two rigs share the frame in turn.
2. Fit the glass platen on the bed adapter and clamp the paper, the glossy strip and the fiducial sheet.
3. Put the sensor on the sled (Mode A). Mount the PAA5100JE on a flat plate at 15–35 mm.
4. Wire SPI1 to DAQ-1.
5. Mount the camera on a bracket looking at a dot beside the sensor window, with the strobe on pins 24/25.
6. Qualify the camera first, on a static dot grid.

**Safety.** The mouse-sensor lasers are low-power; still, do not look into the window. Keep the printer door closed while the head moves.

---

## 8. Test sequence and the decisions it feeds

`results/benchbuild/test_decision_map.csv` holds the full map; this is the summary. The "gate" column names the gates of `validation/prototype_stages.md` §0.

| Build | Experiment | Criteria and pass/fail line | Feeds | If it fails |
|---|---|---|---|---|
| B0 | EXP-BB01 (proposed) | AC-BB01-01…05: 0 CRC errors and 0 missing frames in 10 min at 8 kSPS; ADC noise ≤ 2.4 µV; sync residual ≤ 50 µs; 0 encoder counts lost; current step ≤ 2 ms | DEC-058 (one clock); order 0 of every gate | fix firmware or wiring before any record |
| B1 | EXP-BB02 (proposed) | AC-BB02-01: plate stack first mode ≥ 100 Hz. AC-BB02-02…04: speed, plate residual, guide stiffness | DEC-058's revisit trigger; validity of G1 | stiffen the stack or use the ±10 N plate; persistent failure reopens DEC-058 |
| B1 | EXP-T02 | AC-T02-01: F_c,min ≤ 0.3 N for Rev K's refill everywhere. AC-T02-02: U ≤ 12 mN. AC-T02-03: gaps ≤ 1 % under modulation. AC-T02-04: report per tip type and paper | DEC-050 (the F_s set point; revisited above 0.3 N); REQ-BNIB-014; G1 | another refill; above 0.3 N, DEC-050's revisit |
| B1 | EXP-T01 | AC-T01-01: closure ≤ max(3 mN, 3 % F_c). AC-T01-02: U(N) ≤ 5 mN. AC-T01-04: μ 0.09–0.40. AC-T01-05: side friction ≤ 0.2. AC-B01-03: P-6 within ±15 % in ≥ 90 % of strokes. AC-B01-20: the 0.2–2.0 N envelope covered, which needs S1's 250 g cell and ±10 N plate | DEC-058; study B's balance range; config/nib.yaml (DEC-050); DEC-066 (pre-sliding stiffness); G1, G-B | recalibrate; replace the contact model and re-run the predictions |
| B1 | EXP-BB09 (proposed) | AC-BB09-01…03: contact-channel delay ≤ 5 ms (99th percentile); ≤ 0.1 false events per minute; lift command to ink stop ≤ 50 ms | DEC-070 (the contact model); DEC-071 (lift) | change the contact channel's threshold and filtering; a faster lift |
| B2 | EXP-J17 (c) | AC-J17-04: residual ≤ 10 % mean and ≤ 25 % at the 95th percentile. AC-J17-05: release ≤ 10 % within 20 ms; touchdown travel. AC-J17-06: guide μ ≤ 0.01. AC-J17-07: ink force ±20 % | DEC-050, DEC-064; the measured load for DEC-072 through DEC-096; G1 (`prototype_stages.md` §0 lists EXP-J17 under G1); "Build the Rev K pen" (AC-J17-04) | the clutched bias b', then the unbalanced nib f (DEC-050) |
| B2 | EXP-T07 (with EXP-K22) | AC-T07-01: K_m ≥ 0.7 × the model at every node. AC-T07-05: Rev K's coil ≥ 0.7 × 0.334 / 0.272 N/√W. AC-T07-02…04: model agreement, ripple (predicted to fail), force against back-EMF | DEC-050 (pole size), DEC-062; **"Build Rev K's nib"** | larger poles (the 24 mm bore is the limit); DEC-062 revisited; the firmware uses the measured map |
| B2 | EXP-K21 | AC-K21-01…04: ≤ 0.3 Ω per wire; no failure in 43.2 M cycles at 0.1 A; preload ≤ 0.05 N; Goodman ≥ 1.5 | DEC-063; **"Build Rev K's nib"** | a 0.08 mm wire (which fails 0.3 Ω) or a beryllium-free alloy; DEC-063 revisited |
| B2 | EXP-BB04 (proposed) | AC-BB04-01…05: lead ≤ 0.3 Ω; no failure at the 1.7 mm stop; Goodman ≥ 1.5; heating within ±25 % of the model; drive ≤ 0.2 × first mode | DEC-072 through DEC-096 | the reach candidate is dropped and the 1.059 mm candidate stays |
| B2 | EXP-K20 | AC-K20-01: friction ≤ 5 mN. AC-K20-02: tilt ≤ 0.2 mrad, no wire compressed beyond half its buckling load. AC-K20-03: no race marks after ten 1 m drops | DEC-063; REQ-RVK-003; **"Build Rev K's nib"** | a lower preload or another guide; DEC-063 revisited |
| B2 | EXP-BB05 (proposed) | AC-BB05-01…03: reach drag 5.6–10.5 mN at 4 N; a preload with tilt ≤ 0.2 mrad and drag ≤ 5 mN; no marks on a bare titanium face | DEC-063 (preload); DEC-072 through DEC-096 | hardened flange inserts; another guide topology (study N) |
| B2 | EXP-BB03 (proposed) | AC-BB03-01…03: beam stiffness ±15 % of the calculation; 80–120 N/m with the interconnect; assembly tension ≤ 5 mN | DEC-072 (the soft anchor that replaces Rev K's 10,000 N/m); DEC-063 | re-etch with a corrected width; a softer interconnect |
| B3 | EXP-BB06 (proposed) | AC-BB06-01…04: endpoint ≤ 50 µm RMS; force ≥ 0.40 N; stiffness ≥ 4 N/mm; cap ≤ 0.4 N and release 0.5–0.8 N (guarded) | DEC-071; DEC-099 | 16-bit encoders or a camera-referenced loop; stiffer links; fix the cap before anything else |
| B3 | EXP-BB07 (proposed) | AC-BB07-01…03: ≥ 18 of 20 suffixes meet the grounded gate with no spring hand; ≤ 0.5 mm of ink after a refusal with 200 and 500 N/m springs; acceleration and jerk reported | DEC-071 | the moving-paper platen (study P); a faster, positively sensed lift |
| B4 | EXP-T04 | AC-T04-01: ≥ 1 kHz and ≤ 10 µm RMS. AC-T04-03: truth U ≤ 2.5 µm. AC-T04-05: dropouts ≤ 1 %, none over 300 ms. AC-T04-07: lift cut-off ≥ 2 mm, predicted to fail with a mouse-class die. AC-T04-08: ±20° of roll beside the heel pod, predicted to fail. AC-J10-04: drift and window error by DeltaPen's metric. AC-S01-02: ≤ 5 µm per sample | sensing build gate; DEC-059; DEC-062 (REQ-BNIB-017, the die); DEC-065; "Build the Rev K pen" | another die or optics; external truth stays in the loop; the heel stays a bench module |
| B4 | EXP-T05 | AC-T05-01: latency ≤ 2 ms (99th percentile). AC-T05-02: step rise ≤ 0.5 ms | the estimator's horizon | a faster sensor mode; a stiffer step source |
| B4 | EXP-BB08 (proposed) | AC-BB08-01…03: 0 silent recoveries of the absolute anchor; re-anchored error ≤ 0.1 mm (95th percentile); lost motion reported | DEC-070; DEC-071; REQ-CAP-003 | no accepted writing across an outage without a verified anchor |

**Order of the gates this first build can close.**
- **G1's contact and ink experiments** (EXP-T01 and T02, with EXP-B01's envelope) close at the end of stage S1. G1 also lists EXP-J17: its part (c) runs on R9's frame in S2, while parts (a) and (b) need a built nose or nib, so G1 as a whole cannot close in this build.
- **The G2 part of "Build Rev K's nib"** closes at the end of stage S2. It needs EXP-T07 on the Rev K coil, EXP-K21 with no wire failure, and EXP-K20's friction and drops (`prototype_stages.md` §0).
- **DEC-072's choice** follows DEC-096's rule at the same meeting.
- **"Build the Rev K pen"** cannot close in this build. It also needs EXP-K23 (the head), EXP-T10 on a nib (R13) and EXP-T04's lift result.

---

## 9. Budget and schedule

### 9.1 The minimum viable first build (weeks 0–4)

The first build is DAQ-1 plus R9 with dead-weight F_c, no encoders, a printed arc, the K3D40 ±2 N and the LSB200 100 g. It costs **USD 4,352–7,732** (stage S0 in `cost_schedule.csv`):
- USD 2,220 of it has a seen price (MANUFACTURER);
- the largest ASSUMPTION lines are the K3D40 (900–1,900), the LSB200 (450–900), and the CNC cartridge and bed adapter (250–850).

Add USD 250–650 for a soldering station and hand tools, and a further USD 1,466–1,766 for an oscilloscope, a 4-wire meter and a bench supply if the lab lacks them. With everything, the first build costs USD 6,068–10,148.

It answers:
- F_c,min per refill and paper, at fixed forces (AC-T02-01, AC-T02-04);
- N and friction at 35, 50 and 75° with the axial closure check (AC-T01-01, T01-02, T01-04, T01-05);
- the plate's first mode (AC-BB02-01);
- the contact channel's delay (AC-BB09-01, -02).

### 9.2 Cost per stage

All figures are USD, sums of line ranges from `cost_schedule.csv`.

| Stage | Weeks | What | Core | With instruments if the lab lacks them |
|---|---|---|---|---|
| S0 | 0–2 | orders; pre-registration; DAQ-1 bring-up; printer kit; first-build R9 parts | 4,352–7,732 | 6,068–10,148 |
| S1 | 1–4 | R9 G1 runs, plus the standard upgrades (±10 N plate, 250 g axial cell, voice coil, 2 × LM13, OPA548, CNC arc) | 2,193–5,193 | same |
| S2 | 3–8 | G2 coupons: force maps, wires and shuttle, guides, anchor, counter-face bench | 5,808–17,936 | 6,848–22,976 |
| S2b | 8–12 | custom magnets, only if AC-T07-02 passes | 150–600 | same |
| S3 | 6–12 | five-bar build, EXP-BB06 and BB07 | 987–2,103 | same (reuses B1/B4 instruments) |
| S4 | 6–12 | R10, EXP-T04, T05 and BB08 | 628–2,475 | same |
| **All** | **0–12** | | **13,968–35,439** (without S2b) | **+2,756–7,456** |

### 9.3 Schedule

| Week | Work | Result |
|---|---|---|
| 0 | Pre-register EXP-T01, T02, BB01 and BB02 (§0.2). Request quotes and order: K3D40 ×3, LSB200 (100 g, 250 g and 10 g), LVCM-013, LM13 ×2, coil winding, lapped races, precision etching, the flex interconnect, the aged C17200 wire, stock magnets, page-sensor boards, Faulhaber motors | order book open |
| 1–2 | DAQ-1 bring-up (EXP-BB01); printer kit assembled; first-build R9 parts printed and CNC'd | one clock (DEC-058) |
| 2–4 | R9 qualification (EXP-BB02) as the sensors arrive; EXP-T02 fixed-force lines on 3+ refills × 6 papers × 35/50/75°; EXP-T01 on the nominal pair and a reduced grid; EXP-BB09 | **G1: F_c,min, friction, side load** |
| 3–5 | Wire coupons soldered; first modes measured; fatigue batch 1 (Rev K wires, about 3.3–5 days) | |
| 4–6 | Force-constant coupons with stock magnets (EXP-T07/K22); EXP-J17 (c) on R9's frame; the anchor coupon (EXP-BB03) | K_m map; residual side load |
| 5–8 | Fatigue batch 2 (reach wires, about 7 days); guide coupons once the races arrive (EXP-K20, BB05); drops and profilometry | |
| 6–9 | Five-bar parts and assembly; EXP-BB06 | |
| **8** | **G2 meeting**: the "Build Rev K's nib" inputs; DEC-096's duty re-run with the measured load, K_m, drag and anchor | DEC-062/063 confirmed or revisited; DEC-072 chosen |
| 9–12 | EXP-BB07 (word replay against spring hands); R10 (EXP-T04, T05, BB08) | **the grounded route (DEC-071); the sensing build gate** |

The schedule slips one-for-one with the force-sensor lead time. If the K3D40 or LSB200 lead time is over 6 weeks, start with the low-cost G1 build of `docs/measurement_rig.md` §2.9: TAL221 cells and NAU7802 boards. It still needs a three-axis plate for friction. EXP-T02's ink-force lines need only dead weights and the scanner, so they can run before the plate arrives.

### 9.4 Who can do what

| Task | Skilled hobbyist or small team | Machine shop | Specialist supplier or service |
|---|---|---|---|
| DAQ wiring, firmware upload, printer kit, printed fixtures (arcs, sled, holder, guards), dead-weight calibration, scanning, blind coding, analysis | ✓ | | |
| Cartridge frame, bed adapter, head plates, coupon stator block, five-bar base, supports, capstans and links, clamp blocks (EDM slot), fatigue shuttle, anchor frame, counter-face parts | | ✓ | |
| Lapped 440C races: harden, grind and lap to ≤ 1 µm | | precision grinding shop | |
| Soldering 0.10 mm C17200 into clamps under a microscope; hand-winding a first coil with bondable wire | ✓ (skilled) | | |
| Bonded racetrack coils to ±0.03 mm | | | coil-winding service |
| Aged C17200 fine wire; any heat treatment of it (DEC-097 proposed) | | | wire supplier with beryllium controls |
| Custom magnets | | | magnet maker |
| Anchor beams to ±0.01 mm | | | precision photo-etcher or laser micromachining |
| Flexible interconnect | | | flex-PCB prototype service |
| CFRP cutting | | | supplier (dust) |
| Race profilometry; calibration certificates | | | metrology lab; the sensor makers |
| Laser welding | not used: C17200 is soldered or crimped (DEC-063). Study B's titanium wires (EXP-B25) would need a supplier with fume extraction; they are not in this build | | |

### 9.5 Lead times

| Item | Lead time | Label |
|---|---|---|
| Teensy, ADS131M08EVM, MAX31856, DRV5055, AS5047P boards, DRV8874 carriers, stock magnets, MR63-ZZ, weights, V39 II scanner, Rigol scope | 1–5 days, in stock | MANUFACTURER (AMF-220, 300, 234, 302, 307, 305, 309, 310, 316, 315, 314, 321) |
| Prusa CORE One+ kit | 1–3 business days of preparation, plus shipping | MANUFACTURER (AMF-231) and ASSUMPTION (shipping) |
| Faulhaber 2224 | about 5 days from Faulhaber, DigiKey marketplace | MANUFACTURER (AMF-304) |
| VPG shunt | stock due 12-Oct-2026 | MANUFACTURER (AMF-303) |
| OPA548T | stock due 30-Nov-2026; OPA549T due 02-Dec-2027 | MANUFACTURER (AMF-301) |
| Goodfellow CuBe2 wire | about 2 weeks | MANUFACTURER (AMF-311) |
| K3D40, LSB200, LVCM-013, LM13, Nano17 | 2–6 weeks | ASSUMPTION (quotes) |
| Coil winding; lapped races | 3–6 weeks | ASSUMPTION |
| Precision etching | 2–4 weeks | ASSUMPTION; Ponoko's 10-day minimum applies to a service that cannot make the beams (AMF-313) |
| Custom magnets | 4–8 weeks | ASSUMPTION |
| Page-sensor boards | unknown: PMW3360 breakout out of stock; PAA5100JE on pre-order; PMW3610 not listed by the large distributors | MANUFACTURER (OPT-100, OPT-90, OPT-101) |

---

## 10. Data pipeline

### 10.1 Which script reads which file

Every row below was exercised on synthetic data by `results/benchbuild/tools/pipeline_check.py`, and all 11 steps pass (SIM; `results/benchbuild/pipeline_check.json`; about 3 s). The rig's own checks also pass on this checkout: `python3 -m rig.selftest --no-write` gives 49 of 49, and `python3 -m pytest rig/tests -q -p no:cacheprovider` gives 30 passed (SIM).

| Measurement file (template) | Produced by | Read by | Analysis | Check (SIM result) |
|---|---|---|---|---|
| `raw.bin`, write-once: SAMPLE, EVENT, PAGE and IMU frames with CRC | DAQ-1 firmware over USB; `python3 -m rig.logger --port … --out DIR` | `python3 -m rig.logger --replay raw.bin --out DIR` → `session.npz`, `session.json` (stats, SHA-256) → `rig.logger.load_session` | `rig.convert.to_units(session, CHANNEL_MAPS[rig], cal)` → `events_by_kind` → `split_by_markers` (one record per MARK) | step A: 3,201 samples, 0 CRC errors, 0 missing frames |
| `r9_axial_cell_calibration.csv`, `r9_plate_calibration.csv`, `r9_guide_stiffness.csv` | dead weights and pulls at the test angle | csv | `rig.calib.fit_bridge`, `fit_plate` + `apply_plate`, `fit_guide_stiffness` | step A |
| R9 stroke records | the above | `rig.contact.analyse_stroke(t, F_c, F_plate, xy, θ, φ)` | friction vector, closure, R_⊥/F_c, `p6_check`, `side_load_table`, `balance_range` | step A: μ within 0.8 %, R_⊥/F_c within 0.54 %, closure 0.06 mN |
| s2r-bench-1 records (`manifest.json`, `group/nnnn_k.npz` + `nnnn.json`) | `rig.convert.to_bench` | `s2r.io.load`; the s2r identification (for example `s2r.exp_b01b02`) | — | step A: identical arrays after reload |
| 16-bit TIFF scans + `ink_scan_register.csv` | R3 scanner | PIL → numpy (Pillow comes with matplotlib) | `rig.ink.analyse_line`, `minimum_ink_force` | step B: F_c,min 0.141 against 0.145 N |
| `t07_force_map.csv` | R12 with the coupon | csv → per-node arrays | `rig.coupon.km_map` (and `attraction_fit`, `lateral_stiffness`, `mode_fit`, `tempco`) | step C: K_f within 0.25 % |
| `anchor_stiffness.csv` | balance + micrometer | csv | `rig.calib.fit_guide_stiffness` (the slope is the stiffness) | step D: 95.97 against 96 N/m |
| `guide_drag_sweep.csv` | 10 g cell + stage | csv | `guide_drag()` in `pipeline_check.py`: half the forward-minus-return force | step E: 5.98 against 6.0 mN |
| `k21_wire_log.csv` | current source + 4-wire channels | csv | `wire_failure()` in `pipeline_check.py`: open circuit or > 2 % step | step F: failure found at the right cycle count, no false alarm |
| `thermal_run.csv` | resistance thermometry, thermocouples | csv | `rig.thermal.coil_temperature`, `fit_1node`, `fit_2node` | step G: R12, R2a within 0.7 % |
| `fivebar_encoder_truth.csv`, `fivebar_force_map.csv` | controller Teensy + camera; K3D40 | csv | `fivebar_fk()` in `pipeline_check.py`; `wholepen.grounded.FiveBar.kinematics` (J) | step H: 11.6 µm RMS with 14-bit counts |
| R10 `raw.bin` with PAGE frames + `r10_pose_matrix.csv` | DAQ-1 (page sensor on SPI1) | logger replay → `to_units(CHANNEL_MAPS['R10'])` + PAGE time base | `rig.pagesense.qualify`, `sim2j_page_model`, `patch_sim2j` | step I: latency 1.599 against 1.600 ms |
| Device logs with their own clock (five-bar controller, page-sensor MCU) | the device | csv | `rig.sync.decode_widths`, `fit_clock` | step J: 5.9 µs worst residual |
| `analysis/verdict.yaml` | the analysis | — | `rig.uncertainty.decide` (simple at TUR ≥ 4, guarded otherwise) | step K |

### 10.2 What the check found missing

These are gaps to fill before or while the first data arrive.
1. **ADC delay.** `rig.convert` computes `t_adc_s`, the 375 µs sinc3 delay at 4 kSPS, but does not resample. `rig.contact.analyse_stroke` takes a single time vector, so forces must be interpolated onto the encoder clock first. The pipeline check does this with `np.interp`.
2. **PAGE and IMU frames.** `rig.convert` converts only SAMPLE frames. PAGE and IMU frames must be mapped onto the SAMPLE clock by `(t_cyc − t0)/f_cpu` with the first SAMPLE's `t0`. The check does this in three lines; `rig/` has no helper.
3. **No rig/ function** exists for guide drag, wire-failure detection, five-bar forward kinematics, the wire's first-mode check, or head position from printer move timing (the first build's substitute for encoders). The first three are written and SIM-checked in `pipeline_check.py`. The first mode is predicted in `bench_calcs.py`, but picking it from a measured sweep is not written, and neither is the move-timing reconstruction.
4. **Scans** need a TIFF reader. Pillow is installed with matplotlib but is not pinned in `requirements.txt`.
5. **Firmware.** DAQ-1's firmware has only been checked against stubs, never compiled for the Teensy (`docs/measurement_rig.md` §11 item 3). The five-bar's controller firmware does not exist.

### 10.3 Templates, checklist and notebook

- `results/benchbuild/templates/` holds blank CSVs whose headers match the readers above:
  - instrument register;
  - run order;
  - R9 calibrations and tap test;
  - ink scan register;
  - the T07 force map;
  - the wire mode check and wire log;
  - the anchor;
  - guide drag and tilt;
  - the thermal run;
  - five-bar encoder truth, force map and word replay;
  - R10 pose matrix and re-anchoring trials;
  - contact timing.
- The same folder holds `record_template.yaml` and `verdict_template.yaml`, both following `validation/records/README.md` §3, and `lab_notebook_template.md`.
- `results/benchbuild/first_measurement_checklist.md` takes the first session of each build from paperwork to a signed verdict.

---

## 11. Safety, all builds

No participant takes part in anything in this plan. Every build is bench-only, so gate G-S does not arise; its principle still stands (`prototype_stages.md` §1).

| Hazard | Where | Control | Source |
|---|---|---|---|
| Airborne beryllium from C17200 | wire coupons, clamps | buy aged wire; no in-house heat treatment; shear-cut only; no abrasive cutting, grinding, sanding, pickling or acid cleaning; solder under local exhaust or crimp; never weld; bag and label waste; wash hands; no food at the bench | DEC-063; DEC-097 (proposed); AMF-18; AMF-319 (NGK SDS §2.1, §8: OSHA PEL 0.2 µg/m³, ceiling 2 µg/m³); AMF-320 (OSHA: STEL 2.0 µg/m³, action level 0.1 µg/m³; C17200 with about 2 % Be is not exempt) |
| Skin sensitisation from C17200; slivers of 0.1 mm wire | handling | nitrile gloves; tweezers | AMF-319 (Skin Sens. 1) |
| Flux and solder fumes | all soldering | bench fume absorber; lead-free solder; ventilation | AMF-317 |
| Magnets snapping and chipping; pacemakers | coupons, encoder magnets | non-magnetic jig, one at a time, eye protection; signage; heated runs below the supplier's maximum temperature | ASSUMPTION: the maximum temperature is to be read from the supplier's data |
| Pinch points and entanglement | CoreXY gantry and belts; five-bar capstans and links; fatigue crank at 4,000–9,000 rpm | printer door closed; guards; latching emergency stops; hands out while motors are enabled | DEC-099 (proposed) |
| Unexpected force on a person | five-bar | 0.4 N software cap; rated-current hardware limit (up to 1.06 N possible, CALCULATION); 0.5–0.8 N breakaway coupling; springs instead of hands | DEC-099 (proposed); `bench_calcs.json` |
| Hot surfaces | printer chamber up to 55 °C (AMF-231); coils under current | thermocouples; the 100 °C coil stop rule of EXP-J17; ≥ 30 s cooling above 0.3 I_max (EXP-T07) | `bench_protocols.md` |
| Lasers | HG-C1030 (655 nm), laser lever, mouse-sensor emitters | class 2 or 3R only, with signage; do not look into windows | `bench_protocols.md` §0.10 |
| Sharp edges | etched 301 foil; cut wire; glass underlays | gloves; edge-ground glass | — |
| Dust | CFRP cutting | a supplier cuts it | — |
| Projectiles | 1 m drop tests with 0.8 mm balls | eye protection; a tube guide | — |
| Solvents | IPA; SLA resin | gloves; ventilation | — |
| Electrical | current amplifiers (±15–30 V), mains adapters | certified adapters; heat-sunk amplifiers; current limits below coil ratings | — |

---

## 12. Evidence rows added

The rows are in `results/benchbuild/evidence_rows.csv`. They use the 23-column header of `docs/evidence.csv`, CRLF line endings, and were all retrieved on 2026-09-30.

| Ids | Content |
|---|---|
| AMF-300 | ADS131M08EVM: DigiKey USD 328.11, 2 in stock; TI kit contents |
| AMF-301 | OPA548T back-ordered (DigiKey, TI); OPA549T back-ordered; OPA564 USD 9.51 |
| AMF-302, 303 | DRV5055A4 USD 0.87; VPG 0.1 Ω 0.1 % foil shunt USD 13.05, due 12-Oct |
| AMF-304 | Faulhaber 2224 (DigiKey 2224.11000 USD 122.60; RS 2224U012SR ratings) |
| AMF-305, 306 | Pololu DRV8874 carrier USD 11.94; maxon ESCON Module 24/2 EUR 97.68 (NRND) |
| AMF-307, 308 | AS5047P board USD 19.40 (IC discontinued at DigiKey, 14-bit); Mean Well GST60A12-P1J USD 19.40 |
| AMF-309, 310 | stock N52 magnets (supermagnete 5 × 5 × 3, EUR 0.35; K&J B333-N52, USD 0.56, Br 14,800 G) |
| AMF-311, 312, 313 | Goodfellow CuBe2 wire and 301 foil starting prices; Ponoko etching limits (±0.13 mm, 1 mm minimum feature) |
| AMF-314, 315, 316, 317, 318 | Epson V39 II USD 129.99; Mettler Toledo M1 weights USD 535.50; MR63-ZZ USD 4.38; Hakko FA400-04 USD 93.79; Panasonic HG-C1030 USD 439.60 |
| AMF-319, 320 | NGK C17200 SDS (exposure operations, limits, controls); OSHA beryllium limits |
| AMF-321, 322 | Rigol DHO804 USD 459.00; Siglent SDM3065X USD 857.00 |
| OPT-100, 101 | PMW3360 breakout EUR 29.90, out of stock; PMW3610 at JLCPCB ("Extended", no price or stock shown) |

These existing rows are re-used: AMF-02, 15, 18, 19, 20, 220–225, 231, 233, 234, 236–238, 251; OPT-61, 88–91; CON-21, CON-100.

**Pages that gave no price**, and so carry ASSUMPTION ranges:
- me-systeme.de (HTTP 403) and pm-instrumentation.com (price after login), for the K3D40;
- FUTEK (shows $0.00), for the LSB200;
- Moticont (specifications only);
- Thorlabs (script-rendered pages);
- Omega (HTTP 403);
- Arducam and its resellers (HTTP 403);
- Pimoroni (pre-order).

---

## 13. Open items

1. **Prices not seen.** The K3D40, LSB200, LVCM-013, LM13, Nano17, XYZ stages, OV9281, PAA5100JE, Si3N4 balls, lapped races, coil winding, precision etching and custom magnets are all ASSUMPTION ranges. A request for quotation in week 0 pins them. They make up 72–90 % of the low-end core cost of B1, B2 and B4 (§2).
2. **Supply risks.**
   - OPA548T and OPA549T are back-ordered (AMF-301).
   - The PMW3360 breakout is out of stock, the PAA5100JE is on pre-order, and the PMW3610 is not at the large distributors (OPT-100, OPT-90, OPT-101).
   - The AS5047P IC is discontinued at DigiKey, though its boards are in stock (AMF-307).
   - The shunts are due on 12 October (AMF-303).
3. **No CAD** exists for:
   - the EXP-J17 (c) counter-face fixture;
   - the fatigue shuttle;
   - the wire clamps;
   - the anchor test frame;
   - R10's latency step flexure;
   - the translation-coupon stator (its solids exist in the STEP files, but no drawing does);
   - the five-bar's cable routing, tensioner, pen lift and encoder mounts, which the pass's CAD leaves unresolved.
4. **Kt on 0.10 mm wires.** A strain gauge cannot be bonded on the wire. The plan proposes 10× scaled coupons, since Kt depends on the geometry. The lead should confirm the method, because AC-K21-04, AC-BB04-03 and AC-B25-01 need a measured Kt.
5. **The titanium flange as a raceway.** 2.6 GPa of Hertz stress on Ti-6Al-4V (CALCULATION) probably indents it. Hardened inserts may be needed in the pen (AC-BB05-03 tests this). The CAD also has no ball retainer.
6. **Protocol wording.** DEC-098 (proposed) changes EXP-B25's "about 60 h at 200 Hz" in bench_protocols.md, which EXP-K21 follows. If DEC-098 is accepted, the lead edits that text.
7. **Id format.** The ids EXP-BB01…BB09 and AC-BB0x-yy do not match `validation/check_criteria.py`, whose patterns expect one letter and two digits (`AC-[A-Z]\d\d-\d\d`, `EXP-[A-Z]\d\d`). The lead either widens the patterns or renumbers when these rows go into `validation/acceptance_criteria.csv`. The proposed criteria otherwise pass the checker's other rules: requirement ids exist, and the direction and status vocabularies are respected.
8. **Firmware and software.** DAQ-1's firmware has never been compiled for the Teensy. The five-bar controller firmware is not written. `rig/` lacks the helpers listed in §10.2: resampling onto one clock, PAGE and IMU time mapping, and five analysis functions, of which three are drafted in `pipeline_check.py`.
9. **Study N may change the candidates.** The coupon fixtures accept either candidate. Freeze the coil and race drawings when study N reports; the stock-magnet coupons do not depend on it.
10. **R10's step source.** EXP-T05 names R13's stage, which is not in this build, so a small step flexure is proposed instead (§7.2).
11. **Encoder resolution.** `wholepen/grounded.py` assumes 16-bit output encoders, while the build uses 14-bit (8 µm against 2 µm of endpoint quantisation, CALCULATION). EXP-BB06 decides whether that matters. A 16-bit encoder was not priced.
12. **C17200 wire.** Goodfellow's 0.10 mm size in an aged temper is not confirmed (the table loads dynamically). The wire's resistance coefficient, needed for AC-BB04-04, is not in the ledger and is calibrated on the coupon.
13. **Not in this build.** Rev K's head mock-up (EXP-K23: the SQL-RV-1.8 is for volume customers, AMF-15), Hall interference (EXP-T09), EXP-T08 (its keeper pull needs a sensor above about 11 N, such as R12's K3D40 ±50 N; its thermal steps), and EXP-J17 (a) and (b), which need a built nose or nib. They come next.
14. **Money.** Currency conversion uses an ASSUMED 1.05–1.25 USD/EUR. Shipping, tax, duty and labour are excluded.
15. **Printer.** The CORE One's firmware must run with the extruder parked and its heaters at 0, and must toggle a marker output from G-code. Neither has been checked (§4.4).

---

## 14. Proposed rows for the lead

### 14.1 Decisions (DEC-095…099)

The full text is in `results/benchbuild/proposed_decisions.csv`.

| Id | Decision (proposed) | Alternatives | Basis | Revisit if |
|---|---|---|---|---|
| DEC-095 | **The first bench build is DAQ-1 plus R9 (G1), ordered in week 1 with every long-lead item for the G2 coupons, the five-bar and R10.** G1 runs in weeks 1–4: EXP-T02's minimum ink force first (with dead weights if the voice coil is late), then EXP-T01. No coupon geometry is frozen before G1's F_c,min and side load are known. The first force-constant coupons use stock magnets, with predictions regenerated at the as-built size (§0.2); custom magnets are ordered only after AC-T07-02 passes | coupons or the five-bar first; a six-axis F/T sensor for G1; custom magnets now | report §9 order; DEC-058; DEC-072; this plan's lead times (AMF-301, quotes) | a K3D40 or LSB200 lead time over 6 weeks (then the low-cost G1 build of `docs/measurement_rig.md` §2.9 starts first) |
| DEC-096 | **DEC-072's choice is made by re-running the pass's duty screen (`python -m revk.improve`) with measured inputs.** The screen's `residual_N` bundles contact, balance and guide loads, and it models no gravity term (`revk/improve.py`, `matched_force_duty`). The inputs are: the residual lateral load at the carrier (EXP-J17 (c), 95th percentile over 35–75° and roll, plus the moving mass's weight across the axis, 29.5 mN at 35° by CALCULATION); the K_m map (EXP-T07); the guide drag at the chosen preload (EXP-K20, BB05); and the anchor stiffness (EXP-BB03). The 1.5 mm candidate is taken only if its re-run worst copper loss stays within the 0.15 W allocation and EXP-BB04 passes. **Provisional reading** (CALCULATION, interpolating the pass's own 20/40/80 mN points): 0.15 W is reached at about 34 mN for the 1.5 mm candidate and about 53 mN for the 1.059 mm candidate. The calculated loads at 35° sum to about 49–51 mN: gravity 29.5, face residual at the 95th percentile 11.2–13.1, guide drag 8.1 (`bench_calcs.json`, a conservative sum of magnitudes) | choose on the calculated 20 mN screen now; choose on EXP-T01's side load alone | `mechanics_study.json`; `bench_calcs.json`; DEC-072 | the duty screen misses the first nib's measured coil heat (EXP-J17 (b), T12) by more than 20 % |
| DEC-097 | **Beryllium-copper wire is bought already age-hardened, so no heat treatment is done in-house.** It is cut with shears or flush cutters only, and never abrasive-cut, ground, sanded, pickled or acid-cleaned. Joints are soldered under a bench fume absorber, or crimped; nothing is welded. Offcuts, broken coupons and wipes go into sealed, labelled bags. No food or drink at the bench; hands are washed | age-harden in-house; laser-weld clamps (as study B did for titanium); abrasive cut-off | NGK SDS §2.1 exposure operations (AMF-319); OSHA limits (AMF-320); AMF-18; DEC-063 | no supplier can deliver aged 0.10 mm wire (then a supplier with beryllium controls heat-treats it) |
| DEC-098 | **Wire fatigue coupons (EXP-K21, B25, BB04) are driven at no more than 0.2 × the first transverse mode measured on each coupon.** Failure is detected by 4-wire resistance in current-carrying wires: an open circuit or a step over 2 %. Several coupons run in parallel on one crank shuttle, and 43.2 M cycles take 3–8 days per batch | 200 Hz as the protocol suggests (about 60 h); resonance tracking only | CALCULATION: first modes about 336–373 Hz (34 mm) and 487–763 Hz (26.8 mm); at 200 Hz the clamp stress rises about 90 % (34 mm) and 12–33 % (26.8 mm) | two drive frequencies on one coupon lot give the same cycles to failure |
| DEC-099 | **The grounded five-bar is benched with a passive 24 mm dummy pen and spring hand simulants, never with a person's hand, until a safety gate like G-S is written for it.** The first build includes: a hardware current limit at rated current; the 0.4 N cap in software (at rated current the linkage can still push about 1.06 N at its worst pose, CALCULATION); a breakaway pen coupling releasing at 0.5–0.8 N as the physical backstop; guards; and a latching emergency stop. Accepted-word results are claimed only from its measured replay (EXP-BB06, BB07), not from the rigid model | attach the fine nib first; test with a hand on the pen | DEC-071; the pass's 0 of 20 against 200 and 500 N/m grips; `prototype_stages.md`'s G-S principle | EXP-BB06 and BB07 pass and a G-S-type gate exists |

### 14.2 Experiments (EXP-BB01…BB09)

Each is proposed only where no existing experiment covers the need. The full text is in `results/benchbuild/proposed_experiments.csv`.

| Id | Gate | Rig | Title | Why no existing experiment covers it |
|---|---|---|---|---|
| EXP-BB01 | all (order 0) | DAQ-1 | DAQ-1 bring-up and time-base qualification | `docs/measurement_rig.md` §1.3 lists the bring-up steps with no id or criteria |
| EXP-BB02 | G1 | R9 | Frame qualification: plate mode, motion quality, in-situ calibrations | DEC-058 names the tap test as its falsifier, but no criterion judges it |
| EXP-BB03 | G2 | R12 + balance | The axially soft wire anchor (the pass's floating anchor) | EXP-K21 measures preload on Rev K's diaphragm, not the anchor's stiffness |
| EXP-BB04 | G2 | fatigue shuttle + DAQ-1 | The reach candidate's eight 34 mm C17200 wires at the 1.7 mm stop | EXP-K21's criteria fix Rev K's 26.8 mm wires and stop |
| EXP-BB05 | G2 | R12 stage + 10 g cell + laser lever | Ball-guide drag and tilt against preload, both guides | EXP-K20 tests one guide at one preload; the pass predicts 8.07 mN at 4 N, above K20's 5 mN line |
| EXP-BB06 | none yet | five-bar + K3D40 + camera | Five-bar qualification: kinematics, force, stiffness, force cap | no experiment tests the five-bar |
| EXP-BB07 | none yet | five-bar + passive pen + R3 | Accepted-word replay on paper against spring hands | the grounded results are SIM only |
| EXP-BB08 | sensing build gate | R10 + camera | Page anchoring through lift and occlusion | EXP-T04 judges the lift cut-off and dropouts, not absolute re-anchoring |
| EXP-BB09 | sensing and contact | R9 | Contact-channel delay, false contacts and lift timing | AC-B05-10 judges axial-force noise, not the contact decision's delay |

### 14.3 Criteria (33 rows)

The rows use the columns of `validation/acceptance_criteria.csv` and are in `results/benchbuild/proposed_criteria.csv`, with the full metric and basis text.

| Id | Req. | What | Line | Status |
|---|---|---|---|---|
| AC-BB01-01 | — | CRC errors and missing frames, 10 min at 8 kSPS | both met (0; 0) | derived |
| AC-BB01-02 | — | ADC noise, inputs shorted, gain 128, 4 kSPS | ≤ 2.4 µV RMS (2 × MFR 1.20 µV) | hypothesis |
| AC-BB01-03 | — | sync-pulse clock fit, largest residual | ≤ 50 µs | derived |
| AC-BB01-04 | — | encoder loop-back at 0.5 M counts/s | = 0 counts lost | hypothesis |
| AC-BB01-05 | — | current step 10–90 % and DC error | both met (≤ 2 ms; ≤ 1 % FS) | hypothesis |
| AC-BB02-01 | — | plate stack first mode (tap test) | ≥ 100 Hz | derived |
| AC-BB02-02 | — | steady-window speed within ±20 % | ≥ 95 % | hypothesis |
| AC-BB02-03 | — | plate calibration residual | ≤ 0.2 % FS | hypothesis |
| AC-BB02-04 | — | guide stiffness | within 17.9–33.3 N/m | hypothesis |
| AC-BB03-01 | — | anchor beam stiffness against 4 E w t³/L³ with measured t, w | within 0.85–1.15 | hypothesis |
| AC-BB03-02 | — | anchor with its interconnect | within 80–120 N/m | derived |
| AC-BB03-03 | REQ-BNIB-007 | assembly tension on the eight wires | ≤ 5 mN | derived |
| AC-BB04-01 | REQ-RVK-004 | lead resistance (two wires in parallel) | ≤ 0.3 Ω | requirement |
| AC-BB04-02 | REQ-BNIB-007 | cycles at the 1.7 mm stop with 0.1 A per wire | no failure in 43.2 M | derived |
| AC-BB04-03 | REQ-BNIB-007 | Goodman factor with measured Kt and tension | ≥ 1.5 | requirement |
| AC-BB04-04 | — | wire rise above its clamps at 0.16 A against the model's 45 K | within 0.75–1.25 | hypothesis |
| AC-BB04-05 | — | fatigue drive ÷ measured first mode (validity; also for K21, B25) | ≤ 0.2 | derived |
| AC-BB05-01 | — | reach guide drag at 4 N and the 35° couple | within 5.6–10.5 mN | hypothesis |
| AC-BB05-02 | REQ-RVK-003 | at the lowest preload with tilt ≤ 0.2 mrad, the drag | both met (tilt ≤ 0.2 mrad; drag ≤ 5 mN) | derived |
| AC-BB05-03 | — | marks on a bare Ti flange after drops | none | hypothesis |
| AC-BB06-01 | — | endpoint from encoders against camera truth (held-out poses) | ≤ 50 µm RMS | hypothesis |
| AC-BB06-02 | — | continuous force, lowest over directions and poses | ≥ 0.40 N | derived |
| AC-BB06-03 | — | stiffness at the pen holder | ≥ 4 N/mm | hypothesis |
| AC-BB06-04 | — | force cap and breakaway release (guarded) | both met (≤ 0.4 N; release 0.5–0.8 N) | derived |
| AC-BB07-01 | — | suffixes meeting the grounded gate, no spring hand | ≥ 18 of 20 | hypothesis |
| AC-BB07-02 | — | ink after refusal, 200 and 500 N/m springs | ≤ 0.5 mm | hypothesis |
| AC-BB07-03 | — | acceleration and jerk of every suffix | reported | derived |
| AC-BB08-01 | — | silent recoveries of the absolute anchor in ≥ 100 outages | = 0 | derived |
| AC-BB08-02 | REQ-RVJ-C05 | absolute error after re-anchoring, 95th percentile | ≤ 0.1 mm | derived |
| AC-BB08-03 | — | lost motion per outage | reported | derived |
| AC-BB09-01 | REQ-CTRL-003 | contact-decision delay against plate truth, 99th percentile | ≤ 5 ms | derived |
| AC-BB09-02 | — | false contact or lift decisions per minute | ≤ 0.1 | hypothesis |
| AC-BB09-03 | — | lift command to ink stop (R9 voice-coil lift) | ≤ 50 ms | hypothesis |

---

## 15. Files and how to run

```bash
python3 results/benchbuild/tools/build_tables.py     # BOMs, cost and schedule, map, proposed rows, evidence rows, templates (< 1 s)
python3 results/benchbuild/tools/bench_calcs.py      # CALCULATION: wire modes, anchor foil, selection thresholds, loads, five-bar bounds, R9 force reach (< 5 s)
python3 results/benchbuild/tools/pipeline_check.py   # SIM: synthetic data through the file formats and rig/ analyses (about 3 s)
python3 -m rig.selftest --no-write                   # 49 of 49 (SIM)
python3 -m pytest rig/tests -q -p no:cacheprovider   # 30 passed
```

All three scripts use `rig/`, `s2r/` and `wholepen/` read-only. They write only into `results/benchbuild/`, plus a temporary directory outside the repository.
