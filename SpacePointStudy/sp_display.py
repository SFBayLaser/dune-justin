#!/usr/bin/env python3
"""3D event display of truth deposits and space points, one self-contained HTML page (three.js from a CDN), layers switchable in the page.

Layers:  SimEnergyDeposit midpoints (cyan)   SimChannel IDE positions (magenta)   true space points (yellow: 3-hit, gold: 2-hit)   other space points (light gray, off by default)
The 'true' label is chosen in the page: shared deposit fraction f, deposit distance delta, and an optional position tolerance (point within tol of the matched deposits'
centroid), the same definitions as sp_truth_dep.py (normal hits only; long-hit points are always drawn as 'other').
Points come from point_dir/points.npy + points_cols.json (sp_truth_dep.py --dump; needs the pdist_f* columns).  Deposits are voxelised (--vox) to keep the page small.
Only 3-hit points and 2-hit points that are true under the loosest label (f 0.01, delta 0.4, or ball f 0.01) are embedded; other 2-hit points are left out.
If points.npy has the ballF_R* columns (sp_truth_dep.py --dump --ball) the page also offers the sliding-ball label (particle-level fraction f inside a ball of radius R, optionally with the point within 0.5 cm of the particle's deposits in the ball; long-hit points included).
Usage (SL7 container, gallery_env.sh):
  sp_display.py point_dir --sim-file in_supera.root --events 0 1 2 --out display.html [--vox 0.5] [--sed-tag IonAndScint] [--sc-tag tpcrawdecoder:simpleSC]"""
import argparse, base64, json, os
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("d"); ap.add_argument("--sim-file", required=True); ap.add_argument("--events", type=int, nargs="+", default=[0, 1, 2])
ap.add_argument("--out", default="display.html"); ap.add_argument("--vox", type=float, default=0.5)
ap.add_argument("--sed-tag", default="IonAndScint"); ap.add_argument("--sc-tag", default="tpcrawdecoder:simpleSC"); ap.add_argument("--title", default="")
a = ap.parse_args()
import ROOT
for l in ("libgallery", "liblardataobj_Simulation"): ROOT.gSystem.Load(l)
for v in ("LARDATAOBJ_INC", "NUSIMDATA_INC", "CANVAS_INC", "CETLIB_EXCEPT_INC"):
    if os.environ.get(v): ROOT.gInterpreter.AddIncludePath(os.environ[v])
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')
ROOT.gInterpreter.Declare('#include "lardataobj/Simulation/SimEnergyDeposit.h"')
ROOT.gInterpreter.Declare('''
void fill_ides(const std::vector<sim::SimChannel>& scs, std::vector<float>& o) {
  for (auto const& sc : scs) for (auto const& tdc : sc.TDCIDEMap()) for (auto const& ide : tdc.second) { o.push_back(ide.x); o.push_back(ide.y); o.push_back(ide.z); o.push_back(ide.energy); } }
void fill_seds(const std::vector<sim::SimEnergyDeposit>& v, std::vector<float>& o) {
  for (auto const& d : v) { auto p = d.MidPoint(); o.push_back(p.X()); o.push_back(p.Y()); o.push_back(p.Z()); o.push_back(d.Energy()); } }
''')
tag = lambda s: ROOT.art.InputTag(*s.split(":")) if ":" in s else ROOT.art.InputTag(s)
v = ROOT.std.vector(ROOT.std.string)(); v.push_back(a.sim_file); sim = ROOT.gallery.Event(v)


def to_np(vec):
    n = len(vec)
    return np.frombuffer(vec.data(), dtype=np.float32, count=n).reshape(-1, 4).copy() if n else np.zeros((0, 4), np.float32)


