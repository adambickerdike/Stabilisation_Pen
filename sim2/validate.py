r"""Literature validation and hand-model studies of simulator v2 (SIMULATION and CALCULATION; the comparators are
ledger rows of docs/evidence.csv or sources opened by study V, cited by id in docs/sim_v2.md).

  writer_kinematics  speed, velocity spectrum, stroke durations and the two-thirds power law of the synthetic writers
                     (sigma-lognormal, stabpen.signals; aiguide glyph writer) against CON-20, CON-08, CON-24, CON-25,
                     CON-27
  arm_case           one tremor case in the articulated arm (tremor torques at the forearm and wrist): unmodified ink
                     error and the oracle ratio of the Rev H nose, next to the H1 hand on the same writing
  tremor_spectra     pen-tip and hand tremor of the ET, PD and physiological profiles through the arm model: peak
                     frequency, band amplitude, harmonic content, rest/action gating
  wrist_resonance    mechanical resonance of the hand-wrist in the arm model and its shift with a 300 g load (the
                     mechanical-reflex component falls with inertial loading: Hess & Pullman 2012; Elble 2003)
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

from . import builder as B
from . import params as P
from . import sim as S


# ============================================================================================ writer kinematics
def _kin(t, xy, down, fs_out=1000.0):
    """Kinematics of a pen path: returns dict of arrays at fs_out (low-passed 20 Hz)."""
    dt = float(t[1] - t[0])
    step = max(int(round(1.0 / (fs_out * dt))), 1)
    tt = t[::step]
    P_ = xy[::step]
    dn = down[::step]
    sos = butter(4, 20.0, fs=fs_out, output="sos")
    P_ = sosfiltfilt(sos, P_, axis=0)
    v = np.gradient(P_, 1.0 / fs_out, axis=0)
    a = np.gradient(v, 1.0 / fs_out, axis=0)
    sp = np.hypot(v[:, 0], v[:, 1])
    cross = v[:, 0] * a[:, 1] - v[:, 1] * a[:, 0]
    kappa = np.abs(cross) / np.maximum(sp, 1e-9) ** 3
    return {"t": tt, "v": v, "speed": sp, "kappa": kappa, "down": dn}


def _strokes(speed, down, fs, min_sep=0.04):
    """Stroke durations: intervals between consecutive speed minima (pen down), minima at least min_sep apart."""
    from scipy.signal import find_peaks
    pk, _ = find_peaks(-speed, distance=max(int(min_sep * fs), 1), prominence=0.2 * np.median(speed[down]) if np.any(down) else None)
    pk = [p for p in pk if down[p]]
    d = np.diff(pk) / fs
    return d[(d > 0.02) & (d < 1.0)]


def writer_kinematics(seeds=tuple(range(300, 310)), writer="lognormal", duration=5.0) -> Dict:
    from opt.inertial import scen as SC
    rows = []
    speeds, strokes, P_all, F_all = [], [], [], None
    beta_x, beta_y = [], []
    for seed in seeds:
        sc = SC.get(seed, None, writer=writer, duration=duration)
        down = np.asarray(sc.fpush) > 0.5 * float(np.max(sc.fpush))
        k = _kin(np.asarray(sc.t), np.asarray(sc.intended), down)
        fs = 1000.0
        m = k["down"] & (k["t"] > 0.3)
        speeds.append(k["speed"][m])
        strokes.append(_strokes(k["speed"], k["down"], fs))
        f, Pxx = welch(k["v"][m], fs=fs, nperseg=min(2048, int(np.sum(m))), axis=0)
        Ps = Pxx.sum(axis=1)
        F_all = f
        P_all.append(Ps)
        # power law: log(angular speed) = log k + beta log(curvature), angular speed = v kappa (CON-27: beta = 2/3)
        sel = m & (k["speed"] > 5e-3) & (k["kappa"] > 1.0 / 0.05) & (k["kappa"] < 1.0 / 0.3e-3)
        if np.sum(sel) > 50:
            x = np.log(k["kappa"][sel])
            y = np.log(k["speed"][sel] * k["kappa"][sel])
            beta_x.append(float(np.polyfit(x, y, 1)[0]))
    sp = np.concatenate(speeds)
    st = np.concatenate(strokes)
    Pm = np.mean(np.array(P_all), axis=0)
    cum = np.cumsum(Pm) / np.sum(Pm)
    fq = lambda q: float(F_all[np.searchsorted(cum, q)])
    band = lambda lo, hi: float(np.sum(Pm[(F_all >= lo) & (F_all < hi)]) / np.sum(Pm))
    return {"writer": writer, "seeds": list(seeds), "duration_s": duration,
            "speed_mm_s": {"mean": float(sp.mean() * 1e3), "median": float(np.median(sp) * 1e3),
                           "p95": float(np.percentile(sp, 95) * 1e3)},
            "stroke_duration_ms": {"median": float(np.median(st) * 1e3) if len(st) else None,
                                   "iqr": [float(np.percentile(st, 25) * 1e3), float(np.percentile(st, 75) * 1e3)] if len(st) else None,
                                   "n": int(len(st))},
            "velocity_spectrum": {"peak_Hz": float(F_all[np.argmax(Pm[1:]) + 1]), "f50_Hz": fq(0.5), "f90_Hz": fq(0.9),
                                  "f95_Hz": fq(0.95), "f99_Hz": fq(0.99), "share_0_3Hz": band(0, 3), "share_3_12Hz": band(3, 12),
                                  "share_8_12Hz": band(8, 12), "share_above_12Hz": band(12, 500)},
            "power_law_beta": {"mean": float(np.mean(beta_x)) if beta_x else None,
                               "sd": float(np.std(beta_x)) if beta_x else None, "n": len(beta_x)},
            "spectrum_Hz": F_all[F_all <= 30].tolist(), "spectrum_rel": (Pm[F_all <= 30] / Pm.max()).tolist()}


# ============================================================================================ arm model cases
def arm_config(arm: Optional[P.Arm] = None, **kw) -> P.Config:
    return P.Config(hand_model="arm", arm=arm or P.calibrated_arm(), **kw)


def arm_tremor(pm, sc, profile, seed: int, cal: Optional[Dict] = None):
    from . import tremor as TR
    cal = cal or TR.calibrate(pm, profile)
    t = np.arange(len(sc.t)) * float(sc.t[1] - sc.t[0])
    speed = np.hypot(*np.gradient(np.asarray(sc.intended), float(sc.t[1] - sc.t[0]), axis=0).T)
    tq = TR.torques(t, profile, cal["A0"], np.random.default_rng(seed + 5000), speed=speed)
    return tq, cal


def arm_case(pm, seed: int, profile, duration: float = 3.0, controllers=("oracle",), cache: Optional[Dict] = None) -> Dict:
    """Unmodified ink error, tremor band amplitude and the oracle ratio for one case in the arm model."""
    from opt.inertial import scen as SC
    from sim.handpen import evaluate as HE
    sc = SC.get(seed, None, duration=duration)
    key = ("ref", seed, duration)
    if cache is not None and key in cache:
        ref = cache[key]
    else:
        ref = S.run(pm, sc)
        if cache is not None:
            cache[key] = ref
    tq, cal = arm_tremor(pm, sc, profile, seed)
    un = S.run(pm, sc, arm_tremor=tq)
    mu = HE.compare(un, ref)
    band = band_amplitude(un, ref)
    out = {"seed": seed, "kind": profile.kind, "f0": profile.f0, "amp_tip_target_mm": profile.amp_tip * 1e3,
           "unmod_e_rms_um": mu["e_rms_um"], "unmod_band_um": mu["e_band_rms_um"], "ink_band": band, "A0": cal["A0"]}
    n_ticks = int(math.ceil(len(sc.t) / 20))
    for c in controllers:
        if c == "oracle":
            r = S.run(pm, sc, S.RunOptions(source="oracle", clean=S.clean_ticks(ref, n_ticks)), arm_tremor=tq)
            m = HE.compare(r, ref)
            out["oracle"] = {"ratio": m["e_rms_um"] / mu["e_rms_um"], "band_ratio": m["e_band_rms_um"] / mu["e_band_rms_um"],
                             "q_sat_frac": m["q_sat_frac"], "P_cu_W": float(np.mean(r["Pcu"][r["t"] > 0.5]))}
    return out


def band_amplitude(r, ref, lo=3.0, hi=15.0, t0=0.8) -> Dict:
    """Tremor at the ink: band-passed deviation from the reference (rms, p99 and peak frequency within the band)."""
    t = r["t"]
    fs = 1.0 / float(t[1] - t[0])
    d = r.ink() - np.column_stack([np.interp(t, ref["t"], ref.ink()[:, 0]), np.interp(t, ref["t"], ref.ink()[:, 1])])
    sos = butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    db = sosfiltfilt(sos, d, axis=0)[t > t0]
    f, Pxx = welch(d[t > t0], fs=fs, nperseg=min(8192, int(np.sum(t > t0))), axis=0)
    Ps = Pxx.sum(axis=1)
    mb = (f >= lo) & (f <= hi)
    fpk = float(f[mb][np.argmax(Ps[mb])])
    # second harmonic share
    h2 = (f >= 1.8 * fpk) & (f <= 2.2 * fpk)
    h1 = (f >= 0.8 * fpk) & (f <= 1.2 * fpk)
    return {"rms_um": float(np.sqrt(np.mean(np.sum(db ** 2, axis=1))) * 1e6),
            "p99_um": float(np.percentile(np.linalg.norm(db, axis=1), 99) * 1e6), "peak_Hz": fpk,
            "h2_to_h1_power": float(Ps[h2].sum() / max(Ps[h1].sum(), 1e-30))}


def h1_case(seed: int, f0: float, amp: float, duration: float = 3.0, r_rot: float = 0.5, cache=None) -> Dict:
    """The same writing and tremor frequency with H1's hand in sim2 (imposed hand-path tremor of peak amp)."""
    from opt.inertial import scen as SC
    from sim.handpen import evaluate as HE
    cfg = P.Config(hand=P.HandH1(r_rot=r_rot, lock_roll=True))
    key = ("h1pm", r_rot)
    if cache is not None and key in cache:
        pm = cache[key]
    else:
        pm = B.build(cfg)
        if cache is not None:
            cache[key] = pm
    sc = SC.get(seed, SC.tremor(f0, amp), duration=duration)
    sc0 = SC.get(seed, None, duration=duration)
    ref = S.run(pm, sc0)
    un = S.run(pm, sc)
    mu = HE.compare(un, ref)
    n_ticks = int(math.ceil(len(sc.t) / 20))
    r = S.run(pm, sc, S.RunOptions(source="oracle", clean=S.clean_ticks(ref, n_ticks)))
    m = HE.compare(r, ref)
    return {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "unmod_e_rms_um": mu["e_rms_um"], "unmod_band_um": mu["e_band_rms_um"],
            "ink_band": band_amplitude(un, ref), "oracle_ratio": m["e_rms_um"] / mu["e_rms_um"]}


