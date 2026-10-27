#!/usr/bin/env python3
"""Performance against the fraction of bad channels: collect the validation outputs of the bad channel scan.

Reads the per-spill files  *_BadCh_<set>_<version>_RecoCandidates_validation_{legacy,cluster3d}.root  made by
tms_validation.jobscript for the sets of tms_badchannels_make_configs.py (<set> = f<percent>_s<seed>, f00 = none),
adds the histograms over spills for each set and reconstruction, and writes a table (csv, json) and a figure.

By default only spills present for every set and for both reconstructions are used (--spills common), so every set sees
the same events (the simulation is seeded per event, so the sets then differ only by the bad channels). Spills missing from
some set are listed. With many missing files that leaves few spills; --spills each uses every set's own spills (more
statistics, but the sets are then not exactly paired).

Efficiencies and the charge ID are numerator / denominator integrals with Wilson 68% intervals. Means and rms come
from the histograms' own statistics (exact, they add across files); their error is rms / sqrt(n).

  reco_eff__muon_ke_tms_enter        muon efficiency: muons from the ND-LAr fiducial volume entering the TMS (headline)
  reco_eff__good_reco_...            the same, with the "good reco" requirement
  reco_eff__all_muon_... *           all muons / muons from TMS vertices.  * Their denominators depend on which muons
  reco_eff__tms_vertex_... *         have hits, so they change with the bad channels (seen in the pilot): read with care.
  charge_id__true_muon / antimuon    charge ID efficiency
  reco_track__cleanliness_energy     purity: energy fraction of the track from its main true particle
  momentum__completeness__*          momentum completeness (contained / exiting muons)
  momentum__resolution__*            momentum resolution (mean and rms of (reco - true) / true)

Usage: badchannel_scan.py DATA_DIR OUT_DIR [--version v01] [--sets f00 f25_s1 ...] [--spills common|each]
Needs uproot, numpy, matplotlib (the dune-tms python environment on the laptop).
"""
import argparse
import collections
import csv
import json
import math
import os
import re
import sys

import numpy as np
import uproot

NAME = re.compile(r"sanddrift\.(\d+)\..*_BadCh_(f\d+(?:_s\d+)?)_(v\d+)_RecoCandidates_validation_(legacy|cluster3d)\.root$")

# (key, label, kind, histogram(s), note). kind: eff (numerator/denominator), mean, rms
METRICS = [
    ("eff_muon", "Muon efficiency (LAr vertex, enters TMS)", "eff", "reco_eff__muon_ke_tms_enter"),
    ("eff_good", "Good-reco muon efficiency", "eff", "reco_eff__good_reco_muon_ke_tms_enter"),
    ("eff_all", "All-muon efficiency (*)", "eff", "reco_eff__all_muon_ke_tms_enter"),
    ("eff_tmsvtx", "TMS-vertex muon efficiency (*)", "eff", "reco_eff__tms_vertex_muon_ke_tms_enter"),
    ("cid_mu", "Charge ID, mu-", "eff", "charge_id__true_muon"),
    ("cid_amu", "Charge ID, mu+", "eff", "charge_id__true_antimuon"),
    ("purity_e", "Track purity (energy cleanliness)", "mean", "reco_track__cleanliness_energy"),
    ("purity_n", "Track purity (hit cleanliness)", "mean", "reco_track__cleanliness_nhits"),
    ("compl_cont", "Momentum completeness, contained", "mean", "momentum__completeness__contained"),
    ("compl_exit", "Momentum completeness, exiting", "mean", "momentum__completeness__exiting"),
    ("res_cont_mean", "Momentum resolution mean, contained", "mean", "momentum__resolution__contained"),
    ("res_cont_rms", "Momentum resolution rms, contained", "rms", "momentum__resolution__contained"),
    ("res_exit_mean", "Momentum resolution mean, exiting", "mean", "momentum__resolution__exiting"),
    ("res_exit_rms", "Momentum resolution rms, exiting", "rms", "momentum__resolution__exiting"),
    ("track_hits", "Hits per track", "mean", "special__track_nhits"),
    ("n_tracks", "Tracks per slice", "mean", "basic__raw__ntracks"),
]
HISTS = sorted({h for m in METRICS for h in ([m[3] + "_numerator", m[3] + "_denominator"] if m[2] == "eff" else [m[3]])})


