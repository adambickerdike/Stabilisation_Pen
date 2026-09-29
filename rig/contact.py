"""G1 contact analysis (EXP-T01): axial refill force and paper-normal force kept apart,
the friction vector, and the static side load the nib must hold.

Frames and signs follow stabpen/contact.py and docs/physics.md P-5...P-7:
  z up (paper normal), h = page-plane unit vector from the ball toward the cap's
  projection ("toward the hand"), t2 = z x h, pen axis a = cos(theta) h + sin(theta) z.
  beta = direction of the ball's sliding velocity relative to h (0: pull, pi: push).
  Paper reaction on the ball R = N z + f; kinetic friction f = -mu N v_hat.

Measured on rig R9 (docs/measurement_rig.md):
  * F_c, the axial force the cartridge spring (voice coil or dead weight) applies to the refill,
    from an in-line load cell, corrected for the flexure guide;
  * the force the ball applies to the paper, F_p (page frame), from a 3-axis plate under the
    paper: N = -F_p,z and f = -F_p,xy. N is measured in the page frame, so the goniometer
    angle error does not enter it (it enters only the projections below).

For a refill free to slide along its axis, quasi-static equilibrium gives R.a = F_c
(P-7: F_c = N (sin th - mu cos b cos th)); the lateral guide (the nib actuator) must hold
R_perp = R - (R.a) a (P-6). The closure residual F_c - R.a checks the rig itself.

Nothing here converts axial force into normal force with a constant factor (review section 4;
Schomaker and Plamondon 1990, LIT CON-01, CON-101).
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
from scipy import signal as sps


def basis(phi_h: float):
    h = np.array([np.cos(phi_h), np.sin(phi_h)])
    t2 = np.array([-h[1], h[0]])
    return h, t2


def contact_components(Fp: np.ndarray, theta: float, phi_h: float) -> Dict[str, np.ndarray]:
    """Plate forces (n x 3, force applied ON the platen, page frame, N) to contact components."""
    Fp = np.atleast_2d(np.asarray(Fp, float))
    N = -Fp[:, 2]
    f = -Fp[:, :2]                       # friction on the ball, page plane
    h, t2 = basis(phi_h)
    f_h = f @ h
    f_t2 = f @ t2
    st, ct = np.sin(theta), np.cos(theta)
    R_a = N * st + f_h * ct
    R_t1 = -N * ct + f_h * st
    R_t2 = f_t2
    return {"N": N, "f_x": f[:, 0], "f_y": f[:, 1], "f_h": f_h, "f_t2": f_t2, "R_a": R_a, "R_t1": R_t1,
            "R_t2": R_t2, "R_perp": np.hypot(R_t1, R_t2)}


def predicted_ratio_perp_to_axial(theta, mu, beta):
    """P-6 / P-7: R_perp / F_c for a refill pressed by an axial force F_c (frictionless: cot theta)."""
    st, ct = np.sin(theta), np.cos(theta)
    num = np.sqrt((ct + mu * np.cos(beta) * st) ** 2 + (mu * np.sin(beta)) ** 2)
    den = st - mu * np.cos(beta) * ct
    return num / den


def _velocity(t, xy, cutoff_hz=20.0):
    fs = 1.0 / np.median(np.diff(t))
    if len(t) > 30 and cutoff_hz < 0.45 * fs:
        sos = sps.butter(2, cutoff_hz, fs=fs, output="sos")
        xy = sps.sosfiltfilt(sos, xy, axis=0)
    return np.gradient(xy, t, axis=0)


def analyse_stroke(t, Fc, Fp, xy, theta, phi_h, trim_mm=2.0, band=(3.0, 15.0)) -> Dict:
    """One constant-speed stroke. t (s), Fc (N, corrected axial force), Fp (n x 3 N), xy (n x 2 m,
    pen head position from the encoders), theta and phi_h (rad). Returns means over the steady part
    (first and last trim_mm of travel excluded, as EXP-B01) and ripple in `band`."""
    t = np.asarray(t, float)
    xy = np.asarray(xy, float)
    v = _velocity(t, xy)
    speed = np.hypot(v[:, 0], v[:, 1])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    L = s[-1]
    m = (s > trim_mm * 1e-3) & (s < L - trim_mm * 1e-3)
    vmed = np.median(speed[m]) if m.any() else np.nan
    m &= np.abs(speed - vmed) < 0.2 * vmed
    if m.sum() < 10:
        raise ValueError("stroke too short or speed not steady")
    c = contact_components(Fp, theta, phi_h)
    vhat = np.mean(v[m], axis=0)
    vhat = vhat / np.linalg.norm(vhat)
    e_drag = -vhat                                   # direction of pure kinetic drag on the ball
    e_side = np.array([-e_drag[1], e_drag[0]])       # e_drag turned 90 deg counter-clockwise
    h, t2 = basis(phi_h)
    beta = float(np.arctan2(vhat @ t2, vhat @ h))
    f = np.column_stack([c["f_x"], c["f_y"]])
    N = c["N"]
    Nm = float(np.mean(N[m]))
    drag = float(np.mean(f[m] @ e_drag))
    cross = float(np.mean(f[m] @ e_side))
    Fcm = float(np.mean(np.asarray(Fc, float)[m]))
    R_a = float(np.mean(c["R_a"][m]))
    fs = 1.0 / np.median(np.diff(t))
    ripple = float("nan")
    if band[1] < 0.45 * fs and m.sum() > 3 * fs / band[0]:
        sos = sps.butter(4, band, btype="band", fs=fs, output="sos")
        ft = sps.sosfiltfilt(sos, -(f @ vhat))
        ripple = float(np.sqrt(np.mean(ft[m] ** 2)) / max(abs(drag), 1e-12))
    return {"theta_deg": float(np.degrees(theta)), "beta_deg": float(np.degrees(beta) % 360), "v_mm_s": float(vmed * 1e3),
            "N_N": Nm, "Fc_N": Fcm, "mu_drag": drag / Nm, "mu_cross": cross / Nm,
            "mu_eff": float(np.hypot(drag, cross) / Nm), "friction_angle_deg": float(np.degrees(np.arctan2(cross, drag))),
            "R_a_N": R_a, "closure_N": Fcm - R_a, "R_perp_N": float(np.mean(c["R_perp"][m])),
            "R_perp_over_Fc": float(np.mean(c["R_perp"][m]) / Fcm) if Fcm > 0 else float("nan"),
            "cot_theta": float(1 / np.tan(theta)), "ripple_3_15Hz": ripple, "n_steady": int(m.sum())}


def fit_mu_of_N(rows: Sequence[Dict]) -> Dict:
    """mu(N) = mu0 + mu1 N from steady strokes (EXP-B01 analysis step 3)."""
    N = np.array([r["N_N"] for r in rows])
    mu = np.array([r["mu_drag"] for r in rows])
    A = np.column_stack([np.ones_like(N), N])
    c, *_ = np.linalg.lstsq(A, mu, rcond=None)
    res = mu - A @ c
    cov = np.linalg.pinv(A.T @ A) * np.sum(res ** 2) / max(len(N) - 2, 1)
    return {"mu0": float(c[0]), "mu1_per_N": float(c[1]), "se": np.sqrt(np.diag(cov)).tolist(),
            "resid_rms": float(np.sqrt(np.mean(res ** 2))), "n": int(len(N))}


def p6_check(rows: Sequence[Dict], fit_theta_deg=50.0, band=0.15) -> Dict:
    """AC-B01-03 analogue: fit mu on theta = 50 deg strokes, predict R_perp/F_c elsewhere with P-6/P-7,
    report the fraction of strokes within +-band."""
    fit_rows = [r for r in rows if abs(r["theta_deg"] - fit_theta_deg) < 1.0]
    mu = float(np.mean([r["mu_drag"] for r in fit_rows]))
    ok = []
    for r in rows:
        pred = predicted_ratio_perp_to_axial(np.radians(r["theta_deg"]), mu, np.radians(r["beta_deg"]))
        ok.append(abs(r["R_perp_over_Fc"] / pred - 1) <= band)
    return {"mu_fitted_at_50deg": mu, "fraction_within": float(np.mean(ok)), "band": band, "n": len(rows)}


def side_load_table(rows: Sequence[Dict]) -> List[Dict]:
    """Per tilt: R_perp / F_c over directions and speeds (min, mean, max) against cot(theta).
    This is the static balance range the nib mechanism (study B) must carry per newton of F_c."""
    out = []
    for th in sorted({round(r["theta_deg"], 1) for r in rows}):
        sel = [r for r in rows if abs(r["theta_deg"] - th) < 0.6]
        q = np.array([r["R_perp_over_Fc"] for r in sel])
        out.append({"theta_deg": th, "cot_theta": float(1 / np.tan(np.radians(th))), "ratio_min": float(q.min()),
                    "ratio_mean": float(q.mean()), "ratio_max": float(q.max()), "n": len(sel)})
    return out


def balance_range(side_table: Sequence[Dict], Fc_N: Sequence[float], L_t_mm: float = None) -> List[Dict]:
    """Static side load (mN) and, if the pivot-to-ball length L_t is given, pivot torque (mN m)
    for each tilt and candidate F_c: what a mechanical balancer must supply without current."""
    out = []
    for r in side_table:
        for F in Fc_N:
            d = {"theta_deg": r["theta_deg"], "Fc_N": F, "side_load_min_mN": 1e3 * F * r["ratio_min"],
                 "side_load_max_mN": 1e3 * F * r["ratio_max"]}
            if L_t_mm:
                d["torque_max_mNm"] = d["side_load_max_mN"] * L_t_mm * 1e-3
            out.append(d)
    return out


def apf_npf(Fa: np.ndarray, Fz: np.ndarray, theta: np.ndarray) -> Dict:
    """Recording-pen analysis (EXP-T06): axial pen force (in-pen cell) against paper-normal force
    (plate) in real writing. Reports the correlation, the ratio N/Fa against sin(theta) (Schomaker and
    Plamondon's eq. 1, which assumes the whole pen force is axial), and the residual of that
    constant-factor conversion. Positive Fz means pressing down (N)."""
    Fa = np.asarray(Fa, float)
    N = np.asarray(Fz, float)
    th = np.asarray(theta, float) * np.ones_like(Fa)
    m = (Fa > 0.05) & (N > 0.05)
    r = float(np.corrcoef(Fa[m], N[m])[0, 1]) if m.sum() > 3 else float("nan")
    pred = Fa[m] * np.sin(th[m])
    return {"corr": r, "ratio_N_over_Fa_median": float(np.median(N[m] / Fa[m])),
            "sin_theta_median": float(np.median(np.sin(th[m]))),
            "eq1_residual_rms_N": float(np.sqrt(np.mean((N[m] - pred) ** 2))),
            "eq1_residual_rel": float(np.sqrt(np.mean((N[m] - pred) ** 2)) / np.mean(N[m])), "n": int(m.sum())}
