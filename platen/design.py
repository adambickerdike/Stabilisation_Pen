"""The proposed moving-paper platen (PROPOSED DESIGN), its budgets (CALCULATION) and its sources.

Every entry is (value, unit, label, source).  Labels: PROPOSED DESIGN (a choice made here), CALCULATION (derived
here from the listed inputs), MANUFACTURER (a maker's data sheet or product page; URL given), LITERATURE (a paper,
standard or the project's evidence ledger id), ASSUMPTION (a value chosen here without a source).  Nothing was built
or measured.

Architecture (PROPOSED DESIGN): an A5 paper plate on a two-layer XY stage under a fixed palm-rest bridge.
  fine    voice-coil XY stage, +-5 mm, 40 Hz position servo on linear encoders: tremor cancellation and the fast part
          of accepted writing; carries the paper plate, its hold-down and a 3 mm Z-drop (pen lift)
  coarse  belt-driven H-bot, +-40 mm x +-20 mm, about 8 Hz, closed-loop steppers: slow page repositioning, so that a
          whole accepted word passes under a pen the user keeps still
  sensing an absolute desk-frame tip sensor (a global-shutter camera looking at a marker at the pen tip, or an EMR
          digitiser under the non-metallic plate), the platen's own encoders, load cells under the plate for contact,
          and (for free writing) the pen's IMU (clip-on or a light stylus)
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

# ------------------------------------------------------------------ sources (cited once; the ledger ids are the project's)
SRC = {
    "moticont_lvcm032": "Moticont LVCM-032-025-02 data sheet, https://www.moticont.com/pdf/lvcm-032-025-02.pdf and "
                        "product page https://www.moticont.com/lvcm-032-025-02.htm (retrieved 2026-09-30); ledger AMF-232",
    "stepper_17hs19": "NEMA 17 hybrid stepper 17HS19-2004S1 (ledger AMF-92: 0.59 N m holding, 2.0 A, 1.4 ohm, 3.0 mH, "
                      "rotor 82 g cm2); closed-loop variant with a 1000-line encoder, e.g. StepperOnline 17E1K series "
                      "(https://www.omc-stepperonline.com/nema-17-closed-loop-stepper-motor, retrieved via a search "
                      "listing 2026-09-30)",
    "tmc2209": "ADI/Trinamic TMC2209 stepper driver, StealthChop2 'no-noise' chopper (ledger AMF-93)",
    "rls_lm13": "RLS LM13 magnetic linear encoder, 2 mm pole, down to about 0.244 um resolution (ledger OPT-89)",
    "opa548": "TI OPA548 linear power amplifier, 3 A continuous, 5 A peak (ledger AMF-233)",
    "klipper": "Klipper resonance compensation guide: axis ringing below about 20-25 Hz calls for a stiffer frame or a "
               "lighter moving mass; example measurement 49.4 Hz; https://www.klipper3d.org/Resonance_Compensation.html "
               "(retrieved 2026-09-30)",
    "ov9281": "InnoMaker global-shutter camera modules for Raspberry Pi: OV9281 1280x800 at 120 fps (144 fps with the "
              "maker's driver), 640x400 at 253 fps; https://www.inno-maker.com/gs-camera/ (retrieved 2026-09-30)",
    "optitrack": "OptiTrack Prime 13 motion-capture camera: 240 fps, 4.2 ms latency (manufacturer), "
                 "https://optitrack.com/cameras/prime-13/specs.html (retrieved via a search listing 2026-09-30)",
    "wacom_oem": "Wacom EMR OEM digitiser boards (ledger AMF-98): resolution 0.01 mm, accuracy +-0.4 mm, reading height "
                 "5-14 mm, 133 points/s; Cintiq 12WX (ledger CON-84): +-0.5 mm, 133 points/s; Intuos Pro Paper "
                 "Edition with ink pens on A5/A4 paper (ledger OPT-86); tablet digitisers about 200 Hz (ledger OPT-03)",
    "imu": "TDK ICM-42688-P accelerometer noise 70 ug/sqrt(Hz) (ledger OPT-39); ST LSM6DSV16X 60 ug/sqrt(Hz) (OPT-37); "
           "study E's IMU budget: anti-aliasing 1.04 ms + FIFO/SPI 0.35 ms + pair averaging 0.13 ms = 1.52 ms "
           "(docs/readable_target.md section 6)",
    "digipen": "STABILO DigiPen: Bluetooth live streaming at 200 Hz (ledger OPT-15)",
    "ble": "Bluetooth LE: minimum connection interval 7.5 ms, reduced to 375 us by Core 6.2's Shorter Connection "
           "Intervals (https://www.bluetooth.com/bluetooth-core-6-2-feature-overview/, retrieved 2026-09-30; "
           "proposed row AMF-287)",
    "cricut": "Cricut LightGrip machine mat: low-tack adhesive carrier that holds printer paper in a cutting machine; "
              "https://cricut.com/en-us/tools-accessories/machine-tools/machine-mats/lightgrip-machine-mat-12-x-12/2001976.html "
              "(retrieved 2026-09-30)",
    "electroadhesion": "Electroadhesion release pressures 1-100 kPa (conductive objects at 400 V; dielectric objects 1-100 x "
                       "the pre-contact adhesion; ledger AMF-114)",
    "delta_blower": "Delta Electronics BFB1012M-A 97 mm DC blower: 12 V, 0.55 A, 6.6 W, 3200 rpm, 0.777 m3/min; "
                    "https://www.delta-fan.com/products/BFB1012M-A.html (retrieved 2026-09-30)",
    "iso13854": "ISO 13854:2017 minimum gaps to avoid crushing: finger 25 mm, hand 100 mm (as summarised at "
                "https://www.zt-grassberger.at/en/r/MD/Moving_Parts.html, retrieved 2026-09-30; the same page gives "
                "75 N, 4 J and 25 N/cm2 as values below which an actuator is not a crushing hazard)",
    "iso15066": "ISO/TS 15066 body model: hands and fingers, maximum permissible force 140 N, effective spring constant "
                "75 N/mm, effective mass 0.6 kg (Table 1 of Ghanbarzadeh and Najafi, arXiv:2311.13814, 2023)",
    "iec60601_touch": "IEC 60601-1 touch-temperature limits (ledger AMF-34); IEC 62368-1 precursor: 43 C continuously "
                      "held (ledger AMF-35)",
    "writing_force": "Writing (axial) force of healthy adults: mean of subject means 1.01 N, 0.56-2.08 N (ledger CON-01)",
    "friction": "Kinetic friction of a pen on paper 0.10-0.40 (ledger CON-14); HW1 uses 0.15 (ASSUMPTION in "
                "handwriting/params.py)",
    "pen_tilt": "Pen altitude: mean 62.4 deg, SD 7.5 deg (ledger CON-12); HW1 uses 50 deg",
    "signature": "Adult signatures: 3.2 +- 0.3 s, path 231.7 mm, height 19.8 mm, 87.7 mm/s (ledger CON-08)",
    "axidraw": "AxiDraw V3 pen plotter: usable travel 300 x 218 mm, 38 cm/s, writes 'with your favorite pens', "
               "'signature machine' use; https://shop.evilmadscientist.com/productsmenu/846 ; USD 475 "
               "(https://www.adafruit.com/product/3509, listing marked discontinued; retrieved 2026-09-30)",
    "prusa": "Prusa CORE One+ CoreXY printer: USD 925 kit, USD 1,202.78 assembled (ledger AMF-231)",
    "verily_patent": "Tremor-filtered handwriting redrawn by an actuated pen carriage (Verily patent, ledger PAT-04)",
    "plotter_lift": "Plotter pen lift by solenoid, 0.5-0.64 mm axial (CalComp patent, ledger PAT-41)",
    "fivebar": "The grounded five-bar of the independent engineering pass (docs/mechanics_improvement_audit.md; "
               "results/improvement/mechanics/grounded_batch.json and grounded_derivative_check.json)",
    "study_f": "Study F (docs/readable_target.md section 8; results/readable/readable.json)",
}


def item(value, unit: str, label: str, source: str = "") -> Dict:
    return {"value": value, "unit": unit, "label": label, "source": source}


# ------------------------------------------------------------------ the concept (PROPOSED DESIGN)
PD = "PROPOSED DESIGN"
CALC = "CALCULATION"
MFR = "MANUFACTURER"
LIT = "LITERATURE"
ASM = "ASSUMPTION"

PAPER = {"A5": (210.0, 148.0), "A6": (148.0, 105.0)}      # mm, landscape (ISO 216)

CONCEPT = {
    "writing_area": item("A5 landscape (210 x 148 mm); an A6 variant (148 x 105 mm) for a smaller device", "", PD),
    "plate_mm": item([230.0, 170.0, 6.0], "mm", PD, "A5 sheet + 10 mm margin for the clip bar and edge stops; "
                     "glass-fibre sandwich with a vacuum plenum (non-metallic, so an EMR digitiser can read through it)"),
    "fine": {
        "actuator": item("2 x moving-coil voice-coil motor Moticont LVCM-032-025-02 (one per axis), stacked XY on "
                         "miniature ball guides", "", PD, SRC["moticont_lvcm032"]),
        "stroke_mm": item(12.7, "mm", MFR, SRC["moticont_lvcm032"]),
        "force_continuous_N": item(9.3, "N", MFR, SRC["moticont_lvcm032"]),
        "force_intermittent_N": item(29.3, "N", MFR, SRC["moticont_lvcm032"] + " (10 % duty cycle)"),
        "force_constant_N_per_A": item(3.9, "N/A", MFR, SRC["moticont_lvcm032"]),
        "resistance_ohm": item(2.5, "ohm", MFR, SRC["moticont_lvcm032"]),
        "inductance_mH": item(1.3, "mH", MFR, SRC["moticont_lvcm032"] + " (at 120 Hz)"),
        "coil_mass_g": item(28.0, "g", MFR, SRC["moticont_lvcm032"]),
        "body_mass_g": item(127.0, "g", MFR, SRC["moticont_lvcm032"]),
        "max_continuous_power_W": item(14.0, "W", MFR, SRC["moticont_lvcm032"]),
        "usable_travel_mm": item(5.0, "mm radius", PD, "soft limit at 4.5-5 mm, end-stop bumpers at 6 mm (inside the "
                                 "+-6.35 mm stroke)"),
        "force_cap_N": item(20.0, "N (radial)", PD, "current limit below the intermittent rating"),
        "servo_hz": item(40.0, "Hz", PD, "2nd-order reference follower; the inner PD loop at 250 Hz on the encoders"),
        "encoder": item("magnetic linear encoder, 0.25 um", "", PD, SRC["rls_lm13"]),
        "driver": item("linear current amplifier per axis", "", PD, SRC["opa548"]),
        "moving_mass_kg": item(0.59, "kg (X axis; the Y axis moves 0.29 kg)", CALC, "masses('A5')"),
    },
    "coarse": {
        "actuator": item("H-bot, 2 x NEMA 17 closed-loop steppers, GT2 belts, 20-tooth pulleys, miniature rails", "",
                         PD, SRC["stepper_17hs19"] + "; " + SRC["tmc2209"]),
        "travel_mm": item([80.0, 40.0], "mm (+-40 x +-20)", PD, "a whole accepted word up to about 80 mm long passes "
                          "under a still pen; a line change of 2-3 lines"),
        "servo_hz": item(8.0, "Hz", PD, "well below the belt ringing of desktop belt machines (" + SRC["klipper"] + ")"),
        "force_cap_N": item(20.0, "N", PD, "driver current limit"),
        "speed_cap_mm_s": item(50.0, "mm/s", PD, "accepted writing needs <= 30 mm/s (the reference limit)"),
        "moving_mass_kg": item(1.42, "kg", CALC, "masses('A5')"),
    },
    "hold_down": {
        "choice": item("low vacuum through a perforated plate (primary), with a hinged clip bar and three edge stops "
                       "for registration; a low-tack adhesive carrier sheet as the silent alternative", "", PD,
                       SRC["cricut"]),
        "shear_capacity_N": item(3.0, "N", PD, "3 x the largest shear the paper meets (a hand resting on the paper, "
                                 "about 1 N; the ball drag is 0.15-0.4 N)"),
        "registration": item("two stops on the top edge, one on the left edge; the camera reads two printed or "
                             "pencilled corner marks to register the sheet to about 0.2 mm", "", PD),
        "electroadhesion": item("not chosen: kV electrodes under the user's hand, humidity-dependent hold", "", PD,
                                SRC["electroadhesion"]),
    },
    "palm_rest": item("a fixed bridge across the lower edge of the plate, padded, adjustable 15-35 mm above the paper; "
                      "the hand rests on it and never touches the moving paper; the fingers reach over its front edge",
                      "", PD),
    "sensing": {
        "primary": item("global-shutter camera (250 fps region of interest) on a side arm, tracking a small "
                        "retro-reflective or IR-LED marker ring within 3 mm of the ball; the same camera reads the "
                        "sheet's registration marks", "", PD, SRC["ov9281"]),
        "alternative": item("EMR digitiser under the non-metallic plate, with an EMR ink pen; actuators kept outside "
                            "its active area", "", PD, SRC["wacom_oem"]),
        "contact": item("three load cells under the plate: pen normal force at 1 kHz; contact on above 50 mN", "",
                        PD),
        "pen_imu": item("for free writing: the pen's IMU (clip-on on an ordinary pen, or built into a light stylus), "
                        "wired or 2.4 GHz proprietary radio (BLE adds 7.5-15 ms)", "", PD, SRC["imu"] + "; " +
                        SRC["ble"]),
    },
    "lift": {
        "choice": item("Z-drop of the paper plate by 3 mm (three push-pull solenoids on a flexure, or one voice coil); "
                       "the user keeps the pen down; the load cells confirm the break before any air move", "", PD,
                       SRC["plotter_lift"]),
        "drop_s": item(0.040, "s", ASM, "break of contact after the command; the gravity drop alone takes 25 ms (CALC, "
                       "z_drop())"),
        "rise_s": item(0.040, "s", ASM, "renewed contact after the command"),
        "drop_mm": item(3.0, "mm", PD, "exceeds the fingers' assumed 1-2 mm compliance at 1 N (ASSUMPTION)"),
    },
}


# ------------------------------------------------------------------ calculations
def masses(size: str = "A5") -> Dict:
    """Moving masses (CALCULATION on PROPOSED parts; the part masses are ASSUMPTIONS except the voice coils' (MFR))."""
    w, hgt = PAPER[size]
    plate_area = (w + 20.0) * (hgt + 22.0) * 1e-6                     # m2
    plate = 6.5 * plate_area / (0.230 * 0.170) * 0.150 / 6.5           # 150 g for the A5 plate (ASSUMPTION), by area
    parts_y = {"plate_with_plenum": plate, "z_drop_mechanism": 0.050, "y_guide_carriages": 0.030,
               "y_coil": 0.028, "encoder_head_and_brackets": 0.030, "paper": 0.005}
    m_y = sum(parts_y.values())
    parts_x = {"y_stage": m_y, "y_voice_coil_body": 0.127, "y_rails": 0.050, "x_frame": 0.060, "x_coil": 0.028,
               "x_guide_carriages": 0.030}
    m_x = sum(parts_x.values())
    parts_c = {"fine_stage_moving": m_x, "fine_base_plate_and_x_rails": 0.350, "x_voice_coil_body": 0.127,
               "coarse_carriage_and_belt_clamps": 0.300, "cable_chain_share": 0.050}
    m_c = sum(parts_c.values())
    return {"label": CALC + " (part masses ASSUMPTION except the voice coils, MFR)", "size": size,
            "fine_y_kg": m_y, "fine_x_kg": m_x, "coarse_moving_kg": m_c, "parts_y": parts_y, "parts_x": parts_x,
            "parts_coarse": parts_c}


def coarse_force(m_kg: float, a: float = 2.0, friction_N: float = 1.0) -> Dict:
    """Coarse H-bot: force for the word motion and the steppers' stall capability (CALCULATION)."""
    r_pulley = 20 * 2e-3 / (2 * math.pi)                               # GT2 20-tooth pulley pitch radius
    stall = 0.59 / r_pulley                                             # N per motor (AMF-92 holding torque)
    need = m_kg * a + friction_N
    return {"label": CALC, "pulley_radius_mm": r_pulley * 1e3, "stall_force_per_motor_N": stall,
            "needed_N_at_2_m_s2": need, "cap_N": CONCEPT["coarse"]["force_cap_N"]["value"],
            "margin_to_cap": CONCEPT["coarse"]["force_cap_N"]["value"] / need}


def vca_power(F_rms_N: float, Kf: float = 3.9, R: float = 2.5) -> float:
    """Copper loss of one voice coil at a given RMS force (CALCULATION: (F/Kf)^2 R)."""
    return (F_rms_N / Kf) ** 2 * R


def z_drop(drop_m: float = 3e-3) -> Dict:
    """Free-fall time of the plate over the drop (CALCULATION); the lift actuator must beat or match it."""
    t = math.sqrt(2 * drop_m / 9.81)
    return {"label": CALC, "drop_mm": drop_m * 1e3, "gravity_drop_s": t}


def hold_down(size: str = "A5", shear_N: float = 3.0, mu: float = 0.4) -> Dict:
    """Vacuum needed for a shear capacity (CALCULATION: p = F / (mu A))."""
    w, hgt = PAPER[size]
    A = w * hgt * 1e-6
    p = shear_N / (mu * A)
    return {"label": CALC, "sheet_area_m2": A, "shear_N": shear_N, "mu_paper_plate": mu, "vacuum_Pa": p,
            "note": "a few hundred pascals; a small blower or a diaphragm pump with a reservoir"}


def pinch(m_kg: float, v: float = 0.05, F_cap: float = 20.0) -> Dict:
    """Crushing screen of the coarse stage (CALCULATION against ISO 13854 / ISO/TS 15066 values, LITERATURE)."""
    E = 0.5 * m_kg * v * v
    return {"label": CALC, "kinetic_energy_J": E, "energy_limit_J": 4.0, "force_cap_N": F_cap,
            "iso15066_hand_finger_N": 140.0, "iso13854_finger_gap_mm": 25.0,
            "passes": bool(E < 4.0 and F_cap < 75.0),
            "sources": [SRC["iso13854"], SRC["iso15066"]]}


def paper_drag(N: float = 1.01, mu: Tuple[float, float] = (0.10, 0.40)) -> Dict:
    """The largest force the moving page can put on the pen: kinetic friction (CALCULATION on LITERATURE)."""
    return {"label": CALC, "normal_force_N": N, "mu_range": list(mu), "drag_N": [N * mu[0], N * mu[1]],
            "note": "the platen cannot push the hand harder than this: the page only slides under the ball",
            "sources": [SRC["writing_force"], SRC["friction"]]}


COSTS = [   # (item, qty, unit cost low, high USD, label, note)
    ("voice-coil motors LVCM-032-025-02", 2, 150, 300, ASM, "price not listed by the maker; low-volume estimate"),
    ("linear encoders (magnetic, 0.25 um)", 2, 50, 120, ASM, "RLS LM13 class (OPT-89)"),
    ("miniature ball guides (fine XY)", 4, 15, 40, ASM, ""),
    ("closed-loop NEMA 17 steppers + drivers", 2, 35, 90, ASM, "17HS19 class (AMF-92), TMC2209 (AMF-93)"),
    ("belts, pulleys, rails (coarse)", 1, 40, 90, ASM, ""),
    ("Z-drop solenoids/flexure + 3 load cells + ADC", 1, 30, 90, ASM, ""),
    ("hold-down: blower or pump, plenum, clip bar", 1, 25, 70, ASM, "tack-mat alternative 10-15 USD per sheet carrier"),
    ("camera (global shutter) + IR ring + marker", 1, 50, 150, ASM, "OV9281 class (InnoMaker)"),
    ("compute (single-board computer) + real-time MCU", 1, 70, 140, ASM, ""),
    ("current amplifiers, power stage, 24 V supply", 1, 40, 100, ASM, "OPA548 class (AMF-233)"),
    ("base, frame, palm-rest bridge, covers", 1, 80, 250, ASM, "low-volume machining / moulding"),
    ("pen sensing: clip-on IMU or stylus", 1, 30, 90, ASM, ""),
]


def bom() -> Dict:
    lo = sum(q * a for _, q, a, _, _, _ in COSTS)
    hi = sum(q * b for _, q, _, b, _, _ in COSTS)
    return {"label": ASM + " (prototype quantities; CALCULATION of the sums)", "items": [
        {"item": n, "qty": q, "usd_low": a, "usd_high": b, "label": l, "note": nt} for n, q, a, b, l, nt in COSTS],
        "bom_usd_low": lo, "bom_usd_high": hi,
        "retail_usd": [1500, 3000], "retail_label": ASM + ": 2-3 x a volume BOM of about 500-1,000 USD (assistive "
        "device, low volume, support and regulatory costs); comparators: " + SRC["axidraw"] + "; " + SRC["prusa"]}


POWER = [   # (consumer, W low, W high, label)
    ("fine voice coils (tremor duty, both axes)", 0.2, 2.0, CALC + " from the simulated RMS force (the stage table of "
     "part a; study E's raw commands would need far more)"),
    ("coarse steppers (holding at reduced current / moving)", 1.0, 5.0, ASM),
    ("vision compute + camera", 3.0, 8.0, ASM),
    ("real-time MCU, encoders, load cells", 0.5, 1.5, ASM),
    ("vacuum blower or pump", 1.0, 6.6, ASM + " (a 97 mm blower is 6.6 W at full speed, MFR AMF-285)"),
    ("Z-drop solenoids (duty)", 0.2, 1.5, ASM),
]


def power() -> Dict:
    return {"label": CALC + " on ASSUMPTION ranges", "items": [{"consumer": c, "W_low": a, "W_high": b, "label": l}
                                                            for c, a, b, l in POWER],
            "total_W": [sum(a for _, a, _, _ in POWER), sum(b for _, _, b, _ in POWER)],
            "supply": "24 V, 60 W mains adapter (SELV); an A6 battery variant would need about 50-100 Wh for 4-8 h"}


NOISE = {
    "target": item(40.0, "dB(A) at 0.5 m", ASM, "a quiet office; to be measured (EXP-PL07)"),
    "sources": item("steppers in a silent chopper mode at writing speeds; voice coils move at 4-12 Hz (below "
                    "hearing) but can buzz through the frame; the vacuum blower is the loudest part at full speed "
                    "(a faster model of the same 97 mm blower is listed at 64 dB(A) in a search listing) and must run "
                    "slow, be muffled, or be replaced by a tack mat", "", ASM, SRC["tmc2209"]),
}

SIZES = {
    "A5": {"base_mm": [380, 300], "paper_height_mm": 66, "palm_rest_top_mm": 103, "camera_post_mm": 200,
           "mass_kg": [4.0, 5.5], "label": PD + " (the CAD layout, mechanics/cad/platen.py: plate + coarse travel + "
           "frame margins); mass ASSUMPTION range"},
    "A6": {"base_mm": [320, 260], "paper_height_mm": 62, "palm_rest_top_mm": 99, "camera_post_mm": 200,
           "mass_kg": [3.0, 4.0], "label": CALC + " (the A5 layout's margins around the A6 plate and the same coarse "
           "travel); mass ASSUMPTION range"},
}

SENSING_OPTIONS = [
    {"option": "Ordinary pen + instrumented clip-on IMU",
     "measures": "pen acceleration and rotation (no absolute position)",
     "delay_ms": "1.5 (study E's IMU path: anti-aliasing + FIFO + averaging) + link: 1-2 wired or proprietary radio, "
                 "7.5-15 with BLE",
     "noise": "accelerometer 60-70 µg/√Hz (OPT-37, OPT-39); tremor-band position from the IMU alone about 0.29 mm "
              "with a linear filter on the tremor alone (study F)",
     "pros": "any pen the user likes; cheap", "cons": "no position: cannot write accepted text alone; clip adds "
     "5-8 g off-axis; BLE latency", "label": "MANUFACTURER / LITERATURE (ledger ids) and ASSUMPTION (link)"},
    {"option": "Light stylus with IMU + contact (force) sensing",
     "measures": "acceleration, rotation, refill force (contact) at 1 kHz",
     "delay_ms": "1.5 IMU + <1 contact + link as above", "noise": "as the IMU; contact force about 10 mN (ASSUMPTION)",
     "pros": "known geometry and mass; contact known at the tip", "cons": "not the user's own pen; still no absolute "
     "position", "label": "ASSUMPTION on the IMU data above"},
    {"option": "Tip tracking by an overhead or side camera",
     "measures": "marker position near the tip in the desk frame (absolute, drift-free) and the sheet's marks",
     "delay_ms": "4-8 (exposure + readout + processing; OptiTrack-class 4.2 at 240 fps, MANUFACTURER)",
     "noise": "10-20 um RMS per axis with sub-pixel centroiding at about 0.1 mm per pixel (ASSUMPTION)",
     "pros": "absolute; works with any pen fitted with a marker; also registers the sheet",
     "cons": "occlusion by the fingers from above (a side arm is better); the marker sits above the ball, so pen "
     "rotation reads as motion (kappa, part c)", "label": "MANUFACTURER (frame rates, latency) and ASSUMPTION (noise)"},
    {"option": "Sensing through the platen (EMR digitiser under a non-metallic plate)",
     "measures": "EMR pen coil position, pressure and tilt, absolute",
     "delay_ms": "7.5-15 (one or two reports at 133-266 points/s + USB; ASSUMPTION on the reported rates)",
     "noise": "resolution 0.01 mm; accuracy +-0.4-0.5 mm absolute (AMF-98, CON-84); jitter 10-50 um (ASSUMPTION)",
     "pros": "no line of sight; pressure gives contact; proven with ink pens on paper (OPT-86)",
     "cons": "needs an EMR pen; the coil is 5-10 mm above the ball (tilt error unless corrected with the reported "
     "tilt); metal and magnets of the stage distort the field; lower rate and higher delay than a camera",
     "label": "MANUFACTURER / LITERATURE (ledger ids) and ASSUMPTION"},
]


def summary() -> Dict:
    m5 = masses("A5")
    m6 = masses("A6")
    return {"concept": CONCEPT, "masses": {"A5": m5, "A6": m6}, "coarse_force": coarse_force(m5["coarse_moving_kg"]),
            "z_drop": z_drop(), "hold_down": {"A5": hold_down("A5"), "A6": hold_down("A6")},
            "pinch": pinch(m5["coarse_moving_kg"]), "paper_drag": paper_drag(), "bom": bom(), "power": power(),
            "noise": NOISE, "sizes": SIZES, "sensing_options": SENSING_OPTIONS, "sources": SRC}


# ------------------------------------------------------------------ the stage as the simulation uses it
def sim_stage(variant: str = "fine_A5"):
    """plant.Stage for a design variant (PROPOSED DESIGN values; the belt single stage is the cheaper alternative)."""
    from .plant import Stage
    m = masses("A5")
    if variant == "fine_A5":
        return Stage(m_f=round(m["fine_x_kg"], 3), F_peak_f=20.0, servo_hz=40.0, inner_hz=250.0)
    if variant == "fine_A6":
        m6 = masses("A6")
        return Stage(m_f=round(m6["fine_x_kg"], 3), F_peak_f=20.0, servo_hz=40.0, inner_hz=250.0)
    if variant == "fine_A5_coarse":
        return Stage(m_f=round(m["fine_x_kg"], 3), F_peak_f=20.0, servo_hz=40.0, inner_hz=250.0, coarse_on=True,
                     m_c=round(m["coarse_moving_kg"] - m["fine_x_kg"], 3))
    if variant == "belt_single":          # one belt H-bot carrying the plate directly (no voice coils)
        return Stage(m_f=round(m["coarse_moving_kg"] - 0.3, 3), F_peak_f=20.0, servo_hz=15.0, inner_hz=75.0,
                     Fc_f=0.5, c_f=4.0, enc_res=5e-6, vel_filter_hz=500.0, q_lim_f=5e-3)
    raise KeyError(variant)
