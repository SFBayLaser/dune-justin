#!/usr/bin/env python3
"""Flat tuples for the single-muon TMS field studies.

usage: muon_tuple.py <edep.root> <RecoCandidates.root> <out_tuple.root> [--meta KEY=VALUE ...]

Each --meta is stored in the output as a TNamed called meta_<KEY> (title = VALUE): which field the reco used, the map
checksum, the dune-tms build and so on, so a tuple says how it was made.

Writes two trees:
  events  one row per muon thrown (every edep-sim event, reconstructed or not): the truth from edep-sim plus the
          best matching reco track (most hits). This is what tracking efficiency, charge-sign correctness and
          momentum resolution are made from.
  tracks  one row per reco track (all slices), keyed by the same event number, for duplicate and fake counts.

Reco events are joined to edep-sim events through SpillNo (the input event number; EventNo is the slice index).

Reco momentum is Reco_Tree_C3D.Momentum: it is the Kalman curvature fit only when the reco ran with
[Recon.Cluster3D] MomentumFromRange = false. reco_p_range comes from EnergyRange, the kinetic energy estimated from
the track length, so the two can be compared for tracks that stop.

Units: mm, MeV, MeV/c. Charge is -1 for mu- and +1 for mu+ (reco: from the 13 / -13 PDG-style code).
"""
import math
import sys
from array import array

import ROOT

MU_MASS = 105.658
Z_TMS_FRONT = 11100.0       # mm, where "entering the TMS" is taken from the truth trajectory
# Bar region of the surveyed CLEAN_NEW_GEOMETRY TMS (the "Bar-region bounding box" line of the reco log) and the margins
# Cluster3D uses (RangeContainmentMarginXY/Z) to decide a track stops inside. Set these to match the geometry and config.
BAR_LO = (-3501.0, -3102.23, 11104.5)
BAR_HI = (3501.0, 397.77, 18510.5)
CONTAIN_XY_MM = 100.0
CONTAIN_Z_MM = 100.0
EXIT_DIST_MM = 300.0        # a muon whose trajectory goes on this far past its last TMS hit has left the TMS

ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libedepsim_io")


class Row:
    """A tree whose branches are single numbers set by name."""

    def __init__(self, name, spec):
        self.tree = ROOT.TTree(name, name)
        self.val = {}
        for key, kind in spec:
            self.val[key] = array({"I": "i", "F": "f", "O": "b"}[kind], [0])
            self.tree.Branch(key, self.val[key], key + "/" + kind)
        self.defaults = {key: (0 if kind in "IO" else -999.0) for key, kind in spec}

    def reset(self):
        for key, d in self.defaults.items():
            self.val[key][0] = d

    def set(self, **kw):
        for key, v in kw.items():
            self.val[key][0] = v

    def fill(self):
        self.tree.Fill()


def p_from_ke(ke):
    return math.sqrt(max(0.0, (ke + MU_MASS) ** 2 - MU_MASS ** 2))


def triple(arr, i):
    """Track i of a per-track 3-vector branch (flat, stride 3)."""
    v = list(arr)
    return (v[3 * i], v[3 * i + 1], v[3 * i + 2]) if len(v) >= 3 * (i + 1) else (-999.0, -999.0, -999.0)


def four(arr, i):
    v = list(arr)
    return v[4 * i:4 * i + 4] if len(v) >= 4 * (i + 1) else [-999.0] * 4


