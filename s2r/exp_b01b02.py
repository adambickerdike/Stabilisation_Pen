"""EXP-B01/B02 virtual bench: paper contact stiffness and LuGre friction on the R1 tribometer.

Truth model = M1's contact and friction equations (core.py, P-9), on a rig:
  * pen holder on a vertical slide loaded by a dead weight or the force-controlled
    voice-coil axis W(t): M_v z'' = N - W, N = max(0, k_p d - c_p z'), d = -z;
  * the ball is carried by the holder, whose horizontal mount (holder + F/T) is a
    spring-mass (k_h, m_h: ASSUMPTION 5e5 N/m, 50 g, i.e. the >= 500 Hz mounted
    resonance of PROTOCOL R1);
  * paper on the XY linear-motor platen moving at v_p(t) with <= 1 % RMS velocity
    ripple (PROTOCOL AC-B02-03), recorded by its 0.1 um encoder;
  * LuGre exactly as core.py: z' = v - s0 |v| z / g(v), g = mu_k + (mu_s - mu_k)
    exp(-(v/v_s)^2), f = -N (s0 z + s1 z') - s2 v, implicit bristle update, 25 us step;
    v is the ball velocity relative to the paper. s0 = mu_s / x_pre (model.py).
Instruments: 6-axis F/T in the pen frame (a, t1, t2) at 5 kHz with per-axis gain
errors, goniometer angle error, laser triangulation (indentation, with a series
rig compliance calibrated on a hard flat), capacitive sensor for pre-sliding (10 kHz).

Datasets (protocol §2 and §3, reduced grids documented in docs/sim_to_real.md):
  * B01 part 1: indentation ramp 0 -> 4 N -> 0 at 0.2 N/s, theta 50 deg;
  * B01 part 2: steady sliding, 20 mm strokes after a 1 s dwell, N {0.2...4} N;
  * B02 velocity steps 0.01-200 mm/s after a 1 s dwell, +-t1 and +-t2, N {0.5, 1, 2};
  * B02 slow triangular sweeps through zero velocity (reversal curves);
  * B02 held-out sinusoidal reciprocation 3-15 Hz (validation, R^2, AC-B02-01).
Identification: Stribeck curve by nonlinear least squares on step plateaus; the
pre-sliding length x_pre from reversal curves (f = A - B exp(-dx/x_pre)); k_p from
the 0.5-1.5 N secant corrected for rig compliance; bootstrap over records.

Evidence status: SIMULATION (data) and CALCULATION (fits).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List

import numpy as np
from numba import njit

from . import ident
from . import instruments as ins
from stabpen import params as sp_params

_P = sp_params.load()
DT = 25e-6
G0 = 9.81
M_HOLDER = 0.20          # ASSUMPTION kg moving on the vertical slide (holder + counterbalance), plus W/g
K_H, M_H, ZETA_H = 5e5, 0.05, 0.05     # ASSUMPTION horizontal mount (>= 500 Hz: PROTOCOL R1)
K_RIG_V = 2e6            # ASSUMPTION vertical compliance between laser target and ball (N/m)
RIPPLE_RMS = 0.01        # PROTOCOL AC-B02-03 velocity ripple <= 1 % RMS (worst case used)
POLE_PITCH = 0.03        # ASSUMPTION linear-motor pole pitch (m) for the ripple's periodic part
FT_RIG = replace(ins.FT_SENSOR, resonance_hz=0.0)   # the mount resonance is in the rig dynamics here


@dataclass
class Contact:
    k_p: float
    c_p: float
    mu_k: float
    mu_s: float
    v_s: float
    x_pre: float
    s1: float = 0.0
    s2: float = 0.0

    @classmethod
    def from_truth(cls, v: Dict):
        mu_k = v["writing.mu_eff"]
        return cls(v["writing.paper_stiffness"], v.get("writing.paper_damping", _P["writing.paper_damping"]),
                   mu_k, mu_k * v["writing.mu_static_ratio"], v["writing.stribeck_speed"],
                   v["friction.x_presliding"], v.get("friction.sigma1", 0.0), v.get("friction.sigma2", 0.0))

    def to_m1(self) -> Dict[str, float]:
        return {"writing.mu_eff": self.mu_k, "writing.mu_static_ratio": self.mu_s / self.mu_k,
                "writing.stribeck_speed": self.v_s, "writing.paper_stiffness": self.k_p,
                "friction.x_presliding": self.x_pre}


@njit(cache=True)
def _tribo(dt, vpx, vpy, W, k_p, c_p, mu_k, mu_s, v_s, s0, s1, s2, M_v, m_h, k_h, c_h, dec, out):
    """out columns: 0 N, 1 fx, 2 fy, 3-4 mount force (the contact force as the F/T sees it through the
    holder mount), 5 z_ball, 6 x_p, 7 y_p (platen), 8 x_h, 9 y_h (holder deflection)."""
    n = len(vpx)
    z = -W[0] / k_p if k_p > 0 else 0.0
    vz = 0.0
    xh = 0.0; yh = 0.0; vxh = 0.0; vyh = 0.0
    zb0 = 0.0; zb1 = 0.0
    xp = 0.0; yp = 0.0
    j = 0
    for k in range(n):
        d = -z
        N = 0.0
        if d > 0.0:
            N = k_p * d - c_p * vz
            if N < 0.0:
                N = 0.0
        vrx = vxh - vpx[k]
        vry = vyh - vpy[k]
        fx = 0.0; fy = 0.0
        if N > 0.0:
            vn = math.hypot(vrx, vry)
            g = mu_k + (mu_s - mu_k) * math.exp(-(vn / v_s) ** 2)
            den = 1.0 + dt * s0 * vn / g
            z0n = (zb0 + dt * vrx) / den
            z1n = (zb1 + dt * vry) / den
            zd0 = (z0n - zb0) / dt; zd1 = (z1n - zb1) / dt
            zb0 = z0n; zb1 = z1n
            fx = -N * (s0 * z0n + s1 * zd0) - s2 * vrx
            fy = -N * (s0 * z1n + s1 * zd1) - s2 * vry
        else:
            zb0 = 0.0; zb1 = 0.0
        az = (N - W[k]) / M_v
        axh = (fx - k_h * xh - c_h * vxh) / m_h
        ayh = (fy - k_h * yh - c_h * vyh) / m_h
        vz += az * dt; z += vz * dt
        vxh += axh * dt; xh += vxh * dt
        vyh += ayh * dt; yh += vyh * dt
        xp += vpx[k] * dt; yp += vpy[k] * dt
        if k % dec == 0 and j < out.shape[0]:
            out[j, 0] = N; out[j, 1] = fx; out[j, 2] = fy
            out[j, 3] = k_h * xh + c_h * vxh; out[j, 4] = k_h * yh + c_h * vyh
            out[j, 5] = z; out[j, 6] = xp; out[j, 7] = yp; out[j, 8] = xh; out[j, 9] = yh
            j += 1
    return j


@dataclass
class ContactMS(Contact):
    """Friction-memory truth (C3): generalised Maxwell-slip, M parallel elasto-slide elements with
    break-away displacements spread log-uniformly over [x_pre/spread, x_pre*spread] and equal shares
    of mu_s; each element's limit follows the same Stribeck curve g(v)/mu_s. Nested hysteresis loops
    with non-local memory, which a single-state LuGre model cannot represent."""
    n_el: int = 6
    spread: float = 4.0


@njit(cache=True)
def _tribo_ms(dt, vpx, vpy, W, k_p, c_p, mu_k, mu_s, v_s, kap, alim, M_v, m_h, k_h, c_h, dec, out):
    n = len(vpx)
    ne = len(kap)
    z = -W[0] / k_p
    vz = 0.0
    xh = 0.0; yh = 0.0; vxh = 0.0; vyh = 0.0
    zx = np.zeros(ne); zy = np.zeros(ne)
    xp = 0.0; yp = 0.0
    j = 0
    for k in range(n):
        d = -z
        N = 0.0
        if d > 0.0:
            N = k_p * d - c_p * vz
            if N < 0.0:
                N = 0.0
        vrx = vxh - vpx[k]
        vry = vyh - vpy[k]
        fx = 0.0; fy = 0.0
        if N > 0.0:
            vn = math.hypot(vrx, vry)
            s = (mu_k + (mu_s - mu_k) * math.exp(-(vn / v_s) ** 2)) / mu_s
            for i in range(ne):
                zx[i] += vrx * dt
                zy[i] += vry * dt
                lim = alim[i] * s / kap[i]
                zm = math.hypot(zx[i], zy[i])
                if zm > lim:
                    zx[i] *= lim / zm
                    zy[i] *= lim / zm
                fx -= N * kap[i] * zx[i]
                fy -= N * kap[i] * zy[i]
        else:
            for i in range(ne):
                zx[i] = 0.0; zy[i] = 0.0
        az = (N - W[k]) / M_v
        axh = (fx - k_h * xh - c_h * vxh) / m_h
        ayh = (fy - k_h * yh - c_h * vyh) / m_h
        vz += az * dt; z += vz * dt
        vxh += axh * dt; xh += vxh * dt
        vyh += ayh * dt; yh += vyh * dt
        xp += vpx[k] * dt; yp += vpy[k] * dt
        if k % dec == 0 and j < out.shape[0]:
            out[j, 0] = N; out[j, 1] = fx; out[j, 2] = fy
            out[j, 3] = k_h * xh + c_h * vxh; out[j, 4] = k_h * yh + c_h * vyh
            out[j, 5] = z; out[j, 6] = xp; out[j, 7] = yp; out[j, 8] = xh; out[j, 9] = yh
            j += 1
    return j


def simulate(c: Contact, vpx, vpy, W, rec_hz=20000.0):
    if isinstance(c, ContactMS):
        return _simulate_ms(c, vpx, vpy, W, rec_hz)
    n = len(vpx)
    dec = max(1, int(round(1.0 / (rec_hz * DT))))
    out = np.zeros((n // dec + 1, 10))
    M_v = M_HOLDER + float(np.max(W)) / G0
    c_h = 2 * ZETA_H * math.sqrt(K_H * M_H)
    m = _tribo(DT, np.ascontiguousarray(vpx, float), np.ascontiguousarray(vpy, float),
               np.ascontiguousarray(W, float), c.k_p, c.c_p, c.mu_k, c.mu_s, c.v_s, c.mu_s / c.x_pre, c.s1, c.s2,
               M_v, M_H, K_H, c_h, dec, out)
    t = np.arange(m) * dec * DT
    return t, out[:m]


def _simulate_ms(c: ContactMS, vpx, vpy, W, rec_hz):
    n = len(vpx)
    dec = max(1, int(round(1.0 / (rec_hz * DT))))
    out = np.zeros((n // dec + 1, 10))
    M_v = M_HOLDER + float(np.max(W)) / G0
    c_h = 2 * ZETA_H * math.sqrt(K_H * M_H)
    delta = c.x_pre * np.logspace(-math.log10(c.spread), math.log10(c.spread), c.n_el)
    alim = np.full(c.n_el, c.mu_s / c.n_el)
    kap = alim / delta
    m = _tribo_ms(DT, np.ascontiguousarray(vpx, float), np.ascontiguousarray(vpy, float),
                  np.ascontiguousarray(W, float), c.k_p, c.c_p, c.mu_k, c.mu_s, c.v_s, kap, alim, M_v, M_H, K_H,
                  c_h, dec, out)
    return np.arange(m) * dec * DT, out[:m]


def ripple(t, v, rng, rms=RIPPLE_RMS):
    """Velocity ripple of the linear-motor stage: pole-pitch periodic part + slow random part."""
    x = np.cumsum(v) * DT
    per = math.sqrt(2) * np.sin(2 * np.pi * x / POLE_PITCH + rng.uniform(0, 2 * np.pi))
    wn = rng.standard_normal(len(t) // 400 + 2)
    slow = np.interp(t, np.arange(len(wn)) * 400 * DT, wn)
    r = per * 0.8 + slow * 0.6
    return v * (1 + rms * r / max(np.std(r), 1e-12))


def _dirs(beta):
    return math.cos(beta), math.sin(beta)


# --------------------------------------------------------------------------- measurement
def _rot(theta):
    """Page (h, t2, n) -> pen frame (a, t1, t2) at phi = 0: a = (cos th, 0, sin th), t1 = (sin th, 0, -cos th)."""
    ct, st = math.cos(theta), math.sin(theta)
    return np.array([[ct, 0.0, st], [st, 0.0, -ct], [0.0, 1.0, 0.0]])


def measure_record(t, out, theta_set_deg, rng, session, noise_scale=1.0, cap=False):
    """F/T (pen frame, per-axis gain) + encoder (+ capacitive) as the rig records them. The pen
    sits at the set angle plus the session's hidden goniometer error."""
    th = math.radians(theta_set_deg) + session.offsets.get("theta", 0.0)
    Fpage = np.column_stack([out[:, 3], out[:, 4], out[:, 0]])     # contact force on the ball, page frame
    Fs = Fpage @ _rot(th).T
    ch = replace(FT_RIG.scaled(noise_scale), name="ft_axis")         # gains applied per axis below
    rec = {}
    for i, name in enumerate(("F_a", "F_t1", "F_t2")):
        g = session.gains.get(f"ft_axis_{i}", 1.0)
        tr, y = ins.measure(ch, t, g * Fs[:, i], rng, session)
        rec[name] = y
    rec["t"] = tr
    _, rec["x_enc"] = ins.measure(ins.ENCODER, t, out[:, 6], rng, session, noise_scale)
    _, rec["y_enc"] = ins.measure(ins.ENCODER, t, out[:, 7], rng, session, noise_scale)
    if cap:
        tc, rec["x_cap"] = ins.measure(ins.CAPACITIVE, t, out[:, 6] - out[:, 8], rng, session, noise_scale)
        rec["t_cap"] = tc
    return rec