def read_file(path):
    """The needed statistics of one file: eff -> (sum num, sum den); others -> (sumw, sumwx, sumwx2)."""
    out = {}
    with uproot.open(path) as f:
        have = set(f.keys(cycle=False))
        for h in HISTS:
            if h not in have:
                continue
            t = f[h]
            if h.endswith("_numerator") or h.endswith("_denominator"):
                out[h] = float(t.values().sum())  # in-range bins, as the validation plots
            else:
                out[h] = (float(t.member("fTsumw")), float(t.member("fTsumwx")), float(t.member("fTsumwx2")))
    return out


def wilson(k, n, z=1.0):
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - w, c + w


def evaluate(stats):
    """stats: summed file statistics of one (set, kind) -> {metric key: (value, err_lo, err_hi, n)}."""
    res = {}
    for key, _, kind, h in METRICS:
        if kind == "eff":
            k, n = stats.get(h + "_numerator"), stats.get(h + "_denominator")
            if n is None or n == 0:
                continue
            p, lo, hi = wilson(k, n)
            res[key] = (p, p - lo, hi - p, n)
        else:
            s = stats.get(h)
            if s is None or s[0] <= 0:
                continue
            sw, swx, swx2 = s
            mean = swx / sw
            rms = math.sqrt(max(swx2 / sw - mean * mean, 0.0))
            err = rms / math.sqrt(sw)
            res[key] = (mean if kind == "mean" else rms, err, err, sw)
    return res


def add(a, b):
    for h, v in b.items():
        if isinstance(v, tuple):
            a[h] = tuple(x + y for x, y in zip(a.get(h, (0, 0, 0)), v))
        else:
            a[h] = a.get(h, 0.0) + v


def percent(name):
    return int(re.match(r"f(\d+)", name).group(1))


