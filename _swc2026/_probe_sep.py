import pandas as pd, numpy as np
p=r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx'
d=pd.read_excel(p)
print(d.shape, list(d.columns))
dcrec=[c for c in d.columns if 'Nano' in c][0]; drec=[c for c in d.columns if 'Soak' in c][0]
dcase=[c for c in d.columns if 'Case' in c][0]
def piv(day=1):
    s=d[d['Production_Day']==day].pivot_table(index=[dcase,dcrec],columns=dcrec,values='Oil_Rate_m3_d')
# normalize each trajectory by its day1 value, then compare shapes
g=d.groupby([dcase,dcrec,drec])
med={}
for k,sub in g:
    sub=sub.sort_values('Production_Day'); q=sub['Oil_Rate_m3_d'].values
    med[k]=q/ q[0]
shapes=np.array([v for v in med.values()])
print('shape spread (std/mean) at days 1,30,90,180,360:')
for idx in [0,29,89,179,359]:
    col=shapes[:,idx]; print(' day',idx+1,'mean %.4f cv %.4f'%(col.mean(), col.std()/max(col.mean(),1e-9)))
# ratio across cases at fixed cn,ts
for cn in [0.5,1.0,1.5]:
    for ts in [5,30,60]:
        try:
            a=med[(1 if False else 'Case1',0.5,5)]
        except Exception: pass
print()
# case-level daily-rate ratio: use total cum / cum
cum=d.groupby([dcase,dcrec,drec])['Oil_Rate_m3_d'].sum().unstack(0)
print('sum q by case (cn,ts grid), head:')
print(cum.head(4).round(2))
r=np.log(cum['Case3']/cum['Case1'])
print('log ratio Case3/Case1: mean %.4f std %.4f n=%d'%(r.mean(),r.std(),r.size))