r"""Differentiable design model of the pencil nib stage (PyTorch).

The relations of sim/pencil/design.py (PICMA-class bender as a cantilever, decoupling leaf, lever from the
CAD geometry, reduction of the stage to the nib, skid contact loads, Weibull strength), of the stage check in
analysis/pencil_mechanisms.py (clamp stress at the stops, drive power with the sim/pencil/power.py conventions)
and the fit formulas of mechanics/cad/pencil_revP.py (section checks with the tips at the stops, snubber webs,
nose clearances) are re-expressed with torch tensors.  Reverse-mode automatic differentiation of this model is
the adjoint of the design model: one backward pass gives the exact gradient of any objective or constraint with
respect to all continuous design variables.  The functions are batched: every variable is a tensor of shape
(B,) and B designs are evaluated (and optimised) together.

Extensions beyond the existing model (each labelled):
  * plate thickness, free length, clamp length and ceramic are variables: custom plates scale from the PICMA
    reference part at fixed layer thickness and field (delta ~ LF^2/t, F ~ w t^2/LF, C ~ w L_el t; CALC,
    checked against the PICMA and CTS families in tests and AMF-63);
  * stacked plates (two per position acting in parallel: clamped together with a 0.05 mm spacer, tips not joined
    to each other, each plate driving the collar through its own half of a slit leaf; ASSUMPTION, EXP-Q04), a
    second-stage flexure lever (topology Q2L);
  * drive power: sinusoidal tremor tracking from the P1 oracle's stage velocity per grid case, plus the
    Hall-noise-driven servo activity from a closed-loop discrete-time model of the P1 servo (stationary
    covariance by a discrete Lyapunov equation), combined as E[max(dV,0)] of a Gaussian plus a sinusoid,
    plus a calibrated writing term (results/opt/p1_power_calibration.json);
  * mass from the CAD part list with the changed parts recomputed; battery capacity from the cell length;
  * drop stress from a response surface trained on the finite-element drop model (opt/hardware/drop_surrogate.py).
Evidence status: CALCULATION from labelled inputs (MFR with ledger ids, ASSUMPTION); the drop surrogate is
trained on SIMULATION.  Nothing here is a measurement.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

import torch

from . import OUT, ROOT
from . import catalogue as CAT
from sim.pencil import design as D  # noqa: E402

DT = torch.float64
D2R = math.pi / 180.0
MM = 1e-3
TWO_PI = 2.0 * math.pi

# ------------------------------------------------------------------------------------------------------------
# Fixed geometry of CAD P0.1.2 (mechanics/cad/pencil_revP.py; values checked against
# results/cad/pencil_revPQ_summary.json in the tests)
# ------------------------------------------------------------------------------------------------------------
FIX = dict(od=8.9e-3, wall=0.5e-3, nose_L=18e-3, skid_w=0.4e-3, theta_design=50.0, theta_min=35.0,
           refill_d=2.35e-3, refill_L=67e-3, cone_L=5e-3, ball_d=0.7e-3, socket_d=1.0e-3, collar_L=3e-3,
           collar_od=4e-3, snub_t=0.5e-3, snub_stations=(0.2, 0.4, 0.6, 0.8), snub_gap_extra=0.03e-3,
           clear_min=0.1e-3, web_min=0.2e-3, batt_d=6.5e-3, L_total=166e-3, cap_L=5e-3,
           hub_half=1.0e-3, hub_clear=0.5e-3, L_fixed_stack=126e-3, lever_len=3.0e-3)
# lever_len: axial room of the Q2L second-stage flexure lever between the collar leaves and the plate tips (ASSUMPTION)
# L_fixed_stack: refill 67 + spring 10 + 1 + board 42 + 1 + cap 5 = 126 mm (L_total = 126 mm + cell length)
R_BORE = FIX["od"] / 2 - FIX["wall"]
R_REFILL = FIX["refill_d"] / 2

# Moving parts of the nib assembly (CAD Q, mass g, com z mm); the collar group follows the collar, the hub the gimbal
_CADQ = os.path.join(ROOT, "results", "cad", "pencil_revPQ_summary.json")


def _cad_parts():
    try:
        d = json.load(open(_CADQ))
        return {r["part"]: (r["group"], r["mass_g"], r["com_z_mm"], r.get("volume_mm3")) for r in d["parts"]}, d["summary"]
    except (OSError, ValueError, KeyError):
        return None, None


CAD_PARTS, CAD_SUMMARY = _cad_parts()
COLLAR_GROUP = ("collar", "collar_liner", "collar_magnet")
BASE_MASS_G = 12.20 if CAD_SUMMARY is None else CAD_SUMMARY["mass_total_g"]
DENS = {"PZT": 7.80e-3, "Ti64": 4.43e-3, "Li": 2.6e-3, "PEEK": 1.30e-3, "C17200": 8.25e-3, "PA_GF30": 1.36e-3}  # g/mm^3 (CAD)
BARREL_G_PER_MM = math.pi * ((FIX["od"] / 2 / MM) ** 2 - (R_BORE / MM) ** 2) * DENS["PA_GF30"]


# ------------------------------------------------------------------------------------------------------------
# Design variables (SI) and options
# ------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Var:
    name: str
    lo: float
    hi: float
    unit: str
    desc: str


VARS = [
    Var("w", 1.5e-3, 4.5e-3, "m", "plate width (tangential)"),
    Var("t", 0.50e-3, 1.30e-3, "m", "plate thickness (layer count at the PICMA layer thickness)"),
    Var("Lf", 20e-3, 45e-3, "m", "plate free length"),
    Var("Lc", 3.5e-3, 10e-3, "m", "plate clamp length"),
    Var("d", 1.5e-3, 3.4e-3, "m", "plate mid-plane offset from the barrel axis"),
    Var("zg", 50e-3, 65.5e-3, "m", "rear gimbal position (from the ball centre)"),
    Var("zc0", 12e-3, 22e-3, "m", "collar front face position"),
    Var("leaf_t", 15e-6, 80e-6, "m", "decoupling-leaf thickness"),
    Var("leaf_w", 0.5e-3, 2.0e-3, "m", "decoupling-leaf width along the drive axis (radial)"),
    Var("leaf_L", 2e-3, 9e-3, "m", "decoupling-leaf free span"),
    Var("Fc", 0.08, 0.30, "N", "nib spring force (ASSUMPTION range; EXP-Q02)"),
    Var("r_ring", 1.3e-3, 2.0e-3, "m", "skid-ring contact radius (config/pencil.yaml range max 2.0 mm)"),
    Var("V", 20.0, 60.0, "V", "drive range (<= part and driver rating)"),
    Var("L_cell", 25e-3, 44e-3, "m", "cell length (pen length = 126 mm + cell)"),
    Var("q_stop", 0.30e-3, 0.70e-3, "m", "nib travel to the stops"),
    Var("n2", 0.6, 1.6, "-", "second-stage lever ratio (topology Q2L only)"),
]
NAMES = [v.name for v in VARS]
VMAP = {v.name: v for v in VARS}

# the current design (config/pencil.yaml P0.1.2, CAD pencil_revPQ)
CURRENT = dict(w=2.6e-3, t=0.67e-3, Lf=28e-3, Lc=8e-3, d=2.55e-3, zg=62e-3, zc0=15e-3, leaf_t=30e-6, leaf_w=1.2e-3,
               leaf_L=5e-3, Fc=0.15, r_ring=1.4e-3, V=60.0, L_cell=40e-3, q_stop=0.40e-3, n2=1.0)


@dataclass
class Options:
    topology: str = "Q"            # Q (push-pull pair per axis), L (one plate per axis), Q2L (Q + flexure lever)
    ceramic: str = "PIC252"        # PIC252 (PL128.10 reference) or PIC251 (PL127.10 reference)
    stack: int = 1                 # plates per position, in parallel (clamped together; one leaf half each)
    leaf_mat: str = "C17200"
    driver: str = "drv2700"
    hall: str = "tmag5170_a2"
    clamp_electroded: bool = True  # True: electrodes over the whole length (PICMA-like, conservative for C)
    sweep_mode: str = "derived"    # 'cad': tip sweep fixed at 0.40 mm (CAD P0.1.2); 'derived': q_stop / n + margin
    sweep_margin: float = 0.05e-3  # ASSUMPTION: leaf compliance and assembly tolerance at the plate tip
    theta_wc: float = 35.0         # deg, worst altitude (REQ-ENV-001)
    mu_wc: float = 0.15            # nib friction of the design load (REQ-PNC-003 convention; 0.35 is the envelope)
    tol_wc: float = -0.20          # AMF-11 part tolerance on stroke and force
    theta_nom: float = 50.0
    mu_nom: float = 0.15
    servo_margin: float = 0.10e-3  # stop travel minus servo soft limit (P0.1.2: 0.40 - 0.30)
    q_lim_min: float = 0.30e-3     # usable correction radius at nominal conditions (REQ-PNC-003: >= 0.30 mm)
    k_gimbal_nib: float = 2.0      # N/m, ASSUMPTION (design.py)
    leaf_design_convention: bool = True   # k_leaf_series = k_drive / ppa as design.py (conservative by ~3 % for Q)
    hinge_frac: float = 0.10       # Q2L: flexure-hinge stiffness at the plate tip / plate stiffness (ASSUMPTION)
    lever_eff: float = 0.95        # Q2L: lever force efficiency (ASSUMPTION)
    k_bond_gap: float = 0.05e-3    # radial gap between stacked plates (spacer in the clamp)
    P_fail_max: float = 1e-4       # per-event fracture probability allowed (drop, stop driven opposite)
    stop_drive_frac: float = 1.0   # drive allowed (fraction of full) while pinned at a stop: 1.0 = no firmware clamp
    f1_min: float = 150.0          # Hz (REQ-PNC-003)
    mass_max_g: float = 20.0       # g incl. +10 % wiring/adhesives (REQ-PNC-001 target)
    life_min_h: float = 2.0        # assisted writing (REQ-PNC-005)
    rec_life_min_h: float = 4.0    # recording (REQ-PNC-005)
    p_el_W: float = 0.065          # electronics incl. 3 mW Hall budget (config/pencil.yaml, ASSUMPTION)
    hall_budget_W: float = 0.003
    power_cases: tuple = ("4Hz_0.3mm", "6Hz_0.3mm", "8Hz_0.3mm", "10Hz_0.3mm", "12Hz_0.3mm")
    hall_gap_extra: float = 0.1e-3 # sensor moved out so the peak field (131 mT) fits the sensor range (SIM magpylib)
    hall_location: str = "nose"    # 'nose' (CAD P0.1.2, beside the collar) or 'rear' (behind the collar, in the leaf zone)
    extra: dict = field(default_factory=dict)

    def key(self):
        return f"{self.topology}-{self.ceramic}-s{self.stack}-{self.leaf_mat}-{self.driver}-{self.hall}" + \
            ("" if self.clamp_electroded else "-ic")


def tensor(v, like=None):
    if isinstance(v, torch.Tensor):
        return v.to(DT)
    return torch.as_tensor(v, dtype=DT)


def design_batch(designs: list[dict]) -> dict:
    """List of variable dicts -> dict of (B,) tensors (missing names from CURRENT)."""
    return {n: torch.tensor([float(d.get(n, CURRENT[n])) for d in designs], dtype=DT) for n in NAMES}


def u_to_x(u: torch.Tensor, lo: torch.Tensor, hi: torch.Tensor) -> dict:
    x = lo + u * (hi - lo)
    return {n: x[..., i] for i, n in enumerate(NAMES)}


def bounds(opts: Options, fixed: dict | None = None):
    """Lower and upper bounds per variable (fixed variables collapse); the drive range is capped by the driver."""
    lo = torch.tensor([v.lo for v in VARS], dtype=DT)
    hi = torch.tensor([v.hi for v in VARS], dtype=DT)
    iV = NAMES.index("V")
    hi[iV] = min(hi[iV].item(), CAT.DRIVERS[opts.driver]["V_max"], CAT.V_PART_MAX)
    if opts.topology != "Q2L":
        fixed = dict(fixed or {})
        fixed.setdefault("n2", 1.0)
    for k, v in (fixed or {}).items():
        i = NAMES.index(k)
        lo[i] = v
        hi[i] = v
    return lo, hi


# ------------------------------------------------------------------------------------------------------------
# Bender (PICMA class) and leaf
# ------------------------------------------------------------------------------------------------------------
def bender(x, opts: Options, tol=0.0):
    c = CAT.CERAMICS[opts.ceramic]
    w, t, Lf, Lc, V = x["w"], x["t"], x["Lf"], x["Lc"], x["V"]
    sv = V / c["V"]
    delta_f = c["delta_f"] * (Lf / c["L_free"]) ** 2 * (c["t"] / t) * sv * (1.0 + tol)
    F_b = c["F_b"] * (w / c["w"]) * (t / c["t"]) ** 2 * (c["L_free"] / Lf) * sv * (1.0 + tol)
    L_el = Lf + Lc if opts.clamp_electroded else Lf
    C_half = c["C_half"] * (w / c["w"]) * (t / c["t"]) * (L_el / c["L_total"])
    k = F_b / delta_f
    EI = k * Lf ** 3 / 3.0
    E_eff = EI / (w * t ** 3 / 12.0)
    m_free = CAT.RHO_PZT * w * t * Lf
    m_plate = CAT.RHO_PZT * w * t * (Lf + Lc)
    ns = float(opts.stack)
    return dict(delta_f=delta_f, F_b=F_b * ns, k=k * ns, C_half=C_half * ns, EI=EI * ns, E_eff=E_eff,
                m_free=m_free * ns, m_plate=m_plate * ns, m_eff_tip=33.0 / 140.0 * m_free * ns,
                m_part_tip=0.375 * m_free * ns, F_b1=F_b, k1=k, w=w, t=t, Lf=Lf,
                t_radial=ns * t + (ns - 1.0) * opts.k_bond_gap, M_piezo=2.0 * EI * delta_f / Lf ** 2 * ns)


def leaf(x, opts: Options):
    m = CAT.LEAF_MATERIALS[opts.leaf_mat]
    E, G = m["E"], m["G"]
    t, w, L = x["leaf_t"], x["leaf_w"], x["leaf_L"]
    Iy = w * t ** 3 / 12.0
    J = w * t ** 3 / 3.0
    return dict(k_cross=E * w * t ** 3 / L ** 3, k_drive=E * t * w ** 3 / L ** 3,
                M_cr=5.0 * math.pi / L * torch.sqrt(E * Iy * G * J), E=E, t=t, w=w, L=L, allow=m["allow_alt"])


# ------------------------------------------------------------------------------------------------------------
# Nib assembly (rear gimbal) from the geometry
# ------------------------------------------------------------------------------------------------------------
def nib_assembly(x):
    zg = x["zg"]
    zcc = x["zc0"] + FIX["collar_L"] / 2
    J = torch.zeros_like(zg)
    first = torch.zeros_like(zg)
    m_rot = 0.0
    m_ax = 0.0
    parts = CAD_PARTS or {k: ("moving",) + v for k, v in {
        "refill_D1": (0.84, 34.7, None), "collar": (0.091, 16.5, None), "collar_liner": (0.005, 16.5, None),
        "collar_magnet": (0.004, 16.5, None), "gimbal_hub": (0.016, 62.0, None), "rear_plug": (0.005, 67.5, None),
        "axial_magnet": (0.004, 67.55, None), "nib_spring": (0.075, 72.5, None)}.items()}
    for name, (grp, mg, zc, _v) in parts.items():
        if grp != "moving":
            continue
        m = mg * 1e-3
        if name == "nib_spring":
            m_ax += m / 3.0
            continue
        if name in COLLAR_GROUP:
            z = zcc
        elif name == "gimbal_hub":
            z = zg
        else:
            z = torch.full_like(zg, zc * 1e-3)
        if name == "refill_D1":
            J = J + m * (FIX["refill_L"] ** 2 / 12.0 + (z - zg) ** 2)
            m_ax += m
        else:
            J = J + m * (z - zg) ** 2
            if name in ("rear_plug", "axial_magnet"):
                m_ax += m
        m_rot += m
        first = first + m * (zg - z)
    L_nib = zg
    L_col = zg - zcc
    return dict(J=J, m_rot=m_rot, m_ax=m_ax, L_nib=L_nib, L_col=L_col, n1=L_nib / L_col, m_eq_col=J / L_col ** 2,
                m_couple_nib=first / L_nib, zcc=zcc)


# ------------------------------------------------------------------------------------------------------------
# Loads (skid architecture, design.spring_nib_reaction; worst stroke direction over the 360-point grid)
# ------------------------------------------------------------------------------------------------------------
_BETAS = torch.linspace(0.0, 2.0 * math.pi, 361, dtype=DT)[:-1]


def skid_load(Fc, theta_deg, mu):
    th = theta_deg * D2R
    st, ct = math.sin(th), math.cos(th)
    b = _BETAS
    den = st - mu * torch.cos(b) * ct
    if bool((den <= 0).any()):
        raise ValueError("self-locking: tan(theta) <= mu cos(beta)")
    geom = torch.sqrt((ct + mu * torch.cos(b) * st) ** 2 + (mu * torch.sin(b)) ** 2) / den    # R_perp / F_c
    return Fc * geom.max()


# ------------------------------------------------------------------------------------------------------------
# Stage reduction (design._reduce_stage)
# ------------------------------------------------------------------------------------------------------------
def stage(x, opts: Options, tol=0.0):
    b = bender(x, opts, tol)
    lf = leaf(x, opts)
    nb = nib_assembly(x)
    ppa = 2.0 if opts.topology in ("Q", "Q2L") else 1.0
    n = nb["n1"]
    if opts.topology == "Q2L":
        n2 = x["n2"]
        delta_col = n2 * b["delta_f"]
        k_p = opts.lever_eff * b["k"] / n2 ** 2
        F_p = k_p * delta_col
        k_h = opts.hinge_frac * b["k"] / n2 ** 2
        m_eff = b["m_eff_tip"] / n2 ** 2
        m_part = b["m_part_tip"] / n2
    else:
        n2 = torch.ones_like(n)
        delta_col, k_p, F_p = b["delta_f"], b["k"], b["F_b"]
        k_h = torch.zeros_like(n)
        m_eff, m_part = b["m_eff_tip"], b["m_part_tip"]
    k_col = ppa * k_p
    F_b_col = ppa * F_p
    k_leaf_series = lf["k_drive"] / ppa if opts.leaf_design_convention else lf["k_drive"] * ppa
    k_par_col = ppa * lf["k_cross"] + opts.k_gimbal_nib * n ** 2 + ppa * k_h
    m_col = nb["m_eq_col"] + ppa * m_eff
    C_axis = ppa * 2.0 * b["C_half"]
    k_eff_col = 1.0 / (1.0 / k_col + 1.0 / k_leaf_series)
    k_b_nib = k_eff_col / n ** 2
    k_par_nib = k_par_col / n ** 2
    m_eq_nib = m_col / n ** 2
    F_b_nib = k_eff_col * delta_col / n
    delta_f_nib = n * delta_col
    f1 = torch.sqrt((k_b_nib + k_par_nib) / m_eq_nib) / TWO_PI
    m_couple_nib = nb["m_couple_nib"] + ppa * m_part / n
    g_V = delta_f_nib / (x["V"] / 2.0)
    return dict(b=b, leaf=lf, nib=nb, ppa=ppa, n=n, n2=n2, k_col=k_col, F_b_col=F_b_col, k_leaf_series=k_leaf_series,
                k_par_col=k_par_col, m_col=m_col, C_axis=C_axis, k_eff_col=k_eff_col, k_b_nib=k_b_nib,
                k_par_nib=k_par_nib, k_tot=k_b_nib + k_par_nib, m_eq_nib=m_eq_nib, F_b_nib=F_b_nib,
                delta_f_nib=delta_f_nib, f1=f1, m_couple_nib=m_couple_nib, g_V=g_V, Fv=k_b_nib * g_V,
                delta_col=delta_col, k_p=k_p)


def stroke(st, F):
    """Symmetric nib stroke about the housing-fixed centre against a load of either sign (design.py)."""
    return (st["F_b_nib"] - F) / st["k_tot"]


# ------------------------------------------------------------------------------------------------------------
# Weibull strength of the plate ceramic (design.py, LITERATURE AMF-48)
# ------------------------------------------------------------------------------------------------------------
def sigma0_plate(w, Lf, t, m=D.PZT_WEIBULL_M):
    V4 = D.weibull_veff_4pb(m)
    Vc = w * Lf * t / (2.0 * (m + 1.0) ** 2)
    return D.PZT_SIGMA0_4PB * (V4 / Vc) ** (1.0 / m)


def sigma_at_pfail(sigma0, P, m=D.PZT_WEIBULL_M):
    return sigma0 * (-math.log(1.0 - P)) ** (1.0 / m)


def p_fail(sigma, sigma0, m=D.PZT_WEIBULL_M):
    return 1.0 - torch.exp(-(torch.clamp(sigma, min=0.0) / sigma0) ** m)


# ------------------------------------------------------------------------------------------------------------
# Geometry: nose, fit (CAD formulas), axial stack
# ------------------------------------------------------------------------------------------------------------
def nose_inner_r(x, z):
    r = x["r_ring"]
    zs = r / math.tan(FIX["theta_design"] * D2R) + FIX["skid_w"]
    r0 = r - 0.05e-3
    z1 = zs + FIX["nose_L"] - 0.5e-3
    return r0 + (R_BORE - r0) * torch.clamp((z - zs) / (z1 - zs), 0.0, 1.0)


def geometry(x, opts: Options, st):
    n = st["n"]
    b = st["b"]
    q_stop = x["q_stop"]
    z_tip = x["zc0"] + FIX["collar_L"] + x["leaf_L"] + (FIX["lever_len"] if opts.topology == "Q2L" else 0.0)
    z_clamp0 = z_tip + x["Lf"]
    z_clamp1 = z_clamp0 + x["Lc"]
    zcc = st["nib"]["zcc"]
    zg = x["zg"]
    u_col = q_stop / n                                   # collar travel at the nib stops
    u_tip = u_col / st["n2"]                             # plate-tip travel at the stops
    if opts.sweep_mode == "cad":
        sw = torch.full_like(u_tip, 0.40e-3)
    else:
        sw = u_tip + opts.sweep_margin
    tr, w, d = b["t_radial"], x["w"], x["d"]
    g = {}
    # (a)-(c) section at the bender station, tips swept to the stops (CAD section_checks)
    if opts.topology in ("Q", "Q2L"):
        g["plate_to_bore"] = R_BORE - torch.sqrt((d + tr / 2 + sw) ** 2 + (w / 2) ** 2)
        g["plate_to_plate"] = d - tr / 2 - sw - w / 2
        lat_half = w / 2
    else:   # L: plates at -x and -y, lateral extent [-1.2 mm, w - 1.2 mm] (CAD)
        lat = torch.maximum(torch.full_like(w, 1.2e-3), w - 1.2e-3)
        g["plate_to_bore"] = R_BORE - torch.sqrt((d + tr / 2 + sw) ** 2 + lat ** 2)
        g["plate_to_plate"] = d - tr / 2 - sw - 1.2e-3
        lat_half = lat
    u_ref = q_stop * (zg - z_tip) / zg                   # refill sweep at the plate tip
    g["plate_to_refill"] = d - tr / 2 - (sw - u_ref) - R_REFILL
    # (d) nose: Hall sensor, collar, optical sensor, refill cone in the skid aperture at theta_min
    zc = zcc
    x_face = FIX["collar_od"] / 2 + 0.3e-3 + u_col + 0.15e-3 + opts.hall_gap_extra
    if opts.hall_location == "nose":
        g["hall_outer_to_nose_wall"] = nose_inner_r(x, zc) - (x_face + 0.6e-3)
    else:   # sensor (1.5 mm package, ASSUMPTION) between two leaves behind the collar: leaf span >= 2.5 mm
        g["hall_outer_to_nose_wall"] = x["leaf_L"] - 2.5e-3 + FIX["clear_min"]
    g["collar_to_nose_wall"] = nose_inner_r(x, x["zc0"]) - (FIX["collar_od"] / 2 + u_col)
    p_max = x["r_ring"] / math.tan(FIX["theta_min"] * D2R)
    frac = torch.clamp((p_max - 0.3e-3) / (FIX["cone_L"] - 0.3e-3), 0.0, 1.0)
    r_cone = FIX["socket_d"] / 2 + (R_REFILL - FIX["socket_d"] / 2) * frac
    g["refill_cone_to_skid_aperture"] = (x["r_ring"] - 0.15e-3) - (r_cone + q_stop)
    g["optical_sensor_to_refill"] = nose_inner_r(x, x["zc0"] - 2e-3) - 0.7e-3 - (R_REFILL + q_stop)
    # snubber frames (CAD snubbers(); plus corner and window-to-window webs, this study)
    webs_in, webs_out, corners, winwin, gaps = [], [], [], [], []
    for sfr in FIX["snub_stations"]:
        z = z_tip + sfr * x["Lf"]
        xi = 1.0 - sfr
        gap = u_tip * (3 * xi ** 2 - xi ** 3) / 2 + FIX["snub_gap_extra"]
        sweep = q_stop * (zg - z) / zg
        r_hole = R_REFILL + sweep + 0.10e-3
        inner = d - tr / 2 - gap
        outer = d + tr / 2 + gap
        webs_in.append(inner - r_hole)
        webs_out.append((R_BORE - 0.05e-3) - outer)
        corners.append((R_BORE - 0.05e-3) - torch.sqrt(outer ** 2 + (lat_half + 0.05e-3) ** 2))
        if opts.topology in ("Q", "Q2L"):
            winwin.append(inner - (w / 2 + 0.05e-3))
        else:
            winwin.append(inner - 1.25e-3)
        gaps.append(gap)
    web_in = torch.stack(webs_in, -1)
    web_out = torch.stack(webs_out, -1)
    corner = torch.stack(corners, -1)
    window = torch.stack(winwin, -1)
    g["snubber_min_web"] = torch.minimum(web_in.min(-1).values, web_out.min(-1).values)
    g["snubber_corner_web"] = corner.min(-1).values
    g["snubber_window_web"] = window.min(-1).values
    # axial stack: clamp block ends before the gimbal hub
    g["axial_clamp_to_gimbal"] = zg - FIX["hub_half"] - FIX["hub_clear"] - z_clamp1
    # decoupling leaf spans radially from the collar surface; with the collar swept it must stay 0.1 mm off the bore
    g["leaf_radial_fit"] = R_BORE - FIX["clear_min"] - u_col - (FIX["collar_od"] / 2 + x["leaf_w"])
    # axial travel the nib spring must accommodate (design.protrusion_budget with this stop travel) <= 3.0 mm
    # (config/pencil.yaml nib.protrusion_travel max); ball radius as config (refill.ball_radius 0.35 mm)
    rb = 0.35e-3
    def p_c(th):
        return (x["r_ring"] * math.cos(th * D2R) - rb) / math.sin(th * D2R)
    travel = (p_c(35.0) + q_stop / math.tan(35 * D2R) + 0.1e-3) - (p_c(75.0) - q_stop / math.tan(75 * D2R) - 0.1e-3)
    g["protrusion_travel"] = 3.0e-3 - travel
    vec = {"snubber_web_in": web_in, "snubber_web_out": web_out, "snubber_corner": corner, "snubber_window": window}
    return dict(gaps=g, vec=vec, sweep=sw, u_col=u_col, u_tip=u_tip, z_tip=z_tip, z_clamp0=z_clamp0,
                z_clamp1=z_clamp1, snub_gaps=torch.stack(gaps, -1), u_ref=u_ref, protrusion_travel=travel)


# ------------------------------------------------------------------------------------------------------------
# Mass (CAD part list, changed parts recomputed) and battery
# ------------------------------------------------------------------------------------------------------------
def _snubber_volume(x, geo, st, opts):
    """PEEK frames: annulus minus the plate windows (CAD snubbers()), mm^3."""
    tr, w, d = st["b"]["t_radial"] / MM, x["w"] / MM, x["d"] / MM
    nwin = 4.0 if opts.topology in ("Q", "Q2L") else 2.0
    V = 0.0
    for i, sfr in enumerate(FIX["snub_stations"]):
        z = geo["z_tip"] + sfr * x["Lf"]
        sweep = x["q_stop"] * (x["zg"] - z) / x["zg"]
        r_hole = (R_REFILL + sweep + 0.10e-3) / MM
        gap = geo["snub_gaps"][..., i] / MM
        ann = math.pi * ((R_BORE / MM - 0.05) ** 2 - r_hole ** 2)
        V = V + FIX["snub_t"] / MM * (ann - nwin * (tr + 2 * gap) * (w + 0.1))
    return V


def mass(x, opts: Options, st, geo):
    """Pen mass (g): CAD Q total with the plates, clamp block, snubbers, leaves, cell and barrel length recomputed."""
    nplates = (4.0 if opts.topology in ("Q", "Q2L") else 2.0) * float(opts.stack)
    V_pl = nplates * x["w"] * x["t"] * (x["Lf"] + x["Lc"]) / MM ** 3
    m_plates = V_pl * DENS["PZT"]
    V_clamp = math.pi * ((R_BORE / MM - 0.05) ** 2 - (R_REFILL / MM + 0.45) ** 2) * x["Lc"] / MM
    m_clamp = V_clamp * DENS["Ti64"]
    m_cell = math.pi * (FIX["batt_d"] / 2 / MM) ** 2 * x["L_cell"] / MM * DENS["Li"]
    m_snub = _snubber_volume(x, geo, st, opts) * DENS["PEEK"]
    nleaf = 4.0 if opts.topology in ("Q", "Q2L") else 2.0
    m_leaf = nleaf * x["leaf_t"] * x["leaf_w"] * x["leaf_L"] / MM ** 3 * DENS["C17200"]
    m_barrel_ext = torch.clamp(x["L_cell"] - 40e-3, min=0.0) / MM * BARREL_G_PER_MM
    base = BASE_MASS_G
    if CAD_PARTS is not None:
        base_plates = sum(v[1] for k, v in CAD_PARTS.items() if k.startswith("bender"))
        base_clamp = CAD_PARTS["clamp_block"][1]
        base_cell = CAD_PARTS["battery"][1]
        base_snub = sum(v[1] for k, v in CAD_PARTS.items() if k.startswith("snubber"))
        base_leaf = sum(v[1] for k, v in CAD_PARTS.items() if k.startswith("leaf"))
    else:
        base_plates, base_clamp, base_cell, base_snub, base_leaf = 1.956, 1.399, 3.451, 0.081, 0.004
    total = (base - base_plates - base_clamp - base_cell - base_snub - base_leaf
             + m_plates + m_clamp + m_cell + m_snub + m_leaf + m_barrel_ext)
    return dict(total_g=total, plates_g=m_plates, clamp_g=m_clamp, cell_g=m_cell, snubbers_g=m_snub, leaves_g=m_leaf,
                with_margin_g=1.10 * total)


def cell_capacity_mAh(L_cell):
    c = CAT.CELL_REF
    return c["C_mAh"] * (L_cell - c["L_dead"]) / (c["L"] - c["L_dead"])


# ------------------------------------------------------------------------------------------------------------
# Drive power (sim/pencil/power.py conventions) with a closed-loop Hall-noise model of the P1 servo
# ------------------------------------------------------------------------------------------------------------
CAL_FILE = os.path.join(OUT, "p1_power_calibration.json")
SERVO = dict(Tv=1e-4, drv_bw=2000.0, d_filt=600.0, servo_bw=25.0, zeta_s=0.4, zeta_0=0.05, C_ls=D.C_LARGE_SIGNAL)


def load_calibration(path=CAL_FILE):
    """Per grid case, from the zero-noise P1 runs of the current design (Q26): the class-B rail power of the
    oracle and of the neutral pencil (writing only), the oracle's per-axis stage velocity, and the stage
    amplitude the oracle needs (sqrt(2) x the rms housing deviation of the neutral run)."""
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    run0 = d["runs"]["0"]
    s0 = run0["summary"]
    cal = {"cases": {}, "meta": d["meta"]}
    for case in s0["oracle"]["P_rail_classB_mW"]:
        o = {k: s0["oracle"][k][case]["mean"] for k in ("q1dot_rms_mm_s", "q2dot_rms_mm_s", "P_rail_classB_mW",
                                                         "P_rail_recovery_mW", "V1_mean", "V2_mean", "q1_rms_um", "q2_rms_um")}
        nt = {k: s0["neutral"][k][case]["mean"] for k in ("P_rail_classB_mW", "P_rail_recovery_mW", "V1_mean", "V2_mean")}
        f0, amp = case.split("Hz_")
        rows = [r for r in run0["rows"] if r["mode"] == "neutral" and abs(r["f0"] - float(f0)) < 1e-9
                and abs(r["amp_mm"] - float(amp[:-2])) < 1e-9]
        nt["A_need_m"] = math.sqrt(2.0) * sum(r["housing_dev_rms_um"] for r in rows) / len(rows) * 1e-6
        cal["cases"][case] = {"oracle": o, "neutral": nt}
    cal["runs"] = d["runs"]
    return cal


def _servo_noise_dV(st, x, sigma_n):
    """Std of the per-servo-sample change of the driver output voltage caused by Hall noise sigma_n (m rms per
    sample at the nib), closed loop, stationary.  Discrete-time model of the P1 inner servo at Tv: 1-sample Hall
    delay, velocity from the measurement difference through the first-order derivative filter, integral action,
    V = V_mid + F / Fv, driver lag (P1 drv_bw) and the stage m q'' = Fv V - k q - c q' ZOH-discretised."""
    Tv = SERVO["Tv"]
    m = st["m_eq_nib"]
    k = st["k_tot"]
    c0 = 2 * SERVO["zeta_0"] * torch.sqrt(k * m)
    Kd = torch.clamp(2 * SERVO["zeta_s"] * torch.sqrt(k * m) - c0, min=0.0)
    Ki = k * TWO_PI * SERVO["servo_bw"]
    Fv = st["Fv"]
    tau = 1.0 / (TWO_PI * SERVO["drv_bw"])
    alpha = 1.0 - math.exp(-TWO_PI * SERVO["d_filt"] * Tv)
    B = k.shape[0] if k.dim() else 1
    k, m, c0, Kd, Ki, Fv = [v.reshape(B) for v in (k, m, c0, Kd, Ki, Fv)]
    # continuous plant: s = [V, q, qd], input Vc
    A = torch.zeros(B, 4, 4, dtype=DT)
    A[:, 0, 0] = -1.0 / tau
    A[:, 0, 3] = 1.0 / tau
    A[:, 1, 2] = 1.0
    A[:, 2, 0] = Fv / m
    A[:, 2, 1] = -k / m
    A[:, 2, 2] = -c0 / m
    Ed = torch.linalg.matrix_exp(A * Tv)
    Ad = Ed[:, :3, :3]
    Bd = Ed[:, :3, 3]
    # full state z = [V, q, qd, q_del, qm_prev, ed, eint]; noise n
    nz = 7
    Acl = torch.zeros(B, nz, nz, dtype=DT)
    bcl = torch.zeros(B, nz, dtype=DT)
    # qm = q_del + n ; vmeas = (qm - qm_prev)/Tv ; ed' = (1-a) ed - a vmeas ; eint' = eint - qm Tv
    # vc = (Ki eint' + Kd ed') / Fv
    # coefficients of ed', eint', vc in terms of z and n
    ed_z = torch.zeros(B, nz, dtype=DT)
    ed_z[:, 5] = 1.0 - alpha
    ed_z[:, 3] = -alpha / Tv
    ed_z[:, 4] = alpha / Tv
    ed_n = torch.full((B,), -alpha / Tv, dtype=DT)
    ei_z = torch.zeros(B, nz, dtype=DT)
    ei_z[:, 6] = 1.0
    ei_z[:, 3] = -Tv
    ei_n = torch.full((B,), -Tv, dtype=DT)
    vc_z = (Ki[:, None] * ei_z + Kd[:, None] * ed_z) / Fv[:, None]
    vc_n = (Ki * ei_n + Kd * ed_n) / Fv
    # plant
    Acl[:, 0:3, 0:3] = Ad
    Acl[:, 0:3, :] = Acl[:, 0:3, :] + Bd[:, :, None] * vc_z[:, None, :]
    bcl[:, 0:3] = Bd * vc_n[:, None]
    # q_del' = q (current, before the plant update)
    Acl[:, 3, 1] = 1.0
    # qm_prev' = qm = q_del + n
    Acl[:, 4, 3] = 1.0
    bcl[:, 4] = 1.0
    Acl[:, 5, :] = ed_z
    bcl[:, 5] = ed_n
    Acl[:, 6, :] = ei_z
    bcl[:, 6] = ei_n
    # stationary covariance: S = A S A^T + b b^T  ->  (I - A (x) A) vec(S) = vec(b b^T)
    I = torch.eye(nz * nz, dtype=DT).expand(B, -1, -1)
    K = torch.einsum("bij,bkl->bikjl", Acl, Acl).reshape(B, nz * nz, nz * nz)
    rhs = torch.einsum("bi,bj->bij", bcl, bcl).reshape(B, nz * nz, 1)
    S = torch.linalg.solve(I - K, rhs).reshape(B, nz, nz)
    # dV = V' - V = (A_row0 - e0) z + b0 n
    cvec = Acl[:, 0, :].clone()
    cvec[:, 0] = cvec[:, 0] - 1.0
    var = torch.einsum("bi,bij,bj->b", cvec, S, cvec) + bcl[:, 0] ** 2
    with torch.no_grad():                                      # spectral radius (stability check, reported)
        rho = torch.linalg.eigvals(Acl).abs().max(-1).values
    return torch.sqrt(torch.clamp(var, min=0.0)) * sigma_n, rho


