r"""Study B's nib B1 inside the Rev K pen (CALCULATION on PROPOSED DESIGNS; study B's models imported read-only).

What Rev K checks here that study B's concept layout did not:
  coil      the moving coils' footprint against the bore at the stop.  Study B's force model (bnib/magnetics.py) lets
            every turn of a racetrack share the leg ends (zero-width end turns); a flat coil that can be wound or etched
            spreads its end turns over the leg width, like its legs.  A buildable concentric racetrack is fitted inside
            r <= 11.0 - stop - 0.3 mm with magpylib on study B's own magnets and iron images (an upper bound, as study
            B's), and its force constant, copper mass and force map are reported against study B's.
  leads     the coil leads across the moving carrier: the four suspension wires carry the two coils' currents (the
            optical-pickup practice); Ti-6Al-4V (study B) is a poor conductor, C17200 carries it (resistance, loss,
            peak current, fatigue with bnib/flexure.wire_stage).
  modes     the loaded eigenmodes (bnib/flexure.loaded_modes) with the refill's position in the carrier at 35 / 50 /
            75 deg, the ball free and stuck (three pre-sliding stiffnesses), two refill stiffnesses and three wire
            circles, against DEC-050's rule: the lowest structural mode >= 2.5 x the servo bandwidth.
  shock     axial stops (bnib/flexure.shock), a lateral stop hit in a 1 m drop, and the refill's axial blow on the
            counter-face head.
  hall      keep-outs of the TMAG5170 nib sensor: the pole magnets' stray field, the position magnet's field over the
            stroke (range and gradient), the coil current's field per ampere, the Earth's field (magpylib, free space).
  power     the nib's copper loss for any tremor duty and Km scale (bnib/candidates.evaluate, study B's duty model).
Nothing built or measured.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD, ensure_paths
from . import params as PR
from .params import val

ensure_paths()

MU0 = 4e-7 * math.pi
RHO_CU = 1.7241e-8          # ohm m (MFR AMF-29)
CU_DENS = 8890.0            # kg/m3 (MFR AMF-29)


# ------------------------------------------------------------------------------------------------ the design point
@lru_cache(maxsize=1)
def design():
    return PR.b1_design()


@lru_cache(maxsize=4)
def evaluate(q_rms_mm: float = 0.2, km_scale: float = 1.0) -> Dict:
    """study B's CALC duty model for B1 at a correction duty q_rms (mm rms per axis, 8 Hz, 70 % contact) and a Km scale."""
    from bnib import candidates as CD
    from bnib import loads as LD
    d = replace(design(), km_scale=km_scale)
    return CD.evaluate(d, duty=LD.Duty(q_rms=max(q_rms_mm, 1e-4) * 1e-3), detail=False, fast=True)


def geometry_actuator() -> Dict:
    """The actuator geometry of B1 (m): pole side w, half spacing e, magnet t_m, coil layers t_c, stroke s (stop)."""
    d = design()
    s = d.travel + 0.2e-3
    from bnib.actuators import R_CARRIER
    e = (R_CARRIER + s + 0.3e-3) / math.sqrt(2)
    return {"w": d.w, "e": e, "t_m": d.t_m, "t_c": d.t_c, "s": s, "c": 0.5 * d.w + e, "b_leg": d.w - 2 * s,
            "r_out": math.sqrt(2.0) * (0.5 * d.w + e + 0.5 * d.w)}


def chk_geom():
    from bnib import magnetics as MG
    a = geometry_actuator()
    return MG.ChkGeom(w=a["w"], e=a["e"], t_m=a["t_m"], t_x=a["t_c"], t_y=a["t_c"], s=a["s"])


# ------------------------------------------------------------------------------------------------ coil footprint
def idealised_footprint() -> Dict:
    """Study B's coil as modelled (legs b = w - 2 s wide centred on the poles, end runs of zero width at the pole's
    edges) and the same coil with buildable end turns (the end-run bundle as wide as the legs), against the bore at
    the stop (CALC)."""
    a = geometry_actuator()
    c, w, b, s = a["c"], a["w"], a["b_leg"], a["s"]
    R_bore = val(PR.NIB["housing_bore_coil_mm"]) * 1e-3
    R_ring = 10.8e-3                                   # study B's aluminium housing ring (d_in 21.6 mm)
    c_run = val(PR.FRONT["c_run_mm"]) * 1e-3
    X_out = c + 0.5 * b
    corner_ideal = math.hypot(X_out, c + 0.5 * w)
    corner_real = math.hypot(X_out, c + 0.5 * w + b)
    inner_real = c - 0.5 * w - b                       # the lower edge of the inner end-run bundle (upper row)
    r_max = R_bore - s - c_run
    return {"pole_corner_r_mm": a["r_out"] * 1e3, "leg_bundle_mm": b * 1e3,
            "idealised_corner_r_mm": corner_ideal * 1e3, "buildable_same_legs_corner_r_mm": corner_real * 1e3,
            "buildable_same_legs_inner_edge_y_mm": inner_real * 1e3,
            "carrier_r_mm": val(PR.FRONT["carrier_r_mm"]),
            "r_max_at_rest_mm": r_max * 1e3,
            "margin_idealised_vs_PEEK_bore_mm": (R_bore - corner_ideal - s - c_run) * 1e3,
            "margin_idealised_vs_Al_ring_mm": (R_ring - corner_ideal - s - c_run) * 1e3,
            "margin_buildable_same_legs_mm": (R_bore - corner_real - s - c_run) * 1e3,
            "note": "study B's layout drew the coils as a 20.0 mm disc inside a 21.6 mm aluminium ring and checked the "
                    "actuator in the bore without the coil's stroke; the idealised coil's corner at the stop reaches "
                    f"{(corner_ideal + s) * 1e3:.2f} mm, a buildable coil with the same legs {(corner_real + s) * 1e3:.2f} mm "
                    "(the bore is 11.0 mm), and its inner end runs would cross the carrier (y < 1.7 mm)",
            "label": "CALCULATION (geometry of study B's coil model; bnib/magnetics.py layer_filaments)"}


