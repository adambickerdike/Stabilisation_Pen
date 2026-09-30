r"""sim2j's Rev J stepper with the whole-pen devices and their controllers in the loop (SIMULATION).

Per physics step (sim2j.stepper.RevJStepper order): mj_step1 -> hand drive -> sim2's H1 contact law -> heel wheel ->
[insertion W1: the collar carries the writing push (moved from the pen tip to the collar's pivot); the sled's force on
the hand and the omni heel's force on the pen tip, each capped at mu N] -> 2 kHz tick: sim2j's firmware (tracker, nose,
wheel, end-cap, pen lift) then this study's device laws (control.py) -> nose servo -> pen lift -> record -> mj_step2.
sim2j's files are unchanged: the step is a copy of RevJStepper.step with the insertions marked W1-W3.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, replace
from typing import Dict, List, Optional

import mujoco
import numpy as np

from . import ROOT  # noqa: F401
from . import control as C
from . import devices as DV
from sim2 import sim as S  # noqa: E402
from sim2j import stepper as SJ  # noqa: E402
from sim2j.firmware import Firmware, FWConfig  # noqa: E402

WREC = ["w_cmg_u1", "w_cmg_u2", "w_col_u1", "w_col_u2", "w_sled_fx", "w_sled_fy", "w_omni_fx", "w_omni_fy",
        "w_gate", "w_tu", "w_piv1", "w_piv2", "w_tmd_f", "w_act"]


class WPFirmware(Firmware):
    """sim2j's firmware plus the whole-pen device laws (control.py) at the same tick."""

    def __init__(self, pm, fw: FWConfig, wp: C.WPConfig, task=None, wheel=None, mu_true=0.9):
        super().__init__(pm, fw, task, wheel=wheel, mu_true=mu_true)
        self.wp = wp
        self.gt = next((p for p in pm.plugins if isinstance(p, DV.CMGTail)), None)
        self.tm = next((p for p in pm.plugins if getattr(p, "name", "") == "tm"), None)
        self.col = pm.info.get("collar")
        pen = DV.pen_props(pm)
        self.pen_lin = pen
        self.imc = {}
        self.col_f, self.col_D = None, None
        r0 = wp.model_r_rot
        self.afc = {}
        col_ex = ({"z_p": self.col["z_p"], "K_c": self.col["K_c"], "c_c": self.col["c_c"], "m_c": self.col["m"],
                   "z_cm": self.col["z_cm"], "J_c": self.col["J"], "K_s": self.col["K_s"], "C_s": self.col["C_s"],
                   "skid_on_collar": self.col.get("skid_on_collar", False)}
                  if self.col is not None else None)
        for dev, mode, gain, ok, ex in (("cmg", wp.cmg, wp.cmg_gain, self.gt is not None, {}),
                                        ("collar", wp.collar, wp.collar_gain, self.col is not None, col_ex),
                                        ("sled", wp.sled, wp.sled_gain, True, {}),
                                        ("omni", wp.omni, wp.omni_gain, True, {})):
            if not ok or mode not in ("ff", "oracle", "afc"):
                continue
            f, G = C.internal_model(dev, pen, ex, r0)
            G_inv = C.internal_model(dev, pen, ex, r0, out="ink")[1] if dev == "collar" else None
            if dev == "collar":
                # the nose must cancel the INK's residual, which differs from the measured barrel tip's by
                # (G - G_ink) u (the ball slides on its refill as the pen swings): kept for the nose correction
                self.col_f, self.col_D = f, G - G_inv
            if mode == "afc":
                self.afc[dev] = C.AFC(f, G, tau=wp.afc_tau, G_ink=G_inv)
            elif mode == "oracle":
                self.imc[dev] = C.PhasorIMC(f, G, wp.oracle_gain, G_inv=G_inv, total=True)
            else:
                self.imc[dev] = C.PhasorIMC(f, G, gain, G_inv=G_inv)
        self.u_cmg = np.zeros(2)
        self.u_col = np.zeros(2)
        self.ucol_hist = deque(maxlen=400)
        self.F_sled = np.zeros(2)
        self.F_omni = np.zeros(2)
        self.gate_state = 0.0
        self.gate_t = 0.0
        self.tu_angle = 0.0
        self.ubuf = deque(maxlen=3000)
        self.tmd_f = self.tm.k_c if self.tm is not None else 0.0
        self.tmd_next = 0.0
        self.f_tmd = None
        self.N_meas = 1.0
        th = math.radians(pm.cfg.geom.theta_deg)
        self.cth = math.cos(th)
        self.lift_gate = 0.0
        # capture the sensor reading of each tick (the gyro for the 'damp' law)
        self._last_r = None
        _read = self.sens.read

        # V2 collar: the page sensor sits on the collar (which stays on the paper) and, with the pivot's angle sensors,
        # gives the inner pen's tip position on the page; its validity is the COLLAR's lift, not the swinging tip's
        self._col_body = pm.ids.get("body:collar") if (self.col is not None and self.col.get("skid_on_collar")) else None
        self._col_z0 = None
        lift_max = float(pm.cfg.sensors.page_lift_max)

        def _read_wrap(t, _read=_read):
            r = _read(t)
            if self._col_body is not None and "page" in r:
                zc = float(pm.d.xpos[self._col_body][2])
                if self._col_z0 is None:
                    self._col_z0 = zc
                p = r["page"]
                r["page"] = (p[0], p[1], p[2], bool((zc - self._col_z0) < lift_max))
            self._last_r = r
            return r
        self.sens.read = _read_wrap
        self.bp_gyro = C.BandPass2(*wp.cmg_band) if wp.cmg == "damp" else None
        self.wbuf = deque(maxlen=3000)

    # the tremor estimate the device laws use: the tracker's, or the oracle table (true no-device handle tremor)
    def _d_for(self, mode: str, t: float) -> np.ndarray:
        if mode == "oracle":
            dtab = self.task["oracle_d_dev"]
            k = min(int(round((t + self.wp.preview) / self.Ts)), len(dtab) - 1)
            return dtab[k]
        return self.d_hat

    def _active(self, mode: str) -> bool:
        if mode == "oracle":
            return self.contact or self.ps_valid
        if self.tracker is None:
            return False
        det = getattr(self.tracker, "det_gate", 1.0)
        return (det > 0.5 or not self.wp.detector_gate) and (self.contact or self.ps_valid)

    def _law(self, dev: str, mode: str, t: float, f_est: float, cap: float) -> np.ndarray:
        """The device's command (2-vector) from its law: 'ff'/'oracle' (internal-model phasor on d_hat or the true
        tremor) or 'afc' (adaptive cancellation on the measured handle-tip motion)."""
        if mode == "afc":
            y = self.ps if (self.ps is not None and self.ps_valid) else None
            return self.afc[dev].step(y, y is not None, f_est, self._active(mode), cap)
        imc = self.imc[dev]
        d = self._d_for(mode, t)
        fq = float(self.task.get("f0", f_est)) if mode == "oracle" else f_est
        u = C.cap_vec(imc.step(d, fq, self._active(mode)), cap)
        return u

    def _commit(self, dev: str, mode: str, u: np.ndarray):
        if mode in ("ff", "oracle"):
            self.imc[dev].commit(u)

    def tick(self, t: float):
        q = super().tick(t)
        wp = self.wp
        f_est = float(self.tracker.last[2]) if self.tracker is not None else 6.0
        if not np.isfinite(f_est) or f_est <= 0:
            f_est = 6.0
        det = getattr(self.tracker, "det", None) if self.tracker is not None else None
        if wp.use_line_f and det is not None and getattr(self.tracker, "det_gate", 0.0) > 0.5 and getattr(det, "f_line", 0.0) > 0:
            f_est = float(det.f_line)            # the detector's tremor line (the device laws only; the nose keeps the AKF's)
        if wp.true_f and "f0" in self.task:
            f_est = float(self.task["f0"])
        # ---- CMG tail
        if self.gt is not None and wp.cmg in ("ff", "oracle", "afc", "damp"):
            gt = self.gt
            fq = float(self.task.get("f0", f_est)) if wp.cmg == "oracle" else f_est
            w = TWO_PI * fq
            cap = wp.cmg_frac * 2 * gt.h * min(gt.rate_max, w * gt.delta_max) * 0.88
            if wp.cmg == "damp":
                g = self._last_r["gyro"] if self._last_r is not None else (0.0, 0.0, 0.0)
                wbp = self.bp_gyro.step(np.array([g[0], g[1]]))
                self.wbuf.append(wbp.copy())
                u = -wp.cmg_c * wbp if (self._active("afc") or not wp.detector_gate) else np.zeros(2)
                u = C.cap_vec(u, cap)
            else:
                u = self._law("cmg", wp.cmg, t, f_est, cap)
            if gt.mode == "turret":
                if np.any(u != 0):
                    self.ubuf.append(u.copy())
                buf = self.wbuf if wp.cmg == "damp" else self.ubuf
                target = C.principal_axis(buf) if (len(buf) > 200 and self.k % 20 == 0) else getattr(self, "_tu_target", self.tu_angle)
                self._tu_target = target
                # the turret turns at most 1 rad/s; the axis is defined modulo pi
                dtu = (target - self.tu_angle + math.pi / 2) % math.pi - math.pi / 2
                self.tu_angle += float(np.clip(dtu, -1.0 * self.Ts, 1.0 * self.Ts))
                o = np.array([math.cos(self.tu_angle), math.sin(self.tu_angle)])
                u = o * float(u @ o)
            self._commit("cmg", wp.cmg, u)
            self.u_cmg = u
        # ---- collar: the servo's reference angle (pen relative to the collar, about t1 and t2)
        if self.col is not None and wp.collar in ("ff", "oracle", "afc"):
            u = self._law("collar", wp.collar, t, f_est, wp.collar_frac * self.col["range_rad"])
            if wp.collar == "ff" and wp.collar_alloc == "overflow":
                # coarse/fine allocation: the running rms of the estimated total tremor (the phasor law's e); the
                # collar takes the share beyond the nib's reach at the amplitude-modulated peaks (x 1.3, ASSUMPTION)
                e = getattr(self.imc["collar"], "e_last", np.zeros(2))
                a = self.Ts / max(wp.alloc_tau, 1e-3)
                self.col_ms = (1 - a) * getattr(self, "col_ms", 0.0) + a * float(e @ e)
                peak = 1.3 * math.sqrt(2.0 * self.col_ms)
                share = min(wp.alloc_share_max, max(0.0, 1.0 - wp.alloc_reach / max(peak, 1e-9)))
                u = u * share
                self.col_share = share
            self._commit("collar", wp.collar, u)
            self.u_col = u
            self.ucol_hist.append(u.copy())
            # the nose (sim2j's 'tremor' mode commands -g d_hat, the barrel tip's residual): re-issue its command on
            # the ink's residual d_hat - (G - G_ink) u, phasor-realised at the tracked frequency
            if self.fw.nose == "tremor" and wp.nose_ink_correct and self.col_D is not None and wp.collar in ("ff", "afc"):
                fq = float(np.clip(f_est, self.col_f[0], self.col_f[-1]))
                kq = max(1, int(round(1.0 / (4.0 * fq * self.Ts))))
                Dr = np.array([[np.interp(fq, self.col_f, self.col_D[:, i, j].real) for j in range(2)] for i in range(2)])
                Di = np.array([[np.interp(fq, self.col_f, self.col_D[:, i, j].imag) for j in range(2)] for i in range(2)])
                uq = self.ucol_hist[-kq - 1] if len(self.ucol_hist) > kq else np.zeros(2)
                c = Dr @ u - Di @ uq
                x = -self.g_auth * (self.d_hat - c)
                q, x_used = self.to_q(x)
                self.q_page = x_used
        # ---- sled (force on the hand) and omni heel (force on the pen tip)
        for dev in ("sled", "omni"):
            mode = getattr(wp, dev)
            if mode in ("ff", "oracle", "afc"):
                capF = wp.sled_mu * wp.sled_N if dev == "sled" else wp.omni_F
                u = self._law(dev, mode, t, f_est, capF)
                self._commit(dev, mode, u)
                if dev == "sled":
                    self.F_sled = u
                else:
                    self.F_omni = u
        # ---- tuned mass, semi-active retuning
        if self.tm is not None and wp.tmd == "semi" and t >= self.tmd_next:
            self.tmd_next = t + 0.25
            det = getattr(self.tracker, "det_gate", 0.0) if self.tracker is not None else 0.0
            if det > 0.5:
                fq = float(np.clip(f_est, 3.5, 12.0))
                self.f_tmd = fq if self.f_tmd is None else self.f_tmd + 0.25 * (fq - self.f_tmd)
                k_new = self.tm.m * (TWO_PI * self.f_tmd) ** 2
                for jn in ("tm_0", "tm_1"):
                    self.pm.m.jnt_stiffness[self.pm.ids["jnt:" + jn]] = k_new
                self.tmd_f = k_new
        # ---- write only when in reach (pen lift)
        if wp.gate:
            det = getattr(self.tracker, "det_gate", 0.0) if self.tracker is not None else 0.0
            need = float(np.hypot(*self.d_hat))
            want = 1.0 if (det > 0.5 and need > self.reach - wp.gate_margin) else 0.0
            if want != self.gate_state and t - self.gate_t >= wp.gate_hold:
                self.gate_state = want
                self.gate_t = t
            if self.fw.nose != "autowrite":
                self.lift_cmd = self.gate_state
        return q


