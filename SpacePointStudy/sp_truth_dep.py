#!/usr/bin/env python3
"""Deposit-level truth evaluation of space points (pre-Supera), for parameter scans.

A space point is TRUE if its hits share one deposit: per hit, the IDEs (SimChannel, from the WireCell drift simulation) in the hit's tick window
are summed per particle (abs(trackID)) and per VOX-cm voxel; a point is true if there is one voxel per hit, all of the same particle, each carrying
at least a fraction f of its hit's energy, with all pairwise distances <= delta (cm). IDE positions of one deposit differ a little between planes
(about 0.05 cm), so proximity, not identity. Per point the smallest achievable max-pairwise distance dmin(f) (searched below 0.5 cm) is computed,
so every delta <= 0.5 is read off. Position error of true points: distance between the point and the centroid of its matched voxels.
Truth triples (completeness): all (U hit, V hit, W hit) sets with a common deposit at (f, delta), built from the gaushit hits and the SimChannels
(independent of the builder, cached), weighted by the smallest voxel energy. Recovered = built as a 3-hit point; "any" = also a 2-hit point of a pair.

LONG HITS: a pulse that is too long for one Gaussian is cut into evenly spaced segments (peaks ~10 ticks apart, RMS 3.3, DegreesOfFreedom == 1) that
all share the pulse's [StartTick, EndTick]. Such segments get their own tick window (bounded by the midpoints to the neighbouring peaks) and every point
and truth triple is classed "normal" (no long hit) or "long" (at least one); the tables use --cls (default normal).

Usage:  sp_truth_dep.py point_dir... --sim-file in_supera.root --cache sample_truth_ide.pkl [--events N]
        -> point_dir/dep_eval.json, dep_eval.txt;   sp_truth_dep.py --table dir... [--pf 0.05 --pd 0.2 --cls normal|long|all]
        sp_truth_dep.py point_dir --oracle ...     (metric self-test on the truth triples; uses only the gaushit hits of the point file)
Run in the SL7 container via gallery_env.sh."""
import argparse, collections, json, math, os, pickle, random, sys
import numpy as np
from array import array

ap = argparse.ArgumentParser()
ap.add_argument("dirs", nargs="+")
ap.add_argument("--sim-file"); ap.add_argument("--cache"); ap.add_argument("--events", type=int, default=0, help="0 = all")
ap.add_argument("--fracs", type=float, nargs="+", default=[0.01, 0.05, 0.2]); ap.add_argument("--deltas", type=float, nargs="+", default=[0.2, 0.4])
ap.add_argument("--vox", type=float, default=0.2, help="cm; IDEs of one particle within a hit are summed per voxel")
ap.add_argument("--long-dof", type=float, default=1.5, help="hits with DegreesOfFreedom <= this are long-hit segments")
ap.add_argument("--table", action="store_true"); ap.add_argument("--pf", type=float, default=0.05); ap.add_argument("--pd", type=float, default=0.2)
ap.add_argument("--cls", default="normal", choices=["normal", "long", "all"])
ap.add_argument("--oracle", action="store_true")
ap.add_argument("--site", type=float, default=0.5, help="cm; truth sites = distinct (particle, cell) of the truth triples")
ap.add_argument("--trk-min", type=int, default=100, help="particles with at least this many sites are tracked individually")
ap.add_argument("--trk-r", type=float, default=1.0, help="cm; coverage radius for the per-particle fractions")
ap.add_argument("--cov", action="store_true", help="with --table: coverage table")
ap.add_argument("--dump", action="store_true", help="write point_dir/points.npy: one row per point with features and dmin(f) (columns: points_cols.json)")
ap.add_argument("--sp-tag", default="cluster3d"); ap.add_argument("--hit-tag", default="gaushit"); ap.add_argument("--sc-tag", default="tpcrawdecoder:simpleSC")
a = ap.parse_args()
DMAX = 0.5
CLS = ("normal", "long")


