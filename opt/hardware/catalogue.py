"""Catalogue of buyable and buildable parts for the pencil nib stage, with sources.

Every entry records: category, part, supplier, status, key specification, source (URL, document id or revision,
what was actually read and when), ledger id (docs/evidence.csv, or a new row proposed in
results/opt/hardware_evidence_rows.csv), evidence label, and the role or verdict in this study.

Status vocabulary:
  catalogue  - orderable standard part;
  custom     - custom geometry from a supplier's standard process (the supplier states custom designs are made);
  build      - built in-house from catalogue materials and parts;
  reject     - evaluated and not used (reason given).
Evidence labels: MFR (manufacturer statement, ledger id), LITERATURE (ledger id), ASSUMPTION, CALC.
Prices are listed only where a price was seen on the supplier page, with the date seen.
Nothing here has been measured on hardware.
"""
from __future__ import annotations

RETRIEVED = "2026-09-28"

# ----------------------------------------------------------------------------------------------------------
# Piezo ceramics of the custom plates: reference catalogue parts used for scaling (AMF-11 / AMF-53)
# ----------------------------------------------------------------------------------------------------------
# PI PICMA Bender PL112-PL140 datasheet dated 31.07.2020 (read in full, 2026-09-28): 0-60 V (+/-30 V) differential,
# displacement / blocking force / capacitance / resonance +/-20 %, remaining (free) length LF, height tolerance
# +/-0.1 mm, piezo ceramic PIC252 (PL112, PL128; -20..150 degC) or PIC251 (PL122, PL127, PL140; -20..85 degC);
# "Custom designs or different specifications on request".
CERAMICS = {
    "PIC252": dict(ref="PL128.10", delta_f=450e-6, F_b=0.55, w=6.15e-3, t=0.67e-3, L_free=28e-3, L_total=36e-3,
                   C_half=1.2e-6, fr=360.0, V=60.0, T_range_C=(-20, 150), ledger="AMF-11; AMF-53",
                   label="MFR (AMF-11, AMF-53)"),
    "PIC251": dict(ref="PL127.10", delta_f=450e-6, F_b=1.1, w=9.60e-3, t=0.67e-3, L_free=27e-3, L_total=31e-3,
                   C_half=3.4e-6, fr=420.0, V=60.0, T_range_C=(-20, 85), ledger="AMF-11; AMF-53",
                   label="MFR (AMF-11, AMF-53)"),
}
RHO_PZT = 7800.0          # kg/m^3, ASSUMPTION (as sim/pencil/design.py)
PICMA_TOL = 0.20          # AMF-11
V_PART_MAX = 60.0         # AMF-11: 0-60 V; also the practical SELV-class ceiling in a hand-held product (ASSUMPTION)

# Flexure (decoupling-leaf) materials.  allow_alt: allowable alternating bending stress used as the design limit.
LEAF_MATERIALS = {
    "C17200": dict(E=131e9, G=50.4e9, rho=8250.0, allow_alt=150e6, magnetic=False, ledger="AMF-18, AMF-19",
                   label="MFR (AMF-18) / review (AMF-19: fatigue 310 MPa at 1e8, TH04); allowable 150 MPa = fatigue/2",
                   process="photo-etch from TH04 or TD04 strip then age (AMF-59: +/-10 % of thickness, >= +/-25 um)"),
    "Ti6Al4V": dict(E=110e9, G=42.3e9, rho=4430.0, allow_alt=200e6, magnetic=False, ledger="AMF-20, AMF-21",
                    label="review (AMF-20: fatigue 530-630 MPa, cycle count not stated; screening grade); allowable "
                          "200 MPa is an ASSUMPTION (fatigue/2.65) until coupon tests",
                    process="photo-etch (VACCO lists titanium grades, AMF-59) or laser-cut foil; foil availability at "
                            "20-60 um ASSUMPTION"),
    "301FH": dict(E=200e9, G=77e9, rho=7800.0, allow_alt=250e6, magnetic=True, ledger="AMF-20",
                  label="review (AMF-20: fatigue 540 MPa); ferromagnetic when cold-worked",
                  process="photo-etch; excluded next to the collar magnet and Hall sensor (field distortion)"),
}

