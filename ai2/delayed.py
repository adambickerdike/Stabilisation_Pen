r"""Task 1: delayed ink.  The nose lets the ink trail the hand by a lag, so each stroke is cleaned with look-ahead.

Evidence status: SIMULATION (model HW1 via aiprior conventions; synthetic writers and tremor).

Command (smoothers.py for the estimators).  At tick t the nose command, acting at t + delta (servo group delay), is

    q(t) = [x_h(s | Y_t) - x_h(t + delta | Y_t)]  -  g(t) d(s | Y_t),        s = t + delta - lambda(t)

    x_h   the handle filter's position (fixed-lag smoothed at s, predicted at t + delta).  Only the DIFFERENCE is used:
          the handle's own displacement between s and t + delta, which the IMU + page sensor measure well even while
          the absolute position is being re-anchored after a pen lift;
    d     the tremor estimate at s, smoothed with look-ahead lambda - delta - 2 ms (RTS, fixed-lag Wiener or learned);
    g     output gain x the running tremor-line detector's gate (no tremor line: g = 0, the ink is only delayed).
With lambda = 0 the command is -g d(t + delta): a causal tracker.

Lag policies (what the writer sees: the ball trails the pen body by |q| and the ink appears lambda after the hand):
  catchup  (Rev H hardware) lambda = 0 at touchdown; while the pen writes, lambda grows at rate alpha (the ink moves at
           1 - alpha of the hand's speed) up to lambda_max; when the pen senses the end of a stroke (the hand stops:
           speed below v_stop for t_stop, or the lift starts: hand height above z_warn, sensed by the refill slide) the
           lag collapses at rate beta (the ink catches up at 1 + beta times the hand's speed).  The part of the stroke
           the ink cannot reach before the ball leaves the paper is lost (reported as coverage).
  hold     lambda = min(lambda_max, time since touchdown), no catch-up: the naive fixed lag; the last lambda of each
           stroke is lost.
  limit    the ball's contact is delayed by lambda as well (a Z-actuated refill, not in Rev H): the upper bound.
           Evaluated by shifting the ink record by lambda (the refill's Z motion itself is not simulated).
  oracle   perfect knowledge of the tremor and the handle (same policy): the delayed-ink limit of the mechanism.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import smoothers as SM

ensure_paths()
from aiprior import core as CO  # noqa: E402
from aiprior import study as SD  # noqa: E402
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting.plant import RIDX, Result  # noqa: E402

LAG_GRID = np.round(np.arange(0.0, 0.2501, 0.005), 4)       # s
OUT_EVERY = 4                                                  # estimator output every 4 ticks (500 Hz)

# Handle filter (the pen's own position, for the displacement term): the AKF model with the page sensor's real noise
# (3 um) and a responsive intent model.  Chosen on tuning writers (tuning.py stage D0).
HANDLE_DEFAULTS = {"qj": 1000.0, "qt": 1e-10, "qh": 3e-11, "qb": 2e-6, "ra": 10.0, "rp": 1e-11, "tau_decay": 0.3,
                   "w0_hz": 6.26, "tau_w": 0.124, "wmin_hz": 3.58, "wmax_hz": 14.7, "harm": 0.88, "gap_reset": 0.03,
                   "gap_sd": 0.5e-3}
# Tremor smoother: the Rev H tracker's model with a tremor state that listens (the look-ahead and the detector gate
# decide what is tremor).  Chosen on tuning writers (stage D0).
TREMOR_DEFAULTS = {"qj": 0.0275, "qt": 2e-9, "qh": 7e-10, "qb": 2e-6, "ra": 0.075, "rp": 1.16e-9, "tau_decay": 1.0,
                   "w0_hz": 6.26, "tau_w": 0.4, "wmin_hz": 3.58, "wmax_hz": 14.7, "harm": 0.88, "gap_reset": 0.03,
                   "gap_sd": 0.5e-3}
DET_DEFAULTS = {"win": 4.0, "seg": 2.0, "every": 0.05, "min_win": 4.0, "mode": "hyst", "r_on": 5.0, "r_off": 2.5,
                "t_on": 0.5, "t_off": 1.0, "ramp": 0.2}


def pen_travel(travel_mm: float) -> PR.Pen:
    """Rev H with a different usable nose travel (the +-6 mm case stands for the bigger nose of study N; ASSUMPTION:
    same servo, force and moving mass as Rev H)."""
    p = CO.pens()["revH"]
    if abs(travel_mm - p.q_lim * 1e3) < 1e-9:
        return p
    q = travel_mm * 1e-3
    return replace(p, key=f"revH_{travel_mm:g}mm", label=f"Rev H nose, +-{travel_mm:g} mm (ASSUMPTION: same servo)",
                   q_lim=q, q_taper=0.1 * q, q_stop=q + 0.5e-3)


@dataclass
class DelayCfg:
    estimator: str = "rts"                 # rts | window | wiener | learned | oracle
    policy: str = "catchup"                # catchup | hold | limit
    lam_max: float = 0.05                  # s
    alpha: float = 0.5                     # lag growth rate (1 - alpha = ink speed / hand speed while it grows)
    beta: float = 3.0                      # lag collapse rate (the ink catches up at 1 + beta times the hand speed)
    v_stop: float = 4e-3                   # m/s: the hand counts as stopped below this ...
    t_stop: float = 0.004                  # s ... for this long
    z_warn: float = 0.1e-3                 # m: refill-slide lift warning (hand height)
    gain: float = 1.0                      # output gain on the tremor estimate
    gate: str = "detector"                 # detector | none (always 1) | off (never: pure delay)
    fallback: str = "revh"                 # when the gate is closed: "revh" = the Rev H tracker's causal estimate
                                           # (ink as with the Rev H pen), "none" = no correction
    lag_gate: float = 0.5                  # the lag is allowed only while the detector gate is >= this (else 0)
    amp_lo: float = 0.0                    # amplitude gate on the detector's line amplitude (m): the look-ahead
    amp_hi: float = 0.0                    # estimate fades in between amp_lo and amp_hi (0, 0 = off)
    handle: Dict = field(default_factory=dict)
    tremor: Dict = field(default_factory=dict)
    det: Dict = field(default_factory=dict)
    wiener: Dict = field(default_factory=dict)
    learned: Optional[object] = None       # a learned.WindowModel for estimator "learned"

    def key(self) -> str:
        return (f"{self.estimator}_{self.policy}_{self.lam_max * 1e3:.0f}ms_a{self.alpha:g}_b{self.beta:g}"
                f"_g{self.gain:g}_{self.gate}")


# ------------------------------------------------------------------ estimates on a scenario
def gate_values(det: Dict, t_out: np.ndarray, cfg: DelayCfg) -> np.ndarray:
    """The look-ahead estimate's weight: the detector's hysteresis gate x the amplitude gate (see DelayCfg)."""
    if cfg.gate == "none":
        return np.ones(len(t_out))
    if cfg.gate != "detector":
        return np.zeros(len(t_out))
    g = SM.gate_at(det, t_out)
    if cfg.amp_hi > cfg.amp_lo:
        n = np.searchsorted(det["t"], t_out, side="right")
        k = np.clip(n - 1, 0, len(det["t"]) - 1)
        a = np.where(n > 0, det["amp"][k], 0.0)
        g = g * np.clip((a - cfg.amp_lo) / (cfg.amp_hi - cfg.amp_lo), 0.0, 1.0)
    return g


def regate(est: Dict, cfg: DelayCfg) -> Dict:
    """The same estimates with another gate setting (no re-estimation)."""
    out = dict(est)
    out["g"] = gate_values(est["det"], est["t"], cfg)
    return out


def estimates(sc: CO.Scenario, cfg: DelayCfg, lags: Sequence[float] = LAG_GRID, det: Optional[Dict] = None,
              handle_out: Optional[Dict] = None) -> Dict:
    """Everything the command needs, at the estimator output rate (every OUT_EVERY ticks), for every lag of `lags`."""
    st = sc.streams
    delta = PR.servo_group_delay(sc.pen)
    lags = np.asarray(lags, float)
    if handle_out is None:
        hp = dict(HANDLE_DEFAULTS); hp.update(cfg.handle)
        handle_out = SM.rts_fixed_lag(st, hp, lags, delta, out_every=OUT_EVERY)
    t_out = handle_out["t"]
    if det is None:
        dp = dict(DET_DEFAULTS); dp.update(cfg.det)
        det = SM.detector(st, dp)
    g = gate_values(det, t_out, cfg)
    if cfg.estimator == "rts":
        tp = dict(TREMOR_DEFAULTS); tp.update(cfg.tremor)
        D = SM.rts_fixed_lag(st, tp, lags, delta, out_every=OUT_EVERY)["tremor"]
    elif cfg.estimator == "wiener":
        w = SM.wiener_fixed_lag(st, det, lags, delta, cfg.wiener, out_every=OUT_EVERY)
        D = w["tremor"]
    elif cfg.estimator == "window":
        D = SM.window_smoother(st, det, lags, delta, out_every=OUT_EVERY, **cfg.wiener)["tremor"]
    elif cfg.estimator == "learned":
        D = cfg.learned.fixed_lag(st, lags, delta, t_out)
    elif cfg.estimator == "oracle":
        D = oracle_tremor(sc, t_out, lags, delta)
        g = np.ones(len(t_out)) if cfg.gate != "off" else np.zeros(len(t_out))
    else:
        raise KeyError(cfg.estimator)
    # fallback while the gate is closed: the Rev H tracker's causal estimate of the tremor at s (its tick output dh(t')
    # estimates the tremor at t' + delta, so the value for s is dh at s - delta = t - lag)
    Dfb = np.zeros_like(D)
    dh_ticks = None
    if cfg.fallback == "revh" and cfg.estimator != "oracle":
        tt = st.tick_t
        dh_ticks = np.asarray(sc.dh)
        for i, lag in enumerate(lags):
            Dfb[:, i, 0] = np.interp(t_out - lag, tt, sc.dh[:, 0], left=0.0)
            Dfb[:, i, 1] = np.interp(t_out - lag, tt, sc.dh[:, 1], left=0.0)
    return {"t": t_out, "H": handle_out["handle"], "Pn": handle_out["p_now"], "D": D, "Dfb": Dfb, "dh": dh_ticks, "g": g,
            "gain": cfg.gain, "lags": lags, "delta": delta, "det": det, "handle_out": handle_out}


def oracle_tremor(sc: CO.Scenario, t_out, lags, delta) -> np.ndarray:
    clean = sc.wr.su.clean["revH"]
    n = min(len(sc.neutral.t), len(clean.t))
    tr = sc.neutral.t[:n]
    d = sc.neutral.handle[:n] - clean.handle[:n]
    D = np.zeros((len(t_out), len(lags), 2))
    for i, lag in enumerate(lags):
        s = t_out + delta - lag
        D[:, i, 0] = np.interp(s, tr, d[:, 0]); D[:, i, 1] = np.interp(s, tr, d[:, 1])
    return D


def oracle_handle(sc: CO.Scenario, est: Dict) -> Dict:
    """Replace the handle filter by the true handle (the oracle's displacement term)."""
    tr = sc.neutral.t
    h = sc.neutral.handle
    t_out, lags, delta = est["t"], est["lags"], est["delta"]
    H = np.zeros((len(t_out), len(lags), 2))
    for i, lag in enumerate(lags):
        s = t_out + delta - lag
        H[:, i, 0] = np.interp(s, tr, h[:, 0]); H[:, i, 1] = np.interp(s, tr, h[:, 1])
    Pn = np.column_stack([np.interp(t_out + delta, tr, h[:, 0]), np.interp(t_out + delta, tr, h[:, 1])])
    out = dict(est); out.update({"H": H, "Pn": Pn})
    return out


# ------------------------------------------------------------------ the lag policy (what the pen can sense)
def observables(sc: CO.Scenario, est: Dict, lag_speed: float = 0.02) -> Dict:
    """Per tick: sensed contact (axial slide sensor stream, with its latency), lift warning (hand height above z_warn
    on the refill slide; ASSUMPTION: sensed with 1 ms latency) and the intended speed: the speed of (handle - tremor
    estimate) at a lag of `lag_speed` (20 ms of look-ahead, so tremor does not hold the speed up)."""
    st = sc.streams
    tick_t = st.tick_t
    kc = np.searchsorted(st.con_av, tick_t, side="right") - 1
    con = np.where(kc >= 0, st.con[np.clip(kc, 0, len(st.con) - 1)], 0.0) > 0.5
    lift = np.asarray(sc.scn.meta.get("lift"), float)
    tl = sc.scn.t
    z = np.interp(tick_t - 1e-3, tl, lift)
    t_out = est["t"]
    j = int(np.argmin(np.abs(est["lags"] - lag_speed)))
    g = est["g"][:, None]
    xi = est["H"][:, j] - (g * est["gain"] * est["D"][:, j] + (1.0 - g) * est["Dfb"][:, j])
    k10 = max(1, int(round(0.010 / (t_out[1] - t_out[0]))))
    v = np.zeros(len(t_out))
    v[k10:] = np.hypot(*(xi[k10:] - xi[:-k10]).T) / (t_out[k10] - t_out[0])
    v[~np.isfinite(v)] = 0.0
    sp = np.interp(tick_t, t_out, v)
    gate = np.interp(tick_t, t_out, est["g"])
    return {"con": con, "z": z, "speed": sp, "tick_t": tick_t, "gate": gate}


def lag_schedule(obs: Dict, cfg: DelayCfg, Ts: float) -> np.ndarray:
    """lambda per tick (s) for the catchup / hold / limit policies (see the module docstring)."""
    con, z, sp = obs["con"], obs["z"], obs["speed"]
    n = len(con)
    lam = np.zeros(n)
    L = 0.0
    t_slow = 0.0
    t_td = -1.0
    was = False
    for k in range(n):
        c = bool(con[k])
        if cfg.policy == "limit":
            lam[k] = cfg.lam_max
            continue
        if c and not was:
            t_td = k * Ts
            L = 0.0
            t_slow = 0.0
        if not c:
            L = 0.0
        elif cfg.policy == "catchup":
            t_slow = t_slow + Ts if sp[k] < cfg.v_stop else 0.0
            end = (t_slow >= cfg.t_stop) or (z[k] > cfg.z_warn)
            open_ = obs["gate"][k] >= cfg.lag_gate if "gate" in obs else True
            target = 0.0 if (end or not open_) else cfg.lam_max
            dL = target - L
            dL = min(dL, cfg.alpha * Ts) if dL > 0 else max(dL, -cfg.beta * Ts)
            L = min(max(L + dL, 0.0), cfg.lam_max)
        elif cfg.policy == "hold":
            open_ = obs["gate"][k] >= cfg.lag_gate if "gate" in obs else True
            L = min(cfg.lam_max, k * Ts - t_td) if open_ else 0.0
        lam[k] = L
        was = c
    return lam


def command(est: Dict, lam_ticks: np.ndarray, tick_t: np.ndarray) -> np.ndarray:
    """q per tick from the estimates at the output rate, interpolated in time and between lag columns."""
    t_out, lags = est["t"], est["lags"]
    H, Pn, D, g = est["H"], est["Pn"], est["D"], est["g"]
    Dfb = est.get("Dfb")
    gain = est.get("gain", 1.0)
    fo = np.interp(tick_t, t_out, np.arange(len(t_out), dtype=float))
    i0 = np.clip(np.floor(fo).astype(int), 0, len(t_out) - 1)
    i1 = np.clip(i0 + 1, 0, len(t_out) - 1)
    wt = (fo - i0)[:, None]
    fl = np.interp(lam_ticks, lags, np.arange(len(lags), dtype=float))
    j0 = np.clip(np.floor(fl).astype(int), 0, len(lags) - 1)
    j1 = np.clip(j0 + 1, 0, len(lags) - 1)
    wl = (fl - j0)[:, None]

    def at(A):
        a00 = A[i0, j0]; a01 = A[i0, j1]; a10 = A[i1, j0]; a11 = A[i1, j1]
        return (1 - wt) * ((1 - wl) * a00 + wl * a01) + wt * ((1 - wl) * a10 + wl * a11)
    Hs = at(H)
    Ds = at(D)
    Pnt = (1 - wt) * Pn[i0] + wt * Pn[i1]
    gt = np.interp(tick_t, t_out, g)[:, None]
    q = (Hs - Pnt) - gain * gt * Ds
    if est.get("dh") is not None:                   # the Rev H tracker's own tick output, exact at lambda = 0
        dh = est["dh"]
        tq = tick_t - lam_ticks
        fb = np.column_stack([np.interp(tq, tick_t, dh[:, 0], left=0.0), np.interp(tq, tick_t, dh[:, 1], left=0.0)])
        q = q - (1.0 - gt) * fb
    q[~np.isfinite(q)] = 0.0
    return np.ascontiguousarray(q)


# ------------------------------------------------------------------ closed loop and metrics
def run(sc: CO.Scenario, q: np.ndarray, pen: Optional[PR.Pen] = None) -> Result:
    pen = pen or sc.pen
    return PL.run(sc.scn, pen, sc.wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))


