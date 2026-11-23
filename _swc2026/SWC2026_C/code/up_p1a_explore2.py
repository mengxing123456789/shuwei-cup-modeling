import os
# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Step 2b exploration -- VALIDATION and TRAIN ONLY (test scores are not read).

Levers tested, one at a time:
  1. smoothing scale sigma of the boundary score (2 frames is tiny at 30 fps);
  2. per-record adaptive height (quantile / median+k*MAD) at each sigma;
  3. boundary spacing D;
  4. penalised selection: greedy/DP pick of peaks with a per-boundary penalty and
     a minimum segment length (K then falls out instead of being thresholded).
All hyper-parameters are compared on validation mean ARI; train mean ARI is the
confirmation column (optimistic in absolute terms, only its direction is used).
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from scipy.signal import find_peaks, peak_prominences
from scipy.ndimage import gaussian_filter1d

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
Z = np.load(os.path.join(DATA, "up_p1a_scores.npz"), allow_pickle=True)
META = json.loads(str(Z["meta"][0]))
REC = [int(x) for x in Z["rec"]]
SC = {r: Z["score"][i].astype(np.float64) for i, r in enumerate(REC)}
IN = {r: Z["inside"][i] for i, r in enumerate(REC)}
SB = {r: Z["sub"][i] for i, r in enumerate(REC)}
SPLIT = {r: META["split"][str(r)] for r in REC}
VAL = [r for r in REC if SPLIT[r] == "validation"]
TR = [r for r in REC if SPLIT[r] == "train"]
BOTH = VAL + TR


def sm(r, sigma):
    return gaussian_filter1d(SC[r], sigma, mode="nearest")


def labs(peaks, n):
    return np.searchsorted(np.asarray(peaks), np.arange(n), side="right") if len(peaks) else np.zeros(n, int)


def ari(peaks, r):
    lab = labs(peaks, len(SC[r]))
    ins = IN[r]
    y = SB[r][ins]
    return float(adjusted_rand_score(y, lab[ins])) if len(np.unique(y)) > 1 else np.nan


def greedy(score, cand, L, lam):
    """Pick peaks by score-lambda, enforcing min gap L; stop when score<=lam."""
    order = np.argsort(-score[cand])
    chosen = []
    for i in order:
        p = cand[i]
        if score[p] <= lam:
            break
        if all(abs(p - c) >= L for c in chosen):
            chosen.append(p)
    return np.sort(np.array(chosen, int)) if chosen else np.array([], int)


def dp_pick(score, cand, L, lam):
    """Exact max sum(score[c]) - lam*count over candidates with gap>=L."""
    C = len(cand)
    if C == 0:
        return np.array([], int)
    val = np.full(C, -np.inf)
    prev = np.full(C, -1, int)
    for i in range(C):
        val[i] = score[cand[i]] - lam
        best, bi = -np.inf, -1
        for j in range(i):
            if cand[i] - cand[j] >= L and val[j] > best:
                best, bi = val[j], j
        if best > 0:
            val[i] = score[cand[i]] - lam + best
            prev[i] = bi
    if val.max() <= 0:
        return np.array([], int)
    i = int(np.argmax(val))
    out = []
    while i >= 0:
        out.append(cand[i])
        i = prev[i]
    return np.sort(np.array(out, int))


rows = []
for sigma in (2, 3, 5, 7, 10, 14):
    S = {r: sm(r, sigma) for r in BOTH}
    for D in (54, 78):
        # fixed height
        for H in (0.20, 0.25, 0.30, 0.35, 0.40):
            av, at = [], []
            for r in BOTH:
                p, _ = find_peaks(S[r], height=H, distance=D)
                (av if SPLIT[r] == "validation" else at).append(ari(p, r))
            rows.append(dict(fam="fixed", sigma=sigma, D=D, param=f"H{H:.2f}",
                             val_ari=np.mean(av), train_ari=np.mean(at)))
        # adaptive quantile / mad
        for q in (0.85, 0.90, 0.93, 0.95):
            av, at = [], []
            for r in BOTH:
                H = np.quantile(S[r], q)
                p, _ = find_peaks(S[r], height=H, distance=D)
                (av if SPLIT[r] == "validation" else at).append(ari(p, r))
            rows.append(dict(fam="quant", sigma=sigma, D=D, param=f"q{q:.2f}",
                             val_ari=np.mean(av), train_ari=np.mean(at)))
        for k in (2.0, 2.5, 3.0):
            av, at = [], []
            for r in BOTH:
                med = np.median(S[r])
                H = med + k * np.median(np.abs(S[r] - med))
                p, _ = find_peaks(S[r], height=H, distance=D)
                (av if SPLIT[r] == "validation" else at).append(ari(p, r))
            rows.append(dict(fam="mad", sigma=sigma, D=D, param=f"k{k:.1f}",
                             val_ari=np.mean(av), train_ari=np.mean(at)))

df = pd.DataFrame(rows).sort_values("val_ari", ascending=False)
print("=== smooth/threshold grid, top 20 by val ===")
print(df.head(20).round(4).to_string(index=False))
print("\n=== same grid ranked by train (confirmation) ===")
print(df.sort_values("train_ari", ascending=False).head(10).round(4).to_string(index=False))

# per-record detail for a couple of leading settings
print("\n=== per-record ARI, leading settings ===")
lead = [("sigma7_q0.90_D54", 7, "q", 0.90, 54), ("sigma10_q0.90_D54", 10, "q", 0.90, 54),
        ("sigma5_H0.30_D54", 5, "H", 0.30, 54), ("sigma10_H0.30_D54", 10, "H", 0.30, 54)]
tab = {}
for nm, sg, kind, par, D in lead:
    col = []
    for r in VAL:
        S = sm(r, sg)
        H = par if kind == "H" else np.quantile(S, par)
        p, _ = find_peaks(S, height=H, distance=D)
        col.append(round(ari(p, r), 3))
    tab[nm] = col
print(pd.DataFrame(tab, index=[f"rec{r}" for r in VAL]).to_string())

# penalised selection
print("\n=== penalised selection (candidates = local maxima at h=0, gap L=D) ===")
rows2 = []
for sigma in (2, 5, 8, 12):
    S = {r: sm(r, sigma) for r in BOTH}
    cand = {r: find_peaks(S[r], distance=5)[0] for r in BOTH}
    for lam in (0.30, 0.40, 0.50, 0.60, 0.70, 0.85):
        for D in (54, 78):
            av, at = [], []
            for r in BOTH:
                p = greedy(S[r], cand[r], D, lam)
                (av if SPLIT[r] == "validation" else at).append(ari(p, r))
            rows2.append(dict(fam="greedy", sigma=sigma, D=D, param=f"lam{lam:.2f}",
                              val_ari=np.mean(av), train_ari=np.mean(at)))
d2 = pd.DataFrame(rows2).sort_values("val_ari", ascending=False)
print(d2.head(12).round(4).to_string(index=False))

out = pd.concat([df, d2], ignore_index=True)
out.to_csv(os.path.join(DATA, "up_p1a_explore2_grid.csv"), index=False, encoding="utf-8")