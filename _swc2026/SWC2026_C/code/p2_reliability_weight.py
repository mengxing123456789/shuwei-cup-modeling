# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成的可靠性权重实验（P1 的软权重是否真的服务 P2）。
# -*- coding: utf-8 -*-
"""P1 -> P2 的那条链：把可靠性做成 P2 的样本权重，而不是一个阈值过滤器。

现状（Arm A）：`p2_predict.windows` 只保留「窗口内零坏帧」的窗口。于是可靠性分数
无论多准都进不了回归 —— 08 纲领把它列成第一个结构性缺口。

三臂对照，**特征、目标、上下文、提前量、正则、测试集全部相同**，只改训练集的权重
与是否纳入含坏帧的窗口：

  A  clean_only     仅干净窗口，无权重（现状）
  B  soft_weight    含坏帧窗口也进训练，权重 = 窗口内干净帧比例
  C  all_unweighted 含坏帧窗口也进训练，不加权

设计沿用 `p2_predict.train_ridge`：每个窗口展开 L 行，特征 = [feats(ctx), (h+1)/L,
L/30]，目标 = tgt[h] - ctx[-1]，不同之处只有 (i) 起跳点取自**全位置均匀格点**（A 是其
子集，其余两臂用全集）与 (ii) 加权正规方程。测试只在**干净窗口**上评，与论文一致。

输出 data/p2_reliability_weight.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from common import DATA
import p2_predict as P

CTX = 10
LEAD = 30
CAP = 400
ALPHA = 10.0


def starts_all(split):
    """Uniform start lattice over every frame position (not conditioned on badness)."""
    out = []
    span = CTX + LEAD
    stride = max(1, LEAD // 2)
    for r in P.recs[P.recs.split == split].rec:
        ii = np.where(P.rec == r)[0]
        F = P.hand_of(r)[ii, :3]
        bad = (P.badL[ii] if P.dom[r] == 0 else P.badR[ii]).astype(bool)
        n = len(ii)
        if n < span + 1:
            continue
        st = np.arange(0, n - span, stride)
        if len(st) > CAP:
            st = st[np.linspace(0, len(st) - 1, CAP).astype(int)]
        for s0 in st:
            clean = ~bad[s0:s0 + span]
            out.append((F[s0:s0 + CTX], F[s0 + CTX:s0 + span], float(clean.mean()), int(r)))
    return out


def rows_for(win, w):
    f = P.feats(win[0])
    ctx_last = win[0][-1]
    X, Y = [], []
    for h in range(LEAD):
        X.append(np.concatenate([f, [(h + 1) / LEAD, LEAD / 30.0]]))
        Y.append(win[1][h] - ctx_last)
    return np.asarray(X), np.asarray(Y), float(w)


def build(split, keep):
    Xs, Ys, Ws = [], [], []
    for ctx, tgt, w, _r in starts_all(split):
        if keep == "clean" and w < 1.0:
            continue
        X, Y, _ = rows_for((ctx, tgt), w)
        Xs.append(X)
        Ys.append(Y)
        Ws.append(np.full(len(X), w if keep == "soft" else 1.0))
    return np.vstack(Xs), np.vstack(Ys), np.concatenate(Ws)


def wridge(X, Y, w, alpha=ALPHA):
    sw = np.sqrt(w)[:, None]
    Xs, Ys = X * sw, Y * sw
    xm, ym = Xs.mean(0, keepdims=True), Ys.mean(0, keepdims=True)
    Xc, Yc = Xs - xm, Ys - ym
    M = Xc.T @ Xc + alpha * np.eye(X.shape[1])
    Wc = np.linalg.solve(M, Xc.T @ Yc)
    b0 = (ym - xm @ Wc).ravel()
    return Wc, b0


def pred_window(mdl, ctx):
    f = P.feats(ctx)
    X = np.asarray([np.concatenate([f, [(h + 1) / LEAD, LEAD / 30.0]]) for h in range(LEAD)])
    Wc, b0 = mdl
    return X @ Wc + b0 + ctx[-1]


def main():
    t0 = time.time()
    arms = {}
    models = {}
    lst = starts_all("test")
    tests = [(c, t, w, r) for c, t, w, r in lst if w >= 1.0]
    print(f"start lattice: train={len(starts_all('train'))} test={len(lst)} (clean test={len(tests)})")

    for name, keep in (("A_clean_only", "clean"),
                       ("B_soft_weight", "soft"),
                       ("C_all_unweighted", "all")):
        X, Y, W = build("train", keep)
        mdl = wridge(X, Y, W)
        models[name] = mdl
        errs, ends, per = [], [], {}
        for ctx, tgt, w, r in tests:
            pr = pred_window(mdl, ctx)
            e = np.linalg.norm(pr - tgt, axis=1)
            errs.append(e)
            ends.append(e[-1])
            per.setdefault(r, []).append(float(np.sqrt((e ** 2).mean()) * 100))
        E, end = np.asarray(errs), np.asarray(ends)
        arms[name] = {
            "n_train_windows": int(len(X) // LEAD),
            "n_train_rows": int(X.shape[0]),
            "sum_weights": float(W.sum()),
            "rmse_cm": float(np.sqrt((E ** 2).mean()) * 100),
            "rmse_coord_cm": float(np.sqrt((E ** 2).mean()) * 100 / np.sqrt(3)),
            "median_end_cm": float(np.median(end) * 100),
            "within_2cm": float((end < 0.02).mean()),
            "per_record_cm": {str(k): float(np.mean(v)) for k, v in per.items()},
        }
        a = arms[name]
        print(f"  {name:18s} win={a['n_train_windows']:5d} rows={a['n_train_rows']:6d} "
              f"rmse={a['rmse_cm']:7.3f} coord={a['rmse_coord_cm']:6.3f} "
              f"med_end={a['median_end_cm']:6.3f} w2cm={a['within_2cm']:.3f}")

    comp = {}
    recs = sorted(set.intersection(*(set(v["per_record_cm"]) for v in arms.values())), key=int)
    for a, b in (("A_clean_only", "B_soft_weight"),
                 ("C_all_unweighted", "B_soft_weight"),
                 ("A_clean_only", "C_all_unweighted")):
        d = np.array([arms[b]["per_record_cm"][k] - arms[a]["per_record_cm"][k] for k in recs])
        half = float(1.96 * d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
        comp[f"{a}__to__{b}"] = dict(delta_cm=float(d.mean()), ci95=half,
                                    lower=float(d.mean() - half), upper=float(d.mean() + half),
                                    n_records=len(d), improved=int((d < 0).sum()),
                                    worsened=int((d > 0).sum()), per_record_cm=d.tolist())
        c = comp[f"{a}__to__{b}"]
        print(f"  {a} -> {b}: {c['delta_cm']:+.4f} cm +/- {c['ci95']:.4f} (improved {c['improved']}/{c['n_records']})")

    out = {"_meta": {
        "script": "p2_reliability_weight.py",
        "question": "does the reliability score change P2 when it enters as a sample weight?",
        "design": "same features/target/context/lead/ridge alpha/test set; only training weights differ",
        "arms": {"A_clean_only": "clean windows only (current practice)",
                 "B_soft_weight": "all windows, weight = clean fraction of the window",
                 "C_all_unweighted": "all windows, no weighting"},
        "start_lattice": "uniform stride LEAD//2 over every frame position; A is a subset of B and C",
        "test_rule": "evaluated on clean windows only, as in the paper",
        "ctx_frames": CTX, "lead_frames": LEAD, "ridge_alpha": ALPHA},
        "arms": arms, "comparisons": comp,
        "seconds": round(time.time() - t0, 1),
        "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    (Path(str(DATA)) / "p2_reliability_weight.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("written p2_reliability_weight.json")


if __name__ == "__main__":
    main()