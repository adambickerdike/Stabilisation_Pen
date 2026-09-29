r"""The balance mechanisms (CALC on PROPOSED DESIGNS; inputs labelled).

Every mechanism returns, for a pose (theta, roll phi), an ink-spring force F_s and a duty, the tip-referred force it adds
on the nib's axes while the ball is on the paper (B_contact) and while it is lifted (B_penup), the extra dynamic load it
causes (sigma_extra: friction at its own contacts) and the stiffness it adds (k_add).  loads.loads_at adds them.

(b) BiasSpring -- a tilt- and roll-scheduled bias: a soft spring (tip stiffness k_b) whose preload is set by a slow
    two-axis positioner with zero holding power (two New Scale SQL-RV-1.8 piezo screw motors, MFR AMF-15/AMF-106, or a
    micro-stepper leadscrew) from the IMU's tilt and roll and a calibrated ink force:
        B = -F^_c cot(th^) e(phi^)        (e: the tilt-plane direction in the nib's axes)
    It does NOT know about contact: after a lift it stays and the coils hold it (ungated), unless an electro-permanent
    clutch releases it at every lift and touchdown (gated 'epm': switching energy per event, ASSUMPTION).
(c) CounterFace -- contact-driven and load-proportional (this study's proposal).  The ink spring does not push the refill
    along the pen from the moving carrier; it pushes a FACE on the handle against the refill's rear end (a 3 mm ball
    in the refill holder's end rolls on the face).  For a translation nib the face is set parallel to the paper (its
    normal n^_r = n, the paper normal) and is spring-loaded along that normal, so
        the face pushes the refill with -F_n n, the paper pushes the ball with +N n (+ friction): N = F_n and the
        carrier carries only the friction and the residual of the face's orientation error;
    and because the refill translates parallel to the paper when the nib moves (both ends keep their heights), its end
    slides ALONG the face: the nib's motion does not move the face.  For the gimbal nib the face is tilted by
    atan((L/b) cot th) (rear end b behind the pivot).  Load-proportional: the balance scales with the ACTUAL spring
    force (tolerance, a replacement refill, another ink) and needs no force calibration.  Contact-driven: the face's
    travel toward the paper ends on a follower stop set a small gap (0.1-0.25 mm) beyond its writing position; when the
    ball lifts, the refill moves forward, the face lands on its stop and leaves the refill (a light axial seat spring
    keeps the refill on its front stop on the carrier: an axial force, no side load), so the balance vanishes on lift
    and returns within the gap at touchdown.  The stop follows the writing position slowly (a slow positioner from the
    IMU tilt schedule, corrected in contact by the refill-slide sensor; it holds during pen-up).  Face-orientation
    drivers: 'imu2' (two slow motors from the IMU: tilt and roll errors propagate); 'slidecam' (the refill slide
    encodes the tilt: a cam sets the face angle, adding a negative stiffness -F_s cot(th) / R_skid; one motor for
    roll); 'keyed' (slide cam + a keyed grip, no motors; the grip's roll spread is the error).  comp_weight: the face
    schedule also cancels the moving nib's weight across the pen (the IMU knows gravity's direction; CALC below).
(e) steep tip is a geometry (candidates.py), (d) low ink force a parameter.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from . import contact as C
from .labels import POSITIONER, SENSORS, val

D2R = math.pi / 180.0


class NoBalance:
    name = "none"

    def balance_force(self, nib, theta, phi, F_s, duty) -> Dict:
        return {"B_contact": np.zeros(2), "B_penup": np.zeros(2), "sigma_extra": np.zeros(2), "k_add": 0.0}

    def describe(self) -> Dict:
        return {"mechanism": "none"}


def _tilt_dir(theta: float, phi: float) -> np.ndarray:
    """Direction of the static side load (away from the paper) in the nib's axes (u1, u2)."""
    fr = C.frame(theta, phi)
    d = -fr["t1"]                          # the paper pushes the ball toward -t1 (away from the paper side)
    return np.array([d @ fr["u1"], d @ fr["u2"]])


