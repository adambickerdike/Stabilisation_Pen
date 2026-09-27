#!/usr/bin/env python3
"""Generate golden test vectors for the firmware host/QEMU unit tests.

Every vector file is produced by the project's Python/numba reference code,
never by the firmware itself:

  kf_step.vec          sim.pensim.core._kf_step (numba, float64) on states
                       sampled from a realistic estimator run
  kf_seq_bal.vec       estimator wrapper (reinit, NIS, frequency tracking,
  kf_seq_asr.vec       gate, horizon prediction): the `mode == 3` block of
                       core.simulate() transcribed line by line below
                       (ref_kf_estimator), calling core._kf_step
  bpf_seq.vec          `mode == 2` block transcribed, calling core._biquad
  replay_kf.vec        the REAL core.simulate() closed-loop run; the
  replay_bpf.vec       controller inputs are reconstructed exactly from the
  replay_ffc.vec       recording (noise-free sensors, Hall delay 0.5 ms,
                       optical delay = IMU delay = 1 ms so that the fused
                       position equals the delayed optical sample, IMU
                       feedforward off, 20 V bus so the current loop never
                       clamps); outputs dhat, west, g_eff, qr, iref are the
                       simulator's own records
  biquad.vec           scipy.signal.sosfilt with the coefficients of
                       model.build_params (contact-FF 60 Hz Butterworth,
                       band-pass sections)
  jacobian.vec         stabpen.frames (jacobian, inverse_jacobian, and a
                       numeric 3-D construction generalised to gamma)
  crc16.vec            binascii.crc_hqx(data, 0xFFFF) = CRC-16/CCITT-FALSE

File format "PENVEC01": magic | n_rows u32 | n_cols u32 | 32-byte column
names | float32 little-endian row-major data. A JSON sidecar (<file>.json)
records the columns, the provenance and the SHA-256 of the data.
Evidence status: SIMULATION / reference computations (no hardware data).

Run: python3 firmware/tools/gen_vectors.py   (or make -C firmware vectors)
"""
from __future__ import annotations

import binascii
import hashlib
import json
import math
import os
import struct
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)
ROOT = os.path.dirname(FW)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(FW, "build", "numba_cache"))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from scipy import signal as sps  # noqa: E402

from sim.pensim import core, model, scenarios  # noqa: E402
from sim.pensim.layout import IDX, MODES, RIDX  # noqa: E402
from stabpen import frames  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(FW, "tests", "vectors")
SEL = os.path.join(ROOT, "results", "sim", "estimator_selection.json")


def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def write_vec(name, cols, meta):
    names = list(cols.keys())
    rows = len(next(iter(cols.values())))
    for n in names:
        if len(n) >= 32:
            raise ValueError(n)
        if len(cols[n]) != rows:
            raise ValueError(f"column {n} length")
    data = np.column_stack([np.asarray(cols[n], dtype=np.float64) for n in names]).astype("<f4")
    if not np.all(np.isfinite(data)):
        raise ValueError(f"{name}: non-finite data")
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(b"PENVEC01")
        f.write(struct.pack("<II", rows, len(names)))
        for n in names:
            f.write(n.encode("ascii").ljust(32, b"\0"))
        f.write(data.tobytes())
    side = {"file": name, "rows": rows, "columns": names, "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
            "evidence_status": "reference computation / simulation (no hardware)", **meta}
    with open(path + ".json", "w") as f:
        json.dump(side, f, indent=1)
        f.write("\n")
    print(f"  {name}: {rows} rows x {len(names)} cols")


def nominal(theta_deg=50.0):
    dt = 25e-6
    t = np.arange(4) * dt
    z2 = np.zeros((4, 2))
    return model.Scenario(t=t, pref=np.zeros((4, 3)), vref=np.zeros((4, 3)), fpush=np.zeros(4), dtrue=z2,
                          intended=z2.copy(), opt_ok=np.ones(4, np.uint8), theta_deg=theta_deg, N0=1.0)


def frozen():
    sel = json.load(open(SEL))["results"]
    return {"bal": sel["kfosc"]["selected"]["params"], "asr": sel["kfosc"]["selected_assertive"]["params"],
            "bpf": sel["bpf"]["selected"]["params"], "bpf_asr": sel["bpf"]["selected_assertive"]["params"]}