def table(dirs, pf, pd, cls):
    k = f"{pf:g}|{pd:g}"
    print(f"{'point':<22}{'pts/ev 3h':>10}{'pts/ev 2h':>10}{'true3':>7}{'true2':>7}{'true3/ev':>9}{'truth tri/ev':>13}{'recall':>8}{'E-w':>7}{'rec any':>9}{'err3 cm':>9}{'err2 cm':>9}"
          f"   ({cls} hits; true: common deposit, f>={pf:g}, delta<={pd:g} cm)")
    for d in dirs:
        f = os.path.join(d, "dep_eval.json")
        if not os.path.exists(f): continue
        r = json.load(open(f)); ne = r["events"]; x = r["res"][k][cls]; n3, n2 = x["n3"], x["n2"]
        print(f"{os.path.basename(d.rstrip('/')):<22}{n3 / ne:10.0f}{n2 / ne:10.0f}{100 * x['true3'] / max(1, n3):6.1f}%{100 * x['true2'] / max(1, n2):6.1f}%{x['true3'] / ne:9.0f}"
              f"{x['T'] / ne:13.0f}{100 * x['rec'] / max(1, x['T']):7.1f}%{100 * x['recw'] / max(1e-30, x['Tw']):6.1f}%{100 * x['recany'] / max(1, x['T']):8.1f}%"
              f"{x['err3']:9.2f}{x['err2']:9.2f}")


def cov_table(dirs, pf, pd):
    k = f"{pf:g}|{pd:g}"
    print(f"\n{'point':<22}{'sites/ev':>9}" + "".join(f"{kd + ' @' + format(R, 'g'):>12}" for kd in ("any", "p3", "true3") for R in (0.5, 1.0))
          + f"{'E-w any@1':>11}{'trks':>6}{'trk med any':>12}{'trk med true3':>14}{'<50% any':>9}{'hit3/hT':>9}{'hitany/hT':>10}"
          f"   (sites: truth cells of {a.site:g} cm, normal hits; covered = builder point within R cm; trk = particles with >= {a.trk_min} sites at {a.trk_r:g} cm)")
    med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")
    for d in dirs:
        f = os.path.join(d, "dep_eval.json")
        if not os.path.exists(f): continue
        r = json.load(open(f)); ne = r["events"]
        if k not in r["res"] or "cov" not in r["res"][k]: continue
        c = r["res"][k]["cov"]; t = r["res"][k]["trk"]; S = max(1, c.get("C_sites", 0)); ta = t["any"]; tt = t["true3"]
        print(f"{os.path.basename(d.rstrip('/')):<22}{S / ne:9.0f}" + "".join(f"{100 * c.get(f'C_{kd}_{R:g}', 0) / S:11.1f}%" for kd in ("any", "p3", "true3") for R in (0.5, 1.0))
              + f"{100 * c.get('Cw_any_1', 0) / max(1e-30, c.get('C_w', 0)):10.1f}%{len(ta):6d}{100 * med(ta):11.1f}%{100 * med(tt):13.1f}%"
              + f"{100 * sum(1 for x in ta if x < 0.5) / max(1, len(ta)):8.1f}%{100 * c.get('C_h3', 0) / max(1, c.get('C_hT', 0)):8.1f}%{100 * c.get('C_hany', 0) / max(1, c.get('C_hT', 0)):9.1f}%")


if a.table:
    (cov_table if a.cov else lambda d, f, dl: table(d, f, dl, a.cls))(a.dirs, a.pf, a.pd); sys.exit(0)

import ROOT
for l in ("libgallery", "liblardataobj_Simulation"): ROOT.gSystem.Load(l)
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/SpacePoint.h"')
ROOT.gInterpreter.Declare('double spxyz(const recob::SpacePoint& s, int i) { return s.XYZ()[i]; }')
ROOT.gInterpreter.Declare('double sperr(const recob::SpacePoint& s, int i) { return s.ErrXYZ()[i]; }')
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
def mk(f):
    v = ROOT.std.vector(ROOT.std.string)(); v.push_back(f); return ROOT.gallery.Event(v)
hyp = math.hypot
cache = {}
if a.cache and os.path.exists(a.cache): cache = pickle.load(open(a.cache, "rb"))
new_cache = False
simev = mk(a.sim_file)
hkey = lambda e, h: (e, h.Channel(), int(h.StartTick()), int(h.EndTick()), round(h.PeakTime(), 1))


