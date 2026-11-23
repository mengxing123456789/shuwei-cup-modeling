import json,os,math,numpy as np,xgboost as xgb
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
ROOT=r"E:\数学建模\_swc2026\SWC2026_A"
d=json.load(open(os.path.join(ROOT,"data","p4_econ.json"),encoding="utf-8"))
r2=json.load(open(os.path.join(ROOT,"models","surrogate_r2.json"),encoding="utf-8"))
def load(case):
    rows=[]
    for key,pts in d["pareto"].items():
        c,cal=key.split("|")
        if c!=case or cal not in ("geo","emp"): continue
        for p in pts:
            rows.append([math.log10(max(p["ts"],1e-6)),p["cn"],math.log10(max(p["Vinj"],1)),p["fCO2"],math.log10(max(p["qinj"],1)),
                         math.log10(max(p["EUR_m3"],1e-9)),math.log10(max(p["cost_nom"],1e-9)),p["npv"]/1e6])
    return np.array(rows,float)
out={}
for case in ["Case1","Case2","Case3"]:
    A=load(case);X,Y=A[:,:5],A[:,5:]
    p=dict(r2["cases"][case]["best_params"]);p.update(random_state=20261120,n_jobs=4,verbosity=0)
    kf=KFold(5,shuffle=True,random_state=20261120);pred=np.zeros_like(Y)
    for tr,te in kf.split(X):
        for j in range(3):
            m=xgb.XGBRegressor(**p);m.fit(X[tr],Y[tr,j]);pred[te,j]=m.predict(X[te])
    out[case]={n:round(r2_score(Y[:,j],pred[:,j]),4) for j,n in enumerate(["EUR","cost","npv"])}
print(out)
json.dump(out,open(os.path.join(ROOT,"models","surrogate_r2_eval5.json"),"w",encoding="utf-8"),indent=2)
