# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C
import pandas as pd, numpy as np
g = C.load_ghcn_wide(C.RESULTS / "ghcn" / "CHM00057083.csv")
gd = C.daily_grid(g[["date", "prcp_mm", "tmax_c", "tmin_c"]])
print("GHCN range", gd.index.min(), gd.index.max(), "missing%", round(gd.prcp_mm.isna().mean()*100,2))
print("GHCN top10 daily:")
print(gd.prcp_mm.nlargest(10).to_string())
print("GHCN July 2021:")
print(gd.loc["2021-07-17":"2021-07-23", "prcp_mm"].to_string())
a = C.load_gsod_workbook(C.PROBLEM / "2021_“ShuWei Cup”B_Problem" / "Attachment 1：Data of three meteorological stations in zhengzhou annex.xlsx")
ad = C.daily_grid(a[a.station=="57083099999"][["date","prcp_mm"]])
print("GSOD top10 daily:")
print(ad.prcp_mm.nlargest(10).to_string())
print("GSOD July 2021:")
print(ad.loc["2021-07-17":"2021-07-23", "prcp_mm"].to_string())
print("GSOD 2021 sum Jan-Nov5:", round(float(ad.loc["2021-01-01":"2021-11-05","prcp_mm"].sum()),1))
print("GHCN 2021 sum Jan-Nov5:", round(float(gd.loc["2021-01-01":"2021-11-05","prcp_mm"].sum()),1))