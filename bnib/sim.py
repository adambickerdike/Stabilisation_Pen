r"""The best nibs in sim2 (SIMULATION; sim2 and sim2j are imported read-only; what differs is a copy in this module).

Designs (candidates.py / optimise.py; PROPOSED DESIGN parameters):
  B1  pen24_counterface  the translation nib with the contact-driven counter-face (candidate c), 24 mm pen
  B2  pen24_unbalanced   the SAME nib without the balance (candidate f): the ablation that isolates the balance
  B3  slim_piezo         the slim core's piezo bender fine stage (candidate h), 14 mm, rear-pivot lever
How a translation nib is represented in sim2 without editing it.  sim2's nose is a two-axis gimbal at z_p behind the
ball with its actuator at z_a.  With z_p = 10 m (a virtual pivot) and z_a = 2 z_p the nose TRANSLATES the ball (a 1 mm
tip motion tilts the refill by 0.1 mrad), its tip-equivalent mass is the carrier + refill (x (1 - z_g/z_p)^2 = 0.993),
the suspension is k_tip = k_r / z_p^2 and the coil force K_f I acts at the tip.  The refill slides in the carrier as in
sim2 (its constant-force spring for B2; for B1 a light seat spring near the front stop, the ink force coming from the
face).  B3 uses sim2's gimbal as it is (the refill pivots at the rear gimbal, z_p = 80 mm; the plates are the joint
stiffness and a free-stroke 'actuator').
Additions (a copy of sim2j's stepper with insertions, as sim2j did with sim2's):
  every physics step  the counter-face's force on the refill's rear end and its reaction on the handle (face normal
                      scheduled from the IMU's tilt estimate with its error, spring force F_n along it, engaged above
                      the follower stop with a 5 um ramp); the seat spring (B1); the nib's weight on the nose and the
                      refill (sim2 runs gravity-free, H1 convention; the nib's weight is part of its static load)
  every 2 kHz tick    the friction map sets the ball's LuGre coefficients mu(N, v, ink, paper) (contact.mu_kinetic);
                      the follower stop tracks the writing position while the ball is on the paper
  every servo tick    a FILTERED position servo (FilteredServo): a model-based observer on the Hall reading (not the
                      true velocity, not the raw noisy Hall), feed-forward of the reference's inertia and suspension,
                      PD + integral on the observer's estimate; coil limits (driver, supply, back-EMF); a two-node
                      thermal model (thermal.TwoNode) with the governor in the loop (current x g(T))
Page sensor: DeltaPenSensors, a MEASURED-style error calibrated to DeltaPen (LIT OPT-02, Luethi, Fender, Holz, UIST
2022, section 4.4: translation error per 10 ms window median 23.6 um, mean 68.3 um; idle drift 2.6 mm/min): a held
error redrawn every 10 ms whose WINDOW DIFFERENCES have that median and mean (calibrated here by Monte Carlo), a slow
drift at the idle-drift speed, and a per-run scale error with a median of 1.2 % (OPT-75, DeltaPen Fig. 7 MdAPE while
writing).  sim2's ideal sensor (3 um white) is run only as a labelled bound.
Tracker: sim2j's frozen guarded AKF (results/sim2j/rules.json), unchanged.  This study's own rules (servo bandwidth,
face gap) are chosen on tuning writers 100-101 / seed 300 and frozen in results/bnib/rules.json before the test runs
(writers 0-5, seeds 200-203).
Every number from this module is a SIMULATION on synthetic writers and synthetic tremor.
"""
from __future__ import annotations

import contextlib
import copy
import json
import math
import os
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

import mujoco
import numpy as np
from numba import njit
from scipy.signal import butter, sosfiltfilt

from . import BUILD, RESULTS, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, cache_path
from . import actuators as A
from . import balance as BL
from . import candidates as CD
from . import contact as C
from . import thermal as TH
from .labels import CONTACT, DRIVE, FRICTION, G0, MAT, PIEZO, SENSORS, THERMAL, val

import sim2  # noqa: F401,E402
from sim2 import builder as B  # noqa: E402
from sim2 import params as P  # noqa: E402
from sim2 import sim as S  # noqa: E402
from sim2 import plugins as PL  # noqa: E402
from sim2.contact import K_MUK, K_MUS, K_SG0  # noqa: E402
from sim2j import stepper as SJ  # noqa: E402
from sim2j import tasks as TK  # noqa: E402
from sim2j import et as ET  # noqa: E402
from sim2j.sensing import OnlineSensors  # noqa: E402
from handwriting import metrics as MT  # noqa: E402

D2R = math.pi / 180.0
DT = 50e-6                  # sim2j's test-grid step (sim2 section 5.3)
SIM_DT = TK.SIM_DT          # writer scenario step (25 us)
Z_VIRT = 10.0               # m virtual pivot of the translation nib
TEXT = ET.ET_TEXT           # "return library"
PRE_S = ET.ET_PRE_S         # 4 s on the paper before writing (tremor detectors need it; sim2j convention)
L_END = 0.070               # m ball to the refill holder's rear end (refill 67 mm + holder)
ROWS = BUILD / "sim_rows.json"
SETUPS = BUILD / "setups"

# ------------------------------------------------------------------------------------------------ tremor cells
# ET: sim2j's frequencies and amplitudes (4-12 Hz x 0.3-2 mm); PD: 4.5-5.5 Hz, more regular, waxing and waning, more
# elliptical (ASSUMPTION shape parameters of stabpen.signals.TremorSpec; PD tremor in writing is mostly 4-6 Hz)
PD_KW = {"f_jitter": 0.15, "am_depth": 0.45, "ellipticity": 0.6, "harmonic": 0.25}
CELLS = (("ET", 4.0, 1.0e-3), ("ET", 6.0, 2.0e-3), ("ET", 8.0, 0.3e-3), ("ET", 8.0, 1.0e-3), ("ET", 8.0, 2.0e-3),
         ("ET", 12.0, 1.0e-3), ("PD", 4.5, 1.0e-3), ("PD", 5.5, 2.0e-3), ("PD", 5.0, 0.3e-3))
TUNE_CELLS = (("ET", 8.0, 1.0e-3), ("PD", 5.0, 1.0e-3))
# the slim piezo stage (B3) runs on writers 0-2 only (compute; the four cores are shared)
WRITERS_FOR = {"B1": TEST_WRITERS[:4], "B2": TEST_WRITERS[:4], "B3": TEST_WRITERS[:3]}   # two container restarts: shortened
ROWS_LIFT08 = BUILD / "sim_rows_lift08.json"     # the first grid, run with sim2's default 0.8 mm page lift cut-off
# travel variant (B1w, +-1.5 mm) against B1 (+-1.0 mm): the cells where the handle's tremor reaches beyond +-1 mm
TRAVEL_CELLS = (("ET", 8.0, 1.0e-3), ("ET", 8.0, 2.0e-3), ("ET", 6.0, 2.0e-3), ("PD", 5.5, 2.0e-3))


# ================================================================================================ design parameters
@dataclass
class SimDesign:
    name: str
    title: str
    key: str                              # candidate key
    grip: str                             # 'pen24' | 'slim14'
    family: str                           # 'translation' | 'piezo'
    design: object = None                 # candidates.Design
    ev: Dict = field(default_factory=dict)
    counterface: bool = False
    F_s: float = 0.15
    face_gap: float = 0.15e-3             # m follower-stop gap along the face normal (PROPOSED DESIGN; tuned)
    face_tau: float = 0.3                 # s follower time constant in contact (PROPOSED DESIGN)
    face_ramp: float = 5e-6               # m engagement ramp (contact compliance of the rolling ball on the face)
    seat_F: float = 0.02                  # N seat spring near the front stop (B1)
    seat_d: float = 0.1e-3                # m its travel
    servo_fi: float = 150.0               # Hz inner-loop bandwidth (tuned)
    obs_mult: float = 3.0                 # observer bandwidth / inner bandwidth
    front_margin: float = 0.5e-3          # m ball protrusion allowed beyond the contact position (pen-up)
    label: str = "PROPOSED DESIGN (candidates.py / optimise.py) in sim2: SIMULATION"


def _opt_point(pid: str, eps_T_mm: float) -> Optional[Dict]:
    p = BUILD / "opt_cache.json"
    if p.exists():
        c = json.loads(p.read_text())
        runs = c.get(pid, {}).get("runs", [])
    else:
        # The cache is git-ignored. A clean clone must still select the committed
        # studied design instead of silently substituting the hand-sized default.
        from . import RESULTS
        recorded = RESULTS / "bnib.json"
        runs = json.loads(recorded.read_text()).get("optimisation", {}).get("runs", {}).get(pid, []) if recorded.exists() else []
    for run in runs:
        if abs(run["eps_T_mm"] - eps_T_mm) < 1e-6 and run["feasible"]:
            return run["best"]["x"]
    return None


def sim_designs(use_opt: bool = True) -> Dict[str, SimDesign]:
    """B1/B2 share one nib (the optimiser's counter-face design at travel >= 1 mm, else the default); B2 removes the
    balance (the refill spring pushes from the carrier again) and keeps everything else."""
    from . import optimise as OP
    x = _opt_point("pen24_c", 1.0) if use_opt else None
    d1 = CD.make("c_counterface", CD.pen24())
    if x:
        d1 = OP.build("c_counterface", "pen24", x)
    d2 = copy.deepcopy(d1)
    d2.key, d2.title, d2.balance, d2.balance_mass = "f_translation", "(f) the same nib without the balance", BL.NoBalance(), 0.0
    d3 = CD.make("h_piezo", CD.slim(14e-3))
    todo = [("B1", d1, True, "translation", "pen24", "translation nib + counter-face (24 mm)"),
            ("B2", d2, False, "translation", "pen24", "the same nib, no balance (24 mm)"),
            ("B3", d3, False, "piezo", "slim14", "piezo bender fine stage (14 mm slim core)")]
    # the travel variant (stage_travel only): the optimiser's counter-face point at the 1.5 mm travel floor
    xw = _opt_point("pen24_c", 1.5) if use_opt else None
    if xw:
        todo.append(("B1w", OP.build("c_counterface", "pen24", xw), True, "translation", "pen24",
                     "the counter-face nib at +-1.5 mm (24 mm; travel variant)"))
    out = {}
    for nm, d, cf, fam, grip, title in todo:
        ev = CD.evaluate(d, detail=False, fast=True)
        out[nm] = SimDesign(name=nm, title=title, key=d.key, grip=grip, family=fam, design=d, ev=ev, counterface=cf,
                            F_s=d.F_s)
    return out


# ================================================================================================ parts and model
def _tube_r2(od, id_=0.0):
    return (od * od + id_ * id_) / 16.0


