import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C, pandas as pd
files = sorted((C.RESULTS/"ghcn").glob("CHM*.csv"))
print("ghcn files:", len(files))
q2 = pd.read_csv(C.RESULTS/"q2_city_trends.csv")
print("q2 rows:", q2.shape, "cities:", q2["city"].nunique() if "city" in q2 else "n/a")
print(sorted(q2["city"].unique()))
q3 = pd.read_csv(C.RESULTS/"q3_city_risk.csv")
print("q3 cities:", sorted(q3["city"].unique()))
