"""Tests of study K (the Rev K integrated layout).  Run: python3 -m pytest revk/tests -q

They check the models against closed forms, the layout's consistency and the files' formats; they do not check that the
design is good (the fit checks and budgets report that).  About half a minute on one core."""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from revk import REPO_ROOT, clean, write_json
from revk import params as PR
from revk.params import V, val

LABELS = {PR.MFR, PR.LIT, PR.CALC, PR.SIM, PR.ASM, PR.PD, "MFR", "LIT", "CALC", "SIM"}


def _walk(d):
    for k, v in d.items():
        if isinstance(v, V):
            yield k, v
        elif isinstance(v, dict):
            yield from _walk(v)


@pytest.fixture(scope="module")
def chain():
    from revk import budgets as BU, counterface as CF, frontend as F, layout as LY, nib as N
    fc = F.front_close(heel=False, quick=True)
    fc_h = F.front_close(heel=True, quick=True)
    hd = CF.design(fc["R_s_mm"], quick=True)
    coil = N.buildable_coil(quick=True)
    base = LY.base_components(fc, hd, coil)
    ns = N.summary(fc["R_s_mm"], base, quick=True)
    stack = CF.face_stack(n=2000)
    hand = F.hand(fc["R_s_mm"])
    lay = LY.build(fc, fc_h, hd, coil, ns, stack, hand)
    bud = BU.summary(lay, ns, hd)
    return {"fc": fc, "fc_h": fc_h, "hd": hd, "coil": coil, "ns": ns, "lay": lay, "bud": bud, "stack": stack}


def test_every_input_is_labelled():
    from revk import layout as LY, tolerance as TL
    tabs = [PR.B1, PR.ENVELOPE, PR.FRONT, PR.NIB, PR.HEAD, PR.FACE_STACK, PR.ELEC, PR.MODES, PR.THERMAL, LY.LAY,
            TL.SENSING, TL.MECH]
    n = 0
    for t in tabs:
        for k, v in _walk(t):
            assert v.label in LABELS, (k, v.label)
            assert v.source, k
            n += 1
    assert n > 80
    for row in PR.COST:
        assert row[4] in LABELS and row[5]


def test_protrusion_closed_form():
    from revk.frontend import protrusion
    for th in (35.0, 50.0, 75.0):
        t = math.radians(th)
        assert protrusion(th, 6.0) == pytest.approx((6.0 * math.cos(t) - 0.35) / math.sin(t))


def test_front_end_base(chain):
    fc = chain["fc"]
    assert fc["R_s_mm"] == pytest.approx(6.0)
    assert fc["window"]["phi_deg"] == 0.0                 # the page sensor at the bottom of the ring
    lo, hi = fc["band_mm"]["roll0"]
    assert 2.2 - 1e-9 <= lo <= hi <= 2.6 + 1e-9           # OPT-61 lens band over 35-75 deg
    assert fc["roll_tolerance_deg"] >= 20.0


def test_head_kinematics_refill_end_moves_parallel_to_face():
    from revk.counterface import Head
    h = Head(6.0, -6.0, -9.0)
    rng = np.random.default_rng(0)
    for th in (35.0, 50.0, 75.0):
        zO = h.z_O(th)
        c0 = h.contact(th, 0.0, (0.0, 0.0), zO)
        assert c0["f"] == pytest.approx(0.0, abs=1e-9)
        assert c0["u"] == pytest.approx(h.u_nominal(th), abs=1e-9)
        for _ in range(5):
            q = rng.uniform(-1.2, 1.2, 2)
            psi = rng.uniform(-20, 20)
            c = h.contact(th, psi, q, zO)
            assert c["f"] == pytest.approx(0.0, abs=1e-9)   # the nib's correction does not load the float


def test_contact_line_hinge_needs_no_follower():
    """z_O constant when the hinge sits on the ring's paper-side generator and L_O = -(r_b + r_pb) (closed form)."""
    from revk.counterface import Head
    R = 6.0
    h = Head(R, -(0.35 + 1.0), -R)
    z = [h.z_O(t) for t in np.linspace(35, 75, 9)]
    assert max(z) - min(z) == pytest.approx(0.0, abs=1e-9)


def test_head_design_fits(chain):
    hd = chain["hd"]
    assert hd["positioner_travel_needed_mm"] <= 6.0 - val(PR.HEAD["follower_spare_mm"]) + 1e-9
    assert hd["swept_r_max_mm"] <= 11.0 - 0.3 + 1e-9
    assert hd["loads"]["tilt"]["margin_x"] > 1.5          # with the balance spring
    assert hd["lift"]["holding_energy_J"] == 0.0


def test_face_stack_reproducible():
    from revk.counterface import face_stack
    a = face_stack(n=3000, seed=5)
    b = face_stack(n=3000, seed=5)
    assert a["Q_mN"]["mean"] == b["Q_mN"]["mean"]
    assert 0 < a["Q_mN"]["mean"] < a["Q_mN"]["p95"]


def test_leads_resistance_closed_form(chain):
    ld = chain["ns"]["leads"]["options"]
    k = ld["revK_C17200_0.100"]
    rho = 1.7241e-8 / 0.22
    L = 0.0268010411
    assert k["R_wire_ohm"] == pytest.approx(rho * L / (math.pi / 4 * 1e-8), rel=1e-3)
    assert ld["studyB_Ti64_0.128"]["wire_loss_share_of_coil"] > 2.0     # Ti-6Al-4V cannot be the coil lead


def test_couple_closed_form(chain):
    cp = chain["ns"]["couple"]
    F_n = val(PR.B1["F_n_N"])
    for r in cp["rows"]:
        M = F_n * chain["ns"]["L_lever_mm"] * 1e-3 * math.cos(math.radians(r["tilt_deg"]))
        assert r["couple_mNm"] == pytest.approx(M * 1e3)
        assert r["wire_force_N"] == pytest.approx(M / (2 * math.sqrt(2) * 5.5e-3))


