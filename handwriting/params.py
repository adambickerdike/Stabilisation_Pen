"""Device, hand, writing and board parameters of model HW1, each with its evidence label.

Rev H values come from results/revH/tip_params.json when it exists, else from
results/revH/tip_params_provisional.json (the mechanism study's first cut), else from
the lead's ASSUMPTION defaults.  The guidance board comes from
results/board/board_params.json, else board_params_provisional.json, else defaults.
Every value is a hypothesis until measured.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Dict, Optional

from . import REPO_ROOT

REVH_DIR = REPO_ROOT / "results" / "revH"
BOARD_DIR = REPO_ROOT / "results" / "board"
AKF_SHIP = REPO_ROOT / "results" / "opt" / "tracker_models" / "akf_ship.json"
AKF_REVH = REPO_ROOT / "results" / "opt" / "inertial_tracker_revh.json"


def _load_first(*paths: Path) -> tuple[Optional[dict], Optional[str]]:
    for p in paths:
        if p.exists():
            return json.loads(p.read_text()), str(p.relative_to(REPO_ROOT))
    return None, None


# ------------------------------------------------------------------ hand and writing (shared by every pen)
@dataclass
class Hand:
    """HAP-26 (Fu & Cavusoglu 2012) values as used by models M1, P1 and H1 (config/parameters.yaml hand.*)."""
    K_grip: float = 575.0        # N/m, grip at the tip          LITERATURE HAP-26 (via parameters.yaml)
    C_grip: float = 1.3          # N s/m                        LITERATURE HAP-26
    M_hand: float = 0.21         # kg, hand mass                LITERATURE HAP-26
    k_arm: float = 170.0         # N/m, arm spring              LITERATURE HAP-26
    b_arm: float = 11.0          # N s/m                        LITERATURE HAP-26
    writer_comp: str = "drag"    # "drag": writer cancels the paper drag (ASSUMPTION, nominal); "none": P1 open-loop hand

    @classmethod
    def from_config(cls, **over):
        from stabpen import params as sp
        p = sp.load()
        h = cls(K_grip=float(p["hand.grip_stiffness"]), C_grip=float(p["hand.grip_damping"]),
                M_hand=float(p["hand.mass"]), k_arm=float(p["hand.arm_stiffness"]), b_arm=float(p["hand.arm_damping"]))
        return replace(h, **over)


@dataclass
class Writing:
    N: float = 1.0               # N, writing force               LITERATURE CON-01 (mean of subject means 1.01 N)
    theta_deg: float = 50.0      # pen altitude                   LITERATURE CON-02 (about 50 deg)
    mu_ball: float = 0.15        # ball on paper                  ASSUMPTION (config writing.mu_eff; CON-13 0.09-0.165)
    mu_skid: float = 0.12        # skid ring on paper             ASSUMPTION (P1/H1 value)
    ms_ratio: float = 1.3        # static/kinetic                 ASSUMPTION (config writing.mu_static_ratio)
    v_s: float = 0.002           # Stribeck speed (m/s)           ASSUMPTION (config writing.stribeck_speed)
    x_pre: float = 1e-5          # LuGre pre-sliding (m)          ASSUMPTION (M1 friction.x_presliding default)


# ------------------------------------------------------------------ pens
@dataclass
class Pen:
    key: str
    label: str
    mass: float                  # kg, whole pen
    rigid: bool = True           # True: the tip cannot move relative to the handle
    m_tip: float = 0.0           # kg, tip-equivalent moving mass of the nose / nib stage
    k_tip: float = 0.0           # N/m, suspension at the tip
    zeta_tip: float = 0.05       # open-loop damping ratio of the suspension
    q_lim: float = 0.0           # m, usable correction radius (soft limit with taper)
    q_taper: float = 0.0         # m
    q_stop: float = 0.0          # m, mechanical stop radius
    servo_hz: float = 0.0        # closed-loop follower bandwidth of the tip servo
    servo_zeta: float = 0.7
    latency: float = 0.0         # s, extra command delay after the estimator (tick hold, current loop)
    slew: float = 0.0            # m/s, reference slew limit
    F_peak: float = 0.0          # N at the tip
    F_cont: float = 0.0          # N at the tip, continuous (diagnostic only)
    skid: bool = False           # a skid ring on the handle carries the writing force
    F_c: float = 0.0             # N, refill spring force along the axis (skid designs): ball normal = F_c / sin(theta)
    r_imu: float = 0.100         # m, board IMU distance from the tip (fusion r_board)
    tick_hz: float = 2000.0      # controller tick
    sources: Dict[str, str] = field(default_factory=dict)

    def describe(self) -> Dict:
        d = asdict(self)
        return d

    def ball_normal(self, w: Writing) -> float:
        if not self.skid:
            return w.N
        return min(w.N, self.F_c / math.sin(math.radians(w.theta_deg)))


def ordinary_pen() -> Pen:
    return Pen("none", "No device: ordinary pen", mass=0.012, rigid=True,
               sources={"mass": "ASSUMPTION (typical ballpoint 5-20 g; instrumented pens 24-48 g, CON-04/08/10)"})


def weighted_pen(extra: float = 0.060) -> Pen:
    p = ordinary_pen()
    return replace(p, key="weighted", label=f"Passive weighted handle (+{extra * 1e3:.0f} g)", mass=p.mass + extra,
                   sources={"mass": f"ASSUMPTION: ordinary pen + {extra * 1e3:.0f} g (comparators ACT-18/19; PD: ACT-32, PDT-21)"})


def pencil_p0() -> Pen:
    """Rev P0 pencil: +-0.30 mm usable nib stage behind a skid (config/pencil.yaml P0.1.2; H1's kinematic stage)."""
    return Pen("pencil", "Pencil Rev P0 (+-0.3 mm nib stage)", mass=0.0134, rigid=False,
               m_tip=0.0015, k_tip=0.0, zeta_tip=0.05, q_lim=0.30e-3, q_taper=0.05e-3, q_stop=0.40e-3,
               servo_hz=150.0, servo_zeta=0.7, latency=0.5e-3, slew=0.08, F_peak=0.329, F_cont=0.329,
               skid=True, F_c=0.15, r_imu=0.100,
               sources={"mass": "CALC H1 CAD 13.42 g (docs/inertial_stabilisation.md 4.1)",
                        "q_lim/q_taper/q_stop": "CALC config/pencil.yaml stage.travel_nib (P1 0.30/0.05/0.40 mm)",
                        "servo_hz/slew": "ASSUMPTION H1 kinematic stage (150 Hz, 0.08 m/s = P1 value)",
                        "F_peak": "CALC CHECKPOINT 7: 0.329 N at the nib",
                        "m_tip": "ASSUMPTION (only the force diagnostic uses it)",
                        "latency": "ASSUMPTION one 2 kHz tick",
                        "F_c": "ASSUMPTION P1 refill spring 0.15 N"})


_REVH_DEFAULTS = {"q_lim": 3.0e-3, "q_stop": 3.5e-3, "F_peak": 1.0, "F_cont": 1.0, "servo_hz": 40.0, "latency": 2.0e-3,
                  "m_tip": 0.004, "k_tip": 10.0, "mass": 0.085}


def rev_h(source: str = "auto") -> Pen:
    """Rev H active nose.  source: "auto" (tip_params.json > tip_params_provisional.json > lead defaults) or "lead"."""
    d, path = (None, None) if source == "lead" else _load_first(REVH_DIR / "tip_params.json",
                                                               REVH_DIR / "tip_params_provisional.json")
    if d is None:
        v = dict(_REVH_DEFAULTS)
        src = "ASSUMPTION (lead's defaults: +-3.0 mm, 1.0 N, 40 Hz, 2 ms, 4 g at the tip)"
        pen = Pen("revH", "Rev H active nose (+-3 mm)", mass=v["mass"], rigid=False, m_tip=v["m_tip"], k_tip=v["k_tip"],
                  q_lim=v["q_lim"], q_taper=0.3e-3, q_stop=v["q_stop"], servo_hz=v["servo_hz"], servo_zeta=0.7,
                  latency=v["latency"] - 1.39e-3 if v["latency"] > 1.39e-3 else 0.5e-3, slew=0.6,
                  F_peak=v["F_peak"], F_cont=v["F_cont"], skid=True, F_c=0.15, r_imu=0.0935,
                  sources={k: src for k in ("q_lim", "q_stop", "F_peak", "servo_hz", "latency", "m_tip", "mass")})
        pen.sources["file"] = "none (lead defaults)"
        return pen
    lat = d["latency_ms"]
    # the IMU-to-estimate part (1.4 ms) is inside the fusion sensor models (400 Hz anti-aliasing group delay 1.04 ms +
    # FIFO/SPI 0.35 ms); the tick hold and the current loop are added here
    extra_lat = (lat.get("controller_tick", 0.5) + lat.get("current_loop", 0.1)) * 1e-3
    pen = Pen("revH", "Rev H active nose (+-3 mm)", mass=d["mass_g"]["pen_without_inertial_module"] * 1e-3, rigid=False,
              m_tip=d["moving_mass_at_tip_g"]["value"] * 1e-3, k_tip=d["suspension_stiffness_N_per_m"]["value"],
              zeta_tip=0.05, q_lim=d["tip_travel_mm"]["usable_radius"] * 1e-3,
              q_taper=0.1 * d["tip_travel_mm"]["usable_radius"] * 1e-3,
              q_stop=d["tip_travel_mm"]["mechanical_stop_radius"] * 1e-3,
              servo_hz=d["servo"]["bandwidth_Hz"], servo_zeta=d["servo"]["damping"], latency=extra_lat, slew=0.6,
              F_peak=d["actuator"]["force_limit_at_tip_N"]["peak"], F_cont=d["actuator"]["force_limit_at_tip_N"]["continuous"],
              skid=d.get("architecture", "B") == "B", F_c=0.15, r_imu=0.0935,
              sources={"file": path, "evidence": d["meta"]["evidence_status"],
                       "q_lim/q_stop": d["tip_travel_mm"]["label"], "m_tip": d["moving_mass_at_tip_g"]["label"],
                       "k_tip": d["suspension_stiffness_N_per_m"]["label"], "F_peak/F_cont": d["actuator"]["label"],
                       "servo": d["servo"]["label"], "latency": d["latency_ms"]["label"], "mass": d["mass_g"]["label"],
                       "architecture": d.get("architecture_note", ""),
                       "q_taper": "ASSUMPTION (10 % of the travel)", "slew": "ASSUMPTION (0.6 m/s, opt/inertial RevH default)",
                       "r_imu": "ASSUMPTION (layout_provisional.json: IMU at z 92-95 mm)"})
    return pen


def rev_h_lead() -> Pen:
    """The lead's ASSUMPTION defaults (40 Hz, 1.0 N, 4 g, 2 ms), for the sensitivity run."""
    p = rev_h("lead")
    return replace(p, key="revH_lead", label="Rev H, lead's defaults (40 Hz, 2 ms)")


# ------------------------------------------------------------------ guidance board
@dataclass
class Board:
    F_cap: float = 0.4           # N, software cap
    F_max: float = 0.49          # N, magnetic maximum (A4)
    tau: float = 0.008           # s, first-order force lag
    dead: float = 0.002          # s, dead time
    noise: float = 0.05e-3       # m RMS, pen position sensing
    bias: float = 0.0            # m, systematic sensing error (accuracy 0.4 mm quoted; applied as a constant offset in a sensitivity)
    normal_pull: float = 1.1     # N at zero lateral force (adds to the writing force)
    K: float = 400.0             # N/m, guidance spring toward the template (ASSUMPTION; cap reached at 1 mm error)
    D: float = 0.0               # N s/m
    sources: Dict[str, str] = field(default_factory=dict)


def board() -> Board:
    d, path = _load_first(BOARD_DIR / "board_params.json", BOARD_DIR / "board_params_provisional.json")
    if d is None:
        return Board(F_cap=0.4, F_max=0.4, tau=0.010, dead=0.010, noise=0.5e-3, normal_pull=0.0,
                     sources={"all": "ASSUMPTION (lead's defaults: 0.4 N, 20 ms, 0.5 mm noise; HAP-16 488 mN)", "file": "none"})
    return Board(F_cap=d["software_cap_N"]["value"] if "software_cap_N" in d else 0.4,
                 F_max=d["max_lateral_force_N"]["A4_design_gap_2p7mm"], tau=0.008, dead=0.002,
                 noise=d["position_sensing"]["noise_rms_mm"] * 1e-3, bias=0.0,
                 normal_pull=d["normal_pull_N"]["at_zero_lateral_force_A4"],
                 sources={"file": path, "evidence": d.get("status", d["meta"]["evidence_status"]),
                          "tau/dead": d.get("suggested_simulation_model", ""),
                          "noise": d["position_sensing"]["status"], "F_cap": d["software_cap_N"]["status"],
                          "K": "ASSUMPTION: 400 N/m guidance spring, cap reached at 1 mm error (full); 200 N/m (partial)"})


# ------------------------------------------------------------------ trackers
def akf_ship() -> Dict:
    d = json.loads(AKF_SHIP.read_text())
    return {"label": "AKF ship (P1-tuned, opt/tracker)", "params": dict(d["params"]), "sensors": dict(d["sensors"]),
            "file": str(AKF_SHIP.relative_to(REPO_ROOT)), "evidence": d["meta"]["evidence_status"]}


def akf_revh() -> Optional[Dict]:
    """The mechanism study's Rev H re-tune of the AKF (training seeds only), if it exists."""
    if not AKF_REVH.exists():
        return None
    d = json.loads(AKF_REVH.read_text())
    return {"label": "AKF re-tuned for Rev H (opt/inertial, training seeds)", "params": dict(d["params"]),
            "sensors": {"page": "1k", "comp": "gyro"}, "file": str(AKF_REVH.relative_to(REPO_ROOT)),
            "evidence": d["meta"]["evidence_status"], "seeds": d["meta"].get("seeds")}


def servo_group_delay(pen: Pen) -> float:
    """Low-frequency group delay of the tip command path (s): extra latency + 2 zeta / omega_n of the follower."""
    if pen.rigid or pen.servo_hz <= 0:
        return 0.0
    return pen.latency + 2.0 * pen.servo_zeta / (2.0 * math.pi * pen.servo_hz)
