# Endpoint dz (reco - true, cm) for the Reco_Eff "good reco" population,
# legacy vs Cluster3D, using EndPos (as Reco_Eff does), the most downstream
# track hit, and the last Kalman node.
import ROOT, sys, json
import numpy as np
files=[l.strip() for l in open(sys.argv[1]) if l.strip()]
LS=(-3478.48,-2166.71,4179.24); LE=(3478.48,829.282,9135.88)
def larstart(p): return all(LS[i]<=p[i]<=LE[i] for i in range(3))
out={}
for tag,rt,tt in [("legacy","Reco_Tree","Truth_Info"),("cluster3d","Reco_Tree_C3D","Truth_Info_C3D")]:
    r=ROOT.TChain(rt); t=ROOT.TChain(tt)
    for f in files: r.Add(f); t.Add(f)
    r.AddFriend(t)
    rows=[]
    seen=set(); lastfile=None
    for e in range(r.GetEntries()):
        r.GetEntry(e)
        # fingerprint set is per spill in Reco_Eff; approximate by per (file,spill)
        seen=set()
        groups={}
        for jt in range(r.nTracks):
            pj=t.RecoTrackPrimaryParticlePDG[jt]
            fj=(pj,)+tuple(round(t.RecoTrackPrimaryParticleTrueMomentum[jt*4+d]*1000) for d in range(4))+tuple(round(t.RecoTrackPrimaryParticleTruePositionStart[jt*4+d]*1000) for d in range(4))
            groups.setdefault(fj,[]).append((r.EndPos[jt*4+2],r.StartPos[jt*4+2],r.nHits[jt]))
        n=r.nTracks
        for it in range(n):
            pdg=t.RecoTrackPrimaryParticlePDG[it]
            fp=(pdg,)+tuple(round(t.RecoTrackPrimaryParticleTrueMomentum[it*4+d]*1000) for d in range(4))+tuple(round(t.RecoTrackPrimaryParticleTruePositionStart[it*4+d]*1000) for d in range(4))
            dbl = fp in seen; seen.add(fp)
            if abs(pdg)!=13 or dbl: continue
            if t.RecoTrackPrimaryParticleTrueVisibleEnergy[it] < 0: continue
            ps=t.RecoTrackPrimaryParticleTruePositionStart
            if not larstart([ps[it*4],ps[it*4+1],ps[it*4+2]]) or not t.RecoTrackPrimaryParticleTMSFiducialEnd[it]: continue
            tz=t.RecoTrackPrimaryParticleTruePositionEnd[it*4+2]
            ez=r.EndPos[it*4+2]
            nh=r.nHits[it]; hz=max(r.TrackHitPos[(it*200+j)*4+2] for j in range(nh)) if nh>0 else float('nan')
            nk=r.nKalmanNodes[it]; kz=max(r.KalmanPos[(it*200)*3+2],r.KalmanPos[(it*200+nk-1)*3+2]) if nk>0 else float('nan')
            q=r.Charge[it]; tq=-1 if pdg<0 else 1
            ke=t.RecoTrackPrimaryParticleTrueMomentumEnteringTMS[it*4+3]/1000.
            g=groups[fp]; rows.append(((ez-tz)/10.,(hz-tz)/10.,(kz-tz)/10.,int(q*tq>0),ke,tz/10.,ez/10.,len(g),(max(x[0] for x in g)-tz)/10.,nh,r.StartPos[it*4+2]/10.,e))
    a=np.array(rows)
    out[tag]=a
    np.save(sys.argv[2]+f"/dz_{tag}.npy",a)
    dz=a[:,0]; ok=(dz>-30)&(dz<0)
    print(tag,"N",len(a),"charge ok %.3f"%a[:,3].mean(),"end ok %.3f"%ok.mean(),"good %.3f"%(ok&(a[:,3]==1)).mean())
    for nm,c in [("EndPos",0),("maxHitZ",1),("KalmanEnd",2)]:
        d=a[:,c]; d=d[np.isfinite(d)]
        print("  %-9s median %6.1f  <-30: %.3f  [-30,0]: %.3f  >=0: %.3f"%(nm,np.median(d),(d<=-30).mean(),((d>-30)&(d<0)).mean(),(d>=0).mean()))

    short=a[:,0]<=-30
    print("  short(<=-30):",short.sum(),"of which multi-track same particle:",(a[short,7]>1).sum(),
          " best-of-group within [-30,0]:",((a[short,8]>-30)&(a[short,8]<0)).sum(), " median nHits short/all: %.0f/%.0f"%(np.median(a[short,9]),np.median(a[:,9])))
    print("  short: median true-end z %.0f, reco-end z %.0f; ke median %.2f vs all %.2f"%(np.median(a[short,5]),np.median(a[short,6]),np.median(a[short,4]),np.median(a[:,4])))
    h,edges=np.histogram(a[short,0],bins=[-400,-200,-100,-60,-30]); print("  short dz hist",list(zip(edges[:-1].tolist(),h.tolist())))
