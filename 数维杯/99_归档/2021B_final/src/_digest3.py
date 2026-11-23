import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C, pandas as pd, numpy as np
q2 = pd.read_csv(C.RESULTS/"q2_city_trends.csv")
print(q2.columns.tolist())
for idx in ["total","rx1day","r95p","sdii","wet_days"]:
    col = f"{idx}_sen"
    if col in q2.columns:
        s = q2[col].dropna()
        print(idx, "n", len(s), "min %.3f max %.3f median %.3f" % (s.min(), s.max(), s.median()))
if "ge50_pct_per_decade" in q2.columns:
    s=q2["ge50_pct_per_decade"].dropna(); print("ge50 %", "min %.2f max %.2f median %.2f"%(s.min(),s.max(),s.median()))
    print("ge50 sig q<0.05:", int((q2.get("ge50_q", pd.Series(dtype=float))<0.05).sum()))
