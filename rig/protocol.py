"""Binary frame format between the rig DAQ (Teensy 4.1, rig/firmware/rig_daq) and the host.

PROPOSED DESIGN. The firmware header rig/firmware/rig_daq/rig_protocol.h mirrors
this file; tests check the sizes and the CRC against a known vector.

Frame (little-endian):

    0xA5 0x5A | type u8 | len u8 | payload[len] | crc16 u16

crc16 is CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no final
xor) over type, len and payload. Check value for b"123456789": 0x29B1.

Time stamps are raw ARM cycle counts (DWT_CYCCNT extended to 64 bits in the
firmware). The CPU clock (F_CPU_ACTUAL, 600 MHz on a Teensy 4.1 at stock speed)
is sent once in the CONFIG text frame, so t_s = t_cyc / f_cpu. Every channel of
every instrument read by the DAQ is stamped on this one clock.

Payloads
--------
SAMPLE  0x01  seq u32, t_cyc u64, adc i32[8], enc i32[4], cmd i32, flags u16,
              nadc u8, rsv u8                                          68 bytes
              adc: ADS131M08 codes (24-bit, sign-extended), stamped at DRDY;
              enc: quadrature counts latched in the same interrupt;
              cmd: the disturbance or current command sent in that tick
              (digital excitation for instrumental-variable FRFs);
              flags: bit0 camera trigger in this tick, bit1 sync-out level,
              bit2 DUT sync-in level, bit3 strobe on, bit4 disturbance loop on,
              bit5 current loop on, bit6 governor limiting, bit7 overrun seen.
EVENT   0x02  seq u32, t_cyc u64, kind u8, pad[3], value u32         20 bytes
              kinds: 1/2 sync out rise/fall, 3/4 DUT sync in rise/fall, 5 camera
              trigger, 6 strobe, 7 marker, 8 lift, 9 overrun, 10 temperature
TEXT    0x03  ASCII (status, errors, command echo)
CONFIG  0x04  ASCII "key=value;..." (f_cpu, adc rate, gains, channel map, ...)
IMU     0x05  seq u32, t_cyc u64, acc i16[3], gyr i16[3], temp i16, rsv u16  28 bytes
PAGE    0x06  seq u32, t_cyc u64, dx i16, dy i16, squal u8, valid u8, rsv u16 20 bytes
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

SYNC0, SYNC1 = 0xA5, 0x5A
T_SAMPLE, T_EVENT, T_TEXT, T_CONFIG, T_IMU, T_PAGE = 0x01, 0x02, 0x03, 0x04, 0x05, 0x06

FMT = {
    T_SAMPLE: "<IQ8i4iiHBB",
    T_EVENT: "<IQB3xI",
    T_IMU: "<IQ3h3hhH",
    T_PAGE: "<IQhhBBH",
}
SIZE = {k: struct.calcsize(v) for k, v in FMT.items()}
assert SIZE[T_SAMPLE] == 68 and SIZE[T_EVENT] == 20 and SIZE[T_IMU] == 28 and SIZE[T_PAGE] == 20

# event kinds
EV_SYNC_OUT_RISE, EV_SYNC_OUT_FALL, EV_DUT_RISE, EV_DUT_FALL = 1, 2, 3, 4
EV_CAM_TRIGGER, EV_STROBE, EV_MARKER, EV_LIFT, EV_OVERRUN, EV_TEMP = 5, 6, 7, 8, 9, 10
EVENT_NAMES = {1: "sync_out_rise", 2: "sync_out_fall", 3: "dut_rise", 4: "dut_fall", 5: "cam_trigger",
               6: "strobe", 7: "marker", 8: "lift", 9: "overrun", 10: "temperature"}
# EV_TEMP value: bits 31-24 thermocouple channel (0-3), bits 23-0 the MAX31856 linearised temperature
# register LTCBH:LTCBM:LTCBL (19-bit two's complement in bits 23-5, 0.0078125 C per LSB; MFR AMF-234)


def temp_event_to_celsius(value: int):
    """Decode an EV_TEMP value into (channel, degrees C)."""
    ch = (int(value) >> 24) & 0xFF
    raw = int(value) & 0xFFFFFF
    if raw & 0x800000:
        raw -= 1 << 24
    return ch, (raw >> 5) * 0.0078125

SAMPLE_DTYPE = np.dtype([("seq", "<u4"), ("t_cyc", "<u8"), ("adc", "<i4", (8,)), ("enc", "<i4", (4,)),
                         ("cmd", "<i4"), ("flags", "<u2"), ("nadc", "u1"), ("rsv", "u1")])
EVENT_DTYPE = np.dtype([("seq", "<u4"), ("t_cyc", "<u8"), ("kind", "u1"), ("value", "<u4")])
IMU_DTYPE = np.dtype([("seq", "<u4"), ("t_cyc", "<u8"), ("acc", "<i2", (3,)), ("gyr", "<i2", (3,)),
                      ("temp", "<i2"), ("rsv", "<u2")])
PAGE_DTYPE = np.dtype([("seq", "<u4"), ("t_cyc", "<u8"), ("dx", "<i2"), ("dy", "<i2"), ("squal", "u1"),
                       ("valid", "u1"), ("rsv", "<u2")])


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE."""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# a table-driven version for bulk parsing (same result, faster in Python)
_CRC_TABLE = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    _CRC_TABLE.append(_c)


