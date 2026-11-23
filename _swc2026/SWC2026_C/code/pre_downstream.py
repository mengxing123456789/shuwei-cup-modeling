
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 下游四组对照。

C0  从零训练（同骨架、同配方）
C2  预训练编码器冻结 + 岭回归线性探针（alpha 在 val 上选）
C3  预训练编码器 + 全量微调（与 C0 只差初始化）
C1  直接引用 data/p2_gpu.json（不在这里训练）

C0 与 C3 的优化器/调度/批序/早停规则逐字相同，唯一差别是编码器初始化。
"""
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from common import DATA
from pre_common import LENS, build_cache, make_windows
from pre_model import Encoder, Predictor, n_params

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

DEV = "cuda" if torch.cuda.is_available() else "cpu"
CKPT = os.path.join(DATA, "pre_ckpt_{task}_{seed}.pt")
EPOCHS = 25
BATCH = 512
LR = 1.5e-3
WD = 1e-4
PATIENCE = 7
TRAIN_STRIDE = 5
VAL_STRIDE = 5


def _t(a):
    return torch.from_numpy(a).to(DEV)


@torch.no_grad()
def predict(model, X, bs=1024):
    model.eval()
    out = []
    for i in range(0, len(X), bs):
        out.append(model(X[i:i + bs]).cpu().numpy())
    return np.concatenate(out)


def dist_stats(pred, Y, val_endpoint=None, val_all=None):
    """RMSE / median / q90 / 端点覆盖率 / PIT。pred,Y: (W,L,3) cm。"""
    err = np.linalg.norm(pred - Y, axis=2)          # (W,L) cm
    sq = (pred - Y) ** 2
    ep = err[:, -1]
    out = dict(
        rmse_cm=float(np.sqrt(sq.mean())),
        endpoint_rmse_cm=float(np.sqrt(((pred[:, -1] - Y[:, -1]) ** 2).mean())),
        median_cm=float(np.median(err)),
        q90_cm=float(np.quantile(err, 0.90)),
        rmse_per_frame_cm=[float(np.sqrt(sq[:, h].mean())) for h in range(Y.shape[1])],
        n_windows=int(len(Y)),
    )
    if val_endpoint is not None:
        q80, q90 = np.quantile(val_endpoint, [0.80, 0.90])
        out["cov80_endpoint"] = float(np.mean(ep <= q80))
        out["cov90_endpoint"] = float(np.mean(ep <= q90))
        out["calib_q80_cm"] = float(q80)
        out["calib_q90_cm"] = float(q90)
        vs = np.sort(val_endpoint)
        u = np.searchsorted(vs, ep, side="right") / len(vs)
        hist, _ = np.histogram(u, bins=np.linspace(0, 1, 11))
        h = hist / max(len(u), 1)
        out["pit_hist"] = [float(x) for x in h]
        out["pit_maxdev"] = float(np.max(np.abs(h - 0.1)))
    if val_all is not None:
        q80, q90 = np.quantile(val_all, [0.80, 0.90])
        out["cov80_all"] = float(np.mean(err <= q80))
        out["cov90_all"] = float(np.mean(err <= q90))
    return out


def train_arm(cache, arm, task, seed, L, epochs=EPOCHS, lr=LR, tag=""):
    torch.manual_seed(seed)
    np.random.seed(seed)
    t0 = time.time()
    Xtr, Ytr, _ = make_windows(cache, "train", L, stride=TRAIN_STRIDE)
    Xva, Yva, _ = make_windows(cache, "validation", L, stride=VAL_STRIDE)
    Xte, Yte, _ = make_windows(cache, "test", L, stride=1)
    xt, yt = _t(Xtr), _t(Ytr)
    xv, yv = _t(Xva), _t(Yva)
    xe, ye = _t(Xte), _t(Yte)

    enc = Encoder()
    if arm == "C3":
        ck = torch.load(CKPT.format(task=task, seed=seed), map_location="cpu",
                        weights_only=False)
        enc.load_state_dict(ck["state_dict"])
        init = f"ssl {task} step={ck['step']} val={ck['val']:.4f}"
    else:
        init = "scratch"
    model = Predictor(L, enc).to(DEV)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=WD)
    steps = max(1, (len(xt) + BATCH - 1) // BATCH)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * steps,
                                              pct_start=0.20)
    lossf = nn.MSELoss()

    curve, best = [], (1e9, -1, None)
    bad = 0
    for ep in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(len(xt), device=DEV)
        tot, n = 0.0, 0
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            opt.zero_grad(set_to_none=True)
            loss = lossf(model(xt[sel]), yt[sel])
            loss.backward()
            nn.utils.clip_grad_norm_(params, 2.0)
            opt.step()
            sch.step()
            tot += loss.item() * len(sel)
            n += len(sel)
        pv = predict(model, xv)
        vrmse = float(np.sqrt(((pv - Yva) ** 2).mean()))
        curve.append(dict(epoch=ep, train_rmse_cm=float(np.sqrt(tot / n)),
                          val_rmse_cm=vrmse, lr=float(sch.get_last_lr()[0])))
        if vrmse < best[0] - 1e-6:
            best = (vrmse, ep, {k: t.detach().cpu().clone()
                                for k, t in model.state_dict().items()})
            bad = 0
        else:
            bad += 1
        if ep == 1 or ep % 5 == 0:
            print(f"    {arm}_{task} s{seed} L{L} ep{ep:02d} "
                  f"train={curve[-1]['train_rmse_cm']:.3f} val={vrmse:.3f}cm", flush=True)
        if bad >= PATIENCE:
            print(f"    early stop at ep{ep} (best ep{best[1]})", flush=True)
            break

    model.load_state_dict(best[2])
    pt = predict(model, xe)
    # val 预测用于分布校准
    pv = predict(model, xv)
    val_ep = np.linalg.norm(pv - Yva, axis=2)[:, -1]
    val_all = np.linalg.norm(pv - Yva, axis=2).ravel()
    st = dist_stats(pt, Yte, val_ep, val_all)
    res = dict(arm=arm, ssl_task=(task if arm in ("C2", "C3") else None),
               seed=seed, L=L, L_s=round(L / 30.0, 3), init=init,
               best_epoch=int(best[1]), epochs_run=len(curve),
               val_rmse_cm=float(best[0]), n_train=int(len(xt)),
               n_val=int(len(xv)), n_test=int(len(xt) * 0 + len(xe)),
               enc_params=n_params(model.enc), head_params=n_params(model.head),
               seconds=round(time.time() - t0, 1), curve=curve, **st)
    return res


def _features(enc, X, bs=1024):
    """跟 Predictor.features 一致：最后帧 + 时间均值（64+64=128 维）。"""
    enc.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), bs):
            h = enc(X[i:i + bs])
            out.append(torch.cat([h[:, -1], h.mean(1)], dim=-1).cpu().numpy())
    return np.concatenate(out)


def probe_arm(cache, task, seed, L):
    """冻结编码器 + 岭回归；alpha 在 val 上选，test 只评估。"""
    t0 = time.time()
    ck = torch.load(CKPT.format(task=task, seed=seed), map_location="cpu",
                    weights_only=False)
    enc = Encoder()
    enc.load_state_dict(ck["state_dict"])
    enc = enc.to(DEV)
    for p in enc.parameters():
        p.requires_grad = False

    Xtr, Ytr, _ = make_windows(cache, "train", L, stride=1)
    Xva, Yva, _ = make_windows(cache, "validation", L, stride=1)
    Xte, Yte, _ = make_windows(cache, "test", L, stride=1)
    Ftr = _features(enc, _t(Xtr))
    Fva = _features(enc, _t(Xva))
    Fte = _features(enc, _t(Xte))
    mu, sd = Ftr.mean(0), Ftr.std(0) + 1e-6
    Ftr, Fva, Fte = (Ftr - mu) / sd, (Fva - mu) / sd, (Fte - mu) / sd
    ytr, yva = Ytr.reshape(len(Ytr), -1), Yva.reshape(len(Yva), -1)
    yme = ytr.mean(0)
    A = Ftr.T @ Ftr
    B = Ftr.T @ (ytr - yme)
    best = (1e9, None, None)
    for alpha in [1e-2, 1e-1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6, 1e7]:
        W = np.linalg.solve(A + alpha * np.eye(A.shape[0]), B)
        pv = ((Fva @ W) + yme).reshape(len(Yva), L, 3)
        v = float(np.sqrt(((pv - Yva) ** 2).mean()))
        if v < best[0]:
            best = (v, alpha, W)
    W = best[2]
    pt = ((Fte @ W) + yme).reshape(len(Yte), L, 3)
    pv = ((Fva @ W) + yme).reshape(len(Yva), L, 3)
    val_ep = np.linalg.norm(pv - Yva, axis=2)[:, -1]
    val_all = np.linalg.norm(pv - Yva, axis=2).ravel()
    st = dist_stats(pt, Yte, val_ep, val_all)
    return dict(arm="C2", ssl_task=task, seed=seed, L=L, L_s=round(L / 30.0, 3),
                init=f"frozen ssl {task} step={ck['step']}", best_epoch=None,
                epochs_run=0, val_rmse_cm=float(best[0]), alpha=float(best[1]),
                n_train=int(len(Ytr)), n_val=int(len(Yva)), n_test=int(len(Yte)),
                enc_params=n_params(enc), head_params=int(W.size),
                seconds=round(time.time() - t0, 1), curve=[], **st)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="C0")
    ap.add_argument("--task", default="A")
    ap.add_argument("--seed", type=int, default=20261120)
    ap.add_argument("--L", type=int, default=30)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    a = ap.parse_args()
    cache = build_cache()
    if a.arm == "C2":
        r = probe_arm(cache, a.task, a.seed, a.L)
    else:
        r = train_arm(cache, a.arm, a.task, a.seed, a.L, epochs=a.epochs)
    print(json.dumps({k: v for k, v in r.items() if k != "curve"},
                     ensure_ascii=False, indent=1))