TWO_PI = 2.0 * math.pi


class WPStepper(SJ.RevJStepper):
    def __init__(self, pm, scn, fw: FWConfig, wp: C.WPConfig, task: Optional[Dict] = None, mu: float = 0.9,
                 arm_tremor=None, record: bool = True, t_end: Optional[float] = None, seed: int = 0):
        self.wp = wp
        super().__init__(pm, scn, fw, task=task, mu=mu, arm_tremor=arm_tremor, record=record, t_end=t_end, seed=seed)
        # replace sim2j's firmware by the extended one (same arguments)
        self.fw = WPFirmware(pm, fw, wp, task, wheel=self.wheel, mu_true=mu)
        self.gt = next((p for p in pm.plugins if isinstance(p, DV.CMGTail)), None)
        self.col = pm.info.get("collar")
        ids = pm.ids
        self.b_collar = ids.get("body:collar")
        self.b_hand_ = ids.get("body:hand", ids.get("body:palm"))
        self.s_piv = ids.get("site:collar_piv")
        self.a_piv = [ids.get("act:piv_m1"), ids.get("act:piv_m2")]
        self.skid_on_collar = bool(self.col is not None and self.col.get("skid_on_collar", False))
        if self.skid_on_collar and self.law is not None:
            # V2: the H1 contact law's skid point acts on the collar (the ring's frame is the collar's, which is the
            # handle's frame at rest), and the kernel clears the collar's applied force each step
            from sim2 import contact as SC
            bc = self.b_collar
            pc = self.law.pts[0]
            assert pc.name == "skid"
            pc.body = bc
            self.law.tab[0, SC.K_BODY] = bc
            self.law.tab[0, SC.K_ROOT] = pm.m.body_rootid[bc]
            self.law.bodies = sorted(set(self.law.bodies) | {bc})
            self.law.body_arr = np.array(self.law.bodies, dtype=np.int64)
        self.s_ball = ids["site:ball"]
        self.r_ball = float(pm.cfg.geom.r_b)
        self.q_refill = pm.jnt_qadr("refill_s")
        self.ext_max = 3.0e-3                # the V2 refill's extension bound beyond the collar-relative stop (m)
        self.j_piv = [pm.jnt_qadr("piv_1"), pm.jnt_qadr("piv_2")] if "jnt:piv_1" in ids else None
        self.jd_piv = [pm.jnt_dadr("piv_1"), pm.jnt_dadr("piv_2")] if "jnt:piv_1" in ids else None
        self.piv_sign = DV.collar_axes(pm) if "jnt:piv_1" in ids else (1.0, 1.0)
        self.wrec = np.zeros((self.nrec, len(WREC))) if record else None
        self.wenergy = {"cmg_mech_J": 0.0, "col_cu_J": 0.0, "col_mech_J": 0.0, "sled_J": 0.0, "omni_J": 0.0,
                        "gate_lift_cycles": 0}
        self._gate_prev = 0.0
        self.buf6 = np.zeros(6)

    # ---- the tick: sim2j's policy (nose, wheel, end-cap, lift) + this study's device commands
    def _policy(self, t, pm, servo):
        q = super()._policy(t, pm, servo)
        fw = self.fw
        if self.gt is not None:
            gt = self.gt
            if fw.wp.cmg in ("ff", "oracle", "afc", "damp"):
                u = fw.u_cmg
                dl = gt.delta(pm)
                rates = []
                wc = TWO_PI * fw.wp.cmg_center_hz
                def soft(r, dlt):
                    # soft barrier: a rate that drives the gimbal toward its limit fades to 0 over the last 0.25 rad
                    if r * dlt > 0:
                        r *= float(np.clip((gt.delta_max - abs(dlt)) / 0.25, 0.0, 1.0))
                    return r
                if gt.mode == "pairs":
                    for p in range(2):
                        c = max(math.cos(dl[p]), 0.2)
                        rates.append(soft(-u[p] / (2 * gt.h * c) - wc * dl[p], dl[p]))
                    gt.apply(pm, t, rates)
                else:
                    ang = fw.tu_angle
                    # the turret's own angle: 0 = output along t1
                    o = np.array([math.cos(ang), math.sin(ang)])
                    tau = float(u @ o)
                    c = max(math.cos(dl[0]), 0.2)
                    gt.apply(pm, t, [soft(-tau / (2 * gt.h * c) - wc * dl[0], dl[0]), ang])
            else:
                gt.apply(pm, t, [0.0] * len(gt.pairs()) + ([fw.tu_angle] if gt.mode == "turret" else []))
        if self.col is not None and self.a_piv[0] is not None:
            col = self.col
            ref = fw.u_col if fw.wp.collar in ("ff", "oracle", "afc") else np.zeros(2)
            # static-load feed-forward: the writing force's moment about the pivot (tilt plane, about t2), from the
            # skid load cell and the ball force (sim2j sensing: the contact law's normal forces, 5 mN noise ignored)
            # V1: skid and ball load the pen; V2: only the ball (the skid ring is on the collar)
            N = float(self.cont.get("Nb", 0.0)) + (0.0 if self.skid_on_collar else float(self.cont.get("Ns", 0.0)))
            tau_st = N * col["z_p"] * fw.cth
            d = pm.d
            # the servo on each hinge: piv_1 turns about t2 (sign s1), piv_2 about t1 (sign s2) (devices.collar_axes)
            th1, th2 = d.qpos[self.j_piv[0]], d.qpos[self.j_piv[1]]
            w1, w2 = d.qvel[self.jd_piv[0]], d.qvel[self.jd_piv[1]]
            s1, s2 = self.piv_sign
            # the paper's normal force at the tip turns the pen about +t2 by N z_p cos(theta) about the pivot: hold it
            tau1 = col["K_s"] * (s1 * ref[1] - th1) - col["C_s"] * w1 - s1 * tau_st
            tau2 = col["K_s"] * (s2 * ref[0] - th2) - col["C_s"] * w2
            d.ctrl[self.a_piv[0]] = float(np.clip(tau1, -col["tau_max"], col["tau_max"]))
            d.ctrl[self.a_piv[1]] = float(np.clip(tau2, -col["tau_max"], col["tau_max"]))
        if fw.lift_cmd > 0.5 and self._gate_prev <= 0.5 and fw.wp.gate:
            self.wenergy["gate_lift_cycles"] += 1
        self._gate_prev = fw.lift_cmd
        return q

    # ---- one physics step (copy of sim2j.stepper.RevJStepper.step with the insertions W1-W3)
    def step(self):
        k = self.k
        m, d, pm, opt, servo = self.m, self.d, self.pm, self.opt, self.servo
        dt = self.dt
        mujoco.mj_step1(m, d)
        if self.hand and self.relaxed is not None:
            self._relaxed_ctrl(k)
        elif self.hand:
            d.ctrl[self.hidx] = self.hctl[k]
            if self.rot:
                d.ctrl[self.a_psi[0]] = self.psi[k]
                d.ctrl[self.a_psi[1]] = self.psid[k]
        else:
            self.arm.step(k)
        if self.law is not None:
            self.law.forces(self.fpush[k] if self.hand else 0.0)
        elif self.hand:
            S.push_only(pm, self.fpush[k])
        self.wheel.step(d)
        # ---- W1: collar push, sled and omni-heel forces
        self._w_forces(k)
        if k % self.rdec == 0:
            if self.law is None:
                self.cont = S.native_contact_forces(pm)
            else:
                self.cont = self.law.summary()
            in_c = self._update_flag()
            self._in_c = in_c
            tip = d.site_xpos[self.s_tip]
            direct = opt.policy(k * dt, pm, servo)
            # the servo's bias/authority gate sees the firmware's delayed measured contact, as in sim2j's RevJStepper
            # (the true force only with contact_source 'force' / 'legacy_force')
            gate_contact = in_c if self.contact_source in ("force", "legacy_force") else self.fw.contact
            servo.ref_tick(k * dt, self.tick, tip, gate_contact, direct_q=direct)
            self.gate = servo.g_eff
            self.tick += 1
        if k % self.sdec == 0:
            servo.servo_tick(self.sdec * dt, self.gate)
            if self.skid_on_collar and servo.adaptive_stop:
                # W4: the V2 collar's refill stop.  The ball moves -z_p phi along t1 when the pen turns by phi about
                # t2, and the collar itself rocks on its skid ring under the motors' reaction, so the ball's contact
                # position is not a function of phi alone.  PROPOSED DESIGN: while the skid ring carries load (its
                # load cell), the stop follows the paper (the ball may protrude `margin` beyond its contact
                # position), bounded to ext_max beyond the collar-relative stop; with the skid ring unloaded (a
                # lift) the stop is collar-relative, so the ball lifts with the pen and strokes do not join
                phi = self.piv_sign[0] * d.qpos[self.j_piv[0]]
                rel = m.jnt_range[self.j_refill, 0] - self.col["z_p"] * phi * servo.cot
                stop = rel
                if float(self.cont.get("Ns", 0.0)) > 0.05:
                    zlow = float(d.site_xpos[self.s_ball][2]) - self.r_ball
                    az = float(d.xaxis[self.j_refill][2])
                    s_con = float(d.qpos[self.q_refill]) - zlow / max(az, 0.2)
                    stop = max(min(s_con - self.margin, rel + 0.3e-3), rel - self.ext_max)
                m.jnt_range[self.j_refill, 0] = stop
            servo.follower_steps(self.sdec)
            if self.lift_state > 0.0:
                m.jnt_range[self.j_refill, 0] += self.lift_state * (self.margin + self.lift_stroke)
        if self.rec is not None and k % self.recdec == 0 and self.ri < self.nrec:
            if self.law is not None:
                self.cont = self.law.summary()
            self._xrecord()
            self._wrecord()          # W3
            self._record(k)
        mujoco.mj_step2(m, d)
        if not np.isfinite(d.qacc[0]):
            raise FloatingPointError(f"simulation diverged at t = {k * dt:.4f} s")
        # ---- W2: energy bookkeeping of the devices (every step)
        self._w_energy()
        self.k += 1

    def _w_forces(self, k):
        d, pm, fw = self.d, self.pm, self.fw
        dt = self.dt
        bh = self.b_handle
        # the collar carries the writing push: remove the law's push at the pen tip, apply it at the collar's pivot
        if self.b_collar is not None and self.hand:
            P = float(self.fpush[k])
            pt = d.site_xpos[self.s_tip]
            ch = d.xipos[bh]
            xh = d.xfrc_applied[bh]
            ux, uy = pt[0] - ch[0], pt[1] - ch[1]
            xh[2] += P
            xh[3] -= uy * -P
            xh[4] -= -ux * -P
            pp = d.site_xpos[self.s_piv]
            cc = d.xipos[self.b_collar]
            xc = d.xfrc_applied[self.b_collar]
            if not self.skid_on_collar:
                xc[:] = 0.0                  # V1: nothing else pushes the collar (V2: the contact law cleared it)
            xc[2] += -P
            xc[3] += (pp[1] - cc[1]) * -P
            xc[4] += -(pp[0] - cc[0]) * -P
        # sled: force on the hand (H1: the hand body; arm: the palm) from the paper, capped at mu N
        if fw.wp.sled != "off" and self.b_hand_ is not None:
            xh = d.xfrc_applied[self.b_hand_]
            if fw.wp.sled == "damp":
                mujoco.mj_objectVelocity(self.m, d, mujoco.mjtObj.mjOBJ_BODY, self.b_hand_, self.buf6, 0)
                F = -fw.wp.sled_c * self.buf6[3:5]
                F = C.cap_vec(F, fw.wp.sled_mu * fw.wp.sled_N)
                fw.F_sled = F
            else:
                F = fw.F_sled
            xh[:] = 0.0                     # nothing else pushes the hand body: assign (a += would accumulate)
            xh[0] = F[0]
            xh[1] = F[1]
        # omni heel: force on the pen at its tip (paper-grounded), capped
        if fw.wp.omni != "off" and self.in_contact():
            pt = d.site_xpos[self.s_tip]
            ch = d.xipos[bh]
            F = fw.F_omni
            xh = d.xfrc_applied[bh]
            xh[0] += F[0]
            xh[1] += F[1]
            rz = pt[2] - ch[2]
            rx, ry = pt[0] - ch[0], pt[1] - ch[1]
            xh[3] += -rz * F[1]
            xh[4] += rz * F[0]
            xh[5] += rx * F[1] - ry * F[0]

    def _w_energy(self):
        d, pm = self.d, self.pm
        dt = self.dt
        if self.gt is not None:
            self.wenergy["cmg_mech_J"] += self.gt.power(pm) * dt
        if self.col is not None and self.a_piv[0] is not None:
            for j, a in enumerate(self.a_piv):
                tau = float(d.actuator_force[a])
                w = float(d.qvel[pm.jnt_dadr("piv_%d" % (j + 1))])
                self.wenergy["col_mech_J"] += abs(tau * w) * dt
                Km = self.col.get("Km", 0.03)
                self.wenergy["col_cu_J"] += (tau / Km) ** 2 * dt if Km > 0 else 0.0
        fw = self.fw
        if fw.wp.sled != "off":
            self.wenergy["sled_J"] += float(fw.F_sled @ fw.F_sled) * dt
        if fw.wp.omni != "off":
            self.wenergy["omni_J"] += float(fw.F_omni @ fw.F_omni) * dt

    def _wrecord(self):
        if self.wrec is None or self.ri >= self.nrec:
            return
        fw = self.fw
        r = self.wrec[self.ri]
        r[0:2] = fw.u_cmg
        r[2:4] = fw.u_col
        r[4:6] = fw.F_sled
        r[6:8] = fw.F_omni
        r[8] = fw.lift_cmd
        r[9] = fw.tu_angle
        if self.j_piv is not None:
            r[10] = self.d.qpos[self.j_piv[0]]
            r[11] = self.d.qpos[self.j_piv[1]]
        r[12] = fw.tmd_f
        r[13] = 1.0 if (fw.tracker is not None and getattr(fw.tracker, "det_gate", 0.0) > 0.5) else 0.0

    def result(self):
        res = super().result()
        n = res.rec.shape[0]
        if self.wrec is not None:
            res.rec = np.hstack([res.rec, self.wrec[:n]])
            res.names = res.names + WREC
            res.idx = {nm: i for i, nm in enumerate(res.names)}
        res.info["w_energy"] = dict(self.wenergy)
        return res


def run(pm, scn, fw: FWConfig, wp: C.WPConfig, task: Optional[Dict] = None, mu: float = 0.9, arm_tremor=None,
        t_end: Optional[float] = None, seed: int = 0):
    st = WPStepper(pm, scn, fw, wp, task=task, mu=mu, arm_tremor=arm_tremor, t_end=t_end, seed=seed)
    st.advance(st.n)
    return st.result()
