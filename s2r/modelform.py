"""C3 helpers: structurally different truths identified with M1's structure, and residual diagnostics.

Diagnostics (the analyst sees only the data and the M1-structure fit):
  * FRF misfit bands: mean |normalised complex residual|^2 per band (1 = noise level);
  * output-error whiteness on a held-out record: the fitted M1-structure model predicts
    the Hall reading from the logged current command; the residual is compared with the
    sensor noise measured in the record's quiet tail, and tested for whiteness
    (Ljung-Box) and for correlation with the input;
  * parameter drift across excitation levels (chi-square test of constancy);
  * physical plausibility of the identified loop delay against the design value.

Evidence status: SIMULATION (truth data) + CALCULATION (diagnostics).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from . import exp_b05, ident
from . import instruments as ins
from . import stage_model as sm

BANDS = [(2, 8), (8, 20), (20, 50), (50, 100), (100, 160), (160, 240), (240, 300)]


LADDER = (0.05, 0.25)   # setup chirps at these fractions of the target, each shaped on the previous FRF

# Practical-significance margins for the drift test (PROPOSAL, set after the control case showed a
# statistically significant but 0.01 % change of f_n): a parameter drifts only when the change is
# significant at 1 % AND larger than this. f_n, m_eq: a tenth of the smallest single-parameter accuracy
# C2 asks for (m_eq 11 %); loop delay: about a tenth of its 28 us requirement; zeta: its C2
# requirement is > 300 %, so 5 % keeps friction-like amplitude dependence visible.
DRIFT_TOL = {"fn_hz": ("rel", 0.01), "zeta": ("rel", 0.05), "m_eq": ("rel", 0.01), "hall_delay_us": ("abs", 5.0)}


def _shaping_fit(rec):
    """Second-order fit of one chirp's IV FRF (5 % weights), used only to shape the next chirp."""
    fp, Hp, _, _ = ident.frf_iv([rec["daq"]["ref_A"]], [rec["daq"]["i_A"]],
                                [exp_b05._disp(rec["daq"]["v_m_s"], 10000.0)], 10000.0, 2.0, 300.0)
    return ident.fit_second_order(fp, Hp, 0.05 * np.abs(Hp) + 1e-12, fit_delay=False)


def stage_dataset(plant: Dict, ex: sm.Extras, rng, session, q_target=30e-6, n_chirps=4, T_c=10.0, noise_scale=1.0):
    """EXP-B05 dataset (same format as exp_b05.generate) from the standalone structural truth.
    Excitation: pilot chirp shaped for 5 um on the nominal plant, then an amplitude ladder (5 %
    and 25 % of the target, each shaped on the FRF of the previous chirp), then the identification
    chirps shaped on the last ladder FRF. With amplitude-dependent physics (friction) the pilot
    alone under-predicts the response at the target level and the first shaped chirp overshoots."""
    t_in, i_p = exp_b05.chirp_current(min(T_c, 10.0), 10000.0, exp_b05.nominal_amp_fn(5e-6))
    r = sm.run(plant, t_in, i_p, ex, rng)
    rec = exp_b05.attach_reference(exp_b05.measure_chirp(r, rng, session, plant, noise_scale, hall_key="q_lever"),
                                   t_in, i_p)
    fit_p = _shaping_fit(rec)
    setup_peaks = [float(np.max(np.abs(r["q1"])))]
    for s in LADDER:
        t_in, i_c = exp_b05.chirp_current(T_c, 10000.0, exp_b05.fitted_amp_fn(s * q_target, fit_p))
        r = sm.run(plant, t_in, i_c, ex, rng)
        rec = exp_b05.attach_reference(
            exp_b05.measure_chirp(r, rng, session, plant, noise_scale, hall_key="q_lever"), t_in, i_c)
        fit_p = _shaping_fit(rec)
        setup_peaks.append(float(np.max(np.abs(r["q1"]))))
    amp = exp_b05.fitted_amp_fn(q_target, fit_p)
    recs = []
    peak = 0.0
    for c in range(n_chirps):
        t_in, i_c = exp_b05.chirp_current(T_c, 10000.0, amp)
        r = sm.run(plant, t_in, i_c, ex, rng)
        recs.append(exp_b05.attach_reference(
            exp_b05.measure_chirp(r, rng, session, plant, noise_scale, hall_key="q_lever"), t_in, i_c))
        peak = max(peak, float(np.max(np.abs(r["q1"]))))
    k = plant["stage.k_tip"]
    return {"chirps": recs, "T_c": T_c, "n_chirps": n_chirps, "q_peak_last_m": peak, "setup_peaks_m": setup_peaks,
            "static": exp_b05.ds_static_tip(k, rng, session, F_max=0.03, noise_scale=noise_scale),
            "axial": exp_b05.ds_axial(plant["stage.axial_k"], plant["stage.axial_preload"], rng, session,
                                      noise_scale=noise_scale),
            "T_magnet_C": exp_b05.T_TEST + session.offset(ins.THERMOCOUPLE), "bench_s": 0.0}