def parts(sd: SimDesign):
    """(handle, nose, refill) part lists (name, m kg, z m, L m, r2 m^2) for sim2's builder.  Handle: the grip class's
    fixed parts (candidates.pen24 / slim) + the nib's stator (+ the counter-face assembly), x1.10 wiring (P0/H1
    convention); nose (moving): carrier, coils or collar, sleeve, Hall magnet (no allowance: the design's moving
    mass); refill: the D1 refill and its holder (CALC)."""
    d = sd.design
    g = d.grip
    hp = [(n, m * 1.10, z, 0.02, _tube_r2(g.od * 0.8)) for n, m, z in g.fixed_parts]
    ev = sd.ev
    hw = ev.get("hw") or {}
    if sd.family == "translation":
        hp.append(("nib_stator", hw["stator_mass"] * 1.10, d.z_act, 0.010, _tube_r2(0.020, 0.006)))
        hp.append(("suspension", ev["flexure"]["mass_g"] * 1e-3 * 1.10, d.z_act - 0.012, 0.025, _tube_r2(0.011)))
        if sd.counterface:
            hp.append(("counterface", d.balance_mass * 1.10, d.balance_z, 0.008, _tube_r2(0.010)))
        m_move = hw["m_move"]
        refill_m = val(CONTACT["refill_mass"]) + 0.5e-3                      # refill + holder
        m_nose = m_move - refill_m
        npar = [("carrier_coils_sleeve", m_nose, 0.030, 0.040, _tube_r2(0.006, 0.0025))]
        rf = [("refill_D1", val(CONTACT["refill_mass"]), 0.0335, 0.064, 0.00235 ** 2 / 16),
              ("refill_holder", 0.5e-3, 0.068, 0.006, 0.003 ** 2 / 4)]
    else:
        pz = ev["piezo"]
        hp.append(("piezo_plates", pz["plates_mass_g"] * 1e-3 * 1.10, 0.040, 0.030, _tube_r2(0.010)))
        hp.append(("piezo_driver", 0.8e-3 * 1.10, 0.065, 0.010, _tube_r2(0.008)))
        # nose about the rear pivot (z_p = z_g): collar at 20 mm, the refill; mass set so I / z_p^2 = the stage's
        # tip-equivalent mass (actuators.piezo_stage m_eff incl. 0.24 of the plates, CALC)
        z_g = _piezo_zg(d)
        m_eff = pz["m_eff_tip_g"] * 1e-3
        J_ref = val(CONTACT["refill_mass"]) * ((0.0335 - z_g) ** 2 + 0.064 ** 2 / 12)
        m_col = max((m_eff * z_g ** 2 - J_ref) / (0.020 - z_g) ** 2, 0.2e-3)
        npar = [("collar", m_col, 0.020, 0.004, _tube_r2(0.004, 0.0024))]
        rf = [("refill_D1", val(CONTACT["refill_mass"]), 0.0335, 0.064, 0.00235 ** 2 / 16),
              ("refill_holder", 0.2e-3, 0.068, 0.004, 0.003 ** 2 / 4)]
    return hp, npar, rf


def _piezo_zg(d) -> float:
    """Rear gimbal position for the stage's lever lambda = z_g / (z_g - z_collar) with the collar at 20 mm."""
    lam = d.piezo.lam
    return lam * 0.020 / (lam - 1.0) if lam > 1.0 else 0.080


@contextlib.contextmanager
def _parts_patch(sd: SimDesign):
    orig = P.part_lists

    def mine(wiring=P.WIRING):
        return parts(sd)
    P.part_lists = mine
    try:
        yield
    finally:
        P.part_lists = orig


def config(sd: SimDesign, theta_deg: float = 50.0, dt: float = DT) -> P.Config:
    d = sd.design
    ev = sd.ev
    g = d.grip
    tn = TH.model_for(g.od, max((ev.get("hw") or {}).get("L_src", 8e-3), 5e-3), (ev.get("hw") or {}).get("m_cu", 0.5e-3),
                      spreader=TH.GRAPHITE_30, wall=g.wall)
    hall = ev["sensing"]["nib_hall_noise_um_20kSPS"] * 1e-6 / math.sqrt(2.0)          # 10 kSPS (2-sample average)
    geom_kw = dict(theta_deg=theta_deg, length=g.L_base, handle_od=g.od, skid_R=7.0e-3 if sd.grip == "pen24" else 4.5e-3,
                   z_f=0.032, z_w=0.092, z_imu=0.061 if sd.grip == "pen24" else 0.070, r_imu=-3.0e-3 if sd.grip == "pen24" else -2.0e-3,
                   z_hall_sensor=0.036, z_hall_magnet=0.035, z_page_sensor=0.013 if sd.grip == "pen24" else 0.012,
                   z_endcap=(g.L_base - 0.02, g.L_base), front_stop_margin=sd.front_margin)
    if sd.family == "translation":
        k_tip = ev["k_tip_N_m"]
        Km = ev["Km_tip"]
        geom = P.Geometry(z_p=Z_VIRT, z_a=2 * Z_VIRT, travel=d.travel, travel_stop=d.travel + 0.2e-3, **geom_kw)
        nose = P.Nose(k_r=k_tip * Z_VIRT ** 2, zeta_flex=0.01, Km_act=Km, R=2.5, L_ind=50e-6, I_max=val(DRIVE["I_peak"]),
                      V_supply=val(DRIVE["V_bus"]), R_th=tn.R_cs + tn.R_sa, C_th=tn.C_c, T_amb=tn.T_room,
                      servo_hz=80.0, servo_zeta=0.7, inner_hz=sd.servo_fi, slew=0.6, q_taper=0.3e-3,
                      bias=not sd.counterface, hall_noise=hall, hall_delay=50e-6)
        F_c = 1e-4 if sd.counterface else sd.F_s
    else:
        pz = ev["piezo"]
        z_g = _piezo_zg(d)
        k_tip = pz["tip_k_N_m"]
        geom = P.Geometry(z_p=z_g, z_a=2 * z_g, travel=pz["tip_free_stroke_mm"] * 1e-3,
                          travel_stop=pz["tip_free_stroke_mm"] * 1e-3 + 0.1e-3, **geom_kw)
        nose = P.Nose(k_r=k_tip * z_g ** 2, zeta_flex=0.03, Km_act=1.0, R=1.0, L_ind=1e-9, I_max=1e3, V_supply=1e6,
                      R_th=1e3, C_th=1.0, servo_hz=80.0, servo_zeta=0.7, inner_hz=sd.servo_fi, slew=0.6, q_taper=0.1e-3,
                      bias=False, hall_noise=0.44e-6, hall_delay=50e-6)
        F_c = sd.F_s
    refill = P.Refill(F_c=F_c, L_ref=1.0, slide_range=(-0.3e-3, 12e-3), frictionloss=val(CONTACT["slide_friction"]),
                      front_stop="nose_adaptive")
    sensors = P.Sensors(hall_noise=nose.hall_noise, page_rate=val(SENSORS["page_rate"]), page_latency=val(SENSORS["page_latency"]),
                        page_noise=val(SENSORS["page_ideal_noise"]), page_lift_max=val(SENSORS["page_lift_max"]))
    contact = P.Contact(mu_ball=0.15)
    return P.Config(geom=geom, nose=nose, refill=refill, sensors=sensors, contact=contact, hand=P.HandH1(r_rot=0.5),
                    N0=1.0, dt=dt, record_hz=2000.0, hand_model="h1", gravity=False,
                    label=f"bnib {sd.name} {sd.title} theta {theta_deg:g}")


def build(sd: SimDesign, theta_deg: float = 50.0, dt: float = DT) -> B.PenModel:
    cfg = config(sd, theta_deg, dt)
    with _parts_patch(sd):
        pm = B.build(cfg)
    # physical travel stops of the nib (the servo's soft limit is the usable travel)
    z_p = cfg.geom.z_p
    for jn in ("nose_1", "nose_2"):
        j = pm.ids["jnt:" + jn]
        a = cfg.geom.travel_stop / z_p
        pm.m.jnt_range[j, 0] = -a
        pm.m.jnt_range[j, 1] = a
    pm.info["bnib"] = {"design": sd.name, "family": sd.family, "counterface": sd.counterface,
                       "m_tip_equiv_g": pm.info["nose_I_pivot"] / z_p ** 2 * 1e3}
    return pm


# ================================================================================================ page sensor
_DP_CAL = None


def deltapen_calibration(n: int = 200000, seed: int = 5) -> Dict:
    """Held-error magnitude distribution (lognormal: median m, log-sd s) whose 10 ms window DIFFERENCES have DeltaPen's
    median 23.6 um and mean 68.3 um (LIT OPT-02), by Monte Carlo and a 2-D secant solve (CALC)."""
    global _DP_CAL
    if _DP_CAL is not None:
        return _DP_CAL
    rng = np.random.default_rng(seed)
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    a1, a2 = rng.uniform(0, 2 * np.pi, n), rng.uniform(0, 2 * np.pi, n)
    tgt = np.array([val(SENSORS["page_err_window_median"]), val(SENSORS["page_err_window_mean"])])

    def stats(lm, s):
        m = math.exp(lm)
        r1, r2 = m * np.exp(s * z1), m * np.exp(s * z2)
        dx = r1 * np.cos(a1) - r2 * np.cos(a2)
        dy = r1 * np.sin(a1) - r2 * np.sin(a2)
        dd = np.hypot(dx, dy)
        return np.array([np.median(dd), dd.mean()])
    x = np.array([math.log(18e-6), 1.3])
    for _ in range(30):
        f0 = np.log(stats(*x)) - np.log(tgt)
        if np.max(np.abs(f0)) < 1e-4:
            break
        J = np.zeros((2, 2))
        for j in range(2):
            h = np.zeros(2); h[j] = 1e-4
            J[:, j] = (np.log(stats(*(x + h))) - np.log(tgt) - f0) / 1e-4
        x = x - np.linalg.solve(J, f0)
    st = stats(*x)
    _DP_CAL = {"median_m": math.exp(x[0]), "sigma": float(x[1]), "window_diff_median_um": st[0] * 1e6,
               "window_diff_mean_um": st[1] * 1e6, "label": "CALC (Monte Carlo fit to LIT OPT-02)"}
    return _DP_CAL


class DeltaPenSensors(OnlineSensors):
    """sim2j's online sensors with the page reading's error replaced by the DeltaPen-calibrated model (see the module
    docstring); mode 'ideal' keeps sim2's 3 um white noise (the labelled bound)."""

    def __init__(self, pm, Ts=0.5e-3, seed=0, noise_scale=1.0, mode: str = "deltapen"):
        super().__init__(pm, Ts, seed=seed, noise_scale=noise_scale, page_error="white")
        self.mode = mode
        self.cal = deltapen_calibration()
        self._r = np.random.default_rng(seed + 7_777_777)
        self._e = np.zeros(2)
        self._drift = np.zeros(2)
        self._vd = np.zeros(2)
        self._gain = self._r.normal(0.0, 0.012 / 0.6745, 2)            # median |g| = 1.2 % (OPT-75)
        self._p0 = None
        self._tau_d = 2.0
        self._sd_v = val(SENSORS["page_idle_drift"])
        if mode == "ideal":
            return
        self.page_noise = 0.0                                            # the model replaces the white noise

    def read(self, t: float) -> Dict:
        out = super().read(t)
        if self.mode == "ideal" or "page" not in out:
            return out
        k = self.k - 1
        Tp = 1e-3
        a = math.exp(-Tp / self._tau_d)
        self._vd = a * self._vd + self._sd_v * math.sqrt(1 - a * a) * self._r.standard_normal(2)
        self._drift = self._drift + self._vd * Tp
        if k % self._pe_n == 0:
            mag = self.cal["median_m"] * math.exp(self.cal["sigma"] * self._r.standard_normal())
            ang = self._r.uniform(0.0, 2.0 * math.pi)
            self._e = np.array([mag * math.cos(ang), mag * math.sin(ang)])
        ts, tav, (x, y), ok = out["page"]
        if self._p0 is None:
            self._p0 = np.array([x, y])
        gx = self._gain[0] * (x - self._p0[0])
        gy = self._gain[1] * (y - self._p0[1])
        out["page"] = (ts, tav, (x + self._e[0] + self._drift[0] + gx, y + self._e[1] + self._drift[1] + gy), ok)
        return out


