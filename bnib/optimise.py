r"""Multi-objective design of the candidate nibs (CALC on PROPOSED DESIGNS; no weighted score).

Method.  For each candidate family and grip class the continuous design variables are searched by CMA-ES
(endcap.cmaes, imported read-only) on epsilon-constraint problems:
    minimise   P_cont (continuous copper or drive power, mean over 35/50/60/75 deg at duty A, Km x 0.85)
    subject to travel under load >= eps_T at Km x 0.70 (hot coil, 3.3 V: candidates.evaluate), fits the bore,
               Goodman safety factor >= 1.5 at full travel (43.2 M cycles), bandwidth (first parasitic mode / 3)
               >= 40 Hz, skin <= 41 degC, (optionally) mass <= eps_M
for a ladder of eps_T; every evaluated point is kept, and the Pareto fronts are read off the pooled points
(P_cont, peak power, travel, total and moving mass, centre of mass, diameter, skin temperature, sensor error; the
failure state is reported, not traded).  Magnetics uncertainty: Km of the image method is an upper bound; the design
is checked at Km x 0.7 and its power reported at 0.7 / 0.85 / 1.0.
Exact gradients where exact: the translation family's power is a closed-form chain (vc_axial -> Km, moving mass ->
inertia and weight, vector contact statics, counter-face or no balance) re-written here in PyTorch (p_cont_torch,
checked against candidates.evaluate); the CMA-ES optimum of (w, t_m, t_c) is polished by L-BFGS on it with smooth
penalties for the bore and the travel constraint (the wires and travel held).  Discrete choices (piezo plate type
and count) are enumerated.  Results cached per problem in bnib/build/opt_cache.json (resumable).
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from . import BUILD, cache_path
from . import actuators as A
from . import balance as BL
from . import candidates as CD
from . import contact as C
from . import flexure as FX
from . import loads as LD
from .labels import CONTACT, DRIVE, FRICTION, G0, MAT, val

D2R = math.pi / 180.0
DT_ = torch.float64
CACHE = BUILD / "opt_cache.json"
KM_OBJ, KM_CON = 0.85, 0.70
SF_MIN, BW_MIN, T_SKIN_MAX = 1.5, 40.0, 41.0

SPACES = {
    "translation": [("w", 1.2e-3, 6.5e-3), ("t_m", 0.8e-3, 3.5e-3), ("t_c", 0.20e-3, 0.80e-3),
                    ("wire_d", 0.10e-3, 0.30e-3), ("wire_L", 12e-3, 35e-3), ("travel", 0.4e-3, 1.6e-3)],
    "gimbal": [("w", 1.2e-3, 6.5e-3), ("t_m", 0.8e-3, 3.5e-3), ("t_c", 0.20e-3, 0.80e-3),
               ("L_t", 30e-3, 60e-3), ("L_a", 15e-3, 70e-3), ("travel", 0.4e-3, 1.6e-3)],
}
OD_SLIM = ("od", 12e-3, 16e-3)


def _grip(gclass: str, od: Optional[float] = None) -> CD.Grip:
    return CD.pen24() if gclass == "pen24" else CD.slim(od or 14e-3)


def decode(u: np.ndarray, space) -> Dict[str, float]:
    """Unbounded CMA-ES coordinates -> the box (logistic map)."""
    out = {}
    for ui, (nm, lo, hi) in zip(u, space):
        out[nm] = lo + (hi - lo) / (1.0 + math.exp(-float(np.clip(ui, -30, 30))))
    return out


def encode(x: Dict[str, float], space) -> np.ndarray:
    u = []
    for nm, lo, hi in space:
        p = min(max((x[nm] - lo) / (hi - lo), 1e-4), 1 - 1e-4)
        u.append(math.log(p / (1 - p)))
    return np.array(u)


def build(key: str, gclass: str, x: Dict[str, float]) -> CD.Design:
    g = _grip(gclass, x.get("od"))
    d = CD.make(key, g)
    for nm in ("w", "t_m", "t_c", "travel", "L_t", "L_a"):
        if nm in x:
            setattr(d, nm, x[nm])
    if "wire_d" in x or "wire_L" in x:
        d.wire = replace(d.wire, d=x.get("wire_d", d.wire.d), L=x.get("wire_L", d.wire.L))
    return d


def metrics(key: str, gclass: str, x: Dict[str, float]) -> Dict:
    """The design's metrics at Km x 0.85 (objective) and Km x 0.70 (constraints), fast mode (CALC)."""
    d = build(key, gclass, x)
    r_mid = CD.evaluate(replace(d, km_scale=KM_OBJ), detail=False, fast=True)
    r_low = CD.evaluate(replace(d, km_scale=KM_CON), detail=False, fast=True)
    fat = r_mid.get("fatigue", {}).get("goodman_SF_full_travel", 9.9)
    viol = {
        "bore": max(0.0, (r_mid.get("r_need_mm") or 0.0) - d.grip.bore_r * 1e3) if r_mid.get("fits_bore") is not None else 0.0,
        "fatigue": max(0.0, SF_MIN - fat),
        "bandwidth": max(0.0, (BW_MIN - r_mid["bandwidth_Hz"]) / BW_MIN),
        "skin": max(0.0, r_low["T_skin_C"] - T_SKIN_MAX + 1e-9) if r_low["T_skin_C"] >= T_SKIN_MAX - 1e-6 else 0.0,
    }
    return {"key": key, "grip": gclass, "x": {k: float(v) for k, v in x.items()}, "P_cont_W": r_mid["P_cont_W"],
            "P_cont_km070_W": r_low["P_cont_W"], "P_cont_worst_W": r_mid["P_cont_worst_W"], "P_peak_W": r_low.get("P_peak_W"),
            "travel_mm": r_low["travel_under_load_mm"], "mass_g": r_mid["mass_g"], "m_eff_g": r_mid["m_eff_tip_g"],
            "com_mm": r_mid["com_mm"], "od_mm": r_mid["od_mm"], "T_skin_C": r_low["T_skin_C"],
            "hall_noise_um": r_mid["sensing"]["nib_hall_noise_um_1kHz"], "bandwidth_Hz": r_mid["bandwidth_Hz"],
            "goodman_SF": fat, "battery_h": r_mid["battery_h"], "benign_failure": r_mid["failure_state"]["benign"],
            "violations": viol}


