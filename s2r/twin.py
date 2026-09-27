"""Plant/controller separation around M1, and the calibrated-twin outcome evaluation.

Why a shim is needed. M1 packs one parameter vector for the plant and the
controller, and several entries play both roles: m_eq, k_tip and c_tip (plant
and servo feedforward), n*K_f (actuator force and the current reference
i = -F/(n K_f)), L and R20 (coil and current-loop PI gains, computed in
model.build_params), K_n and k_ax (hand/axial plant and the controller's
gamma), imu_delay (sensor and prediction horizon), hall crosstalk (sensor and
its compensation). Overriding a plant parameter with model.build_params
therefore also tells the controller the true value. Real firmware keeps the
values it was generated with (firmware/include/params_gen.h). The shim below
rebuilds the controller-side entries from a separate "controller knowledge"
parameter set and passes them as direct layout-name overrides, which
model.build_params applies last. No file under sim/ is changed.

What it reproduces exactly: PID gains (scaled by kappa = n_t K_f,t / n_c K_f,c
so the current the firmware would command is the current M1 commands),
current-loop PI gains, gamma, horizon, hall-crosstalk compensation,
acceleration feedforward. What it approximates: the reference feedforward
m q''_r + k q_r + c q'_r uses the plant values inside the core, so a single
scale factor is fitted over 3-15 Hz (residual reported in the info dict).
What it cannot separate (documented limits, all small in these runs): the
current-loop R feedforward, the axial-slide estimate s_hat (k_ax, F_pre) and
the contact threshold (F_pre).

Evidence status of outcomes computed here: SIMULATION.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, Optional

import numpy as np

from sim.pensim import bench, evaluate, harness, model, scenarios
from sim.pensim.layout import IDX
from stabpen import params as sp_params
from stabpen import signals as sg
from . import fastharness
from . import truth as tr

_P = sp_params.load()


def geometric_m_eq() -> float:
    g = model.Geometry(L1=_P["stage.L1"], L2=_P["stage.L2"])
    return float(g.reduce()["m_eq"])


def nominal_plant(keys=None) -> Dict[str, float]:
    """Nominal values of the truth keys; stage.m_eq is M1's own geometric value."""
    v = tr.nominal(keys, _P)
    if "stage.m_eq" in v:
        v["stage.m_eq"] = geometric_m_eq()
    return v


def _get(vals: Dict, key: str) -> float:
    if key in vals:
        return float(vals[key])
    if key == "stage.m_eq":
        return geometric_m_eq()
    if key in tr.EXTRA:
        return float(tr.EXTRA[key]["value"])
    return float(_P[key])


def plant_overrides(vals: Dict[str, float]) -> Dict[str, float]:
    """M1 overrides for the plant side of a parameter set (dotted keys + m_eq/c_tip layout)."""
    ov = {k: float(v) for k, v in vals.items() if k != "stage.m_eq"}
    if "stage.m_eq" in vals or "stage.k_tip" in vals or "stage.zeta_open" in vals:
        m = _get(vals, "stage.m_eq")
        k = _get(vals, "stage.k_tip")
        z = _get(vals, "stage.zeta_open")
        ov["m_eq"] = m
        ov["c_tip"] = 2.0 * z * math.sqrt(k * m)
    return ov


def _dummy_scn(theta_deg=50.0, N0=1.0):
    t = np.zeros(2)
    z2 = np.zeros((2, 2))
    return model.Scenario(t=t, pref=np.zeros((2, 3)), vref=np.zeros((2, 3)), fpush=np.zeros(2), dtrue=z2,
                          intended=z2, opt_ok=np.ones(2, np.uint8), theta_deg=theta_deg, N0=N0)


