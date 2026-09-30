r"""Gymnasium environment: the pen's own sensors in, device commands out, with domain randomisation.

  obs    IMU specific force (3, /10 m s^-2) and rate (3, x10 rad/s^-1... scaled), nose Hall tip deflection (2, / travel),
         page-sensor displacement since the episode start (2, / 5 mm, delayed, held between samples) and its valid flag,
         writing force (skid-ring load cell, N), refill slide (/1 mm), contact flag (slide sensor), previous action.
         Every sensor has its noise, bias and delay (sensors.OnlineSensors); nothing privileged.
  action [-1, 1]^k: the nose tip reference along (t1, t2) scaled by the usable travel (it passes the servo's soft
         limit, slew limit and the physical force limits), then each plug-in's commands scaled to its range.
  reward -(e / 0.1 mm)^2 per control tick, with e the ink deviation from the tremor-free ink of the same plant and
         writing (privileged reference run at reset, 'clean'), or from the time-aligned intended path
         ('intent', no reference run); minus action-rate, saturation, missing-ink and extra-ink penalties.
         Tracking is scored whenever the reference requires ink, including when the ball loses contact.
  episode  `episode_s` of synthetic writing (sigma-lognormal writer, stabpen.signals) with a sampled tremor, 1 kHz
         control by default.
Domain randomisation (DR, sampled per episode; `DR` below with sources): grip (tip stiffness and damping, split
r_rot and rho_w), hand (mass, arm stiffness and damping), tremor (frequency, amplitude, wander, profile), friction
(ball, skid, static/kinetic ratio, Stribeck speed, pre-sliding), sensors (IMU noise and bias scale, page latency,
Hall noise), part tolerances (masses, gimbal stiffness, coil constant and resistance, refill spring), writing posture
(tilt, writing force).  Every range is a hypothesis (params.py labels); the MyoSuite study (myo.py) informs the hand.
Evidence status: SIMULATION.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from . import builder as B
from . import params as P
from . import sim as S
from .sensors import OnlineSensors
from .reward import InkCost, InkReference, advance_scored

# name: (low, high, 'log'|'lin', source label)
DR: Dict[str, tuple] = {
    "k_nib": (230.0, 1040.0, "log", "LIT HAP-26 95 % CI 228-1043 N/m"),
    "b_nib": (0.4, 4.6, "log", "LIT HAP-26 0.3-4.6 N s/m"),
    "r_rot": (0.3, 0.7, "lin", "ASSUMPTION (EXP-I01)"),
    "rho_w": (0.15, 0.5, "lin", "ASSUMPTION (EXP-I01)"),
    "M": (0.12, 0.57, "log", "LIT HAP-26 hand mass CI 0.14-0.57 kg (X)"),
    "k_arm": (63.0, 533.0, "log", "LIT HAP-26 k2 63-533 N/m"),
    "b_arm": (3.7, 60.0, "log", "LIT HAP-26 b2 3.7-27.6 N s/m, upper end widened to the MyoArm arm-part damping at "
                                 "co-contraction 0.3 (SIM, fore-aft b2 57.6 N s/m, results/sim2/myo_impedance.json)"),
    "f0": (4.0, 12.0, "lin", "LIT PDT-07, HAP (tremor 4-12 Hz)"),
    "amp": (0.1e-3, 2.0e-3, "log", "ASSUMPTION within PDT-13/PDT-15 scales (0.1-2 mm at the pen)"),
    "f_jitter": (0.1, 0.6, "lin", "ASSUMPTION (stabpen default 0.3 Hz)"),
    "am_depth": (0.1, 0.5, "lin", "ASSUMPTION (stabpen default 0.3)"),
    "mu_ball": (0.09, 0.2, "lin", "LIT CON-13 0.09-0.165 + margin"),
    "mu_skid": (0.05, 0.25, "lin", "ASSUMPTION (EXP-Q01 range)"),
    "ms_ratio": (1.0, 1.5, "lin", "ASSUMPTION (config 1.3)"),
    "v_s": (0.5e-3, 5e-3, "log", "ASSUMPTION (s2r: unidentifiable without a dip)"),
    "presliding": (3e-6, 30e-6, "log", "ASSUMPTION (s2r 3-30 um)"),
    "imu_noise": (0.5, 2.0, "log", "MFR OPT-37 x (0.5-2)"),
    "page_latency": (1e-3, 10e-3, "log", "ASSUMPTION (proposed requirement <= 10 ms)"),
    "hall_noise": (2e-6, 10e-6, "log", "ASSUMPTION from MFR OPT-45"),
    "mass_scale": (0.9, 1.1, "lin", "ASSUMPTION part tolerance"),
    "k_r": (0.02, 0.03, "lin", "ASSUMPTION gimbal +-20 %"),
    "Km": (0.42, 0.52, "lin", "ASSUMPTION Km +-10 %"),
    "F_c": (0.10, 0.20, "lin", "ASSUMPTION refill spring (EXP-Q02)"),
    "theta": (40.0, 60.0, "lin", "LIT CON-02 about 50 deg"),
    "N0": (0.6, 2.0, "log", "LIT CON-01 per-subject means 0.56-2.08 N"),
}


def sample_dr(rng: np.random.Generator, keys=None, scale: float = 1.0) -> Dict[str, float]:
    """Sample DR parameters; scale in [0, 1] shrinks every range toward its geometric/arithmetic centre."""
    out = {}
    for k, (lo, hi, kind, _) in DR.items():
        if keys is not None and k not in keys:
            continue
        if kind == "log":
            c = math.sqrt(lo * hi)
            a, b = c * (lo / c) ** scale, c * (hi / c) ** scale
            out[k] = float(math.exp(rng.uniform(math.log(a), math.log(b))))
        else:
            c = 0.5 * (lo + hi)
            a, b = c + (lo - c) * scale, c + (hi - c) * scale
            out[k] = float(rng.uniform(a, b))
    return out


def config_from_dr(p: Dict[str, float], base: Optional[P.Config] = None) -> P.Config:
    cfg = base or P.Config()
    h = replace(cfg.hand, k_nib=p.get("k_nib", cfg.hand.k_nib), b_nib=p.get("b_nib", cfg.hand.b_nib),
                r_rot=min(p.get("r_rot", cfg.hand.r_rot), 0.74), rho_w=p.get("rho_w", cfg.hand.rho_w),
                M=p.get("M", cfg.hand.M), k_arm=p.get("k_arm", cfg.hand.k_arm), b_arm=p.get("b_arm", cfg.hand.b_arm))
    c = replace(cfg.contact, mu_ball=p.get("mu_ball", cfg.contact.mu_ball), mu_skid=p.get("mu_skid", cfg.contact.mu_skid),
                ms_ratio=p.get("ms_ratio", cfg.contact.ms_ratio), v_s=p.get("v_s", cfg.contact.v_s),
                presliding=p.get("presliding", cfg.contact.presliding))
    nz = replace(cfg.nose, k_r=p.get("k_r", cfg.nose.k_r), Km_act=p.get("Km", cfg.nose.Km_act),
                 hall_noise=p.get("hall_noise", cfg.nose.hall_noise),
                 velocity_source=p.get("velocity_source", cfg.nose.velocity_source))
    rf = replace(cfg.refill, F_c=p.get("F_c", cfg.refill.F_c))
    g = replace(cfg.geom, theta_deg=p.get("theta", cfg.geom.theta_deg))
    s = replace(cfg.sensors, hall_noise=p.get("hall_noise", cfg.sensors.hall_noise),
                page_latency=p.get("page_latency", cfg.sensors.page_latency))
    return cfg.replace(hand=h, contact=c, nose=nz, refill=rf, geom=g, sensors=s, N0=p.get("N0", cfg.N0),
                       wiring=(1 + cfg.wiring) * p.get("mass_scale", 1.0) - 1)


def check_split(p):
    """r_rot must be reachable for the sampled rho_w (sim/handpen/grip.r_max)."""
    from sim.handpen import grip as G
    g = P.Geometry()
    rm = G.r_max(p["rho_w"], g.z_f, g.z_w)
    p["r_rot"] = min(p["r_rot"], rm - 1e-3)
    return p


@dataclass
class EnvConfig:
    base: P.Config = field(default_factory=lambda: P.Config())
    control_hz: float = 1000.0
    episode_s: float = 3.0
    settle_s: float = 0.4
    dr: bool = True
    dr_scale: float = 1.0
    dr_keys: Optional[List[str]] = None
    reward: str = "clean"                      # 'clean' | 'intent'
    tremor_kind: str = "trans"
    fixed: Dict[str, float] = field(default_factory=dict)   # parameters held fixed (override DR)
    w_rate: float = 0.02
    w_sat: float = 0.1
    w_missing_ink: float = 9.0
    w_extra_ink: float = 9.0
    seed: int = 0


class PenEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: Optional[EnvConfig] = None):
        super().__init__()
        self.ec = config or EnvConfig()
        self.rng = np.random.default_rng(self.ec.seed)
        base = self.ec.base
        self.plugins = list(base.plugins)
        self.n_nose = 2
        self.cmd_ranges = []
        for pl in self.plugins:
            self.cmd_ranges += [(lo, hi) for (_, lo, hi, _) in pl.commands()]
        self.n_act = self.n_nose + len(self.cmd_ranges)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(self.n_act,), dtype=np.float32)
        n_obs = 3 + 3 + 2 + 2 + 1 + 1 + 1 + 1 + self.n_act
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(n_obs,), dtype=np.float32)
        self.st = None
        self.params = {}

    # ---------------------------------------------------------------------------------------------- episode
    def _scenario(self, seed, p):
        from opt.inertial import scen as SC
        from sim.handpen import model as HM
        from stabpen import signals as sg
        f0 = p.get("f0", 8.0)
        amp = p.get("amp", 1.0e-3)
        spec_kw = {"f_jitter": p.get("f_jitter", 0.3), "am_depth": p.get("am_depth", 0.3)}
        tr = HM.Tremor(f0=f0, amp_trans=amp, spec_kw=spec_kw)
        sc = HM.build_scenario(seed=seed, duration=self.ec.episode_s + self.ec.settle_s, tremor=tr,
                               theta_deg=p.get("theta", 50.0), N0=p.get("N0", 1.0))
        return sc

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        p = sample_dr(self.rng, self.ec.dr_keys, self.ec.dr_scale) if self.ec.dr else {}
        p.update(self.ec.fixed)
        if "rho_w" in p and "r_rot" in p:
            p = check_split(p)
        self.params = p
        cfg = config_from_dr(p, self.ec.base) if p else self.ec.base
        self.pm = B.build(cfg)
        wseed = int(self.rng.integers(400, 100000))
        self.scn = self._scenario(wseed, p)
        dt = self.pm.m.opt.timestep
        self.nsub = max(int(round(1.0 / (self.ec.control_hz * dt))), 1)
        self.clean = None
        if self.ec.reward == "clean":
            import copy
            sc0 = copy.copy(self.scn)
            from sim.handpen import model as HM
            sc0 = HM.build_scenario(seed=wseed, duration=self.ec.episode_s + self.ec.settle_s, tremor=None,
                                    theta_deg=p.get("theta", 50.0), N0=p.get("N0", 1.0))
            ref = S.run(self.pm, sc0, S.RunOptions())
            self.clean = (ref["t"], ref.ink(), ref["contact"])
            self.reference = InkReference(*self.clean)
        elif self.ec.reward == "intent":
            # Scenario has no Boolean pen-down array: the scheduled push force
            # is used as the explicit contact target (not the agent's contact).
            expected = np.asarray(self.scn.fpush) > 0.5 * float(self.scn.N0)
            self.reference = InkReference(self.scn.t, self.scn.intended, expected)
        else:
            raise ValueError("reward must be 'clean' or 'intent'")
        self.ink_cost = InkCost(scale_m=1e-4, missing_ink=self.ec.w_missing_ink,
                                extra_ink=self.ec.w_extra_ink)
        self.st = S.Stepper(self.pm, self.scn, S.RunOptions(record=False))
        self.sens = OnlineSensors(self.pm, self.nsub * dt, seed=wseed + 1, noise_scale=p.get("imu_noise", 1.0))
        self.prev_a = np.zeros(self.n_act, dtype=np.float32)
        self.st.direct_q = (0.0, 0.0)
        self.st.plugin_cmds = self._plugin_cmds(np.zeros(self.n_act))
        # settle
        self.st.advance(int(round(self.ec.settle_s / dt)))
        self.sens.reset()
        obs = self._obs()
        return obs, {"params": dict(p)}

    def _plugin_cmds(self, a):
        cmds = []
        j = self.n_nose
        for pl in self.plugins:
            nc = len(pl.commands())
            c = []
            for i in range(nc):
                lo, hi = self.cmd_ranges[j - self.n_nose]
                c.append(lo + (a[j] + 1.0) * 0.5 * (hi - lo))
                j += 1
            cmds.append(np.array(c))
        return cmds

    def _obs(self):
        st = self.st
        f = st.law.summary() if st.law is not None else st.cont
        r = self.sens.read(f)
        travel = self.pm.cfg.geom.travel
        c = 1.0 if r["slide"][0] > self.pm.info.get("refill_s_lo", -3e-4) + 0.1e-3 else 0.0
        o = np.concatenate([r["acc"] / 10.0, r["gyro"] * 10.0, r["hall"] / travel, r["page"] / 5e-3, r["page_valid"],
                            r["force"], r["slide"] / 1e-3, [c], self.prev_a]).astype(np.float32)
        return o

    def step(self, action):
        a = np.asarray(action, dtype=np.float64)
        if a.shape != (self.n_act,) or not np.all(np.isfinite(a)):
            raise ValueError("action must be a finite vector matching the action space")
        a = np.clip(a, -1.0, 1.0)
        travel = self.pm.cfg.geom.travel
        self.st.direct_q = (float(a[0]) * travel, float(a[1]) * travel)
        self.st.plugin_cmds = self._plugin_cmds(a)
        metrics = advance_scored(self.st, self.nsub, self.reference, self.ink_cost)
        r = -metrics["cost"]
        r -= self.ec.w_rate * float(np.sum((a - self.prev_a) ** 2))
        r -= self.ec.w_sat * float(self.st.servo.sat)
        self.prev_a = a.astype(np.float32)
        obs = self._obs()
        truncated = self.st.done()
        info = {"ink_error_m": metrics["error_rms_m"], **metrics}
        return obs, float(r), False, truncated, info


def speed_test(n_steps: int = 2000, contact: str = "h1", seed: int = 0) -> Dict:
    import time
    base = P.Config() if contact == "h1" else P.Config(contact=P.Contact(model="mujoco", solref=(2e-3, 1.0),
                                                                      solimp=(0.9, 0.95, 1e-3, 0.5, 2.0), impratio=1.0))
    env = PenEnv(EnvConfig(base=base, reward="intent", seed=seed, episode_s=3.0))
    t0 = time.time()
    obs, info = env.reset(seed=seed)
    t_reset = time.time() - t0
    t0 = time.time()
    n = 0
    rng = np.random.default_rng(seed)
    while n < n_steps:
        obs, r, term, trunc, info = env.step(rng.uniform(-0.05, 0.05, env.n_act))
        n += 1
        if term or trunc:
            env.reset(seed=seed + n)
    el = time.time() - t0
    return {"contact": contact, "control_hz": env.ec.control_hz, "env_steps_per_s": n / el,
            "sim_seconds_per_wall_second": n / el / env.ec.control_hz, "reset_s": t_reset, "obs_dim": int(obs.shape[0]),
            "act_dim": env.n_act}
