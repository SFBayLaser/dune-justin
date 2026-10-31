#!/usr/bin/env python3
"""Summary of single-muon tuples made by TMS/muon_tuple.py (stage 2 of tms_muon_baseline_config.json).

usage: muon_tuple_summary.py [--label TEXT] [--p-bins 500,1000,2000,3500,6000] [--region-x 1860] FILE_OR_GLOB...

Reads the "events" tree of every file (uproot if installed, otherwise PyROOT), joins them, and prints for mu- and mu+
separately and for all muons together: tracking efficiency, charge-sign correctness, momentum resolution of the
Kalman curvature fit and of the range estimate for muons that stop and muons that exit, and how well the reco
containment flag tags exiting muons.

Definitions (see muon_tuple.py): "reconstructible" = more than 1 m of true TMS path; "exits" = the true muon goes on
more than 300 mm past its last TMS hit; resolutions are (reco - truth) / truth with the true momentum entering the TMS.
The reco momentum is the curvature fit only if the reco ran with MomentumFromRange = false (tms_muon_reco_tuple.jobscript
does that).
"""
import argparse
import glob
import sys

import numpy as np


def read_events(path):
    try:
        import uproot
        with uproot.open(path) as f:
            return {k: np.asarray(v) for k, v in f["events"].arrays(library="np").items()}
    except ImportError:
        import ROOT
        f = ROOT.TFile.Open(path)
        t = f.Get("events")
        names = [b.GetName() for b in t.GetListOfBranches()]
        cols = {n: [] for n in names}
        for e in t:
            for n in names:
                cols[n].append(getattr(e, n))
        return {n: np.asarray(v) for n, v in cols.items()}


def read_meta(path):
    """The meta_* entries written by muon_tuple.py (how the tuple was made), as a dict."""
    meta = {}
    try:
        import uproot
        with uproot.open(path) as f:
            for key in f.keys(cycle=False):
                if key.startswith("meta_"):
                    meta[key[5:]] = str(f[key].member("fTitle"))
    except ImportError:
        import ROOT
        f = ROOT.TFile.Open(path)
        for k in f.GetListOfKeys():
            if k.GetName().startswith("meta_"):
                meta[k.GetName()[5:]] = f.Get(k.GetName()).GetTitle()
    return meta


def report_provenance(paths):
    """Print how the tuples were made and warn if they were made differently."""
    metas = [read_meta(p) for p in paths]
    keys = sorted({k for m in metas for k in m})
    if not keys:
        print("provenance: none stored in these tuples (made before metadata was added)")
        return
    print("provenance:")
    for k in keys:
        values = sorted({m.get(k, "<missing>") for m in metas})
        if k == "edep_file":
            continue
        if len(values) == 1:
            print("  %-24s %s" % (k, values[0]))
        else:
            print("  %-24s WARNING: files differ: %s" % (k, "; ".join(values)))


def load(paths):
    parts = [read_events(p) for p in paths]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def pct(x):
    return 100.0 * x


def binom_err(k, n):
    return np.sqrt(max(k, 0) * max(n - k, 0) / n ** 3) if n else float("nan")


def quantiles(x):
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    return tuple(np.percentile(x, [50, 16, 84]))


def frac_line(k, n):
    return "%d/%d = %.1f%% +- %.1f" % (k, n, pct(k / n) if n else float("nan"), pct(binom_err(k, n)))


