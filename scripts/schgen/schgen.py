# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal KiCad schematic generator for the Nexus boards.

A sheet is described in Python: parts with explicit positions and a net per
pin. Every pin gets a short wire stub ending in a power symbol, a global
label or a local label, so connectivity never depends on drawn wires.
After writing, `verify()` exports KiCad's own netlist and compares it with
the intended nets, so a mistake in pin geometry cannot go unnoticed.

UUIDs are derived from stable part keys (uuid5), so regenerating a sheet
keeps the links to the PCB.
"""
import pathlib
import re
import subprocess
import uuid

KICAD_SYM = pathlib.Path("/usr/share/kicad/symbols")
ROOT = pathlib.Path(__file__).resolve().parents[2]
NS = uuid.UUID("6e657875-732d-7363-6867-656e00000000")  # "nexus-schgen"
GRID = 1.27
GROUNDS = ("GND", "AGND")
STUB = 2.54
STUB_IC = 5.08
VERSION = "20231120"


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


# --------------------------------------------------------------- library --
class Library:
    """Loads symbol definitions from KiCad and the project library."""

    def __init__(self):
        self.cache = {}

    def _file(self, lib):
        if lib == "nexus":
            return ROOT / "lib" / "nexus.kicad_sym"
        return KICAD_SYM / f"{lib}.kicad_sym"

    @staticmethod
    def _block(text, name):
        m = re.search(r'^\t\(symbol "' + re.escape(name) + r'"\n.*?^\t\)\n',
                      text, re.M | re.S)
        return m.group(0) if m else None

    def get(self, lib_id):
        if lib_id in self.cache:
            return self.cache[lib_id]
        lib, name = lib_id.split(":", 1)
        text = self._file(lib).read_text()
        block = self._block(text, name)
        if block is None:
            raise KeyError(lib_id)
        parent = re.search(r'\(extends "([^"]+)"\)', block)
        if parent:
            base = self._block(text, parent.group(1))
            pname = parent.group(1)
            body = base.replace(f'(symbol "{pname}"', f'(symbol "{name}"', 1)
            body = re.sub(r'\(symbol "' + re.escape(pname) + r'_(\d+)_(\d+)"',
                          lambda m: f'(symbol "{name}_{m.group(1)}_{m.group(2)}"',
                          body)
            # child properties override the parent's
            for key, val in re.findall(r'\(property "([^"]+)" "([^"]*)"', block):
                body = re.sub(r'(\(property "' + re.escape(key) + r'" )"[^"]*"',
                              lambda m: m.group(1) + '"' + val.replace('\\', '\\\\') + '"',
                              body, count=1)
            block = body
        # embedded name carries the library prefix (top level only)
        emb = block.replace(f'\t(symbol "{name}"', f'\t(symbol "{lib_id}"', 1)
        pins = {}
        for unit_m in re.finditer(r'\(symbol "' + re.escape(name) +
                                  r'_(\d+)_(\d+)"(.*?)\n\t\t\)', block, re.S):
            unit = int(unit_m.group(1))
            for pm in re.finditer(
                    r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)'
                    r'.*?\(name "([^"]*)".*?\(number "([^"]*)"',
                    unit_m.group(3), re.S):
                pins.setdefault(pm.group(6), []).append(dict(
                    unit=unit, type=pm.group(1), x=float(pm.group(2)),
                    y=float(pm.group(3)), a=float(pm.group(4) or 0),
                    name=pm.group(5)))
        is_power = "(power" in block.split("(property")[0]
        field_at = {}
        for fm in re.finditer(r'\(property "(Reference|Value)" "[^"]*"\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', block):
            field_at[fm.group(1)] = (float(fm.group(2)), float(fm.group(3)), float(fm.group(4)))
        sym = dict(lib_id=lib_id, text=emb, pins=pins, power=is_power, field_at=field_at,
                   props=dict(re.findall(r'\(property "([^"]+)" "([^"]*)"',
                                         block)))
        self.cache[lib_id] = sym
        return sym


LIB = Library()


# ----------------------------------------------------------------- model --
class Part:
    def __init__(self, sheet, key, lib_id, value, at, rot=0, nets=None,
                 fp=None, lcsc="", mpn="", assembly="JLC", prefix=None,
                 unit=1, dnp=False, label_side=None):
        self.sheet, self.key, self.lib_id = sheet, key, lib_id
        self.value, self.rot, self.unit, self.dnp = value, rot, unit, dnp
        self.at = (snap(at[0]), snap(at[1]))
        self.sym = LIB.get(lib_id)
        self.fp = fp if fp is not None else self.sym["props"].get("Footprint", "")
        self.lcsc, self.mpn, self.assembly = lcsc, mpn, assembly
        self.nets = dict(nets or {})
        self.prefix = prefix or self.sym["props"].get("Reference", "U")
        self.ref = None
        self.uuid = uid(sheet.board, sheet.name, key)
        for pin in self.nets:
            if pin not in self.sym["pins"]:
                raise KeyError(f"{lib_id} has no pin {pin} ({key})")

    def pin_geom(self, num):
        """Return (x, y, outward_dx, outward_dy) in schematic coordinates."""
        cands = [p for p in self.sym["pins"][num] if p["unit"] in (0, self.unit)]
        p = cands[0]
        import math
        r = math.radians(self.rot)
        x = p["x"] * math.cos(r) - p["y"] * math.sin(r)
        y = p["x"] * math.sin(r) + p["y"] * math.cos(r)
        # pin direction (towards the body) in lib coords, rotated
        a = math.radians(p["a"] + self.rot)
        bx, by = math.cos(a), math.sin(a)
        sx, sy = self.at[0] + x, self.at[1] - y
        return snap(sx), snap(sy), round(-bx), round(by)  # outward, y flipped


class Sheet:
    def __init__(self, board, name, title, paper="A3", page=2):
        self.board, self.name, self.title = board, name, title
        self.paper, self.page = paper, page
        self.parts, self.texts, self.extra = [], [], []
        self.uuid = uid(board, "sheet", name)

    def part(self, key, lib_id, value, at, **kw):
        p = Part(self, key, lib_id, value, at, **kw)
        self.parts.append(p)
        return p

    def text(self, s, at, size=1.8):
        self.texts.append((s, (snap(at[0]), snap(at[1])), size))


# ---------------------------------------------------------------- writer --
def q(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + s + '"'


def eff(hide=False, justify=None, size=1.27):
    j = f" (justify {justify})" if justify else ""
    h = " (hide yes)" if hide else ""
    return f"(effects (font (size {size} {size})){j}{h})"


class Board:
    def __init__(self, name, title, rev="A", date="2026-11-17"):
        self.name, self.title, self.rev, self.date = name, title, rev, date
        self.root_uuid = uid(name, "root")
        self.sheets = []
        self.power_nets = set()
        self.counters = {}
        self.pwr_count = 0

    def sheet(self, name, title):
        s = Sheet(self.name, name, title, page=len(self.sheets) + 2)
        self.sheets.append(s)
        return s

    # -- references: sequential per prefix in sheet order
    def annotate(self):
        for s in self.sheets:
            for p in s.parts:
                n = self.counters.get(p.prefix, 0) + 1
                self.counters[p.prefix] = n
                p.ref = f"{p.prefix}{n}"

    def title_block(self, sheet_title):
        return (f'(title_block (title {q(self.title)}) (date {q(self.date)}) '
                f'(rev {q(self.rev)}) (company "Nexus") (comment 1 {q(sheet_title)}) '
                f'(comment 2 "CERN-OHL-S-2.0") (comment 3 "github.com/bertenvdb/nexus"))')

    def _symbol_instance(self, p, path, ref, value, at, rot, extra_props=()):
        x, y = at
        props = [
            f'(property "Reference" {q(ref)} (at {x + 2.54} {y - 1.27} 0) {eff(justify="left", hide=p is None)})',
        ]
        return props

    def write_sheet(self, s):
        out = []
        libs = {}
        items = []
        path = f"/{self.root_uuid}/{s.uuid}"
        for p in s.parts:
            libs[p.lib_id] = p.sym["text"]
            x, y = p.at
            import math
            def fpos(field, dflt):
                fx, fy, fa = p.sym["field_at"].get(field, dflt)
                r = math.radians(p.rot)
                rx = fx * math.cos(r) - fy * math.sin(r)
                ry = fx * math.sin(r) + fy * math.cos(r)
                ang = 0 if (fa + p.rot) % 180 == 0 else 90
                return snap(x + rx), snap(y - ry), ang
            rx_, ry_, ra_ = fpos("Reference", (2.54, 1.27, 0))
            vx_, vy_, va_ = fpos("Value", (2.54, -1.27, 0))
            props = [
                f'(property "Reference" {q(p.ref)} (at {rx_} {ry_} {ra_}) {eff()})',
                f'(property "Value" {q(p.value)} (at {vx_} {vy_} {va_}) {eff()})',
                f'(property "Footprint" {q(p.fp)} (at {x} {y} 0) {eff(hide=True)})',
                f'(property "Datasheet" {q(p.sym["props"].get("Datasheet", "~"))} (at {x} {y} 0) {eff(hide=True)})',
                f'(property "Description" {q(p.sym["props"].get("Description", ""))} (at {x} {y} 0) {eff(hide=True)})',
                f'(property "LCSC" {q(p.lcsc)} (at {x} {y} 0) {eff(hide=True)})',
                f'(property "MPN" {q(p.mpn)} (at {x} {y} 0) {eff(hide=True)})',
                f'(property "Assembly" {q(p.assembly)} (at {x} {y} 0) {eff(hide=True)})',
            ]
            pins = "".join(f' (pin {q(n)} (uuid {q(uid(p.uuid, "pin", n))}))'
                           for n in p.sym["pins"]
                           if any(pp["unit"] in (0, p.unit) for pp in p.sym["pins"][n]))
            items.append(
                f'(symbol (lib_id {q(p.lib_id)}) (at {x} {y} {p.rot}) (unit {p.unit}) '
                f'(exclude_from_sim no) (in_bom {"no" if p.assembly == "NONE" else "yes"}) '
                f'(on_board yes) (dnp {"yes" if p.dnp else "no"}) (uuid {q(p.uuid)}) '
                + " ".join(props) + pins +
                f' (instances (project {q(self.name)} (path {q(path)} '
                f'(reference {q(p.ref)}) (unit {p.unit})))))')
            # pin stubs
            for num, net in p.nets.items():
                px, py, dx, dy = p.pin_geom(num)
                if net == "NC":
                    items.append(f'(no_connect (at {px} {py}) (uuid {q(uid(p.uuid, "nc", num))}))')
                    continue
                stub = STUB_IC if len(p.sym["pins"]) > 3 else STUB
                ex, ey = snap(px + dx * stub), snap(py + dy * stub)
                items.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) '
                             f'(stroke (width 0) (type default)) (uuid {q(uid(p.uuid, "w", num))}))')
                items.append(self._net_marker(s, p, num, net, ex, ey, dx, dy, libs))
        for t, (x, y), size in s.texts:
            items.append(f'(text {q(t)} (exclude_from_sim no) (at {x} {y} 0) '
                         f'{eff(justify="left", size=size)} (uuid {q(uid(s.uuid, "text", t))}))')
        out.append(f'(kicad_sch (version {VERSION}) (generator "nexus-schgen") '
                   f'(generator_version "8.0") (uuid {q(s.uuid)}) (paper {q(s.paper)}) '
                   + self.title_block(s.title))
        out.append("(lib_symbols\n" + "".join(libs.values()) + ")")
        out.extend(items)
        out.append(")")
        path_file = ROOT / self.name / f"{s.name}.kicad_sch"
        path_file.write_text("\n".join(out) + "\n")
        return path_file

    def _net_marker(self, s, p, num, net, x, y, dx, dy, libs):
        key = uid(p.uuid, "net", num)
        many = len(p.sym["pins"]) > 3 and not p.sym["power"]
        if (net in self.power_nets or net in GROUNDS) and not many:
            if net == "GND":
                sym = LIB.get("power:GND")
            elif net in GROUNDS:
                sym = power_symbol(net, "power:GNDA", "GNDA")
            else:
                sym = power_symbol(net)
            libs[sym["lib_id"]] = sym["text"]
            self.pwr_count += 1
            ref = f"#PWR{self.pwr_count:03d}"
            down = net in GROUNDS
            # place so that the symbol body points away from the pin
            rot = 0
            if not down and dy > 0:
                rot = 180
            if down and dy < 0:
                rot = 180
            if dx != 0:
                rot = (90 if dx > 0 else 270) if not down else (270 if dx > 0 else 90)
            path = f"/{self.root_uuid}/{s.uuid}"
            return (f'(symbol (lib_id {q(sym["lib_id"])}) (at {x} {y} {rot}) (unit 1) '
                    f'(exclude_from_sim no) (in_bom no) (on_board yes) (dnp no) (uuid {q(key)}) '
                    f'(property "Reference" {q(ref)} (at {x} {y} 0) {eff(hide=True)}) '
                    f'(property "Value" {q(net)} (at {x} {y - 2.54 if not down else y + 3.81} 0) {eff()}) '
                    f'(property "Footprint" "" (at {x} {y} 0) {eff(hide=True)}) '
                    f'(property "Datasheet" "" (at {x} {y} 0) {eff(hide=True)}) '
                    f'(pin "1" (uuid {q(uid(key, "pin"))})) '
                    f'(instances (project {q(self.name)} (path {q(path)} (reference {q(ref)}) (unit 1)))))')
        angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
        just = "left" if angle in (0, 90) else "right"
        if self.is_global(net) or net in self.power_nets or net in GROUNDS:
            return (f'(global_label {q(net)} (shape passive) (at {x} {y} {angle}) '
                    f'(fields_autoplaced yes) {eff(justify=just)} (uuid {q(key)}) '
                    f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) {eff(hide=True)}))')
        return (f'(label {q(net)} (at {x} {y} {angle}) (fields_autoplaced yes) '
                f'{eff(justify=just + " bottom")} (uuid {q(key)}))')

    def is_global(self, net):
        return net in self.global_nets

    def compute_globals(self):
        seen = {}
        for s in self.sheets:
            for p in s.parts:
                for net in p.nets.values():
                    seen.setdefault(net, set()).add(s.name)
        self.global_nets = {n for n, ss in seen.items() if len(ss) > 1} | set(
            getattr(self, "force_global", ()))

    def write_root(self):
        items = []
        x0, y0 = 30.48, 40.64
        for i, s in enumerate(self.sheets):
            x = x0 + (i % 4) * 88.9
            y = y0 + (i // 4) * 50.8
            w, h = 63.5, 25.4
            items.append(
                f'(sheet (at {x} {y}) (size {w} {h}) (exclude_from_sim no) (in_bom yes) '
                f'(on_board yes) (dnp no) (fields_autoplaced yes) '
                f'(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) '
                f'(uuid {q(s.uuid)}) '
                f'(property "Sheetname" {q(s.name)} (at {x} {y - 0.7} 0) {eff(justify="left bottom")}) '
                f'(property "Sheetfile" {q(s.name + ".kicad_sch")} (at {x} {y + h + 0.6} 0) {eff(justify="left top")}) '
                f'(instances (project {q(self.name)} (path {q("/" + self.root_uuid)} (page {q(str(s.page))})))))')
            items.append(f'(text {q(s.title)} (exclude_from_sim no) (at {x + 2.54} {y + 12.7} 0) '
                         f'{eff(justify="left")} (uuid {q(uid(s.uuid, "roottext"))}))')
        out = [f'(kicad_sch (version {VERSION}) (generator "nexus-schgen") '
               f'(generator_version "8.0") (uuid {q(self.root_uuid)}) (paper "A4") '
               + self.title_block("Hierarchy"),
               "(lib_symbols)"] + items + [
            '(sheet_instances (path "/" (page "1")))', ")"]
        f = ROOT / self.name / f"{self.name}.kicad_sch"
        f.write_text("\n".join(out) + "\n")
        return f

    def check_complete(self):
        """Every pin of every part must have a net or an explicit NC."""
        missing = []
        for s in self.sheets:
            for p in s.parts:
                for num, defs in p.sym["pins"].items():
                    if any(d["unit"] in (0, p.unit) for d in defs) and num not in p.nets:
                        missing.append(f"{s.name}/{p.key} pin {num} ({defs[0]['name']})")
        if missing:
            raise ValueError("pins without net:\n  " + "\n  ".join(missing))

    def write_power_lib(self):
        """Write the custom power symbols into lib/nexus_power.kicad_sym."""
        blocks = []
        for net, sym in sorted(_PWR_CACHE.items()):
            blocks.append(sym["text"].replace(q(sym["lib_id"]), q(net), 1))
        f = ROOT / "lib" / "nexus_power.kicad_sym"
        old = {}
        if f.exists():  # keep symbols of the other board
            for m in re.finditer(r'^\t\(symbol "([^"]+)"\n.*?^\t\)\n', f.read_text(), re.M | re.S):
                old[m.group(1)] = m.group(0)
        for b in blocks:
            name = re.match(r'\s*\(symbol "([^"]+)"', b).group(1)
            old[name] = b
        f.write_text('(kicad_symbol_lib (version 20231120) (generator "nexus-schgen")\n'
                     + "".join(old[k] for k in sorted(old)) + ")\n")
        subprocess.run(["kicad-cli", "sym", "upgrade", "--force", str(f)],
                       check=True, capture_output=True)

    def write(self):
        self.check_complete()
        self.annotate()
        self.compute_globals()
        files = [self.write_sheet(s) for s in self.sheets] + [self.write_root()]
        self.write_power_lib()
        for f in files:
            subprocess.run(["kicad-cli", "sch", "upgrade", "--force", str(f)],
                           check=True, capture_output=True)
        return files

    # ------------------------------------------------------------ verify --
    def intended_nets(self):
        nets = {}
        for s in self.sheets:
            for p in s.parts:
                for num, net in p.nets.items():
                    if net == "NC" or p.ref.startswith("#"):
                        continue
                    name = net if (net in self.global_nets or net in self.power_nets
                                   or net in GROUNDS) else f"/{s.name}/{net}"
                    nets.setdefault(name, set()).add((p.ref, num))
        return nets

    def verify(self):
        """Compare KiCad's netlist with the intended nets. Returns problems."""
        out = ROOT / "out" / f"{self.name}.net"
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(out),
                        str(ROOT / self.name / f"{self.name}.kicad_sch")],
                       check=True, capture_output=True)
        text = out.read_text()
        actual = {}
        for blk in re.split(r"\(net\s*\n", text.split("(nets", 1)[1])[1:]:
            name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
            nodes = set(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk))
            actual[name] = nodes
        want = self.intended_nets()
        problems = []
        # map: every intended group must be exactly one actual net
        node_to_net = {n: name for name, nodes in actual.items() for n in nodes}
        for name, nodes in sorted(want.items()):
            got = {node_to_net.get(n) for n in nodes}
            if len(got) != 1 or None in got:
                problems.append(f"net {name}: pins land in {got}")
                continue
            got_name = got.pop()
            extra = actual[got_name] - nodes
            extra = {e for e in extra if not e[0].startswith("#")}
            if extra:
                problems.append(f"net {name}: unexpected extra pins {sorted(extra)}")
        return problems


_PWR_CACHE = {}


def power_symbol(net, base_id="power:VCC", base_name="VCC"):
    """A global power symbol whose net name is `net` (graphics of base_id)."""
    if net in _PWR_CACHE:
        return _PWR_CACHE[net]
    base = LIB.get(base_id)
    lib_id = f"nexus_power:{net}"
    text = base["text"].replace(q(base_id), q(lib_id), 1)
    text = re.sub(r'\(symbol "' + base_name + r'_(\d)_(\d)"', lambda m: f'(symbol {q(net + "_" + m.group(1) + "_" + m.group(2))}', text)
    text = re.sub(r'(\(property "Value" )"' + base_name + '"', lambda m: m.group(1) + q(net), text, count=1)
    text = re.sub(r'(\(name )"' + base_name + '"', lambda m: m.group(1) + q(net), text)
    sym = dict(base, lib_id=lib_id, text=text)
    _PWR_CACHE[net] = sym
    return sym
