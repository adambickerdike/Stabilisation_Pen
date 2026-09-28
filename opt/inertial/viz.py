"""3-D replay of Rev H cases in the schema of results/pencil/inertial_viz.json (sim/handpen/run_study.viz; converted by
viewer/build.py stab_trace).  Default: seed 200 (test), 8 Hz, 0.3 mm hand tremor, window 1.0-3.5 s at 200 Hz; a second file
at 10 Hz / 1.0 mm (the regime Rev H is for).  Frames as the H1 replay; the 'pen' of H1 is the Rev H handle, the stage q
is the active nose's tip deflection relative to the handle.  Evidence status: SIMULATION.
"""
from __future__ import annotations

import os

import numpy as np

from sim.handpen import evaluate as HE
from sim.handpen import model as HM
from sim.handpen import params as HP
from stabpen import provenance
from . import addon as AD
from . import addon_eval as AE
from . import control as CL
from . import geometry as GE
from . import revh as RH
from . import scen as SC
from . import tracker as TK

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _f4(x):
    return float(f"{x:.5g}")


def _arr(x, scale=1.0):
    return [[_f4(v * scale) for v in row] for row in np.asarray(x)]


def build(seed=200, f0=8.0, amp=0.3e-3, t0=1.0, t1=3.5, rate=200.0, akf_params=None):
    d = RH.RevH()
    rm = AE.default_rm()
    cfg0 = RH.config_B(d)
    cfgR = RH.config_B(d, device=rm)
    sc0 = SC.get(seed)
    sc = SC.get(seed, SC.tremor(f0, amp))
    n = len(sc.t)
    ref0 = HM.run(sc0, cfg0, rec_hz=TK.REC_HZ)
    refR = HM.run(sc0, cfgR, rec_hz=TK.REC_HZ)
    un = HM.run(sc, cfg0, rec_hz=TK.REC_HZ)
    runs, refs = {"unmodified": un}, {"unmodified": ref0}
    runs["nose_oracle"] = HM.run(sc, cfg0.replace(stage=True), clean=HM.clean_at_sim_rate(ref0, n), rec_hz=TK.REC_HZ)
    refs["nose_oracle"] = ref0
    dh, info, _ = TK.estimate(un, sc, seed=seed + 7000, body="pen", params=akf_params)
    runs["nose"] = HM.run(sc, cfg0.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
    refs["nose"] = ref0
    unR = HM.run(sc, cfgR, rec_hz=TK.REC_HZ)
    dhR, infoR, _ = TK.estimate(unR, sc, seed=seed + 7000, body="pen", params=akf_params)
    u = np.zeros((n, 3))
    u[:, 0:2] = TK.to_steps(AD.ff_phasor(dhR, infoR["f_est"], d, rm), n)
    rR = HM.run(sc, cfgR, uff=u, rec_hz=TK.REC_HZ)
    runs["reaction_mass"], refs["reaction_mass"] = rR, refR
    dh2, _, _ = TK.estimate(rR, sc, seed=seed + 7000, body="pen", params=akf_params)
    runs["nose+reaction_mass"] = HM.run(sc, cfgR.replace(stage=True, stage_src=1), uff=u, clean=TK.to_steps(dh2, n), rec_hz=TK.REC_HZ)
    refs["nose+reaction_mass"] = refR
    # architecture A (rigid nose carrying the load, the 'grip pivot' family) with the shipped tracker, for comparison
    dA = RH.RevH(arch="A")
    msA = RH.masses(dA)
    blocks, _ = CL.tip_servo_A(dA.lever, 50.0, msA["nose_inertia_about_pivot_g_mm2"] * 1e-9 / (dA.z_a - dA.z_p) ** 2, f_bw=dA.servo_hz)
    cfgA = RH.config_A(dA).replace(ctl=CL.ctl_spec(blocks, Ts=2e-4, imu=dict(pos_nd=0.2e-6, lat_ticks=1),
                                                     ulim=[0, 0, 0, dA.F_peak_act, dA.F_peak_act, 0, 0]))
    uA = np.zeros((n, 7))
    refA = HM.run(sc0, cfgA, uff=uA, rec_hz=TK.REC_HZ)
    unA = HM.run(sc, cfgA, uff=uA, rec_hz=TK.REC_HZ)
    dhA, _, _ = TK.estimate(unA, sc, seed=seed + 7000, body="sleeve", params=akf_params)
    uA2 = uA.copy(); uA2[:, 3:5] = TK.to_steps(dhA, n)
    runs["nose_A"], refs["nose_A"] = HM.run(sc, cfgA, uff=uA2, rec_hz=TK.REC_HZ), refA
    desc = {
        "unmodified": "Rev H pen (22 mm handle), nose held centred: the ink carries the hand tremor minus what the skid friction absorbs.",
        "nose_oracle": "Active nose (architecture B) with perfect knowledge of the tremor: the ceiling of the mechanism (+/-3 mm travel).",
        "nose": "Active nose driven by the accelerometer tracker (Rev H setting): what a real pen could do (causal).",
        "reaction_mass": "Rear-cap tungsten reaction mass (19.8 g, +/-2.75 mm) driven by the tracker estimate through a model inverse; the nose held centred.",
        "nose+reaction_mass": "Active nose plus the rear-cap reaction mass, both causal (the evaluated rear-cap module; not fitted in the standard Rev H).",
        "nose_A": "Architecture A (the whole nose carries the writing load, no skid) with its position servo and the same tracker: rejected (more power, lower ceiling, writing-force changes).",
    }
    labels = {"unmodified": "Rev H, no correction", "nose_oracle": "Active nose, perfect knowledge", "nose": "Active nose (tracker)",
              "reaction_mass": "Reaction mass only (tracker)", "nose+reaction_mass": "Nose + reaction mass (tracker)",
              "nose_A": "Architecture A nose (rejected)"}
    order = ["unmodified", "nose_oracle", "nose", "reaction_mass", "nose+reaction_mass", "nose_A"]
    tr_ = runs["unmodified"]["t"]
    sel = np.where((tr_ >= t0) & (tr_ < t1))[0]
    dec = int(round((1.0 / (tr_[1] - tr_[0])) / rate))
    sel = sel[::dec]
    a, t1v, t2v, nvec, h = HP.geometry_vectors(50.0)
    intended = np.column_stack([np.interp(tr_[sel], sc.t, sc.intended[:, 0]), np.interp(tr_[sel], sc.t, sc.intended[:, 1])])
    base_m = HE.compare(runs["unmodified"], ref0)
    cases = []
    for key in order:
        r, ref = runs[key], refs[key]
        m = HE.compare(r, ref)
        if key == "nose_A":
            b1, b2 = r["sb1"][sel], r["sb2"][sel]
            nib = np.column_stack([r["bx"][sel], r["by"][sel], r["bz"][sel] - HP.CONTACT["r_b"]])
            grip = np.column_stack([r["sx"][sel], r["sy"][sel], r["sz"][sel]]) + d.z_f * a[None, :]
            ink = r.ink()[sel]
            mA = HE.compare(unA, refA)
            ratio = m["e_rms_um"] / mA["e_rms_um"]
        else:
            b1, b2 = r["b1"][sel], r["b2"][sel]
            nib = np.column_stack([r["bx"][sel], r["by"][sel], r["bz"][sel] - HP.CONTACT["r_b"]])
            grip = np.column_stack([r["gfx"][sel], r["gfy"][sel], r["gfz"][sel]])
            ink = r.ink()[sel]
            ratio = m["e_rms_um"] / base_m["e_rms_um"]
        axis = a[None, :] + b1[:, None] * t1v[None, :] + b2[:, None] * t2v[None, :]
        axis /= np.linalg.norm(axis, axis=1)[:, None]
        dev = {"type": "active_nose"}
        if key in ("reaction_mass", "nose+reaction_mass"):
            dev = {"type": "reaction_mass", "r_pen_frame_m": _arr(np.column_stack([r["r1"][sel], r["r2"][sel], r["r3"][sel]])),
                   "force_N": _arr(np.column_stack([r["Fd1"][sel], r["Fd2"][sel], r["Fd3"][sel]]))}
        if key.startswith("nose") and key != "nose_A":
            dev["stage_q_m"] = _arr(np.column_stack([r["q1"][sel], r["q2"][sel]]))
        if key == "nose_A":
            # tip deflection of the rigid nose relative to the handle (t1, t2) from the actuator displacement
            dev = {"type": "active_nose_A", "stage_q_m": _arr(-np.column_stack([r["pd1"][sel], r["pd2"][sel]]) * dA.lever),
                   "actuator_force_N": _arr(np.column_stack([r["pf1"][sel], r["pf2"][sel]]))}
        rsel = np.searchsorted(ref["t"], tr_[sel]).clip(0, len(ref["t"]) - 1)
        ref_nib = np.column_stack([ref["bx"][rsel], ref["by"][rsel], ref["bz"][rsel] - HP.CONTACT["r_b"]])
        cases.append({"key": key, "label": labels[key], "description": desc[key], "nib": _arr(nib), "axis": _arr(axis),
                      "tilt_rad": _arr(np.column_stack([b1, b2])), "grip": _arr(grip), "ref_nib": _arr(ref_nib),
                      "ref_ink": _arr(ref.ink()[rsel]), "ink": _arr(ink), "pen_down": [int(v > 0) for v in r["contact"][sel]],
                      "device": dev,
                      "metrics": {"ink_err_rms_um": _f4(m["e_rms_um"]), "band_rms_um": _f4(m["e_band_rms_um"]),
                                  "ratio_vs_unmodified": _f4(ratio), "q_sat_frac": _f4(m["q_sat_frac"])}})
    geo = GE.layout(d)
    g = {"length": geo["length"], "od": geo["handle_od"], "theta_deg": 50.0, "finger_zone_z": [geo["grip_zone"]["z0"], geo["grip_zone"]["z1"]],
         "finger_zone_centre": d.z_f * 1e3, "web_zone_centre": d.z_w * 1e3, "skid_ring_radius": geo["skid_contact_radius"],
         "front_opening_d": geo["front_opening_d"], "pivot_z": geo["pivot_z"], "actuator_z": geo["actuator_z"],
         "tip_travel": geo["tip_travel_mm"], "lever_tip_per_magnet": geo["lever_tip_per_magnet"],
         "cell_z": [c for c in geo["components"] if c["id"] == "battery"][0]["z0"],
         "reaction_mass": {"z_centre": rm.z * 1e3, "d": 10.0, "L": 14.0, "stroke_lateral": rm.stroke[0] * 1e3, "stroke_axial": 0.0},
         "layout_file": "results/revH/layout.json",
         "device_types": {
             "active_nose": "the refill carrier tilts on a 2-axis flexure gimbal at pivot_z inside the fixed handle; device.stage_q_m = "
                            "the ball's deflection relative to the handle along t1, t2 (ink moves q1/sin(theta) along x, q2 along y); the "
                            "magnets at actuator_z move the other way by q/lever",
             "reaction_mass": "tungsten slug in the rear cap on flexures, moved on 2 lateral axes by flat voice coils; r_pen_frame_m = its "
                              "displacement relative to the handle along t1, t2, a; force_N = the coil force",
             "active_nose_A": "architecture A (rejected): the whole nose incl. the ball carries the writing load; stage_q_m = the tip "
                              "deflection relative to the handle; the handle itself is the grip sleeve (grip = handle point at the finger pads)"}}
    meta = provenance.metadata("SIMULATION (hand-pen model H1 with the Rev H handle; synthetic handwriting and tremor; nothing measured)",
                               seeds={"handwriting": seed, "tremor": seed + 1000, "tracker_noise": seed + 7000},
                               extra={"model_version": HM.MODEL_VERSION + "+revH",
                                      "scenario": f"sim.pensim.scenarios.handwriting(seed={seed}, duration=5.0, TremorSpec(f0={f0}, amp_pk={amp}), N0=1.0)",
                                      "window_s": [t0, t1], "rate_Hz": rate, "geometry_mm": g,
                                      "frames": {"page": "x right, y up the page, z out of the page", "pen": "a = axis tip->cap at 50 deg; t1 tilt plane; t2 = y",
                                                 "nib": "ball contact point of the handle's nominal tip (the nose centred)",
                                                 "ink": "page projection of the ball with the nose deflection",
                                                 "grip": "handle point at the finger pads"},
                                      "evidence": {"grip": "LIT HAP-26 calibration + ASSUMPTION split r_rot 0.5", "tracker": "fusion AKF, Rev H setting (SIM)",
                                                   "devices": "PROPOSED DESIGN (CALC masses, MFR parts)", "results": "SIMULATION"},
                                      "cases": {k: desc[k] for k in order}})
    return {"meta": meta, "units": {"length": "m", "time": "s", "angle": "rad", "force": "N", "torque": "N m"},
            "t": [_f4(v) for v in tr_[sel]], "intended": _arr(intended), "cases": cases}


def write(akf_params=None):
    out = os.path.join(ROOT, "results", "opt", "viz_inertial_opt.json")
    v = build(akf_params=akf_params)
    provenance.write_json(out, v)
    v2 = build(f0=10.0, amp=1.0e-3, akf_params=akf_params)
    provenance.write_json(out.replace(".json", "_1mm.json"), v2)
    return {c["key"]: c["metrics"] for c in v["cases"]}, {c["key"]: c["metrics"] for c in v2["cases"]}