def summarize(d, name, p_bins, region_x):
    n = len(d["event"])
    if n == 0:
        return
    found = d["found"].astype(bool)
    nseg = d["true_nseg_tms"]
    path = d["true_zhi_tms"] - d["true_zlo_tms"]
    recon = (nseg > 0) & (path > 1000.0)
    exits = d["true_exits_tms"].astype(bool)
    good = recon & found & (d["reco_true_p_enter"] > 0)
    print("\n" + "=" * 100)
    print("%s: %d muons thrown, %d with any TMS hit, %d reconstructible (>1 m TMS path)" % (name, n, int((nseg > 0).sum()), int(recon.sum())))
    print("  events with more than one reco track: %d" % int((d["n_tracks"] > 1).sum()))

    print("  tracking efficiency (event has a reco track):")
    print("    all thrown        %s" % frac_line(int(found.sum()), n))
    print("    any TMS hit       %s" % frac_line(int((found & (nseg > 0)).sum()), int((nseg > 0).sum())))
    print("    reconstructible   %s" % frac_line(int((found & recon).sum()), int(recon.sum())))
    for cls, sel in (("stopping", ~exits), ("exiting", exits)):
        m = recon & sel
        print("      %-9s       %s" % (cls, frac_line(int((found & m).sum()), int(m.sum()))))
    print("    by true p0 (reconstructible): " + "  ".join(
        "%d-%d: %s" % (lo, hi, frac_line(int((found & recon & (d["true_p0"] >= lo) & (d["true_p0"] < hi)).sum()), int((recon & (d["true_p0"] >= lo) & (d["true_p0"] < hi)).sum())))
        for lo, hi in zip(p_bins[:-1], p_bins[1:])))

    q_ok = d["reco_q"] == d["true_q"]
    print("  charge sign correct (found, reconstructible):")
    print("    all               %s" % frac_line(int((good & q_ok).sum()), int(good.sum())))
    for cls, sel in (("stopping", ~exits), ("exiting", exits)):
        m = good & sel
        print("      %-9s       %s" % (cls, frac_line(int((m & q_ok).sum()), int(m.sum()))))
    for rname, sel in (("central |x|<%d" % region_x, np.abs(d["reco_true_x_enter"]) < region_x), ("outer |x|>=%d" % region_x, np.abs(d["reco_true_x_enter"]) >= region_x)):
        m = good & sel
        print("      %-17s %s" % (rname, frac_line(int((m & q_ok).sum()), int(m.sum()))))
    print("    by true p_enter: " + "  ".join(
        "%d-%d: %s" % (lo, hi, frac_line(int((good & q_ok & (d["reco_true_p_enter"] >= lo) & (d["reco_true_p_enter"] < hi)).sum()), int((good & (d["reco_true_p_enter"] >= lo) & (d["reco_true_p_enter"] < hi)).sum())))
        for lo, hi in zip(p_bins[:-1], p_bins[1:])))

    print("  momentum, (reco - true)/true with true p entering the TMS: median [16%, 84%]   (n)")
    tp = d["reco_true_p_enter"]
    for cls, sel in (("stopping", ~exits), ("exiting", exits)):
        m = good & sel
        fit = (d["reco_p"][m] - tp[m]) / tp[m]
        has_range = d["reco_p_range"][m] > 0
        rng = (d["reco_p_range"][m][has_range] - tp[m][has_range]) / tp[m][has_range]
        print("    %-9s fit p   %+6.1f%% [%+6.1f, %+6.1f]  (%d)    range p %+6.1f%% [%+6.1f, %+6.1f]  (%d)" %
              ((cls,) + tuple(pct(v) for v in quantiles(fit)) + (m.sum(),) + tuple(pct(v) for v in quantiles(rng)) + (has_range.sum(),)))
    print("    fit p by true p_enter (all found):")
    for lo, hi in zip(p_bins[:-1], p_bins[1:]):
        m = good & (tp >= lo) & (tp < hi)
        fit = (d["reco_p"][m] - tp[m]) / tp[m]
        print("      %5d-%-5d  %+6.1f%% [%+6.1f, %+6.1f]  (%d)" % ((lo, hi) + tuple(pct(v) for v in quantiles(fit)) + (m.sum(),)))

    inside = d["reco_stops_inside"].astype(bool)
    tp_, fn_ = int((good & exits & ~inside).sum()), int((good & exits & inside).sum())
    fp_, tn_ = int((good & ~exits & ~inside).sum()), int((good & ~exits & inside).sum())
    print("  reco containment flag as an exit tag: true exits tagged %d, missed %d; true stops tagged exit %d, tagged stop %d" % (tp_, fn_, fp_, tn_))
    print("    purity %.0f%%, efficiency %.0f%%" % (pct(tp_ / max(1, tp_ + fp_)), pct(tp_ / max(1, tp_ + fn_))))
    for cname, sel in (("tagged contained", inside), ("tagged exiting", ~inside)):
        m = good & sel
        fit = (d["reco_p"][m] - tp[m]) / tp[m]
        has_range = d["reco_p_range"][m] > 0
        rng = (d["reco_p_range"][m][has_range] - tp[m][has_range]) / tp[m][has_range]
        print("    %-17s fit p %+6.1f%% [%+6.1f, %+6.1f]   range p %+6.1f%% [%+6.1f, %+6.1f]  (%d)" %
              ((cname,) + tuple(pct(v) for v in quantiles(fit)) + tuple(pct(v) for v in quantiles(rng)) + (m.sum(),)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--label", default="")
    ap.add_argument("--p-bins", default="500,1000,2000,3500,6000", help="momentum bin edges in MeV/c")
    ap.add_argument("--region-x", type=float, default=1860.0, help="|x| (mm) where the field changes sign")
    a = ap.parse_args()
    paths = sorted({p for pat in a.files for p in (glob.glob(pat) or [pat])})
    if not paths:
        sys.exit("no input files")
    d = load(paths)
    p_bins = [float(x) for x in a.p_bins.split(",")]
    print("%s%d files, %d muons" % (a.label + ": " if a.label else "", len(paths), len(d["event"])))
    report_provenance(paths)
    for name, sel in (("mu-", d["true_q"] == -1), ("mu+", d["true_q"] == 1), ("all muons", np.ones(len(d["event"]), bool))):
        summarize({k: v[sel] for k, v in d.items()}, name, p_bins, a.region_x)


if __name__ == "__main__":
    main()
