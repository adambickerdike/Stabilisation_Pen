r"""Reader and writer for the ICD v1.0 section 4 binary log (little-endian).

Layout (docs/icd.md section 4.1)::

    header (36 B, packed)
        magic          8 B   b"PENLOG\x00\x01"
        format_version u16   = 1
        device_id      u64
        session_id     u64
        start_unix_ms  u64
        header_crc     u16   CRC-16/CCITT-FALSE over the first 34 B
    record (repeated)
        type   u8 | length u8 (payload bytes) | payload | crc16 u16
        crc16 = CRC-16/CCITT-FALSE over type, length and payload

Record payloads: 0x01 research frame (52 B, section 4.2), 0x02 stroke sample
(20 B, section 4.3), 0x03 event (10 B, section 4.4), 0x04 calibration
snapshot and 0x05 annotation, as defined in ICD v1.3 section 4.1 (the layouts
the firmware team proposed): 0x04 = rec_type u8 | cal_version u16 | the payload
of the calibration flash container (no magic, length or CRC), 0x05 = t_us u32 |
UTF-8 text.  Both stay available as raw bytes.

Interpretations of points the ICD leaves open (see app/README.md, "ICD
ambiguities"): CRCs are stored little-endian like every other field; the
record CRC covers the type and length bytes; phi in 0x02 is stored as
round(phi / 2 deg) (2 deg LSB, 0..179), theta as round(theta / 0.5 deg);
event 0x0009 (timestamp wrap) is logged after the wrap; ``arg`` = 0 is a plain
marker (current firmware), ``arg`` >= 1 is read as the number of wraps since
session start (proposal that survives lost events and silent gaps).

Robustness
----------
* every record is CRC-checked; a failing record starts a byte-wise resync
  scan that accepts a candidate only if it has a known type, the exact ICD
  length for fixed-length types, a valid CRC and (for the variable-length
  types 0x04/0x05) a valid successor record or end of file;
* 32-bit time stamps are unwrapped: t_us (wraps after 71.6 min) from wrap
  events and, as a fallback, from backward jumps larger than half the counter
  range; stroke t_ms from true 2^32 ms wraps *and* from restarts that follow a
  t_us wrap (the current firmware derives t_ms = t_us / 1000 from the wrapping
  microsecond counter, so t_ms restarts every 4 294 967.296 ms; reported as
  issue ``t_ms_follows_t_us_wrap`` and corrected to within 1 ms);
* nothing is silently dropped: every anomaly becomes a ``ParseIssue``.
"""
from __future__ import annotations

import binascii
import io
import struct
from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np

MAGIC = b"PENLOG\x00\x01"
FORMAT_VERSION = 1
HEADER_SIZE = 36
RECORD_OVERHEAD = 4          # type + length + crc16
_HDR = struct.Struct("<8sHQQQ")   # 34 B covered by the header CRC
_U16 = struct.Struct("<H")


class RecordType(IntEnum):
    RESEARCH_FRAME = 0x01
    STROKE_SAMPLE = 0x02
    EVENT = 0x03
    CALIBRATION_SNAPSHOT = 0x04
    ANNOTATION = 0x05


FIXED_LENGTHS: Dict[int, int] = {0x01: 52, 0x02: 20, 0x03: 10}
VARIABLE_LENGTH_TYPES = frozenset({0x04, 0x05})
KNOWN_TYPES = frozenset(FIXED_LENGTHS) | VARIABLE_LENGTH_TYPES


class EventCode(IntEnum):
    MODE_CHANGE = 0x0001
    FAULT_SET = 0x0002
    FAULT_CLEARED = 0x0003
    CALIBRATION_APPLIED = 0x0004
    ML_MODEL_LOADED = 0x0005
    AUTHORITY_CAPPED = 0x0006
    PEN_DOWN = 0x0007
    PEN_UP = 0x0008
    TIMESTAMP_WRAP = 0x0009
    PAGE_SET = 0x000A
    SYNC_PULSE = 0x000B


# numpy views of the packed payloads (no padding: itemsize == ICD length)
STROKE_DTYPE = np.dtype([("t_ms", "<u4"), ("stroke_id", "<u4"), ("x_um", "<i4"), ("y_um", "<i4"),
                         ("force_mN", "<u2"), ("theta_raw", "u1"), ("phi_raw", "u1")])
