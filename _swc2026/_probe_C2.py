# -*- coding: utf-8 -*-
"""C 题 P2 信号探针：腕点 3D 位置，hold-last vs 常速外推（同一掩码窗口）"""
import os, numpy as np, pandas as pd
root=r'E:\数学建模\_swc2026\cdata\EgoDemo'
recs=sorted(os.listdir(root))[:8]
def load(r):
    f=os.path.join(root,r,'data','chunk-000','file-000.parquet')
    d=pd.read_parquet(f); out={}
    for side in ('left','right'):
        col='observation.state.hand_%s_world'%side
        v=d[col].values
        A=np.array([[np.asarray(p,dtype=np.float64) for p in row] for row in v])  # (n,21,3)
        out[side]=A
    return d, out
rows=[]
for r in recs:
    try: d,H=load(r)
    except Exception as e: print(r,'ERR',e); continue
    n=len(d)
    print(r,'n=%d shape=%s'%(n,H['left'].shape))
    for side in ('left','right'):
        P=H[side][:,0,:]
        for gap in (6,12,18):
            for start in range(6, n-gap-2, max(1,(n-gap)//60)):
                g0,g1=start,start+gap
                if g1>=n-1: continue
                truth=P[g1]; hold=P[g0-1]; vv=(P[g0-1]-P[g0-3])/2.0; lin=P[g0-1]+vv*(gap+1)
                rows.append({'rec':r,'side':side,'gap':gap,
                             'e_hold':float(np.linalg.norm(truth-hold)),
                             'e_lin':float(np.linalg.norm(truth-lin))})
df=pd.DataFrame(rows)
g=df.groupby('gap').agg(n=('e_hold','size'),hold_med=('e_hold','median'),lin_med=('e_lin','median'))
g['improve_%']=(100*(1-g.lin_med/g.hold_med)).round(1)
print(); print(g.round(4).to_string())
print(); print('gap=12 p90: hold %.4f  lin %.4f'%(df[df.gap==12].e_hold.quantile(.9), df[df.gap==12].e_lin.quantile(.9)))
df.to_csv(r'E:\数学建模\_swc2026\_probe_C2.csv',index=False)