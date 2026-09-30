# First-measurement checklist (bench build plan, study H)

**Status: PROPOSED PROCEDURE. Nothing has been built or measured.** Use this list for the first session of each build in `docs/bench_build_plan.md`. A box is ticked only when its evidence is written in the lab notebook (`templates/lab_notebook_template.md`) or the record (`validation/records/README.md`). If a box cannot be ticked, stop and write why in the notebook: a skipped check is a deviation, not a pass.

## A. Before anything is powered (every build)

- [ ] The experiment is pre-registered (`validation/bench_protocols.md` §0.2). The protocol text, the `AC-…` ids used and the analysis code are frozen at a git commit. The commit hash is written in `record.yaml` (`templates/record_template.yaml`).
- [ ] The frozen prediction file for the comparison exists, with `stabpen.provenance` metadata. If the hardware differs from the model, for example stock magnets, the prediction is regenerated at the as-built values first.
- [ ] The instrument register `templates/instruments.csv` lists every instrument with its serial, calibration certificate and due date. No instrument is past its due date.
- [ ] The randomised run order is generated with a logged seed (`templates/run_order_EXP-T01.csv` for G1).
- [ ] Safety walk-through is done (plan §11):
  - [ ] Printer heaters are at target 0 and the extruder is parked.
  - [ ] Guards are fitted and the emergency stop works (five-bar, fatigue shuttle).
  - [ ] Magnets are stored in their jig.
  - [ ] Laser signage is posted.
  - [ ] Fume absorber is placed at the soldering station.
  - [ ] Beryllium-copper waste bag is labelled.
  - [ ] No participant is in the room: the first build is bench-only (`validation/prototype_stages.md` G-S principle).
- [ ] Environment is logged: room temperature and relative humidity. Papers have been conditioned for 24 h at 23 °C and 50 % RH (ISO 12757-1 test atmosphere, LIT CON-21).

## B. DAQ-1 bring-up (EXP-BB01; `docs/measurement_rig.md` §1.3)

- [ ] Firmware `rig/firmware/rig_daq/rig_daq.ino` is built with Arduino IDE ≥ 2.3.10, Teensyduino 1.62 and QuadEncoder (MFR AMF-237/238). The build hash is written down.
- [ ] Boot text shows `crc_check=0x29B1` and the ADC CLOCK register value (0xFF0E at 4 kSPS).
- [ ] Ten minutes at 8 kSPS with every channel on: `session.json → stats` shows 0 CRC errors and 0 missing frames (AC-BB01-01).
- [ ] Inputs shorted at gain 128 and 4 kSPS: RMS noise per channel ≤ 2.4 µV (AC-BB01-02; MFR 1.20 µV, AMF-221/222).
- [ ] Loop-backs:
  - [ ] Sync out to DUT in: `rig.sync.fit_clock` residual ≤ 50 µs (AC-BB01-03).
  - [ ] Camera trigger to marker in.
  - [ ] PWM through the RC filter to a spare ADC channel.
  - [ ] Quadrature generator to each encoder input: 0 counts lost in 10⁶ (AC-BB01-04).
- [ ] Current output step into the R9 voice coil: 10–90 % in ≤ 2 ms and DC error ≤ 1 % (AC-BB01-05). Skip this item in the minimum viable build, which uses dead weights.
- [ ] The replay path works on this session: `python3 -m rig.logger --replay DIR/raw.bin --out DIR2` reproduces `session.npz`. `raw.bin` is read-only and its SHA-256 is in `session.json`.

## C. R9 frame and sensors (EXP-BB02)

- [ ] Before any sensor is mounted, the printer passes its own self-test.
- [ ] The head moves the 190 g contact head without layer shifts at the planned accelerations (0.5 m/s² to start; PROPOSED).
- [ ] The tilt is set at 35, 50, 65 and 75° and read under load with the inclinometer (± 0.1°).
- [ ] Guide stiffness is measured with the refill off the paper (`templates/r9_guide_stiffness.csv`, `rig.calib.fit_guide_stiffness`): 17.9–33.3 N/m (AC-BB02-04).
- [ ] Axial cell calibration uses dead weights on the cartridge at the test angle, loading then unloading (`templates/r9_axial_cell_calibration.csv`, `rig.calib.fit_bridge`). The hysteresis is written down.
- [ ] Plate calibration at the test angle:
  - [ ] Weights at nine positions and horizontal pulls over the pulley (`templates/r9_plate_calibration.csv`).
  - [ ] Fit with `rig.calib.fit_plate`.
  - [ ] Residual ≤ 0.2 % FS per axis (AC-BB02-03).
- [ ] Tap test of the plate stack with each underlay: first mode ≥ 100 Hz (AC-BB02-01; DEC-058). Below 100 Hz, stop and stiffen the stack.
- [ ] Check standard: a 50 g weight on the platen reads within the control limits set at qualification. The value is written in `record.yaml → check_standards`.

## D. The first measurement: EXP-T02, then EXP-T01 (G1)

- [ ] First line: fixed-force line at F_c 0.15 N by dead weight, 30 mm/s, 50°, copy paper, S 635 refill:
  - [ ] Ink is visible along the whole line.
  - [ ] The axial closure F_c − R·a is live on screen: median ≤ max(3 mN, 3 % F_c) (AC-T01-01).
