#!/usr/bin/env python3
r"""Pencil-class pen (Rev P0): exact forces, mechanism candidates, recommended stage.

Task A1 of the pencil study (docs/pencil_mechanisms.md):
  (a) nib and housing loads for a conventional pen (the nib carries the writing force)
      and for the skid architecture (a spring presses the nib, a skid ring carries the
      rest), nominal point and envelope, static and dynamic parts, skid force and
      friction, forces at the fingers, nib-protrusion geometry;
  (b) every mechanism candidate against the same requirements (stroke under load,
      force, resonance, holding and dynamic power, temperature, 2-D fit in the 7.9 mm
      bore, mass, drop and stop robustness, availability, verdict);
  (c) detailed check of the recommended stage: beam model with the piezo moment and the
      tip load, decoupling leaves, lever, stroke against the load line, first resonance
      (lumped and finite-element), position sensor, ceramic stress at the stops and in a
      1 m drop (finite-element time-domain), drive electronics with reactive and real
      power, energy per hour and battery life per mode, haptic cue;
  (d) make/buy list and ordered development steps with experiments.

Evidence labels (every number in the JSON carries one): CALCULATION, SIMULATION,
MANUFACTURER STATEMENT (ledger id), LITERATURE (ledger id), CAD (proposed design),
ASSUMPTION.  Nothing here is a measurement.  Ledger rows that this script relies on
and that are not yet in docs/evidence.csv are written to
results/pencil/proposed_evidence_rows.csv (AMF-46..48) for the lead to append.

Outputs: results/pencil/mechanisms.json, results/pencil/fig_*.png,
results/pencil/proposed_evidence_rows.csv.
Run: python3 analysis/pencil_mechanisms.py            (about 2-4 min; magpylib sweep on 2 processes)
     python3 analysis/pencil_mechanisms.py --fast     (skips the magpylib sweep; uses a cached result if present)
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stabpen import plotstyle, provenance  # noqa: E402
from sim.pencil import design as D  # noqa: E402
from sim.pencil import power as PW  # noqa: E402

OUT = os.path.join(ROOT, "results", "pencil")
D2R = math.pi / 180.0
CALC, SIM, ASSUME, CADL = "CALCULATION", "SIMULATION", "ASSUMPTION", "CAD (proposed design)"


def ms(ledger):
    return f"MANUFACTURER STATEMENT ({ledger})"


def lab(value, unit, label, source="", note=""):
    d = {"value": value, "unit": unit, "label": label}
    if source:
        d["source"] = source
    if note:
        d["note"] = note
    return d


def r4(x):
    """Round to 4 significant digits (recursively)."""
    if isinstance(x, float):
        if not math.isfinite(x) or x == 0.0:
            return x
        return float(f"{x:.4g}")
    if isinstance(x, dict):
        return {k: r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    if isinstance(x, np.floating):
        return r4(float(x))
    return x


# ======================================================================================
# (a) LOADS
# ======================================================================================
def loads(P):
    th0 = P["writing.tilt_deg"] * D2R
    N0 = P["writing.normal_force"]
    mu0 = P["nib.mu_nib"]
    Fc0 = P["nib.spring_force"]
    mu_s = P["skid.mu"]
    st = D.stage("Q26")
    m_eq, m_c = st.m_eq_nib, st.m_couple_nib
    k_par = st.k_par_nib
    f0, A0 = 8.0, 0.3e-3
    w0 = 2 * math.pi * f0

    def dyn(f, A):
        w = 2 * math.pi * f
        return {"inertia_rel_N": m_eq * w * w * A, "base_coupling_N": m_c * w * w * A,
                "nib_still_in_page_N": abs(m_eq - m_c) * w * w * A, "parasitic_elastic_N": k_par * A}

    pen = D.load_extremes("pen", N0, th0, mu0)
    skid = D.load_extremes("skid", Fc0, th0, mu0)
    skid_lead = {"N_nib_frictionless": Fc0 / math.sin(th0), "R_perp_frictionless": Fc0 / math.tan(th0)}
    N_nib_nom = skid_lead["N_nib_frictionless"]
    N_skid = max(N0 - N_nib_nom, 0.0)
    # bushing friction band on the nib force (collar + gimbal bearing loads = (1 + 16.5/43.5) R_perp)
    nb = D.nib_assembly("Q")
    zc = (nb["L_nib"] - nb["L_col"])
    bearing_factor = nb["L_nib"] / nb["L_col"] + zc / nb["L_col"]
    mu_b = 0.08
    dN_bush = mu_b * bearing_factor * skid["R_perp_max"] / math.sin(th0)
    nominal = {
        "point": {"theta_deg": th0 / D2R, "N_user_N": N0, "mu_nib": mu0, "mu_skid": mu_s, "F_c_spring_N": Fc0,
                  "tremor_f_Hz": f0, "tremor_amp_mm": A0 * 1e3,
                  "labels": "inherited targets (writing.tilt_deg, writing.normal_force: REQ-ENV-001/002); mu and F_c ASSUMPTION (EXP-Q01, EXP-Q02)"},
        "conventional_pen": {
            "N_nib_N": lab(N0, "N", "inherited target"),
            "R_t1_max_N": lab(pen["R_t1_max"], "N", CALC, "P-5: N(cos th + mu sin th), beta = 0"),
            "R_t1_static_N": lab(pen["R_t1_static"], "N", CALC, "N cos th (COR-01)"),
            "R_t2_max_N": lab(pen["R_t2_max"], "N", CALC, "mu N, beta = 90 deg"),
            "R_perp_max_N": lab(pen["R_perp_max"], "N", CALC, "P-6 max over stroke direction"),
            "friction_N": lab(mu0 * N0, "N", CALC),
            "axial_N": lab(N0 * math.sin(th0), "N", CALC, "N sin th (beta = 90 deg)"),
        },
        "skid": {
            "N_nib_N": lab(N_nib_nom, "N", CALC, "F_c / sin th (lead convention, friction neglected)"),
            "N_nib_range_N": lab([skid["N_nib_min"], skid["N_nib_max"]], "N", CALC, "axial balance with friction, over stroke direction"),
            "R_perp_frictionless_N": lab(skid_lead["R_perp_frictionless"], "N", CALC, "F_c cot th"),
            "R_t1_max_N": lab(skid["R_t1_max"], "N", CALC, "F_c cot(th - atan mu) at beta = 0 (pull stroke)"),
            "R_t2_max_N": lab(skid["R_t2_max"], "N", CALC),
            "R_perp_max_N": lab(skid["R_perp_max"], "N", CALC, "design load per stage axis (roll unknown)"),
            "R_perp_rms_N": lab(skid["R_perp_rms"], "N", CALC),
            "nib_friction_max_N": lab(skid["friction_max"], "N", CALC),
            "N_skid_N": lab(N_skid, "N", CALC, "N_user - N_nib"),
            "skid_friction_N": lab(mu_s * N_skid, "N", CALC, "mu_skid (ASSUMPTION 0.12, EXP-Q01) x N_skid"),
            "skid_contact_condition": lab(N_nib_nom, "N", CALC, "the skid touches only if N_user > F_c/sin th; below that the nib carries all of N"),
            "nib_force_band_from_bushings_N": lab(dN_bush, "N", CALC,
                                                  f"mu_b {mu_b} (ASSUMPTION, PTFE-lined collar and gimbal bores) x bearing factor {bearing_factor:.2f} x R_perp_max / sin th"),
        },
        "cross_check_config_trade_D": {
            "note": "results/trade/config_trade.json candidate D (F_c = 0.30 N) uses N = F_c/sin th and then adds friction (P-6); "
                    "with friction in the axial balance the maximum is higher",
            "config_trade_D_F_perp_max_N": 0.2967,
            "this_script_same_convention_N": D.load_extremes("pen", 0.30 / math.sin(th0), th0, mu0)["R_perp_max"],
            "this_script_exact_axial_balance_N": D.load_extremes("skid", 0.30, th0, mu0)["R_perp_max"],
            "frictionless_F_c_cot_th_N": 0.30 / math.tan(th0),
            "label": CALC,
        },
        "dynamic_parts_Q26": {"m_eq_nib_g": m_eq * 1e3, "m_couple_nib_g": m_c * 1e3, "k_parasitic_nib_N_per_m": k_par,
                              "at_8Hz_0.3mm": dyn(f0, A0), "at_12Hz_1mm": dyn(12.0, 1e-3), "at_4Hz_0.1mm": dyn(4.0, 1e-4),
                              "label": CALC, "note": "inertia of the nib assembly and plate effective masses referred to the nib; "
                                                     "the benders' own stiffness is inside the actuator's load line and is not listed"},
        "fingers": {
            "conventional": {"normal_N": N0, "drag_N": mu0 * N0, "label": CALC},
            "skid": {"normal_N": N0, "drag_N": mu_s * N_skid + mu0 * N_nib_nom, "label": CALC,
                     "note": "drag = mu_skid N_skid + mu_nib N_nib; plus the stage reaction of the moving mass (m_couple w^2 q)"},
            "stage_reaction_at_8Hz_0.3mm_N": lab(m_c * w0 * w0 * A0, "N", CALC),
        },
    }
    # ---------------- envelope grids
    thetas = [35, 40, 45, 50, 55, 60, 65, 70, 75]
    mus = [0.05, 0.10, 0.15, 0.25, 0.35]
    Ns = [0.2, 0.5, 1.0, 1.5, 2.0]
    Fcs = [0.08, 0.10, 0.15, 0.20, 0.30]
    grid_pen, grid_skid = [], []
    for th in thetas:
        for mu in mus:
            for N in Ns:
                e = D.load_extremes("pen", N, th * D2R, mu)
                grid_pen.append({"theta_deg": th, "mu": mu, "N": N, **{k: e[k] for k in ("R_t1_max", "R_t2_max", "R_perp_max", "friction_max")}})
            for Fc in Fcs:
                e = D.load_extremes("skid", Fc, th * D2R, mu)
                grid_skid.append({"theta_deg": th, "mu": mu, "F_c": Fc, **{k: e[k] for k in ("R_t1_max", "R_t2_max", "R_perp_max", "N_nib_max", "friction_max")}})
    ext = lambda g, k: [min(r[k] for r in g), max(r[k] for r in g)]
    dyn_env = {"min_4Hz_0.1mm": dyn(4.0, 1e-4), "max_12Hz_1mm": dyn(12.0, 1e-3)}
    envelope = {
        "ranges": {"theta_deg": [35, 75], "mu": [0.05, 0.35], "N_user_N": [0.2, 2.0], "F_c_N": [0.08, 0.30],
                   "tremor_Hz": [4, 12], "tremor_mm": [0.1, 1.0]},
        "conventional_R_perp_max_N": ext(grid_pen, "R_perp_max"),
        "conventional_R_t1_max_N": ext(grid_pen, "R_t1_max"),
        "conventional_R_t2_max_N": ext(grid_pen, "R_t2_max"),
        "skid_R_perp_max_N": ext(grid_skid, "R_perp_max"),
        "skid_R_t1_max_N": ext(grid_skid, "R_t1_max"),
        "skid_R_t2_max_N": ext(grid_skid, "R_t2_max"),
        "skid_N_nib_max_N": ext(grid_skid, "N_nib_max"),
        "skid_worst_corner": max(grid_skid, key=lambda r: r["R_perp_max"]),
        "dynamic_Q26": dyn_env,
        "N_skid_range_N": [max(0.2 - 0.30 / math.sin(35 * D2R), 0.0), 2.0 - 0.08 / math.sin(75 * D2R)],
        "label": CALC,
    }
    # ---------------- protrusion
    r_ring = P["skid.ring_radius"]
    pb = D.protrusion_budget(r_ring)
    prot = {"ring_radius_mm": r_ring * 1e3,
            "p_tip_simple_mm": {str(t): D.protrusion(t * D2R, r_ring)["p_tip_simple"] * 1e3 for t in (35, 50, 75)},
            "p_centre_exact_mm": {str(t): D.protrusion(t * D2R, r_ring)["p_centre"] * 1e3 for t in (35, 50, 75)},
            "tilt_range_simple_mm": pb["tilt_range_simple"] * 1e3,
            "tilt_range_exact_mm": pb["tilt_range_exact"] * 1e3,
            "with_working_stroke_0.30_mm": pb["with_working_stroke"] * 1e3,
            "with_stops_0.40_mm": pb["with_stops"] * 1e3,
            "front_stop_centre_mm": pb["front_stop_centre"] * 1e3, "rear_stop_centre_mm": pb["rear_stop_centre"] * 1e3,
            "travel_needed_exact_mm": pb["travel_stops_exact"] * 1e3,
            "configured_travel_mm": P["nib.protrusion_travel"] * 1e3,
            "spring_force_change_over_tilt_N": P["nib.spring_rate"] * pb["tilt_range_simple"],
            "label": CALC, "note": "p >= r cot(theta) keeps the nib on the paper; the axial slide also follows the stage "
                                   "(s = q cot theta), so the travel covers tilt range plus stage accommodation"}
    return {"nominal": nominal, "envelope": envelope, "protrusion": prot,
            "grid_conventional": grid_pen, "grid_skid": grid_skid}


# ======================================================================================
# Thermal: 1-D barrel fin (plastic over a stainless chassis tube)
# ======================================================================================
FIN = dict(L=0.166, od=0.0089, h_out=10.0, T_amb=25.0, T_hand=33.0, grip=(0.012, 0.042),
           finger_frac=0.35, h_finger=600.0, wall=0.5e-3, k_pa=0.35, k_ss=16.0, ss_wall=0.15e-3)


def fin_temperatures(sources, n=333, hand=True):
    """Steady barrel temperature along z for heat sources [(z0, z1, P_W, R_int_K_per_W)].
    Axial conduction in the chassis tube and barrel; lateral loss by convection and
    radiation (h_out, as analysis/thermal.py) and to the fingers over the grip zone (in
    series with the plastic wall).  Returns z, T_surface and per-source temperatures.
    ASSUMPTIONS: h_out 10 W/m2K, finger contact 600 W/m2K over 35 % of the perimeter,
    hand 33 C, PA-GF30 0.35 W/mK, 0.15 mm 304 stainless chassis tube."""
    f = FIN
    z = np.linspace(0.0, f["L"], n)
    dz = z[1] - z[0]
    per = math.pi * f["od"]
    Gax = f["k_ss"] * math.pi * (f["od"] - 2 * f["wall"]) * f["ss_wall"] + f["k_pa"] * math.pi * (f["od"] - f["wall"]) * f["wall"]
    h_w = f["k_pa"] / f["wall"]
    g_amb = f["h_out"] * per * np.ones(n)
    g_hand = np.zeros(n)
    if hand:
        m = (z >= f["grip"][0]) & (z <= f["grip"][1])
        g_hand[m] = 1.0 / (1.0 / f["h_finger"] + 1.0 / h_w) * f["finger_frac"] * per
        g_amb[m] *= (1.0 - f["finger_frac"])
    q = np.zeros(n)
    for z0, z1, Pw, _ in sources:
        m = (z >= z0) & (z <= z1)
        q[m] += Pw / max(m.sum() * dz, dz)
    A = np.zeros((n, n))
    b = np.zeros(n)
    for i in range(n):
        A[i, i] = -(g_amb[i] + g_hand[i]) * dz
        b[i] = -(g_amb[i] * f["T_amb"] + g_hand[i] * f["T_hand"]) * dz - q[i] * dz
        for j in (i - 1, i + 1):
            if 0 <= j < n:
                A[i, i] -= Gax / dz
                A[i, j] += Gax / dz
    T = np.linalg.solve(A, b)
    src = []
    for z0, z1, Pw, Ri in sources:
        m = (z >= z0) & (z <= z1)
        src.append(float(T[m].mean() + Pw * Ri))
    return z, T, src


def fin_Rth(z0, z1, R_int):
    """Source temperature rise per watt above its zero-power value (K/W)."""
    _, T0, s0 = fin_temperatures([(z0, z1, 0.0, R_int)])
    _, T1, s1 = fin_temperatures([(z0, z1, 0.1, R_int)])
    return (s1[0] - s0[0]) / 0.1, float(T1.max() - T0.max()) / 0.1


# ======================================================================================
# Finite-element bender: modes and drop
# ======================================================================================
def fe_matrices(b: D.Bender, n_el=14, tip_mass=0.0, tip_k=0.0):
    L, EI, mu = b.L_free, b.EI, D.RHO_PZT * b.w * b.t
    le = L / n_el
    ndof = 2 * (n_el + 1)
    K = np.zeros((ndof, ndof))
    M = np.zeros((ndof, ndof))
    ke = EI / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                  [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
    me = mu * le / 420 * np.array([[156, 22 * le, 54, -13 * le], [22 * le, 4 * le ** 2, 13 * le, -3 * le ** 2],
                                   [54, 13 * le, 156, -22 * le], [-13 * le, -3 * le ** 2, -22 * le, 4 * le ** 2]])
    for e in range(n_el):
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(idx, idx)] += ke
        M[np.ix_(idx, idx)] += me
    M[-2, -2] += tip_mass
    K[-2, -2] += tip_k
    free = np.arange(2, ndof)          # clamp at node 0
    return K[np.ix_(free, free)], M[np.ix_(free, free)], le


def fe_modes(b, tip_mass=0.0, tip_k=0.0, n_el=14, k=3):
    from scipy.linalg import eigh
    K, M, _ = fe_matrices(b, n_el, tip_mass, tip_k)
    w2 = eigh(K, M, eigvals_only=True)[:k]
    return np.sqrt(np.maximum(w2, 0)) / (2 * math.pi)


def fe_curvature_stress(b, u, le):
    """Max |outer-fibre stress| along the plate from nodal (w, th) including the clamp node."""
    full = np.concatenate([[0.0, 0.0], u])
    sig = 0.0
    E_t2 = b.E_eff * b.t / 2.0
    for e in range(len(full) // 2 - 1):
        w1, t1, w2, t2 = full[2 * e:2 * e + 4]
        for xi in (0.0, 1.0):
            k = ((12 * xi - 6) * w1 + (6 * xi - 4) * le * t1 + (6 - 12 * xi) * w2 + (6 * xi - 2) * le * t2) / le ** 2
            sig = max(sig, abs(E_t2 * k))
    return sig


def drop_sim(b: D.Bender, tip_mass, gap_tip, pulse_T, dv, snubbers=(), k_stop=2e5, zeta=0.02, n_el=14,
             dt=1e-6, t_end=None):
    """Plate (cantilever, clamped at its root to the housing) with the collar share as a tip
    mass, a unilateral tip stop at +/-gap_tip, optional snubbers [(x/L, gap)], under a
    transverse half-sine base-acceleration pulse with velocity change dv (m/s) and
    duration pulse_T.  Newmark average acceleration; stop forces lagged one step.
    Returns the peak outer-fibre stress (Pa) and the peak tip deflection."""
    K, M, le = fe_matrices(b, n_el, tip_mass, 0.0)
    ndof = K.shape[0]
    r = np.zeros(ndof)
    r[0::2] = 1.0                               # translational DOFs (w) move with the base
    from scipy.linalg import eigh
    w2, _ = eigh(K, M)
    w1, w2b = math.sqrt(w2[0]), math.sqrt(w2[1])
    a0 = 2 * zeta * w1 * w2b / (w1 + w2b)
    a1 = 2 * zeta / (w1 + w2b)
    C = a0 * M + a1 * K
    A_pk = math.pi * dv / (2 * pulse_T)
    t_end = t_end or (pulse_T + 4e-3)
    nstep = int(t_end / dt)
    beta, gamma = 0.25, 0.5
    Keff = K + gamma / (beta * dt) * C + M / (beta * dt ** 2)
    Kinv = np.linalg.inv(Keff)
    u = np.zeros(ndof); v = np.zeros(ndof); a = np.zeros(ndof)
    tipi = ndof - 2
    sn_idx = []
    for xr, g in snubbers:
        node = int(round(xr * n_el))
        sn_idx.append((2 * (node - 1), g))
    sig_max, tip_max = 0.0, 0.0
    fc = np.zeros(ndof)
    for k in range(nstep):
        t = (k + 1) * dt
        ab = A_pk * math.sin(math.pi * t / pulse_T) if t <= pulse_T else 0.0
        fc[:] = 0.0
        wt = u[tipi]
        if abs(wt) > gap_tip:
            fc[tipi] = -k_stop * (abs(wt) - gap_tip) * math.copysign(1.0, wt)
        for i, g in sn_idx:
            if abs(u[i]) > g:
                fc[i] = -k_stop * (abs(u[i]) - g) * math.copysign(1.0, u[i])
        F = -M @ r * ab + fc
        rhs = F + M @ (u / (beta * dt ** 2) + v / (beta * dt) + (0.5 / beta - 1) * a) \
            + C @ (gamma / (beta * dt) * u + (gamma / beta - 1) * v + dt * (gamma / (2 * beta) - 1) * a)
        un = Kinv @ rhs
        an = (un - u) / (beta * dt ** 2) - v / (beta * dt) - (0.5 / beta - 1) * a
        vn = v + dt * ((1 - gamma) * a + gamma * an)
        u, v, a = un, vn, an
        if k % 5 == 0:
            sig_max = max(sig_max, fe_curvature_stress(b, u, le))
            tip_max = max(tip_max, abs(u[tipi]))
    return sig_max, tip_max


def fe_static_check(b, tip_mass, acc):
    """Quasi-static check: uniform inertial load + tip mass, no stop: FE vs closed form."""
    K, M, le = fe_matrices(b, 14, tip_mass, 0.0)
    r = np.zeros(K.shape[0]); r[0::2] = 1.0
    u = np.linalg.solve(K, -M @ r * acc)
    mu = D.RHO_PZT * b.w * b.t
    L = b.L_free
    M_root = mu * acc * L ** 2 / 2 + tip_mass * acc * L
    sig_cf = 6 * M_root / (b.w * b.t ** 2)
    return fe_curvature_stress(b, u, le), sig_cf


# ======================================================================================
# Position sensor: 3-D Hall facing the collar magnet (magpylib)
# ======================================================================================
def hall_sensitivity():
    import magpylib as magpy
    st = D.stage("Q26")
    n = st.n
    # CAD: magnet 0.6 x 1.0 x 1.0 mm on the collar flat, outer face at r = 2.3 mm; Hall face at 2.74 mm;
    # sensing element 0.3 mm inside the package (ASSUMPTION); Br 1.32 T (N42 class, ASSUMPTION as em_actuator.py)
    mag = magpy.magnet.Cuboid(polarization=(1.32, 0, 0), dimension=(0.6e-3, 1.0e-3, 1.0e-3), position=(2.0e-3, 0, 0))
    sensor = np.array([2.74e-3 + 0.3e-3, 0.0, 0.0])
    h = 5e-6
    def B(dx, dy):
        mag.position = (2.0e-3 + dx, dy, 0.0)
        return mag.getB(sensor)
    B0 = B(0, 0)
    dBx_dx = (B(h, 0)[0] - B(-h, 0)[0]) / (2 * h)
    dBy_dy = (B(0, h)[1] - B(0, -h)[1]) / (2 * h)
    # worst sensitivity over the collar travel (+/- 0.29 mm): the magnet approaches or leaves
    s = st.nib["nib_stop"] / n
    grid = np.linspace(-s, s, 7)
    sx, sy = [], []
    for gx in grid:
        for gy in grid:
            sx.append(abs((B(gx + h, gy)[0] - B(gx - h, gy)[0]) / (2 * h)))
            sy.append(abs((B(gx, gy + h)[1] - B(gx, gy - h)[1]) / (2 * h)))
    Bmax = max(np.linalg.norm(B(gx, 0)) for gx in grid)
    noise_T = 0.1e-3     # ASSUMPTION: 3-D Hall noise 0.1 mT rms at 1-2 kHz output rate (class value; select part, EXP-Q06)
    res_col = noise_T / min(min(sx), min(sy))
    return {"B_rest_mT": (B0 * 1e3).tolist(), "B_max_over_travel_mT": Bmax * 1e3,
            "dBx_dx_mT_per_mm_centre": dBx_dx, "dBy_dy_mT_per_mm_centre": dBy_dy,
            "min_sensitivity_mT_per_mm": min(min(sx), min(sy)), "noise_assumed_mT": noise_T * 1e3,
            "resolution_collar_um": res_col * 1e6, "resolution_nib_um": res_col * n * 1e6,
            "label": "CALCULATION (magpylib, linear magnet) with ASSUMPTIONS (Br 1.32 T, 0.3 mm element depth, 0.1 mT noise)",
            "choice": "3-D Hall (TMAG5170/TLE493D class, SPI or I2C, >= 2 kSPS) in the nose facing a 0.6 x 1 x 1 mm NdFeB "
                      "magnet on the collar; the piezo drive carries no current near it, so there is no coil crosstalk "
                      "(unlike Rev A); piezo charge self-sensing kept as a plausibility check"}


# ======================================================================================
# Moving-magnet voice coil in the 7.9 mm bore (magpylib, em_planar topology)
# ======================================================================================
def _em_planar():
    spec = importlib.util.spec_from_file_location("em_planar", os.path.join(ROOT, "analysis", "em_planar.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _vcm_eval(args):
    n, t_c, t_m, R_env, travel = args
    em = _em_planar()
    d = em.design(n, tip_travel=travel, R_env=R_env, t_m=t_m, t_c=t_c)
    if d is None:
        return {"n": n, "t_c_mm": t_c * 1e3, "t_m_mm": t_m * 1e3, "fits": False}
    r = em.evaluate(d, grid=3)
    turns = em.turns(d)
    A_w = math.pi * d["wire_d"] ** 2 / 4
    V_cu = (2 if d["double_sided"] else 1) * 2 * turns * em.coil_length_per_turn(d) * A_w   # per axis
    L_ax = d["t_m"] + 2 * (d["gap"] + 2 * d["t_c"] + d["layer_gap"]) + 2 * 0.3e-3             # + 0.3 mm iron each side
    return {"n": n, "t_c_mm": t_c * 1e3, "t_m_mm": t_m * 1e3, "fits": True, "r_magnet_mm": d["r_m"] * 1e3,
            "stroke_mm": d["stroke"] * 1e3, "Kf_centre": r["Kf_centre_N_per_A"], "R_axis_ohm": r["R_axis_ohm"],
            "Km_centre": r["Km_centre"], "Km_min": r["Km_min"], "cross_max_frac": r["cross_max_frac"],
            "magnet_g": r["magnet_mass_g"], "copper_g_2axes": 2 * V_cu * 8900 * 1e3, "axial_length_mm": L_ax * 1e3}


def vcm_sweep(fast=False):
    cache = os.path.join(OUT, "_vcm_sweep_cache.json")
    if fast and os.path.exists(cache):
        return json.load(open(cache))
    R_env = 3.95e-3 - 0.2e-3          # bore radius minus the 0.2 mm radial assembly clearance (config/pencil.yaml envelope.bore)
    jobs = [(n, tc, tm, R_env, 0.30e-3) for n in (1.0, 1.38, 2.0) for tc in (0.55e-3, 1.0e-3) for tm in (1.2e-3, 2.0e-3)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=2) as ex:
        rows = list(ex.map(_vcm_eval, jobs))
    out = {"rows": rows, "R_env_mm": R_env * 1e3, "elapsed_s": time.time() - t0,
           "label": "SIMULATION (magpylib magnetostatics, image iron = upper bound, linear magnets; analysis/em_planar.py topology)"}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(cache, "w"))
    return out


def vcm_candidate(sweep, L):
    best = max((r for r in sweep["rows"] if r["fits"]), key=lambda r: r["n"] * r["Km_min"])
    n, Km = best["n"], best["Km_min"]
    Km_tip = n * Km
    F_skid = L["nominal"]["skid"]["R_perp_max_N"]["value"]
    F_skid0 = L["nominal"]["skid"]["R_perp_frictionless_N"]["value"]
    F_pen = L["nominal"]["conventional_pen"]["R_perp_max_N"]["value"]
    P = lambda F: (F / Km_tip) ** 2
    # front-pivot lever (Rev A style): pivot L1 = 12 mm behind the ball, paddle at n*L1 behind the pivot
    L1 = 12e-3
    J = 0.84e-3 * ((67e-3) ** 2 / 12 + (34.7e-3 - L1) ** 2) + 0.103e-3 * (16.5e-3 - L1) ** 2
    m_eq = J / L1 ** 2 + best["magnet_g"] * 1e-3 * n ** 2
    w = 2 * math.pi * 8.0
    F_dyn = abs(80.0 - m_eq * w * w) * 0.3e-3
    z_coil = 12e-3 + n * L1
    R_int = 10.0      # ASSUMPTION: fixed coils bonded (50 um epoxy) to iron plates and chassis
    Rth, Rsurf = fin_Rth(z_coil - 2e-3, z_coil + 2e-3, R_int)
    # allowable copper loss: coil <= 120 C and surface <= 41 C with 65 mW electronics elsewhere
    def temps(Pc):
        z, T, s = fin_temperatures([(z_coil - 2e-3, z_coil + 2e-3, Pc, R_int), (0.078, 0.120, 0.065, 0.0)])
        return float(T.max()), s[0]
    lo, hi = 0.0, 5.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        Ts, Tc = temps(mid)
        if Ts > 41.0 or Tc > 120.0:
            hi = mid
        else:
            lo = mid
    P_allow = lo
    Ts_hold, Tc_hold = temps(min(P(F_skid), 5.0))
    return {"best_design": best, "Km_tip": Km_tip, "P_hold_skid_betaworst_W": P(F_skid), "P_hold_skid_frictionless_W": P(F_skid0),
            "P_hold_conventional_W": P(F_pen), "m_eq_nib_g": m_eq * 1e3, "F_dyn_8Hz_0.3mm_N": F_dyn,
            "P_dyn_8Hz_0.3mm_W": (F_dyn / Km_tip) ** 2 / 2, "z_coil_mm": z_coil * 1e3,
            "Rth_coil_to_ambient_K_per_W": Rth, "surface_rise_per_W": Rsurf, "P_allowable_W": P_allow,
            "T_surface_at_hold_C": Ts_hold, "T_coil_at_hold_C": Tc_hold,
            "battery_life_at_hold_h": PW.battery_life_h(P(F_skid) + 0.065),
            "labels": {"Km": sweep["label"], "P_hold": CALC, "thermal": "CALCULATION (1-D barrel fin) with ASSUMPTIONS (R_int 10 K/W, h 10 W/m2K, fingers 600 W/m2K)"}}


# ======================================================================================
# 2-D cross-section checks in the bore
# ======================================================================================
def cross_sections():
    r_b = 3.95e-3
    r_fit = r_b - 0.2e-3 * 0.0      # CAD checks against the bore radius; the 0.2 mm radial clearance is reported separately
    rows = {}
    # PICMA catalogue widths: plate chord at the refill-side face (plate beside a centred refill)
    for name, p in D.PICMA.items():
        w, t = p["w"], p["t"]
        # best case: refill pushed off-centre, plate as close to the axis as the refill allows (CAD: plate
        # mid-plane 2.15 mm off-axis leaves 0.26 mm to the bore for 3.5 mm; for one plate alone the minimum
        # distance of the outer face is set by the chord)
        y_face = 0.0 + t / 2 + 0.4e-3     # plate through the centre (no refill) + tip sweep: absolute best case
        chord = 2 * math.sqrt(max(r_b ** 2 - y_face ** 2, 0.0))
        rows[name] = {"width_mm": w * 1e3, "best_chord_mm": chord * 1e3, "fits_alone": w < chord,
                      "fits_two_axes_with_refill": False if w > 6.2e-3 else None}
    # the PL128.10 with refill offset (lead: one fits)
    rows["PL128.10"]["fits_two_axes_with_refill"] = False
    rows["PL128.10"]["note"] = ("one plate fits when swept +/-0.40 mm only with its mid-plane about 0.95 mm off-axis (swept corner at r = 3.51 mm) and "
                                "the refill moved 1.06 mm off-axis the other way (so the nib sits 1.06 mm off the barrel axis); a second orthogonal plate does not fit")
    # APA50XS (AMF-14): cross-section with stroke transverse = H 5 x W 9 mm
    rows["APA50XS"] = {"cross_section_mm": [5.0, 9.0], "diagonal_mm": math.hypot(5.0, 9.0), "bore_mm": 7.9, "fits_alone": False}
    rows["SQL-RV-1.8"] = {"cross_section_mm": [2.8, 2.8], "diagonal_mm": math.hypot(2.8, 2.8), "fits_alone": True,
                          "note": "two motors beside the refill fit (2.8 mm square each)"}
    cadL = D.cad("L").get("section_checks", {})
    cadQ = D.cad("Q").get("section_checks", {})
    rows["L35"] = {"cad_section_checks": cadL, "label": CADL}
    rows["Q26"] = {"cad_section_checks": cadQ, "label": CADL}
    rows["L40"] = {"note": "CAD message: 4.0 mm plates collide at the corner and with the bore at +/-0.40 mm tip sweep", "label": CADL}
    return rows


def _plate_rects(key):
    """Rectangles (x0, x1, y0, y1) in mm of the plates in the CAD layout, swept by +/-0.40 mm."""
    t, d, sw = 0.67, 2.15, 0.40
    out = []
    if key in ("L35", "L40"):
        w = 3.5 if key == "L35" else 4.0
        off = 0.5 * w - 1.2
        out.append((-d - t / 2 - sw, -d + t / 2 + sw, off - w / 2, off + w / 2))
        out.append((off - w / 2, off + w / 2, -d - t / 2 - sw, -d + t / 2 + sw))
    elif key == "Q26":
        w = 2.6
        for sx in (-1, 1):
            out.append((sx * d - t / 2 - sw, sx * d + t / 2 + sw, -w / 2, w / 2))
            out.append((-w / 2, w / 2, sx * d - t / 2 - sw, sx * d + t / 2 + sw))
    elif key == "PL128":
        w, y_mid = 6.15, -0.95           # plate mid-plane 0.95 mm off-axis; refill centre moved to y = +1.06 mm
        out.append((-w / 2, w / 2, y_mid - t / 2 - sw, y_mid + t / 2 + sw))
    return out


# ======================================================================================
# (b) CANDIDATES
# ======================================================================================
def piezo_candidate(key, L, hall, drop, P):
    st = D.stage(key)
    st_tol = D.stage(key, tol=-D.PICMA_TOL)
    F_nom = L["nominal"]["skid"]["R_perp_max_N"]["value"]
    F_0 = L["nominal"]["skid"]["R_perp_frictionless_N"]["value"]
    F_35 = D.load_extremes("skid", P["nib.spring_force"], 35 * D2R, P["nib.mu_nib"])["R_perp_max"]
    # dynamic drive power at 8 Hz, 0.3 mm (one axis), with both driver topologies
    w = 2 * math.pi * 8.0
    Va = 0.3e-3 / st.g_V * abs(st.k_b_nib + st.k_par_nib - st.m_eq_nib * w * w) / st.k_b_nib
    C = st.C_axis * D.C_LARGE_SIGNAL
    pb = PW.sine_drive(C, Va, 8.0, 60.0)
    pr = PW.sine_drive(C, Va, 8.0, 55.0, recovery=True)
    mass_plates = st.plates_per_axis * st.axes * st.bender.m_plate
    fits = {"PL128": "one axis only (fits)", "L40": "no (CAD)", "L35": "yes (CAD, 0.215 mm corner gap)",
            "Q26": "yes (CAD, 0.115 mm plate gap)"}[key]
    return {
        "candidate": st.label, "key": key,
        "stroke_nib_um": {"at_F_frictionless_%.3fN" % F_0: st.stroke_under_load(F_0) * 1e6,
                          "at_F_betaworst_%.3fN" % F_nom: st.stroke_under_load(F_nom) * 1e6,
                          "at_35deg_%.3fN" % F_35: st.stroke_under_load(F_35) * 1e6,
                          "betaworst_at_minus20pct_tolerance": st_tol.stroke_under_load(F_nom) * 1e6,
                          "limit_by_stops": st.nib["nib_stop"] * 1e6},
        "force_nib_N": st.F_b_nib, "first_resonance_Hz": st.f1,
        "holding_power_W": 0.0,
        "holding_note": "capacitive: static load held at zero power apart from leakage and the driver's quiescent power (see drive table)",
        "dyn_power_8Hz_0.3mm_one_axis_mW": {"V_amplitude_V": Va, "reactive_mVA": pb["reactive_VA"] * 1e3,
                                            "rail_class_B_mW": pb["P_rail_W"] * 1e3, "rail_recovery_mW": pr["P_rail_W"] * 1e3},
        "temperature_rise": "piezo self-heating < 1 mK (dielectric loss ~ 2 % of the reactive power); driver heat in the board zone (see drive table)",
        "fit_7p9_bore": fits,
        "mass_plates_g": mass_plates * 1e3,
        "drop_and_stops": drop.get(key, "see stage check"),
        "availability": "catalogue part (PI PL128.10, AMF-11)" if key == "PL128" else "custom-width PICMA-class plates (supplier custom part; make via PI or equivalent)",
        "labels": {"stroke": "CALCULATION from AMF-11 (+/-20 %) and CAD lever", "resonance": "CALCULATION (lumped; FE check in stage_check)",
                   "power": "CALCULATION with ASSUMPTION large-signal capacitance x1.3"},
        "stage": st.summary(),
    }


def other_candidates(L, vcm, P):
    th0 = 50 * D2R
    F_nom = L["nominal"]["skid"]["R_perp_max_N"]["value"]
    k1 = P["hand.grip_stiffness"]
    rows = []
    # other PICMA widths
    rows.append({"candidate": "PL112.10 / PL122.10 / PL127.10 / PL140.10 (catalogue)", "key": "PL1xx",
                 "fit_7p9_bore": "no: widths 9.6-11.0 mm exceed the 7.9 mm bore (AMF-11)",
                 "verdict": "reject (width); the same ceramic only as a custom-width plate (L35/Q26)",
                 "labels": {"widths": ms("AMF-11")}})
    # APA50XS
    apa = {"stroke_um": 66, "F_block_N": 16, "C_uF": 0.30, "V": 150, "mass_g": 2.0}
    n_amp = 0.30e-3 * 2 / (apa["stroke_um"] * 1e-6)
    rows.append({"candidate": "Amplified piezo stack APA50XS (Cedrat, AMF-14)", "key": "APA",
                 "stroke_nib_um": "66 um actuator stroke; x%.1f amplification for +/-0.30 mm" % (n_amp / 2),
                 "force_nib_N": 2 * apa["F_block_N"] / n_amp, "first_resonance_Hz": "2700 blocked-free (AMF-14) before amplification",
                 "holding_power_W": 0.0, "fit_7p9_bore": "no: 5 x 9 mm section (diagonal 10.3 mm) > 7.9 mm bore",
                 "drive": "-20..150 V: DRV2700 boost limited to 105 V; quiescent 13-24 mA per channel (AMF-16)",
                 "mass_g": 2 * apa["mass_g"], "verdict": "reject (does not fit; 150 V drive)",
                 "labels": {"data": ms("AMF-14"), "calc": CALC}})
    # VCM
    rows.append({"candidate": "Moving-magnet voice coil in the 7.9 mm bore (magpylib, em_planar topology)", "key": "VCM",
                 "Km_N_per_sqrtW": vcm["best_design"]["Km_min"], "lever": vcm["best_design"]["n"],
                 "Km_tip": vcm["Km_tip"], "holding_power_W": {"skid_betaworst": vcm["P_hold_skid_betaworst_W"],
                                                              "skid_frictionless": vcm["P_hold_skid_frictionless_W"],
                                                              "conventional_pen": vcm["P_hold_conventional_W"]},
                 "dyn_power_8Hz_0.3mm_W": vcm["P_dyn_8Hz_0.3mm_W"], "Rth_coil_to_ambient_K_per_W": vcm["Rth_coil_to_ambient_K_per_W"],
                 "P_allowable_W": vcm["P_allowable_W"], "T_coil_at_hold_C": vcm["T_coil_at_hold_C"],
                 "T_surface_at_hold_C": vcm["T_surface_at_hold_C"],
                 "battery_life_h_skid_hold": vcm["battery_life_at_hold_h"],
                 "fit_7p9_bore": "fits (planar paddle %.2f mm radius)" % vcm["best_design"]["r_magnet_mm"],
                 "mass_g": vcm["best_design"]["magnet_g"] + vcm["best_design"]["copper_g_2axes"],
                 "verdict": "reject: even with the skid, holding the transverse load costs %.1f W (%.0f x the thermal allowance %.2f W; battery %.1f h)"
                            % (vcm["P_hold_skid_betaworst_W"], vcm["P_hold_skid_betaworst_W"] / max(vcm["P_allowable_W"], 1e-9),
                               vcm["P_allowable_W"], vcm["battery_life_at_hold_h"]),
                 "labels": vcm["labels"]})
    # SQUIGGLE
    v_need = 2 * math.pi * 8.0 * 0.30e-3 / 1.379
    life_h = 1e6 / 8.0 / 3600.0
    rows.append({"candidate": "Piezo ultrasonic screw motor SQL-RV-1.8 (New Scale SQUIGGLE, AMF-15)", "key": "SQUIGGLE",
                 "speed_needed_mm_s": v_need * 1e3, "speed_rated_mm_s": ">10 at 25 g load (AMF-15)",
                 "stall_force_N": 0.3, "force_needed_collar_N": F_nom * 1.379,
                 "life_h_at_8Hz": life_h, "power_W": "about 1 W at 5 mm/s (AMF-15)", "holding_power_W": 0.0,
                 "fit_7p9_bore": "yes (2.8 x 2.8 x 6 mm)", "availability": "OEM only, qualified customers (AMF-15)",
                 "verdict": "reject: 1 M-cycle life is %.0f h of assisted writing at 8 Hz; ~1 W; speed marginal; not needed as a bias because the piezo stage holds at zero power" % life_h,
                 "labels": {"data": ms("AMF-15"), "calc": CALC}})
    # SMA
    d_w, rho, c, h, lat = 50e-6, 6450.0, 837.0, 200.0, 24e3
    tau = rho * c * d_w / (4 * h)
    eff = 170e6 * 0.03 / (rho * lat + rho * c * 30.0)
    rows.append({"candidate": "Shape-memory-alloy wire (NiTi, 50 um, antagonistic pair per axis)", "key": "SMA",
                 "cooling_time_constant_s": tau, "thermal_bandwidth_Hz": 1 / (2 * math.pi * tau),
                 "attenuation_at_8Hz": 8.0 * 2 * math.pi * tau, "efficiency": eff,
                 "fit_7p9_bore": "yes", "verdict": "reject: thermal bandwidth ~%.1f Hz (%.0fx short at 8 Hz); efficiency ~%.1f %%; continuous heating to hold"
                                                    % (1 / (2 * math.pi * tau), 8.0 * 2 * math.pi * tau, eff * 100),
                 "labels": {"calc": CALC, "properties": ASSUME + " (NiTi density 6450 kg/m3, c 837 J/kgK, latent heat 24 J/g, "
                                                         "h 200 W/m2K for a 50 um wire in still air, 3 % strain at 170 MPa); concept prior art PAT-06"}})
    # LRA as corrector
    m_lra, f_r, F_coil = 0.4e-3, 205.0, 0.08
    rows.append({"candidate": "Linear resonant actuator (6 mm coin, AMF-45) as a reaction-mass corrector", "key": "LRA",
                 "force_at_8Hz_N": F_coil * (8.0 / f_r) ** 2, "force_needed_N": k1 * 0.3e-3,
                 "verdict": "reject as corrector (moves no nib; output falls as (f/f_r)^2 below its 150-250 Hz resonance); "
                            "haptic cue only, and the stage can cue itself (stage check)",
                 "labels": {"resonance": ms("AMF-45"), "moving_mass_and_coil_force": ASSUME + " (0.4 g, 0.08 N)"}})
    # Gyroscope
    m_r, r_r, rpm = 3.27e-3, 3.5e-3, 50000.0
    I = 0.5 * m_r * r_r ** 2
    H = I * rpm * 2 * math.pi / 60
    psi = 0.30e-3 / 0.05
    Om = 2 * math.pi * 8.0 * psi
    k_rot = k1 * 0.02 ** 2
    rows.append({"candidate": "Gyroscope (brass rotor 7 x 10 mm, 3.3 g, 50 000 rpm)", "key": "GYRO",
                 "angular_momentum_Nms": H, "gyro_torque_Nm": H * Om, "hand_torque_Nm": k_rot * psi,
                 "ratio": H * Om / (k_rot * psi),
                 "verdict": "reject: gyroscopic torque %.0f %% of the hand's tremor torque; does not resist translation (the dominant nib tremor); "
                            "precession cross-couples axes; spin-up power and 3 g" % (100 * H * Om / (k_rot * psi)),
                 "labels": {"calc": CALC, "rotor_speed_and_geometry": ASSUME, "grip_stiffness": "LITERATURE (HAP-26 via parameters.yaml)"}})
    # Reaction mass / active TMD
    m_bat, x_max = 3.45e-3, 0.5e-3
    F4 = m_bat * (2 * math.pi * 4) ** 2 * x_max
    F12 = m_bat * (2 * math.pi * 12) ** 2 * x_max
    rows.append({"candidate": "Reaction mass / active tuned-mass absorber (the 3.45 g cell moved +/-0.5 mm)", "key": "TMD",
                 "force_4Hz_N": F4, "force_12Hz_N": F12, "force_needed_N": k1 * 0.3e-3,
                 "mass_x_stroke_needed_kg_m": k1 * 0.3e-3 / (2 * math.pi * 8) ** 2,
                 "verdict": "reject: %.1f-%.1f %% of the grip-spring tremor force (575 N/m x 0.3 mm); needs ~%.0f g x mm"
                            % (100 * F4 / (k1 * 0.3e-3), 100 * F12 / (k1 * 0.3e-3), k1 * 0.3e-3 / (2 * math.pi * 8) ** 2 * 1e6),
                 "labels": {"calc": CALC, "cell_mass": CADL}})
    return rows


# ======================================================================================
# (c) STAGE CHECK
# ======================================================================================
def stage_check(key, L, P, hall, fast=False):
    st = D.stage(key)
    b = st.bender
    nb = st.nib
    F_nom = L["nominal"]["skid"]["R_perp_max_N"]["value"]
    # ---- beam model
    beam = {"E_eff_GPa": b.E_eff / 1e9, "EI_Nm2": b.EI, "M_piezo_full_Nm": b.M_piezo, "k_plate_N_per_m": b.k,
            "F_b_plate_N": b.F_b, "delta_f_um": b.delta_f * 1e6,
            "tip_deflection_formula": "delta_tip = M_p L^2/(2EI) - F L^3/(3EI)  ->  delta = delta_f(V) - F/k_b",
            "f1_bare_EulerBernoulli_Hz": b.f1_bare(), "f1_bare_datasheet_Hz": 360.0,
            "clamp_stress_at_blocking_MPa": b.clamp_stress(b.F_b) / 1e6,
            "label": "CALCULATION from AMF-11 (E_eff from the datasheet stiffness; density ASSUMPTION 7.8 g/cm3)"}
    # ---- decoupling leaves
    leafs = {}
    for name, lf in (("CAD_leaf_25um_0.45x1.0mm_stainless", D.CAD_LEAF), ("recommended_C17200_30um_1.2x5mm", D.RECOMMENDED_LEAF)):
        F = b.F_b
        leafs[name] = {"k_cross_N_per_m": lf.k_cross, "k_drive_N_per_m": lf.k_drive,
                       "k_cross_over_axis_stiffness": lf.k_cross * st.plates_per_axis / st.k_col,
                       "buckling_SF_at_plate_F_b": lf.sf_buckling(F),
                       "stress_at_stop_MPa": lf.stress_cross(nb["nib_stop"] / st.n) / 1e6,
                       "stress_at_0.30mm_MPa": lf.stress_cross(0.30e-3 / st.n) / 1e6}
    # stroke if the CAD leaf were used
    st_cadleaf = D.stage(key, leaf=D.CAD_LEAF)
    leafs["effect_of_CAD_leaf"] = {"stroke_betaworst_um": st_cadleaf.stroke_under_load(F_nom) * 1e6,
                                   "free_stroke_nib_um": (st_cadleaf.k_b_nib / (st_cadleaf.k_b_nib + st_cadleaf.k_par_nib)) * st_cadleaf.delta_f_nib * 1e6,
                                   "f1_Hz": st_cadleaf.f1}
    leafs["design_rule"] = ("across: E w t^3/L^3 <= 5 % of the axis stiffness; along: E t w^3/L^3 >= 20x; lateral-torsional "
                            "buckling SF >= 2 at the plate's blocking force; cross-deflection stress <= 150 MPa alternating "
                            "(AMF-19). A single leaf meets all four only with >= ~4.5 mm of free axial span")
    leafs["label"] = "CALCULATION (beam theory; buckling factor ASSUMPTION, confirm by FEA); material AMF-18/19"
    # ---- lever and load line
    lev = []
    for n in np.linspace(0.8, 2.4, 17):
        k_eff = st.k_eff_col
        Fb_n = k_eff * b.delta_f / n
        kn = k_eff / n ** 2 + st.k_par_col / n ** 2
        lev.append({"n": n, "stroke_betaworst_um": max(0.0, (Fb_n - F_nom) / kn) * 1e6})
    load_line = []
    for th in (35, 40, 45, 50, 55, 60, 65, 70, 75):
        for Fc in (0.08, 0.15, 0.30):
            for mu in (0.05, 0.15, 0.35):
                F = D.load_extremes("skid", Fc, th * D2R, mu)["R_perp_max"]
                load_line.append({"theta_deg": th, "F_c": Fc, "mu": mu, "F_nib_N": F,
                                  "stroke_um": st.stroke_under_load(F) * 1e6,
                                  "stroke_minus20_um": D.stage(key, tol=-0.2).stroke_under_load(F) * 1e6})
    ok = [r for r in load_line if r["stroke_um"] >= 300.0]
    # ---- resonance: lumped vs FE (plates distributed, collar share lumped at the tip)
    m_rot_col = nb["m_eq_col"] / st.plates_per_axis
    k_other = st.k_par_col / st.plates_per_axis
    f_fe = fe_modes(b, tip_mass=m_rot_col, tip_k=k_other)
    reson = {"lumped_Hz": st.f1, "FE_first_three_Hz": f_fe.tolist(), "bare_plate_FE_Hz": fe_modes(b)[0],
             "m_eq_nib_g": st.m_eq_nib * 1e3, "k_total_nib_N_per_m": st.k_b_nib + st.k_par_nib,
             "label": "CALCULATION (lumped and 14-element Euler-Bernoulli FE)"}
    # ---- stresses at the stops
    k_p = b.k
    stop_col = nb["nib_stop"] / st.n
    stops = {"unpowered_at_stop_MPa": b.clamp_stress(k_p * stop_col) / 1e6,
             "driven_opposite_at_stop_MPa": b.clamp_stress(k_p * (stop_col + b.delta_f)) / 1e6,
             "blocking_rated_MPa": b.clamp_stress(b.F_b) / 1e6,
             "sigma0_bender_MPa": D.sigma0_bender(b) / 1e6,
             "P_fail_per_event": {"rated_blocking": D.p_fail(b.clamp_stress(b.F_b), b),
                                  "driven_opposite_at_stop": D.p_fail(b.clamp_stress(k_p * (stop_col + b.delta_f)), b),
                                  "unpowered_at_stop": D.p_fail(b.clamp_stress(k_p * stop_col), b)},
             "strength_basis": "LITERATURE (proposed AMF-48: Bermejo & Deluca 2012, poled PZT multilayer, 4PB, sigma0 124 MPa "
                               "elastic, Weibull m 8) scaled to the plate's effective volume; PICMA material itself UNKNOWN (EXP-Q04)",
             "label": CALC}
    # ---- drop (FE time domain)
    dv = 4.43 * 1.4          # 1 m drop, restitution 0.4 (ASSUMPTION) -> 6.2 m/s velocity change
    Ts = [0.2e-3, 0.35e-3, 0.5e-3, 1.0e-3, 2.0e-3]
    x_s = (0.35, 0.70)
    # operating-shape envelope (cubic tip-load shape) at the stop deflection + 30 um
    def w_op(xr):
        return stop_col * (3 * xr ** 2 - xr ** 3) / 2 + 30e-6
    snub = tuple((x, w_op(x)) for x in x_s)
    snub4 = tuple((x, w_op(x)) for x in (0.2, 0.4, 0.6, 0.8))
    drops = []
    for T in Ts:
        s0, t0 = drop_sim(b, m_rot_col, stop_col, T, dv)
        s1, t1 = drop_sim(b, m_rot_col, stop_col, T, dv, snubbers=snub)
        s2, t2 = drop_sim(b, m_rot_col, stop_col, T, dv, snubbers=snub4)
        drops.append({"pulse_ms": T * 1e3, "peak_g": math.pi * dv / (2 * T) / D.G0,
                      "no_snubbers_MPa": s0 / 1e6, "P_fail_no_snubbers": D.p_fail(s0, b),
                      "two_snubbers_MPa": s1 / 1e6, "P_fail_two_snubbers": D.p_fail(s1, b),
                      "four_snubbers_MPa": s2 / 1e6, "P_fail_four_snubbers": D.p_fail(s2, b)})
    s_fe, s_cf = fe_static_check(b, m_rot_col, 1000.0)
    axial = (D.RHO_PZT * b.w * b.t * b.L_free + nb["m_rot"] * 0.1 / st.plates_per_axis) * (math.pi * dv / (2 * 0.35e-3)) / (b.w * b.t)
    drop = {"dv_m_per_s": dv, "snubbers": [{"x_over_L": x, "gap_um": g * 1e6} for x, g in snub],
            "snubbers4": [{"x_over_L": x, "gap_um": g * 1e6} for x, g in snub4],
            "transverse": drops, "axial_nib_first_0.35ms_MPa": axial / 1e6,
            "FE_static_check_MPa": {"FE": s_fe / 1e6, "closed_form": s_cf / 1e6},
            "labels": {"result": "SIMULATION (FE beam, Newmark, unilateral stops)",
                       "pulse": ASSUME + ": 1 m drop, restitution 0.4, half-sine 0.2-2 ms (floor and nose compliance unknown; EXP-Q04 drop test)",
                       "damping": ASSUME + " (2 % Rayleigh)", "stop_stiffness": ASSUME + " (2e5 N/m, parameters.yaml stage.stop_stiffness)"}}
    # ---- drive electronics: reactive and real power 4-12 Hz
    drive_rows = []
    for f in (4.0, 6.0, 8.0, 10.0, 12.0):
        w = 2 * math.pi * f
        for A in (0.1e-3, 0.3e-3, 0.5e-3):
            gain = abs(st.k_b_nib + st.k_par_nib - st.m_eq_nib * w * w) / st.k_b_nib
            Va60 = min(A, st.nib["nib_stop"]) / st.g_V * gain
            C = st.C_axis * D.C_LARGE_SIGNAL
            row = {"f_Hz": f, "nib_amp_mm": A * 1e3, "V_amp_60V_rail": Va60}
            for dk, dd in PW.DRIVERS.items():
                Vr = dd["V_rail"]
                Va = Va60                      # stroke per volt is a material property: same volts on any rail
                s = PW.sine_drive(C, Va, f, Vr, dd["recovery"], dd.get("eta_c", 0.85))
                # two axes: major axis amplitude A, minor 0.4 A (tremor ellipticity 0.4, parameters.yaml)
                s2 = PW.sine_drive(C, Va * 0.4, f, Vr, dd["recovery"], dd.get("eta_c", 0.85))
                P_rail = s["P_rail_W"] + s2["P_rail_W"]
                row[dk] = {"reactive_mVA_major": s["reactive_VA"] * 1e3, "P_rail_mW_2axes": P_rail * 1e3,
                           "P_battery_mW": PW.battery_power(dk, P_rail) * 1e3}
            drive_rows.append(row)
    p_el = P["electronics.p_active"]
    modes = {}
    for dk in PW.DRIVERS:
        rec = p_el + PW.battery_power(dk, 0.0, active=False)
        r8 = next(r for r in drive_rows if r["f_Hz"] == 6.0 and r["nib_amp_mm"] == 0.3)[dk]["P_battery_mW"] * 1e-3
        modes[dk] = {"recording_only_W": rec, "tremor_assist_6Hz_0.3mm_W": p_el + r8,
                     "life_recording_h": PW.battery_life_h(rec), "life_tremor_assist_h": PW.battery_life_h(p_el + r8),
                     "energy_per_hour_recording_mWh": rec * 1e3, "energy_per_hour_assist_mWh": (p_el + r8) * 1e3}
    st55 = D.stage(key, V_rail=55.0)
    rail_penalty = {"stroke_betaworst_60V_um": st.stroke_under_load(F_nom) * 1e6,
                    "stroke_betaworst_55V_um": st55.stroke_under_load(F_nom) * 1e6,
                    "F_b_nib_55V_N": st55.F_b_nib, "label": CALC + " (piezo force and stroke proportional to the drive range)"}
    drive = {"rows": drive_rows, "modes_analytic": modes, "drivers": PW.DRIVERS, "rail_55V_penalty": rail_penalty,
             "C_axis_small_signal_uF": st.C_axis * 1e6, "C_large_signal_factor": D.C_LARGE_SIGNAL,
             "p_electronics_W": p_el, "battery": {"mAh": P["battery.capacity_mAh"], "V": P["battery.v_nom"], "usable": P["battery.usable_fraction"]},
             "labels": {"power": CALC, "p_electronics": ASSUME + " (config/pencil.yaml electronics.p_active, optics 50 mW placeholder)",
                        "battery": ASSUME + " (config/pencil.yaml, AMF-42/43)",
                        "guided": "see results/pencil/sim_metrics.json (SIMULATION)"}}
    # thermal of the board zone for the three driver options
    therm = {}
    for dk in PW.DRIVERS:
        P_tot = modes[dk]["tremor_assist_6Hz_0.3mm_W"]
        z, T, _ = fin_temperatures([(0.078, 0.120, P_tot, 0.0)])
        therm[dk] = {"P_W": P_tot, "T_surface_max_C": float(T.max())}
    z, T, _ = fin_temperatures([(0.078, 0.120, p_el, 0.0)])
    therm["recording_only"] = {"P_W": p_el, "T_surface_max_C": float(T.max())}
    drive["thermal_board_zone"] = therm
    # ---- haptic cue
    M_pen = D.cad("Q")["mass_total_g"] * 1.1e-3
    w = 2 * math.pi * 200.0
    thr = w * w * 0.08e-6      # HAP-27: ~0.06-0.1 um at 160-320 Hz -> 0.08 um at 200 Hz (interpolated)
    hap = []
    for A in (20e-6, 100e-6, 300e-6):
        a = st.m_couple_nib * w * w * A / M_pen
        hap.append({"nib_amp_um": A * 1e6, "barrel_acc_m_s2_peak": a, "barrel_acc_G_rms": a / math.sqrt(2) / D.G0,
                    "dB_above_threshold": 20 * math.log10(a / thr)})
    lra = {"G_rms_vendor": 0.9, "F_rms_N_if_100g_jig": 0.1 * 0.9 * D.G0, "F_rms_N_if_50g_jig": 0.05 * 0.9 * D.G0}
    lra["G_rms_in_pencil_100g"] = lra["F_rms_N_if_100g_jig"] / M_pen / D.G0
    lra["G_rms_in_pencil_50g"] = lra["F_rms_N_if_50g_jig"] / M_pen / D.G0
    haptic = {"stage_200Hz": hap, "lra_6mm": lra, "threshold_m_s2_at_200Hz": thr, "pen_mass_g": M_pen * 1e3,
              "labels": {"stage": CALC + " (momentum balance, free pen; skin impedance ~1 N s/m at 200 Hz, HAP-27, neglected)",
                         "threshold": "LITERATURE (HAP-27)", "lra": ms("AMF-45") + "; jig mass ASSUMPTION 50-100 g"},
              "note": "on paper the burst wiggles the ink by its nib amplitude: use >= 100 um only pen-up, ~20 um in contact"}
    return {"key": key, "stage": st.summary(), "beam": beam, "leaves": leafs,
            "lever_sweep": lev, "optimum_lever_betaworst": st.optimum_lever(F_nom),
            "load_line_grid": load_line, "fraction_of_grid_with_300um": len(ok) / len(load_line),
            "resonance": reson, "sensor": hall, "stops": stops, "drop": drop, "drive": drive, "haptic": haptic}


# ======================================================================================
# (d) MAKE / BUY and development steps
# ======================================================================================
def make_buy():
    return [
        {"item": "D1 low-force refills (gel, rollerball, fineliner inserts)", "decision": "buy", "note": "select by EXP-Q02"},
        {"item": "PICMA PL128.10 benders", "decision": "buy", "note": "1-axis bench stage and characterisation (AMF-11)"},
        {"item": "Custom 2.6 x 36 x 0.67 mm multilayer benders (4 per pen)", "decision": "make (supplier custom part)", "note": "request quotes for diced custom widths incl. edge finish; EXP-Q04"},
        {"item": "Decoupling leaves (C17200 30 um, 1.2 x 5 mm free span)", "decision": "make (photo-etch service)", "note": "AMF-18/19"},
        {"item": "Collar, gimbal (etched cross-strip), PTFE-lined bushings, skid ring (POM-PTFE)", "decision": "make", "note": "precision machining/etching"},
        {"item": "Barrel (PA-GF30 moulding over a stainless chassis tube), nose with snubbers", "decision": "make", "note": "AMF-42 construction"},
        {"item": "Prototype piezo driver: 2 x DRV2700 EVM", "decision": "buy", "note": "AMF-16"},
        {"item": "Product piezo driver: shared LT8330-class boost + charge-recovery half-bridges", "decision": "make (custom power stage from catalogue parts)", "note": "proposed AMF-47; or a qualified CapDrive part (proposed AMF-46)"},
        {"item": "3-D Hall sensor + 0.6 x 1 x 1 mm NdFeB magnet", "decision": "buy", "note": "part selection open (TMAG5170/TLE493D class)"},
        {"item": "nRF54L15 CSP, IMU, optical sensor, rigid-flex board", "decision": "buy parts / make board", "note": "AMF-44; board layout make"},
        {"item": "6.5 x 40 mm Li-ion cell (~90 mAh) / 3 x CG-425A fallback", "decision": "make (custom cell) / buy (fallback)", "note": "AMF-43; EXP-Q03"},
        {"item": "Firmware: piezo servo with integral action, hysteresis model, estimators, safety", "decision": "make", "note": "port the Rev A core (firmware/)"},
    ]


def dev_steps():
    return [
        {"step": 1, "what": "Skid friction and feel", "experiments": ["EXP-Q01 skid friction coefficient (bench: POM-PTFE/PTFE/sapphire on 3 papers, N 0.2-2 N, 1-100 mm/s)",
                                                                       "EXP-H03 skid feel and smear (existing blinded study, DEC-008)"], "gates": "mu_skid, skid acceptability"},
        {"step": 2, "what": "Low-force ink", "experiments": ["EXP-Q02 low-force ink line quality (line width, skips vs nib force 0.05-0.5 N)"], "gates": "nib spring force F_c"},
        {"step": 3, "what": "Bender characterisation", "experiments": ["EXP-Q04 bender characterisation and strength (stroke, blocking force, hysteresis for the Bouc-Wen fit, large-signal capacitance, leakage; tip-load-to-failure on diced custom plates; drop with and without snubbers)"], "gates": "stroke/force tolerance, sigma0 and m of the plate ceramic"},
        {"step": 4, "what": "Drive electronics", "experiments": ["EXP-Q05 piezo driver efficiency and quiescent power (DRV2700 vs charge-recovery stage on 2-2.6 uF, 4-12 Hz and 200 Hz bursts)", "EXP-Q03 cell pulse discharge"], "gates": "driver topology, battery life"},
        {"step": 5, "what": "One-axis loaded bench stage", "experiments": ["EXP-Q06 PL128.10 + D1 refill + skid nose on the stage-A rig: stroke under load vs theta and mu, leaf cross-stiffness, bushing friction, first resonance, closed-loop tracking, cancellation with injected disturbance (EXP-B09 protocol)"], "gates": "stage model, controller"},
        {"step": 6, "what": "Two-axis Q stage in a 7.9 mm bore demonstrator", "experiments": ["EXP-Q07 two-axis stage FRF, cross-coupling and stops (EXP-B05 protocol)", "EXP-Q04 drop repeat on the assembly"], "gates": "Rev P1 freeze"},
        {"step": 7, "what": "Separability and human studies", "experiments": ["EXP-H01/E01 (tremor separability, decisive for free-writing assist)", "EXP-H02 form factor", "EXP-H06 crossover"], "gates": "claims"},
    ]


def proposed_ledger_rows():
    base = {"access_level": "full text", "participants_or_bench": "not applicable (manufacturer data; test method not published)",
            "transferability": "medium", "retrieved": "2026-09-27", "stream": "AMF", "lead_verification": ""}
    rows = [
        dict(base, id="AMF-46", topic="Piezo driver with energy recovery (Boreas BOS1921/BOS1931 CapDrive)",
             citation="Boreas Technologies. BOS1921/BOS1931 Piezo Haptic Driver with Digital Front End, Product Datasheet BT015DDS01.01 Issue 6 (2024).",
             year="2024", doi_or_url="https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6662/2158_BOS19_Datasheet.pdf",
             source_type="datasheet", evidence_class="manufacturer statement", task_or_setup="Recommended operating conditions; electrical characteristics",
             comparator="DRV2700 (AMF-16)",
             key_quantitative_findings="Supply 3.0-5.5 V; full-scale output 190 Vpk-pk (186-194); energy recovery; load capacitance max 100 nF at 190 Vpp/300 Hz, 470 nF at 100 Vpp/220 Hz, 820 nF at 100 Vpp/130 Hz; output frequency 3.9-1000 Hz; VBUS quiescent 0.6 uA SLEEP (no retention), 2.4 uA SLEEP (retention), 530 uA IDLE; average VBUS current 3.7 mA with DC output 95 V on 100 nF, 90 mA at 190 Vpp/300 Hz/100 nF; start-up < 300 us; QFN 4 x 4 mm or WLCSP 2.1 x 1.7 mm.",
             units_and_conditions="TA 25 degC, VBUS 3.6 V", locator="Table 5 (p. 5), Table 6 (p. 6)",
             limitations="Rated load (<= 820 nF) is below a bender stage's 2.0-2.6 uF per axis; DC holding current 3.7 mA (95 V, 100 nF) is not negligible.",
             relevance_to_design="Existence proof of an integrated charge-recovery piezo driver for a 1S cell.",
             transferability_reason="Haptic part; capacitance and waveform range differ from a low-frequency bender stage.",
             design_implication="Use as the reference topology for the product driver; qualify with the vendor at 2-2.6 uF, 60 Vpp, <= 250 Hz, or build a discrete charge-recovery stage (EXP-Q05).",
             search_query="WebSearch: Boreas BOS1901 piezo driver energy recovery capacitive load quiescent current datasheet; WebFetch DigiKey PDF"),
        dict(base, id="AMF-47", topic="Low-Iq 60 V boost converter for a 1S piezo rail (Analog Devices LT8330)",
             citation="Analog Devices. LT8330 Low IQ Boost/SEPIC/Inverting Converter with 1A, 60V Switch, datasheet (via radiolocman.com mirror).",
             year="n.d.", doi_or_url="https://www.radiolocman.com/datasheet/data.html?di=372321",
             source_type="datasheet", evidence_class="manufacturer statement", access_level="secondary account",
             task_or_setup="Features list", comparator="DRV2700 integrated boost (AMF-16)",
             key_quantitative_findings="60 V, 1 A switch (1.2 A switch current); input 3-40 V; Burst Mode quiescent current 6 uA; shutdown 0.9 uA; fixed 2 MHz; output ripple < 15 mV; ThinSOT-6 or 3 x 2 mm DFN-8; output up to 60 V.",
             units_and_conditions="Datasheet features; efficiency at 1-50 mW load not retrieved", locator="Features (mirror page)",
             limitations="analog.com returned HTTP 503; values from a mirror; 60 V switch leaves no margin for a 60 V rail (use about 55 V).",
             relevance_to_design="Shared rail for both piezo axes at micro-watt quiescent power.",
             transferability_reason="Input range matches a 1S cell; efficiency at our light load to be measured.",
             design_implication="Product piezo rail at about 55 V (stroke and force x 0.92) with charge-recovery half-bridges; EXP-Q05.",
             search_query="WebSearch: LT8330 60V boost converter quiescent current Burst Mode datasheet; WebFetch radiolocman"),
        dict(base, id="AMF-48", topic="Strength of poled multilayer PZT (4-point bending, Weibull)",
             citation="Bermejo R., Deluca M. Mechanical Characterization of PZT Ceramics for Multilayer Piezoelectric Actuators. J. Ceram. Sci. Tech. 3(4):159-168 (2012). doi:10.4416/JCST2012-00025",
             year="2012", doi_or_url="https://www.ceramic-science.com/php/article_pdf.php?article_id=100203",
             source_type="journal", evidence_class="physical bench experiment", participants_or_bench="30 specimens per sample, 35 x 3.0 x 2.25 mm, 4PB spans 30/15 mm, 1.5 mm/min",
             task_or_setup="4-point bending of bulk and multilayer PZT (injection-actuator material)", comparator="bulk non-poled and multilayer non-poled",
             key_quantitative_findings="Characteristic strength (elastic / outer-fibre corrected) and Weibull modulus: bulk non-poled 114 (112-116) / 80 MPa, m 20; multilayer non-poled 113 / 80 MPa, m 21; multilayer poled 124 (119-129) / 74 (71-77) MPa, m 8 (6-9). K_Ic 1.1 (bulk) and 1.5 (multilayer) MPa m^0.5 (SEVNB).",
             units_and_conditions="25 degC, 25 % RH, 90 % confidence intervals", locator="Table 1 (p. 163)",
             limitations="Fuel-injection actuator PZT, not PICMA; thick bars (2.25 mm) vs 0.67 mm plates; diced edges of custom plates not represented; no fatigue data.",
             relevance_to_design="Only quantitative strength source for multilayer PZT in the ledger; sets the bender stress allowable.",
             transferability="medium", transferability_reason="Same material class and poled multilayer construction; size and edge condition differ (Weibull scaling applied).",
             design_implication="Plate stress allowable from sigma0 124 MPa scaled to the plate's effective volume (about 181 MPa), m 8; confirm on diced custom plates (EXP-Q04).",
             search_query="WebSearch: multilayer PZT piezoelectric bender flexural strength MPa Weibull; WebFetch ceramic-science.com PDF"),
    ]
    return rows


# ======================================================================================
# FIGURES
# ======================================================================================
def figures(L, cands, sc, P, vcm_sw):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    S = plotstyle.SERIES
    # 1. transverse nib load vs tilt
    th = np.linspace(35, 75, 81)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    conv = [D.load_extremes("pen", 1.0, t * D2R, 0.15)["R_perp_max"] for t in th]
    ax.plot(th, conv, color=S[1], label="conventional nib, N = 1 N, μ 0.15")
    for i, Fc in enumerate((0.30, 0.15, 0.08)):
        y = [D.load_extremes("skid", Fc, t * D2R, 0.15)["R_perp_max"] for t in th]
        y0 = [Fc / math.tan(t * D2R) for t in th]
        ax.plot(th, y, color=S[[0, 2, 3][i]], label=f"skid, spring F_c = {Fc:.2f} N, μ 0.15 (worst stroke direction)")
        ax.plot(th, y0, color=S[[0, 2, 3][i]], lw=1.0, ls="--")
    for key, c in (("Q26", S[4]), ("L35", S[5])):
        stg = D.stage(key)
        ax.axhline(stg.F_b_nib, color=c, lw=1.2, ls=":")
        ax.text(75, stg.F_b_nib + 0.012, f"{key} blocking force at nib {stg.F_b_nib:.2f} N", ha="right", fontsize=7.5, color=plotstyle.INK2)
    ax.set_xlabel("Pen altitude θ (deg)")
    ax.set_ylabel("Transverse load at the nib per stage axis (N)")
    ax.set_title("Load the nib stage must hold: skid cuts it 3-10x (dashed: friction neglected, F_c cot θ)", loc="left", fontsize=9.5)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=7.2, loc="upper right")
    plotstyle.stamp(fig, "calculation", "P-5/P-6 with axial spring balance; AMF-11 forces; not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_loads_vs_tilt.png")); plt.close(fig)
    # 2. stroke under load vs tilt
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for key, c in (("PL128", S[1]), ("L40", S[3]), ("L35", S[5]), ("Q26", S[0])):
        stg = D.stage(key)
        y = [stg.stroke_under_load(D.load_extremes("skid", 0.15, t * D2R, 0.15)["R_perp_max"]) * 1e3 for t in th]
        lbl = {"PL128": "PL128.10 (one axis only)", "L40": "4.0 mm L pair (does not fit)", "L35": "3.5 mm L pair", "Q26": "2.6 mm quad (push-pull)"}[key]
        ax.plot(th, np.minimum(y, 0.40), color=c, label=lbl)
    stt = D.stage("Q26", tol=-0.2)
    ax.plot(th, [min(stt.stroke_under_load(D.load_extremes("skid", 0.15, t * D2R, 0.15)["R_perp_max"]) * 1e3, 0.4) for t in th],
            color=S[0], lw=1.2, ls="--", label="2.6 mm quad at -20 % tolerance")
    ax.axhline(0.30, color=plotstyle.MUTED, lw=1.0)
    ax.text(35.5, 0.307, "target ±0.30 mm usable", fontsize=7.5, color=plotstyle.INK2)
    ax.set_xlabel("Pen altitude θ (deg)")
    ax.set_ylabel("Symmetric nib stroke under load (mm)")
    ax.set_title("Stroke left after holding the load (F_c 0.15 N, μ 0.15, worst direction)", loc="left", fontsize=9.5)
    ax.set_ylim(0, 0.45)
    ax.legend(fontsize=7.5, loc="lower right")
    plotstyle.stamp(fig, "calculation", "AMF-11 +/-20 %; lever 1.38 from CAD; not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_stroke_under_load.png")); plt.close(fig)
    # 3. cross sections
    fig, axs = plt.subplots(1, 4, figsize=(8.8, 2.6))
    for ax, key, title in zip(axs, ("PL128", "L40", "L35", "Q26"), ("PL128.10 (1 axis)", "4.0 mm L", "3.5 mm L", "2.6 mm quad")):
        circ = plt.Circle((0, 0), 3.95, fill=False, color=plotstyle.INK2, lw=1.2)
        ax.add_patch(circ)
        ref_c = (0.0, 1.06) if key == "PL128" else (0.0, 0.0)
        ax.add_patch(plt.Circle(ref_c, 1.175, color=S[2], alpha=0.5))
        for (x0, x1, y0, y1) in _plate_rects(key):
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, color=S[0], alpha=0.35))
        ax.set_xlim(-4.3, 4.3); ax.set_ylim(-4.3, 4.3); ax.set_aspect("equal")
        ax.set_title(title, fontsize=9); ax.tick_params(labelsize=7)
        ax.grid(False)
    axs[0].set_ylabel("mm")
    fig.suptitle("Plates swept ±0.40 mm (blue) and refill (green) in the 7.9 mm bore", fontsize=9.5, x=0.01, ha="left")
    plotstyle.stamp(fig, "cad check (proposed design)", "layout from mechanics/cad/pencil_revP.py")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_cross_sections.png")); plt.close(fig)
    # 4. drop stress
    dr = sc["drop"]["transverse"]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    x = [r["pulse_ms"] for r in dr]
    ax.plot(x, [r["no_snubbers_MPa"] for r in dr], color=S[1], label="plate clamped at root, tip on collar stop", **plotstyle.marker_kw(S[1]) | {"linestyle": "-"})
    ax.plot(x, [r["two_snubbers_MPa"] for r in dr], color=S[0], label="plus two snubbers along the plate", **plotstyle.marker_kw(S[0]) | {"linestyle": "-"})
    ax.plot(x, [r["four_snubbers_MPa"] for r in dr], color=S[2], label="plus four snubbers", **plotstyle.marker_kw(S[2]) | {"linestyle": "-"})
    s0 = sc["stops"]["sigma0_bender_MPa"]
    ax.axhline(s0, color=plotstyle.MUTED, lw=1.0)
    ax.text(x[-1], s0 * 1.05, f"characteristic strength ~{s0:.0f} MPa (Weibull-scaled)", ha="right", fontsize=7.5, color=plotstyle.INK2)
    ax.axhline(sc["stops"]["blocking_rated_MPa"], color=plotstyle.MUTED, lw=1.0, ls="--")
    ax.text(x[-1], sc["stops"]["blocking_rated_MPa"] * 1.06, "rated blocking-force stress", ha="right", fontsize=7.5, color=plotstyle.INK2)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Impact pulse duration (ms), 1 m drop, Δv 6.2 m/s transverse")
    ax.set_ylabel("Peak plate bending stress (MPa)")
    ax.set_title("2.6 mm plate in a sideways 1 m drop: stops alone do not protect the ceramic", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="lower left")
    plotstyle.stamp(fig, "simulation", "FE beam, assumed pulse and damping; strength from proposed AMF-48; not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_drop_stress.png")); plt.close(fig)
    # 5. drive power vs frequency
    rows = [r for r in sc["drive"]["rows"] if r["nib_amp_mm"] == 0.3]
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.5))
    f = [r["f_Hz"] for r in rows]
    for dk, c in zip(PW.DRIVERS, (S[1], S[0], S[3])):
        axs[0].plot(f, [r[dk]["P_battery_mW"] for r in rows], color=c, label=PW.DRIVERS[dk]["label"].split("(")[0].strip()[:40],
                    **plotstyle.marker_kw(c) | {"linestyle": "-"})
    axs[0].set_xlabel("Tremor frequency (Hz)"); axs[0].set_ylabel("Driver battery power, 2 axes (mW)")
    axs[0].set_title("Stage drive at 0.3 mm (0.12 mm minor axis)", loc="left", fontsize=9)
    axs[0].legend(fontsize=6.8)
    modes = sc["drive"]["modes_analytic"]
    labels = list(PW.DRIVERS)
    xb = np.arange(len(labels))
    axs[1].bar(xb - 0.18, [modes[k]["life_recording_h"] for k in labels], 0.36, color=S[2], label="recording only")
    axs[1].bar(xb + 0.18, [modes[k]["life_tremor_assist_h"] for k in labels], 0.36, color=S[0], label="tremor assist 6 Hz 0.3 mm")
    axs[1].set_xticks(xb); axs[1].set_xticklabels(["2 x DRV2700", "boost + recovery", "CapDrive class"], fontsize=7.5)
    axs[1].set_ylabel("Battery life, 90 mAh (h)"); axs[1].set_title("Runtime per charge", loc="left", fontsize=9)
    axs[1].set_ylim(0, 5.2)
    axs[1].legend(fontsize=7, loc="upper right", ncol=2)
    plotstyle.stamp(fig, "calculation", "AMF-16, proposed AMF-46/47; electronics 65 mW placeholder; not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_drive_power_battery.png")); plt.close(fig)
    # 6. VCM
    ok = [r for r in vcm_sw["rows"] if r["fits"]]
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    for i, (tc, tm) in enumerate(((0.55, 1.2), (1.0, 1.2), (0.55, 2.0), (1.0, 2.0))):
        rr = sorted([r for r in ok if abs(r["t_c_mm"] - tc) < 1e-6 and abs(r["t_m_mm"] - tm) < 1e-6], key=lambda r: r["n"])
        if not rr:
            continue
        F = L["nominal"]["skid"]["R_perp_max_N"]["value"]
        ax.plot([r["n"] for r in rr], [(F / (r["n"] * r["Km_min"])) ** 2 for r in rr], color=S[i],
                label=f"coil {tc} mm/layer, magnet {tm} mm", **plotstyle.marker_kw(S[i]) | {"linestyle": "-"})
    ax.axhline(0.15, color=plotstyle.MUTED, lw=1.0)
    ax.text(1.0, 0.16, "0.15 W: 1-2 h per charge (AMF-42)", fontsize=7.5, color=plotstyle.INK2)
    ax.set_yscale("log")
    ax.set_xlabel("Lever ratio n (front pivot)"); ax.set_ylabel("Copper loss to hold 0.17 N at the nib (W)")
    ax.set_title("Moving-magnet voice coil in the 7.9 mm bore, even behind a skid", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.2)
    plotstyle.stamp(fig, "simulation", "magpylib, image iron (upper bound); not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_vcm_holding_power.png")); plt.close(fig)


# ======================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="reuse the cached magpylib sweep")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    P = D.Params()
    L = loads(P)
    hall = hall_sensitivity()
    vsw = vcm_sweep(fast=a.fast)
    vcm = vcm_candidate(vsw, L)
    sc = stage_check("Q26", L, P, hall)
    scL = stage_check("L35", L, P, hall)
    drop_summary = {}
    for key, s in (("Q26", sc), ("L35", scL)):
        worst = max(s["drop"]["transverse"], key=lambda r: r["no_snubbers_MPa"])
        best_sn = max(s["drop"]["transverse"], key=lambda r: r["two_snubbers_MPa"])
        r2 = next(r for r in s["drop"]["transverse"] if abs(r["pulse_ms"] - 2.0) < 1e-9)
        drop_summary[key] = ("stops alone: %.0f-%.0f MPa peak in a 1 m sideways drop (P_fail up to %.2f); with four snubbers and a 2 ms "
                             "(compliant-nose) pulse %.0f MPa (P_fail %.1e); pushed onto a stop while driven the other way %.0f MPa"
                             % (min(r["no_snubbers_MPa"] for r in s["drop"]["transverse"]), worst["no_snubbers_MPa"], worst["P_fail_no_snubbers"],
                                r2["four_snubbers_MPa"], r2["P_fail_four_snubbers"], s["stops"]["driven_opposite_at_stop_MPa"]))
    drop_summary["PL128"] = "as L35 per unit width (same free length and thickness); single plate"
    drop_summary["L40"] = "as L35"
    cands = [piezo_candidate(k, L, hall, drop_summary, P) for k in ("PL128", "L40", "L35", "Q26")]
    verdicts = {"PL128": "bench part: off the shelf, one axis only; use for the 1-axis loaded rig (EXP-Q06), not the product",
                "L40": "reject: does not fit the bore (CAD)",
                "L35": "second choice: fits, but %.0f um under the worst-direction nominal load and %.0f um at -20 %% tolerance"
                       % (cands[2]["stroke_nib_um"][[k for k in cands[2]["stroke_nib_um"] if k.startswith("at_F_beta")][0]],
                          cands[2]["stroke_nib_um"]["betaworst_at_minus20pct_tolerance"]),
                "Q26": "RECOMMENDED: fits, zero holding power, %.0f um under the worst-direction nominal load (%.0f um frictionless), f1 %.0f Hz"
                       % (cands[3]["stroke_nib_um"][[k for k in cands[3]["stroke_nib_um"] if k.startswith("at_F_beta")][0]],
                          cands[3]["stroke_nib_um"][[k for k in cands[3]["stroke_nib_um"] if k.startswith("at_F_fric")][0]],
                          cands[3]["first_resonance_Hz"])}
    for c in cands:
        c["verdict"] = verdicts[c["key"]]
    cands += other_candidates(L, vcm, P)
    xs = cross_sections()
    figures(L, cands, sc, P, vsw)
    rows = proposed_ledger_rows()
    with open(os.path.join(OUT, "proposed_evidence_rows.csv"), "w", newline="") as f:
        cols = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
                "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
                "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
                "stream", "lead_verification"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    meta = provenance.metadata("calculation and simulation (analytical, magpylib, FE); nothing measured", p=P.pencil,
                               extra={"parameters_base_version": P.base.version(), "script": "analysis/pencil_mechanisms.py",
                                      "elapsed_s": round(time.time() - t0, 1), "vcm_sweep_elapsed_s": vsw.get("elapsed_s")})
    out = {"meta": meta,
           "labels_legend": {"CALCULATION": "analytical from labelled inputs", "SIMULATION": "numerical model",
                             "MANUFACTURER STATEMENT (id)": "ledger row", "LITERATURE (id)": "ledger row",
                             "CAD (proposed design)": "mechanics/cad/pencil_revP.py", "ASSUMPTION": "stated with range and the experiment that measures it"},
           "a_loads": L, "b_candidates": cands, "b_cross_sections": xs, "b_vcm_sweep": vsw,
           "c_stage_check_Q26": sc, "c_stage_check_L35": scL,
           "d_make_buy": make_buy(), "d_development_steps": dev_steps(),
           "proposed_ledger_rows": [r["id"] for r in rows]}
    provenance.write_json(os.path.join(OUT, "mechanisms.json"), r4(out))
    # console summary
    n = L["nominal"]
    print(f"conventional R_perp max {n['conventional_pen']['R_perp_max_N']['value']:.3f} N; skid F_c cot th {n['skid']['R_perp_frictionless_N']['value']:.3f} N, "
          f"worst beta {n['skid']['R_perp_max_N']['value']:.3f} N; N_skid {n['skid']['N_skid_N']['value']:.3f} N")
    for c in cands:
        print(f"  {c['key']:9s} {c.get('verdict','')}")
    print("VCM best", {k: round(v, 3) if isinstance(v, float) else v for k, v in vcm["best_design"].items()}, "P_hold skid", round(vcm["P_hold_skid_betaworst_W"], 2), "W")
    print("resonance Q26", sc["resonance"], "\nstops", sc["stops"])
    for r in sc["drop"]["transverse"]:
        print("  drop", {k: round(v, 4) for k, v in r.items()})
    print("modes", json.dumps(r4(sc["drive"]["modes_analytic"]), indent=0)[:600])
    print("haptic", r4(sc["haptic"]["stage_200Hz"]), r4(sc["haptic"]["lra_6mm"]))
    print("hall", r4(hall))
    print("elapsed", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
