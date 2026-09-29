"""The firmware header frames exactly as rig/protocol.py does, and rig_daq.ino parses as C++ against stubs.

Both tests need g++ and are skipped without it. Neither is a Teensy build: the firmware has NOT been compiled
for the target or run (docs/measurement_rig.md section 1.3)."""
import os
import shutil
import subprocess
import tempfile

import pytest

from rig import PKG_DIR, protocol

FW = os.path.join(PKG_DIR, "firmware")
GXX = shutil.which("g++")


@pytest.mark.skipif(GXX is None, reason="g++ not available")
def test_header_frames_match_python():
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "vectors")
        subprocess.run([GXX, "-std=gnu++17", "-O1", "-o", exe, os.path.join(FW, "host_check", "proto_vectors.cpp")],
                       check=True, capture_output=True)
        out = subprocess.run([exe], check=True, capture_output=True, text=True).stdout.split()
    assert out[0] == "crc=0x29B1"
    assert out[1] == protocol.pack_sample(7, 123456789012, [-1000 * i + 5 for i in range(8)],
                                          [100000 * i - 3 for i in range(4)], cmd=-42, flags=0x93, nadc=8).hex()
    assert out[2] == protocol.pack_event(3, 99, protocol.EV_TEMP, 0x02000320).hex()
    assert out[3] == protocol.pack_imu(1, 5, [-2, 0, 0], [0, 0, 300], 25).hex()


@pytest.mark.skipif(GXX is None, reason="g++ not available")
def test_ino_parses_against_stubs():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "check.cpp")
        with open(src, "w") as f:
            f.write('#include "Arduino_stub.h"\n')
            with open(os.path.join(FW, "rig_daq", "rig_daq.ino")) as g:
                f.write(g.read())
            f.write("\nint main() { setup(); loop(); return 0; }\n")
        r = subprocess.run([GXX, "-std=gnu++17", "-Wall", "-Wno-unused-parameter", "-fsyntax-only",
                            "-I", os.path.join(FW, "host_check"), "-I", os.path.join(FW, "rig_daq"), src],
                           capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
