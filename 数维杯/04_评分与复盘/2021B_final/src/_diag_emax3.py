import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from scipy import stats
from scipy.integrate import quad
import common as C

def emax_quantile(fit, n):
    c, loc, scale = fit["c"], fit["loc"], fit["scale"]
    f = lambda u: float(stats.genextreme.ppf(u ** (1.0 / n), c, loc=loc, scale=scale))
    val, err = quad(f, 0.0, 1.0, limit=400, points=[1e-8, 0.5, 1 - 1e-8])
    return val, err

for n in (7, 50):
    v, e = emax_quantile({"c": 0.0, "loc": 0.0, "scale": 1.0}, n)
    print(f"gumbel n={n}: {v:.4f} (theory {np.log(n)+0.5772:.4f}) err={e:.2e}")
g = C.load_ghcn_wide(C.RESULTS / "ghcn" / "CHM00050953.csv")
d = C.daily_grid(g[["date", "prcp_mm"]]); ai = C.annual_indices(d)
am = ai.loc[1961:2010, "rx1day"].to_numpy(float)
f = C.gev_fit_lmom(am)
print("harbin Emax7", emax_quantile(f, 7), "RL7", C.gev_return_level(f, 7), "mean", am.mean())