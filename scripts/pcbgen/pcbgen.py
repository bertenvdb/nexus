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
MIN_GAP = float(__import__("os").environ.get("PACK_MIN_GAP", "0"))  # extra routing room between parts


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
    def __init__(self, board, template, origin=(40.0, 40.0), layers=4):
        self.name = board
        self.board = pcbnew.LoadBoard(str(template))
        self.board.SetCopperLayerCount(layers)
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
        """Place refs inside region (x0, y0, x1, y1) by courtyard.

        MaxRects packing (best short side fit): every part is tried in both
        orientations in every free rectangle; much denser than row packing.
        """
        x0, y0, x1, y1 = region
        gap = max(gap, MIN_GAP)
        sizes = {}
        for ref in refs:
            for rr in ([rot, rot + 90] if turn else [rot]):
                bx = self.crt_box(self.place(ref, 0, 0, rr % 360))
                sizes[(ref, rr % 360)] = (bx[2] - bx[0], bx[3] - bx[1], bx[0], bx[1])
        if sort:
            refs = sorted(refs, key=lambda r_: -max(
                w * h for (rf, _), (w, h, _a, _b) in sizes.items() if rf == r_))
        free = [(x0, y0, x1 + gap, y1 + gap)]   # each part reserves w+gap x h+gap
        obst = getattr(self, "_obstacles", [])
        if obst:
            free = self._cut(free, [(a - gap, b - gap, c + gap, d + gap) for a, b, c, d in obst])
        for ref in refs:
            best = None
            for (rf, rr), (w, h, ox, oy) in sizes.items():
                if rf != ref:
                    continue
                W_, H_ = w + gap, h + gap
                for fx0, fy0, fx1, fy1 in free:
                    fw, fh = fx1 - fx0, fy1 - fy0
                    if W_ <= fw + 1e-6 and H_ <= fh + 1e-6:
                        score = (min(fw - W_, fh - H_), max(fw - W_, fh - H_), fy0, fx0)
                        if best is None or score < best[0]:
                            best = (score, rr, fx0, fy0, W_, H_, ox, oy)
            if best is None:
                raise RuntimeError(f"region {region} full at {ref}")
            _, rr, px, py, W_, H_, ox, oy = best
            self.place(ref, px - ox, py - oy, rr)
            # split every free rectangle that intersects the used one
            used = (px, py, px + W_, py + H_)
            nf = []
            for f in free:
                if (used[0] >= f[2] or used[2] <= f[0] or used[1] >= f[3] or used[3] <= f[1]):
                    nf.append(f)
                    continue
                if used[0] > f[0]:
                    nf.append((f[0], f[1], used[0], f[3]))
                if used[2] < f[2]:
                    nf.append((used[2], f[1], f[2], f[3]))
                if used[1] > f[1]:
                    nf.append((f[0], f[1], f[2], used[1]))
                if used[3] < f[3]:
                    nf.append((f[0], used[3], f[2], f[3]))
            # drop rectangles contained in others
            free = [a for a in nf if not any(
                a != b and a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]
                for b in nf)]

    # ------------------------------------------------- two-level packing --
    def block(self, refs, widths=(10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 34),
              gap=0.3, first=None):
        """Arrange refs compactly at the origin; return the tightest block.

        `first`: a ref placed at the top-left before the rest (e.g. the MCU).
        Returns dict(refs, w, h, pos={ref: (x, y, rot)}).
        """
        best = None
        for w in widths:
            try:
                if first:
                    self.pack([first], (0, 0, w, 1000), gap=gap, turn=False)
                    fb = self.crt_box(self.fps[first])
                    rest = [r_ for r_ in refs if r_ != first]
                    # pack the rest right of and below the first part
                    self._pack_obstacles(rest, (0, 0, w, 1000), [fb], gap)
                else:
                    self.pack(refs, (0, 0, w, 1000), gap=gap)
            except RuntimeError:
                continue
            boxes = [self.crt_box(self.fps[r_]) for r_ in refs]
            bw = max(b_[2] for b_ in boxes) - min(b_[0] for b_ in boxes)
            bh = max(b_[3] for b_ in boxes) - min(b_[1] for b_ in boxes)
            score = bw * bh + 0.5 * abs(bw - bh)   # small, not too elongated
            if best is None or score < best[0]:
                x0 = min(b_[0] for b_ in boxes); y0 = min(b_[1] for b_ in boxes)
                pos = {}
                for r_ in refs:
                    fp = self.fps[r_]
                    pos[r_] = (pcbnew.ToMM(fp.GetPosition().x) - self.ox - x0,
                               pcbnew.ToMM(fp.GetPosition().y) - self.oy - y0,
                               fp.GetOrientationDegrees())
                best = (score, dict(refs=refs, w=bw, h=bh, pos=pos))
        if best is None:
            raise RuntimeError(f"no block arrangement for {refs[:3]}...")
        return best[1]

    def _pack_obstacles(self, refs, region, obstacles, gap):
        """pack() with fixed obstacles (courtyard boxes) inside the region."""
        self._obstacles = obstacles
        try:
            self.pack(refs, region, gap=gap)
        finally:
            self._obstacles = []

    def place_blocks(self, blocks, region, obstacles=(), gap=0.6):
        """MaxRects placement of whole blocks inside region around obstacles.

        Several block orders and fit rules are tried; the first complete
        placement wins.
        """
        x0, y0, x1, y1 = region
        base = [(x0, y0, x1 + gap, y1 + gap)]
        base = self._cut(base, [(a - gap, b - gap, c + gap, d + gap) for a, b, c, d in obstacles])
        orders = [lambda b_: -b_["w"] * b_["h"], lambda b_: -b_["h"], lambda b_: -b_["w"],
                  lambda b_: -max(b_["w"], b_["h"])]
        rules = ["bssf", "blsf", "baf", "bl"]
        for order in orders:
            for rule in rules:
                ordered = sorted(blocks, key=lambda b_: (b_.get("near") is None, order(b_)))
                plan = self._try_blocks(ordered, base, gap, rule)
                if plan:
                    for blk, px, py in plan:
                        for r_, (x, y, rr) in blk["pos"].items():
                            self.place(r_, px + x, py + y, rr)
                    return
        raise RuntimeError("board full: no block placement found")

    def _try_blocks(self, blocks, free, gap, rule):
        plan = []
        for blk in blocks:
            W_, H_ = blk["w"] + gap, blk["h"] + gap
            best = None
            near = blk.get("near")
            for f in free:
                fw, fh = f[2] - f[0], f[3] - f[1]
                if W_ <= fw + 1e-6 and H_ <= fh + 1e-6:
                    lw, lh = fw - W_, fh - H_
                    if near:
                        # the four corners of f keep the packing tight; take
                        # the one whose block centre is closest to the target
                        cands = []
                        for cx in (f[0], f[2] - W_):
                            for cy in (f[1], f[3] - H_):
                                d = ((cx + W_ / 2 - near[0]) ** 2 + (cy + H_ / 2 - near[1]) ** 2) ** 0.5
                                cands.append(((d, min(lw, lh)), cx, cy))
                    else:
                        cands = [({"bssf": (min(lw, lh), max(lw, lh)),
                                   "blsf": (max(lw, lh), min(lw, lh)),
                                   "baf": (fw * fh - W_ * H_, min(lw, lh)),
                                   "bl": (f[1], f[0])}[rule], f[0], f[1])]
                    for score, cx, cy in cands:
                        if best is None or score < best[0]:
                            best = (score, cx, cy)
            if best is None:
                return None
            _, px, py = best
            plan.append((blk, px, py))
            free = self._cut(free, [(px, py, px + W_, py + H_)])
        return plan

    @staticmethod
    def _cut(free, used_list):
        for used in used_list:
            nf = []
            for f in free:
                if used[0] >= f[2] or used[2] <= f[0] or used[1] >= f[3] or used[3] <= f[1]:
                    nf.append(f)
                    continue
                if used[0] > f[0]:
                    nf.append((f[0], f[1], used[0], f[3]))
                if used[2] < f[2]:
                    nf.append((used[2], f[1], f[2], f[3]))
                if used[1] > f[1]:
                    nf.append((f[0], f[1], f[2], used[1]))
                if used[3] < f[3]:
                    nf.append((f[0], used[3], f[2], f[3]))
            free = [a for a in nf if a[2] - a[0] > 0.5 and a[3] - a[1] > 0.5 and not any(
                a != b and a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]
                for b in nf)]
        return free

    def zone(self, net, layer, pts, priority=0, clearance=0.3, min_width=0.25,
             full=True, name=None):
        """Copper zone; pts in board mm. full=True: solid pad connections."""
        z = pcbnew.ZONE(self.board)
        z.SetNet(self.netinfo[net] if net in self.netinfo else self.board.FindNet(net))
        z.SetLayer(layer)
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(min_width))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if full
                           else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(mm(self.ox + x), mm(self.oy + y))
        self.board.Add(z)
        return z

    def via(self, net, x, y, size=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(self.P(x, y))
        v.SetWidth(mm(size))
        v.SetDrill(mm(drill))
        v.SetNet(self.netinfo[net])
        self.board.Add(v)
        return v

    def fill_zones(self):
        self.board.BuildConnectivity()   # else island removal drops everything
        filler = pcbnew.ZONE_FILLER(self.board)
        filler.Fill(self.board.Zones())

    def unplaced(self):
        return sorted(set(self.comps) - self.placed)

    def save(self, netclasses=None, patterns=None):
        alt = __import__("os").environ.get("PCB_OUT")   # placement trials
        out = pathlib.Path(alt) if alt else ROOT / self.name / f"{self.name}.kicad_pcb"
        pcbnew.SaveBoard(str(out), self.board)
        if netclasses and not alt:
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
    # JLCPCB 4-layer capabilities (with margin): track/space 0.09 mm, via 0.45/0.2
    rules = d["board"]["design_settings"]["rules"]
    rules.update(min_track_width=0.12, min_clearance=0.12, min_via_diameter=0.5,
                 min_through_hole_diameter=0.3, min_copper_edge_clearance=0.5)
    d["net_settings"]["netclass_patterns"] = [
        {"netclass": n, "pattern": p} for n, p in patterns]
    f.write_text(json.dumps(d, indent=2))
