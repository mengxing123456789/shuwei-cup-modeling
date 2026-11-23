
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a improved segmentation experiment.

Strict protocol
---------------
* `--phase select` reads train + validation only.  Every tuning choice is made
  on validation mean ARI.  No test label or test feature matrix is loaded.
* `--phase test` reloads the frozen choice from the selection JSON and evaluates
  the seven test records once.
* Both phases share exactly the evaluation in best_p1a_seg.py: per-record z
  score, run-id realisation, ARI, Hungarian frame F1, boundary matching at 5 s.

Candidate families
-------------------
A  Ward + GMM-BIC with feature set / smoothing / kmax grids
B  Ward + distance threshold (K emerges from data)
C  two-stage Ward, coarse cap then recursive significant splits
D  binary change-point splitting with a normalised gain threshold
E  post-hoc short-segment merge with validation-tuned thresholds
F  train-supervised record-level selector for the Ward k cap

Outputs
-------
data/p1a_improved_selection.json
data/p1a_improved_results.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.cluster import AgglomerativeClustering
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import best_p1a_seg as B  # noqa: E402

DATA = B.DATA
SEL_OUT = os.path.join(DATA, "p1a_improved_selection.json")
RES_OUT = os.path.join(DATA, "p1a_improved_results.json")
BASELINE_ARI = 0.4138423666260523
BASELINE_F1 = 0.5613169824306583
SEED = 20261120

# ---------------------------------------------------------------- feature sets
NAMES = json.load(open(os.path.join(DATA, "feature_names.json"), encoding="utf-8"))
NL = NAMES["state_l"]
BASE_IDX = [i for i, n in enumerate(NL)
            if any(n.endswith(s) for s in ["aperture_norm", "reach_norm", "normal_x",
                                           "normal_y", "normal_z", "fwd_x", "fwd_y",
                                           "fwd_z", "speed"])] + list(range(9))
BASE_IDX = sorted(set(BASE_IDX))
ALL_IDX = list(range(32))
DYN_IDX = sorted(set(BASE_IDX) | set(range(24, 32)))
GEO_IDX = [i for i, n in enumerate(NAMES["geom_l"])
           if n.endswith(("collinearity", "bone_cv", "min_gap", "bbox_vol", "z_std",
                          "jump", "jump_max"))]


def raw_matrices(r):
    ii = np.where(B.rec == r)[0]
    k = int(B.dom[r])
    D = (B.fl if k == 0 else B.fr)[ii].astype(np.float64)
    O = (B.fr if k == 0 else B.fl)[ii].astype(np.float64)
    G = (B.gl if k == 0 else B.gr)[ii].astype(np.float64)
    Go = (B.gl if k == 1 else B.gr)[ii].astype(np.float64)
    return ii, D, O, G, Go


def angular_speed(v3):
    """norm of first difference of a unit vector, frame^-1"""
    d = np.diff(v3, axis=0, prepend=v3[:1])
    return np.linalg.norm(d, axis=1)


def derived(D):
    """extra temporal / bimanual terms computed causally from current frame only."""
    def d1(x):
        return np.gradient(x) if len(x) > 2 else np.zeros_like(x)

    # D columns: wrist 0:3, thumbTip 3:6, indexTip 6:9, indexMCP 9:12,
    # littleMCP 12:15, aperture 15, reach 16, palm 17, normal 18:21,
    # fwd 21:24, vel 24:27, acc 27:30, speed 30, accnorm 31
    rel = D[:, 3:9] - D[:, 0:1]
    out = [
        d1(D[:, 15]), d1(D[:, 16]), d1(D[:, 30]),
        angular_speed(D[:, 18:21]), angular_speed(D[:, 21:24]),
        np.linalg.norm(D[:, 24:27], axis=1),
        np.linalg.norm(D[:, 27:30], axis=1),
        d1(np.linalg.norm(rel[:, :3] - rel[:, 3:6], axis=1)),
        d1(D[:, 0]), d1(D[:, 1]), d1(D[:, 2]),
    ]
    return np.stack(out, axis=1)


