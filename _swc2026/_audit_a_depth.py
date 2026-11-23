# -*- coding: utf-8 -*-
"""审 A 题模型的实际深度：脚本行数、函数清单、方程出处。"""
import os
import re

BASE = r"E:\数学建模\_swc2026\SWC2026_A\code"

print("=== code 文件与行数 ===")
rows = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith(".py"):
        continue
    p = os.path.join(BASE, f)
    with open(p, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    rows.append((f, len(lines), len(code_lines)))
    print(f"  {f:28s} total={len(lines):5d}  code={len(code_lines):5d}")
print(f"  合计 code 行 = {sum(r[2] for r in rows)}")

print()
print("=== 每个脚本的 def/class 清单 ===")
for f, _, _ in rows:
    p = os.path.join(BASE, f)
    with open(p, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    defs = re.findall(r"^(?:def|class)\s+(\w+)", src, re.M)
    print(f"  {f}: {defs}")

print()
print("=== p1_mechanistic.py 头部 40 行 ===")
p = os.path.join(BASE, "p1_mechanistic.py")
with open(p, encoding="utf-8", errors="replace") as fh:
    for i, l in enumerate(fh.read().splitlines()[:40], 1):
        print(f"{i:3d}| {l}")