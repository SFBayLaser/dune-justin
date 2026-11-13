import numpy as np, json
S='/tmp/claude-1000/-run-media-usher-Drive2-DUNE/c3075bcf-6c43-4e31-b67d-05ef4c00e29a/scratchpad/'
a=np.load(S+'base_points_prevox.npy'); c=json.load(open('baseline_b8/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]]
m=g('n')==3; f=.05
T=m&(g('ballF_R1_pos')>=f); G=m&~(g('ballF_R1_any')>=f)&(g('c_ncommon')>0); 
def auc(x,y):
    from numpy import argsort
    z=np.concatenate([x,y]); r=np.empty(len(z)); r[argsort(z,kind='mergesort')]=np.arange(1,len(z)+1)
    # ties ignored (approx); use average ranks via unique
    u,inv,cnt=np.unique(z,return_inverse=True,return_counts=True); cs=np.cumsum(cnt)-(cnt-1)/2.; r=cs[inv]
    return (r[:len(x)].sum()-len(x)*(len(x)+1)/2)/(len(x)*len(y))
sub=np.random.RandomState(1)
print('n true %d, same-particle ghost %d'%(T.sum(),G.sum()))
for k in ['long','chi2','err1_totq','err3_asym','qU','qV','qW','ampU','ampV','ampW','rmsU','rmsV','rmsW','dpeak','deg_max','deg_min','deg_mean','deg3_max','pair_max','x','y','z']:
    x=g(k)[T]; y=g(k)[G]
    xs=x[sub.choice(len(x),min(len(x),20000),replace=False)]; ys=y[sub.choice(len(y),min(len(y),20000),replace=False)]
    print('%-10s true med %9.3f  ghost med %9.3f   AUC(true>ghost) %.3f'%(k,np.median(x),np.median(y),auc(xs,ys)))
print()
d=g('deg3_max'); lg=g('long')>0
for lab,mk0 in [('all 3-hit',m),('normal only',m&~lg),('long only',m&lg)]:
    print(lab, 'n/ev %.0f precision %.1f%%'%(mk0.sum()/8,100*(T&mk0).sum()/mk0.sum()))
    for K in (3,5,10,20,50,100,1e9):
        s=mk0&(d<=K); print('   deg3_max<=%-6g keep %5.1f%% of points, %5.1f%% of true, precision %.1f%%'%(K,100*s.sum()/mk0.sum(),100*(T&s).sum()/max(1,(T&mk0).sum()),100*(T&s).sum()/max(1,s.sum())))
