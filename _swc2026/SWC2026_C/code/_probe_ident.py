# AI 辅助：DeepSeek Harness 助手生成的一次性数据探针（相位可辨识性实验的输入对齐）。
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"

seg = pd.read_csv(D / "segments.csv")
print("segments.csv", seg.shape, list(seg.columns))
print(seg.head(3).to_string())
print("records in segments:", seg.rec.nunique(), "segments:", len(seg))
print("rec37 rows:", len(seg[seg.rec == 37]) if (seg.rec == 37).any() else "none")

p = np.load(D / "panel.npz")
print("panel keys:", list(p.keys()))
for k in p.files[:8]:
    print("  ", k, p[k].shape, p[k].dtype)

b = np.load(D / "p1a_gpu_segmentation_probs.npz")
print("boundary probs keys:", list(b.keys()))
for k in b.files:
    print("  ", k, b[k].shape, b[k].dtype)

pn = pd.read_csv(D / "panel_records.csv")
print("panel_records", pn.shape, list(pn.columns)[:12])
print(pn[pn.rec == 37].to_string() if (pn.rec == 37).any() else "no rec37 in panel_records")