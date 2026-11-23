# -*- coding: utf-8 -*-
"""汇总 C 题三个问题的已有结果，并检查成稿状态。"""
import json
import os

BASE = r"E:\数学建模\_swc2026\SWC2026_C"


def brief(name, keys=None, maxlen=900):
    p = os.path.join(BASE, "data", name)
    if not os.path.exists(p):
        print(f"--- {name}: 缺失")
        return
    if name.endswith(".json"):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        print(f"--- {name} ---")
        if isinstance(d, dict):
            for k, v in d.items():
                s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                print(f"  {k}: {s[:maxlen]}")
        else:
            print("  ", json.dumps(d, ensure_ascii=False)[:maxlen])
    print()


for n in ("p1_segmentation.json", "p1_reliability.json", "p1_state_summary.json",
          "p2_prediction.json", "p2_crossover.json", "p2_interval.json"):
    brief(n)

print("=== p3_scheduling.json 顶层 ===")
p = os.path.join(BASE, "data", "p3_scheduling.json")
with open(p, encoding="utf-8") as f:
    d3 = json.load(f)
if isinstance(d3, dict):
    for k, v in d3.items():
        s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        print(f"  {k}: {s[:600]}")
print()

print("=== 成稿状态 ===")
for f in ("main.tex", "main.pdf"):
    fp = os.path.join(BASE, f)
    print(f"  {f}: {'有' if os.path.exists(fp) else '缺'}  {os.path.getsize(fp) if os.path.exists(fp) else ''}")

print()
print("=== code 目录 ===")
cd = os.path.join(BASE, "code")
for f in sorted(os.listdir(cd)):
    print(f"  {f}  {os.path.getsize(os.path.join(cd,f)):,} B")

print()
print("=== figures 目录 ===")
fg = os.path.join(BASE, "figures")
for f in sorted(os.listdir(fg)):
    print(f"  {f}  {os.path.getsize(os.path.join(fg,f)):,} B")