"""ICD v1.0 section 4 example vector for cross-checking independent parsers.

``example_log()`` builds a small log that exercises every record type, field
extremes, a 32-bit t_us wrap with its 0x0009 event, a calibration snapshot,
an annotation and a record of an unknown type (valid CRC).  ``describe()``
returns the decoded expectation (``data/samples/icd_v1_example.json``),
including the reader's reference behaviour on three corrupted variants.

The bytes come from this package's writer; the expectation JSON is what this
package's reader produces.  It is an interoperability vector, not an
independent oracle: the firmware team's golden vector
(firmware/tests/vectors/golden_log_v1.bin) is the independent check.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Dict, List, Tuple

from .logfmt import (HEADER_SIZE, Event, EventCode, Header, RawRecord, RecordType, ResearchFrame,
                     StrokeSample, crc16_ccitt_false, encode_log, encode_record, iter_record_spans, read_log)

HEADER = Header(device_id=0x0123456789ABCDEF, session_id=42, start_unix_ms=1790000000000)


def example_records() -> list:
    return [
        RawRecord(int(RecordType.ANNOTATION), "ICD v1.0 example vector (penapp); SYNTHETIC".encode()),
        Event(0, EventCode.MODE_CHANGE, 3),
        Event(1000, EventCode.PEN_DOWN, 0),
        StrokeSample(1, 0, 0, 0, 0, 0, 0),
        StrokeSample(6, 0, -2147483648, 2147483647, 65535, 180, 179),
        StrokeSample(11, 0, -1234, 5678, 950, 104, 18),
        ResearchFrame(t_us=11000, q1=-32768, q2=32767, qr1=-1, qr2=1, i1=-1234, i2=1234, iref1=-2000,
                      iref2=2000, f_ax=950, p_Hx=-2147483648, p_Hy=2147483647, opt_valid=0b111, dhat_x=-300,
                      dhat_y=300, g=255, f_est=90, mode=3, flags=0b1010_0001, vbat_mV=3700, t_coil=3550,
                      imu_ax=-981, imu_ay=12, theta=5000, phi=-9000),
        Event(12000, EventCode.PEN_UP, 0),
        RawRecord(int(RecordType.CALIBRATION_SNAPSHOT), bytes(range(8))),
        ResearchFrame(t_us=4294967000, flags=0),
        Event(5, EventCode.TIMESTAMP_WRAP, 1),
        ResearchFrame(t_us=505, flags=0),
        RawRecord(0x7F, b"\x00future"),
    ]


def example_log() -> bytes:
    return encode_log(HEADER, example_records())


def _corruptions() -> List[Tuple[str, str, Callable[[bytes], bytes]]]:
    data = example_log()
    spans = iter_record_spans(data)
    s4 = spans[4]     # second stroke sample
    s6 = spans[6]     # research frame

    def flip(b: bytes) -> bytes:
        x = bytearray(b)
        x[s4[0] + 7] ^= 0x10
        return bytes(x)

    def insert(b: bytes) -> bytes:
        return b[:s6[0]] + b"\x02\x14garbage!" + b[s6[0]:]

    def truncate(b: bytes) -> bytes:
        return b[:-3]

    return [("flip_bit_in_stroke_sample", f"xor 0x10 at offset {s4[0] + 7}", flip),
            ("insert_10_bytes_before_research_frame", f"insert 02 14 'garbage!' at offset {s6[0]}", insert),
            ("truncate_last_3_bytes", "drop the final 3 bytes", truncate)]


def _decoded(rec) -> dict:
    if isinstance(rec, RawRecord):
        return {"payload_hex": rec.payload.hex(), **({"text": rec.text} if rec.rtype == RecordType.ANNOTATION else {})}
    d = asdict(rec)
    if isinstance(rec, Event):
        d["name"] = rec.name
    return d


def describe() -> Dict:
    data = example_log()
    parsed = read_log(data)
    records = []
    t_unwrapped = {off: t for off, _, t in parsed.events}
    research_offsets = [off for off, r in parsed.records if isinstance(r, ResearchFrame)]
    for off, t in zip(research_offsets, parsed.research_t_us.tolist()):
        t_unwrapped[off] = t
    for (off, end, rtype), (off2, rec) in zip(iter_record_spans(data), parsed.records):
        assert off == off2
        entry = {"offset": off, "type": f"0x{rtype:02X}", "length": data[off + 1],
                 "bytes_hex": data[off:end].hex(), "crc16": f"0x{int.from_bytes(data[end - 2:end], 'little'):04X}",
                 "decoded": _decoded(rec)}
        if off in t_unwrapped:
            entry["t_us_unwrapped"] = int(t_unwrapped[off])
        records.append(entry)
    cases = []
    for name, op, fn in _corruptions():
        p = read_log(fn(data))
        cases.append({"name": name, "operation": op,
                      "expected": {"records": p.summary()["records"], "issues_by_kind": p.summary()["issues_by_kind"],
                                   "bytes_skipped": p.bytes_skipped,
                                   "stroke_samples": [list(map(int, row)) for row in p.strokes.tolist()]}})
    return {
        "object": "icd_example_vector", "icd_version": "1.0", "generator": "penapp.vectors",
        "evidence_status": "SYNTHETIC interoperability vector (writer and reader of this package)",
        "conventions": ["all multi-byte fields little-endian, CRC fields included",
                        "record CRC = CRC-16/CCITT-FALSE over type, length and payload",
                        "stroke sample phi_raw = round(phi / 2 deg), theta_raw = round(theta / 0.5 deg)",
                        "event 0x0009 is logged after the wrap with arg = wraps since session start",
                        "unknown record types with a valid CRC are kept as raw records"],
        "crc_check": {"input_ascii": "123456789", "crc16_ccitt_false": f"0x{crc16_ccitt_false(b'123456789'):04X}"},
        "header": {**HEADER.to_json(), "bytes_hex": data[:HEADER_SIZE].hex(),
                   "header_crc": f"0x{int.from_bytes(data[34:36], 'little'):04X}"},
        "n_bytes": len(data),
        "records": records,
        "corruption_cases": cases,
    }


__all__ = ["example_log", "example_records", "describe", "HEADER", "encode_record"]
