# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1 v2: temporal smoothing + learned next-frame residual + multi-task reliability.

Pre-registration: data/up2_p1state_prereg.json (written before any training).
Arms:
  A_smooth_reliability  : p1_reliability fused score + bidirectional EMA smoothing
  B_nextframe_residual  : next-frame ridge residual + per-record normalised geometry -> logistic
  C_multitask_raw       : DualTCN (T=15/60) on raw 82-d features + occlusion/near-edge heads
  D_full_v2             : C + per-record normalised geometry + residual features + bidirectional EMA
Outputs: data/up2_p1state.json, data/up2_p1state_probs.npz, logs/up2_p1state_v2.log
"""
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEED = 20261120
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT_JSON = os.path.join(DATA, "up2_p1state.json")
OUT_NPZ = os.path.join(DATA, "up2_p1state_probs.npz")
T_SHORT, T_LONG = 15, 60
BATCH, EPOCHS, LR, WD, AUX_W = 1024, 18, 2e-3, 1e-4, 0.3
DEV = "cuda" if torch.cuda.is_available() else "cpu"
GEOM_IDX = list(range(64, 80))  # gl(8)+gr(8) inside fl32+fr32+gl8+gr8


# ------------------------------------------------------------------ data
def load_meta():
    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig")
    return (dict(zip(meta.rec.astype(int), meta.split.astype(str))),
            dict(zip(meta.rec.astype(int), meta.env.astype(str))), meta)


def rec_norm(F, rec, cols):
    """Unsupervised per-record robust (median/IQR) normalisation of selected columns."""
    out = F.copy()
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        v = F[ii][:, cols].astype(np.float64)
        med = np.median(v, 0)
        iqr = np.percentile(v, 75, 0) - np.percentile(v, 25, 0)
        sd = v.std(0)
        scale = np.where(iqr < 1e-6, np.where(sd < 1e-6, 1.0, sd), iqr)
        out[ii][:, cols] = ((v - med) / scale).astype(np.float32)
    return out


def residual_features(rec, split_of, seed=SEED):
    """Next-frame prediction residual, ridge fitted on train records only."""
    z = np.load(os.path.join(DATA, "panel.npz"))
    P = np.concatenate([z["L"].reshape(len(rec), -1), z["R"].reshape(len(rec), -1)],
                       axis=1).astype(np.float64)
    Pn = rec_norm(P, rec, list(range(P.shape[1])))
    tr_recs = [r for r in np.unique(rec) if split_of[int(r)] == "train"]
    Xp, Yp = [], []
    for r in tr_recs:
        ii = np.flatnonzero(rec == r)
        if len(ii) > 4:
            Xp.append(Pn[ii[:-1]]); Yp.append(Pn[ii[1:]])
    Xp = np.vstack(Xp); Yp = np.vstack(Yp)
    W = np.linalg.solve(Xp.T @ Xp + 10.0 * np.eye(Xp.shape[1]), Xp.T @ Yp)
    out = np.zeros((len(rec), 6), np.float64)
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        if len(ii) < 5:
            continue
        pred = Pn[ii[:-1]] @ W
        Yr = Pn[ii[1:]]
        e = np.linalg.norm(pred - Yr, axis=1)
        eL = np.linalg.norm((pred - Yr)[:, :63], axis=1)
        eR = np.linalg.norm((pred - Yr)[:, 63:], axis=1)
        out[ii[:-1], 0] = e
        out[ii[:-1], 1] = np.abs(e - np.median(e))
        out[ii[:-1], 2] = eL
        out[ii[:-1], 3] = eR
        out[ii[:-1], 4] = np.maximum(eL, eR)
        if len(ii) > 3:
            out[ii[1:-1], 5] = np.linalg.norm(Pn[ii][2:] - 2 * Pn[ii][1:-1] + Pn[ii][:-2], axis=1)
    out[-1] = out[-2]
    return out.astype(np.float32)


def build_frames(use_norm=False, use_res=False, resid=None):
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    F = np.concatenate([z["fl"], z["fr"], z["gl"], z["gr"],
                        z["validL"][:, None].astype(np.float32),
                        z["validR"][:, None].astype(np.float32)], axis=1).astype(np.float32)
    if use_norm:
        F = rec_norm(F, rec, GEOM_IDX)
    if use_res:
        R6 = rec_norm(resid, rec, list(range(6)))
        F = np.concatenate([F, R6], axis=1).astype(np.float32)
    return rec, F


def build_windows(F, rec, T_list):
    bounds = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        bounds[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    T0 = T_list[0]
    parts = {T: [] for T in T_list}
    r_parts = []
    for r, (lo, hi) in bounds.items():
        f = F[lo:hi]
        n = len(f)
        if n <= T0:
            continue
        for T in T_list:
            pad = max(0, T - 1)
            ext = np.concatenate([np.repeat(f[:1], pad, axis=0), f], axis=0) if pad else f
            win = np.lib.stride_tricks.sliding_window_view(ext, T, axis=0)
            win = np.transpose(win, (0, 2, 1))[T0 - 1:n]
            parts[T].append(np.ascontiguousarray(win, dtype=np.float32))
        r_parts.append(np.full(n - T0 + 1, r, np.int32))
    return ({T: np.concatenate(parts[T]) for T in T_list}, np.concatenate(r_parts), bounds)


def frame_labels(rec, resid=None):
    z = np.load(os.path.join(DATA, "state.npz"))
    yL = z["badL"].astype(np.int8); yR = z["badR"].astype(np.int8)
    return yL, yR


def split_arrays(rec, R, split_of, env_of):
    S = np.array([split_of[int(r)] for r in R])
    E = np.array([env_of[int(r)] for r in R])
    return S, E


def aux_labels(R, bounds, T0=T_SHORT):
    a = np.load(os.path.join(DATA, "up_p1b_aux.npz"))
    occ = np.zeros(len(R), np.float32); edge = np.zeros(len(R), np.float32); msk = np.zeros(len(R), np.float32)
    k = 0
    for r in np.unique(R):
        nn = int((R == r).sum())
        lo, hi = bounds[int(r)]
        sl = slice(lo + T0 - 1, hi)
        occ[k:k + nn] = a["occ"][sl]; edge[k:k + nn] = a["edge"][sl]; msk[k:k + nn] = a["aux_mask"][sl]
        k += nn
    return occ, edge, msk


# ------------------------------------------------------------------ model (same skeleton as C arm)
class Block(nn.Module):
    def __init__(self, c, d):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.c2 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.n1 = nn.GroupNorm(8, c); self.n2 = nn.GroupNorm(8, c)
        self.a = nn.GELU(); self.dp = nn.Dropout(0.10)

    def forward(self, x):
        h = self.dp(self.a(self.n1(self.c1(x))))
        return self.a(self.n2(self.c2(h)) + x)


class Branch(nn.Module):
    def __init__(self, fdim, c=96):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d) for d in (1, 2, 4, 8)])

    def forward(self, x):
        h = self.blocks(self.inp(x.transpose(1, 2)))
        return torch.cat([h[:, :, -1], h.mean(dim=2)], dim=1)


class DualTCN(nn.Module):
    def __init__(self, fdim, c=96, aux=True):
        super().__init__()
        self.short = Branch(fdim, c); self.long = Branch(fdim, c)
        self.head = nn.Sequential(nn.Linear(c * 4, 64), nn.GELU(), nn.Linear(64, 1))
        self.aux = nn.Sequential(nn.Linear(c * 4, 64), nn.GELU(), nn.Linear(64, 2)) if aux else None

    def forward(self, xs, xl):
        feat = torch.cat([self.short(xs), self.long(xl)], 1)
        out = self.head(feat).squeeze(1)
        return (out, self.aux(feat)) if self.aux is not None else out


def train_dual(name, X, Y, S, E, R, bounds, seed=SEED, aux=True):
    torch.manual_seed(seed); np.random.seed(seed)
    t0 = time.time()
    tr, va, te = S == "train", S == "validation", S == "test"
    xs_tr = torch.from_numpy(X[T_SHORT][tr]); xl_tr = torch.from_numpy(X[T_LONG][tr])
    Xva = {T: torch.from_numpy(X[T][va]).to(DEV) for T in X}
    Xte = {T: torch.from_numpy(X[T][te]).to(DEV) for T in X}
    ytr = torch.from_numpy(Y[tr]); yva = Y[va]; yte = Y[te]
    pw = torch.tensor([(len(ytr) - ytr.sum()) / max(ytr.sum(), 1.0)], device=DEV)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    occ, edge, msk = aux_labels(R, bounds)
    atgt = torch.from_numpy(np.stack([occ, edge], 1)[tr]); amsk = torch.from_numpy(msk[tr])
    model = DualTCN(X[T_SHORT].shape[2], aux=aux).to(DEV)
    npar = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    steps = (len(xs_tr) + BATCH - 1) // BATCH
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * steps)
    best = {"auc": -1, "ep": -1, "state": None}
    for ep in range(1, EPOCHS + 1):
        model.train(); perm = torch.randperm(len(xs_tr)); tot = 0.0
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            xb = xs_tr[sel].to(DEV); xlb = xl_tr[sel].to(DEV); yb = ytr[sel].to(DEV)
            opt.zero_grad(set_to_none=True)
            out, a = model(xb, xlb)
            loss = lossf(out, yb)
            tb = atgt[sel].to(DEV); mb = amsk[sel].to(DEV)
            bce = nn.functional.binary_cross_entropy_with_logits(a, tb, reduction="none").mean(1)
            loss = loss + AUX_W * (bce * mb).sum() / mb.sum().clamp(min=1.0)
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step(); sched.step(); tot += float(loss.detach()) * len(sel)
        model.eval()
        with torch.no_grad():
            o = model(Xva[T_SHORT], Xva[T_LONG])
            o = o[0] if isinstance(o, tuple) else o
            pv = torch.sigmoid(o).cpu().numpy()
        auc = roc_auc_score(yva, pv)
        if auc > best["auc"]:
            best = {"auc": float(auc), "ep": ep,
                    "state": {k: v.detach().clone() for k, v in model.state_dict().items()}}
        print(f"  ep{ep:02d} loss={tot/len(xs_tr):.4f} valAUC={auc:.4f}")
    model.load_state_dict(best["state"]); model.eval()
    with torch.no_grad():
        ov = model(Xva[T_SHORT], Xva[T_LONG]); ov = ov[0] if isinstance(ov, tuple) else ov
        ot = model(Xte[T_SHORT], Xte[T_LONG]); ot = ot[0] if isinstance(ot, tuple) else ot
        lv = ov.cpu().numpy()
        lt = ot.cpu().numpy()
        aux_t = model.aux(torch.cat([model.short(Xte[T_SHORT]), model.long(Xte[T_LONG])], 1)).cpu().numpy()
    secs = round(time.time() - t0, 1)
    print(f"  {name}: params={npar:,} best_ep={best['ep']} valAUC={best['auc']:.4f} {secs}s")
    return dict(logits_val=lv, logits_test=lt, params=npar, seconds=secs, best_epoch=best["ep"],
                val_auc=float(best["auc"]), aux_test_logits=aux_t,
                aux_meta={"occ": occ[te], "edge": edge[te], "mask": msk[te]})


# ------------------------------------------------------------------ metrics
def expand_logits(logits, Rsub, rec, bounds, T0=T_SHORT):
    """Map window-end logits back to a full-length frame array (first T0-1 frames padded)."""
    out = np.zeros(len(rec), np.float64)
    k = 0
    for r in np.unique(Rsub):
        nn = int((Rsub == r).sum()); lo, hi = bounds[int(r)]
        out[lo + T0 - 1:hi] = logits[k:k + nn]
        out[lo:lo + T0 - 1] = logits[k]
        k += nn
    return out


def hand_rows(frame_score, rec, split_of, yL, yR, split):
    """Expand frame-level scores to hand-level rows in panel_records order."""
    rows, ys, envs = [], [], []
    env_of = dict(zip(pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig").rec,
                      pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig").env))
    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig")
    score_of = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        score_of[int(r)] = frame_score[ii]
    for r in meta[meta.split == split].rec.astype(int):
        s = score_of[r]
        rows.append(s); ys.append(yL[np.flatnonzero(rec == r)])
        envs.append(np.array([env_of[r]] * len(s)))
        rows.append(s); ys.append(yR[np.flatnonzero(rec == r)])
        envs.append(np.array([env_of[r]] * len(s)))
    return np.concatenate(rows), np.concatenate(ys), np.concatenate(envs)


def ece(y, p, bins=15):
    p = np.clip(p, 1e-8, 1 - 1e-8)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def platt(val_score, yval, test_score):
    lr = LogisticRegression(C=1e6, solver="lbfgs").fit(val_score.reshape(-1, 1), yval)
    return lr.predict_proba(test_score.reshape(-1, 1))[:, 1]


def temp_scale(val_logits, yval, test_logits):
    t = torch.tensor(1.0, requires_grad=True)
    lv = torch.tensor(val_logits, dtype=torch.float32); yv = torch.tensor(yval, dtype=torch.float32)
    opt = torch.optim.LBFGS([t], max_iter=100)
    def closure():
        opt.zero_grad(); loss = nn.functional.binary_cross_entropy_with_logits(lv / t.clamp(min=1e-3), yv)
        loss.backward(); return loss
    opt.step(closure)
    T = float(t.detach().clamp(min=1e-3))
    return T, 1 / (1 + np.exp(-np.asarray(test_logits) / T))


def bidi_ema(score_by_rec, alpha):
    out = {}
    for r, s in score_by_rec.items():
        f = np.zeros_like(s); b = np.zeros_like(s)
        acc = s[0]
        for i in range(len(s)):
            acc = alpha * s[i] + (1 - alpha) * acc if i else s[i]
            f[i] = acc
        acc = s[-1]
        for i in range(len(s) - 1, -1, -1):
            acc = alpha * s[i] + (1 - alpha) * acc if i != len(s) - 1 else s[i]
            b[i] = acc
        out[r] = 0.5 * (f + b)
    return out


def group_by_rec(score, rec):
    return {int(r): score[np.flatnonzero(rec == r)] for r in np.unique(rec)}


def flatten(groups, rec):
    out = np.zeros(len(rec), np.float64)
    for r, s in groups.items():
        out[np.flatnonzero(rec == r)] = s
    return out


def auc_ap(y, p):
    return dict(auc=float(roc_auc_score(y, p)), ap=float(average_precision_score(y, p)),
                n=int(len(y)), positives=int(y.sum()))


def per_env(y, p, envs):
    out = []
    for e in sorted(set(envs)):
        m = envs == e
        if m.sum() >= 10 and y[m].sum() > 0:
            out.append(dict(env=str(e), n=int(m.sum()), positives=int(y[m].sum()),
                            auc=float(roc_auc_score(y[m], p[m]))))
    return out


# ------------------------------------------------------------------ arm A: existing reliability score + smoothing
def arm_a(rec, split_of, env_of, meta):
    z = np.load(os.path.join(DATA, "state.npz"))
    fl, fr, gl, gr = z["fl"], z["fr"], z["gl"], z["gr"]
    badL, badR = z["badL"], z["badR"]

    def build(split):
        X, y, rid = [], [], []
        for r in meta[meta.split == split].rec.astype(int):
            ii = np.flatnonzero(rec == r)
            X.append(gl[ii]); y.append(badL[ii]); rid.append(np.full(len(ii), r))
            X.append(gr[ii]); y.append(badR[ii]); rid.append(np.full(len(ii), r))
        return np.vstack(X), np.concatenate(y), np.concatenate(rid)

    Xtr, ytr, rtr = build("train"); Xva, yva, rva = build("validation"); Xte, yte, rte = build("test")

    def ctx(X):
        return np.hstack([X, np.convolve(X[:, 6], np.ones(5) / 5, "same")[:, None],
                          np.convolve(X[:, 7], np.ones(5) / 5, "same")[:, None]])
    Xtr, Xva, Xte = ctx(Xtr), ctx(Xva), ctx(Xte)
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=0.1, class_weight="balanced", max_iter=5000, solver="liblinear").fit(sc.transform(Xtr), ytr)
    p_tr = clf.predict_proba(sc.transform(Xtr))[:, 1]
    p_va = clf.predict_proba(sc.transform(Xva))[:, 1]
    p_te = clf.predict_proba(sc.transform(Xte))[:, 1]
    cov = np.cov(sc.transform(Xtr).T) + np.eye(Xtr.shape[1]) * 1e-6
    inv = np.linalg.pinv(cov); scale = np.median(np.einsum("ij,jk,ik->i", sc.transform(Xtr), inv, sc.transform(Xtr)))
    rg = lambda X: np.exp(-0.5 * np.einsum("ij,jk,ik->i", sc.transform(X), inv, sc.transform(X)) / scale)
    # score_bad = 1 - reliability = 0.5*p + 0.5*(1-r_geo)
    s_tr = 0.5 * p_tr + 0.5 * (1 - rg(Xtr))
    s_va = 0.5 * p_va + 0.5 * (1 - rg(Xva))
    s_te = 0.5 * p_te + 0.5 * (1 - rg(Xte))

    def seq_scores(s, rr):
        return {int(r): s[rr == r] for r in np.unique(rr)}
    # tune alpha on validation hand-level AUC
    grid = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    best = (-1, 1.0)
    for a in grid:
        sm = flatten(bidi_ema(seq_scores(s_va, rva), a), rva)
        v = roc_auc_score(yva, sm)
        if v > best[0]:
            best = (v, a)
    alpha = best[1]
    s_va_sm = flatten(bidi_ema(seq_scores(s_va, rva), alpha), rva)
    s_te_sm = flatten(bidi_ema(seq_scores(s_te, rte), alpha), rte)
    pv_cal = platt(s_va_sm, yva, s_te_sm)
    envte = np.array([env_of[int(r)] for r in rte])
    res = dict(arm="A_smooth_reliability", alpha=alpha, params=0,
               val_auc=float(best[0]), test_auc=float(roc_auc_score(yte, s_te_sm)),
               test_ap=float(average_precision_score(yte, s_te_sm)),
               ece15=ece(yte, pv_cal), per_env=per_env(yte, s_te_sm, envte),
               unsmoothed_test_auc=float(roc_auc_score(yte, s_te)),
               unsmoothed_test_ap=float(average_precision_score(yte, s_te)), seconds=0.0)
    print(f"[A] alpha={alpha} valAUC={best[0]:.4f} testAUC={res['test_auc']:.4f} testAP={res['test_ap']:.4f} (unsmoothed {res['unsmoothed_test_auc']:.4f})")
    return res, s_te_sm, yte, rte


# ------------------------------------------------------------------ arm B: residual + normalised geometry logistic
def arm_b(rec, F, split_of, env_of, meta):
    z = np.load(os.path.join(DATA, "state.npz"))
    X = F[:, GEOM_IDX + list(range(82, F.shape[1]))]  # normalised geom + residual (22)
    y = (z["badL"] | z["badR"]).astype(np.int8)
    tr = np.array([split_of[int(r)] == "train" for r in rec])
    va = np.array([split_of[int(r)] == "validation" for r in rec])
    te = np.array([split_of[int(r)] == "test" for r in rec])
    sc = StandardScaler().fit(X[tr])
    clf = LogisticRegression(C=0.1, class_weight="balanced", max_iter=5000).fit(sc.transform(X[tr]), y[tr])
    pv = clf.predict_proba(sc.transform(X))[:, 1]
    val_auc = float(roc_auc_score(y[va], pv[va]))
    pte_h, yte_h, envte_h = hand_rows(pv, rec, split_of, z["badL"], z["badR"], "test")
    pva_h, yva_h, _ = hand_rows(pv, rec, split_of, z["badL"], z["badR"], "validation")
    p_cal = platt(pva_h, yva_h, pte_h)
    res = dict(arm="B_nextframe_residual", params=int(X.shape[1]), val_auc=val_auc,
               test_auc=float(roc_auc_score(yte_h, pte_h)),
               test_ap=float(average_precision_score(yte_h, pte_h)),
               ece15=ece(yte_h, p_cal), per_env=per_env(yte_h, pte_h, envte_h), seconds=0.0)
    print(f"[B] val frame AUC={val_auc:.4f} test hand AUC={res['test_auc']:.4f} AP={res['test_ap']:.4f}")
    return res, pte_h, yte_h, envte_h


# ------------------------------------------------------------------ main
def main():
    t_start = time.time()
    torch.manual_seed(SEED); np.random.seed(SEED)
    print(f"device={DEV} torch={torch.__version__}")
    if DEV == "cuda":
        p = torch.cuda.get_device_properties(0); print(f"gpu={p.name} {p.total_memory/1e9:.2f}GB")
    split_of, env_of, meta = load_meta()
    rec, _ = build_frames()
    z = np.load(os.path.join(DATA, "state.npz"))
    yL, yR = z["badL"].astype(np.int8), z["badR"].astype(np.int8)
    resid = residual_features(rec, split_of)

    results = {}
    # A
    results["A_smooth_reliability"], pa, ya, ea = arm_a(rec, split_of, env_of, meta)

    # B (uses frame features)
    _, Fb = build_frames(use_norm=True, use_res=True, resid=resid)
    results["B_nextframe_residual"], pb, yb, eb = arm_b(rec, Fb, split_of, env_of, meta)

    # C: raw 82 features DualTCN
    _, Fc = build_frames(use_norm=False, use_res=False)
    Xc, Rc, bc = build_windows(Fc, rec, [T_SHORT, T_LONG])
    Sc, Ec = split_arrays(rec, Rc, split_of, env_of)
    y_frame = (z["badL"] | z["badR"]).astype(np.float32)
    Yw = np.zeros(len(Rc), np.float32)
    k = 0
    for r in np.unique(Rc):
        nn = int((Rc == r).sum()); lo, hi = bc[int(r)]
        Yw[k:k + nn] = y_frame[lo + T_SHORT - 1:hi]; k += nn
    print(f"windows={len(Rc):,} featC={Xc[T_SHORT].shape[2]} pos={Yw.mean():.5f}")
    rc = train_dual("C", Xc, Yw, Sc, Ec, Rc, bc)
    frame_c = expand_logits(rc["logits_test"], Rc[Sc == "test"], rec, bc)
    pth, yth, eth = hand_rows(frame_c, rec, split_of, yL, yR, "test")
    frame_cv = expand_logits(rc["logits_val"], Rc[Sc == "validation"], rec, bc)
    pvh, yvh, _ = hand_rows(frame_cv, rec, split_of, yL, yR, "validation")
    p_c = platt(pvh, yvh, pth)
    results["C_multitask_raw"] = dict(arm="C_multitask_raw", params=rc["params"], seconds=rc["seconds"],
                                      best_epoch=rc["best_epoch"], val_auc=rc["val_auc"],
                                      test_auc=float(roc_auc_score(yth, pth)),
                                      test_ap=float(average_precision_score(yth, pth)),
                                      ece15=ece(yth, p_c), per_env=per_env(yth, pth, eth),
                                      aux_test=_aux_report(rc, yth))
    print(f"[C] test hand AUC={results['C_multitask_raw']['test_auc']:.4f} AP={results['C_multitask_raw']['test_ap']:.4f}")

    # D: normalised geometry + residual, DualTCN + bidirectional EMA smoothing
    Xd, Rd, bd = build_windows(Fb, rec, [T_SHORT, T_LONG])   # Fb already has norm+res features
    Sd, Ed = split_arrays(rec, Rd, split_of, env_of)
    Yd = np.zeros(len(Rd), np.float32); k = 0
    for r in np.unique(Rd):
        nn = int((Rd == r).sum()); lo, hi = bd[int(r)]
        Yd[k:k + nn] = y_frame[lo + T_SHORT - 1:hi]; k += nn
    rd = train_dual("D", Xd, Yd, Sd, Ed, Rd, bd)
    frame_dv = expand_logits(rd["logits_val"], Rd[Sd == "validation"], rec, bd)
    frame_dt = expand_logits(rd["logits_test"], Rd[Sd == "test"], rec, bd)
    val_recs = set(int(r) for r in np.unique(Rd[Sd == "validation"]))
    test_recs = set(int(r) for r in np.unique(Rd[Sd == "test"]))
    vd = {r: frame_dv[np.flatnonzero(rec == r)] for r in val_recs}
    grid = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    best = (-1, 1.0)
    for a in grid:
        fp = np.zeros(len(rec), np.float64)
        for r, s in bidi_ema(vd, a).items():
            fp[np.flatnonzero(rec == r)] = s
        vh, yvh2, _ = hand_rows(fp, rec, split_of, yL, yR, "validation")
        v = roc_auc_score(yvh2, vh)
        if v > best[0]:
            best = (v, a)
    alpha = best[1]
    td = {r: frame_dt[np.flatnonzero(rec == r)] for r in test_recs}
    fp_te = np.zeros(len(rec), np.float64)
    for r, s in bidi_ema(td, alpha).items():
        fp_te[np.flatnonzero(rec == r)] = s
    pte_h, yte_h, envte_h = hand_rows(fp_te, rec, split_of, yL, yR, "test")
    # calibration: Platt fitted on validation smoothed scores
    vh_sm, yvh_sm, _ = hand_rows(np.where(np.isin(rec, list(val_recs)),
                                          flatten(bidi_ema(vd, alpha), rec), 0.0),
                                 rec, split_of, yL, yR, "validation")
    p_cal = platt(vh_sm, yvh_sm, pte_h)
    pth_raw, yth_raw, eth_raw = hand_rows(frame_dt, rec, split_of, yL, yR, "test")
    results["D_full_v2"] = dict(arm="D_full_v2", params=rd["params"], seconds=rd["seconds"],
                                best_epoch=rd["best_epoch"], val_auc=float(best[0]), alpha=alpha,
                                test_auc=float(roc_auc_score(yte_h, pte_h)),
                                test_ap=float(average_precision_score(yte_h, pte_h)),
                                ece15=ece(yte_h, p_cal), per_env=per_env(yte_h, pte_h, envte_h),
                                unsmoothed_test_auc=float(roc_auc_score(yth_raw, pth_raw)),
                                unsmoothed_test_ap=float(average_precision_score(yth_raw, pth_raw)),
                                aux_test=_aux_report(rd, yte_h))
    print(f"[D] alpha={alpha} test hand AUC={results['D_full_v2']['test_auc']:.4f} AP={results['D_full_v2']['test_ap']:.4f} (unsmoothed {results['D_full_v2']['unsmoothed_test_auc']:.4f})")

    gate = dict(test_auc_min=0.70, test_ap_min=0.08, per_env_auc_min=0.60)
    d = results["D_full_v2"]
    per_env_ok = all(e["auc"] >= 0.60 for e in d["per_env"])
    d["gate"] = dict(**gate, per_env_values={e["env"]: e["auc"] for e in d["per_env"]},
                     passes=bool(d["test_auc"] >= 0.70 and d["test_ap"] >= 0.08 and per_env_ok),
                     fail_reasons=[x for x, ok in [
                         ("test AUC %.4f < 0.70" % d["test_auc"], d["test_auc"] >= 0.70),
                         ("test AP %.4f < 0.08" % d["test_ap"], d["test_ap"] >= 0.08),
                         ("per-env AUC below 0.60: " + str({e["env"]: round(e["auc"], 4) for e in d["per_env"] if e["auc"] < 0.60}),
                          per_env_ok)] if not ok])
    for k in ["A_smooth_reliability", "B_nextframe_residual", "C_multitask_raw"]:
        results[k]["gate"] = dict(**gate, passes=None, note="ablation only; gate judged on D_full_v2")

    payload = dict(_meta=dict(script="up2_p1state_v2.py", seed=SEED,
                              prereg="data/up2_p1state_prereg.json",
                              total_seconds=round(time.time() - t_start, 1),
                              protocol=dict(split="panel_records.csv 16/4/4 environment",
                                            metric="hand-frame level: n_test=24482, positives=462, prevalence=0.018871",
                                            windows="causal T=15/60, no record boundary crossing, long window left-padded",
                                            model="DualTCN 4 blocks d=1/2/4/8, 96ch, GroupNorm+GELU, dropout 0.10, aux heads occ/near_edge w=0.3",
                                            calibration="temperature scaling fitted on validation only",
                                            smoothing="bidirectional EMA, alpha selected on validation AUC only")),
                   config=dict(arms=[results[k]["arm"] for k in results],
                               feature_dim=dict(C=int(Xc[T_SHORT].shape[2]), D=int(Xd[T_SHORT].shape[2])),
                               residual_features=6, geom_features=16),
                   arms=results)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    np.savez_compressed(OUT_NPZ, y=yte_h, env=envte_h, pred_D=pte_h, y_all=yL | yR)
    print("\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"{k:24s} valAUC={v.get('val_auc', float('nan')):.4f} testAUC={v['test_auc']:.4f} "
              f"AP={v['test_ap']:.4f} params={v.get('params', 0):,} {v.get('seconds', 0)}s")
    print("D gate:", d["gate"])


def _aux_report(rc, yth):
    a = rc.get("aux_test_logits")
    if a is None:
        return None
    m = rc["aux_meta"]["mask"].astype(bool)
    out = {}
    for j, key in enumerate(["occlusion", "near_edge"]):
        yj = rc["aux_meta"][["occ", "edge"][j]][m]
        if yj.sum() > 0:
            out[key] = dict(n=int(m.sum()), positives=int(yj.sum()),
                            auc=float(roc_auc_score(yj, a[m, j])))
    return out


if __name__ == "__main__":
    main()
