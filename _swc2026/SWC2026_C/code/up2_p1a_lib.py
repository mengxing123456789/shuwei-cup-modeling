# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 shared library: data, labels, metrics, decoders.

Reuses the v1 data pipeline (p1a_gpu_segmentation.load_arrays / build_labels) so the
frames, the train-only normalisation, the annotated-region masks and the segment ids
are byte-identical to the published baseline.  Nothing here handles test-specific
tuning: every selection routine takes an explicit list of records and the callers
pass TRAIN/VALIDATION only.

PREREGISTRATION (written before any v2 training run, see 35-P1a-v2结果.md):
  gate: test mean ARI >= 0.62 AND test mean boundary F1 >= 0.30
  metric bf1 = up_p1a_final.py definition (tolerance +-2 frames, greedy nearest match)
  selection: hyper-parameters and config choice on validation only; test evaluated once
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences
from sklearn.metrics import adjusted_rand_score

import p1a_gpu_segmentation as M

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJ, "data")
MODELS = os.path.join(PROJ, "models")
CACHE = os.path.join(DATA, "up2_p1a_cache.npz")


# ------------------------------------------------------------------ data ----
def build_cache(verbose=True):
    """Build per-record arrays once; identical to the v1 pipeline."""
    z, recs, segs, Xraw = M.load_arrays()
    tr_mask = np.isin(z["rec"], list(recs[recs.split == "train"].rec))
    mu, sd = Xraw[tr_mask].mean(0), Xraw[tr_mask].std(0) + 1e-6
    X = np.clip((Xraw - mu) / sd, -8, 8).astype(np.float32)

    out = dict(rec=[], X=[], t=[], inside=[], sub=[], hard=[], soft=[], bad=[], split=[],
               dataset=[], env=[], dur=[], n=[])
    ri = recs.set_index("rec")
    for r in recs.rec:
        ii = np.where(z["rec"] == r)[0]
        t = z["t"][ii].astype(np.float64)
        hard, soft, inside = M.build_labels(segs, int(r), t, len(ii))
        sub = np.full(len(ii), -1, int)
        for _, s in segs[segs.rec == r].iterrows():
            sub[(t >= s.start) & (t < s.end)] = int(s.seg)
        bad = np.stack([z["badL"][ii], z["badR"][ii]], 1).astype(np.float32)
        out["rec"].append(int(r))
        out["X"].append(X[ii])
        out["t"].append(t)
        out["inside"].append(np.asarray(inside))
        out["sub"].append(sub)
        out["hard"].append(np.asarray(hard, int))
        out["soft"].append(np.asarray(soft, np.float32))
        out["bad"].append(bad)
        out["split"].append(str(ri.loc[r, "split"]))
        out["dataset"].append(str(ri.loc[r, "dataset"]))
        out["env"].append(str(ri.loc[r, "env"]))
        out["dur"].append(round(float(ri.loc[r, "dur"]), 4))
        out["n"].append(int(len(ii)))
    if verbose:
        print(f"cache: {len(out['rec'])} records, dim {X.shape[1]}, "
              f"{int(tr_mask.sum())} train frames", flush=True)
        print("split counts:", {s: out["split"].count(s) for s in ("train", "validation", "test")},
              flush=True)
    save = {k: np.array(v, dtype=object) for k, v in out.items()}
    save["mu"] = mu
    save["sd"] = sd
    np.savez_compressed(CACHE, **save)
    out["_pos"] = {int(r): i for i, r in enumerate(out["rec"])}
    return out


def load_cache(rebuild=False):
    if rebuild or not os.path.exists(CACHE):
        return build_cache()
    z = np.load(CACHE, allow_pickle=True)
    keys = ["rec", "X", "t", "inside", "sub", "hard", "soft", "bad", "split",
            "dataset", "env", "dur", "n"]
    d = {k: list(z[k]) for k in keys}
    d["rec"] = [int(r) for r in d["rec"]]
    d["split"] = [str(s) for s in d["split"]]
    d["dataset"] = [str(s) for s in d["dataset"]]
    d["env"] = [str(s) for s in d["env"]]
    d["dur"] = [float(x) for x in d["dur"]]
    d["n"] = [int(x) for x in d["n"]]
    d["_pos"] = {int(r): i for i, r in enumerate(d["rec"])}
    return d