def g1_bands(f, H, model, sig, fn_hz, f_lo=2.0, f_hi=100.0, per_octave=3, res_factor=1.3):
    """Gap metric G1 (validation/sim_to_real.md section 4): the measured FRF over the twin FRF,
    averaged per 1/3 octave (inverse-variance weights), as magnitude (dB) and phase (deg).
    Reported separately off the resonance and inside [fn/1.3, 1.3 fn]."""
    n_b = int(np.ceil(per_octave * np.log2(f_hi / f_lo)))
    edges = f_lo * 2.0 ** (np.arange(n_b + 1) / per_octave)
    r = H / model
    w = (np.abs(model) / np.maximum(sig, 1e-30)) ** 2
    bands = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (f >= lo) & (f < hi)
        if not m.any():
            continue
        rm = np.sum(w[m] * r[m]) / np.sum(w[m])
        res = (hi > fn_hz / res_factor) and (lo < fn_hz * res_factor)
        bands.append({"band_hz": [float(lo), float(hi)], "mag_db": float(20 * np.log10(abs(rm))),
                      "phase_deg": float(np.degrees(np.angle(rm))), "resonance": bool(res)})
    off = [b for b in bands if not b["resonance"]]
    on = [b for b in bands if b["resonance"]]
    mx = lambda bs, k: float(max(abs(b[k]) for b in bs)) if bs else 0.0  # noqa: E731
    return {"bands": bands, "off_res_max_db": mx(off, "mag_db"), "off_res_max_deg": mx(off, "phase_deg"),
            "res_max_db": mx(on, "mag_db"), "res_max_deg": mx(on, "phase_deg")}


def pen_oe_residual(res: Dict, rec: Dict, tail_s=1.2):
    """Predict the Hall reading of a held-out record from the logged command with the fitted
    M1-structure model (step-invariant plant + identified loop delay) and test the residual."""
    a, fn_, z, _ = res["frf"]["fit"]["p"]
    tau = res["estimates"]["sensing.hall_delay"]["loop_delay_s"]
    u = np.asarray(rec["pen"]["iref_A"])
    y = np.asarray(rec["pen"]["q_hall_m"])
    n = min(len(u), len(y))
    u, y = u[:n], y[:n]
    fs = 2000.0
    f = np.fft.rfftfreq(n, 1 / fs)
    G = exp_b05.step_invariant(a, fn_, z, 1 / fs, np.maximum(f, 1e-6))
    G[0] = exp_b05.step_invariant(a, fn_, z, 1 / fs, np.array([1e-6]))[0]
    yp = np.fft.irfft(np.fft.rfft(u) * G * np.exp(-2j * np.pi * f * tau), n)
    r = y - yp
    tail = slice(n - int(tail_s * fs), n)
    active = slice(int(0.2 * fs), n - int(tail_s * fs))
    noise = float(np.std(r[tail]))
    ra = r[active] - np.mean(r[active])
    lb = ident.ljung_box(ra, 20)
    xc = ident.xcorr_test(ra, u[active], 20)
    spec = np.abs(np.fft.rfft(ra * np.hanning(len(ra)))) ** 2
    fr = np.fft.rfftfreq(len(ra), 1 / fs)
    top = float(fr[np.argmax(spec[fr > 1.0]) + np.sum(fr <= 1.0)])
    return {"resid_rms_um": float(np.std(ra) * 1e6), "tail_noise_um": noise * 1e6,
            "excess_ratio": float(np.std(ra) / max(noise, 1e-12)), "ljung_box": lb, "xcorr_input": xc,
            "resid_peak_hz": top}