def objective(key: str, gclass: str, space, eps_T: float, eps_M: Optional[float], log_pts: List[Dict]) -> Callable:
    def f(u):
        x = decode(u, space)
        m = metrics(key, gclass, x)
        v = dict(m["violations"])
        v["travel"] = max(0.0, (eps_T * 1e3 - m["travel_mm"]) / (eps_T * 1e3))
        if eps_M is not None:
            v["mass"] = max(0.0, (m["mass_g"] - eps_M * 1e3) / (eps_M * 1e3))
        pen = sum(vv * vv for vv in v.values())
        m["feasible_eps"] = pen == 0.0
        m["eps_T_mm"] = eps_T * 1e3
        log_pts.append(m)
        return math.log(max(m["P_cont_W"], 1e-9)) + 200.0 * pen + (5.0 if pen > 0 else 0.0)
    return f


def x0_for(key: str, gclass: str, space) -> Dict[str, float]:
    d = CD.make(key, _grip(gclass))
    x = {}
    for nm, lo, hi in space:
        if nm == "wire_d":
            v = d.wire.d
        elif nm == "wire_L":
            v = d.wire.L
        elif nm == "od":
            v = 14e-3
        else:
            v = getattr(d, nm)
        x[nm] = min(max(v, lo * 1.001), hi * 0.999)
    return x


