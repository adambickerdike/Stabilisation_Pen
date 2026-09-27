#!/usr/bin/env python3
"""Run the Cortex-M33 unit-test image on QEMU mps2-an505 and write the report.

Two runs of build/qemu/pen_tests_an505.elf (tests + start-up of
port/qemu_an505/, semihosting):
  1. the unit tests (same cases as the host build, read the golden vectors
     from tests/vectors through semihosting file I/O);
  2. `--bench` under `-icount shift=N`: instruction counts of
     pen_app_current_isr() and pen_app_stage_tick() on the closed-loop
     scenario of port/qemu_an505/bench_an505.c.
Evidence status: QEMU EXECUTION. QEMU is a functional emulator, not
cycle-accurate; the bench reports executed INSTRUCTIONS (icount virtual
clock), not cycles, and nothing here is a hardware measurement.

Usage (from firmware/): run_qemu.py --qemu qemu-system-arm --elf build/qemu/pen_tests_an505.elf
                        --out ../results/firmware/qemu_report.txt [--timeout 5400] [--shift 7]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import re
import subprocess
import sys
import time

FW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(FW)


def qemu_cmd(qemu, elf, args, icount_shift=None):
    sh = "enable=on,target=native," + ",".join("arg=" + a for a in ["pen_tests"] + args)
    cmd = [qemu, "-M", "mps2-an505", "-nographic", "-monitor", "none", "-serial", "null",
           "-semihosting-config", sh]
    if icount_shift is not None:
        cmd += ["-icount", f"shift={icount_shift},align=off,sleep=off"]
    return cmd + ["-kernel", elf]


def run(cmd, timeout):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=FW, capture_output=True, text=True, timeout=timeout)
        out, rc, to = p.stdout + p.stderr, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")) + \
              (e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""))
        rc, to = None, True
    return out, rc, to, time.time() - t0


def first_line(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0]
    except (OSError, IndexError):
        return "unavailable"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default="qemu-system-arm")
    ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=5400.0)
    ap.add_argument("--shift", type=int, default=7)
    ap.add_argument("--no-bench", action="store_true")
    ap.add_argument("--filter", default=None, help="run only the test cases containing this string")
    a = ap.parse_args()

    elf = os.path.abspath(a.elf)
    sha = hashlib.sha256(open(elf, "rb").read()).hexdigest()[:16]
    t_args = ["tests/vectors"] + ([a.filter] if a.filter else [])
    cmd_t = qemu_cmd(a.qemu, elf, t_args)
    out_t, rc_t, to_t, dt_t = run(cmd_t, a.timeout)
    lines = out_t.splitlines()
    cases = []
    for l in lines:
        m = re.match(r"^\[ (FAIL| OK ) \] (\S+) \((\d+) checks\)", l)
        if m:
            cases.append((m.group(2), m.group(1).strip(), int(m.group(3))))
    summ = next((l for l in lines if l.startswith("SUMMARY:")), None)
    fatal = [l for l in lines if l.startswith("FATAL")]
    ok = summ is not None and not to_t and " 0 failed;" in summ and not fatal

    bench_lines, rc_b, to_b, dt_b, cmd_b = [], None, False, 0.0, None
    if not a.no_bench:
        cmd_b = qemu_cmd(a.qemu, elf, ["--bench"], icount_shift=a.shift)
        out_b, rc_b, to_b, dt_b = run(cmd_b, a.timeout)
        bench_lines = [l for l in out_b.splitlines() if l.startswith("BENCH") or l.startswith("FATAL")]

    r = []
    r.append("QEMU execution report: firmware unit tests on an emulated Cortex-M33 (mps2-an505)")
    r.append("Evidence status: QEMU EXECUTION (functional emulation of the Arm AN505 FPGA image; NOT cycle-accurate,")
    r.append("NOT the nRF5340, NOT hardware). Timing-related numbers below are instruction counts, not cycles.")
    r.append(f"generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    r.append(f"qemu: {first_line([a.qemu, '--version'])}")
    r.append(f"toolchain: {first_line(['arm-none-eabi-gcc', '--version'])}")
    r.append(f"image: {os.path.relpath(elf, ROOT)} (sha256 {sha}); core + tests compiled with -O2 -mcpu=cortex-m33 "
             "-mfpu=fpv5-sp-d16 -mfloat-abi=hard (the nRF5340 flags), newlib + rdimon semihosting, "
             "port/host/hal_host.c as HAL")
    r.append("")
    r.append("1. Unit tests")
    r.append("   command (cwd firmware/): " + " ".join(cmd_t))
    r.append(f"   host wall-clock of the emulation: {dt_t:.1f} s (not target time); QEMU exit status: "
             f"{'TIMEOUT' if to_t else rc_t}")
    r.append(f"   result: {summ if summ else 'no SUMMARY line (run incomplete)'}")
    if fatal:
        r += ["   " + l for l in fatal]
    r.append(f"   verdict: {'PASS' if ok else 'FAIL / INCOMPLETE'} ({len(cases)} cases reported)")
    for name, st, n in cases:
        r.append(f"     {'ok  ' if st == 'OK' else 'FAIL'} {name} ({n} checks)")
    r.append("   Notes: the test code keeps its double-precision references (soft-float on this FPU-SP core);")
    r.append("   the control core itself is float32 and runs on the FPv5-SP hardware. Tolerances are the same as")
    r.append("   on the host; every value the tests print on the target is in the log appendix below.")
    r.append("")
    r.append("2. Instruction-count estimate (bench_an505.c)")
    if a.no_bench:
        r.append("   not run (--no-bench)")
    else:
        r.append("   command (cwd firmware/): " + " ".join(cmd_b))
        r.append(f"   host wall-clock: {dt_b:.1f} s; QEMU exit status: {'TIMEOUT' if to_b else rc_b}")
        r.append("   Method: -icount makes QEMU's virtual clock advance a fixed 2^shift ns per executed guest")
        r.append("   instruction; SysTick (processor clock) then counts instructions. The ticks-per-instruction")
        r.append("   ratio is calibrated with a loop of known length and the empty-measurement overhead is")
        r.append("   subtracted. Budgets are cycles of the 128 MHz nRF5340 application core (3200 per 25 us PWM")
        r.append("   period, 64000 per 500 us stage tick); comparing instructions with cycles assumes CPI = 1,")
        r.append("   so every percentage below is a LOWER BOUND of the real load.")
        r += ["   " + l for l in bench_lines] if bench_lines else ["   no BENCH output"]
        r.append("   Not included: exception entry/exit (12 cycles each way), FP lazy stacking (up to ~17 words),")
        r.append("   the nRF5340 handlers (SAADC END / EGU0, event clears, the 100 Hz SAADC reconfiguration), the")
        r.append("   TMAG5170 / IMU / optical SPI reads in the stage task, flash wait states and cache misses")
        r.append("   (VERIFY on silicon), multi-cycle instructions (VDIV.F32 / VSQRT.F32 14 cycles, loads 2,")
        r.append("   taken branches 2-4), the ML inference itself (no model linked; the window export is included),")
        r.append("   and the USB CDC log drain. Bring-up must measure real cycles with the DWT cycle counter and a")
        r.append("   GPIO toggle on a logic analyser (README, open issues).")
    r.append("")
    r.append("Appendix A: full unit-test log (QEMU stdout)")
    r += ["  " + l for l in lines]
    txt = "\n".join(r) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write(txt)
    print("\n".join(r[:40]))
    if not a.no_bench:
        print("\n".join(bench_lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
