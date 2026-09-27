#!/usr/bin/env python3
"""Per-module size report of the linked nRF5340 image.

Parses the GNU ld map file (after --gc-sections, so only kept input sections
count) and sums the input-section sizes per object file into text (.text,
.rodata, vectors: flash), data (.data: flash image + RAM) and bss (RAM).
Totals are cross-checked against `arm-none-eabi-size` on the ELF.
Evidence status: build artefact measurement (sizes of this build; no
timing or hardware claim).
Usage: size_report.py --elf X.elf --map X.map --size arm-none-eabi-size --out report.txt
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

SEC_RE = re.compile(r"^ (\.[\w.\-]+|COMMON)\s*(?:(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\S.*))?$")
CONT_RE = re.compile(r"^\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\S.*)$")


def category(sec: str):
    if sec.startswith((".text", ".rodata", ".isr_vector", ".ARM.exidx", ".glue", ".vfp11", ".v4_bx", ".iplt",
                       ".rel.iplt", ".igot")):
        return "text"
    if sec.startswith((".data", ".ramfunc")):
        return "data"
    if sec.startswith((".bss", "COMMON")):
        return "bss"
    return None


def module_name(path: str):
    path = path.strip()
    m = re.match(r".*/(lib[\w+-]+)\.a\(([^)]+)\)$", path)
    if m:
        return m.group(1)          # libc_nano, libm, libgcc ...
    base = os.path.basename(path)
    parts = path.split("/build/arm/")
    return parts[1] if len(parts) == 2 else base


def parse_map(path):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("Linker script and memory map"))
    except StopIteration:
        start = 0
    mods = {}
    pending = None
    for l in lines[start:]:
        if l.startswith("OUTPUT(") or l.startswith("LOAD "):
            continue
        m = SEC_RE.match(l)
        if m:
            sec, addr, size, obj = m.groups()
            if addr is None:
                pending = sec
                continue
            pending = None
        else:
            c = CONT_RE.match(l)
            if not (c and pending):
                pending = None
                continue
            sec, (addr, size, obj) = pending, c.groups()
            pending = None
        cat = category(sec)
        if cat is None or int(size, 16) == 0 or int(addr, 16) == 0 and cat != "text":
            continue
        if obj.startswith("*") or "load address" in obj:
            continue
        mod = module_name(obj)
        d = mods.setdefault(mod, {"text": 0, "data": 0, "bss": 0})
        d[cat] += int(size, 16)
    return mods


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--size", default="arm-none-eabi-size")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    mods = parse_map(a.map)
    size_out = subprocess.run([a.size, "-A", a.elf], capture_output=True, text=True, check=True).stdout
    berk = subprocess.run([a.size, "-B", a.elf], capture_output=True, text=True, check=True).stdout
    tot_line = berk.strip().splitlines()[-1].split()
    elf_text, elf_data, elf_bss = int(tot_line[0]), int(tot_line[1]), int(tot_line[2])
    gcc = subprocess.run(["arm-none-eabi-gcc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    order = sorted(mods.items(), key=lambda kv: (not kv[0].startswith("core/"), not kv[0].startswith("port/"), kv[0]))
    out = []
    out.append("nRF5340 application-core image: per-module size after --gc-sections")
    out.append("Evidence status: BUILD ARTEFACT (compile/link only; not run on hardware)")
    out.append(f"toolchain: {gcc}")
    out.append("flags: -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=hard -O2 -ffunction-sections "
               "-fdata-sections -fno-math-errno; link --gc-sections, newlib-nano, nosys")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out.append(f"elf: {os.path.relpath(os.path.abspath(a.elf), repo)}")
    out.append(f"generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    out.append("")
    hdr = f"{'module':<40s} {'text':>8s} {'data':>7s} {'bss':>8s} {'flash':>8s} {'RAM':>8s}"
    out.append(hdr)
    out.append("-" * len(hdr))
    sums = {"text": 0, "data": 0, "bss": 0}
    groups = {"core": {"text": 0, "data": 0, "bss": 0}, "port": {"text": 0, "data": 0, "bss": 0},
              "libraries": {"text": 0, "data": 0, "bss": 0}}
    for mod, d in order:
        out.append(f"{mod:<40s} {d['text']:8d} {d['data']:7d} {d['bss']:8d} {d['text'] + d['data']:8d} "
                   f"{d['data'] + d['bss']:8d}")
        for k in sums:
            sums[k] += d[k]
        g = "core" if mod.startswith("core/") else ("port" if mod.startswith("port/") else "libraries")
        for k in sums:
            groups[g][k] += d[k]
    out.append("-" * len(hdr))
    for g, d in groups.items():
        out.append(f"{'subtotal ' + g:<40s} {d['text']:8d} {d['data']:7d} {d['bss']:8d} {d['text'] + d['data']:8d} "
                   f"{d['data'] + d['bss']:8d}")
    out.append(f"{'sum of input sections':<40s} {sums['text']:8d} {sums['data']:7d} {sums['bss']:8d} "
               f"{sums['text'] + sums['data']:8d} {sums['data'] + sums['bss']:8d}")
    out.append(f"{'ELF (arm-none-eabi-size -B)':<40s} {elf_text:8d} {elf_data:7d} {elf_bss:8d} "
               f"{elf_text + elf_data:8d} {elf_data + elf_bss:8d}")
    out.append("")
    out.append("ELF bss includes the 16 kB main stack reserved by the linker script (.stack); the")
    out.append("difference between the ELF and the sum of input sections is alignment padding and the stack.")
    out.append("Budgets (nRF5340 application core, VERIFY): 1024 kB flash, 512 kB RAM.")
    out.append(f"Flash use {100.0 * (elf_text + elf_data) / (1024 * 1024):.2f} %, RAM use "
               f"{100.0 * (elf_data + elf_bss) / (512 * 1024):.2f} % (incl. stack).")
    out.append("")
    out.append("arm-none-eabi-size -A:")
    out += ["  " + l for l in size_out.strip().splitlines()]
    txt = "\n".join(out) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
