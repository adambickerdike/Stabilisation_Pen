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
    "t_coil_design_c": (85.0, "hot-coil design point (results/thermal: 85.5 C at design load)"),
    "t_amb_c": (25.0, "config thermal.t_ambient"),
    "v_bat_act_min": (3.3, "config electrical.v_bat_min"),
    "p_cu_allow_w": (0.455, "results/thermal/thermal.json allowable average copper loss, moving coil"),
    "v_tip_stage_max": (0.05, "m/s stage velocity relative to housing (tremor 0.3 mm @ 9 Hz ~ 17 mm/s, x3)"),
}


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


def headroom(p, env):
    n = p["stage.L2"] / p["stage.L1"]
    Km20 = p["actuator.Kf"] / math.sqrt(p["actuator.R20"])
    a = 1 + p["actuator.alpha_cu"] * (cv("t_coil_design_c") - 20.0)
    Km_hot = Km20 / math.sqrt(a)
    r_ext = cv("r_ds_on_hs_ls_ohm") * cv("r_ds_hot_factor") + cv("r_shunt_ohm") + cv("r_wiring_ohm")
    # thermal feasibility (independent of winding): direction-averaged continuous load
    P_th = (env["F_rms"] / (n * Km_hot)) ** 2
    therm_ok = P_th <= cv("p_cu_allow_w")
    rows = []
    for R in (2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 11.0):
        Kf = Km20 * math.sqrt(R)
        I = env["F_max"] / (n * Kf)                      # worst stroke direction, one axis carries it all
        v_emf = Kf * n * cv("v_tip_stage_max")
        for vb in (3.3, 3.7, 4.2):
            v_av = vb * cv("d_max") - 2 * I * cv("r_load_switch_ohm")
            V = I * (a * R + r_ext) + v_emf
            ok = V <= v_av
            rows.append({"R20_ohm": R, "Kf_N_per_A": Kf, "L_H": p["actuator.L"] * R / p["actuator.R20"],
                         "v_bat": vb, "frac_voltage_ok": float(ok.mean()),
                         "frac_voltage_ok_within_thermal": float(ok[therm_ok].mean()),
                         "I_p95_A": float(np.percentile(I[therm_ok], 95)),
                         "I_max_within_thermal_A": float(I[therm_ok].max()),
                         "bridge_loss_frac": float(r_ext / (a * R))})
    return {"n": n, "Km20": Km20, "Km_hot": Km_hot, "a_hot": a, "r_ext_ohm": r_ext,
            "frac_thermal_ok": float(therm_ok.mean()), "rows": rows}


def choose_R(h):
    """Largest winding resistance for which, at the minimum actuation voltage,
    every envelope point the thermal limit allows is also voltage-feasible."""
    cands = [r for r in h["rows"] if r["v_bat"] == cv("v_bat_act_min") and r["frac_voltage_ok_within_thermal"] >= 0.999]
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
    # --- headroom: feasible fraction vs winding resistance
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for j, vb in enumerate((3.3, 3.7, 4.2)):
        rr = [r for r in h["rows"] if r["v_bat"] == vb]
        xs = [r["R20_ohm"] for r in rr]
        ys = [100 * r["frac_voltage_ok_within_thermal"] for r in rr]
        ax.plot(xs, ys, color=plotstyle.SERIES[j], label=f"VBAT {vb} V")
        ax.plot(xs, ys, **plotstyle.marker_kw(plotstyle.SERIES[j]))
    ax.axvline(choice["R20_ohm"], color=plotstyle.MUTED, lw=1.0)
    ax.text(choice["R20_ohm"] + 0.15, 8, f"chosen {choice['R20_ohm']:g} ohm", color=plotstyle.INK2, fontsize=8.5)
    ax.set_xlabel("Coil resistance at 20 C (ohm), Km fixed")
    ax.set_ylabel("Voltage-feasible share of thermally allowed envelope (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Winding choice: the supply must not bind before the heat limit", loc="left", fontsize=10)
    ax.legend(loc="lower left", fontsize=8)
    plotstyle.stamp(fig, "analytical calculation", f"coil {cv('t_coil_design_c'):.0f} C, Km {h['Km20']:.3f} N/sqrtW, R_ext {h['r_ext_ohm']:.2f} ohm; thermal-OK share {100*h['frac_thermal_ok']:.0f} %")
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
    env = envelope()
    h = headroom(p, env)
    choice = choose_R(h)
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
        "chosen_winding": {**choice, "criterion": "largest R with all thermally-allowed envelope points voltage-feasible at 3.3 V, 85 C coil"},
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
    print(f"Km20 {h['Km20']:.3f}  Km_hot {h['Km_hot']:.3f}  R_ext {h['r_ext_ohm']:.2f} ohm  thermal-OK {100*h['frac_thermal_ok']:.1f} %")
    for r in h["rows"]:
        print(f"R {r['R20_ohm']:5.1f}  Vb {r['v_bat']}  V-ok {100*r['frac_voltage_ok']:5.1f} %  V-ok|thermal {100*r['frac_voltage_ok_within_thermal']:5.1f} %  "
              f"I95 {r['I_p95_A']:.2f} A  Imax|th {r['I_max_within_thermal_A']:.2f} A  bridge loss {100*r['bridge_loss_frac']:.0f} %")
    print("CHOSEN", {k: round(v, 4) if isinstance(v, float) else v for k, v in choice.items()})
    print("design-point hold current", round(hold_I_design, 3), "A")
    print("sense", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sense.items()})
    print("loop", {k: round(v, 3) for k, v in loop.items()})
    print("ripple @20k", [(r["D"], round(r["ripple_pp_mA"], 1)) for r in ripple_rows if r["f_pwm_kHz"] == 20])
    print("ripple @40k", [(r["D"], round(r["ripple_pp_mA"], 1)) for r in ripple_rows if r["f_pwm_kHz"] == 40])
    print("busy us", busy, "electronics mW", round(powr["total_mW_at_3V7"], 1))


if __name__ == "__main__":
    main()