def _racetrack_filaments(g, Xin, Yin, b, yc, layer="x", nb=4, nt=2, nl=12, disp=(0.0, 0.0)):
    """Concentric flat racetracks (two per layer, one per pole row): turn k has half-width X_k = Xin + f b and
    half-height Y_k = Yin + f b (f across the bundle), centred at (0, +-yc); legs along y at x = +-X_k, end runs along
    x at y = +-yc +- Y_k: the end turns are as wide as the legs (a coil that can be wound or etched)."""
    z0 = g.t_m + g.c0 if layer == "x" else g.t_m + g.c0 + g.t_x
    pts, dls, wts = [], [], []
    for row in (-1, 1):
        cur = 1.0 if row > 0 else -1.0
        ycen = row * yc
        for ib in range(nb):
            f = (ib + 0.5) / nb
            X, Y = Xin + f * b, Yin + f * b
            for it in range(nt):
                z = z0 + (it + 0.5) / nt * g.t_x
                segs = [((X, ycen - Y, z), (X, ycen + Y, z)), ((X, ycen + Y, z), (-X, ycen + Y, z)),
                        ((-X, ycen + Y, z), (-X, ycen - Y, z)), ((-X, ycen - Y, z), (X, ycen - Y, z))]
                for p0, p1 in segs:
                    p0 = np.array(p0)
                    p1 = np.array(p1)
                    if layer == "y":
                        p0, p1 = p0[[1, 0, 2]], p1[[1, 0, 2]]
                    for k in range(nl):
                        q0 = p0 + (p1 - p0) * k / nl
                        q1 = p0 + (p1 - p0) * (k + 1) / nl
                        pts.append(0.5 * (q0 + q1) + np.array([disp[0], disp[1], 0.0]))
                        dls.append((q1 - q0) * cur)
                        wts.append(1.0 / (nb * nt))
    return np.array(pts), np.array(dls), np.array(wts)


def racetrack_km(g, src, Xin, Yin, b, yc, layer="x", disp=(0.0, 0.0), fine=False) -> Dict:
    """Force constant (N/sqrt(W)) of a layer of two concentric racetracks in series, its cross-coupling and axial
    force per ampere-turn (CALC; magpylib cuboids + iron images, an upper bound like study B's)."""
    nb, nt, nl = (4, 2, 12) if fine else (3, 1, 8)
    P, dl, wt = _racetrack_filaments(g, Xin, Yin, b, yc, layer, nb, nt, nl, disp)
    B = src.getB(P)
    F = (np.cross(dl, B) * wt[:, None]).sum(axis=0)          # per ampere-turn in each racetrack, both racetracks
    k = 0 if layer == "x" else 1
    n_r = 2
    F1 = abs(F[k]) / n_r
    A_w = b * g.t_x
    fs = (np.arange(nb) + 0.5) / nb
    l_mean = float(np.mean(4.0 * ((Xin + fs * b) + (Yin + fs * b))))
    Km = math.sqrt(n_r) * F1 * math.sqrt(g.k_fill * A_w / (RHO_CU * l_mean))
    m_cu = n_r * CU_DENS * g.k_fill * A_w * l_mean                 # one layer, kg
    return {"Km": Km, "F_per_AT": F.tolist(), "cross": float(abs(F[1 - k]) / max(abs(F[k]), 1e-12)), "l_mean": l_mean,
            "m_cu_layer_kg": m_cu, "A_w": A_w}


