"""Final per-case MLP surrogates + full-grid surrogate-vs-true optimisation.

Round R4:
- train one MLP per case on all Pareto points (5 inputs, 3 outputs);
- enumerate the entire design grid used by p4_econ (20,664 designs per case);
- compare surrogate NPV with the true `scheme()` NPV on every design;
- report R2, Spearman rank correlation and top-100 overlap;
- report the best design found by the surrogate and its true NPV.
"""
import json, os, math, random, time
import numpy as np
import torch
import torch.nn as nn
import sys

SEED = 20261120
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import p4_econ as P

DEV = "cuda" if torch.cuda.is_available() else "cpu"
D = json.load(open(os.path.join(ROOT, "data", "p4_econ.json"), encoding="utf-8"))
P.OUT["_prm"] = D["_prm"]
OUT = os.path.join(ROOT, "models"); os.makedirs(OUT, exist_ok=True)

def load(case):
    rows = []
    for key, pts in D["pareto"].items():
        c, cal = key.split("|")
        if c != case or cal not in ("geo", "emp"): continue
        for p in pts:
            rows.append([math.log10(max(p["ts"], 1e-6)), p["cn"], math.log10(max(p["Vinj"], 1)),
                         p["fCO2"], math.log10(max(p["qinj"], 1)),
                         math.log10(max(p["EUR_m3"], 1e-9)), math.log10(max(p["cost_nom"], 1e-9)), p["npv"] / 1e6])
    return np.array(rows, float)

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(5, 96), nn.SiLU(), nn.Dropout(0.05),
                                 nn.Linear(96, 96), nn.SiLU(), nn.Linear(96, 48), nn.SiLU(), nn.Linear(48, 3))
    def forward(self, x): return self.net(x)

def train(X, Y, epochs=1200):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    ym, ys = Y.mean(0), Y.std(0) + 1e-9
    xt = torch.tensor((X - mu) / sd, dtype=torch.float32, device=DEV)
    yt = torch.tensor((Y - ym) / ys, dtype=torch.float32, device=DEV)
    m = MLP().to(DEV); opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4); L = nn.MSELoss()
    for _ in range(epochs):
        m.train(); opt.zero_grad(); l = L(m(xt), yt); l.backward(); opt.step()
    m.eval()
    return m, (mu, sd, ym, ys)

def predict(m, stats, X):
    mu, sd, ym, ys = stats
    xt = torch.tensor((X - mu) / sd, dtype=torch.float32, device=DEV)
    with torch.no_grad():
        out = []
        for i in range(0, len(xt), 8192):
            out.append(m(xt[i:i + 8192]).cpu().numpy())
    return np.vstack(out) * ys + ym

def grid():
    ts = np.arange(5, 61, 1.0); vinj = np.arange(1000, 5001, 100.0)
    cn = [0.5, 1.0, 1.5]; fco2 = [0.2, 0.5, 0.8]
    G = []
    for a in ts:
        for v in vinj:
            for c in cn:
                for f in fco2:
                    G.append([a, c, v, f, 800.0])
    return np.array(G, float)

def main():
    t0 = time.time(); G = grid(); Xg = np.column_stack([np.log10(G[:, 0]), G[:, 1], np.log10(G[:, 2]), G[:, 3], np.log10(G[:, 4])])
    rep = {"n_grid": int(len(G)), "cases": {}}
    for case in ["Case1", "Case2", "Case3"]:
        A = load(case); X, Y = A[:, :5], A[:, 5:]
        m, st = train(X, Y)
        torch.save({"state_dict": m.state_dict(), "stats": st, "case": case}, os.path.join(OUT, f"surrogate_final_{case}.pt"))
        pred = predict(m, st, Xg)
        pred_npv = pred[:, 2] * 1e6
        # actual on the same grid
        actual = np.array([P.scheme(case, g[0], g[1], g[2], 800.0, g[3], 0.0)["npv"] for g in G])
        from sklearn.metrics import r2_score
        from scipy.stats import spearmanr
        r2 = float(r2_score(actual, pred_npv))
        rho = float(spearmanr(actual, pred_npv).correlation)
        # top-100 overlap
        true_top = set(np.argsort(-actual)[:100]); pred_top = set(np.argsort(-pred_npv)[:100])
        overlap = len(true_top & pred_top)
        # best predicted
        bi = int(np.argmax(pred_npv)); bg = G[bi]
        best_true = P.scheme(case, bg[0], bg[1], bg[2], 800.0, bg[3], 0.0)
        true_best_i = int(np.argmax(actual)); true_best = G[true_best_i]
        rep["cases"][case] = {
            "n_train": int(len(X)), "r2_npv": round(r2, 4), "spearman": round(rho, 4),
            "top100_overlap": overlap,
            "surrogate_best": {"ts": bg[0], "cn": bg[1], "Vinj": bg[2], "fCO2": bg[3],
                               "pred_npv_wan": round(float(pred_npv[bi] / 1e4), 2),
                               "true_npv_wan": round(float(best_true["npv"] / 1e4), 2)},
            "true_best": {"ts": float(true_best[0]), "cn": float(true_best[1]), "Vinj": float(true_best[2]),
                          "fCO2": float(true_best[3]), "npv_wan": round(float(np.max(actual) / 1e4), 2)},
            "gap_wan": round(float((np.max(actual) - best_true["npv"]) / 1e4), 2)
        }
        print(case, rep["cases"][case], flush=True)
    rep["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(rep, open(os.path.join(OUT, "surrogate_r4_optimization.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", rep["elapsed_s"], "s")

if __name__ == "__main__":
    main()
