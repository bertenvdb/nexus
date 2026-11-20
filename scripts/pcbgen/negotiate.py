#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Negotiated-congestion router (PathFinder) for the open connections (F5 step 3).

  scripts/pcbgen/negotiate.py <board>
  env NEG_ITER=40        maximum number of negotiation rounds
  env NEG_PRES=0.5       starting present-congestion factor (x NEG_PRES_GROW per round)
  env NEG_HIST=0.4       history cost added per round to a conflicting cell
  env MAZE_ESCAPE="U5"   escape lanes (see maze.escape)
  env MAZE_FIRST / MAZE_NETS as in maze.py

Copper that is already on the board is fixed (hard obstacle, as in maze.py).
Everything this router adds is soft: in every round each net is ripped up and
rerouted while other nets' copper only costs extra (present congestion) and
cells that were fought over keep getting more expensive (history). Nets give
way to each other until no two nets violate clearance. Rounds after the first
only reroute nets that are still in conflict. At the end only conflict-free
connections are written to the board. The A* and painting kernels are in
maze_core.c (compiled into out/ on first use).
"""
import ctypes
import os
import pathlib
import subprocess
import sys
import time

import numpy as np
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))
import maze as M  # noqa: E402

G = M.G


def core():
    c = ROOT / "scripts" / "pcbgen" / "maze_core.c"
    so = ROOT / "out" / "maze_core.so"
    if not so.exists() or so.stat().st_mtime < c.stat().st_mtime:
        so.parent.mkdir(exist_ok=True)
        subprocess.run(["gcc", "-O3", "-march=native", "-shared", "-fPIC", "-o", str(so), str(c), "-lm"],
                       check=True)
    lib = ctypes.CDLL(str(so))
    P = ctypes.c_void_p
    lib.astar.restype = ctypes.c_int
    lib.astar.argtypes = [ctypes.c_int] * 3 + [P] * 9 + [ctypes.c_int, P, P, ctypes.c_float,
                                                          ctypes.c_float, ctypes.c_int, P, ctypes.c_int]
    lib.paint.restype = None
    lib.paint.argtypes = [ctypes.c_int] * 3 + [P, P, ctypes.c_int, ctypes.c_int, P, P, P, P, ctypes.c_int]
    return lib


def ptr(a):
    assert a.flags["C_CONTIGUOUS"]
    return a.ctypes.data_as(ctypes.c_void_p)


def u8(a):
    return np.ascontiguousarray(a, dtype=np.uint8)


class Router:
    def __init__(self, g, b, widthf):
        self.g, self.b, self.w = g, b, widthf
        self.lib = core()
        self.L, self.NY, self.NX = g.isl.shape
        self.isl0 = g.isl.copy()
        self.present = set(np.unique(self.isl0).tolist()) - {0}
        self.keys = list(g.radii)
        shape = (self.L, self.NY, self.NX)
        self.occ = {k: np.zeros(shape, np.int16) for k in self.keys}
        self.mark = np.zeros(shape, np.int32)
        self.stamp = 0
        self.hist = np.zeros(shape, np.float32)
        self.histv = np.zeros((self.NY, self.NX), np.float32)
        self.routes = {}        # net -> list of paths (flat indices)
        self.hardfail = {}      # net -> number of island joins without any path
        self.out = np.zeros(400_000, np.int32)
        self.lc = np.array(M.LAYER_COST, np.float32)
        self.dp = np.array([{None: 0, "h": 1, "v": 2}[d] for d in M.DIR], np.int32)
        z = np.zeros((self.NY, self.NX), np.uint8)
        self.penh = u8(getattr(g, "pen_h", z)); self.penv = u8(getattr(g, "pen_v", z))

    # -- occupancy -------------------------------------------------------
    def entries(self, net, k):
        w = self.w(net)
        plane = self.NY * self.NX
        rad = self.g.radii[k]
        li, rr, cc, ra = [], [], [], []
        for p in self.routes.get(net, []):
            idx = np.asarray(p)
            l, rem = idx // plane, idx % plane
            r, c = rem // self.NX, rem % self.NX
            li.append(l); rr.append(r); cc.append(c)
            ra.append(np.full(len(idx), (rad + w / 2) / G + 0.75, np.float32))
            for vr, vc in self.vias(p):
                for l2 in range(self.L):
                    li.append([l2]); rr.append([vr]); cc.append([vc])
                    ra.append(np.array([(rad + M.VIA / 2) / G + 0.75], np.float32))
        if not li:
            return None
        cat = lambda xs, t: np.ascontiguousarray(np.concatenate(xs), dtype=t)
        return cat(li, np.int32), cat(rr, np.int32), cat(cc, np.int32), cat(ra, np.float32)

    def vias(self, p):
        plane = self.NY * self.NX
        out = []
        for a, b in zip(p, p[1:]):
            if a // plane != b // plane:
                out.append(((a % plane) // self.NX, a % self.NX))
        return out

    def paint(self, net, delta):
        for k in self.keys:
            e = self.entries(net, k)
            if e is None:
                return
            self.stamp += 1
            li, rr, cc, ra = e
            self.lib.paint(self.L, self.NY, self.NX, ptr(self.occ[k]), ptr(self.mark), self.stamp,
                           len(li), ptr(li), ptr(rr), ptr(cc), ptr(ra), delta)

    # -- routing ---------------------------------------------------------
    def route(self, net, pres):
        g = self.g
        ids = [i for i, n in g.net_of.items() if n == net and i in self.present]
        if len(ids) < 2:
            return
        code = self.b.FindNet(net).GetNetCode()
        w = self.w(net)
        hard_t = M.blocked_for(g, ("t", w), code)
        bmin = M.blocked_for(g, ("t", M.MIN_W), code)
        vb = M.blocked_for(g, ("v",), code).any(axis=0)
        own = np.isin(self.isl0, ids)
        vb |= M.dilate(own[0] | own[-1], M.disk(M.VIA / 2 / G + 1))
        vb = u8(vb)
        lab = np.where(own, self.isl0, 0).astype(np.int32)
        mult = np.ascontiguousarray(1.0 + self.hist, np.float32)
        add = np.ascontiguousarray(pres * self.occ[("t", w)], np.float32)
        vcost = np.ascontiguousarray(M.VIA_COST * (1.0 + self.histv)
                                     + pres * M.VIA_COST / 5 * self.occ[("v",)].max(axis=0), np.float32)
        mask = 1 if net in M.FONLY else (1 << self.L) - 1
        paths, fails = [], 0
        while True:
            cnt = np.bincount(lab.ravel())
            alive = [i for i in ids if i < len(cnt) and cnt[i] > 0]
            if len(alive) < 2:
                break
            src = min(alive, key=lambda i: cnt[i])
            srcm = lab == src
            tgtm = (lab != 0) & ~srcm
            hard = u8(hard_t & (bmin | ~(srcm | tgtm)))
            n = self.lib.astar(self.L, self.NY, self.NX, ptr(hard), ptr(u8(srcm)), ptr(u8(tgtm)), ptr(vb),
                               ptr(mult), ptr(add), ptr(vcost), ptr(self.penh), ptr(self.penv), mask,
                               ptr(self.lc), ptr(self.dp), ctypes.c_float(M.DIR_PENALTY),
                               ctypes.c_float(M.TURN_COST), 3_000_000, ptr(self.out), len(self.out))
            if n <= 0:
                fails += 1
                lab[srcm] = 0
                continue
            p = self.out[:n].copy()
            flat = lab.reshape(-1)
            hit = flat[p[-1]]
            flat[p] = src
            lab[lab == hit] = src
            paths.append(p)
        self.routes[net] = paths
        self.hardfail[net] = fails

    def conflicts(self, net):
        """Cells (flat) where this net's copper violates another soft net's."""
        w = self.w(net)
        occ_t = self.occ[("t", w)].reshape(-1)
        occ_v = self.occ[("v",)]
        plane = self.NY * self.NX
        bad_t, bad_v = [], []
        for p in self.routes.get(net, []):
            bad_t.append(p[occ_t[p] >= 2])
            for r, c in self.vias(p):
                if (occ_v[:, r, c] >= 2).any():
                    bad_v.append(r * self.NX + c)
        bt = np.concatenate(bad_t) if bad_t else np.zeros(0, np.int64)
        return bt, np.array(bad_v, np.int64), plane

    def path_ok(self, net, p):
        w = self.w(net)
        if (self.occ[("t", w)].reshape(-1)[p] >= 2).any():
            return False
        return not any((self.occ[("v",)][:, r, c] >= 2).any() for r, c in self.vias(p))


def main():
    board = sys.argv[1]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(os.environ.get("NEG_IN", str(pcb)))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    w = M.width_of()
    padnets = {p.GetNetname() for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname()}
    widths = sorted({w(n) for n in padnets} | {M.MIN_W})
    t0 = time.time()
    g = M.build(b, widths)
    esc = [r for r in os.environ.get("MAZE_ESCAPE", "").split(",") if r]
    if esc:
        M.escape(g, b, esc)
    nets = sorted({n for n in g.net_of.values() if n and n not in M.SKIP and not n.startswith("unconnected")})
    only = [n for n in os.environ.get("MAZE_NETS", "").split(",") if n]
    if only:
        nets = [n for n in nets if n in only]
    first = list(dict.fromkeys([n for n in os.environ.get("MAZE_FIRST", "").split(",") if n] + M.FIRST))
    order = [n for n in first if n in nets] + [n for n in nets if n not in first]
    R = Router(g, b, w)
    print(f"grid built in {time.time() - t0:.0f} s, {len(order)} nets", flush=True)
    iters = int(os.environ.get("NEG_ITER", "40"))
    pres = float(os.environ.get("NEG_PRES", "0.5"))
    grow = float(os.environ.get("NEG_PRES_GROW", "1.5"))
    hfac = float(os.environ.get("NEG_HIST", "0.4"))
    todo = order
    last_bad = []
    for it in range(1, iters + 1):
        t1 = time.time()
        for net in todo:
            R.paint(net, -1)
            R.route(net, pres)
            R.paint(net, +1)
        bad = []
        for net in order:
            bt, bv, _ = R.conflicts(net)
            if len(bt) or len(bv):
                bad.append(net)
                np.add.at(R.hist.reshape(-1), bt, hfac)
                np.add.at(R.histv.reshape(-1), bv, hfac)
        nfail = sum(R.hardfail.get(n, 0) for n in order)
        print(f"round {it}: rerouted {len(todo)}, conflicting nets {len(bad)}, "
              f"hard failures {nfail}, pres {pres:.2f}, {time.time() - t1:.0f} s", flush=True)
        if not bad:
            last_bad = []
            break
        todo = order if os.environ.get("NEG_ALL") else [n for n in order if n in bad]
        pres = min(pres * grow, float(os.environ.get("NEG_PRES_MAX", "1e12")))
        last_bad = bad
    done = skipped = 0
    for net in order:
        for p in R.routes.get(net, []):
            if not R.path_ok(net, p):
                skipped += 1
                continue
            cells = [(int(i // (R.NY * R.NX)), int(i % (R.NY * R.NX) // R.NX), int(i % R.NX)) for i in p]
            M.commit(g, b, net, w(net), cells)
            done += 1
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(os.environ.get("NEG_OUT", str(pcb)), b)
    pro.write_text(keep)
    print(f"negotiate: {done} connections written, {skipped} left out (conflict)")
    print("  still in conflict: " + ", ".join(n.split("/")[-1] for n in last_bad))
    plane = R.NY * R.NX
    for n in last_bad:
        bt, bv, _ = R.conflicts(n)
        pts = sorted({(round(g.xy(int(i % plane // R.NX), int(i % R.NX))[0]), round(g.xy(int(i % plane // R.NX), int(i % R.NX))[1]),
                       M.LAYERS[int(i // plane)]) for i in bt} | {(round(g.xy(int(i // R.NX), int(i % R.NX))[0]),
                       round(g.xy(int(i // R.NX), int(i % R.NX))[1]), "via") for i in bv}, key=str)
        print(f"    {n.split('/')[-1]}: " + " ".join(f"({x},{y},{l})" for x, y, l in pts[:12]))
    for n in order:
        if R.hardfail.get(n):
            print(f"  no path at all: {n} ({R.hardfail[n]}x)")


if __name__ == "__main__":
    main()
