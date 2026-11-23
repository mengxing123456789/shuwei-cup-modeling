"""R5: full-design-space surrogate (the fix for R4's extrapolation failure).

R4 trained on Pareto points only; the Pareto set covers a narrow slice of the
design space, so the MLP exploded on the full 20,664-point grid.  R5 samples
the full grid (stratified random 60/40 split per case), computes the true NPV
with p4_econ.scheme(), trains the MLP on the training split and evaluates on
the held-out split.  This is the model that can actually be used for design
optimisation.
"""
import json, os, math, random, time, sys
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import r2_score
from scipy.stats import spearmanr

SEED = 20261120
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import p4_econ as P
DEV = "cuda" if torch.cuda.is_available() else "cpu"
D = json.load(open(os.path.join(ROOT, "data", "p4_econ.json"), encoding="utf-8"))
P.OUT["_prm"] = D["_prm"]
OUT = os.path.join(ROOT, "models"); os.makedirs(OUT, exist_ok=True)

def make_grid():
    ts = np.arange(5, 61, 1.0); vinj = np.arange(1000, 5001, 100.0)
    cn = [0.5, 1.0, 1.5]; fco2 = [0.2, 0.5, 0.8]
    G = [[a, c, v, f, 800.0] for a in ts for v in vinj for c in cn for f in fco2]
    return np.array(G, float)

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(5, 128), nn.SiLU(), nn.Dropout(0.03),
                                 nn.Linear(128, 128), nn.SiLU(), nn.Dropout(0.03),
                                 nn.Linear(128, 64), nn.SiLU(), nn.Linear(64, 3))
    def forward(self, x): return self.net(x)

def train(X, Y, epochs=1500):
    mu, sd = X.mean(0), X.std(0) + 1e-9; ym, ys = Y.mean(0), Y.std(0) + 1e-9
    xt = torch.tensor((X - mu) / sd, dtype=torch.float32, device=DEV)
    yt = torch.tensor((Y - ym) / ys, dtype=torch.float32, device=DEV)
    m = MLP().to(DEV); opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4)
    L = nn.MSELoss()
    for _ in range(epochs):
        m.train(); opt.zero_grad(); l = L(m(xt), yt); l.backward(); opt.step()
    m.eval(); return m, (mu, sd, ym, ys)

def pred(m, st, X):
    mu, sd, ym, ys = st
    xt = torch.tensor((X - mu) / sd, dtype=torch.float32, device=DEV)
    with torch.no_grad():
        return np.vstack([m(xt[i:i + 8192]).cpu().numpy() for i in range(0, len(xt), 8192)]) * ys + ym

def main():
    t0 = time.time(); G = make_grid(); rep = {"n_grid": int(len(G)), "cases": {}}
    for case in ["Case1", "Case2", "Case3"]:
        actual = np.array([P.scheme(case, g[0], g[1], g[2], 800.0, g[3], 0.0)["npv"] for g in G])
        X = np.column_stack([np.log10(G[:, 0]), G[:, 1], np.log10(G[:, 2]), G[:, 3], np.log10(G[:, 4])])
        Y = np.column_stack([np.zeros(len(G)), np.zeros(len(G)), actual / 1e6])  # only NPV matters here
        idx = np.random.permutation(len(G)); ntr = int(0.6 * len(G)); tr, te = idx[:ntr], idx[ntr:]
        m, st = train(X[tr], Y[tr])
        p_te = pred(m, st, X[te])[:, 2] * 1e6
        r2 = float(r2_score(actual[te], p_te)); rho = float(spearmanr(actual[te], p_te).correlation)
        true_top = set(te[np.argsort(-actual[te])[:100]]); pred_top = set(te[np.argsort(-p_te)[:100]])
        overlap = len(true_top & pred_top)
        # optimise on all grid using surrogate, check against true
        p_all = pred(m, st, X)[:, 2] * 1e6
        bi = int(np.argmax(p_all)); bg = G[bi]
        gap = float((np.max(actual) - actual[bi]) / 1e4)
        rep["cases"][case] = {
            "n_train": int(ntr), "n_test": int(len(te)), "r2_npv_test": round(r2, 4),
            "spearman_test": round(rho, 4), "top100_overlap": overlap,
            "surrogate_best": {"ts": float(bg[0]), "cn": float(bg[1]), "Vinj": float(bg[2]), "fCO2": float(bg[3]),
                               "true_npv_wan": round(float(actual[bi] / 1e4), 2)},
            "true_best": {"ts": float(G[int(np.argmax(actual))][0]), "cn": float(G[int(np.argmax(actual))][1]),
                          "Vinj": float(G[int(np.argmax(actual))][2]), "fCO2": float(G[int(np.argmax(actual))][3]),
                          "npv_wan": round(float(np.max(actual) / 1e4), 2)},
            "gap_wan": round(gap, 2)
        }
        torch.save({"state_dict": m.state_dict(), "stats": st, "case": case}, os.path.join(OUT, f"surrogate_r5_{case}.pt"))
        print(case, rep["cases"][case], flush=True)
    rep["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(rep, open(os.path.join(OUT, "surrogate_r5_fullgrid.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", rep["elapsed_s"], "s")

if __name__ == "__main__":
    main()