def _e_pos_gauss_sine(sigma, a, nphi=128):
    """E over phase and noise of max(X, 0), X = a cos(phi) + N(0, sigma^2) (midpoint rule in phase)."""
    phi = (torch.arange(nphi, dtype=DT) + 0.5) * (2.0 * math.pi / nphi)
    mu = a[..., None] * torch.cos(phi)
    s = sigma[..., None] + 1e-30
    zz = mu / s
    Phi = 0.5 * (1.0 + torch.erf(zz / math.sqrt(2.0)))
    pdf = torch.exp(-0.5 * zz ** 2) / math.sqrt(2.0 * math.pi)
    return (mu * Phi + s * pdf).mean(-1)


def hall_noise_nib(st, opts: Options):
    h = CAT.HALL[opts.hall]
    S = CAT.HALL_GAP_TABLE[round(opts.hall_gap_extra, 7)]["S_T_per_m"]
    return st["n"] * h["sigma_B"] / S


def current_options(**kw):
    """Options that reproduce P0.1.2 exactly (CAD tip sweep 0.40 mm, Hall at the CAD position, DRV2700, TMAG5170)."""
    base = dict(sweep_mode="cad", hall_gap_extra=0.0, driver="drv2700", hall="tmag5170_a2")
    base.update(kw)
    return Options(**base)


