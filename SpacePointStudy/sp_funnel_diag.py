#!/usr/bin/env python3
"""Where do the truth triples die inside the builder?  Reads the log written by SnippetHit3DBuilderDUNEFast with DiagTripletFile / DiagOutFile set
(sp_funnel.py --dump-triples writes the triple list; the tool logs every pair and triplet evaluation that involves a listed triple) and the 3-hit points of
the builders, and tabulates the DEEPEST stage any evaluation of a truth triple reached.

Stage order (deepest wins; copies of a hit on several wire segments are separate evaluations):
  never examined | PH filter | pair: coarse time range | pair: time significance | pair: wires do not intersect | pairs ok but no triplet evaluated |
  trip: third hit time range | trip: third-wire window | trip: hit pair already matched | trip: partner pair fails | trip: chi-square | trip: overlap window |
  trip: asymmetry / peak separation | trip: ok (not in output) | built
Usage (SL7 container, gallery_env.sh):  sp_funnel_diag.py diag_triples.txt triplet_diag.txt --fast fast_dir --base baseline_dir"""
import argparse, collections, os
ap = argparse.ArgumentParser(); ap.add_argument("triples"); ap.add_argument("log"); ap.add_argument("--fast", required=True); ap.add_argument("--base")
ap.add_argument("--sp-tag", default="cluster3d")
a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery")
tag = lambda s: ROOT.art.InputTag(s)
def mk(f):
    v = ROOT.std.vector(ROOT.std.string)(); v.push_back(f); return ROOT.gallery.Event(v)
key = lambda h: (h.Channel(), int(h.StartTick()), int(h.EndTick()), int(round(h.PeakTime() * 10)))

STAGES = ["never examined", "PH filter", "pair not examined", "pair: coarse time range", "pair: time significance", "pair: wires do not intersect", "pairs ok, no triplet evaluated",
          "trip: third hit time range", "trip: third-wire window", "trip: hit pair already matched", "trip: partner pair fails", "trip: chi-square", "trip: overlap window",
          "trip: asymmetry / peak separation", "trip: ok, not in output", "built"]
S = {n: i for i, n in enumerate(STAGES)}
TRIP = {1: "trip: third hit time range", 2: "trip: third-wire window", 3: "trip: hit pair already matched", 4: "trip: partner pair fails", 5: "trip: partner pair fails",
        6: "trip: chi-square", 7: "trip: overlap window", 8: "trip: asymmetry / peak separation", 9: "trip: asymmetry / peak separation", 0: "trip: ok, not in output"}
PAIR = {1: "pair: coarse time range", 2: "pair: time significance", 3: "pair: wires do not intersect", 0: "pairs ok, no triplet evaluated"}

triples = {}                                         # (ev, idx) -> (k_u, k_v, k_w)
for line in open(a.triples):
    v = list(map(int, line.split())); triples[(v[0], v[1])] = (tuple(v[2:6]), tuple(v[6:10]), tuple(v[10:14]))
deep = {}                                            # (ev, idx) -> stage index
tdetail = collections.defaultdict(list)
pairs = collections.defaultdict(dict)                # k -> plane pair -> [ok seen, worst failure rank]
trip = {}; ph = set()
for line in open(a.log):
    f = line.split()
    ev, idx, stage, code, val = int(f[1]), int(f[2]), f[3], int(f[4]), float(f[5]); k = (ev, idx)
    if stage == "PHSKIP": ph.add(k)
    elif stage == "PAIR":
        pp = tuple(sorted((int(f[6].split(":")[0]), int(f[7].split(":")[0]))))
        d = pairs[k].setdefault(pp, [False, -1])
        if code == 0: d[0] = True
        else: d[1] = max(d[1], S[PAIR[code]])
    else:
        r = S[TRIP[code]]
        if r > trip.get(k, -1): trip[k] = r
        if code == 2: tdetail[k].append(val)
for k in set(pairs) | set(trip) | ph:
    pp = pairs.get(k, {}); bad = [d for d in pp.values() if not d[0]]
    if k in trip: deep[k] = trip[k]
    elif bad: deep[k] = max(d[1] for d in bad)
    elif k in ph and len(pp) < 2: deep[k] = S["PH filter"]
    elif len(pp) < 2: deep[k] = S["pair not examined"]
    else: deep[k] = S["pairs ok, no triplet evaluated"]


def built_sets(d, evs):
    ev = mk(os.path.join(d, "sp_art.root")); out = {}
    for iev in range(ev.numberOfEventsInFile()):
        ev.goToEntry(iev); e = ev.eventAuxiliary().event()
        if e not in evs: continue
        hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
        asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        sp_hits = collections.defaultdict(list)
        for p in asn: sp_hits[p.second.key()].append(p.first.key())
        s = set()
        for sp, hl in sp_hits.items():
            if len(hl) != 3: continue
            hs = sorted((hits[k] for k in hl), key=lambda h: int(h.View()))
            if [int(h.View()) for h in hs] == [0, 1, 2]: s.add((e,) + tuple(key(h) for h in hs))
        out[e] = s
    return out


evs = {k[0] for k in triples}
BF = built_sets(a.fast, evs); BB = built_sets(a.base, evs) if a.base else {}
tab = collections.Counter(); n = 0
for (e, idx), ks in triples.items():
    n += 1
    inF = (e,) + ks in BF.get(e, ()); inB = (e,) + ks in BB.get(e, ())
    st = S["built"] if inF else deep.get((e, idx), 0)
    tab[(STAGES[st], inB, inF)] += 1
print(f"{n} normal truth triples, {len(evs)} events; Fast builds {sum(v for k, v in tab.items() if k[2])} ({100 * sum(v for k, v in tab.items() if k[2]) / n:.1f}%)"
      + (f", baseline builds {sum(v for k, v in tab.items() if k[1])} ({100 * sum(v for k, v in tab.items() if k[1]) / n:.1f}%)" if a.base else ""))
print(f"\n{'deepest stage reached in the Fast tool':<42}{'all':>9}{'%':>7}{'  not built by baseline':>25}{'%':>7}")
nb = sum(v for k, v in tab.items() if not k[1])
for name in STAGES:
    al = sum(v for k, v in tab.items() if k[0] == name); nbb = sum(v for k, v in tab.items() if k[0] == name and not k[1])
    if al: print(f"{name:<42}{al:9d}{100 * al / n:6.1f}%{nbb:25d}{100 * nbb / max(1, nb):6.1f}%")
print(f"\nbuilt by the baseline but not by Fast: {sum(v for k, v in tab.items() if k[1] and not k[2])};  built by Fast but not by the baseline: {sum(v for k, v in tab.items() if k[2] and not k[1])}")
import numpy as np
d = [min(v) for k, v in tdetail.items() if v and deep.get(k) == S['trip: third-wire window']]
if d: print(f"third-wire window failures (best candidate per triple, cm): median {np.median(d):.2f}, 90% {np.quantile(d, .9):.2f}")
