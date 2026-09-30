"""Fast checks of the re-baseline package (pure functions, the register, provenance and the output formats):
    python3 -m pytest rebaseline/tests -q
Slow checks (a short simulation per model) run only with REBASELINE_SLOW=1."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

import rebaseline
from rebaseline import REPO_ROOT, RESULTS_DIR
from rebaseline import common as CM
from rebaseline import impact as IM

SLOW = os.environ.get("REBASELINE_SLOW") == "1"


# ------------------------------------------------------------------ environment
def test_env_keeps_caches_inside_rebaseline():
    assert "rebaseline" in os.environ["NUMBA_CACHE_DIR"]
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
        assert os.environ[v] == "1"


# ------------------------------------------------------------------ impact register
def _register_tables():
    """Data rows of the four tables of docs/claims_register.md's preserved register, in order, per section."""
    txt = (REPO_ROOT / "docs" / "claims_register.md").read_text()
    body = txt.split("## Preserved upstream register", 1)[1]
    out, sec = {}, None
    for line in body.splitlines():
        m = re.match(r"^## (Tremor|Writing help|Hardware|Simulation)\s*$", line)
        if m:
            sec = m.group(1)
            out[sec] = []
            continue
        if sec and line.startswith("|") and not line.startswith("| Claim") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[sec].append(cells)
    return out


def test_register_integrity():
    assert IM.check() == []


def test_register_covers_every_row_of_the_preserved_register():
    tabs = _register_tables()
    prefix = {"Tremor": "T", "Writing help": "W", "Hardware": "H", "Simulation": "S"}
    for sec, rows in tabs.items():
        base = sorted({r["id"].rstrip("abcdefg") for r in IM.ROWS if r["section"] == sec})
        want = [f"{prefix[sec]}-{k:02d}" for k in range(1, len(rows) + 1)]
        assert base == want, (sec, base, want)
        for k, cells in enumerate(rows, 1):
            evidence = cells[2]
            mine = [r for r in IM.ROWS if r["id"].rstrip("abcdefg") == f"{prefix[sec]}-{k:02d}"]
            if "SIM" in evidence:
                assert any(r["classification"] != IM.NS for r in mine), (sec, k, evidence)


def test_register_csv_and_markdown():
    rows = list(csv.DictReader(io.StringIO(IM.to_csv())))
    assert len(rows) == len(IM.ROWS)
    assert set(rows[0]) == set(IM.FIELDS)
    md = IM.markdown_table()
    assert md.count("\n") + 1 == 2 + sum(1 for r in IM.ROWS if r["classification"] != IM.NS)


# ------------------------------------------------------------------ common
def test_jdump_is_strict_json(tmp_path):
    p = CM.jdump(tmp_path / "x.json", {"a": float("nan"), "b": np.float64(1.5), "c": np.arange(3), "d": [np.inf]})
    d = json.loads(p.read_text())
    assert d == {"a": None, "b": 1.5, "c": [0, 1, 2], "d": [None]}


def test_provenance_block_has_the_required_fields():
    md = CM.provenance("SIMULATION (test)", inputs=("rebaseline/common.py",), seeds=[1], parameters={"x": 1})
    for k in ("git", "input_sha256", "seeds", "parameters", "command", "python", "numpy", "scipy", "evidence_status"):
        assert k in md
    assert md["input_sha256"]["rebaseline/common.py"] == CM.sha256_file(REPO_ROOT / "rebaseline" / "common.py")


def test_bootstraps():
    b = CM.boot_mean([1.0, 2.0, 3.0, 4.0])
    assert b["mean"] == 2.5 and b["lo"] <= 2.5 <= b["hi"] and b["n"] == 4
    c = CM.cluster_boot_mean([1.0, 1.0, 5.0, 5.0], ["a", "a", "b", "b"])
    assert c["mean"] == 3.0 and c["n_clusters"] == 2 and c["lo"] >= 1.0 and c["hi"] <= 5.0
    assert CM.boot_mean([])["n"] == 0


