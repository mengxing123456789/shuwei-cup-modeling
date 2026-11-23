# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p1b_v2.py -- P1-b 坏帧检测器升级 v2（三窗 + attention pooling + 域泛化 + 校准）。

为什么这样改（依据已有结果，不是拍脑袋）
----------------------------------------
* 现有 A/C 两臂 best_epoch 全部 = 1（见 data/up_p1b_dual.json 的 history）：
  val AUC 第 1 轮见顶后一路下滑 → 容量不是瓶颈，**跨环境泛化**才是。
  所以 v2 不加宽加深，只加三件与泛化直接相关的东西。
* C 臂（双窗 15/60 + 多任务）test AP 0.1076/0.0918/0.0786，worst per-env AUC
  0.7884/0.7299/0.7154；只有 2 个 test 环境有正例（logistics_0011 / 0041），
  worst 基本由 logistics_0011（6275 帧 / 213 正例）决定。

四个配置（同一数据划分、同一评估协议；依次训练，test 每个 (config,seed) 只评一次）
--------------------------------------------------------------------------------
  V1 ms3_attn         三窗 0.5 s / 2 s / 4 s（4 s 窗按 2 帧步长取 60 步），
                      learned attention pooling（末帧 + 注意力池化 + 时间 max），
                      GroupNorm + dropout，保留 occlusion/near-edge 辅助头。
  V2 ms3_attn_norm    V1 + 记录级因果归一化视图（用每条记录前 90 帧的均值/方差
                      标准化整条记录，再与原始特征并排输入）—— 去场景偏移。
  V3 ms3_attn_norm_adv V2 + 环境分类头 + 梯度反转（GRL），显式抹掉环境信息。
  V4 ms3_attn_norm_dro V2 + Group-DRO：按环境分层采样 + 每轮 q_e ∝ q_e·exp(η·L_e)。

校准：temperature scaling **只在 validation 上拟合**，再作用于 test；报 ECE、
precision/recall@0.5、误丢好帧率。test 不参与任何选择。

预注册门槛（写在代码里，训练前定死；见 data/up2_p1b.json 的 _meta.gate）
  PASS = 三 seed 平均 test AP >= 0.13
     AND 三 seed 平均 worst per-env AUC >= 0.7646370912154993（A 臂 seed 20261120 基线）

用法：
  python up2_p1b_v2.py --configs V1 --seeds 20261120 --epochs 2 --smoke
  python up2_p1b_v2.py --configs V1,V2,V3,V4
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, roc_auc_score

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
LOGS = os.path.abspath(os.path.join(HERE, "..", "logs"))
OUT_JSON = os.path.join(DATA, "up2_p1b.json")
LOG_PATH = os.path.join(LOGS, "up2_p1b_v2.log")

DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = [20261120, 20261122, 20261123]
SPECS = [(15, 1), (60, 1), (120, 2)]      # (span_frames, stride) -> all 60 steps except 15
SPEC_LABELS = ["0.5s", "2s", "4s/stride2"]
T0 = 15
BATCH = 1024
EPOCHS = 18
LR = 1.5e-3
WD = 1e-4
AUX_W = 0.3
DRO_ETA = 0.5
GRL_MAX = 0.10
NORM_PREFIX = 90                            # 归一化统计用的因果前缀帧数
EPS = 1e-3

# ---------------------------------------------------------------- 预注册门槛
GATE = dict(
    seeds=list(SEEDS),
    mean_test_ap_min=0.13,
    mean_worst_env_auc_min=0.7646370912154993,
    worst_env_baseline_source="data/p1b_gpu.json A 臂 seed 20261120 的 min per-env AUC",
    selection_rule="按 validation mean AUC 选配置（不看 test）",
    test_discipline="每个 (config, seed) 的 test 只在训练结束后评一次",
)

