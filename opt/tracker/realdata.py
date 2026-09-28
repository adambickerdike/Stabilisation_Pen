r"""Executable path from recorded pens to tuned trackers (EXP-E01 / EXP-H01 recordings; SIMULATION self-test only).

Nothing here has seen real data.  This module fixes the recording format, turns recordings into the streams every
tracker of fusion/ and opt/tracker reads, derives the training labels the way fusion.personal does (no simulator
truth exists on a real pen), fits the AKF by the adjoint and reports the metrics.  `python3 -m opt.tracker.realdata
--selftest` writes simulated recordings in this format and runs the whole path, so the path is known to execute
before the first participant is recorded.

Recording format (one .npz per task and participant; SI units; times in s on the pen's clock):
  meta_json        JSON: participant, group ("ET" | "PD" | "control"), task ("trace" | "free"), session,
                   theta_deg, phi_deg, rho_deg (nominal pen altitude, azimuth and roll, stabpen/frames.py; from the
                   stand or the IMU at rest), r_board_m (IMU distance
                   from the nib), page_latency_s, imu_extra_latency_s
  imu_t            (N,)   acquisition time of each IMU sample (record 0x07 time stamps)
  imu_av           (N,)   time the sample was available to the firmware
  f_body           (N, 3) accelerometer specific force, body frame (m/s^2; 0x07 LSB x 0.122 mg at +-4 g)
  w_body           (N, 3) gyroscope rate, body frame (rad/s; 0x07 LSB x 4.375 mdps at +-125 dps)
  pos_t, pos_av    (M,)   page-sensor acquisition and availability times
  pos              (M, 2) page-sensor position (m, page frame), pos_ok (M,) 1 = valid
  con_t, con_av    (L,)   axial contact sensor times, con (L,) 1 = in contact
  shape            (P, 2) for task "trace" only: the known template in drawing order (m, registered only up to an
                   offset, as the calibration shapes of fusion.personal)
The IMU is compensated here exactly as fusion.sensors' "gyro" option (attitude from the leaky-integrated gyroscope,
gravity leak removed, lever arm r d(omega)/dt with a 300 Hz low-pass), so the tracker sees what the firmware sees.

Labels: for "trace" tasks, fusion.personal.page_label (page path matched to the shape in drawing order, cross-track
residual band-passed 3-15 Hz per stroke); the tracker's fit to it is fusion.personal's score, differentiable in
opt.tracker.personal.  For "free" writing of healthy controls the false correction is the RMS of the estimate.
Fit: Adam through the AKF adjoint on the training participants' trace tasks (+ lambda_fc x false correction on the
controls' free writing); participants are split before anything else (AC-E01-01).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
from scipy.signal import butter, lfilter, sosfilt

from fusion import personal as PS
from fusion import sensors as S

from . import adjoint as AD
from . import data as DA
from . import personal as PE
from . import schedule as SCH
from . import torch_akf as TA
from . import train_akf as TR

G_VEC = np.array([0.0, 0.0, -9.80665])


# ------------------------------------------------------------------ IMU compensation (fusion.sensors "gyro")
def compensate(imu_t, f_body, w_body, theta_deg, phi_deg, r_board, odr=None, rho_deg: float = 0.0) -> np.ndarray:
    """Page-frame nib acceleration (N, 3) from raw body-frame accelerometer and gyroscope samples."""
    from stabpen.frames import basis
    B = basis(math.radians(theta_deg), math.radians(phi_deg), math.radians(rho_deg))
    R0 = np.column_stack([B["xH"], B["yH"], B["a"]])
    a = B["a"]
    dt = float(np.median(np.diff(imu_t))) if odr is None else 1.0 / odr
    wp = w_body @ R0.T
    lam = math.exp(-dt / 2.0)
    Omh = lfilter([dt], [1.0, -lam], wp, axis=0)
    fp = f_body @ R0.T
    est = fp + G_VEC + np.cross(Omh, fp)
    alpha = np.vstack([np.zeros((1, 3)), np.diff(wp, axis=0) / dt])
    alpha = sosfilt(butter(2, 300.0, fs=1.0 / dt, output="sos"), alpha, axis=0)
    return est - r_board * np.cross(alpha, a)


def load(path: str, tick_hz: float = 2000.0):
    """(Streams, meta, shape or None) of one recording."""
    z = np.load(path)
    meta = json.loads(str(z["meta_json"]))
    acc = compensate(z["imu_t"], z["f_body"], z["w_body"], meta["theta_deg"], meta.get("phi_deg", 0.0), meta["r_board_m"],
                     rho_deg=meta.get("rho_deg", 0.0))
    t_end = float(max(z["imu_t"][-1], z["pos_t"][-1]))
    st = S.Streams(tick_t=np.arange(0.0, t_end, 1.0 / tick_hz), acc_t=z["imu_t"], acc_av=z["imu_av"],
                   acc=np.ascontiguousarray(acc[:, :2]), pos_t=z["pos_t"], pos_av=z["pos_av"], pos=z["pos"],
                   pos_ok=z["pos_ok"].astype(float), con_t=z["con_t"], con_av=z["con_av"], con=z["con"].astype(float),
                   meta={"page_rate": 1.0 / float(np.median(np.diff(z["pos_t"]))), "page_latency": meta.get("page_latency_s", 2e-3)})
    shape = z["shape"] if "shape" in z.files else None
    return st, meta, shape


class TraceTask(PE.Calib):
    """A trace task with its label (fusion.personal.page_label), built from streams instead of a simulation."""

    def __init__(self, st: S.Streams, shape: np.ndarray, meta: Dict):  # noqa: D401 (no super().__init__: no simulation)
        self.st = st
        self.pl = PS.page_label(st, shape)
        self.est = PS.tremor_from_calibration(self.pl)
        self.meta = meta
        tt = st.tick_t
        tq = np.clip(st.pos_t, tt[0], tt[-1])
        i = np.clip(np.searchsorted(tt, tq, side="right") - 1, 0, len(tt) - 2)
        self.i0 = torch.as_tensor(i, dtype=torch.long)
        self.fr = torch.as_tensor((tq - tt[i]) / (tt[i + 1] - tt[i]), dtype=TA.DT)
        self.nrm = torch.as_tensor(self.pl["normal"], dtype=TA.DT)
        self.segs = [(int(a), int(b)) for a, b in self.pl["segments"]]
        self.use = torch.as_tensor(self.pl["use"])
        lab = np.where(self.pl["use"], self.pl["label"], 0.0)
        self.lab = torch.as_tensor(lab, dtype=TA.DT)
        self.den = float(np.sum(lab[self.pl["use"]] ** 2))
        self.sff = PE.SosFiltFilt(self.pl["sos"], max(b - a for a, b in self.segs) + 2 * 40)


def fit(traces: Sequence[TraceTask], controls: Sequence[S.Streams], start: Dict, lam_fc: float = 0.1, iters: int = 30,
        lr: float = 0.03, log=print) -> Dict:
    """Population fit: mean label misfit over the trace tasks + lambda_fc x false correction (um / 100) on the
    controls' free writing.  All recordings must share the tick count (pad or crop beforehand)."""
    static = TA.static_of(start)
    th = TR.project(TA.to_theta(TA.trainable_start(start)).clone()).requires_grad_(True)
    opt = torch.optim.Adam([th], lr=lr)
    sch_t = [SCH.build(t.st) for t in traces]
    ev_t, pk_t = DA.light_events(sch_t), AD.Packed(sch_t)
    ctl = None
    if controls:
        sch_c = [SCH.build(c) for c in controls]
        m = [torch.as_tensor(((np.interp(c.tick_t, c.con_t, c.con) > 0.5) & (c.tick_t > 0.5)).astype(float)) for c in controls]
        ctl = (DA.light_events(sch_c), AD.Packed(sch_c), torch.stack(m))
    hist, best = [], None
    for it in range(iters + 1):
        vals = TA.from_theta(th)
        dh = AD.forward(pk_t, ev_t, vals, static)
        mis = torch.stack([t.fit(dh[i]) for i, t in enumerate(traces)]).mean()
        J = mis
        fc = torch.zeros((), dtype=TA.DT)
        if ctl is not None:
            dc = AD.forward(ctl[1], ctl[0], vals, static)
            mm = ctl[2][..., None]
            fc = (torch.sqrt((dc ** 2 * mm).sum((1, 2)) / ctl[2].sum(1).clamp(min=1)) * 1e6).mean()
            J = J + lam_fc * fc / 100.0
        hist.append({"iter": it, "J": float(J), "label_misfit": float(mis), "fc_um": float(fc)})
        if best is None or float(J) < best[0]:
            best = (float(J), {k: float(v) for k, v in vals.items()}, it)
        log(f"[realdata fit] it {it}: J {float(J):.4f} misfit {float(mis):.4f} FC {float(fc):.1f} um")
        if it == iters:
            break
        opt.zero_grad()
        J.backward()
        th.grad[~torch.isfinite(th.grad)] = 0.0
        opt.step()
        TR.project(th)
    return {"params": TA.to_numba(best[1], static), "best_iter": best[2], "history": hist}