- [ ] If closure fails, stop. Recalibrate at the angle and check that the cable is not loading the axial path.
- [ ] Each sheet carries fiducials and a blind code; the sheet code and the blind code go into `templates/ink_scan_register.csv`. The key is stored outside the analysis tree (`bench_protocols.md` §0.6).
- [ ] Sheets are scanned within 1 h at 4800 dpi, lossless 16-bit TIFF, after a USAF-1951 check of the scanner.
- [ ] `rig.ink.analyse_line` runs on the first scan. The gap fraction and F_c,min estimate are plausible. The gap fraction must not be 0 or 1 on every window: if it is, the threshold or the registration is wrong.
- [ ] First EXP-T01 stroke on the nominal pair at 50°, β 0°, 30 mm/s:
  - [ ] `rig.contact.analyse_stroke` gives μ_drag inside 0.09–0.40 (AC-T01-04) or a noted surprise.
  - [ ] The forces are resampled from `t_adc_s` onto the encoder or stroke clock first (plan §10, gap 1).
- [ ] Every condition is cut by a MARK event, and `rig.convert.split_by_markers` returns one record per condition.
- [ ] The session ends with the check standard repeated and the environment logged again.

## E. After the session (every build)

- [ ] `MANIFEST.sha256` covers every raw file before any analysis. Raw files are set read-only.
- [ ] Derived files are written to the record's `analysis/` folder by scripts only.
- [ ] Records are exported with `rig.convert.to_bench` (s2r-bench-1). A reload with `s2r.io.load` gives identical arrays, as `tools/pipeline_check.py` step A does.
- [ ] `analysis/verdict.yaml` holds one entry per criterion (`templates/verdict_template.yaml`), filled from `rig.uncertainty.decide`: value, U (k = 2), TUR, simple or guarded rule, verdict and prediction.
- [ ] The notebook page is signed. Deviations are listed with their impact.

## F. First coupon session (G2): extra checks

- [ ] **Beryllium copper** (DEC-063; DEC-097 proposed; SDS AMF-319):
  - [ ] Wire arrives aged; no heat treatment at the bench.
  - [ ] Cutting is by shears or flush cutters only.
  - [ ] No abrasive, grinding, sanding, pickling or acid cleaning.
  - [ ] Soldering is done under the fume absorber, with gloves and eye protection.
  - [ ] Offcuts and wipes go into the labelled bag.
  - [ ] Hands are washed; no food or drink at the bench.
- [ ] Every wire coupon has its first transverse mode measured before cycling. The drive is ≤ 0.2 × that mode (`templates/wire_mode_check.csv`, AC-BB04-05, DEC-098 proposed).
- [ ] Every wire's R20 is measured by 4-wire before cycling (`templates/k21_wire_log.csv`), and the exit from the clamp is photographed at 50×.
- [ ] **Magnets:**
  - [ ] Dimensions are measured and Br is checked (pull or Gaussmeter) before the model re-run.
  - [ ] Assembly uses a non-magnetic jig, one magnet at a time, with eye protection.
  - [ ] The coupon's heated runs stay inside the supplier's stated maximum temperature.
- [ ] **Force-constant coupon:** the coil is centred by the symmetry of the zero-current force (within 0.05 mm, DEC-044's tolerance). Currents are applied in reversal order, with ≥ 30 s cooling above 0.3 I_max.
- [ ] **Ball guide:**
  - [ ] Races and balls are cleaned with IPA.
  - [ ] The preload is read on the K3D40 before every sweep.
  - [ ] Drag is measured on the 10 g cell, never on the plate (TUR < 1, `bench_calcs.json`).
- [ ] **Anchor:** foil thickness is measured at five points on each sheet before the artwork's beam width is set (`bench_calcs.json → anchor_foil`).

## G. First five-bar power-up (EXP-BB06 before anything else)

- [ ] Emergency stop removes motor power. Test it with the motors driven.
- [ ] The hardware current limit is set to the rated current. The software cap of 0.4 N is active.
- [ ] With the holder blocked on the K3D40 ±10 N, the steady force is ≤ 0.4 N at nine poses and the coupling releases between 0.5 and 0.8 N (AC-BB06-04). Nothing else runs until this passes.
- [ ] Guards are over the capstans and the link sweep. No hand is inside the workspace while the motors are enabled (DEC-099 proposed).
- [ ] The controller logs the DAQ sync pulse, and its clock maps onto DAQ-1 within 50 µs.

## H. First page-sensor run (EXP-T04)

- [ ] The camera truth is qualified on a static dot grid: centroid noise and distortion residual are written down before any sensor verdict (`docs/measurement_rig.md` §11 item 5).
- [ ] PAGE frames are mapped onto the SAMPLE clock before `rig.pagesense.qualify` (plan §10, gap 2), and the sensor's report rate is checked (≥ 1 kHz, AC-T04-01).
- [ ] Every outage (lift, occlusion, glossy strip) is logged in `templates/r10_reanchor_trials.csv`. A position output before re-anchoring is a silent recovery (AC-BB08-01).
