r"""Reinforcement learning in the physics simulator: a residual arbiter on the Rev J tremor tracker (SIMULATION).

Environment (Gymnasium; sim2 with the Rev J pen, the H1 hand, 50 us steps (sim2 section 5.3: 0.66 um), the online
sensors and the guarded AKF running in the firmware exactly as in the test grid):
  episode   a 2.5 s window of a training writer (v2, ids 1000+, never the test writers 0-5 or the tuning writers
            100-105) writing a random slice of the handwriting study's sentence, starting at a pen lift; the plant and
            the tremor are drawn from the domain randomisation (below); groups of three episodes share a plant and
            writing, so one clean reference run serves three episodes. Each episode is independently tremor-free
            with configured probability p_free (default 1/3).
  obs (19)  from the pen's own sensors and the firmware only: the tracker's output d_hat (2) and its ungated
            oscillator (2), frequency, authority, amplitude; the tremor-line detector's gate, log ratio and line
            frequency; the page-sensor velocity (2) and speed low-passed at 3 Hz (2); ball contact (slide sensor),
            page-sensor valid; the previous action (3).  Nothing privileged (REQ-SIM-004).
  action    (3) in [-1, 1]: gain alpha = 1 + a0 on the tracker's gated estimate; weight w = max(0, a1) on the tracker's
            ungated oscillator (an arbiter: the policy may act where the detector gate is still closed); quadrature
            gain beta = 0.5 a2 on the combined estimate delayed by a quarter period of the tracked frequency (a phase
            correction).  a = 0 is the model-based controller.  Held for 8 firmware ticks (250 Hz).
  reward    -(|ink - reference ink| / 0.3 mm)^2 at every 2 kHz reference tick requiring ink (the reference is the
            same writer and plant without tremor and with the nose held: in tremor-free episodes this is exactly the
            false correction), plus separate missing/extra-ink costs, averaged per policy step, - 0.005 |a|^2.
  DR        sim2's domain randomisation (sim2/env.py DR, 25 factors, sources there) mapped onto the Rev J pen: grip
            (k_nib, b_nib, r_rot, rho_w), hand (M, k_arm, b_arm), tremor (f0 4-12 Hz, amplitude 0.1-2 mm, frequency
            and amplitude wander; 1 in 3 episodes tremor-free), friction (ball, skid, mu_s/mu_k, Stribeck, pre-sliding),
            sensors (IMU noise scale, page latency), tolerances (part masses +-10 %, gimbal stiffness +-20 %, coil Km
            +-10 %, refill spring 0.1-0.2 N), posture (tilt 40-60 deg, writing force 0.6-2 N).
Training: Stable-Baselines3 PPO (MLP 64-64, tanh), one process; checkpoints are selected on the tuning writers
100-103 and seeds 300-303 with the project's rules (false correction <= 25 um on tremor-free writing, no worse than the
model-based tracker at 0.3 mm) before any test run.  Compute is logged (wall seconds, environment steps).
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from . import BUILD, ROOT  # noqa: F401
from . import revj as RJ
from . import stepper as ST
from . import tasks as TK
from . import writers as WV
from .akf_online import GuardParams, frozen_det, frozen_guard, frozen_tracker
from .firmware import FWConfig
from sim2 import env as SE  # noqa: E402
from sim2 import params as P  # noqa: E402
from sim2.reward import InkCost, InkReference, advance_scored

DT_TRAIN = 50e-6
DECIM = 8                      # firmware ticks per policy step (2 kHz / 8 = 250 Hz)
A_RES = 0.3e-3                 # residual range (m)


# the lead's additions to the domain randomisation (results/revJ/sim_params.json domain_randomisation_added, ASSUMPTION)
LEAD_DR = {"F_c": (0.12, 0.18), "km_scale": (0.7, 1.0), "neg_k": (0.0, 0.00165), "tyre_mu": (0.6, 1.2),
           "wheel_P": (0.5, 0.6)}


def lead_dr_ranges() -> Dict[str, tuple]:
    out = dict(LEAD_DR)
    try:
        d = RJ.lead()["sp"].get("domain_randomisation_added", {})
        out.update({"F_c": tuple(d["refill_spring_N"]), "km_scale": tuple(d["Km_scale"]),
                    "neg_k": tuple(d["nose_negative_k_Nm_per_rad"]), "tyre_mu": tuple(d["tyre_mu"]),
                    "wheel_P": tuple(d["wheel_preload_N"])})
    except Exception:
        pass
    return out


def sample_dr(rng) -> Dict[str, float]:
    """sim2's 25 factors (sim2/env.py DR, sources there) + the lead's Rev J factors (refill spring 0.12-0.18 N replaces
    sim2's 0.10-0.20 N; Km scale 0.7-1.0 replaces sim2's Rev H Km +-10 %; magnetic negative stiffness; tyre friction;
    wheel preload).  Not randomised: the wheel motor's detent torque and the pen's roll in the hand (the lead's list;
    no roll or detent model in this study)."""
    p = SE.sample_dr(rng)
    p = SE.check_split(p)
    for k, (lo, hi) in lead_dr_ranges().items():
        p[k] = float(rng.uniform(lo, hi))
    return p


def config_from_dr(p: Dict[str, float], dt: float = DT_TRAIN, heel: bool = True, endcap: bool = False) -> P.Config:
    """sim2's DR mapped onto the Rev J configuration: absolute ranges for hand, grip, friction, posture, sensors;
    relative range for the gimbal flexure (+-20 %: sim2's range is a Rev H absolute); the lead's ranges for the refill
    spring, Km and the magnetic negative stiffness."""
    base = RJ.config(heel=heel, endcap=endcap, dt=dt, theta_deg=p.get("theta", 50.0), N0=p.get("N0", 1.0),
                     F_c=p.get("F_c"), neg_k=p.get("neg_k", 0.0), km_scale=p.get("km_scale", 1.0))
    h = replace(base.hand, k_nib=p["k_nib"], b_nib=p["b_nib"], r_rot=min(p["r_rot"], 0.74), rho_w=p["rho_w"], M=p["M"],
                k_arm=p["k_arm"], b_arm=p["b_arm"])
    c = replace(base.contact, mu_ball=p["mu_ball"], mu_skid=p["mu_skid"], ms_ratio=p["ms_ratio"], v_s=p["v_s"],
                presliding=p["presliding"])
    kr_scale = p["k_r"] / 0.025
    nz = replace(base.nose, k_r=(base.nose.k_r + p.get("neg_k", 0.0)) * kr_scale - p.get("neg_k", 0.0),
                 hall_noise=p["hall_noise"],
                 velocity_source=p.get("velocity_source", base.nose.velocity_source),
                 inner_hz=p.get("inner_hz", base.nose.inner_hz))
    s = replace(base.sensors, hall_noise=p["hall_noise"], page_latency=p["page_latency"])
    return base.replace(hand=h, contact=c, nose=nz, sensors=s, wiring=(1 + base.wiring) * p.get("mass_scale", 1.0) - 1)


class Policy:
    """Wraps an SB3 model (or a callable) as the firmware's policy hook: it sees the firmware's state, builds the
    observation, and returns the page-plane nose command from the tracker's estimate, the gain and the residual."""

    def __init__(self, model=None, deterministic: bool = True, fixed_action=None):
        self.model = model
        self.det = deterministic
        self.fixed = fixed_action
        self.a = np.zeros(3)
        self.k = 0
        self.last_obs = None
        self.hist = []

    def reset(self, fw):
        self.a = np.zeros(3)
        self.k = 0
        self.hist = []

    def obs(self, fw) -> np.ndarray:
        tr = fw.tracker
        o = tr.last
        det = tr.det
        vs = fw.vs
        vl = fw.vlp
        return np.array([o[0] / 1e-3, o[1] / 1e-3, o[5] / 1e-3, o[6] / 1e-3, o[2] / 10.0, o[3], o[4] / 1e-3,
                         det.gate, math.log(max(det.ratio, 1e-3)) / 3.0, det.f_line / 10.0,
                         vs[0] / 0.05, vs[1] / 0.05, vl[0] / 0.05, vl[1] / 0.05,
                         1.0 if fw.contact else 0.0, 1.0 if fw.ps_valid else 0.0,
                         self.a[0], self.a[1], self.a[2]], dtype=np.float32)

    def act(self, fw, t, x_model):
        if self.k % DECIM == 0:
            ob = self.obs(fw)
            self.last_obs = ob
            if self.fixed is not None:
                a = np.asarray(self.fixed, float)
            elif self.model is not None:
                a, _ = self.model.predict(ob, deterministic=self.det)
            else:
                a = np.zeros(3)
            self.a = np.clip(np.asarray(a, float), -1.0, 1.0)
        self.k += 1
        return combine(self, fw)


def combine(pol, fw):
    """Nose command (page plane) from the tracker's outputs and the policy's action (see the module docstring)."""
    a = pol.a
    tr = fw.tracker
    o = tr.last
    x = (1.0 + a[0]) * fw.d_hat + max(0.0, a[1]) * o[5:7]
    h = pol.hist
    h.append(x.copy())
    if len(h) > 400:
        del h[:200]
    f = max(float(o[2]), 3.0)
    kq = max(1, int(round(1.0 / (4.0 * f * 0.5e-3))))
    xq = h[-1 - kq] if len(h) > kq else np.zeros(2)
    return -fw.g_auth * (x + 0.5 * a[2] * xq)


N_OBS = 19



class RevJTremorEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, seed: int = 0, writers=None, episode_s: float = 5.0, settle_s: float = 3.0, dt: float = DT_TRAIN,
                 p_free: float = 1.0 / 3.0, log_path: Optional[str] = None, guard: Optional[GuardParams] = None,
                 fixed_params: Optional[Dict] = None, heel: bool = True, ink_cost: Optional[InkCost] = None,
                 reference_mode: str = "ideal_clean", respect_fixed_frequency: bool = True):
        """Each episode: the pen rests on the paper for settle_s (tremor on; the model-based tracker runs, the policy's
        action is 0: the test's 4 s rest before writing, shortened to 3 s, enough for the guarded detector's 2.5 s) and
        then writes episode_s of a training writer's sentence while the policy acts (250 Hz)."""
        super().__init__()
        self.guard = guard or frozen_guard()
        self.det = frozen_det()
        self.tracker = frozen_tracker()
        self.rng = np.random.default_rng(seed)
        self.writers = list(writers or range(1000, 1400))
        self.episode_s = episode_s
        self.settle_s = settle_s
        self.dt = dt
        if not 0.0 <= p_free <= 1.0:
            raise ValueError("p_free must be a probability")
        self.p_free = float(p_free)
        self.fixed_params = dict(fixed_params or {})
        self.heel = bool(heel)
        self.ink_cost = ink_cost or InkCost()
        if reference_mode not in ("ideal_clean", "matched_clean"):
            raise ValueError("reference_mode must be 'ideal_clean' or historical 'matched_clean'")
        self.reference_mode = reference_mode
        self.respect_fixed_frequency = bool(respect_fixed_frequency)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(N_OBS,), dtype=np.float32)
        self._group = 0
        self._shared = None
        self.akf = None
        self.stats = {"episodes": 0, "env_steps": 0, "sim_s": 0.0, "wall_s": 0.0, "ref_runs": 0}
        self.log_path = log_path
        self.ep_log = []

    # ---- episode construction
    def _new_group(self):
        rng = self.rng
        p = sample_dr(rng)
        p.update(self.fixed_params)
        w = int(rng.choice(self.writers))
        cfg = config_from_dr(p, self.dt, heel=self.heel)
        pm = RJ.build(cfg)
        wr = WV.writer(w, "v2")
        written = wr.write(WV.ET_SENTENCE, dt=TK.SIM_DT, seed=2000 + w)
        it = written.intended
        # the pen rests on the paper at a touchdown for settle_s, then the writing from that touchdown (episode_s)
        up = np.flatnonzero(~it.pen_down[:-1] & it.pen_down[1:]) + 1
        cand = [k for k in up if it.t[k] + self.episode_s < it.t[-1] and it.t[k] > 0.2]
        k0 = int(rng.choice(cand)) if cand else int(np.argmax(it.pen_down))
        k1 = k0 + int(round(self.episode_s / TK.SIM_DT))
        n_pre = int(round(self.settle_s / TK.SIM_DT))
        from stabpen import signals as sg
        from sim.pensim import scenarios as PS
        xy = np.vstack([np.repeat(it.xy[k0:k0 + 1], n_pre, 0), it.xy[k0:k1]]) - it.xy[k0]
        down = np.r_[np.ones(n_pre, bool), it.pen_down[k0:k1]]
        lift = np.r_[np.zeros(n_pre), it.lift[k0:k1]]
        t = np.arange(len(xy)) * TK.SIM_DT
        itx = sg.Intended(t, xy, down, lift, [])
        self._shared = {"p": p, "w": w, "pm": pm, "itx": itx, "k0": k0, "ref": None,
                        "seed": int(rng.integers(1 << 20)), "fw_seed": int(rng.integers(1 << 20))}

    def _scenario(self, tremor=None):
        from sim.pensim import scenarios as PS
        sh = self._shared
        d = np.zeros_like(sh["itx"].xy) if tremor is None else tremor
        sc = PS._assemble(sh["itx"], d, float(sh["p"].get("N0", 1.0)), float(sh["p"].get("theta", 50.0)))
        sc.psi_disp = np.zeros(len(sc.t))
        sc.tremor_obj = None
        return sc

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
            # A seeded reset is a complete reset, independent of which member
            # of a reused three-episode plant group happened to run previously.
            self._group = 0
            self._shared = None
        if self._shared is None or self._group % 3 == 0:
            self._new_group()
        self._group += 1
        sh = self._shared
        pm = sh["pm"]
        t0 = time.time()
        if sh["ref"] is None:
            reference_pm = pm
            if self.reference_mode == "ideal_clean":
                # A common target across servo candidates. Identical sensor
                # noise in target and rollout can otherwise cancel oscillation
                # in their difference and hide poor absolute handwriting.
                import copy
                reference_cfg = copy.deepcopy(pm.cfg)
                reference_cfg = reference_cfg.replace(nose=replace(reference_cfg.nose,
                    hall_noise=0.0, velocity_source="legacy_true", inner_hz=400.0))
                reference_pm = RJ.build(reference_cfg)
            sh["ref"] = ST.run(reference_pm, self._scenario(), FWConfig(seed=sh["fw_seed"], imu_noise=sh["p"]["imu_noise"]),
                               seed=sh["seed"])
            self.stats["ref_runs"] += 1
            self.stats["sim_s"] += self.episode_s + self.settle_s
        p = sh["p"]
        free = bool(self.rng.uniform() < self.p_free)
        from stabpen import signals as sg
        if free:
            tr = None
            self.amp = 0.0
        else:
            drawn_frequency = p["f0"] if self.rng.uniform() < 0.9 else float(self.rng.uniform(4.0, 12.0))
            if self.respect_fixed_frequency and "f0" in self.fixed_params:
                drawn_frequency = self.fixed_params["f0"]
            spec = sg.TremorSpec(f0=drawn_frequency,
                                 amp_pk=p["amp"], f_jitter=p["f_jitter"], am_depth=p["am_depth"])
            tr = sg.tremor(sh["itx"].t, spec, np.random.default_rng(int(self.rng.integers(1 << 30))))
            self.amp = p["amp"]
            self.f0 = spec.f0
        from sim2 import sensors as SS
        akf = dict(SS.revh_params())
        self.policy = Policy(model=None)
        self.policy_env_action = np.zeros(3)
        fw = FWConfig(nose="tremor", akf=akf, guard=self.guard, det=self.det, tracker=self.tracker,
                      policy=_EnvPolicy(self), seed=sh["fw_seed"], imu_noise=p["imu_noise"])
        self.st = ST.RevJStepper(pm, self._scenario(tr), fw, {}, mu=p["tyre_mu"], record=False, seed=sh["seed"])
        self.nsub = int(round(DECIM * 0.5e-3 / pm.m.opt.timestep))
        self.ref_t = sh["ref"]["t"]
        self.ref_ink = sh["ref"].ink()
        self.ref_con = sh["ref"]["contact"]
        self.reference = InkReference(self.ref_t, self.ref_ink, self.ref_con)
        self.s_ball = pm.ids["site:ball"]
        self.prev = np.zeros(3)
        self.st.advance(int(round(self.settle_s / pm.m.opt.timestep)))
        self._t_wall = time.time()
        self.ep_ret = 0.0
        self.ep_n = 0
        self.ep_err = []
        self.ep_missing = []
        self.ep_extra = []
        self.ep_pcu = []
        obs = self._obs()
        self.stats["wall_s"] += time.time() - t0
        return obs, {"free": free, "writer": sh["w"]}

    def _obs(self):
        pol = self.st.fw.policy
        return pol.obs(self.st.fw) if self.st.fw.tracker is not None else np.zeros(N_OBS, np.float32)

    def step(self, action):
        a = np.asarray(action, dtype=np.float64)
        if a.shape != (3,) or not np.all(np.isfinite(a)):
            raise ValueError("action must be a finite three-vector")
        a = np.clip(a, -1.0, 1.0)
        self.policy_env_action = a
        t0 = time.time()
        metrics = advance_scored(self.st, self.nsub, self.reference, self.ink_cost)
        r = -metrics["cost"]
        r -= 0.005 * float(np.sum(a * a))
        self.prev = a
        self.ep_ret += r
        self.ep_n += 1
        self.ep_err.append((metrics["error_sq_m2"], metrics["reference_fraction"]))
        self.ep_missing.append(metrics["missing_fraction"])
        self.ep_extra.append(metrics["extra_fraction"])
        self.ep_pcu.append(self.st.servo.P_cu)
        trunc = self.st.done()
        self.stats["env_steps"] += 1
        self.stats["wall_s"] += time.time() - t0
        if trunc:
            self.stats["episodes"] += 1
            self.stats["sim_s"] += self.episode_s + self.settle_s
            err = np.asarray(self.ep_err)
            rms = float(np.sqrt(err[:, 0].sum() / max(err[:, 1].sum(), 1e-30))) * 1e6
            self.ep_log.append({"ep": self.stats["episodes"], "amp_mm": self.amp * 1e3, "ret": self.ep_ret,
                                "err_rms_um": rms, "steps": self.ep_n,
                                "missing_ink_fraction": float(np.mean(self.ep_missing)),
                                "extra_ink_fraction": float(np.mean(self.ep_extra)),
                                "coil_power_W": float(np.mean(self.ep_pcu)),
                                "coil_temperature_C": max(c.T for c in self.st.servo.coils)})
        return self._obs(), float(r), False, trunc, {"err_um": metrics["error_rms_m"] * 1e6, **metrics,
                                                     "coil_power_W": self.st.servo.P_cu,
                                                     "coil_temperature_C": max(c.T for c in self.st.servo.coils)}


