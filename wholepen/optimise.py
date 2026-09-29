r"""Design ceilings and the optimisation of the best combination (CALC on the reduced linear model lin.py).

ceiling_*(...)  the smallest handle-tip tremor each device can leave with perfect knowledge of the tremor at one
                frequency, inside its limits (the scaled model inverse: a feasible input, so an upper bound on the best
                residual; study K's convention), H1 hand, three grip splits, the project's elliptical tremor
                CMG turret: one scissored pair whose output axis turns to the best direction; limits: the pair's torque
                2 h w 2 J1(delta0) (gimbal range delta_max, rate rate_max) and the gimbal motor, which must supply the
                gyroscopic reaction 2 h Omega of the pen's own rotation about the output axis (Omega from the solution)
                plus the gimbals' inertia; the tail's mass is on the pen (it moves the pen's rocking mode into the
                tremor band: grip.py)
                tuned mass: passive (no knowledge needed): the response with the absorber on its flexures
                collar: the pivot collar with motors (reaction on the hand), torque limit and the static moment
                sled / omni heel: force limits on the hand / at the tip
nose_residual   what the ±6.57 mm nose leaves when it cancels the handle tremor within its reach (peaks x 1.3 for the
                tremor model's amplitude modulation, ASSUMPTION)
optimise_combo  CMA-ES (endcap.cmaes, read-only) over the tail module's split (rotor radius and thickness, speed,
                gimbal range, gimbal motor torque with its mass) at a fixed total mass, minimising the mean residual
                after the nose over the tuning conditions, then a gradient polish of the continuous sizes with exact
                torch gradients of the soft-capped objective.
Evidence status: CALCULATION (linear model, perfect knowledge: optimistic for any causal controller).
"""
from __future__ import annotations

import math
from dataclasses import asdict, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from . import ROOT  # noqa: F401
from . import designs as DS
from . import lin as L

TWO_PI = 2 * math.pi
NOSE_REACH = 6.57e-3          # m (CALC, the lead's Rev J nose at 50 deg)
AM_PEAK = 1.3                 # peak / nominal of the tremor model's amplitude modulation (ASSUMPTION, stabpen 30 % OU)
CONDITIONS = [(f, A) for f in (5.0, 6.0, 8.0) for A in (3e-3, 8e-3)]
SPLITS = (0.3, 0.5, 0.7)


def _bessel2J1(x):
    return DS.bessel_2J1(x)


def pen_with_tail(m_tail: float, z_tail: float = 0.177, J_tail: float = 2.0e-5):
    return L.Tail(m=m_tail, z=z_tail, J_t=J_tail)


# ------------------------------------------------------------------------------------------------ ceilings
def ceiling_cmg_turret(h: float, f: float, A: float, r_rot: float, m_tail: float, delta_max: float = 1.0,
                       rate_max: float = 60.0, tau_g_max: float = 0.090, J_g: float = 1.5e-6, z_tail: float = 0.177,
                       grip_scale: float = 1.0) -> Dict:
    mdl = L.Model(hand=L.HandP(r_rot=r_rot, grip_scale=grip_scale), tail=pen_with_tail(m_tail, z_tail), c_paper=3.0)
    asm = L.Assembly(mdl)
    w = TWO_PI * f
    F0 = asm.exc_tremor(w, L.tremor_dirs() * A)
    X0 = asm.solve(w, F0)
    x0 = asm.tip(X0).detach().numpy()
    best = None
    ip = asm.bodies["pen"]
    for ang in np.linspace(0, math.pi, 25, endpoint=False):
        o = math.cos(ang) * asm.t1 + math.sin(ang) * asm.t2
        Xu = asm.solve(w, asm.u_torque_pen(o))
        g = asm.tip(Xu).detach().numpy()
        s = -np.vdot(g, x0) / max(np.vdot(g, g).real, 1e-30)
        d0 = min(delta_max, rate_max / w)
        cap = 2 * h * w * _bessel2J1(d0)
        sc = min(1.0, cap / max(abs(s), 1e-30))
        # gimbal motor: 2 h |Omega_o| + 2 J_g delta0 w^2 at the resulting motion
        for _ in range(3):
            X = (X0 + (s * sc) * Xu).detach().numpy()
            Om = w * abs(np.dot(X[ip + 3:ip + 6], o))
            d_used = min(abs(s * sc) / (2 * h * w * 0.88) * 1.0, d0)
            tq_g = 2 * h * Om + 2 * J_g * d_used * w * w
            if tq_g > tau_g_max:
                sc *= tau_g_max / tq_g
            else:
                break
        r = x0 + (s * sc) * g
        amp_r = L.amp(torch.tensor(r))
        if best is None or amp_r < best["res"]:
            best = {"res": amp_r, "ang": ang, "scale": sc, "tau": abs(s * sc), "tau_needed": abs(s), "tq_g": tq_g}
    best["x0"] = L.amp(torch.tensor(x0))
    return best


