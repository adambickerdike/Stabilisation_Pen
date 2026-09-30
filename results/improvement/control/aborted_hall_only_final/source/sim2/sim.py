r"""Time-domain simulation of a PenModel: hand drive, push force, paper contact law, nose servo, plug-ins, recording.

One simulation step = mj_step1 (kinematics and velocities at time t) -> hand references, contact forces of the H1 law,
controller ticks -> mj_step2 (forces, constraint solve, integration).  Controllers therefore see the state at t.

Rates (defaults): simulation 40 kHz (dt 25 us, as P1/H1); nose servo 10 kHz; nose reference and tracker 2 kHz; record
4 kHz.  The nose servo has two modes:
  'ref_model'  H1-equivalent: the 2 kHz reference (soft limit, slew limit, contact-gated authority, as H1's stage) passes
               through H1's second-order follower (80 Hz, zeta 0.7, integrated every step); an inverse-dynamics + PD +
               integral inner loop (400 Hz) makes the gimbal follow it; coil currents are limited by the driver and the
               supply headroom (back-EMF) and filtered by the coil's L/R;
  'pid'        a PID position loop on the (noisy, delayed) Hall reading at the servo bandwidth (the firmware sketch).
Nose command sources: 'neutral' (held centred), 'oracle' (cancels the true deviation of the handle tip from the clean
run, H1 stage_src 0), 'external' (a disturbance estimate per 2 kHz tick, e.g. the AKF: H1 stage_src 1), 'policy' (a
callable returning the tip reference or coil currents).  Every output is a SIMULATION result.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import mujoco
import numpy as np

from . import builder as B
from . import params as P
from .hall_velocity import HallVelocity

REC = ["t", "tipx", "tipy", "tipz", "ballx", "bally", "ballz", "ax", "ay", "az", "b1", "b2",
       "handx", "handy", "handz", "q1", "q2", "qd1", "qd2", "qr1", "qr2", "sat", "geff", "s",
       "Ns", "Nb", "fsx", "fsy", "fbx", "fby", "contact",
       "imux", "imuy", "imuz", "imuvx", "imuvy", "imuvz", "imuwx", "imuwy", "imuwz",
       "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22",
       "I1", "I2", "Ic1", "Ic2", "Pcu", "Tcoil", "grip_fx", "grip_fy", "grip_fz", "fpush", "psi",
       "Epot", "Ekin"]


class Result:
    """Recorded channels (record rate) with the accessors sim/handpen/evaluate.py expects (adapter)."""

    def __init__(self, rec: np.ndarray, names: List[str], info: Dict, cfg: P.Config, scn=None):
        self.rec = rec
        self.names = names
        self.idx = {n: i for i, n in enumerate(names)}
        self.info = info
        self.cfg = cfg
        self.scn = scn

    def __getitem__(self, name):
        if name in self.idx:
            return self.rec[:, self.idx[name]]
        alias = {"bx": "tipx", "by": "tipy", "bz": "tipz", "ix": "ballx", "iy": "bally", "fnx": "fbx", "fny": "fby",
                 "Nn": "Nb"}
        if name in alias:
            return self.rec[:, self.idx[alias[name]]]
        return np.zeros(len(self.rec))            # channels H1 has and this model does not (devices)

    def xy(self, base):
        if base == "q1":
            return self.rec[:, [self.idx["q1"], self.idx["q2"]]]
        i = self.idx[base]
        return self.rec[:, i:i + 2]

    def ink(self):
        return self.rec[:, [self.idx["ballx"], self.idx["bally"]]]

    def ball(self):
        """H1's 'ball' = the pen body's tip point: here the handle tip (nose centred)."""
        return self.rec[:, [self.idx["tipx"], self.idx["tipy"]]]

    def R_imu(self):
        return self.rec[:, self.idx["R00"]:self.idx["R22"] + 1].reshape(-1, 3, 3)


# ================================================================================================ H1 contact law
class H1Contact:
    """H1's paper contact (sim/handpen/core.py): penalty normal and LuGre friction normalised by N (sigma_1 = sigma_2 = 0,
    Stribeck; implicit bristle update) at the skid point (handle-fixed, H1's p_nom a + R t1) and at the ball (on the
    sliding refill: penalty normal k_ball, c_ball; H1 applied a constant force inside a 0.3 mm margin instead)."""

    def __init__(self, pm: B.PenModel):
        c = pm.cfg.contact
        self.pm = pm
        self.m, self.d = pm.m, pm.d
        self.dt = pm.m.opt.timestep
        self.sk = pm.ids["site:skid_pt"]
        self.bl = pm.ids["site:ball"]
        self.tip = pm.ids["site:tip"]
        self.bh = pm.ids["body:handle"]
        self.br = pm.ids["body:refill"]
        self.k_sk, self.c_sk = c.k_sk, c.c_sk
        self.k_b, self.c_b = c.k_ball, c.c_ball
        self.r_b = pm.cfg.geom.r_b
        self.mu_sk = max(c.mu_skid, 1e-6)
        self.mus_sk = self.mu_sk * c.ms_ratio
        self.mu_b = max(c.mu_ball, 1e-6)
        self.mus_b = self.mu_b * c.ms_ratio
        self.vs = c.v_s
        self.sg_sk = self.mus_sk / c.presliding if c.mu_skid > 0 else 0.0
        self.sg_b = self.mus_b / c.presliding if c.mu_ball > 0 else 0.0
        self.z_sk = [0.0, 0.0]
        self.z_b = [0.0, 0.0]
        self.buf = np.zeros(6)
        self.out = dict(Ns=0.0, Nb=0.0, fsx=0.0, fsy=0.0, fbx=0.0, fby=0.0)

    def _lugre(self, z, vx, vy, N, mu_k, mu_s, sg0):
        vn = math.hypot(vx, vy)
        gv = mu_k + (mu_s - mu_k) * math.exp(-(vn / self.vs) ** 2)
        den = 1.0 + self.dt * sg0 * vn / gv
        z[0] = (z[0] + self.dt * vx) / den
        z[1] = (z[1] + self.dt * vy) / den
        return -N * sg0 * z[0], -N * sg0 * z[1]

    def forces(self, fpush: float):
        m, d, buf = self.m, self.d, self.buf
        # ---- skid point (handle)
        ps = d.site_xpos[self.sk]
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_SITE, self.sk, buf, 0)
        vx, vy, vz = buf[3], buf[4], buf[5]
        Ns = 0.0
        if ps[2] < 0.0:
            Ns = self.k_sk * (-ps[2]) - self.c_sk * vz
            if Ns < 0.0:
                Ns = 0.0
        if Ns > 0.0:
            fsx, fsy = self._lugre(self.z_sk, vx, vy, Ns, self.mu_sk, self.mus_sk, self.sg_sk)
        else:
            self.z_sk[0] = self.z_sk[1] = 0.0
            fsx = fsy = 0.0
        # ---- ball (refill)
        pb = d.site_xpos[self.bl]
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_SITE, self.bl, buf, 0)
        bvx, bvy, bvz = buf[3], buf[4], buf[5]
        pen = self.r_b - pb[2]
        Nb = 0.0
        if pen > 0.0:
            Nb = self.k_b * pen - self.c_b * bvz
            if Nb < 0.0:
                Nb = 0.0
        if Nb > 0.0:
            fbx, fby = self._lugre(self.z_b, bvx, bvy, Nb, self.mu_b, self.mus_b, self.sg_b)
        else:
            self.z_b[0] = self.z_b[1] = 0.0
            fbx = fby = 0.0
        # ---- applied wrenches (about each body's centre of mass)
        pt = d.site_xpos[self.tip]
        ch = d.xipos[self.bh]
        cr = d.xipos[self.br]
        xh = d.xfrc_applied[self.bh]
        rx, ry, rz = ps[0] - ch[0], ps[1] - ch[1], ps[2] - ch[2]
        Fx, Fy, Fz = fsx, fsy, Ns
        tx = ry * Fz - rz * Fy
        ty = rz * Fx - rx * Fz
        tz = rx * Fy - ry * Fx
        # push force at the handle tip (H1: external force at the ball centre along -z)
        ux, uy, uz = pt[0] - ch[0], pt[1] - ch[1], pt[2] - ch[2]
        Pz = -fpush
        tx += uy * Pz
        ty += -ux * Pz
        xh[0] = Fx; xh[1] = Fy; xh[2] = Fz + Pz
        xh[3] = tx; xh[4] = ty; xh[5] = tz
        xr = d.xfrc_applied[self.br]
        rx, ry, rz = pb[0] - cr[0], pb[1] - cr[1], pb[2] - cr[2]
        xr[0] = fbx; xr[1] = fby; xr[2] = Nb
        xr[3] = ry * Nb - rz * fby
        xr[4] = rz * fbx - rx * Nb
        xr[5] = rx * fby - ry * fbx
        o = self.out
        o["Ns"] = Ns; o["Nb"] = Nb; o["fsx"] = fsx; o["fsy"] = fsy; o["fbx"] = fbx; o["fby"] = fby


def push_only(pm: B.PenModel, fpush: float):
    """Native contact: only the push force at the handle tip (H1 convention with gravity off)."""
    d = pm.d
    bh = pm.ids["body:handle"]
    pt = d.site_xpos[pm.ids["site:tip"]]
    ch = d.xipos[bh]
    ux, uy = pt[0] - ch[0], pt[1] - ch[1]
    xh = d.xfrc_applied[bh]
    xh[0] = 0.0; xh[1] = 0.0; xh[2] = -fpush
    xh[3] = uy * -fpush
    xh[4] = -ux * -fpush
    xh[5] = 0.0


def native_contact_forces(pm: B.PenModel) -> Dict[str, float]:
    """Normal and friction forces (world frame) on the ball and the skid ring from MuJoCo's contacts."""
    m, d = pm.m, pm.d
    ball = pm.ids["geom:ball"]
    skid = set(pm.info["skid_geoms"])
    f6 = np.zeros(6)
    out = dict(Ns=0.0, Nb=0.0, fsx=0.0, fsy=0.0, fbx=0.0, fby=0.0)
    for i in range(d.ncon):
        con = d.contact[i]
        g1, g2 = con.geom1, con.geom2
        if ball in (g1, g2):
            key = "b"
        elif g1 in skid or g2 in skid:
            key = "s"
        else:
            continue
        mujoco.mj_contactForce(m, d, i, f6)
        fr = con.frame.reshape(3, 3)
        fw = fr.T @ f6[:3]                        # force on geom2 from geom1, world frame
        if con.geom1 in (ball,) or con.geom1 in skid:
            fw = -fw                              # force on the pen geom
        out["N" + key] += fw[2]
        out["f" + key + "x"] += fw[0]
        out["f" + key + "y"] += fw[1]
    return out