def seed(name):
    m = re.search(r"_s(\d+)", name)
    return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--version", default="v01")
    ap.add_argument("--sets", nargs="+")
    ap.add_argument("--spills", choices=("common", "each"), default="common")
    args = ap.parse_args()

    files = collections.defaultdict(dict)  # (set, kind) -> {spill: path}
    for root, _, names in os.walk(args.data_dir):
        for n in names:
            m = NAME.search(n)
            if m and m.group(3) == args.version and (not args.sets or m.group(2) in args.sets):
                files[(m.group(2), m.group(4))][int(m.group(1))] = os.path.join(root, n)
    if not files:
        sys.exit(f"no {args.version} validation files under {args.data_dir}")
    sets = sorted({s for s, _ in files}, key=lambda s: (percent(s), seed(s)))
    kinds = ("legacy", "cluster3d")

    spill_sets = [set(files[(s, k)]) for s in sets for k in kinds if (s, k) in files]
    common = set.intersection(*spill_sets)
    allspills = set.union(*spill_sets)
    print(f"{len(sets)} sets, {len(allspills)} spills in any set, {len(common)} in every set and both reconstructions")
    for s in sets:
        for k in kinds:
            lost = sorted(allspills - set(files.get((s, k), {})))
            if lost:
                print(f"  {s} {k}: missing {len(lost)} spill(s): {lost[:10]}{' ...' if len(lost) > 10 else ''}")
    if args.spills == "common":
        if not common:
            sys.exit("no spill is present in every set (use --spills each)")
        if len(common) < 0.8 * len(allspills):
            print(f"WARNING: only {len(common)} of {len(allspills)} spills are in every set; --spills each keeps more")
        use = {(s, k): common for s in sets for k in kinds}
    else:
        use = {(s, k): set(files.get((s, k), {})) for s in sets for k in kinds}
        # With each set's own spills, the legacy and Cluster3D results of a set still use the same spills
        for s in sets:
            both = use[(s, "legacy")] & use[(s, "cluster3d")]
            use[(s, "legacy")] = use[(s, "cluster3d")] = both
    nspill = {sk: len(v) for sk, v in use.items()}
    print(f"spills used per set: min {min(nspill.values())}, max {max(nspill.values())}")

    results = {}
    for s in sets:
        for k in kinds:
            total = {}
            for sp in sorted(use[(s, k)]):
                add(total, read_file(files[(s, k)][sp]))
            results[(s, k)] = evaluate(total)
        print(f"  read {s}: {nspill[(s, 'legacy')]} spills")

    os.makedirs(args.out_dir, exist_ok=True)
    rows = []
    for (s, k), res in results.items():
        for key, label, _, _ in METRICS:
            if key in res:
                v, lo, hi, n = res[key]
                rows.append({"set": s, "bad_percent": percent(s), "seed": seed(s), "reco": k, "metric": key,
                             "label": label, "value": v, "err_low": lo, "err_high": hi, "n": n, "n_spills": nspill[(s, k)]})
    with open(os.path.join(args.out_dir, "badchannel_scan.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.out_dir, "badchannel_scan.json"), "w") as f:
        json.dump(rows, f, indent=1)

    # Text table: the seed average of the headline metrics per fraction
    print(f"\n{'metric':42s} {'reco':10s} " + " ".join(f"{p:>8d}%" for p in sorted({percent(s) for s in sets})))
    for key, label, _, _ in METRICS:
        for k in kinds:
            cells = []
            for p in sorted({percent(s) for s in sets}):
                vals = [results[(s, k)][key][0] for s in sets if percent(s) == p and key in results[(s, k)]]
                cells.append(f"{np.mean(vals):9.3f}" if vals else f"{'-':>9s}")
            print(f"{label[:42]:42s} {k:10s} " + " ".join(cells))

    try:
        plot(results, sets, nspill, args.out_dir)
    except ImportError as e:
        print(f"matplotlib not available, no figure: {e}")


def plot(results, sets, nspill, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Reference palette, categorical slots 1 and 2 (blue, orange); marker shape and line style also distinguish
    style = {"cluster3d": dict(color="#2a78d6", marker="o", ls="-", label="Cluster3D"),
             "legacy": dict(color="#eb6834", marker="s", ls="--", label="Legacy")}
    panels = [("eff_muon", "Muon efficiency (LAr vertex, enters TMS)"), ("eff_good", "Good-reco muon efficiency"),
              ("cid_mu", "Charge ID, mu-"), ("purity_e", "Track purity (energy cleanliness)"),
              ("compl_cont", "Momentum completeness, contained"), ("res_cont_rms", "Momentum resolution rms, contained"),
              ("track_hits", "Hits per track"), ("eff_all", "All-muon efficiency (*)")]
    fig, axes = plt.subplots(2, 4, figsize=(17, 8), constrained_layout=True)
    pcts = sorted({percent(s) for s in sets})
    for ax, (key, title) in zip(axes.flat, panels):
        for k, st in style.items():
            xs, ys, es = [], [], []
            for p in pcts:
                pts = [results[(s, k)][key] for s in sets if percent(s) == p and key in results[(s, k)]]
                if not pts:
                    continue
                for v, lo, hi, _ in pts:  # one faint point per seed
                    ax.errorbar([p], [v], yerr=[[lo], [hi]], color=st["color"], marker=st["marker"], ms=5,
                                mfc="none", lw=0.8, alpha=0.45, ls="none")
                xs.append(p)
                ys.append(np.mean([v for v, *_ in pts]))
            ax.plot(xs, ys, color=st["color"], marker=st["marker"], ls=st["ls"], lw=2, ms=8, label=st["label"],
                    mec="#fcfcfb", mew=1.5)
        ax.set_title(title, fontsize=10, color="#0b0b0b")
        ax.set_xlabel("bad channels (% of bars)", fontsize=9, color="#52514e")
        ax.set_xticks(pcts)
        ax.grid(axis="y", color="#e5e4e0", lw=0.8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_facecolor("#fcfcfb")
    axes.flat[0].legend(frameon=False, fontsize=9)
    fig.patch.set_facecolor("#fcfcfb")
    fig.suptitle(f"Performance vs random bad channels: {min(nspill.values())}-{max(nspill.values())} spills per set; line = mean over seeds, hollow = single seed "
                 f"(binomial or rms/sqrt(n) errors). (*) denominator changes with the bad channels", fontsize=10, color="#52514e")
    path = os.path.join(out_dir, "badchannel_scan.png")
    fig.savefig(path, dpi=130)
    print("wrote", path)


if __name__ == "__main__":
    main()