def crc16_fast(data: bytes, crc: int = 0xFFFF) -> int:
    tbl = _CRC_TABLE
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ tbl[((crc >> 8) ^ b) & 0xFF]
    return crc


def frame(ftype: int, payload: bytes) -> bytes:
    if len(payload) > 255:
        raise ValueError("payload longer than 255 bytes")
    body = bytes([ftype, len(payload)]) + payload
    return bytes([SYNC0, SYNC1]) + body + struct.pack("<H", crc16_fast(body))


def pack_sample(seq, t_cyc, adc, enc, cmd=0, flags=0, nadc=8) -> bytes:
    adc = list(adc) + [0] * (8 - len(adc))
    enc = list(enc) + [0] * (4 - len(enc))
    return frame(T_SAMPLE, struct.pack(FMT[T_SAMPLE], int(seq) & 0xFFFFFFFF, int(t_cyc), *map(int, adc),
                                       *map(int, enc), int(cmd), int(flags), int(nadc), 0))


def pack_event(seq, t_cyc, kind, value=0) -> bytes:
    return frame(T_EVENT, struct.pack(FMT[T_EVENT], int(seq) & 0xFFFFFFFF, int(t_cyc), int(kind), int(value)))


def pack_imu(seq, t_cyc, acc, gyr, temp=0) -> bytes:
    return frame(T_IMU, struct.pack(FMT[T_IMU], int(seq) & 0xFFFFFFFF, int(t_cyc), *map(int, acc),
                                    *map(int, gyr), int(temp), 0))


def pack_page(seq, t_cyc, dx, dy, squal=0, valid=1) -> bytes:
    return frame(T_PAGE, struct.pack(FMT[T_PAGE], int(seq) & 0xFFFFFFFF, int(t_cyc), int(dx), int(dy),
                                     int(squal), int(valid), 0))


def pack_text(s: str, ftype: int = T_TEXT) -> bytes:
    return frame(ftype, s.encode("ascii", "replace")[:255])


