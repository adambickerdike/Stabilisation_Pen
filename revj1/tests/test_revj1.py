"""Fast checks of the Rev J.1 study (python3 -m pytest revj1/tests -q; about 30-40 s on one core)."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import replace
from functools import lru_cache

import pytest

import revj1  # noqa: F401  (single-thread BLAS, paths)
from revj1 import REPO_ROOT, CACHE_DIR
from revj1 import evidence as EV
from revj1 import gimbal as GB
from revj1 import magnetics as MG
from revj1 import params as P1
from revj1 import power as PW
from revj1 import thermal as TH


@lru_cache(maxsize=1)
def _geo():
    from revj1 import layout as LY
    return LY.build(quick=True)


# ------------------------------------------------------------------ P1 gimbal (beam model)
def test_beam_model_reproduces_the_closed_form_stiffness():
    """Unloaded mid-length pivot: 2 EI / L = E b t^3 / (6 L) (nose2's formula), and the near-end crossing's closed form."""
    cp = GB.CrossPivot(GB.STUDY_N, 12)
    assert cp.stiffness(0.0) == pytest.approx(GB.k_elastic_closed(GB.STUDY_N), rel=1e-4)
    s2 = replace(GB.STUDY_N, lam=GB.wittrick_lambda())
    assert GB.CrossPivot(s2, 12).stiffness(0.0) == pytest.approx(GB.k_elastic_closed(s2), rel=1e-3)


def test_wittrick_point_from_the_closed_form():
    assert GB.wittrick_lambda() == pytest.approx(0.1273, abs=2e-4)
    assert abs(GB.f_lambda(GB.wittrick_lambda())) < 1e-9


def test_small_load_sensitivity_matches_the_closed_form_sign():
    """At a small load the beam model's stiffness change has the closed form's sign (tension softens a mid-length pivot)."""
    cp = GB.CrossPivot(GB.STUDY_N, 12)
    dk = cp.stiffness(0.5) - cp.stiffness(0.0)
    assert dk < 0
    assert dk == pytest.approx(GB.k_load_closed(GB.STUDY_N, 0.5), rel=0.35)


def test_studyN_pivot_buckles_near_the_pull_and_75um_does_not():
    b50 = GB.buckling_load(GB.STUDY_N, n=12)
    b75 = GB.buckling_load(GB.chosen_strip(), n=12)
    assert 15.0 < b50 < 18.0                       # at the 16.5 N upper-bound pull
    assert b75 > 2 * 22.2                          # twice the largest convention's pull
    assert b75 / b50 == pytest.approx(1.5 ** 3, rel=0.1)


def test_tension_near_end_fails_fatigue_and_chosen_passes():
    t = GB.design_row(GB.TENSION_NEAR_END, 16.5, n=12)
    c = GB.design_row(GB.chosen_strip(), -16.5, n=12)
    assert t["goodman_SF_1e8"] < 1.0
    assert c["goodman_SF_1e8"] > 1.5 and c["k_beam_model_mNm_rad"] > 0


def test_thrust_pivot_friction_is_large_at_the_ball():
    tp = GB.thrust_pivot_options(16.5)
    ok = [r for r in tp["sliding"] if r["pressure_ok"]]
    assert ok and min(r["friction_at_tip_mN"] for r in ok) > 20.0


# ------------------------------------------------------------------ P1/P6 magnetics
def test_pull_reproduces_revj_and_spacer_trade():
    base = MG.pull_and_B(grid_n=81)
    sp = MG.pull_and_B(spacer=0.5, grid_n=81)
    assert base["pull_N"] == pytest.approx(16.5, rel=0.03)
    assert sp["pull_N"] < 0.7 * base["pull_N"]
    assert sp["B_coil_T"] / base["B_coil_T"] < 0.9          # the force constant falls too


def test_air_core_loses_force_constant():
    a = MG.pull_and_B(air_core=True, grid_n=41)
    b = MG.pull_and_B(grid_n=41)
    assert a["B_coil_T"] / b["B_coil_T"] < 0.7


def test_back_iron_has_margin_at_1p5_mm():
    b = MG.back_iron_flux(n=61)
    r = [x for x in b["rows"] if abs(x["t_mm"] - 1.5) < 1e-9][0]
    assert 1.0 < r["B_mean_T"] < 1.5 and r["B_peak_T_est"] < 2.4


def test_cup_shielding_formula_limits():
    assert MG.cup_shielding(1.0, 0.2) == pytest.approx(1.0)
    assert MG.cup_shielding(2000.0, 0.2, 3.2) == pytest.approx(1 + 2000 * 0.2 / (2 * 3.2), rel=0.1)


def test_detent_falls_when_the_motors_move_back():
    d = MG.detent(_geo(), quick=True)
    assert d["worst_torque_amp_mNm"] < 0.080                 # below Rev J's |B| bound at the Rev J.1 position already
    assert d["moving_back"][-1]["torque_amp_mNm"] < d["moving_back"][0]["torque_amp_mNm"]


# ------------------------------------------------------------------ P2 power
def test_electronics_bottom_up_below_revJ_assumption():
    e = PW.electronics()
    assert e["total_W"][0] < e["total_W"][1] < e["revJ_W"]
    assert e["nose_halls_W"][0] == pytest.approx(2 * 2e-3 * 3.7)


def test_low_power_page_sensor():
    p = PW.page_options()
    assert p["PMW3610_class"][1] < 0.1 * p["PMW3360_1kHz"][0]


def test_sixteen_mm_cell_does_not_fit_beside_the_motors():
    assert PW.cells()["16mm_beside_motors"]["feasible"] is False


def test_coil_power_scales_with_the_factor():
    base = PW.modes(3.9, 1.017, 0.007, {}, factor=1.0)
    x2 = PW.modes(3.9, 1.017, 0.007, {}, factor=2.0)
    for k in base:
        assert x2[k]["nose_coil_W"] == pytest.approx(2 * base[k]["nose_coil_W"])


# ------------------------------------------------------------------ P3 heat
def test_spreader_resistance_bounds():
    assert TH.chosen_R() < 0.5 * TH.R_bare(2.6)
    rows = TH.spreader_options(0.17, 2.6)["rows"]
    g = [r for r in rows if r["material"] == "PGS_graphite" and r["t_mm"] == 0.1 and r["L_mm"] == 30.0][0]
    al = [r for r in rows if r["material"] == "Al_6061" and r["t_mm"] == 0.5 and r["L_mm"] == 30.0][0]
    assert g["R_K_W"] == pytest.approx(al["R_K_W"], rel=0.05) and g["mass_g"] < 0.1 * al["mass_g"]


def test_skin_limit_is_from_the_opened_standard():
    assert P1.SKIN["held_max_C"].value == 43.0 and "ECMA-287" in P1.SKIN["held_max_C"].source


# ------------------------------------------------------------------ integration
def test_layout_passes_fit_checks_and_budgets():
    g = _geo()
    assert g["fit_checks"]["all_pass"]
    assert g["length_with_endcap"] <= 175.0
    from revj import budgets as RBU
    mb = RBU.mass_budget(g)
    assert mb["with_endcap"]["mass_g"] <= 120.0
    assert mb["base"]["mass_g"] < 87.0


def test_endcap_cache_reproduces_studyK_if_present():
    p = CACHE_DIR / "full" / "endcap_test.json"
    if not p.exists():
        pytest.skip("end-cap SIM cache not built (python3 -m revj1.endcap_mass)")
    d = json.loads(p.read_text())
    v = d["verdicts"]["lrm_14.98"]
    ref = json.loads((REPO_ROOT / "results" / "endcap" / "endcap_study.json").read_text())["recommendation"]["verdicts"]["lrm"]
    for k in ("r0.3", "r0.5", "r0.7"):
        assert v[k] == pytest.approx(ref[k], abs=1e-9)


def test_evidence_rows_have_the_ledger_header_and_ids_in_range():
    h = EV.header()
    assert len(h) == 23
    ids = [r["id"] for r in EV.ROWS]
    assert len(set(ids)) == len(ids)
    for i in ids:
        pre, num = i.split("-")
        rng = {"AMF": (155, 179), "OPT": (60, 69), "ACT": (105, 119), "CON": (70, 74), "HAP": (110, 114),
               "PDT": (59, 62), "PAT": (45, 49)}[pre]
        assert rng[0] <= int(num) <= rng[1]
    # An id already in the ledger must be this study's own row, merged by the lead unchanged (same citation and URL);
    # any other clash is an id collision.
    ledger = {r["id"]: r for r in csv.DictReader(open(REPO_ROOT / "docs" / "evidence.csv", encoding="utf-8", newline=""))}
    for r in EV.ROWS:
        if r["id"] in ledger:
            assert ledger[r["id"]]["citation"] == r["citation"]
            assert ledger[r["id"]]["doi_or_url"] == r["doi_or_url"]