def controller_constants(ctrl_vals: Dict, ctrl: model.Controller, theta_deg: float) -> Dict[str, float]:
    """What the firmware computes from its own parameter set (as model.build_params does)."""
    pos_bw = ctrl.pos_bw if ctrl.pos_bw is not None else _P["control.pos_bw"]
    cur_bw = ctrl.cur_bw if ctrl.cur_bw is not None else _P["control.current_bw"]
    f_stage = ctrl.f_stage if ctrl.f_stage is not None else _P["control.f_stage"]
    wc = 2 * math.pi * pos_bw
    m = _get(ctrl_vals, "stage.m_eq")
    k = _get(ctrl_vals, "stage.k_tip")
    z = _get(ctrl_vals, "stage.zeta_open")
    Kp = max(m * wc ** 2 - k, 0.0)
    Kd = max(2 * ctrl.zeta * m * wc, 0.0)
    Ki = Kp * wc * ctrl.ki_ratio
    wci = 2 * math.pi * cur_bw
    L = _get(ctrl_vals, "actuator.L")
    Rtot = _get(ctrl_vals, "actuator.R20") + _P["electrical.r_bridge"] + _P["electrical.r_shunt"]
    th = math.radians(theta_deg)
    Kn = _get(ctrl_vals, "hand.normal_stiffness")
    kax = _get(ctrl_vals, "stage.axial_k")
    gam = Kn * math.sin(th) ** 2 / (Kn * math.sin(th) ** 2 + kax) if ctrl.gamma_acc is None else ctrl.gamma_acc
    dt = 25e-6
    Ts = round(1.0 / (f_stage * dt)) * dt
    if ctrl.horizon is None:
        servo_lag = 0.0 if ctrl.ff_ref > 0 else 2 * ctrl.zeta / wc
        hor = _get(ctrl_vals, "sensing.imu_delay") + Ts / 2 + servo_lag + 1.0 / (2 * math.pi * cur_bw)
    else:
        hor = ctrl.horizon
    return {"Kp": Kp, "Kd": Kd, "Ki": Ki, "Kp_i": L * wci, "Ki_i": Rtot * wci, "gamma_acc": gam,
            "horizon": hor, "m": m, "k": k, "c": 2 * z * math.sqrt(k * m),
            "nKf": _get(ctrl_vals, "actuator.Kf"),
            "hall_ict": _get(ctrl_vals, "sensing.hall_i_crosstalk_tip")}


def shim(plant_vals: Dict[str, float], ctrl_vals: Optional[Dict[str, float]] = None,
         ctrl: Optional[model.Controller] = None, theta_deg: float = 50.0, ff_band=(3.0, 15.0)):
    """Overrides and Controller kwargs that run the TRUE plant under firmware generated from
    ctrl_vals (default: nominal YAML). Returns (overrides, ctrl_kwargs, info)."""
    ctrl = ctrl or model.Controller()
    ctrl_vals = dict(ctrl_vals or {})
    cc = controller_constants(ctrl_vals, ctrl, theta_deg)
    ov = plant_overrides(plant_vals)
    Pt, it = model.build_params(_dummy_scn(theta_deg), ctrl, overrides=ov)
    n_t, Kf_t = Pt[IDX["n_lever"]], Pt[IDX["Kf"]]
    n_c = n_t  # lever ratio is geometry: not perturbed in these experiments
    kappa = (n_t * Kf_t) / (n_c * cc["nKf"])
    m_t, k_t, c_t = Pt[IDX["m_eq"]], Pt[IDX["k_tip"]], Pt[IDX["c_tip"]]
    w = 2 * math.pi * np.linspace(ff_band[0], ff_band[1], 25)
    a_c = cc["k"] - cc["m"] * w ** 2 + 1j * cc["c"] * w
    a_t = k_t - m_t * w ** 2 + 1j * c_t * w
    s_ff = float(np.real(np.sum(np.conj(a_t) * a_c)) / np.sum(np.abs(a_t) ** 2))
    ff_resid = float(np.sqrt(np.mean(np.abs(kappa * a_c - kappa * s_ff * a_t) ** 2)))
    ov.update({"Kp": kappa * cc["Kp"], "Kd": kappa * cc["Kd"], "Ki": kappa * cc["Ki"],
               "Kp_i": cc["Kp_i"], "Ki_i": cc["Ki_i"],
               "ff_ref": kappa * ctrl.ff_ref * s_ff, "ff_accel": kappa * ctrl.ff_accel,
               "ff_contact": kappa * ctrl.ff_contact,
               "sensing.hall_ict_comp": cc["hall_ict"]})
    kw = {"gamma_acc": cc["gamma_acc"], "horizon": cc["horizon"]}
    info = {"kappa": kappa, "ff_scale": s_ff, "ff_resid_N_per_m": ff_resid,
            "ff_resid_vs_Kp": ff_resid / max(cc["Kp"], 1e-9), "controller": cc}
    return ov, kw, info