@dataclass
class Parsed:
    samples: List[tuple] = field(default_factory=list)
    events: List[tuple] = field(default_factory=list)
    imu: List[tuple] = field(default_factory=list)
    page: List[tuple] = field(default_factory=list)
    text: List[str] = field(default_factory=list)
    config: Dict[str, str] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=lambda: {"frames": 0, "crc_errors": 0, "resync_bytes": 0,
                                                            "bad_length": 0, "unknown_type": 0})

    def arrays(self) -> Dict[str, np.ndarray]:
        return {"samples": np.array(self.samples, dtype=SAMPLE_DTYPE) if self.samples else
                np.zeros(0, SAMPLE_DTYPE),
                "events": np.array(self.events, dtype=EVENT_DTYPE) if self.events else np.zeros(0, EVENT_DTYPE),
                "imu": np.array(self.imu, dtype=IMU_DTYPE) if self.imu else np.zeros(0, IMU_DTYPE),
                "page": np.array(self.page, dtype=PAGE_DTYPE) if self.page else np.zeros(0, PAGE_DTYPE)}


class StreamParser:
    """Incremental parser: feed() arbitrary byte chunks (as read from USB serial); frames that
    fail the CRC or have an impossible length are counted and skipped by resynchronising on the
    next 0xA5 0x5A pair. Nothing is silently repaired."""

    def __init__(self):
        self.buf = bytearray()
        self.out = Parsed()

    def feed(self, chunk: bytes) -> None:
        self.buf.extend(chunk)
        buf = self.buf
        i = 0
        n = len(buf)
        st = self.out.stats
        while True:
            j = buf.find(b"\xa5\x5a", i)
            if j < 0:
                # keep a trailing 0xA5 that may start the next sync pair
                keep = 1 if n and buf[-1] == SYNC0 else 0
                st["resync_bytes"] += max(0, n - i - keep)
                i = n - keep
                break
            st["resync_bytes"] += j - i
            if j + 4 > n:
                i = j
                break
            ftype, flen = buf[j + 2], buf[j + 3]
            exp = SIZE.get(ftype)
            if exp is not None and flen != exp:
                st["bad_length"] += 1
                i = j + 2
                continue
            end = j + 4 + flen + 2
            if end > n:
                i = j
                break
            body = bytes(buf[j + 2:j + 4 + flen])
            (crc,) = struct.unpack_from("<H", buf, j + 4 + flen)
            if crc16_fast(body) != crc:
                st["crc_errors"] += 1
                i = j + 2
                continue
            payload = body[2:]
            st["frames"] += 1
            if ftype == T_SAMPLE:
                v = struct.unpack(FMT[T_SAMPLE], payload)
                self.out.samples.append((v[0], v[1], v[2:10], v[10:14], v[14], v[15], v[16], v[17]))
            elif ftype == T_EVENT:
                v = struct.unpack(FMT[T_EVENT], payload)
                self.out.events.append((v[0], v[1], v[2], v[3]))
            elif ftype == T_IMU:
                v = struct.unpack(FMT[T_IMU], payload)
                self.out.imu.append((v[0], v[1], v[2:5], v[5:8], v[8], v[9]))
            elif ftype == T_PAGE:
                v = struct.unpack(FMT[T_PAGE], payload)
                self.out.page.append(v)
            elif ftype == T_TEXT:
                self.out.text.append(payload.decode("ascii", "replace"))
            elif ftype == T_CONFIG:
                s = payload.decode("ascii", "replace")
                for kv in s.split(";"):
                    if "=" in kv:
                        k, val = kv.split("=", 1)
                        self.out.config[k.strip()] = val.strip()
            else:
                st["unknown_type"] += 1
            i = end
        del buf[:i]


def parse_bytes(data: bytes) -> Parsed:
    p = StreamParser()
    p.feed(data)
    return p.out


def seq_gaps(seq: np.ndarray) -> int:
    """Number of missing frames from a u32 sequence counter (wrap-safe)."""
    if len(seq) < 2:
        return 0
    d = (np.diff(seq.astype(np.int64)) % (1 << 32))
    return int(np.sum(d[d > 1] - 1))


def adc_code_to_volts(code, gain=1, vref=1.2):
    """ADS131M08 24-bit two's complement code to differential input voltage.
    Full scale is +-VREF/gain (MFR, ADS131M08 datasheet SBAS950B; internal VREF 1.2 V)."""
    return np.asarray(code, float) * (vref / gain) / (1 << 23)
