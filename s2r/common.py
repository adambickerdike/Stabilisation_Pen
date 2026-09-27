"""Output helpers: provenance-stamped JSON and evidence-stamped figures.

Every JSON written by s2r carries stabpen.provenance.metadata() and an
``evidence`` block; every figure carries a plotstyle.stamp() footer. Values in
these files are SIMULATION (virtual bench, M1 twin) or CALCULATION (analytic,
fitted); instrument figures are labelled PROTOCOL or ASSUMPTION at their source
(s2r/instruments.py).
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager

import numpy as np

from . import RESULTS
from stabpen import plotstyle, provenance


def out_path(*parts) -> str:
    p = os.path.join(RESULTS, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def write_result(name: str, payload: dict, evidence: str, seeds=None, extra=None) -> str:
    """Write results/s2r/<name>.json with provenance metadata."""
    meta = provenance.metadata(evidence, seeds=seeds, extra=extra)
    path = out_path(name if name.endswith(".json") else name + ".json")
    provenance.write_json(path, {"meta": meta, **payload})
    return path


def figure(nrows=1, ncols=1, figsize=(7.2, 3.8), **kw):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    return plt.subplots(nrows, ncols, figsize=figsize, **kw)


def save_figure(fig, name: str, status: str, note: str = "") -> str:
    import matplotlib.pyplot as plt
    plotstyle.stamp(fig, status, note)
    fig.tight_layout()
    path = out_path(name if name.endswith(".png") else name + ".png")
    fig.savefig(path)
    plt.close(fig)
    return path


@contextmanager
def timed(label: str, log: dict):
    t0 = time.time()
    yield
    log[label] = round(time.time() - t0, 2)


def rel_err(est, true):
    est = np.asarray(est, float)
    true = np.asarray(true, float)
    return (est - true) / np.where(true == 0, 1.0, np.abs(true))


def summarize(x):
    """Median, 10/90 percentiles, RMS and |x| 95th percentile of an array (NaN-safe)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    return {"n": int(x.size), "median": float(np.median(x)), "p10": float(np.percentile(x, 10)),
            "p90": float(np.percentile(x, 90)), "rms": float(np.sqrt(np.mean(x ** 2))),
            "abs_p95": float(np.percentile(np.abs(x), 95)), "mean": float(np.mean(x))}
