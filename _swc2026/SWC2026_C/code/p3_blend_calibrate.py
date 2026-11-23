
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Select a duration predictor on validation, then freeze quantile calibration.

Candidate point predictions: old ridge, progress ridge, phase-TCN median, family
median and convex blends. Selection uses validation MAE + monotone-prefix penalty.
Residual quantiles are fitted on TRAIN only, grouped by family and prefix with
shrinkage to the global prefix distribution. Test is reported after selection.
"""
import json
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from common import DATA, write_json

P = pd.read_csv(os.path.join(DATA, "prefix_progress_features.csv"))
O = pd.read_csv(os.path.join(DATA, "prefix_features.csv"))
N = pd.read_csv(os.path.join(DATA, "p3_neural_predictions.csv"))
KEY = ["unit_id", "split", "family", "prefix", "duration"]
D = P[KEY + [c for c in P.columns if c.startswith("x")]].copy()
D = D.merge(O[KEY + ["speed_mean", "speed_std", "speed_max", "acc_mean", "aperture_mean",
                      "aperture_std", "depth_mean", "depth_std"]], on=KEY, suffixes=("", "_old"))
D = D.merge(N[["unit_id", "prefix", "q10", "q25", "q50", "q75", "q90"]], on=["unit_id", "prefix"])
XCOL = [c for c in P.columns if c.startswith("x")]
OLDC = ["speed_mean", "speed_std", "speed_max", "acc_mean", "aperture_mean",
        "aperture_std", "depth_mean", "depth_std"]
tr = D[D.split == "train"].copy(); va = D[D.split == "validation"].copy(); te = D[D.split == "test"].copy()


def old_design(df):
    fam = pd.get_dummies(df.family).reindex(columns=["A", "L", "P"], fill_value=0).astype(float)
    return np.hstack([df[OLDC].values, fam.values, df.prefix.values[:, None]])


osc = StandardScaler().fit(old_design(tr))
om = Ridge(alpha=3.0).fit(osc.transform(old_design(tr)), np.log(tr.duration.values))
D["old"] = np.exp(om.predict(osc.transform(old_design(D))))
psc = StandardScaler().fit(tr[XCOL].values)
pm = Ridge(alpha=30.0).fit(psc.transform(tr[XCOL].values), np.log(tr.duration.values))
D["progress"] = np.exp(pm.predict(psc.transform(D[XCOL].values)))
med = tr.groupby("family").duration.median().to_dict()
D["family_median"] = D.family.map(med)
D["neural"] = D.q50
tr = D[D.split == "train"].copy(); va = D[D.split == "validation"].copy(); te = D[D.split == "test"].copy()


def score(df, pred):
    z = df.copy(); z["pred"] = np.maximum(pred, z.prefix)
    by = []
    for p, g in z.groupby("prefix"):
        by.append(dict(prefix=float(p), mae=float(np.mean(np.abs(g.duration - g.pred))),
                       rmse=float(np.sqrt(np.mean((g.duration-g.pred)**2))),
                       spearman=float(spearmanr(g.duration,g.pred).statistic)))
    maes = np.array([r["mae"] for r in by])
    return dict(mae=float(maes.mean()), rmse=float(np.mean([r["rmse"] for r in by])),
                spearman=float(np.mean([r["spearman"] for r in by])),
                monotone_gain=float(maes[0]-maes[-1]),
                nonmonotone=float(np.maximum(0, -np.diff(maes)).sum()), by_prefix=by)


candidates = {}
for name in ("old", "progress", "neural", "family_median"):
    candidates[name] = D[name].values
# Convex blends avoid uncontrolled stacking on only 35 validation units.
for a in np.linspace(0, 1, 21):
    candidates[f"old_neural_{a:.2f}"] = a*D.old.values + (1-a)*D.neural.values
    candidates[f"old_progress_{a:.2f}"] = a*D.old.values + (1-a)*D.progress.values
    candidates[f"neural_progress_{a:.2f}"] = a*D.neural.values + (1-a)*D.progress.values
# Three-way blend on a coarse simplex.
for a in (0.25, 0.5, 0.75):
    for b in (0.25, 0.5, 0.75):
        if a+b <= 1:
            candidates[f"triple_{a:.2f}_{b:.2f}"] = a*D.old.values+b*D.neural.values+(1-a-b)*D.progress.values

rank = []
for name, pred in candidates.items():
    vmask = D.split.values == "validation"
    s = score(D[vmask], pred[vmask])
    # Soft preference for monotone information gain, not a hard constraint.
    objective = s["mae"] + 0.08*s["nonmonotone"] - 0.03*max(0, s["monotone_gain"])
    rank.append(dict(name=name, objective=objective, **s))
rank = sorted(rank, key=lambda r: r["objective"])
best = rank[0]
D["pred"] = candidates[best["name"]]
tr = D[D.split == "train"].copy()

# Frozen train residual quantiles with family shrinkage. The median is recentred;
# other quantiles remain in duration units and preserve asymmetric tail risk.
resrows = []
for p in (0.2, 0.6, 1.0):
    gp = tr[tr.prefix == p]
    for fam in ("A", "L", "P", "ALL"):
        g = gp if fam == "ALL" else gp[gp.family == fam]
        # shrink family quantiles toward the prefix-global quantiles
        glob = gp.duration.values - gp.pred.values
        loc = g.duration.values - g.pred.values
        w = len(loc)/(len(loc)+20.0)
        row = dict(prefix=p, family=fam, n=len(loc), shrinkage=w)
        for q in (0.1, 0.25, 0.5, 0.6, 0.75, 0.8, 0.9):
            row[f"r{int(q*100)}"] = float(w*np.quantile(loc,q)+(1-w)*np.quantile(glob,q)) if len(loc) else float(np.quantile(glob,q))
        resrows.append(row)
R = pd.DataFrame(resrows)
R.to_csv(os.path.join(DATA, "p3_duration_residuals.csv"), index=False)

# Produce deployment table for every source unit and official prefix.
out = D[["unit_id", "split", "family", "prefix", "duration", "pred", "old", "progress", "neural"]].copy()
out["pred"] = np.maximum(out.pred, out.prefix)
for q in (10,25,50,60,75,80,90):
    vals = []
    for r in out.itertuples():
        rr = R[(R.prefix == r.prefix) & (R.family == r.family)].iloc[0]
        vals.append(max(r.prefix, r.pred + rr[f"r{q}"]))
    out[f"q{q}"] = vals
out.to_csv(os.path.join(DATA, "p3_duration_predictions.csv"), index=False)

# Quantile coverage and final test metrics.
coverage = {}
for split in ("train", "validation", "test"):
    g = out[out.split == split]
    coverage[split] = {f"q{q}": float(np.mean(g.duration <= g[f"q{q}"])) for q in (10,25,50,60,75,80,90)}
result = dict(_meta=dict(selection="validation MAE + 0.08 nonmonotonicity - 0.03 positive monotone gain",
                         candidates=len(candidates), calibration="train residuals; family shrinkage n/(n+20) toward prefix global",
                         deployment="data/p3_duration_predictions.csv", test_usage="metrics only after selection"),
              selected=best, top10=rank[:10],
              validation=score(out[out.split=="validation"], out[out.split=="validation"].pred),
              test=score(out[out.split=="test"], out[out.split=="test"].pred),
              coverage=coverage)
write_json("p3_duration_selected.json", result)
print("SELECTED", best["name"], "objective", best["objective"])
print("TOP10")
for r in rank[:10]: print(r["name"], round(r["objective"],4), round(r["mae"],4), round(r["monotone_gain"],4), round(r["spearman"],4))
print("VALIDATION", result["validation"])
print("TEST", result["test"])
print("COVERAGE", coverage)