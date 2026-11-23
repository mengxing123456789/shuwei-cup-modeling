
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Is extra prefix length worth anything? Fit one model per prefix length.

If MAE barely moves from 0.2 s to 1.0 s, then the marginal information of the paid
observation is ~0 and the observation budget is optimally unused. Fit per prefix
(no prefix indicator), evaluate on the same frozen split, and report the marginal
value of the 0.6 s and 1.0 s releases against the free 0.2 s release.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from common import DATA, write_json

SEED = 20261120
POSE = pd.read_csv(os.path.join(DATA, "prefix_progress_features.csv"))
VIS = pd.read_csv(os.path.join(DATA, "prefix_visual_features.csv"))
OLD = pd.read_csv(os.path.join(DATA, "prefix_features.csv"))
KEY = ["unit_id", "prefix"]
PCOLS = [c for c in POSE.columns if c.startswith("x")]
VCOLS = [c for c in VIS.columns if c.startswith("v") or c.startswith("flow")]
OCLS = ["speed_mean", "speed_std", "speed_max", "acc_mean", "aperture_mean",
        "aperture_std", "depth_mean", "depth_std"]
D = POSE[["unit_id", "split", "family", "task", "duration", "prefix"] + PCOLS].merge(
    VIS[KEY + VCOLS], on=KEY).merge(OLD[KEY + OCLS], on=KEY)
COLS = OCLS + PCOLS + VCOLS


def fam(df):
    return pd.get_dummies(df.family).reindex(columns=["A", "L", "P"], fill_value=0).astype(float).values


MODELS = {
    "ridge": lambda: make_pipeline(StandardScaler(), Ridge(alpha=30.0)),
    "ridge_hi": lambda: make_pipeline(StandardScaler(), Ridge(alpha=300.0)),
    "hgb_weak": lambda: HistGradientBoostingRegressor(max_iter=120, learning_rate=0.05,
                                                       max_leaf_nodes=7, l2_regularization=10.0,
                                                       min_samples_leaf=20, random_state=SEED),
    "rf": lambda: RandomForestRegressor(n_estimators=400, min_samples_leaf=6, max_features=0.5,
                                         n_jobs=-1, random_state=SEED),
    "krr": lambda: make_pipeline(StandardScaler(), KernelRidge(alpha=1.0, kernel="rbf", gamma=0.02)),
}

rows = []
for tag, cols in (("pose", OCLS + PCOLS), ("visual", VCOLS), ("all", COLS)):
    for mname, mk in MODELS.items():
        per_prefix = {}
        for pre in (0.2, 0.6, 1.0):
            g = D[D.prefix == pre]
            tr, va, te = g[g.split == "train"], g[g.split == "validation"], g[g.split == "test"]
            if len(tr) < 30:
                continue
            X = lambda d: np.nan_to_num(np.hstack([d[cols].values, fam(d)]))
            m = mk()
            m.fit(X(tr), np.log(tr.duration.values))
            r = {}
            for name, d in (("validation", va), ("test", te)):
                p = np.exp(m.predict(X(d)))
                res = d.duration.values - p
                r[name] = dict(n=int(len(d)), mae=float(np.mean(np.abs(res))),
                               sd_resid=float(np.std(res)),
                               sd_total=float(np.std(d.duration.values)),
                               shrink=float(1 - np.std(res) / max(np.std(d.duration.values), 1e-9)),
                               spearman=float(spearmanr(d.duration, p).statistic))
            per_prefix[pre] = r
        if len(per_prefix) < 3:
            continue
        for name in ("validation", "test"):
            m02 = per_prefix[0.2][name]["mae"]; m06 = per_prefix[0.6][name]["mae"]; m10 = per_prefix[1.0][name]["mae"]
            sh02 = per_prefix[0.2][name]["shrink"]; sh10 = per_prefix[1.0][name]["shrink"]
            rows.append(dict(features=tag, model=mname, split=name,
                             mae_0p2=m02, mae_0p6=m06, mae_1p0=m10,
                             mae_gain_0p2_to_1p0=m02 - m10,
                             mae_gain_frac=(m02 - m10) / max(m02, 1e-9),
                             shrink_0p2=sh02, shrink_1p0=sh10,
                             shrink_gain=sh10 - sh02,
                             spearman_0p2=per_prefix[0.2][name]["spearman"],
                             spearman_1p0=per_prefix[1.0][name]["spearman"]))

R = pd.DataFrame(rows)
R.to_csv(os.path.join(DATA, "p3_prefix_marginal_value.csv"), index=False)
print(R.round(4).to_string(index=False))
best_val = R[R.split == "validation"].sort_values("mae_1p0").head(8)
print("\nBEST by 1.0 s validation MAE")
print(best_val[["features", "model", "mae_0p2", "mae_1p0", "mae_gain_frac", "shrink_gain", "spearman_1p0"]].round(4).to_string(index=False))
v = R[R.split == "validation"]
t = R[R.split == "test"]
write_json("p3_prefix_marginal.json", dict(_meta=dict(
    question="marginal information of the paid prefixes 0.6 s and 1.0 s over the free 0.2 s",
    design="one model per prefix, no prefix indicator, identical frozen split",
    note="positive mae_gain_frac means the longer prefix helps; near zero means useless"),
    rows=rows,
    validation_median_gain_frac=float(v.mae_gain_frac.median()),
    test_median_gain_frac=float(t.mae_gain_frac.median()),
    validation_median_shrink_gain=float(v.shrink_gain.median()),
    test_median_shrink_gain=float(t.shrink_gain.median()),
    best_validation_1p0=best_val.iloc[0].to_dict()))