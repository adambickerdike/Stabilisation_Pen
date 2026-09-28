"""CoreXY stage under the glass: speed, acceleration, modes, bandwidth, latency, power (CALC).

Motor data are MFR (AMF-92, 17HS19-2004S1); driver limits MFR (AMF-93,
TMC2209); the torque-speed curve is a CALC from a simple hybrid-stepper model:
peak torque constant k_t = T_hold / I_rated, back-EMF constant k_e = k_t,
50 rotor teeth, phase voltage limited to the bus voltage.  Belt stiffness is an
ASSUMPTION (no verified datasheet value).
"""
from __future__ import annotations

import math

import numpy as np

from . import params as P

S = P.STAGE


def pulley_radius_m() -> float:
    return S["pulley_teeth"].value * 2e-3 / (2 * math.pi)


def torque_at_speed(v_mm_s: float, I_set: float = None, V: float = None) -> float:
    """Available motor torque (N m) at belt speed v (mm/s)."""
    I_set = S["I_run_A"].value if I_set is None else I_set
    V = S["V_bus"].value if V is None else V
    kt = S["motor_hold_Nm"].value / S["motor_I_rated_A"].value
    R, L = S["motor_R_ohm"].value, S["motor_L_H"].value
    w = abs(v_mm_s) * 1e-3 / pulley_radius_m()
    we = 50 * w
    # (I R)^2 + (I we L + ke w)^2 = V^2  ->  a I^2 + b I + c = 0
    a = R ** 2 + (we * L) ** 2
    b = 2 * we * L * kt * w
    c = (kt * w) ** 2 - V ** 2
    disc = b * b - 4 * a * c
    I_av = 0.0 if disc < 0 else max(0.0, (-b + math.sqrt(disc)) / (2 * a))
    return kt * min(I_set * math.sqrt(2), I_av)  # I_set is RMS; the peak phase current sets torque


def effective_mass(axis: str) -> float:
    """Mass seen by the belts for a pure x or y move (kg), including both rotors (CoreXY)."""
    J = S["motor_J_kgm2"].value
    r = pulley_radius_m()
    m = S["carriage_mass_kg"].value if axis == "x" else S["gantry_mass_kg"].value + S["carriage_mass_kg"].value
    return m + 2 * J / r ** 2


def max_accel(axis: str, v_mm_s: float = 0.0, load_N: float = 1.5) -> float:
    """Acceleration capability (m/s^2) along x or y at speed v with a load force (friction + magnet)."""
    F = 2 * torque_at_speed(v_mm_s) / pulley_radius_m() - load_N - S["friction_N"].value
    return max(F, 0.0) / effective_mass(axis)


def top_speed(load_N: float = 1.5) -> float:
    """Speed (mm/s) where the motors can just hold the load and friction."""
    lo, hi = 1.0, 2000.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if 2 * torque_at_speed(mid) / pulley_radius_m() > load_N + S["friction_N"].value:
            lo = mid
        else:
            hi = mid
    return lo


def belt_mode_hz(axis: str) -> float:
    """First mode of the carriage (x) or gantry (y) on the belts (CALC, ASSUMPTION belt EA)."""
    EA = S["belt_EA_N"].value
    L = 0.35  # effective free belt length on each side (m), ASSUMPTION from the 300 x 400 frame
    k_belt = 2 * EA / L
    kt = S["motor_hold_Nm"].value * (S["I_run_A"].value * math.sqrt(2) / S["motor_I_rated_A"].value)
    k_motor = kt * 50 / pulley_radius_m() ** 2   # stepper static stiffness at the belt
    k = 1.0 / (1.0 / k_belt + 1.0 / (2 * k_motor))
    m = S["carriage_mass_kg"].value if axis == "x" else S["gantry_mass_kg"].value + S["carriage_mass_kg"].value
    return math.sqrt(k / m) / (2 * math.pi)


