#!/usr/bin/env python3
"""Study V (simulator v2): every stage behind results/sim2/.

Stages (each writes results/sim2/_cache/stage_<name>.json; `report` assembles results/sim2/*.json, the figures with
their CSV twins, the evidence rows and the replay):
  h1check     reproduce H1 (opt/inertial Rev H-B) on its test seeds: oracle and causal ratios        (SIM, ~45 min)
  diagnose    attribution of the largest H1 differences (stiff inner servo; tracker noise seeds)     (SIM, ~20 min)
  contact     MuJoCo soft contact: stiffness, creep, sliding force, gliding, slip onset, pen sliding;
              the H1 law (LuGre): breakaway, pre-sliding stiffness, stick-slip                       (SIM, ~5 min)
  convergence timestep and integrator convergence of the Rev H case (training seed 300)              (SIM, ~20 min)
  energy      energy balance: conservative, damped and actuated checks, four integrators             (SIM, ~2 min)
  gyro        rotor reaction torque against h x omega                                                (SIM, <1 min)
  sensors     IMU noise and ODR against fusion/, native accelerometer, page-sensor latency           (SIM, ~1 min)
  native      the Rev H cases with MuJoCo's native Coulomb contact (model-form difference)           (SIM, ~15 min)
  frontstop   refill front-stop designs under large nose corrections (design interaction)          (SIM, ~10 min)
  arm         articulated arm: tip impedance fit to H1, tremor torque calibration, writer tracking,
              the Rev H nose in the arm hand against the H1 hand                                     (SIM, ~30 min)
  myo         MyoSuite MyoArm pen-point impedance at a pen grasp over co-contraction                 (SIM, <1 min)
  validate    literature validation: writing kinematics, tremor spectra, wrist resonance, forces    (SIM, ~10 min)
  env         Gymnasium environment: speed on one core, domain randomisation, smoke rollouts         (SIM, ~3 min)
  plugins     plug-in smoke runs (reaction mass, end-cap rotor, heel drive, multi-plane nose)         (SIM, ~3 min)
  report      JSON, figures, CSV twins, evidence rows, replay
Run: python3 -m sim2.run_study [--quick] [--stages a,b,...]
--quick runs a reduced version of every stage into results/sim2/_cache/quick/ (final results untouched).
Seed plan: test seeds 200-203 are used only by h1check/diagnose (the H1 comparison needs H1's own test cases); every
other stage and every tuning choice uses seeds >= 300.  Evidence status: SIMULATION and CALCULATION.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import sim2  # noqa: E402,F401
from stabpen import provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim2")
CACHE = os.path.join(OUT, "_cache")
QUICK = False


def cache_dir():
    return os.path.join(CACHE, "quick") if QUICK else CACHE


def save_stage(name, obj):
    os.makedirs(cache_dir(), exist_ok=True)
    obj = dict(obj)
    obj["meta"] = provenance.metadata("SIMULATION (simulator v2, MuJoCo 3.6; synthetic writing and tremor; nothing measured)",
                                      extra={"stage": name, "quick": QUICK, "script": "sim2/run_study.py"})
    provenance.write_json(os.path.join(cache_dir(), f"stage_{name}.json"), obj)


def load_stage(name, quick=None):
    q = QUICK if quick is None else quick
    p = os.path.join(CACHE, "quick" if q else "", f"stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def log(msg):
    print(msg, flush=True)


# ============================================================================================ H1 reproduction
def stage_h1check(quick=False):
    from sim2 import h1compare as HC
    if quick:
        grids = {0.5: [{"seed": 200, "f0": 10.0, "amp": 1.0e-3}]}
    else:
        grids = {0.5: [{"seed": s, "f0": f, "amp": a} for s in (200, 201, 202, 203) for f in (4.0, 8.0, 12.0)
                       for a in (0.3e-3, 1.0e-3, 2.0e-3)]
                      + [{"seed": s, "f0": 8.0, "amp": 1.0e-3, "kind": "wrist"} for s in (200, 201, 202, 203)],
                 0.3: [{"seed": s, "f0": f, "amp": a} for s in (200, 201) for f in (8.0, 12.0) for a in (1.0e-3, 2.0e-3)],
                 0.7: [{"seed": s, "f0": f, "amp": a} for s in (200, 201) for f in (8.0, 12.0) for a in (1.0e-3, 2.0e-3)]}
    out = {"splits": {}}
    for r, cases in grids.items():
        log(f"h1check: r_rot {r}, {len(cases)} cases")
        out["splits"][str(r)] = HC.compare_grid(cases, r, log=log)
    pub = json.load(open(os.path.join(ROOT, "results", "opt", "inertial_opt.json")))["rev_h_B_table"]
    pubm = {}
    for row in pub:
        pubm[(row["tracker"], row["r_rot"], row["kind"], round(row["amp_mm"], 3), row["f0"])] = row
    comp = []
    for sp, res in out["splits"].items():
        for e in res["summary"]["by_condition"]:
            ko = ("ship", float(sp), e["kind"], round(e["amp_mm"], 3), e["f0"])
            kc = ("revh", float(sp), e["kind"], round(e["amp_mm"], 3), e["f0"])
            if ko in pubm and kc in pubm:
                comp.append({"r_rot": float(sp), **e, "pub_oracle": pubm[ko].get("oracle_ratio"), "pub_akf": pubm[kc]["akf_ratio"],
                             "pub_n": pubm[kc]["n"]})
    out["published_means"] = comp
    out["label"] = ("SIM: sim2 (H1 hand, H1 contact law, dynamic nose + refill) against H1 (opt.inertial.evaluate) on H1's own "
                    "test scenarios; published = results/opt/inertial_opt.json rev_h_B_table (means over seeds 200-203)")
    save_stage("h1check", out)
    return out


def stage_diagnose(quick=False):
    from sim2 import h1compare as HC
    h1 = load_stage("h1check", quick=quick) or load_stage("h1check", quick=False)
    rows = h1["splits"]["0.5"]["rows"]
    out = HC.diagnose(rows, n_worst=1 if quick else 3, noise_seeds=(0, 1) if quick else (0, 1, 2, 3, 4), log=log)
    out["label"] = ("SIM: the largest sim2-H1 differences of stage h1check (r_rot 0.5) rerun with a 2 kHz inner nose servo "
                    "(oracle) and with five sensor-noise seeds in both models (causal)")
    save_stage("diagnose", out)
    return out


# ============================================================================================ verification
CONTACT_SETTINGS = [
    {"name": "sim2 native default", "solref": (5e-4, 1.0), "solimp": (0.99, 0.999, 1e-4, 0.5, 2.0), "impratio": 10.0},
    {"name": "MuJoCo default", "solref": (0.02, 1.0), "solimp": (0.9, 0.95, 0.001, 0.5, 2.0), "impratio": 1.0},
    {"name": "intermediate", "solref": (2e-3, 1.0), "solimp": (0.95, 0.99, 1e-4, 0.5, 2.0), "impratio": 1.0},
]


def stage_contact(quick=False):
    from sim2 import verify as V
    out = {"native_block": [], "pen_sliding": [], "label": "SIM: MuJoCo 3.6 soft contacts and the H1 contact law (verify.py)"}
    sets = CONTACT_SETTINGS[:1] if quick else CONTACT_SETTINGS
    for st in sets:
        t0 = time.time()
        r = V.native_block_tests(st["solref"], st["solimp"], 0.12, st["impratio"])
        r["name"] = st["name"]
        out["native_block"].append(r)
        log(f"  native block '{st['name']}': k {r['static_stiffness_N_per_m']['measured']:.3g} vs {r['static_stiffness_N_per_m']['closed_form']:.3g} N/m, "
            f"creep {r['creep']['v_creep_m_s'] * 1e6:.3g} um/s (closed form {r['creep']['closed_form_m_s'] * 1e6:.3g}), "
            f"mu_slide {r['sliding_mu_elliptic']:.4f}/{r['sliding_mu_pyramidal']:.4f}, gliding {r['gliding']['mean_gap_um']:.2f} um "
            f"(pred {r['gliding']['predicted_um']:.2f}) ({time.time() - t0:.0f} s)")
    out["lugre"] = V.lugre_tests()
    log(f"  LuGre: {json.dumps(out['lugre'])[:400]}")
    ps = [{"solref": st["solref"], "solimp": st["solimp"], "impratio": st["impratio"], "dt": 25e-6} for st in sets]
    if not quick:
        ps.append({"solref": (5e-4, 1.0), "solimp": (0.99, 0.999, 1e-4, 0.5, 2.0), "impratio": 10.0, "noslip_iterations": 10, "dt": 25e-6})
    dirs = ((1, 0),) if quick else ((1, 0), (-1, 0), (0, 1))
    rows = V.pen_sliding(ps, directions=dirs, T=0.25 if quick else 0.3)
    for r in rows:
        r["solref"] = list(r["solref"])
        r["solimp"] = list(r["solimp"])
        log(f"  pen sliding solref {r['solref']} impratio {r['impratio']} noslip {r.get('noslip_iterations', 0)} dir {r['dir']}: "
            f"Ns {r['Ns_mean']:.3f} N cv {r['Ns_cv']:.3f}, mu_app {r['mu_apparent']:.3f}, flicker {r['flicker']}")
    out["pen_sliding"] = rows
    save_stage("contact", out)
    return out


def stage_convergence(quick=False):
    from sim2 import verify as V
    T = 1.0 if quick else 3.0
    out = {"label": "SIM: Rev H case (H1 hand, H1 contact law unless stated), training seed 300, 8 Hz 1 mm, first "
                    f"{T:g} s; ink path difference against the finest step"}
    out["h1_contact"] = V.convergence((25e-6, 50e-6) if quick else (12.5e-6, 25e-6, 50e-6, 100e-6), contact="h1", T=T, log=log)
    if not quick:
        out["native_contact"] = V.convergence((12.5e-6, 25e-6, 50e-6, 100e-6), contact="mujoco", T=T, log=log)
        out["integrators"] = [V.convergence((25e-6,), contact="h1", T=T, log=log, integrator=ig) for ig in ("RK4", "Euler", "implicit")]
    save_stage("convergence", out)
    return out


def stage_energy(quick=False):
    from sim2 import verify as V
    rows = []
    for ig in (("implicitfast",) if quick else ("implicitfast", "implicit", "Euler", "RK4")):
        for case in ("conservative", "damped", "actuated"):
            r = V.energy_audit(case, T=0.2 if quick else 0.5, integrator=ig)
            rows.append(r)
            log(f"  energy {ig} {case}: E0 {r['E0_J']:.3e} J, dE {r['dE_J']:+.3e}, W_damp {r['W_damper_J']:+.3e}, "
                f"W_act {r['W_actuator_J']:+.3e}, residual {r['residual_rel']:+.2e}")
    save_stage("energy", {"rows": rows, "label": "SIM: pen in the air, H1 hand springs as joint springs (verify.energy_audit)"})


def stage_gyro(quick=False):
    from sim2 import verify as V
    out = V.gyro_torque(spin_rpms=(20000,) if quick else (5000, 10000, 20000), rates=(5.0,) if quick else (2.0, 5.0, 10.0))
    log(f"  gyro: max relative error {out['max_rel_error']:.2e}")
    out["label"] = "SIM: 18.1 g rotor (16 x 5 mm WHA) on a driven gimbal; reaction torque against h x omega"
    save_stage("gyro", out)


def stage_sensors(quick=False):
    from sim2 import verify as V
    out = V.sensor_tests(T=2.0 if quick else 4.0)
    log(f"  sensors: {json.dumps(out)[:600]}")
    out["label"] = "SIM: sensor models (sensors.py) against fusion.sensors and MuJoCo's native accelerometer"
    save_stage("sensors", out)


def stage_native(quick=False):
    """Model-form difference of the paper contact: the Rev H oracle and unmodified ink error with MuJoCo's native
    soft Coulomb contact against the H1 contact law (training seeds)."""
    from dataclasses import replace
    from sim2 import h1compare as HC, params as P
    cases = [(300, 8.0, 1e-3)] if quick else [(s, f, 1e-3) for s in (300, 301) for f in (8.0, 12.0)]
    rows = []
    settings = [("h1", None), ("mujoco", {})]
    if not quick:
        settings.append(("mujoco_stiff", {"solref": (5e-4, 1.0), "solimp": (0.99, 0.999, 1e-4, 0.5, 2.0), "impratio": 10.0}))
    for model, kw in settings:
        cfg = P.h1_check_config(0.5)
        if kw is not None:
            cfg = cfg.replace(contact=replace(cfg.contact, model="mujoco", **kw))
        ev = HC.Sim2Eval(0.5, cfg=cfg)
        for (seed, f0, amp) in cases:
            t0 = time.time()
            r = ev.case(seed, f0, amp, controllers=("oracle",))
            rows.append({"contact": model, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "unmod_e_rms_um": r["unmod_e_rms_um"],
                         "oracle_ratio": r["oracle"]["ratio"], "oracle_band_ratio": r["oracle"]["band_ratio"]})
            log(f"  native-vs-h1 {model} seed {seed} {f0:g} Hz: unmod {r['unmod_e_rms_um']:.1f} um, oracle {r['oracle']['ratio']:.3f} "
                f"({time.time() - t0:.0f} s)")
    save_stage("native", {"rows": rows, "label": "SIM: Rev H-B, H1 hand, training seeds; mujoco = native soft contact at the "
                                                 "default setting (solref 2 ms, solimp 0.95/0.99, impratio 1, elliptic); "
                                                 "mujoco_stiff = solref 0.5 ms, solimp 0.99/0.999, impratio 10"})


def stage_frontstop(quick=False):
    """Design interaction found while building sim2: tilting the nose moves the ball along t1 and changes its height, so
    the refill must extend by about q z_p cot(theta); a front stop fixed 0.3 mm beyond the contact position lifts the
    ball off the paper during large corrections.  Oracle correction with three front-stop designs (training seeds)."""
    from dataclasses import replace
    import numpy as np
    from sim.handpen import evaluate as HE
    from sim2 import builder as B, h1compare as HC, params as P, sim as S
    cases = [(300, 8.0, 2e-3)] if quick else [(s, f, a) for s in (300, 301) for (f, a) in ((8.0, 1e-3), (8.0, 2e-3), (12.0, 2e-3))]
    rows = []
    for fs in ("nose_adaptive", "carrier", "wide"):
        cfg = P.h1_check_config(0.5)
        cfg = cfg.replace(refill=replace(cfg.refill, front_stop=fs))
        pm = B.build(cfg)
        for (seed, f0, amp) in cases:
            t0 = time.time()
            sc, sc0 = HC.scenario(seed, f0, amp)
            ref = S.run(pm, sc0)
            un = S.run(pm, sc)
            n_ticks = int(math.ceil(len(sc.t) / 20))
            orc = S.run(pm, sc, S.RunOptions(source="oracle", clean=S.clean_ticks(ref, n_ticks)))
            mu = HE.compare(un, ref)
            mo = HE.compare(orc, ref)
            t = orc["t"]
            down = sc.fpush[np.minimum((t / (sc.t[1] - sc.t[0])).astype(int), len(sc.fpush) - 1)] > 0.5
            rows.append({"front_stop": fs, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "unmod_e_rms_um": mu["e_rms_um"],
                         "oracle_ratio": mo["e_rms_um"] / mu["e_rms_um"],
                         "oracle_contact_frac_pen_down": float(np.mean(orc["contact"][down & (t > 0.5)] > 0)),
                         "ref_contact_frac_pen_down": float(np.mean(ref["contact"][down & (t > 0.5)] > 0)),
                         "refill_s_min_mm": float(np.min(orc["s"][t > 0.5]) * 1e3), "s_lo_mm": pm.info["refill_s_lo"] * 1e3})
            log(f"  front stop {fs} seed {seed} {f0:g} Hz {amp * 1e3:g} mm: oracle {rows[-1]['oracle_ratio']:.3f}, contact while pen down "
                f"{rows[-1]['oracle_contact_frac_pen_down']:.3f} (reference {rows[-1]['ref_contact_frac_pen_down']:.3f}) ({time.time() - t0:.0f} s)")
    save_stage("frontstop", {"rows": rows, "label": "SIM: Rev H-B with the H1 hand; nose_adaptive = stop follows the nose "
                                                    "deflection (0.3 mm margin), carrier = fixed 0.3 mm beyond contact, wide = "
                                                    "0.3 mm + stop travel x cot(theta)"})


# ============================================================================================ arm and MyoSuite
def stage_arm(quick=False):
    import numpy as np
    from sim2 import builder as B, hand as HD, params as P, tremor as TR, validate as VA
    out = {"label": "SIM: articulated arm (hand.py); tip impedance fitted to H1's (SIM fit); tremor torques calibrated on "
                    "the linearised model (CALC); training seeds 300-301"}
    t0 = time.time()
    cal = HD.calibrate_to_h1(P.Config(hand_model="arm"), maxiter=40 if quick else 700, log=log)
    out["calibration"] = cal
    log(f"  arm calibration done ({time.time() - t0:.0f} s): rms rel error {cal['rms_rel_error']:.3f}")
    if not quick:
        provenance.write_json(P.ARM_CALIBRATION, {"arm": cal["arm"], "multipliers": cal["multipliers"],
                                                  "rms_rel_error": cal["rms_rel_error"],
                                                  "meta": provenance.metadata("SIMULATION (fit of the arm's joint impedance to H1's tip impedance)",
                                                                              extra={"script": "sim2/run_study.py stage arm"})})
    arm = P.Arm(**{k: v for k, v in {"k_wrist_fe": cal["arm"]["k_wrist_fe"], "k_wrist_rud": cal["arm"]["k_wrist_rud"],
                                     "k_ps": cal["arm"]["k_ps"], "zeta": cal["arm"]["zeta"], "k_base": cal["arm"]["k_base_x"],
                                     "k_base_y": cal["arm"]["k_base_y"], "k_base_z": cal["arm"]["k_base_z"],
                                     "b_base": cal["arm"]["b_base"], "b_base_z": cal["arm"]["b_base_z"]}.items()})
    pm = B.build(VA.arm_config(arm))
    # tremor torque per unit tip amplitude
    tab = []
    for kind in ("ET", "PD_action"):
        for f0 in ((6.0,) if quick else (4.0, 5.0, 6.0, 8.0, 10.0, 12.0)):
            c = TR.calibrate(pm, TR.profile(kind, f0=f0, amp_tip=1e-3))
            tab.append({"kind": kind, "f0": f0, "A0_N_m_per_mm": c["A0"], "tip_m_per_N_m": c["tip_per_unit_m"]})
    out["tremor_calibration"] = tab
    log(f"  tremor torque for 1 mm at the tip: " + "; ".join(f"{r['kind']} {r['f0']:g} Hz ps {r['A0_N_m_per_mm']['ps'] * 1e3:.1f} mN m" for r in tab))
    out["writer_tracking"] = VA.writer_tracking(pm, seeds=(300,) if quick else (300, 301), duration=2.0 if quick else 3.0)
    log(f"  writer tracking: {out['writer_tracking']}")
    # the Rev H nose in the arm hand against the H1 hand, same writing, same tremor frequency and pen amplitude target
    cache = {}
    rows = []
    cases = [(300, 6.0)] if quick else [(s, f) for s in (300, 301) for f in (6.0, 10.0)]
    for (seed, f0) in cases:
        ts = time.time()
        a = VA.arm_case(pm, seed, TR.profile("ET", f0=f0, amp_tip=1e-3), duration=2.0 if quick else 3.0, cache=cache)
        h = VA.h1_case(seed, f0, 1e-3, duration=2.0 if quick else 3.0, cache=cache)
        rows.append({"seed": seed, "f0": f0, "arm": a, "h1": h})
        log(f"  arm vs H1 hand seed {seed} {f0:g} Hz: arm unmod {a['unmod_e_rms_um']:.0f} um (band {a['ink_band']['rms_um']:.0f}), "
            f"oracle {a['oracle']['ratio']:.3f}; H1 unmod {h['unmod_e_rms_um']:.0f} um (band {h['ink_band']['rms_um']:.0f}), "
            f"oracle {h['oracle_ratio']:.3f} ({time.time() - ts:.0f} s)")
    out["arm_vs_h1"] = rows
    save_stage("arm", out)


def stage_myo(quick=False):
    from sim2 import myo as MY
    out = MY.study(quick=quick, log=log)
    out["label"] = ("SIM: MyoSuite 2.12.2 MyoArm (63 Hill-type muscles, 38 joints) with a 5 g pen welded to thumb, index and "
                    "middle distal phalanges; linearised about the grasp posture at constant activation")
    save_stage("myo", out)


# ============================================================================================ validation
def stage_validate(quick=False):
    from sim2 import builder as B, params as P, validate as VA
    out = {"label": "SIM/CALC against literature ranges (ledger ids in docs/sim_v2.md section 6)"}
    seeds = (300, 301) if quick else tuple(range(300, 310))
    out["writer_lognormal"] = VA.writer_kinematics(seeds, "lognormal")
    log(f"  writer lognormal: speed {out['writer_lognormal']['speed_mm_s']}, strokes {out['writer_lognormal']['stroke_duration_ms']}, "
        f"spectrum {out['writer_lognormal']['velocity_spectrum']}, beta {out['writer_lognormal']['power_law_beta']}")
    try:
        gs = (330, 331) if quick else tuple(range(330, 338))
        out["writer_glyph"] = VA.writer_kinematics(gs, "glyph")
        log(f"  writer glyph: speed {out['writer_glyph']['speed_mm_s']}, strokes {out['writer_glyph']['stroke_duration_ms']}, "
            f"spectrum {out['writer_glyph']['velocity_spectrum']}, beta {out['writer_glyph']['power_law_beta']}")
    except Exception as e:                                  # the glyph writer needs aiguide data
        out["writer_glyph"] = {"error": repr(e)}
        log(f"  writer glyph unavailable: {e!r}")
    pm = B.build(VA.arm_config())
    out["tremor_spectra"] = VA.tremor_spectra(pm, duration=2.5 if quick else 4.0)
    for r in out["tremor_spectra"]:
        log(f"  tremor {r['kind']} {r['f0']:g} Hz: ink band rms {r['ink']['rms_um']:.0f} um p99 {r['ink']['p99_um']:.0f} um, "
            f"peak {r['ink']['peak_Hz']:.2f} Hz, h2/h1 {r['ink']['h2_to_h1_power']:.3f}, pen rate {r['pen_rate_rms_deg_s']:.2f} deg/s, "
            f"gate writing {r['gate_mean_writing']:.2f}")
    out["wrist_resonance"] = VA.wrist_resonance()
    wr = out["wrist_resonance"]
    log(f"  hand-wrist: tip response peak {wr['nominal']['peak_Hz']:.1f} Hz (+300 g {wr['loaded']['peak_Hz']:.1f} Hz); wrist natural "
        f"frequency {wr['nominal']['f_n_wrist_Hz']:.1f} Hz (+300 g {wr['loaded']['f_n_wrist_Hz']:.1f} Hz), zeta {wr['nominal']['zeta_wrist']:.2f}")
    save_stage("validate", out)


# ============================================================================================ environment, plug-ins
def stage_env(quick=False):
    import numpy as np
    from sim2 import env as E, params as P, plugins as PL
    out = {"label": "SIM: Gymnasium environment (env.py) on one core of a shared 4-core machine (load from other studies)"}
    n = 300 if quick else 2000
    out["speed"] = [E.speed_test(n_steps=n, contact="h1", seed=0)]
    if not quick:
        out["speed"].append(E.speed_test(n_steps=n, contact="mujoco", seed=0))
    for s in out["speed"]:
        log(f"  env speed {s['contact']}: {s['env_steps_per_s']:.0f} steps/s at {s['control_hz']:.0f} Hz "
            f"({s['sim_seconds_per_wall_second']:.3f} sim s per wall s), reset {s['reset_s']:.1f} s")
    out["dr"] = {k: {"low": v[0], "high": v[1], "scale": v[2], "source": v[3]} for k, v in E.DR.items()}
    # smoke rollouts: zero action vs a small random policy, one episode each (training seeds)
    roll = []
    for pol in ("zero", "random"):
        env = E.PenEnv(E.EnvConfig(seed=300, episode_s=1.0 if quick else 2.0))
        obs, info = env.reset(seed=300)
        rng = np.random.default_rng(1)
        R = 0.0
        errs = []
        done = False
        k = 0
        while not done:
            a = np.zeros(env.n_act) if pol == "zero" else rng.uniform(-0.2, 0.2, env.n_act)
            obs, r, term, trunc, inf = env.step(a)
            R += r
            if inf["contact"]:
                errs.append(inf["ink_error_m"])
            done = term or trunc
            k += 1
        roll.append({"policy": pol, "steps": k, "return": float(R), "ink_err_rms_um": float(np.sqrt(np.mean(np.square(errs))) * 1e6) if errs else None,
                     "obs_finite": bool(np.all(np.isfinite(obs))), "params": {kk: float(v) for kk, v in info["params"].items()}})
        log(f"  rollout {pol}: {k} steps, return {R:.1f}, ink error rms {roll[-1]['ink_err_rms_um']} um")
    out["rollouts"] = roll
    # with a plug-in: the action space grows by the plug-in's commands
    env = E.PenEnv(E.EnvConfig(base=P.Config(plugins=[PL.ReactionMass()]), seed=301, episode_s=0.5))
    obs, info = env.reset(seed=301)
    for _ in range(50):
        obs, r, term, trunc, inf = env.step(np.full(env.n_act, 0.1))
    out["plugin_env"] = {"act_dim": env.n_act, "obs_dim": int(obs.shape[0]), "obs_finite": bool(np.all(np.isfinite(obs)))}
    log(f"  env with reaction mass: act {env.n_act}, obs {obs.shape[0]}")
    save_stage("env", out)


def stage_plugins(quick=False):
    import numpy as np
    from sim2 import builder as B, params as P, plugins as PL, sim as S, verify as V
    from sim2 import h1compare as HC
    out = {"label": "SIM: plug-in smoke runs on the Rev H pen with the H1 hand (every plug-in parameter is ASSUMPTION)"}
    T = 0.4 if quick else 0.8
    # reaction mass: 8 Hz sinusoidal force command on t1, pen writing still
    rm = PL.ReactionMass()
    cfg = P.h1_check_config(0.5).replace(plugins=[rm])
    pm = B.build(cfg)
    F = 0.1
    w = 2 * math.pi * 8.0
    r = S.run(pm, V._still(T=T), S.RunOptions(plugin_cmd=lambda t, pm_: [np.array([F * math.sin(w * t), 0.0])]))
    x = r["rm_x0"][r["t"] > 0.2]
    out["reaction_mass"] = {"F_amp_N": F, "f_Hz": 8.0, "stroke_pp_mm": float((x.max() - x.min()) * 1e3),
                            "free_mass_pp_mm": float(2 * F / (rm.m * w * w) * 1e3), "describe": rm.describe()}
    log(f"  reaction mass: stroke p-p {out['reaction_mass']['stroke_pp_mm']:.2f} mm (free slug {out['reaction_mass']['free_mass_pp_mm']:.2f} mm)")
    # end-cap rotor as a passive gyroscope: handle tilt response to tremor with and without spin
    res = {}
    for spin in (0.0, 20000.0):
        rot = PL.EndCapRotor(mode="gyro", spin_rpm=spin)
        cfg = P.h1_check_config(0.5).replace(plugins=[rot])
        ev = HC.Sim2Eval(0.5, cfg=cfg)
        c = ev.case(300, 8.0, 1e-3, controllers=())
        res[f"{int(spin)}rpm"] = {"unmod_e_rms_um": c["unmod_e_rms_um"], "unmod_band_um": c["unmod_band_um"]}
    out["rotor_gyro"] = {"h_mNms_at_20000": PL.EndCapRotor().h * 1e3, **res}
    log(f"  passive rotor: {res}")
    # CMG: gimbal-rate step, spin held
    rot = PL.EndCapRotor(mode="cmg")
    pm = B.build(P.h1_check_config(0.5).replace(plugins=[rot]))
    r = S.run(pm, V._still(T=T), S.RunOptions(plugin_cmd=lambda t, pm_: [np.array([5.0 if 0.2 < t < 0.3 else 0.0])]))
    out["rotor_cmg"] = {"gimbal_peak_rad": float(np.max(np.abs(r["rotor0_delta"]))),
                        "spin_change_rel": float(abs(r["rotor0_spin"][-1] / r["rotor0_spin"][0] - 1.0)),
                        "torque_expected_mNm": rot.h * 5.0 * 1e3}
    log(f"  CMG: {out['rotor_cmg']}")
    # heel drive: driven ball with native contact at the heel (the pen keeps the H1 contact law); maximum drive torque
    hd = PL.HeelDrive(kind="ball")
    pm = B.build(P.h1_check_config(0.5).replace(plugins=[hd]))
    r = S.run(pm, V._still(T=T), S.RunOptions(plugin_cmd=lambda t, pm_: [np.array([hd.tau_max if t > 0.2 else 0.0, 0.0])]))
    late = r["t"] > 0.3
    i0 = int(np.searchsorted(r["t"], 0.2))
    out["heel_drive"] = {"tau_Nm": hd.tau_max, "traction_expected_N": hd.tau_max / hd.radius,
                         "heel_N_mean": float(np.mean(r["heel_N"][late])), "heel_ft_mean": float(np.mean(r["heel_ft"][late])),
                         "mu_heel": hd.mu, "N_skid_mean": float(np.mean(r["Ns"][late])),
                         "tip_dx_mm": float((r["tipx"][-1] - r["tipx"][i0]) * 1e3),
                         "tip_dy_mm": float((r["tipy"][-1] - r["tipy"][i0]) * 1e3), "describe": hd.describe()}
    log(f"  heel drive: {out['heel_drive']}")
    # multi-plane nose: constant lateral pivot force; (a) pen lifted 3 mm (static F/k), (b) pen on the paper
    mp = PL.MultiPlaneNose()
    pm = B.build(P.h1_check_config(0.5).replace(plugins=[mp]))
    res = {}
    for lbl, lift in (("lifted", 3e-3), ("on_paper", 0.0)):
        sc = V._still(T=max(T, 0.8), N=0.0 if lift > 0 else 1.0)
        sc.pref[:, 2] = lift
        r = S.run(pm, sc, S.RunOptions(plugin_cmd=lambda t, pm_: [np.array([0.1 if t > 0.3 else 0.0, 0.0])]))
        pre = (r["t"] > 0.15) & (r["t"] < 0.3)
        post = r["t"] > r["t"][-1] - 0.3
        res[lbl] = {"slide_before_mm": float(np.mean(r["mpn_s0"][pre]) * 1e3), "slide_after_mm": float(np.mean(r["mpn_s0"][post]) * 1e3),
                    "ink_dx_mm": float((np.mean(r["ballx"][post]) - np.mean(r["ballx"][pre])) * 1e3)}
    out["multi_plane_nose"] = {"F_N": 0.1, "k_lat_N_per_m": mp.k_lat, "static_F_over_k_mm": 0.1 / mp.k_lat * 1e3, **res,
                               "describe": mp.describe()}
    log(f"  multi-plane nose: {out['multi_plane_nose']}")
    save_stage("plugins", out)


def stage_report(quick=False):
    from sim2 import report as RP
    RP.build(quick=quick, log=log)


STAGES = {"h1check": stage_h1check, "diagnose": stage_diagnose, "contact": stage_contact, "convergence": stage_convergence,
          "frontstop": stage_frontstop,
          "energy": stage_energy, "gyro": stage_gyro, "sensors": stage_sensors, "native": stage_native, "arm": stage_arm,
          "myo": stage_myo, "validate": stage_validate, "env": stage_env, "plugins": stage_plugins, "report": stage_report}
QUICK_DEFAULT = ["contact", "energy", "gyro", "sensors", "myo", "env", "plugins", "report"]


def main(argv=None):
    global QUICK
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="reduced version of the stages into results/sim2/_cache/quick/")
    ap.add_argument("--stages", default=None, help="comma-separated stages (default: all; with --quick a fast subset)")
    a = ap.parse_args(argv)
    QUICK = a.quick
    stages = a.stages.split(",") if a.stages else (QUICK_DEFAULT if QUICK else list(STAGES))
    t0 = time.time()
    for s in [x.strip() for x in stages if x.strip()]:
        ts = time.time()
        log(f"=== stage {s}{' (quick)' if QUICK else ''}")
        STAGES[s](quick=QUICK)
        log(f"=== stage {s} done in {time.time() - ts:.0f} s")
    log(f"all done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