# ================================================================================================ nose servo
class NoseServo:
    """Tip reference (2 kHz, H1 stage rules) -> second-order follower -> inner loop -> coil currents."""

    def __init__(self, pm: B.PenModel, source: str = "neutral", clean: Optional[np.ndarray] = None,
                 dhat: Optional[np.ndarray] = None, policy: Optional[Callable] = None, seed: int = 0):
        cfg = pm.cfg
        self.pm = pm
        self.nz = cfg.nose
        self.g = cfg.geom
        self.on = cfg.nose_on and pm.has("jnt:nose_1")
        self.source = source
        self.clean = clean
        self.dhat = dhat
        self.policy = policy
        th = self.g.theta_deg * P.D2R
        self.sth, self.cth = math.sin(th), math.cos(th)
        a, t1, t2, n, h = self.g.vectors()
        self.h = h
        self.t2 = t2
        self.dt = pm.m.opt.timestep
        nz = self.nz
        self.ws = 2 * math.pi * nz.servo_hz
        self.zs = nz.servo_zeta
        self.qlim = self.g.travel
        self.qtap = nz.q_taper
        self.slew = nz.slew
        self.Ts_ref = 1.0 / nz.ref_rate
        self.alpha_a = 1.0 - math.exp(-self.Ts_ref / max(nz.auth_tau, 1e-6))
        self.zp = self.g.z_p
        self.I = pm.info["nose_I_pivot"]
        self.kr = nz.k_r
        self.c_flex = pm.info["nose_c_flex"]
        self.gear = pm.info["K_f"] * pm.info["coil_arm"]
        wi = 2 * math.pi * nz.inner_hz
        self.Kp = self.I * wi * wi
        self.Kd = 2 * 0.8 * self.I * wi
        self.Ki = self.Kp * 2 * math.pi * 20.0
        if nz.servo_mode == "pid":
            wb = 2 * math.pi * nz.servo_hz
            self.Kp = self.I * wb * wb * 1.2
            self.Kd = 2 * nz.servo_zeta * self.I * wb
            self.Ki = self.Kp * 2 * math.pi * 10.0
        self.tau_bias = pm.info["tau_bias"] if nz.bias else 0.0
        self.adaptive_stop = cfg.refill.front_stop == "nose_adaptive"
        self.j_refill = pm.ids["jnt:refill_s"]
        self.margin = cfg.geom.front_stop_margin
        self.cot = pm.info["cot_theta"]
        if self.on:
            self.qa = [pm.jnt_qadr("nose_1"), pm.jnt_qadr("nose_2")]
            self.va = [pm.jnt_dadr("nose_1"), pm.jnt_dadr("nose_2")]
            self.act = [pm.ids["act:coil_1"], pm.ids["act:coil_2"]]
        from .plugins import Coil
        self.coils = [Coil(K_f=pm.info["K_f"], R20=nz.R, L=nz.L_ind, I_max=nz.I_max, V=nz.V_supply, alpha=nz.alpha_cu,
                           R_th=nz.R_th, C_th=nz.C_th, T_amb=nz.T_amb, T=nz.T_amb) for _ in range(2)]
        self.rng = np.random.default_rng(seed)
        self.qr = [0.0, 0.0]
        self.qd = [0.0, 0.0]
        self.qdv = [0.0, 0.0]
        self.qdd = [0.0, 0.0]
        self.ei = [0.0, 0.0]
        self.g_eff = 0.0
        self.sat = 0.0
        self.Icmd = [0.0, 0.0]
        self.P_cu = 0.0
        self.copper_energy_J = 0.0
        hd = max(int(round(nz.hall_delay * nz.servo_rate)), 0)
        self.hbuf = [[0.0] * (hd + 1), [0.0] * (hd + 1)]
        self.hk = 0
        if nz.velocity_source not in ("hall", "legacy_true"):
            raise ValueError("velocity_source must be 'hall' or 'legacy_true'")
        if not 0 < cfg.sensors.hall_rate <= nz.servo_rate:
            raise ValueError("Hall rate must be positive and no faster than the simulated servo")
        if nz.hall_delay < 0 or nz.hall_max_age <= 0:
            raise ValueError("Hall delay must be nonnegative and maximum age positive")
        self.hall_estimators = [HallVelocity(nz.velocity_cutoff_hz) for _ in range(2)]
        self.hall_queue = deque()
        self.hall_angles = [0.0, 0.0]
        self.hall_next_acquisition = 0.0
        self.hall_period = 1.0 / cfg.sensors.hall_rate
        self.servo_time = 0.0
        self.feedback_velocity = [0.0, 0.0]
        self.hall_feedback_valid = False
        self.hall_stale_ticks = 0
        self.hall_age_s = math.inf

    def _hall_feedback(self, now):
        """Acquire at the declared rate; deliver only after Hall latency.

        A held reading never becomes another derivative observation. Sampling
        times are the actual servo instants, so unsupported rates round late,
        without manufacturing intermediate samples from future states.
        """
        if now + 1e-12 >= self.hall_next_acquisition:
            angles = [float(self.pm.d.qpos[q]) for q in self.qa]
            if self.nz.hall_noise > 0:
                angles = [a + self.rng.standard_normal() * self.nz.hall_noise / self.zp for a in angles]
            self.hall_queue.append((now, now + self.nz.hall_delay, angles))
            while self.hall_next_acquisition <= now + 1e-12:
                self.hall_next_acquisition += self.hall_period
        while self.hall_queue and self.hall_queue[0][1] <= now + 1e-12:
            acquired, _, angles = self.hall_queue.popleft()
            self.hall_angles = angles
            for est, angle in zip(self.hall_estimators, angles):
                est.observe(acquired, angle)
        readings = [est.read(now, self.nz.hall_max_age) for est in self.hall_estimators]
        self.feedback_velocity = [r.value for r in readings]
        self.hall_age_s = max(r.age_s for r in readings)
        self.hall_feedback_valid = all(r.valid for r in readings)
        if not self.hall_feedback_valid:
            self.hall_stale_ticks += 1
        return self.hall_angles, self.feedback_velocity, self.hall_feedback_valid

    # -- 2 kHz reference (H1 stage rules)
    def ref_tick(self, t: float, tick: int, tip_xy, in_contact: bool, direct_q=None):
        self.g_eff += self.alpha_a * ((1.0 if in_contact else 0.0) - self.g_eff)
        if direct_q is not None:
            qn0, qn1 = float(direct_q[0]), float(direct_q[1])
        else:
            if self.source == "oracle":
                kc = min(tick, len(self.clean) - 1)
                ex = tip_xy[0] - self.clean[kc, 0]
                ey = tip_xy[1] - self.clean[kc, 1]
            elif self.source == "external":
                k = min(tick, len(self.dhat) - 1)
                ex, ey = self.dhat[k, 0], self.dhat[k, 1]
            else:
                ex = ey = 0.0
            eh = ex * self.h[0] + ey * self.h[1]
            e2 = ex * self.t2[0] + ey * self.t2[1]
            qn0 = -self.g_eff * self.sth * eh
            qn1 = -self.g_eff * e2
        rq = math.hypot(qn0, qn1)
        knee = self.qlim - self.qtap
        if rq > knee and rq > 0:
            rnew = knee + self.qtap * math.tanh((rq - knee) / self.qtap)
            qn0 *= rnew / rq
            qn1 *= rnew / rq
        self.sat = 1.0 if math.hypot(qn0, qn1) > 0.95 * self.qlim else 0.0
        dq0, dq1 = qn0 - self.qr[0], qn1 - self.qr[1]
        dmx = self.slew * self.Ts_ref
        dm = math.hypot(dq0, dq1)
        if dm > dmx:
            dq0 *= dmx / dm
            dq1 *= dmx / dm
        self.qr[0] += dq0
        self.qr[1] += dq1

    # -- the follower (as H1: integrated at dt), advanced n steps at a servo tick (the reference only changes at the
    #    2 kHz ticks, which coincide with servo ticks, so this equals integrating it every step)
    def follower_steps(self, nsub: int):
        ws, zs, dt = self.ws, self.zs, self.dt
        w2 = ws * ws
        c2 = 2.0 * zs * ws
        for i in (0, 1):
            qr, qd, qv = self.qr[i], self.qd[i], self.qdv[i]
            qdd = 0.0
            for _ in range(nsub):
                qdd = w2 * (qr - qd) - c2 * qv
                qv += qdd * dt
                qd += qv * dt
            self.qd[i], self.qdv[i], self.qdd[i] = qd, qv, qdd

    def follower_step(self):
        ws, zs, dt = self.ws, self.zs, self.dt
        for i in (0, 1):
            qdd = ws * ws * (self.qr[i] - self.qd[i]) - 2.0 * zs * ws * self.qdv[i]
            self.qdd[i] = qdd
            self.qdv[i] += qdd * dt
            self.qd[i] += self.qdv[i] * dt

    # -- inner loop (servo rate)
    def servo_tick(self, Ts: float, contact_gate: float):
        if not self.on:
            return
        d = self.pm.d
        zp = self.zp
        if self.nz.velocity_source == "hall":
            hall_angles, hall_velocities, hall_valid = self._hall_feedback(self.servo_time)
        # tip deflection q along (t1, t2) <-> gimbal angles: q1 = -z_p a1, q2 = +z_p a2
        for i in (0, 1):
            sgn = -1.0 if i == 0 else 1.0
            if self.nz.velocity_source == "legacy_true":
                # Preserved solely to reproduce historical optimistic studies.
                a_meas = d.qpos[self.qa[i]]
                if self.nz.hall_noise > 0:
                    a_meas += self.rng.standard_normal() * self.nz.hall_noise / zp
                buf = self.hbuf[i]
                buf[self.hk % len(buf)] = a_meas
                a_hall = buf[(self.hk + 1) % len(buf)] if len(buf) > 1 else a_meas
                v = d.qvel[self.va[i]]
                self.feedback_velocity[i] = float(v)
            else:
                a_hall, v = hall_angles[i], hall_velocities[i]
                if not hall_valid:
                    # Hold the integrator; current then decays through modeled
                    # coil dynamics. This is a fail-closed command, not a claim
                    # that the moving nib stops instantaneously or safely.
                    self.Icmd[i] = 0.0
                    d.ctrl[self.act[i]] = 0.0
                    continue
            ad = sgn * self.qd[i] / zp
            avd = sgn * self.qdv[i] / zp
            aad = sgn * self.qdd[i] / zp
            e = ad - a_hall
            self.ei[i] += e * Ts
            tau = (self.I * aad + self.kr * ad + self.c_flex * avd + self.Kp * e + self.Kd * (avd - v)
                   + self.Ki * self.ei[i])
            if i == 0:
                tau += -self.tau_bias * contact_gate
            I_cmd = tau / self.gear
            # Physical back-EMF depends on actual magnet velocity. This plant
            # law may use qvel; the causal feedback controller above may not.
            vm = d.qvel[self.va[i]] * self.pm.info["coil_arm"]
            I_lim = self.coils[i].limit(I_cmd, vm)
            if I_lim != I_cmd and self.Ki > 0:
                self.ei[i] -= e * Ts                 # anti-windup
            self.Icmd[i] = I_lim
            d.ctrl[self.act[i]] = I_lim
        self.hk += 1
        self.servo_time += Ts
        if self.adaptive_stop:
            # front stop that follows the nose: the ball may protrude at most `margin` beyond its contact position
            q1 = -zp * d.qpos[self.qa[0]]
            self.pm.m.jnt_range[self.j_refill, 0] = q1 * self.cot - self.margin
        # copper loss and coil temperature with the actual (filtered) currents
        P = 0.0
        for i in (0, 1):
            Ia = d.act[self.pm.m.actuator_actadr[self.act[i]]] if self.pm.m.actuator_actadr[self.act[i]] >= 0 else self.Icmd[i]
            P += self.coils[i].step_thermal(float(Ia), Ts)
        self.P_cu = P
        self.copper_energy_J += P * Ts


