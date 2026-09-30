"""Calculations behind the bench build plan (study H): python3 results/benchbuild/tools/bench_calcs.py

Writes results/benchbuild/bench_calcs.json. Every number is a CALCULATION on the inputs named beside it
(MANUFACTURER / LITERATURE ledger ids, repository results, or ASSUMPTION). Nothing here is a measurement.

  1  first transverse mode of the C17200 wire coupons, and how much a fast fatigue drive raises the clamp stress
     (sets the fatigue drive frequency and the test duration: DEC-098 proposed)
  2  anchor coupon: beam-only axial stiffness against foil thickness, and the beam width that keeps 76.6 N/m
  3  the residual lateral load at which each DEC-072 candidate reaches the assumed 0.15 W copper allocation
     (interpolated from the pass's own duty screen: DEC-096 proposed)
  4  gravity's lateral load on the moving nib at 35/50/75 deg
  5  five-bar endpoint resolution with 12/14/16-bit output encoders (wholepen.grounded.FiveBar, read-only)
  6  test uncertainty ratios of the drag and anchor measurements with the proposed instruments
  7  R9: the normal force reachable in every stroke direction with the 100 g and 250 g axial cells
     (N = F_c / (sin theta - mu cos beta cos theta), validation/bench_protocols.md s0.11)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "benchbuild" / "bench_calcs.json"


def wire_modes():
    # C17200: E 127.6 GPa and density 8.26 g/cm3 (MFR AMF-19); diameter 0.10 mm (DEC-063; the pass's reach candidate)
    E, rho, d = 127.6e9, 8260.0, 0.10e-3
    I = math.pi * d ** 4 / 64
    mu = rho * math.pi * d ** 2 / 4
    EI = E * I

    def f1(L, T):
        beam = 22.37 / (2 * math.pi * L ** 2) * math.sqrt(EI / mu)       # clamped-clamped beam, first mode
        return beam, beam * math.sqrt(1 + T * L ** 2 / (4 * math.pi ** 2 * EI))   # Rayleigh estimate with tension

    cases = []
    for name, L, T, basis in [
            ("Rev K wire, 26.8 mm, no preload", 0.0268, 0.0, "DEC-063 geometry; preload 0"),
            ("Rev K wire, 26.8 mm, 0.05 N preload", 0.0268, 0.05, "AC-K21-03's preload limit"),
            ("reach wire, 34 mm, 5 mN assembly tension", 0.034, 0.005, "results/improvement/mechanics/mechanics_study.json"),
            ("reach wire, 34 mm, 11 mN at the 1.7 mm stop", 0.034, 0.0111, "same file, worst_corner tension_total_N")]:
        beam, f = f1(L, T)
        row = {"case": name, "L_mm": L * 1e3, "tension_N": T, "f1_beam_only_Hz": beam, "f1_with_tension_Hz": f,
               "basis": basis, "drive": []}
        for fd in (60, 100, 150, 200):
            r = fd / f
            # base-excited fixed-guided wire: the static S-shape has clamp curvature 6 delta/L^2; the symmetric first
            # mode driven by the support's inertia adds about 19.7 a/L^2 with a ~ 0.5 delta r^2/(1-r^2) (single-mode
            # estimate, ASSUMPTION) -> relative rise of the clamp stress 1.64 r^2/(1-r^2)
            rise = 1.64 * r * r / (1 - r * r) if r < 1 else float("inf")
            row["drive"].append({"drive_Hz": fd, "ratio": r, "clamp_stress_rise": rise,
                                 "hours_for_43p2M_cycles": 43.2e6 / fd / 3600})
        row["max_drive_Hz_at_0p2_f1"] = 0.2 * f
        row["hours_at_0p2_f1"] = 43.2e6 / (0.2 * f) / 3600
        cases.append(row)
    return {"label": "CALCULATION (Rayleigh first mode of a clamped-clamped wire with tension; single-mode base-"
                     "excitation estimate of the clamp stress rise, ASSUMPTION); inputs MFR AMF-19, DEC-063, "
                     "results/improvement/mechanics/mechanics_study.json",
            "EI_Nm2": EI, "mu_kg_per_m": mu, "cases": cases,
            "reading": "bench_protocols.md's 'about 60 h at 200 Hz' raises the clamp stress of a 34 mm reach wire by "
                       "~90 % over the quasi-static stress the pen sees (tremor <= 12 Hz), and a 26.8 mm Rev K wire by "
                       "12-33 %; at <= 0.2 x the measured first mode the rise is <= ~7 %: 43.2 M cycles then take "
                       "3-8 days per batch"}


def anchor_foil():
    # anchor coupon: 4 fixed-guided beams, k = 4 E w t^3 / L^3 (mechanics/cad/improved_nib.py), E 193 GPa ASSUMPTION
    E, L, w0, t0 = 193e9, 6e-3, 0.5e-3, 35e-6
    rows = []
    for t_um in (25.4, 30.0, 35.0, 38.1, 40.0, 50.0):
        t = t_um * 1e-6
        k = 4 * E * w0 * t ** 3 / L ** 3
        rows.append({"foil_um": t_um, "k_beams_N_per_m_at_w0p5mm": k,
                     "beam_width_mm_for_76p6_N_per_m": w0 * (t0 / t) ** 3 * 1e3})
    k0 = 4 * E * w0 * t0 ** 3 / L ** 3
    return {"label": "CALCULATION (fixed-guided beams; E 193 GPa ASSUMPTION as the pass's CAD); 25.4 and 38.1 um are the "
                     "US 0.001/0.0015 inch shim gauges",
            "k_design_N_per_m": k0, "sensitivity": {"dk_over_k_per_dt_over_t": 3.0, "dk_over_k_per_dw_over_w": 1.0,
                                                    "dk_over_k_per_dL_over_L": -3.0},
            "example": "a +-1 um foil thickness error on 35 um moves the beam stiffness by +-8.6 %; measure the foil, "
                       "then set the artwork's beam width",
            "table": rows,
            "beam_stress_at_50um_axial_MPa": 3 * E * t0 * 50e-6 / L ** 2 / 1e6,
            "note": "bending stress of a fixed-guided beam 3 E t delta / L^2 at the 50 um anchor motion of the worst "
                    "corner (mechanics_study.json): far below 301 full-hard's 540 MPa fatigue strength (LIT AMF-20)"}


def selection_thresholds():
    f = ROOT / "results" / "improvement" / "mechanics" / "mechanics_study.json"
    d = json.loads(f.read_text())
    out = []
    for c in d["candidates"]:
        pts = sorted((float(k) * 1e3, max(r["copper_power_W"] for r in v["rows"])) for k, v in c["duty_by_residual"].items())
        F = np.array([p[0] for p in pts])
        s = np.sqrt([p[1] for p in pts])
        tgt = math.sqrt(0.15)
        cross = None
        for i in range(len(F) - 1):
            if s[i] <= tgt <= s[i + 1]:
                cross = float(F[i] + (tgt - s[i]) * (F[i + 1] - F[i]) / (s[i + 1] - s[i]))
        out.append({"radius_mm": c["radius_mm"], "worst_copper_W_by_residual_mN": {f"{a:g}": b for a, b in pts},
                    "residual_mN_at_0p15W": cross if cross is not None else ("below 20 mN" if s[0] > tgt else "above 80 mN")})
    return {"label": "CALCULATION: linear interpolation of sqrt(worst copper loss) between the pass's duty-screen points "
                     "(20/40/80 mN residual, 0.7 field scale, 4/8/12 Hz full-radius motion; results/improvement/mechanics/"
                     "mechanics_study.json); the 0.15 W allocation is the pass's ASSUMPTION",
            "candidates": out,
            "use": "provisional reading only: DEC-096 re-runs the duty screen (python -m revk.improve) with the measured "
                   "residual load, force map and guide drag instead of this interpolation"}


def residual_sum():
    """Conservative sum of magnitudes of the calculated lateral loads at 35 deg that revk.improve.matched_force_duty
    bundles into residual_N (it models no gravity term): gravity across the axis, the counter-face residual at the
    95th percentile and the guide drag at 4 N preload."""
    g35 = 1e3 * 3.67e-3 * 9.81 * math.cos(math.radians(35))
    parts = {"gravity_35deg_mN": g35,
             "counterface_residual_p95_mN": {"Rev K head (docs/revK_design.md s3.4, CALC)": 11.2,
                                             "study B face (docs/balanced_nib.md s1, CALC)": 13.1},
             "guide_drag_4N_mN": 8.07}
    total = {k: g35 + v + 8.07 for k, v in parts["counterface_residual_p95_mN"].items()}
    return {"label": "CALCULATION: sum of magnitudes (conservative: the duty screen applies residual_N along the motion "
                     "direction, gravity has a fixed direction); inputs are themselves CALCULATIONS",
            "parts": parts, "sum_mN": total,
            "reading": "about 49-51 mN, above the ~34 mN at which the 1.5 mm candidate reaches 0.15 W and near the ~53 mN "
                       "of the 1.059 mm candidate: the measured residual and drag decide (DEC-096)"}


def gravity():
    rows = []
    for m_g, src in ((3.57, "1.059 mm candidate moving mass"), (3.67, "1.5 mm candidate moving mass")):
        rows.append({"moving_mass_g": m_g, "source": src + " (mechanics_study.json, ASSUMPTION estimate)",
                     "lateral_mN": {str(t): 1e3 * m_g * 1e-3 * 9.81 * math.cos(math.radians(t)) for t in (35, 50, 75)}})
    return {"label": "CALCULATION: component of the moving mass's weight across the pen axis, m g cos(theta)", "rows": rows}


def fivebar_encoders():
    from wholepen.grounded import FiveBar
    fb = FiveBar()
    xs = np.linspace(-fb.workspace_half_x, fb.workspace_half_x, 13)
    ys = np.linspace(fb.centre_y - fb.workspace_half_y, fb.centre_y + fb.workspace_half_y, 9)
    out = []
    for bits in (12, 14, 16):
        q = 2 * math.pi / 2 ** bits
        worst = 0.0
        for x in xs:
            for y in ys:
                J = fb.kinematics([x, y])["J"]                 # dp/dtheta (checked by finite differences)
                C = J @ J.T * (q ** 2 / 12)
                worst = max(worst, math.sqrt(max(np.linalg.eigvalsh(C))))
        out.append({"bits": bits, "worst_1sigma_endpoint_quantisation_um": worst * 1e6})
    return {"label": "CALCULATION with wholepen.grounded.FiveBar (read-only): uniform quantisation of both output angles "
                     "mapped through the Jacobian over the 60 x 40 mm patch; encoder integral non-linearity is not "
                     "included (to measure: EXP-BB06)", "rows": out}


def fivebar_force_bounds():
    """Endpoint force the five-bar can produce with both output torques at the rated value (box constraint, worst
    pose and direction) against the guaranteed force disk (the pass's static_force_radius): why a current limit
    alone cannot enforce the 0.4 N cap."""
    from wholepen.grounded import FiveBar
    fb = FiveBar()
    tau = fb.rated_torque * fb.ratio * fb.transmission_efficiency
    xs = np.linspace(-fb.workspace_half_x, fb.workspace_half_x, 25)
    ys = np.linspace(fb.centre_y - fb.workspace_half_y, fb.centre_y + fb.workspace_half_y, 17)
    fmax, rmin = 0.0, float("inf")
    for x in xs:
        for y in ys:
            JinvT = np.linalg.inv(fb.kinematics([x, y])["J"]).T
            for s in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                fmax = max(fmax, float(np.linalg.norm(JinvT @ (tau * np.array(s)))))
            rmin = min(rmin, fb.static_force_radius([x, y]))
    return {"label": "CALCULATION with wholepen.grounded.FiveBar (rated torque 6.21 mNm, 6:1, 80 % efficiency: MFR sheet and "
                     "ASSUMPTIONS of the pass)", "output_torque_at_rated_mNm": tau * 1e3,
            "largest_endpoint_force_N": fmax, "guaranteed_force_disk_N": rmin,
            "current_fraction_for_0p6N_worst_case": 0.6 / fmax, "disk_at_that_fraction_N": rmin * 0.6 / fmax,
            "reading": "a hardware current limit that bounds the worst case below ~0.6 N leaves a disk below the 0.4 N cap, "
                       "so the cap is software and a breakaway coupling (0.5-0.8 N) is the physical backstop (DEC-099)"}


def turs():
    # drag line 5 mN (AC-K20-01) with predictions 2.6 mN (Rev K) and 8.07 mN (reach, 4 N preload): distance ~2.4-3 mN
    lsb10 = 0.1e-3 * 0.001 * 2 * 1e3             # +-0.1 % RO hysteresis of a 0.1 N cell (MFR AMF-225), k=2 -> mN
    k3d40_2N = 4.3                               # friction-force U of the +-2 N plate, mN (docs/measurement_rig.md s2.4)
    return {"label": "CALCULATION (simple GUM-style bounds; ASSUMPTION that the cell's hysteresis dominates)",
            "drag_line_mN": 5.0, "distance_to_line_mN": [2.4, 3.07],
            "LSB200_10g_U_mN_bound": 0.2, "TUR_LSB200_10g": [2.4 / 0.2, 3.07 / 0.2],
            "K3D40_2N_U_mN": k3d40_2N, "TUR_K3D40_2N": [2.4 / k3d40_2N, 3.07 / k3d40_2N],
            "anchor": {"band_N_per_m": [80, 120], "force_at_50um_mN_for_100N_per_m": 5.0,
                       "balance_1mg_resolution_mN": 9.81e-3, "micrometer_1um_on_100um_span": 0.01,
                       "note": "slope over 0-100 um in 10 um steps: displacement error dominates, ~1 % per step; TUR "
                               "against the +-20 N/m half band > 10"},
            "reading": "measure guide drag with a 10 g (0.1 N) cell, not with a K3D40 plate (TUR < 1)"}


def r9_normal_force_reach():
    """R9 sets N through the axial force F_c. The normal force for a given F_c depends on the stroke direction beta;
    the lowest N over all directions is F_c / (sin theta + mu cos theta) (cos beta = -1), the highest
    F_c / (sin theta - mu cos theta). Cell limits: the rig design uses the 100 g LSB200 for F_c <= 0.5 N and the
    250 g cell above (docs/measurement_rig.md s2.2; 250 g = 2.45 N rated, MFR AMF-225); mu 0.15 as in s0.11."""
    mu = 0.15
    cells = {"LSB200 100 g (design use F_c <= 0.5 N)": 0.5, "LSB200 250 g (rated 2.45 N)": 2.45}
    rows = []
    for th in (35, 50, 75):
        t = math.radians(th)
        lo_den, hi_den = math.sin(t) + mu * math.cos(t), math.sin(t) - mu * math.cos(t)
        rows.append({"theta_deg": th,
                     "N_every_direction_N": {k: fc / lo_den for k, fc in cells.items()},
                     "N_best_direction_N": {k: fc / hi_den for k, fc in cells.items()},
                     "F_c_for_N_2N_every_direction_N": 2.0 * lo_den,
                     "F_c_for_N_4N_every_direction_N": 4.0 * lo_den})
    return {"label": "CALCULATION: N = F_c / (sin theta - mu cos beta cos theta) (validation/bench_protocols.md s0.11), "
                     "mu 0.15 (ASSUMPTION, the protocols' design value)",
            "rows": rows,
            "reading": "the first build (100 g cell, F_c <= 0.5 N) reaches N of about 0.5 N at 75 deg and 0.7 N at 35 deg "
                       "in every direction: EXP-T01's grid (F_c 0.08-0.30 N) but not AC-B01-20's 0.2-2.0 N envelope, which "
                       "needs the 250 g cell (F_c 2.0 N at 75 deg) and the +-10 N plate (2 N is the +-2 N plate's full "
                       "scale); EXP-B01's 4 N level needs F_c 2.8-4.0 N, beyond the 250 g cell at most tilts"}


def main():
    out = {"evidence_status": "CALCULATION (study H bench build plan); nothing measured",
           "wire_modes_and_fatigue_drive": wire_modes(), "anchor_foil": anchor_foil(),
           "candidate_selection_thresholds": selection_thresholds(), "gravity_lateral_load": gravity(),
           "residual_sum_35deg": residual_sum(),
           "fivebar_encoder_resolution": fivebar_encoders(), "fivebar_force_bounds": fivebar_force_bounds(),
           "test_uncertainty_ratios": turs(), "r9_normal_force_reach": r9_normal_force_reach()}
    try:
        from stabpen import provenance
        out["meta"] = provenance.metadata(out["evidence_status"])
    except Exception as e:
        out["meta"] = {"note": f"stabpen.provenance unavailable: {e!r}"}
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    w = out["wire_modes_and_fatigue_drive"]["cases"]
    for c in w:
        print(f"{c['case']:<44} f1 {c['f1_with_tension_Hz']:6.0f} Hz; 0.2 f1 = {c['max_drive_Hz_at_0p2_f1']:5.0f} Hz "
              f"-> {c['hours_at_0p2_f1']:5.0f} h; rise at 200 Hz {c['drive'][3]['clamp_stress_rise']:.2f}")
    for c in out["candidate_selection_thresholds"]["candidates"]:
        print("radius", round(c["radius_mm"], 3), "mm: 0.15 W reached at residual", c["residual_mN_at_0p15W"])
    print("written:", OUT)


if __name__ == "__main__":
    main()
