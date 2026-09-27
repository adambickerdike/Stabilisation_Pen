#!/usr/bin/env python3
"""Independent Python reader/writer of the pen binary log (docs/icd.md s4,
format_version 1), written from the ICD text, not from the C code, so that
the C encoder (firmware/core/log_format.c) is cross-checked by a second
implementation.

  decode <file.bin> [--json out.json]   decode, check every CRC, print/write JSON
  verify <file.bin> <file.json>         decode again, compare with the JSON, and
                                        re-encode the JSON to bytes: must equal the file

JSON: header + records; every record carries its byte offset, type, length,
CRC status, the raw log-unit fields ("raw") and SI values ("si").
Proposed layouts for record types the ICD leaves undefined (0x04 calibration
snapshot, 0x05 annotation) follow firmware/include/log_format.h.
Evidence status: format tooling (no measurement content).
"""
from __future__ import annotations

import argparse
import binascii
import json
import math
import struct
import sys

MAGIC = b"PENLOG\x00\x01"
TYPE_NAMES = {1: "research_frame", 2: "stroke_sample", 3: "event", 4: "calibration_snapshot", 5: "annotation"}
EVENT_NAMES = {1: "mode_change", 2: "fault_set", 3: "fault_cleared", 4: "calibration_applied", 5: "ml_model_loaded",
               6: "authority_capped", 7: "pen_down", 8: "pen_up", 9: "timestamp_wrap", 10: "page_set",
               11: "external_sync_pulse"}
MODE_NAMES = {0: "OFF", 1: "STANDBY", 2: "NEUTRAL_HOLD", 3: "ASSIST_KF", 4: "ASSIST_ML", 5: "GUIDED",
              6: "TRAINING_FADE", 7: "SAFE_PASSIVE"}
FAULT_NAMES = ["over_current_latch", "hall_frozen_implausible", "over_temperature", "low_battery",
               "optical_invalid_300ms", "watchdog_reset", "voltage_headroom", "charging_interlock",
               "ml_guard_trip_count"]
FLAG_NAMES = ["contact", "lift", "v_sat", "stop", "fault_latched", "ml_active", "ml_rejected", "thermal_derate"]
CAL_NAMES = {1: "CAL_HALL", 2: "CAL_ACT", 3: "CAL_ISNS", 4: "CAL_AXIAL", 5: "CAL_USER"}
ML_REASONS = ["nan_inf", "output_saturation", "clipped", "slew_limited", "a_posteriori_fallback", "stale"]
PH_UNDEFINED = -2147483648
G0 = 9.80665

# research frame, ICD s4.2 field order: (name, struct code, count)
RESEARCH = [("t_us", "I", 1), ("q", "h", 2), ("qr", "h", 2), ("i", "h", 2), ("iref", "h", 2), ("f_ax", "h", 1),
            ("p_H", "i", 2), ("opt_valid", "B", 1), ("dhat", "h", 2), ("g", "B", 1), ("f_est", "B", 1),
            ("mode", "B", 1), ("flags", "H", 1), ("vbat_mV", "H", 1), ("t_coil", "h", 1), ("imu_a", "h", 2),
            ("theta", "h", 1), ("phi", "h", 1)]
RESEARCH_FMT = "<" + "".join(c * n for _, c, n in RESEARCH)
STROKE_FMT = "<IIiiHBB"
EVENT_FMT = "<IHi"


def crc16(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)   # CRC-16/CCITT-FALSE


def bits(v, names):
    return [n for k, n in enumerate(names) if v >> k & 1]


def dec_research(p: bytes):
    vals = list(struct.unpack(RESEARCH_FMT, p))
    raw = {}
    for name, _c, n in RESEARCH:
        raw[name] = vals[:n] if n > 1 else vals[0]
        del vals[:n]
    ph_defined = raw["p_H"][0] != PH_UNDEFINED
    si = {"t_s": raw["t_us"] * 1e-6,
          "q_m": [v * 1e-7 for v in raw["q"]], "qr_m": [v * 1e-7 for v in raw["qr"]],
          "i_A": [v * 1e-4 for v in raw["i"]], "iref_A": [v * 1e-4 for v in raw["iref"]],
          "f_ax_N": raw["f_ax"] * 1e-3,
          "p_H_m": [v * 1e-7 for v in raw["p_H"]] if ph_defined else None,
          "opt_valid_modules": [k + 1 for k in range(8) if raw["opt_valid"] >> k & 1],
          "dhat_m": [v * 1e-7 for v in raw["dhat"]], "g": raw["g"] / 255.0, "f_est_Hz": raw["f_est"] * 0.1,
          "mode": MODE_NAMES.get(raw["mode"], f"unknown_{raw['mode']}"), "flags": bits(raw["flags"], FLAG_NAMES),
          "vbat_V": raw["vbat_mV"] * 1e-3, "t_coil_C": raw["t_coil"] * 0.01,
          "imu_a_mps2": [v * 1e-3 * G0 for v in raw["imu_a"]],
          "theta_deg": raw["theta"] * 0.01, "phi_deg": raw["phi"] * 0.01}
    return raw, si


