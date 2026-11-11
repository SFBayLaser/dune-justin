#!/usr/bin/env python3
"""Which planes carry an exact (abs(trackID), x, y, z) IDE key?  Energy-weighted breakdown by the set of views, and channels per key.
Usage: sp_ide_planes.py in_supera.root [--events 3]"""
import argparse, collections, os
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[3]); a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery"); ROOT.gSystem.Load("liblardataobj_Simulation")
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
v = ROOT.std.vector(ROOT.std.string)(); v.push_back(a.f); ev = ROOT.gallery.Event(v)
for iev in a.events:
    ev.goToEntry(iev)
    hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag("gaushit")).product()
    scs = ev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag("tpcrawdecoder:simpleSC")).product()
    view = {h.Channel(): int(h.View()) for h in hits}; names = "UVW"
    d = collections.defaultdict(lambda: [set(), set(), 0., 0])        # views, channels, energy, n IDEs
    for sc in scs:
        vw = view.get(sc.Channel())
        if vw is None: continue
        for tdc in sc.TDCIDEMap():
            for ide in tdc.second:
                x = d[(abs(ide.trackID), ide.x, ide.y, ide.z)]; x[0].add(vw); x[1].add(sc.Channel()); x[2] += ide.energy; x[3] += 1
    tot = sum(x[2] for x in d.values()); en = collections.Counter(); cnt = collections.Counter(); multi = collections.Counter()
    for vs, chs, e, n in d.values():
        k = "".join(names[i] for i in sorted(vs)); en[k] += e; cnt[k] += 1
        if len(chs) > 1: multi[k] += 1
    print(f"=== event {iev}: {len(d)} exact keys ===")
    for k in sorted(en, key=lambda k: -en[k]): print(f"  planes {k:<4}: {cnt[k]:7d} keys, {100*en[k]/tot:5.1f}% of energy, {100*multi[k]/cnt[k]:5.1f}% of the keys on >1 channel")
