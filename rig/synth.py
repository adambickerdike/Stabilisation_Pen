"""Synthetic data for every rig analysis (SIMULATION, method checks only).

Each generator returns the data an analysis would receive from a rig record, plus the hidden
truth under the key "_truth" so the self-test can score recovery. Instrument effects use the
measurement models of s2r.instruments (noise, quantisation, sensor bandwidth, session gain and
offset) with channels defined here for the rig's instruments; every channel lists its origin.
Nothing produced here is a measurement, and none of it is evidence about a pen, an ink or a paper.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from s2r import instruments as ins

from . import protocol, sync
from .contact import basis

# ----------------------------------------------------------------------------- channels
AXIAL_CELL = ins.Channel(
    "rig_axial_cell", "N", fs=1000.0, noise_rms=0.12e-3, lsb=0.0, gain_bound=0.0, bw_hz=300.0, bw_order=2,
    src={"noise_rms": "CALC: 0.77 uV RMS at 1 kSPS, gain 128 (MFR AMF-221) over 6.6 mV full scale x 1 N",
         "bw_hz": "MFR AMF-225 (LSB200 100 g natural frequency 300 Hz, unloaded)"})
PLATE = ins.Channel(
    "rig_plate", "N", fs=1000.0, noise_rms=0.4e-3, lsb=0.0, gain_bound=0.0, bw_hz=250.0, bw_order=2,
    src={"noise_rms": "ASSUMPTION (K3D40 +-2 N bridge on the ADS131M08 at gain 128)",
         "bw_hz": "CALC (0.1 mm rated displacement at 2 N gives 2e4 N/m; with a 20 g platen about 160 Hz; "
                  "250 Hz used for the anti-alias chain)"})
ENCODER_LM13 = ins.Channel(
    "rig_lm13", "m", fs=1000.0, noise_rms=0.0, lsb=0.244e-6,
    src={"lsb": "MFR OPT-89 (LM13 resolution option 13B, about 0.244 um)"})


def _meas(ch, t, x, rng):
    return ins.measure(ch, t, x, rng, fs=1.0 / (t[1] - t[0]), t_start=t[0], t_stop=t[-1])[1]


# ----------------------------------------------------------------------------- G1 tribometer
def stroke(theta_deg=50.0, beta_deg=0.0, v_mm_s=30.0, Fc_N=0.15, mu_k=0.15, mu_s_ratio=1.3, v_s_mm_s=2.0,
           friction_angle_deg=3.0, ripple=0.08, L_mm=20.0, fs=1000.0, k_guide=40.0, s_free=-0.5e-3, rng=None,
           plate_matrix=None) -> Dict:
    """One constant-speed stroke of the R9 head with phi_h = 0 (h = +x)."""
    rng = rng or np.random.default_rng(0)
    th = np.radians(theta_deg)
    b = np.radians(beta_deg)
    v = v_mm_s * 1e-3
    T = L_mm * 1e-3 / v + 0.4
    t = np.arange(0, T, 1 / fs)
    h, t2 = basis(0.0)
    dirv = np.cos(b) * h + np.sin(b) * t2
    # speed profile: 0.2 s ramps
    s_prof = np.clip(t / 0.2, 0, 1) * np.clip((T - t) / 0.2, 0, 1)
    sp = v * s_prof
    s = np.cumsum(sp) / fs
    xy = s[:, None] * dirv[None, :]
    mu = mu_k * (1 + (mu_s_ratio - 1) * np.exp(-(sp / (v_s_mm_s * 1e-3)) ** 2))
    # friction ripple: band-limited 3-15 Hz noise (a friction nuisance, relative to mu)
    from scipy import signal as sps
    sos = sps.butter(2, [3, 15], btype="band", fs=fs, output="sos")
    rp = sps.sosfilt(sos, rng.standard_normal(len(t)))
    rp *= ripple / (rp.std() + 1e-12)
    mu = mu * (1 + rp)
    N = Fc_N / (np.sin(th) - mu * np.cos(b) * np.cos(th))
    delta = np.radians(friction_angle_deg)
    rot = np.array([[np.cos(delta), -np.sin(delta)], [np.sin(delta), np.cos(delta)]])
    fdir = -(rot @ dirv)
    f = (mu * N)[:, None] * fdir[None, :]
    f[sp < 1e-6] = 0.0
    # true page-frame force ON the plate
    Fp = np.column_stack([-f[:, 0], -f[:, 1], -N])
    # axial chain: slide wanders with paper height (+-0.2 mm) -> guide force in the cell
    slide = 0.2e-3 * np.sin(2 * np.pi * 0.3 * t) + 0.1e-3
    F_axial_contact = N * np.sin(th) + (f @ h) * np.cos(th)
    cell = F_axial_contact + k_guide * (slide - s_free)     # the guide pushes back from its rest position
    M = np.eye(3) if plate_matrix is None else np.asarray(plate_matrix)
    raw = np.linalg.solve(M, Fp.T).T                      # what the bridges read (volts-equivalent in N)
    raw_m = np.column_stack([_meas(PLATE, t, raw[:, k], rng) for k in range(3)])
    cell_m = _meas(AXIAL_CELL, t, cell, rng)
    xy_m = np.column_stack([_meas(ENCODER_LM13, t, xy[:, k], rng) for k in range(2)])
    slide_m = slide + 0.5e-6 * rng.standard_normal(len(t))
    return {"t": t, "cell": cell_m, "slide": slide_m, "raw": raw_m, "xy": xy_m, "theta": th, "phi_h": 0.0,
            "_truth": {"mu_k": mu_k, "Fc": Fc_N, "friction_angle_deg": friction_angle_deg,
                       "R_perp_over_Fc": float(np.mean(np.hypot(-N * np.cos(th) + (f @ h) * np.sin(th), f @ t2)[
                           (sp > 0.9 * v)]) / Fc_N)}}


def plate_calibration(M_true=None, rng=None, n_pos=9, loads=(0.1, 0.5, 1.0, 1.5)) -> Dict:
    """Dead weights (downward) at n_pos positions and horizontal pulls (thread over a pulley)."""
    rng = rng or np.random.default_rng(1)
    M = np.eye(3) if M_true is None else np.asarray(M_true)
    F, pos = [], []
    for ix in np.linspace(-20, 20, 3):
        for iy in np.linspace(-20, 20, 3):
            for L in loads:
                F.append([0.0, 0.0, -L])
                pos.append([ix, iy])
    for L in loads:
        for d in ([1, 0], [-1, 0], [0, 1], [0, -1]):
            F.append([L * d[0], L * d[1], -0.2])        # pull with a small dead weight holding the hook
            pos.append([0.0, 0.0])
    F = np.array(F)
    raw = np.linalg.solve(M, F.T).T + 0.4e-3 * rng.standard_normal(F.shape)
    return {"F": F, "raw": raw, "pos": np.array(pos)}


def guide_calibration(k_guide=40.0, s_free=-0.5e-3, rng=None) -> Dict:
    """Refill off the paper: the cell reads the guide force k_g (s - s_free) as the voice coil
    moves the holder through the slide range."""
    rng = rng or np.random.default_rng(2)
    s = np.linspace(-0.5e-3, 0.5e-3, 21)
    f = k_guide * (s - s_free) + 0.1e-3 * rng.standard_normal(len(s))
    return {"slide": s, "force": f}


# ----------------------------------------------------------------------------- G1 ink
def ink_line(F_hi=0.30, F_lo=0.02, F_g=0.09, s_log=0.012, L_mm=100.0, dpi=1200, width_um=350.0,
             mean_gap_um=120.0, step_um=20.0, rng=None) -> Dict:
    """Synthetic scan of a force-ramp line. The ink leaves gaps as a two-state Markov chain whose
    stationary gap fraction is g(F) = 1 / (1 + exp((F - F_g) / s_log)); the continuity limit
    (gap fraction 1 %) is then F_1 = F_g + s_log * ln(99)."""
    rng = rng or np.random.default_rng(3)
    px_um = 25400.0 / dpi
    n = int(L_mm * 1000 / step_um) + 1
    s = np.linspace(0, L_mm * 1000, n)
    F = F_hi + (F_lo - F_hi) * s / s[-1]
    g = 1 / (1 + np.exp((F - F_g) / s_log))
    b = step_um / mean_gap_um                          # gap -> ink per step
    a = np.clip(b * g / np.maximum(1 - g, 1e-9), 0, 1)  # ink -> gap per step
    ink = np.ones(n, bool)
    for k in range(1, n):
        ink[k] = (rng.random() >= a[k]) if ink[k - 1] else (rng.random() < b)
    # render: horizontal line at the image centre
    H = int(2000 / px_um)
    W = int(L_mm * 1000 / px_um) + 40
    rr = np.arange(H)[:, None]
    cc = np.arange(W)[None, :]
    c0 = 20
    s_px = (cc - c0) * px_um
    ink_px = np.interp(s_px.ravel(), s, ink.astype(float)).reshape(1, W) > 0.5
    ink_px &= (s_px >= 0) & (s_px <= s[-1])
    prof = np.exp(-0.5 * ((rr - H / 2) * px_um / (width_um / 2.5)) ** 2)
    img = 235 - 170 * prof * ink_px + 4 * rng.standard_normal((H, W))       # paper texture as noise
    F1 = F_g + s_log * np.log(99.0)
    return {"img": img, "p0": (H / 2, c0), "p1": (H / 2, c0 + L_mm * 1000 / px_um), "px_um": px_um,
            "force_of_s": lambda su: np.interp(su, s, F), "_truth": {"F_1pct": float(F1), "F_g": F_g}}


# ----------------------------------------------------------------------------- G2 coupon
def coupon_map(K0=1.04, ripple=0.08, cross=0.03, k_neg=0.6, R_ohm=2.47, n=7, span_mm=1.0, rng=None,
               currents=(-0.6, -0.3, -0.1, 0.1, 0.3, 0.6), noise_N=2e-3) -> Dict:
    """Force map over an n x n grid of magnet positions. K_f(x,y) falls quadratically to the corners
    by `ripple`; the zero-current force has a lateral negative stiffness k_neg (N/mm)."""
    rng = rng or np.random.default_rng(4)
    xs = np.linspace(-span_mm, span_mm, n)
    nodes, I_list, F_list, Kt = [], [], [], []
    for x in xs:
        for y in xs:
            r2 = (x * x + y * y) / (2 * span_mm ** 2)
            Kx = K0 * (1 - ripple * r2)
            Kc = cross * K0 * x / span_mm
            I = np.array(currents * 2)                # two passes in reversal order
            drift = 0.5e-3 * np.linspace(-1, 1, len(I))
            F = np.column_stack([Kx * I + k_neg * x + drift, Kc * I + k_neg * y, -16.5 + 0 * I])
            F = F + noise_N * rng.standard_normal(F.shape)
            nodes.append([x, y])
            I_list.append(I)
            F_list.append(F)
            Kt.append(Kx)
    return {"nodes": np.array(nodes), "I": I_list, "F": F_list, "R_ohm": R_ohm,
            "model_Kf": np.array(Kt) * (1 + 0.03 * rng.standard_normal(len(Kt))),
            "_truth": {"Kf": np.array(Kt), "Km_centre": K0 / np.sqrt(R_ohm), "ripple": ripple,
                       "k_neg": k_neg}}


def attraction(gaps=np.linspace(0.6, 1.2, 13), A=6.0, g0=0.3, n=2.2, noise=0.02, rng=None) -> Dict:
    rng = rng or np.random.default_rng(5)
    F = A / (gaps + g0) ** n
    return {"gap": gaps, "F": F * (1 + noise * rng.standard_normal(len(gaps))), "_truth": {"A": A, "g0": g0, "n": n}}


def hall(I=np.linspace(-1.5, 1.5, 31), um_per_A=6.0, quad=0.4, noise_um=0.5, rng=None) -> Dict:
    rng = rng or np.random.default_rng(6)
    y = um_per_A * I + quad * I * I + noise_um * rng.standard_normal(len(I))
    return {"I": I, "reading_um": y, "_truth": {"um_per_A": um_per_A}}


def mode(fn=420.0, zeta=0.03, gain_per_A=None, tau=60e-6, f=np.geomspace(50, 2000, 200), noise=0.01, rng=None) -> Dict:
    rng = rng or np.random.default_rng(7)
    a = (2 * np.pi * fn) ** 2 * 1e-4 if gain_per_A is None else gain_per_A
    w = 2 * np.pi * f
    H = a * np.exp(-1j * w * tau) / ((2 * np.pi * fn) ** 2 - w ** 2 + 2j * zeta * 2 * np.pi * fn * w)
    H = H * (1 + noise * (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))))
    return {"f": f, "H": H, "_truth": {"fn": fn, "zeta": zeta}}


# ----------------------------------------------------------------------------- G3 nib
def nib_run(x_dist: np.ndarray, fs: float, fn=60.0, zeta=0.6, tau=2.5e-3, noise_um=1.0, locked=False,
            rng=None) -> Dict:
    """One-axis loaded nib: the housing moves by x_dist; the nib subtracts a delayed, servo-filtered
    copy of it (oracle estimator). Ink = housing + correction. Returns the housing encoder record,
    the ink (camera or scan) record and the command."""
    from scipy import signal as sps
    rng = rng or np.random.default_rng(8)
    w = 2 * np.pi * fn
    sysd = sps.cont2discrete(([w * w], [1, 2 * zeta * w, w * w]), 1 / fs, method="bilinear")
    b, a = np.squeeze(sysd[0]), sysd[1]
    d = int(round(tau * fs))
    ref = np.concatenate([np.zeros(d), x_dist[:-d]]) if d > 0 else x_dist.copy()
    q = np.zeros_like(x_dist) if locked else -sps.lfilter(b, a, ref)
    ink = x_dist + q
    enc = x_dist + 0.3e-6 * rng.standard_normal(len(x_dist))
    ink_m = ink + noise_um * 1e-6 * rng.standard_normal(len(x_dist))
    Tf = lambda f: 1 - (w * w / (w * w - (2 * np.pi * f) ** 2 + 2j * zeta * w * 2 * np.pi * f)) * np.exp(
        -2j * np.pi * f * d / fs)
    return {"housing": enc, "ink": ink_m, "q": q, "_truth": {"T_of_f": Tf, "fn": fn, "zeta": zeta, "tau": d / fs}}


# ----------------------------------------------------------------------------- page sensor
def page_run(duration=6.0, fs_truth=5000.0, fs_sensor=1000.0, latency_s=1.6e-3, noise_um=3.0, um_per_count=7.9375,
             scale=(1.02, 0.99), rotation_deg=4.0, tremor_mm=0.5, tremor_hz=8.0, drop_rate_hz=0.5, rng=None,
             truth="lm13") -> Dict:
    """A writing-like path with tremor, seen by a page sensor (latency, per-sample noise, count
    quantisation, scale and rotation errors, dropouts) and by the ground truth."""
    from stabpen import signals
    rng = rng or np.random.default_rng(9)
    dt = 1 / fs_truth
    it = signals.lognormal_handwriting(dt, duration, rng, letter_height=4e-3)
    xy = it.xy - it.xy[0]
    tt = it.t
    tr = signals.tremor(tt, signals.TremorSpec(f0=tremor_hz, amp_pk=tremor_mm * 1e-3, ellipticity=0.5), rng)
    g = (xy + tr) * 1e6                                # um, true pen motion over the page
    # sensor sees motion with latency, scale/rotation error, noise; reports increments in counts
    ts = np.arange(0.05, duration - 0.05, 1 / fs_sensor)
    th = np.radians(rotation_deg)
    Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]) @ np.diag(scale)
    gs = np.column_stack([np.interp(ts - latency_s, tt, g[:, k]) for k in range(2)]) @ Rm.T
    gs = gs + noise_um * rng.standard_normal(gs.shape)
    counts = np.round(gs / um_per_count)
    dxy = np.diff(counts, axis=0, prepend=counts[:1])
    valid = np.ones(len(ts), bool)
    nd = rng.poisson(drop_rate_hz * duration)
    for t0 in rng.uniform(0.5, duration - 0.5, nd):
        m = (ts >= t0) & (ts < t0 + rng.uniform(0.005, 0.03))
        valid[m] = False
        dxy[m] = 0
    if truth == "lm13":
        tg = tt
        gt = np.round(g / 0.244) * 0.244
    elif truth == "camera":
        tg = np.arange(0, duration, 0.01)
        gt = np.column_stack([np.interp(tg, tt, g[:, k]) for k in range(2)]) + 1.5 * rng.standard_normal((len(tg), 2))
    else:
        tg, gt = tt, g.copy()
    Ainv = np.linalg.inv(Rm)
    return {"t_truth": tg, "g_xy": gt, "t_sens": ts, "dx": dxy[:, 0], "dy": dxy[:, 1], "valid": valid,
            "um_per_count": um_per_count,
            "_truth": {"latency_s": latency_s, "noise_um": noise_um, "A_inv": Ainv, "scale": scale,
                       "rotation_deg": rotation_deg}}


# ----------------------------------------------------------------------------- thermal
def thermal_run(C1=0.6, C2=6.0, R12=35.0, R2a=55.0, Ta=30.0, duration=1800.0, dt=2.0, noise_K=0.15, rng=None,
                cap_W=0.39, T_limit=110.0) -> Dict:
    """30 min of writing-duty coil power with a simple governor (power capped when the coil,
    estimated from its resistance, passes T_limit)."""
    from .thermal import simulate_2node
    rng = rng or np.random.default_rng(10)
    t = np.arange(0, duration, dt)
    P = 0.18 + 0.12 * (np.sin(2 * np.pi * t / 240) > 0.3) + 0.05 * rng.random(len(t))
    P = np.minimum(P, cap_W)
    T1, T2 = simulate_2node(t, P, Ta, C1, C2, R12, R2a, Ta, Ta)
    return {"t": t, "P": P, "Ta": Ta, "T_coil": T1 + noise_K * rng.standard_normal(len(t)),
            "T_web": T2 + 0.1 * rng.standard_normal(len(t)),
            "_truth": {"C1": C1, "C2": C2, "R12": R12, "R2a": R2a}}


# ----------------------------------------------------------------------------- G5
def collar_errors(n_seeds=10, base_um=300.0, r_locked=0.05, r_active=0.20, r_passive=0.03, sd=0.06,
                  grips=("light_2N", "medium_4N", "firm_8N"), grip_scale=(1.0, 0.75, 0.4), rng=None) -> Dict:
    """Per-seed ink errors for the four G5 conditions at three grip strengths. Effects are
    ASSUMPTIONS of the synthetic test, not predictions."""
    rng = rng or np.random.default_rng(11)
    out = {}
    for g, sc in zip(grips, grip_scale):
        e0 = base_um * (1 + sd * rng.standard_normal(n_seeds))
        noise = lambda: 1 + 0.03 * rng.standard_normal(n_seeds)
        out[g] = {"none": e0 * noise(), "locked": e0 * (1 - r_locked * sc) * noise(),
                  "passive": e0 * (1 - r_passive * sc) * noise(),
                  "active": e0 * (1 - r_active * sc) * noise()}
    return out


# ----------------------------------------------------------------------------- sync and stream
def sync_edges(duration_s=600.0, offset_s=0.1234, drift_ppm=20.0, jitter_s=2e-6, rng=None) -> Dict:
    """Rig pulses on the DAQ clock and their edges on a device clock with offset, drift, jitter."""
    rng = rng or np.random.default_rng(12)
    k = np.arange(int(duration_s))
    n = k % 256
    t_rise = k * sync.PERIOD_S + 0.5
    t_fall = t_rise + np.array([sync.width_for(v) for v in n])
    to_dev = lambda tq: (tq - offset_s) / (1 + drift_ppm * 1e-6)
    return {"daq_rise": t_rise, "daq_fall": t_fall,
            "dev_rise": to_dev(t_rise) + jitter_s * rng.standard_normal(len(k)),
            "dev_fall": to_dev(t_fall) + jitter_s * rng.standard_normal(len(k)),
            "_truth": {"offset_s": offset_s, "drift_ppm": drift_ppm}}


def daq_stream(n=2000, f_cpu=600e6, rate=4000.0, corrupt_every=97, rng=None) -> Dict:
    """A byte stream as the firmware would send it, with occasional corrupted bytes and a
    dropped frame, for the logger and parser tests."""
    rng = rng or np.random.default_rng(13)
    out = bytearray(protocol.pack_text(f"f_cpu={int(f_cpu)};adc_rate={rate:g};gain=128,128,128,128,1,1,1,1",
                                       protocol.T_CONFIG))
    truth = []
    for k in range(n):
        if k == 500:
            continue                          # a dropped frame
        t = int(k * f_cpu / rate)
        adc = rng.integers(-2 ** 23, 2 ** 23, 8)
        enc = [k, -k, 2 * k, 0]
        fr = bytearray(protocol.pack_sample(k, t, adc, enc, cmd=k % 100, flags=k & 1))
        if corrupt_every and k % corrupt_every == 13:
            fr[10] ^= 0xFF                    # corrupt one payload byte -> CRC error
        else:
            truth.append(k)
        out += fr
        if k % 1000 == 0:
            out += protocol.pack_event(k, t, protocol.EV_SYNC_OUT_RISE, k // 1000)
    return {"bytes": bytes(out), "_truth": {"good_seq": truth}}


# ----------------------------------------------------------------------------- tablet
def tablet_loops(duration=12.0, fs=200.0, tremor_mm_pk=0.4, tremor_hz=6.0, loop_hz=2.2, rng=None, jitter_ms=0.8):
    """Continuous pen-down cursive-loop task with a sinusoidal tremor along 30 deg (peak tremor_mm_pk),
    sampled like a tablet (jittered times, 0.01 mm resolution)."""
    rng = rng or np.random.default_rng(14)
    t = np.cumsum(np.full(int(duration * fs), 1 / fs) + jitter_ms * 1e-3 * rng.standard_normal(int(duration * fs)) / 3)
    ph = 2 * np.pi * loop_hz * t
    x = 6.0 * t + 2.0 * np.sin(ph)
    y = 4.0 * (1 - np.cos(ph)) / 2
    ang = np.radians(30)
    ft = tremor_hz + 0.1 * np.sin(2 * np.pi * 0.2 * t)
    tr = tremor_mm_pk * np.sin(2 * np.pi * np.cumsum(ft * np.gradient(t)))
    xy_clean = np.column_stack([x, y])
    xy = xy_clean + np.column_stack([tr * np.cos(ang), tr * np.sin(ang)])
    q = lambda a: np.round(a / 0.01) * 0.01
    return {"t": t, "xy": q(xy), "xy_clean": q(xy_clean), "pen_down": np.ones(len(t), bool),
            "_truth": {"A_pp_major_mm": 2 * tremor_mm_pk, "f_hz": tremor_hz}}