# ------------------------------------------------------------------ self-test on simulated recordings in the format
def write_simulated(out_dir: str, seed: int, f0: float, amp: float, task: str) -> str:
    """A simulated recording in the format above (SIMULATION; for the self-test only)."""
    from fusion import data as FD
    os.makedirs(out_dir, exist_ok=True)
    cfg = S.config(page="1k", comp="gyro")
    if task == "trace":
        r1, _ = PS.calibration_records(seed, f0, amp, clean=False)
        shape_it = PS.calibration_path(dt=1e-3)
        shape = shape_it.xy[shape_it.pen_down]
    else:
        spec = FD.nominal_spec(seed, 0.0, 0.0, duration=5.0)
        _, r1 = FD.pair_records(spec, use_cache=False)
        shape = None
    rng = np.random.default_rng(seed + 7)
    t_a = np.arange(rng.uniform(0, 1.0 / cfg.acc.odr), r1.t[-1], 1.0 / cfg.acc.odr)
    sig = S.body_signals(r1, cfg)
    fb = S._accel_readings(sig["board"], r1.t, t_a, cfg.acc, rng)
    wb = S._gyro_readings(sig["rate"], r1.t, t_a, cfg.gyro, cfg.acc.odr, rng)
    st = S.make_streams(r1, cfg, seed + 11)
    meta = {"participant": f"sim{seed}", "group": "ET" if task == "trace" else "control", "task": task, "session": 1,
            "theta_deg": math.degrees(r1.theta), "phi_deg": math.degrees(r1.phi), "rho_deg": math.degrees(r1.rho),
            "r_board_m": cfg.r_board,
            "page_latency_s": cfg.page.latency, "imu_extra_latency_s": cfg.acc.extra_latency, "simulated": True}
    arrs = {"meta_json": json.dumps(meta), "imu_t": t_a, "imu_av": t_a + cfg.acc.extra_latency, "f_body": fb, "w_body": wb,
            "pos_t": st.pos_t, "pos_av": st.pos_av, "pos": st.pos, "pos_ok": st.pos_ok, "con_t": st.con_t,
            "con_av": st.con_av, "con": st.con}
    if shape is not None:
        arrs["shape"] = shape
    p = os.path.join(out_dir, f"{meta['participant']}_{task}.npz")
    np.savez_compressed(p, **arrs)
    return p


