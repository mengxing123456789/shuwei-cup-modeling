import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import common as C

s = pd.read_csv(C.RESULTS / "q5_selective_protection.csv")
print(s.columns.tolist())
print("rows", len(s), "| bcr notna", int(s["bcr"].notna().sum()),
      "| bcr>1", int((s["bcr"] > 1).sum()), "| max", round(float(s["bcr"].max()), 4))
print(s.groupby("city")["bcr"].agg(["count", "max"]).round(3).to_string())
print("storage values:", sorted(s["storage_mm"].unique().tolist()))
