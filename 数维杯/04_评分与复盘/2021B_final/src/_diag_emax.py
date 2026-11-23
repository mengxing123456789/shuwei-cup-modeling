import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
import common as C
from s04_q3 import gev_emax

city = pd.read_csv(C.RESULTS / "q3_city_predictions.csv")
print(city[["city", "rx1day_sen", "GEV_Emax", "GEV_Emax_trend", "obs_max_rx1day"]].head(8).round(2).to_string(index=False))
print("max abs diff", (city["GEV_Emax_trend"] - city["GEV_Emax"]).abs().max())