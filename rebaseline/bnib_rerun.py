"""Task 3: the balanced nib (B1 family) in sim2 under causal sensing, with DEC-066's servo and corrected loads
(SIMULATION, sim2 / MuJoCo through bnib/sim.py, study B's set-up, imported read-only; synthetic v2 writers, synthetic
ET tremor; DeltaPen-calibrated page sensor of study B; sim2j's frozen guarded tracker G4; nothing measured).

Configurations (one per process; each a runtime configuration of the unmodified bnib/sim.py):
  B1_studyB_now    study B's B1 as frozen (80 Hz position loop, 100 Hz inner loop, Km 0.400 N/sqrt(W), linear wires
                   3.79 N/m, 3.49 g, no guide drag) on the CURRENT code: the servo's authority gate and the firmware now
                   see the delayed measured contact (the only change from study B's own runs)
  B1_studyB_exact  the same with the historical true-contact gate and immediate firmware contact (a reproduction check)
  B1_dec066        + DEC-066's servo: 40 Hz position loop, 46 Hz inner loop
  revK_linear      + Rev K's nib constants (Km 0.3335 N/sqrt(W) x-axis at the centre, 3.44 g moving mass, wires linear
                   1.56 N/m) as study K's servo check ran them (revk/servo_sim.py variant C)
  revK_corrected   + corrected loads: Rev K's four 0.10 mm x 26.8 mm C17200 wires with the stated 10,000 N/m anchor, as a
                   nonlinear force law (revk/feasibility.wire_anchor: 11.5 mN at 1.06 mm, 18.2 mN at the 1.26 mm stop),
                   and the ball guide's rolling drag 8.07 mN (thrust_guide at 4 N preload per race, rolling coefficient
                   0.001, ASSUMPTION), acting on the carrier's velocity relative to the handle at every physics step
  cand15_corrected the 24 mm / 1.5 mm candidate of the engineering pass (results/improvement/mechanics/
                   mechanics_study.json): usable radius 1.5 mm, stop 1.7 mm, Km 0.2729 N/sqrt(W) (x-axis at the centre,
                   the same map method), 3.67 g moving mass, eight 0.10 mm x 34 mm wires with a 100 N/m anchor and 5 mN
                   assembly tension (nonlinear law), 8.07 mN guide drag; DEC-066 servo
The harmonic-load correction of bnib/loads.py (coherent spring and inertia) is automatic in a time-domain simulation;
it matters for the CALC budgets, reported beside the SIM power.  Force constants: the sim2 nib is isotropic, so the
x-axis centre value is used on both axes; the weaker y-axis and the disk minimum (and the 0.7 field derating) are given
as CALC scalings of the simulated copper loss (P = F^2 / Km^2 at the same force).
Cells: ET 8 and 12 Hz x 1 and 2 mm (study B ran 12 Hz x 2 mm only in no configuration: it is new here), tremor-free
writing, controllers none / G4 / perfect knowledge; writers 0-5 on seed TEST_SEEDS[w % 4] (study B: writers 0-3).
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import BUILD_DIR, REPO_ROOT
from . import common as CM

CELLS: Tuple[Tuple[str, float, float], ...] = (("ET", 8.0, 1.0e-3), ("ET", 8.0, 2.0e-3), ("ET", 12.0, 1.0e-3),
                                                ("ET", 12.0, 2.0e-3))
WRITERS = (0, 1, 2, 3, 4, 5)
CTLS = ("none", "nose", "oracle")
GUIDE_DRAG_N = 0.008071901379567488      # CALC revk.feasibility.thrust_guide at Rev K's worst couple, 4 N/race preload
DRAG_V0 = 0.5e-3                         # m/s regularisation of the rolling drag (ASSUMPTION; explicit-step check below)
REVK = {"Km_tip": 0.33354573489671424, "Km_y": 0.27169865452228603, "Km_disk_min_map": 0.2350, "m_move": 3.439830737727785e-3,
        "k_lin": 1.5617, "travel": 1.0586959658821008e-3,
        "wires": {"length": 26.801041139863813e-3, "diameter": 0.10e-3, "n_wires": 4, "anchor_stiffness": 10000.0,
                  "assembly_tension": 0.0},
        "source": "results/revK/revK.json nib (Km_tip_revK, m_move_g); revk/servo_sim.py (k 1.5617 N/m); "
                  "revk/feasibility.wire_anchor defaults (Rev K's wires, stated 0.01 N/um anchor)"}
CAND15 = {"Km_tip": 0.27286010296453670, "Km_y": 0.21856178524149422, "Km_disk_min_map": 0.15837233149404356,
          "m_move": 3.6699750000000002e-3, "travel": 1.5e-3, "stop": 1.7e-3,
          "wires": {"length": 34e-3, "diameter": 0.10e-3, "n_wires": 8, "anchor_stiffness": 100.0,
                    "assembly_tension": 0.005},
          "source": "results/improvement/mechanics/mechanics_study.json candidates[radius 1.5] (coil map centre, "
                    "minimum singular value, wire design, duty moving mass)"}
CONFIGS: Dict[str, Dict] = {
    "B1_studyB_now": {"nib": "B1", "servo": (80.0, 100.0), "loads": "linear", "contact": "current"},
    "B1_studyB_exact": {"nib": "B1", "servo": (80.0, 100.0), "loads": "linear", "contact": "historical"},
    "B1_dec066": {"nib": "B1", "servo": (40.0, 46.0), "loads": "linear", "contact": "current"},
    "revK_linear": {"nib": "revK", "servo": (40.0, 46.0), "loads": "linear", "contact": "current"},
    "revK_corrected": {"nib": "revK", "servo": (40.0, 46.0), "loads": "corrected", "contact": "current"},
    "cand15_corrected": {"nib": "cand15", "servo": (40.0, 46.0), "loads": "corrected", "contact": "current"},
}
HIST_ROWS = REPO_ROOT / "bnib" / "build" / "sim_rows.json"           # read-only (git-ignored historical rows)
SOURCES = ("bnib/sim.py", "bnib/candidates.py", "bnib/loads.py", "bnib/flexure.py", "bnib/thermal.py",
           "bnib/contact.py", "bnib/actuators.py", "bnib/data/vc_calibration.json", "results/bnib/bnib.json",
           "results/bnib/rules.json", "sim2/sim.py", "sim2/params.py", "sim2j/stepper.py", "sim2j/sensing.py",
           "sim2j/firmware.py", "sim2j/et.py", "results/sim2j/rules.json", "revk/feasibility.py", "results/revK/revK.json",
           "results/improvement/mechanics/mechanics_study.json", "rebaseline/bnib_rerun.py", "rebaseline/common.py")
_STATE: Dict = {}


# ------------------------------------------------------------------ nonlinear wire law and guide drag (CALC inputs)
def wire_table(w: Dict, q_max: float, n: int = 241) -> Dict:
    """Lateral force of the wire set against radial displacement (revk.feasibility.wire_anchor, self-consistent
    beam-column with the anchor in series), tabulated for the per-step force law; small-q tangent stiffness k0."""
    from revk.feasibility import wire_anchor
    q = np.linspace(0.0, q_max, n)
    F = np.array([wire_anchor(float(x), length=w["length"], diameter=w["diameter"], n_wires=w["n_wires"],
                              anchor_stiffness=w["anchor_stiffness"], assembly_tension=w["assembly_tension"])[
                  "lateral_force_N"] for x in q])
    k0 = float(F[1] / q[1])
    return {"q": q, "F": F, "k0": k0}


def extra_force(x: np.ndarray, v: np.ndarray, tab: Optional[Dict], drag: float, k0: float, v0: float = DRAG_V0) -> np.ndarray:
    """Force on the carrier (tip plane, N) that the linear model in MuJoCo lacks: the wires' nonlinear remainder
    F_wire(r) - k0 r along -x/r, and the guide's rolling drag -drag v/|v| tanh(|v|/v0).  Pure function (tested)."""
    F = np.zeros(2)
    r = float(math.hypot(x[0], x[1]))
    if tab is not None and r > 1e-12:
        Fw = float(np.interp(r, tab["q"], tab["F"])) if r <= tab["q"][-1] else float(
            tab["F"][-1] + (tab["F"][-1] - tab["F"][-2]) / (tab["q"][-1] - tab["q"][-2]) * (r - tab["q"][-1]))
        F -= (Fw - k0 * r) * x / r
    s = float(math.hypot(v[0], v[1]))
    if drag > 0 and s > 1e-15:
        F -= drag * math.tanh(s / v0) * v / s
    return F


