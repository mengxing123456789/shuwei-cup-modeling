# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成。相位可辨识性实验 v2：把「分离度」换成四种统计量再判。
# -*- coding: utf-8 -*-
"""v1 用 8 阶谱签名得到 spearman=0.089（无关系），但那个统计量可能太钝。
v2 在**同一批边界**上并列四种分离度，每一种都先写死判据，再一起算：

  spec8   归一化 6-NN 拉普拉斯最小 8 个非零特征值的均值差（v1 用的）
  pose63  21 关键点平均位置（63 维）的差
  speed   段均速度分布的差（4 个分位：均值/中位/q90/标准差）
  wrist   主导手腕平均位置的差

分母统一用 sqrt(½(σ_s²+σ_{s+1}²))，σ 为段内帧级离散（同样的空间）。
检出强度同时取 ±2 与 ±5 帧两种窗口，避免窗口太窄把「其实检出了」记成漏检。

判据（先写死）：命题成立 ⟺ 至少一种统计量的 Spearman ρ > 0.4（p<0.01）**且**
该统计量在中位数以上的边界检出率至少是中位数以下的两倍。
输出 data/phase_identifiability2.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import p1a_identifiability as K  # 复用签名与主函数里的数据加载方式

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def stats_of(block):
    mu = block.mean(0)
    sd = float(np.sqrt(((block - mu) ** 2).mean()))
    return mu, sd


def speed_profile(P):
    v = np.linalg.norm(np.diff(P, axis=0), axis=2).mean(1)
    if len(v) < 4:
        v = np.pad(v, (0, 4 - len(v)))
    return np.array([v.mean(), np.median(v), np.quantile(v, 0.9), v.std()])


def main():
    t0 = time.time()
    panel = np.load(D / "panel.npz")
    Lh, Rh, rec = panel["L"], panel["R"], panel["rec"]
    badL, badR = panel["badL"], panel["badR"]
    pn = pd.read_csv(D / "panel_records.csv").set_index("rec")
    segs = pd.read_csv(D / "segments.csv")
    probs = np.load(D / "p1a_gpu_segmentation_probs.npz")
    test_recs = sorted(int(r) for r in pn[pn.split == "test"].index)

    rows = []
    for r in test_recs:
        fps = float(pn.loc[r, "fps"])
        ii = np.where(rec == r)[0]
        useL = badL[ii].mean() <= badR[ii].mean()
        hands = (Lh if useL else Rh)[ii]
        n = len(ii)
        sig = np.array([K.spectral_signature(hands[k]) for k in range(n)])
        flat = hands.reshape(n, -1)
        wrist = hands[:, 0, :]
        pr = np.asarray(probs[f"rec{r}"], dtype=float)
        pr = pr[:n] if len(pr) >= n else np.pad(pr, (0, n - len(pr)), constant_values=np.nan)

        ss = segs[segs.rec == r].sort_values("seg")
        blocks = []
        for _, s in ss.iterrows():
            a = int(round(s.start * fps))
            b = int(round(s.end * fps))
            a, b = max(0, a), min(n, max(b, a + 2))
            blocks.append((a, b, s))

        for k in range(len(blocks) - 1):
            a0, b0, _s0 = blocks[k]
            a1, b1, s1 = blocks[k + 1]
            mu_spec0, sd_spec0 = stats_of(sig[a0:b0])
            mu_spec1, sd_spec1 = stats_of(sig[a1:b1])
            mu_pos0, sd_pos0 = stats_of(flat[a0:b0])
            mu_pos1, sd_pos1 = stats_of(flat[a1:b1])
            mu_w0, sd_w0 = stats_of(wrist[a0:b0])
            mu_w1, sd_w1 = stats_of(wrist[a1:b1])
            sp0, sp1 = speed_profile(hands[a0:b0]), speed_profile(hands[a1:b1])

            def sep(m0, m1, s0, s1):
                return float(np.linalg.norm(m1 - m0) / max(np.sqrt(0.5 * (s0 ** 2 + s1 ** 2)), 1e-9))

            d2 = float(np.nanmax(pr[max(0, a1 - 2):min(n, a1 + 3)])) if np.any(np.isfinite(pr[max(0, a1 - 2):min(n, a1 + 3)])) else float("nan")
            d5 = float(np.nanmax(pr[max(0, a1 - 5):min(n, a1 + 6)])) if np.any(np.isfinite(pr[max(0, a1 - 5):min(n, a1 + 6)])) else float("nan")
            rows.append(dict(rec=r, seg=int(s1.seg),
                             spec8=sep(mu_spec0, mu_spec1, sd_spec0, sd_spec1),
                             pose63=sep(mu_pos0, mu_pos1, sd_pos0, sd_pos1),
                             wrist=sep(mu_w0, mu_w1, sd_w0, sd_w1),
                             speed=sep(sp0, sp1, float(sp0.std() if sp0.std() > 1e-9 else 1e-9),
                                       float(sp1.std() if sp1.std() > 1e-9 else 1e-9)),
                             detect2=d2, detect5=d5))

    R = pd.DataFrame(rows)
    res = {}
    for stat in ("spec8", "pose63", "wrist", "speed"):
        for dw in ("detect2", "detect5"):
            x, y = R[stat].values, R[dw].values
            ok = np.isfinite(x) & np.isfinite(y)
            rho, p = spearmanr(x[ok], y[ok])
            med = float(np.median(x[ok]))
            lo = ok & (x <= med)
            hi = ok & (x > med)
            res[f"{stat}__{dw}"] = dict(
                spearman=float(rho), p=float(p), n=int(ok.sum()),
                rate_low=float((y[lo] >= 0.5).mean()), rate_high=float((y[hi] >= 0.5).mean()),
                median_stat=med,
            )
        print(f"{stat:7s} " + "  ".join(
            f"{dw}: rho={res[f'{stat}__{dw}']['spearman']:+.3f} p={res[f'{stat}__{dw}']['p']:.2g} "
            f"lo={res[f'{stat}__{dw}']['rate_low']:.2f} hi={res[f'{stat}__{dw}']['rate_high']:.2f}"
            for dw in ("detect2", "detect5")))

    best = max(res.items(), key=lambda kv: kv[1]["spearman"])
    holds = (best[1]["spearman"] > 0.4 and best[1]["p"] < 0.01
             and best[1]["rate_high"] >= 2 * max(best[1]["rate_low"], 1e-9))
    summary = dict(
        max_abs_spearman=float(max(abs(v["spearman"]) for v in res.values())),
        min_p=float(min(v["p"] for v in res.values())),
        n_boundaries=int(len(R)),
        rate_low_min=float(min(v["rate_low"] for v in res.values())),
        rate_high_max=float(max(v["rate_high"] for v in res.values())),
    )
    out = dict(
        _meta=dict(script="p1a_identifiability.py (v2)",
                   criterion="proposition holds iff some statistic has rho>0.4, p<0.01 and rate_high >= 2*rate_low",
                   n_boundaries=int(len(R)), test_records=test_recs,
                   note="v1 used spec8 with a +-2 window only; v2 puts four statistics side by side"),
        table=res, best=best[0], proposition_holds=bool(holds),
        per_boundary=R.to_dict(orient="records"), summary=summary,
        seconds=round(time.time() - t0, 1), created=time.strftime("%Y-%m-%d %H:%M:%S"))
    (D / "phase_identifiability2.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"best={best[0]}  proposition_holds={holds}")
    print(f"written phase_identifiability2.json ({out['seconds']} s)")


if __name__ == "__main__":
    main()