# ================================================================================================ servos
class FilteredServo(S.NoseServo):
    """Translation nib (virtual pivot): tip coordinates x_i = sgn_i z_p a_i (sgn = -1, +1).  Per axis:
        observer   xh' = vh + l1 (y - xh),  vh' = (F - k xh - c vh)/m + l2 (y - xh)   (poles at w_o, zeta 0.8; y = the
                   Hall reading, noisy and delayed; F = the force commanded)
        control    F = m a_d + k x_d + c v_d + Kp (x_d - xh) + Kd (v_d - vh) + Ki int(x_d - xh) [+ bias (B2)]
                   Kp = m w_i^2, Kd = 1.6 m w_i, Ki = Kp 2 pi 10 Hz; F x g (governor)
        coil       I = F / K_f through sim2's Coil limits (1.5 A, 3.7 V headroom with R(T) and back-EMF)
        thermal    two nodes (coil, shell) with the copper loss of both coils; governor g = min(1, g_c, g_s)."""

    def __init__(self, pm, *a, tn: Optional[TH.TwoNode] = None, governor: bool = True, T0=None, **kw):
        super().__init__(pm, *a, **kw)
        nz = self.nz
        zp = self.zp
        self.m_t = self.I / zp ** 2
        self.k_t = self.kr / zp ** 2
        self.c_t = self.c_flex / zp ** 2
        wi = 2 * math.pi * nz.inner_hz
        wo = wi * pm.info.get("obs_mult", 3.0)
        self.Kp_t = self.m_t * wi * wi
        self.Kd_t = 1.6 * self.m_t * wi
        self.Ki_t = self.Kp_t * 2 * math.pi * 10.0
        self.l1 = 1.6 * wo
        self.l2 = wo * wo
        self.xh = [0.0, 0.0]
        self.vh = [0.0, 0.0]
        self.F_last = [0.0, 0.0]
        self.eiT = [0.0, 0.0]
        self.K_f = pm.info["K_f"]
        self.F_bias = self.tau_bias / zp if nz.bias else 0.0
        self.tn = tn
        self.governor = governor
        T0c, T0s = (tn.T_room, tn.T_room) if (tn is not None and T0 is None) else (T0 or (25.0, 25.0))
        self.Tc, self.Ts = T0c, T0s
        self.g = 1.0
        self.hb = [[0.0] * (len(self.hbuf[0])), [0.0] * (len(self.hbuf[0]))]
        self.P_sum = 0.0
        self.n_P = 0

    def servo_tick(self, Ts: float, contact_gate: float):
        if not self.on:
            return
        d = self.pm.d
        zp = self.zp
        nz = self.nz
        # governor from the two-node temperatures
        if self.tn is not None and self.governor:
            gc = min(max((self.tn.T_c_max - 10.0 - self.Tc) / 10.0, 0.0), 1.0) ** 0.5
            gs = min(max((self.tn.T_s_target - self.Ts) / 1.5, 0.0), 1.0) ** 0.5
            self.g = min(1.0, gc, gs)
        for i in (0, 1):
            sgn = -1.0 if i == 0 else 1.0
            x_true = sgn * zp * d.qpos[self.qa[i]]
            y = x_true + (self.rng.standard_normal() * nz.hall_noise if nz.hall_noise > 0 else 0.0)
            buf = self.hb[i]
            buf[self.hk % len(buf)] = y
            y_d = buf[(self.hk + 1) % len(buf)] if len(buf) > 1 else y
            # observer (explicit, at the servo rate)
            eo = y_d - self.xh[i]
            xh = self.xh[i] + Ts * (self.vh[i] + self.l1 * eo)
            vh = self.vh[i] + Ts * ((self.F_last[i] - self.k_t * self.xh[i] - self.c_t * self.vh[i]) / self.m_t + self.l2 * eo)
            self.xh[i], self.vh[i] = xh, vh
            xd, vd, ad = self.qd[i], self.qdv[i], self.qdd[i]
            e = xd - xh
            self.eiT[i] += e * Ts
            F = (self.m_t * ad + self.k_t * xd + self.c_t * vd + self.Kp_t * e + self.Kd_t * (vd - vh)
                 + self.Ki_t * self.eiT[i])
            if i == 0 and self.F_bias:
                F += self.F_bias * contact_gate
            F *= self.g
            I_cmd = sgn * F / self.K_f
            vm = d.qvel[self.va[i]] * self.pm.info["coil_arm"]
            I_lim = self.coils[i].limit(I_cmd, vm)
            if I_lim != I_cmd:
                self.eiT[i] -= e * Ts
            self.F_last[i] = sgn * I_lim * self.K_f
            self.Icmd[i] = I_lim
            d.ctrl[self.act[i]] = I_lim
        self.hk += 1
        if self.adaptive_stop:
            q1 = -zp * d.qpos[self.qa[0]]
            self.pm.m.jnt_range[self.j_refill, 0] = q1 * self.cot - self.margin
        P = 0.0
        for i in (0, 1):
            Ia = d.act[self.pm.m.actuator_actadr[self.act[i]]]
            P += Ia * Ia * self.coils[i].R()
        if self.tn is not None:
            tn = self.tn
            self.Tc += Ts * (P - (self.Tc - self.Ts) / tn.R_cs) / tn.C_c
            self.Ts += Ts * ((self.Tc - self.Ts) / tn.R_cs - (self.Ts - tn.T_room) / tn.R_sa) / tn.C_s
            for c in self.coils:
                c.T = self.Tc
        self.P_cu = P
        self.P_sum += P
        self.n_P += 1


class PiezoServo(S.NoseServo):
    """Piezo bender stage on sim2's gimbal (rear pivot z_g): the plates are the joint stiffness k_tip z_g^2; the
    'actuator' adds k_tip u (u = the free displacement set by the voltage, |u| <= free stroke).
        u = x_d + integral(Ki (x_d - x_f)) - K_v v_f        (x_f, v_f: the Hall reading filtered at 2 kHz and its
                                                              rate; K_v = 2 zeta_a sqrt(m / k) adds damping zeta_a 0.5
                                                              to the plates' lightly damped resonance)
    The static load is held by the voltage offset (the integral).  Rail power: the pencil study's recovery
    convention, (1/eta - eta) V_mean C_axis sum(dV+) / T per axis (docs/opt_hardware.md A7)."""

    def __init__(self, pm, *a, k_tip: float = 1000.0, x_free: float = 0.4e-3, C_axis: float = 4.8e-6, **kw):
        super().__init__(pm, *a, **kw)
        self.k_tip = k_tip
        self.x_free = x_free
        self.C_axis = C_axis
        self.u = [0.0, 0.0]
        self.eiP = [0.0, 0.0]
        self.xf = [0.0, 0.0]
        self.xf_prev = [0.0, 0.0]
        self.vf = [0.0, 0.0]
        Tsv = 1.0 / self.nz.servo_rate
        self.a_f = 1.0 - math.exp(-2 * math.pi * 2000.0 * Tsv)
        self.a_v = 1.0 - math.exp(-2 * math.pi * 500.0 * Tsv)
        self.a_drv = 1.0 - math.exp(-2 * math.pi * 1500.0 * Tsv)        # driver output bandwidth (ASSUMPTION)
        self.u_app = [0.0, 0.0]
        m_t = self.I / self.zp ** 2
        self.K_v = 2 * 0.5 * math.sqrt(m_t / k_tip)
        self.Ki_p = 2 * math.pi * 15.0
        self.V_prev = [30.0, 30.0]
        self.dVpos = [0.0, 0.0]
        self.t_acc = 0.0
        self.sat_n = 0
        self.n_tick = 0
        self.hb = [[0.0] * (len(self.hbuf[0])), [0.0] * (len(self.hbuf[0]))]
        self.P_cu = 0.0

    def servo_tick(self, Ts: float, contact_gate: float):
        if not self.on:
            return
        d = self.pm.d
        zp = self.zp
        nz = self.nz
        for i in (0, 1):
            sgn = -1.0 if i == 0 else 1.0
            x_true = sgn * zp * d.qpos[self.qa[i]]
            y = x_true + self.rng.standard_normal() * nz.hall_noise
            buf = self.hb[i]
            buf[self.hk % len(buf)] = y
            y_d = buf[(self.hk + 1) % len(buf)] if len(buf) > 1 else y
            self.xf[i] += self.a_f * (y_d - self.xf[i])
            self.vf[i] += self.a_v * ((self.xf[i] - self.xf_prev[i]) / Ts - self.vf[i])
            self.xf_prev[i] = self.xf[i]
            xd = self.qd[i]
            de = self.Ki_p * (xd - self.xf[i]) * Ts
            self.eiP[i] += de
            u = xd + self.eiP[i] - self.K_v * self.vf[i]
            if abs(u) > self.x_free:
                self.eiP[i] -= de
                u = math.copysign(self.x_free, u)
                self.sat_n += 1
            self.u_app[i] += self.a_drv * (u - self.u_app[i])
            ua = self.u_app[i]
            self.u[i] = ua
            # joint torque k_r sgn u / z_p through the unit-gear 'coil': ctrl = torque / gear
            d.ctrl[self.act[i]] = sgn * self.k_tip * ua * zp / self.pm.info["K_f"] / self.pm.info["coil_arm"]
            V = 30.0 + 30.0 * ua / self.x_free
            dv = V - self.V_prev[i]
            if dv > 0:
                self.dVpos[i] += dv
            self.V_prev[i] = V
        self.hk += 1
        self.n_tick += 1
        self.t_acc += Ts
        if self.adaptive_stop:
            q1 = -zp * d.qpos[self.qa[0]]
            self.pm.m.jnt_range[self.j_refill, 0] = q1 * self.cot - self.margin

    def rail_power(self) -> float:
        eta = val(PIEZO["eta_rec"])
        if self.t_acc <= 0:
            return 0.0
        return sum((1.0 / eta - eta) * val(PIEZO["V_mean"]) * self.C_axis * dv / self.t_acc for dv in self.dVpos)


