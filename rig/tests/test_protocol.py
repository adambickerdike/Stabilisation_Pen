"""Frame format, CRC, parser robustness, sync-pulse decoding and the logger round trip (SIM)."""
import os
import tempfile

import numpy as np

from rig import convert, logger, protocol, sync, synth


def test_sizes_and_crc():
    assert protocol.SIZE[protocol.T_SAMPLE] == 68
    assert protocol.SIZE[protocol.T_EVENT] == 20
    assert protocol.SIZE[protocol.T_IMU] == 28
    assert protocol.SIZE[protocol.T_PAGE] == 20
    assert protocol.crc16_ccitt(b"123456789") == 0x29B1
    assert protocol.crc16_fast(b"123456789") == 0x29B1


def test_round_trip_and_corruption():
    d = synth.daq_stream(n=1200)
    p = protocol.parse_bytes(d["bytes"])
    a = p.arrays()
    assert list(a["samples"]["seq"]) == d["_truth"]["good_seq"]
    assert p.stats["crc_errors"] > 0
    assert p.config["f_cpu"] == "600000000"
    # chunked feeding gives the same result
    sp = protocol.StreamParser()
    for i in range(0, len(d["bytes"]), 37):
        sp.feed(d["bytes"][i:i + 37])
    assert len(sp.out.samples) == len(p.samples)


def test_temperature_event():
    raw = (int(round(-12.5 / 0.0078125)) << 5) & 0xFFFFFF
    ch, c = protocol.temp_event_to_celsius((3 << 24) | raw)
    assert ch == 3 and abs(c + 12.5) < 1e-9


def test_sync_fit():
    e = synth.sync_edges(duration_s=120.0)
    tr, n = sync.decode_widths(e["dev_rise"], e["dev_fall"])
    tr_d, n_d = sync.decode_widths(e["daq_rise"], e["daq_fall"])
    assert len(n) == len(n_d) > 100
    fit = sync.fit_clock(tr, n, tr_d, n_d)
    assert fit["meets_50us"]
    assert abs(fit["drift_ppm"] - e["_truth"]["drift_ppm"]) < 1.0


def test_logger_replay_and_units():
    d = synth.daq_stream(n=800, corrupt_every=0)
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "in.bin")
        with open(raw, "wb") as f:
            f.write(d["bytes"])
        out = os.path.join(tmp, "s")
        info = logger.replay(raw, out)
        assert info["stats"]["missing_frames"] == 1          # frame 500 was dropped on purpose
        s = logger.load_session(out)
        u = convert.to_units(s, convert.CHANNEL_MAPS["R9"])
        dt = np.median(np.diff(u["t_s"]))
        assert abs(dt - 1 / 4000) < 1e-9
        # ADC times lead the encoder latch by the sinc3 group delay (1.5 output periods)
        assert np.allclose(u["t_s"] - u["t_adc_s"], 1.5 / 4000)
        assert "F_a_mVV" in u and "x_enc" in u
