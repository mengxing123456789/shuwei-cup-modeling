
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 两个自监督任务（只用 train 环境帧，val 早停）。

A 掩码重构：连续 3-8 帧、覆盖 15-25%，重构 42 关键点(126) + 头部位姿(7)
B 时序对比：同记录不同窗为正、跨记录为负，多正例 InfoNCE (tau=0.10)

每一步的窗口长度从 {24,32,48,64} 里随机抽，迫使编码器适配不同前缀长度
（下游只用 10 帧，这一步是任务-下游匹配的关键）。
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from common import DATA
from pre_common import build_cache, clean_starts
from pre_model import Contrastive, Encoder, MaskedRecon, n_params, supcon_loss

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

SSL_JSON = os.path.join(DATA, "pre_p2_ssl.json")
CKPT = os.path.join(DATA, "pre_ckpt_{task}_{seed}.pt")
WIN_LENS = [24, 32, 48, 64]
BATCH = 64
STEPS = 500
LR = 1.5e-3
WD = 1e-4
TAU = 0.10
EVAL_EVERY = 50
DEV = "cuda" if torch.cuda.is_available() else "cpu"


class WindowPool:
    """按记录维护干净起始点，按窗口长度分别建池。"""

    def __init__(self, cache, split, win):
        recs = cache["recs"]
        self.items = []
        for r in recs[recs.split == split].rec.astype(int):
            lo, idx = clean_starts(cache, r, win)
            if len(idx) > 0:
                self.items.append((int(r), int(lo), idx))
        self.p = np.array([len(it[2]) for it in self.items], float)
        self.p = self.p / self.p.sum()


def sample_windows(cache, pool, n, T, rng):
    """从池里取 n 个窗，同时返回输入(87)与重构目标(133)。"""
    j = rng.choice(len(pool.items), size=n, p=pool.p)
    D = cache["Xn"].shape[1]
    C = cache["Yn"].shape[1]
    X = np.empty((n, T, D), np.float32)
    Y = np.empty((n, T, C), np.float32)
    for k, jj in enumerate(j):
        r, lo, st = pool.items[jj]
        s = int(st[rng.integers(len(st))])
        X[k] = cache["Xn"][lo + s:lo + s + T]
        Y[k] = cache["Yn"][lo + s:lo + s + T]
    return X, Y


def make_mask(B, T, rng, lo=0.15, hi=0.25):
    mask = np.zeros((B, T), bool)
    for b in range(B):
        target = int(rng.integers(int(np.ceil(lo * T)), int(np.floor(hi * T)) + 1))
        span_hi = min(8, T - 1)
        tries = 0
        while mask[b].sum() < target and tries < 40:
            ln = int(rng.integers(3, span_hi + 1))
            s = int(rng.integers(0, T - ln + 1))
            mask[b, s:s + ln] = True
            tries += 1
    return mask