def drag_step_check(m: float, dt: float = 50e-6, drag: float = GUIDE_DRAG_N, v0: float = DRAG_V0) -> Dict:
    """Explicit-step stability of the regularised drag (the ai3 friction defect the pass found): the velocity update
    multiplier near v = 0 is 1 - dt c / m with c = drag / v0; it must stay in (0, 1] (no sign flip, no energy gain)."""
    c = drag / v0
    mult = 1.0 - dt * c / m
    return {"c_N_s_m": c, "dt_s": dt, "mass_kg": m, "multiplier": mult, "stable_monotone": bool(0.0 < mult <= 1.0),
            "label": "CALC (linearised explicit update; the MuJoCo integrator treats qfrc_applied explicitly)"}


# ------------------------------------------------------------------ installation (runtime, this process only)
def install(config: str) -> Dict:
    if config not in CONFIGS:
        raise KeyError(config)
    if _STATE and _STATE.get("config") != config:
        raise RuntimeError("one configuration per process")
    import bnib.sim as S
    S.SETUPS = BUILD_DIR / "bnib" / "setups"                     # never study B's build folder
    cfg = CONFIGS[config]
    servo_hz, inner_hz = cfg["servo"]
    orig = S.config

    def config_fn(sd, theta_deg=50.0, dt=S.DT):
        c = orig(sd, theta_deg, dt)
        nose = replace(c.nose, servo_hz=servo_hz, inner_hz=inner_hz)
        if cfg["contact"] == "historical":
            nose = replace(nose, contact_source="legacy_force")
        geom = c.geom
        stop = _STATE.get("stop")
        if stop is not None:
            geom = replace(geom, travel_stop=stop)
        return replace(c, nose=nose, geom=geom)
    S.config = config_fn
    if cfg["contact"] == "historical":
        import sim2j.sensing as SE
        from .sim2j_cards import _historical_contact_read
        if not getattr(SE.OnlineSensors.read, "__wrapped_historical__", False):
            SE.OnlineSensors.read = _historical_contact_read(SE.OnlineSensors.read)
    loads = None
    if cfg["loads"] == "corrected":
        nib = REVK if cfg["nib"] == "revK" else CAND15
        stop = nib.get("stop", nib["travel"] + 0.2e-3)
        tab = wire_table(nib["wires"], stop + 0.3e-3)
        loads = {"tab": tab, "k0": tab["k0"], "drag": GUIDE_DRAG_N}
    _STATE.update({"config": config, "loads": loads})

    class LoadStepper(S.BStepper):
        """bnib's stepper + the nonlinear wire remainder and the guide drag as generalised forces on the nib's two
        joints (virtual pivot: tip x_i = sgn_i z_p a_i, sgn = (-1, +1); torque = sgn_i z_p F_i), every physics step."""

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            sv = self.servo
            self._qa, self._va, self._zp = list(sv.qa), list(sv.va), float(sv.zp)
            self._F_extra_rms = 0.0
            self._n_extra = 0

        def step(self):
            L = _STATE.get("loads")
            if L is not None:
                d, zp = self.d, self._zp
                x = np.array([-zp * d.qpos[self._qa[0]], zp * d.qpos[self._qa[1]]])
                v = np.array([-zp * d.qvel[self._va[0]], zp * d.qvel[self._va[1]]])
                F = extra_force(x, v, L["tab"], L["drag"], L["k0"])
                d.qfrc_applied[self._va[0]] = -zp * F[0]
                d.qfrc_applied[self._va[1]] = zp * F[1]
                self._F_extra_rms += float(F @ F)
                self._n_extra += 1
            super().step()

        def result(self):
            res = super().result()
            res.info["extra_load_rms_N"] = math.sqrt(self._F_extra_rms / max(self._n_extra, 1))
            return res
    S.BStepper = LoadStepper
    return {"config": config, **cfg, "setup_cache": str(S.SETUPS),
            "wire_k0_N_m": loads["k0"] if loads else None}