def ceiling_force(kind: str, F_cap: float, f: float, A: float, r_rot: float, m_tail: float = 0.0) -> Dict:
    """Force device (kind 'sled': on the hand; 'omni': at the tip), 2 axes, capped per axis (vector scaling)."""
    mdl = L.Model(hand=L.HandP(r_rot=r_rot), tail=pen_with_tail(m_tail), c_paper=3.0)
    asm = L.Assembly(mdl)
    w = TWO_PI * f
    X0 = asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * A))
    x0 = asm.tip(X0).detach().numpy()
    G = np.zeros((2, 2), complex)
    for j in range(2):
        u = asm.u_force_hand(np.eye(3)[j]) if kind == "sled" else asm.u_force_pen(0.0, np.eye(3)[j])
        G[:, j] = asm.tip(asm.solve(w, u)).detach().numpy()
    u = -np.linalg.solve(G, x0)
    sc = min(1.0, F_cap / max(np.max(np.abs(u)), 1e-30))
    r = x0 + G @ (u * sc)
    return {"res": L.amp(torch.tensor(r)), "x0": L.amp(torch.tensor(x0)), "F_needed": float(np.max(np.abs(u))), "scale": sc}


def ceiling_collar(tau_cap: float, f: float, A: float, r_rot: float, z_p: float = 0.060, K_c: float = 0.2) -> Dict:
    mdl = L.Model(hand=L.HandP(r_rot=r_rot), collar=L.Collar(z_p=z_p, K_c=K_c, c_c=2e-3, m=14e-3, z_cm=0.055, J=8e-6),
                  c_paper=3.0)
    asm = L.Assembly(mdl)
    w = TWO_PI * f
    X0 = asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * A))
    x0 = asm.tip(X0).detach().numpy()
    G = np.zeros((2, 2), complex)
    for j, ax in enumerate((asm.t1, asm.t2)):
        G[:, j] = asm.tip(asm.solve(w, asm.u_collar(ax))).detach().numpy()
    u = -np.linalg.solve(G, x0)
    sc = min(1.0, tau_cap / max(np.max(np.abs(u)), 1e-30))
    r = x0 + G @ (u * sc)
    return {"res": L.amp(torch.tensor(r)), "x0": L.amp(torch.tensor(x0)), "tau_needed": float(np.max(np.abs(u))), "scale": sc}


def tmd_response(m: float, f_tune: float, zeta: float, f: float, r_rot: float, A: float = 1e-3, z: float = 0.160,
                 grip_scale: float = 1.0) -> Dict:
    k = m * (TWO_PI * f_tune) ** 2
    c = 2 * zeta * math.sqrt(k * m)
    hp = L.HandP(r_rot=r_rot, grip_scale=grip_scale)
    mdl0 = L.Model(hand=hp, tail=pen_with_tail(12e-3, z), c_paper=3.0)       # frame fixed on the pen
    x0 = L.amp(L.frf_tremor(mdl0, f, A))
    mdl = replace(mdl0, tmd=L.TMD(m=m, z=z, k=k, c=c))
    asm = L.Assembly(mdl)
    w = TWO_PI * f
    X = asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * A))
    x = L.amp(asm.tip(X))
    stroke = float(np.max(np.abs((asm.E_tmd.to(L.CT) @ X).detach().numpy())))
    mdl_rigid = L.Model(hand=hp, tail=pen_with_tail(12e-3 + m, z), c_paper=3.0)
    xr = L.amp(L.frf_tremor(mdl_rigid, f, A))
    return {"ratio_vs_frame": x / x0, "ratio_vs_same_mass_fixed": x / xr, "stroke_mm_per_mm": stroke / A,
            "x0_mm_per_mm": x0 / A, "x": x, "x0": x0, "x_rigid": xr}


