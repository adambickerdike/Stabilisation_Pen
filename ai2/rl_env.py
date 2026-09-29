"""Task 3: a Gymnasium environment for learned shared control of the nose, with a swappable plant backend.

Evidence status: SIMULATION tooling.

What the policy decides (and why this, not the nose command itself).  Separating tremor from writing is an
estimation problem with a known loss, which supervised learning solves directly (learned.py).  What is a sequential
decision is HOW MUCH of an aggressive estimate to use: the pen must decide, from what it senses, whether a strong
("listening") tremor estimate is trustworthy now, knowing that a wrong decision on tremor-free writing distorts the
user's letters.  The policy therefore acts as the arbitration (shared-control) function:

    q(t) = -[ w(t) d_listen(t + delta) + (1 - w(t)) d_revh(t + delta) ]         (lag 0, causal)

with d_listen the fixed-lag RTS smoother's causal estimate (ungated, the listening model) and d_revh the Rev H
tracker's own gated output.  w is chosen every 20 ms from causal features.  The reward per decision is the reduction
of the squared tremor residual on pen-down samples against the Rev H tracker alone, normalised by (0.3 mm)^2; on
tremor-free writing any w > 0 costs reward (false correction).

A second environment, ResidualEnv, is the direct alternative for comparison: residual RL on the nose command itself
(Johannink et al. 2019; Silver et al. 2018): every 2 ms the policy adds a bounded correction to the model-based
stack's estimate, q = -(b(t + delta) + 0.2 mm x a), from the recent sensor features, with the same reward per step.

Backends (the plant interface; sim2 can supply its own):
  ReplayBackend  HW1 replay (the project's convention): the model-based estimates and features are computed on the
                 nose-held run's sensor streams, the ink error from the true handle disturbance assuming the nose
                 servo tracks its command with its compensated delay.  The final evaluation of any policy runs the
                 full HW1 closed loop (stage rl).
  A sim2 backend implements `n_episodes()` and `episode(i) -> dict` with the same keys (see REQUIRED_KEYS), or steps
  its own plant inside `step`.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import learned as LE

ensure_paths()
import gymnasium as gym  # noqa: E402
from gymnasium import spaces  # noqa: E402

REQUIRED_KEYS = ("D", "dh", "Y", "mask", "ratio", "amp", "f_hat", "gate", "X")
DECIM = 10                  # 500 Hz steps per decision (20 ms)
NORM = (0.3e-3) ** 2


class ReplayBackend:
    """Episodes from precomputed HW1 samples (data.py npz with the model-based arrays)."""

    def __init__(self, samples: List[Dict]):
        self.samples = [s for s in samples if all(k in s for k in REQUIRED_KEYS)]

    def n_episodes(self) -> int:
        return len(self.samples)

    def episode(self, i: int) -> Dict:
        return self.samples[i]


def features(ep: Dict) -> np.ndarray:
    """Causal per-step observation features (T, 9): detector ratio / 10, line amplitude / 1 mm, frequency / 10 Hz,
    hysteresis gate, RMS of the listening estimate and of the Rev H estimate over the last 0.2 s (/ 1 mm), their
    disagreement RMS (/ 1 mm), pen-down fraction over the last 20 ms, accelerometer RMS over 0.2 s (/ 10 m/s^2)."""
    T = len(ep["X"])
    D0 = ep["D"][:, 0]
    dh = ep["dh"]

    def run_rms(x, n):
        c = np.cumsum(np.r_[0.0, np.sum(np.asarray(x, float) ** 2, axis=-1) if np.ndim(x) > 1 else np.asarray(x, float) ** 2])
        i = np.arange(1, T + 1)
        j = np.maximum(0, i - n)
        return np.sqrt((c[i] - c[j]) / np.maximum(i - j, 1))
    con = ep["X"][:, 6]
    cc = np.cumsum(np.r_[0.0, con])
    i = np.arange(1, T + 1); j = np.maximum(0, i - DECIM)
    confrac = (cc[i] - cc[j]) / np.maximum(i - j, 1)
    acc = ep["X"][:, 0:2]
    F = np.column_stack([ep["ratio"] / 10.0, ep["amp"] / 1e-3, ep["f_hat"] / 10.0, ep["gate"],
                         run_rms(D0, 100) / 1e-3, run_rms(dh, 100) / 1e-3, run_rms(D0 - dh, 100) / 1e-3,
                         confrac, run_rms(acc, 100) / 10.0])
    return np.nan_to_num(F.astype(np.float32))


class GateEnv(gym.Env):
    """Shared-control arbitration environment (see the module docstring).  Observation = features + previous w."""
    metadata = {"render_modes": []}

    def __init__(self, backend, episode_s: float = 4.0, seed: int = 0, w_max: float = 1.0, deterministic_start: bool = False):
        super().__init__()
        self.backend = backend
        self.n_dec = int(round(episode_s * 500 / DECIM))
        self.w_max = w_max
        self.rng = np.random.default_rng(seed)
        self.deterministic_start = deterministic_start
        self.observation_space = spaces.Box(-10.0, 10.0, shape=(10,), dtype=np.float32)
        self.action_space = spaces.Box(0.0, 1.0, shape=(1,), dtype=np.float32)
        self._cache: Dict[int, np.ndarray] = {}

    def _obs(self):
        k = self.k0 + self.j * DECIM - 1
        f = self.F[max(k, 0)]
        return np.r_[f, self.w_prev].astype(np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        i = int(options["episode"]) if options and "episode" in options else int(self.rng.integers(self.backend.n_episodes()))
        self.ep = self.backend.episode(i)
        if i not in self._cache:
            self._cache[i] = features(self.ep)
        self.F = self._cache[i]
        T = len(self.F)
        need = self.n_dec * DECIM + DECIM
        if options and options.get("full"):
            self.k0 = DECIM
            self.n_run = (T - DECIM) // DECIM - 1
        else:
            self.k0 = DECIM if (self.deterministic_start or T <= need + DECIM) else int(self.rng.integers(DECIM, T - need))
            self.n_run = min(self.n_dec, (T - self.k0) // DECIM - 1)
        self.j = 0
        self.w_prev = 0.0
        return self._obs(), {}

    def step(self, action):
        w = float(np.clip(np.asarray(action).reshape(-1)[0], 0.0, 1.0)) * self.w_max
        a = self.k0 + self.j * DECIM
        b = a + DECIM
        m = self.ep["mask"][a:b] > 0.5
        r = 0.0
        if m.any():
            d = self.ep["Y"][a:b, 0][m]
            dl = self.ep["D"][a:b, 0][m]
            dr = self.ep["dh"][a:b][m]
            e = np.sum((d - (w * dl + (1 - w) * dr)) ** 2, axis=1)
            e0 = np.sum((d - dr) ** 2, axis=1)
            r = float(np.mean(e0 - e)) / NORM
        r -= 0.02 * abs(w - self.w_prev)                  # smoothness (a jumping arbitration is felt)
        self.w_prev = w
        self.j += 1
        done = self.j >= self.n_run
        return self._obs(), r, done, False, {"w": w}


def policy_weights(policy_fn, ep: Dict) -> np.ndarray:
    """Run a policy (obs -> w) over a whole episode; returns w per 500 Hz step (zero-order hold)."""
    env = GateEnv(ReplayBackend([ep]))
    obs, _ = env.reset(options={"episode": 0, "full": True})
    T = len(ep["X"])
    w = np.zeros(T)
    done = False
    while not done:
        a = policy_fn(obs)
        k = env.k0 + env.j * DECIM
        obs, r, done, _, info = env.step(a)
        w[k:k + DECIM] = info["w"]
    return w


def model_based_weight(ep: Dict, amp_lo: float, amp_hi: float) -> np.ndarray:
    """The model-based arbitration for comparison: hysteresis gate x amplitude gate (delayed.gate_values)."""
    g = np.asarray(ep["gate"], float)
    if amp_hi > amp_lo:
        g = g * np.clip((np.asarray(ep["amp"], float) - amp_lo) / (amp_hi - amp_lo), 0.0, 1.0)
    return g


# ------------------------------------------------------------------ residual RL on the command (comparison)
RES_HIST = 8               # 500 Hz steps of sensor history in the observation (16 ms)
RES_SCALE = 0.2e-3         # m per unit action


def residual_features(ep: Dict, amp_gate=(0.0, 0.0)) -> np.ndarray:
    """(T, 44) causal features: the last RES_HIST steps of accelerometer and page-sensor increments (fusion scaling),
    the model-based stack's estimate b, the ungated listening estimate and the Rev H estimate (/ 1 mm), the gate,
    the effective gate, line amplitude (/ 1 mm), peak ratio (/ 10), frequency (/ 10 Hz) and contact."""
    X = np.asarray(ep["X"], np.float32)
    T = len(X)
    B, g = LE.base_estimate(ep, *amp_gate)
    cols = []
    for h in range(RES_HIST):
        sh = np.zeros((T, 4), np.float32)
        sh[h:] = X[:T - h, 0:4] if h else X[:, 0:4]
        cols.append(np.clip(sh, -20, 20))
    cols.append(B[:, 0] / 1e-3)
    cols.append(np.asarray(ep["D"][:, 0], float) / 1e-3)
    cols.append(np.asarray(ep["dh"], float) / 1e-3)
    cols.append(np.column_stack([ep["gate"], g, np.asarray(ep["amp"]) / 1e-3, np.asarray(ep["ratio"]) / 10.0,
                                 np.asarray(ep["f_hat"]) / 10.0, X[:, 6]]))
    return np.nan_to_num(np.concatenate(cols, axis=1).astype(np.float32)), B[:, 0]


class ResidualEnv(gym.Env):
    """Residual RL on the command: q = -(b + RES_SCALE x a) every 2 ms; reward = reduction of the squared residual
    against the model-based stack b (normalised by (0.3 mm)^2) minus a small action cost."""
    metadata = {"render_modes": []}

    def __init__(self, backend, episode_s: float = 4.0, seed: int = 0, amp_gate=(0.0, 0.0)):
        super().__init__()
        self.backend = backend
        self.n_steps = int(round(episode_s * 500))
        self.rng = np.random.default_rng(seed)
        self.amp_gate = tuple(amp_gate)
        self.observation_space = spaces.Box(-50.0, 50.0, shape=(4 * RES_HIST + 14,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self._cache: Dict[int, tuple] = {}

    def _obs(self):
        return np.r_[self.F[self.k - 1], self.a_prev].astype(np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        i = int(options["episode"]) if options and "episode" in options else int(self.rng.integers(self.backend.n_episodes()))
        self.ep = self.backend.episode(i)
        if i not in self._cache:
            self._cache[i] = residual_features(self.ep, self.amp_gate)
        self.F, self.b = self._cache[i]
        T = len(self.F)
        if options and options.get("full"):
            self.k, self.k_end = RES_HIST, T
        else:
            self.k = RES_HIST if T <= self.n_steps + RES_HIST + 1 else int(self.rng.integers(RES_HIST, T - self.n_steps))
            self.k_end = min(T, self.k + self.n_steps)
        self.a_prev = np.zeros(2, np.float32)
        return self._obs(), {}

    def step(self, action):
        a = np.clip(np.asarray(action, np.float32).reshape(-1)[:2], -1.0, 1.0)
        k = self.k
        r = 0.0
        if self.ep["mask"][k] > 0.5:
            d = np.asarray(self.ep["Y"][k, 0], float)
            e0 = float(np.sum((d - self.b[k]) ** 2))
            e = float(np.sum((d - self.b[k] - RES_SCALE * a) ** 2))
            r = (e0 - e) / NORM
        r -= 0.002 * float(np.sum(a * a))
        self.a_prev = a
        self.k += 1
        done = self.k >= self.k_end
        return (self._obs() if not done else np.r_[self.F[self.k - 1], a].astype(np.float32)), r, done, False, {}


def residual_actions(policy_fn, ep: Dict, amp_gate=(0.0, 0.0)) -> np.ndarray:
    """The residual policy's actions (T, 2) over a whole episode, step by step (it sees its previous action); zero
    before the sensor history fills."""
    F, _ = residual_features(ep, amp_gate)
    T = len(F)
    A = np.zeros((T, 2))
    a_prev = np.zeros(2, np.float32)
    for k in range(RES_HIST, T):
        a = np.clip(np.asarray(policy_fn(np.r_[F[k - 1], a_prev].astype(np.float32)), np.float32).reshape(-1)[:2], -1, 1)
        A[k] = a
        a_prev = a
    return A


def residual_estimate(policy_fn, ep: Dict, amp_gate=(0.0, 0.0)) -> np.ndarray:
    """The residual policy's estimate (T, 2): the model-based stack's estimate b + RES_SCALE x action."""
    b = LE.base_estimate(ep, *amp_gate)[0][:, 0]
    return b + RES_SCALE * residual_actions(policy_fn, ep, amp_gate)
