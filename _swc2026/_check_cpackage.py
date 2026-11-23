# -*- coding: utf-8 -*-
"""核对交付包：三个 zip 的条目构成 + 题面引用的 6 个文件是否存在。"""
import os
import zipfile
from collections import Counter

ROOT = (r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data"
        r"\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN")
ATT = os.path.join(ROOT, "Restocking_Tasks_and_Constraints")

print("=== 三个 zip 的条目构成 ===")
for z in ("EgoDemo.zip", "EgoPro.zip", "EgoStandard.zip"):
    p = os.path.join(ROOT, "Raw_Data", z)
    with zipfile.ZipFile(p) as zf:
        names = zf.namelist()
        ext = Counter(os.path.splitext(n)[1].lower() for n in names if not n.endswith("/"))
        sizes = sum(i.file_size for i in zf.infolist())
        print(f"  {z}: 压缩 {os.path.getsize(p)/1e9:.3f} GB, 解压 {sizes/1e9:.3f} GB, "
              f"{len([n for n in names if not n.endswith('/')])} 个文件, {dict(ext)}")

print()
print("=== 题面引用的文件是否存在 ===")
want = [
    ("Data_Documentation/record_index.csv", os.path.join(ROOT, "Data_Documentation", "record_index.csv")),
    ("Data_Documentation/record_split.csv", os.path.join(ROOT, "Data_Documentation", "record_split.csv")),
    ("Data_Documentation/attachment_guide.md", os.path.join(ROOT, "Data_Documentation", "attachment_guide.md")),
    ("Data_Documentation/missing_observation_experiments.md", os.path.join(ROOT, "Data_Documentation", "missing_observation_experiments.md")),
    ("file_manifest.csv (包根)", os.path.join(ROOT, "file_manifest.csv")),
    ("Restocking_Tasks_and_Constraints/tasks_and_evaluation.md", os.path.join(ATT, "tasks_and_evaluation.md")),
]
for label, p in want:
    print(f"  {'有' if os.path.exists(p) else '缺'}  {label}")

print()
print("=== 实际交付的 6 个约束文件里都有什么列 ===")
import csv
for name in ("source_segment_index.csv", "record_split.csv", "tasks.csv",
             "service_zones.csv", "job_families.csv"):
    p = os.path.join(ATT, name)
    with open(p, encoding="utf-8-sig") as f:
        r = csv.reader(f)
        head = next(r)
        n = sum(1 for _ in r)
    print(f"  {name}: {n} 行, 列={head}")

import json
with open(os.path.join(ATT, "common_conditions.json"), encoding="utf-8") as f:
    cc = json.load(f)
print(f"  common_conditions.json: 顶层键={list(cc.keys())}")