# ================================================================================================ per-step kernel
@njit(cache=True)
def _nib_kernel(xpos, xmat, xipos, xfrc, br, bh, bn, nfw, p_st, F_n, ramp, L_end, w_nose, w_ref, seat_F, s, s_lo,
                seat_d, out):
    """Counter-face force on the refill's rear end (+ reaction on the handle), seat spring, weights.  nfw: the face
    normal in the world frame; p_st: the stop's position along it from the handle origin."""
    # refill rear end (refill frame: origin at the ball, z along the pen axis)
    ax = xmat[br, 2]; ay = xmat[br, 5]; az = xmat[br, 8]
    ex = xpos[br, 0] + L_end * ax; ey = xpos[br, 1] + L_end * ay; ez = xpos[br, 2] + L_end * az
    xe = (ex - xpos[bh, 0]) * nfw[0] + (ey - xpos[bh, 1]) * nfw[1] + (ez - xpos[bh, 2]) * nfw[2]
    F = 0.0
    if F_n > 0.0:
        pen = xe - p_st
        if pen > 0.0:
            F = F_n * min(pen / ramp, 1.0)
    fx = -F * nfw[0]; fy = -F * nfw[1]; fz = -F * nfw[2]
    # seat spring near the front stop: along -a on the refill, reaction on the nose (carrier)
    Fs = 0.0
    if seat_F > 0.0:
        r = (s_lo + seat_d - s) / seat_d
        if r > 0.0:
            Fs = seat_F * min(r, 1.0)
    gx = -Fs * ax; gy = -Fs * ay; gz = -Fs * az
    # refill: face + seat + weight
    rx = ex - xipos[br, 0]; ry = ey - xipos[br, 1]; rz = ez - xipos[br, 2]
    xfrc[br, 0] += fx + gx; xfrc[br, 1] += fy + gy; xfrc[br, 2] += fz + gz - w_ref
    xfrc[br, 3] += ry * fz - rz * fy
    xfrc[br, 4] += rz * fx - rx * fz
    xfrc[br, 5] += rx * fy - ry * fx
    # handle: face reaction at the same point
    hx = ex - xipos[bh, 0]; hy = ey - xipos[bh, 1]; hz = ez - xipos[bh, 2]
    xfrc[bh, 0] -= fx; xfrc[bh, 1] -= fy; xfrc[bh, 2] -= fz
    xfrc[bh, 3] -= hy * fz - hz * fy
    xfrc[bh, 4] -= hz * fx - hx * fz
    xfrc[bh, 5] -= hx * fy - hy * fx
    # nose: seat reaction and weight (set, not added: the contact law does not clear this body)
    xfrc[bn, 0] = -gx; xfrc[bn, 1] = -gy; xfrc[bn, 2] = -gz - w_nose
    xfrc[bn, 3] = 0.0; xfrc[bn, 4] = 0.0; xfrc[bn, 5] = 0.0
    out[0] = F; out[1] = xe; out[2] = Fs


# ================================================================================================ stepper
XB = ["Fface", "xe", "pst", "Fseat", "mu_b", "Tc2", "Ts2", "gov", "ux", "uy"]


class BStepper(SJ.RevJStepper):
    """sim2j's stepper (a copy of its step with this study's insertions marked; the heel wheel is absent)."""

    def __init__(self, pm, scn, fw, sd: SimDesign, task=None, seed: int = 0, page_mode: str = "deltapen",
                 ink: str = "oil_common", paper: float = 1.0, face_err=(0.0, 0.0), tn: Optional[TH.TwoNode] = None,
                 governor: bool = True, T0=None, t_end=None, record: bool = True):
        super().__init__(pm, scn, fw, task, mu=0.9, seed=seed, t_end=t_end, record=record)
        self.sd = sd
        cfg = pm.cfg
        # ---- the nib's servo replaces sim2's
        if sd.family == "translation":
            pm.info["obs_mult"] = sd.obs_mult
            self.servo = FilteredServo(pm, "neutral", None, None, self.opt.policy, seed=seed, tn=tn, governor=governor, T0=T0)
        else:
            pz = sd.ev["piezo"]
            self.servo = PiezoServo(pm, "neutral", None, None, self.opt.policy, seed=seed, k_tip=pz["tip_k_N_m"],
                                    x_free=pz["tip_free_stroke_mm"] * 1e-3, C_axis=pz["C_per_axis_uF"] * 1e-6)
        # ---- page sensor
        self.fw.sens = DeltaPenSensors(pm, self.fw.Ts, seed=fw.seed + 11, noise_scale=fw.imu_noise, mode=page_mode)
        # ---- friction map
        self.ink, self.paper = ink, paper
        self.ms = cfg.contact.ms_ratio
        self.xpre = cfg.contact.presliding
        self.Nf, self.vf = 0.2, 0.0
        self.mu_b = 0.15
        self._set_mu(C.mu_kinetic(ink, 15e-3, 0.2, paper))
        # ---- counter-face, seat spring, weights
        self.br, self.bh, self.bn = pm.ids["body:refill"], pm.ids["body:handle"], pm.ids["body:nose"]
        self.w_nose = pm.info["nose"]["m"] * G0
        self.w_ref = pm.info["refill"]["m"] * G0
        th = cfg.geom.theta_deg * D2R
        self.F_n = sd.F_s / math.sin(th) if sd.counterface else 0.0
        self.seat_F = sd.seat_F if sd.counterface else 0.0
        self.face_err = face_err
        m_comp = pm.info["bnib"]["m_tip_equiv_g"] * 1e-3
        self.w_comp = -m_comp * G0 / sd.F_s
        self.nfh = self._face_normal_h(None)
        self.nfw = np.zeros(3)
        self.kout = np.zeros(3)
        self.p_st = None
        self.a_face = 1.0 - math.exp(-0.5e-3 / sd.face_tau)
        self.a_sched = 1.0 - math.exp(-0.5e-3 / 0.2)
        self.nh_f = None
        self.brec = np.zeros((self.nrec, len(XB))) if record else None

    # -- face schedule: the paper normal in the handle frame (IMU estimate, low-passed by the slow positioner), rotated
    #    by the per-run tilt and roll errors, plus the weight term
    def _face_normal_h(self, nh):
        if nh is None:
            Rh = self.d.xmat[self.pm.ids["body:handle"]].reshape(3, 3)
            nh = Rh.T @ np.array([0.0, 0.0, 1.0])
        dth, dph = self.face_err
        # tilt error: rotate about the handle's y axis (t2); roll error: about z (the pen axis)
        cy, sy = math.cos(dth), math.sin(dth)
        n1 = np.array([cy * nh[0] + sy * nh[2], nh[1], -sy * nh[0] + cy * nh[2]])
        cz, sz = math.cos(dph), math.sin(dph)
        n2 = np.array([cz * n1[0] - sz * n1[1], sz * n1[0] + cz * n1[1], n1[2]])
        a = np.array([0.0, 0.0, 1.0])
        sth = max(n2[2], 0.1)
        nperp = n2 - n2[2] * a
        v = a + (1.0 / sth + self.w_comp) * nperp
        return v / np.linalg.norm(v)

    def _set_mu(self, mu):
        law = self.law
        law.tab[1, K_MUK] = mu
        law.tab[1, K_MUS] = mu * self.ms
        law.tab[1, K_SG0] = mu * self.ms / self.xpre
        self.mu_b = mu

    def _tick_extra(self):
        """2 kHz: friction map, face schedule, follower stop."""
        d = self.d
        ko = self.law.kout
        N = ko[1, 0]
        v = math.hypot(ko[1, 6], ko[1, 7])
        self.Nf += 0.2 * (N - self.Nf)
        self.vf += 0.2 * (v - self.vf)
        if N > 0:
            self._set_mu(C.mu_kinetic(self.ink, max(self.vf, 1e-4), max(self.Nf, 0.02), self.paper))
        if self.F_n > 0:
            Rh = d.xmat[self.bh].reshape(3, 3)
            nh = Rh.T @ np.array([0.0, 0.0, 1.0])
            self.nh_f = nh.copy() if self.nh_f is None else self.nh_f + self.a_sched * (nh - self.nh_f)
            self.nfh = self._face_normal_h(self.nh_f)
            self.nfw[:] = Rh @ self.nfh
            xe = self.kout[1]
            if self.p_st is None:
                self.p_st = xe - self.sd.face_gap
            elif self.cont["Nb"] > 0.0:
                self.p_st += self.a_face * ((xe - self.sd.face_gap) - self.p_st)

    def step(self):
        k = self.k
        m, d, pm, opt, servo = self.m, self.d, self.pm, self.opt, self.servo
        dt = self.dt
        mujoco.mj_step1(m, d)
        d.ctrl[self.hidx] = self.hctl[k]
        self.law.forces(self.fpush[k])
        # ---- insertion 1 (bnib): counter-face, seat spring, weights (every physics step)
        if self.F_n > 0 and self.p_st is None:
            Rh = d.xmat[self.bh].reshape(3, 3)
            self.nfw[:] = Rh @ self.nfh
            _nib_kernel(d.xpos, d.xmat, d.xipos, d.xfrc_applied, self.br, self.bh, self.bn, self.nfw, 1e9, 0.0, 1.0,
                        L_END, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, self.kout)
            self.p_st = self.kout[1] - self.sd.face_gap
        s = d.qpos[self.js]
        s_lo = m.jnt_range[self.j_refill, 0]
        _nib_kernel(d.xpos, d.xmat, d.xipos, d.xfrc_applied, self.br, self.bh, self.bn, self.nfw,
                    self.p_st if self.p_st is not None else 1e9, self.F_n, self.sd.face_ramp, L_END, self.w_nose,
                    self.w_ref, self.seat_F, s, s_lo, self.sd.seat_d, self.kout)
        if k % self.rdec == 0:
            self.cont = self.law.summary()
            in_c = self._update_flag()
            self._in_c = in_c
            self._tick_extra()
            tip = d.site_xpos[self.s_tip]
            direct = opt.policy(k * dt, pm, servo)
            servo.ref_tick(k * dt, self.tick, tip, in_c, direct_q=direct)
            self.gate = servo.g_eff
            self.tick += 1
        if k % self.sdec == 0:
            servo.servo_tick(self.sdec * dt, self.gate)
            servo.follower_steps(self.sdec)
        if self.rec is not None and k % self.recdec == 0 and self.ri < self.nrec:
            self.cont = self.law.summary()
            self._xrecord()
            self._brecord()
            self._record(k)
        mujoco.mj_step2(m, d)
        if not np.isfinite(d.qacc[0]):
            raise FloatingPointError(f"simulation diverged at t = {k * dt:.4f} s")
        self.k += 1

    def _brecord(self):
        if self.brec is None or self.ri >= self.nrec:
            return
        r = self.brec[self.ri]
        sv = self.servo
        r[0] = self.kout[0]; r[1] = self.kout[1]; r[2] = self.p_st if self.p_st is not None else 0.0
        r[3] = self.kout[2]; r[4] = self.mu_b
        if isinstance(sv, FilteredServo):
            r[5] = sv.Tc; r[6] = sv.Ts; r[7] = sv.g
        if isinstance(sv, PiezoServo):
            r[8] = sv.u[0]; r[9] = sv.u[1]

    def result(self):
        res = super().result()
        n = res.rec.shape[0]
        if self.brec is not None:
            res.rec = np.hstack([res.rec, self.brec[:n]])
            res.names = res.names + XB
            res.idx = {nm: i for i, nm in enumerate(res.names)}
        sv = self.servo
        if isinstance(sv, PiezoServo):
            res.info["piezo_rail_W"] = sv.rail_power()
            res.info["piezo_sat_share"] = sv.sat_n / max(2 * sv.n_tick, 1)
        if isinstance(sv, FilteredServo):
            res.info["T_end"] = (sv.Tc, sv.Ts)
        return res


def run(pm, scn, fw, sd: SimDesign, task=None, seed: int = 0, **kw):
    st = BStepper(pm, scn, fw, sd, task, seed=seed, **kw)
    st.advance(st.n)
    return st.result()


