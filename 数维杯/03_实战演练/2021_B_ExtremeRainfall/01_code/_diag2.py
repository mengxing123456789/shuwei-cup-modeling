# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C
import pandas as pd
print("load attach", flush=True)
raw = C.load_gsod_workbook(C.PROBLEM / "2021_“ShuWei Cup”B_Problem" / "Attachment 1：Data of three meteorological stations in zhengzhou annex.xlsx")
print("attach ok", raw.shape, flush=True)
att = raw[raw.station == "57083099999"]
print("filter ok", len(att), flush=True)
att_d = C.daily_grid(att[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "gsod"})
print("grid ok", att_d.shape, att_d.index.min(), att_d.index.max(), flush=True)
gh_path = C.RESULTS / "ghcn" / "CHM00057083.csv"
gh = C.load_ghcn_wide(gh_path)
print("ghcn ok", gh.shape, flush=True)
gh_d = C.daily_grid(gh[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "ghcn"})
print("ghcn grid ok", gh_d.shape, flush=True)
both = att_d.join(gh_d, how="inner").dropna()
print("join ok", both.shape, flush=True)
both = both[(both.index >= "1961-01-01") & (both.index <= "2021-11-30")]
print("slice ok", both.shape, flush=True)
print("corr", both["gsod"].corr(both["ghcn"]), flush=True)
g1 = both.groupby(both.index.year)["gsod"].sum()
g2 = both.groupby(both.index.year)["ghcn"].sum()
print("annual corr", g1.corr(g2), flush=True)
print("done", flush=True)