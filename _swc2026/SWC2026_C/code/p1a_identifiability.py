# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成。相位可辨识性实验（08 纲领 §8.2 的命题 1）。
# -*- coding: utf-8 -*-
"""阶段是否真的可由单帧姿态辨识？

命题：一个阶段边界只有在两侧姿态的**谱分离度**超过某个阈值时才可辨识；低于该阈值，
任何检测器给出的峰都是噪声。

做法（不引入新数据，全部来自既有面板与既有检测器输出）：

1. 每帧用主导手的 21 个关键点建 k 近邻图（高斯核，带宽 = 该帧距离中位数，故图对
   平移/旋转不变、对整体缩放近似不变），取归一化拉普拉斯的最小 8 个非零特征值作
   **谱签名** φ(t)∈R^8。
2. 逐段取签名均值 μ_s 与段内 RMS 离散 σ_s，定义相邻段的**分离度**
       sep = ||μ_{s+1} − μ_s|| / sqrt(½(σ_s² + σ_{s+1}²))
   与**段内漂移**
       drift = ||μ_(后半段) − μ_(前半段)|| / σ_s
3. 检出强度取 `p1a_gpu_segmentation_probs.npz` 在真边界帧 ±2 帧内的最大概率。
4. 判据（先写死，再算）：
   - 命题成立 ⟺ Spearman(sep, detect) > 0.4 且 sep 低于中位数的边界检出率 ≤ 50%；
   - 过分割的解释 ⟺ 存在记录 drift > 平均 sep（段内漂移大于段间分离）。
输出 data/phase_identifiability.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"

KNN = 6
NSPEC = 8


def spectral_signature(P: np.ndarray) -> np.ndarray:
    """P: (21,3) keypoints -> 8 smallest non-trivial eigenvalues of the normalised Laplacian."""
    d = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    sigma = np.median(d[d > 0]) if np.any(d > 0) else 1.0
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = 1.0
    A = np.exp(-(d ** 2) / (2 * sigma ** 2))
    np.fill_diagonal(A, 0.0)
    # keep the k nearest neighbours, symmetrised
    for i in range(len(P)):
        idx = np.argsort(-A[i])[KNN:]
        A[i, idx] = 0.0
    A = np.maximum(A, A.T)
    deg = A.sum(1)
    deg[deg <= 0] = 1e-9
    Dm = 1.0 / np.sqrt(deg)
    Lsym = np.eye(len(P)) - (A * Dm[:, None]) * Dm[None, :]
    w = np.linalg.eigvalsh(Lsym)
    return np.sort(w)[1:NSPEC + 1]


def main():
    t0 = time.time()
    panel = np.load(D / "panel.npz")
    Lh, Rh = panel["L"], panel["R"]
    rec = panel["rec"]
    badL, badR = panel["badL"], panel["badR"]
    pn = pd.read_csv(D / "panel_records.csv").set_index("rec")
    segs = pd.read_csv(D / "segments.csv")
    probs = np.load(D / "p1a_gpu_segmentation_probs.npz")

    test_recs = sorted(int(r) for r in pn[pn.split == "test"].index)
    out_records = {}
    pairs = []          # (sep, detect, record, seg)
    drifts = []         # (drift, record, seg)

    for r in test_recs:
        fps = float(pn.loc[r, "fps"])
        ii = np.where(rec == r)[0]
        useL = badL[ii].mean() <= badR[ii].mean()
        hands = (Lh if useL else Rh)[ii]
        n = len(ii)
        sig = np.array([spectral_signature(hands[k]) for k in range(n)])
        pr = np.asarray(probs[f"rec{r}"], dtype=float)
        pr = pr[:n] if len(pr) >= n else np.pad(pr, (0, n - len(pr)), constant_values=np.nan)

        rows = segs[segs.rec == r].sort_values("seg")
        seg_stats = []
        for _, s in rows.iterrows():
            a, b = int(round(s.start * fps)), int(round(s.end * fps))
            a, b = max(0, a), min(n, max(b, a + 2))
            block = sig[a:b]
            mu = block.mean(0)
            sd = float(np.sqrt(((block - mu) ** 2).mean()))
            half = max(1, (b - a) // 2)
            mu1 = sig[a:a + half].mean(0)
            mu2 = sig[a + half:b].mean(0)
            drift = float(np.linalg.norm(mu2 - mu1) / max(sd, 1e-9))
            seg_stats.append(dict(seg=int(s.seg), start=float(s.start), end=float(s.end),
                                  dur=float(s.dur), mu=mu, sd=sd, drift=drift,
                                  bframe=a, label=str(s.label)[:60]))
            drifts.append((drift, r, int(s.seg)))

        for k in range(len(seg_stats) - 1):
            s0, s1 = seg_stats[k], seg_stats[k + 1]
            sep = float(np.linalg.norm(s1["mu"] - s0["mu"])
                        / max(np.sqrt(0.5 * (s0["sd"] ** 2 + s1["sd"] ** 2)), 1e-9))
            bf = s1["bframe"]
            win = pr[max(0, bf - 2):min(n, bf + 3)]
            det = float(np.nanmax(win)) if len(win) and np.any(np.isfinite(win)) else float("nan")
            pairs.append(dict(sep=sep, detect=det, rec=r, seg=int(s1["seg"])))
            seg_stats[k]["sep_to_next"] = sep
            seg_stats[k]["detect_next"] = det

        sp = [s for s in seg_stats]
        out_records[str(r)] = dict(
            fps=fps, n_frames=n, hand="left" if useL else "right",
            n_segments=len(sp),
            mean_drift=float(np.mean([s["drift"] for s in sp])),
            mean_sep=float(np.mean([s["sep_to_next"] for s in sp if "sep_to_next" in s])) if len(sp) > 1 else None,
            segments=[{k: v for k, v in s.items() if k not in ("mu",)} for s in sp],
        )

    sep = np.array([p["sep"] for p in pairs], float)
    det = np.array([p["detect"] for p in pairs], float)
    ok = np.isfinite(sep) & np.isfinite(det)
    rho, pval = spearmanr(sep[ok], det[ok])

    med = float(np.median(sep[ok]))
    lo = ok & (sep <= med)
    hi = ok & (sep > med)
    rate_lo = float((det[lo] >= 0.5).mean()) if lo.any() else float("nan")
    rate_hi = float((det[hi] >= 0.5).mean()) if hi.any() else float("nan")

    # threshold where the detection rate crosses one half, by binned crossing
    order = np.argsort(sep[ok])
    s_sorted, d_sorted = sep[ok][order], (det[ok] >= 0.5)[order]
    eps = float("nan")
    for k in range(1, len(s_sorted)):
        left = d_sorted[:k].mean()
        right = d_sorted[k:].mean()
        if left <= 0.5 < right:
            eps = float(0.5 * (s_sorted[k - 1] + s_sorted[k]))
            break

    # over-segmentation: within-segment drift versus between-segment separation
    dr = np.array([d for d, _r, _s in drifts], float)
    out_records_os = {k: dict(mean_drift=v["mean_drift"], mean_sep=v["mean_sep"],
                              n_segments=v["n_segments"]) for k, v in out_records.items()}
    overseg = {k: bool(v["mean_sep"] is not None and v["mean_drift"] > v["mean_sep"])
               for k, v in out_records_os.items()}

    rec37 = out_records_os.get("37", {})
    others = [v for k, v in out_records_os.items() if k != "37" and v["mean_sep"] is not None]

    out = {
        "_meta": {
            "script": "p1a_identifiability.py",
            "question": "is a stage boundary identifiable from single-frame pose at all?",
            "criterion_frozen_before_run": {
                "proposition_holds": "spearman(sep, detect) > 0.4 and detection rate in the low-separation half <= 0.5",
                "oversegmentation_explained": "within-segment drift > between-segment separation on that record",
            },
            "signature": f"{NSPEC} smallest non-trivial eigenvalues of the normalised {KNN}-NN Laplacian",
            "sep_definition": "||mu_next - mu|| / sqrt(0.5*(sd^2+sd_next^2))",
            "drift_definition": "||mu_secondhalf - mu_firsthalf|| / sd",
            "detect_definition": "max boundary probability within +-2 frames of the true boundary",
            "test_records": test_recs,
        },
        "pairs": pairs,
        "summary": {
            "n_boundaries": int(ok.sum()),
            "spearman_rho": float(rho), "spearman_p": float(pval),
            "sep_median": med,
            "detect_rate_low_half": rate_lo, "detect_rate_high_half": rate_hi,
            "epsilon_at_half_detection": eps,
            "mean_detect": float(np.nanmean(det[ok])),
        },
        "records": out_records_os,
        "oversegmentation": overseg,
        "rec37_vs_others": {
            "rec37_mean_drift": rec37.get("mean_drift"),
            "rec37_mean_sep": rec37.get("mean_sep"),
            "others_mean_drift": float(np.mean([v["mean_drift"] for v in others])) if others else None,
            "others_mean_sep": float(np.mean([v["mean_sep"] for v in others])) if others else None,
        },
        "seconds": round(time.time() - t0, 1),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (D / "phase_identifiability.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"boundaries={int(ok.sum())}  spearman={rho:.3f} (p={pval:.2g})")
    print(f"sep median={med:.3f}  detect>=0.5: low half={rate_lo:.2f} high half={rate_hi:.2f}")
    print(f"epsilon at half detection={eps:.3f}")
    print("rec37 drift/sep:", rec37.get("mean_drift"), rec37.get("mean_sep"))
    print("oversegmented records:", [k for k, v in overseg.items() if v])
    print(f"written phase_identifiability.json ({out['seconds']} s)")


if __name__ == "__main__":
    main()