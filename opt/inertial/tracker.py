r"""The accelerometer tremor tracker (fusion AKF, shipped adjoint-tuned set) on model H1 runs.

Sensor streams are generated from the H1 record of the body that carries the IMU (the Rev H handle; the pen body for
architecture B, the grip sleeve for architecture A), with the TRUE pen rotation of H1 (not fusion's kinematic rotation
model), then passed through fusion's own reading models (noise, bias, drift, scale, misalignment, quantisation:
fusion.sensors, read-only) and its gyroscope compensation of gravity and lever arm, and finally fusion.estimators.akf
with results/opt/tracker_models/akf_ship.json.  The page sensor sees the tip point of the same body (P1 default 1 kHz /
2 ms / 3 um, ASSUMPTION).  Output: the disturbance estimate per 2 kHz stage tick (what the stage or the active nose
cancels), expanded onto the simulation steps.
Causality: every sample is used only after its availability time (fusion's convention).  In closed loop the IMU body
moves differently from the open-loop run; `iterate()` regenerates the streams from the controlled run and re-applies
the estimate (the fusion harness's check), reporting the change.
Evidence status: SIMULATION.
"""
from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from typing import Dict, Optional

import numpy as np
from scipy.signal import butter, lfilter, sosfilt

from fusion import estimators as ES
from fusion import sensors as FS
from sim.handpen import model as HM
from sim.handpen.params import geometry_vectors

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHIP = os.path.join(ROOT, "results", "opt", "tracker_models", "akf_ship.json")
REC_HZ = 4000.0
G_VEC = np.array([0.0, 0.0, -FS.G0])


@lru_cache(maxsize=1)
def ship_params() -> Dict:
    d = json.load(open(SHIP))
    return dict(d["params"])


def body_kinematics(res, body="pen", z_imu=0.100, theta_deg=50.0, phi_deg=0.0):
    """Page-frame position of the tip point (z = 0) and of the IMU point, the rotation vector and its rates of the body
    that carries the IMU, from an H1 record."""
    a, t1, t2, n, h = geometry_vectors(theta_deg, phi_deg)
    t = res["t"]
    if body == "pen":
        p = np.column_stack([res["bx"], res["by"], res["bz"]])
        b1, b2 = res["b1"], res["b2"]
    else:
        p = np.column_stack([res["sx"], res["sy"], res["sz"]])
        b1, b2 = res["sb1"], res["sb2"]
    phi = -b2[:, None] * t1[None, :] + b1[:, None] * t2[None, :]
    imu = p + z_imu * (a[None, :] + b1[:, None] * t1[None, :] + b2[:, None] * t2[None, :])
    return t, p, imu, phi, a


def make_streams(res, scn, seed: int, body="pen", z_imu=0.100, theta_deg=50.0, page_rate=1000.0, page_latency=2e-3,
                 page_noise=3e-6, lift_max=0.8e-3, z_contact=None) -> FS.Streams:
    """Sensor streams of one H1 run (see module doc).  The record must be at 4 kHz (HM.run(..., rec_hz=REC_HZ))."""
    rng = np.random.default_rng(seed)
    t, p, imu, phi, a = body_kinematics(res, body, z_imu, theta_deg)
    fs = 1.0 / float(t[1] - t[0])
    dt = 1.0 / fs
    sos_aa = FS.aa_sos(fs)
    acc_imu = np.gradient(np.gradient(imu, dt, axis=0), dt, axis=0)
    Om = phi
    Omd = np.gradient(Om, dt, axis=0)
    # specific force in the body frame: R^T (a - g) with R = (I + [phi]x) R0 (small rotation)
    from stabpen.frames import basis
    Bs = basis(theta_deg * math.pi / 180.0, 0.0, 0.0)
    R0 = np.column_stack([Bs["xH"], Bs["yH"], Bs["a"]])
    f_page = acc_imu - G_VEC
    f_rot = f_page - np.cross(Om, f_page)                    # (I - [phi]x)(a - g): page vector expressed in the rotated frame
    f_body = sosfilt(sos_aa, f_rot, axis=0) @ R0
    w_body = sosfilt(sos_aa, Omd, axis=0) @ R0
    acc_m = FS.AccelModel()
    gyr_m = FS.GyroModel()
    t_end = float(t[-1])
    t_a = np.arange(rng.uniform(0, 1.0 / acc_m.odr), t_end, 1.0 / acc_m.odr)
    fb = FS._accel_readings(f_body, t, t_a, acc_m, rng)
    wb = FS._gyro_readings(w_body, t, t_a, gyr_m, acc_m.odr, rng)
    # fusion's 'gyro' compensation: attitude from the leaky-integrated gyro removes gravity; lever arm removed with r x alpha
    dta = 1.0 / acc_m.odr
    wp = wb @ R0.T
    Omh = FS._leaky_integrate(wp, dta, 2.0)
    fp = fb @ R0.T
    est = fp + G_VEC + np.cross(Omh, fp)
    alpha = np.vstack([np.zeros((1, 3)), np.diff(wp, axis=0) / dta])
    alpha = sosfilt(butter(2, 300.0, fs=acc_m.odr, output="sos"), alpha, axis=0)
    est = est - z_imu * np.cross(alpha, a)
    # page sensor on the tip point of the same body
    t_p = np.arange(rng.uniform(0, 1.0 / page_rate), t_end, 1.0 / page_rate)
    pos = np.column_stack([np.interp(t_p, t, p[:, 0]), np.interp(t_p, t, p[:, 1])]) + rng.standard_normal((len(t_p), 2)) * page_noise
    zc = p[:, 2] if z_contact is None else z_contact
    hz = np.interp(t_p, t, zc) - float(np.min(zc[len(zc) // 10:]))
    pos_ok = (hz < lift_max).astype(np.float64)
    # contact stream (unused by the AKF)
    t_c = np.arange(rng.uniform(0, 1e-3), t_end, 1e-3)
    con = (np.interp(t_c, t, res["contact"]) > 0.5).astype(np.float64)
    Ts = scn_tick(res)
    n_ticks = int(math.ceil(len(scn.t) * HM.DT / Ts - 1e-9))
    tick_t = np.arange(n_ticks) * Ts
    return FS.Streams(tick_t=tick_t, acc_t=t_a, acc_av=t_a + acc_m.extra_latency, acc=np.ascontiguousarray(est[:, :2]),
                      pos_t=t_p, pos_av=t_p + page_latency, pos=np.ascontiguousarray(pos), pos_ok=pos_ok,
                      con_t=t_c, con_av=t_c + 1e-3, con=con, meta={"seed": seed, "body": body, "z_imu": z_imu})


def scn_tick(res):
    return 0.5e-3


def estimate(res, scn, seed, body="pen", z_imu=0.100, theta_deg=50.0, params: Optional[Dict] = None, gain: float = 1.0):
    """AKF estimate per tick (n_ticks x 2) and the info dict (frequency, authority)."""
    st = make_streams(res, scn, seed, body=body, z_imu=z_imu, theta_deg=theta_deg)
    prm = dict(ship_params())
    if params:
        prm.update(params)
    dh, info = ES.akf(st, prm)
    return dh * gain, info, st


def to_steps(dhat_ticks, n_steps, sdec=20):
    return FS.expand_to_steps(dhat_ticks, n_steps, sdec)


def freq_to_steps(f_ticks, n_steps, sdec=20):
    return np.ascontiguousarray(np.repeat(np.asarray(f_ticks, float), sdec)[:n_steps])
