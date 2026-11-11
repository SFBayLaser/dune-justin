#!/usr/bin/env python3
"""How close are the IDE positions of one deposit seen on different planes?  For each W-plane IDE (same abs(trackID)), the nearest IDE
on the U and on the V plane (3D distance, cm), energy-weighted histogram.  Usage: sp_ide_nn.py in_supera.root [--events 3]"""
import argparse, collections, math, os
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[3]); ap.add_argument("--cell", type=float, default=0.5)
a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery"); ROOT.gSystem.Load("liblardataobj_Simulation")
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
v = ROOT.std.vector(ROOT.std.string)(); v.push_back(a.f); ev = ROOT.gallery.Event(v)
edges = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
for iev in a.events:
    ev.goToEntry(iev)
    hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag("gaushit")).product()
    scs = ev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag("tpcrawdecoder:simpleSC")).product()
    view = {h.Channel(): int(h.View()) for h in hits}
    grid = [collections.defaultdict(list) for _ in range(3)]; w = []
    c = a.cell
    for sc in scs:
        vw = view.get(sc.Channel())
        if vw is None: continue
        for tdc in sc.TDCIDEMap():
            for ide in tdc.second:
                t = abs(ide.trackID); p = (ide.x, ide.y, ide.z)
                grid[vw][(t, int(p[0] // c), int(p[1] // c), int(p[2] // c))].append(p)
                if vw == 2: w.append((t, p, ide.energy))
    def nearest(vw, t, p):
        ix, iy, iz = (int(q // c) for q in p); best = 1e9
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid[vw].get((t, ix + dx, iy + dy, iz + dz), ()):
                        d = math.dist(p, q)
                        if d < best: best = d
        return best
    print(f"=== event {iev}: {len(w)} W-plane IDEs ===")
    for vw, name in ((0, "U"), (1, "V")):
        h = collections.Counter(); tot = 0.
        for t, p, e in w:
            d = nearest(vw, t, p); tot += e
            h[next((i for i, x in enumerate(edges) if d < x), len(edges))] += e
        cum = 0.; s = []
        for i, x in enumerate(edges): cum += h[i]; s.append(f"<{x}: {100*cum/tot:.1f}%")
        print(f"  nearest same-particle IDE on {name}: " + "  ".join(s) + f"  none within ~{c} cm cell: {100*h[len(edges)]/tot:.1f}%")
