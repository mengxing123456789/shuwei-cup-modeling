import os

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Freeze the P1-a decoding rule without searching on test.

Rule provenance:
  * minimum peak distance = 10th percentile of TRAINING segment durations in
    frames.  Predicting two boundaries closer than the shortest annotated
    subtask would create segments the annotation process itself never produced.
    This is a label prior, not a test-tuned constant.
  * peak height is the only free scalar; it is selected on validation ARI.

The test set is then scored once with that frozen rule.
"""
import json, os
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import adjusted_rand_score, f1_score
from scipy.optimize import linear_sum_assignment
import p1a_gpu_segmentation as M

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJ, "data")
MODELS = os.path.join(PROJ, "models")


def main():
    z, recs, segs, Xraw = M.load_arrays()
    tr = list(recs[recs.split == "train"].rec)
    va = list(recs[recs.split == "validation"].rec)
    te = list(recs[recs.split == "test"].rec)
    trm = np.isin(z["rec"], tr)
    mu, sd = Xraw[trm].mean(0), Xraw[trm].std(0) + 1e-6
    X = np.clip((Xraw - mu) / sd, -8, 8).astype(np.float32)
    M.X, M.XTR_DIM, M.XREC = X, X.shape[1], {}
    lab = {}
    for r in recs.rec:
        ii = np.where(z["rec"] == r)[0]
        hard, soft, inside = M.build_labels(segs, int(r), z["t"][ii], len(ii))
        sub = np.full(len(ii), -1, int)
        for _, s in segs[segs.rec == r].iterrows():
            sub[(z["t"][ii] >= s.start) & (z["t"][ii] < s.end)] = int(s.seg)
        M.XREC[r] = X[ii]
        lab[r] = (np.asarray(hard), inside, sub)

    # label prior: shortest annotated subtask in the training split
    dtr = segs[segs.split == "train"].dur.values * 30.0
    D = int(max(5, round(np.percentile(dtr, 10))))
    print(f"minimum peak distance from training label prior = {D} frames "
          f"({np.percentile(dtr,10)/30:.2f} s)", flush=True)

    nets = []
    for seed in (20261120, 20261121, 20261122):
        net = M.BoundaryNet(X.shape[1], bidir=True).to(M.DEVICE)
        net.load_state_dict(torch.load(os.path.join(MODELS, f"p1a_seg_seed{seed}.pt"),
                                       map_location=M.DEVICE))
        net.eval()
        nets.append(net)

    def ens(rs):
        mem = [M.infer(n, rs) for n in nets]
        return [np.mean([m[i] for m in mem], 0) for i in range(len(rs))]

    vs, ts = ens(va), ens(te)

    def split_scores(scores, rs, h, d):
        ari, bf1, mae = [], [], []
        for sc, r in zip(scores, rs):
            hard, inside, sub = lab[r]
            b, peaks = M.decode_scores(sc, h, d)
            ari.append(float(adjusted_rand_score(sub[inside], b[inside])))
            f, m = M.boundary_f1(peaks, hard)
            bf1.append(f)
            if not np.isnan(m):
                mae.append(m)
        return float(np.mean(ari)), float(np.nanmean(bf1)), float(np.nanmean(mae))

    grid = []
    for H in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70):
        a, b, m = split_scores(vs, va, H, D)
        grid.append(dict(height=H, distance=D, val_ari=a, val_bf1=b, val_mae=m))
    g = pd.DataFrame(grid).sort_values("val_ari", ascending=False)
    print(g.head(6).round(4).to_string(index=False), flush=True)
    H = float(g.iloc[0].height)

    rows = []
    for sc, r in zip(ts, te):
        hard, inside, sub = lab[r]
        b, peaks = M.decode_scores(sc, H, D)
        ari = float(adjusted_rand_score(sub[inside], b[inside]))
        f, mae = M.boundary_f1(peaks, hard)
        yl, pl = np.unique(sub[inside]), np.unique(b[inside])
        Mx = np.zeros((len(yl), len(pl)))
        for i, u in enumerate(yl):
            for j, v in enumerate(pl):
                Mx[i, j] = ((sub[inside] == u) & (b[inside] == v)).sum()
        ri, ci = linear_sum_assignment(-Mx)
        mp = {pl[c]: yl[i] for i, c in zip(ri, ci)}
        pred = np.array([mp.get(v, -1) for v in b[inside]])
        rows.append(dict(rec=int(r), dataset=recs.set_index("rec").loc[r, "dataset"],
                         n=int(inside.sum()), n_pred=len(peaks), n_true=len(hard),
                         ari=ari, f1=float(f1_score(sub[inside], pred, average="micro")),
                         boundary_f1=f, boundary_mae=mae))
    tdf = pd.DataFrame(rows)
    tdf.to_csv(os.path.join(DATA, "p1a_gpu_segmentation_final_records.csv"), index=False, encoding="utf-8")
    out = dict(
        _meta=dict(rule="peak distance = round(10th percentile of training segment duration in frames); "
                         "height selected on validation ARI; test scored once",
                   distance=D, distance_seconds=float(D / 30),
                   height=H, val_ari=float(g.iloc[0].val_ari),
                   val_bf1=float(g.iloc[0].val_bf1), val_mae=float(g.iloc[0].val_mae),
                   weights="three-seed ensemble, 40 epochs, identical training script",
                   height_grid=grid),
        test=dict(mean_ari=float(tdf.ari.mean()), std_ari=float(tdf.ari.std(ddof=1)),
                  mean_f1=float(tdf.f1.mean()), mean_boundary_f1=float(tdf.boundary_f1.mean()),
                  mean_boundary_mae=float(tdf.boundary_mae.mean()), records=int(len(tdf))))
    with open(os.path.join(DATA, "p1a_gpu_segmentation_final.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(tdf.round(3).to_string(index=False), flush=True)
    print(json.dumps(out["test"], indent=1), flush=True)


if __name__ == "__main__":
    main()