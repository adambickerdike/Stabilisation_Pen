"""Inner piezo servo of the pencil stage: loop margins (CALC) and P1 scoring (SIMULATION).

Servo (sim/pencil/core.py, 10 kHz): F = ff_ref (k q_r + (c + K_d) q_r' + m q_r'') + contact-load bias
                                       + K_p e + K_i int(e) + K_d D(-q_meas)',  e = q_r - q_meas,
with K_i = k 2 pi servo_bw, K_d = 2 servo_zeta sqrt(k m) - c, K_p = servo_kp k and D a first-order derivative filter
at d_filt_hz.  loop_margins() repeats sim/pencil/run_study.servo_check (ZOH, 0.1 ms Hall delay, 2 kHz driver pole)
with the proportional term, for open-loop stage damping 0.02-0.1 and the stage stiffness at +-20 % (AMF-11 part
tolerance).  The design rule used here: phase margin >= 45 deg, gain margin >= 10 dB and peak sensitivity <= 2
(6 dB) in all those cases; the P0.1.2 servo has 46 deg / 14.5 dB / 1.57 at the worst nominal-stiffness case.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable

import numpy as np

import sim.pencil  # noqa: F401
from sim.pencil import design as D
from sim.pencil import evaluate as E
from sim.pencil import model as M

from . import metrics as MT
from .runs import TREMOR, writing

SERVO_BOUNDS = {"servo_bw": (10.0, 150.0), "servo_zeta": (0.2, 1.0), "d_filt_hz": (200.0, 3000.0), "ff_ref": (0.8, 1.1),
                "servo_kp": (0.0, 0.6)}
SERVO_LOG = ("servo_bw", "d_filt_hz")
DEFAULT = {"servo_bw": 25.0, "servo_zeta": 0.4, "d_filt_hz": 600.0, "ff_ref": 1.0, "servo_kp": 0.0}
RULE = {"pm_min_deg": 45.0, "gm_min_db": 10.0, "peak_s_max": 2.0}


def loop_margins(servo_bw=25.0, servo_zeta=0.4, d_filt_hz=600.0, servo_kp=0.0, ff_ref=1.0, stage_key="Q26",
                 zeta_open=(0.02, 0.05, 0.1), k_scales=(0.8, 1.0, 1.2), fs=10000.0, drv_bw=2000.0, delay=1e-4, n_freq=6000):
    cfg = M.PencilConfig()
    st = D.stage(stage_key)
    m, k = st.m_eq_nib, st.k_b_nib + st.k_par_nib
    c = 2 * cfg.zeta_stage * math.sqrt(k * m)
    Ts = 1.0 / fs
    Kd = max(2 * servo_zeta * math.sqrt(k * m) - c, 0.0)
    Ki = k * 2 * math.pi * servo_bw
    Kp = servo_kp * k
    w = 2 * np.pi * np.logspace(0, math.log10(fs / 2 * 0.999), n_freq)
    s = 1j * w
    z = np.exp(s * Ts)
    ad = 1 - math.exp(-2 * math.pi * d_filt_hz * Ts)
    Dz = (1 - 1 / z) / Ts * ad / (1 - (1 - ad) / z)
    C = Kp + Ki * Ts / (1 - 1 / z) + Kd * Dz
    cases = []
    for ks in k_scales:
        kk = k * ks
        for zo in zeta_open:
            cz = 2 * zo * math.sqrt(kk * m)
            G = 1 / (m * s ** 2 + cz * s + kk) * (1 - np.exp(-s * Ts)) / (s * Ts) / (1 + s / (2 * np.pi * drv_bw)) * np.exp(-s * delay)
            L = C * G
            mag, ph = np.abs(L), np.unwrap(np.angle(L))
            idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
            p180 = np.where(np.diff(np.sign(ph + np.pi)) != 0)[0]
            S = 1 / (1 + L)
            # closed-loop stability: count encirclements via the argument of 1 + L is costly; use the margins and a
            # finite peak sensitivity (an unstable loop shows negative margins here)
            pms = [180 + math.degrees(ph[i]) for i in idx]
            gms = [-20 * math.log10(mag[i]) for i in p180]
            cases.append({"k_scale": ks, "zeta_open": zo, "crossovers_Hz": [float(w[i] / 2 / np.pi) for i in idx],
                          "pm_deg": float(min(pms)) if pms else 180.0, "gm_db": float(min(gms)) if gms else 99.0,
                          "peak_S": float(np.max(np.abs(S))),
                          "compliance_mm_per_N_10Hz": float(abs(G[np.argmin(abs(w / 2 / np.pi - 10))] * S[np.argmin(abs(w / 2 / np.pi - 10))]) * 1e3)})
    nominal = [cc for cc in cases if cc["k_scale"] == 1.0]
    out = {"Kp": Kp, "Ki": Ki, "Kd": Kd, "cases": cases,
           "pm_min_deg": min(cc["pm_deg"] for cc in cases), "gm_min_db": min(cc["gm_db"] for cc in cases),
           "peak_S_max": max(cc["peak_S"] for cc in cases),
           "pm_min_nominal_deg": min(cc["pm_deg"] for cc in nominal), "gm_min_nominal_db": min(cc["gm_db"] for cc in nominal),
           "peak_S_nominal": max(cc["peak_S"] for cc in nominal),
           "label": "CALCULATION (discrete loop: ZOH, 0.1 ms Hall delay, 2 kHz driver pole)"}
    out["feasible"] = bool(out["pm_min_deg"] >= RULE["pm_min_deg"] and out["gm_min_db"] >= RULE["gm_min_db"]
                           and out["peak_S_max"] <= RULE["peak_s_max"])
    out["feasible_nominal"] = bool(out["pm_min_nominal_deg"] >= RULE["pm_min_deg"] and out["gm_min_nominal_db"] >= RULE["gm_min_db"]
                                   and out["peak_S_nominal"] <= RULE["peak_s_max"])
    return out


def feasible(p: Dict[str, float]) -> bool:
    """The margin rule at nominal stiffness (fast check used to confine the servo search)."""
    return loop_margins(**{k: v for k, v in p.items() if k in SERVO_BOUNDS}, k_scales=(1.0,), n_freq=1500)["feasible_nominal"]


def servo_cfg_kw(p: Dict[str, float]):
    return {"servo_bw": p["servo_bw"], "servo_zeta": p["servo_zeta"], "d_filt_hz": p["d_filt_hz"], "servo_kp": p["servo_kp"]}


def score_servo_seed(p: Dict[str, float], seed: int, law=None, hall_noise=1e-6, theta=50.0, duration=5.2, kalman=False):
    """Tracking error of the stage (RMS of q_r - q in contact) in the oracle run (6 Hz / 0.3 mm) and in the clean
    NEUTRAL run (holding zero against the writing loads), rail powers, oracle ratio and time at the limit."""
    from .law import tilt_range_stop
    law = law or tilt_range_stop()
    ov = {"hall_noise": hall_noise}
    cfg = law.pencil_config(overrides=ov, **servo_cfg_kw(p))
    ctrl_kw = {"ff_ref": p.get("ff_ref", 1.0)}
    sc0 = writing(seed, theta, None, duration)
    sc1 = writing(seed, theta, TREMOR, duration)
    clean = M.run(sc0, M.Controller(mode="neutral", **ctrl_kw), cfg, seed=seed + 1)
    rn = M.run(sc1, M.Controller(mode="neutral", **ctrl_kw), cfg, seed=seed + 1)
    ro = M.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, clean)), M.Controller(mode="oracle", **ctrl_kw), cfg, seed=seed + 1)
    base = E.compare(rn, clean)
    mo = E.compare(ro, clean)

    def track(r):
        c = (r["contact"] > 0) & (r["t"] > 0.5)
        e = r.xy("qr1") - r.xy("q1")
        return float(np.sqrt(np.mean(np.sum(e[c] ** 2, axis=1))) * 1e6)
    row = {"seed": seed, "track_oracle_um": track(ro), "track_neutral_um": track(clean),
           "oracle_ratio": mo["e_rms_um"] / base["e_rms_um"], "oracle_q_sat_frac": mo["q_sat_frac"],
           "P_rail_classB_mW": mo["P_rail_classB_mW"], "P_rail_recovery_mW": mo["P_rail_recovery_mW"],
           "P_neutral_classB_mW": base["P_rail_classB_mW"], "oracle_frac_vsat": mo["frac_vsat"]}
    row["track_um"] = 0.5 * (row["track_oracle_um"] + row["track_neutral_um"])
    if kalman:
        rk = M.run(sc1, M.kalman_controller(ff_ref=p.get("ff_ref", 1.0)), cfg, seed=seed + 1)
        mk = E.compare(rk, clean)
        row.update({"kalman_ratio": mk["e_rms_um"] / base["e_rms_um"], "kalman_P_rail_classB_mW": mk["P_rail_classB_mW"],
                    "kalman_q_sat_frac": mk["q_sat_frac"]})
    return row


def _task(args):
    p, seed, kw = args
    return score_servo_seed(p, seed, **kw)


def score_servo(p: Dict[str, float], seeds: Iterable[int], pool=None, **kw):
    tasks = [(p, s, kw) for s in seeds]
    rows = list(pool.map(_task, tasks)) if pool is not None else [_task(t) for t in tasks]
    agg = {k: float(np.mean([r[k] for r in rows])) for k in rows[0] if k != "seed"}
    agg["n_seeds"] = len(rows)
    return agg, rows