def designs(config: str):
    """The SimDesign for this configuration (study B's B1 with the frozen rules, then the nib's constants)."""
    import bnib.sim as S
    cfg = CONFIGS[config]
    ds = S.apply_rules(S.sim_designs(), S.frozen_rules())
    b1 = ds["B1"]
    servo_hz, inner_hz = cfg["servo"]
    if cfg["nib"] == "B1":
        sd = replace(b1, servo_fi=inner_hz)
        return sd, {"Km_tip": b1.ev["Km_tip"], "k_tip": b1.ev["k_tip_N_m"], "m_move": b1.ev["hw"]["m_move"],
                    "travel": b1.design.travel, "source": "study B (bnib/sim.py sim_designs + results/bnib/rules.json)"}
    nib = REVK if cfg["nib"] == "revK" else CAND15
    ev = copy.deepcopy(b1.ev)
    ev["Km_tip"] = nib["Km_tip"]
    ev["hw"] = dict(ev["hw"], m_move=nib["m_move"])
    L = _STATE.get("loads")
    k_lin = L["k0"] if L is not None else nib.get("k_lin")
    if k_lin is None:
        k_lin = wire_table(nib["wires"], nib.get("stop", nib["travel"] + 0.2e-3))["k0"]
    ev["k_tip_N_m"] = k_lin
    d = copy.deepcopy(b1.design)
    d.travel = nib["travel"]
    if "stop" in nib:
        _STATE["stop"] = nib["stop"]
    name = "B1"                                 # keep the design name: bnib's face and balance logic keys on it
    sd = replace(b1, ev=ev, design=d, servo_fi=inner_hz, name=name,
                 title=f"{cfg['nib']} nib ({'corrected loads' if cfg['loads'] == 'corrected' else 'linear wires'})")
    return sd, {"Km_tip": nib["Km_tip"], "Km_y": nib["Km_y"], "Km_disk_min_map": nib["Km_disk_min_map"],
                "k_tip_linear": k_lin, "m_move": nib["m_move"], "travel": nib["travel"],
                "stop": nib.get("stop", nib["travel"] + 0.2e-3), "wires": nib["wires"], "source": nib["source"]}