def writer_tracking(pm, seeds=(300, 301), duration=3.0) -> Dict:
    """Tremor-free writing in the arm model: ink against the intended path (mean offset removed), pen-down share,
    writing forces (skid, ball) and the paper drag."""
    from opt.inertial import scen as SC
    rows = []
    for seed in seeds:
        sc = SC.get(seed, None, duration=duration)
        r = S.run(pm, sc)
        t = r["t"]
        it = np.column_stack([np.interp(t, sc.t, sc.intended[:, 0]), np.interp(t, sc.t, sc.intended[:, 1])])
        down = (np.interp(t, sc.t, sc.fpush) > 0.5) & (t > 0.5)
        e = r.ink() - it
        e0 = e[down] - e[down].mean(axis=0)
        rows.append({"seed": seed, "track_rms_um": float(np.sqrt(np.mean(np.sum(e0 ** 2, axis=1))) * 1e6),
                     "mean_offset_um": (e[down].mean(axis=0) * 1e6).tolist(),
                     "contact_frac_when_down": float(np.mean(r["contact"][down] > 0)),
                     "N_skid_mean": float(np.mean(r["Ns"][down])), "N_ball_mean": float(np.mean(r["Nb"][down])),
                     "drag_mean_N": float(np.mean(np.hypot(r["fsx"][down] + r["fbx"][down], r["fsy"][down] + r["fby"][down])))})
    return {"rows": rows}


