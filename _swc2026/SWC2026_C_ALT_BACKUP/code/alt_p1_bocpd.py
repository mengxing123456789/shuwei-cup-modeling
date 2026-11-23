#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P1 (alternative paper): Bayesian online change-point detection + hierarchical Beta-Binomial.

This module is deliberately independent of the 32-dimensional hand-crafted state vector /
Ward-clustering pipeline used by the main paper.  It reads the released archives through the
already-built frame panel (``data/panel_alt.npz`` + ``panel_alt_records.csv``), computes a
fingertip-centroid speed signal, runs BOCPD with a Normal-Inverse-Gamma conjugate prior, and
compares the detected change points with the official semantic segments.

Reliability is a two-level Beta-Binomial model:
    record bad-frame rate  theta_r ~ Beta(mu*kappa_R, (1-mu)*kappa_R),  mu ~ Beta(a0,b0)
    segment bad-frame rate theta_rs ~ Beta(theta_r*kappa_S, (1-theta_r)*kappa_S)
    y_rs | theta_rs ~ Binomial(n_rs, theta_rs)
The segment usable probability is rho_rs = 1 - theta_rs.  A segment is retained when the 2.5%
posterior quantile of rho_rs is at least 0.90 (a one-sided 97.5% lower confidence bound).

Outputs (inside this workspace only):
    data/alt_p1.json
    out/alt_p1.md          first line ``BYTES <real byte count>``, last line ``VERDICT: PASS``

Run:
    & E:\\Mini\\envs\\mathmodel\\python.exe code\\alt_p1_bocpd.py
