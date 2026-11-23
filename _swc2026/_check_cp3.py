# -*- coding: utf-8 -*-
"""把 C 题 P3 的关键汇总数拉齐：三案例 under nominal mapping 的 on-time / 完成率 / 成本。"""
import json
import os

BASE = r"E:\数学建模\_swc2026\SWC2026_C\data"
with open(os.path.join(BASE, "p3_scheduling.json"), encoding="utf-8") as f:
    d = json.load(f)

print("=== constraint_nominal（全量）===")
for r in d["constraint_nominal"]:
    print(f"  {r}")

print()
print("=== summary 中 alpha=1.0,beta=0.0（名义映射）各案例各策略 ===")
seen = set()
for r in d["summary"]:
    key = (r["case"], r["alpha"], r["beta"], r["policy"])
    if key in seen:
        continue
    seen.add(key)
    if abs(r["alpha"] - 1.0) < 1e-9 and abs(r["beta"]) < 1e-9:
        print(
            f"  {r['case']:3s} {r['policy']:6s} "
            f"completion={r['weighted_completion_rate']:.4f} "
            f"on_time={r['weighted_on_time_rate']:.4f} "
            f"cost={r['cost']:.2f} reviews={r['reviews']:.2f} "
            f"tardiness={r['weighted_tardiness_s']:.2f}"
        )

print()
print("=== alpha=0.75,beta=0.5（另一映射）===")
for r in d["summary"]:
    if abs(r["alpha"] - 0.75) < 1e-9 and abs(r["beta"] - 0.5) < 1e-9:
        print(
            f"  {r['case']:3s} {r['policy']:6s} "
            f"completion={r['weighted_completion_rate']:.4f} "
            f"on_time={r['weighted_on_time_rate']:.4f} cost={r['cost']:.2f}"
        )