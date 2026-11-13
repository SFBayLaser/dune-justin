import numpy as np, json, sys
v=sys.argv[1]
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
n=g('n'); ev=g('ev'); evn=len(set(ev)); T=g('ballF_R1_pos')>=.05
m3=n==3; m2=n==2
key=lambda k,s:(ev[s]*1e7+g(f'gi{k}')[s])
# rank (chi2) of each 3-hit point within each of its 3 hits
ch=g('chi2')[m3]; rs=np.random.RandomState(0); x=ch+rs.rand(m3.sum())*1e-9
R=[]
for k in range(3):
    kk=key(k,m3); o=np.lexsort((x,kk)); ks=kk[o]; st=np.r_[0,np.flatnonzero(ks[1:]!=ks[:-1])+1]; cnt=np.diff(np.r_[st,len(ks)]); r=np.arange(len(ks))-np.repeat(st,cnt); rk=np.empty(len(ks),int); rk[o]=r; R.append(rk)
R=np.stack(R,1); nbest=(R==0).sum(1)
k0=key(0,m2); k1=key(1,m2); t2=T[m2]
def hits_of(sel):
    s=set()
    for k in range(3): s.update(key(k,m3)[sel].tolist())
    return s
print(v,'2-hit/ev %.0f true %.0f/ev'%(m2.sum()/evn,t2.sum()/evn))
rules=[('any 3-hit point (current)',np.ones(m3.sum(),bool)),('rank-0 in >=1 of its hits',nbest>=1),('rank-0 in >=2 hits',nbest>=2),('rank-0 in all 3 hits (mutual best)',nbest>=3),('rank<=1 in all 3 hits',(R<=1).all(1)),('rank<=2 in all 3 hits',(R<=2).all(1))]
for name,sel in rules:
    G=list(hits_of(sel)); i0=np.isin(k0,G); i1=np.isin(k1,G)
    for mode,drop in (('either',i0|i1),('both',i0&i1)):
        keep=~drop; print('  %-36s %-6s keeps %7.0f/ev (%5.2f%%) true kept %5.1f%% (%.0f/ev), precision %.2f%%'%(name,mode,keep.sum()/evn,100*keep.mean(),100*t2[keep].sum()/t2.sum(),t2[keep].sum()/evn,100*t2[keep].mean()))
print('  --- orphan competes with the best 3-hit point of each shared hit (chi2)')
c3=g('chi2')[m3]; c2=g('chi2')[m2]
best={}
for k in range(3):
    kk=key(k,m3)
    for h,cv in zip(kk.tolist(),c3.tolist()):
        if h not in best or cv<best[h]: best[h]=cv
def comp(kk):
    return np.array([best.get(h,np.inf) for h in kk.tolist()])
b0=comp(k0); b1=comp(k1)
for fac in (0.5,1.0,2.0,4.0):
    # orphan "beaten" at a hit if best3(h) <= fac*orphan chi2
    be0=b0<=fac*c2; be1=b1<=fac*c2
    for mode,drop in (('either',be0|be1),('both',(be0|~np.isfinite(b0))&(be1|~np.isfinite(b1))&(np.isfinite(b0)|np.isfinite(b1)))):
        keep=~drop; print('  beaten if best3chi2 <= %.1f x orphan chi2, %-6s keeps %7.0f/ev (%5.2f%%) true kept %5.1f%% (%.0f/ev), precision %.2f%%'%(fac,mode,keep.sum()/evn,100*keep.mean(),100*t2[keep].sum()/t2.sum(),t2[keep].sum()/evn,100*t2[keep].mean()))
