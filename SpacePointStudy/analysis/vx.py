import numpy as np, json, sys
for v in sys.argv[1:]:
    a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
    g=lambda k:a[:,I[k]]; ev=len(set(g('ev'))); m=g('n')==3; tot=m.sum(); lg=g('long')>0
    T=m&(g('ballF_R1_pos')>=.05); vd=g('v_d'); nn=g('v_nn'); nb=g('v_nb')
    print(v,'3-hit/ev %.0f  ball-true %.1f%%'%(tot/ev,100*T.sum()/tot))
    for lab,mk in [('point within 0.3 cm of any deposit voxel',vd<=.3),('... within 0.5 cm',vd<=.5),
                   ('nearest voxel particle in >=1 of the hits (0.3)',(vd<=.3)&(nn>=1)),('... in >=2 hits',(vd<=.3)&(nn>=2)),('... in all 3 hits',(vd<=.3)&(nn>=3)),
                   ('any voxel within 0.3 has particle in all 3 hits',(vd<=.3)&(nb>=3)),('any voxel within 0.3, particle in >=2 hits',(vd<=.3)&(nb>=2))]:
        print('  %-52s %5.1f%% of points | ball-true %5.1f%% of them | ball-false in it %5.1f%% of points'%(lab,100*mk.sum()/tot,100*(mk&T).sum()/max(mk.sum(),1),100*(mk&~T).sum()/tot))
    print('  ball-true points also nearest-voxel(all 3 hits) : %.1f%%'%(100*(T&(vd<=.3)&(nn>=3)).sum()/T.sum()))
    print('  nearest voxel with distance cutoff D (particle of nearest voxel in k hits):')
    for D in (0.5,1.0,1.7):
        for k in (1,3):
            mk=m&(vd<=D)&(nn>=k); print('   D<=%.1f k>=%d : %5.1f%% of points | ball-true %5.1f%% of them | catches %5.1f%% of ball-true'%(D,k,100*mk.sum()/tot,100*(mk&T).sum()/max(mk.sum(),1),100*(mk&T).sum()/T.sum()))
    print('   no point has nearest voxel at all: %.1f%%'%(100*(m&(vd>=99)).sum()/tot))
