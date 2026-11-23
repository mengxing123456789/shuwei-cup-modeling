# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 probe 2 -- why does the v1 score fail at +-2 frame boundary F1?
VALIDATION + TRAIN only.

For every true boundary: distance to the nearest candidate local maximum, and the
score rank of that candidate (1 = strongest).  Then the best boundary F1 any
score-driven selection can reach with a spacing-constrained DP over lambda.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up2_p1a_lib as L

D = L.load_cache()
TR, VA = L.ids(D, "train"), L.ids(D, "validation")
Z = np.load(os.path.join(L.DATA, "up_p1a_scores.npz"), allow_pickle=True)
REC = [int(x) for x in Z["rec"]]
SC = {r: Z["score"][i].astype(np.float64) for i, r in enumerate(REC)}

for recs, name in ((VA, "val"), (TR, "train")):
    dists, ranks, rel = [], [], []
    for r in recs:
        s = L.smooth(SC[r], 1.0)
        cand = L._candidates(s, 5, 0.02)
        if len(cand) == 0:
            continue
        order = np.argsort(-s[cand])
        rank_of = {int(c): int(k) + 1 for k, c in enumerate(cand[order])}
        for t in L.true_bounds(D, r):
            j = int(cand[np.argmin(np.abs(cand - t))])
            dists.append(abs(j - t))
            ranks.append(rank_of[j])
            rel.append(float(s[j] - np.median(s)) / (np.quantile(s, .75) - np.quantile(s, .25) + 1e-9))
    dists, ranks = np.asarray(dists), np.asarray(ranks)
    print(f"\n=== {name}: {len(dists)} true boundaries ===")
    print(f"nearest-candidate distance: <=2 {np.mean(dists<=2):.2f} <=5 {np.mean(dists<=5):.2f} "
          f"median {np.median(dists):.0f}")
    print(f"rank of boundary-nearest candidate: median {np.median(ranks):.0f} "
          f"p25 {np.quantile(ranks,.25):.0f} p75 {np.quantile(ranks,.75):.0f} "
          f"max {ranks.max()}; share in top-3 {np.mean(ranks<=3):.2f} top-5 {np.mean(ranks<=5):.2f}")
    print(f"z of boundary-nearest candidate: median {np.median(rel):.2f}")

print("\n=== decoder ceiling on val: DP over (sigma, min_len, lam) ===")
rows = []
for sigma in (0.0, 0.7, 1.0, 1.5, 2.0, 3.0):
    for Lmin in (8, 12, 18, 24, 30):
        for lam in (0.15, 0.25, 0.35, 0.45, 0.6, 0.8, 1.0):
            pk = {r: L.decode_dp(SC[r], sigma=sigma, min_len=Lmin, lam=lam,
                                 cand_dist=5, prom_floor=0.02, n=D["n"][L.pos(D, r)])
                  for r in VA}
            ev = L.eval_peaks(pk, D, VA)
            rows.append(dict(sigma=sigma, min_len=Lmin, lam=lam, ari=ev["mean_ari"],
                             bf1=ev["mean_bf1"], npred=ev["mean_npred"],
                             kerr=ev["mean_k_abs_err"]))
df = pd.DataFrame(rows).sort_values("bf1", ascending=False)
print("top 10 by bf1:")
print(df.head(10).round(4).to_string(index=False))
print("\ntop 10 by ARI:")
print(df.sort_values("ari", ascending=False).head(10).round(4).to_string(index=False))
print(f"\nbest val bf1 achievable by DP: {df.bf1.max():.4f}")

# combined criterion
df["j"] = df.ari + df.bf1
print("\nbest by ARI+bf1:")
print(df.sort_values("j", ascending=False).head(6).round(4).to_string(index=False))
df.to_csv(os.path.join(L.DATA, "up2_p1a_probe_dp_grid.csv"), index=False, encoding="utf-8")
print("probe2 done")