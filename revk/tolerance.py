r"""Nib-centring tolerance stack of Rev K (CALCULATION; every contributor an ASSUMPTION that a named test pins).

Two questions, kept apart:
  sensing   where the servo believes the centre is against where it is: the TMAG5170's zero after the factory
            calibration, its offset drift over the pen's temperature range, the position magnet's Br temperature
            coefficient (a gain error that grows with the displacement), the Earth's field turning with the pen, and the
            coil current's field left after the cross-talk calibration.  These move the ball on the page (a slow offset).
  mechanics where the stops, coils, ring and guides are against the handle's axis: the carrier's rest position on its
            wires, the magnets' and the coils' positions, the ring's and the anchor ring's coaxiality.  These do not move
            the ink (the servo holds whatever the sensor calls zero) but eat the usable travel in the worst direction and
            the running clearances (the ring bore, the coil against the bore, the refill against the page-sensor optics).
Monte Carlo over the contributors, each drawn uniformly between its limits (a conservative shape for machining and
assembly tolerances) unless stated.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from . import ensure_paths
from . import params as PR
from .params import V, val

ensure_paths()

ASM, MFR, PD = PR.ASM, PR.MFR, PR.PD

SENSING = {
    "hall_zero_residual_um": V(5.0, "um (1 sigma)", ASM, "factory zero against a mechanical centring jig (EXP-B24 / EXP-T09 set it)"),
    "hall_offset_drift_uT_per_K": V(1.0, "uT/K", ASM, "TMAG5170 offset drift: not read from the datasheet in this study; "
                                    "EXP-T09 measures it over 15-45 degC"),
    "temp_span_K": V(15.0, "K", ASM, "pen from 20 to 35 degC between calibrations (in the hand)"),
    "br_tempco_pct_per_K": V(-0.12, "%/K", ASM, "sintered NdFeB reversible Br coefficient (typical; the magnet's grade sheet "
                             "pins it, AMF-139 class)"),
    "earth_uT": V(50.0, "uT", ASM, "the Earth's field, turning with the pen (slow)"),
    "coil_crosstalk_residual": V(0.05, "-", ASM, "share of the coil field left after the current calibration (EXP-B24)"),
    "coil_I_rms_A": V(0.06, "A", PR.CALC, "from study B's duty (params NIB coil_I_rms_duty_A)"),
}

MECH = {  # half-ranges (mm), uniform
    "carrier_rest_offset": V(0.05, "mm", ASM, "the carrier's rest position on its four wires after soldering / welding "
                             "(residual stress); the servo holds centre, so this costs travel only (EXP-B25 jig)"),
    "magnet_assembly": V(0.05, "mm", ASM, "the four pole magnets' centre against the bore (bonded in a pocketed back plate)"),
    "coil_on_carrier": V(0.05, "mm", ASM, "the coil layers' centre on the carrier flange"),
    "ring_to_axis": V(0.03, "mm", ASM, "the skid ring and the sleeve against the handle's axis (moulded, machined at 100)"),
    "anchor_to_axis": V(0.03, "mm", ASM, "the wire anchor ring against the handle's axis"),
    "guide_station_play": V(0.01, "mm", ASM, "the rolling guide stations' radial play"),
    "optics_block": V(0.05, "mm", ASM, "the page-sensor lens and mirror block against the ring"),
}


def sensing(gradient_mT_per_mm: float, crosstalk_um_per_A: float, earth_um: float, n: int = 20000, seed: int = 11) -> Dict:
    """Zero error of the tip position the servo holds (um), and the gain error at the stop (CALC)."""
    rng = np.random.default_rng(seed)
    g = gradient_mT_per_mm * 1e3                                    # uT per mm
    z0 = rng.normal(0.0, val(SENSING["hall_zero_residual_um"]), n)
    drift = rng.uniform(-1, 1, n) * val(SENSING["hall_offset_drift_uT_per_K"]) * val(SENSING["temp_span_K"]) / g * 1e3
    earth = rng.uniform(-1, 1, n) * earth_um
    xt = rng.uniform(-1, 1, n) * val(SENSING["coil_crosstalk_residual"]) * crosstalk_um_per_A * val(SENSING["coil_I_rms_A"])
    tot = np.abs(z0 + drift + earth + xt)
    gain = abs(val(SENSING["br_tempco_pct_per_K"])) / 100 * val(SENSING["temp_span_K"])
    stop = val(PR.B1["travel_mm"])
    return {"zero_um": {"mean": float(tot.mean()), "p95": float(np.percentile(tot, 95)), "p99": float(np.percentile(tot, 99))},
            "parts_um_max": {"hall_zero_3sigma": 3 * val(SENSING["hall_zero_residual_um"]),
                             "offset_drift": val(SENSING["hall_offset_drift_uT_per_K"]) * val(SENSING["temp_span_K"]) / g * 1e3,
                             "earth": earth_um,
                             "coil_crosstalk_after_cal": val(SENSING["coil_crosstalk_residual"]) * crosstalk_um_per_A
                             * val(SENSING["coil_I_rms_A"])},
            "gain_error_pct": gain * 100, "gain_error_at_travel_um": gain * stop * 1e3,
            "gradient_mT_per_mm": gradient_mT_per_mm,
            "effect": "a slow offset of the ink by tens of micrometres at most: below the 25 um rule for moving clean writing "
                      "(REQ-RVJ-C02) only if the p95 stays under it; the tracker's own drift is separate",
            "label": "CALCULATION (Monte Carlo; contributors ASSUMPTION, SENSING table; gradient from nib.hall_fields)"}


def mechanics(stop_mm: float, travel_mm: float, clearances: Dict[str, float], n: int = 20000, seed: int = 12) -> Dict:
    """Worst-direction usable travel and the running clearances after the mechanical offsets (CALC).  clearances: the
    nominal margins (mm) of the layout's checks that a centring error eats (name -> margin beyond its rule)."""
    rng = np.random.default_rng(seed)

    def draw(key):
        a = rng.uniform(0, 2 * math.pi, n)
        r = val(MECH[key]) * np.sqrt(rng.uniform(0, 1, n))       # uniform over the disc of the half-range
        return np.stack([r * np.cos(a), r * np.sin(a)], 1)
    rest = draw("carrier_rest_offset")
    mag = draw("magnet_assembly")
    coil = draw("coil_on_carrier")
    ring = draw("ring_to_axis")
    anchor = draw("anchor_to_axis")
    gs = draw("guide_station_play")
    opt = draw("optics_block")
    # the stops sit on the handle (the ball guide's races and the lateral stop ring, centred on the axis); the servo
    # holds the Hall zero (= the magnets' and the handle's centre); the carrier's rest offset costs holding force only
    e_stop = np.linalg.norm(mag + anchor, axis=1)                  # the stops' centre against the magnetic centre
    usable = stop_mm - 0.2 - e_stop                                # the 0.2 mm soft-stop allowance (study B)
    e_coil = np.linalg.norm(coil - mag, axis=1)                    # the coil against the magnets (force map)
    e_ring = np.linalg.norm(ring + gs, axis=1)                     # the refill against the ring bore
    e_opt = np.linalg.norm(opt + ring, axis=1)
    res = {"usable_travel_mm": {"nominal": travel_mm, "p1": float(np.percentile(usable, 1)),
                                "mean": float(usable.mean()), "min": float(usable.min())},
           "stop_centre_offset_mm": {"p99": float(np.percentile(e_stop, 99))},
           "coil_to_magnets_mm": {"p99": float(np.percentile(e_coil, 99))},
           "clearances_after_offsets_mm": {}}
    run = val(PR.FRONT["c_run_mm"])
    for name, m in clearances.items():
        e = e_opt if "optics" in name else (e_coil if "coil" in name else e_ring)
        gap = run + m - float(np.percentile(e, 99))
        res["clearances_after_offsets_mm"][name] = {"nominal_gap": run + m, "p99_gap": gap,
                                                    "keeps_0p3_rule_p99": bool(gap >= run - 1e-9),
                                                    "keeps_0p2_p99": bool(gap >= 0.2)}
    res["travel_passes_p1"] = bool(np.percentile(usable, 1) >= travel_mm - 1e-9)
    res["holding_force_rest_offset_mN"] = float(val(PR.B1["k_tip_N_m"]) * val(MECH["carrier_rest_offset"]))
    res["label"] = "CALCULATION (Monte Carlo, uniform over each tolerance disc; tolerances ASSUMPTION, MECH table)"
    return res


def tables() -> Dict:
    return {"sensing": PR.table(SENSING), "mechanics": PR.table(MECH)}