def draw_rig_session(rng, systematic_scale=1.0):
    s = ins.draw_session(rng, systematic_scale=systematic_scale)
    for i in range(3):
        s.gains[f"ft_axis_{i}"] = 1.0 + systematic_scale * ins.FT_SENSOR.gain_bound * rng.uniform(-1, 1)
    s.offsets["theta"] = systematic_scale * ins.ANGLE.offset_bound * rng.uniform(-1, 1)
    return s


def to_page(rec, theta_deg_meas):
    Fs = np.column_stack([rec["F_a"], rec["F_t1"], rec["F_t2"]])
    Fp = Fs @ _rot(math.radians(theta_deg_meas))      # inverse of an orthonormal rotation
    return Fp[:, 0], Fp[:, 1], Fp[:, 2]                # f_h, f_t2, N


# --------------------------------------------------------------------------- datasets
def ds_indentation(c: Contact, rng, session, n_rep=3, rate=0.2, Nmax=4.0, noise_scale=1.0, k_ref=1e8):
    """B01 part 1 (force-controlled axis), plus the rig-compliance calibration on a hard flat
    (ASSUMPTION: a polished sapphire flat, treated as rigid)."""
    recs = []
    for surface in ("paper", "hard_flat"):
        cc = replace(c, k_p=k_ref, c_p=5.0) if surface == "hard_flat" else c
        for r in range(n_rep if surface == "paper" else 1):
            T = 2 * Nmax / rate
            n = int(T / DT)
            t = np.arange(n) * DT
            W = np.maximum(Nmax - np.abs(Nmax - rate * t), 0.02)
            z0 = np.zeros(n)
            tt, out = simulate(cc, z0, z0, W, rec_hz=1000.0)
            zlaser = out[:, 5] - out[:, 0] / K_RIG_V            # laser target sees the rig compliance too
            tl, yl = ins.measure(ins.LASER_TRIANG, tt, zlaser, rng, session, noise_scale, fs=100.0)
            rec = measure_record(tt, out, 50.0, rng, session, noise_scale)
            keep = {k: np.interp(tl, rec["t"], rec[k]) for k in ("F_a", "F_t1", "F_t2")}
            recs.append({"surface": surface, "t": tl, "z_laser": yl, "theta": 50.0, "rep": r, **keep})
    return {"records": recs, "bench_s": n_rep * (2 * Nmax / rate + 60) + 120.0}