def shifted(res: Result, lam: float) -> Result:
    """The 'limit' policy: the ball's contact is delayed by lam with the ink (Z-actuated refill).  The ink record is
    shifted back by lam so the metrics' letter windows and the hand's contact apply to it."""
    rec = res.rec.copy()
    t = res.t
    for key in ("tipx", "tipy", "qx", "qy", "qcx", "qcy"):
        rec[:, RIDX[key]] = np.interp(t + lam, t, res.rec[:, RIDX[key]])
    return Result(rec, dict(res.info))


def coverage(sc: CO.Scenario, res: Result, radius: float = 0.3e-3) -> float:
    """Share of the intended pen-down path (per letter, 1 kHz) that has in-contact ink of the same letter within
    `radius` (0.3 mm, ASSUMPTION; about a tenth of the x-height)."""
    from scipy.spatial import cKDTree
    it = sc.wr.written.intended
    dec = max(1, int(round(1e-3 / (it.t[1] - it.t[0]))))
    t = res.t; ink = res.ink; con = res.contact > 0.5
    hit, tot = 0, 0
    for L in sc.wr.written.letters:
        idx = np.concatenate([np.arange(a, b, dec) for (a, b) in L.strokes])
        idx = idx[np.asarray(it.pen_down)[idx]]
        if len(idx) == 0:
            continue
        m = (t >= L.t0 - 0.01) & (t <= L.t1 + 0.01) & con
        tot += len(idx)
        if not m.any():
            continue
        tree = cKDTree(ink[m])
        d, _ = tree.query(it.xy[idx])
        hit += int(np.sum(d <= radius))
    return hit / max(tot, 1)


