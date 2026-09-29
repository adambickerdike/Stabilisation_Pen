"""USB-serial logger for the rig DAQ (rig/firmware/rig_daq). One process, one DAQ.

    python3 -m rig.logger --port /dev/ttyACM0 --seconds 60 --out DIR [--cmd "RATE 4000" --cmd "START"]
    python3 -m rig.logger --replay DIR/raw.bin --out DIR2        (parse an existing raw file again)

Writes, per session:
  raw.bin        every byte received, unmodified (write-once raw, validation/records/README.md section 4)
  session.npz    parsed arrays: samples, events, imu, page (numpy structured arrays)
  session.json   configuration echoed by the firmware, host commands with host times, parser
                 statistics (frames, CRC errors, resync bytes, missing frames), SHA-256 of raw.bin,
                 and stabpen.provenance metadata

Dependency for live capture: pyserial==3.5 (pip install pyserial==3.5). Replay needs nothing extra.
The Teensy's USB serial ignores the baud rate; 12 Mbit/s is passed for form.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import List

import numpy as np

from . import protocol

BAUD = 12_000_000


def _open_serial(port: str):
    try:
        import serial  # pyserial
    except ImportError as e:  # pragma: no cover - depends on the host
        raise SystemExit("live capture needs pyserial: pip install pyserial==3.5") from e
    return serial.Serial(port, BAUD, timeout=0.05)


def save_session(out_dir: str, raw: bytes, parsed: protocol.Parsed, commands: List[dict], extra: dict = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "raw.bin")
    if not os.path.exists(raw_path):
        with open(raw_path, "wb") as f:
            f.write(raw)
        try:
            os.chmod(raw_path, 0o444)                    # write-once raw
        except OSError:
            pass
    arrs = parsed.arrays()
    np.savez_compressed(os.path.join(out_dir, "session.npz"), **arrs)
    st = dict(parsed.stats)
    st["missing_frames"] = protocol.seq_gaps(arrs["samples"]["seq"]) if len(arrs["samples"]) else 0
    st["samples"] = int(len(arrs["samples"]))
    st["events"] = int(len(arrs["events"]))
    info = {"format": "rig-daq-1", "config": parsed.config, "text": parsed.text[-200:], "stats": st,
            "commands": commands, "raw_sha256": hashlib.sha256(raw).hexdigest(), "evidence_status":
            "MEASURED if recorded on a rig; otherwise say what produced raw.bin"}
    if extra:
        info.update(extra)
    try:
        from stabpen import provenance
        info["meta"] = provenance.metadata(info["evidence_status"])
    except Exception:
        pass
    with open(os.path.join(out_dir, "session.json"), "w") as f:
        json.dump(info, f, indent=1, default=str)
    return info


def capture(port: str, seconds: float, out_dir: str, commands: List[str] = (), stop_cmd: str = "STOP") -> dict:
    ser = _open_serial(port)
    sent = []
    raw = bytearray()
    parser = protocol.StreamParser()
    for c in commands:
        ser.write((c.strip() + "\n").encode("ascii"))
        sent.append({"host_time": time.time(), "cmd": c})
        time.sleep(0.05)
    t_end = time.time() + seconds
    try:
        while time.time() < t_end:
            chunk = ser.read(65536)
            if chunk:
                raw += chunk
                parser.feed(chunk)
    except KeyboardInterrupt:
        pass
    finally:
        ser.write((stop_cmd + "\n").encode("ascii"))
        sent.append({"host_time": time.time(), "cmd": stop_cmd})
        time.sleep(0.1)
        tail = ser.read(65536)
        raw += tail
        parser.feed(tail)
        ser.close()
    return save_session(out_dir, bytes(raw), parser.out, sent, {"port": port, "seconds": seconds})


def replay(raw_path: str, out_dir: str) -> dict:
    with open(raw_path, "rb") as f:
        raw = f.read()
    p = protocol.parse_bytes(raw)
    return save_session(out_dir, raw, p, [], {"replayed_from": raw_path})


def load_session(out_dir: str) -> dict:
    with open(os.path.join(out_dir, "session.json")) as f:
        info = json.load(f)
    with np.load(os.path.join(out_dir, "session.npz")) as z:
        arrs = {k: z[k] for k in z.files}
    return {"info": info, **arrs}


def main(argv=None):
    ap = argparse.ArgumentParser(description="rig DAQ logger")
    ap.add_argument("--port")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cmd", action="append", default=[], help="command line sent before capture (repeatable)")
    ap.add_argument("--replay", help="parse an existing raw.bin instead of capturing")
    a = ap.parse_args(argv)
    if a.replay:
        info = replay(a.replay, a.out)
    else:
        if not a.port:
            ap.error("--port is required for live capture")
        info = capture(a.port, a.seconds, a.out, a.cmd or ["START"])
    print(json.dumps(info["stats"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
