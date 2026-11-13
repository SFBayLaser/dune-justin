import numpy as np, json, sys
v=sys.argv[1]
a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
g=lambda k:a[:,I[k]].astype(np.float64)
n=g('n'); m2=n==2; ev=len(set(g('ev'))); lg=g('long')>0; vm=g('viewmask').astype(int)
T=g('ballF_R1_pos')>=.05; A=g('ballF_R1_any')>=.05
print(v,'2-hit points/ev %.0f, ball-true %.2f%% (%.0f/ev), long-hit involved %.1f%%'%(m2.sum()/ev,100*(m2&T).sum()/m2.sum(),(m2&T).sum()/ev,100*(m2&lg).sum()/m2.sum()))
print(' by view pair (viewmask 3=UV 5=UW 6=VW):')
for k,nm in ((3,'UV'),(5,'UW'),(6,'VW')):
    s=m2&(vm==k); print('   %s %7.0f/ev (%4.1f%%), true %5.2f%% , long %4.1f%%, long true %5.2f%% normal true %5.2f%%'%(nm,s.sum()/ev,100*s.sum()/m2.sum(),100*(s&T).sum()/max(s.sum(),1),100*(s&lg).sum()/max(s.sum(),1),100*(s&lg&T).sum()/max((s&lg).sum(),1),100*(s&~lg&T).sum()/max((s&~lg).sum(),1)))
print(' truth category of 2-hit points:')
nc=g('c_ncommon'); nh=g('c_nohit'); npr=g('c_npair')
cats=[('true (ball + position)',T),('same ball, misplaced',A&~T),('common particle, hits not co-located',~A&(nc>0)),('no common particle, 2 hits',(nc==0)&(nh==0)),('a hit has no particle',nh>0)]
for k,mk in cats:
    s=m2&mk; print('   %-40s %5.1f%%  long %4.1f%%'%(k,100*s.sum()/m2.sum(),100*(s&lg).sum()/max(s.sum(),1)))
print(' feature medians true vs false (2-hit): chi2 %.2f/%.2f dpeak %.2f/%.2f deg_max %.0f/%.0f'%(np.median(g('chi2')[m2&T]),np.median(g('chi2')[m2&~T]),np.median(g('dpeak')[m2&T]),np.median(g('dpeak')[m2&~T]),np.median(g('deg_max')[m2&T]),np.median(g('deg_max')[m2&~T])))
