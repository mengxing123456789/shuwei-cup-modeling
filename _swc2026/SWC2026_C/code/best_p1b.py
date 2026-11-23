
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-b 最强单点：可靠度估计器 —— 两个臂在同一脚本、同一 split、同一 seed 下配对对比。

臂 A（对照，复刻 data/p1b_gpu.json 的配方）：TCN 96ch dropout .10，window 15，batch 1024，
        lr 2e-3 OneCycle，18 epochs，硬标签，全精度（frozen 检验：best_epoch=1）。
臂 B（候选）：同架构 + 只加「不破坏时间对齐」的增强（帧遮挡 / 通道 dropout / 高斯噪声，
        不做时间 roll —— roll 会让标签指向的最后一帧错位），10 epochs OneCycle，
        早停 patience 3，逐特征标准化，标签 eps=0.01。

两臂共用：验证集温度标定（temperature scaling）、Brier、ECE(15)、可靠性曲线、
逐环境 AUC（含 0011）、测试集按记录 cluster bootstrap 的配对 AUC/AP 差 95% CI。

输出 data/best_p1b.json（不覆盖 p1b_gpu.json）。
"""
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

SEED = 20261120
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "best_p1b.json")
T = 15
BATCH = 1024
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def build():
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    feats = np.concatenate([z["fl"], z["fr"], z["gl"], z["gr"],
                            z["validL"][:, None].astype(np.float32),
                            z["validR"][:, None].astype(np.float32)], axis=1).astype(np.float32)
    y = (z["badL"] | z["badR"]).astype(np.float32)
    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
    env_of = dict(zip(meta["rec"].astype(int), meta["env"].astype(str)))
    Xs, Ys, Ss, Es, Rs = [], [], [], [], []
    for r in np.unique(rec):
        idx = np.flatnonzero(rec == r)
        lo, hi = int(idx[0]), int(idx[-1]) + 1
        f, lb = feats[lo:hi], y[lo:hi]
        if len(f) <= T:
            continue
        w = np.lib.stride_tricks.sliding_window_view(f, T, axis=0)  # (n-T+1, F, T)
        Xs.append(np.ascontiguousarray(w, dtype=np.float32))
        n = w.shape[0]
        Ys.append(lb[T - 1:])
        Ss.append(np.array([split_of[int(r)]] * n))
        Es.append(np.array([env_of[int(r)]] * n))
        Rs.append(np.array([int(r)] * n))
    return (np.concatenate(Xs), np.concatenate(Ys), np.concatenate(Ss),
            np.concatenate(Es), np.concatenate(Rs))


class Block(nn.Module):
    def __init__(self, c, d, p):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.c2 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.n1, self.n2 = nn.GroupNorm(8, c), nn.GroupNorm(8, c)
        self.a, self.dp = nn.GELU(), nn.Dropout(p)

    def forward(self, x):
        h = self.dp(self.a(self.n1(self.c1(x))))
        return self.a(h + self.n2(self.c2(h)))


class TCN(nn.Module):
    def __init__(self, fdim, c=96, p=0.10, head=64):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d, p) for d in (1, 2, 4, 8)])
        self.head = nn.Sequential(nn.Linear(c * 2, head), nn.GELU(),
                                  nn.Linear(head, 1))

    def forward(self, x):
        h = self.blocks(self.inp(x))
        return self.head(torch.cat([h[:, :, -1], h.mean(2)], 1)).squeeze(1)


def aug(xb):
    """只做不破坏时间对齐的增强：随机 1-2 帧遮挡（置为特征均值 0）、通道 dropout、噪声。"""
    B, F, Tn = xb.shape
    nm = torch.randint(0, 3, (B,), device=xb.device)
    tg = torch.arange(Tn, device=xb.device)[None, :]
    for k in (1, 2):
        sel = torch.nonzero(nm == k).squeeze(1)
        if len(sel):
            st = torch.randint(0, Tn - k + 1, (len(sel),), device=xb.device)
            m = ((tg >= st[:, None]) & (tg < st[:, None] + k)).float()
            xb[sel] = xb[sel] * (1 - m)[:, None, :]
    ch = (torch.rand(B, F, device=xb.device) < 0.03).float()
    return xb * (1 - ch)[:, :, None] + 0.05 * torch.randn_like(xb)


def ece(y, p, bins=15):
    edges = np.linspace(0, 1, bins + 1)
    e, curve = 0.0, []
    for i in range(bins):
        m = (p >= edges[i]) & (p <= edges[i + 1])
        if m.sum() == 0:
            continue
        conf, acc = float(p[m].mean()), float(y[m].mean())
        e += float(m.mean()) * abs(conf - acc)
        curve.append(dict(bin=i, lo=float(edges[i]), hi=float(edges[i + 1]), n=int(m.sum()),
                          mean_prob=conf, frac_pos=acc))
    return float(e), curve


def train_arm(cfg, Xtr, ytr, Xva, yva, Xte):
    torch.manual_seed(SEED)
    model = TCN(cfg["fdim"], cfg.get("ch", 96), cfg.get("drop", 0.10),
                cfg.get("head", 64)).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"],
                            weight_decay=cfg.get("wd", 0.0))
    ep = cfg["epochs"]
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=cfg["lr"], total_steps=ep * cfg["steps"], pct_start=cfg.get("pct", 0.3))
    ytr_eps = ytr * (1 - 2 * cfg.get("eps", 0.0)) + cfg.get("eps", 0.0)
    pos = float(ytr.sum())
    pw = torch.tensor([min((len(ytr) - pos) / max(pos, 1.0), cfg.get("pwclip", 1e9))],
                      device=DEV)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    ytr_t = torch.from_numpy(ytr_eps.astype(np.float32))
    best = {"auc": -1.0, "epoch": -1, "state": None, "val_ap": -1.0, "stale": 0}
    hist = []
    for e in range(1, ep + 1):
        model.train()
        perm = torch.randperm(len(Xtr))
        tot, n = 0.0, 0
        for i in range(cfg["steps"]):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            xb = Xtr[sel].clone().to(DEV, non_blocking=True)
            if cfg.get("aug"):
                xb = aug(xb)
            yb = ytr_t[sel].to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            loss = lossf(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            sched.step()
            tot += float(loss.detach()) * len(sel)
            n += len(sel)
        model.eval()
        with torch.no_grad():
            lv = model(Xva).cpu().numpy()
        auc = float(roc_auc_score(yva, lv))
        ap = float(average_precision_score(yva, lv))
        hist.append(dict(epoch=e, train_loss=tot / n, val_auc=auc, val_ap=ap))
        star = ""
        if auc > best["auc"]:
            best = {"auc": auc, "epoch": e, "val_ap": ap, "stale": 0,
                    "state": {k: v.detach().clone() for k, v in model.state_dict().items()}}
            star = " *"
        else:
            best["stale"] = best.get("stale", 0) + 1
        print(f"  [{cfg['name']}] ep{e:02d} loss={tot/n:.4f} valAUC={auc:.4f} "
              f"valAP={ap:.4f}{star}")
        if best["stale"] >= cfg.get("patience", 99):
            print(f"  [{cfg['name']}] early stop at ep{e}")
            break
    model.load_state_dict(best["state"])
    model.eval()
    with torch.no_grad():
        lv = model(Xva).cpu().numpy()
        lt = model(Xte).cpu().numpy()
    return dict(model=model, logit_val=lv, logit_test=lt, hist=hist,
                best_epoch=best["epoch"], val_auc=best["auc"], val_ap=best["val_ap"],
                params=sum(p.numel() for p in model.parameters()))


def calibrate(yva, lv, lte, yte):
    ts = np.linspace(0.3, 6.0, 400)
    bce = [float(np.mean(np.logaddexp(0, lv / t) - yva * (lv / t))) for t in ts]
    Tb = float(ts[int(np.argmin(bce))])
    pv = 1 / (1 + np.exp(-lv / Tb))
    pt = 1 / (1 + np.exp(-lte / Tb))
    e, curve = ece(yte, pt)
    # 保序回归（isotonic）：只在验证集 logits 上拟合，测试集只做 transform
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(1 / (1 + np.exp(-lv)), yva)
    pt_iso = np.clip(iso.predict(1 / (1 + np.exp(-lte))), 1e-6, 1 - 1e-6)
    e_iso, curve_iso = ece(yte, pt_iso)
    pv_iso = np.clip(iso.predict(1 / (1 + np.exp(-lv))), 1e-6, 1 - 1e-6)
    return dict(temperature=Tb, pv=pv, pt=pt, ece=e, curve=curve,
                brier=float(brier_score_loss(yte, pt)),
                brier_raw=float(brier_score_loss(yte, 1 / (1 + np.exp(-lte)))),
                pt_iso=pt_iso, ece_iso=e_iso, curve_iso=curve_iso,
                brier_iso=float(brier_score_loss(yte, pt_iso)),
                brier_val_iso=float(brier_score_loss(yva, pv_iso)),
                brier_val_temp=float(brier_score_loss(yva, pv)))


def main():
    np.random.seed(SEED)
    print(f"device={DEV} torch={torch.__version__}")
    t0 = time.time()
    X, Y, S, E, R = build()
    tr, va, te = S == "train", S == "validation", S == "test"
    print(f"windows={len(X):,} feat={X.shape[1]} T={X.shape[2]} pos_rate={Y.mean():.5f} "
          f"train/val/test={tr.sum()}/{va.sum()}/{te.sum()}")
    mu = X[tr].mean(axis=(0, 2))
    sd = X[tr].std(axis=(0, 2)) + 1e-6

    def nz(a):
        return torch.from_numpy(((a - mu[:, None]) / sd[:, None]).astype(np.float32))

    Xraw = (torch.from_numpy(X[tr]), torch.from_numpy(X[va]).to(DEV),
            torch.from_numpy(X[te]).to(DEV))
    Xstd = (nz(X[tr]), nz(X[va]).to(DEV), nz(X[te]).to(DEV))
    ytr, yva, yte = Y[tr], Y[va], Y[te]
    Ete, Rte = E[te], R[te]
    steps = (len(Xraw[0]) + BATCH - 1) // BATCH

    arms = {
        "A_exact_replica": dict(name="A_exact_replica", fdim=X.shape[1], steps=steps,
                                lr=2e-3, epochs=18, pct=0.3, drop=0.10, ch=96, head=64,
                                wd=1e-4, aug=False, eps=0.0, patience=99, std=False),
        "B_std_only": dict(name="B_std_only", fdim=X.shape[1], steps=steps,
                           lr=2e-3, epochs=14, pct=0.3, drop=0.10, ch=96, head=64,
                           wd=1e-4, aug=False, eps=0.0, patience=3, std=True),
        "C_aug_longer": dict(name="C_aug_longer", fdim=X.shape[1], steps=steps,
                             lr=2e-3, epochs=12, pct=0.3, drop=0.10, ch=96, head=64,
                             wd=1e-4, aug=True, eps=0.01, patience=3, std=True),
    }
    res = {}
    for k, cfg in arms.items():
        print(f"\n=== arm {k} ===")
        pack = Xstd if cfg["std"] else Xraw
        r = train_arm(cfg, pack[0], ytr, pack[1], yva, pack[2])
        c = calibrate(yva, r["logit_val"], r["logit_test"], yte)
        p_raw = 1 / (1 + np.exp(-r["logit_test"]))
        res[k] = dict(
            config={kk: vv for kk, vv in cfg.items() if kk not in ("name", "fdim", "steps")},
            params=r["params"], best_epoch=r["best_epoch"], val_auc_at_best=r["val_auc"],
            val_ap_at_best=r["val_ap"],
            temperature=c["temperature"],
            test_auc=float(roc_auc_score(yte, c["pt"])),
            test_ap=float(average_precision_score(yte, c["pt"])),
            test_ap_raw=float(average_precision_score(yte, p_raw)),
            brier=c["brier"], brier_raw=c["brier_raw"], ece15=c["ece"],
            reliability=c["curve"], history=r["hist"],
            ece15_iso=c["ece_iso"], brier_iso=c["brier_iso"],
            brier_val_iso=c["brier_val_iso"], brier_val_temp=c["brier_val_temp"],
            reliability_iso=c["curve_iso"],
            logit_test=r["logit_test"].tolist(),
            logit_val=r["logit_val"].tolist(),
        )
        for env in sorted(set(Ete)):
            m = Ete == env
            res[k].setdefault("per_env_test", []).append(dict(
                env=str(env), n=int(m.sum()), positives=int(yte[m].sum()),
                auc_bad=float(roc_auc_score(yte[m], c["pt"][m]))
                if yte[m].sum() > 0 and yte[m].sum() < m.sum() else None))
        print(f"  test AUC={res[k]['test_auc']:.4f} AP={res[k]['test_ap']:.4f} "
              f"Brier={c['brier']:.6f} ECE={c['ece']:.4f} T={c['temperature']:.2f}")

    # risk-coverage: 只保留概率最高的 x% 帧，看留存的坏帧率与召回（下游按概率筛帧）
    for k in res:
        p = np.array(res[k]["logit_test"])
        p = 1 / (1 + np.exp(-p))
        order = np.argsort(-p)
        rc = []
        for cov in [1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.2, 0.1]:
            n = max(1, int(round(cov * len(p))))
            keep = order[:n]
            rc.append(dict(keep_frac=cov, n=n, bad_rate=float(yte[keep].mean()),
                           recall_bad=float(yte[keep].sum() / max(1, yte.sum()))))
        res[k]["risk_coverage"] = rc

    # paired cluster bootstrap over test records
    rng = np.random.default_rng(SEED)
    recs = np.unique(Rte)
    ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    boots = {}
    for cand in ["B_std_only", "C_aug_longer"]:
        lA = np.array(res["A_exact_replica"]["logit_test"])
        lB = np.array(res[cand]["logit_test"])
        d_auc, d_ap = [], []
        for _ in range(2000):
            pick = rng.choice(recs, len(recs), replace=True)
            idx = np.concatenate([np.flatnonzero(Rte == r) for r in pick])
            yy = yte[idx]
            if yy.sum() == 0 or yy.sum() == len(yy):
                continue
            d_auc.append(roc_auc_score(yy, lB[idx]) - roc_auc_score(yy, lA[idx]))
            d_ap.append(average_precision_score(yy, lB[idx])
                        - average_precision_score(yy, lA[idx]))
        boots[f"{cand}_vs_A_exact_replica"] = dict(
            d_auc_mean=float(np.mean(d_auc)), d_auc_ci95=ci(d_auc),
            d_ap_mean=float(np.mean(d_ap)), d_ap_ci95=ci(d_ap),
            n_boot=len(d_auc), cluster="record", n_clusters=int(len(recs)))

    out = dict(
        _meta=dict(
            purpose="P1-b 可靠度估计：同架构、同 split、同 seed 的三臂配对对比 + 概率校准",
            model="TCN 4 blocks(d=1/2/4/8) 96ch GroupNorm GELU + 64-unit head（无 head dropout）",
            window_frames=T, window_s=T / 30.0, batch=BATCH, seed=SEED, device=DEV,
            features="82 dims/frame (fl32+fr32+gl8+gr8+validL+validR)",
            label="badL | badR", split="panel_records.csv split (16/4/4 env)",
            prev_run="data/p1b_gpu.json test_auc=0.822032 AP=0.067556 best_epoch=1",
            arms_note="A=原配方精确复刻（raw 特征, wd 1e-4）；B=A+逐特征标准化；"
                      "C=B+不破坏时间对齐的增强（帧遮挡/通道dropout/噪声）+ 标签 eps=0.01 + 早停",
            augmentation_warning="不做时间 roll：roll 会让窗口最后一帧与标签错位（第一版实测 val AUC 掉到 0.806）"),
        arms=res, paired_bootstrap=boots, seconds=round(time.time() - t0, 1))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n=== SUMMARY ===")
    print(f"{'arm':22s} {'AUC':>7s} {'AP':>7s} {'Brier':>9s} {'ECE':>7s} {'ep':>4s} {'T':>5s}")
    for k, v in res.items():
        print(f"{k:22s} {v['test_auc']:.4f} {v['test_ap']:.4f} {v['brier']:.6f} "
              f"{v['ece15']:.4f} {v['best_epoch']:4d} {v['temperature']:5.2f}")
    for k, v in boots.items():
        print(f"{k}: dAUC={v['d_auc_mean']:+.4f} {v['d_auc_ci95']} "
              f"dAP={v['d_ap_mean']:+.5f} {v['d_ap_ci95']}")
    print(f"saved -> {OUT} ({out['seconds']}s)")


if __name__ == "__main__":
    main()