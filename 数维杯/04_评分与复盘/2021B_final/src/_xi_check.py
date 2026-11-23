import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import common as C

g = C.load_ghcn_wide(C.RESULTS / "ghcn" / "CHM00057083.csv")
d = C.daily_grid(g[["date", "prcp_mm"]])
ai = C.annual_indices(d)

for lo, hi in [(1961, 2020), (1961, 2024), (1961, 2010)]:
    sub = ai.loc[lo:hi]
    x = sub["rx1day"].dropna().to_numpy()
    lm = C.gev_fit_lmom(x)
    mle = C.gev_fit(x)
    print(f"{lo}-{hi}  n={len(x):3d}  lm_xi={-lm['xi']:+.5f}  mle_xi={-mle['xi']:+.5f}  "
          f"lm_scale={lm['scale']:.2f}  mle_scale={mle['scale']:.2f}")