def read_truth(edep_path):
    fe = ROOT.TFile.Open(edep_path)
    te = fe.Get("EDepSimEvents")
    ev = ROOT.TG4Event()
    te.SetBranchAddress("Event", ev)
    truth = []
    for i in range(te.GetEntries()):
        te.GetEntry(i)
        prim = [t for t in ev.Trajectories if t.GetParentId() == -1]
        if not prim:
            truth.append(None)
            continue
        traj = prim[0]
        pts = list(traj.Points)
        p0 = traj.GetInitialMomentum()
        first, last = pts[0], pts[-1]
        enter = next((p for p in pts if p.GetPosition().Z() >= Z_TMS_FRONT), None)
        p_last = last.GetMomentum().Mag()
        ke_end = math.sqrt(p_last ** 2 + MU_MASS ** 2) - MU_MASS
        nseg = 0
        zlo, zhi, edep = 1e9, -1e9, 0.0
        last_seg = None
        for kv in ev.SegmentDetectors:
            if str(kv.first) != "volTMS":
                continue
            for s in kv.second:
                nseg += 1
                zlo = min(zlo, s.GetStart().Z(), s.GetStop().Z())
                zhi = max(zhi, s.GetStart().Z(), s.GetStop().Z())
                if last_seg is None or s.GetStop().Z() > last_seg[2]:
                    last_seg = (s.GetStop().X(), s.GetStop().Y(), s.GetStop().Z())
                edep += s.GetEnergyDeposit()
        # Did the muon leave the TMS? Compare where its trajectory ends with its deepest TMS hit: a muon that stops
        # inside ends within a bar or so of its last hit, one that leaves goes on (it may still stop in the rock).
        dist_after, p_exit = -999.0, -999.0
        if last_seg is not None:
            def gap(p):
                return math.sqrt((p.GetPosition().X() - last_seg[0]) ** 2 + (p.GetPosition().Y() - last_seg[1]) ** 2 +
                                 (p.GetPosition().Z() - last_seg[2]) ** 2)
            dist_after = gap(last)
            p_exit = min(pts, key=gap).GetMomentum().Mag()
        truth.append(dict(
            pdg=traj.GetPDGCode(), p0=math.sqrt(p0.X() ** 2 + p0.Y() ** 2 + p0.Z() ** 2), ke0=p0.E() - MU_MASS,
            x0=first.GetPosition().X(), y0=first.GetPosition().Y(), z0=first.GetPosition().Z(),
            dxdz0=p0.X() / p0.Z() if p0.Z() else 0.0, dydz0=p0.Y() / p0.Z() if p0.Z() else 0.0,
            p_enter=enter.GetMomentum().Mag() if enter else -999.0,
            xe=last.GetPosition().X(), ye=last.GetPosition().Y(), ze=last.GetPosition().Z(), ke_end=ke_end,
            dist_after=dist_after, p_exit=p_exit,
            nseg=nseg, zlo=zlo if nseg else -999.0, zhi=zhi if nseg else -999.0, edep=edep))
    return truth


def read_reco(reco_path):
    """All reco tracks, grouped by SpillNo (= edep event number)."""
    f = ROOT.TFile.Open(reco_path)
    r = f.Get("Reco_Tree_C3D")
    r.AddFriend(f.Get("Truth_Info_C3D"))
    by_event = {}
    for e in r:
        n = int(e.nTracks)
        for i in range(n):
            ps, pe = triple(e.StartPos, i), triple(e.EndPos, i)
            ds, de = triple(e.StartDirection, i), triple(e.EndDirection, i)
            tm, tp = four(e.RecoTrackPrimaryParticleTrueMomentumEnteringTMS, i), four(e.RecoTrackPrimaryParticleTruePositionEnteringTMS, i)
            ke_range = float(e.EnergyRange[i])
            tr = dict(
                slice=int(e.EventNo), nslice_tracks=n, nhits=int(e.nHits[i]), p=float(e.Momentum[i]),
                q=-1 if int(e.Charge_Kalman[i]) == 13 else 1,
                q_curv=-1 if int(e.Charge_Kalman_curvature[i]) == 13 else 1,
                ke_range=ke_range, p_range=p_from_ke(ke_range) if ke_range > 0 else -999.0,
                length=float(e.Length[i]), chi2=float(e.Chi2[i]), ndof=int(e.NDoF[i]),
                xs=ps[0], ys=ps[1], zs=ps[2], xe=pe[0], ye=pe[1], ze=pe[2],
                dxdzs=ds[0] / ds[2] if ds[2] not in (0.0, -999.0) else -999.0,
                dxdze=de[0] / de[2] if de[2] not in (0.0, -999.0) else -999.0,
                pdg=int(e.RecoTrackPrimaryParticlePDG[i]) if len(e.RecoTrackPrimaryParticlePDG) > i else 0,
                stops_inside=int(BAR_LO[0] + CONTAIN_XY_MM < pe[0] < BAR_HI[0] - CONTAIN_XY_MM and
                                 BAR_LO[1] + CONTAIN_XY_MM < pe[1] < BAR_HI[1] - CONTAIN_XY_MM and
                                 pe[2] < BAR_HI[2] - CONTAIN_Z_MM),
                true_p_enter=math.sqrt(tm[0] ** 2 + tm[1] ** 2 + tm[2] ** 2) if tm[0] != -999.0 else -999.0,
                true_x_enter=tp[0])
            by_event.setdefault(int(e.SpillNo), []).append(tr)
    return by_event