CONFIGS = {
    "V1": dict(desc="三窗 + attention pooling + 辅助头（raw 特征）", views="raw",
               adv=False, dro=False, drop=0.15, lr=1.5e-3, wd=1e-4, jitter=0, loss="bce"),
    "V2": dict(desc="V1 + 记录级因果归一化视图（raw+norm 并排）", views="both",
               adv=False, dro=False, drop=0.15, lr=1.5e-3, wd=1e-4, jitter=0, loss="bce"),
    "V3": dict(desc="V2 + 环境分类 GRL（梯度反转）", views="both", adv=True, dro=False,
               drop=0.15, lr=1.5e-3, wd=1e-4, jitter=0, loss="bce"),
    "V4": dict(desc="V2 + Group-DRO（环境分层采样 + q_e 重加权）", views="both",
               adv=False, dro=True, drop=0.15, lr=1.5e-3, wd=1e-4, jitter=0, loss="bce"),
    "V5": dict(desc="V1 + 强正则（dropout .25 / wd 3e-4 / lr 1e-3 / 时间抖动 ±2）",
               views="raw", adv=False, dro=False, drop=0.25, lr=1e-3, wd=3e-4,
               jitter=2, loss="bce"),
    "V6": dict(desc="V1 + focal loss（alpha .75, gamma 2）替代 pos_weight BCE",
               views="raw", adv=False, dro=False, drop=0.15, lr=1.5e-3, wd=1e-4,
               jitter=0, loss="focal"),
    "V7": dict(desc="V5 + focal loss", views="raw", adv=False, dro=False, drop=0.25,
               lr=1e-3, wd=3e-4, jitter=2, loss="focal"),
    "V8": dict(desc="V1 + 左右手交换增广 + 交换 TTA（标签对左右对称）", views="raw",
               adv=False, dro=False, drop=0.15, lr=1.5e-3, wd=1e-4, jitter=0,
               loss="bce", swap_aug=True, tta=True),
}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- 数据
def frame_bounds(rec):
    b = {}
    for r in np.unique(rec):
        idx = np.flatnonzero(rec == r)
        b[int(r)] = (int(idx[0]), int(idx[-1]) + 1)
    return b


def record_normalize(feats, rec, bounds):
    """每条记录用前 NORM_PREFIX 帧的均值/方差标准化整条记录（因果、不看未来）。"""
    out = np.empty_like(feats)
    for r, (lo, hi) in bounds.items():
        n = hi - lo
        k = min(NORM_PREFIX, n)
        mu = feats[lo:lo + k].mean(axis=0)
        sd = feats[lo:lo + k].std(axis=0)
        sd = np.maximum(sd, EPS)
        out[lo:hi] = np.clip((feats[lo:hi] - mu) / sd, -8.0, 8.0)
    return out.astype(np.float32)


def build_data():
    t0 = time.time()
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    feats = np.concatenate([
        z["fl"], z["fr"], z["gl"], z["gr"],
        z["validL"][:, None].astype(np.float32),
        z["validR"][:, None].astype(np.float32),
    ], axis=1).astype(np.float32)
    y = (z["badL"] | z["badR"]).astype(np.float32)
    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"), encoding="utf-8-sig")
    split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
    env_of = dict(zip(meta["rec"].astype(int), meta["env"].astype(str)))

    bounds = frame_bounds(rec)
    X = np.concatenate([feats, record_normalize(feats, rec, bounds)], axis=1)  # (N,164)
    del feats

    idx_all = {sp: [] for sp in SPECS}
    yp, sp_, ep_, rp = [], [], [], []
    for r, (lo, hi) in bounds.items():
        n = hi - lo
        if n <= T0:
            continue
        j = np.arange(T0 - 1, n)                       # 样本 = 结束帧 j
        for sp in SPECS:
            T, stride = sp
            L = 60 if sp == (120, 2) else T
            steps = np.arange(L)
            ii = j[:, None] - (T - 1) + steps[None, :] * stride
            idx_all[sp].append((lo + np.clip(ii, 0, None)).astype(np.int32))
        m = len(j)
        yp.append(y[lo + T0 - 1: hi])
        sp_.append(np.array([split_of[r]] * m))
        ep_.append(np.array([env_of[r]] * m))
        rp.append(np.full(m, r, np.int32))
    IDX = {sp: np.concatenate(v, axis=0) for sp, v in idx_all.items()}
    Y = np.concatenate(yp)
    S = np.concatenate(sp_)
    E = np.concatenate(ep_)
    R = np.concatenate(rp)
    log(f"data: frames={len(rec)} samples={len(Y):,} feat={X.shape[1]} "
        f"pos_rate={Y.mean():.5f} build={time.time()-t0:.1f}s")
    log("split " + str({k: int((S == k).sum()) for k in ("train", "validation", "test")}))
    return dict(X=X, IDX=IDX, Y=Y, S=S, E=E, R=R, bounds=bounds, rec=rec)


