
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 的 K 上限：用 **train 内部**（55 条记录）选，再在 test 上跑一次。

背景（`data/best_p1a_select.json` 的实测）：
  validation 的 7 条记录 Ktrue 只有 {3,3,4,6,6,6,7}（最大 7），
  而 test 的 Ktrue 是 {2,4,4,9,10,12,21}。validation 分布上根本没有长记录，
  所以"在 validation 上选 K 上限"必然倒向 kmax=8 —— 这不代表 kmax=8 更好，
  只代表 validation 与 test 的段数分布不同（train 的 Ktrue 最大 23，与 test 同量级）。

因此按官方 `fit on train / freeze before test` 的允许范围，把 K 上限的选择
放在 **train 内部**：对每条 train 记录算一次 BIC 曲线 k=2..30，再对每个上限
cap 取 argmin_{k<=cap} BIC，用 train 的**段标签**评 ARI（只用 train 标签，
不碰 test）。选出的 cap 冻结后，在 test 上一次性评估。

输出 data/best_p1a_traincv.json
"""
import json
import os
import sys
import time

import numpy as np
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import best_p1a_seg as B  # noqa: E402

OUT = os.path.join(B.DATA, "best_p1a_traincv.json")
CAPS = [8, 12, 16, 20, 25, 30]
KMAX = 30


def bic_curve(X, kmax=KMAX, seed=0):
    """返回 {k: bic}，与 best_p1a_seg.choose_k 同一构造（X[::3] 子采样）。"""
    Xs = X[::3]
    top = min(kmax, len(Xs) // 20)
    out = {}
    for k in range(2, top + 1):
        try:
            g = GaussianMixture(k, covariance_type="diag", random_state=seed,
                                n_init=2, max_iter=200).fit(Xs)
            out[k] = float(g.bic(Xs))
        except Exception:
            continue
    return out


def prep(r):
    ii, X = B.state_matrix(r)
    y = B.true_labels(r, ii)
    good = y >= 0
    Xg = np.nan_to_num(X[good], nan=0.0, posinf=0.0, neginf=0.0)
    Xg = B.smooth(Xg, 5)
    Xg = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-6)
    return Xg, y[good], B.T[ii][good]


def main():
    t0 = time.time()
    train_recs = [int(r) for r in B.recs[B.recs.split == "train"].rec
                  if len(B.segs[B.segs.rec == r]) >= 2]
    print(f"train records with >=2 segments: {len(train_recs)}")

    per_rec = {}
    for i, r in enumerate(train_recs):
        Xg, y, t = prep(r)
        bc = bic_curve(Xg)
        row = dict(ktrue=int(len(np.unique(y))), n=int(len(y)), bic_n=max(bc) if bc else 0,
                   ari={})
        for cap in CAPS:
            cand = [k for k in bc if k <= cap]
            if not cand:
                continue
            k = min(cand, key=lambda kk: bc[kk])
            lab = B.ward_segments(Xg, k)
            row["ari"][str(cap)] = dict(k=int(k), ari=float(adjusted_rand_score(y, lab)))
        per_rec[r] = row
        if i % 10 == 0:
            print(f"  {i+1}/{len(train_recs)} rec {r:02d} Ktrue={row['ktrue']} "
                  f"k@25={row['ari'].get('25', {}).get('k')} "
                  f"({time.time()-t0:.0f}s)")

    mean = {}
    for cap in CAPS:
        vals = [v["ari"][str(cap)]["ari"] for v in per_rec.values() if str(cap) in v["ari"]]
        mean[str(cap)] = dict(mean=float(np.mean(vals)), n=len(vals), min=float(np.min(vals)))

    # 只看"上限真正绑定"的子集：Ktrue > cap 的记录
    strat = {}
    for cap in CAPS:
        sub = [v["ari"][str(cap)]["ari"] for v in per_rec.values()
               if v["ktrue"] > cap and str(cap) in v["ari"]]
        strat[str(cap)] = dict(mean=float(np.mean(sub)) if sub else float("nan"),
                               n=len(sub))
    # 长记录子集（Ktrue>=9，与 test 的长记录同量级）
    longsub = {r: v for r, v in per_rec.items() if v["ktrue"] >= 9}
    long_mean = {}
    for cap in CAPS:
        vals = [v["ari"][str(cap)]["ari"] for v in longsub.values() if str(cap) in v["ari"]]
        long_mean[str(cap)] = dict(mean=float(np.mean(vals)) if vals else float("nan"),
                                   n=len(vals))

    print("\ncap   train_mean  (n bound)   longrec(Ktrue>=9)")
    for cap in CAPS:
        m = mean[str(cap)]
        s = strat[str(cap)]
        lm = long_mean[str(cap)]
        print(f"{cap:3d}   {m['mean']:.4f}  ({s['n']:2d} bound {s['mean']:.4f})   "
              f"{lm['mean']:.4f} (n={lm['n']})")

    best = max(CAPS, key=lambda c: mean[str(c)]["mean"])
    print(f"\n=> cap chosen on train-internal ARI: {best} (train mean {mean[str(best)]['mean']:.4f})")

    # 冻结后 test（数字来自 best_p1a_ksweep.json，同一代码路径）
    ks = json.load(open(os.path.join(B.DATA, "best_p1a_ksweep.json"), encoding="utf-8"))
    test_frozen = ks["bic"][str(best)]["mean"]
    print(f"   frozen -> test mean ARI = {test_frozen['ari']:.4f}")

    out = {"_meta": {"caps": CAPS, "kmax": KMAX,
                     "selection": "train-internal ARI (labels of train only)",
                     "n_train": len(train_recs),
                     "note": "validation has Ktrue max 7 while test has up to 21; "
                             "val-based selection is biased toward kmax=8"},
           "train_mean": mean, "train_strat_bound": strat, "long_records": long_mean,
           "cap_chosen": best, "test_frozen": test_frozen,
           "per_record": {str(k): {kk: vv for kk, vv in v.items()} for k, v in per_rec.items()},
           "seconds": time.time() - t0}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"written {OUT}  {out['seconds']:.1f}s")


if __name__ == "__main__":
    main()