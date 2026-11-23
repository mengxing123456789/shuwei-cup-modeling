import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import common as C

d = pd.read_csv(C.RESULTS / "q2_city_trends.csv")
for c in ["total", "rx1day", "r95p", "sdii", "wet_days"]:
    v = d[c + "_sen"].dropna()
    print(f"{c:9s} n={len(v):2d} median={v.median():+8.4f} "
          f"min={v.min():+8.3f} max={v.max():+8.3f} sig={int(d[c + '_sig'].sum())}")
v = d["ge50_pct_per_decade"].dropna()
print(f"ge50      n={len(v):2d} median={v.median():+8.4f} "
      f"min={v.min():+8.3f} max={v.max():+8.3f} sig={int(d['ge50_sig'].sum())}")
print("nulls in ge50_pct_per_decade:", int(d["ge50_pct_per_decade"].isna().sum()))
print("ge50 mean:", round(float(d['ge50_pct_per_decade'].mean()), 4))