# ----------------------------------------------------------------------------------------------------------
# Drivers.  V_max = highest rail usable with a 60 V bender; P_q = quiescent battery power of the driver set
# (both axes); eta_boost / eta_c: ASSUMPTIONS as sim/pencil/power.py (EXP-Q05).
# ----------------------------------------------------------------------------------------------------------
_DRV_IQ = ((30.0, 5e-3), (55.0, 9e-3), (80.0, 13e-3), (105.0, 24e-3))   # AMF-16 (DRV2700); same table in DRV8662 (AMF-57)
DRIVERS = {
    "drv2700": dict(label="2 x TI DRV2700 (integrated boost + class-B amplifier)", recovery=False, V_max=60.0,
                    iq_table=_DRV_IQ, channels=2, P_q_fixed=0.0, eta_boost=0.75, eta_c=None, C_max_axis=None,
                    status="catalogue", ledger="AMF-16", price=None,
                    note="Iq 5/9/13/24 mA at 30/55/80/105 V boost (MFR AMF-16); prototype driver"),
    "drv8662": dict(label="2 x TI DRV8662 (integrated 105 V boost + differential amplifier)", recovery=False, V_max=60.0,
                    iq_table=_DRV_IQ, channels=2, P_q_fixed=0.0, eta_boost=0.75, eta_c=None, C_max_axis=None,
                    status="catalogue", ledger="AMF-57", price=None,
                    note="IDDQ 5/9/13/24 mA at 30/55/80/105 V (MFR AMF-57, SLOS709C Table 6.5): same quiescent profile "
                         "as DRV2700; load table up to 3 uF at 20 Vpp/300 Hz; no power advantage"),
    "recovery_lt8330": dict(label="LT8330 low-Iq boost (60 V switch) + 2 discrete charge-recovery half-bridges",
                            recovery=True, V_max=55.0, iq_table=None, channels=2, P_q_fixed=6e-6 * 3.7 + 2 * 0.5e-3,
                            eta_boost=0.80, eta_c=0.85, C_max_axis=None, status="build", ledger="AMF-47",
                            price=None, note="Burst-mode Iq 6 uA (MFR AMF-47, mirror); rail 55 V keeps 5 V below the "
                                             "switch rating; 0.5 mW per half-bridge ASSUMPTION"),
    "recovery_lt8365": dict(label="LT8365 low-Iq boost (150 V switch) + 2 discrete charge-recovery half-bridges",
                            recovery=True, V_max=60.0, iq_table=None, channels=2, P_q_fixed=9e-6 * 3.7 + 2 * 0.5e-3,
                            eta_boost=0.80, eta_c=0.85, C_max_axis=None, status="build", ledger="AMF-58",
                            price=None, note="Burst-mode Iq 9 uA, 1.5 A/150 V switch, 2.8-60 V in, 100-500 kHz, "
                                             "MSOP-16 (MFR AMF-58, radiolocman mirror; analog.com HTTP 503): "
                                             "allows the full 60 V bender range with switch margin"),
    "capdrive_bos1931": dict(label="2 x Boreas BOS1931-class CapDrive (integrated boost, energy recovery)",
                             recovery=True, V_max=60.0, iq_table=None, channels=2, P_q_fixed=2 * 3.7e-3 * 3.6,
                             eta_boost=0.80, eta_c=0.85, C_max_axis=1.0 / (2 * 3.141592653589793 * 12.0 * 5300.0),
                             status="catalogue (outside rated load; vendor qualification)", ledger="AMF-46",
                             price=None, note="rated load <= 820 nF at 100 Vpp/130 Hz; limit stated as 5.3 kOhm at "
                                              "190 Vpp (AMF-46, lead-verified) -> C <= 2.5 uF at 12 Hz; 3.7 mA "
                                              "average at DC output (95 V, 100 nF) taken as the quiescent cost"),
}


def drv_iq(table, v):
    """Linear interpolation of a (V, I) table (as sim/pencil/power.drv2700_iq)."""
    vs = [a for a, _ in table]
    i_s = [b for _, b in table]
    if v <= vs[0]:
        return i_s[0]
    for (v0, i0), (v1, i1) in zip(table[:-1], table[1:]):
        if v <= v1:
            return i0 + (i1 - i0) * (v - v0) / (v1 - v0)
    return i_s[-1]


