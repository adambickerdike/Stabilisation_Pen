"""Every analysis recovers what was put into synthetic data (the full self-test, quick mode), plus the
tablet recorder's file round trip. SIMULATION: method checks only; no rig exists."""
import os
import tempfile

import numpy as np

from rig import selftest, synth, tablet


def test_selftest_quick_all_pass():
    s = selftest.run(quick=True, write=False)
    failed = [r for r in s["checks"] if not r["pass"]]
    assert not failed, failed
    assert s["n_checks"] >= 40


def test_tablet_recorder_file_round_trip():
    d = synth.tablet_loops(duration=12.0)
    A = np.array([[3.78, 0.05], [-0.04, 3.80]])
    b = np.array([120.0, 80.0])
    px = d["xy"] @ A.T + b
    fmm = np.array([[10, 10], [200, 10], [200, 287], [10, 287]], float)
    fpx = fmm @ A.T + b
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "rec.csv")
        tablet.write_recording_csv(p, d["t"], px, np.ones(len(px), bool), fiducials_mm=fmm, fiducials_px=fpx)
        rec = tablet.load_recording(p)
    assert rec["units"] == "mm" and rec["cal"]["resid_rms_mm"] < 1e-6
    _, xc = tablet.resample(d["t"], d["xy_clean"], 200.0)
    ref = tablet.cross_spectra(xc, 200.0, np.ones(len(xc), bool))
    res = tablet.analyse_recording(rec, 200.0, S_ref=ref)
    assert abs(res["tremor"]["A_pp_major_mm"] - d["_truth"]["A_pp_major_mm"]) < 0.05
    assert abs(res["tremor"]["f_peak_hz"] - d["_truth"]["f_hz"]) < 0.3


def test_recorder_page_is_self_contained():
    from rig import PKG_DIR
    with open(os.path.join(PKG_DIR, "tablet", "tablet_recorder.html"), encoding="utf-8") as f:
        html = f.read()
    assert "getCoalescedEvents" in html and "pointerType" in html
    assert "http://" not in html.replace("http://www.w3.org", "") and "https://" not in html   # offline, sends nothing


def test_sim2j_page_model_and_patch():
    import types
    from rig import pagesense
    r = synth.page_error_runs(walk_step_um=8.0)
    m = pagesense.page_error_model_from_runs(r["runs"])
    assert m["mode_supported"] == "deltapen_walk" and abs(m["walk_step_rms_um"] - 8.0) < 1.0
    sensing = types.SimpleNamespace(DP_MEDIAN=23.6e-6, DP_SIGMA=1.46)
    run_study = types.SimpleNamespace(PAGE_MODELS=("white", "deltapen_held", "deltapen_walk"))
    with pagesense.patch_sim2j(m, sensing, run_study):
        assert sensing.DP_MEDIAN == m["sim2j"]["DP_MEDIAN_walk_m"]
        assert run_study.PAGE_MODELS == ("white", "deltapen_walk")
    assert sensing.DP_MEDIAN == 23.6e-6 and len(run_study.PAGE_MODELS) == 3


def test_sim2j_page_model_on_tracks():
    from rig import pagesense
    d = synth.page_run(duration=6.0)
    q = pagesense.qualify(d["t_truth"], d["g_xy"], d["t_sens"], d["dx"], d["dy"], d["um_per_count"], d["valid"])
    tr = pagesense.integrate(d["t_sens"], d["dx"], d["dy"], d["um_per_count"])
    s_cal = pagesense.apply_matrix(q["matrix"]["A"], tr["xy"])
    m = pagesense.sim2j_page_model(d["t_truth"], d["g_xy"], d["t_sens"], s_cal, q["latency"]["delay_s"], d["valid"],
                                   per_sample_rms_um=q["per_sample"]["rms_um_per_axis"])
    assert m["n_windows"] > 100 and m["sim2j"]["page_latency_s"] > 0
    assert "req_rvj_c05" in m and m["req_rvj_c05"]["drift_line_um"] == 100.0
