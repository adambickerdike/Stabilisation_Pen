r"""The matched load model, the duties and the copper loss (CALCULATION; inputs labelled in nibopt/params.py).

Loads on the nib's two axes (u1 in the tilt plane at roll 0, u2 lateral; tip-referred, the force the coils supply):
  gravity   G = m g cos(theta) (-cos phi, sin phi)  (bnib/loads.gravity_load, translation nib), in contact and pen-up;
            removed in contact only if the face is trimmed to cancel it (study B's comp_weight; LOADS weight_trim)
  residual  the face's parallelism error, study K's Monte Carlo (revk/counterface.face_stack re-drawn with its seed):
            isotropic, E|R|^2 for the mean; the 95th percentile aligned with G for the worst case; contact only
  drag      the ball's drag while writing in every direction at 30.5 mm/s with the ink force at the ball N = F_n
            (study K's constant-force float): bnib/contact.writing_load_stats with F_s' = F_n sin(theta): the mean
            offset (mean_sliding - static; the face balances the static part) and the fluctuation per axis, plus
            study B's refill-slide friction h_sl cot(theta) and face friction mu_f F_n + h_f cot(theta); contact only
  guide     the ball guide's rolling drag mu_roll N_total (Coulomb, opposing the carrier's velocity) while it moves
  suspension the wires' nonlinear radial force F_w(|q|) (the pass's beam-column with the anchor stiffness)
  inertia   m q'' (coherent with the spring: prescribed motion, the pass's harmonic correction)
Copper loss for a load F and a force matrix K (N / sqrt(W), 20 degC copper):  P = F^T A F x (R_loop / R_coil)
x (1 + alpha (T_cu - 20)) / (1 + beta (T_mag - 20))^2 with A = K^-T K^-1.  Force-constant conventions:
  'worst07'   A = I / (0.7 sigma_min)^2, sigma_min the smallest singular value over the usable disk (the brief's)
  'centre10'  A = diag(1 / Kx0^2, 1 / Ky0^2) at the centre, upper-bound magnetics (study K's low end)
  'centre07'  the same with 0.7 x (study K's high end)
  'map07'     A(q) of the nearest map sample x 0.7 (the pass's convention in its periodic screen)
Duties:
  A        study B's duty A: 0.2 mm rms per axis at 8 Hz (circular), 70 % contact, mean over 35/50/60/75 deg and
           twelve rolls; 'worst' = 35 deg, worst roll, residual p95
  modes_K  study K's REQ-RVJ-I01 modes (steady 0 / 1 / 2 mm, guide, spelling) at 8 Hz, 2 mm clipped at the reach
  severe   study F's severe-tremor correction at DEC-067's residual: an elliptical (0.4) narrowband process at 6 Hz
           (0.6 Hz line width) whose magnitude spread matches the perfect-knowledge command's p50/p90/p99, scaled to
           the 1.036 mm 2-D rms that leaves the +2-words residual, clipped at the reach, smoothed by a 40 Hz servo
  screen   the pass's worst-case periodic screen (full-radius sinusoids, 4 / 8 / 12 Hz, eight directions) with the
           matched loads at 35 deg (G + R_p95 aligned + the drag offset, the drag's writing-direction fluctuation) in
           continuous contact; 'pass_loads' reproduces the pass's own constant 20 / 40 / 80 mN
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Dict, Optional, Sequence

import numpy as np

from . import params as P
from .params import val

import sys
from . import REPO_ROOT
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

D2R = math.pi / 180.0
G0 = P.G0


# ------------------------------------------------------------------------------------------------ study K's residual
@lru_cache(maxsize=1)
def k_residual() -> Dict:
    """Study K's face-parallelism Monte Carlo, re-drawn with its seed and contributors (revk/counterface.face_stack,
    revk/params.FACE_STACK, read-only) to get the second moment the budgets need (CALC)."""
    from revk import params as KP
    from revk.counterface import face_stack
    ref = face_stack()
    rng = np.random.default_rng(5)
    S = KP.FACE_STACK
    n = 20000
    F_n = KP.val(KP.B1["F_n_N"])
    th = rng.uniform(35.0, 75.0, n) * D2R
    t_err = (rng.normal(0, KP.val(S["imu_tilt_deg"]), n) + rng.normal(0, KP.val(S["imu_to_axis_residual_deg"]), n)
             + rng.normal(0, KP.val(S["hinge_axis_deg"]), n) + rng.normal(0, KP.val(S["face_perp_deg"]), n)
             + rng.uniform(-1, 1, n) * KP.val(S["linkage_backlash_deg"]) + rng.uniform(-1, 1, n) * KP.val(S["deadband_deg"]))
    r_err = (rng.normal(0, KP.val(S["imu_roll_deg"]), n) + rng.normal(0, KP.val(S["roll_ring_axis_deg"]), n)
             + rng.uniform(-1, 1, n) * KP.val(S["linkage_backlash_deg"]) + rng.uniform(-1, 1, n) * KP.val(S["deadband_deg"]))
    lat = r_err * np.cos(th) + rng.normal(0, KP.val(S["imu_to_axis_residual_deg"]), n) + rng.normal(0, KP.val(S["face_perp_deg"]), n)
    delta = np.hypot(t_err, lat) * D2R
    Q = F_n * np.sin(delta)
    out = {"mean_N": float(Q.mean()), "p95_N": float(np.percentile(Q, 95)), "rms_N": float(np.sqrt(np.mean(Q ** 2))),
           "reproduces_K": bool(abs(Q.mean() * 1e3 - ref["Q_mN"]["mean"]) < 1e-9 and abs(np.percentile(Q, 95) * 1e3 -
                                                                                        ref["Q_mN"]["p95"]) < 1e-9),
           "K_reported_mN": ref["Q_mN"], "label": "CALCULATION (study K's Monte Carlo re-drawn, seed 5, n 20,000)"}
    return out


# ------------------------------------------------------------------------------------------------ contact terms
@lru_cache(maxsize=4096)
def contact_terms(theta_deg: float, phi_deg: float, normal: str = "K", n_dir: int = 36):
    """Mean offset m_d (2,) and per-axis variance (2,) of the writing loads with the balance engaged (CALC)."""
    from bnib import contact as C
    th, ph = theta_deg * D2R, phi_deg * D2R
    F_n = val(P.LOADS["F_n_N"])
    F_s = F_n * math.sin(th) if normal == "K" else 0.15
    st = C.writing_load_stats(th, ph, F_s, val(P.LOADS["ink"]), 1.0, n_dir=n_dir, v=val(P.LOADS["writing_speed_m_s"]))
    m_d = np.asarray(st["mean_sliding"]) - np.asarray(st["static"])
    sig_ball = np.asarray(st["rms_about_mean"])
    h_sl = val(P.LOADS["slide_friction_N"])
    sig_sl = h_sl / math.tan(th) * np.abs(np.array([math.cos(ph), math.sin(ph)]))
    N_r = F_s / math.sin(th)
    sig_face = np.full(2, val(P.LOADS["face_mu"]) * N_r + val(P.LOADS["face_guide_N"]) / math.tan(th))
    var = sig_ball ** 2 + sig_sl ** 2 + sig_face ** 2
    # the largest single-direction drag load (for the peak-force check): max over writing directions of |Q - Q_static|
    return m_d, var, float(np.sqrt(np.sum(var))), st["mu"]


def peak_drag(theta_deg: float, normal: str = "K") -> float:
    from bnib import contact as C
    th = theta_deg * D2R
    F_n = val(P.LOADS["F_n_N"])
    F_s = F_n * math.sin(th) if normal == "K" else 0.15
    mu = C.mu_kinetic(val(P.LOADS["ink"]), val(P.LOADS["writing_speed_m_s"]), F_s / math.sin(th), 1.0)
    ang = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    N = F_s / (math.sin(th) - mu * np.cos(ang) * math.cos(th))
    q1 = (N - F_s / math.sin(th)) * math.cos(th) + mu * N * np.cos(ang) * math.sin(th)
    q2 = mu * N * np.sin(ang)
    h = val(P.LOADS["slide_friction_N"]) / math.tan(th)
    return float(np.max(np.hypot(np.abs(q1) + h, q2)))


def gravity(m_kg: float, theta_deg: float, phi_deg: float) -> np.ndarray:
    th, ph = theta_deg * D2R, phi_deg * D2R
    return m_kg * G0 * math.cos(th) * np.array([-math.cos(ph), math.sin(ph)])


# ------------------------------------------------------------------------------------------------ the severe process
@lru_cache(maxsize=1)
def severe_command(seconds: float = 60.0, fs: float = 1000.0, seed: int = 11) -> Dict:
    """Unclipped 2-D command (m) of the severe-tremor correction: elliptical narrowband Gaussian (minor/major 0.4,
    6 Hz, 0.6 Hz SD), 2-D rms 1.036 mm (study F's a_r2 at 6 mm reach) (CALC fitted to SIM statistics)."""
    d = val(P.DUTIES["severe"])
    n = int(seconds * fs)
    t = np.arange(n) / fs
    r = np.random.default_rng(seed)
    K = 300
    f = np.abs(r.normal(d["f_Hz"], d["bw_Hz"], K))
    p1 = r.uniform(0, 2 * np.pi, K)
    p2 = r.uniform(0, 2 * np.pi, K)
    x = np.cos(2 * np.pi * np.outer(t, f) + p1).sum(axis=1) / math.sqrt(K / 2)
    y = 0.4 * np.cos(2 * np.pi * np.outer(t, f) + p2).sum(axis=1) / math.sqrt(K / 2)
    m = np.hypot(x, y)
    s = d["q_rms_2d_mm_by_reach"]["6.0"] * 1e-3 / math.sqrt(np.mean(m ** 2))
    x *= s
    y *= s
    mm = np.hypot(x, y)
    orc = mm * (1.599 / 1.036)
    stats = {"p50_mm": float(np.median(orc) * 1e3), "p90_mm": float(np.percentile(orc, 90) * 1e3),
             "p99_mm": float(np.percentile(orc, 99) * 1e3), "rms_mm": float(np.sqrt(np.mean(orc ** 2)) * 1e3),
             "F_oracle_mm": {"p50": 1.212, "p90": 2.498, "p99": 3.813, "rms": 1.599}}
    return {"x": x, "y": y, "fs": fs, "stats_as_oracle": stats}


def _lowpass2(x: np.ndarray, fs: float, fc: float) -> np.ndarray:
    """Critically damped second-order low-pass, forward-backward (the servo's smoothing of the clipped command)."""
    from scipy.signal import bilinear, filtfilt
    w = 2 * math.pi * fc
    b, a = bilinear([w * w], [1, 2 * w, w * w], fs)
    return filtfilt(b, a, x)


@lru_cache(maxsize=256)
def severe_motion(reach_mm: float, decim: int = 2) -> Dict:
    """Clipped, servo-smoothed nib motion for a reach (q, v, a in m, m/s, m/s^2) and its statistics (CALC)."""
    c = severe_command()
    x, y, fs = c["x"], c["y"], c["fs"]
    R = reach_mm * 1e-3
    m = np.hypot(x, y)
    k = np.minimum(1.0, R / np.maximum(m, 1e-15))
    qx, qy = _lowpass2(x * k, fs, 40.0), _lowpass2(y * k, fs, 40.0)
    mq = np.hypot(qx, qy)
    kk = np.minimum(1.0, R / np.maximum(mq, 1e-15))
    qx, qy = qx * kk, qy * kk
    vx, vy = np.gradient(qx, 1 / fs), np.gradient(qy, 1 / fs)
    ax, ay = np.gradient(vx, 1 / fs), np.gradient(vy, 1 / fs)
    sl = slice(int(fs), None, decim)
    q = np.column_stack([qx[sl], qy[sl]])
    v = np.column_stack([vx[sl], vy[sl]])
    a = np.column_stack([ax[sl], ay[sl]])
    return {"q": q, "v": v, "a": a, "q_rms_2d_mm": float(np.sqrt(np.mean(np.sum(q ** 2, 1))) * 1e3),
            "at_limit": float(np.mean(m > R)), "reach_mm": reach_mm}


def f_reach_interp(key: str, reach_mm: float) -> float:
    d = val(P.F_REACH)
    return float(np.interp(reach_mm, d["reach_mm"], d[key]))


# ------------------------------------------------------------------------------------------------ design context
@dataclass
class Ctx:
    """Everything the duty model needs about one design (built by evaluate.context)."""
    m: float                                   # moving mass, kg
    fw: Callable                               # |q| (m) -> radial wire force (N)
    fd: Callable                               # theta_deg -> guide Coulomb drag (N) while moving; pen up uses 'penup'
    K0: np.ndarray                             # 2 x 2 centre force matrix, N / sqrt(W), upper bound
    sv_min: float                              # smallest singular value over the usable disk, upper bound
    map_pos: np.ndarray                        # map positions (N x 2, m)
    map_K: np.ndarray                          # map matrices (N x 2 x 2), upper bound
    reach_m: float
    lead_factor: float                         # R_loop / R_coil
    weight_trim: bool = False
    normal: str = "K"
    temp_factor: float = 1.0                   # (1 + alpha dT_cu) / (1 + beta dT_mag)^2, set by the thermal loop
    fd_penup: float = 0.0
    residual_mode: str = "K"                   # 'K': study K's Monte Carlo; 'B': study B's duty model (deterministic
                                               # +1 sigma IMU errors, weight trimmed, F_s along the pen)
    rolls: Optional[tuple] = None              # None: twelve rolls; (0.0,): study B's fast mode
    A_fixed: Optional[np.ndarray] = None       # a fixed A (e.g. study K's per-axis Km_tip) for the waterfall

    def A(self, conv: str) -> np.ndarray:
        if self.A_fixed is not None:
            return self.A_fixed
        der = val(P.KM["derating"])
        if conv == "worst07":
            return np.eye(2) / (der * self.sv_min) ** 2
        if conv in ("centre10", "centre07"):
            s = 1.0 if conv == "centre10" else der
            Ki = np.linalg.inv(self.K0 * s)
            return Ki.T @ Ki
        raise ValueError(conv)

    def A_at(self, q: np.ndarray, scale: float = None) -> np.ndarray:
        scale = val(P.KM["derating"]) if scale is None else scale
        idx = np.argmin(np.linalg.norm(self.map_pos[:, None, :] - q[None, :, :], axis=2), axis=0)
        Ki = np.linalg.inv(self.map_K[idx] * scale)
        return np.einsum("nji,njk->nik", Ki, Ki)


def _theta_list(worst: bool):
    return [val(P.LOADS["tilt_worst_deg"])] if worst else list(val(P.LOADS["tilts_mean_deg"]))


def _rolls(ctx=None):
    if ctx is not None and ctx.rolls is not None:
        return list(ctx.rolls)
    n = val(P.LOADS["rolls_n"])
    return [360.0 * k / n for k in range(n)]


@lru_cache(maxsize=4096)
def contact_B(m_kg: float, theta_deg: float, phi_deg: float):
    """Study B's own contact load for B1 (bnib/loads.loads_at with the CounterFace balance, read-only): the static hold
    vector (friction offset + the +1 sigma IMU-error residual, the weight trimmed) and the per-axis variance (CALC)."""
    from bnib import balance as BL
    from bnib import loads as LD
    nib = LD.NibModel(name="B1", kind="translation", Km_tip=0.40007, m_eff_tip=m_kg, m_nib=m_kg, k_tip=0.0, R_coil=2.5)
    L = LD.loads_at(nib, theta_deg * D2R, phi_deg * D2R, 0.15, LD.Duty(q_rms=1e-7), BL.CounterFace())
    hold = np.asarray(L["Q_mean_sliding"]) + np.asarray(L["balance_contact"]) + np.asarray(L["gravity"])
    return hold, np.asarray(L["sigma_friction"]) ** 2


def motion_moments(ctx: Ctx, kind: str, q_rms_axis_mm: float = 0.0, f_Hz: float = 8.0, theta_deg: float = 35.0) -> Dict:
    """E[M M^T] (2 x 2) of the motion loads, split into inertia + wires ('dyn') and the guide's drag ('guide') (CALC).
    kind: 'hold' (no motion), 'circle' (radius sqrt 2 q_rms, clipped at the reach), 'severe' (study F's process)."""
    fd = ctx.fd(theta_deg)
    Z = np.zeros((2, 2))
    if kind == "hold" or (kind == "circle" and q_rms_axis_mm <= 0):
        return {"dyn": Z, "guide": Z}
    if kind == "circle":
        a = min(math.sqrt(2.0) * q_rms_axis_mm * 1e-3, ctx.reach_m)
        w = 2 * math.pi * f_Hz
        F_r = float(ctx.fw(a)) - ctx.m * w * w * a
        return {"dyn": 0.5 * F_r ** 2 * np.eye(2), "guide": 0.5 * fd ** 2 * np.eye(2), "radius_mm": a * 1e3}
    if kind == "severe":
        mo = severe_motion(round(ctx.reach_m * 1e3, 4))
        q, v, acc = mo["q"], mo["v"], mo["a"]
        r = np.linalg.norm(q, axis=1)
        qh = q / np.maximum(r, 1e-15)[:, None]
        sp = np.linalg.norm(v, axis=1)
        vh = v / np.maximum(sp, 1e-12)[:, None]
        Md = ctx.m * acc + ctx.fw(r)[:, None] * qh
        Mg = fd * vh * (sp > 1e-5)[:, None]
        n = len(q)
        return {"dyn": Md.T @ Md / n, "guide": Mg.T @ Mg / n, "cross": (Md.T @ Mg + Mg.T @ Md) / n,
                "q_rms_2d_mm": mo["q_rms_2d_mm"], "at_limit": mo["at_limit"]}
    raise ValueError(kind)


ITEMS = ("gravity", "residual", "writing_drag", "guide_drag", "inertia_and_wires", "cross_terms")


def typical(ctx: Ctx, conv: str, kind: str = "circle", q_rms_axis_mm: float = 0.2, f_Hz: float = 8.0,
            thetas: Optional[Sequence[float]] = None) -> Dict:
    """Mean copper loss over 35/50/60/75 deg and twelve rolls (residual as its rms, isotropic), and the worst case
    (35 deg, worst roll, residual p95 aligned with gravity); each load item's own quadratic term and the cross terms,
    so that the items add up to the total (CALC)."""
    A = ctx.A(conv)
    c = val(P.LOADS["contact_share"])
    kr = k_residual()
    fac = ctx.lead_factor * ctx.temp_factor
    out = {"conv": conv}
    for tag in ("mean", "worst"):
        worst = tag == "worst"
        rows = []
        for th in (_theta_list(worst) if thetas is None else list(thetas)):
            mm = motion_moments(ctx, kind, q_rms_axis_mm, f_Hz, th)
            E_dyn = float(np.trace(A @ mm["dyn"]))
            E_gd = float(np.trace(A @ mm["guide"]))
            E_x = float(np.trace(A @ mm.get("cross", np.zeros((2, 2)))))
            for ph in _rolls(ctx):
                G = gravity(ctx.m, th, ph)
                m_d, var, _, _ = contact_terms(th, ph, ctx.normal)
                Gc = np.zeros(2) if ctx.weight_trim else G
                if ctx.residual_mode == "B":
                    hold, var = contact_B(round(ctx.m, 9), th, ph)
                    m_d = hold
                    Gc = np.zeros(2)
                    R = np.zeros(2)
                    E_R = 0.0
                elif worst:
                    R = kr["p95_N"] * G / max(np.linalg.norm(G), 1e-15)
                    E_R = float(R @ A @ R)
                else:
                    R = np.zeros(2)
                    E_R = kr["rms_N"] ** 2 / 2 * float(np.trace(A))
                S_c = Gc + R + m_d
                if ctx.residual_mode == "B":
                    worst_R = False
                else:
                    worst_R = worst
                E_drag = float(np.sum(np.diag(A) * var)) + float(m_d @ A @ m_d)
                tot_c = float(S_c @ A @ S_c) + (0.0 if worst_R else E_R) + float(np.sum(np.diag(A) * var))
                tot = c * tot_c + (1 - c) * float(G @ A @ G) + E_dyn + E_gd + E_x
                it = {"gravity": c * float(Gc @ A @ Gc) + (1 - c) * float(G @ A @ G), "residual": c * E_R,
                      "writing_drag": c * E_drag, "guide_drag": E_gd, "inertia_and_wires": E_dyn}
                it["cross_terms"] = tot - sum(it.values())
                rows.append((tot, it))
        if worst:
            tot, it = max(rows, key=lambda r: r[0])
            out["worst"] = tot * fac
            out["worst_items_W"] = {k: v * fac for k, v in it.items()}
        else:
            out["mean"] = float(np.mean([r[0] for r in rows])) * fac
            out["mean_items_W"] = {k: float(np.mean([r[1][k] for r in rows])) * fac for k in ITEMS}
    return out


def screen(ctx: Ctx, conv: str, loads: str = "matched", residual_N: float = 0.02, hot_factor: Optional[float] = None,
           mass_kg: Optional[float] = None, fw: Optional[Callable] = None, n_phase: int = 256,
           drag_var: bool = True) -> Dict:
    """The pass's periodic screen: worst over 4/8/12 Hz and eight directions of the cycle-mean copper loss (CALC).
    loads 'matched': gravity at 35 deg (+ the p95 residual aligned with it + the drag offset) and the drag's
    fluctuation in continuous contact, the guide's Coulomb drag and the wires, worst roll; 'pass': a constant
    residual along the motion, no guide drag (the pass's own model; hot_factor and mass_kg reproduce it)."""
    th = val(P.LOADS["tilt_worst_deg"])
    kr = k_residual()
    fw = ctx.fw if fw is None else fw
    m = ctx.m if mass_kg is None else mass_kg
    phase = np.linspace(0, 2 * np.pi, n_phase, endpoint=False)
    fac = ctx.lead_factor * (ctx.temp_factor if hot_factor is None else hot_factor)
    rows = []
    for f in val(P.DUTIES["screen"])["f_Hz"]:
        w = 2 * math.pi * f
        for k in range(val(P.DUTIES["screen"])["n_dir"]):
            a = k * math.pi / 4
            d = np.array([math.cos(a), math.sin(a)])
            qs = ctx.reach_m * np.sin(phase)
            q = qs[:, None] * d
            vs = ctx.reach_m * w * np.cos(phase)
            M = (m * (-w * w) * qs + np.sign(qs) * fw(np.abs(qs)))[:, None] * d
            A_map = ctx.A_at(q) if conv == "map07" else None
            A_c = None if conv == "map07" else ctx.A(conv)
            if loads == "matched":
                M = M + ctx.fd(th) * np.sign(vs)[:, None] * d
                cands = []
                for ph in _rolls(ctx):
                    G = gravity(ctx.m, th, ph)
                    m_d, var, _, _ = contact_terms(th, ph, ctx.normal)
                    if not drag_var:
                        var = np.zeros(2)
                    gh = G / np.linalg.norm(G)
                    S = (np.zeros(2) if ctx.weight_trim else G) + kr["p95_N"] * gh + m_d
                    F = S[None, :] + M
                    if A_map is not None:
                        E = float(np.mean(np.einsum("ni,nij,nj->n", F, A_map, F))
                                  + np.mean(A_map[:, 0, 0] * var[0] + A_map[:, 1, 1] * var[1]))
                    else:
                        E = float(np.mean(np.einsum("ni,ij,nj->n", F, A_c, F)) + A_c[0, 0] * var[0] + A_c[1, 1] * var[1])
                    cands.append((E, ph))
                E, ph = max(cands)
            else:
                F = M + residual_N * d[None, :]
                if A_map is not None:
                    E = float(np.mean(np.einsum("ni,nij,nj->n", F, A_map, F)))
                else:
                    E = float(np.mean(np.einsum("ni,ij,nj->n", F, A_c, F)))
                ph = None
            rows.append({"f_Hz": f, "dir_deg": math.degrees(a), "roll_deg": ph, "P_W": E * fac})
    worst = max(rows, key=lambda r: r["P_W"])
    return {"P_worst_W": worst["P_W"], "at": worst, "loads": loads, "conv": conv, "rows": rows}


def peak_force(ctx: Ctx) -> Dict:
    """The largest force the coils must give (N): 35 deg gravity + residual p95 + the worst-direction writing drag,
    aligned, + the wires at the stop + inertia of a full-radius 12 Hz stroke + the guide drag (study B's travel-under-
    load rule, with the matched loads) (CALC)."""
    th = val(P.LOADS["tilt_worst_deg"])
    kr = k_residual()
    G = 0.0 if ctx.weight_trim else ctx.m * G0 * math.cos(th * D2R)
    stat = G + kr["p95_N"] + peak_drag(th, ctx.normal)
    w = 2 * math.pi * 12.0
    dyn = float(ctx.fw(ctx.reach_m + 0.2e-3)) + ctx.m * w * w * ctx.reach_m + ctx.fd(th)
    return {"static_N": stat, "dynamic_N": dyn, "total_N": stat + dyn}