# ------------------------------------------------------------------ runs
def _key(config: str, kind: str, f0: float, amp: float, w: int, seed: int, ctl: str) -> str:
    return f"{config}|{kind}|{f0:g}|{amp * 1e3:g}|{w}|{seed}|{ctl}"


def run_writer(config: str, su, rows: CM.Rows, w: int, seed: int, cells, ctls, log=CM.log) -> None:
    import bnib.sim as S
    t0 = time.time()
    kc = f"{config}|clean|{w}|{seed}|nose"
    if not rows.has(kc):
        env = S.case_env(w, seed)
        ref = su.clean_ref(seed, env)
        r = su.run("nose", seed, env)
        m = su.metrics(r, clean_ref=ref)
        mr = su.metrics(ref)
        m.update({"kind": "clean", "w": w, "seed": seed, "ctl": "nose", "config": config, "env": env,
                  "none_P_nib_W": mr["P_nib_W"], "none_words_app": mr["words_app"], "none_battery_h": mr["battery_h"],
                  "extra_load_rms_N": r.info.get("extra_load_rms_N")})
        rows.put(kc, m, save=True)
        log(f"[{config}] w{w} s{seed} clean: moved {m['moved_vs_clean_um']:.1f} um, P nib {m['P_nib_W'] * 1e3:.1f} mW "
            f"(held {mr['P_nib_W'] * 1e3:.1f})")
    for kind, f0, amp in cells:
        keys = {c: _key(config, kind, f0, amp, w, seed, c) for c in ctls}
        if all(rows.has(k) for k in keys.values()):
            continue
        env = S.case_env(w, seed)
        tr = S._tremor(su.case, kind, f0, amp, seed)
        rn = su.run("none", seed, env, tremor=tr)
        mn = su.metrics(rn)
        rows.put(keys["none"], dict(mn, kind=kind, f0=f0, amp_mm=amp * 1e3, w=w, seed=seed, ctl="none", config=config,
                                    env=env, extra_load_rms_N=rn.info.get("extra_load_rms_N")))
        for c in ctls:
            if c == "none":
                continue
            r = su.run(c, seed, env, tremor=tr, ref_none=rn)
            mm = su.metrics(r, ref_none=rn)
            mm.update({"kind": kind, "f0": f0, "amp_mm": amp * 1e3, "w": w, "seed": seed, "ctl": c, "config": config,
                       "env": env, "none_ink_err_um": mn["ink_err_um"], "ratio": mm["ink_err_um"] / max(mn["ink_err_um"], 1e-9),
                       "none_words_app": mn["words_app"], "extra_load_rms_N": r.info.get("extra_load_rms_N")})
            rows.put(keys[c], mm)
        rows.save()
        log(f"[{config}] w{w} s{seed} {kind} {f0:g} Hz {amp * 1e3:g} mm: none {mn['ink_err_um']:.0f} um -> G4 "
            f"{rows.get(keys['nose'])['ink_err_um']:.0f} ({rows.get(keys['nose'])['ratio']:.3f})"
            + (f", oracle {rows.get(keys['oracle'])['ratio']:.3f}" if "oracle" in keys else "")
            + f"; words {mn['words_app']:.2f} -> {rows.get(keys['nose'])['words_app']:.2f}; "
              f"P {rows.get(keys['nose'])['P_nib_W'] * 1e3:.1f} mW [{time.time() - t0:.0f} s]")