@dataclass
class BiasSpring:
    k_b: float = 40.0                     # N/m tip-referred bias-spring stiffness (added to the nib's suspension)
    gated: str = "none"                   # 'none' | 'epm'
    tilt_err: float = 1.0 * D2R           # IMU errors (1 sigma) used deterministically at +1 sigma (worst sign)
    roll_err: float = 2.0 * D2R
    Fc_cal_err: float = 0.10              # the bias is set for F^_c = F_c (1 + err): spring tolerance / refill change
    E_switch: float = 3e-3                # J per EPM switching event (ASSUMPTION, Rev J pen-lift brake value)
    events_per_s: float = 4.0             # lifts + touchdowns per second while writing (ASSUMPTION: ~2 lifts/s)
    name: str = "b_bias"

    def balance_force(self, nib, theta, phi, F_s, duty) -> Dict:
        th_h = theta + self.tilt_err
        ph_h = phi + self.roll_err
        F_h = F_s * (1 + self.Fc_cal_err)
        mag = F_h / math.tan(th_h)
        B = mag * _tilt_dir(theta, ph_h)          # the positioner sets the bias along the estimated roll
        Bu = B.copy() if self.gated == "none" else np.zeros(2)
        P_sw = self.E_switch * self.events_per_s if self.gated == "epm" else 0.0
        preload = mag / max(self.k_b, 1e-9)
        return {"B_contact": B, "B_penup": Bu, "sigma_extra": np.zeros(2), "k_add": self.k_b,
                "P_aux_W": P_sw + 0.002, "preload_travel_mm": preload * 1e3,
                "positioner_ok": bool(preload <= val(POSITIONER["squiggle_travel"]))}

    def describe(self) -> Dict:
        return {"mechanism": "b: tilt/roll-scheduled bias spring", "k_b_N_m": self.k_b, "gated": self.gated,
                "errors": {"tilt_deg": self.tilt_err / D2R, "roll_deg": self.roll_err / D2R, "Fc_cal": self.Fc_cal_err}}


@dataclass
class CounterFace:
    nib_kind: str = "translation"         # 'translation' | 'gimbal'
    b_over_L: float = 1.0                 # rear-end lever for the gimbal nib (b / L)
    driver: str = "imu2"                  # 'imu2' | 'slidecam' | 'keyed'
    tilt_err: float = 1.0 * D2R
    roll_err: float = 2.0 * D2R
    keyed_roll_sd: float = 15.0 * D2R     # a keyed (triangular) grip's roll spread (ASSUMPTION; EXP-B30 measures it)
    R_skid: float = 7.0e-3                # skid contact radius (the slide cam's tilt encoder)
    mu_face: float = 0.005                # rolling ball on a hardened face (ASSUMPTION; 0.05-0.1 if it slides)
    keeper: float = 0.0                   # share of the balance force left during pen-up (0: the face rests on its stop)
    h_face: float = 0.004                 # N friction of the face's guide (flexure-guided: small; ASSUMPTION)
    comp_weight: bool = True              # the schedule also cancels the moving nib's weight (translation nib)
    F_s_nom: float = 0.15                 # N the spring force the weight compensation is scaled for
    name: str = "c_counterface"

    def face_normal(self, theta: float, phi: float, w_comp: float = 0.0) -> np.ndarray:
        """Face normal (page frame, pointing from the refill end into the face) scheduled for (theta, phi).
        v = a + c n_perp with c = s (1 / sin th + w_comp): the face's force across the pen cancels the paper's static
        load (s = 1 translation, -L/b gimbal) and, with w_comp = G_coef / F_s_nom, the nib's weight across the pen
        (translation: G_coef = -m g; gimbal: m g d_cm / L_t) (CALC; derivation in docs/balanced_nib.md)."""
        fr = C.frame(theta, phi)
        a, n = fr["a"], fr["n"]
        n_perp = n - (n @ a) * a
        s = 1.0 if self.nib_kind == "translation" else -1.0 / self.b_over_L
        v = a + s * (1.0 / math.sin(theta) + w_comp) * n_perp
        return v / np.linalg.norm(v)

    def _w_comp(self, nib) -> float:
        if not self.comp_weight or nib is None:
            return 0.0
        from .labels import G0
        if getattr(nib, "kind", "translation") == "translation":
            return -nib.m_nib * G0 / self.F_s_nom
        return nib.m_nib * G0 * nib.d_cm / (nib.L_t * self.F_s_nom)

    def balance_force(self, nib, theta, phi, F_s, duty) -> Dict:
        if self.driver == "imu2":
            th_h, ph_h = theta + self.tilt_err, phi + self.roll_err
            k_add = 0.0
        elif self.driver == "slidecam":
            th_h, ph_h = theta, phi + self.roll_err       # the slide encodes the tilt exactly at rest
            k_add = -F_s / math.tan(theta) / self.R_skid
        else:                                             # keyed grip, no motor
            th_h, ph_h = theta, phi + self.keyed_roll_sd
            k_add = -F_s / math.tan(theta) / self.R_skid
        # the scheduled face normal: computed in the estimated pose, then fixed in the pen body.  Express it in the true
        # pose: rotate by the roll difference about a and by the tilt difference in the tilt plane (small angles).
        nr_est = self.face_normal(th_h, ph_h, self._w_comp(nib))
        fr_e = C.frame(th_h, ph_h)
        fr = C.frame(theta, phi)
        comp = np.array([nr_est @ fr_e["a"], nr_est @ fr_e["u1"], nr_est @ fr_e["u2"]])
        nr = comp[0] * fr["a"] + comp[1] * fr["u1"] + comp[2] * fr["u2"]
        Nr = F_s / max(nr @ fr["a"], 1e-6)
        F_face = -Nr * nr
        if self.nib_kind == "translation":
            B = np.array([-(F_face @ fr["u1"]), -(F_face @ fr["u2"])])
            lever = 1.0
        else:
            B = np.array([self.b_over_L * (F_face @ fr["u1"]), self.b_over_L * (F_face @ fr["u2"])])
            lever = self.b_over_L
        sig = np.full(2, self.mu_face * Nr * lever + self.h_face / math.tan(theta))
        return {"B_contact": B, "B_penup": self.keeper * B, "sigma_extra": sig, "k_add": k_add, "N_face": Nr,
                "face_tilt_deg": math.degrees(math.acos(min(1.0, abs(nr @ fr["a"])))), "P_aux_W": 0.002 if self.driver != "keyed" else 0.0}

    def describe(self) -> Dict:
        return {"mechanism": "c: contact-driven counter-face", "nib_kind": self.nib_kind, "b_over_L": self.b_over_L,
                "driver": self.driver, "mu_face": self.mu_face, "keeper": self.keeper, "comp_weight": self.comp_weight}


