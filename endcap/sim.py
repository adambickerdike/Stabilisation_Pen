r"""Time-domain runs of the end-cap devices in model H1 (sim/handpen, read-only, through opt/inertial, read-only).

H1 (sim/handpen/core.py, opt/inertial extensions): rigid Rev H pen with rotation, two-zone grip calibrated to HAP-26 at a
grip split r_rot, hand mass on the arm spring, LuGre paper friction at the skid ring and the ball, the Rev H nose as H1's
kinematic stage (+/-3 mm, 80 Hz servo), and one device: an active reaction mass ('rm'), a scissored-pair CMG per axis
('cmg': torque 2 H cos(delta) delta_dot with gimbal angle, rate and servo limits), a passive rotor ('gyro'), or a fixed
mass ('mass').  This module adds, in its own package:
  * a tracker-driven torque feed-forward for the CMG (the phasor model inverse of addon.ff_phasor, written for torques);
  * the same feed-forward for the reaction mass with a flexure-aware stroke cap (ff_force; addon.ff_phasor caps the coil
    force at frac m w^2 X, which under-uses the stroke below about 8 Hz);
  * the evaluation cascade of opt/inertial/addon_eval.py for any device: tracker on the device-neutral pen -> device
    feed-forward -> tracker re-estimated on the closed-loop motion -> the nose on what is left;
  * letter-scale steering runs (open-loop sinusoids and single-stroke pulses at the device's limit);
  * gyroscopic-stiffening runs (passive rotor, with and without its mass);
  * the pseudo-force cue's side effects on the ink (asymmetric force pulses at 40-75 Hz).
Every result is a SIMULATION on synthetic writing and tremor.  Nothing was measured.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, Optional, Sequence

import numpy as np

import sim.handpen  # noqa: F401  (numba cache location)
from sim.handpen import evaluate as HE
from sim.handpen import model as HM
from sim.handpen.params import Device
from opt.inertial import addon as AD
from opt.inertial import revh as RH
from opt.inertial import scen as SC
from opt.inertial import tracker as TK
from opt.inertial.linear_ext import LinearExt

from . import params as P

REVH_TRACKER = os.path.join(P.ROOT, "results", "opt", "inertial_tracker_revh.json")
DRV_W = 0.012          # drivers and sensors of an active module (ASSUMPTION, as opt/inertial)


def revh_akf():
    """The Rev H tracker setting (results/opt/inertial_tracker_revh.json, ParEGO on training seeds; read-only)."""
    return json.load(open(REVH_TRACKER))["params"]


# ------------------------------------------------------------------------------------------------ devices
def h1_device(s: Dict) -> Device:
    """H1 device from an optimiser summary (endcap/optimise.summarize)."""
    c = s["class"]
    if c == "LRM2":
        m_r = s["moving_mass_g"] * 1e-3
        f_c = 5.0
        k_c = m_r * (2 * math.pi * f_c) ** 2
        return Device(kind="rm", m=m_r, z=P.Z_CAP, stroke=(s["X"], s["X"], 0.0), F_max=(s["F_act"], s["F_act"], 0.0),
                      k_c=k_c, c_c=2 * 0.7 * math.sqrt(k_c * m_r), Km=s["Km"], added_fixed=(s["mass_g"] - s["moving_mass_g"]) * 1e-3,
                      label=f"end-cap LRM {s['moving_mass_g']:.1f} g moving, +/-{s['X'] * 1e3:.2f} mm, {s['mass_g']:.1f} g total")
    if c in ("SP2", "SP1", "DG1", "DG2", "PL2"):
        kx = {"SP2": (2.0, 2.0), "SP1": (2.0, 0.0), "DG1": (1.0, 1.0), "DG2": (2.0, 2.0), "PL2": (1.73, 1.0)}[c]
        k_eq = min(k for k in kx if k > 0)
        H_eq = k_eq * s["H"] / 2.0                          # H1 models a scissored pair per axis: torque 2 H' delta_dot
        axes = (1, 1) if kx[1] > 0 else (1, 0)
        return Device(kind="cmg", m=0.0, z=P.Z_CAP, H=H_eq, delta_max=float(min(s["x"]["delta"], 0.5 if c == "PL2" else 9.0)),
                      rate_max=float(P.GIMBAL_DRIVE["rate_max"]), axes=axes, added_fixed=s["mass_g"] * 1e-3,
                      label=f"end-cap CMG {c} ({s['choice'][1]}), H {s['H'] * 1e3:.2f} mN m s per rotor, {s['mass_g']:.1f} g")
    if c == "PG":
        return Device(kind="gyro", m=0.0, z=P.Z_CAP, H=s["H"], added_fixed=s["mass_g"] * 1e-3,
                      label=f"passive gyroscope H {s['H'] * 1e3:.2f} mN m s, {s['mass_g']:.1f} g")
    raise KeyError(c)


def weight_device(m, z=P.Z_CAP):
    return Device(kind="mass", m=m, z=z, stroke=(0, 0, 0), label=f"passive weight {m * 1e3:.1f} g at {z * 1e3:.0f} mm")


def gyro_device(H, m_fix):
    return Device(kind="gyro", m=0.0, z=P.Z_CAP, H=max(H, 1e-12), added_fixed=m_fix,
                  label=f"passive rotor H {H * 1e3:.2f} mN m s, +{m_fix * 1e3:.1f} g")


# ------------------------------------------------------------------------------------------------ CMG torque feed-forward
def torque_plant(dev: Device, r_rot_model=0.5, f=np.arange(2.0, 16.01, 0.25)):
    """Tip response (page x, y) per unit torque on (tau_t2, tau_t1) from the linear model at the MODEL split (CALC)."""
    lm = LinearExt(RH.config_B(RH.RevH(), r_rot=r_rot_model, device=dev))
    G = np.zeros((len(f), 2, 2), complex)
    for i, fi in enumerate(f):
        w = 2 * np.pi * fi
        for j, nm in enumerate(("tau_t2", "tau_t1")):
            G[i, :, j] = lm.solve(w, lm.input_vector(nm).astype(complex))[0:2]
    return f, G


def cmg_cap(dev: Device, f, margin):
    w = 2 * np.pi * np.asarray(f, float)
    return margin * 2 * dev.H * np.minimum(dev.rate_max, w * dev.delta_max)


def ff_torque(dh_ticks, f_ticks, dev: Device, r_rot_model=0.5, Ts=5e-4, margin=0.7, gain=1.0, plant=None):
    """Tracker-driven torque feed-forward: tau = Re(H) e(t) - Im(H) e(t - T/4), H = -G(jw)^-1 at the tracked frequency
    (pseudo-inverse for a one-axis cluster), capped at margin x the CMG limit (as addon.ff_phasor for forces)."""
    f, G = plant if plant is not None else torque_plant(dev, r_rot_model)
    if dev.axes[1] == 0:
        H = np.array([-np.linalg.pinv(g[:, 0:1]) for g in G])            # (nf, 1, 2)
        H = np.concatenate([H, np.zeros_like(H)], axis=1)               # second torque input unused
    else:
        H = np.array([-np.linalg.inv(g) for g in G])
    e = np.asarray(dh_ticks, float)
    fq = np.clip(np.asarray(f_ticks, float), f[0], f[-1])
    n = len(e)
    kq = np.clip(np.round(1.0 / (4.0 * fq * Ts)).astype(int), 1, None)
    idx = np.clip(np.arange(n) - kq, 0, None)
    eq = e[idx]
    Hr = np.stack([np.interp(fq, f, H[:, i, j].real) for i in range(2) for j in range(2)], axis=1).reshape(n, 2, 2)
    Hi = np.stack([np.interp(fq, f, H[:, i, j].imag) for i in range(2) for j in range(2)], axis=1).reshape(n, 2, 2)
    u = np.einsum("nij,nj->ni", Hr, e) - np.einsum("nij,nj->ni", Hi, eq)
    cap = cmg_cap(dev, fq, margin)
    mag = np.max(np.abs(u), axis=1)
    sc = np.where(mag > cap, cap / np.maximum(mag, 1e-12), 1.0)
    return gain * u * sc[:, None]


# ------------------------------------------------------------------------------------------------ reaction-mass feed-forward
def rm_coil_cap(dev: Device, f, frac):
    """Coil-force amplitude that drives the slug through frac x its stroke on its flexure (k_c, c_c), capped at F_max:
    frac X |k_c - m w^2 + j c_c w| (CALC; the pen's own motion is neglected).  Below the flexure resonance most of this
    force goes into the spring; the net force on the pen stays at most frac m w^2 X."""
    w = 2 * np.pi * np.asarray(f, float)
    dyn = np.sqrt((dev.k_c - dev.m * w * w) ** 2 + (dev.c_c * w) ** 2)
    return np.minimum(dev.F_max[0], frac * dev.stroke[0] * dyn)


def ff_force(dh_ticks, f_ticks, d: RH.RevH, dev: Device, r_rot_model=0.5, Ts=5e-4, stroke_frac=0.7, gain=1.0, tables=None):
    """The Rev H phasor feed-forward (opt/inertial/addon.ff_phasor: u = Re(H) e(t) - Im(H) e(t - T/4), H = -G_tip^-1 at the
    MODEL split), with one change: the cap is the coil force that uses stroke_frac of the stroke on the flexure
    (rm_coil_cap), instead of stroke_frac m w^2 X, which under-uses the stroke below about 8 Hz (1.2x at 6 Hz, 1.8x at
    4 Hz for a 5 Hz flexure with damping 0.7; CALC)."""
    f, Gt, _ = tables if tables is not None else AD.plant_tables(d, dev, r_rot=r_rot_model)
    H = np.array([-np.linalg.pinv(G) for G in Gt])
    e = np.asarray(dh_ticks, float)
    fq = np.clip(np.asarray(f_ticks, float), f[0], f[-1])
    n = len(e)
    kq = np.clip(np.round(1.0 / (4.0 * fq * Ts)).astype(int), 1, None)
    idx = np.clip(np.arange(n) - kq, 0, None)
    eq = e[idx]
    Hr = np.stack([np.interp(fq, f, H[:, i, j].real) for i in range(2) for j in range(2)], axis=1).reshape(n, 2, 2)
    Hi = np.stack([np.interp(fq, f, H[:, i, j].imag) for i in range(2) for j in range(2)], axis=1).reshape(n, 2, 2)
    u = np.einsum("nij,nj->ni", Hr, e) - np.einsum("nij,nj->ni", Hi, eq)
    cap = rm_coil_cap(dev, fq, stroke_frac)
    mag = np.max(np.abs(u), axis=1)
    sc = np.where(mag > cap, cap / np.maximum(mag, 1e-12), 1.0)
    return gain * u * sc[:, None]


# ------------------------------------------------------------------------------------------------ tremor cascade
class TremorEval:
    """Rev H nose alone, and nose + end-cap device, with the Rev H tracker (causal), on one grip split."""

    def __init__(self, dev: Optional[Device], r_rot=0.5, akf=None, gain=1.0, margin=0.7, model_split=0.5,
                 Km=None, J_gimbal=None, eta_gimbal=None):
        self.d = RH.RevH()
        self.dev = dev
        self.r_rot = r_rot
        self.akf = akf if akf is not None else revh_akf()
        self.cfg0 = RH.config_B(self.d, r_rot=r_rot)
        self.cfgD = RH.config_B(self.d, r_rot=r_rot, device=dev) if dev is not None else None
        self.gain, self.margin, self.model_split = gain, margin, model_split
        self.Km = Km
        self.J_gimbal = J_gimbal
        self.eta_gimbal = eta_gimbal or P.GIMBAL_DRIVE["eta"]
        self._ref = {}
        self._plant = None
        if dev is not None and dev.kind == "cmg":
            self._plant = torque_plant(dev, model_split)
        if dev is not None and dev.kind == "rm":
            self._plant = AD.plant_tables(self.d, dev, r_rot=model_split)

    def ref(self, seed, key, writer="lognormal"):
        k = (seed, key, writer)
        if k not in self._ref:
            cfg = self.cfg0 if key == "0" else self.cfgD
            self._ref[k] = HM.run(SC.get(seed, None, writer), cfg, rec_hz=TK.REC_HZ)
        return self._ref[k]

    def est(self, res, sc, seed):
        dh, info, _ = TK.estimate(res, sc, seed=seed + 7000, body="pen", params=self.akf)
        return dh, info

    def device_uff(self, dh, info, n):
        dev = self.dev
        u = np.zeros((n, 3))
        if dev.kind == "rm":
            ff = ff_force(dh, info["f_est"], self.d, dev, r_rot_model=self.model_split, stroke_frac=self.margin, gain=self.gain,
                          tables=self._plant)
            u[:, 0:2] = TK.to_steps(ff, n)
        elif dev.kind == "cmg":
            ff = ff_torque(dh, info["f_est"], dev, margin=self.margin, gain=self.gain, plant=self._plant)
            u[:, 0:2] = TK.to_steps(ff, n)
        return u

    def power(self, res):
        """Actuation power (W) from the simulated forces or gimbal motion (CALC on SIM), excluding spin power."""
        dev = self.dev
        sel = (res["t"] > 0.5) & (res["contact"] > 0)
        if dev.kind == "rm":
            F = np.column_stack([res["Fd1"], res["Fd2"]])[sel]
            return float(np.sum(np.mean(F ** 2, axis=0)) / (self.Km or dev.Km) ** 2) + DRV_W
        if dev.kind == "cmg":
            rate = np.column_stack([res["dr1"], res["dr2"]])[sel]
            acc = np.column_stack([res["ddl1"], res["ddl2"]])[sel]
            J_g = self.J_gimbal or 0.0
            return float(np.sum(np.mean(np.abs(J_g * acc * rate), axis=0)) / self.eta_gimbal) + DRV_W
        return 0.0

    def case(self, seed, f0, amp, kind="trans", writer="lognormal", active=True, oracle=False) -> Dict:
        tr = SC.tremor(f0, amp, kind) if amp > 0 else None
        sc = SC.get(seed, tr, writer)
        n = len(sc.t)
        ref0 = self.ref(seed, "0", writer)
        un0 = HM.run(sc, self.cfg0, rec_hz=TK.REC_HZ)
        base = HE.compare(un0, ref0)["e_rms_um"]
        out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "kind": kind, "r_rot": self.r_rot, "unmod0_um": base}
        dh0, info0 = self.est(un0, sc, seed)
        rn = HM.run(sc, self.cfg0.replace(stage=True, stage_src=1), clean=TK.to_steps(dh0, n), rec_hz=TK.REC_HZ)
        out["nose"] = HE.compare(rn, ref0)["e_rms_um"] / base
        if self.dev is None:
            return out
        refD = self.ref(seed, "D", writer)
        unD = HM.run(sc, self.cfgD, rec_hz=TK.REC_HZ)
        out["dev_passive"] = HE.compare(unD, refD)["e_rms_um"] / base
        dhD, infoD = self.est(unD, sc, seed)
        rnD = HM.run(sc, self.cfgD.replace(stage=True, stage_src=1), clean=TK.to_steps(dhD, n), rec_hz=TK.REC_HZ)
        out["nose+passive"] = HE.compare(rnD, refD)["e_rms_um"] / base
        if active and self.dev.kind in ("rm", "cmg"):
            u = self.device_uff(dhD, infoD, n)
            r = HM.run(sc, self.cfgD, uff=u, rec_hz=TK.REC_HZ)
            m = HE.compare(r, refD)
            out["dev"] = m["e_rms_um"] / base
            dh2, _ = self.est(r, sc, seed)
            rn2 = HM.run(sc, self.cfgD.replace(stage=True, stage_src=1), uff=u, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
            m2 = HE.compare(rn2, refD)
            out["nose+dev"] = m2["e_rms_um"] / base
            out["P_act_W"] = self.power(rn2)
            if self.dev.kind == "rm":
                out["stroke_pk_mm"] = m2["dev_stroke_peak_mm"][:2]
                out["F_rms_N"] = m2["dev_force_rms_N"][:2]
            else:
                out["gimbal_pk_rad"] = m2["cmg_gimbal_peak_rad"]
                out["torque_rms_mNm"] = m2["cmg_torque_rms_mNm"]
                out["rate_rms_rad_s"] = m2["cmg_rate_rms_rad_s"]
            out["nose_sat_frac"] = m2["q_sat_frac"]
        if oracle and self.dev.kind in ("rm", "cmg"):
            refR2 = HM.run(SC.get(seed), self.cfgD)
            un2 = HM.run(sc, self.cfgD)
            best = None
            for pct in (60.0, 95.0):
                r_, u_, h_ = HM.ilc_oracle(sc, self.cfgD, refR2, n_iter=6, pct=pct, margin=1.0)
                e = HE.compare(r_, refR2)["e_rms_um"]
                best = e if best is None else min(best, e)
            out["dev_oracle"] = best / HE.compare(un2, refR2)["e_rms_um"] * out["dev_passive"]
        return out

    def distortion(self, seed, writer="lognormal"):
        """False correction of the device + nose cascade on tremor-free writing (closed loop, against the device pen)."""
        sc0 = SC.get(seed, None, writer)
        n = len(sc0.t)
        refD = self.ref(seed, "D", writer)
        dhD, infoD = self.est(refD, sc0, seed)
        u = self.device_uff(dhD, infoD, n)
        r = HM.run(sc0, self.cfgD, uff=u, rec_hz=TK.REC_HZ)
        dh2, _ = self.est(r, sc0, seed)
        rn2 = HM.run(sc0, self.cfgD.replace(stage=True, stage_src=1), uff=u, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
        return HE.distortion(rn2, refD)["detrended_rms_um"]


# ------------------------------------------------------------------------------------------------ steering ('can inertia write')
def _hold_scenario(duration=4.0):
    from sim.pensim import scenarios
    sc = scenarios.static_hold(duration=duration)
    sc.psi_disp = np.zeros(len(sc.t))
    sc.tremor_obj = None
    return sc


def steer_cfg(dev, r_rot, hand_scale=1.0, voluntary=False):
    cfg = RH.config_B(RH.RevH(), r_rot=r_rot, device=dev)
    if hand_scale != 1.0:
        cfg = cfg.replace(k_nib=cfg.k_nib * hand_scale, b_nib=cfg.b_nib * hand_scale, k_arm=cfg.k_arm * hand_scale,
                          b_arm=cfg.b_arm * hand_scale)
    if voluntary:
        cfg = cfg.replace(voluntary=True, vc_hz=P.VOLUNTARY["vc_hz"], vc_delay=P.VOLUNTARY["vc_delay"])
    return cfg


def device_limit(dev: Device, f, margin=0.9):
    """Sinusoidal command amplitude at the device limit (CALC): for a reaction mass the COIL force that drives the slug
    through margin x its stroke on its flexure (the net force on the pen is then about margin m w^2 X); for a CMG the
    torque 2 H' min(rate, w delta)."""
    w = 2 * np.pi * f
    if dev.kind == "rm":
        return float(rm_coil_cap(dev, f, margin))
    if dev.kind == "cmg":
        return margin * 2 * dev.H * min(dev.rate_max, w * dev.delta_max)
    return 0.0


def steer_case(dev: Device, r_rot, f, axis=0, scenario="write", seed=300, margin=0.9, hand_scale=1.0, voluntary=False,
               t_on=1.0, dur=3.0):
    """Open-loop sinusoid at the device limit along one input axis (0: tilt plane -> tip along x; 1: sideways -> y) from
    t_on for dur seconds.  Returns the tip (ink) displacement caused by the device: amplitude of the ink difference to the
    same run without the command, in a band around f (sqrt(2) x RMS), and its peak."""
    sc = SC.get(seed) if scenario == "write" else _hold_scenario(t_on + dur + 0.5)
    cfg = steer_cfg(dev, r_rot, hand_scale, voluntary)
    n = len(sc.t)
    t = np.arange(n) * HM.DT
    A = device_limit(dev, f, margin)
    u = np.zeros((n, 3))
    win = (t >= t_on) & (t < t_on + dur)
    ramp = np.clip((t - t_on) / 0.1, 0, 1) * np.clip((t_on + dur - t) / 0.1, 0, 1)
    u[win, axis] = A * np.sin(2 * np.pi * f * (t[win] - t_on)) * ramp[win]
    ref = HM.run(sc, cfg, rec_hz=TK.REC_HZ)
    r = HM.run(sc, cfg, uff=u, rec_hz=TK.REC_HZ)
    k = min(len(r["t"]), len(ref["t"]))
    tt = r["t"][:k]
    e = r.ink()[:k] - ref.ink()[:k]
    sel = (tt > t_on + 0.3) & (tt < t_on + dur - 0.1) & (r["contact"][:k] > 0) & (ref["contact"][:k] > 0)
    fs = 1.0 / (tt[1] - tt[0])
    eb = HE.band(e, fs, max(0.3, 0.5 * f), 2.0 * f)
    amp = float(np.sqrt(2.0) * np.sqrt(np.mean(np.sum(eb[sel] ** 2, axis=1)))) if sel.any() else float("nan")
    pk = float(np.max(np.linalg.norm(e[sel], axis=1))) if sel.any() else float("nan")
    ball = r.ball()[:k] - ref.ball()[:k]
    slide = float(np.mean(np.linalg.norm(np.gradient(ref.ball()[:k], tt, axis=0)[sel], axis=1))) if sel.any() else float("nan")
    return {"f": f, "axis": axis, "scenario": scenario, "r_rot": r_rot, "hand_scale": hand_scale, "voluntary": voluntary,
            "command_amp": A, "tip_amp_mm": amp * 1e3, "tip_peak_mm": pk * 1e3,
            "ball_amp_mm": float(np.sqrt(2) * np.sqrt(np.mean(np.sum(HE.band(ball, fs, max(0.3, 0.5 * f), 2 * f)[sel] ** 2, axis=1)))) * 1e3 if sel.any() else float("nan"),
            "ref_tip_speed_mm_s": slide * 1e3}


def pulse_case(dev: Device, r_rot, scenario="hold", seed=300, T_pulse=0.15, T_reset=0.55, axis=0, hand_scale=1.0,
               voluntary=False, t_on=1.0):
    """Single stroke: the CMG gimbals swing across their range in T_pulse (constant torque at the rate limit or less),
    then return in T_reset (Walker et al. 2018's asymmetric pulse, HAP-82); an LRM crosses its stroke with a bang-bang
    force.  Returns the tip displacement time course summary: peak during the pulse and the offset 0.5 s after the reset."""
    sc = SC.get(seed) if scenario == "write" else _hold_scenario(t_on + T_pulse + T_reset + 1.2)
    cfg = steer_cfg(dev, r_rot, hand_scale, voluntary)
    n = len(sc.t)
    t = np.arange(n) * HM.DT
    u = np.zeros((n, 3))
    if dev.kind == "cmg":
        rate = min(dev.rate_max, 2 * dev.delta_max / T_pulse)
        tp = 2 * dev.H * rate
        tr = -tp * T_pulse / T_reset
        # pre-position the gimbals at -delta_max: a slow ramp before the pulse, not counted
        u[(t >= t_on - 0.6) & (t < t_on - 0.1), axis] = -2 * dev.H * (dev.delta_max / 0.5)
        u[(t >= t_on) & (t < t_on + T_pulse), axis] = tp
        u[(t >= t_on + T_pulse) & (t < t_on + T_pulse + T_reset), axis] = tr
        cmd = tp
    else:
        F = min(dev.F_max[0], 0.9 * (4 * dev.m * dev.stroke[0] / (T_pulse / 2) ** 2 + dev.k_c * dev.stroke[0]))
        u[(t >= t_on) & (t < t_on + T_pulse / 2), axis] = F
        u[(t >= t_on + T_pulse / 2) & (t < t_on + T_pulse), axis] = -F
        cmd = F
    ref = HM.run(sc, cfg, rec_hz=TK.REC_HZ)
    r = HM.run(sc, cfg, uff=u, rec_hz=TK.REC_HZ)
    k = min(len(r["t"]), len(ref["t"]))
    tt = r["t"][:k]
    e = (r.ink()[:k] - ref.ink()[:k])
    during = (tt >= t_on) & (tt < t_on + T_pulse + 0.05)
    after = (tt >= t_on + T_pulse + T_reset + 0.4) & (tt < t_on + T_pulse + T_reset + 0.6)
    before = (tt >= t_on - 0.05) & (tt < t_on)
    e0 = e[before].mean(axis=0) if before.any() else np.zeros(2)
    pk = float(np.max(np.linalg.norm(e[during] - e0, axis=1))) if during.any() else float("nan")
    off = float(np.linalg.norm(e[after].mean(axis=0) - e0)) if after.any() else float("nan")
    return {"scenario": scenario, "r_rot": r_rot, "cmd": cmd, "tip_peak_mm": pk * 1e3, "tip_offset_after_mm": off * 1e3,
            "trace_t": tt[(tt > t_on - 0.2) & (tt < t_on + 1.2)][::20].tolist(),
            "trace_mm": (np.linalg.norm(e - e0, axis=1)[(tt > t_on - 0.2) & (tt < t_on + 1.2)][::20] * 1e3).tolist()}


# ------------------------------------------------------------------------------------------------ pseudo-force cue side effects
def cue_case(r_rot=0.5, f_cue=40.0, F0=0.5, phase_deg=0.0, harmonic=True, m_v=5e-3, scenario="write", seed=300,
             nose_cancel=False, t_on=1.5, dur=1.0):
    """Asymmetric vibration F(t) = F0 [sin(w t) + sin(2 w t + phi)] (Tanabe's waveform, HAP-80/85) applied between a small
    moving mass m_v (a Force Reactor-class vibrator, HAP-86) and the pen at the end-cap, for dur seconds.  Returns the
    grip-point acceleration amplitude at f_cue (what the fingers feel), the ink jitter (20-300 Hz RMS) and the net ink drift
    over the cue (mean offset, < 5 Hz), each against the same run without the cue.  With nose_cancel the nose cancels the
    cue's known effect on the tip (upper bound: the true ball deviation it causes)."""
    sc = SC.get(seed) if scenario == "write" else _hold_scenario(t_on + dur + 1.0)
    k_c = m_v * (2 * np.pi * 15.0) ** 2
    dev = Device(kind="rm", m=m_v, z=P.Z_CAP, stroke=(3e-3, 3e-3, 0.0), F_max=(10.0, 10.0, 0.0), k_c=k_c,
                 c_c=2 * 0.3 * math.sqrt(k_c * m_v), added_fixed=0.0, label="cue vibrator")
    cfg = RH.config_B(RH.RevH(), r_rot=r_rot, device=dev)
    n = len(sc.t)
    t = np.arange(n) * HM.DT
    w = 2 * np.pi * f_cue
    ph = math.radians(phase_deg)
    win = (t >= t_on) & (t < t_on + dur)
    tt_ = t[win] - t_on
    F = F0 * (np.sin(w * tt_) + (np.sin(2 * w * tt_ + ph) if harmonic else 0.0))
    ramp = np.clip(tt_ / 0.02, 0, 1) * np.clip((dur - tt_) / 0.02, 0, 1)
    u = np.zeros((n, 3))
    u[win, 0] = F * ramp
    ref = HM.run(sc, cfg, rec_hz=TK.REC_HZ)
    if nose_cancel:
        r0 = HM.run(sc, cfg, uff=u)
        dball = HM.clean_at_sim_rate(r0, n) - HM.clean_at_sim_rate(HM.run(sc, cfg), n)
        r = HM.run(sc, cfg.replace(stage=True, stage_src=1), uff=u, clean=dball, rec_hz=TK.REC_HZ)
    else:
        r = HM.run(sc, cfg, uff=u, rec_hz=TK.REC_HZ)
    k = min(len(r["t"]), len(ref["t"]))
    tt = r["t"][:k]
    fs = 1.0 / (tt[1] - tt[0])
    sel = (tt > t_on + 0.1) & (tt < t_on + dur - 0.05)
    g = np.column_stack([r["gfx"][:k], r["gfy"][:k], r["gfz"][:k]]) - np.column_stack([ref["gfx"][:k], ref["gfy"][:k], ref["gfz"][:k]])
    acc = np.gradient(np.gradient(g, tt, axis=0), tt, axis=0)
    accb = HE.band(acc, fs, 0.7 * f_cue, 2.6 * f_cue)
    a_amp = float(np.sqrt(2) * np.sqrt(np.mean(np.sum(accb[sel] ** 2, axis=1))))
    a_pk = float(np.max(np.linalg.norm(accb[sel], axis=1)))
    e = r.ink()[:k] - ref.ink()[:k]
    jit = float(np.sqrt(np.mean(np.sum(HE.band(e, fs, 20.0, 300.0)[sel] ** 2, axis=1))))
    drift = float(np.linalg.norm(HE.band(e, fs, None, 5.0)[sel].mean(axis=0)))
    return {"f_cue": f_cue, "F0_N": F0, "phase_deg": phase_deg, "harmonic": harmonic, "r_rot": r_rot, "scenario": scenario,
            "nose_cancel": nose_cancel, "grip_acc_amp_m_s2": a_amp, "grip_acc_peak_m_s2": a_pk, "ink_jitter_um": jit * 1e6,
            "ink_drift_um": drift * 1e6}
