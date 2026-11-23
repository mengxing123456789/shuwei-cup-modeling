"""R1: per-case surrogate models.

Rationale: R0 showed that a pooled model cannot extrapolate to an unseen
geological case (leave-one-case-out R2 < 0 because the cases differ by more
than an order of magnitude in level).  The fix is to train one model per case
and keep the case identifier out of the features.  This is also the physically
honest choice: each case has its own permeability/stress level, so a shared
regression is not identifiable across cases.
"""
import json, os, math, random, time
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error
import xgboost as xgb

SEED = 20261120
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models"); os.makedirs(OUT, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"

def load_case(case):
    d = json.load(open(os.path.join(ROOT, "data", "p4_econ.json"), encoding="utf-8"))
    rows = []
    for key, pts in d["pareto"].items():
        c, cal = key.split("|")
        if c != case or cal not in ("geo", "emp"):
            continue
        for p in pts:
            rows.append([math.log10(max(p["ts"], 1e-6)), p["cn"], math.log10(max(p["Vinj"], 1)),
                         p["fCO2"], math.log10(max(p["qinj"], 1)),
                         math.log10(max(p["EUR_m3"], 1e-9)), math.log10(max(p["cost_nom"], 1e-9)), p["npv"] / 1e6])
    return np.array(rows, float)

class MLP(nn.Module):
    def __init__(self, d_in=5, d_out=3):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, 96), nn.SiLU(), nn.Dropout(0.05),
                                 nn.Linear(96, 96), nn.SiLU(), nn.Linear(96, 48), nn.SiLU(), nn.Linear(48, d_out))
    def forward(self, x): return self.net(x)

def mlp_fit(Xtr, Ytr, Xte, epochs=700):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    ym, ys = Ytr.mean(0), Ytr.std(0) + 1e-9
    xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32, device=DEV)
    yt = torch.tensor((Ytr - ym) / ys, dtype=torch.float32, device=DEV)
    xe = torch.tensor((Xte - mu) / sd, dtype=torch.float32, device=DEV)
    m = MLP().to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4)
    lossf = nn.MSELoss()
    for _ in range(epochs):
        m.train(); opt.zero_grad(); l = lossf(m(xt), yt); l.backward(); opt.step()
    m.eval()
    with torch.no_grad(): return m(xe).cpu().numpy() * ys + ym

def met(y, p):
    return {n: dict(r2=float(r2_score(y[:, j], p[:, j])),
                    rmse=float(np.sqrt(mean_squared_error(y[:, j], p[:, j]))))
            for j, n in enumerate(["EUR", "cost", "npv"])}

def main():
    rep = {"device": DEV, "cases": {}}
    t0 = time.time()
    for case in ["Case1", "Case2", "Case3"]:
        A = load_case(case); X, Y = A[:, :5], A[:, 5:]
        kf = KFold(5, shuffle=True, random_state=SEED)
        xp = np.zeros_like(Y); mp = np.zeros_like(Y)
        for k, (tr, te) in enumerate(kf.split(X)):
            for j in range(3):
                m = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                                     subsample=0.9, colsample_bytree=0.9, random_state=SEED + k,
                                     n_jobs=4, verbosity=0)
                m.fit(X[tr], Y[tr, j]); xp[te, j] = m.predict(X[te])
            mp[te] = mlp_fit(X[tr], Y[tr], X[te])
        rep["cases"][case] = {"n": len(X), "xgb": met(Y, xp), "mlp": met(Y, mp)}
        # final per-case models
        for j, n in enumerate(["EUR", "cost", "npv"]):
            m = xgb.XGBRegressor(n_estimators=500, max_depth=4, learning_rate=0.05,
                                 subsample=0.9, colsample_bytree=0.9, random_state=SEED, n_jobs=4, verbosity=0)
            m.fit(X, Y[:, j]); m.save_model(os.path.join(OUT, f"surrogate_{case}_xgb_{n}.json"))
        print(case, {t: round(rep["cases"][case]["mlp"][t]["r2"], 4) for t in ["EUR", "cost", "npv"]}, flush=True)
    rep["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(rep, open(os.path.join(OUT, "surrogate_r1.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", rep["elapsed_s"], "s")

if __name__ == "__main__":
    main()
