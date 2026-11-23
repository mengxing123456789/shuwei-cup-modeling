import os
# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Step 2 exploration -- VALIDATION and TRAIN ONLY. Test scores are never read here.

Questions:
  A. what does the score distribution look like per record (quantiles, peak counts);
  B. how much ARI is on the table if K were known (top-m peak curve, oracle-ish);
  C. do label-free per-record adaptive thresholds beat the global height on val,
     and does the same direction hold on the 55 train records.
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from scipy.signal import find_peaks, peak_prominences

import p1a_gpu_segmentation as M

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
Z = np.load(os.path.join(DATA, "up_p1a_scores.npz"), allow_pickle=True)
META = json.loads(str(Z["meta"][0]))
REC = [int(x) for x in Z["rec"]]
SC = {r: Z["score"][i].astype(np.float64) for i, r in enumerate(REC)}
IN = {r: Z["inside"][i] for i, r in enumerate(REC)}
HD = {r: Z["hard"][i] for i, r in enumerate(REC)}
SB = {r: Z["sub"][i] for i, r in enumerate(REC)}
SPLIT = {r: META["split"][str(r)] for r in REC}
DUR = {r: META["dur"][str(r)] for r in REC}
VAL = [r for r in REC if SPLIT[r] == "validation"]
TR = [r for r in REC if SPLIT[r] == "train"]
D0 = 54


def smooth(s, sigma=2.0):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(s, k, mode="same")


def labels_from(peaks, n):
    if len(peaks) == 0:
        return np.zeros(n, int)
    return np.searchsorted(peaks, np.arange(n), side="right")


def ari_of(peaks, r):
    lab = labels_from(np.asarray(peaks), len(SC[r]))
    ins = IN[r]
    y = SB[r][ins]
    if len(np.unique(y)) < 2:
        return np.nan
    return float(adjusted_rand_score(y, lab[ins]))


def peaks_at(r, height, dist, prominence_frac=None):
    s = smooth(SC[r])
    p, _ = find_peaks(s, height=height, distance=max(int(dist), 1))
    if prominence_frac is not None and len(p):
        prom = peak_prominences(s, p)[0]
        keep = prom >= prominence_frac * prom.max()
        p = p[keep]
    return p


def report(name, rows):
    df = pd.DataFrame(rows)
    print(f"\n=== {name} ===")
    print(df.round(4).to_string(index=False))
    return df


print("record diagnostics (val/train)")
diag = []
for r in VAL + TR:
    s = smooth(SC[r])
    q = np.quantile(s, [0.5, 0.8, 0.9, 0.95, 0.99])
    med = np.median(s)
    mad = np.median(np.abs(s - med))
    p0 = peaks_at(r, 0.0, D0)
    diag.append(dict(rec=r, split=SPLIT[r], n=len(s), dur=round(DUR[r], 1),
                     K_true=len(set(SB[r][IN[r]])), n_peaks_h0=len(p0),
                     q50=med, q80=q[1], q90=q[2], q95=q[3], q99=q[4], max=s.max(),
                     med_plus_3mad=med + 3 * mad, std=s.std()))
diag = pd.DataFrame(diag)
print(diag.head(14).round(4).to_string(index=False))
print("\nquantile reference (over all val/train records):")
print(diag[["q50", "q80", "q90", "q95", "q99", "med_plus_3mad"]].describe().round(4).to_string())

# ---- A. baseline rule on val + train ----
rows = []
for r in VAL + TR:
    p = peaks_at(r, 0.30, D0)
    rows.append(dict(rec=r, split=SPLIT[r], K=len(set(SB[r][IN[r]])), n_pred=len(p), ari=ari_of(p, r)))
a = pd.DataFrame(rows)
print(f"\nbaseline (H=0.30,D=54)  val mean ARI {a[a.split=='validation'].ari.mean():.4f} "
      f"| train mean ARI {a[a.split=='train'].ari.mean():.4f}")
print(a[a.split == "validation"].round(3).to_string(index=False))

