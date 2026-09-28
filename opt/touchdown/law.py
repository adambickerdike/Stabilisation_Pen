r"""Touchdown / lift feed-forward law of the pencil stage and its kinematics (proposed design; CALC).

Geometry (sim/pencil/core.py conventions, azimuth phi, roll rho, tilt theta between the pen axis and the page):
ball centre C = p_H + q1 x_H + q2 y_H + (s + |q|^2/(2 L_piv)) a.  With the ball on the page (C_z = r_b), the
refill slide splits into the part the housing height h = p_Hz - r_b imposes and the part the stage imposes:

    s = s_h + cot(theta) (u . q),   s_h = -h / sin(theta),   u = (cos rho, -sin rho)   (stage-induced slide)

and the ink (page projection of C) moves along the azimuth by

    C_xy = p_H,xy + s_h cos(theta) e_az + J q,   J q = (u . q)/sin(theta) e_az + (u_perp . q) e_perp.

Holding the ink at its working position (s_h = s_ref) therefore needs

    q_ff = sin(theta) cos(theta) (s_ref - s_h) u                                  (kinematic law)

with s_h estimated from the axial sensor as s_meas - kappa cot(theta) (u . q_Hall) (kappa = 1 removes the stage's
own contribution; without it the loop through the slide has gain -cos^2(theta)).  While the refill rests on its
front stop (s = s_min, ball in the air) the same formula has the fixed point

    q_pre = (s_ref - s_min) cot(theta) u                                          (pre-positioning)

so the ball lands where it writes, and the stage returns to zero as the refill retracts.  With the adaptive stop
s_min = -margin, so q_pre = (margin + s_ref) cot(theta): 0.25 mm at 0.30 mm margin and 50 deg, which uses 85 % of
the 0.30 mm usable travel (the brief's estimate of 0.15 mm, sin cos x margin, omits that the pre-deflected ball
lands higher up the descent).  With pre-positioning the ball first touches when the housing is margin/sin(theta)
above its working height, instead of margin x sin(theta) without it.

The simulator implementation is in sim/pencil/core.py (td_* parameters); TouchdownLaw maps onto it.
Evidence status: CALCULATION (kinematics) and PROPOSED DESIGN (the law).  Nothing is measured.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional

import numpy as np

# bounds of the tuned parameters (SI) used by the optimisers; see TouchdownLaw for meanings
BOUNDS = {
    "margin": (0.10e-3, 0.40e-3),
    "gain": (0.6, 1.3),
    "kappa": (0.5, 1.2),
    "pre": (0.0, 1.2),
    "lead_s": (0.0, 3.0e-3),
    "lp_hz": (50.0, 400.0),
    "dz": (0.0, 60e-6),
    "k_load": (0.6, 1.5),
    "det_s": (8e-6, 60e-6),
    "det_e": (0.0, 30e-6),
    "hold_s": (1e-3, 10e-3),
    "v_td": (0.0, 0.08),
}
LOG_PARAMS = ("lp_hz",)


@dataclass
class TouchdownLaw:
    """Touchdown / lift feed-forward plus the tilt-adaptive front-stop margin.

    margin   front stop beyond the protrusion the current tilt needs (m); None = tilt-range stop (P0.1.2)
    enabled  False = adaptive stop (or tilt-range stop) alone, no feed-forward
    gain     kinematic gain on the ideal sin(th) cos(th) (1 = ideal)
    kappa    fraction of the stage-induced slide cot(th) (u.q) removed from the measured slide (1 = ideal)
    s_ref    working slide (m); None = static equilibrium of the skid and ball indentations (model.working_slide)
    lead_s   prediction horizon of the alpha-beta tracker on s_h (s): beats the 1 ms sensor delay and stage lag
    lp_hz    alpha-beta tracker bandwidth (Hz)
    pre      pre-positioning gain while the refill rests on its stop (1 = land where it writes)
    dz       dead zone on s_ref - s_h (m): the law is silent in steady writing (no command noise at the nib)
    prio     travel priority: 0 shared (sum tapered), 1 feed-forward first, 2 tremor first
    bias     1: the static contact-load bias is switched at once by the feed-forward's contact state; 0: legacy ramp
    k_load   gain of that bias (1 = N_nib0 cos(theta), the static normal load)
    det_s    slide above the stop that signals contact (m)
    det_e    Hall-error threshold along the load direction for an early touchdown detection (m); 0 = off
    hold_s   debounce between contact-state changes and quiet time that arms the Hall detection (s)
    v_td     descent speed assumed after a Hall-detected touchdown until the slide is measured (m/s); 0 = off
    handover 1: when the bias switches on (off), the servo integrator hands over the load share it already carries
             (drops a negative share), so a slow touchdown or lift gets no force step
    """
    margin: Optional[float] = 0.30e-3
    enabled: bool = True
    gain: float = 1.0
    kappa: float = 1.0
    s_ref: Optional[float] = None
    lead_s: float = 0.0
    lp_hz: float = 200.0
    pre: float = 1.0
    dz: float = 20e-6
    prio: int = 1
    bias: int = 1
    k_load: float = 1.0
    det_s: float = 20e-6
    det_e: float = 0.0
    hold_s: float = 2e-3
    v_td: float = 0.0
    handover: int = 1
    overrides: Dict = field(default_factory=dict)   # further simulator overrides (e.g. a faster axial sensor)

    def ff_dict(self) -> Optional[dict]:
        if not self.enabled:
            return None
        d = {k: getattr(self, k) for k in ("gain", "kappa", "s_ref", "lead_s", "lp_hz", "pre", "dz", "prio", "bias",
                                            "k_load", "det_s", "det_e", "hold_s", "v_td", "handover")}
        d["prio"] = int(round(d["prio"])); d["bias"] = int(round(d["bias"])); d["handover"] = int(round(d["handover"]))
        if d["det_e"] < 2e-6:          # below 2 Hall noise sigma the detector is off
            d["det_e"] = 0.0
        return d

    def pencil_config(self, **cfg_kw):
        """PencilConfig for this law (sim.pencil.model); extra keyword arguments pass through."""
        from sim.pencil import model as M
        ov = dict(cfg_kw.pop("overrides", {}))
        if self.margin is not None:
            ov.update({"s_min": -self.margin, "s_init": -self.margin})
        ov.update(self.overrides)
        return M.PencilConfig(overrides=ov, touchdown_ff=self.ff_dict(), **cfg_kw)

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_vector(cls, names, x, **fixed):
        kw = dict(fixed)
        for n, v in zip(names, x):
            kw[n] = float(v)
        return cls(**kw)


def tilt_range_stop() -> TouchdownLaw:
    return TouchdownLaw(margin=None, enabled=False)


def adaptive_stop(margin=0.30e-3) -> TouchdownLaw:
    return TouchdownLaw(margin=margin, enabled=False)


# ------------------------------------------------------------------ kinematics (CALC)
def ink_shift(h, q1, theta):
    """Page shift of the ink along the azimuth (rho = 0, ball on the page): -h cot(th) + q1/sin(th)."""
    return -h / math.tan(theta) + q1 / math.sin(theta)


def slide(h, q1, theta):
    """Refill slide with the ball on the page (rho = 0): s = -h/sin(th) + q1 cot(th)."""
    return -h / math.sin(theta) + q1 / math.tan(theta)


def q_ff_ideal(s_meas, q_meas, theta, s_ref=0.0, gain=1.0, kappa=1.0, rho=0.0):
    """Kinematic law in housing axes from a measured slide and Hall-measured stage deflection (2-vector)."""
    u = np.array([math.cos(rho), -math.sin(rho)])
    s_h = s_meas - kappa / math.tan(theta) * float(u @ np.asarray(q_meas, float))
    return gain * math.sin(theta) * math.cos(theta) * (s_ref - s_h) * u


def q_pre(margin, theta, s_ref=0.0):
    """Pre-positioning deflection with the refill on a stop at s_min = -margin (m)."""
    return (s_ref + margin) / math.tan(theta)


def contact_height(margin, theta, pre=1.0, s_ref=0.0):
    """Housing height above its working height at the ball's first contact, with a fraction pre of q_pre."""
    q = pre * q_pre(margin, theta, s_ref)
    return q * math.cos(theta) + margin * math.sin(theta)


