#!/usr/bin/env python3
"""Does a time offset shift reco relative to truth? For truth voxels above --min-sed, the fraction that have a reco
voxel at truth + s along one axis (other two axes within +-1 voxel), for s in -S..S. A peak away from s = 0, or a broad peak,
means a per-particle/per-event time offset is moving reco along that axis (drift = the axis showing it).
Usage: drift_shift.py larcv.root [--nevents N] [--min-sed 0.5] [--max-shift 12]   (run via larcv_env.sh in the container)"""
import argparse, itertools, numpy as np
import compare_truth as C
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--nevents", type=int, default=10)
ap.add_argument("--min-sed", type=float, default=0.5); ap.add_argument("--max-shift", type=int, default=12)
ap.add_argument("--reco", default="sparse3d_reco_rescaled"); a = ap.parse_args()
f = C.ROOT.TFile.Open(a.f); S = a.max_shift; shifts = list(range(-S, S + 1))
hits = {ax: np.zeros(len(shifts)) for ax in "xyz"}; ntot = 0
for i in range(a.nevents):
    tid, tval, dims = C.read(f, C.TRUTH, i); sel = tval > a.min_sed; tid = tid[sel]
    rid, _, _ = C.read(f, a.reco, i); rset = np.sort(rid)
    nx, ny, nz = dims; x, y, z = C.xyz(tid, dims); ntot += len(tid)
    for k, ax in enumerate("xyz"):
        for j, s in enumerate(shifts):
            hit = np.zeros(len(tid), bool)
            for d1, d2 in itertools.product((-1, 0, 1), repeat=2):
                off = [d1, d2]; d = [0, 0, 0]
                oth = [m for m in range(3) if m != k]; d[k] = s; d[oth[0]] = off[0]; d[oth[1]] = off[1]
                xx, yy, zz = x + d[0], y + d[1], z + d[2]
                ok = (xx >= 0) & (xx < nx) & (yy >= 0) & (yy < ny) & (zz >= 0) & (zz < nz)
                key = xx + nx * (yy + ny * zz); pos = np.searchsorted(rset, key); pos[pos == len(rset)] = 0
                hit |= ok & (rset[pos] == key)
            hits[ax][j] += hit.sum()
print(f"{a.f} {a.reco} events={a.nevents} truth voxels>{a.min_sed} MeV: {ntot}   (rows: shift in voxels, columns: fraction matched)")
print("shift " + "".join(f"{ax:>8}" for ax in "xyz"))
for j, s in enumerate(shifts): print(f"{s:>5} " + "".join(f"{hits[ax][j]/ntot:>8.3f}" for ax in "xyz"))
for ax in "xyz": print(ax, "peak shift:", shifts[int(np.argmax(hits[ax]))], " frac at 0: %.3f  max: %.3f" % (hits[ax][S] / ntot, hits[ax].max() / ntot))
