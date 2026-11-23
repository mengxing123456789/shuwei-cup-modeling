# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p1b_dual.py -- P1-b 升级：多时间尺度（15/60 帧双窗）+ 多任务（occlusion / near edge 辅助头）。

本脚本只做两件有依据的事（基线 best_epoch=1 → 容量不是瓶颈，所以不加深不加宽）：

  A_baseline_replica   逐字复现 code/train_gpu_p1b.py（TCN, T=15）作为对账臂
  B_dual_window        同骨架两个输入分支：短窗 15 帧(0.5s) + 长窗 60 帧(2s)，各自卷积后拼接
  C_dual_plus_multitask = B + 两个辅助头（occlusion / near edge，多标签 BCE，权重 0.3）
                        辅助损失只在 data/up_p1b_aux.npz 的 aux_mask 帧上计

纪律（与生产脚本一致，避免口径漂移）：
  - 划分 = panel_records.csv 的 split 列（16/4/4 environment）
  - 窗口不跨记录边界；长窗在记录开头用第 0 帧左填充（因果、不用未来帧）
  - 早停看 validation AUC；test 只在最后、用 best state 评一次
  - 样本集合一律由短窗（T=15）定义 → A/B/C 的 val/test 帧完全相同，指标可比
  - 固定种子 20261120；单进程；单臂 ≤10 min
  - 只写新文件 data/up_p1b_dual.json 与 data/up_p1b_probs.npz，不碰任何已有 JSON

用法：
  python up_p1b_dual.py --arms A          # 先只对账基线
  python up_p1b_dual.py --arms B,C        # 基线对上后再跑升级臂
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
from sklearn.metrics import average_precision_score, roc_auc_score

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEED = 20261120
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT_JSON = os.path.join(DATA, "up_p1b_dual.json")
OUT_NPZ = os.path.join(DATA, "up_p1b_probs.npz")

T_SHORT = 15
T_LONG = 60
BATCH = 1024
EPOCHS = 18
LR = 2e-3
WD = 1e-4
AUX_W = 0.3
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# 预注册门槛（写在代码里，跑完只认它）
BAR = dict(
    primary="test AUC >= 0.85 OR test AP >= 0.09",
    secondary=("if primary fails: AP relative gain >= 15% AND val same direction "
               "AND worst per-env AUC drop <= 0.02 vs baseline 0.7646370912154993"),
    baseline_repro=dict(test_auc=0.8220322044197129, test_ap=0.06755601550659424,
                        val_auc=0.8852539948743638, tol=1e-6),
    worst_env_baseline=0.7646370912154993,
)


# ------------------------------------------------------------------ 数据
def frame_bounds(rec):
    bounds = {}
    for r in np.unique(rec):
        idx = np.flatnonzero(rec == r)
        bounds[int(r)] = (int(idx[0]), int(idx[-1]) + 1)
    return bounds


def build_multi(T_list):
    """返回 {T: X_all}, Y, S, E, R（R = 每个样本的 rec，用于 per-env）。

    样本集合由 T_list[0]（短窗）定义；更长的窗在记录开头用第 0 帧左填充，
    保证每个样本的窗口都结束在同一帧、且不跨记录边界、不看未来帧。
    """
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
    T0 = T_list[0]
    parts = {T: [] for T in T_list}
    y_parts, s_parts, e_parts, r_parts = [], [], [], []

    for r, (lo, hi) in bounds.items():
        f = feats[lo:hi]
        lb = y[lo:hi]
        n = len(f)
        if n <= T0:
            continue
        for T in T_list:
            pad = max(0, T - 1)
            ext = np.concatenate([np.repeat(f[:1], pad, axis=0), f], axis=0) if pad else f
            win = np.lib.stride_tricks.sliding_window_view(ext, T, axis=0)  # (pad+n-T+1, F, T)
            win = np.transpose(win, (0, 2, 1))                              # (pad+n-T+1, T, F)
            win = win[T0 - 1: n]                                            # 行 j = 以原帧 j 结尾的窗
            parts[T].append(np.ascontiguousarray(win, dtype=np.float32))
        y_parts.append(lb[T0 - 1:])
        s_parts.append(np.array([split_of[r]] * len(y_parts[-1])))
        e_parts.append(np.array([env_of[r]] * len(y_parts[-1])))
        r_parts.append(np.full(len(y_parts[-1]), r, np.int32))

    X = {T: np.concatenate(parts[T], axis=0) for T in T_list}
    Y = np.concatenate(y_parts)
    S = np.concatenate(s_parts)
    E = np.concatenate(e_parts)
    R = np.concatenate(r_parts)
    del parts, y_parts, s_parts, e_parts, r_parts
    return X, Y, S, E, R