def run(config: str, writers: Sequence[int] = WRITERS, cells=CELLS, ctls=CTLS, quick: bool = False, log=CM.log) -> Dict:
    info = install(config)
    import bnib.sim as S
    from bnib import TEST_SEEDS
    sd, nib = designs(config)
    if quick:
        writers, cells, ctls = tuple(writers)[:1], cells[:1], ("none", "nose")
    rows = CM.Rows(f"bnib_{config}", quick=quick)
    rows.put(f"{config}|design", {"kind": "design", "config": config, **{k: v for k, v in nib.items()},
                                  "servo_hz": CONFIGS[config]["servo"][0], "inner_hz": CONFIGS[config]["servo"][1],
                                  "loads": CONFIGS[config]["loads"], "contact": CONFIGS[config]["contact"],
                                  "wire_k0_N_m": info.get("wire_k0_N_m"),
                                  "drag_step_check": drag_step_check(nib["m_move"]) if CONFIGS[config]["loads"] == "corrected" else None},
             save=True)
    pens = S.Pens({"B1": sd})
    t0 = time.time()
    for w in writers:
        seed = TEST_SEEDS[w % len(TEST_SEEDS)]
        su = S.Setup(int(w), pens, "B1", log=log)
        if not rows.has(f"{config}|setup|{w}"):
            rows.put(f"{config}|setup|{w}", {"kind": "setup", "w": w, "adapt_hist_um": su.adapt_hist,
                                             "clean_floor": su.clean_floor}, save=True)
        run_writer(config, su, rows, int(w), seed, cells, ctls, log=log)
    rows.save()
    info.update({"writers": list(writers), "wall_s": time.time() - t0})
    log(f"[{config}] done in {info['wall_s']:.0f} s")
    return info


