"""Reproduce adversarial sensor-model checks; these are software experiments, not device data.

Run: python -m realdata.sensor_integrity_study
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from fusion.sensors import Streams
from realdata.sensors import PageModel, degrade_page, degrade_page_legacy
from rig.pagesense import stroke_error, window_errors
from stabpen.provenance import metadata


def make_stream(n=1001, gap=None):
    t = np.arange(n, dtype=float) * .001
    xy = np.column_stack([.02 * t, .001 * np.sin(2 * np.pi * 3 * t)])
    ok = np.ones(n)
    if gap:
        ok[slice(*gap)] = 0
    return Streams(tick_t=t, acc_t=t, acc_av=t, acc=np.zeros((n, 2)),
                   pos_t=t, pos_av=t+.002, pos=xy, pos_ok=ok,
                   con_t=t, con_av=t, con=np.ones(n))


def run(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    clean = PageModel(c=0, sigma=0, drift_m_s=0, scale_sd=0, outlier_p=0,
                      drop_rate_hz=0, jitter_s=0, quant_m=1e-12)
    gap = make_stream(gap=(200, 300))
    old = degrade_page_legacy(gap, clean, 19)
    new = degrade_page(gap, clean, 19)
    a, b = make_stream(), make_stream()
    b.pos[203:] += np.arange(len(b.pos)-203)[:, None] * .02
    noisy = replace(clean, c=20e-6, sigma=1., quant_m=25.4e-3/6000)
    future = {}
    for name, fn in (("legacy", degrade_page_legacy), ("causal_v2", degrade_page)):
        aa, bb = fn(a, noisy, 19), fn(b, noisy, 19)
        future[name] = float(np.max(np.linalg.norm(aa.pos[:203]-bb.pos[:203], axis=1))*1e6)
    unknown = stroke_error(a.pos_t, a.pos*1e6, a.pos_t, a.pos*1e6, valid=np.zeros(len(a.pos_t), bool))
    no_windows = window_errors(a.pos_t, a.pos*1e6, a.pos_t, a.pos*1e6, valid=np.zeros(len(a.pos_t), bool))
    report = {
        "stabpen.provenance": metadata("SOFTWARE VERIFICATION with synthetic trajectories; no physical measurements", seeds=[19]),
        "gap_case": {"speed_x_mm_s": 20., "invalid_reports": 100,
                     "lost_intervals": new.meta['page_lost_intervals'],
                     "legacy_final_x_error_mm": float((gap.pos[-1, 0]-old.pos[-1, 0])*1e3),
                     "causal_final_x_error_mm": float((gap.pos[-1, 0]-new.pos[-1, 0])*1e3),
                     "expected_unobserved_x_mm": float((gap.pos[300, 0]-gap.pos[199, 0])*1e3),
                     "absolute_reference_valid_after_gap": bool(new.meta['page_reference_valid'][-1]),
                     "meaning": "A larger reported error is an honesty correction: missing motion is no longer supplied by ground truth."},
        "future_mutation_max_change_in_past_um": future,
        "all_invalid_metrology": {"stroke_valid": unknown['valid'], "window_valid": no_windows['valid'],
                                  "n_windows": no_windows['n_windows'], "rms_um": None,
                                  "reason": "No valid measurement; never score zero error."},
        "interpretation": "DeltaPen's translation-magnitude summary cannot identify a causal vector-error distribution. Both model shape and ordinary-paper transfer remain assumptions."
    }
    (output/'sensor_integrity.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    np.savetxt(output/'dropout_trace.csv', np.column_stack([gap.pos_t, gap.pos[:,0]*1e3,
               old.pos[:,0]*1e3, new.pos[:,0]*1e3, gap.pos_ok]), delimiter=',',
               header='time_s,true_x_mm,legacy_x_mm,causal_x_mm,flow_valid', comments='')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8,4.4), constrained_layout=True)
    ax.plot(gap.pos_t, gap.pos[:,0]*1e3, color='#8897a8', lw=4, label='True path')
    ax.plot(gap.pos_t, old.pos[:,0]*1e3, '--', color='#b75c31', label='Legacy: restores unseen motion')
    ax.plot(gap.pos_t, new.pos[:,0]*1e3, color='#006e7f', lw=2, label='Causal: retains missing displacement')
    ax.axvspan(.2,.3, alpha=.12, color='black', label='Optical dropout')
    ax.set(xlabel='Time (s)', ylabel='Integrated x position (mm)', title='A tracking gap requires an absolute re-anchor')
    ax.grid(alpha=.18); ax.legend(frameon=False, fontsize=9)
    fig.savefig(output/'dropout_integrity.png', dpi=180); plt.close(fig)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/improvement/sensing'))
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, allow_nan=False))