def bandwidth_hz() -> dict:
    fx, fy = belt_mode_hz("x"), belt_mode_hz("y")
    f1 = min(fx, fy)
    return {"mode_x_Hz": fx, "mode_y_Hz": fy, "position_bandwidth_Hz": f1 / 3.0,
            "rule": "closed-loop position bandwidth about one third of the first mode (ASSUMPTION, input-shaped step commands)"}


def latency_budget() -> dict:
    items = {
        "hall_conversion_ms": 0.6,   # TMAG5170 3 axes, 8x averaging (AMF-95 conversion times: 25 us per sample per axis)
        "spi_read_8_sensors_ms": 0.1,  # 8 x 3 x 32 bit at 10 MHz (AMF-95)
        "pose_fit_ms": 0.2,           # Gauss-Newton, 6 unknowns, 24 residuals, Cortex-M33 (ASSUMPTION)
        "control_and_allocation_ms": 0.1,
        "step_generation_ms": 0.5,    # half a 1 kHz tick
    }
    bw = bandwidth_hz()["position_bandwidth_Hz"]
    items["stage_equivalent_delay_ms"] = 1e3 / (2 * math.pi * bw)
    total = sum(items.values())
    return {**{k: round(v, 3) for k, v in items.items()}, "total_effective_ms": round(total, 2),
            "label": "CALC from MFR conversion times (AMF-95) and ASSUMPTION compute times; stage delay = 1/(2 pi f_bw)",
            "comparison": "Langerak et al.: ~10 ms pen-to-magnet, ~20 ms total (LIT HAP-16)"}


def handwriting_demand() -> dict:
    """What the head must do to follow a writer (CALC from ASSUMPTION writing kinematics)."""
    v_pen = 150.0          # mm/s peak pen speed, fast adult (ASSUMPTION; config speed_typ 30 mm/s, max 80 mm/s)
    a_pen = (2 * math.pi * 5) ** 2 * 2e-3  # 2 mm amplitude at 5 Hz strokes (m/s^2)
    a_force = (2 * math.pi * 20) ** 2 * 1e-3  # 1 mm offset modulation at 20 Hz (force changes)
    return {"pen_speed_peak_mm_s": v_pen, "pen_accel_m_s2": a_pen, "offset_modulation_accel_m_s2": a_force,
            "required_accel_m_s2": a_pen + a_force,
            "label": "CALC from ASSUMPTION kinematics (config writing.speed_typ, stroke_freq)"}


def power_budget(duty_moving: float = 0.6) -> dict:
    R = S["motor_R_ohm"].value
    I = S["I_run_A"].value
    p_motor_run = 2 * I ** 2 * R            # two phases, RMS current each
    p_motor_hold = 2 * (0.3 * I) ** 2 * R   # standby current reduction to 30 % (AMF-93 feature; setting ASSUMPTION)
    p_driver = 2 * 2 * I ** 2 * 0.17        # HS + LS 0.17 ohm typ (AMF-93) per phase
    p_motors = 2 * (duty_moving * (p_motor_run + p_driver) + (1 - duty_moving) * p_motor_hold)
    p_servo = 0.35   # XL330 holding (ASSUMPTION; stall 1.47 A at 5 V, AMF-96)
    p_logic = 0.25   # MCU + 8 Hall sensors 3.4 mA each (AMF-95) + LEDs (ASSUMPTION)
    total = p_motors + p_servo + p_logic
    eff = 0.905      # AMF-97 GST60A24 typical efficiency
    return {"motor_copper_W_each_running": p_motor_run, "driver_W_each_running": p_driver,
            "motors_and_drivers_W_avg": p_motors, "servo_W": p_servo, "logic_W": p_logic,
            "board_W_avg": total, "wall_W_avg": total / eff, "peak_W": 2 * (p_motor_run + p_driver) + 1.5 * 5 + p_logic,
            "magnet_force_power_W": 0.0,
            "label": "CALC from MFR resistances and currents (AMF-92/93/96/97) with ASSUMPTION duty"}


