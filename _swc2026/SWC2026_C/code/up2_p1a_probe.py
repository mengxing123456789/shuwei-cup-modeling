# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 probe -- VALIDATION + TRAIN ONLY (test scores are never read).

Questions answered before any v2 training run:
  1. how many segments per record, and how short are the shortest ones (min_len lever);
  2. what is the localisation ceiling of the v1 boundary score: if K were known, what
     boundary F1 and ARI can the score reach with a spacing-constrained top-k pick;
  3. is there a systematic offset between the score peak and the annotated boundary
     (train-calibrated shift lever);
  4. how well does a label-free K predictor (ridge on duration + peak statistics,
     fitted on train only) recover K on validation.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up2_p1a_lib as L

D = L.load_cache()
TR, VA = L.ids(D, "train"), L.ids(D, "validation")
print(f"train {len(TR)} val {len(VA)} test {len(L.ids(D,'test'))}")

Z = np.load(os.path.join(L.DATA, "up_p1a_scores.npz"), allow_pickle=True)
REC = [int(x) for x in Z["rec"]]
SC = {r: Z["score"][i].astype(np.float64) for i, r in enumerate(REC)}
assert set(REC) == set(D["rec"])

# ---- 1. segment counts and segment durations (train only: labels of val are used only
#         through the aggregate metrics below, never for feature fitting) ----
seg_rows = []
for r in TR + VA:
    i = L.pos(D, r)
    k = len(np.unique(D["sub"][i][D["inside"][i]]))
    b = L.true_bounds(D, r)
    dur_seg = np.diff(np.concatenate([[0], b, [D["n"][i]]]))
    seg_rows.append(dict(rec=r, split=D["split"][i], K=int(k), n=D["n"][i],
                         dur=round(D["dur"][i], 1), min_seg=int(dur_seg.min()),
                         p10_seg=int(np.quantile(dur_seg, 0.10)),
                         med_seg=int(np.median(dur_seg))))
sg = pd.DataFrame(seg_rows)
print("\n=== segment geometry (train+val) ===")
print(sg.groupby("split")[["K", "n", "min_seg", "p10_seg", "med_seg"]].describe().round(1).to_string())
for split in ("train", "validation"):
    v = sg[sg.split == split]
    print(f"{split}: K range {v.K.min()}-{v.K.max()} median {v.K.median():.0f}; "
          f"segment frames min {v.min_seg.min()} p10 {v.p10_seg.quantile(.5):.0f} "
          f"median {v.med_seg.median():.0f}")

# ---- 2. ceiling of the v1 score: oracle K, spacing-constrained top-k ----
print("\n=== ceiling with K known (val): top-K strongest peaks, min_len grid ===")
rows = []
for Lmin in (8, 12, 18, 24, 30, 40, 54):
    pk = {}
    for r in VA:
        i = L.pos(D, r)
        kt = len(np.unique(D["sub"][i][D["inside"][i]])) - 1
        pk[r] = L.decode_topk(SC[r], kt, sigma=1.0, min_len=Lmin, n=D["n"][i])
    ev = L.eval_peaks(pk, D, VA, f"oracleK_L{Lmin}")
    rows.append(dict(min_len=Lmin, ari=ev["mean_ari"], bf1=ev["mean_bf1"],
                     kerr=ev["mean_k_abs_err"]))
print(pd.DataFrame(rows).round(4).to_string(index=False))
best = max(rows, key=lambda x: x["bf1"])
print(f"best oracle-K bf1 {best['bf1']:.4f} at min_len {best['min_len']}")

# also: no spacing constraint at all
pk = {}
for r in VA:
    i = L.pos(D, r)
    kt = len(np.unique(D["sub"][i][D["inside"][i]])) - 1
    pk[r] = L.decode_topk(SC[r], kt, sigma=1.0, min_len=1, n=D["n"][i])
ev = L.eval_peaks(pk, D, VA, "oracleK_free")
print(f"oracle-K without spacing: ARI {ev['mean_ari']:.4f} bf1 {ev['mean_bf1']:.4f}")

# ---- 3. localisation offset, calibrated on train ----
shift, st = L.fit_k_offset(D, TR, SC)
print(f"\n=== offset train->true: median {st['median']:+.1f} mad {st['mad']:.1f} "
      f"(n={st['n']}) -> shift {shift:+d}")

# ---- 4. K predictor fitted on train, checked on validation ----
Ktr = [len(np.unique(D["sub"][L.pos(D, r)][D["inside"][L.pos(D, r)]])) for r in TR]
Xtr = [L.k_features(SC[r], D["dur"][L.pos(D, r)], D["n"][L.pos(D, r)],
                    D["bad"][L.pos(D, r)]) for r in TR]
model = L.fit_k_ridge(Xtr, Ktr, alpha=3.0)
print("\n=== K ridge (train fit, val check) ===")
print("coef", dict(zip(L.__dict__.get("K_FEATURES", []), np.round(model[2], 3))) if False else
      "features log_dur,npred_q90,npred_q80,npred_q30,mean_z,max_z,frac_half,bad_rate,log_n")
print(f"intercept {model[3]:.3f}")
for r in VA:
    i = L.pos(D, r)
    x = L.k_features(SC[r], D["dur"][i], D["n"][i], D["bad"][i])
    kt = len(np.unique(D["sub"][i][D["inside"][i]]))
    print(f"  val rec{r:02d} n={D['n'][i]:4d} dur={D['dur'][i]:6.1f}s K_true={kt:2d} "
          f"K_hat={L.predict_k(model, x):5.2f}")

# val ARI/BF1 with predicted K + top-k
for alpha_name, kf in (("ridge", None),):
    picks = {}
    for r in VA:
        i = L.pos(D, r)
        x = L.k_features(SC[r], D["dur"][i], D["n"][i], D["bad"][i])
        k = max(1, int(round(L.predict_k(model, x))))
        picks[r] = L.decode_topk(SC[r], k, sigma=1.0, min_len=best["min_len"],
                                 shift=shift, n=D["n"][i])
    ev = L.eval_peaks(picks, D, VA, "ridgeK")
    print(f"val ridgeK + topk: ARI {ev['mean_ari']:.4f} bf1 {ev['mean_bf1']:.4f} "
          f"kerr {ev['mean_k_abs_err']:.2f}")
    print(ev["frame"].round(3).to_string(index=False))

# ---- 5. v1 baseline on val for reference, same metric ----
picks = {}
for r in VA:
    picks[r] = L.decode_legacy(SC[r], sigma=3, kind="q", param=0.85, dist=54)
ev = L.eval_peaks(picks, D, VA, "v1_q85_s3_D54")
print(f"\nval v1 best rule: ARI {ev['mean_ari']:.4f} bf1 {ev['mean_bf1']:.4f}")

sg.to_csv(os.path.join(L.DATA, "up2_p1a_probe_geometry.csv"), index=False, encoding="utf-8")
print("\nprobe done")