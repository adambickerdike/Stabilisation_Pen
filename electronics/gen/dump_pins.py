#!/usr/bin/env python3
"""Print pin number, name and electrical type of library symbols.

Usage: python3 dump_pins.py Lib:Symbol [Lib:Symbol ...]
Used when writing design_revA.py so net maps use library pin names.
"""
import sys

from kicad_gen import SymbolLib

lib = SymbolLib()
for arg in sys.argv[1:]:
    l, n = arg.split(":", 1)
    pins = lib.pins(l, n)
    print(f"== {arg}  ({len(pins)} pins)")
    for p in sorted(pins, key=lambda p: (len(p['number']), p['number'])):
        print(f"  {p['number']:>5} {p['name']:<18} {p['type']:<14}{' hidden' if p['hidden'] else ''}")