def pos(d, r):
    return d["_pos"][int(r)]


def ids(d, split):
    return [r for r, s in zip(d["rec"], d["split"]) if s == split]


# --------------------------------------------------------------- scoring ----
def labels_from_peaks(peaks, n):
    if len(peaks) == 0:
        return np.zeros(n, int)
    return np.searchsorted(np.asarray(peaks, int), np.arange(n), side="right")


def ari_of(peaks, d, r):
    """ARI on the annotated region, exactly as up_p1a_final.py."""
    i = pos(d, r)
    lab = labels_from_peaks(peaks, d["n"][i])
    ins = d["inside"][i]
    y = d["sub"][i][ins]
    if len(np.unique(y)) <= 1:
        return np.nan
    return float(adjusted_rand_score(y, lab[ins]))


def true_bounds(d, r):
    """True change points as frame indices (the inside mask is a contiguous prefix)."""
    i = pos(d, r)
    y = d["sub"][i][d["inside"][i]]
    return (np.where(np.diff(y) != 0)[0] + 1).astype(int)


def bf1_of(peaks, d, r, tol=2):
    """up_p1a_final.py boundary F1: +-tol frames, greedy nearest match."""
    true = true_bounds(d, r)
    pred = np.asarray(peaks, int)
    if len(true) == 0 and len(pred) == 0:
        return np.nan
    hit_t = sum(1 for t in true if len(pred) and np.min(np.abs(pred - t)) <= tol)
    hit_p = sum(1 for p in pred if len(true) and np.min(np.abs(true - p)) <= tol)
    if hit_t + hit_p == 0:
        return 0.0
    prec = hit_p / max(1, len(pred))
    rec = hit_t / max(1, len(true))
    return float(2 * prec * rec / max(1e-12, prec + rec))


def bf1_hard(peaks, d, r, tol=5):
    """Secondary diagnostic: build_labels hard boundaries, +-tol greedy (v1 GPU metric)."""
    i = pos(d, r)
    true = np.asarray(d["hard"][i], int)
    pred = np.asarray(peaks, int)
    if len(pred) == 0 or len(true) == 0:
        return 0.0
    hit_t = sum(1 for t in true if len(pred) and np.min(np.abs(pred - t)) <= tol)
    hit_p = sum(1 for p in pred if len(true) and np.min(np.abs(true - p)) <= tol)
    if hit_t + hit_p == 0:
        return 0.0
    prec, rec = hit_p / len(pred), hit_t / len(true)
    return float(2 * prec * rec / max(1e-12, prec + rec))


def score_record(peaks, d, r):
    i = pos(d, r)
    kt = int(len(np.unique(d["sub"][i][d["inside"][i]])) - 1)
    return dict(n_pred=int(len(peaks)), k_true=kt, k_err=int(len(peaks) - kt),
                ari=ari_of(peaks, d, r), bf1=bf1_of(peaks, d, r),
                bf1_hard5=bf1_hard(peaks, d, r))


def eval_peaks(peaks_by_rec, d, recs, label=""):
    rows = [dict(rec=r, **score_record(peaks_by_rec[r], d, r)) for r in recs]
    df = pd.DataFrame(rows)
    return dict(label=label, mean_ari=float(np.nanmean(df.ari)),
                mean_bf1=float(np.nanmean(df.bf1)),
                mean_bf1_hard5=float(np.nanmean(df.bf1_hard5)),
                mean_k_abs_err=float(np.nanmean(np.abs(df.k_err))),
                mean_npred=float(df.n_pred.mean()),
                per_record=rows, frame=df)


def by_env(rows, d):
    out = {}
    for row in rows:
        e = d["env"][pos(d, row["rec"])]
        o = out.setdefault(e, dict(n=0, ari=[], bf1=[]))
        o["n"] += 1
        o["ari"].append(row["ari"])
        o["bf1"].append(row["bf1"])
    return {e: dict(n=o["n"], mean_ari=float(np.nanmean(o["ari"])),
                    mean_bf1=float(np.nanmean(o["bf1"]))) for e, o in out.items()}


# -------------------------------------------------------------- smoothing ---
def smooth(score, sigma, mode="nearest"):
    s = np.asarray(score, np.float64)
    if sigma is None or sigma <= 0:
        return s
    return gaussian_filter1d(s, sigma, mode=mode)


