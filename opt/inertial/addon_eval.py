"""Evaluation of the rear-cap inertial add-on on top of the Rev H active nose (architecture B), model H1.

Controllers of the reaction mass (RM):
  ilc        oracle: iterative learning on the true disturbance (sim/handpen/model.ilc_oracle), RM alone (upper bound)
  ff         tracker-driven feed-forward (task 4a): phasor model inverse at the tracked frequency (addon.ff_phasor), with the
             linear model at the nominal split r_rot 0.5 ('ff') or at the case's true split ('ff_cal' = after a grip
             calibration that identifies the plant; ASSUMPTION that 2 s of probing identifies it exactly)
  afc        adaptive narrow-band feedback (task 4b) at the tracked frequency, error = the handle-tip acceleration from the
             IMU (accelerometer minus gyro lever arm); table at the nominal split ('afc') or the true split ('afc_cal')
  nn         neural policy trained by BPTT (opt/inertial/neural.py), when available
The nose always uses the Rev H tracker setting on the closed-loop handle motion (the realistic cascade: the RM changes the
handle motion and the tracker sees it).  Comparator: the same mass fixed in the rear cap ('weight', passive).
Ratios: against the Rev H pen WITHOUT the add-on and without correction (unmod0), so the add-on is credited with both its
passive mass and its control.  Evidence status: SIMULATION.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np

from sim.handpen import evaluate as HE
from sim.handpen import model as HM
from . import addon as AD
from . import control as CL
from . import revh as RH
from . import scen as SC
from . import tracker as TK


def default_rm():
    """Rear-cap RM of the recommendation candidate: WHA 10 x 14 mm (19.8 g, AMF-49), +/-2.75 mm, centring loop 5 Hz, 0.5 N."""
    return AD.rm_rear(m_slug=19.8e-3, d_slug=10e-3, f_c=5.0, F_max=0.5, Km=0.9, coil_mass=4e-3, frame_mass=4e-3)


class AddonEval:
    def __init__(self, d: Optional[RH.RevH] = None, rm=None, r_rot=0.5, akf_params=None, afc_mu=0.005, afc_leak=2e-4, ff_gain=1.0,
                 nn_spec=None):
        self.d = d or RH.RevH()
        self.rm = rm or default_rm()
        self.r_rot = r_rot
        self.cfg0 = RH.config_B(self.d, r_rot=r_rot)
        self.cfgR = RH.config_B(self.d, r_rot=r_rot, device=self.rm)
        m_add = self.rm.m + self.rm.added_fixed
        self.cfgW = RH.config_B(RH.RevH(**{**self.d.__dict__, "extra_mass": m_add, "extra_mass_z": self.rm.z}), r_rot=r_rot)
        self.akf = akf_params
        imu = dict(seed=5, lat_ticks=3)
        uls = [self.rm.F_max[0], self.rm.F_max[1], 0, 0, 0, 0, 0]
        self.ctl = {}
        for tag, rr in (("afc", 0.5), ("afc_cal", r_rot)):
            blk, afc = AD.afc_rm(self.d, self.rm, r_rot_model=rr, mu=afc_mu, leak=afc_leak)
            self.ctl[tag] = CL.ctl_spec(blk, Ts=5e-4, imu=imu, afc=afc, ulim=uls)
        self.nn_spec = nn_spec
        self.ff_gain = ff_gain
        self._ref = {}

    def ref(self, seed, cfg_key):
        k = (seed, cfg_key)
        if k not in self._ref:
            cfg = {"0": self.cfg0, "R": self.cfgR, "W": self.cfgW}[cfg_key]
            self._ref[k] = HM.run(SC.get(seed), cfg, rec_hz=TK.REC_HZ)
        return self._ref[k]

    def _est(self, res, sc, seed):
        dh, info, _ = TK.estimate(res, sc, seed=seed + 7000, body="pen", params=self.akf)
        return dh, info

    def case(self, seed, f0, amp, kind="trans", controllers=("ilc", "ff", "ff_cal", "afc", "afc_cal"), with_nose=True,
             writer="lognormal") -> Dict:
        tr = SC.tremor(f0, amp, kind) if amp > 0 else None
        sc = SC.get(seed, tr, writer)
        n = len(sc.t)
        ref0, refR, refW = self.ref(seed, "0"), self.ref(seed, "R"), self.ref(seed, "W")
        un0 = HM.run(sc, self.cfg0, rec_hz=TK.REC_HZ)
        m0 = HE.compare(un0, ref0)
        base = m0["e_rms_um"]
        out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "kind": kind, "r_rot": self.r_rot, "unmod0_um": base}
        # nose alone (the Rev H pen)
        dh0, info0 = self._est(un0, sc, seed)
        rn = HM.run(sc, self.cfg0.replace(stage=True, stage_src=1), clean=TK.to_steps(dh0, n), rec_hz=TK.REC_HZ)
        out["nose"] = HE.compare(rn, ref0)["e_rms_um"] / base
        # passive weight
        unW = HM.run(sc, self.cfgW, rec_hz=TK.REC_HZ)
        out["weight"] = HE.compare(unW, refW)["e_rms_um"] / base
        if with_nose:
            dhW, _ = self._est(unW, sc, seed)
            rnw = HM.run(sc, self.cfgW.replace(stage=True, stage_src=1), clean=TK.to_steps(dhW, n), rec_hz=TK.REC_HZ)
            out["nose+weight"] = HE.compare(rnw, refW)["e_rms_um"] / base
        unR = HM.run(sc, self.cfgR, rec_hz=TK.REC_HZ)
        out["rm_neutral"] = HE.compare(unR, refR)["e_rms_um"] / base
        # tracker on the neutral RM pen (open loop) gives the frequency and the feed-forward estimate
        dhR, infoR = self._est(unR, sc, seed)
        f_ticks = infoR["f_est"]
        uext = np.zeros((n, 7))
        uext[:, 3:5] = TK.to_steps(dhR, n)
        uext[:, 5] = TK.freq_to_steps(f_ticks, n)
        uext[:, 6] = TK.freq_to_steps(infoR["authority"] / max(float((self.akf or TK.ship_params()).get("g", 1.0)), 1e-9), n)
        for c in controllers:
            if c == "ilc":
                refR2 = HM.run(SC.get(seed), self.cfgR)
                un2 = HM.run(sc, self.cfgR)
                best = None
                for pct in (60.0, 95.0):
                    r, u, hist = HM.ilc_oracle(sc, self.cfgR, refR2, n_iter=6, pct=pct, margin=1.0)
                    e = HE.compare(r, refR2)["e_rms_um"]
                    best = e if best is None else min(best, e)
                out["ilc"] = best / HE.compare(un2, refR2)["e_rms_um"] * out["rm_neutral"]
                continue
            if c.startswith("ff"):
                rr = 0.5 if c == "ff" else self.r_rot
                u = np.zeros((n, 7))
                u[:, 0:2] = TK.to_steps(AD.ff_phasor(dhR, f_ticks, self.d, self.rm, r_rot_model=rr, gain=self.ff_gain), n)
                cfg = self.cfgR
                r = HM.run(sc, cfg, uff=u[:, 0:3].copy(), rec_hz=TK.REC_HZ)
                useq = u[:, 0:3].copy()
            elif c.startswith("afc"):
                cfg = self.cfgR.replace(ctl=self.ctl[c])
                r = HM.run(sc, cfg, uff=uext, rec_hz=TK.REC_HZ)
                useq = uext
            elif c == "nn" and self.nn_spec is not None:
                cfg = self.cfgR.replace(ctl=self.nn_spec)
                r = HM.run(sc, cfg, uff=uext, rec_hz=TK.REC_HZ)
                useq = uext
            else:
                continue
            m = HE.compare(r, refR)
            out[c] = m["e_rms_um"] / base
            out[c + "_F_rms_N"] = m["dev_force_rms_N"][:2]
            out[c + "_stroke_pk_mm"] = m["dev_stroke_peak_mm"][:2]
            out[c + "_P_W"] = float(sum(f * f for f in m["dev_force_rms_N"][:2]) / self.rm.Km ** 2)
            if with_nose:
                dh2, _ = self._est(r, sc, seed)
                if c.startswith("ff"):
                    rn2 = HM.run(sc, cfg.replace(stage=True, stage_src=1), uff=useq, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
                else:
                    rn2 = HM.run(sc, cfg.replace(stage=True, stage_src=1), uff=useq, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
                out["nose+" + c] = HE.compare(rn2, refR)["e_rms_um"] / base
        return out

    def distortion(self, seed, c, writer="lognormal"):
        """False correction of the RM controller on tremor-free writing (closed loop), against the neutral RM pen."""
        sc0 = SC.get(seed, None, writer)
        n = len(sc0.t)
        refR = HM.run(sc0, self.cfgR, rec_hz=TK.REC_HZ)
        dhR, infoR = self._est(refR, sc0, seed)
        if c.startswith("ff"):
            u = np.zeros((n, 3))
            u[:, 0:2] = TK.to_steps(AD.ff_phasor(dhR, infoR["f_est"], self.d, self.rm, r_rot_model=0.5 if c == "ff" else self.r_rot,
                                                 gain=self.ff_gain), n)
            r = HM.run(sc0, self.cfgR, uff=u, rec_hz=TK.REC_HZ)
        else:
            uext = np.zeros((n, 7))
            uext[:, 3:5] = TK.to_steps(dhR, n)
            uext[:, 5] = TK.freq_to_steps(infoR["f_est"], n)
            uext[:, 6] = TK.freq_to_steps(infoR["authority"] / max(float((self.akf or TK.ship_params()).get("g", 1.0)), 1e-9), n)
            spec = self.nn_spec if c == "nn" else self.ctl[c]
            r = HM.run(sc0, self.cfgR.replace(ctl=spec), uff=uext, rec_hz=TK.REC_HZ)
        return HE.distortion(r, refR)["detrended_rms_um"]
