
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""把重跑后的 P3 结果压成几张表：名义映射、配对差、再观测敏感性。"""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA = os.path.abspath(DATA)
d = json.load(open(os.path.join(DATA, "p3_scheduling.json"), encoding="utf-8"))

print("=" * 84)
print("A 名义映射 alpha=1.0 beta=0.5 —— 与 0.50 门槛对照（30 个官方种子）")
print("=" * 84)
print(f"{'case':4s} {'policy':8s} {'on-time':>9s} {'complet':>9s} {'cost':>7s} {'reviews':>8s} {'idle s':>8s} {'tard s':>8s}")
for r in d["summary"]:
    if abs(r["alpha"] - 1.0) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9:
        print(f"{r['case']:4s} {r['policy']:8s} {r['weighted_on_time_rate']:>9.4f} "
              f"{r['weighted_completion_rate']:>9.4f} {r['cost']:>7.2f} "
              f"{r['reviews']:>8.2f} {r['reserved_idle_s']:>8.2f} {r['weighted_tardiness_s']:>8.2f}")

print()
print("=" * 84)
print("B 与 EDF 的配对差（同种子），名义映射")
print("=" * 84)
for r in d["paired_vs_edf"]:
    if abs(r["alpha"] - 1.0) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9:
        print(f"  {r['case']}  {r['policy']:8s}  diff={r['mean_diff']:+.4f}  "
              f"±{r['ci95']:.4f}  {'显著' if abs(r['mean_diff']) > r['ci95'] else '不显著'}")

print()
print("=" * 84)
print("C 再观测：VoI 门槛敏感性（edf_rev，10 种子）")
print("=" * 84)
print(f"{'case':4s} {'bar':>6s} {'reviews':>8s} {'on-time':>9s} {'cost':>7s} {'idle s':>8s}")
for r in d["review_bar_sensitivity"]:
    print(f"{r['case']:4s} {r['review_bar']:>6.2f} {r['reviews']:>8.2f} "
          f"{r['eta']:>9.4f} {r['cost']:>7.2f} {r['idle']:>8.2f}")

print()
print("=" * 84)
print("D 前缀信息量：同一单元在不同前缀档的绝对误差（配对）")
print("=" * 84)
print("  见 duration_model：", {k: (round(v["mae"], 3), round(v["spearman"], 3))
                              for k, v in d["duration_model"].items()})
print("  残差分位：", d["residuals"])
print("  voi:", json.dumps(d["_meta"].get("review_voi", {}), ensure_ascii=False))