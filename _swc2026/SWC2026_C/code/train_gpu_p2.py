
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""C 题 P2：缺失观测窗口下的轨迹预测 —— GPU 序列模型（GRU encoder + multi-horizon head）
对比 CPU 基线（`p2_crossover.json` / `p2_interval.json` 的 ridge, alpha=10, ctx=10 帧）。

两个变体，把「模型类」与「输入信息」两种增益分开归因：
  V1  same-input  ：只喂主导手腕（头坐标系）后 10 帧的 3 维 → 30 维
  V2  rich-input  ：喂双手状态 32+32 + 头部几何 8+8 = 80 维/帧 → 800 维

窗口档位对齐官方 `common_conditions.json` 的 observation.prefix_seconds = [0.2, 0.6, 1.0]
（= 6 / 18 / 30 帧 @30 fps），另保留 60 帧做外推压力测试。
"""
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

SEED = 20261120
CTX = 10
LENS = [6, 18, 30, 60]
DEV = "cuda" if torch.cuda.is_available() else "cpu"
BATCH = 512
EPOCHS = 40
LR = 2e-3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
WRIST_L = slice(0, 3)     # fl 前 3 维 = 左手腕头坐标系位置
WRIST_R = slice(32, 35)   # fr 前 3 维（在拼接后偏移 32）


def load():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    rec, dom = st["rec"].astype(np.int64), st["dom"].astype(np.int64)
    rich = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"]],
                          axis=1).astype(np.float32)      # 80 维
    badL, badR = st["badL"], st["badR"]
    slices = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        slices[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    return st, recs, rec, dom, badL, badR, rich, slices


def windows(recs, rec, dom, badL, badR, rich, slices, split, L):
    v1s, v2s, ys = [], [], []
    for r in recs[recs.split == split].rec.astype(int):
        lo, hi = slices[r]
        d = int(dom[r])
        bad = (badL[lo:hi] if d == 0 else badR[lo:hi]).astype(bool)
        wr = WRIST_L if d == 0 else WRIST_R
        wrist = rich[lo:hi, wr]                 # (n,3) 头坐标系手腕
        n = hi - lo
        span = CTX + L
        if n <= span:
            continue
        clean = np.lib.stride_tricks.sliding_window_view(bad, span).sum(axis=1) == 0
        idx = np.flatnonzero(clean)             # 起点，长度 = n-span+1
        if len(idx) == 0:
            continue
        anchor = wrist[idx + CTX - 1]           # (W,3)

        seg = np.lib.stride_tricks.sliding_window_view(rich[lo:hi], CTX, axis=0)
        seg = np.transpose(seg, (0, 2, 1))[idx].copy()          # (W,CTX,80)
        seg[:, :, 0:3] -= anchor[:, None, :]
        seg[:, :, 32:35] -= anchor[:, None, :]

        v1 = wrist[np.arange(len(idx))[:, None] + np.arange(CTX)[None, :]] - anchor[:, None, :]
        tgt = wrist[idx[:, None] + CTX + np.arange(L)[None, :]] - anchor[:, None, :]

        v1s.append(v1.astype(np.float32))
        v2s.append(seg.astype(np.float32))
        ys.append(tgt.astype(np.float32))
    if not v1s:
        return None, None, None
    return (np.concatenate(v1s), np.concatenate(v2s)), np.concatenate(ys), len(ys)


def nan_to_num(a):
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)


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


def run(L, variant):
    torch.manual_seed(SEED)
    Xtr, Ytr, ntr = windows(recs, rec, dom, badL, badR, rich, slices, "train", L)
    Xva, Yva, nva = windows(recs, rec, dom, badL, badR, rich, slices, "validation", L)
    Xte, Yte, nte = windows(recs, rec, dom, badL, badR, rich, slices, "test", L)
    if Xtr is None or Xte is None:
        print(f"L={L} {variant}: no windows")
        return None

    k = 0 if variant == "v1" else 1
    Xtr = [nan_to_num(x) for x in Xtr]
    Xva = [nan_to_num(x) for x in Xva]
    Xte = [nan_to_num(x) for x in Xte]
    Ytr = nan_to_num(Ytr); Yva = nan_to_num(Yva); Yte = nan_to_num(Yte)

    xa = torch.from_numpy(Xtr[k])
    ya = torch.from_numpy(Ytr)
    xv = torch.from_numpy(Xva[k]).to(DEV)
    xt = torch.from_numpy(Xte[k]).to(DEV)
    yv, yt = Yva, Yte

    m = Seq(Xtr[k].shape[2], L).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=LR, weight_decay=1e-4)
    steps = (len(xa) + BATCH - 1) // BATCH
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * steps)
    lossf = nn.MSELoss()

    best = (1e9, -1, None)
    for ep in range(1, EPOCHS + 1):
        m.train()
        perm = torch.randperm(len(xa))
        tot, n = 0.0, 0
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            xb = xa[sel].to(DEV, non_blocking=True)
            yb = ya[sel].to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            loss = lossf(m(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 2.0)
            opt.step()
            sch.step()
            tot += loss.item() * len(sel)
            n += len(sel)
        m.eval()
        with torch.no_grad():
            pv = m(xv).cpu().numpy()
        vm = float(np.sqrt(np.mean((pv - yv) ** 2)))
        if vm < best[0]:
            best = (vm, ep, {a: b.detach().clone() for a, b in m.state_dict().items()})
        if ep % 10 == 0 or ep == 1:
            print(f"  L={L:2d} {variant} ep{ep:02d} train_mse={tot/n:.6f} val_rmse={100*vm:.2f}cm")

    m.load_state_dict(best[2])
    m.eval()
    with torch.no_grad():
        pt = m(xt).cpu().numpy()
    err = np.linalg.norm(pt - yt, axis=2)
    res = {
        "L_frames": L, "L_s": round(L / 30.0, 3), "variant": variant,
        "n_train": int(ntr), "n_val": int(nva), "n_test": int(nte),
        "best_val_epoch": best[1],
        "val_rmse_m": float(best[0]),
        "test_rmse_m": float(np.sqrt(np.mean((pt - yt) ** 2))),
        "test_rmse_per_frame_m": [float(np.sqrt(np.mean((pt[:, h] - yt[:, h]) ** 2)))
                                  for h in range(L)],
        "test_endpoint_rmse_m": float(np.sqrt(np.mean(err[:, -1] ** 2))),
        "test_median_err_m": float(np.median(err)),
        "test_within_2cm": float(np.mean(err <= 0.02)),
        "test_within_5cm": float(np.mean(err <= 0.05)),
    }
    print(f"  -> L={L:2d} {variant}  test RMSE {100*res['test_rmse_m']:.2f} cm | "
          f"endpoint {100*res['test_endpoint_rmse_m']:.2f} cm | "
          f"median {100*res['test_median_err_m']:.2f} cm | "
          f"w2cm {res['test_within_2cm']:.3f} w5cm {res['test_within_5cm']:.3f}")
    return res


if __name__ == "__main__":
    st, recs, rec, dom, badL, badR, rich, slices = load()
    print(f"device={DEV} torch={torch.__version__}  frames={len(rec):,}  rich_dim={rich.shape[1]}")
    if DEV == "cuda":
        p = torch.cuda.get_device_properties(0)
        print(f"gpu={p.name} {p.total_memory/1e9:.2f} GB")
    t0 = time.time()
    out = []
    for L in LENS:
        for v in ("v1", "v2"):
            r = run(L, v)
            if r:
                out.append(r)
    res = {
        "_meta": {
            "model": "GRU(128, 2 layers) encoder + MLP multi-horizon head, GPU",
            "context_frames": CTX, "epochs": EPOCHS, "batch": BATCH, "lr": LR,
            "seed": SEED, "device": DEV,
            "target": "dominant-hand wrist position (head frame), displacement vs last observed frame",
            "variants": {"v1": "wrist only 3 dims/frame (same input as ridge baseline)",
                         "v2": "both hands 32+32 + head geometry 8+8 = 80 dims/frame"},
            "baseline_ridge": {
                "L6": {"cv_rmse_m": 0.023395402889693676, "hold_rmse_m": 0.02563893049955368,
                       "cv_endpoint_rmse_m": 0.038719331732100605},
                "L15": {"cv_rmse_m": 0.06301438276229286},
                "L30": {"conformal_q90_m": 1.0194606533405701,
                        "empirical_median_err_m": 0.15301206107471466},
                "L60": {"conformal_q90_m": 4.069236836052754},
            },
            "official_prefix_seconds": [0.2, 0.6, 1.0],
        },
        "rows": out,
        "total_seconds": round(time.time() - t0, 1),
    }
    fp = os.path.join(DATA, "p2_gpu.json")
    with open(fp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\nsaved -> {fp}  ({res['total_seconds']}s)")