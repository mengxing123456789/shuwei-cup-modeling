"""Train surrogate models on the Pareto design data (A problem).

Inputs : data/p4_econ.json -> pareto["Case|geo"] and ["Case|emp"]
Targets: EUR_m3, cost_nom, npv
Models : XGBoost (CPU) and a 3-layer MLP (torch, CUDA when available)
Metrics: R2 / RMSE / MAPE on 5-fold KFold and leave-one-case-out GroupKFold
Outputs: models/surrogate_r0.json, models/surrogate_xgb_*.json, models/surrogate_mlp.pt
"""
import json, os, math, random, time
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import KFold, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import xgboost as xgb

SEED = 20261120
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "p4_econ.json")
OUT = os.path.join(ROOT, "models")
os.makedirs(OUT, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"

def load():
    d = json.load(open(DATA, encoding="utf-8"))
    rows = []
    for key, pts in d["pareto"].items():
        case, cal = key.split("|")
        if cal not in ("geo", "emp"):
            continue
        for p in pts:
            rows.append(dict(case=case, cal=cal, ts=p["ts"], cn=p["cn"], Vinj=p["Vinj"],
                             fCO2=p["fCO2"], qinj=p["qinj"], EUR=p["EUR_m3"],
                             cost=p["cost_nom"], npv=p["npv"]))
    return rows

def featurize(rows):
    cases = sorted({r["case"] for r in rows})
    cidx = {c: i for i, c in enumerate(cases)}
    X, G, Y = [], [], []
    for r in rows:
        oh = [0.0] * len(cases); oh[cidx[r["case"]]] = 1.0
        X.append(oh + [math.log10(max(r["ts"], 1e-6)), r["cn"], math.log10(max(r["Vinj"], 1)),
                       r["fCO2"], math.log10(max(r["qinj"], 1))])
        G.append(r["case"])
        Y.append([math.log10(max(r["EUR"], 1e-9)), math.log10(max(r["cost"], 1e-9)), r["npv"] / 1e6])
    return np.array(X, float), np.array(G), np.array(Y, float)

class MLP(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, 128), nn.SiLU(), nn.Dropout(0.05),
            nn.Linear(128, 128), nn.SiLU(), nn.Dropout(0.05),
            nn.Linear(128, 64), nn.SiLU(), nn.Linear(64, d_out))
    def forward(self, x): return self.net(x)

def train_mlp(Xtr, Ytr, Xte, epochs=800):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    ym, ys = Ytr.mean(0), Ytr.std(0) + 1e-9
    xtr = torch.tensor((Xtr - mu) / sd, dtype=torch.float32, device=DEV)
    ytr = torch.tensor((Ytr - ym) / ys, dtype=torch.float32, device=DEV)
    xte = torch.tensor((Xte - mu) / sd, dtype=torch.float32, device=DEV)
    model = MLP(Xtr.shape[1], Ytr.shape[1]).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    lossf = nn.MSELoss()
    for ep in range(epochs):
        model.train(); opt.zero_grad()
        loss = lossf(model(xtr), ytr); loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(xte).cpu().numpy() * ys + ym
    return pred, model, (mu, sd, ym, ys)

def metrics(y, p):
    out = {}
    for j, name in enumerate(["EUR", "cost", "npv"]):
        out[name] = dict(r2=float(r2_score(y[:, j], p[:, j])),
                         rmse=float(np.sqrt(mean_squared_error(y[:, j], p[:, j]))),
                         mape=float(np.mean(np.abs((y[:, j] - p[:, j]) / np.where(np.abs(y[:, j]) < 1e-9, 1e-9, y[:, j]))) * 100))
    return out

def main():
    t0 = time.time()
    rows = load()
    X, G, Y = featurize(rows)
    print("rows", len(rows), "features", X.shape[1], "device", DEV)
    report = {"n": len(rows), "features": X.shape[1], "device": DEV,
              "targets": ["log10_EUR", "log10_cost", "npv_million"], "folds": {}}

    # 5-fold random CV, XGBoost
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    xgb_preds = np.zeros_like(Y); mlp_preds = np.zeros_like(Y)
    for k, (tr, te) in enumerate(kf.split(X)):
        for j in range(3):
            m = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                                 subsample=0.9, colsample_bytree=0.9, random_state=SEED + k,
                                 n_jobs=4, verbosity=0)
            m.fit(X[tr], Y[tr, j]); xgb_preds[te, j] = m.predict(X[te])
        p, _, _ = train_mlp(X[tr], Y[tr], X[te], epochs=600)
        mlp_preds[te] = p
        print("fold", k, "done", round(time.time() - t0, 1), "s")
    report["folds"]["xgb_random5"] = metrics(Y, xgb_preds)
    report["folds"]["mlp_random5"] = metrics(Y, mlp_preds)

    # leave-one-case-out
    gkf = GroupKFold(n_splits=3)
    loo_xgb = []
    for tr, te in gkf.split(X, Y, G):
        pred = np.zeros_like(Y[te])
        for j in range(3):
            m = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                                 subsample=0.9, colsample_bytree=0.9, random_state=SEED, n_jobs=4, verbosity=0)
            m.fit(X[tr], Y[tr, j]); pred[:, j] = m.predict(X[te])
        loo_xgb.append(metrics(Y[te], pred))
    report["folds"]["xgb_leave_one_case_out"] = loo_xgb

    # final models on all data
    for j, name in enumerate(["EUR", "cost", "npv"]):
        m = xgb.XGBRegressor(n_estimators=500, max_depth=4, learning_rate=0.05,
                             subsample=0.9, colsample_bytree=0.9, random_state=SEED, n_jobs=4, verbosity=0)
        m.fit(X, Y[:, j]); m.save_model(os.path.join(OUT, f"surrogate_xgb_{name}.json"))
    p, model, stats = train_mlp(X, Y, X, epochs=800)
    torch.save({"state_dict": model.state_dict(), "stats": stats,
                "n_features": X.shape[1], "targets": ["log10_EUR", "log10_cost", "npv_million"]},
               os.path.join(OUT, "surrogate_mlp.pt"))
    report["final_fit"] = {"mlp_full": metrics(Y, p)}
    report["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(report, open(os.path.join(OUT, "surrogate_r0.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False)[:1200])

if __name__ == "__main__":
    main()
