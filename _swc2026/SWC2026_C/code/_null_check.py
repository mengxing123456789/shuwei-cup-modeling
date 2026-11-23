# AI 辅助：DeepSeek Harness 助手生成的零假设对照：真边界处的峰是否真的比对随便一帧更强。
# -*- coding: utf-8 -*-
"""分离度不解释检出，剩两种可能：(a) 真边界处根本没峰；(b) 到处都有峰（检测器处处说"是"）。
这里用零分布把它分开：在同一记录里随机抽非边界帧，取 ±2/±5 帧内的最大概率作对照，
再算 AUC(真边界, 随机帧)。AUC≈0.5 = 盲；AUC 明显 >0.5 但有峰也一堆 = 噪声。
输出 data/phase_null_check.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
RNG = np.random.default_rng(20261120)
NPOS = 250


def main():
    t0 = time.time()
    panel = np.load(D / "panel.npz")
    rec = panel["rec"]
    pn = pd.read_csv(D / "panel_records.csv").set_index("rec")
    segs = pd.read_csv(D / "segments.csv")
    probs = np.load(D / "p1a_gpu_segmentation_probs.npz")
    test_recs = sorted(int(r) for r in pn[pn.split == "test"].index)

    pos, neg = [], []
    per = {}
    for r in test_recs:
        fps = float(pn.loc[r, "fps"])
        n = int(np.sum(rec == r))
        pr = np.asarray(probs[f"rec{r}"], dtype=float)[:n]
        bounds = np.array([int(round(s.start * fps)) for _, s in segs[segs.rec == r].iterrows()
                           if int(round(s.start * fps)) > 5], dtype=int)

        def peak(fr, half):
            w = pr[max(0, fr - half):min(n, fr + half + 1)]
            return float(np.nanmax(w)) if len(w) and np.any(np.isfinite(w)) else float("nan")

        for b in bounds:
            pos.append((peak(b, 2), peak(b, 5), r))
        far = np.setdiff1d(np.arange(5, n - 5),
                           np.concatenate([np.arange(max(0, b - 5), min(n, b + 6)) for b in bounds]))
        if len(far) > NPOS:
            far = RNG.choice(far, NPOS, replace=False)
        for f in far:
            neg.append((peak(f, 2), peak(f, 5), r))
        per[str(r)] = dict(n_true=int(len(bounds)), n_null=int(len(far)))

    pos = pd.DataFrame(pos, columns=["p2", "p5", "rec"])
    neg = pd.DataFrame(neg, columns=["p2", "p5", "rec"])
    vp2, vn2 = pos.p2.dropna().tolist(), neg.p2.dropna().tolist()
    auc2 = float(roc_auc_score([1] * len(vp2) + [0] * len(vn2), vp2 + vn2))
    vp5, vn5 = pos.p5.dropna().tolist(), neg.p5.dropna().tolist()
    auc5 = float(roc_auc_score([1] * len(vp5) + [0] * len(vn5), vp5 + vn5))

    out = dict(
        _meta=dict(script="_null_check.py",
                   design="true boundaries vs random non-boundary frames of the same records; "
                          "statistic = max boundary probability within +-2 / +-5 frames",
                   nulls_per_record=NPOS, seed=20261120, test_records=test_recs),
        auc_at_2_frames=auc2, auc_at_5_frames=auc5,
        mean_pos_p2=float(pos.p2.mean()), mean_neg_p2=float(neg.p2.mean()),
        mean_pos_p5=float(pos.p5.mean()), mean_neg_p5=float(neg.p5.mean()),
        share_pos_ge_half_p2=float((pos.p2 >= 0.5).mean()),
        share_neg_ge_half_p2=float((neg.p2 >= 0.5).mean()),
        per_record=per,
        seconds=round(time.time() - t0, 1), created=time.strftime("%Y-%m-%d %H:%M:%S"))
    (D / "phase_null_check.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"AUC(+-2)={auc2:.3f}  AUC(+-5)={auc5:.3f}")
    print(f"true: mean={pos.p2.mean():.3f} share>=0.5={out['share_pos_ge_half_p2']:.3f}")
    print(f"null: mean={neg.p2.mean():.3f} share>=0.5={out['share_neg_ge_half_p2']:.3f}")


if __name__ == "__main__":
    main()