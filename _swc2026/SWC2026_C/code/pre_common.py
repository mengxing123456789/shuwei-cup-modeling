
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 共用数据层。

口径（与 data/p2_gpu.json 的 v2 基线同源）：
  输入 87 维/帧 = 左手 32 + 右手 32 + 左几何 8 + 右几何 8
                  + 头部世界位移 3（相对记录首帧）+ 头四元数 4 (wxyz)
  目标 = 主导手腕（头坐标系）相对最后观测帧的位移，单位 cm

纪律：
  * 预训练只允许 train 环境的帧（16 env / 55 records）
  * val 只用于早停与分布校准；test 只在最后评估一次
  * 归一化统计量只用 train 帧计算
"""
import json
import os

import numpy as np
import pandas as pd

from common import DATA, quat_to_R

CACHE = os.path.join(DATA, "pre_cache.npz")
NORM_PATH = os.path.join(DATA, "pre_norm.json")
CTX = 10
LENS = [6, 18, 30, 60]
FPS = 30.0
IN_DIM = 87
TGT_DIM = 133


def record_slices(rec):
    out = {}
    for r in np.unique(rec):
        ii = np.flatnonzero(rec == r)
        out[int(r)] = (int(ii[0]), int(ii[-1]) + 1)
    return out


def build_cache(force=False):
    """把 panel/state 拼成逐帧张量，缓存到 data/pre_cache.npz。"""
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE, allow_pickle=True)
        rec = z["rec"].astype(np.int64)
        recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
        return dict(Xn=z["Xn"], Xraw=z["Xraw"], Yn=z["Yn"], Yraw=z["Yraw"],
                    wrist=z["wrist"], rec=rec, badL=z["badL"].astype(bool),
                    badR=z["badR"].astype(bool), dom=z["dom"].astype(np.int64),
                    recs=recs, slices=record_slices(rec))

    Z = np.load(os.path.join(DATA, "panel.npz"))
    st = np.load(os.path.join(DATA, "state.npz"))
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    rec = Z["rec"].astype(np.int64)
    Lw, Rw, Hw, Q = Z["L"], Z["R"], Z["H"], Z["Q"]
    dom = st["dom"].astype(np.int64)
    sl = record_slices(rec)

    # 关键点 -> 头坐标系（与 p1_state.py 的 to_head 完全一致）
    Rm = quat_to_R(Q).astype(np.float32)
    Rmt = np.transpose(Rm, (0, 2, 1))
    Pl = np.einsum("nij,nkj->nki", Rmt, (Lw - Hw[:, None, :]).astype(np.float32))
    Pr = np.einsum("nij,nkj->nki", Rmt, (Rw - Hw[:, None, :]).astype(np.float32))

    Hrel = np.zeros_like(Hw, dtype=np.float32)
    for r, (lo, hi) in sl.items():
        Hrel[lo:hi] = Hw[lo:hi] - Hw[lo]

    Xraw = np.concatenate([st["fl"], st["fr"], st["gl"], st["gr"], Hrel, Q], axis=1)
    Xraw = np.nan_to_num(Xraw.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    Yraw = np.concatenate([Pl.reshape(len(Pl), -1), Pr.reshape(len(Pr), -1),
                           Hrel, Q], axis=1).astype(np.float32)
    Yraw = np.nan_to_num(Yraw, nan=0.0, posinf=0.0, neginf=0.0)

    wrist = np.zeros((len(rec), 3), np.float32)
    for r, (lo, hi) in sl.items():
        wrist[lo:hi] = Xraw[lo:hi, 0:3] if dom[r] == 0 else Xraw[lo:hi, 32:35]

    train_recs = recs[recs.split == "train"].rec.to_numpy()
    tr_mask = np.isin(rec, train_recs)
    mu, sd = Xraw[tr_mask].mean(0), Xraw[tr_mask].std(0)
    sd = np.maximum(sd, 1e-3)
    ny_mu, ny_sd = Yraw[tr_mask].mean(0), Yraw[tr_mask].std(0)
    ny_sd = np.maximum(ny_sd, 1e-3)

    Xn = ((Xraw - mu) / sd).astype(np.float32)
    Yn = ((Yraw - ny_mu) / ny_sd).astype(np.float32)

    np.savez_compressed(CACHE, Xn=Xn, Xraw=Xraw, Yn=Yn, Yraw=Yraw, wrist=wrist,
                        rec=rec.astype(np.int16), badL=Z["badL"], badR=Z["badR"],
                        dom=dom.astype(np.int8))
    meta = dict(
        n_frames=int(len(rec)), in_dim=IN_DIM, tgt_dim=TGT_DIM,
        train_frames=int(tr_mask.sum()),
        x_mean=mu.tolist(), x_std=sd.tolist(),
        y_mean=ny_mu.tolist(), y_std=ny_sd.tolist(),
        note="归一化统计量只来自 train split；Hrel = 头部世界坐标 - 记录首帧",
    )
    with open(NORM_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False)

    return dict(Xn=Xn, Xraw=Xraw, Yn=Yn, Yraw=Yraw, wrist=wrist, rec=rec,
                badL=Z["badL"].astype(bool), badR=Z["badR"].astype(bool),
                dom=dom, recs=recs, slices=sl)


def _bad(cache, r, lo, hi):
    return (cache["badL"][lo:hi] if cache["dom"][r] == 0 else cache["badR"][lo:hi]).astype(bool)


def clean_starts(cache, r, span):
    lo, hi = cache["slices"][r]
    bad = _bad(cache, r, lo, hi)
    if len(bad) < span:
        return lo, np.zeros(0, np.int64)
    ok = np.lib.stride_tricks.sliding_window_view(bad, span).sum(1) == 0
    return lo, np.flatnonzero(ok)


def count_windows(cache, split, L, stride=1, ctx=CTX):
    recs = cache["recs"]
    n = 0
    for r in recs[recs.split == split].rec.astype(int):
        _, idx = clean_starts(cache, r, ctx + L)
        n += len(idx[::stride])
    return int(n)


def make_windows(cache, split, L, stride=1, ctx=CTX):
    """返回 X (W,ctx,87) 归一化、Y (W,L,3) 厘米、meta。"""
    recs = cache["recs"]
    Xs, Ys, mrec, mstart = [], [], [], []
    for r in recs[recs.split == split].rec.astype(int):
        lo, idx = clean_starts(cache, r, ctx + L)
        if len(idx) == 0:
            continue
        idx = idx[::stride]
        hi = cache["slices"][r][1]
        sw = np.lib.stride_tricks.sliding_window_view(cache["Xn"][lo:hi], ctx, axis=0)
        xb = np.transpose(sw[idx], (0, 2, 1)).copy()
        w = cache["wrist"][lo:hi]
        anchor = w[idx + ctx - 1]
        yb = (w[idx[:, None] + ctx + np.arange(L)[None, :]] - anchor[:, None, :]) * 100.0
        Xs.append(xb.astype(np.float32))
        Ys.append(yb.astype(np.float32))
        mrec.append(np.full(len(idx), r, np.int32))
        mstart.append((idx + lo).astype(np.int32))
    if not Xs:
        return None, None, None
    return (np.concatenate(Xs), np.concatenate(Ys),
            dict(rec=np.concatenate(mrec), start=np.concatenate(mstart)))