"""Tremor estimates for HW1 runs: the project's sensor models (fusion.sensors) and tremor tracker (fusion.estimators AKF).

Pattern (as fusion/harness.py does on model P1):
  1. run the pen with the tip held at centre ("neutral") on the tremor scenario, and on the same writing without tremor;
  2. build fusion sensor streams (gyroscope-compensated 6-axis IMU on the handle, 1 kHz page sensor) from the recorded
     handle motion, with their own noise draws;
  3. run the causal AKF -> d_hat per 2 kHz tick; the tip command is -d_hat (the AKF output already carries its own
     authority, gates and cap);
  4. run the closed loop with that command (the handle motion differs slightly from step 1 because of the tip
     reaction: reported as handle_departure_um).
The oracle is the true handle disturbance d = p_H(tremor) - p_H(clean) of step 1, with a non-causal preview equal to
the tip servo's group delay (perfect knowledge of the tremor, including its immediate future: a limit, not a design).

The AKF parameters are the shipped set of opt/tracker (tuned on the pencil model P1).  For a tip servo slower than
P1's, the prediction horizon is increased by the servo group delay (a physical compensation, not a tuning).  The
mechanism study's Rev H re-tune (results/opt/inertial_tracker_revh.json, training seeds only) is run as a variant
when the file exists.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfilt

from . import ensure_paths
from .params import Pen, servo_group_delay
from .plant import RIDX, Result, Scenario

ensure_paths()
from fusion import estimators as ES  # noqa: E402
from fusion import sensors as S  # noqa: E402

THETA = math.radians(50.0)


def record(res: Result, scn: Scenario, tick_decim: int) -> S.Record:
    """fusion.sensors.Record from an HW1 run (4 kHz record).  The handle acceleration passes the P1 core's 400 Hz
    4th-order Butterworth anti-aliasing filter; the page sensor validity uses the hand lift height."""
    t = res.t.copy()
    fs = 1.0 / float(t[1] - t[0])
    k = np.clip(np.round(t / scn.dt).astype(int), 0, len(scn.t) - 1)
    lift = scn.meta.get("lift")
    lz = np.zeros(len(t)) if lift is None else np.asarray(lift)[k]
    sos = butter(4, 400.0, fs=fs, output="sos")
    aH = np.column_stack([res["aHx"], res["aHy"], np.gradient(np.gradient(lz, t), t)])
    aH = sosfilt(sos, aH, axis=0)
    pH = np.column_stack([res["pHx"], res["pHy"], lz])
    con = res.contact.copy()
    s = np.where(con > 0.5, 0.5e-3, 0.0)
    return S.Record(t=t, pH=pH, aH=aH, s=s, contact=con, hand_tremor=np.asarray(scn.tremor)[k].copy(),
                    intended=np.asarray(scn.intended)[k].copy(), theta=THETA, phi=0.0, rho=0.0, z0=0.0, s_min=0.0,
                    n_steps=len(scn.t), dt=scn.dt, sdec=tick_decim)


def sensor_config(pen: Pen, sensors: Dict) -> S.SensorConfig:
    cfg = S.config(**sensors)
    cfg.r_board = pen.r_imu
    return cfg


def akf_estimate(res_neutral: Result, scn: Scenario, pen: Pen, tracker: Dict, sensor_seed: int,
                 horizon_comp: bool = True) -> Tuple[np.ndarray, Dict]:
    """Causal AKF estimate per tick from the neutral run's handle motion."""
    rec = record(res_neutral, scn, res_neutral.info["tick_decim"])
    st = S.make_streams(rec, sensor_config(pen, tracker["sensors"]), sensor_seed)
    p = dict(tracker["params"])
    if horizon_comp:
        p["horizon"] = float(p.get("horizon", 0.0)) + servo_group_delay(pen)
    dh, info = ES.run_estimator("akf", st, p)
    return dh, {"horizon_s": p["horizon"], "authority_mean": float(np.mean(info["authority"])),
                "f_est_median_hz": float(np.median(info["f_est"][info["authority"] > 0.05])) if np.any(info["authority"] > 0.05) else None}


def oracle_command(res_neutral: Result, res_clean: Result, pen: Pen, n_ticks: int, Ts: float) -> np.ndarray:
    """-d(t + preview) at the ticks, d = handle(tremor, neutral) - handle(clean, neutral)."""
    n = min(len(res_neutral.t), len(res_clean.t))
    t = res_neutral.t[:n]
    d = res_neutral.handle[:n] - res_clean.handle[:n]
    tt = np.arange(n_ticks) * Ts + servo_group_delay(pen)
    return -np.column_stack([np.interp(tt, t, d[:, 0]), np.interp(tt, t, d[:, 1])])


def truth(res_neutral: Result, res_clean: Result) -> np.ndarray:
    n = min(len(res_neutral.t), len(res_clean.t))
    return res_neutral.handle[:n] - res_clean.handle[:n]
