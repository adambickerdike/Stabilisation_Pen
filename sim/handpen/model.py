"""Python interface to the H1 core: parameter packing, scenarios with a rotational tremor component,
runs, and the oracle (perfect disturbance knowledge) controllers.

Oracle controllers (estimation excluded; the other study handles estimation):
  * nib stage: the stage cancels the true deviation of the ball from its clean path (model P1's oracle),
    within P1's limits (0.30 mm soft limit, 0.40 mm stop, 2 kHz reference, slew limit);
  * reaction mass and control-moment gyroscope: iterative learning on the true disturbance.  Each
    iteration runs the full nonlinear simulation, takes the ball's deviation from the clean path (same
    pen, device neutral, no tremor), and updates the device's feed-forward input by the inverse of the
    frictionless linear model (linear.py) in the 2-20 Hz band.  This converges on the best open-loop
    input the device can apply within its force, stroke, gimbal-angle and gimbal-rate limits; it is an
    upper bound on what any causal estimator could achieve with the same hardware.
Evidence status: SIMULATION.
"""
from __future__ import annotations

import copy
import math
from dataclasses import replace
from typing import Optional

import numpy as np

from . import core
from . import grip as G
from . import linear as L
from .params import (CONTACT, Config, Device, geometry_vectors, pen_with_device, protrusion_centre, D2R)
from stabpen import signals as sg

MODEL_VERSION = "H1.0"
DT = 25e-6
REC_HZ = 2000.0


# ------------------------------------------------------------------------------------------ scenarios
class Tremor:
    """Hand tremor: translation (TremorSpec on the hand path, model P1 convention) plus an optional rotation of the
    hand frame about a wrist axis through a pivot L_p behind the grip.  amp_rot is the nib-level peak amplitude
    of the rotational part (m); the angle is amp / (distance from the pivot to the nib)."""

    def __init__(self, f0=6.0, amp_trans=0.3e-3, amp_rot=0.0, L_p=0.175, axis="yaw", pivot_height=0.04, spec_kw=None):
        self.f0, self.amp_trans, self.amp_rot, self.L_p, self.axis, self.pivot_height = f0, amp_trans, amp_rot, L_p, axis, pivot_height
        self.spec_kw = spec_kw or {}

    def spec(self, amp):
        return sg.TremorSpec(f0=self.f0, amp_pk=amp, **self.spec_kw)

    def label(self):
        return f"{self.f0:g}Hz trans {self.amp_trans * 1e3:.2f}mm rot {self.amp_rot * 1e3:.2f}mm ({self.axis}, L_p {self.L_p * 1e3:.0f} mm)"


def build_scenario(seed=200, duration=5.0, tremor: Optional[Tremor] = None, theta_deg=50.0, N0=1.0):
    from sim.pensim import scenarios
    tr = None if (tremor is None or tremor.amp_trans <= 0) else tremor.spec(tremor.amp_trans)
    scn = scenarios.handwriting(seed=seed, duration=duration, tremor=tr, theta_deg=theta_deg, N0=N0)
    n = len(scn.t)
    psi = np.zeros(n)
    if tremor is not None and tremor.amp_rot > 0:
        spec = tremor.spec(tremor.amp_rot)
        spec = replace(spec, ellipticity=0.0, orientation=0.0)
        d = sg.tremor(scn.t, spec, np.random.default_rng(seed + 3000))
        psi = d[:, 0]              # nib-level displacement; converted to an angle in pack()
    scn.psi_disp = psi
    scn.tremor_obj = tremor
    return scn


def rotation_geometry(cfg: Config, tremor: Optional[Tremor]):
    """Axis and pivot of the rotational tremor, and the lever from the pivot to the nib (m)."""
    a, t1, t2, n, h = geometry_vectors(cfg.theta_deg, cfg.phi_deg)
    if tremor is None:
        return n, np.zeros(3), 1.0
    g = G.from_config(cfg)
    zc = g.z_c
    th = cfg.theta_deg * D2R
    if tremor.axis == "yaw":          # wrist flexion-extension with a semi-pronated hand: axis ~ page normal
        axis = n
        P = (zc * math.cos(th) + tremor.L_p) * h
        lever = zc * math.cos(th) + tremor.L_p
    elif tremor.axis == "pitch":      # palm-down flexion-extension: axis along t2 (page y), pivot above the page
        axis = t2
        P = (zc * math.cos(th) + tremor.L_p) * h + tremor.pivot_height * n
        lever = math.hypot(zc * math.cos(th) + tremor.L_p, tremor.pivot_height)
    else:
        raise ValueError(tremor.axis)
    return axis, P, lever