def drive_power(x, opts: Options, st, usable, cal, cases=None, sigma_n=None):
    """Rail and battery power per grid case for this design, with the P1 conventions (sim/pencil/power.py):
    class-B P_rail = V_rail <max(i,0)>, recovery P_rail = <p+>/eta - eta <p->, i = C dV/dt, two axes.
    Signal (zero Hall noise): P1 oracle and neutral powers of the current design per case, the tremor part
    scaled by C V k_tot / Fv and by the stroke-limited amplitude, the writing part by C V / Fv and F_c.
    Noise: closed-loop servo model (_servo_noise_dV).  Both combined per axis as E[max(Gaussian + sinusoid, 0)].
    Returns dict case -> tensors."""
    drv = CAT.DRIVERS[opts.driver]
    Tv = SERVO["Tv"]
    C = st["C_axis"] * SERVO["C_ls"]
    V = x["V"]
    k_tot, Fv = st["k_tot"], st["Fv"]
    sn = hall_noise_nib(st, opts) if sigma_n is None else sigma_n * torch.ones_like(V)
    sdV, rho = _servo_noise_dV(st, x, sn)
    cases = cases or list(cal["cases"].keys())
    ref = _REF_SCALE()
    s_trem = (C * V * k_tot / Fv) / ref["CVk_over_Fv"]
    s_write = (C * V / Fv) / ref["CVoverFv"] * (x["Fc"] / 0.15)
    th = 50.0 * D2R
    V_mid = V / 2.0
    F_bias = x["Fc"] / math.sin(th) * math.cos(th)                  # static tilt-plane load the stage holds (P1)
    V1_mean = torch.clamp(V_mid + F_bias / Fv, max=V)
    eta = drv["eta_c"] or 0.85
    out = {}
    for case in cases:
        cc = cal["cases"][case]
        PB_or0 = cc["oracle"]["P_rail_classB_mW"] * 1e-3
        PB_ne0 = cc["neutral"]["P_rail_classB_mW"] * 1e-3
        A_need = cc["neutral"]["A_need_m"]
        A0 = min(A_need, ref["usable_ref"])                          # what the P0.1.2 stage delivered in P1
        r_amp = torch.clamp(usable, max=A_need) / A0
        PB_sig = max(PB_or0 - PB_ne0, 0.0) * s_trem * r_amp + PB_ne0 * s_write
        v1, v2 = cc["oracle"]["q1dot_rms_mm_s"], cc["oracle"]["q2dot_rms_mm_s"]
        share = torch.tensor([v1 ** 2, v2 ** 2], dtype=DT) / (v1 ** 2 + v2 ** 2)
        a_dV = math.pi * PB_sig[..., None] * share * Tv / (V * C)[..., None]    # sinusoid giving PB_sig at zero noise
        e_pos = _e_pos_gauss_sine(sdV[..., None].expand_as(a_dV), a_dV)
        PB_axes = V[..., None] * C[..., None] * e_pos / Tv
        Vbar = torch.stack([V1_mean, V_mid], -1)
        PR_axes = Vbar * C[..., None] * e_pos / Tv * (1.0 / eta - eta)
        P_rail_B = PB_axes.sum(-1)
        P_rail_R = PR_axes.sum(-1)
        P_rail = P_rail_R if drv["recovery"] else P_rail_B
        if drv["iq_table"] is not None:
            Pq = drv["channels"] * _iq_interp(drv["iq_table"], V) * 3.7
        else:
            Pq = torch.full_like(V, drv["P_q_fixed"])
        P_batt_drive = Pq + P_rail / drv["eta_boost"]
        P_sensor = CAT.HALL[opts.hall]["P_W"] - opts.hall_budget_W
        P_total = opts.p_el_W + P_sensor + P_batt_drive
        out[case] = dict(P_rail_B=P_rail_B, P_rail_R=P_rail_R, P_rail=P_rail, P_q=Pq, P_batt_drive=P_batt_drive,
                         P_total=P_total, P_noise_B=2 * V * C * sdV / math.sqrt(2 * math.pi) / Tv)
    return out, dict(sigma_dV=sdV, rho=rho, sigma_nib=sn)


