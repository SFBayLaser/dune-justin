# Requirements scorecard numbers from converted files (legacy and Cluster3D trees), organized by the TMS
# capability requirements of the ND PDR (DocDB 25546, Table 1.1), in muon KINETIC energy T throughout.
# (The thesis-era version is scorecard_thesis_v2.py.)
#
# Population: true muons (|PDG| 13) born in the ND-LAr fiducial volume, forward-going (pz > 0).
# Each muon is credited with the reconstructed track (in its spill) whose largest true energy
# contributor it is, keeping the purest such track; "found" additionally requires that the muon
# contributes at least half of that track's true visible energy (the suite credits any plurality).
#
#   C161 coverage (ND-C1.6.1): fraction entering the TMS, stopping in it, and found, vs T at the vertex and angle.
#   C162 energy (ND-C1.6.2): stopping muons' kinetic energy, reco (from the track's Momentum) vs true entering the TMS,
#        per bin: median, 68% half-width, fraction within +-5%, and an iterative Gaussian core fit (mean +- 1.5 sigma).
#   C164 front face (ND-C1.6.4): reco start extrapolated to the true TMS-entry z vs the true entry point; angle residuals.
#   C165 stopping power (ND-C1.6.5): of muons entering the TMS from vertices in the upstream 1 m of the ND-LAr
#        fiducial volume, going within 20 degrees of the beam, the fraction that stop inside and the fraction that
#        leave through the back (true PositionTMSEnd within 50 mm of the last plane), vs T at the vertex.
#   C166 stop or exit (ND-C1.6.6): found muons entering the TMS, reco "stops inside" (fitted end >= 100 mm inside the
#        bar region's x/y faces and before its back face, the reconstruction's own rule) against truth.
#   C17  charge (ND-C1.7): charge mis-ID per true sign (mu- / mu+) vs T entering the TMS.
#   C13  separation of interactions / rate (ND-C1.3, ND-M7): found fraction vs the spill's total visible energy in the TMS.
#
# (PyROOT exposes the [n][4] / [n][3] array branches flattened.)
# Usage: python3 scorecard.py <files.txt> <out.json>
import ROOT, sys, json, math, collections
ROOT.gROOT.SetBatch(True)
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
MMU = 0.1056584  # GeV
# The bar region (mm) as the reconstruction's containment rule sees it, and its 100 mm margins
# (TMS_Event.cpp stopsInside; RangeContainmentMarginXY/Z).
XLO, XHI, YLO, YHI, ZHI, MARGIN = -3501.0, 3501.0, -3102.0, 398.0, 18510.0, 100.0
LAR_Z_LO = 4179.24  # upstream face of the ND-LAr fiducial box used by the validation suite (mm)

def ke(p):  # GeV/c -> kinetic energy, GeV
    return math.sqrt(p * p + MMU * MMU) - MMU