def params_for(profile):
    fz = frozen()
    if profile == "asr":
        ctrl = model.Controller(mode="kfosc", **fz["asr"], **fz["bpf_asr"])
    else:
        ctrl = model.Controller(mode="kfosc", **fz["bal"], **fz["bpf"])
    P, info = model.build_params(nominal(), ctrl)
    return P, info


# ---------------------------------------------------------------------------- reference estimators
def ref_kf_estimator(ph, valid, P, capture=None):
    """Transcription of core.simulate() `mode == 3` (estimator part).
    The optical 0->1 transition sets need_reinit (sensor-sampling block of
    simulate()); a tick with invalid optics sets need_reinit as well."""
    Ts = P[IDX["dt"]] * P[IDX["stage_decim"]]
    wkf = P[IDX["kf_w0"]]; rdamp = P[IDX["kf_rdamp"]]; qj = P[IDX["kf_qj"]]; qt = P[IDX["kf_qt"]]; kr = P[IDX["kf_r"]]
    wg = P[IDX["kf_wgain"]]; wmin = P[IDX["kf_wmin"]]; wmax = P[IDX["kf_wmax"]]; nishi = P[IDX["conf_nis_hi"]]
    hor = P[IDX["horizon"]]; fgate = P[IDX["f_gate"]]; fgw = P[IDX["f_gate_width"]]
    xk = np.zeros((2, 5)); Pk = np.zeros((2, 5, 5))
    for ax in range(2):
        for i in range(5):
            Pk[ax, i, i] = 1e-6
    kf_init = 0; phase_prev = 0.0; nis_f = 1.0; need_reinit = 1
    dhat = np.zeros(2); conf = 0.0; conf_nis = 0.0; gate = 1.0
    n = len(valid)
    out = {k: np.zeros(n) for k in ("dhat0", "dhat1", "w", "conf_nis", "gate", "conf", "nis_f", "updated")}
    vprev = False
    for m in range(n):
        v = bool(valid[m])
        if v and not vprev:
            need_reinit = 1
        vprev = v
        upd = 0.0
        if v:
            if need_reinit == 1:
                for ax in range(2):
                    for i in range(5):
                        xk[ax, i] = 0.0
                        for j in range(5):
                            Pk[ax, i, j] = 0.0
                    xk[ax, 0] = ph[m, 0] if ax == 0 else ph[m, 1]
                    Pk[ax, 0, 0] = 1e-8; Pk[ax, 1, 1] = 1e-4; Pk[ax, 2, 2] = 1e-2
                    Pk[ax, 3, 3] = 1e-7; Pk[ax, 4, 4] = 1e-7
                need_reinit = 0
            nis_sum = 0.0
            for ax in range(2):
                yv = ph[m, 0] if ax == 0 else ph[m, 1]
                if capture is not None and m in capture:
                    capture[m].append((xk[ax].copy(), Pk[ax].copy(), yv, wkf))
                innov, S = core._kf_step(xk[ax], Pk[ax], yv, Ts, wkf, rdamp, qj, qt, kr)
                nis_sum += innov * innov / S
            nis_f = nis_f + 0.01 * (0.5 * nis_sum - nis_f)
            amp0 = math.hypot(xk[0, 3], xk[0, 4]); amp1 = math.hypot(xk[1, 3], xk[1, 4])
            axm = 0 if amp0 >= amp1 else 1
            ampm = amp0 if axm == 0 else amp1
            phs = math.atan2(xk[axm, 4], xk[axm, 3])
            if kf_init == 1 and ampm > 2e-5:
                dph = phs - phase_prev
                while dph > math.pi:
                    dph -= 2 * math.pi
                while dph < -math.pi:
                    dph += 2 * math.pi
                wm = -dph / Ts
                wkf = wkf + wg * (wm - wkf)
                wkf = min(max(wkf, wmin), wmax)
            phase_prev = phs
            kf_init = 1
            ch = math.cos(wkf * hor); sh = math.sin(wkf * hor)
            rh = rdamp ** (hor / Ts)
            dhat[0] = rh * (ch * xk[0, 3] + sh * xk[0, 4])
            dhat[1] = rh * (ch * xk[1, 3] + sh * xk[1, 4])
            conf_nis = min(1.0, max(0.0, 1.0 - (nis_f - 1.0) / max(nishi - 1.0, 1e-6)))
            conf = conf_nis
            gate = 1.0
            f_tr = wkf / (2.0 * math.pi)
            if fgate > 0.0:
                gate = min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-6)))
                conf = conf * gate
            upd = 1.0
        else:
            need_reinit = 1
        out["dhat0"][m] = dhat[0]; out["dhat1"][m] = dhat[1]; out["w"][m] = wkf
        out["conf_nis"][m] = conf_nis; out["gate"][m] = gate; out["conf"][m] = conf; out["nis_f"][m] = nis_f
        out["updated"][m] = upd
    return out


