
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 严格模型选择：**在 validation 上选准则与 K 上限，冻结后只在 test 跑一次**。

依据官方 `information_rule`（fit on train / choose model on validation /
freeze before test / no future-source lookup）。

split 取值实测为 `train` / `validation` / `test`（55 / 7 / 7 条记录）。

候选：
  bic@kmax    : GMM-BIC 选 K（kmax 取 8/12/16/20/25/30）
  sil@kmax    : 轮廓系数选 K（kmax 取 8/25）
  rule        : k = clip(round(总时长 / train 中位段长), 2, 30)

输出 data/best_p1a_select.json
"""
import json
import os
import sys
import time

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import best_p1a_seg as B  # noqa: E402

OUT = os.path.join(B.DATA, "best_p1a_select.json")
BIC_KMAX = [8, 12, 16, 20, 25, 30]
SIL_KMAX = [8, 25]


def sil_best(X, kmax=8, seed=0):
    Xs = X[::3]
    if len(Xs) > 1200:
        Xs = Xs[:: max(1, len(Xs) // 1200)]
    best, bk = -1.0, 2
    for k in range(2, min(kmax, len(Xs) // 20) + 1):
        try:
            lab = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Xs)
            if len(np.unique(lab)) < 2:
                continue
            s = float(silhouette_score(Xs, lab))
        except Exception:
            continue
        if s > best:
            best, bk = s, k
    return bk, best


def prep(split, med, tag):
    out = {}
    recs = [int(r) for r in B.recs[B.recs.split == split].rec
            if len(B.segs[B.segs.rec == r]) >= 2]
    for r in recs:
        ii, X = B.state_matrix(r)
        y = B.true_labels(r, ii)
        good = y >= 0
        Xg = np.nan_to_num(X[good], nan=0.0, posinf=0.0, neginf=0.0)
        Xg = B.smooth(Xg, 5)
        Xg = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-6)
        yv, tv = y[good], B.T[ii][good]
        dt = float(np.median(np.diff(tv))) if len(tv) > 2 else 0.0333
        k_bic = {km: int(B.choose_k(Xg, kmax=km)) for km in BIC_KMAX}
        k_sil = {km: int(sil_best(Xg, kmax=km)[0]) for km in SIL_KMAX}
        k_rule = int(np.clip(round(len(tv) * dt / med), 2, 30))
        rows = {}
        for km, k in k_bic.items():
            rows[f"bic@{km}"] = dict(k=k, **B.score(B.ward_segments(Xg, k), yv, tv))
        for km, k in k_sil.items():
            rows[f"sil@{km}"] = dict(k=k, **B.score(B.ward_segments(Xg, k), yv, tv))
        rows["rule"] = dict(k=k_rule, **B.score(B.ward_segments(Xg, k_rule), yv, tv))
        out[r] = dict(split=tag, ktrue=int(len(np.unique(yv))), cand=rows)
        print(f"  [{tag}] rec {r:02d} Ktrue={out[r]['ktrue']:2d} " +
              " ".join(f"{c}:k{r_['k']}/ari{r_['ari']:.3f}" for c, r_ in rows.items()
                       if c in ("bic@25", "sil@25", "rule")))
    return out


def main():
    t0 = time.time()
    train_recs = [int(r) for r in B.recs[B.recs.split == "train"].rec]
    dur = (B.segs.end - B.segs.start)
    med = float(np.median(dur[B.segs.rec.isin(train_recs)]))
    ktrue_train_max = 23  # 实测：train 55 条中最大段数 23（rec 60）
    print(f"train median segment = {med:.2f} s ; train max Ktrue = {ktrue_train_max}")

    print("== validation ==")
    val = prep("validation", med, "validation")
    print("== test ==")
    test = prep("test", med, "test")

    cands = sorted({c for r in val.values() for c in r["cand"]})

    def mean_ari(db, c):
        return float(np.mean([r["cand"][c]["ari"] for r in db.values()]))

    table = {c: dict(val=mean_ari(val, c), test=mean_ari(test, c),
                     val_min=float(np.min([r["cand"][c]["ari"] for r in val.values()])),
                     test_min=float(np.min([r["cand"][c]["ari"] for r in test.values()])))
             for c in cands}
    for c in cands:
        t = table[c]
        print(f"  {c:9s} val={t['val']:.4f} (min {t['val_min']:.3f})   "
              f"test={t['test']:.4f} (min {t['test_min']:.3f})")

    chosen = max(cands, key=lambda c: table[c]["val"])
    print(f"\n=> chosen on validation: {chosen}  "
          f"val={table[chosen]['val']:.4f}  test={table[chosen]['test']:.4f}")

    out = {"_meta": {"split_values": "train/validation/test = 55/7/7",
                     "train_median_segment_s": med,
                     "train_max_ktrue": ktrue_train_max,
                     "bic_kmax": BIC_KMAX, "sil_kmax": SIL_KMAX,
                     "candidates": cands},
           "table": table, "chosen": chosen,
           "chosen_test_ari": table[chosen]["test"],
           "val_detail": {str(r): v for r, v in val.items()},
           "test_detail": {str(r): v for r, v in test.items()},
           "seconds": time.time() - t0}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"written {OUT}  {out['seconds']:.1f}s")


if __name__ == "__main__":
    main()