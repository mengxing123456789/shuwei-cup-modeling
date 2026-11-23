# -*- coding: utf-8 -*-
"""核对 C 题数据：panel.npz / state.npz 的形状，以及 cdata 原始包的文件清单。"""
import collections
import json
import os

import numpy as np

BASE = r"E:\数学建模\_swc2026\SWC2026_C\data"
RAW = r"E:\数学建模\_swc2026\cdata"

for name in ("panel.npz", "state.npz"):
    path = os.path.join(BASE, name)
    print(f"=== {name}  ({os.path.getsize(path)/1e6:.1f} MB) ===")
    z = np.load(path)
    for k in z.keys():
        a = z[k]
        print(f"  {k}: shape={a.shape} dtype={a.dtype}")
    print()

print("=== cdata 原始包清单 ===")
for ds in sorted(os.listdir(RAW)):
    d = os.path.join(RAW, ds)
    if not os.path.isdir(d):
        continue
    ext = collections.Counter()
    n = 0
    total = 0
    for base, _, files in os.walk(d):
        for f in files:
            n += 1
            total += os.path.getsize(os.path.join(base, f))
            ext[os.path.splitext(f)[1].lower()] += 1
    print(f"{ds}: {n} files, {total/1e9:.3f} GB, {dict(ext)}")

print()
print("=== panel_records.csv 前 3 行 + 行数 ===")
p = os.path.join(BASE, "panel_records.csv")
with open(p, encoding="utf-8") as f:
    lines = f.read().splitlines()
print(f"rows(incl header)={len(lines)}")
for ln in lines[:3]:
    print(" ", ln[:160])