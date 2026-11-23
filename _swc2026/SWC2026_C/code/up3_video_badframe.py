# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-b third-round probe: does the video channel add information for bad frames?

Pre-registered gate (written before the run):
  P+V must beat P on test AP by at least 10% relative AND on test AUC by at least
  0.010 absolute, with the same record split and the same LightGBM budget.

The video stream is standardised *within each record* (robust median/MAD) and a
small set of video statistics is selected on the training split only, because
camera exposure and scene brightness differ across environments. The occlusion
signature is a relative drop, not an absolute level.

Outputs data/up3_video_badframe.json.
"""
from __future__ import annotations

import json
import os
import re

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import average_precision_score, roc_auc_score

import lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

GATE = dict(ap_rel=0.10, auc_abs=0.010)
SEEDS = [20261121, 20261122, 20261123]
CAMS = ["head_left", "head_right", "left_wrist", "right_wrist"]
STATS = ["diff_mean", "diff_p90", "static_frac", "roi_diff_mean", "roi_diff_p90",
         "roi_static_frac", "bright_mean", "bright_std", "roi_bright_mean",
         "roi_bright_std", "flow_mean", "flow_p90", "roi_flow_mean", "roi_flow_p90"]
K_VIDEO = 12


def rec_key(dataset: str, sample: str, uuid: str) -> str:
    if dataset == "EgoDemo":
        return str(sample)
    m = re.match(r"([0-9a-f]{8})", str(sample))
    prefix = "EgoPro_" if dataset == "EgoPro" else "EgoStan_"
    return prefix + (m.group(1) if m else "")


def build_video_table() -> pd.DataFrame:
    v = pd.read_csv(os.path.join(DATA, "v2_video_features.csv"))
    v = v[v["decode_ok"] == 1].copy()
    v["camera"] = pd.Categorical(v["camera"], categories=CAMS)
    wide = v.pivot_table(index=["record_id", "t_s"], columns="camera",
                         values=STATS, aggfunc="mean")
    wide.columns = [f"{cam}_{stat}" for stat, cam in wide.columns]
    wide = wide.reset_index()
    for cam in CAMS:
        wide[f"has_{cam}"] = wide[f"{cam}_diff_mean"].notna().astype(np.int8)
    return wide.sort_values(["record_id", "t_s"]).reset_index(drop=True)


def pose_features(panel: dict) -> pd.DataFrame:
    L, R = panel["L"], panel["R"]
    rec = panel["rec"]
    out = {}
    for side, K in (("L", L), ("R", R)):
        c = K.mean(axis=1)
        out[f"{side}_cx"], out[f"{side}_cy"], out[f"{side}_cz"] = c[:, 0], c[:, 1], c[:, 2]
        out[f"{side}_span"] = np.linalg.norm(K - c[:, None, :], axis=2).mean(axis=1)
        out[f"{side}_zrange"] = K[:, :, 2].max(axis=1) - K[:, :, 2].min(axis=1)
    out["interhand"] = np.linalg.norm(L.mean(axis=1) - R.mean(axis=1), axis=1)
    df = pd.DataFrame(out)
    for col in ("L_cx", "L_cy", "L_cz", "R_cx", "R_cy", "R_cz", "interhand"):
        df[f"{col}_v"] = df.groupby(rec)[col].diff().fillna(0.0)
        df[f"{col}_a"] = df.groupby(rec)[f"{col}_v"].diff().fillna(0.0)
    df["speed"] = np.sqrt(df["L_cx_v"] ** 2 + df["L_cy_v"] ** 2 + df["L_cz_v"] ** 2) + \
        np.sqrt(df["R_cx_v"] ** 2 + df["R_cy_v"] ** 2 + df["R_cz_v"] ** 2)
    for col in ("speed", "interhand"):
        df[f"{col}_mean15"] = df.groupby(rec)[col].transform(lambda s: s.rolling(15, min_periods=1).mean())
        df[f"{col}_std15"] = df.groupby(rec)[col].transform(lambda s: s.rolling(15, min_periods=1).std().fillna(0.0))
    return df


def align_video(v: pd.DataFrame, panel: dict, recs: pd.DataFrame) -> pd.DataFrame:
    keys = [rec_key(r.dataset, r.sample, r.uuid) for r in recs.itertuples()]
    n = len(panel["H"])
    rec, t = panel["rec"], panel["t"]
    vcols = [c for c in v.columns if c not in ("record_id", "t_s")]
    out = np.full((n, len(vcols) + 2), np.nan, dtype=np.float32)
    for ridx in range(len(recs)):
        g = v[v["record_id"] == keys[ridx]]
        idx = np.where(rec == ridx)[0]
        if len(g) == 0:
            continue
        gt = g["t_s"].to_numpy()
        vals = g[vcols].to_numpy(dtype=np.float32)
        pos = np.searchsorted(gt, t[idx])
        pos = np.clip(pos, 0, len(gt) - 1)
        prev = np.clip(pos - 1, 0, len(gt) - 1)
        choose = np.abs(gt[prev] - t[idx]) <= np.abs(gt[pos] - t[idx])
        pos = np.where(choose, prev, pos)
        dt = np.abs(gt[pos] - t[idx])
        ok = dt <= 0.75
        out[idx[ok], :len(vcols)] = vals[pos[ok]]
        out[idx[ok], -2] = dt[ok]
        out[idx[ok], -1] = 1.0
    df = pd.DataFrame(out, columns=vcols + ["v_age", "v_found"])
    df["v_found"] = df["v_found"].fillna(0).astype(np.int8)
    return df


def robust_normalise(V: pd.DataFrame, rec: np.ndarray) -> pd.DataFrame:
    out = V.copy()
    cols = [c for c in V.columns if c not in ("v_age", "v_found")]
    for rid in np.unique(rec):
        m = rec == rid
        sub = V.loc[m, cols]
        med = sub.median()
        mad = (sub - med).abs().median() * 1.4826
        mad = mad.replace(0, np.nan).fillna(1.0)
        out.loc[m, cols] = ((sub - med) / mad).clip(-6, 6)
    for c in cols:
        out[c] = out[c].fillna(0.0)
    return out


def fit_lgb(Xtr, ytr, Xva, yva, Xte, seed):
    m = lgb.LGBMClassifier(
        n_estimators=1000, learning_rate=0.03, num_leaves=15,
        min_child_samples=100, subsample=0.8, colsample_bytree=0.6,
        reg_lambda=3.0, random_state=seed, n_jobs=4, verbose=-1,
        objective="binary")
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="average_precision",
          callbacks=[lgb.early_stopping(60, verbose=False)])
    return m.predict_proba(Xte)[:, 1], int(m.best_iteration_ or m.n_estimators)


def main():
    z = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
    panel = {k: z[k] for k in z.files}
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    y = ((panel["badL"] > 0) | (panel["badR"] > 0)).astype(np.int8)
    frame_rec = panel["rec"]

    P = pose_features(panel)
    V = align_video(build_video_table(), panel, recs)
    Vn = robust_normalise(V, frame_rec)
    tr = recs.index[recs["split"] == "train"].to_numpy()
    va = recs.index[recs["split"] == "validation"].to_numpy()
    te = recs.index[recs["split"] == "test"].to_numpy()

    def mask(ids):
        return np.isin(frame_rec, ids)

    vid_cols = [c for c in Vn.columns if c not in ("v_age", "v_found")]
    sel = SelectKBest(f_classif, k=min(K_VIDEO, len(vid_cols))).fit(
        Vn.loc[mask(tr), vid_cols].fillna(0.0), y[mask(tr)])
    chosen = [vid_cols[i] for i in sel.get_support(indices=True)]
    Vsel = Vn[chosen + ["v_age", "v_found"]].copy()

    res = {}
    arms = (("P", P), ("V", V), ("Vsel", Vsel), ("P+Vsel", pd.concat([P, Vsel], axis=1)))
    for arm, X in arms:
        preds, iters = [], []
        for seed in SEEDS:
            p, it = fit_lgb(X[mask(tr)], y[mask(tr)], X[mask(va)], y[mask(va)], X[mask(te)], seed)
            preds.append(p)
            iters.append(it)
        p = np.mean(preds, axis=0)
        yt = y[mask(te)]
        res[arm] = dict(test_ap=float(average_precision_score(yt, p)),
                        test_auc=float(roc_auc_score(yt, p)),
                        positives=int(yt.sum()), frames=int(len(yt)),
                        best_iters=iters, n_features=int(X.shape[1]))
    ap_gain = res["P+Vsel"]["test_ap"] / max(res["P"]["test_ap"], 1e-12) - 1.0
    auc_gain = res["P+Vsel"]["test_auc"] - res["P"]["test_auc"]
    vmeta = pd.read_csv(os.path.join(DATA, "v2_video_features.csv"))
    decoded = int(vmeta[["record_id", "camera", "decoded_frames"]].drop_duplicates()["decoded_frames"].sum())
    videos = int(vmeta[["record_id", "camera"]].drop_duplicates().shape[0])
    out = dict(gate=GATE, seeds=SEEDS, arms=res,
               selected_video=chosen, videos=videos, frames_decoded=decoded,
               ap_rel_gain=float(ap_gain), auc_abs_gain=float(auc_gain),
               passes=bool(ap_gain >= GATE["ap_rel"] and auc_gain >= GATE["auc_abs"]),
               note="Video statistics are camera-specific, robust-standardised within record, and the top-12 are selected on train only.")
    with open(os.path.join(DATA, "up3_video_badframe.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
