
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 补充：K 选择敏感性 + 过分割后处理（阈值在 TRAIN 记录上定，TEST 上冻结评估）。

动机（data/best_p1a.json 已跑）：BIC 的 kmax 从 8 提到 25，ARI 0.4138 -> 0.5387，
但 b_recall 0.993 / b_precision 0.527、平均段数 18.3 vs 真值 8.9 —— 主要误差已从
「找不到边界」变成「过分割」。本脚本两件事：

1) kmax 扫描 {8,12,16,20,25,32,40}：同一 7 条 test 记录、同一评估函数。
2) 固定 kmax=25，加相邻段合并规则：相邻两段若都短于 dmin 帧、且质心距离 < tau 就合并；
   tau/dmin 在 TRAIN 记录（同样 kmax=25 的 ward）上网格搜索取 ARI 最优，再只在 TEST 评一次。

函数全部 import 自 best_p1a_seg.py（同协议、同特征），不 import p1_model.py（那个模块
一旦 import 会重跑评估并覆写 data/p1_segmentation.json）。输出 data/best_p1a_k.json。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))

import best_p1a_seg as B  # noqa: E402  安全：模块级只有 np.load / read_csv

state_matrix, true_labels, smooth = B.state_matrix, B.true_labels, B.smooth
choose_k, ward_segments, score, runs_of = B.choose_k, B.ward_segments, B.score, B.runs_of
recs, segs, T = B.recs, B.segs, B.T


def merge_runs(X, lab, tau, dmin):
    """相邻两段都短于 dmin 帧、质心距离 < tau 则合并；返回 run id。"""
    cur = lab.copy()
    for _ in range(400):
        rr = runs_of(cur)
        if len(rr) < 2:
            break
        cents = [X[a:b].mean(0) for a, b, _ in rr]
        lens = [b - a for a, b, _ in rr]
        done = False
        for i in range(len(rr) - 1):
            if lens[i] < dmin and lens[i + 1] < dmin and \
                    np.linalg.norm(cents[i] - cents[i + 1]) < tau:
                a0 = rr[i][0]
                b1 = rr[i + 1][1]
                cur[a0:b1] = cur[a0]
                done = True
                break
        if not done:
            break
    return B.to_run_id(cur)


def prep(r):
    ii, X = state_matrix(r)
    y = true_labels(r, ii)
    good = y >= 0
    if good.sum() < 20 or len(np.unique(y[good])) < 2:
        return None
    Xg = np.nan_to_num(X[good], nan=0.0, posinf=0.0, neginf=0.0)
    Xg = smooth(Xg, 5)
    Xg = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-6)
    return dict(rec=int(r), X=Xg, y=y[good], t=T[ii][good],
                Ktrue=int(len(np.unique(y[good]))), n=int(good.sum()))


def m(rows, k):
    v = [r[k] for r in rows if np.isfinite(r[k])]
    return float(np.mean(v)) if v else float("nan")


CACHE = {}


def get(r):
    if r not in CACHE:
        CACHE[r] = prep(r)
    return CACHE[r]


