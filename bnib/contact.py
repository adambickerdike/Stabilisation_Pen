r"""Vector contact statics at the ball, with a friction map (CALC; inputs labelled in labels.py).

Frames (as sim2/params.py and H1): page frame x, y in the paper, n = z out of the paper; the pen axis a points from the
ball to the back of the pen at altitude theta: a = cos(theta) h + sin(theta) n (h: the pen's azimuth in the paper);
t1 = sin(theta) h - cos(theta) n (in the tilt plane, toward the paper side); t2 = n x h (lateral).  The nib's two axes
u1, u2 are fixed in the pen body; with the pen rolled by phi about a, u1 = cos(phi) t1 + sin(phi) t2,
u2 = -sin(phi) t1 + cos(phi) t2 (phi = 0: u1 in the tilt plane).

The refill slides freely along a (friction hysteresis h_sl) and is pushed toward the paper by the ink spring F_s.  The
paper pushes the ball with F = N n + f, f the friction (kinetic -mu N v_hat while sliding, v_hat in the paper).  The
refill's axial balance fixes N (the review's point: do not convert axial force into normal force by a constant
multiplier):
    F . a = F_s - h_sl sign(slide rate)      ->   N (sin(theta) - mu v_h cos(theta)) = F_s'     (v_h = v_hat . h)
The load on the nib (tip-referred, per nib axis, in the direction that the nib must push) is  Q_i = -F . u_i ; with no
friction Q_1 = -N (n . t1) = N cos(theta) = F_s cot(theta) for phi = 0 (the static side load).
With friction the tilt-plane load is F_s cot(theta -+ phi_f) (tan phi_f = mu) for sliding toward -+h.
The nib-to-ink Jacobian: a nib displacement dq along u (perpendicular to a) moves the ink by (I - n n^T)(dq + ds a) with
the refill sliding into the pen by ds = -(n . dq) / sin(theta) (= cot(theta) dq_1 at roll 0) to keep the ball on the
paper:  dx_ink = dq_1 / sin(theta) h + dq_2 t2 for phi = 0.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np

from .labels import CONTACT, FRICTION, val

D2R = math.pi / 180.0


# ------------------------------------------------------------------------------------------------ frames
def frame(theta: float, phi: float = 0.0, psi: float = 0.0) -> Dict[str, np.ndarray]:
    """Page-frame unit vectors for pen altitude theta (rad), roll phi (rad) and azimuth psi (rad)."""
    h = np.array([math.cos(psi), math.sin(psi), 0.0])
    n = np.array([0.0, 0.0, 1.0])
    a = math.cos(theta) * h + math.sin(theta) * n
    t1 = math.sin(theta) * h - math.cos(theta) * n
    t2 = np.cross(n, h)
    u1 = math.cos(phi) * t1 + math.sin(phi) * t2
    u2 = -math.sin(phi) * t1 + math.cos(phi) * t2
    return {"a": a, "t1": t1, "t2": t2, "n": n, "h": h, "u1": u1, "u2": u2}


# ------------------------------------------------------------------------------------------------ friction map
def mu_kinetic(ink: str = "oil_common", v: float = 15e-3, N: float = 1.2, paper: float = 1.0) -> float:
    """Kinetic friction coefficient of the ball on paper (friction map).  Base value by ink type (LIT CON-13, 1.0-1.5 N,
    15 mm/s); load dependence (N / 1.2 N)^0.10 and speed dependence 1 + 0.04 ln(v / 15 mm/s) are ASSUMPTION shapes
    (CON-14 reports mu rising with load on a tablet film); paper factor 0.8-1.3 ASSUMPTION (six papers, gate G1)."""
    mu0 = val(FRICTION["mu_ink"][ink])
    le = val(FRICTION["load_exp"])
    sl = val(FRICTION["speed_log"])
    fN = (max(N, 1e-3) / 1.2) ** le
    fv = 1.0 + sl * math.log(max(v, 1e-4) / 15e-3)
    return mu0 * fN * max(fv, 0.5) * paper


def mu_map_table(inks=("oil_common", "oil_low_friction", "gel", "water_based"), loads=(0.05, 0.1, 0.2, 0.4, 1.2),
                 speeds=(2e-3, 15e-3, 30e-3, 100e-3)) -> Dict:
    rows = []
    for ink in inks:
        for N in loads:
            for v in speeds:
                rows.append({"ink": ink, "N": N, "v_mm_s": v * 1e3, "mu": mu_kinetic(ink, v, N)})
    return {"rows": rows, "label": "friction map: LIT CON-13 base values x ASSUMPTION load and speed shapes (FRICTION in labels.py)"}


# ------------------------------------------------------------------------------------------------ contact force
def contact_force(theta: float, F_s: float, mu: float = 0.0, v_hat: Optional[np.ndarray] = None, psi: float = 0.0,
                  h_sl: float = 0.0, slide_sign: float = 0.0) -> Dict:
    """Normal force, friction and total contact force on the ball (page frame).  v_hat: the ball's sliding direction
    in the paper (unit 3-vector with zero n component) or None (not sliding: friction set to zero, the static case).
    slide_sign: +1 refill sliding back into the pen, -1 forward (slide friction opposes it)."""
    fr = frame(theta, 0.0, psi)
    a, n, h = fr["a"], fr["n"], fr["h"]
    F_eff = F_s - h_sl * slide_sign
    if v_hat is None or mu == 0.0:
        N = F_eff / math.sin(theta)
        f = np.zeros(3)
    else:
        v = np.asarray(v_hat, float)
        v = v - (v @ n) * n
        v = v / max(np.linalg.norm(v), 1e-12)
        den = math.sin(theta) - mu * (v @ a)
        if den <= 0.0:
            raise ValueError("self-locking contact: sin(theta) <= mu (v . a)")
        N = F_eff / den
        f = -mu * N * v
    F = N * n + f
    return {"N": N, "f": f, "F": F, "F_axial": float(F @ a), "frame": fr}


def nib_load(theta: float, phi: float, F_s: float, mu: float = 0.0, v_hat: Optional[np.ndarray] = None,
             h_sl: float = 0.0, slide_sign: float = 0.0) -> np.ndarray:
    """Tip-referred load the nib must push against on its axes (u1, u2): Q_i = -F . u_i (N)."""
    c = contact_force(theta, F_s, mu, v_hat, 0.0, h_sl, slide_sign)
    fr = frame(theta, phi)
    F = c["F"]
    return np.array([-(F @ fr["u1"]), -(F @ fr["u2"])])


def static_side_load(theta: float, F_c: float) -> float:
    """The review's frictionless static term F_c cot(theta) (N, in the tilt plane, away from the paper)."""
    return F_c / math.tan(theta)