def ds_sliding(c: Contact, rng, session, Ns=(0.2, 0.5, 1.0, 2.0, 4.0), betas_deg=(0, 90, 180, 270), v=0.03,
               L=0.02, dwell=1.0, n_rep=1, theta=50.0, noise_scale=1.0):
    """B01 part 2 at theta 50 deg: 20 mm strokes after a 1 s dwell (breakaway + kinetic plateau)."""
    recs = []
    for r in range(n_rep):
        for N0 in rng.permutation(Ns):
            for b in rng.permutation(betas_deg):
                T = dwell + L / v
                n = int(T / DT)
                t = np.arange(n) * DT
                sp = np.where(t < dwell, 0.0, v * np.clip((t - dwell) / 0.01, 0, 1))
                sp = ripple(t, sp, rng)
                cx, cy = _dirs(math.radians(b))
                tt, out = simulate(c, sp * cx, sp * cy, np.full(n, N0), rec_hz=5000.0)
                rec = measure_record(tt, out, theta, rng, session, noise_scale)
                rec.update({"N_set": float(N0), "beta_deg": float(b), "v_set": v, "dwell": dwell, "theta": theta})
                recs.append(rec)
    n = len(recs)
    return {"records": recs, "bench_s": n * (dwell + L / v + 15.0)}


