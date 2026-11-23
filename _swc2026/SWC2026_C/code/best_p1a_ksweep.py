
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 稳健性：K 上限敏感性 + 换 k 准则对照。

问题：ward_k25 的 ARI 0.5387 是不是只在 kmax=25 这一档出现？
协议与 best_p1a_seg.py 完全一致（同 7 条 test 记录、同预处理、同评分），
只替换 choose_k 的上限 / 准则。

三条准则：
  gustafsson? 不 —— 实际是：
  1) bic      : 原脚本的 GMM-BIC（无标签）
  2) sil      : 轮廓系数（无标签，同样子采样 X[::3]）
  3) rule     : 固定经验规则 k = round(总时长 / train 中位段长)，与数据分布绑定但不用标签

输出 data/best_p1a_ksweep.json
"""
import json
import os
import sys
import time

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import best_p1a_seg as B  # noqa: E402

DATA = B.DATA
OUT = os.path.join(DATA, "best_p1a_ksweep.json")

KSWEEP = [8, 12, 16, 20, 25, 30]


def choose_k_sil(X, kmax=8, seed=0):
    Xs = X[::3]
    if len(Xs) > 1200:
        Xs = Xs[:: max(1, len(Xs) // 1200)]
    best, bk = -1.0, 2
    for k in range(2, min(kmax, len(Xs) // 20) + 1):
        try:
            lab = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Xs)
            if len(np.unique(lab)) < 2:
                continue
            s = silhouette_score(Xs, lab)
        except Exception:
            continue
        if s > best:
            best, bk = s, k
    return bk


def main():
    t0 = time.time()
    eval_recs = [int(r) for r in B.recs[B.recs.split == "test"].rec
                 if len(B.segs[B.segs.rec == r]) >= 2]
    print("eval records", eval_recs)

    train_recs = [int(r) for r in B.recs[B.recs.split == "train"].rec]
    dur = (B.segs.end - B.segs.start)
    med = float(np.median(dur[B.segs.rec.isin(train_recs)]))
    print(f"train median segment duration = {med:.2f} s")

    cache = {}
    for r in eval_recs:
        ii, X = B.state_matrix(r)
        y = B.true_labels(r, ii)
        good = y >= 0
        Xg = np.nan_to_num(X[good], nan=0.0, posinf=0.0, neginf=0.0)
        Xg = B.smooth(Xg, 5)
        Xg = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-6)
        tt = B.T[ii][good]
        dt = float(np.median(np.diff(tt))) if len(tt) > 2 else 0.0333
        cache[r] = dict(X=Xg, y=y[good], t=tt, dt=dt,
                        Ktrue=int(len(np.unique(y[good]))), n=int(good.sum()))
        print(f"  rec {r:02d} n={good.sum():5d} Ktrue={cache[r]['Ktrue']} dt={dt:.4f}")

    res = {"_meta": {"protocol": "same as best_p1a_seg.py", "ksweep": KSWEEP,
                     "train_median_segment_s": med, "eval_records": eval_recs,
                     "seed": 0}, "bic": {}, "sil": {}, "rule": {}}

    # --- 1) BIC 上限扫描 ---
    for kmax in KSWEEP:
        rows = []
        for r in eval_recs:
            c = cache[r]
            K = B.choose_k(c["X"], kmax=kmax)
            lab = B.ward_segments(c["X"], K)
            s = B.score(lab, c["y"], c["t"])
            rows.append(dict(rec=r, k=int(K), ktrue=c["Ktrue"], **s))
            print(f"[bic kmax={kmax:2d}] rec {r:02d} k={K:2d} ktrue={c['Ktrue']:2d} "
                  f"ari={s['ari']:.4f} f1={s['f1']:.4f} recall={s['b_recall']:.4f}")
        keys = ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]
        mean = {k: float(np.nanmean([x[k] for x in rows])) for k in keys}
        res["bic"][str(kmax)] = dict(mean=mean, records=rows)
        print(f"  >> kmax={kmax}: mean ARI={mean['ari']:.4f} recall={mean['b_recall']:.4f} "
              f"prec={mean['b_precision']:.4f} mae={mean['b_mae']:.3f}")

    # --- 2) 轮廓系数准则 ---
    for kmax in (8, 25):
        rows = []
        for r in eval_recs:
            c = cache[r]
            K = choose_k_sil(c["X"], kmax=kmax)
            lab = B.ward_segments(c["X"], K)
            s = B.score(lab, c["y"], c["t"])
            rows.append(dict(rec=r, k=int(K), ktrue=c["Ktrue"], **s))
            print(f"[sil kmax={kmax:2d}] rec {r:02d} k={K:2d} ari={s['ari']:.4f}")
        keys = ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]
        mean = {k: float(np.nanmean([x[k] for x in rows])) for k in keys}
        res["sil"][str(kmax)] = dict(mean=mean, records=rows)
        print(f"  >> sil kmax={kmax}: mean ARI={mean['ari']:.4f}")

    # --- 3) 经验规则 k = 总时长/中位段长 ---
    rows = []
    for r in eval_recs:
        c = cache[r]
        total = len(c["t"]) * c["dt"]
        K = int(np.clip(round(total / med), 2, 30))
        lab = B.ward_segments(c["X"], K)
        s = B.score(lab, c["y"], c["t"])
        rows.append(dict(rec=r, k=int(K), ktrue=c["Ktrue"], total_s=float(total), **s))
        print(f"[rule] rec {r:02d} k={K:2d} ktrue={c['Ktrue']:2d} ari={s['ari']:.4f}")
    keys = ["ari", "f1", "b_mae", "b_recall", "b_precision", "b_count_err"]
    res["rule"]["total"] = dict(mean={k: float(np.nanmean([x[k] for x in rows])) for k in keys},
                               records=rows)
    print(f"  >> rule: mean ARI={res['rule']['total']['mean']['ari']:.4f}")

    res["seconds"] = time.time() - t0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\nwritten {OUT}  {res['seconds']:.1f}s")


if __name__ == "__main__":
    main()