def selftest(out_dir: str, start: Dict, iters: int = 5) -> Dict:
    """Write 2 simulated trace tasks and 1 control free-writing recording, then load, label, fit and report."""
    paths = [write_simulated(out_dir, 7101, 8.0, 0.3e-3, "trace"), write_simulated(out_dir, 7102, 6.0, 0.3e-3, "trace"),
             write_simulated(out_dir, 7103, 0.0, 0.0, "free")]
    traces, controls = [], []
    for p in paths:
        st, meta, shape = load(p)
        if meta["task"] == "trace":
            traces.append(TraceTask(st, shape, meta))
        else:
            controls.append(st)
    K = min(len(t.st.tick_t) for t in traces)
    for t in traces:
        t.st.tick_t = t.st.tick_t[:K]
    r = fit(traces, controls, start, iters=iters)
    return {"paths": paths, "fit": {k: r[k] for k in ("best_iter", "history")}, "params": r["params"]}


if __name__ == "__main__":
    from fusion import run_study as FRS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "build", "realdata_selftest"))
    a = ap.parse_args()
    if a.selftest:
        torch.set_num_threads(1)
        AD.set_threads(1)
        out = selftest(a.dir, FRS.population(FRS.tuned()))
        print(json.dumps(out["fit"]["history"], indent=1))