# ------------------------------------------------------------------------------------------------ exact-gradient chain
def p_cont_torch(key: str, gclass: str, x: Dict[str, float], z: Dict[str, torch.Tensor], km_scale: float = KM_OBJ,
                 duty: Optional[LD.Duty] = None) -> Dict[str, torch.Tensor]:
    """The translation family's continuous power in PyTorch (roll 0, the four tilts, duty A), differentiable in the
    actuator geometry z = {w, t_m, t_c} (tensors); x holds the rest (wires, travel).  Same model as
    candidates.evaluate -> loads.loads_at (vector statics, friction map, slide friction, inertia, suspension, weight,
    no balance or the counter-face with its sensing errors at +1 sigma).  Also returns the peak force margin for the
    travel constraint and the bore margin."""
    duty = duty or CD.DUTY_A
    d = build(key, gclass, x)
    s_stop = d.travel + 0.2e-3
    act = A.vc_axial(z["w"], z["t_m"], z["t_c"], s_stop, moving="coil")
    Km = act["Km0"] * km_scale
    Km_min = act["Km_min"] * km_scale
    refill_m = val(CONTACT["refill_mass"])
    m_move = act["m_move"] + CD.CARRIER + refill_m + 0.5e-3 + CD.TI_SLEEVE + CD.HALL_MAGNET
    fx = FX.wire_stage(d.wire, d.travel, s_stop, float(m_move.detach()) if torch.is_tensor(m_move) else float(m_move))
    m_eff = m_move + fx["mass_g"] * 1e-3 / 3
    k_tip = fx["k_lat_N_m"]
    w8 = 2 * math.pi * duty.f
    bal = d.balance
    rows = []
    for th_deg in CD.THETAS:
        th = th_deg * D2R
        st = C.writing_load_stats(th, 0.0, d.F_s, duty.ink, duty.paper, v=duty.v_write)
        Qm = torch.tensor(st["mean_sliding"], dtype=DT_)
        sig = torch.tensor(st["rms_about_mean"], dtype=DT_)
        if duty.slide_friction:
            h = val(CONTACT["slide_friction"]) / math.tan(th)
            sig = torch.sqrt(sig ** 2 + torch.tensor([h, 0.0], dtype=DT_) ** 2)
        G = m_eff * G0 * torch.tensor([-math.cos(th), 0.0], dtype=DT_)          # translation: m g (n . u), roll 0
        Bc = torch.zeros(2, dtype=DT_)
        k_add = 0.0
        if isinstance(bal, BL.CounterFace):
            # the face normal scheduled at the estimated pose (+1 sigma errors) incl. the weight term, fixed in the pen
            th_h, ph_h = th + bal.tilt_err, bal.roll_err
            wc = -m_eff * G0 / bal.F_s_nom if bal.comp_weight else 0.0
            fr_e = C.frame(th_h, ph_h)
            fr = C.frame(th, 0.0)
            a_e, n_e = torch.tensor(fr_e["a"], dtype=DT_), torch.tensor(fr_e["n"], dtype=DT_)
            nperp = n_e - (n_e @ a_e) * a_e
            v = a_e + (1.0 / math.sin(th_h) + wc) * nperp
            v = v / torch.linalg.norm(v)
            comp = torch.stack([v @ a_e, v @ torch.tensor(fr_e["u1"], dtype=DT_), v @ torch.tensor(fr_e["u2"], dtype=DT_)])
            nr = comp[0] * torch.tensor(fr["a"], dtype=DT_) + comp[1] * torch.tensor(fr["u1"], dtype=DT_) + \
                comp[2] * torch.tensor(fr["u2"], dtype=DT_)
            Nr = d.F_s / (nr @ torch.tensor(fr["a"], dtype=DT_))
            Fface = -Nr * nr
            Bc = torch.stack([-(Fface @ torch.tensor(fr["u1"], dtype=DT_)), -(Fface @ torch.tensor(fr["u2"], dtype=DT_))])
            sig = torch.sqrt(sig ** 2 + (bal.mu_face * Nr + bal.h_face / math.tan(th)) ** 2)
            Bu = bal.keeper * Bc
        else:
            Bu = torch.zeros(2, dtype=DT_)
        hold_c = Qm + Bc + G
        hold_u = Bu + G
        D_rms2 = (m_eff * w8 * w8 * duty.q_rms) ** 2 + (k_tip * duty.q_rms) ** 2 + (k_add * duty.q_rms) ** 2
        c = duty.contact
        EF2 = c * hold_c ** 2 + (1 - c) * hold_u ** 2 + c * sig ** 2 + D_rms2
        rows.append(torch.sum(EF2) / Km ** 2)
        if th_deg == 35.0:
            hold35 = torch.linalg.norm(hold_c)
    P = torch.stack(rows).mean()
    R_hot = 2.5 * (1 + val(MAT["Cu_alpha"]) * 90)
    I_pk = min(val(DRIVE["I_peak"]), val(DRIVE["V_low"]) / R_hot)
    F_pk = Km_min * (KM_CON / km_scale) * math.sqrt(2.5) * I_pk                # the travel constraint at Km x 0.70
    w12 = 2 * math.pi * 12.0
    F_need = hold35 + k_tip * d.travel + m_eff * w12 * w12 * d.travel + 0.05
    bore_margin = d.grip.bore_r - (act["r_out"] + 0.6e-3)
    return {"P": P, "force_margin": F_pk - F_need, "bore_margin": torch.as_tensor(bore_margin, dtype=DT_), "Km": Km,
            "m_eff": m_eff}