# ============================================================================================ tremor spectra
def tremor_spectra(pm, seed=300, duration=4.0) -> List[Dict]:
    """ET, PD (rest and action) and physiological profiles through the arm model: ink tremor peak frequency, band
    amplitude and harmonic content; hand (palm) angular-rate amplitude; PD rest gating (writing vs pauses)."""
    from opt.inertial import scen as SC
    from . import tremor as TR
    sc = SC.get(seed, None, duration=duration)
    ref = S.run(pm, sc)
    rows = []
    specs = [("ET", 6.0, 1.0e-3), ("ET", 9.0, 0.5e-3), ("PD_action", 5.0, 1.0e-3), ("PD_rest", 5.0, 1.0e-3),
             ("physio", 10.0, 0.0425e-3)]
    for kind, f0, amp in specs:
        p = TR.profile(kind, f0=f0, amp_tip=amp)
        tq, cal = arm_tremor(pm, sc, p, seed)
        r = S.run(pm, sc, arm_tremor=tq)
        band = band_amplitude(r, ref, lo=2.5 if kind.startswith("PD") else 3.0, hi=15.0)
        # hand angular rate (palm body) in the tremor band: from the recorded hand position is not enough; use the
        # IMU angular rate on the handle as the pen-side gyro (what a device sees)
        t = r["t"]
        w = np.column_stack([r["imuwx"], r["imuwy"], r["imuwz"]])
        w0 = np.column_stack([np.interp(t, ref["t"], ref["imuwx"]), np.interp(t, ref["t"], ref["imuwy"]),
                              np.interp(t, ref["t"], ref["imuwz"])])
        sos = butter(4, [3.0, 15.0], btype="band", fs=1.0 / float(t[1] - t[0]), output="sos")
        wb = sosfiltfilt(sos, w - w0, axis=0)[t > 0.8]
        gate = tq["_gate"]
        rows.append({"kind": kind, "f0": f0, "amp_tip_target_um": amp * 1e6, "A0_N_m": cal["A0"], "ink": band,
                     "pen_rate_rms_deg_s": float(np.degrees(np.sqrt(np.mean(np.sum(wb ** 2, axis=1))))),
                     "gate_mean_writing": float(np.mean(gate[np.asarray(sc.fpush) > 0.5])),
                     "gate_min": float(np.min(gate))})
    return rows


