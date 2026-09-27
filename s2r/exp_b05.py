"""EXP-B05 virtual bench: stage FRF (m_eq, k_tip, zeta, loop delay), static tip stiffness, axial path.

The FRF uses M1 itself as the plant, configured as the protocol's "signal
injection at the loop-breaking points in a firmware test build" (§6 equipment):
  * pen clamped in the R5 fixture (grip and normal springs 1e6 N/m, no hand
    mass), lifted (no contact), altitude 90 deg so the page Jacobian is identity;
  * mode 'oracle' with require_contact = 0 and the stage sensor frozen at 0
    (fail_type 3 at t = 0): the position loop is open and the servo output is
    F = K_inj q_r, so the current reference is i_ref = -K_inj q_r / (n K_f);
  * q_r is the injected signal (a current chirp expressed as a reference),
    derivative, integral and feedforward gains zero; slew and travel limits
    lifted for the test build.
All controller-side numbers come from the firmware's nominal parameter set via
s2r.twin.shim, so the current actually commanded is the designed one even when
the true K_f differs.

Excitation. The protocol's flat 0.05 A chirp from 1 Hz is not usable on this
stage (CALCULATION: 0.05 A gives n K_f i / k_tip = 1.4 mm of static deflection
against a 0.6 mm stop, and about 14 mm at the 11.8 Hz resonance). The virtual
bench therefore runs (1) a pilot chirp shaped on the nominal plant for 5 um,
then (2) chirps shaped on the pilot FRF for a 30 um target, capped at the
protocol's 0.05 A. Documented as a deviation in docs/sim_to_real.md.

Measurements:
  * rig DAQ (10 kS/s): current through a 0.1 %-class shunt and LDV velocity on
    the refill -> mechanical FRF q/i (matched anti-alias filters);
  * pen test log (2 kHz): the float current command and the Hall reading ->
    FRF q_hall/i_ref, whose extra phase over the mechanical FRF and the known
    zero-order hold is the loop delay (Hall + current loop);
  * static tip stiffness by force probe and R5 tip metrology (standalone static
    model: q = F/k_tip inside the stop, stop stiffness outside);
  * axial path: load cell and laser displacement, 0 -> 2 N -> 0, three cycles.

Evidence status: SIMULATION (data) and CALCULATION (fits).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

from sim.pensim import model
from . import ident
from . import instruments as ins
from . import twin
from stabpen import params as sp_params

_P = sp_params.load()
DT = 25e-6
REC_HZ = 20000.0               # M1 record rate for the virtual instruments (spectral velocity)
F_LO, F_HI = 1.0, 500.0          # PROTOCOL EXP-B05 procedure 3: chirp 1-500 Hz
I_CAP = 0.05                     # PROTOCOL EXP-B05 procedure 3: 0.05 A per axis (used as a cap)
K_INJ = 400.0                    # N/m: test-build injection gain (0.05 A <-> q_r 0.28 mm)
TAIL = 1.5                       # s of zero input after each chirp (response decays, ~5.5/(zeta w_n))
# R5 fixture (ASSUMPTION 1e7 N/m, zeta ~0.3): at 1e6 N/m the fixture biases zeta by -0.2 % and m_eq by +0.2 %
CLAMP = {"hand.grip_stiffness": 1.0e7, "hand.grip_damping": 350.0, "hand.normal_stiffness": 1.0e7,
         "hand.normal_damping": 350.0, "hand.mass": 0.0}
T_TEST = float(_P["thermal.t_ambient"])   # magnet temperature of the M1 truth during the test (ambient)
_TIMING: Dict[str, float] = {}


def lever_ratio() -> float:
    return float(_P["stage.L2"] / _P["stage.L1"])


def _injection_controller():
    return model.Controller(mode="oracle", ff_ref=0.0, ff_accel=0.0, q_lim=5e-3, q_taper=1e-4, slew=100.0,
                            authority_tau=1e-3, oracle_h=0.0)


def chirp_current(T_c, fs, amp_fn, f0=F_LO, f1=F_HI):
    """Log chirp with frequency-dependent amplitude, followed by TAIL s of zeros."""
    t = np.arange(int(round((T_c + TAIL) * fs))) / fs
    tc = np.minimum(t, T_c)
    k = math.log(f1 / f0) / T_c
    phase = 2 * math.pi * f0 * (np.exp(k * tc) - 1) / k
    finst = f0 * np.exp(k * tc)
    taper = np.clip(t / 0.05, 0, 1) * np.clip((T_c - t) / 0.05, 0, 1)
    return t, amp_fn(finst) * np.sin(phase) * taper


def nominal_amp_fn(q_target, Kf=None, k=None, m=None, zeta=None, cap=I_CAP):
    Kf = Kf or _P["actuator.Kf"]
    k = k or _P["stage.k_tip"]
    m = m or twin.geometric_m_eq()
    zeta = zeta or _P["stage.zeta_open"]
    c = 2 * zeta * math.sqrt(k * m)
    nKf = lever_ratio() * Kf

    def fn(f):
        w = 2 * math.pi * f
        return np.minimum(q_target * np.abs(k - m * w ** 2 + 1j * c * w) / nKf, cap)
    return fn


def fitted_amp_fn(q_target, fit, cap=I_CAP, floor=2e-5):
    a, fn_, z, _ = fit["p"]
    wn = 2 * math.pi * fn_

    def fn(f):
        w = 2 * math.pi * f
        G = a / np.abs(wn ** 2 - w ** 2 + 2j * z * wn * w)
        return np.clip(q_target / G, floor, cap)
    return fn


def run_chirp(plant_vals: Dict, t_in, i_design, seed=1):
    """One M1 test-build run. Returns the 40 kHz record (true signals) and the shim info."""
    ctrl = _injection_controller()
    n = int(round(t_in[-1] / DT)) + 1
    t = np.arange(n) * DT
    i_d = np.interp(t, t_in, i_design)
    pv = dict(plant_vals)
    pv.update(CLAMP)
    ov, kw, info = twin.shim(pv, None, ctrl, theta_deg=90.0)
    nKf_c = lever_ratio() * info["controller"]["nKf"]
    qr = -i_d * nKf_c / K_INJ
    ov.update({"Kp": info["kappa"] * K_INJ, "Kd": 0.0, "Ki": 0.0, "require_contact": 0.0,
               "fail_type": 3, "fail_time": 0.0})
    lift = 3e-3
    pref = np.zeros((n, 3))
    pref[:, 2] = lift
    scn = model.Scenario(t=t, pref=pref, vref=np.zeros((n, 3)), fpush=np.zeros(n),
                         dtrue=np.column_stack([qr, np.zeros(n)]), intended=np.zeros((n, 2)),
                         opt_ok=np.ones(n, np.uint8), theta_deg=90.0, N0=0.0)
    from dataclasses import replace
    r = model.run(scn, replace(ctrl, **kw), overrides=ov, seed=seed, rec_hz=REC_HZ)
    return r, info


def _velocity(q, fs):
    Q = np.fft.rfft(q)
    f = np.fft.rfftfreq(len(q), 1 / fs)
    return np.fft.irfft(2j * np.pi * f * Q, len(q))


def measure_chirp(r, rng, session, plant_vals, noise_scale=1.0, hall_key="q1"):
    """Instrument views of one run: rig DAQ (current, LDV on the tip) and pen test log (i_ref,
    Hall on the lever; the same coordinate in M1)."""
    t = r["t"]
    q = r["q1"]
    q_h = r[hall_key]
    i = r["i1"]
    fs = REC_HZ
    vel = _velocity(q, fs)
    from dataclasses import replace
    daq_i = ins.DAQ_SHUNT_CURRENT.scaled(noise_scale)
    # LDV sampled by the same DAQ: its anti-alias (4.5 kHz, 4th order) dominates the LDV's own 20 kHz
    ldv = replace(ins.LDV, fs=10000.0, bw_hz=4500.0, bw_order=4).scaled(noise_scale)
    _, i_m = ins.measure(daq_i, t, i, rng, session)
    _, v_m = ins.measure(ldv, t, vel, rng, session)
    # pen test log at the 2 kHz ticks: float command, Hall (delay, noise, crosstalk, 0.1 um log step)
    sdec = int(round(1.0 / (_P["control.f_stage"] * DT)))
    k_tick = np.arange(0, int(round(t[-1] / DT)) + 1 - sdec, sdec)
    t_tick = k_tick * DT
    iref = np.interp(t_tick, t, r["iref1"])
    hd = int(round(plant_vals.get("sensing.hall_delay", _P["sensing.hall_delay"]) / DT))
    t_h = (k_tick - hd) * DT
    ict = _P["sensing.hall_i_crosstalk_tip"]
    hn = plant_vals.get("sensing.hall_noise_tip", _P["sensing.hall_noise_tip"]) * noise_scale
    qh = (np.interp(t_h, t, q_h) + ict * np.interp(t_h, t, i) - ict * np.interp(t_tick, t, i)
          + hn * rng.standard_normal(len(t_tick)))
    qh = ins.HALL_FRAME.lsb * np.round(qh / ins.HALL_FRAME.lsb)
    return {"daq": {"fs": 10000.0, "i_A": i_m, "v_m_s": v_m},
            "pen": {"fs": 2000.0, "iref_A": iref, "q_hall_m": qh}}


def attach_reference(rec, t_in, i_design):
    """The designed digital chirp (known to the analyst) on the DAQ rate; its clock offset
    cancels in the instrumental-variable FRF."""
    rec["daq"]["ref_A"] = np.interp(np.arange(len(rec["daq"]["i_A"])) / 10000.0, t_in, i_design)
    return rec


# --------------------------------------------------------------------------- standalone static tests
def ds_static_tip(k_tip, rng, session, F_max=0.03, n_dir=8, n_cycles=3, n_pts=11, noise_scale=1.0,
                  q_stop=None, k_stop=None):
    """Force probe at the tip, coils open (PROTOCOL EXP-B05 procedure 1; +-0.2 N in the text)."""
    q_stop = q_stop or _P["stage.travel_tip_mech"]
    k_stop = k_stop or _P["stage.stop_stiffness"]
    F_knee = k_tip * q_stop
    rows = []
    for d in range(n_dir):
        for c in range(n_cycles):
            Fs = np.concatenate([np.linspace(0, F_max, n_pts), np.linspace(F_max, 0, n_pts)[1:]])
            for F in Fs:
                q = F / k_tip if F <= F_knee else q_stop + (F - F_knee) / (k_tip + k_stop)
                Fm = ins.measure_static(ins.FORCE_PROBE, F, rng, session, noise_scale, n_avg=100)
                qm = ins.measure_static(ins.TIP_METROLOGY, q, rng, session, noise_scale, n_avg=10)
                rows.append((d, c, Fm, qm))
    a = np.array(rows)
    return {"dir": a[:, 0], "cycle": a[:, 1], "F_N": a[:, 2], "q_m": a[:, 3], "F_max_N": F_max,
            "bench_s": n_dir * n_cycles * (2 * n_pts * 2.0 + 10.0)}


def id_static_tip(d, q_lin=0.8 * _P["stage.travel_tip_mech"]):
    """Slope of force against tip displacement, using only points inside 0.8 of the design stop
    radius (a probe force chosen from nominal constants can still reach the stop)."""
    m = np.abs(d["q_m"]) < q_lin
    if m.sum() < 10:
        m = np.ones_like(d["q_m"], bool)
    r = ident.ols(np.column_stack([d["q_m"][m], np.ones(m.sum())]), d["F_N"][m])
    k = float(r["b"][0])
    unc = ident.combine(k, float(r["se"][0]), rel_bounds=[ins.FORCE_PROBE.gain_bound, 0.002])
    return {"k_tip": k, **unc, "n_used": int(m.sum()), "n_total": int(len(m))}


def ds_axial(k_ax, F_pre, rng, session, s_max=None, F_top=2.0, n_cycles=3, n_pts=41, noise_scale=1.0,
             k_stop=None):
    s_max = s_max or _P["stage.axial_travel"]
    k_stop = k_stop or _P["stage.stop_stiffness"]
    F_stop = F_pre + k_ax * s_max
    Fs = np.concatenate([np.linspace(0, F_top, n_pts), np.linspace(F_top, 0, n_pts)[1:]])
    rows = []
    for c in range(n_cycles):
        for F in Fs:
            if F <= F_pre:
                s = 0.0
            elif F <= F_stop:
                s = (F - F_pre) / k_ax
            else:
                s = s_max + (F - F_stop) / k_stop
            rows.append((c, ins.measure_static(ins.AXIAL_LOAD_CELL, F, rng, session, noise_scale, n_avg=100),
                         ins.measure_static(ins.LASER_DISP, s, rng, session, noise_scale, n_avg=10)))
    a = np.array(rows)
    return {"F_N": a[:, 1], "s_m": a[:, 2], "bench_s": n_cycles * (2 * n_pts * 1.0 + 20.0)}


def id_axial(d):
    """Seat + spring (+ stop) fit. Breakpoints by grid search with linear LS inside, the stop
    segment kept only if it lowers the BIC; then a joint nonlinear refinement."""
    F, s = np.asarray(d["F_N"]), np.asarray(d["s_m"])
    n = len(F)
    Ftop = float(F.max())
    cands = []
    for Fp in np.linspace(0.02, min(1.0, Ftop - 0.3), 120):
        X = np.column_stack([np.ones_like(F), np.clip(F, Fp, None) - Fp])
        b, *_ = np.linalg.lstsq(X, s, rcond=None)
        sse = float(np.sum((X @ b - s) ** 2))
        cands.append((n * math.log(sse / n + 1e-300) + 3 * math.log(n), Fp, None, b))
        for Fs_ in np.linspace(Fp + 0.2, Ftop - 0.1, 40):
            X = np.column_stack([np.ones_like(F), np.clip(F, Fp, Fs_) - Fp, np.clip(F - Fs_, 0, None)])
            b, *_ = np.linalg.lstsq(X, s, rcond=None)
            if b[1] <= 0 or b[2] > 0.2 * b[1]:
                continue       # a stop must be at least 5x stiffer than the spring it ends
            sse = float(np.sum((X @ b - s) ** 2))
            cands.append((n * math.log(sse / n + 1e-300) + 5 * math.log(n), Fp, Fs_, b))
    _, Fp0, Fs0, b0 = min(cands, key=lambda c: c[0])
    if Fs0 is None:
        def res(p):
            Fp, c0, g = p
            return c0 + g * (np.clip(F, Fp, None) - Fp) - s
        fit = ident.nls(res, [Fp0, b0[0], max(b0[1], 1e-7)])
        Fp, c0, g = fit["p"]
        Fs_ = None
        se_g, se_Fp = fit["se"][2], fit["se"][0]
        span = (Ftop - Fp) * g
    else:
        def res(p):
            Fp, Fs_, c0, g, h = p
            return c0 + g * (np.clip(F, Fp, Fs_) - Fp) + h * np.clip(F - Fs_, 0, None) - s
        fit = ident.nls(res, [Fp0, Fs0, b0[0], max(b0[1], 1e-7), b0[2]])
        Fp, Fs_, c0, g, h = fit["p"]
        se_g, se_Fp = fit["se"][3], fit["se"][0]
        span = (Fs_ - Fp) * g
    k_ax = 1.0 / g
    u_k = se_g / g ** 2
    # laser nonlinearity (absolute bound) acting across the spring span, load-cell gain
    uk = ident.combine(k_ax, u_k, rel_bounds=[ins.AXIAL_LOAD_CELL.gain_bound,
                                              2 * ins.LASER_DISP.nonlin_bound / max(span, 1e-6)])
    uF = ident.combine(Fp, se_Fp, abs_bounds=[ins.AXIAL_LOAD_CELL.offset_bound])
    return {"axial_k": float(k_ax), "u_axial_k": uk["u"], "U95_axial_k": uk["U95"],
            "axial_preload": float(Fp), "u_axial_preload": uF["u"], "U95_axial_preload": uF["U95"],
            "F_stop": None if Fs_ is None else float(Fs_), "spring_span_m": float(span)}


# --------------------------------------------------------------------------- full experiment
def generate(truth_vals: Dict, rng, session=None, n_chirps=4, T_c=10.0, noise_scale=1.0, q_target=30e-6,
             static_F=0.03, seed0=11):
    session = session or ins.draw_session(rng)
    pv = dict(truth_vals)
    # (1) pilot chirp, nominal shaping, 5 um
    t_in, i_p = chirp_current(min(T_c, 10.0), 10000.0, nominal_amp_fn(5e-6))
    r, info = run_chirp(pv, t_in, i_p, seed=seed0)
    pil = attach_reference(measure_chirp(r, rng, session, pv, noise_scale), t_in, i_p)
    del r
    # pilot FRF from the single record has no coherence estimate; fit it with 5 % weights
    fp, Hp, cp, _ = ident.frf_iv([pil["daq"]["ref_A"]], [pil["daq"]["i_A"]],
                                 [_disp(pil["daq"]["v_m_s"], 10000.0)], 10000.0, 2.0, 300.0)
    fit_p = ident.fit_second_order(fp, Hp, 0.05 * np.abs(Hp) + 1e-12, fit_delay=False)
    amp = fitted_amp_fn(q_target, fit_p)
    # analyst's choice of the static probe force: keep the tip within 0.8 of the stop radius, using the
    # pilot FRF (k/(n K_f) = w_n^2 / a) with the nominal n K_f
    k_pilot = lever_ratio() * _P["actuator.Kf"] * (2 * math.pi * fit_p["p"][1]) ** 2 / fit_p["p"][0]
    static_F = min(static_F, 0.8 * _P["stage.travel_tip_mech"] * k_pilot)
    recs = []
    for c in range(n_chirps):
        t_in, i_c = chirp_current(T_c, 10000.0, amp)
        r, _ = run_chirp(pv, t_in, i_c, seed=seed0 + 1 + c)
        recs.append(attach_reference(measure_chirp(r, rng, session, pv, noise_scale), t_in, i_c))
        peak = float(np.max(np.abs(r["q1"])))
        del r
    k_t = truth_vals.get("stage.k_tip", _P["stage.k_tip"])
    ds = {"chirps": recs, "T_c": T_c, "n_chirps": n_chirps, "q_peak_last_m": peak,
          "static": ds_static_tip(k_t, rng, session, F_max=static_F, noise_scale=noise_scale),
          "axial": ds_axial(truth_vals.get("stage.axial_k", _P["stage.axial_k"]),
                            truth_vals.get("stage.axial_preload", _P["stage.axial_preload"]), rng, session,
                            noise_scale=noise_scale),
          "_hidden": {"kappa": info["kappa"]},
          "T_magnet_C": T_TEST + session.offset(ins.THERMOCOUPLE) + 0.05 * rng.standard_normal()}
    ds["bench_s"] = (n_chirps + 1) * (T_c + TAIL + 5.0) + ds["static"]["bench_s"] + ds["axial"]["bench_s"] + 600.0
    return ds


def _u_rel(v, u_stat, rel_bound):
    """ASSUMPTION 0.5 % bound for fixture and housing coupling on zeta (virtual-bench finding:
    -0.2 % at a 1e6 N/m fixture)."""
    c = ident.combine(v, u_stat, rel_bounds=[rel_bound])
    return {"u": c["u"], "U95": c["U95"]}


def step_invariant(a, fn_, z, Ts, f):
    """Frequency response of the exact ZOH-sampled second-order plant (step invariance)."""
    from scipy import signal as sps
    wn = 2 * math.pi * fn_
    bd, ad, _ = sps.cont2discrete(([-a], [1.0, 2 * z * wn, wn * wn]), Ts, method="zoh")
    _, G = sps.freqz(np.ravel(bd), ad, worN=2 * np.pi * np.asarray(f) * Ts)
    return G


def m1_timing_offset(L: float = None, R20: float = None) -> float:
    """Deterministic lead between the tick-labelled command and the tick-labelled stage
    reading in M1's discrete timing (command effective within its own 25 us step, current
    loop at 40 kHz), with zero Hall delay. A known property of the simulator (the analogue
    of the firmware's documented PWM/ADC latencies), computed once on the nominal twin
    without noise; the Hall delay is what remains."""
    key = (round(L or _P["actuator.L"], 7), round(R20 or _P["actuator.R20"], 3))
    if key not in _TIMING:
        pv = twin.nominal_plant()
        pv["actuator.L"], pv["actuator.R20"] = key
        t_in, i_c = chirp_current(10.0, 10000.0, nominal_amp_fn(30e-6))
        r, _ = run_chirp(pv, t_in, i_c, seed=1)
        sdec = int(round(1.0 / (_P["control.f_stage"] * DT)))
        tt = np.arange(0, r["t"][-1] - sdec * DT, sdec * DT)          # tick instants (record-rate independent)
        f, H, _, _ = ident.frf_h1([np.interp(tt, r["t"], r["iref1"])], [np.interp(tt, r["t"], r["q1"])], 2000.0,
                                  5.0, 300.0)
        k = pv["stage.k_tip"]
        m = pv["stage.m_eq"]
        z = pv["stage.zeta_open"]
        nKf = lever_ratio() * pv["actuator.Kf"] * (1 + float(_P["actuator.alpha_B"]) * (T_TEST - 20.0))
        G = step_invariant(nKf / m, math.sqrt(k / m) / (2 * math.pi), z, 1.0 / 2000.0, f)
        ph = np.unwrap(np.angle(H / G))
        w = 2 * np.pi * f
        _TIMING[key] = float(-np.sum(w * ph) / np.sum(w * w))
    return _TIMING[key]


def _disp(v, fs):
    """LDV velocity -> displacement for the FRF (spectral integration, DC removed)."""
    V = np.fft.rfft(v - np.mean(v))
    f = np.fft.rfftfreq(len(v), 1 / fs)
    f[0] = 1.0
    X = V / (2j * np.pi * f)
    X[0] = 0.0
    return np.fft.irfft(X, len(v))


def identify(ds, Kf_hat: float, u_Kf: float, fit_band=(2.0, 300.0), delay_band=(5.0, 300.0), L_hat=None,
             R20_hat=None):
    """Blind identification. Kf_hat and u_Kf come from EXP-B03 (the mass line needs n K_f); L_hat and
    R20_hat (also EXP-B03) set the known current-loop part of the loop delay."""
    n = lever_ratio()
    recs = ds["chirps"]
    u = [c["daq"]["i_A"] for c in recs]
    y = [_disp(c["daq"]["v_m_s"], 10000.0) for c in recs]
    rr = [c["daq"]["ref_A"] for c in recs]
    f, H, coh, sig = ident.frf_iv(rr, u, y, 10000.0, *fit_band)
    fit = ident.fit_second_order(f, H, sig, fit_delay=True)
    a, fn_, z, tau_m = fit["p"]
    cov = fit["cov"]
    from .exp_b03 import ALPHA_B_NOM
    Kf_T = Kf_hat * (1 + ALPHA_B_NOM * (ds["T_magnet_C"] - 20.0))
    nKf = n * Kf_T
    m = nKf / a
    k = m * (2 * math.pi * fn_) ** 2
    # propagate: m = nKf/a ; k = nKf wn^2/a
    rel_u_a = fit["se"][0] / a
    rel_u_fn = fit["se"][1] / fn_
    u_m = ident.combine(m, m * math.hypot(rel_u_a, u_Kf / Kf_hat),
                        rel_bounds=[ins.LDV.gain_bound, ins.DAQ_SHUNT_CURRENT.gain_bound])
    u_k = ident.combine(k, k * math.sqrt(rel_u_a ** 2 + (u_Kf / Kf_hat) ** 2 + (2 * rel_u_fn) ** 2),
                        rel_bounds=[ins.LDV.gain_bound, ins.DAQ_SHUNT_CURRENT.gain_bound])
    st = id_static_tip(ds["static"])
    # combined k_tip (independent static + FRF estimates)
    w1, w2 = 1 / u_k["u"] ** 2, 1 / st["u"] ** 2
    k_comb = (w1 * k + w2 * st["k_tip"]) / (w1 + w2)
    u_kc = math.sqrt(1 / (w1 + w2))
    chi_k = (k - st["k_tip"]) ** 2 / (u_k["u"] ** 2 + st["u"] ** 2)   # consistency of the two routes
    # loop delay from the pen log: H_pen / (G_mech ZOH)
    up = [c["pen"]["iref_A"] for c in recs]
    yp = [c["pen"]["q_hall_m"] for c in recs]
    # frequency smoothing over 20 bins (~1.7 Hz): the residual phase is smooth, and the smoothed
    # coherence has 20x the degrees of freedom (4 records alone give coherence estimates biased high)
    fp, Hp, cohp, sigp = ident.frf_h1(up, yp, 2000.0, *delay_band, smooth=20)
    Ts = 1.0 / 2000.0
    w = 2 * np.pi * fp
    Gd = step_invariant(a, fn_, z, Ts, fp)
    R = Hp / Gd
    # the residual phase is small (|ωτ| << π up to 300 Hz for any plausible delay), so no unwrapping:
    # an unwrap slip on one noisy bin would corrupt every bin above it
    ph = np.angle(R)
    good = cohp >= 0.9                       # PROTOCOL EXP-B05 procedure 3: coherence >= 0.9 required
    if good.sum() < 10:
        good = cohp >= 0.5
    w, ph = w[good], ph[good]
    s_ph2 = (sigp[good] / np.maximum(np.abs(Hp[good]), 1e-30)) ** 2 + (np.interp(fp[good], f, sig / np.abs(H))) ** 2
    wt = 1.0 / np.maximum(s_ph2, 1e-8)
    tau = float(-np.sum(wt * w * ph) / np.sum(wt * w * w))
    res_ph = ph + w * tau
    chi2 = float(np.sum(wt * res_ph ** 2) / max(len(w) - 1, 1))
    u_tau = float(math.sqrt(max(chi2, 1.0) / np.sum(wt * w * w)))
    f_delay_max = float(w.max() / (2 * np.pi))
    loop = tau
    toff = m1_timing_offset(L_hat, R20_hat)
    tau = tau - toff
    ulp = ident.combine(tau, u_tau, abs_bounds=[5e-6])     # ASSUMPTION residual current-loop phase
    est = {
        "stage.m_eq": {"value": float(m), "u": u_m["u"], "U95": u_m["U95"]},
        "stage.k_tip": {"value": float(k_comb), "u": u_kc, "U95": 2 * u_kc, "frf": float(k),
                        "u_frf": u_k["u"], "static": st["k_tip"], "u_static": st["u"]},
        "stage.zeta_open": {"value": float(z), **_u_rel(z, float(fit["se"][2]), 0.005)},
        "sensing.hall_delay": {"value": tau, "u": ulp["u"], "U95": ulp["U95"],
                               "loop_delay_s": loop, "timing_offset_s": toff,
                               "f_max_coh_0.9_hz": f_delay_max},
    }
    ax = id_axial(ds["axial"])
    est["stage.axial_k"] = {"value": ax["axial_k"], "u": ax["u_axial_k"], "U95": ax["U95_axial_k"]}
    est["stage.axial_preload"] = {"value": ax["axial_preload"], "u": ax["u_axial_preload"],
                                  "U95": ax["U95_axial_preload"]}
    diag = {"fn_hz": float(fn_), "fit_chi2_per_dof": fit["chi2_per_dof"], "tau_mech_s": float(tau_m),
            "coherence_min_fit_band": float(np.min(coh)), "coherence_median": float(np.median(coh)),
            "frac_bins_coh_ge_0.9": float(np.mean(coh >= 0.9)), "q_peak_um": ds["q_peak_last_m"] * 1e6,
            "k_static_vs_frf_chi2": float(chi_k), "k_static_points_used": st["n_used"]}
    return {"estimates": est, "diag": diag, "bench_s": ds["bench_s"],
            "frf": {"f": f, "H": H, "coh": coh, "sigma": sig, "fit": fit}}