def polish(key: str, gclass: str, x: Dict[str, float], iters: int = 40) -> Dict:
    """L-BFGS on the exact PyTorch chain over (w, t_m, t_c) with smooth penalties (bore, travel force margin, box)."""
    names = ("w", "t_m", "t_c")
    box = {nm: (lo, hi) for nm, lo, hi in SPACES["translation"]}
    z0 = {nm: torch.tensor(x[nm], dtype=DT_) for nm in names}
    # optimise in log space (positive, scale-free)
    y = torch.tensor([math.log(x[nm]) for nm in names], dtype=DT_, requires_grad=True)
    P0 = float(p_cont_torch(key, gclass, x, z0)["P"])
    opt = torch.optim.LBFGS([y], lr=0.5, max_iter=iters, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        z = {nm: torch.exp(y[i]) for i, nm in enumerate(names)}
        r = p_cont_torch(key, gclass, x, z)
        pen = torch.relu(-r["bore_margin"] / 1e-3) ** 2 * 100 + torch.relu(-r["force_margin"] / 0.05) ** 2 * 100
        for i, nm in enumerate(names):
            lo, hi = box[nm]
            pen = pen + torch.relu(math.log(lo) - y[i]) ** 2 * 100 + torch.relu(y[i] - math.log(hi)) ** 2 * 100
        loss = torch.log(r["P"]) + pen
        loss.backward()
        return loss
    try:
        opt.step(closure)
    except Exception as ex:                                   # pragma: no cover
        return {"ok": False, "error": repr(ex), "x": x}
    xz = dict(x)
    for i, nm in enumerate(names):
        xz[nm] = float(torch.exp(y[i]).detach())
    # project onto the feasible set (the soft penalties allow tiny overshoots): the box, and the bore fit
    # r_out + 0.6 mm <= bore with r_out = sqrt(2) (w + e), e = (r_carrier + s_stop + 0.3 mm) / sqrt(2)
    for nm in names:
        lo, hi = box[nm]
        xz[nm] = min(max(xz[nm], lo), hi)
    g = build(key, gclass, xz).grip
    s_stop = xz.get("travel", build(key, gclass, xz).travel) + 0.2e-3
    e = (A.R_CARRIER + s_stop + 0.30e-3) / math.sqrt(2.0)
    w_max = (g.bore_r - 0.6e-3) / math.sqrt(2.0) - e - 1e-7
    xz["w"] = min(xz["w"], w_max)
    with torch.no_grad():
        r1 = p_cont_torch(key, gclass, xz, {nm: torch.tensor(xz[nm], dtype=DT_) for nm in names})
    grad_check = gradient_check(key, gclass, x)
    return {"ok": True, "x": xz, "P_before_W": P0, "P_after_W": float(r1["P"]),
            "force_margin_N": float(r1["force_margin"]), "bore_margin_mm": float(r1["bore_margin"]) * 1e3,
            "gradient_check": grad_check}


def gradient_check(key: str, gclass: str, x: Dict[str, float], h: float = 1e-4) -> Dict:
    """Autograd gradient of the chain vs central differences (relative error; CALC check)."""
    names = ("w", "t_m", "t_c")
    zt = {nm: torch.tensor(x[nm], dtype=DT_, requires_grad=True) for nm in names}
    P = p_cont_torch(key, gclass, x, zt)["P"]
    g = torch.autograd.grad(P, [zt[nm] for nm in names])
    out = {}
    for i, nm in enumerate(names):
        xp, xm = dict(x), dict(x)
        xp[nm] *= 1 + h
        xm[nm] *= 1 - h
        Pp = float(p_cont_torch(key, gclass, xp, {k: torch.tensor(xp[k], dtype=DT_) for k in names})["P"])
        Pm = float(p_cont_torch(key, gclass, xm, {k: torch.tensor(xm[k], dtype=DT_) for k in names})["P"])
        fd = (Pp - Pm) / (2 * h * x[nm])
        out[nm] = {"autograd": float(g[i]), "fd": fd, "rel_err": abs(float(g[i]) - fd) / max(abs(fd), 1e-30)}
    return out


# ------------------------------------------------------------------------------------------------ problems
PROBLEMS = [
    # (id, candidate key, grip class, family, eps_T levels (m), eps_M, evals)
    ("pen24_c", "c_counterface", "pen24", "translation", (0.5e-3, 0.75e-3, 1.0e-3, 1.25e-3, 1.5e-3), None, 240),
    ("pen24_f", "f_translation", "pen24", "translation", (0.5e-3, 0.75e-3, 1.0e-3, 1.25e-3, 1.5e-3), None, 240),
    ("pen24_b_epm", "b_bias_epm", "pen24", "translation", (1.0e-3,), None, 200),
    ("pen24_a", "a_long_arm", "pen24", "gimbal", (0.5e-3, 1.0e-3, 1.5e-3), None, 240),
    ("slim_c", "c_counterface", "slim", "translation", (0.3e-3, 0.5e-3, 1.0e-3), None, 240),
]


def _load_cache() -> Dict:
    if CACHE.exists():
        try:
            return json.load(open(CACHE))
        except Exception:
            return {}
    return {}


def _save_cache(c: Dict) -> None:
    cache_path("opt_cache.json")
    tmp = str(CACHE) + ".tmp"
    json.dump(c, open(tmp, "w"), default=float)
    import os
    os.replace(tmp, CACHE)


def run_problem(pid: str, key: str, gclass: str, family: str, eps_list, eps_M, evals: int, quick: bool = False,
                log=print) -> Dict:
    from endcap.cmaes import cmaes
    space = list(SPACES[family]) + ([OD_SLIM] if gclass == "slim" else [])
    out = {"id": pid, "key": key, "grip": gclass, "family": family, "space": space, "runs": []}
    pts_all: List[Dict] = []
    x_prev = x0_for(key, gclass, space)
    for eps in eps_list:
        pts: List[Dict] = []
        f = objective(key, gclass, space, eps, eps_M, pts)
        t0 = time.time()
        res = cmaes(f, encode(x_prev, space), sigma0=0.6, max_evals=(24 if quick else evals), popsize=8, seed=17)
        x_best = decode(res["x"], space)
        best = metrics(key, gclass, x_best)
        feas = [p for p in pts if p["feasible_eps"]]
        run = {"eps_T_mm": eps * 1e3, "best": best, "feasible": bool(feas), "evals": res["evals"],
               "wall_s": time.time() - t0}
        torch_ok = isinstance(CD.make(key, _grip(gclass)).balance, (BL.CounterFace, BL.NoBalance))
        if family == "translation" and feas and torch_ok:
            pol = polish(key, gclass, x_best) if not quick else {"ok": False, "note": "quick"}
            if pol.get("ok"):
                mp = metrics(key, gclass, pol["x"])
                ok = mp["travel_mm"] >= eps * 1e3 - 1e-6 and not any(v > 0 for v in mp["violations"].values())
                pol["accepted"] = bool(ok and mp["P_cont_W"] <= best["P_cont_W"])
                pol["metrics_after"] = mp
                if pol["accepted"]:
                    run["best"] = mp
                    pts.append(dict(mp, feasible_eps=True, eps_T_mm=eps * 1e3, polished=True))
            run["polish"] = pol
        out["runs"].append(run)
        pts_all += pts
        if feas:
            x_prev = x_best
        log(f"[opt] {pid} eps_T {eps * 1e3:.2f} mm: P {run['best']['P_cont_W'] * 1e3:.2f} mW, travel "
            f"{run['best']['travel_mm']:.2f} mm, mass {run['best']['mass_g']:.1f} g, feasible {run['feasible']} "
            f"({run['wall_s']:.0f} s)")
    out["points"] = pts_all
    return out


def piezo_grid(gclass: str, keys=("h_piezo", "h_piezo_c")) -> Dict:
    """Enumerate the piezo stage's discrete choices (plate type, plates per axis) and its lever (CALC)."""
    pts = []
    ods = (14e-3,) if gclass == "pen24" else (12e-3, 14e-3, 16e-3)
    for key in keys:
        for od in ods:
            g = _grip(gclass, od)
            for plate in ("PL127", "PL128"):
                w_pl = val(A.PIEZO[plate]["w"])
                if gclass == "slim" and w_pl > 2 * g.bore_r * 0.80:           # a flat plate across the bore (ASSUMPTION fit rule)
                    continue
                for n_p in (1, 2, 3):
                    for lam in (1.0, 1.33, 1.6, 2.0):
                        d = CD.make(key, g)
                        d.piezo = A.PiezoStage(plate=plate, n_p=n_p, lam=lam, m_tip=d.piezo.m_tip)
                        r = CD.evaluate(d, detail=False, fast=True)
                        pz = r["piezo"]
                        pts.append({"key": key, "grip": gclass, "x": {"plate": plate, "n_p": n_p, "lam": lam, "od": od},
                                    "P_cont_W": r["P_cont_W"], "P_cont_km070_W": r["P_cont_W"], "P_peak_W": r["P_peak_W"],
                                    "travel_mm": r["travel_under_load_mm"], "mass_g": r["mass_g"], "m_eff_g": r["m_eff_tip_g"],
                                    "com_mm": r["com_mm"], "od_mm": r["od_mm"], "T_skin_C": r["T_skin_C"],
                                    "hall_noise_um": r["sensing"]["nib_hall_noise_um_1kHz"],
                                    "bandwidth_Hz": r["bandwidth_Hz"], "goodman_SF": None, "battery_h": r["battery_h"],
                                    "benign_failure": True, "duty_feasible": r.get("duty_feasible"),
                                    "feasible_eps": bool(r.get("duty_feasible")) and r["bandwidth_Hz"] >= BW_MIN,
                                    "f_loaded_Hz": pz["f_loaded_Hz"], "violations": {}})
    return {"id": f"{gclass}_piezo", "grip": gclass, "family": "piezo", "points": pts}


# ------------------------------------------------------------------------------------------------ Pareto
OBJ = (("P_cont_W", -1), ("P_peak_W", -1), ("travel_mm", +1), ("mass_g", -1), ("m_eff_g", -1), ("od_mm", -1),
       ("T_skin_C", -1), ("hall_noise_um", -1))


def pareto(points: Sequence[Dict], objs=OBJ) -> List[Dict]:
    """Non-dominated feasible points (every objective in its own direction; no weights)."""
    P = [p for p in points if p.get("feasible_eps") and all(p.get(k) is not None for k, _ in objs)]
    if not P:
        return []
    X = np.array([[p[k] * s for k, s in objs] for p in P])        # maximise all
    keep = []
    for i in range(len(P)):
        dom = np.all(X >= X[i], axis=1) & np.any(X > X[i], axis=1)
        if not dom.any():
            keep.append(i)
    return [P[i] for i in keep]


def front2(points: Sequence[Dict], xk: str, yk: str, sx: int = +1, sy: int = -1) -> List[Dict]:
    """2-D front (maximise sx*x, maximise sy*y)."""
    P = [p for p in points if p.get("feasible_eps") and p.get(xk) is not None and p.get(yk) is not None]
    P.sort(key=lambda p: -sx * p[xk])
    out, best = [], -float("inf")
    for p in P:
        v = sy * p[yk]
        if v > best + 1e-15:
            out.append(p)
            best = v
    return out


def run(quick: bool = False, log=print, problems=None) -> Dict:
    cache = _load_cache() if not quick else {}
    out = {"problems": {}, "piezo": {}}
    for pid, key, gclass, fam, eps_list, eps_M, evals in PROBLEMS:
        if problems and pid not in problems:
            continue
        if pid in cache and not quick:
            out["problems"][pid] = cache[pid]
            log(f"[opt] {pid}: cached")
            continue
        r = run_problem(pid, key, gclass, fam, eps_list[:1] if quick else eps_list, eps_M, evals, quick=quick, log=log)
        out["problems"][pid] = r
        if not quick:
            cache[pid] = r
            _save_cache(cache)
    for gclass in ("pen24", "slim"):
        pid = f"{gclass}_piezo"
        if pid in cache and not quick:
            out["piezo"][gclass] = cache[pid]
            continue
        r = piezo_grid(gclass, keys=("h_piezo",) if quick else ("h_piezo", "h_piezo_c"))
        out["piezo"][gclass] = r
        if not quick:
            cache[pid] = r
            _save_cache(cache)
    # pooled points and fronts per grip class
    fronts = {}
    for gclass in ("pen24", "slim"):
        pts = []
        for pr in out["problems"].values():
            if pr["grip"] == gclass:
                pts += [dict(p, family=pr["family"]) for p in pr["points"]]
        pts += [dict(p, family="piezo") for p in out["piezo"].get(gclass, {}).get("points", [])]
        fronts[gclass] = {
            "n_points": len(pts), "n_feasible": sum(1 for p in pts if p.get("feasible_eps")),
            "pareto_all": _slim_pts(pareto(pts)),
            "P_vs_travel": _slim_pts(front2(pts, "travel_mm", "P_cont_W")),
            "P_vs_mass": _slim_pts(front2(pts, "mass_g", "P_cont_W", sx=-1)),
            "Ppeak_vs_meff": _slim_pts(front2(pts, "m_eff_g", "P_peak_W", sx=-1)),
            "P_vs_od": _slim_pts(front2(pts, "od_mm", "P_cont_W", sx=-1)),
            "by_family_best": _best_by_family(pts),
        }
    out["fronts"] = fronts
    out["method"] = __doc__
    return out


def _slim_pts(pts: Sequence[Dict]) -> List[Dict]:
    keys = ("key", "family", "grip", "x", "P_cont_W", "P_cont_km070_W", "P_peak_W", "travel_mm", "mass_g", "m_eff_g",
            "com_mm", "od_mm", "T_skin_C", "hall_noise_um", "bandwidth_Hz", "goodman_SF", "battery_h", "benign_failure",
            "eps_T_mm")
    return [{k: p.get(k) for k in keys} for p in pts]


def _best_by_family(pts: Sequence[Dict]) -> Dict:
    out = {}
    for p in pts:
        if not p.get("feasible_eps"):
            continue
        k = f"{p['key']}"
        for lvl in (0.5, 1.0):
            if p["travel_mm"] >= lvl - 1e-9:
                kk = f"{k}|travel>={lvl}"
                if kk not in out or p["P_cont_W"] < out[kk]["P_cont_W"]:
                    out[kk] = _slim_pts([p])[0]
    return out
