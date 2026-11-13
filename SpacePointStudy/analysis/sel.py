import numpy as np, json, sys
v=sys.argv[1]
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
m0=g('n')==3; T0=g('ballF_R1_pos')>=.05; lg0=g('long')>0
rs=np.random.RandomState(0)
def best_flags(sel,metric):
    """for each selected point and view: is it the lowest-metric point of its hit?"""
    ev=g('ev')[sel]; x=metric[sel]+rs.rand(sel.sum())*1e-9; out=[]
    for k in range(3):
        key=ev*1e7+g(f'gi{k}')[sel]; u,inv=np.unique(key,return_inverse=True)
        mn=np.full(len(u),np.inf); np.minimum.at(mn,inv,x); out.append(x<=mn[inv])
    return np.stack(out,1)
for lab,sel0 in [('normal-hit points',m0&~lg0),('all 3-hit points',m0)]:
    sel=sel0; T=T0[sel]; ev=g('ev')[sel]
    thits=set(); 
    keys=[ev*1e7+g(f'gi{k}')[sel] for k in range(3)]
    ntrue_hits=sum(len(np.unique(k_[T])) for k_ in keys)
    print(v,lab,'n/ev %.0f, precision %.1f%%, true/ev %.0f'%(sel.sum()/8,100*T.mean(),T.sum()/8))
    for name,met in [('dpeak',g('dpeak')),('chi2',g('chi2')),('dpeak+chi2 rank sum',None)]:
        if met is None:
            def rk(x): 
                r=np.empty(len(x)); r[np.argsort(x)]=np.arange(len(x)); return r/len(x)
            met=np.zeros(len(a)); met[sel]=rk(g('dpeak')[sel])+rk(g('chi2')[sel])
        F=best_flags(sel,met)
        for rule,keep in [('best of its W hit',F[:,2]),('best for >=1 hit',F.any(1)),('best for >=2 hits',F.sum(1)>=2),('best for all 3 hits',F.all(1))]:
            kt=keep&T
            hr=sum(len(np.unique(k_[kt])) for k_ in keys)/ntrue_hits
            print('   %-20s %-22s keeps %5.1f%% of points, precision %5.1f%%, true points kept %5.1f%%, hits-of-true-points still covered %5.1f%%'%(name,rule,100*keep.mean(),100*kt.sum()/keep.sum(),100*kt.sum()/T.sum(),100*hr))