# ---- B. top-m peak curve: is the ceiling high if K were right? ----
print("\n=== top-m by peak height (D=54, no height threshold): best m per record ===")
curve = []
for r in VAL + TR:
    p0 = peaks_at(r, 0.0, D0)
    s = smooth(SC[r])
    prom = peak_prominences(s, p0)[0] if len(p0) else np.array([])
    best_h = (-1, None)
    best_p = (-1, None)
    for m in range(1, min(len(p0), 20) + 1):
        top_h = np.sort(p0[np.argsort(-s[p0])[:m]])
        top_p = np.sort(p0[np.argsort(-prom)[:m]])
        ah, ap = ari_of(top_h, r), ari_of(top_p, r)
        if ah > best_h[0]:
            best_h = (ah, m)
        if ap > best_p[0]:
            best_p = (ap, m)
    kt = len(set(SB[r][IN[r]])) - 1
    a_kt = ari_of(np.sort(p0[np.argsort(-s[p0])[:kt]]) if len(p0) >= kt else p0, r)
    curve.append(dict(rec=r, split=SPLIT[r], K_minus1=kt, n_cand=len(p0),
                      best_ari_h=best_h[0], best_m_h=best_h[1],
                      best_ari_prom=best_p[0], best_m_prom=best_p[1],
                      ari_topKtrue=a_kt))
c = pd.DataFrame(curve)
print(c[c.split == "validation"].round(3).to_string(index=False))
print("val median best-by-height", round(c[c.split == "validation"].best_ari_h.median(), 3),
      "| train median", round(c[c.split == "train"].best_ari_h.median(), 3))

# ---- C. adaptive rule grid on val (and same numbers on train) ----
print("\n=== adaptive rules ===")
rules = []
for q in (0.80, 0.85, 0.90, 0.92, 0.95, 0.97, 0.98):
    rules.append(("q%.2f" % q, dict(kind="quantile", q=q)))
for k in (2.0, 2.5, 3.0, 3.5, 4.0, 4.5):
    rules.append(("mad%.1f" % k, dict(kind="mad", k=k)))
for p in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
    rules.append(("prom%.2f" % p, dict(kind="prom", p=p)))
for pf in (0.15, 0.25, 0.35):
    rules.append(("q90+prom%.2f" % pf, dict(kind="qprom", q=0.90, p=pf)))

grid = []
for name, rule in rules:
    for D in (D0, 66, 78, 90):
        av, at, nv = [], [], []
        for r in VAL + TR:
            s = smooth(SC[r])
            if rule["kind"] == "quantile":
                H = float(np.quantile(s, rule["q"]))
            elif rule["kind"] == "mad":
                med = np.median(s)
                H = float(med + rule["k"] * np.median(np.abs(s - med)))
            elif rule["kind"] in ("prom", "qprom"):
                H = float(np.quantile(s, rule["q"])) if rule["kind"] == "qprom" else 0.0
            p, _ = find_peaks(s, height=H, distance=D)
            if rule["kind"] in ("prom", "qprom") and len(p):
                prom = peak_prominences(s, p)[0]
                p = p[prom >= rule["p"] * prom.max()]
            ar = ari_of(p, r)
            (av if SPLIT[r] == "validation" else at).append(ar)
            nv.append(len(p))
        grid.append(dict(rule=name, D=D, val_ari=float(np.mean(av)), train_ari=float(np.mean(at)),
                         val_pred=float(np.mean([x for x, r in zip(nv, VAL + TR) if SPLIT[r] == "validation"]))))
g = pd.DataFrame(grid).sort_values("val_ari", ascending=False)
print(g.head(18).round(4).to_string(index=False))
print("\ntrain ranking (confirmation, top 8):")
print(g.sort_values("train_ari", ascending=False).head(8).round(4).to_string(index=False))
g.to_csv(os.path.join(DATA, "up_p1a_explore_grid.csv"), index=False, encoding="utf-8")

# ---- D. K vs duration on train (label prior) ----
print("\n=== K vs duration on train ===")
ktr = np.array([len(set(SB[r][IN[r]])) for r in TR], float)
dtr = np.array([DUR[r] for r in TR], float)
A = np.vstack([np.ones_like(dtr), dtr]).T
coef, *_ = np.linalg.lstsq(A, ktr, rcond=None)
pred = A @ coef
print(f"OLS K = {coef[0]:.3f} + {coef[1]:.4f}*dur_s ; train MAE {np.mean(np.abs(pred-ktr)):.2f} "
      f"| R2 {1 - np.sum((pred-ktr)**2)/np.sum((ktr-ktr.mean())**2):.3f}")
for r in VAL:
    print(f"  val rec{r}: dur {DUR[r]:.0f}s -> K_hat {coef[0]+coef[1]*DUR[r]:.2f} (K_true {len(set(SB[r][IN[r]]))})")