def ref_bpf_estimator(ph, valid, P):
    """Transcription of core.simulate() `mode == 2`, calling core._biquad."""
    Ts = P[IDX["dt"]] * P[IDX["stage_decim"]]
    bp1 = P[IDX["bp1_b0"]:IDX["bp1_b0"] + 5]; bp2 = P[IDX["bp2_b0"]:IDX["bp2_b0"] + 5]
    bpg = P[IDX["bp_gain_comp"]]; hor = P[IDX["horizon"]]
    bst = np.zeros((2, 4)); ybp_prev = np.zeros(2); ybpd = np.zeros(2)
    need_reinit = 1; vprev = False
    n = len(valid)
    d0 = np.zeros(n); d1 = np.zeros(n)
    for m in range(n):
        v = bool(valid[m])
        if v and not vprev:
            need_reinit = 1
        vprev = v
        if need_reinit == 1 and v:
            bst[:, :] = 0.0
            need_reinit = 0
        yb = np.zeros(2)
        for ax in range(2):
            s1 = bst[ax, 0:2].copy(); s2 = bst[ax, 2:4].copy()
            y1 = core._biquad(bp1[0], bp1[1], bp1[2], bp1[3], bp1[4], ph[m, ax], s1)
            y2 = core._biquad(bp2[0], bp2[1], bp2[2], bp2[3], bp2[4], y1, s2)
            bst[ax, 0] = s1[0]; bst[ax, 1] = s1[1]; bst[ax, 2] = s2[0]; bst[ax, 3] = s2[1]
            y2 = y2 * bpg
            yd = (y2 - ybp_prev[ax]) / Ts
            ybpd[ax] = ybpd[ax] + 0.2 * (yd - ybpd[ax])
            ybp_prev[ax] = y2
            yb[ax] = y2 + hor * ybpd[ax]
        d0[m] = yb[0]; d1[m] = yb[1]
    return d0, d1


