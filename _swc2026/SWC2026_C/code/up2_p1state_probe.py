# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Probe (validation only): can per-record normalisation / temporal residual features
recover the logistics-domain signal that the global logistic model misses?

No test scoring here; this script only uses train/validation to choose the recipe.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler

sys.stdout.reconfigure(encoding="utf-8")
DATA = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
Z = np.load(os.path.join(DATA, "state.npz"))
rec = Z["rec"].astype(int)
fl, fr, gl, gr = Z["fl"], Z["fr"], Z["gl"], Z["gr"]
badL, badR = Z["badL"], Z["badR"]
recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
split_of = dict(zip(recs.rec, recs.split)); env_of = dict(zip(recs.rec, recs.env))

# frame-level design: both hands' geometry (16) + state summary
Xg = np.concatenate([gl, gr], axis=1).astype(np.float64)   # 16
Xfull = np.concatenate([fl, fr, gl, gr], axis=1).astype(np.float64)  # 80
y = (badL | badR).astype(int)


def per_record_norm(X, mode="z"):
    out = np.zeros_like(X)
    for r in np.unique(rec):
        ii = np.where(rec == r)[0]
        v = X[ii]
        if mode == "z":
            mu = np.median(v, 0); sd = np.percentile(v, 75, 0) - np.percentile(v, 25, 0) + 1e-6
            out[ii] = (v - mu) / sd
        elif mode == "rank":
            from scipy.stats import rankdata
            for j in range(v.shape[1]):
                out[ii, j] = rankdata(v[:, j]) / len(ii) - 0.5
    return out


def auc_report(name, p, mask=None):
    m = np.ones(len(y), bool) if mask is None else mask
    print("  %-40s AUC=%.4f AP=%.4f n=%d pos=%d" % (
        name, roc_auc_score(y[m], p[m]), average_precision_score(y[m], p[m]), m.sum(), y[m].sum()))


Xg_z = per_record_norm(Xg)
Xfull_z = per_record_norm(Xfull)
tr = np.array([split_of[r] == "train" for r in rec])
va = np.array([split_of[r] == "validation" for r in rec])

print("== validation envs feature strength (per-record z of geometry) ==")
for e in sorted(set(env_of[r] for r in np.unique(rec[va]))):
    m = np.array([env_of[r] == e for r in rec]) & va
    if y[m].sum() == 0:
        continue
    aucs = [(j, roc_auc_score(y[m], Xg_z[m, j])) for j in range(Xg_z.shape[1])]
    aucs.sort(key=lambda t: -abs(t[1] - 0.5))
    print(e, "n", m.sum(), "pos", y[m].sum(), "best", [(j, round(a, 3)) for j, a in aucs[:5]])

print("\n== models (train -> validation) ==")
for tag, Xall in [("raw_geom", Xg), ("recnorm_geom", Xg_z), ("recnorm_full", Xfull_z)]:
    sc = StandardScaler().fit(Xall[tr])
    clf = LogisticRegression(C=0.1, class_weight="balanced", max_iter=4000).fit(sc.transform(Xall[tr]), y[tr])
    p = clf.predict_proba(sc.transform(Xall))[:, 1]
    auc_report("logreg " + tag, p, va)
    for e in sorted(set(env_of[r] for r in np.unique(rec[va]))):
        m = np.array([env_of[r] == e for r in rec]) & va
        if y[m].sum() > 0:
            print("      %-36s AUC=%.3f" % (e, roc_auc_score(y[m], p[m])))

print("\n== nonlinear HGB on recnorm_full ==")
hgb = HistGradientBoostingClassifier(max_depth=4, max_iter=200, learning_rate=0.05,
                                     min_samples_leaf=40, l2_regularization=1.0,
                                     class_weight="balanced", random_state=0)
hgb.fit(Xfull_z[tr], y[tr])
p = hgb.predict_proba(Xfull_z)[:, 1]
auc_report("HGB recnorm_full", p, va)
for e in sorted(set(env_of[r] for r in np.unique(rec[va]))):
    m = np.array([env_of[r] == e for r in rec]) & va
    if y[m].sum() > 0:
        print("      %-36s AUC=%.3f" % (e, roc_auc_score(y[m], p[m])))

# ---------------- next-frame prediction residual (self-supervised, train-only fit) ----------------
ZP = np.load(os.path.join(DATA, "panel.npz"))
P = np.concatenate([ZP["L"].reshape(len(rec), -1), ZP["R"].reshape(len(rec), -1)], axis=1).astype(np.float64)  # 126
Pn = per_record_norm(P)
res_feats = np.zeros((len(rec), 6), np.float64)
# pooled train pairs; no test record contributes to the fit
Xp, Yp = [], []
for r in np.unique(rec[tr]):
    ii = np.where(rec == r)[0]
    if len(ii) > 4:
        Xp.append(Pn[ii[:-1]]); Yp.append(Pn[ii[1:]])
Xp = np.vstack(Xp); Yp = np.vstack(Yp)
W = np.linalg.solve(Xp.T @ Xp + 10.0 * np.eye(Xp.shape[1]), Xp.T @ Yp)
for r in np.unique(rec):
    ii = np.where(rec == r)[0]
    if len(ii) < 5:
        continue
    Xr = Pn[ii[:-1]]; Yr = Pn[ii[1:]]
    pred = Xr @ W
    err = np.linalg.norm(pred - Yr, axis=1)
    med = np.median(err)
    eL = np.linalg.norm((pred - Yr)[:, :63], axis=1)
    eR = np.linalg.norm((pred - Yr)[:, 63:], axis=1)
    res_feats[ii[:-1], 0] = err
    res_feats[ii[:-1], 1] = np.abs(err - med)
    res_feats[ii[:-1], 2] = eL
    res_feats[ii[:-1], 3] = eR
    res_feats[ii[:-1], 4] = np.maximum(eL, eR)
    if len(ii) > 3:
        acc = np.linalg.norm(Pn[ii][2:] - 2 * Pn[ii][1:-1] + Pn[ii][:-2], axis=1)
        res_feats[ii[1:-1], 5] = acc
res_feats[-1] = res_feats[-2]
print("\n== next-frame residual (val AUC, frame-level) ==")
for j in range(6):
    print("res%d val AUC %.3f" % (j, roc_auc_score(y[va], res_feats[va, j])))
# combined HGB with recnorm geom + residual
Xc = np.concatenate([Xfull_z, res_feats], axis=1)
hgb2 = HistGradientBoostingClassifier(max_depth=4, max_iter=250, learning_rate=0.05,
                                      min_samples_leaf=40, l2_regularization=1.0,
                                      class_weight="balanced", random_state=0)
hgb2.fit(Xc[tr], y[tr])
p2 = hgb2.predict_proba(Xc)[:, 1]
print("\n== HGB recnorm_full + residual ==")
auc_report("HGB+res", p2, va)
for e in sorted(set(env_of[r] for r in np.unique(rec[va]))):
    m = np.array([env_of[r] == e for r in rec]) & va
    if y[m].sum() > 0:
        print("      %-36s AUC=%.3f" % (e, roc_auc_score(y[m], p2[m])))
