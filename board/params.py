"""Design values for the guidance board, each with a label and a source.

Labels: CALC (calculated here), SIM (simulated here), MFR (manufacturer
statement, ledger id), LIT (literature, ledger id), ASSUMPTION (chosen here;
the experiment that measures it is named in docs/guidance_board.md section 8).
Nothing here is a measurement of our hardware.

Frames
------
Board frame: x right, y away from the writer, z up; origin at the board's
front-left corner on the writing surface (top of the cover glass).
Pen frame: the ball touches the paper; the pen axis points from the ball up
and back at the altitude angle ``alt`` and the azimuth ``az`` (az = -90 deg:
the pen's rear points toward the writer).
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class V:
    """A labelled value."""
    value: float
    unit: str
    label: str
    source: str
    note: str = ""

    def as_dict(self):
        d = {"value": self.value, "unit": self.unit, "label": self.label, "source": self.source}
        if self.note:
            d["note"] = self.note
        return d


MU0 = 4e-7 * math.pi

# --------------------------------------------------------------------- pen side
PEN = {
    # Pen add-on: one K&J D42-N52 disc (6.35 x 3.17 mm) fixed in the heel of the
    # Rev H front sleeve / skid ring (moves with the HANDLE, not with the nose).
    "pen_magnet_d_mm": V(6.35, "mm", "MFR", "AMF-91 (K&J D42-N52)"),
    "pen_magnet_h_mm": V(3.17, "mm", "MFR", "AMF-91 (K&J D42-N52)"),
    "pen_magnet_Br_T": V(1.45, "T", "MFR", "AMF-28 (N52 Br 1.45-1.48 T, lower bound); AMF-91 Br max 1.48 T"),
    "pen_magnet_mass_g": V(0.75, "g", "MFR", "AMF-91"),
    "pen_magnet_height_mm": V(3.8, "mm", "ASSUMPTION",
                              "centre above the paper at 50 deg: half-extent 3.26 mm of a 6.35 x 3.17 disc tilted 40 deg from vertical plus 0.5 mm clearance",
                              "Rev H team to confirm in CAD (heel boss of the front sleeve)"),
    "pen_magnet_behind_ball_mm": V(16.5, "mm", "CALC",
                                   "disc edge outside the nose envelope (fixed-sleeve bore radius 6.47 mm + 0.5 mm wall, results/revH/layout.json): centre 10.2 mm off-axis, 13.5 mm along the axis, 3.8 mm high at 50 deg",
                                   "horizontal distance from the ball to the magnet centre, along the pen azimuth; a keel under the fixed front sleeve"),
    "pen_magnet_axial_mm": V(13.5, "mm", "CALC", "pen frame: along the axis from the ball"),
    "pen_magnet_radial_mm": V(10.2, "mm", "CALC", "pen frame: off-axis toward the paper side"),
    "alt_deg": V(50.0, "deg", "ASSUMPTION", "config/parameters.yaml writing.tilt_deg (REQ-ENV-001)", "sweep 35-75 deg"),
    "az_deg": V(-90.0, "deg", "ASSUMPTION", "pen rear toward the writer (right-hander about -60 to -120 deg)"),
    "nose_continuous_force_N": V(0.21, "N", "CALC", "results/revH/tip_params.json actuator.force_limit_at_tip_N.continuous",
                                 "why the board magnet may not ride on the moving nose"),
    "nose_suspension_N_per_m": V(12.35, "N/m", "ASSUMPTION", "results/revH/tip_params.json suspension_stiffness_N_per_m"),
    "pen_mass_kg": V(0.075, "kg", "CALC", "results/revH/layout.json mass_g.total_g 74.95"),
}

# --------------------------------------------------------------------- head
HEAD = {
    "head_d_mm": V(12.7, "mm", "MFR", "AMF-90 (K&J D88-N52, 12.7 x 12.7 mm, axial)"),
    "head_h_mm": V(12.7, "mm", "MFR", "AMF-90"),
    "head_Br_T": V(1.45, "T", "MFR", "AMF-28 N52 lower bound; AMF-90 Br max 1.48 T"),
    "head_mass_g": V(12.07, "g", "MFR", "AMF-90"),
    "zlift_travel_mm": V(12.0, "mm", "ASSUMPTION", "cam on the Z servo (AMF-96); retracted = working gap + 12 mm"),
    "diam_head_d_mm": V(12.7, "mm", "MFR", "AMF-99 (K&J D8X0DIA 12.7 x 25.4 mm N42, diametric) - variant only"),
    "diam_head_h_mm": V(25.4, "mm", "MFR", "AMF-99"),
    "diam_head_Br_T": V(1.30, "T", "MFR", "AMF-28 N42 lower bound; AMF-99 Br max 1.32 T"),
}

# --------------------------------------------------------------------- writing surface stack
STACK = {
    "paper_mm": V(0.2, "mm", "ASSUMPTION", "one or two 80 g/m2 sheets plus a thin underlay"),
    "glass_mm": V(3.0, "mm", "CALC", "A4 span 294 x 357 mm: 2 mm glass would touch the head at ~20 N of hand load, 3 mm at ~70 N (board.stage.cover_check); A5 keeps 2 mm"),
    "glass_mm_A5": V(2.0, "mm", "CALC", "A5 span ~202 x 270 mm (board.stage.cover_check)"),
    "clearance_mm": V(0.5, "mm", "ASSUMPTION", "running clearance head-to-glass incl. flatness"),
    "glass_E_GPa": V(72.0, "GPa", "ASSUMPTION", "soda-lime / aluminosilicate glass, textbook class value"),
    "glass_nu": V(0.22, "-", "ASSUMPTION", "textbook class value"),
    "glass_density_kg_m3": V(2500.0, "kg/m3", "ASSUMPTION", "textbook class value"),
}


def design_gap_mm(stack=STACK) -> float:
    """Paper top surface (where the pen writes) to the top face of the head magnet."""
    return stack["paper_mm"].value + stack["glass_mm"].value + stack["clearance_mm"].value


# --------------------------------------------------------------------- hand (HAP-26 two-stage, config/parameters.yaml)
HAND = {
    "k1": V(575.0, "N/m", "LIT", "HAP-26 grip stiffness (config hand.grip_stiffness)"),
    "b1": V(1.3, "N s/m", "LIT", "HAP-26 grip damping"),
    "M": V(0.21, "kg", "LIT", "HAP-26 hand/arm mass (M1/P1 convention)"),
    "k2": V(170.0, "N/m", "LIT", "HAP-26 arm stiffness"),
    "b2": V(11.0, "N s/m", "LIT", "HAP-26 arm damping"),
    "k1_range": V((230.0, 1040.0), "N/m", "LIT", "HAP-26 95 % CI sweep"),
    "k2_range": V((63.0, 533.0), "N/m", "LIT", "HAP-26 95 % CI sweep"),
    "b2_range": V((3.7, 27.6), "N s/m", "LIT", "HAP-26 95 % CI sweep"),
    "mu_paper": V(0.15, "-", "ASSUMPTION", "config writing.mu_eff (skid / ball on paper)"),
    "writing_force_N": V(1.0, "N", "ASSUMPTION", "config writing.normal_force (REQ-ENV-002)"),
}

# --------------------------------------------------------------------- stage (CoreXY)
STAGE = {
    "motor_hold_Nm": V(0.59, "N m", "MFR", "AMF-92 (17HS19-2004S1)"),
    "motor_I_rated_A": V(2.0, "A", "MFR", "AMF-92"),
    "motor_R_ohm": V(1.40, "ohm", "MFR", "AMF-92"),
    "motor_L_H": V(3.0e-3, "H", "MFR", "AMF-92"),
    "motor_J_kgm2": V(82e-7, "kg m2", "MFR", "AMF-92 (82 g cm2)"),
    "motor_mass_kg": V(0.40, "kg", "MFR", "AMF-92"),
    "I_run_A": V(1.2, "A", "ASSUMPTION", "TMC2209 run current (<= 2 A RMS, AMF-93); quiet, cool"),
    "V_bus": V(24.0, "V", "MFR", "AMF-97 (GST60A24-P1J 24 V 2.5 A)"),
    "pulley_teeth": V(20, "-", "ASSUMPTION", "GT2 20-tooth pulley, 2 mm pitch: 40 mm per revolution"),
    "microsteps": V(16, "-", "ASSUMPTION", "TMC2209 16 microsteps interpolated to 256 (AMF-93)"),
    "carriage_mass_kg": V(0.16, "kg", "CALC", "head magnet 12 g (AMF-90) + servo 18 g (AMF-96) + MGN9H block 26 g (AMF-94) + plate, cam, Hall ring PCB, clamps 100 g (ASSUMPTION)"),
    "gantry_mass_kg": V(0.42, "kg", "CALC", "MGN9 rail 0.38 kg/m x 0.30 m (AMF-94) + 2 MGN12H blocks 0.108 kg + beam 0.15 kg (ASSUMPTION) + carriage"),
    "belt_EA_N": V(25000.0, "N", "ASSUMPTION", "GT2 6 mm glass-cord belt axial stiffness per unit strain; range 15-40 kN; no verified datasheet (Gates does not publish it)"),
    "belt_loop_m": V(1.3, "m", "CALC", "CoreXY belt length per motor for a 300 x 400 mm frame"),
    "friction_N": V(1.5, "N", "ASSUMPTION", "rails, belts, idlers"),
    "loop_rate_Hz": V(1000.0, "Hz", "ASSUMPTION", "control loop"),
}

# --------------------------------------------------------------------- sensing (carriage Hall ring)
SENSE = {
    "n_sensors": V(8, "-", "ASSUMPTION", "ring of 3-axis Hall sensors on the carriage"),
    "ring_radius_mm": V(22.0, "mm", "CALC", "head field at the ring < 75 mT range (board.sensing)"),
    "noise_xy_uT_fast": V(160.0, "uT", "MFR", "AMF-95 TMAG5170A2 NRMS X/Y, CONV_AVG 000, 25 C"),
    "noise_z_uT_fast": V(72.0, "uT", "MFR", "AMF-95 TMAG5170A2 NRMS Z, CONV_AVG 000"),
    "noise_xy_uT_avg32": V(28.0, "uT", "MFR", "AMF-95 TMAG5170A2 NRMS X/Y, CONV_AVG 101 (32x)"),
    "noise_z_uT_avg32": V(13.0, "uT", "MFR", "AMF-95 TMAG5170A2 NRMS Z, CONV_AVG 101"),
    "averaging": V(8, "-", "ASSUMPTION", "8x averaging: ~0.6 ms for 3 axes (AMF-95 conversion times), 1 kHz frame"),
    "gain_error_after_cal": V(0.003, "-", "ASSUMPTION", "residual gain error after a one-time calibration (datasheet total error +/-2.6 % before calibration, AMF-95)"),
    "placement_error_mm": V(0.05, "mm", "ASSUMPTION", "residual sensor position error after calibration"),
}

# --------------------------------------------------------------------- control defaults
CONTROL = {
    "force_cap_N": V(0.40, "N", "ASSUMPTION", "software cap below the magnetic breakaway (board.magnetics)"),
    "slew_N_per_s": V(8.0, "N/s", "ASSUMPTION", "force rate limit (no jerks)"),
    "partial_deadband_mm": V(1.0, "mm", "ASSUMPTION", "HAP-03 assist-as-needed deadband; HAP-15 retroactive guidance"),
    "partial_gain_N_per_mm": V(0.10, "N/mm", "ASSUMPTION", "a quarter of Bluteau's 0.4 N/mm (HAP-10), limited by the magnet"),
    "full_gain_N_per_mm": V(0.20, "N/mm", "ASSUMPTION", "half of Bluteau's 0.4 N/mm (HAP-10)"),
    "damping_N_s_per_m": V(2.0, "N s/m", "ASSUMPTION", "normal damping of the path spring"),
    "lead_force_N": V(0.10, "N", "ASSUMPTION", "full guidance: tangential pull along the path, only while the writer moves forward"),
    "override_error_mm": V(4.0, "mm", "ASSUMPTION", "sustained error that counts as the writer overriding"),
    "override_time_s": V(0.30, "s", "ASSUMPTION", "HAP-22/23: yield when the writer persistently deviates"),
    "head_speed_max_mm_s": V(300.0, "mm/s", "CALC", "stepper torque at 24 V (board.stage)"),
}

A4_MM = (210.0, 297.0)
A5_MM = (148.0, 210.0)


def table(d: dict) -> dict:
    return {k: v.as_dict() for k, v in d.items()}


def all_tables() -> dict:
    return {"pen": table(PEN), "head": table(HEAD), "stack": table(STACK), "hand": table(HAND),
            "stage": table(STAGE), "sensing": table(SENSE), "control": table(CONTROL),
            "design_gap_mm": {"value": design_gap_mm(), "unit": "mm", "label": "CALC", "source": "paper + glass + clearance"}}