STEP_SPEEDS = (1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.2)   # PROTOCOL EXP-B02 procedure 1 (m/s)
# proposed: quarter-decade spacing through the Stribeck transition (0.3-30 mm/s), same end points
QUARTER_SPEEDS = (1e-5, 3e-5, 1e-4, 3e-4, 5.6e-4, 1e-3, 1.8e-3, 3.2e-3, 5.6e-3, 1e-2, 1.8e-2, 3.2e-2, 0.1, 0.2)


def ds_steps(c: Contact, rng, session, speeds=STEP_SPEEDS, Ns=(0.5, 1.0, 2.0), thetas=(45.0, 60.0),
             dirs_deg=(0, 180, 90, 270), n_rep=1, dwell=1.0, noise_scale=1.0, t_max=10.0):
    recs = []
    for r in range(n_rep):
        for th in thetas:
            for N0 in Ns:
                for b in dirs_deg:
                    for v in rng.permutation(speeds):
                        T_move = float(np.clip(0.02 / v, 0.1, t_max))
                        n = int((dwell + T_move) / DT)
                        t = np.arange(n) * DT
                        sp = np.where(t < dwell, 0.0, v)
                        sp = ripple(t, sp, rng)
                        cx, cy = _dirs(math.radians(b))
                        tt, out = simulate(c, sp * cx, sp * cy, np.full(n, N0), rec_hz=5000.0)
                        rec = measure_record(tt, out, th, rng, session, noise_scale)
                        rec.update({"N_set": float(N0), "beta_deg": float(b), "v_set": float(v), "dwell": dwell,
                                    "theta": th})
                        recs.append(rec)
    bench = sum(r["t"][-1] + 10.0 for r in recs)
    return {"records": recs, "bench_s": float(bench)}


