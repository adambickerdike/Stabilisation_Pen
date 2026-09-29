"""Uncertainty budgets (JCGM 100 / GUM) and decision rules (JCGM 106), as bench_protocols.md section 0.5.

Every budget line carries its value, distribution and source label (MFR + ledger id,
ASSUMPTION, CALC). Budgets here are CALCULATIONS for the proposed rigs; they are
replaced by the measured budgets of each record (check standards, repeatability).

Decision rule: simple acceptance when TUR = tolerance half-width / U >= 4, otherwise guarded
acceptance (pass only if the measured value +- U lies inside the limit). Safety criteria
always use guarded acceptance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Line:
    name: str
    value: float          # half-width (rect), standard uncertainty (normal) or +-bound (u-shape)
    kind: str             # "rect", "normal", "ushape", "triangular"
    unit: str
    source: str

    @property
    def u(self) -> float:
        if self.kind == "rect":
            return abs(self.value) / math.sqrt(3)
        if self.kind == "triangular":
            return abs(self.value) / math.sqrt(6)
        if self.kind == "ushape":
            return abs(self.value) / math.sqrt(2)
        return abs(self.value)


@dataclass
class Budget:
    measurand: str
    unit: str
    lines: List[Line] = field(default_factory=list)
    k: float = 2.0
    note: str = ""

    def add(self, name, value, kind, source, unit=None):
        self.lines.append(Line(name, float(value), kind, unit or self.unit, source))
        return self

    @property
    def u(self) -> float:
        return math.sqrt(sum(l.u ** 2 for l in self.lines))

    @property
    def U(self) -> float:
        return self.k * self.u

    def dominant(self) -> str:
        return max(self.lines, key=lambda l: l.u).name if self.lines else ""

    def as_dict(self) -> Dict:
        return {"measurand": self.measurand, "unit": self.unit, "k": self.k, "u": self.u, "U": self.U,
                "dominant": self.dominant(), "note": self.note,
                "lines": [{"name": l.name, "value": l.value, "distribution": l.kind, "u": l.u, "unit": l.unit,
                           "source": l.source} for l in self.lines]}


def tur(tolerance_halfwidth: float, U: float) -> float:
    return float("inf") if U <= 0 else abs(tolerance_halfwidth) / U


def decide(value: float, limit: float, direction: str, U: float, tolerance_halfwidth: float = None,
           safety: bool = False) -> Dict:
    """Verdict for one criterion. direction: '<=' or '>='. tolerance_halfwidth defaults to the
    distance of the limit from the value (bench_protocols.md section 0.5)."""
    tol = abs(limit - value) if tolerance_halfwidth is None else tolerance_halfwidth
    t = tur(tol, U)
    rule = "guarded" if (safety or t < 4) else "simple"
    if direction == "<=":
        ok_simple = value <= limit
        ok_guard = value + U <= limit
        fail_guard = value - U > limit
    elif direction == ">=":
        ok_simple = value >= limit
        ok_guard = value - U >= limit
        fail_guard = value + U < limit
    else:
        raise ValueError(direction)
    if rule == "simple":
        verdict = "pass" if ok_simple else "fail"
    else:
        verdict = "pass" if ok_guard else ("fail" if fail_guard else "inconclusive")
    return {"value": value, "limit": limit, "direction": direction, "U": U, "TUR": t, "rule": rule,
            "verdict": verdict}


# ---------------------------------------------------------------------------------------
# Budgets for the proposed rigs (CALC). Sources: ledger ids in results/rig/evidence_rows.csv
# (AMF-220...239, OPT-85...94) or docs/evidence.csv; ASSUMPTION where no source was opened.
# ---------------------------------------------------------------------------------------
def axial_force_budget(fs_N=1.0, window_s=0.5, adc_rate=1000.0) -> Budget:
    """Axial refill force F_c from a FUTEK LSB200 (1 N, 2 mV/V) in series with the refill,
    read by the ADS131M08 at gain 128, after an in-situ dead-weight calibration."""
    ro_mV = 2.0 * 3.3                       # 2 mV/V (MFR AMF-225) x 3.3 V excitation (PROPOSED)
    noise_uV = 0.77                         # 1 kSPS, gain 128 (MFR AMF-221, Table 7-1)
    n = max(1, int(window_s * adc_rate))
    b = Budget("axial refill force F_c (R9 cartridge)", "mN",
               note="after in-situ dead-weight calibration at the test angle; flexure-guide force corrected")
    b.add("hysteresis +-0.1 % RO", 0.001 * fs_N * 1e3, "rect", "MFR AMF-225 (FUTEK LSB200 drawing FI1455-B)")
    b.add("non-repeatability +-0.05 % RO", 0.0005 * fs_N * 1e3, "rect", "MFR AMF-225")
    b.add("residual non-linearity after 5-point calibration", 0.0003 * fs_N * 1e3, "rect",
          "ASSUMPTION (30 % of the +-0.1 % RO spec left after a 2nd-order fit)")
    b.add("zero shift, +-1 K during a run (0.018 % RO/K)", 0.00018 * fs_N * 1e3, "rect", "MFR AMF-225")
    b.add("ADC noise averaged over the window", noise_uV / (ro_mV * 1e3) * fs_N * 1e3 / math.sqrt(n), "normal",
          "MFR AMF-221 (ADS131M04/M08 Table 7-1) / CALC")
    b.add("flexure-guide force correction k_g*dx (40 N/m +-5 %, dx <= 0.5 mm)", 40 * 0.5e-3 * 0.05 * 1e3,
          "rect", "PROPOSED DESIGN / ASSUMPTION (k_g calibrated to 5 %)")
    b.add("dead-weight standard (class M1, 5-50 g)", 0.02, "rect", "ASSUMPTION (OIML class M1 tolerance)")
    b.add("inertia of refill+holder (6 g) at <= 0.1 m/s^2 in steady strokes", 6e-3 * 0.1 * 1e3, "rect", "CALC")
    return b


def plate_force_budget(fs_N=2.0, axis="normal") -> Budget:
    """Paper-normal (or tangential) force from an ME K3D40 3-axis sensor under the platen,
    after in-situ calibration with dead weights at 9 positions (matrix + position correction)."""
    b = Budget(f"{axis} force on the paper (R9 plate, K3D40 +-{fs_N:g} N)", "mN",
               note="3x3 matrix and position correction fitted in situ; residuals replace these lines once measured")
    b.add("relative linearity error 0.2 % FS (half left after calibration)", 0.001 * fs_N * 1e3, "rect",
          "MFR AMF-224 (K3D40 data sheet, 5 Oct 2016) / ASSUMPTION (half removed)")
    b.add("zero-signal hysteresis 0.1 % FS", 0.001 * fs_N * 1e3, "rect", "MFR AMF-224")
    b.add("creep 0.05 % FS", 0.0005 * fs_N * 1e3, "rect", "MFR AMF-224")
    b.add("zero drift 0.05 % FS/K, +-0.5 K between zeroings", 0.00025 * fs_N * 1e3, "rect", "MFR AMF-224")
    b.add("eccentric load 0.5 % FS/100 mm, +-30 mm, 80 % corrected", 0.2 * 0.005 * 0.3 * fs_N * 1e3, "rect",
          "MFR AMF-224 / ASSUMPTION (position correction removes 80 %)")
    if axis != "normal":
        b.add("crosstalk z->x/y 1 % FS, 90 % removed by the matrix", 0.1 * 0.01 * fs_N * 1e3, "rect",
              "MFR AMF-224 / ASSUMPTION (matrix removes 90 %)")
    b.add("ADC noise (1 s average)", 0.05, "normal", "CALC from MFR AMF-221")
    return b


def page_truth_budget(kind="zaber") -> Budget:
    """Ground truth for one 10 ms page-sensor window (displacement difference of two positions)."""
    if kind == "zaber":
        b = Budget("truth displacement over a 10 ms window (2 x Zaber X-LDM110C)", "um")
        b.add("encoder count 1 nm, two endpoints", 0.001 * math.sqrt(2), "rect", "MFR AMF-229")
        b.add("accuracy 1 um over 110 mm (local slope over <= 2 mm)", 1.0 * 2 / 110, "rect", "MFR AMF-229 / CALC")
        b.add("repeatability < 0.08 um", 0.08, "rect", "MFR AMF-229")
        b.add("time-stamp jitter x speed (1 us x 100 mm/s)", 0.1, "rect", "ASSUMPTION (DAQ ISR jitter 1 us)")
        b.add("Abbe/yaw error of the stacked stages over the sensor offset", 0.3, "rect", "ASSUMPTION")
    elif kind == "lm13":
        b = Budget("truth displacement over a 10 ms window (CoreXY + 2 x RLS LM13)", "um")
        b.add("resolution 0.244 um, two endpoints", 0.244 / 2 * math.sqrt(2), "rect", "MFR OPT-89 (LM13 13B)")
        b.add("sub-divisional error (not stated in the data sheet)", 1.0, "rect", "ASSUMPTION (not in MFR OPT-89)")
        b.add("hysteresis < 4 um, only in windows with a reversal (1 in 5 at 8 Hz tremor)", 4.0 * math.sqrt(0.2),
              "rect", "MFR OPT-89 / CALC (fraction of windows)")
        b.add("belt/carriage flex between encoder and sensor (Abbe)", 1.0, "rect", "ASSUMPTION")
        b.add("time-stamp jitter x speed", 0.1, "rect", "ASSUMPTION")
    elif kind == "camera":
        b = Budget("truth displacement over a 10 ms window (strobed global-shutter camera, 9.4 um/px)", "um")
        b.add("dot centroid noise 0.05 px, two frames", 0.05 * 9.4 * math.sqrt(2), "normal",
              "ASSUMPTION (to be measured on a static target)")
        b.add("lens distortion after a dot-grid calibration 0.1 px", 0.1 * 9.4, "rect", "ASSUMPTION")
        b.add("motion blur residual (50 us strobe at 100 mm/s = 5 um streak)", 1.0, "rect", "CALC / ASSUMPTION")
        b.add("scale (grid pitch 1 um in 10 mm) over 1 mm", 0.1, "rect", "ASSUMPTION")
    else:
        raise ValueError(kind)
    return b


def stage_truth_budget() -> Budget:
    """Housing disturbance position from an RLS LM13 on the R13 flexure stage."""
    b = Budget("housing position (R13 disturbance stage, LM13)", "um")
    b.add("resolution 0.244 um", 0.122, "rect", "MFR OPT-89")
    b.add("hysteresis < 4 um at reversals", 4.0, "rect", "MFR OPT-89")
    b.add("sub-divisional error", 1.0, "rect", "ASSUMPTION")
    b.add("Abbe offset x flexure yaw (5 mm x 50 urad)", 0.25, "rect", "ASSUMPTION / CALC")
    return b


def ink_path_budget() -> Budget:
    """Ink centreline position from a 4800 dpi scan (R3), within a 25 mm field."""
    b = Budget("ink centreline position (Epson V850 Pro at 4800 dpi, 5.3 um/px)", "um")
    b.add("ridge-fit noise per 20 um step (0.2 px)", 0.2 * 5.3, "normal", "ASSUMPTION")
    b.add("residual distortion after grid correction", 1.5, "rect", "ASSUMPTION (R3 requirement <= 5 um k=2)")
    b.add("paper cockle/shrinkage over 25 mm between writing and scan", 1.0, "rect", "ASSUMPTION")
    b.add("fiducial registration", 1.0, "rect", "ASSUMPTION")
    return b


def sync_budget() -> Budget:
    b = Budget("time alignment DAQ <-> device under test", "us")
    b.add("device edge-capture latency and jitter", 5.0, "rect", "ASSUMPTION (GPIO interrupt on a Cortex-M)")
    b.add("affine clock-fit residual over 10 min", 3.0, "normal", "CALC (rig.sync on synthetic 20 ppm drift)")
    b.add("DAQ ISR jitter", 1.0, "rect", "ASSUMPTION")
    return b


def km_budget(Kf_nominal=1.04, I_A=0.5) -> Budget:
    """Force constant from +-I reversals at one grid point (R12)."""
    F = Kf_nominal * I_A
    b = Budget("force constant K_f at one grid point (R12, K3D40 +-10 N, reversal method)", "%")
    b.add("sensor gain after dead-weight calibration", 0.3, "rect", "ASSUMPTION (calibration residual)")
    b.add("hysteresis 0.1 % FS of 10 N on a +-F swing", 100 * 0.01 / (2 * F), "rect", "MFR AMF-224 / CALC")
    b.add("current: 0.1 % shunt read by the 24-bit ADC", 0.1, "rect", "ASSUMPTION (0.1 % shunt)")
    b.add("coil warming between +I and -I (K_f follows the magnets, not the coil)", 0.05, "rect", "CALC")
    b.add("position error 10 um on a 15 %/mm ripple slope", 0.15, "rect", "ASSUMPTION / CALC")
    return b


def thermal_budget() -> Budget:
    b = Budget("coil temperature by resistance (4-wire, alpha_cu 0.00393/K)", "K")
    b.add("R20 reference at 20.0 +- 0.5 C", 0.5, "rect", "PROTOCOL R4 bath band")
    b.add("resistance ratio (0.02 % of R)", 0.0002 / 0.00393, "rect", "ASSUMPTION (4-wire ratio)")
    b.add("alpha_cu tolerance (1 %) at a 60 K rise", 0.6, "rect", "ASSUMPTION")
    b.add("hot-spot minus mean winding temperature", 2.0, "rect", "ASSUMPTION (a thermocouple on the coil checks it)")
    return b


def all_budgets() -> Dict[str, Budget]:
    return {"axial_force": axial_force_budget(), "normal_force_2N": plate_force_budget(2.0, "normal"),
            "tangential_force_2N": plate_force_budget(2.0, "tangential"),
            "normal_force_10N": plate_force_budget(10.0, "normal"),
            "page_truth_zaber": page_truth_budget("zaber"), "page_truth_lm13": page_truth_budget("lm13"),
            "page_truth_camera": page_truth_budget("camera"), "stage_truth": stage_truth_budget(),
            "ink_path": ink_path_budget(), "sync": sync_budget(), "km_point": km_budget(),
            "coil_temperature": thermal_budget()}


def tur_table() -> List[Dict]:
    """TUR of the main measurands against the tolerance each decision needs (CALC)."""
    B = all_budgets()
    rows = [
        ("R9", "F_c,min resolved against a 20 mN decision band (0.12 vs 0.14 N)", B["axial_force"], 20.0, "mN"),
        ("R9", "N at the ink threshold against EXP-Q02's +-5 mN target", B["normal_force_2N"], 5.0, "mN"),
        ("R9", "|R_perp| against AC-B01-09 (10 mN floor)", B["tangential_force_2N"], 10.0, "mN"),
        ("R9", "friction force at N = 0.2 N, mu 0.15 (+-20 % of 30 mN)", B["tangential_force_2N"], 6.0, "mN"),
        ("R10", "10 um RMS page error (REQ-RVJ-N06), Zaber truth", B["page_truth_zaber"], 10.0, "um"),
        ("R10", "10 um RMS page error, LM13 truth", B["page_truth_lm13"], 10.0, "um"),
        ("R10", "10 um RMS page error, camera truth", B["page_truth_camera"], 10.0, "um"),
        ("R10", "DeltaPen median 23.6 um per window, camera truth", B["page_truth_camera"], 23.6, "um"),
        ("R13", "false correction 25 um (AC-E01-09 bound), stage truth", B["stage_truth"], 25.0, "um"),
        ("R13", "30 % reduction of 250 um residual (review G3 target), stage truth", B["stage_truth"], 75.0, "um"),
        ("R13", "false correction 25 um from scanned ink", B["ink_path"], 25.0, "um"),
        ("R12", "K_f within +-10 % of the model (AC-B03-04 analogue)", B["km_point"], 10.0, "%"),
        ("R13", "coil rise <= 20 K (REQ-RVJ-N03) at 15 K", B["coil_temperature"], 5.0, "K"),
        ("all", "time alignment <= 50 us (section 0.4)", B["sync"], 50.0, "us"),
    ]
    out = []
    for rig, what, b, tol, unit in rows:
        out.append({"rig": rig, "decision": what, "measurand": b.measurand, "U_k2": round(b.U, 3), "unit": unit,
                    "tolerance": tol, "TUR": round(tur(tol, b.U), 2), "rule": "simple" if tur(tol, b.U) >= 4
                    else "guarded", "dominant_term": b.dominant()})
    return out
