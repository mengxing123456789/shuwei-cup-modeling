
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""C 题 P2：缺失观测下的位置预测 —— 自建随机段掩码 × 三种缺失处理机制

问题：现有 `train_gpu_p2.py` 只用「窗口内零坏帧」的干净窗口（`clean` 过滤），
等于把带缺失的片段全部丢掉。P2 要求「缺失观测下的预测与再观测」，所以必须回答：
    当上下文窗口里有一部分帧不可用时，怎么填、要不要把「哪帧不可用」告诉模型？

三臂（同一骨架 GRU-128×2、同一 CTX=10、同一 L=30 帧=1.0 s、同一 seed）：
  A `clean_only`  ：训练只用干净窗口，不加掩码通道（现状做法，缺失时的对照）
  B `locf_mask`   ：训练 = 干净 + 随机段掩码副本；被掩位置用**前值保持(LOCF)**填；附 1 维观测指示通道
  C `interp_mask` ：训练 = 干净 + 随机段掩码副本；被掩位置用**线性插值**填；附 1 维观测指示通道

评测：test 上 4 档掩码长度 k∈{0,1,3,6} 帧（k=0 即无缺失）。掩码位置固定 seed，三臂共用同一批扰动，
保证配对可比。指标 = 全视界 RMSE（cm）、末点 RMSE（cm）、within-2cm。