# ================================================================================================ simulation
@dataclass
class RunOptions:
    source: str = "neutral"
    clean: Optional[np.ndarray] = None          # (n_ticks, 2) clean handle-tip path at the 2 kHz ticks (oracle)
    dhat: Optional[np.ndarray] = None           # (n_ticks, 2) disturbance estimate per tick (external)
    policy: Optional[Callable] = None
    plugin_cmd: Optional[Callable] = None       # f(t, obs) -> list of command arrays per plug-in
    record: bool = True
    energy: bool = False
    t_end: Optional[float] = None
    seed: int = 0
    contact_from: str = "force"                 # contact gate: 'force' (true ball force > 0, H1) or 'slide' (sensor)


def _scn_arrays(scn, dt_sim: float):
    """Scenario arrays (H1 convention at 25 us) resampled to the simulation step if it differs."""
    t = np.asarray(scn.t)
    dt0 = float(t[1] - t[0])
    pref, vref, fpush = np.asarray(scn.pref), np.asarray(scn.vref), np.asarray(scn.fpush)
    psi = np.asarray(getattr(scn, "psi_disp", np.zeros(len(t))))
    if abs(dt0 - dt_sim) < 1e-12:
        return t, pref, vref, fpush, psi
    tn = np.arange(0.0, t[-1] + 0.5 * dt_sim, dt_sim)
    it = lambda X: np.column_stack([np.interp(tn, t, X[:, j]) for j in range(X.shape[1])]) if X.ndim == 2 else np.interp(tn, t, X)
    return tn, it(pref), it(vref), it(fpush), it(psi)


