# -*- coding: utf-8 -*-
"""A 题：cum(ts) 的两种形状谁能解释数据 —— 指数饱和 vs 平方根标度（nu=1/2）"""
import numpy as np, pandas as pd, json
p=r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx'
d=pd.read_excel(p).rename(columns={'Nano_Concentration_wt%':'cn','Soak_Time_Days':'ts','Case_ID':'case','Oil_Rate_m3_d':'q'})
d['casek']=d['case'].str.extract(r'^(Case\d)')
def ols(X,y):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]
    yh=X@b; ss=1-((y-yh)**2).sum()/((y-y.mean())**2).sum(); return b,ss
out={}
for ck,sub in d.groupby('casek'):
    for cn in (0.5,1.0,1.5):
        s=sub[sub.cn==cn].groupby('ts')['q'].sum().sort_index()
        ts=s.index.values.astype(float); cum=s.values
        # sqrt 标度：cum = A + B*sqrt(ts)
        b1,r1=ols(np.sqrt(ts),cum)
        # 指数饱和：cum = A*(1-exp(-ts/tau))，网格搜 tau
        best=(-9,None)
        for tau in np.arange(1,80,0.25):
            X=1-np.exp(-ts/tau); b,ss=ols(X,cum)
            if ss>best[0]: best=(ss,tau,b)
        # 幂律：cum = A*ts^nu
        b3,r3=ols(np.log(ts),np.log(cum))
        out['%s/cn%.1f'%(ck,cn)]={'sqrt_R2':round(float(r1),5),
            'exp_tau_d':float(best[1]),'exp_R2':round(float(best[0]),5),
            'power_nu':round(float(b3[1]),4),'power_R2':round(float(r3),5),
            'cum_ts5':float(cum[0]),'cum_ts60':float(cum[-1])}
print(json.dumps(out,ensure_ascii=False,indent=1))