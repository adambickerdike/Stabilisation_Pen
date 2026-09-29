r"""The pen's own sensors, online, one 2 kHz firmware tick at a time (SIMULATION models; values MFR or ASSUMPTION).

  IMU          LSM6DSV16X class (MFR OPT-37 via fusion.sensors): specific force and body rate of the IMU site from
               MuJoCo's kinematics, block-averaged over the tick (Delta v / Ts: a 2 kHz output data rate with a
               moving-average anti-alias filter), white noise at the part's densities over the 1 kHz Nyquist band,
               a constant bias per episode (fusion's calibrated bias SD), then the firmware's compensation as
               sim2/sensors.make_streams ('gyro': leaky-integrated attitude removes the gravity leak; lever arm to the
               tip removed with the IMU's position r (alpha x r), alpha low-passed at 300 Hz).  Output: the page-frame acceleration of
               the handle tip (x, y), stamped at the block centre (group delay Ts/2) and available 0.35 ms later
               (fusion AccelModel.extra_latency).  sim2 runs the dynamics with gravity off (H1 convention); the IMU sees
               the physical gravity, as sim2's offline streams do.
  page sensor  optical flow at the handle tip: 1 kHz, 2 ms latency, 3 um rms, valid below 0.8 mm lift (sim2 Sensors;
               ASSUMPTION, EXP-S01/N07).
  refill slide Hall on the refill slide, 1 kHz, 2 um, 1 ms (sim2 Sensors): the ball's contact flag = slide beyond the
               front stop by 0.1 mm.
  wheel        load (pod flexure Hall, 10 mN rms), lateral force across the heading (5 mN rms), heading (fork Hall,
               exact), rolling speed (odometry) (drive/plant.py sensing noise; ASSUMPTION).
The firmware only reads these values (REQ-SIM-004: nothing privileged).
"""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, Optional

import numpy as np

from . import ROOT  # noqa: F401
from fusion import sensors as FS  # noqa: E402
from sim2 import builder as B  # noqa: E402

G_VEC = np.array([0.0, 0.0, -FS.G0])


