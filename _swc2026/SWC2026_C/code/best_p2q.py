
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 最强单点：多步分位数预测（不是点估计）。

做法：与 data/p2_gpu.json 的 v2 同输入（双手 32+32 + 头部 8+8 = 80 维/帧，ctx=10 帧，
头坐标系、相对最后一个已观测帧的位移），把 MLP 点估计头换成**分位数头**
（7 个分位 τ = .05/.10/.25/.50/.75/.90/.95 × 3 轴 × L 步），损失 = pinball loss。
输出按 τ 排序（rearrangement）保证不交叉。

报什么：
  - q50 的 RMSE / 中位 / q90 / ≤2cm 命中率 —— 与点估计基线同表可比
  - 名义 90% 区间 [q05,q95] 与名义 50% 区间 [q25,q75] 的**实测覆盖率**（逐轴）
  - 区间平均宽度（cm）—— 与 conformal ridge 比「同覆盖率下谁更窄」
  - PIT 直方图（10 箱）+ 与均匀分布的 KS 距离
  - 分位校准按 horizon 分开报（L=6/18/30/60 帧 = 0.2/0.6/1.0/2.0 s）

输出 data/best_p2q.json（不覆盖 p2_gpu.json / p2_interval.json）。
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
TAUS = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
SCALE = 100.0            # 目标换成 cm，pinball 损失量级才合适
BATCH = 512
EPOCHS = 32
LR = 2e-3
DEV = "cuda" if torch.cuda.is_available() else "cpu"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "best_p2q.json")
WRIST_L, WRIST_R = slice(0, 3), slice(32, 35)


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
    """与 train_gpu_p2.py 完全一致的窗口与特征（干净窗口、锚点相对位移）。"""
    xs, ys = [], []
    for r in recs[recs.split == split].rec.astype(int):
        lo, hi = slices[r]
        d = int(dom[r])
        bad = (badL[lo:hi] if d == 0 else badR[lo:hi]).astype(bool)
        wr = WRIST_L if d == 0 else WRIST_R
        wrist = rich[lo:hi, wr]
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
        xs.append(np.nan_to_num(seg, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
        ys.append(np.nan_to_num(tgt, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32))
    if not xs:
        return None, None
    return np.concatenate(xs), np.concatenate(ys)


class QSeq(nn.Module):
    def __init__(self, fdim, L, h=128, nq=len(TAUS)):
        super().__init__()
        self.gru = nn.GRU(fdim, h, num_layers=2, batch_first=True, dropout=0.10)
        self.head = nn.Sequential(nn.Linear(h, 256), nn.GELU(), nn.Dropout(0.10),
                                  nn.Linear(256, L * 3 * nq))
        self.L, self.nq = L, nq

    def forward(self, x):
        _, hn = self.gru(x)
        return self.head(hn[-1]).view(-1, self.L, 3, self.nq)


def pinball(pred, y):
    """pred (B,L,3,Q), y (B,L,3) in cm."""
    q = torch.tensor(TAUS, device=pred.device, dtype=pred.dtype).view(1, 1, 1, -1)
    d = y.unsqueeze(-1) - pred
    return torch.maximum(q * d, (q - 1) * d).mean()


def pit_hist(y, qs):
    """qs (N, Q) 分位值（已排序），y (N,)；线性插值 CDF 后做 PIT。"""
    n, Q = qs.shape
    cdf = np.empty(n)
    for i in range(n):
        v, p = qs[i], TAUS
        # 两端用线性外推截断
        if y[i] <= v[0]:
            cdf[i] = TAUS[0] * (y[i] - (v[0] - (v[1] - v[0]))) / max(1e-9, (v[1] - v[0]))
        elif y[i] >= v[-1]:
            cdf[i] = TAUS[-1] + (1 - TAUS[-1]) * (y[i] - v[-1]) / max(1e-9, (v[-1] - v[-2]))
        else:
            cdf[i] = np.interp(y[i], v, p)
    cdf = np.clip(cdf, 0, 1)
    h, _ = np.histogram(cdf, bins=np.linspace(0, 1, 11))
    h = h / max(1, h.sum())
    grid = (np.arange(10) + 0.5) / 10
    ks = float(np.max(np.abs(np.cumsum(h) - np.arange(1, 11) / 10)))
    return [float(x) for x in h], ks, float(np.mean(np.abs(np.array(h) - 0.1)))


def run(L, recs, rec, dom, badL, badR, rich, slices):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    Xtr, Ytr = windows(recs, rec, dom, badL, badR, rich, slices, "train", L)
    Xva, Yva = windows(recs, rec, dom, badL, badR, rich, slices, "validation", L)
    Xte, Yte = windows(recs, rec, dom, badL, badR, rich, slices, "test", L)
    if Xtr is None or Xte is None:
        print(f"L={L}: no windows")
        return None
    xa = torch.from_numpy(Xtr)
    ya = torch.from_numpy(Ytr * SCALE)
    xv = torch.from_numpy(Xva).to(DEV)
    yv = Yva * SCALE
    xt = torch.from_numpy(Xte).to(DEV)

    m = QSeq(Xtr.shape[2], L).to(DEV)
    npar = sum(p.numel() for p in m.parameters())
    opt = torch.optim.AdamW(m.parameters(), lr=LR, weight_decay=1e-4)
    steps = (len(xa) + BATCH - 1) // BATCH
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * steps)
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
            loss = pinball(m(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 2.0)
            opt.step()
            sch.step()
            tot += float(loss.detach()) * len(sel)
            n += len(sel)
        m.eval()
        with torch.no_grad():
            pv = m(xv).cpu().numpy()
        vq = np.sort(pv, axis=-1)
        med = vq[..., list(TAUS).index(0.5)]
        vl = float(np.mean(np.abs(med - yv)))
        if vl < best[0]:
            best = (vl, ep, {k: v.detach().clone() for k, v in m.state_dict().items()})
        if ep % 8 == 0 or ep == 1:
            print(f"  L={L:2d} ep{ep:02d} pinball={tot/n:.4f} val_medAE={vl/SCALE*100:.2f}cm")

    m.load_state_dict(best[2])
    m.eval()
    with torch.no_grad():
        pt = np.sort(m(xt).cpu().numpy(), axis=-1) / SCALE       # (N,L,3,Q) 米
    i50 = list(TAUS).index(0.5)
    out = dict(L_frames=L, L_s=round(L / 30.0, 3), n_train=int(len(Xtr)),
               n_val=int(len(Xva)), n_test=int(len(Xte)), params=int(npar),
               best_val_epoch=best[1], val_median_ae_m=float(best[0] / SCALE),
               horizons=[], pit=[], coverage=[])
    for h in range(L):
        y = Yte[:, h]                                     # (N,3)
        q = pt[:, h]                                      # (N,3,Q)
        med = q[:, :, i50]
        err = np.linalg.norm(med - y, axis=1)
        lo90, hi90 = q[:, :, 0], q[:, :, -1]
        lo50, hi50 = q[:, :, 2], q[:, :, 4]
        cov90 = np.mean((y >= lo90) & (y <= hi90), axis=0)
        cov50 = np.mean((y >= lo50) & (y <= hi50), axis=0)
        w90 = np.mean(hi90 - lo90, axis=0)
        w50 = np.mean(hi50 - lo50, axis=0)
        out["horizons"].append(dict(step=h, t_s=round((h + 1) / 30.0, 3),
                                    rmse_m=float(np.sqrt(np.mean((med - y) ** 2))),
                                    median_err_m=float(np.median(err)),
                                    q90_err_m=float(np.percentile(err, 90)),
                                    within_2cm=float(np.mean(err <= 0.02)),
                                    coverage90_axis=[float(c) for c in cov90],
                                    coverage90_mean=float(np.mean(cov90)),
                                    coverage50_axis=[float(c) for c in cov50],
                                    coverage50_mean=float(np.mean(cov50)),
                                    width90_axis_cm=[float(w * 100) for w in w90],
                                    width90_mean_cm=float(np.mean(w90) * 100),
                                    width50_mean_cm=float(np.mean(w50) * 100)))
        hh, ks, mdev = pit_hist(y.reshape(-1), q.reshape(-1, len(TAUS)))
        out["pit"].append(dict(step=h, hist=hh, ks=ks, mean_dev=mdev))
    # 末端（最远 horizon）单独强调
    last = out["horizons"][-1]
    print(f"  -> L={L:2d} q50 RMSE {100*last['rmse_m']:.2f} cm | median "
          f"{100*last['median_err_m']:.2f} cm | q90 {100*last['q90_err_m']:.2f} cm | "
          f"w2cm {last['within_2cm']:.3f} | cov90 {last['coverage90_mean']:.3f} "
          f"width90 {last['width90_mean_cm']:.2f} cm | PIT KS {out['pit'][-1]['ks']:.3f}")
    return out


def main():
    t0 = time.time()
    print(f"device={DEV} torch={torch.__version__}")
    recs, rec, dom, badL, badR, rich, slices = load()
    print(f"frames={len(rec):,} rich_dim={rich.shape[1]} taus={TAUS.tolist()}")
    rows = []
    for L in LENS:
        r = run(L, recs, rec, dom, badL, badR, rich, slices)
        if r:
            rows.append(r)
    out = dict(
        _meta=dict(
            purpose="P2 分位数（分布）预测：同一 v2 输入、同一窗口规则，把点估计头换成 7 分位头",
            model="GRU(128, 2 layers, dropout .10) + MLP 分位头 (7 tau x 3 轴 x L 步)",
            loss="pinball (quantile) loss, 按 tau 排序消交叉",
            ctx_frames=CTX, epochs=EPOCHS, batch=BATCH, lr=LR, seed=SEED, device=DEV,
            taus=TAUS.tolist(), scale_note="目标乘 100 换 cm 后再算损失，输出除回来",
            target="dominant-hand wrist displacement vs last observed frame (head frame)",
            input="v2: both hands 32+32 + head geometry 8+8 = 80 dims/frame",
            baseline_point="data/p2_gpu.json rows variant=v2: L6 RMSE .0054 m med .0028 w2cm .958; L18 .0229/.0203/.495; L30 .0331/.0318/.329; L60 .0453/.0500/.172",
            baseline_conformal="data/p2_interval.json: test coverage .893/.926/.932/.939 for L=.2/.5/1/2 s (split conformal ridge)",
            horizon_note="L=6/18/30/60 帧 = .2/.6/1.0/2.0 s，与 p2_gpu.json 同一组档位"),
        rows=rows, total_seconds=round(time.time() - t0, 1))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n=== SUMMARY (末步 = 该档最远 horizon) ===")
    print(f"{'L':>3s} {'q50RMSE':>8s} {'med':>7s} {'q90':>7s} {'w2cm':>6s} "
          f"{'cov90':>6s} {'w90cm':>7s} {'cov50':>6s} {'PITks':>6s}")
    for r in rows:
        h, p = r["horizons"][-1], r["pit"][-1]
        print(f"{r['L_frames']:3d} {100*h['rmse_m']:8.2f} {100*h['median_err_m']:7.2f} "
              f"{100*h['q90_err_m']:7.2f} {h['within_2cm']:6.3f} {h['coverage90_mean']:6.3f} "
              f"{h['width90_mean_cm']:7.2f} {h['coverage50_mean']:6.3f} {p['ks']:6.3f}")
    print(f"saved -> {OUT} ({out['total_seconds']}s)")


if __name__ == "__main__":
    main()