def side_load_friction_band(theta: float, F_c: float, mu: float) -> Tuple[float, float]:
    """Tilt-plane side load while sliding along -h / +h: F_c cot(theta + phi_f) and F_c cot(theta - phi_f)."""
    pf = math.atan(mu)
    return F_c / math.tan(theta + pf), F_c / math.tan(theta - pf)


def writing_load_stats(theta: float, phi: float, F_s: float, ink: str = "oil_common", paper: float = 1.0,
                       n_dir: int = 72, v: float = 30e-3, h_sl: float = 0.0) -> Dict:
    """Nib load over writing directions (uniform over the circle, sliding at speed v) and the static (not sliding)
    value: mean (static part) and rms of the fluctuation about it per axis (N).  Vectorised form of nib_load:
        N = F_s / (sin th - mu cos(ang) cos th),  Q_i = N (-(n . u_i) + mu (v . u_i))
    with n . u1 = -cos th cos phi, n . u2 = cos th sin phi, v . u1 = cos phi cos(ang) sin th + sin phi sin(ang),
    v . u2 = -sin phi cos(ang) sin th + cos phi sin(ang)."""
    st, ct = math.sin(theta), math.cos(theta)
    sp, cp = math.sin(phi), math.cos(phi)
    mu = mu_kinetic(ink, v, F_s / st, paper)
    ang = 2 * np.pi * np.arange(n_dir) / n_dir
    ca, sa = np.cos(ang), np.sin(ang)
    N = F_s / (st - mu * ca * ct)
    nu1, nu2 = -ct * cp, ct * sp
    vu1 = cp * ca * st + sp * sa
    vu2 = -sp * ca * st + cp * sa
    Q = np.column_stack([N * (-nu1 + mu * vu1), N * (-nu2 + mu * vu2)])
    N0 = F_s / st
    Q0 = np.array([-N0 * nu1, -N0 * nu2])
    mean = Q.mean(axis=0)
    dev = Q - mean
    return {"mu": mu, "static": Q0, "mean_sliding": mean, "rms_about_mean": np.sqrt((dev ** 2).mean(axis=0)),
            "rms_total": np.sqrt((Q ** 2).mean(axis=0)), "max_abs": np.abs(Q).max(axis=0)}


