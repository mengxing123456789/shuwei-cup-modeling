import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import common as C
from s03_q2 import bh_fdr

d = pd.read_csv(C.RESULTS / "q2_city_trends.csv")
INDICES = ["total", "rx1day", "r95p", "sdii", "wet_days"]
pcols = [f"{c}_p" for c in INDICES] + ["ge50_p"]
mat = d[pcols].to_numpy(dtype=float)

# family of all finite tests (NaN dropped), which is what a careful implementation does
mask = np.isfinite(mat)
flat = mat[mask]
q = bh_fdr(flat)
qfull = np.full(mat.shape, np.nan)
qfull[mask] = q
print("family size (finite):", flat.size)
for i, c in enumerate(INDICES + ["ge50"]):
    print(f"  {c:8s} tested={int(mask[:, i].sum()):2d} sig={int((qfull[:, i] < 0.05).sum())}")
