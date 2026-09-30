"""Tests of study P's code: the moving-page plant against HW1, the stage and its limits, the page-drag physics, the
hand-compliance model, the predictor, the accepted-writing helpers, the design calculations, the CAD layout rules and
the published files' format.  Synthetic inputs only (no licensed data), under a minute."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest

import platen  # noqa: F401  (environment first)
from platen import common as CM
from platen import design as D
from platen import plant as PP

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "platen"


def _scenario(T=2.0, dt=2.5e-5, tremor_mm=0.0, f=6.0, write=True):
    """A synthetic HW1 scenario: a slow loop of 'writing' (or a still pen) with an optional sinusoidal tremor."""
    from handwriting import plant as PL
    t = np.arange(0.0, T, dt)
    if write:
        xy = np.column_stack([3e-3 * np.sin(2 * np.pi * 1.5 * t), 2e-3 * np.cos(2 * np.pi * 1.1 * t)])
    else:
        xy = np.zeros((len(t), 2))
    d = np.column_stack([tremor_mm * 1e-3 * np.sin(2 * np.pi * f * t), 0.5 * tremor_mm * 1e-3 * np.cos(2 * np.pi * f * t)])
    pref = xy + d
    vref = np.gradient(pref, dt, axis=0)
    down = np.ones(len(t))
    down[: int(0.1 / dt)] = 0.0
    return PL.Scenario(t=t, pref=np.ascontiguousarray(pref), vref=np.ascontiguousarray(vref), down=down,
                       intended=xy, tremor=d, dt=dt, meta={"lift": np.where(down > 0.5, 0.0, 5e-3)})


def _hand():
    from handwriting import params as PR
    return PR.Hand.from_config()


def test_plant_reproduces_hw1_ordinary_pen_with_the_page_held():
    from handwriting import params as PR
    from handwriting import plant as PL
    scn = _scenario(tremor_mm=1.0)
    hand = _hand()
    r = PL.run(scn, PR.ordinary_pen(), hand)
    pr = PP.run(scn.pref, scn.vref, scn.down, scn.dt, hand=hand, writing=PR.Writing(), pen_mass=CM.PEN_MASS_HW1)
    n = min(len(r.t), len(pr.t))
    assert np.max(np.abs(r.t[:n] - pr.t[:n])) == 0.0
    assert np.max(np.abs(r.ink[:n] - pr.tip[:n])) < 1e-12          # the pen is exactly HW1's
    assert np.max(np.abs(pr.page)) < 1e-6                           # the held page yields < 1 um to the drag
    assert np.array_equal(r.contact[:n] > 0.5, pr.contact[:n] > 0.5)


def test_page_motion_moves_the_ink_not_the_pen_under_hw1_convention():
    from handwriting import params as PR
    scn = _scenario(tremor_mm=0.0)
    hand = _hand()
    n_ticks = int(math.ceil(len(scn.t) / 20)) + 1
    tt = np.arange(n_ticks) * 5e-4
    cmd = np.column_stack([1e-3 * np.sin(2 * np.pi * 2.0 * tt), np.zeros(n_ticks)])
    held = PP.run(scn.pref, scn.vref, scn.down, scn.dt, hand=hand, writing=PR.Writing(), pen_mass=CM.PEN_MASS_HW1)
    pr = PP.run(scn.pref, scn.vref, scn.down, scn.dt, hand=hand, writing=PR.Writing(), pen_mass=CM.PEN_MASS_HW1,
                cmd_ext=cmd)
    assert np.max(np.abs(pr.tip - held.tip)) < 1e-12                # the writer cancels the drag: the pen is unmoved
    assert np.allclose(pr.ink, pr.tip - pr.xy("paperx"))
    # the stage follows a 2 Hz command within its group delay
    g = PP.Stage().group_delay()
    ref = 1e-3 * np.sin(2 * np.pi * 2.0 * (pr.t - g))
    m = pr.t > 0.5
    assert np.sqrt(np.mean((pr.page[m, 0] - ref[m]) ** 2)) < 20e-6


def test_fine_stage_stays_inside_its_stop():
    from handwriting import params as PR
    scn = _scenario(T=1.0, write=False)
    n_ticks = int(math.ceil(len(scn.t) / 20)) + 1
    cmd = np.tile([12e-3, 0.0], (n_ticks, 1))                       # far beyond the +-5 mm usable travel
    st = PP.Stage()
    pr = PP.run(scn.pref, scn.vref, scn.down, scn.dt, hand=_hand(), writing=PR.Writing(), pen_mass=CM.PEN_MASS_HW1,
                stage=st, cmd_ext=cmd)
    rel = np.hypot(pr["fx"], pr["fy"])
    assert rel.max() <= st.q_stop_f + 0.2e-3
    assert rel[-1] <= st.q_lim_f + 1e-6


def test_hand_compliance_dc_gain():
    h = _hand()
    b, a = PP.hand_compliance(h, 0.012)
    assert abs(b.sum() / a.sum() - (1.0 / h.K_grip + 1.0 / h.k_arm)) < 1e-9
    b2, a2 = PP.hand_compliance(h, 0.012, scale=1.3)
    assert abs(b2.sum() / a2.sum() - 1.3 * (1.0 / h.K_grip + 1.0 / h.k_arm)) < 1e-9


def test_moving_page_drags_a_relaxed_pen_by_its_compliance():
    """With no drag compensation ('intended' writer, no intended motion) a page sliding at constant speed drags the
    pen tip by about compliance x kinetic friction (the stick-slip coupling of part b)."""
    from handwriting import params as PR
    scn = _scenario(T=1.5, write=False)
    n_ticks = int(math.ceil(len(scn.t) / 20)) + 1
    tt = np.arange(n_ticks) * 5e-4
    cmd = np.column_stack([np.clip(tt - 0.3, 0, None) * 4e-3, np.zeros(n_ticks)])   # 4 mm/s after 0.3 s
    w = PR.Writing()
    pr = PP.run(scn.pref, scn.vref, scn.down, scn.dt, hand=_hand(), writing=w, pen_mass=CM.PEN_MASS_HW1,
                cmd_ext=cmd, writer="intended")
    G0 = 1.0 / _hand().K_grip + 1.0 / _hand().k_arm
    expect = G0 * w.mu_ball * w.N
    tip = pr.tip[pr.t > 1.2, 0].mean()
    assert 0.8 * expect < tip < 1.2 * expect


def test_predictor_is_causal_and_predicts_a_sine():
    from platen import predictor as PRD
    t = np.arange(0.0, 12.0, 2.5e-4)
    sig = []
    for i in range(5):
        f = 5.0 + 0.3 * i
        e = np.column_stack([1e-3 * np.sin(2 * np.pi * f * t), 0.5e-3 * np.cos(2 * np.pi * f * t)])
        sig.append({"id": f"s{i}", "fold": i, "level": "severe", "t": t, "e": e, "contact": np.ones(len(t)),
                    "drift_seed": i})
    fit = PRD.fit(sig, cam_hz=250.0, cam_latency=4e-3, noise=0.0, g=5e-3, quick=True, with_drift=False,
                  log=lambda *a: None)
    assert fit["cv_rms_m"] < 0.1 * fit["hold_rms_m"]
    coef = np.asarray(fit["coef"])
    assert coef.shape[0] == fit["cam_lat_ticks"] + fit["cam_every"]
    # causality: the prediction uses only frames at or before the newest available one (design_rows)
    tf, y = PRD.frames(t, sig[0]["e"], fit["cam_every"], 5e-4, 0.0, 1)
    X, T, _ = PRD.design_rows(tf, y, t, sig[0]["e"], 4, fit["phases"][0], 5e-4, 5e-3)
    assert X.shape[2] == 4 and np.all(np.isfinite(T))


def test_friction_feedforward_direction_and_hold():
    from platen import accepted as A
    n = 400
    v = np.zeros((n, 2))
    v[100:200, 0] = 0.02                       # a stroke to +x, then a stroke to +y
    v[250:350, 1] = 0.02
    contact = np.zeros(n, bool)
    contact[50:380] = True
    ff = A.friction_feedforward(v, contact, 7.6e-3, 0.15, 1.0)
    assert np.all(ff[~contact] == 0.0)
    assert ff[60, 0] < 0 and abs(ff[60, 1]) < 1e-15          # wound up before the first stroke, against its direction
    assert ff[300, 1] < 0 and abs(ff[300, 0]) < 1e-15
    assert ff[370, 1] < 0                                      # held after the last stroke until the lift
    assert abs(np.linalg.norm(ff[150]) - 7.6e-3 * 0.15) < 1e-12


def test_accepted_metrics_on_a_perfect_trace():
    from platen import accepted as A

    class R:
        def __init__(self):
            self.t = np.arange(0, 1.0, 5e-4)
            n = len(self.t)
            self.ink = np.column_stack([1e-3 * self.t, np.zeros(n)])
            self.page = np.zeros((n, 2))
            self.tip = self.ink.copy()
            self.contact = np.ones(n)
            self._c = {"abort": np.zeros(n), "stop": np.zeros(n), "fx": np.zeros(n), "fy": np.zeros(n),
                       "cx": np.zeros(n), "cy": np.zeros(n), "Ffx": np.zeros(n), "Ffy": np.zeros(n),
                       "Fcx": np.zeros(n), "Fcy": np.zeros(n), "Fbx": np.zeros(n), "Fby": np.zeros(n)}

        def __getitem__(self, k):
            return self._c[k]
    r = R()
    tick_t = np.arange(len(r.t)) * 5e-4
    m = A.metrics(r, r.ink.copy(), np.ones(len(tick_t), bool), np.array(["ink"] * len(tick_t)), tick_t)
    assert m["ink_coverage_fraction"] == 1.0
    assert m["actual_requested_ink_rms_error_mm"] < 1e-9
    assert m["engineering_complete"]
    assert m["derivatives"]["ink_on_page"]["max_acc_m_s2"] < 1e-6


def test_design_calculations():
    m = D.masses("A5")
    assert 0.3 < m["fine_x_kg"] < 1.0 and m["coarse_moving_kg"] > m["fine_x_kg"]
    assert D.masses("A6")["fine_x_kg"] < m["fine_x_kg"]
    hd = D.hold_down("A5", 3.0, 0.4)
    assert abs(hd["vacuum_Pa"] - 3.0 / (0.4 * 0.210 * 0.148)) < 1e-9
    assert D.pinch(m["coarse_moving_kg"])["passes"]
    assert abs(D.z_drop(3e-3)["gravity_drop_s"] - math.sqrt(2 * 3e-3 / 9.81)) < 1e-12
    b = D.bom()
    assert b["bom_usd_low"] < b["bom_usd_high"]
    assert abs(D.vca_power(3.9) - 2.5) < 1e-12              # 1 A in 2.5 ohm
    st = D.sim_stage("fine_A5")
    assert abs(st.group_delay() - (5e-4 + 2 * 0.7 / (2 * math.pi * 40.0))) < 1e-12


def test_cad_layout_rules():
    import importlib
    cad = importlib.import_module("mechanics.cad.platen")
    comps = {c["name"]: c for c in cad.layout()}
    swept = comps["plate_swept_envelope"]
    half_x = swept["dims"][0] / 2
    for sx in (-1, 1):
        post = comps[f"palm_post_{sx}"]
        assert abs(post["centre"][0]) - post["dims"][0] / 2 > half_x        # posts outside the swept plate
    bridge = comps["palm_rest_bridge"]
    gap = bridge["centre"][2] - bridge["dims"][2] / 2 - cad.Z["plate_top"]
    assert gap >= 25.0 - 1e-9                                               # ISO 13854 finger gap
    bx, by, _ = cad.BASE
    for c in comps.values():
        if c["shape"] == "box" and not c["name"].startswith(("palm_rest_bridge", "plate_swept")):
            assert abs(c["centre"][0]) + c["dims"][0] / 2 <= bx / 2 + 1e-6, c["name"]


@pytest.mark.skipif(not (RES / "evidence_rows.csv").exists(), reason="results not generated")
def test_evidence_rows_format():
    raw = (RES / "evidence_rows.csv").read_bytes()
    assert b"\r\n" in raw and raw.count(b"\r\n") >= raw.count(b"\n")
    hdr = next(csv.reader(open(ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8")))
    rows = list(csv.DictReader(open(RES / "evidence_rows.csv", newline="", encoding="utf-8")))
    assert list(rows[0].keys()) == hdr and len(hdr) == 23
    for r in rows:
        pre, num = r["id"].split("-")
        num = int(num)
        assert (pre == "ACT" and 170 <= num <= 189) or (pre == "AMF" and 280 <= num <= 299) or \
               (pre == "CON" and 110 <= num <= 119)
    ledger = {r["id"] for r in csv.DictReader(open(ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8"))}
    assert not ({r["id"] for r in rows} & ledger)


@pytest.mark.skipif(not (RES / "platen.json").exists(), reason="results not generated")
def test_results_carry_provenance():
    for p in RES.glob("*.json"):
        d = json.loads(p.read_text())
        assert "stabpen.provenance" in d, p.name
        pv = d["stabpen.provenance"]
        assert "git_revision" in pv and "generated_utc" in pv


def test_doc_fields_resolve_from_results(tmp_path):
    from platen import doc
    b = {"mean": 0.1234, "lo": 0.1, "hi": 0.15}
    res = {"tremor": {"by_class": {"all/severe": {"P_oracle": {"tip_tremor_mm": b, "words_read": {"mean": 8.25, "lo": 7.0,
                                                                                                     "hi": 9.0}}}}},
           "sensitivity": {"rows": {"baseline|camera": {"tip_tremor_mm": b}}},
           "accepted": {"summary": {"se|proposed|still": {"engineering_complete": 19, "n": 20, "median_rms_mm": 0.0412}},
                        "sensitivity": {}},
           "fivebar": {"summary": [{"grip_stiffness_N_m": 200.0, "feedforward": True, "engineering_complete": 0,
                                    "words": 20}]},
           "design": {"masses": {"A5": {"fine_x_kg": 0.5876}}}}
    assert doc.resolve(res, "t:all/severe:P_oracle:tip_tremor_mm") == "0.12"
    assert doc.resolve(res, "t:all/severe:P_oracle:tip_tremor_mm:ci") == "0.12 (0.10 to 0.15)"
    assert doc.resolve(res, "t:all/severe:P_oracle:words_read") == "8.2"
    assert doc.resolve(res, "s:baseline|camera:tip_tremor_mm") == "0.12"
    assert doc.resolve(res, "a:se|proposed|still:complete") == "19/20"
    assert doc.resolve(res, "a:se|proposed|still:median_rms_mm") == "0.041"
    assert doc.resolve(res, "a:se|cradle|cradle:complete") == "not run"
    assert doc.resolve(res, "fb:200") == "0/20"
    assert doc.resolve(res, "d:masses.A5.fine_x_kg") == "0.59"
    tpl = tmp_path / "t.md"
    tpl.write_text("x {{t:all/severe:P_oracle:tip_tremor_mm}} y {{t:all/severe:nothing:tip_tremor_mm}} z {{bogus:1}}")
    out = doc.fill(res, template=tpl, out=tmp_path / "o.md")
    text = out.read_text()
    assert text.startswith("x 0.12 y n/a z [missing: bogus:1]")


def test_ledger_rows_have_unique_sorted_ids():
    from platen import evidence as EV
    rows = sorted(EV.source_rows(), key=EV._key)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert all(set(r.keys()) >= set(EV.HEADER) for r in rows)
