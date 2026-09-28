"""Where is the pen?  Hall-ring localisation of the pen magnet, and the options compared (CALC).

Recommended sensing: a ring of 3-axis Hall sensors (TI TMAG5170A2, AMF-95) on
the carriage, just under the glass, around the head magnet.  The head's own
field is axisymmetric, so it is the same at every sensor on the ring: it is
removed with a per-sensor calibration at each Z-lift height plus one common
scale factor fitted on line (it absorbs the magnet's temperature drift,
-0.12 %/K, AMF-27).  What remains is the pen magnet's field.  A dipole fit
(position, axis direction, moment) gives the pen magnet's position relative to
the head; the stage position (step count after homing) makes it absolute.
The ball position follows from the magnet position and the fitted pen axis
(the magnet sits 12 mm behind the ball, board.params).

Monte Carlo here: truth = magpylib field of the real disc magnet plus the
head field with a common scale error and a per-sensor calibration residual;
noise = TMAG5170A2 datasheet RMS noise reduced by averaging; fit = dipole
model with a common head scale (scipy least squares).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from . import params as P
from . import magnetics as M

MM = 1e-3


def ring(n: int = None, radius_mm: float = None, z_mm: float = None) -> np.ndarray:
    n = n or int(P.SENSE["n_sensors"].value)
    radius_mm = radius_mm or P.SENSE["ring_radius_mm"].value
    if z_mm is None:
        z_mm = -(P.STACK["paper_mm"].value + P.STACK["glass_mm"].value + 0.25)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([radius_mm * np.cos(a), radius_mm * np.sin(a), np.full(n, z_mm)], 1)


def dipole_B(r_sens_mm, c_mm, u, m) -> np.ndarray:
    """Field (T) of a point dipole at c (mm), unit axis u, moment m (A m2)."""
    r = (np.asarray(r_sens_mm) - np.asarray(c_mm)) * MM
    d = np.linalg.norm(r, axis=1)[:, None]
    rh = r / d
    mv = m * np.asarray(u)
    return 1e-7 * (3 * rh * (rh @ mv)[:, None] - mv) / d ** 3


def _unit(alt, az):
    return np.array([math.cos(alt) * math.cos(az), math.cos(alt) * math.sin(az), math.sin(alt)])


def head_ring_field(gap_mm: float, sensors=None) -> np.ndarray:
    sensors = ring() if sensors is None else sensors
    return M.head_field_at(sensors, gap_mm)


def noise_sigma_T(avg: int = None) -> np.ndarray:
    avg = avg or int(P.SENSE["averaging"].value)
    sxy = P.SENSE["noise_xy_uT_fast"].value * 1e-6 / math.sqrt(avg)
    sz = P.SENSE["noise_z_uT_fast"].value * 1e-6 / math.sqrt(avg)
    return np.array([sxy, sxy, sz])


def localise_mc(offsets_mm=((0, 0), (6, 0), (0, 10), (-12, 4), (8, -8), (15, 0)), gap_mm: float = None,
                n_draws: int = 40, seed: int = 1, avg: int = None, calib_resid_uT: float = 20.0,
                scale_err: float = 0.005, pen: M.PenMagnet = None) -> dict:
    """Monte Carlo of the pen-magnet localisation (magnet centre and ball) from the Hall ring."""
    rng = np.random.default_rng(seed)
    gap_mm = P.design_gap_mm() if gap_mm is None else gap_mm
    pen = pen or M.PenMagnet(mesh=60)
    sens = ring()
    Bh = head_ring_field(gap_mm, sens)
    sig = noise_sigma_T(avg)
    alt0, az0 = math.radians(pen.alt_deg), math.radians(pen.az_deg)
    m0 = pen.moment_Am2()
    rows = []
    for off in offsets_mm:
        c_true = np.array([off[0], off[1], pen.height_mm])
        B_pen = M.pen_field_at(sens, pen, c_true)
        errs, errs_ball, fit_bias = [], [], None
        # noise-free fit: bias of the dipole model against the real disc
        for draw in range(n_draws + 1):
            if draw == 0:
                meas = B_pen + Bh
            else:
                meas = (B_pen + Bh * (1 + rng.normal(0, scale_err)) +
                        rng.normal(0, calib_resid_uT * 1e-6, Bh.shape) + rng.normal(0, 1, Bh.shape) * sig)

            def resid(p):
                c = p[:3]
                u = _unit(p[3], p[4])
                model = dipole_B(sens, c, u, p[5]) + p[6] * Bh
                return ((model - meas) / sig).ravel()

            p0 = np.r_[c_true + rng.normal(0, 0.5, 3), alt0 + 0.05, az0 - 0.05, m0 * 1.05, 1.0]
            sol = least_squares(resid, p0, method="lm", xtol=1e-10, ftol=1e-10, max_nfev=400)
            c_fit = sol.x[:3]
            u_fit = _unit(sol.x[3], sol.x[4])
            # ball = magnet centre minus the lever along the (horizontal) pen azimuth
            lever = pen.behind_mm
            az_fit = math.atan2(u_fit[1], u_fit[0])
            ball_fit = c_fit[:2] - lever * np.array([math.cos(az_fit), math.sin(az_fit)])
            ball_true = c_true[:2] - lever * np.array([math.cos(az0), math.sin(az0)])
            e = c_fit[:2] - c_true[:2]
            eb = ball_fit - ball_true
            if draw == 0:
                fit_bias = {"magnet_xy_mm": float(np.hypot(*e)), "ball_xy_mm": float(np.hypot(*eb)),
                            "az_deg": float(math.degrees(az_fit - az0))}
            else:
                errs.append(e)
                errs_ball.append(eb)
        errs = np.array(errs)
        errs_ball = np.array(errs_ball)
        rows.append({
            "offset_mm": list(off),
            "dipole_model_bias": fit_bias,
            "magnet_xy_noise_rms_mm": float(np.sqrt(np.mean(np.sum((errs - errs.mean(0)) ** 2, 1)))),
            "magnet_xy_total_rms_mm": float(np.sqrt(np.mean(np.sum(errs ** 2, 1)))),
            "ball_xy_noise_rms_mm": float(np.sqrt(np.mean(np.sum((errs_ball - errs_ball.mean(0)) ** 2, 1)))),
            "ball_xy_total_rms_mm": float(np.sqrt(np.mean(np.sum(errs_ball ** 2, 1)))),
            "pen_field_at_ring_max_mT": float(np.abs(B_pen).max() * 1e3),
        })
    return {
        "gap_mm": gap_mm, "sensors": int(len(sens)), "ring_radius_mm": float(np.hypot(*sens[0, :2])),
        "head_field_at_ring_mT": {"max_abs_component": float(np.abs(Bh).max() * 1e3),
                                  "range_used_mT": 75.0, "fits_range": bool(np.abs(Bh).max() * 1e3 < 75.0)},
        "noise_sigma_uT": (noise_sigma_T(avg) * 1e6).tolist(), "averaging": avg or int(P.SENSE["averaging"].value),
        "calibration_residual_uT": calib_resid_uT, "head_scale_error_rms": scale_err,
        "rows": rows,
        "summary": {
            "magnet_noise_rms_mm_median": float(np.median([r["magnet_xy_noise_rms_mm"] for r in rows])),
            "ball_noise_rms_mm_median": float(np.median([r["ball_xy_noise_rms_mm"] for r in rows])),
            "ball_total_rms_mm_max": float(max(r["ball_xy_total_rms_mm"] for r in rows)),
            "dipole_bias_ball_mm_max": float(max(r["dipole_model_bias"]["ball_xy_mm"] for r in rows)),
        },
        "label": "CALC (Monte Carlo; MFR noise AMF-95; calibration residual and scale error ASSUMPTION)",
    }


def options_table() -> list:
    """Sensing options compared (values labelled)."""
    return [
        {"option": "EMR digitiser under the glass (Wacom-type)",
         "rate_Hz": "133-200 (MFR AMF-98)", "latency_ms": ">= 5-8 + USB/UART (CALC from rate)",
         "accuracy_mm": "+/-0.25 to +/-0.4 (MFR AMF-98)",
         "pen_hardware": "LC resonant coil on a ferrite core near the tip",
         "compatibility": "Poor: a Wacom digitiser is a sensor board plus a magnetic (soft-iron) sheet (MFR AMF-98); a sheet between head and pen would short the head's field, and the moving NdFeB head and steel stage would disturb the EMR field. The ferrite in the pen would also be pulled by the head.",
         "availability": "OEM modules exist (Wacom components catalogue 2010, sensor boards 6-14 inch, 2.7 mm thick; Hanvon Ugee business EMR modules) - MFR AMF-98; pen-coil parts: Chinese EMR refills sold as spares (search summary only, not verified)",
         "verdict": "Reject for the magnetic board; good choice for architecture (iii) if encoders were not enough"},
        {"option": "Pen's own sensors over BLE (paper optical-flow sensor + IMU in Rev H)",
         "rate_Hz": "1000 in the pen; 67-133 over BLE (7.5-15 ms connection interval, ASSUMPTION)",
         "latency_ms": "10-20 (ASSUMPTION)", "accuracy_mm": "relative only; drifts with distance (OPT-01/02 class)",
         "pen_hardware": "already in Rev H (optional paper sensor)",
         "compatibility": "Good, no interference; cannot give absolute page position alone",
         "availability": "in the pen", "verdict": "Secondary: pen-up tracking, pen-down flag, tilt; fuse with the ring"},
        {"option": "Camera above the page",
         "rate_Hz": "30-120 (ASSUMPTION)", "latency_ms": "20-50 (ASSUMPTION)",
         "accuracy_mm": "0.2-0.5 on A4 with a marker on the pen's rear (ASSUMPTION); hand occludes the tip",
         "pen_hardware": "a marker", "compatibility": "Good, but needs an arm over the desk",
         "availability": "commodity", "verdict": "Optional: page registration and video for therapists; not in the force loop"},
        {"option": "Carriage Hall ring + stage position (recommended)",
         "rate_Hz": "1000 (8x averaging; AMF-95 conversion times)", "latency_ms": "about 1.5 (CALC, board.stage.latency_budget)",
         "accuracy_mm": "see localise_mc: noise and dipole-model bias; stage position error after homing 0.1-0.2 (ASSUMPTION)",
         "pen_hardware": "none beyond the force magnet (the same magnet is sensed)",
         "compatibility": "Designed together with the head (axisymmetric head field is common-mode on the ring)",
         "availability": "catalogue parts (TMAG5170, AMF-95)",
         "verdict": "Choose: measures exactly the offset that sets the force, at the loop rate"},
    ]
