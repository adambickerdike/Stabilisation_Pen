"""python3 -m rig.selftest : every rig analysis on synthetic data (SIMULATION), in one light process.

Each check generates data with hidden truth (rig.synth, partly through s2r's instrument models),
runs the analysis a real record would go through, and scores the recovery against a tolerance
chosen well inside the uncertainty the rig itself is expected to have. A pass means the software
recovers what it should from data whose structure we control. It says nothing about any real
refill, paper, actuator, sensor, pen or person.

Options: --no-write (do not write results/rig/selftest.json), --quick (smaller data sets).
Target run time: well under a minute on one core.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Callable, Dict, List

import numpy as np

from . import RESULTS, SIM, results_path


class Check:
    def __init__(self):
        self.rows: List[Dict] = []

    def add(self, area: str, name: str, value, truth, tol, ok: bool, unit: str = ""):
        self.rows.append({"area": area, "check": name, "value": _j(value), "truth": _j(truth), "tolerance": _j(tol),
                          "unit": unit, "pass": bool(ok)})


def _j(v):
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


# ------------------------------------------------------------------------------------------ checks
def check_protocol(C: Check, quick: bool):
    from . import protocol, synth
    C.add("protocol", "CRC-16/CCITT-FALSE check value", hex(protocol.crc16_fast(b"123456789")), "0x29b1", "exact",
          protocol.crc16_fast(b"123456789") == 0x29B1)
    s = synth.daq_stream(n=800 if quick else 2000)
    p = protocol.StreamParser()
    data = s["bytes"]
    for k in range(0, len(data), 509):              # feed in odd-sized chunks, as USB delivers
        p.feed(data[k:k + 509])
    a = p.out.arrays()
    good = s["_truth"]["good_seq"]
    got = a["samples"]["seq"].tolist()
    C.add("protocol", "good frames recovered, corrupted frames rejected", len(got), len(good), 0, got == good)
    C.add("protocol", "config frame parsed (f_cpu)", p.out.config.get("f_cpu"), "600000000", "exact",
          p.out.config.get("f_cpu") == "600000000")
    gaps = protocol.seq_gaps(a["samples"]["seq"])
    n_bad = (800 if quick else 2000) - 1 - len(good)
    C.add("protocol", "missing frames counted from the sequence number", gaps, n_bad + 1, 0, gaps == n_bad + 1)


def check_sync(C: Check, quick: bool):
    from . import sync, synth
    e = synth.sync_edges(duration_s=300 if quick else 600)
    tq, nq = sync.decode_widths(e["daq_rise"], e["daq_fall"])
    td, nd = sync.decode_widths(e["dev_rise"], e["dev_fall"])
    fit = sync.fit_clock(td, nd, tq, nq)
    C.add("sync", "clock fit residual max (us), must be <= 50", fit["residual_max_s"] * 1e6, "<=50", 50,
          fit["meets_50us"], "us")
    C.add("sync", "drift recovered (ppm)", fit["drift_ppm"], e["_truth"]["drift_ppm"], 0.5,
          abs(fit["drift_ppm"] - e["_truth"]["drift_ppm"]) < 0.5, "ppm")
    # delay estimators
    fs = 1000.0
    rng = np.random.default_rng(3)
    x = np.convolve(rng.standard_normal(20000), np.ones(15) / 15, "same")
    d_true = 3.4e-3
    # exact fractional delay by a spectral phase shift (linear interpolation would add its own phase)
    Xf = np.fft.rfft(x)
    y = np.fft.irfft(Xf * np.exp(-2j * np.pi * np.fft.rfftfreq(len(x), 1 / fs) * d_true), len(x))
    y = y + 0.05 * rng.standard_normal(len(x))
    d = sync.xcorr_delay(x, y, fs)["delay_s"]
    C.add("sync", "cross-correlation delay (ms)", d * 1e3, d_true * 1e3, 0.05, abs(d - d_true) < 5e-5, "ms")


def check_contact(C: Check, quick: bool):
    from . import calib, contact, synth
    M_true = np.array([[1.0, 0.004, 0.008], [-0.003, 1.0, 0.009], [0.002, 0.001, 1.0]])
    cd = synth.plate_calibration(M_true)
    pc = calib.fit_plate(cd["F"], cd["raw"], cd["pos"])
    gd = synth.guide_calibration(40.0)
    gc = calib.fit_guide_stiffness(gd["slide"], gd["force"])
    C.add("G1 contact", "guide stiffness recovered (N/m)", gc["k_g_N_per_m"], 40.0, 1.0,
          abs(gc["k_g_N_per_m"] - 40) < 1.0, "N/m")
    rows, truths = [], []
    thetas = (35.0, 50.0, 75.0)
    betas = (0.0, 90.0, 180.0, 270.0) if quick else (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
    rng = np.random.default_rng(21)
    for th in thetas:
        for b in betas:
            s = synth.stroke(theta_deg=th, beta_deg=b, v_mm_s=30.0, Fc_N=0.15, rng=rng, plate_matrix=M_true)
            Fp = calib.apply_plate(pc, s["raw"])
            Fc = s["cell"] - (gc["f0_N"] + gc["k_g_N_per_m"] * s["slide"])
            r = contact.analyse_stroke(s["t"], Fc, Fp, s["xy"], s["theta"], s["phi_h"])
            rows.append(r)
            truths.append(s["_truth"])
    mu = np.array([r["mu_drag"] for r in rows])
    C.add("G1 contact", "kinetic friction (mean over strokes)", float(mu.mean()), 0.15, 0.0075,
          abs(mu.mean() - 0.15) < 0.0075)
    ang = np.array([r["friction_angle_deg"] for r in rows])
    C.add("G1 contact", "friction vector angle to the velocity (deg)", float(np.median(ang)), 3.0, 1.0,
          abs(np.median(ang) - 3.0) < 1.0, "deg")
    ratio_err = np.array([r["R_perp_over_Fc"] / t["R_perp_over_Fc"] - 1 for r, t in zip(rows, truths)])
    C.add("G1 contact", "static side load R_perp/F_c, worst relative error", float(np.max(np.abs(ratio_err))), 0.0,
          0.03, np.max(np.abs(ratio_err)) < 0.03)
    clo = np.array([r["closure_N"] for r in rows]) * 1e3
    C.add("G1 contact", "axial closure F_c - R.a, worst (mN)", float(np.max(np.abs(clo))), 0.0, 3.0,
          np.max(np.abs(clo)) < 3.0, "mN")
    p6 = contact.p6_check(rows)
    C.add("G1 contact", "P-6 predicts R_perp/F_c within 15 % (fraction)", p6["fraction_within"], 1.0, 0.1,
          p6["fraction_within"] >= 0.9)
    return rows


def check_ink(C: Check, quick: bool):
    from . import ink, synth
    rng = np.random.default_rng(31)
    lines = []
    n = 3 if quick else 5
    for k in range(n):
        s = synth.ink_line(rng=rng, dpi=1200)
        lines.append(ink.analyse_line(s["img"], s["p0"], s["p1"], s["px_um"], s["force_of_s"]))
    res = ink.minimum_ink_force(lines)
    tru = s["_truth"]["F_1pct"]
    C.add("G1 ink", "minimum ink force from windows (N)", res["F_min_windows_median"], tru, 0.012,
          abs(res["F_min_windows_median"] - tru) < 0.012, "N")
    C.add("G1 ink", "logistic segment model is monotone and finite (F50, N)", res["logistic"]["F50"],
          "finite, below the window threshold", "-",
          np.isfinite(res["logistic"]["F50"]) and res["logistic"]["F50"] < res["F_min_windows_median"] + 0.02)
    return res


def check_coupon(C: Check, quick: bool):
    from . import coupon, synth
    d = synth.coupon_map(n=5 if quick else 7)
    m = coupon.km_map(d["nodes"], d["I"], d["F"], d["R_ohm"], model_Kf=d["model_Kf"])
    err = np.max(np.abs(m["Kf"] / d["_truth"]["Kf"] - 1))
    C.add("G2 coupon", "K_f map, worst relative error", float(err), 0.0, 0.01, err < 0.01)
    C.add("G2 coupon", "K_m at the centre (N/sqrt(W))", m["Km_centre"], d["_truth"]["Km_centre"], 0.005,
          abs(m["Km_centre"] - d["_truth"]["Km_centre"]) < 0.005)
    xs = d["nodes"][:, 0]
    ys = d["nodes"][:, 1]
    sel = np.abs(ys) < 1e-9
    ls = coupon.lateral_stiffness(xs[sel], m["F0"][sel][:, 0])
    C.add("G2 coupon", "parasitic lateral stiffness (N/mm)", ls["dF_dx_N_per_mm"], d["_truth"]["k_neg"], 0.02,
          abs(ls["dF_dx_N_per_mm"] - d["_truth"]["k_neg"]) < 0.02, "N/mm")
    a = synth.attraction()
    af = coupon.attraction_fit(a["gap"], a["F"], 0.77)
    t = a["_truth"]
    Ftrue = t["A"] / (0.77 + t["g0"]) ** t["n"]
    C.add("G2 coupon", "attraction at the design gap (N)", af["F_design_N"], Ftrue, 0.03 * Ftrue,
          abs(af["F_design_N"] / Ftrue - 1) < 0.03, "N")
    h = synth.hall()
    hi = coupon.hall_interference(h["I"], h["reading_um"], 1.0)
    C.add("G2 coupon", "Hall sensitivity to coil current (um/A)", hi["um_per_A"], 6.0, 0.2,
          abs(hi["um_per_A"] - 6.0) < 0.2, "um/A")
    md = synth.mode()
    mf = coupon.mode_fit(md["f"], md["H"])
    C.add("G2 coupon", "loaded mode frequency (Hz)", mf["fn_hz"], md["_truth"]["fn"], 4.0,
          abs(mf["fn_hz"] - md["_truth"]["fn"]) < 4.0, "Hz")
    C.add("G2 coupon", "loaded mode damping ratio", mf["zeta"], md["_truth"]["zeta"], 0.005,
          abs(mf["zeta"] - md["_truth"]["zeta"]) < 0.005)


def check_frf(C: Check, quick: bool):
    from . import frf, synth
    fs = 2000.0
    T = 10.0
    dd = frf.design_disturbance(0.5e-3, T=T, fs=fs, a_max=40.0, n_tones=20)
    C.add("G3 nib", "multitone peak displacement (mm)", dd["x_peak_m"] * 1e3, 0.5, 0.05,
          abs(dd["x_peak_m"] * 1e3 - 0.5) < 0.05, "mm")
    C.add("G3 nib", "multitone peak acceleration (m/s^2) <= cap", dd["a_peak"], "<=40", 40, dd["a_peak"] <= 40.0 * 1.001,
          "m/s^2")
    P = 2 if quick else 3
    x = np.tile(dd["x"], P)
    run = synth.nib_run(x, fs)
    r = frf.frf_periodic(run["housing"][int(T * fs):], run["ink"][int(T * fs):], fs, T, dd["f"])
    Ttrue = run["_truth"]["T_of_f"](r["f"])
    err = np.max(np.abs(np.abs(r["H"]) - np.abs(Ttrue)))
    C.add("G3 nib", "transmissibility |T(f)| recovered 1-30 Hz, worst abs error", float(err), 0.0, 0.02, err < 0.02)
    # closed-loop tracking FRF (q / -housing) and its bandwidth, on a wide multitone
    dw = frf.design_disturbance(0.05e-3, f_lo=2.0, f_hi=400.0, T=2.0, fs=fs, a_max=1e9, n_tones=40)
    xw = np.tile(dw["x"], 3)
    rw = synth.nib_run(xw, fs)
    tr = frf.frf_periodic(-rw["housing"][int(2 * fs):], rw["q"][int(2 * fs):], fs, 2.0, dw["f"])
    bw = frf.bandwidth_3db(tr["f"], tr["H"])
    from scipy import signal as sps
    w, hh = sps.freqs([(2 * np.pi * 60) ** 2], [1, 2 * 0.6 * 2 * np.pi * 60, (2 * np.pi * 60) ** 2],
                      worN=2 * np.pi * np.geomspace(1, 1000, 4000))
    bw_true = w[np.argmax(np.abs(hh) < 1 / np.sqrt(2))] / (2 * np.pi)
    C.add("G3 nib", "closed-loop -3 dB bandwidth (Hz)", bw, bw_true, 0.05 * bw_true, abs(bw / bw_true - 1) < 0.05, "Hz")
    # ink-error reduction against the locked nib over seeds
    rng = np.random.default_rng(41)
    on, off = [], []
    for k in range(4 if quick else 8):
        from stabpen import signals
        tt = np.arange(0, 8.0, 1 / fs)
        d = signals.tremor(tt, signals.TremorSpec(f0=rng.uniform(5, 9), amp_pk=0.5e-3), rng)[:, 0]
        on.append(synth.nib_run(d, fs, rng=rng)["ink"])
        off.append(synth.nib_run(d, fs, locked=True, rng=rng)["ink"])
    red = frf.ink_error_reduction(on, off, fs)
    C.add("G3 nib", "ink-error reduction vs locked nib, 3-12 Hz (oracle, 60 Hz servo, 2.5 ms)",
          red["reduction_mean"], ">= 0.30 (review target, for this synthetic plant)", "-", red["reduction_mean"] >= 0.30)
    return {"transmissibility_f": r["f"], "T_meas": np.abs(r["H"]), "T_true": np.abs(Ttrue), "bandwidth": bw,
            "reduction": red}


def check_pagesense(C: Check, quick: bool):
    from . import pagesense, synth
    d = synth.page_run(duration=6.0)              # the matrix fit needs >= 1.8 s of motion (30 % of the run); 4 s is too short
    q = pagesense.qualify(d["t_truth"], d["g_xy"], d["t_sens"], d["dx"], d["dy"], d["um_per_count"], d["valid"])
    tl = d["_truth"]["latency_s"]
    C.add("page sensing", "latency (ms)", q["latency"]["delay_s"] * 1e3, tl * 1e3, 0.05,
          abs(q["latency"]["delay_s"] - tl) < 5e-5, "ms")
    A = np.asarray(q["matrix"]["A"])
    Ai = d["_truth"]["A_inv"]
    err = np.max(np.abs(A - Ai))
    C.add("page sensing", "scale/rotation matrix, worst element error", float(err), 0.0, 0.01, err < 0.01)
    # expected per-sample noise: white position noise sigma plus count quantisation
    sig = np.sqrt(d["_truth"]["noise_um"] ** 2 + d["um_per_count"] ** 2 / 12)
    ps = q["per_sample"]["rms_um_per_axis"]
    C.add("page sensing", "per-sample noise after 100 ms detrend (um)", ps, round(sig, 2), 0.25 * sig,
          abs(ps / sig - 1) < 0.25, "um")
    w = q["window_10ms"]
    C.add("page sensing", "10 ms window error, vector >= magnitude (DeltaPen metric)",
          [round(w["mag_median_um"], 2), round(w["vec_median_um"], 2)], "vec >= mag", "-",
          w["vec_median_um"] >= w["mag_median_um"])
    # EXP-J10 addition: held/walk split of window errors in sim2j's terms
    for walk in (0.0, 8.0):
        r = synth.page_error_runs(walk_step_um=walk)
        m = pagesense.page_error_model_from_runs(r["runs"])
        C.add("page sensing", f"sim2j model: walk step recovered (truth {walk:g} um)", round(m["walk_step_rms_um"], 2), walk, 1.0,
              abs(m["walk_step_rms_um"] - walk) < 1.0, "um")
        want = "deltapen_held" if walk == 0 else "deltapen_walk"
        C.add("page sensing", f"sim2j model: mode (truth {want})", m["mode_supported"], want, "-", m["mode_supported"] == want)
    return q


def check_thermal(C: Check, quick: bool):
    from . import thermal, synth
    d = synth.thermal_run(duration=900 if quick else 1800)
    f2 = thermal.fit_2node(d["t"], d["P"], d["T_coil"], d["T_web"], d["Ta"])
    tr = d["_truth"]
    for k, key in (("R12_K_per_W", "R12"), ("R2a_K_per_W", "R2a")):
        C.add("thermal", f"two-node {key} (K/W)", f2[k], tr[key], 0.1 * tr[key], abs(f2[k] / tr[key] - 1) < 0.1, "K/W")
    C.add("thermal", "two-node C2 (J/K)", f2["C2_J_per_K"], tr["C2"], 0.2 * tr["C2"],
          abs(f2["C2_J_per_K"] / tr["C2"] - 1) < 0.2, "J/K")
    f1 = thermal.fit_1node(d["t"], d["P"], d["T_coil"], d["Ta"])
    C.add("thermal", "one-node R_th is the coil-to-room sum (K/W)", f1["Rth_K_per_W"], tr["R12"] + tr["R2a"],
          0.15 * (tr["R12"] + tr["R2a"]), abs(f1["Rth_K_per_W"] / (tr["R12"] + tr["R2a"]) - 1) < 0.15, "K/W")
    return f2


def check_collar(C: Check, quick: bool):
    from . import collar, synth
    e = synth.collar_errors()
    dec = collar.g5_decision(e)
    pg = dec["per_grip"]
    C.add("G5 collar", "gate passes where active beats locked by 16 % (light grip)",
          pg["light_2N"]["active_vs_locked"]["mean"], ">= 0.10", "-", pg["light_2N"]["meets_gate_point"])
    C.add("G5 collar", "gate fails where active beats locked by 6 % (firm grip)",
          pg["firm_8N"]["active_vs_locked"]["mean"], "< 0.10", "-", not pg["firm_8N"]["meets_gate_point"])
    return dec


def check_camera(C: Check, quick: bool):
    from . import camera
    rng = np.random.default_rng(51)
    # grid calibration with radial distortion
    pts_mm = np.array([[x, y] for x in np.arange(-5, 5.01, 1.0) for y in np.arange(-3, 3.01, 1.0)])
    true = [0.0094, 0.0, 0.0, 0.0, 0.0094, 0.0, 2e-3, 400.0, 640.0]
    # invert the model numerically: find px for each mm point
    from scipy import optimize
    px = []
    for p in pts_mm:
        g0 = [400 + p[0] / 0.0094, 640 + p[1] / 0.0094]
        sol = optimize.least_squares(lambda q: (camera._distort(true, np.array([q])) - p).ravel(), g0)
        px.append(sol.x)
    px = np.array(px) + 0.03 * rng.standard_normal((len(px), 2))
    # the model maps (row, col) -> (x, y) with x from rows: build mm to match
    cal = camera.calibrate_grid(px, pts_mm, centre=(400.0, 640.0))
    C.add("camera", "dot-grid calibration residual (um)", cal["resid_rms_um"], "< 1", 1.0, cal["resid_rms_um"] < 1.0, "um")
    # static and blurred dot tracking
    errs = []
    for k in range(10):
        rc = (40 + rng.uniform(-2, 2), 40 + rng.uniform(-2, 2))
        img = camera.render_dot((80, 80), rc, rng=rng, blur_vec=(0.0, 3.0 if k % 2 else 0.0))
        c = camera.centroid(img, (40, 40), half=12)
        errs.append(np.hypot(c[0] - rc[0], c[1] - rc[1]))
    C.add("camera", "dot centroid error, worst of 10 (px)", float(max(errs)), "< 0.1", 0.1, max(errs) < 0.1, "px")


def check_tablet(C: Check, quick: bool):
    from . import tablet, synth
    d = synth.tablet_loops(duration=10.0 if quick else 12.0)
    fs = 200.0
    tt, xy = tablet.resample(d["t"], d["xy"], fs)
    _, xc = tablet.resample(d["t"], d["xy_clean"], fs)
    ref = tablet.cross_spectra(xc, fs, np.ones(len(xc), bool))
    ep = tablet.excess_power(xy, fs, np.ones(len(xy), bool), S_ref=ref)
    tru = d["_truth"]
    C.add("tablet (EXP-H01 method)", "excess-power A_pp, major axis (mm)", ep["A_pp_major_mm"], tru["A_pp_major_mm"],
          0.1 * tru["A_pp_major_mm"], abs(ep["A_pp_major_mm"] / tru["A_pp_major_mm"] - 1) < 0.1, "mm")
    C.add("tablet (EXP-H01 method)", "tremor peak frequency (Hz)", ep["f_peak_hz"], tru["f_hz"], 0.3,
          abs(ep["f_peak_hz"] - tru["f_hz"]) <= 0.3, "Hz")
    q = tablet.sampling_quality(d["t"])
    C.add("tablet (EXP-H01 method)", "sampling rate estimate (Hz)", q["rate_hz"], fs, 5.0, abs(q["rate_hz"] - fs) < 5.0,
          "Hz")


def check_uncertainty(C: Check, quick: bool):
    from . import uncertainty as U
    rows = U.tur_table()
    ok = all(np.isfinite(r["TUR"]) and r["TUR"] > 0 for r in rows)
    C.add("uncertainty", "budgets and TUR table computed", len(rows), ">0 rows", "-", ok)
    d = U.decide(0.118, 0.14, "<=", U=0.004)
    C.add("uncertainty", "simple acceptance when TUR >= 4", d["rule"] + "/" + d["verdict"], "simple/pass", "-",
          d["rule"] == "simple" and d["verdict"] == "pass")
    d2 = U.decide(0.137, 0.14, "<=", U=0.004)
    C.add("uncertainty", "guarded acceptance when TUR < 4", d2["rule"] + "/" + d2["verdict"], "guarded/inconclusive",
          "-", d2["rule"] == "guarded" and d2["verdict"] == "inconclusive")


CHECKS: List[Callable] = [check_protocol, check_sync, check_uncertainty, check_contact, check_ink, check_coupon,
                          check_frf, check_pagesense, check_thermal, check_collar, check_camera, check_tablet]


def run(quick: bool = False, write: bool = True) -> Dict:
    C = Check()
    timing = {}
    extras = {}
    for fn in CHECKS:
        t0 = time.time()
        try:
            out = fn(C, quick)
            if out is not None:
                extras[fn.__name__] = out
        except Exception as e:                       # a crash is a failed check, not a silent skip
            C.add(fn.__name__, "ran without error", repr(e), "no exception", "-", False)
        timing[fn.__name__] = round(time.time() - t0, 2)
    n_pass = sum(r["pass"] for r in C.rows)
    summary = {"evidence_status": SIM + " (synthetic data through the rig analyses; method check only)",
               "n_checks": len(C.rows), "n_pass": n_pass, "all_pass": n_pass == len(C.rows), "quick": quick,
               "timing_s": timing, "checks": C.rows}
    if write:
        from stabpen import provenance
        meta = provenance.metadata(SIM + " (rig self-test on synthetic data)", seeds="fixed per check (see rig/selftest.py)")
        provenance.write_json(results_path("selftest.json"), {"meta": meta, **summary})
    summary["_extras"] = extras
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    s = run(quick=a.quick, write=not a.no_write)
    w = max(len(r["check"]) for r in s["checks"])
    for r in s["checks"]:
        v = r["value"]
        vs = f"{v:.4g}" if isinstance(v, float) else str(v)
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {r['area']:<24} {r['check']:<{w}}  {vs} {r['unit']}")
    print(f"\n{s['n_pass']}/{s['n_checks']} checks pass in {time.time() - t0:.1f} s "
          f"(SIMULATION: synthetic data; no rig exists). Timing per area: {s['timing_s']}")
    if not a.no_write:
        print(f"written: {RESULTS}/selftest.json")
    return 0 if s["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
