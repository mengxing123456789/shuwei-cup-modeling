# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Late fusion of the V8 detector with the video-only bad-frame score.

The concatenation test (up4) asked a strong TCN to absorb 120 extra columns and
it overfitted.  This test keeps the production detector untouched and asks only
whether its probability should be blended with a weak video-only detector at the
score level.  The blend weight is chosen on validation AP and evaluated once on
test; the bar is AP >= 5% relative over V8 alone and worst-environment AUC not
below V8.

Usage: python code/up6_video_late_fusion.py [features.csv] [out.json]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import average_precision_score, roc_auc_score
import lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
FEATURES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, "v2_video_features.csv")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DATA, "up6_video_late_fusion.json")
CAMS = ["head_left", "head_right", "left_wrist", "right_wrist"]
STATS = ["diff_mean", "diff_p90", "static_frac", "roi_diff_mean", "roi_diff_p90",
         "roi_static_frac", "bright_mean", "bright_std", "roi_bright_mean",
         "roi_bright_std", "flow_mean", "flow_p90", "roi_flow_mean", "roi_flow_p90"]
SEEDS = [20261120, 20261122, 20261123]
K = 12


def rec_key(dataset: str, sample: str, uuid: str) -> str:
    if dataset == "EgoDemo":
        return str(sample)
    import re
    m = re.match(r"([0-9a-f]{8})", str(sample))
    prefix = "EgoPro_" if dataset == "EgoPro" else "EgoStan_"
    return prefix + (m.group(1) if m else "")


def video_table():
    v = pd.read_csv(FEATURES)
    v = v[v["decode_ok"] == 1].copy()
    v["camera"] = pd.Categorical(v["camera"], categories=CAMS)
    wide = v.pivot_table(index=["record_id", "t_s"], columns="camera",
                         values=STATS, aggfunc="mean")
    wide.columns = [f"{cam}_{stat}" for stat, cam in wide.columns]
    wide = wide.reset_index()
    for cam in CAMS:
        wide[f"has_{cam}"] = wide[f"{cam}_diff_mean"].notna().astype(np.int8)
    return wide.sort_values(["record_id", "t_s"]).reset_index(drop=True)


def align(v, panel, recs):
    keys = [rec_key(r.dataset, r.sample, r.uuid) for r in recs.itertuples()]
    n = len(panel["H"])
    rec, t = panel["rec"], panel["t"]
    vcols = [c for c in v.columns if c not in ("record_id", "t_s")]
    out = np.full((n, len(vcols)), np.nan, dtype=np.float32)
    for ridx in range(len(recs)):
        g = v[v["record_id"] == keys[ridx]]
        idx = np.where(rec == ridx)[0]
        if len(g) == 0:
            continue
        gt = g["t_s"].to_numpy()
        vals = g[vcols].to_numpy(dtype=np.float32)
        pos = np.clip(np.searchsorted(gt, t[idx]), 0, len(gt) - 1)
        prev = np.clip(pos - 1, 0, len(gt) - 1)
        choose = np.abs(gt[prev] - t[idx]) <= np.abs(gt[pos] - t[idx])
        p = np.where(choose, prev, pos)
        out[idx] = vals[p]
    df = pd.DataFrame(out, columns=vcols)
    df["v_age"] = 0.0
    df["v_found"] = (~df.iloc[:, 0].isna()).astype(np.int8)
    return df


def robust(df, rec):
    out = df.copy()
    cols = [c for c in df.columns if c not in ("v_age", "v_found")]
    for rid in np.unique(rec):
        m = rec == rid
        sub = df.loc[m, cols]
        med = sub.median()
        mad = ((sub - med).abs().median() * 1.4826).replace(0, np.nan).fillna(1.0)
        out.loc[m, cols] = ((sub - med) / mad).clip(-6, 6)
    for c in cols:
        out[c] = out[c].fillna(0.0)
    return out


