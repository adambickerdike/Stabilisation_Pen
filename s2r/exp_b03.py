"""EXP-B03 virtual bench: actuator coupon K_f, R20, L, coil thermal R_th and C_th.

Truth model (the M1 actuator equations, P-14...P-16, one-node thermal as core.py):
  force at the paddle      F = K_f(T_mag) i,  K_f(T) = K_f20 (1 + alpha_B (T - 20))
  coil                     v = R(T) i + L di/dt + K_f x'
  resistance               R(T) = R20 (1 + alpha_cu (T - 20))
  coil node                C_th T' = i^2 R(T) - (T - T_amb)/R_th

Datasets follow the protocol (bench_protocols.md §4) where it is specific:
  * R20: 4-wire micro-ohmmeter at 20.0 +- 0.5 C (procedure 2);
  * voltage steps recorded with the R7 scope and current probe (the task's "current
    steps"; the protocol's LCR meter is the cross-check). tau = L/R is gain free,
    so L = tau * R with R from the 4-wire reading;
  * blocked force at q = 0 for the protocol currents {-0.6, -0.3, -0.1, 0.1, 0.3, 0.6} A
    from the precision current source, F/T sensor averaged over the hold (procedure 3);
  * back-EMF with the coil open, paddle driven by the shaker at 10-50 Hz, +-0.5 mm,
    velocity by LDV (procedure 5): an estimate of K_f independent of the F/T gain;
  * thermal: constant-current step, coil temperature by resistance (procedure 6).
Identification: least squares with Laplace and bootstrap intervals; the systematic
(type B) bounds of the instruments are combined per GUM (ident.combine).

Evidence status: SIMULATION (data) and CALCULATION (fits).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from . import ident
from . import instruments as ins
from stabpen import params as sp_params

_P = sp_params.load()
ALPHA_CU = float(_P["actuator.alpha_cu"])
ALPHA_B_NOM = float(_P["actuator.alpha_B"])
ALPHA_B_BOUND = 0.0002     # CONFIG actuator.alpha_B declared span -0.0013...-0.0009 about -0.0011; bound used +-0.0002
PROTOCOL_CURRENTS = (-0.6, -0.3, -0.1, 0.1, 0.3, 0.6)   # PROTOCOL EXP-B03 procedure 3
T_BATH_BOUND = 0.5         # PROTOCOL R4: R20 at 20.0 +- 0.5 C
LAB_T = 23.0               # PROTOCOL R1 environment 23 +- 2 C (lab; chamber for thermal steps)
ZERO_RESID = 0.5e-3        # ASSUMPTION residual F/T zero after re-zeroing before each point (N, 1 sigma)
SETTLE = 0.1               # ASSUMPTION s discarded at the start of each hold


@dataclass
class Coupon:
    Kf: float
    R20: float
    L: float
    Rth: float
    Cth: float
    alpha_B: float = ALPHA_B_NOM

    @classmethod
    def from_truth(cls, v: Dict):
        return cls(v["actuator.Kf"], v["actuator.R20"], v["actuator.L"], v["actuator.Rth_coil_amb"],
                   v["actuator.Cth_coil"])


# --------------------------------------------------------------------------- datasets
def ds_r20(c: Coupon, rng, session, n_read=10, noise_scale=1.0):
    T = 20.0 + T_BATH_BOUND * rng.uniform(-1, 1)          # true bath temperature (hidden)
    Rt = c.R20 * (1 + ALPHA_CU * (T - 20.0))
    g = session.gain(ins.MICRO_OHM)
    noise = 2e-5 * c.R20 * noise_scale                  # ASSUMPTION 20 ppm reading noise
    y = g * Rt + noise * rng.standard_normal(n_read)
    return {"R_ohm": y, "T_nominal_C": 20.0, "bench_s": 60.0 + 2.0 * n_read}


def ds_step(c: Coupon, rng, session, n_avg=16, V0=1.0, R_src=0.05, T_rec=300e-6, noise_scale=1.0):
    """Scope record of a voltage step on the blocked coil, averaged n_avg acquisitions."""
    fs = ins.SCOPE_CURRENT.fs
    dt_f = 1.0 / (4 * fs)
    t = np.arange(-20e-6, T_rec, dt_f)
    Tc = LAB_T + rng.uniform(-1, 1)                      # coupon at lab temperature (hidden)
    R = c.R20 * (1 + ALPHA_CU * (Tc - 20.0))
    tr = 100e-9                                          # ASSUMPTION switch rise time
    # exact response of L i' = V_s(t) - (R + R_src) i to a ramp-then-hold source
    Rt = R + R_src
    tau = c.L / Rt
    tp = np.clip(t, 0, None)
    ramp = V0 / (Rt * tr) * (tp - tau * (1 - np.exp(-tp / tau)))
    i_tr = V0 / (Rt * tr) * (tr - tau * (1 - math.exp(-tr / tau)))
    hold = V0 / Rt + (i_tr - V0 / Rt) * np.exp(-(tp - tr) / tau)
    i = np.where(tp <= tr, ramp, hold)
    vs = V0 * np.clip(tp / tr, 0, 1)
    v = vs - R_src * i
    chI = ins.SCOPE_CURRENT.scaled(noise_scale / math.sqrt(n_avg))
    chV = ins.SCOPE_VOLT.scaled(noise_scale / math.sqrt(n_avg))
    # averaging n acquisitions: noise / sqrt(n); quantisation is dithered by the noise, then averaged
    tI, iI = ins.measure(replace_lsb(chI, n_avg), t, i, rng, session)
    tV, vV = ins.measure(replace_lsb(chV, n_avg), t, v, rng, session)
    T_thermo = Tc + session.offset(ins.THERMOCOUPLE) + 0.05 * rng.standard_normal()
    return {"t_s": tI, "i_A": iI, "v_V": vV, "T_coupon_C": T_thermo, "n_avg": n_avg,
            "bench_s": 30.0 + n_avg * 0.01}


def replace_lsb(ch, n_avg):
    """Averaged acquisitions: the effective quantisation of the mean is LSB/sqrt(n) once
    noise dithers it (noise >= LSB/2 here); modelled as a finer step."""
    from dataclasses import replace
    return replace(ch, lsb=ch.lsb / math.sqrt(n_avg))


def coil_heating(c: Coupon, I, hold, T0):
    """Adiabatic-with-loss coil temperature after holding current I for hold seconds."""
    T = T0
    dt = 0.01
    for _ in range(int(hold / dt)):
        P = I * I * c.R20 * (1 + ALPHA_CU * (T - 20.0))
        T += dt / c.Cth * (P - (T - T0) / c.Rth)
    return T


def ds_blocked_force(c: Coupon, rng, session, hold=2.0, n_rep=1, currents=PROTOCOL_CURRENTS, noise_scale=1.0,
                     cool_s=30.0):
    ch = ins.FT_SENSOR
    n = max(int((hold - SETTLE) * ch.fs), 1)
    g_ft = session.gain(ch)
    g_src = session.gain(ins.CURRENT_SOURCE)
    T_mag = LAB_T + rng.uniform(-2, 2)                   # PROTOCOL environment 23 +- 2 C (hidden)
    Kf_T = c.Kf * (1 + c.alpha_B * (T_mag - 20.0))
    rows = []
    for r in range(n_rep):
        for I in rng.permutation(currents):              # PROTOCOL §0.6 randomised order
            Itrue = g_src * I + ins.CURRENT_SOURCE.noise_rms * rng.standard_normal()
            F = Kf_T * Itrue
            y = g_ft * F + ZERO_RESID * rng.standard_normal() + noise_scale * ch.noise_rms * rng.standard_normal(n)
            y = ch.lsb * np.round(y / ch.lsb)
            dT = coil_heating(c, I, hold, LAB_T) - LAB_T
            rows.append({"I_set_A": float(I), "F_mean_N": float(y.mean()), "F_sd_N": float(y.std()),
                         "n": n, "rep": r, "coil_dT_K": float(dT)})
    T_read = T_mag + session.offset(ins.THERMOCOUPLE)
    bench = len(rows) * (hold + 5.0) + max(0, len(rows) - 1) * cool_s * (max(abs(np.array(currents))) > 0.2)
    return {"points": rows, "T_magnet_C": float(T_read), "hold_s": hold, "bench_s": float(bench)}


def ds_back_emf(c: Coupon, rng, session, freqs=(10.0, 20.0, 50.0), amp=0.5e-3, dur=2.0, noise_scale=1.0):
    fs = 10000.0
    out = []
    T_mag = LAB_T + rng.uniform(-2, 2)
    Kf_T = c.Kf * (1 + c.alpha_B * (T_mag - 20.0))
    for f in freqs:
        t = np.arange(0, dur, 1 / (4 * fs))
        xdot = 2 * np.pi * f * amp * np.cos(2 * np.pi * f * t)
        emf = Kf_T * xdot
        _, vel = ins.measure(ins.LDV, t, xdot, rng, session, noise_scale)
        _, vv = ins.measure(_DAQ_V, t, emf, rng, session, noise_scale)
        out.append({"f_Hz": f, "fs": fs, "v_emf_V": vv, "vel_m_s": vel})
    return {"records": out, "T_magnet_C": float(T_mag + session.offset(ins.THERMOCOUPLE)),
            "bench_s": len(freqs) * (dur + 20.0) + 300.0}


_DAQ_V = ins.Channel("daq_voltage", "V", fs=10000.0, noise_rms=5e-6, gain_bound=0.0005, bw_hz=4500.0, bw_order=4,
                     src={"all": "ASSUMPTION 24-bit DAQ voltage input, 0.05 % gain, 5 uV RMS"})


def ds_thermal(c: Coupon, rng, session, I=0.2, duration=180.0, noise_scale=1.0, fs=10.0, T_amb=25.0,
               pre_s=5.0):
    """Constant-current step in still air (chamber at T_amb); coil temperature by resistance.
    The first pre_s seconds are read with the DMM test current only (coil at ambient)."""
    dt = 0.01
    n = int((pre_s + duration) / dt)
    t = np.arange(n) * dt
    T = np.empty(n)
    Tk = T_amb
    for k in range(n):
        Ik = I if t[k] >= pre_s else 0.0
        P = Ik * Ik * c.R20 * (1 + ALPHA_CU * (Tk - 20.0))
        Tk += dt / c.Cth * (P - (Tk - T_amb) / c.Rth)
        T[k] = Tk
    Rt = c.R20 * (1 + ALPHA_CU * (T - 20.0))
    ch = ins.DMM_RESISTANCE.scaled(noise_scale)
    tr_, Rm = ins.measure(ch, t, Rt, rng, session, fs=fs)
    Tamb_read = T_amb + session.offset(ins.THERMOCOUPLE) + 0.05 * rng.standard_normal()
    return {"t_s": tr_, "R_ohm": Rm, "I_set_A": I, "t_on_s": pre_s,
            "T_amb_C": float(Tamb_read), "bench_s": duration + pre_s + 120.0}


def generate(truth_vals: Dict, rng, session=None, noise_scale=1.0, hold=2.0, n_rep=1, n_avg=16,
             thermal_s=180.0, back_emf=True):
    c = Coupon.from_truth(truth_vals)
    session = session or ins.draw_session(rng)
    ds = {"r20": ds_r20(c, rng, session, noise_scale=noise_scale),
          "step": ds_step(c, rng, session, n_avg=n_avg, noise_scale=noise_scale),
          "force": ds_blocked_force(c, rng, session, hold=hold, n_rep=n_rep, noise_scale=noise_scale),
          "thermal": ds_thermal(c, rng, session, duration=thermal_s, noise_scale=noise_scale)}
    if back_emf:
        ds["emf"] = ds_back_emf(c, rng, session, noise_scale=noise_scale)
    return ds


# --------------------------------------------------------------------------- identification
def id_r20(d):
    y = np.asarray(d["R_ohm"])
    R = float(y.mean())
    u_stat = float(y.std(ddof=1) / math.sqrt(len(y))) if len(y) > 1 else 2e-5 * R
    unc = ident.combine(R, u_stat, rel_bounds=[ins.MICRO_OHM.gain_bound, ALPHA_CU * T_BATH_BOUND])
    return {"R20": R, **unc}


def id_step(d, R20_hat):
    """Output-error fit of L di/dt + R i = v on the averaged scope record: parameters
    a = g_i/(g_v L) (gain-contaminated) and b = R/L (gain free). L = R(T)/b."""
    t, i, v = np.asarray(d["t_s"]), np.asarray(d["i_A"]), np.asarray(d["v_V"])
    m = t >= 0
    t, i, v = t[m], i[m], v[m]
    dt = t[1] - t[0]
    Rc = R20_hat * (1 + ALPHA_CU * (d["T_coupon_C"] - 20.0))

    from scipy.signal import lfilter

    def sim(p):
        # first-order hold on the measured terminal voltage (exact for piecewise-linear v)
        a, b, i0 = p
        E = math.exp(-b * dt)
        ph2 = 1.0 / b - (1 - E) / (b * b * dt)
        ph1 = (1 - E) / b - ph2
        bb = [a * ph2, a * ph1]
        y, _ = lfilter(bb, [1.0, -E], v, zi=[i0 - bb[0] * v[0]])
        return y

    b0 = Rc / 175e-6
    p0 = [b0 * (i[-1] / max(v[-1], 1e-9)), b0, 0.0]
    fit = ident.nls(lambda p: sim(p) - i, p0, bounds=([0, 1e3, -0.05], [np.inf, 1e7, 0.05]))
    a, b, _ = fit["p"]
    L = Rc / b
    u_b = fit["se"][1]
    u_stat = L * u_b / b
    unc = ident.combine(L, u_stat, rel_bounds=[ins.MICRO_OHM.gain_bound, ALPHA_CU * 0.5,
                                               ALPHA_CU * T_BATH_BOUND])
    resid = fit["resid"]
    return {"L": float(L), "tau_s": float(1 / b), **unc, "resid_rms_A": float(np.sqrt(np.mean(resid ** 2)))}


def _kf_from_points(pts):
    I = np.array([p["I_set_A"] for p in pts])
    F = np.array([p["F_mean_N"] for p in pts])
    r = ident.ols(np.column_stack([I, np.ones_like(I)]), F)
    return r


def id_force(d, rng=None, n_boot=200):
    pts = d["points"]
    r = _kf_from_points(pts)
    Kf_T = float(r["b"][0])
    corr = 1.0 / (1 + ALPHA_B_NOM * (d["T_magnet_C"] - 20.0))
    Kf20 = Kf_T * corr
    u_stat = float(r["se"][0]) * corr
    if rng is not None and len(pts) >= 4:
        bs = ident.bootstrap(pts, lambda s: [_kf_from_points(s)["b"][0]], n_boot, rng)
        u_boot = float(np.std(bs[:, 0])) * corr if len(bs) > 10 else u_stat
        u_stat = max(u_stat, u_boot)
    unc = ident.combine(Kf20, u_stat, rel_bounds=[ins.FT_SENSOR.gain_bound, ins.CURRENT_SOURCE.gain_bound,
                                                  ALPHA_B_BOUND * abs(d["T_magnet_C"] - 20.0) + ALPHA_B_BOUND * 0.5])
    dTmax = max(p["coil_dT_K"] for p in pts)
    return {"Kf": Kf20, **unc, "intercept_N": float(r["b"][1]), "coil_dT_max_K": dTmax,
            "protocol_dT_rule_2K_met": bool(dTmax < 2.0)}


def id_back_emf(d):
    num = 0.0
    den = 0.0
    for rec in d["records"]:
        v, x = np.asarray(rec["v_emf_V"]), np.asarray(rec["vel_m_s"])
        n = min(len(v), len(x))
        num += float(x[:n] @ v[:n])
        den += float(x[:n] @ x[:n])
    Kf_T = num / den
    corr = 1.0 / (1 + ALPHA_B_NOM * (d["T_magnet_C"] - 20.0))
    Kf20 = Kf_T * corr
    unc = ident.combine(Kf20, 1e-5 * Kf20, rel_bounds=[ins.LDV.gain_bound, _DAQ_V.gain_bound,
                                                       ALPHA_B_BOUND * abs(d["T_magnet_C"] - 20.0)])
    return {"Kf": Kf20, **unc}


def id_thermal(d, R20_hat):
    """Ratio method: the coil starts at ambient, so its temperature rise is
    (R(t)/R_pre - 1)(1/alpha + T_amb - 20), free of the DMM gain and the thermocouple
    offset. The one-node model with P = I^2 R(T) is linear in the rise and is fitted
    in closed form: C th' = P0 - (1/R_th - beta) th."""
    t, R = np.asarray(d["t_s"]), np.asarray(d["R_ohm"])
    pre = t < d["t_on_s"] - 0.2
    on = t >= d["t_on_s"]
    R0 = float(R[pre].mean())
    Ta = d["T_amb_C"]
    th = (R[on] / R0 - 1) * (1 / ALPHA_CU + Ta - 20.0)
    tt = t[on] - d["t_on_s"]
    I = d["I_set_A"]

    def sim(p):
        Rth, Cth, th0 = p
        P0 = I * I * R20_hat * (1 + ALPHA_CU * (Ta - 20.0))
        beta = I * I * R20_hat * ALPHA_CU
        g = 1.0 / Rth - beta
        th_inf = P0 / g
        return th_inf + (th0 - th_inf) * np.exp(-g * tt / Cth)

    fit = ident.nls(lambda p: sim(p) - th, [150.0, 0.3, 0.0], bounds=([5.0, 0.01, -2.0], [2000.0, 10.0, 5.0]))
    Rth, Cth, _ = fit["p"]
    # type B: current source 0.1 % (power 0.2 %), R20 0.2 %, alpha_cu declared span 0.0039-0.00393 (0.8 %)
    a_b = (0.00393 - 0.0039) / 0.00393
    uRth = ident.combine(Rth, fit["se"][0], rel_bounds=[2 * ins.CURRENT_SOURCE.gain_bound, 0.002, a_b])
    uCth = ident.combine(Cth, fit["se"][1], rel_bounds=[2 * ins.CURRENT_SOURCE.gain_bound, 0.002, a_b])
    return {"Rth": float(Rth), "Cth": float(Cth), "u_Rth": uRth["u"], "u_Cth": uCth["u"],
            "U95_Rth": uRth["U95"], "U95_Cth": uCth["U95"], "tau_s": float(Rth * Cth)}


