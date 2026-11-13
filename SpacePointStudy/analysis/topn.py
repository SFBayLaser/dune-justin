import numpy as np, json, sys
v=sys.argv[1]
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
m0=g('n')==3; T0=g('ballF_R1_pos')>=.05; lg0=g('long')>0
rs=np.random.RandomState(0)
def rank_in_hit(sel,metric):
    ev=g('ev')[sel]; x=metric[sel]+rs.rand(sel.sum())*1e-9; out=[]
    for k in range(3):
        key=ev*1e7+g(f'gi{k}')[sel]; o=np.lexsort((x,key)); ks=key[o]
        start=np.r_[0,np.flatnonzero(ks[1:]!=ks[:-1])+1]; cnt=np.diff(np.r_[start,len(ks)])
        r=np.arange(len(ks))-np.repeat(start,cnt); rk=np.empty(len(ks),int); rk[o]=r; out.append(rk)
    return np.stack(out,1)
for lab,sel in [('normal-hit points',m0&~lg0),('all 3-hit points',m0)]:
    T=T0[sel]; ev=g('ev')[sel]; keys=[ev*1e7+g(f'gi{k}')[sel] for k in range(3)]
    nth=sum(len(np.unique(k_[T])) for k_ in keys)
    print(v,lab,'n/ev %.0f precision %.1f%% true/ev %.0f'%(sel.sum()/8,100*T.mean(),T.sum()/8))
    for name in ('dpeak','chi2'):
        R=rank_in_hit(sel,g(name))
        for n in (1,2,3,5,10):
            keep=(R<n).any(1); kt=keep&T; hr=sum(len(np.unique(k_[kt])) for k_ in keys)/nth
            print('   %-6s top-%-2d of >=1 hit: keeps %5.1f%% (%6.0f/ev), precision %5.1f%%, true kept %5.1f%%, hits covered %5.1f%%'%(name,n,100*keep.mean(),keep.sum()/8,100*kt.sum()/keep.sum(),100*kt.sum()/T.sum(),100*hr))