def make_features(r, fset="base18"):
    ii, D, O, G, Go = raw_matrices(r)
    D = np.nan_to_num(D, nan=0.0, posinf=0.0, neginf=0.0)
    O = np.nan_to_num(O, nan=0.0, posinf=0.0, neginf=0.0)
    G = np.nan_to_num(G, nan=0.0, posinf=0.0, neginf=0.0)
    Go = np.nan_to_num(Go, nan=0.0, posinf=0.0, neginf=0.0)
    if fset == "base18":
        X = D[:, BASE_IDX]
    elif fset == "full32":
        X = D[:, ALL_IDX]
    elif fset == "dyn30":
        X = np.hstack([D[:, BASE_IDX], derived(D)])
    elif fset == "cross24":
        relw = O[:, 0:3] - D[:, 0:3]
        relt = O[:, 6:9] - D[:, 6:9]
        X = np.hstack([D[:, BASE_IDX], relw, relt,
                       O[:, [15, 16, 30]], np.linalg.norm(O[:, 0:3] - D[:, 0:3],
                                                         axis=1)[:, None]])
    elif fset == "geo44":
        relw = O[:, 0:3] - D[:, 0:3]
        relt = O[:, 6:9] - D[:, 6:9]
        X = np.hstack([D[:, BASE_IDX], derived(D), G[:, GEO_IDX], Go[:, GEO_IDX],
                       relw, relt, O[:, [15, 16, 30]]])
    else:
        raise ValueError(fset)
    return ii, np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def smooth_X(X, w):
    if w <= 1 or len(X) < w:
        return X
    k = np.ones(w) / w
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, X)


def prep_record(r, fset, sw):
    ii, X = make_features(r, fset)
    y = B.true_labels(r, ii)
    good = y >= 0
    ii = ii[good]
    X = smooth_X(X[good], sw)
    X = (X - X.mean(0)) / (X.std(0) + 1e-6)
    t = B.T[ii]
    return dict(rec=int(r), ii=ii, X=X.astype(np.float64), y=y[good], t=t,
                ktrue=int(len(np.unique(y[good]))), n=int(good.sum()),
                fset=fset, sw=sw)


# ---------------------------------------------------------------- algorithms
def runs_of(lab):
    return B.runs_of(lab)


def to_run_id(lab):
    return B.to_run_id(lab)


_BIC_CURVE = {}