def main():
    z = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    rec = z["rec"].astype(np.int64)
    t = z["t"].astype(np.float32)
    y_all = (z["badL"] | z["badR"]).astype(np.int8)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    bounds = {}
    for r in np.unique(rec):
        idx = np.where(rec == r)[0]
        bounds[int(r)] = (int(idx[0]), int(idx[-1]) + 1)
    sample_idx = np.concatenate([
        np.arange(lo + 14, hi) for lo, hi in bounds.values() if hi - lo > 14])
    Srec = rec[sample_idx]
    Sy = y_all[sample_idx]
    St = t[sample_idx]
    tr = recs.index[recs["split"] == "train"].to_numpy()
    va = recs.index[recs["split"] == "validation"].to_numpy()
    te = recs.index[recs["split"] == "test"].to_numpy()
    mask = lambda ids: np.isin(Srec, ids)

    fake = {"H": np.zeros((len(rec), 3)), "rec": rec, "t": t}
    V = robust(align(video_table(), fake, recs), rec).iloc[sample_idx].reset_index(drop=True)
    vid = [c for c in V.columns if c not in ("v_age", "v_found")]
    sel = SelectKBest(f_classif, k=min(K, len(vid))).fit(V.loc[mask(tr), vid], Sy[mask(tr)])
    chosen = [vid[i] for i in sel.get_support(indices=True)]
    X = V[chosen + ["v_age", "v_found"]]

    # video-only validation and test scores, averaged over the same three seeds
    vp, vv = [], []
    for s in SEEDS:
        m = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.03, num_leaves=15,
                               min_child_samples=100, subsample=0.8, colsample_bytree=0.6,
                               reg_lambda=3.0, random_state=s, n_jobs=4, verbose=-1,
                               objective="binary")
        m.fit(X[mask(tr)], Sy[mask(tr)], eval_set=[(X[mask(va)], Sy[mask(va)])],
              eval_metric="average_precision", callbacks=[lgb.early_stopping(60, verbose=False)])
        vp.append(m.predict_proba(X[mask(va)])[:, 1])
        vv.append(m.predict_proba(X[mask(te)])[:, 1])
    pv_video = np.mean(vp, axis=0)
    pt_video = np.mean(vv, axis=0)

    # V8 out-of-fold probability, average of the three saved seeds
    pts, pvs = [], []
    for s in SEEDS:
        q = np.load(os.path.join(DATA, f"up2_p1b_probs_V8_{s}.npz"), allow_pickle=True)
        pts.append(q["pt"]); pvs.append(q["pv"])
    pt_v8 = np.mean(pts, axis=0); pv_v8 = np.mean(pvs, axis=0)

    yv = Sy[mask(va)].astype(int); yt = Sy[mask(te)].astype(int)
    env = np.load(os.path.join(DATA, f"up2_p1b_probs_V8_{SEEDS[0]}.npz"), allow_pickle=True)["env"]
    baseline = dict(ap=float(average_precision_score(yt, pt_v8)),
                    auc=float(roc_auc_score(yt, pt_v8)),
                    worst=float(min(roc_auc_score(yt[env == e], pt_v8[env == e])
                                    for e in np.unique(env) if len(np.unique(yt[env == e])) > 1)))

    grid = np.linspace(0.0, 1.0, 21)
    scores = []
    for w in grid:
        p = (1 - w) * pv_v8 + w * pv_video
        scores.append(float(average_precision_score(yv, p)))
    best_w = float(grid[int(np.argmax(scores))])
    p_test = (1 - best_w) * pt_v8 + best_w * pt_video
    ap = float(average_precision_score(yt, p_test))
    auc = float(roc_auc_score(yt, p_test))
    worst = float(min(roc_auc_score(yt[env == e], p_test[env == e])
                      for e in np.unique(env) if len(np.unique(yt[env == e])) > 1))
    out = dict(
        features=os.path.basename(FEATURES), seeds=SEEDS, blend_weight=best_w,
        baseline_v8=baseline,
        fused=dict(ap=ap, auc=auc, worst_env_auc=worst),
        ap_rel_gain=float(ap / baseline["ap"] - 1),
        auc_gain=float(auc - baseline["auc"]),
        worst_gain=float(worst - baseline["worst"]),
        gate=dict(ap_rel=0.05, auc_abs=0.0),
        passes=bool(ap / baseline["ap"] - 1 >= 0.05 and worst >= baseline["worst"]),
        note="Late score fusion, weight chosen on validation AP; test evaluated once.")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
