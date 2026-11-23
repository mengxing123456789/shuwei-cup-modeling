
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""One-factor ablation: change the regression target, keep everything else.

The first submission regressed *total* duration d on features measured inside a
released prefix of s seconds.  A prefix can only bound d from below (d >= s), so no
linear or shallow model can use it, and every downstream conclusion inherited the
symptom: longer prefix looked worse (MAE 2.939 / 2.972 / 3.290 s), the value of
re-observing came out negative, and masking channels bought nothing.

Here only one thing changes between the two arms:

    arm TOTAL     target = d            (the original formulation)
    arm RESIDUAL  target = d - s        (the quantity a scheduler needs)

Everything else is held fixed: same segments, same split, same features (all
measurable at time s, no hindsight), same ridge penalty selected on validation, same
MLP sizes and seed.  A second, purely geometric estimator is evaluated in the same
table:

    R_hat = s * (1 - phi_hat) / phi_hat ,   phi_hat predicted from the same features

with phi(s) = L(s)/L(T) used only as a *training target* (it is a hindsight quantity;
at run time the head predicts it).

Outputs
    data/residual_target.json
    data/residual_target_records.csv
"""
import json
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FPS = 30.0
PREFIXES = (0.2, 0.6, 1.0)
SEED = 20261120
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def build():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    segs = pd.read_csv(os.path.join(DATA, "segments.csv"))
    rec = st["rec"].astype(int)
    dom = st["dom"].astype(int)
    wrist = {0: st["fl"][:, 0:3].astype(np.float64), 1: st["fr"][:, 0:3].astype(np.float64)}
    sl = {}
    for r in recs.rec.astype(int):
        ii = np.flatnonzero(rec == r)
        sl[r] = (int(ii[0]), int(ii[-1]) + 1)

    rows = []
    for _, s in segs.iterrows():
        r = int(s.rec)
        if r not in sl:
            continue
        lo, hi = sl[r]
        a = lo + int(round(s.start * FPS))
        b = min(lo + int(round(s.end * FPS)), hi)
        if b - a < 8:
            continue
        w = wrist[int(dom[r])]
        traj = w[a:b]
        step = np.linalg.norm(np.diff(traj, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(step)])
        if cum[-1] <= 1e-9:
            continue
        phi = cum / cum[-1]
        d = float(s.end - s.start)
        if d <= 0:
            continue
        for pre in PREFIXES:
            k = int(round(pre * FPS))
            if k >= len(phi) - 1:
                continue
            sub = traj[:k + 1]
            stp = step[:k] if k > 0 else np.array([0.0])
            L = float(cum[k])
            net = float(np.linalg.norm(sub[-1] - sub[0]))
            v = stp / (1.0 / FPS)
            # direction reversals along the path, a curvature proxy that is causal
            dvec = np.diff(sub, axis=0)
            dirs = dvec / np.maximum(np.linalg.norm(dvec, axis=1, keepdims=True), 1e-9)
            if len(dirs) > 1:
                cosang = np.sum(dirs[1:] * dirs[:-1], axis=1)
                reversals = float(np.sum(cosang < 0.0))
            else:
                reversals = 0.0
            rows.append(dict(
                rec=r, seg=int(s.seg), split=str(s.split), dataset=str(s.dataset),
                dur=d, prefix=pre,
                f_prefix=pre, f_L=L, f_Lrate=L / pre, f_net=net,
                f_curv=L / max(net, 1e-6), f_vmean=float(v.mean()), f_vmax=float(v.max()),
                f_vstd=float(v.std()), f_rev=reversals, f_revrate=reversals / pre,
                f_pos0=float(sub[0, 0]), f_pos0y=float(sub[0, 1]), f_pos0z=float(sub[0, 2]),
                f_end=float(sub[-1, 0]), f_endy=float(sub[-1, 1]), f_endz=float(sub[-1, 2]),
                phi=float(min(max(phi[k], 1e-3), 0.999)),
                r_true=d - pre, d_true=d))
    df = pd.DataFrame(rows)
    df["fam"] = df.seg  # placeholder, replaced below
    return df, segs


FCOLS = ["f_prefix", "f_L", "f_Lrate", "f_net", "f_curv", "f_vmean", "f_vmax",
         "f_vstd", "f_rev", "f_revrate", "f_pos0", "f_pos0y", "f_pos0z",
         "f_end", "f_endy", "f_endz"]


def widen(df):
    """One-hot for dataset and family via the sid/seg label prefix."""
    d = pd.get_dummies(df, columns=["dataset"], prefix="ds")
    return d


class MLP(nn.Module):
    def __init__(self, n_in):
        super(MLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, 64), nn.GELU(), nn.Dropout(0.1),
            nn.Linear(64, 32), nn.GELU(),
            nn.Linear(32, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def fit_mlp(Xtr, ytr, Xva, yva, Xte, epochs=600, lr=3e-3):
    torch.manual_seed(SEED)
    m = MLP(Xtr.shape[1]).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-3)
    lossf = nn.SmoothL1Loss(beta=0.5)
    xt = torch.tensor(Xtr, dtype=torch.float32, device=DEV)
    yt = torch.tensor(ytr, dtype=torch.float32, device=DEV)
    xv = torch.tensor(Xva, dtype=torch.float32, device=DEV)
    yv = torch.tensor(yva, dtype=torch.float32, device=DEV)
    xe = torch.tensor(Xte, dtype=torch.float32, device=DEV)
    best, best_state, best_ep = 1e9, None, -1
    for ep in range(epochs):
        m.train()
        perm = torch.randperm(len(xt), device=DEV)
        for i in range(0, len(xt), 32):
            idx = perm[i:i + 32]
            opt.zero_grad()
            out = m(xt[idx])
            loss = lossf(out, yt[idx])
            loss.backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            v = float(torch.abs(m(xv) - yv).mean())
        if v < best - 1e-6:
            best, best_ep = v, ep
            best_state = {k: v2.detach().clone() for k, v2 in m.state_dict().items()}
    if best_state is not None:
        m.load_state_dict(best_state)
    m.eval()
    with torch.no_grad():
        pred = m(xe).cpu().numpy()
    return pred, best, best_ep


def evaluate(df):
    d = widen(df)
    cols = [c for c in d.columns if c.startswith("f_") or c.startswith("ds_")]
    res = {}
    for pre in PREFIXES:
        g = d[np.isclose(d.prefix, pre)]
        tr = g[g.split == "train"]
        va = g[g.split == "validation"]
        te = g[g.split == "test"]
        if len(te) < 10 or len(va) < 5:
            continue
        Xtr_all, Xva_all, Xte_all = (tr[cols].values, va[cols].values, te[cols].values)
        sc = StandardScaler().fit(Xtr_all)
        Xtr, Xva, Xte = sc.transform(Xtr_all), sc.transform(Xva_all), sc.transform(Xte_all)
        for arm, ycol in (("total", "d_true"), ("residual", "r_true")):
            ytr, yva, yte = tr[ycol].values, va[ycol].values, te[ycol].values
            # prefix-free baseline: family median of the same target, train only
            base = np.median(tr[ycol].values)
            mae_base = float(np.mean(np.abs(base - yte)))
            # ridge with the penalty chosen on validation
            best_a, best_v = None, 1e9
            for a in (0.3, 1.0, 3.0, 10.0, 30.0):
                rg = Ridge(alpha=a).fit(Xtr, ytr)
                v = float(np.mean(np.abs(rg.predict(Xva) - yva)))
                if v < best_v:
                    best_a, best_v = a, v
            pr = Ridge(alpha=best_a).fit(Xtr, ytr).predict(Xte)
            mae_r = float(np.mean(np.abs(pr - yte)))
            pm, mv, mep = fit_mlp(Xtr, ytr, Xva, yva, Xte)
            mae_m = float(np.mean(np.abs(pm - yte)))
            res["%s@%.1f" % (arm, pre)] = dict(
                n_train=int(len(tr)), n_val=int(len(va)), n_test=int(len(te)),
                target=ycol, ridge_alpha=best_a, ridge_val_mae=best_v,
                mae_baseline=mae_base, mae_ridge=mae_r, mae_mlp=mae_m,
                ratio_ridge=mae_r / max(mae_base, 1e-9),
                ratio_mlp=mae_m / max(mae_base, 1e-9),
                spearman_ridge=float(spearmanr(pr, yte).correlation),
                spearman_mlp=float(spearmanr(pm, yte).correlation),
                mlp_best_epoch=int(mep))
    return res


def progress_head(df):
    """Third estimator: predict phi from the same features, then R = s(1-phi)/phi."""
    d = widen(df)
    cols = [c for c in d.columns if c.startswith("f_") or c.startswith("ds_")]
    out = {}
    for pre in PREFIXES:
        g = d[np.isclose(d.prefix, pre)]
        tr, va, te = g[g.split == "train"], g[g.split == "validation"], g[g.split == "test"]
        if len(te) < 10 or len(va) < 5:
            continue
        sc = StandardScaler().fit(tr[cols].values)
        Xtr, Xva, Xte = (sc.transform(tr[cols].values), sc.transform(va[cols].values),
                         sc.transform(te[cols].values))
        # regress logit(phi) so the estimate stays inside (0, 1)
        def logit(p):
            p = np.clip(p, 1e-3, 1 - 1e-3)
            return np.log(p / (1 - p))
        ytr = logit(tr.phi.values)
        best_a, best_v = None, 1e9
        for a in (0.3, 1.0, 3.0, 10.0):
            rg = Ridge(alpha=a).fit(Xtr, ytr)
            v = float(np.mean(np.abs(rg.predict(Xva) - logit(va.phi.values))))
            if v < best_v:
                best_a, best_v = a, v
        ph = 1.0 / (1.0 + np.exp(-Ridge(alpha=best_a).fit(Xtr, ytr).predict(Xte)))
        ph = np.clip(ph, 0.02, 0.98)
        r_hat = np.minimum(pre * (1 - ph) / ph, 4.0 * te.d_true.values + 1.0)
        r_true = te.r_true.values
        base = float(np.median(tr.r_true.values))
        mae_base = float(np.mean(np.abs(base - r_true)))
        mae = float(np.mean(np.abs(r_hat - r_true)))
        out["progress@%.1f" % pre] = dict(
            n_test=int(len(te)), ridge_alpha=best_a,
            mae_baseline=mae_base, mae_progress=mae, ratio=mae / max(mae_base, 1e-9),
            spearman=float(spearmanr(r_hat, r_true).correlation),
            note="phi is predicted (logit scale) from the same causal features; it is "
                 "not read off the full trajectory at run time.")
    return out


def main():
    df, segs = build()
    res = evaluate(df)
    res.update(progress_head(df))
    seq = {}
    for arm in ("total", "residual"):
        v = [res.get("%s@%.1f" % (arm, p), {}).get("mae_mlp") for p in PREFIXES]
        if all(x is not None for x in v):
            seq[arm] = dict(mae_by_prefix=v, improves=bool(v[0] > v[1] > v[2]))
    gp = [res.get("progress@%.1f" % p, {}).get("mae_progress") for p in PREFIXES]
    if all(x is not None for x in gp):
        seq["progress"] = dict(mae_by_prefix=gp, improves=bool(gp[0] > gp[1] > gp[2]))
    audit = dict(
        script="residual_target.py", device=DEV, seed=SEED,
        torch=torch.__version__, prefixes=list(PREFIXES),
        n_segments=int(len(df[df.prefix == PREFIXES[0]])),
        n_records=int(df.rec.nunique()),
        manipulation="only the regression target changes between the two arms; "
                     "features, split, penalties, MLP sizes and seed are shared",
        three_estimators="ridge / MLP on the causal features, plus a progress head "
                         "that predicts phi and applies R=s(1-phi)/phi",
        results=res, sequences=seq)
    with open(os.path.join(DATA, "residual_target.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    df.to_csv(os.path.join(DATA, "residual_target_records.csv"), index=False,
              encoding="utf-8")
    print("segments %d  records %d  device %s" % (audit["n_segments"], audit["n_records"], DEV))
    hdr = "%-12s%6s%9s%9s%9s%9s%8s" % ("key", "n", "base", "ridge", "mlp", "r/mlp", "rho")
    print(hdr)
    for k in sorted(res):
        o = res[k]
        if "mae_mlp" in o:
            print("%-12s%6d%9.4f%9.4f%9.4f%9.3f%8.3f" % (
                k, o["n_test"], o["mae_baseline"], o["mae_ridge"], o["mae_mlp"],
                o["ratio_mlp"], o["spearman_mlp"]))
        else:
            print("%-12s%6d%9.4f%9s%9.4f%9.3f%8.3f" % (
                k, o["n_test"], o["mae_baseline"], "-", o["mae_progress"], o["ratio"],
                o["spearman"]))
    print("improves with prefix:", seq)


if __name__ == "__main__":
    main()