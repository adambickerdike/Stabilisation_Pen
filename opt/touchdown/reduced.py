"""Differentiable reduced touchdown model (torch) and adjoint-gradient fit of the feed-forward law.

Planar model in the tilt plane (azimuth 0, roll 0) with the P1 parameter values (sim/pencil/model.build_params):
  housing (x, z) on the two-stage hand impedance, skid contact (penalty + tanh friction);
  refill slide s (mass, spring, damping, bushing friction, front stop);
  ball-page contact: smooth penalty normal force, friction -mu N tanh(v / v_s) (P1: LuGre bristles);
  stage q1 as a second-order system driven by the piezo force behind a first-order driver lag;
  the discrete controller of P1: axial sensor 1 kHz / 1 ms delay, Hall 10 kHz / 0.1 ms delay, estimator 2 kHz,
  servo 10 kHz (feedforward + integral + filtered damping), the feed-forward law with a smooth contact state.
Left out: the out-of-plane axis, hysteresis, sensor noise, the drive slew limit, LuGre pre-sliding; the
friction regularisation speeds are raised (bushing 1 mm/s, ball and skid 2 mm/s) so that the linearised
dynamics, which the adjoint integrates backwards, stay stable at the 50 us step.

Gradients: reverse-mode automatic differentiation through the whole time loop (backpropagation through time),
which is the discrete adjoint of the simulation, so one backward pass gives d(loss)/d(all law parameters).
Evidence status: SIMULATION of a reduced model; its agreement with P1 is checked on a touchdown event
(check_against_p1), and its optimum only seeds the P1 search.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import torch

from sim.pencil.layout import IDX

# Keep physical calculations in float64 without changing the caller's ML defaults.


def _softplus(x, width):
    return width * torch.nn.functional.softplus(x / width)


@dataclass
class Events:
    """Hand inputs of a batch of touchdown / lift events (numpy arrays, batch x n)."""
    t: np.ndarray
    x_ref: np.ndarray
    vx_ref: np.ndarray
    z_ref: np.ndarray
    vz_ref: np.ndarray
    push: np.ndarray
    start_down: np.ndarray          # batch: True -> start in writing contact (lift event)
    labels: list


def smooth_step(t, t0, T=0.06):
    """Moving-average step of width T centred on t0 (the lift smoothing of stabpen.signals.lognormal_handwriting)."""
    return np.clip((t - (t0 - T / 2)) / T, 0.0, 1.0)


def make_events(dt=50e-6, T=0.22, lift=1.5e-3, N0=1.0, vx=(0.0, 0.02), t_down=0.04, t_up=0.14):
    """Down-then-up events: the hand lowers the pen (ramp centred on t_down), writes in place or while moving at
    vx, and lifts it again (ramp centred on t_up).  P1 cannot start in writing contact, so every event starts in
    the air; the touchdown and the lift of the same event are scored together."""
    n = int(round(T / dt))
    t = np.arange(n) * dt
    rows = {k: [] for k in ("x_ref", "vx_ref", "z_ref", "vz_ref", "push")}
    labels = []
    for v in vx:
        z = lift * (1 - smooth_step(t, t_down) + smooth_step(t, t_up))
        rows["x_ref"].append(v * t); rows["vx_ref"].append(np.full(n, v))
        rows["z_ref"].append(z); rows["vz_ref"].append(np.gradient(z, dt))
        rows["push"].append(N0 * (1 - z / lift))
        labels.append(f"down-up, hand {v * 1e3:.0f} mm/s")
    return Events(t=t, start_down=np.zeros(len(vx), bool), labels=labels, **{k: np.array(v) for k, v in rows.items()})


class ReducedTouchdown:
    """Batch simulator; law parameters are torch tensors, everything else comes from the P1 parameter vector."""

    def __init__(self, Pv, dt=50e-6, v_fric=2e-3, v_bush=1e-3):
        g = lambda n: float(Pv[IDX[n]])   # noqa: E731
        self.th = g("theta"); self.st, self.ct = math.sin(self.th), math.cos(self.th)
        self.m_eq, self.k_b, self.k_par, self.c_st, self.m_cpl = g("m_eq"), g("k_b"), g("k_par"), g("c_st"), g("m_cpl")
        self.q_stop, self.k_stop, self.c_stop = g("q_stop"), g("k_stop"), g("c_stop")
        self.m_ax, self.k_sp, self.F_sp0, self.c_ax = g("m_ax"), g("k_sp"), g("F_sp0"), g("c_ax")
        self.s_min, self.mu_b, self.bear = g("s_min"), g("mu_b"), g("bear_fac")
        # regularisation speeds of the tanh friction laws: P1 uses 0.1 mm/s for the bushing (explicit, so its
        # linearisation is unstable at dt = 25 us and only the tanh bounds it); the adjoint needs a stable
        # linearisation, so the reduced model uses v_bush (1 mm/s) and v_fric (2 mm/s): c dt / m <= 1.1
        self.v_b = max(g("v_b"), v_bush)
        self.M_t, self.K_hxy, self.C_hxy, self.K_hz, self.C_hz, self.z0 = g("M_t"), g("K_hxy"), g("C_hxy"), g("K_hz"), g("C_hz"), g("z0")
        self.M_h, self.k_arm, self.b_arm = g("M_hand"), g("k_arm"), g("b_arm")
        self.k_p, self.c_p, self.r_b, self.mu = g("k_p"), g("c_p"), g("r_b"), g("mu_k")
        self.k_sk, self.c_sk, self.mu_sk = g("k_sk"), g("c_sk"), g("mu_sk")
        self.Ki, self.Kp, self.Kd, self.d_filt = g("Ki"), g("Kp"), g("Kd"), g("d_filt")
        self.ffr, self.Fb0, self.drv_tau = g("ff_ref"), g("F_bias0"), g("drv_tau")
        self.F_max = self.k_b * g("g_V") * 0.5 * g("V_rail")          # blocked force at full drive
        self.q_lim, self.q_tap = g("q_lim"), g("q_taper")
        self.dt = dt
        P1dt = g("dt")
        self.adec = max(1, int(round(g("ax_decim") * P1dt / dt))); self.adl = max(1, int(round(g("ax_delay") * P1dt / dt)))
        self.sdec = max(1, int(round(g("stage_decim") * P1dt / dt))); self.vdec = max(1, int(round(g("servo_decim") * P1dt / dt)))
        self.hd = max(0, int(round(g("hall_delay") * P1dt / dt)))
        self.v_fric = v_fric
        self.s_ref0 = (max(1.0 - self.F_sp0 / self.st, 0.0) / self.k_sk - (self.F_sp0 / self.st) / self.k_p) / self.st

    # ------------------------------------------------------------------ simulation
    def simulate(self, ev: Events, law: Dict[str, torch.Tensor], ff_on=True, record=False, handover=True):
        B, n = ev.x_ref.shape
        dt, st, ct = self.dt, self.st, self.ct
        T = lambda a: torch.as_tensor(a, dtype=torch.float64)   # noqa: E731
        xr, vxr, zr, vzr, push = T(ev.x_ref), T(ev.vx_ref), T(ev.z_ref), T(ev.vz_ref), T(ev.push)
        down = T(ev.start_down.astype(float))
        sref = law.get("s_ref", T(self.s_ref0))
        k_tot = self.k_b + self.k_par
        # initial state: in the air on the stop, or in writing contact at the working slide
        N_sk0 = max(1.0 - self.F_sp0 / st, 0.0)
        hz = torch.where(down > 0, T(self.z0 - self.r_b + 0.0), zr[:, 0] + self.z0 - self.r_b)
        hx = xr[:, 0].clone(); vx = torch.zeros(B, dtype=torch.float64); vz = torch.zeros(B, dtype=torch.float64); ax_ = torch.zeros(B, dtype=torch.float64); az_ = torch.zeros(B, dtype=torch.float64)
        dMx = torch.zeros(B, dtype=torch.float64); dMz = torch.zeros(B, dtype=torch.float64); vMx = torch.zeros(B, dtype=torch.float64); vMz = torch.zeros(B, dtype=torch.float64)
        s = torch.where(down > 0, T(self.s_ref0), T(self.s_min)); sd = torch.zeros(B, dtype=torch.float64); sdd = torch.zeros(B, dtype=torch.float64)
        q = torch.zeros(B, dtype=torch.float64); qd = torch.zeros(B, dtype=torch.float64); qdd = torch.zeros(B, dtype=torch.float64)
        Fdrv = down * self.Fb0; eint = torch.zeros(B, dtype=torch.float64); edf = torch.zeros(B, dtype=torch.float64); qm_prev = torch.zeros(B, dtype=torch.float64)
        qr = torch.zeros(B, dtype=torch.float64); qr1 = torch.zeros(B, dtype=torch.float64); qr2 = torch.zeros(B, dtype=torch.float64)
        s_hist, q_hist = [], []
        s_meas = s.clone(); x_ab = torch.zeros(B, dtype=torch.float64); v_ab = torch.zeros(B, dtype=torch.float64); k_samp = 0; c_w = down.clone()
        lp = law.get("lp_hz", T(200.0))
        Ta = self.adec * dt
        r_ab = torch.exp(-2 * math.pi * lp * Ta); a_ab = 1 - r_ab ** 2; b_ab = (1 - r_ab) ** 2
        q_pre = (sref - self.s_min) * ct / st
        alpha_d = 1 - math.exp(-2 * math.pi * self.d_filt * dt * self.vdec)
        ex_drv = 1 - math.exp(-dt / self.drv_tau)
        Ts = self.sdec * dt; Tv = self.vdec * dt
        rec = {k: [] for k in ("Cx", "Cz", "N", "Ns", "s", "q", "qr", "hx", "hz", "cw")} if record else None
        loss_num = torch.zeros(B, dtype=torch.float64); loss_den = torch.zeros(B, dtype=torch.float64); travel_pen = torch.zeros(B, dtype=torch.float64)
        for k in range(n):
            if k % self.sdec == 0:
                if ff_on:
                    shp = x_ab + v_ab * ((k - k_samp) * dt + law.get("lead_s", T(0.0)))
                    q_law = law.get("gain", T(1.0)) * st * ct * (sref - shp)
                    q_ff = (1 - c_w) * law.get("pre", T(1.0)) * q_pre + c_w * q_law
                    # P1's radial taper (core._taper): linear up to q_lim - q_taper, tanh-limited beyond
                    knee = self.q_lim - self.q_tap
                    a = torch.abs(q_ff)
                    q_ff = torch.sign(q_ff) * torch.where(a > knee, knee + self.q_tap * torch.tanh((a - knee) / self.q_tap), a)
                else:
                    q_ff = torch.zeros(B, dtype=torch.float64)
                qr2, qr1, qr = qr1, qr, q_ff
            qddr = (qr - 2 * qr1 + qr2) / Ts ** 2; qdr = (qr - qr1) / Ts
            if k % self.vdec == 0:
                qm = q_hist[k - self.hd] if k - self.hd >= 0 else q
                e = qr - qm
                vmeas = (qm - qm_prev) / Tv; qm_prev = qm
                edf = edf + alpha_d * (-vmeas - edf)
                bias = (law.get("k_load", T(1.0)) * c_w if ff_on else c_w) * self.Fb0
                F = (self.ffr * (k_tot * qr + (self.c_st + self.Kd) * qdr + self.m_eq * qddr) + bias
                     + self.Kp * e + self.Ki * eint + self.Kd * edf)
                F = torch.clamp(F, -self.F_max, self.F_max)
                eint = eint + e * Tv
            Fdrv = Fdrv + (F - Fdrv) * ex_drv
            # kinematics
            Cx = hx + q * st + s * ct
            Cz = hz + self.r_b - q * ct + s * st
            vax = sd
            vCx = vx + qd * st + vax * ct
            vCz = vz - qd * ct + vax * st
            N = _softplus(self.k_p * (self.r_b - Cz) - self.c_p * vCz, 2e-4)
            fx = -self.mu * N * torch.tanh(vCx / self.v_fric)
            Ns = _softplus(self.k_sk * (-hz) - self.c_sk * vz, 2e-4)
            fsx = -self.mu_sk * Ns * torch.tanh(vx / self.v_fric)
            Q0 = fx * st - N * ct
            Qs = fx * ct + N * st
            # hand (two-stage impedance)
            Fhx = self.K_hxy * (xr[:, k] + dMx - hx) + self.C_hxy * (vxr[:, k] + vMx - vx)
            Fhz = self.K_hz * (zr[:, k] + self.z0 - self.r_b + dMz - hz) + self.C_hz * (vzr[:, k] + vMz - vz) - push[:, k]
            aMx = (-Fhx - self.k_arm * dMx - self.b_arm * vMx) / self.M_h
            aMz = (-(Fhz + push[:, k]) - self.k_arm * dMz - self.b_arm * vMz) / self.M_h
            vMx = vMx + aMx * dt; vMz = vMz + aMz * dt; dMx = dMx + vMx * dt; dMz = dMz + vMz * dt
            # stage and slide
            Fs = -_softplus(self.k_stop * (torch.abs(q) - self.q_stop), 1e-3) * torch.sign(q)
            qdd = (Fdrv - k_tot * q - self.c_st * qd + Q0 + Fs - self.m_cpl * (ax_ * st - az_ * ct)) / self.m_eq
            Fst = _softplus(self.k_stop * (self.s_min - s), 1e-3) - self.c_stop * torch.clamp(sd, max=0.0) * (s < self.s_min)
            sdd = (Qs - (self.F_sp0 + self.k_sp * s) - self.c_ax * sd - self.mu_b * self.bear * torch.abs(Q0) * torch.tanh(sd / self.v_b)
                   + Fst - self.m_ax * (ax_ * ct + az_ * st)) / self.m_ax
            cx = self.m_cpl * qdd * st + self.m_ax * sdd * ct
            cz = -self.m_cpl * qdd * ct + self.m_ax * sdd * st
            ax_ = (Fhx + fx + fsx - cx) / self.M_t
            az_ = (Fhz + N + Ns - cz) / self.M_t
            vx = vx + ax_ * dt; vz = vz + az_ * dt; hx = hx + vx * dt; hz = hz + vz * dt
            qd = qd + qdd * dt; q = q + qd * dt
            sd = sd + sdd * dt; s = s + sd * dt
            q_hist.append(q); s_hist.append(s)
            # axial sensor + feed-forward estimator (1 kHz, 1 ms delay)
            if k % self.adec == 0 and k >= self.adl:
                s_meas = s_hist[k - self.adl]
                qh = q_hist[k - self.adl + self.hd] if k - self.adl + self.hd < len(q_hist) else q
                sh_raw = s_meas - law.get("kappa", T(1.0)) * (ct / st) * qh
                c_old = c_w
                c_w = torch.sigmoid((s_meas - self.s_min - law.get("det_s", T(20e-6))) / 4e-6)
                if ff_on and handover:
                    # load hand-over of the P1 core (td_handover), in smooth form: as the contact state rises the
                    # integrator gives up the load share it carries; as it falls it drops a negative share
                    kl_Fb = law.get("k_load", T(1.0)) * self.Fb0
                    dc = c_w - c_old
                    carried = self.Ki * eint
                    eint = eint - (torch.clamp(dc, min=0.0) * torch.minimum(torch.clamp(carried, min=0.0), kl_Fb)
                                   - torch.clamp(-dc, min=0.0) * torch.minimum(torch.clamp(-carried, min=0.0), kl_Fb)) / self.Ki
                pred = x_ab + v_ab * (k - k_samp) * dt
                res = sh_raw - pred
                # reset to the measurement while on the stop in the air, track otherwise
                x_ab = c_w * (pred + a_ab * res) + (1 - c_w) * sh_raw
                v_ab = c_w * (v_ab + b_ab / Ta * res)
                k_samp = k
            # loss: ink deviation from the working position during contact, travel beyond the usable limit
            w = N / (N + 0.01)
            e_ink = Cx - (hx + sref * ct)
            loss_num = loss_num + w * e_ink ** 2
            loss_den = loss_den + w
            travel_pen = travel_pen + torch.relu(torch.abs(qr) - self.q_lim) ** 2
            if record:
                for key, val in (("Cx", Cx), ("Cz", Cz), ("N", N), ("Ns", Ns), ("s", s), ("q", q), ("qr", qr), ("hx", hx), ("hz", hz), ("cw", c_w)):
                    rec[key].append(val.detach().clone())
        rms = torch.sqrt(loss_num / torch.clamp(loss_den, min=1e-9))
        out = {"rms_ink": rms, "travel_pen": travel_pen / n}
        if record:
            out["rec"] = {k: torch.stack(v, 1).numpy() for k, v in rec.items()}
        return out


PARAM_INIT = {"gain": 1.0, "kappa": 1.0, "lead_s": 0.5e-3, "pre": 1.0, "k_load": 1.0}
SCALE = {"gain": 1.0, "kappa": 1.0, "lead_s": 1e-3, "pre": 1.0, "k_load": 1.0}


def fit_law(model: ReducedTouchdown, ev: Events, free=("gain", "kappa", "lead_s", "pre", "k_load"), iters=40, lr=0.05,
            fixed: Optional[Dict[str, float]] = None, verbose=True, handover=True):
    """Adam on the adjoint (BPTT) gradient of the mean RMS ink deviation over the batch."""
    fixed = dict(fixed or {})
    z = {k: torch.tensor(PARAM_INIT[k] / SCALE[k], requires_grad=True, dtype=torch.float64) for k in free}
    opt = torch.optim.Adam(list(z.values()), lr=lr)
    hist = []
    for it in range(iters):
        law = {k: v * SCALE[k] for k, v in z.items()}
        law.update({k: torch.tensor(v, dtype=torch.float64) for k, v in fixed.items()})
        out = model.simulate(ev, law, handover=handover)
        loss = (out["rms_ink"] * 1e6).mean() + 1e12 * out["travel_pen"].mean()
        opt.zero_grad()
        loss.backward()
        grads = {k: float(v.grad) for k, v in z.items()}
        opt.step()
        with torch.no_grad():
            if "lead_s" in z:
                z["lead_s"].clamp_(0.0, 4.0)
            if "pre" in z:
                z["pre"].clamp_(0.0, 1.5)
        row = {"iter": it, "loss_um": float(loss.detach()), "per_event_um": [float(v) for v in out["rms_ink"].detach() * 1e6],
               **{k: float(v.detach()) * SCALE[k] for k, v in z.items()}, "grad": grads}
        hist.append(row)
        if verbose:
            print(f"adjoint it {it:2d} loss {row['loss_um']:.2f} um  " + " ".join(f"{k}={row[k]:.4g}" for k in free), flush=True)
    return hist


def evaluate_law(model, ev, law_values: Dict[str, float], ff_on=True, record=False, handover=True):
    with torch.no_grad():
        law = {k: torch.tensor(v, dtype=torch.float64) for k, v in law_values.items()}
        out = model.simulate(ev, law, ff_on=ff_on, record=record, handover=handover)
    res = {"rms_ink_um": [float(v) * 1e6 for v in out["rms_ink"]], "mean_rms_ink_um": float(out["rms_ink"].mean()) * 1e6}
    if record:
        res["rec"] = out["rec"]
    return res


def p1_event_scenario(vx=0.0, T=0.22, dt=25e-6, theta=50.0, N0=1.0, lift=1.5e-3, t_down=0.04, t_up=0.14):
    """The same hand input for P1 (sim.pensim.scenarios assembly) as make_events for one event."""
    from sim.pensim import scenarios
    from stabpen import signals as sg
    n = int(round(T / dt))
    t = np.arange(n) * dt
    z = lift * (1 - smooth_step(t, t_down) + smooth_step(t, t_up))
    xy = np.column_stack([vx * t, np.zeros(n)])
    it = sg.Intended(t=t, xy=xy, pen_down=(z < lift / 2), lift=z, features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)), N0, theta)
    sc.fpush = N0 * (1 - z / lift)
    return sc


def check_against_p1(law_values: Dict[str, float], margin=0.3e-3, dt_red=50e-6, vx=(0.0, 0.02), ff_on=True):
    """Run the same down-up event in P1 (feed-forward with the same law, noise and hysteresis off) and in the
    reduced model; compare the traces over the event."""
    from sim.pencil import model as M
    from .law import TouchdownLaw
    out, traces = {}, {}
    for v in vx:
        sc = p1_event_scenario(v)
        keys = ("gain", "kappa", "lead_s", "pre", "k_load", "lp_hz")
        law = TouchdownLaw(margin=margin, dz=0.0, enabled=ff_on, **{k: v2 for k, v2 in law_values.items() if k in keys})
        cfg = law.pencil_config(overrides={"hall_noise": 0.0, "sensing.axial_noise": 0.0}, hysteresis=False)
        r = M.run(sc, M.Controller(mode="neutral"), cfg, seed=1, rec_hz=40000)
        model = ReducedTouchdown(r.P, dt=dt_red)
        ev = make_events(dt=dt_red, vx=(v,))
        s_ref = model.s_ref0
        red = evaluate_law(model, ev, dict(law_values, s_ref=s_ref), ff_on=ff_on, record=True)
        rr = red["rec"]
        tr, tp = ev.t, r["t"]
        res = {}
        for name, p1v, redv in (("ink_minus_housing_um", (r["Cx"] - r["pHx"]) * 1e6, (rr["Cx"][0] - rr["hx"][0]) * 1e6),
                                ("slide_um", r["s"] * 1e6, rr["s"][0] * 1e6), ("stage_q1_um", r["q1"] * 1e6, rr["q"][0] * 1e6),
                                ("housing_height_um", (r["pHz"] - model.r_b) * 1e6, rr["hz"][0] * 1e6),
                                ("nib_normal_N", r["Nn"], rr["N"][0])):
            p1i = np.interp(tr, tp, p1v)
            res[name] = {"rms_diff": float(np.sqrt(np.mean((p1i - redv) ** 2))), "p1_range": float(np.ptp(p1i)),
                         "reduced_range": float(np.ptp(redv))}
            traces.setdefault(f"vx{v * 1e3:.0f}", {"t": tr}).setdefault("p1", {})[name] = p1i
            traces[f"vx{v * 1e3:.0f}"].setdefault("reduced", {})[name] = redv
        c1 = np.interp(tr, tp, r["contact"]) > 0.5
        c2 = rr["N"][0] > 1e-3
        on1, on2 = np.flatnonzero(np.diff(c1.astype(int)) == 1), np.flatnonzero(np.diff(c2.astype(int)) == 1)
        off1, off2 = np.flatnonzero(np.diff(c1.astype(int)) == -1), np.flatnonzero(np.diff(c2.astype(int)) == -1)
        res["contact_agreement"] = float(np.mean(c1 == c2))
        res["touchdown_ms"] = {"p1": float(tr[on1[0]] * 1e3) if len(on1) else None, "reduced": float(tr[on2[0]] * 1e3) if len(on2) else None}
        res["lift_ms"] = {"p1": float(tr[off1[-1]] * 1e3) if len(off1) else None, "reduced": float(tr[off2[-1]] * 1e3) if len(off2) else None}
        e1 = np.interp(tr, tp, r["Cx"] - r["pHx"]) - s_ref * model.ct
        res["ink_dev_rms_contact_um"] = {"p1": float(np.sqrt(np.mean(e1[c1] ** 2)) * 1e6) if c1.any() else None,
                                         "reduced": red["rms_ink_um"][0]}
        out[f"vx{v * 1e3:.0f}"] = res
    return out, traces


# ------------------------------------------------------------------ adjoint study (structure and initial gains)
ABLATIONS = {
    "full": {"free": ("gain", "kappa", "lead_s", "pre", "k_load"), "fixed": {}},
    "no_prepositioning": {"free": ("gain", "kappa", "lead_s", "k_load"), "fixed": {"pre": 0.0}},
    "no_lead": {"free": ("gain", "kappa", "pre", "k_load"), "fixed": {"lead_s": 0.0}},
    "no_slide_removal": {"free": ("gain", "lead_s", "pre", "k_load"), "fixed": {"kappa": 0.0}},
    "full_without_handover": {"free": ("gain", "kappa", "lead_s", "pre", "k_load"), "fixed": {}, "handover": False},
}


def _study_one(args):
    name, iters, margin = args
    torch.set_num_threads(1)
    from sim.pencil import model as M
    from .law import TouchdownLaw
    sc = p1_event_scenario(0.0)
    Pv, _ = M.build_params(sc, M.Controller(mode="neutral"), TouchdownLaw(margin=margin).pencil_config())
    model = ReducedTouchdown(Pv)
    ev = make_events()
    spec = ABLATIONS[name]
    ho = spec.get("handover", True)
    hist = fit_law(model, ev, free=spec["free"], fixed=spec["fixed"], iters=iters, verbose=False, handover=ho)
    best = min(hist, key=lambda h: h["loss_um"])
    final = {k: best[k] for k in spec["free"]}
    final.update(spec["fixed"])
    ev_best = evaluate_law(model, ev, final, handover=ho)
    return name, {"history": hist, "best": final, "best_loss_um": best["loss_um"], "per_event_um": ev_best["rms_ink_um"],
                  "labels": ev.labels}


def adjoint_study(iters=24, margin=0.3e-3, workers=2, names=None):
    """Fit each law structure by Adam on its adjoint gradient; also score the ideal law and no feed-forward."""
    from concurrent.futures import ProcessPoolExecutor
    from sim.pencil import model as M
    from .law import TouchdownLaw
    names = list(names or ABLATIONS)
    with ProcessPoolExecutor(workers) as ex:
        res = dict(ex.map(_study_one, [(n, iters, margin) for n in names]))
    torch.set_num_threads(1)
    sc = p1_event_scenario(0.0)
    Pv, _ = M.build_params(sc, M.Controller(mode="neutral"), TouchdownLaw(margin=margin).pencil_config())
    model = ReducedTouchdown(Pv)
    ev = make_events()
    res["ideal_law"] = {"best": dict(PARAM_INIT, lead_s=0.0), **evaluate_law(model, ev, dict(PARAM_INIT, lead_s=0.0))}
    res["ideal_law_without_handover"] = {"best": dict(PARAM_INIT, lead_s=0.0),
                                         **evaluate_law(model, ev, dict(PARAM_INIT, lead_s=0.0), handover=False)}
    res["no_feedforward"] = evaluate_law(model, ev, {}, ff_on=False)
    res["events"] = ev.labels
    res["margin_mm"] = margin * 1e3
    return res
