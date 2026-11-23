import pandas as pd, glob, pathlib
R = pathlib.Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\03_results")
sel = pd.read_csv(R/"q5_selective_protection.csv")
print("== best hotspot per city/h/m ==")
best = sel.sort_values("bcr", ascending=False).groupby(["city","hotspot_share","damage_multiplier"]).head(1)
print(best.sort_values("bcr", ascending=False)[["city","hotspot_share","damage_multiplier","storage_mm","bcr"]].head(12).to_string(index=False))
print("\n== max per city ==")
print(sel.sort_values("bcr", ascending=False).groupby("city").head(1)[["city","hotspot_share","damage_multiplier","storage_mm","bcr"]].to_string(index=False))
reg = R/"q2_region_summary.csv"
if reg.exists():
    print("\n== regions =="); print(pd.read_csv(reg).to_string(index=False))
ghcn = sorted((R/"ghcn").glob("CHM*.csv")); print("\nghcn files:", len(ghcn))
aud = pd.read_csv(R/"audit_ghcn_stations.csv"); print("audit rows:", len(aud)); print(list(aud.columns)[:10])