# ================================================================================================ writer set-up
class Pens:
    def __init__(self, designs: Dict[str, SimDesign], dt: float = DT):
        self.designs = designs
        self.dt = dt
        self.pms = {}

    def get(self, name: str, theta: float = 50.0):
        key = (name, theta)
        if key not in self.pms:
            self.pms[key] = build(self.designs[name], theta, self.dt)
        return self.pms[key]


def case_env(w: int, seed: int) -> Dict:
    """Per (writer, seed): ink, paper factor and the face's sensing errors (ASSUMPTION draws, labels.FRICTION/SENSORS)."""
    rng = np.random.default_rng(770_000 + 1000 * w + seed)
    ink = ("oil_common", "gel")[int(rng.integers(2))]
    paper = float(rng.uniform(*val(FRICTION["paper_spread"])))
    face_err = (float(rng.normal(0, val(SENSORS["tilt_err_sd"]))), float(rng.normal(0, val(SENSORS["roll_err_sd"]))))
    return {"ink": ink, "paper": paper, "face_err": face_err}


def fw_config(ctl: str, seed: int, w: int):
    """'none' (nib held centred), 'nose' (sim2j's frozen guarded tracker), 'oracle' (perfect knowledge of the handle's
    tremor: the mechanism's limit, H1 stage_src 0)."""
    return ET.controller(ctl, seed=seed * 7 + w)


class Setup:
    """sim2j.et.WriterSetup's logic (a copy: adapted hand path by iterative learning on the tremor-free run with the
    nib off, the clean-ink reference letters, the metrics) for this study's pens; caches in bnib/build/setups."""

    def __init__(self, w: int, pens: Pens, name: str, theta: float = 50.0, text: str = TEXT, pre_s: float = PRE_S,
                 n_adapt: int = 3, log=print):
        self.w, self.name, self.theta, self.text = w, name, theta, text
        self.case_pre_s = pre_s
        self.sd = pens.designs[name]
        self.pm = pens.get(name, theta)
        self.case = TK.WriterCase(w, version="v2", text=text, pre_s=pre_s)
        t0 = time.time()
        cache = self._cache_path(n_adapt, pre_s)
        if cache.exists():
            z = np.load(cache)
            self.case.hand_path = z["hand_path"]
            self.adapt_hist = [float(v) for v in z["adapt_hist"]]
        else:
            self.adapt_hist = self._adapt(n_adapt)
            np.savez(cache, hand_path=self.case.hand_path, adapt_hist=np.array(self.adapt_hist))
        self.clean_runs = {}
        env = case_env(w, 0)
        self.clean = self.run("none", seed=0, env=env)
        self.ref_polys = ET.clean_letters(self.case.written, self.clean)
        rows = MT.letter_rows(self.case.written, TK.Res(self.clean), self.case.rec)
        s = MT.summary(rows)
        wd = MT.words(rows, text)
        self.clean_floor = {"ink_to_intended_um": s.get("path_rms_um"), "letters_read": s.get("recognition_accuracy"),
                            "words_app": wd.get("word_accuracy_app"), "adapt_hist_um": self.adapt_hist}
        log(f"[sim] setup {name} w{w} theta {theta:g}: adaptation {['%.0f' % h for h in self.adapt_hist]} um, "
            f"floor {self.clean_floor['ink_to_intended_um']:.0f} um ({time.time() - t0:.0f} s)")

    def _cache_path(self, n_adapt, pre_s):
        import hashlib
        pm = self.pm
        nz = replace(pm.cfg.nose, inner_hz=0.0)          # the adapted path is shared across the tuned servo/face settings
        key = f"{self.w}|{self.text}|{self.name}|{pm.cfg.label}|{pm.m.opt.timestep}|{n_adapt}|{pre_s}|{nz}|" \
              f"{pm.cfg.refill}|{pm.cfg.geom}"
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        SETUPS.mkdir(parents=True, exist_ok=True)
        return SETUPS / f"setup_{self.name}_w{self.w}_{h}.npz"

    def run(self, ctl: str, seed: int, env: Dict, tremor=None, page_mode: str = "deltapen", ref_none=None, **kw):
        scn = self.case.scenario(tremor=tremor, theta_deg=self.theta)
        fw = fw_config(ctl, seed, self.w)
        task = None
        if ctl == "oracle":
            nz = self.pm.cfg.nose
            gd = 2 * nz.servo_zeta / (2 * math.pi * nz.servo_hz) + 0.25e-3
            task = {"oracle_d": ET.oracle_table(ref_none, self.clean, int(len(self.case.t) * SIM_DT / 0.5e-3) + 10, gd)}
        return run(self.pm, scn, fw, self.sd, task=task, seed=seed, page_mode=page_mode, ink=env["ink"], paper=env["paper"],
                   face_err=env["face_err"], tn=self._tn(), **kw)

    def _tn(self):
        ev = self.sd.ev
        if self.sd.family != "translation":
            return None
        g = self.sd.design.grip
        return TH.model_for(g.od, max(ev["hw"]["L_src"], 5e-3), ev["hw"]["m_cu"], spreader=TH.GRAPHITE_30, wall=g.wall)

    def _adapt(self, n_iter):
        case = self.case
        m = case.written.intended.pen_down
        sos = butter(2, 10.0, fs=1.0 / SIM_DT, output="sos")
        hist = []
        v = np.gradient(case.intended, SIM_DT, axis=0)
        env = case_env(self.w, 0)
        for it in range(n_iter):
            r = self.run("none", seed=0, env=env)
            ink = np.column_stack([np.interp(case.t, r["t"], r.ink()[:, j]) for j in range(2)])
            e = ink - case.intended
            hist.append(float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6))
            lag = max(0.0, float(-np.sum(e[m] * v[m]) / max(np.sum(v[m] * v[m]), 1e-30)))
            kk = int(round(lag / SIM_DT))
            ea = np.vstack([e[kk:], np.repeat(e[-1:], kk, 0)]) if kk > 0 else e
            case.hand_path = case.hand_path - 0.9 * sosfiltfilt(sos, ea, axis=0)
        return hist

    def clean_ref(self, seed: int, env: Dict):
        if seed not in self.clean_runs:
            self.clean_runs[seed] = self.run("none", seed=seed, env=env)
        return self.clean_runs[seed]

    def metrics(self, r, ref_none=None, clean_ref=None) -> Dict:
        R = TK.Res(r)
        rows = MT.letter_rows(self.case.written, R, self.case.rec, target_polys=self.ref_polys)
        s = MT.summary(rows)
        wd = MT.words(rows, self.text)
        out = {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"),
               "letters_read": s.get("recognition_accuracy"), "words_app": wd.get("word_accuracy_app"),
               "recognised": " ".join(wd["recognised"])}
        rows_i = MT.letter_rows(self.case.written, R, self.case.rec)
        out["ink_err_intended_um"] = MT.summary(rows_i).get("path_rms_um")
        if clean_ref is not None:
            out["moved_vs_clean_um"] = TK.moved(r, clean_ref)
        if ref_none is not None:
            out.update(TK.device_effect(r, ref_none))
        out.update(power_summary(r, self.sd))
        c = r["contact"] > 0.5
        out["contact_share"] = float(np.mean(c[r["t"] > 0.3]))
        return out


def power_summary(r, sd: SimDesign) -> Dict:
    """Mean nib power (SIM) and the battery time for the grip class (CALC on SIM): copper loss (translation) or the
    recovery driver's rail power (piezo), electronics (candidates' grip), the face positioners' 2 mW (B1)."""
    t = r["t"]
    m = t > 0.3
    g = sd.design.grip
    if sd.family == "translation":
        P_nib = float(np.mean(r["Pcu"][m]))
        P_bat_nib = P_nib / val(DRIVE["driver_eff"])
    else:
        P_nib = float(r.info.get("piezo_rail_W", 0.0))
        P_bat_nib = 2 * 0 + P_nib / val(PIEZO["eta_boost"]) + val(PIEZO["boost_Iq_W"])
    P_aux = 0.002 if sd.counterface else 0.0
    P_tot = g.electronics_W + P_bat_nib + P_aux
    out = {"P_nib_W": P_nib, "P_battery_W": P_tot, "battery_h": g.cell_Wh / P_tot}
    if "Tc2" in r.idx and sd.family == "translation":
        out["T_coil_end_C"] = float(r["Tc2"][-1])
        out["T_skin_end_C"] = float(r["Ts2"][-1])
        out["gov_min"] = float(np.min(r["gov"][m])) if m.any() else 1.0
    if "Fface" in r.idx and sd.counterface:
        c = r["contact"] > 0.5
        out["face_engaged_in_contact"] = float(np.mean(r["Fface"][c] > 0.5 * sd.F_s)) if c.any() else float("nan")
        out["face_engaged_penup"] = float(np.mean(r["Fface"][~c] > 0.01)) if (~c).any() else float("nan")
    if sd.family == "piezo":
        out["piezo_sat_share"] = float(r.info.get("piezo_sat_share", 0.0))
    return out


# ================================================================================================ rows cache
class Rows:
    def __init__(self, path=ROWS):
        self.path = path
        self.rows = json.load(open(path)) if os.path.exists(path) else {}
        self._n = 0

    def has(self, k):
        return k in self.rows

    def put(self, k, row):
        self.rows[k] = {kk: v for kk, v in row.items() if not kk.startswith("_")}
        self._n += 1
        if self._n % 2 == 0:
            self.save()

    def save(self):
        cache_path(os.path.basename(str(self.path)))
        tmp = str(self.path) + ".tmp"
        json.dump(self.rows, open(tmp, "w"), default=float)
        os.replace(tmp, self.path)


def _tremor(case, kind, f0, amp, seed):
    kw = PD_KW if kind == "PD" else {}
    return case.tremor(f0, amp, seed, **kw)


def run_cell(su: Setup, rows: Rows, prefix: str, kind: str, f0: float, amp: float, seed: int, ctls=("none", "nose"),
             page_mode: str = "deltapen", log=print):
    env = case_env(su.w, seed)
    cell = f"{prefix}|{su.name}|{kind}|{f0:g}|{amp * 1e3:g}|{su.w}|{seed}|{page_mode}|"
    if all(rows.has(cell + c) for c in ctls):
        return
    tr = _tremor(su.case, kind, f0, amp, seed)
    t0 = time.time()
    rn = su.run("none", seed, env, tremor=tr, page_mode=page_mode)
    mn = su.metrics(rn)
    rows.put(cell + "none", dict(mn, kind=kind, f0=f0, amp_mm=amp * 1e3, w=su.w, seed=seed, ctl="none", design=su.name,
                                 page=page_mode, env=env))
    for ctl in ctls:
        if ctl == "none":
            continue
        r = su.run(ctl, seed, env, tremor=tr, page_mode=page_mode, ref_none=rn)
        mm = su.metrics(r, ref_none=rn)
        mm.update({"kind": kind, "f0": f0, "amp_mm": amp * 1e3, "w": su.w, "seed": seed, "ctl": ctl, "design": su.name,
                   "page": page_mode, "env": env, "none_ink_err_um": mn["ink_err_um"],
                   "ratio": mm["ink_err_um"] / max(mn["ink_err_um"], 1e-9),
                   "none_words_app": mn["words_app"]})
        rows.put(cell + ctl, mm)
    log(f"[sim] {prefix} {su.name} w{su.w} s{seed} {kind} {f0:g} Hz {amp * 1e3:g} mm ({page_mode}): none "
        f"{mn['ink_err_um']:.0f} um -> nib {rows.rows[cell + 'nose']['ink_err_um']:.0f} um, words "
        f"{mn['words_app']:.2f} -> {rows.rows[cell + 'nose']['words_app']:.2f}, P {rows.rows[cell + 'nose']['P_nib_W'] * 1e3:.1f} mW"
        f" ({time.time() - t0:.0f} s)")