EVENT_DTYPE = np.dtype([("t_us", "<u4"), ("code", "<u2"), ("arg", "<i4")])
RESEARCH_FIELDS = (("t_us", "<u4"), ("q1", "<i2"), ("q2", "<i2"), ("qr1", "<i2"), ("qr2", "<i2"),
                   ("i1", "<i2"), ("i2", "<i2"), ("iref1", "<i2"), ("iref2", "<i2"), ("f_ax", "<i2"),
                   ("p_Hx", "<i4"), ("p_Hy", "<i4"), ("opt_valid", "u1"), ("dhat_x", "<i2"),
                   ("dhat_y", "<i2"), ("g", "u1"), ("f_est", "u1"), ("mode", "u1"), ("flags", "<u2"),
                   ("vbat_mV", "<u2"), ("t_coil", "<i2"), ("imu_ax", "<i2"), ("imu_ay", "<i2"),
                   ("theta", "<i2"), ("phi", "<i2"))
RESEARCH_DTYPE = np.dtype(list(RESEARCH_FIELDS))
assert STROKE_DTYPE.itemsize == 20 and EVENT_DTYPE.itemsize == 10 and RESEARCH_DTYPE.itemsize == 52

_STROKE = struct.Struct("<IIiiHBB")
_EVENT = struct.Struct("<IHi")
_RESEARCH = struct.Struct("<I9h2iB2h3BHHh2h2h")
assert _STROKE.size == 20 and _EVENT.size == 10 and _RESEARCH.size == 52

# scale factors (raw integer -> SI) for research frames, ICD section 4.2
RESEARCH_SCALE = {"q1": 1e-7, "q2": 1e-7, "qr1": 1e-7, "qr2": 1e-7, "i1": 1e-4, "i2": 1e-4,
                  "iref1": 1e-4, "iref2": 1e-4, "f_ax": 1e-3, "p_Hx": 1e-7, "p_Hy": 1e-7,
                  "dhat_x": 1e-7, "dhat_y": 1e-7, "g": 1 / 255, "f_est": 0.1, "vbat_mV": 1e-3,
                  "t_coil": 0.01, "imu_ax": 1e-3, "imu_ay": 1e-3, "theta": 0.01, "phi": 0.01}
RESEARCH_FLAG_BITS = {"contact": 0, "lift": 1, "v_sat": 2, "stop": 3, "fault_latched": 4,
                      "ml_active": 5, "ml_rejected": 6, "thermal_derate": 7}

THETA_LSB_DEG = 0.5      # stroke sample theta
PHI_LSB_DEG = 2.0        # stroke sample phi, "phi/2" in u8 (interpretation, see module doc)
T_US_MOD = 1 << 32
T_MS_MOD = 1 << 32


class LogFormatError(ValueError):
    """Unrecoverable format problem (bad magic, bad header, unsupported version)."""


class StrictParseError(LogFormatError):
    """Raised by ``read_log(strict=True)`` on the first recoverable anomaly."""


