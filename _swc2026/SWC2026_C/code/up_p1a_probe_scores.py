import os
# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Step 1 probe: cache ensemble boundary scores for ALL 69 records and reproduce
the published test baseline (height 0.30 / distance 54) exactly.

Writes (new files only):
  data/up_p1a_scores.npz      rec -> ensemble score, t, inside mask, hard idx, sub labels
  data/up_p1a_baseline_check.json
"""
import json, os, time
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import adjusted_rand_score

import p1a_gpu_segmentation as M

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MODELS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def main():
    t0 = time.time()
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
        lab[r] = (np.asarray(hard, int), inside, sub)
    print(f"data ready {time.time()-t0:.1f}s | records {len(recs)}", flush=True)

    nets = []
    for seed in (20261120, 20261121, 20261122):
        net = M.BoundaryNet(X.shape[1], bidir=True).to(M.DEVICE)
        net.load_state_dict(torch.load(os.path.join(MODELS, f"p1a_seg_seed{seed}.pt"),
                                       map_location=M.DEVICE))
        net.eval()
        nets.append(net)
    print(f"nets loaded {time.time()-t0:.1f}s", flush=True)

    allrec = [int(r) for r in recs.rec]
    scores, tt, ins, hd, sb = {}, {}, {}, {}, {}
    for i, r in enumerate(allrec):
        mem = [M.infer(n, [r])[0] for n in nets]
        scores[r] = np.mean(mem, 0).astype(np.float32)
        ii = np.where(z["rec"] == r)[0]
        tt[r] = z["t"][ii].astype(np.float64)
        ins[r] = lab[r][1]
        hd[r] = lab[r][0]
        sb[r] = lab[r][2]
        if i % 10 == 9:
            print(f"  infer {i+1}/{len(allrec)} {time.time()-t0:.1f}s", flush=True)

    meta = dict(split={int(r): str(recs.set_index("rec").loc[r, "split"]) for r in allrec},
                dataset={int(r): str(recs.set_index("rec").loc[r, "dataset"]) for r in allrec},
                n={int(r): int(recs.set_index("rec").loc[r, "n"]) for r in allrec},
                dur={int(r): float(recs.set_index("rec").loc[r, "dur"]) for r in allrec})
    np.savez_compressed(os.path.join(DATA, "up_p1a_scores.npz"),
                        rec=np.array(allrec),
                        score=np.array([scores[r] for r in allrec], dtype=object),
                        t=np.array([tt[r] for r in allrec], dtype=object),
                        inside=np.array([ins[r] for r in allrec], dtype=object),
                        hard=np.array([hd[r] for r in allrec], dtype=object),
                        sub=np.array([sb[r] for r in allrec], dtype=object),
                        meta=np.array([json.dumps(meta, ensure_ascii=False)], dtype=object),
                        allow_pickle=True)

    # ---- reproduce the published baseline exactly ----
    rows = []
    for r in te:
        sc, inside, sub, hard = scores[r], ins[r], sb[r], hd[r]
        lab_, peaks = M.decode_scores(sc, 0.30, 54)
        ari = float(adjusted_rand_score(sub[inside], lab_[inside]))
        bf1, bmae = M.boundary_f1(peaks, hard)
        rows.append(dict(rec=r, dataset=meta["dataset"][r], n_pred=len(peaks),
                         n_true=len(hard), ari=ari, boundary_f1=bf1, boundary_mae=bmae))
    tdf = pd.DataFrame(rows)
    mean_ari = float(tdf.ari.mean())
    print(tdf.round(4).to_string(index=False), flush=True)
    print(f"\nreproduced test mean ARI = {mean_ari:.9f}  (published 0.548686890159744)", flush=True)
    out = dict(published=0.548686890159744, reproduced=mean_ari,
               abs_diff=abs(mean_ari - 0.548686890159744), tol=5e-4,
               pass_=bool(abs(mean_ari - 0.548686890159744) <= 5e-4),
               per_record=tdf.round(6).to_dict("records"),
               seconds=round(time.time() - t0, 1))
    with open(os.path.join(DATA, "up_p1a_baseline_check.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_record"}, indent=1), flush=True)


if __name__ == "__main__":
    main()