def contrast_batch(cache, split, T, K, rng, crops=4):
    recs = cache["recs"]
    pool = WindowPool(cache, split, T)
    cand = [i for i, it in enumerate(pool.items) if len(it[2]) >= 2]
    K = min(K, len(cand))
    pick = rng.choice(cand, size=K, replace=False)
    sep = max(6, T // 4)
    D = cache["Xn"].shape[1]
    xs = np.empty((crops * K, T, D), np.float32)
    labels = np.repeat(np.arange(K), crops).astype(np.int64)
    for k, j in enumerate(pick):
        r, lo, idx = pool.items[j]
        chosen = []
        tries = 0
        while len(chosen) < crops and tries < 20 * crops:
            c = int(idx[rng.integers(len(idx))])
            if all(abs(c - x) >= sep for x in chosen):
                chosen.append(c)
            tries += 1
        while len(chosen) < crops:
            chosen.append(int(idx[rng.integers(len(idx))]))
        for m, s in enumerate(chosen):
            xs[k * crops + m] = cache["Xn"][lo + s:lo + s + T]
    order = rng.permutation(crops * K)
    return xs[order], labels[order]


def eval_masked(model, Xva, mask_va, yva):
    model.eval()
    with torch.no_grad():
        pred = model(torch.from_numpy(Xva).to(DEV), torch.from_numpy(mask_va).to(DEV))
        loss = ((pred - torch.from_numpy(yva).to(DEV)) ** 2)[
            torch.from_numpy(mask_va).to(DEV)].mean().item()
    model.train()
    return float(loss)


def eval_contrast(model, cache, seed):
    rng = np.random.default_rng(seed + 999)
    x, lab = contrast_batch(cache, "validation", 32, 7, rng, crops=16)
    model.eval()
    with torch.no_grad():
        z = model(torch.from_numpy(x).to(DEV))
        loss = supcon_loss(z, torch.from_numpy(lab).to(DEV), TAU).item()
    model.train()
    return float(loss)


def pretrain(task, seed, cache, steps=STEPS, select="best"):
    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    enc = Encoder().to(DEV)
    model = (MaskedRecon(enc) if task == "A" else Contrastive(enc)).to(DEV)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=WD)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=steps,
                                              pct_start=0.15)
    train_pools = {T: WindowPool(cache, "train", T) for T in
                   (WIN_LENS if task == "A" else [12, 16, 24, 32, 48])}

    # 固定 val 批（只用于早停），整段训练复用同一批
    if task == "A":
        vp = WindowPool(cache, "validation", 48)
        vrng = np.random.default_rng(seed + 12345)
        Xva, yva = sample_windows(cache, vp, 512, 48, vrng)
        mask_va = make_mask(512, 48, np.random.default_rng(seed + 777))

    curve = []
    best = (1e9, -1, None)
    t0 = time.time()
    for step in range(1, steps + 1):
        if task == "A":
            T = int(rng.choice(WIN_LENS))
            x, ys = sample_windows(cache, train_pools[T], BATCH, T, rng)
            mask = make_mask(BATCH, T, rng)
            mb = torch.from_numpy(mask).to(DEV)
            opt.zero_grad(set_to_none=True)
            pred = model(torch.from_numpy(x).to(DEV), mb)
            loss = ((pred - torch.from_numpy(ys).to(DEV)) ** 2)[mb].mean()
        else:
            T = int(rng.choice([12, 16, 24, 32, 48]))
            x, lab = contrast_batch(cache, "train", T, 32, rng)
            z = model(torch.from_numpy(x).to(DEV))
            loss = supcon_loss(z, torch.from_numpy(lab).to(DEV), TAU)
        loss.backward()
        nn.utils.clip_grad_norm_(params, 2.0)
        opt.step()
        sch.step()

        if step % EVAL_EVERY == 0 or step == 1:
            v = (eval_masked(model, Xva, mask_va, yva) if task == "A"
                 else eval_contrast(model, cache, seed))
            curve.append(dict(step=step, train=float(loss.item()), val=float(v)))
            if v < best[0]:
                best = (v, step, {k: t.detach().cpu().clone()
                                 for k, t in model.enc.state_dict().items()})
            print(f"  [{task}] seed={seed} step {step:4d}/{steps} "
                  f"train={loss.item():.4f} val={v:.4f} best={best[0]:.4f}@{best[1]}",
                  flush=True)

    final_state = {k: t.detach().cpu().clone() for k, t in model.enc.state_dict().items()}
    # 选择规则：A 用 val 最优（与末步几乎重合）；B 的 val 只有 7 条记录、
    # 多正例对比损失在 100-550 步间随机跳动，早停不可信，改用固定预算末步。
    if select == "final":
        sel_state, sel_step, sel_val = final_state, steps, curve[-1]["val"]
    else:
        sel_state, sel_step, sel_val = best[2], best[1], best[0]
    enc.load_state_dict(sel_state)
    path = CKPT.format(task=task, seed=seed)
    torch.save(dict(task=task, seed=seed, step=sel_step, val=sel_val,
                    best_step=best[1], best_val=best[0], select=select,
                    win_lens=WIN_LENS, tau=TAU, state_dict=sel_state), path)
    return dict(task=task, seed=seed, best_val=float(best[0]), best_step=int(best[1]),
                selected_step=int(sel_step), selected_val=float(sel_val),
                select=select, steps=steps, batch=BATCH, lr=LR,
                tau=TAU if task == "B" else None,
                enc_params=n_params(model.enc), total_params=n_params(model),
                curve=curve, seconds=round(time.time() - t0, 1),
                ckpt=os.path.basename(path), device=DEV)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="20261120,20261121,20261122")
    ap.add_argument("--tasks", default="A,B")
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--select", default="auto", choices=["auto", "best", "final"],
                    help="auto: A=best-val, B=final（val 早停在 B 上不稳定）")
    args = ap.parse_args()

    cache = build_cache()
    if cache["Xn"].shape[1] != 87:
        raise SystemExit("cache dim mismatch")
    out = {}
    if os.path.exists(SSL_JSON) and not args.force:
        with open(SSL_JSON, encoding="utf-8") as f:
            out = json.load(f)
    runs = out.setdefault("runs", [])
    done = {(r["task"], r["seed"]) for r in runs}
    for seed in [int(x) for x in args.seeds.split(",")]:
        for task in [x for x in args.tasks.split(",") if x]:
            if (task, seed) in done and not args.force:
                print(f"skip {task} seed={seed}")
                continue
            print(f"=== pretrain task {task} seed {seed} ===", flush=True)
            sel = args.select if args.select != "auto" else ("final" if task == "B" else "best")
            r = pretrain(task, seed, cache, steps=args.steps, select=sel)
            runs = [x for x in runs if not (x["task"] == task and x["seed"] == seed)]
            runs.append(r)
            out["runs"] = runs
            out["_meta"] = dict(device=DEV, torch=torch.__version__,
                                window_lengths=WIN_LENS, batch=BATCH,
                                lr_max=LR, weight_decay=WD, tau=TAU, steps=args.steps,
                                note="pretrain 只用 train 环境帧；val 仅早停")
            with open(SSL_JSON, "w", encoding="utf-8", newline="\n") as f:
                json.dump(out, f, ensure_ascii=False, indent=1)
            print(f"saved -> {SSL_JSON}  {r['seconds']}s", flush=True)


if __name__ == "__main__":
    main()