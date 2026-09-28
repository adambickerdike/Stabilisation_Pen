"""The pencil model P1 on the harness grid for any stage (built-in or registered).

Harness conventions of sim/pencil/run_study.py (and sim/pensim/harness.py):
  * reference ink = the same pencil in NEUTRAL mode on the same handwriting without tremor;
  * ratio = e_rms(mode, tremor) / e_rms(neutral, tremor), both against that reference;
  * the oracle receives the clean housing path (neutral, no tremor) as its disturbance reference
    (M.housing_disturbance / M.with_disturbance);
  * scenarios.handwriting(seed, duration, tremor=TremorSpec(f0, amp_pk), N0=1.0), test seeds 200-203.
Extra per-axis stage statistics (rms deflection and velocity on the evaluated samples) are recorded for the
calibration of the drive-power model in opt/hardware/model.py.
Everything here is a SIMULATION on synthetic signals; nothing is measured.
"""
from __future__ import annotations

import contextlib
import math
import time

import numpy as np

from . import ROOT  # noqa: F401  (sys.path)
import sim.pencil  # noqa: E402,F401  (numba cache outside sim/pensim)
from sim.pencil import design as D  # noqa: E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

SEEDS = (200, 201, 202, 203)
F0S = (4.0, 6.0, 8.0, 10.0, 12.0)
AMPS = (0.1e-3, 0.3e-3, 0.5e-3)
DUR = 5.0


@contextlib.contextmanager
def pencil_params_overlay(overrides: dict | None):
    """Run P1 with config/pencil.yaml values overridden (dotted keys, e.g. 'skid.ring_radius') without
    editing the file: model.py reads its parameters through M._base_params(), which is patched here."""
    if not overrides:
        yield
        return
    orig = M._base_params

    def patched():
        P = D.Params()
        P.pencil = P.pencil.with_overrides(overrides)
        return P

    M._base_params = patched
    try:
        yield
    finally:
        M._base_params = orig


def pencil_config(stage_key: str, **kw) -> "M.PencilConfig":
    """PencilConfig for a stage; for a registered stage the pen mass comes from its CAD mass x 1.1
    (wiring and adhesives, as model.py does for the Q CAD) unless given."""
    if stage_key not in D.STAGE_VARIANTS and "pen_mass" not in kw:
        spec = D.registered_stages().get(stage_key, {})
        m = spec.get("cad", {}).get("mass_total_g")
        if m is not None:
            kw["pen_mass"] = float(m) * 1.1e-3
    return M.PencilConfig(stage_key=stage_key, **kw)


def _axis_stats(res, ref):
    m, fs, n = E._mask(res, ref)
    q = res.xy("q1")[:n]
    dq = np.gradient(q, 1.0 / fs, axis=0)
    V = res.xy("V1")[:n]
    dV = np.gradient(V, 1.0 / fs, axis=0)
    if not m.any():
        return {}
    return {"q1_rms_um": float(np.sqrt(np.mean(q[m, 0] ** 2)) * 1e6), "q2_rms_um": float(np.sqrt(np.mean(q[m, 1] ** 2)) * 1e6),
            "q1dot_rms_mm_s": float(np.sqrt(np.mean(dq[m, 0] ** 2)) * 1e3), "q2dot_rms_mm_s": float(np.sqrt(np.mean(dq[m, 1] ** 2)) * 1e3),
            "V1_mean": float(np.mean(V[m, 0])), "V2_mean": float(np.mean(V[m, 1])),
            "V1dot_rms_V_s": float(np.sqrt(np.mean(dV[m, 0] ** 2))), "V2dot_rms_V_s": float(np.sqrt(np.mean(dV[m, 1] ** 2)))}


def run_seed(stage_key: str, seed: int, f0s=F0S, amps=AMPS, modes=("oracle",), duration=DUR, cfg_kw=None,
             ctrl_kw=None, scn_kw=None, params_overrides=None):
    """One seed of the grid: reference, then neutral and each mode for every (f0, amp)."""
    cfg_kw = dict(cfg_kw or {})
    ctrl_kw = dict(ctrl_kw or {})
    scn_kw = dict(scn_kw or {})
    rows = []
    with pencil_params_overlay(params_overrides):
        cfg = pencil_config(stage_key, **cfg_kw)
        sc0 = scenarios.handwriting(seed=seed, duration=duration, N0=1.0, **scn_kw)
        ref = M.run(sc0, M.Controller(mode="neutral", **ctrl_kw), cfg, seed=seed)
        for f0 in f0s:
            for amp in amps:
                sc1 = scenarios.handwriting(seed=seed, duration=duration, N0=1.0,
                                            tremor=sg.TremorSpec(f0=f0, amp_pk=amp), **scn_kw)
                d_clean = M.housing_disturbance(sc1, ref)
                rn = M.run(sc1, M.Controller(mode="neutral", **ctrl_kw), cfg, seed=seed)
                base = E.compare(rn, ref)
                rows.append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "mode": "neutral", "ratio": 1.0,
                             **base, **_axis_stats(rn, ref)})
                for mode in modes:
                    if mode == "oracle":
                        r = M.run(M.with_disturbance(sc1, d_clean), M.Controller(mode="oracle", **ctrl_kw), cfg, seed=seed)
                    else:
                        r = M.run(sc1, M.Controller(mode=mode, **ctrl_kw), cfg, seed=seed)
                    mm = E.compare(r, ref)
                    mm["ratio"] = mm["e_rms_um"] / base["e_rms_um"]
                    rows.append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "mode": mode, **mm, **_axis_stats(r, ref)})
    return rows


def run_grid(stage_key: str, seeds=SEEDS, **kw):
    t0 = time.time()
    rows = []
    for s in seeds:
        rows += run_seed(stage_key, s, **kw)
    return rows, time.time() - t0


def summarise(rows, keys=("ratio", "q_sat_frac", "P_rail_classB_mW", "P_rail_recovery_mW", "e_rms_um")):
    """Mean and sd over seeds per (mode, f0, amp)."""
    out = {}
    for r in rows:
        k = (r["mode"], r["f0"], r["amp_mm"])
        out.setdefault(k, []).append(r)
    summ = {}
    for (mode, f0, amp), rs in sorted(out.items()):
        d = summ.setdefault(mode, {})
        for key in keys:
            v = [x[key] for x in rs if key in x and x[key] is not None and not (isinstance(x[key], float) and math.isnan(x[key]))]
            if v:
                d.setdefault(key, {})[f"{f0:g}Hz_{amp:g}mm"] = {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)}
    return summ


def warm():
    """Compile / load the numba core once in this process."""
    M.run(scenarios.handwriting(seed=1, duration=0.3), M.Controller(mode="neutral"))