def ds_sweeps(c: Contact, rng, session, amps=(5e-6, 20e-6, 50e-6, 200e-6), speed=2e-5, cycles=2, N0=1.0,
              theta=50.0, noise_scale=1.0):
    """B02 procedure 2: slow triangular sweeps through zero velocity (pre-sliding and reversals)."""
    recs = []
    for A in amps:
        Tq = A / speed
        T = 4 * Tq * cycles + 0.5
        n = int(T / DT)
        t = np.arange(n) * DT
        ph = np.clip(t - 0.5, 0, None) / Tq
        tri = np.where((np.floor(ph) % 4 == 0) | (np.floor(ph) % 4 == 3), 1.0, -1.0)
        sp = np.where(t < 0.5, 0.0, speed * tri)
        sp = ripple(t, sp, rng)
        tt, out = simulate(c, sp, np.zeros(n), np.full(n, N0), rec_hz=10000.0)
        rec = measure_record(tt, out, theta, rng, session, noise_scale, cap=True)
        rec.update({"A": A, "speed": speed, "N_set": N0, "theta": theta})
        recs.append(rec)
    return {"records": recs, "bench_s": float(sum(r["t"][-1] + 30.0 for r in recs))}


def ds_recip(c: Contact, rng, session, n_rec=32, noise_scale=1.0, dur=2.0):
    """B02 validation (held out): sinusoidal reciprocation 3-15 Hz, 0.02-0.5 mm, +-10 mm/s drift."""
    recs = []
    for i in range(n_rec):
        f = float(rng.choice([3.0, 5.0, 8.0, 10.0, 12.0, 15.0]))
        A = float(rng.choice([2e-5, 5e-5, 1e-4, 2e-4, 5e-4]))
        N0 = float(rng.choice([0.5, 1.0, 2.0]))
        th = float(rng.choice([45.0, 60.0]))
        drift = float(rng.choice([0.0, 0.01]))
        n = int(dur / DT)
        t = np.arange(n) * DT
        sp = 2 * np.pi * f * A * np.cos(2 * np.pi * f * t) * np.clip(t / 0.2, 0, 1) + drift
        sp = ripple(t, sp, rng)
        tt, out = simulate(c, sp, np.zeros(n), np.full(n, N0), rec_hz=5000.0)
        rec = measure_record(tt, out, th, rng, session, noise_scale)
        rec.update({"f": f, "A": A, "N_set": N0, "theta": th, "drift": drift})
        recs.append(rec)
    return {"records": recs, "bench_s": float(n_rec * (dur + 15.0))}


