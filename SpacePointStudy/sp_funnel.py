#!/usr/bin/env python3
"""Failure funnel for the truth triples: why does the (baseline) builder not make a 3-hit point for a truth triple?

Truth triples = (U hit, V hit, W hit) sets with a common deposit (sp_truth_dep.py, cached: truth_ide_cache.pkl, key ("T3", event, f, delta, vox)); normal hits only.
For every truth triple the baseline (SnippetHit3DBuilderDUNE) hit-level criteria are re-evaluated from the gaushit hits alone (no geometry):
  A  snippet overlap     the three [StartTick, EndTick] windows overlap the earliest one (the snippet iterators of BuildHitPairMapByTPC)
  D  pulse-height filter hit skipped in findGoodHitPairs (multi-hit snippet, amplitude < PulseHeightFraction * snippet max and < PHLowSelection);
                         approximation: snippet = same view and same (start, end) ticks, all TPCs pooled
  B  pair time cuts      |dt| < DeltaPeakTimeSig * sqrt(s1^2 + s2^2) for all three hit pairs (makeHitPair; s = RMS, x1.5 if long)
  C  triplet chi-square  < MaxHitChiSquare (makeHitTriplet)
A triple that passes A-D but is not built is lost to something this script cannot see: the wire geometry (wires intersect, third wire within 0.95 pitch),
the candidate selection (first match wins, pair exclusivity), or the pulse never being paired. If the second builder (--other) makes it as a 3-hit point it is
counted as 'selection', otherwise 'geometry or other'.
Also: median/spread of the signed hit time differences of the truth triples per plane pair (systematic plane offsets).
Usage (SL7 container, gallery_env.sh):  sp_funnel.py baseline_dir --other new_default_dir --cache truth_ide_cache.pkl [--events 8] [--f 0.05 --delta 0.2]"""
import argparse, collections, math, os, pickle
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("d"); ap.add_argument("--other"); ap.add_argument("--also", nargs="*", default=[], help="more builders: how many of the unbuilt-but-passing triples each one makes"); ap.add_argument("--cache", required=True)
ap.add_argument("--events", type=int, default=8); ap.add_argument("--f", type=float, default=0.05); ap.add_argument("--delta", type=float, default=0.2); ap.add_argument("--vox", type=float, default=0.2)
ap.add_argument("--dpts", type=float, default=1.7); ap.add_argument("--chi2", type=float, default=10.); ap.add_argument("--phf", type=float, default=0.5); ap.add_argument("--phl", type=float, default=20.)
ap.add_argument("--geom", action="store_true", help="add the wire-geometry stage: lattice per TPC plane fitted from the builder's own 3-hit points, then the third-wire window test at the truth deposit position"); ap.add_argument("--dump-triples", help="write the normal truth triples as hit keys for the builder diagnostics (DiagTripletFile)"); ap.add_argument("--roi", action="store_true", help="snippet for the pulse-height filter = same channel and ticks (lower bound; default pools all channels with the same ticks, upper bound)"); ap.add_argument("--long-dof", type=float, default=1.5); ap.add_argument("--hit-tag", default="gaushit"); ap.add_argument("--sp-tag", default="cluster3d")
a = ap.parse_args()
import ROOT
ROOT.gSystem.Load("libgallery")
tag = lambda s: ROOT.art.InputTag(s)
def mk(f):
    v = ROOT.std.vector(ROOT.std.string)(); v.push_back(f); return ROOT.gallery.Event(v)
hkey = lambda e, h: (e, h.Channel(), int(h.StartTick()), int(h.EndTick()), round(h.PeakTime(), 1))
cache = pickle.load(open(a.cache, "rb"))
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/SpacePoint.h"')
ROOT.gInterpreter.Declare('#include "lardataobj/RecoBase/Hit.h"')
ROOT.gInterpreter.Declare('double spxyz(const recob::SpacePoint& s, int i) { return s.XYZ()[i]; }')
ROOT.gInterpreter.Declare('int widf(const recob::Hit& h, int i) { auto w = h.WireID(); return i == 0 ? (int)w.Cryostat : i == 1 ? (int)w.TPC : i == 2 ? (int)w.Plane : (int)w.Wire; }')
WIRES = {}; FIT = {}; PITCH = {}; CUTCM = 0.


