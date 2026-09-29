"""Convert a logged rig session (rig.logger) into physical units and into the s2r-bench-1 layout
(s2r/io.py) that the identification pipeline and the rig analyses read.

A channel map says what each ADS131M08 channel, encoder and the command word carry. The defaults
below are the PROPOSED wiring of docs/measurement_rig.md (section "Wiring"); a record that uses
different wiring stores its own map in its record.yaml and passes it here.

Units: bridges are converted to mV/V (reading / excitation), then to newtons with the in-situ
calibration of rig.calib (polynomial in mV/V); shunts to amperes; encoders to metres.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from . import protocol

VREF = 1.2           # ADS131M08 internal reference (MFR AMF-222)

# PROPOSED DESIGN: default channel maps per rig. kind: bridge | shunt | volt | hall ; gain = PGA gain
CHANNEL_MAPS: Dict[str, Dict] = {
    "R9": {"adc": {0: ("F_a", "bridge", 128), 1: ("F_x", "bridge", 128), 2: ("F_y", "bridge", 128),
                   3: ("F_z", "bridge", 128), 4: ("i_A", "shunt", 1), 5: ("s_hall_V", "volt", 1)},
           "enc": {0: ("x_enc", 0.244e-6), 1: ("y_enc", 0.244e-6)}, "cmd": ("iref_A", 1e-6),
           "excitation_V": 3.3, "shunt_ohm": 0.1},
    "R10": {"adc": {}, "enc": {0: ("x_enc", 0.244e-6), 1: ("y_enc", 0.244e-6)}, "cmd": ("cmd", 1.0),
            "excitation_V": 3.3, "shunt_ohm": 0.1},
    "R12": {"adc": {0: ("F_x", "bridge", 128), 1: ("F_y", "bridge", 128), 2: ("F_z", "bridge", 128),
                    3: ("i_A", "shunt", 4), 4: ("i2_A", "shunt", 4), 5: ("v_V", "volt", 1),
                    6: ("hall1_V", "volt", 1), 7: ("hall2_V", "volt", 1)},
            "enc": {0: ("x_enc", 0.244e-6), 1: ("y_enc", 0.244e-6)}, "cmd": ("iref_A", 1e-6),
            "excitation_V": 3.3, "shunt_ohm": 0.1},
    "R13": {"adc": {0: ("F_a", "bridge", 128), 1: ("F_x", "bridge", 128), 2: ("F_y", "bridge", 128),
                    3: ("F_z", "bridge", 128), 4: ("i_A", "shunt", 4), 5: ("i2_A", "shunt", 4),
                    6: ("vcm_i_A", "shunt", 1), 7: ("v_V", "volt", 1)},
            "enc": {0: ("x_enc", 0.244e-6), 1: ("y_enc", 0.244e-6), 2: ("d1_enc", 0.244e-6), 3: ("d2_enc", 0.244e-6)},
            "cmd": ("dist_cmd_m", 0.244e-6), "excitation_V": 3.3, "shunt_ohm": 0.1},
}


def time_s(t_cyc: np.ndarray, f_cpu: float) -> np.ndarray:
    t = np.asarray(t_cyc, np.float64)
    return (t - t[0]) / f_cpu


def adc_volts(code, gain) -> np.ndarray:
    return protocol.adc_code_to_volts(code, gain, VREF)


def to_units(session: Dict, chmap: Dict, cal: Dict = None) -> Dict[str, np.ndarray]:
    """session: dict from rig.logger.load_session. cal: {name: bridge calibration dict (rig.calib)}.
    Bridges without a calibration are returned in mV/V (name + '_mVV')."""
    cal = cal or {}
    s = session["samples"]
    f_cpu = float(session["info"]["config"].get("f_cpu", 600e6))
    out = {"t_s": time_s(s["t_cyc"], f_cpu), "seq": s["seq"].astype(np.int64), "flags": s["flags"]}
    for ch, (name, kind, gain) in chmap.get("adc", {}).items():
        v = adc_volts(s["adc"][:, ch], gain)
        if kind == "bridge":
            mvv = 1e3 * v / chmap["excitation_V"]
            if name in cal:
                from .calib import apply_bridge
                out[name] = apply_bridge(cal[name], mvv)
            else:
                out[name + "_mVV"] = mvv
        elif kind == "shunt":
            out[name] = v / chmap["shunt_ohm"]
        else:
            out[name] = v
    for ch, (name, m_per_count) in chmap.get("enc", {}).items():
        out[name] = s["enc"][:, ch].astype(np.float64) * m_per_count
    if "cmd" in chmap:
        name, scale = chmap["cmd"]
        out[name] = s["cmd"].astype(np.float64) * scale
    return out


def events_by_kind(session: Dict, f_cpu: float, t0_cyc: int) -> Dict[str, Dict[str, np.ndarray]]:
    ev = session["events"]
    out = {}
    for k, name in protocol.EVENT_NAMES.items():
        m = ev["kind"] == k
        out[name] = {"t_s": (ev["t_cyc"][m].astype(np.float64) - t0_cyc) / f_cpu, "value": ev["value"][m]}
    return out


def split_by_markers(units: Dict[str, np.ndarray], markers: Dict[str, np.ndarray]) -> List[Dict]:
    """Cut a session into condition records at marker events (value = condition index, sent by the
    run script with the MARK command)."""
    t = units["t_s"]
    tm = np.asarray(markers["t_s"])
    vm = np.asarray(markers["value"])
    recs = []
    for i, (ta, v) in enumerate(zip(tm, vm)):
        tb = tm[i + 1] if i + 1 < len(tm) else t[-1] + 1
        m = (t >= ta) & (t < tb)
        if m.sum() < 2:
            continue
        rec = {k: a[m] for k, a in units.items() if isinstance(a, np.ndarray) and a.shape[:1] == t.shape}
        rec["condition"] = int(v)
        recs.append(rec)
    return recs


def to_bench(records: List[Dict], out_dir: str, experiment: str, group: str = "records", meta: Dict = None,
             evidence: str = "measured") -> str:
    """Write records in the s2r-bench-1 layout (s2r/io.py)."""
    from s2r import io as s2rio
    ds = {group: {"records": records}}
    return s2rio.save(ds, out_dir, experiment, evidence=evidence, meta=meta or {})