def run_clean(su: Setup, rows: Rows, prefix: str, seed: int, page_mode: str = "deltapen", log=print):
    key = f"{prefix}|{su.name}|clean|{su.w}|{seed}|{page_mode}|nose"
    if rows.has(key):
        return
    env = case_env(su.w, seed)
    ref = su.clean_ref(seed, env)
    r = su.run("nose", seed, env, page_mode=page_mode)
    m = su.metrics(r, clean_ref=ref)
    mr = su.metrics(ref)
    m.update({"kind": "clean", "w": su.w, "seed": seed, "ctl": "nose", "design": su.name, "page": page_mode, "env": env,
              "none_P_nib_W": mr["P_nib_W"], "none_words_app": mr["words_app"], "none_battery_h": mr["battery_h"]})
    rows.put(key, m)
    log(f"[sim] {prefix} {su.name} w{su.w} s{seed} clean ({page_mode}): moved {m['moved_vs_clean_um']:.1f} um, P nib "
        f"{m['P_nib_W'] * 1e3:.1f} mW (off {mr['P_nib_W'] * 1e3:.1f})")


# ================================================================================================ stages
RULES = RESULTS / "rules.json"
TUNE_VARIANTS = ({"servo_fi": 70.0, "face_gap": 0.15e-3}, {"servo_fi": 100.0, "face_gap": 0.15e-3},
                 {"servo_fi": 150.0, "face_gap": 0.15e-3}, {"servo_fi": 100.0, "face_gap": 0.25e-3})


def frozen_rules() -> Optional[Dict]:
    if RULES.exists():
        return json.load(open(RULES))
    return None


def stage_tune(designs: Dict[str, SimDesign], rows: Rows, quick: bool = False, log=print) -> Dict:
    """Choose the servo bandwidth (B1/B2 share it) and the face gap (B1) on tuning writers 100-101, seed 300, cells ET
    8 Hz 1 mm and PD 5 Hz 1 mm + tremor-free writing.  Rule stated before running: the setting with the lowest mean ink
    error on the tremor cells among those whose tremor-free false correction is <= 25 um and whose nib power is within
    1.5 x the lowest; frozen in results/bnib/rules.json and never re-chosen once the test grid has started."""
    fr = frozen_rules()
    if fr is not None and not quick:
        log("[sim] rules frozen: " + json.dumps(fr["chosen"]))
        return fr
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS[:2]
    seed = TUNE_SEEDS[0]
    res = []
    for var in (TUNE_VARIANTS if not quick else TUNE_VARIANTS[1:2]):
        sd = replace(designs["B1"], **var)
        pens = Pens({"B1": sd})
        tag = f"tune|fi{var['servo_fi']:g}|gap{var['face_gap'] * 1e6:g}"
        errs, moved, pw = [], [], []
        for w in writers:
            su = Setup(w, pens, "B1", log=log)
            run_clean(su, rows, tag, seed, log=log)
            ck = f"{tag}|B1|clean|{w}|{seed}|deltapen|nose"
            moved.append(rows.rows[ck]["moved_vs_clean_um"])
            for kind, f0, amp in (TUNE_CELLS if not quick else TUNE_CELLS[:1]):
                run_cell(su, rows, tag, kind, f0, amp, seed, log=log)
                k = f"{tag}|B1|{kind}|{f0:g}|{amp * 1e3:g}|{w}|{seed}|deltapen|nose"
                errs.append(rows.rows[k]["ink_err_um"])
                pw.append(rows.rows[k]["P_nib_W"])
        rows.save()
        res.append({"servo_fi": var["servo_fi"], "face_gap_mm": var["face_gap"] * 1e3, "ink_err_um": float(np.mean(errs)),
                    "moved_um": float(np.mean(moved)), "P_nib_W": float(np.mean(pw))})
        log(f"[sim] tune {res[-1]}")
    Pmin = min(r["P_nib_W"] for r in res)
    ok = [r for r in res if r["moved_um"] <= 25.0 and r["P_nib_W"] <= 1.5 * Pmin] or res
    ch = min(ok, key=lambda r: r["ink_err_um"])
    out = {"chosen": {"servo_fi": ch["servo_fi"], "face_gap_mm": ch["face_gap_mm"]}, "grid": res,
           "rule": stage_tune.__doc__, "writers": list(writers), "seed": seed}
    if not quick:
        from . import write_json, provenance
        write_json(str(RULES), {"stabpen.provenance": provenance("SIMULATION (tuning set only)", seeds=[seed]), **out})
    return out


def apply_rules(designs: Dict[str, SimDesign], rules: Optional[Dict]) -> Dict[str, SimDesign]:
    if not rules:
        return designs
    ch = rules["chosen"]
    out = {}
    for k, sd in designs.items():
        kw = {"servo_fi": ch["servo_fi"]} if sd.family == "translation" else {}
        if sd.counterface:
            kw["face_gap"] = ch["face_gap_mm"] * 1e-3
        out[k] = replace(sd, **kw)
    return out


def _done(rows: Rows, prefix: str, name: str, w: int, seed: int, cells, ctls, page_mode: str = "deltapen") -> bool:
    """All rows of one (writer, design) block present: skip building its Setup (a resumed stage costs no sim time)."""
    keys = [f"{prefix}|{name}|clean|{w}|{seed}|{page_mode}|nose"]
    for kind, f0, amp in cells:
        keys += [f"{prefix}|{name}|{kind}|{f0:g}|{amp * 1e3:g}|{w}|{seed}|{page_mode}|{c}" for c in ("none",) + tuple(ctls)]
    return all(rows.has(k) for k in keys)


def stage_test(designs: Dict[str, SimDesign], rows: Rows, quick: bool = False, names=("B1", "B2", "B3"),
               writers=TEST_WRITERS, log=print) -> None:
    pens = Pens(designs)
    ws = writers[:1] if quick else writers
    cells = CELLS[3:4] if quick else CELLS
    for w in ws:                                  # writers outer: partial results cover every design
        for name in names:
            if w not in WRITERS_FOR.get(name, ws):
                continue
            seed = TEST_SEEDS[w % len(TEST_SEEDS)]
            if _done(rows, "test", name, w, seed, cells, ("nose", "oracle") if name in ("B1", "B3") else ("nose",)):
                continue
            su = Setup(w, pens, name, log=log)
            run_clean(su, rows, "test", seed, log=log)
            ctls = ("none", "nose", "oracle") if name in ("B1", "B3") else ("none", "nose")
            for kind, f0, amp in cells:
                run_cell(su, rows, "test", kind, f0, amp, seed, ctls=ctls, log=log)
            rows.save()


def stage_ideal(designs: Dict[str, SimDesign], rows: Rows, quick: bool = False, log=print) -> None:
    """The ideal page sensor (sim2's 3 um white noise) as a labelled bound: B1, writers 0-1, three cells."""
    pens = Pens(designs)
    for w in (TEST_WRITERS[:1] if quick else TEST_WRITERS[:2]):
        seed = TEST_SEEDS[w % len(TEST_SEEDS)]
        icells = (CELLS[3],) if quick else (CELLS[0], CELLS[3], CELLS[6])
        if _done(rows, "ideal", "B1", w, seed, icells, ("nose",), page_mode="ideal"):
            continue
        su = Setup(w, pens, "B1", log=log)
        run_clean(su, rows, "ideal", seed, page_mode="ideal", log=log)
        for kind, f0, amp in icells:
            run_cell(su, rows, "ideal", kind, f0, amp, seed, page_mode="ideal", log=log)
        rows.save()


def stage_travel(designs: Dict[str, SimDesign], rows: Rows, quick: bool = False, log=print) -> None:
    """Does B1's +-1.0 mm reach limit the correction?  B1w (the optimiser's counter-face point at the 1.5 mm travel
    floor, the same frozen rules) on writers 0-1 (their test seeds) in TRAVEL_CELLS with none / tracker / perfect
    knowledge, compared case by case with B1's test rows.  Added after the test grid had started (diagnosis of one
    case, SIM: in ET 8 Hz 1 mm the handle's tremor at the tip exceeds B1's reach 11 % of the time, p95 1.29 mm); it
    changes no rule and no B1 result."""
    if "B1w" not in designs:
        log("[sim] travel: no B1w design (the optimiser cache has no 1.5 mm point)")
        return
    pens = Pens({"B1w": designs["B1w"]})
    for w in (TEST_WRITERS[:1] if quick else TEST_WRITERS[:2]):          # writers 0-1 (shortened after container restarts)
        seed = TEST_SEEDS[w % len(TEST_SEEDS)]
        tcells = TRAVEL_CELLS[:1] if quick else TRAVEL_CELLS
        if _done(rows, "travel", "B1w", w, seed, tcells, ("nose", "oracle")):
            continue
        su = Setup(w, pens, "B1w", log=log)
        run_clean(su, rows, "travel", seed, log=log)
        for kind, f0, amp in tcells:
            run_cell(su, rows, "travel", kind, f0, amp, seed, ctls=("none", "nose", "oracle"), log=log)
        rows.save()