class _EnvPolicy(Policy):
    """The environment's action source for the firmware: the latest action given to env.step."""

    def __init__(self, env):
        super().__init__()
        self.env = env

    def act(self, fw, t, x_model):
        if self.k % DECIM == 0:
            self.a = np.asarray(self.env.policy_env_action, float)
        self.k += 1
        return combine(self, fw)


# ------------------------------------------------------------------------------------------------ training
def train(total_steps: int, out_dir: str, seed: int = 0, ckpt_every: int = 50_000, log=print, n_steps: int = 2500,
          lr: float = 3e-4) -> Dict:
    """PPO training; resumable: when checkpoints exist in out_dir the latest is loaded and training continues to
    total_steps (the environment's random stream restarts from a new seed; compute is accumulated in train_log.json)."""
    import glob
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
    torch.set_num_threads(1)
    os.makedirs(out_dir, exist_ok=True)
    logp = os.path.join(out_dir, "train_log.json")
    prev = json.load(open(logp)) if os.path.exists(logp) else {"segments": [], "episodes": []}
    cks = sorted(glob.glob(os.path.join(out_dir, "ppo_revj_*_steps.zip")), key=lambda p: int(p.split("_")[-2]))
    done = int(cks[-1].split("_")[-2]) if cks else 0
    env = RevJTremorEnv(seed=seed + 1000 * len(prev["segments"]))
    if done > 0:
        model = PPO.load(cks[-1], env=env, device="cpu")
        log(f"[rl] resuming from {os.path.basename(cks[-1])}")
    else:
        model = PPO("MlpPolicy", env, n_steps=n_steps, batch_size=500, n_epochs=5, learning_rate=lr, gamma=0.9,
                    gae_lambda=0.9, clip_range=0.2, ent_coef=0.0, seed=seed, verbose=0,
                    policy_kwargs={"net_arch": [64, 64], "activation_fn": torch.nn.Tanh, "log_std_init": -1.0})
    t0 = time.time()

    class _Log(BaseCallback):
        def _on_rollout_end(self):
            seg = {"start_steps": done, "steps": int(self.model.num_timesteps), "wall_s": time.time() - t0,
                   "env": dict(env.stats)}
            json.dump({"segments": prev["segments"] + [seg], "episodes": prev["episodes"] + env.ep_log},
                      open(logp, "w"), indent=1)

        def _on_step(self):
            return True
    cb = [CheckpointCallback(save_freq=ckpt_every, save_path=out_dir, name_prefix="ppo_revj"), _Log()]
    remaining = max(0, total_steps - done)
    if remaining > 0:
        model.learn(total_timesteps=remaining, callback=cb, progress_bar=False, reset_num_timesteps=(done == 0))
    model.save(os.path.join(out_dir, "ppo_revj_final"))
    seg = {"start_steps": done, "steps": int(model.num_timesteps), "wall_s": time.time() - t0, "env": dict(env.stats)}
    out = {"segments": prev["segments"] + [seg], "episodes": prev["episodes"] + env.ep_log}
    json.dump(out, open(logp, "w"), indent=1)
    stats = {"total_steps": int(model.num_timesteps), "wall_s_all_segments": float(sum(s["wall_s"] for s in out["segments"])),
             "episodes": len(out["episodes"]), "segments": len(out["segments"])}
    return stats


def load(path: str):
    from stable_baselines3 import PPO
    return PPO.load(path, device="cpu")
