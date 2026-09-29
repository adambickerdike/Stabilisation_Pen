r"""Actuator models of the candidate nibs (CALC; differentiable where the optimiser needs gradients).

Voice coil, annular axial-gap checkerboard (magnetics.py topology), moving coil or moving magnet:
    B      = Br t_m / (t_m + G) * eta_axial(w, t_m, G, t_c)        (study N's magpylib-fitted surrogate, nose2.designs,
                                                                     G = c0 + 2 t_c + c1 the magnetic gap)
    Km0    = kappa * 2 sqrt(2) * B * w * sqrt(k_fill b t_c / (rho_Cu l_turn)),  b = w - 2 s,  l_turn = 2 (w + 2 c)
             (four legs per layer, two racetracks in series: F / sqrt(n_r) = 4 B w / sqrt(2) per ampere-turn)
    Km_min = Km0 * (1 - nu s / w)                                    (the worst corner of the stroke)
kappa and nu are fitted to the full-coil magpylib force maps (magnetics.km_map) over the design range and cached
(bnib/build/vc_calibration.json); the fit's residual is reported.  Moving mass: the two coil layers + a former (moving
coil) or the magnets + their back plate (moving magnet).
Gimbal voice coil (candidate a): nose2's own differentiable model (act_unit, spherical axial gap), imported read-only.
Piezo stage (candidate h): PICMA-class multilayer benders (MFR AMF-11, AMF-53) in push-pull pairs per axis driving the
refill's front collar through decoupling leaves, the refill pivoting at a rear gimbal (the pencil's Q layout, DEC-019/030):
    tip free stroke x_f = n_p lambda d_free (d_free per plate at full voltage; n_p plates per axis act in parallel)
    tip blocking force F_b = n_p F_block / lambda;  tip stiffness k = F_b / x_f
    loaded usable (symmetric) travel under a static tip load F_s:  x_u = x_f - |F_s| / k
    loaded resonance f = sqrt(k / (m_tip + m_plates_eff lambda^2... )) / 2 pi  (plate effective mass 0.24 m at the tip)
    drive power P = (1 - r) sum C V_pp^2 f (reactive energy per cycle, charge recovery share r ASSUMPTION) + hold/boost
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import torch

from . import BUILD
from .labels import MAT, PIEZO, val

torch.set_num_threads(1)
DT = torch.float64
RHO_CU = val(MAT["Cu_res"])
CU_D = val(MAT["Cu_rho"])
NDFEB = val(MAT["NdFeB_rho"])
FE = val(MAT["Fe_rho"])


def _t(x):
    return x if torch.is_tensor(x) else torch.tensor(float(x), dtype=DT)


def eta_axial(w, t_m, G, t_c):
    from nose2 import designs as ND
    return ND.eta_axial(_t(w), _t(t_m), _t(G), _t(t_c))


CAL_PATH = BUILD / "vc_calibration.json"
_CAL = None


def calibration() -> Dict:
    global _CAL
    if _CAL is None:
        if CAL_PATH.exists():
            _CAL = json.load(open(CAL_PATH))
        else:
            _CAL = {"kappa": 1.0, "nu": 0.8, "fitted": False}
    return _CAL


def vc_axial(w, t_m, t_c, s, e=None, c0: float = 0.30e-3, c1: float = 0.15e-3, k_fill: float = 0.55, Br: float = 1.42,
             moving: str = "coil", refill_r: float = 1.175e-3, cal: Optional[Dict] = None) -> Dict:
    """Moving-coil (or moving-magnet) annular axial-gap checkerboard, differentiable in the continuous variables."""
    cal = cal or calibration()
    w, t_m, t_c, s = _t(w), _t(t_m), _t(t_c), _t(s)
    if e is None:
        e = (refill_r + s + 0.30e-3) / math.sqrt(2.0)       # the refill swings +-s in the hole with 0.3 mm clearance
    e = _t(e)
    c = 0.5 * w + e
    G = c0 + 2 * t_c + c1
    B = Br * t_m / (t_m + G) * eta_axial(w, t_m, G, t_c)
    b = torch.clamp(w - 2 * s, min=0.4e-3)
    l_turn = 2 * (w + 2 * c)
    Km0 = kappa_of(cal, w, t_m, G, s, t_c) * 2.0 * math.sqrt(2.0) * B * w * torch.sqrt(k_fill * b * t_c / (RHO_CU * l_turn))
    Km_min = Km0 * torch.clamp(1 - cal["nu"] * s / w, min=0.05)
    m_cu = 2 * 2 * CU_D * k_fill * b * t_c * l_turn / 2 * 2       # two layers x two racetracks x (bundle area x turn length)
    m_mag = 4 * NDFEB * w * w * t_m
    r_out = math.sqrt(2.0) * (c + 0.5 * w)
    t_bi = torch.clamp(B * w / 1.6 + 0.3e-3, min=0.6e-3)          # 1010 plates carrying one pole's flux (nose2 rule)
    m_plates = 2 * FE * math.pi * (r_out + 0.3e-3) ** 2 * t_bi
    if moving == "coil":
        m_move = m_cu + 0.25e-3                                    # + a thin glass-epoxy/polyimide former (ASSUMPTION)
        m_stat = m_mag + m_plates
    else:
        m_move = m_mag + m_plates / 2
        m_stat = m_cu + m_plates / 2
    length = t_bi * 2 + t_m + G
    return {"Km0": Km0, "Km_min": Km_min, "B": B, "b_leg": b, "c": c, "r_out": r_out, "r_hole": math.sqrt(2.0) * e,
            "m_cu": m_cu, "m_mag": m_mag, "m_move": m_move, "m_stat": m_stat, "length": length, "t_bi": t_bi, "G": G}


def _kappa_features(w, t_m, G, s, t_c):
    """Features of the calibration factor's log-linear fit (dimensionless ratios)."""
    lib = torch if torch.is_tensor(w) else np
    x = lib.log(G / w); y = lib.log(t_m / w); u = s / w; v = lib.log(t_c / G)
    return [1.0 + 0 * x, x, y, u, x * x, y * y, x * y, u * u, v]


