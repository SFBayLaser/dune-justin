import numpy as np, json
S='/tmp/claude-1000/-run-media-usher-Drive2-DUNE/c3075bcf-6c43-4e31-b67d-05ef4c00e29a/scratchpad/'
a=np.load(S+'base_points_prevox.npy'); c=json.load(open('baseline_b8/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]]
m=g('n')==3; f=.05; lg=g('long')>0
T=m&(g('ballF_R1_pos')>=f); G=m&~(g('ballF_R1_any')>=f)&(g('c_ncommon')>0)
def auc(x,y):
    z=np.concatenate([x,y]); u,inv,cnt=np.unique(z,return_inverse=True,return_counts=True); r=(np.cumsum(cnt)-(cnt-1)/2.)[inv]
    return (r[:len(x)].sum()-len(x)*(len(x)+1)/2)/(len(x)*len(y))
rs=np.random.RandomState(1)
def sm(x): return x[rs.choice(len(x),min(len(x),15000),replace=False)]
feats=['chi2','dpeak','deg_max','deg_min','deg3_max','rmsU','rmsV','rmsW','ampU','ampV','ampW','qU','qV','qW','err3_asym']
for lab,sel in [('normal hits',~lg),('long hits',lg)]:
    t=T&sel; gg=G&sel; print(lab,'true',t.sum(),'ghost',gg.sum())
    print('  '+'  '.join('%s %.2f'%(k,auc(sm(g(k)[t]),sm(g(k)[gg]))) for k in feats))
# dpeak distribution
for lab,sel in [('normal',~lg),('long',lg)]:
    for k in ('dpeak',):
        print(lab,k,'true pct 50/90/99',np.percentile(g(k)[T&sel],[50,90,99]),'ghost',np.percentile(g(k)[G&sel],[50,90,99]))
print()
nm=m&~lg; d=g('dpeak'); dg=g('deg3_max')
print('normal-hit 3-hit points: n/ev %.0f precision %.1f%%'%(nm.sum()/8,100*(T&nm).sum()/nm.sum()))
for K in (1,2,3,4,6,8,12):
    s=nm&(d<=K); print('  dpeak<=%-3g keep %5.1f%% of points, %5.1f%% of true, precision %.1f%%'%(K,100*s.sum()/nm.sum(),100*(T&s).sum()/(T&nm).sum(),100*(T&s).sum()/s.sum()))
for K in (3,4):
  for D in (10,20,50):
    s=nm&(d<=K)&(dg<=D); print('  dpeak<=%g & deg3<=%g keep %5.1f%% pts, %5.1f%% of true, precision %.1f%%'%(K,D,100*s.sum()/nm.sum(),100*(T&s).sum()/(T&nm).sum(),100*(T&s).sum()/s.sum()))