纪律：掩码是**输入侧**扰动，不使用 badL/badR 标签；模型选择按官方 information_rule 在 validation 上做
（统一用 **k=0（无缺失）的 val RMSE** 选 epoch，与原始脚本一致，保证 A 臂能复现 3.31 cm，保证三臂同一把尺）。
"""
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

SEED = 20261120
CTX = 10          # 上下文 10 帧（≈0.33 s），与 train_gpu_p2.py 一致
LHOR = 30         # 预测 30 帧 = 1.0 s
DEV = "cuda" if torch.cuda.is_available() else "cpu"
BATCH = 512
EPOCHS = 40
LR = 2e-3
AUG_COPIES = 1     # 每个干净窗口额外生成 2 个掩码副本（含原件=3 倍数据）
KMAX_TRAIN = 6     # 训练时掩码长度上限
KS_EVAL = [0, 1, 3, 6]

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "p2_masked.json")

WRIST_L = slice(0, 3)
WRIST_R = slice(32, 35)


def load():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    rec, dom = st["rec"].astype(np.int64), st["dom"].astype(np.int64)
    rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]], axis=1).astype(np.float32)
    badL, badR = st["badL"], st["badR"]
    slices = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        slices[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    return recs, rec, dom, badL, badR, rich, slices


def windows(recs, rec, dom, badL, badR, rich, slices, split, L):
    Xs, Ys = [], []
    for r in recs[recs.split == split].rec.astype(int):
        lo, hi = slices[r]
        d = int(dom[r])
        bad = (badL[lo:hi] if d == 0 else badR[lo:hi]).astype(bool)
        wrist = rich[lo:hi, WRIST_L if d == 0 else WRIST_R]
        n = hi - lo
        span = CTX + L
        if n <= span:
            continue
        clean = np.lib.stride_tricks.sliding_window_view(bad, span).sum(axis=1) == 0
        idx = np.flatnonzero(clean)
        if len(idx) == 0:
            continue
        anchor = wrist[idx + CTX - 1]
        seg = np.lib.stride_tricks.sliding_window_view(rich[lo:hi], CTX, axis=0)
        seg = np.transpose(seg, (0, 2, 1))[idx].copy()
        seg[:, :, 0:3] -= anchor[:, None, :]
        seg[:, :, 32:35] -= anchor[:, None, :]
        tgt = wrist[idx[:, None] + CTX + np.arange(L)[None, :]] - anchor[:, None, :]
        Xs.append(seg.astype(np.float32))
        Ys.append(tgt.astype(np.float32))
    if not Xs:
        return None, None
    return np.concatenate(Xs), np.concatenate(Ys)


def nan_to_num(a):
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)


def apply_mask(x, pos, mode):
    """x: (CTX,80) 已锚定坐标；pos: 不可用帧下标（升序）；mode: locf|interp。
    返回 (x2, m) —— x2 为填充后窗口，m 为观测指示（1=观测到）。"""
    x2 = x.copy()
    m = np.ones(CTX, dtype=np.float32)
    m[pos] = 0.0
    if mode == "locf":
        for p in pos:
            src = p - 1
            while src >= 0 and src in pos:
                src -= 1
            if src < 0:
                src = p  # 整段缺到开头：保持自身（等价于零位移假设）
            x2[p] = x[src]
    else:  # interp
        ipos = list(pos)
        i = 0
        while i < len(ipos):
            a = ipos[i]
            b = a
            while i + 1 < len(ipos) and ipos[i + 1] == b + 1:
                i += 1
                b = ipos[i]
            left, right = a - 1, b + 1
            for t in range(a, b + 1):
                if left >= 0 and right < CTX:
                    w = (t - left) / float(right - left)
                    x2[t] = (1.0 - w) * x[left] + w * x[right]
                elif left >= 0:
                    x2[t] = x[left]
                elif right < CTX:
                    x2[t] = x[right]
            i += 1
    return x2, m


def make_aug(X, kmax, mode, seed):
    rng = np.random.default_rng(seed)
    XA, MA = [], []
    n = len(X)
    for c in range(AUG_COPIES):
        for i in range(n):
            k = int(rng.integers(1, kmax + 1))
            pos = sorted(rng.choice(CTX, size=k, replace=False).tolist())
            x2, m = apply_mask(X[i], pos, mode)
            XA.append(x2)
            MA.append(m)
    return np.stack(XA), np.stack(MA)


def eval_mask(X, k, mode, seed):
    """把 test 窗口按固定 seed 施加长度 k 的掩码，返回 (X2, M)。k=0 时 M 全 1。"""
    if k == 0:
        return X, np.ones((len(X), CTX), dtype=np.float32)
    rng = np.random.default_rng(seed)
    XA, MA = [], []
    for i in range(len(X)):
        pos = sorted(rng.choice(CTX, size=k, replace=False).tolist())
        x2, m = apply_mask(X[i], pos, mode)
        XA.append(x2)
        MA.append(m)
    return np.stack(XA), np.stack(MA)


class Seq(nn.Module):
    def __init__(self, fdim, L, h=128):
        super().__init__()
        self.gru = nn.GRU(fdim, h, num_layers=2, batch_first=True, dropout=0.10)
        self.head = nn.Sequential(nn.Linear(h, 256), nn.GELU(), nn.Dropout(0.10),
                                  nn.Linear(256, L * 3))
        self.L = L

    def forward(self, x):
        _, hn = self.gru(x)
        return self.head(hn[-1]).view(-1, self.L, 3)


def cat_mask(X, M):
    return torch.from_numpy(np.concatenate([X, M[:, :, None]], axis=2))


def metrics(pred, y):
    e = pred - y
    d = np.sqrt((e ** 2).sum(axis=2))          # (N,L)
    end = d[:, -1]
    return dict(rmse=float(np.sqrt((d ** 2).mean())) * 100.0,
                end_rmse=float(np.sqrt((end ** 2).mean())) * 100.0,
                med=float(np.median(end)) * 100.0,
                within_2cm=float((end < 0.02).mean()))


def run_arm(name, Xtr, Ytr, Xva, Yva, Xte, Yte, use_mask, fill):
    torch.manual_seed(SEED)
    t0 = time.time()
    if use_mask:
        XA, MA = make_aug(Xtr, KMAX_TRAIN, fill, SEED + 11)
        xtr_np = np.concatenate([Xtr, XA], axis=0)
        mtr_np = np.concatenate([np.ones((len(Xtr), CTX), dtype=np.float32), MA], axis=0)
        ytr_np = np.concatenate([Ytr, Ytr[:len(XA)]], axis=0)
        xa = cat_mask(nan_to_num(xtr_np), mtr_np)
    else:
        xa = torch.from_numpy(nan_to_num(Xtr))
        ytr_np = Ytr
    ya = torch.from_numpy(nan_to_num(ytr_np))

    def prep(X, k):
        X2, M = eval_mask(nan_to_num(X), k, fill, SEED + 101)
        return cat_mask(X2, M).to(DEV) if use_mask else torch.from_numpy(X2).to(DEV)

    xv0 = prep(Xva, 0)
    xt = {k: prep(Xte, k) for k in KS_EVAL}
    yv = torch.from_numpy(nan_to_num(Yva)).to(DEV)
    yt = nan_to_num(Yte)

    m = Seq(xa.shape[2], LHOR).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=LR, weight_decay=1e-4)
    steps = (len(xa) + BATCH - 1) // BATCH
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * steps)
    lossf = nn.MSELoss()

    best = (1e9, -1, None)
    for ep in range(1, EPOCHS + 1):
        m.train()
        perm = torch.randperm(len(xa))
        tot = 0.0
        for s in range(0, len(xa), BATCH):
            bi = perm[s:s + BATCH]
            xb, yb = xa[bi].to(DEV), ya[bi].to(DEV)
            opt.zero_grad()
            loss = lossf(m(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 2.0)
            opt.step()
            sch.step()
            tot += float(loss.detach()) * len(bi)
        m.eval()
        with torch.no_grad():
            vm = float(torch.sqrt(((m(xv0) - yv) ** 2).sum(dim=2).mean()))
        if vm < best[0]:
            best = (vm, ep, {k: v.detach().clone() for k, v in m.state_dict().items()})
    m.load_state_dict(best[2])
    m.eval()
    res = {"epochs": EPOCHS, "best_epoch": best[1], "best_val_rmse_k0_m": best[0],
           "n_train_windows": int(len(xa)), "n_test_windows": int(len(Xte)),
           "seconds": None, "mask": {}}
    with torch.no_grad():
        for k in KS_EVAL:
            res["mask"][str(k)] = metrics(m(xt[k]).cpu().numpy(), yt)
    res["seconds"] = round(time.time() - t0, 1)
    print(f"[{name}] best_ep={best[1]} val(k3)={100*best[0]:.2f}cm "
          + " | ".join(f"k={k}:{res['mask'][str(k)]['rmse']:.2f}/{res['mask'][str(k)]['end_rmse']:.2f}"
                       for k in KS_EVAL), flush=True)
    return res


def main():
    assert torch.cuda.is_available(), "需要 GPU"
    print("device", torch.cuda.get_device_name(0), flush=True)
    recs, rec, dom, badL, badR, rich, slices = load()
    Xtr, Ytr = windows(recs, rec, dom, badL, badR, rich, slices, "train", LHOR)
    Xva, Yva = windows(recs, rec, dom, badL, badR, rich, slices, "validation", LHOR)
    Xte, Yte = windows(recs, rec, dom, badL, badR, rich, slices, "test", LHOR)
    print(f"windows: train={len(Xtr)} val={len(Xva)} test={len(Xte)} CTX={CTX} L={LHOR}", flush=True)

    out = {"_meta": {"script": "p2_masked.py", "seed": SEED, "CTX": CTX, "L": LHOR,
                     "KS_EVAL": KS_EVAL, "KMAX_TRAIN": KMAX_TRAIN, "AUG_COPIES": AUG_COPIES,
                     "protocol": "输入侧随机段掩码；不使用 badL/badR 标签；模型选择用 validation k=3 RMSE",
                     "target": "dominant-hand wrist position (head frame), displacement vs anchor",
                     "arms": {"clean_only": "不加掩码通道、训练只用干净窗口",
                              "locf_mask": "掩码通道 + 前值保持填充",
                              "interp_mask": "掩码通道 + 线性插值填充"}},
           "arms": {}, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    out["arms"]["clean_only"] = run_arm("clean_only", Xtr, Ytr, Xva, Yva, Xte, Yte, False, "locf")
    out["arms"]["locf_mask"] = run_arm("locf_mask", Xtr, Ytr, Xva, Yva, Xte, Yte, True, "locf")
    out["arms"]["interp_mask"] = run_arm("interp_mask", Xtr, Ytr, Xva, Yva, Xte, Yte, True, "interp")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()