# ------------------------------------------------------------------------------------------------ Jacobians
def contact_jacobian(theta: float, phi: float = 0.0) -> Dict:
    """Ink motion in the paper per nib motion (2 x 2, page axes (h, t2) vs nib axes (u1, u2)) and the refill slide
    per nib motion (1 x 2), for a nib that moves the ball perpendicular to the pen axis (CALC, first order)."""
    fr = frame(theta, phi)
    n, a = fr["n"], fr["a"]
    P = np.eye(3) - np.outer(n, n)
    J = np.zeros((2, 2))
    ds = np.zeros(2)
    for j, u in enumerate((fr["u1"], fr["u2"])):
        s_rate = -(n @ u) / (n @ a)           # refill slide INTO the pen (m per m of nib motion): the ball moves by
        dx = P @ (u + s_rate * a)             # dq u + ds a and must stay on the paper, n . (u + ds a) = 0
        J[0, j] = dx @ fr["h"]
        J[1, j] = dx @ fr["t2"]
        ds[j] = s_rate
    return {"J_ink_per_nib": J, "slide_per_nib": ds,
            "label": "CALC: dx_ink = (I - n n^T)(dq + ds a), ds = -(n . dq) / (n . a) (into the pen); page axes (h, t2), "
                     "nib axes (u1, u2)"}


def ball_protrusion(theta: float, R_skid: float, r_b: float = None) -> float:
    """Axial distance of the ball centre ahead of the skid-ring contact plane with both on the paper (H1 p_nom)."""
    r_b = val(CONTACT["r_ball"]) if r_b is None else r_b
    return (R_skid * math.cos(theta) - r_b) / math.sin(theta)


def refill_slide_range(R_skid: float, th_lo: float = 35 * D2R, th_hi: float = 75 * D2R, travel: float = 0.0) -> float:
    """Refill slide needed over the tilt range with the nib centred, plus the nib travel's own slide (cot theta_min
    x travel): the counter-face / ink spring must follow this (CALC)."""
    return ball_protrusion(th_lo, R_skid) - ball_protrusion(th_hi, R_skid) + travel / math.tan(th_lo)


# ------------------------------------------------------------------------------------------------ the review's check
def review_static_power(theta_deg: float, F_c: float = 0.15, L_t: float = 76.48e-3, L_a: float = 11.5e-3,
                        Km: float = 0.656, R: float = 2.47) -> Dict:
    """The review's section-4 statics (frictionless, quasi-static): transverse ball force, pivot torque, coil current and
    static copper heat (CALC; inputs: the C1S design)."""
    th = theta_deg * D2R
    Fp = F_c / math.tan(th)
    tau = L_t * Fp
    F_act = tau / L_a
    K_f = Km * math.sqrt(R)
    return {"theta_deg": theta_deg, "F_perp_N": Fp, "tau_mNm": tau * 1e3, "F_act_N": F_act, "I_A": F_act / K_f,
            "P_W": (F_act / Km) ** 2}
