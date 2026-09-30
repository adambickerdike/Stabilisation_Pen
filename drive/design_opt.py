"""Differentiable sizing of the two best heel drives and its optimisation (CALC; PROPOSED DESIGN).

Concepts: 'wheel' = the steered and driven wheel (powered cobot); 'ball' = the driven ball (two rollers).
Continuous design variables: element radius r_e (wheel or ball), gear ratio G (relaxed to a continuous value, then
snapped to the catalogue ratios), spring preload P, and for the ball the roller radius r_r.  Discrete: the motor
(catalogue), enumerated.

The model is smooth, cheap and analytic, so reverse-mode automatic differentiation (torch autograd, i.e. the adjoint of
the model) gives exact gradients; Adam from several starts finds the optimum for every weight set, and the gradients
are checked against central finite differences.  Bayesian optimisation is used instead for the control gains
(tune.py), where each evaluation is a noisy, non-smooth closed-loop simulation.

What the model says (CALC, each term labelled in `evaluate`):
  * traction every writer gets:       E_w[ mu_lo * min(P, N_heel,w) ]  over the CON-01 writer-force distribution;
  * share of writers with full force: P(N_heel >= P);
  * motor force (continuous):          tau_c G eta(G) / r_out;  eta = 0.9 per planetary stage (MFR AMF-102/103 class);
  * speed:                             omega_0(3.7 V) r_out / G  >= 0.15 m/s;
  * reflected mass (feel):             J G^2 / r_out^2;
  * back-drive force:                  tau_f G / (eta r_out);
  * copper power at 0.15 N RMS:        R (F r_out / (k_t G eta))^2;
  * heel size:                         contact radius R_d(r_e[, r_r]) with the mechanism on top (geometry.py
                                      wheel_pod / ball_pod, linear fits) - 6.75 mm of today's ring;
  * rolling resistance:                Persson mu_rr = 2.34 (p_a/E) tan(delta) (AMF-112) with Hertz p_a;
  * ball only:                         the orthogonal roller's axial scrub 0.3 x preload (LIT AMF-117).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np
import torch

from . import catalog as CT
from .params import CONTACT, WRITING

# Keep physical calculations in float64 without changing the caller's ML defaults.
torch.set_num_threads(1)

V_BATT = 3.7
MU_LO, MU_HI = CONTACT["mu_drive_range"].value
F_TYP = 0.15
N_BALL = WRITING["F_c_refill"].value / math.sin(math.radians(50.0))
# geometry fits (mm), exact to 0.001 mm over r_e 0.75-2.0 mm (CALC, geometry.wheel_pod / ball_pod): the heel contact
# radius needed so that the element AND the mechanism on top of it (steering ring; drive rollers) clear the nose
RD_WHEEL = (6.531, 2.145)            # R_d = a + b r_e
RD_BALL = (5.459, 1.674, 2.235)      # R_d = a + b r_e + c r_r
R_E_MIN = 1.0          # mm, smallest wheel radius with a replaceable O-ring tyre (ASSUMPTION)


def _lognorm_params():
    m, s = WRITING["N_mean"].value, WRITING["N_between_sd"].value
    sig2 = math.log(1.0 + (s / m) ** 2)
    return math.log(m) - 0.5 * sig2, math.sqrt(sig2)


LN_MU, LN_SIG = _lognorm_params()
_Q = np.linspace(0.005, 0.995, 99)
from scipy.stats import norm as _norm  # noqa: E402

WRITER_N = torch.tensor(np.clip(np.exp(LN_MU + LN_SIG * _norm.ppf(_Q)), WRITING["N_min_writer"].value,
                                WRITING["N_max_writer"].value), dtype=torch.float64)


def softmin(a, b, k=40.0):
    return -torch.logsumexp(torch.stack([-k * a, -k * b]), 0) / k


def evaluate(x: torch.Tensor, motor: CT.Motor, concept: str = "wheel") -> Dict[str, torch.Tensor]:
    """x = [log(r_e/1 mm), log(G), P (N), log(r_r/1 mm)] -> performance terms (torch, differentiable)."""
    r_e = torch.exp(x[0]) * 1e-3
    G = torch.exp(x[1])
    P = x[2]
    r_r = torch.exp(x[3]) * 1e-3
    r_out = r_e if concept == "wheel" else r_r
    stages = torch.clamp(torch.log(G) / math.log(4.0), min=0.0)
    eta = 0.9 ** stages
    tau_c = motor.tau_cont_mNm * CT.MNM
    kt = motor.kt_mNm_A * CT.MNM
    w0 = motor.n0_at(V_BATT) * 2.0 * math.pi / 60.0
    F_mot = tau_c * G * eta / r_out
    v_max = w0 * r_out / G
    m_r = motor.J() * G ** 2 / r_out ** 2
    F_bd = motor.tau_fric_mNm * CT.MNM * G / (eta * r_out)
    P_cu = motor.R_ohm * (F_TYP * r_out / (kt * G * eta)) ** 2
    Nh = torch.clamp(WRITER_N - N_BALL, min=0.0)
    Nd = softmin(Nh, P.expand_as(Nh), 60.0)
    F_tr_writers = MU_LO * Nd
    F_use = softmin(F_tr_writers, F_mot.expand_as(F_tr_writers), 60.0)
    share_full = torch.sigmoid((Nh - P) / 0.02).mean()
    E_tyre = CONTACT["E_tyre"].value
    rho = torch.clamp(0.3 * r_e, max=0.5e-3) if concept == "wheel" else r_e     # O-ring cord 0.6 r_e (0.6 mm at r_e 1 mm)
    Re = torch.sqrt(r_e * rho)
    a = (3.0 * P * Re / (4.0 * E_tyre / 0.75)) ** (1.0 / 3.0)
    p_a = P / (math.pi * a * a)
    mu_rr = 2.34 * p_a / E_tyre * CONTACT["tan_delta"].value
    F_rr = mu_rr * P
    R_d = (RD_WHEEL[0] + RD_WHEEL[1] * r_e * 1e3 if concept == "wheel"
           else RD_BALL[0] + RD_BALL[1] * r_e * 1e3 + RD_BALL[2] * r_r * 1e3)
    dR = R_d - 6.75
    scrub = torch.tensor(0.3 * (0.6 / 0.8) if concept == "ball" else 0.0, dtype=torch.float64)
    mass = motor.mass_g * (2.0 if concept in ("wheel", "ball") else 1.0) + 2.0 + 0.4 * stages * 2.0
    return {"r_e_mm": r_e * 1e3, "G": G, "P_N": P, "r_r_mm": r_r * 1e3, "eta": eta, "F_mot_N": F_mot,
            "v_max_m_s": v_max, "m_r_g": m_r * 1e3, "F_bd_N": F_bd, "P_cu_W": P_cu, "F_use_mean_N": F_use.mean(),
            "F_use_p10_N": torch.quantile(F_use, 0.10), "share_full": share_full, "F_rr_N": F_rr, "R_d_mm": R_d,
            "dR_mm": dR, "scrub_N": scrub, "mass_g": torch.as_tensor(mass, dtype=torch.float64), "mu_rr": mu_rr}


def objective(x, motor, concept, w: Dict[str, float]):
    t = evaluate(x, motor, concept)
    J = -t["F_use_mean_N"] / 0.3
    J = J + w.get("dR", 0.15) * t["dR_mm"] ** 2
    J = J + w.get("m_r", 0.02) * t["m_r_g"]
    J = J + w.get("P_cu", 2.0) * t["P_cu_W"]
    J = J + w.get("F_rr", 5.0) * t["F_rr_N"] + w.get("F_bd", 5.0) * (t["F_bd_N"] + t["scrub_N"])
    # constraints as smooth penalties
    J = J + 50.0 * torch.relu(0.15 - t["v_max_m_s"]) ** 2 / 0.01
    J = J + 50.0 * torch.relu(0.5 - t["F_mot_N"]) ** 2
    J = J + 20.0 * torch.relu(0.7 - t["share_full"]) ** 2
    # manufacturing bounds (ASSUMPTION): an O-ring tyre needs a wheel of at least 2 mm diameter; ball rollers
    # 0.4-1.0 mm radius fit the pod
    J = J + 200.0 * torch.relu(R_E_MIN - t["r_e_mm"]) ** 2 + 20.0 * torch.relu(t["r_e_mm"] - 3.0) ** 2
    J = J + 200.0 * torch.relu(t["r_r_mm"] - 1.0) ** 2
    J = J + 50.0 * torch.relu(0.15 - t["P_N"]) ** 2 + 50.0 * torch.relu(t["P_N"] - 1.2) ** 2
    J = J + 20.0 * torch.relu(1.0 - t["G"]) ** 2 + 20.0 * torch.relu(0.4 - t["r_r_mm"]) ** 2
    return J, t


def optimise(motor_key: str, concept: str = "wheel", w: Optional[Dict] = None, starts: int = 6, iters: int = 400,
             seed: int = 0) -> Dict:
    w = w or {}
    motor = CT.MOTORS[motor_key]
    rng = np.random.default_rng(seed)
    best = None
    for s in range(starts):
        x0 = np.array([math.log(rng.uniform(1.0, 2.5)), math.log(rng.uniform(1.5, 30.0)), rng.uniform(0.3, 0.8),
                       math.log(rng.uniform(0.5, 1.0))])
        x = torch.tensor(x0, requires_grad=True, dtype=torch.float64)
        opt = torch.optim.Adam([x], lr=0.03)
        for _ in range(iters):
            opt.zero_grad()
            J, _ = objective(x, motor, concept, w)
            J.backward()
            opt.step()
        J, t = objective(x, motor, concept, w)
        if best is None or float(J.detach()) < best[0]:
            best = (float(J.detach()), x.detach().clone(), {k: float(torch.as_tensor(v, dtype=torch.float64).detach()) for k, v in t.items()})
    return {"motor": motor_key, "concept": concept, "J": best[0], "x": best[1].tolist(), "terms": best[2], "weights": w}


def grad_check(motor_key: str = "fh0620B", concept: str = "wheel", h: float = 1e-6) -> Dict:
    """Autograd (adjoint) gradient against central finite differences at a random design (CALC)."""
    motor = CT.MOTORS[motor_key]
    x0 = torch.tensor([math.log(1.4), math.log(5.0), 0.45, math.log(0.8)], dtype=torch.float64)
    x = x0.clone().requires_grad_(True)
    J, _ = objective(x, motor, concept, {})
    J.backward()
    g_ad = x.grad.detach().numpy()
    g_fd = np.zeros(4)
    for i in range(4):
        e = torch.zeros(4, dtype=torch.float64); e[i] = h
        Jp, _ = objective(x0 + e, motor, concept, {})
        Jm, _ = objective(x0 - e, motor, concept, {})
        g_fd[i] = float(Jp - Jm) / (2 * h)
    rel = float(np.max(np.abs(g_ad - g_fd) / np.maximum(np.abs(g_fd), 1e-9)))
    return {"grad_autograd": g_ad.tolist(), "grad_fd": g_fd.tolist(), "max_rel_err": rel}


def snap(res: Dict) -> Dict:
    """Snap the continuous ratio to the catalogue (Faulhaber 06/1: 4, 16, 64; maxon GP 6 A: 3.9, 15, 57), re-optimise
    r_e, P (and r_r) at the fixed ratio and report the catalogue build (CALC)."""
    motor = CT.MOTORS[res["motor"]]
    concept = res["concept"]
    G_cont = math.exp(res["x"][1])
    out = []
    opts = [("bevel 1:1 only", 1.0, 0.9), ("bevel 2:1 only", 2.0, 0.9)]
    opts += [(g.key + " + bevel 1:1", g.ratio, g.eta * 0.9) for g in CT.GEARHEADS.values()
             if g.d_mm <= motor.d_mm + 0.5 and not g.key.startswith("SPG04")]
    for name, ratio, eta_cat in opts:
        x = torch.tensor(res["x"], requires_grad=True, dtype=torch.float64)
        opt = torch.optim.Adam([x], lr=0.02)
        for _ in range(300):
            opt.zero_grad()
            xx = torch.cat([x[:1], torch.tensor([math.log(ratio)], dtype=torch.float64), x[2:]])
            J, _ = objective(xx, motor, concept, res["weights"])
            J.backward()
            opt.step()
        xx = torch.cat([x[:1], torch.tensor([math.log(ratio)], dtype=torch.float64), x[2:]]).detach()
        J, t = objective(xx, motor, concept, res["weights"])
        out.append({"gear": name, "ratio": ratio, "eta_catalogue_with_bevel": eta_cat, "J": float(J),
                    "terms": {k: float(v) for k, v in t.items()}})
    out.sort(key=lambda r: r["J"])
    return {"G_continuous": G_cont, "options": out, "chosen": out[0],
            "note": "ratio = gearhead x a 1:1 bevel at the heel (a 2:1 bevel doubles it); CALC"}


def pareto(concept: str = "wheel", motor_key: str = "fh0620B") -> List[Dict]:
    """Trade-off of usable force against heel size: sweep the heel-size weight (CALC)."""
    rows = []
    for wdR in (0.0, 0.05, 0.15, 0.4, 1.0, 3.0):
        r = optimise(motor_key, concept, {"dR": wdR}, starts=3, iters=300)
        t = r["terms"]
        rows.append({"w_dR": wdR, "r_e_mm": t["r_e_mm"], "R_d_mm": t["R_d_mm"], "P_N": t["P_N"], "G": t["G"],
                     "F_use_mean_N": t["F_use_mean_N"], "F_use_p10_N": t["F_use_p10_N"], "share_full": t["share_full"],
                     "m_r_g": t["m_r_g"], "P_cu_W": t["P_cu_W"], "F_rr_N": t["F_rr_N"]})
    return rows


def study(quick: bool = False) -> Dict:
    out = {"grad_check": {c: grad_check(concept=c) for c in ("wheel", "ball")}, "runs": {}, "pareto": {}}
    motors = ["fh0620B", "mxDCX6M"] if quick else ["fh0620B", "mxDCX6M", "mxDCX8M"]
    for concept in ("wheel", "ball"):
        best = None
        for m in motors:
            r = optimise(m, concept, starts=3 if quick else 6, iters=250 if quick else 400)
            r["snapped"] = snap(r)
            # layout feasibility (CALC, drive/layout.fit_checks): a motor beside the nose's rear arm must be <= 6 mm
            # in diameter (arm at its stop 4.2 mm from the axis, shell bore 10 mm)
            r["fits_layout"] = bool(CT.MOTORS[m].d_mm <= 6.0 + 1e-9)
            out["runs"][f"{concept}/{m}"] = r
            if not r["fits_layout"]:
                continue
            if best is None or r["snapped"]["chosen"]["J"] < best["snapped"]["chosen"]["J"]:
                best = r
        out[f"best_{concept}"] = best
        if not quick:
            out["pareto"][concept] = pareto(concept, best["motor"])
    return out
