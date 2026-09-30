r"""Pen sensors on top of sim2's native kinematics.

Offline streams (the tracker's input, fusion.estimators convention):
  IMU        specific force and body rates of the IMU site from MuJoCo's full nonlinear kinematics (site velocity and
             angular velocity recorded at 4 kHz, rotation matrix of the site): f_body = R^T (a - g) with the physical
             gravity (also when the dynamics run with gravity off, H1 convention), anti-aliasing 4th-order 400 Hz, then
             fusion's reading models (LSM6DSV16X class: noise density, ODR 3840 Hz, bias, Gauss-Markov drift, scale,
             misalignment, 16-bit quantisation and range) and the firmware's 'gyro' compensation (leaky-integrated
             attitude removes the gravity leak; lever arm removed with r x d(omega)/dt), as opt/inertial/tracker.py.
  page       optical flow at the handle's tip point: 1 kHz, 2 ms latency, 3 um noise, valid below 0.8 mm lift.
  contact    refill slide Hall: 1 kHz, 1 ms, 2 um, contact when the slide exceeds its front stop by 0.1 mm.
Online sensors (Gymnasium observations, one sample per control tick, causal): IMU block average over the tick with
the same noise densities, nose Hall angle (tip-referred noise), delayed page-sensor displacement, writing force (skid
ring load cell), refill slide.  Every value is SIMULATION; the noise figures are MFR (OPT-37) or ASSUMPTION (params.py).
"""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, Optional

import numpy as np
from scipy.signal import butter, sosfilt

from fusion import estimators as ES
from fusion import sensors as FS

from . import params as P

G_VEC = np.array([0.0, 0.0, -FS.G0])


def imu_kinematics(res, g_phys: bool = True):
    """(t, f_body (n,3), w_body (n,3), R0) at the record rate from a sim2 Result."""
    t = res["t"]
    fs = 1.0 / float(t[1] - t[0])
    v = np.column_stack([res["imuvx"], res["imuvy"], res["imuvz"]])
    w = np.column_stack([res["imuwx"], res["imuwy"], res["imuwz"]])
    R = res.R_imu()
    a = np.gradient(v, 1.0 / fs, axis=0)
    f_world = a - G_VEC
    f_body = np.einsum("nji,nj->ni", R, f_world)          # R^T f
    w_body = np.einsum("nji,nj->ni", R, w)
    return t, fs, f_body, w_body, R


