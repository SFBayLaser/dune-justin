#!/usr/bin/env python3
"""Inspect long hits: DegreesOfFreedom, window width, segments sharing a window, and their share in space points.
Usage: sp_longhits.py sp_art.root [--events 0 3]"""
import argparse, collections
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[0, 3]); a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery")
tag = lambda s: ROOT.art.InputTag(s)
v = ROOT.std.vector(ROOT.std.string)(); v.push_back(a.f); ev = ROOT.gallery.Event(v)
for iev in a.events:
    ev.goToEntry(iev)
    g = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag("gaushit")).product()
    c3 = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag("cluster3d")).product()
    asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag("cluster3d")).product()
    print(f"=== event {iev}: {len(g)} gaushit, {len(c3)} cluster3d hits ===")
    dof = collections.Counter(round(h.DegreesOfFreedom()) for h in g)
    print("  DegreesOfFreedom (rounded):", dict(sorted(dof.items())[:12]))
    multi = collections.Counter(h.Multiplicity() for h in g); print("  Multiplicity:", dict(sorted(multi.items())[:12]))
    win = collections.Counter((h.Channel(), int(h.StartTick()), int(h.EndTick())) for h in g)
    shared = sum(1 for h in g if win[(h.Channel(), int(h.StartTick()), int(h.EndTick()))] > 1)
    print(f"  hits whose (channel,start,end) window is shared with another hit: {shared} ({100*shared/len(g):.1f}%)")
    long_ = [h for h in g if h.DegreesOfFreedom() <= 1.5]
    print(f"  hits with DegreesOfFreedom <= 1: {len(long_)} ({100*len(long_)/len(g):.1f}%)")
    for name, sel in (("DoF<=1", long_), ("DoF>1", [h for h in g if h.DegreesOfFreedom() > 1.5])):
        w = sorted(int(h.EndTick()) - int(h.StartTick()) for h in sel)
        if w: print(f"  {name}: window width ticks median {w[len(w)//2]}, 90% {w[int(.9*len(w))]}, max {w[-1]}")
    for h in long_[:6]:
        same = [x for x in g if x.Channel() == h.Channel() and int(x.StartTick()) == int(h.StartTick()) and int(x.EndTick()) == int(h.EndTick())]
        print(f"    ch {h.Channel()} view {int(h.View())} start {int(h.StartTick())} end {int(h.EndTick())} peak {h.PeakTime():.1f} rms {h.RMS():.1f} dof {h.DegreesOfFreedom():.0f} mult {h.Multiplicity()} idx {h.LocalIndex()}  hits in same window: {len(same)}, peaks {[round(x.PeakTime(),1) for x in same][:8]}")
    # share in space points
    islong = lambda h: h.DegreesOfFreedom() <= 1.5
    sp = collections.defaultdict(list)
    for p in asn: sp[p.second.key()].append(c3[p.first.key()])
    cnt = collections.Counter()
    for hl in sp.values():
        n = len(hl); nl = sum(1 for h in hl if islong(h)); cnt[(n, nl)] += 1
    for n in (2, 3):
        t = sum(c for (m, _), c in cnt.items() if m == n)
        print(f"  {n}-hit points: {t}; with >=1 long hit: {100*sum(c for (m, k), c in cnt.items() if m == n and k >= 1)/t:.1f}%; all hits long: {100*cnt[(n, n)]/t:.1f}%")
    # evenness of the peak spacing inside windows whose hits have DoF <= 1
    grp = collections.defaultdict(list)
    for h in long_: grp[(h.Channel(), int(h.StartTick()), int(h.EndTick()))].append(h)
    sizes = collections.Counter(min(len(l), 20) for l in grp.values()); print("  long-hit windows by number of segments:", dict(sorted(sizes.items())))
    cv = []
    for l in grp.values():
        if len(l) >= 4:
            pk = sorted(h.PeakTime() for h in l); gp = [b - a for a, b in zip(pk, pk[1:])]; m = sum(gp) / len(gp)
            cv.append((sum((x - m) ** 2 for x in gp) / len(gp)) ** .5 / m)
    if cv: cv.sort(); print(f"  peak-gap coefficient of variation in windows with >= 4 segments: median {cv[len(cv)//2]:.3f}, 90% {cv[int(.9*len(cv))]:.3f}")
    print(f"  long-hit rms values: {sorted({round(h.RMS(), 1) for h in long_})[:8]}; amplitudes median {sorted(h.PeakAmplitude() for h in long_)[len(long_)//2]:.1f} vs others {sorted(h.PeakAmplitude() for h in g if h.DegreesOfFreedom() > 1.5)[len(g)//2 - len(long_)//2]:.1f}")
