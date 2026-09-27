#!/usr/bin/env python3
"""Cross-check KiCad's exported netlist against the generator's intended netlist.

The generator records, for every net, the pins it attached a label to
(electronics/kicad/intended_netlist.json).  KiCad resolves connectivity on its
own from label positions; if a label missed its pin, or two labels collided,
the two netlists differ.  This check is what makes the generated schematic
trustworthy as a netlist, independent of how it looks.

Usage: python3 check_netlist.py [netlist.net] [intended.json]
Exit 0 when identical (ignoring power-flag symbols and single-pin unconnected nets).
"""
import json
import os
import sys

from sexpr import find, find_all, parse

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.join(os.path.dirname(HERE), "kicad")


def kicad_nets(path):
    tree = parse(open(path, encoding="utf-8").read())[0]
    nets = {}
    for net in find_all(find(tree, "nets"), "net"):
        name = str(find(net, "name")[1]).lstrip("/")
        pins = []
        for node in find_all(net, "node"):
            ref = str(find(node, "ref")[1])
            if ref.startswith("#"):
                continue
            pins.append(f"{ref}.{find(node, 'pin')[1]}")
        if name.startswith("unconnected-") or not pins:
            continue
        nets[name] = sorted(pins)
    return nets


def main():
    net_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KDIR, "pen_research.net")
    int_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(KDIR, "intended_netlist.json")
    kn = kicad_nets(net_path)
    it = {k: sorted(v) for k, v in json.load(open(int_path)).items()}
    ok = True
    for name in sorted(set(kn) | set(it)):
        a, b = set(kn.get(name, [])), set(it.get(name, []))
        if a != b:
            ok = False
            print(f"MISMATCH {name}: only in KiCad {sorted(a - b)}; only intended {sorted(b - a)}")
    n_pins = sum(len(v) for v in it.values())
    print(f"{'PASS' if ok else 'FAIL'}: {len(it)} intended nets, {len(kn)} KiCad nets, {n_pins} connected pins compared")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