def _iq_interp(table, V):
    vs = torch.tensor([a for a, _ in table], dtype=DT)
    is_ = torch.tensor([b for _, b in table], dtype=DT)
    Vc = torch.clamp(V, vs[0].item(), vs[-1].item())
    idx = torch.clamp(torch.searchsorted(vs, Vc.detach().contiguous()), 1, len(vs) - 1)
    v0, v1 = vs[idx - 1], vs[idx]
    i0, i1 = is_[idx - 1], is_[idx]
    return i0 + (i1 - i0) * (Vc - v0) / (v1 - v0)


_REF_CACHE = {}


def _REF_SCALE():
    """Writing term of the current design (zero-noise NEUTRAL rail power at 6 Hz / 0.3 mm, P1) and its scale."""
    if "v" in _REF_CACHE:
        return _REF_CACHE["v"]
    x0 = design_batch([CURRENT])
    st0 = stage(x0, Options())
    C0 = st0["C_axis"] * SERVO["C_ls"]
    q0 = MD_stroke_nominal(x0, st0)
    ref = {"CVoverFv": (C0 * x0["V"] / st0["Fv"]).detach(),
           "CVk_over_Fv": (C0 * x0["V"] * st0["k_tot"] / st0["Fv"]).detach(),
           "usable_ref": float(torch.minimum(q0, x0["q_stop"] - 0.1e-3)[0])}
    _REF_CACHE["v"] = ref
    return ref


