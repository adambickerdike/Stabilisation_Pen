"""Design models: part masses add up, constraints bite, the optimiser's summary is consistent."""
import math

import torch

from endcap import design as DS
from endcap import optimise as OP
from endcap import params as P


def test_lrm_parts_sum_and_stroke():
    d = DS.lrm2(dict(d_s=10e-3, L_s=14e-3, t_c=1.0e-3))
    s = sum(float(v) for v in d["parts"].values()) * 1e-3
    assert abs(s - float(d["m_total"])) < 1e-9
    assert abs(float(d["X"]) - ((24e-3 - 10e-3) / 2 - 1e-3 - 1e-3 - 0.5e-3)) < 1e-12
    assert float(d["viol"]["flexure"]) > 0            # 4.5 mm stroke exceeds the 4 mm flexure limit


def test_cmg_parts_sum_momentum_and_fit():
    d = DS.cmg(dict(D=18e-3, t=3e-3, n=20000.0, delta=1.0), arr="DG1", motor="0824B")
    s = sum(float(v) for v in d["parts"].values()) * 1e-3
    assert abs(s - float(d["m_total"])) < 1e-9
    m = P.RHO_WHA * math.pi / 4 * (0.018 ** 2 - 0.002 ** 2) * 0.003
    J = m * (0.018 ** 2 + 0.002 ** 2) / 8 + P.MOTORS["0824B"].J
    assert abs(float(d["H"]) - J * 20000 * 2 * math.pi / 60) < 1e-12
    big = DS.cmg(dict(D=24e-3, t=3e-3, n=20000.0, delta=1.0), arr="DG1", motor="0824B")
    assert float(big["viol"]["radial"]) > 0            # a 24 mm rotor with two gimbal rings does not fit the 24 mm bore
    four = DS.cmg(dict(D=18e-3, t=3e-3, n=20000.0, delta=1.0), arr="SP2", motor="0620B")
    assert float(four["viol"]["length"]) > 0           # two scissored pairs are too long for 45 mm


def test_summary_consistency():
    s = OP.summarize("LRM2", dict(d_s=10e-3, L_s=14e-3, t_c=1.0e-3), ())
    assert s["class"] == "LRM2" and 0 < s["tremor_mean"] < 1.5 and s["steer_3Hz_mm"] >= 0
    assert s["battery_h_14500"] > s["battery_h_10440"]
    with torch.no_grad():
        w = OP.passive_weight_ratio(0.03)
    assert max(w.values()) > 1.0                        # a fixed rear mass amplifies some tremor frequencies (resonance)


def test_lrm_coil_cap_is_flexure_aware():
    """The reaction mass's coil-force cap drives the slug through 0.7 of its stroke on the 5 Hz flexure: about 25x the
    free-slug force m w^2 X at 1 Hz, about 1x at 10 Hz (then limited by the coil)."""
    import math
    import torch
    from endcap import design as DS
    x = {"d_s": torch.tensor(10e-3, dtype=torch.float64), "L_s": torch.tensor(18e-3, dtype=torch.float64), "t_c": torch.tensor(1.4e-3, dtype=torch.float64)}
    d = DS.lrm2(x)
    m, X = float(d["m_r"]), float(d["X"])
    for f, lo, hi in ((1.0, 20.0, 30.0), (10.0, 0.9, 1.1)):
        free = 0.7 * m * (2 * math.pi * f) ** 2 * X
        cap = float(DS.lrm_limit(d, f)[0])
        assert lo < min(cap, 1e9) / free < hi or cap == float(d["F_act"])