def oe_refine(res: Dict, recs, fs=2000.0):
    """Output-error refinement of the M1-structure pen-domain model (a, f_n, zeta, loop delay) on
    the estimation records: minimise the time-domain Hall prediction error. Returns a copy of res
    with the refined parameters (used only for the whiteness test on the held-out record)."""
    import copy
    a0, fn0, z0, _ = res["frf"]["fit"]["p"]
    tau0 = res["estimates"]["sensing.hall_delay"]["loop_delay_s"]
    data = []
    for rec in recs:
        u = np.asarray(rec["pen"]["iref_A"])
        y = np.asarray(rec["pen"]["q_hall_m"])
        n = min(len(u), len(y))
        data.append((np.fft.rfft(u[:n]), y[:n], np.fft.rfftfreq(n, 1 / fs), n))
    scale = max(np.std(data[0][1]), 1e-12)

    def resid(p):
        a, fn_, z, tau = a0 * p[0], fn0 * p[1], z0 * p[2], tau0 + p[3] * 1e-4
        out = []
        for U, y, f, n in data:
            G = exp_b05.step_invariant(a, fn_, z, 1 / fs, np.maximum(f, 1e-6))
            yp = np.fft.irfft(U * G * np.exp(-2j * np.pi * f * tau), n)
            out.append((y - yp)[int(0.2 * fs):] / scale)
        return np.concatenate(out)

    fit = ident.nls(resid, [1.0, 1.0, 1.0, 0.0])
    p = fit["p"]
    r2 = copy.deepcopy({"frf": {"fit": {"p": [a0 * p[0], fn0 * p[1], z0 * p[2], 0.0]}},
                        "estimates": {"sensing.hall_delay": {"loop_delay_s": tau0 + p[3] * 1e-4}}})
    return r2