def enc_research(raw) -> bytes:
    vals = []
    for name, _c, n in RESEARCH:
        vals += list(raw[name]) if n > 1 else [raw[name]]
    return struct.pack(RESEARCH_FMT, *vals)


def dec_stroke(p: bytes):
    t_ms, sid, x, y, force, th, ph = struct.unpack(STROKE_FMT, p)
    raw = {"t_ms": t_ms, "stroke_id": sid, "x": x, "y": y, "force": force, "theta": th, "phi": ph}
    si = {"t_s": t_ms * 1e-3, "x_m": x * 1e-6, "y_m": y * 1e-6, "force_N": force * 1e-3, "theta_deg": th * 0.5,
          "phi_deg": ph * 2.0}
    return raw, si


def enc_stroke(raw) -> bytes:
    return struct.pack(STROKE_FMT, raw["t_ms"], raw["stroke_id"], raw["x"], raw["y"], raw["force"], raw["theta"],
                       raw["phi"])


def dec_event(p: bytes):
    t_us, code, arg = struct.unpack(EVENT_FMT, p)
    raw = {"t_us": t_us, "code": code, "arg": arg}
    si = {"t_s": t_us * 1e-6, "name": EVENT_NAMES.get(code, f"unknown_{code:#06x}")}
    if code == 1:
        si["mode_new"] = MODE_NAMES.get(arg & 0xFF)
        si["mode_old"] = MODE_NAMES.get((arg >> 8) & 0xFF)
    elif code in (2, 3):
        si["faults"] = bits(arg & 0xFFFF, FAULT_NAMES)
    elif code == 6:
        si["reasons"] = bits(arg & 0xFF, ML_REASONS)
    elif code == 9:
        si["wrap_count"] = arg
    return raw, si


def enc_event(raw) -> bytes:
    return struct.pack(EVENT_FMT, raw["t_us"], raw["code"], raw["arg"])


def dec_cal_user(rec: bytes):
    """CAL_USER flash record (firmware/include/calib.h)."""
    if len(rec) < 11 or rec[:4] != b"PCAL":
        return {"error": "not a PCAL record"}
    rtype, ver, ln = rec[4], struct.unpack("<H", rec[5:7])[0], struct.unpack("<H", rec[7:9])[0]
    body = rec[9:9 + ln]
    crc_ok = crc16(rec[:9 + ln]) == struct.unpack("<H", rec[9 + ln:11 + ln])[0]
    out = {"rec_type": CAL_NAMES.get(rtype, rtype), "cal_version": ver, "length": ln, "crc_ok": crc_ok}
    if rtype == 5 and ver == 1 and ln == 30:
        f = struct.unpack("<7fBB", body)
        out.update({"f0_Hz": f[0], "f_stroke_Hz": f[1], "f_gate_Hz": f[2], "f_gate_width_Hz": f[3], "g_max": f[4],
                    "q_lim_m": f[5], "gamma": f[6], "mode_perm": f[7], "flags": f[8]})
    return out


def dec_calsnap(p: bytes):
    raw = {"cal_type": p[0], "cal_version": struct.unpack("<H", p[1:3])[0], "data_hex": p[3:].hex()}
    si = {"cal_type": CAL_NAMES.get(p[0], p[0])}
    if p[0] == 5:
        si["record"] = dec_cal_user(p[3:])
    return raw, si


def enc_calsnap(raw) -> bytes:
    return bytes([raw["cal_type"]]) + struct.pack("<H", raw["cal_version"]) + bytes.fromhex(raw["data_hex"])