def cell_energy_Wh(x):
    return cell_capacity_mAh(x["L_cell"]) * 1e-3 * CAT.CELL_REF["V"] * CAT.CELL_REF["usable"]


def MD_stroke_nominal(x, st):
    return stroke(st, skid_load(x["Fc"], 50.0, 0.15))


def battery_life(x, P_total):
    return cell_energy_Wh(x) / P_total


# ------------------------------------------------------------------------------------------------------------
# Drop stress surrogate
# ------------------------------------------------------------------------------------------------------------
_DROP = {}


def drop_surrogate():
    if "s" not in _DROP:
        from . import drop_surrogate as DS
        _DROP["s"] = DS.load()
    return _DROP["s"]


# ------------------------------------------------------------------------------------------------------------
# Full evaluation
# ------------------------------------------------------------------------------------------------------------
def evaluate(x: dict, opts: Options, cal=None, with_power=True, with_drop=True) -> dict:
    """All quantities of a batch of designs.
    out["g"]:  constraint margins for reporting (>= 0 feasible; lengths in m, the rest relative), scalars per design;
    out["gs"]: the same constraints for the optimiser, normalised to O(1) (lengths / 0.1 mm) and split into
               smooth pieces (per snubber station, per power case), each of shape (B,) or (B, k)."""
    st = stage(x, opts)
    st_wc = stage(x, opts, tol=opts.tol_wc)
    F_wc = skid_load(x["Fc"], opts.theta_wc, opts.mu_wc)
    F_nom = skid_load(x["Fc"], opts.theta_nom, opts.mu_nom)
    F_35_nomtol = F_wc
    F_env = skid_load(x["Fc"], opts.theta_wc, 0.35)
    q_wc = stroke(st_wc, F_wc)
    q_nom = stroke(st, F_nom)
    q_lim = x["q_stop"] - opts.servo_margin
    usable_wc = torch.minimum(q_wc, q_lim)
    usable_nom = torch.minimum(q_nom, q_lim)
    geo = geometry(x, opts, st)
    ms = mass(x, opts, st, geo)
    b = st["b"]
    lf = st["leaf"]
    # plate clamp stress with the tip pushed onto the stop while driven the other way (per plate, nominal part)
    F_stop = b["k1"] * (geo["u_tip"] + opts.stop_drive_frac * b["delta_f"])
    sig_stop = 6.0 * F_stop * x["Lf"] / (x["w"] * x["t"] ** 2)
    sig0 = sigma0_plate(x["w"], x["Lf"], x["t"])
    sig_allow = sigma_at_pfail(sig0, opts.P_fail_max)
    out = dict(stage=st, stage_wc=st_wc, F_wc=F_wc, F_nom=F_nom, q_wc=q_wc, q_nom=q_nom, q_lim=q_lim,
               usable_wc=usable_wc, usable_nom=usable_nom, geo=geo, mass=ms, sig_stop=sig_stop, sig0=sig0,
               sig_allow=sig_allow, P_fail_stop=p_fail(sig_stop, sig0),
               q_35_nomtol=stroke(st, F_35_nomtol), q_wc_mu035=stroke(st_wc, F_env), F_env=F_env,
               q_nom_tol=stroke(st_wc, F_nom))
    LS = 1e-4                                   # length scale of the normalised fit constraints (0.1 mm)
    g, gs = {}, {}
    for key, val in geo["gaps"].items():
        lim = FIX["web_min"] if "web" in key else (0.0 if key in ("axial_clamp_to_gimbal", "leaf_radial_fit",
                                                                  "protrusion_travel") else FIX["clear_min"])
        g[key] = val - lim
        if not key.startswith("snubber"):
            gs[key] = (val - lim) / LS
    for key, arr in geo["vec"].items():
        gs[key] = (arr - FIX["web_min"]) / LS
    g["f1"] = gs["f1"] = (st["f1"] - opts.f1_min) / opts.f1_min
    g["leaf_cross_ratio"] = gs["leaf_cross_ratio"] = (0.05 - lf["k_cross"] * st["ppa"] / st["k_col"]) / 0.05
    g["leaf_drive_ratio"] = gs["leaf_drive_ratio"] = (lf["k_drive"] / st["k_p"] - 20.0) / 20.0
    F_leaf = st["F_b_col"] / st["ppa"]
    sf = lf["M_cr"] / (F_leaf * lf["L"] / 2.0)
    out["leaf_sf"] = sf
    g["leaf_buckling"] = gs["leaf_buckling"] = (sf - 2.0) / 2.0
    sig_leaf = 3.0 * lf["E"] * lf["t"] * geo["u_col"] / lf["L"] ** 2
    out["leaf_stress"] = sig_leaf
    g["leaf_stress"] = gs["leaf_stress"] = (lf["allow"] - sig_leaf) / lf["allow"]
    g["stop_stress"] = gs["stop_stress"] = (sig_allow - sig_stop) / sig_allow
    g["mass"] = gs["mass"] = (opts.mass_max_g - ms["with_margin_g"]) / opts.mass_max_g
    g["pen_length"] = gs["pen_length"] = (170e-3 - (FIX["L_fixed_stack"] + x["L_cell"])) / 170e-3
    # the soft limit is at least the required usable radius, and the nominal loaded stroke fills it
    g["soft_limit_min"] = q_lim - opts.q_lim_min
    gs["soft_limit_min"] = g["soft_limit_min"] / LS
    g["nominal_fills_limit"] = q_nom - q_lim
    gs["nominal_fills_limit"] = g["nominal_fills_limit"] / LS
    if with_drop:
        ds = drop_surrogate()
        if ds is not None:
            m_tip = st["nib"]["m_eq_col"] / (st["ppa"] * float(opts.stack)) * st["n2"] ** 2
            m_free1 = b["m_free"] / float(opts.stack)
            sig_drop = ds.predict(t=x["t"], Lf=x["Lf"], w=x["w"], u_s=geo["u_tip"], mu_tip=m_tip / m_free1, E=b["E_eff"])
            out["sig_drop_2ms"] = sig_drop
            out["P_fail_drop_2ms"] = p_fail(sig_drop, sig0)
            out["drop_mu_tip"] = m_tip / m_free1
            g["drop_stress"] = gs["drop_stress"] = (sig_allow - sig_drop) / sig_allow
    drv = CAT.DRIVERS[opts.driver]
    if drv["C_max_axis"] is not None:
        g["driver_capacitance"] = gs["driver_capacitance"] = \
            (drv["C_max_axis"] - st["C_axis"] * SERVO["C_ls"]) / drv["C_max_axis"]
    if with_power:
        cal = cal or load_calibration()
        if cal is not None:
            pw, noise = drive_power(x, opts, st, torch.clamp(usable_nom, min=0.0), cal)
            out["power"] = pw
            out["noise"] = noise
            cases = [c for c in opts.power_cases if c in pw]
            P_cases = torch.stack([pw[c]["P_total"] for c in cases], -1)
            allc = torch.stack([pw[c]["P_total"] for c in pw], -1)
            out["P_total_mean"] = P_cases.mean(-1)
            out["P_total_worst"] = P_cases.max(-1).values
            out["P_total_grid_mean"] = allc.mean(-1)
            out["P_rail_grid_mean"] = torch.stack([pw[c]["P_rail"] for c in pw], -1).mean(-1)
            out["life_assist_h"] = battery_life(x, out["P_total_worst"])
            out["life_assist_mean_h"] = battery_life(x, out["P_total_mean"])
            P_rec = opts.p_el_W - opts.hall_budget_W + (2 * 13e-6 * 3.7 if drv["iq_table"] is not None else 0.0)
            out["life_recording_h"] = battery_life(x, torch.full_like(x["V"], P_rec))
            g["assist_life"] = (out["life_assist_h"] - opts.life_min_h) / opts.life_min_h
            life_cases = cell_energy_Wh(x)[..., None] / P_cases
            gs["assist_life"] = (life_cases - opts.life_min_h) / opts.life_min_h
            g["recording_life"] = gs["recording_life"] = (out["life_recording_h"] - opts.rec_life_min_h) / opts.rec_life_min_h
            g["servo_stable"] = (1.0 - noise["rho"]) / 0.01            # reported; the P1 gains scale with the stage
    out["g"] = g
    out["gs"] = gs
    return out


