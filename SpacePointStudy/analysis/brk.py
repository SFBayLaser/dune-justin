import numpy as np, json, sys
for v in sys.argv[1:]:
    a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
    g=lambda k:a[:,I[k]]
    n=g('n'); lg=g('long')>0
    pos=g('ballF_R1_pos'); any_=g('ballF_R1_any'); pd=g('pdist_f0.01'); dm=g('dmin_f0.01')
    ev=len(set(g('ev')))
    print(v, 'events',ev, 'cols n unique',np.unique(n))
    m3=(n==3)
    f=0.05
    cats={}
    T=m3&(pos>=f)
    M=m3&(any_>=f)&(pos<f)
    N=m3&(any_<f)
    # within N: partial overlap (any 0..f) vs none (<=0)
    N0=N&(any_<=0)
    N1=N&(any_>0)
    tot=m3.sum()
    for nm,mk in [('true',T),('same ball, point misplaced',M),('weak overlap (0<F<0.05)',N1),('no common ball (F=0)',N0)]:
        print('  %-28s %7.0f/ev %5.1f%%  long %4.1f%%'%(nm,mk.sum()/ev,100*mk.sum()/tot,100*(mk&lg).sum()/max(mk.sum(),1)))
    print('  total 3-hit/ev',tot/ev)