def voxelise(arr, vox):
    """(N,4) x,y,z,E -> energy-weighted position per vox-cm cell, with the cell energy"""
    if not len(arr): return arr
    k = np.floor(arr[:, :3] / vox).astype(np.int64); k -= k.min(0)
    key = (k[:, 0] * (k[:, 1].max() + 1) + k[:, 1]) * (k[:, 2].max() + 1) + k[:, 2]
    u, inv = np.unique(key, return_inverse=True); e = np.bincount(inv, weights=arr[:, 3]); out = np.zeros((len(u), 4), np.float32)
    for j in range(3): out[:, j] = np.bincount(inv, weights=arr[:, 3] * arr[:, j]) / np.maximum(e, 1e-12)
    out[:, 3] = e
    return out


b64 = lambda x: base64.b64encode(np.ascontiguousarray(x).tobytes()).decode()
P = np.load(os.path.join(a.d, "points.npy")); cols = json.load(open(os.path.join(a.d, "points_cols.json"))); C = {c: P[:, i] for i, c in enumerate(cols)}
fl = [c[len("dmin_f"):] for c in cols if c.startswith("dmin_f")]
BR = sorted(float(c[len("ballF_R"):-len("_pos")]) for c in cols if c.startswith("ballF_R") and c.endswith("_pos"))
assert all(f"pdist_f{f}" in C for f in fl), "points.npy has no pdist_f* columns: rerun sp_truth_dep.py --dump"
events = []
for iev in a.events:
    sim.goToEntry(iev); aux = sim.eventAuxiliary()
    seds = ROOT.std.vector("float")(); ROOT.fill_seds(sim.getValidHandle[ROOT.vector[ROOT.sim.SimEnergyDeposit]](tag(a.sed_tag)).product(), seds)
    ides = ROOT.std.vector("float")(); ROOT.fill_ides(sim.getValidHandle[ROOT.vector[ROOT.sim.SimChannel]](tag(a.sc_tag)).product(), ides)
    sed = voxelise(to_np(seds), a.vox); ide = voxelise(to_np(ides), a.vox)
    m = C["ev"] == iev; dmin = np.stack([C[f"dmin_f{f}"] for f in fl], 1); keep2 = dmin.min(1) <= 0.4
    if BR: keep2 = keep2 | (np.stack([C[f"ballF_R{R:g}_pos"] for R in BR], 1).max(1) >= 0.01)
    keep = m & ((C["n"] == 3) | ((C["n"] == 2) & keep2))
    xyz = np.stack([C["x"], C["y"], C["z"]], 1)[keep].astype(np.float32)
    u8 = lambda x, s: np.clip(np.round(x * s), 0, 255).astype(np.uint8)
    pts = dict(n=int(keep.sum()), xyz=b64(xyz), nh=b64(C["n"][keep].astype(np.uint8)), long=b64(C["long"][keep].astype(np.uint8)),
               dmin=b64(u8(np.stack([C[f"dmin_f{f}"][keep] for f in fl]), 100)), pdist=b64(u8(np.stack([C[f"pdist_f{f}"][keep] for f in fl]), 20)))
    if BR:
        for k in ("pos", "any"): pts["ball_" + k] = b64(u8(np.stack([np.maximum(C[f"ballF_R{R:g}_{k}"][keep], 0) for R in BR]), 250))
    events.append(dict(ev=int(aux.event()), run=int(aux.run()), index=iev,
                       sed=dict(n=len(sed), xyz=b64(sed[:, :3]), e=b64(sed[:, 3])), ide=dict(n=len(ide), xyz=b64(ide[:, :3]), e=b64(ide[:, 3])), pts=pts))
    print(f"event {iev} (run {aux.run()} evt {aux.event()}): SED voxels {len(sed)}, IDE voxels {len(ide)}, points embedded {pts['n']}", flush=True)
data = dict(title=a.title or os.path.basename(a.d.rstrip("/")), vox=a.vox, fracs=[float(f) for f in fl], ballR=BR, events=events)
html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sp_display_template.html")).read().replace("__DATA__", json.dumps(data))
open(a.out, "w").write(html); print(f"wrote {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)")
