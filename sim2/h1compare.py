r"""Verification against model H1 (opt/inertial Rev H-B): the same cases, the same scenarios, the same metrics.

For each case (seed, tremor frequency, amplitude, kind, grip split) both models run
  reference  tremor-free writing, nose held centred;
  unmodified with tremor, nose held centred;
  oracle     the nose cancels the true deviation of the handle tip from the reference (perfect knowledge);
  causal     the fusion AKF (Rev H setting, results/opt/inertial_tracker_revh.json) estimates the disturbance from the
             unmodified run's IMU and page-sensor streams and the nose cancels the estimate (H1: stage_src 1);
and the ratio = ink error with correction / without (sim/handpen/evaluate.compare, both against the reference).
H1 is run through opt.inertial.evaluate.RevHEval (read-only code); sim2 through this package.  Pre-registered
tolerances (set before the first comparison run, docs/sim_v2.md section 5.1): oracle ratio |delta| <= 0.03,
causal ratio |delta| <= 0.05, unmodified ink error within +-10 %.  Evidence status: SIMULATION.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

import numpy as np

from sim.handpen import evaluate as HE

from . import builder as B
from . import params as P
from . import sensors as SN
from . import sim as S

TOL = {"oracle_abs": 0.03, "causal_abs": 0.05, "unmod_rel": 0.10}


def scenario(seed, f0, amp, kind="trans"):
    from opt.inertial import scen as SC
    tr = SC.tremor(f0, amp, kind) if amp > 0 else None
    return SC.get(seed, tr), SC.get(seed, None)


class Sim2Eval:
    def __init__(self, r_rot: float = 0.5, cfg: Optional[P.Config] = None, tracker: str = "revh"):
        self.cfg = cfg or P.h1_check_config(r_rot)
        self.pm = B.build(self.cfg)
        self.pm_rot = None
        self.akf = SN.revh_params() if tracker == "revh" else SN.ship_params()
        self._ref = {}

    def model(self, kind):
        if kind == "wrist":
            if self.pm_rot is None:
                cfg = self.cfg.replace(hand=P.replace(self.cfg.hand, rot_tremor=True))
                self.pm_rot = B.build(cfg)
            return self.pm_rot
        return self.pm

    def ref(self, seed, sc0, kind):
        k = (seed, kind == "wrist")
        if k not in self._ref:
            self._ref[k] = S.run(self.model(kind), sc0)
        return self._ref[k]

    def case(self, seed, f0, amp, kind="trans", controllers=("oracle", "akf")) -> Dict:
        sc, sc0 = scenario(seed, f0, amp, kind)
        pm = self.model(kind)
        n = len(sc.t)
        n_ticks = int(math.ceil(n / 20))
        ref = self.ref(seed, sc0, kind)
        un = S.run(pm, sc)
        mu = HE.compare(un, ref)
        out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "kind": kind, "unmod_e_rms_um": mu["e_rms_um"],
               "unmod_band_um": mu["e_band_rms_um"]}
        for c in controllers:
            if c == "oracle":
                clean = S.clean_ticks(ref, n_ticks)
                r = S.run(pm, sc, S.RunOptions(source="oracle", clean=clean))
            else:
                dh, info, _ = SN.akf_estimate(un, seed + 7000, self.cfg.geom.z_imu, self.akf, n_ticks=n_ticks)
                r = S.run(pm, sc, S.RunOptions(source="external", dhat=dh))
                out["akf_f_est_mean"] = float(np.mean(info["f_est"][len(info["f_est"]) // 5:]))
            m = HE.compare(r, ref)
            out[c] = {"ratio": m["e_rms_um"] / mu["e_rms_um"], "band_ratio": m["e_band_rms_um"] / mu["e_band_rms_um"],
                      "e_rms_um": m["e_rms_um"], "q_sat_frac": m["q_sat_frac"], "q_rms_um": m["q_rms_um"],
                      "P_cu_W": float(np.mean(r["Pcu"][r["t"] > 0.5]))}
        return out


class H1Eval:
    def __init__(self, r_rot: float = 0.5, tracker: str = "revh"):
        from opt.inertial import evaluate as EV, revh as RH
        from opt.inertial import run_study as RS
        prm = RS.revh_tracker_params() if tracker == "revh" else None
        self.ev = EV.RevHEval(RH.RevH(), r_rot=r_rot, akf_params=prm)

    def case(self, seed, f0, amp, kind="trans", controllers=("oracle", "akf")) -> Dict:
        return self.ev.case(seed, f0, amp, kind, controllers=controllers, power=False)


def compare_grid(cases: List[Dict], r_rot: float = 0.5, log=print, controllers=("oracle", "akf")) -> Dict:
    s2 = Sim2Eval(r_rot)
    h1 = H1Eval(r_rot)
    rows = []
    t0 = time.time()
    for c in cases:
        a = s2.case(c["seed"], c["f0"], c["amp"], c.get("kind", "trans"), controllers)
        b = h1.case(c["seed"], c["f0"], c["amp"], c.get("kind", "trans"), controllers)
        row = {"seed": c["seed"], "f0": c["f0"], "amp_mm": c["amp"] * 1e3, "kind": c.get("kind", "trans"), "r_rot": r_rot,
               "h1_unmod_um": b["unmod_e_rms_um"], "s2_unmod_um": a["unmod_e_rms_um"]}
        row["unmod_rel"] = a["unmod_e_rms_um"] / b["unmod_e_rms_um"] - 1.0
        for ctl in controllers:
            row[f"h1_{ctl}"] = b[ctl]["ratio"]
            row[f"s2_{ctl}"] = a[ctl]["ratio"]
            row[f"d_{ctl}"] = a[ctl]["ratio"] - b[ctl]["ratio"]
            row[f"s2_{ctl}_Pcu_W"] = a[ctl]["P_cu_W"]
            row[f"s2_{ctl}_qsat"] = a[ctl]["q_sat_frac"]
        rows.append(row)
        if log:
            log(f"  H1 check seed {c['seed']} {c['f0']:g} Hz {c['amp'] * 1e3:g} mm {row['kind']}: unmod {row['unmod_rel']:+.3f}, "
                + ", ".join(f"{ctl} {row[f'h1_{ctl}']:.3f}/{row[f's2_{ctl}']:.3f}" for ctl in controllers)
                + f"  ({time.time() - t0:.0f} s)")
    summ = summarise(rows, controllers)
    return {"rows": rows, "summary": summ, "tolerance": TOL}


def summarise(rows, controllers=("oracle", "akf")) -> Dict:
    out = {}
    u = np.array([r["unmod_rel"] for r in rows])
    out["unmod_rel"] = {"max_abs": float(np.max(np.abs(u))), "mean": float(np.mean(u)),
                        "pass_frac": float(np.mean(np.abs(u) <= TOL["unmod_rel"]))}
    for ctl in controllers:
        dd = np.array([r[f"d_{ctl}"] for r in rows])
        tol = TOL["oracle_abs"] if ctl == "oracle" else TOL["causal_abs"]
        out[ctl] = {"max_abs": float(np.max(np.abs(dd))), "mean": float(np.mean(dd)), "rms": float(np.sqrt(np.mean(dd ** 2))),
                    "pass_frac": float(np.mean(np.abs(dd) <= tol)), "tol": tol}
    # means over seeds per condition (the published table's convention)
    cond = {}
    for r in rows:
        k = (r["kind"], r["amp_mm"], r["f0"])
        cond.setdefault(k, []).append(r)
    out["by_condition"] = []
    for k, rs in sorted(cond.items()):
        e = {"kind": k[0], "amp_mm": k[1], "f0": k[2], "n": len(rs)}
        for ctl in controllers:
            e[f"h1_{ctl}"] = float(np.mean([r[f"h1_{ctl}"] for r in rs]))
            e[f"s2_{ctl}"] = float(np.mean([r[f"s2_{ctl}"] for r in rs]))
        out["by_condition"].append(e)
    return out


# nose actuator variants for the oracle diagnosis: the Rev H nose as modelled (400 Hz inner loop at 10 kHz, 50 us Hall
# delay, coil L/R 40 us) against idealised actuators closer to H1's kinematic stage (every-step servo, no Hall delay,
# no coil lag; then also a 2 kHz inner loop).  A 2 kHz loop with the modelled delays and 10 kHz update is unstable.
ORACLE_VARIANTS = {"no_delay_400Hz": dict(inner_hz=400.0, servo_rate=40000.0, hall_delay=0.0, L_ind=1e-8),
                   "ideal_2kHz": dict(inner_hz=2000.0, servo_rate=40000.0, hall_delay=0.0, L_ind=1e-8)}


def diagnose(rows, n_worst=3, noise_seeds=(0, 1, 2, 3, 4), r_rot=0.5, log=print, parts=("oracle", "causal")) -> Dict:
    """Attribution of the largest differences.
    Oracle: rerun the worst cases with idealised nose actuators (ORACLE_VARIANTS), which bring the dynamic nose closer
    to H1's kinematic stage; if the gap closes, it comes from the modelled actuator dynamics (bandwidth and delays).
    Causal: rerun the tracker with other sensor-noise seeds on both models' unmodified runs; if the spread within a
    model is as large as the difference between the models, the causal ratio is not a sharp comparator (the AKF's
    frequency lock is bistable)."""
    out = {"oracle": [], "causal": [], "oracle_variants": ORACLE_VARIANTS}
    worst_o = sorted(rows, key=lambda r: -abs(r["d_oracle"]))[:n_worst]
    worst_c = sorted(rows, key=lambda r: -abs(r["d_akf"]))[:n_worst]
    for r in (worst_o if "oracle" in parts else []):
        sc, sc0 = scenario(r["seed"], r["f0"], r["amp_mm"] * 1e-3, r["kind"])
        res = {"seed": r["seed"], "f0": r["f0"], "amp_mm": r["amp_mm"], "kind": r["kind"], "h1": r["h1_oracle"],
               "s2_modelled": r["s2_oracle"]}
        for vname, kw in ORACLE_VARIANTS.items():
            cfg = P.h1_check_config(r_rot)
            cfg = cfg.replace(nose=P.replace(cfg.nose, **kw))
            if r["kind"] == "wrist":
                cfg = cfg.replace(hand=P.replace(cfg.hand, rot_tremor=True))
            pm = B.build(cfg)
            ref = S.run(pm, sc0)
            un = S.run(pm, sc)
            n_ticks = int(math.ceil(len(sc.t) / 20))
            orc = S.run(pm, sc, S.RunOptions(source="oracle", clean=S.clean_ticks(ref, n_ticks)))
            m = HE.compare(orc, ref)
            res[f"s2_{vname}"] = m["e_rms_um"] / HE.compare(un, ref)["e_rms_um"]
            res[f"s2_{vname}_n_eval"] = m["n_eval"]
        out["oracle"].append(res)
        if log:
            log(f"  oracle diag {r['seed']} {r['f0']} Hz {r['amp_mm']} mm: H1 {res['h1']:.3f}, sim2 modelled nose {res['s2_modelled']:.3f}, "
                + ", ".join(f"{v} {res['s2_' + v]:.3f}" for v in ORACLE_VARIANTS))
    from opt.inertial import tracker as TK
    from sim.handpen import model as HM
    if "causal" not in parts:
        return out
    h1 = H1Eval(r_rot)
    s2 = Sim2Eval(r_rot)
    for r in worst_c:
        sc, sc0 = scenario(r["seed"], r["f0"], r["amp_mm"] * 1e-3, r["kind"])
        n = len(sc.t)
        n_ticks = int(math.ceil(n / 20))
        ev = h1.ev
        un_h = HM.run(sc, ev.cfg, rec_hz=TK.REC_HZ)
        ref_h = ev.ref(r["seed"])
        mu_h = HE.compare(un_h, ref_h)["e_rms_um"]
        pm = s2.model(r["kind"])
        ref_s = s2.ref(r["seed"], sc0, r["kind"])
        un_s = S.run(pm, sc)
        mu_s = HE.compare(un_s, ref_s)["e_rms_um"]
        rh, rs = [], []
        for j in noise_seeds:
            dh, info, _ = TK.estimate(un_h, sc, seed=r["seed"] + 7000 + 1000 * j, body="pen", z_imu=0.100, params=ev.akf_params)
            rr = HM.run(sc, ev.cfg.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
            rh.append(HE.compare(rr, ref_h)["e_rms_um"] / mu_h)
            dh2, info2, _ = SN.akf_estimate(un_s, r["seed"] + 7000 + 1000 * j, s2.cfg.geom.z_imu, s2.akf, n_ticks=n_ticks)
            rr2 = S.run(pm, sc, S.RunOptions(source="external", dhat=dh2))
            rs.append(HE.compare(rr2, ref_s)["e_rms_um"] / mu_s)
        res = {"seed": r["seed"], "f0": r["f0"], "amp_mm": r["amp_mm"], "kind": r["kind"], "h1_seeds": rh, "s2_seeds": rs,
               "h1_mean": float(np.mean(rh)), "s2_mean": float(np.mean(rs)), "h1_range": [float(min(rh)), float(max(rh))],
               "s2_range": [float(min(rs)), float(max(rs))]}
        out["causal"].append(res)
        if log:
            log(f"  causal diag {r['seed']} {r['f0']} Hz {r['amp_mm']} mm: H1 {np.round(rh, 3)} | sim2 {np.round(rs, 3)}")
    return out


def stream_comparison(seed=200, f0=8.0, amp=2.0e-3, noise_seeds=(0, 1, 2), r_rot=0.5, log=print) -> Dict:
    """The causal tracker's inputs from both models on one case: page-frame acceleration and page-sensor band powers
    (sim2 / H1), correlations, and the AKF's settled frequency estimate per sensor-noise seed.  Tells whether a causal
    difference comes from the plant (different streams) or from the tracker (same streams, different lock)."""
    from scipy.signal import welch
    from opt.inertial import tracker as TK
    from sim.handpen import model as HM
    sc, sc0 = scenario(seed, f0, amp)
    h1 = H1Eval(r_rot)
    ev = h1.ev
    un_h = HM.run(sc, ev.cfg, rec_hz=TK.REC_HZ)
    s2 = Sim2Eval(r_rot)
    un_s = S.run(s2.pm, sc)
    n_ticks = int(math.ceil(len(sc.t) / 20))
    bands = [(1, 4), (4, 7), (7, 9), (9, 12), (12, 16), (16, 30), (30, 100), (100, 400), (400, 1900)]
    out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "akf_f_max_Hz": float(ev.akf_params.get("wmax_hz", float("nan")))
           if isinstance(ev.akf_params, dict) else None, "per_noise_seed": []}
    for j in noise_seeds:
        ns = seed + 7000 + 1000 * j
        dh, info, st = TK.estimate(un_h, sc, seed=ns, body="pen", z_imu=0.100, params=ev.akf_params)
        dh2, info2, st2 = SN.akf_estimate(un_s, ns, s2.cfg.geom.z_imu, s2.akf, n_ticks=n_ticks)
        fe1, fe2 = np.asarray(info["f_est"]), np.asarray(info2["f_est"])
        out["per_noise_seed"].append({"noise_seed": ns, "f_est_h1_Hz": float(np.median(fe1[len(fe1) // 2:])),
                                      "f_est_sim2_Hz": float(np.median(fe2[len(fe2) // 2:]))})
        if j == noise_seeds[0]:
            fs = 1.0 / float(np.median(np.diff(st.acc_t)))
            n = min(len(st.acc), len(st2.acc))
            a1, a2 = st.acc[len(st.acc) // 10:n], st2.acc[len(st2.acc) // 10:n]
            f, P1 = welch(a1, fs=fs, nperseg=4096, axis=0)
            f, P2 = welch(a2, fs=fs, nperseg=4096, axis=0)
            P1, P2 = P1.sum(1), P2.sum(1)
            out["acc_band_power_sim2_over_h1"] = {f"{lo}-{hi} Hz": float(P2[(f >= lo) & (f < hi)].sum() / max(P1[(f >= lo) & (f < hi)].sum(), 1e-30))
                                                  for lo, hi in bands}
            m = min(len(a1), len(a2))
            out["acc_corr_x_y"] = [float(np.corrcoef(a1[:m, i], a2[:m, i])[0, 1]) for i in range(2)]
            p1, p2 = st.pos[len(st.pos) // 10:], st2.pos[len(st2.pos) // 10:]
            m = min(len(p1), len(p2))
            out["page_corr_x_y"] = [float(np.corrcoef(p1[:m, i], p2[:m, i])[0, 1]) for i in range(2)]
        if log:
            log(f"  streams seed {seed} {f0:g} Hz {amp * 1e3:g} mm noise {ns}: AKF settles at H1 {out['per_noise_seed'][-1]['f_est_h1_Hz']:.2f} Hz, "
                f"sim2 {out['per_noise_seed'][-1]['f_est_sim2_Hz']:.2f} Hz")
    return out

