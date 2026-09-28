r"""The acceleration-domain Kalman filter (AKF) of fusion.estimators.akf in PyTorch (SIMULATION tooling).

Same equations as fusion.estimators._akf_run, batched over B recordings that each keep their own sample clocks:

  states per axis (8): intent p, v, a (white jerk q_j); tremor oscillator c1, s1 at the tracked w (q_t); 2nd
      harmonic c2, s2 at 2w (q_h, only with harm = 1); accelerometer bias b (q_b); both axes share w and P.
  accelerometer update  y_a = a - w^2 c1 - 4 w^2 harm c2 + b      (noise r_a), at its acquisition time - 1.04 ms
  page update           y_p = p + c1 + harm c2                     (noise r_p), at its acquisition time: the filter
      rolls back to the snapshot of the last accelerometer sample acquired no later than the page sample, predicts
      to the page time, updates (or re-anchors the position after a gap), and re-applies the later accelerometer
      samples with the frequency each of them was first processed with.  This is the numba algorithm, replayed from
      opt.tracker.schedule; with autograd the snapshots are graph nodes, so the rollback is differentiable exactly.
  frequency tracking    phase rate of the larger fundamental oscillator over the advance of the filter time,
      smoothed with tau_w and clamped to [wmin, wmax] (hard clamp: its gradient goes to the bounds).
  output                tremor predicted to t + horizon + (low-pass group delay); cap at cap_k x the amplitude seen
      during slow motion; frequency gate and amplitude gate; authority smoothing tau_auth; gain g; 2nd-order
      Butterworth output low-pass.  The output stage has no feedback into the filter, so it is evaluated for all
      ticks at once (FFT convolution for the linear time-invariant smoothers, a blocked scan for the amplitude
      reference), which is exact up to floating-point rounding.

Gates: `gate_beta=None` gives the numba ramps (clamp to [0, 1]; used for the agreement check and for deployment),
a finite beta gives a smooth ramp (softplus(beta z) - softplus(beta (z - 1))) / beta that tends to the ramp as
beta -> inf, so that closed gates still receive gradients during training.

Backpropagation through time of this recursion is the discrete adjoint of the filter.  Memory is bounded by
checkpointing the tick loop in chunks (torch.utils.checkpoint): the forward is recomputed chunk by chunk in the
backward pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
import torch.nn.functional as TF
from torch.utils.checkpoint import checkpoint

from . import schedule as SCH

NS = 8
DT = torch.float64
TWO_PI = 2.0 * math.pi

# ------------------------------------------------------------------ fixed basis matrices
_E = lambda i, j: torch.zeros(NS, NS, dtype=DT).index_put_((torch.tensor([i]), torch.tensor([j])), torch.tensor([1.0], dtype=DT))  # noqa: E731


def _basis():
    I = torch.zeros(NS, NS, dtype=DT)
    for i in (0, 1, 2, 7):
        I[i, i] = 1.0
    Fdt = _E(0, 1) + _E(1, 2)
    Fdt2 = _E(0, 2)                          # coefficient dt^2 / 2
    Mc1 = _E(3, 3) + _E(4, 4)
    Ms1 = _E(3, 4) - _E(4, 3)
    Mc2 = _E(5, 5) + _E(6, 6)
    Ms2 = _E(5, 6) - _E(6, 5)
    FB = torch.stack([I, Fdt, Fdt2, Mc1, Ms1, Mc2, Ms2])          # (7, 8, 8): coef [1, dt, dt^2/2, rd c1, rd s1, rd c2, rd s2]
    QJ = torch.stack([_E(0, 0), _E(0, 1) + _E(1, 0), _E(0, 2) + _E(2, 0), _E(1, 1), _E(1, 2) + _E(2, 1), _E(2, 2)])
    # QJ coefficients: [dt^5/20, dt^4/8, dt^3/6, dt^3/3, dt^2/2, dt] (white-jerk intent block, times q_j)
    Mt = _E(3, 3) + _E(4, 4)
    Mh = _E(5, 5) + _E(6, 6)
    Mb = _E(7, 7)
    return FB, QJ, Mt, Mh, Mb


FB, QJB, MT, MH, MB = _basis()


def _fcoef(dt: np.ndarray) -> np.ndarray:
    return np.stack([np.ones_like(dt), dt, 0.5 * dt * dt], -1)


def _qcoef(dt: np.ndarray) -> np.ndarray:
    return np.stack([dt ** 5 / 20.0, dt ** 4 / 8.0, dt ** 3 / 6.0, dt ** 3 / 3.0, dt ** 2 / 2.0, dt], -1)


# ------------------------------------------------------------------ batched event data
@dataclass
class EventBatch:
    B: int
    K: int
    Ts: float
    tick_t: torch.Tensor          # (K,)
    D: int
    R: int
    # per tick, (K, B, ...) layout so that tick k is a contiguous slice
    acc_ev: torch.Tensor          # (K, B) bool
    acc_first: torch.Tensor
    acc_dt: torch.Tensor          # (K, B)
    acc_fc: torch.Tensor          # (K, B, 3)
    acc_qc: torch.Tensor          # (K, B, 6)
    acc_y: torch.Tensor           # (K, B, 2)
    pg_ev: torch.Tensor           # (K, B) bool
    pg_off: torch.Tensor          # (K, B) long: k - snapshot tick
    pg_dt: torch.Tensor
    pg_fc: torch.Tensor
    pg_qc: torch.Tensor
    pg_gap: torch.Tensor          # (K, B) bool
    pg_y: torch.Tensor            # (K, B, 2)
    re_off: torch.Tensor          # (K, R, B) long: k - tick of the re-applied sample (-1: none)
    re_dt: torch.Tensor           # (K, R, B)
    re_fc: torch.Tensor           # (K, R, B, 3)
    re_qc: torch.Tensor           # (K, R, B, 6)
    re_y: torch.Tensor            # (K, R, B, 2)
    fr_adv: torch.Tensor          # (K, B) bool
    fr_have: torch.Tensor
    fr_upd: torch.Tensor
    fr_dtp: torch.Tensor          # (K, B)
    tf: torch.Tensor              # (B, K)
    started: torch.Tensor         # (B, K) float
    # tick-level flags (python) for skipping empty work
    any_acc: np.ndarray
    all_acc: np.ndarray
    any_pg: np.ndarray
    d_tick: np.ndarray            # rollback depth needed at each tick (max over the batch)
    r_tick: np.ndarray            # re-applied samples needed at each tick (max over the batch)

    @staticmethod
    def from_schedules(scheds: Sequence[SCH.Schedule]) -> "EventBatch":
        K = scheds[0].K
        if any(s.K != K for s in scheds):
            raise ValueError("all recordings of a batch need the same number of ticks")
        if any(abs(s.Ts - scheds[0].Ts) > 1e-12 for s in scheds):
            raise ValueError("tick period differs")
        B = len(scheds)
        R = max(s.R for s in scheds)
        D = max(s.D for s in scheds)

        def st(name):
            return np.stack([getattr(s, name) for s in scheds], 1)          # (K, B, ...)

        acc_dt = st("acc_dt"); pg_dt = st("pg_dt")
        pg_off = np.where(st("pg_ev"), np.arange(K)[:, None] - st("pg_snap"), 0)
        re_tick = np.full((K, R, B), -1, np.int64); re_dt = np.zeros((K, R, B))
        for b, s in enumerate(scheds):
            re_tick[:, :s.R, b] = s.re_tick
            re_dt[:, :s.R, b] = s.re_dt
        re_off = np.where(re_tick >= 0, np.arange(K)[:, None, None] - re_tick, -1)
        acc_y = st("acc_y")                                                    # (K, B, 2)
        re_y = np.zeros((K, R, B, 2))
        for b in range(B):
            v = re_tick[:, :, b] >= 0
            re_y[:, :, b][v] = acc_y[re_tick[:, :, b][v], b]
        pg_ev = st("pg_ev"); acc_ev = st("acc_ev")
        nre = st("pg_nre")
        t = lambda a, dt=DT: torch.as_tensor(np.ascontiguousarray(a), dtype=dt)  # noqa: E731
        return EventBatch(
            B=B, K=K, Ts=scheds[0].Ts, tick_t=t(scheds[0].tick_t), D=D, R=R,
            acc_ev=t(acc_ev, torch.bool), acc_first=t(st("acc_first"), torch.bool), acc_dt=t(acc_dt),
            acc_fc=t(_fcoef(acc_dt)), acc_qc=t(_qcoef(acc_dt)), acc_y=t(acc_y),
            pg_ev=t(pg_ev, torch.bool), pg_off=t(pg_off, torch.long), pg_dt=t(pg_dt), pg_fc=t(_fcoef(pg_dt)),
            pg_qc=t(_qcoef(pg_dt)), pg_gap=t(st("pg_gap"), torch.bool), pg_y=t(st("pg_y")),
            re_off=t(re_off, torch.long), re_dt=t(re_dt), re_fc=t(_fcoef(re_dt)), re_qc=t(_qcoef(re_dt)), re_y=t(re_y),
            fr_adv=t(st("fr_adv"), torch.bool), fr_have=t(st("fr_have"), torch.bool), fr_upd=t(st("fr_upd"), torch.bool),
            fr_dtp=t(st("fr_dtp")), tf=t(st("tf").T), started=t(st("started").T.astype(float)),
            any_acc=acc_ev.any(1), all_acc=acc_ev.all(1), any_pg=pg_ev.any(1),
            d_tick=np.where(pg_ev, pg_off, 0).max(1), r_tick=np.where(pg_ev, nre, 0).max(1))

    def subset(self, idx) -> "EventBatch":
        """Recordings idx (a list of batch indices), same ticks."""
        idx_t = torch.as_tensor(idx, dtype=torch.long)
        kw = {}
        for f in self.__dataclass_fields__:
            v = getattr(self, f)
            if f in ("tf", "started"):
                kw[f] = v[idx_t]
            elif f in ("re_off", "re_dt", "re_fc", "re_qc", "re_y"):
                kw[f] = v[:, :, idx_t]
            elif isinstance(v, torch.Tensor) and v.dim() >= 2 and f != "tick_t":
                kw[f] = v[:, idx_t]
            else:
                kw[f] = v
        kw["B"] = len(idx)
        acc_ev = kw["acc_ev"].numpy(); pg_ev = kw["pg_ev"].numpy()
        kw["any_acc"] = acc_ev.any(1); kw["all_acc"] = acc_ev.all(1); kw["any_pg"] = pg_ev.any(1)
        kw["d_tick"] = np.where(pg_ev, kw["pg_off"].numpy(), 0).max(1)
        nre = (kw["re_off"].numpy() >= 0).sum(1)
        kw["r_tick"] = np.where(pg_ev, nre, 0).max(1)
        kw["D"] = int(kw["d_tick"].max()) if len(kw["d_tick"]) else 0
        return EventBatch(**kw)


# ------------------------------------------------------------------ parameters
# name: (kind, scale).  kind "log": value = exp(theta) * scale; "lin": value = theta * scale.
PARAM_DEFS: Dict[str, tuple] = {
    "qj": ("log", 1.0), "qt": ("log", 1.0), "qh": ("log", 1.0), "qb": ("log", 1.0), "ra": ("log", 1.0),
    "rp": ("log", 1.0), "tau_decay": ("log", 1.0), "w0_hz": ("lin", 1.0), "tau_w": ("log", 1.0),
    "wmin_hz": ("lin", 1.0), "wmax_hz": ("lin", 1.0), "f_gate": ("lin", 1.0), "f_gate_w": ("log", 1.0),
    "a_c": ("lin", 1e-5), "a_w": ("log", 1.0), "tau_amp": ("log", 1.0), "horizon": ("lin", 1e-3),
    "tau_auth": ("log", 1.0), "g": ("log", 1.0), "lp_hz": ("log", 1.0), "cap_k": ("log", 1.0), "v_slow": ("log", 1.0),
    "tau_ref": ("log", 1.0), "v_xt": ("log", 1.0),
}
TRAIN_KEYS = ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz", "f_gate",
              "f_gate_w", "a_c", "a_w", "tau_amp", "horizon", "tau_auth", "g", "lp_hz", "cap_k", "v_slow", "tau_ref")
DEFAULTS = dict(__import__("fusion.estimators", fromlist=["AKF_DEFAULTS"]).AKF_DEFAULTS)


def complete(p: Dict) -> Dict:
    """A numba parameter dict with every AKF key (fusion defaults for the missing ones)."""
    q = dict(DEFAULTS)
    q.update(p or {})
    return q


def trainable_start(p: Dict) -> Dict:
    """Values of TRAIN_KEYS from a numba parameter dict.  Features the dict switches off are switched on in a
    neutral position so that gradients can find them: frequency gate open below 2.5 Hz, amplitude gate open from
    1 um, cap at 30x the slow-motion amplitude, second-harmonic noise 1e-3 q_t when harm = 0 (unused then)."""
    q = complete(p)
    out = {k: float(q[k]) for k in ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz",
                                     "wmax_hz", "tau_amp", "horizon", "tau_auth", "g", "lp_hz", "v_slow", "tau_ref")}
    if out["qh"] <= 0:
        out["qh"] = 1e-3 * out["qt"]
    if q["f_gate"] > 0:
        out["f_gate"], out["f_gate_w"] = float(q["f_gate"]), float(q["f_gate_w"])
    else:
        out["f_gate"], out["f_gate_w"] = 2.0, 1.0
    if q["a_hi"] > q["a_lo"]:
        out["a_c"], out["a_w"] = 0.5 * (q["a_lo"] + q["a_hi"]), float(q["a_hi"] - q["a_lo"])
    else:
        out["a_c"], out["a_w"] = 0.0, 2e-6
    out["cap_k"] = float(q["cap_k"]) if q["cap_k"] > 0 else 30.0
    if out["lp_hz"] <= 0:
        out["lp_hz"] = 400.0
    return out


def to_theta(vals: Dict, keys: Sequence[str] = TRAIN_KEYS) -> torch.Tensor:
    th = []
    for k in keys:
        kind, sc = PARAM_DEFS[k]
        v = float(vals[k])
        th.append(math.log(v / sc) if kind == "log" else v / sc)
    return torch.tensor(th, dtype=DT)


def from_theta(theta: torch.Tensor, keys: Sequence[str] = TRAIN_KEYS) -> Dict[str, torch.Tensor]:
    """theta (..., n) -> {name: tensor (...)}; positive quantities through exp."""
    out = {}
    for i, k in enumerate(keys):
        kind, sc = PARAM_DEFS[k]
        out[k] = torch.exp(theta[..., i]) * sc if kind == "log" else theta[..., i] * sc
    return out


def to_numba(vals: Dict, static: Dict) -> Dict:
    """A parameter dict for fusion.estimators.akf from trained values (floats or tensors)."""
    f = {k: float(v.detach()) if isinstance(v, torch.Tensor) else float(v) for k, v in vals.items()}
    p = {k: f[k] for k in ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz",
                           "f_gate", "f_gate_w", "tau_amp", "horizon", "tau_auth", "g", "lp_hz", "cap_k", "v_slow",
                           "tau_ref") if k in f}
    if "a_c" in f:
        p["a_lo"] = f["a_c"] - 0.5 * f["a_w"]
        p["a_hi"] = f["a_c"] + 0.5 * f["a_w"]
    for k in ("a_lo", "a_hi"):
        if k in f:
            p[k] = f[k]
    p["harm"] = float(static.get("harm", 1.0))
    p["xtrack"] = float(static.get("xtrack", 0.0))
    p["v_xt"] = float(f.get("v_xt", static.get("v_xt", DEFAULTS["v_xt"])))
    return p


def numba_to_values(p: Dict) -> Dict:
    """Every quantity the torch filter reads, as floats, from a numba parameter dict (exact numba semantics)."""
    q = complete(p)
    v = {k: float(q[k]) for k in ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz",
                                  "wmax_hz", "f_gate", "f_gate_w", "a_lo", "a_hi", "tau_amp", "horizon", "tau_auth",
                                  "g", "lp_hz", "cap_k", "v_slow", "tau_ref", "v_xt", "acc_gd", "gap_reset")}
    return v


def static_of(p: Dict) -> Dict:
    q = complete(p)
    return {"harm": float(q["harm"]), "xtrack": float(q["xtrack"]), "v_xt": float(q["v_xt"]),
            "acc_gd": float(q["acc_gd"]), "gap_reset": float(q["gap_reset"]), "use_pos": float(q["use_pos"]),
            "use_acc": float(q["use_acc"])}


def expand(vals: Dict, B: int) -> Dict[str, torch.Tensor]:
    """{name: float | tensor ()/(B,)} -> {name: tensor (B,)} float64; a_c/a_w become a_lo/a_hi."""
    out = {}
    for k, v in vals.items():
        t = v if isinstance(v, torch.Tensor) else torch.tensor(float(v), dtype=DT)
        t = t.to(DT)
        out[k] = t.expand(B) if t.dim() == 0 else t
    if "a_c" in out:
        out["a_lo"] = out["a_c"] - 0.5 * out["a_w"]
        out["a_hi"] = out["a_c"] + 0.5 * out["a_w"]
    return out


# ------------------------------------------------------------------ filter arithmetic
def _F(fc, dt, w, tau_d):
    """Transition matrices (B, 8, 8): fc (B, 3) = [1, dt, dt^2/2]."""
    wdt = w * dt
    rd = torch.exp(-dt / tau_d)
    osc = rd[:, None] * torch.stack([torch.cos(wdt), torch.sin(wdt), torch.cos(2.0 * wdt), torch.sin(2.0 * wdt)], 1)
    return torch.einsum("bi,ijk->bjk", torch.cat([fc, osc], 1), FB)


def _Q(qc, dt, qj, Qd):
    return qj[:, None, None] * torch.einsum("bi,ijk->bjk", qc, QJB) + dt[:, None, None] * Qd


def _predict(x, P, F, Q):
    Ft = F.transpose(1, 2)
    return torch.matmul(x, Ft), torch.bmm(torch.bmm(F, P), Ft) + Q


def _update(x, P, H, y, R):
    """Scalar update per axis with the shared covariance.  H (B, 8), y (B, 2), R (B,)."""
    PH = torch.bmm(P, H[:, :, None])[:, :, 0]
    S = (H * PH).sum(1) + R
    e = y - (x * H[:, None, :]).sum(2)
    x = x + PH[:, None, :] * (e / S[:, None])[:, :, None]
    P = P - PH[:, :, None] * PH[:, None, :] / S[:, None, None]
    return x, P


def _ha(w, harm):
    B = w.shape[0]
    H = torch.zeros(B, NS, dtype=DT)
    w2 = w * w
    return H.index_copy(1, torch.tensor([2, 3, 5, 7]), torch.stack([torch.ones_like(w), -w2, -4.0 * harm * w2,
                                                                    torch.ones_like(w)], 1))


def _where(m, a, b):
    mm = m.reshape(m.shape + (1,) * (a.dim() - m.dim()))
    return torch.where(mm, a, b)


def _p_init(B):
    d = torch.tensor([1e-6, 1e-4, 1.0, 1e-7, 1e-7, 1e-8, 1e-8, 0.05], dtype=DT)
    return torch.diag_embed(d.expand(B, NS)).clone()


@dataclass
class CoreParams:
    qj: torch.Tensor
    ra: torch.Tensor
    rp: torch.Tensor
    tau_d: torch.Tensor
    tau_w: torch.Tensor
    wmin: torch.Tensor
    wmax: torch.Tensor
    Qd: torch.Tensor          # (B, 8, 8) q_t, q_h harm, q_b diagonal
    Hp: torch.Tensor          # (B, 8)
    harm: float


def _core_chunk(k0: int, k1: int, ev: EventBatch, cp: CoreParams, x, P, w, phase_prev, ax_prev, ring_x, ring_P, ring_w):
    """Ticks k0..k1-1.  ring_* hold the snapshots of ticks k0-L .. k0-1 (L = len(ring)) as lists of tensors."""
    B = ev.B
    L = len(ring_x)
    rx = list(ring_x); rP = list(ring_P); rw = list(ring_w)
    base = k0 - L                                     # tick index of rx[0]
    xs, ws = [], []
    ar = torch.arange(B)
    harm = cp.harm
    TINY = 1e-60
    for k in range(k0, k1):
        # ---------------- accelerometer event
        w_used = w
        if ev.any_acc[k]:
            m = ev.acc_ev[k]
            first = ev.acc_first[k]
            if bool(first.any()):
                P = _where(first, _p_init(B), P)
            dt = ev.acc_dt[k]
            F = _F(ev.acc_fc[k], dt, w, cp.tau_d)
            Q = _Q(ev.acc_qc[k], dt, cp.qj, cp.Qd)
            xn, Pn = _predict(x, P, F, Q)
            xn, Pn = _update(xn, Pn, _ha(w, harm), ev.acc_y[k], cp.ra)
            if ev.all_acc[k]:
                x, P = xn, Pn
            else:
                x, P = _where(m, xn, x), _where(m, Pn, P)
        rx.append(x); rP.append(P); rw.append(w_used)
        # ---------------- page event: roll back, update, re-apply
        if ev.any_pg[k]:
            m = ev.pg_ev[k]
            d = int(ev.d_tick[k])
            # snapshot at tick k - off (in the ring: index k - off - base)
            off = ev.pg_off[k]
            j0 = len(rx) - 1 - d
            sx = torch.stack(rx[j0:], 0)              # (d+1, B, 2, 8), last = tick k
            sP = torch.stack(rP[j0:], 0)
            sw = torch.stack(rw[j0:], 0)
            idx = (d - off).clamp(0, d)
            x1 = sx[idx, ar]; P1 = sP[idx, ar]; w1 = sw[idx, ar]
            dt = ev.pg_dt[k]
            F = _F(ev.pg_fc[k], dt, w1, cp.tau_d)
            Q = _Q(ev.pg_qc[k], dt, cp.qj, cp.Qd)
            x1, P1 = _predict(x1, P1, F, Q)
            gap = ev.pg_gap[k]
            y = ev.pg_y[k]
            xu, Pu = _update(x1, P1, cp.Hp, y, cp.rp)
            if bool((gap & m).any()):
                # position re-anchoring: p += y - (p + c1 + harm c2); P row/col 0 cleared, P00 = r_p
                pnew = y - x1[:, :, 3] - harm * x1[:, :, 5]
                xg = torch.cat([pnew[:, :, None], x1[:, :, 1:]], 2)
                keep = torch.ones(NS, NS, dtype=DT); keep[0, :] = 0.0; keep[:, 0] = 0.0
                e00 = torch.zeros(NS, NS, dtype=DT); e00[0, 0] = 1.0
                Pg = P1 * keep + cp.rp[:, None, None] * e00
                xu, Pu = _where(gap, xg, xu), _where(gap, Pg, Pu)
            nre = int(ev.r_tick[k])
            for j in range(nre):
                offj = ev.re_off[k, j]                # (B,) k - tick of the sample, -1 none
                act = (offj >= 0) & m
                if not bool(act.any()):
                    continue
                ij = (d - offj).clamp(0, d)
                wq = sw[ij, ar]
                dt = ev.re_dt[k, j]
                F = _F(ev.re_fc[k, j], dt, wq, cp.tau_d)
                Q = _Q(ev.re_qc[k, j], dt, cp.qj, cp.Qd)
                xn, Pn = _predict(xu, Pu, F, Q)
                xn, Pn = _update(xn, Pn, _ha(wq, harm), ev.re_y[k, j], cp.ra)
                xu, Pu = _where(act, xn, xu), _where(act, Pn, Pu)
                # overwrite the re-applied sample's snapshot (only where active)
                for r in range(d + 1):
                    sel = act & (ij == r)
                    if bool(sel.any()):
                        rr = j0 + r
                        rx[rr] = _where(sel, xu, rx[rr]); rP[rr] = _where(sel, Pu, rP[rr])
            x, P = _where(m, xu, x), _where(m, Pu, P)
        # ---------------- frequency tracking
        a0 = torch.sqrt(x[:, 0, 3] ** 2 + x[:, 0, 4] ** 2 + TINY)
        a1 = torch.sqrt(x[:, 1, 3] ** 2 + x[:, 1, 4] ** 2 + TINY)
        axm = a1 > a0
        ampm = torch.maximum(a0, a1)
        xc = torch.where(axm, x[:, 1, 3], x[:, 0, 3])
        xsn = torch.where(axm, x[:, 1, 4], x[:, 0, 4])
        zero = (xc == 0) & (xsn == 0)
        phs = torch.atan2(torch.where(zero, torch.zeros_like(xsn), xsn), torch.where(zero, torch.ones_like(xc), xc))
        cond = ev.fr_have[k] & ev.fr_adv[k] & (ampm > 2e-6) & (axm == ax_prev)
        if bool(cond.any()):
            dtp = torch.where(cond, ev.fr_dtp[k], torch.ones_like(w))
            dph = torch.remainder(phs - phase_prev + math.pi, TWO_PI) - math.pi
            wm = -dph / dtp
            a_w = torch.clamp(dtp / cp.tau_w, max=1.0)
            wn = w + a_w * (wm - w)
            wn = torch.minimum(torch.maximum(wn, cp.wmin), cp.wmax)
            w = torch.where(cond, wn, w)
        upd = ev.fr_upd[k]
        phase_prev = torch.where(upd, phs, phase_prev)
        ax_prev = torch.where(upd, axm, ax_prev)
        xs.append(x[:, :, [1, 3, 4, 5, 6]])
        ws.append(w)
        # keep only the snapshots a later rollback can reach
        keep_n = ev.D + 1
        if len(rx) > keep_n:
            rx = rx[-keep_n:]; rP = rP[-keep_n:]; rw = rw[-keep_n:]
    return x, P, w, phase_prev, ax_prev, rx, rP, rw, torch.stack(xs, 1), torch.stack(ws, 1)


def core(ev: EventBatch, prm: Dict[str, torch.Tensor], harm: float, chunk: Optional[int] = 400):
    """The sequential part: returns XO (B, K, 2, 5) = [v, c1, s1, c2, s2] per axis after each tick, W (B, K)."""
    B = ev.B
    qhh = prm["qh"] * harm
    Qd = prm["qt"][:, None, None] * MT + qhh[:, None, None] * MH + prm["qb"][:, None, None] * MB
    Hp = torch.zeros(B, NS, dtype=DT)
    Hp[:, 0] = 1.0; Hp[:, 3] = 1.0; Hp[:, 5] = harm
    cp = CoreParams(qj=prm["qj"], ra=prm["ra"], rp=prm["rp"], tau_d=prm["tau_decay"], tau_w=prm["tau_w"],
                    wmin=TWO_PI * prm["wmin_hz"], wmax=TWO_PI * prm["wmax_hz"], Qd=Qd, Hp=Hp, harm=harm)
    x = torch.zeros(B, 2, NS, dtype=DT)
    P = torch.zeros(B, NS, NS, dtype=DT)
    w = TWO_PI * prm["w0_hz"]
    phase_prev = torch.zeros(B, dtype=DT)
    ax_prev = torch.zeros(B, dtype=torch.bool)
    L = ev.D + 1
    ring_x = [x] * L; ring_P = [P] * L; ring_w = [w] * L
    XO, WO = [], []
    K = ev.K
    step = chunk or K
    need_grad = torch.is_grad_enabled() and any(t.requires_grad for t in prm.values())
    for k0 in range(0, K, step):
        k1 = min(K, k0 + step)
        if chunk and need_grad:
            n = len(ring_x)

            def fn(x_, P_, w_, pp_, axp_, rxs, rPs, rws, k0=k0, k1=k1, n=n):
                o = _core_chunk(k0, k1, ev, cp, x_, P_, w_, pp_, axp_, list(rxs.unbind(0)), list(rPs.unbind(0)),
                                list(rws.unbind(0)))
                x2, P2, w2, pp2, axp2, rx2, rP2, rw2, xo, wo = o
                return x2, P2, w2, pp2, axp2, torch.stack(rx2, 0), torch.stack(rP2, 0), torch.stack(rw2, 0), xo, wo
            out = checkpoint(fn, x, P, w, phase_prev, ax_prev, torch.stack(ring_x, 0), torch.stack(ring_P, 0),
                             torch.stack(ring_w, 0), use_reentrant=False)
            x, P, w, phase_prev, ax_prev, rxs, rPs, rws, xo, wo = out
            ring_x, ring_P, ring_w = list(rxs.unbind(0)), list(rPs.unbind(0)), list(rws.unbind(0))
        else:
            x, P, w, phase_prev, ax_prev, ring_x, ring_P, ring_w, xo, wo = _core_chunk(
                k0, k1, ev, cp, x, P, w, phase_prev, ax_prev, ring_x, ring_P, ring_w)
        XO.append(xo); WO.append(wo)
    return torch.cat(XO, 1), torch.cat(WO, 1)


# ------------------------------------------------------------------ output stage (all ticks at once)
def ramp(z, beta):
    """clamp(z, 0, 1).  beta None: exact (numba) ramp; ("leaky", eps): the exact ramp's value with gradient eps
    outside [0, 1] (straight-through), so closed or saturated gates still receive a first-order signal; a float:
    the softplus-smoothed ramp (softplus(beta z) - softplus(beta (z - 1))) / beta."""
    if beta is None:
        return torch.clamp(z, 0.0, 1.0)
    if isinstance(beta, tuple):
        h = torch.clamp(z, 0.0, 1.0)
        out = ((z < 0.0) | (z > 1.0)).to(z.dtype)
        return h + beta[1] * (z - z.detach()) * out
    return (TF.softplus(beta * z) - TF.softplus(beta * (z - 1.0))) / beta


def relu_s(z, beta):
    if beta is None:
        return torch.clamp(z, min=0.0)
    if isinstance(beta, tuple):
        return torch.clamp(z, min=0.0) + beta[1] * (z - z.detach()) * (z < 0.0).to(z.dtype)
    return TF.softplus(beta * z) / beta


def _fft_causal_conv(x, h):
    """y[..., k] = sum_{j <= k} h[..., k - j] x[..., j]  (x, h (..., K)); exact linear convolution by FFT."""
    K = x.shape[-1]
    n = fast_len(2 * K)
    return torch.fft.irfft(torch.fft.rfft(x, n=n) * torch.fft.rfft(h, n=n), n=n)[..., :K]


def fast_len(n: int) -> int:
    from scipy.fft import next_fast_len
    return int(next_fast_len(int(n), real=True))


def iir1(x, alpha):
    """y[k] = y[k-1] + alpha (x[k] - y[k-1]), y[-1] = 0; x (B, K) with alpha (B,) (blocked exact scan)."""
    return aref_scan(x, alpha[:, None].expand_as(x))


def lp2_ir(fc, Ts, K):
    """Impulse response (B, K) of fusion.estimators._lp2_coef(fc, Ts) (2nd-order Butterworth, bilinear)."""
    Kt = torch.tan(math.pi * fc * Ts)
    norm = 1.0 / (1.0 + math.sqrt(2.0) * Kt + Kt * Kt)
    b0 = Kt * Kt * norm
    a1 = 2.0 * (Kt * Kt - 1.0) * norm
    a2 = (1.0 - math.sqrt(2.0) * Kt + Kt * Kt) * norm
    r = torch.sqrt(a2)
    cth = torch.clamp(-a1 / (2.0 * r), -1.0 + 1e-15, 1.0 - 1e-15)
    th = torch.acos(cth)
    n = torch.arange(K + 2, dtype=DT)
    g = torch.exp(n[None, :] * torch.log(r)[:, None]) * torch.sin((n[None, :] + 1.0) * th[:, None]) / torch.sin(th)[:, None]
    gp = TF.pad(g, (2, 0))                                                               # g[n-1], g[n-2]
    h = b0[:, None] * (g[:, :K] + 2.0 * gp[:, 1:K + 1] + gp[:, :K])
    return h


def aref_scan(amp, beta, block: int = 512):
    """a[k] = a[k-1] + beta_k (amp_k - a[k-1]), a[-1] = 0; amp, beta (B, K); exact scan in blocks (within a block
    a[k] = prod(1 - beta) (carry + cumsum(beta amp / prod(1 - beta))), computed in log space)."""
    B, K = amp.shape
    out = []
    carry = torch.zeros(B, dtype=DT)
    lb = torch.log1p(-torch.clamp(beta, max=0.9))
    for s in range(0, K, block):
        e = min(K, s + block)
        L = torch.cumsum(lb[:, s:e], 1)                                  # log prod_{i<=k} (1 - beta_i) within block
        inner = torch.cumsum(beta[:, s:e] * amp[:, s:e] * torch.exp(-L), 1)
        a = torch.exp(L) * (carry[:, None] + inner)
        out.append(a)
        carry = a[:, -1]
    return torch.cat(out, 1)


def output_stage(XO, W, ev: EventBatch, prm: Dict[str, torch.Tensor], static: Dict, gate_beta: Optional[float] = None,
                 return_parts: bool = False):
    """Estimate (B, K, 2) from the per-tick filter states (exact numba output semantics)."""
    B, K = W.shape
    Ts = ev.Ts
    t = ev.tick_t[None, :]
    harm = float(static.get("harm", 1.0))
    started = ev.started
    lp = prm["lp_hz"]
    hor = prm["horizon"] + torch.where(lp > 0, math.sqrt(2.0) / (TWO_PI * lp), torch.zeros_like(lp))
    dtp = t + hor[:, None] - ev.tf
    rd = torch.exp(-torch.clamp(dtp, min=0.0) / prm["tau_decay"][:, None])
    ph = W * dtp
    v, c1, s1, c2, s2 = XO.unbind(3)                                   # each (B, K, 2)
    d = (torch.cos(ph)[..., None] * c1 + torch.sin(ph)[..., None] * s1)
    if harm != 0.0:
        d = d + harm * (torch.cos(2.0 * ph)[..., None] * c2 + torch.sin(2.0 * ph)[..., None] * s2)
    d = rd[..., None] * d * started[..., None]
    if float(static.get("xtrack", 0.0)) > 0.5:
        vx, vy = v[..., 0], v[..., 1]
        sp = torch.sqrt(vx * vx + vy * vy + 1e-60)
        mv = sp > 1e-9
        sps = torch.where(mv, sp, torch.ones_like(sp))
        tx, ty = vx / sps, vy / sps
        v_xt = prm["v_xt"][:, None] if "v_xt" in prm else float(static.get("v_xt", 5e-3))
        wgt = torch.clamp(sp / v_xt, max=1.0)
        dl = tx * d[..., 0] + ty * d[..., 1]
        d = torch.where(mv[..., None], torch.stack([d[..., 0] - wgt * dl * tx, d[..., 1] - wgt * dl * ty], -1), d)
    amp = torch.sqrt((c1[..., 0] ** 2 + s1[..., 0] ** 2) + (c1[..., 1] ** 2 + s1[..., 1] ** 2) + 1e-60)
    amp_f = iir1(amp, Ts / prm["tau_amp"])
    cap_on = prm["cap_k"] > 0
    if bool(cap_on.any()):
        sp_i = torch.sqrt(v[..., 0] ** 2 + v[..., 1] ** 2 + 1e-60)
        wv = relu_s(1.0 - sp_i / prm["v_slow"][:, None], gate_beta)
        beta = wv * (Ts / prm["tau_ref"])[:, None] * started
        a_ref = aref_scan(amp, beta)
        mag = torch.sqrt(d[..., 0] ** 2 + d[..., 1] ** 2 + 1e-60)
        lim = prm["cap_k"][:, None] * a_ref
        over = (mag > lim) & (started > 0.5) & cap_on[:, None]
        sc = torch.where(mag > 1e-15, lim / mag, torch.zeros_like(mag))
        d = torch.where(over[..., None], d * sc[..., None], d)
    target = prm["g"][:, None].expand(B, K)
    fg_on = prm["f_gate"] > 0
    zf = (W / TWO_PI - (prm["f_gate"] - 0.5 * prm["f_gate_w"])[:, None]) / torch.clamp(prm["f_gate_w"], min=1e-9)[:, None]
    target = target * torch.where(fg_on[:, None], ramp(zf, gate_beta), torch.ones_like(zf))
    ag_on = prm["a_hi"] > prm["a_lo"]
    dw = torch.where(ag_on, prm["a_hi"] - prm["a_lo"], torch.ones_like(prm["a_hi"]))
    za = (amp_f - prm["a_lo"][:, None]) / dw[:, None]
    target = target * torch.where(ag_on[:, None], ramp(za, gate_beta), torch.ones_like(za))
    target = target * started
    g_eff = iir1(target, 1.0 - torch.exp(-Ts / prm["tau_auth"]))
    u = g_eff[..., None] * d                                            # (B, K, 2)
    if bool((lp > 0).all()):
        h = lp2_ir(lp, Ts, K)                                            # (B, K)
        out = _fft_causal_conv(u.movedim(1, -1), h[:, None, :]).movedim(-1, 1)
    elif bool((lp <= 0).all()):
        out = u
    else:
        raise ValueError("mixed output low-pass on/off in one batch")
    if return_parts:
        return out, {"authority": g_eff, "amp_f": amp_f, "f_est": W / TWO_PI, "d_pred": d}
    return out


def forward(ev: EventBatch, vals: Dict, static: Dict, gate_beta: Optional[float] = None, chunk: Optional[int] = 400,
            return_parts: bool = False):
    """Estimate (B, K, 2) for parameter values `vals` ({name: float or tensor () / (B,)})."""
    prm = expand(vals, ev.B)
    harm = float(static.get("harm", 1.0))
    XO, W = core(ev, prm, harm, chunk=chunk)
    return output_stage(XO, W, ev, prm, static, gate_beta, return_parts)


def run_numba_equivalent(streams_list, p: Dict, gate_beta=None, chunk=None):
    """Convenience: torch AKF on fusion Streams with a numba parameter dict (no gradients)."""
    st0 = static_of(p)
    scheds = [SCH.build(s, acc_gd=st0["acc_gd"], gap_reset=st0["gap_reset"], use_pos=st0["use_pos"] > 0.5)
              for s in streams_list]
    ev = EventBatch.from_schedules(scheds)
    with torch.no_grad():
        return forward(ev, numba_to_values(p), st0, gate_beta=gate_beta, chunk=chunk, return_parts=True)
