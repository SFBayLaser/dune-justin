#!/usr/bin/env python3
"""Efficiency of truth voxels vs deposit energy: where are the missed truth voxels?
Usage: eff_vs_energy.py larcv.root [--nevents N] [--tol r]   (run via larcv_env.sh in the container)"""
import argparse, numpy as np
import compare_truth as C
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--nevents", type=int, default=10); ap.add_argument("--tol", type=int, default=2)
a = ap.parse_args()
f = C.ROOT.TFile.Open(a.f)
edges = [0, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 1e9]
acc = {k: np.zeros((len(edges) - 1, 3)) for k in ("raw", "cut")}   # n, hit, energy
nE = np.zeros(len(edges) - 1)
for i in range(a.nevents):
    tid, tval, dims = C.read(f, C.TRUTH, i)
    for key, name in (("raw", "sparse3d_reco"), ("cut", "sparse3d_reco_rescaled")):
        rid, _, _ = C.read(f, name, i)
        m = C.near(tid, rid, dims, a.tol)
        for b in range(len(edges) - 1):
            s = (tval >= edges[b]) & (tval < edges[b + 1])
            acc[key][b] += [s.sum(), (s & m).sum(), tval[s].sum()]
tot = acc["raw"][:, 0].sum(); etot = acc["raw"][:, 2].sum()
print(f"{a.f}  events={a.nevents} tol={a.tol}  truth voxels/event={tot/a.nevents:.0f}")
print(f"{'E_voxel(MeV)':<14}{'frac vox':>9}{'frac E':>8}{'eff raw':>9}{'eff cuts':>9}")
for b in range(len(edges) - 1):
    n, h, e = acc["raw"][b]; hc = acc["cut"][b][1]
    print(f"{edges[b]:<6}-{min(edges[b+1],99):<6}{n/tot:>9.3f}{e/etot:>8.3f}{h/max(n,1):>9.3f}{hc/max(n,1):>9.3f}")