def gaus_core(vals, name):
    """Iterative Gaussian fit within mean +- 1.5 sigma (as range_gaus_fit.py). Returns (mean, sigma, sigma_err) or None."""
    s = sorted(vals)
    if len(s) < 30: return None
    h = ROOT.TH1D(name, "", 400, -1.0, 1.0)
    for v in s: h.Fill(v)
    mean, sigma = s[len(s) // 2], 0.5 * (s[int(0.84 * len(s))] - s[int(0.16 * len(s))])
    fn = ROOT.TF1(name + "_g", "gaus", -1, 1)
    for _ in range(6):
        fn.SetParameters(h.GetMaximum(), mean, max(sigma, 0.01))
        h.Fit(fn, "QN0", "", mean - 1.5 * sigma, mean + 1.5 * sigma)
        mean, sigma = fn.GetParameter(1), abs(fn.GetParameter(2))
    return mean, sigma, fn.GetParError(2)

out = {}
for tracker, rt_name, ti_name in [("legacy", "Reco_Tree", "Truth_Info"), ("cluster3d", "Reco_Tree_C3D", "Truth_Info_C3D")]:
    muons = []  # one dict per true muon
    for fn in files:
        f = ROOT.TFile.Open(fn)
        ts, rt, ti = f.Get("Truth_Spill"), f.Get(rt_name), f.Get(ti_name)
        best = {}
        for e in range(rt.GetEntries()):
            rt.GetEntry(e); ti.GetEntry(e)
            for it in range(min(rt.nTracks, 20)):
                ip = ti.RecoTrackPrimaryParticleIndex[it]
                if ip < 0 or abs(ti.RecoTrackPrimaryParticlePDG[it]) != 13: continue
                tot = ti.RecoTrackTrueVisibleEnergy[it]
                pur = ti.RecoTrackPrimaryParticleTrueVisibleEnergy[it] / tot if tot > 0 else 0.0
                k = (rt.SpillNo, ip)
                if k in best and best[k]["purity"] >= pur: continue
                ent = [ti.RecoTrackPrimaryParticleTruePositionEnteringTMS[4 * it + j] for j in range(3)]
                pent = [ti.RecoTrackPrimaryParticleTrueMomentumEnteringTMS[4 * it + j] for j in range(4)]
                end = [rt.EndPos[4 * it + j] for j in range(3)]
                best[k] = dict(purity=pur, charge=rt.Charge[it], p_reco=rt.Momentum[it],
                               start=[rt.StartPos[4 * it + j] for j in range(3)], sdir=[rt.StartDirection[3 * it + j] for j in range(3)],
                               ent=ent, pent=pent,
                               reco_stops=(XLO + MARGIN < end[0] < XHI - MARGIN and YLO + MARGIN < end[1] < YHI - MARGIN and end[2] < ZHI - MARGIN))
        for e in range(ts.GetEntries()):
            ts.GetEntry(e)
            spill_vis = 0.0
            cand = []
            for ip in range(ts.nTrueParticles):
                if ts.TMSFiducialTouch[ip]: spill_vis += ts.TrueVisibleEnergy[ip]
                if abs(ts.PDG[ip]) != 13 or not ts.LArFiducialStart[ip]: continue
                b = [ts.BirthMomentum[4 * ip + j] for j in range(4)]
                if b[2] <= 0: continue
                cand.append((ip, b, ts.BirthPosition[4 * ip + 2], ts.PositionTMSEnd[4 * ip + 2]))
            for ip, b, vz, zend in cand:
                p = math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2) / 1000.0
                theta = math.degrees(math.atan2(math.hypot(b[0], b[1]), b[2]))
                c = best.get((ts.SpillNo, ip))
                muons.append(dict(T=ke(p), p=p, theta=theta, vz=vz, zend=zend, pdg=ts.PDG[ip], enters=bool(ts.TMSFiducialTouch[ip]),
                                  stops=bool(ts.TMSFiducialEnd[ip]) and bool(ts.TMSFiducialTouch[ip]),
                                  spill_vis=spill_vis, credit=c))
        f.Close()
    print(tracker, len(muons), "forward ND-LAr fiducial muons", file=sys.stderr)

    def found(m): return m["credit"] is not None and m["credit"]["purity"] >= 0.5
    def t_enter(m):
        pe = m["credit"]["pent"]; return ke(math.sqrt(pe[0] ** 2 + pe[1] ** 2 + pe[2] ** 2) / 1000.0)
    R = {}
    # ND-C1.6.1 coverage vs T at the vertex
    tb = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0]
    rows = []
    for lo, hi in zip(tb[:-1], tb[1:]):
        sel = [m for m in muons if lo <= m["T"] < hi]
        ent = [m for m in sel if m["enters"]]
        stp = [m for m in ent if m["stops"]]
        rows.append(dict(lo=lo, hi=hi, n=len(sel), enters=len(ent), stops=len(stp),
                         found_enter=sum(found(m) for m in ent), found_stop=sum(found(m) for m in stp)))
    R["C161_T"] = rows
    rows = []
    for lo, hi in zip([0, 10, 20, 30, 40], [10, 20, 30, 40, 90]):
        sel = [m for m in muons if m["T"] >= 1.0 and lo <= m["theta"] < hi]
        ent = [m for m in sel if m["enters"]]
        stp = [m for m in ent if m["stops"]]
        rows.append(dict(lo=lo, hi=hi, n=len(sel), enters=len(ent), stops=len(stp),
                         found_enter=sum(found(m) for m in ent), found_stop=sum(found(m) for m in stp)))
    R["C161_theta"] = rows
    # ND-C1.6.2 kinetic-energy resolution, stopping muons, vs T entering the TMS
    kb = [0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
    rows, allres = [], []
    for lo, hi in zip(kb[:-1], kb[1:]):
        res = []
        for m in muons:
            if not (m["stops"] and found(m)) or m["credit"]["p_reco"] <= 0: continue
            tt = t_enter(m)
            if not (lo <= tt < hi) or tt <= 0: continue
            res.append((ke(m["credit"]["p_reco"] / 1000.0) - tt) / tt)
        allres += res
        if len(res) < 10:
            rows.append(dict(lo=lo, hi=hi, n=len(res))); continue
        g = gaus_core(res, f"{tracker}_k{lo}")
        res.sort(); q = lambda f: res[int(f * (len(res) - 1))]
        row = dict(lo=lo, hi=hi, n=len(res), median=q(0.5), hw68=(q(0.84) - q(0.16)) / 2, within5=sum(abs(r) < 0.05 for r in res) / len(res))
        if g: row.update(core_mean=g[0], core_sigma=g[1], core_sigma_err=g[2])
        rows.append(row)
    g = gaus_core(allres, f"{tracker}_kall")
    allres.sort(); q = lambda f: allres[int(f * (len(allres) - 1))]
    R["C162_bins"] = rows
    R["C162_all"] = dict(n=len(allres), median=q(0.5), hw68=(q(0.84) - q(0.16)) / 2, within5=sum(abs(r) < 0.05 for r in allres) / len(allres),
                         core_mean=g[0], core_sigma=g[1], core_sigma_err=g[2])
    # ND-C1.7 charge mis-ID per true sign vs T entering the TMS
    rows = []
    for lo, hi in zip([0.0, 0.5, 1.0, 2.0, 3.0], [0.5, 1.0, 2.0, 3.0, 10.0]):
        row = dict(lo=lo, hi=hi)
        for sign, pdg in [("mu-", 13), ("mu+", -13)]:
            for cont, sel in [("stop", True), ("exit", False)]:
                n = w = 0
                for m in muons:
                    if m["pdg"] != pdg or not m["enters"] or m["stops"] != sel or not found(m): continue
                    if not (lo <= t_enter(m) < hi): continue
                    n += 1
                    if (1 if pdg > 0 else -1) * m["credit"]["charge"] <= 0: w += 1
                row[f"{sign}_{cont}_n"] = n; row[f"{sign}_{cont}_wrong"] = w
        rows.append(row)
    R["C17"] = rows
    # ND-C1.6.4 front face
    dx, dy, dax, day = [], [], [], []
    for m in muons:
        if not (m["enters"] and found(m)): continue
        c = m["credit"]; ent = c["ent"]; pe = c["pent"]
        if pe[2] <= 0 or c["sdir"][2] <= 0: continue
        s = c["start"]; d = c["sdir"]
        t = (ent[2] - s[2]) / d[2]
        if abs(ent[2] - s[2]) > 500: continue  # reco track must start near the TMS front
        dx.append(s[0] + t * d[0] - ent[0]); dy.append(s[1] + t * d[1] - ent[1])
        dax.append(math.degrees(math.atan(d[0] / d[2]) - math.atan(pe[0] / pe[2])))
        day.append(math.degrees(math.atan(d[1] / d[2]) - math.atan(pe[1] / pe[2])))
    def w68(v):
        v = sorted(v); return dict(n=len(v), median=v[len(v) // 2], hw68=(v[int(.84 * (len(v) - 1))] - v[int(.16 * (len(v) - 1))]) / 2) if v else None
    R["C164"] = dict(dx_mm=w68(dx), dy_mm=w68(dy), dthx_deg=w68(dax), dthy_deg=w68(day))
    # ND-C1.6.5 stopping power: upstream-edge vertices, within 20 degrees
    rows = []
    for lo, hi in zip([2.5, 3.0, 3.5, 4.0, 4.5, 5.0], [3.0, 3.5, 4.0, 4.5, 5.0, 6.0]):
        sel = [m for m in muons if m["enters"] and m["vz"] < LAR_Z_LO + 1000.0 and m["theta"] < 20 and lo <= m["T"] < hi]
        back = [m for m in sel if not m["stops"] and m["zend"] > ZHI - 50.0]
        rows.append(dict(lo=lo, hi=hi, enters=len(sel), stops=sum(m["stops"] for m in sel), exit_back=len(back)))
    R["C165"] = rows
    # ND-C1.6.6 stop or exit, found muons entering the TMS
    cm = collections.Counter()
    for m in muons:
        if m["enters"] and found(m): cm[(m["stops"], m["credit"]["reco_stops"])] += 1
    R["C166"] = {f"true_{'stop' if a else 'exit'}_reco_{'stop' if b else 'exit'}": v for (a, b), v in cm.items()}
    # ND-C1.3 / ND-M7: found fraction (entering, T > 1 GeV) vs spill TMS activity quartile
    sel = [m for m in muons if m["enters"] and m["T"] >= 1.0]
    vis = sorted(m["spill_vis"] for m in sel)
    edges = [vis[int(f * (len(vis) - 1))] for f in (0, .25, .5, .75, 1.0)]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = [m for m in sel if lo <= m["spill_vis"] <= hi]
        rows.append(dict(lo=lo, hi=hi, n=len(s), found=sum(found(m) for m in s)))
    R["C13"] = rows
    out[tracker] = R
json.dump(out, open(sys.argv[2], "w"), indent=1)
