
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""把 best_p1a.json / best_p1a_k.json 汇总成任务要求的 data/audit_p1a_*.json 对照表，
并顺手校验报告里引用的键都真实存在（缺键即抛错，不写文件）。"""
import json
import os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def load(n):
    with open(os.path.join(D, n), encoding="utf-8") as f:
        return json.load(f)


a = load("best_p1a.json")
k = load("best_p1a_k.json")
base = load("p1_segmentation.json")

BASE_ARI = 0.4138423666260523
rows = []
for tag, m in a["methods"].items():
    mean = m["mean"]
    rows.append(dict(candidate=tag, ran=True, ari=mean["ari"], f1=mean["f1"],
                     b_mae_s=mean["b_mae"], n_seg=mean["n_seg"],
                     delta_ari=mean["ari"] - BASE_ARI,
                     source="data/best_p1a.json:methods.%s.mean" % tag))
sweep = []
for r in k["kmax_sweep"]:
    sweep.append(r)
out = dict(
    _meta=dict(
        purpose="P1-a 候选 vs 现基线（Ward+头部特征 ARI 0.4138）的机器可读对照表",
        protocol="与 code/p1_model.py 同 7 条测试记录、同 ARI/F1/边界口径；官方题面未规定状态标签与分割指标",
        baseline_source="data/p1_segmentation.json (ward) ARI=0.4138423666260523 F1=0.5613169824306583",
        oracle_k_ceiling="data/p1_segmentation.json ward_oracleK ARI=0.5994（K 给真值时的上界）",
        recommendation="kmax=20（ARI 0.5380 / F1 0.6075，过分割较少）；追求 ARI 上限用 kmax=25（0.5387）",
        negative_results=["hmm 系列：无停留时间先验导致逐帧切换（n_seg 64.7–152.4）",
                          "ae_ward：自监督重构表征只带来 +0.0123 ARI",
                          "相邻段质心合并：55 条训练记录上所有参数组合一次都未触发，测试指标逐位不变"],
        not_run=["时空图网络（ST-GCN 类）：无状态标签、仅 7 条可评记录，未跑"]),
    baseline_ari=BASE_ARI, candidates=rows, k_sweep=sweep,
    best=dict(candidate="ward_k25", ari=a["methods"]["ward_k25"]["mean"]["ari"],
              delta_ari=a["methods"]["ward_k25"]["mean"]["ari"] - BASE_ARI))

# 校验：报告引用的其它文件键必须存在
b = load("best_p1b.json")
for arm in ("A_exact_replica", "B_std_only", "C_aug_longer"):
    for key in ("test_auc", "test_ap", "brier", "brier_iso", "ece15", "ece15_iso",
                "temperature", "per_env_test", "risk_coverage"):
        assert key in b["arms"][arm], (arm, key)
q = load("best_p2q.json")
assert len(q["rows"]) == 4
for r in q["rows"]:
    for key in ("rmse_m", "median_err_m", "q90_err_m", "within_2cm",
                "coverage90_mean", "width90_mean_cm"):
        assert key in r["horizons"][-1], key
s = load("best_p3_sens.json")
assert len(s["sensitivity"]) == 23 and "paired_vs_default" in s
c = load("best_p3_combo.json")
assert len(c["combos"]) == 4 and "paired_vs_default" in c

p = os.path.join(D, "audit_p1a_best.json")
with open(p, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("k_sweep entries:", len(sweep))
print("candidates:", len(rows))
print("best:", out["best"])
print("all cited keys verified; saved ->", p)