class OnlineSensors:
    def __init__(self, pm, Ts: float = 0.5e-3, seed: int = 0, noise_scale: float = 1.0, page_latency: Optional[float] = None):
        self.pm = pm
        self.Ts = Ts
        self.rng = np.random.default_rng(seed)
        cfg = pm.cfg
        s = cfg.sensors
        acc, gyr = FS.AccelModel(), FS.GyroModel()
        nyq = 0.5 / Ts
        self.sa = noise_scale * acc.nd * math.sqrt(nyq)
        self.sg = noise_scale * gyr.nd * math.sqrt(nyq)
        self.ba = self.rng.normal(0.0, acc.bias_sd, 3) * noise_scale
        self.bg = self.rng.normal(0.0, gyr.bias_sd, 3) * noise_scale
        self.acc_latency = acc.extra_latency
        self.s_imu = pm.ids["site:imu"]
        self.s_tip = pm.ids["site:tip"]
        self.sl_v = B.sensor_slice(pm, "imu_linvel")
        self.sl_w = B.sensor_slice(pm, "imu_angvel")
        self.z_imu = cfg.geom.z_imu
        self.r_imu = cfg.geom.r_imu
        self.r_p = None
        self.page_every = max(int(round(1.0 / (s.page_rate * Ts))), 1)
        self.page_latency = s.page_latency if page_latency is None else page_latency
        self.page_noise = s.page_noise * noise_scale
        self.lift_max = s.page_lift_max
        self.slide_noise = s.slide_noise * noise_scale
        self.js = pm.jnt_qadr("refill_s")
        self.j_refill = pm.ids["jnt:refill_s"]
        # firmware compensation state
        self.R0 = None
        self.a_ax = None
        self.Omh = np.zeros(3)
        self.lam = math.exp(-Ts / 2.0)
        self.w_prev = None
        from scipy.signal import butter
        self.sos_alpha = butter(2, 300.0, fs=1.0 / Ts, output="sos")
        self.z_alpha = np.zeros((self.sos_alpha.shape[0], 2, 3))
        self.v_prev = None
        self.k = 0
        self.z_rest = None
        self._nb = np.zeros((0, 9))
        self._ni = 0
        self._sosc = [tuple(float(v) for v in row) for row in self.sos_alpha]

    def reset(self):
        self.R0 = None
        self.Omh[:] = 0.0
        self.w_prev = None
        self.z_alpha[:] = 0.0
        self.v_prev = None
        self.k = 0
        self.z_rest = None

    def _sos_step(self, x):
        y = x
        for i in range(self.sos_alpha.shape[0]):
            b0, b1, b2, a0, a1, a2 = self.sos_alpha[i]
            z = self.z_alpha[i]
            out = b0 * y + z[0]
            z[0] = b1 * y - a1 * out + z[1]
            z[1] = b2 * y - a2 * out
            y = out
        return y

    def _noise(self):
        if self._ni >= len(self._nb):
            self._nb = self.rng.standard_normal((4096, 9))
            self._ni = 0
        v = self._nb[self._ni]
        self._ni += 1
        return v

    def read(self, t: float) -> Dict:
        """Called once per firmware tick at time t (after the physics of the previous tick)."""
        d = self.pm.d
        R = d.site_xmat[self.s_imu]            # row-major 3x3
        v = d.sensordata[self.sl_v]
        w = d.sensordata[self.sl_w]
        nz = self._noise()
        if self.R0 is None:
            self.R0 = R.reshape(3, 3).copy()
            self.a_ax = self.R0[:, 2].copy()
            # the IMU's position from the tip in the page frame at rest (on the board: r_imu off the axis)
            self.r_p = self.R0[:, 2] * self.z_imu + self.R0[:, 0] * self.r_imu
            self.v_prev = v.copy()
        vp = self.v_prev
        iT = 1.0 / self.Ts
        ax = (v[0] - vp[0]) * iT; ay = (v[1] - vp[1]) * iT; az = (v[2] - vp[2]) * iT + 9.80665
        self.v_prev = v.copy()
        # body frame (R^T x) + bias + noise
        fb0 = R[0] * ax + R[3] * ay + R[6] * az + self.ba[0] + nz[0] * self.sa
        fb1 = R[1] * ax + R[4] * ay + R[7] * az + self.ba[1] + nz[1] * self.sa
        fb2 = R[2] * ax + R[5] * ay + R[8] * az + self.ba[2] + nz[2] * self.sa
        wb0 = R[0] * w[0] + R[3] * w[1] + R[6] * w[2] + self.bg[0] + nz[3] * self.sg
        wb1 = R[1] * w[0] + R[4] * w[1] + R[7] * w[2] + self.bg[1] + nz[4] * self.sg
        wb2 = R[2] * w[0] + R[5] * w[1] + R[8] * w[2] + self.bg[2] + nz[5] * self.sg
        R0 = self.R0
        fp0 = R0[0, 0] * fb0 + R0[0, 1] * fb1 + R0[0, 2] * fb2
        fp1 = R0[1, 0] * fb0 + R0[1, 1] * fb1 + R0[1, 2] * fb2
        fp2 = R0[2, 0] * fb0 + R0[2, 1] * fb1 + R0[2, 2] * fb2
        wp0 = R0[0, 0] * wb0 + R0[0, 1] * wb1 + R0[0, 2] * wb2
        wp1 = R0[1, 0] * wb0 + R0[1, 1] * wb1 + R0[1, 2] * wb2
        wp2 = R0[2, 0] * wb0 + R0[2, 1] * wb1 + R0[2, 2] * wb2
        O = self.Omh
        lam, Ts = self.lam, self.Ts
        O[0] = lam * O[0] + Ts * wp0; O[1] = lam * O[1] + Ts * wp1; O[2] = lam * O[2] + Ts * wp2
        # est = fp + g + Omh x fp  (gravity leak removed)
        e0 = fp0 + (O[1] * fp2 - O[2] * fp1)
        e1 = fp1 + (O[2] * fp0 - O[0] * fp2)
        if self.w_prev is None:
            al = (0.0, 0.0, 0.0)
        else:
            wq = self.w_prev
            al = ((wp0 - wq[0]) * iT, (wp1 - wq[1]) * iT, (wp2 - wq[2]) * iT)
        self.w_prev = (wp0, wp1, wp2)
        a0, a1, a2 = self._sos_step3(al)
        rp = self.r_p
        # lever arm to the tip: est -= alpha x r (r = the IMU's position from the tip, incl. its radial offset)
        e0 -= (a1 * rp[2] - a2 * rp[1])
        e1 -= (a2 * rp[0] - a0 * rp[2])
        out = {"acc": (e0, e1), "acc_t": t - 0.5 * self.Ts, "acc_av": t + self.acc_latency, "gyro": (wb0, wb1, wb2)}
        tip = d.site_xpos[self.s_tip]
        if self.z_rest is None:
            self.z_rest = float(tip[2])
        if self.k % self.page_every == 0:
            ok = (tip[2] - self.z_rest) < self.lift_max
            out["page"] = (t, t + self.page_latency, (tip[0] + nz[6] * self.page_noise, tip[1] + nz[7] * self.page_noise),
                           bool(ok))
        s = d.qpos[self.js] + nz[8] * self.slide_noise
        out["slide"] = float(s)
        out["contact"] = bool(s > self.pm.m.jnt_range[self.j_refill, 0] + 0.1e-3)
        self.k += 1
        return out

    def _sos_step3(self, x):
        out = []
        for c in range(3):
            y = x[c]
            for i in range(self.sos_alpha.shape[0]):
                b0, b1, b2, a0, a1, a2 = self._sosc[i]
                z = self.z_alpha[i, :, c]
                o = b0 * y + z[0]
                z[0] = b1 * y - a1 * o + z[1]
                z[1] = b2 * y - a2 * o
                y = o
            out.append(y)
        return out


class DelayLine:
    """A fixed-latency queue of samples (t_av, value): pop() returns every value available by t."""

    def __init__(self):
        self.q = deque()

    def push(self, t_av, val):
        self.q.append((t_av, val))

    def pop(self, t):
        out = []
        while self.q and self.q[0][0] <= t:
            out.append(self.q.popleft()[1])
        return out
