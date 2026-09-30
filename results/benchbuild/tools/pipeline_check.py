"""Bench-build data pipeline check (study H): synthetic data through the real file formats and the rig/ analyses.

    python3 results/benchbuild/tools/pipeline_check.py            # writes results/benchbuild/pipeline_check.json
    python3 results/benchbuild/tools/pipeline_check.py --no-write # prints only

Evidence status: SIMULATION. Every input is synthetic (rig.synth and the generators below, with hidden truth);
the check proves that the files the first bench build will produce can be read by the analysis code, in the
order the plan uses, and that the analyses recover the synthetic truth. It says nothing about any sensor,
refill, paper, coil, wire, guide, anchor, linkage or page sensor. Nothing here is a measurement.

What is exercised (file -> reader -> analysis), one step per build of docs/bench_build_plan.md:
  A  R9 (G1)     DAQ byte stream (raw.bin) -> `python3 -m rig.logger --replay` (CLI) -> session.npz/json
                 -> rig.convert.to_units(CHANNEL_MAPS['R9']) -> split_by_markers -> rig.calib (axial cell,
                 plate matrix, guide stiffness) -> ADC group-delay alignment (t_adc_s) -> rig.contact.analyse_stroke
                 -> rig.convert.to_bench (s2r-bench-1) -> s2r.io.load round trip
  B  R3 ink      16-bit TIFF scan -> PIL -> rig.ink.analyse_line / minimum_ink_force
  C  G2 K_m map  force-map CSV (data template t07_force_map.csv) -> rig.coupon.km_map
  D  G2 anchor   balance CSV (anchor_stiffness.csv) -> rig.calib.fit_guide_stiffness (slope = axial stiffness)
  E  G2 guide    sweep CSV (guide_drag_sweep.csv) -> drag = half the forward/return force difference (numpy, here)
  F  G2 wires    resistance log CSV (k21_wire_log.csv) -> failure rule (numpy, here)
  G  thermal     thermal_run.csv -> rig.thermal.fit_2node
  H  five-bar    encoder/truth CSV (fivebar_encoder_truth.csv) -> forward kinematics (here) checked against
                 wholepen.grounded.FiveBar.kinematics; force map tau = J^T F
  I  R10         DAQ byte stream with SAMPLE (encoder truth) and PAGE frames -> logger replay -> convert (R10) ->
                 PAGE time base (here: rig.convert has no PAGE helper) -> rig.pagesense.qualify
  J  sync        device clock -> rig.sync.decode_widths / fit_clock
  K  verdict     rig.uncertainty.decide
Read-only use of rig/, s2r/, wholepen/; writes only results/benchbuild/pipeline_check.json and a temporary
directory outside the repository.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "benchbuild" / "pipeline_check.json"

from rig import calib, contact, convert, coupon, ink, logger, pagesense, protocol, synth, sync, thermal  # noqa: E402
from rig import uncertainty as U  # noqa: E402

VREF = convert.VREF
F_CPU = 600_000_000


def mvv_to_code(mvv, gain, exc=3.3):
    """Bridge output (mV/V) to an ADS131M08 code at PGA `gain` (inverse of rig.protocol.adc_code_to_volts)."""
    v = np.asarray(mvv, float) * 1e-3 * exc
    return np.round(v * gain / VREF * (1 << 23)).astype(np.int64)


def volts_to_code(v, gain):
    return np.round(np.asarray(v, float) * gain / VREF * (1 << 23)).astype(np.int64)


def write_csv(path, header, rows, comments=()):
    with open(path, "w", newline="", encoding="utf-8") as f:
        for c in comments:
            f.write(f"# {c}\n")
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    return rows


# ------------------------------------------------------------------------------------------------ A: R9 (G1) chain
AX_MVV_PER_N = 2.0          # LSB200 100 g: 2 mV/V at 1 N (MFR AMF-225)
PLATE_MVV_PER_N = 0.25      # SYNTHETIC choice for this check (K3D40: exact sensitivity only in its test report, AMF-224)
HALL_V0, HALL_V_PER_M = 1.65, 500.0   # SYNTHETIC slide Hall: 0.5 V/mm about mid-supply


def step_A(work: Path) -> dict:
    rng = np.random.default_rng(101)
    fs = 1000.0                                   # rig.synth.stroke samples at 1 kHz; the DAQ runs RATE 1000
    M_true = np.array([[1.0, 0.004, 0.008], [-0.003, 1.0, 0.009], [0.002, 0.001, 1.0]])
    # --- calibrations as they would be logged (templates r9_*_calibration.csv) -------------------------------
    loads = np.repeat([0.0, 0.05, 0.1, 0.2, 0.5, 0.2, 0.1, 0.05, 0.0], 1)
    direction = np.array([1, 1, 1, 1, 1, -1, -1, -1, -1])
    ax_read = loads * AX_MVV_PER_N + 2e-5 * rng.standard_normal(len(loads))
    write_csv(work / "r9_axial_cell_calibration.csv", ["load_N", "reading_mVV", "direction"],
              np.column_stack([loads, ax_read, direction]).tolist())
    rows = read_csv(work / "r9_axial_cell_calibration.csv")
    ax_cal = calib.fit_bridge(np.array([float(r["load_N"]) for r in rows]),
                              np.array([float(r["reading_mVV"]) for r in rows]), order=1,
                              direction=np.array([float(r["direction"]) for r in rows]))
    pc_data = synth.plate_calibration(M_true, rng=rng)
    raw_mvv = pc_data["raw"] * PLATE_MVV_PER_N
    write_csv(work / "r9_plate_calibration.csv",
              ["Fx_N", "Fy_N", "Fz_N", "raw_x_mVV", "raw_y_mVV", "raw_z_mVV", "pos_x_mm", "pos_y_mm"],
              np.column_stack([pc_data["F"], raw_mvv, pc_data["pos"]]).tolist())
    rows = read_csv(work / "r9_plate_calibration.csv")
    F_app = np.array([[float(r[k]) for k in ("Fx_N", "Fy_N", "Fz_N")] for r in rows])
    R_app = np.array([[float(r[k]) for k in ("raw_x_mVV", "raw_y_mVV", "raw_z_mVV")] for r in rows])
    P_app = np.array([[float(r[k]) for k in ("pos_x_mm", "pos_y_mm")] for r in rows])
    plate_cal = calib.fit_plate(F_app, R_app, P_app)
    gd = synth.guide_calibration(40.0, rng=rng)
    guide_cal = calib.fit_guide_stiffness(gd["slide"], gd["force"])
    # --- the session: three strokes (conditions) at 50 deg, as rig.synth makes them ------------------------------
    conds = [(50.0, 0.0), (50.0, 90.0), (50.0, 180.0)]
    strokes = [synth.stroke(theta_deg=th, beta_deg=b, v_mm_s=30.0, Fc_N=0.15, fs=fs, rng=rng, plate_matrix=M_true)
               for th, b in conds]
    gd_delay = convert.ADC_GROUP_DELAY_PERIODS / fs   # the ADC reports the input 1.5 periods late (SBAS950B)
    buf = bytearray(protocol.pack_text(f"f_cpu={F_CPU};adc_rate={fs:g};gain=128,128,128,128,1,1,1,1;rig=R9",
                                       protocol.T_CONFIG))
    seq = 0
    t0 = 0.0
    x_off = 0.0
    truth = []
    for ci, s in enumerate(strokes):
        t = s["t"] + t0
        # emulate the sinc3 group delay: the ADC value logged at t_k is the input at t_k - 1.5/fs
        def delayed(y):
            return np.interp(s["t"] - gd_delay, s["t"], y)
        ax_code = mvv_to_code(delayed(s["cell"]) * AX_MVV_PER_N, 128)
        pl = [mvv_to_code(delayed(s["raw"][:, k]) * PLATE_MVV_PER_N, 128) for k in range(3)]
        hall = volts_to_code(HALL_V0 + HALL_V_PER_M * delayed(s["slide"]), 1)
        xy_counts = np.round((s["xy"] + np.array([x_off, 0.0])) / 0.244e-6).astype(np.int64)
        tc = np.round(t * F_CPU).astype(np.int64)
        buf += protocol.pack_event(seq, int(tc[0]), protocol.EV_MARKER, ci)
        for k in range(len(t)):
            buf += protocol.pack_sample(seq, int(tc[k]), [ax_code[k], pl[0][k], pl[1][k], pl[2][k], 0, hall[k], 0, 0],
                                        [xy_counts[k, 0], xy_counts[k, 1], 0, 0], cmd=0, flags=0)
            seq += 1
        t0 = t[-1] + 1.0 / fs
        x_off += s["xy"][-1, 0]
        truth.append(s["_truth"])
    raw_path = work / "r9_session" / "raw_in.bin"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(bytes(buf))
    sess_dir = work / "r9_session" / "replayed"
    cmd = [sys.executable, "-m", "rig.logger", "--replay", str(raw_path), "--out", str(sess_dir)]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if cp.returncode != 0:
        raise RuntimeError("rig.logger --replay failed: " + cp.stderr[-400:])
    sess = logger.load_session(str(sess_dir))
    st = sess["info"]["stats"]
    units = convert.to_units(sess, convert.CHANNEL_MAPS["R9"], {"F_a": ax_cal})
    ev = convert.events_by_kind(sess, float(sess["info"]["config"]["f_cpu"]), int(sess["samples"]["t_cyc"][0]))
    recs = convert.split_by_markers(units, ev["marker"])
    rows_out, errs = [], []
    for rec, (th, b), tru in zip(recs, conds, truth):
        # align: forces (ADC, t_adc_s) resampled onto the encoder clock (t_s) before the stroke analysis
        t_s, t_a = rec["t_s"], rec["t_adc_s"]
        Fa = np.interp(t_s, t_a, rec["F_a"])
        raw = np.column_stack([np.interp(t_s, t_a, rec[k]) for k in ("F_x_mVV", "F_y_mVV", "F_z_mVV")])
        Fp = calib.apply_plate(plate_cal, raw)
        slide = (np.interp(t_s, t_a, rec["s_hall_V"]) - HALL_V0) / HALL_V_PER_M
        Fc = Fa - (guide_cal["f0_N"] + guide_cal["k_g_N_per_m"] * slide)
        xy = np.column_stack([rec["x_enc"], rec["y_enc"]])
        r = contact.analyse_stroke(t_s - t_s[0], Fc, Fp, xy, math.radians(th), 0.0)
        rows_out.append(r)
        errs.append({"mu_drag": r["mu_drag"], "mu_truth": tru["mu_k"], "closure_mN": 1e3 * r["closure_N"],
                     "R_perp_over_Fc": r["R_perp_over_Fc"], "R_perp_over_Fc_truth": tru["R_perp_over_Fc"]})
    # s2r-bench-1 export and reload
    bench_dir = work / "r9_session" / "bench"
    convert.to_bench([{k: v for k, v in rec.items() if isinstance(v, np.ndarray)} | {"condition": rec["condition"]}
                      for rec in recs], str(bench_dir), "EXP-T01", group="strokes",
                     meta={"note": "SIMULATION pipeline check"}, evidence="SIMULATION (bench-build pipeline check)")
    from s2r import io as s2rio
    back = s2rio.load(str(bench_dir))
    back_recs = back["strokes"]["records"]
    same = all(np.array_equal(back_recs[i]["F_a"], recs[i]["F_a"]) and np.array_equal(back_recs[i]["x_enc"], recs[i]["x_enc"])
               for i in range(len(recs)))
    mu_err = max(abs(e["mu_drag"] / e["mu_truth"] - 1) for e in errs)
    rp_err = max(abs(e["R_perp_over_Fc"] / e["R_perp_over_Fc_truth"] - 1) for e in errs)
    clo = max(abs(e["closure_mN"]) for e in errs)
    return {"files": ["raw.bin (write-once)", "session.npz", "session.json", "r9_axial_cell_calibration.csv",
                      "r9_plate_calibration.csv", "s2r-bench-1: manifest.json + strokes/nnnn_k.npz + nnnn.json"],
            "readers": ["python3 -m rig.logger --replay", "rig.logger.load_session", "rig.convert.to_units (R9 map)",
                        "rig.convert.events_by_kind / split_by_markers", "rig.calib.fit_bridge / fit_plate / apply_plate / "
                        "fit_guide_stiffness", "rig.contact.analyse_stroke", "rig.convert.to_bench", "s2r.io.load"],
            "logger_stats": {k: st.get(k) for k in ("frames", "crc_errors", "missing_frames", "samples", "events")},
            "n_conditions": len(recs), "mu_worst_rel_error": mu_err, "R_perp_over_Fc_worst_rel_error": rp_err,
            "closure_worst_mN": clo, "bench_round_trip_identical": bool(same),
            "pass": bool(st.get("crc_errors") == 0 and st.get("missing_frames") == 0 and len(recs) == 3 and mu_err < 0.05
                         and rp_err < 0.03 and clo < 3.0 and same),
            "gap": "rig.contact.analyse_stroke takes one time vector: forces logged at t_adc_s must be resampled onto the "
                   "encoder clock t_s first (done here with np.interp); rig.convert does not do it"}


# ------------------------------------------------------------------------------------------------ B: ink scan
def step_B(work: Path) -> dict:
    from PIL import Image
    rng = np.random.default_rng(202)
    lines, truth = [], None
    for k in range(3):
        s = synth.ink_line(rng=rng, dpi=1200)
        img16 = np.clip(s["img"] * 257.0, 0, 65535).astype(np.uint16)       # 8-bit synthetic scan -> 16-bit TIFF
        p = work / f"scan_line_{k}.tif"
        Image.fromarray(img16).save(p)
        back = np.asarray(Image.open(p)).astype(float)
        lines.append(ink.analyse_line(back, s["p0"], s["p1"], s["px_um"], s["force_of_s"]))
        truth = s["_truth"]["F_1pct"]
    res = ink.minimum_ink_force(lines)
    err = abs(res["F_min_windows_median"] - truth)
    return {"files": ["scan_<code>.tif (16-bit lossless, R3)", "ink_scan_register.csv (line end points, dpi, blind code)"],
            "readers": ["PIL.Image.open -> numpy", "rig.ink.analyse_line", "rig.ink.minimum_ink_force"],
            "F_min_N": res["F_min_windows_median"], "truth_N": truth, "abs_error_N": err, "pass": bool(err < 0.012),
            "note": "force along the line comes from the R9 record (force_of_s); line end points from the fiducial registration"}


# ------------------------------------------------------------------------------------------------ C: coupon force map
def step_C(work: Path) -> dict:
    d = synth.coupon_map(n=5, rng=np.random.default_rng(303))
    rows = []
    for k, (xy, I, F) in enumerate(zip(d["nodes"], d["I"], d["F"])):
        for j in range(len(I)):
            rows.append([k, xy[0], xy[1], I[j], F[j, 0], F[j, 1], F[j, 2]])
    p = work / "t07_force_map.csv"
    write_csv(p, ["node_id", "x_mm", "y_mm", "I_A", "Fx_N", "Fy_N", "Fz_N"], rows)
    back = read_csv(p)
    nodes, I_list, F_list = [], [], []
    for nid in sorted({int(float(r["node_id"])) for r in back}):
        rr = [r for r in back if int(float(r["node_id"])) == nid]
        nodes.append([float(rr[0]["x_mm"]), float(rr[0]["y_mm"])])
        I_list.append(np.array([float(r["I_A"]) for r in rr]))
        F_list.append(np.array([[float(r[k]) for k in ("Fx_N", "Fy_N", "Fz_N")] for r in rr]))
    m = coupon.km_map(np.array(nodes), I_list, F_list, d["R_ohm"], model_Kf=d["model_Kf"])
    err = float(np.max(np.abs(m["Kf"] / d["_truth"]["Kf"] - 1)))
    return {"files": ["t07_force_map.csv"], "readers": ["csv -> per-node arrays (here)", "rig.coupon.km_map"],
            "Km_centre": m["Km_centre"], "Km_centre_truth": d["_truth"]["Km_centre"], "Kf_worst_rel_error": err,
            "pass": bool(err < 0.01)}


# ------------------------------------------------------------------------------------------------ D: anchor stiffness
def step_D(work: Path) -> dict:
    rng = np.random.default_rng(404)
    k_true = 96.0                                            # N/m, SYNTHETIC (inside the 80-120 N/m target band)
    disp_um = np.concatenate([np.arange(0, 101, 10), np.arange(100, -1, -10)])
    g = 9.80665
    force_mN = k_true * disp_um * 1e-6 * 1e3 + 0.01 * rng.standard_normal(len(disp_um))     # 10 uN balance noise
    reading_g = force_mN * 1e-3 / g * 1e3
    p = work / "anchor_stiffness.csv"
    write_csv(p, ["disp_um", "balance_reading_g", "direction"],
              [[d_, r_, 1 if i < 11 else -1] for i, (d_, r_) in enumerate(zip(disp_um, reading_g))])
    back = read_csv(p)
    s = np.array([float(r["disp_um"]) for r in back]) * 1e-6
    f = np.array([float(r["balance_reading_g"]) for r in back]) * 1e-3 * g
    fit = calib.fit_guide_stiffness(s, f)
    return {"files": ["anchor_stiffness.csv (displacement against balance reading)"],
            "readers": ["csv (here)", "rig.calib.fit_guide_stiffness (slope = axial stiffness)"],
            "k_N_per_m": fit["k_g_N_per_m"], "u_k": fit["u_k_g"], "truth": k_true,
            "pass": bool(abs(fit["k_g_N_per_m"] - k_true) < 2.0)}


# ------------------------------------------------------------------------------------------------ E: guide drag
def guide_drag(x_mm, F_mN, direction, trim=0.1):
    """Drag = half the difference between forward and return force at the same position (middle of the stroke);
    the mean of the two is the wires' spring force plus offset. Returns mean drag and its spread."""
    x_mm, F_mN, direction = map(np.asarray, (x_mm, F_mN, direction))
    lo, hi = np.percentile(x_mm, [100 * trim, 100 * (1 - trim)])
    grid = np.linspace(lo, hi, 50)
    fw = np.interp(grid, *_sorted(x_mm[direction > 0], F_mN[direction > 0]))
    bw = np.interp(grid, *_sorted(x_mm[direction < 0], F_mN[direction < 0]))
    d = 0.5 * (fw - bw)
    return {"drag_mN": float(np.mean(d)), "drag_sd_mN": float(np.std(d)),
            "spring_slope_mN_per_mm": float(np.polyfit(grid, 0.5 * (fw + bw), 1)[0])}


