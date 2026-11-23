import pandas as pd, numpy as np, json
p=r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx'
d=pd.read_excel(p)
d=d.rename(columns={'Nano_Concentration_wt%':'cn','Soak_Time_Days':'ts','Case_ID':'case'})
d['casek']=d['case'].str.extract(r'^(Case\d)')
out={}
for ck,sub in d.groupby('casek'):
    s=sub[(sub.cn==1.0)&(sub.ts==30)].sort_values('Production_Day')
    q=s['Oil_Rate_m3_d'].values; day=s['Production_Day'].values
    # log-linear fit on days 1..60
    m=day<=60; x=np.log(day[m]); y=np.log(np.maximum(q[m],1e-9))
    A=np.vstack([x,np.ones_like(x)]).T
    coef,*_=np.linalg.lstsq(A,y,rcond=None)
    pred=A@coef; ss=1-((y-pred)**2).sum()/((y-y.mean())**2).sum()
    out[ck]={'q1':float(q[0]),'cum':float(q.sum()),'alpha':float(-coef[0]),'tau_d':float(1/(-coef[0])),'r2_loglinear_60d':float(ss)}
print(json.dumps(out,indent=1))
# additive-in-log test on day 1 across full grid
d1=d[d.Production_Day==1].copy()
X=pd.get_dummies(d1['casek'],drop_first=True).astype(float)
X['lts']=np.log(d1.ts); X['lcn']=np.log(d1.cn)
y=np.log(d1['Oil_Rate_m3_d'].values)
A=np.hstack([np.ones((len(y),1)),X.values])
coef,*_=np.linalg.lstsq(A,y,rcond=None); yh=A@coef
r2=1-((y-yh)**2).sum()/((y-y.mean())**2).sum()
print('day1 log-model R2 %.5f'%r2, 'coef',dict(zip(['const']+list(X.columns),np.round(coef,4))))
print('resid sd %.4f'%np.sqrt(((y-yh)**2).mean()))