# ------------------------------------------------------------------------------------------ packing
def mass_matrix(body, t1, t2):
    m, zg, Jn = body.m, body.z_g, body.J_nib
    M = np.zeros((5, 5))
    M[0:3, 0:3] = m * np.eye(3)
    M[0:3, 3] = m * zg * t1
    M[0:3, 4] = m * zg * t2
    M[3, 0:3] = m * zg * t1
    M[4, 0:3] = m * zg * t2
    M[3, 3] = Jn
    M[4, 4] = Jn
    return M


def pack(cfg: Config, n_steps: int, dt: float = DT, rec_hz: float = REC_HZ, tremor: Optional[Tremor] = None):
    Pv = np.zeros(core.NP)

    def s(name, val):
        Pv[core.IDX[name]] = float(val)

    a, t1, t2, nvec, h = geometry_vectors(cfg.theta_deg, cfg.phi_deg)
    th = cfg.theta_deg * D2R
    s("dt", dt); s("n_steps", n_steps); s("rec_decim", round(1.0 / (rec_hz * dt)))
    for nm, vec in (("a", a), ("t1", t1), ("t2", t2)):
        for j, c in enumerate("xyz"):
            s(f"{nm}{c}", vec[j])
    s("sin_th", math.sin(th)); s("cos_th", math.cos(th))
    body = pen_with_device(cfg)
    Minv = np.linalg.inv(mass_matrix(body, t1, t2))
    for i in range(5):
        for j in range(i, 5):
            s(f"Mi{i}{j}", Minv[i, j])
    g = G.from_config(cfg)
    s("zf", g.z_f); s("zw", g.z_w); s("kf", g.k_f); s("kw", g.k_w); s("ka", g.k_a); s("kap", g.kappa_f); s("beta_g", g.beta)
    s("Mh", cfg.M_hand); s("karm", cfg.k_arm); s("barm", cfg.b_arm)
    N_nib0 = cfg.F_c / math.sin(th)
    N_sk0 = max(cfg.N0 - N_nib0, 0.0)
    r_b = CONTACT["r_b"]
    s("z0", r_b - (N_sk0 / cfg.k_sk if cfg.skid else 0.0))
    axis, P, lever = rotation_geometry(cfg, tremor)
    for j, c in enumerate("xyz"):
        s(f"nw{c}", axis[j]); s(f"P{c}", P[j])
    s("skid_on", 1.0 if cfg.skid else 0.0); s("k_sk", cfg.k_sk); s("c_sk", cfg.c_sk)
    s("p_nom", protrusion_centre(cfg.theta_deg)); s("r_ring", CONTACT["r_ring"]); s("r_b", r_b)
    if getattr(cfg, "skid_geom", None) is not None:       # extension (opt/inertial): e.g. a rigid nose whose ball carries the load
        s("p_nom", cfg.skid_geom[0]); s("r_ring", cfg.skid_geom[1])
    mu = max(cfg.mu_skid, 1e-6)
    s("mu_sk", mu); s("mus_sk", mu * cfg.ms_ratio); s("vs", cfg.v_s)
    s("sg0_sk", mu * cfg.ms_ratio / CONTACT["presliding"] if cfg.mu_skid > 0 else 0.0)
    mun = max(cfg.mu_nib, 1e-6)
    s("N_nib0", N_nib0); s("mu_n", mun); s("mus_n", mun * cfg.ms_ratio)
    s("sg0_n", mun * cfg.ms_ratio / CONTACT["presliding"] if cfg.mu_nib > 0 else 0.0)
    s("margin_b", 0.30e-3 * math.sin(th)); s("ramp_b", 20e-6); s("c_visc", cfg.c_visc)
    dv = cfg.device
    s("kind", core.KINDS[dv.kind]); s("m_r", max(dv.m, 1e-9)); s("z_d", dv.z)
    for i in range(3):
        s(f"st{i + 1}", dv.stroke[i]); s(f"Fm{i + 1}", dv.F_max[i])
    s("kc", dv.k_c); s("cc", dv.c_c); s("k_stop", 2.0e4); s("c_stop", 2.0 * math.sqrt(2.0e4 * max(dv.m, 1e-6)))
    s("k_lock", 2.0e4); s("c_lock", 2 * 0.7 * math.sqrt(2.0e4 * max(dv.m, 1e-6)))
    s("H", dv.H if dv.H > 0 else 1e-12); s("dmax", dv.delta_max); s("ratemax", dv.rate_max)
    s("cmg1", dv.axes[0]); s("cmg2", dv.axes[1]); s("tau_g", 1.0 / (2 * math.pi * 100.0)); s("tau_c", 0.5)
    s("stage_on", 1.0 if cfg.stage else 0.0); s("qlim", cfg.q_lim); s("qtap", cfg.q_taper); s("qstop", cfg.q_stop)
    s("ws", 2 * math.pi * cfg.stage_hz); s("zs", cfg.stage_zeta); s("sdec", round(1.0 / (cfg.stage_rate * dt)))
    s("slew", getattr(cfg, "stage_slew", 0.08)); s("atau", 0.05)
    s("lock_rot", 1.0 if cfg.lock_rotation else 0.0); s("m_pen", body.m)
    s("vc_on", 1.0 if cfg.voluntary else 0.0); s("vc_ki", 2 * math.pi * cfg.vc_hz); s("vc_delay", round(cfg.vc_delay / dt))
    info = {"model_version": MODEL_VERSION, "pen": body.summary(), "grip": g.summary(), "rotation_lever_m": lever,
            "N_nib0": N_nib0, "N_skid0": N_sk0}
    Pv = _pack_extensions(Pv, s, cfg, dt, t1, t2, info)
    return Pv, info, lever