# ============================================================================================ wrist resonance
def wrist_resonance(arm: Optional[P.Arm] = None, extra_mass=0.3, freqs=None) -> Dict:
    """Peak of the pen-tip response to a wrist flexion-extension torque (pen lifted) with and without an extra mass
    on the hand (at the hand's centre of mass; inertia of a point mass about the wrist)."""
    from . import hand as HD
    freqs = np.asarray(freqs if freqs is not None else np.arange(1.0, 30.01, 0.1))
    out = {}
    for lbl, dm in (("nominal", 0.0), ("loaded", extra_mass)):
        a = arm or P.calibrated_arm()
        if dm > 0:
            a = replace(a, m_hand=a.m_hand + dm, J_hand=a.J_hand + dm * a.hand_com ** 2)
        pm = B.build(arm_config(a, nose_on=False))
        H = HD.torque_frf(pm, freqs, joints=("wfe",))["wfe"]
        mag = np.linalg.norm(np.abs(H[:, :2]), axis=1)
        i = int(np.argmax(mag))
        Hj = np.abs(HD.torque_frf(pm, freqs, joints=("wfe",), output="joint")["wfe"][:, 0])
        ij = int(np.argmax(Hj))
        out[lbl] = {"peak_Hz": float(freqs[i]), "peak_mm_per_Nm": float(mag[i] * 1e3), "extra_mass_kg": dm,
                    "joint_peak_Hz": float(freqs[ij]), "joint_peak_rad_per_Nm": float(Hj[ij]),
                    "curve_mm_per_Nm": (mag * 1e3).tolist(), "joint_curve_rad_per_Nm": Hj.tolist(),
                    "k_wrist_fe_N_m_per_rad": a.k_wrist_fe * a.cc, "J_hand_kg_m2": a.J_hand,
                    # CALC: undamped natural frequency and damping ratio of the wrist flexion-extension joint alone
                    "f_n_wrist_Hz": math.sqrt(a.k_wrist_fe * a.cc / a.J_hand) / (2 * math.pi), "zeta_wrist": a.zeta}
    out["freqs_Hz"] = freqs.tolist()
    out["shift_Hz"] = out["loaded"]["peak_Hz"] - out["nominal"]["peak_Hz"]
    out["f_n_shift_Hz"] = out["loaded"]["f_n_wrist_Hz"] - out["nominal"]["f_n_wrist_Hz"]
    return out