# ------------------------------------------------------------------ summaries
def summarise_config(R: Dict[str, Dict], writers: Optional[Sequence[int]] = None) -> Dict:
    rows = [r for r in R.values() if r.get("kind") in ("ET", "PD", "clean") and (writers is None or r.get("w") in writers)]
    tr = [r for r in rows if r.get("kind") == "ET"]
    mean = lambda L, k, sc=1.0: CM.mean_or_none(x[k] * sc for x in L if x.get(k) is not None)    # noqa: E731
    out = {"n_writers": len({r["w"] for r in tr}), "cells": {}}
    for kind, f0, amp in CELLS:
        sel = [r for r in tr if abs(r["f0"] - f0) < 1e-9 and abs(r["amp_mm"] - amp * 1e3) < 1e-9]
        n, g, o = ([r for r in sel if r["ctl"] == c] for c in CTLS)
        if not g:
            continue
        out["cells"][f"{kind} {f0:g} Hz {amp * 1e3:g} mm"] = {
            "n": len(g), "ratio_G4": mean(g, "ratio"), "ratio_G4_boot": CM.boot_mean([r["ratio"] for r in g]),
            "ratio_oracle": mean(o, "ratio"), "ink_off_um": mean(n, "ink_err_um"), "ink_G4_um": mean(g, "ink_err_um"),
            "words_off": mean(n, "words_app", 10), "words_G4": mean(g, "words_app", 10),
            "words_oracle": mean(o, "words_app", 10), "letters_off": mean(n, "letters_read", 10),
            "letters_G4": mean(g, "letters_read", 10), "P_nib_mW_off": mean(n, "P_nib_W", 1e3),
            "P_nib_mW_G4": mean(g, "P_nib_W", 1e3), "P_nib_mW_oracle": mean(o, "P_nib_W", 1e3),
            "extra_load_rms_mN_G4": mean(g, "extra_load_rms_N", 1e3)}
    g = [r for r in tr if r["ctl"] == "nose"]
    n = [r for r in tr if r["ctl"] == "none"]
    o = [r for r in tr if r["ctl"] == "oracle"]
    cl = [r for r in rows if r.get("kind") == "clean"]
    if g:
        out["pooled_4_cells"] = {"n": len(g), "ratio_G4": mean(g, "ratio"),
                                 "ratio_G4_writer_boot": CM.cluster_boot_mean([r["ratio"] for r in g], [r["w"] for r in g]),
                                 "ratio_oracle": mean(o, "ratio"), "words_off": mean(n, "words_app", 10),
                                 "words_G4": mean(g, "words_app", 10), "words_oracle": mean(o, "words_app", 10),
                                 "letters_off": mean(n, "letters_read", 10), "letters_G4": mean(g, "letters_read", 10),
                                 "P_nib_mW_G4": mean(g, "P_nib_W", 1e3), "P_nib_mW_off": mean(n, "P_nib_W", 1e3),
                                 "battery_h_G4": mean(g, "battery_h"), "T_coil_end_C_max": max(
                                     (r.get("T_coil_end_C") or float("nan") for r in g), default=None),
                                 "worse_than_off_share": float(np.mean([r["ratio"] > 1.0 for r in g]))}
    if cl:
        out["clean"] = {"n": len(cl), "moved_um_mean": mean(cl, "moved_vs_clean_um"),
                        "moved_um_max": max(r["moved_vs_clean_um"] for r in cl), "P_nib_mW": mean(cl, "P_nib_W", 1e3),
                        "P_nib_mW_held": mean(cl, "none_P_nib_W", 1e3), "words": mean(cl, "words_app", 10),
                        "battery_h": mean(cl, "battery_h")}
    return out


def studyB_published() -> Dict:
    """Study B's published B1 figures (results/bnib/bnib.json, committed) in the same cells, writers 0-3."""
    d = CM.jload(REPO_ROOT / "results" / "bnib" / "bnib.json") or {}
    c = ((d.get("sim") or {}).get("cards") or {}).get("B1") or {}
    keep = ("n_tremor_cases", "n_writers", "tremor_left_ratio_mean", "tremor_left_ratio_oracle_mean", "words_per10_nib",
            "words_per10_off", "clean_moved_um_mean", "clean_moved_um_max", "P_nib_mW_tremor_mean",
            "P_nib_mW_clean_mean", "battery_h_tremor", "battery_h_clean")
    out = {k: c.get(k) for k in keep}
    out["by_cell"] = {k: v for k, v in (c.get("by_cell") or {}).items() if k.startswith("ET 8 Hz 1") or k.startswith(
        "ET 8 Hz 2") or k.startswith("ET 12 Hz")}
    out["design"] = ((d.get("sim") or {}).get("designs") or {}).get("B1")
    out["servo_check_revK"] = (CM.jload(REPO_ROOT / "results" / "revK" / "servo_bandwidth_sim.json") or {}).get("summary")
    out["label"] = ("SIMULATION (study B: sim2 with bnib/sim.py, 80/100 Hz servo, linear wires, no guide drag, true "
                    "contact gate; writers 0-3; all 9 of its cells pooled in the top-line numbers)")
    return out


