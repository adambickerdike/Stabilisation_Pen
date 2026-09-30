"""DEC-076: the owners' patches of the six defects of docs/rebaseline.md s8, against study X's own runtime workarounds
(which stay in place): where both exist they must agree.
    python3 -m pytest rebaseline/tests -q"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

import rebaseline  # noqa: F401  (one numerical thread; caches inside rebaseline/build)
from rebaseline import REPO_ROOT


# ------------------------------------------------------------------ patch 1: the historical firmware contact channel
def _lifted_scenario(T: float = 0.6):
    """A line written with a 1.5 mm lift between 0.25 and 0.40 s (contact changes both ways)."""
    from sim.pensim import scenarios as PS
    from stabpen import signals as sg
    t = np.arange(0.0, T, 50e-6)
    xy = np.column_stack([0.02 * np.clip(t - 0.1, 0, None), np.zeros_like(t)])
    lift = np.where((t > 0.25) & (t < 0.40), 1.5e-3 * np.sin(np.pi * (t - 0.25) / 0.15), 0.0)
    sc = PS._assemble(sg.Intended(t, xy, lift < 1e-9, lift, []), np.zeros_like(xy), 1.0, 50.0)
    sc.psi_disp = np.zeros(len(t))
    sc.tremor_obj = None
    return sc


def test_patch1_legacy_immediate_equals_the_historical_contact_wrapper():
    """Sensors.firmware_contact = 'legacy_immediate' gives the firmware the contact stream of study X's substitution
    (sim2j_cards._historical_contact_read, mode legacy_exact) on the delayed channel: tick by tick, and the same run."""
    from sim2 import sensors as SS
    from sim2j import revj as RJ, sensing as SE, stepper as ST
    from sim2j.firmware import FWConfig
    from rebaseline import sim2j_cards as SC
    assert not getattr(SE.OnlineSensors.read, "__wrapped_historical__", False)
    pm = RJ.build(RJ.config(heel=True, dt=50e-6))
    sc = _lifted_scenario()

    def run(wrapper: bool):
        st = ST.RevJStepper(pm, sc, FWConfig(nose="tremor", akf=SS.revh_params(), seed=1), {}, mu=0.9, seed=1)
        sens = st.fw.sens
        if wrapper:                                  # study X's substitution, on this instance only
            sens.read = types.MethodType(SC._historical_contact_read(SE.OnlineSensors.read), sens)
        seen, read = [], sens.read

        def spy(t):
            o = read(t)
            seen.append((o["contact"], o["slide"]))
            return o
        sens.read = spy
        st.advance(st.n)
        return seen, st.result()
    a, ra = run(wrapper=True)
    cfg0 = pm.cfg
    pm.cfg = cfg0.replace(sensors=dataclasses.replace(cfg0.sensors, firmware_contact="legacy_immediate"))
    try:
        b, rb = run(wrapper=False)
    finally:
        pm.cfg = cfg0
    delayed, _ = run(wrapper=False)
    assert len(a) == len(b) == len(delayed) and a == b
    assert np.array_equal(ra.ink(), rb.ink())
    assert [c for c, _ in delayed] != [c for c, _ in a]            # the current channel lags: the check can fail
    assert rb.info["online_sensor_version"] == "contact-legacy-immediate"


# ------------------------------------------------------------------ patch 2: the writer-setup cache key
def test_patch2_setup_key_separates_what_study_x_kept_in_separate_folders(tmp_path, monkeypatch):
    """Study X kept one adapted-hand-path folder per sensing mode ('causal', 'legacy'); the patched key tells those
    modes apart within one folder, and the legacy_exact channel, as the patched option, gets a key of its own."""
    import sim2j.et as ET
    from sim2j import revj as RJ
    from rebaseline import sim2j_cards as SC
    monkeypatch.setattr(ET, "BUILD", str(tmp_path))
    base = RJ.config(heel=True, dt=50e-6)

    def key(mode: str, firmware_contact: str = "delayed") -> str:
        cfg = base.replace(nose=dataclasses.replace(base.nose, **SC.MODES[mode]["nose"]),
                           sensors=dataclasses.replace(base.sensors, firmware_contact=firmware_contact))
        su = ET.WriterSetup.__new__(ET.WriterSetup)
        su.w, su.version, su.text, su.pen, su.pre_s, su.adapt_ctl = 0, "v2", ET.ET_TEXT, "base", ET.ET_PRE_S, "none"
        su.pm = SimpleNamespace(cfg=cfg, m=SimpleNamespace(opt=SimpleNamespace(timestep=50e-6)), info={})
        return su._cache_path(3)
    for a in SC.MODES:
        for b in SC.MODES:
            if SC.MODES[a]["setups"] != SC.MODES[b]["setups"]:
                assert key(a) != key(b), (a, b)
    assert key("legacy_exact", "legacy_immediate") != key("legacy_flags")


# ------------------------------------------------------------------ patch 3: bnib's servo gets the measured contact
_P3 = r'''
import json
import rebaseline
import numpy as np
import bnib.sim as S
import sim2.sim as S2
import sim2j.tasks as TK
patched = S.BStepper
import rebaseline.bnib_rerun as BR
BR.install("B1_studyB_now")
seen = []
ref_tick = S2.NoseServo.ref_tick
def spy(self, t, tick, tip, in_contact, direct_q=None):
    seen.append(bool(in_contact))
    return ref_tick(self, t, tick, tip, in_contact, direct_q=direct_q)
S2.NoseServo.ref_tick = spy
sd, _ = BR.designs("B1_studyB_now")
pm = S.build(sd, 50.0)
case = TK.WriterCase(0, version="v2", text="r", pre_s=0.2)
env = S.case_env(0, 200)
out = {}
for name, cls in (("workaround", S.BStepper), ("patched", patched)):
    del seen[:]
    st = cls(pm, case.scenario(), S.fw_config("none", 200, 0), sd, seed=200, ink=env["ink"], paper=env["paper"],
             face_err=env["face_err"], t_end=0.1)
    st.advance(st.n)
    out[name] = {"cls": cls.__name__, "gate": list(seen), "q1": np.asarray(st.result()["q1"]).tolist()}
print(json.dumps(out))
'''


def test_patch3_bnib_servo_gate_equals_the_rerun_wrapper():
    """Study X's bnib_rerun wraps the servo's ref_tick so that it gets the firmware's delayed contact (configurations
    'contact: current'); the patched BStepper passes that contact itself: the same gate stream and the same run.  In a
    child process, because the workaround is installed module-wide."""
    p = subprocess.run([sys.executable, "-c", _P3], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, p.stderr[-3000:]
    out = json.loads(p.stdout.strip().splitlines()[-1])
    w, b = out["workaround"], out["patched"]
    assert (w["cls"], b["cls"]) == ("LoadStepper", "BStepper")
    assert len(w["gate"]) == len(b["gate"]) == 200 and w["gate"] == b["gate"] and not all(b["gate"])
    assert w["q1"] == b["q1"]


# ------------------------------------------------------------------ patch 4: the version-1 page-model file is kept
def test_patch4_page_model_files_agree_with_study_x_records(tmp_path, monkeypatch):
    """Study X recorded the version-1 fit (page_v2.V1_PUBLISHED_FIT) and fitted version 2 in memory only (its record in
    results/rebaseline/page_v2.json); the patched cache reads version 1 from page_model.json and version 2 from
    page_model_v2.json, and a version-2 save never writes the version-1 file."""
    from realdata import sensors as RS
    from rebaseline import page_v2 as PV
    v1 = RS.load_model(allow_legacy=True)
    if v1 is not None and v1.version == 1:                          # a cache that was not overwritten (or was restored)
        F = PV.V1_PUBLISHED_FIT
        assert (v1.c, v1.sigma, v1.fitted["n_windows"]) == (F["c"], F["sigma"], F["n_windows"])
        assert v1.fitted["median_um"] == pytest.approx(F["median_um"])
        assert v1.fitted["mean_um"] == pytest.approx(F["mean_um"])
    rec = json.loads((REPO_ROOT / "results" / "rebaseline" / "page_v2.json").read_text())["page_model"]["v2"]
    v2 = RS.load_model()
    if v2 is not None:
        assert v2.version == 2 and (v2.c, v2.sigma, v2.fitted["n_windows"]) == (rec["c"], rec["sigma"],
                                                                             rec["fitted"]["n_windows"])
    monkeypatch.setattr(RS, "PAGE_MODEL_JSON", tmp_path / "page_model.json")
    monkeypatch.setattr(RS, "PAGE_MODEL_V2_JSON", tmp_path / "page_model_v2.json")
    RS.save_model(RS.PageModel(c=rec["c"], sigma=rec["sigma"]))
    assert not (tmp_path / "page_model.json").exists() and RS.load_model().c == rec["c"]


# ------------------------------------------------------------------ patch 5: no aggregation across page-model versions
def test_patch5_aggregation_refuses_what_study_x_kept_apart():
    """Study X wrote its version-2 cases apart and compared the full version-1 set with the full version-2 set; the
    patched aggregation takes each full set and refuses one that mixes them."""
    from realdata import hw1 as H
    from realtrack import test as T
    v1 = [{"set": "real", "writer": f"w{w}", "kind": "PD", "class": "severe", "tremor": {"amp_mm": 1.7, "f0": 6.0},
           "devices": {"none": {"words_read": 2, "words_total": 10, "tip_tremor_mm": 1.7},
                       "revJ_gated|deltapen": {"words_read": 3, "words_total": 10, "tip_tremor_mm": 1.2}}}
          for w in range(4)]
    v2 = [dict(c, page_model_version=2) for c in v1]
    fr = {"g4": {}, "chosen": {}}
    for cases in (v1, v2):
        assert H.aggregate(cases)["real"]["PD/severe"] and T.aggregate(cases, fr)["real"]["PD/severe"]
    with pytest.raises(ValueError):
        H.aggregate(v1[:2] + v2[2:])
    with pytest.raises(ValueError):
        T.aggregate(v1[:2] + v2[2:], fr)


# ------------------------------------------------------------------ patch 6: version 2 anchored at the first valid one
def test_patch6_anchored_wrapper_equals_the_patched_degrade_page():
    """page_v2.anchored (study X's wrapper) around the patched degrade_page gives exactly what the patched function
    gives by itself: records that start lifted (with a gap later, dropouts and outliers on), a record that starts
    valid, version 1."""
    from fusion.sensors import Streams
    from realdata import sensors as RS
    from rebaseline import page_v2 as PV
    patched = getattr(RS.degrade_page, "__wrapped__", RS.degrade_page)
    wrapped = PV.anchored(patched)
    t = np.arange(0, 1.2, 1e-3)
    n = len(t)
    xy = np.column_stack([0.02 * t, 0.003 * np.sin(2 * np.pi * 3 * t)])
    m = RS.PageModel(drop_rate_hz=4.0, outlier_p=0.02)
    for lead, seed, model in ((37, 5, m), (262, 11, m), (262, 23, dataclasses.replace(m, drop_rate_hz=0.2)), (0, 5, m),
                              (37, 5, dataclasses.replace(m, version=1))):
        ok = np.ones(n)
        ok[:lead] = 0.0
        ok[600:640] = 0.0
        st = Streams(tick_t=t, acc_t=t, acc_av=t, acc=np.zeros((n, 2)), pos_t=t, pos_av=t + 2e-3, pos=xy, pos_ok=ok,
                     con_t=t, con_av=t, con=np.ones(n), meta={})
        a, b = wrapped(st, model, seed), patched(st, model, seed)
        for f in ("pos_t", "pos_av", "pos", "pos_ok"):
            assert np.array_equal(np.asarray(getattr(a, f)), np.asarray(getattr(b, f))), (lead, seed, f)
        for k in ("page_reference_valid", "page_dropouts", "page_lost_intervals", "page_lost_displacement_m",
                  "page_scale_err", "page_anchor_index"):
            assert a.meta.get(k) == b.meta.get(k), (lead, seed, k)
        if lead and model.version == 2:
            assert b.meta["page_anchor_index"] == lead and not any(b.meta["page_reference_valid"][:lead])