def kappa_of(cal: Dict, w, t_m, G, s, t_c):
    c = cal.get("coef")
    if not c:
        return cal["kappa"]
    f = _kappa_features(w, t_m, G, s, t_c)
    lib = torch if torch.is_tensor(w) else np
    return lib.exp(sum(ci * fi for ci, fi in zip(c, f)))


def fit_calibration(n: int = 40, seed: int = 3, quick: bool = False) -> Dict:
    """Fit the calibration factor kappa(w, t_m, G, s, t_c) of vc_axial (log-linear in dimensionless ratios) and the
    worst-corner loss nu to full-coil magpylib maps (magnetics.km_map) at random geometries in the design range (CALC).
    The fit's residual on held-out geometries is reported.  Cached in bnib/build/vc_calibration.json."""
    from . import magnetics as MG
    rng = np.random.default_rng(seed)
    rows = []
    n = 4 if quick else n
    for i in range(n + max(n // 4, 2)):
        w = rng.uniform(2.5e-3, 6.5e-3)
        s = rng.uniform(0.3e-3, 1.4e-3) * min(1.0, w / 4e-3)
        t_m = rng.uniform(1.0e-3, 3.2e-3)
        t_c = rng.uniform(0.2e-3, 0.7e-3)
        e = (1.175e-3 + s + 0.3e-3) / math.sqrt(2)
        g = MG.ChkGeom(w=w, e=e, t_m=t_m, t_x=t_c, t_y=t_c, s=s)
        mp = MG.km_map(g, n=3, nb=3, nt=2, nl=10)
        sur = vc_axial(w, t_m, t_c, s, e, cal={"kappa": 1.0, "nu": 0.0})
        rows.append({"w": w, "s": s, "t_m": t_m, "t_c": t_c, "G": float(sur["G"]),
                     "Km0_magpylib": mp["Km0"], "Km_min_magpylib": mp["Km_min"], "Km0_surrogate_raw": float(sur["Km0"]),
                     "cross_max": mp["cross_max"]})
    fitr, hold = rows[:n], rows[n:]
    X = np.array([[float(f) for f in _kappa_features(r["w"], r["t_m"], r["G"], r["s"], r["t_c"])] for r in fitr])
    yv = np.log([r["Km0_magpylib"] / r["Km0_surrogate_raw"] for r in fitr])
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    cal = {"kappa": float(np.exp(np.mean(yv))), "coef": coef.tolist()}

    def resid(rs):
        return np.array([r["Km0_surrogate_raw"] * kappa_of(cal, r["w"], r["t_m"], r["G"], r["s"], r["t_c"]) / r["Km0_magpylib"] - 1
                         for r in rs])
    rf, rh = resid(fitr), resid(hold)
    loss = np.array([1 - r["Km_min_magpylib"] / r["Km0_magpylib"] for r in rows])
    sw = np.array([r["s"] / r["w"] for r in rows])
    nu = float(np.sum(loss * sw) / np.sum(sw * sw))
    out = {"kappa": cal["kappa"], "coef": cal["coef"], "nu": nu, "fitted": True, "n_fit": len(fitr), "n_holdout": len(hold),
           "rel_rms_fit": float(np.sqrt(np.mean(rf ** 2))), "rel_rms_holdout": float(np.sqrt(np.mean(rh ** 2))),
           "rel_max_holdout": float(np.abs(rh).max()), "nu_resid_rms": float(np.sqrt(np.mean((loss - nu * sw) ** 2))),
           "cross_max_at_s_over_w_le_0.25": float(max([r["cross_max"] for r in rows if r["s"] / r["w"] <= 0.25] or [0.0])),
           "rows": [{k: (v * 1e3 if k in ("w", "s", "t_m", "t_c", "G") else v) for k, v in r.items()} for r in rows],
           "label": "CALC (magpylib full-coil force maps with iron images vs the surrogate; an upper bound for ideal iron)"}
    if not quick:
        CAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(CAL_PATH, "w"), indent=1)
        global _CAL
        _CAL = out
    return out


def coil_electrical(Km: float, R: float = 2.5, V: float = 3.7, I_max: float = 1.5, v_max: float = 0.1) -> Dict:
    """Drive check for a coil wound to R: K_f = Km sqrt(R); headroom at the peak current and speed (CALC)."""
    K_f = Km * math.sqrt(R)
    V_need = I_max * R + K_f * v_max
    return {"K_f_N_A": K_f, "F_peak_N": K_f * I_max, "V_need_at_peak_V": V_need, "headroom_V": V - V_need}


# ------------------------------------------------------------------------------------------------ piezo stage
@dataclass
class PiezoStage:
    plate: str = "PL128"
    n_p: int = 2                  # plates per axis acting in parallel (a push-pull pair)
    lam: float = 1.33             # tip motion per collar motion (rear-pivot lever: z_g / (z_g - z_collar))
    m_tip: float = 1.2e-3         # tip-equivalent moving mass of refill + collar (kg)
    derate: float = 0.8           # -20 % part tolerance (MFR AMF-11) applied to stroke and force (worst case)


def piezo_stage(ps: PiezoStage, F_static_tip: float, q_rms: float = 0.3e-3, f: float = 8.0, worst: bool = True) -> Dict:
    p = PIEZO[ps.plate]
    d_free = val(p["free_um"]) * 1e-6
    Fb = val(p["F_block"])
    tol = ps.derate if worst else 1.0
    x_f = ps.lam * d_free * tol
    F_b = ps.n_p * Fb * tol / ps.lam
    k = F_b / x_f
    x_u = x_f - abs(F_static_tip) / k
    m_plate = val(MAT["PZT_rho"]) * val(p["L"]) * val(p["w"]) * val(p["t"])
    m_eff = ps.m_tip + 0.24 * ps.n_p * m_plate * ps.lam ** -2 * 0 + 0.24 * ps.n_p * m_plate / ps.lam ** 2
    f_res = math.sqrt(k / m_eff) / (2 * math.pi)
    Vr = val(p["V_range"])
    Vpp_full = Vr[1] - Vr[0]
    C = 2 * val(p["C_half"])                                       # both halves of a bimorph plate
    frac = min(math.sqrt(2) * q_rms / x_f, 1.0)                    # share of the full voltage swing the duty uses
    Vpp = frac * Vpp_full
    r = val(PIEZO["recovery"])
    P_axis = (1 - r) * ps.n_p * C * Vpp ** 2 * f
    return {"plate": ps.plate, "tip_free_stroke_mm": x_f * 1e3, "tip_block_N": F_b, "tip_k_N_m": k,
            "loaded_usable_mm": x_u * 1e3, "f_loaded_Hz": f_res, "P_drive_2axes_W": 2 * P_axis + val(PIEZO["boost_Iq_W"]),
            "plates_mass_g": 2 * ps.n_p * m_plate * 1e3, "C_per_axis_uF": ps.n_p * C * 1e6, "V_pp": Vpp,
            "worst_case_tol": worst, "label": "CALC (force-travel line of MFR AMF-11 endpoints; power ASSUMPTION recovery)"}