def slide_tail(margin, theta):
    """Ink slide of one touchdown (or lift) without feed-forward: margin x cos(theta) (CALC, rigid stage)."""
    return margin * math.cos(theta)


def air_loop_gain(theta, gain=1.0, kappa=1.0):
    """Gain of the in-air fixed-point iteration q <- gain kappa cos^2(th) q + c (stable below 1)."""
    return gain * kappa * math.cos(theta) ** 2


def contact_loop_gain_without_removal(theta, gain=1.0):
    """Loop gain through the physical slide if the stage-induced part is not removed: -gain cos^2(th)."""
    return -gain * math.cos(theta) ** 2


def travel_table(margins=(0.1e-3, 0.2e-3, 0.3e-3, 0.4e-3), thetas_deg=(35.0, 50.0, 75.0), q_usable=0.30e-3):
    """Pre-positioning travel against the usable travel, per margin and tilt (CALC)."""
    rows = []
    for th in thetas_deg:
        t = math.radians(th)
        for m in margins:
            qp = q_pre(m, t)
            rows.append({"theta_deg": th, "margin_mm": m * 1e3, "q_pre_mm": qp * 1e3, "fraction_of_usable": qp / q_usable,
                         "contact_height_pre_mm": contact_height(m, t) * 1e3, "contact_height_nopre_mm": contact_height(m, t, 0.0) * 1e3,
                         "slide_tail_nopre_mm": slide_tail(m, t) * 1e3,
                         "max_neg_q1_before_stop_mm": m * math.tan(t) * 1e3})
    return rows