def main(edep_path, reco_path, out_path, meta=()):
    truth = read_truth(edep_path)
    reco = read_reco(reco_path)

    out = ROOT.TFile(out_path, "RECREATE")
    ev_keys = [("event", "I"), ("true_pdg", "I"), ("true_q", "I"), ("true_p0", "F"), ("true_ke0", "F"),
               ("true_x0", "F"), ("true_y0", "F"), ("true_z0", "F"), ("true_dxdz0", "F"), ("true_dydz0", "F"),
               ("true_p_enter", "F"), ("true_xend", "F"), ("true_yend", "F"), ("true_zend", "F"), ("true_ke_end", "F"),
               ("true_dist_after_tms", "F"), ("true_p_exit", "F"), ("true_exits_tms", "O"), ("true_nseg_tms", "I"), ("true_zlo_tms", "F"), ("true_zhi_tms", "F"),
               ("true_edep_tms", "F"),
               ("n_slices", "I"), ("n_tracks", "I"), ("found", "O")]
    trk_keys = [("nhits", "I"), ("p", "F"), ("q", "I"), ("q_curv", "I"), ("ke_range", "F"), ("p_range", "F"),
                ("length", "F"), ("chi2", "F"), ("ndof", "I"), ("xs", "F"), ("ys", "F"), ("zs", "F"), ("xe", "F"),
                ("ye", "F"), ("ze", "F"), ("dxdzs", "F"), ("dxdze", "F"), ("pdg", "I"), ("stops_inside", "O"), ("true_p_enter", "F"),
                ("true_x_enter", "F")]
    events = Row("events", ev_keys + [("reco_" + k, t) for k, t in trk_keys])
    tracks = Row("tracks", [("event", "I"), ("slice", "I"), ("rank", "I")] + [("reco_" + k, t) for k, t in trk_keys])

    for i, t in enumerate(truth):
        events.reset()
        events.set(event=i)
        if t is not None:
            events.set(true_pdg=t["pdg"], true_q=-1 if t["pdg"] == 13 else 1, true_p0=t["p0"], true_ke0=t["ke0"],
                       true_x0=t["x0"], true_y0=t["y0"], true_z0=t["z0"], true_dxdz0=t["dxdz0"], true_dydz0=t["dydz0"],
                       true_p_enter=t["p_enter"], true_xend=t["xe"], true_yend=t["ye"], true_zend=t["ze"],
                       true_ke_end=t["ke_end"], true_dist_after_tms=t["dist_after"], true_p_exit=t["p_exit"],
                       true_exits_tms=int(t["dist_after"] > EXIT_DIST_MM), true_nseg_tms=t["nseg"],
                       true_zlo_tms=t["zlo"], true_zhi_tms=t["zhi"], true_edep_tms=t["edep"])
        trs = sorted(reco.get(i, []), key=lambda r: -r["nhits"])
        events.set(n_slices=len({r["slice"] for r in trs}), n_tracks=len(trs), found=int(bool(trs)))
        if trs:
            b = trs[0]
            events.set(**{"reco_" + k: b[k] for k, _ in trk_keys})
        events.fill()
        for rank, r in enumerate(trs):
            tracks.reset()
            tracks.set(event=i, slice=r["slice"], rank=rank,
                       **{"reco_" + k: r[k] for k, _ in trk_keys})
            tracks.fill()

    out.cd()
    for key, value in meta:
        ROOT.TNamed("meta_" + key, value).Write()
    events.tree.Write()
    tracks.tree.Write()
    out.Close()
    print("wrote %s: %d events, %d with a reco track, %d reco tracks" %
          (out_path, len(truth), sum(1 for i in range(len(truth)) if reco.get(i)), sum(len(v) for v in reco.values())))


if __name__ == "__main__":
    args = sys.argv[1:]
    meta = []
    while "--meta" in args:
        i = args.index("--meta")
        if i + 1 >= len(args) or "=" not in args[i + 1]:
            sys.exit(__doc__)
        meta.append(tuple(args[i + 1].split("=", 1)))
        del args[i:i + 2]
    if len(args) != 3:
        sys.exit(__doc__)
    main(*args, meta=meta)