# ----------------------------------------------------------------------------- cover plate
def plate_D(t_mm: float) -> float:
    E = P.STACK["glass_E_GPa"].value * 1e9
    nu = P.STACK["glass_nu"].value
    t = t_mm * 1e-3
    return E * t ** 3 / (12 * (1 - nu ** 2))


def plate_deflection(x_mm, y_mm, load_xy_mm, load_N: float, a_mm: float, b_mm: float, t_mm: float,
                     n_terms: int = 31) -> np.ndarray:
    """Simply supported rectangular plate, point load (Navier series).  Returns deflection (mm)."""
    D = plate_D(t_mm)
    a, b = a_mm * 1e-3, b_mm * 1e-3
    xi, eta = load_xy_mm[0] * 1e-3, load_xy_mm[1] * 1e-3
    x = np.asarray(x_mm, float) * 1e-3
    y = np.asarray(y_mm, float) * 1e-3
    w = np.zeros(np.broadcast(x, y).shape)
    for m in range(1, n_terms + 1, 1):
        sm = math.sin(m * math.pi * xi / a)
        if abs(sm) < 1e-12:
            continue
        for n in range(1, n_terms + 1, 1):
            sn = math.sin(n * math.pi * eta / b)
            if abs(sn) < 1e-12:
                continue
            coef = sm * sn / ((m / a) ** 2 + (n / b) ** 2) ** 2
            w = w + coef * np.sin(m * math.pi * x / a) * np.sin(n * math.pi * y / b)
    return 4 * load_N / (a * b * D * math.pi ** 4) * w * 1e3


def cover_check(t_mm: float = None, span=(250.0, 330.0), load_N: float = 10.0) -> dict:
    t_mm = P.STACK["glass_mm"].value if t_mm is None else t_mm
    a, b = span
    w_c = float(plate_deflection(a / 2, b / 2, (a / 2, b / 2), load_N, a, b, t_mm))
    # centre bending stress, point load spread over a 20 mm radius palm (Timoshenko approximation)
    nu = P.STACK["glass_nu"].value
    t = t_mm * 1e-3
    r0 = 0.02
    sigma = 3 * load_N * (1 + nu) / (2 * math.pi * t ** 2) * (math.log(2 * a * 1e-3 / (math.pi * r0)) + 1.0)
    return {"glass_mm": t_mm, "span_mm": list(span), "load_N": load_N, "centre_deflection_mm": w_c,
            "load_for_clearance_contact_N": load_N * P.STACK["clearance_mm"].value / w_c,
            "centre_stress_MPa_at_100N": sigma * 100.0 / load_N / 1e6,
            "label": "CALC (Kirchhoff plate, simply supported; glass properties ASSUMPTION)",
            "note": "chemically strengthened glass or a bonded anti-shatter film is needed at a 100 N lean load (annealed glass design strength is of the same order)"}


def summary() -> dict:
    return {
        "pulley_radius_mm": pulley_radius_m() * 1e3,
        "microstep_mm": 40.0 / (200 * S["microsteps"].value),
        "effective_mass_kg": {"x": effective_mass("x"), "y": effective_mass("y")},
        "torque_Nm_at": {str(v): torque_at_speed(v) for v in (0, 100, 200, 300, 400)},
        "accel_m_s2_at_200mm_s": {"x": max_accel("x", 200), "y": max_accel("y", 200)},
        "top_speed_mm_s": top_speed(),
        **bandwidth_hz(),
        "latency": latency_budget(),
        "demand": handwriting_demand(),
        "power": power_budget(),
        "cover": cover_check(),
        "cover_1p1mm_A5": cover_check(1.1, (180.0, 245.0)),
        "cover_1p5mm_A5": cover_check(1.5, (180.0, 245.0)),
    }