def _pack_extensions(Pv, s, cfg: Config, dt, t1, t2, info):
    """Grip sleeve + actuated pivot, stage command source and in-loop controller (opt/inertial extension).  With the
    defaults (no sleeve, stage_src 0, no controller) nothing is written, so the parameter vector is the original one
    followed by zeros."""
    sl = getattr(cfg, "sleeve", None)
    if sl is not None:
        s("slv_on", 1.0)
        Sinv = np.linalg.inv(mass_matrix(sl, t1, t2))
        for i in range(5):
            for j in range(i, 5):
                s(f"Si{i}{j}", Sinv[i, j])
        s("zp", sl.z_p); s("kpt", sl.k_pt); s("kpa", sl.k_pa); s("kpr", sl.k_pr); s("bpv", sl.beta_p); s("za", sl.z_a)
        s("kas", sl.k_a); s("cas", sl.c_a); s("act_ty", {"vcm": 0, "piezo": 1}[sl.act]); s("astr", sl.stroke)
        s("afm", sl.F_max); s("apre1", sl.preload[0]); s("apre2", sl.preload[1])
        s("push_slv", 1.0 if sl.push_on_sleeve else 0.0); s("k_astop", sl.k_stop)
        info["sleeve"] = {"mass_g": sl.m * 1e3, "com_mm": sl.z_g * 1e3, "z_p_mm": sl.z_p * 1e3, "z_a_mm": sl.z_a * 1e3,
                          "act": sl.act, "label": sl.label}
    if getattr(cfg, "stage_src", 0):
        s("stg_src", cfg.stage_src)
    ctl = getattr(cfg, "ctl", None)
    if ctl is None:
        return Pv
    NI, NO, NYE = core.NY + core.NE + core.NU, core.NU + core.NEPS, core.NY + core.NE
    s("ctl_on", 1.0)
    s("cdec", max(1, round(ctl.get("Ts", 5e-4) / dt)))
    imu = ctl.get("imu", {})
    s("zib", imu.get("z_b", 0.100)); s("zis", imu.get("z_s", 0.050)); s("ilat", imu.get("lat_ticks", 3))
    s("acc_nd", imu.get("acc_nd", 60e-6 * 9.80665)); s("gyr_nd", imu.get("gyr_nd", math.radians(2.8e-3)))
    s("pos_nd", imu.get("pos_nd", 0.0)); s("iseed", imu.get("seed", 1)); s("iaa_hz", imu.get("aa_hz", 400.0))
    A = np.asarray(ctl.get("A", np.zeros((0, 0))), float)
    nx = A.shape[0]
    B = np.asarray(ctl.get("B", np.zeros((nx, NI))), float).reshape(nx, NI)
    C = np.asarray(ctl.get("C", np.zeros((NO, nx))), float).reshape(NO, nx)
    D = np.asarray(ctl.get("D", np.zeros((NO, NYE))), float).reshape(NO, NYE)
    blocks = []
    off = [len(Pv)]

    def put(name, arr):
        s(name, off[0])
        a_ = np.ascontiguousarray(np.asarray(arr, float).ravel())
        blocks.append(a_)
        off[0] += len(a_)

    s("c_nx", nx)
    put("c_oA", A); put("c_oB", B); put("c_oC", C); put("c_oD", D)
    nn = ctl.get("nn")
    if nn is not None:
        W1 = np.asarray(nn["W1"], float)
        s("nn_h", W1.shape[0])
        assert W1.shape[1] == nx + NYE, "MLP input must be [x; y; e]"
        put("nn_oW1", W1); put("nn_ob1", nn["b1"]); put("nn_oW2", np.asarray(nn["W2"], float).reshape(core.NU, W1.shape[0]))
        put("nn_ob2", nn["b2"])
    afc = ctl.get("afc")
    if afc is not None:
        tab = np.asarray(afc["table"], float)
        if tab.shape[1] == 8:                      # no per-frequency cap given
            tab = np.column_stack([tab, np.zeros(len(tab))])
        assert tab.ndim == 2 and tab.shape[1] == 9 and tab.shape[0] >= 2
        s("afc_on", 1.0); s("afc_mu", afc["mu"]); s("afc_leak", afc.get("leak", 0.0)); s("afc_nf", tab.shape[0])
        s("afc_f0", afc["f0"]); s("afc_df", afc["df"]); s("afc_o1", afc["out"][0]); s("afc_o2", afc["out"][1])
        s("afc_umax", afc.get("umax", 1.0))
        put("afc_ot", tab)
    for i, u in enumerate(ctl.get("ulim", [0.0] * core.NU)):
        s(f"ul{i + 1}", u)
    return np.concatenate([Pv] + blocks) if blocks else Pv


