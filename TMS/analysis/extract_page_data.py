# Pull the numbers the comparison page draws, for any number of validation
# outputs. Usage: extract_page_data.py <out.json> tag=<validation.root>:<dz.npy> ...
import ROOT, json, sys, math
import numpy as np

EFF = ["reco_eff__muon_ke_tms_enter", "reco_eff__good_reco_muon_ke_tms_enter", "reco_eff__all_muon_ke_tms_enter",
       "charge_id__all_true_muon", "charge_id__true_muon", "reco_eff__tms_vertex_muon_ke_tms_enter"]


def eff(f, base):
    n = f.Get(base + "_numerator"); d = f.Get(base + "_denominator")
    bins = []
    for i in range(1, d.GetNbinsX() + 1):
        N, D = n.GetBinContent(i), d.GetBinContent(i)
        lo = hi = 0.0
        if D > 0:
            lo = ROOT.TEfficiency.ClopperPearson(int(D), int(N), 0.683, False)
            hi = ROOT.TEfficiency.ClopperPearson(int(D), int(N), 0.683, True)
        bins.append(dict(lo=d.GetXaxis().GetBinLowEdge(i), hi=d.GetXaxis().GetBinUpEdge(i), n=N, d=D,
                         e=(N / D if D > 0 else None), elo=lo, ehi=hi))
    return dict(bins=bins, n=n.Integral(), d=d.Integral())


def hist1d(h):
    if not h: return None
    return dict(edges=[h.GetXaxis().GetBinLowEdge(i) for i in range(1, h.GetNbinsX() + 2)],
                counts=[h.GetBinContent(i) for i in range(1, h.GetNbinsX() + 1)],
                under=h.GetBinContent(0), over=h.GetBinContent(h.GetNbinsX() + 1),
                n=h.GetEntries(), mean=h.GetMean(), rms=h.GetRMS())


def median_from(h):
    tot = sum(h["counts"]) + h["under"] + h["over"]
    if tot <= 0: return None
    acc = h["under"]
    for i, c in enumerate(h["counts"]):
        if acc + c >= tot / 2:
            frac = (tot / 2 - acc) / c if c > 0 else 0
            return h["edges"][i] + frac * (h["edges"][i + 1] - h["edges"][i])
        acc += c
    return h["edges"][-1]


def profile(h2):
    # Per true-momentum bin: median and 16-84% half-width of (fit-true)/true.
    out = []
    ny = h2.GetNbinsY()
    ye = [h2.GetYaxis().GetBinLowEdge(j) for j in range(1, ny + 2)]
    for i in range(1, h2.GetNbinsX() + 1):
        col = [h2.GetBinContent(i, j) for j in range(0, ny + 2)]  # incl. under/overflow
        tot = sum(col)
        entry = dict(lo=h2.GetXaxis().GetBinLowEdge(i), hi=h2.GetXaxis().GetBinUpEdge(i), n=tot)
        if tot >= 5:
            def q(frac):
                acc = col[0]
                if acc >= frac * tot: return ye[0]
                for j in range(1, ny + 1):
                    c = col[j]
                    if acc + c >= frac * tot:
                        return ye[j - 1] + ((frac * tot - acc) / c if c > 0 else 0) * (ye[j] - ye[j - 1])
                    acc += c
                return ye[-1]
            entry.update(median=q(0.5), q16=q(0.16), q84=q(0.84))
        out.append(entry)
    return out


out = {}
for arg in sys.argv[2:]:
    tag, rest = arg.split("=", 1)
    root, dz = rest.split(":")
    f = ROOT.TFile.Open(root)
    d = {k: eff(f, k) for k in EFF if f.Get(k + "_denominator")}
    m = f.Get("reco_eff__multi_reco__probability_multi_reco_numerator")
    md = f.Get("reco_eff__multi_reco__probability_multi_reco_denominator")
    d["multi_reco"] = dict(n=m.Integral(), d=md.Integral())
    # ND-LAr-restricted duplicate rates (validation suite, 2026-10-01); absent in older outputs.
    for sub in ("lar_fiducial", "nd_physics"):
        mn = f.Get(f"reco_eff__multi_reco__probability_multi_reco_{sub}_numerator")
        mdn = f.Get(f"reco_eff__multi_reco__probability_multi_reco_{sub}_denominator")
        if mn and mdn:
            d[f"multi_reco_{sub}"] = dict(n=mn.Integral(), d=mdn.Integral())
    d["eres"] = hist1d(f.Get("energy_resolution__resolution__all_muon_starting_ke_fractional_resolution_nostack_optsmooth_1_contained"))
    for s in ["contained", "exiting"]:
        h = hist1d(f.Get(f"momentum__resolution__{s}"))
        if h: h["median"] = median_from(h)
        d[f"pres_{s}"] = h
        h2 = f.Get(f"momentum__resolution__{s}_vs_p")
        d[f"pres_{s}_vs_p"] = profile(h2) if h2 else None
        c = hist1d(f.Get(f"momentum__completeness__{s}"))
        if c: c["median"] = median_from(c)
        d[f"compl_{s}"] = c
    p = hist1d(f.Get("reco_track__cleanliness_energy"))
    if p: p["median"] = median_from(p)
    d["purity"] = p
    a = np.load(dz)
    h, e = np.histogram(np.clip(a[:, 0], -99.9, 49.9), bins=np.arange(-100, 55, 5))
    d["dz"] = dict(edges=e.tolist(), counts=h.tolist(), n=len(a),
                   short=int((a[:, 0] <= -30).sum()), ok=int(((a[:, 0] > -30) & (a[:, 0] < 0)).sum()),
                   over=int((a[:, 0] >= 0).sum()), frag=int(((a[:, 0] <= -30) & (a[:, 7] > 1)).sum()),
                   frag_fixable=int(((a[:, 0] <= -30) & (a[:, 8] > -30) & (a[:, 8] < 0)).sum()),
                   median=float(np.median(a[:, 0])))
    out[tag] = d
    print(tag, "found", round(d["reco_eff__muon_ke_tms_enter"]["n"]), "/", round(d["reco_eff__muon_ke_tms_enter"]["d"]),
          "good", round(d["reco_eff__good_reco_muon_ke_tms_enter"]["n"]), "multi", round(d["multi_reco"]["n"]), "/", round(d["multi_reco"]["d"]),
          "short", d["dz"]["short"], "/", d["dz"]["n"],
          "pres_contained median", d["pres_contained"] and round(d["pres_contained"]["median"], 3),
          "compl_contained median", d["compl_contained"] and round(d["compl_contained"]["median"], 3),
          "purity median", d["purity"] and round(d["purity"]["median"], 3))
json.dump(out, open(sys.argv[1], "w"))