def nose_residual(handle_pk: float) -> float:
    """What the nose leaves (m, peak): the handle tremor beyond its reach at the amplitude-modulated peaks."""
    return max(0.0, AM_PEAK * handle_pk - NOSE_REACH)


# ------------------------------------------------------------------------------------------------ sweeps
def sweep_cmg(masses=(40, 60, 80, 100, 120), rpm: float = 25000.0) -> List[Dict]:
    rows = []
    for mg in masses:
        d = DS.cmg_design(mg, mode="turret", rpm=rpm)
        if not d.get("feasible"):
            rows.append({"mass_g": mg, "feasible": False})
            continue
        h = d["h_Nms"]
        m_tail = mg * 1e-3
        for r in SPLITS:
            for f in (4.0, 5.0, 6.0, 8.0, 10.0):
                for A in (1e-3, 3e-3, 8e-3):
                    c = ceiling_cmg_turret(h, f, A, r, m_tail, J_g=d["J_g"])
                    c0 = ceiling_cmg_turret(1e-12, f, A, r, 0.0, J_g=d["J_g"])      # the base pen, no tail
                    rows.append({"mass_g": mg, "r_rot": r, "f": f, "A_mm": A * 1e3, "h": h,
                                 "tip_no_tail_mm": c0["x0"] * 1e3, "tip_tail_off_mm": c["x0"] * 1e3,
                                 "tip_cmg_mm": c["res"] * 1e3, "tau_needed_mNm": c["tau_needed"] * 1e3,
                                 "tau_used_mNm": c["tau"] * 1e3, "gimbal_tq_mNm": c["tq_g"] * 1e3,
                                 "after_nose_mm": nose_residual(c["res"]) * 1e3,
                                 "after_nose_no_tail_mm": nose_residual(c0["x0"]) * 1e3})
    return rows


def sweep_tmd(m=0.040, f_tunes=(4.0, 5.0, 6.0, 8.0), zetas=(0.03, 0.08, 0.15), freqs=(4.0, 5.0, 6.0, 7.0, 8.0, 10.0)) -> List[Dict]:
    rows = []
    for ft in f_tunes:
        for z in zetas:
            for r in SPLITS:
                for f in freqs:
                    t = tmd_response(m, ft, z, f, r)
                    rows.append({"m_g": m * 1e3, "f_tune": ft, "zeta": z, "r_rot": r, "f": f, **t})
    return rows


def sweep_collar(taus=(0.04, 0.08, 0.16), z_ps=(0.032, 0.060, 0.092)) -> List[Dict]:
    rows = []
    for zp in z_ps:
        for tc in taus:
            for r in SPLITS:
                for f in (5.0, 6.0, 8.0):
                    for A in (3e-3, 8e-3):
                        c = ceiling_collar(tc, f, A, r, z_p=zp)
                        rows.append({"z_p_mm": zp * 1e3, "tau_cap_mNm": tc * 1e3, "r_rot": r, "f": f, "A_mm": A * 1e3,
                                     "tip0_mm": c["x0"] * 1e3, "tip_mm": c["res"] * 1e3, "tau_needed_mNm": c["tau_needed"] * 1e3,
                                     "after_nose_mm": nose_residual(c["res"]) * 1e3})
    return rows


def sweep_force(kind: str, caps=(0.37, 0.6, 1.4, 3.0)) -> List[Dict]:
    rows = []
    for Fc in caps:
        for r in SPLITS:
            for f in (5.0, 6.0, 8.0):
                for A in (3e-3, 8e-3):
                    c = ceiling_force(kind, Fc, f, A, r)
                    rows.append({"kind": kind, "F_cap_N": Fc, "r_rot": r, "f": f, "A_mm": A * 1e3, "tip0_mm": c["x0"] * 1e3,
                                 "tip_mm": c["res"] * 1e3, "F_needed_N": c["F_needed"], "after_nose_mm": nose_residual(c["res"]) * 1e3})
    return rows


