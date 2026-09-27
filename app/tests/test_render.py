"""SVG rendering: well-formed, faithful geometry, force-to-width, overlays, determinism."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np

from penapp import render
from penapp.render import RenderOptions, render_svg

NS = "{http://www.w3.org/2000/svg}"


def _ink(svg: str):
    root = ET.fromstring(svg.encode())
    return root, [e for e in root.iter() if e.get("class", "").startswith("ink")]


def test_svg_is_well_formed_and_draws_every_stroke(loaded):
    store, ids = loaded
    orig = store.original_for_note(ids["a"])
    svg = render.render_note(store, ids["a"])
    root, ink = _ink(svg)
    assert root.tag == NS + "svg" and "SYNTHETIC" in svg
    assert {int(e.get("data-stroke-id")) for e in ink} == set(orig.stroke_ids)
    assert orig.sha256 in root.find(NS + "desc").text


def test_geometry_is_exact_and_y_is_flipped(loaded):
    store, ids = loaded
    orig = store.original_for_note(ids["a"])
    _, ink = _ink(render.render_note(store, ids["a"]))
    sid, a, b = orig.stroke_runs[5]
    poly = next(e for e in ink if e.get("data-stroke-id") == str(sid))
    pts = np.array([[float(v) for v in p.split(",")] for p in poly.get("points").split()])
    s = orig.samples[a:b]
    assert np.allclose(pts[:, 0], s["x_um"] / 1000.0, atol=5e-4)       # mm with 1 um resolution
    assert np.allclose(pts[:, 1], -s["y_um"] / 1000.0, atol=5e-4)      # page y up -> SVG y down


def test_force_width_varies_with_force(loaded):
    store, ids = loaded
    _, ink = _ink(render.render_note(store, ids["a"], force_width=True))
    widths = {float(e.get("stroke-width")) for e in ink if e.tag == NS + "polyline"}
    assert len(widths) >= 3
    lo, hi = RenderOptions().width_range_mm
    assert lo <= min(widths) and max(widths) <= hi


def test_overlays_and_highlight(loaded):
    store, ids = loaded
    for kind in ("segmentation", "text"):
        root = ET.fromstring(render.render_note(store, ids["a"], overlay=kind).encode())
        g = [e for e in root.iter(NS + "g") if e.get("class") == "overlay"]
        assert len(g) == 1 and g[0].get("data-layer-id")
    txt = [e.text for e in ET.fromstring(render.render_note(store, ids["a"], overlay="text").encode()).iter(NS + "text")]
    assert "library" in txt
    svg = render.render_note(store, ids["a"], highlight_ranges=[[0, 2]], caption=["Q: x", "A: y [S1]"])
    _, ink = _ink(svg)
    hl = {int(e.get("data-stroke-id")) for e in ink if "highlighted" in e.get("class")}
    assert hl == {0, 1, 2} and "A: y [S1]" in svg


def test_hand_path_overlay_on_research_session(tmp_path):
    from conftest import TRACE
    import pytest
    if not TRACE.exists():
        pytest.skip("simulator traces not present")
    from penapp.cli import import_log_file
    from penapp.notes import NoteStore
    from penapp.synth import synth_sim_session
    log = tmp_path / "sim.penlog"
    synth_sim_session(TRACE).write(log)
    st = NoteStore(tmp_path / "s")
    s = import_log_file(st, log)
    assert s["layers"]["hand_path_estimate"]
    layer = st.get_layer(s["layers"]["hand_path_estimate"])
    al = layer["payload"]["origin_alignment"]
    assert al["mode"] == "fit" and al["residual_rms_um"] < 60 and al["J_est"] is not None
    root = ET.fromstring(render.render_note(st, s["note_id"], overlay="hand_path_estimate").encode())
    assert [e for e in root.iter(NS + "polyline") if e.get("class") == "hand-path"]


def test_rendering_is_deterministic_and_leaves_original_untouched(loaded):
    store, ids = loaded
    orig = store.original_for_note(ids["a"])
    before = orig.payload
    a = render.render_note(store, ids["a"], overlay="text", force_width=True)
    b = render.render_note(store, ids["a"], overlay="text", force_width=True)
    assert a == b
    assert store.get_original(orig.sha256, use_cache=False).payload == before


def test_single_sample_stroke_renders_as_dot():
    from penapp import logfmt
    from penapp.notes import OriginalLayer
    arr = np.zeros(1, dtype=logfmt.STROKE_DTYPE)
    arr[0] = (0, 4, 10, 20, 500, 100, 0)
    svg = render_svg(OriginalLayer(arr.tobytes()))
    assert '<circle class="ink" data-stroke-id="4"' in svg
