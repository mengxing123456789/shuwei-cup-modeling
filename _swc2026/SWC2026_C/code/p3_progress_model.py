
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 v2 model comparison: frozen train/validation/test and monotone prefix audit.

Models:
  M0 official-family median / training residual quantiles
  M1 old 8-statistic ridge (reproduced for reference)
  M2 progress ridge + log duration
  M3 histogram gradient boosting on progress features
  M4 GPU residual network with duration and pinball losses

The task metadata is official and visible at decision time. UUID/sample IDs and
source-segment indices are excluded. Validation selects the model; test is final.
"""
import json
import os
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
from common import DATA, write_json

SEED = 20261120
np.random.seed(SEED)
P = pd.read_csv(os.path.join(DATA, "prefix_progress_features.csv"))
OLD = pd.read_csv(os.path.join(DATA, "prefix_features.csv"))
XCOL = [c for c in P.columns if c.startswith("x")]
TAU = np.array([0.1, 0.25, 0.5, 0.75, 0.9])


def metrics(df, pred):
    out = []
    for pre, g in df.assign(pred=pred).groupby("prefix"):
        err = g.duration.values - g.pred.values
        out.append(dict(prefix=float(pre), n=int(len(g)),
                        mae=float(np.abs(err).mean()),
                        rmse=float(np.sqrt(np.mean(err ** 2))),
                        median_ae=float(np.median(np.abs(err))),
                        spearman=float(spearmanr(g.pred, g.duration).statistic),
                        bias=float(err.mean())))
    return out


def summary(rows):
    return dict(mae=float(np.mean([r["mae"] for r in rows])),
                rmse=float(np.mean([r["rmse"] for r in rows])),
                spearman=float(np.mean([r["spearman"] for r in rows])),
                by_prefix=rows)


def fit_classical():
    tr = P[P.split == "train"].copy()
    va = P[P.split == "validation"].copy()
    te = P[P.split == "test"].copy()
    results = {}
    # Official family median, fit only on train.
    med = tr.groupby("family").duration.median().to_dict()
    for name, d in (("validation", va), ("test", te)):
        results.setdefault("M0_family_median", {})[name] = summary(metrics(d, d.family.map(med).values))

    # Old baseline, exact design.
    oldf = ["speed_mean", "speed_std", "speed_max", "acc_mean", "aperture_mean",
            "aperture_std", "depth_mean", "depth_std"]
    def old_design(df):
        fam = pd.get_dummies(df.family).reindex(columns=["A", "L", "P"], fill_value=0).astype(float)
        return np.hstack([df[oldf].values, fam.values, df.prefix.values[:, None]])
    oldtr = OLD[OLD.split == "train"].copy()
    osc = StandardScaler().fit(old_design(oldtr))
    om = Ridge(alpha=3.0).fit(osc.transform(old_design(oldtr)), np.log(oldtr.duration.values))
    for name in ("validation", "test"):
        d = OLD[OLD.split == name].copy()
        pred = np.exp(om.predict(osc.transform(old_design(d))))
        results.setdefault("M1_old_ridge", {})[name] = summary(metrics(d, pred))

    xtr = np.nan_to_num(tr[XCOL].values)
    ytr = tr.duration.values
    xva = np.nan_to_num(va[XCOL].values)
    xte = np.nan_to_num(te[XCOL].values)
    sc = StandardScaler().fit(xtr)
    models = {
        "M2_progress_ridge": Ridge(alpha=30.0),
        "M3_progress_hgb": HistGradientBoostingRegressor(max_iter=180, learning_rate=0.045,
                                                          max_leaf_nodes=15, l2_regularization=3.0,
                                                          min_samples_leaf=12, random_state=SEED),
        "M3_progress_extra": ExtraTreesRegressor(n_estimators=350, min_samples_leaf=5,
                                                  max_features=0.75, n_jobs=-1,
                                                  random_state=SEED),
    }
    fitted = {}
    for name, m in models.items():
        if "ridge" in name:
            m.fit(sc.transform(xtr), np.log(ytr))
            pv = np.exp(m.predict(sc.transform(xva)))
            pt = np.exp(m.predict(sc.transform(xte)))
        else:
            m.fit(xtr, np.log(ytr))
            pv = np.exp(m.predict(xva))
            pt = np.exp(m.predict(xte))
        results[name] = {"validation": summary(metrics(va, pv)),
                         "test": summary(metrics(te, pt))}
        fitted[name] = (m, pv, pt)
    return results, (tr, va, te, sc, models, fitted)


if __name__ == "__main__":
    t0 = time.time()
    results, pack = fit_classical()
    out = {"_meta": {
        "split": "official train/validation/test by environment, no future lookup",
        "features": "progress-aware prefix features; no UUID/sample/source index",
        "selection": "validation MAE averaged over official prefix lengths",
        "target": "log duration for learned models",
        "models": list(results),
        "seed": SEED,
    }, "results": results, "seconds": time.time() - t0}
    write_json("p3_progress_models.json", out)
    for name, r in results.items():
        print("\n", name)
        for split in ("validation", "test"):
            print(split, "MAE", round(r[split]["mae"], 4),
                  "RMSE", round(r[split]["rmse"], 4),
                  "rho", round(r[split]["spearman"], 4))
            print("  ", [(x["prefix"], round(x["mae"], 3), round(x["spearman"], 3))
                         for x in r[split]["by_prefix"]])
    print("seconds", round(time.time() - t0, 1))