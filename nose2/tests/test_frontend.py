"""The vectorised front-end closure equals opt/inertial/front_end.py at the Rev H point (CALC verification)."""
from __future__ import annotations

from dataclasses import replace

from nose2 import frontend as FEN


def test_matches_original_at_revh():
    from opt.inertial import front_end as FE
    from opt.inertial.revh import RevH
    a = FEN.check(6.75, FEN.Nose(z_p=45.0, travel=3.0))
    b = FE.check(6.75, replace(RevH(), travel=3e-3, z_p=45e-3), replace(FE.FrontRules(), stop=3.5), n_theta=9, n_phi=24)
    keys = [k for k in a if k in b and isinstance(a[k], (int, float)) and isinstance(b[k], (int, float))]
    assert len(keys) >= 8
    assert max(abs(float(a[k]) - float(b[k])) for k in keys) < 1e-9


def test_revh_size_and_growth():
    s3 = FEN.size(FEN.Nose(z_p=45.0, travel=3.0))
    assert abs(s3["R_mm"] - 6.75) < 1e-9                      # DEC-034
    assert 13.0 < s3["refill_slide_range_mm"] < 14.0          # DEC-034: about 13.5 mm
    s6 = FEN.size(FEN.Nose(z_p=45.0, travel=6.0))
    assert s6["passes"] and s6["R_mm"] > s3["R_mm"] and s6["refill_slide_range_mm"] > s3["refill_slide_range_mm"]
    assert s6["ball_travel_usable_min_mm"] < 6.0              # the guaranteed minimum is below the nominal travel