# ------------------------------------------------------------------ task 2 (sim2j cards): pure parts
def test_modes_are_the_named_flags():
    from rebaseline import sim2j_cards as SC
    assert SC.MODES["causal"]["nose"] == {}
    lf = SC.MODES["legacy_flags"]["nose"]
    assert lf == {"velocity_source": "legacy_true", "inner_hz": 400.0, "contact_source": "legacy_force"}
    assert SC.MODES["legacy_exact"]["nose"] == lf
    from sim2 import params as P
    n = P.Nose()
    assert (n.velocity_source, n.contact_source, n.inner_hz) == ("hall", "measured", 80.0)


def test_historical_contact_wrapper_restores_the_immediate_flag():
    from types import SimpleNamespace
    from rebaseline import sim2j_cards as SC

    class Fake:
        def __init__(self):
            self._nb = np.array([[0.0] * 8 + [1.0]])
            self._ni = 1
            self.slide_noise = 1e-5
            self.js = 0
            self.j_refill = 0
            self.pm = SimpleNamespace(d=SimpleNamespace(qpos=np.array([0.2e-3])),
                                      m=SimpleNamespace(jnt_range=np.array([[0.0, 1.0]])))

        def read(self, t):
            return {"contact": False, "slide": -1e-3, "contact_t": None}
    rd = SC._historical_contact_read(Fake.read)
    out = rd(Fake(), 0.0)
    assert out["contact"] is True and abs(out["slide"] - 0.21e-3) < 1e-12 and "contact_t" not in out


def test_card_and_paired_on_synthetic_rows():
    from rebaseline import sim2j_cards as SC
    rows = []
    for w in range(3):
        for f0 in (8.0, 12.0):
            for amp in (1.0, 2.0):
                rows.append({"kind": "tremor", "ctl": "none", "w": w, "f0": f0, "amp_mm": amp, "ink_err_um": 400.0 * amp,
                             "words_app": 0.5, "letters_read": 0.8, "P_total_W": 2.0, "P_nose_W": 1.9})
                rows.append({"kind": "tremor", "ctl": "nose", "w": w, "f0": f0, "amp_mm": amp, "ink_err_um": 240.0 * amp,
                             "ratio": 0.6, "words_app": 1.0, "letters_read": 0.9, "P_total_W": 2.1, "P_nose_W": 2.0})
    c = SC.card(rows, SC.CARD_SEL["headline_8_12Hz_1_2mm"][1])
    assert c["n_cases"] == 12 and abs(c["ratio_mean"] - 0.6) < 1e-12
    assert c["words_of_10"] == [5.0, 10.0] and c["err_mm"][0] == pytest.approx(0.6)
    a = {f"{i}": dict(r) for i, r in enumerate(rows)}
    b = {k: dict(v, ratio=(v.get("ratio") or 0) + 0.1 if v["ctl"] == "nose" else None) for k, v in a.items()}
    p = SC.paired(b, a)
    assert p["nose"]["ratio_diff"]["mean"] == pytest.approx(0.1)
    assert p["none"]["exactly_equal_ink_share"] == 1.0


