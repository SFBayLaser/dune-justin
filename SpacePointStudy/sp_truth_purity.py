#!/usr/bin/env python3
"""Hit-level truth matching of cluster3d space points (traditional approach).
Each cluster3d hit -> dominant particle from the SimChannel (SimChannel::TrackIDEs over the hit's tick range; the
track ID is taken as abs(trackID) so EM-shower daughters, stored negative, map to their shower parent).
Each space point (3-hit or 2-hit) is then:  pure = all hits share one particle, partial = a majority share one
(3-hit only), mixed = no majority, untruthed = at least one hit has no truth.
Usage: sp_truth_purity.py art_file.root [--events 0 1 2] [--sp-tag cluster3d] [--min-frac 0.0]
Run in the SL7 container with dunesw + gallery set up (see RUNS.md). Gallery reads the art file directly from PyROOT."""
import argparse, collections, ROOT
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--events", type=int, nargs="+", default=[0, 1, 2])
ap.add_argument("--sp-tag", default="cluster3d"); ap.add_argument("--sc-tag", default="tpcrawdecoder:simpleSC")
ap.add_argument("--min-frac", type=float, default=0.0, help="dominant particle must have at least this energy fraction on the hit")
a = ap.parse_args()
ROOT.gSystem.Load("libgallery")
fl = ROOT.std.vector(ROOT.std.string)(); fl.push_back(a.f); ev = ROOT.gallery.Event(fl)
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
tot = collections.defaultdict(collections.Counter)
for iev in a.events:
    ev.goToEntry(iev)
    hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
    scs = ev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag(a.sc_tag)).product()
    asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
    chan = {sc.Channel(): k for k, sc in enumerate(scs)}
    hid = {}                                          # hit key -> dominant particle (or None)
    def dominant(k):
        if k in hid: return hid[k]
        h = hits[k]; k_sc = chan.get(h.Channel()); res = None
        if k_sc is not None:
            best = 0.; e_tot = 0.
            for t in scs[k_sc].TrackIDEs(int(h.StartTick()), int(h.EndTick())):
                e_tot += t.energy
                if t.energy > best: best, res = t.energy, abs(t.trackID)
            if res is not None and e_tot > 0 and best / e_tot < a.min_frac: res = None
        hid[k] = res; return res
    sp_hits = collections.defaultdict(list)
    for pair in asn: sp_hits[pair.second.key()].append(pair.first.key())
    for sp, hl in sp_hits.items():
        n = len(hl); ids = [dominant(k) for k in hl]; c = tot[n]; c["all"] += 1
        if any(i is None for i in ids): c["untruthed"] += 1
        else:
            top = collections.Counter(ids).most_common(1)[0][1]
            c["pure" if top == n else ("partial" if top > n // 2 else "mixed")] += 1
    print(f"event {iev}: hits {len(hits)}, spacepoints {len(sp_hits)}")
print(f"\n{a.f}  events {a.events}")
print(f"{'hits':>5}{'points':>10}{'pure':>9}{'partial':>9}{'mixed':>9}{'untruthed':>11}")
for n in sorted(tot):
    c = tot[n]; t = c["all"]; f = lambda k: f"{100*c[k]/t:8.1f}%"
    print(f"{n:>5}{t:>10}{f('pure')}{f('partial')}{f('mixed')}{f('untruthed'):>11}")