def _sorted(x, y):
    o = np.argsort(x)
    return x[o], y[o]


def step_E(work: Path) -> dict:
    rng = np.random.default_rng(505)
    drag_true, k_w = 6.0, 2.1                        # mN and mN/mm, SYNTHETIC
    t = np.linspace(0, 1 / 8.0, 400, endpoint=False)
    rows = []
    for cyc in range(5):
        x = 1.26 * np.sin(2 * np.pi * 8.0 * t)
        v = np.gradient(x, t)
        F = k_w * x + drag_true * np.sign(v) + 0.2 * rng.standard_normal(len(t))
        rows += [[cyc, xi, Fi, 1 if vi > 0 else -1] for xi, Fi, vi in zip(x, F, v)]
    p = work / "guide_drag_sweep.csv"
    write_csv(p, ["cycle", "x_mm", "F_lat_mN", "direction"], rows)
    back = read_csv(p)
    r = guide_drag([float(q["x_mm"]) for q in back], [float(q["F_lat_mN"]) for q in back],
                   [float(q["direction"]) for q in back])
    return {"files": ["guide_drag_sweep.csv"], "readers": ["csv (here)", "guide_drag() in this file (no rig/ function)"],
            **r, "truth_drag_mN": drag_true, "truth_spring_mN_per_mm": k_w,
            "pass": bool(abs(r["drag_mN"] - drag_true) < 0.3 and abs(r["spring_slope_mN_per_mm"] - k_w) < 0.2)}


