# Muon-by-muon: which fiducial (LAr-start, TMS-end) muons each reconstruction
# finds, keyed by the same truth fingerprint Reco_Eff uses, per slice.
import ROOT, sys, json
files=[l.strip() for l in open(sys.argv[1]) if l.strip()]
LS=(-3478.48,-2166.71,4179.24); LE=(3478.48,829.282,9135.88)
def found(rt,tt):
    r=ROOT.TChain(rt); t=ROOT.TChain(tt)
    for f in files: r.Add(f); t.Add(f)
    out={}
    for e in range(r.GetEntries()):
        r.GetEntry(e); t.GetEntry(e)
        for it in range(r.nTracks):
            pdg=t.RecoTrackPrimaryParticlePDG[it]
            if abs(pdg)!=13: continue
            ps=t.RecoTrackPrimaryParticleTruePositionStart
            if not all(LS[i]<=ps[it*4+i]<=LE[i] for i in range(3)): continue
            if not t.RecoTrackPrimaryParticleTMSFiducialEnd[it]: continue
            ke=t.RecoTrackPrimaryParticleTrueMomentumEnteringTMS[it*4+3]/1000.
            if not (0<=ke<5): continue
            key=(pdg,)+tuple(round(t.RecoTrackPrimaryParticleTrueMomentum[it*4+d]*1000) for d in range(4))+tuple(round(ps[it*4+d]*1000) for d in range(4))
            out.setdefault((e,key),ke)
    return out
L=found("Reco_Tree","Truth_Info"); C=found("Reco_Tree_C3D","Truth_Info_C3D")
both=set(L)&set(C); lo=set(L)-set(C); co=set(C)-set(L)
res=dict(legacy=len(L),cluster3d=len(C),both=len(both),legacy_only=len(lo),c3d_only=len(co))
B=[0.0,0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.25,2.5,2.75,3.0,3.5,4.0,4.5,5.0]
import bisect
def hist(keys,src): 
    h=[0]*16
    for k in keys: h[bisect.bisect_right(B,src[k])-1]+=1
    return h
res["legacy_only_ke"]=hist(lo,L); res["c3d_only_ke"]=hist(co,C)
print(json.dumps(res)); json.dump(res,open(sys.argv[2],"w"))
