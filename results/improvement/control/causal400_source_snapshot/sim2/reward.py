"""Contact-complete RL scoring, using privileged references only in the reward.

SIMULATION tooling; the weights are engineering choices, not human outcomes.
Tracking cost is charged on every *reference* pen-down sample, even when the
simulated ball has lost contact. Missing and unwanted ink have separate costs.
This prevents an agent earning a better score merely by ceasing to write.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class InkCost:
    scale_m: float = 0.3e-3
    missing_ink: float = 9.0
    extra_ink: float = 9.0

    def __post_init__(self):
        if self.scale_m <= 0 or self.missing_ink < 0 or self.extra_ink < 0:
            raise ValueError("cost scale must be positive and ink penalties nonnegative")

    def evaluate(self, ink, target, contact: bool, target_contact: bool):
        error_m = float(np.linalg.norm(np.asarray(ink) - np.asarray(target)))
        tracking = (error_m / self.scale_m) ** 2 if target_contact else 0.0
        missing = bool(target_contact and not contact)
        extra = bool(contact and not target_contact)
        return {
            "cost": tracking + self.missing_ink * missing + self.extra_ink * extra,
            "tracking_cost": tracking,
            "error_m": error_m if target_contact else 0.0,
            "missing": missing,
            "extra": extra,
            "reference_contact": bool(target_contact),
            "contact": bool(contact),
        }


class InkReference:
    """Time-aligned position and left-held contact from a separate reference run.

    Position is linearly interpolated. Contact is a discrete state and is never
    taken from a future sample. Scenario and physics sampling rates may differ.
    """

    def __init__(self, t, xy, contact):
        self.t = np.asarray(t, dtype=float)
        self.xy = np.asarray(xy, dtype=float)
        self.contact = np.asarray(contact, dtype=bool)
        if (self.t.ndim != 1 or len(self.t) < 2 or self.xy.shape != (len(self.t), 2)
                or self.contact.shape != self.t.shape or np.any(np.diff(self.t) <= 0)
                or not np.all(np.isfinite(self.t)) or not np.all(np.isfinite(self.xy))):
            raise ValueError("reference must contain finite ordered times, XY and contact")

    def at(self, t):
        j = int(np.clip(np.searchsorted(self.t, t, side="right") - 1, 0, len(self.t) - 1))
        p = np.array([np.interp(t, self.t, self.xy[:, ax]) for ax in range(2)])
        return p, bool(self.contact[j])


def sample_stepper(st):
    """Last resolved kinematic state, before the most recent mj_step2 integration.

    MuJoCo's site_xpos is produced by mj_step1, so after advance() it belongs to
    (k-1)*dt, not k*dt. The custom contact law has forces from that same state.
    """
    if st.k < 1:
        raise ValueError("advance the stepper before scoring")
    ink = st.d.site_xpos[st.pm.ids["site:ball"]][:2].copy()
    if st.law is not None:
        contact = st.law.summary()["Nb"] > st.n_thr
    else:
        # Native contacts are already resolved at the last mj_step1 state.
        from .sim import native_contact_forces
        contact = native_contact_forces(st.pm)["Nb"] > st.n_thr
    return (st.k - 1) * st.dt, ink, bool(contact)


def advance_scored(st, nsteps, reference, cost, sample_steps=None):
    """Advance with equal-time scoring at the reference tick rate by default.

    Scores every reference tick within a policy decision, including missing ink;
    an endpoint-only reward can hide high-frequency excursions and contact loss.
    The final shorter chunk receives its actual duration weight.
    """
    sample_steps = int(sample_steps or st.rdec)
    if sample_steps < 1 or nsteps < 1:
        raise ValueError("sample and advance steps must be positive")
    totals = {k: 0.0 for k in ("cost", "tracking_cost", "missing_fraction", "extra_fraction",
                              "reference_fraction", "contact_fraction", "error_sq_m2")}
    duration_steps = 0
    samples = 0
    left = min(int(nsteps), st.n - st.k)
    while left > 0:
        n = min(sample_steps, left)
        st.advance(n)
        t, ink, contact = sample_stepper(st)
        target, reference_contact = reference.at(t)
        part = cost.evaluate(ink, target, contact, reference_contact)
        for key in ("cost", "tracking_cost"):
            totals[key] += n * part[key]
        for key, src in (("missing_fraction", "missing"), ("extra_fraction", "extra"),
                         ("reference_fraction", "reference_contact"), ("contact_fraction", "contact")):
            totals[key] += n * part[src]
        totals["error_sq_m2"] += n * part["error_m"] ** 2
        duration_steps += n
        samples += 1
        left -= n
    if duration_steps == 0:
        raise RuntimeError("cannot step an exhausted episode; reset first")
    out = {k: v / duration_steps for k, v in totals.items()}
    out.update(samples=samples, duration_s=duration_steps * st.dt,
               error_rms_m=float(np.sqrt(out["error_sq_m2"] / max(out["reference_fraction"], 1e-30))),
               t=t)
    return out