def voxelize(ides):
    """((track,x,y,z,e), ...) -> [(track, x, y, z, E)] with the IDEs of one particle summed (energy-weighted position) per VOX-cm cell"""
    inv = 1. / a.vox; acc = {}
    for t, x, y, z, e in ides:
        k = (t, math.floor(x * inv), math.floor(y * inv), math.floor(z * inv)); r = acc.get(k)
        if r is None: acc[k] = [e * x, e * y, e * z, e]
        else: r[0] += e * x; r[1] += e * y; r[2] += e * z; r[3] += e
    return [(k[0], r[0] / r[3], r[1] / r[3], r[2] / r[3], r[3]) for k, r in acc.items() if r[3] > 0]


def hit_windows(ghits):
    """tick window per gaushit; long-hit segments of one pulse get disjoint windows split at the midpoints between neighbouring peaks"""
    win = [(int(h.StartTick()), int(h.EndTick())) for h in ghits]
    islong = [h.DegreesOfFreedom() <= a.long_dof for h in ghits]
    grp = collections.defaultdict(list)
    for i, h in enumerate(ghits):
        if islong[i]: grp[(h.Channel(), win[i])].append(i)
    for (ch, (s, en)), idxs in grp.items():
        if len(idxs) < 2: continue
        idxs.sort(key=lambda i: ghits[i].PeakTime()); pk = [ghits[i].PeakTime() for i in idxs]
        for j, i in enumerate(idxs):
            lo = s if j == 0 else int(math.ceil((pk[j - 1] + pk[j]) / 2))
            hi = en if j == len(idxs) - 1 else int(math.ceil((pk[j] + pk[j + 1]) / 2)) - 1
            win[i] = (lo, hi)
    return win, islong


def best_common(trs):
    """trs: per hit dict track -> [(x,y,z,e)]; -> (dmin below DMAX or DMAX, the best combination of voxels)"""
    common = set(trs[0]).intersection(*trs[1:]); best = DMAX; bc = None
    for t in common:
        L = [d[t] for d in trs]
        if len(L) == 2:
            for p in L[0]:
                for q in L[1]:
                    dd = hyp(p[0] - q[0], p[1] - q[1], p[2] - q[2])
                    if dd < best: best, bc = dd, (p, q)
        else:
            for p in L[0]:
                for q in L[1]:
                    dpq = hyp(p[0] - q[0], p[1] - q[1], p[2] - q[2])
                    if dpq >= best: continue
                    for r in L[2]:
                        m = max(dpq, hyp(p[0] - r[0], p[1] - r[1], p[2] - r[2]), hyp(q[0] - r[0], q[1] - r[1], q[2] - r[2]))
                        if m < best: best, bc = m, (p, q, r)
    return best, bc


def truth_triples(idx_vox, views, f, delta):
    """idx_vox[i] = [(track,x,y,z,E)] of gaushit i; -> dict code -> (weight, x, y, z of the W voxel, track) for (U,V,W) hit index triples with a common deposit"""
    N = len(views); grid = [collections.defaultdict(list) for _ in range(3)]; inv = 1. / delta
    for i, vx in enumerate(idx_vox):
        tot = sum(x[4] for x in vx)
        for t, x, y, z, e in vx:
            if e >= f * tot: grid[views[i]][(t, math.floor(x * inv), math.floor(y * inv), math.floor(z * inv))].append((i, x, y, z, e))
    T = {}
    nb = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]
    def near(g, cell, p):
        t, cx, cy, cz = cell; out = []
        for i, j, k in nb:
            for q in g.get((t, cx + i, cy + j, cz + k), ()):
                if hyp(p[1] - q[1], p[2] - q[2], p[3] - q[3]) <= delta: out.append(q)
        return out
    for cell, lst in grid[2].items():
        for w in lst:
            us = near(grid[0], cell, w)
            if not us: continue
            vs = near(grid[1], cell, w)
            for u in us:
                for v in vs:
                    if hyp(u[1] - v[1], u[2] - v[2], u[3] - v[3]) <= delta:
                        code = (u[0] * N + v[0]) * N + w[0]; m = min(u[4], v[4], w[4])
                        if code not in T or T[code][0] < m: T[code] = (m, w[1], w[2], w[3], cell[0])
    return T