def generate(truth_vals: Dict, rng, session=None, noise_scale=1.0, n_rep=1, reduced=False, speeds=STEP_SPEEDS):
    c = Contact.from_truth(truth_vals)
    session = session or draw_rig_session(rng)
    if reduced:
        steps = ds_steps(c, rng, session, speeds=speeds, Ns=(1.0,), thetas=(50.0,), dirs_deg=(0, 180),
                         n_rep=n_rep, noise_scale=noise_scale)
    else:
        steps = ds_steps(c, rng, session, speeds=speeds, n_rep=n_rep, noise_scale=noise_scale)
    return {"_hidden": {"theta_offset_deg": math.degrees(session.offsets["theta"])},
            "indent": ds_indentation(c, rng, session, n_rep=max(1, min(3, n_rep * 3)), noise_scale=noise_scale),
            "sliding": ds_sliding(c, rng, session, n_rep=n_rep, noise_scale=noise_scale),
            "steps": steps,
            "sweeps": ds_sweeps(c, rng, session, noise_scale=noise_scale),
            "recip": ds_recip(c, rng, session, noise_scale=noise_scale)}


# --------------------------------------------------------------------------- identification
def _secant_compliance(rec):
    _, _, N = to_page(rec, rec["theta"])
    z = rec["z_laser"]
    k = int(np.argmax(N))
    m = (N[:k] >= 0.5) & (N[:k] <= 1.5)
    r = ident.ols(np.column_stack([N[:k][m], np.ones(m.sum())]), -z[:k][m])
    return float(r["b"][0]), float(r["se"][0])


def id_paper(d):
    """Secant 0.5-1.5 N on the loading branch, minus the rig compliance from the hard flat."""
    flats = [r for r in d["records"] if r["surface"] == "hard_flat"]
    papers = [r for r in d["records"] if r["surface"] == "paper"]
    comp_rig = float(np.mean([_secant_compliance(r)[0] for r in flats]))
    comps = np.array([_secant_compliance(r)[0] for r in papers])
    comp_p = float(comps.mean() - comp_rig)
    k_p = 1.0 / comp_p
    u_c = comps.std(ddof=1) / math.sqrt(len(comps)) if len(comps) > 1 else _secant_compliance(papers[0])[1]
    u_stat = k_p * u_c / comp_p
    # laser local nonlinearity over the span (slope error ~ 4 bound / full scale), F/T normal gain,
    # rig-compliance correction (30 % of it, ASSUMPTION)
    unc = ident.combine(k_p, u_stat, rel_bounds=[4 * ins.LASER_TRIANG.nonlin_bound / ins.LASER_TRIANG.full_scale,
                                                 ins.FT_SENSOR.gain_bound, 0.3 * comp_rig / comp_p])
    return {"k_p": float(k_p), **unc, "rig_compliance_m_per_N": comp_rig}


def plateau(rec, theta_meas):
    """Steady mu over the last half of the motion (excluding the last 2 mm when sliding far)."""
    f_h, f_t2, N = to_page(rec, theta_meas)
    t = rec["t"]
    move = t > rec["dwell"]
    tm = t[move]
    T_move = tm[-1] - tm[0]
    sel = move & (t > rec["dwell"] + 0.5 * T_move)
    if rec["v_set"] * T_move > 0.006:
        sel &= t < t[-1] - 0.002 / rec["v_set"]
    mu = np.hypot(f_h[sel], f_t2[sel]) / np.maximum(N[sel], 1e-6)
    return float(np.mean(mu)), float(np.mean(N[sel]))


def breakaway(rec, theta_meas):
    f_h, f_t2, N = to_page(rec, theta_meas)
    t = rec["t"]
    x = np.hypot(rec["x_enc"], rec["y_enc"])
    first = (t > rec["dwell"]) & (x < 0.002)
    steady = (x > 0.004) & (x < 0.018)
    ft = np.hypot(f_h, f_t2)
    return float(ft[first].max() / ft[steady].mean())


def stribeck(v, g, s2N):
    mu_k, dmu, v_s = g
    return mu_k + dmu * np.exp(-(v / v_s) ** 2) + s2N * v


def _fit_stribeck(pts):
    v = np.array([p[0] for p in pts])
    mu = np.array([p[1] for p in pts])
    N = np.array([p[2] for p in pts])

    def res(q):
        mu_k, dmu, lv, s2 = q
        return (stribeck(v, (mu_k, dmu, math.exp(lv)), s2 / N) - mu) / (0.002 + 0.01 * mu)
    lo = mu[v > 0.05].mean() if np.any(v > 0.05) else mu.min()
    hi = mu[v < 2e-5].mean() if np.any(v < 2e-5) else mu.max()
    fit = ident.nls(res, [lo, max(hi - lo, 1e-3), math.log(2e-3), 0.0],
                    bounds=([0.0, -1.0, math.log(1e-5), -1.0], [2.0, 2.0, math.log(1.0), 1.0]))
    return fit


