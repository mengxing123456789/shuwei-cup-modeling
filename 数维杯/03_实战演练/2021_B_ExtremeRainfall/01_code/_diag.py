# -*- coding: utf-8 -*-
import sys, time, traceback
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
print("step0 start", flush=True)
import common as C
print("import ok", flush=True)
p = C.PROBLEM / "2021_“ShuWei Cup”B_Problem" / "Attachment 1：Data of three meteorological stations in zhengzhou annex.xlsx"
print("exists", p.exists(), flush=True)
df = C.load_gsod_workbook(p)
print("gsod", df.shape, flush=True)
for name in ["CHM00057083", "CHM00053959", "CHM00054511"]:
    q = C.RESULTS / "ghcn" / f"{name}.csv"
    g = C.load_ghcn_wide(q)
    print(name, g.shape, g["name"].iloc[0], flush=True)
print("done", flush=True)