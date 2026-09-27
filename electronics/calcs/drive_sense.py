#!/usr/bin/env python3
"""Drive-stage and sensing calculations for the Rev A research electronics.

Evidence status: ANALYTICAL CALCULATION from datasheet-class values (marked
VERIFY where a datasheet check is outstanding) and the parameter file.
Nothing here is measured.

1. Coil resistance vs supply headroom.  Holding power P = (F_tip/(n Km))^2
   does not depend on the winding, but the voltage needed to push the holding
   current does: V = F_tip/(n Km sqrt(R)) (a R + R_ext) + back-EMF.  The coil
   is wound so that, at the minimum actuation voltage and the hot-coil design
   temperature, the supply is never the binding constraint inside the part of
   the writing envelope the thermal limit already allows.
2. Current-sense chain: range, resolution, noise, offset.
3. PWM ripple (exact exponential steady state, drive/brake slow decay).
4. Current-loop bandwidth from the loop delay.
5. Timing: one 500 us stage period (ADC scan, SPI transactions, compute).
6. Electronics power budget.

Outputs: results/electronics/drive_sense.json, fig_headroom.png,
fig_pwm_ripple.png, fig_stage_timeline.png.
Run: python3 electronics/calcs/drive_sense.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from stabpen import contact, plotstyle, provenance  # noqa: E402
from stabpen import params as sp  # noqa: E402

OUT = os.path.join(ROOT, "results", "electronics")

# ---------------------------------------------------------------- component values
# (value, source/status).  VERIFY = datasheet check outstanding.
COMP = {
    "r_ds_on_hs_ls_ohm": (0.28, "DRV8212P HS+LS typ at 25 C; VERIFY; x1.5 hot -> 0.42"),
    "r_ds_hot_factor": (1.5, "assumed FET tempco at 100 C junction"),
    "r_shunt_ohm": (0.10, "design (electronics/gen/design_revA.py R30/R50)"),
    "r_load_switch_ohm": (0.08, "TPS22917 Ron at 3.6 V; VERIFY; shared by both axes"),
    "r_wiring_ohm": (0.06, "flex + connector per coil loop; estimate"),
    "d_max": (0.97, "max PWM duty kept for current sampling window"),
    "ina_gain": (10.0, "INA241A1 G = 10 V/V"),
    "ina_bw_hz": (1.0e6, "INA241A1 small-signal bandwidth class; VERIFY"),
    "ina_vos_v": (25e-6, "INA241A1 input offset max class; VERIFY"),
    "ina_en_nv_rthz": (40.0, "INA241 input-referred noise density class; VERIFY"),
    "aa_r_ohm": (1000.0, "design"),
    "aa_c_f": (10e-9, "design"),
    "vref_v": (1.25, "REF3012"),
    "adc_bits": (12, "nRF5340 SAADC differential, 12-bit mode"),
    "adc_fs_diff_v": (1.2, "gain 1/2, internal 0.6 V reference -> +/-1.2 V"),
    "adc_enob": (10.3, "SAADC effective bits class; VERIFY"),
    "adc_tacq_s": (3e-6, "SAADC TACQ setting for <= 10 kOhm source"),
    "adc_tconv_s": (2e-6, "SAADC conversion time"),
    "pwm_clock_hz": (16e6, "nRF5340 PWM base clock"),
    "f_pwm_hz": (40e3, "centre-aligned, 200 duty levels; 20 periods per stage tick; ripple and loop-delay choice (see pwm_ripple, current_loop)"),
    "f_stage_hz": (2000.0, "config control.f_stage"),
    "t_coil_design_c": (None, "hot-coil design point: configuration B at the design load, results/thermal/thermal.json (read at run time)"),
    "t_coil_limit_c": (120.0, "coil temperature limit used for the thermal allowable (analysis/thermal.py)"),
    "br_tempco_per_k": (-0.0012, "NdFeB reversible Br tempco class (AMF-27, AMF-29); VERIFY with the magnet grade"),
    "f_corr_hz": (12.0, "highest tremor frequency addressed (REQ-ENV-003)"),
    "q_corr_m": (0.55e-3, "correction amplitude at the control limit q_lim (sim/pensim/model.py)"),
    "t_amb_c": (25.0, "config thermal.t_ambient"),
    "v_bat_act_min": (3.3, "config electrical.v_bat_min"),
    "p_cu_allow_w": (None, "results/thermal/thermal.json allowable average copper loss, moving coil (read at run time; 25 C-referenced)"),
    "v_tip_stage_max": (0.05, "m/s stage velocity relative to housing (tremor 0.3 mm @ 9 Hz ~ 17 mm/s, x3)"),
}


def _thermal_inputs():
    """Hot-coil design point, thermal allowable and structure (magnet) model from analysis/thermal.py."""
    th = json.load(open(os.path.join(ROOT, "results", "thermal", "thermal.json")))
    b = next(v for k, v in th["cases"].items() if k.startswith("B lever") and k.endswith("| design"))
    COMP["t_coil_design_c"] = (b["T_coil_end_C"], COMP["t_coil_design_c"][1])
    COMP["p_cu_allow_w"] = (th["allowable_avg_copper_W_for_41C_and_coil120C"]["moving"], COMP["p_cu_allow_w"][1])
    return th["two_node_governor_model"], th["meta"].get("parameters_version")


def cv(k):
    return COMP[k][0]


def envelope(n=20000, seed=3):
    """Writing envelope sample: altitude, normal force, friction (bench ranges from config)."""
    rng = np.random.default_rng(seed)
    th = np.radians(rng.uniform(35, 75, n))
    N = np.exp(rng.uniform(math.log(0.2), math.log(2.0), n))
    mu = rng.uniform(0.05, 0.35, n)
    betas = np.linspace(0, 2 * math.pi, 72, endpoint=False)
    R = np.array([contact.transverse_load(N, mu, b, th) for b in betas])     # (72, n)
    return {"theta": th, "N": N, "mu": mu, "F_max": R.max(axis=0), "F_rms": np.sqrt((R ** 2).mean(axis=0))}


def headroom(p, env, two_node):
    """Supply headroom of candidate windings over the writing envelope.

    Thermal feasibility: direction-averaged continuous load as copper loss referenced to 25 C,
    compared with the thermal allowable (analysis/thermal.py adds the tempco feedback itself).
    Voltage feasibility at each envelope point uses that point's own steady coil temperature and
    magnet (structure) temperature from the two-node model, the worst stroke direction, and three
    correction cases on top of the static load: none, typical (9 Hz, 0.3 mm) and extreme (f_corr, q_lim).
    """
    n = p["stage.L2"] / p["stage.L1"]
    Km20 = p["actuator.Kf"] / math.sqrt(p["actuator.R20"])
    alpha = p["actuator.alpha_cu"]
    a = 1 + alpha * (cv("t_coil_design_c") - 20.0)
    Km_hot = Km20 / math.sqrt(a)
    r_ext = cv("r_ds_on_hs_ls_ohm") * cv("r_ds_hot_factor") + cv("r_shunt_ohm") + cv("r_wiring_ohm")
    Km25 = Km20 / math.sqrt(1 + alpha * 5.0)
    P25 = (env["F_rms"] / (n * Km25)) ** 2
    therm_ok = P25 <= cv("p_cu_allow_w")
    # steady temperatures per envelope point (continuous contact), two-node model
    T_coil = np.full_like(P25, 60.0)
    for _ in range(60):
        P_hot = P25 * (1 + alpha * (T_coil - 25.0))
        T_coil = two_node["T_struct_no_coil_loss_C"] + two_node["R_coil_amb_total_K_per_W"] * P_hot
    T_mag = two_node["T_struct_no_coil_loss_C"] + two_node["R_struct_amb_K_per_W"] * P_hot
    k_br = 1 + cv("br_tempco_per_k") * (T_mag - 20.0)
    a_pt = 1 + alpha * (T_coil - 20.0)

    def f_corr(f_hz, q):
        return p["stage.m_eq"] * (2 * math.pi * f_hz) ** 2 * q + p["stage.k_tip"] * q
    corr = {"static": 0.0, "typical_9Hz_0p3mm": f_corr(9.0, 0.3e-3), "extreme": f_corr(cv("f_corr_hz"), cv("q_corr_m"))}
    rows = []
    for R in (2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 11.0):
        for vb in (3.3, 3.7, 4.2):
            row = {"R20_ohm": R, "Kf_N_per_A": Km20 * math.sqrt(R), "L_H": p["actuator.L"] * R / p["actuator.R20"],
                   "v_bat": vb, "bridge_loss_frac": float(r_ext / (a * R))}
            for name, Fc in corr.items():
                Kf = Km20 * math.sqrt(R) * k_br
                I = (env["F_max"] + Fc) / (n * Kf)       # worst stroke direction, one axis carries it all
                V = I * (a_pt * R + r_ext) + Kf * n * cv("v_tip_stage_max")
                v_av = vb * cv("d_max") - 2 * I * cv("r_load_switch_ohm")
                ok = V <= v_av
                row[f"frac_ok_within_thermal_{name}"] = float(ok[therm_ok].mean())
                row[f"worst_voltage_ratio_{name}"] = float((V[therm_ok] / v_av[therm_ok]).max())
                if name == "static":
                    row["I_p95_A"] = float(np.percentile(I[therm_ok], 95))
                    row["I_max_within_thermal_A"] = float(I[therm_ok].max())
            rows.append(row)
    return {"n": n, "Km20": Km20, "Km_hot": Km_hot, "a_hot": a, "t_coil_design_C": cv("t_coil_design_c"),
            "r_ext_ohm": r_ext, "r_ext_note": "includes 0.06 ohm wiring; the simulator uses r_bridge + r_shunt = 0.52 ohm",
            "t_coil_max_in_envelope_C": float(T_coil[therm_ok].max()), "t_magnet_max_in_envelope_C": float(T_mag[therm_ok].max()),
            "F_corr_N": corr, "p_cu_allow_W": cv("p_cu_allow_w"), "frac_thermal_ok": float(therm_ok.mean()), "rows": rows}


def choose_R(h):
    """Assessment only: largest winding resistance for which, at the minimum actuation voltage, the static
    hold is voltage-feasible at every thermally allowed envelope point and the typical correction at
    >= 99.9 % of them.  The design baseline is the YAML actuator.R20 (DEC-012)."""
    cands = [r for r in h["rows"] if r["v_bat"] == cv("v_bat_act_min") and r["frac_ok_within_thermal_static"] >= 1.0
             and r["frac_ok_within_thermal_typical_9Hz_0p3mm"] >= 0.999]
    return max(cands, key=lambda r: r["R20_ohm"]) if cands else None


def sense_chain():
    G = cv("ina_gain"); rsh = cv("r_shunt_ohm")
    k = G * rsh                                       # V/A
    lsb = 2 * cv("adc_fs_diff_v") / 2 ** cv("adc_bits")
    en_out = cv("ina_en_nv_rthz") * 1e-9 * G
    f_aa = 1 / (2 * math.pi * cv("aa_r_ohm") * cv("aa_c_f"))
    nbw = min(f_aa, cv("ina_bw_hz")) * math.pi / 2
    v_noise = en_out * math.sqrt(nbw)
    adc_noise_v = 2 * cv("adc_fs_diff_v") / 2 ** cv("adc_enob") / math.sqrt(12)
    return {
        "sensitivity_V_per_A": k,
        "linear_range_A": (cv("vref_v") - 0.05) / k,
        "adc_lsb_mA": lsb / k * 1e3,
        "adc_range_A": cv("adc_fs_diff_v") / k,
        "ina_noise_mA_rms": v_noise / k * 1e3,
        "adc_noise_mA_rms": adc_noise_v / k * 1e3,
        "total_noise_mA_rms_per_sample": math.hypot(v_noise, adc_noise_v) / k * 1e3,
        "offset_mA_uncal": cv("ina_vos_v") * G / k * 1e3,
        "aa_corner_Hz": f_aa,
        "aa_phase_deg_at_2kHz": math.degrees(math.atan(2000 / f_aa)),
        "shunt_loss_W_at_0p5A": 0.25 * rsh,
        "trip_window_A": 0.8,
        "note": "offset calibrated at every pen-lift with the bridge in coast (I = 0)",
    }


def pwm_ripple(R, L, vb, D, f, r_ext):
    """Steady-state peak-to-peak ripple for drive (+V) / brake (0 V) slow decay.
    Exact: on-phase i -> (V/Rt) with tau, off-phase i -> 0 with tau."""
    Rt = R + r_ext
    tau = L / Rt
    T = 1 / f
    ton, toff = D * T, (1 - D) * T
    iinf = vb / Rt
    eon, eoff = math.exp(-ton / tau), math.exp(-toff / tau)
    # periodic solution: i_min -> i_max over ton, i_max -> i_min over toff
    i_min = iinf * (1 - eon) * eoff / (1 - eon * eoff)
    i_max = iinf + (i_min - iinf) * eon
    return i_max - i_min, 0.5 * (i_max + i_min), tau


def current_loop(R, L):
    Ts = 1 / cv("f_pwm_hz")
    t_aa = cv("aa_r_ohm") * cv("aa_c_f")
    delay = Ts + 0.5 * Ts + t_aa                     # compute + ZOH + anti-alias (first-order approximation)
    # PI with zero on the electrical pole: open loop = wc/s * exp(-s delay); PM = 90 - 360 f_c delay
    fc = (90.0 - 50.0) / (360.0 * delay)
    return {"loop_delay_us": delay * 1e6, "crossover_Hz_for_PM50": fc, "electrical_pole_Hz": (R / L) / (2 * math.pi),
            "Kp_V_per_A": 2 * math.pi * fc * L, "Ki_V_per_As": 2 * math.pi * fc * R}


def timeline():
    """One stage period (500 us) as (resource, label, start_us, duration_us)."""
    ev = []
    per = 1e6 / cv("f_pwm_hz")
    for k in range(int(round(cv("f_pwm_hz") / cv("f_stage_hz")))):     # PWM periods per stage tick
        t0 = k * per + per / 2 - 5.0
        ev.append(("SAADC", "I_x, I_y" if k == 0 else "", t0, 10.0))
        ev.append(("CPU", "", t0 + 10.0, 1.5))       # current PI both axes
    ev += [("SPIM4 32 MHz", "Hall x,y,z", 30.0, 14.0), ("SPIM4 32 MHz", "optics 1-3", 50.0, 36.0),
           ("SPIB 8 MHz", "IMU 12 B", 30.0, 16.0),
           ("CPU", "estimator + servo", 90.0, 40.0), ("CPU", "log + comms", 140.0, 60.0),
           ("SAADC", "VBAT, NTC (1 per 20 ticks)", 470.0, 10.0)]
    return ev


def electronics_power():
    loads_mA = {  # typical active current at 3.0-3.7 V; VERIFY each
        "nRF5340 app 128 MHz + net core idle (LDO mode)": 7.5,
        "BLE connection (average, 7.5 ms interval, streaming)": 2.5,
        "TMAG5170 continuous 3-axis": 2.3,
        "LSM6DSV16X 7.68 kHz accel+gyro high-performance": 0.65,
        "optical modules x3 (unselected; placeholder)": 15.0,
        "INA241 x2": 2.0,
        "LMV331 x4, logic, REF3012, dividers": 0.4,
        "QSPI flash (write duty 5 %)": 0.8,
        "TLV75530 quiescent": 0.03,
    }
    tot = sum(loads_mA.values())
    return {"loads_mA": loads_mA, "total_mA": tot, "total_mW_at_3V7": tot * 3.7}


def figures(h, choice, ripple_rows, ev, env, p):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    # --- headroom at the minimum actuation voltage: feasible fraction vs winding resistance
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    vmin = cv("v_bat_act_min")
    rr = [r for r in h["rows"] if r["v_bat"] == vmin]
    xs = [r["R20_ohm"] for r in rr]
    for j, (key, lab) in enumerate((("static", "static hold"), ("typical_9Hz_0p3mm", "+ typical correction (9 Hz, 0.3 mm)"),
                                    ("extreme", f"+ extreme correction ({cv('f_corr_hz'):g} Hz, q_lim)"))):
        ys = [100 * r[f"frac_ok_within_thermal_{key}"] for r in rr]
        ax.plot(xs, ys, color=plotstyle.SERIES[j], label=lab)
        ax.plot(xs, ys, **plotstyle.marker_kw(plotstyle.SERIES[j]))
    ax.axvline(choice["R20_ohm"], color=plotstyle.MUTED, lw=1.0)
    ax.text(choice["R20_ohm"] + 0.15, 76, f"baseline {choice['R20_ohm']:g} ohm", color=plotstyle.INK2, fontsize=8.5)
    ax.set_xlabel("Coil resistance at 20 C (ohm), Km fixed")
    ax.set_ylabel("Voltage-feasible share (%)")
    ax.set_ylim(75, 101)
    ax.set_title(f"Winding choice at VBAT {vmin} V: where the supply binds before the heat limit", loc="left", fontsize=10)
    ax.legend(loc="lower left", fontsize=8)
    plotstyle.stamp(fig, "analytical calculation", f"share of the {100*h['frac_thermal_ok']:.0f} % thermally allowed envelope; coil up to {h['t_coil_max_in_envelope_C']:.0f} C")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_headroom.png"))
    plt.close(fig)
    # --- PWM ripple vs frequency for the chosen winding
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for j, D in enumerate((0.3, 0.5, 0.8)):
        rr = [r for r in ripple_rows if r["D"] == D]
        ax.plot([r["f_pwm_kHz"] for r in rr], [r["ripple_pp_mA"] for r in rr], color=plotstyle.SERIES[j], label=f"duty {D:g}")
    ax.axvline(cv("f_pwm_hz") / 1e3, color=plotstyle.MUTED, lw=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("PWM frequency (kHz), centre-aligned, drive/brake")
    ax.set_ylabel("Coil current ripple, peak-peak (mA)")
    ax.set_title(f"Current ripple, {choice['R20_ohm']:g} ohm coil at 3.7 V", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    plotstyle.stamp(fig, "analytical calculation", "exact exponential steady state; L scaled with turns^2 from the EM estimate")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_pwm_ripple.png"))
    plt.close(fig)
    # --- stage-period timeline
    res = ["SAADC", "SPIM4 32 MHz", "SPIB 8 MHz", "CPU"]
    fig, ax = plt.subplots(figsize=(9.0, 2.8))
    for j, r in enumerate(res):
        for rr, lab, t0, d in ev:
            if rr != r:
                continue
            ax.barh(j, d, left=t0, height=0.55, color=plotstyle.SERIES[j], edgecolor=plotstyle.SURFACE, linewidth=1.0)
            if lab:
                ax.text(t0 + d + 3, j, lab, va="center", fontsize=7.5, color=plotstyle.INK2)
    ax.set_yticks(range(len(res)), res)
    ax.set_xlim(0, 500)
    ax.invert_yaxis()
    ax.set_xlabel("Time within one 2 kHz stage period (us)")
    ax.set_title("Proposed scan and compute schedule (current samples at every PWM centre)", loc="left", fontsize=10)
    plotstyle.stamp(fig, "proposed design", "durations are estimates to be replaced by logic-analyser captures (bring-up step 7)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_stage_timeline.png"))
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    p = sp.load()
    two_node, th_version = _thermal_inputs()
    env = envelope()
    h = headroom(p, env, two_node)
    best = choose_R(h)
    choice = next(r for r in h["rows"] if r["R20_ohm"] == p["actuator.R20"] and r["v_bat"] == cv("v_bat_act_min"))
    R = choice["R20_ohm"]
    L = choice["L_H"]
    a = h["a_hot"]
    ripple_rows = []
    for f in (10e3, 20e3, 25e3, 40e3, 50e3, 100e3):
        for D in (0.3, 0.5, 0.8):
            rp, iav, tau = pwm_ripple(a * R, L, 3.7, D, f, h["r_ext_ohm"])
            ripple_rows.append({"f_pwm_kHz": f / 1e3, "D": D, "ripple_pp_mA": rp * 1e3, "i_avg_A": iav,
                                "pwm_levels_centre_aligned": cv("pwm_clock_hz") / (2 * f)})
    loop = current_loop(a * R, L)
    sense = sense_chain()
    ev = timeline()
    busy = {r: sum(d for rr, _, _, d in ev if rr == r) for r in {e[0] for e in ev}}
    powr = electronics_power()
    hold_I_design = 0.76 / (h["n"] * choice["Kf_N_per_A"])    # 50 deg, 1 N, mu 0.15 worst direction
    out = {
        "components": {k: {"value": v[0], "source": v[1]} for k, v in COMP.items()},
        "headroom": h,
        "chosen_winding": {**choice, "note": "design baseline = config actuator.R20 (DEC-012); ripple, current loop and hold current use it"},
        "winding_assessment": {"largest_R_meeting_criterion": best["R20_ohm"] if best else None,
                               "criterion": "at 3.3 V: static hold feasible at every thermally allowed envelope point and typical "
                                            "correction (9 Hz, 0.3 mm) at >= 99.9 %, each point at its own steady coil and magnet temperature",
                               "baseline_meets_criterion": bool(best and best["R20_ohm"] >= p["actuator.R20"])},
        "thermal_inputs": {"source": "results/thermal/thermal.json", "parameters_version": th_version, **two_node},
        "design_point_hold_current_A": hold_I_design,
        "sense_chain": sense,
        "pwm_ripple": ripple_rows,
        "current_loop": loop,
        "stage_period_busy_us": busy,
        "electronics_power": powr,
        "protection_timing_us": {"comparator_LMV331_prop": 1.0, "latch_and_gate": 0.02, "load_switch_off_with_QOD": 20.0,
                                 "note": "VERIFY each against datasheets; coil current then decays with tau = L/R through the bridge body diodes"},
    }
    meta = provenance.metadata("analytical calculation (datasheet-class values; VERIFY flags in components)", p=p)
    provenance.write_json(os.path.join(OUT, "drive_sense.json"), {"meta": meta, **out})
    figures(h, choice, ripple_rows, ev, env, p)
    print(f"Km20 {h['Km20']:.3f}  Km_hot {h['Km_hot']:.3f}  R_ext {h['r_ext_ohm']:.2f} ohm  thermal-OK {100*h['frac_thermal_ok']:.1f} %"
          f"  coil max {h['t_coil_max_in_envelope_C']:.1f} C  magnets max {h['t_magnet_max_in_envelope_C']:.1f} C")
    for r in h["rows"]:
        print(f"R {r['R20_ohm']:5.1f}  Vb {r['v_bat']}  V-ok|thermal static {100*r['frac_ok_within_thermal_static']:6.2f} % "
              f"(worst {r['worst_voltage_ratio_static']:.3f})  typical {100*r['frac_ok_within_thermal_typical_9Hz_0p3mm']:6.2f} %  "
              f"extreme {100*r['frac_ok_within_thermal_extreme']:6.2f} %  Imax|th {r['I_max_within_thermal_A']:.2f} A  bridge loss {100*r['bridge_loss_frac']:.0f} %")
    print("BASELINE", {k: round(v, 4) if isinstance(v, float) else v for k, v in choice.items()})
    print("largest R meeting the criterion:", best["R20_ohm"] if best else None)
    print("design-point hold current", round(hold_I_design, 3), "A")
    print("sense", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sense.items()})
    print("loop", {k: round(v, 3) for k, v in loop.items()})
    print("ripple @20k", [(r["D"], round(r["ripple_pp_mA"], 1)) for r in ripple_rows if r["f_pwm_kHz"] == 20])
    print("ripple @40k", [(r["D"], round(r["ripple_pp_mA"], 1)) for r in ripple_rows if r["f_pwm_kHz"] == 40])
    print("busy us", busy, "electronics mW", round(powr["total_mW_at_3V7"], 1))


if __name__ == "__main__":
    main()