# --------------------------------------------------------------------- CRC
def crc16_ccitt_false(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, xorout 0.

    ``binascii.crc_hqx`` implements exactly this polynomial without reflection;
    check value for b"123456789" is 0x29B1.
    """
    return binascii.crc_hqx(bytes(data), crc)


def _check_range(name: str, value: int, lo: int, hi: int) -> int:
    v = int(value)
    if v != value or not lo <= v <= hi:
        raise ValueError(f"{name}={value!r} outside [{lo}, {hi}] or not an integer")
    return v


U8, U16, U32, U64 = (0, 0xFF), (0, 0xFFFF), (0, 0xFFFFFFFF), (0, (1 << 64) - 1)
I16, I32 = (-(1 << 15), (1 << 15) - 1), (-(1 << 31), (1 << 31) - 1)


# ----------------------------------------------------------------- records
@dataclass(frozen=True)
class Header:
    device_id: int
    session_id: int
    start_unix_ms: int
    format_version: int = FORMAT_VERSION

    def encode(self) -> bytes:
        body = _HDR.pack(MAGIC, _check_range("format_version", self.format_version, *U16),
                         _check_range("device_id", self.device_id, *U64),
                         _check_range("session_id", self.session_id, *U64),
                         _check_range("start_unix_ms", self.start_unix_ms, *U64))
        return body + _U16.pack(crc16_ccitt_false(body))

    @classmethod
    def decode(cls, buf: bytes, *, verify_crc: bool = True) -> "Header":
        if len(buf) < HEADER_SIZE:
            raise LogFormatError(f"file shorter than the {HEADER_SIZE}-byte header ({len(buf)} B)")
        magic, ver, dev, ses, start = _HDR.unpack_from(buf, 0)
        if magic != MAGIC:
            raise LogFormatError(f"bad magic {magic!r} (expected {MAGIC!r})")
        (crc,) = _U16.unpack_from(buf, 34)
        calc = crc16_ccitt_false(buf[:34])
        if verify_crc and crc != calc:
            raise LogFormatError(f"header CRC mismatch: stored 0x{crc:04X}, computed 0x{calc:04X}")
        if ver != FORMAT_VERSION:
            raise LogFormatError(f"unsupported format_version {ver} (this reader implements {FORMAT_VERSION})")
        return cls(device_id=dev, session_id=ses, start_unix_ms=start, format_version=ver)

    def to_json(self) -> dict:
        # u64 ids as decimal strings: JSON numbers lose precision above 2**53
        return {"format_version": self.format_version, "device_id": str(self.device_id),
                "session_id": str(self.session_id), "start_unix_ms": self.start_unix_ms}


@dataclass(frozen=True)
class StrokeSample:
    """ICD 0x02 stroke sample in raw integer units (deposited ink, page frame)."""
    t_ms: int
    stroke_id: int
    x_um: int
    y_um: int
    force_mN: int
    theta_raw: int
    phi_raw: int

    RTYPE = RecordType.STROKE_SAMPLE

    @property
    def theta_deg(self) -> float:
        return self.theta_raw * THETA_LSB_DEG

    @property
    def phi_deg(self) -> float:
        return self.phi_raw * PHI_LSB_DEG

    @staticmethod
    def angles_to_raw(theta_deg: float, phi_deg: float) -> Tuple[int, int]:
        th = int(round(min(max(theta_deg, 0.0), 90.0) / THETA_LSB_DEG))
        ph = int(round((phi_deg % 360.0) / PHI_LSB_DEG)) % int(round(360.0 / PHI_LSB_DEG))
        return th, ph

    def encode(self) -> bytes:
        return _STROKE.pack(_check_range("t_ms", self.t_ms, *U32),
                            _check_range("stroke_id", self.stroke_id, *U32),
                            _check_range("x_um", self.x_um, *I32), _check_range("y_um", self.y_um, *I32),
                            _check_range("force_mN", self.force_mN, *U16),
                            _check_range("theta_raw", self.theta_raw, *U8),
                            _check_range("phi_raw", self.phi_raw, *U8))

    @classmethod
    def decode(cls, payload: bytes) -> "StrokeSample":
        return cls(*_STROKE.unpack(payload))


@dataclass(frozen=True)
class Event:
    """ICD 0x03 event record."""
    t_us: int
    code: int
    arg: int

    RTYPE = RecordType.EVENT

    def encode(self) -> bytes:
        return _EVENT.pack(_check_range("t_us", self.t_us, *U32), _check_range("code", self.code, *U16),
                           _check_range("arg", self.arg, *I32))

    @classmethod
    def decode(cls, payload: bytes) -> "Event":
        return cls(*_EVENT.unpack(payload))

    @property
    def name(self) -> str:
        try:
            return EventCode(self.code).name
        except ValueError:
            return f"UNKNOWN_0x{self.code:04X}"


_RESEARCH_RANGES = {"t_us": U32, "opt_valid": U8, "g": U8, "f_est": U8, "mode": U8, "flags": U16,
                    "vbat_mV": U16, "p_Hx": I32, "p_Hy": I32}


@dataclass(frozen=True)
class ResearchFrame:
    """ICD 0x01 research frame (2 kHz bench stream), raw integer units."""
    t_us: int
    q1: int = 0
    q2: int = 0
    qr1: int = 0
    qr2: int = 0
    i1: int = 0
    i2: int = 0
    iref1: int = 0
    iref2: int = 0
    f_ax: int = 0
    p_Hx: int = 0
    p_Hy: int = 0
    opt_valid: int = 0
    dhat_x: int = 0
    dhat_y: int = 0
    g: int = 0
    f_est: int = 0
    mode: int = 0
    flags: int = 0
    vbat_mV: int = 0
    t_coil: int = 0
    imu_ax: int = 0
    imu_ay: int = 0
    theta: int = 0
    phi: int = 0

    RTYPE = RecordType.RESEARCH_FRAME

    def encode(self) -> bytes:
        vals = []
        for name, _ in RESEARCH_FIELDS:
            vals.append(_check_range(name, getattr(self, name), *_RESEARCH_RANGES.get(name, I16)))
        return _RESEARCH.pack(*vals)

    @classmethod
    def decode(cls, payload: bytes) -> "ResearchFrame":
        return cls(*_RESEARCH.unpack(payload))


@dataclass(frozen=True)
class RawRecord:
    """Record kept as opaque bytes (0x04, 0x05, unknown types, length mismatches)."""
    rtype: int
    payload: bytes

    def encode(self) -> bytes:
        return bytes(self.payload)

    def annotation(self) -> Optional[Tuple[int, str]]:
        """(t_us, text) of a 0x05 payload in the proposed layout t_us u32 | UTF-8, else None."""
        if self.rtype != RecordType.ANNOTATION or len(self.payload) < 4:
            return None
        try:
            return int.from_bytes(self.payload[:4], "little"), self.payload[4:].decode("utf-8")
        except UnicodeDecodeError:
            return None

    def calibration(self) -> Optional[Tuple[int, int, bytes]]:
        """(cal_type, cal_version, container payload) of a 0x04 record (ICD v1.3 s4.1), else None."""
        if self.rtype != RecordType.CALIBRATION_SNAPSHOT or len(self.payload) < 3:
            return None
        return self.payload[0], int.from_bytes(self.payload[1:3], "little"), self.payload[3:]


def annotation_record(text: str, t_us: int = 0) -> RawRecord:
    """0x05 record (ICD v1.3 s4.1): t_us u32 | UTF-8 text."""
    body = _check_range("t_us", t_us, *U32).to_bytes(4, "little") + text.encode("utf-8")
    if len(body) > 255:
        raise ValueError("annotation longer than the 255-byte payload limit")
    return RawRecord(int(RecordType.ANNOTATION), body)


def calibration_record(cal_type: int, cal_version: int, data: bytes) -> RawRecord:
    """0x04 record (ICD v1.3 s4.1): rec_type u8 | cal_version u16 | calibration container payload."""
    body = bytes([_check_range("cal_type", cal_type, *U8)]) + _check_range(
        "cal_version", cal_version, *U16).to_bytes(2, "little") + bytes(data)
    return RawRecord(int(RecordType.CALIBRATION_SNAPSHOT), body)


AnyRecord = Union[StrokeSample, Event, ResearchFrame, RawRecord]


def encode_record(rtype: int, payload: bytes) -> bytes:
    _check_range("record type", rtype, *U8)
    if len(payload) > 255:
        raise ValueError(f"payload of {len(payload)} B exceeds the u8 length field")
    if rtype in FIXED_LENGTHS and len(payload) != FIXED_LENGTHS[rtype]:
        raise ValueError(f"type 0x{rtype:02X} requires {FIXED_LENGTHS[rtype]} B, got {len(payload)}")
    body = bytes((rtype, len(payload))) + bytes(payload)
    return body + _U16.pack(crc16_ccitt_false(body))


def record_type_of(rec: AnyRecord) -> int:
    return int(rec.rtype) if isinstance(rec, RawRecord) else int(rec.RTYPE)


# ------------------------------------------------------------------ writer
class LogWriter:
    """Streaming writer: header on construction, then one call per record."""

    def __init__(self, fp: BinaryIO, header: Header):
        self._fp = fp
        self.header = header
        fp.write(header.encode())
        self.n_bytes = HEADER_SIZE
        self.counts: Counter = Counter()

    def write(self, rec: AnyRecord) -> None:
        rtype = record_type_of(rec)
        data = encode_record(rtype, rec.encode())
        self._fp.write(data)
        self.n_bytes += len(data)
        self.counts[rtype] += 1

    def write_all(self, recs: Iterable[AnyRecord]) -> None:
        for r in recs:
            self.write(r)

    def annotation(self, text: str, t_us: int = 0) -> None:
        self.write(annotation_record(text, t_us))


def encode_log(header: Header, records: Iterable[AnyRecord]) -> bytes:
    buf = io.BytesIO()
    LogWriter(buf, header).write_all(records)
    return buf.getvalue()


def write_log(path, header: Header, records: Iterable[AnyRecord]) -> bytes:
    data = encode_log(header, records)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return data


# ------------------------------------------------------------------ reader
@dataclass
class ParseIssue:
    offset: int
    kind: str
    detail: str = ""
    skipped: int = 0

    def to_json(self) -> dict:
        return {"offset": self.offset, "kind": self.kind, "detail": self.detail, "skipped": self.skipped}


# kinds that indicate lost or unusable data (vs. informational ones)
DATA_LOSS_KINDS = frozenset({"crc_mismatch", "bad_length", "unknown_type_resync", "truncated",
                             "resync", "trailing_garbage", "length_mismatch"})


T_US_WRAP_MS = T_US_MOD / 1000.0          # 4 294 967.296 ms


class _Unwrapper:
    """Extend a wrapping unsigned counter to 64-bit time."""

    def __init__(self, modulus: int):
        self.mod = modulus
        self.epoch = 0
        self.last: Optional[int] = None
        self.inferred = 0

    def feed(self, t: int) -> int:
        if self.last is not None and t < self.last and (self.last - t) > self.mod // 2:
            self.epoch += 1
            self.inferred += 1
        self.last = t
        return self.epoch * self.mod + t


class _MicroClock:
    """t_us of events and research frames: heuristic unwrap + wrap events (count or marker)."""

    def __init__(self):
        self.u = _Unwrapper(T_US_MOD)
        self.n = 0
        self.inferred_at = -10
        self.unconfirmed = False
        self.events = 0

    @property
    def epoch(self) -> int:
        return self.u.epoch

    def feed(self, t: int) -> int:
        before = self.u.epoch
        v = self.u.feed(t)
        self.n += 1
        if self.u.epoch != before:
            self.inferred_at = self.n
            self.unconfirmed = True
        return v

    def wrap_event(self, t: int, arg: int) -> Tuple[int, Optional[str]]:
        """Apply a 0x0009 event already passed through ``feed``; returns (t unwrapped, issue)."""
        self.events += 1
        note = None
        if arg >= 1:                                   # wraps since session start
            if self.u.epoch > arg:
                note = f"inferred epoch {self.u.epoch} > wrap event count {arg}; using event"
            self.u.epoch = arg
        elif arg == 0:                                 # marker: exactly one wrap just happened
            if not (self.unconfirmed and self.inferred_at >= self.n - 1):
                self.u.epoch += 1
        else:
            return self.u.epoch * self.u.mod + t, f"wrap event with negative arg {arg} ignored"
        self.unconfirmed = False
        return self.u.epoch * self.u.mod + t, note


class _StrokeClock:
    """Stroke t_ms: true 2^32 ms wraps plus restarts that follow t_us wraps."""

    def __init__(self):
        self.ms = _Unwrapper(T_MS_MOD)
        self.k = 0
        self.prev: Optional[int] = None
        self.prev_epoch = 0

    def feed(self, t_ms: int, us_epoch: int) -> Tuple[int, Optional[str]]:
        flag = None
        if self.prev is not None and t_ms < self.prev and self.prev - t_ms <= T_MS_MOD // 2:
            if us_epoch > self.prev_epoch:
                self.k += us_epoch - self.prev_epoch
                flag = "t_ms_follows_t_us_wrap"
            elif self.prev > T_US_WRAP_MS - 600_000 and t_ms < 600_000:
                self.k += 1
                flag = "t_ms_follows_t_us_wrap"
            else:
                flag = "t_ms_backwards"
        self.prev = t_ms
        self.prev_epoch = us_epoch
        return self.ms.feed(t_ms) + int(round(self.k * T_US_WRAP_MS)), flag


@dataclass
class ParsedLog:
    header: Header
    n_bytes: int
    records: List[Tuple[int, AnyRecord]] = field(default_factory=list)
    issues: List[ParseIssue] = field(default_factory=list)
    stroke_payload: bytes = b""
    stroke_t_ms: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int64))
    events: List[Tuple[int, Event, int]] = field(default_factory=list)   # (offset, event, t_us unwrapped)
    research_payload: bytes = b""
    research_t_us: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int64))
    raw: List[Tuple[int, RawRecord]] = field(default_factory=list)
    counts: Dict[int, int] = field(default_factory=dict)
    t_us_wraps_total: int = 0          # final 32-bit epoch of t_us
    t_us_wraps_explicit: int = 0       # 0x0009 events seen
    t_us_wraps_inferred: int = 0       # backward jumps > 2^31 us detected by the heuristic
    t_ms_wraps_inferred: int = 0

    @property
    def strokes(self) -> np.ndarray:
        """Read-only structured array of the stroke samples in log order."""
        return np.frombuffer(self.stroke_payload, dtype=STROKE_DTYPE)

    @property
    def research(self) -> np.ndarray:
        return np.frombuffer(self.research_payload, dtype=RESEARCH_DTYPE)

    @property
    def annotations(self) -> List[Tuple[int, RawRecord]]:
        return [(o, r) for o, r in self.raw if r.rtype == RecordType.ANNOTATION]

    @property
    def bytes_skipped(self) -> int:
        return sum(i.skipped for i in self.issues)

    @property
    def data_loss(self) -> bool:
        return any(i.kind in DATA_LOSS_KINDS for i in self.issues)

    def summary(self, max_issues: int = 50) -> dict:
        kinds = Counter(i.kind for i in self.issues)
        return {"n_bytes": self.n_bytes,
                "records": {RecordType(k).name if k in KNOWN_TYPES else f"0x{k:02X}": v
                            for k, v in sorted(self.counts.items())},
                "n_records": sum(self.counts.values()),
                "issues_by_kind": dict(sorted(kinds.items())),
                "bytes_skipped": self.bytes_skipped,
                "data_loss": self.data_loss,
                "t_us_wraps": {"total": self.t_us_wraps_total, "wrap_events": self.t_us_wraps_explicit,
                               "heuristic_detections": self.t_us_wraps_inferred},
                "t_ms_wraps_inferred": self.t_ms_wraps_inferred,
                "issues": [i.to_json() for i in self.issues[:max_issues]],
                "issues_truncated": max(0, len(self.issues) - max_issues)}


def _candidate(buf: memoryview, pos: int, n: int, *, scanning: bool):
    """Try to read one record at ``pos``.

    Returns (rtype, payload, end) on success or a failure-kind string.
    While scanning (resync) only known types with an ICD-valid length count.
    """
    if pos + 2 > n:
        return "truncated"
    rtype = buf[pos]
    length = buf[pos + 1]
    if scanning:
        if rtype in FIXED_LENGTHS:
            if length != FIXED_LENGTHS[rtype]:
                return "bad_length"
        elif rtype not in VARIABLE_LENGTH_TYPES:
            return "unknown_type"
    end = pos + 2 + length + 2
    if end > n:
        return "truncated"
    stored = buf[end - 2] | (buf[end - 1] << 8)
    if binascii.crc_hqx(buf[pos:end - 2], 0xFFFF) != stored:
        return "crc_mismatch"
    return rtype, bytes(buf[pos + 2:end - 2]), end


def read_log(source: Union[bytes, bytearray, memoryview, str, Path], *, strict: bool = False,
             verify_header_crc: bool = True) -> ParsedLog:
    """Parse a complete log.

    ``strict=True`` raises ``StrictParseError`` on the first anomaly (use for
    golden vectors); otherwise anomalies are recorded in ``ParsedLog.issues``
    and parsing resynchronises.
    """
    if isinstance(source, (str, Path)):
        data = Path(source).read_bytes()
    else:
        data = bytes(source)
    header = Header.decode(data, verify_crc=verify_header_crc)
    n = len(data)
    buf = memoryview(data)
    out = ParsedLog(header=header, n_bytes=n)
    strokes = bytearray()
    research = bytearray()
    stroke_t: List[int] = []
    research_t: List[int] = []
    counts: Counter = Counter()
    us = _MicroClock()
    ms = _StrokeClock()
    seen_flags: set = set()

    def issue(pos, kind, detail="", skipped=0):
        pi = ParseIssue(pos, kind, detail, skipped)
        if strict:
            raise StrictParseError(f"{kind} at offset {pos}: {detail}")
        out.issues.append(pi)

    def accept(pos, rtype, payload):
        counts[rtype] += 1
        expected = FIXED_LENGTHS.get(rtype)
        if expected is not None and len(payload) != expected:
            issue(pos, "length_mismatch", f"type 0x{rtype:02X} with {len(payload)} B (ICD: {expected} B)")
            rec: AnyRecord = RawRecord(rtype, payload)
        elif rtype == RecordType.STROKE_SAMPLE:
            rec = StrokeSample.decode(payload)
            strokes.extend(payload)
            t_val, flag = ms.feed(rec.t_ms, us.epoch)
            stroke_t.append(t_val)
            if flag == "t_ms_backwards" or (flag and flag not in seen_flags):
                seen_flags.add(flag)
                issue(pos, flag, "stroke t_ms restarted after a t_us wrap (firmware derives t_ms from the "
                                 "32-bit us counter; ICD 4.3 implies a u32 ms counter); corrected by "
                                 "+4294967.296 ms per wrap" if flag != "t_ms_backwards" else
                      f"t_ms decreased to {rec.t_ms} without a wrap")
        elif rtype == RecordType.EVENT:
            rec = Event.decode(payload)
            t_unwrapped = us.feed(rec.t_us)
            if rec.code == EventCode.TIMESTAMP_WRAP:
                out.t_us_wraps_explicit += 1
                t_unwrapped, note = us.wrap_event(rec.t_us, rec.arg)
                if note:
                    issue(pos, "wrap_count_mismatch" if rec.arg >= 1 else "wrap_event_invalid", note)
            out.events.append((pos, rec, t_unwrapped))
        elif rtype == RecordType.RESEARCH_FRAME:
            rec = ResearchFrame.decode(payload)
            research.extend(payload)
            research_t.append(us.feed(rec.t_us))
        else:
            rec = RawRecord(rtype, payload)
            if rtype not in KNOWN_TYPES:
                issue(pos, "unknown_type", f"type 0x{rtype:02X} with valid CRC kept as raw bytes")
            out.raw.append((pos, rec))
        out.records.append((pos, rec))

    pos = HEADER_SIZE
    scanning = False
    scan_start = pos
    while pos < n:
        res = _candidate(buf, pos, n, scanning=scanning)
        if not scanning:
            if isinstance(res, tuple):
                rtype, payload, end = res
                accept(pos, rtype, payload)
                pos = end
                continue
            detail = f"type byte 0x{buf[pos]:02X}" if pos < n else ""
            issue(pos, res, detail)
            scanning = True
            scan_start = pos
            pos += 1
            continue
        # scanning for the next trustworthy record
        if isinstance(res, tuple):
            rtype, payload, end = res
            ok = True
            if rtype in VARIABLE_LENGTH_TYPES and end != n:
                ok = isinstance(_candidate(buf, end, n, scanning=True), tuple)
            if ok:
                issue(scan_start, "resync", f"resynchronised at offset {pos}", skipped=pos - scan_start)
                scanning = False
                accept(pos, rtype, payload)
                pos = end
                continue
        pos += 1
    if scanning:
        issue(scan_start, "trailing_garbage", "no valid record found before end of file",
              skipped=n - scan_start)
    out.stroke_payload = bytes(strokes)
    out.research_payload = bytes(research)
    out.stroke_t_ms = np.asarray(stroke_t, dtype=np.int64)
    out.research_t_us = np.asarray(research_t, dtype=np.int64)
    out.counts = dict(counts)
    out.t_us_wraps_inferred = us.u.inferred
    out.t_us_wraps_total = us.epoch
    out.t_ms_wraps_inferred = ms.ms.inferred + ms.k
    return out


def iter_record_spans(data: bytes) -> List[Tuple[int, int, int]]:
    """(offset, end, type) of every record of an *uncorrupted* log (test helper)."""
    spans = []
    pos = HEADER_SIZE
    while pos < len(data):
        length = data[pos + 1]
        end = pos + 4 + length
        spans.append((pos, end, data[pos]))
        pos = end
    return spans
