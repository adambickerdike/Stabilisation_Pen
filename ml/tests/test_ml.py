"""Unit and consistency tests for the ml/ pipeline (SIMULATION / synthetic data).

Run: python3 -m pytest -p no:cacheprovider ml/tests -q
(-p no:cacheprovider keeps pytest from writing .pytest_cache outside ml/.)
Tests that need generated artefacts (datasets, trained model, C build) are skipped
when those artefacts are absent.
"""
from __future__ import annotations

import json
import os
import subprocess

import numpy as np
import pytest

from ml import common as C  # noqa: F401  (sets byte-code / numba cache guards first)
from ml import baselines as BL
from ml import metrics as MT
from ml import models as M
from ml import quantize as Q
from ml import synth
from stabpen import signals as sg

HAVE_DATA = os.path.exists(os.path.join(C.RUNS, "data", "test.npz"))


def _have_int8(name):
    return os.path.exists(os.path.join(C.RESULTS, "model", f"{name}_int8.npz"))


def test_kf_step_is_a_verbatim_port_of_the_simulator():
    from sim.pensim import core   # pure-Python original via .py_func: nothing is compiled into sim/
    rng = np.random.default_rng(0)
    for _ in range(20):
        x = rng.normal(size=5) * 1e-4
        A = rng.normal(size=(5, 5)) * 1e-4
        P = A @ A.T + np.eye(5) * 1e-9
        args = (float(rng.normal() * 1e-4), 0.004, 2 * np.pi * rng.uniform(3, 12), 0.99, 3.0, 1e-8, 3e-12)
        x1, P1 = x.copy(), P.copy()
        x2, P2 = x.copy(), P.copy()
        r1 = BL._kf_step(x1, P1, *args)
        r2 = core._kf_step.py_func(x2, P2, *args)
        np.testing.assert_allclose(x1, x2, rtol=1e-12, atol=1e-18)
        np.testing.assert_allclose(P1, P2, rtol=1e-12, atol=1e-24)
        np.testing.assert_allclose(r1, r2, rtol=1e-12)


@pytest.mark.parametrize("burst,bb", [(0.0, 0.0), (0.3, 0.0), (0.0, 2e-5), (0.2, 1e-5)])
def test_tremor_wrapper_reproduces_stabpen(burst, bb):
    t = np.arange(4000) * 1e-3
    spec = sg.TremorSpec(f0=6.3, amp_pk=4e-4, burst_rate=burst, broadband_rms=bb)
    a = sg.tremor(t, spec, np.random.default_rng(5))
    b, st = synth.tremor_with_state(t, spec, np.random.default_rng(5))
    np.testing.assert_array_equal(a, b)
    assert set(st) == {"f", "phase", "amp", "extra"}


def test_oscillator_oracle_is_exact_at_zero_horizon():
    t = np.arange(3000) * 1e-3
    spec = sg.TremorSpec(f0=8.0, amp_pk=3e-4)
    d, s = synth.tremor_with_state(t, spec, np.random.default_rng(1))
    st = {"phase": s["phase"], "f": s["f"], "amp": s["amp"], "env": np.ones(len(t)), "harm": np.full(len(t), spec.harmonic),
          "ell": np.full(len(t), spec.ellipticity), "ori": np.full(len(t), spec.orientation), "hph": np.full(len(t), 0.7)}
    np.testing.assert_allclose(synth.oscillator_oracle(st, 0.0), d, atol=1e-15)


@pytest.mark.parametrize("c_in", [2, 3])
def test_tcn_output_depends_only_on_the_window(c_in):
    torch = pytest.importorskip("torch")
    torch.manual_seed(0)
    model = M.TCNTree(**M.CONFIGS["tcn_s"], c_in=c_in)
    rng = np.random.default_rng(2)
    n = 300
    rec = {"dp_um": rng.normal(0, 50, (n, 2)).astype(np.float32), "f_est": rng.uniform(4, 10, n).astype(np.float32)}
    base = M.predict(model, rec)
    k = 200
    rec2 = {"dp_um": rec["dp_um"].copy(), "f_est": rec["f_est"].copy()}
    rec2["dp_um"][k + 1:] += 500.0            # change the future
    rec2["dp_um"][: k - C.W + 1] -= 300.0      # change the distant past (outside the 64-sample window)
    rec2["f_est"][k + 1:] = 2.0
    p2 = M.predict(model, rec2)
    np.testing.assert_allclose(base[k], p2[k], atol=1e-9)
    assert not np.allclose(base[k + 1], p2[k + 1])


