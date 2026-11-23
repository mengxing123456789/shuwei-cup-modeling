import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import common as C
from s03_q2 import bh_fdr

d = pd.read_csv(C.RESULTS / "q2_city_trends.csv")
INDICES = ["total", "rx1day", "r95p", "sdii", "wet_days"]

print("== single family of 150 (current code) ==")
pcols = [f"{c}_p" for c in INDICES] + ["ge50_p"]
flat = d[pcols].to_numpy(dtype=float).ravel()
q = bh_fdr(flat).reshape(d[pcols].shape)
for i, c in enumerate(INDICES + ["ge50"]):
    print(f"  {c:8s} sig={int((q[:, i] < 0.05).sum())}")

print("== per-index families of 25 (method as described in the text) ==")
for c in INDICES + ["ge50"]:
    p = d[f"{c}_p"].to_numpy(dtype=float)
    qq = bh_fdr(p)
    print(f"  {c:8s} n_tested={int(np.isfinite(p).sum()):2d} sig={int((qq < 0.05).sum())} "
          f"minq={np.nanmin(qq):.4f}")