def build_aux(D):
    a = np.load(os.path.join(DATA, "up_p1b_aux.npz"))
    n = len(D["Y"])
    occ = np.zeros(n, np.float32)
    edge = np.zeros(n, np.float32)
    msk = np.zeros(n, np.float32)
    k = 0
    for r in np.unique(D["R"]):
        nn = int((D["R"] == r).sum())
        lo, hi = D["bounds"][int(r)]
        sl = slice(lo + T0 - 1, hi)
        occ[k:k + nn] = a["occ"][sl]
        edge[k:k + nn] = a["edge"][sl]
        msk[k:k + nn] = a["aux_mask"][sl]
        k += nn
    assert k == n, (k, n)
    return dict(occ=occ, edge=edge, mask=msk)


# ---------------------------------------------------------------- 模型
class Block(nn.Module):
    def __init__(self, c, d, drop):
        super().__init__()
        self.c1 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.c2 = nn.Conv1d(c, c, 3, padding=d, dilation=d)
        self.n1 = nn.GroupNorm(8, c)
        self.n2 = nn.GroupNorm(8, c)
        self.a = nn.GELU()
        self.dp = nn.Dropout(drop)

    def forward(self, x):
        h = self.dp(self.a(self.n1(self.c1(x))))
        h = self.n2(self.c2(h))
        return self.a(h + x)


class AttnPool(nn.Module):
    """末帧 + 学到的注意力池化 + 时间维 max。"""

    def __init__(self, c):
        super().__init__()
        self.score = nn.Conv1d(c, 1, 1)

    def forward(self, h):                                 # (B,c,T)
        w = torch.softmax(self.score(h).squeeze(1), dim=1)  # (B,T)
        att = (h * w[:, None, :]).sum(dim=2)
        return torch.cat([h[:, :, -1], att, h.max(dim=2).values], dim=1)


class Branch(nn.Module):
    def __init__(self, fdim, c, drop):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d, drop) for d in (1, 2, 4, 8)])
        self.pool = AttnPool(c)

    def forward(self, x):                                  # (B,T,F)
        h = self.blocks(self.inp(x.transpose(1, 2)))
        return self.pool(h)


class GRL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lam):
        ctx.lam = lam
        return x.view_as(x)

    @staticmethod
    def backward(ctx, g):
        return -ctx.lam * g, None


class V2Net(nn.Module):
    def __init__(self, fdim, chans, n_env, adv=False, drop=0.15):
        super().__init__()
        self.branches = nn.ModuleList([Branch(fdim, c, drop) for c in chans])
        feat = sum(3 * c for c in chans)
        self.head = nn.Sequential(nn.Linear(feat, 128), nn.GELU(),
                                  nn.Dropout(drop), nn.Linear(128, 1))
        self.aux = nn.Sequential(nn.Linear(feat, 64), nn.GELU(), nn.Linear(64, 2))
        self.adv = None
        if adv:
            self.adv = nn.Sequential(nn.Linear(feat, 128), nn.GELU(), nn.Linear(128, n_env))

    def forward(self, xs, lam=0.0):
        f = torch.cat([b(x) for b, x in zip(self.branches, xs)], dim=1)
        out = self.head(f).squeeze(1)
        aux = self.aux(f)
        adv = None
        if self.adv is not None:
            adv = self.adv(GRL.apply(f, lam))
        return out, aux, adv, f


