import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
import common as C

att = pd.read_csv(C.RESULTS / "attachment_daily_tidy.csv", parse_dates=["date"])
for sid in ["CHM00053772", "CHM00053959"]:
    g = C.load_ghcn_wide(C.RESULTS / "ghcn" / f"{sid}.csv")
    d = C.daily_grid(g[["date", "prcp_mm"]])["prcp_mm"]
    w = d.loc["2021-09-28":"2021-10-10"]
    print(sid, "missing in window:", int(w.isna().sum()), "of", len(w))
    print(w.to_string())
s = att[(att["station"].astype(str) == "53975099999") & (att["date"] >= "2021-09-28")
        & (att["date"] <= "2021-10-10")][["date", "prcp_mm"]]
print("53975099999 rows", len(s))
print(s.to_string(index=False))