# ------------------------------------------------------------------------------------------------------------
# Alternatives evaluated outside the batch model
# ------------------------------------------------------------------------------------------------------------
def tube_best(V=60.0, L=45e-3, wall=0.30e-3, d31=180e-12):
    """Quartered piezo tube around the refill (PI PT230 class, AMF-56): tip deflection
    dx = 2 sqrt(2) d31 U L^2 / (pi ID d) (PI formula) for the largest tube that fits the bore.
    d31 of PIC255 about 180 pm/V: ASSUMPTION (class value; the datasheet quotes the formula, not d31)."""
    OD = 2 * (R_BORE - 0.1e-3)
    ID = OD - 2 * wall
    dx = 2 * math.sqrt(2) * d31 * V * L ** 2 / (math.pi * ID * wall)
    # check against the catalogue part PT230.14 (30 x 6.35 x 5.35 mm, +/-250 V -> +/-16 um)
    dx_pt = 2 * math.sqrt(2) * d31 * 250.0 * 30e-3 ** 2 / (math.pi * 5.35e-3 * 0.5e-3)
    return {"OD_mm": OD / MM, "ID_mm": ID / MM, "L_mm": L / MM, "V": V, "tip_deflection_um": dx * 1e6,
            "with_lever_1.34_um": 1.34 * dx * 1e6, "PT230.14_formula_um_at_250V": dx_pt * 1e6,
            "PT230.14_datasheet_um": 16.0,
            "verdict": "reject: about %.0f um at the nib against >= 300 um needed (CALC; PT230.14 formula %.0f um vs "
                       "16 um datasheet)" % (1.34 * dx * 1e6, dx_pt * 1e6)}


def front_pivot_check(z_pivot=12e-3, q_stop=0.40e-3, z_plates=(23e-3, 51e-3), d=2.55e-3, t=0.67e-3):
    """Front gimbal (lever < 1): the refill tail and the plate zone swing about a pivot near the nib."""
    rows = []
    for z in z_plates:
        sweep = q_stop * (z - z_pivot) / z_pivot
        room = d - t / 2 - R_REFILL
        rows.append({"z_mm": z / MM, "refill_sweep_mm": sweep / MM, "room_to_plate_face_mm": room / MM})
    tail = q_stop * (FIX["refill_L"] - z_pivot) / z_pivot
    return {"pivot_z_mm": z_pivot / MM, "tail_sweep_mm": tail / MM, "rows": rows,
            "verdict": "reject: at the plate zone the refill would swing %.2f-%.2f mm against %.2f mm of room to the "
                       "plate faces (CAD layout), and the tail %.2f mm (CALC)" % (
                           rows[0]["refill_sweep_mm"], rows[-1]["refill_sweep_mm"], rows[0]["room_to_plate_face_mm"],
                           tail / MM)}
