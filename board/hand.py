"""How far a guidance force moves the pen in a writer's hand (CALC).

Model (per axis, in the paper plane), after HAP-26 and config/parameters.yaml:

    pen (mass m_p) -(k1 || b1, grip)- hand/arm mass M -(k2 || b2, arm)- intended path

The board's force F acts on the pen.  With the intended path held still, the
pen deviates by X(jw) = F(jw) * H(jw).  This is a passive impedance model: it
describes a writer who does not voluntarily resist.  A writer who resists is
modelled by a stiffer, better damped arm (co-contraction, HAP-26 upper 95 %
CI) or, in the limit, by an arm that holds its position so only the grip
yields.

Paper friction is not in the linear model; ``friction_deadband`` gives the
static force the board must exceed to move a pen that is standing still.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math

import numpy as np

from . import params as P


@dataclass
class HandCase:
    name: str
    k1: float
    b1: float
    M: float
    k2: float
    b2: float
    m_pen: float
    label: str
    note: str = ""


def cases() -> list:
    H = P.HAND
    mp = P.PEN["pen_mass_kg"].value
    k1, b1, M, k2, b2 = (H[k].value for k in ("k1", "b1", "M", "k2", "b2"))
    return [
        HandCase("relaxed", k1, b1, M, k2, b2, mp, "LIT HAP-26 nominal",
                 "the writer lets the board lead; passive grip and arm"),
        HandCase("relaxed_compliant", H["k1_range"].value[0], 0.87, M, H["k2_range"].value[0], H["b2_range"].value[0], mp,
                 "LIT HAP-26 lower 95 % CI", "soft grip, soft arm"),
        HandCase("lightly_resisting", k1, b1, M, H["k2_range"].value[1], H["b2_range"].value[1], mp,
                 "LIT HAP-26 upper 95 % CI for the arm (ASSUMPTION: co-contraction = light resistance)",
                 "arm stiffened by co-contraction"),
        HandCase("hand_held_still", k1, b1, M, 1e9, 0.0, mp, "CALC limit (ASSUMPTION)",
                 "arm holds its position; only the grip yields"),
    ]


def compliance(case: HandCase, f_hz) -> np.ndarray:
    """Complex pen displacement per unit force (m/N) at frequencies f_hz."""
    w = 2 * np.pi * np.atleast_1d(np.asarray(f_hz, float))
    s = 1j * w
    z1 = case.k1 + case.b1 * s                 # grip
    z2 = case.k2 + case.b2 * s + case.M * s ** 2  # arm + hand mass (hand side, to ground)
    # pen node: m_p s^2 X + z1 (X - Xm) = F ; hand node: z1 (Xm - X) + (k2 + b2 s) Xm + M s^2 Xm = 0
    zarm = case.k2 + case.b2 * s
    zm = case.M * s ** 2 + zarm
    # eliminate Xm: Xm = z1 X / (z1 + zm)
    zin = case.m_pen * s ** 2 + z1 * zm / (z1 + zm)
    return 1.0 / zin


def deflection_table(freqs=(0.0, 1.0, 2.0, 4.0, 8.0), force_N: float = 0.1) -> list:
    out = []
    for c in cases():
        H = compliance(c, [max(f, 1e-4) for f in freqs])
        out.append({"case": c.name, "label": c.label, "note": c.note, "force_N": force_N,
                    **{f"deflection_mm_at_{f:g}Hz": float(abs(h) * force_N * 1e3) for f, h in zip(freqs, H)}})
    return out


def force_for_correction(correction_mm: float, f_hz: float, case: HandCase) -> float:
    """Force amplitude (N) that moves the pen by correction_mm at frequency f_hz (passive writer)."""
    h = abs(compliance(case, [max(f_hz, 1e-4)])[0])
    return correction_mm * 1e-3 / h


def friction_deadband(normal_extra_N: float = 0.0) -> dict:
    """Static friction the board must beat to move a pen that stands still (CALC)."""
    mu = P.HAND["mu_paper"].value
    Nw = P.HAND["writing_force_N"].value
    mu_s = mu * 1.3  # config writing.mu_static_ratio (ASSUMPTION)
    return {"mu_kinetic": mu, "mu_static": mu_s, "writing_force_N": Nw, "magnetic_normal_N": normal_extra_N,
            "static_friction_N": mu_s * (Nw + normal_extra_N), "kinetic_friction_N": mu * (Nw + normal_extra_N),
            "label": "CALC from ASSUMPTION mu (config writing.mu_eff, mu_static_ratio)"}


def nudge_vs_steer(force_N: float = 0.3, freqs=(0.5, 1.0, 2.0, 4.0)) -> list:
    """Path correction a force produces when the writer does not resist, per case and frequency."""
    rows = []
    for c in cases():
        r = {"case": c.name, "force_N": force_N}
        for f in freqs:
            r[f"correction_mm_at_{f:g}Hz"] = float(abs(compliance(c, [f])[0]) * force_N * 1e3)
        r["static_correction_mm"] = float(abs(compliance(c, [1e-4])[0]) * force_N * 1e3)
        rows.append(r)
    return rows


def forces_needed(corrections_mm=(1.0, 3.0), freqs=(1.0, 4.0)) -> list:
    rows = []
    for c in cases():
        for d in corrections_mm:
            for f in freqs:
                rows.append({"case": c.name, "correction_mm": d, "f_Hz": f,
                             "force_N": float(force_for_correction(d, f, c))})
    return rows


def step_response(case: HandCase, force_N: float, t_end: float = 1.0, dt: float = 1e-4) -> dict:
    """Pen deviation under a force step, passive writer (CALC, explicit integration)."""
    n = int(t_end / dt)
    x = v = xm = vm = 0.0
    xs = np.empty(n)
    for i in range(n):
        f_grip = case.k1 * (x - xm) + case.b1 * (v - vm)
        a = (force_N - f_grip) / case.m_pen
        am = (f_grip - case.k2 * xm - case.b2 * vm) / case.M if case.k2 < 1e8 else 0.0
        v += a * dt
        x += v * dt
        if case.k2 < 1e8:
            vm += am * dt
            xm += vm * dt
        xs[i] = x
    t = np.arange(n) * dt
    final = xs[-1]
    i90 = int(np.argmax(np.abs(xs) >= 0.9 * abs(final))) if final != 0 else 0
    return {"t": t, "x": xs, "final_mm": final * 1e3, "t90_s": float(t[i90]), "peak_mm": float(np.max(np.abs(xs)) * 1e3)}


def as_dicts():
    return [asdict(c) for c in cases()]
