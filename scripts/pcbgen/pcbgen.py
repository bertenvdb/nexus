# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial PCB placement from the schematic netlist (F5 step 1).

Builds a board from scratch with KiCad's pcbnew API: outline, mounting
holes, every footprint linked to its schematic symbol (path), pads on
their nets, and placement by explicit position or by packing a group of
parts into a region. Used once per board revision: after routing starts
the .kicad_pcb file itself is the source (re-running would discard it).
"""
import pathlib
import re
import subprocess

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
FPDIRS = {"nexus": ROOT / "lib" / "nexus.pretty"}
mm = pcbnew.FromMM


def fp_dir(lib):
    return FPDIRS.get(lib, pathlib.Path("/usr/share/kicad/footprints") / f"{lib}.pretty")


# --------------------------------------------------------------- netlist --
def read_netlist(board):
    out = ROOT / "out" / f"{board}.net"
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(out),
                    str(ROOT / board / f"{board}.kicad_sch")], check=True,
                   capture_output=True)
    text = out.read_text()
    comps = {}
    comp_txt = text.split("(components", 1)[1].split("(libparts", 1)[0]
    for blk in re.split(r"\n\t\t\(comp\n", comp_txt)[1:]:
        g = lambda pat: (re.search(pat, blk) or [None, ""])[1]
        ref = g(r'\(ref "([^"]+)"\)')
        comps[ref] = dict(
            ref=ref, value=g(r'\(value "([^"]*)"\)'),
            footprint=g(r'\(footprint "([^"]*)"\)'),
            sheet=g(r'\(names "/([^"/]*)/?"\)'),
            path=g(r'\(tstamps "(/[^"]*/)"\)') + g(r'\n\t\t\t\(tstamps "([^"]+)"\)'),
            lcsc=g(r'\(name "LCSC"\) "([^"]*)"'),
            mpn=g(r'\(name "MPN"\) "([^"]*)"'),
            assembly=g(r'\(name "Assembly"\) "([^"]*)"'),
            description=g(r'\(description "([^"]*)"\)'),
            datasheet=g(r'\(name "Datasheet"\) "([^"]*)"'),
        )
    nets = {}
    for blk in re.split(r"\(net\s*\n", text.split("(nets", 1)[1])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        nets[name] = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk)
    return comps, nets


# ----------------------------------------------------------------- board --
class Pcb:
    def __init__(self, board, template, origin=(40.0, 40.0)):
        self.name = board
        self.board = pcbnew.LoadBoard(str(template))
        self.board.SetCopperLayerCount(4)
        self.ox, self.oy = origin
        self.comps, self.nets = read_netlist(board)
        self.fps = {}
        self.netinfo = {}
        for name in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(ni)
            self.netinfo[name] = ni
        self.pin_net = {(r, p): n for n, nodes in self.nets.items() for r, p in nodes}
        self.placed = set()

    def P(self, x, y):
        return pcbnew.VECTOR2I(mm(self.ox + x), mm(self.oy + y))

    # -- outline and holes
    def outline(self, w, h, r=2.0):
        self.w, self.h = w, h
        seg = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)),
               ((w - r, h), (r, h)), ((0, h - r), (0, r))]
        for a, b in seg:
            s = pcbnew.PCB_SHAPE(self.board, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(self.P(*a)); s.SetEnd(self.P(*b))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            self.board.Add(s)
        for cx, cy, a0 in [(r, r, 180), (w - r, r, 270), (w - r, h - r, 0), (r, h - r, 90)]:
            s = pcbnew.PCB_SHAPE(self.board, pcbnew.SHAPE_T_ARC)
            s.SetCenter(self.P(cx, cy))
            import math
            sx = cx + r * math.cos(math.radians(a0)); sy = cy + r * math.sin(math.radians(a0))
            s.SetStart(self.P(sx, sy))
            s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            self.board.Add(s)

    def hole(self, ref, x, y):
        fp = pcbnew.FootprintLoad(str(fp_dir("MountingHole")), "MountingHole_3.2mm_M3")
        fp.SetReference(ref)
        fp.SetValue("M3")
        fp.SetFPIDAsString("MountingHole:MountingHole_3.2mm_M3")
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        fp.SetPosition(self.P(x, y))
        self.board.Add(fp)

    # -- footprints
    def _load(self, ref):
        c = self.comps[ref]
        lib, name = c["footprint"].split(":", 1)
        fp = pcbnew.FootprintLoad(str(fp_dir(lib)), name)
        if fp is None:
            raise RuntimeError(f"footprint {c['footprint']} not found ({ref})")
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetFPIDAsString(c["footprint"])
        fp.SetLibDescription(c["description"]) if hasattr(fp, "SetLibDescription") else None
        fp.SetField("Description", c["description"])
        fp.GetField("Description").SetVisible(False)
        for key, name in (("lcsc", "LCSC"), ("mpn", "MPN"), ("assembly", "Assembly"),
                          ("datasheet", "Datasheet")):
            fp.SetField(name, c[key])
            fp.GetField(name).SetVisible(False)
        if c["assembly"] == "NONE":
            fp.SetExcludedFromBOM(True)
            fp.SetExcludedFromPosFiles(True)
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname(c["sheet"])
        fp.SetSheetfile(c["sheet"] + ".kicad_sch")
        for pad in fp.Pads():
            net = self.pin_net.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(self.netinfo[net])
        self.board.Add(fp)
        self.fps[ref] = fp
        return fp

    def place(self, ref, x, y, rot=0, back=False):
        fp = self.fps.get(ref) or self._load(ref)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(self.P(x, y))
        if back and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        self.placed.add(ref)
        return fp

    def fab_box(self, fp):
        """Bounding box (board mm) of F.Fab graphics, else courtyard."""
        for layer in (pcbnew.F_Fab, pcbnew.F_CrtYd):
            boxes = [g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer() == layer]
            if boxes:
                x0 = min(b.GetLeft() for b in boxes); x1 = max(b.GetRight() for b in boxes)
                y0 = min(b.GetTop() for b in boxes); y1 = max(b.GetBottom() for b in boxes)
                return (pcbnew.ToMM(x0) - self.ox, pcbnew.ToMM(y0) - self.oy,
                        pcbnew.ToMM(x1) - self.ox, pcbnew.ToMM(y1) - self.oy)
        raise RuntimeError("no fab/courtyard")

    def crt_box(self, fp):
        boxes = [g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_CrtYd]
        if not boxes:
            b = fp.GetBoundingBox(False)
            boxes = [b]
        x0 = min(b.GetLeft() for b in boxes); x1 = max(b.GetRight() for b in boxes)
        y0 = min(b.GetTop() for b in boxes); y1 = max(b.GetBottom() for b in boxes)
        return (pcbnew.ToMM(x0) - self.ox, pcbnew.ToMM(y0) - self.oy,
                pcbnew.ToMM(x1) - self.ox, pcbnew.ToMM(y1) - self.oy)

    def edge(self, ref, side, along, overhang=0.0, rot=None):
        """Place a connector on a board edge with its F.Fab front `overhang`
        mm past the edge. side: left/right/top/bottom. `rot` must make the
        mating face point outwards."""
        fp = self.place(ref, 0, 0, rot or 0)
        x0, y0, x1, y1 = self.fab_box(fp)
        if side == "left":
            self.place(ref, -overhang - x0, along, rot)
        elif side == "right":
            self.place(ref, self.w + overhang - x1, along, rot)
        elif side == "top":
            self.place(ref, along, -overhang - y0, rot)
        else:
            self.place(ref, along, self.h + overhang - y1, rot)
        return fp

    def pack(self, refs, region, gap=0.6, rot=0, turn=True, sort=True):
        """Place refs row by row inside region (x0, y0, x1, y1) by courtyard.

        If a part does not fit in the rest of the row, it is also tried
        turned by 90 degrees before a new row is started.
        """
        x0, y0, x1, y1 = region
        x, y, row_h = x0, y0, 0.0
        if sort:
            def area(ref):
                bx = self.crt_box(self.place(ref, 0, 0, rot))
                return -(bx[2] - bx[0]) * (bx[3] - bx[1])
            refs = sorted(refs, key=area)
        for ref in refs:
            options = [rot, rot + 90] if turn else [rot]
            done = False
            for attempt in ("row", "newrow"):
                if attempt == "newrow":
                    x, y, row_h = x0, y + row_h + gap, 0.0
                for rr in options:
                    fp = self.place(ref, 0, 0, rr % 360)
                    cx0, cy0, cx1, cy1 = self.crt_box(fp)
                    w, h = cx1 - cx0, cy1 - cy0
                    if x + w <= x1 + 1e-6 and y + h <= y1 + 1e-6:
                        self.place(ref, x - cx0, y - cy0, rr % 360)
                        x += w + gap
                        row_h = max(row_h, h)
                        done = True
                        break
                if done:
                    break
            if not done:
                raise RuntimeError(f"region {region} full at {ref} (part {w:.1f} x {h:.1f})")

    def unplaced(self):
        return sorted(set(self.comps) - self.placed)

    def save(self, netclasses=None, patterns=None):
        out = ROOT / self.name / f"{self.name}.kicad_pcb"
        pcbnew.SaveBoard(str(out), self.board)
        if netclasses:
            write_netclasses(self.name, netclasses, patterns or [])
        return out


def write_netclasses(board, classes, patterns):
    """Net classes into <board>.kicad_pro (SaveBoard resets them).

    classes: {name: dict(track=, clearance=, via=, drill=, dp_w=, dp_g=)}
    patterns: [(netclass, wildcard), ...]
    """
    import json
    f = ROOT / board / f"{board}.kicad_pro"
    d = json.loads(f.read_text())
    base = d["net_settings"]["classes"][0]
    out = []
    for prio, (name, c) in enumerate(classes.items()):
        e = dict(base)
        e.update(name=name, track_width=c.get("track", 0.2),
                 clearance=c.get("clearance", 0.15),
                 via_diameter=c.get("via", 0.6), via_drill=c.get("drill", 0.3),
                 diff_pair_width=c.get("dp_w", 0.2), diff_pair_gap=c.get("dp_g", 0.25),
                 priority=2147483647 if name == "Default" else prio)
        out.append(e)
    d["net_settings"]["classes"] = out
    d["net_settings"]["netclass_patterns"] = [
        {"netclass": n, "pattern": p} for n, p in patterns]
    f.write_text(json.dumps(d, indent=2))