def buildable_coil(quick: bool = False, use_cache: bool = True) -> Dict:
    """Search for the buildable coil with the largest force constant whose outer corner stays inside the bore at the
    stop (r <= 11.0 - s_stop - 0.3 mm) and whose inner end runs clear the carrier (y >= 1.7 mm), then its force map
    over the stroke, both layers (CALC).  Cached in revk/build/coil*.json."""
    from bnib import magnetics as MG
    tag = "coil_quick.json" if quick else "coil.json"
    cp = BUILD / tag
    if use_cache and cp.exists():
        try:
            return json.load(open(cp))
        except Exception:
            pass
    g = chk_geom()
    src = MG.sources(g)
    a = geometry_actuator()
    s = a["s"]
    R_bore = val(PR.NIB["housing_bore_coil_mm"]) * 1e-3
    r_max = R_bore - s - val(PR.FRONT["c_run_mm"]) * 1e-3
    y_min = (val(PR.FRONT["carrier_r_mm"]) + val(PR.NIB["coil_former_margin_mm"])) * 1e-3
    ref = MG.km_map(g, n=3 if quick else 5, axis="x", nb=3, nt=2, nl=10)
    F0 = MG.layer_force(g, "x", (0.0, 0.0), src, nb=3, nt=2, nl=10)
    Km_ideal = MG.km_from_force(g, abs(F0[0]), "x")
    bs = np.arange(1.6, 2.81, 0.4 if quick else 0.2) * 1e-3
    ycs = np.arange(4.25, 5.76, 0.5 if quick else 0.25) * 1e-3
    xis = np.arange(1.9, 3.01, 0.3 if quick else 0.15) * 1e-3
    best, rows = None, []
    for b in bs:
        for yc in ycs:
            for Xin in xis:
                Xout = Xin + b
                if Xout >= r_max:
                    continue
                Yin = min(math.sqrt(r_max ** 2 - Xout ** 2) - yc - b, yc - b - y_min)
                if Yin < 0.1e-3:
                    continue
                r = racetrack_km(g, src, Xin, Yin, b, yc)
                rows.append({"b_mm": b * 1e3, "yc_mm": yc * 1e3, "Xin_mm": Xin * 1e3, "Yin_mm": Yin * 1e3, "Km": r["Km"]})
                if best is None or r["Km"] > best["Km"]:
                    best = dict(rows[-1])
    b, yc, Xin, Yin = best["b_mm"] * 1e-3, best["yc_mm"] * 1e-3, best["Xin_mm"] * 1e-3, best["Yin_mm"] * 1e-3
    fx = racetrack_km(g, src, Xin, Yin, b, yc, "x", fine=True)
    fy = racetrack_km(g, src, Xin, Yin, b, yc, "y", fine=True)
    n = 3 if quick else 5
    xs = np.linspace(-s, s, n)
    grid = [[racetrack_km(g, src, Xin, Yin, b, yc, "x", (dx, dy), fine=not quick)["Km"] for dy in xs] for dx in xs]
    cross = max(racetrack_km(g, src, Xin, Yin, b, yc, "x", (dx, dy))["cross"] for dx in (-s, 0.0, s) for dy in (-s, 0.0, s))
    corner = math.hypot(Xin + b, yc + Yin + b)
    m_cu_both = fx["m_cu_layer_kg"] + fy["m_cu_layer_kg"]
    d = design()
    from bnib import actuators as A
    act = A.vc_axial(d.w, d.t_m, d.t_c, s, moving="coil")
    m_cu_B = float(act["m_cu"])
    out = {"geometry_mm": {"bundle_b": b * 1e3, "row_centre_yc": yc * 1e3, "X_in": Xin * 1e3, "Y_in": Yin * 1e3,
                           "X_out": (Xin + b) * 1e3, "Y_out": (Yin + b) * 1e3, "outer_corner_r": corner * 1e3,
                           "inner_edge_y": (yc - Yin - b) * 1e3, "r_max_rule": r_max * 1e3,
                           "corner_at_stop_r": (corner + s) * 1e3, "bore_r": R_bore * 1e3},
           "Km0_x": fx["Km"], "Km0_y": fy["Km"], "Km_idealised_x_same_method": Km_ideal, "Km_idealised_map": ref["Km0"],
           "ratio_x": fx["Km"] / Km_ideal, "ratio_y_over_idealised_x": fy["Km"] / Km_ideal,
           "Km_map_x": grid, "stroke_mm": (xs * 1e3).tolist(), "Km_min_x": float(np.min(grid)),
           "variation": float((np.max(grid) - np.min(grid)) / fx["Km"]), "cross_max": cross,
           "m_cu_g": m_cu_both * 1e3, "m_cu_studyB_g": m_cu_B * 1e3, "l_mean_mm": fx["l_mean"] * 1e3,
           "n_candidates": len(rows), "power_factor": (Km_ideal / fx["Km"]) ** 2,
           "label": "CALCULATION (magpylib cuboids + iron images, study B's magnets and gap; concentric racetracks with end "
                    "turns as wide as the legs; an upper bound like study B's)"}
    cp.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(cp, "w"), indent=1)
    return out


# ------------------------------------------------------------------------------------------------ coil leads
def wire_stage(mat: str = "C17200_TH04", r_w_mm: float = None, Kt: float = None):
    from bnib import flexure as FX
    d = design()
    ws = replace(d.wire, mat=mat)
    if r_w_mm is not None:
        ws = replace(ws, r_w=r_w_mm * 1e-3)
    if Kt is not None:
        ws = replace(ws, Kt=Kt)
    return ws


WIRE_CHOICE = {"material": "C17200_TH04", "d_mm": 0.10, "r_w_mm": 5.5, "Kt": 1.8}


def leads() -> Dict:
    """The suspension wires as the coils' leads (two wires per coil): resistance, the share of the coil's loss they add,
    the current they allow at 3.3 V, and the wire stage (stiffness, fatigue, buckling, violin mode, tolerance Monte
    Carlo) for study B's Ti-6Al-4V wire, the same wire in C17200, and Rev K's thinner C17200 wire (CALC; resistivities
    MANUFACTURER)."""
    from bnib import flexure as FX
    d = design()
    R_c = val(PR.NIB["coil_R_ohm"])
    Rds = 0.24                                          # DRV8214 HS + LS (MFR AMF-37)
    rho_be = RHO_CU / val(PR.NIB["IACS_C17200_min"])
    rho = {"Ti6Al4V": val(PR.NIB["rho_Ti64_ohm_m"]), "C17200_TH04": rho_be}
    opts = {"studyB_Ti64_0.128": ("Ti6Al4V", d.wire.d), "C17200_0.128": ("C17200_TH04", d.wire.d),
            "revK_C17200_0.100": ("C17200_TH04", WIRE_CHOICE["d_mm"] * 1e-3)}
    out = {"coil_R_ohm": R_c, "rho_C17200_ohm_m": rho_be, "rho_Ti64_ohm_m": rho["Ti6Al4V"], "options": {}}
    keep = ("k_lat_N_m", "k_axial_N_um", "k_tilt_Nm_rad", "stress_stop_MPa", "goodman_SF", "static_SF_stop", "P_buckle_N",
            "f_violin_Hz", "f_suspension_Hz", "mass_g", "magnetic")
    for name, (mat, dw) in opts.items():
        ws = replace(wire_stage(mat, 5.5), d=dw)
        A = math.pi / 4 * dw ** 2
        Rw = rho[mat] * ws.L / A
        R_loop = R_c + 2 * Rw
        fx = FX.wire_stage(ws, d.travel, d.travel + 0.2e-3, 3.49e-3)
        mc = FX.tolerance_mc(ws, d.travel, d.travel + 0.2e-3, 3.49e-3, n=1000)
        sf_kt = {f"{kt:g}": FX.wire_stage(replace(ws, Kt=kt), d.travel, d.travel + 0.2e-3, 3.49e-3)["goodman_SF"]
                 for kt in (1.3, 1.5, 1.8, 2.5)}
        out["options"][name] = {"material": mat, "d_mm": dw * 1e3, "R_wire_ohm": Rw, "R_loop_ohm": R_loop,
                                "wire_loss_share_of_coil": 2 * Rw / R_c, "power_factor": R_loop / R_c,
                                "I_max_3V3_A": min(1.5, 3.3 / (R_loop + Rds)),
                                "F_peak_ratio_vs_design": min(1.5, 3.3 / (R_loop + Rds)) / min(1.5, 3.3 / (R_c + Rds)),
                                "wire_stage": {k: fx[k] for k in keep}, "goodman_SF_by_Kt": sf_kt,
                                "tolerance_mc": mc, "carries_current": mat != "Ti6Al4V"}
    ch = out["options"]["revK_C17200_0.100"]
    ti = out["options"]["studyB_Ti64_0.128"]
    out["choice"] = WIRE_CHOICE
    out["verdict"] = (f"C17200 0.10 mm wires carry the currents: {ch['R_wire_ohm']:.2f} ohm each, +{ch['wire_loss_share_of_coil'] * 100:.0f} % "
                      f"on the coil loop, Goodman SF {ch['wire_stage']['goodman_SF']:.2f} at Kt 1.8 ({ch['goodman_SF_by_Kt']['2.5']:.2f} at "
                      f"Kt 2.5); study B's Ti-6Al-4V wire would add {2 * ti['R_wire_ohm']:.1f} ohm per coil loop "
                      f"({ti['wire_loss_share_of_coil']:.1f} x the coil) and cap the current at {ti['I_max_3V3_A']:.2f} A")
    out["label"] = ("CALCULATION (resistances from MANUFACTURER resistivities: AMF-21 re-read, AMF-251; wire stage and Monte "
                    "Carlo bnib/flexure.py (tolerances ASSUMPTION as study B); fatigue AMF-19 x 0.85; Kt 1.8 ASSUMPTION)")
    return out


