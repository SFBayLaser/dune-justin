import numpy as np, json, sys
v=sys.argv[1]; view=int(sys.argv[2]) if len(sys.argv)>2 else 2
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
m=g('n')==3; f=.05
T=(g('ballF_R1_pos')>=f); lg=g('long')>0
amp=np.stack([g('ampU'),g('ampV'),g('ampW')],1); q=np.stack([g('qU'),g('qV'),g('qW')],1)
la=np.log(np.clip(amp,1e-3,None)); lq=np.log(np.clip(q,1e-3,None))
M={'dpeak':g('dpeak'),'chi2':g('chi2'),'|err3_asym|':np.abs(g('err3_asym')),
   'amp spread (std log amp)':la.std(1),'charge spread (std log q)':lq.std(1),
   '|log ampU/ampW|':np.abs(la[:,0]-la[:,2]),'|log ampV/ampW|':np.abs(la[:,1]-la[:,2]),'|log qU/qW|':np.abs(lq[:,0]-lq[:,2]),'|log qV/qW|':np.abs(lq[:,1]-lq[:,2]),
   'rms spread':np.stack([g('rmsU'),g('rmsV'),g('rmsW')],1).std(1)}
rs=np.random.RandomState(0)
for sel_name,sel in [('normal-hit points',m&~lg),('all 3-hit points',m)]:
    ev=g('ev')[sel]; h=g(f'gi{view}')[sel]; t=T[sel]
    key=ev*1e7+h; u,inv=np.unique(key,return_inverse=True); size=np.bincount(inv); nt=np.bincount(inv,weights=t)
    ok=(size>=2)&(nt>=1)&(nt<size); frac=nt[ok]/size[ok]
    print(f'{v} view {view} hit contests, {sel_name}: hits in >=2 points {int((size>=2).sum())}, with a true point {int(((size>=2)&(nt>=1)).sum())}, contested (true and false both present) {int(ok.sum())}; mean group size {size[ok].mean():.1f}; random pick correct {100*frac.mean():.1f}%')
    for k,x in M.items():
        xs=x[sel]+rs.rand(sel.sum())*1e-9; o=np.lexsort((xs,inv)); first=np.r_[True,inv[o][1:]!=inv[o][:-1]]
        pick=t[o][first]; gid=inv[o][first]; res=pick[ok[gid]]
        print('   %-26s lowest value picks a true point in %5.1f%% of contested hits'%(k,100*res.mean()))
