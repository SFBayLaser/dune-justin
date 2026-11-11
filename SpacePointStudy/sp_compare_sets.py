#!/usr/bin/env python3
"""What are the extra points of builder B compared with builder A?  Points are matched by their hit set
(hit key = event, channel, start tick, end tick, peak time), truth from the cache written by sp_truth_scan.py.
Categories for every point of B (and A, for symmetry):
  shared      the same hit set is a point in the other builder
  superset    n=3 point containing the hit pair of a 2-hit point of the other builder
  subset      n=2 point whose pair is part of a 3-hit point of the other builder
  recombined  all hits are used by the other builder, but never in this combination
  new hits    at least one hit is not used by any point of the other builder
Also: duplicate hit sets inside one builder (same hits, several positions), points per hit.
Usage: sp_compare_sets.py A_dir B_dir --cache truth_cache.pkl [--events 0 1 2] [--tol 2]"""
import argparse, collections, itertools, math, os, pickle, sys
ap = argparse.ArgumentParser(); ap.add_argument("A"); ap.add_argument("B"); ap.add_argument("--cache", required=True)
ap.add_argument("--events", type=int, nargs="+", default=list(range(8))); ap.add_argument("--tol", type=float, default=2.)
a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery")
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/SpacePoint.h"')
ROOT.gInterpreter.Declare('double spxyz(const recob::SpacePoint& s, int i) { return s.XYZ()[i]; }')
tag = lambda s: ROOT.art.InputTag(s)
cache = pickle.load(open(a.cache, "rb"))
def vec(f):
    v = ROOT.std.vector(ROOT.std.string)(); v.push_back(f); return v

def load(d, iev):
    """-> list of (frozenset(keys), n, xyz, pure, dist, particle) for one event"""
    ev = ROOT.gallery.Event(vec(os.path.join(d, "sp_art.root"))); ev.goToEntry(iev); e = ev.eventAuxiliary().event()
    hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag("cluster3d")).product()
    sps = ev.getValidHandle[ROOT.vector[ROOT.recob.SpacePoint]](tag("cluster3d")).product()
    asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag("cluster3d")).product()
    spk = collections.defaultdict(list)
    for p in asn: spk[p.second.key()].append(p.first.key())
    out = []
    for sp, hl in spk.items():
        keys = [(e, hits[k].Channel(), int(hits[k].StartTick()), int(hits[k].EndTick()), round(hits[k].PeakTime(), 1)) for k in hl]
        tr = [cache.get(k, (None, ())) for k in keys]
        s = sps[sp]; p = tuple(ROOT.spxyz(s, i) for i in range(3))
        if any(t[0] is None for t in tr): out.append((frozenset(keys), len(keys), p, None, None)); continue
        pure = len({t[0] for t in tr}) == 1
        d = max(min(math.dist(p, q) for q in t[1]) for t in tr) if pure else None
        out.append((frozenset(keys), len(keys), p, pure, d))
    return out

def classify(P, Q):
    """categories of points in P relative to Q"""
    qsets = {x[0] for x in Q}; qhits = set().union(*qsets) if qsets else set()
    pairs3 = collections.defaultdict(int)             # pairs contained in 3-hit points of Q
    for s in qsets:
        if len(s) == 3:
            for pr in itertools.combinations(sorted(s), 2): pairs3[frozenset(pr)] += 1
    q2 = {s for s in qsets if len(s) == 2}
    res = []
    for s, n, p, pure, d in P:
        if s in qsets: c = "shared"
        elif n == 3 and any(frozenset(pr) in q2 for pr in itertools.combinations(sorted(s), 2)): c = "superset"
        elif n == 2 and s in pairs3: c = "subset"
        elif s <= qhits: c = "recombined"
        else: c = "new hits"
        res.append((c, n, pure, d))
    return res

stat = {"A": collections.defaultdict(list), "B": collections.defaultdict(list)}
extra = collections.Counter()
for iev in a.events:
    PA, PB = load(a.A, iev), load(a.B, iev)
    for name, P, Q in (("A", PA, PB), ("B", PB, PA)):
        for c, n, pure, d in classify(P, Q): stat[name][(c, n)].append((pure, d))
        cnt = collections.Counter(x[0] for x in P)
        extra[f"{name} duplicate hit-sets"] += sum(v - 1 for v in cnt.values() if v > 1)
        extra[f"{name} points"] += len(P)
        hp = collections.Counter(k for x in P if x[1] == 3 for k in x[0]); extra[f"{name} 3-hit pts"] += sum(1 for x in P if x[1] == 3)
        extra[f"{name} hits in 3-hit pts"] += len(hp)
    # position difference for shared sets
    pa = {x[0]: x[2] for x in PA}
    dd = [math.dist(pa[x[0]], x[2]) for x in PB if x[0] in pa]
    extra["shared pos diff >0.01 cm"] += sum(1 for v in dd if v > 0.01); extra["shared pairs"] += len(dd)
    print(f"event {iev}: A {len(PA)} B {len(PB)} shared {len(dd)}", flush=True)

def show(name, label):
    print(f"\nPoints of {label} relative to the other builder (tol {a.tol:g} cm):")
    print(f"{'category':<12}{'hits':>5}{'points':>9}{'pure':>8}{'ok':>8}{'mixed':>8}{'untr':>7}{'median d (pure)':>17}")
    for (c, n), L in sorted(stat[name].items(), key=lambda kv: (kv[0][1], kv[0][0])):
        t = len(L); pu = sum(1 for p, d in L if p); ok = sum(1 for p, d in L if p and d < a.tol)
        un = sum(1 for p, d in L if p is None); ds = sorted(d for p, d in L if p)
        print(f"{c:<12}{n:>5}{t:>9}{100*pu/t:7.1f}%{100*ok/t:7.1f}%{100*(t-pu-un)/t:7.1f}%{100*un/t:6.1f}%{(ds[len(ds)//2] if ds else float('nan')):17.2f}")
show("A", "A = " + os.path.basename(a.A.rstrip("/"))); show("B", "B = " + os.path.basename(a.B.rstrip("/")))
print()
for k, v in sorted(extra.items()): print(f"{k}: {v}")
for n in "AB":
    print(f"{n}: mean 3-hit points per hit (hits in at least one) = {extra[n + ' 3-hit pts'] * 3 / max(1, extra[n + ' hits in 3-hit pts']):.2f}  (summed over events)")