def wire_mc(mat: str = "C17200_TH04", d_mm: float = 0.10, preload_max_N: float = 0.3, n: int = 2000, seed: int = 7) -> Dict:
    """bnib/flexure.tolerance_mc's Monte Carlo (diameter +-2 %, length +-0.05 mm, modulus +-4 %, Kt 1.3-2.5, axial
    assembly preload 0..preload_max) with the preload range as a parameter (CALC; tolerances ASSUMPTION as study B).
    Rev K's ball guide fixes the flange axially, so an axial mismatch between the flange and the anchor ring strains the
    wires directly (0.15 N per um for 0.10 mm C17200): an axially soft anchor diaphragm keeps the preload small."""
    from bnib import flexure as FX
    d = design()
    ws = replace(wire_stage(mat, 5.5), d=d_mm * 1e-3)
    rng = np.random.default_rng(seed)
    sfs = []
    for _ in range(n):
        w2 = replace(ws, d=ws.d * (1 + 0.02 * rng.standard_normal()), L=ws.L + 0.05e-3 * rng.standard_normal(),
                     Kt=rng.uniform(1.3, 2.5), P_axial=ws.P_axial + rng.uniform(0.0, preload_max_N))
        r = FX.wire_stage(w2, d.travel, d.travel + 0.2e-3, 3.49e-3)
        kE = 1 + 0.04 * rng.standard_normal()
        sfs.append(r["goodman_SF"] / kE)
    sfs = np.array(sfs)
    return {"material": mat, "d_mm": d_mm, "preload_max_N": preload_max_N,
            "goodman_SF_p1_p5_p50": np.percentile(sfs, [1, 5, 50]).tolist(), "n": n,
            "label": "CALCULATION (bnib/flexure.wire_stage in study B's Monte Carlo; tolerances ASSUMPTION)"}


def wire_mc_table(n: int = 2000) -> Dict:
    rows = []
    for mat, dmm in (("Ti6Al4V", 0.1284), ("C17200_TH04", 0.10), ("C17200_TH04", 0.08)):
        for pre in (0.3, 0.05):
            rows.append(wire_mc(mat, dmm, pre, n=n))
    return {"rows": rows, "note": "p5 of the Goodman safety factor over study B's tolerance draws, with the assembly's axial "
                                  "preload up to 0.3 N (study B) or 0.05 N (Rev K's axially soft anchor diaphragm)",
            "label": "CALCULATION"}


