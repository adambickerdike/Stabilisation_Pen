"""Fast checks of study D (about 30-60 s with a warm numba cache): pytest drive/tests -q"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest

from drive import RESULTS_DIR, REPO_ROOT, ensure_paths

ensure_paths()


# ----------------------------------------------------------------------------- evidence rows
def test_evidence_rows_match_the_ledger_header(tmp_path):
    from drive import evidence as EV
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert EV.HEADER == header and len(header) == 23
    ids = [r["id"] for r in EV.ROWS]
    assert len(ids) == len(set(ids)) >= 25
    for i in ids:
        pre, num = i.split("-")
        num = int(num)
        assert (pre, True) in {("HAP", 60 <= num <= 79), ("AMF", 100 <= num <= 119), ("CON", 36 <= num <= 45),
                               ("PAT", 30 <= num <= 34)}
    p = tmp_path / "rows.csv"
    EV.write_rows(p)
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == header and all(len(r) == 23 for r in rows)
    # Study rows have now been merged into the ledger. Reusing their IDs is
    # legitimate only for the same source, never for an unrelated citation.
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        existing = {r["id"]: r for r in csv.DictReader(f)}
    for row in EV.ROWS:
        if row["id"] in existing:
            for key in ("citation", "doi_or_url"):
                assert row[key] == existing[row["id"]][key]


# ----------------------------------------------------------------------------- geometry and contact (CALC)
def test_heel_geometry():
    from drive import geometry as GE
    r = [GE.required_contact_radius(x)["R_d_mm"] for x in (0.75, 1.0, 1.5, 2.0)]
    assert all(b > a for a, b in zip(r, r[1:]))                  # bigger element, bigger heel
    assert all(x > 6.75 for x in r)                              # never inside today's ring
    wp = GE.wheel_pod(1.0)["R_d_mm"]
    assert 8.5 < wp < 8.9
    assert abs(GE.roll_tolerance(8.4, GE.travel_for_roll(8.4, 20.0)) - 20.0) < 1e-9
    assert all(t["protrusion_mm"] > 0 for t in GE.protrusion_vs_tilt(1.0, 0.35))


def test_contact_mechanics():
    from drive import contact as CO
    ty = CO.Tyre(r_e=1.0e-3, rho=0.33e-3)
    a1, a2 = ty.hertz(0.3)["a_m"], ty.hertz(0.6)["a_m"]
    assert a2 > a1 > 0
    mu_rr = ty.rolling_resistance(0.55)
    assert 0.0 < mu_rr < 0.2
    c = CO.capacity_stats(0.55, 0.6, seeds=range(200))
    assert 0.0 <= c["share_full"] <= 1.0 and 0.0 < c["cap_mean_N"] <= 0.6 * 0.55 + 1e-12
    assert CO.paper_hold(0.5, 1.0, 0.0, 0.25)["slides"] and not CO.paper_hold(0.3, 1.0, 1.0, 0.5)["slides"]


# ----------------------------------------------------------------------------- optimisers
def test_design_gradient_matches_finite_differences():
    from drive import design_opt as DO
    for c in ("wheel", "ball"):
        assert DO.grad_check(concept=c)["max_rel_err"] < 1e-5


def test_bayes_opt_finds_a_toy_minimum():
    from drive.tune import bayes_opt
    f = lambda x: (math.log(x[0]) - math.log(3.0)) ** 2 + (x[1] - 0.2) ** 2
    r = bayes_opt(f, [(0.5, 20.0), (-1.0, 1.0)], [True, False], n_init=6, n_iter=12, seed=0)
    assert r["best_J"] < 0.05


# ----------------------------------------------------------------------------- plant
def _short_scenario():
    from drive import scenarios as S
    stroke = np.array([[20.0, 150.0], [24.0, 153.0], [28.0, 150.0], [32.0, 153.0]])
    return S.strokes_scenario([stroke], 25.0), stroke


def test_plant_matches_hw1_when_the_drive_is_off():
    from handwriting import params as PR, plant as PL
    from drive import plant as DP
    scn, _ = _short_scenario()
    pen, hand, wri = PR.rev_h(), PR.Hand.from_config(), PR.Writing()
    r0 = PL.run(scn, pen, hand, wri, PL.Controls(), seed=3, rec_hz=2000.0)
    r1 = DP.run(scn, pen, hand, wri, PL.Controls(), DP.Drive(mode="off"), seed=3, rec_hz=2000.0)
    n = min(len(r0.t), len(r1.t))
    assert np.max(np.abs(r0.ink[:n] - r1.ink[:n])) < 2e-6          # < 2 um (HW1-D = HW1 + a drive that is off)


def test_drive_force_stays_under_its_caps():
    from handwriting import params as PR, plant as PL
    from drive import plant as DP, scenarios as S
    scn, stroke = _short_scenario()
    trk = S.strokes_track([stroke + np.array([0.0, 0.6])], 25.0)      # template 0.6 mm off: the drive must act
    pen, hand, wri = PR.rev_h(), PR.Hand.from_config(), PR.Writing()
    for cond in ("sd_full", "ball_full", "wheel_path"):
        drv = S.drive_for(cond, S.Gains(), 0.6)
        r = DP.run(scn, pen, hand, wri, PL.Controls(), drv, drive_tmpl=trk.xy, drive_tdown=trk.pen_down.astype(float),
                   seed=5, rec_hz=2000.0)
        c = r.contact > 0.5
        F = np.hypot(r["Ftx"], r["Fty"])[c]                           # tyre force on the pen
        Nd = r["Nd"][c]
        assert F.max() <= 0.6 * 1.1 * Nd.max() + 1e-3                 # physics: never above mu_static x N_d
        assert np.hypot(r["Fmx"], r["Fmy"])[c].max() <= drv.F_cap * 1.2 + 0.05   # command cap (+ compensation terms)


# ----------------------------------------------------------------------------- layout and rules
def test_layout_parts_schema(tmp_path):
    from drive import layout as LY
    doc = LY.write_layout(tmp_path / "layout_parts.json")
    keys = {"id", "label", "group", "shape", "z0", "z1", "moves_with", "optional", "function", "part", "ledger"}
    for c in doc["components"]:
        assert keys <= set(c) and c["group"] == "drive" and c["shape"] in ("cylinder", "cone", "tube", "box")
        assert c["z1"] > c["z0"]
        if c["shape"] == "box":
            assert len(c["size"]) == 3
        else:
            assert c["d0"] > 0
    assert "skid_ring" in doc["meta"]["replaces"]
    assert doc["meta"]["fit_checks"]["all_pass"]
    json.dumps(doc)


def test_frozen_rules_are_intact():
    p = RESULTS_DIR / "rules.json"
    if not p.exists():
        pytest.skip("no frozen rules yet")
    import hashlib
    body = json.loads(p.read_text())
    sha = body.pop("sha256_16")
    s = json.dumps(body, sort_keys=True, default=float)
    assert hashlib.sha256(s.encode()).hexdigest()[:16] == sha


def test_lateral_release_lowers_the_steered_hold():
    """The proposed release (off in the frozen test) caps the steer-only wheel's reaction nearer the command cap."""
    from dataclasses import replace
    from drive import plant as DP, scenarios as S
    case = S.loops_case(300, hand="lightly_resisting")
    g = S.Gains()
    base = S.drive_for("sd_path", g, 1.2)
    out = {}
    for rel in (False, True):
        drv = replace(base, rel_on=rel)
        trk = case["track"]
        r = DP.run(case["scn"], case["pen"], case["hand"], S.PR.Writing(), S.nose_ctl({}, trk), drv, Ntot=case["Nt"],
                   drive_tmpl=trk.xy, drive_tdown=trk.pen_down.astype(float), seed=7300, rec_hz=2000.0)
        c = r.contact > 0.5
        F = np.hypot(r["FBx"], r["FBy"])[c]
        out[rel] = (float(np.percentile(F, 95)), float(F.max()))
    assert out[True][0] < out[False][0]
    assert out[True][1] <= out[False][1] + 1e-3
