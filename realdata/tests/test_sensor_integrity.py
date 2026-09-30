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
