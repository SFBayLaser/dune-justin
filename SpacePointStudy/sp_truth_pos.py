#!/usr/bin/env python3
"""Hit-level truth matching of cluster3d space points with a positional check (extends sp_truth_purity.py).
Each cluster3d hit -> dominant particle (abs(trackID), energy summed over the hit's tick range) from the SimChannel
IDEs. The IDEs of that particle in the tick range give the truth positions that the hit could have come from.
For a space point, d_hit = distance (3D, cm) from the point to the nearest truth IDE of the hit's dominant particle;
d_point = max over its hits. Classes:
  pure          all hits share one particle (as in sp_truth_purity.py)
  pure & d<tol  pure and every hit has a truth deposit of that particle within tol of the point  -> "correct"
  pure & d>=tol same particle but wrong position (same-particle ghost)
Usage: sp_truth_pos.py art_file.root [--events 0 1 2] [--tols 0.5 1 2 5] [--sp-tag cluster3d] [--json out.json]
Run in the SL7 container with dunesw + gallery set up (see RUNS.md)."""
import argparse, collections, json, math, ROOT
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[0, 1, 2])
ap.add_argument("--sp-tag", default="cluster3d"); ap.add_argument("--sc-tag", default="tpcrawdecoder:simpleSC")
ap.add_argument("--tols", type=float, nargs="+", default=[0.5, 1., 2., 5.])
ap.add_argument("--json", default=None)
a = ap.parse_args()
ROOT.gSystem.Load("libgallery")
import os
ROOT.gSystem.Load("liblardataobj_Simulation")
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/SpacePoint.h"')
ROOT.gInterpreter.Declare('double spxyz(const recob::SpacePoint& s, int i) { return s.XYZ()[i]; }')
fl = ROOT.std.vector(ROOT.std.string)(); fl.push_back(a.f); ev = ROOT.gallery.Event(fl)
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
tot = collections.defaultdict(collections.Counter)
disp = collections.defaultdict(list)
dists = collections.defaultdict(list)       # n hits -> d_point of pure points (subsampled)
for iev in a.events:
    ev.goToEntry(iev)
    hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
    sps = ev.getValidHandle[ROOT.vector[ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
    scs = ev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag(a.sc_tag)).product()
    asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
    chan = {sc.Channel(): k for k, sc in enumerate(scs)}
    hid = {}                                          # hit key -> (particle, [(x, y, z), ...]) or (None, [])
    def truth(k):
        if k in hid: return hid[k]
        h = hits[k]; k_sc = chan.get(h.Channel()); res = (None, [])
        if k_sc is not None:
            t0, t1 = int(h.StartTick()), int(h.EndTick()); en = collections.defaultdict(float); pos = collections.defaultdict(list)
            for tdc in scs[k_sc].TDCIDEMap():
                if tdc.first < t0 or tdc.first > t1: continue
                for ide in tdc.second:
                    p = abs(ide.trackID); en[p] += ide.energy; pos[p].append((ide.x, ide.y, ide.z))
            if en:
                best = max(en, key=en.get); res = (best, pos[best])
        hid[k] = res; return res
    sp_hits = collections.defaultdict(list)
    for pair in asn: sp_hits[pair.second.key()].append(pair.first.key())
    for sp, hl in sp_hits.items():
        n = len(hl); c = tot[n]; c["all"] += 1
        tr = [truth(k) for k in hl]
        if any(t[0] is None for t in tr): c["untruthed"] += 1; continue
        ids = [t[0] for t in tr]
        top = collections.Counter(ids).most_common(1)[0][1]
        if top != n: c["partial" if top > n // 2 else "mixed"] += 1; continue
        c["pure"] += 1
        s_ = sps[sp]; p = (ROOT.spxyz(s_, 0), ROOT.spxyz(s_, 1), ROOT.spxyz(s_, 2))
        nearest = [min(t[1], key=lambda q: math.dist(p, q)) for t in tr]
        dh = [math.dist(p, q) for q in nearest]; d = max(dh)
        if len(disp[n]) < 20000:                      # signed displacement (point - nearest truth IDE) of the worst hit
            q = nearest[dh.index(d)]; disp[n].append((d, p[0] - q[0], p[1] - q[1], p[2] - q[2]))
        if len(dists[n]) < 200000: dists[n].append(d)
        for tol in a.tols:
            if d < tol: c[f"ok{tol}"] += 1
    print(f"event {iev}: hits {len(hits)}, spacepoints {len(sp_hits)}", flush=True)
print(f"\n{a.f}  events {a.events}")
hdr = f"{'hits':>5}{'points':>10}{'pure':>8}" + "".join(f"{'ok<'+str(t):>9}" for t in a.tols) + f"{'ghost(same)':>13}{'mixed':>8}{'partial':>9}{'untruthed':>11}"
print(hdr)
out = {}
for n in sorted(tot):
    c = tot[n]; t = c["all"]; f = lambda k: f"{100*c[k]/t:7.1f}%"
    last = f"ok{a.tols[-1]}"
    print(f"{n:>5}{t:>10}{f('pure')}" + "".join(f"{f'ok{tol}':>9}".replace(f'ok{tol}', f(f'ok{tol}')[-8:].rjust(9)) for tol in a.tols)
          + f"{100*(c['pure']-c[last])/t:12.1f}%{f('mixed')}{f('partial'):>9}{f('untruthed'):>11}")
    d = sorted(dists[n]); q = lambda x: d[int(x * (len(d) - 1))] if d else None
    out[str(n)] = {"counts": dict(c), "d_pct": {"50": q(.5), "90": q(.9), "99": q(.99)}}
    print(f"      d_point of pure points (cm): median {q(.5):.2f}  90% {q(.9):.2f}  99% {q(.99):.2f}")
med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")
for n in sorted(disp):
    for lo, hi in ((0, 1), (1, 5), (5, 30), (30, 1e9)):
        s = [r for r in disp[n] if lo <= r[0] < hi]
        print(f"  n={n} d in [{lo},{hi}) cm: {len(s):6d} pure pts; median signed dx {med([r[1] for r in s]):7.2f}  dy {med([r[2] for r in s]):7.2f}  dz {med([r[3] for r in s]):7.2f};"
              f" median |dx| {med([abs(r[1]) for r in s]):7.2f} |dy| {med([abs(r[2]) for r in s]):7.2f} |dz| {med([abs(r[3]) for r in s]):7.2f}")
if a.json: json.dump(out, open(a.json, "w"), indent=1)