def oracle_diagnosis(designs: Dict[str, SimDesign], rows: Rows, name: str = "B1", w: int = 0,
                     cell=("ET", 8.0, 1.0e-3), log=print) -> Dict:
    """One case, taken apart: why perfect knowledge of the tremor still leaves part of it (SIM).  The oracle commands
    -d(t + preview), d = the handle's tremor at its tip point (tremor run minus the set-up's tremor-free run, both with
    the nib held centred).  Reported on the writing phase (the letters, which the ink metric scores) and on all contact
    after 0.5 s (including the 4 s on the paper before writing): the handle's tremor and how often it passes the nib's
    page-plane reach, the ink residual, the part the reach clips, the seed-to-seed floor (a tremor-free run with the
    test seed against the set-up's), the nib's page gain and lag, and sim2's contact gate (the servo fades the command
    when the ball lifts; the H1 writer's ball chatters in short lifts)."""
    kind, f0, amp = cell
    key = f"diag5|{name}|{kind}|{f0:g}|{amp * 1e3:g}|{w}"
    if rows.has(key):
        return rows.rows[key]
    sd = designs[name]
    su = Setup(w, Pens({name: sd}), name, log=log)
    seed = TEST_SEEDS[w % len(TEST_SEEDS)]
    env = case_env(w, seed)
    tr = _tremor(su.case, kind, f0, amp, seed)
    t0 = time.time()
    rn = su.run("none", seed, env, tremor=tr)
    ro = su.run("oracle", seed, env, tremor=tr, ref_none=rn)
    rf = su.clean_ref(seed, env)
    cl = su.clean
    n = min(len(rn["t"]), len(ro["t"]), len(cl["t"]), len(rf["t"]))
    t = rn["t"][:n]
    dt = float(t[1] - t[0])
    co = ro["contact"][:n] > 0.5
    c = (rn["contact"][:n] > 0.5) & co & (t > 0.5)
    pdn = np.interp(t, su.case.t, np.asarray(su.case.written.intended.pen_down, dtype=float)) > 0.5
    cw = c & pdn & (t >= su.case_pre_s)                     # the letters: pen down after the time on the paper before writing
    d = rn.ball()[:n] - cl.ball()[:n]
    e_none = rn.ink()[:n] - cl.ink()[:n]
    e_or = ro.ink()[:n] - cl.ink()[:n]
    e_fl = rf.ink()[:n] - cl.ink()[:n]
    dink = ro.ink()[:n] - rn.ink()[:n]
    qp = np.column_stack([ro["qpx"][:n], ro["qpy"][:n]])
    reach = float(su.pm.cfg.geom.travel)
    r = np.hypot(d[:, 0], d[:, 1])
    clip_res = d * (1.0 - np.where(r > reach, reach / np.maximum(r, 1e-12), 1.0))[:, None]
    rms = lambda v, m: float(np.sqrt(np.mean(np.sum(v[m] ** 2, axis=1))) * 1e6) if m.any() else None      # um
    gains, lags = [], []
    for j in (0, 1):
        gains.append(float(np.sum(dink[c, j] * qp[c, j]) / np.sum(qp[c, j] ** 2)))
        a_ = qp[c, j] - qp[c, j].mean()
        b_ = dink[c, j] - dink[c, j].mean()
        L = range(-40, 41)
        cc = [float(np.sum(a_[max(0, -k):len(a_) - max(0, k)] * b_[max(0, k):len(b_) - max(0, -k)])) for k in L]
        lags.append(list(L)[int(np.argmax(cc))] * dt)
    nz = su.pm.cfg.nose
    gd = 2 * nz.servo_zeta / (2 * math.pi * nz.servo_hz) + 0.25e-3
    kk = int(round(gd / dt))
    ds = np.vstack([d[kk:], np.repeat(d[-1:], kk, 0)])
    rs = np.hypot(ds[:, 0], ds[:, 1])
    m2 = c & (rs > 0.2e-3) & (rs < 0.7 * reach)
    g_eff = -np.sum(qp * ds, axis=1) / np.maximum(np.sum(ds * ds, axis=1), 1e-18)
    td = np.where(np.diff(co.astype(int)) > 0)[0] + 1
    lo = np.where(np.diff(co.astype(int)) < 0)[0] + 1
    durs = np.array([t[td[td > a][0]] - t[a] for a in lo if np.any(td > a)])
    since = np.full(n, np.inf)
    last = -np.inf
    tds = set(td.tolist())
    for i in range(n):
        if i in tds:
            last = t[i]
        since[i] = t[i] - last
    low = m2 & (g_eff < 0.5)
    err = qp + ds

    dh = ro.ball()[:n] - rn.ball()[:n]                      # how the correction changed the handle's own motion
    mu_n, mu_o = rn["mu_b"][:n], ro["mu_b"][:n]

    def block(m):
        return {"handle_tremor_rms_um": rms(d, m), "handle_tremor_p95_mm": float(np.percentile(r[m], 95) * 1e3) if m.any() else None,
                "handle_change_um": rms(dh, m), "mu_ball_none": float(np.mean(mu_n[m])) if m.any() else None,
                "mu_ball_oracle": float(np.mean(mu_o[m])) if m.any() else None,
                "share_beyond_reach": float(np.mean(r[m] > reach)) if m.any() else None, "ink_none_um": rms(e_none, m),
                "ink_oracle_um": rms(e_or, m), "clip_residual_um": rms(clip_res, m), "floor_um": rms(e_fl, m),
                "n_samples": int(m.sum())}

    tz = ro["tipz"][:n]
    up = (~co) & (t >= su.case_pre_s)
    row = {"design": name, "w": w, "seed": seed, "cell": f"{kind} {f0:g} Hz {amp * 1e3:g} mm", "reach_mm": reach * 1e3,
           "page_lift_max_mm": float(su.pm.cfg.sensors.page_lift_max * 1e3),
           "handle_lift_up_median_mm": float(np.median(tz[up] - tz[0]) * 1e3) if up.any() else None,
           "handle_lift_up_p90_mm": float(np.percentile(tz[up] - tz[0], 90) * 1e3) if up.any() else None,
           "writing": block(cw), "all_contact": block(c), "page_gain_xy": gains, "lag_ms_xy": [1e3 * x for x in lags],
           "preview_ms": gd * 1e3, "command_error_unclipped_um": rms(err, m2), "gated_share": float(np.mean(g_eff[m2] < 0.5)),
           "gated_share_of_command_error": float(np.sum(err[low] ** 2) / max(np.sum(err[m2] ** 2), 1e-30)),
           "gated_ms_after_touchdown_median": float(np.median(since[low]) * 1e3) if low.any() else None,
           "lifts": int(len(durs)), "lifts_under_5ms": int(np.sum(durs < 5e-3)), "lifts_over_50ms": int(np.sum(durs >= 0.05)),
           "wall_s": time.time() - t0,
           "label": f"SIMULATION (sim2; one case: writer {w}, its test seed; {name} with perfect knowledge of the tremor)"}
    rows.put(key, row)
    rows.save()
    wr = row["writing"]
    log(f"[sim] oracle diagnosis {name} {row['cell']} (writing phase): ink none {wr['ink_none_um']:.0f} -> oracle "
        f"{wr['ink_oracle_um']:.0f} um; clipped {wr['clip_residual_um']:.0f} um; floor {wr['floor_um']:.0f} um; handle motion "
        f"changed by {wr['handle_change_um']:.0f} um; mu {wr['mu_ball_none']:.3f}/{wr['mu_ball_oracle']:.3f}; beyond reach "
        f"{100 * wr['share_beyond_reach']:.1f} %; gain {gains[0]:.3f}/{gains[1]:.3f}; lag {1e3 * lags[0]:.1f}/{1e3 * lags[1]:.1f} ms")
    return row


def _lift_sensitivity(rows: Rows) -> Dict:
    """The first test grid ran with sim2's default page lift cut-off (0.8 mm) instead of the sensor's 2 mm (OPT-54): the
    firmware then lost the page at every pen lift between strokes (the H1 writer lifts the handle about 1.2-1.6 mm) and
    faded its authority back in over 50 ms after each touchdown.  Case by case (same keys), what that cost."""
    if not os.path.exists(ROWS_LIFT08):
        return {}
    try:
        old = json.load(open(ROWS_LIFT08))
    except Exception:
        return {}
    acc: Dict = {}
    for k, r in rows.rows.items():
        if not k.startswith("test|") or r.get("ctl") not in ("nose", "oracle") or r.get("kind") not in ("ET", "PD"):
            continue
        o = old.get(k)
        if not o or o.get("ratio") is None or r.get("ratio") is None:
            continue
        a = acc.setdefault(r["design"], {}).setdefault(r["ctl"], {"old": [], "new": [], "w_old": [], "w_new": []})
        a["old"].append(o["ratio"]); a["new"].append(r["ratio"])
        a["w_old"].append(o["words_app"]); a["w_new"].append(r["words_app"])
    out = {"designs": {}, "label": "SIMULATION (the same cases with a 0.8 mm and a 2 mm page lift cut-off)"}
    for dsg, v in acc.items():
        out["designs"][dsg] = {ctl: {"ratio_lift08": float(np.mean(x["old"])), "ratio_lift2": float(np.mean(x["new"])),
                                     "words10_lift08": float(10 * np.mean(x["w_old"])), "words10_lift2": float(10 * np.mean(x["w_new"])),
                                     "n": len(x["new"])} for ctl, x in v.items()}
    return out


def _travel_summary(rows: Rows) -> Dict:
    tv = [r for k, r in rows.rows.items() if k.startswith("travel|B1w|") and r.get("kind") in ("ET", "PD")
          and r.get("ctl") in ("nose", "oracle")]
    if not tv:
        return {}
    comp: Dict = {}
    for r in tv:
        k1 = f"test|B1|{r['kind']}|{r['f0']:g}|{r['amp_mm']:g}|{r['w']}|{r['seed']}|deltapen|{r['ctl']}"
        b = rows.rows.get(k1)
        if b is None:
            continue
        cell = f"{r['kind']} {r['f0']:g} Hz {r['amp_mm']:g} mm"
        comp.setdefault(cell, {}).setdefault(r["ctl"], []).append(
            (b["ratio"], r["ratio"], b["P_nib_W"], r["P_nib_W"], b["words_app"], r["words_app"], b["ink_err_um"], r["ink_err_um"]))
    out = {"cells": {}}
    for cell, v in comp.items():
        out["cells"][cell] = {}
        for ctl, L in v.items():
            A_ = np.array(L)
            out["cells"][cell][ctl] = {"ratio_B1": float(A_[:, 0].mean()), "ratio_B1w": float(A_[:, 1].mean()),
                                       "P_B1_mW": float(1e3 * A_[:, 2].mean()), "P_B1w_mW": float(1e3 * A_[:, 3].mean()),
                                       "words10_B1": float(10 * A_[:, 4].mean()), "words10_B1w": float(10 * A_[:, 5].mean()),
                                       "ink_B1_um": float(A_[:, 6].mean()), "ink_B1w_um": float(A_[:, 7].mean()), "n": len(L)}
    cl = [r for k, r in rows.rows.items() if k.startswith("travel|B1w|clean|")]
    if cl:
        out["clean_moved_um_B1w"] = float(np.mean([r["moved_vs_clean_um"] for r in cl]))
        out["clean_P_mW_B1w"] = float(1e3 * np.mean([r["P_nib_W"] for r in cl]))
    out["label"] = ("SIMULATION (sim2; writers 0-1, their test seeds; B1w = the optimiser's counter-face point at the "
                    "1.5 mm travel floor, same frozen rules; compared case by case with B1)")
    return out


def stage_thermal(designs: Dict[str, SimDesign], rows: Rows, quick: bool = False, log=print) -> Dict:
    """Long thermal run with the governor: writer 0 writes the full sentence ('return library books by friday') at
    35 deg tilt (the largest static load) with ET 8 Hz 2 mm tremor, nib on, B1 and B2; the two-node model and governor
    run in the servo loop from a pen already at the 30-min temperature of the same power (hot start, CALC on SIM:
    the sim's mean power drives the two-node model for 30 min first)."""
    out = {}
    text = "return library books by friday" if not quick else TEXT
    for name in ("B1", "B2"):
        key = f"thermal|{name}"
        if rows.has(key):
            out[name] = rows.rows[key]
            continue
        sd = designs[name]
        pens = Pens({name: sd})
        su = Setup(0, pens, name, theta=35.0, text=text, pre_s=2.0, log=log)
        env = case_env(0, TEST_SEEDS[0])
        tr = _tremor(su.case, "ET", 8.0, 2.0e-3, TEST_SEEDS[0])
        t0 = time.time()
        r_cold = su.run("nose", TEST_SEEDS[0], env, tremor=tr)
        P_mean = float(np.mean(r_cold["Pcu"][r_cold["t"] > 0.3]))
        tn = su._tn()
        # 30 min of the same mean power (two nodes, governor) -> the hot start
        n = int(30 * 60 / 0.05)
        th = tn.simulate(np.full(n, P_mean), 0.05, governor=True)
        T0 = (float(th["T_coil"][-1]), float(th["T_skin"][-1]))
        r_hot = su.run("nose", TEST_SEEDS[0], env, tremor=tr, T0=T0)
        mh = su.metrics(r_hot)
        mc = su.metrics(r_cold)
        row = {"design": name, "theta_deg": 35.0, "text": text, "P_nib_mean_W": P_mean, "T_after_30min": T0,
               "T_coil_peak_hot_C": float(np.max(r_hot["Tc2"])), "T_skin_peak_hot_C": float(np.max(r_hot["Ts2"])),
               "gov_min_hot": float(np.min(r_hot["gov"])), "gov_min_30min_calc": float(np.min(th["g"])),
               "ink_err_cold_um": mc["ink_err_um"], "ink_err_hot_um": mh["ink_err_um"], "words_cold": mc["words_app"],
               "words_hot": mh["words_app"], "battery_h": mh["battery_h"], "wall_s": time.time() - t0,
               "label": "SIMULATION (sim2, two-node thermal model and governor in the servo loop) + CALC (30-min "
                        "two-node extrapolation at the simulated mean power)"}
        rows.put(key, row)
        rows.save()
        out[name] = row
        log(f"[sim] thermal {name}: P {P_mean * 1e3:.1f} mW, 30 min -> coil {T0[0]:.1f} C, skin {T0[1]:.1f} C, "
            f"governor min {row['gov_min_hot']:.2f}")
    return out