# -------------------------------------------------------------- decoders ---
def decode_legacy(score, sigma=2.0, kind="q", param=0.85, dist=54):
    """v1 rule family (fixed height / quantile / MAD + find_peaks)."""
    s = smooth(score, sigma)
    if kind == "H":
        h = float(param)
    elif kind == "q":
        h = float(np.quantile(s, param))
    else:
        med = np.median(s)
        h = float(med + param * np.median(np.abs(s - med)))
    p, _ = find_peaks(s, height=h, distance=max(int(dist), 1))
    return p


def _candidates(score, cand_dist=5, prom_floor=0.0):
    """Local maxima of the smoothed score with a prominence floor (record-local)."""
    s = np.asarray(score, np.float64)
    p, _ = find_peaks(s, distance=max(int(cand_dist), 1))
    if len(p) == 0:
        return np.array([], int)
    prom = peak_prominences(s, p)[0]
    keep = prom >= prom_floor
    return p[keep]


def zscore(score):
    s = np.asarray(score, np.float64)
    med = np.median(s)
    iqr = np.quantile(s, 0.75) - np.quantile(s, 0.25) + 1e-9
    return (s - med) / iqr


def decode_dp(score, sigma=1.0, min_len=20, lam=0.5, cand_dist=5, prom_floor=0.02,
              shift=0, k_hat=None, k_pen=0.0, n=None):
    """DP over local maxima: maximise sum(z_i - lam) with spacing >= min_len.

    lam is a per-boundary penalty on the IQR-normalised score, so one value works
    across records.  k_hat (optional) adds a quadratic deviation penalty; the chosen
    peaks are shifted by `shift` frames (train-calibrated localisation offset).
    This is the "minimum segment length + segment-count penalty" decoder.
    """
    s = smooth(score, sigma)
    z = zscore(s)
    cand = _candidates(s, cand_dist, prom_floor)
    if len(cand) == 0:
        return np.array([], int)
    C = len(cand)
    val = np.full(C, -np.inf)
    prev = np.full(C, -1, int)
    cnt = np.zeros(C, int)
    for i in range(C):
        val[i] = z[cand[i]] - lam
        cnt[i] = 1
        best, bi, bc = -np.inf, -1, 0
        for j in range(i):
            if cand[i] - cand[j] >= min_len and val[j] > best:
                best, bi, bc = val[j], j, cnt[j]
        if best > 0:
            val[i] = z[cand[i]] - lam + best
            prev[i] = bi
            cnt[i] = bc + 1
    val2 = val - k_pen * (cnt - k_hat) ** 2 if (k_hat is not None and k_pen > 0) else val
    if val2.max() <= 0:
        return np.array([], int)
    i = int(np.argmax(val2))
    out = []
    while i >= 0:
        out.append(cand[i])
        i = prev[i]
    p = np.sort(np.array(out, int))
    if shift:
        p = np.clip(p + int(shift), 0, (n - 1) if n else None)
    return p


def decode_topk(score, k, sigma=1.0, min_len=20, cand_dist=5, shift=0, n=None):
    """Take the k strongest local maxima, enforcing spacing with a greedy pass."""
    s = smooth(score, sigma)
    cand = _candidates(np.asarray(s, np.float64), cand_dist, 0.0)
    if len(cand) == 0:
        return np.array([], int)
    order = cand[np.argsort(-np.asarray(s)[cand])]
    chosen = []
    for p in order:
        if all(abs(p - c) >= min_len for c in chosen):
            chosen.append(int(p))
        if len(chosen) >= k:
            break
    out = np.sort(np.array(chosen, int))
    if shift:
        out = np.clip(out + int(shift), 0, (n - 1) if n else None)
    return out


def decode_hybrid(score, sigma=1.0, lam=0.5, min_len=20, k_hat=None, k_pen=0.6,
                  cand_dist=5, prom_floor=0.02, shift=0, n=None):
    """DP with the K prior folded in as a count penalty (task brief: count penalty)."""
    return decode_dp(score, sigma, min_len, lam, cand_dist, prom_floor, shift,
                     k_hat, k_pen, n)


