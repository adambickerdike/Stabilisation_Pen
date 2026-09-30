"""Adversarial relative-flow and timing tests. No patient benefit is inferred."""
import numpy as np
import pytest
from fusion.sensors import Streams
from realdata.sensors import PageModel, degrade_page, degrade_page_legacy, _window_translations, window_error_check


def stream(n=500, gap=None):
    t = np.arange(n, dtype=float) * .001
    p = np.column_stack([.02 * t, .001 * np.sin(2 * np.pi * 3 * t)])
    ok = np.ones(n)
    if gap is not None:
        ok[slice(*gap)] = 0
    return Streams(tick_t=t, acc_t=t, acc_av=t, acc=np.zeros((n, 2)),
                   pos_t=t, pos_av=t+.002, pos=p, pos_ok=ok,
                   con_t=t, con_av=t, con=np.ones(n))


def noiseless(**kw):
    args = dict(c=0., sigma=0., drift_m_s=0., scale_sd=0., outlier_p=0.,
                drop_rate_hz=0., jitter_s=0., quant_m=1e-12)
    args.update(kw)
    return PageModel(**args)


def test_future_motion_cannot_change_past_observations():
    a = stream()
    b = stream()
    b.pos[203:] += np.arange(len(b.pos)-203)[:, None] * .02
    m = PageModel(drop_rate_hz=0., outlier_p=0.)
    x, y = degrade_page(a, m, 19), degrade_page(b, m, 19)
    np.testing.assert_array_equal(x.pos[:203], y.pos[:203])
    # This is a regression witness: the old sensor reads the end of the window.
    oldx, oldy = degrade_page_legacy(a, m, 19), degrade_page_legacy(b, m, 19)
    assert not np.array_equal(oldx.pos[:203], oldy.pos[:203])


def test_identical_prefix_when_recording_is_extended():
    short, long = stream(373), stream(500)
    m = PageModel(drop_rate_hz=4, outlier_p=.02)
    a, b = degrade_page(short, m, 11), degrade_page(long, m, 11)
    for name in ('pos', 'pos_ok', 'pos_av'):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name)[:373])


def test_missing_flow_never_recovers_ground_truth_displacement():
    source = stream(gap=(100, 200))
    out = degrade_page(source, noiseless(), 1)
    np.testing.assert_allclose(out.pos[100:201], np.tile(out.pos[99], (101, 1)), atol=1e-12)
    lost = source.pos[200] - source.pos[99]
    np.testing.assert_allclose(source.pos[-1] - out.pos[-1], lost, atol=1e-12)
    assert out.meta['page_reference_valid'][99]
    assert not any(out.meta['page_reference_valid'][100:])
    assert out.pos_ok[201] == 1  # Relative reports resumed; the absolute anchor has not.


def test_zero_error_model_is_identity_without_gaps():
    source = stream()
    out = degrade_page(source, noiseless(), 0)
    np.testing.assert_allclose(out.pos, source.pos, atol=1e-12)
    assert all(out.meta['page_reference_valid'])


def test_invalid_nan_positions_are_not_interpolated_into_measurement():
    source = stream(gap=(100, 200))
    source.pos[100:200] = np.nan
    out = degrade_page(source, noiseless(), 3)
    assert np.all(np.isfinite(out.pos))
    assert not np.any(out.pos_ok[100:200])


def test_window_is_ten_intervals_not_nine():
    source = stream(31)
    source.pos[:, 1] = 0.
    d = _window_translations(source.pos_t, source.pos, source.pos_ok, .010)
    np.testing.assert_allclose(d, [.0002, .0002, .0002])


def test_window_error_does_not_hide_invalid_shared_boundary():
    source = stream(31)
    out = degrade_page(source, noiseless(), 0)
    out.pos_ok[10] = 0
    assert window_error_check(source, out)['n'] == 1


def test_invalid_model_parameters_fail_before_simulation():
    for bad in ({'outlier_p': 1.1}, {'quant_m': 0.}, {'window_s': -1.},
                {'latency_s': -.1}, {'version': 7}, {'drop_ms': (10., 1.)},
                {'window_s': float('nan')}, {'c': float('inf')}):
        with pytest.raises(ValueError):
            degrade_page(stream(), noiseless(**bad), 1)


def test_declared_latency_and_validity_are_preserved():
    source = stream()
    out = degrade_page(source, PageModel(), 1)
    assert np.all(out.pos_av >= out.pos_t + .002)
    assert np.all(np.diff(out.pos_av) >= 0)
    assert out.meta['page_model_version'] == 2


def test_record_starting_lifted_is_anchored_at_its_first_valid_report():
    """DEC-076: a record whose first reports are invalid (every recorded note starts with the pen lifted) is anchored at
    its first valid report instead of raising; from there it equals version 2 on the suffix, before it the reports are
    invalid with monotone availability and no absolute reference.  Only a record with no valid report raises."""
    import dataclasses
    m = PageModel(drop_rate_hz=4, outlier_p=.02)
    source = stream(gap=(0, 37))
    out = degrade_page(source, m, 11)
    suffix = dataclasses.replace(source, pos_t=source.pos_t[37:], pos_av=source.pos_av[37:], pos=source.pos[37:],
                                 pos_ok=source.pos_ok[37:])
    ref = degrade_page(suffix, m, 11)
    for name in ('pos', 'pos_ok', 'pos_av'):
        np.testing.assert_array_equal(getattr(out, name)[37:], getattr(ref, name))
    assert not np.any(out.pos_ok[:37]) and np.all(np.diff(out.pos_av) >= 0)
    assert np.all(out.pos_av >= out.pos_t + m.latency_s)
    rv = out.meta['page_reference_valid']
    assert not any(rv[:37]) and rv[37:] == ref.meta['page_reference_valid'] and out.meta['page_anchor_index'] == 37
    assert degrade_page(stream(gap=(0, 499)), noiseless(), 1).pos_ok.tolist() == [0.] * 499 + [1.]
    with pytest.raises(ValueError):
        degrade_page(stream(gap=(0, 500)), m, 11)


def test_record_starting_valid_and_version_1_are_unchanged_by_the_anchor():
    """The anchoring leaves a record that starts valid as version 2 gave it before (values of the unpatched code for
    this record, model and seed), and version 1 passes through to the legacy model."""
    out = degrade_page(stream(), PageModel(drop_rate_hz=4, outlier_p=.02), 11)
    assert out.pos[:, 0].sum() == pytest.approx(2.2849204999999997, rel=1e-12)
    assert out.pos[:, 1].sum() == pytest.approx(0.3067558, rel=1e-12)
    assert out.pos_av.sum() == pytest.approx(125.98967465780423, rel=1e-12)
    assert out.pos_ok.sum() == 401 and sum(out.meta['page_reference_valid']) == 64
    assert out.meta['page_dropouts'] == 1 and 'page_anchor_index' not in out.meta
    source = stream(gap=(0, 37))
    m1 = PageModel(version=1)
    a, b = degrade_page(source, m1, 3), degrade_page_legacy(source, m1, 3)
    for name in ('pos', 'pos_ok', 'pos_av'):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))