class Stepper:
    """One simulation run, advanced step by step (run() and the Gymnasium environment both use it).

    Per step: mj_step1 -> hand drive (H1 reference path with inertial feedforward, or the arm's writer controller) ->
    paper contact law (or the push force alone with native contacts) -> nose reference at 2 kHz (source: oracle,
    external estimate, a policy callable, or a direct command set by the environment) -> H1's follower every step ->
    inner servo at the servo rate -> record -> mj_step2."""

    def __init__(self, pm: B.PenModel, scn, opt: Optional[RunOptions] = None, arm_tremor=None, **kw):
        self.opt = opt or RunOptions(**kw)
        opt = self.opt
        self.pm = pm
        cfg = pm.cfg
        self.cfg = cfg
        m, d = pm.m, pm.d
        self.m, self.d = m, d
        B.reset(pm)
        dt = m.opt.timestep
        self.dt = dt
        t_arr, pref, vref, fpush, psi_disp = _scn_arrays(scn, dt)
        self.scn = scn
        n = len(t_arr)
        if opt.t_end is not None:
            n = min(n, int(round(opt.t_end / dt)))
        self.n = n
        self.fpush = fpush
        nz = cfg.nose
        self.sdec = max(int(round(1.0 / (nz.servo_rate * dt))), 1)
        self.rdec = max(int(round(1.0 / (nz.ref_rate * dt))), 1)
        self.recdec = max(int(round(1.0 / (cfg.record_hz * dt))), 1)
        self.servo = NoseServo(pm, opt.source, opt.clean, opt.dhat, opt.policy, seed=opt.seed)
        from .contact import ContactLaw
        self.law = ContactLaw(pm) if cfg.contact.model == "h1" else None
        if opt.energy:
            m.opt.enableflags |= int(mujoco.mjtEnableBit.mjENBL_ENERGY)
        self.hand = cfg.hand_model == "h1"
        self.rot = False
        self.psi = np.zeros(n)
        if self.hand:
            ap = [pm.ids["act:arm_p_x"], pm.ids["act:arm_p_y"], pm.ids["act:arm_p_z"]]
            av = [pm.ids["act:arm_v_x"], pm.ids["act:arm_v_y"], pm.ids["act:arm_v_z"]]
            af = [pm.ids["act:arm_f_x"], pm.ids["act:arm_f_y"], pm.ids["act:arm_f_z"]]
            aref = np.gradient(vref, dt, axis=0) * cfg.hand.M
            self.hidx = np.array(ap + av + af, dtype=np.int64)
            self.hctl = np.ascontiguousarray(np.column_stack([pref, vref, aref]))
            tremor = getattr(scn, "tremor_obj", None)
            lever, P_piv, axis = rotation_geometry(pm, tremor)
            self.psi = psi_disp / lever
            self.psid = np.gradient(self.psi, dt)
            self.rot = pm.has("jnt:hand_psi")
            if self.rot:
                self.a_psi = (pm.ids["act:psi_p"], pm.ids["act:psi_v"])
                jpsi = pm.ids["jnt:hand_psi"]
                m.jnt_axis[jpsi] = axis
                m.jnt_pos[jpsi] = P_piv
            elif np.any(self.psi != 0.0):
                raise ValueError("the scenario has a wrist-rotation tremor: build with HandH1(rot_tremor=True)")
        else:
            from . import hand as HD
            self.arm = HD.ArmDrive(pm, scn, dt, tremor=arm_tremor)
        ids = pm.ids
        self.s_tip, self.s_ball, self.s_imu = ids["site:tip"], ids["site:ball"], ids["site:imu"]
        self.b_handle = ids["body:handle"]
        self.b_hand = ids.get("body:hand", ids.get("body:palm"))
        self.js = pm.jnt_qadr("refill_s")
        self.sl_vimu = B.sensor_slice(pm, "imu_linvel")
        self.sl_wimu = B.sensor_slice(pm, "imu_angvel")
        self.gq = [pm.jnt_dadr(nm) for nm in ("grip_t1", "grip_t2", "grip_a")]
        self.gb = [pm.jnt_qadr(nm) for nm in ("grip_b1", "grip_b2")]
        plug_ch = []
        for pl in pm.plugins:
            plug_ch += pl.record_channels()
        self.names = REC + plug_ch
        self.nrec = n // self.recdec + 2
        self.rec = np.zeros((self.nrec, len(self.names))) if opt.record else None
        self.ri = 0
        self.cont = {"Ns": 0.0, "Nb": 0.0, "fsx": 0.0, "fsy": 0.0, "fbx": 0.0, "fby": 0.0}
        self.tick = 0
        self.gate = 0.0
        # contact flag: ball normal force above a threshold (H1: > 0; native soft contacts carry solver noise of mN)
        self.n_thr = 0.0 if self.law is not None else 0.02
        # native soft contacts flicker (the equilibrium penetration is nanometres and the solver force of a resting
        # contact dithers): the contact flag is then the ball force low-passed (2 ms) with hysteresis (on 0.05 N,
        # off 0.01 N), as a slide sensor would report it; the H1 law keeps the raw flag (force > 0)
        self.nb_f = 0.0
        self.c_state = False
        self.k = 0
        self.direct_q = None                    # set by an environment: tip reference (t1, t2) for the next ticks
        self.plugin_cmds = None                 # set by an environment: list of command arrays per plug-in

    def in_contact(self) -> bool:
        if self.law is None:
            return self.c_state
        return self.cont["Nb"] > self.n_thr

    def _update_flag(self):
        if self.law is not None:
            return self.cont["Nb"] > self.n_thr
        a = min(1.0, (self.rdec * self.dt) / 2e-3)
        self.nb_f += a * (self.cont["Nb"] - self.nb_f)
        if self.c_state and self.nb_f < 0.01:
            self.c_state = False
        elif not self.c_state and self.nb_f > 0.05:
            self.c_state = True
        return self.c_state

    def step(self):
        k = self.k
        m, d, pm, opt, servo = self.m, self.d, self.pm, self.opt, self.servo
        dt = self.dt
        mujoco.mj_step1(m, d)
        if self.hand:
            d.ctrl[self.hidx] = self.hctl[k]
            if self.rot:
                d.ctrl[self.a_psi[0]] = self.psi[k]
                d.ctrl[self.a_psi[1]] = self.psid[k]
        else:
            self.arm.step(k)
        if self.law is not None:
            self.law.forces(self.fpush[k] if self.hand else 0.0)
        elif self.hand:
            push_only(pm, self.fpush[k])
        if k % self.rdec == 0:
            if self.law is None:
                self.cont = native_contact_forces(pm)
            else:
                self.cont = self.law.summary()
            in_c = self._update_flag()
            tip = d.site_xpos[self.s_tip]
            direct = self.direct_q
            if opt.policy is not None:
                direct = opt.policy(k * dt, pm, servo)
            servo.ref_tick(k * dt, self.tick, tip, in_c, direct_q=direct)
            self.gate = servo.g_eff
            cmds = self.plugin_cmds
            if opt.plugin_cmd is not None:
                cmds = opt.plugin_cmd(k * dt, pm)
            if cmds is not None:
                for pl, c_ in zip(pm.plugins, cmds):
                    pl.apply(pm, k * dt, c_)
            self.tick += 1
        if k % self.sdec == 0:
            # the servo uses the follower state at step k, then the follower advances to the next servo tick (H1:
            # q follows qr integrated every step; identical because qr only changes at ticks that are servo ticks)
            servo.servo_tick(self.sdec * dt, self.gate)
            servo.follower_steps(self.sdec)
        if self.rec is not None and k % self.recdec == 0 and self.ri < self.nrec:
            if self.law is not None:
                self.cont = self.law.summary()
            self._record(k)
        mujoco.mj_step2(m, d)
        if not np.isfinite(d.qacc[0]):
            raise FloatingPointError(f"simulation diverged at t = {k * dt:.4f} s")
        self.k += 1

    def advance(self, nsteps: int):
        for _ in range(min(nsteps, self.n - self.k)):
            self.step()

    def done(self) -> bool:
        return self.k >= self.n

    def _record(self, k):
        d, m, servo, pm = self.d, self.m, self.servo, self.pm
        r = self.rec[self.ri]
        cont = self.cont
        r[0] = k * self.dt
        pt = d.site_xpos[self.s_tip]; r[1] = pt[0]; r[2] = pt[1]; r[3] = pt[2]
        pb = d.site_xpos[self.s_ball]; r[4] = pb[0]; r[5] = pb[1]; r[6] = pb[2]
        Rh = d.xmat[self.b_handle]
        r[7] = Rh[2]; r[8] = Rh[5]; r[9] = Rh[8]
        r[10] = d.qpos[self.gb[0]]; r[11] = d.qpos[self.gb[1]]
        r[12:15] = d.xpos[self.b_hand] if self.b_hand is not None else 0.0
        if servo.on:
            r[15] = -pm.cfg.geom.z_p * d.qpos[servo.qa[0]]
            r[16] = pm.cfg.geom.z_p * d.qpos[servo.qa[1]]
        r[17] = servo.qd[0]; r[18] = servo.qd[1]; r[19] = servo.qr[0]; r[20] = servo.qr[1]
        r[21] = servo.sat; r[22] = servo.g_eff; r[23] = d.qpos[self.js]
        r[24] = cont["Ns"]; r[25] = cont["Nb"]; r[26] = cont["fsx"]; r[27] = cont["fsy"]
        r[28] = cont["fbx"]; r[29] = cont["fby"]
        r[30] = (1.0 if cont["Nb"] > self.n_thr else 0.0) if self.law is not None else (1.0 if self.c_state else 0.0)
        pi_ = d.site_xpos[self.s_imu]; r[31] = pi_[0]; r[32] = pi_[1]; r[33] = pi_[2]
        r[34:37] = d.sensordata[self.sl_vimu]
        r[37:40] = d.sensordata[self.sl_wimu]
        r[40:49] = d.site_xmat[self.s_imu]
        if servo.on:
            r[49] = d.act[m.actuator_actadr[servo.act[0]]]; r[50] = d.act[m.actuator_actadr[servo.act[1]]]
            r[51] = servo.Icmd[0]; r[52] = servo.Icmd[1]
        r[53] = servo.P_cu; r[54] = servo.coils[0].T
        r[55] = -d.qfrc_passive[self.gq[0]]; r[56] = -d.qfrc_passive[self.gq[1]]; r[57] = -d.qfrc_passive[self.gq[2]]
        r[58] = self.fpush[k] if self.hand else 0.0
        r[59] = self.psi[k] if self.hand else 0.0
        if self.opt.energy:
            r[60] = d.energy[0]; r[61] = d.energy[1]
        j = len(REC)
        for pl in pm.plugins:
            vals = pl.record(pm)
            r[j:j + len(vals)] = vals
            j += len(vals)
        self.ri += 1

    def result(self) -> Result:
        if self.opt.energy:
            self.m.opt.enableflags &= ~int(mujoco.mjtEnableBit.mjENBL_ENERGY)
        rec = self.rec[:self.ri] if self.rec is not None else np.zeros((0, len(self.names)))
        info = dict(self.pm.info)
        info["servo_feedback"] = {
            "version": "hall-causal-v1-2026-09-30" if self.cfg.nose.velocity_source == "hall" else "legacy-true-velocity-bound",
            "velocity_source": self.cfg.nose.velocity_source,
            "cutoff_hz": self.cfg.nose.velocity_cutoff_hz,
            "inner_hz": self.cfg.nose.inner_hz,
            "hall_rate_hz": self.cfg.sensors.hall_rate,
            "hall_noise_tip_m": self.cfg.nose.hall_noise,
            "hall_delay_s": self.cfg.nose.hall_delay,
            "hall_max_age_s": self.cfg.nose.hall_max_age,
            "stale_or_warmup_ticks": self.servo.hall_stale_ticks,
            "copper_energy_J": self.servo.copper_energy_J,
        }
        return Result(rec, self.names, info, self.cfg, self.scn)


