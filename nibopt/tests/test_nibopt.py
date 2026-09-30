"""Tests of study N (nibopt): the fast field against magpylib, the force map against the pass's winding_map, the
reproductions of study K's and the pass's numbers, the fin model, the duty model's limits, the evidence rows."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nibopt import duty as DU  # noqa: E402
from nibopt import evaluate as E  # noqa: E402
from nibopt import evidence as EV  # noqa: E402
from nibopt import magnet as M  # noqa: E402
from nibopt import optimise as O  # noqa: E402
from nibopt import pen as PN  # noqa: E402
from nibopt import reconcile as RC  # noqa: E402
from nibopt import suspension as SU  # noqa: E402
from nibopt.design import reconciliation_designs  # noqa: E402


def test_bz_matches_magpylib():
    import magpylib as magpy
    rng = np.random.default_rng(0)
    P = rng.uniform(-8e-3, 8e-3, (400, 3))
    P[:, 2] = rng.uniform(4e-3, 6e-3, 400)
    S = np.array([[1e-3, -2e-3, 1.5e-3, 2.5e-3, 2e-3, 1.75e-3, 1.42], [-3e-3, 3e-3, -2e-3, 1e-3, 1.5e-3, 0.5e-3, -1.2]])
    ref = np.zeros(len(P))
    for s in S:
        ref += magpy.magnet.Cuboid(polarization=(0, 0, s[6]), dimension=(2 * s[3], 2 * s[4], 2 * s[5]),
                                   position=(s[0], s[1], s[2])).getB(P)[:, 2]
    assert np.abs(M.bz(P, S) - ref).max() < 1e-12


def test_force_map_matches_pass_winding_map():
    from bnib.magnetics import ChkGeom
    from revk.feasibility import CoilShape, winding_map
    gK = ChkGeom(w=5.120275187158268e-3, e=2.233535337181825e-3, t_m=3.5e-3, t_x=0.8e-3, t_y=0.8e-3, s=1.2587e-3)
    pos = np.array([[0.0, 0.0], [1.0587e-3, 0.0], [0.7486e-3, 0.7486e-3]])
    for order in ("xy", "xyyx"):
        ref = winding_map(gK, CoilShape(2.35e-3, 1.0726e-3, 2.2e-3, 5.0e-3), pos, order, quadrature=(2, 1, 6))
        fm = M.force_map(M.Magnets(w=gK.w, e=gK.e, t_m=gK.t_m, t_cu=1.6e-3), M.Coil(2.35e-3, 1.0726e-3, 2.2e-3, 5.0e-3,
                                                                                  order), pos, quad=(2, 1, 6))
        assert np.abs(ref["wrench_per_sqrtW"][:, :2, :] - fm["K"]).max() < 1e-12


def test_fast_quadrature_converged():
    g = M.Magnets(w=5.120275187158268e-3, e=2.233535337181825e-3, t_m=3.5e-3, t_cu=1.6e-3)
    c = M.Coil(2.35e-3, 1.0726e-3, 2.2e-3, 5.0e-3, "xy")
    pos = M.disk_positions(1.0587e-3, 8)
    fast = M.force_map(g, c, pos, quad=(2, 1, 6), n_img=2)["sv_min"].min()
    ref = M.force_map(g, c, pos, quad=(6, 3, 24), n_img=3)["sv_min"].min()
    assert abs(fast / ref - 1) < 3e-3


def test_k_residual_reproduced():
    kr = DU.k_residual()
    assert kr["reproduces_K"]
    assert kr["rms_N"] >= kr["mean_N"]


def test_k_moving_mass_and_pass_lengths():
    ds = reconciliation_designs()
    assert abs(ds["K_B1"].m_move_g() - 3.4398) < 1e-3
    assert abs(ds["K_B1"].length_mm() - 145.13) < 0.01
    assert abs(ds["P_150_24"].length_mm() - 152.33) < 0.01
    assert abs(ds["P_1059_24"].length_mm() - 148.33) < 0.01


def test_k_chain_reproduced_per_axis():
    """Study K's scalar chain (study B's model x 1.80 x 1.21) equals this package's per-axis model averaged over roll."""
    w = RC.waterfall_K()
    s = {x["name"]: x["P_mW"] for x in w["steps"]}
    assert abs(s["all rolls"] / s["coherent harmonic load"] - 1) < 1e-6
    assert abs(s["K as published"] - 16.63) < 0.05


