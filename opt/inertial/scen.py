"""Scenarios for the study (H1 convention) with a small in-process cache.

writer 'lognormal': sim.pensim.scenarios.handwriting(seed) as every H1/P1 study (harness convention);
writer 'glyph'    : an aiguide glyph writer's note line (fusion.data.glyph_handwriting; sharper letters, 3-4x more
                    intended motion in 3-15 Hz; never aiguide writers 0-5 or 100-105) assembled the same way.
Tremor: hand-path TremorSpec (P1 convention) and optional wrist rotation (H1 Tremor).
Seed plan (no test leakage): tuning and training seeds >= 300 (lognormal and glyph); test seeds 200-203 only for the final
tables (see SEEDS).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from sim.handpen import model as HM
from sim.pensim import scenarios
from stabpen import signals as sg

SEEDS = {"test": (200, 201, 202, 203), "train": tuple(range(300, 316)), "val": tuple(range(316, 324)),
         "glyph_train": tuple(range(330, 338)), "glyph_test": (210, 211, 212, 213)}
DUR = 5.0
_C = {}


def _key(seed, tremor, writer, duration):
    tk = None if tremor is None else (tremor.f0, tremor.amp_trans, tremor.amp_rot, tremor.L_p, tremor.axis,
                                      tuple(sorted(tremor.spec_kw.items())))
    return (seed, tk, writer, duration)


def get(seed, tremor=None, writer="lognormal", duration=DUR):
    k = _key(seed, tremor, writer, duration)
    if k in _C:
        return _C[k]
    if writer == "lognormal":
        sc = HM.build_scenario(seed=seed, duration=duration, tremor=tremor)
    else:
        from fusion import data as FD
        it = FD.glyph_handwriting(seed, duration)
        if tremor is not None and tremor.amp_trans > 0:
            d = sg.tremor(it.t, tremor.spec(tremor.amp_trans), np.random.default_rng(seed + 1000))
        else:
            d = np.zeros_like(it.xy)
        sc = scenarios._assemble(it, d, 1.0, 50.0, meta={"kind": "glyph", "seed": seed})
        n = len(sc.t)
        psi = np.zeros(n)
        if tremor is not None and tremor.amp_rot > 0:
            spec = replace(tremor.spec(tremor.amp_rot), ellipticity=0.0, orientation=0.0)
            psi = sg.tremor(sc.t, spec, np.random.default_rng(seed + 3000))[:, 0]
        sc.psi_disp = psi
        sc.tremor_obj = tremor
    if len(_C) > 60:
        _C.clear()
    _C[k] = sc
    return sc


def tremor(f0, amp, kind="trans", L_p=0.175):
    if kind == "trans":
        return HM.Tremor(f0=f0, amp_trans=amp)
    if kind == "wrist":
        return HM.Tremor(f0=f0, amp_trans=0.0, amp_rot=amp, L_p=L_p, axis="yaw")
    if kind == "mixed":
        return HM.Tremor(f0=f0, amp_trans=amp / np.sqrt(2), amp_rot=amp / np.sqrt(2), L_p=L_p)
    raise ValueError(kind)