# ------------------------------------------------------------------------------------------------ F: wire log
def wire_failure(cycles, R, step_rel=0.02, open_ohm=10.0):
    """First cycle count at which the 4-wire resistance steps up by more than step_rel over its running median of
    the previous 20 readings, or reads open. None if no failure."""
    R = np.asarray(R, float)
    for k in range(1, len(R)):
        ref = np.median(R[max(0, k - 20):k])
        if R[k] > open_ohm or R[k] > ref * (1 + step_rel):
            return int(cycles[k])
    return None


def step_F(work: Path) -> dict:
    rng = np.random.default_rng(606)
    cycles = np.arange(0, 43_200_001, 200_000)
    rows = []
    fail_at = {"W1": None, "W2": 31_400_000}
    for wid, fa in fail_at.items():
        R = 0.339 * (1 + 0.0005 * rng.standard_normal(len(cycles)))
        if fa:
            R[cycles >= fa] = 1e6
        rows += [["C01", wid, "solder", int(c), float(r)] for c, r in zip(cycles, R)]
    p = work / "k21_wire_log.csv"
    write_csv(p, ["coupon_id", "wire_id", "clamp_type", "cycles", "R_4w_ohm"], rows)
    back = read_csv(p)
    found = {}
    for wid in fail_at:
        rr = [q for q in back if q["wire_id"] == wid]
        found[wid] = wire_failure([int(q["cycles"]) for q in rr], [float(q["R_4w_ohm"]) for q in rr])
    ok = found["W1"] is None and found["W2"] is not None and abs(found["W2"] - fail_at["W2"]) <= 200_000
    return {"files": ["k21_wire_log.csv"], "readers": ["csv (here)", "wire_failure() in this file (no rig/ function)"],
            "detected": found, "truth": fail_at, "pass": bool(ok)}


