r"""sim2's stepper with the Rev J devices and the firmware in the loop (SIMULATION).

Per physics step (25 us, implicitfast; sim2's order): mj_step1 -> hand drive (H1 imposed path or the arm's writer
controller) -> sim2's H1 contact law (skid ring, ball) -> the heel wheel kernel (wheel.py; adds its wrench) -> at the
2 kHz tick: the firmware (sensors -> tracker -> controllers) sets the nose reference, the wheel's heading and motor
force, the end-cap coil forces and the pen-lift command -> nose servo at 10 kHz (sim2) -> the pen lift moves the
refill's front stop -> record -> mj_step2.  sim2's files are unchanged: this subclass copies sim2.sim.Stepper.step
with the two insertions (wheel kernel, pen lift) marked below.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, Optional

import mujoco
import numpy as np

from . import ROOT  # noqa: F401
from sim2 import sim as S  # noqa: E402
from .firmware import Firmware, FWConfig
from .wheel import OI, Wheel, WheelParams

XREC = ["wN", "wFx", "wFy", "wpsi", "wu", "wslide", "wFmc", "qpx", "qpy", "dhx", "dhy", "f_est", "auth", "det_gate",
        "lift", "ecx", "ecy", "wcap", "wmuh", "grip_ax", "grip_ay"]


class RevJStepper(S.Stepper):
    """relaxed = {"tau": 0.25, "tau_air": 0.05} makes the H1 writer relaxed (the drive study's lead-through model,
    drive/plant.py 'relaxed'): while the pen is down the writer's aim (the arm spring's anchor) follows the hand with
    time constant tau (the writer yields to the pen); while the pen is up it follows the writer's own path (the
    scenario's hand path: the moves to the next stroke) with tau_air.  The scenario's z (lift) and pen force are kept;
    tremor is not supported in this mode."""

    def __init__(self, pm, scn, fw: FWConfig, task: Optional[Dict] = None, wheel_params: Optional[WheelParams] = None,
                 mu: float = 0.9, arm_tremor=None, record: bool = True, t_end: Optional[float] = None, seed: int = 0,
                 relaxed: Optional[Dict] = None):
        self._fw_cfg = fw
        opt = S.RunOptions(source="neutral", policy=self._policy, record=record, t_end=t_end, seed=seed)
        super().__init__(pm, scn, opt, arm_tremor=arm_tremor)
        if wheel_params is None:
            from . import revj as _RJ
            wheel_params = _RJ.wheel_params(_RJ.source_of(pm.cfg), mu=mu)
        wp = wheel_params
        if wp.mu != mu:
            from dataclasses import replace
            wp = replace(wp, mu=mu)
        self.wheel = Wheel(pm, wp, on=(fw.wheel != "off"))
        if fw.wheel in ("free", "path", "tremor"):
            pass
        self.fw = Firmware(pm, fw, task, wheel=self.wheel, mu_true=mu)
        psi0 = 0.0
        if task and task.get("psi0") is not None:
            psi0 = float(task["psi0"])
        self.wheel.reset(psi0)
        self.j_refill = pm.ids["jnt:refill_s"]
        self.margin = pm.cfg.geom.front_stop_margin
        self.lift_stroke = fw.lift_stroke
        self.lift_q = deque()
        self.lift_state = 0.0
        self.lift_delay = fw.aw_lift_delay
        self.lift_ramp = 5e-3
        self.rm = [pl for pl in pm.plugins if pl.name == "rm"]
        self.xrec = np.zeros((self.nrec, len(XREC))) if record else None
        self.xi = 0
        self.energy = {"wheel_pos_J": 0.0, "lift_cycles": 0, "ec_cu_J": 0.0}
        self._last_lift_cmd = 0.0
        self.relaxed = relaxed
        self._in_c = False
        if relaxed is not None:
            if not self.hand:
                raise ValueError("the relaxed writer needs the H1 hand")
            self.hq = [pm.jnt_qadr("hand_x"), pm.jnt_qadr("hand_y")]
            self.anchor = self.hctl[0, 0:2].copy()
            self.a_tau = float(relaxed.get("tau", 0.25))
            self.a_tau_air = float(relaxed.get("tau_air", 0.05))
            self._row = np.zeros(self.hctl.shape[1])

    # the firmware is sim2's 'policy' hook: called at every 2 kHz reference tick, returns the tip reference (t1, t2)
    def _policy(self, t, pm, servo):
        q = self.fw.tick(t)
        # end-cap coil forces (applied here, at the tick)
        if self.rm and self.fw.ec_cmd is not None:
            self.rm[0].apply(pm, t, self.fw.ec_cmd)
            self.energy["ec_cu_J"] += float(self.rm[0].power(pm)) * 0.5e-3
        elif self.rm:
            self.rm[0].apply(pm, t, np.zeros(2))
        # pen lift: the command enters a delay line (switching delay), then a ramp
        lc = self.fw.lift_cmd
        if lc != self._last_lift_cmd and lc > 0.5:
            self.energy["lift_cycles"] += 1
        self._last_lift_cmd = lc
        self.lift_q.append((t + self.lift_delay, lc))
        while self.lift_q and self.lift_q[0][0] <= t:
            target = self.lift_q.popleft()[1]
            self._lift_target = target
        tgt = getattr(self, "_lift_target", 0.0)
        step = 0.5e-3 / self.lift_ramp
        self.lift_state = min(tgt, self.lift_state + step) if tgt > self.lift_state else max(tgt, self.lift_state - step)
        return q

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
        # ---- insertion 1: the heel wheel's wrench (every physics step)
        self.wheel.step(d)
        if k % self.rdec == 0:
            if self.law is None:
                self.cont = S.native_contact_forces(pm)
            else:
                self.cont = self.law.summary()
            in_c = self._update_flag()
            self._in_c = in_c
            tip = d.site_xpos[self.s_tip]
            direct = opt.policy(k * dt, pm, servo)
            servo.ref_tick(k * dt, self.tick, tip, in_c, direct_q=direct)
            self.gate = servo.g_eff
            self.tick += 1
        if k % self.sdec == 0:
            servo.servo_tick(self.sdec * dt, self.gate)
            servo.follower_steps(self.sdec)
            # ---- insertion 2: the pen lift moves the front stop back by (margin + stroke) x lift state
            if self.lift_state > 0.0:
                m.jnt_range[self.j_refill, 0] += self.lift_state * (self.margin + self.lift_stroke)
        if self.rec is not None and k % self.recdec == 0 and self.ri < self.nrec:
            if self.law is not None:
                self.cont = self.law.summary()
            self._xrecord()
            self._record(k)
        mujoco.mj_step2(m, d)
        if not np.isfinite(d.qacc[0]):
            raise FloatingPointError(f"simulation diverged at t = {k * dt:.4f} s")
        self.k += 1

    def _relaxed_ctrl(self, k):
        d = self.d
        row = self._row
        row[:] = self.hctl[k]
        an = self.anchor
        if self._in_c:
            q0 = d.qpos[self.hq[0]]; q1 = d.qpos[self.hq[1]]
            v0 = (q0 - an[0]) / self.a_tau; v1 = (q1 - an[1]) / self.a_tau
        else:
            v0 = (row[0] - an[0]) / self.a_tau_air; v1 = (row[1] - an[1]) / self.a_tau_air
        an[0] += v0 * self.dt; an[1] += v1 * self.dt
        row[0] = an[0]; row[1] = an[1]
        row[3] = v0; row[4] = v1
        row[6] = 0.0; row[7] = 0.0
        d.ctrl[self.hidx] = row

    def _xrecord(self):
        if self.xrec is None or self.ri >= self.nrec:
            return
        o = self.wheel.out
        fw = self.fw
        r = self.xrec[self.ri]
        r[0] = o[OI["N"]]; r[1] = o[OI["Fx"]]; r[2] = o[OI["Fy"]]; r[3] = o[OI["psi"]]; r[4] = o[OI["u"]]
        r[5] = o[OI["slide"]]; r[6] = self.wheel.st[5]
        r[7] = fw.q_page[0]; r[8] = fw.q_page[1]; r[9] = fw.d_hat[0]; r[10] = fw.d_hat[1]
        if fw.tracker is not None:
            r[11] = fw.tracker.last[2]; r[12] = fw.tracker.last[3]; r[13] = fw.tracker.det_gate
        r[14] = self.lift_state
        if fw.ec_cmd is not None:
            r[15] = fw.ec_cmd[0]; r[16] = fw.ec_cmd[1]
        r[17] = fw.capd; r[18] = fw.muh
        # grip force on the pen in the page plane (what the writer's hand feels), from sim2's grip joints
        d = self.d
        r[19] = -d.qfrc_passive[self.gq[0]]
        r[20] = -d.qfrc_passive[self.gq[1]]

    def result(self):
        res = super().result()
        n = res.rec.shape[0]
        if self.xrec is not None:
            res.rec = np.hstack([res.rec, self.xrec[:n]])
            res.names = res.names + XREC
            res.idx = {nm: i for i, nm in enumerate(res.names)}
        res.info["energy"] = dict(self.energy)
        res.info["wheel_energy_pos_J"] = float(self.wheel.energy_pos)
        res.info["wheel_kP"] = float(self.wheel.wp.kP_copper)
        if self.fw.fw.record_streams:
            res.info["streams"] = self.fw.streams
            res.info["n_ticks"] = int(self.fw.k)
        res.info["guard_events"] = list(self.fw.tracker.events) if self.fw.tracker is not None else []
        if self.fw.aw is not None:
            res.info["aw_tau"] = np.array(self.fw.aw["tau_log"])
        return res


def run(pm, scn, fw: FWConfig, task: Optional[Dict] = None, mu: float = 0.9, arm_tremor=None,
        wheel_params: Optional[WheelParams] = None, t_end: Optional[float] = None, seed: int = 0,
        relaxed: Optional[Dict] = None):
    st = RevJStepper(pm, scn, fw, task, wheel_params=wheel_params, mu=mu, arm_tremor=arm_tremor, t_end=t_end, seed=seed,
                     relaxed=relaxed)
    st.advance(st.n)
    return st.result()
