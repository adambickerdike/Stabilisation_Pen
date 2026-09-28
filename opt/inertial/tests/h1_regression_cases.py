"""Regression cases for the hand-pen model H1 (sim/handpen): the default behaviour must stay bit for bit.

`make_baseline()` was run on the unmodified sim/handpen (git 77e39e3, before opt/inertial extended it) and wrote
tests/data/h1_baseline.json: a SHA-256 of every recorded array (and of the ILC oracle's input) for cases that cover
every code path of the original core (no device, nib stage, active reaction mass, CMG, passive tuned mass, passive
gyroscope, fixed cap mass, locked rotation, wrist-rotation tremor, voluntary correction, viscous nose, soft grip)
plus the linear model's frequency responses.  test_h1_regression.py recomputes them after the extension.
Run once, by hand, on an unmodified tree only:  python3 -m opt.inertial.tests.h1_regression_cases --write
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import sim.handpen  # noqa: E402,F401
from sim.handpen import devices as DV  # noqa: E402
from sim.handpen import linear as L  # noqa: E402
from sim.handpen import model as HM  # noqa: E402
from sim.handpen import params as HP  # noqa: E402

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "h1_baseline.json")
DUR = 1.5
SEED = 311


def _sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a, dtype=np.float64)).tobytes()).hexdigest()


def _orig(rec):
    """The channels that existed before the extension (appended channels are excluded; they are checked to be zero)."""
    from sim.handpen import core
    n0 = getattr(core, "NREC_ORIG", rec.shape[1])
    return rec[:, :n0]


def _uff(n, amp, f=8.0, cols=3, dt=HM.DT):
    t = np.arange(n) * dt
    u = np.zeros((n, 3))
    for j in range(cols):
        u[:, j] = amp * np.sin(2 * np.pi * f * t + 0.7 * j)
    return u


def cases():
    """(name, scenario tremor, cfg, uff amplitude, uses clean reference)"""
    b = HP.Config()
    tr8 = HM.Tremor(f0=8.0, amp_trans=0.3e-3)
    rot = HM.Tremor(f0=10.0, amp_trans=0.0, amp_rot=0.3e-3, L_p=0.175, axis="yaw")
    pit = HM.Tremor(f0=8.0, amp_trans=0.0, amp_rot=0.3e-3, L_p=0.175, axis="pitch")
    return [
        ("none_clean", None, b, 0.0, False),
        ("none_tremor", tr8, b, 0.0, False),
        ("stage", tr8, b.replace(stage=True), 0.0, True),
        ("rm_slug3_uff", tr8, b.replace(device=DV.rm_slug(axes=3)), 0.03, False),
        ("rm_slug3_uff_stage", tr8, b.replace(device=DV.rm_slug(axes=3), stage=True), 0.03, True),
        ("rm_cell", tr8, b.replace(device=DV.rm_cell()), 0.01, False),
        ("cmg_2ax_uff", tr8, b.replace(device=DV.cmg_pair()), 1.0e-3, False),
        ("cmg_lat_stage", tr8, b.replace(device=DV.cmg_pair(axes=(0, 1)), stage=True), 1.0e-3, True),
        ("tmd_8", tr8, b.replace(device=DV.tmd_slug(8.0)), 0.0, False),
        ("gyro_30k", tr8, b.replace(device=DV.gyro_rotor(30000.0)), 0.0, False),
        ("cap_10g", tr8, b.replace(device=DV.cap_mass(10.3e-3)), 0.0, False),
        ("locked", tr8, b.replace(lock_rotation=True), 0.0, False),
        ("rot_yaw_stage", rot, b.replace(stage=True), 0.0, True),
        ("rot_pitch", pit, b, 0.0, False),
        ("voluntary", tr8, b.replace(voluntary=True), 0.0, False),
        ("visc_soft", tr8, b.replace(c_visc=10.0, grip_scale=0.5, grip_damp_add=3.0), 0.0, False),
        ("split_0.7_0.1_mu", tr8, b.replace(r_rot=0.7, rho_w=0.1, mu_skid=0.25), 0.0, False),
        ("tilt35", tr8, b.replace(theta_deg=35.0), 0.0, False),
    ]


def compute():
    out = {}
    sc0 = HM.build_scenario(seed=SEED, duration=DUR)
    for name, tr, cfg, amp, use_clean in cases():
        sc = sc0 if tr is None else HM.build_scenario(seed=SEED, duration=DUR, tremor=tr)
        n = len(sc.t)
        ref = HM.run(sc0, cfg.replace(stage=False))
        clean = HM.clean_at_sim_rate(ref, n) if use_clean else None
        uff = _uff(n, amp) if amp > 0 else None
        r = HM.run(sc, cfg, uff=uff, clean=clean)
        out[name] = {"rec_sha256": _sha(_orig(r.rec)), "shape": list(_orig(r.rec).shape),
                     "appended_all_zero": bool(not np.any(r.rec[:, _orig(r.rec).shape[1]:])),
                     "ink_rms_um": float(np.sqrt(np.mean(np.sum((r.ink() - ref.ink()[:len(r.ink())]) ** 2, axis=1))) * 1e6)}
    # ILC oracle (model.py path): two iterations, reaction mass and CMG
    tr = HM.Tremor(f0=10.0, amp_trans=0.3e-3)
    sc = HM.build_scenario(seed=SEED, duration=DUR, tremor=tr)
    for name, dv in (("ilc_rm", DV.rm_slug(axes=3)), ("ilc_cmg", DV.cmg_pair())):
        cfg = HP.Config(device=dv)
        ref = HM.run(sc0, cfg)
        res, u, hist = HM.ilc_oracle(sc, cfg, ref, n_iter=2, stage_cfg=cfg.replace(stage=True))
        out[name] = {"rec_sha256": _sha(_orig(res.rec)), "u_sha256": _sha(u), "hist": [float(h) for h in hist]}
    # linear model
    for name, cfg in (("lin_none", HP.Config()), ("lin_rm", HP.Config(device=DV.rm_slug(axes=3))),
                      ("lin_gyro", HP.Config(device=DV.gyro_rotor(30000.0), r_rot=0.3))):
        lm = L.LinearModel(cfg)
        f = np.array([4.0, 8.0, 12.0])
        X = lm.frf(f, lambda w: lm.exc_translation(np.array([1.0, 0.0, 0.0]), w))
        out[name] = {"frf_sha256": _sha(np.column_stack([X.real, X.imag]))}
    return out


def make_baseline(path=BASELINE):
    import subprocess
    rev = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "sim/handpen"], capture_output=True, text=True).stdout.strip()
    data = {"note": "SHA-256 of sim/handpen outputs recorded BEFORE opt/inertial extended sim/handpen; see h1_regression_cases.py",
            "git_revision": rev, "sim_handpen_modified_at_recording": bool(dirty), "numpy": np.__version__,
            "cases": compute()}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    return data


if __name__ == "__main__":
    if "--write" in sys.argv:
        d = make_baseline()
        print(json.dumps({k: v.get("rec_sha256", v.get("frf_sha256"))[:16] for k, v in d["cases"].items()}, indent=1))
    else:
        print(json.dumps(compute(), indent=1)[:2000])