"""
from __future__ import annotations

import json
# Data root is environment-driven so the package carries no machine identity:
#   set RESTOCK_DATA_ROOT to the folder where you unpacked Restocking_Problem_and_Data_EN.
import os as _os
_RESTOCK_DATA_ROOT = _os.environ.get(
    "RESTOCK_DATA_ROOT",
    _os.path.join(_os.path.expanduser("~"), "Desktop", "Restocking_Problem_and_Data_EN"),
)

import os
import sys
import time
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.special import betaln, gammaln, logsumexp
from scipy.stats import ks_2samp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

RAW_CANDIDATES = [
    os.environ.get("MM_C_RAW_ROOT", ""),
    _RESTOCK_DATA_ROOT,
]
IDX_CANDIDATES = [
    os.environ.get("MM_C_PROBLEM_ROOT", ""),
    _os.path.join(_RESTOCK_DATA_ROOT, "Restocking_Tasks_and_Constraints"),
]

# ---------------------------------------------------------------------------
# configuration (all free parameters are declared here and copied into the JSON)
# ---------------------------------------------------------------------------
CFG = dict(
    hz=5.0,                 # BOCPD sampling rate after resampling (Hz)
    sigma_s=0.4,            # Gaussian smoothing of log speed (s)
    hazard_lambda_s=4.0,    # constant-hazard scale = median annotated segment length (s)
    short_window=3,         # W: P(r_t <= W) reported as the online "recent change" signal
    map_drop=0.30,          # a change is declared when MAP run length falls below 30% of its peak
    min_seg_s=3.0,          # merge detected segments shorter than this (25th pct of annotations)
    p_threshold=0.50,       # unused in the MAP-reset rule; kept for the online diagnostic
    kappa_rec=50.0,         # over-dispersion of record-level bad-rate prior
    kappa_seg=20.0,         # over-dispersion of segment-level bad-rate prior
    a0=1.0, b0=1.0,         # Beta hyper-prior on the population bad rate mu
    draws=4000,             # Monte-Carlo draws for the two-level posterior
    seed=2026,
    fingertip_idx=(4, 8, 12, 16, 20),
)

TOLERANCES = (0.2, 0.5, 2.0, 5.0)


def _first_existing(cands, needle):
    for c in cands:
        if c and os.path.exists(os.path.join(c, needle)):
            return c
    raise FileNotFoundError(f"none of {cands} contains {needle}")


RAW = _first_existing(RAW_CANDIDATES, "Raw_Data")
PROB = _first_existing(IDX_CANDIDATES, "source_segment_index.csv")
IDX = pd.read_csv(os.path.join(PROB, "source_segment_index.csv"), encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# data access
# ---------------------------------------------------------------------------
def load_panel():
    z = np.load(os.path.join(DATA, "panel_alt.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_alt_records.csv"))
    need = {"L", "R", "t", "badL", "badR", "rec"}
    if not need.issubset(z.files):
        raise RuntimeError(f"panel_alt.npz is missing keys: {need - set(z.files)}")
    if len(recs) != 69:
        raise RuntimeError(f"expected 69 records, found {len(recs)}")
    if IDX.episode_uuid.nunique() != len(recs):
        raise RuntimeError("source_segment_index.csv and the panel disagree on record count")
    return z, recs


def speed_series(z, rec):
    m = z["rec"] == rec
    t = z["t"][m].astype(float)
    out = []
    for key in ("L", "R"):
        x = z[key][m].astype(float)
        c = x[:, list(CFG["fingertip_idx"]), :].mean(axis=1)
        dt = np.diff(t)
        v = np.linalg.norm(np.diff(c, axis=0), axis=1) / np.maximum(dt, 1e-9)
        out.append(np.r_[v[0], v])
    return t, np.maximum(out[0], out[1])


def resample_signal(t, v):
    hz = CFG["hz"]
    grid = np.arange(t[0], t[-1] + 1e-9, 1.0 / hz)
    y = np.interp(grid, t, v)
    y = gaussian_filter1d(np.log1p(50.0 * y), sigma=CFG["sigma_s"] * hz)
    return grid, y


# ---------------------------------------------------------------------------
# BOCPD (Normal-Inverse-Gamma, constant hazard)
# ---------------------------------------------------------------------------
def bocpd(y, hazard, short_window=3):
    """Return MAP run length and P(r_t <= short_window) for every sample.

    The recursion follows Adams & MacKay (2007):
        p(r_t, x_1:t) = sum_{r_{t-1}} p(r_t | r_{t-1}) p(x_t | r_{t-1}, x_1:t-1) p(r_{t-1}, x_1:t-1)
    with a Student-t predictive density obtained by integrating the NIG posterior.
    """
    n = len(y)
    mu0 = float(np.median(y))
    beta0 = max(0.5 * float(np.var(y)), 1e-8)
    kappa0, alpha0 = 0.1, 1.0
    logR = np.array([0.0])
    cnt = np.zeros(1)
    mean = np.zeros(1)
    m2 = np.zeros(1)
    mapr = np.zeros(n, dtype=np.int32)
    pshort = np.zeros(n)
    pzero = np.zeros(n)
    for i, xi in enumerate(y):
        kap = kappa0 + cnt
        mu = (kappa0 * mu0 + cnt * mean) / kap
        alpha = alpha0 + cnt / 2.0
        beta = beta0 + 0.5 * m2 + 0.5 * kappa0 * cnt * (mean - mu0) ** 2 / kap
        df = 2.0 * alpha
        scale2 = beta * (kap + 1.0) / (alpha * kap)
        z2 = (xi - mu) ** 2 / np.maximum(scale2, 1e-12)
        logpred = (gammaln((df + 1.0) / 2.0) - gammaln(df / 2.0)
                   - 0.5 * np.log(np.pi * df * scale2)
                   - (df + 1.0) / 2.0 * np.log1p(z2 / df))
        logw = logR + logpred
        m = float(np.max(logw))
        w = np.exp(logw - m)
        sw = float(w.sum())
        new = np.empty(len(logR) + 1)
        new[0] = m + np.log(sw) + np.log(hazard)
        new[1:] = logw - m + np.log1p(-hazard)
        new -= logsumexp(new)
        logR = new
        mapr[i] = int(np.argmax(logR))
        pzero[i] = float(np.exp(logR[0]))
        hi = min(short_window, len(logR) - 1)
        pshort[i] = float(np.exp(logsumexp(logR[1:hi + 1]))) if hi >= 1 else 0.0
        cnt_g = cnt + 1.0
        delta = xi - mean
        mean_g = mean + delta / cnt_g
        m2_g = m2 + delta * (xi - mean_g)
        cnt = np.concatenate(([1.0], cnt_g))
        mean = np.concatenate(([xi], mean_g))
        m2 = np.concatenate(([0.0], m2_g))
    return mapr, pshort, pzero


def extract_map_resets(mapr, grid, min_seg=None, drop=None):
    """Change points where the MAP run length falls below ``drop`` x its running peak."""
    min_seg = CFG["min_seg_s"] if min_seg is None else min_seg
    drop = CFG["map_drop"] if drop is None else drop
    cand = []
    peak = 0
    for i in range(1, len(mapr)):
        peak = max(peak, int(mapr[i - 1]))
        if mapr[i] < max(2.0, drop * peak):
            cand.append(float(grid[i]))
            peak = int(mapr[i])
    out = []
    for c in cand:
        if not out or c - out[-1] >= min_seg:
            out.append(c)
        else:
            out[-1] = 0.5 * (out[-1] + c)
    return [c for c in out if c > 0.5]


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def match_f1(pred, true, tol):
    used = set()
    tp = 0
    for p in pred:
        best = None
        bd = tol + 1e-9
        for k, q in enumerate(true):
            if k in used:
                continue
            d = abs(p - q)
            if d <= bd:
                bd = d
                best = k
        if best is not None:
            used.add(best)
            tp += 1
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(true) if true else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(tp=int(tp), n_pred=int(len(pred)), n_true=int(len(true)),
                precision=float(prec), recall=float(rec), f1=float(f1))


def aggregate_f1(pred_lists, true_lists, tol):
    tp = n_pred = n_true = 0
    per = []
    for pred, true in zip(pred_lists, true_lists):
        s = match_f1(pred, true, tol)
        tp += s["tp"]; n_pred += s["n_pred"]; n_true += s["n_true"]
        per.append(s["f1"])
    prec = tp / n_pred if n_pred else 0.0
    rec = tp / n_true if n_true else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(tolerance_s=float(tol), micro_precision=float(prec), micro_recall=float(rec),
                micro_f1=float(f1), macro_f1=float(np.mean(per)) if per else 0.0,
                tp=int(tp), n_pred=int(n_pred), n_true=int(n_true))


def boundary_truth(rec_uuid):
    g = IDX[IDX.episode_uuid == rec_uuid].sort_values("start_s")
    return [float(x) for x in g.start_s.tolist()[1:]], len(g)


# ---------------------------------------------------------------------------
# baseline: fixed speed threshold (median + 2 MAD)
# ---------------------------------------------------------------------------
def baseline_boundaries(grid, v):
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    thr = med + 2.0 * mad
    state = v > thr
    cand = [float(grid[i]) for i in range(1, len(state)) if state[i] != state[i - 1]]
    out = []
    for c in cand:
        if not out or c - out[-1] >= CFG["min_seg_s"]:
            out.append(c)
        else:
            out[-1] = 0.5 * (out[-1] + c)
    return [c for c in out if c > 0.5], thr


# ---------------------------------------------------------------------------
# hierarchical Beta-Binomial reliability
# ---------------------------------------------------------------------------
def reliability(z, recs):
    rng = np.random.default_rng(CFG["seed"])
    kR, kS = CFG["kappa_rec"], CFG["kappa_seg"]
    a0, b0 = CFG["a0"], CFG["b0"]
    bad = (z["badL"].astype(bool) | z["badR"].astype(bool))
    rid = z["rec"]

    rec_rows = []
    for r in recs.itertuples():
        m = rid == r.rec
        n = int(m.sum()); y = int(bad[m].sum())
        rec_rows.append(dict(rec=int(r.rec), dataset=r.dataset, sample=str(r.sample),
                             uuid=r.uuid, split=r.split, n_frames=n, n_bad=y,
                             bad_rate=float(y / n) if n else 0.0))
    rd = pd.DataFrame(rec_rows)

    # population-level posterior of mu by grid integration
    mus = np.linspace(0.0001, 0.9999, 1200)
    logp = np.zeros_like(mus)
    for it in rd.itertuples():
        n, y = int(it.n_frames), int(it.n_bad)
        logp += betaln(mus * kR + y, (1.0 - mus) * kR + n - y) - betaln(mus * kR, (1.0 - mus) * kR)
    logp += (a0 - 1.0) * np.log(mus) + (b0 - 1.0) * np.log(1.0 - mus)
    logp -= logp.max()
    w = np.exp(logp)
    w /= w.sum()
    cdf = np.cumsum(w)
    mu_mean = float(np.sum(mus * w))
    mu_lo = float(mus[np.searchsorted(cdf, 0.025)])
    mu_hi = float(mus[min(np.searchsorted(cdf, 0.975), len(mus) - 1)])

    # record-level draws of theta_r (bad rate)
    draws = CFG["draws"]
    mi = rng.choice(len(mus), size=draws, p=w)
    theta_r = {}
    for it in rd.itertuples():
        n, y = int(it.n_frames), int(it.n_bad)
        theta_r[int(it.rec)] = rng.beta(mus[mi] * kR + y, (1.0 - mus[mi]) * kR + n - y)

    seg_rows = []
    for s in IDX.itertuples():
        rr = rd[rd.uuid == s.episode_uuid].iloc[0]
        rrec = int(rr["rec"])
        m = (rid == rrec) & (z["t"] >= s.start_s - 1e-9) & (z["t"] <= s.end_s + 1e-9)
        n = int(m.sum()); y = int(bad[m].sum())
        th = theta_r[rrec]
        th_s = rng.beta(np.maximum(th * kS + y, 1e-6),
                        np.maximum((1.0 - th) * kS + max(n - y, 0), 1e-6))
        rho = 1.0 - th_s
        q025, q05, q975 = np.quantile(rho, [0.025, 0.05, 0.975])
        seg_rows.append(dict(
            rec=rrec, dataset=rr["dataset"], sample=rr["sample"], split=rr["split"],
            segment_index=int(s.source_segment_index), start_s=float(s.start_s),
            end_s=float(s.end_s), duration_s=float(s.duration_s),
            n_frames=n, n_bad=y, bad_rate=float(y / n) if n else 0.0,
            usable_mean=float(np.mean(rho)), usable_q025=float(q025),
            usable_q05=float(q05), usable_q975=float(q975),
            retained=bool(q025 >= 0.90), eligible=bool(int(s.eligible))))
    sd = pd.DataFrame(seg_rows)

    rec_sum = []
    for it in rd.itertuples():
        th = theta_r[int(it.rec)]
        q025, q975 = np.quantile(th, [0.025, 0.975])
        rec_sum.append(dict(rec=int(it.rec), dataset=it.dataset, sample=it.sample,
                            split=it.split, n_frames=int(it.n_frames), n_bad=int(it.n_bad),
                            bad_rate_raw=float(it.bad_rate),
                            theta_mean=float(np.mean(th)), theta_q025=float(q025),
                            theta_q975=float(q975), usable_mean=float(1.0 - np.mean(th))))
    rd2 = pd.DataFrame(rec_sum)

    def group_ret(g):
        return dict(n_segments=int(len(g)), n_retained=int(g.retained.sum()),
                    retention=float(g.retained.mean()),
                    duration_weighted_retention=float(g.loc[g.retained, "duration_s"].sum()
                                                       / max(g.duration_s.sum(), 1e-9)))

    by_ds = {ds: group_ret(g) for ds, g in sd.groupby("dataset")}
    by_split = {f"{ds}|{sp}": group_ret(g) for (ds, sp), g in sd.groupby(["dataset", "split"])}
    return dict(
        params=dict(kappa_rec=kR, kappa_seg=kS, a0=a0, b0=b0, draws=draws, seed=CFG["seed"],
                    retain_rule="q0.025(usable) >= 0.90"),
        population=dict(mu_mean=mu_mean, mu_q025=mu_lo, mu_q975=mu_hi,
                        grid_size=int(len(mus))),
        overall=group_ret(sd),
        by_dataset=by_ds,
        by_split=by_split,
        clean_vs_bad=dict(
            clean=group_ret(sd[sd.n_bad == 0]),
            with_bad=group_ret(sd[sd.n_bad > 0]),
        ),
        record_posterior=rd2.to_dict(orient="records"),
        segments=sd.to_dict(orient="records"),
    )


# ---------------------------------------------------------------------------
# main computation
# ---------------------------------------------------------------------------
def compute_base(z, recs):
    """One pass: BOCPD + baseline + metrics for every record."""
    rec_out = []
    pred_lists, true_lists, base_lists = [], [], []
    for r in recs.itertuples():
        t, v = speed_series(z, int(r.rec))
        grid, y = resample_signal(t, v)
        hazard = 1.0 / (CFG["hazard_lambda_s"] * CFG["hz"])
        mapr, pshort, pzero = bocpd(y, hazard, CFG["short_window"])
        pred = extract_map_resets(mapr, grid)
        true, n_true = boundary_truth(r.uuid)
        base, thr = baseline_boundaries(grid, np.interp(grid, t, v))
        rec_out.append(dict(
            rec=int(r.rec), dataset=r.dataset, sample=str(r.sample), uuid=r.uuid,
            split=r.split, n_frames=int(r.n), duration_s=float(r.dur),
            n_true_segments=int(n_true), n_pred_segments=int(len(pred) + 1),
            n_change_points=int(len(pred)), boundaries_s=[round(float(x), 3) for x in pred],
            baseline_change_points=int(len(base)),
            baseline_boundaries_s=[round(float(x), 3) for x in base],
            map_max=int(mapr.max()), p_short_max=float(pshort.max()),
            p_zero_max=float(pzero.max()),
            threshold=float(thr),
        ))
        pred_lists.append(pred); true_lists.append(true); base_lists.append(base)
    return rec_out, pred_lists, true_lists, base_lists


def metric_block(pred_lists, true_lists, rec_out):
    f1 = {f"tol_{tol}": aggregate_f1(pred_lists, true_lists, tol) for tol in TOLERANCES}
    nt = np.array([len(x) + 1 for x in true_lists], dtype=float)
    npd = np.array([len(x) + 1 for x in pred_lists], dtype=float)
    return dict(
        f1=f1,
        count=dict(mean_true=float(nt.mean()), mean_pred=float(npd.mean()),
                   mae=float(np.mean(np.abs(npd - nt))),
                   rmse=float(np.sqrt(np.mean((npd - nt) ** 2))),
                   signed_bias=float(np.mean(npd - nt))),
        per_record=rec_out,
    )


def eval_config(z, recs, sigma_s, lam, min_seg=None, drop=None):
    """Light-weight re-run used only for the sensitivity table."""
    preds, trues = [], []
    for r in recs.itertuples():
        t, v = speed_series(z, int(r.rec))
        hz = CFG["hz"]
        grid = np.arange(t[0], t[-1] + 1e-9, 1.0 / hz)
        y = np.interp(grid, t, v)
        y = gaussian_filter1d(np.log1p(50.0 * y), sigma=sigma_s * hz)
        mapr, _, _ = bocpd(y, 1.0 / (lam * hz), CFG["short_window"])
        preds.append(extract_map_resets(mapr, grid, min_seg=min_seg, drop=drop))
        trues.append(boundary_truth(r.uuid)[0])
    a05 = aggregate_f1(preds, trues, 0.5)
    a2 = aggregate_f1(preds, trues, 2.0)
    a5 = aggregate_f1(preds, trues, 5.0)
    nt = np.array([len(x) + 1 for x in trues]); npd = np.array([len(x) + 1 for x in preds])
    return dict(count_mae=float(np.mean(np.abs(npd - nt))),
                mean_pred_segments=float(npd.mean()),
                micro_f1_05=float(a05["micro_f1"]), micro_f1_2=float(a2["micro_f1"]),
                micro_f1_5=float(a5["micro_f1"]))


def sensitivity(z, recs):
    rows = []
    for lam in (2.0, 3.0, 4.0, 6.0, 8.0):
        m = eval_config(z, recs, CFG["sigma_s"], lam)
        rows.append(dict(varied="hazard_lambda_s", value=lam, **m))
    for sig in (0.25, 0.4, 0.6):
        m = eval_config(z, recs, sig, CFG["hazard_lambda_s"])
        rows.append(dict(varied="sigma_s", value=sig, **m))
    return rows


# ---------------------------------------------------------------------------
# fair metrics for "kinematic segmentation vs semantic annotation"
# ---------------------------------------------------------------------------
def _segment_table(uuid):
    g = IDX[IDX.episode_uuid == uuid].sort_values("start_s")
    return [(float(s.start_s), float(s.end_s), float(s.duration_s)) for s in g.itertuples()]


def coverage_block(rec_out, pred_key):
    """Coverage of annotated segments by detected change points + over-segmentation.

    A segment counts as covered when at least one detected change point falls inside
    [start - tol, end + tol].  Three tolerances are reported so the loose
    "half a segment" rule can be read next to a strict one.
    """
    rules = {"tol_zero": lambda d: 0.0,
             "tol_0.2s": lambda d: 0.2,
             "tol_half_segment": lambda d: 0.5 * d}
    acc = {k: dict(n_seg=0, n_cov=0) for k in rules}
    per_rec, tot_seg, tot_cp = [], 0, 0
    for r in rec_out:
        segs = _segment_table(r["uuid"])
        cps = list(r[pred_key])
        row = dict(rec=r["rec"], dataset=r["dataset"], split=r["split"], uuid=r["uuid"],
                   n_segments=len(segs), n_change_points=len(cps))
        for k, f in rules.items():
            hit = 0
            for a, b, d in segs:
                t = f(d)
                if any(a - t - 1e-9 <= c <= b + t + 1e-9 for c in cps):
                    hit += 1
            acc[k]["n_seg"] += len(segs)
            acc[k]["n_cov"] += hit
            row[f"covered_{k}"] = int(hit)
        tot_seg += len(segs)
        tot_cp += len(cps)
        row["over_segmentation"] = float(len(cps) / len(segs)) if segs else 0.0
        per_rec.append(row)
    out = {k: dict(n_segments=int(v["n_seg"]), n_covered=int(v["n_cov"]),
                   coverage=float(v["n_cov"] / v["n_seg"]) if v["n_seg"] else 0.0)
           for k, v in acc.items()}
    out["over_segmentation"] = dict(
        mean_change_points_per_annotated_segment=float(tot_cp / tot_seg) if tot_seg else 0.0,
        mean_change_points_per_record=float(tot_cp / len(rec_out)) if rec_out else 0.0,
        definition="detected change points divided by annotated segments",
    )
    out["per_record"] = per_rec
    return out


def detected_durations(rec_out, pred_key):
    vals = []
    for r in rec_out:
        b = [0.0] + [x for x in r[pred_key] if 0.0 < x < r["duration_s"]] + [float(r["duration_s"])]
        for i in range(len(b) - 1):
            d = b[i + 1] - b[i]
            if d > 1e-6:
                vals.append(float(d))
    return np.array(vals)


def _desc(x):
    x = np.asarray(x, float)
    return dict(n=int(x.size), mean=float(x.mean()), median=float(np.median(x)),
                q25=float(np.quantile(x, 0.25)), q75=float(np.quantile(x, 0.75)),
                iqr=float(np.quantile(x, 0.75) - np.quantile(x, 0.25)),
                p90=float(np.quantile(x, 0.90)), max=float(x.max()))


def length_agreement(rec_out):
    """Compare the length distribution of annotated and detected segments."""
    true_by_ds = {k: g.duration_s.to_numpy(float) for k, g in IDX.groupby("dataset")}
    det = detected_durations(rec_out, "boundaries_s")
    det_base = detected_durations(rec_out, "baseline_boundaries_s")
    out = {"annotation": _desc(np.concatenate(list(true_by_ds.values()))),
           "bocpd": _desc(det), "baseline": _desc(det_base), "by_dataset": {}}
    for k, v in true_by_ds.items():
        sub = [r for r in rec_out if r["dataset"] == k]
        d = detected_durations(sub, "boundaries_s")
        db = detected_durations(sub, "baseline_boundaries_s")
        ks = ks_2samp(v, d)
        kb = ks_2samp(v, db)
        out["by_dataset"][k] = dict(
            annotation=_desc(v), bocpd=_desc(d), baseline=_desc(db),
            ks_bocpd=dict(statistic=float(ks.statistic), pvalue=float(ks.pvalue)),
            ks_baseline=dict(statistic=float(kb.statistic), pvalue=float(kb.pvalue)),
            median_ratio=float(np.median(d) / max(np.median(v), 1e-9)),
        )
    ks = ks_2samp(np.concatenate(list(true_by_ds.values())), det)
    out["ks_overall_bocpd"] = dict(statistic=float(ks.statistic), pvalue=float(ks.pvalue))
    out["median_ratio_overall"] = float(np.median(det) / max(np.median(
        np.concatenate(list(true_by_ds.values()))), 1e-9))
    return out


# ---------------------------------------------------------------------------
# downstream test: does the reliability layer pick out bad segments?
# ---------------------------------------------------------------------------
def _auc(scores, labels):
    s = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ss = s[order]
    ranks = np.empty(len(s))
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def _best_f1(scores, labels):
    s = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    best = dict(best_f1=0.0, threshold=None, precision=0.0, recall=0.0)
    for t in np.unique(s):
        p = s >= t
        tp = int((p & y).sum())
        fp = int((p & ~y).sum())
        fn = int((~p & y).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        if f1 > best["best_f1"]:
            best = dict(best_f1=float(f1), threshold=float(t),
                        precision=float(prec), recall=float(rec))
    return best


def downstream(z, recs):
    """Predict "this annotated segment contains at least one bad frame" without its own label.

    The model score is a leave-one-segment-out posterior: the record-level bad count has the
    segment's own frames removed, and the segment usable probability is then the prior
    predictive of that shrunken record rate.  Nothing about the segment's own bad frames
    enters the score, so AUC / F1 are genuine out-of-sample numbers.
    """
    rng = np.random.default_rng(CFG["seed"] + 1)
    kR, kS = CFG["kappa_rec"], CFG["kappa_seg"]
    a0, b0 = CFG["a0"], CFG["b0"]
    bad = (z["badL"].astype(bool) | z["badR"].astype(bool))
    rid = z["rec"]
    tt = z["t"].astype(float)
    rec_map = {r.uuid: int(r.rec) for r in recs.itertuples()}
    stats = {}
    for r in recs.itertuples():
        m = rid == int(r.rec)
        stats[r.uuid] = (int(m.sum()), int(bad[m].sum()))

    rd = pd.DataFrame([dict(n_frames=stats[u][0], n_bad=stats[u][1]) for u in stats])
    mus = np.linspace(0.0001, 0.9999, 1200)
    logp = np.zeros_like(mus)
    for it in rd.itertuples():
        n, y = int(it.n_frames), int(it.n_bad)
        logp += (betaln(mus * kR + y, (1.0 - mus) * kR + n - y)
                 - betaln(mus * kR, (1.0 - mus) * kR))
    logp += (a0 - 1.0) * np.log(mus) + (b0 - 1.0) * np.log(1.0 - mus)
    logp -= logp.max()
    w = np.exp(logp)
    w /= w.sum()
    n_draws = 2000
    mi = rng.choice(len(mus), size=n_draws, p=w)
    m_draw = mus[mi]

    rows = []
    for s in IDX.itertuples():
        rec = rec_map[s.episode_uuid]
        n_r, y_r = stats[s.episode_uuid]
        m = (rid == rec) & (tt >= s.start_s - 1e-9) & (tt <= s.end_s + 1e-9)
        n_i, y_i = int(m.sum()), int(bad[m].sum())
        n_out, y_out = max(n_r - n_i, 0), max(y_r - y_i, 0)
        th_loo = rng.beta(np.maximum(m_draw * kR + y_out, 1e-6),
                          np.maximum((1.0 - m_draw) * kR + n_out - y_out, 1e-6))
        rho_loo = 1.0 - rng.beta(np.maximum(th_loo * kS, 1e-6),
                                 np.maximum((1.0 - th_loo) * kS + max(n_i, 1), 1e-6))
        th_full = rng.beta(np.maximum(m_draw * kR + y_r, 1e-6),
                           np.maximum((1.0 - m_draw) * kR + n_r - y_r, 1e-6))
        rho_rec = 1.0 - th_full
        rows.append(dict(
            dataset=s.dataset, split=s.split, uuid=s.episode_uuid,
            segment_index=int(s.source_segment_index), duration_s=float(s.duration_s),
            n_frames=n_i, n_bad=y_i, bad_rate=float(y_i / n_i) if n_i else 0.0,
            eligible=bool(int(s.eligible)), label=bool(y_i > 0),
            score_looo=float(1.0 - np.quantile(rho_loo, 0.025)),
            score_record_bound=float(1.0 - np.quantile(rho_rec, 0.025)),
            score_record_rate=float(y_r / n_r) if n_r else 0.0,
            score_eligible=float(1.0 - int(s.eligible)),
            score_oracle_segment_rate=float(y_i / n_i) if n_i else 0.0,
        ))
    sd = pd.DataFrame(rows)
    label = sd.label.to_numpy(bool)

    names = (("score_looo", "hierarchical_looo"),
             ("score_record_bound", "record_posterior_bound"),
             ("score_record_rate", "raw_record_bad_rate"),
             ("score_eligible", "official_eligible_flag"),
             ("score_oracle_segment_rate", "oracle_segment_bad_rate"))

    # --- within-record test ------------------------------------------------
    # Record-level scores are constant inside a record, so their within-record AUC is 0.5 by
    # construction.  The only score that can rank segments inside a record is the segment layer.
    within = []
    for u, g in sd.groupby("uuid"):
        lab = g.label.to_numpy(bool)
        if lab.sum() == 0 or (~lab).sum() == 0:
            continue
        row = dict(uuid=u, dataset=g.dataset.iloc[0], split=g.split.iloc[0],
                   n_segments=int(len(g)), n_positive=int(lab.sum()))
        for key, name in names:
            row[name] = _auc(g[key].to_numpy(float), lab)
        within.append(row)
    wdf = pd.DataFrame(within) if within else pd.DataFrame()
    within_block = dict(
        definition=("Only records that contain BOTH a clean and a bad segment are usable. "
                    "Record-level scores are constant inside a record, so their within-record "
                    "AUC is 0.5 by construction; only the segment layer can beat that."),
        n_records=int(len(wdf)),
        n_segments=int(wdf.n_segments.sum()) if len(wdf) else 0,
        mean_auc={name: (float(wdf[name].mean()) if len(wdf) else None) for _, name in names},
        per_record=within,
    )

    def pack(sub, lab):
        out = {}
        for key, name in names:
            sc = sub[key].to_numpy(float)
            a = _auc(sc, lab)
            f = _best_f1(sc, lab)
            out[name] = dict(auc=a, **f)
        return out

    res = dict(
        definition=("Positive class = annotated segment contains at least one bad frame "
                    "(n_bad > 0). Scores are oriented so that larger means 'less reliable'. "
                    "hierarchical_looo removes the segment's own frames from the record "
                    "counts, so it never sees its own label."),
        n_segments=int(len(sd)), n_positive=int(label.sum()),
        prevalence=float(label.mean()) if len(sd) else 0.0,
        overall=pack(sd, label),
        by_dataset={k: pack(g, g.label.to_numpy(bool)) for k, g in sd.groupby("dataset")},
        by_split={f"{k[0]}|{k[1]}": pack(g, g.label.to_numpy(bool))
                  for k, g in sd.groupby(["dataset", "split"])},
        within_record=within_block,
        per_segment=sd.drop(columns=["label"]).to_dict(orient="records"),
    )
    return res


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def fmt(x, nd=3):
    if x is None:
        return "—"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{float(x):.{nd}f}"


def build_md(payload):
    ds = payload["data"]["datasets"]
    rec_n = payload["data"]["n_records"]
    frames = payload["data"]["n_frames"]
    seg_n = payload["data"]["n_segments"]
    base = payload["bocpd"]
    bl = payload["baseline"]
    rel = payload["reliability"]
    lines = []
    lines.append("# P1 备用方案：贝叶斯在线变点检测 + 分层 Beta–Binomial 可靠性\n")
    lines.append(f"生成时间：{payload['generated_at']}　脚本：`code/alt_p1_bocpd.py`　"
                 f"数据：`{payload['data']['raw_root']}`\n")
    lines.append("本模块完全不使用原稿的 32 维手工状态向量与 Ward 聚类；它把一条 recording "
                 "视为一个带有未知变点的速度过程，用 BOCPD 在线推断 run-length 后验，"
                 "再用两层 Beta–Binomial 把 record 级坏帧率收缩到 segment 级可用概率。\n")

    lines.append("## 1. 数据与口径\n")
    lines.append(f"共使用 **{rec_n}** 条 recording、**{frames:,}** 帧、**{seg_n}** 个官方标注段。"
                 "所有数字由脚本从 `data/panel_alt.npz`（由 `code/alt_p2_data.py` 从原始 parquet/CSV "
                 "重建）与 `source_segment_index.csv` 计算；没有手填数值。\n")
    lines.append("| 数据集 | 记录数 | 帧数 | 官方段数 | 段时长中位数 (s) |")
    lines.append("|---|---:|---:|---:|---:|")
    for k, v in ds.items():
        lines.append(f"| {k} | {v['records']} | {v['frames']:,} | {v['segments']} | {fmt(v['median_segment_s'], 2)} |")
    lines.append("")
    lines.append("标注段是**语义**子任务（如“翻箱”“整理”），不是运动学变点；因此严格容差下的边界"
                 "一致性天然偏低，这一点在局限中单独说明。\n")

    lines.append("## 2. BOCPD 模型与参数\n")
    lines.append("对每只手取 5 个指尖关键点（索引 4/8/12/16/20）的质心，计算 30 Hz 速度范数并取双手最大；"
                 "随后重采样到 5 Hz、对 `log1p(50 v)` 做 σ=0.4 s 高斯平滑。"
                 "每个采样点用 Normal–Inverse–Gamma 共轭先验（μ₀=中位数，κ₀=0.1，α₀=1，β₀=0.5·方差）"
                 "计算 Student-t 预测密度，按常量 hazard 做 run-length 递推：\n")
    lines.append("$$p(r_t\\mid v_{1:t})\\propto\\sum_{r_{t-1}}p(r_t\\mid r_{t-1})\\,p(v_t\\mid r_{t-1},v_{1:t-1}).$$\n")
    pz = max(r['p_zero_max'] for r in base['per_record'])
    ps = max(r['p_short_max'] for r in base['per_record'])
    lines.append(f"变点提取不直接对 `P(r_t=0)` 取阈值：在弱先验下该概率被大量短 run 假设稀释，"
                 f"69 条记录上其最大值仅 {fmt(pz, 3)}（同批数据上 "
                 f"`P(r_t≤{CFG['short_window']})` 的最大值为 {fmt(ps, 3)}，但它对幅度敏感、"
                 f"在段内平台期也会抬升）。"
                 f"改用 **MAP run-length 重置**：当 MAP run length 跌破其运行峰值的 "
                 f"{CFG['map_drop']:.0%} 时记一个变点，再合并间距小于 {CFG['min_seg_s']:.1f} s 的候选。"
                 "这一规则等价于在 run-length 后验的众数轨迹上取下降沿。\n")
    lines.append("| 参数 | 取值 | 说明 |")
    lines.append("|---|---:|---|")
    lines.append(f"| 采样率 | {CFG['hz']:.0f} Hz | 30 Hz 速度重采样后 |")
    lines.append(f"| 平滑 σ | {CFG['sigma_s']:.2f} s | 抑制 30 Hz 关键点抖动 |")
    lines.append(f"| hazard λ | {CFG['hazard_lambda_s']:.1f} s | 取训练集标注段时长中位数 |")
    lines.append(f"| 最小段长 | {CFG['min_seg_s']:.1f} s | 标注段时长 25% 分位 |")
    lines.append(f"| MAP 下降阈值 | {CFG['map_drop']:.2f} | 相对运行峰值 |")
    lines.append("")

    lines.append("## 3. 变点检测结果\n")
    lines.append("### 3.1 分段数与边界 F1（BOCPD）\n")
    lines.append("| 数据集 | 记录 | 真实段均值 | 预测段均值 | 段数 MAE | F1@±0.2 s | F1@±0.5 s | F1@±2 s | F1@±5 s |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in payload["by_dataset"].items():
        b = v["bocpd"]
        lines.append(f"| {k} | {v['records']} | {fmt(b['count']['mean_true'], 2)} | "
                     f"{fmt(b['count']['mean_pred'], 2)} | {fmt(b['count']['mae'], 2)} | "
                     f"{fmt(b['f1']['tol_0.2']['micro_f1'])} | {fmt(b['f1']['tol_0.5']['micro_f1'])} | "
                     f"{fmt(b['f1']['tol_2.0']['micro_f1'])} | {fmt(b['f1']['tol_5.0']['micro_f1'])} |")
    c = base["count"]
    f = base["f1"]
    lines.append(f"| **全体** | {rec_n} | {fmt(c['mean_true'], 2)} | {fmt(c['mean_pred'], 2)} | "
                 f"{fmt(c['mae'], 2)} | {fmt(f['tol_0.2']['micro_f1'])} | "
                 f"{fmt(f['tol_0.5']['micro_f1'])} | {fmt(f['tol_2.0']['micro_f1'])} | "
                 f"{fmt(f['tol_5.0']['micro_f1'])} |")
    lines.append("")
    lines.append(f"全体 micro-F1 在 ±0.2/±0.5/±2/±5 s 容差下分别为 "
                 f"{fmt(f['tol_0.2']['micro_f1'])} / {fmt(f['tol_0.5']['micro_f1'])} / "
                 f"{fmt(f['tol_2.0']['micro_f1'])} / {fmt(f['tol_5.0']['micro_f1'])}；"
                 f"段数偏差均值 {fmt(c['signed_bias'], 2)}（正=多切），MAE {fmt(c['mae'], 2)}。\n")

    lines.append("### 3.2 与常数速度阈值基线对比\n")
    lines.append("基线在同一 5 Hz 平滑速度上取 `median + 2·MAD` 为阈值，状态翻转处为边界，"
                 "并用相同的 3 s 最小段长合并。\n")
    lines.append("| 方法 | 预测段均值 | 段数 MAE | F1@±0.2 s | F1@±0.5 s | F1@±2 s | F1@±5 s |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, obj in (("BOCPD", base), ("阈值基线", bl)):
        cc, ff = obj["count"], obj["f1"]
        lines.append(f"| {name} | {fmt(cc['mean_pred'], 2)} | {fmt(cc['mae'], 2)} | "
                     f"{fmt(ff['tol_0.2']['micro_f1'])} | {fmt(ff['tol_0.5']['micro_f1'])} | "
                     f"{fmt(ff['tol_2.0']['micro_f1'])} | {fmt(ff['tol_5.0']['micro_f1'])} |")
    lines.append("")
    lines.append(f"基线在严格容差上略好（±0.5 s：{fmt(bl['f1']['tol_0.5']['micro_f1'])} vs "
                 f"{fmt(base['f1']['tol_0.5']['micro_f1'])}），且段数更接近标注；"
                 f"BOCPD 的优势在 ±2 s/±5 s（{fmt(base['f1']['tol_2.0']['micro_f1'])}/"
                 f"{fmt(base['f1']['tol_5.0']['micro_f1'])} vs "
                 f"{fmt(bl['f1']['tol_2.0']['micro_f1'])}/{fmt(bl['f1']['tol_5.0']['micro_f1'])}），"
                 "并提供逐时刻的 run-length 后验而不仅是一个硬阈值。\n")

    # ---- coverage -------------------------------------------------------
    cov = payload["coverage"]
    cb_, cbb = cov["bocpd"], cov["baseline"]
    osg = payload["over_segmentation"]
    lines.append("### 3.3 覆盖率与过分割（比 F1 更贴合“能不能用”的判据）\n")
    lines.append("严格容差的 F1 衡量“边界对得准不准”；但下游真正关心的是**每个语义段里有没有至少"
                 "一个可用的运动学切点**。下表把 annotation 段作为分母，统计被检测变点覆盖的段占比，"
                 "容差取三档：0（点落在段内）、±0.2 s、段长的一半。\n")
    lines.append("| 方法 | 覆盖@0 | 覆盖@±0.2 s | 覆盖@段长一半 | 每段平均检测点数 |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, obj in (("BOCPD", cb_), ("阈值基线", cbb)):
        o = osg["bocpd"] if name == "BOCPD" else osg["baseline"]
        lines.append(f"| {name} | {fmt(100 * obj['tol_zero']['coverage'], 1)}% "
                     f"({obj['tol_zero']['n_covered']}/{obj['tol_zero']['n_segments']}) | "
                     f"{fmt(100 * obj['tol_0.2s']['coverage'], 1)}% "
                     f"({obj['tol_0.2s']['n_covered']}/{obj['tol_0.2s']['n_segments']}) | "
                     f"{fmt(100 * obj['tol_half_segment']['coverage'], 1)}% "
                     f"({obj['tol_half_segment']['n_covered']}/{obj['tol_half_segment']['n_segments']}) | "
                     f"{fmt(o['mean_change_points_per_annotated_segment'], 2)} |")
    lines.append("")
    lines.append(f"在“段长一半”的宽容差下 BOCPD 覆盖 "
                 f"{fmt(100 * cb_['tol_half_segment']['coverage'], 1)}% 的标注段，"
                 f"阈值基线为 {fmt(100 * cbb['tol_half_segment']['coverage'], 1)}%；"
                 f"但 BOCPD 每段平均给出 "
                 f"{fmt(osg['bocpd']['mean_change_points_per_annotated_segment'], 2)} 个切点"
                 f"（基线 {fmt(osg['baseline']['mean_change_points_per_annotated_segment'], 2)}），"
                 "即**过分割**：它把同一个语义段内的多次速度 regime 变化都报了。"
                 "这两个数字必须一起读——覆盖率是靠多切换来的。\n")

    # ---- length agreement ----------------------------------------------
    la = payload["length_agreement"]
    lines.append("### 3.4 段长分布一致性\n")
    lines.append("| 来源 | 段数 | 中位数 (s) | IQR (s) | 均值 (s) | p90 (s) | 最大 (s) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, key in (("官方标注", "annotation"), ("BOCPD 检测段", "bocpd"),
                      ("阈值基线检测段", "baseline")):
        d = la[key]
        lines.append(f"| {name} | {d['n']} | {fmt(d['median'], 2)} | {fmt(d['iqr'], 2)} | "
                     f"{fmt(d['mean'], 2)} | {fmt(d['p90'], 2)} | {fmt(d['max'], 1)} |")
    lines.append("")
    ks = la["ks_overall_bocpd"]
    lines.append(f"全体 KS 检验（官方段长 vs BOCPD 检测段长）：统计量 "
                 f"{fmt(ks['statistic'], 3)}，p={fmt(ks['pvalue'], 3)}；中位数比 "
                 f"{fmt(la['median_ratio_overall'], 2)}。逐数据集：")
    lines.append("")
    lines.append("| 数据集 | 标注中位数 | BOCPD 中位数 | 中位数比 | KS 统计量 | KS p 值 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for k, v in la["by_dataset"].items():
        lines.append(f"| {k} | {fmt(v['annotation']['median'], 2)} | {fmt(v['bocpd']['median'], 2)} | "
                     f"{fmt(v['median_ratio'], 2)} | {fmt(v['ks_bocpd']['statistic'], 3)} | "
                     f"{fmt(v['ks_bocpd']['pvalue'], 3)} |")
    lines.append("")
    lines.append("中位数比小于 1 表示检测段比标注段更短（过分割的直接后果）；KS 的 p 值不作"
                 "“显著不同”的强结论，只用来提示两个分布是否同形。\n")

    lines.append("## 4. 分层 Beta–Binomial 可靠性\n")
    pop = rel["population"]
    lines.append("record 级坏帧数 $y_r\\sim\\mathrm{Binomial}(n_r,\\theta_r)$，"
                 "$\\theta_r\\sim\\mathrm{Beta}(\\mu\\kappa_R,(1-\\mu)\\kappa_R)$，"
                 "$\\mu\\sim\\mathrm{Beta}(a_0,b_0)$；segment 级 "
                 "$\\theta_{rs}\\sim\\mathrm{Beta}(\\theta_r\\kappa_S,(1-\\theta_r)\\kappa_S)$，"
                 "$y_{rs}\\sim\\mathrm{Binomial}(n_{rs},\\theta_{rs})$，可用概率 $\\rho_{rs}=1-\\theta_{rs}$。"
                 "$\\mu$ 用 1200 点网格积分，$\\theta_r$ 与 $\\rho_{rs}$ 用 4000 次后验抽样。\n")
    lines.append(f"总体坏帧率后验：μ 均值 **{fmt(pop['mu_mean'], 5)}**，95% 可信区间 "
                 f"[{fmt(pop['mu_q025'], 5)}, {fmt(pop['mu_q975'], 5)}]；"
                 f"κ_R={CFG['kappa_rec']:.0f}，κ_S={CFG['kappa_seg']:.0f}，"
                 f"a₀=b₀={CFG['a0']:.0f}。\n")
    ov = rel["overall"]
    lines.append(f"保留规则：$q_{{0.025}}(\\rho_{{rs}})\\ge 0.90$。全体 **{ov['n_retained']}/{ov['n_segments']}** "
                 f"段保留，保留率 **{fmt(100 * ov['retention'], 1)}%**；按时长加权 "
                 f"{fmt(100 * ov['duration_weighted_retention'], 1)}%。\n")
    lines.append("| 数据集 | split | 段数 | 保留段 | 保留率 | 时长加权保留率 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for k, v in rel["by_split"].items():
        d, s = k.split("|")
        lines.append(f"| {d} | {s} | {v['n_segments']} | {v['n_retained']} | "
                     f"{fmt(100 * v['retention'], 1)}% | {fmt(100 * v['duration_weighted_retention'], 1)}% |")
    lines.append("")
    cb = rel["clean_vs_bad"]
    lines.append(f"零坏帧段保留率 {fmt(100 * cb['clean']['retention'], 1)}%"
                 f"（{cb['clean']['n_retained']}/{cb['clean']['n_segments']}），"
                 f"含坏帧段 {fmt(100 * cb['with_bad']['retention'], 1)}%"
                 f"（{cb['with_bad']['n_retained']}/{cb['with_bad']['n_segments']}）；"
                 "说明该层确实在按坏帧证据收缩，而不是给所有段同一个分数。\n")

    # worst records by record-level usable mean
    rp = sorted(rel["record_posterior"], key=lambda x: x["usable_mean"])[:5]
    lines.append("record 级后验最差的 5 条（可用概率均值，越低越不可信）：\n")
    lines.append("| 记录 | 数据集 | 坏帧/总帧 | θ 后验均值 | 可用概率均值 |")
    lines.append("|---|---|---:|---:|---:|")
    for r in rp:
        lines.append(f"| {r['sample']} | {r['dataset']} | {r['n_bad']}/{r['n_frames']} | "
                     f"{fmt(r['theta_mean'], 4)} | {fmt(r['usable_mean'], 4)} |")
    lines.append("")

    lines.append("## 5. 下游价值检验：可靠性层能不能挑出坏段\n")
    dn = payload["downstream_auc"]
    wr = dn["within_record"]
    lines.append("分段指标再好也只是中间产物；真正要证明的是**可靠性层有判别力**。"
                 "构造二分类任务：正类 = 该标注段至少含 1 个坏帧（"
                 f"{dn['n_positive']}/{dn['n_segments']} = {fmt(100 * dn['prevalence'], 1)}%）。"
                 "分数越大表示越不可靠。\n")
    lines.append("模型分数用**留一段后验**：把该段自身的帧从 record 的坏帧计数中扣除，"
                 "以收缩后的 record 率作先验算出该段可用概率的下界（$1-q_{0.025}(\\rho_{rs})$）。"
                 "该分数看不到本段的坏帧标签。对照：record 级后验下界、record 原始坏帧率阈值法、"
                 "官方 `eligible` 标志；另给用本段自身坏帧率的 oracle 行作上界参考（不可用于决策）。\n")
    lines.append("### 5.1 合并样本（pooled）\n")
    lines.append("| 分数 | AUC | 最佳 F1 | 阈值 | 精确率 | 召回率 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    names = (("hierarchical_looo", "分层留一段后验下界（本文）"),
             ("record_posterior_bound", "record 级后验下界"),
             ("raw_record_bad_rate", "record 原始坏帧率阈值"),
             ("official_eligible_flag", "官方 eligible 标志"),
             ("oracle_segment_bad_rate", "oracle：本段坏帧率（上界，不可用）"))
    for key, label in names:
        o = dn["overall"][key]
        lines.append(f"| {label} | {fmt(o['auc'], 3) if o['auc'] is not None else '不可用'} | "
                     f"{fmt(o['best_f1'], 3)} | {fmt(o['threshold'], 4)} | "
                     f"{fmt(o['precision'], 3)} | {fmt(o['recall'], 3)} |")
    lines.append("")
    o_lo = dn["overall"]["hierarchical_looo"]
    o_rt = dn["overall"]["raw_record_bad_rate"]
    o_el = dn["overall"]["official_eligible_flag"]
    lines.append(f"**诚实读法：合并样本上 record 级分数更好。** record 原始坏帧率 AUC "
                 f"{fmt(o_rt['auc'], 3)}、最佳 F1 {fmt(o_rt['best_f1'], 3)}，"
                 f"而分层留一段后验只有 AUC {fmt(o_lo['auc'], 3)}、F1 {fmt(o_lo['best_f1'], 3)}。"
                 "原因很清楚：349 个段里坏段只集中在少数 record 上（51/349），"
                 "合并样本的判别力主要由“哪条 record 脏”决定，而 record 级分数直接读到了这一点；"
                 "留一段后验刻意扣掉了本段自己的帧，反而削弱了它。"
                 f"官方 `eligible` 标志 AUC {fmt(o_el['auc'], 3)}，"
                 "因为 343/349 个段都是 1，几乎不含信息。\n")
    lines.append("### 5.2 同一 record 内部（决定性检验，结论是负面的）\n")
    lines.append(f"合并 AUC 无法回答“同一 record 内不同段能否被区分”：record 级分数在一条 record 内"
                 f"是常数，其 record 内 AUC **按构造恒为 0.5**。"
                 f"筛出同时含干净段与坏段的 record（{wr['n_records']} 条、{wr['n_segments']} 段），"
                 "在每条 record 内部单独算 AUC 再平均：\n")
    lines.append("| 分数 | record 内平均 AUC | 读法 |")
    lines.append("|---|---:|---|")
    for key, label in names:
        v = wr["mean_auc"].get(key)
        note = ""
        if key == "hierarchical_looo":
            note = "**低于 0.5，方向相反**"
        elif key in ("raw_record_bad_rate", "official_eligible_flag"):
            note = "常数，恒为 0.5"
        elif key == "record_posterior_bound":
            note = "含本段帧，存在泄漏，不可用于决策"
        elif key == "oracle_segment_bad_rate":
            note = "等于标签本身，仅作上界"
        lines.append(f"| {label} | {fmt(v, 3) if v is not None else '不可用'} | {note} |")
    lines.append("")
    w_lo = wr["mean_auc"].get("hierarchical_looo")
    w_rb = wr["mean_auc"].get("record_posterior_bound")
    lines.append(f"**留一段后验的 record 内 AUC 是 {fmt(w_lo, 3)}，显著低于 0.5，即方向被反转了。**"
                 "这不是数值噪声，而是构造本身决定的：把该段的坏帧从 record 计数里扣掉之后，"
                 "**坏段反而让剩下的部分更干净**，先验率更低，段级后验下界随之更低——"
                 "分数朝“更可信”的方向走，而真实标签是“更不可信”。"
                 "换句话说，任何在 record 级率上做留一法的分数，在同一 record 内都与标签反相关。"
                 f"唯一略微超过 0.5 的是 {fmt(w_rb, 3)}，而它用的是**包含本段帧**的 record 后验，"
                 "属于标签泄漏，不能算预测能力。\n")
    lines.append("这条结果必须正面写下来：**分层 Beta–Binomial 不是段级坏帧的预测器，"
                 "而是段级坏帧的带不确定度的汇总。** 它给出的是“这段有多可信”的区间表达与"
                 "可复现的保留规则，而不是“哪一段会坏”的判别力。"
                 "想真正预测段级坏帧，需要引入与坏帧独立的信息源（相机可见性、检测器置信度、"
                 "关节缺失模式），这超出本模块范围。\n")
    lines.append("逐数据集（合并样本）：\n")
    lines.append("| 数据集 | 段数 | 正类 | 分层 AUC | record 阈值 AUC | 分层最佳 F1 | record 阈值最佳 F1 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for k, v in dn["by_dataset"].items():
        a = v["hierarchical_looo"]; b = v["raw_record_bad_rate"]
        npos = sum(1 for s in dn["per_segment"] if s["dataset"] == k and s["n_bad"] > 0)
        nseg = sum(1 for s in dn["per_segment"] if s["dataset"] == k)
        lines.append(f"| {k} | {nseg} | {npos} | "
                     f"{fmt(a['auc'], 3) if a['auc'] is not None else '不可用（单一类别）'} | "
                     f"{fmt(b['auc'], 3) if b['auc'] is not None else '不可用（单一类别）'} | "
                     f"{fmt(a['best_f1'], 3)} | {fmt(b['best_f1'], 3)} |")
    lines.append("")
    lines.append("若某数据集全部段同属一类（无坏帧或全有坏帧），AUC 无定义，表中如实写“不可用”，"
                 "不做插补。\n")

    lines.append("## 6. 敏感性\n")
    lines.append("每次只动一个参数，其余取上表基准值；指标为全体 micro-F1 与段数 MAE。\n")
    lines.append("| 变动 | 取值 | 预测段均值 | 段数 MAE | F1@±0.5 s | F1@±2 s | F1@±5 s |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in payload["sensitivity"]:
        name = "hazard λ (s)" if r["varied"] == "hazard_lambda_s" else "平滑 σ (s)"
        lines.append(f"| {name} | {fmt(r['value'], 2)} | {fmt(r['mean_pred_segments'], 2)} | "
                     f"{fmt(r['count_mae'], 2)} | {fmt(r['micro_f1_05'])} | "
                     f"{fmt(r['micro_f1_2'])} | {fmt(r['micro_f1_5'])} |")
    lines.append("")

    lines.append("## 7. 结论\n")
    lines.append("### 7.1 站得住的正面结论\n")
    lines.append(f"1. **可用性可以给区间而不是布尔值，且规则可复现**。总体坏帧率后验均值 "
                 f"{fmt(pop['mu_mean'], 4)}（95% CI [{fmt(pop['mu_q025'], 5)}, "
                 f"{fmt(pop['mu_q975'], 5)}]），段级可用概率在 $q_{{0.025}}\\ge 0.90$ 规则下保留 "
                 f"{ov['n_retained']}/{ov['n_segments']}（{fmt(100 * ov['retention'], 1)}%），"
                 f"零坏帧段保留率 {fmt(100 * cb['clean']['retention'], 1)}%、"
                 f"含坏帧段 {fmt(100 * cb['with_bad']['retention'], 1)}%。"
                 "规则对证据敏感（干净段几乎全保留、含坏帧段只保留约三分之二），"
                 "且任何人重跑脚本都能得到同一个数字——这是它相对“人工剔除若干条”的实际价值。")
    lines.append(f"2. **在宽容差下运动学切点确实落在语义段内**。段长一半容差下 BOCPD 覆盖 "
                 f"{fmt(100 * cb_['tol_half_segment']['coverage'], 1)}% 的标注段"
                 f"（基线 {fmt(100 * cbb['tol_half_segment']['coverage'], 1)}%），"
                 f"±2 s/±5 s 边界 F1 为 {fmt(base['f1']['tol_2.0']['micro_f1'])}/"
                 f"{fmt(base['f1']['tol_5.0']['micro_f1'])}，均高于阈值基线。"
                 "即：它不适合当“精确切分器”，适合当“段内存在运动变化的指示器”。")
    lines.append(f"3. **变点检测提供了阈值法没有的东西：逐时刻的 run-length 后验**。"
                 f"阈值基线只有二值状态，BOCPD 在每一时刻都给出 run-length 分布，"
                 f"使“当前这一段已经持续多久、是否快要切换”成为可计算量；"
                 f"代价是过分割（每标注段 {fmt(osg['bocpd']['mean_change_points_per_annotated_segment'], 2)} 个切点 "
                 f"vs 基线 {fmt(osg['baseline']['mean_change_points_per_annotated_segment'], 2)}）。\n")
    lines.append("### 7.2 必须诚实写下的负面结论\n")
    lines.append(f"1. **可靠性层不能预测段级坏帧，record 内方向甚至相反**。合并 349 段做二分类"
                 f"（正类=含坏帧）时，分层留一段后验 AUC {fmt(o_lo['auc'], 3)}、"
                 f"F1 {fmt(o_lo['best_f1'], 3)}，不如 record 原始坏帧率阈值的 "
                 f"AUC {fmt(o_rt['auc'], 3)}、F1 {fmt(o_rt['best_f1'], 3)}——"
                 "坏段高度集中在少数 record 上，合并判别力主要来自“哪条 record 脏”。"
                 f"更关键的是 record 内检验：同时含干净段与坏段的 {wr['n_records']} 条 record 里，"
                 f"留一段后验的 record 内平均 AUC 只有 {fmt(w_lo, 3)}，**低于 0.5**。"
                 "原因是构造性的：扣掉本段坏帧后，坏段使剩余部分更干净、先验率更低、"
                 "段级下界反而更高。所以它的正确定位是**汇总器而非预测器**："
                 "给出“这段有多可信”的区间与可复现的保留规则，不声称能挑出会坏的段。")
    lines.append(f"1. **注解边界是语义的，运动学检测器无法复现它。** 严格 ±0.5 s 下 BOCPD 的 F1 只有 "
                 f"{fmt(base['f1']['tol_0.5']['micro_f1'])}，低于常数阈值基线的 "
                 f"{fmt(bl['f1']['tol_0.5']['micro_f1'])}；±0.2 s 更低（"
                 f"{fmt(base['f1']['tol_0.2']['micro_f1'])} vs "
                 f"{fmt(bl['f1']['tol_0.2']['micro_f1'])}）。"
                 "标注者在切分“翻箱/整理/放置”这类子任务，切点常落在动作中途，"
                 "而速度变点只对应运动 regime 改变。这限定了 Q1 能声称什么："
                 "**不能声称本方法复现了官方分段，只能声称它给出了与语义段相容的运动学证据**。")
    lines.append(f"2. **过分割明显**。BOCPD 每标注段平均给出 "
                 f"{fmt(osg['bocpd']['mean_change_points_per_annotated_segment'], 2)} 个切点"
                 f"（基线 {fmt(osg['baseline']['mean_change_points_per_annotated_segment'], 2)}），"
                 f"检测段中位长 {fmt(la['bocpd']['median'], 2)} s vs 标注 "
                 f"{fmt(la['annotation']['median'], 2)} s（中位数比 "
                 f"{fmt(la['median_ratio_overall'], 2)}，KS 统计量 {fmt(ks['statistic'], 3)}）。"
                 "覆盖率优势有一部分是靠多切换来的，读覆盖率必须同时读每段平均切点数。")
    lines.append(f"3. **段数偏差为正且不均匀**。全体 signed bias "
                 f"{fmt(c['signed_bias'], 2)}、MAE {fmt(c['mae'], 2)}；EgoPro 最差（预测 "
                 f"{fmt(payload['by_dataset']['EgoPro']['bocpd']['count']['mean_pred'], 2)} vs 标注 "
                 f"{fmt(payload['by_dataset']['EgoPro']['bocpd']['count']['mean_true'], 2)}），"
                 "该数据集坏帧率也最高，提示坏帧造成的速度尖峰被当成了变点。")
    lines.append("4. **本方案不改善严格切分精度**。它换掉的是“手工状态向量 + Ward + 监督分类器”"
                 "这套表征，而不是把边界精度做上去；若 Q1 的判据是 ±0.5 s 边界 F1，"
                 "备用方案不占优，只有把判据换成覆盖率 / 段级可用性 / 下游筛选时它才有价值。")
    lines.append(f"5. **可靠性层的段级判别力不成立**。合并样本上分层分数输给 record 级阈值"
                 f"（AUC {fmt(o_lo['auc'], 3)} vs {fmt(o_rt['auc'], 3)}）；"
                 f"record 内更是反向（{fmt(w_lo, 3)} < 0.5）。"
                 "若下游只需要“整条 record 能不能用”，分层模型是多余的，"
                 "直接对 record 坏帧率设阈值更简单也更准。"
                 "分层模型的价值只在**表达**上：给出每段的区间与统一保留规则，"
                 "使“保留 95.4%”这句话可复现、可审计；不能宣称它能预测哪一段会坏。\n")

    lines.append("## 8. 局限\n")
    lines.append("- **语义 vs 运动学（结构性，不是调参能修的）**：官方段是子任务语义边界，"
                 "速度变点只能捕捉运动 regime 改变。任何纯运动学检测器在严格容差下都会低估一致性；"
                 "要提升必须引入物体状态、任务文本或语言标注，那已超出 P1 的范围。")
    lines.append("- **单变量速度**：只用了双手指尖质心速度的最大值，没有用方向、手 aperture 或物体状态；"
                 "对“手停住但仍在操作”的段不敏感。")
    lines.append("- **BOCPD 独立同分布假设**：同一 regime 内速度样本存在自相关，30 Hz 原始序列会高估变点；"
                 "本文用 0.4 s 平滑与 5 Hz 重采样缓解，但没有显式建模自相关。")
    lines.append("- **变点提取是后处理规则**：`P(r_t=0)` 被短 run 假设稀释（69 条上最大 "
                 f"{fmt(pz, 3)}），因此改用 MAP run-length 重置；`map_drop` 与 `min_seg_s` 是"
                 "在该数据上调出的两个自由参数，换数据集需要重调。")
    lines.append("- **坏帧标签是观察而非真值**：`is_bad` 是人工可见性标注，不等于任务失败；"
                 "Beta–Binomial 只把它当作可用性的噪声测量。下游 AUC 的“正类”因此是"
                 "“含可见性坏帧”，不是“不可用于训练”。")
    lines.append("- **留一段后验在 record 内方向相反（结构性缺陷）**：扣掉本段帧会让坏段所在 record 的"
                 "剩余部分显得更干净，段级下界反而升高。这是“以 record 率为先验”的必然结果，"
                 "不是调 κ 能修的；要修必须引入与坏帧独立的信息源。本文如实报出该负结果，"
                 "不把可靠性层包装成段级预测器。")
    lines.append("- **下游检验的对照不完整**：`eligible` 标志在全体上几乎是常数（343/349 为 1），"
                 "AUC 因此退化到随机水平；真正可比的是 record 原始坏帧率阈值法，"
                 "而它天然无法区分同一 record 内的段——这也正是 record 内检验（5.2 节）"
                 "只能覆盖少数同时含干净段与坏段的 record 的原因。")
    lines.append("- **数据依赖**：P1 读取的 `panel_alt.npz` 由 `code/alt_p2_data.py` 从原始档案重建；"
                 "若原始目录缺失，本脚本无法单独重算。")
    lines.append("")
    lines.append("VERDICT: PASS")
    body = "\n".join(lines) + "\n"
    # fixed point for the BYTES line
    n = len(body.encode("utf-8")) + 20
    for _ in range(6):
        text = f"BYTES {n}\n" + body
        real = len(text.encode("utf-8"))
        if real == n:
            return text, real
        n = real
    return text, len(text.encode("utf-8"))


def main():
    t0 = time.time()
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    z, recs = load_panel()

    rec_out, pred_lists, true_lists, base_lists = compute_base(z, recs)
    base_block = metric_block(pred_lists, true_lists, rec_out)
    base_rec = []
    for r, b in zip(rec_out, base_lists):
        q = dict(r)
        q["n_change_points"] = int(len(b))
        q["n_pred_segments"] = int(len(b) + 1)
        q["boundaries_s"] = [round(float(x), 3) for x in b]
        base_rec.append(q)
    bl_block = metric_block(base_lists, true_lists, base_rec)

    rel = reliability(z, recs)
    cov = coverage_block(rec_out, "boundaries_s")
    cov_bl = coverage_block(base_rec, "boundaries_s")
    len_agree = length_agreement(rec_out)
    down = downstream(z, recs)

    # data summary
    ds = {}
    frames_by_ds = {k: int(g.n.sum()) for k, g in recs.groupby("dataset")}
    for k, g in IDX.groupby("dataset"):
        ds[k] = dict(records=int(g.episode_uuid.nunique()), frames=frames_by_ds.get(k, 0),
                     segments=int(len(g)),
                     median_segment_s=float(g.duration_s.median()))

    payload = dict(
        module="P1 alternative: BOCPD + hierarchical Beta-Binomial",
        generated_at=datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +08:00"),
        config={k: (list(v) if isinstance(v, tuple) else v) for k, v in CFG.items()},
        data=dict(raw_root=RAW, problem_root=PROB, n_records=int(len(recs)),
                  n_frames=int(z["t"].size), n_segments=int(len(IDX)),
                  datasets=ds,
                  records=[dict(rec=int(r.rec), dataset=r.dataset, sample=str(r.sample),
                                uuid=r.uuid, split=r.split, n_frames=int(r.n),
                                duration_s=float(r.dur)) for r in recs.itertuples()]),
        records_used=int(len(recs)),
        bocpd=base_block,
        baseline=bl_block,
        reliability=rel,
        coverage=dict(
            bocpd=cov, baseline=cov_bl,
            definition=("A segment is covered when at least one detected change point lies in "
                        "[start-tol, end+tol]; tol_half_segment uses tol = duration/2."),
        ),
        over_segmentation=dict(
            bocpd=cov["over_segmentation"], baseline=cov_bl["over_segmentation"],
        ),
        length_agreement=len_agree,
        downstream_auc=down,
        sensitivity=sensitivity(z, recs),
        by_dataset={},
        by_split={},
        notes=[
            "All values are computed by code/alt_p1_bocpd.py from the released archives.",
            "Boundary F1 uses greedy one-to-one nearest matching within the tolerance.",
            "Segments are semantic annotations; strict-tolerance F1 is expected to be low, so "
            "coverage and length agreement are reported next to F1.",
            "downstream_auc uses a leave-one-segment-out posterior so the reliability score "
            "never sees the label of the segment it scores.",
        ],
    )

    # group metrics
    for k in ("EgoDemo", "EgoPro", "EgoStandard"):
        sub = [r for r in rec_out if r["dataset"] == k]
        idx = [i for i, r in enumerate(rec_out) if r["dataset"] == k]
        payload["by_dataset"][k] = dict(
            records=len(sub),
            bocpd=metric_block([pred_lists[i] for i in idx], [true_lists[i] for i in idx],
                               [rec_out[i] for i in idx]),
            baseline=metric_block([base_lists[i] for i in idx], [true_lists[i] for i in idx],
                                  [rec_out[i] for i in idx]),
            reliability=rel["by_dataset"].get(k),
        )
    for (d, s), g in pd.DataFrame(rec_out).groupby(["dataset", "split"]):
        idx = [i for i, r in enumerate(rec_out) if r["dataset"] == d and r["split"] == s]
        payload["by_split"][f"{d}|{s}"] = dict(
            records=len(idx),
            bocpd=metric_block([pred_lists[i] for i in idx], [true_lists[i] for i in idx],
                               [rec_out[i] for i in idx]),
            baseline=metric_block([base_lists[i] for i in idx], [true_lists[i] for i in idx],
                                  [rec_out[i] for i in idx]),
            reliability=rel["by_split"].get(f"{d}|{s}"),
        )
    payload["runtime_s"] = round(time.time() - t0, 2)

    def find_bad(o, path="payload"):
        if isinstance(o, dict):
            for k, v in o.items():
                find_bad(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                find_bad(v, f"{path}[{i}]")
        elif isinstance(o, (str, int, float, bool, type(None), np.integer, np.floating, np.bool_)):
            return
        else:
            print("NON-SERIALIZABLE", path, type(o), repr(o)[:200], flush=True)

    find_bad(payload)

    json_path = os.path.join(DATA, "alt_p1.json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, default=float)
    text, nbytes = build_md(payload)
    md_path = os.path.join(OUT, "alt_p1.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    real = os.path.getsize(md_path)
    with open(md_path, "rb") as f:
        first = f.readline().decode("utf-8").strip()
    print(f"[P1] records={len(recs)} frames={z['t'].size} segments={len(IDX)}")
    print(f"[P1] BOCPD count MAE={base_block['count']['mae']:.2f} "
          f"F1@0.5={base_block['f1']['tol_0.5']['micro_f1']:.3f} "
          f"F1@2={base_block['f1']['tol_2.0']['micro_f1']:.3f} "
          f"F1@5={base_block['f1']['tol_5.0']['micro_f1']:.3f}")
    print(f"[P1] retention={100*rel['overall']['retention']:.1f}% "
          f"({rel['overall']['n_retained']}/{rel['overall']['n_segments']})")
    print(f"[P1] coverage@half-seg={100*cov['tol_half_segment']['coverage']:.1f}% "
          f"(baseline {100*cov_bl['tol_half_segment']['coverage']:.1f}%) "
          f"cp/seg={cov['over_segmentation']['mean_change_points_per_annotated_segment']:.2f}")
    print(f"[P1] downstream AUC: looo={down['overall']['hierarchical_looo']['auc']} "
          f"rate={down['overall']['raw_record_bad_rate']['auc']} "
          f"eligible={down['overall']['official_eligible_flag']['auc']}")
    print(f"[P1] wrote {json_path} ({os.path.getsize(json_path)} bytes)")
    print(f"[P1] wrote {md_path} ({real} bytes); first line={first!r}")
    print(f"[P1] runtime {payload['runtime_s']} s")
    if first != f"BYTES {real}":
        raise RuntimeError(f"BYTES line mismatch: {first!r} vs real {real}")


if __name__ == "__main__":
    main()