# ------------------------------------------------------------------------------------------------ G: thermal
def step_G(work: Path) -> dict:
    d = synth.thermal_run(duration=900, rng=np.random.default_rng(707))
    p = work / "thermal_run.csv"
    write_csv(p, ["t_s", "P_W", "T_coil_C", "T_web_C", "T_amb_C"],
              np.column_stack([d["t"], d["P"], d["T_coil"], d["T_web"], np.full(len(d["t"]), d["Ta"])]).tolist())
    back = read_csv(p)
    arr = {k: np.array([float(r[k]) for r in back]) for k in ("t_s", "P_W", "T_coil_C", "T_web_C", "T_amb_C")}
    f2 = thermal.fit_2node(arr["t_s"], arr["P_W"], arr["T_coil_C"], arr["T_web_C"], arr["T_amb_C"][0])
    tr = d["_truth"]
    err = max(abs(f2["R12_K_per_W"] / tr["R12"] - 1), abs(f2["R2a_K_per_W"] / tr["R2a"] - 1))
    return {"files": ["thermal_run.csv"], "readers": ["csv (here)", "rig.thermal.fit_2node"],
            "R12": f2["R12_K_per_W"], "R2a": f2["R2a_K_per_W"], "worst_rel_error": err, "pass": bool(err < 0.1)}