class Result:
    def __init__(self, rec, info, cfg, scn):
        self.rec = rec
        self.info = info
        self.cfg = cfg
        self.scn = scn

    def __getitem__(self, name):
        return self.rec[:, core.RIDX[name]]

    def xy(self, base):
        i = core.RIDX[base]
        return self.rec[:, i:i + 2]

    def ink(self):
        return self.rec[:, [core.RIDX["ix"], core.RIDX["iy"]]]

    def ball(self):
        return self.rec[:, [core.RIDX["bx"], core.RIDX["by"]]]


def run(scn, cfg: Config, uff=None, clean=None, dt=DT, rec_hz=REC_HZ) -> Result:
    n = len(scn.t)
    tremor = getattr(scn, "tremor_obj", None)
    Pv, info, lever = pack(cfg, n, dt, rec_hz, tremor)
    psi_disp = getattr(scn, "psi_disp", None)
    psi = np.zeros(n) if psi_disp is None else psi_disp / lever
    psid = np.gradient(psi, dt)
    if uff is None:
        uff = np.zeros((n, 3))
    elif uff.shape[0] != n:
        uff = upsample(uff, n)
    if clean is None:
        clean = np.zeros((n, 2))
    elif clean.shape[0] != n:
        clean = upsample(clean, n)
    nrec = int(math.ceil(n / Pv[core.IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, core.NREC))
    m = core.simulate(Pv, np.ascontiguousarray(scn.pref), np.ascontiguousarray(scn.vref), np.ascontiguousarray(scn.fpush),
                      np.ascontiguousarray(psi), np.ascontiguousarray(psid), np.ascontiguousarray(uff, dtype=np.float64),
                      np.ascontiguousarray(clean, dtype=np.float64), np.ascontiguousarray(scn.intended, dtype=np.float64), rec)
    return Result(rec[:m], info, cfg, scn)


def upsample(x, n):
    """Record-rate array (m, k) -> simulation rate (n, k) by linear interpolation on the index."""
    x = np.asarray(x, float)
    m = x.shape[0]
    src = np.linspace(0.0, 1.0, m)
    dst = np.linspace(0.0, 1.0, n)
    # the record starts at t = 0 with decimation d: sample j at step j*d -> map exactly
    return np.column_stack([np.interp(dst, src, x[:, j]) for j in range(x.shape[1])])


def clean_at_sim_rate(ref: Result, n: int, dt=DT):
    """Clean ball path of a reference run at the simulation rate (oracle reference, as model P1)."""
    t = np.arange(n) * dt
    b = ref.ball()
    return np.column_stack([np.interp(t, ref["t"], b[:, 0]), np.interp(t, ref["t"], b[:, 1])])


def uff_at_sim_rate(u_rec, t_rec, n, dt=DT):
    t = np.arange(n) * dt
    return np.column_stack([np.interp(t, t_rec, u_rec[:, j]) for j in range(u_rec.shape[1])])


# ------------------------------------------------------------------------------------------ oracle (ILC)
def device_inputs(cfg: Config):
    """Linear-model input names per page component: x <- inputs[0], y <- inputs[1] (with optional extra x input)."""
    dv = cfg.device
    if dv.kind == "rm":
        ins = {"x": ["F_t1"] + (["F_a"] if dv.stroke[2] > 0 else []), "y": ["F_t2"]}
        col = {"F_t1": 0, "F_t2": 1, "F_a": 2}
        lim = {"F_t1": dv.F_max[0], "F_t2": dv.F_max[1], "F_a": dv.F_max[2]}
        if dv.stroke[0] <= 0:
            ins["x"] = [i for i in ins["x"] if i != "F_t1"]
        if dv.stroke[1] <= 0:
            ins["y"] = []
    elif dv.kind == "cmg":
        ins = {"x": ["tau_t2"] if dv.axes[0] else [], "y": ["tau_t1"] if dv.axes[1] else []}
        col = {"tau_t2": 0, "tau_t1": 1}
        lim = {"tau_t2": 1.0, "tau_t1": 1.0}
    else:
        raise ValueError("oracle ILC only for rm and cmg devices")
    return ins, col, lim


def ilc_oracle(scn, cfg: Config, ref: Result, n_iter=6, band=(2.0, 20.0), gain=0.7, verbose=False, lin=None,
               margin=1.0, pct=95.0, stage_cfg: Optional[Config] = None):
    """Iterative-learning oracle feed-forward for a reaction mass or CMG with projection onto the feasible set.
    Each iteration: u <- P(u - gain * G^-1 e), where e is the ball's deviation from the clean path (band 2-20 Hz),
    G the frictionless linear model's response per unit input, and P scales each input channel so that the
    linear-model prediction of its force, stroke (reaction mass) or gimbal angle and rate (CMG), at percentile `pct`
    of the record, stays within `margin` of the device limits; the peaks above that are clipped by the core's own
    limits (force saturation, stroke stops, gimbal angle and rate limits).  Returns (Result of the last run, uff at record rate, history of the ball-deviation
    RMS).  If stage_cfg is given, a final run with the nib stage uses the learned input."""
    n = len(scn.t)
    clean_sim = clean_at_sim_rate(ref, n)
    lin = lin or L.LinearModel(cfg, paper="free")
    dv = cfg.device
    ins, col, lim = device_inputs(cfg)
    res = run(scn, cfg, uff=None, clean=clean_sim)
    t = res["t"]
    fs = 1.0 / (t[1] - t[0])
    m = len(t)
    freqs = np.fft.rfftfreq(m, 1.0 / fs)
    sel = np.where((freqs >= band[0]) & (freqs <= band[1]))[0]
    fb = freqs[sel]
    wb = 2 * np.pi * fb
    names = sum(ins.values(), [])
    gains, strokes = {}, {}
    for name in names:
        u = lin.input_vector(name).astype(complex)
        X = lin.frf(fb, lambda w: u)
        gains[name] = X[:, 0:2]
        if dv.kind == "rm":
            strokes[name] = X[:, 8 + col[name]]
    win = np.ones(len(sel))
    lo = fb < band[0] + 1.0
    hi = fb > band[1] - 2.0
    win[lo] = 0.5 - 0.5 * np.cos(np.pi * (fb[lo] - band[0]) / 1.0)
    win[hi] = 0.5 + 0.5 * np.cos(np.pi * (fb[hi] - (band[1] - 2.0)) / 2.0)
    U = np.zeros((len(freqs), 3), complex)
    hist = []
    ref_ball = ref.ball()
    k = min(len(t), len(ref["t"]))

    def deviation(r_):
        e_ = np.zeros((m, 2))
        kk = min(k, len(r_["t"]))
        e_[:kk] = r_.ball()[:kk] - ref_ball[:kk]
        return e_ - e_.mean(axis=0)

    def project(U_):
        U_ = U_.copy()
        def pk(x):
            return max(np.percentile(np.abs(x), pct), 1e-12)
        for name in names:
            c = col[name]
            u_t = np.fft.irfft(U_[:, c], n=m)
            scale = 1.0
            if dv.kind == "rm":
                Fm = dv.F_max[c]
                xm = dv.stroke[c]
                if Fm > 0:
                    scale = min(scale, margin * Fm / pk(u_t))
                Rw = np.zeros(len(freqs), complex)
                Rw[sel] = strokes[name] * U_[sel, c]
                r_t = np.fft.irfft(Rw, n=m)
                if xm > 0:
                    scale = min(scale, margin * xm / pk(r_t))
            else:
                H2 = 2 * dv.H
                rate = u_t / H2
                Aw = np.zeros(len(freqs), complex)
                Aw[sel] = U_[sel, c] / (H2 * 1j * wb)
                ang = np.fft.irfft(Aw, n=m)
                scale = min(scale, margin * dv.rate_max / pk(rate), margin * dv.delta_max / pk(ang))
            if scale < 1.0:
                U_[:, c] *= scale
        return U_

    e = deviation(res)
    for it in range(n_iter):
        hist.append(float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))))
        if verbose:
            print(f"  ILC it {it}: ball deviation rms {hist[-1] * 1e6:.1f} um")
        E = np.fft.rfft(e, axis=0)
        for comp, key in ((0, "x"), (1, "y")):
            nm_ = ins[key]
            if not nm_:
                continue
            gs = [gains[nm][:, comp] for nm in nm_]
            wts = [max(lim[nm], 1e-9) ** 2 for nm in nm_]
            den = sum(w_ * np.abs(g_) ** 2 for w_, g_ in zip(wts, gs)) + 1e-30
            target = -gain * win * E[sel, comp]
            for nm, g_, w_ in zip(nm_, gs, wts):
                U[sel, col[nm]] += w_ * np.conj(g_) * target / den
        U = project(U)
        u_rec = np.fft.irfft(U, n=m, axis=0)
        res = run(scn, cfg, uff=uff_at_sim_rate(u_rec, t, n), clean=clean_sim)
        e = deviation(res)
    hist.append(float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))))
    if verbose:
        print(f"  ILC final: ball deviation rms {hist[-1] * 1e6:.1f} um")
    u_rec = np.fft.irfft(U, n=m, axis=0)
    if stage_cfg is not None:
        res = run(scn, stage_cfg, uff=uff_at_sim_rate(u_rec, t, n), clean=clean_sim)
    return res, u_rec, hist


def with_stage(cfg: Config, **kw):
    return replace(cfg, stage=True, **kw)