@pytest.mark.parametrize("c_in", [2, 3])
def test_tree_equals_streaming_dilated_tcn(c_in):
    torch = pytest.importorskip("torch")
    torch.manual_seed(1)
    model = M.TCNTree(**M.CONFIGS["tcn_s"], c_in=c_in)
    rng = np.random.default_rng(3)
    n = 400
    dp = rng.normal(0, 60, (n, 2)).astype(np.float32)
    f = np.full(n, 6.5, np.float32)                  # constant f_est (3 channels) or none (2): exact equivalence
    ch = M.input_channels(dp, f, c_in)
    stream = M.stream_reference(model, ch) * C.S_OUT
    tree = M.predict(model, {"dp_um": dp, "f_est": f})
    np.testing.assert_allclose(stream[C.W - 1:], tree[C.W - 1:], rtol=1e-4, atol=1e-3)


def _requant_scalar(v, m, s):
    """Independent scalar re-implementation of CMSIS-NN arm_nn_requantize (Python ints)."""
    left, right = max(s, 0), max(-s, 0)
    x = v * (1 << left)
    prod = x * m + (1 << 30)
    hi = prod >> 31
    if right == 0:
        return hi
    mask = (1 << right) - 1
    rem = hi & mask
    res = hi >> right
    thr = (mask >> 1) + (1 if res < 0 else 0)
    return res + (1 if rem > thr else 0)


def test_requantize_matches_independent_scalar_version():
    rng = np.random.default_rng(4)
    for _ in range(500):
        s = int(rng.integers(-24, 3))
        m = int(rng.integers(1 << 30, (1 << 31) - 1))
        lim = (1 << 30) >> max(s, 0)
        v = int(rng.integers(-lim, lim))
        assert int(Q.requantize(np.array([v], np.int64), m, s)[0]) == _requant_scalar(v, m, s)


def test_quantize_multiplier_roundtrip():
    for x in (1e-6, 0.00371, 0.5, 0.999, 1.7, 3.2):
        q, s = Q.quantize_multiplier(x)
        assert (1 << 30) <= q < (1 << 31)
        assert abs(q * 2.0 ** (s - 31) - x) / x < 1e-9


