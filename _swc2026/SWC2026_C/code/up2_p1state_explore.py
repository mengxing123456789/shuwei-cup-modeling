# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1 v2 exploration: label inventory, per-record/env rates, temporal structure,
and signal checks of the existing geometry features."""
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA = os.path.abspath(DATA)
Z = np.load(os.path.join(DATA, "panel.npz"), allow_pickle=True)
badL, badR, rec = Z["badL"], Z["badR"], Z["rec"].astype(int)
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))

print("total frames", len(rec), "badL", badL.mean(), "badR", badR.mean(),
      "any", (badL | badR).mean())
print()
for _, s in recs.iterrows():
    ii = np.where(rec == s.rec)[0]
    bt = json.loads(s.bad_types)
    print("rec%2d %-10s %-38s n=%5d badL=%.4f badR=%.4f types=%s" % (
        s.rec, s.split, s.env, len(ii), badL[ii].mean(), badR[ii].mean(), bt))

print("\n-- split totals (hand-frames) --")
for split in ["train", "validation", "test"]:
    rs = recs[recs.split == split].rec
    ii = np.concatenate([np.where(rec == r)[0] for r in rs])
    pos = int(badL[ii].sum() + badR[ii].sum())
    print(split, "hand-frames", len(ii) * 2, "pos", pos, "rate", pos / (2 * len(ii)))

print("\n-- run lengths --")
for hand, b in [("L", badL), ("R", badR)]:
    runs = []
    for r in recs.rec:
        ii = np.where(rec == r)[0]
        v = b[ii].astype(int)
        d = np.diff(np.concatenate([[0], v, [0]]))
        st = np.where(d == 1)[0]
        en = np.where(d == -1)[0]
        runs += list(en - st)
    print(hand, "n_runs", len(runs), "mean", np.mean(runs) if runs else None,
          "median", np.median(runs) if runs else None, "max", max(runs) if runs else None)

print("\n-- per-env hand-level --")
recs["frame_pos_L"] = 0
for e, g in recs.groupby(["split", "env"]):
    ii = np.concatenate([np.where(rec == r)[0] for r in g.rec])
    posL = int(badL[ii].sum()); posR = int(badR[ii].sum())
    print(g.split.iloc[0] if hasattr(g, 'split') else e[0], e, "recs", len(g),
          "frames", len(ii), "posL", posL, "posR", posR,
          "rate_hand", (posL + posR) / (2 * len(ii)))

print("\n-- signal of raw geometry features per env (point-biserial / AUC) --")
st = np.load(os.path.join(DATA, "state.npz"))
gl, gr = st["gl"], st["gr"]
for e in sorted(recs.env.unique()):
    g = recs[recs.env == e]
    ii = np.concatenate([np.where(rec == r)[0] for r in g.rec])
    X = np.concatenate([gl[ii], gr[ii]], axis=0)
    y = np.concatenate([badL[ii], badR[ii]])
    if y.sum() == 0 or y.sum() == len(y):
        print("%-38s no both-class" % e)
        continue
    aucs = []
    for j in range(X.shape[1]):
        try:
            aucs.append(roc_auc_score(y, X[:, j]))
        except Exception:
            aucs.append(np.nan)
    aucs = np.array(aucs)
    best = np.argsort(-np.abs(aucs - 0.5))[:3]
    print("%-38s n=%6d pos=%4d  best=%s" % (
        e, len(y), int(y.sum()),
        ", ".join("f%d=%.3f" % (j, aucs[j]) for j in best)))