def test_severe_and_autowrite_cards():
    from rebaseline import sim2j_cards as SC
    rows = []
    for w in range(2):
        for f0 in (5.0, 8.0):
            rows.append({"task": "severe", "ctl": "none", "w": w, "f0": f0, "amp_mm": 3.0, "ink_err_um": 1500.0,
                         "words_app": 0.0, "letters_read": 0.4, "P_total_W": 2.0})
            rows.append({"task": "severe", "ctl": "nose", "w": w, "f0": f0, "amp_mm": 3.0, "ink_err_um": 1200.0,
                         "ratio": 0.8, "words_app": 0.5, "letters_read": 0.6, "P_total_W": 2.0})
            rows.append({"task": "autowrite", "ctl": "autowrite", "plan_ok": True, "w": w, "f0": f0, "amp_mm": 3.0,
                         "ink_err_um": 80.0, "words_app": 1.0, "letters_read": 0.9, "P_total_W": 2.5, "q_max_mm": 6.5})
        rows.append({"task": "autowrite", "ctl": "autowrite", "plan_ok": True, "w": w, "f0": 8.0, "amp_mm": 0.0,
                     "ink_err_um": 40.0, "words_app": 1.0, "letters_read": 1.0, "P_total_W": 2.2})
    c = SC.severe_autowrite_cards(rows)
    assert c["severe_through"]["words_of_10"] == [0.0, 5.0] and c["severe_through"]["ratio_mean"] == pytest.approx(0.8)
    assert c["severe_autowrite"]["words_of_10"] == [0.0, 10.0] and c["severe_autowrite"]["n_cases"] == 4
    assert c["autowrite_no_tremor"]["err_mm"][1] == pytest.approx(0.04)


# ------------------------------------------------------------------ task 3 (balanced nib): force laws
def test_wire_table_reproduces_the_engineering_pass():
    from rebaseline import bnib_rerun as BR
    t = BR.wire_table(BR.REVK["wires"], 1.2587e-3 + 0.3e-3)
    F_stop = float(np.interp(1.2587e-3, t["q"], t["F"]))
    assert F_stop == pytest.approx(18.2e-3, rel=0.01)           # 18.2 mN at the stop with the 10,000 N/m anchor
    assert t["k0"] == pytest.approx(1.5617, rel=0.01)            # the linear bending stiffness at small q
    assert np.all(np.diff(t["F"]) > 0)
    c = BR.wire_table(BR.CAND15["wires"], 2.0e-3)
    assert float(np.interp(1.5e-3, c["q"], c["F"])) < 3.5e-3       # the soft 100 N/m anchor stays nearly linear


def test_extra_force_directions_and_limits():
    from rebaseline import bnib_rerun as BR
    t = BR.wire_table(BR.REVK["wires"], 1.6e-3)
    x = np.array([1.0e-3, 0.0])
    F = BR.extra_force(x, np.zeros(2), t, 0.0, t["k0"])
    assert F[0] < 0 and abs(F[1]) < 1e-15                         # hardening remainder restores
    assert BR.extra_force(np.zeros(2), np.zeros(2), t, 0.008, t["k0"]).tolist() == [0.0, 0.0]
    v = np.array([0.0, 0.05])
    Fd = BR.extra_force(np.zeros(2), v, None, 0.008, 0.0)
    assert Fd[1] == pytest.approx(-0.008, rel=1e-6)               # full drag, opposing the velocity
    Fs = BR.extra_force(np.zeros(2), np.array([1e-6, 0.0]), None, 0.008, 0.0)
    assert abs(Fs[0]) < 0.008 * 1e-6 / BR.DRAG_V0 * 1.0001       # regularised near zero velocity
    xb = np.array([0.0, 2.0e-3])                                  # beyond the table: linear extrapolation, still restoring
    assert BR.extra_force(xb, np.zeros(2), t, 0.0, t["k0"])[1] < 0


def test_drag_step_is_stable_at_the_simulation_step():
    from rebaseline import bnib_rerun as BR
    for m in (BR.REVK["m_move"], BR.CAND15["m_move"]):
        c = BR.drag_step_check(m)
        assert c["stable_monotone"] and 0.5 < c["multiplier"] < 1.0


def test_power_bands_scale_as_force_constant_squared():
    from rebaseline import bnib_rerun as BR
    nib = {"Km_tip": 0.3, "Km_y": 0.15, "Km_disk_min_map": 0.1}
    b = BR.calc_power_bands(10.0, nib)
    assert b["weaker_axis_mW"] == pytest.approx(40.0) and b["disk_minimum_mW"] == pytest.approx(90.0)
    assert b["disk_minimum_derated_0p7_mW"] == pytest.approx(90.0 / 0.49)