def test_modes_rule(chain):
    md = chain["ns"]["modes"]
    for r in md["rows"]:
        assert r["servo_bw_max_Hz"] == pytest.approx(min(r["first_structural_free_Hz"], r["lowest_stuck_Hz"]) / 2.5)
    by = md["by_restraint"]
    assert by["revK_ball_guide"]["servo_bw_max_worst_Hz"] > by["studyB_wires"]["servo_bw_max_worst_Hz"]


def test_layout_schema_and_stack(chain):
    lay = chain["lay"]
    keys = {"id", "label", "group", "shape", "z0", "z1", "offset", "moves_with", "optional", "function", "part", "ledger", "mass_g"}
    ids = set()
    for c in lay["components"] + lay["heel_variant"]["components"]:
        assert keys <= set(c), c["id"]
        assert c["shape"] in ("cylinder", "cone", "tube", "box")
        assert c["z1"] > c["z0"], c["id"]
        assert c["id"] not in ids
        ids.add(c["id"])
        if c["shape"] == "box":
            assert len(c["size"]) == 3
        else:
            assert c["d0"] > 0
    c = {x["id"]: x for x in lay["components"]}
    assert c["anchor_ring"]["z1"] < c["head_cage"]["z0"]
    assert c["bulkhead"]["z1"] < c["battery"]["z0"]
    assert c["keeper"]["z1"] <= c["front_race"]["z0"] + 1e-9
    assert lay["length"] <= 175.0
    fs = lay["fit_summary"]
    assert fs["n"] == len(lay["fit_checks"]) == fs["pass"] + fs["marginal"] + fs["fail"]


def test_budgets_consistent(chain):
    bud = chain["bud"]
    E = bud["power"]["E_usable_Wh"]
    for k, r in bud["power"]["rows"].items():
        lo, hi = r["total_W"]
        assert 0 < lo <= hi
        assert r["hours"][0] == pytest.approx(E / hi)
        assert r["hours"][1] == pytest.approx(E / lo)
    m = bud["mass"]
    assert 50 < m["base"]["mass_g"] < m["with_heel_module"]["mass_g"] < 120
    assert bud["heat"]["worst_shell_C"] < 43.0
    c = bud["cost"]["unit_cost_usd"]
    assert c["1000"][0] < c["100"][0] and c["1000"][1] < c["100"][1]


def test_tolerance_runs(chain):
    from revk import tolerance as TL
    ns = chain["ns"]
    s = TL.sensing(ns["hall"]["gradient_mT_per_mm"]["min_norm"], ns["hall"]["coil_crosstalk_um_per_A"],
                   ns["hall"]["earth_offset_um"], n=2000)
    assert 0 < s["zero_um"]["mean"] < s["zero_um"]["p99"]
    m = TL.mechanics(val(PR.B1["stop_mm"]), 1.0, {"ring_bore": 0.0}, n=2000)
    assert m["usable_travel_mm"]["min"] < m["usable_travel_mm"]["mean"] <= val(PR.B1["travel_mm"]) + 1e-9


def test_sim_params_has_revJ_keys(chain):
    from revk import simparams as SP
    sp = SP.build(chain["lay"], chain["ns"], chain["hd"], chain["fc"], chain["fc_h"], chain["bud"])["sim_params"]
    ref = json.load(open(REPO_ROOT / "results" / "revJ" / "sim_params.json"))["sim_params"]
    for block in ("handle", "skid_ring", "nose", "refill", "sensors"):
        for k in ref[block]:
            if block == "handle" and "endcap" in k:
                continue
            if block == "refill" and k in ("spring_gradient_N_per_m",):
                continue
            alt = k.replace("endcap", "heel").replace("studyN", "studyB")
            assert k in sp[block] or alt in sp[block], (block, k)
    n = sp["nose"]
    assert n["usable_angle_rad"]["value"] * SP.Z_P_VIRTUAL == pytest.approx(val(PR.B1["travel_mm"]) * 1e-3)
    allowed = chain["ns"]["modes"]["by_restraint"]["revK_ball_guide"]["servo_bw_max_worst_Hz"]
    assert n["servo_hz"]["value"] <= allowed + 1e-9


def test_evidence_rows_format():
    from revk import evidence as EV
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "e.csv"
        EV.write(p)
        raw = p.read_bytes()
        assert b"\r\n" in raw and raw.count(b"\r\n") == len(EV.ROWS) + 1
        rows = list(csv.reader(open(p, newline="", encoding="utf-8")))
        ledger = list(csv.reader(open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8")))
        assert rows[0] == ledger[0] and len(rows[0]) == 23
        used = {r[0] for r in ledger[1:] if r}
        for r in rows[1:]:
            assert len(r) == 23 and r[0] not in used


def test_write_json_has_provenance(tmp_path):
    p = write_json(tmp_path / "x.json", {"a": np.float64(1.5), "b": float("inf")}, "CALCULATION")
    d = json.load(open(p))
    assert "stabpen.provenance" in d and d["a"] == 1.5 and d["b"] == "inf"
    assert "read_only_inputs_sha256_16" in json.dumps(d["stabpen.provenance"])


def test_quick_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("REVK_OUT", str(tmp_path))
    from revk import run as RR
    assert RR.main(["--quick", "--no-figures"]) == 0
    for f in ("revK.json", "layout.json", "budgets.json", "sim_params.json", "evidence_rows.csv"):
        assert (tmp_path / f).exists(), f
    d = json.load(open(tmp_path / "revK.json"))
    assert d["summary"]["length_mm"] > 100 and "stabpen.provenance" in d
