import numpy as np, json, sys
for v in sys.argv[1:]:
    a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
    g=lambda k:a[:,I[k]]
    ev=len(set(g('ev'))); m=(g('n')==3); f=0.05
    pos=g('ballF_R1_pos'); an=g('ballF_R1_any'); nh=g('c_nohit'); nc=g('c_ncommon'); npr=g('c_npair'); nd=g('c_nd'); dx=g('c_ndx'); lg=g('long')>0
    T=m&(pos>=f); tot=m.sum()
    cats=[('true',T),
     ('same ball, misplaced',m&(an>=f)&(pos<f)),
     ('common particle, weak/no ball',m&~(an>=f)&(nc>0)),
     ('no common particle, 2 of 3 hits share one',m&(nc==0)&(nh==0)&(npr>=1)),
     ('no common particle, no pair shares',m&(nc==0)&(nh==0)&(npr==0)),
     ('>=1 hit has no particle (noise)',m&(nh>0))]
    print(v)
    for k,mk in cats: print('  %-44s %6.0f/ev %5.1f%%  long %4.1f%%'%(k,mk.sum()/ev,100*mk.sum()/tot,100*(mk&lg).sum()/max(mk.sum(),1)))
    print('  sum check',sum(mk.sum() for _,mk in cats)/tot)
    s=T&(nd<0.5); print('  true: signed dx (point - nearest deposit) mean %.3f median %.3f rms %.3f cm, n=%d'%(dx[s].mean(),np.median(dx[s]),dx[s].std(),s.sum()))
    s=m&(nc>0)&(nd<99); print('  all 3-hit w/ common particle: median nearest dist %.2f cm; frac>2cm %.1f%%'%(np.median(nd[s]),100*(nd[s]>2).mean()))