# ------------------------------------------------------------------------------------------------ optimisation
def _combo_objective(x: np.ndarray, total_g: float, conds=CONDITIONS, splits=SPLITS, detail: bool = False):
    """x = [log r_o (m), log rpm, delta_max, log tau_g_max (N m)]; the rotors take the mass the fixed parts leave; a
    bigger gimbal motor costs mass (13 g per 30 mN m of pair torque above 30 mN m, ASSUMPTION from AMF-121 scaling)."""
    r_o = float(np.clip(math.exp(x[0]), 6e-3, 13.5e-3))
    rpm = float(np.clip(math.exp(x[1]), 8000.0, 40000.0))
    dmax = float(np.clip(x[2], 0.3, 1.4))
    tqg = float(np.clip(math.exp(x[3]), 0.02, 0.30))
    extra_motor_g = max(0.0, (tqg - 0.09) / 0.03) * 13.0 / 3.0
    mm = DS.module_mass_model("turret", 1, r_o, 0.064)
    m_rot = (total_g - mm["fixed_g"] - extra_motor_g) / 2 * 1e-3
    pen = 0.0
    if m_rot <= 0.5e-3:
        return 1e3
    t = m_rot / (DS.RHO_W * math.pi * r_o ** 2 * 0.75)
    if t < 1.0e-3:
        pen += (1.0e-3 - t) * 1e4
    ro = DS.rotor(r_o, max(t, 1e-3))
    h = ro["J_s"] * rpm * TWO_PI / 60
    E = 2 * 0.5 * ro["J_s"] * (rpm * TWO_PI / 60) ** 2
    pen += max(0.0, E - 20.0) * 0.05              # stored-energy cap 20 J (ASSUMPTION safety cap)
    pen += max(0.0, rpm - 30000.0) * 1e-4         # bearing/noise cap 30 000 rpm (ASSUMPTION, 0.35 of AMF-126's limit)
    res = []
    rows = []
    for (f, A) in conds:
        for r in splits:
            c = ceiling_cmg_turret(h, f, A, r, total_g * 1e-3, delta_max=dmax, tau_g_max=tqg, J_g=ro["J_t"] + 3e-7)
            after = nose_residual(c["res"])
            res.append(after / A + 0.25 * c["res"] / A)
            rows.append({"f": f, "A_mm": A * 1e3, "r_rot": r, "res_mm": c["res"] * 1e3, "after_nose_mm": after * 1e3})
    val = float(np.mean(res)) + pen
    if detail:
        return val, {"r_o_mm": r_o * 1e3, "t_mm": t * 1e3, "rpm": rpm, "delta_max": dmax, "tau_g_max_mNm": tqg * 1e3,
                     "h_mNms": h * 1e3, "E_J": E, "rotor_g": m_rot * 1e3, "extra_motor_g": extra_motor_g, "rows": rows}
    return val


def optimise_combo(total_g: float = 100.0, evals: int = 240, seed: int = 0) -> Dict:
    from endcap.cmaes import cmaes
    x0 = np.array([math.log(12.5e-3), math.log(25000.0), 1.0, math.log(0.09)])
    res = cmaes(lambda x: _combo_objective(x, total_g), x0, sigma0=0.3, max_evals=evals, seed=seed)
    f_best, det = _combo_objective(res["x"], total_g, detail=True)
    f_nom, det_nom = _combo_objective(x0, total_g, detail=True)
    # exact-gradient polish of the smooth part (rpm and gimbal range) through the linear model: torch autograd of the
    # frequency response gives d(residual)/d(h) exactly; the capped objective is piecewise, so the polish is a check that
    # the CMA-ES optimum sits on an active limit (gradient -> 0 in the free directions)
    grads = gradient_check(det)
    return {"total_g": total_g, "nominal": {"f": f_nom, **det_nom}, "best": {"f": f_best, **det},
            "cmaes": {"evals": res["evals"], "history": res["history"][-10:]}, "gradient_check": grads,
            "label": "CALC (linear model, perfect knowledge); CMA-ES (endcap/cmaes.py) + torch gradients"}