def travel_needed(q: np.ndarray, con_ticks: np.ndarray) -> Dict:
    r = np.hypot(q[:, 0], q[:, 1])[con_ticks]
    if r.size == 0:
        return {}
    return {"q_p50_mm": float(np.percentile(r, 50) * 1e3), "q_p95_mm": float(np.percentile(r, 95) * 1e3),
            "q_p99_mm": float(np.percentile(r, 99) * 1e3), "q_max_mm": float(r.max() * 1e3),
            "over_3mm": float(np.mean(r > 3e-3)), "over_6mm": float(np.mean(r > 6e-3))}


def ink_timeline_error(sc: CO.Scenario, res: Result, lam_ticks: np.ndarray, ref: Result) -> float:
    """RMS over contact of |ink(t) - ref_ink(t - lambda(t))|: the delayed ink against a reference ink at the time the
    delayed ink shows (for lambda = 0 the project's false-correction definition)."""
    Ts = sc.Ts
    t = res.t
    delta = PR.servo_group_delay(sc.pen)
    lam = np.interp(t - delta, np.arange(len(lam_ticks)) * Ts, lam_ticks)     # the command issued at t - delta
    s = t - lam
    n = min(len(t), len(ref.t))
    rx = np.interp(s[:n], ref.t, ref.ink[:, 0]); ry = np.interp(s[:n], ref.t, ref.ink[:, 1])
    m = (res.contact[:n] > 0.5) & (np.interp(s[:n], ref.t, ref.contact) > 0.5)
    e = np.column_stack([res.ink[:n, 0] - rx, res.ink[:n, 1] - ry])[m]
    return float(np.sqrt(np.mean(np.sum(e ** 2, axis=1))) * 1e6) if len(e) else float("nan")


def evaluate_run(sc: CO.Scenario, res: Result, pen: PR.Pen, q: np.ndarray, lam: np.ndarray, obs: Dict,
                 extra: bool = True) -> Dict:
    rows = SD.letters_of(sc, res)
    m = SD.metrics(sc, res, rows, travel=False)
    m.update({k: v for k, v in MT.travel(res, pen).items() if k in ("at_travel_limit", "on_stop", "at_force_limit",
                                                                    "q_rms_mm", "q_max_mm", "F_rms_N")})
    if extra:
        m["coverage"] = coverage(sc, res)
        m.update(travel_needed(q, obs["con"]))
        c = obs["con"]
        m["lag_mean_ms"] = float(np.mean(lam[c]) * 1e3) if c.any() else 0.0
        m["lag_p95_ms"] = float(np.percentile(lam[c], 95) * 1e3) if c.any() else 0.0
    return m
