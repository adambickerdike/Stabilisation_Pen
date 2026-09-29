"""Image convention and the gap-flux surrogate against magpylib (CALC verification)."""
from __future__ import annotations

import numpy as np

from nose2 import designs as DS
from nose2 import magnetics as MG


def test_image_convention():
    assert MG.image_check()["max_abs_diff_T"] < 1e-9


def test_surrogates_on_a_subset():
    for kind, coef, tol in (("radial", DS.ETA_RADIAL, 0.30), ("axial", DS.ETA_AXIAL, 0.30)):
        rows = MG.surrogate_rows(kind, npts=5, every=61 if kind == "radial" else 23)
        chk = MG.check_surrogate(kind, rows, coef)
        assert chk["rel_max"] < tol, (kind, chk["rel_max"])


def test_revh_recalibration():
    r = DS.revh_as_designed(1.33)
    assert abs(r["Km_act_lumped"] - 0.46) < 0.02               # reproduces Rev H's 0.47 N/sqrt(W) with eta 0.55
    assert r["Km_act_images"] < 0.5 * r["Km_act_lumped"]       # the image calculation is much lower
    # the surrogate at the Rev H point against magpylib directly
    w, l, t_m, g, t_c = 3.0e-3, 6.5e-3, 2.8e-3, 0.5e-3 + 2.27e-3, 1.43e-3
    B = MG.radial_B(w, l, t_m, g, t_c, npts=5)
    eta = B / (MG.BR * t_m / (t_m + g + t_c))
    assert abs(r["eta_images"] / eta - 1.0) < 0.15
