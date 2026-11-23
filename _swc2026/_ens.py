import json,os,math,random,numpy as np,torch,torch.nn as nn
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
import xgboost as xgb
SEED=20261120;random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED)
ROOT=r"E:\数学建模\_swc2026\SWC2026_A";DEV="cuda" if torch.cuda.is_available() else "cpu"
d=json.load(open(os.path.join(ROOT,"data","p4_econ.json"),encoding="utf-8"))
def load(case):
    rows=[]
    for key,pts in d["pareto"].items():
        c,cal=key.split("|")
        if c!=case or cal not in ("geo","emp"):continue
        for p in pts:
            rows.append([math.log10(max(p["ts"],1e-6)),p["cn"],math.log10(max(p["Vinj"],1)),p["fCO2"],math.log10(max(p["qinj"],1)),
                         math.log10(max(p["EUR_m3"],1e-9)),math.log10(max(p["cost_nom"],1e-9)),p["npv"]/1e6])
    return np.array(rows,float)
class MLP(nn.Module):
    def __init__(self):
        super().__init__();self.n=nn.Sequential(nn.Linear(5,96),nn.SiLU(),nn.Linear(96,96),nn.SiLU(),nn.Linear(96,48),nn.SiLU(),nn.Linear(48,3))
    def forward(self,x):return self.n(x)
def fit(Xtr,Ytr,Xte,ep=700):
    mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9;ym,ys=Ytr.mean(0),Ytr.std(0)+1e-9
    xt=torch.tensor((Xtr-mu)/sd,dtype=torch.float32,device=DEV);yt=torch.tensor((Ytr-ym)/ys,dtype=torch.float32,device=DEV)
    xe=torch.tensor((Xte-mu)/sd,dtype=torch.float32,device=DEV);m=MLP().to(DEV);o=torch.optim.AdamW(m.parameters(),lr=2e-3,weight_decay=1e-4);L=nn.MSELoss()
    for _ in range(ep):m.train();o.zero_grad();l=L(m(xt),yt);l.backward();o.step()
    m.eval()
    with torch.no_grad():return m(xe).cpu().numpy()*ys+ym,m,(mu,sd,ym,ys)
out={}
for case in ["Case1","Case2","Case3"]:
    A=load(case);X,Y=A[:,:5],A[:,5:];kf=KFold(5,shuffle=True,random_state=SEED)
    px=np.zeros_like(Y);pm=np.zeros_like(Y)
    for tr,te in kf.split(X):
        for j in range(3):
            m=xgb.XGBRegressor(n_estimators=400,max_depth=4,learning_rate=0.05,subsample=.9,colsample_bytree=.9,random_state=SEED,n_jobs=4,verbosity=0)
            m.fit(X[tr],Y[tr,j]);px[te,j]=m.predict(X[te])
        pm[te]=fit(X[tr],Y[tr],X[te],500)[0]
    ens=0.5*px+0.5*pm
    out[case]={n:{"xgb":round(r2_score(Y[:,j],px[:,j]),4),"mlp":round(r2_score(Y[:,j],pm[:,j]),4),"ens":round(r2_score(Y[:,j],ens[:,j]),4)} for j,n in enumerate(["EUR","cost","npv"])}
    print(case,out[case])
json.dump(out,open(os.path.join(ROOT,"models","surrogate_r3_ensemble.json"),"w",encoding="utf-8"),indent=2)
