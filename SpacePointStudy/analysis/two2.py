import numpy as np, json, sys
v=sys.argv[1]
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
n=g('n'); ev=g('ev'); evn=len(set(ev)); lg=g('long')>0; T=g('ballF_R1_pos')>=.05
m3=n==3; m2=n==2
key=lambda k,s:(ev[s]*1e7+g(f'gi{k}')[s])
# hits that sit in any 3-hit point, and in a TRUE 3-hit point
h3=set(); h3t=set()
for k in range(3):
    h3.update(key(k,m3).tolist()); h3t.update(key(k,m3&T).tolist())
# 2-hit rows: hits are gi0,gi1 (views ascending), gi2=-1
k0=key(0,m2); k1=key(1,m2)
in3=np.isin(k0,list(h3))|np.isin(k1,list(h3)); both3=np.isin(k0,list(h3))&np.isin(k1,list(h3)); in3t=np.isin(k0,list(h3t))|np.isin(k1,list(h3t))
t2=T[m2]
print(v,'2-hit/ev %.0f; true %.0f/ev'%(m2.sum()/evn,t2.sum()/evn))
for lab,s in (('a hit is in some 3-hit point',in3),('both hits are in 3-hit points',both3),('a hit is in a TRUE 3-hit point',in3t)):
    print('  %-34s all 2-hit: %5.1f%% | of true 2-hit: %5.1f%% | precision inside %.2f%%, outside %.2f%%'%(lab,100*s.mean(),100*s[t2].mean(),100*t2[s].mean(),100*t2[~s].mean()))
# among the 2-hit points with NO hit in a 3-hit point: rank within hit by chi2 / dpeak
free=~in3; idx=np.flatnonzero(m2)[free]
tf=T[idx]; print('  free 2-hit points (neither hit in any 3-hit point): %.0f/ev, true %.0f/ev (%.2f%%), long %.1f%%'%(len(idx)/evn,tf.sum()/evn,100*tf.mean(),100*lg[idx].mean()))
rs=np.random.RandomState(0)
for name in ('chi2','dpeak'):
    x=g(name)[idx]+rs.rand(len(idx))*1e-9
    R=[]
    for k in (0,1):
        kk=key(k,m2)[free]; o=np.lexsort((x,kk)); ks=kk[o]; st=np.r_[0,np.flatnonzero(ks[1:]!=ks[:-1])+1]; cnt=np.diff(np.r_[st,len(ks)]); r=np.arange(len(ks))-np.repeat(st,cnt); rk=np.empty(len(ks),int); rk[o]=r; R.append(rk)
    R=np.stack(R,1)
    ht=set(); 
    for k in (0,1): ht.update(key(k,m2)[free][tf].tolist())
    for nn in (1,2,3,5,10):
        keep=(R<nn).any(1); kt=keep&tf
        hc=len(set(np.concatenate([key(k,m2)[free][kt] for k in (0,1)]).tolist()))/max(len(ht),1)
        print('   %-5s top-%-2d of >=1 hit: keeps %5.1f%% (%6.0f/ev), precision %.2f%%, true kept %5.1f%%, hits of true 2-hit pts covered %5.1f%%'%(name,nn,100*keep.mean(),keep.sum()/evn,100*kt.sum()/max(keep.sum(),1),100*kt.sum()/max(tf.sum(),1),100*hc))