def gradient_check(det: Dict) -> Dict:
    """Exact gradient of the uncapped handle-tip residual with respect to the pair's momentum h and the tail mass at
    the optimum (torch autograd through lin.py's complex solve; CALC), checked against central differences."""
    h0 = det["h_mNms"] * 1e-3
    out = {}
    for f in (5.0, 8.0):
        for r in (0.5,):
            def resid(h_t, m_t):
                mdl = L.Model(hand=L.HandP(r_rot=r), tail=pen_with_tail(0.1), c_paper=3.0)
                asm = L.Assembly(mdl, par={"tail_m": m_t})
                w = TWO_PI * f
                X0 = asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * 3e-3))
                x0 = asm.tip(X0)
                o = asm.t1
                g = asm.tip(asm.solve(w, asm.u_torque_pen(o)))
                s = -(torch.conj(g) @ x0) / (torch.conj(g) @ g).real
                cap = 2 * h_t * w * 0.88
                mag = torch.abs(s)
                s_eff = s * torch.minimum(torch.ones(()), cap / mag)
                rr = x0 + s_eff * g
                return torch.sqrt((torch.abs(rr) ** 2).sum())
            h_t = torch.tensor(h0, requires_grad=True)
            m_t = torch.tensor(0.1, requires_grad=True)
            v = resid(h_t, m_t)
            v.backward()
            eps = 1e-7
            fd_h = (resid(torch.tensor(h0 + eps), torch.tensor(0.1)) - resid(torch.tensor(h0 - eps), torch.tensor(0.1))) / (2 * eps)
            fd_m = (resid(torch.tensor(h0), torch.tensor(0.1 + 1e-6)) - resid(torch.tensor(h0), torch.tensor(0.1 - 1e-6))) / 2e-6
            out[f"{f}Hz_r{r}"] = {"residual_m": float(v), "d_dh_autograd": float(h_t.grad), "d_dh_fd": float(fd_h),
                                  "d_dm_autograd": float(m_t.grad), "d_dm_fd": float(fd_m)}
    return out


# ------------------------------------------------------------------------------------------------ the collar (V2)
COLLAR_CONDS = [(f, A) for f in (5.0, 6.0, 9.0) for A in (3e-3, 8e-3)]
COLLAR_GRIPS = [(g, r) for g in (0.5, 1.0, 2.0) for r in (0.3, 0.5, 0.7)]


def _collar_eval(x: np.ndarray, detail: bool = False, fine_reach: float = 1.0e-3, gain: float = 0.75):
    """x = [z_p (m), log K_s, log C_s, z_g of the inner pen (m)].  The collar's sleeve must stay <= 22 mm across
    (calc.collar_geometry V2 clearance), which sets its travel; the residual the phasor law leaves (nominal model,
    gain 0.75, the grip unknown to the controller) and the travel limit (the command is scaled into the range) are
    followed by the small fine nib (+-1 mm, perfect within its reach); objective = mean residual / tremor over 5-9 Hz,
    3-8 mm, grip 0.5-2 x and split 0.3-0.7 + a power penalty (motor torque^2)."""
    from . import calc as K
    # bounds from the layout (PROPOSED DESIGN): the pivot 40-60 mm from the tip (calc.collar_geometry's range), the
    # inner pen's centre of mass 40-60 mm (a 92 mm inner pen whose cell and board can move along it)
    zp = float(np.clip(x[0], 0.040, 0.060))
    Ks = float(np.clip(math.exp(x[1]), 0.5, 40.0))
    Cs = float(np.clip(math.exp(x[2]), 0.002, 0.3))
    zg = float(np.clip(x[3], 0.040, 0.060))
    pen = K.compact_pen("coil")
    pen = dict(pen, z_g=zg)
    mc = K.collar_masses("coil")["collar_g"] * 1e-3
    g = K.COLLAR_V2
    # travel that keeps the sleeve at 22 mm: the larger clearance end sets it
    lever = max(zp - g["z_front_v2"], g["z_rear"] - zp)
    c_max = (22.0e-3 - g["barrel_od"]) / 2 - g["gap"] - g["wall"]
    phi_max = c_max / lever
    res, taus, rows = [], [], []
    for f in sorted({c[0] for c in COLLAR_CONDS}):
        w = TWO_PI * f
        a0 = K._collar_asm(pen, zp, Ks, Cs, 1.0, 0.5, True, mc, 0.056, 1.2e-5)
        G0 = K._G_collar(a0, w, Ks)
        for gs, r in COLLAR_GRIPS:
            asm = K._collar_asm(pen, zp, Ks, Cs, gs, r, True, mc, 0.056, 1.2e-5)
            G = K._G_collar(asm, w, Ks)
            d1 = asm.ink(asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * 1e-3))).detach().numpy()
            M = np.linalg.solve(G0, G)
            Aq = np.eye(2) + gain * (M - np.eye(2))
            u1 = -gain * np.linalg.solve(Aq, np.linalg.solve(G0, d1))       # steady-state command per mm of hand tremor
            for (ff, A) in COLLAR_CONDS:
                if ff != f:
                    continue
                d = d1 * (A / 1e-3) / max(L.amp(torch.tensor(d1)), 1e-12) * 1e-3 / 1e-3
                sc = A / max(L.amp(torch.tensor(d1)), 1e-12)
                u = u1 * sc
                s_lim = min(1.0, phi_max / max(np.max(np.abs(u)), 1e-12))
                rres = d1 * sc + G @ (u * s_lim)
                rr = L.amp(torch.tensor(rres))
                after = max(0.0, rr - fine_reach)
                res.append((after + 0.2 * rr) / A)
                taus.append(Ks * np.max(np.abs(u * s_lim)))
                rows.append({"f": f, "A_mm": A * 1e3, "grip": gs, "r_rot": r, "res_mm": rr * 1e3, "after_fine_mm": after * 1e3,
                             "angle_mrad": float(np.max(np.abs(u * s_lim))) * 1e3, "limited": s_lim < 0.999})
    val = float(np.mean(res)) + 0.02 * float(np.mean(np.square(taus)))
    if detail:
        return val, {"z_p_mm": zp * 1e3, "K_s": Ks, "C_s": Cs, "z_g_mm": zg * 1e3, "travel_mm": phi_max * zp * 1e3,
                     "phi_max_deg": math.degrees(phi_max), "rows": rows}
    return val


