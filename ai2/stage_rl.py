"""Stage rl (task 3): train shared-control policies with Stable-Baselines3 on the domain-randomised samples (replay
backend), select on the tuning writers, and keep them for the closed-loop check (stage cl) and the test.

  arbiter   GateEnv: how much of the listening (fixed-lag RTS) estimate to use against the Rev H tracker, every 20 ms
            (PPO and SAC, same budget rule)
  residual  ResidualEnv: a bounded correction added to the model-based stack's estimate every 2 ms (PPO)

Evidence status: SIMULATION.  Compute is recorded (wall-clock minutes and environment steps, one CPU thread).
Selection rules (fixed before training; tuning writers 100-103, seed 300, replay objective, full episodes):
  RL1 arbiter: highest mean reward among checkpoints whose mean weight on every tremor-free episode is <= 0.05;
  RL2 residual: highest mean reward among checkpoints whose added output on tremor-free writing is <= 10 um RMS.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import BUILD_DIR, ensure_paths
from . import common as C
from . import data as DA
from . import learned as LE
from . import rl_env as RE
from . import stage_learn_data as SLD

ensure_paths()

POLICY_DIR = BUILD_DIR / "rl"


def _res(e, m):
    return float(np.sqrt(np.mean(e[m])) * 1e6) if m.any() else float("nan")


def summarise(rows: List[Dict]) -> Dict:
    big = [r for r in rows if r["amp_mm"] >= 1.0]
    small = [r for r in rows if 0 < r["amp_mm"] < 0.5]
    free = [r for r in rows if r["amp_mm"] == 0]
    f = lambda rr, k: float(np.mean([r[k] for r in rr])) if rr else float("nan")  # noqa: E731
    return {"reward_mean": f(rows, "reward"), "res_1_2mm_um": f(big, "res_um"), "res_base_1_2mm_um": f(big, "res_base_um"),
            "res_revh_1_2mm_um": f(big, "res_revh_um"), "res_0p3mm_um": f(small, "res_um"),
            "res_base_0p3mm_um": f(small, "res_base_um"), "res_revh_0p3mm_um": f(small, "res_revh_um"),
            "w_tremor_free_max": float(max([r.get("w_mean", 0.0) for r in free] or [0.0])),
            "added_tremor_free_um": f(free, "added_um"), "out_tremor_free_um": f(free, "out_um")}


def score_estimate(ep: Dict, est: np.ndarray, base: np.ndarray, extra: Dict) -> Dict:
    m = ep["mask"] > 0.5
    d = np.asarray(ep["Y"][:, 0], float)
    e = np.sum((d - est) ** 2, axis=1); eb = np.sum((d - base) ** 2, axis=1)
    er = np.sum((d - np.asarray(ep["dh"], float)) ** 2, axis=1)
    return {"f0": ep["spec"].get("f0", 0.0), "amp_mm": ep["spec"].get("amp", 0.0) * 1e3, "res_um": _res(e, m),
            "res_base_um": _res(eb, m), "res_revh_um": _res(er, m), "reward": float(np.mean(eb[m] - e[m]) / RE.NORM) if m.any() else 0.0,
            "added_um": _res(np.sum((est - base) ** 2, axis=1), m), "out_um": _res(np.sum(est ** 2, axis=1), m), **extra}


def evaluate_arbiter(policy_fn, episodes: List[Dict]) -> Dict:
    """Arbiter policies on full episodes; reward against the Rev H tracker (base = Rev H)."""
    rows = []
    for ep in episodes:
        w = RE.policy_weights(policy_fn, ep)
        m = ep["mask"] > 0.5
        dl = np.asarray(ep["D"][:, 0], float); dr = np.asarray(ep["dh"], float)
        est = w[:, None] * dl + (1 - w[:, None]) * dr
        rows.append(score_estimate(ep, est, dr, {"w_mean": float(np.mean(w[m])) if m.any() else 0.0}))
    return {**summarise(rows), "rows": rows}


def evaluate_weights(weights: List[np.ndarray], episodes: List[Dict]) -> Dict:
    rows = []
    for ep, w in zip(episodes, weights):
        m = ep["mask"] > 0.5
        dl = np.asarray(ep["D"][:, 0], float); dr = np.asarray(ep["dh"], float)
        est = w[:, None] * dl + (1 - w[:, None]) * dr
        rows.append(score_estimate(ep, est, dr, {"w_mean": float(np.mean(w[m])) if m.any() else 0.0}))
    return {**summarise(rows), "rows": rows}


def evaluate_residual(policy_fn, episodes: List[Dict], amp_gate) -> Dict:
    rows = []
    for ep in episodes:
        est = RE.residual_estimate(policy_fn, ep, amp_gate)
        base = LE.base_estimate(ep, *amp_gate)[0][:, 0]
        rows.append(score_estimate(ep, est, base, {}))
    return {**summarise(rows), "rows": rows}


def _train(algo: str, make_env, budget: int, n_eval: int, evaluate, name: str, ok_fn) -> Dict:
    import torch
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.vec_env import DummyVecEnv
    torch.set_num_threads(1)
    t0 = time.time()
    env = DummyVecEnv([lambda i=i: make_env(100 + i) for i in range(4)])
    if algo == "PPO":
        model = PPO("MlpPolicy", env, n_steps=1024, batch_size=256, n_epochs=8, learning_rate=3e-4, gamma=0.98,
                    gae_lambda=0.95, ent_coef=0.0, policy_kwargs={"net_arch": [64, 64]}, seed=0, verbose=0, device="cpu")
    else:
        model = SAC("MlpPolicy", env, learning_rate=3e-4, buffer_size=200_000, batch_size=256, gamma=0.98,
                    train_freq=4, gradient_steps=1, policy_kwargs={"net_arch": [64, 64]}, seed=0, verbose=0, device="cpu")
    checkpoints, done, t_train = [], 0, 0.0
    chunk = budget // n_eval
    while done < budget:
        t1 = time.time()
        model.learn(total_timesteps=chunk, reset_num_timesteps=False)
        t_train += time.time() - t1
        done += chunk
        sc = evaluate(fast_policy(model))
        path = POLICY_DIR / f"{name}_{done}.zip"
        model.save(path)
        checkpoints.append({"steps": done, "minutes": (time.time() - t0) / 60.0, "path": str(path), "ok": bool(ok_fn(sc)),
                            **{k: v for k, v in sc.items() if k != "rows"}})
        C.log(f"[rl] {name} {done} steps ({(time.time() - t0) / 60:.1f} min): reward {sc['reward_mean']:.4f} res 1-2 mm "
              f"{sc['res_1_2mm_um']:.0f} (base {sc['res_base_1_2mm_um']:.0f}, Rev H {sc['res_revh_1_2mm_um']:.0f}) 0.3 mm "
              f"{sc['res_0p3mm_um']:.0f} tremor-free w {sc['w_tremor_free_max']:.3f} added {sc['added_tremor_free_um']:.1f} um")
    ok = [c for c in checkpoints if c["ok"]]
    best = max(ok or checkpoints, key=lambda c: c["reward_mean"])
    return {"algorithm": algo, "checkpoints": checkpoints, "best": best, "passes_rule": bool(ok),
            "wall_min": (time.time() - t0) / 60.0, "train_min": t_train / 60.0, "env_steps": done, "threads": 1}


def run(quick: bool, workers: int):
    DA.set_quick(quick)
    n = SLD.N_TRAIN_QUICK if quick else SLD.N_TRAIN
    mp = SLD.model_params(quick)
    ag = tuple(mp["amp_gate"])
    train = [s for s in DA.load_set("train", n) if all(k in s for k in RE.REQUIRED_KEYS)]
    tune = SLD.load_tuning()
    C.log(f"[rl] {len(train)} training episodes, {len(tune)} tuning episodes; amp gate {ag}")
    global POLICY_DIR
    POLICY_DIR = BUILD_DIR / ("rl_quick" if quick else "rl")
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    out = {"n_train": len(train), "n_tune": len(tune), "amp_gate": ag, "policies": {},
           "rules": {"RL1": "arbiter: highest mean tuning reward with mean weight <= 0.05 on every tremor-free episode",
                     "RL2": "residual: highest mean tuning reward with added output <= 10 um RMS on tremor-free writing"}}
    # the model-based arbitration on the same tuning episodes (hysteresis gate x the D2b amplitude gate)
    out["model_based_arbiter"] = {k: v for k, v in evaluate_weights([RE.model_based_weight(ep, *ag) for ep in tune], tune).items()}
    C.log(f"[rl] model-based arbiter on tuning: " + str({k: round(v, 4) for k, v in out['model_based_arbiter'].items() if k != 'rows'}))
    q = 20 if quick else 1
    backend = RE.ReplayBackend(train)
    specs = [("arbiter_ppo", "PPO", lambda s: RE.GateEnv(backend, seed=s), 600_000 // q, 6,
              lambda pf: evaluate_arbiter(pf, tune), lambda sc: sc["w_tremor_free_max"] <= 0.05),
             # added after the first PPO run: its later checkpoints opened on tremor-free writing (w 0.06-0.11) because
             # tremor-free episodes carry little reward; the supervised models' false-correction weight (4) is applied
             # to the reward of tremor-free training episodes (the policy's observation is unchanged)
             ("arbiter_ppo_fc", "PPO", lambda s: RE.GateEnv(backend, seed=s, fc_weight=4.0), 600_000 // q, 6,
              lambda pf: evaluate_arbiter(pf, tune), lambda sc: sc["w_tremor_free_max"] <= 0.05),
             ("arbiter_sac", "SAC", lambda s: RE.GateEnv(backend, seed=s), 80_000 // q, 4,
              lambda pf: evaluate_arbiter(pf, tune), lambda sc: sc["w_tremor_free_max"] <= 0.05),
             ("arbiter_sac_fc", "SAC", lambda s: RE.GateEnv(backend, seed=s, fc_weight=4.0), 80_000 // q, 4,
              lambda pf: evaluate_arbiter(pf, tune), lambda sc: sc["w_tremor_free_max"] <= 0.05),
             ("residual_ppo", "PPO", lambda s: RE.ResidualEnv(backend, seed=s, amp_gate=ag), 400_000 // q, 4,
              lambda pf: evaluate_residual(pf, tune, ag), lambda sc: sc["added_tremor_free_um"] <= 10.0),
             ("residual_ppo_fc", "PPO", lambda s: RE.ResidualEnv(backend, seed=s, amp_gate=ag, fc_weight=4.0), 400_000 // q, 4,
              lambda pf: evaluate_residual(pf, tune, ag), lambda sc: sc["added_tremor_free_um"] <= 10.0)]
    prev = C.load("rl", quick) or {}
    for name, algo, mk, budget, n_eval, ev, ok_fn in specs:
        old = (prev.get("policies") or {}).get(name)
        if old and old.get("env_steps") == budget and all(Path(c["path"]).exists() for c in old["checkpoints"]):
            out["policies"][name] = old                     # already trained with this budget (resume)
            C.log(f"[rl] {name}: reusing the trained run ({budget} steps)")
            continue
        out["policies"][name] = _train(algo, mk, budget, n_eval, ev, name, ok_fn)
        C.save("rl", out, quick)
    arb = [(k, v) for k, v in out["policies"].items() if k.startswith("arbiter") and v["passes_rule"]]
    out["chosen_arbiter"] = max(arb, key=lambda kv: kv[1]["best"]["reward_mean"])[0] if arb else None
    resp = [(k, v) for k, v in out["policies"].items() if k.startswith("residual") and v["passes_rule"]]
    out["chosen_residual"] = max(resp, key=lambda kv: kv[1]["best"]["reward_mean"])[0] if resp else None
    out["compute_min_total"] = float(sum(v["wall_min"] for v in out["policies"].values()))
    C.save("rl", out, quick)
    C.log(f"[rl] chosen arbiter {out['chosen_arbiter']}, residual {out['chosen_residual']}; {out['compute_min_total']:.0f} min")
    return out


def fast_policy(model):
    """The deterministic action of an SB3 PPO or SAC MlpPolicy as a plain numpy function (the same result as
    model.predict(obs, deterministic=True) for a Box action space; about 20x faster per call, which matters for the
    step-by-step residual policy)."""
    from stable_baselines3 import SAC
    sd = {k: v.detach().cpu().numpy().astype(np.float64) for k, v in model.policy.state_dict().items()}
    lo, hi = model.action_space.low.astype(np.float64), model.action_space.high.astype(np.float64)
    if isinstance(model, SAC):
        W = [(sd["actor.latent_pi.0.weight"], sd["actor.latent_pi.0.bias"]), (sd["actor.latent_pi.2.weight"], sd["actor.latent_pi.2.bias"])]
        Wm, bm = sd["actor.mu.weight"], sd["actor.mu.bias"]

        def f(o):
            h = np.asarray(o, np.float64)
            for Wi, bi in W:
                h = np.maximum(Wi @ h + bi, 0.0)
            a = np.tanh(Wm @ h + bm)
            return (lo + 0.5 * (a + 1.0) * (hi - lo)).astype(np.float32)
        return f
    W = [(sd["mlp_extractor.policy_net.0.weight"], sd["mlp_extractor.policy_net.0.bias"]),
         (sd["mlp_extractor.policy_net.2.weight"], sd["mlp_extractor.policy_net.2.bias"])]
    Wa, ba = sd["action_net.weight"], sd["action_net.bias"]

    def g(o):
        h = np.asarray(o, np.float64)
        for Wi, bi in W:
            h = np.tanh(Wi @ h + bi)
        return np.clip(Wa @ h + ba, lo, hi).astype(np.float32)
    return g


def load_policy(path: str):
    from stable_baselines3 import PPO, SAC
    cls = PPO if "ppo" in str(path).split("/")[-1] else SAC
    return fast_policy(cls.load(path, device="cpu"))
