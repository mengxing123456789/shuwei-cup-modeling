# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C
import numpy as np, pandas as pd
raw = C.load_gsod_workbook(C.PROBLEM / "2021_“ShuWei Cup”B_Problem" / "Attachment 1：Data of three meteorological stations in zhengzhou annex.xlsx")
att = raw[raw.station == "57083099999"]
att_d = C.daily_grid(att[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "gsod"})
gh_d = C.daily_grid(C.load_ghcn_wide(C.RESULTS / "ghcn" / "CHM00057083.csv")[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "ghcn"})
both = att_d.join(gh_d, how="inner").dropna()
both = both[(both.index >= "1961-01-01") & (both.index <= "2021-11-30")]
print(both.dtypes.to_dict(), flush=True)
a = both["gsod"].to_numpy(dtype=np.float64)
b = both["ghcn"].to_numpy(dtype=np.float64)
print(a[:5], b[:5], flush=True)
print("np.corrcoef...", flush=True)
print(np.corrcoef(a, b), flush=True)
print("manual...", flush=True)
am, bm = a.mean(), b.mean()
num = ((a-am)*(b-bm)).sum()
den = np.sqrt(((a-am)**2).sum() * ((b-bm)**2).sum())
print(num/den, flush=True)