def run(pm: B.PenModel, scn, opt: Optional[RunOptions] = None, arm_tremor=None, **kw) -> Result:
    st = Stepper(pm, scn, opt, arm_tremor=arm_tremor, **kw)
    st.advance(st.n)
    return st.result()


def rotation_geometry(pm: B.PenModel, tremor):
    """Axis, pivot (hand frame) and lever of H1's imposed wrist rotation (sim/handpen/model.rotation_geometry)."""
    cfg = pm.cfg
    a, t1, t2, n, h = cfg.geom.vectors()
    zc = pm.info["grip"]["z_c"]
    th = cfg.geom.theta_deg * P.D2R
    if tremor is None or getattr(tremor, "amp_rot", 0.0) <= 0:
        return 1.0, np.array([0.2, 0.0, 0.0]), n
    if tremor.axis == "yaw":
        Ppiv = (zc * math.cos(th) + tremor.L_p) * h
        lever = zc * math.cos(th) + tremor.L_p
        axis = n
    else:
        Ppiv = (zc * math.cos(th) + tremor.L_p) * h + tremor.pivot_height * n
        lever = math.hypot(zc * math.cos(th) + tremor.L_p, tremor.pivot_height)
        axis = t2
    return lever, Ppiv, axis


def clean_ticks(ref: Result, n_ticks: int, Ts: float = 0.5e-3) -> np.ndarray:
    """Clean handle-tip path of a reference run at the 2 kHz ticks (oracle reference, H1 convention)."""
    tt = np.arange(n_ticks) * Ts
    b = ref.ball()
    return np.column_stack([np.interp(tt, ref["t"], b[:, 0]), np.interp(tt, ref["t"], b[:, 1])])