# ---------------------------------------------------------------- 训练/评估
def to_gpu(D, fdim):
    """特征与窗口索引一次搬到 GPU（X 164 维仅 43 MB，索引 ~35 MB），
    之后每步只做 GPU 内的 fancy indexing，省掉每步 40 MB×2 的 PCIe 拷贝。"""
    if "_gpu" not in D:
        D["_gpu"] = {}
    if fdim not in D["_gpu"]:
        Xg = torch.from_numpy(np.ascontiguousarray(D["X"][:, :fdim])).to(DEV)
        IDXg = {sp: torch.from_numpy(D["IDX"][sp].astype(np.int64)).to(DEV) for sp in SPECS}
        D["_gpu"][fdim] = (Xg, IDXg)
    return D["_gpu"][fdim]


def gather(D, sp, sel, fdim, jitter=0, n_frames=None):
    """sel: GPU LongTensor -> (B,L,F) 窗口，全部在显存里完成。
    jitter>0 时把窗口整体随机平移 ±jitter 帧（仅训练用，标签留在原结束帧）。"""
    Xg, IDXg = to_gpu(D, fdim)
    ii = IDXg[sp][sel]
    if jitter:
        off = torch.randint(-jitter, jitter + 1, (ii.shape[0], 1), device=ii.device)
        ii = (ii + off).clamp_(0, Xg.shape[0] - 1)
    return Xg[ii]


def swap_perm(fdim):
    """左右手特征互换的列置换（bad 标签对左右对称，所以这是保标签增广）。"""
    perm = np.arange(fdim)
    offs = [0] if fdim == 82 else [0, 82]
    for off in offs:
        perm[off + 0:off + 32] = np.arange(off + 32, off + 64)
        perm[off + 32:off + 64] = np.arange(off + 0, off + 32)
        perm[off + 64:off + 72] = np.arange(off + 72, off + 80)
        perm[off + 72:off + 80] = np.arange(off + 64, off + 72)
        perm[off + 80] = off + 81
        perm[off + 81] = off + 80
    return torch.from_numpy(perm.astype(np.int64)).to(DEV)


def predict(model, D, sel, fdim, batch=4096, tta=False):
    """返回概率（不是 logits）。tta=True 时对左右交换后的输入再前向一次并平均。"""
    model.eval()
    outs, auxs = [], []
    sel_t = torch.from_numpy(np.asarray(sel)).long().to(DEV)
    perm = swap_perm(fdim) if tta else None
    with torch.no_grad():
        for i in range(0, len(sel), batch):
            s = sel_t[i:i + batch]
            xs = [gather(D, sp, s, fdim) for sp in SPECS]
            o, a, _, _ = model(xs)
            p = torch.sigmoid(o)
            if tta:
                p2 = torch.sigmoid(model([x[:, :, perm] for x in xs])[0])
                p = 0.5 * (p + p2)
            outs.append(p.cpu().numpy())
            auxs.append(a.cpu().numpy())
    return np.concatenate(outs), np.concatenate(auxs)


def ece(y, p, bins=10):
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def fit_temperature(logits, y):
    """只在 validation 上拟合 T（最小化未加权 BCE）。"""
    best = (1.0, 1e9)
    for T in np.exp(np.linspace(-1.5, 1.5, 61)):
        p = 1.0 / (1.0 + np.exp(-logits / T))
        p = np.clip(p, 1e-7, 1 - 1e-7)
        bce = float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())
        if bce < best[1]:
            best = (float(T), bce)
    return best[0]


def focal_loss(logits, y, alpha=0.75, gamma=2.0):
    ce = F.binary_cross_entropy_with_logits(logits, y, reduction="none")
    p = torch.sigmoid(logits)
    pt = p * y + (1 - p) * (1 - y)
    w = (alpha * y + (1 - alpha) * (1 - y)) * (1 - pt).pow(gamma)
    return (w * ce).mean()


