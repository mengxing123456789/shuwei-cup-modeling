import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
import common as C
from s04_q3 import TRAIN, TEST

for path in sorted((C.RESULTS / "ghcn").glob("CHM*.csv"))[:4]:
    head = pd.read_csv(path, nrows=1, dtype=str, keep_default_na=False, skipinitialspace=True)
    head.columns = [c.strip().upper() for c in head.columns]
    g = C.load_ghcn_wide(path)
    d = C.daily_grid(g[["date", "prcp_mm"]])
    ai = C.annual_indices(d)
    print(path.name, "wide cols", list(g.columns)[:4], "ai rows", len(ai), "index dtype", ai.index.dtype,
          "first/last", ai.index.min(), ai.index.max())
    tr = ai.loc[TRAIN[0]:TRAIN[1]]
    te = ai.loc[TEST[0]:TEST[1]]
    print("   train", tr.shape[0], "test", te.shape[0])