def main():
    test_ids = [int(r) for r in recs[recs.split == "test"].rec
                if len(segs[segs.rec == r]) >= 2]
    train_ids = [int(r) for r in recs[recs.split == "train"].rec
                 if len(segs[segs.rec == r]) >= 2]
    print("test", test_ids, "| train records", len(train_ids))

    # 1) kmax sweep on TEST
    sweep = []
    for kmax in [8, 12, 16, 20, 25, 32, 40]:
        rows = []
        for r in test_ids:
            d = get(r)
            if d is None:
                continue
            K = choose_k(d["X"], kmax)
            sc = score(ward_segments(d["X"], K), d["y"], d["t"])
            sc.update(rec=r, K=int(K), Ktrue=d["Ktrue"])
            rows.append(sc)
        agg = {k: m(rows, k) for k in ["ari", "f1", "b_mae", "b_recall", "b_precision",
                                       "n_seg", "K"]}
        agg.update(kmax=kmax, records=len(rows))
        print(f"kmax={kmax:2d} ARI={agg['ari']:.4f} F1={agg['f1']:.4f} "
              f"Kbar={agg['K']:.1f} nseg={agg['n_seg']:.1f} "
              f"bRec={agg['b_recall']:.3f} bPre={agg['b_precision']:.3f}")
        sweep.append(dict(kmax=kmax, agg=agg, rows=rows))

    # 2) merge rule, tuned on TRAIN only
    KMAX = 25
    lab_train = {}
    for r in train_ids:
        d = get(r)
        if d is None:
            continue
        lab_train[r] = ward_segments(d["X"], choose_k(d["X"], KMAX))
    print(f"train ward(kmax={KMAX}) over {len(lab_train)} records")

    grid = [(0.0, 0)] + [(tau, dm) for tau in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
                         for dm in [5, 10, 20, 40]]
    gres = []
    for tau, dm in grid:
        aris, nsegs = [], []
        for r, lab in lab_train.items():
            d = get(r)
            l2 = lab if tau == 0 else merge_runs(d["X"], lab, tau, dm)
            sc = score(l2, d["y"], d["t"])
            aris.append(sc["ari"])
            nsegs.append(sc["n_seg"])
        gres.append(dict(tau=tau, dmin=dm, train_ari=float(np.mean(aris)),
                         train_nseg=float(np.mean(nsegs))))
        print(f"  tau={tau:4.2f} dmin={dm:3d} trainARI={np.mean(aris):.4f} "
              f"nseg={np.mean(nsegs):.1f}")
    best = max(gres, key=lambda g: g["train_ari"])
    print("best merge on TRAIN:", best)

    rows = []
    for r in test_ids:
        d = get(r)
        if d is None:
            continue
        K = choose_k(d["X"], KMAX)
        lab = ward_segments(d["X"], K)
        l2 = merge_runs(d["X"], lab, best["tau"], best["dmin"])
        s0, s1 = score(lab, d["y"], d["t"]), score(l2, d["y"], d["t"])
        rows.append(dict(rec=r, K=int(K), Ktrue=d["Ktrue"],
                         ari_before=s0["ari"], ari_after=s1["ari"],
                         f1_before=s0["f1"], f1_after=s1["f1"],
                         nseg_before=s0["n_seg"], nseg_after=s1["n_seg"],
                         b_pre_before=s0["b_precision"], b_pre_after=s1["b_precision"],
                         b_rec_before=s0["b_recall"], b_rec_after=s1["b_recall"],
                         b_mae_before=s0["b_mae"], b_mae_after=s1["b_mae"]))
    keys = ["ari_before", "ari_after", "f1_before", "f1_after", "nseg_before",
            "nseg_after", "b_pre_before", "b_pre_after", "b_rec_before",
            "b_rec_after", "b_mae_before", "b_mae_after"]
    agg = {k: m(rows, k) for k in keys}
    d_ari = np.array([r["ari_after"] - r["ari_before"] for r in rows])
    out = dict(
        _meta=dict(protocol="exact best_p1a_seg.py protocol (same features, smooth5, "
                            "per-record z, run ids, ARI + Hungarian F1 + boundary tol 5 s)",
                   baseline="data/p1_segmentation.json ward ARI=0.413842 F1=0.561317 (kmax=8)",
                   prev="data/best_p1a.json ward_k25 ARI=0.538672 F1=0.602829",
                   merge_rule="merge adjacent runs when both < dmin frames and centroid "
                              "distance < tau; tau/dmin fitted on TRAIN records only",
                   test_records=test_ids, n_train_records=len(lab_train)),
        kmax_sweep=sweep, merge_grid=gres, best_merge=best,
        merge_test_agg=agg, merge_test_rows=rows,
        merge_delta_ari_per_record=d_ari.tolist(),
        merge_delta_ari_mean=float(d_ari.mean()),
        merge_delta_ari_median=float(np.median(d_ari)),
        merge_wins=int((d_ari > 0).sum()), merge_losses=int((d_ari < 0).sum()))
    p = os.path.join(DATA, "best_p1a_k.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nMERGE TEST:", {k: round(v, 4) for k, v in agg.items()})
    print(f"delta ARI mean={d_ari.mean():+.4f} wins={out['merge_wins']}/{len(rows)}")
    print("saved ->", p)


if __name__ == "__main__":
    main()