def run_one(cfg_name, cfg, seed, D, AX, epochs):
    t0 = time.time()
    torch.manual_seed(seed)
    np.random.seed(seed)
    tr, va, te = D["S"] == "train", D["S"] == "validation", D["S"] == "test"
    fdim = D["X"].shape[1] if cfg["views"] == "both" else D["X"].shape[1] // 2
    itr = np.flatnonzero(tr)
    iva = np.flatnonzero(va)
    ite = np.flatnonzero(te)
    ytr, yva, yte = D["Y"][tr], D["Y"][va], D["Y"][te]

    pos = float(ytr.sum())
    pw = torch.tensor([(len(ytr) - pos) / max(pos, 1.0)], device=DEV)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    lossf_nw = nn.BCEWithLogitsLoss(reduction="none")

    env_tr_str = D["E"][itr]
    train_envs = sorted(set(env_tr_str))
    env2id = {e: i for i, e in enumerate(train_envs)}
    env_id = np.array([env2id[e] for e in env_tr_str], np.int64)
    n_env = len(train_envs)
    env_cnt = np.bincount(env_id, minlength=n_env).clip(min=1)
    env_w = torch.tensor((1.0 / np.sqrt(env_cnt)) / (1.0 / np.sqrt(env_cnt)).sum() * n_env,
                         dtype=torch.float32, device=DEV)

    model = V2Net(fdim, [64, 48, 48], n_env, adv=cfg["adv"], drop=cfg["drop"]).to(DEV)
    n_par = sum(p.numel() for p in model.parameters())
    log(f"[{cfg_name}][{seed}] params={n_par:,} fdim={fdim} train={len(itr):,} "
        f"pos_weight={pw.item():.1f} adv={cfg['adv']} dro={cfg['dro']} "
        f"drop={cfg['drop']} lr={cfg['lr']} wd={cfg['wd']} jitter={cfg['jitter']} loss={cfg['loss']}")

    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
    steps = (len(itr) + BATCH - 1) // BATCH
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=cfg["lr"], total_steps=epochs * steps)
    tr_idx = torch.from_numpy(itr).long().to(DEV)
    tgt = torch.from_numpy(np.stack([AX["occ"][itr], AX["edge"][itr]], 1)).to(DEV)
    msk_all = torch.from_numpy(AX["mask"][itr]).to(DEV)
    ytr_t = torch.from_numpy(ytr).to(DEV)
    env_g = torch.from_numpy(env_id).long().to(DEV)

    q = np.ones(n_env, np.float64) / n_env
    dro_ema = np.zeros(n_env)
    best = dict(auc=-1.0, epoch=-1, state=None, ap=0.0)
    hist = []
    for ep in range(1, epochs + 1):
        model.train()
        if cfg["dro"]:
            w = q[env_id] / env_cnt[env_id]
            perm_np = np.random.choice(len(itr), size=len(itr), replace=True, p=w / w.sum())
            perm = torch.from_numpy(perm_np).long().to(DEV)
        else:
            perm = torch.randperm(len(itr), device=DEV)
        lam = 0.0
        if cfg["adv"]:
            lam = GRL_MAX * min(1.0, ep / 3.0)
        tot, seen = 0.0, 0
        env_loss_sum = np.zeros(n_env)
        env_loss_cnt = np.zeros(n_env)
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            g = tr_idx[sel]
            xs = [gather(D, sp, g, fdim, jitter=cfg["jitter"]) for sp in SPECS]
            if cfg.get("swap_aug"):
                m = torch.rand(len(g), device=DEV) < 0.5
                for x in xs:
                    x[m] = x[m][:, :, swap_perm(fdim)]
            yb = ytr_t[sel]
            opt.zero_grad(set_to_none=True)
            out, aux, adv, _ = model(xs, lam=lam)
            loss = focal_loss(out, yb) if cfg["loss"] == "focal" else lossf(out, yb)
            if cfg["dro"]:
                el = lossf_nw(out, yb).detach().cpu().numpy()
                eid = env_id[sel.cpu().numpy()]
                for e in np.unique(eid):
                    m = eid == e
                    env_loss_sum[e] += el[m].sum()
                    env_loss_cnt[e] += m.sum()
            # 辅助头（occlusion / near edge），mask 全 1 时等价于普通多标签 BCE
            tb = tgt[sel]
            mb = msk_all[sel]
            bce = F.binary_cross_entropy_with_logits(aux, tb, reduction="none").mean(dim=1)
            loss = loss + AUX_W * (bce * mb).sum() / mb.sum().clamp(min=1.0)
            if cfg["adv"]:
                loss = loss + F.cross_entropy(adv, env_g[sel], weight=env_w)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            sched.step()
            tot += float(loss.detach()) * len(sel)
            seen += len(sel)
        if cfg["dro"]:
            le = np.where(env_loss_cnt > 0, env_loss_sum / np.maximum(env_loss_cnt, 1), dro_ema)
            dro_ema = 0.5 * dro_ema + 0.5 * le
            q = q * np.exp(DRO_ETA * (dro_ema - dro_ema.mean()))
            q = np.clip(q, 1.0 / (4 * n_env), 0.5)
            q = q / q.sum()
        pv, _ = predict(model, D, iva, fdim)
        auc = float(roc_auc_score(yva, pv))
        ap = float(average_precision_score(yva, pv))
        hist.append(dict(epoch=ep, loss=round(tot / max(seen, 1), 4),
                         val_auc=auc, val_ap=ap))
        flag = ""
        if auc > best["auc"]:
            best = dict(auc=auc, epoch=ep, ap=ap,
                        state={k: v.detach().clone() for k, v in model.state_dict().items()})
            flag = " *"
        log(f"[{cfg_name}][{seed}] ep{ep:02d} loss={tot/max(seen,1):.4f} "
            f"valAUC={auc:.4f} valAP={ap:.4f}{flag}")

    model.load_state_dict(best["state"])
    tta = bool(cfg.get("tta"))
    pv, _ = predict(model, D, iva, fdim, tta=tta)   # validation 概率
    pt, aux_t = predict(model, D, ite, fdim, tta=tta)  # test 概率（每 (config,seed) 只算这一次）
    pv = np.clip(pv, 1e-7, 1 - 1e-7)
    pt = np.clip(pt, 1e-7, 1 - 1e-7)
    lv = np.log(pv / (1 - pv))
    lt = np.log(pt / (1 - pt))
    T = fit_temperature(lv, yva)
    pt_cal = 1.0 / (1.0 + np.exp(-lt / T))

    test_auc = float(roc_auc_score(yte, pt))
    test_ap = float(average_precision_score(yte, pt))
    per_env = []
    for env in sorted(set(D["E"][te])):
        m = D["E"][te] == env
        pos_e = int(yte[m].sum())
        per_env.append(dict(env=str(env), n=int(m.sum()), positives=pos_e,
                            auc_bad=float(roc_auc_score(yte[m], pt[m])) if pos_e >= 2 else None))
    valid_envs = [e for e in per_env if e["auc_bad"] is not None]
    worst = min(e["auc_bad"] for e in valid_envs) if valid_envs else None
    worst_name = [e["env"] for e in valid_envs if e["auc_bad"] == worst][0] if valid_envs else None

    drop = pt_cal >= 0.5
    bad = yte > 0.5
    tp = int((drop & bad).sum())
    fp = int((drop & ~bad).sum())
    nb, ng = int(bad.sum()), int((~bad).sum())
    prec = float(tp / (tp + fp)) if tp + fp else None
    rec = float(tp / nb) if nb else None
    secs = round(time.time() - t0, 1)
    res = dict(
        config=cfg_name, seed=seed, params=int(n_par), seconds=secs,
        best_epoch=best["epoch"], epochs=epochs,
        val_auc=float(roc_auc_score(yva, pv)), val_ap=float(average_precision_score(yva, pv)),
        val_auc_selected=best["auc"], val_ap_selected=best["ap"],
        test_auc=test_auc, test_ap=test_ap, per_env=per_env,
        worst_env=worst, worst_env_name=worst_name,
        calib=dict(temperature=T, ece_before=ece(yte, pt), ece_after=ece(yte, pt_cal),
                   precision_at_half=prec, recall_at_half=rec,
                   drop_rate=float(drop.mean()),
                   good_dropped_rate=float(fp / ng) if ng else None),
        history=hist,
        probs=dict(pt=pt.astype(np.float32), pt_cal=pt_cal.astype(np.float32),
                   pv=pv.astype(np.float32), yte=yte.astype(np.float32),
                   yv=yva.astype(np.float32), env=D["E"][te]),
    )
    log(f"[{cfg_name}][{seed}] testAUC={test_auc:.6f} testAP={test_ap:.6f} "
        f"worst={worst if worst is None else round(worst,6)}({worst_name}) bestEp={best['epoch']} "
        f"T={T:.2f} ECE {res['calib']['ece_before']:.4f}->{res['calib']['ece_after']:.4f} "
        f"P@0.5={prec} R@0.5={rec} {secs}s")
    return res


