"""R2: Optuna tuning of the per-case XGBoost surrogates.

Objective: mean R2 over EUR and NPV (cost is already ~1.0), 3-fold CV.
Saves best parameters and the R2 table to models/surrogate_r2.json.
"""
import json, os, math, random, time
import numpy as np
import optuna
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
import xgboost as xgb

SEED = 20261120
random.seed(SEED); np.random.seed(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models")
optuna.logging.set_verbosity(optuna.logging.WARNING)

def load(case):
    d = json.load(open(os.path.join(ROOT, "data", "p4_econ.json"), encoding="utf-8"))
    rows = []
    for key, pts in d["pareto"].items():
        c, cal = key.split("|")
        if c != case or cal not in ("geo", "emp"): continue
        for p in pts:
            rows.append([math.log10(max(p["ts"], 1e-6)), p["cn"], math.log10(max(p["Vinj"], 1)),
                         p["fCO2"], math.log10(max(p["qinj"], 1)),
                         math.log10(max(p["EUR_m3"], 1e-9)), math.log10(max(p["cost_nom"], 1e-9)), p["npv"] / 1e6])
    return np.array(rows, float)

def evaluate(params, X, Y):
    kf = KFold(3, shuffle=True, random_state=SEED)
    scores = {0: [], 1: [], 2: []}
    for tr, te in kf.split(X):
        for j in range(3):
            m = xgb.XGBRegressor(**params, random_state=SEED, n_jobs=4, verbosity=0)
            m.fit(X[tr], Y[tr, j])
            scores[j].append(r2_score(Y[te, j], m.predict(X[te])))
    return {j: float(np.mean(v)) for j, v in scores.items()}

def main():
    t0 = time.time(); rep = {"device": "cpu", "cases": {}}
    for case in ["Case1", "Case2", "Case3"]:
        A = load(case); X, Y = A[:, :5], A[:, 5:]
        def obj(trial):
            p = dict(n_estimators=trial.suggest_int("n_estimators", 200, 700, step=100),
                     max_depth=trial.suggest_int("max_depth", 3, 6),
                     learning_rate=trial.suggest_float("learning_rate", 0.02, 0.12, log=True),
                     subsample=trial.suggest_float("subsample", 0.7, 1.0),
                     colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),
                     min_child_weight=trial.suggest_float("min_child_weight", 0.5, 5.0))
            s = evaluate(p, X, Y)
            return 0.5 * s[0] + 0.5 * s[2]
        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
        study.optimize(obj, n_trials=12, show_progress_bar=False)
        best = dict(study.best_params); best.update(random_state=SEED, n_jobs=4, verbosity=0)
        sc = evaluate({k: v for k, v in best.items() if k not in ("random_state", "n_jobs", "verbosity")}, X, Y)
        rep["cases"][case] = {"n": len(X), "best_params": study.best_params,
                              "cv3_r2": {n: round(sc[j], 4) for j, n in enumerate(["EUR", "cost", "npv"])},
                              "best_value": round(study.best_value, 4)}
        # refit on all data
        for j, n in enumerate(["EUR", "cost", "npv"]):
            m = xgb.XGBRegressor(**best); m.fit(X, Y[:, j])
            m.save_model(os.path.join(OUT, f"surrogate_{case}_r2_{n}.json"))
        print(case, rep["cases"][case]["cv3_r2"], flush=True)
    rep["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(rep, open(os.path.join(OUT, "surrogate_r2.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", rep["elapsed_s"], "s")

if __name__ == "__main__":
    main()
