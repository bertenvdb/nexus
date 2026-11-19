#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Grid maze router for the connections left open (F5 step 3).

  scripts/pcbgen/maze.py <board>
  env MAZE_FIRST="NET,NET"   route these nets first (second pass for failures)
  env MAZE_NETS="NET,NET"    route only these nets
  env MAZE_ESCAPE="U5"        fine-pitch parts: escape lanes (see escape())

Deterministic A* on a 0.1 mm grid over the routing layers F.Cu, In2.Cu and
B.Cu (In1 is the GND/AGND plane and never gets tracks). Exact clearances:
every copper item is inflated by clearance + half the track width (one map
per track width, one for vias) before it is sampled at the cell centres, and
track centre lines run through cell centres. Through vias 0.6/0.3 mm. Run
stitch.py first; GND/AGND pads it could not reach get a track here. The power
trunk is left alone.
"""
import fnmatch
import heapq
import math
import os
import pathlib
import sys

import numpy as np
import pcbnew
from matplotlib.path import Path

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))

G = 0.1                      # grid pitch, mm
CLEAR = 0.17                 # 0.15 rule + 0.02, mm
HOLE_CLEAR = 0.27            # 0.25 hole rule + 0.02, mm
EDGE = 0.55                  # copper to board edge (rule 0.5), mm
VIA, DRILL = 0.6, 0.3
VIA_COST = 25                # in grid steps
MAX_EXPAND = 2_000_000
SKIP = {"+24V_IN", "+24V_HEATER", "/power_input/VIN_RAW", "/heater_cutoff/CUTOFF_SRC"}
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYER_COST = [1.0, 1.15, 1.3]
# preferred direction per layer (classic two-direction routing): moves against
# it cost DIR_PENALTY more. F.Cu free (pads), In2 horizontal, B.Cu vertical.
DIR = [None, "h", "v"]
DIR_PENALTY = float(os.environ.get("MAZE_DIR_PENALTY", "2.0"))
FIRST = ["USB_DP", "USB_DM", "/usb_can/CANH", "/usb_can/CANL", "CAN_TX", "CAN_RX",
         "/mcu/OSC_IN", "/mcu/OSC_OUT"]
FONLY = {"USB_DP", "USB_DM"}  # stay on F.Cu, over the solid In1 plane
MIN_W = 0.2                   # track width for the stretch inside own pads
mm = pcbnew.FromMM


def width_of():
    import toolboard_place as tp
    cls = {n: c["track"] for n, c in tp.NETCLASSES.items()}

    def w(net):
        for c, pat in tp.NETCLASS_PATTERNS:
            if fnmatch.fnmatchcase(net, pat):
                return min(cls[c], 0.8)
        return cls["Default"]
    return w


def disk(rc):
    r = int(math.ceil(rc))
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx <= rc * rc]


def dilate(mask, offs):
    out = np.zeros_like(mask)
    ny, nx = mask.shape
    for dy, dx in offs:
        ys, yd = (slice(dy, ny), slice(0, ny - dy)) if dy >= 0 else (slice(0, ny + dy), slice(-dy, ny))
        xs, xd = (slice(dx, nx), slice(0, nx - dx)) if dx >= 0 else (slice(0, nx + dx), slice(-dx, nx))
        out[yd, xd] |= mask[ys, xs]
    return out


class Board:
    """Rasterised copper: island ids (exact copper) and per-radius keep-out maps."""

    def __init__(self, b, radii):
        self.b = b
        bb = b.GetBoardEdgesBoundingBox()
        # half a cell back: cell centres on whole 0.1 mm, i.e. on the centre
        # lines of 0.5 mm pitch pads (a 0.25 mm track then just fits a lane)
        self.x0, self.y0 = pcbnew.ToMM(bb.GetLeft()) - G / 2, pcbnew.ToMM(bb.GetTop()) - G / 2
        self.nx = int(pcbnew.ToMM(bb.GetWidth()) / G) + 1
        self.ny = int(pcbnew.ToMM(bb.GetHeight()) / G) + 1
        self.cx = self.x0 + (np.arange(self.nx) + 0.5) * G
        self.cy = self.y0 + (np.arange(self.ny) + 0.5) * G
        shape = (len(LAYERS), self.ny, self.nx)
        self.isl = np.zeros(shape, np.int32)          # 0 free, >0 island id
        self.radii = radii                            # key -> inflation, mm
        self.owner = {k: np.zeros(shape, np.int32) for k in radii}   # net code
        self.multi = {k: np.zeros(shape, bool) for k in radii}       # >1 net
        self.forbid = {k: np.zeros((self.ny, self.nx), bool) for k in radii}
        self.net_of = {}

    def xy(self, r, c):
        return self.x0 + (c + 0.5) * G, self.y0 + (r + 0.5) * G

    def mask(self, poly):
        """Cell-centre masks of a polygon set: yields (r0, c0, bool array)."""
        poly.Fracture()
        for k in range(poly.OutlineCount()):
            ol = poly.COutline(k)
            pts = np.array([(pcbnew.ToMM(ol.CPoint(i).x), pcbnew.ToMM(ol.CPoint(i).y))
                            for i in range(ol.PointCount())])
            if len(pts) < 3:
                continue
            c0 = max(int((pts[:, 0].min() - self.x0) / G) - 1, 0)
            c1 = min(int((pts[:, 0].max() - self.x0) / G) + 2, self.nx)
            r0 = max(int((pts[:, 1].min() - self.y0) / G) - 1, 0)
            r1 = min(int((pts[:, 1].max() - self.y0) / G) + 2, self.ny)
            if c1 <= c0 or r1 <= r0:
                continue
            X, Y = np.meshgrid(self.cx[c0:c1], self.cy[r0:r1])
            m = Path(pts).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
            yield r0, c0, m

    def paint_owner(self, key, li, poly, net):
        for r0, c0, m in self.mask(poly):
            o = self.owner[key][li, r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
            mu = self.multi[key][li, r0:r0 + m.shape[0], c0:c0 + m.shape[1]]
            mu |= m & (o != 0) & (o != net)
            o[m & (o == 0)] = net


def item_poly(it, L, extra):
    if it.GetClass() == "ZONE":
        p = pcbnew.SHAPE_POLY_SET(it.GetFilledPolysList(L))
        if extra:
            p.Inflate(mm(extra), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
        return p
    p = pcbnew.SHAPE_POLY_SET()
    it.TransformShapeToPolygon(p, L, mm(extra), mm(0.005),
                               pcbnew.ERROR_OUTSIDE if extra else pcbnew.ERROR_INSIDE)
    return p


def build(b, widths):
    radii = {("t", w): CLEAR + w / 2 for w in widths}
    radii[("v",)] = CLEAR + VIA / 2
    g = Board(b, radii)
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    items = list(b.GetTracks()) + [p for fp in b.GetFootprints() for p in fp.Pads()]
    items += [z for z in b.Zones() if not z.GetIsRuleArea()]
    key = lambda o: o.m_Uuid.AsString()
    island, nid = {}, 0
    for it in items:
        if it.GetNetCode() <= 0 or key(it) in island:
            continue
        nid += 1
        for o in [it] + list(conn.GetConnectedItems(it)):
            island.setdefault(key(o), nid)
        g.net_of[nid] = it.GetNetname()
    NONET = -7          # owner code for copper without a net: blocks everyone
    for it in items:
        net = it.GetNetCode() if it.GetNetCode() > 0 else NONET
        val = island.get(key(it), 0) if it.GetNetCode() > 0 else 0
        for li, L in enumerate(LAYERS):
            if not it.IsOnLayer(L):
                continue
            if val:
                for r0, c0, m in g.mask(item_poly(it, L, 0)):
                    g.isl[li, r0:r0 + m.shape[0], c0:c0 + m.shape[1]][m] = val
            for k, rad in radii.items():
                g.paint_owner(k, li, item_poly(it, L, rad), net)
    # NPTH holes (hole clearance) and the board edge block every net
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            for k, rad in radii.items():
                poly = pcbnew.SHAPE_POLY_SET()
                p.TransformHoleToPolygon(poly, mm(HOLE_CLEAR + rad - CLEAR), mm(0.005),
                                         pcbnew.ERROR_OUTSIDE)
                for r0, c0, m in g.mask(poly):
                    g.forbid[k][r0:r0 + m.shape[0], c0:c0 + m.shape[1]] |= m
    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge, False)
    inside = np.zeros((g.ny, g.nx), bool)
    for r0, c0, m in g.mask(edge):
        inside[r0:r0 + m.shape[0], c0:c0 + m.shape[1]] |= m
    for k, rad in radii.items():
        g.forbid[k] |= dilate(~inside, disk((EDGE + rad - CLEAR) / G))
    return g


def escape(g, b, refs, depth=1.5, fan=4.0):
    """Escape lanes around fine-pitch parts (F.Cu).

    For every pad a strip of one pitch width runs `depth` mm straight out of
    the package. Inside that ring a net may only use the lane in front of its
    own pad (pad width); the rest of the ring is closed to everyone and no
    via may sit in it. Without this, early routes hug the pad rows and lock
    the neighbouring pins in.
    """
    g.ring = np.zeros((g.ny, g.nx), bool)
    g.lane = {}
    g.pen_h = np.zeros((g.ny, g.nx), bool)   # F.Cu: horizontal moves penalised
    g.pen_v = np.zeros((g.ny, g.nx), bool)
    cell = lambda x, y: (int((y - g.y0) / G), int((x - g.x0) / G))
    for ref in refs:
        fp = b.FindFootprintByReference(ref)
        c = fp.GetPosition()
        pads = list(fp.Pads())
        # under the body, inside the pad ring: closed on F.Cu (a track there
        # runs along the pad rows and locks pins in)
        inner = [pcbnew.ToMM(v) for v in (c.x, c.y)]
        px = [pcbnew.ToMM(p.GetPosition().x) for p in pads]
        py = [pcbnew.ToMM(p.GetPosition().y) for p in pads]
        ix0, ix1 = min(px) + 0.8, max(px) - 0.8
        iy0, iy1 = min(py) + 0.8, max(py) - 0.8
        (ra, ca), (rb, cb) = cell(ix0, iy0), cell(ix1, iy1)
        g.ring[ra:rb + 1, ca:cb + 1] = True
        # fan-out zone beyond the lanes: no running parallel to the side
        ox0, ox1, oy0, oy1 = min(px) - 1.0 - depth, max(px) + 1.0 + depth, min(py) - 1.0 - depth, max(py) + 1.0 + depth
        for (x0_, y0_, x1_, y1_), m in [((ix0, oy0 - fan, ix1, oy0), g.pen_h), ((ix0, oy1, ix1, oy1 + fan), g.pen_h),
                                        ((ox0 - fan, iy0, ox0, iy1), g.pen_v), ((ox1, iy0, ox1 + fan, iy1), g.pen_v)]:
            (ra, ca), (rb, cb) = cell(x0_, y0_), cell(x1_, y1_)
            m[max(ra, 0):rb + 1, max(ca, 0):cb + 1] = True
        for p in pads:
            q = p.GetPosition()
            dx, dy = pcbnew.ToMM(q.x - c.x), pcbnew.ToMM(q.y - c.y)
            bb = p.GetBoundingBox()
            x0, x1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())
            y0, y1 = pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())
            if abs(dx) >= abs(dy):      # left/right side: lane runs in x
                pitch = 0.5
                lx0, lx1 = (x1, x1 + depth) if dx > 0 else (x0 - depth, x0)
                ring = (lx0, (y0 + y1) / 2 - pitch / 2, lx1, (y0 + y1) / 2 + pitch / 2)
                lane = (lx0, y0, lx1, y1)
            else:
                pitch = 0.5
                ly0, ly1 = (y1, y1 + depth) if dy > 0 else (y0 - depth, y0)
                ring = ((x0 + x1) / 2 - pitch / 2, ly0, (x0 + x1) / 2 + pitch / 2, ly1)
                lane = (x0, ly0, x1, ly1)
            (ra, ca), (rb, cb) = cell(ring[0], ring[1]), cell(ring[2], ring[3])
            g.ring[ra:rb + 1, ca:cb + 1] = True
            if p.GetNetCode() > 0 and not p.GetNetname().startswith("unconnected"):
                (ra, ca), (rb, cb) = cell(lane[0], lane[1]), cell(lane[2], lane[3])
                m = g.lane.setdefault(p.GetNetCode(), np.zeros((g.ny, g.nx), bool))
                m[ra:rb + 1, ca:cb + 1] = True


def blocked_for(g, k, net):
    o, mu = g.owner[k], g.multi[k]
    bl = mu | ((o != 0) & (o != net)) | g.forbid[k][None]
    if getattr(g, "ring", None) is not None:
        closed = g.ring & ~g.lane.get(net, np.zeros_like(g.ring))
        bl[0] |= closed
        if k == ("v",):
            bl |= g.ring[None]
    return bl


def route_net(g, net, w, log):
    """Join the islands of one net. Returns (joins, fails, paths)."""
    ids = [i for i, n in g.net_of.items() if n == net and (g.isl == i).any()]
    if len(ids) < 2:
        return 0, 0, []
    code = g.b.FindNet(net).GetNetCode()
    blocked = blocked_for(g, ("t", w), code)
    bmin = blocked_for(g, ("t", MIN_W), code)
    vb = blocked_for(g, ("v",), code).any(axis=0)
    own = np.isin(g.isl, ids)
    vb |= dilate(own[0] | own[-1], disk(VIA / 2 / G + 1))      # no via in own pads
    layers_ok = [0] if net in FONLY else list(range(len(LAYERS)))
    joins = fails = 0
    paths = []
    while True:
        ids = [i for i in ids if (g.isl == i).any()]
        if len(ids) < 2:
            return joins, fails, paths
        cnt = {i: int((g.isl == i).sum()) for i in ids}
        src = min(ids, key=cnt.get)          # start from the smallest island
        src_mask = g.isl == src
        tgt_mask = np.isin(g.isl, [i for i in ids if i != src])
        path = astar(src_mask, tgt_mask, blocked, bmin, vb, layers_ok,
                     getattr(g, "pen_h", None), getattr(g, "pen_v", None))
        if path is None:
            fails += 1
            log.append(f"no path: {net} ({len(ids)} islands)")
            ids = [i for i in ids if i != src]
            continue
        hit = g.isl[path[-1]]
        paths.append(path)
        stamp(g, path, w, code, src)
        g.isl[g.isl == hit] = src
        joins += 1


TURN_COST = 3.0       # per change of direction (grid steps): straight runs, no stair steps


def astar(src, tgt, blocked, bmin, vb, layers_ok, pen_h=None, pen_v=None):
    """A* over (layer, row, col, last direction). Moves parallel to a package
    side inside its fan-out zone (pen_h / pen_v) are not allowed on F.Cu."""
    tr = np.argwhere(tgt)
    if not len(tr):
        return None
    ty, tx = tr[:, 1].mean(), tr[:, 2].mean()
    spread = max(np.ptp(tr[:, 1]), np.ptp(tr[:, 2])) / 2

    def h(r, c):
        dy, dx = abs(r - ty), abs(c - tx)
        return max(max(dy, dx) + 0.414 * min(dy, dx) - spread, 0)
    L, NY, NX = blocked.shape
    starts = [tuple(int(v) for v in s) for s in np.argwhere(src) if s[0] in layers_ok]
    starts = sorted(starts, key=lambda s: math.hypot(s[1] - ty, s[2] - tx))[:400]
    best, heap = {}, []
    for li, r, c in starts:
        s = (li, r, c, 8)
        best[s] = 0.0
        heap.append((h(r, c), 0.0, s, None))
    heapq.heapify(heap)
    prev = {}
    steps = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
             (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
    n = 0
    while heap:
        f, cost, s, p = heapq.heappop(heap)
        if s in prev:
            continue
        prev[s] = p
        li, r, c, d = s
        if tgt[li, r, c]:
            out = [s]
            while prev[out[-1]] is not None:
                out.append(prev[out[-1]])
            return [x[:3] for x in out[::-1]]
        n += 1
        if n > MAX_EXPAND:
            return None
        here_src = src[li, r, c]
        for di, (dr, dc, k) in enumerate(steps):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < NY and 0 <= cc < NX):
                continue
            if blocked[li, rr, cc] and (bmin[li, rr, cc]
                                        or not (tgt[li, rr, cc] or src[li, rr, cc])):
                continue
            if src[li, rr, cc] and not here_src:
                continue
            if li == 0 and pen_h is not None and (
                    dr == 0 and pen_h[rr, cc] or dc == 0 and pen_v[rr, cc]):
                continue
            kk = k
            if DIR[li] == "h" and dr != 0 or DIR[li] == "v" and dc != 0:
                kk *= DIR_PENALTY
            nc = cost + kk * LAYER_COST[li] + (TURN_COST if d not in (8, di) else 0)
            t = (li, rr, cc, di)
            if nc < best.get(t, 1e18):
                best[t] = nc
                heapq.heappush(heap, (nc + h(rr, cc), nc, t, s))
        if not vb[r, c]:
            for l2 in layers_ok:
                if l2 == li or blocked[l2, r, c]:
                    continue
                t = (l2, r, c, 8)
                nc = cost + VIA_COST
                if nc < best.get(t, 1e18):
                    best[t] = nc
                    heapq.heappush(heap, (nc + h(r, c), nc, t, s))
    return None


def segments(path):
    """Path cells -> [("trk", layer, (r0, c0), (r1, c1)) | ("via", r, c)]."""
    out, run = [], [path[0]]
    for a, c in zip(path, path[1:]):
        if c[0] != a[0]:
            out.append(run); out.append(("via", a[1], a[2])); run = [c]
            continue
        if len(run) >= 2 and (run[-1][1] - run[-2][1], run[-1][2] - run[-2][2]) != (c[1] - a[1], c[2] - a[2]):
            out.append(run); run = [a]
        run.append(c)
    out.append(run)
    res = []
    for s in out:
        if s and s[0] == "via":
            res.append(s)
        elif len(s) >= 2:
            res.append(("trk", s[0][0], s[0][1:], s[-1][1:]))
    return res


def stamp(g, path, w, code, src):
    """Mark new copper: island (exact) and keep-out maps (inflated)."""
    vias = [(s[1], s[2]) for s in segments(path) if s[0] == "via"]
    rows = [r for _, r, _ in path]; cols = [c for _, _, c in path]
    pad = int(max(g.radii.values()) / G) + 8
    r0, r1 = max(min(rows) - pad, 0), min(max(rows) + pad + 1, g.ny)
    c0, c1 = max(min(cols) - pad, 0), min(max(cols) + pad + 1, g.nx)
    v = np.zeros((r1 - r0, c1 - c0), bool)
    for r, c in vias:
        v[r - r0, c - c0] = True
    for li in range(len(LAYERS)):
        m = np.zeros_like(v)
        for l2, r, c in path:
            if l2 == li:
                m[r - r0, c - c0] = True
        if not m.any() and not v.any():
            continue
        cu = dilate(m, disk(w / 2 / G)) | dilate(v, disk(VIA / 2 / G))
        isl = g.isl[li, r0:r1, c0:c1]
        isl[cu & (isl == 0)] = src
        for k, rad in g.radii.items():
            # +0.75 cell: the new copper is drawn from cell centres
            area = dilate(m, disk((rad + w / 2) / G + 0.75)) | dilate(v, disk((rad + VIA / 2) / G + 0.75))
            o = g.owner[k][li, r0:r1, c0:c1]
            mu = g.multi[k][li, r0:r1, c0:c1]
            mu |= area & (o != 0) & (o != code)
            o[area & (o == 0)] = code


def commit(g, b, net, w, path):
    nobj = b.FindNet(net)
    for s in segments(path):
        if s[0] == "via":
            x, y = g.xy(s[1], s[2])
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(VIA)); v.SetDrill(mm(DRILL)); v.SetNet(nobj)
            b.Add(v)
        else:
            _, li, (ra, ca), (rb, cb) = s
            xa, ya = g.xy(ra, ca); xb, yb = g.xy(rb, cb)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(xa), mm(ya))); t.SetEnd(pcbnew.VECTOR2I(mm(xb), mm(yb)))
            t.SetWidth(mm(w)); t.SetLayer(LAYERS[li]); t.SetNet(nobj)
            b.Add(t)


def main():
    board = sys.argv[1]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    w = width_of()
    padnets = {p.GetNetname() for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname()}
    widths = sorted({w(n) for n in padnets} | {MIN_W})
    g = build(b, widths)
    esc = [r for r in os.environ.get("MAZE_ESCAPE", "").split(",") if r]
    if esc:
        escape(g, b, esc)
    nets = sorted({n for n in g.net_of.values() if n and n not in SKIP and not n.startswith("unconnected")})
    only = [n for n in os.environ.get("MAZE_NETS", "").split(",") if n]
    if only:
        nets = [n for n in nets if n in only]
    first = list(dict.fromkeys([n for n in os.environ.get("MAZE_FIRST", "").split(",") if n] + FIRST))
    order = [n for n in first if n in nets] + [n for n in nets if n not in first]
    log, total, failed = [], 0, 0
    for net in order:
        j, f, paths = route_net(g, net, w(net), log)
        for p in paths:
            commit(g, b, net, w(net), p)
        total += j
        failed += f
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"maze: {total} connections routed, {failed} failed")
    for l in log:
        print("  " + l)


if __name__ == "__main__":
    main()
