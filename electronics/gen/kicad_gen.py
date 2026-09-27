"""Generate editable KiCad schematics from a declarative design specification.

Each part instance is placed on its sheet and every pin receives either a
global label carrying its net name (placed exactly on the pin's electrical
connection point) or an explicit no-connect flag.  Symbols are copied from the
installed official KiCad libraries (flattening `extends`), so pin numbers come
from maintained library data, not from hand entry.

Outputs a root schematic with hierarchical sheet symbols and one .kicad_sch per
sheet, plus an intended-netlist JSON used to cross-check KiCad's own netlist
export (electronics/gen/check_netlist.py).
"""
from __future__ import annotations

import copy
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sexpr import Q, dumps, find, find_all, parse

LIBDIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
PROJECT = "pen_research"


def uid():
    return Q(str(uuid.uuid4()))


# ------------------------------------------------------------------ library
class SymbolLib:
    def __init__(self, libdir=LIBDIR):
        self.libdir = libdir
        self.cache = {}
        self.version = None

    def _load(self, lib):
        if lib not in self.cache:
            with open(os.path.join(self.libdir, f"{lib}.kicad_sym"), encoding="utf-8") as f:
                tree = parse(f.read())[0]
            v = find(tree, "version")
            self.version = int(v[1]) if v else 20211014
            self.cache[lib] = {s[1]: s for s in find_all(tree, "symbol")}
        return self.cache[lib]

    def flat(self, lib, name):
        """Flattened symbol node named `name` (no library prefix)."""
        syms = self._load(lib)
        if name not in syms:
            raise KeyError(f"{lib}:{name} not found")
        s = syms[name]
        ext = find(s, "extends")
        if ext is None:
            return copy.deepcopy(s)
        parent = self.flat(lib, ext[1])
        node = copy.deepcopy(parent)
        node[1] = Q(name)
        for sub in find_all(node, "symbol"):
            sub[1] = Q(re.sub("^" + re.escape(str(ext[1])) + "_", name + "_", str(sub[1])))
        node[:] = [x for x in node if not (isinstance(x, list) and x and x[0] == "property")]
        # insert child properties after header items
        props = [copy.deepcopy(x) for x in find_all(s, "property")]
        idx = next((i for i, x in enumerate(node) if isinstance(x, list) and x and x[0] == "symbol"), len(node))
        node[idx:idx] = props
        return node

    def embedded(self, lib, name):
        node = self.flat(lib, name)
        node[1] = Q(f"{lib}:{name}")
        return node

    def pins(self, lib, name, unit=1):
        node = self.flat(lib, name)
        out = []
        for sub in find_all(node, "symbol"):
            m = re.match(r"^(.*)_(\d+)_(\d+)$", str(sub[1]))
            if not m:
                continue
            u, st = int(m.group(2)), int(m.group(3))
            if u not in (0, unit) or st not in (0, 1):
                continue
            for p in find_all(sub, "pin"):
                at = find(p, "at")
                nm = find(p, "name")
                nu = find(p, "number")
                hidden = ("hide" in p) or any(isinstance(x, list) and x[:2] == ["hide", "yes"] for x in p)
                out.append({"type": str(p[1]), "x": float(at[1]), "y": float(at[2]),
                            "angle": float(at[3]) if len(at) > 3 else 0.0,
                            "name": str(nm[1]), "number": str(nu[1]), "hidden": hidden})
        return out


# ------------------------------------------------------------------ design model
@dataclass
class Part:
    ref: str
    lib_id: str               # "Lib:Name"
    value: str
    footprint: str = ""
    nets: Dict[str, str] = field(default_factory=dict)   # pin name or "#number" -> net ('NC' = no-connect)
    fields: Dict[str, str] = field(default_factory=dict)
    dnp: bool = False
    unit: int = 1


@dataclass
class Sheet:
    name: str
    file: str
    title: str
    parts: List[Part] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    pwr_flags: List[str] = field(default_factory=list)
    paper: str = "A2"


