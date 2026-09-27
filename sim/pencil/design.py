r"""Pencil-class pen (Rev P0): shared physical design model.

One source for every derived design quantity used by analysis/pencil_mechanisms.py
and by the pencil simulator (sim/pencil/model.py):

* parameter access: config/pencil.yaml first, config/parameters.yaml for anything
  the pencil file does not define (hand, paper, sensing), each value with its label;
* CAD-derived masses and positions (results/cad/pencil_revP{L,Q}_summary.json from
  mechanics/cad/pencil_revP.py; fall-back constants from the same script);
* the multilayer piezo bender (PICMA class, AMF-11) as a cantilever: force source
  k_b*delta_free(V) in parallel with its stiffness k_b, width scaling, beam stresses;
* reduction of a two-axis bender stage driving the refill at a front collar, the
  refill pivoting in a rear gimbal, to tip-equivalent (nib) quantities;
* contact loads of a spring-loaded nib behind a skid, and of a conventional nib
  that carries the whole writing force (P-5/P-6 of docs/physics.md);
* the nib protrusion geometry behind a skid ring;
* the decoupling leaf between a bender tip and the collar.

Sign conventions follow stabpen/frames.py: a is the barrel axis toward the cap,
t1 = sin(th) h - cos(th) n lies in the tilt plane, t2 = (-sin phi, cos phi, 0).

Evidence status: every derived number is a CALCULATION from inputs labelled
MANUFACTURER STATEMENT (ledger id), LITERATURE, CAD (proposed design) or
ASSUMPTION.  Nothing here has been measured on hardware.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stabpen import params as sp_params  # noqa: E402

PENCIL_YAML = os.path.join(ROOT, "config", "pencil.yaml")
BASE_YAML = os.path.join(ROOT, "config", "parameters.yaml")
CAD_SUMMARY = os.path.join(ROOT, "results", "cad", "pencil_revP{}_summary.json")
D2R = math.pi / 180.0
G0 = 9.80665

# --------------------------------------------------------------------------------------
# Labelled constants (each with its evidence label)
# --------------------------------------------------------------------------------------
# AMF-11: PI PICMA benders PL112-PL140 datasheet (31.07.2020), 0-60 V differential, +/-20 %.
PICMA = {
    "PL112.10": dict(stroke=100e-6, L=18e-3, w=9.60e-3, t=0.67e-3, Fb=2.1, C_half=1.1e-6, fr=1800.0),
    "PL122.10": dict(stroke=310e-6, L=25e-3, w=9.60e-3, t=0.67e-3, Fb=1.25, C_half=2.5e-6, fr=600.0),
    "PL127.10": dict(stroke=450e-6, L=31e-3, w=9.60e-3, t=0.67e-3, Fb=1.1, C_half=3.4e-6, fr=420.0),
    "PL128.10": dict(stroke=450e-6, L=36e-3, w=6.15e-3, t=0.67e-3, Fb=0.55, C_half=1.2e-6, fr=360.0),
    "PL140.10": dict(stroke=1000e-6, L=45e-3, w=11.00e-3, t=0.55e-3, Fb=0.5, C_half=4.1e-6, fr=160.0),
}
PICMA_TOL = 0.20                 # AMF-11: +/-20 % on stroke, force, capacitance
PICMA_V = 60.0                   # AMF-11: 0-60 V (+/-30 V) differential control
RHO_PZT = 7800.0                 # kg/m^3; ASSUMPTION (CAD density; PZT with electrodes 7.6-8.0)
C_LARGE_SIGNAL = 1.3             # ASSUMPTION: large-signal / small-signal capacitance (range 1.0-1.7); EXP-Q04
# Strength of poled multilayer PZT, 4-point bending, 35 x 3.0 x 2.25 mm, spans 30/15 mm, n = 30:
# elastic characteristic strength 124 MPa (90 % CI 119-129), Weibull modulus 8 (6-9);
# LITERATURE (Bermejo & Deluca 2012, J. Ceram. Sci. Tech. 3(4):159; proposed ledger row AMF-48).
PZT_SIGMA0_4PB = 124e6
PZT_WEIBULL_M = 8.0
PZT_4PB = dict(L_o=30e-3, L_i=15e-3, b=3.0e-3, h=2.25e-3)
# Flexure material C17200 TH04 (AMF-18, AMF-19): E 131 GPa, yield >= 1130 MPa, fatigue 310 MPa at 1e8.
CUBE = dict(E=131e9, G=50.4e9, yield_=1130e6, fatigue=310e6, allow_alt=150e6)  # G: ASSUMPTION nu = 0.3


def _load(path):
    return sp_params.load(path)


@dataclass
class Label:
    value: float
    status: str
    source: str


class Params:
    """config/pencil.yaml over config/parameters.yaml, with labels."""

    def __init__(self, pencil_path: str = PENCIL_YAML, base_path: str = BASE_YAML):
        self.pencil = _load(pencil_path)
        self.base = _load(base_path)

    def __getitem__(self, key):
        try:
            return self.pencil[key]
        except KeyError:
            return self.base[key]

    def label(self, key) -> Label:
        try:
            lf = self.pencil.leaf(key)
        except KeyError:
            lf = self.base.leaf(key)
        return Label(lf["value"], lf.get("status", ""), lf.get("source", ""))

    def version(self):
        return {"pencil": self.pencil.version(), "base": self.base.version(),
                "pencil_sha256_16": self.pencil.digest(), "base_sha256_16": self.base.digest()}


# --------------------------------------------------------------------------------------
# CAD geometry and nib-assembly inertia (proposed design, mechanics/cad/pencil_revP.py)
# --------------------------------------------------------------------------------------
_CAD_FALLBACK = {  # mm and g, from the lead's CAD message 2026-09-27 (nominal geometry)
    "z_gimbal": 60.0, "collar_z0": 15.0, "collar_L": 3.0, "z_plate_tip": 19.0, "nib_travel": 0.40,
    "refill_L": 67.0, "ball_d": 0.7, "plate_d": 2.15,
    "parts": [("refill_D1", "moving", 0.84, 34.7), ("collar", "moving", 0.099, 16.5),
              ("collar_magnet", "moving", 0.004, 16.5), ("gimbal_hub", "moving", 0.016, 60.0),
              ("rear_plug", "moving", 0.005, 67.5), ("axial_magnet", "moving", 0.004, 67.55),
              ("nib_spring", "moving", 0.075, 72.5)],
    "mass_total_g": {"L": 11.48, "Q": 12.12},
}


def cad(variant: str = "Q") -> dict:
    """CAD summary (mm, g).  Falls back to the nominal numbers if the file is absent."""
    path = CAD_SUMMARY.format(variant)
    if os.path.exists(path):
        d = json.load(open(path))
        s, P = d["summary"], d["summary"]["parameters_mm"]
        parts = [(r["part"], r["group"], r["mass_g"], r["com_z_mm"]) for r in d["parts"]]
        return {"z_gimbal": P["z_gimbal"], "collar_z0": P["collar_z0"], "collar_L": P["collar_L"],
                "z_plate_tip": P["z_plate_tip"], "nib_travel": P["nib_travel"], "refill_L": P["refill_L"],
                "ball_d": P["ball_d"], "plate_d": P["plate_d"], "parts": parts,
                "mass_total_g": s["mass_total_g"], "source": os.path.relpath(path, ROOT),
                "section_checks": s.get("section_checks", {})}
    fb = dict(_CAD_FALLBACK)
    fb["mass_total_g"] = _CAD_FALLBACK["mass_total_g"][variant]
    fb["source"] = "fallback constants (CAD message)"
    return fb


def nib_assembly(variant: str = "Q") -> dict:
    """Rotational inertia of the nib assembly about the rear gimbal and its lever factors.
    The refill is a uniform rod (length refill_L); other parts are point masses at their CoM.
    The nib spring bears on the bulkhead and is excluded from the rotating mass."""
    c = cad(variant)
    zg = c["z_gimbal"] * 1e-3
    J = 0.0
    m_rot = 0.0
    first = 0.0          # sum m_i * (zg - z_i): momentum of the rotating parts per unit (theta_dot * 1)
    m_ax = 0.0           # axially sliding mass (refill + plug + magnet + 1/3 spring)
    for name, grp, mg, zc in c["parts"]:
        if grp != "moving":
            continue
        m = mg * 1e-3
        z = zc * 1e-3
        if name == "nib_spring":
            m_ax += m / 3.0
            continue
        if name in ("refill_D1",):
            Lr = c["refill_L"] * 1e-3
            J += m * (Lr ** 2 / 12.0 + (z - zg) ** 2)
            m_ax += m
        else:
            J += m * (z - zg) ** 2
            if name in ("rear_plug", "axial_magnet"):
                m_ax += m
        m_rot += m
        first += m * (zg - z)
    zc_col = (c["collar_z0"] + c["collar_L"] / 2.0) * 1e-3
    L_nib = zg                                 # gimbal to ball centre
    L_col = zg - zc_col                        # gimbal to collar centre
    return {"J_gimbal": J, "m_rot": m_rot, "m_ax": m_ax, "L_nib": L_nib, "L_col": L_col,
            "n_lever": L_nib / L_col,           # nib motion per collar motion
            "m_eq_nib": J / L_nib ** 2,          # tip-equivalent inertia of the rotating parts
            "m_eq_col": J / L_col ** 2,
            "m_couple_nib": first / L_nib,       # base-acceleration coupling mass referred to the nib
            "z_cm_rot": zg - first / max(m_rot, 1e-12),
            "cad_source": c["source"], "z_plate_tip": c["z_plate_tip"] * 1e-3,
            "nib_stop": c["nib_travel"] * 1e-3, "ball_r": c["ball_d"] * 0.5e-3}


# --------------------------------------------------------------------------------------
# Piezo bender (PICMA class) as a cantilever
# --------------------------------------------------------------------------------------
@dataclass
class Bender:
    name: str
    w: float                 # plate width (m)
    t: float                 # thickness (m)
    L_free: float            # free (active) length (m)
    L_total: float           # overall length (m)
    delta_f: float           # free tip stroke at full drive, one side (m)
    F_b: float               # blocking force at full drive (N)
    C_half: float            # capacitance of one half (F), small signal
    fr_datasheet: float      # Hz (PL128.10 value; width-independent)
    V_full: float = PICMA_V  # full differential range (V)

    @property
    def k(self):             # tip stiffness (N/m)
        return self.F_b / self.delta_f

    @property
    def EI(self):
        return self.k * self.L_free ** 3 / 3.0

    @property
    def E_eff(self):
        return self.EI / (self.w * self.t ** 3 / 12.0)

    @property
    def m_plate(self):
        return RHO_PZT * self.w * self.t * self.L_total

    @property
    def m_free(self):
        return RHO_PZT * self.w * self.t * self.L_free

    @property
    def m_eff_tip(self):     # kinetic-energy equivalent tip mass, tip-load (cubic) shape: 33/140
        return 33.0 / 140.0 * self.m_free

    @property
    def m_part_tip(self):    # momentum-equivalent tip mass, cubic shape: integral of shape = 3/8
        return 0.375 * self.m_free

    @property
    def M_piezo(self):       # equivalent uniform piezo moment at full drive (N m)
        return 2.0 * self.EI * self.delta_f / self.L_free ** 2

    def f1_bare(self):
        """First cantilever mode, Euler-Bernoulli (1.8751^2), from EI and the density."""
        mu = RHO_PZT * self.w * self.t
        return 1.8751 ** 2 / (2 * math.pi) * math.sqrt(self.EI / (mu * self.L_free ** 4))

    def clamp_stress(self, F_tip):
        """Outer-fibre bending stress at the clamp for a tip force (Pa)."""
        return 6.0 * F_tip * self.L_free / (self.w * self.t ** 2)

    def scaled(self, V_rail):
        """Stroke and blocking force scale with the drive range (linear piezo model)."""
        s = V_rail / self.V_full
        return Bender(self.name, self.w, self.t, self.L_free, self.L_total, self.delta_f * s, self.F_b * s,
                      self.C_half, self.fr_datasheet, V_rail)


def picma_width(w: float, name: str = "custom") -> Bender:
    """PL128.10 scaled to plate width w (AMF-11; blocking force and capacitance scale with width,
    free stroke and resonance do not).  Free length from config/pencil.yaml (28 mm, AMF-11)."""
    b = PICMA["PL128.10"]
    s = w / b["w"]
    return Bender(name, w, b["t"], 28e-3, b["L"], b["stroke"], b["Fb"] * s, b["C_half"] * s, b["fr"])


# --------------------------------------------------------------------------------------
# Stage variants and their reduction to the nib
# --------------------------------------------------------------------------------------
STAGE_VARIANTS = {
    # key: (label, plate width, plates per axis, axes, fits the 7.9 mm bore per CAD)
    "PL128": ("PL128.10 as-is (6.15 mm), one axis", 6.15e-3, 1, 1, "one plate fits beside an off-centre refill (AMF-11, lead)"),
    "L40": ("custom 4.0 mm L pair (P0.1.0 concept)", 4.0e-3, 1, 2, "does not fit: corners collide at +/-0.40 mm tip sweep (CAD message)"),
    "L35": ("custom 3.5 mm L pair", 3.5e-3, 1, 2, "fits: corner gap 0.215 mm, bore gap 0.26 mm (CAD pencil_revPL)"),
    "Q26": ("custom 2.6 mm quad, push-pull pair per axis", 2.6e-3, 2, 2, "fits: plate gap 0.115 mm, bore gap 0.786 mm (CAD pencil_revPQ)"),
}


@dataclass
class Leaf:
    """Decoupling leaf between a bender tip and the collar: thin across the other axis,
    wide along the drive axis, free span along the barrel axis (fixed-guided)."""
    t: float = 30e-6
    w: float = 1.2e-3
    L: float = 5.0e-3
    E: float = CUBE["E"]
    G: float = CUBE["G"]
    Cb_over_K: float = 5.0     # ASSUMPTION: moment-gradient factor 2.5 / effective-length factor 0.5 (check by FEA)

    @property
    def k_cross(self):          # across (out of plane): fixed-guided E w t^3 / L^3
        return self.E * self.w * self.t ** 3 / self.L ** 3

    @property
    def k_drive(self):          # along the drive axis (in-plane bending of the deep leaf)
        return self.E * self.t * self.w ** 3 / self.L ** 3

    def M_cr(self):             # lateral-torsional buckling moment
        Iy = self.w * self.t ** 3 / 12.0
        J = self.w * self.t ** 3 / 3.0
        return self.Cb_over_K * math.pi / self.L * math.sqrt(self.E * Iy * self.G * J)

    def sf_buckling(self, F):
        return self.M_cr() / max(F * self.L / 2.0, 1e-18)

    def stress_cross(self, y):  # fixed-guided outer-fibre stress at a cross deflection y
        return 3.0 * self.E * self.t * y / self.L ** 2


CAD_LEAF = Leaf(t=25e-6, w=0.45e-3, L=1.0e-3, E=193e9, G=77e9)   # CAD drawing: 25 um stainless, 0.45 x 1.0 mm free span
RECOMMENDED_LEAF = Leaf()                                          # C17200 30 um x 1.2 mm x 5 mm free span


@dataclass
class Stage:
    key: str
    label: str
    bender: Bender
    plates_per_axis: int
    axes: int
    fit_note: str
    n: float                     # nib motion per collar motion
    k_col: float                 # bender stiffness per axis at the collar (all plates of the axis)
    F_b_col: float               # blocking force per axis at the collar
    k_leaf_series: float         # drive stiffness of the axis' leaves (in series with the plates)
    k_par_col: float             # parasitic stiffness at the collar (other axis' leaves across + gimbal)
    m_col: float                 # moving mass per axis at the collar (rotating parts + plate effective masses)
    m_part_col: float            # momentum-equivalent mass per axis at the collar
    C_axis: float                # driven capacitance per axis (centre electrodes of all plates), small signal
    V_rail: float
    nib: dict = field(default_factory=dict)

    # --- nib-referred quantities
    @property
    def k_eff_col(self):         # plates in series with their leaves
        return 1.0 / (1.0 / self.k_col + 1.0 / self.k_leaf_series)

    @property
    def k_b_nib(self):
        return self.k_eff_col / self.n ** 2

    @property
    def k_par_nib(self):
        return self.k_par_col / self.n ** 2

    @property
    def m_eq_nib(self):
        return self.m_col / self.n ** 2

    @property
    def m_couple_nib(self):
        # rotating parts (from nib_assembly) + plates' momentum-equivalent mass referred to the nib
        return self.nib["m_couple_nib"] + self.plates_part_nib

    @property
    def plates_part_nib(self):
        return self.plates_per_axis * self.bender.m_part_tip / self.n

    @property
    def delta_f_nib(self):       # free stroke at the nib (one side), leaves included (no force -> no loss)
        return self.n * self.bender.delta_f

    @property
    def F_b_nib(self):           # blocking force at the nib (leaves in series reduce it)
        return self.k_eff_col * self.bender.delta_f / self.n

    @property
    def g_V(self):               # free nib stroke per volt of centre-electrode offset
        return self.delta_f_nib / (self.V_rail / 2.0)

    @property
    def f1(self):                # first stage resonance (in air, leaves and parasitics included)
        return math.sqrt((self.k_b_nib + self.k_par_nib) / self.m_eq_nib) / (2 * math.pi)

    def stroke_under_load(self, F_nib):
        """Symmetric nib stroke about the housing-fixed centre against a load F_nib whose
        direction can be either sign (roll unknown): q = (F_b - |F|)/(k_b + k_par) at the nib."""
        F = abs(F_nib)
        return max(0.0, (self.F_b_nib - F) / (self.k_b_nib + self.k_par_nib))

    def optimum_lever(self, F_nib):
        """n* maximising the loaded stroke for this bender set: n* = F_b,col / (2 F)."""
        return self.F_b_col / (2.0 * max(abs(F_nib), 1e-12))

    def summary(self):
        return {"key": self.key, "label": self.label, "plate_width_mm": self.bender.w * 1e3,
                "plates_per_axis": self.plates_per_axis, "axes": self.axes, "fit": self.fit_note,
                "lever_nib_per_collar": self.n, "F_b_collar_N": self.F_b_col, "k_collar_N_per_m": self.k_col,
                "k_leaf_series_N_per_m": self.k_leaf_series, "k_parasitic_collar_N_per_m": self.k_par_col,
                "F_b_nib_N": self.F_b_nib, "free_stroke_nib_um": self.delta_f_nib * 1e6,
                "k_b_nib_N_per_m": self.k_b_nib, "k_par_nib_N_per_m": self.k_par_nib,
                "m_eq_nib_g": self.m_eq_nib * 1e3, "m_couple_nib_g": self.m_couple_nib * 1e3,
                "f1_Hz": self.f1, "C_axis_small_signal_uF": self.C_axis * 1e6, "V_rail": self.V_rail,
                "g_V_um_per_V": self.g_V * 1e6}


def stage(key: str = "Q26", V_rail: float = PICMA_V, leaf: Leaf = RECOMMENDED_LEAF,
          k_gimbal_nib: float = 2.0, variant_cad: str | None = None, tol: float = 0.0) -> Stage:
    """Build a stage variant.  tol = -0.2 applies the AMF-11 -20 % tolerance to stroke and force.
    k_gimbal_nib: ASSUMPTION (cross-strip gimbal about 0.8 N/m at the nib by beam theory; 2 N/m
    with margin; the CAD gimbal is an envelope only)."""
    label, w, ppa, axes, fit = STAGE_VARIANTS[key]
    b = picma_width(w, key)
    if tol:
        b = Bender(b.name, b.w, b.t, b.L_free, b.L_total, b.delta_f * (1 + tol), b.F_b * (1 + tol),
                   b.C_half, b.fr_datasheet)
    b = b.scaled(V_rail)
    nib = nib_assembly(variant_cad or ("L" if key.startswith("L") else "Q"))
    n = nib["n_lever"]
    k_col = ppa * b.k
    F_b_col = ppa * b.F_b
    k_leaf_series = leaf.k_drive / ppa          # plates in parallel, each through its own leaf
    other = ppa if axes == 2 else 0             # leaves of the other axis resist this axis across
    k_par_col = other * leaf.k_cross + k_gimbal_nib * n ** 2
    m_col = nib["m_eq_col"] + ppa * b.m_eff_tip
    m_part_col = ppa * b.m_part_tip
    C_axis = ppa * 2.0 * b.C_half               # centre electrodes of the axis' plates, both halves in parallel
    return Stage(key, label, b, ppa, axes, fit, n, k_col, F_b_col, k_leaf_series, k_par_col, m_col,
                 m_part_col, C_axis, V_rail, nib)


# --------------------------------------------------------------------------------------
# Contact loads
# --------------------------------------------------------------------------------------
def pen_reaction(N, theta, mu, beta):
    """Conventional pen: the nib carries the whole normal force N (P-5).  Components of the
    paper reaction on the ball: t1 (tilt plane), t2 (sideways), a (axial)."""
    f_h = -mu * N * np.cos(beta)
    f_t2 = -mu * N * np.sin(beta)
    R_t1 = -N * np.cos(theta) + f_h * np.sin(theta)
    R_t2 = f_t2
    R_a = N * np.sin(theta) + f_h * np.cos(theta)
    return {"N": N * np.ones_like(np.asarray(beta, float)), "R_t1": R_t1, "R_t2": R_t2, "R_a": R_a,
            "R_perp": np.hypot(R_t1, R_t2), "friction": mu * N * np.ones_like(np.asarray(beta, float))}


def spring_nib_reaction(F_c, theta, mu, beta, axial_friction=0.0):
    """Skid architecture: the refill is pressed along the barrel axis by a spring force F_c
    (axial balance R_a = F_c + axial_friction).  Exact with friction:
        N = (F_c + F_fr) / (sin th - mu cos(beta) cos th),  R_perp = N sqrt((cos th + mu cos b sin th)^2 + (mu sin b)^2)
    Frictionless limit (lead / config_trade convention): N = F_c / sin th, R_perp = F_c cot th."""
    den = np.sin(theta) - mu * np.cos(beta) * np.cos(theta)
    if np.any(den <= 0):
        raise ValueError("self-locking: tan(theta) <= mu cos(beta)")
    N = (F_c + axial_friction) / den
    r = pen_reaction(N, theta, mu, beta)
    r["N"] = N
    r["friction"] = mu * N
    return r


BETAS = np.linspace(0.0, 2.0 * np.pi, 361)[:-1]


def load_extremes(kind, force, theta, mu):
    """Max over stroke direction of the tilt-plane, sideways and total transverse loads,
    the nib normal force and friction.  kind: 'pen' (force = N) or 'skid' (force = F_c)."""
    if kind == "pen":
        r = pen_reaction(force, theta, mu, BETAS)
    else:
        r = spring_nib_reaction(force, theta, mu, BETAS)
    return {"R_t1_max": float(np.max(np.abs(r["R_t1"]))), "R_t2_max": float(np.max(np.abs(r["R_t2"]))),
            "R_perp_max": float(np.max(r["R_perp"])), "R_perp_rms": float(np.sqrt(np.mean(r["R_perp"] ** 2))),
            "R_perp_min": float(np.min(r["R_perp"])), "N_nib_max": float(np.max(r["N"])),
            "N_nib_min": float(np.min(r["N"])), "friction_max": float(np.max(r["friction"])),
            "R_t1_static": float(abs(r["R_t1"][90]))}   # beta = 90 deg: no friction in the tilt plane


# --------------------------------------------------------------------------------------
# Nib protrusion behind a skid ring
# --------------------------------------------------------------------------------------
def protrusion(theta, r_ring, r_ball=0.35e-3):
    """Protrusion of the nib beyond the skid-ring plane when both touch the paper.
    lead formula (tip, sharp ring, ball radius neglected): p_tip = r cot(theta);
    exact for a spherical ball: ball-centre protrusion p_c = (r cos th - r_b)/sin th, tip = p_c + r_b."""
    p_simple = r_ring / math.tan(theta)
    p_centre = (r_ring * math.cos(theta) - r_ball) / math.sin(theta)
    return {"p_tip_simple": p_simple, "p_centre": p_centre, "p_tip_exact": p_centre + r_ball}


def protrusion_budget(r_ring, th_min=35 * D2R, th_max=75 * D2R, q_work=0.30e-3, q_stop=0.40e-3,
                      margin=0.10e-3, r_ball=0.35e-3):
    """Axial travel the nib spring must accommodate: tilt range plus the axial slide that
    keeps the ball on the paper while the stage moves in the tilt plane (s = q cot th)."""
    lo, hi = protrusion(th_max, r_ring, r_ball), protrusion(th_min, r_ring, r_ball)
    tilt_simple = hi["p_tip_simple"] - lo["p_tip_simple"]
    tilt_exact = hi["p_centre"] - lo["p_centre"]
    acc_work = q_work * (1 / math.tan(th_min) + 1 / math.tan(th_max))
    acc_stop = q_stop * (1 / math.tan(th_min) + 1 / math.tan(th_max))
    front = hi["p_centre"] + q_stop / math.tan(th_min) + margin     # ball-centre protrusion at the front stop
    rear = lo["p_centre"] - q_stop / math.tan(th_max) - margin
    return {"tilt_range_simple": tilt_simple, "tilt_range_exact": tilt_exact,
            "with_working_stroke": tilt_simple + acc_work, "with_stops": tilt_simple + acc_stop,
            "front_stop_centre": front, "rear_stop_centre": rear, "travel_stops_exact": front - rear,
            "p_centre_35": hi["p_centre"], "p_centre_75": lo["p_centre"]}


# --------------------------------------------------------------------------------------
# Weibull strength of the bender ceramic
# --------------------------------------------------------------------------------------
def weibull_veff_4pb(m=PZT_WEIBULL_M, g=PZT_4PB):
    """Effective volume of a 4-point bend bar (ASTM C1683): V_E = (L_o b h / 2)(m L_i/L_o + 1)/(m+1)^2."""
    return g["L_o"] * g["b"] * g["h"] / 2.0 * (m * g["L_i"] / g["L_o"] + 1.0) / (m + 1.0) ** 2


def weibull_veff_cantilever(b: Bender, m=PZT_WEIBULL_M, stress_shape="linear"):
    """Effective volume of a cantilever plate under a tip load (moment linear along the length,
    tension on one half of the thickness): V_E = w L t / (2 (m+1)^2)."""
    return b.w * b.L_free * b.t / (2.0 * (m + 1.0) ** 2)


def sigma0_bender(b: Bender, m=PZT_WEIBULL_M):
    """Characteristic strength scaled from the 4PB bars to the bender's effective volume."""
    return PZT_SIGMA0_4PB * (weibull_veff_4pb(m) / weibull_veff_cantilever(b, m)) ** (1.0 / m)


def p_fail(sigma, b: Bender, m=PZT_WEIBULL_M):
    return 1.0 - math.exp(-(max(sigma, 0.0) / sigma0_bender(b, m)) ** m)
