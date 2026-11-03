#!/usr/bin/env python3
"""Geometric truth comparison of space-point builders using Supera larcv output.

Truth  : sparse3d_sed          (true energy deposits, MeV)
Reco   : sparse3d_reco         (raw space points)   and
         sparse3d_reco_rescaled (after the Supera cuts/rescaling)

For tolerance r (in voxels, Chebyshev distance):
  efficiency = fraction of truth voxels having a reco voxel within r   (also energy weighted)
  ghost frac = fraction of reco voxels having no truth voxel within r
  n_ghost    = number of reco voxels with no truth voxel within r (per event)

Reco voxels are also split by the number of hits that made the point (sparse3d_reco_nhits):
  all, 3hit (triplets), 2hit ("mythical" points). Efficiency of a class uses only that class's points.
Chi-square cuts can be emulated offline, since the chi2 of each point is stored (sparse3d_reco_chi2):
  --max-chi2-3hit X / --max-chi2-2hit Y drop points above the cut (cannot be looser than the run's own cut).

Usage: compare_truth.py LABEL=larcv.root [LABEL=larcv.root ...] [--tol 0 1 2 4] [--nevents N]
       [--max-chi2-3hit X] [--max-chi2-2hit Y] [--json out.json]
Run via larcv_env.sh (PyROOT + cvmfs larcv2).
"""
import argparse, itertools, json
import numpy as np
import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kFatal
ROOT.gSystem.Load("liblarcv.so")

TRUTH = "sparse3d_sed"
RECO = ["sparse3d_reco", "sparse3d_reco_rescaled"]


def read(tree_file, name, i):
    t = tree_file.Get(name + "_tree")
    t.GetEntry(i)
    b = getattr(t, name + "_branch")
    m = b.meta()
    v = b.as_vector()
    n = v.size()
    ids = np.empty(n, dtype=np.int64)
    val = np.empty(n, dtype=np.float64)
    for k in range(n):
        ids[k] = v[k].id()
        val[k] = v[k].value()
    dims = (m.num_voxel_x(), m.num_voxel_y(), m.num_voxel_z())
    return ids, val, dims


def xyz(ids, dims):
    nx, ny, _ = dims
    return ids % nx, (ids // nx) % ny, ids // (nx * ny)


def near(ids_a, ids_b, dims, r):
    """bool mask: each voxel of A has a voxel of B within Chebyshev distance r"""
    nx, ny, nz = dims
    ax, ay, az = xyz(ids_a, dims)
    bset = np.sort(ids_b)
    hit = np.zeros(len(ids_a), dtype=bool)
    rng = range(-r, r + 1)
    for dx, dy, dz in itertools.product(rng, rng, rng):
        x, y, z = ax + dx, ay + dy, az + dz
        ok = (x >= 0) & (x < nx) & (y >= 0) & (y < ny) & (z >= 0) & (z < nz)
        key = x + nx * (y + ny * z)
        pos = np.searchsorted(bset, key)
        pos[pos == len(bset)] = 0
        hit |= ok & (bset[pos] == key) if len(bset) else False
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="LABEL=path/to/larcv.root")
    ap.add_argument("--tol", type=int, nargs="+", default=[0, 1, 2, 4])
    ap.add_argument("--min-sed", type=float, default=0.0, help="min truth voxel energy (MeV)")
    ap.add_argument("--nevents", type=int, default=None)
    ap.add_argument("--max-chi2-3hit", type=float, default=None)
    ap.add_argument("--max-chi2-2hit", type=float, default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    out = {}
    for item in a.inputs:
        label, path = item.split("=", 1)
        f = ROOT.TFile.Open(path)
        n = f.Get(TRUTH + "_tree").GetEntries()
        if a.nevents:
            n = min(n, a.nevents)
        rows = []
        for i in range(n):
            tid, tval, dims = read(f, TRUTH, i)
            sel = tval > a.min_sed
            tid, tval = tid[sel], tval[sel]
            raw_id, _, _ = read(f, "sparse3d_reco", i)
            nid, nh, _ = read(f, "sparse3d_reco_nhits", i)
            cid, chi, _ = read(f, "sparse3d_reco_chi2", i)
            assert np.array_equal(raw_id, nid) and np.array_equal(raw_id, cid)
            keep = np.ones(len(raw_id), dtype=bool)
            if a.max_chi2_3hit is not None:
                keep &= ~((nh == 3) & (chi > a.max_chi2_3hit))
            if a.max_chi2_2hit is not None:
                keep &= ~((nh == 2) & (chi > a.max_chi2_2hit))
            for rn in RECO:
                if rn == "sparse3d_reco":
                    rid, rnh = raw_id[keep], nh[keep]
                else:
                    qid, _, _ = read(f, rn, i)
                    pos = np.searchsorted(raw_id, qid)          # rescaled voxels are a subset of raw voxels
                    ok = keep[pos]
                    rid, rnh = qid[ok], nh[pos][ok]
                for cls, cmask in (("all", np.ones(len(rid), bool)), ("3hit", rnh == 3), ("2hit", rnh == 2)):
                    cid_ = rid[cmask]
                    for r in a.tol:
                        if len(cid_) == 0:
                            eff = eff_e = 0.0; gh = 0.0; ngh = 0
                        else:
                            eff_mask = near(tid, cid_, dims, r)
                            gh_mask = ~near(cid_, tid, dims, r)
                            eff, eff_e = float(eff_mask.mean()), float(tval[eff_mask].sum() / tval.sum())
                            gh, ngh = float(gh_mask.mean()), int(gh_mask.sum())
                        rows.append(dict(event=i, reco=rn, cls=cls, tol=r, n_truth=int(len(tid)), n_reco=int(len(cid_)),
                                         eff=eff, eff_e=eff_e, ghost=gh, n_ghost=ngh))
        out[label] = rows

    # summary table (mean over events)
    print(f"{'label':<14}{'reco':<24}{'cls':<5}{'tol':>4}{'<n_reco>':>10}{'<n_ghost>':>10}{'eff':>8}{'eff(E)':>8}{'ghost':>8}")
    for label, rows in out.items():
        for rn in RECO:
            for cls in ("all", "3hit", "2hit"):
                for r in a.tol:
                    s = [x for x in rows if x["reco"] == rn and x["cls"] == cls and x["tol"] == r]
                    m = lambda k: np.mean([x[k] for x in s])
                    print(f"{label:<14}{rn:<24}{cls:<5}{r:>4}{m('n_reco'):>10.0f}{m('n_ghost'):>10.0f}"
                          f"{m('eff'):>8.3f}{m('eff_e'):>8.3f}{m('ghost'):>8.3f}")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
