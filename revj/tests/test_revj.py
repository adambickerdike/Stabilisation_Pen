"""Fast checks of the Rev J integration (pytest revj/tests -q; about 20-30 s on one core)."""
from __future__ import annotations

import json
import math
import os
from dataclasses import replace
from functools import lru_cache

import numpy as np
import pytest

from revj import REPO_ROOT, budgets as BU, frontend as FR, magnetics as MG, packaging as PK, params as PA, refill as RF


@lru_cache(maxsize=1)
def _fe():
    return FR.close(FR.Heel(), n_theta=9, n_phi=24)


@lru_cache(maxsize=1)
def _geo():
    return PK.build(_fe(), quick=True)


# ------------------------------------------------------------------ front end
def test_pod_solver_reproduces_study_D():
    """With the Rev H nose's envelope, the pod solver gives study D's own contact radius (drive/geometry.wheel_pod)."""
    from drive import geometry as DG
    env = lambda R: (DG.envelope(R)["s_mm"], DG.envelope(R)["r_mm"])     # noqa: E731
    mine = FR.pod_contact_radius(env, FR.Heel())["R_d_mm"]
    assert abs(mine - DG.wheel_pod(1.0)["R_d_mm"]) < 1e-3
    assert abs(mine - 8.676) < 0.01


def test_nose_only_matches_study_N():
    c = FR.close(None, nz0=FR.c1s_nose(), keep_angle=True, n_theta=9, n_phi=24, sleeve_step=0.75)
    assert c["R_mm"] == pytest.approx(10.0)
    assert c["refill_slide_range_mm"] == pytest.approx(24.4, abs=0.15)
    assert c["ball_travel_usable_min_mm"] == pytest.approx(6.0, abs=0.02)


def test_integrated_closure_passes_every_rule():
    fe = _fe()
    assert fe["R_d_mm"] == pytest.approx(12.0)
    assert fe["R_mm"] == pytest.approx(11.65)
    assert fe["ball_travel_usable_min_mm"] >= 6.0 - 2e-3
    assert all(v >= -1e-9 for v in fe["rule_margins_mm"].values())
    assert fe["sleeve_front_d_mm"] <= 24.0


def test_bigger_ring_needs_more_angle():
    """Keeping study N's angle with the heel's ring loses guaranteed travel (the ball sits further ahead of the ring)."""
    c = FR.close(FR.Heel(), nz0=FR.c1s_nose(), keep_angle=True, n_theta=9, n_phi=24)
    assert c["ball_travel_usable_min_mm"] < 5.95
    assert _fe()["X_nom_mm"] > PA.nose_design()["X_nom"]


def test_window_height_formula_invariant_point():
    dr, s = 2.47 * math.cos(math.radians(55.0)), 2.47 * math.sin(math.radians(55.0))
    h = FR.window_height(11.65, s, 11.65 - dr, 0.0, np.linspace(35, 75, 9))
    assert np.all(np.abs(h - 2.4) < 0.1)


def test_visibility_runs():
    fe = _fe()
    nz = replace(FR.c1s_nose(), X=fe["X_nom_mm"])
    v = FR.visibility(fe["R_mm"], nz, FR.Heel(), thetas=(50.0,), n_dir=8, d_step=0.5)
    assert set(v["50"]) == set(FR.EYES)
    side = v["50"]["side_view"]
    assert 0.0 <= side["share_directions_visible_within_3mm"] <= 1.0


# ------------------------------------------------------------------ layout
def test_layout_schema_and_fit_checks():
    geo = _geo()
    fc = geo["fit_checks"]
    assert fc["all_pass"], {k: v for k, v in fc.items() if isinstance(v, (int, float)) and v < 0}
    for c in geo["components"]:
        assert c["group"] in PK.GROUPS, c["id"]
        assert c["moves_with"] in PK.MOVES, c["id"]
        assert c["shape"] in ("cylinder", "cone", "tube", "box"), c["id"]
        assert c["z1"] > c["z0"], c["id"]
        if c["group"] == "inertial":
            assert c["optional"] is True
    assert any(c.get("replaced_by_endcap") for c in geo["components"])
    assert geo["length"] <= 175.0 and geo["length_with_endcap"] <= 175.0
    ids = [c["id"] for c in geo["components"]]
    assert len(ids) == len(set(ids))