# ================================================================================================ summary / cards
def _sim2j_reference(cells, writers=None) -> Dict:
    """sim2j's Rev J C1S runs in the same cells (the same writers and seeds when `writers` is given, the same frozen
    tracker; sim2j/build/et_rows.json, read-only, SIM) as a reference: ink ratio, words and nose power."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim2j", "build", "et_rows.json")
    if not os.path.exists(p):
        return {}
    try:
        R = json.load(open(p))
    except Exception:
        return {}
    R = list(R.values()) if isinstance(R, dict) else R
    if writers is not None:
        R = [r for r in R if r.get("w") in writers and r.get("seed") == TEST_SEEDS[r["w"] % len(TEST_SEEDS)]]
    out = {}
    for kind, f0, amp in cells:
        if kind != "ET":
            continue
        rn = [r for r in R if r.get("kind") == "tremor" and r.get("ctl") == "nose" and abs(r.get("f0", -1) - f0) < 1e-6
              and abs(r.get("amp_mm", -1) - amp * 1e3) < 1e-6]
        ro = [r for r in R if r.get("kind") == "tremor" and r.get("ctl") == "oracle" and abs(r.get("f0", -1) - f0) < 1e-6
              and abs(r.get("amp_mm", -1) - amp * 1e3) < 1e-6]
        if rn:
            out[f"ET {f0:g} Hz {amp * 1e3:g} mm"] = {
                "ratio_nose": float(np.mean([r["ratio"] for r in rn if r.get("ratio") is not None])),
                "ratio_oracle": float(np.mean([r["ratio"] for r in ro if r.get("ratio") is not None])) if ro else None,
                "words_nose": float(np.mean([r["words_app"] for r in rn])), "P_nose_W": float(np.mean([r["P_nose_W"] for r in rn])),
                "n": len(rn)}
    return {"cells": out, "writers": sorted(writers) if writers is not None else None,
            "label": "SIMULATION (sim2j, Rev J C1S nose, same writers, seeds and tracker; read-only reference)"}


def summarise(rows: Rows, designs: Dict[str, SimDesign]) -> Dict:
    out = {"cards": {}, "ideal": {}, "tuning": [r for k, r in rows.rows.items() if k.startswith("tune|")]}
    for name, sd in designs.items():
        tr = [r for k, r in rows.rows.items() if k.startswith(f"test|{name}|") and r.get("ctl") == "nose"
              and r.get("kind") in ("ET", "PD")]
        to = [r for k, r in rows.rows.items() if k.startswith(f"test|{name}|") and r.get("ctl") == "oracle"
              and r.get("kind") in ("ET", "PD")]
        tn = [r for k, r in rows.rows.items() if k.startswith(f"test|{name}|") and r.get("ctl") == "none"
              and r.get("kind") in ("ET", "PD")]
        cl = [r for k, r in rows.rows.items() if k.startswith(f"test|{name}|clean|")]
        if not tr:
            continue
        mean = lambda L, k: float(np.mean([x[k] for x in L if x.get(k) is not None])) if L else None
        card = {
            "design": name, "title": sd.title, "n_tremor_cases": len(tr), "n_writers": len({r["w"] for r in tr}),
            "tremor_left_ratio_median": float(np.median([r["ratio"] for r in tr])),
            "tremor_left_ratio_mean": mean(tr, "ratio"),
            "tremor_left_ratio_oracle_mean": mean(to, "ratio"),
            "ink_err_um_nib_mean": mean(tr, "ink_err_um"), "ink_err_um_off_mean": mean(tn, "ink_err_um"),
            "ink_err_um_oracle_mean": mean(to, "ink_err_um"),
            "words_per10_nib": 10 * mean(tr, "words_app"), "words_per10_off": 10 * mean(tn, "words_app") if tn else None,
            "words_per10_oracle": 10 * mean(to, "words_app") if to else None,
            "clean_moved_um_mean": mean(cl, "moved_vs_clean_um"),
            "clean_ink_err_um_mean": mean(cl, "ink_err_um"),
            "clean_moved_um_max": float(np.max([r["moved_vs_clean_um"] for r in cl])) if cl else None,
            "clean_words_per10": 10 * mean(cl, "words_app") if cl else None,
            "P_nib_mW_tremor_mean": 1e3 * mean(tr, "P_nib_W"), "P_nib_mW_off_mean": 1e3 * mean(tn, "P_nib_W") if tn else None,
            "P_nib_mW_oracle_mean": 1e3 * mean(to, "P_nib_W") if to else None,
            "P_nib_mW_clean_mean": 1e3 * mean(cl, "P_nib_W") if cl else None,
            "battery_h_tremor": mean(tr, "battery_h"), "battery_h_clean": mean(cl, "battery_h"),
            "label": "SIMULATION (sim2; synthetic writers (see n_writers) and synthetic ET/PD tremor; DeltaPen-calibrated page sensor)",
        }
        if sd.family == "translation":
            card["T_coil_end_C_max"] = float(np.nanmax([r.get("T_coil_end_C", float("nan")) for r in tr]))
            card["T_skin_end_C_max"] = float(np.nanmax([r.get("T_skin_end_C", float("nan")) for r in tr]))
        if sd.family == "piezo":
            card["piezo_sat_share_mean"] = mean(tr, "piezo_sat_share")
        th = rows.rows.get(f"thermal|{name}")
        if th:
            card["thermal_35deg"] = th
        by = {}
        for r in tr + to:
            k = f"{r['kind']} {r['f0']:g} Hz {r['amp_mm']:g} mm"
            by.setdefault(k, {"nose": [], "oracle": []})[r["ctl"]].append(r)
        card["by_cell"] = {}
        for k, v in by.items():
            vn, vo = v["nose"], v["oracle"]
            card["by_cell"][k] = {"ratio_mean": mean(vn, "ratio"), "ratio_oracle": mean(vo, "ratio"),
                                  "ink_nib_um": mean(vn, "ink_err_um"), "ink_off_um": mean(vn, "none_ink_err_um"),
                                  "words_nib": mean(vn, "words_app"), "words_off": mean(vn, "none_words_app"),
                                  "words_oracle": mean(vo, "words_app"), "P_mW": 1e3 * mean(vn, "P_nib_W") if vn else None,
                                  "n": len(vn)}
        if sd.counterface:
            fe = [r.get("face_engaged_in_contact") for r in tr if r.get("face_engaged_in_contact") is not None]
            fu = [r.get("face_engaged_penup") for r in tr if r.get("face_engaged_penup") is not None]
            card["face_engaged_in_contact_mean"] = float(np.nanmean(fe)) if fe else None
            card["face_engaged_penup_mean"] = float(np.nanmean(fu)) if fu else None
        out["cards"][name] = card
    idl = [r for k, r in rows.rows.items() if k.startswith("ideal|") and r.get("ctl") == "nose" and r.get("kind") in ("ET", "PD")]
    if idl:
        pairs = []
        for r in idl:
            k2 = f"test|{r['design']}|{r['kind']}|{r['f0']:g}|{r['amp_mm']:g}|{r['w']}|{r['seed']}|deltapen|nose"
            if k2 in rows.rows:
                pairs.append((r["ink_err_um"], rows.rows[k2]["ink_err_um"], r["ratio"], rows.rows[k2]["ratio"]))
        if pairs:
            P_ = np.array(pairs)
            out["ideal"] = {"n": len(pairs), "ink_err_um_ideal": float(P_[:, 0].mean()), "ink_err_um_deltapen": float(P_[:, 1].mean()),
                            "ratio_ideal": float(P_[:, 2].mean()), "ratio_deltapen": float(P_[:, 3].mean()),
                            "label": "SIMULATION: the ideal page sensor (3 um white) is a BOUND, not a prediction"}
    wb1 = sorted({r["w"] for k, r in rows.rows.items() if k.startswith("test|B1|") and r.get("kind") in ("ET", "PD")})
    out["sim2j_revJ_reference"] = _sim2j_reference(CELLS, writers=wb1 or None)
    out["travel"] = _travel_summary(rows)
    out["lift_cutoff_sensitivity"] = _lift_sensitivity(rows)
    out["oracle_diagnosis"] = {r["design"]: r for k, r in rows.rows.items() if k.startswith("diag5|")}
    return out


def run_all(quick: bool = False, stages=("tune", "test", "ideal", "thermal", "travel"), log=print) -> Dict:
    t0 = time.time()
    designs = sim_designs()
    rows = Rows(BUILD / ("sim_rows_quick.json" if quick else "sim_rows.json"))
    rules = None
    if "tune" in stages:
        rules = stage_tune(designs, rows, quick=quick, log=log)
    else:
        rules = frozen_rules()
    designs = apply_rules(designs, rules)
    th = {}
    if "thermal" in stages:
        th = stage_thermal(designs, rows, quick=quick, log=log)
    if "test" in stages:
        stage_test(designs, rows, quick=quick, log=log)
    if "ideal" in stages:
        stage_ideal(designs, rows, quick=quick, log=log)
    if "travel" in stages:
        stage_travel(designs, rows, quick=quick, log=log)
        if not quick:
            for nm in ("B1", "B1w"):
                if nm in designs:
                    oracle_diagnosis(designs, rows, name=nm, log=log)
    rows.save()
    summ = summarise(rows, designs)
    summ["designs"] = {k: {"title": sd.title, "key": sd.key, "grip": sd.grip, "family": sd.family, "counterface": sd.counterface,
                           "servo_fi": sd.servo_fi, "face_gap_mm": sd.face_gap * 1e3, "travel_mm": sd.design.travel * 1e3,
                           "Km_tip": sd.ev.get("Km_tip"), "m_eff_g": sd.ev.get("m_eff_tip_g"), "k_tip": sd.ev.get("k_tip_N_m"),
                           "P_cont_calc_W": sd.ev.get("P_cont_W")} for k, sd in designs.items()}
    summ["rules"] = rules
    summ["deltapen_calibration"] = deltapen_calibration()
    summ["wall_s"] = time.time() - t0
    summ["cells"] = [{"kind": k, "f0": f, "amp_mm": a * 1e3} for k, f, a in CELLS]
    return summ
