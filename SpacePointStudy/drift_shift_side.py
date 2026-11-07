#!/usr/bin/env python3
"""x-shift peak per x-bin (position along the drift axis). Truth voxels > --min-sed are split into --nbins equal x bins;
for each bin: the shift s (voxels, along x, y/z within +-1) with the most matching reco voxels, and fraction at s = 0 and at the peak.
Usage: drift_shift_side.py larcv.root [--nevents N] [--nbins 4]   (via larcv_env.sh in the container)"""
import argparse, itertools, numpy as np
import compare_truth as C
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--nevents", type=int, default=8)
ap.add_argument("--min-sed", type=float, default=0.5); ap.add_argument("--max-shift", type=int, default=8); ap.add_argument("--nbins", type=int, default=4)
a = ap.parse_args(); f = C.ROOT.TFile.Open(a.f); S = a.max_shift; shifts = list(range(-S, S + 1)); B = a.nbins
hits = np.zeros((B, len(shifts))); n = np.zeros(B)
for i in range(a.nevents):
    tid, tval, dims = C.read(f, C.TRUTH, i); tid = tid[tval > a.min_sed]
    rid, _, _ = C.read(f, "sparse3d_reco_rescaled", i); rset = np.sort(rid); nx, ny, nz = dims; x, y, z = C.xyz(tid, dims)
    b = np.minimum(x * B // nx, B - 1)
    for k in range(B): n[k] += (b == k).sum()
    for j, s in enumerate(shifts):
        hit = np.zeros(len(tid), bool)
        for dy, dz in itertools.product((-1, 0, 1), repeat=2):
            xx, yy, zz = x + s, y + dy, z + dz; ok = (xx >= 0) & (xx < nx) & (yy >= 0) & (yy < ny) & (zz >= 0) & (zz < nz)
            key = xx + nx * (yy + ny * zz); pos = np.searchsorted(rset, key); pos[pos == len(rset)] = 0; hit |= ok & (rset[pos] == key)
        for k in range(B): hits[k, j] += hit[b == k].sum()
print(f"{a.f}  nx={nx}  x bins (low x -> high x)")
for k in range(B):
    fr = hits[k] / n[k]; print(f"bin {k} (x idx {k*nx//B}-{(k+1)*nx//B}): n={int(n[k])}  peak shift {shifts[int(np.argmax(fr))]:+d} frac {fr.max():.3f}  at0 {fr[S]:.3f}")
