#!/usr/bin/env python3
"""Inefficiency (1 - efficiency) of the reco space points against the angle theta_x between the truth particle direction and the
drift (x) axis. Each truth voxel of cluster3d_sed (true deposit positions) belongs to a particle (momentum from particle_pcluster); theta_x is folded to
0-90 degrees (|px|/|p|), so 90 = parallel to the wire planes (perpendicular to x), 0 = along the drift direction.
A truth voxel is efficient if a reco voxel (sparse3d_reco_rescaled) lies within --r voxels (Chebyshev) in all axes.
Usage: theta_inefficiency.py NAME=larcv.root [NAME=larcv.root ...] [--nevents N] [--r 2] [--min-voxels 20] [--bin 10] [--json out.json]
(run via larcv_env.sh in the container)"""
import argparse, itertools, json, numpy as np
import compare_truth as C
ap = argparse.ArgumentParser(); ap.add_argument("inputs", nargs="+"); ap.add_argument("--nevents", type=int, default=20)
ap.add_argument("--r", type=int, default=2); ap.add_argument("--min-voxels", type=int, default=20)
ap.add_argument("--bin", type=float, default=10.); ap.add_argument("--json"); a = ap.parse_args()
def near(ids_a, ids_b, dims, r):
    nx, ny, nz = dims; ax, ay, az = C.xyz(ids_a, dims); bset = np.sort(ids_b); hit = np.zeros(len(ids_a), bool)
    for dx, dy, dz in itertools.product(range(-r, r + 1), repeat=3):
        x, y, z = ax + dx, ay + dy, az + dz
        ok = (x >= 0) & (x < nx) & (y >= 0) & (y < ny) & (z >= 0) & (z < nz); key = x + nx * (y + ny * z)
        pos = np.searchsorted(bset, key); pos[pos == len(bset)] = 0; hit |= ok & (bset[pos] == key)
    return hit
edges = np.arange(0, 90 + a.bin, a.bin); res = {}
for spec in a.inputs:
    name, path = spec.split("=", 1) if "=" in spec else (spec, spec); f = C.ROOT.TFile.Open(path)
    n = np.zeros(len(edges) - 1); nm = np.zeros(len(edges) - 1); e = np.zeros(len(edges) - 1); em = np.zeros(len(edges) - 1)
    for i in range(a.nevents):
        tp = f.Get("particle_pcluster_tree"); tp.GetEntry(i); parts = tp.particle_pcluster_branch.as_vector()
        tc = f.Get("cluster3d_sed_tree"); tc.GetEntry(i); cl = tc.cluster3d_sed_branch   # sed cluster k <-> particle k (one extra leftover cluster at the end)
        rid, _, dims = C.read(f, "sparse3d_reco_rescaled", i)
        for k in range(parts.size()):
            p = parts[k]; vs = cl.voxel_set(k); vv = vs.as_vector(); nv = vv.size()
            pm = (p.px() ** 2 + p.py() ** 2 + p.pz() ** 2) ** 0.5
            if nv < a.min_voxels or pm <= 0: continue
            th = np.degrees(np.arccos(min(1., abs(p.px()) / pm)))
            ids = np.array([vv[j].id() for j in range(nv)], dtype=np.int64); en = np.array([vv[j].value() for j in range(nv)])
            hit = near(ids, rid, dims, a.r); b = min(int(th // a.bin), len(edges) - 2)
            n[b] += nv; nm[b] += (~hit).sum(); e[b] += en.sum(); em[b] += en[~hit].sum()
    res[name] = {"edges": edges.tolist(), "voxels": n.tolist(), "ineff": (nm / np.maximum(n, 1)).tolist(), "ineff_E": (em / np.maximum(e, 1e-9)).tolist()}
print(f"inefficiency vs theta_x (r = {a.r}, particles with >= {a.min_voxels} voxels, {a.nevents} events)")
print("theta_x      " + "".join(f"{int(edges[j])}-{int(edges[j+1])}".rjust(10) for j in range(len(edges) - 1)))
for name, r in res.items():
    print(f"{name:<10} N " + "".join(f"{int(v):>10}" for v in r["voxels"])); print(f"{'':<10} 1-eff " + "".join(f"{v:>7.3f}   " for v in r["ineff"]))
    print(f"{'':<10} 1-eff(E) " + "".join(f"{v:>4.3f}     " for v in r["ineff_E"]))
if a.json: json.dump(res, open(a.json, "w"))
