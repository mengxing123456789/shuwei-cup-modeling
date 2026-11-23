
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""C 题 P1-b 观测可靠性：GPU 时序模型（TCN）替代 CPU 逻辑回归+马氏距离。

对标基线（`data/p1_reliability.json`，CPU，10 个手工几何特征）：
    AUC_bad  test: 校准 0.5961 / 几何 0.6131 / 融合 0.6267
    AP       test: 融合 0.0407（正例率 0.0189 → 2.15x）
    per-env  test: 0011 -> 0.5281  (12,634 帧 / 426 正)   <-- 无信号
                   0041 -> 0.9383  ( 7,274 帧 /  36 正)

本脚本只做一件事：把「每帧 21 关键点」换成「每帧时序窗口 + 卷积感受野」，
在同一 record/env 划分上重算 AUC 与 AP，看 0.5281 那个环境能不能救回来。

纪律：
  - 划分用 panel_records.csv 的 split 列（record_split.csv 的 16/4/4 environment）
  - 窗口不跨记录边界
  - 早停看 validation AUC，test 只在最后评一次
  - 固定种子 20261120
"""
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score

SEED = 20261120
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA = os.path.abspath(DATA)
OUT = os.path.join(DATA, "p1b_calib.json")

T = 15          # 因果窗口 0.5 s @ 30 fps
BATCH = 1024
EPOCHS = 18
LR = 2e-3
WD = 1e-4
DEV = "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------------------------ 数据
def build(dataset_holdout=None):
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    feats = np.concatenate([
        z["fl"], z["fr"], z["gl"], z["gr"],
        z["validL"][:, None].astype(np.float32),
        z["validR"][:, None].astype(np.float32),
    ], axis=1).astype(np.float32)
    y = (z["badL"] | z["badR"]).astype(np.float32)

    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
    env_of = dict(zip(meta["rec"].astype(int), meta["env"].astype(str)))

    # 按记录切片（数据已按记录连续排列）
    bounds = {}
    for r in np.unique(rec):
        idx = np.flatnonzero(rec == r)
        bounds[int(r)] = (int(idx[0]), int(idx[-1]) + 1)

    X_parts, y_parts, s_parts, e_parts = [], [], [], []
    for r, (lo, hi) in bounds.items():
        f = feats[lo:hi]
        lb = y[lo:hi]
        n = len(f)
        if n <= T:
            continue
        # 因果窗口：第 i 个样本 = f[i-T+1 .. i]，标签 = lb[i]
        win = np.lib.stride_tricks.sliding_window_view(f, T, axis=0)  # (n-T+1, F, T)
        win = np.transpose(win, (0, 2, 1))                            # (N, T, F)
        X_parts.append(np.ascontiguousarray(win, dtype=np.float32))
        y_parts.append(lb[T - 1:])
        s_parts.append(np.array([split_of[r]] * len(y_parts[-1])))
        e_parts.append(np.array([env_of[r]] * len(y_parts[-1])))

    X = np.concatenate(X_parts, axis=0)
    Y = np.concatenate(y_parts, axis=0)
    S = np.concatenate(s_parts, axis=0)
    E = np.concatenate(e_parts, axis=0)
    del X_parts, y_parts, s_parts, e_parts
    return X, Y, S, E


# ------------------------------------------------------------------ 模型
class Block(nn.Module):
    def __init__(self, c, d):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.c2 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.n1 = nn.GroupNorm(8, c)
        self.n2 = nn.GroupNorm(8, c)
        self.a = nn.GELU()
        self.dp = nn.Dropout(0.10)

    def forward(self, x):
        h = self.dp(self.a(self.n1(self.c1(x))))
        h = self.n2(self.c2(h))
        return self.a(h + x)


class TCN(nn.Module):
    def __init__(self, fdim, c=96):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d) for d in (1, 2, 4, 8)])
        self.head = nn.Sequential(nn.Linear(c * 2, 64), nn.GELU(), nn.Linear(64, 1))

    def forward(self, x):                 # x: (B, T, F)
        h = x.transpose(1, 2)             # (B, F, T)
        h = self.blocks(self.inp(h))      # (B, C, T)
        feat = torch.cat([h[:, :, -1], h.mean(dim=2)], dim=1)
        return self.head(feat).squeeze(1)


# ------------------------------------------------------------------ 训练
def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    print(f"device={DEV}  torch={torch.__version__}")
    if DEV == "cuda":
        p = torch.cuda.get_device_properties(0)
        print(f"gpu={p.name}  {p.total_memory/1e9:.2f} GB  cap={p.major}.{p.minor}")

    t0 = time.time()
    X, Y, S, E = build()
    print(f"windows={len(X):,}  feat={X.shape[2]}  T={T}  pos_rate={Y.mean():.5f}  "
          f"build {time.time()-t0:.1f}s")

    tr = S == "train"
    va = S == "validation"
    te = S == "test"
    print(f"split  train={tr.sum():,}  val={va.sum():,}  test={te.sum():,}")

    Xtr = torch.from_numpy(X[tr])
    ytr = torch.from_numpy(Y[tr])
    Xva = torch.from_numpy(X[va]).to(DEV)
    yva = Y[va]
    Xte = torch.from_numpy(X[te]).to(DEV)
    yte = Y[te]
    Ete = E[te]

    pos = float(ytr.sum())
    neg = float(len(ytr) - pos)
    pw = torch.tensor([neg / max(pos, 1.0)], device=DEV)
    print(f"pos_weight={pw.item():.2f}")

    model = TCN(X.shape[2]).to(DEV)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"params={n_par:,}")

    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    steps = (len(Xtr) + BATCH - 1) // BATCH
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR,
                                                total_steps=EPOCHS * steps)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)

    best = {"auc": -1.0, "epoch": -1, "state": None}
    for ep in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(Xtr))
        tot, nseen = 0.0, 0
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            xb = Xtr[sel].to(DEV, non_blocking=True)
            yb = ytr[sel].to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            out = model(xb)
            loss = lossf(out, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            sched.step()
            tot += float(loss) * len(sel)
            nseen += len(sel)
        model.eval()
        with torch.no_grad():
            pv = torch.sigmoid(model(Xva)).cpu().numpy()
        auc = roc_auc_score(yva, pv)
        ap = average_precision_score(yva, pv)
        flag = ""
        if auc > best["auc"]:
            best = {"auc": float(auc), "epoch": ep,
                    "state": {k: v.detach().clone() for k, v in model.state_dict().items()}}
            flag = " *"
        print(f"ep{ep:02d}  loss={tot/nseen:.4f}  val AUC={auc:.4f}  val AP={ap:.4f}{flag}")

    model.load_state_dict(best["state"])
    model.eval()
    with torch.no_grad():
        pt = torch.sigmoid(model(Xte)).cpu().numpy()

    # --- calibration block (added): raw vs temperature-scaled ---
    from scipy.optimize import minimize_scalar
    def _logit(p):
        p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p))
    def _nll(T):
        q=1/(1+np.exp(-_logit(pv)/T))
        return -np.mean(yva*np.log(q+1e-12)+(1-yva)*np.log(1-q+1e-12))
    res=minimize_scalar(_nll,bounds=(0.25,4.0),method="bounded")
    Tcal=float(res.x)
    pcal=1/(1+np.exp(-_logit(pt)/Tcal))
    def _ece(p,y,nb=15):
        e=np.linspace(0,1,nb+1); tot=0.0
        for i in range(nb):
            m=(p>=e[i])&(p<=e[i+1] if i==nb-1 else p<e[i+1])
            if m.sum()>0: tot+=m.mean()*abs(p[m].mean()-y[m].mean())
        return float(tot)
    calib=dict(temperature=Tcal,val_nll_raw=float(_nll(1.0)),val_nll_cal=float(_nll(Tcal)),
               brier_raw=float(np.mean((pt-yte)**2)),brier_cal=float(np.mean((pcal-yte)**2)),
               ece15_raw=_ece(pt,yte),ece15_cal=_ece(pcal,yte),
               mean_prob_raw=float(pt.mean()),mean_prob_cal=float(pcal.mean()),base_rate=float(yte.mean()))
    # Platt scaling (a,b) on validation: fixes both slope and intercept
    from scipy.optimize import minimize as _min
    def _platt_nll(w):
        a,b=w
        q=1/(1+np.exp(-(a*_logit(pv)+b)))
        return -np.mean(yva*np.log(q+1e-12)+(1-yva)*np.log(1-q+1e-12))
    r2=_min(_platt_nll,x0=np.array([1.0,0.0]),method="Nelder-Mead")
    a_pl,b_pl=float(r2.x[0]),float(r2.x[1])
    ppl=1/(1+np.exp(-(a_pl*_logit(pt)+b_pl)))
    const=float(yte.mean())
    calib.update(platt_a=a_pl,platt_b=b_pl,
                 platt_val_nll=float(r2.fun),
                 brier_platt=float(np.mean((ppl-yte)**2)),
                 ece15_platt=_ece(ppl,yte),
                 mean_prob_platt=float(ppl.mean()),
                 brier_constant=float(np.mean((const-yte)**2)),
                 brier_constant_baserate=const)
    print("CALIB",json.dumps(calib,ensure_ascii=False))
    np.savez(os.path.join(DATA,"p1b_probs.npz"),pt=pt,pcal=pcal,ppl=ppl,yte=yte,env=Ete,
             pv=pv,yv=yva)  # validation scores kept for cost-weighted threshold selection

    res = {
        "_meta": {
            "model": "TCN(4 blocks, dilations 1/2/4/8, 96ch, GroupNorm, GELU) on GPU",
            "window_frames": T, "window_s": T / 30.0, "epochs": EPOCHS,
            "batch": BATCH, "lr": LR, "seed": SEED, "device": DEV,
            "features": "fl(32)+fr(32)+gl(8)+gr(8)+validL+validR = 82 dims/frame",
            "label": "badL | badR (annotated hand bad frame)",
            "split": "panel_records.csv split column (16/4/4 environment)",
            "baseline_cpu_test": {"auc_calibrated": 0.5961, "auc_geometry": 0.6131,
                                  "auc_fused": 0.6267, "ap_fused": 0.0407,
                                  "positive_rate": 0.0189},
        },
        "best_epoch": best["epoch"],
        "val_auc_at_best": best["auc"],
        "test_auc": float(roc_auc_score(yte, pt)),
        "test_ap": float(average_precision_score(yte, pt)),
        "test_positive_rate": float(yte.mean()),
        "test_ap_lift": float(average_precision_score(yte, pt) / yte.mean()),
        "per_env_test": [],
        "train_seconds": round(time.time() - t0, 1),
        "params": n_par,
    }
    res["calibration"]=calib
    for env in sorted(set(Ete)):
        m = Ete == env
        if m.sum() < 10 or Y[te][m].sum() == 0:
            continue
        res["per_env_test"].append({
            "env": str(env), "n": int(m.sum()), "positives": int(Y[te][m].sum()),
            "auc_bad": float(roc_auc_score(Y[te][m], pt[m])),
        })



    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    print()
    print("=== RESULT ===")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()