import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")))
import numpy as np
from scipy import stats
import common as C
from s04_q3 import gev_emax
print("gumbel test (expect ~2.52):", gev_emax({"c":0.0,"loc":0.0,"scale":1.0}, 7))
print("gumbel test n=50 (expect ~4.5):", gev_emax({"c":0.0,"loc":0.0,"scale":1.0}, 50))
g = C.load_ghcn_wide(C.RESULTS/"ghcn"/"CHM00050953.csv")
d = C.daily_grid(g[["date","prcp_mm"]]); ai = C.annual_indices(d)
am = ai.loc[1961:2010,"rx1day"].to_numpy(float)
f = C.gev_fit_lmom(am)
print("harbin lm fit", {k: round(v,3) for k,v in f.items() if isinstance(v,float)})
print("RL7", C.gev_return_level(f,7), "Emax7", gev_emax(f,7), "mean am", am.mean(), "max am", am.max())
print("scipy ppf check", stats.genextreme.ppf([0.5,0.857,0.99], f["c"], loc=f["loc"], scale=f["scale"]))
