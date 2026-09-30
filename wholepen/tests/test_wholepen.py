"""Fast checks of study W (well under a minute): pytest wholepen/tests -q"""
from __future__ import annotations

import csv
import math
import os
import re

import numpy as np
import pytest

import wholepen
from wholepen import ROOT


# ----------------------------------------------------------------------------- the linear model
def test_lin_reproduces_hap26_tip_impedance():
    """The two-zone grip + hand, massless pen: the tip's static stiffness is HAP-26's 575 N/m in series with the arm."""
    from wholepen import lin as L
    for r in (0.3, 0.5, 0.7):
        h = L.HandP(r_rot=r)
        c = L.tip_compliance_H1(h, 0.05)
        k_expected = 1.0 / (1.0 / h.k_nib + 1.0 / h.k_arm)
        assert abs(1.0 / c.real - k_expected) / k_expected < 0.02


def test_cmg_coupling_is_conservative():
    """The CMG pair's gyroscopic coupling adds a skew-symmetric block to D (no work)."""
    from wholepen import lin as L
    mdl = L.Model(cmg=[L.CMGPair(h=5e-3, J_g=2e-6, out="t1")])
    asm = L.Assembly(mdl)
    mdl0 = L.Model(cmg=[L.CMGPair(h=0.0, J_g=2e-6, out="t1")])
    D = (asm.D - L.Assembly(mdl0).D).numpy()
    assert np.allclose(D, -D.T, atol=1e-12)
    assert np.max(np.abs(D)) > 0


def test_v2_collar_ink_is_kinematic_at_low_frequency():
    """V2 collar: the ball slides on its refill, so a pivot angle about t2 moves the ink by z_p / sin(theta) (page x)."""
    from wholepen import lin as L
    th = 50.0
    zp = 0.05
    mdl = L.Model(theta_deg=th, collar=L.Collar(z_p=zp, K_c=50.0, c_c=0.01, skid_on_collar=True), c_paper=0.0,
                  hand=L.HandP(grip_scale=20.0))
    asm = L.Assembly(mdl)
    X = asm.solve(2 * math.pi * 0.2, asm.u_collar(asm.t2) * 50.0)
    ink = asm.ink(X).detach().numpy()
    expected = zp / math.sin(math.radians(th))
    assert abs(abs(ink[0]) - expected) / expected < 0.1


# ----------------------------------------------------------------------------- calculations
def test_nose_static_load_reproduces_the_review():
    from wholepen import calc as K
    P = {r["theta_deg"]: r["P_W"] for r in K.nose_static()["rows"]}
    assert abs(P[35.0] - 4.717) < 0.01 and abs(P[50.0] - 1.628) < 0.01 and abs(P[75.0] - 0.166) < 0.005


def test_review_gyroscope_example():
    """A solid 20 g, 6 mm radius rotor at 30 000 rpm: h 1.13 mN m s, 1.78 J; 12.4 mN m at 5 Hz with a 20 deg swing."""
    from wholepen import calc as K
    r = next(x for x in K.cmg_sizing()["rows"] if x["name"].startswith("review 20 g"))
    assert abs(r["h_Nms"] - 1.131e-3) < 2e-6
    assert abs(r["E_J_total"] - 1.777) < 0.005
    assert abs(r["torque_5Hz_20deg_mNm_one_rotor"] - 12.4) < 0.1


def test_pair_torque_closed_form():
    from wholepen import designs as DS
    from scipy.special import j1
    h, f = 4e-3, 6.0
    w = 2 * math.pi * f
    assert abs(DS.pair_torque(h, f, 1.0, 1e9) - 2 * h * w * 2 * j1(1.0)) < 1e-12


def test_collar_geometry_fits_the_review_envelope():
    from wholepen import calc as K
    r = next(x for x in K.collar_geometry()["rows"] if x["z_p_mm"] == 50.0 and x["travel_mm"] == 4.0 and x["path"] == "V2")
    assert 21.0 < r["collar_od_mm"] <= 22.0
    assert abs(r["swing_deg"] - math.degrees(4.0 / 50.0)) < 1e-9


def test_reaction_mass_force_formula():
    from wholepen import calc as K
    rm = K.reaction_mass(m=0.030, X=4e-3, f_tunes=(0.0,), freqs=(5.0,))
    r = rm["rows"][0]
    assert abs(r["shell_force_N"] - 0.030 * (2 * math.pi * 5) ** 2 * 4e-3) < 1e-12
    assert abs(r["shell_force_N"] - 0.118) < 0.001            # the review's table


# ----------------------------------------------------------------------------- control laws and metrics
def test_phasor_imc_total_mode():
    from wholepen import control as C
    f = np.array([4.0, 8.0])
    G = np.array([np.eye(2, dtype=complex)] * 2)
    imc = C.PhasorIMC(f, G, gain=1.0, total=True)
    u = imc.step(np.array([1e-3, -2e-3]), 6.0, True)
    assert np.allclose(u, [-1e-3, 2e-3])