def recall_counts(codes, ws, S3, S2, N, islong, c):
    for code, w in zip(codes, ws):
        iu, rem = divmod(code, N * N); iv, iw = divmod(rem, N)
        cl = "long" if (islong[iu] or islong[iv] or islong[iw]) else "normal"
        c[f"T_{cl}"] += 1; c[f"Tw_{cl}"] += w
        if code in S3: c[f"rec_{cl}"] += 1; c[f"recw_{cl}"] += w; c[f"recany_{cl}"] += 1
        elif (1, iu * N + iv) in S2 or (2, iu * N + iw) in S2 or (5, iv * N + iw) in S2: c[f"recany_{cl}"] += 1


DUMP_COLS = (["ev", "n", "long", "chi2", "err1_totq", "err3_asym", "x", "y", "z", "qU", "qV", "qW", "ampU", "ampV", "ampW", "rmsU", "rmsV", "rmsW",
              "dpeak", "deg_max", "deg_min", "deg_mean", "deg3_max", "pair_max", "viewmask"]); RS = (0.5, 1.0, 2.0); RC = 2.0; KINDS = ("any", "p3", "true3")


def mkgrid(pts):
    g = collections.defaultdict(list)
    for p in pts: g[(math.floor(p[0] / RC), math.floor(p[1] / RC), math.floor(p[2] / RC))].append(p)
    return g


def nearest(g, p):
    cx, cy, cz = math.floor(p[0] / RC), math.floor(p[1] / RC), math.floor(p[2] / RC); best = 1e9
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                for q in g.get((cx + i, cy + j, cz + k), ()):
                    dd = hyp(p[0] - q[0], p[1] - q[1], p[2] - q[2])
                    if dd < best: best = dd
    return best


def coverage(codes, ws, pos, trk, N, islong, grids, H3, H2, c, trkc):
    """Builder-independent completeness along the truth: SITES = distinct (particle, SITE-cm cell) of the normal truth triples (position of the
    triple's W voxel); a site is covered at radius R if a builder point (any = 2 or 3 hits, p3 = 3 hits, true3 = 3-hit point that is true) lies
    within R. Per particle with >= trk-min sites the covered fraction is kept. Hit coverage: hits of the truth triples that are in a 3-hit point / any point."""
    sites = {}; hT = set()
    for n, code in enumerate(codes):
        iu, rem = divmod(code, N * N); iv, iw = divmod(rem, N)
        if islong[iu] or islong[iv] or islong[iw]: continue
        hT.update((iu, iv, iw)); p = (pos[3 * n], pos[3 * n + 1], pos[3 * n + 2])
        k = (trk[n], math.floor(p[0] / a.site), math.floor(p[1] / a.site), math.floor(p[2] / a.site))
        r = sites.get(k)
        if r is None or ws[n] > r[0]: sites[k] = (ws[n], p)
    per = collections.defaultdict(list)
    for k, (w, p) in sites.items():
        d = {kind: nearest(g, p) for kind, g in grids.items()}
        c["C_sites"] += 1; c["C_w"] += w; per[k[0]].append(d)
        for kind in KINDS:
            for R in RS:
                if d[kind] <= R: c[f"C_{kind}_{R:g}"] += 1; c[f"Cw_{kind}_{R:g}"] += w
    for t, L in per.items():
        if len(L) >= a.trk_min:
            for kind in KINDS: trkc[kind].append(sum(1 for d in L if d[kind] <= a.trk_r) / len(L))
    c["C_hT"] += len(hT); c["C_h3"] += len(hT & H3); c["C_hany"] += len(hT & (H3 | H2))