def agg(rows):
    out = {}
    for k in ("val_auc", "val_ap", "test_auc", "test_ap", "seconds", "params",
              "best_epoch", "calib.ece_after"):
        pass
    def m(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return float(np.mean(vals)) if vals else None
    out["n_seeds"] = len(rows)
    out["val_auc"] = m("val_auc")
    out["val_ap"] = m("val_ap")
    out["test_auc"] = m("test_auc")
    out["test_ap"] = m("test_ap")
    out["test_ap_std"] = float(np.std([r["test_ap"] for r in rows], ddof=1)) if len(rows) > 1 else 0.0
    out["test_auc_std"] = float(np.std([r["test_auc"] for r in rows], ddof=1)) if len(rows) > 1 else 0.0
    out["worst_env"] = float(np.mean([r["worst_env"] for r in rows if r["worst_env"] is not None]))
    out["worst_env_per_seed"] = {str(r["seed"]): r["worst_env"] for r in rows}
    out["test_ap_per_seed"] = {str(r["seed"]): r["test_ap"] for r in rows}
    out["test_auc_per_seed"] = {str(r["seed"]): r["test_auc"] for r in rows}
    out["val_auc_per_seed"] = {str(r["seed"]): r["val_auc"] for r in rows}
    out["params"] = rows[0]["params"]
    out["train_seconds_total"] = float(sum(r["seconds"] for r in rows))
    out["calib"] = dict(
        temperature={str(r["seed"]): r["calib"]["temperature"] for r in rows},
        ece_after=float(np.mean([r["calib"]["ece_after"] for r in rows])),
        ece_before=float(np.mean([r["calib"]["ece_before"] for r in rows])),
        precision_at_half={str(r["seed"]): r["calib"]["precision_at_half"] for r in rows},
        recall_at_half={str(r["seed"]): r["calib"]["recall_at_half"] for r in rows},
        good_dropped_rate=float(np.mean([r["calib"]["good_dropped_rate"] for r in rows])),
    )
    ok_ap = out["test_ap"] >= GATE["mean_test_ap_min"]
    ok_worst = out["worst_env"] >= GATE["mean_worst_env_auc_min"]
    out["gate"] = dict(
        mean_test_ap_ge=out["test_ap"] >= GATE["mean_test_ap_min"],
        mean_worst_env_auc_ge=out["worst_env"] >= GATE["mean_worst_env_auc_min"],
        ap_margin=out["test_ap"] - GATE["mean_test_ap_min"],
        worst_margin=out["worst_env"] - GATE["mean_worst_env_auc_min"],
        passes=bool(ok_ap and ok_worst),
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfgs = [c.strip() for c in args.configs.split(",") if c.strip()]
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    epochs = 2 if args.smoke else args.epochs

    os.makedirs(LOGS, exist_ok=True)
    log(f"=== run start: device={DEV} torch={torch.__version__} configs={cfgs} "
        f"seeds={seeds} epochs={epochs} smoke={args.smoke} ===")
    if DEV == "cuda":
        p = torch.cuda.get_device_properties(0)
        log(f"gpu={p.name} {p.total_memory/1e9:.2f}GB")

    D = build_data()
    AX = build_aux(D)
    payload = dict(_meta=dict(script="up2_p1b_v2.py", gate=GATE, protocol=dict(
        windows=[[t, st] for t, st in SPECS], batch=BATCH, lr=LR, wd=WD, epochs=epochs,
        aux_weight=AUX_W, dropout=0.15, norm_prefix=NORM_PREFIX,
        selection="best epoch by validation AUC; test scored once"), configs=CONFIGS),
        results={})
    # 续跑：已有 JSON 里别的配置原样保留（V1 的结果不能被后来的 run 覆盖）
    if os.path.exists(OUT_JSON) and not args.smoke:
        try:
            old = json.load(open(OUT_JSON, encoding="utf-8"))
            payload["results"] = old.get("results", {})
            payload["_meta"]["configs"] = {**old.get("_meta", {}).get("configs", {}), **CONFIGS}
            log(f"merge existing {OUT_JSON}: {list(payload['results'])}")
        except Exception as e:
            log(f"merge skipped: {e}")

    for cname in cfgs:
        cfg = CONFIGS[cname]
        rows = []
        for seed in seeds:
            log(f"running {cname} seed={seed}")
            res = run_one(cname, cfg, seed, D, AX, epochs)
            probs = res.pop("probs")
            np.savez_compressed(os.path.join(DATA, f"up2_p1b_probs_{cname}_{seed}.npz"), **probs)
            rows.append(res)
            payload["results"].setdefault(cname, dict(desc=cfg["desc"], per_seed={}))
            payload["results"][cname]["per_seed"][str(seed)] = res
            payload["results"][cname]["aggregate"] = agg(rows)
            with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
        a = payload["results"][cname]["aggregate"]
        log(f"== {cname} == valAUC={a['val_auc']:.5f} testAUC={a['test_auc']:.5f} "
            f"testAP={a['test_ap']:.5f} worst={a['worst_env']:.5f} "
            f"gate={'PASS' if a['gate']['passes'] else 'FAIL'}")

    # 选择规则：validation mean AUC 最高的配置（不看 test）
    if len(payload["results"]) > 1:
        ranked = sorted(payload["results"].items(),
                        key=lambda kv: kv[1]["aggregate"]["val_auc"], reverse=True)
        sel = ranked[0][0]
        payload["selection"] = dict(rule=GATE["selection_rule"], selected=sel,
                                    val_auc=payload["results"][sel]["aggregate"]["val_auc"])
        payload["passes"] = bool(payload["results"][sel]["aggregate"]["gate"]["passes"])
        payload["any_config_passes"] = {k: bool(v["aggregate"]["gate"]["passes"])
                                        for k, v in payload["results"].items()}
        payload["gate"] = GATE
    else:
        only = list(payload["results"])[0]
        payload["passes"] = bool(payload["results"][only]["aggregate"]["gate"]["passes"])
        payload["gate"] = GATE
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    log(f"saved -> {OUT_JSON}")
    for k, v in payload["results"].items():
        a = v["aggregate"]
        log(f"RESULT {k}: AP={a['test_ap']:.5f} AUC={a['test_auc']:.5f} "
            f"worst={a['worst_env']:.5f} params={a['params']:,} "
            f"secs={a['train_seconds_total']:.0f} pass={a['gate']['passes']}")


if __name__ == "__main__":
    main()