def test_metrics_definitions():
    rng = np.random.default_rng(5)
    n = 2000
    rec = {"t": np.arange(n) * C.TS, "pen_tgt": np.ones(n, bool), "env_tgt": np.r_[np.ones(n // 2), np.zeros(n // 2)],
           "f0_tgt": np.r_[np.full(n // 2, 9.0), np.zeros(n // 2)], "d_tgt_um": rng.normal(0, 100, (n, 2))}
    rec["d_tgt_um"][n // 2:] = 0.0
    perfect = MT.stack([MT.rec_stats(rec, rec["d_tgt_um"])])
    zero = MT.stack([MT.rec_stats(rec, np.zeros((n, 2)))])
    assert MT.pooled(perfect)["rr_all"] < 1e-12
    assert abs(MT.pooled(zero)["rr_all"] - 1.0) < 1e-12
    noisy = rec["d_tgt_um"] + rng.normal(0, 30, (n, 2))
    st = MT.stack([MT.rec_stats(rec, noisy)])
    g, _ = MT.select_gain(st, 10.0)
    assert abs(MT.pooled(st, g)["fc_um"] - 10.0) < 1e-6 or g == MT.select_gain(st, 1e9)[0]


@pytest.mark.skipif(not HAVE_DATA, reason="datasets not built")
def test_leakage_checks_pass():
    man = json.load(open(os.path.join(C.RESULTS, "dataset_manifest.json")))
    assert man["leakage_checks"]["all_pass"] is True


def test_schema_examples_validate():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(os.path.join(C.DATA_DIR, "schema", "ml_sample.schema.json")))
    jsonschema.Draft202012Validator.check_schema(schema)
    path = os.path.join(C.DATA_DIR, "samples", "ml_samples_example.json")
    if not os.path.exists(path):
        pytest.skip("no example samples")
    for s in json.load(open(path))["samples"]:
        jsonschema.validate(s, schema)
        assert s["evidence_status"] == C.EVIDENCE


def test_fest_free_model_reduces_exactly_to_two_channels():
    """models.drop_fest: a 3-channel TCN whose f_est input is held at zero equals the
    2-channel TCN without the f_est weight columns (contract v1.1 export of tcn_s_nofest)."""
    torch = pytest.importorskip("torch")
    torch.manual_seed(5)
    m3 = M.build("tcn_s")
    m3.use_fest = False
    with torch.no_grad():                            # make the dropped columns large: they must not matter
        m3.levels[0].weight[:, [2, 5]] = 3.0
    m2 = M.drop_fest(m3)
    assert m2.c_in == 2 and not m2.use_fest and m2.config()["c_in"] == 2
    assert m2.macs() == m3.macs() - 32 * 2 * 8 and m2.n_params() == m3.n_params() - 2 * 8
    rng = np.random.default_rng(6)
    n = 500
    rec = {"dp_um": rng.normal(0, 80, (n, 2)).astype(np.float32), "f_est": rng.uniform(4, 12, n).astype(np.float32)}
    p3, p2 = M.predict(m3, rec), M.predict(m2, rec)
    np.testing.assert_allclose(p2, p3, rtol=0, atol=1e-3)            # um; float32 summation order only
    np.testing.assert_array_equal(p2, M.predict(m2, {"dp_um": rec["dp_um"]}))   # f_est not needed at all


def test_deployed_nofest_model_equals_its_training_form():
    torch = pytest.importorskip("torch")
    name = C.EXPORT_MODEL
    path = os.path.join(C.RESULTS, "model", f"{name}.pt")
    if not os.path.exists(path):
        pytest.skip("model not trained")
    cfg = json.load(open(os.path.join(C.RESULTS, "model", f"{name}.json")))
    assert M.deployed_c_in(cfg) == 2, "the exported model implements contract v1.1 (no f_est)"
    m3 = M.TCNTree(channels=tuple(cfg["channels"]), head=cfg["head"], c_in=cfg["c_in"])
    m3.load_state_dict(torch.load(path))
    m3.use_fest = bool(cfg["use_fest"])
    m2, _ = Q.load_float(name)
    assert m2.c_in == 2
    rng = np.random.default_rng(7)
    n = 800
    rec = {"dp_um": rng.normal(0, 60, (n, 2)).astype(np.float32), "f_est": rng.uniform(4, 12, n).astype(np.float32)}
    np.testing.assert_allclose(M.predict(m2, rec), M.predict(m3, rec), rtol=0, atol=1e-3)


def test_two_channel_input_quantiser_is_the_dp_part():
    rng = np.random.default_rng(8)
    n = 300
    dp = rng.normal(0, 150, (n, 2)).astype(np.float32)
    f = rng.uniform(3, 13, n).astype(np.float32)
    q3, q2 = Q.quantize_inputs(dp, f, 3), Q.quantize_inputs(dp, None, 2)
    np.testing.assert_array_equal(q2, q3[:, :2])
    w3, w2 = Q.int_windows(q3), Q.int_windows(q2)
    assert w2.shape == (n, C.W, 2) and w3.shape == (n, C.W, 3)
    np.testing.assert_array_equal(w2, w3[:, :, :2])


@pytest.mark.skipif(not _have_int8(C.EXPORT_MODEL), reason="exported model not quantised")
def test_committed_export_is_the_export_model():
    """ml/export/ holds the int8 model C.EXPORT_MODEL: channel count, name and hash agree."""
    import re
    qm = Q.load_qmodel(os.path.join(C.RESULTS, "model", f"{C.EXPORT_MODEL}_int8.npz"))
    txt = open(os.path.join(C.EXPORT, "tcn_model.h")).read()
    d = dict(re.findall(r"#define (TCN_\w+) (\S+)", txt))
    assert int(d["TCN_CIN"]) == Q.qm_c_in(qm) == 2
    assert d["TCN_MODEL_NAME"] == f'"{C.EXPORT_MODEL}"'
    assert d["TCN_MODEL_HASH_LOW32"].lower() == f"0x{qm['hash'][-8:]}u"
    w = open(os.path.join(C.EXPORT, "tcn_weights.h")).read()
    assert f"TCN_L0_W[{qm['layers'][0]['c_out']}][{2 * Q.qm_c_in(qm)}]" in w
    assert "TCN_F_INV_SCALE" not in w                # no f_est quantiser in a 2-channel export


@pytest.mark.skipif(not HAVE_DATA, reason="data not built")
@pytest.mark.parametrize("name", [C.EXPORT_MODEL, "tcn_s"])
def test_int8_reference_is_close_to_float(name):
    from ml import datasets as D
    if not _have_int8(name):
        pytest.skip(f"{name} not quantised")
    model, _ = Q.load_float(name)
    qm = Q.load_qmodel(os.path.join(C.RESULTS, "model", f"{name}_int8.npz"))
    assert Q.qm_c_in(qm) == model.c_in
    rec = D.load_split("test")[0]
    pf, pq = M.predict(model, rec), Q.predict_int8(qm, rec)
    m = MT.score_mask(rec)
    assert np.sqrt(np.mean((pf[m] - pq[m]) ** 2)) < 15.0


@pytest.mark.skipif(not os.path.exists(os.path.join(C.RUNS, "export_build", "test_host")), reason="C test not built")
def test_c_host_bit_exact():
    exe = os.path.join(C.RUNS, "export_build", "test_host")
    binp = os.path.join(C.RUNS, "export_build", "vectors_test_20000.bin")
    out = subprocess.run([exe, binp], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stdout
    assert "RESULT PASS" in out.stdout