def balance_quality(bal, nib, F_s: float = 0.15, n: int = 4000, seed: int = 11, inks=("oil_common", "gel"),
                    theta_range=(35.0, 75.0), Fs_spread: float = 0.2) -> Dict:
    """How well a mechanism balances across tilt, roll, friction (inks, papers), the ink force's spread (a replacement
    refill: +-20 %) and the sensing errors (drawn +-1 sigma): residual static load (contact load + balance + the moving
    nib's weight) in contact and during pen-up, and the friction-driven fluctuation (CALC, Monte Carlo)."""
    rng = np.random.default_rng(seed)
    from .loads import Duty, gravity_load
    res_c, res_u, unb, sig = [], [], [], []
    for _ in range(n):
        th = rng.uniform(*theta_range) * D2R
        ph = rng.uniform(0, 2 * math.pi)
        ink = inks[rng.integers(len(inks))]
        paper = rng.uniform(0.8, 1.3)
        Fs = F_s * (1 + Fs_spread * rng.uniform(-1, 1))
        duty = Duty(ink=ink, paper=paper)
        if hasattr(bal, "tilt_err"):
            te, re = bal.tilt_err, bal.roll_err
            bal.tilt_err = te * rng.standard_normal()
            bal.roll_err = re * rng.standard_normal()
        st = C.writing_load_stats(th, ph, Fs, ink, paper, n_dir=24)
        bb = bal.balance_force(nib, th, ph, Fs, duty)
        if hasattr(bal, "tilt_err"):
            bal.tilt_err, bal.roll_err = te, re
        G = gravity_load(nib, th, ph) if nib is not None else np.zeros(2)
        res_c.append(np.linalg.norm(st["mean_sliding"] + bb["B_contact"] + G))
        res_u.append(np.linalg.norm(bb["B_penup"] + G))
        unb.append(np.linalg.norm(st["static"] + G))
        sig.append(np.linalg.norm(np.sqrt(st["rms_about_mean"] ** 2 + bb["sigma_extra"] ** 2)))
    res_c, res_u, unb, sig = map(np.array, (res_c, res_u, unb, sig))
    return {"residual_contact_mean_N": float(res_c.mean()), "residual_contact_p95_N": float(np.percentile(res_c, 95)),
            "residual_penup_mean_N": float(res_u.mean()), "unbalanced_mean_N": float(unb.mean()),
            "balance_ratio_mean": float(res_c.mean() / unb.mean()),
            "balance_ratio_power": float(np.mean(res_c ** 2) / np.mean(unb ** 2)),
            "friction_fluct_rms_N": float(np.sqrt(np.mean(sig ** 2))), "n": n,
            "label": "CALC (Monte Carlo over tilt 35-75 deg, roll, inks, papers 0.8-1.3, F_s +-20 %, sensing errors)"}
