import numpy as np, json, sys, re
for v in sys.argv[1:]:
    a=np.load(v+'/points.npy'); c=json.load(open(v+'/points_cols.json')); I={k:i for i,k in enumerate(c)}
    g=lambda k:a[:,I[k]]; m=g('n')==3; T=g('ballF_R1_pos')>=.05; lg=g('long')>0; cov={}
    for l in open(v+'/ball_recall.txt'):
        w=l.split()
        if len(w)>8 and w[0]=='1' and w[1]=='0.05' and w[2] in('all','normal'): cov[w[2]]=w[8:11]
    n2=(g('n')==2); t2=(g('ballF_R1_pos')>=.05)&n2
    print('%-22s 3hit/ev %6.0f true/ev %5.0f prec %4.1f%% | normal 3hit/ev %6.0f prec %4.1f%% | 2hit/ev %5.0f | site cov all %s normal %s'%(v,m.sum()/8,(m&T).sum()/8,100*(m&T).sum()/m.sum(),(m&~lg).sum()/8,100*(m&~lg&T).sum()/(m&~lg).sum(),n2.sum()/8,cov['all'][0],cov['normal'][0]))