def calc_power_bands(P_sim_mW: Optional[float], nib: Dict) -> Optional[Dict]:
    """CALC: the simulated copper loss rescaled by (Km_sim / Km)^2 for the weaker axis, the disk minimum, and the 0.7
    field derating (P = F^2 / Km^2 at the same force demand)."""
    if P_sim_mW is None or "Km_y" not in nib:
        return None
    k = nib["Km_tip"]
    return {"sim_x_axis_mW": P_sim_mW, "weaker_axis_mW": P_sim_mW * (k / nib["Km_y"]) ** 2,
            "disk_minimum_mW": P_sim_mW * (k / nib["Km_disk_min_map"]) ** 2,
            "disk_minimum_derated_0p7_mW": P_sim_mW * (k / (0.7 * nib["Km_disk_min_map"])) ** 2,
            "label": "CALC on SIM (P = F^2 / Km^2 at the simulated force demand; the servo force does not depend on Km)"}


def summarise(quick: bool = False, write: bool = True) -> Dict:
    out = {"what": "the balanced nib in sim2 under causal sensing, DEC-066 servo and corrected loads (task 3; the "
                   "synthetic-input half of EXP-E23)",
           "evidence": ("SIMULATION (sim2 / MuJoCo via bnib/sim.py; synthetic v2 writers, synthetic ET tremor, study B's "
                        "DeltaPen-calibrated page sensor, sim2j's G4 tracker); nib parameters CALC / PROPOSED DESIGN"),
           "configs": {}, "studyB_published": studyB_published()}
    for c in CONFIGS:
        R = CM.Rows(f"bnib_{c}", quick=quick).rows
        if not any(r.get("kind") == "ET" for r in R.values()):
            continue
        d = R.get(f"{c}|design", {})
        s = {"setup": CONFIGS[c], "design": d, "all_writers": summarise_config(R),
             "writers_0_3": summarise_config(R, writers=(0, 1, 2, 3)), "writers_0_1": summarise_config(R, writers=(0, 1))}
        P = ((s["all_writers"].get("pooled_4_cells") or {}).get("P_nib_mW_G4"))
        s["power_bands"] = calc_power_bands(P, d)
        s["wall_s_total"] = float(sum((r.get("wall_s") or 0.0) for r in R.values()))
        out["configs"][c] = s
    hist = CM.jload(HIST_ROWS) if HIST_ROWS.exists() else None
    if hist:
        ex = CM.Rows("bnib_B1_studyB_exact", quick=quick).rows
        cmp_ = []
        for k, r in ex.items():
            if r.get("kind") != "ET":
                continue
            hk = f"test|B1|{r['kind']}|{r['f0']:g}|{r['amp_mm']:g}|{r['w']}|{r['seed']}|deltapen|{r['ctl']}"
            if hk in hist:
                cmp_.append({"key": hk, "ink_err_um_now": r["ink_err_um"], "ink_err_um_hist": hist[hk]["ink_err_um"],
                             "abs_diff_um": abs(r["ink_err_um"] - hist[hk]["ink_err_um"])})
        out["reproduction_vs_studyB_rows"] = {"n": len(cmp_), "max_abs_diff_um": max((c["abs_diff_um"] for c in cmp_), default=None),
                                              "rows": cmp_, "source": "bnib/build/sim_rows.json (read-only)"}
    if write and not quick:
        CM.write_result("bnib_rerun", out, out["evidence"], inputs=SOURCES, seeds=[200, 201, 202, 203],
                        parameters={"cells": [list(c) for c in CELLS], "writers": list(WRITERS), "controllers": list(CTLS),
                                    "configs": CONFIGS, "guide_drag_N": GUIDE_DRAG_N, "drag_v0_m_s": DRAG_V0,
                                    "revK": REVK, "cand15": CAND15})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", choices=list(CONFIGS))
    ap.add_argument("--writers", default=",".join(map(str, WRITERS)))
    ap.add_argument("--cells", default="all", help="'all' or comma list of indices into CELLS")
    ap.add_argument("--no-oracle", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args(argv)
    if a.config:
        cells = CELLS if a.cells == "all" else tuple(CELLS[int(i)] for i in a.cells.split(","))
        ctls = ("none", "nose") if a.no_oracle else CTLS
        run(a.config, [int(x) for x in a.writers.split(",") if x.strip()], cells, ctls, a.quick)
    if a.summarise:
        s = summarise(quick=a.quick)
        print(json.dumps({c: v["all_writers"].get("pooled_4_cells") for c, v in s["configs"].items()}, indent=1,
                         default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