# ------------------------------------------------------------------------------------------------ H: five-bar
def fivebar_fk(stage, theta, elbows_out=True):
    """Forward kinematics of the five-bar (circle intersection of the two distal links), matching
    wholepen.grounded.FiveBar's elbows-out assembly mode; theta = (theta_0, theta_1) output-shaft angles (rad)."""
    b = np.array([[-stage.base / 2, 0.0], [stage.base / 2, 0.0]])
    e = b + stage.proximal * np.column_stack([np.cos(theta), np.sin(theta)])
    d = np.linalg.norm(e[1] - e[0])
    a = d / 2
    h = math.sqrt(max(stage.distal ** 2 - a * a, 0.0))
    mid = (e[0] + e[1]) / 2
    u = (e[1] - e[0]) / d
    n = np.array([-u[1], u[0]])
    cands = [mid + h * n, mid - h * n]
    return max(cands, key=lambda p: p[1])          # the endpoint above the elbows (workspace y > 0)


def step_H(work: Path) -> dict:
    from wholepen.grounded import FiveBar
    fb = FiveBar()
    rng = np.random.default_rng(808)
    counts_per_rev = 2 ** 14                          # AS5047P: 14-bit (MFR AMF-307)
    rows = []
    for x in np.linspace(-0.03, 0.03, 7):
        for y in np.linspace(fb.centre_y - 0.02, fb.centre_y + 0.02, 5):
            k = fb.kinematics([x, y])
            c = np.round(k["angles"] / (2 * np.pi) * counts_per_rev).astype(int)
            cam = np.array([x, y]) * 1e3 + 0.002 * rng.standard_normal(2)       # camera truth, 2 um noise (SYNTHETIC)
            rows.append([len(rows), int(c[0]), int(c[1]), cam[0], cam[1]])
    p = work / "fivebar_encoder_truth.csv"
    write_csv(p, ["pose_id", "enc0_counts", "enc1_counts", "cam_x_mm", "cam_y_mm"], rows)
    back = read_csv(p)
    err = []
    for r in back:
        th = np.array([float(r["enc0_counts"]), float(r["enc1_counts"])]) / counts_per_rev * 2 * np.pi
        pfk = fivebar_fk(fb, th) * 1e3
        err.append(np.hypot(pfk[0] - float(r["cam_x_mm"]), pfk[1] - float(r["cam_y_mm"])))
    err = np.array(err) * 1e3
    # force map: joint torques for a 0.4 N endpoint force in 8 directions at the patch centre (tau = J^T F)
    k0 = fb.kinematics([0.0, fb.centre_y])
    tau = [k0["J"].T @ (0.4 * np.array([math.cos(a), math.sin(a)])) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    tau_max_mNm = 1e3 * max(np.max(np.abs(t)) for t in tau)
    return {"files": ["fivebar_encoder_truth.csv", "fivebar_force_map.csv"],
            "readers": ["csv (here)", "fivebar_fk() in this file (no rig/ function)", "wholepen.grounded.FiveBar.kinematics (J)"],
            "endpoint_error_rms_um": float(np.sqrt(np.mean(err ** 2))), "endpoint_error_max_um": float(err.max()),
            "output_torque_for_0p4N_max_mNm": tau_max_mNm,
            "pass": bool(np.sqrt(np.mean(err ** 2)) < 20.0),
            "note": "14-bit output encoders and ideal link lengths; the bench fits link lengths and encoder offsets "
                    "against camera truth before judging (EXP-BB06)"}


# ------------------------------------------------------------------------------------------------ I: R10 page sensing
def step_I(work: Path) -> dict:
    d = synth.page_run(duration=6.0, rng=np.random.default_rng(909))
    fs_daq = 4000.0
    t_daq = np.arange(0.0, 6.0, 1 / fs_daq)
    gx = np.interp(t_daq, d["t_truth"], d["g_xy"][:, 0])
    gy = np.interp(t_daq, d["t_truth"], d["g_xy"][:, 1])
    enc = np.round(np.column_stack([gx, gy]) / 0.244).astype(np.int64)          # um -> LM13 counts
    buf = bytearray(protocol.pack_text(f"f_cpu={F_CPU};adc_rate={fs_daq:g};rig=R10", protocol.T_CONFIG))
    events = [(t, "S", k) for k, t in enumerate(t_daq)] + [(t, "P", k) for k, t in enumerate(d["t_sens"])]
    events.sort(key=lambda e: (e[0], e[1]))
    for t, kind, k in events:
        tc = int(round(t * F_CPU))
        if kind == "S":
            buf += protocol.pack_sample(k, tc, [0] * 8, [enc[k, 0], enc[k, 1], 0, 0])
        else:
            buf += protocol.pack_page(k, tc, int(d["dx"][k]), int(d["dy"][k]), squal=100, valid=int(d["valid"][k]))
    raw_path = work / "r10_session" / "raw_in.bin"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(bytes(buf))
    out = work / "r10_session" / "replayed"
    cp = subprocess.run([sys.executable, "-m", "rig.logger", "--replay", str(raw_path), "--out", str(out)],
                        cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    if cp.returncode != 0:
        raise RuntimeError("replay failed: " + cp.stderr[-400:])
    sess = logger.load_session(str(out))
    units = convert.to_units(sess, convert.CHANNEL_MAPS["R10"])
    f_cpu = float(sess["info"]["config"]["f_cpu"])
    t0 = int(sess["samples"]["t_cyc"][0])
    page = sess["page"]
    t_page = (page["t_cyc"].astype(np.float64) - t0) / f_cpu      # PAGE frames on the SAMPLE time base (no rig helper)
    g_xy = np.column_stack([units["x_enc"], units["y_enc"]]) * 1e6
    q = pagesense.qualify(units["t_s"], g_xy, t_page, page["dx"], page["dy"], d["um_per_count"], page["valid"].astype(bool))
    lat_err = abs(q["latency"]["delay_s"] - d["_truth"]["latency_s"])
    return {"files": ["raw.bin with SAMPLE (encoder truth) and PAGE frames", "session.npz", "session.json",
                      "r10_pose_matrix.csv (run plan)"],
            "readers": ["python3 -m rig.logger --replay", "rig.convert.to_units (R10 map)",
                        "PAGE frame time base (here: (t_cyc - t0)/f_cpu)", "rig.pagesense.qualify"],
            "latency_ms": 1e3 * q["latency"]["delay_s"], "latency_truth_ms": 1e3 * d["_truth"]["latency_s"],
            "per_sample_noise_um": q["per_sample"]["rms_um_per_axis"], "window_mag_median_um": q["window_10ms"]["mag_median_um"],
            "n_page_frames": int(len(page)), "pass": bool(lat_err < 1e-4),
            "gap": "rig.convert converts SAMPLE frames only; PAGE and IMU frames need their time base mapped onto the "
                   "SAMPLE clock (3 lines, shown here) before rig.pagesense"}


# ------------------------------------------------------------------------------------------------ J: sync
def step_J(work: Path) -> dict:
    e = synth.sync_edges(duration_s=300, rng=np.random.default_rng(1001))
    tq, nq = sync.decode_widths(e["daq_rise"], e["daq_fall"])
    td, nd = sync.decode_widths(e["dev_rise"], e["dev_fall"])
    fit = sync.fit_clock(td, nd, tq, nq)
    return {"files": ["device log with its own time stamps of the SYNC edges (five-bar controller, page-sensor MCU)"],
            "readers": ["rig.sync.decode_widths", "rig.sync.fit_clock"], "residual_max_us": 1e6 * fit["residual_max_s"],
            "pass": bool(fit["meets_50us"])}


# ------------------------------------------------------------------------------------------------ K: verdict
def step_K(work: Path) -> dict:
    d1 = U.decide(0.118, 0.3, "<=", U=0.006)
    d2 = U.decide(0.29, 0.3, "<=", U=0.006)
    return {"readers": ["rig.uncertainty.decide"], "example_simple": d1, "example_guarded": d2,
            "pass": bool(d1["verdict"] == "pass" and d2["rule"] == "guarded")}


STEPS = [("A_R9_G1_chain", step_A), ("B_ink_scan", step_B), ("C_coupon_Km_map", step_C), ("D_anchor_stiffness", step_D),
         ("E_guide_drag", step_E), ("F_wire_log", step_F), ("G_thermal", step_G), ("H_fivebar", step_H),
         ("I_R10_page_sensing", step_I), ("J_sync", step_J), ("K_verdict", step_K)]


def _j(o):
    if isinstance(o, dict):
        return {k: _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    out = {"evidence_status": "SIMULATION (synthetic data through the file formats and rig/ analyses; no rig exists)",
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": {}}
    t_all = time.time()
    with tempfile.TemporaryDirectory(prefix="benchbuild_pipeline_") as tmp:
        work = Path(tmp)
        for name, fn in STEPS:
            t0 = time.time()
            try:
                r = fn(work)
            except Exception as e:                      # a crash is a failed step, not a skip
                r = {"pass": False, "error": repr(e)}
            r["seconds"] = round(time.time() - t0, 2)
            out["steps"][name] = _j(r)
            print(f"{'PASS' if r.get('pass') else 'FAIL'}  {name:<22} {r['seconds']:6.2f} s")
    out["n_steps"] = len(STEPS)
    out["n_pass"] = sum(1 for v in out["steps"].values() if v.get("pass"))
    out["seconds"] = round(time.time() - t_all, 1)
    try:
        from stabpen import provenance
        out["meta"] = provenance.metadata(out["evidence_status"], seeds="fixed per step (see this file)")
    except Exception as e:                              # provenance is optional here
        out["meta"] = {"note": f"stabpen.provenance unavailable: {e!r}"}
    print(f"{out['n_pass']}/{out['n_steps']} steps pass in {out['seconds']} s (SIMULATION)")
    if not a.no_write:
        OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
        print("written:", OUT)
    return 0 if out["n_pass"] == out["n_steps"] else 1


if __name__ == "__main__":
    sys.exit(main())