# ----------------------------------------------------------------------------------------------------------
# Stage-position sensors.  sigma_B: rms field noise per sample at the servo rate (>= 10 kSPS, two axes);
# power at 3.3 V.  The electronics budget (config/pencil.yaml electronics.p_active) already holds 3 mW for it.
# ----------------------------------------------------------------------------------------------------------
HALL = {
    "tmag5170_a2": dict(label="TI TMAG5170-A2 3-D Hall, SPI 10 MHz, +/-150 mT range, CONV_AVG=000", sigma_B=160e-6,
                        rate_2axes=13.3e3, P_W=3.4e-3 * 3.3, status="catalogue", ledger="OPT-44",
                        note="XY noise 160 uT typ (236 max) at 25 degC, Z 72 uT; 20/13.3/10 kSPS for 1/2/3 axes; "
                             "active 3.4 mA (MFR OPT-44, SBASAF4); the A1 (+/-100 mT) variant saturates at the 169 mT "
                             "peak field of the P0.1.2 magnet (SIM magpylib, results/pencil/mechanisms.json)"),
    "drv5055a4_x2": dict(label="2 x TI DRV5055A4 ratiometric linear Hall (analog, 20 kHz, +/-169 mT) + MCU ADC",
                         sigma_B=2.36e-5, rate_2axes=None, P_W=2 * 2.0e-3 * 3.3, status="catalogue", ledger="OPT-46",
                         note="215 nT/sqrt(Hz) at 3.3 V (MFR OPT-46, SBAS640C); with a 3 kHz RC anti-alias filter "
                              "(noise bandwidth 4.7 kHz) 14.8 uT rms, plus 12-bit ADC quantisation at 12.5 mV/mT "
                              "(18.5 uT) -> 23.6 uT rms (CALC); 2 mA each at 3.3 V; SOT-23 2.92 x 2.37 mm: one sensor "
                              "and magnet per axis (packaging ASSUMPTION)"),
    "tmag5273": dict(label="TI TMAG5273 3-D Hall, I2C 1 MHz", sigma_B=125e-6, rate_2axes=None, P_W=2.3e-3 * 3.3,
                     status="reject", ledger="OPT-45",
                     note="XY 125 uT at CONV_AVG=000 (MFR OPT-45, SLYS045C); the 1 MHz I2C bus cannot carry two axes "
                          "at the 10 kSPS servo rate (CALC: about 90 us per read) -> not usable for the servo"),
}
HALL_SENS_T_PER_M = 94.78       # dBy/dy at the centre, T/m (SIM magpylib, results/pencil/mechanisms.json; weaker axis)
# magpylib (P0.1.2 magnet 0.6 x 1 x 1 mm, Br 1.32 T ASSUMPTION; opt/hardware/run_study.hall_field_check) with the
# sensor moved out by gap_extra: peak field over the travel and the weaker-axis sensitivity at the centre (SIM)
HALL_GAP_TABLE = {0.0: dict(B_max_mT=169.4, S_T_per_m=94.78), 0.1e-3: dict(B_max_mT=131.4, S_T_per_m=71.93),
                  0.2e-3: dict(B_max_mT=102.8, S_T_per_m=55.13), 0.3e-3: dict(B_max_mT=81.3, S_T_per_m=42.72)}

# ----------------------------------------------------------------------------------------------------------
# Cells.  Capacity model of a custom cylinder (ASSUMPTION): 90 mAh at 6.5 x 40 mm (config/pencil.yaml) scaled
# linearly in length with the dead length of the Panasonic CG series (CG-420A 23 mAh at 20 mm, CG-425A 32 mAh at
# 25 mm -> 7.2 mm; MFR AMF-43).
# ----------------------------------------------------------------------------------------------------------
CELL_REF = dict(C_mAh=90.0, L=40e-3, L_dead=7.2e-3, d=6.5e-3, rho=2.6e3, V=3.7, usable=0.8)

