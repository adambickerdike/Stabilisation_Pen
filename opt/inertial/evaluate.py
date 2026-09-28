"""Evaluation of Rev H designs on model H1: oracle and causal (tracker) runs, metrics, power.

Harness convention (sim/handpen/run_study.py, P1): reference = the same pen (nose held centred, devices neutral) on the
same handwriting without tremor; ratio = e_rms(controller) / e_rms(no correction), both against that reference; band
ratio = the same in 3-15 Hz; stage saturation as P1; distortion = the controller on tremor-free writing against the
reference (false correction); vs_intended = ink against the writer's intended path (3-15 Hz).
Power (CALC from the simulated trajectories): tip actuator copper loss (F / Km_tip)^2 per axis with the static bias
removed, plus drivers and electronics.  Evidence status: SIMULATION (runs) and CALCULATION (power).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

from sim.handpen import evaluate as HE
from sim.handpen import model as HM
from sim.handpen.params import geometry_vectors
from . import catalog as CT
from . import revh as RH
from . import scen as SC
from . import tracker as TK

P_BASE = CT.ELECTRONICS["base_W"]       # 0.065 W recording, BLE, MCU (ASSUMPTION, config)
P_DRV_Q = 0.012                          # two coil drivers + Hall sensors (ASSUMPTION)


def tip_power_B(res, d: RH.RevH, theta_deg=50.0, mask=None) -> Dict:
    """Copper loss of the architecture-B nose actuators (CALC): F_tip = m_eff q'' + k_s q + ball loads - bias."""
    ms = RH.masses(d)
    m_eff = ms["moving_mass_at_tip_g"] * 1e-3
    k_s = d.k_r / d.z_p ** 2
    a, t1, t2, n, h = geometry_vectors(theta_deg)
    t = res["t"]
    dt = t[1] - t[0]
    q = np.column_stack([res["q1"], res["q2"]])
    qdd = np.gradient(np.gradient(q, dt, axis=0), dt, axis=0)
    fn = np.column_stack([res["fnx"], res["fny"], np.zeros(len(t))])
    Nn = res["Nn"]
    load1 = -Nn * math.cos(theta_deg * math.pi / 180) + fn @ t1
    load2 = fn @ t2
    bias1 = -0.15 / math.sin(theta_deg * math.pi / 180) * math.cos(theta_deg * math.pi / 180) if d.bias else 0.0
    F1 = m_eff * qdd[:, 0] + k_s * q[:, 0] - (load1 - bias1 * (Nn > 0))
    F2 = m_eff * qdd[:, 1] + k_s * q[:, 1] - load2
    m = np.ones(len(t), bool) if mask is None else mask
    m = m & (t > 0.5)
    P_cu = float((np.mean(F1[m] ** 2) + np.mean(F2[m] ** 2)) / d.Km_tip ** 2)
    return {"F_tip_rms_N": [float(np.sqrt(np.mean(F1[m] ** 2))), float(np.sqrt(np.mean(F2[m] ** 2)))],
            "F_tip_peak_N": [float(np.max(np.abs(F1[m]))), float(np.max(np.abs(F2[m])))],
            "P_cu_W": P_cu, "P_total_W": P_BASE + P_DRV_Q + P_cu,
            "tip_speed_peak_m_s": float(np.max(np.linalg.norm(np.gradient(q, dt, axis=0)[m], axis=1)))}


class RevHEval:
    """Runs of one Rev H architecture-B design (the pen body is the handle; the stage is the moving refill)."""

    def __init__(self, d: RH.RevH, r_rot=0.5, rho_w=0.3, device=None, akf_params: Optional[Dict] = None, ctl=None,
                 dev_uff=None, theta_deg=50.0):
        self.d = d
        self.cfg = RH.config_B(d, r_rot=r_rot, rho_w=rho_w, device=device, theta_deg=theta_deg)
        if ctl is not None:
            self.cfg = self.cfg.replace(ctl=ctl)
        self.akf_params = akf_params
        self.theta = theta_deg
        self._ref = {}

    def ref(self, seed, writer="lognormal"):
        k = (seed, writer)
        if k not in self._ref:
            sc0 = SC.get(seed, None, writer)
            self._ref[k] = HM.run(sc0, self.cfg, rec_hz=TK.REC_HZ)
        return self._ref[k]

    def estimate(self, res, sc, seed):
        dh, info, st = TK.estimate(res, sc, seed=seed + 7000, body="pen", z_imu=0.100, theta_deg=self.theta, params=self.akf_params)
        return dh, info

    def case(self, seed, f0, amp, kind="trans", writer="lognormal", controllers=("oracle", "akf"), power=True) -> Dict:
        tr = SC.tremor(f0, amp, kind) if amp > 0 else None
        sc = SC.get(seed, tr, writer)
        n = len(sc.t)
        ref = self.ref(seed, writer)
        un = HM.run(sc, self.cfg, rec_hz=TK.REC_HZ)
        mu = HE.compare(un, ref)
        out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "kind": kind, "writer": writer, "unmod_e_rms_um": mu["e_rms_um"],
               "unmod_band_um": mu["e_band_rms_um"]}
        iu = HE.vs_intended(un, sc)
        out["unmod_int_band_um"] = iu["e_int_band_um"]
        for c in controllers:
            if c == "oracle":
                r = HM.run(sc, self.cfg.replace(stage=True), clean=HM.clean_at_sim_rate(ref, n), rec_hz=TK.REC_HZ)
            elif c == "akf":
                dh, info = self.estimate(un, sc, seed)
                r = HM.run(sc, self.cfg.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
                out["akf_f_est_mean"] = float(np.mean(info["f_est"][len(info["f_est"]) // 5:]))
            else:
                raise KeyError(c)
            m = HE.compare(r, ref)
            iv = HE.vs_intended(r, sc)
            row = {"ratio": m["e_rms_um"] / mu["e_rms_um"], "band_ratio": m["e_band_rms_um"] / mu["e_band_rms_um"],
                   "e_rms_um": m["e_rms_um"], "q_sat_frac": m["q_sat_frac"], "q_rms_um": m["q_rms_um"],
                   "int_band_ratio": iv["e_int_band_um"] / max(iu["e_int_band_um"], 1e-12)}
            if power:
                row.update(tip_power_B(r, self.d, self.theta))
            out[c] = row
        return out

    def distortion(self, seed, writer="lognormal") -> Dict:
        """False correction of the causal tracker on tremor-free writing (closed loop, against the reference)."""
        sc0 = SC.get(seed, None, writer)
        n = len(sc0.t)
        ref = self.ref(seed, writer)
        dh, info = self.estimate(ref, sc0, seed)
        r = HM.run(sc0, self.cfg.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
        dst = HE.distortion(r, ref)
        return {"seed": seed, "writer": writer, "distortion_um": dst["detrended_rms_um"], "lag_ms": dst["lag_ms"],
                "amp_ratio": dst["amplitude_ratio"]}
