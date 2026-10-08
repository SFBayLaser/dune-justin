# Gaussian core fits to (p_reco - p_true)/p_true for muons that start in the
# ND-LAr fiducial volume and stop in the TMS, each muon's most complete track
# (the validation suite's MomentumResolution selection), legacy and Cluster3D,
# overall and per true-momentum bin. Iterative: fit within mean +- 1.5 sigma,
# re-centre, repeat.
import ROOT, sys, json, math
ROOT.gROOT.SetBatch(True)
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
PBINS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]
def collect(rt, tt):
    vals = []
    for fn in files:
        f = ROOT.TFile.Open(fn); r = f.Get(rt); t = f.Get(tt)
        for e in range(r.GetEntries()):
            r.GetEntry(e); t.GetEntry(e)
            best = {}
            for it in range(r.nTracks):
                if abs(t.RecoTrackPrimaryParticlePDG[it]) != 13 or not t.RecoTrackPrimaryParticleLArFiducialStart[it]: continue
                ip = t.RecoTrackPrimaryParticleIndex[it]
                if ip < 0: continue
                if ip not in best or t.RecoTrackPrimaryParticleTrueVisibleEnergy[it] > t.RecoTrackPrimaryParticleTrueVisibleEnergy[best[ip]]: best[ip] = it
            for ip, it in best.items():
                if not t.RecoTrackPrimaryParticleTMSFiducialEnd[it]: continue
                m = t.RecoTrackPrimaryParticleTrueMomentumEnteringTMS
                pt = math.sqrt(sum(m[it * 4 + d] ** 2 for d in range(3)))
                pr = r.Momentum[it]
                if pt > 0 and pr > 0 and math.isfinite(pr): vals.append((pt / 1000.0, (pr - pt) / pt))
        f.Close()
    return vals
def fit(vals, name):
    h = ROOT.TH1D(name, "", 400, -1.0, 1.0)
    for _, v in vals: h.Fill(v)
    s = sorted(v for _, v in vals)
    if len(s) < 20: return None, h
    mean, sigma = s[len(s) // 2], 0.5 * (s[int(0.84 * len(s))] - s[int(0.16 * len(s))])
    fn = ROOT.TF1(name + "_g", "gaus", -1, 1)
    for _ in range(6):
        fn.SetParameters(h.GetMaximum(), mean, max(sigma, 0.01))
        h.Fit(fn, "QN0", "", mean - 1.5 * sigma, mean + 1.5 * sigma)
        mean, sigma = fn.GetParameter(1), abs(fn.GetParameter(2))
    lo, hi = mean - 1.5 * sigma, mean + 1.5 * sigma
    core = sum(1 for v in s if lo <= v <= hi) / len(s)
    return dict(n=len(s), mean=mean, mean_err=fn.GetParError(1), sigma=sigma, sigma_err=fn.GetParError(2),
                amp=fn.GetParameter(0), chi2=fn.GetChisquare(), ndf=fn.GetNDF(), core_frac=core,
                below_3sigma=sum(1 for v in s if v < mean - 3 * sigma) / len(s)), h
def clipped(vals, k=2.0):
    # Unbinned Gaussian core estimate for small samples: iterate mean and RMS
    # within +-k sigma, correcting the RMS for the truncation (for k = 2 a
    # Gaussian's truncated RMS is 0.8796 sigma).
    s = sorted(v for _, v in vals)
    if len(s) < 15: return None
    mean, sigma = s[len(s) // 2], 0.5 * (s[int(0.84 * len(s))] - s[int(0.16 * len(s))])
    phi = math.exp(-0.5 * k * k) / math.sqrt(2 * math.pi)
    inside = math.erf(k / math.sqrt(2))
    shrink = math.sqrt(1 - 2 * k * phi / inside)
    for _ in range(50):
        core = [v for v in s if abs(v - mean) <= k * sigma]
        if len(core) < 5: return None
        m = sum(core) / len(core)
        rms = math.sqrt(sum((v - m) ** 2 for v in core) / len(core))
        new_sigma = rms / shrink
        if abs(m - mean) < 1e-6 and abs(new_sigma - sigma) < 1e-6: break
        mean, sigma = m, new_sigma
    n_core = len(core)
    return dict(n=len(s), mean=mean, mean_err=sigma / math.sqrt(n_core), sigma=sigma,
                sigma_err=sigma / math.sqrt(2 * n_core), core_frac=n_core / len(s),
                below_3sigma=sum(1 for v in s if v < mean - 3 * sigma) / len(s))
out = {}
for tag, rt, tt in [("legacy", "Reco_Tree", "Truth_Info"), ("linked", "Reco_Tree_C3D", "Truth_Info_C3D")]:
    vals = collect(rt, tt)
    res, h = fit(vals, tag)
    # Histogram for drawing: 0.01 bins over -0.5..0.5 (the fit used 0.005 bins over -1..1).
    hd = ROOT.TH1D(tag + "_d", "", 100, -0.5, 0.5)
    for _, v in vals: hd.Fill(v)
    res["hist"] = dict(edges=[hd.GetXaxis().GetBinLowEdge(i) for i in range(1, 102)],
                       counts=[hd.GetBinContent(i) for i in range(1, 101)], under=hd.GetBinContent(0), over=hd.GetBinContent(101),
                       width_ratio=h.GetBinWidth(1) / hd.GetBinWidth(1))
    bins = []
    for lo, hi in zip(PBINS[:-1], PBINS[1:]):
        r_ = clipped([x for x in vals if lo <= x[0] < hi])
        bins.append(dict(lo=lo, hi=hi, **(r_ or dict(n=sum(1 for x in vals if lo <= x[0] < hi)))))
    res["pbins"] = bins
    res["clipped"] = clipped(vals)
    out[tag] = res
    print(f"{tag}: n={res['n']} mean {100*res['mean']:+.2f} +- {100*res['mean_err']:.2f}%  sigma {100*res['sigma']:.2f} +- {100*res['sigma_err']:.2f}%  "
          f"chi2/ndf {res['chi2']:.1f}/{res['ndf']}  within +-1.5 sigma {100*res['core_frac']:.0f}%  below -3 sigma {100*res['below_3sigma']:.1f}%")
    c = res["clipped"]
    print(f"   unbinned 2-sigma-clipped: mean {100*c['mean']:+.2f} +- {100*c['mean_err']:.2f}%  sigma {100*c['sigma']:.2f} +- {100*c['sigma_err']:.2f}%  core {100*c['core_frac']:.0f}%  below -3 sigma {100*c['below_3sigma']:.1f}%")
    for b in bins:
        if "sigma" in b: print(f"    p {b['lo']:.2f}-{b['hi']:.2f}: n={b['n']:4d} mean {100*b['mean']:+5.1f} +- {100*b['mean_err']:.1f}%  sigma {100*b['sigma']:4.1f} +- {100*b['sigma_err']:.1f}%  below -3 sigma {100*b['below_3sigma']:4.1f}%")
json.dump(out, open(sys.argv[2], "w"))
