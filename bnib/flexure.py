r"""Flexures of the candidate nibs: stiffness, full-travel strain with stress concentrations, Goodman fatigue at 43.2
million cycles, buckling, loaded eigenmodes with geometric stiffness and magnetic stiffness, tolerances (CALC; beam
theory, no FEM of the real parts).

Translation stage (candidates b-g): n_w wires parallel to the pen axis, fixed at a front anchor ring and at the carrier
(fixed-guided), in the manner of optical-pickup lens suspensions (the wires also carry the moving coils' currents).
  lateral stiffness per wire under axial tension P:  k = P alpha / (alpha L - 2 tanh(alpha L / 2)),  alpha^2 = P / EI
      (-> 12 EI / L^3 for P -> 0; -> P / L for a string); under compression the same with tan (sidesway buckling at
      P = pi^2 EI / L^2);
  root bending moment M = F tanh(alpha L / 2) / alpha  (F = k delta; -> F L / 2 = 6 EI delta / L^2 for P -> 0)
      -> bending strain d M / (2 EI), times the clamp stress-concentration factor Kt;
  axial k_ax = n_w E A / L; tilt k_tilt = (n_w / 2) (E A / L) r_w^2 (wires on a circle of radius r_w);
  wire violin mode (fixed-fixed) f = (4.730^2 / (2 pi L^2)) sqrt(EI / (rho A)), with tension added in quadrature
      (f_string = sqrt(P / (rho A)) / (2 L)).
Gimbal (candidate a): revj1.gimbal (co-rotational beam model of the cross-strip pivot, imported read-only) for the
stiffness under the magnet pull, the strain at full travel and the buckling load.
Fatigue: fully reversed full-travel bending (the stop, not the usable travel) x Kt against the listed fatigue strength
x a size/surface knock-down, Goodman with the tensile mean stress; safety factor reported (target >= 1.5).
Loaded eigenmodes: a planar beam model of the refill (Euler-Bernoulli elements with the compressive ink force's
geometric stiffness) joined to the rigid carrier at two bushings, the carrier on the suspension, the ball on the paper
(normal penalty and tangential pre-sliding stiffness mu N / x_pre while stuck) and the counter-face at the rear end.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Dict, List, Optional

import numpy as np

from .labels import FAT, FLEX, FRICTION, val


# ------------------------------------------------------------------------------------------------ wire stage
@dataclass(frozen=True)
class WireStage:
    n_w: int = 4
    d: float = 0.20e-3            # wire diameter
    L: float = 18e-3              # free length
    r_w: float = 5.5e-3           # radius of the wire circle
    mat: str = "C17200_TH04"      # non-magnetic near the magnets (BeCu or Ti-6Al-4V)
    Kt: float = 1.8               # clamp stress concentration (labels.FAT)
    P_axial: float = 0.0          # N total axial tension (+) on the stage in service

    @property
    def E(self):
        return FLEX[self.mat]["E"]

    @property
    def I(self):
        return math.pi * self.d ** 4 / 64.0

    @property
    def A(self):
        return math.pi * self.d ** 2 / 4.0


def k_wire_lateral(E: float, I: float, L: float, P: float) -> float:
    """Lateral stiffness of one fixed-guided wire under axial force P (tension +), N/m (CALC)."""
    if abs(P) < 1e-9:
        return 12.0 * E * I / L ** 3
    if P > 0:
        al = math.sqrt(P / (E * I))
        x = al * L
        if x < 1e-3:
            return 12.0 * E * I / L ** 3
        return P * al / (x - 2.0 * math.tanh(0.5 * x))
    be = math.sqrt(-P / (E * I))
    x = be * L
    if x >= math.pi - 1e-9:
        return -1e9                                      # buckled (sidesway)
    return -P * be / (2.0 * math.tan(0.5 * x) - x)


def root_moment(F: float, E: float, I: float, L: float, P: float) -> float:
    if abs(P) < 1e-9:
        return F * L / 2.0
    if P > 0:
        al = math.sqrt(P / (E * I))
        return F * math.tanh(0.5 * al * L) / al
    be = math.sqrt(-P / (E * I))
    return F * math.tan(0.5 * be * L) / be


def wire_stage(ws: WireStage, travel: float, stop: float, m_moving: float, I_carrier: float = 2e-8) -> Dict:
    """Stiffness, strain, fatigue, buckling and modes of the wire suspension (CALC)."""
    mat = FLEX[ws.mat]
    E, I, A, L = ws.E, ws.I, ws.A, ws.L
    Pw = ws.P_axial / ws.n_w
    kw = k_wire_lateral(E, I, L, Pw)
    k_lat = ws.n_w * kw
    k_ax = ws.n_w * E * A / L
    k_tilt = 0.5 * ws.n_w * E * A / L * ws.r_w ** 2
    out = {"k_lat_N_m": k_lat, "k_axial_N_um": k_ax * 1e-6, "k_tilt_Nm_rad": k_tilt}
    for key, dl in (("usable", travel), ("stop", stop)):
        F = kw * dl
        M = root_moment(F, E, I, L, Pw)
        eps = M * (ws.d / 2) / (E * I)
        out[f"strain_{key}"] = eps
        out[f"stress_{key}_MPa"] = eps * E * ws.Kt / 1e6
    sig_a = out["stress_stop_MPa"] * 1e6
    sig_m = max(Pw / A, 0.0)
    S_f = mat["S_f"] * val(FAT["size_surface"])
    out["goodman_SF"] = 1.0 / (sig_a / S_f + sig_m / mat["S_u"])
    out["static_SF_stop"] = mat["S_y"] / (sig_a + abs(Pw) / A)
    out["P_buckle_N"] = ws.n_w * math.pi ** 2 * E * I / L ** 2            # sidesway, all wires together
    rho = mat["rho"]
    f_b = 4.730 ** 2 / (2 * math.pi * L ** 2) * math.sqrt(E * I / (rho * A))
    f_s = math.sqrt(max(Pw, 0.0) / (rho * A)) / (2 * L)
    out["f_violin_Hz"] = math.sqrt(f_b ** 2 + f_s ** 2)
    out["f_suspension_Hz"] = math.sqrt(max(k_lat, 1e-9) / m_moving) / (2 * math.pi)
    out["f_axial_Hz"] = math.sqrt(k_ax / m_moving) / (2 * math.pi)
    out["f_tilt_Hz"] = math.sqrt(k_tilt / I_carrier) / (2 * math.pi)
    out["mass_g"] = ws.n_w * rho * A * L * 1e3
    out["magnetic"] = mat["magnetic"]
    out["material_source"] = mat["src"]
    return out


def shock(ws: WireStage, m_carrier: float, stop_axial: float = 20e-6, stop_lat: float = 1.2e-3,
          g_levels=(100.0, 500.0, 2000.0)) -> Dict:
    """Drops (CALC): axial -- the carrier's inertia m a in the wires until an axial stop engages after stop_axial of
    wire stretch/shortening; lateral -- the carrier on its lateral stop (strain from stop_lat, listed in wire_stage).
    A buckled wire stays elastic if the stop limits its end shortening (Rev J.1's rule for strips)."""
    E, A, L, I = ws.E, ws.A, ws.L, ws.I
    k_ax = ws.n_w * E * A / L
    rows = []
    for g in g_levels:
        F = m_carrier * 9.81 * g
        d = F / k_ax
        stop_hit = d > stop_axial
        F_wires = min(F, k_ax * stop_axial)
        sig = F_wires / (ws.n_w * A)
        rows.append({"g": g, "F_N": F, "wire_stress_MPa": sig / 1e6, "stop_engaged": bool(stop_hit),
                     "buckles_in_compression": F_wires > ws.n_w * math.pi ** 2 * E * I / L ** 2})
    w0 = 2 / math.pi * math.sqrt(L * stop_axial)
    eps_b = ws.d / 2 * (2 * math.pi / L) ** 2 * w0 / 2
    return {"rows": rows, "k_axial_N_um": k_ax * 1e-6, "stop_axial_um": stop_axial * 1e6,
            "buckled_strain_at_stop": eps_b, "buckled_elastic": eps_b * E < FLEX[ws.mat]["S_y"],
            "label": "CALC (drop loads; stop gaps PROPOSED DESIGN)"}


def tolerance_mc(ws: WireStage, travel: float, stop: float, m_moving: float, n: int = 2000, seed: int = 7) -> Dict:
    """Monte Carlo of the manufacturing spread (ASSUMPTION tolerances): wire diameter +-2 % (1 sigma), free length
    +-0.05 mm, modulus +-4 %, Kt 1.3-2.5 uniform, axial preload 0-0.3 N from assembly."""
    rng = np.random.default_rng(seed)
    ks, sfs, fs = [], [], []
    for _ in range(n):
        w2 = replace(ws, d=ws.d * (1 + 0.02 * rng.standard_normal()), L=ws.L + 0.05e-3 * rng.standard_normal(),
                     Kt=rng.uniform(1.3, 2.5), P_axial=ws.P_axial + rng.uniform(0.0, 0.3))
        r = wire_stage(w2, travel, stop, m_moving)
        kE = 1 + 0.04 * rng.standard_normal()
        ks.append(r["k_lat_N_m"] * kE)
        sfs.append(r["goodman_SF"] / kE)
        fs.append(r["f_suspension_Hz"] * math.sqrt(kE))
    ks, sfs, fs = map(np.array, (ks, sfs, fs))
    return {"k_lat_p5_p50_p95": np.percentile(ks, [5, 50, 95]).tolist(),
            "goodman_SF_p1_p5_p50": np.percentile(sfs, [1, 5, 50]).tolist(),
            "f_susp_p5_p95": np.percentile(fs, [5, 95]).tolist(), "n": n,
            "label": "CALC (Monte Carlo; tolerances ASSUMPTION)"}


# ------------------------------------------------------------------------------------------------ gimbal (revj1)
_PB_CACHE: Dict = {}


def _buckling(t, b, L, n):
    """revj1.gimbal.buckling_load depends only on the strip (cached: it dominates the optimiser's cost)."""
    key = (round(t, 12), round(b, 12), round(L, 12), n)
    if key not in _PB_CACHE:
        from revj1 import gimbal as G
        _PB_CACHE[key] = G.buckling_load(G.Strip(t=t, b=b, L=L), n=n)
    return _PB_CACHE[key]


def gimbal_check(t: float = 75e-6, b: float = 2.55e-3, L: float = 3.8e-3, F_pull: float = 0.0, alpha_usable: float = 0.013,
                 alpha_stop: float = 0.017, n: int = 12) -> Dict:
    """revj1.gimbal's co-rotational cross-strip model for a small-travel gimbal (CALC, imported read-only)."""
    from revj1 import gimbal as G
    s = G.Strip(t=t, b=b, L=L)
    cp = G.CrossPivot(s, n)
    k0 = cp.stiffness(-F_pull)
    e_u = cp.peak_strain(-F_pull, alpha_usable)["bending_strain"]
    e_s = cp.peak_strain(-F_pull, alpha_stop)["bending_strain"]
    Pb = _buckling(t, b, L, n)
    sig_a = e_s * s.E * val(FAT["Kt_etched_strip"])
    S_f = G.FATIGUE_301FH * val(FAT["size_surface"])
    return {"k_rot_Nm_rad": k0, "strain_usable": e_u, "strain_stop": e_s, "buckling_N": Pb,
            "goodman_SF": 1.0 / (sig_a / S_f + max(-0.0, 0.0)), "label": "CALC (revj1.gimbal beam model, 301 FH, AMF-20)"}


# ------------------------------------------------------------------------------------------------ loaded eigenmodes
@dataclass
class RefillBeam:
    L: float = 70e-3              # ball to the rear end (refill + holder)
    EI: float = 0.166             # N m^2 (stainless tube 2.35/1.9 mm, E 193 GPa: ASSUMPTION for a metal refill tube)
    m_per_len: float = 0.019      # kg/m (1.34 g over 70 mm: refill 0.84 g + holder 0.5 g)
    n_el: int = 20


def _beam_mats(L, EI, mpl, n, P_comp):
    """Planar Euler-Bernoulli element matrices (w, w') with the geometric stiffness of an axial compression P."""
    le = L / n
    ke = EI / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                  [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
    kg = P_comp / (30 * le) * np.array([[36, 3 * le, -36, 3 * le], [3 * le, 4 * le ** 2, -3 * le, -le ** 2],
                                        [-36, -3 * le, 36, -3 * le], [3 * le, -le ** 2, -3 * le, 4 * le ** 2]])
    me = mpl * le / 420 * np.array([[156, 22 * le, 54, -13 * le], [22 * le, 4 * le ** 2, 13 * le, -3 * le ** 2],
                                    [54, 13 * le, 156, -22 * le], [-13 * le, -3 * le ** 2, -22 * le, 4 * le ** 2]])
    nd = 2 * (n + 1)
    K = np.zeros((nd, nd)); M = np.zeros((nd, nd))
    for e in range(n):
        i = 2 * e
        K[i:i + 4, i:i + 4] += ke - kg
        M[i:i + 4, i:i + 4] += me
    return K, M


def loaded_modes(beam: RefillBeam, m_carrier: float, J_carrier: float, z_carrier: float, z_b1: float, z_b2: float,
                 k_susp: float, k_tilt: float, k_mag: float = 0.0, F_c: float = 0.15, k_ball_t: float = 0.0,
                 k_face_t: float = 0.0, k_bush: float = 5e5, n_modes: int = 5) -> Dict:
    """Lateral modes of carrier + refill (one lateral plane), ball free (k_ball_t = 0) or stuck on the paper (pre-sliding
    stiffness), with the ink force as a compressive geometric stiffness in the refill and the magnetic stiffness on the
    carrier (negative for a moving magnet; zero for a moving coil).  z measured from the ball (CALC)."""
    Kb, Mb = _beam_mats(beam.L, beam.EI, beam.m_per_len, beam.n_el, F_c)
    nb = Kb.shape[0]
    nd = nb + 2                                  # + carrier lateral x_c and rotation r_c (about its centre z_carrier)
    K = np.zeros((nd, nd)); M = np.zeros((nd, nd))
    K[:nb, :nb] = Kb; M[:nb, :nb] = Mb
    ic, ir = nb, nb + 1
    K[ic, ic] += k_susp - k_mag
    K[ir, ir] += k_tilt
    M[ic, ic] += m_carrier
    M[ir, ir] += J_carrier
    le = beam.L / beam.n_el

    def couple(z, k):
        # bushing: spring between the beam's lateral displacement at z (shape-function interpolation) and the carrier
        e = min(int(z / le), beam.n_el - 1)
        xi = (z - e * le) / le
        N = np.array([1 - 3 * xi ** 2 + 2 * xi ** 3, le * (xi - 2 * xi ** 2 + xi ** 3), 3 * xi ** 2 - 2 * xi ** 3,
                      le * (-xi ** 2 + xi ** 3)])
        g = np.zeros(nd)
        g[2 * e:2 * e + 4] = N
        g[ic] -= 1.0
        g[ir] -= (z - z_carrier)
        K[:, :] += k * np.outer(g, g)
    couple(z_b1, k_bush)
    couple(z_b2, k_bush)
    if k_ball_t > 0:
        K[0, 0] += k_ball_t
    if k_face_t != 0.0:
        K[nb - 2, nb - 2] += k_face_t
    from scipy.linalg import eigh
    w2, vec = eigh(K, M)
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * math.pi)
    return {"f_Hz": f[:n_modes].tolist(), "min_eig_stable": bool(w2.min() > -1e-6 * abs(w2).max()),
            "label": "CALC (planar beam + rigid carrier; bushings as stiff springs)"}


def stick_stiffness(F_c: float, theta: float) -> float:
    """Tangential pre-sliding stiffness of the ball on the paper while stuck: mu_s N / x_pre (H1 LuGre, ASSUMPTION)."""
    mu_s = 0.15 * val(FRICTION["ms_ratio"])
    N = F_c / math.sin(theta)
    return mu_s * N / val(FRICTION["presliding"])