def build_aux():
    """帧级原因标签；每个样本的原因标签 = 该样本窗口末帧（= 被分类帧）的原因。"""
    a = np.load(os.path.join(DATA, "up_p1b_aux.npz"))
    return dict(occ=a["occ"], edge=a["edge"], mask=a["aux_mask"], bad_derived=a["bad_derived"])


def aux_at(AX, R, Y, S, bounds, T0=T_SHORT):
    """把帧级 aux 标签展开成样本级（与 build_multi 的样本顺序一致）。"""
    n_samp = len(Y)
    occ = np.zeros(n_samp, np.float32)
    edge = np.zeros(n_samp, np.float32)
    msk = np.zeros(n_samp, np.float32)
    k = 0
    for r in np.unique(R):
        nn = int((R == r).sum())
        lo, hi = bounds[int(r)]
        sl = slice(lo + T0 - 1, hi)
        occ[k:k + nn] = AX["occ"][sl]
        edge[k:k + nn] = AX["edge"][sl]
        msk[k:k + nn] = AX["mask"][sl]
        k += nn
    assert k == n_samp, (k, n_samp)
    return occ, edge, msk


# ------------------------------------------------------------------ 模型
class Block(nn.Module):
    """与 train_gpu_p1b.py 逐字一致。"""

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
    """A 臂：生产模型，逐字一致（保证对账）。"""

    def __init__(self, fdim, c=96):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d) for d in (1, 2, 4, 8)])
        self.head = nn.Sequential(nn.Linear(c * 2, 64), nn.GELU(), nn.Linear(64, 1))

    def forward(self, x):
        h = x.transpose(1, 2)
        h = self.blocks(self.inp(h))
        feat = torch.cat([h[:, :, -1], h.mean(dim=2)], dim=1)
        return self.head(feat).squeeze(1)


class Branch(nn.Module):
    """单分支：1x1 投影 + 同款 4 个膨胀残差块 + (末帧, 均值) 池化。"""

    def __init__(self, fdim, c=96):
        super().__init__()
        self.inp = nn.Conv1d(fdim, c, 1)
        self.blocks = nn.Sequential(*[Block(c, d) for d in (1, 2, 4, 8)])

    def forward(self, x):
        h = self.blocks(self.inp(x.transpose(1, 2)))
        return torch.cat([h[:, :, -1], h.mean(dim=2)], dim=1)


class DualTCN(nn.Module):
    """B 臂：两个独立的同构 TCN 分支（短窗 0.5 s / 长窗 2 s）后拼接。

    aux=True 时加两个辅助头（occlusion / near edge），C 臂用。
    """

    def __init__(self, fdim, c=96, aux=False):
        super().__init__()
        self.short = Branch(fdim, c)
        self.long = Branch(fdim, c)
        self.head = nn.Sequential(nn.Linear(c * 4, 64), nn.GELU(), nn.Linear(64, 1))
        self.aux = None
        if aux:
            self.aux = nn.Sequential(nn.Linear(c * 4, 64), nn.GELU(), nn.Linear(64, 2))

    def forward(self, xs, xl):
        fs = self.short(xs)
        fl = self.long(xl)
        feat = torch.cat([fs, fl], dim=1)
        out = self.head(feat).squeeze(1)
        if self.aux is None:
            return out
        return out, self.aux(feat)