# ------------------------------------------------------------------ task 4 (reach)
def test_b1_pen_changes_only_servo_mass_suspension_and_force():
    from rebaseline import reach_b1 as RB
    from realdata import hw1 as H
    revj = H.pens()["revJ"]
    p = RB.b1_pen(revj, "B1k")
    assert p.servo_hz == 40.0 and p.m_tip == pytest.approx(3.44e-3, rel=1e-3) and p.k_tip == pytest.approx(1.5617)
    for f in ("mass", "q_lim", "q_taper", "q_stop", "latency", "slew", "servo_zeta", "skid", "F_c", "r_imu"):
        assert getattr(p, f) == getattr(revj, f), f
    lp = RB.limited(p, 1.0587)
    assert lp.q_lim == pytest.approx(1.0587e-3) and lp.servo_hz == 40.0
    assert RB.inner_hz_of("B1c") == 46.0 and RB.inner_hz_of("revJ") is None


# ------------------------------------------------------------------ task 5 (page model v2)
def test_page_dependent_configs():
    from rebaseline import page_v2 as PV
    for k in ("oracle", "held", "pred_ar_imu", "fir_full_raw", "page_ar_trem_ideal", "akf_trem_raw_idealpage"):
        assert not PV._page_dependent(k), k
    for k in ("page_ar_trem_deltapen", "ai2tcn_full_gated", "net_trem_raw", "akf_full_raw"):
        assert PV._page_dependent(k), k


def test_page_v2_plan_matches_study_r():
    from rebaseline import page_v2 as PV
    p = PV.plan(False)
    assert len(p) == 9 * (1 + 6) + 4 * 2
    assert len({PV.r_name(*x[:3], bridge=x[3]) for x in p}) == len(p)


def test_version2_page_model_is_causal():
    """A later extension of the record must not change earlier readings (the defect of version 1)."""
    from fusion.sensors import Streams
    from realdata import sensors as RS
    t = np.arange(0, 2.0, 1e-3)
    xy = np.column_stack([0.02 * t, 0.003 * np.sin(2 * np.pi * 3 * t)])

    def st(n):
        return Streams(tick_t=t[:n], acc_t=t[:n], acc_av=t[:n], acc=np.zeros((n, 2)), pos_t=t[:n], pos_av=t[:n] + 2e-3,
                       pos=xy[:n], pos_ok=np.ones(n), con_t=t[:n], con_av=t[:n], con=np.ones(n), meta={})
    m = RS.PageModel()
    a = RS.degrade_page(st(1000), m, 11)
    b = RS.degrade_page(st(2000), m, 11)
    assert np.array_equal(np.asarray(a.pos), np.asarray(b.pos)[:1000])


def test_anchored_version2_starts_at_the_first_valid_report():
    """Patch-proposal-6 workaround: a record that starts lifted is anchored at its first valid page report; from there
    the output is exactly version 2 on the suffix; a record that starts valid is untouched; version 1 passes through."""
    import dataclasses
    from fusion.sensors import Streams
    from realdata import sensors as RS
    from rebaseline import page_v2 as PV
    orig = getattr(RS.degrade_page, "__wrapped__", RS.degrade_page)
    wrapped = PV.anchored(orig)
    t = np.arange(0, 1.0, 1e-3)
    n = len(t)
    xy = np.column_stack([0.02 * t, 0.003 * np.sin(2 * np.pi * 3 * t)])
    ok = np.ones(n)
    ok[:37] = 0.0
    st = Streams(tick_t=t, acc_t=t, acc_av=t, acc=np.zeros((n, 2)), pos_t=t, pos_av=t + 2e-3, pos=xy, pos_ok=ok,
                 con_t=t, con_av=t, con=np.ones(n), meta={})
    m = RS.PageModel()
    with pytest.raises(ValueError):
        orig(st, m, 5)
    out = wrapped(st, m, 5)
    ref = orig(dataclasses.replace(st, pos_t=t[37:], pos_av=(t + 2e-3)[37:], pos=xy[37:], pos_ok=ok[37:]), m, 5)
    assert len(out.pos_t) == n and np.array_equal(np.asarray(out.pos)[37:], np.asarray(ref.pos))
    assert np.array_equal(np.asarray(out.pos_ok)[37:], np.asarray(ref.pos_ok)) and not np.any(np.asarray(out.pos_ok)[:37])
    assert np.all(np.diff(np.asarray(out.pos_av)) >= 0)
    rv = out.meta["page_reference_valid"]
    assert len(rv) == n and not any(rv[:37]) and rv[37] and out.meta["page_anchor_index"] == 37
    st_ok = dataclasses.replace(st, pos_ok=np.ones(n))
    assert np.array_equal(np.asarray(wrapped(st_ok, m, 5).pos), np.asarray(orig(st_ok, m, 5).pos))
    m1 = dataclasses.replace(m, version=1)
    assert np.array_equal(np.asarray(wrapped(st, m1, 5).pos), np.asarray(orig(st, m1, 5).pos))


