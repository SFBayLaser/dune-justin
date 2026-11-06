#!/usr/bin/env python3
"""Efficiency / ghost fraction with an anisotropic tolerance: +-rx along x (drift), +-2 along y and z.
If a per-particle time offset shifts reco along the drift axis, efficiency should climb as rx grows past 2.
Usage: drift_tolerance.py larcv.root [--nevents N] [--min-sed E] [--rx 2 3 4 6]  (via larcv_env.sh in the container)"""
import argparse, itertools, numpy as np
import compare_truth as C
def near_a(ids_a, ids_b, dims, rx, ry, rz):
    nx, ny, nz = dims; ax, ay, az = C.xyz(ids_a, dims); bset = np.sort(ids_b); hit = np.zeros(len(ids_a), bool)
    for dx, dy, dz in itertools.product(range(-rx, rx + 1), range(-ry, ry + 1), range(-rz, rz + 1)):
        x, y, z = ax + dx, ay + dy, az + dz
        ok = (x >= 0) & (x < nx) & (y >= 0) & (y < ny) & (z >= 0) & (z < nz); key = x + nx * (y + ny * z)
        pos = np.searchsorted(bset, key); pos[pos == len(bset)] = 0; hit |= ok & (bset[pos] == key)
    return hit
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--nevents", type=int, default=8)
ap.add_argument("--min-sed", type=float, default=0.0); ap.add_argument("--rx", type=int, nargs="+", default=[2, 3, 4, 6])
a = ap.parse_args(); f = C.ROOT.TFile.Open(a.f)
print(f"{a.f}  events={a.nevents} min_sed={a.min_sed}  (ry = rz = 2)")
print(f"{'rx':>3}{'eff':>8}{'eff(E)':>8}{'eff>0.5MeV':>12}{'ghost':>8}")
for rx in a.rx:
    e = ee = eh = g = 0.0; n = 0
    for i in range(a.nevents):
        tid, tval, dims = C.read(f, C.TRUTH, i); s = tval > a.min_sed; tid, tval = tid[s], tval[s]
        rid, _, _ = C.read(f, "sparse3d_reco_rescaled", i)
        m = near_a(tid, rid, dims, rx, 2, 2); gm = ~near_a(rid, tid, dims, rx, 2, 2); h = tval > 0.5
        e += m.mean(); ee += tval[m].sum() / tval.sum(); eh += m[h].mean(); g += gm.mean(); n += 1
    print(f"{rx:>3}{e/n:>8.3f}{ee/n:>8.3f}{eh/n:>12.3f}{g/n:>8.3f}")