# ------------------------------------------------------------------ 训练
def run_arm(name, arm, X, Y, S, E, R, AX, bounds):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    t0 = time.time()

    tr, va, te = S == "train", S == "validation", S == "test"
    ytr = torch.from_numpy(Y[tr])
    yva, yte = Y[va], Y[te]
    Xva = {T: torch.from_numpy(X[T][va]).to(DEV) for T in X}
    Xte = {T: torch.from_numpy(X[T][te]).to(DEV) for T in X}
    Ete = E[te]
    Rte = R[te]

    pos = float(ytr.sum())
    neg = float(len(ytr) - pos)
    pw = torch.tensor([neg / max(pos, 1.0)], device=DEV)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)

    fdim = X[T_SHORT].shape[2]
    if arm == "A":
        model = TCN(fdim).to(DEV)
        xs_tr = torch.from_numpy(X[T_SHORT][tr])
    else:
        model = DualTCN(fdim, aux=(arm == "C")).to(DEV)
        xs_tr = torch.from_numpy(X[T_SHORT][tr])
        xl_tr = torch.from_numpy(X[T_LONG][tr])
    n_par = sum(p.numel() for p in model.parameters())
    print(f"\n=== arm {name} ===  params={n_par:,}  pos_weight={pw.item():.2f}")

    aux_tr = None
    if arm == "C":
        occ, edge, msk = aux_at(AX, R, Y, S, bounds)
        tgt = torch.from_numpy(np.stack([occ, edge], axis=1)[tr])
        msk_t = torch.from_numpy(msk[tr])
        aux_tr = (tgt, msk_t)
        print(f"    aux train: occ+={int(tgt[:,0].sum())} edge+={int(tgt[:,1].sum())} "
              f"masked={int(msk_t.sum()):,}/{len(msk_t):,}")
    aux_va = aux_te = None
    if arm == "C":
        occ, edge, msk = aux_at(AX, R, Y, S, bounds)
        aux_va = (torch.from_numpy(np.stack([occ, edge], 1)[va]).to(DEV),
                  torch.from_numpy(msk[va]).to(DEV))
        aux_te = (torch.from_numpy(np.stack([occ, edge], 1)[te]).to(DEV),
                  torch.from_numpy(msk[te]).to(DEV))

    def fwd_eval(which):
        """-> (main logits, aux logits or None); identical sample order for every arm."""
        xs = Xva[T_SHORT] if which == "va" else Xte[T_SHORT]
        if arm == "A":
            return model(xs), None
        xl = Xva[T_LONG] if which == "va" else Xte[T_LONG]
        o = model(xs, xl)
        return (o, None) if arm == "B" else o

    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    steps = (len(xs_tr) + BATCH - 1) // BATCH
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * steps)

    best = {"auc": -1.0, "epoch": -1, "state": None, "ap": None}
    hist = []
    for ep in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(xs_tr))
        tot, nseen = 0.0, 0
        for i in range(steps):
            sel = perm[i * BATCH:(i + 1) * BATCH]
            xb = xs_tr[sel].to(DEV, non_blocking=True)
            yb = ytr[sel].to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            if arm == "A":
                out = model(xb)
                loss = lossf(out, yb)
            else:
                xlb = xl_tr[sel].to(DEV, non_blocking=True)
                if arm == "B":
                    out = model(xb, xlb)
                    loss = lossf(out, yb)
                else:
                    out, a = model(xb, xlb)
                    tgt, msk = aux_tr
                    tb = tgt[sel].to(DEV, non_blocking=True)
                    mb = msk[sel].to(DEV, non_blocking=True)
                    loss_main = lossf(out, yb)
                    bce = nn.functional.binary_cross_entropy_with_logits(
                        a, tb, reduction="none").mean(dim=1)
                    denom = mb.sum().clamp(min=1.0)
                    loss_aux = (bce * mb).sum() / denom
                    loss = loss_main + AUX_W * loss_aux
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            sched.step()
            tot += float(loss) * len(sel)
            nseen += len(sel)
        model.eval()
        with torch.no_grad():
            lg, _ = fwd_eval("va")
            pv = torch.sigmoid(lg).cpu().numpy()
        auc = roc_auc_score(yva, pv)
        ap = average_precision_score(yva, pv)
        hist.append(dict(epoch=ep, loss=round(tot / nseen, 4),
                         val_auc=float(auc), val_ap=float(ap)))
        flag = ""
        if auc > best["auc"]:
            best = {"auc": float(auc), "epoch": ep, "ap": float(ap),
                    "state": {k: v.detach().clone() for k, v in model.state_dict().items()}}
            flag = " *"
        print(f"ep{ep:02d}  loss={tot/nseen:.4f}  val AUC={auc:.4f}  val AP={ap:.4f}{flag}")

    model.load_state_dict(best["state"])
    model.eval()
    with torch.no_grad():
        lg, _ = fwd_eval("va")
        pv_best = torch.sigmoid(lg).cpu().numpy()
        lg, ax = fwd_eval("te")
        pt = torch.sigmoid(lg).cpu().numpy()
        aux_test = None
        if arm == "C":
            at = ax.cpu().numpy()
            aux_test = {}
            tgt, msk = aux_te
            tgt = tgt.cpu().numpy(); msk = msk.cpu().numpy().astype(bool)
            for j, key in enumerate(["occlusion", "near_edge"]):
                yj = tgt[msk, j]
                pj = at[msk, j]
                aux_test[key] = dict(n=int(msk.sum()), positives=int(yj.sum()),
                                     auc=float(roc_auc_score(yj, pj)) if yj.sum() > 0 else None)

    test_auc = float(roc_auc_score(yte, pt))
    test_ap = float(average_precision_score(yte, pt))
    val_auc_best = float(roc_auc_score(yva, pv_best))
    val_ap_best = float(average_precision_score(yva, pv_best))
    per_env = []
    for env in sorted(set(Ete)):
        m = Ete == env
        if m.sum() < 10 or yte[m].sum() == 0:
            continue
        per_env.append(dict(env=str(env), n=int(m.sum()), positives=int(yte[m].sum()),
                            auc_bad=float(roc_auc_score(yte[m], pt[m]))))
    secs = round(time.time() - t0, 1)
    print(f"test AUC={test_auc:.6f} AP={test_ap:.6f} | val(best ep{best['epoch']}) "
          f"AUC={val_auc_best:.6f} AP={val_ap_best:.6f} | {secs}s")
    return dict(arm=name, params=int(n_par), epochs=EPOCHS, best_epoch=int(best["epoch"]),
                val_auc=val_auc_best, val_ap=val_ap_best,
                val_auc_selected=float(best["auc"]), val_ap_selected=float(best["ap"]),
                test_auc=test_auc, test_ap=test_ap,
                test_ap_lift=float(test_ap / float(yte.mean())),
                per_env=per_env, seconds=secs, history=hist,
                aux_test=aux_test), pt, pv_best, yte, yva, Ete


