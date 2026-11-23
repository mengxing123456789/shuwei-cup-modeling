import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
import common as C

for sid in ["CHM00054511", "CHM00057083", "CHM00058362", "CHM00059287"]:
    g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{sid}.csv")
    g["year"] = g["date"].dt.year
    v = g.groupby("year").agg(rows=("prcp_mm", "size"), valid=("prcp_mm", "count"))
    print(sid, "rows", len(g), "date", g["date"].min().date(), g["date"].max().date())
    print(v.loc[2008:].to_string())
    print()