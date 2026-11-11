#!/usr/bin/env python3
"""Hit-level evaluation of one space point builder configuration, for parameter scans (pre-Supera).

Truth: SimChannels from a fixed input file (--sim-file, the *_supera.root the points were produced from), read with a second
gallery Event kept in step with the point file. Per hit: dominant particle (abs(trackID), energy summed over the hit's tick
range) and the positions of that particle's IDEs in the range (cached in --cache, a pickle shared by all points of a sample).

Per space point (n = 2 or 3 hits): pure = all hits share one particle; ok<tol = pure and every hit has a deposit of that
particle within tol cm (3D) of the point (a "correct" point).
Completeness (hit recovery): of the truthed gaushit hits, the fraction that belong to at least one correct point
(also energy-weighted by the hit integral, and per view). Also reported: fraction in any point, in any pure point.

Usage:  sp_truth_scan.py point_dir --sim-file in_supera.root --cache sample_truth.pkl [--events N] [--tols 1 2 5]
        -> point_dir/hit_eval.json and hit_eval.txt
        sp_truth_scan.py --table dir1 dir2 ...      -> comparison table of the hit_eval.json files
Run in the SL7 container via gallery_env.sh."""
import argparse, collections, json, math, os, pickle, sys

ap = argparse.ArgumentParser()
ap.add_argument("dirs", nargs="+")
ap.add_argument("--sim-file"); ap.add_argument("--cache"); ap.add_argument("--events", type=int, default=0, help="0 = all")
ap.add_argument("--tols", type=float, nargs="+", default=[1., 2., 5.])
ap.add_argument("--table", action="store_true"); ap.add_argument("--primary-tol", type=float, default=2.)
ap.add_argument("--sp-tag", default="cluster3d"); ap.add_argument("--hit-tag", default="gaushit")
ap.add_argument("--sc-tag", default="tpcrawdecoder:simpleSC")
a = ap.parse_args()


def table(dirs, ptol):
    rows = []
    for d in dirs:
        f = os.path.join(d, "hit_eval.json")
        if os.path.exists(f): rows.append((os.path.basename(d.rstrip("/")), json.load(open(f))))
    k = f"ok{ptol:g}"
    print(f"{'point':<28}{'pts/ev 3h':>10}{'pts/ev 2h':>10}{'pure3':>7}{'ok3':>7}{'ok2h':>7}{'mix3':>7}{'mix2':>7}"
          f"{'hits>=1pt':>10}{'hits ok':>9}{'E-w ok':>8}{'U':>6}{'V':>6}{'W':>6}   (ok = within {ptol:g} cm)")
    for name, r in rows:
        ne = r["events"]; c3 = r["classes"].get("3", {}); c2 = r["classes"].get("2", {}); h = r["hits"]
        pc = lambda c, x: 100 * c.get(x, 0) / c["all"] if c.get("all") else float("nan")
        hv = lambda v: 100 * h["views"][v].get(k, 0) / h["views"][v]["n"] if h["views"].get(v, {}).get("n") else float("nan")
        print(f"{name:<28}{c3.get('all', 0) / ne:10.0f}{c2.get('all', 0) / ne:10.0f}{pc(c3, 'pure'):6.1f}%{pc(c3, k):6.1f}%{pc(c2, k):6.1f}%"
              f"{pc(c3, 'mixed'):6.1f}%{pc(c2, 'mixed'):6.1f}%{100 * h['any'] / h['n']:9.1f}%{100 * h[k] / h['n']:8.1f}%"
              f"{100 * h['w_' + k] / h['w']:7.1f}%{hv('0'):6.1f}{hv('1'):6.1f}{hv('2'):6.1f}")


if a.table:
    table(a.dirs, a.primary_tol); sys.exit(0)

import ROOT
for l in ("libgallery", "liblardataobj_Simulation"): ROOT.gSystem.Load(l)
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/SpacePoint.h"')
ROOT.gInterpreter.Declare('double spxyz(const recob::SpacePoint& s, int i) { return s.XYZ()[i]; }')
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
mk = lambda f: ROOT.gallery.Event(_vec(f))
def _vec(f):
    v = ROOT.std.vector(ROOT.std.string)(); v.push_back(f); return v

cache = {}
if a.cache and os.path.exists(a.cache): cache = pickle.load(open(a.cache, "rb"))
new_cache = False
simev = mk(a.sim_file)