def run_stage_case(plant: Dict, ex: sm.Extras, rng, levels=(10e-6, 30e-6, 100e-6), n_chirps=4, T_c=10.0,
                   Kf=None, L=None, R20=None, fit_band=(2.0, 300.0)):
    """Identify with M1's structure at several excitation levels; return fits and diagnostics."""
    session = ins.draw_session(rng)
    Kf = Kf or plant["actuator.Kf"]
    out = {"levels": []}
    for lv in levels:
        ds = stage_dataset(plant, ex, rng, session, q_target=lv, n_chirps=n_chirps + 1, T_c=T_c)
        held = ds["chirps"][-1]
        ds["chirps"] = ds["chirps"][:-1]
        res = exp_b05.identify(ds, Kf, 0.005 * Kf, L_hat=L or plant["actuator.L"],
                               R20_hat=R20 or plant["actuator.R20"], fit_band=fit_band)
        f = res["frf"]["f"]
        bands = ident.band_misfit(f, res["frf"]["fit"]["norm_resid"], BANDS)
        sig_eff = np.maximum(res["frf"]["sigma"], 1e-3 * np.abs(res["frf"]["H"]) + 1e-30)
        model = res["frf"]["H"] + res["frf"]["fit"]["norm_resid"] * sig_eff     # the fitted twin FRF
        g1 = g1_bands(f, res["frf"]["H"], model, sig_eff, res["frf"]["fit"]["p"][1])
        oe_raw = pen_oe_residual(res, held)
        oe = pen_oe_residual(oe_refine(res, ds["chirps"]), held)
        oe["before_refinement"] = {"excess_ratio": oe_raw["excess_ratio"], "ljung_box_p": oe_raw["ljung_box"]["p"]}
        e = res["estimates"]
        a, fn_, z, tau_m = res["frf"]["fit"]["p"]
        se = res["frf"]["fit"]["se"]
        out["levels"].append({
            "q_target_um": lv * 1e6, "q_peak_um": ds["q_peak_last_m"] * 1e6,
            "setup_peaks_um": [x * 1e6 for x in ds["setup_peaks_m"]],
            "fn_hz": float(fn_), "u_fn_hz": float(se[1]), "zeta": float(z), "u_zeta": float(se[2]),
            "m_eq": e["stage.m_eq"]["value"], "u_m_eq": e["stage.m_eq"]["u"],
            "k_tip_frf": e["stage.k_tip"]["frf"], "u_k_frf": e["stage.k_tip"]["u_frf"],
            "hall_delay_us": e["sensing.hall_delay"]["value"] * 1e6, "u_hall_delay_us": e["sensing.hall_delay"]["u"] * 1e6,
            "tau_mech_us": float(tau_m * 1e6), "fit_chi2_per_dof": res["frf"]["fit"]["chi2_per_dof"],
            "band_misfit": bands, "g1": g1, "oe": oe,
            "coh_pen_fmax_hz": e["sensing.hall_delay"]["f_max_coh_0.9_hz"]})
    lv = out["levels"]
    out["drift"] = {}
    for k, u in (("fn_hz", "u_fn_hz"), ("zeta", "u_zeta"), ("m_eq", "u_m_eq"), ("hall_delay_us", "u_hall_delay_us")):
        v = np.array([x[k] for x in lv])
        kind, tol = DRIFT_TOL[k]
        out["drift"][k] = ident.drift_test(v, np.array([x[u] for x in lv]),
                                           tol=tol * abs(float(np.mean(v))) if kind == "rel" else tol)
    return out


def verdicts(case: Dict, design_hall_us=100.0, delay_tol_us=25.0):
    """What a reviewer would flag from the diagnostics alone (thresholds are proposals)."""
    lv = case["levels"]
    mid = lv[len(lv) // 2]
    worst = max(mid["band_misfit"], key=lambda b: b["chi2_per_dof"])
    flags = {
        "frf_misfit_band": worst["band_hz"] if worst["chi2_per_dof"] > 4.0 else None,
        "frf_misfit_chi2": worst["chi2_per_dof"],
        "oe_residual_not_white": not mid["oe"]["ljung_box"]["white_at_1pct"],
        "oe_excess_over_sensor_noise": mid["oe"]["excess_ratio"],
        "oe_flag": mid["oe"]["excess_ratio"] > 1.3,
        "oe_resid_peak_hz": mid["oe"]["resid_peak_hz"],
        "drift_flags": [k for k, d in case["drift"].items() if d["drift"]],
        "drift_significant_only": [k for k, d in case["drift"].items() if not d["constant_at_1pct"] and not d["drift"]],
        "g1_off_res_db_deg": [mid["g1"]["off_res_max_db"], mid["g1"]["off_res_max_deg"]],
        "g1_res_db_deg": [mid["g1"]["res_max_db"], mid["g1"]["res_max_deg"]],
        "g1_flag": bool(mid["g1"]["off_res_max_db"] > 1.0 or mid["g1"]["off_res_max_deg"] > 5.0
                        or mid["g1"]["res_max_db"] > 3.0 or mid["g1"]["res_max_deg"] > 20.0),
        "loop_delay_excess_us": mid["hall_delay_us"] - design_hall_us,
        "loop_delay_flag": abs(mid["hall_delay_us"] - design_hall_us) > max(delay_tol_us, 3 * mid["u_hall_delay_us"]),
    }
    flags["any"] = bool(flags["frf_misfit_band"] or flags["oe_flag"] or flags["drift_flags"]
                        or flags["loop_delay_flag"])
    return flags