# --------------------------------------------------------------------------- outcomes (C2)
def frozen_kf(which: str = "selected"):
    """Frozen Kalman set from results/sim/estimator_selection.json (tuning seeds only)."""
    import json
    import os
    from . import ROOT
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
    return dict(sel["kfosc"][which]["params"])


def outcome_cases(ov, kw, seeds, f0s=(6.0, 9.0), amp=3e-4, kf_params=None, theta=50.0, N0=1.0,
                  duration=6.0, tag=""):
    kf = dict(kf_params or frozen_kf())
    cases = []
    for s in seeds:
        for f in f0s:
            cases.append(dict(seed=s, f0=f, amp=amp, mode="oracle", ctrl=dict(kw), overrides=ov, theta=theta,
                              N0=N0, duration=duration, distortion=False, tag=tag))
            cases.append(dict(seed=s, f0=f, amp=amp, mode="kfosc", ctrl={**kf, **kw}, overrides=ov, theta=theta,
                              N0=N0, duration=duration, distortion=(f == f0s[0]), tag=tag))
    return cases


def aggregate(rows, f0s=(6.0, 9.0)):
    out = {}
    for f in f0s:
        for mode in ("oracle", "kfosc"):
            sub = [r for r in rows if r["mode"] == mode and r["f0"] == f]
            if not sub:
                continue
            out[f"{mode}_ratio@{f:g}Hz"] = float(np.mean([r["ratio"] for r in sub]))
            out[f"neutral_e_um@{f:g}Hz"] = float(np.mean([r["base_e_rms_um"] for r in sub]))
    d = [r["distortion_um"] for r in rows if r["mode"] == "kfosc" and r["distortion_um"] > 0]
    if d:
        out["kf_distortion_um"] = float(np.mean(d))
    return out


def static_hold_power(ov, theta=50.0, N0=1.0, duration=1.2):
    """Copper loss holding the static contact load (neutral servo), as run_nominal 'static'."""
    sc = scenarios.static_hold(duration=duration, theta_deg=theta, N0=N0)
    r = model.run(sc, model.Controller(mode="neutral"), overrides=ov)
    sel = r["t"] > 0.9
    return float(r["Pcu"][sel].mean())


def device_distortion(ov, seeds, duration=6.0, theta=50.0, N0=1.0):
    vals = []
    for s in seeds:
        sc0 = fastharness.scenario(s, duration, theta, N0)
        rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=s)
        rr = model.run(sc0, model.Controller(mode="rigid"), overrides=ov, seed=s)
        vals.append(bench.device_distortion(rs, rr)["detrended_rms_um"])
    return float(np.mean(vals))


def evaluate_plant(plant_vals, ctrl_vals=None, seeds=harness.TEST_SEEDS, f0s=(6.0, 9.0), amp=3e-4, workers=2,
                   kf_params=None, device=True, theta=50.0, N0=1.0):
    """All C2 outcomes for one plant under firmware built from ctrl_vals (nominal by default)."""
    ov, kw, info = shim(plant_vals, ctrl_vals, model.Controller(), theta)
    rows = fastharness.run_cases(outcome_cases(ov, kw, seeds, f0s, amp, kf_params, theta, N0), workers)
    out = aggregate(rows, f0s)
    out["static_hold_W"] = static_hold_power(ov, theta, N0)
    if device:
        out["device_distortion_um"] = device_distortion(ov, seeds, theta=theta, N0=N0)
    out["_per_seed"] = {f"{r['mode']}@{r['f0']:g}|{r['seed']}": r["ratio"] for r in rows}
    out["_shim"] = {"kappa": info["kappa"], "ff_scale": info["ff_scale"], "ff_resid_vs_Kp": info["ff_resid_vs_Kp"]}
    return out
