
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-a 混准则：用**验证集**冻结合并规则，再在 test 上一次性评估。

动机（来自 best_p1a_ksweep.json 的实测）：
  - BIC 准则在 kmax>=20 后 ARI 稳定在 0.52~0.54，但**在 rec 37 上崩塌**
    （Ktrue=2，BIC 选 23，ARI 0.014）；
  - 轮廓系数在同一记录上选 k=2，ARI 0.855，但在多段记录上远不如 BIC（总 0.4496）。

所以两条准则各有失效区。规则（无标签，只用各准则自身输出）：
      k = 2                if silhou_k == 2 and silhou_val >= tau
      k = min_bic_k(25)     otherwise
tau 只在 **validation 记录**上选，冻结后跑 test。

输出 data/best_p1a_hybrid.json
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

OUT = os.path.join(B.DATA, "best_p1a_hybrid.json")
TAU_GRID = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def sil_best(X, kmax=25, seed=0):
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


def prep(split):
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
        k_bic = int(B.choose_k(Xg, kmax=25))
        k_sil, v_sil = sil_best(Xg, kmax=25)
        yv, tv = y[good], B.T[ii][good]
        a_bic = B.score(B.ward_segments(Xg, k_bic), yv, tv)
        a_sil = B.score(B.ward_segments(Xg, k_sil), yv, tv)
        out[r] = dict(k_bic=k_bic, k_sil=int(k_sil), sil_val=v_sil,
                      ktrue=int(len(np.unique(yv))),
                      ari_bic=float(a_bic["ari"]), ari_sil=float(a_sil["ari"]),
                      X=Xg, y=yv, t=tv)
        print(f"  rec {r:02d} Ktrue={out[r]['ktrue']:2d} k_bic={k_bic:2d} "
              f"k_sil={int(k_sil):2d} v_sil={v_sil:.3f} "
              f"ari_bic={a_bic['ari']:.4f} ari_sil={a_sil['ari']:.4f}")
    return out


def hybrid_ari(c, tau):
    k = 2 if (c["k_sil"] == 2 and c["sil_val"] >= tau) else c["k_bic"]
    return float(B.score(B.ward_segments(c["X"], k), c["y"], c["t"])["ari"]), k


def main():
    t0 = time.time()
    print("== validation ==")
    val = prep("val")
    grid = {}
    for tau in TAU_GRID:
        aris = [hybrid_ari(c, tau)[0] for c in val.values()]
        grid[tau] = float(np.mean(aris))
        print(f"  tau={tau:.2f}  val mean ARI={grid[tau]:.4f}")
    tau = max(grid, key=grid.get)
    print(f"  chosen tau={tau}  (val ARI {grid[tau]:.4f})")

    print("== test (frozen rule) ==")
    test = prep("test")
    rows = []
    for r, c in test.items():
        ari_h, k_h = hybrid_ari(c, tau)
        rows.append(dict(rec=r, ktrue=c["ktrue"], k_bic=c["k_bic"], k_sil=c["k_sil"],
                         sil_val=c["sil_val"], k_hybrid=int(k_h),
                         ari_bic=c["ari_bic"], ari_sil=c["ari_sil"], ari_hybrid=ari_h))
        print(f"  rec {r:02d} k={int(k_h):2d} ari bic={c['ari_bic']:.4f} "
              f"sil={c['ari_sil']:.4f} hybrid={ari_h:.4f}")

    out = {"_meta": {"tau_grid": TAU_GRID, "tau_val_min": 0.0,
                     "n_val": len(val), "n_test": len(test),
                     "rule": "k=2 if (k_sil==2 and sil_val>=tau) else k_bic(kmax=25)"},
           "val_grid": {str(k): v for k, v in grid.items()},
           "tau": tau,
           "val_mean_ari": grid[tau],
           "test": rows,
           "test_mean": {"bic": float(np.mean([x["ari_bic"] for x in rows])),
                         "sil": float(np.mean([x["ari_sil"] for x in rows])),
                         "hybrid": float(np.mean([x["ari_hybrid"] for x in rows]))},
           "val_detail": {str(r): {k: v for k, v in c.items() if k not in ("X", "y", "t")}
                          for r, c in val.items()},
           "seconds": time.time() - t0}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\ntest mean: {out['test_mean']}")
    print(f"written {OUT}  {out['seconds']:.1f}s")


if __name__ == "__main__":
    main()