def built3(ev, e, gidx):
    """set of codes (u*N+v)*N+w of the 3-hit points, and of the 2-hit point pairs (view-pair code, i*N+j)"""
    N = len(gidx[1]); hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
    asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
    sp_hits = collections.defaultdict(list)
    for p in asn: sp_hits[p.second.key()].append(p.first.key())
    S3 = set(); S2 = set(); views = gidx[1]
    for sp, hl in sp_hits.items():
        gi = [gidx[0].get(hkey(e, hits[k])) for k in hl]
        if None in gi: continue
        gi = sorted(gi, key=lambda i: views[i])
        if len(gi) == 3 and [views[i] for i in gi] == [0, 1, 2]: S3.add((gi[0] * N + gi[1]) * N + gi[2])
        elif len(gi) == 2 and views[gi[0]] != views[gi[1]]: S2.add((gi[0] * N + gi[1]) if views[gi[0]] == 0 else None)
    return S3, S2


def collect_wires(ev, nev, samp):
    for iev in range(nev):
        ev.goToEntry(iev); e = ev.eventAuxiliary().event()
        hits = ev.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.sp_tag)).product()
        sps = ev.getValidHandle[ROOT.vector[ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        asn = ev.getValidHandle[ROOT.art.Assns[ROOT.recob.Hit, ROOT.recob.SpacePoint]](tag(a.sp_tag)).product()
        wid = [tuple(ROOT.widf(h, i) for i in range(4)) for h in hits]
        for k, h in enumerate(hits): WIRES.setdefault(hkey(e, h), set()).add(wid[k])
        if samp is None: continue
        sp_hits = collections.defaultdict(list)
        for p in asn: sp_hits[p.second.key()].append(p.first.key())
        for sp, hl in sp_hits.items():
            if len(hl) != 3: continue
            p = sps[sp]; y, z = ROOT.spxyz(p, 1), ROOT.spxyz(p, 2)
            for k in hl: w = wid[k]; samp[w[:3]].append((y, z, w[3]))


def fit_lattice(samp):
    """wire index = alpha*y + beta*z + gamma per (cryostat, TPC, plane), robust (clip at 1 wire)"""
    for key, L in samp.items():
        M = np.array(L[:60000], dtype=float); X = np.c_[M[:, 0], M[:, 1], np.ones(len(M))]; wv = M[:, 2]; keep = np.ones(len(M), bool)
        for _ in range(6):
            coef = np.linalg.lstsq(X[keep], wv[keep], rcond=None)[0]; res = wv - X @ coef; keep = np.abs(res) < 1.0
        FIT[key] = coef; PITCH[key] = 1. / math.hypot(coef[0], coef[1])
        print(f"  lattice {key}: {len(M)} samples, kept {keep.mean():.3f}, rms residual {np.std(res[keep]):.3f} wires, pitch {PITCH[key]:.4f} cm", flush=True)


def geometry(e, ghits, hs, y0, z0):
    """-> None (no wire info) or (residuals in wires of the chosen wire copies, [third-wire distance in cm for the left-out plane 0,1,2])"""
    ws = [WIRES.get(hkey(e, ghits[i])) for i in hs]
    if any(not w for w in ws): return None
    tpcs = set.intersection(*[{(c, t) for c, t, pl, wi in w} for w in ws])
    best = None
    for ct in tpcs:
        sel = []; tot = 0.
        for pl, w in enumerate(ws):
            f = FIT.get((ct[0], ct[1], pl))
            if f is None: sel = None; break
            c = [(abs(f[0] * y0 + f[1] * z0 + f[2] - wi), wi) for cc, tt, pp, wi in w if (cc, tt) == ct and pp == pl]
            if not c: sel = None; break
            r, wi = min(c); sel.append((r, wi)); tot += r
        if sel is not None and (best is None or tot < best[0]): best = (tot, ct, sel)
    if best is None: return None
    _, ct, sel = best; F = [FIT[(ct[0], ct[1], pl)] for pl in range(3)]; ds = []
    for t in range(3):
        f_, s_ = [p for p in range(3) if p != t]
        Am = np.array([[F[f_][0], F[f_][1]], [F[s_][0], F[s_][1]]]); b = np.array([sel[f_][1] - F[f_][2], sel[s_][1] - F[s_][2]])
        if abs(np.linalg.det(Am)) < 1e-6: ds.append(99.); continue
        y, z = np.linalg.solve(Am, b); ds.append(abs(F[t][0] * y + F[t][1] * z + F[t][2] - sel[t][1]) * PITCH[(ct[0], ct[1], t)])
    return [x[0] for x in sel], ds


evX = [mk(os.path.join(x, "sp_art.root")) for x in a.also]; evA = mk(os.path.join(a.d, "sp_art.root")); evB = mk(os.path.join(a.other, "sp_art.root")) if a.other else None
stage = collections.Counter(); first_fail = collections.Counter(); pairfail = collections.Counter(); dts = {"VU": [], "WU": [], "WV": []}; dtsig = {"VU": [], "WU": [], "WV": []}
dumpf = open(a.dump_triples, 'w') if a.dump_triples else None
chi_all = []; also = collections.Counter(); gres = []; gd = [[], [], []]; gpass = collections.Counter()
if a.geom:
    NEV = min(a.events, evA.numberOfEventsInFile()); samp = collections.defaultdict(list)
    collect_wires(evA, NEV, samp)
    if evB is not None: collect_wires(evB, NEV, None)
    fit_lattice(samp); CUTCM = 0.5 * 1.9 * max(PITCH.values()); print(f"third-wire window = {CUTCM:.3f} cm", flush=True)
for iev in range(min(a.events, evA.numberOfEventsInFile())):
    evA.goToEntry(iev); e = evA.eventAuxiliary().event()
    ghits = evA.getValidHandle[ROOT.vector[ROOT.recob.Hit]](tag(a.hit_tag)).product()
    gidx = {}; views = []
    for i, h in enumerate(ghits): gidx[hkey(e, h)] = i; views.append(int(h.View()))
    N = len(views)
    tk = ("T3", e, a.f, a.delta, a.vox)
    if tk not in cache: print("no truth for event", e); continue
    codes = cache[tk][0]
    SA, _ = built3(evA, e, (gidx, views))
    SB = None
    if evB is not None:
        evB.goToEntry(iev); assert evB.eventAuxiliary().event() == e; SB, _ = built3(evB, e, (gidx, views))
    SX = []
    for ex in evX:
        ex.goToEntry(iev); SX.append(built3(ex, e, (gidx, views))[0])
    # hit properties, lazily
    P = {}
    def prop(i):
        r = P.get(i)
        if r is None:
            h = ghits[i]; ndf = h.DegreesOfFreedom(); s = h.RMS() * (1.5 if ndf < 2 else 1.)
            r = P[i] = (h.PeakTime(), s, ndf, h.PeakAmplitude(), int(h.StartTick()), int(h.EndTick()), h.RMS())
        return r
    snip = collections.defaultdict(list)                     # (view, start, end) -> hit indices (only for hits we need)
    need = set()
    for c in codes:
        c = int(c); need.update((c // (N * N), (c // N) % N, c % N))
    for i in range(N):
        snip[(views[i], int(ghits[i].StartTick()), int(ghits[i].EndTick()), ghits[i].Channel() if a.roi else 0)].append(i)
    maxamp = {k: max(ghits[i].PeakAmplitude() for i in v) for k, v in snip.items() if any(i in need for i in v)}
    def skipped(i):
        p = prop(i); k = (views[i], p[4], p[5], ghits[i].Channel() if a.roi else 0)
        return p[2] > 1 and p[3] < a.phf * maxamp[k] and p[3] < a.phl
    ntr = 0; ntr_idx = {int(c): j for j, c in enumerate(codes)}
    for c in codes:
        c = int(c); iu, iv, iw = c // (N * N), (c // N) % N, c % N
        if any(prop(i)[2] <= a.long_dof for i in (iu, iv, iw)): continue                 # normal triples only
        ntr += 1; hs = (iu, iv, iw); pr = [prop(i) for i in hs]
        if dumpf: dumpf.write(f"{e} {ntr_idx[c]} " + " ".join(f"{ghits[i].Channel()} {int(ghits[i].StartTick())} {int(ghits[i].EndTick())} {int(round(ghits[i].PeakTime() * 10))}" for i in hs) + "\n")
        # signed time differences of the truth triple (peak time, ticks)
        for nm, (x, y) in (("VU", (1, 0)), ("WU", (2, 0)), ("WV", (2, 1))):
            d = pr[x][0] - pr[y][0]; dts[nm].append(d); dtsig[nm].append(d / math.hypot(pr[x][1], pr[y][1]))
        # A snippet overlap with the earliest-start window
        order = sorted(range(3), key=lambda j: pr[j][4]); s0, e0 = pr[order[0]][4], pr[order[0]][5]
        A = all(pr[j][5] >= s0 and pr[j][4] < e0 for j in order[1:])
        D = not any(skipped(i) for i in hs)
        # B pair time cuts
        okp = {}
        for nm, (x, y) in (("UV", (0, 1)), ("UW", (0, 2)), ("VW", (1, 2))):
            okp[nm] = abs(pr[x][0] - pr[y][0]) < a.dpts * math.hypot(pr[x][1], pr[y][1]) and abs(pr[x][0] - pr[y][0]) <= 6. * (pr[x][1] + pr[y][1])
        B = all(okp.values())
        # C triplet chi-square
        w = [1. / (p[1] * p[1]) for p in pr]; sw = sum(w); ave = sum(p[0] * wi for p, wi in zip(pr, w)) / sw; sm2 = 1. / sw
        chi = sum(((p[0] - ave) ** 2) / max(p[1] ** 2 - sm2, 1e-9) for p in pr); chi_all.append(chi)
        C = chi < a.chi2
        # E overlap of the +-3 sigma windows and peak separation vs overlap range (makeHitTriplet)
        lo, hi = [], []
        for p in pr:
            rg = 3. * p[6] * (1.5 if p[2] < 2 else 1.); lo.append(int(p[0] - rg - 0.5)); hi.append(int(p[0] + rg + 0.5) + 1)
        ovr = min(hi) - max(lo); mdp = max(abs(pr[0][0] - pr[1][0]), abs(pr[1][0] - pr[2][0]), abs(pr[0][0] - pr[2][0]))
        E = ovr > 0 and mdp <= 3. * ovr
        if E: stage["passE"] += 1
        built = c in SA
        g = None
        if a.geom:
            pos = cache[tk][2]; g = geometry(e, ghits, hs, pos[3 * ntr_idx[c] + 1], pos[3 * ntr_idx[c] + 2])
            if g is not None:
                gres.extend(g[0]); [gd[t].append(g[1][t]) for t in range(3)]
                gpass["has_wires"] += 1; gany = any(d < CUTCM for d in g[1])
                for t in range(3):
                    if g[1][t] < CUTCM: gpass[f"third={'UVW'[t]}"] += 1
                if gany: gpass["any"] += 1
                if built: gpass["built"] += 1; gpass["built_any"] += int(gany)
        row = "built 3-hit" if built else "not built"
        stage["T"] += 1
        if built: stage["built3"] += 1
        for nm, ok in (("A", A), ("D", D), ("B", B), ("C", C)):
            if ok: stage["pass" + nm] += 1
        allok = A and D and B and C and E
        if allok: stage["passAll"] += 1
        if not built:
            if not A: first_fail["A snippet windows do not overlap"] += 1
            elif not D: first_fail["D pulse-height filter"] += 1
            elif not B:
                first_fail["B pair time cut"] += 1
                for nm, ok in okp.items():
                    if not ok: pairfail[nm] += 1
            elif not C: first_fail["C triplet chi-square"] += 1
            elif not E: first_fail["E window overlap / peak separation"] += 1
            else:
                for k, sx in enumerate(SX):
                    if c in sx: also[a.also[k]] += 1
                if any(c in sx for sx in SX): stage["bucket_any_also"] += 1
                if a.geom:
                    ok2 = None if g is None else [g[1][t] < CUTCM for t in (order[1], order[2])]    # the two possible left-out planes (the builder takes one, set by the pair counts)
                    by = "made by the other builder (selection)" if (SB is not None and c in SB) else "not built by either (other)"
                    if g is None: first_fail["passes A-D: no wire info"] += 1
                    elif not any(ok2): first_fail["passes A-D, G: third-wire window fails for both possible left-out planes"] += 1
                    elif not all(ok2): first_fail["passes A-D, G: window passes for only one left-out plane; " + by] += 1
                    else: first_fail["passes A-D and G (both left-out planes): " + by] += 1
                elif SB is not None and c in SB: first_fail["passes A-D: made by the other builder (selection)"] += 1
                else: first_fail["passes A-D: not built by either (geometry or other)"] += 1
        else:
            if not allok: first_fail["(built although a re-evaluated cut fails: approximation)"] += 1
    print(f"event {e}: {ntr} normal truth triples", flush=True)
T = max(1, stage["T"])
print(f"\nnormal truth triples: {stage['T']}  (f {a.f}, delta {a.delta} cm); built as 3-hit point by {os.path.basename(a.d.rstrip('/'))}: {stage['built3']} ({100 * stage['built3'] / T:.1f}%)")
print("pass each hit-level cut on its own: " + ", ".join(f"{k} {100 * stage['pass' + k] / T:.1f}%" for k in "ADBCE") + f";  all four: {100 * stage['passAll'] / T:.1f}%")
print("\nnot built, first failing criterion (order A, D, B, C, E, then the unseen rest):")
for k, v in sorted(first_fail.items(), key=lambda kv: -kv[1]): print(f"  {k:<62}{v:8d}  {100 * v / T:5.1f}%")
if a.also:
    print("\nof the triples that pass A-D and are not built by the baseline, made as 3-hit points by:")
    for x in a.also: print(f"  {os.path.basename(x.rstrip('/')):<14}{also[x]:8d}")
    print(f"  union of these:{stage['bucket_any_also']:8d}")
if a.geom:
    nh = max(1, gpass["has_wires"]); r = np.abs(np.array(gres))
    print(f"\ngeometry stage: {gpass['has_wires']} of {stage['T']} truth triples have wire info; third-wire window {CUTCM:.3f} cm")
    print(f"  lattice check: |lattice coordinate of the truth deposit - wire| of the chosen wire copies: median {np.median(r):.2f}, 90% {np.quantile(r, .9):.2f}, 99% {np.quantile(r, .99):.2f} wires (uniform +-0.5 would give 0.25 / 0.45 / 0.5)")
    print(f"  third-wire distance of the pair intersection, for the left-out plane U / V / W, median and 90% (cm): " + "; ".join(f"{np.median(v):.2f} / {np.quantile(v, .9):.2f}" for v in gd))
    print(f"  truth triples inside the window: left-out U {100 * gpass['third=U'] / nh:.1f}%, V {100 * gpass['third=V'] / nh:.1f}%, W {100 * gpass['third=W'] / nh:.1f}%, any pair choice {100 * gpass['any'] / nh:.1f}%")
    print(f"  sanity: built baseline triples inside the window for some pair choice: {100 * gpass['built_any'] / max(1, gpass['built']):.1f}% (should be ~100%)")
print("pair cut failures (B), which pair: " + ", ".join(f"{k} {v}" for k, v in pairfail.items()))
print("\nsigned peak-time differences of the truth triples (ticks; and in units of sqrt(s1^2+s2^2)):  median, 16%, 84%")
for nm in dts:
    v = np.array(dts[nm]); s = np.array(dtsig[nm]); q = np.quantile(v, [.5, .16, .84]); qs = np.quantile(s, [.5, .16, .84])
    print(f"  {nm}: {q[0]:+.2f} ({q[1]:+.2f}, {q[2]:+.2f}) ticks;  {qs[0]:+.2f} ({qs[1]:+.2f}, {qs[2]:+.2f}) sigma")
ch = np.array(chi_all); print(f"\ntruth-triple chi-square (formula of makeHitTriplet): median {np.median(ch):.2f}, 90% {np.quantile(ch, .9):.2f}, 99% {np.quantile(ch, .99):.2f}, fraction >= {a.chi2:g}: {100 * (ch >= a.chi2).mean():.1f}%")