def make_streams(res, seed: int, z_imu: float, page_rate: float = 1000.0, page_latency: float = 2e-3,
                 page_noise: float = 3e-6, lift_max: float = 0.8e-3, comp: str = "gyro",
                 acc: Optional[FS.AccelModel] = None, gyr: Optional[FS.GyroModel] = None, tick: float = 0.5e-3,
                 n_ticks: Optional[int] = None) -> FS.Streams:
    rng = np.random.default_rng(seed)
    t, fs, f_body, w_body, R = imu_kinematics(res)
    sos_aa = FS.aa_sos(fs)
    f_b = sosfilt(sos_aa, f_body, axis=0)
    w_b = sosfilt(sos_aa, w_body, axis=0)
    acc_m = acc or FS.AccelModel()
    gyr_m = gyr or FS.GyroModel()
    t_end = float(t[-1])
    t_a = np.arange(rng.uniform(0, 1.0 / acc_m.odr), t_end, 1.0 / acc_m.odr)
    fb = FS._accel_readings(f_b, t, t_a, acc_m, rng)
    wb = FS._gyro_readings(w_b, t, t_a, gyr_m, acc_m.odr, rng)
    R0 = R[0] if len(R) else np.eye(3)
    # nominal mounting (the firmware knows the design attitude, not the instantaneous one)
    a_ax = R0[:, 2]
    dta = 1.0 / acc_m.odr
    fp = fb @ R0.T
    if comp == "gyro":
        wp = wb @ R0.T
        Omh = FS._leaky_integrate(wp, dta, 2.0)
        est = fp + G_VEC + np.cross(Omh, fp)
        alpha = np.vstack([np.zeros((1, 3)), np.diff(wp, axis=0) / dta])
        alpha = sosfilt(butter(2, 300.0, fs=acc_m.odr, output="sos"), alpha, axis=0)
        est = est - z_imu * np.cross(alpha, a_ax)
    else:
        est = fp + G_VEC
    t_p = np.arange(rng.uniform(0, 1.0 / page_rate), t_end, 1.0 / page_rate)
    pos = np.column_stack([np.interp(t_p, t, res["tipx"]), np.interp(t_p, t, res["tipy"])])
    pos = pos + rng.standard_normal((len(t_p), 2)) * page_noise
    zc = res["tipz"]
    hz = np.interp(t_p, t, zc) - float(np.min(zc[len(zc) // 10:]))
    pos_ok = (hz < lift_max).astype(np.float64)
    t_c = np.arange(rng.uniform(0, 1e-3), t_end, 1e-3)
    con = (np.interp(t_c, t, res["contact"]) > 0.5).astype(np.float64)
    if n_ticks is None:
        n_ticks = int(math.ceil((t_end + 1.0 / fs) / tick - 1e-9))
    tick_t = np.arange(n_ticks) * tick
    return FS.Streams(tick_t=tick_t, acc_t=t_a, acc_av=t_a + acc_m.extra_latency, acc=np.ascontiguousarray(est[:, :2]),
                      pos_t=t_p, pos_av=t_p + page_latency, pos=np.ascontiguousarray(pos), pos_ok=pos_ok,
                      con_t=t_c, con_av=t_c + 1e-3, con=con, meta={"seed": seed, "z_imu": z_imu, "source": "sim2"})


def akf_estimate(res, seed: int, z_imu: float, params: Optional[Dict] = None, n_ticks: Optional[int] = None, **kw):
    """fusion AKF on sim2 streams: disturbance estimate per 2 kHz tick (n_ticks, 2) and the info dict."""
    st = make_streams(res, seed, z_imu, n_ticks=n_ticks, **kw)
    prm = dict(ship_params())
    if params:
        prm.update(params)
    dh, info = ES.akf(st, prm)
    return dh, info, st


_SHIP = None


def ship_params() -> Dict:
    global _SHIP
    if _SHIP is None:
        import json, os
        from . import ROOT
        _SHIP = json.load(open(os.path.join(ROOT, "results", "opt", "tracker_models", "akf_ship.json")))["params"]
    return dict(_SHIP)


def revh_params() -> Dict:
    import json, os
    from . import ROOT
    p = ship_params()
    f = os.path.join(ROOT, "results", "opt", "inertial_tracker_revh.json")
    if os.path.exists(f):
        p.update(json.load(open(f))["params"])
    return p


# ================================================================================================ online sensors
class OnlineSensors:
    """Causal per-tick pen sensors for control and RL (Gymnasium observations).  Called once per control tick with the
    current MjData; returns a dict of noisy readings.  IMU: block average of the specific force and rate over the tick
    (FIFO), white noise at the LSM6DSV16X densities over the tick bandwidth, fixed bias per episode; Hall: nose tip
    deflection with tip-referred noise; page sensor: tip-point displacement delayed by the latency, at its own rate
    (held between samples), valid flag; writing force: skid + ball normal force with load-cell noise; slide: refill
    slide with Hall noise."""

    def __init__(self, pm, Ts: float, seed: int = 0, noise_scale: float = 1.0):
        self.pm = pm
        self.Ts = Ts
        self.rng = np.random.default_rng(seed)
        s = pm.cfg.sensors
        acc = FS.AccelModel()
        gyr = FS.GyroModel()
        self.sa = noise_scale * acc.nd * math.sqrt(0.5 / Ts)
        self.sg = noise_scale * gyr.nd * math.sqrt(0.5 / Ts)
        self.ba = self.rng.normal(0.0, acc.bias_sd, 3) * noise_scale
        self.bg = self.rng.normal(0.0, gyr.bias_sd, 3) * noise_scale
        self.sh = noise_scale * s.hall_noise
        self.sp = noise_scale * s.page_noise
        self.sf = noise_scale * s.force_noise
        self.ss = noise_scale * s.slide_noise
        self.page_every = max(int(round(1.0 / (s.page_rate * Ts))), 1)
        self.page_latency = s.page_latency
        self.force_every = max(int(round(1.0 / (s.force_rate * Ts))), 1)
        self.slide_every = max(int(round(1.0 / (s.slide_rate * Ts))), 1)
        self.force_latency = s.force_latency
        self.slide_latency = s.slide_latency
        self.pbuf = deque()
        self.fbuf = deque()
        self.sbuf = deque()
        self.k = 0
        self.last_page = np.zeros(2)
        self.last_valid = False
        self.last_force = 0.0
        self.last_slide = 0.0
        self.v_prev = None
        m = pm.m
        self.s_imu = pm.ids["site:imu"]
        self.s_tip = pm.ids["site:tip"]
        from . import builder as B
        self.sl_v = B.sensor_slice(pm, "imu_linvel")
        self.sl_w = B.sensor_slice(pm, "imu_angvel")
        self.jq1 = pm.jnt_qadr("nose_1") if pm.has("jnt:nose_1") else None
        self.jq2 = pm.jnt_qadr("nose_2") if pm.has("jnt:nose_2") else None
        self.js = pm.jnt_qadr("refill_s")
        self.zp = pm.cfg.geom.z_p
        self.origin = None

    def reset(self):
        self.pbuf.clear()
        self.fbuf.clear()
        self.sbuf.clear()
        self.last_page[:] = 0.0
        self.last_valid = False
        self.last_force = 0.0
        self.last_slide = -1e-3  # unavailable -> no contact, not a false touchdown
        self.k = 0
        self.v_prev = None
        self.origin = None

    def read(self, forces: Dict[str, float]) -> Dict[str, np.ndarray]:
        d = self.pm.d
        R = d.site_xmat[self.s_imu].reshape(3, 3)
        v = d.sensordata[self.sl_v].copy()
        w = d.sensordata[self.sl_w].copy()
        a = np.zeros(3) if self.v_prev is None else (v - self.v_prev) / self.Ts
        self.v_prev = v
        f = R.T @ (a - G_VEC) + self.ba + self.rng.standard_normal(3) * self.sa
        g = R.T @ w + self.bg + self.rng.standard_normal(3) * self.sg
        tip = d.site_xpos[self.s_tip]
        if self.origin is None:
            self.origin = tip[:2].copy()
        t = self.k * self.Ts
        if self.k % self.page_every == 0:
            valid = bool(tip[2] < self.pm.cfg.sensors.page_lift_max)
            pos = tip[:2] - self.origin + self.rng.standard_normal(2) * self.sp
            self.pbuf.append((t + self.page_latency, pos.copy(), valid))
        while self.pbuf and self.pbuf[0][0] <= t + 1e-12:
            _, pos, valid = self.pbuf.popleft()
            self.last_valid = valid
            if valid:
                self.last_page = pos
        hall = np.zeros(2)
        if self.jq1 is not None:
            hall = np.array([-self.zp * d.qpos[self.jq1], self.zp * d.qpos[self.jq2]]) + self.rng.standard_normal(2) * self.sh
        if self.k % self.force_every == 0:
            N = forces.get("Ns", 0.0) + forces.get("Nb", 0.0) + self.rng.standard_normal() * self.sf
            self.fbuf.append((t + self.force_latency, N))
        if self.k % self.slide_every == 0:
            s = d.qpos[self.js] + self.rng.standard_normal() * self.ss
            self.sbuf.append((t + self.slide_latency, s))
        while self.fbuf and self.fbuf[0][0] <= t + 1e-12:
            self.last_force = self.fbuf.popleft()[1]
        while self.sbuf and self.sbuf[0][0] <= t + 1e-12:
            self.last_slide = self.sbuf.popleft()[1]
        self.k += 1
        return {"acc": f, "gyro": g, "hall": hall, "page": self.last_page.copy(),
                "page_valid": np.array([float(self.last_valid)]),
                "force": np.array([self.last_force]), "slide": np.array([self.last_slide])}
