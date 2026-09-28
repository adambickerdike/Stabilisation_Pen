"""Path guidance for the board, and a closed-loop simulation with the hand model (SIM).

Guidance law (HAP-16: time-free contouring; HAP-13/14: partial and full
guidance; HAP-03: assist-as-needed deadband; HAP-21/22/23: continuous
authority that yields to the writer):

* progress: s is the arc length of the template point closest to the ink,
  searched only a little behind and ahead of the previous s, so the writer
  sets the speed and the target never runs away in time;
* partial guidance: no force inside a deadband around the path, a spring
  toward the path outside it;
* full guidance: a stiffer spring with no deadband, plus a small pull along
  the path while the writer moves forward ("lead");
* authority g in [0, 1] scales the force (the app's guidance level);
* safety supervisor: force cap, force slew limit, yield when the writer keeps
  overriding, zero force when the pen is lifted.

Plant used by the simulation (all per axis in the paper plane):
pen handle (heel magnet) -(grip k1, b1)- hand mass M -(arm k2, b2)- the
writer's intended path (HAP-26 two-stage, board.hand).  The board's force acts
on the handle through a stage delay and lag (board.stage).  The Rev H nose can
move the ink up to 3 mm relative to the handle ("assist" mode) or be held
central ("learn" mode, so the writer's own error stays visible, HAP-01/05/06).
The extra skid friction caused by the magnet's normal pull is included as an
uncompensated drag; the writer is assumed to compensate the ordinary writing
friction.

Evidence status: SIM on synthetic paths and the literature hand model.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from . import params as P
from . import hand as H


# ----------------------------------------------------------------------------- templates
class Path:
    """A single pen-down stroke as a polyline (mm), parametrised by arc length."""

    def __init__(self, pts):
        self.p = np.asarray(pts, float)
        d = np.hypot(*np.diff(self.p, axis=0).T)
        keep = np.r_[True, d > 1e-9]
        self.p = self.p[keep]
        d = np.hypot(*np.diff(self.p, axis=0).T)
        self.s = np.r_[0.0, np.cumsum(d)]
        self.L = float(self.s[-1])

    def point(self, s):
        s = np.clip(s, 0.0, self.L)
        return np.array([np.interp(s, self.s, self.p[:, 0]), np.interp(s, self.s, self.p[:, 1])])

    def tangent(self, s, h=0.2):
        a, b = self.point(max(s - h, 0.0)), self.point(min(s + h, self.L))
        t = b - a
        n = np.linalg.norm(t)
        return t / n if n > 0 else np.array([1.0, 0.0])

    def project(self, q, s_prev, back=2.0, ahead=6.0, n=41):
        lo, hi = max(0.0, s_prev - back), min(self.L, s_prev + ahead)
        ss = np.linspace(lo, hi, n)
        pts = np.stack([np.interp(ss, self.s, self.p[:, 0]), np.interp(ss, self.s, self.p[:, 1])], 1)
        d = np.hypot(pts[:, 0] - q[0], pts[:, 1] - q[1])
        k = int(np.argmin(d))
        # refine on the local segment
        k0, k1 = max(k - 1, 0), min(k + 1, n - 1)
        ss2 = np.linspace(ss[k0], ss[k1], 21)
        pts2 = np.stack([np.interp(ss2, self.s, self.p[:, 0]), np.interp(ss2, self.s, self.p[:, 1])], 1)
        d2 = np.hypot(pts2[:, 0] - q[0], pts2[:, 1] - q[1])
        j = int(np.argmin(d2))
        return float(ss2[j]), pts2[j]

    def resample(self, n):
        u = np.linspace(0, self.L, n)
        return np.stack([np.interp(u, self.s, self.p[:, 0]), np.interp(u, self.s, self.p[:, 1])], 1)


def loops(n_loops=5, height=10.0, advance=6.0, n=900, x0=0.0, y0=0.0, scale_fn=None):
    """Cursive 'e/l'-like loops (prolate cycloid), the PD writing-practice pattern (PDT-16/20)."""
    t = np.linspace(0.0, n_loops, n)
    R = height / 2.0
    w = 2 * math.pi
    sc = np.ones_like(t) if scale_fn is None else scale_fn(t / n_loops)
    x = x0 + advance * t - R * np.sin(w * t) * sc
    y = y0 + R * (1 - np.cos(w * t)) * sc
    return np.stack([x, y], 1)


def letter_b_or_d(which="d", xh=8.0, x0=0.0, y0=0.0, n=300):
    """Two strokes: the stem (top to baseline) then the bowl (one full turn)."""
    asc = 1.6 * xh
    stem = np.stack([np.full(40, x0), np.linspace(y0 + asc, y0, 40)], 1)
    r = xh / 2
    side = 1.0 if which == "b" else -1.0
    th = np.linspace(0, 2 * math.pi, n)
    # bowl starts at the stem (x0, y0 + r) side, goes round and back to the stem
    cx = x0 + side * r
    bowl = np.stack([cx - side * r * np.cos(th), y0 + r + side * r * np.sin(th) * (1 if which == "b" else -1)], 1)
    return [stem, bowl]


def tracing_word(xh=8.0, x0=0.0, y0=0.0):
    """Tracing practice shapes: an 'o', a 'c' and a 'u' built from arcs (strokes, mm)."""
    r = xh / 2
    th = np.linspace(math.radians(60), math.radians(60) + 2 * math.pi, 220)
    o = np.stack([x0 + r + r * np.cos(th), y0 + r + r * np.sin(th)], 1)
    thc = np.linspace(math.radians(45), math.radians(315), 180)
    c = np.stack([x0 + 3 * r + 0.6 * r + r * np.cos(thc), y0 + r + r * np.sin(thc)], 1)
    thu = np.linspace(math.pi, 2 * math.pi, 120)
    u0 = x0 + 6.5 * r
    u = np.vstack([np.stack([np.full(30, u0), np.linspace(y0 + xh, y0 + r, 30)], 1),
                   np.stack([u0 + r + r * np.cos(thu), y0 + r + r * np.sin(thu)], 1),
                   np.stack([np.full(30, u0 + 2 * r), np.linspace(y0 + r, y0 + xh, 30)], 1),
                   np.stack([np.full(20, u0 + 2 * r), np.linspace(y0 + xh, y0, 20)], 1)])
    return [o, c, u]


def smooth_deviation(path: Path, rms_mm: float, rng, wavelengths=(4.0, 7.0, 13.0)):
    """A smooth normal deviation along a path (the writer's own tracing error)."""
    s = path.s
    d = np.zeros_like(s)
    for lam in wavelengths:
        d += rng.normal() * np.sin(2 * math.pi * s / lam + rng.uniform(0, 2 * math.pi))
    d *= rms_mm / max(np.sqrt(np.mean(d ** 2)), 1e-9)
    t = np.array([path.tangent(si) for si in s])
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    return path.p + d[:, None] * nrm


# ----------------------------------------------------------------------------- guidance law
@dataclass
class Guidance:
    mode: str = "partial"          # "off" | "partial" | "full" | "lead_through"
    authority: float = 1.0
    deadband_mm: float = P.CONTROL["partial_deadband_mm"].value
    k_partial: float = P.CONTROL["partial_gain_N_per_mm"].value
    k_full: float = P.CONTROL["full_gain_N_per_mm"].value
    b_n: float = P.CONTROL["damping_N_s_per_m"].value
    lead_N: float = P.CONTROL["lead_force_N"].value
    cap_N: float = P.CONTROL["force_cap_N"].value
    slew_N_s: float = P.CONTROL["slew_N_per_s"].value
    override_mm: float = P.CONTROL["override_error_mm"].value
    override_s: float = P.CONTROL["override_time_s"].value

    def force(self, e_vec, e_n, n_hat, t_hat, v_pen, e_n_dot):
        """Commanded lateral force (N, 2-vector) before the supervisor."""
        if self.mode == "off":
            return np.zeros(2)
        if self.mode == "partial":
            mag = max(abs(e_n) - self.deadband_mm, 0.0)
            f_n = -math.copysign(self.k_partial * mag, e_n) - (self.b_n * e_n_dot * 1e-3 if mag > 0 else 0.0)
            return self.authority * f_n * n_hat
        k = self.k_full
        f = -k * e_vec - self.b_n * e_n_dot * 1e-3 * n_hat
        if self.mode == "lead_through" or (self.mode == "full" and float(np.dot(v_pen, t_hat)) > 3.0):
            f = f + self.lead_N * t_hat
        return self.authority * f


@dataclass
class Supervisor:
    """Force cap, slew limit, override yield, lift cut-off."""
    cap_N: float
    slew_N_s: float
    override_mm: float
    override_s: float
    fade_s: float = 0.3
    t_over: float = 0.0
    g: float = 1.0
    f_prev: np.ndarray = field(default_factory=lambda: np.zeros(2))
    events: list = field(default_factory=list)

    def step(self, f_cmd, e_n, pen_down, dt, t):
        if not pen_down:
            self.f_prev = np.zeros(2)
            return self.f_prev
        if abs(e_n) > self.override_mm:
            self.t_over += dt
        else:
            self.t_over = max(0.0, self.t_over - dt)
        if self.t_over > self.override_s:
            if self.g > 0.99:
                self.events.append(("yield", round(t, 3)))
            self.g = max(0.0, self.g - dt / self.fade_s)
        elif abs(e_n) < 1.0:
            self.g = min(1.0, self.g + dt / 0.5)
        f = f_cmd * self.g
        n = float(np.linalg.norm(f))
        if n > self.cap_N:
            f = f * self.cap_N / n
        df = f - self.f_prev
        dn = float(np.linalg.norm(df))
        lim = self.slew_N_s * dt
        if dn > lim:
            f = self.f_prev + df * lim / dn
        self.f_prev = f
        return f


# ----------------------------------------------------------------------------- plant + simulation
@dataclass
class SimConfig:
    hand: str = "relaxed"
    speed_mm_s: float = 25.0
    dt: float = 5e-4
    stage_delay_s: float = 1.5e-3
    stage_tau_s: float = 1.0 / (2 * math.pi * 25.0)
    force_gain_error: float = 0.0
    normal_pull_per_N: float = 2.2     # |F_z| per N of lateral capability in use (board.magnetics, near branch)
    normal_pull_offset_N: float = 0.0
    mu_skid: float = P.HAND["mu_paper"].value
    nose: str = "locked"               # "locked" (learn) | "assist"
    nose_travel_mm: float = 3.0
    nose_bw_hz: float = 20.0
    floating_anchor_tau_s: float = 0.0  # > 0: the writer relaxes and lets the pen be led (lead-through)
    seed: int = 0


def _hand_case(name):
    for c in H.cases():
        if c.name == name:
            return c
    raise KeyError(name)


def simulate_stroke(template: Path, intended: np.ndarray, guid: Guidance, cfg: SimConfig):
    """Simulate one pen-down stroke. Returns time series and metrics."""
    hc = _hand_case(cfg.hand)
    ipath = Path(intended)
    T = ipath.L / cfg.speed_mm_s + 0.25
    if guid.mode == "lead_through":
        T = template.L / 6.0 + 0.5  # the board leads; the relaxed hand sets a slower pace
    n = int(T / cfg.dt)
    dt = cfg.dt
    ramp = 0.12
    # intended ink position vs time (constant speed, smooth start/stop)
    tt = np.arange(n) * dt
    s_int = np.clip(cfg.speed_mm_s * np.where(tt < ramp, tt ** 2 / (2 * ramp), tt - ramp / 2), 0.0, ipath.L)
    xi = np.stack([np.interp(s_int, ipath.s, ipath.p[:, 0]), np.interp(s_int, ipath.s, ipath.p[:, 1])], 1) * 1e-3
    # states (m): pen handle x, v; hand xm, vm; nose q, qd; board force pipeline
    x = xi[0].copy(); v = np.zeros(2); xm = xi[0].copy(); vm = np.zeros(2)
    q = np.zeros(2); qd = np.zeros(2)
    anchor = xi[0].copy()
    f_board = np.zeros(2)
    nd = max(1, int(round(cfg.stage_delay_s / dt)))
    fifo = [np.zeros(2)] * nd
    sup = Supervisor(guid.cap_N, guid.slew_N_s, guid.override_mm, guid.override_s)
    s_prog = 0.0
    e_prev = 0.0
    ctrl_every = max(1, int(round(1e-3 / dt)))
    f_cmd_sup = np.zeros(2)
    wn = 2 * math.pi * cfg.nose_bw_hz
    out_ink = np.empty((n, 2)); out_F = np.empty((n, 2)); out_en = np.empty(n); out_fz = np.empty(n)
    Nw = P.HAND["writing_force_N"].value
    for i in range(n):
        t = i * dt
        ink = (x + q) * 1e3
        if i % ctrl_every == 0:
            # the board acts on the handle's gross error; the nose (if assisting) removes
            # the rest from the ink.  The pen knows q from its own Hall sensor, so the
            # handle position is ink - q.
            handle = x * 1e3
            s_prog, g_pt = template.project(handle, s_prog)
            t_hat = template.tangent(s_prog)
            n_hat = np.array([-t_hat[1], t_hat[0]])
            e_vec = handle - g_pt
            e_n = float(np.dot(e_vec, n_hat))
            e_n_dot = (e_n - e_prev) / (ctrl_every * dt)
            e_prev = e_n
            f_raw = guid.force(e_vec, e_n, n_hat, t_hat, v * 1e3, e_n_dot)
            f_cmd_sup = sup.step(f_raw, e_n, True, ctrl_every * dt, t)
            if cfg.nose == "assist":
                q_cmd = -e_vec * 1e-3
                nq = np.linalg.norm(q_cmd)
                lim = cfg.nose_travel_mm * 1e-3
                q_cmd = q_cmd if nq <= lim else q_cmd * lim / nq
            else:
                q_cmd = np.zeros(2)
        fifo.append(f_cmd_sup.copy())
        f_del = fifo.pop(0)
        f_board += (f_del * (1 + cfg.force_gain_error) - f_board) * dt / cfg.stage_tau_s
        fz = cfg.normal_pull_offset_N + cfg.normal_pull_per_N * float(np.linalg.norm(f_board))
        spd = float(np.linalg.norm(v))
        f_fric = -cfg.mu_skid * fz * (v / spd) * math.tanh(spd / 0.002) if spd > 1e-9 else np.zeros(2)
        # writer ground: intended path, or a floating anchor that follows the hand (lead-through)
        if cfg.floating_anchor_tau_s > 0:
            anchor += (xm - anchor) * dt / cfg.floating_anchor_tau_s
            ground = anchor
        else:
            ground = xi[i] - q * 0.0
        # dynamics (semi-implicit Euler)
        f_grip = hc.k1 * (x - xm) + hc.b1 * (v - vm)
        a = (f_board + f_fric - f_grip) / hc.m_pen
        v = v + a * dt
        x = x + v * dt
        if hc.k2 < 1e8:
            gv = (xi[min(i + 1, n - 1)] - xi[i]) / dt if cfg.floating_anchor_tau_s <= 0 else np.zeros(2)
            am = (f_grip - hc.k2 * (xm - ground) - hc.b2 * (vm - gv)) / hc.M
            vm = vm + am * dt
            xm = xm + vm * dt
        else:
            xm = ground.copy(); vm = np.zeros(2)
        # nose second-order response
        qdd = wn * wn * (q_cmd - q) - 2 * 0.7 * wn * qd
        qd = qd + qdd * dt
        q = q + qd * dt
        out_ink[i] = (x + q) * 1e3
        out_F[i] = f_board
        out_en[i] = e_prev
        out_fz[i] = fz
    # metrics: distance of ink to the template (closest point, full template)
    dense = template.resample(max(200, int(template.L * 10)))
    def dist(pts):
        d = np.sqrt(((pts[:, None, :] - dense[None, :, :]) ** 2).sum(-1)).min(1)
        return d
    sel = slice(int(0.1 / dt), n)
    d_ink = dist(out_ink[sel][::10])
    d_int = dist(ipath.resample(400))
    return {
        "t": tt, "ink": out_ink, "F": out_F, "e_n": out_en, "fz": out_fz, "intended": ipath.p,
        "template": template.p,
        "metrics": {
            "ink_to_template_rms_mm": float(np.sqrt(np.mean(d_ink ** 2))),
            "ink_to_template_max_mm": float(d_ink.max()),
            "intended_to_template_rms_mm": float(np.sqrt(np.mean(d_int ** 2))),
            "force_rms_N": float(np.sqrt(np.mean((out_F[sel] ** 2).sum(1)))),
            "force_max_N": float(np.sqrt((out_F[sel] ** 2).sum(1)).max()),
            "normal_pull_mean_N": float(out_fz[sel].mean()),
            "yield_events": len(sup.events),
            "duration_s": float(T),
        },
    }


# ----------------------------------------------------------------------------- scenarios
def scenario_tracing(mode, hand="relaxed", nose="locked", seed=0, dev_rms=1.5, speed=25.0):
    rng = np.random.default_rng(seed)
    res = []
    for stroke in tracing_word(8.0, 20.0, 150.0):
        tp = Path(stroke)
        intended = smooth_deviation(tp, dev_rms, rng)
        guid = Guidance(mode=mode)
        cfg = SimConfig(hand=hand, nose=nose, speed_mm_s=speed, seed=seed)
        res.append(simulate_stroke(tp, intended, guid, cfg))
    return res


def scenario_write_big(mode, hand="relaxed", seed=0, target_mm=10.0, start_ratio=0.8, end_ratio=0.6, speed=30.0):
    """PD 'write big': template loops of target height; the writer's loops shrink (PDT-05/06)."""
    tp = Path(loops(5, target_mm, 6.0, 900, 20.0, 150.0))
    intended = loops(5, target_mm, 6.0, 900, 20.0, 150.0,
                     scale_fn=lambda u: start_ratio + (end_ratio - start_ratio) * u)
    guid = Guidance(mode=mode)
    cfg = SimConfig(hand=hand, speed_mm_s=speed, seed=seed)
    r = simulate_stroke(tp, intended, guid, cfg)
    y = r["ink"][:, 1] - 150.0
    yi = intended[:, 1] - 150.0
    r["metrics"]["loop_height_ratio_ink"] = float((np.percentile(y, 99) - np.percentile(y, 1)) / target_mm)
    r["metrics"]["loop_height_ratio_intended"] = float((yi.max() - yi.min()) / target_mm)
    # mean of per-loop heights
    return r


def scenario_reversal(mode, hand="relaxed", lead_through=False):
    """Dyslexia-type reversal: the template is 'd', the writer intends 'b'."""
    tpl = letter_b_or_d("d", 8.0, 30.0, 150.0)
    intended = letter_b_or_d("b", 8.0, 30.0, 150.0)
    out = []
    for k in range(2):
        tp = Path(tpl[k])
        guid = Guidance(mode=mode)
        cfg = SimConfig(hand=hand, speed_mm_s=25.0,
                        floating_anchor_tau_s=(0.25 if lead_through else 0.0))
        r = simulate_stroke(tp, intended[k], guid, cfg)
        if k == 1:
            ink = r["ink"][int(0.1 / cfg.dt):]
            r["metrics"]["bowl_ink_on_correct_side_fraction"] = float(np.mean(ink[:, 0] < 30.0 - 0.5))
        out.append(r)
    return out