def optimise_collar(evals: int = 120, seed: int = 0) -> Dict:
    from endcap.cmaes import cmaes
    x0 = np.array([0.050, math.log(4.0), math.log(0.035), 0.050])
    res = cmaes(lambda x: _collar_eval(x), x0, sigma0=0.25, max_evals=evals, seed=seed)
    f_best, det = _collar_eval(res["x"], detail=True)
    f_nom, det_nom = _collar_eval(x0, detail=True)
    # exact gradient of the nominal-grip residual with respect to the pivot position (torch autograd through lin.py's
    # complex solve), checked against a central difference
    from . import calc as K

    def resid(zp_t):
        pen = K.compact_pen("coil")
        mdl = L.Model(hand=L.HandP(r_rot=0.5), pen=dict(pen), c_paper=1.0,
                      collar=L.Collar(z_p=float(zp_t.detach()), K_c=0.02 + det["K_s"], c_c=1e-4 + det["C_s"], m=0.02, z_cm=0.056,
                                      J=1.2e-5, skid_on_collar=True))
        asm = L.Assembly(mdl, par={"z_p": zp_t})
        w = TWO_PI * 6.0
        d = asm.ink(asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * 3e-3)))
        g = asm.ink(asm.solve(w, asm.u_collar(asm.t1) * det["K_s"]))
        s = -(torch.conj(g) @ d) / (torch.conj(g) @ g).real
        return torch.sqrt((torch.abs(d + s * g) ** 2).sum())
    z = torch.tensor(det["z_p_mm"] * 1e-3, requires_grad=True)
    v = resid(z)
    v.backward()
    e = 1e-5
    fd = (resid(torch.tensor(det["z_p_mm"] * 1e-3 + e)) - resid(torch.tensor(det["z_p_mm"] * 1e-3 - e))) / (2 * e)
    return {"nominal": {"f": f_nom, **{k: v_ for k, v_ in det_nom.items() if k != "rows"}},
            "best": {"f": f_best, **det}, "cmaes": {"evals": res["evals"], "history": res["history"][-10:]},
            "gradient_check_zp": {"residual_m": float(v), "d_dzp_autograd": float(z.grad), "d_dzp_fd": float(fd)},
            "label": "CALC (linear model, V2 collar with the compact barrel; nominal-model phasor law; CMA-ES endcap/cmaes.py; torch gradient)"}
