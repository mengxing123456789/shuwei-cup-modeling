import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
import common as C

path = C.RESULTS / "ghcn" / "CHM00054511.csv"
g = C.load_ghcn_wide(path)
d = C.daily_grid(g[["date", "prcp_mm"]])
print("grid", len(d), d["date"].min(), d["date"].max(), "nulls", d["prcp_mm"].isna().sum())
d["year"] = d["date"].dt.year
v = d.groupby("year")["prcp_mm"].apply(lambda s: int(s.notna().sum()))
print(v.loc[2005:].to_string())
ai = C.annual_indices(d)
print("annual rows", len(ai), "idx 2011+:", list(ai.loc[2011:].index))