def test_pass_screen_reproduced():
    d = reconciliation_designs()["P_150_24"]
    fm = E.force_map(d, fine=True, n_ang=48)
    w = RC.waterfall_pass("P_150_24", d, fm)
    st = {x["name"]: x["P_W"] for x in w["steps"]}
    assert abs(st["the pass's function re-run"] / st["the pass as published"] - 1) < 1e-9
    assert abs(st["this package, the pass's loads"] / st["the pass as published"] - 1) < 2e-3


def test_fin_model_matches_study_k():
    from revk.budgets import surface_rise as ksr
    src = [{"z0": 21.4, "z1": 29.9, "P": 0.08}, {"z0": 35.5, "z1": 58.3, "P": 0.043}, {"z0": 10.2, "z1": 15.2, "P": 0.002}]
    for z in (10.0, 26.0, 32.0, 38.0, 92.0):
        assert abs(PN.surface_rise(z, src, 24.0) - ksr(z, src)) < 1e-12


def test_coherent_harmonic_zero_at_resonance():
    d = reconciliation_designs()["K_B1"]
    ctx = E.context(d, E.force_map(d))
    m = ctx.m
    w = 2 * math.pi * 8.0
    k = m * w * w
    from dataclasses import replace
    c2 = replace(ctx, fw=lambda q: k * np.abs(np.asarray(q, float)), fd=lambda th: 0.0)
    mm = DU.motion_moments(c2, "circle", 0.2, 8.0)
    assert np.abs(mm["dyn"]).max() < 1e-12


def test_temp_factor_monotonic_and_clamped():
    vals = [PN.temp_factor(T, T) for T in (20, 40, 80, 150, 200, 400, 2000)]
    assert vals[0] == pytest.approx(1.0)
    assert all(b >= a for a, b in zip(vals[:5], vals[1:5]))
    assert vals[-1] == vals[-2] == vals[4]


def test_wire_force_nonlinear_with_stiff_anchor():
    f_stiff = SU.wire_force_law(4, 0.10, 26.801, 10000.0, 1.6)(1.2587e-3)
    f_soft = SU.wire_force_law(4, 0.10, 26.801, 100.0, 1.6)(1.2587e-3)
    assert f_stiff > 5 * f_soft


def test_guide_drag_falls_with_preload():
    hi = SU.ball_guide(8.3, 4.0)["drag_35_mN"]
    lo = SU.ball_guide(8.3, 1.0)["drag_35_mN"]
    assert 7.5 < hi < 8.5 and lo < hi / 2


def test_screening_rejects_flexures():
    sc = SU.screen_topologies(1.7)
    struts = [r for r in sc["rows"] if r["topology"].startswith("necked")][0]
    assert struts["best_with_buckling_margin_2"]["goodman_Kt1.8"] < 1.5
    planar = [r for r in sc["rows"] if r["topology"].startswith("two planar")][0]
    assert planar["tilt_mrad"] > 10.0


def test_evaluate_constraints_and_items_add_up():
    d = reconciliation_designs()["P_1059_24"]
    ev = E.evaluate(d, fine=False, full=False)
    items = ev["dutyA"]["worst07"]["mean_items_W"]
    assert abs(sum(items.values()) - ev["dutyA"]["worst07"]["mean"]) < 1e-9 * max(1.0, ev["dutyA"]["worst07"]["mean"])
    assert set(O.SCALES) <= set(ev["constraints"])


def test_optimiser_build_and_dominance():
    for x in O.seeds():
        d, why = O.build(x)
        assert d is None or d.reach_mm >= 1.0
    a = {"V": 0.0, "F": [0, 1, 1, 1, 1]}
    b = {"V": 0.1, "F": [-9, 0, 0, 0, 0]}
    assert O._dominates(a, b) and not O._dominates(b, a)


def test_evidence_rows_format(tmp_path):
    p = EV.write(tmp_path / "rows.csv")
    chk = EV.check(p)
    assert chk["header_ok"] and chk["crlf"] and chk["ids_in_range"]
    assert set(chk["n_columns"]) == {23}