def test_round1_drive_parts_collide_with_the_c1s_nose():
    r = PK.round1_conflicts(_fe())["parts"]
    assert r["drive_motor"]["collides"] and r["drive_motor"]["worst_overlap_mm"] > 1.5
    assert r["drive_shaft_drive"]["collides"]


def test_motors_are_behind_the_actuator_and_under_the_cell():
    geo = _geo()
    c = {x["id"]: x for x in geo["components"]}
    assert c["drive_motor"]["z0"] > c["coil_plate"]["z1"]
    assert c["battery"]["z0"] <= c["drive_motor"]["z0"] and c["drive_motor"]["z1"] <= c["battery"]["z1"]
    assert c["main_board"]["z1"] < c["gimbal"]["z0"]


# ------------------------------------------------------------------ refill
def test_refill_holder_stays_in_front_of_the_cap():
    geo = _geo()
    sl = geo["_internal"]["refill"]["slide"]
    assert sl["fits"]
    assert sl["holder_rear_max_z_mm"] < PA.nose_design()["cap_front"] - 0.3


def test_spiral_spring_meets_force_and_fatigue():
    sp = RF.spiral_spring(27.4)
    ch = sp["chosen"]
    assert ch is not None and ch["fits"]
    assert sp["force_range_N"][0] == pytest.approx(0.12) and sp["force_range_N"][1] == pytest.approx(0.18)
    assert ch["SF_small"] >= 1.3 and ch["SF_large"] >= 1.2
    assert ch["sigma_max_MPa"] <= 0.55 * 1460 + 1


# ------------------------------------------------------------------ budgets
def test_mass_budget_consistent():
    geo = _geo()
    mb = BU.mass_budget(geo)
    base_parts = sum((c.get("mass_g") or 0) for c in geo["components"] if c["group"] != "inertial") * 1.1
    assert mb["base"]["mass_g"] == pytest.approx(base_parts, rel=1e-6)
    assert mb["with_endcap"]["mass_g"] == pytest.approx(mb["base"]["mass_g"] - mb["rear_cap_removed_g"] + mb["endcap_g"], rel=1e-6)
    assert mb["with_endcap"]["com_mm"][2] > mb["base"]["com_mm"][2]


def test_nose_coil_power_matches_study_N_duty():
    assert BU.nose_coil_power(1.0)["P_W"] == pytest.approx(PA.nose_design()["P_tremor_W"], rel=0.05)


def test_power_hours_consistent():
    pw = BU.power_modes(1.0)
    E = pw["energy_Wh"]
    for m in pw["modes"].values():
        assert m["hours"][0] == pytest.approx(E / m["total_W"][1])
        assert m["total_W"][0] <= m["total_W"][1]


def test_power_options_gating_and_energy():
    pw = BU.power_modes(1.0)
    o = BU.power_options(pw, 144.72, 165.72)
    for k, v in o["page_sensor_gated_in_steady_modes"].items():
        assert v["hours"][0] > pw["modes"][k]["hours"][0]
    need = o["energy_needed"]
    assert need["steady_no_tremor"]["vs_cell"] < 1.0 < need["autowrite_1mm"]["vs_cell"]
    assert need["autowrite_1mm"]["cell_length_for_8h_mm"] > PA.POWER["cell_l_mm"].value


# ------------------------------------------------------------------ magnetics
def test_field_helper_shape_and_axial_pull_order():
    col = MG.c1s_cap()
    assert MG.field_at(col, [0.0, 0.0, 100.0]).shape == (1, 3)
    ap = MG.axial_pull(n=61)
    assert 5.0 < ap["F_axial_N_images"] < 40.0


# ------------------------------------------------------------------ outputs (if the pipeline has been run)
@pytest.mark.parametrize("name", ["layout.json", "budgets.json", "sim_params.json", "frontend.json", "refill.json",
                                  "magnetics.json", "revJ.json"])
def test_result_files_have_provenance(name):
    p = REPO_ROOT / "results" / "revJ" / name
    if not p.exists():
        pytest.skip("run python3 -m revj.run first")
    d = json.loads(p.read_text())
    assert "stabpen.provenance" in d
    if name == "sim_params.json":
        for k in ("nose", "refill", "heel_wheel", "endcap", "handle", "skid_ring", "sensors"):
            assert k in d["sim_params"]
