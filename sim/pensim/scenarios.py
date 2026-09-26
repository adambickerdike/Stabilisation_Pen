"""Scenario builders: hand reference = intended path + disturbance, pen-down
schedule and push force.  All signals synthetic (see stabpen.signals)."""
from __future__ import annotations

import numpy as np

from stabpen import signals as sg
from .model import Scenario


def _assemble(intended: sg.Intended, d: np.ndarray, N0: float, theta_deg: float,
              rho_deg: float = 0.0, phi_deg: float = 0.0, opt_ok=None, meta=None):
    t = intended.t
    dt = t[1] - t[0]
    lift = intended.lift
    lift_h = max(float(lift.max()), 1e-9)
    down_frac = np.clip(1.0 - lift / lift_h, 0.0, 1.0)
    pref = np.column_stack([intended.xy + d, lift])
    vref = np.gradient(pref, dt, axis=0)
    fpush = N0 * down_frac
    if opt_ok is None:
        opt_ok = np.ones(len(t), np.uint8)
    return Scenario(t=t, pref=pref, vref=vref, fpush=fpush, dtrue=d, intended=intended.xy.copy(),
                    opt_ok=opt_ok, theta_deg=theta_deg, phi_deg=phi_deg, rho_deg=rho_deg, N0=N0,
                    meta=dict(meta or {}, features=intended.features))


def handwriting(seed=0, duration=8.0, dt=25e-6, tremor: sg.TremorSpec | None = None,
                theta_deg=50.0, N0=1.0, rho_deg=0.0, phi_deg=0.0, opt_ok=None, **kw):
    rng = np.random.default_rng(seed)
    it = sg.lognormal_handwriting(dt, duration, rng, **kw)
    if tremor is None:
        d = np.zeros_like(it.xy)
    else:
        d = sg.tremor(it.t, tremor, np.random.default_rng(seed + 1000))
    return _assemble(it, d, N0, theta_deg, rho_deg, phi_deg, opt_ok,
                     meta={"kind": "handwriting", "seed": seed, "tremor": None if tremor is None else vars(tremor)})


def features(dt=25e-6, tremor: sg.TremorSpec | None = None, theta_deg=50.0, N0=1.0, seed=0, rho_deg=0.0):
    it = sg.feature_course(dt)
    d = np.zeros_like(it.xy) if tremor is None else sg.tremor(it.t, tremor, np.random.default_rng(seed + 2000))
    return _assemble(it, d, N0, theta_deg, rho_deg, meta={"kind": "features", "seed": seed,
                                                           "tremor": None if tremor is None else vars(tremor)})


def static_hold(duration=1.5, dt=25e-6, theta_deg=50.0, N0=1.0, rho_deg=0.0):
    """Pen held still in contact (for statics verification)."""
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.ones(n, bool), lift=np.zeros(n), features=[])
    sc = _assemble(it, np.zeros((n, 2)), N0, theta_deg, rho_deg)
    ramp = np.clip(t / 0.2, 0, 1)
    sc.fpush = N0 * ramp
    return sc


def constant_velocity(duration=1.0, dt=25e-6, speed=0.03, direction_deg=0.0, theta_deg=50.0, N0=1.0, rho_deg=0.0):
    """Straight stroke at constant speed after a smooth start (friction verification)."""
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    ramp_T = 0.15
    s = np.where(t < ramp_T, speed * (t ** 2) / (2 * ramp_T), speed * (t - ramp_T / 2))
    u = np.array([np.cos(np.radians(direction_deg)), np.sin(np.radians(direction_deg))])
    xy = s[:, None] * u[None, :]
    it = sg.Intended(t=t, xy=xy, pen_down=np.ones(n, bool), lift=np.zeros(n), features=[])
    sc = _assemble(it, np.zeros((n, 2)), N0, theta_deg, rho_deg)
    sc.fpush = N0 * np.clip(t / 0.1, 0, 1)
    return sc
