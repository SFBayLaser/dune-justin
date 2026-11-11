#!/usr/bin/env python3
"""Feasibility check for deposit-level truth matching, one or a few events of a *_supera.root (gaushit + SimChannels):
 1. Is a G4 deposit recognisable across planes?  IDEs keyed by (abs(trackID), x, y, z) exactly; count the views (U/V/W channels that
    carry hits) each key appears in, energy-weighted. Then the same with positions rounded to 0.1 cm.
 2. Alignment of hit windows with IDE TDC: for each hit, energy-weighted mean TDC of the IDEs on its channel in [start-W, end+W]
    minus the hit peak time (per view), and the fraction of hits with no IDE inside [start, end].
Usage: sp_ide_check.py in_supera.root [--events 3 0] [--max-hits 4000]"""
import argparse, collections, os, statistics
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[3])
ap.add_argument("--max-hits", type=int, default=4000); ap.add_argument("--win", type=int, default=30)
a = ap.parse_args()
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
    view = {}
    for h in hits: view[h.Channel()] = int(h.View())
    print(f"\n=== event {iev}: {len(hits)} hits, {len(scs)} SimChannels, {len(view)} channels with hits ===", flush=True)
    byview = collections.defaultdict(list)
    for h in hits: byview[int(h.View())].append(h)
    # --- 1. deposit identity across planes
    ex = collections.defaultdict(lambda: [set(), 0.]); rd = collections.defaultdict(lambda: [set(), 0.]); nide = 0
    chmap = {}
    for sc in scs:
        vw = view.get(sc.Channel())
        if vw is None: continue
        chmap[sc.Channel()] = sc
        for tdc in sc.TDCIDEMap():
            for ide in tdc.second:
                nide += 1; e = ide.energy; t = abs(ide.trackID)
                k1 = (t, ide.x, ide.y, ide.z); k2 = (t, round(ide.x, 1), round(ide.y, 1), round(ide.z, 1))
                for d, k in ((ex, k1), (rd, k2)): d[k][0].add(vw); d[k][1] += e
    print(f"IDEs on channels with hits: {nide}")
    for name, d in (("exact (trackID,x,y,z)", ex), ("rounded to 0.1 cm", rd)):
        tot = sum(x[1] for x in d.values()); cnt = collections.Counter(); en = collections.Counter()
        for vs, e in d.values(): cnt[len(vs)] += 1; en[len(vs)] += e
        print(f"  {name}: {len(d)} deposits; planes seen: " + ", ".join(f"{n}: {cnt[n]} ({100*en[n]/tot:.1f}% of energy)" for n in (3, 2, 1)))
    # --- 2. hit window vs TDC
    print(f"hit window alignment (IDE window [start-{a.win}, end+{a.win}]), mean IDE TDC minus hit peak time, ticks:")
    for vw in sorted(byview):
        hl = byview[vw][:a.max_hits]; off = []; none_in = 0; none_any = 0; inside = []
        for h in hl:
            sc = chmap.get(h.Channel())
            if sc is None: none_any += 1; continue
            t0, t1 = int(h.StartTick()), int(h.EndTick()); se = sw = 0.; ein = 0.; etot = 0.
            for tdc in sc.TDCIDEMap():
                if tdc.first < t0 - a.win or tdc.first > t1 + a.win: continue
                e = sum(i.energy for i in tdc.second); se += e * tdc.first; sw += e; etot += e
                if t0 <= tdc.first <= t1: ein += e
            if sw == 0: none_any += 1; continue
            off.append(se / sw - h.PeakTime()); inside.append(ein / etot)
            if ein == 0: none_in += 1
        n = len(hl); q = statistics.quantiles(off, n=20) if len(off) > 20 else [float("nan")] * 19
        print(f"  view {vw}: {n} hits; no IDE near: {100*none_any/n:.1f}%, none inside [start,end]: {100*none_in/n:.1f}%; "
              f"offset median {statistics.median(off):+.2f} (5%..95%: {q[0]:+.1f} .. {q[-1]:+.1f}); "
              f"energy fraction of window inside [start,end] median {statistics.median(inside):.2f}")