PAPER = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594)}


def _prop(name, value, x, y, hide=False, v8=True, justify=None):
    effects = ["effects", ["font", ["size", "1.27", "1.27"]]]
    if justify:
        effects.append(["justify", justify])
    if hide:
        effects.append(["hide", "yes"] if v8 else "hide")
    return ["property", Q(name), Q(value), ["at", f"{x:.2f}", f"{y:.2f}", "0"], effects]


class Generator:
    def __init__(self, lib: SymbolLib, title="Active stabilisation pen - research electronics Rev A"):
        self.lib = lib
        self.title = title
        self.root_uuid = str(uuid.uuid4())
        self.intended: Dict[str, List[str]] = {}
        self.issues: List[str] = []

    # --------------------------------------------------------------- placement
    def _bbox(self, pins):
        xs = [p["x"] for p in pins] or [0]
        ys = [p["y"] for p in pins] or [0]
        return min(xs), max(xs), min(ys), max(ys)

    def _layout(self, parts, W):
        """Row-wrapped placement; returns [(part, pins, ox, oy, xmin, xmax, ymin, ymax)] and the used height."""
        x0, y0 = 30.0, 35.0
        x, y, row_h = x0, y0, 0.0
        placed = []
        for part in parts:
            lib, name = part.lib_id.split(":", 1)
            pins = self.lib.pins(lib, name, part.unit)
            if not pins:
                placed.append((part, pins, 0, 0, 0, 0, 0, 0))
                continue
            xmin, xmax, ymin, ymax = self._bbox(pins)
            w = (xmax - xmin) + 55.0
            h = (ymax - ymin) + 26.0
            if x + w > W - 25 and x > x0:
                x = x0
                y += row_h + 8
                row_h = 0.0
            # grid-align origin (2.54 mm) so pins land on grid
            ox = round((x - xmin + 22) / 2.54) * 2.54
            oy = round((y + ymax + 9) / 2.54) * 2.54
            x += w
            row_h = max(row_h, h)
            placed.append((part, pins, ox, oy, xmin, xmax, ymin, ymax))
        return placed, y + row_h

    def build_sheet(self, sheet: Sheet, sheet_uuid: str, page: int):
        v8 = (self.lib.version or 0) >= 20231120
        # smallest paper that holds the parts above the notes and title block
        for paper in ("A4", "A3", "A2", "A1"):
            W, H = PAPER[paper]
            placed, used = self._layout(sheet.parts, W)
            if used < H - 45 - 4.0 * len(sheet.notes):
                break
        sheet.paper = paper
        items = []
        lib_syms = {}
        for part, pins, ox, oy, xmin, xmax, ymin, ymax in placed:
            lib, name = part.lib_id.split(":", 1)
            if not pins:
                self.issues.append(f"{sheet.name}:{part.ref} has no pins for {part.lib_id}")
                continue
            lib_syms[part.lib_id] = self.lib.embedded(lib, name)
            sym = ["symbol", ["lib_id", Q(part.lib_id)], ["at", f"{ox:.2f}", f"{oy:.2f}", "0"], ["unit", str(part.unit)],
                   ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "yes" if part.dnp else "no"],
                   ["uuid", uid()],
                   _prop("Reference", part.ref, ox, oy + ymin * -1 - 0 - (ymax - ymin) - 3, v8=v8),
                   _prop("Value", part.value, ox, oy - ymin + 3, v8=v8),
                   _prop("Footprint", part.footprint, ox, oy, hide=True, v8=v8),
                   _prop("Datasheet", part.fields.get("Datasheet", "~"), ox, oy, hide=True, v8=v8)]
            for k, v in part.fields.items():
                if k != "Datasheet":
                    sym.append(_prop(k, v, ox, oy, hide=True, v8=v8))
            seen_numbers = set()
            for p in pins:
                if p["number"] in seen_numbers:
                    continue
                seen_numbers.add(p["number"])
                sym.append(["pin", Q(p["number"]), ["uuid", uid()]])
            sym.append(["instances", ["project", Q(PROJECT), ["path", Q(f"/{self.root_uuid}/{sheet_uuid}"),
                                                               ["reference", Q(part.ref)], ["unit", str(part.unit)]]]])
            items.append(sym)
            # connections
            used = set()
            for p in pins:
                key_num = "#" + p["number"]
                net = part.nets.get(key_num, part.nets.get(p["name"]))
                px, py = ox + p["x"], oy - p["y"]
                if net is None:
                    if p["type"] == "no_connect":
                        continue
                    if p["hidden"] and p["type"] in ("power_in",):
                        self.issues.append(f"{part.ref}: hidden power pin {p['name']} unconnected")
                    net = "NC"
                    self.issues.append(f"{part.ref}: pin {p['number']} ({p['name']}) unmapped -> NC")
                used.add(p["name"])
                used.add(key_num)
                if net == "NC":
                    items.append(["no_connect", ["at", f"{px:.2f}", f"{py:.2f}"], ["uuid", uid()]])
                    continue
                self.intended.setdefault(net, []).append(f"{part.ref}.{p['number']}")
                ang = (p["angle"] + 180.0) % 360.0
                just = {0.0: "left", 90.0: "left", 180.0: "right", 270.0: "right"}.get(ang, "left")
                items.append(["global_label", Q(net), ["shape", "passive"], ["at", f"{px:.2f}", f"{py:.2f}", f"{ang:g}"],
                              ["fields_autoplaced", "yes"] if v8 else ["fields_autoplaced"],
                              ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", just]], ["uuid", uid()],
                              ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", f"{px:.2f}", f"{py:.2f}", "0"],
                               ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"] if v8 else "hide"]]])
            for k in part.nets:
                if k not in used:
                    self.issues.append(f"{part.ref}: net mapping key '{k}' matched no pin")
        # power flags
        for i, net in enumerate(sheet.pwr_flags):
            fx = round((W - 35) / 2.54) * 2.54
            fy = round((H - 75 - 10 * i) / 2.54) * 2.54
            lib_syms["power:PWR_FLAG"] = self.lib.embedded("power", "PWR_FLAG")
            items.append(["symbol", ["lib_id", Q("power:PWR_FLAG")], ["at", f"{fx:.2f}", f"{fy:.2f}", "0"], ["unit", "1"],
                          ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", uid()],
                          _prop("Reference", f"#FLG{page:02d}{i:02d}", fx, fy - 3, hide=True, v8=v8),
                          _prop("Value", "PWR_FLAG", fx, fy + 3, v8=v8),
                          _prop("Footprint", "", fx, fy, hide=True, v8=v8), _prop("Datasheet", "~", fx, fy, hide=True, v8=v8),
                          ["pin", Q("1"), ["uuid", uid()]],
                          ["instances", ["project", Q(PROJECT), ["path", Q(f"/{self.root_uuid}/{sheet_uuid}"),
                                                                 ["reference", Q(f"#FLG{page:02d}{i:02d}")], ["unit", "1"]]]]])
            items.append(["global_label", Q(net), ["shape", "passive"], ["at", f"{fx:.2f}", f"{fy:.2f}", "180"],
                          ["fields_autoplaced", "yes"] if v8 else ["fields_autoplaced"],
                          ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "right"]], ["uuid", uid()],
                          ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", f"{fx:.2f}", f"{fy:.2f}", "0"],
                           ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"] if v8 else "hide"]]])
        # notes
        ny = H - 38.0 - 4.0 * len(sheet.notes)
        for j, note in enumerate(sheet.notes):
            items.append(["text", Q(note), ["exclude_from_sim", "no"], ["at", "20", f"{ny + 4.0 * j:.2f}", "0"],
                          ["effects", ["font", ["size", "1.6", "1.6"]], ["justify", "left", "bottom"]], ["uuid", uid()]])
        return lib_syms, items

    def write(self, sheets: List[Sheet], outdir: str, root_notes: List[str]):
        os.makedirs(outdir, exist_ok=True)
        v8 = (self.lib.version or 0) >= 20231120
        ver = "20231120" if v8 else "20230121"
        root_items = []
        for i, sh in enumerate(sheets):
            s_uuid = str(uuid.uuid4())
            lib_syms, items = self.build_sheet(sh, s_uuid, i + 2)
            doc = ["kicad_sch", ["version", ver], ["generator", Q("eeschema")]]
            if v8:
                doc.append(["generator_version", Q("8.0")])
            doc += [["uuid", uid()], ["paper", Q(sh.paper)],
                    ["title_block", ["title", Q(sh.title)], ["date", Q("2026-09-27")], ["rev", Q("A")],
                     ["company", Q("Active stabilisation pen programme")],
                     ["comment", "1", Q("RESEARCH ELECTRONICS - DEVELOPMENT DRAFT - NOT RELEASED FOR FABRICATION")],
                     ["comment", "2", Q("Generated by electronics/gen/design_revA.py; edit the spec or edit here in KiCad")]],
                    ["lib_symbols"] + list(lib_syms.values())] + items
            with open(os.path.join(outdir, sh.file), "w", encoding="utf-8") as f:
                f.write(dumps(doc) + "\n")
            col, row = i % 4, i // 4
            sx, sy = 30 + col * 95, 35 + row * 62
            root_items.append(["sheet", ["at", str(sx), str(sy)], ["size", "80", "45"],
                               ["fields_autoplaced", "yes"] if v8 else ["fields_autoplaced"],
                               ["stroke", ["width", "0.1524"], ["type", "solid"]], ["fill", ["color", "0", "0", "0", "0.0000"]],
                               ["uuid", Q(s_uuid)],
                               ["property", Q("Sheetname"), Q(sh.name), ["at", str(sx), str(sy - 1), "0"],
                                ["effects", ["font", ["size", "1.8", "1.8"]], ["justify", "left", "bottom"]]],
                               ["property", Q("Sheetfile"), Q(sh.file), ["at", str(sx), str(sy + 46), "0"],
                                ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "top"]]],
                               ["instances", ["project", Q(PROJECT), ["path", Q(f"/{self.root_uuid}"), ["page", Q(str(i + 2))]]]]])
        for j, note in enumerate(root_notes):
            root_items.append(["text", Q(note), ["exclude_from_sim", "no"], ["at", "30", f"{228 + 5.0 * j:.2f}", "0"],
                               ["effects", ["font", ["size", "2", "2"]], ["justify", "left", "bottom"]], ["uuid", uid()]])
        root = ["kicad_sch", ["version", ver], ["generator", Q("eeschema")]]
        if v8:
            root.append(["generator_version", Q("8.0")])
        root += [["uuid", Q(self.root_uuid)], ["paper", Q("A3")],
                 ["title_block", ["title", Q(self.title)], ["date", Q("2026-09-27")], ["rev", Q("A")],
                  ["company", Q("Active stabilisation pen programme")],
                  ["comment", "1", Q("RESEARCH ELECTRONICS - DEVELOPMENT DRAFT - NOT RELEASED FOR FABRICATION")]],
                 ["lib_symbols"]] + root_items + [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]]]
        with open(os.path.join(outdir, f"{PROJECT}.kicad_sch"), "w", encoding="utf-8") as f:
            f.write(dumps(root) + "\n")
        pro = {"meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
               "sheets": [[self.root_uuid, "Root"]] , "text_variables": {}}
        with open(os.path.join(outdir, f"{PROJECT}.kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        with open(os.path.join(outdir, "intended_netlist.json"), "w") as f:
            json.dump({k: sorted(v) for k, v in sorted(self.intended.items())}, f, indent=1)
        return self.issues