def dec_annot(p: bytes):
    t_us = struct.unpack("<I", p[:4])[0]
    raw = {"t_us": t_us, "text_hex": p[4:].hex()}
    si = {"t_s": t_us * 1e-6, "text": p[4:].decode("utf-8", errors="replace")}
    return raw, si


def enc_annot(raw) -> bytes:
    return struct.pack("<I", raw["t_us"]) + bytes.fromhex(raw["text_hex"])


CODECS = {1: (dec_research, enc_research, 52), 2: (dec_stroke, enc_stroke, 20), 3: (dec_event, enc_event, 10),
          4: (dec_calsnap, enc_calsnap, None), 5: (dec_annot, enc_annot, None)}


def decode(buf: bytes):
    if len(buf) < 36 or buf[:8] != MAGIC:
        raise ValueError("not a PENLOG file")
    fv, dev, ses, t0, hcrc = struct.unpack("<HQQQH", buf[8:36])
    header = {"magic": buf[:8].hex(), "format_version": fv, "device_id": f"{dev:#018x}", "session_id": ses,
              "start_unix_ms": t0, "header_crc": f"{hcrc:#06x}", "header_crc_ok": crc16(buf[:34]) == hcrc}
    recs = []
    off = 36
    while off < len(buf):
        if off + 4 > len(buf):
            raise ValueError(f"truncated record at {off}")
        t, ln = buf[off], buf[off + 1]
        end = off + 2 + ln
        crc = struct.unpack("<H", buf[end:end + 2])[0]
        r = {"offset": off, "type": t, "type_name": TYPE_NAMES.get(t, "unknown"), "length": ln,
             "crc": f"{crc:#06x}", "crc_ok": crc16(buf[off:end]) == crc}
        p = buf[off + 2:end]
        if t in CODECS:
            dec, _enc, fixed = CODECS[t]
            r["length_ok"] = fixed is None or ln == fixed
            r["raw"], r["si"] = dec(p)
        else:
            r["payload_hex"] = p.hex()
        recs.append(r)
        off = end + 2
    return {"source": "firmware/tools/pen_log.py (independent decoder of docs/icd.md s4)", "header": header,
            "records": recs}


def encode(doc) -> bytes:
    h = doc["header"]
    body = bytes.fromhex(h["magic"]) + struct.pack("<HQQQ", h["format_version"], int(h["device_id"], 16),
                                                   h["session_id"], h["start_unix_ms"])
    out = bytearray(body + struct.pack("<H", crc16(body)))
    for r in doc["records"]:
        t = r["type"]
        p = CODECS[t][1](r["raw"]) if t in CODECS else bytes.fromhex(r["payload_hex"])
        rec = bytes([t, len(p)]) + p
        out += rec + struct.pack("<H", crc16(rec))
    return bytes(out)


def _clean(o):
    """JSON-safe floats (no NaN) rounded to 12 significant digits for stable diffs."""
    if isinstance(o, float):
        if not math.isfinite(o):
            return None
        return float(f"{o:.12g}")
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode")
    d.add_argument("bin")
    d.add_argument("--json")
    v = sub.add_parser("verify")
    v.add_argument("bin")
    v.add_argument("json")
    a = ap.parse_args(argv)
    buf = open(a.bin, "rb").read()
    doc = _clean(decode(buf))
    bad = [r["offset"] for r in doc["records"] if not r["crc_ok"] or not r.get("length_ok", True)]
    if a.cmd == "decode":
        txt = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        if a.json:
            open(a.json, "w", encoding="utf-8").write(txt)
            counts = {}
            for r in doc["records"]:
                counts[r["type_name"]] = counts.get(r["type_name"], 0) + 1
            print(f"decoded {a.bin}: {len(buf)} bytes, header CRC ok {doc['header']['header_crc_ok']}, "
                  f"records {counts}, bad {bad}; wrote {a.json}")
        else:
            sys.stdout.write(txt)
    else:
        ref = json.load(open(a.json, encoding="utf-8"))
        same = ref == doc
        re = encode(ref)
        print(f"verify {a.bin}: JSON matches fresh decode: {same}; re-encoded JSON == file bytes: {re == buf}; "
              f"bad records: {bad}; header CRC ok {doc['header']['header_crc_ok']}")
        return 0 if (same and re == buf and not bad and doc["header"]["header_crc_ok"]) else 1
    return 0 if not bad and doc["header"]["header_crc_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