# ----------------------------------------------------------------------------------------------------------
# The catalogue table (for the report, the BOM and results/opt/hardware.json)
# ----------------------------------------------------------------------------------------------------------
PARTS = [
    # ---------------- piezo benders and plates
    dict(id="PICMA-PL128.10", category="piezo bender", part="PI PICMA PL128.10", supplier="Physik Instrumente (PI)",
         status="catalogue", key_spec="36 x 6.15 x 0.67 mm, LF 28 mm, +/-450 um, +/-0.55 N, 2 x 1.2 uF, 360 Hz, 0-60 V, PIC252",
         source="PL112-PL140 datasheet 31.07.2020 (full table read 2026-09-28)", ledger="AMF-11; AMF-53", label="MFR",
         role="reference for the PIC252 custom plates; bench part for the 1-axis rig (EXP-Q06); one axis only in the bore"),
    dict(id="PICMA-PL127.10", category="piezo bender", part="PI PICMA PL127.10", supplier="PI", status="catalogue",
         key_spec="31 x 9.60 x 0.67 mm, LF 27 mm, +/-450 um, +/-1.1 N, 2 x 3.4 uF, 420 Hz, PIC251", ledger="AMF-11; AMF-53",
         source="PL112-PL140 datasheet 31.07.2020", label="MFR",
         role="reference for PIC251 custom plates (24 % more force and 7.5 % more stroke than PIC252 at equal geometry, "
              "2.1 x the capacitance, CALC); too wide for the bore as-is"),
    dict(id="PICMA-custom", category="piezo plate (custom)", part="PICMA-class multilayer bender, custom width/length/thickness",
         supplier="PI (custom designs on request)", status="custom",
         key_spec="scaled from PL128.10 (PIC252) or PL127.10 (PIC251): delta ~ LF^2/t, F ~ w t^2/LF, C ~ w L t (CALC, "
                  "checked against the PICMA and CTS families within +/-20 %, AMF-63)",
         source="AMF-53 ('Custom designs or different specifications on request'); lengths to 45 mm and thickness "
                "0.55-0.67 mm in the catalogue; thicker plates demonstrated by CTS to 1.8 mm (AMF-54)", ledger="AMF-53; AMF-63",
         label="MFR + CALC", role="the P0.2 stage plates (quote needed: EXP-Q04 qualifies stroke, force, strength)"),
    dict(id="CTS-NAC2224", category="piezo bender", part="CTS (Noliac) NAC2224 plate bender", supplier="CTS Corporation",
         status="catalogue", key_spec="32 x 7.8 x 0.7 mm, inactive clamp 3.5 mm, 200 V, +/-530 um, 0.92 N, 2 x 170 nF, 1.7 N/mm, 340 Hz, NCE51F",
         source="CTS Plate Benders datasheet RevC_0524 (full table read 2026-09-28)", ledger="AMF-54", label="MFR",
         role="reject for the product (200 V drive, 7.8 mm wide); evidence that multilayer benders are made 0.7-1.8 mm "
              "thick with a 3.5 mm inactive clamp and custom designs"),
    dict(id="CTS-NAC2225", category="piezo bender", part="CTS (Noliac) NAC2225", supplier="CTS", status="catalogue",
         key_spec="32 x 7.8 x 1.3 mm, 200 V, +/-365 um, 3.4 N, 2 x 350 nF, 9.3 N/mm, 620 Hz", source="RevC_0524",
         ledger="AMF-54", label="MFR", role="thickness scaling check (force ~ t^2: 3.7x vs 3.45x predicted)"),
    dict(id="PiezoDrive-BA3502", category="piezo bender", part="PiezoDrive BA3502 bimorph", supplier="PiezoDrive",
         status="catalogue", key_spec="35 x 2.5 x 0.8 mm, LF 28 mm, 0-150 V (+/-90 V AC), 0.7 mm range, 0.08 N, 20 nF, "
                                      "220 N/m, 230 Hz, 0.3 g", price="USD 11.80 each (piezodrive.com, seen 2026-09-28)",
         source="piezodrive.com bender table and BA3502 product page (read 2026-09-28)", ledger="AMF-55", label="MFR",
         role="buy now: same footprint as the Q plates (2.5 mm wide, 28 mm free) for a fit / assembly / servo mock-up "
              "of the Q stage; 150 V and about 1/4 of the custom plate's work, so not the product"),
    dict(id="Thorlabs-PB4NB2W", category="piezo bender", part="Thorlabs PB4NB2W", supplier="Thorlabs", status="catalogue",
         key_spec="150 V, +/-450 um, 28 mm active free length, co-fired multilayer (force/capacitance not retrieved)",
         source="product-page title and search summary; spec tables JavaScript-rendered", ledger="AMF-12", label="MFR (partial)",
         role="reject: 150 V drive, width not suited; no force data"),
    dict(id="piezo.com-Q220", category="piezo bender", part="PIEZO.COM Q220-A4BR-1305YB", supplier="Mide / piezo.com",
         status="catalogue", key_spec="31.8 x 12.7 x 0.51 mm, +/-90 V, +/-0.32 mm, 0.24 N", ledger="AMF-13", label="MFR",
         source="product page (AMF-13)", role="reject: 12.7 mm wide"),
    dict(id="Steminc-SMBA3531T06", category="piezo bender", part="Steminc SMBA3531T06 bimorph", supplier="STEMINC",
         status="catalogue", key_spec="35 x 31 x 0.57 mm, 200 V, 8 nF", price="USD 26.14 per 2 (steminc.com, seen 2026-09-28; out of stock)",
         source="product page (read 2026-09-28)", ledger="AMF-62", label="MFR", role="reject: 31 mm wide, 200 V; no narrow multilayer bender found at Steminc"),
    dict(id="APC", category="piezo bender", part="APC International bimorphs", supplier="APC International", status="not verified",
         key_spec="no bender specification could be retrieved (search returned no part data)", source="search 2026-09-28",
         ledger="", label="-", role="not used"),
    dict(id="PI-PT230.14", category="piezo tube", part="PI PT230.14 quartered scanner tube", supplier="PI Ceramic",
         status="catalogue", key_spec="30 x 6.35 x 5.35 mm, +/-250 V, +/-16 um XY, 4 x 4.5 nF, PIC255; custom L <= 70 mm, "
                                      "OD 2-80 mm, wall >= 0.30 mm", source="PT120-PT140 datasheet R1 13/08/23 (read 2026-09-28)",
         ledger="AMF-56", label="MFR",
         role="reject: best custom tube in the bore at <= 60 V gives about 10 um at the tip (CALC, 30x short)"),
    # ---------------- drivers
    dict(id="DRV2700", category="piezo driver", part="TI DRV2700", supplier="Texas Instruments", status="catalogue",
         key_spec="105 V boost, class-B; Iq 5/9/13/24 mA at 30/55/80/105 V; 4 x 4 mm VQFN", source="SLOS861C",
         ledger="AMF-16", label="MFR", role="prototype driver (EVM); 72 mW quiescent for two"),
    dict(id="DRV8662", category="piezo driver", part="TI DRV8662", supplier="Texas Instruments", status="catalogue",
         key_spec="105 V boost, differential; IDDQ 5/9/13/24 mA at 30/55/80/105 V; CL to 3 uF at 20 Vpp/300 Hz; 4 x 4 mm",
         source="SLOS709C (Dec 2022), read 2026-09-28", ledger="AMF-57", label="MFR",
         role="alternative prototype driver; same quiescent power as DRV2700"),
    dict(id="BOS1931", category="piezo driver", part="Boreas BOS1921/BOS1931 CapDrive", supplier="Boreas Technologies",
         status="catalogue (vendor qualification)", key_spec="energy recovery; 3.7 mA at DC output; <= 820 nF rated",
         source="BT015DDS01.01 Issue 6", ledger="AMF-46", label="MFR",
         role="integrated recovery option only if the plate capacitance stays <= 2.5 uF per axis"),
    dict(id="LT8330", category="boost converter", part="ADI LT8330", supplier="Analog Devices", status="catalogue",
         key_spec="60 V/1 A switch, Iq 6 uA", source="mirror datasheet", ledger="AMF-47", label="MFR",
         role="rail for a 55 V recovery driver"),
    dict(id="LT8365", category="boost converter", part="ADI LT8365", supplier="Analog Devices", status="catalogue",
         key_spec="150 V/1.5 A switch, 2.8-60 V in, Iq 9 uA (Burst Mode), 100-500 kHz, MSOP-16", source="radiolocman mirror "
         "(analog.com HTTP 503), read 2026-09-28", ledger="AMF-58", label="MFR",
         role="rail for a full 60 V recovery driver (+8.3 % stroke and force over 55 V)"),
    dict(id="recovery-stage", category="piezo driver", part="discrete charge-recovery half-bridge per axis",
         supplier="in-house (catalogue MOSFETs, inductor, MCU PWM)", status="build",
         key_spec="bidirectional buck/boost between the rail capacitor and the plate; eta 0.85 per transfer ASSUMPTION",
         source="topology of AMF-46; efficiency EXP-Q05", ledger="AMF-46 (topology)", label="ASSUMPTION",
         role="product driver"),
    # ---------------- sensors
    dict(id="TMAG5170", category="position sensor", part="TI TMAG5170-A2", supplier="Texas Instruments", status="catalogue",
         key_spec="3-D Hall, SPI, 13.3 kSPS (2 axes), 160 uT rms XY", source="SBASAF4 (Sept 2021)", ledger="OPT-44",
         label="MFR", role="baseline sensor: about 3 um rms at the nib on the weaker axis with the sensor 0.1 mm further out (72 T/m, needed to stay inside the +/-150 mT range) and lever 1.34 (CALC)"),
    dict(id="DRV5055A4", category="position sensor", part="TI DRV5055A4 x 2", supplier="Texas Instruments", status="catalogue",
         key_spec="analog linear Hall, 20 kHz, 215 nT/sqrt(Hz) at 3.3 V, +/-169 mT", source="SBAS640C (rev. June 2026)",
         ledger="OPT-46", label="MFR", role="low-noise option: about 0.44 um rms at the nib at 72 T/m and lever 1.34 (CALC) -> lower servo power"),
    dict(id="TMAG5273", category="position sensor", part="TI TMAG5273", supplier="Texas Instruments", status="reject",
         key_spec="3-D Hall, I2C 1 MHz, 125 uT rms", source="SLYS045C (rev. Apr 2026)", ledger="OPT-45", label="MFR",
         role="reject: I2C rate below the 10 kSPS servo"),
    # ---------------- cells
    dict(id="CG-425A", category="cell", part="Panasonic CG-425A", supplier="Panasonic", status="catalogue",
         key_spec="4.7 x 25 mm, 32 mAh, 1.0 g", source="product page", ledger="AMF-43", label="MFR", role="fallback cell (3 in series length)"),
    dict(id="custom-cell", category="cell", part="custom 6.5 mm Li-ion cylinder", supplier="cell maker (custom)", status="custom",
         key_spec="90 mAh at 40 mm (ASSUMPTION), +2.7 mAh per mm (scaled with the CG-series dead length, AMF-43)",
         source="config/pencil.yaml battery.*", ledger="AMF-42; AMF-43", label="ASSUMPTION", role="baseline cell (EXP-Q03)"),
    # ---------------- flexures
    dict(id="C17200-leaf", category="flexure", part="C17200 TH04 photo-etched leaf", supplier="photo-etch service",
         status="build", key_spec="E 131 GPa, fatigue 310 MPa at 1e8; etch tolerance +/-10 % of thickness, >= +/-25 um",
         source="Materion DS-AS-24; CDA; VACCO design guide; PEI BeCu page", ledger="AMF-18; AMF-19; AMF-59", label="MFR",
         role="decoupling leaves (Be dust controls)"),
    dict(id="Ti64-leaf", category="flexure", part="Ti-6Al-4V etched or laser-cut leaf", supplier="photo-etch / laser service",
         status="build", key_spec="E 110 GPa, fatigue 530-630 MPa (screening)", source="MakeItFrom; AZoM; VACCO",
         ledger="AMF-20; AMF-21; AMF-59", label="review", role="alternative leaf, higher stress allowance, non-magnetic"),
    dict(id="301FH-leaf", category="flexure", part="301 full-hard / 17-7PH leaf", supplier="photo-etch service", status="reject",
         key_spec="E 200 GPa, fatigue 540 MPa", source="MakeItFrom", ledger="AMF-20", label="review",
         role="reject next to the collar magnet and Hall sensor (ferromagnetic)"),
    # ---------------- refills
    dict(id="D1-refill", category="refill", part="ISO 12757-2 D1 gel / fineliner refills", supplier="various", status="catalogue",
         key_spec="67 x 2.35 mm; no published line-quality-vs-force data found", source="search 2026-09-28",
         ledger="AMF-60", label="-",
         role="F_c must be measured (EXP-Q02); ISO 27668-1:2017 write-test machines span 0.1-5 N and 60-90 deg (AMF-60), "
              "so a standard write tester can run EXP-Q02"),
]
