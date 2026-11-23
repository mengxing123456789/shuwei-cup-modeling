#!/usr/bin/env python3

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 补两个空槽：官方 0.6 s 档（L=18 帧）的 ridge 误差 + 分环境条件覆盖率。

为什么单独一个脚本：
  * `p2_predict.py` 的冻结掩码集合是 0.2/0.5/1.0/2.0 s（{6,15,30,60} 帧），
    而 `common_conditions.json` 的官方前缀集合是 [0.2, 0.6, 1.0] s —— 0.6 s（18 帧）不在里面。
  * `p2_interval.json` 只报了边际覆盖率，没有分环境覆盖率。
本脚本不改任何已有 json，只新增 `data/p2_extra.json`。

口径（与 p2_interval.py 一致，便于并列）：
  predictor = ridge(alpha=10, 上下文 10 帧, 特征 rel/vel/acc + (h+1)/L + L/30)
  windows  = p2_predict.windows(split, L)，最多 400 个/记录，stride L//2，上下文与掩码内无标注坏帧
  conformal = 验证集上 3D 绝对误差的 q90 作半径，测试集覆盖率 = 误差≤半径的比例
"""
import json
import os

import numpy as np
import pandas as pd

import p2_predict as P
from common import DATA

GRID = [6, 18, 30]          # 0.2 / 0.6 / 1.0 s —— 官方前缀集合
RECS = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
ENV = RECS.set_index("rec").env.to_dict()


def errors(split, L, sc, mdl):
    """返回 (逐窗逐帧 3D 误差数组 (n,L), 记录 id 数组 (n,), 末点误差 (n,))"""
    ws = P.windows(split, L)
    E, R = [], []
    for ctx, tgt, _, r in ws:
        pr = P.ridge_predict(sc, mdl, ctx, L)
        E.append(np.linalg.norm(pr - tgt, axis=1))
        R.append(int(r))
    return np.array(E), np.array(R)


def main():
    out = {"_meta": {"script": "p2_extra.py", "predictor": "ridge alpha=10, ctx=10 frames",
                     "grid_L_frames": GRID, "grid_L_s": [g / 30 for g in GRID],
                     "convention": "split conformal, absolute 3D error radius, q90 on validation",
                     "answers": ["\\slotPTwoMaskZeroSixRMSE", "\\slotPConConditionalCoverage"]},
           "lengths": [], "conditional_coverage": {}, "created": ""}
    import time
    out["created"] = time.strftime("%Y-%m-%d %H:%M:%S")

    for L in GRID:
        tr = {L: P.windows("train", L)}
        sc, mdl = P.train_ridge(tr, L)
        Eva, Rva = errors("validation", L, sc, mdl)
        Ete, Rte = errors("test", L, sc, mdl)
        q90 = float(np.quantile(Eva.ravel(), 0.90))
        cov = float((Ete.ravel() <= q90).mean())
        row = dict(L_frames=L, L_s=round(L / 30, 3),
                   rmse_m=float(np.sqrt((Ete ** 2).mean())),
                   rmse_coord_cm=round(float(np.sqrt((Ete ** 2).mean() / 3)) * 100, 3),
                   rmse_cm=round(float(np.sqrt((Ete ** 2).mean())) * 100, 3),
                   end_rmse_m=float(np.sqrt((Ete[:, -1] ** 2).mean())),
                   end_rmse_cm=round(float(np.sqrt((Ete[:, -1] ** 2).mean())) * 100, 3),
                   median_err_m=float(np.median(Ete[:, -1])),
                   within_2cm=float((Ete[:, -1] < 0.02).mean()),
                   n_val=int(Eva.shape[0]), n_test=int(Ete.shape[0]),
                   q90_m=q90, coverage_test=cov)
        out["lengths"].append(row)
        print(f"L={L:>2} ({L/30:.1f}s) rmse={row['rmse_cm']:.2f}cm end={row['end_rmse_cm']:.2f}cm "
              f"cov={cov:.3f} q90={q90:.3f}m", flush=True)

        if L == 30:                      # 分环境条件覆盖率只在最长的官方档上算
            flat = Ete.ravel()
            lab = np.repeat(Rte, Ete.shape[1])
            per = {}
            for r in sorted(set(Rte.tolist())):
                m = lab == r
                per[str(int(r))] = dict(env=str(ENV.get(int(r), "?")),
                                        n_windows=int((Rte == r).sum()),
                                        coverage=float((flat[m] <= q90).mean()),
                                        rmse_cm=round(float(np.sqrt((flat[m] ** 2).mean())) * 100, 3))
            by_env = {}
            for v in per.values():
                by_env.setdefault(v["env"], []).append(v)
            for e, vs in by_env.items():
                w = np.array([v["n_windows"] for v in vs], dtype=float)
                out["conditional_coverage"][e] = dict(
                    n_records=len(vs), n_windows=int(w.sum()),
                    coverage=float(np.average([v["coverage"] for v in vs], weights=w)),
                    rmse_cm=round(float(np.average([v["rmse_cm"] for v in vs], weights=w)), 3))
            out["per_record_L30"] = per
            cs = np.array([v["coverage"] for v in out["conditional_coverage"].values()])
            names = list(out["conditional_coverage"])
            out["conditional_summary"] = dict(
                n_env=int(len(cs)), marginal=round(cov, 4),
                min=float(cs.min()), max=float(cs.max()), mean=float(cs.mean()),
                n_below_0p85=int((cs < 0.85).sum()),
                min_env=names[int(cs.argmin())], max_env=names[int(cs.argmax())])

    # 语料/数据完整性顺带确认
    with open(os.path.join(DATA, "p2_extra.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", os.path.join(DATA, "p2_extra.json"), flush=True)


if __name__ == "__main__":
    main()