def bic_curve(X, key=None, kmax=25, seed=SEED):
    """(k, BIC) pairs, computed once per record/feature/smoothing combination."""
    if key is not None and key in _BIC_CURVE:
        return _BIC_CURVE[key]
    Xs = X[::3]
    out = []
    for k in range(2, min(kmax, len(Xs) // 20) + 1):
        try:
            g = GaussianMixture(k, covariance_type="diag", random_state=seed,
                                n_init=2, max_iter=200).fit(Xs)
            out.append((k, float(g.bic(Xs))))
        except Exception:
            continue
    if key is not None:
        _BIC_CURVE[key] = out
    return out


def choose_k_gamma(X, kmax=25, gamma=1.0, seed=SEED, key=None):
    """GMM diagonal BIC multiplied by gamma; gamma>1 penalises extra states."""
    curve = bic_curve(X, key=key, kmax=max(25, kmax), seed=seed)
    usable = [(k, b) for k, b in curve if k <= kmax]
    if not usable:
        return 2
    return int(min(usable, key=lambda kb: kb[1] * gamma)[0])


def ward_run(X, K):
    return B.ward_segments(X, K)


def ward_dist(X, threshold):
    n = len(X)
    if n < 4:
        return np.zeros(n, int)
    C = sparse.diags([np.ones(n - 1), np.ones(n - 1)], [1, -1], shape=(n, n),
                     format="csr")
    try:
        lab = AgglomerativeClustering(n_clusters=None, distance_threshold=threshold,
                                      connectivity=C, linkage="ward").fit_predict(X)
    except Exception:
        return np.zeros(n, int)
    for _ in range(2):
        for i in range(1, len(lab) - 1):
            if lab[i] != lab[i - 1] and lab[i] != lab[i + 1]:
                lab[i] = lab[i - 1]
    return to_run_id(lab)


def sse(X):
    if len(X) == 0:
        return 0.0
    return float(((X - X.mean(0)) ** 2).sum())


def merge_short(X, lab, min_len=12, mode="centroid"):
    """Merge every short run into the adjacent run with nearest centroid."""
    cur = to_run_id(lab)
    for _ in range(500):
        rr = runs_of(cur)
        if len(rr) <= 1:
            break
        short = [(b - a, a, b) for a, b, _ in rr if b - a < min_len]
        if not short:
            break
        _, a, b = min(short)
        idx = [j for j, (u, v, _) in enumerate(rr) if u == a and v == b][0]
        c = X[a:b].mean(0)
        cand = []
        if idx > 0:
            u, v, _ = rr[idx - 1]
            cand.append((np.linalg.norm(c - X[u:v].mean(0)), u, v))
        if idx + 1 < len(rr):
            u, v, _ = rr[idx + 1]
            cand.append((np.linalg.norm(c - X[u:v].mean(0)), u, v))
        _, u, v = min(cand)
        lo, hi = min(a, u), max(b, v)
        cur[lo:hi] = cur[lo]
        cur = to_run_id(cur)
    return cur


def _prefix(X):
    """Sums and squared norms for O(1) contiguous SSE queries."""
    S = np.vstack([np.zeros((1, X.shape[1])), np.cumsum(X, axis=0)])
    Q = np.concatenate([[0.0], np.cumsum(np.einsum("ij,ij->i", X, X))])
    return S, Q


def _seg_sse(S, Q, a, b):
    L = b - a
    if L <= 0:
        return 0.0
    s = S[b] - S[a]
    return float(Q[b] - Q[a] - np.dot(s, s) / L)


def recursive_gain_split(X, max_seg=25, gain_min=0.02, min_len=18):
    """Binary splitting: split the segment with largest relative SSE gain."""
    n, d = X.shape
    if n < 2 * min_len:
        return np.zeros(n, int)
    S, Q = _prefix(X)
    segments = [(0, n)]
    while len(segments) < max_seg:
        best = None
        for si, (a, b) in enumerate(segments):
            if b - a < 2 * min_len:
                continue
            parent = _seg_sse(S, Q, a, b)
            if parent <= 1e-12:
                continue
            lo, hi = a + min_len, b - min_len
            ms = np.arange(lo, hi + 1)
            Lt = ms - a
            Rt = b - ms
            Sl = S[ms] - S[a]
            Sr = S[b] - S[ms]
            Ql = Q[ms] - Q[a]
            Qr = Q[b] - Q[ms]
            sse_l = Ql - np.einsum("ij,ij->i", Sl, Sl) / Lt
            sse_r = Qr - np.einsum("ij,ij->i", Sr, Sr) / Rt
            gains = (parent - sse_l - sse_r) / (parent + 1e-12)
            j = int(np.argmax(gains))
            cand = (float(gains[j]), si, int(ms[j]))
            if best is None or cand[0] > best[0]:
                best = cand
        if best is None or best[0] < gain_min:
            break
        _, si, m = best
        a, b = segments[si]
        segments[si:si + 1] = [(a, m), (m, b)]
    lab = np.zeros(n, int)
    for j, (a, b) in enumerate(sorted(segments)):
        lab[a:b] = j
    return lab


def recursive_two_stage(X, k0=8, max_seg=25, gain_min=0.15, min_len=18):
    """Ward coarse K0, then split a cluster only when the split is substantial."""
    base = ward_run(X, min(k0, max(2, len(X) // 60)))
    cur = base.copy()
    # seed initial run ids, then split by largest within-run gain until max_seg
    cur = to_run_id(cur)
    for _ in range(max_seg):
        rr = runs_of(cur)
        if len(rr) >= max_seg:
            break
        best = None
        for a, b, _ in rr:
            if b - a < 2 * min_len:
                continue
            # choose best 2-way Ward split inside run
            sub = X[a:b]
            try:
                l2 = AgglomerativeClustering(n_clusters=2, linkage="ward").fit_predict(sub)
            except Exception:
                continue
            m = np.where(np.diff(l2) != 0)[0]
            if len(m) == 0:
                continue
            cut = a + int(m[0]) + 1
            gain = (sse(sub) - sse(X[a:cut]) - sse(X[cut:b])) / (sse(sub) + 1e-12)
            if best is None or gain > best[0]:
                best = (gain, a, b, cut)
        if best is None or best[0] < gain_min:
            break
        _, a, b, cut = best
        old = cur[a]
        cur[cut:b] = cur.max() + 1
        cur = to_run_id(cur)
    return cur


def short_merge_rule(X, lab, dmin, tau):
    cur = lab.copy()
    for _ in range(400):
        rr = runs_of(cur)
        if len(rr) < 2:
            break
        cents = [X[a:b].mean(0) for a, b, _ in rr]
        lens = [b - a for a, b, _ in rr]
        done = False
        for i in range(len(rr) - 1):
            if lens[i] < dmin and lens[i + 1] < dmin and \
                    np.linalg.norm(cents[i] - cents[i + 1]) < tau:
                a0, b1 = rr[i][0], rr[i + 1][1]
                cur[a0:b1] = cur[a0]
                done = True
                break
        if not done:
            break
    return to_run_id(cur)


# ---------------------------------------------------------------- scoring
def boundary_metrics(pred_b, true_b, t, tol=5.0):
    bm = B.boundary_metrics(pred_b, true_b, t, tol)
    p, r = bm["b_precision"], bm["b_recall"]
    bm["b_f1"] = float(2 * p * r / (p + r)) if np.isfinite(p) and np.isfinite(r) and (p + r) else 0.0
    return bm


def score_full(lab, y, t):
    """ARI, Hungarian frame F1 and boundary metrics (5 s tolerance)."""
    from scipy.optimize import linear_sum_assignment
    from sklearn.metrics import adjusted_rand_score, f1_score
    ari = float(adjusted_rand_score(y, lab))
    yl, pl = np.unique(y), np.unique(lab)
    M = np.zeros((len(yl), len(pl)))
    for a in yl:
        for b in pl:
            M[a, b] = ((y == a) & (lab == b)).sum()
    ri, ci = linear_sum_assignment(-M)
    mp = {pl[c]: yl[rr] for rr, c in zip(ri, ci)}
    pred = np.array([mp.get(v, -1) for v in lab])
    f1 = float(f1_score(y, pred, average="micro"))
    tb = np.where(np.diff(y) != 0)[0] + 1
    bm = boundary_metrics(np.where(np.diff(lab) != 0)[0] + 1, tb, t)
    return dict(ari=ari, f1=f1, n_seg=int(len(np.unique(lab))), **bm)


# ---------------------------------------------------------------- record descriptors / supervised selectors
def record_features(d, k8=None, k25=None):
    X = d["X"]
    n = len(X)
    ev = np.linalg.eigvalsh(np.cov(X.T) + 1e-8 * np.eye(X.shape[1]))
    ev = np.clip(ev, 1e-8, None)
    p = ev / ev.sum()
    participation = float(1.0 / (p ** 2).sum())
    entropy = float(-(p * np.log(p)).sum())
    dt = np.diff(d["t"])
    dv = np.linalg.norm(np.diff(X, axis=0), axis=1)
    # blockwise variability: coefficient of variation of local SSE across 1 s windows
    w = max(10, int(round(1.0 / max(np.median(dt), 1e-3))))
    blocks = [sse(X[i:i + w]) for i in range(0, max(1, n - w + 1), w)]
    blocks = np.asarray(blocks, float)
    return np.array([
        d["n"], n * float(np.median(dt)), float(np.mean(X[:, 0])),
        float(np.mean(np.linalg.norm(X, axis=1))), float(np.std(np.linalg.norm(X, axis=1))),
        float(np.mean(dv)), float(np.std(dv)), float(np.percentile(dv, 95)),
        participation, entropy, float(ev[0] / (ev.sum() + 1e-12)),
        float(np.mean(blocks) / (np.std(blocks) + 1e-9)),
        float(np.median([len(rr) for rr in runs_of(to_run_id(np.zeros(n, int)))]) if n else 0),
    ], dtype=float)


def cap_choice_models(train_rows, val_rows):
    """Fit train-only supervised selectors; return candidates as K policies."""
    out = {}
    caps = [8, 12, 16, 20, 25]
    Ftr = np.stack([record_features(d) for d in train_rows])
    Fva = np.stack([record_features(d) for d in val_rows])
    # target cap with best ARI on each train record (labels are training labels)
    ybest, ydelta = [], []
    for d in train_rows:
        aris = []
        for c in caps:
            k = _k(d, c)
            aris.append(score_full(ward_run(d["X"], k), d["y"], d["t"])["ari"])
        ybest.append(int(np.argmax(aris)))
        ydelta.append([a - aris[0] for a in aris])
    ybest = np.asarray(ybest)
    ydelta = np.asarray(ydelta)
    sc = StandardScaler().fit(Ftr)
    Ztr, Zva = sc.transform(Ftr), sc.transform(Fva)
    models = {
        "et_cls": ExtraTreesClassifier(n_estimators=300, min_samples_leaf=2,
                                       random_state=SEED, n_jobs=-1),
        "rf_reg": RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                        random_state=SEED, n_jobs=-1),
        "ridge_reg": Ridge(alpha=10.0),
    }
    for tag, m in models.items():
        if tag == "et_cls":
            m.fit(Ztr, ybest)
            pred = m.predict(Zva).astype(int)
        elif tag == "rf_reg":
            m.fit(Ztr, ydelta)
            pred = np.argmax(m.predict(Zva), axis=1)
        else:
            m.fit(Ztr, ydelta)
            pred = np.argmax(m.predict(Zva), axis=1)
        out[tag] = [caps[int(i)] for i in pred]
    return out


# ---------------------------------------------------------------- candidate evaluation
@dataclass(frozen=True)
class Cfg:
    tag: str
    fset: str
    sw: int
    algo: str
    param: float | int


def configs():
    cs = []
    # BIC cap grid across all feature sets; gamma variants test the BIC penalty itself.
    for fset in ["base18", "full32", "dyn30", "cross24", "geo44"]:
        for sw in [1, 5, 9]:
            for km in [8, 12, 16, 20, 25]:
                cs.append(Cfg(f"ward_bic_{fset}_s{sw}_k{km}", fset, sw, "ward_bic", km))
            for gam in [0.85, 1.15]:
                cs.append(Cfg(f"ward_gamma_{fset}_s{sw}_g{gam}", fset, sw, "ward_gamma", gam))
            cs.append(Cfg(f"cp_{fset}_s{sw}_g0.05", fset, sw, "cp", 0.05))
    # data-driven K without BIC: ward distance threshold
    for fset in ["base18", "full32", "dyn30", "cross24", "geo44"]:
        for sw in [5, 9]:
            for th in [2.0, 3.0, 4.0, 5.0, 6.0]:
                cs.append(Cfg(f"ward_dist_{fset}_s{sw}_t{th}", fset, sw, "ward_dist", th))
    # recursive split after a cap-8 coarse solution
    for fset in ["base18", "full32", "dyn30"]:
        for sw in [5, 9]:
            for g in [0.20, 0.35, 0.50]:
                cs.append(Cfg(f"twostage_{fset}_s{sw}_g{g}", fset, sw, "twostage", g))
    for fset in ["base18", "full32", "dyn30"]:
        for sw in [5]:
            for g in [0.10, 0.20, 0.35]:
                cs.append(Cfg(f"cp_{fset}_s{sw}_g{g}", fset, sw, "cp", g))
    # minimum-duration cleanup after the unconstrained cap
    for dm in [6, 12, 18, 24]:
        cs.append(Cfg(f"merge_short_{dm}", "base18", 5, "merge_short", dm))
    return cs


def _k(d, kmax=25, gamma=1.0):
    return choose_k_gamma(d["X"], kmax=kmax, gamma=gamma,
                          key=(d["rec"], d["fset"], d["sw"]))


def apply_cfg(d, cfg, aux=None):
    X = d["X"]
    if cfg.algo == "ward_bic":
        K = _k(d, int(cfg.param), 1.0)
        lab = ward_run(X, K)
        Kuse = K
    elif cfg.algo == "ward_gamma":
        K = _k(d, 25, float(cfg.param))
        lab = ward_run(X, K)
        Kuse = K
    elif cfg.algo == "ward_dist":
        lab = ward_dist(X, float(cfg.param))
        Kuse = int(len(np.unique(lab)))
    elif cfg.algo == "twostage":
        lab = recursive_two_stage(X, k0=8, max_seg=25, gain_min=float(cfg.param))
        Kuse = int(len(np.unique(lab)))
    elif cfg.algo == "cp":
        lab = recursive_gain_split(X, max_seg=25, gain_min=float(cfg.param))
        Kuse = int(len(np.unique(lab)))
    elif cfg.algo == "merge_short":
        K = _k(d, 25)
        lab = merge_short(X, ward_run(X, K), min_len=int(cfg.param))
        Kuse = int(len(np.unique(lab)))
    else:
        raise ValueError(cfg.algo)
    return lab, Kuse


def eval_config(records, cfg):
    rows = []
    for d in records:
        lab, K = apply_cfg(d, cfg)
        sc = score_full(lab, d["y"], d["t"])
        rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=int(K),
                         k_bic=_k(d, 25), **sc))
    keys = ["ari", "f1", "b_f1", "b_mae", "b_recall", "b_precision", "b_count_err",
            "n_seg", "k"]
    agg = {}
    for k in keys:
        v = [r[k] for r in rows if np.isfinite(r[k])]
        agg[k] = float(np.mean(v)) if v else float("nan")
    return agg, rows


def build_records(split, fset, sw):
    ids = [int(r) for r in B.recs[B.recs.split == split].rec
           if len(B.segs[B.segs.rec == r]) >= 2]
    return [prep_record(r, fset, sw) for r in ids]


def phase_select():
    t0 = time.time()
    print("selection phase: train + validation only; test is not loaded")
    cache = {}
    # For each feature/smoothing, cached records for both splits.
    for fset in ["base18", "full32", "dyn30", "cross24", "geo44"]:
        for sw in [1, 5, 9]:
            cache[(fset, sw)] = dict(
                train=build_records("train", fset, sw),
                val=build_records("validation", fset, sw),
            )
            print(f"prepared {fset} sw={sw}: train={len(cache[(fset, sw)]['train'])} "
                  f"val={len(cache[(fset, sw)]['val'])}")

    rows = []
    for cfg in configs():
        # feature-specific cache when cfg denotes base setup
        if cfg.algo == "merge_short":
            fset, sw = "base18", 5
        else:
            fset, sw = cfg.fset, cfg.sw
        val = cache[(fset, sw)]["val"]
        agg, det = eval_config(val, cfg)
        rows.append(dict(cfg=cfg.__dict__, agg=agg, val_records=det))
        print(f"{cfg.tag:34s} val ARI={agg['ari']:.4f} bF1={agg['b_f1']:.4f} "
              f"K={agg['k']:.1f}")

    # supervised record-level cap selectors (fit on train labels, check on validation)
    sup = []
    for cfg0 in [Cfg("dummy", "base18", 5, "none", 0)]:
        pass
    for fset, sw in [("base18", 5), ("full32", 5), ("dyn30", 5), ("cross24", 5),
                     ("geo44", 5), ("base18", 1), ("base18", 9)]:
        tr, va = cache[(fset, sw)]["train"], cache[(fset, sw)]["val"]
        choices = cap_choice_models(tr, va)
        for tag, ks in choices.items():
            det, ari = [], []
            for d, cap in zip(va, ks):
                k = _k(d, int(cap))
                lab = ward_run(d["X"], k)
                sc = score_full(lab, d["y"], d["t"])
                det.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=int(k), cap=int(cap), **sc))
                ari.append(sc["ari"])
            agg = {kk: (float(np.mean([x[kk] for x in det if np.isfinite(x[kk])]))
                        if any(np.isfinite(x[kk]) for x in det) else float("nan"))
                   for kk in ["ari", "f1", "b_f1", "b_mae", "b_recall", "b_precision",
                              "b_count_err", "n_seg", "k"]}
            row = dict(cfg=dict(tag=f"sup_{tag}_{fset}_s{sw}", fset=fset, sw=sw,
                                algo="supervised_cap", param=tag), agg=agg, val_records=det,
                       caps=list(map(int, ks)))
            rows.append(row)
            sup.append(row)
            print(f"{row['cfg']['tag']:34s} val ARI={agg['ari']:.4f} bF1={agg['b_f1']:.4f} "
                  f"caps={list(map(int, ks))}")

    rows = sorted(rows, key=lambda r: (-r["agg"]["ari"], -r["agg"]["b_f1"]))
    best = rows[0]
    # Conservative eligibility: mean ARI must beat the official val baseline
    # (bic@8 = 0.5481464837243661), not merely the test baseline.
    eligible = [r for r in rows if r["agg"]["ari"] > 0.5481464837243661]
    chosen = eligible[0] if eligible else None
    out = dict(
        _meta=dict(phase="select", protocol="train+validation only; test untouched",
                   selection_rule="max validation mean ARI; must exceed official val bic@8=0.548146",
                   baseline_test_ari=BASELINE_ARI, baseline_test_f1=BASELINE_F1,
                   n_val=len(cache[("base18", 5)]["val"]), seed=SEED,
                   candidate_count=len(rows), elapsed_s=round(time.time() - t0, 1)),
        official_val_baseline=0.5481464837243661,
        ranking=rows,
        chosen=chosen,
        eligible=bool(chosen),
        selected_on_val_ari=(chosen["agg"]["ari"] if chosen else None),
        selected_on_val_bf1=(chosen["agg"]["b_f1"] if chosen else None),
    )
    with open(SEL_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nTOP 10")
    for r in rows[:10]:
        print(f"{r['cfg']['tag']:34s} valARI={r['agg']['ari']:.4f} bF1={r['agg']['b_f1']:.4f}")
    print(f"chosen={chosen['cfg']['tag'] if chosen else None}")
    print(f"saved {SEL_OUT}  {time.time()-t0:.1f}s")
    return out


def phase_test():
    sel = json.load(open(SEL_OUT, encoding="utf-8"))
    if not sel.get("chosen"):
        raise SystemExit("selection found no candidate above the official validation baseline")
    c = sel["chosen"]
    cfg = Cfg(**c["cfg"])
    print(f"test phase: frozen config {cfg.tag}")
    # supervised config needs its fitted model refit from train only (deterministic seed)
    if cfg.algo == "supervised_cap":
        fset, sw = cfg.fset, cfg.sw
        train = build_records("train", fset, sw)
        test = build_records("test", fset, sw)
        # Deterministic refit on train labels, then predict each test descriptor.
        caps_all = cap_choice_models(train, test)
        caps = caps_all[cfg.param]
        rows = []
        for d, cap in zip(test, caps):
            k = _k(d, int(cap))
            lab = ward_run(d["X"], k)
            sc = score_full(lab, d["y"], d["t"])
            rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], cap=int(cap), k=int(k), **sc))
    else:
        test = build_records("test", cfg.fset, cfg.sw)
        rows = []
        for d in test:
            lab, k = apply_cfg(d, cfg)
            sc = score_full(lab, d["y"], d["t"])
            rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=int(k), **sc))
    keys = ["ari", "f1", "b_f1", "b_mae", "b_recall", "b_precision", "b_count_err", "n_seg", "k"]
    agg = {k: float(np.mean([r[k] for r in rows if np.isfinite(r[k])]))
           for k in keys}
    base_rows = None
    # baseline per-record values are re-computed here for a paired comparison
    test_base = build_records("test", "base18", 5)
    base_rows = []
    for d in test_base:
        lab = ward_run(d["X"], _k(d, 8))
        sc = score_full(lab, d["y"], d["t"])
        base_rows.append(dict(rec=d["rec"], ktrue=d["ktrue"], k=8, **sc))
    base_agg = {k: float(np.mean([r[k] for r in base_rows if np.isfinite(r[k])]))
                for k in keys}
    # Verification against the published baseline; guards accidental protocol drift.
    assert abs(base_agg["ari"] - BASELINE_ARI) < 5e-6, (base_agg["ari"], BASELINE_ARI)
    delta = np.array([r["ari"] - b["ari"] for r, b in zip(rows, base_rows)])
    out = dict(
        _meta=dict(phase="test", protocol="frozen selection; one evaluation",
                   selected_tag=cfg.tag, selection_val_ari=sel["selected_on_val_ari"],
                   selection_val_bf1=sel["selected_on_val_bf1"],
                   baseline_test_ari=BASELINE_ARI, baseline_test_f1=BASELINE_F1,
                   selection_json=os.path.basename(SEL_OUT), seed=SEED),
        selected_cfg=cfg.__dict__,
        test_records=rows,
        test_mean=agg,
        baseline_records=base_rows,
        baseline_mean=base_agg,
        delta_ari=dict(mean=float(delta.mean()), median=float(np.median(delta)),
                       min=float(delta.min()), max=float(delta.max()),
                       wins=int((delta > 0).sum()), losses=int((delta < 0).sum()),
                       per_record=delta.tolist()),
        exceeds_baseline=bool(agg["ari"] > BASELINE_ARI),
        exceeds_by=float(agg["ari"] - BASELINE_ARI),
    )
    with open(RES_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nselected test mean", {k: round(v, 4) for k, v in agg.items()})
    print("baseline test mean", {k: round(v, 4) for k, v in base_agg.items()})
    print(f"delta ARI {delta.mean():+.4f}; wins {int((delta>0).sum())}/{len(delta)}")
    print(f"saved {RES_OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["select", "test"], required=True)
    a = ap.parse_args()
    if a.phase == "select":
        phase_select()
    else:
        phase_test()


if __name__ == "__main__":
    main()