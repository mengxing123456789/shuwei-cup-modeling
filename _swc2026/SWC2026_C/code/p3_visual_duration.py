
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Does the image carry duration information that the pose features miss?

Same frozen official split. Compares pose-only, visual-only and fused designs, and
reports the diagnostic that matters for P3: the residual spread as the released
prefix grows. If the spread does not shrink, a paid observation cannot be worth its
cost no matter how good the point predictor is.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
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
    VIS[KEY + VCOLS], on=KEY, how="inner").merge(OLD[KEY + OCLS], on=KEY, how="inner")
print("merged", D.shape, "pose", len(PCOLS), "visual", len(VCOLS))
tr = D[D.split == "train"]; va = D[D.split == "validation"]; te = D[D.split == "test"]


def design(df, cols):
    fam = pd.get_dummies(df.family).reindex(columns=["A", "L", "P"], fill_value=0).astype(float)
    return np.nan_to_num(np.hstack([df[cols].values, fam.values, df.prefix.values[:, None]]))


def fit(cols, tag, hgb=True):
    xtr, ytr = design(tr, cols), np.log(tr.duration.values)
    sc = StandardScaler().fit(xtr)
    out = {}
    rg = Ridge(alpha=30.0).fit(sc.transform(xtr), ytr)
    out["ridge"] = rg
    out["_sc"] = sc
    if hgb:
        hg = HistGradientBoostingRegressor(max_iter=220, learning_rate=0.04, max_leaf_nodes=15,
                                           l2_regularization=3.0, min_samples_leaf=12,
                                           random_state=SEED).fit(xtr, ytr)
        out["hgb"] = hg
    rows = []
    for name in (["ridge", "hgb"] if hgb else ["ridge"]):
        m = out[name]
        pred = np.exp((m.predict(sc.transform(xtr)) if name == "ridge" else m.predict(xtr)))
        tr2 = tr.assign(pred=pred)
        predv = np.exp((m.predict(sc.transform(design(va, cols))) if name == "ridge"
                        else m.predict(design(va, cols))))
        predt = np.exp((m.predict(sc.transform(design(te, cols))) if name == "ridge"
                        else m.predict(design(te, cols))))
        va2 = va.assign(pred=predv); te2 = te.assign(pred=predt)
        for split, df2 in (("train", tr2), ("validation", va2), ("test", te2)):
            sds = []
            for p in (0.2, 0.6, 1.0):
                g = df2[df2.prefix == p]
                res = g.duration.values - g.pred.values
                sds.append(dict(prefix=p, n=int(len(g)),
                                mae=float(np.mean(np.abs(res))),
                                sd_resid=float(np.std(res)),
                                sd_total=float(np.std(g.duration.values)),
                                spearman=float(spearmanr(g.duration, g.pred).statistic),
                                shrink=float(1 - np.std(res) / max(np.std(g.duration.values), 1e-9))))
            rows.append(dict(design=tag, model=name, split=split,
                             mae=float(np.mean([r["mae"] for r in sds])),
                             mean_shrink=float(np.mean([r["shrink"] for r in sds])),
                             shrink_0p2=float(sds[0]["shrink"]),
                             shrink_1p0=float(sds[-1]["shrink"]),
                             shrink_gain=float(sds[-1]["shrink"] - sds[0]["shrink"]),
                             spearman=float(np.mean([r["spearman"] for r in sds])),
                             by_prefix=sds))
    return rows


def main():
    allrows = []
    allrows += fit(OCLS, "pose_old8")
    allrows += fit(PCOLS, "pose_progress94")
    allrows += fit(VCOLS, "visual_only")
    allrows += fit(OCLS + PCOLS + VCOLS, "all_fused")
    allrows += fit(OCLS + VCOLS, "old8_visual")
    S = pd.DataFrame([{k: v for k, v in r.items() if k != "by_prefix"} for r in allrows])
    print(S.round(4).to_string(index=False))
    print("\nVALIDATION spread by prefix (the P3 decision-relevant view)")
    for r in allrows:
        if r["split"] != "validation":
            continue
        print(f"  {r['design']:18s} {r['model']:5s} "
              + "  ".join(f"{x['prefix']}:sd={x['sd_resid']:.3f},sh={x['shrink']:+.3f}"
                          for x in r["by_prefix"]))
    write_json("p3_visual_duration.json", dict(_meta=dict(
        split="official train/validation/test", target="log duration",
        question="does the image add transferable duration information to the pose features",
        diagnostic="residual spread per released prefix on the validation pool"), rows=allrows))


if __name__ == "__main__":
    main()