def run_point(d):
    global new_cache
    ev = mk(os.path.join(d, "sp_art.root"))
    n_ev = ev.numberOfEventsInFile()
    if a.events: n_ev = min(n_ev, a.events)
    cls = collections.defaultdict(collections.Counter)
    hit = collections.Counter(); views = collections.defaultdict(collections.Counter)
    for iev in range(n_ev):
        ev.goToEntry(iev); simev.goToEntry(iev)
        ea, sa = ev.eventAuxiliary(), simev.eventAuxiliary()
        assert (ea.run(), ea.event()) == (sa.run(), sa.event()), f"event mismatch {iev}: {ea.event()} vs {sa.event()}"
        hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
        ghits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.hit_tag)).product()
        sps = ev.getValidHandle[ROOT.vector[ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        scs = simev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag(a.sc_tag)).product()
        chan = {sc.Channel(): k for k, sc in enumerate(scs)}
        key = lambda h: (ea.event(), h.Channel(), int(h.StartTick()), int(h.EndTick()), round(h.PeakTime(), 1))

        def truth(h):
            global new_cache
            k = key(h)
            if k in cache: return cache[k]
            res = (None, ())
            k_sc = chan.get(h.Channel())
            if k_sc is not None:
                t0, t1 = k[2], k[3]; en = collections.defaultdict(float); pos = collections.defaultdict(list)
                for tdc in scs[k_sc].TDCIDEMap():
                    if tdc.first < t0 or tdc.first > t1: continue
                    for ide in tdc.second:
                        p = abs(ide.trackID); en[p] += ide.energy; pos[p].append((ide.x, ide.y, ide.z))
                if en:
                    best = max(en, key=en.get); res = (best, tuple(pos[best]))
            cache[k] = res; new_cache = True
            return res

        sp_hits = collections.defaultdict(list)
        for pair in asn: sp_hits[pair.second.key()].append(pair.first.key())
        any_pt, in_pure, in_ok = set(), set(), {t: set() for t in a.tols}
        for sp, hl in sp_hits.items():
            n = len(hl); c = cls[n]; c["all"] += 1
            hh = [hits[k] for k in hl]; keys = [key(h) for h in hh]; any_pt.update(keys)
            tr = [truth(h) for h in hh]
            if any(t[0] is None for t in tr): c["untruthed"] += 1; continue
            top = collections.Counter(t[0] for t in tr).most_common(1)[0][1]
            if top != n: c["partial" if top > n // 2 else "mixed"] += 1; continue
            c["pure"] += 1; in_pure.update(keys)
            s_ = sps[sp]; p = (ROOT.spxyz(s_, 0), ROOT.spxyz(s_, 1), ROOT.spxyz(s_, 2))
            d_pt = max(min(math.dist(p, q) for q in t[1]) for t in tr)
            for t in a.tols:
                if d_pt < t: c[f"ok{t:g}"] += 1; in_ok[t].update(keys)
        for h in ghits:                               # completeness over all truthed input hits
            if truth(h)[0] is None: continue
            k = key(h); w = float(h.Integral()); v = str(int(h.View()))
            for tgt in (hit, views[v]):
                tgt["n"] += 1; tgt["w"] += w
                if k in any_pt: tgt["any"] += 1
                if k in in_pure: tgt["pure"] += 1
                for t in a.tols:
                    if k in in_ok[t]: tgt[f"ok{t:g}"] += 1; tgt[f"w_ok{t:g}"] += w
        print(f"  {d} event {iev}: points {len(sps)}", flush=True)
    out = {"events": n_ev, "tols": a.tols, "classes": {str(n): dict(c) for n, c in cls.items()},
           "hits": {**dict(hit), "views": {v: dict(c) for v, c in views.items()}}}
    json.dump(out, open(os.path.join(d, "hit_eval.json"), "w"), indent=1)
    with open(os.path.join(d, "hit_eval.txt"), "w") as f:
        sys.stdout, old = f, sys.stdout
        table([d], a.primary_tol if a.primary_tol in a.tols else a.tols[0]); sys.stdout = old
    table([d], a.primary_tol if a.primary_tol in a.tols else a.tols[0])


for d in a.dirs: run_point(d)
if a.cache and new_cache:
    tmp = f"{a.cache}.{os.getpid()}.tmp"; pickle.dump(cache, open(tmp, "wb")); os.replace(tmp, a.cache)
