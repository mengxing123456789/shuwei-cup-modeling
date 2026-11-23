import os

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Re-select only the decoding rule for the trained P1-a boundary detector.

Training already happened; this script rebuilds the inputs, loads the saved seed
models, and searches a wider (height, minimum-distance) grid on validation.  The
test set is scored once with the validation-selected rule.  Keeping this separate
means the test numbers cannot leak into model or rule selection.
"""
import json, os
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import f1_score
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

    nets = []
    for seed in (20261120, 20261121, 20261122):
        p = os.path.join(MODELS, f"p1a_seg_seed{seed}.pt")
        net = M.BoundaryNet(X.shape[1], bidir=True).to(M.DEVICE)
        net.load_state_dict(torch.load(p, map_location=M.DEVICE))
        net.eval()
        nets.append(net)

    def ens(rs):
        mem = [M.infer(n, rs) for n in nets]
        return [np.mean([m[i] for m in mem], 0) for i in range(len(rs))]

    vs, ts = ens(va), ens(te)

    def score_split(scores, rs, h, d):
        ari, bf1, mae = [], [], []
        for sc, r in zip(scores, rs):
            hard, inside, sub = lab[r]
            b, peaks = M.decode_scores(sc, h, d)
            ari.append(adjusted_rand_score(sub[inside], b[inside]))
            f, m = M.boundary_f1(peaks, hard)
            bf1.append(f); mae.append(m)
        return float(np.mean(ari)), float(np.mean(bf1)), float(np.nanmean(mae))

    grid = []
    for H in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        for D in (20, 30, 45, 60, 90, 120, 160, 220, 300):
            a, b, m = score_split(vs, va, H, D)
            grid.append(dict(height=H, distance=D, val_ari=a, val_bf1=b, val_mae=m))
    g = pd.DataFrame(grid).sort_values("val_ari", ascending=False)
    print(g.head(10).round(4).to_string(index=False))
    best = g.iloc[0]
    H, D = float(best.height), int(best.distance)
    a_te = []
    rows = []
    for sc, r in zip(ts, te):
        hard, inside, sub = lab[r]
        b, peaks = M.decode_scores(sc, H, D)
        ari = float(adjusted_rand_score(sub[inside], b[inside]))
        f, mae = M.boundary_f1(peaks, hard)
        # Hungarian frame F1
        yl, pl = np.unique(sub[inside]), np.unique(b[inside])
        Mx = np.zeros((len(yl), len(pl)))
        for i, u in enumerate(yl):
            for j, v in enumerate(pl):
                Mx[i, j] = ((sub[inside] == u) & (b[inside] == v)).sum()
        ri, ci = linear_sum_assignment(-Mx)
        mp = {pl[c]: yl[i] for i, c in zip(ri, ci)}
        pred = np.array([mp.get(v, -1) for v in b[inside]])
        f1 = float(f1_score(sub[inside], pred, average="micro"))
        a_te.append(ari)
        rows.append(dict(rec=int(r), dataset=recs.set_index("rec").loc[r, "dataset"],
                         n_pred=len(peaks), n_true=len(hard), ari=ari, f1=f1,
                         boundary_f1=f, boundary_mae=mae))
    tdf = pd.DataFrame(rows)
    tdf.to_csv(os.path.join(DATA, "p1a_gpu_segmentation_tuned_records.csv"), index=False, encoding="utf-8")
    out = dict(_meta=dict(height=H, distance=D, selected_on="validation only",
                          val_ari=float(best.val_ari), val_bf1=float(best.val_bf1),
                          grid_size=len(grid),
                          note="decoding re-selection only; weights are the trained 3-seed ensemble"),
               test=dict(mean_ari=float(np.mean(a_te)), std_ari=float(np.std(a_te, ddof=1)),
                         mean_f1=float(tdf.f1.mean()), mean_boundary_f1=float(tdf.boundary_f1.mean()),
                         mean_boundary_mae=float(tdf.boundary_mae.mean())),
               top_grid=grid[:0])
    out["top_grid"] = g.head(10).to_dict("records")
    with open(os.path.join(DATA, "p1a_gpu_segmentation_tuned.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out["test"], indent=1), "\nselected", H, D)


H = D = None
if __name__ == "__main__":
    main()