def synthetic_housing(n, Ts, seed, f_a=8.0, f_b=10.0, t_switch=1.5, drop=(2.0, 2.1)):
    """Housing page motion: slow intended motion + tremor (frequency step,
    phase continuous, elliptical) + 3 um white noise; optical dropout."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * Ts
    x_int = 2.0e-3 * np.sin(2 * np.pi * 1.1 * t) + 0.6e-3 * np.sin(2 * np.pi * 3.7 * t + 0.4)
    y_int = 1.5e-3 * np.cos(2 * np.pi * 0.9 * t) + 0.4e-3 * np.sin(2 * np.pi * 4.3 * t)
    f = np.where(t < t_switch, f_a, f_b)
    phase = 2 * np.pi * np.cumsum(f) * Ts
    tx = 3.0e-4 * np.sin(phase)
    ty = 1.2e-4 * np.sin(phase + 0.9)
    ph = np.column_stack([x_int + tx + 3e-6 * rng.standard_normal(n), y_int + ty + 3e-6 * rng.standard_normal(n)])
    valid = np.ones(n)
    valid[(t >= drop[0]) & (t < drop[1])] = 0.0
    return t, ph, valid


# ---------------------------------------------------------------------------- generators
def gen_kf(meta):
    P, info = params_for("bal")
    Ts = info["Ts"]
    n = 6000
    t, ph, valid = synthetic_housing(n, Ts, seed=11)
    cap_ticks = sorted(set(list(range(1, 40, 3)) + list(range(200, 5990, 131))))
    capture = {m: [] for m in cap_ticks}
    out = ref_kf_estimator(ph, valid, P, capture=capture)
    cols = {"t": t, "ph0": ph[:, 0], "ph1": ph[:, 1], "valid": valid}
    cols.update({k: v for k, v in out.items()})
    write_vec("kf_seq_bal.vec", cols, {**meta, "profile": "balanced", "reference": "ref_kf_estimator (core._kf_step)",
                                       "signal": "synthetic housing motion, tremor 8->10 Hz at 1.5 s, dropout 2.0-2.1 s"})
    Pa, _ = params_for("asr")
    outa = ref_kf_estimator(ph, valid, Pa)
    cols = {"t": t, "ph0": ph[:, 0], "ph1": ph[:, 1], "valid": valid}
    cols.update({k: v for k, v in outa.items()})
    write_vec("kf_seq_asr.vec", cols, {**meta, "profile": "assertive", "reference": "ref_kf_estimator (core._kf_step)"})
    # single-step vectors from captured realistic states
    rows = []
    qj = P[IDX["kf_qj"]]; qt = P[IDX["kf_qt"]]; kr = P[IDX["kf_r"]]; rdamp = P[IDX["kf_rdamp"]]
    for m in cap_ticks:
        for (x, Pm, y, w) in capture[m]:
            x2 = x.copy(); P2 = Pm.copy()
            innov, S = core._kf_step(x2, P2, y, Ts, w, rdamp, qj, qt, kr)
            rows.append((x, Pm, y, w, x2, P2, innov, S))
    cols = {}
    for i in range(5):
        cols[f"x{i}"] = [r[0][i] for r in rows]
    for i in range(5):
        for j in range(5):
            cols[f"P{i}{j}"] = [r[1][i, j] for r in rows]
    cols["y"] = [r[2] for r in rows]
    cols["w"] = [r[3] for r in rows]
    for i in range(5):
        cols[f"xo{i}"] = [r[4][i] for r in rows]
    for i in range(5):
        for j in range(5):
            cols[f"Po{i}{j}"] = [r[5][i, j] for r in rows]
    cols["innov"] = [r[6] for r in rows]
    cols["S"] = [r[7] for r in rows]
    write_vec("kf_step.vec", cols, {**meta, "reference": "sim.pensim.core._kf_step (numba float64)",
                                    "Ts": Ts, "qj": qj, "qt": qt, "r": kr, "rdamp": rdamp, "profile": "balanced"})


def gen_bpf(meta):
    P, info = params_for("bal")
    Ts = info["Ts"]
    n = 6000
    t, ph, valid = synthetic_housing(n, Ts, seed=12)
    d0, d1 = ref_bpf_estimator(ph, valid, P)
    write_vec("bpf_seq.vec", {"t": t, "ph0": ph[:, 0], "ph1": ph[:, 1], "valid": valid, "dhat0": d0, "dhat1": d1},
              {**meta, "profile": "balanced", "reference": "mode==2 transcription (core._biquad)"})


def gen_biquad(meta):
    P, info = params_for("bal")
    fs = 1.0 / info["Ts"]
    n = 2000
    rng = np.random.default_rng(5)
    t = np.arange(n) / fs
    x = np.where(t >= 0.01, 1.0, 0.0) + 0.3 * np.sin(2 * np.pi * (5 + 200 * t) * t) + 0.05 * rng.standard_normal(n)
    out = {"x": x}
    for name, base in (("ffc", "ffc_b0"), ("bp1", "bp1_b0"), ("bp2", "bp2_b0")):
        b0, b1, b2, a1, a2 = P[IDX[base]:IDX[base] + 5]
        sos = np.array([[b0, b1, b2, 1.0, a1, a2]])
        out[f"y_{name}"] = sps.sosfilt(sos, x)
    # contact-FF design check: the same filter from scipy directly
    sos60 = sps.butter(2, 60.0, btype="low", fs=fs, output="sos")
    out["y_butter60"] = sps.sosfilt(sos60, x)
    write_vec("biquad.vec", out, {**meta, "reference": "scipy.signal.sosfilt; coefficients from model.build_params",
                                  "fs": fs})


def gen_jacobian(meta):
    rng = np.random.default_rng(3)
    rows = []
    for k in range(240):
        th = rng.uniform(math.radians(30), math.radians(89))
        ph = rng.uniform(-math.pi, math.pi)
        ro = rng.uniform(-math.pi, math.pi)
        gam = 1.0 if k < 60 else rng.uniform(0.0, 1.0)
        b = frames.basis(th, ph, ro)
        # numeric construction: a fraction gamma of the rigid-page axial
        # accommodation s = -(v.n)/(a.n) is taken by the suspension
        cols = []
        for v in (b["xH"], b["yH"]):
            s = -(v @ b["n"]) / (b["a"] @ b["n"])
            d = v + gam * s * b["a"]
            cols.append(d[:2])
        J = np.column_stack(cols)
        if gam == 1.0:
            assert np.allclose(J, frames.jacobian(th, ph, ro), atol=1e-12)
            assert np.allclose(np.linalg.inv(J), frames.inverse_jacobian(th, ph, ro), atol=1e-12)
        Ji = np.linalg.inv(J)
        rows.append((th, ph, ro, gam, J, Ji))
    cols = {"theta": [r[0] for r in rows], "phi": [r[1] for r in rows], "rho": [r[2] for r in rows],
            "gamma": [r[3] for r in rows]}
    for i in range(2):
        for j in range(2):
            cols[f"J{i}{j}"] = [r[4][i, j] for r in rows]
    for i in range(2):
        for j in range(2):
            cols[f"Ji{i}{j}"] = [r[5][i, j] for r in rows]
    write_vec("jacobian.vec", cols, {**meta, "reference": "stabpen.frames basis/jacobian/inverse_jacobian; numeric 3-D construction generalised to gamma"})


def gen_crc(meta):
    rng = np.random.default_rng(9)
    rows = []
    for k in range(64):
        n = int(rng.integers(0, 61))
        data = bytes(rng.integers(0, 256, n).astype(np.uint8))
        rows.append((n, binascii.crc_hqx(data, 0xFFFF), data))
    cols = {"len": [r[0] for r in rows], "crc": [r[1] for r in rows]}
    for i in range(60):
        cols[f"b{i}"] = [r[2][i] if i < r[0] else 0 for r in rows]
    write_vec("crc16.vec", cols, {**meta, "reference": "binascii.crc_hqx(data, 0xFFFF) (CRC-16/CCITT-FALSE)"})


def gen_replay(meta, name, mode, ctrl_kw, seed=200, f0=8.0, duration=2.0):
    fz = frozen()
    kw = dict(fz["bal"]) if mode == "kfosc" else {}
    kw.update(fz["bpf"])
    kw.update(ctrl_kw)
    ctrl = model.Controller(mode=mode, **kw)
    tr = sg.TremorSpec(f0=f0, amp_pk=3e-4)
    scn = scenarios.handwriting(seed=seed, duration=duration, tremor=tr)
    ov = {"sensing.opt_noise": 0.0, "sensing.hall_noise_tip": 0.0, "sensing.hall_i_crosstalk_tip": 0.0,
          "sensing.hall_ict_comp": 0.0, "sensing.imu_acc_noise_density": 0.0, "sensing.imu_acc_bias": 0.0,
          "sensing.force_noise": 0.0, "sensing.hall_delay": 0.5e-3, "sensing.opt_delay": 1.0e-3,
          "sensing.imu_delay": 1.0e-3, "electrical.v_bat_nom": 20.0}
    r = model.run(scn, ctrl, overrides=ov, seed=seed)
    P = r.P
    dt = P[IDX["dt"]]; sdec = int(P[IDX["stage_decim"]]); odec = int(P[IDX["opt_decim"]]); od = int(P[IDX["opt_delay"]])
    idl = int(P[IDX["imu_delay"]]); hd = int(P[IDX["hall_delay"]])
    assert int(P[IDX["rec_decim"]]) == sdec == 20 and odec == 40 and od == 40 and idl == 40 and hd == 20
    assert int(P[IDX["mode"]]) == MODES[mode]
    rec = r.rec
    nrec = rec.shape[0]
    if np.any(rec[:, RIDX["sat_v"]] > 0.5):
        raise SystemExit("replay: current loop clamped; raise V_bus")
    z0 = P[IDX["z0"]]; olift = P[IDX["opt_lift_max"]]
    pH = rec[:, RIDX["pHx"]:RIDX["pHx"] + 3]
    q = rec[:, RIDX["q1"]:RIDX["q1"] + 2]
    opt_ok = scn.opt_ok
    n = nrec - 1
    cols = {k: np.zeros(n) for k in ("qm0", "qm1", "fa", "ph0", "ph1", "valid", "dhat0", "dhat1", "west", "g_eff",
                                     "qr0", "qr1", "iref0", "iref1")}
    ph_hold = np.zeros(2)
    for m in range(n):
        k_t = sdec * m
        # Hall: q at the end of step k_t - 20 = record m-1
        qm = q[m - 1] if m >= 1 else np.zeros(2)
        # force: fa_meas as recorded at the end of step k_t - 20
        fa = rec[m - 1, RIDX["Fax_meas"]] if m >= 1 else P[IDX["F_pre"]]
        # optics: last sample at k' = largest multiple of odec <= k_t - 1
        valid = 0.0
        if k_t >= 1:
            kp = ((k_t - 1) // odec) * odec
            if kp >= od:
                idx = (kp - od) // sdec
                hz = pH[idx, 2] - z0
                ok = (opt_ok[kp - od] > 0) and (hz < olift)
                if ok:
                    ph_hold = pH[idx, :2].copy()
                    valid = 1.0
                else:
                    valid = 0.0
        cols["qm0"][m], cols["qm1"][m] = qm
        cols["fa"][m] = fa
        cols["ph0"][m], cols["ph1"][m] = ph_hold
        cols["valid"][m] = valid
        cols["dhat0"][m] = rec[m, RIDX["dhx"]]; cols["dhat1"][m] = rec[m, RIDX["dhx"] + 1]
        cols["west"][m] = rec[m, RIDX["west"]]; cols["g_eff"][m] = rec[m, RIDX["conf"]]
        cols["qr0"][m] = rec[m, RIDX["qr1"]]; cols["qr1"][m] = rec[m, RIDX["qr1"] + 1]
        cols["iref0"][m] = rec[m, RIDX["iref1"]]; cols["iref1"][m] = rec[m, RIDX["iref1"] + 1]
    const = {"theta": P[IDX["theta"]], "phi": P[IDX["phi"]], "rho": P[IDX["rho"]], "gamma": P[IDX["gamma_acc"]],
             "ff_accel": P[IDX["ff_accel"]], "ff_contact": P[IDX["ff_contact"]], "horizon": P[IDX["horizon"]],
             "est": {"kfosc": 2.0, "bpf": 1.0, "neutral": 0.0}[mode]}
    for k, v in const.items():
        cols[k] = np.full(n, v)
    contact = cols["fa"] > P[IDX["F_pre"]] + 0.02
    write_vec(name, cols, {**meta, "reference": "sim.pensim.core.simulate() closed-loop run (numba float64)",
                           "mode": mode, "controller": kw, "overrides": ov, "seed": seed, "tremor_f0": f0,
                           "duration_s": duration, "frac_valid": float(np.mean(cols["valid"])),
                           "frac_contact": float(np.mean(contact)),
                           "note": "inputs reconstructed exactly from the recording (see module docstring)"})


def params_fresh():
    """The vectors must be generated from the same inputs as include/params_gen.h."""
    meta = json.load(open(os.path.join(FW, "include", "params_gen.json")))["meta"]
    cur = {"yaml_sha16": sha16(os.path.join(ROOT, "config", "parameters.yaml")), "estimator_selection_sha16": sha16(SEL),
           "model_py_sha16": sha16(os.path.join(ROOT, "sim", "pensim", "model.py")),
           "core_py_sha16": sha16(os.path.join(ROOT, "sim", "pensim", "core.py"))}
    bad = [k for k, v in cur.items() if meta.get(k) != v]
    if bad:
        raise SystemExit(f"include/params_gen.h is stale ({', '.join(bad)}): run tools/gen_params.py first")


def main():
    params_fresh()
    os.makedirs(OUT, exist_ok=True)
    meta = {"generator": "firmware/tools/gen_vectors.py", "yaml_sha16": sha16(os.path.join(ROOT, "config", "parameters.yaml")),
            "estimator_selection_sha16": sha16(SEL), "core_py_sha16": sha16(os.path.join(ROOT, "sim", "pensim", "core.py")),
            "model_py_sha16": sha16(os.path.join(ROOT, "sim", "pensim", "model.py"))}
    print("generating vectors in", os.path.relpath(OUT, ROOT))
    gen_crc(meta)
    gen_jacobian(meta)
    gen_biquad(meta)
    gen_kf(meta)
    gen_bpf(meta)
    gen_replay(meta, "replay_kf.vec", "kfosc", {"ff_accel": 0.0})
    gen_replay(meta, "replay_bpf.vec", "bpf", {"ff_accel": 0.0})
    gen_replay(meta, "replay_ffc.vec", "kfosc", {"ff_accel": 0.0, "ff_contact": 1.0}, seed=201, f0=9.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
