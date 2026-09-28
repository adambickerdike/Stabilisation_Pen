r"""Adjoint (reverse-mode autodiff) design optimisation on differentiable models (PyTorch, CPU, 2 threads).

1. nose_design: the Rev H active-nose actuator.  Continuous variables: gimbal position z_p, magnet arm length L_b = z_a - z_p,
   magnet face width w and length l, magnet thickness t_m, coil thickness t_c, usable tip travel X.
   Model (CALC; inputs ASSUMPTION unless marked):
     lever lambda = z_p / L_b (tip motion per magnet motion), magnet stroke s = X / lambda
     gap flux B_g = eta_leak B_r t_m / (t_m + t_c + g0)     (B_r 1.33 T N45, AMF-28; eta_leak 0.55; g0 0.5 mm)
     Km per axis = sqrt(2) eta_end B_g sqrt(k_fill V_active / rho_Cu), V_active = 2 w l t_c   (k_fill 0.6, eta_end 0.8,
                  rho_Cu AMF-29; two magnets per axis, push-pull)
     calibration check: the same formula gives 0.7-1.0 N/sqrt(W) for the 15.9 mm Moticont volumes (AMF-02, AMF-73)
     moving inertia about the gimbal: nose tube + refill + arm + 4 magnets; m_eff = I / z_p^2 at the tip
     design duty (per axis): tip motion 1.0 mm rms at 8 Hz plus 0.03 N rms residual load (bias on) and the gimbal spring
     power P = 2 (F_tip_rms lambda / Km)^2 + base; peak at 2 mm, 12 Hz must stay under the drive limit (1.5 A, 3.7 V)
     stroke constraint: s <= (l - 2 mm)/2 (the magnet stays over the coil), travel X >= X_min
     mass: magnets + copper + back iron (steel 7.8 g/cm3, 1 mm) + the arm
   Objective: P + mu_m * mass, swept over mu_m for a power-mass front; gradients by autograd; Adam then L-BFGS.
2. rm_design: rear-cap reaction mass (mass, lateral stroke via the slug diameter, position, centring frequency) against the
   frictionless linear-model bound of sim/handpen/linear (assembled differentiably here), per grip split.
Evidence status: CALCULATION (design models); the chosen designs are then checked in the time-domain model H1 (SIM).
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np
import torch

torch.set_num_threads(2)
DT = torch.float64

RHO_MAG = 7.5e3        # NdFeB (ASSUMPTION handbook value)
RHO_CU = 8.89e3        # AMF-29
RES_CU = 1.7241e-8     # AMF-29
BR = 1.33              # AMF-28 (N45 low end)
RHO_FE = 7.8e3         # ASSUMPTION (soft iron back iron)


def _sp(x, lo, hi):
    """Bounded reparametrisation: raw -> lo + (hi - lo) sigmoid(raw)."""
    return lo + (hi - lo) * torch.sigmoid(x)


NOSE_BOUNDS = {"z_p": (0.030, 0.075), "L_b": (0.015, 0.060), "w": (3e-3, 8e-3), "l": (5e-3, 16e-3), "t_m": (1.5e-3, 5e-3),
               "t_c": (0.8e-3, 3.5e-3), "X": (2.0e-3, 4.0e-3)}


def nose_model(v: Dict[str, torch.Tensor], eta_leak=0.55, eta_end=0.8, k_fill=0.6, g0=0.5e-3, f_duty=8.0, x_rms=1.0e-3,
               F_res=0.03, k_r=0.025, X_min=3.0e-3, I_peak=1.5, V_bus=3.7):
    z_p, L_b, w, l, t_m, t_c, X = (v[k] for k in ("z_p", "L_b", "w", "l", "t_m", "t_c", "X"))
    lam = z_p / L_b
    s = X / lam
    Bg = eta_leak * BR * t_m / (t_m + t_c + g0)
    V_act = 2 * w * l * t_c
    Km = math.sqrt(2) * eta_end * Bg * torch.sqrt(k_fill * V_act / RES_CU)
    R_axis = None
    m_mag = 4 * RHO_MAG * w * l * t_m
    # nose: Ti tube 7/6 mm from the tip to the gimbal (4.5 g/cm3), refill 0.84 g at 34.5 mm, Al arm d5 over L_b, clamp 0.6 g
    m_tube = 4.5e3 * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * z_p
    m_arm = 2.7e3 * math.pi / 4 * 0.005 ** 2 * L_b
    I = (m_tube * (z_p ** 2 / 3) + 0.84e-3 * (0.0345 - z_p) ** 2 + 0.4e-3 * z_p ** 2 + m_arm * L_b ** 2 / 3
         + (m_mag + 0.6e-3) * L_b ** 2)
    m_eff = I / z_p ** 2
    k_s = k_r / z_p ** 2
    w_d = 2 * math.pi * f_duty
    F_tip = torch.sqrt((m_eff * w_d ** 2 * x_rms) ** 2 + (k_s * x_rms) ** 2 + F_res ** 2)
    P_axis = (F_tip * lam / Km) ** 2
    P = 2 * P_axis
    # peak: 2 mm at 12 Hz (+0.1 N load)
    F_pk_tip = m_eff * (2 * math.pi * 12.0) ** 2 * 2e-3 + k_s * 2e-3 + 0.1
    F_pk_act = F_pk_tip * lam
    # coil resistance from the active volume (turns sized to the 3.7 V bus at I_peak: Kf = Km sqrt(R))
    m_cu = RHO_CU * k_fill * V_act * 1.4 * 2          # 2 axes, end turns +40 %
    m_fe = RHO_FE * 2 * (w + 2e-3) * (l + 2e-3) * 1.0e-3 * 2 * 2
    mass = m_mag + m_cu + m_fe + m_arm + 0.6e-3
    # constraints (penalties): stroke within the coil, peak force within the drive (F_pk <= Km sqrt(V_bus I_peak)),
    # travel at least X_min, the arm swing fits a 19 mm bore: s + t_m + t_c + 2.5 mm (arm radius) <= 9.5 mm
    c_stroke = torch.relu(s - (l - 2e-3) / 2) / 1e-3
    c_peak = torch.relu(F_pk_act - Km * math.sqrt(V_bus * I_peak)) / 0.1
    c_trav = torch.relu(X_min - X) / 1e-3
    c_bore = torch.relu(s + t_m + t_c + 2.5e-3 + 0.5e-3 - 9.5e-3) / 1e-3
    return {"lambda": lam, "stroke": s, "Bg": Bg, "Km": Km, "Km_tip": Km / lam, "m_eff": m_eff, "I": I, "P": P, "F_tip_rms": F_tip,
            "F_pk_act": F_pk_act, "mass": mass, "m_mag": m_mag, "pen": c_stroke ** 2 + c_peak ** 2 + c_trav ** 2 + c_bore ** 2}


def nose_optimise(mu_mass=2.0, n_start=6, seed=0, iters=600, fixed=None):
    """Minimise P [W] + mu_mass [W/kg] * mass + 10 * penalties over the bounded variables (Adam, then L-BFGS)."""
    g = torch.Generator().manual_seed(seed)
    best = None
    for s_ in range(n_start):
        raw = {k: torch.randn(1, generator=g, dtype=DT).requires_grad_(True) for k in NOSE_BOUNDS}
        params = list(raw.values())
        opt = torch.optim.Adam(params, lr=0.05)

        def obj():
            v = {k: _sp(raw[k], *NOSE_BOUNDS[k]) for k in NOSE_BOUNDS}
            if fixed:
                for k, val in fixed.items():
                    v[k] = torch.tensor([val], dtype=DT)
            o = nose_model(v)
            return (o["P"] + mu_mass * o["mass"] + 10.0 * o["pen"]).sum(), v, o

        for it in range(iters):
            opt.zero_grad()
            J, v, o = obj()
            J.backward()
            opt.step()
        lb = torch.optim.LBFGS(params, max_iter=200, line_search_fn="strong_wolfe")

        def closure():
            lb.zero_grad()
            J, _, _ = obj()
            J.backward()
            return J
        lb.step(closure)
        J, v, o = obj()
        if best is None or J.item() < best[0]:
            best = (J.item(), {k: float(x.item()) for k, x in v.items()}, {k: float(x.item()) for k, x in o.items()})
    return {"J": best[0], "x": best[1], "out": best[2], "mu_mass": mu_mass}


def nose_grad_check(v0=None, eps=1e-7):
    """Autograd against central differences on P + mass (CALC; test)."""
    v0 = v0 or {k: 0.5 * (a + b) for k, (a, b) in NOSE_BOUNDS.items()}
    x = {k: torch.tensor([val], dtype=DT, requires_grad=True) for k, val in v0.items()}
    o = nose_model(x)
    J = (o["P"] + o["mass"]).sum()
    J.backward()
    out = {}
    for k in v0:
        vp = dict(v0); vm = dict(v0)
        vp[k] += eps * max(abs(v0[k]), 1e-3); vm[k] -= eps * max(abs(v0[k]), 1e-3)
        fp = nose_model({kk: torch.tensor([vv], dtype=DT) for kk, vv in vp.items()})
        fm = nose_model({kk: torch.tensor([vv], dtype=DT) for kk, vv in vm.items()})
        fd = ((fp["P"] + fp["mass"]) - (fm["P"] + fm["mass"])).item() / (2 * eps * max(abs(v0[k]), 1e-3))
        out[k] = (float(x[k].grad.item()), fd)
    return out
