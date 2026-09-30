"""Qualification must not turn missing optical reports into accurate measurements."""
import numpy as np
from rig.pagesense import window_errors, stroke_error


def fixture():
    t = np.arange(31) * .001
    xy = np.column_stack([20000 * t, np.zeros_like(t)])  # um, 20 mm/s
    return t, xy


def test_all_invalid_has_no_fabricated_zero_error_stroke():
    t, xy = fixture()
    result = stroke_error(t, xy, t, xy, valid=np.zeros(len(t), bool))
    assert not result['valid']
    assert np.isnan(result['rms_um']) and result['run_s'] == 0


def test_all_invalid_windows_are_reported_without_percentile_crash():
    t, xy = fixture()
    result = window_errors(t, xy, t, xy, valid=np.zeros(len(t), bool))
    assert not result['valid'] and result['n_windows'] == 0
    assert np.isnan(result['vec_p95_um'])


def test_invalid_boundary_excludes_each_adjacent_window():
    t, xy = fixture()
    valid = np.ones(len(t), bool)
    valid[10] = False
    result = window_errors(t, xy, t, xy, valid=valid)
    assert result['excluded_windows'] == 2


def test_interpolation_does_not_bridge_invalid_bracket():
    t, xy = fixture()
    valid = np.ones(len(t), bool)
    valid[10] = False
    # Truth timestamps make the window endpoint fall between samples10 and11.
    result = window_errors(t + .0005, xy, t, xy, valid=valid)
    assert result['excluded_windows'] == 2


def test_valid_data_retains_zero_error_and_count():
    t, xy = fixture()
    result = window_errors(t, xy, t, xy)
    stroke = stroke_error(t, xy, t, xy)
    assert result['valid'] and result['vec_mae_um'] == 0
    assert stroke['valid'] and stroke['rms_um'] == 0