# ------------------------------------------------------------- K prior ------
def k_features(score, dur, n, bad=None):
    s = smooth(score, 1.0)
    z = zscore(s)
    q90, q80, q30 = (float(np.quantile(s, q)) for q in (0.90, 0.80, 0.30))
    npred_q90 = len(find_peaks(s, height=q90, distance=15)[0])
    npred_q80 = len(find_peaks(s, height=q80, distance=15)[0])
    npred_q30 = len(find_peaks(s, height=q30, distance=15)[0])
    bad_rate = float(np.mean(bad)) if bad is not None else 0.0
    return np.array([np.log(max(dur, 1e-3)), npred_q90, npred_q80, npred_q30,
                     float(np.mean(z)), float(np.max(z)), float(np.mean(s > 0.5)),
                     bad_rate, np.log(max(n, 1))], float)


def fit_k_ridge(Xk, K, alpha=3.0):
    """Closed-form ridge with intercept; returns (mu, sd, coef, b)."""
    Xk = np.asarray(Xk, float)
    mu, sd = Xk.mean(0), Xk.std(0) + 1e-9
    Z = (Xk - mu) / sd
    A = np.hstack([np.ones((len(Z), 1)), Z])
    pen = alpha * np.eye(A.shape[1])
    pen[0, 0] = 0.0
    w = np.linalg.solve(A.T @ A + pen, A.T @ np.asarray(K, float))
    return mu, sd, w[1:], float(w[0])


def predict_k(model, x):
    mu, sd, coef, b = model
    return float(b + ((np.asarray(x, float) - mu) / sd) @ coef)


def fit_k_offset(d, recs, score_by_rec, radius=15):
    """Train-only localisation offset: median (true - nearest peak) over boundaries."""
    offs = []
    for r in recs:
        cand = _candidates(smooth(score_by_rec[r], 1.0), 5, 0.02)
        if len(cand) == 0:
            continue
        for t in true_bounds(d, r):
            j = cand[np.argmin(np.abs(cand - t))]
            if abs(j - t) <= radius:
                offs.append(int(t - j))
    if not offs:
        return 0, dict(n=0, median=0.0, mean=0.0, mad=0.0)
    offs = np.asarray(offs, int)
    return int(np.round(np.median(offs))), dict(n=int(len(offs)),
                                                median=float(np.median(offs)),
                                                mean=float(np.mean(offs)),
                                                mad=float(np.median(np.abs(offs - np.median(offs)))))


# ------------------------------------------------------- fast DP (O(C)) -----
def dp_prep(score, sigma=1.0, cand_dist=5, prom_floor=0.02):
    """Everything decode_dp does before the DP: sigma smoothing + IQR z + candidates."""
    s = smooth(score, sigma)
    return zscore(s), _candidates(s, cand_dist, prom_floor)


def dp_fast(z, cand, min_len, lam, shift=0, k_hat=None, k_pen=0.0, n=None):
    """Same problem as decode_dp, solved in O(C) with an incremental prefix maximum.

    val[j] is final by the time j becomes eligible (eligibility needs cand[j] < cand[i]),
    and the eligibility window is monotone in i, so one forward pointer over j maintains
    max(val[:j]) exactly.  Verified equal to decode_dp on random signals in up2_p1a_select.
    """
    cand = np.asarray(cand, int)
    C = len(cand)
    if C == 0:
        return np.array([], int)
    val = np.empty(C, np.float64)
    prev = np.full(C, -1, int)
    cnt = np.zeros(C, int)
    best_v, best_i, best_c, j = -np.inf, -1, 0, 0
    for i in range(C):
        while j < i and cand[i] - cand[j] >= min_len:
            if val[j] > best_v:
                best_v, best_i, best_c = val[j], j, cnt[j]
            j += 1
        base = z[cand[i]] - lam
        if best_v > 0:
            val[i], prev[i], cnt[i] = base + best_v, best_i, best_c + 1
        else:
            val[i], prev[i], cnt[i] = base, -1, 1
    obj = val - k_pen * (cnt - k_hat) ** 2 if (k_hat is not None and k_pen > 0) else val
    if obj.max() <= 0:
        return np.array([], int)
    i = int(np.argmax(obj))
    out = []
    while i >= 0:
        out.append(int(cand[i]))
        i = int(prev[i])
    p = np.sort(np.array(out, int))
    if shift:
        p = np.clip(p + int(shift), 0, (n - 1) if n else None)
    return p


# --------------------------------------------------------------- dumping ----
def save_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)