def run_point(d):
    global new_cache
    ev = mk(os.path.join(d, "sp_art.root")); n_ev = ev.numberOfEventsInFile()
    if a.events: n_ev = min(n_ev, a.events)
    F, D = a.fracs, a.deltas; K = [(f, dl) for f in F for dl in D]
    nb = collections.Counter(); unmapped = 0
    cnt = collections.defaultdict(collections.Counter); errs = collections.defaultdict(list)
    orc = collections.defaultdict(collections.Counter); rng = random.Random(12345)
    trkc = collections.defaultdict(lambda: {k: [] for k in KINDS}); dump_rows = []
    for iev in range(n_ev):
        ev.goToEntry(iev); simev.goToEntry(iev)
        ea, sa = ev.eventAuxiliary(), simev.eventAuxiliary(); e = ea.event()
        assert (ea.run(), e) == (sa.run(), sa.event()), f"event mismatch {iev}"
        ghits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.hit_tag)).product()
        scs = simev.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag(a.sc_tag)).product()
        chan = {sc.Channel(): k for k, sc in enumerate(scs)}
        gidx = {}; views = []
        for i, h in enumerate(ghits): gidx[hkey(e, h)] = i; views.append(int(h.View()))
        N = len(views); win, islong = hit_windows(ghits)

        def ides_of(i):                                    # IDEs of gaushit i in its window: ((track,x,y,z,e), ...)
            global new_cache
            h = ghits[i]; t0, t1 = win[i]; ck = ("ide2", hkey(e, h), t0, t1)
            if ck in cache: return cache[ck]
            res = []; k_sc = chan.get(h.Channel())
            if k_sc is not None:
                for tdc in scs[k_sc].TDCIDEMap():
                    if tdc.first < t0 or tdc.first > t1: continue
                    for ide in tdc.second: res.append((abs(ide.trackID), ide.x, ide.y, ide.z, ide.energy))
            cache[ck] = tuple(res); new_cache = True
            return cache[ck]

        vcache = {}
        def vox(i):
            r = vcache.get(i)
            if r is None: r = vcache[i] = voxelize(ides_of(i))
            return r
        hf = {}                                            # (gaushit index, f) -> {track: [(x,y,z,e)]}
        def tracks(i, f):
            r = hf.get((i, f))
            if r is None:
                vx = vox(i); tot = sum(x[4] for x in vx); r = collections.defaultdict(list)
                for t, x, y, z, en in vx:
                    if en >= f * tot: r[t].append((x, y, z, en))
                hf[(i, f)] = r
            return r

        Tc = {}
        def truth_set(f, dl):
            global new_cache
            if (f, dl) not in Tc:
                tk = ("T3", e, f, dl, a.vox)
                if tk not in cache:
                    T = truth_triples([vox(i) for i in range(N)], views, f, dl); vl = list(T.values())
                    cache[tk] = (array("q", T.keys()), array("f", (v[0] for v in vl)), array("f", [c for v in vl for c in v[1:4]]), array("q", (v[4] for v in vl))); new_cache = True
                Tc[(f, dl)] = cache[tk]
            return Tc[(f, dl)]

        if a.oracle:
            by_ch = collections.defaultdict(list)
            for i in range(N):
                if views[i] == 2: by_ch[ghits[i].Channel()].append(i)
            Widx = [i for i in range(N) if views[i] == 2]
            for f, dl in K:
                codes, ws, _p, _t = truth_set(f, dl)
                sel = [c for c in codes if not (islong[c // (N * N)] or islong[(c // N) % N] or islong[c % N])]   # normal triples only
                rng.shuffle(sel); sel = sel[:4000]; o = orc[(f, dl)]
                for code in sel:
                    iu, iv, iw = code // (N * N), (code // N) % N, code % N
                    o["n_truth"] += 1
                    if best_common([tracks(iu, f), tracks(iv, f), tracks(iw, f)])[0] <= dl: o["ok_truth"] += 1
                    hw = ghits[iw]; c0 = hw.Channel(); pk = hw.PeakTime()
                    for k in (1, 2, 3, 5, 10):
                        cands = [j for ch in (c0 - k, c0 + k) for j in by_ch.get(ch, ()) if abs(ghits[j].PeakTime() - pk) <= 15 and not islong[j]]
                        if not cands: continue
                        j = min(cands, key=lambda j: abs(ghits[j].PeakTime() - pk)); o[f"n_shift{k}"] += 1
                        if best_common([tracks(iu, f), tracks(iv, f), tracks(j, f)])[0] <= dl: o[f"ok_shift{k}"] += 1
                    j = rng.choice(Widx); o["n_rand"] += 1
                    if best_common([tracks(iu, f), tracks(iv, f), tracks(j, f)])[0] <= dl: o["ok_rand"] += 1
                # recall plumbing: a random 30% of the truth triples as 3-hit points
                S3 = {c for c in codes if rng.random() < 0.3}; o["S3"] += len(S3); o["T"] += len(codes)
                c = collections.Counter(); recall_counts(codes, ws, S3, set(), N, islong, c)
                o["rec_normal"] += c["rec_normal"] + c["rec_long"]; o["recany"] += c["recany_normal"] + c["recany_long"]
            print(f"  oracle event {iev} done", flush=True); continue

        hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
        sps = ev.getValidHandle[ROOT.vector[ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        sp_hits = collections.defaultdict(list)
        for pair in asn: sp_hits[pair.second.key()].append(pair.first.key())
        raw = []; S3 = set(); S2 = set(); H3 = set(); H2 = set(); pts_all = []; pts_p3 = []; tp3 = collections.defaultdict(list)
        for sp, hl in sp_hits.items():
            n = len(hl)
            gi = [gidx.get(hkey(e, hits[k])) for k in hl]
            if None in gi: unmapped += 1; continue
            cl = "long" if any(islong[i] for i in gi) else "normal"; nb[(n, cl)] += 1
            order = sorted(range(n), key=lambda j: views[gi[j]]); gi = [gi[j] for j in order]
            if n == 3 and [views[i] for i in gi] == [0, 1, 2]: S3.add((gi[0] * N + gi[1]) * N + gi[2]); H3.update(gi)
            elif n == 2 and views[gi[0]] != views[gi[1]]: S2.add((views[gi[0]] * 3 + views[gi[1]], gi[0] * N + gi[1])); H2.update(gi)
            s_ = sps[sp]; p = (ROOT.spxyz(s_, 0), ROOT.spxyz(s_, 1), ROOT.spxyz(s_, 2))
            pts_all.append(p)
            if n == 3: pts_p3.append(p)
            dm = []
            for f in F:
                dmin, bc = best_common([tracks(i, f) for i in gi])
                dm.append(dmin if bc is not None else 9.)
                if bc is None: continue
                for dl in D:
                    if dmin <= dl:
                        cnt[(f, dl)][f"true{n}_{cl}"] += 1
                        if n == 3: tp3[(f, dl)].append(p)
                if len(errs[(n, f, cl)]) < 50000:
                    cen = [sum(q[j] for q in bc) / n for j in range(3)]
                    errs[(n, f, cl)].append((dmin, hyp(p[0] - cen[0], p[1] - cen[1], p[2] - cen[2])))
            if a.dump: raw.append((gi, n, p, ROOT.sperr(s_, 1), ROOT.sperr(s_, 3), s_.Chisq(), cl, dm))
        if a.dump:
            deg = collections.Counter(); deg3 = collections.Counter(); pair = collections.Counter(); hf_ = {}
            for gi, n, p, e1, e3, chi2, cl, dm in raw:
                for i in gi:
                    deg[i] += 1
                    if n == 3: deg3[i] += 1
                for x in range(n):
                    for y in range(x + 1, n): pair[(gi[x], gi[y])] += 1
            def hfeat(i):
                r = hf_.get(i)
                if r is None: h = ghits[i]; r = hf_[i] = (h.Integral(), h.PeakAmplitude(), h.RMS(), h.PeakTime())
                return r
            nan = float("nan"); rows = []
            for gi, n, p, e1, e3, chi2, cl, dm in raw:
                q = [nan] * 3; am = [nan] * 3; rm = [nan] * 3; pk = []; vm = 0
                for i in gi:
                    v = views[i]; I, A, R, T = hfeat(i); q[v] = I; am[v] = A; rm[v] = R; pk.append(T); vm |= 1 << v
                dg = [deg[i] for i in gi]; pm = max(pair[(gi[x], gi[y])] for x in range(n) for y in range(x + 1, n))
                rows.append([iev, n, int(cl == "long"), chi2, e1, e3, p[0], p[1], p[2], *q, *am, *rm, max(pk) - min(pk), max(dg), min(dg), sum(dg) / n,
                             max(deg3[i] for i in gi), pm, vm, *dm])
            dump_rows.append(np.array(rows, dtype=np.float32))
        g_all = mkgrid(pts_all); g_p3 = mkgrid(pts_p3)
        for f, dl in K:                                    # completeness against the builder-independent truth triples
            codes, ws, pos, trk = truth_set(f, dl); recall_counts(codes, ws, S3, S2, N, islong, cnt[(f, dl)])
            coverage(codes, ws, pos, trk, N, islong, {"any": g_all, "p3": g_p3, "true3": mkgrid(tp3[(f, dl)])}, H3, H2, cnt[(f, dl)], trkc[(f, dl)])
        print(f"  {d} event {iev}: points {len(sps)}", flush=True)

    if a.oracle:
        print(f"\noracle (normal truth triples only; first 4000 per event): percentage judged TRUE by the metric at the given f and delta")
        print(f"{'f':>6}{'delta':>7}{'truth as pts':>14}" + "".join(f"{'W shift ' + str(k):>10}" for k in (1, 2, 3, 5, 10)) + f"{'random W':>10}{'recall (30% in)':>17}{'any':>7}")
        for f, dl in K:
            o = orc[(f, dl)]; r = lambda x, n: f"{100 * o[x] / o[n]:9.1f}%" if o[n] else f"{'-':>10}"
            print(f"{f:6g}{dl:7g}{r('ok_truth', 'n_truth'):>14}" + "".join(r(f"ok_shift{k}", f"n_shift{k}") for k in (1, 2, 3, 5, 10)) + f"{r('ok_rand', 'n_rand'):>10}"
                  f"{100 * o['rec_normal'] / max(1, o['T']):16.1f}%{100 * o['recany'] / max(1, o['T']):6.1f}%   (n_truth {o['n_truth']}, shifts tested {o['n_shift1']}/{o['n_shift10']}, 30% sample = {100 * o['S3'] / max(1, o['T']):.1f}% of T)")
        return
    med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")
    res = {}
    for f, dl in K:
        c = cnt[(f, dl)]; res[f"{f:g}|{dl:g}"] = {}
        for cl in CLS + ("all",):
            sel = CLS if cl == "all" else (cl,); x = {}
            for n in (2, 3): x[f"n{n}"] = sum(nb[(n, s)] for s in sel); x[f"true{n}"] = sum(c[f"true{n}_{s}"] for s in sel)
            for k in ("T", "Tw", "rec", "recw", "recany"): x[k] = sum(c[f"{k}_{s}"] for s in sel)
            for n in (2, 3):
                ee = [er for s in sel for dd, er in errs[(n, f, s)] if dd <= dl]; x[f"err{n}"] = med(ee)
                ee.sort(); x[f"err{n}_p90"] = ee[int(0.9 * len(ee))] if ee else float("nan"); x[f"err{n}_p99"] = ee[int(0.99 * len(ee))] if ee else float("nan")
                x[f"far{n}"] = sum(1 for v in ee if v > 1.0) / len(ee) if ee else float("nan"); x[f"nerr{n}"] = len(ee)
            res[f"{f:g}|{dl:g}"][cl] = x
        res[f"{f:g}|{dl:g}"]["cov"] = {k: v for k, v in c.items() if k.startswith("C")}; res[f"{f:g}|{dl:g}"]["trk"] = trkc[(f, dl)]
    if a.dump:
        np.save(os.path.join(d, "points.npy"), np.concatenate(dump_rows))
        json.dump(DUMP_COLS + [f"dmin_f{f:g}" for f in F], open(os.path.join(d, "points_cols.json"), "w"))
    out = {"events": n_ev, "fracs": F, "deltas": D, "vox": a.vox, "long_dof": a.long_dof, "unmapped_points": unmapped, "res": res}
    json.dump(out, open(os.path.join(d, "dep_eval.json"), "w"), indent=1)
    with open(os.path.join(d, "dep_eval.txt"), "w") as fh:
        old, sys.stdout = sys.stdout, fh
        for cl in ("normal", "long"):
            for f, dl in K: table([d], f, dl, cl)
        sys.stdout = old
    for f, dl in K: table([d], f, dl, "normal")
    cov_table([d], a.pf, a.pd)
    if unmapped: print(f"  warning: {unmapped} points with a hit not found in {a.hit_tag}")


for d in a.dirs: run_point(d)
if a.cache and new_cache:
    tmp = f"{a.cache}.{os.getpid()}.tmp"; pickle.dump(cache, open(tmp, "wb"), protocol=4); os.replace(tmp, a.cache)