def test_ink_completeness_counts_missing_strokes():
    from wholepen import cases as CS

    class R(dict):
        def ink(self):
            return self["ink"]
    t = np.arange(0, 10, 0.01)
    c_ref = ((t > 5) & (t < 6)) | ((t > 7) & (t < 8))
    ink = np.column_stack([t * 1e-3, 0 * t])
    ref = R(t=t, contact=c_ref.astype(float), ink=ink)
    c = c_ref.copy()
    c[(t > 7) & (t < 8)] = False                              # the second stroke is lost
    r = R(t=t, contact=c.astype(float), ink=ink)
    m = CS.ink_completeness(r, ref, t0=4.0)
    assert m["n_strokes"] == 2 and m["missing_strokes"] == 1
    assert abs(m["coverage"] - 0.5) < 0.02


def test_strokes_from_trace_merges_contact_flicker(tmp_path):
    """The reported stroke metric: the writer's intended strokes; contact flicker shorter than 40 ms is not a lost
    stroke, a stroke inked less than half is."""
    from wholepen import cases as CS
    t = np.arange(0, 10, 0.004)
    down = ((t > 5) & (t < 6)) | ((t > 7) & (t < 8))
    c = down.copy()
    for k in range(20):                                        # 12 ms flicker every 50 ms in the first stroke
        c[(t > 5.0 + 0.05 * k) & (t < 5.012 + 0.05 * k)] = False
    c[(t > 7) & (t < 7.7)] = False                             # the second stroke 70 % lost
    xy = np.column_stack([t * 1e-3, 0 * t])
    fn = tmp_path / "trace.npz"
    np.savez(fn, t=t, ink=xy, contact=c.astype(float), it_t=t, it_xy=xy, it_down=down.astype(float))
    m = CS.strokes_from_trace(str(fn), t0=4.0)
    assert m["n_strokes"] == 2 and m["missing_strokes"] == 1 and m["lost_pieces"] == 1
    assert abs(m["coverage_intended"] - 0.65) < 0.02


def test_lin_gradient_in_the_pivot_position():
    """lin.py's Jacobians are differentiable in the collar's pivot position (optimise.py's gradient check)."""
    import torch
    from wholepen import calc as K, lin as L

    def resid(zp):
        mdl = L.Model(hand=L.HandP(r_rot=0.5), pen=dict(K.compact_pen("coil")), c_paper=1.0,
                      collar=L.Collar(z_p=float(zp.detach()), K_c=4.02, c_c=0.035, m=0.02, z_cm=0.056, J=1.2e-5,
                                      skid_on_collar=True))
        asm = L.Assembly(mdl, par={"z_p": zp})
        w = 2 * math.pi * 6.0
        d = asm.ink(asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * 3e-3)))
        return torch.sqrt((torch.abs(d) ** 2).sum())
    z = torch.tensor(0.05, requires_grad=True, dtype=torch.float64)
    v = resid(z)
    v.backward()
    e = 1e-5
    fd = (resid(torch.tensor(0.05 + e, dtype=torch.float64)) - resid(torch.tensor(0.05 - e, dtype=torch.float64))) / (2 * e)
    assert abs(float(z.grad) - float(fd)) <= 1e-4 * max(abs(float(fd)), 1e-12) + 1e-12


# ----------------------------------------------------------------------------- the simulator model
def test_collar_hinges_on_t1_t2_and_skid_on_collar():
    from wholepen import cases as CS, devices as DV
    pm = CS.PenVariant("test_collar", collar=dict(z_p=0.050)).build()
    assert DV.collar_axes(pm) == (1.0, 1.0)
    assert pm.m.geom_bodyid[pm.ids["geom:skid0"]] == pm.ids["body:collar"]


# ----------------------------------------------------------------------------- deliverables
def test_evidence_rows_header_and_ids():
    from wholepen import evidence as E
    hdr = next(csv.reader(open(os.path.join(ROOT, "docs", "evidence.csv"))))
    assert E.HEADER == hdr
    ledger = {r["id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "docs", "evidence.csv")))}
    ranges = {"ACT": (120, 139), "AMF": (180, 199), "HAP": (115, 129), "PDT": (63, 74), "CON": (75, 79), "PAT": (50, 54),
              "OPT": (70, 74)}
    rows = E._lit() + E._derived()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    for i in ids:
        pre, n = i.split("-")
        lo, hi = ranges[pre]
        assert lo <= int(n) <= hi, i
    for row in rows:
        if row["id"] in ledger:
            for key in ("citation", "doi_or_url"):
                assert row[key] == ledger[row["id"]][key]


def test_labels_on_every_result_file():
    import json
    d = os.path.join(ROOT, "results", "wholepen")
    if not os.path.isdir(d):
        pytest.skip("no results yet")
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            body = json.load(open(os.path.join(d, fn)))
            assert "stabpen.provenance" in body or "stabpen.provenance" in body.get("meta", {}), fn