def main():
    global SEED, OUT_JSON, OUT_NPZ
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=OUT_JSON, help="output json (a NEW file)")
    ap.add_argument("--outnpz", default=OUT_NPZ)
    args = ap.parse_args()
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    SEED, OUT_JSON, OUT_NPZ = args.seed, args.out, args.outnpz
    print(f"seed={SEED}  out={os.path.basename(OUT_JSON)}")

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    print(f"device={DEV}  torch={torch.__version__}  seed={SEED}")
    if DEV == "cuda":
        p = torch.cuda.get_device_properties(0)
        print(f"gpu={p.name}  {p.total_memory/1e9:.2f} GB  cap={p.major}.{p.minor}")

    T_list = [T_SHORT] if arms == ["A"] else [T_SHORT, T_LONG]
    t0 = time.time()
    X, Y, S, E, R = build_multi(T_list)
    print(f"windows={len(Y):,}  feat={X[T_SHORT].shape[2]}  "
          f"pos_rate={Y.mean():.5f}  build {time.time()-t0:.1f}s")
    tr, va, te = S == "train", S == "validation", S == "test"
    print(f"split  train={tr.sum():,}  val={va.sum():,}  test={te.sum():,}")

    z = np.load(os.path.join(DATA, "state.npz"))
    bounds = frame_bounds(z["rec"].astype(np.int64))
    AX = build_aux()
    aux_occ_s, aux_edge_s, aux_mask_s = aux_at(AX, R, Y, S, bounds)
    print(f"aux frame labels aligned: occ+={int(aux_occ_s.sum())} edge+={int(aux_edge_s.sum())} "
          f"masked={int(aux_mask_s.sum()):,}/{len(aux_mask_s):,}")

    out = {}
    probs = {}
    for arm in arms:
        name = {"A": "A_baseline_replica", "B": "B_dual_window",
                "C": "C_dual_plus_multitask"}[arm]
        res, pt, pv, yte, yva, Ete = run_arm(name, arm, X, Y, S, E, R, AX, bounds)
        out[name] = res
        probs["pt_" + arm] = pt.astype(np.float32)
        probs["pv_" + arm] = pv.astype(np.float32)

    # 与已有结果合并（同一脚本多次调用时不丢别的臂）；只写 up_ 前缀的新文件
    merged = {}
    if os.path.exists(OUT_JSON):
        try:
            old = json.load(open(OUT_JSON, encoding="utf-8"))
            merged = old.get("arms", {})
        except Exception:
            merged = {}
    merged.update(out)

    payload = dict(
        _meta=dict(
            script="up_p1b_dual.py",
            seed=SEED, seconds=round(sum(v["seconds"] for v in out.values()), 1),
            bar=BAR,
            baseline=dict(source="data/p1b_gpu.json (production train_gpu_p1b.py)",
                          test_auc=0.8220322044197129, test_ap=0.06755601550659424,
                          val_auc=0.8852539948743638, params=243873,
                          worst_env=0.7646370912154993, best_epoch=1),
            protocol=dict(
                split="panel_records.csv split (16/4/4 environment)",
                window_short=T_SHORT, window_long=T_LONG,
                window_rule=("causal; no window crosses a record boundary; the long window is "
                             "left-padded with the record's first frame so that A/B/C share the "
                             "exact same sample set (defined by the T=15 window)"),
                model="TCN 4 blocks dilations 1/2/4/8, 96ch, GroupNorm(8)+GELU, dropout 0.10",
                dual=(f"two independent 96ch branches (T={T_SHORT} and T={T_LONG}), "
                      "features (last||mean) of each concatenated -> MLP head"),
                multitask=dict(aux_heads=["occlusion", "near_edge"], aux_weight=AUX_W,
                               aux_mask="frames with a resolved reason label (data/up_p1b_aux.npz)",
                               aux_target="frame-level multi-label (side-agnostic)"),
                selection="best epoch by validation AUC; test scored once from that state",
                batch=BATCH, lr=LR, wd=WD, epochs=EPOCHS,
                early_stop="none (fixed 18 epochs, best val AUC kept)"),
            alignment=dict(script="up_p1b_align.py",
                           failure_rate=json.load(open(os.path.join(DATA, "up_p1b_align.json"),
                                                       encoding="utf-8"))["alignment_failure_rate"],
                           gate="<= 0.05"),
            arms_run=arms,
        ),
        arms=merged,
    )
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    # 概率：只补写本次跑的臂，已有键保留
    old = {}
    if os.path.exists(OUT_NPZ):
        try:
            zz = np.load(OUT_NPZ)
            old = {k: zz[k] for k in zz.files}
        except Exception:
            old = {}
    old.update(probs)
    old["yte"] = yte
    old["yv"] = yva
    old["env"] = Ete
    old["y_all"] = Y.astype(np.float32)
    old["split_all"] = S
    old["env_all"] = E
    old["rec_all"] = R
    old["aux_occ_all"] = aux_occ_s
    old["aux_edge_all"] = aux_edge_s
    old["aux_mask_all"] = aux_mask_s
    np.savez_compressed(OUT_NPZ, **old)

    print("\n=== SUMMARY ===")
    for k, v in out.items():
        print(f"{k:26s} valAUC={v['val_auc']:.6f} testAUC={v['test_auc']:.6f} "
              f"testAP={v['test_ap']:.6f} params={v['params']:,} best_ep={v['best_epoch']} "
              f"{v['seconds']}s")
        print(f"    per-env " + ", ".join(f"{e['env'].split('_')[-1]}:{e['auc_bad']:.4f}"
                                          for e in v["per_env"]))
    print(f"saved -> {OUT_JSON}\nsaved -> {OUT_NPZ}")


if __name__ == "__main__":
    main()