def identify(ds, rng=None):
    """Blind identification from the datasets only. Returns M1 keys with value, u, U95."""
    r20 = id_r20(ds["r20"])
    st = id_step(ds["step"], r20["R20"])
    fo = id_force(ds["force"], rng)
    est = {"actuator.R20": {"value": r20["R20"], "u": r20["u"], "U95": r20["U95"]},
           "actuator.L": {"value": st["L"], "u": st["u"], "U95": st["U95"]}}
    kf = {"value": fo["Kf"], "u": fo["u"], "U95": fo["U95"], "force_only": fo["Kf"],
          "coil_dT_max_K": fo["coil_dT_max_K"], "protocol_dT_rule_2K_met": fo["protocol_dT_rule_2K_met"]}
    if "emf" in ds:
        em = id_back_emf(ds["emf"])
        w1, w2 = 1 / fo["u"] ** 2, 1 / em["u"] ** 2
        kf.update({"value": (w1 * fo["Kf"] + w2 * em["Kf"]) / (w1 + w2), "u": math.sqrt(1 / (w1 + w2)),
                   "emf_only": em["Kf"], "u_force_only": fo["u"], "u_emf_only": em["u"]})
        kf["U95"] = 2 * kf["u"]
    est["actuator.Kf"] = kf
    th = id_thermal(ds["thermal"], r20["R20"])
    est["actuator.Rth_coil_amb"] = {"value": th["Rth"], "u": th["u_Rth"], "U95": th["U95_Rth"]}
    est["actuator.Cth_coil"] = {"value": th["Cth"], "u": th["u_Cth"], "U95": th["U95_Cth"]}
    bench = sum(d.get("bench_s", 0.0) for d in ds.values())
    return {"estimates": est, "bench_s": bench}