# ------------------------------------------------------------------------------------------------ the couple
def couple(r_w_mm: float = 5.5, wire_mat: str = "Ti6Al4V", wire_d_mm: float = None, L_lever_mm: float = 69.5,
           r_ball_circle_mm: float = 6.0, n_balls: int = 6, mu_roll: float = 0.001, race_preload_N: float = 4.0) -> Dict:
    """The counter-face moves the static side load into a couple (study B, docs/balanced_nib.md s5.2): the paper's push
    at the ball and the face's push at the refill's rear end are parallel (both along the paper normal, F_n) and
    L apart along the pen, so the carrier must carry M = F_n L cos(theta).  B1's four wires carry it as axial forces,
    F = M / (2 sqrt 2 r_w) per wire of the loaded pair: tension on one side, COMPRESSION on the other, against the
    wires' sidesway buckling load pi^2 EI / L_w^2 each (CALC).  Also: the carrier's tilt (study B's number), the axial
    motion at the flange rim against the 20 um axial stops, the post-buckling bow of a compressed wire, and the loads
    of the alternative that Rev K proposes, a double-race ball thrust guide at the flange (the tilt taken by rolling
    balls, the wires left to centre the carrier and carry the currents)."""
    from bnib import flexure as FX
    from bnib.labels import FLEX
    d = design()
    ws = wire_stage(wire_mat, r_w_mm)
    if wire_d_mm:
        ws = replace(ws, d=wire_d_mm * 1e-3)
    fx = FX.wire_stage(ws, d.travel, d.travel + 0.2e-3, 3.49e-3)
    E, I, Lw = ws.E, ws.I, ws.L
    Pcr_side = math.pi ** 2 * E * I / Lw ** 2
    Pcr_ff = 4 * math.pi ** 2 * E * I / Lw ** 2
    F_n = val(PR.B1["F_n_N"])
    rows = []
    for th in (35.0, 50.0, 60.0, 75.0):
        M = F_n * L_lever_mm * 1e-3 * math.cos(math.radians(th))
        Fw = M / (2 * math.sqrt(2) * r_w_mm * 1e-3)
        tilt = M / fx["k_tilt_Nm_rad"]
        dz_rim = tilt * (r_w_mm + 0.8) * 1e-3
        # post-buckling: the compressed wire's end shortening = its axial displacement at the tilt with the tension
        # wires alone carrying the moment (tilt doubles); bow amplitude w0 = (2 / pi) sqrt(L_w delta)
        delta = 2 * tilt * r_w_mm * 1e-3 / math.sqrt(2)
        w0 = 2 / math.pi * math.sqrt(Lw * delta)
        eps_b = ws.d / 2 * (2 * math.pi / Lw) ** 2 * w0 / 2
        P_balls = 2 * M / (r_ball_circle_mm * 1e-3)
        rows.append({"tilt_deg": th, "couple_mNm": M * 1e3, "wire_force_N": Fw, "x_sidesway_buckling": Fw / Pcr_side,
                     "x_fixed_fixed_buckling": Fw / Pcr_ff, "carrier_tilt_mrad": tilt * 1e3,
                     "ball_offset_from_tilt_mm": tilt * 36.0, "flange_rim_axial_um": dz_rim * 1e6,
                     "hits_20um_axial_stops": dz_rim > 20e-6,
                     "buckled_bow_mm": w0 * 1e3, "buckled_bend_stress_MPa": eps_b * E / 1e6,
                     "ball_guide_load_N": P_balls, "ball_guide_friction_mN": mu_roll * P_balls * 1e3})
    # ball guide: Hertz stress of one ball on a flat race (Si3N4 on 440C, handbook moduli ASSUMPTION): at the couple's
    # load, at the release load of the sprung races (the preload shared by three balls) and at a 2000 g drop with rigid
    # races (the carrier's 3.2 g shared by three balls)
    Estar = 1.0 / ((1 - 0.27 ** 2) / 310e9 + (1 - 0.3 ** 2) / 200e9)
    hz = []
    P_couple = max(r["ball_guide_load_N"] for r in rows) / max(n_balls // 2, 1)
    for db in (0.8, 1.0, 1.5, 2.0):
        R = db * 1e-3 / 2
        for case, F in (("couple", P_couple), ("race_spring_release", race_preload_N / 3.0),
                        ("drop_2000g_rigid_races", 3.2e-3 * 9.81 * 2000.0 / 3.0)):
            a = (3 * F * R / (4 * Estar)) ** (1.0 / 3.0)
            delta = a * a / R
            hz.append({"ball_d_mm": db, "case": case, "F_N": F, "p_max_GPa": 3 * F / (2 * math.pi * a * a) / 1e9,
                       "deflection_um": delta * 1e6})
    return {"wire": {"material": wire_mat, "d_mm": ws.d * 1e3, "r_w_mm": r_w_mm, "k_tilt_Nm_rad": fx["k_tilt_Nm_rad"],
                     "P_sidesway_per_wire_N": Pcr_side, "P_fixed_fixed_per_wire_N": Pcr_ff}, "rows": rows,
            "worst": max(rows, key=lambda r: r["x_sidesway_buckling"]), "ball_guide_hertz": hz,
            "ball_guide": {"balls_per_race": n_balls, "ball_circle_r_mm": r_ball_circle_mm, "mu_roll": mu_roll,
                           "race_preload_N": race_preload_N, "drop_stop_um": 20.0,
                           "note": "Si3N4 balls between the carrier flange and two flat 440C races on the handle, set with "
                                   "<= 2 um of play: the carrier translates on the balls, its tilt and axial position are "
                                   "fixed.  Each race sits on its seat under a wave spring preloaded to about 1.5 x the "
                                   "couple's ball load; a drop lifts a race off its seat and the flange lands on hard stops "
                                   "20 um away, so the balls never see more than the spring's release load (rigid races "
                                   "would brinel in a 1 m drop)"},
            "L_lever_mm": L_lever_mm, "F_n_N": F_n,
            "label": "CALCULATION (statics; sidesway buckling pi^2 EI / L^2 per fixed-guided wire; post-buckling bow of a "
                     "clamped column; Hertz contact with handbook moduli, ASSUMPTION; rolling resistance 0.001 ASSUMPTION)"}


# ------------------------------------------------------------------------------------------------ loaded modes
def p_ahead(theta_deg: float, R_s: float, r_b: float = 0.35) -> float:
    th = math.radians(theta_deg)
    return (R_s * math.cos(th) - r_b) / math.sin(th)


RESTRAINTS = {   # (label, tilt-stiffness multiplier on the wires' own, wire material, wire d mm)
    "studyB_wires": ("B1 as designed: four 0.128 mm Ti-6Al-4V wires carry the tilt", 1.0, "Ti6Al4V", 0.1284),
    "buckled_pair": ("the compressed pair buckled: the tension pair alone carries the tilt", 0.5, "Ti6Al4V", 0.1284),
    "revK_ball_guide": ("Rev K: 0.10 mm C17200 wires + a ball thrust guide at the flange (tilt locked)", 300.0, "C17200_TH04", 0.10),
}


def modes_grid(R_s_mm: float, m_carrier_g: float, quick: bool = False, zb: Sequence[float] = (10.0, 36.0),
               z_car: float = 32.0, restraints: Sequence[str] = None) -> Dict:
    """Loaded modes of carrier + refill (bnib/flexure.loaded_modes, read-only) over tilt (the refill slides in the
    carrier), the ball free and stuck (pre-sliding 5 / 10 / 20 um), two refill stiffnesses and three tilt restraints;
    the servo bandwidth that DEC-050's 2.5 x rule allows (CALC)."""
    from bnib import flexure as FX
    d = design()
    F_n = val(PR.B1["F_n_N"])
    mu_s = 0.15 * 1.3                                   # study B stick_stiffness convention
    zb = tuple(zb)                                      # guide stations (mm, pen frame at 50 deg)
    J_car = 3e-8 + 0.65e-3 * 0.028 ** 2 / 12.0          # study B's 3e-8 + the Ti tube about its centre (kg m^2)
    mpl = (0.84e-3 + val(PR.HEAD["puck"])["mass_g"] * 1e-3) / 0.0695
    rows = []
    thetas = (35.0, 50.0, 75.0) if not quick else (35.0, 50.0)
    keys = list(RESTRAINTS) if restraints is None else list(restraints)
    for key in keys:
        lab, kmul, mat, dw = RESTRAINTS[key]
        ws = replace(wire_stage(mat, 5.5), d=dw * 1e-3)
        fx = FX.wire_stage(ws, d.travel, d.travel + 0.2e-3, 3.49e-3)
        m_car = m_carrier_g if key == "revK_ball_guide" else 1.798
        for EI in val(PR.NIB["refill_EI_Nm2"]):
            beam = FX.RefillBeam(L=0.0695, EI=EI, m_per_len=mpl, n_el=20)
            for th in thetas:
                ds = (p_ahead(th, R_s_mm) - p_ahead(50.0, R_s_mm)) * 1e-3     # refill further ahead at low tilt
                args = (beam, m_car * 1e-3, J_car, z_car * 1e-3 + ds, zb[0] * 1e-3 + ds, zb[1] * 1e-3 + ds,
                        fx["k_lat_N_m"], fx["k_tilt_Nm_rad"] * kmul, 0.0, F_n)
                free = FX.loaded_modes(*args, 0.0)["f_Hz"]
                for xp in val(PR.NIB["x_pre_um"]):
                    k_st = mu_s * F_n / (xp * 1e-6)
                    stuck = FX.loaded_modes(*args, k_st)["f_Hz"]
                    lim = min(free[1], stuck[0]) / val(PR.NIB["servo_bw_rule_x"])
                    rows.append({"restraint": key, "EI_Nm2": EI, "theta_deg": th, "x_pre_um": xp,
                                 "free_Hz": [round(f, 1) for f in free[:3]], "stuck_Hz": [round(f, 1) for f in stuck[:3]],
                                 "first_structural_free_Hz": free[1], "lowest_stuck_Hz": stuck[0],
                                 "servo_bw_max_Hz": lim, "passes_40Hz": lim >= val(PR.NIB["servo_bw_min_Hz"]),
                                 "k_tilt_Nm_rad": fx["k_tilt_Nm_rad"] * kmul, "k_lat_N_m": fx["k_lat_N_m"],
                                 "m_carrier_g": m_car})
    by = {}
    for key in keys:
        rr = [r for r in rows if r["restraint"] == key]
        nom = [r for r in rr if r["EI_Nm2"] == 0.385 and r["x_pre_um"] == 10.0]
        by[key] = {"label": RESTRAINTS[key][0], "servo_bw_max_nominal_Hz": min(r["servo_bw_max_Hz"] for r in nom),
                   "servo_bw_max_worst_Hz": min(r["servo_bw_max_Hz"] for r in rr),
                   "lowest_stuck_nominal_Hz": min(r["lowest_stuck_Hz"] for r in nom),
                   "lowest_stuck_worst_Hz": min(r["lowest_stuck_Hz"] for r in rr),
                   "first_free_nominal_Hz": min(r["first_structural_free_Hz"] for r in nom),
                   "share_cases_passing_40Hz": float(np.mean([r["passes_40Hz"] for r in rr])),
                   "ratio_at_40Hz_stuck_nominal": min(r["lowest_stuck_Hz"] for r in nom) / 40.0,
                   "ratio_at_40Hz_free_nominal": min(r["first_structural_free_Hz"] for r in nom) / 40.0}
    return {"rows": rows, "by_restraint": by, "m_carrier_g": m_carrier_g, "guide_stations_z_mm": zb,
            "J_carrier_kg_m2": J_car, "R_s_mm": R_s_mm,
            "rule": "servo bandwidth <= min(first structural mode ball free, lowest mode ball stuck) / 2.5 (DEC-050, "
                    "REQ-BNIB-006 as edited by the lead); closed-loop bandwidth >= 40 Hz",
            "studyB_reference": {"free": val(PR.B1["modes_free_Hz"]), "stuck": val(PR.B1["modes_stuck_Hz"]),
                                 "servo_inner_Hz": val(PR.B1["servo_inner_Hz"])},
            "label": "CALCULATION (bnib/flexure.loaded_modes: planar beam refill + rigid carrier on the wires; pre-sliding "
                     "stiffness mu_s F_n / x_pre, x_pre ASSUMPTION 5-20 um; the ball guide as a tilt stiffness 300 x the "
                     "wires')"}


# ------------------------------------------------------------------------------------------------ shock
def drop(m_move_g: float, flange_r_mm: float, coil_margin_mm: float) -> Dict:
    """1 m drop (CALC): the axial stops (bnib/flexure.shock with C17200 wires), a lateral hit of the carrier on its
    stop ring (energy method, three stop stiffnesses), and the refill's axial blow on the counter-face head."""
    from bnib import flexure as FX
    d = design()
    h = val(PR.NIB["drop_height_m"])
    v = math.sqrt(2 * 9.81 * h)
    m = m_move_g * 1e-3
    ws = wire_stage("C17200_TH04")
    sh = FX.shock(ws, m)
    E = 0.5 * m * v * v
    rows = []
    fx = FX.wire_stage(ws, d.travel, d.travel + 0.2e-3, m)
    s_stop = d.travel + 0.2e-3
    for k in val(PR.NIB["lateral_stop_k_N_m"]):
        x = math.sqrt(2 * E / k)
        F = k * x
        defl = s_stop + x
        sig = fx["stress_stop_MPa"] * defl / s_stop
        from bnib.labels import FLEX
        rows.append({"k_stop_N_m": k, "stop_deflection_mm": x * 1e3, "peak_force_N": F, "g_level": F / (m * 9.81),
                     "wire_deflection_mm": defl * 1e3, "wire_stress_MPa": sig,
                     "wire_static_SF": FLEX["C17200_TH04"]["S_y"] / 1e6 / sig,
                     "coil_hits_bore": x * 1e3 > coil_margin_mm, "coil_margin_mm": coil_margin_mm})
    m_ref = (0.84 + val(PR.HEAD["puck"])["mass_g"]) * 1e-3
    E_ref = 0.5 * m_ref * v * v
    blows = []
    for x_stop in (0.2e-3, 0.5e-3, 1.0e-3):
        F = 2 * E_ref / x_stop
        blows.append({"stopping_mm": x_stop * 1e3, "peak_force_N": F})
    return {"v_impact_m_s": v, "axial": sh, "lateral": rows, "lateral_energy_mJ": E * 1e3, "refill_blow": blows,
            "refill_energy_mJ": E_ref * 1e3,
            "rule": "a drop stop on the handle side of the counter-face head takes the refill's blow (the SQUIGGLE's axial "
                    "load capacity is not in the datasheets seen, AMF-15/106); the lateral stop ring at the carrier flange "
                    "must be stiff enough that the coils never reach the bore",
            "label": "CALCULATION (energy method; stop stiffnesses ASSUMPTION; EXP-B25 drop tests)"}


# ------------------------------------------------------------------------------------------------ Hall keep-outs
def hall_fields(z_mag0_mm: float, z_sensor_mm: float, r_sensor_mm: float, coil: Dict, quick: bool = False,
                gap_mm: float = 1.6, z_coil0_mm: float = None) -> Dict:
    """Fields at the TMAG5170 (free space, magpylib; no iron: the keeper plate lies between the poles and the sensor,
    so the pole-magnet value is an upper bound) (CALC):
      - the four pole magnets (checkerboard) at the sensor;
      - the 1 mm N52 position magnet on the carrier flange (magnetised along the pen axis, toward the die) over the
        +-stop stroke: range and gradient -> tip noise (a magnet magnetised across the pen gives no first-order signal
        for motion along its own axis's normal: both lateral axes need the axial magnetisation);
      - the coil current (both layers' racetracks, per ampere of drive current) -> cross-talk before calibration;
      - the Earth's field (50 uT, ASSUMPTION) -> slow offset."""
    import magpylib as magpy
    mm = 1e-3                                             # everything in metres (magpylib 5 is SI; currents need it)
    a = geometry_actuator()
    zb = z_mag0_mm * mm                                   # the magnets' front face (pen frame), where the back plate ends
    mags = []
    for i in (-1, 1):
        for j in (-1, 1):
            sgn = 1.0 if i * j > 0 else -1.0
            mags.append(magpy.magnet.Cuboid(polarization=(0, 0, sgn * 1.42), dimension=(a["w"], a["w"], a["t_m"]),
                                            position=(i * a["c"], j * a["c"], zb + a["t_m"] / 2)))
    poles = magpy.Collection(*mags)
    S = np.array([r_sensor_mm, 0.0, z_sensor_mm]) * mm
    B_poles = poles.getB(S)                               # T
    s = a["s"]
    pm_z = (z_sensor_mm - gap_mm) * mm                    # position magnet centre gap_mm in front of the die (study B: 1.7)
    n = 5 if quick else 9
    xs = np.linspace(-s, s, n)

    def B_pm(dx, dy):
        m = magpy.magnet.Cuboid(polarization=(0, 0, 1.42), dimension=(mm, mm, mm), position=(r_sensor_mm * mm + dx, dy, pm_z))
        return m.getB(S) * 1e3                            # mT
    Bs = np.array([[B_pm(dx, dy) for dy in xs] for dx in xs])
    Bmax = float(np.abs(Bs).max())
    h = 0.05 * mm
    gx = (B_pm(h, 0.0) - B_pm(-h, 0.0)) / (2 * h * 1e3)   # mT per mm
    gy = (B_pm(0.0, h) - B_pm(0.0, -h)) / (2 * h * 1e3)
    g_min = float(min(np.linalg.norm(gx), np.linalg.norm(gy)))
    noise_uT = 140.0
    tip_noise_um_20k = noise_uT * 1e-3 / g_min * 1e3
    tip_noise_um_1k = tip_noise_um_20k / math.sqrt(20.0)
    # coil current field per ampere of drive current: the buildable coil's mean turn (both layers), turns for 2.5 ohm
    geo = coil["geometry_mm"]
    g = chk_geom()
    l_mean = coil["l_mean_mm"] * mm
    A_w = geo["bundle_b"] * mm * g.t_x
    N = math.sqrt(val(PR.NIB["coil_R_ohm"]) * g.k_fill * A_w / (2 * RHO_CU * l_mean))
    z_coil0 = zb + a["t_m"] + 0.3 * mm if z_coil0_mm is None else z_coil0_mm * mm
    cur = []
    X = 0.5 * (geo["X_in"] + geo["X_out"]) * mm
    Y = 0.5 * (geo["Y_in"] + geo["Y_out"]) * mm
    yc = geo["row_centre_yc"] * mm
    for layer, zc in (("x", z_coil0 + 0.4 * mm), ("y", z_coil0 + 1.2 * mm)):
        for row in (-1, 1):
            ycen = row * yc
            verts = [(X, ycen - Y, zc), (X, ycen + Y, zc), (-X, ycen + Y, zc), (-X, ycen - Y, zc), (X, ycen - Y, zc)]
            if layer == "y":
                verts = [(v[1], v[0], v[2]) for v in verts]
            cur.append(magpy.current.Polyline(current=(1.0 if row > 0 else -1.0) * N, vertices=verts))
    Bc = magpy.Collection(*cur).getB(S) * 1e3             # mT per ampere of drive current (both axes' coils energised)
    earth_mT = 0.05
    return {"sensor_mm": (S / mm).tolist(), "magnet_to_die_mm": gap_mm, "pole_magnets_mT": (B_poles * 1e3).tolist(),
            "pole_magnets_abs_mT": float(np.linalg.norm(B_poles) * 1e3),
            "position_magnet_max_component_mT": Bmax, "range_A1_mT": val(PR.NIB["hall_range_mT"]),
            "within_A1_range": Bmax + float(np.abs(B_poles).max()) * 1e3 < val(PR.NIB["hall_range_mT"]),
            "gradient_mT_per_mm": {"x": gx.tolist(), "y": gy.tolist(), "min_norm": g_min},
            "tip_noise_um_rms_20kSPS": tip_noise_um_20k, "tip_noise_um_rms_1kHz": tip_noise_um_1k,
            "coil_turns_per_racetrack": N, "coil_field_mT_per_A": Bc.tolist(),
            "coil_crosstalk_um_per_A": float(np.linalg.norm(Bc)) / g_min * 1e3,
            "earth_offset_um": earth_mT / g_min * 1e3,
            "note": "the pole magnets' field is taken in free space with no keeper (an upper bound); the coil cross-talk is "
                    "calibrated by current (EXP-B24 / EXP-T09); the Earth's field turns with the pen (slow)",
            "label": "CALCULATION (magpylib 5, free space; noise MANUFACTURER OPT-44 140 uT rms at 20 kSPS)"}


# ------------------------------------------------------------------------------------------------ power by duty
def power_table(km_scales: Sequence[float] = (1.0, 0.85, 0.7), q_rms_mm: Sequence[float] = (0.0, 0.2, 0.3, 0.75)) -> Dict:
    """Nib copper loss (W) by correction duty and Km scale (study B's duty model; mean over 35-75 deg and at 35 deg)."""
    out = {}
    for k in km_scales:
        for q in q_rms_mm:
            ev = evaluate(q, k)
            out[f"km{k:g}_q{q:g}"] = {"km_scale": k, "q_rms_mm": q, "P_cont_W": ev["P_cont_W"], "P_35deg_W": ev["P_cont_worst_W"],
                                      "hold_max_W": max(r["P_hold_W"] for r in ev["rows"]),
                                      "penup_35deg_W": ev["rows"][0]["P_penup_W"]}
    return {"rows": out, "label": "CALCULATION (bnib/candidates.evaluate: duty model, 8 Hz, 70 % contact, CON-20 writing speed; "
                                  "Km image-method upper bound x scale)"}


def summary(R_s_mm: float, lay: Dict, quick: bool = False) -> Dict:
    """Everything the nib section of Rev K reports, at the positions of the Rev K layout (lay: layout.base_components)."""
    coil = buildable_coil(quick=quick)
    fp = idealised_footprint()
    ld = leads()
    comps = {c["id"]: c for c in lay["components"]}
    P = lay["positions"]
    moving = [c for c in lay["components"] if c.get("moves_with") == "nib" and c.get("mass_g")]
    m_car = sum(c["mass_g"] for c in moving if c["id"] not in ("ball", "refill", "refill_holder"))
    m_move = sum(c["mass_g"] for c in moving)
    zc = sum(c["mass_g"] * 0.5 * (c["z0"] + c["z1"]) for c in moving if c["id"] not in ("ball", "refill", "refill_holder")) / m_car
    zb = (val(PR.FRONT["carrier_front_z_mm"]) + 1.0, 0.5 * sum(P["flange_z"]))
    md = modes_grid(R_s_mm, m_car, quick=quick, zb=zb, z_car=zc)
    L_lever = comps["refill_holder"]["z0"] + val(PR.HEAD["puck"])["stem_mm"]
    cp_B = couple(L_lever_mm=L_lever)
    from .layout import LAY
    bg = val(LAY["ball_guide"])
    cp_K = couple(wire_mat="C17200_TH04", wire_d_mm=WIRE_CHOICE["d_mm"], L_lever_mm=L_lever,
                  r_ball_circle_mm=bg["circle_r_mm"], n_balls=bg["n_per_side"], race_preload_N=bg["race_spring_preload_N"])
    mag_z0 = comps["pole_magnet_1"]["z0"]
    hall = hall_fields(mag_z0, P["hall_die_z"], comps["nose_hall"]["offset"][0], coil, quick=quick,
                       gap_mm=P["hall_die_z"] - P["position_magnet_centre_z"], z_coil0_mm=comps["coil_x"]["z0"])
    coil_margin = coil["geometry_mm"]["bore_r"] - coil["geometry_mm"]["corner_at_stop_r"]
    dr = drop(m_move, comps["carrier_flange"]["d0"] / 2, coil_margin)
    return {"coil_footprint": fp, "buildable_coil": coil, "leads": ld, "modes": md, "couple": cp_K, "couple_studyB": cp_B,
            "hall": hall, "drop": dr, "m_carrier_g": m_car, "m_move_g": m_move, "carrier_com_z_mm": zc,
            "guide_stations_z_mm": zb, "L_lever_mm": L_lever,
            "Km_tip_revK": {"x": val(PR.B1["Km_tip"]) * coil["ratio_x"], "y": val(PR.B1["Km_tip"]) * coil["ratio_y_over_idealised_x"],
                            "x_min_over_stroke": val(PR.B1["Km_tip"]) * coil["Km_min_x"] / coil["Km_idealised_x_same_method"],
                            "power_factor_vs_studyB": 0.5 * (1 / coil["ratio_x"] ** 2 + 1 / coil["ratio_y_over_idealised_x"] ** 2),
                            "label": "CALCULATION (study B's Km_tip x the buildable coil's ratio to study B's idealised coil, "
                                     "same magpylib method; an upper bound)"},
            "wire_mc": wire_mc_table(n=500 if quick else 2000),
            "power_table": power_table()}