def reversal_fit(rec, theta_meas, min_amp=40e-6):
    """Fit f(dx) = A - B exp(-dx / x_c) after each reversal of the large sweeps."""
    if rec["A"] < min_amp:
        return []
    f_h, _, N = to_page(rec, theta_meas)
    fh = np.interp(rec["t_cap"], rec["t"], f_h)
    Nn = np.interp(rec["t_cap"], rec["t"], N)
    x = rec["x_cap"]
    xs = np.convolve(x, np.ones(21) / 21, mode="same")
    dx = np.diff(xs)
    sgn = np.sign(dx)
    rev = np.flatnonzero((sgn[1:] != sgn[:-1]) & (np.abs(xs[1:-1] - np.median(xs)) > 0.5 * rec["A"]))
    out = []
    last = -10 ** 9
    for i in rev:
        if i - last < 200:
            continue
        last = i
        s = int(np.sign(dx[min(i + 50, len(dx) - 1)]))
        j1 = min(len(x), i + int(0.6 * rec["A"] / rec["speed"] * 10000))
        seg = slice(i, j1)
        u = s * (x[seg] - x[i])
        y = s * fh[seg] / np.maximum(Nn[seg], 1e-6)
        m = u > -1e-7
        if m.sum() < 50:
            continue

        def res(q):
            A, B, lx = q
            return A - B * np.exp(-np.clip(u[m], 0, None) / math.exp(lx)) - y[m]
        try:
            fit = ident.nls(res, [y[m][-1], y[m][-1] - y[m][0], math.log(1e-5)],
                            bounds=([0, 0, math.log(1e-7)], [2, 4, math.log(1e-3)]))
            out.append((math.exp(fit["p"][2]), fit["p"][0]))
        except Exception:
            continue
    return out


def predict_recip(rec, cont: Contact, theta_meas):
    """Simulate a held-out record with the identified model, driven by the encoder."""
    t = rec["t"]
    x = rec["x_enc"]
    tf = np.arange(0, t[-1], DT)
    xf = np.interp(tf, t, x)
    from scipy.signal import savgol_filter
    vf = savgol_filter(xf, 201, 3, deriv=1, delta=DT)
    tt, out = simulate(cont, vf, np.zeros_like(vf), np.full(len(vf), rec["N_set"]), rec_hz=5000.0)
    f_h, _, N = to_page(rec, theta_meas)
    fp = np.interp(t, tt, out[:, 3])
    m = t > 0.3
    return ident.r2(f_h[m], fp[m]), fp