# ------------------------------------------------------------------ outputs
def _result_files():
    return sorted(RESULTS_DIR.glob("*.json")) if RESULTS_DIR.exists() else []


def test_every_result_json_carries_provenance():
    files = _result_files()
    if not files:
        pytest.skip("no results yet")
    for p in files:
        d = json.loads(p.read_text())
        md = d.get("stabpen.provenance")
        assert md, p
        for k in ("git", "input_sha256", "seeds", "parameters", "command", "python", "numpy", "evidence_status"):
            assert k in md, (p, k)


def test_evidence_rows_csv_format():
    p = RESULTS_DIR / "evidence_rows.csv"
    if not p.exists():
        pytest.skip("no evidence rows yet")
    raw = p.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
    head = (REPO_ROOT / "docs" / "evidence.csv").read_bytes().split(b"\r\n", 1)[0].decode()
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline="")))
    assert ",".join(rows[0]) == head and len(rows[0]) == 23
    for r in rows[1:]:
        assert len(r) == 23
        m = re.match(r"^(EML|ACT)-(\d+)$", r[0])
        assert m and ((m.group(1) == "EML" and 110 <= int(m.group(2)) <= 119) or
                      (m.group(1) == "ACT" and 150 <= int(m.group(2)) <= 159)), r[0]


def test_no_model_identifiers_in_written_files():
    bad = re.compile(r"(claude|opus|sonnet|haiku|gpt-\d|chatgpt|gemini)", re.I)
    paths = list((REPO_ROOT / "rebaseline").glob("*.py")) + list(RESULTS_DIR.glob("*")) if RESULTS_DIR.exists() else []
    doc = REPO_ROOT / "docs" / "rebaseline.md"
    if doc.exists():
        paths.append(doc)
    for p in paths:
        if p.is_file() and p.suffix in (".py", ".json", ".csv", ".md"):
            assert not bad.search(p.read_text(errors="ignore")), p


# ------------------------------------------------------------------ slow: one short run per model (opt-in)
@pytest.mark.skipif(not SLOW, reason="set REBASELINE_SLOW=1")
def test_legacy_exact_reproduces_a_historical_row():
    import subprocess
    import sys
    code = ("import rebaseline.sim2j_cards as S; S.install('legacy_exact'); import sim2j.et as ET; "
            "p=S.pen_models('legacy_exact'); su=ET.WriterSetup(0,p); rn=ET.run_case(su,'none',8.0,1e-3,200,keep=True,record=True); "
            "r=rn.pop('_r'); m=ET.run_case(su,'nose',8.0,1e-3,200,ref_none=r); print(rn['ink_err_um'], m['ink_err_um'])")
    out = subprocess.check_output([sys.executable, "-c", code], cwd=str(REPO_ROOT), text=True).split()
    assert float(out[-2]) == pytest.approx(440.60591721132454, abs=1e-9)
    assert float(out[-1]) == pytest.approx(377.05517288774064, abs=1e-9)
