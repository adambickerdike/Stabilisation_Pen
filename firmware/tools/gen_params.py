#!/usr/bin/env python3
"""Generate firmware/include/params_gen.h (and params_gen.json) from the
project's sources of truth.

Evidence status of every generated constant: PROPOSED DESIGN / CALCULATED /
ASSUMED exactly as declared by its source (config/parameters.yaml `status`
fields, simulator design rules, electronics calculations).  Nothing generated
here is a measurement of hardware.

Sources (read-only):
  config/parameters.yaml             parameter values + provenance (via stabpen.params)
  sim/pensim/model.py                build_params(): packed parameter vector and the
                                     controller gains, computed EXACTLY as the simulator
                                     does (Kp = m_eq wc^2 - k_tip, Kd = 2 zeta m_eq wc,
                                     Ki = Kp wc ki_ratio, Kp_i = L wc_i, Ki_i = R wc_i,
                                     biquads from scipy.signal.butter, KF noise terms)
  results/sim/estimator_selection.json  frozen estimator parameters (balanced = default
                                     profile, assertive = alternative profile)
  results/electronics/drive_sense.json  sense chain, PWM, duty limit, design hold current
  electronics/gen/design_revA.py     divider/NTC/trip values (copied constants, cited)
  docs/icd.md                        ICD thresholds (sections 2, 5, 6)

The nominal scenario used for scenario-dependent quantities (gamma_acc) is
theta = config writing.tilt_deg, N0 = config writing.normal_force, phi = rho = 0.

Output is deterministic (no timestamps): regenerating from identical inputs
gives a byte-identical header.  Input digests are embedded instead.

Run from anywhere:  python3 firmware/tools/gen_params.py   (or: make -C firmware params)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys

sys.dont_write_bytecode = True          # never write __pycache__ outside firmware/
HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)
ROOT = os.path.dirname(FW)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(FW, "build", "numba_cache"))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sim.pensim import model  # noqa: E402
from sim.pensim.layout import IDX  # noqa: E402
from stabpen import params as sp  # noqa: E402

OUT_H = os.path.join(FW, "include", "params_gen.h")
OUT_J = os.path.join(FW, "include", "params_gen.json")
YAML = os.path.join(ROOT, "config", "parameters.yaml")
SEL = os.path.join(ROOT, "results", "sim", "estimator_selection.json")
DRV = os.path.join(ROOT, "results", "electronics", "drive_sense.json")
DESIGN = os.path.join(ROOT, "electronics", "gen", "design_revA.py")
MODEL_PY = os.path.join(ROOT, "sim", "pensim", "model.py")
CORE_PY = os.path.join(ROOT, "sim", "pensim", "core.py")
ICD = os.path.join(ROOT, "docs", "icd.md")

MIN_YAML_VERSION = (0, 4, 0)            # winding R20 6 ohm / 40 kHz / 0.1 ohm shunt (DEC-012)


def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def git_rev():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:  # pragma: no cover
        return "unknown"


class Emitter:
    def __init__(self):
        self.rows = []          # (section, name, value, ctype, unit, source)
        self.section = ""
        self.names = set()

    def sec(self, title):
        self.section = title

    def f(self, name, value, unit, source):
        self._add(name, float(value), "float", unit, source)

    def i(self, name, value, unit, source):
        if abs(value - round(value)) > 1e-9:
            raise ValueError(f"{name} = {value} is not an integer")
        self._add(name, int(round(value)), "int", unit, source)

    def s(self, name, value, source):
        self._add(name, str(value), "str", "", source)

    def _add(self, name, value, ctype, unit, source):
        if name in self.names:
            raise ValueError(f"duplicate constant {name}")
        if ctype == "float" and not math.isfinite(value):
            raise ValueError(f"{name} not finite")
        self.names.add(name)
        self.rows.append((self.section, name, value, ctype, unit, source))


def c_float(v):
    """float32 literal: 9 significant digits round-trip a float32 exactly."""
    f32 = float(np.float32(v))
    if f32 == 0.0:
        return "0.0f"
    s = f"{f32:.9g}"
    if "e" not in s and "." not in s:
        s += ".0"
    return s + "f"


def nominal_scenario(p):
    dt = 25e-6
    t = np.arange(4) * dt
    z2 = np.zeros((4, 2))
    return model.Scenario(t=t, pref=np.zeros((4, 3)), vref=np.zeros((4, 3)), fpush=np.zeros(4), dtrue=z2,
                          intended=z2.copy(), opt_ok=np.ones(4, np.uint8), theta_deg=float(p["writing.tilt_deg"]),
                          phi_deg=0.0, rho_deg=0.0, N0=float(p["writing.normal_force"]))


def kf_q(qj, qt, Ts):
    """Process-noise entries exactly as sim/pensim/core.py _kf_step()."""
    T2 = Ts * Ts; T3 = T2 * Ts; T4 = T3 * Ts; T5 = T4 * Ts
    return {"Q00": qj * T5 / 20.0, "Q01": qj * T4 / 8.0, "Q02": qj * T3 / 6.0, "Q11": qj * T3 / 3.0,
            "Q12": qj * T2 / 2.0, "Q22": qj * Ts, "QOSC": qt * Ts}


def main():
    p = sp.load(YAML)
    ver = tuple(int(x) for x in p.version().split("."))
    checks = []
    if ver < MIN_YAML_VERSION:
        raise SystemExit(f"config/parameters.yaml version {p.version()} < {'.'.join(map(str, MIN_YAML_VERSION))}: "
                         "the Rev A winding change (DEC-012) is not in the YAML yet; refusing to generate stale parameters.")
    sel = json.load(open(SEL))["results"]
    drv = json.load(open(DRV))
    comp = {k: v["value"] for k, v in drv["components"].items()}
    kf_bal = sel["kfosc"]["selected"]["params"]
    kf_asr = sel["kfosc"]["selected_assertive"]["params"]
    bpf = sel["bpf"]["selected"]["params"]
    bpf_asr = sel["bpf"]["selected_assertive"]["params"]
    scn = nominal_scenario(p)
    ctrl_bal = model.Controller(mode="kfosc", **kf_bal, **bpf)
    ctrl_asr = model.Controller(mode="kfosc", **kf_asr, **bpf_asr)
    P, info = model.build_params(scn, ctrl_bal)
    Pa, info_a = model.build_params(scn, ctrl_asr)

    def g(name, PP=P):
        return float(PP[IDX[name]])

    # every quantity not depending on the KF profile must agree between the two builds
    prof_keys = {"kf_qj", "kf_qt", "kf_w0", "f_gate", "bp_gain_comp"} | {f"bp{k}_{c}" for k in (1, 2) for c in ("b0", "b1", "b2", "a1", "a2")}
    for nm, ix in IDX.items():
        if nm in prof_keys:
            continue
        if not (P[ix] == Pa[ix]):
            raise SystemExit(f"profile builds differ in non-profile parameter {nm}")

    E = Emitter()
    src_bp = "sim/pensim/model.py build_params()"
    ctl = model.Controller()
    yml = "config/parameters.yaml"

    # ------------------------------------------------------------------ timing
    E.sec("Timing (ICD section 2)")
    Ts = info["Ts"]
    dt = g("dt")
    f_pwm = float(p["electrical.f_pwm"])
    f_cur = float(p["control.f_current"])
    f_stage = float(p["control.f_stage"])
    if abs(f_pwm - f_cur) > 0.5:
        raise SystemExit("current loop must run once per PWM period (f_current == f_pwm)")
    if abs(comp["f_pwm_hz"] - f_pwm) > 0.5:
        checks.append(f"drive_sense f_pwm_hz {comp['f_pwm_hz']} != yaml electrical.f_pwm {f_pwm}")
    E.f("F_PWM_HZ", f_pwm, "Hz", f"{yml} electrical.f_pwm ({p.leaf('electrical.f_pwm')['status']})")
    E.f("F_CURRENT_HZ", f_cur, "Hz", f"{yml} control.f_current")
    E.f("F_STAGE_HZ", f_stage, "Hz", f"{yml} control.f_stage (REQ-CTRL-001)")
    E.i("PWM_PER_STAGE", f_pwm / f_stage, "-", "derived f_pwm / f_stage (ICD s2: every 20 PWM periods)")
    E.f("TS_STAGE", Ts, "s", f"{src_bp}: Ts = stage_decim * dt")
    E.f("TS_CURRENT", 1.0 / f_cur, "s", "1 / f_current")
    E.i("CUR_DECIM_SIM", g("cur_decim"), "-", f"{src_bp}: cur_decim (sim steps of 25 us per current update; 1 = 40 kHz)")
    E.f("PWM_CLOCK_HZ", comp["pwm_clock_hz"], "Hz", "results/electronics/drive_sense.json components.pwm_clock_hz (nRF5340 PWM base clock)")
    E.i("PWM_COUNTERTOP", comp["pwm_clock_hz"] / (2.0 * f_pwm), "counts", "derived: centre-aligned up/down counter, 16 MHz / (2 x 40 kHz) = 200 levels (ICD s2)")
    E.f("F_ML_HZ", float(p["control.f_predictor"]), "Hz", f"{yml} control.f_predictor; ICD s2/s5")
    E.i("ML_DECIM", f_stage / float(p["control.f_predictor"]), "ticks", "derived f_stage / f_predictor (ICD s2: every 8 stage ticks)")
    E.f("F_STROKE_LOG_HZ", 200.0, "Hz", "docs/icd.md s2/s4.3 stroke sample rate")

    # ------------------------------------------------------------------ plant
    E.sec("Stage, lever and actuator (tip-equivalent; used by servo and tests)")
    red = info["reduction"]
    E.f("M_EQ", g("m_eq"), "kg", f"{src_bp}: Geometry.reduce() J_pivot/L1^2 (CAD Rev A masses; calculated)")
    E.f("K_TIP", g("k_tip"), "N/m", f"{yml} stage.k_tip ({p.leaf('stage.k_tip')['status']})")
    E.f("C_TIP", g("c_tip"), "N s/m", f"{src_bp}: 2 zeta_open sqrt(k_tip m_eq)")
    E.f("M_COUPLE", g("m_couple"), "kg", f"{src_bp}: Geometry.reduce() m_mov L_cm / L1")
    E.f("L1", g("L1"), "m", f"{yml} stage.L1")
    E.f("N_LEVER", g("n_lever"), "-", f"{src_bp}: L2 / L1 ({yml} stage.L2 / stage.L1)")
    E.f("Q_STOP", g("q_stop"), "m", f"{yml} stage.travel_tip_mech (mechanical stop radius at the tip)")
    E.f("F_PRE", g("F_pre"), "N", f"{yml} stage.axial_preload")
    E.f("K_AX", g("k_ax"), "N/m", f"{yml} stage.axial_k")
    E.f("S_MAX", g("s_max"), "m", f"{yml} stage.axial_travel")
    E.f("KF20", g("Kf"), "N/A", f"{yml} actuator.Kf (per axis, at the actuator; {p.leaf('actuator.Kf')['status']})")
    E.f("R20", g("R20"), "ohm", f"{yml} actuator.R20 (DEC-012)")
    E.f("L_COIL", g("Lc"), "H", f"{yml} actuator.L")
    E.f("R_BRIDGE", g("r_bridge"), "ohm", f"{yml} electrical.r_bridge (DRV8212P HS+LS hot; VERIFY)")
    E.f("R_SHUNT", g("r_shunt"), "ohm", f"{yml} electrical.r_shunt")
    E.f("I_MAX", g("i_max"), "A", f"{yml} actuator.i_max (software limit per axis)")
    E.f("I_TRIP_HW", float(p["actuator.i_trip"]), "A", f"{yml} actuator.i_trip (hardware window comparator + latch)")
    E.f("ALPHA_CU", g("alpha_cu"), "1/K", f"{yml} actuator.alpha_cu")
    E.f("ALPHA_B", g("alpha_B"), "1/K", f"{src_bp}: alpha_B default (NdFeB Br tempco, assumed)")
    E.f("RTH_COIL", g("Rth"), "K/W", f"{yml} actuator.Rth_coil_amb ({p.leaf('actuator.Rth_coil_amb')['status']}; see README discrepancy D6)")
    E.f("CTH_COIL", g("Cth"), "J/K", f"{yml} actuator.Cth_coil")
    E.f("T_AMB", g("T_amb"), "degC", f"{yml} thermal.t_ambient")
    E.f("V_BAT_NOM", g("V_bus"), "V", f"{yml} electrical.v_bat_nom")
    E.f("V_BAT_MIN", float(p["electrical.v_bat_min"]), "V", f"{yml} electrical.v_bat_min (actuation cut-off)")

    # ------------------------------------------------------------------ current loop
    E.sec("Current loop (40 kHz PI per axis)")
    E.f("CUR_BW_HZ", ctl.cur_bw, "Hz", "sim/pensim/model.py Controller.cur_bw (yaml control.current_bw = %g)" % float(p["control.current_bw"]))
    if abs(ctl.cur_bw - float(p["control.current_bw"])) > 1e-9:
        checks.append("model.Controller.cur_bw != yaml control.current_bw")
    E.f("KP_I", g("Kp_i"), "V/A", f"{src_bp}: Kp_i = L wc_i")
    E.f("KI_I", g("Ki_i"), "V/(A s)", f"{src_bp}: Ki_i = (R20 + r_bridge + r_shunt) wc_i")
    E.f("R_LOOP_FF", g("R20") + g("r_bridge") + g("r_shunt"), "ohm", f"{src_bp}: Rhat used for the R*i_ref voltage feedforward (at 20 C)")
    E.f("CUR_R_FF", 0.0, "-", "firmware default 0: PI with pole-zero cancellation as designed in electronics/calcs/drive_sense.py; "
        "the simulator adds R*i_ref (= 1), which overshoots 55 % with the 1-period sample-to-PWM delay (README D10)")
    E.f("DUTY_MAX", comp["d_max"], "-", "results/electronics/drive_sense.json components.d_max (sampling window)")
    E.f("R_LOAD_SWITCH", comp["r_load_switch_ohm"], "ohm", "drive_sense.json components.r_load_switch_ohm (TPS22917, shared; VERIFY)")
    E.f("DUTY_HEADROOM", 0.95, "-", "docs/icd.md s6 fault bit 6 threshold")

    # ------------------------------------------------------------------ sense chain
    E.sec("Analogue sense chain (electronics/gen/design_revA.py, drive_sense.json)")
    v_per_a = comp["ina_gain"] * comp["r_shunt_ohm"]
    fs_diff = comp["adc_fs_diff_v"]
    bits = int(comp["adc_bits"])
    E.f("ISNS_V_PER_A", v_per_a, "V/A", "INA241A1 G = 10 x 0.1 ohm shunt (drive_sense sense_chain.sensitivity_V_per_A)")
    E.f("ISNS_VREF", comp["vref_v"], "V", "REF3012 1.25 V (INA241 REF and SAADC negative input AIN4)")
    E.f("SAADC_DIFF_FS_V", fs_diff, "V", "SAADC gain 1/2, internal 0.6 V reference, differential (drive_sense adc_fs_diff_v)")
    E.i("SAADC_BITS", bits, "bit", "SAADC 12-bit mode (drive_sense adc_bits)")
    E.f("ISNS_COUNTS_PER_A", (2 ** (bits - 1)) / fs_diff * v_per_a, "count/A", "derived: 2^(bits-1)/FS x V/A (differential result is signed)")
    E.f("ISNS_OFFSET_MAX_A", 0.025, "A", "proposed plausibility bound on the pen-up offset (drive_sense offset_mA_uncal 0.25 mA + ADC offset; generous)")
    E.i("ISNS_OFFSET_SAMPLES", 32, "samples", "proposed: centre+edge samples averaged during a coast window")
    E.f("VBAT_DIV", 0.5, "-", "design_revA.py R9/R10 470k/470k (VBAT_SENSE = VBAT/2)")
    E.f("SAADC_SE_FS_V", 3.6, "V", "SAADC gain 1/6 x internal 0.6 V reference (single-ended; VERIFY)")
    E.f("NTC_R25", 10000.0, "ohm", "design_revA.py sheet_sensing note: NTC 10k")
    E.f("NTC_BETA", 3435.0, "K", "design_revA.py sheet_sensing note: B25/85 ~3435 K (VERIFY part)")
    E.f("NTC_R_PULLUP", 10000.0, "ohm", "design_revA.py R14 10k to +3V0A (ratiometric read, REFSEL VDD/4, gain 1/4)")
    E.f("I_HOLD_DESIGN", drv["design_point_hold_current_A"], "A", "drive_sense.json design_point_hold_current_A (50 deg, 1 N, mu 0.15 worst direction)")
    E.f("R_EXT_HOT", drv["headroom"]["r_ext_ohm"], "ohm", "drive_sense.json headroom.r_ext_ohm (bridge hot + shunt + wiring)")
    E.f("T_COIL_DESIGN", comp["t_coil_design_c"], "degC", "drive_sense.json components.t_coil_design_c")

    # ------------------------------------------------------------------ servo
    E.sec("Stage position servo (2 kHz)")
    E.f("POS_BW_HZ", ctl.pos_bw, "Hz", "sim/pensim/model.py Controller.pos_bw (yaml control.pos_bw = %g)" % float(p["control.pos_bw"]))
    if abs(ctl.pos_bw - float(p["control.pos_bw"])) > 1e-9:
        checks.append("model.Controller.pos_bw != yaml control.pos_bw")
    E.f("ZETA", ctl.zeta, "-", "model.Controller.zeta")
    E.f("KP", g("Kp"), "N/m", f"{src_bp}: Kp = m_eq wc^2 - k_tip")
    E.f("KD", g("Kd"), "N s/m", f"{src_bp}: Kd = 2 zeta m_eq wc")
    E.f("KI", g("Ki"), "N/(m s)", f"{src_bp}: Ki = Kp wc ki_ratio")
    E.f("D_FILT_HZ", g("d_filt"), "Hz", f"{src_bp}: d_filt = d_filt_ratio pos_bw")
    E.f("ALPHA_D", 1.0 - math.exp(-2.0 * math.pi * g("d_filt") * Ts), "-", "core.simulate(): alpha_d = 1 - exp(-2 pi d_filt Ts)")
    E.f("FF_REF", g("ff_ref"), "-", "model.Controller.ff_ref")
    E.f("FF_ACCEL", g("ff_accel"), "-", "model.Controller.ff_accel")
    E.f("FF_CONTACT", g("ff_contact"), "-", "model.Controller.ff_contact = 0 (DEC-011: contact feedforward disabled by default; bench option)")
    E.f("FFC_FC_HZ", g("ffc_fc"), "Hz", "model.Controller.ff_contact_fc (2nd-order Butterworth, DEC-011)")
    for nm in ("b0", "b1", "b2", "a1", "a2"):
        E.f(f"FFC_{nm.upper()}", g(f"ffc_{nm}"), "-", f"{src_bp}: scipy.signal.butter(2, fc, fs=f_stage) sos[0] ({nm})")

    # ------------------------------------------------------------------ authority, limits
    E.sec("Authority, Jacobian and limits")
    E.f("G_ASSIST", g("g_assist"), "-", "model.Controller.g_assist")
    E.f("Q_LIM", g("q_lim"), "m", "model.Controller.q_lim (= yaml stage.travel_tip_ctrl %g)" % float(p["stage.travel_tip_ctrl"]))
    if abs(g("q_lim") - float(p["stage.travel_tip_ctrl"])) > 1e-12:
        checks.append("model.Controller.q_lim != yaml stage.travel_tip_ctrl")
    E.f("Q_TAPER", g("q_taper"), "m", "model.Controller.q_taper")
    E.f("SLEW", g("slew"), "m/s", "model.Controller.slew")
    E.f("AUTHORITY_TAU", g("authority_tau"), "s", "model.Controller.authority_tau")
    E.f("ALPHA_A", 1.0 - math.exp(-Ts / max(g("authority_tau"), 1e-6)), "-", "core.simulate(): alpha_a = 1 - exp(-Ts/authority_tau)")
    E.f("GAMMA_NOM", g("gamma_acc"), "-", f"{src_bp}: gamma = Kn sin^2(th)/(Kn sin^2(th) + k_ax) at the nominal theta (default CAL_USER gamma)")
    E.f("K_HAND_NORMAL", float(p["hand.normal_stiffness"]), "N/m", f"{yml} hand.normal_stiffness (gamma formula)")
    E.f("THETA_NOM", math.radians(float(p["writing.tilt_deg"])), "rad", f"{yml} writing.tilt_deg")
    E.f("KAPPA_S", g("kappa_s"), "-", f"{yml} stage.kappa_s via {src_bp} (DEC-007 rev.: 1 = refill slides in the carrier, lever arm L1 - s)")
    E.f("AXIAL_COMP", g("axial_comp"), "-", "model.Controller.axial_comp (off)")
    E.f("AXIAL_COMP_TAU", g("axial_comp_tau"), "s", "model.Controller.axial_comp_tau")
    E.f("AXIAL_COMP_MAX", 0.3e-3, "m", "core.simulate(): axial compensation magnitude clamp 0.3e-3")
    E.f("LAM_MIN", 0.5, "-", "core.simulate(): lam_hat = max(0.5, 1 - kappa s/L1)")
    E.f("CONTACT_DF", 0.02, "N", "core.simulate(): in_contact = F_ax > F_pre + 0.02")

    # ------------------------------------------------------------------ estimators
    E.sec("Estimators (profiles: BAL = estimator_selection selected, ASR = selected_assertive)")
    E.f("BP_DERIV_ALPHA", 0.2, "-", "core.simulate() mode 2: ybpd += 0.2 (yd - ybpd)")
    hor = g("horizon")
    E.f("HORIZON", hor, "s", f"{src_bp}: imu_delay + Ts/2 + servo_lag(0 with ff_ref) + 1/(2 pi cur_bw)")
    E.f("KF_R", g("kf_r"), "m^2", "model.Controller.kf_r")
    E.f("KF_RDAMP", g("kf_rdamp"), "-", f"{src_bp}: exp(-Ts/kf_tau_decay)")
    E.f("KF_RH", g("kf_rdamp") ** (hor / Ts), "-", "core.simulate(): rh = rdamp^(horizon/Ts) (constant)")
    E.f("KF_WGAIN", g("kf_wgain"), "-", f"{src_bp}: Ts/kf_tau_w")
    E.f("KF_WMIN", g("kf_wmin"), "rad/s", f"{src_bp}: 2 pi kf_wmin_hz")
    E.f("KF_WMAX", g("kf_wmax"), "rad/s", f"{src_bp}: 2 pi kf_wmax_hz")
    E.f("CONF_NIS_HI", g("conf_nis_hi"), "-", "model.Controller.conf_nis_hi")
    E.f("NIS_ALPHA", 0.01, "-", "core.simulate(): nis_f += 0.01 (0.5 nis_sum - nis_f)")
    E.f("KF_AMP_MIN", 2e-5, "m", "core.simulate(): frequency adaptation only if oscillator amplitude > 2e-5")
    E.f("KF_P0_POS", 1e-8, "m^2", "core.simulate(): reinit P diag")
    E.f("KF_P0_VEL", 1e-4, "(m/s)^2", "core.simulate(): reinit P diag")
    E.f("KF_P0_ACC", 1e-2, "(m/s^2)^2", "core.simulate(): reinit P diag")
    E.f("KF_P0_OSC", 1e-7, "m^2", "core.simulate(): reinit P diag")
    E.f("KF_P_INIT", 1e-6, "-", "core.simulate(): initial P = 1e-6 I (before first reinit)")
    E.f("F_GATE_WIDTH", g("f_gate_width"), "Hz", "model.Controller.f_gate_width")
    for tag, PP, kfp, key in (("BAL", P, kf_bal, "selected"), ("ASR", Pa, kf_asr, "selected_assertive")):
        src = f"results/sim/estimator_selection.json kfosc.{key}"
        E.f(f"{tag}_KF_QJ", g("kf_qj", PP), "m^2/s^5", f"{src} kf_qj={kfp['kf_qj']}")
        E.f(f"{tag}_KF_QT", g("kf_qt", PP), "m^2/s", f"{src} kf_qt={kfp['kf_qt']}")
        E.f(f"{tag}_KF_W0", g("kf_w0", PP), "rad/s", f"{src} kf_w0_hz={kfp['kf_w0_hz']}")
        E.f(f"{tag}_F_GATE", g("f_gate", PP), "Hz", f"{src} f_gate={kfp['f_gate']} (default CAL_USER f_gate)")
        for qn, qv in kf_q(g("kf_qj", PP), g("kf_qt", PP), Ts).items():
            E.f(f"{tag}_KF_{qn}", qv, "SI", "core._kf_step(): Q entries precomputed in double precision")
    for tag, PP, bp, key in (("BAL", P, bpf, "selected"), ("ASR", Pa, bpf_asr, "selected_assertive")):
        src = f"results/sim/estimator_selection.json bpf.{key}"
        for nm in ("b0", "b1", "b2", "a1", "a2"):
            E.f(f"{tag}_BP1_{nm.upper()}", g(f"bp1_{nm}", PP), "-", f"{src_bp}: butter(2, bp_lo={bp['bp_lo']} Hz, high) sos ({nm}); {src}")
        for nm in ("b0", "b1", "b2", "a1", "a2"):
            E.f(f"{tag}_BP2_{nm.upper()}", g(f"bp2_{nm}", PP), "-", f"{src_bp}: butter(2, bp_hi={bp['bp_hi']} Hz, low) sos ({nm}); {src}")
        E.f(f"{tag}_BP_GAIN_COMP", g("bp_gain_comp", PP), "-", f"{src_bp}: 1/|H(bp_tune_hz={bp['bp_tune_hz']})|; {src}")

    # realised disturbance for the ML a-posteriori check (ICD s5 v1.1 rule 4)
    from scipy import signal as sps
    for tag, kind, fc in (("MLG_BP1", "high", 3.0), ("MLG_BP2", "low", 15.0)):
        b0, b1, b2, _a0, a1, a2 = sps.butter(2, fc, btype=kind, fs=1.0 / Ts, output="sos")[0]
        for nm, v in zip(("B0", "B1", "B2", "A1", "A2"), (b0, b1, b2, a1, a2)):
            E.f(f"{tag}_{nm}", v, "-", f"docs/icd.md s5 v1.1: realised disturbance band-pass 3-15 Hz; scipy butter(2, {fc:g} Hz, {kind}, fs=2 kHz)")

    # ------------------------------------------------------------------ sensing and fusion
    E.sec("Sensing and housing-position fusion")
    od = int(g("opt_delay")); idl = int(g("imu_delay")); sdec = int(g("stage_decim"))
    E.f("HALL_ICT_COMP", g("hall_ict_comp"), "m/A", f"{yml} sensing.hall_i_crosstalk_tip (sim compensation; firmware uses CAL_HALL T/A)")
    E.f("HALL_DELAY", float(p["sensing.hall_delay"]), "s", f"{yml} sensing.hall_delay")
    E.f("OPT_DELAY", float(p["sensing.opt_delay"]), "s", f"{yml} sensing.opt_delay")
    E.f("IMU_DELAY", float(p["sensing.imu_delay"]), "s", f"{yml} sensing.imu_delay")
    E.i("FUSION_LAG_TICKS", max(0, (od - idl) // sdec), "ticks", "core.simulate(): lag_t = max(0, (opt_delay - imu_delay) // stage_decim) in sim steps")
    E.f("IMU_LEAK_TAU", 0.5, "s", "core.simulate(): vimu *= (1 - dti/0.5) leaky velocity")
    E.f("IMU_RATE_HZ", float(p["sensing.imu_rate"]), "Hz", f"{yml} sensing.imu_rate (ICD s2 says 7.68 kHz ODR; README D8)")
    E.f("OPT_RATE_HZ", float(p["sensing.opt_rate"]), "Hz", f"{yml} sensing.opt_rate (ICD s2 says 2 kHz burst; README D8)")
    E.f("OPT_LIFT_MAX", 0.8e-3, "m", "model.build_params default sensing.opt_lift_max")
    E.i("FUSION_RING", 1024, "ticks", "core.simulate(): rb_pimu length")

    # ------------------------------------------------------------------ safety / ICD thresholds
    E.sec("Safety thresholds (docs/icd.md s5, s6; requirements; proposed values marked)")
    E.f("HEADROOM_TIME", 0.050, "s", "docs/icd.md s6 fault bit 6: duty > 0.95 for > 50 ms")
    E.f("OPT_INVALID_TIME", 0.300, "s", "docs/icd.md s6 fault bit 4: optical invalid > 300 ms")
    E.f("HALL_DETECT_BUDGET", 0.005, "s", "docs/icd.md s6: frozen Hall detected within 5 ms")
    E.i("HALL_STUCK_TICKS", 8, "ticks", "proposed: 8 bit-identical x/y/z readings (4 ms < 5 ms budget); needs >= 1 LSB noise (VERIFY EXP-B04)")
    E.f("HALL_JUMP_MAX", 100e-6, "m", "proposed: |second difference| residual bound (physical accel <= ~330 m/s^2 -> 83 um/tick^2)")
    E.f("HALL_RANGE_MARGIN", 50e-6, "m", "proposed: |q| > q_stop + margin is implausible")
    E.f("PENUP_TIMEOUT", 5.0, "s", "docs/icd.md s6: soft-fault shutdown waits for pen-up, timeout 5 s")
    E.f("RAMP_DOWN_TIME", 0.030, "s", "REQ-SAF-004: ramp actuator current down over >= 30 ms")
    E.f("VBAT_RECOVER", 3.45, "V", "proposed: low-battery clear threshold (hysteresis)")
    E.f("VBAT_DEBOUNCE", 0.200, "s", "proposed: low-battery debounce")
    E.f("VBAT_LPF_TAU", 0.050, "s", "proposed: VBAT measurement low-pass")
    E.f("T_COIL_LIMIT", 120.0, "degC", "REQ-THM-002 coil hot-spot limit")
    E.f("T_DERATE_START", 100.0, "degC", "proposed: authority cap starts falling")
    E.f("T_FAULT", 115.0, "degC", "proposed: over-temperature fault (bit 2), 5 degC margin for observer error")
    E.f("T_RECOVER", 90.0, "degC", "proposed: over-temperature clear threshold")
    E.f("T_NTC_GAIN", 0.02, "-", "proposed: NTC relaxation gain per 100 Hz observer update (both coils idle)")
    E.f("T_RES_GAIN", 0.05, "-", "proposed: resistance-thermometry gain per valid 100 Hz observer update")
    E.f("R_EST_I_MIN", 0.10, "A", "proposed: minimum |I| for resistance estimate")
    E.f("R_EST_DI_MAX", 0.02, "A", "proposed: max current change over a tick for 'steady'")
    E.f("OC_CLEAR_RETRIES", 3.0, "-", "proposed: latch clear attempts before the fault is permanent")
    E.f("ML_RATE_MAX", 0.050, "m/s", "docs/icd.md s5 v1.1 rule 3: slew-limit d_hat at 50 mm/s")
    E.f("ML_HORIZON", 0.006, "s", "docs/icd.md s5 v1.1: h = 6 ms after the acquisition time of the newest sample")
    E.i("ML_WINDOW", 64, "samples", "docs/icd.md s5 v1.1: W = 64 x (dx, dy) at 250 Hz (f_est dropped)")
    E.f("ML_APOST_WINDOW", 0.200, "s", "docs/icd.md s5 v1.1 rule 4: running RMS over 200 ms")
    E.f("ML_FALLBACK_HOLD", 1.0, "s", "docs/icd.md s5 v1.1 rule 4: fall back to the Kalman estimate for >= 1 s")
    E.f("ML_REAL_SETTLE", 0.300, "s", "proposed: a-posteriori evaluation suspended 300 ms after the realised-disturbance band-pass is reset")
    E.f("ML_STALE_TIME", 0.008, "s", "proposed: ML output older than 2 predictor periods is expired (REQ-SAF-003)")
    E.f("ML_FADE_TIME", 0.020, "s", "REQ-SAF-003: fall back smoothly within 20 ms")
    E.i("ML_TRIP_COUNT", 5, "trips", "proposed: fault bit 8 when > 5 guard trips within ML_TRIP_WINDOW")
    E.f("ML_TRIP_WINDOW", 10.0, "s", "proposed")
    E.f("PENUP_DEBOUNCE", 0.020, "s", "proposed: contact must be absent 20 ms to declare pen-up")

    # ------------------------------------------------------------------ write
    meta = {
        "generator": "firmware/tools/gen_params.py",
        "yaml_version": p.version(),
        "yaml_sha16": sha16(YAML),
        "estimator_selection_sha16": sha16(SEL),
        "drive_sense_sha16": sha16(DRV),
        "design_revA_sha16": sha16(DESIGN),
        "model_py_sha16": sha16(MODEL_PY),
        "core_py_sha16": sha16(CORE_PY),
        "icd_sha16": sha16(ICD),
        "model_version": info["model_version"],
        "git_head": git_rev(),
        "nominal_theta_deg": float(p["writing.tilt_deg"]),
        "nominal_N0": float(p["writing.normal_force"]),
        "evidence_status": "proposed design / calculated / assumed values; no hardware measurement",
    }
    lines = []
    lines.append("/* AUTO-GENERATED by firmware/tools/gen_params.py -- DO NOT EDIT.")
    lines.append(" * Regenerate: make -C firmware params   (after config/parameters.yaml changes)")
    lines.append(" * Evidence status: PROPOSED DESIGN. Every value is calculated, assumed or copied")
    lines.append(" * from a design file as cited; none is a measurement of Rev A hardware.")
    for k, v in meta.items():
        lines.append(f" *   {k}: {v}")
    lines.append(" */")
    lines.append("#ifndef PEN_PARAMS_GEN_H")
    lines.append("#define PEN_PARAMS_GEN_H")
    lines.append("")
    lines.append(f'#define PEN_PARAMS_YAML_VERSION "{meta["yaml_version"]}"')
    lines.append(f'#define PEN_PARAMS_YAML_SHA16 "{meta["yaml_sha16"]}"')
    lines.append(f'#define PEN_PARAMS_MODEL_VERSION "{meta["model_version"]}"')
    ymaj, ymin, ypat = ver
    lines.append(f"#define PEN_PARAMS_YAML_VERSION_NUM ({ymaj * 10000 + ymin * 100 + ypat}u)")
    lines.append(f'#define PEN_PARAMS_SEL_SHA16 "{meta["estimator_selection_sha16"]}"')
    lines.append(f'#define PEN_PARAMS_DRV_SHA16 "{meta["drive_sense_sha16"]}"')
    lines.append(f'#define PEN_PARAMS_MODEL_SHA16 "{meta["model_py_sha16"]}"')
    lines.append(f'#define PEN_PARAMS_CORE_SHA16 "{meta["core_py_sha16"]}"')
    sec = None
    for section, name, value, ctype, unit, source in E.rows:
        if section != sec:
            lines.append("")
            lines.append(f"/* ---- {section} ---- */")
            sec = section
        if ctype == "float":
            val = c_float(value)
        elif ctype == "int":
            val = f"{value}"
        else:
            val = f'"{value}"'
        lines.append(f"#define PEN_{name:<22s} ({val}) /* {unit}; {source} */")
    lines.append("")
    lines.append("#endif /* PEN_PARAMS_GEN_H */")
    txt = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(OUT_H), exist_ok=True)
    with open(OUT_H, "w") as f:
        f.write(txt)
    jrows = [{"section": s, "name": "PEN_" + n, "value": v, "type": t, "unit": u, "source": src}
             for s, n, v, t, u, src in E.rows]
    with open(OUT_J, "w") as f:
        json.dump({"meta": meta, "checks": checks, "constants": jrows}, f, indent=1)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT_H, ROOT)} ({len(E.rows)} constants) from yaml {p.version()} [{meta['yaml_sha16']}]")
    for c in checks:
        print("CHECK:", c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