def identify(ds, rng=None, n_boot=100, theta_offset_known=0.0):
    """Blind identification from the tribometer datasets. theta_meas = setpoint (the
    goniometer error is unknown to the analyst and stays as a type-B term)."""
    th = lambda rec: rec["theta"] + theta_offset_known          # noqa: E731
    paper = id_paper(ds["indent"])
    pts = [(r["v_set"],) + plateau(r, th(r)) for r in ds["steps"]["records"]]
    fit = _fit_stribeck(pts)
    mu_k, dmu, lv, s2 = fit["p"]
    v_s = math.exp(lv)
    mu_s = mu_k + dmu
    # bootstrap over records
    se = {"mu_k": fit["se"][0], "mu_s": math.hypot(fit["se"][0], fit["se"][1]), "v_s": v_s * fit["se"][2]}
    if rng is not None:
        bs = ident.bootstrap(pts, lambda s: _fit_stribeck(s)["p"], n_boot, rng)
        if len(bs) > 10:
            se = {"mu_k": float(np.std(bs[:, 0])), "mu_s": float(np.std(bs[:, 0] + bs[:, 1])),
                  "v_s": float(np.std(np.exp(bs[:, 2])))}
    revs = [x for r in ds["sweeps"]["records"] for x in reversal_fit(r, th(r))]
    xc = np.array([x[0] for x in revs]) if revs else np.array([1e-5])
    x_pre = float(np.median(xc))
    u_x = float(1.2533 * np.std(xc) / math.sqrt(max(len(xc), 1))) if len(xc) > 1 else 0.5 * x_pre
    brk = [breakaway(r, th(r)) for r in ds["sliding"]["records"]]
    mu_sl = [plateau(r, th(r)) for r in ds["sliding"]["records"]]
    # mu(N) = mu0 + mu1 N at theta 50 (protocol B01 analysis 3)
    Nl = np.array([m[1] for m in mu_sl])
    rN = ident.ols(np.column_stack([np.ones_like(Nl), Nl]), np.array([m[0] for m in mu_sl]))
    # type B on mu: per-axis F/T gains (tangential vs normal), angle error crosstalk (N sin dth / N)
    tb_mu = [math.sqrt(2) * ins.FT_SENSOR.gain_bound, math.radians(0.1) / max(mu_k, 1e-3)]
    est = {
        "writing.mu_eff": {"value": float(mu_k), **_c(mu_k, se["mu_k"], tb_mu)},
        # ASSUMPTION 0.5 % floor: plateau settling at the slowest steps and ripple (gains cancel in the ratio)
        "writing.mu_static_ratio": {"value": float(mu_s / mu_k), **_c(mu_s / mu_k, (mu_s / mu_k) * math.hypot(
            se["mu_s"] / mu_s, se["mu_k"] / mu_k), [0.005])},
        "writing.stribeck_speed": {"value": float(v_s), **_c(v_s, se["v_s"], [RIPPLE_RMS])},
        "writing.paper_stiffness": {"value": paper["k_p"], "u": paper["u"], "U95": paper["U95"]},
        "friction.x_presliding": {"value": x_pre, **_c(x_pre, u_x, [ins.CAPACITIVE.gain_bound])},
    }
    cont = Contact(paper["k_p"], _P["writing.paper_damping"], mu_k, mu_s, v_s, x_pre)
    r2s, ys, yps, nr = [], [], [], []
    for rec in ds["recip"]["records"]:
        r2v, fp = predict_recip(rec, cont, th(rec))
        f_h, _, N = to_page(rec, th(rec))
        m = rec["t"] > 0.3
        r2s.append(r2v)
        ys.append(f_h[m])
        yps.append(fp[m])
        nr.append(float(np.sqrt(np.mean((f_h[m] - fp[m]) ** 2)) / (mu_k * rec["N_set"])))
    r2_pooled = ident.r2(np.concatenate(ys), np.concatenate(yps))
    # the same after a 50 Hz zero-phase low-pass of both signals (3-15 Hz reciprocation and harmonics)
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, 50.0, fs=5000.0, output="sos")
    r2_lp = ident.r2(np.concatenate([sosfiltfilt(sos, y) for y in ys]),
                     np.concatenate([sosfiltfilt(sos, y) for y in yps]))
    # per-record means removed: a constant tangential offset from F/T cross-axis gain errors
    # (N (g_a - g_t1) sin th cos th, up to ~1 % of N) is not friction dynamics
    r2_dyn = ident.r2(np.concatenate([y - y.mean() for y in ys]), np.concatenate([y - y.mean() for y in yps]))
    ceiling = 1 - (FT_RIG.noise_rms ** 2 + FT_RIG.lsb ** 2 / 12) / np.var(np.concatenate(ys))
    diag = {"sigma2_fit_N_s_per_m": float(s2), "breakaway_ratio_median": float(np.median(brk)),
            "mu1_per_N": float(rN["b"][1]), "mu1_se": float(rN["se"][1]), "n_reversals": len(revs),
            "recip_R2_pooled": float(r2_pooled), "recip_R2_pooled_lp50": float(r2_lp),
            "recip_R2_pooled_mean_removed": float(r2_dyn),
            "recip_R2_noise_ceiling": float(ceiling), "recip_R2_median": float(np.median(r2s)),
            "recip_R2_min": float(np.min(r2s)), "recip_NRMSE_vs_muN_median": float(np.median(nr)),
            "recip_NRMSE_vs_muN_max": float(np.max(nr)), "AC_B02_01_pooled_R2_gt_0.9": bool(r2_pooled > 0.9)}
    bench = sum(ds[k]["bench_s"] for k in ("indent", "sliding", "steps", "sweeps", "recip"))
    return {"estimates": est, "diag": diag, "bench_s": float(bench), "contact_model": cont}


def _c(v, u_stat, rel_bounds):
    c = ident.combine(v, u_stat, rel_bounds=rel_bounds)
    return {"u": c["u"], "U95": c["U95"]}
